"""Spec 015 T020 (I-2): why an approval row stopped being open, and who may write that.

Every NI-2.3 row is driven through its real path: `answer_prompt` with the real
`_LivePromptResolver` (Bot Chat over a fake HTTP session and the real classifier, Phone over the
real bridge coercion), `AdapterHooks.reconcile_chat` and `retire`, the real `consume_sse` for the
end of a bound stream, and the real AP-3 route. The lock, clock and concurrency tests are causal:
each fails when the guarded single writer is replaced by the unguarded one of `150bd0f`.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
import types
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import direct_send as ds
from hmp_plugin import prompts, server
from hmp_plugin.bridge import HermesReadBridge
from hmp_plugin.contract import DirectSendEndpoint
from hmp_plugin.prompts import AdapterHooks, HttpResult, PromptRow, PromptStore, is_authoritative

from .hmp_kit import Env, get, pair, run
from .test_approval_native_answer import _error, _fake_session
from .test_approval_route_gates import BOT, _row, _setup
from .test_approvals import IID, PROFILE, REQ, RUN, USER, _frame

ENDPOINT = DirectSendEndpoint(host="127.0.0.1", port=9, api_key="k" * 20, path_prefix="")
SESSION = "namespace:hmp:dm:phone"
CHOICES = ("once", "session", "always", "deny")
PRE_AWAIT = 5_000  # what the store clock reads before the Hermes call
OTHER_WRITER_AT = 9_999  # when a concurrent path settles the row during the await


def _approval(surface: str = "bot_chat", **extra: Any) -> PromptRow:
    bot = surface == "bot_chat"
    fields: dict[str, Any] = {
        "iid": IID, "user_id": USER, "profile": PROFILE, "request_id": REQ, "kind": "approval",
        "surface": surface, "choices": CHOICES, "command": "ls", "description": "d",
        "run_id": RUN if bot else None, "session_key": None if bot else SESSION,
        "expires_at": PRE_AWAIT + 100, "observed_at": 1_000,
    }
    fields.update(extra)
    return PromptRow(**fields)


def _clarify(**extra: Any) -> PromptRow:
    fields: dict[str, Any] = {
        "iid": IID, "user_id": USER, "profile": PROFILE, "request_id": REQ, "kind": "clarify",
        "surface": "phone_chat", "choices": (), "question": "Ship?", "awaiting_text": True,
        "session_key": SESSION, "expires_at": PRE_AWAIT + 100, "observed_at": 1_000,
    }
    fields.update(extra)
    return PromptRow(**fields)


def _store(row: PromptRow | None = None) -> PromptStore:
    store = PromptStore(clock=lambda: PRE_AWAIT)
    if row is not None:
        store.put(row)
        assert store.get((row.iid, row.user_id, row.profile, row.request_id)) is row
    return store


class _PhoneBridge:
    """The Hermes-facing calls the live Phone resolver makes. `approval` is the raw helper
    result, coerced by the real `HermesReadBridge.resolve_gateway_approval`."""

    def __init__(self, approval: Any = 1, clarify: bool = True, awaiting: bool = True) -> None:
        self.approval, self.clarify, self.awaiting = approval, clarify, awaiting

    def _call_phone(self, *_a: Any, **_k: Any) -> Any:
        return self.approval

    resolve_gateway_approval = HermesReadBridge.resolve_gateway_approval

    def resolve_gateway_clarify(self, _id: str, _response: str) -> bool:
        return self.clarify

    def mark_clarify_awaiting_text(self, _id: str) -> bool:
        return self.awaiting


def _live(bridge: Any = None, endpoint: Any = ENDPOINT) -> Any:
    return server._LivePromptResolver(types.SimpleNamespace(bridge=bridge), endpoint)


async def _answer(store: PromptStore, resolver: Any, body: dict[str, Any], now: int = 2_000):
    async def unowned(_row: PromptRow) -> prompts.DesktopOwnership:
        return prompts.DesktopOwnership.UNOWNED

    return await prompts.answer_prompt(
        store, iid=IID, user_id=USER, profile=PROFILE, request_id=REQ, body=body,
        resolver=resolver, now=now, ownership_check=unowned,
    )


def _settled(row: PromptRow) -> tuple[str, int | None, str | None]:
    return row.status, row.settled_at, row.settle_cause


# --------------------------------------------------------------------------------------------
# Contract of the writers
# --------------------------------------------------------------------------------------------


def test_expire_requires_a_cause_and_records_it_first_writer_wins() -> None:
    row = _approval()
    with pytest.raises(TypeError):
        PromptStore.expire(row, 1)  # type: ignore[call-arg]
    PromptStore.expire(row, 7, cause="local_expiry")
    PromptStore.expire(row, 8, cause="generation_closed")
    assert _settled(row) == ("expired", 7, "local_expiry")


def test_settle_answer_and_remember_have_the_frozen_shapes() -> None:
    assert list(inspect.signature(prompts._remember).parameters) == ["row", "result", "digest"]
    params = inspect.signature(PromptStore.settle_answer).parameters
    assert list(params) == ["self", "row", "status", "cause", "now"]
    assert all(params[name].kind is inspect.Parameter.KEYWORD_ONLY
               for name in ("status", "cause", "now"))


def test_remember_writes_only_replay_fields() -> None:
    row = _approval()
    prompts._remember(row, HttpResult(200, {"status": "resolved"}), b"digest")
    assert (row.stored_status, row.stored_body, row.answer_hash) == (
        200, {"status": "resolved"}, b"digest")
    assert _settled(row) == ("open", None, None)
    prompts._remember(row, HttpResult(409, {"x": 1}), None)
    assert row.answer_hash == b"digest" and _settled(row) == ("open", None, None)


def test_settle_answer_overwrites_unconditionally_and_reads_no_clock() -> None:
    def clock() -> float:
        raise AssertionError("settle_answer sampled a clock")

    store = PromptStore(clock=clock)
    row = _approval()
    PromptStore.expire(row, 3, cause="local_expiry")
    store.settle_answer(row, status="resolved", cause="answer_applied", now=11)
    assert _settled(row) == ("resolved", 11, "answer_applied")


# --------------------------------------------------------------------------------------------
# NI-2.3, answer path, through the real resolver
# --------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bot_chat_applied_answer_is_answer_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_session(monkeypatch, 200, b'{"resolved":1}')
    row = _approval()
    store = _store(row)
    result = await _answer(store, _live(), {"choice": "once"})
    assert (result.status, result.body) == (200, {"status": "resolved", "applied": True})
    assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")
    assert is_authoritative(row.settle_cause)


@pytest.mark.asyncio
async def test_phone_applied_answer_is_answer_applied() -> None:
    row = _approval("phone_chat")
    await _answer(_store(row), _live(_PhoneBridge(approval=2)), {"choice": "deny"})
    assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"text": "yes"}, {"other": True}])
async def test_clarify_accepted_and_awaiting_text(body: dict[str, Any]) -> None:
    row = _clarify(awaiting_text="other" not in body)
    result = await _answer(_store(row), _live(_PhoneBridge()), body)
    if "other" in body:  # awaiting_text is not a settle write
        assert result.body["status"] == "awaiting_text"
        assert _settled(row) == ("open", None, None)
    else:
        assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")


@pytest.mark.asyncio
async def test_clarify_choice_accepted_is_answer_applied() -> None:
    row = _clarify(choices=("Ship", "Wait"), awaiting_text=False)
    await _answer(_store(row), _live(_PhoneBridge()), {"choice": "Ship"})
    assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "body"),
    [
        (409, _error("approval_not_pending")),
        (409, _error("approval_not_active")),
        (404, _error("run_not_found")),
    ],
)
async def test_each_native_code_on_a_bot_chat_row_is_native_not_pending(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes
) -> None:
    seen = _fake_session(monkeypatch, status, body)
    row = _approval()
    store = _store(row)
    result = await _answer(store, _live(), {"choice": "once"})
    assert (result.status, result.body["error"]["code"]) == (409, "stale")  # type: ignore[index]
    assert _settled(row) == ("expired", PRE_AWAIT, "native_not_pending")
    assert is_authoritative(row.settle_cause)
    assert seen["posts"] == 1
    # The row is now expired, so the second answer returns stale before any Hermes call.
    replay = await _answer(store, _live(), {"choice": "once"})
    assert replay.status == 409 and row.settle_cause == "native_not_pending"
    assert seen["posts"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["bot_chat", "phone_chat"])
async def test_the_stale_branch_writes_the_replay_fields_but_never_the_answer_hash(
    monkeypatch: pytest.MonkeyPatch, surface: str
) -> None:
    """After the real answer path settles a row as stale, `_remember(row, result, None)` has
    stored the stale result in the existing replay fields and left `answer_hash` unset. The
    expired-row branch returns before `_replay`, so this pins the write itself, not a replay."""
    if surface == "bot_chat":
        _fake_session(monkeypatch, 409, _error("approval_not_pending"))
        resolver = _live()
    else:
        resolver = _live(_PhoneBridge(approval=0))
    row = _approval(surface)
    result = await _answer(_store(row), resolver, {"choice": "once"})
    assert (result.status, result.body["error"]["code"]) == (409, "stale")  # type: ignore[index]
    assert row.status == "expired"
    assert row.stored_status == 409 and row.stored_body == result.body
    assert row.answer_hash is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, b'{"resolved":0}'), (200, b"{}"), (200, b"not json"), (409, _error("other_code")),
        (404, b"<html></html>"), (401, b"{}"), (403, _error("run_not_found")), (500, b"{}"),
        (302, b""),
    ],
)
async def test_every_other_native_result_leaves_the_row_open_with_no_cause(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes
) -> None:
    _fake_session(monkeypatch, status, body)
    row = _approval()
    result = await _answer(_store(row), _live(), {"choice": "once"})
    assert result.status == 503
    assert _settled(row) == ("open", None, None) and row.stored_status is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [TimeoutError(), ds.aiohttp.ClientConnectionError("x")])
async def test_a_native_timeout_leaves_the_row_open_with_no_cause(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    _fake_session(monkeypatch, 200, b"{}", fail=failure)
    row = _approval()
    assert (await _answer(_store(row), _live(), {"choice": "once"})).status == 503
    assert _settled(row) == ("open", None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, b'{"resolved":1}'), (409, _error("approval_not_pending")),
        (409, _error("approval_not_active")), (404, _error("run_not_found")),
        (409, _error("x")), (404, b"<html>"), (401, b"{}"), (403, b"{}"), (500, b"{}"),
        (200, b'{"resolved":0}'), (200, b"nope"), (200, b'{"resolved":true}'),
    ],
)
async def test_the_live_bot_chat_resolver_is_stale_only_from_the_native_classifier(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes
) -> None:
    """RD-5: the answer path derives `native_not_pending` from row kind and surface, so this pins
    that the live Bot Chat resolver returns `stale` only when `classify_native_answer` does."""
    _fake_session(monkeypatch, status, body)
    verdict = await _live().resolve_approval(_approval(), "once")
    assert verdict == ds.classify_native_answer(status, body)
    if verdict == "stale":
        assert (status, __import__("json").loads(body)["error"]["code"]) in ds._NATIVE_STALE


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [0, "1", True, None, 1.5, [1], -1])
async def test_a_phone_resolve_without_a_positive_count_is_phone_not_resolved(raw: Any) -> None:
    """The real bridge coerces a non-int (and a bool) to 0, so `0` and the coerced values are the
    same non-authoritative answer (RD-4)."""
    row = _approval("phone_chat")
    result = await _answer(_store(row), _live(_PhoneBridge(approval=raw)), {"choice": "once"})
    assert result.status == 409
    assert _settled(row) == ("expired", PRE_AWAIT, "phone_not_resolved")
    assert not is_authoritative(row.settle_cause)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("row", "bridge", "body"),
    [
        (_clarify(), _PhoneBridge(clarify=False), {"text": "yes"}),
        (_clarify(awaiting_text=False), _PhoneBridge(awaiting=False), {"other": True}),
        (_clarify(choices=("Ship", "Wait"), awaiting_text=False), _PhoneBridge(clarify=False),
         {"choice": "Ship"}),
    ],
)
async def test_a_stale_clarify_is_phone_not_resolved(
    row: PromptRow, bridge: _PhoneBridge, body: dict[str, Any]
) -> None:
    assert (await _answer(_store(row), _live(bridge), body)).status == 409
    assert _settled(row) == ("expired", PRE_AWAIT, "phone_not_resolved")


@pytest.mark.asyncio
async def test_an_unavailable_phone_helper_changes_nothing() -> None:
    class Failing(_PhoneBridge):
        def _call_phone(self, *_a: Any, **_k: Any) -> Any:
            raise prompts.HelperUnavailableError("x")

    row = _approval("phone_chat")
    assert (await _answer(_store(row), _live(Failing()), {"choice": "once"})).status == 503
    assert _settled(row) == ("open", None, None)


# --------------------------------------------------------------------------------------------
# NI-2.3, listing, local, close, fence, run end, retire
# --------------------------------------------------------------------------------------------


class _Lister:
    def __init__(self, result: Any) -> None:
        self.result = result

    def list_gateway_approvals(self, _key: str) -> Any:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _hooks(store: PromptStore, bridge: Any = None, now: int = OTHER_WRITER_AT) -> AdapterHooks:
    return AdapterHooks(store=store, bridge=bridge, now=lambda: now, iid=IID,
                        phone_available=lambda: True)


@pytest.mark.asyncio
async def test_a_successful_listing_without_the_row_is_phone_listing_omitted() -> None:
    row, kept = _approval("phone_chat"), _approval("phone_chat", request_id="req_kept" + "0" * 8)
    store = _store(row)
    store.put(kept)
    store.remember_session(SESSION, IID, USER, PROFILE, "chat")
    hooks = _hooks(store, _Lister([{"request_id": kept.request_id}, "junk"]))
    await hooks.reconcile_chat("chat")
    assert _settled(row) == ("expired", OTHER_WRITER_AT, "phone_listing_omitted")
    assert is_authoritative(row.settle_cause)
    assert _settled(kept) == ("open", None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [RuntimeError("x"), prompts.HelperUnavailableError("x"),
                                    "not a list", None])
async def test_a_raising_or_non_list_lister_changes_nothing(result: Any) -> None:
    row = _approval("phone_chat")
    store = _store(row)
    store.remember_session(SESSION, IID, USER, PROFILE, "chat")
    await _hooks(store, _Lister(result)).reconcile_chat("chat")
    assert _settled(row) == ("open", None, None)


@pytest.mark.parametrize(("listing", "expected"), [
    ([], ("expired", "phone_listing_omitted")),
    ([{"request_id": REQ}], ("open", None)),
    (prompts.HelperUnavailableError("x"), ("open", None)),
])
def test_ap3_route_reconcile_records_the_listing_cause(
    tmp_path: Path, listing: Any, expected: tuple[str, str | None]
) -> None:
    env = Env(tmp_path)
    _setup(env)

    def lister(*_a: Any, **_k: Any) -> Any:
        if isinstance(listing, Exception):
            raise listing
        return listing

    env.bridge.list_gateway_approvals = lister  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="phone_chat")
        status, _body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert (row.status, row.settle_cause) == expected

    run(env, scenario)


def test_purge_past_the_grace_is_local_expiry_and_not_authoritative() -> None:
    row = _approval(expires_at=100)
    store = _store(row)
    store.purge(130)
    assert _settled(row) == ("open", None, None)
    store.purge(131)
    assert _settled(row) == ("expired", 131, "local_expiry")
    assert not is_authoritative(row.settle_cause)
    store.close(500)  # first writer wins
    assert _settled(row) == ("expired", 131, "local_expiry")


def test_close_is_generation_closed_for_every_open_row_only() -> None:
    bot, phone, done = _approval(), _approval("phone_chat", request_id="r2" * 8), _approval(
        request_id="r3" * 8)
    store = _store(bot)
    store.put(phone)
    store.put(done)
    PromptStore.expire(done, 4, cause="local_expiry")
    store.close(77)
    assert _settled(bot) == ("expired", 77, "generation_closed")
    assert _settled(phone) == ("expired", 77, "generation_closed")
    assert _settled(done) == ("expired", 4, "local_expiry")
    assert not is_authoritative(bot.settle_cause)


def test_close_phone_chat_is_binding_fence_for_phone_rows_only() -> None:
    bot, phone = _approval(), _approval("phone_chat", request_id="r2" * 8)
    store = _store(bot)
    store.put(phone)
    store.close_phone_chat(66)
    assert _settled(phone) == ("expired", 66, "binding_fence")
    assert _settled(bot) == ("open", None, None)
    assert not is_authoritative(phone.settle_cause)


@pytest.mark.asyncio
@pytest.mark.parametrize("completes", [True, False])
async def test_the_end_of_a_bound_stream_is_run_ended_never_authoritative(completes: bool) -> None:
    """D4: run completion, and a stream that ends without one, settle a row as `run_ended`."""
    store = PromptStore(clock=lambda: 1)
    bind = ds.StreamBind(store=store, iid=IID, user_id=USER, profile=PROFILE,
                         now=lambda: 321, timeout_s=300)

    async def parts():
        yield _frame("run.started", {"run_id": RUN})
        yield _frame("approval.request", {"run_id": RUN, "request_id": REQ, "command": "x",
                                          "choices": ["once", "deny"]})
        if completes:
            yield _frame("assistant.completed", {"content": "ok", "session_id": "s1"})
            yield _frame("run.completed", {"run_id": RUN})
            yield _frame("done", {})

    if completes:
        await ds.consume_sse(parts(), bind=bind)
    else:
        with pytest.raises(ds.aiohttp.ClientPayloadError):
            await ds.consume_sse(parts(), bind=bind)
    row = store.get((IID, USER, PROFILE, REQ))
    assert row is not None
    assert _settled(row) == ("expired", 321, "run_ended")
    assert not is_authoritative(row.settle_cause)


def test_retire_is_clarify_retired_and_only_for_an_open_clarify() -> None:
    clarify = _clarify()
    approval = _approval("phone_chat", request_id="r2" * 8)
    store = _store(clarify)
    store.put(approval)
    hooks = _hooks(store, now=88)
    hooks.retire(approval.request_id)  # an approval with that ID is not a clarify
    assert _settled(approval) == ("open", None, None)
    hooks.retire(REQ)
    assert _settled(clarify) == ("expired", 88, "clarify_retired")
    assert not is_authoritative(clarify.settle_cause)
    hooks.now = lambda: 99
    hooks.retire(REQ)
    assert _settled(clarify) == ("expired", 88, "clarify_retired")


# --------------------------------------------------------------------------------------------
# Locks, clock and the replay fields
# --------------------------------------------------------------------------------------------


class _CountingGuard:
    """The store's `threading.Lock` with a count of sections entered."""

    def __init__(self, inner: Any) -> None:
        self.inner, self.sections = inner, 0

    def __enter__(self) -> _CountingGuard:
        self.inner.acquire()
        self.sections += 1
        return self

    def __exit__(self, *_exc: object) -> bool:
        self.inner.release()
        return False

    def locked(self) -> bool:
        return self.inner.locked()


class _ProbeRow(PromptRow):
    """Records the guard state at every write of the three settle attributes."""

    def __setattr__(self, name: str, value: Any) -> None:
        probe = self.__dict__.get("_probe")
        if probe is not None and name in ("status", "settled_at", "settle_cause"):
            probe(name)
        object.__setattr__(self, name, value)


def _probed(store: PromptStore, row: _ProbeRow) -> list[tuple[str, bool, int]]:
    guard = _CountingGuard(store._guard)
    store._guard = guard  # type: ignore[assignment]
    writes: list[tuple[str, bool, int]] = []
    object.__setattr__(row, "_probe", lambda name: writes.append(
        (name, guard.locked(), guard.sections)))
    return writes


class _Resolver:
    def __init__(self, verdict: str, store: PromptStore | None = None, during: Any = None) -> None:
        self.verdict, self.store, self.during, self.calls = verdict, store, during, 0

    async def resolve_approval(self, row: PromptRow, choice: str) -> str:
        self.calls += 1
        if self.store is not None:
            assert not self.store._guard.locked()  # no await while `_guard` is held
        if self.during is not None:
            await self.during(row)
        await asyncio.sleep(0)
        return self.verdict

    async def resolve_clarify(self, row: PromptRow, response: str) -> str:
        return await self.resolve_approval(row, response)

    async def mark_awaiting(self, row: PromptRow) -> str:
        return "ok"


@pytest.mark.asyncio
@pytest.mark.parametrize(("verdict", "status", "cause"), [
    ("accepted", "resolved", "answer_applied"), ("stale", "expired", "native_not_pending")])
async def test_every_status_settled_at_and_cause_write_is_one_guarded_section(
    verdict: str, status: str, cause: str
) -> None:
    row = _ProbeRow(**vars(_approval()))
    store = _store(row)
    writes = _probed(store, row)
    await _answer(store, _Resolver(verdict, store), {"choice": "once"})
    assert sorted(name for name, _locked, _n in writes) == ["settle_cause", "settled_at", "status"]
    assert all(locked for _name, locked, _n in writes)
    assert len({n for _name, _locked, n in writes}) == 1  # one `_guard` section for all three
    assert _settled(row) == (status, PRE_AWAIT, cause)


@pytest.mark.asyncio
async def test_a_writer_waits_for_the_guard_and_nothing_is_written_before_it_is_free() -> None:
    row = _approval()
    store = _store(row)
    held, observed = threading.Event(), []

    def holder() -> None:
        with store._guard:
            held.set()
            time.sleep(0.25)
            observed.append(_settled(row))

    thread = threading.Thread(target=holder)

    async def during(_row: PromptRow) -> None:
        thread.start()
        assert await asyncio.to_thread(held.wait, 5)  # bounded: fail rather than hang

    try:
        await _answer(store, _Resolver("accepted", during=during), {"choice": "once"})
    finally:
        if thread.ident is not None:
            thread.join(5)
    assert not thread.is_alive()
    assert observed == [("open", None, None)]  # the answer's writes waited for the lock
    assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["accepted", "stale"])
async def test_settled_at_is_the_pre_await_sample_and_the_helper_reads_no_clock(
    verdict: str,
) -> None:
    reads: list[int] = []
    now = {"value": PRE_AWAIT}

    def clock() -> float:
        reads.append(now["value"])
        return now["value"]

    async def during(_row: PromptRow) -> None:
        now["value"] = PRE_AWAIT + 4_000  # the clock moves while Hermes is awaited

    row = _approval(expires_at=None)
    store = PromptStore(clock=clock)
    store.put(row)
    await _answer(store, _Resolver(verdict, during=during), {"choice": "once"}, now=2_000)
    assert reads == [PRE_AWAIT]  # one sample, before the await; `settle_answer` read none
    assert row.settled_at == PRE_AWAIT


@pytest.mark.asyncio
async def test_a_caller_clock_ahead_of_the_store_clock_wins_the_pre_await_max() -> None:
    row = _approval(expires_at=None)
    store = _store(row)
    await _answer(store, _Resolver("accepted"), {"choice": "once"}, now=PRE_AWAIT + 7)
    assert row.settled_at == PRE_AWAIT + 7


@pytest.mark.asyncio
async def test_a_queued_answerer_never_sees_resolved_without_its_replay_fields() -> None:
    row = _approval()
    store = _store(row)
    resolver = _Resolver("accepted", store)
    first, second = await asyncio.gather(
        _answer(store, resolver, {"choice": "once"}), _answer(store, resolver, {"choice": "once"})
    )
    assert resolver.calls == 1 and first.body == second.body
    assert row.answer_hash is not None and row.stored_status == 200
    assert _settled(row) == ("resolved", PRE_AWAIT, "answer_applied")
    conflict = await _answer(store, resolver, {"choice": "deny"})
    assert conflict.status == 409 and conflict.body["error"]["code"] == "idempotency_conflict"  # type: ignore[index]


# --------------------------------------------------------------------------------------------
# A concurrent settlement during the awaited Hermes call (RD-7, NI-2.4)
# --------------------------------------------------------------------------------------------


def _writers() -> dict[str, Any]:
    """writer -> (row factory, action run on a worker thread, the cause it records)."""

    def purge(store: PromptStore, _row: PromptRow) -> None:
        store.purge(OTHER_WRITER_AT)

    def close(store: PromptStore, _row: PromptRow) -> None:
        store.close(OTHER_WRITER_AT)

    def fence(store: PromptStore, _row: PromptRow) -> None:
        store.close_phone_chat(OTHER_WRITER_AT)

    def reconcile(store: PromptStore, _row: PromptRow) -> None:
        store.reconcile_approvals(SESSION, set(), OTHER_WRITER_AT)

    def run_end(store: PromptStore, _row: PromptRow) -> None:
        store.expire_run(RUN, OTHER_WRITER_AT)

    def retire(store: PromptStore, _row: PromptRow) -> None:
        _hooks(store).retire(REQ)

    return {
        "purge": (_approval, purge, "local_expiry"),
        "close": (_approval, close, "generation_closed"),
        "close_phone_chat": (lambda: _approval("phone_chat"), fence, "binding_fence"),
        "reconcile": (lambda: _approval("phone_chat"), reconcile, "phone_listing_omitted"),
        "expire_run": (_approval, run_end, "run_ended"),
        "retire": (_clarify, retire, "clarify_retired"),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("writer", list(_writers()))
@pytest.mark.parametrize("verdict", ["accepted", "stale"])
async def test_the_answer_overwrites_a_concurrent_settlement_and_owns_the_cause(
    writer: str, verdict: str
) -> None:
    factory, action, recorded = _writers()[writer]
    row = factory()
    store = _store(row)
    seen: list[tuple[str, int | None, str | None]] = []

    async def during(live: PromptRow) -> None:
        await asyncio.to_thread(action, store, live)  # a worker thread settles it mid-await
        seen.append(_settled(live))

    body = {"text": "yes"} if row.kind == "clarify" else {"choice": "once"}
    await _answer(store, _Resolver(verdict, during=during), body)
    assert seen == [("expired", OTHER_WRITER_AT, recorded)]
    if verdict == "accepted":
        expected = ("resolved", PRE_AWAIT, "answer_applied")
    elif row.kind == "approval" and row.surface == "bot_chat":
        expected = ("expired", PRE_AWAIT, "native_not_pending")
    else:
        expected = ("expired", PRE_AWAIT, "phone_not_resolved")
    assert _settled(row) == expected  # unconditional overwrite; no first-writer-wins, no merge


@pytest.mark.asyncio
async def test_an_authoritative_listing_cause_is_downgraded_by_a_phone_stale_answer() -> None:
    """NI-2.4: fails closed. The cause belongs to the last status writer."""
    row = _approval("phone_chat")
    store = _store(row)
    store.remember_session(SESSION, IID, USER, PROFILE, "chat")
    hooks = _hooks(store, _Lister([]))

    async def during(_row: PromptRow) -> None:
        await hooks.reconcile_chat("chat")
        assert is_authoritative(row.settle_cause)  # `phone_listing_omitted`, recorded first

    result = await _answer(store, _Resolver("stale", during=during), {"choice": "once"})
    assert result.status == 409
    assert _settled(row) == ("expired", PRE_AWAIT, "phone_not_resolved")
    assert not is_authoritative(row.settle_cause)
