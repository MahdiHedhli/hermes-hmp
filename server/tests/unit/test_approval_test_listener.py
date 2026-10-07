"""Listener/adapter actual lifecycle with controlled service/endpoint ports only."""

from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace
from typing import ClassVar

import pytest

from hmp_plugin import approval_test_host_transport, approval_test_routes, server

from . import test_adapter as _adapter_tests
from .hmp_kit import Env
from .test_adapter import _Config

# Re-export the exact original fixture object under its original discovery name.
# The module alias is not itself a fixture; no wrapper or duplicate alias is registered.
adapter_module = _adapter_tests.adapter_module


class Endpoint:
    instances: ClassVar[list[Endpoint]] = []

    def __init__(self, record, generation, handler):
        self.record = record
        self.generation = generation
        self.handler = handler
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.events = []
        self.fail = False
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True
        self.events.append("accepts")

    async def close(self):
        self.events.append("stop_accepts")
        self.entered.set()
        await self.handler.shutdown()
        await self.release.wait()
        if self.fail:
            raise RuntimeError("synthetic unknown cleanup")
        self.events.append("joined")
        return True


def arm(env, monkeypatch):
    Endpoint.instances = []
    monkeypatch.setattr(approval_test_host_transport, "HostIpcEndpoint", Endpoint)
    native = [True]
    factories = []
    def factory(loop):
        factories.append(loop)
        def producer(**_kwargs):
            pytest.fail("no host begin was authorized in this lifecycle case")
        return producer, lambda: native[0]
    env.bridge.approval_test_producer_factory = factory
    env.ctx.approvals_available = lambda: True
    env.ctx.direct_send_flag = lambda: True
    srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0),
                           approval_test_owners=(sys.modules[server.__package__],
                                                 sys.modules[__name__]))
    srv.bound = ("127.0.0.1", 12345)
    return srv, native, factories


def test_listener_same_nonce_one_service_and_no_replacement_after_native_drift(
        tmp_path, monkeypatch):
    env = Env(tmp_path)
    async def scenario():
        srv, native, factories = arm(env, monkeypatch)
        record = tmp_path / "synthetic-listener.json"
        await srv.start_approval_test(record, "b" * 32)
        original = env.ctx.approval_test_service
        endpoint = Endpoint.instances[0]
        assert endpoint.started and endpoint.record == record
        assert endpoint.generation.nonce == "b" * 32
        assert endpoint.generation.pid == os.getpid() and endpoint.generation.iid == env.iid
        assert env.ctx.approval_test_current() is True
        await srv.start_approval_test(record, "c" * 32)
        assert env.ctx.approval_test_service is original and len(factories) == 1
        native[0] = False
        assert env.ctx.approval_test_current() is False
        native[0] = True
        assert env.ctx.approval_test_current() is False
        await srv.stop(notify=False)
        assert endpoint.events == ["accepts", "stop_accepts", "joined"]
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_module_replacement_retires_service_even_if_original_is_restored(tmp_path, monkeypatch):
    env = Env(tmp_path)
    async def scenario():
        srv, _, _ = arm(env, monkeypatch)
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        name = approval_test_routes.__name__
        monkeypatch.setitem(sys.modules, name, SimpleNamespace())
        assert env.ctx.approval_test_current() is False
        monkeypatch.setitem(sys.modules, name, approval_test_routes)
        assert env.ctx.approval_test_current() is False
        await srv.stop(notify=False)
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_stop_observer_cancel_keeps_join_owner_and_all_dependencies(tmp_path, monkeypatch):
    env = Env(tmp_path)
    async def scenario():
        srv, _, _ = arm(env, monkeypatch)
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        endpoint = Endpoint.instances[0]
        endpoint.release.clear()
        events = endpoint.events
        class Runner:
            async def cleanup(self):
                events.append("runner_destroyed")
        srv._runner = Runner()
        srv._on_closed = lambda: events.append("store_callback")
        observer = asyncio.create_task(srv.stop())
        await endpoint.entered.wait()
        assert env.ctx.approval_test_current() is False
        assert not srv.closed.is_set() and "store_callback" not in events
        observer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await observer
        assert not srv._stop_owner.done()
        assert srv._runner is not None
        endpoint.release.set()
        await srv.stop()
        assert events == ["accepts", "stop_accepts", "joined", "runner_destroyed", "store_callback"]
        assert srv.closed.is_set()
        await srv.stop()
        assert events.count("joined") == 1
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_unknown_endpoint_cleanup_never_notifies_store_owner(tmp_path, monkeypatch):
    env = Env(tmp_path)
    async def scenario():
        srv, _, _ = arm(env, monkeypatch)
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        endpoint = Endpoint.instances[0]
        endpoint.fail = True
        notifications = []
        srv._on_closed = lambda: notifications.append(True)
        with pytest.raises(RuntimeError):
            await srv.stop()
        assert notifications == [] and not srv.closed.is_set()
        assert srv._at1_endpoint is endpoint
        with pytest.raises(RuntimeError):
            await srv.stop()
        assert endpoint.events.count("stop_accepts") == 1
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_optional_endpoint_start_failure_joins_service_and_never_retries(tmp_path, monkeypatch):
    env = Env(tmp_path)
    async def scenario():
        srv, _, factories = arm(env, monkeypatch)
        def fail(endpoint):
            endpoint.events.append("failed_start")
            raise OSError("synthetic bind refusal")
        monkeypatch.setattr(Endpoint, "start", fail)
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        assert env.ctx.approval_test_current() is False
        assert Endpoint.instances[0].events == ["failed_start", "stop_accepts", "joined"]
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        assert len(factories) == 1
        await srv.stop(notify=False)
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


@pytest.mark.parametrize("written", [False, True], ids=["record_failed", "record_written"])
def test_adapter_only_activates_after_successful_same_nonce_record(
        adapter_module, tmp_path, monkeypatch, written):
    env = Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    observed = []
    async def start(srv):
        srv.bound = ("127.0.0.1", 12345)
    async def activate(srv, record, nonce):
        assert observed == ["record"]
        assert adapter._record == record and adapter._nonce == nonce
        observed.append("service")
    def write(*_args, **_kwargs):
        if not written:
            raise OSError("synthetic write refusal")
        observed.append("record")
    monkeypatch.setattr(server.HmpServer, "start", start)
    monkeypatch.setattr(server.HmpServer, "start_approval_test", activate)
    monkeypatch.setattr(adapter_module.cli, "write_listener_record", write)
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": 12345}))
    async def scenario():
        assert await adapter.connect()
        assert observed == (["record", "service"] if written else [])
        await adapter.disconnect()
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_adapter_disconnect_retains_record_store_and_pointer_until_real_join(
        adapter_module, tmp_path, monkeypatch):
    env = Env(tmp_path)
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": 12345}))
    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()
        events = []
        class Listener:
            ctx = env.ctx
            async def stop(self, **_kwargs):
                events.append("fence")
                entered.set()
                await release.wait()
                events.append("joined")
        srv = Listener()
        adapter._server = srv
        adapter._record = tmp_path / "synthetic-listener.json"
        monkeypatch.setattr(adapter, "_drop_record", lambda: events.append("record_removed"))
        monkeypatch.setattr(adapter, "_close_generation",
                            lambda _ctx: events.append("prompt_closed"))
        monkeypatch.setattr(env.store, "close", lambda: events.append("store_closed"))
        observer = asyncio.create_task(adapter.disconnect())
        await entered.wait()
        assert adapter._server is srv and adapter._record is not None
        assert events == ["fence"]
        observer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await observer
        assert adapter._server is srv and events == ["fence"]
        release.set()
        await adapter.disconnect()
        assert events == ["fence", "fence", "joined", "record_removed",
                          "prompt_closed", "store_closed"]
        assert adapter._server is None
    try:
        asyncio.run(scenario())
    finally:
        monkeypatch.undo()
        env.store.close()


def test_listener_store_destruction_waits_for_actual_service_producer_join():
    from .test_approval_test_authority_service import admitted, finish, rig

    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        events = []
        joined_entered = asyncio.Event()
        producer = r.made[0]
        producer.joinable.clear()
        original_join = producer.close_and_join
        async def owned_join():
            events.append("native_join_entered")
            joined_entered.set()
            result = await original_join()
            events.append("native_joined")
            return result
        producer.close_and_join = owned_join
        r.ctx.push_hints = SimpleNamespace(clear=lambda: events.append("dependencies_live"))
        r.ctx.direct_send_deps = None
        srv = server.HmpServer(r.ctx, server.ListenerSettings("127.0.0.1", 12345))
        srv._at1_live = True
        srv._at1_service = r.service
        srv._at1_endpoint = Endpoint(None, r.gen, r.service)
        srv._on_closed = lambda: events.append("store_destroyed")
        observer = asyncio.create_task(srv.stop())
        try:
            await joined_entered.wait()
            assert not srv.closed.is_set() and "store_destroyed" not in events
            observer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await observer
            assert producer.join_calls == 1 and not srv._stop_owner.done()
        finally:
            producer.joinable.set()
            await srv.stop()
            await finish(r, lease)
        assert events.index("native_joined") < events.index("dependencies_live")
        assert events.index("dependencies_live") < events.index("store_destroyed")
        assert producer.join_calls == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("owner", ["adapter", "plugin"])
def test_actual_owning_module_replacement_restore_cannot_revive_generation(
        adapter_module, tmp_path, monkeypatch, owner):
    from hmp_plugin.approval_test_host_codec import HostBeginRequest

    env = Env(tmp_path)
    async def scenario():
        srv, _, factories = arm(env, monkeypatch)
        plugin = sys.modules[adapter_module.__package__]
        srv._at1_owners = (plugin, adapter_module)
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "b" * 32)
        service = env.ctx.approval_test_service
        assert env.ctx.approval_test_current() is True
        module = adapter_module if owner == "adapter" else plugin
        monkeypatch.setitem(sys.modules, module.__name__, SimpleNamespace())
        assert env.ctx.approval_test_current() is False
        monkeypatch.setitem(sys.modules, module.__name__, module)
        assert env.ctx.approval_test_current() is False
        await srv.start_approval_test(tmp_path / "synthetic-listener.json", "c" * 32)
        assert len(factories) == 1 and env.ctx.approval_test_service is service
        lease = service.responses(HostBeginRequest(env.ctx.approval_test_generation,
                                                  "synthetic-device", "synthetic-profile",
                                                  "synthetic-session"))
        try:
            assert (await anext(lease)).result == "unavailable"
        finally:
            await lease.aclose()
            await srv.stop(notify=False)
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()
