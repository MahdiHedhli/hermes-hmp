"""F3 approvals and Phone chat (HMP_V1.md §7b). Fakes only — no Hermes import."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import direct_send as ds
from hmp_plugin import prompts
from hmp_plugin.contract import AuthzState, DirectSendEndpoint, ErrorCode
from hmp_plugin.direct_send import DirectSendDeps, ProfileLocks, StreamBind
from hmp_plugin.logging_policy import LOGGER_NAME
from hmp_plugin.prompts import AdapterHooks, PromptRow, PromptStore

from .hmp_kit import Env, get, pair, post, run

IID = "iid_" + "a" * 48
USER = "hmpu_" + "ab" * 16
OTHER = "hmpu_" + "cd" * 16
PROFILE = "default"
REQ = "req_" + "12" * 16
RUN = "run_" + "34" * 16
SECRET_COMMAND = "rm -rf /super-secret-path"


class FakeResolver:
    def __init__(self, verdict: str = "accepted") -> None:
        self.verdict = verdict
        self.calls: list[tuple[Any, ...]] = []

    async def resolve_approval(self, row: PromptRow, choice: str) -> str:
        self.calls.append(("approval", row.request_id, row.run_id, row.session_key, choice))
        return self.verdict

    async def resolve_clarify(self, row: PromptRow, response: str) -> str:
        self.calls.append(("clarify", row.request_id, response))
        return "accepted" if self.verdict == "accepted" else "stale"

    async def mark_awaiting(self, row: PromptRow) -> str:
        self.calls.append(("other", row.request_id))
        return "ok" if self.verdict != "stale" else "stale"


def _store_approval(store: PromptStore, *, user: str = USER, **overrides: Any) -> None:
    row = PromptRow(
        iid=IID,
        user_id=user,
        profile=PROFILE,
        request_id=REQ,
        kind="approval",
        surface="bot_chat",
        choices=("once", "session", "always", "deny"),
        command=SECRET_COMMAND,
        description="because",
        run_id=RUN,
        session_key="namespace:hmp:dm:should-not-be-used",
        observed_at=1_000,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    store.put(row)


def _store_clarify(store: PromptStore, **overrides: Any) -> None:
    row = PromptRow(
        iid=IID,
        user_id=USER,
        profile=PROFILE,
        request_id=REQ,
        kind="clarify",
        surface="phone_chat",
        choices=("Ship it (Recommended)", "Wait"),
        question="Ship?",
        session_key="namespace:hmp:dm:phone",
        observed_at=1_000,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    store.put(row)


async def _answer(
    store: PromptStore, resolver: FakeResolver, body: dict[str, Any], **kw: Any
) -> prompts.HttpResult:
    return await prompts.answer_prompt(
        store,
        iid=kw.get("iid", IID),
        user_id=kw.get("user_id", USER),
        profile=PROFILE,
        request_id=kw.get("request_id", REQ),
        body=body,
        resolver=resolver,
        now=kw.get("now", 2_000),
    )


@pytest.mark.asyncio
async def test_first_accept_then_same_body_does_not_call_again() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store)
    first = await _answer(store, resolver, {"choice": "once", "session_key": "client-supplied"})
    assert first.status == 200 and first.body["applied"] is True
    assert resolver.calls == [("approval", REQ, RUN, "namespace:hmp:dm:should-not-be-used", "once")]
    second = await _answer(store, resolver, {"choice": "once"})
    assert second.body == first.body
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
async def test_different_choice_after_accept_is_a_conflict() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store)
    await _answer(store, resolver, {"choice": "once"})
    conflict = await _answer(store, resolver, {"choice": "always"})
    assert conflict.status == 409
    assert conflict.body["applied"] is False
    assert conflict.body["error"]["code"] == "idempotency_conflict"
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
async def test_stale_resolver_is_applied_false_and_replayed() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver("stale")
    _store_approval(store)
    stale = await _answer(store, resolver, {"choice": "deny"})
    assert stale.status == 409 and stale.body["applied"] is False
    assert stale.body["error"]["code"] == "stale"
    again = await _answer(store, resolver, {"choice": "once"})
    assert again.body["error"]["code"] == "stale"
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
async def test_unknown_and_other_user_are_404_with_no_call() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store)
    missing = await _answer(
        store, resolver, {"choice": "once"}, request_id="never-stored-id-12345678"
    )
    foreign = await _answer(store, resolver, {"choice": "once"}, user_id=OTHER)
    assert missing.status == foreign.status == 404
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_choice_not_offered_does_not_call() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store, choices=("once", "deny"))
    result = await _answer(store, resolver, {"choice": "always"})
    assert result.status == 409 and result.body["applied"] is False
    assert result.body["error"]["code"] == "invalid_choice"
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_all_and_mixed_bodies_are_400() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store)
    for body in (
        {"choice": "once", "all": True},
        {"choice": "once", "resolve_all": False},
        {"choice": "once", "text": "yes"},
        {"other": True, "text": "x"},
        {"other": False},
    ):
        result = await _answer(store, resolver, body)
        assert result.status == 400, body
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_past_expiry_grace_is_refused() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store, expires_at=1)
    result = await _answer(store, resolver, {"choice": "once"}, now=10_000)
    assert result.body["applied"] is False
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_clarify_strips_recommended_and_other_then_text() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store)
    chosen = await _answer(store, resolver, {"choice": "Ship it (Recommended)"})
    assert chosen.body == {"status": "resolved", "applied": True}
    assert resolver.calls[-1] == ("clarify", REQ, "Ship it")

    store2, resolver2 = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store2)
    other = await _answer(store2, resolver2, {"other": True})
    assert other.body == {"status": "awaiting_text", "applied": False}
    prose = await _answer(store2, resolver2, {"text": "something else"})
    assert prose.body["applied"] is True
    assert resolver2.calls[-1] == ("clarify", REQ, "something else")


@pytest.mark.asyncio
async def test_clarify_text_before_other_is_invalid_and_not_applied() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store)
    result = await _answer(store, resolver, {"text": "free prose"})
    assert result.status == 409 and result.body["applied"] is False
    assert resolver.calls == []
    assert store.get((IID, USER, PROFILE, REQ)).status == "open"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_multi_select_dumps_labels() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store, choices=("A (Recommended)", "B"), multi_select=True)
    result = await _answer(store, resolver, {"choices": ["A (Recommended)", "B"]})
    assert result.body["applied"] is True
    assert resolver.calls[-1][2] == json.dumps(["A", "B"], ensure_ascii=False)


AMBIGUOUS_OFFERS = [
    ("Apple", "apple"),
    ("Apple", " apple "),
    ("Apple (Recommended)", "apple"),
    ("Apple", "apple (RECOMMENDED)"),
    ("Straße", "STRASSE"),
    ("σ", "ς"),  # noqa: RUF001 - deliberate Greek sigma collision vector
    ("Σ", "ς"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("first", "second"), AMBIGUOUS_OFFERS)
@pytest.mark.parametrize("multi", [False, True])
async def test_ambiguous_normalized_choice_is_refused(first: str, second: str, multi: bool) -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store, choices=(first, second, "Other"), multi_select=multi)
    for submitted in (first, second, first.casefold()):
        body = {"choices": [submitted]} if multi else {"choice": submitted}
        result = await _answer(store, resolver, body)
        assert result.status == 409 and result.body["applied"] is False
        assert result.body["error"]["code"] == "invalid_choice"
    assert resolver.calls == []
    assert store.get((IID, USER, PROFILE, REQ)).status == "open"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_multi_ambiguous_member_refuses_whole_answer() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store, choices=("Apple", "apple", "B"), multi_select=True)
    result = await _answer(store, resolver, {"choices": ["B", "APPLE"]})
    assert result.status == 409 and result.body["applied"] is False
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_unambiguous_normalized_choice_still_resolves() -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_clarify(store, choices=("Straße (Recommended)", "B"))
    result = await _answer(store, resolver, {"choice": " STRASSE "})
    assert result.body == {"status": "resolved", "applied": True}
    assert resolver.calls[-1] == ("clarify", REQ, "Straße")


@pytest.mark.asyncio
async def test_two_in_flight_answers_share_one_resolver_call() -> None:
    store = PromptStore(clock=lambda: 1)
    _store_approval(store)
    started = asyncio.Event()
    release = asyncio.Event()

    class Slow(FakeResolver):
        async def resolve_approval(self, row: PromptRow, choice: str) -> str:
            started.set()
            await release.wait()
            return await super().resolve_approval(row, choice)

    resolver = Slow()
    first = asyncio.create_task(_answer(store, resolver, {"choice": "once"}))
    await started.wait()
    second = asyncio.create_task(_answer(store, resolver, {"choice": "once"}))
    await asyncio.sleep(0)
    release.set()
    assert (await first).body["applied"] is True
    assert (await second).body["applied"] is True
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
async def test_logs_do_not_contain_the_command(caplog: pytest.LogCaptureFixture) -> None:
    store, resolver = PromptStore(clock=lambda: 1), FakeResolver()
    _store_approval(store)
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        await _answer(store, resolver, {"choice": "deny"})
    assert SECRET_COMMAND not in caplog.text
    assert "outcome=resolved" in caplog.text
    assert "resolved_deny" not in caplog.text
    assert "because" not in caplog.text


@pytest.mark.asyncio
async def test_desktop_held_hides_bot_chat_cards_and_keeps_phone_cards() -> None:
    store = PromptStore(clock=lambda: 1)
    _store_approval(store)
    _store_clarify(store, request_id="clarify-id-12345678")
    store.set_desktop_held(IID, USER, PROFILE)
    listed = prompts.list_prompts(store, iid=IID, user_id=USER, profile=PROFILE, now=2_000)
    assert listed.body["desktop_held"] is True
    surfaces = [item["surface"] for item in listed.body["prompts"]]
    assert surfaces == ["phone_chat"]
    store.clear_desktop_held(IID, USER, PROFILE)
    listed = prompts.list_prompts(store, iid=IID, user_id=USER, profile=PROFILE, now=2_000)
    assert listed.body["desktop_held"] is False
    assert {item["surface"] for item in listed.body["prompts"]} == {"bot_chat", "phone_chat"}


def _frame(event: str, payload: dict[str, Any] | None = None) -> bytes:
    body = {"event": event, **(payload or {})}
    return f"event: {event}\ndata: {json.dumps(body)}\n\n".encode()


async def _chunks(*parts: bytes) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


@pytest.mark.asyncio
async def test_stream_stores_approval_and_does_not_store_clarify_or_execute_code() -> None:
    store = PromptStore(clock=lambda: 1)
    bind = StreamBind(
        store=store, iid=IID, user_id=USER, profile=PROFILE, now=lambda: 5_000, timeout_s=300
    )
    seen = asyncio.Event()

    async def parts() -> AsyncIterator[bytes]:
        yield _frame("run.started", {"run_id": RUN})
        yield _frame("message.started", {})
        yield _frame(
            "approval.request",
            {
                "run_id": RUN,
                "request_id": REQ,
                "command": SECRET_COMMAND,
                "description": "flagged",
                "choices": ["once", "deny"],
            },
        )
        assert store.get((IID, USER, PROFILE, REQ)) is not None
        seen.set()
        yield _frame("tool.completed", {"tool_name": "execute_code"})
        yield _frame("clarify.requested", {"clarify_id": "c", "question": "huh"})
        yield _frame("assistant.completed", {"content": "done", "session_id": "tip"})
        yield _frame("run.completed", {"session_id": "tip"})
        assert store.get((IID, USER, PROFILE, REQ)).status == "expired"
        yield _frame("done", {})

    result = await ds.consume_sse(parts(), bind=bind)
    assert seen.is_set()
    assert result.status == 200
    assert result.body is not None
    assert result.body["message"]["content"] == "done"  # type: ignore[index]
    row = store.get((IID, USER, PROFILE, REQ))
    assert row is not None and row.kind == "approval" and row.choices == ("once", "deny")
    assert row.command == SECRET_COMMAND and row.run_id == RUN
    assert store.desktop_held(IID, USER, PROFILE) is False
    assert store.list_visible(IID, USER, PROFILE) == ()


@pytest.mark.asyncio
async def test_mailbox_keepalive_sets_desktop_held_until_done() -> None:
    store = PromptStore(clock=lambda: 1)
    bind = StreamBind(
        store=store, iid=IID, user_id=USER, profile=PROFILE, now=lambda: 5_000, timeout_s=300
    )
    held = asyncio.Event()

    async def parts() -> AsyncIterator[bytes]:
        yield _frame("run.started", {})
        yield b": keepalive\n\n"
        assert store.desktop_held(IID, USER, PROFILE) is True
        held.set()
        yield _frame("run.queued", {"status": "queued"})
        yield _frame("done", {})

    result = await ds.consume_sse(parts(), bind=bind)
    assert held.is_set()
    assert result.status == 202
    assert store.desktop_held(IID, USER, PROFILE) is False
    assert store.list_visible(IID, USER, PROFILE) == ()


@pytest.mark.asyncio
async def test_json_completion_is_not_a_sync_fallback() -> None:
    async def parts() -> AsyncIterator[bytes]:
        yield b'{"message":{"role":"assistant","content":"sync"}}'

    result = await ds.consume_sse(parts(), bind=None)
    assert result.status == 502
    assert result.body is None


@pytest.mark.asyncio
async def test_stream_dying_before_done_is_an_error() -> None:
    async def parts() -> AsyncIterator[bytes]:
        yield _frame("run.started", {})
        yield _frame("message.started", {})

    with pytest.raises(Exception, match="terminal"):
        await ds.consume_sse(parts(), bind=None)


@pytest.mark.asyncio
async def test_unqualified_build_does_not_call_loopback(tmp_path: Path) -> None:
    from hmp_plugin.store import Store

    calls: list[str] = []

    async def loopback(*_a: Any) -> ds.LoopbackResult:
        calls.append("loopback")
        return ds.LoopbackResult(status=200, body=None, effective_session_id=None)

    class Bridge:
        def direct_send_endpoint(self, _profile: str) -> DirectSendEndpoint:
            calls.append("endpoint")
            return DirectSendEndpoint(host="127.0.0.1", port=9, api_key="k" * 20, path_prefix="")

        def resolve_bot_chat(self, _profile: str) -> None:
            return None

    sqlite = Store(tmp_path / "h.sqlite3")
    sqlite.migrate()
    deps = DirectSendDeps(
        bridge=Bridge(),  # type: ignore[arg-type]
        store=sqlite,
        locks=ProfileLocks(),
        now=lambda: 1,
        loopback_call=loopback,
        qualified=lambda: False,
    )
    from hmp_plugin.contract import DirectSendRequest, WriteGate, WriteGateState
    from hmp_plugin.direct_send import DirectSendError, handle_direct_send

    with pytest.raises(DirectSendError) as caught:
        await handle_direct_send(
            deps,
            iid=IID,
            user_id=USER,
            profile=PROFILE,
            request=DirectSendRequest(client_message_id="c1", expected_head=0, text="hi"),
            flag_enabled=True,
            base_write_gate=WriteGate(state=WriteGateState.CLOSED, reason="write_gate_closed"),
        )
    assert caught.value.failure.code is ErrorCode.WRITE_GATE_CLOSED
    assert calls == []


def test_shipped_fingerprint_is_not_qualified() -> None:
    from hmp_plugin.compat import direct_send_build_qualified

    assert direct_send_build_qualified() is False


@pytest.mark.asyncio
async def test_phone_replay_conflict_and_pending_approval_suppression() -> None:
    store = PromptStore(clock=lambda: 1)
    delivered: list[str] = []

    class Sqlite:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}

        def reserve_phone_cmid(self, iid, user_id, profile, cmid, payload_hash, now):
            key = (iid, user_id, profile, cmid)
            if key in self.rows:
                return self.rows[key], False
            row = {
                "payload_hash": payload_hash,
                "status": "pending",
                "result_json": None,
            }
            self.rows[key] = row
            return row, True

        def finalize_phone_cmid(
            self, iid, user_id, profile, cmid, *, status, result_json, updated_at
        ):
            del updated_at
            row = self.rows[(iid, user_id, profile, cmid)]
            row["status"] = status
            row["result_json"] = result_json

    sqlite = Sqlite()
    approvals = ["pending"]

    delivery_status: bool | None = True

    async def deliver() -> bool | None:
        delivered.append("yes")
        return delivery_status

    def pending(key: str) -> list[dict[str, str]]:
        del key
        return [{"request_id": "x"}] if approvals else []

    common = {
        "prompts": store,
        "sqlite_store": sqlite,
        "iid": IID,
        "user_id": USER,
        "profile": PROFILE,
        "chat_id": "c_chat",
        "now": 10,
        "resolver": FakeResolver(),
        "session_key": lambda: "namespace:hmp:dm:phone-session-key",
        "pending_approvals": pending,
        "deliver": deliver,
    }
    refused = await prompts.handle_phone_send(cmid="cmid-1", text="hello", **common)
    assert refused.status == 409 and refused.body["applied"] is False
    assert delivered == []
    approvals.clear()
    sent = await prompts.handle_phone_send(cmid="cmid-2", text="hello", **common)
    assert sent.status == 202 and sent.body == {"state": "submitted"}
    assert delivered == ["yes"]
    assert len(store.observations(IID, USER, PROFILE)) == 1
    replay = await prompts.handle_phone_send(cmid="cmid-2", text="hello", **common)
    assert replay.body == sent.body
    assert delivered == ["yes"]
    conflict = await prompts.handle_phone_send(cmid="cmid-2", text="other", **common)
    assert conflict.status == 409
    assert conflict.body["error"]["code"] == "idempotency_conflict"
    assert delivered == ["yes"]
    delivery_status = None
    uncertain = await prompts.handle_phone_send(cmid="cmid-3", text="hello", **common)
    assert uncertain.status == 200 and uncertain.body == {"state": "unknown"}
    assert sqlite.rows[(IID, USER, PROFILE, "cmid-3")]["status"] == "unknown"
    assert len(store.observations(IID, USER, PROFILE)) == 1
    replay = await prompts.handle_phone_send(cmid="cmid-3", text="hello", **common)
    assert replay.body == uncertain.body and delivered == ["yes", "yes"]
    delivery_status = False
    rejected = await prompts.handle_phone_send(cmid="cmid-4", text="hello", **common)
    assert rejected.status == 503
    assert len(store.observations(IID, USER, PROFILE)) == 1


@pytest.mark.asyncio
async def test_phone_message_while_clarify_is_pending_is_not_a_new_turn() -> None:
    store = PromptStore(clock=lambda: 1)
    _store_clarify(store)
    delivered: list[str] = []

    class Sqlite:
        def reserve_phone_cmid(self, iid, user_id, profile, cmid, payload_hash, now):
            del iid, user_id, profile, cmid, now
            return {"payload_hash": payload_hash, "status": "pending", "result_json": None}, True

        def finalize_phone_cmid(self, *args, **kwargs):
            del args, kwargs

    async def deliver() -> bool:
        delivered.append("nope")
        return True

    result = await prompts.handle_phone_send(
        prompts=store,
        sqlite_store=Sqlite(),
        iid=IID,
        user_id=USER,
        profile=PROFILE,
        chat_id="c_chat",
        cmid="cmid-3",
        text="Ship it (Recommended)",
        now=10,
        resolver=FakeResolver(),
        session_key=lambda: "namespace:hmp:dm:phone",
        pending_approvals=lambda _key: [],
        deliver=deliver,
    )
    assert result.status == 409 and result.body["applied"] is False
    assert delivered == []


@pytest.mark.asyncio
async def test_binder_requires_exactly_one_match_and_text_fallback_is_not_a_card() -> None:
    store = PromptStore(clock=lambda: 1)
    session = "namespace:hmp:dm:phone"
    store.remember_session(session, IID, USER, PROFILE, "c_chat")

    class Bridge:
        def __init__(self, rows: list[dict[str, str]]) -> None:
            self.rows = rows

        def list_gateway_approvals(self, _key: str) -> list[dict[str, str]]:
            return self.rows

        def approval_timeout_s(self, profile: str) -> int:
            return 300

    class Prompt:
        session_key = session
        command = "echo hi"
        description = "why"
        choices = ("once", "deny")

    hooks = AdapterHooks(
        store=store, bridge=Bridge([]), now=lambda: 9, iid=IID, approval_qualified=lambda: True
    )
    assert await hooks.on_exec_approval(Prompt()) is False
    hooks.bridge = Bridge(  # type: ignore[assignment]
        [
            {"command": "echo hi", "request_id": REQ},
            {"command": "echo hi", "request_id": REQ + "b"},
        ]
    )
    assert await hooks.on_exec_approval(Prompt()) is True
    assert all(row.choices == ("deny",) for row in store._rows.values())
    store = PromptStore(clock=lambda: 1)
    store.remember_session(session, IID, USER, PROFILE, "c_chat")
    hooks.store = store
    hooks.bridge = Bridge([{"command": "echo hi", "request_id": REQ}])  # type: ignore[assignment]
    assert await hooks.on_exec_approval(Prompt()) is True
    assert store.get((IID, USER, PROFILE, REQ)).surface == "phone_chat"  # type: ignore[union-attr]
    assert hooks.on_send("c_chat", "please /approve", None, {"is_approval_prompt": True}) is True
    assert len(store.list_visible(IID, USER, PROFILE)) == 1


def test_inert_reply_is_not_stored() -> None:
    store = PromptStore(clock=lambda: 1)
    store.remember_session("k", IID, USER, PROFILE, "c_chat")
    hooks = AdapterHooks(store=store, bridge=object(), now=lambda: 1, iid=IID)
    hooks.note_inert("c_chat")
    assert hooks.on_send("c_chat", "pairing code ABCD", "hmp:auth:abc", None) is False
    assert store.observations(IID, USER, PROFILE) == ()
    hooks.store.release_transcript("c_chat")
    assert hooks.on_send("c_chat", "hello back", None, None) is True


def _arm(env: Env, *, flag: bool) -> None:
    env.bridge.authz_state = lambda *_a, **_k: AuthzState.AUTHORIZED  # type: ignore[method-assign]
    env.ctx.direct_send_flag = lambda: flag
    # Test-only premise: these fixtures exercise F3 behavior on an approval-qualified build. The
    # shipped production default is closed (see test_approval_route_qualification.py).
    env.ctx.approval_qualified = lambda: True
    env.ctx.prompt_store = PromptStore(clock=lambda: 1)
    env.bridge.direct_send_endpoint = lambda *_a, **_k: DirectSendEndpoint(  # type: ignore[method-assign]
        host="127.0.0.1", port=9, api_key="k" * 20, path_prefix=""
    )
    env.ctx.direct_send_deps = DirectSendDeps(
        bridge=env.bridge,  # type: ignore[arg-type]
        store=env.store,
        locks=ProfileLocks(),
        now=lambda: env.clock.now,
    )


def test_prompt_routes_are_closed_when_the_flag_is_off(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _arm(env, flag=False)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, body = await get(client, "/bots/b/prompts", headers=env.headers(dev))
        assert status == 503 and body["error"]["code"] == "write_gate_closed"
        status, body = await post(
            client,
            "/bots/b/prompts/" + REQ,
            {"choice": "once"},
            headers=env.headers(dev),
        )
        assert status == 503 and body["error"]["code"] == "write_gate_closed"
        status, body = await post(
            client,
            "/bots/b/phone/messages",
            {"client_message_id": "c1", "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 503 and body["error"]["code"] == "write_gate_closed"
        assert "direct_send_endpoint" not in env.bridge.calls

    run(env, scenario)


def test_empty_prompt_list_and_unknown_answer(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, body = await get(client, "/bots/b/prompts", headers=env.headers(dev))
        assert status == 200 and body == {"prompts": [], "desktop_held": False}
        status, body = await post(
            client,
            "/bots/b/prompts/not-a-stored-id",
            {"choice": "once", "session_key": "nope"},
            headers=env.headers(dev),
        )
        assert status == 404 and body["error"]["code"] == "not_found"

    run(env, scenario)
