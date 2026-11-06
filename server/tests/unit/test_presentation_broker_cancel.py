"""Real owned Unix bytes/tasks; peer and Darwin clock facts explicitly mocked.

No service activation, reader launch, native authorizations, host or user data.
"""
import asyncio
import errno
import os
import time
from contextlib import suppress
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_broker_cancel as cancel
from hmp_plugin import presentation_broker_service as service
from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader, encode_frame
from hmp_plugin.presentation_broker_lifecycle import OperationGrammar
from hmp_plugin.presentation_broker_registry import RegistryStatus
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model


@pytest_asyncio.fixture
async def broker_context(local, monkeypatch):
    spine, enrollment, client, packet, _, _ = local
    darwin_model(monkeypatch)
    peer = client()
    sock, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    sock.setblocking(False)
    e = replace(enrollment, gateway_pid=os.getpid() + 1, service_pid=os.getpid(),
                protocol_version=2)
    channel = service.SocketChannel(sock, e, role="broker", endpoint=spine._endpoint,
                                    observation=spine._observation)
    b = binding()
    end = time.monotonic_ns() + 1_500_000_000
    data = packet(b, end)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "BEGIN", 0, data, version=2))
    first = await channel.receive(end)
    grammar = OperationGrammar(b, role="broker", protocol_version=2)
    grammar.observe(first, sender="client")
    ticket = spine._registry.reserve(b, "default", "METADATA", end)
    try:
        yield channel, peer, spine._registry, ticket, b, grammar
    finally:
        owner = channel._cancel_receiver_snapshot
        if (type(owner) is cancel.BrokerCancellationOwner and owner._allocation_snapshot is not None
                and owner._slot_snapshot.initialized is True):
            if not owner._allocation_snapshot.task.done():
                owner.abort()
            with suppress(BaseException):
                await asyncio.wait_for(asyncio.shield(owner._allocation_snapshot.task), 1)
            assert owner._allocation_snapshot.task.done()
        if (type(owner) is cancel.BrokerCancellationOwner
                and owner._io_unknown is True):
            assert channel._reading is True and not channel.close()
            # Fixture-only disposal after the original controller Task joined.
            # Keep production socket/read/clock facts UNKNOWN; our synthetic
            # loop/FD ownership permits disposal without certifying retirement.
            asyncio.get_running_loop().remove_reader(sock.fileno())
            assert cancel.NativeClockOwner.close_local(channel._clock_owner_snapshot)
            sock.close()
            assert not channel._closed_known and not channel._clock_closed_known
        else:
            assert channel.close() and channel.close_clock()
        peer.close()
        sock.close()
        assert await spine.stop_local_sockets()


@pytest_asyncio.fixture
async def receiver(broker_context):
    channel, peer, registry, ticket, b, grammar = broker_context
    owner = cancel.BrokerCancellationOwner.retain(channel, registry, ticket, grammar)
    yield owner, channel, peer, registry, ticket, b


@pytest.mark.asyncio
async def test_exact_cancel_adopts_existing_budget_before_any_resource_effect(receiver):
    owner, channel, peer, registry, ticket, b = receiver
    record = registry._record(ticket)
    original = record.cleanup_budget
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, window.encode(), version=2))
    frame = await service.BrokerServiceSpine._v2_control(None, owner)
    assert frame.header.kind == "CANCEL" and owner._adopted and owner._retired
    assert record.cleanup_budget is original is record.cleanup_budget_snapshot
    assert CancellationBudget.inspect(original)[2] == window.end_ns
    assert record.resources is None and not record.start_attempted
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    assert registry.status(b) is RegistryStatus.PENDING
    assert channel._closed_known is False and owner.join is not None
    assert not owner._allocation_snapshot.task.done() and channel._reading


@pytest.mark.asyncio
@pytest.mark.parametrize("local_first", [False, True])
async def test_local_and_received_causes_only_shorten_original_end(receiver, local_first):
    owner, _, peer, registry, ticket, b = receiver
    budget = registry._record(ticket).cleanup_budget
    now = time.monotonic_ns()
    local = CancellationWindow(now, now + CLEANUP_NS)
    earlier = CancellationWindow(now - 100_000_000, now - 100_000_000 + CLEANUP_NS)
    if local_first:
        CancellationBudget.local(budget, now)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, earlier.encode(), version=2))
    await service.BrokerServiceSpine._v2_control(None, owner)
    assert CancellationBudget.inspect(budget)[2] == earlier.end_ns
    owner._local_cause()
    assert CancellationBudget.inspect(budget)[2] == min(local.end_ns, earlier.end_ns)


@pytest.mark.asyncio
async def test_already_expired_received_window_never_gets_new_time(receiver):
    owner, _, peer, registry, ticket, b = receiver
    now = time.monotonic_ns()
    window = CancellationWindow(now - CLEANUP_NS - 1000, now - 1000)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, window.encode(), version=2))
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert owner._adopted
    assert not owner._notice_completed and owner._cancel_receipt_snapshot is None
    budget = registry._record(ticket).cleanup_budget
    assert CancellationBudget.remaining_ns(budget, time.monotonic_ns()) == 0
    assert budget.local(time.monotonic_ns()).end_ns == window.end_ns


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["version", "sequence", "scope", "GO", "future", "body"])
async def test_invalid_cancel_never_adopts_or_launches(receiver, bad):
    owner, _, peer, registry, ticket, b = receiver
    now = time.monotonic_ns()
    body = CancellationWindow(now, now + CLEANUP_NS).encode()
    version, sequence, kind = 2, 1, "CANCEL"
    if bad == "version":
        version, body = 1, b""
    elif bad == "sequence":
        sequence = 2
    elif bad == "scope":
        b = replace(b, operation="0" * 15 + "2" + "b" * 48)
    elif bad == "GO":
        kind, body = "GO", b""
    elif bad == "future":
        body = CancellationWindow(now + 10_000_000_000, now + 10_000_000_000 + CLEANUP_NS).encode()
    else:
        body = b"x" * 16
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, kind, sequence, body, version=version))
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert not owner._adopted and owner._failed
    assert registry._record(ticket).resources is None
    assert not registry._record(ticket).start_attempted


@pytest.mark.asyncio
async def test_exclusive_reader_blocks_general_receive_and_second_owner(receiver):
    owner, channel, _, registry, ticket, b = receiver
    with pytest.raises(FrameError):
        await channel.receive(owner._scope[2], expected=b)
    with pytest.raises(FrameError):
        cancel.BrokerCancellationOwner.retain(channel, registry, ticket, owner._grammar)
    owner.abort()
    assert await owner.join()
    assert not owner._adopted and registry.status(b) is RegistryStatus.PENDING


@pytest.mark.asyncio
async def test_partial_cancel_header_and_body_survive_original_work_expiry(receiver):
    owner, _, peer, registry, ticket, b = receiver
    deadline = owner._scope[2]
    window = CancellationWindow(deadline - 10_000_000, deadline - 10_000_000 + CLEANUP_NS)
    data = encode_frame(b, "CANCEL", 1, window.encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(peer, data[:12])
    await asyncio.sleep(max(0, (deadline - time.monotonic_ns()) / 1e9) + 0.01)
    assert owner._retired and not owner._allocation_snapshot.task.done()
    assert owner._grammar._invalidated
    await asyncio.get_running_loop().sock_sendall(peer, data[12:-4])
    await asyncio.sleep(0)
    await asyncio.get_running_loop().sock_sendall(peer, data[-4:])
    await service.BrokerServiceSpine._v2_control(None, owner)
    assert owner._adopted
    assert CancellationBudget.inspect(registry._record(ticket).cleanup_budget)[2] == window.end_ns


@pytest.mark.asyncio
async def test_eof_during_partial_frame_retires_and_retains_without_release(receiver):
    owner, _, peer, registry, ticket, b = receiver
    data = encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)
    await asyncio.get_running_loop().sock_sendall(peer, data[:14])
    peer.shutdown(1)
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert owner._retired and owner._failed and not owner._adopted
    assert registry.status(b) is RegistryStatus.PENDING
    assert registry._record(ticket).resources is None


@pytest.mark.asyncio
async def test_nonblocking_native_timeout_guard_refuses_before_read(receiver):
    owner, channel, peer, registry, ticket, b = receiver
    channel._socket.settimeout(0.1)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)[:8])
    try:
        with pytest.raises(FrameError):
            await owner._allocation_snapshot.task
        assert owner._failed and not owner._adopted
        assert registry._record(ticket).resources is None
    finally:
        channel._socket.setblocking(False)  # fixture-owned disposal only, no work retry


@pytest.mark.asyncio
async def test_generic_workclock_error_never_requalifies_cleanup(receiver, monkeypatch):
    owner, _, peer, registry, ticket, b = receiver
    def fail(clock):
        raise FrameError("synthetic generic clock-integrity failure")
    monkeypatch.setattr(cancel.NativeClockOwner, "sample", fail)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)[:8])
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert not owner._adopted and owner._failed
    budget = registry._record(ticket).cleanup_budget
    assert CancellationBudget.inspect(budget)[2:] == (None, True)


@pytest.mark.asyncio
async def test_factory_refusal_retires_original_budget_before_any_task(broker_context):
    channel, _, registry, ticket, _, grammar = broker_context
    budget = registry._record(ticket).cleanup_budget
    loop = asyncio.get_running_loop()
    calls = []
    def factory(loop, coro, **kwargs):
        calls.append("unexpected factory")
        return asyncio.Task(coro, loop=loop, **kwargs)
    loop.set_task_factory(factory)
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.retain(channel, registry, ticket, grammar)
    finally:
        loop.set_task_factory(None)
    retained = channel._cancel_receiver_snapshot
    assert retained._failed and retained._allocation_snapshot is None and calls == []
    assert grammar._invalidated and CancellationBudget.inspect(budget)[3]
    with pytest.raises(FrameError):
        registry.start_resources(ticket)


@pytest.mark.asyncio
@pytest.mark.parametrize("after", [False, True])
async def test_task_initializer_ambiguity_retains_and_retires_original_work(
    broker_context, monkeypatch, after
):
    channel, _, registry, ticket, _, grammar = broker_context
    budget = registry._record(ticket).cleanup_budget
    original = cancel._initialize_task
    def initialize(slot, loop):
        retained = channel._cancel_receiver_snapshot
        assert retained._allocation_snapshot.task is slot.task
        assert retained._allocation_snapshot.coroutine is slot.coroutine
        if after:
            original(slot, loop)
        raise RuntimeError("synthetic native initialization ambiguity")
    monkeypatch.setattr(cancel, "_initialize_task", initialize)
    with pytest.raises(FrameError):
        cancel.BrokerCancellationOwner.retain(channel, registry, ticket, grammar)
    retained = channel._cancel_receiver_snapshot
    assert retained is channel._cancel_receiver and retained._failed
    assert not await retained.join()  # initializer ambiguity is never native task completion proof
    assert grammar._invalidated and CancellationBudget.inspect(budget)[3]
    with pytest.raises(FrameError):
        registry.start_resources(ticket)
    if not after:
        # Fixture-only known-before-init injection: dispose exact synthetic task
        # behind failed owner, after outcome freeze. Production never retries.
        original(retained._slot_snapshot, retained._loop)
    assert await retained._allocation_snapshot.task is None


@pytest.mark.asyncio
@pytest.mark.parametrize("field", [
    "channel_role", "grammar_role", "grammar_values", "grammar_snapshot", "grammar_counter",
    "grammar_mode",
])
async def test_constructor_metadata_tripwires_refuse_without_comparison_callbacks(
    broker_context, field
):
    channel, _, registry, ticket, _, grammar = broker_context
    budget = registry._record(ticket).cleanup_budget
    callbacks = []
    class Foreign:
        def __eq__(self, other):
            callbacks.append("eq")
            return True
    target, key = ((channel, "_role") if field == "channel_role" else
                   (grammar, {"grammar_role": "_role", "grammar_values": "_binding_values",
                              "grammar_snapshot": "_role_snapshot",
                              "grammar_counter": "_client_next",
                              "grammar_mode": "_mode"}[field]))
    original = getattr(target, key)
    setattr(target, key, Foreign())
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.retain(channel, registry, ticket, grammar)
        assert callbacks == [] and CancellationBudget.inspect(budget)[3]
        assert grammar._invalidated
        with pytest.raises(FrameError):
            registry.start_resources(ticket)
    finally:
        setattr(target, key, original)  # fixture-only local close, never work retry


@pytest.mark.asyncio
async def test_native_task_substitution_cannot_join_or_cancel_the_wrong_reader(receiver):
    owner, _, _, _, _, _ = receiver
    await asyncio.sleep(0)  # original receiver is waiting on its owned socket
    original = owner._allocation_snapshot
    async def completed():
        return None
    fake = asyncio.create_task(completed())
    await fake
    slot = owner._slot_snapshot
    slot.task = slot.task_snapshot = fake
    slot.coroutine = slot.coroutine_snapshot = fake.get_coro()
    owner.abort()
    assert not fake.cancelling() and original.task.cancelling() == 1
    with pytest.raises(asyncio.CancelledError):
        await original.task
    assert await owner.join()  # original actual join, never substituted completion
    assert not owner._adopted
    slot.task = slot.task_snapshot = original.task
    slot.coroutine = slot.coroutine_snapshot = original.coroutine


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["clock", "domain", "deadline", "enrollment"])
async def test_post_native_metadata_drift_refuses_before_wire_read(receiver, monkeypatch, field):
    owner, channel, peer, registry, ticket, b = receiver
    callbacks = []
    class Foreign:
        def __getattribute__(self, key):
            callbacks.append(key)
            raise AssertionError("foreign getter")
    original = cancel.NativeClockOwner.sample
    saved = (channel._clock_owner, owner._scope[6]._domain, registry._record(ticket).deadline_ns,
             channel._enrollment)
    def sample(clock):
        now = original(clock)
        if field == "clock":
            channel._clock_owner = Foreign()
        elif field == "domain":
            clock._domain = Foreign()
        elif field == "deadline":
            registry._record(ticket).deadline_ns = Foreign()
        else:
            channel._enrollment = Foreign()
        return now
    monkeypatch.setattr(cancel.NativeClockOwner, "sample", sample)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)[:8])
    try:
        with pytest.raises(FrameError):
            await owner._allocation_snapshot.task
        assert callbacks == [] and not owner._adopted
        assert owner._failed
    finally:
        channel._clock_owner, owner._scope[6]._domain = saved[:2]
        registry._records[ticket].deadline_ns = saved[2]
        channel._enrollment = saved[3]


@pytest.mark.asyncio
async def test_abort_flag_drift_after_cleanup_sample_never_invokes_foreign_truthiness(
    receiver, monkeypatch
):
    owner, _, _, _, _, _ = receiver
    callbacks = []
    class Foreign:
        def __bool__(self):
            callbacks.append("bool")
            raise AssertionError("foreign truthiness")
    original = cancel.NativeClockOwner.cleanup_sample
    def sample(clock):
        now = original(clock)
        owner._cancel_attempted = Foreign()
        return now
    monkeypatch.setattr(cancel.NativeClockOwner, "cleanup_sample", sample)
    owner.abort()
    assert callbacks == [] and owner._failed and not owner._adopted
    # Fixture disposal only after refusal: retained original task, no retry.
    owner._cancel_attempted = False
    owner.abort()
    with pytest.raises(asyncio.CancelledError):
        await owner._allocation_snapshot.task


@pytest.mark.asyncio
async def test_go_clear_preserves_cumulative_original_cursor(receiver):
    owner, _, peer, _, _, b = receiver
    now = time.monotonic_ns()
    owner._grammar.observe(BrokerFrame(BrokerHeader(b, "READY", 0, 0, 2), b""),
                           sender="broker")  # explicit synthetic prior READY grammar fact
    go = encode_frame(b, "GO", 1, b"", version=2)
    cancel_wire = encode_frame(b, "CANCEL", 2,
        CancellationWindow(now, now + CLEANUP_NS).encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(peer, go + cancel_wire)
    frame = await service.BrokerServiceSpine._v2_control(None, owner)
    assert frame.header.kind == "CANCEL" and owner._adopted
    assert owner._frame_start == len(go) + len(cancel_wire)
    assert owner._wire_received == len(go) + len(cancel_wire)
    assert bytes(owner._buffer_origin) == b""
    assert not owner._allocation_snapshot.task.done()
    assert owner._pending is None and not owner._recv_intent and not owner._io_unknown


@pytest.mark.asyncio
async def test_cancel_after_readiness_hint_keeps_partial_bytes_in_original_cursor(
    receiver, monkeypatch
):
    owner, channel, peer, _, _, b = receiver
    original_recv, original_wait = cancel._SOCKET_RECV, cancel.SelectorReadiness.wait
    seen = []
    registered = asyncio.Event()

    def short_recv(sock, count):
        return original_recv(sock, min(count, 3))

    async def wait(waiter, end, **options):
        registered.set()
        await original_wait(waiter, end, **options)
        if owner._wire_received == 3 and not seen:
            seen.append(True)
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

    monkeypatch.setattr(cancel, "_SOCKET_RECV", short_recv)
    monkeypatch.setattr(cancel.SelectorReadiness, "wait", wait)
    now = time.monotonic_ns()
    wire = encode_frame(b, "CANCEL", 1,
        CancellationWindow(now, now + CLEANUP_NS).encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    with pytest.raises(asyncio.CancelledError):
        await owner._allocation_snapshot.task
    assert seen and owner._wire_received == 3 and bytes(owner._buffer_origin) == wire[:3]
    assert not owner._io_unknown and not channel._reading
    assert not owner._adopted and owner._pending is None


@pytest.mark.asyncio
async def test_uncertain_control_recv_retains_read_claim(receiver, monkeypatch):
    owner, channel, peer, _, _, b = receiver
    original = cancel._SOCKET_RECV
    consumed = []

    def recv(sock, count):
        part = original(sock, count)
        consumed.append(len(part))
        raise RuntimeError("synthetic interruption after syscall")

    monkeypatch.setattr(cancel, "_SOCKET_RECV", recv)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, b"x" * 16, version=2))
    with pytest.raises(RuntimeError):
        await owner._allocation_snapshot.task
    assert consumed == [8] and owner._wire_received == 0
    assert owner._io_unknown and owner._recv_intent and channel._reading
    assert not owner._adopted and not channel._closed_known


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["_wire_received", "_frame_start"])
async def test_control_recv_counter_drift_has_no_foreign_arithmetic(
    receiver, monkeypatch, field
):
    owner, channel, peer, _, _, b = receiver
    original = cancel._SOCKET_RECV
    callbacks = []

    class Foreign:
        def __add__(self, other):
            callbacks.append("add")
            raise AssertionError("foreign arithmetic")
        __iadd__ = __add__
        def __eq__(self, other):
            callbacks.append("eq")
            raise AssertionError("foreign comparison")

    def recv(sock, count):
        part = original(sock, count)
        setattr(owner, field, Foreign())
        return part

    monkeypatch.setattr(cancel, "_SOCKET_RECV", recv)
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "CANCEL", 1, b"x" * 16, version=2))
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert callbacks == [] and owner._wire_received == 8 and len(owner._buffer_origin) == 8
    assert owner._io_unknown and channel._reading and not owner._adopted


@pytest.mark.asyncio
async def test_control_eagain_wait_keeps_original_end(receiver, monkeypatch):
    owner, _, peer, _, _, b = receiver
    original_recv, original_wait = cancel._SOCKET_RECV, cancel.SelectorReadiness.wait
    calls, cutoffs = [], []

    def recv(sock, count):
        if not calls:
            calls.append(True)
            raise BlockingIOError(errno.EAGAIN, "synthetic zero-byte EAGAIN")
        return original_recv(sock, count)

    async def wait(waiter, end, **options):
        cutoffs.append(end)
        return await original_wait(waiter, end, **options)

    monkeypatch.setattr(cancel, "_SOCKET_RECV", recv)
    monkeypatch.setattr(cancel.SelectorReadiness, "wait", wait)
    now = time.monotonic_ns()
    wire = encode_frame(b, "CANCEL", 1,
        CancellationWindow(now, now + CLEANUP_NS).encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(peer, wire)
    await service.BrokerServiceSpine._v2_control(None, owner)
    assert cutoffs and set(cutoffs) == {owner._scope[2]}
    assert owner._wire_received == len(wire) and owner._adopted
    assert not owner._io_unknown and owner._pending is None


@pytest.mark.asyncio
async def test_control_non_eagain_blocking_error_keeps_unknown_read_claim(receiver, monkeypatch):
    owner, channel, _, _, _, _ = receiver

    def recv(sock, count):
        raise BlockingIOError(errno.EIO, "synthetic uncertain syscall")

    monkeypatch.setattr(cancel, "_SOCKET_RECV", recv)
    with pytest.raises(BlockingIOError):
        await owner._allocation_snapshot.task
    assert owner._io_unknown and owner._recv_intent and channel._reading
    assert owner._wire_received == 0 and not owner._adopted


@pytest.mark.asyncio
async def test_control_scope_retarget_cannot_retire_other_channel(receiver, monkeypatch):
    owner, channel, peer, _, _, b = receiver
    original_wait = cancel.SelectorReadiness.wait
    foreign = service.SocketChannel.__new__(service.SocketChannel)
    foreign._reading = True
    foreign._cancel_receiver_snapshot = owner
    changed = []
    registered = asyncio.Event()

    async def wait(waiter, end, **options):
        registered.set()
        await original_wait(waiter, end, **options)
        owner._channel = owner._channel_snapshot = foreign
        changed.append(True)

    monkeypatch.setattr(cancel.SelectorReadiness, "wait", wait)
    wire = encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    try:
        with pytest.raises(FrameError):
            await owner._allocation_snapshot.task
        assert changed and foreign._reading is True
        assert channel._reading is False and owner._wire_received == 3
        assert not owner._adopted
    finally:
        owner._channel = owner._channel_snapshot = channel  # synthetic disposal only


@pytest.mark.asyncio
async def test_lost_readiness_proof_and_budget_refusal_keeps_control_claim(receiver, monkeypatch):
    owner, channel, peer, _, _, b = receiver
    original = cancel.SelectorReadiness.wait
    registered = asyncio.Event()
    callbacks = []

    class Foreign:
        def __bool__(self):
            callbacks.append("bool")
            raise AssertionError("foreign retirement flag")

    async def wait(waiter, end, **options):
        registered.set()
        await original(waiter, end, **options)
        waiter._retired = Foreign()
        CancellationBudget.refuse(owner._scope_snapshot[3])

    monkeypatch.setattr(cancel.SelectorReadiness, "wait", wait)
    wire = encode_frame(b, "CANCEL", 1, b"x" * 16, version=2)
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    with pytest.raises(FrameError):
        await owner._allocation_snapshot.task
    assert callbacks == [] and owner._wire_received == 3
    assert owner._io_unknown and channel._reading and not owner._adopted
