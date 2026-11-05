"""Synthetic coupled GO controls, real Unix IO/owned reader, mocked peer/clock.

No live host, real content, result publication or remote/native credit release.
"""
import asyncio
import os
import time
from contextlib import suppress
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_remote_cleanup as cleanup
from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_broker_service import SocketChannel
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from hmp_plugin.presentation_jobs import FrameError, RemotePhase, State

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_cancel_transport import read_v2, wait_receiver
from .test_presentation_clock import darwin_model
from .test_presentation_remote import adopt, prepare
from .test_presentation_supervisor import context as context

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


@pytest_asyncio.fixture
async def coupled(local, context, monkeypatch):
    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    channel = SocketChannel(sock, replace(enrollment, gateway_pid=os.getpid(),
                                         service_pid=os.getpid() + 1), role="gateway",
                            endpoint=spine._endpoint, observation=spine._observation)
    row = await prepare(context, (channel, None, spine))
    remote = adopt(row)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 2_000_000_000))
    yield remote, task, row, spine
    row[2].release.set()
    owner = remote._cleanup_owner_snapshot
    if owner is not None and owner._initialized is True:
        cleanup.RemoteCleanupOwner.request(owner)
        with suppress(BaseException):
            await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    if not task.done():
        task.cancel()
    with suppress(BaseException):
        await task
    # Test-owned disposal after outcomes; not timely/remote closure proof.
    channel.close()
    channel.close_clock()
    await spine.stop_local_sockets()


async def test_fresh_native_go_and_cancel2_keep_original_work_and_started_debt(
    coupled, monkeypatch
):
    # This causal isolates GO/CANCEL2 before RESULT; result transport has its own matrix.
    monkeypatch.setattr(BrokerRegistry, "poll_resource_result", lambda *args: False)
    remote, task, row, spine = coupled
    authority, op, native, channel, _, _, _, b = row
    assert await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    work = owner._allocations_snapshot[1]
    assert native.calls["PRE_GO"] == 3
    assert await remote.go()
    assert native.calls["PRE_GO"] == 4
    assert authority.owner.inspect_remote(authority._record(op).handle) is RemotePhase.GO_SENT
    assert authority.owner.inspect(authority._record(op).handle) == (State.RUNNING, True, False)
    assert owner._allocations_snapshot[1] is work and not work.task.done()
    assert channel._go_write_fact.intent.work is work
    record, receiver = await wait_receiver(spine)
    for _ in range(100):
        if receiver._go_relay_completed:
            break
        await asyncio.sleep(0.001)
    assert receiver._go_relay_intent and receiver._go_relay_completed
    assert receiver._allocation_snapshot.task is receiver._slot_snapshot.task
    cleanup.RemoteCleanupOwner.request(owner)
    assert await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    await task
    held = spine._registry._record(record.ticket)
    assert receiver._adopted and receiver._frame.header.sequence == 2
    assert owner._cancel_sequence == 2 and owner._cancel_write_completed
    assert held.resources._go_attempted and held.resources._phase == "LOCAL_DRAINED"
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert authority._record(op).headers is not None
    assert authority.owner.inspect(authority._record(op).handle)[2] is False
    assert CancellationBudget.inspect(held.cleanup_budget)[2] == (
        CancellationBudget.inspect(authority._record(op).cleanup_budget)[2])


async def test_another_public_task_cannot_request_go(coupled):
    remote, _, row, _ = coupled
    assert await remote.begin_ready()
    before = dict(row[2].calls)
    foreign = asyncio.create_task(remote.go())
    with pytest.raises(AuthorityRefusalError):
        await foreign
    assert row[2].calls == before
    assert remote._go_admission is None and row[3]._go_write_intent is None
    assert remote._cleanup_owner_snapshot._intent


async def test_fresh_native_refusal_cannot_write_go_or_use_ready_observations(coupled, monkeypatch):
    remote, _, row, _ = coupled
    assert await remote.begin_ready()
    native = row[2]
    original = native.observe
    async def denied(record, phase):
        value = await original(record, phase)
        return replace(value, allowed=False)
    monkeypatch.setattr(native, "observe", denied)
    with pytest.raises(AuthorityRefusalError):
        await remote.go()
    assert native.calls["PRE_GO"] == 4
    assert remote._go_admission is None and row[3]._go_write_intent is None
    assert row[0].owner.inspect(row[0]._record(row[1]).handle)[1] is False


async def test_duplicate_go_is_not_replayed(coupled):
    remote, _, row, _ = coupled
    assert await remote.begin_ready() and await remote.go()
    fact = row[3]._go_write_fact_snapshot
    before = dict(row[2].calls)
    with pytest.raises(AuthorityRefusalError):
        await remote.go()
    assert row[3]._go_write_fact_snapshot is fact and row[2].calls == before
    assert row[0]._record(row[1]).headers is not None


async def test_delivered_go_and_cancel2_revoke_before_resource_relay(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_900_000_000))
    assert (await read_v2(sock, b)).header.kind == "READY"
    record, receiver = await wait_receiver(spine)
    allocation = receiver._allocation_snapshot
    now = time.monotonic_ns()
    window = CancellationWindow(now, now + CLEANUP_NS)
    await asyncio.get_running_loop().sock_sendall(sock,
        encode_frame(b, "GO", 1, version=2)
        + encode_frame(b, "CANCEL", 2, window.encode(), version=2))
    await task
    assert receiver._allocation_snapshot is allocation and receiver._go_receipt is not None
    assert receiver._adopted and not receiver._go_relay_intent
    held = spine._registry._record(record.ticket)
    assert not held.resources._go_attempted and held.resources._phase == "LOCAL_DRAINED"
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert await spine.stop_local_sockets()


async def test_torn_go_has_no_following_cancel_or_replay(coupled, monkeypatch):
    remote, task, row, _ = coupled
    assert await remote.begin_ready()
    channel, b = row[3], row[7]
    original = cleanup._LOOP.sock_sendall
    writes = []
    async def send(loop, sock, data):
        if sock is channel._socket_snapshot:
            writes.append(data)
            if data == encode_frame(b, "GO", 1, version=2):
                await original(loop, sock, b"tornGO")
                raise OSError("synthetic partial GO ambiguity")
        return await original(loop, sock, data)
    monkeypatch.setattr(cleanup._LOOP, "sock_sendall", send)
    with pytest.raises(AuthorityRefusalError):
        await remote.go()
    owner = remote._cleanup_owner_snapshot
    await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    with pytest.raises(FrameError):
        await task
    assert len(writes) == 1 and channel._go_write_intent is not None
    assert channel._go_write_fact is None and not owner._cancel_write_attempted
    assert owner._unknown and owner._work_joined
    assert row[0]._record(row[1]).headers is not None
    assert row[0].owner.inspect(row[0]._record(row[1]).handle)[2] is False


async def test_public_cancel_during_fresh_native_go_freezes_before_task_cancel(coupled):
    remote, _, row, _ = coupled
    ready = asyncio.Event()
    start_go = asyncio.Event()
    native = row[2]
    async def flow():
        assert await remote.begin_ready()
        ready.set()
        await start_go.wait()
        return await remote.go()
    public = asyncio.create_task(flow())
    await asyncio.wait_for(ready.wait(), 1)
    native.block = "PRE_GO"
    native.block_occurrence = 4
    start_go.set()
    await asyncio.wait_for(native.entered.wait(), 1)
    owner = remote._cleanup_owner_snapshot
    public.cancel()
    with pytest.raises(asyncio.CancelledError):
        await public
    end = CancellationBudget.inspect(row[0]._record(row[1]).cleanup_budget)[2]
    assert end is not None and owner._intent
    await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert owner._cancel_attempted and owner._work_joined
    assert remote._go_admission is None and row[3]._go_write_intent is None
    assert row[0]._record(row[1]).headers is not None
    assert CancellationBudget.inspect(row[0]._record(row[1]).cleanup_budget)[2] == end


@pytest.mark.parametrize("field", ["owner", "fence", "policy_work"])
async def test_native_go_return_scope_drift_never_reaches_wire(coupled, monkeypatch, field):
    remote, _, row, _ = coupled
    assert await remote.begin_ready()
    native, record = row[2], row[0]._record(row[1])
    held = getattr(record, field)
    calls = []
    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("foreign GO scope must not run")
    # Put drift after the concrete native observer's own local postcheck, so
    # this exercises the remote operation's post-await raw-reference fence.
    original_observe = cleanup.ParentAuthorityAdapter._observe
    async def observed(a, r, phase):
        result = await original_observe(a, r, phase)
        if r is record and phase == "PRE_GO":
            setattr(record, field, Foreign())
        return result
    monkeypatch.setattr(cleanup.ParentAuthorityAdapter, "_observe", observed)
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.go()
        assert native.calls["PRE_GO"] == 4 and calls == []
        assert remote._go_admission is None and row[3]._go_write_intent is None
    finally:
        setattr(record, field, held)


async def test_job_clock_cannot_invoke_foreign_go_allocation_index(coupled, monkeypatch):
    from hmp_plugin.presentation_jobs import JobOwner

    remote, _, row, _ = coupled
    assert await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    allocation = owner._allocations_snapshot
    original = JobOwner._current
    changed, callbacks = [], []
    class Foreign:
        def __getitem__(self, key):
            callbacks.append(key)
            raise AssertionError("allocation must be sealed before indexing")
    def current(jobs, job):
        result = original(jobs, job)
        if (jobs is row[0].owner and remote._go_admission is not None
                and job.remote_phase is RemotePhase.READY and not changed):
            changed.append(True)
            owner._allocations_snapshot = Foreign()
        return result
    monkeypatch.setattr(JobOwner, "_current", current)
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.go()
        assert changed and callbacks == []
        assert row[3]._go_write_intent is None
        assert row[0]._record(row[1]).headers is not None
    finally:
        owner._allocations_snapshot = allocation  # test-only disposal after refusal
        with suppress(AuthorityRefusalError, asyncio.CancelledError):
            await asyncio.wait_for(asyncio.shield(allocation[1].task), 1)


@pytest.mark.parametrize("scope", ["device", "profile", "revoked"])
async def test_stale_or_revoked_native_scope_cannot_request_go(coupled, scope):
    remote, _, row, _ = coupled
    assert await remote.begin_ready()
    record = row[0]._record(row[1])
    before = dict(row[2].calls)
    held = record.lease
    if scope == "revoked":
        record.fence.retire()
    else:
        field = "device_id" if scope == "device" else "profile"
        record.lease = replace(held, **{field: "synthetic-other"})
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.go()
        assert row[2].calls == before and remote._go_admission is None
        assert row[3]._go_write_intent is None and record.headers is not None
    finally:
        record.lease = held  # test disposal; revocation remains sticky


@pytest.mark.parametrize("after_init", [False, True])
async def test_partial_broker_go_notification_init_retains_debt_without_launch(
    local, monkeypatch, after_init
):
    from hmp_plugin import presentation_broker_cancel as broker_cancel

    spine, _, client, packet, _, _ = local
    darwin_model(monkeypatch)
    original = broker_cancel._initialize_future
    def initialize(future, loop):
        if after_init:
            original(future, loop)
        raise RuntimeError("synthetic GO notification init ambiguity")
    monkeypatch.setattr(broker_cancel, "_initialize_future", initialize)
    b, sock = binding(), client()
    deadline = time.monotonic_ns() + 1_500_000_000
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(b, "BEGIN", 0, packet(b, deadline), version=2))
    with pytest.raises(FrameError):
        await spine.serve_once(time.monotonic_ns() + 1_900_000_000)
    record = spine._records[0]
    owner = record.cancel_owner
    held = spine._registry._record(record.ticket)
    assert owner._go_allocation_snapshot == (owner._go_future_snapshot,)
    assert owner._go_initialized is None and owner._allocation_snapshot is None
    assert held.resources is None and not held.start_attempted
    assert CancellationBudget.inspect(held.cleanup_budget)[3]
    assert not record.local_closed and not owner._joined
    # No Task was allocated. Exact fixture socket/clock disposal only after the
    # retained-failure outcome; never a production retry or native release.
    assert SocketChannel.close(record.channel_snapshot)
    assert SocketChannel.close_clock(record.channel_snapshot)
    spine._records.remove(record)
    assert await spine.stop_local_sockets()
