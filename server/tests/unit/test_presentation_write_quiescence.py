"""Original task/write facts only; no cleanup-reader or release activation."""
import asyncio
from contextlib import suppress

import pytest

from hmp_plugin import presentation_remote_cleanup as cleanup
from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import local as local
from .test_presentation_go_transport import coupled as coupled
from .test_presentation_result_transport import coupled_result as coupled_result
from .test_presentation_supervisor import context as context

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


async def test_actual_go_quiescence_is_not_a_task_or_reader_join(coupled_result):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go()
    owner = remote._cleanup_owner_snapshot
    channel = remote._channel_snapshot
    fact = owner._write_fact_snapshot
    assert type(fact) is cleanup._WriteQuiescence
    assert fact.owner is owner and fact.work is owner._allocations_snapshot[1]
    assert fact.channel is channel and fact.begin is channel._begin_write_fact_snapshot
    assert fact.go is channel._go_write_fact_snapshot
    assert fact.budget is owner._refs_snapshot[8] and fact.clock is owner._refs_snapshot[4]
    assert owner._write_notice_snapshot.result() is fact
    assert channel._work_write_retired and not channel._refused
    assert not owner._work_joined and not fact.work.task.done()
    assert not owner._write_fact_consumed
    assert await remote.result_ready()  # retirement does not disable result reads/work clock
    cleanup.RemoteCleanupOwner.request(owner)
    assert await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert owner._work_joined and fact.work.task.done()
    assert owner._write_fact_snapshot is fact and owner._write_fact_consumed
    assert owner._cancel_write_attempted and owner._cancel_write_completed


async def test_ready_cancel_mints_no_go_quiescence_on_original_work_finally(coupled):
    remote, _, _, _ = coupled
    assert await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert owner._write_fact_snapshot is None and not owner._write_notice_snapshot.done()
    cleanup.RemoteCleanupOwner.request(owner)
    assert await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    fact = owner._write_fact_snapshot
    assert type(fact) is cleanup._WriteQuiescence and fact.go is None
    assert fact.begin is remote._channel_snapshot._begin_write_fact_snapshot
    assert fact.work.task.done() and owner._work_joined and owner._write_fact_consumed
    assert owner._write_notice_snapshot.result() is fact and owner._cancel_sequence == 1


async def test_foreign_caller_cannot_publish_or_consume_original_write_fact(coupled_result):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go()
    owner = remote._cleanup_owner_snapshot
    fact = owner._write_fact_snapshot
    with pytest.raises(AuthorityRefusalError):
        cleanup.RemoteCleanupOwner._publish_write_quiescence(owner)
    with pytest.raises(AuthorityRefusalError):
        cleanup.RemoteCleanupOwner._prepare_cancel(owner, remote._channel_snapshot)
    assert owner._write_fact_snapshot is fact and not owner._write_fact_consumed
    assert await remote.result_ready()


async def test_forged_barrier_completion_cannot_authorize_go_or_cancel(coupled_result):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    owner._write_notice_snapshot.set_result(object())
    with pytest.raises(AuthorityRefusalError):
        await remote.go()
    assert owner._write_fact_snapshot is None and not owner._write_fact_consumed
    assert remote._channel_snapshot._go_write_intent_snapshot is None
    assert not owner._cancel_write_attempted


@pytest.mark.parametrize("field", ["channel", "work", "budget", "clock", "future", "owner"])
async def test_fact_scope_retarget_refuses_before_foreign_callbacks(coupled_result, field):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go()
    owner = remote._cleanup_owner_snapshot
    original = owner._write_fact_snapshot
    callbacks = []
    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign quiescence scope must not be inspected")
    owner._write_fact = owner._write_fact_snapshot = original._replace(**{field: Foreign()})
    try:
        with pytest.raises(AuthorityRefusalError):
            await remote.result_ready()
        assert callbacks == [] and not owner._cancel_write_attempted
    finally:
        owner._write_fact = owner._write_fact_snapshot = original  # disposal after refusal only


@pytest.mark.parametrize("after", [False, True])
async def test_quiescence_future_allocation_retained_before_failing_initializer(
    coupled_result, monkeypatch, after
):
    remote, _, _, _ = coupled_result
    initialize = cleanup._initialize_future
    seen = []
    def fail(future, loop):
        owner = remote._cleanup_owner_snapshot
        if owner is not None and future is owner._write_notice_snapshot:
            seen.append(future)
            assert owner._write_barrier_snapshot[0] is future
            assert owner._allocations_snapshot == (None, None)
            if after:
                initialize(future, loop)
            raise OSError("synthetic quiescence Future initialization ambiguity")
        initialize(future, loop)
    monkeypatch.setattr(cleanup, "_initialize_future", fail)
    with pytest.raises(AuthorityRefusalError):
        await remote.begin_ready()
    owner = remote._cleanup_owner_snapshot
    assert seen and owner._write_notice_snapshot is seen[0] and owner._unknown
    assert not owner._write_notice_initialized and owner._write_fact_snapshot is None
    assert owner._allocations_snapshot == (None, None)
    if after:
        assert not cleanup._FUTURE.done(seen[0])  # test knows the injected native phase


async def test_failed_native_mint_is_retained_and_never_retried_in_finally(
    coupled_result, monkeypatch
):
    from hmp_plugin.presentation_clock import NativeClockOwner

    remote, _, _, _ = coupled_result
    sample = NativeClockOwner.sample
    calls = []
    def fail(clock):
        owner = remote._cleanup_owner_snapshot
        if (owner is not None and owner._write_fact_attempted
                and owner._write_fact_snapshot is None and clock is owner._refs_snapshot[4]):
            calls.append(True)
            raise FrameError("synthetic quiescence sample refusal")
        return sample(clock)
    monkeypatch.setattr(NativeClockOwner, "sample", fail)
    assert await remote.begin_ready()
    with suppress(AuthorityRefusalError, FrameError):
        await remote.go()
    owner = remote._cleanup_owner_snapshot
    with suppress(BaseException):
        await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    assert calls == [True] and owner._write_fact_attempted and owner._write_fact_failed
    assert owner._write_fact_snapshot is None and not owner._write_fact_consumed
    assert remote._channel_snapshot._work_write_retired and not owner._cancel_write_attempted
