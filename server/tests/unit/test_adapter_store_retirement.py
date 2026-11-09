"""Original adapter Store ownership under synthetic drain/close faults; no live host."""

import asyncio
from types import SimpleNamespace

import pytest

from .test_adapter import adapter_module as adapter_module


class FakeStore:
    def __init__(self, *, fail=False):
        self.closes = 0
        self.fail = fail

    def close(self):
        self.closes += 1
        if self.fail:
            raise OSError("synthetic private close acknowledgement loss")


class FakeServer:
    def __init__(self, store, debt=1):
        self.ctx = SimpleNamespace(store=store)
        self.operator_worker_debt = debt
        self.drain = asyncio.Event()
        self.stops = 0

    async def stop(self, *, notify):
        assert notify is False
        self.stops += 1

    async def wait_operator_drain(self):
        await self.drain.wait()


def fixture(adapter_module, *, debt=1, fail_close=False):
    adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
    adapter._close_generation = lambda _ctx: None
    store = FakeStore(fail=fail_close)
    srv = FakeServer(store, debt)
    adapter._server = srv
    return adapter, srv, store


def test_pending_original_owner_blocks_connect_before_open_components(adapter_module, monkeypatch):
    async def scenario():
        adapter, srv, store = fixture(adapter_module)
        opened = []
        monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: opened.append(True))
        await adapter.disconnect()
        owner = adapter._retiring_stores[id(srv)]
        assert adapter._server is None and store.closes == 0
        assert await adapter.connect() is False and opened == []
        assert not owner.task.done()
        srv.drain.set()
        assert await owner.task is owner.completion
        assert store.closes == 1 and adapter._retired_stores_ready()
        assert not adapter._retiring_stores
        await adapter.disconnect()
        assert store.closes == 1

    asyncio.run(scenario())


def test_cancelled_disconnect_waiter_does_not_cancel_actual_close_owner(adapter_module):
    async def scenario():
        adapter, srv, store = fixture(adapter_module, debt=0)
        caller = asyncio.create_task(adapter.disconnect())
        await asyncio.sleep(0)
        owner = adapter._retiring_stores[id(srv)]
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller
        assert not owner.task.done() and not adapter._retired_stores_ready()
        assert store.closes == 0
        srv.drain.set()
        assert await owner.task is owner.completion
        assert store.closes == 1 and adapter._retired_stores_ready()

    asyncio.run(scenario())


@pytest.mark.parametrize("after_schedule", (False, True))
def test_unknown_creation_retains_listener_and_coro_without_automatic_replay(
    adapter_module, monkeypatch, after_schedule
):
    async def scenario():
        adapter, srv, store = fixture(adapter_module)
        original, calls, actual = asyncio.create_task, [], []

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) != "_retire_owned_store":
                return original(coro, *args, **kwargs)
            calls.append(1)
            if after_schedule:
                actual.append(original(coro, *args, **kwargs))
            raise MemoryError("synthetic creation acknowledgement loss")

        monkeypatch.setattr(asyncio, "create_task", create)
        try:
            with pytest.raises(RuntimeError, match="retain original listener"):
                await adapter.disconnect()
            owner = adapter._retiring_stores[id(srv)]
            assert owner.server is srv and owner.store is store and owner.coro is not None
            assert owner.task is None and adapter._server is srv
            assert await adapter.connect() is False
            with pytest.raises(RuntimeError, match="retain original listener"):
                await adapter.disconnect()
            assert len(calls) == 1 and store.closes == 0
            if after_schedule:
                srv.drain.set()
                assert await actual[0] is owner.completion
                assert store.closes == 1
            assert not adapter._retired_stores_ready()
        finally:
            if not after_schedule:
                # The fault injector, unlike production, knows scheduling was never called.
                adapter._retiring_stores[id(srv)].coro.close()

    asyncio.run(scenario())


def test_close_return_loss_never_replays_or_unblocks_connect(adapter_module):
    async def scenario():
        adapter, srv, store = fixture(adapter_module, fail_close=True)
        errors = []
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: errors.append(context))
        try:
            await adapter.disconnect()
            owner = adapter._retiring_stores[id(srv)]
            srv.drain.set()
            assert await owner.task is owner.failure
            assert store.closes == 1 and not adapter._retired_stores_ready()
            assert await adapter.connect() is False
            await adapter.disconnect()
            assert store.closes == 1 and errors == []
        finally:
            loop.set_exception_handler(None)

    asyncio.run(scenario())


@pytest.mark.parametrize("drift", ("context", "store", "generation_callback"))
def test_old_retirement_never_closes_foreign_context_store(adapter_module, drift):
    async def scenario():
        adapter, srv, store = fixture(adapter_module)
        original_ctx, foreign_store = srv.ctx, FakeStore()
        await adapter.disconnect()
        owner = adapter._retiring_stores[id(srv)]
        if drift == "context":
            srv.ctx = SimpleNamespace(store=foreign_store)
        elif drift == "store":
            original_ctx.store = foreign_store
        else:
            adapter._close_generation = lambda ctx: setattr(ctx, "store", foreign_store)
        srv.drain.set()
        assert await owner.task is owner.failure
        assert not adapter._retired_stores_ready()
        assert store.closes == 0 and foreign_store.closes == 0
        assert await adapter.connect() is False

    asyncio.run(scenario())
