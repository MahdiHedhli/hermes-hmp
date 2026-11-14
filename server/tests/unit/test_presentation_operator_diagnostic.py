"""Binding metadata only: synthetic context/loop, real private Unix transport."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import cli, operator_read
from hmp_plugin.presentation_native_service import NativePresentationService
from hmp_plugin.request_ctx import ReadWorkerBudget

from .hmp_kit import Env
from .test_cli import Cli
from .test_operator_read import (
    _operator_test_parent_fixture as _operator_test_parent_fixture,
)
from .test_operator_read import (
    _owned_operator_parent,
)

IID, NONCE, GEN = "a" * 52, "b" * 32, "c" * 32


class _NoEquality:
    def __eq__(self, other):
        raise AssertionError("binding must compare identity, not application equality")


def _context():
    return SimpleNamespace(
        iid=IID, readiness_generation=GEN, read_worker_budget=ReadWorkerBudget(),
        bridge=_NoEquality(), store=_NoEquality(),
        identity=SimpleNamespace(still_current=lambda: True),
        presentation_service=None, presentation_available=lambda: False,
    )


def _structural_binding(ctx, calls):
    """Synthetic structural DATA, not an original native owner/receipt fixture."""
    loop = asyncio.get_running_loop()
    def current():
        assert asyncio.get_running_loop() is loop
        calls.append(threading.get_ident())
        return True
    service = object.__new__(NativePresentationService)
    service._ctx, service._loop = ctx, loop
    service._bridge, service._store = ctx.bridge, ctx.store
    service._identity, service._iid = ctx.identity, ctx.iid
    service._retired = False
    service._current = service._worker_current = current
    ctx.presentation_service, ctx.presentation_available = service, current
    return service


@pytest.mark.parametrize("bound", [False, True])
def test_binding_samples_only_on_loop_and_worker_never_uses_service(bound):
    async def scenario():
        ctx = _context()
        calls, workers = [], []
        loop_thread = threading.get_ident()
        def identity_current():
            workers.append(threading.get_ident())
            return True
        ctx.identity.still_current = identity_current
        if bound:
            _structural_binding(ctx, calls)
        service = operator_read.OperatorReadService(ctx, "/private/tmp/synthetic", NONCE)
        try:
            result = await service._context("", "0" * 32, presentation=True)
            assert result["state"] == ("bound_not_probed" if bound else "unavailable")
            assert set(result) == {"protocol", "operation", "iid", "nonce", "challenge",
                                   "generation", "state", "sample_ms", "expires_ms"}
            assert workers and all(t != loop_thread for t in workers)
            assert all(t == loop_thread for t in calls)
        finally:
            assert await service.stop() in (0, 1)
            await asyncio.wait_for(service.wait_drained(), 1.0)
        assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["service", "retired", "generation", "bridge", "callback"])
def test_changed_source_during_worker_wait_refuses(change):
    async def scenario():
        ctx = _context()
        native = _structural_binding(ctx, [])
        entered, release = threading.Event(), threading.Event()
        def blocked():
            entered.set()
            assert release.wait(3)
            return True
        ctx.identity.still_current = blocked
        service = operator_read.OperatorReadService(ctx, "/private/tmp/synthetic", NONCE)
        task = asyncio.create_task(service._context("", "0" * 32, presentation=True))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            if change == "service":
                _structural_binding(ctx, [])
            elif change == "retired":
                native._retired = True
            elif change == "generation":
                ctx.readiness_generation = "d" * 32
            elif change == "bridge":
                ctx.bridge = object()
            else:
                ctx.presentation_available = lambda: False
            release.set()
            with pytest.raises(operator_read.OperatorUnavailableError):
                await task
        finally:
            release.set()
            await service.stop()
            await asyncio.wait_for(service.wait_drained(), 1)
        assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
    asyncio.run(scenario())


def test_cancelled_observer_cannot_retire_identity_worker(monkeypatch):
    monkeypatch.setattr(operator_read, "DEADLINE_S", 0.05)
    async def scenario():
        ctx = _context()
        entered, release = threading.Event(), threading.Event()
        def blocked():
            entered.set()
            assert release.wait(3)
            return True
        ctx.identity.still_current = blocked
        service = operator_read.OperatorReadService(ctx, "/private/tmp/synthetic", NONCE)
        task = asyncio.create_task(service._context("", "0" * 32, presentation=True))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            with pytest.raises(operator_read.OperatorUnavailableError):
                await task
            assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (1, 1)
            assert await service.stop() == 1
        finally:
            release.set()
            await service.stop()
            await asyncio.wait_for(service.wait_drained(), 1)
        assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
    asyncio.run(scenario())


def test_existing_operator_capacity_is_not_broadened():
    async def scenario():
        ctx = _context()
        budget = ctx.read_worker_budget
        assert budget.reserve(operator=True) is True
        assert budget.reserve(operator=True) is True
        service = operator_read.OperatorReadService(ctx, "/private/tmp/synthetic", NONCE)
        try:
            with pytest.raises(operator_read.OperatorUnavailableError):
                await service._context("", "0" * 32, presentation=True)
            assert (budget.active, budget.operator) == (2, 2)
            assert not service._read_operations
        finally:
            budget.release(operator=True)
            budget.release(operator=True)
            assert await service.stop() == 0
    asyncio.run(scenario())


def test_actual_owned_unix_roundtrip_contains_no_image_or_phone_data():
    async def scenario():
        ctx = _context()
        _structural_binding(ctx, [])
        service = operator_read.OperatorReadService(ctx, _owned_operator_parent() / "anchor", NONCE)
        await service.start()
        try:
            result = await asyncio.to_thread(operator_read.read_presentation_context,
                                             service.path, iid=IID, nonce=NONCE)
            assert result["state"] == "bound_not_probed"
            assert not {"profile", "device_id", "avatar", "metadata", "decision"} & result.keys()
        finally:
            assert await service.stop() == 0
        assert not service.path.exists()
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value", [
    ("protocol", True), ("nonce", "d" * 32), ("iid", "b" * 52),
    ("challenge", "bad"), ("profile", "default"), ("operation", "other"),
])
def test_closed_request_rejects_foreign_or_extra_fields(field, value):
    request = {"protocol": 1, "operation": "host_presentation_binding_context",
               "iid": IID, "nonce": NONCE, "challenge": "0" * 32}
    request[field] = value
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._presentation_request(json.dumps(request).encode(), iid=IID, nonce=NONCE)


@pytest.mark.parametrize("change", ["protocol", "state", "challenge", "nonce", "generation",
                                    "expired", "long_ttl", "extra"])
def test_client_rejects_invalid_reply(monkeypatch, change):
    def exchange(_path, message, keys, *, deadline):
        assert 0 < deadline - time.monotonic() <= operator_read.DEADLINE_S
        now = int(time.monotonic() * 1_000)
        result = {**message, "generation": GEN, "state": "bound_not_probed",
                  "sample_ms": now, "expires_ms": now + 1500}
        updates = {
            "protocol": {"protocol": True}, "state": {"state": "ready"},
            "challenge": {"challenge": "f" * 32}, "nonce": {"nonce": "d" * 32},
            "generation": {"generation": "bad"},
            "expired": {"sample_ms": now - 100, "expires_ms": now - 1},
            "long_ttl": {"expires_ms": now + 3000}, "extra": {"profile": "default"},
        }
        result.update(updates[change])
        return operator_read._closed_json(json.dumps(result).encode(), keys)
    monkeypatch.setattr(operator_read, "_exchange", exchange)
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read.read_presentation_context(Path("/unused"), iid=IID, nonce=NONCE)


def test_absolute_transport_deadline_does_not_renew_per_recv():
    path = _owned_operator_parent() / operator_read.SOCKET_NAME
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    os.chmod(path, 0o600)
    listener.listen(2)
    listener.settimeout(1)
    original = path.stat()
    errors = []
    def serve():
        try:
            for _ in range(2):
                stream, _address = listener.accept()
                with stream:
                    stream.settimeout(1)
                    stream.recv(512)
                    for byte in b"{}\n":
                        time.sleep(0.025)
                        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                            stream.sendall(bytes([byte]))
        except Exception as error:
            errors.append(type(error).__name__)
    thread = threading.Thread(target=serve)
    thread.start()
    try:
        # Existing callers keep their original per-call transport behavior.
        assert operator_read._exchange(path, {}, frozenset()) == {}
        with pytest.raises(operator_read.OperatorUnavailableError):
            operator_read._exchange(path, {}, frozenset(), deadline=time.monotonic() + 0.06)
    finally:
        thread.join(2)
        assert not thread.is_alive()
        listener.close()
        current = path.stat()
        assert (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino)
        path.unlink()
    assert not errors


@pytest.mark.parametrize("state,expected", [("bound_not_probed", cli.EXIT_OK),
                                             ("unavailable", cli.EXIT_REFUSED)])
def test_cli_is_readonly_and_does_not_claim_image_readiness(tmp_path: Path, monkeypatch,
                                                          state, expected):
    c = Cli(Env(tmp_path))
    c.write_record(profiles=[("default", "Default")])
    def no_store(*_args, **_kwargs):
        pytest.fail("diagnostic entered writable Store dispatch")
    monkeypatch.setattr(cli, "_open", no_store)
    now = int(time.monotonic() * 1_000)
    monkeypatch.setattr(operator_read, "read_presentation_context",
                        lambda *_args, **_kwargs: {"state": state, "sample_ms": now,
                                                  "expires_ms": now + 1500})
    assert c.run("health", "presentation") == expected
    assert "Images and phone access were not tested." in c.stdout.getvalue()
    assert len(c.listener_live_calls) == 2
    assert ("health", "presentation") not in cli.MUTATING_COMMANDS


def test_cli_refuses_observation_expiring_during_final_tls_check(tmp_path: Path, monkeypatch):
    c = Cli(Env(tmp_path))
    c.write_record(profiles=[("default", "Default")])
    clock = [100.0]
    monkeypatch.setattr(cli.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(operator_read, "read_presentation_context",
                        lambda *_args, **_kwargs: {"state": "bound_not_probed",
                                                  "sample_ms": 100_000,
                                                  "expires_ms": 101_500})
    original = c.cli_env
    def environment():
        env = original()
        verifier = env.verify_listener_live
        calls = 0
        def verify(record, iid):
            nonlocal calls
            calls += 1
            if calls == 2:
                clock[0] = 102.0
            return verifier(record, iid)
        env.verify_listener_live = verify
        return env
    monkeypatch.setattr(c, "cli_env", environment)
    assert c.run("health", "presentation") == cli.EXIT_REFUSED
    assert "bound (not probed)" not in c.stdout.getvalue()
    assert "Desktop appearance binding: unavailable" in c.stdout.getvalue()


@pytest.mark.parametrize("failure", ["legacy", "listener_changed", "tls_changed"])
def test_cli_refuses_stale_or_legacy_context_without_private_error(tmp_path: Path,
                                                                 monkeypatch, failure):
    c = Cli(Env(tmp_path))
    c.write_record(profiles=[("default", "Default")])
    def observe(*_args, **_kwargs):
        if failure == "legacy":
            raise operator_read.OperatorUnavailableError("synthetic private path")
        if failure == "listener_changed":
            c.write_record(profiles=[("default", "Default")], nonce="d" * 32)
        else:
            c.listener_live = False
        return {"state": "bound_not_probed"}
    monkeypatch.setattr(operator_read, "read_presentation_context", observe)
    assert c.run("health", "presentation") == cli.EXIT_REFUSED
    assert "Desktop appearance binding: unavailable" in c.stdout.getvalue()
    assert "synthetic private path" not in c.stdout.getvalue() + c.stderr.getvalue()
