"""Real adapter/server/Store/TLS lifecycle, synthetic native bridge/platform API.

No actual GatewayRunner, installed host, provider, decoder or device pass follows.
"""

import asyncio
import hashlib
import shutil
import sys
import tempfile
import threading
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import ClientSession, Fingerprint, web

from hmp_plugin import server
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.presentation_native_service import (
    NativePresentationOwner,
    NativePresentationUnavailableError,
)
from hmp_plugin.wire import b64u_encode

from .hmp_kit import Env
from .test_adapter import _free_port
from .test_adapter import adapter_module as adapter_module
from .test_presentation_native_service import env as env
from .test_presentation_native_service import until


@pytest.fixture
def native(env, tmp_path):
    # Native Unix socket paths must fit the actual platform limit. Use a short,
    # exclusively created private fixture root rather than a test-name path.
    temp_root = "/private/tmp" if sys.platform == "darwin" else tempfile.gettempdir()
    identity_root = Path(tempfile.mkdtemp(prefix="hl-", dir=str(Path(temp_root).resolve())))
    tls = Env(identity_root)
    # The operator socket lives beside instance/, whose private parent is part
    # of its native contract. Set only this newly owned synthetic directory.
    tls.identity.custody.anchor_dir.parent.chmod(0o700)
    old = env.ctx
    env.iid = tls.iid
    token = b"B" * 32
    env.authorization = "Bearer " + b64u_encode(token)
    env.store.insert_access_token(
        hashlib.sha256(token).digest(), "family", "device", env.iid, 100000
    )
    env.ctx = server.ServerContext(
        identity=tls.identity,
        store=env.store,
        compat=CompatResult(CompatStatus.SUPPORTED),
        bridge=old.bridge,
        clock=old.now,
        reads=SimpleNamespace(roster=lambda user_id: {"bots": []}),
    )
    env.pin = Fingerprint(hashlib.sha256(tls.identity.certificate_der()).digest())
    env.headers = {"Authorization": env.authorization, "HMP-Instance": env.iid}
    try:
        yield env
    finally:
        tls.store.close()
        shutil.rmtree(identity_root)


def register(native, listener):
    service = listener._presentation_service
    assert service is not None
    if service not in native.services:
        native.services.append(service)
    return service


def adapter_for(native, adapter_module, monkeypatch):
    monkeypatch.setattr(adapter_module, "open_components", lambda adapter: native.ctx)
    return adapter_module.HmpAdapter(
        SimpleNamespace(extra={"bind": "127.0.0.1", "port": _free_port()})
    )


def block_home(native):
    entered, release = threading.Event(), threading.Event()

    def gate(profile):
        entered.set()
        assert release.wait(12)

    native.gate = gate
    return entered, release


@pytest.mark.asyncio
async def test_immediate_reconnect_cannot_report_identity_fenced_listener_connected(
    native, adapter_module, monkeypatch
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    assert await adapter.connect()
    listener = adapter._server
    service = register(native, listener)
    try:
        listener._identity_changed()
        assert listener._stopping is not None and listener._stop_owner is None
        # No loop yield between the fence and this completed uncontended call:
        # the identity task has not yet assigned the stop owner.
        assert await adapter.connect() is False
        assert listener._stop_owner is None and adapter._presentation_owner._service is service
        await asyncio.wait_for(listener.closed.wait(), 3)
    finally:
        await listener.stop(notify=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["setup", "purge", "site", "push"])
async def test_stop_joins_cancellation_resistant_actual_startup_before_runner_cleanup(
    native, monkeypatch, phase
):
    owner = NativePresentationOwner()
    listener = server.HmpServer(
        native.ctx, server.ListenerSettings("127.0.0.1", 0), presentation_owner=owner
    )
    entered, cancelled, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []
    runner_type = server._HmpAppRunner
    actual_setup, actual_cleanup = runner_type.setup, runner_type.cleanup
    actual_site = server.web.TCPSite.start
    actual_purge, actual_push = listener._purge_push_once, listener._start_push_dispatcher

    async def delayed(action):
        entered.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.set()
            await release.wait()
        await action()

    class ObservedRunner(runner_type):
        async def setup(self):
            if phase == "setup":
                await delayed(lambda: actual_setup(self))
            else:
                await actual_setup(self)

        async def cleanup(self):
            calls.append(True)
            await actual_cleanup(self)

    async def site_start(site):
        await delayed(lambda: actual_site(site))

    monkeypatch.setattr(server, "_HmpAppRunner", ObservedRunner)
    if phase == "site":
        monkeypatch.setattr(server.web.TCPSite, "start", site_start)
    if phase == "purge":
        monkeypatch.setattr(listener, "_purge_push_once", lambda: delayed(actual_purge))
    if phase == "push":
        monkeypatch.setattr(listener, "_start_push_dispatcher", lambda: delayed(actual_push))
    starting = asyncio.create_task(listener.start())
    stopping = None
    try:
        await asyncio.wait_for(entered.wait(), 3)
        stopping = asyncio.create_task(listener.stop(notify=False))
        await asyncio.wait_for(cancelled.wait(), 3)
        assert not stopping.done() and not calls and owner._service is None
        assert native.store.get_device("device") is not None
        release.set()
        with pytest.raises(ConnectionError):
            await starting
        await asyncio.wait_for(stopping, 3)
        assert calls == [True] and listener._runner is None and listener.closed.is_set()
        assert owner._service is None and not listener._presentation_live.is_set()
    finally:
        release.set()
        if stopping is not None:
            await asyncio.wait_for(asyncio.shield(stopping), 3)


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["stop", "identity"])
async def test_stopped_during_native_push_setup_cannot_bind_a_late_pool(
    native, monkeypatch, reason
):
    owner = NativePresentationOwner()
    listener = server.HmpServer(
        native.ctx, server.ListenerSettings("127.0.0.1", 0), presentation_owner=owner
    )
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_setup():
        entered.set()
        await release.wait()

    monkeypatch.setattr(listener, "_start_push_dispatcher", paused_setup)
    task = asyncio.create_task(listener.start())
    try:
        await asyncio.wait_for(entered.wait(), 3)
        if reason == "identity":
            listener._identity_changed()
            await asyncio.wait_for(listener.closed.wait(), 3)
        else:
            await listener.stop(notify=False)
        release.set()
        with pytest.raises((ConnectionError, asyncio.CancelledError)):
            await task
        assert owner._service is None and listener._presentation_service is None
        assert not listener._presentation_live.is_set()
        assert native.store.get_device("device") is not None
    finally:
        release.set()
        await listener.stop(notify=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["operator", "approval"])
async def test_identity_close_during_final_setup_cannot_publish_connected_or_close_twice(
    native, adapter_module, monkeypatch, phase
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()
    method = "start_operator_read" if phase == "operator" else "start_approval_test"
    original = getattr(server.HmpServer, method)
    listeners, closed = [], []
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])

    async def paused(listener, *args):
        await original(listener, *args)
        listeners.append(listener)
        register(native, listener)
        entered.set()
        await release.wait()

    monkeypatch.setattr(server.HmpServer, method, paused)
    task = asyncio.create_task(adapter.connect())
    try:
        await asyncio.wait_for(entered.wait(), 3)
        listener = listeners[0]
        listener._identity_changed()
        await asyncio.wait_for(listener.closed.wait(), 3)
        release.set()
        with pytest.raises(ConnectionError):
            await task
        assert "connected" not in adapter.states and adapter._server is None
        assert closed == [True] and listener._dependencies_closed
        assert adapter._presentation_owner._service.drained
    finally:
        release.set()
        if adapter._server is not None:
            await adapter.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("second_action", ["connect", "disconnect"])
async def test_component_start_is_serialized_with_connect_and_disconnect(
    native, adapter_module, monkeypatch, second_action
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    entered, release = threading.Event(), threading.Event()
    second_entered = asyncio.Event()
    calls = []

    def components(instance):
        calls.append(instance)
        entered.set()
        assert release.wait(8)
        return native.ctx

    monkeypatch.setattr(adapter_module, "open_components", components)
    first = asyncio.create_task(adapter.connect())
    await until(entered.is_set)

    async def second():
        second_entered.set()
        return await (adapter.connect() if second_action == "connect" else adapter.disconnect())

    other = asyncio.create_task(second())
    try:
        await second_entered.wait()
        assert calls == [adapter] and not other.done()
        release.set()
        result = await asyncio.gather(first, other)
        assert result[0] is True and calls == [adapter]
        if second_action == "connect":
            assert result[1] is True and adapter.states.count("connected") == 1
            register(native, adapter._server)
        else:
            assert result[1] is None and adapter._server is None
            assert adapter._presentation_owner._service.drained
    finally:
        release.set()
        if adapter._server is not None:
            await adapter.disconnect()


@pytest.mark.asyncio
async def test_old_listener_callback_cannot_retire_a_new_current_listener(
    native, adapter_module, monkeypatch
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    owner = adapter._presentation_owner
    old = server.HmpServer(
        native.ctx, server.ListenerSettings("127.0.0.1", 0), presentation_owner=owner
    )
    await old.start()
    register(native, old)
    await old.stop(notify=False)
    ctx = replace(native.ctx, presentation_service=None, presentation_available=lambda: False)
    current = server.HmpServer(
        ctx, server.ListenerSettings("127.0.0.1", 0), presentation_owner=owner
    )
    try:
        await current.start()
        register(native, current)
        adapter._server = current
        adapter._listener_closed(old)
        assert adapter._server is current and current._presentation_current()
        assert not current.closed.is_set() and not adapter.states
        assert native.store.get_device("device") is not None
    finally:
        await adapter.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["error", "cancel"])
async def test_partial_native_runner_cleanup_is_retained_without_replay(
    native, adapter_module, monkeypatch, failure
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    actual_runner = server._HmpAppRunner
    calls, closed = [], []
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])

    class PartialCleanup(actual_runner):
        async def setup(self):
            await super().setup()
            raise RuntimeError("synthetic failure after native setup")

        async def cleanup(self):
            calls.append(True)
            await super().cleanup()
            if failure == "cancel":
                raise asyncio.CancelledError()
            raise RuntimeError("synthetic lost native cleanup acknowledgement")

    monkeypatch.setattr(server, "_HmpAppRunner", PartialCleanup)
    with pytest.raises(asyncio.CancelledError if failure == "cancel" else ConnectionError):
        await adapter.connect()
    listener = adapter._failed_start_server
    assert listener._runner is not None and listener._runner_cleanup_unknown
    assert adapter._start_cleanup_task.done()
    assert adapter._start_cleanup_task.exception() is not None
    assert calls == [True] and not closed
    assert await adapter.connect() is False
    assert native.store.get_device("device") is not None
    monkeypatch.setattr(native.store, "close", actual_close)


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["disconnect", "identity"])
async def test_actual_adapter_retains_store_and_capacity_through_held_writer_exporter(
    native, adapter_module, monkeypatch, reason
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    held, closed = [], []
    written = asyncio.Event()
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])

    class HoldingResponse(web.StreamResponse):
        async def write(self, data):
            held.append(data)
            await super().write(data)
            written.set()
            await asyncio.Future()

    try:
        assert await adapter.connect()
        listener = adapter._server
        service = register(native, listener)
        service._response_type = HoldingResponse
        async with ClientSession() as client:
            response = await client.get(
                f"https://127.0.0.1:{listener.bound[1]}/hmp/v1/bots/belac/presentation",
                headers=native.headers,
                ssl=native.pin,
            )
            await asyncio.wait_for(written.wait(), 3)
            op = next(iter(service._ops.values()))
            if reason == "disconnect":
                await adapter.disconnect()
            else:
                listener._identity_changed()
                await asyncio.wait_for(listener.closed.wait(), 6)
            assert op.writer.task.done() and not op.writer.settled
            assert op.writer._chunk_ref() is held[0].obj
            assert op.result is not None and op.memory.snapshot()[0] > 0
            assert listener.presentation_worker_debt and not closed
            assert native.store.get_device("device") is not None
            held.pop().release()
            await until(lambda: not adapter._dependency_closers)
            assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
            assert service.drained and closed == [True]
            response.close()
    finally:
        for view in held:
            view.release()
        held.clear()
        if adapter._server is not None:
            await adapter.disconnect()


@pytest.mark.asyncio
async def test_unknown_worker_start_keeps_generation_and_cancelled_closer_blocks_reset(
    native, adapter_module, monkeypatch
):
    """No actual thread starts; fixture disposal is not a production drain proof."""
    adapter = adapter_for(native, adapter_module, monkeypatch)
    closed = []
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])

    class UnknownStart(threading.Thread):
        def start(self):
            raise RuntimeError("synthetic ambiguous native start acknowledgement")

    assert await adapter.connect()
    listener = adapter._server
    service = register(native, listener)
    service._thread_type = UnknownStart
    handle = service.submit(native.authorization, native.iid, "belac")
    await adapter.disconnect()
    op = service._ops[handle]
    assert op.start_uncertain and not op.entered and not op.worker.is_alive()
    assert not service.drained and listener.presentation_worker_debt and not closed
    with pytest.raises(NativePresentationUnavailableError, match="previous_generation_not_drained"):
        adapter._presentation_owner.bind(
            native.ctx, current=lambda: True, worker_current=lambda: True
        )
    closer = next(iter(adapter._dependency_closers))
    closer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closer
    assert await adapter.connect() is False
    assert closer in adapter._dependency_closers and not closed
    assert native.store.get_device("device") is not None
    monkeypatch.setattr(native.store, "close", actual_close)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["disconnect", "identity"])
@pytest.mark.parametrize("failure", ["generation", "store"])
async def test_uncertain_synchronous_dependency_close_is_retained_and_never_replayed(
    native, adapter_module, monkeypatch, route, failure
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    assert await adapter.connect()
    listener = adapter._server
    register(native, listener)
    calls = []
    actual_generation = adapter._close_generation
    actual_store = native.store.close

    def generation(ctx):
        calls.append("generation")
        actual_generation(ctx)
        if failure == "generation":
            raise RuntimeError("synthetic partial generation close")

    def store():
        calls.append("store")
        actual_store()
        raise RuntimeError("synthetic lost store close acknowledgement")

    monkeypatch.setattr(adapter, "_close_generation", generation)
    monkeypatch.setattr(native.store, "close", store if failure == "store" else actual_store)
    if route == "disconnect":
        with pytest.raises(RuntimeError):
            await adapter.disconnect()
    else:
        listener._identity_changed()
        await asyncio.wait_for(listener.closed.wait(), 3)
        await asyncio.shield(listener._stop_owner)
    assert adapter._dependency_close_unknown is listener and adapter._server is None
    assert await adapter.connect() is False
    await adapter.disconnect()
    assert calls == (["generation"] if failure == "generation" else ["generation", "store"])
    monkeypatch.setattr(native.store, "close", actual_store)


@pytest.mark.asyncio
async def test_actual_server_start_capability_tls_delivery_stop_and_retained_owner_rebind(native):
    owner = NativePresentationOwner()
    ctx = native.ctx
    previous = None
    for _ in range(2):
        listener = server.HmpServer(
            ctx, server.ListenerSettings("127.0.0.1", 0), presentation_owner=owner
        )
        try:
            await listener.start()
            service = register(native, listener)
            assert service is owner._service and service is not previous
            assert listener._presentation_current() and service.available
            port = listener.bound[1]
            async with ClientSession() as client:
                async with client.get(
                    f"https://127.0.0.1:{port}/hmp/v1/bots", headers=native.headers, ssl=native.pin
                ) as response:
                    assert response.status == 200
                    assert (await response.json())["capabilities"]["bot_presentation"] == 1
                async with client.get(
                    f"https://127.0.0.1:{port}/hmp/v1/bots/belac/presentation",
                    headers=native.headers,
                    ssl=native.pin,
                ) as response:
                    assert response.status == 200
                    assert (await response.json())["display_name"] == "Synthetic native fixture"
        finally:
            await listener.stop(notify=False)
        assert not listener._presentation_live.is_set()
        assert service.drained and not listener.presentation_worker_debt
        await listener.wait_presentation_drain()
        previous = service
        ctx = replace(ctx, presentation_service=None, presentation_available=lambda: False)


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["disconnect", "identity"])
async def test_actual_adapter_keeps_store_until_blocked_native_worker_really_joins(
    native, adapter_module, monkeypatch, reason
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    entered, release = block_home(native)
    closed = []
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])
    try:
        assert await adapter.connect()
        listener = adapter._server
        service = register(native, listener)
        handle = service.submit(native.authorization, native.iid, "belac")
        await until(entered.is_set)
        op = service._ops[handle]
        if reason == "disconnect":
            await adapter.disconnect()
        else:
            listener._identity_changed()
            await asyncio.wait_for(listener.closed.wait(), 6)
        assert not listener._presentation_live.is_set() and listener.presentation_worker_debt
        assert not closed and native.store.get_device("device") is not None
        assert op.worker.is_alive() and adapter._dependency_closers
        with pytest.raises(
            NativePresentationUnavailableError, match="previous_generation_not_drained"
        ):
            adapter._presentation_owner.bind(
                native.ctx, current=lambda: True, worker_current=lambda: True
            )
        release.set()
        await until(lambda: not adapter._dependency_closers)
        assert service.drained and not op.worker.is_alive() and closed == [True]
    finally:
        release.set()
        if adapter._server is not None:
            await adapter.disconnect()
        await until(
            lambda: all(
                not op.worker or not op.worker.is_alive()
                for s in native.services
                for op in s._ops.values()
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        "exception",
        "cancel",
        "double_cancel",
        "finish_exception",
        "finish_cancel",
        "operator_cancel",
    ],
)
async def test_failed_or_cancelled_start_adopts_listener_and_defers_dependency_close(
    native, adapter_module, monkeypatch, failure
):
    adapter = adapter_for(native, adapter_module, monkeypatch)
    entered, release = block_home(native)
    bound = asyncio.Event()
    original_start = server.HmpServer.start
    closed = []
    actual_close = native.store.close
    monkeypatch.setattr(native.store, "close", lambda: (closed.append(True), actual_close())[-1])

    async def fail_after_binding(listener):
        await original_start(listener)
        service = register(native, listener)
        service.submit(native.authorization, native.iid, "belac")
        await until(entered.is_set)
        if failure.startswith("finish_") or failure == "operator_cancel":
            return
        bound.set()
        if failure == "exception":
            raise RuntimeError("synthetic post-bind startup failure")
        await asyncio.Future()

    async def fail_finish(listener, ctx):
        adapter._server = listener
        bound.set()
        if failure == "finish_exception":
            raise RuntimeError("synthetic final setup failure")
        await asyncio.Future()

    original_operator = server.HmpServer.start_operator_read

    async def hold_operator(listener, anchor, nonce):
        await original_operator(listener, anchor, nonce)
        bound.set()
        await asyncio.Future()

    monkeypatch.setattr(server.HmpServer, "start", fail_after_binding)
    if failure.startswith("finish_"):
        monkeypatch.setattr(adapter, "_finish_connect", fail_finish)
    if failure == "operator_cancel":
        monkeypatch.setattr(server.HmpServer, "start_operator_read", hold_operator)
    task = asyncio.create_task(adapter.connect())
    try:
        await asyncio.wait_for(bound.wait(), 3)
        cancelling = failure.endswith("cancel")
        if cancelling:
            task.cancel()
            if failure == "double_cancel":
                await until(lambda: adapter._start_cleanup_task is not None)
                task.cancel()
        with pytest.raises(asyncio.CancelledError if cancelling else ConnectionError):
            await task
        assert not closed and adapter._failed_start_server is not None
        if failure == "double_cancel":
            assert not adapter._start_cleanup_task.done()
            assert await adapter.connect() is False
        await until(lambda: adapter._start_cleanup_task.done())
        assert adapter._start_cleanup_task.exception() is None
        assert adapter._server is None
        if failure == "operator_cancel":
            operator = adapter._failed_start_server._operator_read_drained
            assert operator is not None and operator._server is None and operator._fd is None
        assert adapter._dependency_closers and not closed
        release.set()
        await until(lambda: not adapter._dependency_closers)
        assert closed == [True] and adapter._presentation_owner._service.drained
    finally:
        release.set()
        if not task.done():
            task.cancel()
        if adapter._start_cleanup_task is not None:
            await asyncio.wait_for(asyncio.shield(adapter._start_cleanup_task), 6)
