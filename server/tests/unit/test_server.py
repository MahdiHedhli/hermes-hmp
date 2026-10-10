"""T024: the aiohttp server — TLS 1.3 listener, bind and peer policy (TR-4), limits (TR-6), ERR-1
shaping, the ERR-2a middleware, the F1 route table only (FR-053), the reduced access log (SR-007,
CS-22), PR7-6 per-request and watchdog checks, and the package data in a built wheel.

Every listener binds to loopback in an isolated temporary home with a synthetic host id.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import shutil
import socket
import ssl
import subprocess
import threading
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, make_mocked_request

from hmp_plugin import crypto, identity, server, wire
from hmp_plugin.auth import AuthContext
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import (
    ERROR_MESSAGES,
    MAX_BODY_BYTES,
    MAX_HEADER_BYTES,
    RATE_PAIR_REQUEST_PER_MIN_PER_IP,
    RATE_PAIR_REQUEST_PER_MIN_PER_OFFER,
    RATE_TOKEN_PER_MIN_PER_DEVICE_ID,
    RATE_TOKEN_PER_MIN_PER_IP,
    AuthzState,
    BotChatTarget,
    DirectSendEndpoint,
    ErrorCode,
    HmpError,
    OtherWhy,
    Row,
)
from hmp_plugin.direct_send import DirectSendDeps, LoopbackResult, ProfileLocks
from hmp_plugin.pairing import PairingService

from .hmp_kit import (
    UNSUPPORTED,
    Device,
    Env,
    code,
    get,
    pair,
    post,
    run,
)
from .test_log_hygiene import _scanner

SERVER_DIR = Path(__file__).resolve().parents[2]
REPO = SERVER_DIR.parent
WATCH_S = 0.05

LOOKUP_CMID = "0190a0b0-0000-7000-8000-000000000000"

WRITE_PATHS: tuple[tuple[str, str], ...] = (
    ("POST", "/bots/b/conversations/default/messages"),  # submit
    ("GET", "/bots/b/conversations/default/messages/by-client-id/" + LOOKUP_CMID),  # lookup
    ("GET", "/bots/b/conversations/default/events"),  # SSE
    ("POST", "/bots/b/conversations/default/approvals/r1"),
    ("POST", "/bots/b/conversations/default/clarify/c1"),
    ("POST", "/bots/b/conversations/default/stop"),
)


# --------------------------------------------------------------------------------------------------
# A minimal reference TLS client (TR-2: pin checked before the first byte is written)
# --------------------------------------------------------------------------------------------------


def tls_exchange(
    port: int,
    pin: str,
    request: bytes,
    *,
    max_version: ssl.TLSVersion | None = None,
) -> tuple[str, bytes]:
    """Return (status code | "pin_mismatch" | "connection_failure", raw response)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # trust comes from the pin alone (TR-2)
    if max_version is not None:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = max_version
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=3) as raw,
            ctx.wrap_socket(raw) as tls,
        ):
            peer = tls.getpeercert(binary_form=True)
            if peer is None or crypto.spki_fingerprint(crypto.certificate_spki(peer)) != pin:
                return "pin_mismatch", b""
            tls.sendall(request)
            chunks = []
            while True:
                data = tls.recv(65536)
                if not data:
                    break
                chunks.append(data)
    except (OSError, ssl.SSLError):
        return "connection_failure", b""
    head = b"".join(chunks)
    # A parser-level fault (a bad request line or header, rejected before any HMP middleware or
    # even routing runs) answers `HTTP/1.0`, not `1.1`: aiohttp's dummy `_ErrInfo` dispatch has no
    # real parsed request line to echo a version from. Ordinary responses (including this app's
    # own ERR-1 middleware responses) are always `HTTP/1.1`.
    if not (head.startswith(b"HTTP/1.1 ") or head.startswith(b"HTTP/1.0 ")):
        return "connection_failure", head
    return head.split(b" ")[1].decode("ascii"), head


def http_get(path: str, *, extra_headers: str = "") -> bytes:
    return (f"GET {path} HTTP/1.1\r\nHost: t\r\n{extra_headers}Connection: close\r\n\r\n").encode(
        "ascii"
    )


class Listener:
    """An `HmpServer` on loopback, started and stopped inside one event loop."""

    def __init__(self, env: Env, watch: float = WATCH_S) -> None:
        self.env = env
        self.closed_calls = 0
        self.srv = server.HmpServer(
            env.ctx,
            server.ListenerSettings("127.0.0.1", 0),
            watchdog_interval=watch,
            on_closed=self._closed,
        )

    def _closed(self) -> None:
        self.closed_calls += 1

    @property
    def port(self) -> int:
        assert self.srv.bound is not None
        return self.srv.bound[1]

    async def call(self, request: bytes, **kw: Any) -> tuple[str, bytes]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: tls_exchange(self.port, self.env.iid, request, **kw)
        )


def with_listener(env: Env, scenario: Any, *, watch: float = WATCH_S) -> None:
    async def main() -> None:
        listener = Listener(env, watch)
        await listener.srv.start()
        try:
            await scenario(listener)
        finally:
            await listener.srv.stop(notify=False)

    asyncio.run(main())


# --------------------------------------------------------------------------------------------------
# TLS (TR-1) and /ready (PR0-1)
# --------------------------------------------------------------------------------------------------


def test_tls13_listener_serves_ready_with_the_instance_certificate(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        status, raw = await listener.call(http_get("/hmp/v1/ready"))
        assert status == "200"
        body = json.loads(raw.split(b"\r\n\r\n", 1)[1])
        assert body == {
            "versions": [1],
            "contract": "1.0",
            "iid": env.iid,
            "guarantees": {
                "no_defer": False,
                "atomic_anchor": False,
                "approval_request_id": False,
                "confirmed_settle": False,
            },
            "write_gate": {"state": "closed", "reason": "guarantees_unavailable"},
        }
        assert b"\r\nServer: hmp\r\n" in raw  # no version or host details
        assert b"aiohttp" not in raw.lower() and b"python" not in raw.lower()

    with_listener(env, scenario)


def test_tls12_client_is_refused(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        status, _ = await listener.call(
            http_get("/hmp/v1/ready"), max_version=ssl.TLSVersion.TLSv1_2
        )
        assert status == "connection_failure"
        status, _ = await listener.call(http_get("/hmp/v1/ready"))  # 1.3 still works
        assert status == "200"

    with_listener(env, scenario)


def test_server_context_is_tls13_only_without_tickets(tmp_path: Path) -> None:
    env = Env(tmp_path)
    ctx = server.server_ssl_context(env.identity)
    assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3
    assert ctx.maximum_version == ssl.TLSVersion.TLSv1_3
    assert ctx.options & ssl.OP_NO_TICKET


# --------------------------------------------------------------------------------------------------
# Bind and peer policy (TR-4)
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("addr", "ok"),
    [
        ("127.0.0.1", True),
        ("127.5.6.7", True),
        ("::1", True),
        ("100\x2e64.0.1", True),
        ("100\x2e127.255.255", True),
        ("fd7a\x3a115c:a1e0::1", True),
        ("fd7a\x3a115c:a1e0:1:2:3:4:5", True),
        ("::ffff:100\x2e64.0.1", True),
        ("::ffff:127.0.0.1", True),
        ("0.0.0.0", False),  # noqa: S104 - must be refused
        ("::", False),
        ("100.128.0.1", False),
        ("100.63.255.255", False),
        ("192.168.1.10", False),
        ("10.0.0.1", False),
        ("203.0.113.9", False),
        ("fd7a:115c:a1e1::1", False),
        ("::ffff:192.168.1.10", False),
        ("localhost", False),
        ("", False),
        (None, False),
    ],
)
def test_address_policy(addr: str | None, ok: bool) -> None:
    assert server.address_allowed(addr) is ok


@pytest.mark.parametrize(
    "extra",
    [
        {"bind": "0.0.0.0", "port": 18920},  # noqa: S104 - must be refused
        {"bind": "::", "port": 18920},
        {"bind": "192.168.1.10", "port": 18920},
        {"bind": "localhost", "port": 18920},
        {"bind": "127.0.0.1"},
        {"bind": "127.0.0.1", "port": 0},
        {"bind": "127.0.0.1", "port": 70000},
        {"bind": "127.0.0.1", "port": True},
        {"bind": "127.0.0.1", "port": "18920"},
        {"bind": 127, "port": 18920},
    ],
)
def test_bind_validation_refuses(extra: dict[str, Any]) -> None:
    with pytest.raises(server.ListenerConfigError):
        server.listener_settings(extra)


def test_bind_validation_accepts() -> None:
    assert server.listener_settings({"port": 18920}) == server.ListenerSettings("127.0.0.1", 18920)
    for bind in ("100\x2e64.0.1", "fd7a\x3a115c:a1e0::1", "::1"):
        assert server.listener_settings({"bind": bind, "port": 1}).bind == bind


def test_start_refuses_a_non_tailnet_bind(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def main() -> None:
        wildcard = server.ListenerSettings("0.0.0.0", 0)  # noqa: S104 - must be refused
        srv = server.HmpServer(env.ctx, wildcard)
        with pytest.raises(server.ListenerConfigError):
            await srv.start()

    asyncio.run(main())


def _mocked(
    app: web.Application,
    method: str,
    path: str,
    peer: str,
    *,
    match_info: dict[str, str] | None = None,
) -> web.Request:
    transport = mock.Mock()
    transport.get_extra_info.side_effect = lambda name, default=None: (
        (peer, 40000) if name == "peername" else default
    )
    kw: dict[str, Any] = {} if match_info is None else {"match_info": match_info}
    return make_mocked_request(method, path, app=app, transport=transport, **kw)


@pytest.mark.parametrize("peer", ["203.0.113.9", "192.168.1.10", "100.128.0.1", "fd00::1"])
def test_peer_not_allowed(tmp_path: Path, peer: str) -> None:
    env = Env(tmp_path)
    app = env.app()
    reached: list[str] = []

    async def handler(_req: web.Request) -> web.Response:
        reached.append("handler")
        return web.Response(text="x")

    async def main() -> None:
        req = _mocked(app, "GET", "/hmp/v1/ready", peer)

        async def inner(r: web.Request) -> web.StreamResponse:
            return await server.peer_middleware(r, handler)

        resp = await server.error_middleware(req, inner)
        assert resp.status == 403
        assert json.loads(resp.body) == {
            "error": {
                "code": "forbidden",
                "message": ERROR_MESSAGES[ErrorCode.FORBIDDEN],
                "why": "peer_not_allowed",
            }
        }

    asyncio.run(main())
    assert reached == []


def test_allowed_peer_reaches_the_handler(tmp_path: Path) -> None:
    env = Env(tmp_path)
    app = env.app()

    async def handler(_req: web.Request) -> web.Response:
        return web.Response(text="x")

    async def main() -> None:
        for peer in ("127.0.0.1", "100\x2e64.0.1", "fd7a\x3a115c:a1e0::1"):
            resp = await server.peer_middleware(_mocked(app, "GET", "/hmp/v1/ready", peer), handler)
            assert resp.status == 200

    asyncio.run(main())


# --------------------------------------------------------------------------------------------------
# Limits (TR-6)
# --------------------------------------------------------------------------------------------------


def test_body_over_limit_is_413(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        big = b'{"pad":"' + b"a" * MAX_BODY_BYTES + b'"}'
        for path in ("/pair/request", "/pair/complete", "/auth/token", "/devices/self/revoke"):
            status, body = await post(client, path, big)
            assert (status, code(body)) == (413, "too_large"), path

    run(env, scenario)


def test_chunked_body_over_limit_is_413(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def chunks() -> Any:
        for _ in range(3):
            yield b"a" * (MAX_BODY_BYTES // 2 + 1)

    async def scenario(client: TestClient) -> None:
        resp = await client.post("/hmp/v1/pair/request", data=chunks())
        body = await resp.json()
        assert (resp.status, code(body)) == (413, "too_large")

    run(env, scenario)


def test_json_depth_over_limit_is_413(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        deep = b'{"a":' * 9 + b"1" + b"}" * 9
        status, body = await post(client, "/pair/request", deep)
        assert (status, code(body)) == (413, "too_large")

    run(env, scenario)


def test_headers_over_limit_are_413(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        headers = {f"X-Pad-{i}": "v" * 900 for i in range(10)}  # > MAX_HEADER_BYTES in total
        status, body = await get(client, "/ready", headers=headers)
        assert (status, code(body)) == (413, "too_large")
        status, body = await get(client, "/ready", headers={"X-One": "v" * MAX_HEADER_BYTES})
        assert (status, code(body)) == (413, "too_large")
        status, _ = await get(client, "/ready", headers={"X-Small": "v" * 100})
        assert status == 200

    run(env, scenario)


@pytest.mark.parametrize(
    "raw",
    [b"not json", b"[]", b'"x"', b'{"a":1,"a":2}', b"\xff\xfe", b'{"a":NaN}', b""],
)
def test_non_ijson_body_is_400_bad_request(tmp_path: Path, raw: bytes) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        for path in ("/pair/request", "/pair/complete", "/auth/token"):
            status, body = await post(client, path, raw)
            assert (status, code(body)) == (400, "bad_request"), path

    run(env, scenario)


def test_pair_request_rate_limited_per_ip(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        offer = env.offer()
        body = env.p2_body(Device(), offer, s=wire.b64u_encode(b"\0" * 32))  # wrong secret
        statuses = []
        for _ in range(RATE_PAIR_REQUEST_PER_MIN_PER_IP + 1):
            other = env.offer()  # a fresh offer each time: only the per-IP limit can trip
            status, reply = await post(client, "/pair/request", {**body, "oid": other.oid})
            statuses.append((status, code(reply)))
        assert statuses[:-1] == [(401, "pair_failed")] * RATE_PAIR_REQUEST_PER_MIN_PER_IP
        assert statuses[-1] == (429, "rate_limited")
        env.clock.now += 60  # a new window
        status, _ = await post(client, "/pair/request", body)
        assert status != 429

    run(env, scenario)


def test_pair_request_rate_limited_per_offer(tmp_path: Path) -> None:
    env = Env(tmp_path)
    svc = PairingService(env.store, env.identity, server.RateLimiter())
    body = env.p2_body(Device(), env.offer())
    body["oid"] = wire.b64u_encode(b"\x01" * 16)  # an unknown offer: nothing burns
    for i in range(RATE_PAIR_REQUEST_PER_MIN_PER_OFFER):  # each from a different peer
        with pytest.raises(HmpError) as err:
            svc.request(body, peer=f"100.64.0.{i + 1}", now=env.clock.now)
        assert err.value.code is ErrorCode.PAIR_FAILED
    with pytest.raises(HmpError) as err:
        svc.request(body, peer="100\x2e64.0.0", now=env.clock.now)
    assert err.value.code is ErrorCode.RATE_LIMITED


def test_token_rate_limited_per_ip(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        body = {"device_id": "dev_" + "A" * 22, "refresh_token": "x", "ts": 1, "nonce": "x"}
        statuses = []
        for i in range(RATE_TOKEN_PER_MIN_PER_IP + 1):
            status, _ = await post(client, "/auth/token", {**body, "device_id": f"dev_{i:022d}"})
            statuses.append(status)
        assert statuses[:-1] == [401] * RATE_TOKEN_PER_MIN_PER_IP
        assert statuses[-1] == 429

    run(env, scenario)


def test_token_rate_limited_per_device(tmp_path: Path) -> None:
    env = Env(tmp_path)
    device_id = "dev_" + "B" * 22
    for _ in range(RATE_TOKEN_PER_MIN_PER_DEVICE_ID):  # other peers used this device's budget
        env.ctx.limiter.allow(
            "token_device", device_id, RATE_TOKEN_PER_MIN_PER_DEVICE_ID, env.clock.now
        )

    async def scenario(client: TestClient) -> None:
        body = {"device_id": device_id, "refresh_token": "x", "ts": 1, "nonce": "x"}
        status, reply = await post(client, "/auth/token", body)
        assert (status, code(reply)) == (429, "rate_limited")

    run(env, scenario)


@pytest.mark.parametrize(
    ("method", "path", "bucket"),
    [
        ("GET", "/bots", "bots_roster"),
        ("GET", "/bots/alpha/conversations/default", "bots_snapshot"),
        ("GET", "/bots/alpha/conversations/default/messages", "bots_history"),
        ("POST", "/bots/alpha/authorize", "bots_authorize"),
    ],
)
def test_read_and_authorize_routes_are_rate_limited_per_device(
    tmp_path: Path, method: str, path: str, bucket: str
) -> None:
    """SR-4: `/bots`, snapshot, history and authorize each get their own per-device TR-6-style
    limit, checked before the (possibly blocking) reads/authorize component ever runs -- so it
    trips even though this harness's `reads`/`authorize` are fakes/absent."""
    from hmp_plugin.contract import (
        RATE_AUTHORIZE_PER_MIN_PER_DEVICE_ID,
        RATE_READ_PER_MIN_PER_DEVICE_ID,
    )

    env = Env(tmp_path)
    limit = (
        RATE_AUTHORIZE_PER_MIN_PER_DEVICE_ID
        if bucket == "bots_authorize"
        else RATE_READ_PER_MIN_PER_DEVICE_ID
    )

    query = "?after=0" if path.endswith("/messages") else ""  # history's `after` is required

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        for _ in range(limit):  # other requests used this device's budget
            env.ctx.limiter.allow(bucket, dev.device_id, limit, env.clock.now)
        resp = await client.request(method, "/hmp/v1" + path + query, headers=env.headers(dev))
        body = await resp.json()
        assert (resp.status, code(body)) == (429, "rate_limited")

    run(env, scenario)


USER = "hmpu_" + "e" * 32


@pytest.mark.parametrize(
    ("attr", "method", "path"),
    [
        ("reads", "GET", "/bots"),
        ("reads", "GET", "/bots/alpha/conversations/default"),
        ("reads", "GET", "/bots/alpha/conversations/default/messages"),
        ("authorize", "POST", "/bots/alpha/authorize"),
    ],
)
def test_read_and_authorize_handlers_run_off_the_event_loop_thread(
    tmp_path: Path, attr: str, method: str, path: str
) -> None:
    """SR-4: the bridge's reads and authorization must not run synchronously on the gateway's
    shared event loop (they can block on SQLite and on Hermes internals, including a secret-
    source hydration that can shell out). Each handler must dispatch through `asyncio.to_thread`,
    which runs the call on a worker thread."""
    env = Env(tmp_path)
    loop_thread_id = threading.get_ident()
    seen: list[int] = []

    class Component:
        def roster(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            seen.append(threading.get_ident())
            return {"bots": []}

        snapshot = roster  # each real call passes different positional args; the fake ignores them
        history = roster
        authorize = roster

    setattr(env.ctx, attr, Component())
    app = env.app()
    match_info = None if path == "/bots" else {"p": "alpha"}
    query = "?after=0" if path.endswith("/messages") else ""  # history's `after` is required

    async def main() -> None:
        req = _mocked(app, method, "/hmp/v1" + path + query, "127.0.0.1", match_info=match_info)
        with mock.patch.object(
            server,
            "bearer",
            return_value=AuthContext(device_id="dev_x", user_id=USER, family_id="fam_x"),
        ):
            handler = {
                "/bots": server.handle_roster,
                "/bots/alpha/conversations/default": server.handle_snapshot,
                "/bots/alpha/conversations/default/messages": server.handle_history,
                "/bots/alpha/authorize": server.handle_authorize,
            }[path]
            resp = await handler(req)
        assert resp.status == 200

    asyncio.run(main())
    assert len(seen) == 1 and seen[0] != loop_thread_id


def test_bridge_reads_dispatch_preserves_the_ambient_contextvar_scope(tmp_path: Path) -> None:
    """SR-4: `asyncio.to_thread` copies the CURRENT context into its worker thread, unlike a bare
    `loop.run_in_executor`, which would hand the call a fresh, empty context. Hermes's real
    profile secret-scope lives in a contextvar for exactly this reason (`agent.secret_scope`):
    losing it here would silently break secret resolution once these calls moved off the loop."""
    env = Env(tmp_path)
    scope_var: contextvars.ContextVar[str] = contextvars.ContextVar("hmp_test_profile_scope")
    seen: list[str] = []

    class ScopedReads:
        def roster(self, _user_id: str) -> dict[str, Any]:
            seen.append(scope_var.get("<unset>"))
            return {"bots": []}

    env.ctx.reads = ScopedReads()
    app = env.app()

    async def main() -> web.Response:
        scope_var.set("alpha-scope")  # set in THIS task's context, ambient to the call below
        req = _mocked(app, "GET", "/hmp/v1/bots", "127.0.0.1")
        with mock.patch.object(
            server,
            "bearer",
            return_value=AuthContext(device_id="dev_x", user_id=USER, family_id="fam_x"),
        ):
            return await server.handle_roster(req)

    resp = asyncio.run(main())
    assert resp.status == 200
    assert seen == ["alpha-scope"]


def test_rate_limiter_is_lru_bounded() -> None:
    limiter = server.RateLimiter(max_entries=8)
    for i in range(100):
        assert limiter.allow("b", str(i), 1, 0)
    assert len(limiter) == 8
    assert not limiter.allow("b", "99", 1, 0)
    assert limiter.allow("b", "0", 1, 0)  # evicted, so a fresh window


# --------------------------------------------------------------------------------------------------
# ERR-1 shaping and the route table (FR-053)
# --------------------------------------------------------------------------------------------------


def test_route_table_matches_declared_routes(tmp_path: Path) -> None:
    app = Env(tmp_path).app()
    routes = sorted((r.method, r.resource.canonical) for r in app.router.routes())
    expected = sorted(
        (m, server.full_path(p))
        for m, p, _ in (
            *server.F1_ROUTES,
            *server.A1_SESSION_ROUTES,
            *server.F2_DIRECT_SEND_ROUTES,
            *server.F3_APPROVAL_ROUTES,
            *server.MOBILE_CRON_ROUTES,
            *server.MOBILE_MODEL_ROUTES,
            *server.S5_MEDIA_ROUTES,
        )
    )
    assert routes == expected
    assert len(expected) == 29


def test_a1_session_routes_are_not_registered_when_the_kill_switch_is_off(
    tmp_path: Path,
) -> None:
    """Amendment A1: `gateway.platforms.hmp.extra.session_browsing = false` -- SES-1/SES-2 are
    never added to the router at all, so they 404 exactly like F1's other unregistered routes.
    Amendment F2's direct-send routes are unaffected by this kill switch (server-modules.md):
    they stay registered, gated per-request instead (`test_direct_send_*` below)."""
    app = Env(tmp_path, session_browsing=False).app()
    routes = sorted((r.method, r.resource.canonical) for r in app.router.routes())
    expected = sorted(
        (m, server.full_path(p))
        for m, p, _ in (
            *server.F1_ROUTES,
            *server.F2_DIRECT_SEND_ROUTES,
            *server.F3_APPROVAL_ROUTES,
            *server.MOBILE_CRON_ROUTES,
            *server.MOBILE_MODEL_ROUTES,
            *server.S5_MEDIA_ROUTES,
        )
    )
    assert routes == expected
    assert len(expected) == 26


def test_e10_session_routes_are_not_registered_when_browsing_is_unavailable(
    tmp_path: Path,
) -> None:
    """The session routes depend on two SessionDB methods; if this Hermes lacks them only those
    routes 404 (like the kill switch), and everything else stays registered."""
    env = Env(tmp_path)
    env.ctx.session_browsing_available = False
    routes = sorted((r.method, r.resource.canonical) for r in env.app().router.routes())
    expected = sorted(
        (m, server.full_path(p))
        for m, p, _ in (
            *server.F1_ROUTES, *server.F2_DIRECT_SEND_ROUTES, *server.F3_APPROVAL_ROUTES,
            *server.MOBILE_CRON_ROUTES, *server.MOBILE_MODEL_ROUTES, *server.S5_MEDIA_ROUTES,
        )
    )
    assert routes == expected


def test_write_paths_are_404_with_zero_bridge_calls(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.bridge.calls.clear()
        for authed in (False, True):
            headers = env.headers(dev) if authed else {}
            for method, path in WRITE_PATHS:
                data = wire.dump_json({"client_message_id": "x", "text": "hi"})
                resp = await client.request(method, "/hmp/v1" + path, data=data, headers=headers)
                body = await resp.json()
                assert resp.status == 404, (method, path)
                assert body == {
                    "error": {"code": "not_found", "message": ERROR_MESSAGES[ErrorCode.NOT_FOUND]}
                }
        # Wrong methods on registered paths are 404 too (never 405).
        for method, path in (("PUT", "/ready"), ("GET", "/pair/request"), ("DELETE", "/bots")):
            resp = await client.request(method, "/hmp/v1" + path)
            assert resp.status == 404
        assert env.bridge.calls == []

    run(env, scenario)


def test_other_conversation_ids_are_404(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.bridge.calls.clear()
        for path in ("/bots/b/conversations/other", "/bots/b/conversations/x/messages"):
            status, body = await get(client, path, headers=env.headers(dev))
            assert (status, code(body)) == (404, "not_found")
        assert env.bridge.calls == []

    run(env, scenario)


def test_internal_error_is_500_other_without_detail(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = Env(tmp_path)

    class Boom:
        def roster(self, _user: str) -> Any:
            raise RuntimeError("secret detail that must not leak")

    env.ctx.reads = Boom()

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        with caplog.at_level(logging.DEBUG):
            status, body = await get(client, "/bots", headers=env.headers(dev))
        assert status == 500
        assert body == {
            "error": {
                "code": "other",
                "message": ERROR_MESSAGES[ErrorCode.OTHER],
                "why": "internal_error",
            }
        }
        assert "secret detail" not in caplog.text
        assert "exception_type=RuntimeError" in caplog.text
        assert "last=test_server.py:roster:" in caplog.text

    run(env, scenario)


def test_error_bodies_carry_only_err1_extras() -> None:
    with pytest.raises(ValueError):
        HmpError(ErrorCode.FORBIDDEN, detail="x")
    with pytest.raises(ValueError):
        HmpError(ErrorCode.OTHER)  # 500 or 503 must be explicit
    with pytest.raises(ValueError):
        HmpError(ErrorCode.NOT_FOUND, 409)
    with pytest.raises(ValueError):
        HmpError(ErrorCode.BUSY, guarantees={"no_defer": False})
    body = HmpError(ErrorCode.GUARANTEES_UNAVAILABLE, guarantees={"no_defer": False}).body()
    assert set(body) == {"error", "guarantees"}
    assert set(ERROR_MESSAGES) == set(ErrorCode)


# --------------------------------------------------------------------------------------------------
# ERR-2a (FR-044a)
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "why", [OtherWhy.HERMES_BUILD_UNSUPPORTED, OtherWhy.HERMES_READ_DEPENDENCY_MISSING]
)
def test_unsupported_build_serves_only_ready(tmp_path: Path, why: OtherWhy) -> None:
    env = Env(tmp_path, compat=CompatResult(CompatStatus.UNSUPPORTED, why))
    assert env.ctx.bridge is None and env.ctx.reads is None

    async def scenario(client: TestClient) -> None:
        status, body = await get(client, "/ready")
        assert status == 200 and body["iid"] == env.iid
        assert body["write_gate"] == {"state": "closed", "reason": "guarantees_unavailable"}
        assert not any(body["guarantees"].values())
        offer = env.offer()
        paths = [
            ("POST", "/pair/request", env.p2_body(Device(), offer)),
            ("POST", "/pair/complete", {}),
            ("POST", "/auth/token", {}),
            ("POST", "/devices/self/revoke", {}),
            ("GET", "/bots", None),
            ("POST", "/bots/b/authorize", None),
            ("GET", "/bots/b/conversations/default", None),
            ("GET", "/bots/b/conversations/default/messages?after=1", None),
            *((m, p, None) for m, p in WRITE_PATHS),
            ("GET", "/nothing-here", None),
            ("GET", "/ready/", None),
        ]
        for method, path, payload in paths:
            data = wire.dump_json(payload) if payload is not None else None
            resp = await client.request(method, "/hmp/v1" + path, data=data)
            reply = await resp.json()
            assert resp.status == 503, path
            assert reply == {
                "error": {
                    "code": "other",
                    "message": ERROR_MESSAGES[ErrorCode.OTHER],
                    "why": why.value,
                }
            }, path
        assert env.store.get_offer(offer.oid)["state"] == "open"  # nothing ran

    run(env, scenario)


def test_unsupported_build_default_why(tmp_path: Path) -> None:
    env = Env(tmp_path, compat=UNSUPPORTED)

    async def scenario(client: TestClient) -> None:
        status, body = await get(client, "/bots")
        assert (status, body["error"]["why"]) == (503, "hermes_build_unsupported")

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# Access log (SR-007, CS-22)
# --------------------------------------------------------------------------------------------------


def test_access_log_has_no_query_string_or_bearer(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    env = Env(tmp_path)
    secret_query = "tok=" + "Q" * 30
    secret_bearer = "Z" * 43

    async def scenario(listener: Listener) -> None:
        with caplog.at_level(logging.DEBUG):
            status, _ = await listener.call(
                http_get(
                    f"/hmp/v1/bots/some-profile/conversations/default?{secret_query}",
                    extra_headers=f"Authorization: Bearer {secret_bearer}\r\nHMP-Instance: x\r\n",
                )
            )
            assert status == "401"
            await asyncio.sleep(0.05)

    with_listener(env, scenario)
    access = [r for r in caplog.records if r.name == server.ACCESS_LOGGER_NAME]
    assert access, "the access log should have one reduced line"
    line = access[0].getMessage()
    assert line.startswith("GET /hmp/v1/bots/{p}/conversations/default 401 ")
    text = caplog.text
    for leaked in (secret_query, secret_bearer, "Bearer", "some-profile", "127.0.0.1"):
        assert leaked not in text


# --------------------------------------------------------------------------------------------------
# Independent security review of T024-T027: parser-level faults (SEC-4)
# --------------------------------------------------------------------------------------------------


def test_malformed_header_with_bearer_token_never_reaches_the_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A header with no `:` is not valid HTTP-message grammar: aiohttp's own parser rejects it
    (`BadHttpMessage`) before any HMP middleware runs. Its default `handle_error()` logs the peer
    address and the raw offending bytes (here, a header that happens to carry a Bearer token) via
    `exc_info` -- `HmpServer.start()`'s `logger=` (`_ParserSafeLogger`) must stop that."""
    env = Env(tmp_path)
    secret_bearer = "Z" * 43

    async def scenario(listener: Listener) -> None:
        with caplog.at_level(logging.DEBUG):
            bad = (
                b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\n"
                b"Authorization Bearer " + secret_bearer.encode("ascii") + b"\r\n\r\n"
            )
            status, raw = await listener.call(bad)
            assert status == "400"
            assert secret_bearer.encode("ascii") not in raw
            await asyncio.sleep(0.05)

    with_listener(env, scenario)
    text = caplog.text
    assert secret_bearer not in text
    assert "127.0.0.1" not in text
    assert "event=http_parse_error outcome=bad_request" in text  # the fixed line still fires
    scanner = _scanner()
    rules = scanner.build_rules(REPO / "fixtures" / "f1" / "instances.yaml")
    findings = scanner.scan_text(text, rules)
    assert findings == [], [(n, rule) for n, rule, _ in findings]


def test_parser_level_bad_request_is_err1_json_not_aiohttp_plain_text(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        bad = b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nBadHeaderNoColon\r\n\r\n"
        status, raw = await listener.call(bad)
        assert status == "400"
        # aiohttp's default body echoes the bad line; ours must not.
        assert b"BadHeaderNoColon" not in raw
        assert b"text/plain" not in raw
        assert b"application/json" in raw
        body = json.loads(raw.split(b"\r\n\r\n", 1)[1])
        assert body == {
            "error": {"code": "bad_request", "message": ERROR_MESSAGES[ErrorCode.BAD_REQUEST]}
        }

    with_listener(env, scenario)


def test_parser_level_oversized_field_is_413_too_large_err1_json(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        # Well above MAX_HEADER_BYTES: aiohttp's own parser (max_field_size == MAX_HEADER_BYTES)
        # refuses this with `LineTooLong` before the request ever reaches `limits_middleware`.
        pad = b"a" * (3 * MAX_HEADER_BYTES)
        bad = b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nX-Pad: " + pad + b"\r\n\r\n"
        status, raw = await listener.call(bad)
        assert status == "413"
        assert pad[:200] not in raw
        assert b"application/json" in raw
        body = json.loads(raw.split(b"\r\n\r\n", 1)[1])
        assert body == {
            "error": {"code": "too_large", "message": ERROR_MESSAGES[ErrorCode.TOO_LARGE]}
        }

    with_listener(env, scenario)


def test_non_ascii_hmp_instance_header_is_wrong_instance_not_500(tmp_path: Path) -> None:
    """A non-UTF-8 `HMP-Instance` header decodes (aiohttp uses surrogateescape) to a Python `str`
    holding a lone surrogate. Comparing it with `crypto.constant_time_equal` used to call
    `str.encode("utf-8")` (strict) first, raising `UnicodeEncodeError` and reaching this app's own
    generic-exception handling as `500 other` instead of the correct `401 wrong_instance`."""
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        bad = (
            b"GET /hmp/v1/bots HTTP/1.1\r\nHost: t\r\n"
            b"Authorization: Bearer " + b"Z" * 43 + b"\r\n"
            b"HMP-Instance: ab\xffcd\r\nConnection: close\r\n\r\n"
        )
        status, raw = await listener.call(bad)
        assert status == "401"
        body = json.loads(raw.split(b"\r\n\r\n", 1)[1])
        assert body == {
            "error": {
                "code": "wrong_instance",
                "message": ERROR_MESSAGES[ErrorCode.WRONG_INSTANCE],
            }
        }

    with_listener(env, scenario)


def test_peer_key_collapses_every_loopback_address_to_one_bucket(tmp_path: Path) -> None:
    env = Env(tmp_path)
    app = env.app()
    for peer in ("127.0.0.1", "127.0.0.2", "127.255.255.255", "::1", "::ffff:127.0.0.1"):
        req = _mocked(app, "GET", "/hmp/v1/ready", peer)
        assert server.peer_key(req) == server.LOOPBACK_RATE_LIMIT_KEY, peer


def test_peer_key_keeps_non_loopback_addresses_distinct(tmp_path: Path) -> None:
    env = Env(tmp_path)
    app = env.app()
    for peer in ("100\x2e64.0.1", "100\x2e127.255.255", "fd7a\x3a115c:a1e0::1", "203.0.113.9"):
        req = _mocked(app, "GET", "/hmp/v1/ready", peer)
        assert server.peer_key(req) == peer


def test_loopback_cannot_be_used_to_bypass_the_per_ip_rate_limit(tmp_path: Path) -> None:
    """127.0.0.0/8 alone is 16,777,216 addresses; without the loopback collapse, cycling through
    them would give each request its own rate-limit bucket -- unlimited "per-IP" budget from
    loopback alone, and enough distinct one-shot keys to evict every other peer's live entry from
    the shared, LRU-bounded limiter table."""
    env = Env(tmp_path)
    app = env.app()
    limiter = server.RateLimiter()
    now = 0
    for i in range(RATE_PAIR_REQUEST_PER_MIN_PER_IP):
        req = _mocked(app, "POST", "/hmp/v1/pair/request", f"127.0.0.{i + 1}")
        assert limiter.allow(
            "pair_request_ip", server.peer_key(req), RATE_PAIR_REQUEST_PER_MIN_PER_IP, now
        )
    req = _mocked(app, "POST", "/hmp/v1/pair/request", "127.0.0.99")  # yet another fresh address
    assert not limiter.allow(
        "pair_request_ip", server.peer_key(req), RATE_PAIR_REQUEST_PER_MIN_PER_IP, now
    )
    assert len(limiter) == 1  # every loopback peer shares the single "loopback" bucket


# --------------------------------------------------------------------------------------------------
# PR7-6: the old key stops serving on the next request or watchdog tick
# --------------------------------------------------------------------------------------------------


def test_rotation_request_never_200_and_watchdog_closes(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        pin = env.iid
        assert (await listener.call(http_get("/hmp/v1/ready")))[0] == "200"
        identity.rotate_key(env.store, **env.kwargs)  # as the operator CLI would
        status, _ = await listener.call(http_get("/hmp/v1/ready"))
        assert status in ("connection_failure", "pin_mismatch")
        await asyncio.wait_for(listener.srv.closed.wait(), timeout=4 * WATCH_S + 2)
        assert listener.closed_calls == 1
        port = listener.port
        status, _ = await asyncio.get_running_loop().run_in_executor(
            None, lambda: tls_exchange(port, pin, http_get("/hmp/v1/ready"))
        )
        assert status == "connection_failure"

    with_listener(env, scenario)


def test_rotation_per_request_check_without_watchdog(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(listener: Listener) -> None:
        assert (await listener.call(http_get("/hmp/v1/ready")))[0] == "200"
        identity.rotate_key(env.store, **env.kwargs)
        for _ in range(3):
            status, _ = await listener.call(http_get("/hmp/v1/ready"))
            assert status in ("connection_failure", "pin_mismatch")
        await asyncio.wait_for(listener.srv.closed.wait(), timeout=5)

    with_listener(env, scenario, watch=3600)  # the watchdog never ticks in this test


def test_current_key_middleware_aborts_without_status(tmp_path: Path) -> None:
    env = Env(tmp_path)
    app = env.app()
    changed: list[bool] = []
    env.ctx.on_identity_changed = lambda: changed.append(True)

    async def handler(_req: web.Request) -> web.Response:
        raise AssertionError("must not run under a stale key")

    async def main() -> None:
        req = _mocked(app, "GET", "/hmp/v1/ready", "127.0.0.1")
        with mock.patch.object(env.identity, "still_current", return_value=False):
            await server.current_key_middleware(req, handler)
        req.transport.abort.assert_called_once()  # type: ignore[union-attr]

    asyncio.run(main())
    assert changed == [True]


def test_current_key_middleware_treats_a_raising_still_current_as_not_current(
    tmp_path: Path,
) -> None:
    """A raising `still_current()` must fail closed exactly like `False`, not escape as an
    unhandled exception: this middleware is outermost, wrapping `error_middleware`, so an
    exception here would otherwise reach aiohttp's own default 500 handling instead of this
    app's ERR-1 shaping (SEC-4)."""
    env = Env(tmp_path)
    app = env.app()
    changed: list[bool] = []
    env.ctx.on_identity_changed = lambda: changed.append(True)

    async def handler(_req: web.Request) -> web.Response:
        raise AssertionError("must not run under a stale key")

    async def main() -> None:
        req = _mocked(app, "GET", "/hmp/v1/ready", "127.0.0.1")
        with mock.patch.object(
            env.identity, "still_current", side_effect=RuntimeError("custody check exploded")
        ):
            resp = await server.current_key_middleware(req, handler)
        assert resp.status == 503
        req.transport.abort.assert_called_once()  # type: ignore[union-attr]

    asyncio.run(main())
    assert changed == [True]


# --------------------------------------------------------------------------------------------------
# Package data (T024)
# --------------------------------------------------------------------------------------------------


def test_built_wheel_contains_package_data(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not available to build the wheel")
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy2(SERVER_DIR / "pyproject.toml", src / "pyproject.toml")
    shutil.copy2(SERVER_DIR / "README.md", src / "README.md")
    shutil.copytree(
        SERVER_DIR / "hmp_plugin", src / "hmp_plugin", ignore=shutil.ignore_patterns("__pycache__")
    )
    out = tmp_path / "dist"
    completed = subprocess.run(
        [uv, "build", "--offline", "--wheel", "--out-dir", str(out), str(src)],
        check=False,
        capture_output=True,
        timeout=300,
    )
    assert completed.returncode == 0, (
        f"offline wheel build failed (exit {completed.returncode}); "
        f"stdout={completed.stdout[:8192]!r}; stderr={completed.stderr[:8192]!r}"
    )
    (wheel,) = out.glob("*.whl")
    names = set(zipfile.ZipFile(wheel).namelist())
    for data in (
        "plugin.yaml",
        "read_compat_builds.json",
        "write_supported_builds.json",
        "direct_send_supported_builds.json",
    ):
        assert f"hmp_plugin/{data}" in names


# --------------------------------------------------------------------------------------------------
# Amendment F2 (direct send, HMP_V1.md §7a): route-level integration tests
# --------------------------------------------------------------------------------------------------

_AN_ENDPOINT = DirectSendEndpoint(host="127.0.0.1", port=8642, api_key="k" * 20, path_prefix="")


def _authorized_target(env: Env, *, head: int = 5) -> None:
    """Wires `env.bridge` (a `SpyBridge`) and `env.ctx` with everything `handle_chat_send` needs:
    an AUTHORIZED bot, a resolvable Bot Chat, an empty lease snapshot and a usable endpoint."""
    env.bridge.authz_state = lambda *a, **k: AuthzState.AUTHORIZED
    env.bridge.resolve_bot_chat = lambda *a, **k: BotChatTarget(
        root_session_id="root1",
        live_tip_session_id="tip1",
        head_message_id=head,
        compression_chain=("root1", "tip1"),
    )
    env.bridge.lease_snapshot = lambda *a, **k: []
    env.bridge.direct_send_endpoint = lambda *a, **k: _AN_ENDPOINT
    # DS-7a's post-hoc identity check (`_check_interleave`): a clean read -- our own user row
    # ("hi", matching every scenario's own request text below) immediately followed by our own
    # assistant reply ("hi", matching `_ok_loopback`'s fixed body) -- so a normal end-to-end send
    # never reports a false-positive interleave.
    env.bridge.after = lambda *a, **k: [
        Row(id=head + 1, role="user", text="hi", client_message_id=None, created_at=env.clock.now),
        Row(
            id=head + 2,
            role="assistant",
            text="hi",
            client_message_id=None,
            created_at=env.clock.now,
        ),
    ]
    env.ctx.direct_send_deps = DirectSendDeps(
        bridge=env.bridge,
        store=env.store,
        locks=ProfileLocks(),
        now=lambda: env.clock.now,
        loopback_call=_ok_loopback,
    )


async def _ok_loopback(endpoint: Any, session_id: str, text: str) -> LoopbackResult:
    return LoopbackResult(
        status=200,
        body={"message": {"id": 42, "role": "assistant", "content": "hi"}},
        effective_session_id=session_id,
    )


def test_chat_send_closed_when_flag_disabled(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: False  # OD-F14/OD-F15 default

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 503, body
        assert code(body) == "write_gate_closed"

    run(env, scenario)


def test_e8_chat_send_closed_when_this_hermes_cannot_send_but_reads_still_work(
    tmp_path: Path,
) -> None:
    """The owner's flag is on, but the send dependencies are missing on this Hermes: the route
    answers `write_gate_closed`, the instance gate reports closed, and reads keep working."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True
    env.ctx.send_available = lambda: False

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 503, body
        assert code(body) == "write_gate_closed"
        status, body = await get(client, "/ready")
        assert status == 200 and body["write_gate"]["state"] == "closed"
        status, _ = await get(client, "/bots", headers=env.headers(dev))
        assert status == 200

    run(env, scenario)
    from hmp_plugin.contract import WriteGateState

    assert env.ctx.reported_send_gate("b").state is WriteGateState.CLOSED


def test_chat_send_accepts_end_to_end_when_flag_enabled(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 200, body
        assert body["state"] == "accepted"
        assert body["message_id"] == 42
        assert body["guarantee_level"] == "guarded"

        # DS-8: the lookup route reflects the definitive outcome, scoped to this device's user.
        status2, body2 = await get(
            client, "/bots/b/chat/messages/by-client-id/c1", headers=env.headers(dev)
        )
        assert status2 == 200, body2
        assert body2 == {"state": "accepted", "message_id": 42}

    run(env, scenario)


def test_chat_send_missing_text_is_bad_request(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5},
            headers=env.headers(dev),
        )
        assert status == 400, body
        assert code(body) == "bad_request"

    run(env, scenario)


def test_chat_send_missing_expected_head_is_bad_request(tmp_path: Path) -> None:
    """DS-1: once this route is registered, an `expected_head`-less request is refused, never
    silently treated as "no precondition"."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 400, body
        assert code(body) == "bad_request"

    run(env, scenario)


def test_chat_send_stale_head_is_409(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _authorized_target(env, head=5)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 1, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 409, body
        assert code(body) == "stale_head"

    run(env, scenario)


def test_chat_send_unauthorized_bot_is_refused_before_any_direct_send_call(tmp_path: Path) -> None:
    """ERR-3 first, per SUB-2's gate order -- an unauthorized caller never reaches the guard."""
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *a, **k: AuthzState.PENDING_OPERATOR
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 403, body
        assert code(body) == "forbidden"

    run(env, scenario)


def test_chat_lookup_unknown_cmid(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await get(
            client, "/bots/b/chat/messages/by-client-id/does-not-exist", headers=env.headers(dev)
        )
        assert status == 200, body
        assert body == {"state": "unknown", "message_id": None}

    run(env, scenario)


def test_chat_send_401_closes_the_row_and_lookup_reports_not_accepted(tmp_path: Path) -> None:
    """Review round 2, BLOCKER #1: a 401 from `api_server` is definitive, not left dangling
    `pending` -- and DS-8's lookup reports it as `not_accepted` (Hermes never processed content;
    only auth was refused), never `accepted`/`submitted`."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def unauthorized(endpoint: Any, session_id: str, text: str) -> LoopbackResult:
        return LoopbackResult(status=401, body=None, effective_session_id=None)

    # `DirectSendDeps` is frozen: swap in a fresh one with the same bridge/store/locks, a
    # `loopback_call` that answers 401.
    prior = env.ctx.direct_send_deps
    env.ctx.direct_send_deps = DirectSendDeps(
        bridge=prior.bridge,
        store=prior.store,
        locks=prior.locks,
        now=prior.now,
        loopback_call=unauthorized,
    )

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 503, body
        assert code(body) == "write_gate_closed"

        status2, body2 = await get(
            client, "/bots/b/chat/messages/by-client-id/c1", headers=env.headers(dev)
        )
        assert status2 == 200, body2
        assert body2 == {"state": "not_accepted", "message_id": None}

    run(env, scenario)


def test_chat_lookup_pending_with_no_tracked_task_is_unknown(tmp_path: Path) -> None:
    """Review round 2, BLOCKER #1: a row left `pending` with no live task in THIS process's
    registry (modelling a gateway restart, where a fresh process starts with an empty registry) is
    reported `unknown`, never resent and never reported as still `submitted`."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = env.store.get_device(dev.device_id)["user_id"]
        # Simulate a row that was left pending by a process that no longer exists: reserve it
        # directly on the store, without ever launching a background task for it.
        env.store.reserve_cmid(env.ctx.iid, user_id, "b", "orphaned", b"x" * 32, env.clock.now)

        status, body = await get(
            client, "/bots/b/chat/messages/by-client-id/orphaned", headers=env.headers(dev)
        )
        assert status == 200, body
        assert body == {"state": "unknown", "message_id": None}

    run(env, scenario)


def test_chat_lookup_stored_unknown_matches_a_post_with_no_live_task(tmp_path: Path) -> None:
    """Review round 3: a row finalized `unknown` (cancel/exception) is reported `unknown` by
    DS-8, the same state a POST of that row returns."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = env.store.get_device(dev.device_id)["user_id"]
        env.store.reserve_cmid(env.ctx.iid, user_id, "b", "done", b"x" * 32, env.clock.now)
        env.store.finalize_cmid(
            env.ctx.iid,
            user_id,
            "b",
            "done",
            status="unknown",
            result_json='{"state":"unknown"}',
            updated_at=env.clock.now,
        )
        status, body = await get(
            client, "/bots/b/chat/messages/by-client-id/done", headers=env.headers(dev)
        )
        assert status == 200, body
        assert body == {"state": "unknown", "message_id": None}

    run(env, scenario)


def test_chat_lookup_surfaces_interleave_detected(tmp_path: Path) -> None:
    """Review round 2, BLOCKER #4: `interleave_detected` reaches a caller reconciling through the
    DS-8 lookup route, not only the original synchronous `POST` response."""
    env = Env(tmp_path)
    _authorized_target(env)
    env.ctx.direct_send_flag = lambda: True
    # Override the clean-turn `after()` fixture with one showing a foreign interleaved row.
    env.bridge.after = lambda *a, **k: [
        Row(id=6, role="user", text="hi", client_message_id=None, created_at=env.clock.now),
        Row(
            id=7,
            role="user",
            text="someone else",
            client_message_id=None,
            created_at=env.clock.now,
        ),
        Row(id=8, role="assistant", text="hi", client_message_id=None, created_at=env.clock.now),
    ]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(
            client,
            "/bots/b/chat/messages",
            {"client_message_id": "c1", "expected_head": 5, "text": "hi"},
            headers=env.headers(dev),
        )
        assert status == 200, body
        assert body.get("interleave_detected") is True

        status2, body2 = await get(
            client, "/bots/b/chat/messages/by-client-id/c1", headers=env.headers(dev)
        )
        assert status2 == 200, body2
        assert body2.get("interleave_detected") is True

    run(env, scenario)


def test_reported_write_gate_follows_the_owner_only_direct_send_flag(tmp_path: Path) -> None:
    """The `/ready` diagnostic follows the flag; roster bot gates resolve profiles separately."""
    from hmp_plugin.contract import Guarantees, WriteGateState

    env = Env(tmp_path)
    env.ctx.direct_send_flag = lambda: False
    assert env.ctx.reported_write_gate().state is WriteGateState.CLOSED
    env.ctx.direct_send_flag = lambda: True
    assert env.ctx.reported_write_gate().state is WriteGateState.OPEN_GUARDED
    assert env.ctx.write_gate().state is WriteGateState.CLOSED

    def broken() -> bool:
        raise RuntimeError("config read failed")

    env.ctx.direct_send_flag = broken  # a broken flag reader fails closed
    assert env.ctx.reported_write_gate().state is WriteGateState.CLOSED

    env.ctx.guarantee_cache = Guarantees(no_defer=True, atomic_anchor=True)
    env.ctx.direct_send_flag = lambda: False
    assert env.ctx.write_gate().state is WriteGateState.OPEN
    assert env.ctx.reported_write_gate().state is WriteGateState.CLOSED


def test_reported_send_gate_is_profile_scoped_and_switch_gated(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from hmp_plugin.contract import DirectSendEndpoint, WriteGateState

    env = Env(tmp_path)
    seen: list[str] = []
    endpoint = DirectSendEndpoint("127.0.0.1", 8642, "synthetic-key-for-tests", "")

    def resolve(profile: str):
        seen.append(profile)
        return endpoint if profile == "alpha" else None

    env.bridge.direct_send_endpoint = resolve
    env.ctx.direct_send_deps = SimpleNamespace()
    env.ctx.direct_send_flag = lambda: False
    assert env.ctx.reported_send_gate("alpha").state is WriteGateState.CLOSED
    assert seen == []

    env.ctx.direct_send_flag = lambda: True
    assert env.ctx.reported_send_gate("alpha").state is WriteGateState.OPEN_GUARDED
    assert env.ctx.reported_send_gate("beta").state is WriteGateState.CLOSED
    assert env.ctx.reported_send_gate("alpha").state is WriteGateState.OPEN_GUARDED
    assert seen == ["alpha", "beta", "alpha"]

    env.ctx.send_available = lambda: False
    assert env.ctx.reported_send_gate("alpha").state is WriteGateState.CLOSED
    assert seen == ["alpha", "beta", "alpha"]
