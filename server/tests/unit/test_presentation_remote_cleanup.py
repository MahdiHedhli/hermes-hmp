"""Actual owned async tasks/sockets, synthetic authority and mocked native peers.

No host content, GO, result, server deployment or remote release.
"""
import asyncio
from contextlib import suppress

import pytest

from hmp_plugin import presentation_remote_cleanup as cleanup
from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_cancel_budget import CancellationBudget
from hmp_plugin.presentation_jobs import State

from .test_presentation_broker_service import local as local
from .test_presentation_remote import adopt, read_selected
from .test_presentation_remote import prepared_v2 as prepared_v2
from .test_presentation_selected_protocol import v2gateway as v2gateway
from .test_presentation_supervisor import context as context


async def start_waiting(prepared_v2):
    remote = adopt(prepared_v2)
    public = asyncio.create_task(remote.begin_ready())
    frame = await read_selected(prepared_v2[4], prepared_v2[7])
    assert frame.header.kind == "BEGIN"
    return remote, public, remote._cleanup_owner_snapshot


async def joined_cleanup(owner, seconds=1):
    task = owner._slots_snapshot[0].task_snapshot
    result = await asyncio.wait_for(asyncio.shield(task), seconds)
    assert task.done() and not task.cancelled()
    return result


@pytest.mark.asyncio
async def test_caller_cancel_retains_cleanup_and_sends_one_frozen_cancel(prepared_v2):
    a, op, _, channel, peer, _, _, _ = prepared_v2
    remote, public, owner = await start_waiting(prepared_v2)
    record = a._record(op)
    work = owner._slots_snapshot[1].task_snapshot
    cleanup_task = owner._slots_snapshot[0].task_snapshot
    assert work is not public and cleanup_task is not public and cleanup_task is not work
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    end = CancellationBudget.inspect(record.cleanup_budget)[2]
    assert end is not None
    assert await joined_cleanup(owner)
    assert owner._work_joined and owner._socket_closed and owner._clock_closed
    assert work.done() and channel._closed_known and channel._clock_closed_known
    frame = await read_selected(peer, prepared_v2[7])
    assert frame.header.kind == "CANCEL" and frame.header.sequence == 1
    from hmp_plugin.presentation_cancel_budget import CancellationWindow
    assert CancellationWindow.decode(frame.body).end_ns == end
    assert owner._cancel_write_attempted and owner._cancel_write_completed
    assert await asyncio.wait_for(asyncio.get_running_loop().sock_recv(peer, 1), 1) == b""
    assert record.headers is not None
    assert a.owner.inspect(record.handle) == (State.UNKNOWN, False, False)
    owner.request()
    assert CancellationBudget.inspect(record.cleanup_budget)[2] == end
    assert remote._cleanup_owner is owner and not hasattr(owner, "release")


@pytest.mark.asyncio
async def test_first_cause_is_frozen_before_owned_task_cancellation(prepared_v2, monkeypatch):
    a, op, _, _, _, _, _, _ = prepared_v2
    remote, public, owner = await start_waiting(prepared_v2)
    record = a._record(op)
    original = cleanup.NativeClockOwner.cleanup_sample
    observed = []
    def sample(clock):
        work = owner._slots_snapshot[1].task_snapshot
        observed.append((owner._intent, record.fence.current, work.cancelling()))
        return original(clock)
    monkeypatch.setattr(cleanup.NativeClockOwner, "cleanup_sample", sample)
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert observed[0] == (True, False, 0)
    assert owner._cancel_attempted
    assert CancellationBudget.inspect(record.cleanup_budget)[2] is not None
    assert await joined_cleanup(owner)
    assert remote._failed


@pytest.mark.asyncio
async def test_default_factory_gate_refuses_before_work_task_or_begin(prepared_v2):
    a, op, native, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    loop = asyncio.get_running_loop()
    calls = []
    def factory(loop, coro, **kwargs):
        calls.append("factory")
        return asyncio.Task(coro, loop=loop, **kwargs)
    before = dict(native.calls)
    loop.set_task_factory(factory)
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.begin_ready()
    finally:
        loop.set_task_factory(None)
    assert calls == [] and native.calls == before
    assert not remote._begin_attempted and remote._cleanup_owner._unknown
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    assert a._record(op).headers is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("slot_index,after_init", [(0, False), (0, True), (1, False), (1, True)])
async def test_partial_task_initialization_retains_allocations_and_never_opens_work(
    prepared_v2, monkeypatch, slot_index, after_init
):
    a, op, native, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    original = cleanup._initialize_task
    calls = []
    def initialize(slot, loop):
        calls.append(slot)
        owner = remote._cleanup_owner_snapshot
        assert owner is remote._cleanup_owner
        assert slot.task is slot.task_snapshot and slot.coroutine is slot.coroutine_snapshot
        if len(calls) - 1 == slot_index:
            if after_init:
                original(slot, loop)
            raise RuntimeError("synthetic initializer ambiguity")
        original(slot, loop)
    monkeypatch.setattr(cleanup, "_initialize_task", initialize)
    before = dict(native.calls)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert owner._unknown and native.calls == before and not remote._begin_attempted
    assert owner._start_snapshot.done() and owner._start_snapshot.result() is False
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    assert a._record(op).headers is not None
    # Test-only disposal after outcome freeze: initialize an exact known fixture
    # allocation whose injected failure ran before its initializer, with barriers
    # still closed. No production retry or release fact is inferred.
    for slot in owner._slots_snapshot:
        if slot.task is not None:
            if slot.initialized is not True:
                original(slot, owner._loop)
            assert await asyncio.wait_for(asyncio.shield(slot.task), 1) is False


@pytest.mark.asyncio
async def test_late_ready_after_cancel_never_returns_success(prepared_v2):
    from hmp_plugin.presentation_broker_codec import encode_frame

    a, op, _, _, peer, _, _, b = prepared_v2
    _, public, owner = await start_waiting(prepared_v2)
    public.cancel()
    with suppress(BrokenPipeError, ConnectionResetError):
        await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0, version=2))
    with pytest.raises(asyncio.CancelledError):
        await public
    await joined_cleanup(owner)
    assert a.owner.inspect(a._record(op).handle)[0] is State.UNKNOWN


@pytest.mark.asyncio
async def test_ready_retains_deadline_watcher_and_only_local_closure(prepared_v2):
    from hmp_plugin.presentation_broker_codec import encode_frame

    a, op, _, _, peer, _, _, b = prepared_v2
    remote, public, owner = await start_waiting(prepared_v2)
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0, version=2))
    assert await public
    assert not owner._slots_snapshot[0].task_snapshot.done()
    assert not owner._slots_snapshot[1].task_snapshot.done()  # READY is not a work join
    assert owner._ready_fact.future is owner._barriers_snapshot.ready
    assert owner._ready_fact.work is owner._allocations_snapshot[1]
    assert not owner._intent and not owner._socket_closed
    assert await joined_cleanup(owner, seconds=3)
    budget = a._record(op).cleanup_budget
    assert CancellationBudget.inspect(budget)[2] <= remote._end + 250_000_000
    assert a._record(op).headers is not None
    assert a.owner.inspect(a._record(op).handle) == (State.UNKNOWN, False, False)


@pytest.mark.asyncio
async def test_cancellation_swallowing_work_is_not_closed_or_released(prepared_v2):
    a, op, native, channel, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    native.block = "PRE_GO"
    native.block_occurrence = native.calls["PRE_GO"] + 1
    native.ignore_cancel = True
    public = asyncio.create_task(remote.begin_ready())
    await asyncio.wait_for(native.entered.wait(), 1)
    owner = remote._cleanup_owner_snapshot
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    end = CancellationBudget.inspect(a._record(op).cleanup_budget)[2]
    owner.request()
    assert not await joined_cleanup(owner)
    assert owner._unknown and not owner._work_joined
    assert not owner._socket_closed and not channel._close_attempted
    assert not owner._slots_snapshot[1].task_snapshot.done()
    assert a._record(op).native_claim is not None and a._record(op).headers is not None
    assert CancellationBudget.inspect(a._record(op).cleanup_budget)[2] == end
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    native.release.set()  # fixture-owned native continuation, after outcome freeze
    with pytest.raises((asyncio.CancelledError, AuthorityRefusalError)):
        await asyncio.wait_for(asyncio.shield(owner._slots_snapshot[1].task_snapshot), 1)


@pytest.mark.asyncio
async def test_expired_original_budget_does_not_start_local_close(prepared_v2, monkeypatch):
    from hmp_plugin import presentation_clock

    a, op, _, channel, _, _, _, _ = prepared_v2
    remote, public, owner = await start_waiting(prepared_v2)
    monkeypatch.setattr(presentation_clock, "_MONOTONIC_NS", lambda: remote._end + 1_000_000_000)
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert not await joined_cleanup(owner)
    assert CancellationBudget.inspect(a._record(op).cleanup_budget)[2] == remote._end + 250_000_000
    assert not channel._close_attempted and not owner._socket_closed
    assert owner._unknown and a._record(op).headers is not None


@pytest.mark.asyncio
async def test_ambiguous_partial_begin_gets_eof_not_an_appended_frame(prepared_v2, monkeypatch):
    from hmp_plugin.presentation_broker_service import SocketChannel
    from hmp_plugin.presentation_jobs import FrameError

    a, op, _, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    async def partial(channel, frame, end, *, owner):
        channel._writing = True
        try:
            await asyncio.get_running_loop().sock_sendall(channel._socket, b"partial-BEGIN")
            raise FrameError("synthetic partial write")
        finally:
            channel._writing = False
    monkeypatch.setattr(SocketChannel, "send", partial)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert not remote._send_completed
    assert await joined_cleanup(owner)
    chunks = []
    while True:
        part = await asyncio.wait_for(asyncio.get_running_loop().sock_recv(peer, 128), 1)
        if not part:
            break
        chunks.append(part)
    assert b"".join(chunks) == b"partial-BEGIN"
    assert a._record(op).headers is not None


@pytest.mark.asyncio
async def test_cleanup_task_cancel_retains_debt_without_replacement(prepared_v2):
    _, public, owner = await start_waiting(prepared_v2)
    cleanup_task = owner._slots_snapshot[0].task_snapshot
    cleanup_task.cancel()
    assert not await joined_cleanup(owner)
    with pytest.raises((asyncio.CancelledError, AuthorityRefusalError)):
        await public
    assert owner._unknown and owner._slots_snapshot[0].task_snapshot is cleanup_task
    assert not owner._socket_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("field,after_init", [("start", False), ("start", True),
                                               ("cause", False), ("cause", True),
                                               ("ready", False), ("ready", True),
                                               ("go_request", False), ("go_request", True),
                                               ("go_notice", False), ("go_notice", True),
                                               ("result_notice", False), ("result_notice", True)])
async def test_partial_barrier_future_is_retained_without_work(
    prepared_v2, monkeypatch, field, after_init
):
    _, _, native, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    original = cleanup._initialize_future
    def initialize(future, loop):
        owner = remote._cleanup_owner_snapshot
        assert future in (owner._start_snapshot, owner._cause_snapshot, owner._ready_snapshot,
                          owner._go_request_snapshot, owner._go_notice_snapshot,
                          owner._result_notice_snapshot)
        if future is getattr(owner, "_" + field + "_snapshot"):
            if after_init:
                original(future, loop)
            raise RuntimeError("synthetic barrier ambiguity")
        original(future, loop)
    monkeypatch.setattr(cleanup, "_initialize_future", initialize)
    before = dict(native.calls)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert owner._unknown and native.calls == before and not remote._begin_attempted
    assert all(slot.task is None for slot in owner._slots_snapshot)
    assert getattr(owner, "_" + field + "_snapshot") is not None
    with pytest.raises(BlockingIOError):
        peer.recv(1)


@pytest.mark.asyncio
async def test_exact_completed_task_substitution_cannot_fake_original_work_join(prepared_v2):
    a, op, native, channel, _, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    native.block = "PRE_GO"
    native.block_occurrence = native.calls["PRE_GO"] + 1
    native.ignore_cancel = True
    public = asyncio.create_task(remote.begin_ready())
    await asyncio.wait_for(native.entered.wait(), 1)
    owner = remote._cleanup_owner_snapshot
    original = owner._allocations_snapshot[1]
    async def completed():
        return False
    fake = asyncio.create_task(completed())
    assert await fake is False
    slot = owner._slots_snapshot[1]
    slot.task = slot.task_snapshot = fake
    slot.coroutine = slot.coroutine_snapshot = fake.get_coro()
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert not await joined_cleanup(owner)
    assert owner._unknown and not owner._work_joined and not original.task.done()
    assert original.task.cancelling() == 1 and not fake.cancelling()
    assert not channel._close_attempted and a._record(op).headers is not None
    # Test-only disposal of exact retained original after the refusal outcome.
    slot.task = slot.task_snapshot = original.task
    slot.coroutine = slot.coroutine_snapshot = original.coroutine
    native.release.set()
    with pytest.raises((asyncio.CancelledError, AuthorityRefusalError)):
        await asyncio.wait_for(asyncio.shield(original.task), 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["start", "cause", "ready"])
async def test_exact_barrier_substitution_never_becomes_original_barrier(prepared_v2, field):
    _, public, owner = await start_waiting(prepared_v2)
    original = owner._barriers_snapshot
    fake = asyncio.Future()
    fake.set_result(True)
    setattr(owner, "_" + field, fake)
    setattr(owner, "_" + field + "_snapshot", fake)
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert not await joined_cleanup(owner)
    assert owner._unknown and not owner._socket_closed
    assert owner._barriers_snapshot is original
    setattr(owner, "_" + field, getattr(original, field))
    setattr(owner, "_" + field + "_snapshot", getattr(original, field))


@pytest.mark.asyncio
async def test_cancel_before_barrier_open_still_joins_and_uses_cleanup_clock(
    prepared_v2, monkeypatch
):
    _, _, native, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    original = cleanup._initialize_task
    calls = []
    def initialize(slot, loop):
        original(slot, loop)
        calls.append(slot)
        if len(calls) == 2:
            asyncio.current_task().cancel()  # cancellation observed before work gate opens
    monkeypatch.setattr(cleanup, "_initialize_task", initialize)
    before = dict(native.calls)
    public = asyncio.create_task(remote.begin_ready())
    with pytest.raises(asyncio.CancelledError):
        await public
    owner = remote._cleanup_owner_snapshot
    assert await joined_cleanup(owner)
    assert owner._work_joined and not remote._begin_attempted and native.calls == before
    assert await asyncio.wait_for(asyncio.get_running_loop().sock_recv(peer, 1), 1) == b""


@pytest.mark.asyncio
async def test_mutable_begin_completion_flag_cannot_authorize_appended_cancel(
    prepared_v2, monkeypatch
):
    from hmp_plugin.presentation_broker_service import SocketChannel
    from hmp_plugin.presentation_jobs import FrameError

    _, _, _, channel, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    async def partial(channel, frame, end, *, owner):
        await asyncio.get_running_loop().sock_sendall(channel._socket, b"torn-BEGIN")
        owner._send_completed = True  # tainted metadata cannot mint native write evidence
        raise FrameError("synthetic incomplete send")
    monkeypatch.setattr(SocketChannel, "send", partial)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert await joined_cleanup(owner)
    assert owner._unknown and channel._begin_write_fact is None
    assert not owner._cancel_write_attempted
    data = bytearray()
    while True:
        part = await asyncio.wait_for(asyncio.get_running_loop().sock_recv(peer, 128), 1)
        if not part:
            break
        data.extend(part)
    assert bytes(data) == b"torn-BEGIN"


@pytest.mark.asyncio
async def test_partial_cancel_write_retains_intent_without_retry(prepared_v2, monkeypatch):
    from hmp_plugin.presentation_broker_service import SocketChannel

    a, op, _, channel, peer, _, _, _ = prepared_v2
    _, public, owner = await start_waiting(prepared_v2)
    original = cleanup._LOOP.sock_sendall
    calls = []
    async def partial(loop, sock, data):
        calls.append(data)
        await original(loop, sock, data[:11])
        raise OSError("synthetic cancellation write ambiguity")
    monkeypatch.setattr(cleanup._LOOP, "sock_sendall", partial)
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert not await joined_cleanup(owner)
    assert len(calls) == 1 and owner._cancel_write_attempted and not owner._cancel_write_completed
    assert owner._unknown and not owner._socket_closed and not channel._writing
    partial_data = await asyncio.wait_for(asyncio.get_running_loop().sock_recv(peer, 11), 1)
    assert partial_data == calls[0][:11]
    with pytest.raises(AuthorityRefusalError):
        await SocketChannel.send_cancel(channel, owner)
    assert len(calls) == 1 and a._record(op).headers is not None


@pytest.mark.asyncio
async def test_actual_local_sender_receiver_adopt_same_original_window(prepared_v2):
    import os
    from dataclasses import replace

    from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
    from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader
    from hmp_plugin.presentation_broker_lifecycle import OperationGrammar
    from hmp_plugin.presentation_broker_registry import RegistryStatus
    from hmp_plugin.presentation_broker_service import BrokerServiceSpine, SocketChannel
    from hmp_plugin.presentation_input_v3 import decode_input_v3

    a, op, _, gateway_channel, peer, _, packet, b = prepared_v2
    remote = adopt(prepared_v2)
    enrollment = replace(gateway_channel._enrollment,
                         gateway_pid=os.getpid() + 1, service_pid=os.getpid())
    broker = SocketChannel(peer, enrollment, role="broker", endpoint=gateway_channel._endpoint,
                           observation=gateway_channel._observation)
    from hmp_plugin.presentation_broker_registry import BrokerRegistry
    registry = BrokerRegistry(b)
    public = asyncio.create_task(remote.begin_ready())
    first = await SocketChannel.receive(broker, remote._end, expected=b)
    assert first.body == packet
    grammar = OperationGrammar(b, role="broker", protocol_version=2)
    grammar.observe(first, sender="client")
    row = decode_input_v3(packet)
    ticket = registry.reserve(b, row["profile"], row["operation"], row["deadline_ns"])
    receiver = BrokerCancellationOwner.retain(broker, registry, ticket, grammar)
    try:
        ready = BrokerFrame(BrokerHeader(b, "READY", 0, 0, 2), b"")
        grammar.observe(ready, sender="broker")
        await SocketChannel.send(broker, ready, remote._end)
        assert await public
        owner = remote._cleanup_owner_snapshot
        owner.request()
        assert await joined_cleanup(owner)
        frame = await BrokerServiceSpine._v2_control(None, receiver)
        assert frame.header.kind == "CANCEL" and receiver._adopted
        assert not receiver._allocation_snapshot.task.done() and broker._reading
        assert CancellationBudget.inspect(registry._record(ticket).cleanup_budget)[2] == (
            CancellationBudget.inspect(a._record(op).cleanup_budget)[2])
        assert registry.status(b) is RegistryStatus.PENDING
        assert registry._record(ticket).resources is None and a._record(op).headers is not None
    finally:
        if not receiver._allocation_snapshot.task.done():
            receiver.abort()
        with suppress(BaseException):
            await asyncio.wait_for(asyncio.shield(receiver._allocation_snapshot.task), 1)
        assert SocketChannel.close(broker) and SocketChannel.close_clock(broker)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["wire", "writing"])
async def test_cancel_post_native_drift_cannot_supply_bytes_or_clear_write_intent(
    prepared_v2, monkeypatch, field
):
    _, public, owner = await start_waiting(prepared_v2)
    channel, peer = prepared_v2[3:5]
    original = cleanup.NativeClockOwner.cleanup_sample
    changed = []
    def sample(clock):
        now = original(clock)
        if owner._cancel_write_attempted and channel._writing and not changed:
            changed.append(True)
            if field == "wire":
                owner._cancel_wire = owner._cancel_wire_snapshot = b"forged-wire"
            else:
                channel._writing = False
        return now
    monkeypatch.setattr(cleanup.NativeClockOwner, "cleanup_sample", sample)
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert not await joined_cleanup(owner)
    assert changed and owner._unknown and not owner._cancel_write_completed
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    assert not channel._writing


@pytest.mark.asyncio
async def test_begin_write_fact_is_immutable_and_redacted(prepared_v2):
    _, public, owner = await start_waiting(prepared_v2)
    channel = prepared_v2[3]
    fact = channel._begin_write_fact_snapshot
    assert repr(fact) == "<BeginWriteFact redacted>"
    assert repr(fact.intent) == "<BeginWriteIntent redacted>"
    with pytest.raises(AttributeError):
        object.__setattr__(fact.intent, "packet", b"forged")
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert await joined_cleanup(owner)


@pytest.mark.asyncio
async def test_foreign_ready_notification_cannot_certify_ready_or_work_join(prepared_v2):
    _, public, owner = await start_waiting(prepared_v2)
    owner._barriers_snapshot.ready.set_result(True)  # exact Future, no concrete work fact
    with pytest.raises(AuthorityRefusalError):
        await public
    assert owner._ready_fact is None
    assert await joined_cleanup(owner)
    assert owner._work_joined and owner._cancel_write_completed


@pytest.mark.asyncio
async def test_public_cancel_does_not_cancel_ready_notification_future(prepared_v2):
    _, public, owner = await start_waiting(prepared_v2)
    ready = owner._barriers_snapshot.ready
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    assert await joined_cleanup(owner)
    assert ready.done() and not ready.cancelled() and ready.result() is False
    assert owner._work_joined and owner._cancel_attempted


@pytest.mark.asyncio
async def test_ready_task_remains_original_until_explicit_cleanup(prepared_v2):
    from hmp_plugin.presentation_broker_codec import encode_frame

    _, public, owner = await start_waiting(prepared_v2)
    peer, b = prepared_v2[4], prepared_v2[7]
    work = owner._allocations_snapshot[1]
    await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0, version=2))
    assert await public
    assert owner._allocations_snapshot[1] is work and not work.task.done()
    assert not owner._work_joined and not owner._socket_closed
    assert owner._ready_fact.packet is owner._remote_snapshot._packet_snapshot
    assert "packet" not in repr(owner._ready_fact)
    owner.request()
    assert await joined_cleanup(owner)
    assert owner._allocations_snapshot[1] is work and work.task.done()
    assert owner._barriers_snapshot.ready.result() is True
    assert not owner._barriers_snapshot.cause.cancelled()
    assert owner._work_joined and owner._cancel_write_completed


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["owner", "fence", "policy_work"])
async def test_public_ready_post_native_record_drift_refuses_without_foreign_callbacks(
    prepared_v2, monkeypatch, field
):
    from hmp_plugin.presentation_broker_codec import encode_frame

    authority, op, _, _, peer, _, _, b = prepared_v2
    record = authority._record(op)
    remote, public, owner = await start_waiting(prepared_v2)
    original = cleanup.ParentAuthorityAdapter._current
    held = getattr(record, field)
    calls = []
    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("foreign record field must never be invoked")
    foreign = Foreign()
    changed = []
    def current(a, r):
        result = original(a, r)
        if a is authority and asyncio.current_task() is public and not changed:
            changed.append(True)
            setattr(record, field, foreign)
        return result
    monkeypatch.setattr(cleanup.ParentAuthorityAdapter, "_current", current)
    try:
        await asyncio.get_running_loop().sock_sendall(peer, encode_frame(b, "READY", 0, version=2))
        with pytest.raises(AuthorityRefusalError):
            await public
        assert changed and calls == [] and remote._failed
        await joined_cleanup(owner)
        assert record.headers is not None
    finally:
        setattr(record, field, held)  # test-only disposal after the refusal outcome
