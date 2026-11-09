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


def test_verified_client_real_socket_commits_once_and_stale_snapshot_conflicts(tmp_path):
    from hmp_plugin.media_operator_client import exchange_media_decision

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        try:
            reply = await asyncio.to_thread(exchange_media_decision, service.path, request)
            assert reply.status == "committed" and reply.decision.revision == 1
            duplicate = await asyncio.to_thread(exchange_media_decision, service.path, request)
            assert duplicate.status == "conflict"
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 1
            assert store.owner_controls_decision(request.device_id) is None
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ("peer", "before_send", "after_reply", "reply_decode"))
def test_verified_client_classifies_before_send_vs_possible_commit_without_retry(
    tmp_path, monkeypatch, failure
):
    from hmp_plugin import media_operator_client as client

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        binding = client._binding
        calls = []

        def checked(*args):
            calls.append(1)
            if (failure == "before_send" and len(calls) == 3) or (
                failure == "after_reply" and len(calls) == 4
            ):
                raise OSError("synthetic binding change")
            return binding(*args)

        def decode_failed(*_args, **_kwargs):
            raise ValueError("synthetic reply parsing loss")

        monkeypatch.setattr(client, "_binding", checked)
        if failure == "peer":
            monkeypatch.setattr(client, "_peer_uid", lambda _sock: os.getuid() + 1)
        if failure == "reply_decode":
            monkeypatch.setattr(client, "decode_reply", decode_failed)
        try:
            possible_write = failure in {"after_reply", "reply_decode"}
            error = (
                client.MediaOperatorOutcomeUnknownError
                if possible_write
                else client.MediaOperatorUnavailableError
            )
            with pytest.raises(error):
                await asyncio.to_thread(client.exchange_media_decision, service.path, request)
            assert store.media_read_decision(ctx.iid, request.device_id).revision == int(
                possible_write
            )
            assert store.owner_controls_decision(request.device_id) is None
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "bad", ("iid", "nonce", "generation", "expired", "future", "bool", "duplicate")
)
def test_client_invalid_server_challenge_sends_no_mutation(tmp_path, bad):
    from hmp_plugin import media_operator_client as client

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        await service.stop()
        received = []
        finished = asyncio.Event()

        async def fake(reader, writer):
            hello = {
                "protocol": 1,
                "operation": "host_media_read_challenge",
                "iid": request.iid,
                "nonce": request.nonce,
                "generation": request.generation,
                "challenge": "e" * 32,
                "expires_ms": int(time.monotonic() * 1000) + 1500,
            }
            if bad in {"iid", "nonce", "generation"}:
                hello[bad] = "f" * (52 if bad == "iid" else 32)
            elif bad == "expired":
                hello["expires_ms"] = int(time.monotonic() * 1000) - 1
            elif bad == "future":
                hello["expires_ms"] = int(time.monotonic() * 1000) + 10000
            elif bad == "bool":
                hello["protocol"] = True
            raw = wire.dump_json(hello)
            if bad == "duplicate":
                raw = b'{"protocol":1,' + raw[1:]
            try:
                writer.write(raw + b"\n")
                await writer.drain()
                received.append(await reader.readline())
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        listener = await asyncio.start_unix_server(fake, path=str(service.path))
        service.path.chmod(0o600)
        try:
            with pytest.raises(client.MediaOperatorUnavailableError):
                await asyncio.to_thread(client.exchange_media_decision, service.path, request)
            await asyncio.wait_for(finished.wait(), 1)
            assert received == [b""]
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            listener.close()
            await listener.wait_closed()
            service.path.unlink(missing_ok=True)  # newer asyncio already removes its socket
            await finish(actor, store, service)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "allowed,answer", ((True, "exact"), (False, "exact"), (True, "wrong"), (True, "eof"))
)
def test_cli_confirmation_actual_client_service_cas_and_readback(
    tmp_path, monkeypatch, allowed, answer
):
    import argparse
    import io

    from hmp_plugin import cli

    async def scenario():
        actor, store, ctx, request, service = await open_service(tmp_path)
        expected_token = ("ALLOW" if allowed else "DENY") + " MEDIA_READ device\n"
        stdin = expected_token if answer == "exact" else ("yes\n" if answer == "wrong" else "")
        command_ctx = SimpleNamespace(
            store=store,
            out=io.StringIO(),
            now=lambda: 2,
            custody=SimpleNamespace(anchor_dir=service.path.parent / "anchor"),
            env=SimpleNamespace(stdin=io.StringIO(stdin)),
        )
        reads = []

        def live(_ctx, device_id, iid):
            assert iid == ctx.iid and device_id == request.device_id
            decision = store.media_read_decision(iid, device_id)
            reads.append(decision.revision)
            return {
                "decision": decision._asdict(),
                "nonce": request.nonce,
                "generation": request.generation,
                "host_enabled": False,
                "api_available": True,
                "effective": decision.allowed is True,
                "expires_ms": int(time.monotonic() * 1000) + 1500,
            }

        def forbidden(*_args, **_kwargs):
            raise AssertionError("CLI direct SQL write bypassed service")

        monkeypatch.setattr(cli, "_load_identity", lambda _ctx: SimpleNamespace(iid=ctx.iid))
        monkeypatch.setattr(cli, "_media_operator_context", live)
        # Executor captured its original bound Store mutator at construction.
        # A direct CLI lookup is forbidden while the real service retains that method.
        monkeypatch.setattr(store, "set_media_read", forbidden)
        args = argparse.Namespace(
            devices_command="grant-media-read" if allowed else "deny-media-read",
            device_id="device",
        )
        try:
            if answer == "exact":
                assert await asyncio.to_thread(cli._cmd_devices_media, command_ctx, args) == 0
                assert reads == [0, 0, 1]
                decision = store.media_read_decision(ctx.iid, "device")
                assert decision.revision == 1 and decision.allowed is allowed
                assert "saved at revision 1" in command_ctx.out.getvalue()
            else:
                with pytest.raises(cli.RefusedError, match="exact typed"):
                    await asyncio.to_thread(cli._cmd_devices_media, command_ctx, args)
                assert reads == [0]
                assert store.media_read_decision(ctx.iid, "device").revision == 0
            assert "Type " + expected_token.rstrip("\n") in command_ctx.out.getvalue()
            assert store.owner_controls_decision("device") is None
        finally:
            await finish(actor, store, service)

    asyncio.run(scenario())
