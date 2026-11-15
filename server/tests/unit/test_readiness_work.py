"""Actual host executor/read leases; no host, credentials or feature authority."""
import asyncio
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from hmp_plugin.readiness_work import ReadActivityUnavailableError, ReadinessReadService
from hmp_plugin.request_ctx import ReadWorkerBudget


def owner():
    budget = ReadWorkerBudget()
    ctx = SimpleNamespace(store=object(), identity=object(), bridge=object(),
                          readiness_generation='a' * 32, read_worker_budget=budget)
    return ctx, budget, ReadinessReadService(ctx)


async def until(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(.005)
    raise AssertionError('bounded fixture condition absent')


def test_actual_future_end_keeps_caller_tail_charged_and_rejects_self_drain():
    async def scenario():
        _, budget, lane = owner()
        async with lane.activity(lambda: 7, deadline=time.monotonic() + 2) as value:
            assert value == 7
            assert budget.active == 1  # caller tail owns capacity even after result arrival
            await until(lambda: budget.active == 0
                        or any(op.worker_done for op in lane._activities))
            assert budget.active == 1
            assert lane.stop() == 1
            with pytest.raises(ReadActivityUnavailableError):
                await lane.wait_drained()
        await lane.wait_drained()
        assert budget.active == 0
    asyncio.run(scenario())


def test_timeout_keeps_real_worker_and_store_until_actual_return():
    async def scenario():
        _, budget, lane = owner()
        started, release = threading.Event(), threading.Event()
        def work():
            started.set()
            assert release.wait(3)
        try:
            with pytest.raises(TimeoutError):
                async with lane.activity(work, deadline=time.monotonic() + .05):
                    pytest.fail('timed-out read yielded')
            assert started.is_set() and budget.active == 1
            assert lane.stop() == 1
            waiter = asyncio.create_task(lane.wait_drained())
            await asyncio.sleep(.01)
            assert not waiter.done()
        finally:
            release.set()
        await asyncio.wait_for(waiter, 2)
        assert budget.active == 0
    asyncio.run(scenario())


def test_caller_cancel_does_not_cancel_actual_worker_or_refund_capacity():
    async def scenario():
        _, budget, lane = owner()
        started, release = threading.Event(), threading.Event()
        def work():
            started.set()
            assert release.wait(3)
        async def read():
            async with lane.activity(work, deadline=time.monotonic() + 2):
                pytest.fail('cancelled read yielded')
        task = asyncio.create_task(read())
        try:
            await until(started.is_set)
            actual = next(iter(lane._activities)).future
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not actual.cancel()  # actual running SDK Future cannot be cancelled
            assert budget.active == 1
            lane.stop()
        finally:
            release.set()
        await asyncio.wait_for(lane.wait_drained(), 2)
        assert budget.active == 0
    asyncio.run(scenario())


def test_source_replacement_discards_result_without_retargeting_original_store():
    async def scenario():
        ctx, budget, lane = owner()
        original = ctx.store
        def work():
            assert lane._store is original
            ctx.store = object()
            return 'not current'
        with pytest.raises(ReadActivityUnavailableError):
            async with lane.activity(work, deadline=time.monotonic() + 2):
                pytest.fail('foreign source yielded')
        lane.stop()
        await asyncio.wait_for(lane.wait_drained(), 2)
        assert budget.active == 0 and lane._store is original
    asyncio.run(scenario())


def test_queued_then_throw_retains_unknown_original_without_replay():
    async def scenario():
        _, budget, lane = owner()
        real = lane._pool
        started, release = threading.Event(), threading.Event()
        class LostReturn:
            calls = 0
            def submit(self, *args):
                self.calls += 1
                real.submit(*args)
                raise RuntimeError('synthetic lost return')
            def shutdown(self, **kwargs):
                real.shutdown(**kwargs)
        proxy = LostReturn()
        lane._pool = proxy
        def work():
            started.set()
            assert release.wait(3)
        try:
            with pytest.raises(ReadActivityUnavailableError):
                async with lane.activity(work, deadline=time.monotonic() + 2):
                    pytest.fail('uncertain submit yielded')
            await until(started.is_set)
            assert budget.active == 1 and proxy.calls == 1
            with pytest.raises(ReadActivityUnavailableError):
                async with lane.activity(lambda: None, deadline=time.monotonic() + 2):
                    pytest.fail('uncertain service replayed')
            lane.stop()
        finally:
            release.set()
            real.shutdown(wait=True)
        assert budget.active == 1 and len(lane._activities) == 1
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(lane.wait_drained(), .02)
    asyncio.run(scenario())


def test_callback_registration_failure_retains_the_bound_actual_future():
    async def scenario():
        _, budget, lane = owner()
        real = lane._pool
        class RegistrationFailure:
            def submit(self, *args):
                future = real.submit(*args)
                register = future.add_done_callback
                def fail(callback):
                    register(callback)
                    raise RuntimeError('synthetic uncertain registration')
                future.add_done_callback = fail
                return future
            def shutdown(self, **kwargs):
                real.shutdown(**kwargs)
        lane._pool = RegistrationFailure()
        with pytest.raises(ReadActivityUnavailableError):
            async with lane.activity(lambda: 1, deadline=time.monotonic() + 2):
                pytest.fail('unknown registration yielded')
        op = next(iter(lane._activities))
        await until(lambda: op.worker_done)
        assert op.future.done() and op.caller_done and op.unknown
        assert budget.active == 1 and lane.stop() == 1
        real.shutdown(wait=True)
    asyncio.run(scenario())


def test_duplicate_completion_and_ambiguous_release_cannot_refund_twice():
    async def scenario():
        _, budget, lane = owner()
        original_release = budget.release
        calls = []
        def fail_after_release(**kwargs):
            calls.append('release')
            original_release(**kwargs)
            raise RuntimeError('synthetic lost ledger return')
        budget.release = fail_after_release
        async with lane.activity(lambda: 1, deadline=time.monotonic() + 2):
            op = next(iter(lane._activities))
            await until(lambda: op.worker_done)
        assert budget.active == 0 and budget.poisoned and op.unknown
        lane._worker_ended(op, op.future)
        lane._retire(op)
        assert calls == ['release']
        assert not budget.reserve(operator=False) and not budget.reserve(operator=True)
        assert lane.stop() == 1
    asyncio.run(scenario())


def test_shared_operator_capacity_and_context_are_preserved():
    async def scenario():
        _, budget, lane = owner()
        assert budget.reserve(operator=True) and budget.reserve(operator=True)
        assert not budget.reserve(operator=True)
        async with lane.activity(lambda: True, deadline=time.monotonic() + 2):
            assert budget.active == 3 and budget.operator == 2
        await until(lambda: budget.active == 2)
        lane.stop()
        await lane.wait_drained()
        budget.release(operator=True)
        budget.release(operator=True)
        assert budget.active == 0
    asyncio.run(scenario())


def test_failed_retirement_marshal_retains_debt_and_fences_new_reads(monkeypatch):
    async def scenario():
        _, budget, lane = owner()
        loop = asyncio.get_running_loop()
        original = loop.call_soon_threadsafe
        def marshal(callback, *args, **kwargs):
            if callback == lane._worker_ended:
                raise RuntimeError('synthetic closed retirement route')
            return original(callback, *args, **kwargs)
        monkeypatch.setattr(loop, 'call_soon_threadsafe', marshal)
        try:
            with pytest.raises(ReadActivityUnavailableError):
                async with lane.activity(lambda: 1, deadline=time.monotonic() + 2):
                    pytest.fail('failed marshal yielded')
            assert budget.active == 1 and lane._marshal_failed.is_set()
            with pytest.raises(ReadActivityUnavailableError):
                async with lane.activity(lambda: 2, deadline=time.monotonic() + 2):
                    pytest.fail('failed service admitted another read')
            assert lane.stop() == 1
        finally:
            monkeypatch.setattr(loop, 'call_soon_threadsafe', original)
            lane._pool.shutdown(wait=True)
    asyncio.run(scenario())


def test_worker_cannot_wait_for_its_own_drain():
    async def scenario():
        _, budget, lane = owner()
        loop = asyncio.get_running_loop()
        def work():
            asyncio.run_coroutine_threadsafe(stop_and_wait(), loop).result(timeout=1)
        async def stop_and_wait():
            lane.stop()
            with pytest.raises(ReadActivityUnavailableError):
                await lane.wait_drained()
        with pytest.raises(ReadActivityUnavailableError):
            async with lane.activity(work, deadline=time.monotonic() + 2):
                pytest.fail('stopped service yielded')
        await asyncio.wait_for(lane.wait_drained(), 2)
        assert budget.active == 0
    asyncio.run(scenario())


def test_build_app_rejects_foreign_or_drifted_service_without_replacement(tmp_path):
    from hmp_plugin import server

    from .hmp_kit import Env
    async def scenario():
        first, second = Env(tmp_path / 'a'), Env(tmp_path / 'b')
        service = ReadinessReadService(first.ctx)
        first.ctx.readiness_reads = service
        second.ctx.readiness_reads = service
        copied = replace(first.ctx)
        assert copied.readiness_reads is None and first.ctx.readiness_reads is service
        try:
            with pytest.raises(RuntimeError, match='readiness owner unavailable'):
                server.build_app(second.ctx)
            assert second.ctx.readiness_reads is service and service.is_for(first.ctx)
            original = first.ctx.store
            first.ctx.store = second.ctx.store
            try:
                with pytest.raises(RuntimeError, match='readiness owner unavailable'):
                    server.build_app(first.ctx)
            finally:
                first.ctx.store = original
            service.stop()
            with pytest.raises(RuntimeError, match='readiness owner unavailable'):
                server.build_app(first.ctx)
            assert first.ctx.readiness_reads is service
        finally:
            service.stop()
            first.store.close()
            second.store.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('field,replacement', [('bridge', object()),
                                             ('readiness_generation', 'b' * 32)])
def test_bridge_or_generation_drift_cannot_retarget_or_revive_service(field, replacement):
    async def scenario():
        ctx, budget, lane = owner()
        original = getattr(ctx, field)
        setattr(ctx, field, replacement)
        assert not lane.is_for(ctx)
        with pytest.raises(ReadActivityUnavailableError):
            async with lane.activity(lambda: pytest.fail('foreign source ran'),
                                     deadline=time.monotonic() + 2):
                pytest.fail('foreign source yielded')
        setattr(ctx, field, original)
        assert not lane.is_for(ctx)
        with pytest.raises(ReadActivityUnavailableError):
            async with lane.activity(lambda: pytest.fail('retired source revived'),
                                     deadline=time.monotonic() + 2):
                pytest.fail('retired source yielded')
        lane.stop()
        await lane.wait_drained()
        assert budget.active == 0
    asyncio.run(scenario())
