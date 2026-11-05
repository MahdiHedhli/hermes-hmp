"""Shared native/job admission and remote BEGIN/READY; synthetic authority only.

Parent policy/thread work and Unix sockets are real. Kernel peer identity is
explicitly mocked by the local gateway fixture. No child, GO or result dispatch.
"""
import asyncio
import os
import time
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_remote as remote_module
from hmp_plugin.presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    OriginalHeaders,
    ParentAuthorityAdapter,
)
from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader, encode_frame
from hmp_plugin.presentation_broker_service import TerminalStatusExchange
from hmp_plugin.presentation_cancel_budget import CancellationBudget
from hmp_plugin.presentation_input_v3 import decode_input_v3
from hmp_plugin.presentation_jobs import FrameError, RemotePhase, State
from hmp_plugin.presentation_policy_binding import NativePolicyWork
from hmp_plugin.presentation_remote import RemoteOperationOwner
from hmp_plugin.presentation_supervisor import ReaderSupervisor

from .test_presentation_broker_service import binding, read_frame
from .test_presentation_broker_service import local as local
from .test_presentation_supervisor import Native, Request
from .test_presentation_supervisor import context as context
from .test_presentation_terminal_status import gateway as gateway


@pytest_asyncio.fixture
async def prepared(context, gateway):
    authority, operation, native = context
    channel, peer, _ = gateway
    assert await authority.initialize(operation)
    authority.start(operation)
    work = NativePolicyWork(authority, operation)
    work.start()
    for _ in range(256):
        if work.poll_join():
            break
        await asyncio.sleep(0.005)
    else:
        pytest.fail("synthetic parent policy did not join within setup budget")
    assert await work.postcheck()
    packet = work.worker_input(source_manifest_sha="b" * 64,
                              canonical_fallback="Synthetic", observed_at=0)
    b = binding()
    yield authority, operation, native, channel, peer, work, packet, b
    native.release.set()


def adopt(prepared):
    authority, operation, _, channel, _, _, packet, b = prepared
    return authority.bind_remote(operation, channel, b, packet)


async def ready_exchange(prepared, remote):
    _, _, _, _, peer, _, packet, b = prepared
    running = asyncio.create_task(remote.begin_ready())
    frame = await read_frame(peer, b)
    assert frame.header.kind == "BEGIN" and frame.body == packet
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0))
    assert await running


@pytest.mark.asyncio
async def test_native_policy_and_shared_slot_join_one_begin_ready_without_credentials(prepared):
    a, op, native, _, _, work, packet, _ = prepared
    remote = adopt(prepared)
    record = a._record(op)
    job = a.owner._resolve(record.handle)
    assert record.remote_operation is job.remote_slot.read() is remote
    assert record.remote_slot is job.remote_slot
    assert remote._cleanup_budget is record.cleanup_budget is record.cleanup_budget_snapshot
    assert CancellationBudget.inspect(record.cleanup_budget)[0] == int(record.deadline * 1e9)
    assert job.child is None and job.go_sent is False
    assert a.owner.inspect_remote(record.handle) is RemotePhase.BOUND
    assert work._thread.joined and work.resources_closed
    assert record.headers.authorization.encode() not in packet
    row = decode_input_v3(packet)
    assert row["home"] == native.home and row["challenge"] == job.challenge
    await ready_exchange(prepared, remote)
    assert native.calls == {"INITIAL": 1, "BEFORE": 1, "PRE_GO": 3}
    assert a.owner.inspect(record.handle) == (State.STARTING, False, False)
    assert a.owner.inspect_remote(record.handle) is RemotePhase.READY
    assert record.headers is not None and not await a.retire_known(op)
    assert not hasattr(remote, "go") and not hasattr(remote, "release")


@pytest.mark.asyncio
async def test_original_cleanup_cause_blocks_remote_work_without_releasing_native_debt(prepared):
    authority, operation, native, _, _, _, _, _ = prepared
    remote = adopt(prepared)
    record = authority._record(operation)
    budget = record.cleanup_budget
    window = CancellationBudget.local(budget, time.monotonic_ns())
    calls = dict(native.calls)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    assert native.calls == calls
    assert record.cleanup_budget is budget and remote._cleanup_budget is budget
    assert CancellationBudget.inspect(budget)[2] == window.end_ns
    assert authority.owner.inspect(record.handle)[2] is False
    assert record.headers is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["copy", "profile", "boot", "channel", "instance"])
async def test_constructor_refusal_retains_same_partial_owner_in_both_ledgers(prepared, bad):
    a, op, _, channel, _, work, packet, b = prepared
    if bad == "copy":
        packet = bytes(bytearray(packet))  # equal content cannot establish packet provenance
    elif bad == "profile":
        object.__setattr__(a._record(op).lease, "profile", "other")
    elif bad == "boot":
        b = replace(b, broker="f" * 64)
    elif bad == "channel":
        channel = object()
    else:
        b = replace(b, iid="b" * 51 + "a")
    with pytest.raises((AuthorityRefusalError, FrameError)):
        a.bind_remote(op, channel, b, packet)
    record = a._record(op)
    retained = record.remote_operation
    assert type(retained) is RemoteOperationOwner
    assert a.owner.remote_slot(record.handle).read() is retained
    assert record.headers is not None
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert retained._failed is True
    assert not a.refuse_policy_prelaunch(op) and not await a.retire_known(op)
    assert work.resources_closed  # policy closure cannot substitute for remote custody


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["process", "child", "supervisor", "prior_remote"])
async def test_mutually_exclusive_local_and_remote_adoption(prepared, guard):
    a, op, _, _, _, _, _, _ = prepared
    record = a._record(op)
    if guard == "process":
        record.process_owner = object()
    elif guard == "child":
        record.child = object()
    elif guard == "supervisor":
        record.reader_supervisor = object()
    else:
        first = adopt(prepared)
    with pytest.raises(AuthorityRefusalError):
        adopt(prepared)
    if guard == "prior_remote":
        assert record.remote_operation is first
        assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    else:
        assert record.remote_operation is None


@pytest.mark.asyncio
async def test_remote_slot_cannot_be_used_by_local_supervisor_or_child(prepared):
    a, op, _, _, _, _, _, _ = prepared
    remote = adopt(prepared)
    record = a._record(op)
    with pytest.raises(AuthorityRefusalError):
        ReaderSupervisor(a, op)
    with pytest.raises(AuthorityRefusalError):
        a.bind_child(op, object())
    assert record.remote_operation is remote and record.child is None
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["WAIT_OK", "GROUP_GONE", "SIGNAL_CLOSED", "RESULT_EOF"])
async def test_local_custody_events_never_complete_remote_credit(prepared, event):
    a, op, _, _, _, _, _, _ = prepared
    remote = adopt(prepared)
    record = a._record(op)
    a.owner.custody(record.handle, event, remote)
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert record.remote_operation is remote and record.child is None
    assert not await a.retire_known(op)


@pytest.mark.asyncio
async def test_cancel_ready_keeps_native_headers_and_remote_credit(prepared):
    a, op, _, _, _, _, _, _ = prepared
    remote = adopt(prepared)
    await ready_exchange(prepared, remote)
    record = a._record(op)
    a.cancel(op)
    assert a.owner.inspect(record.handle) == (State.DRAINING, False, False)
    assert a.owner.inspect_remote(record.handle) is RemotePhase.DRAINING
    assert not a.refuse_policy_prelaunch(op) and not await a.retire_known(op)
    assert record.headers is not None and record.remote_operation is remote
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["wrong_operation", "wrong_sequence", "CLOSED", "missing"])
async def test_lost_or_invalid_ready_is_unknown_and_never_replayed(prepared, reply):
    a, op, _, _, peer, _, _, b = prepared
    remote = adopt(prepared)
    running = asyncio.create_task(remote.begin_ready())
    await read_frame(peer, b)
    if reply == "missing":
        peer.close()
    else:
        scoped = replace(b, operation="e" * 64) if reply == "wrong_operation" else b
        kind = "CLOSED" if reply == "CLOSED" else "READY"
        seq = 1 if reply == "wrong_sequence" else 0
        await asyncio.get_running_loop().sock_sendall(peer, encode_frame(scoped, kind, seq))
    with pytest.raises(AuthorityRefusalError):
        await running
    record = a._record(op)
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert record.remote_operation is remote
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()


@pytest.mark.asyncio
async def test_partial_begin_write_is_recorded_once_and_retained(prepared, monkeypatch):
    a, op, _, channel, peer, _, _, _ = prepared
    calls = []
    async def partial(self, frame, end, *, owner=None):
        assert frame.header.kind == "BEGIN"
        calls.append(frame)
        await asyncio.get_running_loop().sock_sendall(self._socket, b"HBR1")
        raise BrokenPipeError("synthetic partial write outcome")
    monkeypatch.setattr(type(channel), "send", partial)
    remote = adopt(prepared)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    record = a._record(op)
    assert len(calls) == 1 and remote._begin_attempted
    assert await asyncio.get_running_loop().sock_recv(peer, 4) == b"HBR1"
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert a.owner.inspect_remote(record.handle) is RemotePhase.UNKNOWN


@pytest.mark.asyncio
@pytest.mark.parametrize("drift", ["epoch", "home", "slot", "packet", "lease", "store",
                                  "headers", "policy"])
async def test_stale_scope_after_ready_cannot_return_success(prepared, drift):
    a, op, native, _, peer, work, _, b = prepared
    remote = adopt(prepared)
    record = a._record(op)
    running = asyncio.create_task(remote.begin_ready())
    await read_frame(peer, b)
    if drift == "epoch":
        record.fence.retire()
    elif drift == "home":
        native.home += "/other"
    elif drift == "slot":
        record.remote_slot = type(record.remote_slot)()
    elif drift == "lease":
        object.__setattr__(record.lease, "profile", "other")
    elif drift == "store":
        record.store = object()
    elif drift == "headers":
        record.headers = None
    elif drift == "policy":
        work._invalid = True
    else:
        work._packet = b"bad"
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0))
    with pytest.raises(AuthorityRefusalError):
        await running
    assert remote._failed is True
    if drift != "headers":
        assert record.headers is not None
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)


@pytest.mark.asyncio
async def test_cancelled_wait_never_returns_late_ready(prepared):
    a, op, _, _, peer, _, _, b = prepared
    remote = adopt(prepared)
    running = asyncio.create_task(remote.begin_ready())
    await read_frame(peer, b)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    record = a._record(op)
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert record.remote_operation is remote and record.headers is not None


@pytest.mark.asyncio
async def test_local_go_and_prelaunch_refusal_have_no_remote_shortcut(prepared):
    a, op, _, _, _, _, _, _ = prepared
    remote = adopt(prepared)
    record = a._record(op)
    with pytest.raises(FrameError):
        a.owner.refuse_prelaunch(record.handle)
    a.owner.go(record.handle, remote, a.owner.challenge(record.handle))
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    assert not await a.retire_known(op)


@pytest.mark.asyncio
@pytest.mark.parametrize("local_path", ["cancel_complete", "emit", "reauthorize"])
async def test_no_local_terminal_projection_releases_remote_credit(prepared, local_path):
    a, op, _, _, _, _, _, _ = prepared
    adopt(prepared)
    record = a._record(op)
    job = a.owner._resolve(record.handle)
    emitted = []
    if local_path == "emit":
        job.state = State.REAUTHORIZED  # emulate an erroneous future local projection
        a.owner.emit_inline(record.handle, lambda _: True, lambda *args: emitted.append(args))
    elif local_path == "reauthorize":
        job.state = State.COMPLETE
        await a.owner.reauthorize(record.handle)
    else:
        job.state = State.COMPLETE
        a.owner.cancel(record.handle)
    assert emitted == [] and a.owner.inspect(record.handle)[2] is False
    assert record.headers is not None and not await a.retire_known(op)


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["send", "receive"])
async def test_adopted_channel_rejects_ordinary_io_before_bytes(prepared, direction):
    a, op, _, channel, peer, _, _, b = prepared
    remote = adopt(prepared)
    with pytest.raises(FrameError):
        if direction == "send":
            await channel.send(BrokerFrame(BrokerHeader(b, "GO", 0, 0), b""), remote._end)
        else:
            await channel.receive(remote._end, expected=b)
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    assert channel._remote_owner is remote and a._record(op).remote_operation is remote


@pytest.mark.asyncio
async def test_terminal_status_cannot_adopt_remote_operation_channel(prepared):
    a, op, _, channel, _, _, _, b = prepared
    remote = adopt(prepared)
    with pytest.raises(FrameError):
        TerminalStatusExchange(channel, b, remote._end)
    assert channel._terminal_owner is None and channel._remote_owner is remote
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    assert a.owner.inspect(a.handle(op)) == (State.UNKNOWN, False, False)


@pytest.mark.asyncio
async def test_two_native_reservations_cannot_share_one_wire_channel(prepared):
    a, op, native, channel, _, _, _, b = prepared
    first = adopt(prepared)
    other = ParentAuthorityAdapter("a" * 52, service=Native(native.home))
    other_op = other.reserve(
        replace(a._record(op).lease), "METADATA", OriginalHeaders.from_request(Request()),
        listener=object(), fence=ListenerFence(1), store=object(), bridge=object(),
        identity=object(), native_owner=object())
    assert await other.initialize(other_op)
    other.start(other_op)
    work = NativePolicyWork(other, other_op)
    work.start()
    for _ in range(256):
        if work.poll_join():
            break
        await asyncio.sleep(0.005)
    else:
        pytest.fail("second synthetic policy did not join")
    assert await work.postcheck()
    packet = work.worker_input(source_manifest_sha="b" * 64,
                               canonical_fallback="Synthetic", observed_at=0)
    with pytest.raises(AuthorityRefusalError):
        other.bind_remote(other_op, channel, b, packet)
    assert channel._remote_owner is first
    assert other._record(other_op).remote_operation is not first
    assert other.owner.inspect(other.handle(other_op)) == (State.UNKNOWN, False, False)
    await ready_exchange(prepared, first)  # no substituted reservation or second BEGIN


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["deadline", "cancel"])
async def test_final_peer_boundary_cannot_return_stale_ready(prepared, monkeypatch, boundary):
    a, op, _, channel, peer, _, _, b = prepared
    remote = adopt(prepared)
    original = channel._check
    reached = []
    def peer_check():
        result = original()
        if a.owner.inspect_remote(a.handle(op)) is RemotePhase.READY:
            reached.append(True)
            if boundary == "deadline":
                monkeypatch.setattr(remote_module.time, "monotonic_ns", lambda: remote._end)
            else:
                asyncio.current_task().cancel()
        return result
    monkeypatch.setattr(channel, "_check", peer_check)
    running = asyncio.create_task(remote.begin_ready())
    await read_frame(peer, b)
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0))
    expected = AuthorityRefusalError if boundary == "deadline" else asyncio.CancelledError
    with pytest.raises(expected):
        await running
    assert reached and remote._failed is True
    assert a.owner.inspect(a.handle(op)) == (State.UNKNOWN, False, False)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["owner", "fence"])
async def test_scope_refusal_never_invokes_drifted_metadata_callbacks(prepared, field):
    a, op, _, _, peer, _, _, b = prepared
    remote = adopt(prepared)
    record = a._record(op)
    original_owner, handle, fence = record._custody_snapshot
    class Foreign:
        def __getattr__(self, name):
            pytest.fail("drifted context must not supply a callback or closure")
    running = asyncio.create_task(remote.begin_ready())
    await read_frame(peer, b)
    setattr(record, field, Foreign())
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0))
    with pytest.raises(AuthorityRefusalError):
        await running
    assert original_owner.inspect(handle) == (State.UNKNOWN, False, False)
    assert fence.current is False and remote._failed is True and record.headers is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["kernel", "python_timeout"])
async def test_changed_socket_mode_refuses_before_begin_io(prepared, monkeypatch, mode):
    a, op, _, channel, peer, _, _, _ = prepared
    remote = adopt(prepared)
    if mode == "kernel":
        os.set_blocking(channel._fd, True)
    else:
        channel._socket.settimeout(0.25)
        assert os.get_blocking(channel._fd) is False
    def forbidden(*args, **kwargs):
        pytest.fail("no socket write may even be created in blocking/timeout mode")
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_sendall", forbidden)
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.begin_ready()
        with pytest.raises(BlockingIOError):
            peer.recv(1)
        assert a.owner.inspect(a.handle(op)) == (State.UNKNOWN, False, False)
    finally:
        channel._socket.setblocking(False)
