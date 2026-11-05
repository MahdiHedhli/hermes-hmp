"""Coupled private v2 model: actual Unix IO/reader cleanup, synthetic roots.

Kernel peer and Darwin clock facts are explicitly mocked, not qualification.
No live host, phone credentials/messages, GO dispatch, result or native release.
"""
import asyncio
import time
from contextlib import suppress

import pytest

from hmp_plugin import presentation_broker_cancel as cancel
from hmp_plugin import presentation_broker_service as service
from hmp_plugin.presentation_broker_codec import (
    decode_frame,
    decode_header,
    encode_frame,
    header_size,
)
from hmp_plugin.presentation_broker_registry import RegistryStatus
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_supervisor import context as context

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


async def read_v2(sock, b):
    async def exact(n):
        data = bytearray()
        while len(data) < n:
            part = await asyncio.get_running_loop().sock_recv(sock, n - len(data))
            assert part
            data.extend(part)
        return bytes(data)
    async def receive():
        prefix = await exact(8)
        raw = prefix + await exact(header_size(prefix))
        header = decode_header(raw, expected=b, expected_version=2)
        return decode_frame(raw + await exact(header.body_length), expected=b, expected_version=2)
    return await asyncio.wait_for(receive(), 1)


async def wait_receiver(spine):
    for _ in range(100):
        if spine._records and spine._records[0].cancel_owner is not None:
            return spine._records[0], spine._records[0].cancel_owner
        await asyncio.sleep(0.001)
    pytest.fail("synthetic retained receiver did not appear")


async def test_queued_cancel_closes_only_never_launched_journal(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    monkeypatch.setattr(spine._registry, "resources_startable", lambda ticket: False)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    await asyncio.get_running_loop().sock_sendall(sock,
        encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2)
        + encode_frame(b, "CANCEL", 1, window.encode(), version=2))
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    await task
    held = spine._registry._record(spine._registry._operations[b.operation])
    assert held.resources is None and not held.start_attempted
    assert spine._registry.status(b) is RegistryStatus.CLOSED  # never-launched journal only
    assert CancellationBudget.inspect(held.cleanup_budget)[2] == window.end_ns
    assert await asyncio.wait_for(asyncio.get_running_loop().sock_recv(sock, 1), 1) == b""
    assert not spine._records
    assert await spine.stop_local_sockets()


async def test_cancel_header_stops_launch_while_body_is_pending(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    data = encode_frame(b, "CANCEL", 1, window.encode(), version=2)
    await asyncio.get_running_loop().sock_sendall(sock,
        encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2) + data[:-16])
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    record, owner = await wait_receiver(spine)
    for _ in range(100):
        if owner._retired:
            break
        await asyncio.sleep(0.001)
    assert owner._retired and not owner._adopted
    held = spine._registry._record(record.ticket)
    assert held.resources is None and not held.start_attempted
    await asyncio.get_running_loop().sock_sendall(sock, data[-16:])
    await task
    assert owner._adopted and owner._joined
    assert CancellationBudget.inspect(held.cleanup_budget)[2] == window.end_ns
    assert spine._registry.status(b) is RegistryStatus.CLOSED
    assert await spine.stop_local_sockets()


async def test_ready_cancel_cleans_owned_reader_but_started_registry_stays_pending(
    local, monkeypatch
):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    ready = await read_v2(sock, b)
    assert ready.header.kind == "READY"
    record, owner = await wait_receiver(spine)
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "CANCEL", 1, window.encode(), version=2))
    await task
    held = spine._registry._record(record.ticket)
    assert owner._adopted and owner._joined and record.local_closed and record.clock_closed
    assert held.resources._phase == "LOCAL_DRAINED" and not held.resources._go_attempted
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert CancellationBudget.inspect(held.cleanup_budget)[2] == window.end_ns
    assert not spine._records and await spine.stop_local_sockets()


async def test_service_cancel_freezes_before_cancelling_exclusive_reader(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    monkeypatch.setattr(spine._registry, "resources_startable", lambda ticket: False)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    record, owner = await wait_receiver(spine)
    original = cancel.NativeClockOwner.cleanup_sample
    observed = []
    def sample(clock):
        observed.append((owner._retired, owner._allocation_snapshot.task.cancelling()))
        return original(clock)
    monkeypatch.setattr(cancel.NativeClockOwner, "cleanup_sample", sample)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert observed[0] == (True, 0)
    assert owner._cancel_attempted and owner._joined
    assert owner._allocation_snapshot.task.cancelling() == 1
    assert record.local_closed and record.clock_closed and not spine._records
    assert spine._registry.status(b) is RegistryStatus.CLOSED
    assert await spine.stop_local_sockets()


async def test_v2_go_is_cleanup_refusal_not_execution_permission(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    assert (await read_v2(sock, b)).header.kind == "READY"
    record, _ = await wait_receiver(spine)
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "GO", 1, version=2))
    with pytest.raises(FrameError):
        await task
    resources = spine._registry._record(record.ticket).resources
    assert not resources._go_attempted and resources._phase == "LOCAL_DRAINED"
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert not spine._records and await spine.stop_local_sockets()


async def test_partial_receiver_init_retains_connection_and_disables_launch(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    original = cancel._initialize_task
    def fail_after(slot, loop):
        original(slot, loop)
        raise RuntimeError("synthetic native initializer ambiguity")
    monkeypatch.setattr(cancel, "_initialize_task", fail_after)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    with pytest.raises(FrameError):
        await spine.serve_once(time.monotonic_ns() + 1_900_000_000)
    assert len(spine._records) == 1
    record = spine._records[0]
    owner = record.cancel_owner
    held = spine._registry._record(record.ticket)
    assert held.resources is None and not held.start_attempted
    assert CancellationBudget.inspect(held.cleanup_budget)[3]
    assert not record.local_closed and not owner._joined
    # Controlled AFTER-init injection only: fixture knows native init returned.
    # Dispose the exact original task/FDs after the failure outcome; this is not
    # a production retry, release or timely-cleanup observation.
    assert owner._slot_snapshot.initialized
    with suppress(BaseException):
        await owner._allocation_snapshot.task
    assert owner._allocation_snapshot.task.done()
    assert service.SocketChannel.close(record.channel_snapshot)
    assert service.SocketChannel.close_clock(record.channel_snapshot)
    spine._records.remove(record)
    assert await spine.stop_local_sockets()


async def test_native_remote_service_roundtrip_preserves_parent_and_started_debt(
    local, context, monkeypatch
):
    import os
    from dataclasses import replace

    from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

    from .test_presentation_remote import adopt, prepare

    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    gateway_enrollment = replace(enrollment, gateway_pid=os.getpid(), service_pid=os.getpid() + 1)
    channel = service.SocketChannel(sock, gateway_enrollment, role="gateway",
                                    endpoint=spine._endpoint, observation=spine._observation)
    row = await prepare(context, (channel, None, spine))
    authority, operation, native, _, _, _, _, b = row
    remote = adopt(row)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 2_000_000_000))
    public = asyncio.create_task(remote.begin_ready())
    try:
        assert await public
        record, receiver = await wait_receiver(spine)
        cleanup_owner = remote._cleanup_owner_snapshot
        assert channel._begin_write_fact is channel._begin_write_fact_snapshot
        assert channel._begin_write_fact.intent.packet is remote._packet_snapshot
        RemoteCleanupOwner.request(cleanup_owner)
        cleanup_task = cleanup_owner._allocations_snapshot[0].task
        assert await asyncio.wait_for(asyncio.shield(cleanup_task), 1)
        await task
        assert receiver._adopted and receiver._joined
        held = spine._registry._record(record.ticket)
        assert CancellationBudget.inspect(held.cleanup_budget)[2] == (
            CancellationBudget.inspect(authority._record(operation).cleanup_budget)[2])
        assert held.resources._phase == "LOCAL_DRAINED" and not held.resources._go_attempted
        assert spine._registry.status(b) is RegistryStatus.PENDING
        assert authority._record(operation).headers is not None
        assert authority.owner.inspect(authority._record(operation).handle)[2] is False
        assert native.calls == {"INITIAL": 1, "BEFORE": 1, "PRE_GO": 3}
        assert cleanup_owner._cancel_write_attempted and cleanup_owner._cancel_write_completed
        assert not spine._records
    finally:
        native.release.set()
        if not public.done():
            public.cancel()
        with suppress(BaseException):
            await public
        if not task.done():
            task.cancel()
        with suppress(BaseException):
            await task
        assert channel.close() and channel.close_clock()
        assert await spine.stop_local_sockets()
