"""Real listener/adapter, synthetic temporary Store; no owner home or device."""
import asyncio
import threading
import time

import pytest

from hmp_plugin.readiness_work import ReadActivityUnavailableError

from .hmp_kit import Env
from .test_adapter import _Config, _free_port
from .test_adapter import adapter_module as adapter_module


async def until(predicate):
    for _ in range(400):
        if predicate():
            return
        await asyncio.sleep(.005)
    raise AssertionError('bounded lifecycle condition absent')


@pytest.mark.parametrize('reason', ['disconnect', 'identity', 'failed_start'])
@pytest.mark.parametrize('half', ['worker', 'caller'])
def test_adapter_keeps_original_store_and_blocks_reconnect_until_both_ends(
    adapter_module, tmp_path, monkeypatch, reason, half,
):
    env = Env(tmp_path)
    monkeypatch.setattr(adapter_module, 'open_components', lambda _: env.ctx)
    adapter = adapter_module.HmpAdapter(_Config({'bind': '127.0.0.1', 'port': _free_port()}))
    entered, release_worker = threading.Event(), threading.Event()
    closed = []
    original_close = env.store.close
    monkeypatch.setattr(env.store, 'close', lambda: (closed.append(True), original_close())[-1])

    async def scenario():
        release_caller = asyncio.Event()
        caller_entered = asyncio.Event()
        reads = []
        listeners = []
        async def read(lane):
            def work():
                if half == 'worker':
                    entered.set()
                    assert release_worker.wait(5)
                return 1
            try:
                async with lane.activity(work, deadline=time.monotonic() + 3):
                    caller_entered.set()
                    await release_caller.wait()
            except ReadActivityUnavailableError:
                # stop won while worker was in flight; no response is published.
                pass
        async def begin(listener):
            listeners.append(listener)
            reads.append(asyncio.create_task(read(listener.ctx.readiness_reads)))
            await until(entered.is_set if half == 'worker' else caller_entered.is_set)
        async def fail_start(listener, _ctx):
            await begin(listener)
            raise RuntimeError('synthetic post-start failure')
        try:
            if reason == 'failed_start':
                monkeypatch.setattr(adapter, '_finish_connect', fail_start)
                with pytest.raises(ConnectionError, match="HMP listener did not start"):
                    await adapter.connect()
            else:
                assert await adapter.connect()
                listener = adapter._server
                await begin(listener)
                if reason == 'disconnect':
                    await adapter.disconnect()
                else:
                    listener._identity_changed()
                    await asyncio.wait_for(listener.closed.wait(), 5)
            listener = listeners[0]
            assert listener.readiness_worker_debt == 1
            assert env.ctx.read_worker_budget.active == 1
            assert not closed
            assert adapter._readiness_dependency_closers
            assert not await adapter.connect()  # cannot replace the outstanding owner
            assert not closed
        finally:
            release_worker.set()
            release_caller.set()
            if reads:
                await asyncio.gather(*reads)
            await until(lambda: not adapter._dependency_closers)
            if adapter._server is not None:
                await adapter.disconnect()
        assert closed == [True]
        assert env.ctx.read_worker_budget.active == 0
        assert not adapter._readiness_dependency_closers
    asyncio.run(scenario())
