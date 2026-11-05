"""Actual owned async tasks/sockets, synthetic authority and mocked native peers.

No host content, CANCEL frame, GO, result, server deployment or remote release.
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
async def test_caller_cancel_retains_cleanup_and_no_following_cancel_frame(prepared_v2):
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
                                               ("cause", False), ("cause", True)])
async def test_partial_barrier_future_is_retained_without_work(
    prepared_v2, monkeypatch, field, after_init
):
    _, _, native, _, peer, _, _, _ = prepared_v2
    remote = adopt(prepared_v2)
    original = cleanup._initialize_future
    def initialize(future, loop):
        owner = remote._cleanup_owner_snapshot
        assert future is owner._start_snapshot or future is owner._cause_snapshot
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
@pytest.mark.parametrize("field", ["start", "cause"])
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
