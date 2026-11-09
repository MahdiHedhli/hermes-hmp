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


@pytest.mark.parametrize("drift", ("context", "store", "generation_callback", "server_callback"))
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
        elif drift == "generation_callback":
            adapter._close_generation = lambda ctx: setattr(ctx, "store", foreign_store)
        else:
            adapter._close_generation = lambda _ctx: setattr(adapter, "_server", FakeServer(store))
        srv.drain.set()
        assert await owner.task is owner.failure
        assert not adapter._retired_stores_ready()
        assert store.closes == 0 and foreign_store.closes == 0
        assert await adapter.connect() is False

    asyncio.run(scenario())


def test_concurrent_component_opens_never_overlap(adapter_module, monkeypatch):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        entered, second, release = threading.Event(), threading.Event(), threading.Event()
        lock = threading.Lock()
        counts = {"calls": 0, "active": 0, "peak": 0}

        def open_components(_adapter):
            with lock:
                counts["calls"] += 1
                counts["active"] += 1
                counts["peak"] = max(counts["peak"], counts["active"])
                if counts["calls"] == 2:
                    second.set()
            entered.set()
            try:
                assert release.wait(3)
                raise adapter_module.identity.IdentityError("synthetic startup refusal")
            finally:
                with lock:
                    counts["active"] -= 1

        monkeypatch.setattr(adapter_module, "open_components", open_components)
        first = asyncio.create_task(adapter.connect())
        other = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            other = asyncio.create_task(adapter.connect())
            await asyncio.to_thread(second.wait, 0.1)
        finally:
            release.set()
            results = await asyncio.gather(first, *([other] if other is not None else []))
        # A completed failed attempt can be followed by a new attempt, never overlapped.
        assert results == [False, False] and counts["calls"] == 2
        assert counts["peak"] == 1

    asyncio.run(scenario())


def test_concurrent_successful_connects_open_one_actual_listener(
    adapter_module, tmp_path, monkeypatch
):
    import threading

    from .hmp_kit import Env
    from .test_adapter import _free_port

    async def scenario():
        env = Env(tmp_path)
        entered, release = threading.Event(), threading.Event()
        calls = []

        def components(_adapter):
            calls.append(1)
            entered.set()
            assert release.wait(3)
            return env.ctx

        monkeypatch.setattr(adapter_module, "open_components", components)
        adapter = adapter_module.HmpAdapter(
            SimpleNamespace(extra={"bind": "127.0.0.1", "port": _free_port()})
        )
        first = asyncio.create_task(adapter.connect())
        second = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            second = asyncio.create_task(adapter.connect())
            await asyncio.sleep(0)
            assert not second.done()
            release.set()
            assert await asyncio.gather(first, second) == [True, True]
            assert calls == [1] and adapter._server is not None
            assert adapter._server.bound is not None
        finally:
            release.set()
            await asyncio.gather(
                first, *([second] if second is not None else []), return_exceptions=True
            )
            await adapter.disconnect()

    asyncio.run(scenario())


def test_disconnect_waits_for_in_progress_component_startup(adapter_module, monkeypatch):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        entered, release = threading.Event(), threading.Event()

        def components(_adapter):
            entered.set()
            assert release.wait(3)
            raise adapter_module.identity.IdentityError("synthetic startup refusal")

        monkeypatch.setattr(adapter_module, "open_components", components)
        first = asyncio.create_task(adapter.connect())
        stop = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            stop = asyncio.create_task(adapter.disconnect())
            await asyncio.sleep(0)
            assert not stop.done()
            release.set()
            assert await first is False
            await stop
            assert adapter.states[-1] == "disconnected"
        finally:
            release.set()
            await asyncio.gather(
                first, *([stop] if stop is not None else []), return_exceptions=True
            )

    asyncio.run(scenario())


def test_cancelled_bootstrap_waiter_cannot_allow_overlapping_retry(adapter_module, monkeypatch):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        calls = []

        def components(_adapter):
            calls.append(1)
            entered.set()
            try:
                assert release.wait(3)
                raise adapter_module.identity.IdentityError("synthetic startup refusal")
            finally:
                finished.set()

        monkeypatch.setattr(adapter_module, "open_components", components)
        first = asyncio.create_task(adapter.connect())
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            assert adapter._startup_unresolved and not finished.is_set()
            assert await adapter.connect() is False and calls == [1]
            release.set()
            assert await asyncio.to_thread(finished.wait, 1)
            # This source slice cannot infer bootstrap resource cleanup from its
            # waiter; even fixture-observed worker end does not reset the latch.
            assert await adapter.connect() is False and calls == [1]
        finally:
            release.set()
            await asyncio.gather(first, return_exceptions=True)
            assert await asyncio.to_thread(finished.wait, 1)

    asyncio.run(scenario())


def test_cancelled_disconnect_never_reports_old_stopping_listener_connected(adapter_module):
    async def scenario():
        adapter, srv, store = fixture(adapter_module, debt=0)
        entered, release = asyncio.Event(), asyncio.Event()
        actual_stop = None

        async def stop(*, notify):
            nonlocal actual_stop
            assert notify is False
            if actual_stop is None:
                actual_stop = asyncio.create_task(release.wait())
            entered.set()
            await asyncio.shield(actual_stop)

        srv.stop = stop
        caller = asyncio.create_task(adapter.disconnect())
        try:
            await entered.wait()
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
            assert adapter._server is srv and adapter._disconnect_unresolved
            assert actual_stop is not None and not actual_stop.done()
            assert await adapter.connect() is False
            release.set()
            await actual_stop
            assert await adapter.connect() is False  # stop completion is not Store-close proof
            srv.drain.set()
            await adapter.disconnect()  # explicitly resume the same stop owner, then close once
            assert store.closes == 1 and not adapter._disconnect_unresolved
            assert adapter._server is None and adapter._retired_stores_ready()
        finally:
            release.set()
            await asyncio.gather(caller, return_exceptions=True)
            if actual_stop is not None:
                await actual_stop

    asyncio.run(scenario())


def test_cancelled_wait_for_lifecycle_lock_does_not_poison_disconnect(adapter_module):
    async def scenario():
        adapter, srv, store = fixture(adapter_module)
        await adapter._lifecycle_lock.acquire()
        caller = asyncio.create_task(adapter.disconnect())
        try:
            await asyncio.sleep(0)
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
            assert not adapter._disconnect_unresolved and not adapter._startup_unresolved
            assert srv.stops == 0 and store.closes == 0
        finally:
            adapter._lifecycle_lock.release()

    asyncio.run(scenario())


def test_failed_disconnect_does_not_return_connected_for_retained_old_server(adapter_module):
    async def scenario():
        adapter, srv, store = fixture(adapter_module, debt=0)

        async def failed_stop(*, notify):
            assert notify is False
            raise RuntimeError("synthetic unresolved stop completion")

        srv.stop = failed_stop
        with pytest.raises(RuntimeError, match="unresolved stop"):
            await adapter.disconnect()
        assert adapter._disconnect_unresolved and adapter._server is srv
        assert await adapter.connect() is False and store.closes == 0

    asyncio.run(scenario())


def test_failed_bootstrap_cannot_automatically_start_another_attempt(adapter_module, monkeypatch):
    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        calls = []

        def failed_open(_adapter):
            calls.append(1)
            raise OSError("synthetic unresolved bootstrap failure")

        monkeypatch.setattr(adapter_module, "open_components", failed_open)
        with pytest.raises(OSError):
            await adapter.connect()
        assert adapter._startup_unresolved
        assert await adapter.connect() is False and calls == [1]

    asyncio.run(scenario())


def test_cancelled_open_retains_actual_future_and_explicit_cleanup_closes_unpublished_store(
    adapter_module, monkeypatch
):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        adapter._close_generation = lambda _ctx: None
        entered, release = threading.Event(), threading.Event()
        store, calls = FakeStore(), []
        ctx = SimpleNamespace(store=store)

        def components(_adapter):
            calls.append(1)
            entered.set()
            assert release.wait(3)
            return ctx

        monkeypatch.setattr(adapter_module, "open_components", components)
        caller = asyncio.create_task(adapter.connect())
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
            opening = adapter._opening
            assert opening.future is not None and not opening.future.done()
            assert not opening.future.cancelled() and store.closes == 0
            assert await adapter.connect() is False and calls == [1]
            cleanup = asyncio.create_task(adapter.disconnect())
            await asyncio.sleep(0)
            assert not cleanup.done() and store.closes == 0
            release.set()
            await cleanup
            assert opening.future.done() and opening.ctx is ctx and opening.closed
            assert store.closes == 1 and adapter._opening is None
            assert not adapter._startup_unresolved and not adapter._disconnect_unresolved
        finally:
            release.set()
            await asyncio.gather(caller, return_exceptions=True)

    asyncio.run(scenario())


def test_unpublished_close_return_loss_is_never_replayed(adapter_module, monkeypatch):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        adapter._close_generation = lambda _ctx: None
        entered, release = threading.Event(), threading.Event()
        store = FakeStore(fail=True)

        def components(_adapter):
            entered.set()
            assert release.wait(3)
            return SimpleNamespace(store=store)

        monkeypatch.setattr(adapter_module, "open_components", components)
        caller = asyncio.create_task(adapter.connect())
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
            opening = adapter._opening
            release.set()
            with pytest.raises(OSError):
                await adapter.disconnect()
            assert opening.close_attempted and store.closes == 1 and not opening.closed
            with pytest.raises(RuntimeError):
                await adapter.disconnect()
            assert store.closes == 1 and await adapter.connect() is False
        finally:
            release.set()
            await asyncio.gather(caller, return_exceptions=True)

    asyncio.run(scenario())


def test_unknown_bootstrap_submit_keeps_returned_context_but_cannot_claim_cleanup(
    adapter_module, monkeypatch
):
    import threading

    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        store, release, actual = FakeStore(), threading.Event(), []

        def components(_adapter):
            assert release.wait(3)
            return SimpleNamespace(store=store)

        original_start = adapter_module.BootstrapOpening.start

        def start(owner):
            submit = owner.pool.submit

            def lost_ack(*args, **kwargs):
                actual.append(submit(*args, **kwargs))
                raise MemoryError("synthetic bootstrap enqueue acknowledgement loss")

            monkeypatch.setattr(owner.pool, "submit", lost_ack)
            return original_start(owner)

        monkeypatch.setattr(adapter_module, "open_components", components)
        monkeypatch.setattr(adapter_module.BootstrapOpening, "start", start)
        try:
            with pytest.raises(RuntimeError, match="retain original resources"):
                await adapter.connect()
            opening = adapter._opening
            assert opening is not None and opening.future is None
            assert await adapter.connect() is False and len(actual) == 1
            release.set()
            ctx = await asyncio.wrap_future(actual[0])
            assert opening.ctx is ctx and opening.store is store
            with pytest.raises(RuntimeError):
                await adapter.disconnect()
            assert store.closes == 0 and adapter._opening is opening
        finally:
            release.set()
            if actual:
                await asyncio.wrap_future(actual[0])
            adapter._opening.pool.shutdown(wait=False, cancel_futures=False)

    asyncio.run(scenario())


@pytest.mark.parametrize("replacement", ("close", "cohort"))
def test_unpublished_cleanup_cannot_follow_callback_replacement_fields(adapter_module, replacement):
    async def scenario():
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        original_store, foreign_store = FakeStore(), FakeStore()
        original_ctx = SimpleNamespace(store=original_store)
        opening = adapter_module.BootstrapOpening(lambda _adapter: original_ctx, adapter)
        adapter._opening = opening
        opening.start()
        assert await opening.wait() is original_ctx

        def change(_ctx):
            opening.close = foreign_store.close
            if replacement == "cohort":
                opening.ctx = SimpleNamespace(store=foreign_store)
                opening.store = foreign_store

        adapter._close_generation = change
        with pytest.raises(RuntimeError, match="retain original resources"):
            opening.close_unpublished(adapter)
        assert original_store.closes == 0 and foreign_store.closes == 0
        assert opening.close_attempted and not opening.closed

    asyncio.run(scenario())
