"""Synthetic socket/CAS and actual-worker retirement; no live host or human consent."""

import asyncio
import os
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import media_operator_service as module
from hmp_plugin import wire
from hmp_plugin.media_operator_protocol import MediaReadMutation, decode_reply
from hmp_plugin.media_publication_actor import MediaPublicationActor
from hmp_plugin.request_ctx import ReadWorkerBudget
from hmp_plugin.store import Store


@pytest.fixture(autouse=True)
def private_socket_parent(monkeypatch):
    # A fresh owned short pathname keeps Darwin's Unix socket path bound usable.
    with tempfile.TemporaryDirectory(
        prefix="hmp-mut-", dir=os.path.realpath(tempfile.gettempdir())
    ) as value:
        assert Path(value).stat().st_mode & 0o777 == 0o700
        monkeypatch.setenv("HOST_OPERATOR_TEST_PARENT", value)
        yield
        assert not (Path(value) / "media-operator.sock").exists()


async def open_service(tmp_path):
    actor = MediaPublicationActor()
    store = Store(tmp_path / "store.sqlite3", mutation_observer=actor)
    store.migrate()
    await asyncio.to_thread(store.insert_user, "user", "owner", 1)
    await asyncio.to_thread(
        store.insert_device, "device", "user", "f" * 52, b"public", "phone", 1, state="ACTIVE"
    )
    ctx = SimpleNamespace(
        iid="a" * 52,
        identity=SimpleNamespace(still_current=lambda: True),
        store=store,
        bridge=object(),
        readiness_generation="b" * 32,
        now=lambda: 2,
    )
    request = MediaReadMutation(
        ctx.iid,
        "c" * 32,
        ctx.readiness_generation,
        "d" * 32,
        "device",
        store.media_read_decision(ctx.iid, "device"),
        True,
    )
    ctx.read_worker_budget = ReadWorkerBudget()
    parent = Path(os.environ["HOST_OPERATOR_TEST_PARENT"])
    service = module.MediaOperatorMutationService(ctx, parent / "anchor", request.nonce, actor)
    await service.start()
    return actor, store, ctx, request, service


async def finish(actor, store, service):
    await service.stop()
    await service.wait_drained()
    actor.close()
    await actor.wait_drained()
    store.close()


async def exchange(service, request, *, challenge=None):
    reader, writer = await asyncio.open_unix_connection(str(service.path))
    hello = wire.parse_body(await reader.readline(), max_bytes=4096, max_depth=3)
    envelope = {
        "challenge": hello["challenge"] if challenge is None else challenge,
        "mutation": wire.parse_body(request.encode(), max_bytes=2048, max_depth=3),
    }
    writer.write(wire.dump_json(envelope) + b"\n")
    await writer.drain()
    response = await reader.readline()
    writer.close()
    await writer.wait_closed()
    return hello, response


def test_real_socket_cas_and_fresh_challenge_do_not_replay_snapshot(tmp_path):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        try:
            first, raw = await exchange(service, request)
            assert decode_reply(raw.rstrip(b"\n"), request=request).status == "committed"
            second, raw = await exchange(service, request)
            assert first["challenge"] != second["challenge"]
            assert decode_reply(raw.rstrip(b"\n"), request=request).status == "conflict"
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 1
            assert store.owner_controls_decision(request.device_id) is None
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize("bad", ("challenge", "nonce", "generation", "peer"))
def test_socket_scope_refusal_does_not_write(tmp_path, monkeypatch, bad):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        try:
            if bad == "peer":
                monkeypatch.setattr(module, "_peer_uid", lambda _socket: os.getuid() + 1)
                reader, writer = await asyncio.open_unix_connection(str(service.path))
                assert await reader.readline() == b""
                writer.close()
                await writer.wait_closed()
            else:
                if bad in ("nonce", "generation"):
                    from dataclasses import replace

                    altered = replace(request, **{bad: "e" * 32})
                else:
                    altered = request
                _, raw = await exchange(
                    service, altered, challenge="e" * 32 if bad == "challenge" else None
                )
                if bad == "challenge":
                    assert raw == b""
                else:
                    assert decode_reply(raw.rstrip(b"\n"), request=altered).status == "refused"
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", (False, True))
def test_timeout_or_cancel_and_stop_retain_actual_worker_debt(tmp_path, monkeypatch, cancel):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        entered, release = threading.Event(), threading.Event()

        def blocked(*_args, **_kwargs):
            entered.set()
            assert release.wait(3)
            return SimpleNamespace(status="refused", decision=None)

        monkeypatch.setattr(service._executor, "decide", blocked)
        try:
            task = asyncio.create_task(service._decide(request, time.monotonic() + 0.05))
            assert await asyncio.to_thread(entered.wait, 1)
            if cancel:
                task.cancel()
            raw = await task
            assert decode_reply(raw, request=request).status == "unknown"
            assert service._operator_debt() == 1 and ctx.read_worker_budget.operator == 1
            assert await service.stop() == 1
            waiter = asyncio.create_task(service.wait_drained())
            await asyncio.sleep(0)
            assert not waiter.done()
            release.set()
            await asyncio.wait_for(waiter, 1)
            assert service._operator_debt() == 0 and ctx.read_worker_budget.operator == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            release.set()
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize("malformed", ("duplicate", "oversize", "deep", "extra", "type"))
def test_malformed_frame_never_dispatches_mutation(tmp_path, monkeypatch, malformed):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        dispatched = []

        def forbidden(*_args, **_kwargs):
            dispatched.append(True)
            raise AssertionError("malformed request reached worker")

        monkeypatch.setattr(service._executor, "decide", forbidden)
        reader, writer = await asyncio.open_unix_connection(str(service.path))
        try:
            hello = wire.parse_body(await reader.readline(), max_bytes=4096, max_depth=3)
            envelope = {
                "challenge": hello["challenge"],
                "mutation": wire.parse_body(request.encode(), max_bytes=2048, max_depth=3),
            }
            if malformed == "duplicate":
                raw = b'{"challenge":"bad",' + wire.dump_json(envelope)[1:]
            elif malformed == "oversize":
                raw = b" " * 4096
            elif malformed == "deep":
                envelope["mutation"] = {"a": {"b": {"c": {"d": {"e": 1}}}}}
                raw = wire.dump_json(envelope)
            elif malformed == "extra":
                envelope["other"] = True
                raw = wire.dump_json(envelope)
            else:
                envelope["mutation"] = []
                raw = wire.dump_json(envelope)
            writer.write(raw + b"\n")
            await writer.drain()
            assert await asyncio.wait_for(reader.readline(), 1) == b""
            assert not dispatched and service._operator_debt() == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            writer.close()
            await writer.wait_closed()
            await finish(actor, store, service)

    asyncio.run(scenario())


def test_two_waiting_clients_bound_admission_without_worker_reservations(tmp_path):
    async def scenario():
        actor, store, ctx, _request, service = await open_service(tmp_path)
        connections = []
        try:
            for _ in range(2):
                reader, writer = await asyncio.open_unix_connection(str(service.path))
                connections.append((reader, writer))
                assert await reader.readline()  # each original connection owns its challenge
            reader, writer = await asyncio.open_unix_connection(str(service.path))
            connections.append((reader, writer))
            assert await reader.readline() == b""
            assert len(service._clients) == 2
            assert ctx.read_worker_budget.operator == 0 and service._operator_debt() == 0
        finally:
            for _reader, writer in connections:
                writer.close()
                await writer.wait_closed()
            await finish(actor, store, service)

    asyncio.run(scenario())


def test_challenge_from_another_connection_cannot_authorize_write(tmp_path):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        reader, writer = await asyncio.open_unix_connection(str(service.path))
        try:
            original = wire.parse_body(await reader.readline(), max_bytes=4096, max_depth=3)
            other, response = await exchange(service, request, challenge=original["challenge"])
            assert other["challenge"] != original["challenge"] and response == b""
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            writer.close()
            await writer.wait_closed()
            await finish(actor, store, service)

    asyncio.run(scenario())


def test_cohort_replaced_after_challenge_never_dispatches(tmp_path):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        reader, writer = await asyncio.open_unix_connection(str(service.path))
        try:
            hello = wire.parse_body(await reader.readline(), max_bytes=4096, max_depth=3)
            ctx.bridge = object()
            writer.write(
                wire.dump_json(
                    {
                        "challenge": hello["challenge"],
                        "mutation": wire.parse_body(request.encode(), max_bytes=2048, max_depth=3),
                    }
                )
                + b"\n"
            )
            await writer.drain()
            assert await reader.readline() == b""
            assert service._operator_debt() == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            writer.close()
            await writer.wait_closed()
            await finish(actor, store, service)

    asyncio.run(scenario())


def test_lost_submit_ack_retains_unknown_debt_even_after_actual_commit(tmp_path, monkeypatch):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        submit = service._pool.submit
        actual = []

        def lost_ack(*args, **kwargs):
            actual.append(submit(*args, **kwargs))
            raise RuntimeError("synthetic post-enqueue lost acknowledgement")

        monkeypatch.setattr(service._pool, "submit", lost_ack)
        try:
            raw = await service._decide(request, time.monotonic() + 1)
            assert decode_reply(raw, request=request).status == "unknown"
            # This test possesses the hidden Future solely to end its synthetic worker.
            # Production has no such completion proof and must retain debt indefinitely.
            result = await asyncio.wrap_future(actual[0])
            assert result.status == "committed"
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 1
            assert service._operator_debt() == 1 and ctx.read_worker_budget.operator == 1
            assert await service.stop() == 1
            waiter = asyncio.create_task(service.wait_drained())
            await asyncio.sleep(0)
            assert not waiter.done()
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
            assert store.owner_controls_decision(request.device_id) is None
        finally:
            await service.stop()
            actor.close()
            await actor.wait_drained()
            # Test-only teardown after the separately retained actual Future ended;
            # never treat service.stop or cancelled wait_drained as Store retirement proof.
            store.close()

    asyncio.run(scenario())


def test_late_worker_exception_is_consumed_without_async_log_or_early_retirement(
    tmp_path, monkeypatch
):
    import gc

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        entered, release = threading.Event(), threading.Event()
        errors = []
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: errors.append(context))

        def late_failure(*_args, **_kwargs):
            entered.set()
            assert release.wait(3)
            raise RuntimeError("synthetic worker diagnostic must not reach async log")

        monkeypatch.setattr(service._executor, "decide", late_failure)
        try:
            raw = await service._decide(request, time.monotonic() + 0.05)
            assert entered.is_set() and decode_reply(raw, request=request).status == "unknown"
            assert service._operator_debt() == 1
            assert await service.stop() == 1
            release.set()
            await asyncio.wait_for(service.wait_drained(), 1)
            gc.collect()
            await asyncio.sleep(0)
            assert errors == []
            assert ctx.read_worker_budget.operator == 0
        finally:
            release.set()
            await finish(actor, store, service)
            loop.set_exception_handler(None)

    asyncio.run(scenario())


@pytest.mark.parametrize("after_insert", (False, True))
def test_registration_fault_before_submit_releases_only_unsubmitted_reservation(
    tmp_path, monkeypatch, after_insert
):
    class FailedRegistration(dict):
        def __setitem__(self, key, value):
            if after_insert:
                super().__setitem__(key, value)
            raise MemoryError("synthetic registration interruption")

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        submitted = []

        def forbidden(*_args, **_kwargs):
            submitted.append(True)
            raise AssertionError("unregistered operation submitted")

        service._operations = FailedRegistration()
        monkeypatch.setattr(service._pool, "submit", forbidden)
        try:
            raw = await service._decide(request, time.monotonic() + 1)
            assert decode_reply(raw, request=request).status == "refused"
            assert not submitted and service._operator_debt() == 0
            assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
            assert await service.stop() == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


def test_intent_allocation_failure_occurs_before_budget_reservation(tmp_path, monkeypatch):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)

        def fail_allocation():
            raise MemoryError("synthetic intent allocation interruption")

        monkeypatch.setattr(module, "object", fail_allocation, raising=False)
        try:
            with pytest.raises(MemoryError):
                await service._decide(request, time.monotonic() + 1)
            assert service._operator_debt() == 0
            assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
            assert await service.stop() == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize("acquired", (False, True))
def test_budget_acquisition_return_loss_retains_intent_and_poisoned_admission(
    tmp_path, monkeypatch, acquired
):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        reserve = ctx.read_worker_budget.reserve
        submitted = []

        def lost_return(*, operator):
            if acquired:
                assert reserve(operator=operator) is True
            raise MemoryError("synthetic budget acquisition return loss")

        def forbidden(*_args, **_kwargs):
            submitted.append(True)
            raise AssertionError("uncertain reservation reached submit")

        monkeypatch.setattr(ctx.read_worker_budget, "reserve", lost_return)
        monkeypatch.setattr(service._pool, "submit", forbidden)
        try:
            raw = await service._decide(request, time.monotonic() + 1)
            assert decode_reply(raw, request=request).status == "unknown"
            assert not submitted and service._operator_debt() == 1
            assert ctx.read_worker_budget.poisoned is True
            assert ctx.read_worker_budget.operator == int(acquired)
            assert await service.stop() == 1
            assert not service._drained.is_set()
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            await service.stop()
            actor.close()
            await actor.wait_drained()
            # Test knows submission was never called; service's unknown acquisition
            # is intentionally NOT reconciled into a false successful drain.
            store.close()

    asyncio.run(scenario())


def test_definite_capacity_refusal_removes_only_unacquired_intent(tmp_path, monkeypatch):
    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        monkeypatch.setattr(ctx.read_worker_budget, "reserve", lambda **_kwargs: False)
        try:
            raw = await service._decide(request, time.monotonic() + 1)
            assert decode_reply(raw, request=request).status == "refused"
            assert service._operator_debt() == 0
            assert not ctx.read_worker_budget.poisoned
            assert ctx.read_worker_budget.operator == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())
