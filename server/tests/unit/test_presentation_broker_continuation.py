"""Original-controller continuation with no child launch or release authority.

Temporary Unix sockets/roots only. Peer and clock premises are mocked. These
checks do not run the native reader, supervisor, launchd or a live Hermes host.
"""
import asyncio
import socket
import time
from contextlib import suppress

import pytest

from hmp_plugin import presentation_broker_cancel as cancel
from hmp_plugin import presentation_broker_service as service
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_registry import RegistryStatus
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_cancel_transport import wait_receiver
from .test_presentation_clock import darwin_model

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


async def retained(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    monkeypatch.setattr(spine._registry, "resources_startable", lambda ticket: False)
    b, sock = binding(), client()
    end = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, end), version=2))
    task = asyncio.create_task(spine.serve_once(end + 200_000_000))
    record, owner = await wait_receiver(spine)
    return spine, b, sock, task, record, owner


def hold_service(monkeypatch):
    original = service.BrokerServiceSpine._v2_control
    notice = asyncio.get_running_loop().create_future()
    release = asyncio.Event()

    async def hold(spine, owner):
        frame = await original(spine, owner)
        notice.set_result(frame)
        await release.wait()
        return frame

    monkeypatch.setattr(service.BrokerServiceSpine, "_v2_control", hold)
    return notice, release


async def send_cancel(sock, b, *, suffix=b""):
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    wire = encode_frame(b, "CANCEL", 1, window.encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(sock, wire + suffix)
    return wire


async def dispose_unknown(spine, task, record, owner, release):
    """Freeze unknown production facts, then dispose only fixture-owned handles."""
    release.set()
    with suppress(FrameError):
        await task
    controller = owner._allocation_snapshot.task
    with suppress(BaseException):
        await asyncio.wait_for(asyncio.shield(controller), 1)
    assert controller.done() and owner._io_unknown and not owner._stop_known
    channel = record.channel_snapshot
    assert channel._reading is True
    assert not record.local_closed and not record.clock_closed and record in spine._records
    assert cancel.NativeClockOwner.close_local(channel._clock_owner_snapshot)
    socket.socket.close(channel._socket_snapshot)
    assert not channel._closed_known and not channel._clock_closed_known
    spine._records.remove(record)
    assert await spine.stop_local_sockets()


async def test_notice_keeps_original_controller_and_early_bytes_until_exact_join(
    local, monkeypatch
):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    original = owner._allocation_snapshot
    wire = await send_cancel(sock, b, suffix=b"SYNTHETIC_EARLY_ACK_NOT_AUTHORITY")
    try:
        frame = await asyncio.wait_for(notice, 1)
        receipt = cancel.BrokerCancellationOwner.cancel_receipt(owner)
        assert receipt.frame is frame and receipt.allocation is original
        assert receipt.future is owner._cancel_future_snapshot
        assert receipt.park is owner._park_future_snapshot
        assert owner._allocation_snapshot is original and not original.task.done()
        assert record.channel_snapshot._reading is True and not owner._joined
        assert owner._frame_start == owner._wire_received == len(wire)
        assert owner._buffer_origin == b""
        assert record.channel_snapshot._socket_snapshot.recv(128, socket.MSG_PEEK) == (
            b"SYNTHETIC_EARLY_ACK_NOT_AUTHORITY")
        held = spine._registry._record(record.ticket)
        assert held.resources is None and not held.start_attempted
        assert not record.local_closed and not record.clock_closed
    finally:
        release.set()
        await task
    assert owner._joined and owner._stop_known
    assert owner._allocation_snapshot.task.cancelling() == 1
    assert record.local_closed and record.clock_closed
    assert spine._registry.status(b) is RegistryStatus.CLOSED  # unlaunched journal only
    assert await spine.stop_local_sockets()


async def test_repeated_abort_has_one_original_stop_intent(local, monkeypatch):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    cancel.BrokerCancellationOwner.abort(owner)
    intent = owner._stop_intent_snapshot
    cancel.BrokerCancellationOwner.abort(owner)
    assert owner._stop_intent_snapshot is intent
    assert await cancel.BrokerCancellationOwner.join(owner)
    assert owner._stop_known and owner._allocation_snapshot.task.cancelling() == 1
    release.set()
    await task
    assert record.local_closed and record.clock_closed
    assert await spine.stop_local_sockets()


@pytest.mark.parametrize("field", ["mint", "scope", "allocation", "future", "park", "timeout"])
async def test_replaced_receipt_refuses_before_foreign_effects(local, monkeypatch, field):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    original = owner._cancel_receipt_snapshot
    owner._cancel_receipt = owner._cancel_receipt_snapshot = original._replace(**{field: object()})
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.cancel_receipt(owner)
    finally:
        owner._cancel_receipt = owner._cancel_receipt_snapshot = original
        await dispose_unknown(spine, task, record, owner, release)


async def test_sticky_refusal_never_follows_another_operation_budget(local, monkeypatch):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    original = owner._cancel_receipt_snapshot
    other = CancellationBudget(time.monotonic_ns() + 1_500_000_000)
    before = CancellationBudget.inspect(other)
    scope = (*original.scope[:3], other, *original.scope[4:])
    owner._cancel_receipt = owner._cancel_receipt_snapshot = original._replace(scope=scope)
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.cancel_receipt(owner)
        assert CancellationBudget.inspect(other) == before
    finally:
        owner._cancel_receipt = owner._cancel_receipt_snapshot = original
        await dispose_unknown(spine, task, record, owner, release)
    assert CancellationBudget.inspect(other) == before


async def test_foreign_paired_deadline_never_calls_equality(local, monkeypatch):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    calls = []

    class Foreign:
        def __eq__(self, other):
            calls.append("equality")
            raise AssertionError("foreign callback")

    original = owner._park_end_snapshot
    owner._park_end = owner._park_end_snapshot = Foreign()
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.cancel_receipt(owner)
        assert not calls
    finally:
        owner._park_end = owner._park_end_snapshot = original
        await dispose_unknown(spine, task, record, owner, release)


@pytest.mark.parametrize("target,name", [("notice", "done"), ("task", "result"),
                                       ("park", "add_done_callback")])
async def test_service_refuses_shadowed_future_methods_without_calling_them(
    local, monkeypatch, target, name
):
    control = service.BrokerServiceSpine._v2_control
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    calls = []

    def foreign(*args, **kwargs):
        calls.append(name)
        raise AssertionError("foreign callback")

    value = {"notice": owner._cancel_future_snapshot, "task": owner._allocation_snapshot.task,
             "park": owner._park_future_snapshot}[target]
    setattr(value, name, foreign)
    try:
        with pytest.raises(FrameError):
            await control(spine, owner)
        assert not calls
    finally:
        delattr(value, name)
        await dispose_unknown(spine, task, record, owner, release)


@pytest.mark.parametrize("replacement", ["other_receiver", "wrong_method"])
async def test_other_native_bound_method_cannot_replace_notice_done(
    local, monkeypatch, replacement
):
    control = service.BrokerServiceSpine._v2_control
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    other = asyncio.get_running_loop().create_future()
    future = owner._cancel_future_snapshot
    future.done = other.done if replacement == "other_receiver" else future.cancel
    try:
        with pytest.raises(FrameError):
            await control(spine, owner)
        assert not other.done() and not future.cancelled()
    finally:
        del future.done
        await dispose_unknown(spine, task, record, owner, release)


async def test_rescheduled_park_timer_cannot_renew_original_end(local, monkeypatch):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    timeout = owner._timeout_snapshot
    original_end = timeout.when()
    timeout.reschedule(original_end + 5)
    try:
        with pytest.raises(FrameError):
            cancel.BrokerCancellationOwner.cancel_receipt(owner)
        assert owner._park_end_snapshot / 1_000_000_000 == original_end
    finally:
        timeout.reschedule(original_end)  # fixture restoration, not production retry
        await dispose_unknown(spine, task, record, owner, release)


@pytest.mark.parametrize("after_notice", [False, True])
async def test_service_cancellation_joins_the_original_controller(local, monkeypatch, after_notice):
    if after_notice:
        notice, _ = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    if after_notice:
        await send_cancel(sock, b)
        await asyncio.wait_for(notice, 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert owner._joined and owner._cancel_attempted
    assert owner._allocation_snapshot.task.cancelling() == 1
    assert record.local_closed and record.clock_closed
    assert await spine.stop_local_sockets()


@pytest.mark.parametrize("which", ["notice", "park"])
@pytest.mark.parametrize("after", [False, True])
async def test_partial_future_initializer_never_notifies_or_launches(
    local, monkeypatch, which, after
):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    monkeypatch.setattr(spine._registry, "resources_startable", lambda ticket: False)
    original = cancel._initialize_future
    calls = 0

    def initialize(future, loop):
        nonlocal calls
        calls += 1
        if calls == (2 if which == "notice" else 3):
            if after:
                original(future, loop)
            raise RuntimeError("SYNTHETIC_CONTINUATION_INIT_FAILURE")
        original(future, loop)

    monkeypatch.setattr(cancel, "_initialize_future", initialize)
    b, sock = binding(), client()
    end = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, end), version=2))
    with pytest.raises(FrameError):
        await spine.serve_once(end + 200_000_000)
    record = spine._records[0]
    owner = record.cancel_owner
    held = spine._registry._record(record.ticket)
    assert held.resources is None and not held.start_attempted
    assert owner._allocation_snapshot is None and owner._cancel_receipt_snapshot is None
    assert not record.local_closed and not owner._joined
    # No controller Task or resource exists in this exact injected initializer
    # failure. Test-only close after the outcome; no production retry/closure.
    assert service.SocketChannel.close(record.channel_snapshot)
    assert service.SocketChannel.close_clock(record.channel_snapshot)
    spine._records.remove(record)
    assert await spine.stop_local_sockets()


@pytest.mark.parametrize("kind", ["foreign_cancel", "foreign_wake", "deadline"])
async def test_unknown_park_outcome_retains_read_and_connection_debt(local, monkeypatch, kind):
    notice, release = hold_service(monkeypatch)
    spine, b, sock, task, record, owner = await retained(local, monkeypatch)
    await send_cancel(sock, b)
    await asyncio.wait_for(notice, 1)
    controller = owner._allocation_snapshot.task
    if kind == "foreign_cancel":
        owner._park_future_snapshot.cancel()
    elif kind == "foreign_wake":
        owner._park_future_snapshot.set_result(None)
    with suppress(BaseException):
        await asyncio.wait_for(asyncio.shield(controller), 1)
    assert controller.done() and owner._io_unknown
    assert record.channel_snapshot._reading is True and not owner._stop_known
    await dispose_unknown(spine, task, record, owner, release)
