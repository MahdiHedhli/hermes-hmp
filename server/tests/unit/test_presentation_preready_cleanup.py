"""Original pre-READY task/cursor cleanup on synthetic sockets; no child or GO.

Parent policy thread is real; native authority, peer and clock premises are
mocked. A decoded terminal remains unaccepted data, never release permission.
"""
import asyncio
import os
import socket
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

import pytest
import pytest_asyncio

from hmp_plugin.presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    OriginalHeaders,
    ParentAuthorityAdapter,
)
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_service import SocketChannel, _PreResultCursor
from hmp_plugin.presentation_cancel_budget import CancellationBudget
from hmp_plugin.presentation_cleanup_reader import CleanupReadGate
from hmp_plugin.presentation_clock import NativeClockOwner
from hmp_plugin.presentation_jobs import CapturedLease, FrameError
from hmp_plugin.presentation_readiness import SelectorReadiness
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner
from hmp_plugin.presentation_terminal_claim import CleanupStamp, encode_handoff

from .test_presentation_broker_service import binding as fresh_binding
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_remote import adopt, prepare, read_selected
from .test_presentation_remote import prepared_v2 as prepared_v2
from .test_presentation_selected_protocol import v2gateway as v2gateway
from .test_presentation_supervisor import Native, Request
from .test_presentation_supervisor import context as context
from .test_presentation_terminal_claim import claim as claim

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def unknown_reader_v2(context, local, monkeypatch):
    """Synthetic raw-socket disposal after an UNKNOWN read claim, never a close fact."""
    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    peer, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    peer.setblocking(False)
    selected = replace(enrollment, gateway_pid=os.getpid(), service_pid=os.getpid() + 1,
                       protocol_version=2)
    channel = SocketChannel(sock, selected, role="gateway", endpoint=spine._endpoint,
                            observation=spine._observation)
    original_clock = channel._clock_owner_snapshot
    try:
        row = await prepare(context, (channel, peer, spine))
        yield row
    finally:
        context[2].release.set()
        remote = channel._remote_owner_snapshot
        if remote is not None:
            owner = remote._cleanup_owner_snapshot
            if owner is not None and owner._initialized:
                RemoteCleanupOwner.request(owner)
                for allocation in owner._allocations_snapshot:
                    original_task = allocation.task
                    with suppress(asyncio.CancelledError, AuthorityRefusalError):
                        await asyncio.wait_for(asyncio.shield(original_task), 1)
                    assert original_task.done()
        # The fixture owns these synthetic resources. Raw disposal after task
        # observation does not set channel/cleanup closure facts or native credit.
        sock.close()
        peer.close()
        NativeClockOwner.close_local(original_clock)
        assert await spine.stop_local_sockets()


@pytest_asyncio.fixture
async def two_admitted_v2(context, local, monkeypatch):
    """Two real parent-policy admissions; synthetic native authority/peer/clock."""
    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    beta_home = Path(context[2].home).parent / "beta"
    beta_home.mkdir(mode=0o700)
    config = beta_home / "profile.yaml"
    config.write_text("display_name: Synthetic Beta\n")
    config.chmod(0o600)
    beta_native = Native(beta_home)
    beta_authority = ParentAuthorityAdapter("a" * 52, service=beta_native)
    beta_operation = beta_authority.reserve(
        CapturedLease("a" * 52, "second-device", "user", "family", "beta", "b" * 64,
                      "second-binding", 1),
        "METADATA", OriginalHeaders.from_request(Request()),
        listener=object(), fence=ListenerFence(1), store=object(), bridge=object(),
        identity=object(), native_owner=object(),
    )
    contexts = (context, (beta_authority, beta_operation, beta_native))
    held, rows = [], []
    try:
        # Acquire all socket resources before either policy read, avoiding
        # directory-entry churn during either admitted policy snapshot.
        for serial in (1, 2):
            sock = client()
            peer, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
            peer.setblocking(False)
            binding = fresh_binding(serial)
            selected = replace(enrollment, scope=binding, gateway_pid=os.getpid(),
                               service_pid=os.getpid() + 1, protocol_version=2)
            channel = SocketChannel(sock, selected, role="gateway", endpoint=spine._endpoint,
                                    observation=spine._observation)
            held.append((sock, peer, channel, channel._clock_owner_snapshot, binding))
        for ctx, (_, peer, channel, _, binding) in zip(contexts, held, strict=True):
            row = await prepare(ctx, (channel, peer, spine))
            rows.append((*row[:-1], binding))
        yield tuple(rows)
    finally:
        for ctx in contexts:
            ctx[2].release.set()
        for sock, peer, channel, clock, _ in held:
            remote = channel._remote_owner_snapshot
            if remote is not None:
                owner = remote._cleanup_owner_snapshot
                if owner is not None and owner._initialized:
                    RemoteCleanupOwner.request(owner)
                    for allocation in owner._allocations_snapshot:
                        task = allocation.task
                        with suppress(asyncio.CancelledError, AuthorityRefusalError):
                            await asyncio.wait_for(asyncio.shield(task), 1)
                        assert task.done()
            sock.close()
            peer.close()
            NativeClockOwner.close_local(clock)
        assert await spine.stop_local_sockets()


async def cursor_waiting(cursor, count):
    for _ in range(100):
        waiter = cursor._waiter
        if (cursor._received == count and waiter is not None
                and waiter._attempted is True and waiter._retired is False):
            return
        await asyncio.sleep(0.001)
    pytest.fail("synthetic original pre-result cursor did not reach its wait")


async def cancel_written(owner):
    for _ in range(100):
        if owner._cancel_write_completed is True:
            return
        await asyncio.sleep(0)
    pytest.fail("synthetic CANCEL bytes arrived without original completed-write fact")


@pytest.mark.parametrize("phase,path", [
    ("none", "direct"), ("none", "ready"), ("prefix", "ready"),
    ("header", "ready"), ("ready_wait", "ready"),
])
@pytest.mark.parametrize("ending", ["eof", "terminal"])
async def test_original_preready_cursor_drains_under_one_frozen_cancel(
    prepared_v2, claim, phase, path, ending
):
    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    first = await read_selected(peer, binding)
    assert first.header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    original_work = owner._allocations_snapshot[1]
    cursor = channel._pre_result_cursor_origin
    ready = encode_frame(binding, "READY", 0, version=2)
    count = {"none": 0, "prefix": 3, "header": 12, "ready_wait": len(ready)}[phase]
    if count:
        await asyncio.get_running_loop().sock_sendall(peer, ready[:count])
    if phase == "ready_wait":
        assert await public is True
        assert not channel._reading and not original_work.task.done()
    else:
        await cursor_waiting(cursor, count)
    assert owner._write_fact_snapshot is None  # healthy pre-READY must not quiesce writes
    RemoteCleanupOwner.request(owner)
    end = CancellationBudget.inspect(owner._refs_snapshot[8])[2]
    cancel = await read_selected(peer, binding)
    assert cancel.header.kind == "CANCEL" and cancel.header.sequence == 1
    await cancel_written(owner)
    gate = owner._read_gate_snapshot
    assert gate._requested and gate._activated
    assert gate._fact_origin.work is original_work
    assert gate._fact_origin.request.reader is cursor
    assert gate._fact_origin.mode == ("ready_wait" if phase == "ready_wait" else "ready")
    assert original_work.task is owner._allocations_snapshot[1].task
    assert channel._go_write_intent is None and not owner._go_attempted
    tail = ready[count:] if path == "ready" and phase != "ready_wait" else b""
    if ending == "terminal":
        body = encode_handoff(claim, CleanupStamp(1, 250_000_001))
        sequence = 1 if path == "ready" else 0
        tail += encode_frame(binding, "TERMINAL", sequence, body, version=2)
    if tail:
        await asyncio.get_running_loop().sock_sendall(peer, tail)
    if ending == "eof":
        peer.shutdown(socket.SHUT_WR)
    cleanup = owner._allocations_snapshot[0].task
    result = await asyncio.wait_for(asyncio.shield(cleanup), 1)
    assert original_work.task.done() and owner._work_joined
    assert CancellationBudget.inspect(owner._refs_snapshot[8])[2] == end
    assert channel._go_write_intent is None and not owner._go_attempted
    assert authority._record(operation).headers is not None
    if ending == "terminal":
        assert result is False and owner._unknown and gate._terminal_data is not None
        assert not owner._socket_closed and not owner._clock_closed
    else:
        assert result is True and gate._eof
        assert owner._socket_closed and owner._clock_closed
    if phase != "ready_wait":
        try:
            value = await public
        except AuthorityRefusalError:
            value = False
        assert value is False


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("bad", ["terminal_sequence", "result", "go", "ready_sequence",
                                "duplicate_ready"])
async def test_invalid_cleanup_frame_never_scans_to_a_later_valid_terminal(
    prepared_v2, claim, ready_wait, bad
):
    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    cursor = channel._pre_result_cursor_origin
    ready = encode_frame(binding, "READY", 0, version=2)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(peer, ready)
        assert await public is True
    else:
        await cursor_waiting(cursor, 0)
    RemoteCleanupOwner.request(owner)
    assert (await read_selected(peer, binding)).header.kind == "CANCEL"
    await cancel_written(owner)
    gate = owner._read_gate_snapshot
    assert gate._activated and gate._fact_origin.request.reader is cursor
    body = encode_handoff(claim, CleanupStamp(1, 250_000_001))
    sequence = 1 if ready_wait or bad == "duplicate_ready" else 0
    good = encode_frame(binding, "TERMINAL", sequence, body, version=2)
    if bad == "terminal_sequence":
        invalid = encode_frame(binding, "TERMINAL", 0 if ready_wait else 1, body, version=2)
    elif bad == "result":
        invalid = encode_frame(binding, "RESULT", 1, b"SYNTHETIC_RESULT", version=2)
    elif bad == "go":
        invalid = encode_frame(binding, "GO", 1, version=2)
    elif bad == "ready_sequence":
        invalid = encode_frame(binding, "READY", 1, version=2)
    else:
        invalid = ready + ready
    await asyncio.get_running_loop().sock_sendall(peer, invalid + good)
    result = await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    if not ready_wait:
        try:
            value = await public
        except AuthorityRefusalError:
            value = False
        assert value is False
    assert result is False and owner._unknown and gate._failed
    assert gate._terminal_data is None and gate._done
    assert owner._allocations_snapshot[1].task.done()
    # The original task actually stopped. Invalid mode metadata still prevents
    # the cleanup ledger from certifying its join; preserve that UNKNOWN debt.
    assert owner._work_joined is (bad not in ("result", "go"))
    assert channel._go_write_intent is None and not owner._go_attempted
    assert not owner._socket_closed and not owner._clock_closed
    assert authority._record(operation).headers is not None
    unread = socket.socket.recv(channel._socket_snapshot, len(invalid + good), socket.MSG_PEEK)
    assert unread.endswith(good)  # later valid frame is still queued, never scanned/adopted
    with pytest.raises(BlockingIOError):
        peer.recv(1)  # no ACK, retry or closure response


@pytest.mark.parametrize("field", ["_received", "_target", "_scope", "_buffer",
                                  "_go_write_intent"])
async def test_capture_rejects_changed_original_cursor_without_touching_foreign_state(
    prepared_v2, field
):
    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    gate = owner._read_gate_snapshot
    CleanupReadGate.capture(gate)
    assert gate._preflight_origin.reader is cursor
    assert not gate._requested and owner._write_fact_snapshot is None
    callbacks = []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign cursor state must not be inspected")

    target = channel if field == "_go_write_intent" else cursor
    original = getattr(target, field)
    foreign = bytearray(b"foreign buffer retained") if field == "_buffer" else Foreign()
    setattr(target, field, foreign)
    try:
        with pytest.raises(AuthorityRefusalError):
            CleanupReadGate.guard(gate)
        assert callbacks == []
        if field == "_buffer":
            assert foreign == bytearray(b"foreign buffer retained")
        assert not gate._activated and owner._write_fact_snapshot is None
        assert authority._record(operation).headers is not None
        with pytest.raises(BlockingIOError):
            peer.recv(1)
    finally:
        setattr(target, field, original)
    # A second capture is refused, rather than reinterpreting an earlier seal.
    with pytest.raises(AuthorityRefusalError):
        CleanupReadGate.capture(gate)
    RemoteCleanupOwner.request(owner)
    await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    with suppress(AuthorityRefusalError):
        assert await public is False


async def test_capture_and_switch_reject_foreign_owners_before_attribute_callbacks():
    callbacks = []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign owner callbacks must not run")

    gate = object.__new__(CleanupReadGate)
    gate._capture_attempted = False
    gate._owner_origin = gate._owner = Foreign()
    CleanupReadGate.capture(gate)
    assert gate._capture_attempted and gate._capture_failed
    assert gate._preflight_origin is None and callbacks == []
    cursor = object.__new__(_PreResultCursor)
    cursor._scope_origin = Foreign()
    with pytest.raises(FrameError, match="BI1_BROKER_SERVICE_REFUSED"):
        _PreResultCursor._switch_cleanup(cursor)
    assert callbacks == []


@pytest.mark.parametrize("drift", ["received", "buffer", "go_intent"])
async def test_first_request_reseals_after_native_sample_without_following_changed_state(
    prepared_v2, monkeypatch, drift
):
    from hmp_plugin import presentation_remote_cleanup as cleanup

    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    gate = owner._read_gate_snapshot
    original_sample = cleanup.NativeClockOwner.cleanup_sample
    foreign = bytearray(b"unrelated operation buffer")
    target, field = (channel, "_go_write_intent") if drift == "go_intent" else (
        cursor, "_buffer" if drift == "buffer" else "_received")
    before = getattr(target, field)
    sampled = []

    def sample(clock):
        now = original_sample(clock)
        if not sampled:
            assert gate._capture_attempted and gate._preflight_origin is not None
            assert not gate._requested and owner._intent
            sampled.append(True)
            setattr(target, field, foreign if drift == "buffer" else
                    object() if drift == "go_intent" else before + 1)
        return now

    monkeypatch.setattr(cleanup.NativeClockOwner, "cleanup_sample", sample)
    RemoteCleanupOwner.request(owner)
    assert sampled and owner._unknown
    assert not gate._requested and not gate._activated
    assert owner._write_fact_snapshot is None and not owner._cancel_write_attempted
    assert foreign == bytearray(b"unrelated operation buffer")
    # Fixture disposal restores local storage only after the production refusal.
    # UNKNOWN remains sticky; restoring bytes is not recovery or permission.
    setattr(target, field, before)
    result = await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert result is False and owner._unknown
    assert not owner._socket_closed and not owner._clock_closed
    assert authority._record(operation).headers is not None
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    with suppress(AuthorityRefusalError):
        assert await public is False


@pytest.mark.parametrize("ending", ["eof", "terminal"])
async def test_fully_buffered_ready_at_final_sample_transfers_original_bytes(
    prepared_v2, claim, monkeypatch, ending
):
    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    ready = encode_frame(binding, "READY", 0, version=2)
    original = SocketChannel._remaining
    captured = []

    def remaining(ch, end):
        value = original(ch, end)
        if (ch is channel and cursor._received == len(ready)
                and cursor._header is None and not captured):
            captured.append(bytes(cursor._buffer_origin))
            assert owner._write_fact_snapshot is None
            RemoteCleanupOwner.request(owner)
        return value

    monkeypatch.setattr(SocketChannel, "_remaining", remaining)
    await asyncio.get_running_loop().sock_sendall(peer, ready)
    cancel = await read_selected(peer, binding)
    assert captured == [ready] and cancel.header.kind == "CANCEL"
    await cancel_written(owner)
    gate = owner._read_gate_snapshot
    assert gate._request_origin.reader is cursor and gate._fact_origin.mode == "ready"
    assert gate._request_origin.state.received == len(ready)
    if ending == "terminal":
        body = encode_handoff(claim, CleanupStamp(1, 250_000_001))
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "TERMINAL", 1, body, version=2))
    else:
        peer.shutdown(socket.SHUT_WR)
    result = await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert result is (ending == "eof")
    assert owner._work_joined and owner._allocations_snapshot[1].task.done()
    assert not owner._go_attempted and channel._go_write_intent is None
    assert owner._socket_closed is (ending == "eof")
    assert owner._clock_closed is (ending == "eof")
    assert authority._record(operation).headers is not None
    with suppress(AuthorityRefusalError):
        assert await public is False


async def test_healthy_ready_go_has_no_premature_quiescence_or_cleanup_capture(prepared_v2):
    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    ready_notice, allow_go = asyncio.Event(), asyncio.Event()

    async def caller():
        assert await remote.begin_ready()
        ready_notice.set()
        await allow_go.wait()
        return await remote.go()

    public = asyncio.create_task(caller())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(binding, "READY", 0, version=2))
    await asyncio.wait_for(ready_notice.wait(), 1)
    owner = remote._cleanup_owner_snapshot
    original_work = owner._allocations_snapshot[1].task
    gate = owner._read_gate_snapshot
    assert owner._write_fact_snapshot is None and not gate._capture_attempted
    assert not original_work.done() and not owner._intent and not channel._reading
    allow_go.set()
    go = await read_selected(peer, binding)
    assert go.header.kind == "GO" and go.header.sequence == 1
    assert await asyncio.wait_for(public, 1)
    assert owner._allocations_snapshot[1].task is original_work and not original_work.done()
    assert owner._write_fact_snapshot is not None and not gate._capture_attempted
    assert authority._record(operation).headers is not None
    RemoteCleanupOwner.request(owner)
    cancel = await read_selected(peer, binding)
    assert cancel.header.kind == "CANCEL" and cancel.header.sequence == 2
    peer.shutdown(socket.SHUT_WR)
    assert await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert owner._work_joined and gate._eof


@pytest.mark.parametrize("ready_wait,field,value", [
    (True, "_unknown", True), (True, "_retired", False), (True, "_attempted", False),
    (False, "_unknown", True), (False, "_attempted", False), (False, "_retired", True),
])
async def test_ready_wait_reseals_retired_readiness_proof_after_native_sample(
    prepared_v2, monkeypatch, ready_wait, field, value
):
    from hmp_plugin import presentation_remote_cleanup as cleanup

    _, _, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "READY", 0, version=2))
        assert await public
    owner = remote._cleanup_owner_snapshot
    gate, waiter = owner._read_gate_snapshot, cursor._waiter
    assert waiter._retired is ready_wait and waiter._attempted and not waiter._unknown
    before = getattr(waiter, field)
    original = cleanup.NativeClockOwner.cleanup_sample
    changed = []

    def sample(clock):
        now = original(clock)
        if not changed:
            assert gate._preflight_origin.mode == ("ready_wait" if ready_wait else "ready")
            changed.append(True)
            setattr(waiter, field, value)
        return now

    monkeypatch.setattr(cleanup.NativeClockOwner, "cleanup_sample", sample)
    try:
        RemoteCleanupOwner.request(owner)
        assert changed and owner._unknown
        assert not gate._requested and not gate._activated
        assert owner._write_fact_snapshot is None and not owner._cancel_write_attempted
    finally:
        setattr(waiter, field, before)
    assert not await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert not owner._socket_closed and not owner._clock_closed
    if not ready_wait:
        with suppress(AuthorityRefusalError):
            assert await public is False


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("drift", ["owner_unknown", "budget_failed", "budget_shortened"])
async def test_final_selector_proof_cannot_publish_selection_after_scope_invalidation(
    prepared_v2, monkeypatch, ready_wait, drift
):
    from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationWindow

    _, _, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "READY", 0, version=2))
        assert await public
    owner = remote._cleanup_owner_snapshot
    gate, waiter = owner._read_gate_snapshot, cursor._waiter
    budget = owner._refs_snapshot[8]
    original, changed = SelectorReadiness._slots, []

    def slots(readiness):
        row = original(readiness)
        if readiness is waiter and owner._intent and not gate._requested and not changed:
            changed.append(True)
            if drift == "owner_unknown":
                owner._unknown = True
            elif drift == "budget_failed":
                CancellationBudget.refuse(budget)
            else:
                _, last, end, _ = CancellationBudget.inspect(budget)
                CancellationBudget.inherit(
                    budget, CancellationWindow(end - CLEANUP_NS - 1, end - 1), last)
        return row

    monkeypatch.setattr(SelectorReadiness, "_slots", slots)
    RemoteCleanupOwner.request(owner)
    assert changed and owner._unknown
    assert not gate._requested and not gate._activated and gate._fact_origin is None
    assert not owner._cancel_write_attempted
    assert not await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert not owner._socket_closed and not owner._clock_closed
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    if not ready_wait:
        with suppress(AuthorityRefusalError):
            assert await public is False


@pytest.mark.parametrize("request_go", [False, True])
async def test_queued_cause_dominates_ready_notification_and_following_public_go(
    prepared_v2, monkeypatch, request_go
):
    from hmp_plugin import presentation_broker_service as service

    authority, operation, _, channel, peer, _, _, binding = prepared_v2
    remote = adopt(prepared_v2)
    ready = encode_frame(binding, "READY", 0, version=2)
    queued = []

    async def caller():
        try:
            result = await remote.begin_ready()
            if request_go and result:
                return await remote.go()
            return result
        except AuthorityRefusalError:
            return False

    public = asyncio.create_task(caller())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    owner = remote._cleanup_owner_snapshot
    cursor = channel._pre_result_cursor_origin
    original_work = owner._allocations_snapshot[1].task
    await cursor_waiting(cursor, 0)
    original_recv = service._SOCKET_RECV

    def recv(sock, count):
        part = original_recv(sock, count)
        if (sock is channel._socket_snapshot and not queued
                and cursor._received + len(part) == len(ready)):
            queued.append(True)
            asyncio.get_running_loop().call_soon(RemoteCleanupOwner.request, owner)
        return part

    monkeypatch.setattr(service, "_SOCKET_RECV", recv)
    await asyncio.get_running_loop().sock_sendall(peer, ready)
    assert await asyncio.wait_for(public, 1) is False
    # The internal READY notification was minted, but its public return fence
    # observed the queued cause. It cannot be reused to admit public GO.
    assert queued and owner._barriers_snapshot.ready.result() is True
    assert owner._read_gate_snapshot._request_origin.mode == "ready_wait"
    assert not owner._go_attempted and channel._go_write_intent is None
    cancel = await read_selected(peer, binding)
    assert cancel.header.kind == "CANCEL" and cancel.header.sequence == 1
    peer.shutdown(socket.SHUT_WR)
    assert await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert original_work.done() and owner._work_joined
    assert authority._record(operation).headers is not None


@pytest.mark.parametrize("after_init", [False, True])
async def test_partial_cleanup_notice_initialization_retains_allocation_without_begin(
    prepared_v2, monkeypatch, after_init
):
    from hmp_plugin import presentation_cleanup_reader as cleanup

    authority, operation, native, channel, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    original, attempts = cleanup._initialize_future, []

    def initialize(future, loop):
        owner = remote._cleanup_owner_snapshot
        gate = owner._read_gate_snapshot
        assert gate is owner._read_gate and future is gate._notice_origin
        assert gate._notice_allocation == (gate, future, loop)
        assert not gate._notice_initialized and not gate._initialized
        assert all(slot.task is None for slot in owner._slots_snapshot)
        attempts.append(future)
        if after_init:
            original(future, loop)
        raise RuntimeError("synthetic cleanup-notice initialization ambiguity")

    monkeypatch.setattr(cleanup, "_initialize_future", initialize)
    before = dict(native.calls)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    gate = owner._read_gate_snapshot
    assert attempts == [gate._notice_origin]
    assert gate._notice is gate._notice_allocation[1] is gate._notice_origin
    assert not gate._initialized and not gate._notice_initialized
    assert owner._unknown and not owner._initialized
    assert all(slot.task is None for slot in owner._slots_snapshot)
    assert not gate._requested and not gate._activated and gate._fact_origin is None
    assert not remote._begin_attempted and native.calls == before
    assert not owner._socket_closed and not owner._clock_closed
    assert authority._record(operation).headers is not None
    assert channel._pre_result_cursor_origin is None
    with pytest.raises(BlockingIOError):
        peer.recv(1)


@pytest.mark.parametrize("after_init", [False, True])
async def test_partial_original_cursor_initialization_never_mints_read_fact_or_go(
    unknown_reader_v2, monkeypatch, after_init
):
    authority, operation, _, channel, peer, _, _, binding = unknown_reader_v2
    remote = adopt(unknown_reader_v2)
    original, attempts = _PreResultCursor.__init__, []

    def initialize(cursor, ch, end, expected, owner):
        assert ch is channel and ch._pre_result_cursor_origin is cursor
        assert ch._pre_result_cursor_snapshot is ch._pre_result_cursor is cursor
        attempts.append(cursor)
        if after_init:
            original(cursor, ch, end, expected, owner)
        raise RuntimeError("synthetic original cursor initialization ambiguity")

    monkeypatch.setattr(_PreResultCursor, "__init__", initialize)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    with suppress(AuthorityRefusalError):
        assert await asyncio.wait_for(public, 1) is False
    owner = remote._cleanup_owner_snapshot
    await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    cursor = channel._pre_result_cursor_origin
    assert attempts == [cursor]
    assert getattr(cursor, "_initialized", False) is after_init
    assert owner._read_gate_snapshot._capture_failed
    assert not owner._read_gate_snapshot._requested
    assert owner._read_gate_snapshot._fact_origin is None
    assert not owner._go_attempted and channel._go_write_intent is None
    assert owner._allocations_snapshot[1].task.done()
    assert authority._record(operation).headers is not None
    if not after_init:
        assert channel._reading and owner._unknown
        assert not owner._socket_closed and not owner._clock_closed
        assert not owner._cancel_write_attempted


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("drift", ["fact_mode", "fact_outer", "fact_work", "request_mode"])
async def test_cleanup_record_substitution_at_recv_cannot_follow_foreign_state(
    unknown_reader_v2, claim, monkeypatch, ready_wait, drift
):
    from hmp_plugin import presentation_cleanup_reader as cleanup

    authority, operation, _, channel, peer, _, _, binding = unknown_reader_v2
    remote = adopt(unknown_reader_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "READY", 0, version=2))
        assert await public
    owner = remote._cleanup_owner_snapshot
    RemoteCleanupOwner.request(owner)
    assert (await read_selected(peer, binding)).header.kind == "CANCEL"
    await cancel_written(owner)
    gate = owner._read_gate_snapshot
    original_outer = gate._fact_origin.outer
    foreign = bytearray(b"unrelated buffer must remain untouched")
    callbacks, changed = [], []

    class ForeignWork:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign work must not be inspected")

    original_recv = cleanup._RECV

    def recv(sock, count):
        part = original_recv(sock, count)
        if sock is channel._socket_snapshot and not changed:
            changed.append(True)
            fact = gate._fact_origin
            if drift == "request_mode":
                request = gate._request_origin._replace(mode="result")
                gate._request = gate._request_origin = request
                gate._preflight = gate._preflight_origin = request
            else:
                values = {"fact_mode": {"mode": "result"},
                          "fact_outer": {"outer": foreign},
                          "fact_work": {"work": ForeignWork()}}
                replacement = fact._replace(**values[drift])
                gate._fact = gate._fact_origin = replacement
        return part

    monkeypatch.setattr(cleanup, "_RECV", recv)
    body = encode_handoff(claim, CleanupStamp(1, 250_000_001))
    wire = encode_frame(binding, "TERMINAL", 1 if ready_wait else 0, body, version=2)
    await asyncio.get_running_loop().sock_sendall(peer, wire)
    result = await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert changed and result is False and owner._unknown
    assert gate._failed and gate._terminal_data is None
    assert owner._allocations_snapshot[1].task.done()
    assert not owner._socket_closed and not owner._clock_closed
    assert channel._go_write_intent is None and not owner._go_attempted
    assert original_outer == bytearray() and callbacks == []
    assert foreign == bytearray(b"unrelated buffer must remain untouched")
    assert authority._record(operation).headers is not None
    assert socket.socket.recv(channel._socket_snapshot, len(wire), socket.MSG_PEEK) == wire[8:]
    if not ready_wait:
        with suppress(AuthorityRefusalError):
            assert await public is False


@pytest.mark.parametrize("forged_switch", [False, True])
async def test_unqualified_switch_failure_wipes_only_original_partial_cursor(
    unknown_reader_v2, monkeypatch, forged_switch
):
    from hmp_plugin.presentation_cleanup_reader import CleanupReadSwitch

    authority, operation, _, channel, peer, _, _, binding = unknown_reader_v2
    remote = adopt(unknown_reader_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    original_outer = cursor._buffer_origin
    foreign = bytearray(b"foreign cursor must remain untouched")
    callbacks, injected = [], []

    class ForeignReader:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("forged switch must not inspect its reader")

    original_switch = CleanupReadGate.switch

    def switch(gate, reader):
        original_switch(gate, reader)
        if reader is cursor and cursor._received == 3 and not injected:
            injected.append(bytes(original_outer))
            cursor._buffer = cursor._buffer_origin = foreign
            if forged_switch:
                raise CleanupReadSwitch(ForeignReader())
            raise RuntimeError("synthetic generic cursor failure")

    monkeypatch.setattr(CleanupReadGate, "switch", switch)
    prefix = encode_frame(binding, "READY", 0, version=2)[:3]
    await asyncio.get_running_loop().sock_sendall(peer, prefix)
    with suppress(AuthorityRefusalError):
        assert await asyncio.wait_for(public, 1) is False
    owner = remote._cleanup_owner_snapshot
    await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert injected == [prefix] and original_outer == bytearray()
    assert foreign == bytearray(b"foreign cursor must remain untouched") and callbacks == []
    assert not cursor._cleanup_switched and owner._read_gate_snapshot._fact_origin is None
    assert not owner._go_attempted and channel._go_write_intent is None
    assert owner._allocations_snapshot[1].task.done()
    assert authority._record(operation).headers is not None


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("borrow", ["cursor_scope", "budget"])
async def test_cancel_cannot_borrow_another_admitted_operations_cursor_or_budget(
    two_admitted_v2, monkeypatch, ready_wait, borrow
):
    from hmp_plugin import presentation_remote_cleanup as cleanup

    first, second = two_admitted_v2
    remote_a, remote_b = adopt(first), adopt(second)
    public_a = asyncio.create_task(remote_a.begin_ready())
    public_b = asyncio.create_task(remote_b.begin_ready())
    assert (await read_selected(first[4], first[7])).header.kind == "BEGIN"
    assert (await read_selected(second[4], second[7])).header.kind == "BEGIN"
    cursor_a = first[3]._pre_result_cursor_origin
    cursor_b = second[3]._pre_result_cursor_origin
    await cursor_waiting(cursor_a, 0)
    await cursor_waiting(cursor_b, 0)
    ready_a = encode_frame(first[7], "READY", 0, version=2)
    ready_b = encode_frame(second[7], "READY", 0, version=2)
    await asyncio.get_running_loop().sock_sendall(second[4], ready_b[:3])
    await cursor_waiting(cursor_b, 3)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(first[4], ready_a)
        assert await public_a
    owner_a, owner_b = remote_a._cleanup_owner_snapshot, remote_b._cleanup_owner_snapshot
    gate_a = owner_a._read_gate_snapshot
    budget_b = owner_b._refs_snapshot[8]
    before_budget = CancellationBudget.inspect(budget_b)
    before_buffer = bytes(cursor_b._buffer_origin)
    before_calls = dict(second[2].calls)
    before_work = owner_b._allocations_snapshot[1].task
    before_headers = second[0]._record(second[1]).headers
    original_sample, changed = cleanup.NativeClockOwner.cleanup_sample, []

    def sample(clock):
        now = original_sample(clock)
        if clock is owner_a._refs_snapshot[4] and not changed:
            changed.append(True)
            if borrow == "cursor_scope":
                request = gate_a._preflight_origin._replace(
                    reader=cursor_b, cursor=cursor_b, scope=cursor_b._scope_origin,
                    channel=second[3], outer=cursor_b._buffer_origin)
                gate_a._preflight = gate_a._preflight_origin = request
            else:
                refs = list(gate_a._refs)
                refs[8] = budget_b
                gate_a._refs = tuple(refs)
        return now

    monkeypatch.setattr(cleanup.NativeClockOwner, "cleanup_sample", sample)
    RemoteCleanupOwner.request(owner_a)
    assert changed and owner_a._unknown and not gate_a._requested
    assert not await asyncio.wait_for(asyncio.shield(owner_a._allocations_snapshot[0].task), 1)
    if not ready_wait:
        with suppress(AuthorityRefusalError):
            assert await public_a is False
    assert CancellationBudget.inspect(budget_b) == before_budget
    assert bytes(cursor_b._buffer_origin) == before_buffer
    assert second[2].calls == before_calls
    assert owner_b._allocations_snapshot[1].task is before_work
    assert not before_work.done() and before_work.cancelling() == 0
    assert not owner_b._intent and not owner_b._read_gate_snapshot._capture_attempted
    assert second[0]._record(second[1]).headers is before_headers
    assert not owner_a._socket_closed and not owner_a._clock_closed
    assert not owner_a._go_attempted and not owner_b._go_attempted
    # The second independently admitted operation remains operational after the
    # first refuses: complete its original partial READY on its original socket.
    await asyncio.get_running_loop().sock_sendall(second[4], ready_b[3:])
    assert await asyncio.wait_for(public_b, 1)
    assert not owner_b._intent and owner_b._ready_fact is not None
    RemoteCleanupOwner.request(owner_b)
    assert (await read_selected(second[4], second[7])).header.kind == "CANCEL"
    second[4].shutdown(socket.SHUT_WR)
    assert await asyncio.wait_for(asyncio.shield(owner_b._allocations_snapshot[0].task), 1)
    assert second[0]._record(second[1]).headers is before_headers


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("fault", [None, "before_signal", "after_signal"])
async def test_original_caller_shortens_armed_cleanup_wait_without_new_allowance(
    unknown_reader_v2, monkeypatch, ready_wait, fault
):
    from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationWindow

    authority, operation, _, channel, peer, _, _, binding = unknown_reader_v2
    remote = adopt(unknown_reader_v2)
    ready_notice, shorten, changed, finish = (asyncio.Event() for _ in range(4))
    observed = []
    original_signal = CleanupReadGate._signal_change

    def signal(gate, future):
        if fault == "before_signal":
            raise RuntimeError("synthetic before-change-signal failure")
        original_signal(gate, future)
        if fault == "after_signal":
            raise RuntimeError("synthetic after-change-signal failure")

    monkeypatch.setattr(CleanupReadGate, "_signal_change", signal)

    async def caller():
        result = False
        with suppress(AuthorityRefusalError):
            result = await remote.begin_ready()
        ready_notice.set()
        await shorten.wait()
        owner = remote._cleanup_owner_snapshot
        budget = owner._refs_snapshot[8]
        end = CancellationBudget.inspect(budget)[2]
        window = CancellationWindow(end - CLEANUP_NS - 30_000_000, end - 30_000_000)
        try:
            CleanupReadGate.inherit(owner._read_gate_snapshot, window)
            observed.append(("inherited", window.end_ns))
        except RuntimeError:
            observed.append(("refused", window.end_ns))
        finally:
            changed.set()
        await finish.wait()
        return result

    public = asyncio.create_task(caller())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "READY", 0, version=2))
        await asyncio.wait_for(ready_notice.wait(), 1)
    owner = remote._cleanup_owner_snapshot
    RemoteCleanupOwner.request(owner)
    assert (await read_selected(peer, binding)).header.kind == "CANCEL"
    gate = owner._read_gate_snapshot
    for _ in range(100):
        if (gate._change_active and gate._waiter is not None
                and gate._waiter._attempted and not gate._waiter._retired):
            break
        await asyncio.sleep(0.001)
    else:
        pytest.fail("original cleanup reader did not arm its bounded change wait")
    original_waiter = gate._waiter
    old_end = CancellationBudget.inspect(owner._refs_snapshot[8])[2]
    shorten.set()
    await asyncio.wait_for(changed.wait(), 1)
    peer.shutdown(socket.SHUT_WR)
    result = await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    finish.set()
    assert await asyncio.wait_for(public, 1) is ready_wait
    assert observed == [("inherited" if fault is None else "refused", old_end - 30_000_000)]
    assert gate._generation == 1 and original_waiter._retired
    assert authority._record(operation).headers is not None
    assert not owner._go_attempted and channel._go_write_intent is None
    if fault is None:
        assert result and gate._eof and owner._work_joined
        assert owner._socket_closed and owner._clock_closed
        assert CancellationBudget.inspect(owner._refs_snapshot[8])[2] == old_end - 30_000_000
    else:
        assert not result and owner._unknown and gate._failed
        assert not owner._socket_closed and not owner._clock_closed
        assert CancellationBudget.inspect(owner._refs_snapshot[8])[3]


@pytest.mark.parametrize("ready_wait", [False, True])
@pytest.mark.parametrize("after_init", [False, True])
async def test_partial_cleanup_change_future_never_registers_a_new_reader_or_closes(
    unknown_reader_v2, monkeypatch, ready_wait, after_init
):
    from hmp_plugin import presentation_cleanup_reader as cleanup

    authority, operation, _, channel, peer, _, _, binding = unknown_reader_v2
    remote = adopt(unknown_reader_v2)
    public = asyncio.create_task(remote.begin_ready())
    assert (await read_selected(peer, binding)).header.kind == "BEGIN"
    cursor = channel._pre_result_cursor_origin
    await cursor_waiting(cursor, 0)
    if ready_wait:
        await asyncio.get_running_loop().sock_sendall(
            peer, encode_frame(binding, "READY", 0, version=2))
        assert await public
    owner = remote._cleanup_owner_snapshot
    gate = owner._read_gate_snapshot
    original, attempts = cleanup._initialize_future, []

    def initialize(future, loop):
        assert gate._change_active and gate._change_origin.future is future
        assert gate._change_allocation == (gate, gate._fact_origin, gate._change_origin)
        assert not gate._change_initialized and gate._waiter is None
        attempts.append(future)
        if after_init:
            original(future, loop)
        raise RuntimeError("synthetic cleanup-change initialization ambiguity")

    monkeypatch.setattr(cleanup, "_initialize_future", initialize)
    RemoteCleanupOwner.request(owner)
    assert not await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    if not ready_wait:
        with suppress(AuthorityRefusalError):
            assert await public is False
    assert attempts == [gate._change_origin.future]
    assert not gate._change_initialized and gate._change_active
    assert gate._waiter is None and gate._generation == 0
    assert gate._failed and owner._unknown and owner._allocations_snapshot[1].task.done()
    assert not owner._socket_closed and not owner._clock_closed
    assert not owner._cancel_write_attempted and not owner._go_attempted
    assert authority._record(operation).headers is not None
    with pytest.raises(BlockingIOError):
        peer.recv(1)
