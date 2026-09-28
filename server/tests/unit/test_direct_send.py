"""Direct send orchestration (HMP_V1.md §7a DS-2..DS-8, amendment F2; review round 2 redesign).

Fakes `contract.ReadBridge` and injects a fake loopback call, exactly like `reads.py`'s own tests
inject a fake bridge -- never a real Hermes internal, never a real network call.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

import aiohttp
import pytest

from hmp_plugin import direct_send as ds
from hmp_plugin.contract import (
    BotChatTarget,
    ConversationRef,
    DirectSendEndpoint,
    DirectSendRequest,
    ResetReason,
    Row,
    WriteGate,
    WriteGateState,
)
from hmp_plugin.store import Store

CLOSED = WriteGate(state=WriteGateState.CLOSED, reason="guarantees_unavailable")
AN_ENDPOINT = DirectSendEndpoint(host="127.0.0.1", port=8642, api_key="k" * 20, path_prefix="")


_NO_LEASE_GIVEN: list = []


def _default_after_rows(request_text: str, reply_text: str, sent_at: int) -> list[Row]:
    """The clean, no-interleave shape: our own user row immediately after `expected_head`, then
    our own assistant reply, nothing else -- what a normal turn's post-hoc read looks like."""
    return [
        Row(id=101, role="user", text=request_text, client_message_id=None, created_at=sent_at),
        Row(id=102, role="assistant", text=reply_text, client_message_id=None, created_at=sent_at),
    ]


class FakeBridge:
    def __init__(
        self,
        *,
        bot_chat: BotChatTarget | None,
        lease: list | None = _NO_LEASE_GIVEN,
        after_rows: list[Row] | ResetReason | Exception | None = "auto",
    ) -> None:
        self._bot_chat = bot_chat
        self._lease: list | None = [] if lease is _NO_LEASE_GIVEN else lease
        self.endpoint = AN_ENDPOINT
        self._after_rows = after_rows  # "auto" builds a clean pair lazily, from the actual call

    def resolve_bot_chat(self, profile: str) -> BotChatTarget | None:
        return self._bot_chat

    def lease_snapshot(self, profile: str) -> list | None:
        return self._lease

    def direct_send_endpoint(self, profile: str) -> DirectSendEndpoint | None:
        return self.endpoint

    def after(self, ref: ConversationRef, after_id: int, limit: int):
        if self._after_rows == "auto":
            raise AssertionError("test must set after_rows explicitly for any call reaching DS-7a")
        if isinstance(self._after_rows, Exception):
            raise self._after_rows
        return self._after_rows


def make_target(head: int = 5) -> BotChatTarget:
    return BotChatTarget(
        root_session_id="root1",
        live_tip_session_id="tip1",
        head_message_id=head,
        compression_chain=("root1", "tip1"),
    )


async def ok_loopback(endpoint, session_id, text) -> ds.LoopbackResult:
    return ds.LoopbackResult(
        status=200,
        body={"message": {"id": 42, "role": "assistant", "content": "hi"}},
        effective_session_id=session_id,
    )


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "hmp.sqlite3")
    s.migrate()
    return s


def make_deps(store: Store, bridge: FakeBridge, *, loopback=ok_loopback, now: int = 1000):
    return ds.DirectSendDeps(
        bridge=bridge, store=store, locks=ds.ProfileLocks(), now=lambda: now, loopback_call=loopback
    )


def clean_bridge(head: int = 5, *, request_text: str = "hi", reply_text: str = "hi") -> FakeBridge:
    """A bridge whose DS-7a post-hoc read always reports a clean (non-interleaved) turn."""
    return FakeBridge(
        bot_chat=make_target(head=head),
        after_rows=[
            Row(
                id=head + 1,
                role="user",
                text=request_text,
                client_message_id=None,
                created_at=1000,
            ),
            Row(
                id=head + 2,
                role="assistant",
                text=reply_text,
                client_message_id=None,
                created_at=1000,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_missing_expected_head_is_bad_request(store: Store) -> None:
    bridge = clean_bridge()
    req = DirectSendRequest(client_message_id="c1", expected_head=None, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "bad_request"


@pytest.mark.asyncio
async def test_flag_disabled_closes_the_gate_without_a_bridge_call(store: Store) -> None:
    calls: list[str] = []

    class RecordingBridge(FakeBridge):
        def direct_send_endpoint(self, profile: str):
            calls.append("endpoint")
            return super().direct_send_endpoint(profile)

        def resolve_bot_chat(self, profile: str):
            calls.append("bot_chat")
            return super().resolve_bot_chat(profile)

    bridge = RecordingBridge(bot_chat=make_target())
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=False,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "write_gate_closed"
    assert calls == []  # ERR-2a discipline: no bridge call when the route is gated off


OPEN = WriteGate(state=WriteGateState.OPEN, reason=None)


@pytest.mark.asyncio
async def test_genuinely_open_gate_still_resolves_and_uses_the_endpoint(store: Store) -> None:
    """Found only by running the new fixture-gateway suite against the `experimental` build,
    whose own capability map genuinely satisfies GU-4's OPEN floor: HMP_V1.md's own text describes
    a native Hermes admission path for this case that does not exist in this codebase (FR-053).
    The loopback mechanism is the only one implemented -- a genuinely OPEN gate must still resolve
    and use it (never silently skip straight to `api_server_unavailable` with no attempt at all),
    and the flag being off must not matter when the base gate is already OPEN."""
    bridge = clean_bridge(head=5)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=False,
        base_write_gate=OPEN,
    )
    assert outcome.state == "accepted"


@pytest.mark.asyncio
async def test_genuinely_open_gate_with_no_resolvable_endpoint_fails_closed(store: Store) -> None:
    class NoEndpointBridge(FakeBridge):
        def direct_send_endpoint(self, profile: str):
            return None

    bridge = NoEndpointBridge(bot_chat=make_target())
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=False,
            base_write_gate=OPEN,
        )
    assert excinfo.value.failure.code.value == "api_server_unavailable"
    assert excinfo.value.failure.retryable is True


@pytest.mark.asyncio
async def test_happy_path_accepts_and_returns_the_synchronous_reply(store: Store) -> None:
    bridge = clean_bridge(head=5, request_text="hello")
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hello")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "accepted"
    assert outcome.message_id == 42
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_idempotent_replay_never_calls_the_loopback_twice(store: Store) -> None:
    bridge = clean_bridge(head=5, request_text="hello")
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hello")
    deps = make_deps(store, bridge)
    first = await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )

    calls = {"n": 0}

    async def counting(endpoint, session_id, text):
        calls["n"] += 1
        return await ok_loopback(endpoint, session_id, text)

    deps2 = make_deps(store, bridge, loopback=counting, now=1001)
    second = await ds.handle_direct_send(
        deps2,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert second == first
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_retry_while_still_pending_awaits_the_same_task_never_the_network_again(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review round 2, BLOCKER #1: a retry with the same cmid while the row is still `pending`
    (this call did not create the reservation) must never call the loopback a second time -- it
    reuses whatever task is already tracked for that cmid."""
    monkeypatch.setattr(ds, "ADMISSION_WAIT_S", 0.05)  # keep the retry's own bounded wait short
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    async def slow(endpoint, session_id, text):
        calls["n"] += 1
        started.set()
        await release.wait()
        return await ok_loopback(endpoint, session_id, text)

    bridge = clean_bridge(head=5, request_text="hello")
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hello")
    deps = make_deps(store, bridge, loopback=slow)

    # BLOCKER #1's own point: the caller's OWN wait is bounded and gives up long before the
    # background task does. A short bound here just keeps this test fast -- it does not change
    # what is being verified (the background task itself is never cancelled by that timeout).
    first_outcome = await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert first_outcome.state == "submitted"  # gave up waiting; the task keeps running
    assert calls["n"] == 1

    # A retry while the row is still `pending` and this process still tracks the running task:
    # never calls the network again, and (bounded the same way) also reports `submitted`.
    second_outcome = await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert calls["n"] == 1  # the retry never called the network itself
    assert second_outcome.state == "submitted"

    key = ("i1", "u1", "default", "c1")
    background_task = deps.tasks.get(key)
    assert background_task is not None  # BLOCKER #1: still tracked, still running

    release.set()
    background_outcome = await background_task
    assert background_outcome.state == "accepted"
    assert calls["n"] == 1  # still just the one real call, ever

    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None and record["status"] == "accepted"  # finalized after the fact


@pytest.mark.asyncio
async def test_same_cmid_different_payload_is_a_conflict(store: Store) -> None:
    bridge = clean_bridge(head=5)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hello")
    deps = make_deps(store, bridge)
    await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    req2 = DirectSendRequest(client_message_id="c1", expected_head=5, text="different text")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            deps,
            iid="i1",
            user_id="u1",
            profile="default",
            request=req2,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "idempotency_conflict"
    assert excinfo.value.failure.retryable is False


@pytest.mark.asyncio
async def test_no_bot_chat_is_definitive(store: Store) -> None:
    bridge = FakeBridge(bot_chat=None)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "no_bot_chat"
    assert excinfo.value.failure.retryable is False


@pytest.mark.asyncio
async def test_session_busy_on_live_tip_lease(store: Store) -> None:
    bridge = FakeBridge(bot_chat=make_target(head=5), lease=[{"session_id": "tip1"}])
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"
    assert excinfo.value.failure.retryable is True


@pytest.mark.asyncio
async def test_session_busy_on_pre_compression_chain_id(store: Store) -> None:
    """The review's own finding: a lease on a PRE-compression id (not the live tip) must still be
    caught, via the full compression-lineage check (DS-4(3))."""
    bridge = FakeBridge(bot_chat=make_target(head=5), lease=[{"session_id": "root1"}])
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"


@pytest.mark.asyncio
async def test_lease_snapshot_failure_fails_closed(store: Store) -> None:
    """Ownership uncertainty fails CLOSED -- `None` from the bridge is never "not busy"."""
    bridge = FakeBridge(bot_chat=make_target(head=5), lease=None)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"


@pytest.mark.asyncio
async def test_session_busy_releases_the_reservation_for_a_clean_retry(store: Store) -> None:
    busy_bridge = FakeBridge(bot_chat=make_target(head=5), lease=[{"session_id": "tip1"}])
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError):
        await ds.handle_direct_send(
            make_deps(store, busy_bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    clear_bridge = clean_bridge(head=5)
    outcome = await ds.handle_direct_send(
        make_deps(store, clear_bridge, now=1001),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "accepted"


@pytest.mark.asyncio
async def test_stale_head_is_definitive_and_refuses_before_any_loopback_call(store: Store) -> None:
    calls = {"n": 0}

    async def counting(endpoint, session_id, text):
        calls["n"] += 1
        return await ok_loopback(endpoint, session_id, text)

    bridge = FakeBridge(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=1, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge, loopback=counting),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "stale_head"
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_401_from_loopback_call_is_treated_as_gate_closed_and_closes_the_row(
    store: Store,
) -> None:
    """Review round 2, BLOCKER #1: a 401 is a definitive HTTP response -- it must close the row,
    never leave it dangling `pending`."""

    async def unauthorized(endpoint, session_id, text):
        return ds.LoopbackResult(status=401, body=None, effective_session_id=None)

    bridge = FakeBridge(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge, loopback=unauthorized),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "write_gate_closed"
    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None
    assert record["status"] == "rejected"  # closed, not left pending


@pytest.mark.asyncio
async def test_other_definitive_http_error_closes_the_row_as_rejected(store: Store) -> None:
    """Review round 2, BLOCKER #1: ANY non-200/202 HTTP response from `api_server` closes the row
    -- Hermes did answer, it just refused."""

    async def server_error(endpoint, session_id, text):
        return ds.LoopbackResult(status=500, body=None, effective_session_id=None)

    bridge = FakeBridge(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge, loopback=server_error),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "api_server_unavailable"
    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None
    assert record["status"] == "rejected"


@pytest.mark.asyncio
async def test_mailbox_queued_outcome_is_reported_as_queued(store: Store) -> None:
    async def queued(endpoint, session_id, text):
        return ds.LoopbackResult(status=202, body={"state": "queued"}, effective_session_id=None)

    bridge = FakeBridge(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge, loopback=queued),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "queued"
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_connection_error_finalizes_unknown_and_is_not_resent(store: Store) -> None:
    """Review round 3: a connect failure stores `unknown` (never left `pending`). A later POST
    of the same cmid reports that state and does not call the network again."""

    async def broken(endpoint, session_id, text):
        raise aiohttp.ClientConnectionError("boom")

    calls = {"n": 0}

    async def counting(endpoint, session_id, text):
        calls["n"] += 1
        return await ok_loopback(endpoint, session_id, text)

    bridge = FakeBridge(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge, loopback=broken),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "api_server_unavailable"
    assert excinfo.value.failure.retryable is True
    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None
    assert record["status"] == "unknown"

    outcome = await ds.handle_direct_send(
        make_deps(store, bridge, loopback=counting, now=1001),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "unknown"
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_interleave_true_positive_another_user_row_before_our_reply(store: Store) -> None:
    """Review round 2, BLOCKER #4: identity check, not a row-count heuristic. A second, distinct
    user row landing between `expected_head` and our own reply is the true interleave case."""
    bridge = FakeBridge(
        bot_chat=make_target(head=5),
        after_rows=[
            Row(id=6, role="user", text="hi", client_message_id=None, created_at=1000),
            Row(
                id=7,
                role="user",
                text="a foreign message",
                client_message_id=None,
                created_at=1000,
            ),
            Row(id=8, role="assistant", text="hi", client_message_id=None, created_at=1000),
        ],
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "accepted"
    assert outcome.interleave_detected is True


@pytest.mark.asyncio
async def test_ordinary_reply_never_false_flags_as_interleaved(store: Store) -> None:
    """The review's own explicit ask: a normal turn (no other writer) must never trip
    `interleave_detected`, even with tool rows of our own turn in between."""
    bridge = FakeBridge(
        bot_chat=make_target(head=5),
        after_rows=[
            Row(id=6, role="user", text="hi", client_message_id=None, created_at=1000),
            Row(id=7, role="tool", text="tool output", client_message_id=None, created_at=1000),
            Row(id=8, role="assistant", text="hi", client_message_id=None, created_at=1000),
        ],
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_interleave_never_flags_a_later_unrelated_turn(store: Store) -> None:
    """Rows appended only AFTER our own reply -- a later, separate conversation turn -- must never
    be mistaken for an interleave of THIS send."""
    bridge = FakeBridge(
        bot_chat=make_target(head=5),
        after_rows=[
            Row(id=6, role="user", text="hi", client_message_id=None, created_at=1000),
            Row(id=7, role="assistant", text="hi", client_message_id=None, created_at=1000),
            Row(
                id=8,
                role="user",
                text="a later, separate message",
                client_message_id=None,
                created_at=1050,
            ),
            Row(
                id=9,
                role="assistant",
                text="a later reply",
                client_message_id=None,
                created_at=1050,
            ),
        ],
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_reset_reason_alone_is_unverified_not_an_interleave(
    store: Store, caplog: pytest.LogCaptureFixture
) -> None:
    """Review round 3: HISTORY_REWRITTEN (or any ResetReason) does not by itself set
    `interleave_detected`. When the post-compaction re-read is also a reset, the result is
    unverified: the flag stays false and a log code is emitted."""
    bridge = FakeBridge(bot_chat=make_target(head=5), after_rows=ResetReason.CURSOR_NOT_RESOLVABLE)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with caplog.at_level(logging.INFO, logger="hmp_plugin"):
        outcome = await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert outcome.interleave_detected is False
    assert "outcome=interleave_unverified" in caplog.text


@pytest.mark.asyncio
async def test_interleave_fails_safe_when_our_own_reply_never_appears(store: Store) -> None:
    bridge = FakeBridge(
        bot_chat=make_target(head=5),
        after_rows=[Row(id=6, role="user", text="hi", client_message_id=None, created_at=1000)],
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.interleave_detected is True


@pytest.mark.asyncio
async def test_lock_contention_bound_gives_session_busy_not_an_indefinite_wait(
    store: Store,
) -> None:
    """Review round 2, BLOCKER #1: the DS-4(1) lock is bounded (`LOCK_WAIT_S`) -- a second send
    queued behind a stuck first turn gets `session_busy`, never an unbounded wait."""
    release = asyncio.Event()
    started = asyncio.Event()

    async def stuck(endpoint, session_id, text):
        started.set()
        await release.wait()
        return await ok_loopback(endpoint, session_id, text)

    bridge = clean_bridge(head=5)
    locks = ds.ProfileLocks()
    req1 = DirectSendRequest(client_message_id="c1", expected_head=5, text="first")
    deps1 = ds.DirectSendDeps(
        bridge=bridge, store=store, locks=locks, now=lambda: 1000, loopback_call=stuck
    )
    first_task = asyncio.ensure_future(
        ds.handle_direct_send(
            deps1,
            iid="i1",
            user_id="u1",
            profile="default",
            request=req1,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    )
    await started.wait()

    req2 = DirectSendRequest(client_message_id="c2", expected_head=5, text="second")
    deps2 = ds.DirectSendDeps(
        bridge=bridge, store=store, locks=locks, now=lambda: 1001, loopback_call=ok_loopback
    )
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            deps2,
            iid="i1",
            user_id="u1",
            profile="default",
            request=req2,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"
    assert excinfo.value.failure.retryable is True

    release.set()
    first_outcome = await first_task
    assert first_outcome.state == "accepted"


@pytest.mark.asyncio
async def test_expected_head_is_read_fresh_inside_the_lock(store: Store) -> None:
    """Review round 2, BLOCKER #1: `expected_head` must be compared against a head value taken
    INSIDE the serialization lock, not a pre-lock snapshot -- otherwise two concurrent in-process
    sends could both pass the precondition against the same stale head."""

    class ChangesUnderLock(FakeBridge):
        def __init__(self) -> None:
            super().__init__(bot_chat=make_target(head=5))
            self._resolved = 0

        def resolve_bot_chat(self, profile: str):
            self._resolved += 1
            # First call: resolving the lock key, before the lock is held -- still head 5.
            # Every call after that (inside the lock, and the post-hoc check) sees the head that
            # ALREADY advanced -- simulating another in-process attempt having just committed.
            return make_target(head=5 if self._resolved <= 1 else 9)

    bridge = ChangesUnderLock()
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "stale_head"


class _CompactingBridge(FakeBridge):
    """`after` reports a reset for the pre-compaction cursor and the rewritten transcript for a
    re-read from the start (`after_id == 0`)."""

    def __init__(self, rewritten: list[Row] | ResetReason) -> None:
        super().__init__(bot_chat=make_target(head=5), after_rows=rewritten)
        self._rewritten = rewritten

    def after(self, ref: ConversationRef, after_id: int, limit: int):
        if after_id > 0:
            return ResetReason.HISTORY_REWRITTEN
        if isinstance(self._rewritten, ResetReason):
            return self._rewritten
        return [row for row in self._rewritten if row.id > after_id][:limit]


@pytest.mark.asyncio
async def test_inplace_compaction_reread_does_not_flag_a_clean_turn(store: Store) -> None:
    """Review round 3: an in-place compaction (`HISTORY_REWRITTEN`) is re-read on the
    post-compaction transcript. A clean user+reply there is not an interleave."""
    bridge = _CompactingBridge(
        [
            Row(id=1, role="user", text="earlier", client_message_id=None, created_at=100),
            Row(id=2, role="user", text="hi", client_message_id=None, created_at=1000),
            Row(id=3, role="tool", text="tool", client_message_id=None, created_at=1000),
            Row(id=4, role="assistant", text="hi", client_message_id=None, created_at=1000),
        ]
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "accepted"
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_inplace_compaction_reread_still_flags_a_foreign_user_row(store: Store) -> None:
    bridge = _CompactingBridge(
        [
            Row(id=2, role="user", text="hi", client_message_id=None, created_at=1000),
            Row(id=3, role="user", text="someone else", client_message_id=None, created_at=1000),
            Row(id=4, role="assistant", text="hi", client_message_id=None, created_at=1000),
        ]
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.interleave_detected is True


@pytest.mark.asyncio
async def test_reply_past_the_first_page_is_not_an_interleave(store: Store) -> None:
    """Review round 3: the 64-row window pages until our reply is found. A long tool turn is
    not an interleave."""
    rows = [Row(id=6, role="user", text="hi", client_message_id=None, created_at=1000)]
    rows.extend(
        Row(id=7 + i, role="tool", text=f"t{i}", client_message_id=None, created_at=1000)
        for i in range(70)
    )
    rows.append(Row(id=80, role="assistant", text="hi", client_message_id=None, created_at=1000))

    class Paged(FakeBridge):
        def after(self, ref: ConversationRef, after_id: int, limit: int):
            return [row for row in rows if row.id > after_id][:limit]

    bridge = Paged(bot_chat=make_target(head=5))
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.interleave_detected is False


@pytest.mark.asyncio
async def test_exception_before_finalize_stores_unknown(store: Store) -> None:
    async def boom(endpoint, session_id, text):
        raise RuntimeError("boom")

    bridge = clean_bridge()
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(RuntimeError):
        await ds.handle_direct_send(
            make_deps(store, bridge, loopback=boom),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None and record["status"] == "unknown"


@pytest.mark.asyncio
async def test_cancel_before_finalize_stores_unknown(store: Store) -> None:
    started = asyncio.Event()

    async def stuck(endpoint, session_id, text):
        started.set()
        await asyncio.Event().wait()
        return await ok_loopback(endpoint, session_id, text)

    bridge = clean_bridge()
    deps = make_deps(store, bridge, loopback=stuck)
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    task = asyncio.create_task(
        ds.handle_direct_send(
            deps,
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    )
    await started.wait()
    background = deps.tasks.get(("i1", "u1", "default", "c1"))
    assert background is not None
    background.cancel()  # type: ignore[attr-defined]
    with pytest.raises(asyncio.CancelledError):
        await task
    record = store.get_cmid_record("i1", "u1", "default", "c1")
    assert record is not None and record["status"] == "unknown"


@pytest.mark.asyncio
async def test_pending_row_with_no_live_task_reports_unknown(store: Store) -> None:
    """Review round 3: a POST for a row with no live task reports the same state DS-8 does
    (`unknown`), never `submitted`, and does not call Hermes."""
    payload = ds._payload_hash("hi", 5)
    store.reserve_cmid("i1", "u1", "default", "c1", payload, 1000)
    calls = {"n": 0}

    async def counting(endpoint, session_id, text):
        calls["n"] += 1
        return await ok_loopback(endpoint, session_id, text)

    bridge = clean_bridge()
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge, loopback=counting),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "unknown"
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_uncertain_lineage_is_session_busy_and_releases_the_row(store: Store) -> None:
    class Uncertain(FakeBridge):
        def resolve_bot_chat(self, profile: str):
            raise RuntimeError("compression lineage uncertain")

    bridge = Uncertain(bot_chat=make_target())
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"
    assert store.get_cmid_record("i1", "u1", "default", "c1") is None


@pytest.mark.asyncio
async def test_profile_lock_is_keyed_by_the_lineage_root(store: Store) -> None:
    seen: list[str] = []

    class RecordingLocks(ds.ProfileLocks):
        def get(self, profile: str, lineage_root_id: str) -> object:
            seen.append(lineage_root_id)
            return super().get(profile, lineage_root_id)

    bridge = clean_bridge()
    locks = RecordingLocks()
    deps = ds.DirectSendDeps(
        bridge=bridge, store=store, locks=locks, now=lambda: 1000, loopback_call=ok_loopback
    )
    req = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome.state == "accepted"
    # make_target's chain is ("root1", "tip1"). The lock key is the root, not the tip.
    assert seen
    assert set(seen) == {"root1"}


def test_profile_lock_is_not_evicted_while_handed_out() -> None:
    """Review round 3: `get` returns the lock before `acquire`. Over the cap, that object must
    not be replaced by a second Lock for the same key."""
    locks = ds.ProfileLocks(max_entries=1)
    first = locks.get("p", "root-a")
    locks.get("p", "root-b")  # over the cap; root-a is handed out, not yet acquired
    assert locks.get("p", "root-a") is first


def test_profile_lock_is_not_evicted_while_it_has_waiters() -> None:
    locks = ds.ProfileLocks(max_entries=1)
    first = locks.get("p", "root-a")
    locks.release_ref("p", "root-a")  # refcount zero, but a waiter is still queued
    first._waiters = [object()]  # type: ignore[attr-defined]
    locks.get("p", "root-b")
    assert locks.get("p", "root-a") is first


@pytest.mark.asyncio
async def test_profile_lock_is_not_evicted_while_held() -> None:
    locks = ds.ProfileLocks(max_entries=1)
    first = locks.get("p", "root-a")
    await first.acquire()  # type: ignore[attr-defined]
    locks.release_ref("p", "root-a")  # handed back, but still locked
    locks.get("p", "root-b")
    assert locks.get("p", "root-a") is first
    first.release()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cancel_and_wait_is_bounded() -> None:
    """A task whose cancellation handler keeps running does not extend the wait."""
    tasks = ds.PendingSendTasks()
    started = asyncio.Event()

    async def slow_cleanup() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await asyncio.sleep(30)

    task = asyncio.create_task(slow_cleanup())
    await started.wait()
    tasks.put(("i", "u", "p", "c"), task)
    await tasks.cancel_and_wait(0.05)
    assert not task.done()
    task.cancel()
    await asyncio.wait([task], timeout=1)


@pytest.mark.asyncio
async def test_server_stop_cancels_pending_send_tasks() -> None:
    from hmp_plugin.server import SHUTDOWN_TIMEOUT_S, HmpServer, ListenerSettings

    tasks = ds.PendingSendTasks()
    seen: dict[str, float] = {}
    original = tasks.cancel_and_wait

    async def spy(bound_s: float) -> None:
        seen["timeout"] = bound_s
        await original(bound_s)

    tasks.cancel_and_wait = spy  # type: ignore[method-assign]
    started = asyncio.Event()

    async def hang() -> None:
        started.set()
        await asyncio.Event().wait()

    background = asyncio.create_task(hang())
    await started.wait()
    tasks.put(("i", "u", "p", "c"), background)
    ctx = SimpleNamespace(direct_send_deps=SimpleNamespace(tasks=tasks))
    srv = HmpServer(ctx, ListenerSettings("127.0.0.1", 0))  # type: ignore[arg-type]
    await srv.stop(notify=False)
    assert background.cancelled()
    assert seen["timeout"] == SHUTDOWN_TIMEOUT_S


@pytest.mark.asyncio
async def test_loopback_call_pins_the_connector_and_keeps_trust_env_off() -> None:
    """Review round 3: the aiohttp request is the verification. The connector resolves only the
    literal loopback address, `trust_env` stays false, and a connect failure surfaces to the
    caller (mapped to `api_server_unavailable` by `_execute`)."""
    seen: dict[str, object] = {}

    class Capture(aiohttp.ClientSession):
        def __init__(self, *args, **kwargs) -> None:
            seen["trust_env"] = kwargs.get("trust_env")
            seen["timeout"] = kwargs.get("timeout")
            seen["connector"] = kwargs.get("connector")
            super().__init__(*args, **kwargs)

        def post(self, url, *args, **kwargs):  # type: ignore[override]
            seen["url"] = url

            class _Resp:
                async def __aenter__(self):
                    connector = seen["connector"]
                    resolver = connector._resolver  # type: ignore[attr-defined]
                    seen["resolved"] = await resolver.resolve("not-a-loopback.example", 9)
                    raise aiohttp.ClientConnectionError("refused")

                async def __aexit__(self, *exc):
                    return False

            return _Resp()

    original = aiohttp.ClientSession
    ds.aiohttp.ClientSession = Capture  # type: ignore[misc]
    try:
        endpoint = DirectSendEndpoint(host="127.0.0.1", port=9, api_key="k" * 20, path_prefix="")
        with pytest.raises(aiohttp.ClientConnectionError):
            await ds.aiohttp_loopback_call(endpoint, "tip1", "hi")
    finally:
        ds.aiohttp.ClientSession = original  # type: ignore[misc]
    assert seen["trust_env"] is False
    timeout = seen["timeout"]
    assert isinstance(timeout, aiohttp.ClientTimeout)
    assert timeout.connect == ds.LOOPBACK_CONNECT_TIMEOUT_S
    assert ds.LOOPBACK_CONNECT_TIMEOUT_S <= 1.0
    resolved = seen["resolved"]
    assert isinstance(resolved, list) and resolved[0]["host"] == "127.0.0.1"
    assert str(seen["url"]).startswith("http://127.0.0.1:9/")
    assert str(seen["url"]).endswith("/api/sessions/tip1/chat/stream")


_LIVE_OWNER_META = {"bot_live_delivery_consumer": True, "live_session_id": "desk-live-1"}


@pytest.mark.asyncio
async def test_desktop_live_mailbox_owner_on_the_tip_is_not_busy(store: Store) -> None:
    """OD-F14: Desktop holding the canonical Bot Chat live is the mailbox owner Hermes hands the
    turn to, not a competing writer -- the send proceeds."""
    bridge = FakeBridge(
        bot_chat=make_target(head=5),
        lease=[{"session_id": "tip1", "metadata": dict(_LIVE_OWNER_META)}],
    )
    req = DirectSendRequest(client_message_id="c-live", expected_head=5, text="hi")
    outcome = await ds.handle_direct_send(
        make_deps(store, bridge),
        iid="i1",
        user_id="u1",
        profile="default",
        request=req,
        flag_enabled=True,
        base_write_gate=CLOSED,
    )
    assert outcome is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entry",
    [
        {"session_id": "root1", "metadata": dict(_LIVE_OWNER_META)},  # owner lease on a non-tip id
        {"session_id": "tip1", "metadata": {"bot_live_delivery_consumer": False}},
        {"session_id": "tip1", "metadata": {"bot_live_delivery_consumer": True}},  # no live id
        {"session_id": "tip1"},  # an ordinary lease (CLI/TUI prompt)
    ],
)
async def test_other_leases_on_the_lineage_stay_busy(store: Store, entry: dict) -> None:
    bridge = FakeBridge(bot_chat=make_target(head=5), lease=[entry])
    req = DirectSendRequest(client_message_id="c-busy", expected_head=5, text="hi")
    with pytest.raises(ds.DirectSendError) as excinfo:
        await ds.handle_direct_send(
            make_deps(store, bridge),
            iid="i1",
            user_id="u1",
            profile="default",
            request=req,
            flag_enabled=True,
            base_write_gate=CLOSED,
        )
    assert excinfo.value.failure.code.value == "session_busy"
