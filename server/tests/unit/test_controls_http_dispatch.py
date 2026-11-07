"""One-attempt loopback mutation checks, using disposable synthetic TCP peers."""
from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from hmp_plugin import mobile_cron, wire
from hmp_plugin.contract import PATH_PREFIX, AuthzState, DirectSendEndpoint, ErrorCode, HmpError

from .hmp_kit import Env, pair, run


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["delete", "pause", "resume"])
@pytest.mark.parametrize("refuse", [False, True])
async def test_lost_ack_never_replays_and_send_refusal_closes_peer(action, refuse):
    requests = []
    eof_bytes = []
    finished = asyncio.Event()

    async def peer(reader, writer):
        try:
            try:
                data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 1)
                requests.append(data.split(b" ", 1)[0])
            except asyncio.IncompleteReadError as exc:
                eof_bytes.append(len(exc.partial))
        finally:
            writer.close()
            await writer.wait_closed()
            finished.set()

    listener = await asyncio.start_server(peer, "127.0.0.1", 0)
    calls = []

    def preflight():
        calls.append(True)
        if refuse and len(calls) == 2:
            raise HmpError(ErrorCode.NOT_FOUND)

    try:
        port = listener.sockets[0].getsockname()[1]
        endpoint = DirectSendEndpoint("127.0.0.1", port, "x" * 24, "/p/default")
        with pytest.raises(HmpError) as exc:
            await mobile_cron.call(
                endpoint, method="DELETE" if action == "delete" else "POST",
                job="abcdef123456", action=None if action == "delete" else action,
                before_dispatch=preflight,
            )
        await asyncio.wait_for(finished.wait(), 1)
        assert len(calls) == 2
        if refuse:
            assert exc.value.code is ErrorCode.NOT_FOUND
            assert requests == [] and eof_bytes == [0]
        else:
            assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
            assert requests == [b"DELETE" if action == "delete" else b"POST"]
            assert eof_bytes == []
    finally:
        listener.close()
        await listener.wait_closed()


@pytest.mark.parametrize("action", ["delete", "pause", "resume"])
def test_real_route_rechecks_controls_after_connection_acquired(
    tmp_path: Path, monkeypatch, action,
):
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.cron_flag = env.ctx.cron_available = lambda: True
    requests = []
    eof_bytes = []

    async def scenario(client):
        finished = asyncio.Event()

        async def peer(reader, writer):
            try:
                try:
                    data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 1)
                    requests.append(len(data))
                except asyncio.IncompleteReadError as exc:
                    eof_bytes.append(len(exc.partial))
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        listener = await asyncio.start_server(peer, "127.0.0.1", 0)
        port = listener.sockets[0].getsockname()[1]
        env.bridge.direct_send_endpoint = lambda _: DirectSendEndpoint(
            "127.0.0.1", port, "x" * 24, "/p/default",
        )
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        original = aiohttp.TCPConnector.connect

        async def connect(self, request, *args, **kwargs):
            connection = await original(self, request, *args, **kwargs)
            if request.url.port == port:
                env.store.set_owner_controls(dev.device_id, allowed=False, now=env.ctx.now())
            return connection

        monkeypatch.setattr(aiohttp.TCPConnector, "connect", connect)
        method = "DELETE" if action == "delete" else "POST"
        path = "/bots/default/jobs/abcdef123456" + ("" if action == "delete" else "/" + action)
        try:
            response = await client.request(method, PATH_PREFIX + path,
                                            data=wire.dump_json({}), headers=env.headers(dev))
            assert response.status == 404
            await asyncio.wait_for(finished.wait(), 1)
            assert requests == [] and eof_bytes == [0]
        finally:
            listener.close()
            await listener.wait_closed()

    run(env, scenario)


@pytest.mark.asyncio
async def test_missing_middleware_extension_refuses_without_fallback(monkeypatch):
    calls = []

    def unsupported(**kwargs):
        calls.append(set(kwargs))
        raise TypeError("synthetic unsupported extension")

    monkeypatch.setattr(aiohttp, "ClientSession", unsupported)
    with pytest.raises(HmpError) as exc:
        await mobile_cron.call(
            DirectSendEndpoint("127.0.0.1", 1, "x" * 24, ""),
            method="DELETE", job="abcdef123456",
        )
    assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
    assert len(calls) == 1 and "middlewares" in calls[0] and "request_class" in calls[0]


@pytest.mark.parametrize("action", ["delete", "pause", "resume"])
def test_current_route_dispatches_once_and_preserves_response(tmp_path, action):
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.cron_flag = env.ctx.cron_available = lambda: True
    calls = []

    async def scenario(client):
        async def native(request):
            assert request.headers["Authorization"] == "Bearer " + "x" * 24
            calls.append((request.method, request.path))
            if action == "delete":
                return web.json_response({"ok": True})
            return web.json_response({"job": {
                "id": "abcdef123456", "name": "synthetic", "prompt": "synthetic",
                "schedule_display": "every 1h", "enabled": action == "resume",
            }})

        app = web.Application()
        app.router.add_route("*", "/p/default/api/jobs/{tail:.*}", native)
        upstream = TestServer(app)
        await upstream.start_server()
        env.bridge.direct_send_endpoint = lambda _: DirectSendEndpoint(
            "127.0.0.1", upstream.port, "x" * 24, "/p/default",
        )
        try:
            dev = await pair(env, client)
            env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
            method = "DELETE" if action == "delete" else "POST"
            suffix = "" if action == "delete" else "/" + action
            response = await client.request(
                method, PATH_PREFIX + "/bots/default/jobs/abcdef123456" + suffix,
                headers=env.headers(dev),
            )
            assert response.status == 200
            data = await response.json()
            assert calls == [(method, "/p/default/api/jobs/abcdef123456" + suffix)]
            if action == "delete":
                assert data == {"deleted": True}
            else:
                assert data["job"]["id"] == "abcdef123456"
                assert data["job"]["enabled"] is (action == "resume")
        finally:
            await upstream.close()

    run(env, scenario)
