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


def test_bootstrap_worker_preserves_original_context_without_leaking_worker_changes(adapter_module):
    import contextvars

    async def scenario():
        scope = contextvars.ContextVar("synthetic_bootstrap_scope", default=None)
        marker = object()
        scope.set(marker)
        adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
        ctx = SimpleNamespace(store=FakeStore())

        def components(_adapter):
            assert scope.get() is marker
            scope.set("synthetic worker-only value")
            return ctx

        opening = adapter_module.BootstrapOpening(components, adapter)
        adapter._opening = opening
        opening.start()
        assert await opening.wait() is ctx
        assert scope.get() is marker

    asyncio.run(scenario())


def partial_real_listener(adapter_module, monkeypatch, *, fail_close=False, block_site=False):
    from .test_listener_startup_ownership import rig

    listener, runner, events, entered, release = rig(
        monkeypatch, setup_error=not block_site, block_site=block_site
    )
    store = FakeStore(fail=fail_close)
    listener.ctx.store = store
    adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
    adapter._close_generation = lambda _ctx: events.append("generation-closed")
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: listener.ctx)
    monkeypatch.setattr(adapter_module.server, "HmpServer", lambda *_args, **_kwargs: listener)
    return adapter, listener, store, events, entered, release


@pytest.mark.parametrize("phase", ("migration", "identity", "configuration"))
@pytest.mark.parametrize("close_fails", (False, True))
def test_component_builder_failure_retains_store_and_attempts_close_once(
    adapter_module, monkeypatch, tmp_path, phase, close_fails
):
    from hmp_plugin.compat import CompatResult, CompatStatus

    store = FakeStore(fail=close_fails)

    def fail():
        raise ValueError("synthetic component failure")

    store.migrate = fail if phase == "migration" else lambda: None
    monkeypatch.setattr(adapter_module.compat, "default_gate", lambda: SimpleNamespace(
        evaluate=lambda: CompatResult(CompatStatus.UNSUPPORTED)))
    monkeypatch.setattr(adapter_module.identity, "resolve_custody",
                        lambda: SimpleNamespace(anchor_dir=tmp_path))
    monkeypatch.setattr(adapter_module, "Store", lambda _path: store)
    monkeypatch.setattr(adapter_module.identity, "load_or_create",
                        lambda _store: fail() if phase == "identity" else object())

    class ConfigurationFailure:
        @property
        def extra(self):
            return fail()

    adapter = SimpleNamespace(config=ConfigurationFailure())
    with pytest.raises((ValueError, OSError)):
        adapter_module.open_components(adapter)
    owner = adapter._component_store_owner
    assert owner.store is store and owner.attempted is True
    assert owner.closed is (not close_fails) and store.closes == 1
    with pytest.raises(RuntimeError, match="outcome unresolved"):
        owner.close_once()
    assert store.closes == 1


def partial_real_listener(adapter_module, monkeypatch, *, fail_close=False, block_site=False):
    from .test_listener_startup_ownership import rig

    listener, runner, events, entered, release = rig(
        monkeypatch, setup_error=not block_site, block_site=block_site
    )
    store = FakeStore(fail=fail_close)
    listener.ctx.store = store
    adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"port": 12345}))
    adapter._close_generation = lambda _ctx: events.append("generation-closed")
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: listener.ctx)
    monkeypatch.setattr(adapter_module.server, "HmpServer", lambda *_args, **_kwargs: listener)
    return adapter, listener, store, events, entered, release


def test_explicit_disconnect_recovers_actual_partial_listener_once(adapter_module, monkeypatch):
    async def scenario():
        adapter, listener, store, events, _, _ = partial_real_listener(adapter_module, monkeypatch)
        with pytest.raises(ConnectionError):
            await adapter.connect()
        opening = adapter._opening
        assert store.closes == 0 and adapter._startup_unresolved
        await adapter.disconnect()
        assert listener.closed.is_set() and events.count("cleanup") == 1
        assert store.closes == 1 and opening.closed and opening.close_attempted
        assert adapter._opening is None and adapter._retired_stores_ready()
        assert not adapter._startup_unresolved and not adapter._disconnect_unresolved
        await adapter.disconnect()
        assert store.closes == 1 and events.count("cleanup") == 1
        admitted = []

        def next_open(_adapter):
            admitted.append(True)
            raise adapter_module.identity.IdentityError("synthetic preallocation refusal")

        monkeypatch.setattr(adapter_module, "open_components", next_open)
        assert await adapter.connect() is False  # controlled refusal after actual reconnect admission
        assert admitted == [True] and adapter._opening is None

    asyncio.run(scenario())


def test_cancelled_partial_recovery_joins_same_listener_before_store_close(adapter_module,
                                                                         monkeypatch):
    async def scenario():
        adapter, listener, store, events, entered, release = partial_real_listener(
            adapter_module, monkeypatch, block_site=True
        )
        caller = asyncio.create_task(adapter.connect())
        await entered.wait()
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller
        opening = adapter._opening
        recovery = asyncio.create_task(adapter.disconnect())
        await asyncio.sleep(0)
        recovery.cancel()
        with pytest.raises(asyncio.CancelledError):
            await recovery
        assert adapter._opening is opening and store.closes == 0
        release.set()
        await adapter.disconnect()
        assert listener.closed.is_set() and events.count("cleanup") == 1 and store.closes == 1
        assert events.index("site-returned") < events.index("cleanup")
        assert not adapter._startup_unresolved and not adapter._disconnect_unresolved

    asyncio.run(scenario())


def test_real_store_migration_close_uncertainty_survives_component_cleanup(
    adapter_module, monkeypatch, tmp_path
):
    import sqlite3
    from hmp_plugin.compat import CompatResult, CompatStatus

    calls = []

    class Connection:
        def execute(self, *_args):
            raise ValueError("synthetic migration refusal")

        def close(self):
            calls.append("close")
            raise OSError("synthetic close acknowledgement loss")

    connection = Connection()
    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(adapter_module.compat, "default_gate", lambda: SimpleNamespace(
        evaluate=lambda: CompatResult(CompatStatus.UNSUPPORTED)))
    monkeypatch.setattr(adapter_module.identity, "resolve_custody",
                        lambda: SimpleNamespace(anchor_dir=tmp_path))
    adapter = SimpleNamespace(config=SimpleNamespace(extra={}))
    with pytest.raises(RuntimeError, match="Store close outcome unresolved"):
        adapter_module.open_components(adapter)
    owner = adapter._component_store_owner
    assert owner.attempted and not owner.closed
    assert owner.store._conn is connection
    assert owner.store._poisoned and owner.store._close_uncertain
    assert calls == ["close"]  # outer cleanup must not repeat migration's failed close


def test_identity_close_during_auxiliary_start_cannot_publish_connected(adapter_module, monkeypatch, tmp_path):
    from .hmp_kit import Env
    env = Env(tmp_path)
    adapter = adapter_module.HmpAdapter(SimpleNamespace(extra={"bind": "127.0.0.1", "port": 0}))
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)

    async def interrupted(srv, *_args):
        await srv.stop()  # real original stop invokes adapter's identity-close callback

    monkeypatch.setattr(adapter_module.server.HmpServer, "start_operator_read", interrupted)

    async def scenario():
        with pytest.raises(RuntimeError, match="startup ownership changed"):
            await adapter.connect()
        assert adapter._server is None and adapter._opening is not None
        assert adapter._startup_unresolved and "connected" not in adapter.states
        await adapter.disconnect()
        assert adapter._opening is None and adapter._retired_stores_ready()

    try:
        asyncio.run(scenario())
    finally:
        env.store.close()
