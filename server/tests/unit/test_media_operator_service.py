"""Synthetic socket/CAS and actual-worker retirement; no live host or human consent."""

import asyncio
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_media_operator_execution import setup

from hmp_plugin import media_operator_service as module
from hmp_plugin import wire
from hmp_plugin.media_operator_protocol import decode_reply
from hmp_plugin.request_ctx import ReadWorkerBudget


async def open_service(tmp_path):
    actor, store, ctx, request = await setup(tmp_path)
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


def test_timeout_and_handler_cancel_retain_actual_worker_debt(tmp_path, monkeypatch):
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
            raw = await task
            assert decode_reply(raw, request=request).status == "unknown"
            assert service._outstanding == 1 and ctx.read_worker_budget.operator == 1
            assert await service.stop() == 1
            waiter = asyncio.create_task(service.wait_drained())
            await asyncio.sleep(0)
            assert not waiter.done()
            release.set()
            await asyncio.wait_for(waiter, 1)
            assert service._outstanding == 0 and ctx.read_worker_budget.operator == 0
            assert store.media_read_decision(ctx.iid, request.device_id).revision == 0
        finally:
            release.set()
            await finish(actor, store, service)

    asyncio.run(scenario())
