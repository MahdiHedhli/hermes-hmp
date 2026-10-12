"""S5: the authenticated local image fetch route (spec 011; HMP v1 §7e LM-10..LM-16).

Real authenticated aiohttp requests drive the real `GET /hmp/v1/bots/{p}/media/{ref}` over the real
`media_fetch` orchestrator and service, the real `HermesReadBridge` phase methods, the accepted
scanner, file leaf, raster check and registry (bound by the adapter's real `_media_bind`), on a
synthetic native database and real temporary image files. Nothing touches a live Hermes home,
network, provider or device, and no phase is replaced by a canned payload for an authority test:
the bridge wrappers below only observe, delay or block a worker, then call the real method.

Authority tests flip one real fact (a grant, a tip, a row, a file, a registry entry, a flag) between
mint and fetch, or between the two phases, and expect a refusal that the unflipped control does
not give. Expected values are hand-written. Native cost, T12 memory, the independent exact-candidate
review and device acceptance are NOT claimed here.
"""

from __future__ import annotations

import asyncio
import contextvars
import gc
import hashlib
import json
import logging
import os
import re
import socket
import sys
import threading
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import local_media_registry as real_registry
from hmp_plugin import server
from hmp_plugin.logging_policy import AllowListedAccessLogger
from hmp_plugin.revoke import revoke_device

from . import hmp_kit
from .media_binding_world import World as PackageWorld
from .test_local_media_active_batch import independent_digest
from .test_local_media_batch_binding import OTHER_USER, USER, session_row
from .test_local_media_raster_structure import (
    IDAT_OK,
    VALID_JPEG,
    VALID_PNG,
    VALID_VP8,
    chunk,
    ihdr,
    png,
    png_chunks,
)
from .test_s4_descriptors import PROFILE, REF_RE, Rig, caller, media_of

PACKAGE = Path(server.__file__).parent
FETCH = server.media_fetch
CV: contextvars.ContextVar[str] = contextvars.ContextVar("hmp_s5_scope", default="unset")
NOT_FOUND = {"error": {"code": "not_found", "message": "not found"}}
RATE_LIMITED = {"error": {"code": "rate_limited", "message": "rate limited"}}
UNAVAILABLE = {"error": {"code": "media_unavailable", "message": "image delivery is unavailable"}}
VALID_PNG_B = png(png_chunks(color=2))  # a different, valid PNG
TOOL_IDS = (2, 4, 6)  # the three seeded image tool rows (assistant rows are 1, 3, 5)


def big_png(size: int) -> bytes:
    """A structurally valid PNG of about `size` bytes (structure only, never decoded)."""
    return png([ihdr(2, 2), chunk(b"IDAT", IDAT_OK + b"\x00" * size), chunk(b"IEND")])


async def until(predicate: Callable[[], bool], within: float = 5.0) -> None:
    deadline = time.monotonic() + within
    while not predicate():
        assert time.monotonic() < deadline, "condition never held"
        await asyncio.sleep(0.01)


class Fx:
    """One paired-owner rig with real image files, observable (never canned) phase wrappers, and a
    probe middleware that records the handler task and sets a `ContextVar`."""

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        kind: str = "phone",
        images: int = 3,
    ) -> None:
        self.monkeypatch = monkeypatch
        self.rig = Rig(tmp_path, monkeypatch, kind=kind, images=images)
        self.native, self.ctx, self.registry = self.rig.native, self.rig.ctx, self.rig.registry
        self.lock = threading.Lock()
        self.p1_gate: threading.Event | None = None
        self.p2_gate: threading.Event | None = None
        self.p1_in = 0
        self.p2_in = 0
        self.p1_sleep = 0.0
        self.p2_sleep = 0.0
        self.seen: list[tuple[str, str, str]] = []
        self.after_p1: list[Callable[[], None]] = []
        self.before_p2: list[Callable[[], None]] = []
        self.after_p2: list[Callable[[], None]] = []
        self.p1_results: list[Any] = []
        self.tasks: list[asyncio.Task[Any]] = []
        self.starts: list[tuple[Any, str, Any]] = []
        self.grant_threads: list[str] = []
        self.owned_media_services: list[Any] = []
        self.app: web.Application | None = None
        self.server: TestServer | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._wrap()
        for tool_id in TOOL_IDS[: images]:
            self.write(tool_id, VALID_PNG)

    # -- files ---------------------------------------------------------------------------------

    def image_path(self, tool_id: int) -> Path:
        return self.native.home_path / "cache" / "images" / f"img{tool_id - 1}.png"

    def write(self, tool_id: int, data: bytes) -> Path:
        path = self.image_path(tool_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    # -- observation of the real bridge --------------------------------------------------------

    def _wrap(self) -> None:
        bridge = self.native.bridge
        real1, real2 = bridge.media_fetch_phase_one, bridge.media_fetch_phase_two
        real_authz = bridge.authz_state

        def authz(user_id: str, profile: str) -> Any:
            self.grant_threads.append(threading.current_thread().name)
            return real_authz(user_id, profile)

        def one(*args: Any) -> Any:
            with self.lock:
                self.p1_in += 1
                self.seen.append(("p1", threading.current_thread().name, CV.get()))
            gate = self.p1_gate
            if gate is not None:
                assert gate.wait(15)
            if self.p1_sleep:
                time.sleep(self.p1_sleep)
            out = real1(*args)
            self.p1_results.append(type(out).__name__)
            for callback in list(self.after_p1):
                callback()
            return out

        def two(*args: Any) -> Any:
            with self.lock:
                self.p2_in += 1
                self.seen.append(("p2", threading.current_thread().name, CV.get()))
            for callback in list(self.before_p2):
                callback()
            gate = self.p2_gate
            if gate is not None:
                assert gate.wait(15)
            if self.p2_sleep:
                time.sleep(self.p2_sleep)
            out = real2(*args)
            for callback in list(self.after_p2):
                callback()
            return out

        bridge.media_fetch_phase_one = one  # type: ignore[method-assign]
        bridge.media_fetch_phase_two = two  # type: ignore[method-assign]
        bridge.authz_state = authz  # type: ignore[method-assign]

    def _observe_starts(self) -> Callable[[], None]:
        """Record every `_Lease.start` for the duration of ONE run. It is installed only while a
        server runs, never at construction: the listener binder proves `_Lease.start` executes in
        the orchestrator's namespace, so a patched class would (correctly) refuse a later open."""
        real_start = FETCH._Lease.start

        def start(lease: Any, call: Any, payload_type: Any) -> Any:
            status, future = real_start(lease, call, payload_type)
            self.starts.append((lease, status, future))
            self._remember_media_service(lease._service)
            return status, future

        FETCH._Lease.start = start  # type: ignore[method-assign]

        def restore() -> None:
            FETCH._Lease.start = real_start  # type: ignore[method-assign]

        return restore

    def _remember_media_service(self, service: Any) -> None:
        if all(service is not owner for owner in self.owned_media_services):
            self.owned_media_services.append(service)

    def _close_media_admissions_and_release_gates(self) -> None:
        """Fence every retained owner before the first fixture teardown gate release."""
        for service in self.owned_media_services:
            service.close()  # Fence admissions before releasing this rig's held work.
        for gate in (self.p1_gate, self.p2_gate):
            if gate is not None:
                gate.set()

    def _close_owned_media_workers(self) -> None:
        """Close only this rig's retained pools, then prove their bounded actual joins."""
        self._close_media_admissions_and_release_gates()
        workers = {
            worker
            for service in self.owned_media_services
            for worker in tuple(service._executor._threads)
        }
        deadline = time.monotonic() + 20.0  # Existing held fixture jobs are bounded at 15 seconds.
        for worker in workers:
            assert worker is not threading.current_thread()
            worker.join(max(0.0, deadline - time.monotonic()))
        assert not any(worker.is_alive() for worker in workers), "owned media worker did not join"

    @property
    def service(self) -> Any:
        assert self.app is not None
        return self.app[FETCH.MEDIA_SERVICE_KEY]

    # -- running -------------------------------------------------------------------------------

    def run(
        self,
        scenario: Callable[[TestClient], Any],
        *,
        tweak: Callable[[web.Application], None] | None = None,
        logger_names: tuple[str, ...] = (),
    ) -> Any:
        fx = self

        @web.middleware
        async def probe(request: web.Request, handler: Any) -> Any:
            CV.set("scope-alpha")
            if "/media/" in request.path:
                task = asyncio.current_task()
                assert task is not None
                fx.tasks.append(task)
            return await handler(request)

        async def main() -> Any:
            app = self.rig.env.app()
            self._remember_media_service(app[FETCH.MEDIA_SERVICE_KEY])
            app.middlewares.append(probe)
            if tweak is not None:
                tweak(app)
            selected = app.get(FETCH.MEDIA_SERVICE_KEY)
            if type(selected) is FETCH.MediaFetchService:
                self._remember_media_service(selected)
            test_server = TestServer(app)
            await test_server.start_server(
                access_log_class=AllowListedAccessLogger,
                access_log=logging.getLogger(server.ACCESS_LOGGER_NAME),
            )
            self.app, self.server, self.loop = app, test_server, asyncio.get_running_loop()
            async with TestClient(test_server) as client:
                try:
                    return await scenario(client)
                finally:
                    self._close_media_admissions_and_release_gates()

        del logger_names
        restore = self._observe_starts()
        try:
            return asyncio.run(main())
        finally:
            restore()
            self._close_owned_media_workers()

    # -- requests ------------------------------------------------------------------------------

    async def mint(
        self, client: TestClient, dev: hmp_kit.Device | None = None, route: str | None = None
    ) -> dict[int, str]:
        dev = dev or self.rig.device
        assert dev is not None
        name = route or ("ro3" if self.rig.kind == "phone" else "ses2")
        resp = await client.get(
            hmp_kit.url(self.rig.routes()[name]), headers=self.rig.env.headers(dev)
        )
        body = await resp.read()
        assert resp.status == 200, body
        return {row: d["ref"] for row, d in media_of(body).items()}

    async def get(
        self,
        client: TestClient,
        ref: str,
        *,
        dev: hmp_kit.Device | None = None,
        profile: str = PROFILE,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        suffix: str = "",
        **kw: Any,
    ) -> tuple[int, Any, bytes]:
        dev = dev or self.rig.device
        assert dev is not None
        merged = self.rig.env.headers(dev)
        merged.update(headers or {})
        resp = await client.request(
            method, hmp_kit.url(f"/bots/{profile}/media/{ref}{suffix}"), headers=merged, **kw
        )
        return resp.status, resp.headers, await resp.read()

    async def served(self, client: TestClient, ref: str, **kw: Any) -> bytes:
        status, _headers, body = await self.get(client, ref, **kw)
        assert status == 200, body
        return body

    async def refused(self, client: TestClient, ref: str, **kw: Any) -> bytes:
        status, _headers, body = await self.get(client, ref, **kw)
        assert status == 404 and json.loads(body) == NOT_FOUND, (status, body)
        return body


def png_signature(body: bytes) -> bool:
    return body.startswith(b"\x89PNG\r\n\x1a\n")


# ---------------------------------------------------------------------------------------------
# LM-14 success: exact bytes and headers, every structural MIME, both session kinds
# ---------------------------------------------------------------------------------------------

FORBIDDEN_HEADERS = (
    "Content-Disposition",
    "ETag",
    "Last-Modified",
    "Accept-Ranges",
    "Content-Range",
    "Set-Cookie",
)


@pytest.mark.parametrize(
    ("kind", "data", "mime"),
    [
        ("phone", VALID_PNG, "image/png"),
        ("phone", VALID_JPEG, "image/jpeg"),
        ("phone", VALID_VP8, "image/webp"),
        ("bot", VALID_PNG, "image/png"),
        ("bot", VALID_JPEG, "image/jpeg"),
    ],
)
def test_success_streams_the_exact_bytes_with_the_exact_headers(
    kind: str, data: bytes, mime: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch, kind=kind)
    fx.write(6, data)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        status, headers, body = await fx.get(client, refs[6])
        assert status == 200 and body == data
        assert headers["Content-Type"] == mime  # exactly the structural MIME, no charset
        assert headers["Content-Length"] == str(len(data))
        assert headers["Cache-Control"] == "no-store, private"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Server"] == "hmp"
        for name in FORBIDDEN_HEADERS:
            assert name not in headers, name

    fx.run(scenario)


def test_range_is_ignored_and_the_full_body_is_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        for value in ("bytes=0-3", "bytes=-2", "bytes=999999-"):
            status, headers, body = await fx.get(client, refs[6], headers={"Range": value})
            assert (status, body) == (200, VALID_PNG)
            assert "Content-Range" not in headers and "Accept-Ranges" not in headers

    fx.run(scenario)


def test_a_repeat_fetch_of_the_same_unchanged_file_is_served_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        for _ in range(3):
            assert await fx.served(client, refs[4]) == VALID_PNG
        entry = fx.registry.lookup(refs[4], caller(fx.rig, fx.rig.device.device_id))  # type: ignore[union-attr]
        assert entry is not None and entry.first_served == hashlib.sha256(VALID_PNG).digest()

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# LM-10 order and LM-3 closed states
# ---------------------------------------------------------------------------------------------


def test_a_non_owner_gets_404_before_the_gate_even_when_everything_else_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        control = await fx.served(client, refs[6])
        assert control == VALID_PNG
        fx.rig.owners.discard(dev.device_id)  # type: ignore[arg-type]
        fx.rig.flag = False  # the gate is closed too: a non-owner must still see only 404
        fx.ctx.media_available = lambda: False
        body = await fx.refused(client, refs[6])
        assert body == await fx.refused(client, "A" * 43)  # no oracle between ref states
        assert fx.p1_in == 1  # the control only: no worker ran for the non-owner

    fx.run(scenario)


@pytest.mark.parametrize("closed", ["flag", "availability", "service_missing", "service_closed"])
def test_an_owner_with_a_closed_gate_gets_503_media_unavailable(
    closed: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    def tweak(app: web.Application) -> None:
        if closed == "service_missing":
            app._state.pop(FETCH.MEDIA_SERVICE_KEY)
        if closed == "service_closed":
            app[FETCH.MEDIA_SERVICE_KEY].close()

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        if closed == "flag":
            fx.rig.flag = False
        if closed == "availability":
            fx.ctx.media_available = lambda: False
        status, _h, body = await fx.get(client, refs[6])
        assert (status, json.loads(body)) == (503, UNAVAILABLE)
        assert fx.p1_in == 0 and fx.p2_in == 0  # no native phase, no permit

    fx.run(scenario, tweak=tweak)


def test_flag_off_precedes_a_bad_ref_and_a_good_ref_under_a_closed_flag_is_still_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.rig.flag = False
        for ref in (refs[6], "A" * 43, "not-a-ref"):
            status, _h, body = await fx.get(client, ref)
            assert (status, json.loads(body)) == (503, UNAVAILABLE)

    fx.run(scenario)


def test_bearer_comes_first_with_the_existing_401_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        url = hmp_kit.url(f"/bots/{PROFILE}/media/{refs[6]}")
        resp = await client.get(url, headers={"HMP-Instance": fx.rig.env.iid})
        assert resp.status == 401
        assert json.loads(await resp.read())["error"]["code"] == "unauthenticated"
        resp = await client.get(url)
        assert resp.status == 401
        assert json.loads(await resp.read())["error"]["code"] == "wrong_instance"
        resp = await client.get(url, headers=fx.rig.env.headers(dev, iid="x" * 20))
        assert resp.status == 401
        assert json.loads(await resp.read())["error"]["code"] == "wrong_instance"
        revoke_device(fx.rig.env.store, dev.device_id, now=fx.rig.env.clock.now)  # type: ignore[arg-type]
        resp = await client.get(url, headers=fx.rig.env.headers(dev))
        assert resp.status == 401 and json.loads(await resp.read())["error"]["code"] == "revoked"
        assert fx.p1_in == 0

    fx.run(scenario)


@pytest.mark.parametrize("mode", ["query", "body", "chunked", "transfer_encoding_header"])
def test_query_body_and_transfer_encoding_are_400_for_an_owner(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        kw: dict[str, Any] = {}
        suffix = ""
        if mode == "query":
            suffix = "?a=b"
        elif mode == "body":
            kw["data"] = b"x"
        elif mode == "chunked":

            async def gen() -> Any:
                yield b"abc"

            kw["data"] = gen()
        else:
            kw["headers"] = {"Transfer-Encoding": "chunked"}
        status, _h, body = await fx.get(client, refs[6], suffix=suffix, **kw)
        assert status == 400 and json.loads(body)["error"]["code"] == "bad_request", mode
        assert fx.p1_in == 0

    fx.run(scenario)


def test_a_bare_question_mark_is_also_a_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert fx.server is not None
        loop = asyncio.get_running_loop()
        sock = socket.socket()
        sock.setblocking(False)
        await loop.sock_connect(sock, (fx.server.host, fx.server.port))
        raw = _raw_get(fx, refs[6], dev).replace(b" HTTP/1.1", b"? HTTP/1.1", 1)
        await loop.sock_sendall(sock, raw)
        reply = b""
        while b"bad_request" not in reply and len(reply) < 4096:
            chunk = await asyncio.wait_for(loop.sock_recv(sock, 4096), 5)
            if not chunk:
                break
            reply += chunk
        sock.close()
        assert reply.startswith(b"HTTP/1.1 400") and b"bad_request" in reply
        assert fx.p1_in == 0

    fx.run(scenario)


def test_the_shape_check_runs_after_the_owner_check_and_before_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.rig.flag = False  # closed gate, owner: the shape error still comes first (step 3 < 6)
        status, _h, body = await fx.get(client, refs[6], suffix="?x=1")
        assert status == 400
        fx.rig.owners.discard(dev.device_id)  # type: ignore[arg-type]
        status, _h, body = await fx.get(client, refs[6], suffix="?x=1")  # step 2 < 3
        assert (status, json.loads(body)) == (404, NOT_FOUND)

    fx.run(scenario)


@pytest.mark.parametrize("method", ["HEAD", "POST", "PUT", "DELETE", "PATCH"])
def test_other_methods_get_the_existing_404(
    method: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        status, _h, body = await fx.get(client, refs[6], method=method)
        assert status == 404
        if method != "HEAD":
            assert json.loads(body) == NOT_FOUND
        assert fx.p1_in == 0

    fx.run(scenario)


def test_the_rate_limit_is_120_per_minute_per_device_and_precedes_the_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        other = await fx.rig.pair(client)
        for _ in range(120):
            await fx.refused(client, "A" * 43, dev=dev)
        grants = len(fx.grant_threads)
        status, _h, body = await fx.get(client, "A" * 43, dev=dev)
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        assert len(fx.grant_threads) == grants  # refused before any native grant call
        await fx.refused(client, "A" * 43, dev=other)  # another device has its own budget

    fx.run(scenario)


def test_the_initial_grant_keeps_err3_and_precedes_the_media_gate_and_ref_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.rig.flag = False  # a closed gate AND a refused grant: ERR-3 must win
        fx.native.world.runner.approved[PROFILE].discard(USER)
        status, _h, body = await fx.get(client, refs[6])
        assert status == 403
        assert json.loads(body) == {
            "error": {
                "code": "forbidden",
                "message": "forbidden",
                "authz": "pending_operator",
            }
        }
        fx.native.world.approve(USER, PROFILE)
        fx.native.world.runner.authz_raises = True
        status, _h, body = await fx.get(client, "A" * 43)
        error = json.loads(body)["error"]
        assert status == 503 and error["code"] == "other" and error["authz"] == "unverifiable"
        assert error["why"] == "unverifiable"
        fx.native.world.runner.authz_raises = False
        status, _h, body = await fx.get(client, "A" * 43, profile="lonely")
        assert (status, json.loads(body)) == (409, {
            "error": {
                "code": "not_routed", "message": "bot is not served by this instance",
                "authz": "not_routed",
            }
        })
        assert fx.p1_in == 0

    fx.run(scenario)


def test_the_initial_grant_runs_on_the_default_executor_not_the_media_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.grant_threads.clear()
        await fx.served(client, refs[6])
        names = fx.grant_threads
        assert names and not any(n.startswith("hmp-media") for n in names[:1])
        # phases 1 and 2 re-authorize on the dedicated media executor
        assert any(n.startswith("hmp-media") for n in names[1:])

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# LM-9 ref binding: one 404 shape for every foreign or dead ref (T2)
# ---------------------------------------------------------------------------------------------


def test_a_ref_used_by_another_device_user_or_profile_or_after_expiry_is_one_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    fx.native.world.approve(USER, "beta")

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        other = await fx.rig.pair(client)  # same user, another owner device
        refs = await fx.mint(client, dev)
        control = await fx.served(client, refs[6], dev=dev)
        assert control == VALID_PNG
        bodies = {
            "device": await fx.refused(client, refs[6], dev=other),
            "profile": await fx.refused(client, refs[6], profile="beta"),
        }
        # another USER: the same registry, a different bound user
        foreign_user = fx.registry.mint(
            real_registry.Binding(
                device_id=dev.device_id,  # type: ignore[arg-type]
                user_id=OTHER_USER,
                instance_id=fx.rig.env.iid,
                profile=PROFILE,
                kind=real_registry.SessionKind.PHONE,
                session_id=fx.rig.session,
                tip=fx.rig.tip,
                tool_row_id=6,
                raw_digest=fx.native.digests[6],
            )
        )
        bodies["user"] = await fx.refused(client, foreign_user)
        # another INSTANCE: bound to a different iid
        foreign_iid = fx.registry.mint(
            real_registry.Binding(
                device_id=dev.device_id,  # type: ignore[arg-type]
                user_id=USER,
                instance_id="i" * 20,
                profile=PROFILE,
                kind=real_registry.SessionKind.PHONE,
                session_id=fx.rig.session,
                tip=fx.rig.tip,
                tool_row_id=6,
                raw_digest=fx.native.digests[6],
            )
        )
        bodies["instance"] = await fx.refused(client, foreign_iid)
        bodies["unknown"] = await fx.refused(client, "A" * 43)
        bodies["grammar"] = await fx.refused(client, "short")
        fx.registry._clock = lambda: time.monotonic() + 1801  # past the 1800 s TTL
        bodies["expired"] = await fx.refused(client, refs[6], dev=dev)
        assert len(set(bodies.values())) == 1, sorted(bodies)  # no oracle between the causes
        assert fx.p1_in == 1  # only the control ever reached a worker

    fx.run(scenario)


def test_an_evicted_entry_is_a_404_and_the_other_refs_still_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        with fx.registry._lock:
            fx.registry._remove(refs[6])  # an LRU eviction
        await fx.refused(client, refs[6])
        assert await fx.served(client, refs[4]) == VALID_PNG

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# Phase one: every native/file/raster fact is re-proven on the real bridge (T4, T5, T7, T8, T9)
# ---------------------------------------------------------------------------------------------


def _row(fx: Fx, row_id: int) -> dict[str, Any]:
    return next(r for r in fx.native.db.messages[fx.rig.tip] if r["id"] == row_id)


def _grant_revoked(fx: Fx) -> None:
    fx.native.world.runner.approved[PROFILE].discard(USER)


def _tip_moved(fx: Fx) -> None:
    db, tip = fx.native.db, fx.rig.tip
    db.sessions["p3"] = session_row("p3", parent=tip)
    db.compression[tip] = "p3"
    db.messages["p3"] = list(db.messages[tip])


def _title_lost(fx: Fx) -> None:
    fx.native.db.sessions["C"]["title"] = None  # the canonical Bot Chat title moved away


def _content_changed(fx: Fx) -> None:
    row = _row(fx, 6)
    row["content"] = row["content"].replace("img5", "imgX")


def _declaration_removed(fx: Fx) -> None:
    fx.native.db.messages[fx.rig.tip][:] = [
        r for r in fx.native.db.messages[fx.rig.tip] if r["id"] != 5
    ]


def _row_removed(fx: Fx) -> None:
    fx.native.db.messages[fx.rig.tip][:] = [
        r for r in fx.native.db.messages[fx.rig.tip] if r["id"] != 6
    ]


def _row_renamed(fx: Fx) -> None:
    _row(fx, 6)["tool_name"] = "other_tool"


def _image_outside_cache(fx: Fx) -> None:
    row = _row(fx, 6)
    row["content"] = '{"success": true, "image": "/tmp/elsewhere.png"}'


PHASE_ONE_FACTS = {
    "grant": ("phone", _grant_revoked),
    "tip": ("phone", _tip_moved),
    "bot_title": ("bot", _title_lost),
    "digest": ("phone", _content_changed),
    "declaration": ("phone", _declaration_removed),
    "row_gone": ("phone", _row_removed),
    "tool_name": ("phone", _row_renamed),
    "outside_cache": ("phone", _image_outside_cache),
}


@pytest.mark.parametrize("fact", sorted(PHASE_ONE_FACTS))
def test_a_changed_native_fact_before_the_fetch_is_a_404_and_the_control_serves(
    fact: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kind, flip = PHASE_ONE_FACTS[fact]
    fx = Fx(tmp_path, monkeypatch, kind=kind)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG  # the unflipped control
        flip(fx)
        if fact == "grant":  # the INITIAL grant refuses first: ERR-3, not the phase-one 404
            status, _h, body = await fx.get(client, refs[6])
            assert status == 403 and json.loads(body)["error"]["authz"] == "pending_operator"
        else:
            await fx.refused(client, refs[6])
        assert fx.p2_in == 1  # only the control reached phase two

    fx.run(scenario)


def test_a_ref_forced_into_the_registry_for_an_image_outside_the_cache_is_a_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T7: the strict row says `/tmp/elsewhere.png` and its digest is bound correctly, so the scan
    passes; only the lexical derivation against the captured home refuses, never a file read."""
    fx = Fx(tmp_path, monkeypatch)
    outside = fx.native.home_path.parent / "outside.png"
    outside.write_bytes(VALID_PNG)
    content = '{"success": true, "image": "' + str(outside) + '"}'
    _row(fx, 6)["content"] = content
    digest = independent_digest(6, "image_generate", "c5", content)
    assert digest != fx.native.digests[6]

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        ref = fx.registry.mint(
            real_registry.Binding(
                device_id=dev.device_id,  # type: ignore[arg-type]
                user_id=USER,
                instance_id=fx.rig.env.iid,
                profile=PROFILE,
                kind=real_registry.SessionKind.PHONE,
                session_id=fx.rig.session,
                tip=fx.rig.tip,
                tool_row_id=6,
                raw_digest=digest,
            )
        )
        await fx.refused(client, ref)
        assert fx.p1_results == ["NoneType"]  # phase one refused (no payload ever existed)

    fx.run(scenario)


def test_assistant_media_text_never_gives_a_file_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T6: the cache holds a real image that only an assistant `MEDIA:` string names. No tool row,
    so no descriptor was minted; a ref forced for the assistant row id gets nothing either."""
    fx = Fx(tmp_path, monkeypatch)
    rows = fx.native.db.messages[fx.rig.tip]
    path = fx.native.home_path / "cache" / "images" / "only-assistant.png"
    path.write_bytes(VALID_PNG)
    rows.append({"id": 90, "role": "assistant", "content": f"MEDIA:{path}", "active": 1})

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert set(refs) == set(TOOL_IDS)  # no descriptor for the assistant row
        ref = fx.registry.mint(
            real_registry.Binding(
                device_id=dev.device_id,  # type: ignore[arg-type]
                user_id=USER,
                instance_id=fx.rig.env.iid,
                profile=PROFILE,
                kind=real_registry.SessionKind.PHONE,
                session_id=fx.rig.session,
                tip=fx.rig.tip,
                tool_row_id=90,
                raw_digest=b"\x00" * 32,
            )
        )
        await fx.refused(client, ref)

    fx.run(scenario)


def _symlink(fx: Fx) -> None:
    path = fx.image_path(6)
    target = path.parent / "real.png"
    target.write_bytes(VALID_PNG)
    path.unlink()
    path.symlink_to(target)


def _missing(fx: Fx) -> None:
    fx.image_path(6).unlink()


def _empty(fx: Fx) -> None:
    fx.image_path(6).write_bytes(b"")


def _oversize(fx: Fx) -> None:
    fx.image_path(6).write_bytes(VALID_PNG + b"\x00" * (8 * 1024 * 1024))


def _hardlink(fx: Fx) -> None:
    os.link(fx.image_path(6), fx.image_path(6).parent / "second-link.png")


def _not_a_raster(fx: Fx) -> None:
    fx.image_path(6).write_bytes(b"GIF89a not a png jpeg or webp")


def _animated(fx: Fx) -> None:
    chunks = [ihdr(2, 2), chunk(b"acTL", b"\0" * 8), chunk(b"IDAT", IDAT_OK), chunk(b"IEND")]
    fx.image_path(6).write_bytes(png(chunks))


def _images_dir_symlink(fx: Fx) -> None:
    images = fx.image_path(6).parent
    moved = images.parent / "images-real"
    images.rename(moved)
    images.symlink_to(moved, target_is_directory=True)


FILE_FACTS = {
    "symlink": _symlink,
    "missing": _missing,
    "empty": _empty,
    "oversize": _oversize,
    "hardlink": _hardlink,
    "not_a_raster": _not_a_raster,
    "animated_png": _animated,
    "images_dir_symlink": _images_dir_symlink,
}


@pytest.mark.parametrize("fact", sorted(FILE_FACTS))
def test_an_unsafe_or_invalid_file_is_a_404_with_no_bytes(
    fact: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        FILE_FACTS[fact](fx)
        body = await fx.refused(client, refs[6])
        assert VALID_PNG[:8] not in body and fx.p2_in == 0  # phase two never ran

    fx.run(scenario)


def test_the_file_is_read_with_the_exact_captured_home_not_a_normalized_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A home spelled with a `..` detour is never normalized: the scanned row's image string no
    longer starts with the captured home string, so the lexical check refuses."""
    fx = Fx(tmp_path, monkeypatch)
    detour = str(fx.native.home_path) + "/../" + fx.native.home_path.name
    row = _row(fx, 6)
    row["content"] = '{"success": true, "image": "' + detour + '/cache/images/img5.png"}'
    digest = independent_digest(6, "image_generate", "c5", row["content"])

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        ref = fx.registry.mint(
            real_registry.Binding(
                device_id=dev.device_id,  # type: ignore[arg-type]
                user_id=USER,
                instance_id=fx.rig.env.iid,
                profile=PROFILE,
                kind=real_registry.SessionKind.PHONE,
                session_id=fx.rig.session,
                tip=fx.rig.tip,
                tool_row_id=6,
                raw_digest=digest,
            )
        )
        await fx.refused(client, ref)

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# First-served digest CAS (T8)
# ---------------------------------------------------------------------------------------------


def test_a_file_replaced_after_the_first_200_is_a_404_and_the_entry_is_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[6]) == VALID_PNG
        fx.write(6, VALID_PNG_B)  # structurally valid but different bytes
        await fx.refused(client, refs[6])
        fx.write(6, VALID_PNG)  # the original is restored: the entry is already gone
        await fx.refused(client, refs[6])
        assert fx.registry.lookup(refs[6], caller(fx.rig, dev.device_id)) is None  # type: ignore[arg-type]
        assert await fx.served(client, refs[4]) == VALID_PNG  # other refs unaffected

    fx.run(scenario)


def test_concurrent_first_fetches_serve_at_most_one_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p2_gate = threading.Event()
        first = asyncio.create_task(fx.get(client, refs[6]))  # reads v1, parks in phase two
        await until(lambda: fx.p2_in >= 1)
        fx.write(6, VALID_PNG_B)  # the file changes while request A is parked
        gate_a, fx.p2_gate = fx.p2_gate, None
        status, _h, body = await fx.get(client, refs[6])  # B reads v2 and finishes first
        assert (status, body) == (200, VALID_PNG_B)
        gate_a.set()
        status_a, _h, body_a = await first
        assert status_a == 404 and json.loads(body_a) == NOT_FOUND  # A's v1 digest lost the CAS

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# Phase two and the synchronous final section: late causal changes refuse (T3, T9)
# ---------------------------------------------------------------------------------------------


def _late(fx: Fx, action: Callable[[], None]) -> None:
    fx.after_p1.append(action)  # runs in the worker after phase one returned its payload


def test_a_grant_revoked_between_the_phases_is_a_404_not_the_err3_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        _late(fx, lambda: _grant_revoked(fx))
        await fx.refused(client, refs[6])
        assert fx.p1_in == 1 and fx.p2_in == 1  # phase two ran and refused

    fx.run(scenario)


def test_a_tip_change_between_the_phases_is_a_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase two re-proves grant, eligibility and tip (LM-11). A single tool row changed after the
    phase-one recheck is outside phase two's scope (it holds no row authority): that residual is
    the contract's stated non-atomic window, covered by the phase-one recheck, not here."""
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        _late(fx, lambda: _tip_moved(fx))
        await fx.refused(client, refs[6])
        assert fx.p1_in == 1 and fx.p2_in == 1

    fx.run(scenario)


@pytest.mark.parametrize("fact", ["digest", "declaration"])
def test_a_row_change_during_phase_one_after_the_read_is_caught_by_the_phase_one_recheck(
    fact: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The accepted `recheck` runs after the file read: a tool row (or its declaration) that
    changes while the file is being read is refused inside phase one, before any phase two."""
    fx = Fx(tmp_path, monkeypatch)
    flips = {"digest": _content_changed, "declaration": _declaration_removed}
    leaf = fx.ctx.media_modules[0][4]  # the accepted file-leaf module (chain member 4)
    real_read, armed = leaf.read_profile_cache_image, []

    def read_then_change(*args: Any, **kw: Any) -> Any:
        out = real_read(*args, **kw)  # the REAL leaf reads the REAL file first
        if armed:
            flips[fact](fx)
        return out

    monkeypatch.setattr(leaf, "read_profile_cache_image", read_then_change)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG  # control: same hook, nothing armed
        armed.append(True)
        await fx.refused(client, refs[6])
        assert fx.p2_in == 1 and fx.p1_results == ["MediaPayload", "NoneType"]

    fx.run(scenario)


def test_an_eligibility_change_between_the_phases_is_a_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch, kind="bot")

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        _late(fx, lambda: _title_lost(fx))
        await fx.refused(client, refs[6])

    fx.run(scenario)


def test_a_device_revoked_after_phase_two_gets_the_existing_401_and_no_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T3: the final fresh bearer check catches a revocation that landed after the last native
    check; without that check the response would be a 200 with the image."""
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.after_p2.append(
            lambda: revoke_device(fx.rig.env.store, dev.device_id, now=fx.rig.env.clock.now)  # type: ignore[arg-type]
        )
        status, _h, body = await fx.get(client, refs[6])
        assert status == 401 and json.loads(body)["error"]["code"] == "revoked"
        assert not png_signature(body)

    fx.run(scenario)


def test_an_access_token_that_expires_during_the_fetch_is_a_401(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.after_p2.append(lambda: setattr(fx.rig.env.clock, "now", fx.rig.env.clock.now + 100000))
        status, _h, body = await fx.get(client, refs[6])
        assert status == 401 and json.loads(body)["error"]["code"] == "unauthenticated"

    fx.run(scenario)


def _owner_removed(fx: Fx) -> None:
    fx.rig.owners.clear()


def _flag_off(fx: Fx) -> None:
    fx.rig.flag = False


def _availability_closed(fx: Fx) -> None:
    fx.ctx.media_registry = object()  # a foreign registry: the use-time fence closes the listener


def _raster_swapped(fx: Fx) -> None:
    fx.ctx.media_raster_module = sys.modules[__name__]  # a foreign raster module


def _payload_swapped(fx: Fx) -> None:
    fx.ctx.media_payload_module = sys.modules[__name__]


def _fetch_swapped(fx: Fx) -> None:
    fx.ctx.media_fetch_module = sys.modules[__name__]


def _entry_expired(fx: Fx) -> None:
    fx.registry._clock = lambda: time.monotonic() + 1801


def _entry_evicted(fx: Fx) -> None:
    for ref in list(fx.registry._entries):
        with fx.registry._lock:
            fx.registry._remove(ref)


def _service_replaced(fx: Fx) -> None:
    assert fx.app is not None
    replacement = FETCH.MediaFetchService()
    fx._remember_media_service(replacement)
    fx.app._state[FETCH.MEDIA_SERVICE_KEY] = replacement


def _service_closed(fx: Fx) -> None:
    fx.service.close()


LOOP_FACTS = {
    "owner": _owner_removed,
    "flag": _flag_off,
    "availability": _availability_closed,
    "raster": _raster_swapped,
    "payload": _payload_swapped,
    "fetch_module": _fetch_swapped,
    "ttl": _entry_expired,
    "eviction": _entry_evicted,
    "service_replaced": _service_replaced,
    "service_closed": _service_closed,
}


@pytest.mark.parametrize("fact", sorted(LOOP_FACTS))
def test_each_loop_side_fact_that_changes_after_phase_two_refuses_with_no_bytes(
    fact: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.after_p2.append(lambda: LOOP_FACTS[fact](fx))
        status, _h, body = await fx.get(client, refs[6])
        assert status == 404 and json.loads(body) == NOT_FOUND, (fact, status)
        assert not png_signature(body) and fx.p2_in == 1

    fx.run(scenario)


def test_the_loop_side_checks_have_a_working_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.after_p2.append(lambda: None)  # the same hook with no change
        assert await fx.served(client, refs[6]) == VALID_PNG

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# Workers, executors and copied ContextVars (T9, T17)
# ---------------------------------------------------------------------------------------------


def test_both_phases_run_on_the_dedicated_executor_with_the_callers_contextvar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.seen.clear()
        assert CV.get() == "unset"  # the test's own context never had the value
        await fx.served(client, refs[6])
        assert [s[0] for s in fx.seen] == ["p1", "p2"]
        for _phase, thread, value in fx.seen:
            assert thread.startswith("hmp-media") and value == "scope-alpha"
        assert threading.main_thread().name not in {s[1] for s in fx.seen}

    fx.run(scenario)


def test_the_executor_is_per_app_with_at_most_four_workers_and_lazy_threads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    first = fx.rig.env.app()
    second = fx.rig.env.app()
    one, two = first[FETCH.MEDIA_SERVICE_KEY], second[FETCH.MEDIA_SERVICE_KEY]
    assert one is not two and one._executor is not two._executor  # never module-global
    assert one._executor._max_workers == 4 == FETCH.MEDIA_WORKERS
    assert len(one._executor._threads) == 0  # no thread until a submission
    assert not any(isinstance(v, FETCH.MediaFetchService) for v in vars(FETCH).values())


def test_a_phase_one_worker_fault_is_a_fixed_404_and_drops_the_buffer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)

        def boom() -> None:
            raise RuntimeError("SENTINEL-PRIVATE-9f3a /tmp/secret path")

        fx.after_p1.append(boom)  # the real phase one already produced a payload
        body = await fx.refused(client, refs[6])
        assert b"SENTINEL" not in body and fx.p2_in == 0
        _lease, _status, future = fx.starts[-1]
        assert future.result(5) is False
        assert fx.service.stats() == (0, 0, 0)  # permits returned, nothing leaked
        assert _lease._payload is None

    fx.run(scenario)


def test_a_phase_two_worker_fault_is_a_fixed_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)

        def boom() -> None:
            raise RuntimeError("private")

        fx.after_p2.append(boom)
        await fx.refused(client, refs[6])
        assert fx.service.stats() == (0, 0, 0)

    fx.run(scenario)


def test_the_worker_future_returns_a_bool_never_the_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        await fx.served(client, refs[6])
        results = [future.result(5) for _l, _s, future in fx.starts]
        assert results == [True, True]
        assert all(type(r) is bool for r in results)  # no completed future retains 8 MiB

    fx.run(scenario)


def test_the_shared_20_second_deadline_is_one_budget_across_both_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WORKER_WAIT_S", 0.9)
    results: dict[str, int] = {}
    for label, p1, p2 in (("within", 0.25, 0.25), ("exceeds", 0.6, 0.6)):
        sub = tmp_path / label
        sub.mkdir()
        fx = Fx(sub, monkeypatch)
        fx.p1_sleep, fx.p2_sleep = p1, p2

        async def scenario(client: TestClient, fx: Fx = fx, label: str = label) -> None:
            await fx.rig.pair(client)
            refs = await fx.mint(client)
            status, _h, _b = await fx.get(client, refs[6])
            results[label] = status
            await until(lambda: fx.service.stats() == (0, 0, 0))

        fx.run(scenario)
    # each phase alone fits the 0.9 s budget (0.6 < 0.9) but the two together do not (1.2 > 0.9)
    assert results == {"within": 200, "exceeds": 404}


# ---------------------------------------------------------------------------------------------
# Permits: 2 per device, 4 per instance, 4 workers; held through cancellation (T10, LM-13)
# ---------------------------------------------------------------------------------------------


def test_a_third_concurrent_fetch_for_one_device_is_429_with_no_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p1_gate = threading.Event()
        held = [asyncio.create_task(fx.get(client, refs[r])) for r in (6, 4)]
        await until(lambda: fx.p1_in == 2)
        status, _h, body = await fx.get(client, refs[2])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        assert "why" not in json.loads(body)["error"]
        fx.p1_gate.set()
        assert [r[0] for r in await asyncio.gather(*held)] == [200, 200]
        await until(lambda: fx.service.stats() == (0, 0, 0))
        assert await fx.served(client, refs[2]) == VALID_PNG  # permits came back

    fx.run(scenario)


def test_a_fifth_instance_buffer_is_429_across_devices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        devs = [await fx.rig.pair(client) for _ in range(3)]
        refs = [await fx.mint(client, d) for d in devs]
        fx.p1_gate = threading.Event()
        held = [
            asyncio.create_task(fx.get(client, refs[i][r], dev=devs[i]))
            for i, r in ((0, 6), (0, 4), (1, 6), (1, 4))
        ]
        await until(lambda: fx.p1_in == 4)
        status, _h, body = await fx.get(client, refs[2][6], dev=devs[2])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        assert fx.p1_in == 4  # the fifth never reached a worker
        fx.p1_gate.set()
        assert [r[0] for r in await asyncio.gather(*held)] == [200] * 4

    fx.run(scenario)


def test_a_cancelled_handler_keeps_its_permits_until_the_worker_really_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p1_gate = threading.Event()
        victim = asyncio.create_task(fx.get(client, refs[6]))
        await until(lambda: fx.p1_in == 1 and len(fx.tasks) >= 1)  # the probe records /media/ tasks
        fx.tasks[-1].cancel()  # the server cancels the handler while its worker is still running
        await asyncio.gather(victim, return_exceptions=True)
        await asyncio.sleep(0.1)
        assert fx.service.stats() == (1, 1, 1)  # buffer, device and worker permits all still held
        # the device has a second slot, then no more: cancellation freed nothing early
        second = asyncio.create_task(fx.get(client, refs[4], dev=dev))
        await until(lambda: fx.p1_in == 2)
        status, _h, body = await fx.get(client, refs[2])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        fx.p1_gate.set()
        assert (await second)[0] == 200
        await until(lambda: fx.service.stats() == (0, 0, 0))
        lease, _status, future = fx.starts[0]
        assert future.result(5) is False  # the late worker published nothing to a finished lease
        assert lease._payload is None and lease._finished and lease._released

    fx.run(scenario)


def test_four_cancelled_late_workers_block_every_new_buffer_until_they_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        devs = [await fx.rig.pair(client) for _ in range(3)]
        refs = [await fx.mint(client, d) for d in devs]
        fx.p1_gate = threading.Event()
        started = [
            asyncio.create_task(fx.get(client, refs[i][r], dev=devs[i]))
            for i, r in ((0, 6), (0, 4), (1, 6), (1, 4))
        ]
        await until(lambda: fx.p1_in == 4 and len(fx.tasks) >= 4)
        for task in fx.tasks[-4:]:
            task.cancel()
        await asyncio.gather(*started, return_exceptions=True)
        assert fx.service.stats() == (4, 4, 2)
        status, _h, body = await fx.get(client, refs[2][6], dev=devs[2])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)  # no 5th 8 MiB buffer starts
        assert fx.p1_in == 4
        fx.p1_gate.set()
        await until(lambda: fx.service.stats() == (0, 0, 0))
        assert await fx.served(client, refs[2][6], dev=devs[2]) == VALID_PNG
        assert all(lease._payload is None for lease, _s, _f in fx.starts)

    fx.run(scenario)


def test_a_timed_out_phase_one_keeps_its_permits_and_never_exposes_late_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WORKER_WAIT_S", 0.3)
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p1_gate = threading.Event()
        await fx.refused(client, refs[6])  # the shared 20 s wait (here 0.3 s) expired: 404
        assert fx.service.stats() == (1, 1, 1)  # the worker is really still running
        assert fx.p2_in == 0
        fx.p1_gate.set()
        await until(lambda: fx.service.stats() == (0, 0, 0))
        lease, _status, future = fx.starts[0]
        assert future.result(5) is False and lease._payload is None

    fx.run(scenario)


def test_a_timed_out_phase_two_keeps_its_permits_until_it_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WORKER_WAIT_S", 0.5)
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p2_gate = threading.Event()
        await fx.refused(client, refs[6])
        assert fx.service.stats() == (1, 1, 1)
        fx.p2_gate.set()
        await until(lambda: fx.service.stats() == (0, 0, 0))

    fx.run(scenario)


def test_phase_two_busy_is_429_with_no_queue_and_no_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    release = threading.Event()
    blockers: list[Any] = []

    def tweak(app: web.Application) -> None:
        app._state[FETCH.MEDIA_SERVICE_KEY] = FETCH.MediaFetchService(_worker_cap=2)

    real_start = FETCH._Lease.start
    calls: list[int] = []

    def start(lease: Any, call: Any, payload_type: Any) -> Any:
        calls.append(1)
        if len(calls) == 2:  # this request's phase-two submission: other leases hold every permit
            service = lease._service
            for i in range(2):
                other = service.lease(f"other-{i}")
                assert other is not None
                status, future = real_start(other, lambda: release.wait(15) and False, None)
                assert status == FETCH.STARTED
                blockers.append((other, future))
        return real_start(lease, call, payload_type)

    monkeypatch.setattr(FETCH._Lease, "start", start)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        status, _h, body = await fx.get(client, refs[6])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)  # not 404, not a wait
        assert "why" not in json.loads(body)["error"]
        assert fx.p2_in == 0  # the busy phase two was never submitted, queued or retried
        assert len(calls) == 2
        release.set()
        for other, future in blockers:
            future.result(5)
            other.finish()
        await until(lambda: fx.service.stats() == (0, 0, 0))

    try:
        fx.run(scenario, tweak=tweak)
    finally:
        release.set()


def test_phase_one_busy_is_429_and_nothing_is_submitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    def tweak(app: web.Application) -> None:
        service = FETCH.MediaFetchService(_worker_cap=1)
        app._state[FETCH.MEDIA_SERVICE_KEY] = service
        lease = service.lease("holder")
        assert lease is not None
        assert lease.start(lambda: threading.Event().wait(0.5) and False, None)[0] == FETCH.STARTED

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        status, _h, body = await fx.get(client, refs[6])
        assert (status, json.loads(body)) == (429, RATE_LIMITED)
        assert fx.p1_in == 0

    fx.run(scenario, tweak=tweak)


@pytest.mark.parametrize("which", ["phase_one", "phase_two"])
def test_a_submission_failure_unwinds_every_permit_exactly(
    which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        service = fx.service
        real_submit = service._executor.submit
        count = [0]

        def submit(*args: Any, **kw: Any) -> Any:
            count[0] += 1
            if count[0] == (1 if which == "phase_one" else 2):
                raise RuntimeError("cannot schedule new futures")
            return real_submit(*args, **kw)

        service._executor.submit = submit  # type: ignore[method-assign]
        status, _h, body = await fx.get(client, refs[6])
        assert (status, json.loads(body)) == (404, NOT_FOUND)
        assert not png_signature(body)
        assert fx.starts[-1][1:] == (FETCH.SUBMISSION_FAILED, None)
        await until(lambda: service.stats() == (0, 0, 0))  # buffer, device and worker unwound
        service._executor.submit = real_submit  # type: ignore[method-assign]
        assert await fx.served(client, refs[6]) == VALID_PNG  # and the route still works

    fx.run(scenario)


def test_cleanup_closes_admissions_without_cancelling_the_pending_actual_future(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    seen: dict[str, Any] = {}

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.p1_gate = threading.Event()
        inflight = asyncio.create_task(fx.get(client, refs[6]))
        await until(lambda: fx.p1_in == 1)
        service = fx.service
        seen["service"], seen["future"] = service, fx.starts[0][2]
        await FETCH.close_service(fx.app)  # type: ignore[arg-type]
        assert service.closed and service._executor._shutdown
        assert service.lease("anyone") is None  # admissions are closed
        assert not seen["future"].cancelled() and not seen["future"].done()  # still running
        fx.p1_gate.set()
        await asyncio.gather(inflight, return_exceptions=True)
        await until(lambda: service.stats() == (0, 0, 0))
        assert seen["future"].result(5) is not None  # it finished, never cancelled

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# Streaming: deadlines, abort, no second body (T11)
# ---------------------------------------------------------------------------------------------


def _raw_get(fx: Fx, ref: str, dev: hmp_kit.Device) -> bytes:
    return (
        f"GET /hmp/v1/bots/{PROFILE}/media/{ref} HTTP/1.1\r\nHost: x\r\n"
        f"Authorization: Bearer {dev.access}\r\nHMP-Instance: {fx.rig.env.iid}\r\n\r\n"
    ).encode()


def test_a_slow_reader_is_aborted_at_the_write_deadline_and_the_handler_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WRITE_DEADLINE_S", 0.6)
    fx = Fx(tmp_path, monkeypatch)
    big = big_png(7 * 1024 * 1024)
    fx.write(6, big)
    caplog.set_level(logging.INFO)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert fx.server is not None
        loop = asyncio.get_running_loop()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
        sock.setblocking(False)
        await loop.sock_connect(sock, (fx.server.host, fx.server.port))
        await loop.sock_sendall(sock, _raw_get(fx, refs[6], dev))
        head = await loop.sock_recv(sock, 512)
        assert head.startswith(b"HTTP/1.1 200")
        await asyncio.sleep(1.6)  # the reader stalls past the 0.6 s deadline
        await until(lambda: fx.service.stats() == (0, 0, 0))  # the handler returned: leases freed
        received = len(head)
        try:
            while True:
                chunk = await asyncio.wait_for(loop.sock_recv(sock, 1 << 16), 5)
                if not chunk:
                    break
                received += len(chunk)
        except ConnectionError:
            pass
        sock.close()
        assert received < len(big)  # the transport was aborted: no complete body
        assert any("outcome=stream_aborted" in r.getMessage() for r in caplog.records)

    fx.run(scenario)


def test_an_eof_stall_is_aborted_at_the_deadline_and_no_json_is_appended(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WRITE_DEADLINE_S", 0.5)
    caplog.set_level(logging.INFO)
    fx = Fx(tmp_path, monkeypatch)

    real_eof = web.StreamResponse.write_eof
    calls: list[int] = []

    async def stall(self: Any, *args: Any, **kw: Any) -> None:
        if type(self) is web.StreamResponse:  # the media response only (JSON replies are Response)
            calls.append(1)
        if type(self) is web.StreamResponse and len(calls) == 1:
            # the handler's own EOF stalls; aiohttp's later, post-abort EOF is the real one
            await asyncio.sleep(3600)
        await real_eof(self, *args, **kw)

    monkeypatch.setattr(web.StreamResponse, "write_eof", stall)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        started = time.monotonic()
        resp = await client.get(
            hmp_kit.url(f"/bots/{PROFILE}/media/{refs[6]}"),
            headers=fx.rig.env.headers(fx.rig.device),  # type: ignore[arg-type]
        )
        try:
            body = await resp.read()
        except Exception:  # the aborted transport may surface as a client error: also acceptable
            body = b""
        assert time.monotonic() - started < 10  # bounded by the deadline, never the 3600 s stall
        assert b'"error"' not in body  # no second JSON body after the 200 was prepared
        await until(lambda: fx.service.stats() == (0, 0, 0))
        assert any("outcome=stream_aborted" in r.getMessage() for r in caplog.records)

    fx.run(scenario)


def test_a_disconnect_during_streaming_releases_every_permit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WRITE_DEADLINE_S", 5)
    fx = Fx(tmp_path, monkeypatch)
    fx.write(6, big_png(7 * 1024 * 1024))

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert fx.server is not None
        loop = asyncio.get_running_loop()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
        sock.setblocking(False)
        await loop.sock_connect(sock, (fx.server.host, fx.server.port))
        await loop.sock_sendall(sock, _raw_get(fx, refs[6], dev))
        await loop.sock_recv(sock, 512)
        sock.close()  # the phone goes away mid-body
        await until(lambda: fx.service.stats() == (0, 0, 0), within=10)

    fx.run(scenario)


def test_the_response_is_a_stream_response_sent_in_64_kib_slices_not_a_buffered_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    big = big_png(300 * 1024)
    fx.write(6, big)
    writes: list[int] = []
    real_write = web.StreamResponse.write
    kinds: list[type] = []

    async def spy(self: Any, data: Any) -> None:
        kinds.append(type(self))
        writes.append(len(data))
        await real_write(self, data)

    monkeypatch.setattr(web.StreamResponse, "write", spy)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        writes.clear()
        kinds.clear()
        assert await fx.served(client, refs[6]) == big
        assert set(kinds) == {web.StreamResponse}
        assert max(writes) == 65536 and sum(writes) == len(big) and len(writes) >= 5

    fx.run(scenario)


# ---------------------------------------------------------------------------------------------
# Logging and access log: closed enums only (T15)
# ---------------------------------------------------------------------------------------------


def test_logs_and_the_access_log_carry_closed_enums_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        await fx.served(client, refs[6])
        _content_changed(fx)
        await fx.refused(client, refs[6])
        fx.write(4, VALID_PNG_B)
        await fx.served(client, refs[4])  # first serve of a different file is recorded
        fx.write(4, VALID_PNG)
        await fx.refused(client, refs[4])
        fx.after_p1.append(lambda: (_ for _ in ()).throw(RuntimeError("SENTINEL-PRIVATE-9f3a")))
        await fx.refused(client, refs[2])
        fx.refs = refs  # type: ignore[attr-defined]

    fx.run(scenario)
    text = "\n".join(r.getMessage() for r in caplog.records)
    refs = fx.refs  # type: ignore[attr-defined]
    for forbidden in (
        *refs.values(),
        str(fx.native.home_path),
        "cache/images",
        "img5.png",
        "SENTINEL",
        hashlib.sha256(VALID_PNG).hexdigest()[:12],
        hashlib.sha256(VALID_PNG_B).hexdigest()[:12],
        fx.native.digests[6].hex()[:12],
        "89504e47",
    ):
        assert forbidden not in text, forbidden
    access = [r.getMessage() for r in caplog.records if r.name == server.ACCESS_LOGGER_NAME]
    media = [line for line in access if "/media/" in line]
    assert media and all("GET /hmp/v1/bots/{p}/media/{ref} " in line for line in media)
    assert not any(re.search(r"[A-Za-z0-9_-]{43}", line) for line in access)
    events = [r.getMessage() for r in caplog.records if "event=media_fetch" in r.getMessage()]
    assert events and all(
        re.fullmatch(
            r"event=media_fetch outcome=(phase_one_refused|phase_two_refused|stream_aborted)", e
        )
        for e in events
    )


# ---------------------------------------------------------------------------------------------
# Listener binding: raster, payload and orchestrator bound at open, per listener (A9/A10)
# ---------------------------------------------------------------------------------------------


def test_the_listener_binds_raster_payload_and_orchestrator_beside_the_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    ctx = fx.ctx
    snap = ctx.media_snapshot()
    assert snap is not None
    assert snap.raster_module is ctx.media_raster_module
    payload_name = FETCH.__name__.rsplit(".", 1)[0] + ".media_payload"
    assert snap.payload_module is ctx.media_payload_module is sys.modules[payload_name]
    assert snap.fetch_module is ctx.media_fetch_module is FETCH
    entry = vars(snap.raster_module)["check_raster_structure"]
    assert entry.__globals__ is vars(snap.raster_module)
    assert snap.same_as(ctx.media_snapshot())  # type: ignore[arg-type]
    for slot in ("media_raster_module", "media_payload_module", "media_fetch_module"):
        saved = getattr(ctx, slot)
        setattr(ctx, slot, object())
        assert ctx.media_snapshot() is None and ctx.is_media_available() is False, slot
        assert getattr(ctx, slot) is None  # a closed listener hands out nothing
        for other in ("media_raster_module", "media_payload_module", "media_fetch_module"):
            assert getattr(ctx, other) is None
        assert ctx.media_registry is None and ctx.media_modules is None
        del saved
        break


def test_each_new_fence_conjunct_closes_only_this_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index, slot in enumerate(
        ("media_raster_module", "media_payload_module", "media_fetch_module")
    ):
        sub = tmp_path / str(index)
        sub.mkdir()
        world = PackageWorld(sub, monkeypatch, label=f"w{index}")
        _, ctx = world.open()
        assert ctx.media_snapshot() is not None
        other_dir = tmp_path / f"o{index}"
        other_dir.mkdir()
        sibling = PackageWorld(other_dir, monkeypatch, label=f"s{index}")
        _, sctx = sibling.open()
        setattr(ctx, slot, object())
        assert ctx.is_media_available() is False and ctx.media_snapshot() is None
        assert sctx.is_media_available() is True and sctx.media_snapshot() is not None


def test_a_closed_listener_binds_none_of_the_s5_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = PackageWorld(tmp_path, monkeypatch, label="c", features=("read",))
    _, ctx = world.open()
    assert ctx.media_raster_module is None and ctx.media_payload_module is None
    assert ctx.media_fetch_module is None and ctx.media_snapshot() is None
    assert f"{world.pkg}.local_media_raster_structure" not in sys.modules


_SPLIT_RASTER = "\n_check_png = type(_check_png)(_check_png.__code__, dict(globals()))\n"


@pytest.mark.parametrize(
    ("label", "edits"),
    [
        (
            "raster_helper_foreign_namespace",
            {
                "local_media_raster_structure.py": [
                    ("\n# --- entry point", _SPLIT_RASTER + "\n# --- entry point")
                ]
            },
        ),
        (
            "raster_entry_foreign_namespace",
            {
                "local_media_raster_structure.py": [
                    (
                        "def check_raster_structure(data: bytes) -> Structure:",
                        "def _real_check(data: bytes) -> Structure:",
                    ),
                    (
                        "    raise _refuse(Reason.UNSUPPORTED_FORMAT, \"input.signature\")\n",
                        "    raise _refuse(Reason.UNSUPPORTED_FORMAT, \"input.signature\")\n\n\n"
                        "check_raster_structure = type(_real_check)(\n"
                        "    _real_check.__code__, dict(globals())\n)\n",
                    ),
                ]
            },
        ),
    ],
)
def test_a_split_raster_namespace_closes_this_listener_and_a_coherent_one_opens(
    label: str,
    edits: dict[str, list[tuple[str, str]]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_dir, good_dir = tmp_path / "b", tmp_path / "g"
    broken_dir.mkdir()
    good_dir.mkdir()
    broken = PackageWorld(broken_dir, monkeypatch, label=label, edits=edits)
    _, bctx = broken.open()
    assert bctx.is_media_available() is False and bctx.media_snapshot() is None
    assert bctx.media_raster_module is None and bctx.media_registry is None
    good = PackageWorld(good_dir, monkeypatch, label="ok")
    _, gctx = good.open()
    assert gctx.is_media_available() is True  # no process latch


_SECOND_CARRIER = (
    "import types as _t\n"
    "media_payload = _t.ModuleType('media_payload_second_copy')\n"
    "exec(compile(open(__file__.replace('media_fetch.py', 'media_payload.py')).read(),"
    " 'x', 'exec'),"
    " media_payload.__dict__)\n"
)


def test_a_split_payload_carrier_between_the_bridge_and_the_route_closes_the_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route's `media_payload` is a second, separately executed copy of the carrier module: the
    bridge would build one class and the route check for another. The binder refuses it."""
    split_dir, good_dir = tmp_path / "split", tmp_path / "ok"
    split_dir.mkdir()
    good_dir.mkdir()
    edits = {"media_fetch.py": [("from . import media_payload\n", _SECOND_CARRIER)]}
    _, ctx = PackageWorld(split_dir, monkeypatch, label="sp", edits=edits).open()
    assert ctx.is_media_available() is False and ctx.media_snapshot() is None
    assert ctx.media_payload_module is None and ctx.media_registry is None
    _, good = PackageWorld(good_dir, monkeypatch, label="ok").open()
    assert good.is_media_available() is True


def test_whole_package_eviction_after_open_leaves_the_old_listener_fully_working(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[6]) == VALID_PNG
        for name in [k for k in sys.modules if k == "hmp_plugin" or k.startswith("hmp_plugin.")]:
            monkeypatch.delitem(sys.modules, name)  # what the Hermes loader's eviction does
        assert not [k for k in sys.modules if k.startswith("hmp_plugin")]
        snap = fx.ctx.media_snapshot()
        assert snap is not None and snap.fetch_module is FETCH
        # mint AND fetch still use the very objects bound at open: no request-time import
        refs = await fx.mint(client)
        assert await fx.served(client, refs[4]) == VALID_PNG
        assert await fx.served(client, refs[6]) == VALID_PNG

    fx.run(scenario)


def test_a_second_listener_in_the_process_has_its_own_service_and_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    second = hmp_kit.Env(tmp_path / "second").ctx
    second.bridge, second.reads = fx.native.bridge, fx.rig.reads
    second.media_available = fx.rig.adapter._media_bind(
        second, fx.rig.bridge_module, fx.rig.reads_module
    )
    assert second.media_registry is not fx.ctx.media_registry
    assert second.media_raster_module is fx.ctx.media_raster_module  # one process-wide module
    app_a, app_b = fx.rig.env.app(), server.build_app(second)
    assert app_a[FETCH.MEDIA_SERVICE_KEY] is not app_b[FETCH.MEDIA_SERVICE_KEY]


def test_phase_methods_refuse_an_unbound_or_foreign_chain_before_any_native_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    bridge = fx.native.bridge
    real1 = type(bridge).media_fetch_phase_one
    real2 = type(bridge).media_fetch_phase_two
    snap = fx.ctx.media_snapshot()
    assert snap is not None
    rm, rs = snap.registry_module, snap.raster_module
    registry = snap.registry
    binding = real_registry.Binding(
        device_id="d1",
        user_id=USER,
        instance_id=fx.rig.env.iid,
        profile=PROFILE,
        kind=real_registry.SessionKind.PHONE,
        session_id=fx.rig.session,
        tip=fx.rig.tip,
        tool_row_id=6,
        raw_digest=fx.native.digests[6],
    )
    del registry
    fx.native.world.runner.calls.clear()
    fx.native.db.calls.clear()
    wrong_chain = (*snap.chain,)  # an equal but NOT identical tuple: not the bridge's cache
    assert wrong_chain == snap.chain and wrong_chain is not snap.chain
    foreign_binding = type("Binding", (), {})()
    for args in (
        (binding, wrong_chain, rm, rs),
        (foreign_binding, snap.chain, rm, rs),
        (binding, snap.chain, sys.modules[__name__], rs),
        (binding, snap.chain, rm, sys.modules[__name__]),
        (binding, snap.chain, rm, None),
        (binding, list(snap.chain), rm, rs),
    ):
        assert real1(bridge, *args) is None
    for args in (
        (binding, wrong_chain, rm),
        (foreign_binding, snap.chain, rm),
        (binding, snap.chain, sys.modules[__name__]),
    ):
        assert real2(bridge, *args) is False
    assert not fx.native.world.runner.calls and not fx.native.db.calls  # no native call at all
    # The control: the very same binding, chain and registry module are accepted by phase two when
    # the native facts still hold, so every refusal above came from the bound-input check alone;
    # and one flipped native fact (the grant) is then a plain False, never an exception.
    assert real2(bridge, binding, snap.chain, rm) is True
    _grant_revoked(fx)
    assert real2(bridge, binding, snap.chain, rm) is False


def test_phase_one_refuses_a_raster_module_whose_function_runs_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    snap = fx.ctx.media_snapshot()
    assert snap is not None
    import types

    foreign = types.ModuleType("foreign_raster")
    foreign.check_raster_structure = lambda data: (_ for _ in ()).throw(AssertionError("ran"))  # type: ignore[attr-defined]
    binding = real_registry.Binding(
        device_id="d1",
        user_id=USER,
        instance_id=fx.rig.env.iid,
        profile=PROFILE,
        kind=real_registry.SessionKind.PHONE,
        session_id=fx.rig.session,
        tip=fx.rig.tip,
        tool_row_id=6,
        raw_digest=fx.native.digests[6],
    )
    fx.native.world.runner.calls.clear()
    assert type(fx.native.bridge).media_fetch_phase_one(
        fx.native.bridge, binding, snap.chain, snap.registry_module, foreign
    ) is None
    assert not fx.native.world.runner.calls


# ---------------------------------------------------------------------------------------------
# Recovery regressions (provisional root findings): the buffer through retained exception
# tracebacks, ERR-1 before prepare and abort after it, the deadline's start, every raster helper
# ---------------------------------------------------------------------------------------------

MIB = 1024 * 1024


def _walk_traceback(exc: BaseException, skip: Any) -> tuple[list[str], list[str]]:
    """`(frame names on the exception chain, "frame.local" names still holding the payload)`.

    This reads the ACTUAL retained exception: every frame its traceback keeps alive, and every
    local of those frames. A `MediaPayload`, or a `bytes` larger than one stream slice, is the
    8 MiB buffer (or its carrier). `skip` is the capture wrapper's own code object."""
    names: list[str] = []
    held: list[str] = []
    seen: set[int] = set()
    todo: list[BaseException | None] = [exc]
    while todo:
        current = todo.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        todo += [current.__cause__, current.__context__]
        tb = current.__traceback__
        while tb is not None:
            frame = tb.tb_frame
            if frame.f_code is not skip:
                names.append(frame.f_code.co_name)
                for local, value in frame.f_locals.items():
                    big = type(value) is bytes and len(value) > FETCH.STREAM_SLICE_BYTES
                    if type(value).__name__ == "MediaPayload" or big:
                        held.append(f"{frame.f_code.co_name}.{local}")
            tb = tb.tb_next
    return names, held


def _capture_escaping(monkeypatch: pytest.MonkeyPatch) -> tuple[list[BaseException], Any]:
    """Wrap `serve` (after the listener bound the real one) to keep every exception that escapes
    it, traceback included, exactly as a framework log or a debugger would keep it."""
    real = FETCH.serve
    caught: list[BaseException] = []

    async def serve(request: web.Request) -> Any:
        try:
            return await real(request)
        except BaseException as exc:
            caught.append(exc)
            raise

    monkeypatch.setattr(FETCH, "serve", serve)
    return caught, serve.__code__


def test_a_final_section_refusal_leaves_no_payload_on_the_retained_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    caught, skip = _capture_escaping(monkeypatch)
    fx.write(6, big_png(7 * MIB))
    tracemalloc.start()

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        fx.after_p2.append(lambda: _flag_off(fx))  # refused inside `_final_section`
        gc.collect()
        tracemalloc.reset_peak()
        base = tracemalloc.get_traced_memory()[0]
        await fx.refused(client, refs[6])
        await until(lambda: fx.service.stats() == (0, 0, 0))  # every permit is back
        gc.collect()
        settled, peak = tracemalloc.get_traced_memory()
        assert peak - base >= 7 * MIB  # the window really held the buffer ...
        names, held = _walk_traceback(caught[0], skip)
        assert "_final_section" in names  # ... and this is the raising frame
        assert held == [], held  # no frame of the retained exception keeps the payload
        assert settled - base < MIB  # ... so the memory is gone while the exception is kept

    try:
        fx.run(scenario)
    finally:
        tracemalloc.stop()


def test_a_cancelled_stream_leaves_no_payload_on_the_retained_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FETCH, "MEDIA_WRITE_DEADLINE_S", 30)
    fx = Fx(tmp_path, monkeypatch)
    caught, skip = _capture_escaping(monkeypatch)
    fx.write(6, big_png(7 * MIB))
    tracemalloc.start()

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert fx.server is not None
        gc.collect()
        tracemalloc.reset_peak()
        base = tracemalloc.get_traced_memory()[0]
        loop = asyncio.get_running_loop()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
        sock.setblocking(False)
        await loop.sock_connect(sock, (fx.server.host, fx.server.port))
        await loop.sock_sendall(sock, _raw_get(fx, refs[6], dev))
        assert (await loop.sock_recv(sock, 512)).startswith(b"HTTP/1.1 200")
        await asyncio.sleep(0.3)  # the stalled reader parks the handler inside `response.write`
        assert fx.service.stats() == (1, 0, 1)  # the lease is held while it streams
        fx.tasks[-1].cancel()
        await until(lambda: fx.service.stats() == (0, 0, 0))
        sock.close()
        gc.collect()
        settled, peak = tracemalloc.get_traced_memory()
        assert peak - base >= 7 * MIB
        assert any(type(e) is asyncio.CancelledError for e in caught)
        names, held = _walk_traceback(caught[0], skip)
        assert "_stream" in names
        assert held == [], held
        assert settled - base < MIB

    try:
        fx.run(scenario)
    finally:
        tracemalloc.stop()


def test_an_unexpected_failure_before_prepare_is_the_standard_err1_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    fx = Fx(tmp_path, monkeypatch)
    real_prepare = web.StreamResponse.prepare
    armed: list[bool] = []

    async def prepare(self: Any, request: Any) -> Any:
        if armed and type(self) is web.StreamResponse:
            raise RuntimeError("SENTINEL-PRIVATE-9f3a /tmp/secret")
        return await real_prepare(self, request)

    monkeypatch.setattr(web.StreamResponse, "prepare", prepare)

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert await fx.served(client, refs[6]) == VALID_PNG  # the same hook, unarmed
        armed.append(True)
        status, headers, body = await fx.get(client, refs[6])
        error = json.loads(body)["error"]
        assert status == 500 and error["code"] == "other" and error["why"] == "internal_error"
        assert headers["Content-Type"].startswith("application/json")
        assert b"SENTINEL" not in body and "Content-Length" in headers
        armed.clear()
        await until(lambda: fx.service.stats() == (0, 0, 0))
        assert await fx.served(client, refs[4]) == VALID_PNG

    fx.run(scenario)
    assert "SENTINEL" not in "\n".join(r.getMessage() for r in caplog.records)
    assert not any("outcome=stream_aborted" in r.getMessage() for r in caplog.records)


def test_an_unexpected_failure_after_prepare_aborts_and_appends_no_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    fx = Fx(tmp_path, monkeypatch)
    big = big_png(300 * 1024)
    fx.write(6, big)
    real_write = web.StreamResponse.write
    calls: list[int] = []

    async def write(self: Any, data: Any) -> None:
        if type(self) is web.StreamResponse:
            calls.append(1)
            if len(calls) == 3:  # two slices went out, then the third fails
                raise RuntimeError("SENTINEL-PRIVATE-9f3a")
        await real_write(self, data)

    monkeypatch.setattr(web.StreamResponse, "write", write)

    async def scenario(client: TestClient) -> None:
        dev = await fx.rig.pair(client)
        refs = await fx.mint(client)
        assert fx.server is not None
        loop = asyncio.get_running_loop()
        sock = socket.socket()
        sock.setblocking(False)
        await loop.sock_connect(sock, (fx.server.host, fx.server.port))
        await loop.sock_sendall(sock, _raw_get(fx, refs[6], dev))
        received = b""
        try:
            while True:
                chunk = await asyncio.wait_for(loop.sock_recv(sock, 1 << 16), 5)
                if not chunk:
                    break
                received += chunk
        except ConnectionError:
            pass
        sock.close()
        assert received.startswith(b"HTTP/1.1 200")  # the 200 was already prepared
        assert b'"error"' not in received and b"SENTINEL" not in received  # no second body
        assert len(received) < len(big)  # the transport was aborted before the body completed
        await until(lambda: fx.service.stats() == (0, 0, 0))

    fx.run(scenario)
    assert any("outcome=stream_aborted" in r.getMessage() for r in caplog.records)
    assert "SENTINEL" not in "\n".join(r.getMessage() for r in caplog.records)


def test_the_shared_deadline_starts_at_the_phase_one_submission_not_after_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow submission (the executor creating its first thread) spends part of the one 20 s
    budget (here 1.0 s): 0.6 s there plus 0.3 s per phase cannot fit, 0.0 s can."""
    monkeypatch.setattr(FETCH, "MEDIA_WORKER_WAIT_S", 1.0)
    results: dict[str, int] = {}
    for label, delay in (("fast_submit", 0.0), ("slow_submit", 0.6)):
        sub = tmp_path / label
        sub.mkdir()
        fx = Fx(sub, monkeypatch)
        fx.p1_sleep = fx.p2_sleep = 0.3

        async def scenario(
            client: TestClient, fx: Fx = fx, label: str = label, delay: float = delay
        ) -> None:
            await fx.rig.pair(client)
            refs = await fx.mint(client)
            real_submit, count = fx.service._executor.submit, [0]

            def submit(*args: Any, **kw: Any) -> Any:
                count[0] += 1
                if count[0] == 1:
                    time.sleep(delay)  # before any future exists, inside the submission
                return real_submit(*args, **kw)

            fx.service._executor.submit = submit  # type: ignore[method-assign]
            results[label] = (await fx.get(client, refs[6]))[0]
            await until(lambda: fx.service.stats() == (0, 0, 0))

        fx.run(scenario)
    assert results == {"fast_submit": 200, "slow_submit": 404}


RASTER_HELPERS = (
    "_bad",
    "_check_dims",
    "_check_png_ancillary",
    "_jpeg_sof",
    "_jpeg_dqt",
    "_jpeg_dht",
    "_jpeg_scan",
    "_webp_vp8",
    "_webp_vp8l",
    "_webp_alph",
    "_webp_vp8x",
    "_webp_extended_chunk",
)


def _split(name: str) -> str:
    return f"\n{name} = type({name})({name}.__code__, dict(globals()))\n"


RASTER_SPLITS = {
    **{helper: _split(helper) for helper in RASTER_HELPERS},
    "refusal_init": (
        "\n_f = RasterRefused.__init__\n"  # keep the `super()` closure so the copy still loads
        "RasterRefused.__init__ = type(_f)(\n"
        "    _f.__code__, dict(globals()), _f.__name__, None, _f.__closure__\n)\n"
    ),
    "unlisted_future_helper": "\n_later_helper = type(_bad)(_bad.__code__, dict(globals()))\n",
}


@pytest.mark.parametrize("which", sorted(RASTER_SPLITS))
def test_a_split_namespace_in_any_reachable_raster_function_closes_this_listener(
    which: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every function the entry point can reach must run in the one bound raster module, not only
    the entry and its three format dispatchers. Each case splits exactly one other function."""
    edits = {
        "local_media_raster_structure.py": [
            ("\n# --- entry point", RASTER_SPLITS[which] + "\n# --- entry point")
        ]
    }
    _, ctx = PackageWorld(tmp_path, monkeypatch, label=f"r_{which}", edits=edits).open()
    assert ctx.is_media_available() is False and ctx.media_snapshot() is None, which
    assert ctx.media_raster_module is None and ctx.media_registry is None


def test_every_raster_function_the_binder_proves_is_a_real_module_function() -> None:
    """The proof list is not stale: each name still exists in the accepted raster module and the
    sweep finds no module function beyond the ones named, so a split is not hiding in a gap."""
    from hmp_plugin import local_media_raster_structure as raster

    function_type = type(_split)
    functions = {
        name
        for name, value in vars(raster).items()
        if type(value) is function_type and value.__module__ == raster.__name__
    }
    assert set(RASTER_HELPERS) | {
        "check_raster_structure",
        "_refuse",
        "_check_png",
        "_check_jpeg",
        "_check_webp",
    } == functions


# ---------------------------------------------------------------------------------------------
# Pins on the new interfaces and the protected files (S4 regression lives in test_s4_descriptors)
# ---------------------------------------------------------------------------------------------


def test_the_new_bridge_methods_import_nothing_log_nothing_and_never_raise_out() -> None:
    import ast

    tree = ast.parse((PACKAGE / "bridge.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "HermesReadBridge")
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    for name in ("_media_fetch_bound", "media_fetch_phase_one", "media_fetch_phase_two"):
        for node in ast.walk(methods[name]):
            assert not isinstance(node, ast.Import | ast.ImportFrom), name
            if isinstance(node, ast.Call):
                label = getattr(node.func, "id", getattr(node.func, "attr", ""))
                assert label not in {"log_event", "log_bridge_exception", "import_module", "open"}
    for name in ("media_fetch_phase_one", "media_fetch_phase_two"):
        tries = [n for n in methods[name].body if isinstance(n, ast.Try)]
        assert len(tries) == 1 and [h.type.id for h in tries[0].handlers] == ["Exception"]  # type: ignore[union-attr]


def test_media_fetch_and_payload_import_no_local_media_module_and_payload_is_stdlib() -> None:
    import ast

    for name in ("media_fetch.py", "media_payload.py"):
        tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                assert "local_media" not in ast.unparse(node), name
    payload = ast.parse((PACKAGE / "media_payload.py").read_text(encoding="utf-8"))
    for node in ast.walk(payload):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0  # no relative (package) import at all


def test_the_orchestrator_has_no_module_level_service_executor_or_per_request_import() -> None:
    import ast

    tree = ast.parse((PACKAGE / "media_fetch.py").read_text(encoding="utf-8"))
    for node in tree.body:  # module level: no instance of the service or an executor
        if isinstance(node, ast.Assign | ast.AnnAssign):
            value = node.value
            assert not (isinstance(value, ast.Call) and getattr(value.func, "id", "") in {
                "MediaFetchService",
                "ThreadPoolExecutor",
            })
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
            for node in ast.walk(fn):
                assert not isinstance(node, ast.Import | ast.ImportFrom), fn.name
                if isinstance(node, ast.Name):
                    assert node.id not in {"importlib", "__import__", "sys", "os", "open", "Path"}


def test_the_final_section_is_synchronous_and_every_await_is_enumerated() -> None:
    import ast

    tree = ast.parse((PACKAGE / "media_fetch.py").read_text(encoding="utf-8"))
    final = next(n for n in tree.body if getattr(n, "name", "") == "_final_section")
    assert isinstance(final, ast.FunctionDef)  # a plain function: it cannot await
    assert not [n for n in ast.walk(final) if isinstance(n, ast.Await)]
    serve = next(n for n in tree.body if getattr(n, "name", "") == "serve")
    awaits = [
        ast.unparse(n.value).split("(")[0] for n in ast.walk(serve) if isinstance(n, ast.Await)
    ]
    assert sorted(awaits) == sorted(["asyncio.to_thread", "_wait", "_wait", "_stream"])
    stream = next(n for n in tree.body if getattr(n, "name", "") == "_stream")
    inner = [
        ast.unparse(n.value).split("(")[0] for n in ast.walk(stream) if isinstance(n, ast.Await)
    ]
    assert sorted(inner) == sorted(["response.prepare", "response.write", "response.write_eof"])


def test_the_route_is_always_registered_for_get_only() -> None:
    assert server.S5_MEDIA_ROUTES == (("GET", "/bots/{p}/media/{ref}", "LM-10"),)


def test_the_media_registry_ref_grammar_matches_the_descriptor_grammar() -> None:
    assert REF_RE.match("A" * 43) and not REF_RE.match("A" * 42)


def _observe_first_fixture_gate_release(fx: Fx) -> list[tuple[bool, bool]]:
    """Observe the causal first release; a final is_set value alone cannot prove order."""
    releases: list[tuple[bool, bool]] = []

    class ObservedGate(threading.Event):
        def set(self) -> None:
            if not releases:
                owners_closed = bool(fx.owned_media_services) and all(
                    service.closed for service in fx.owned_media_services
                )
                both_unset = all(
                    gate is not None and not gate.is_set() for gate in (fx.p1_gate, fx.p2_gate)
                )
                releases.append((owners_closed, both_unset))
                assert owners_closed and both_unset
            super().set()

    fx.p1_gate, fx.p2_gate = ObservedGate(), ObservedGate()
    return releases


# The fixture owns the original pool even when an authority probe replaces the app slot.
def test_fixture_joins_original_media_pool_after_service_slot_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    seen: dict[str, Any] = {}

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        seen["original"] = fx.service
        fx.after_p2.append(lambda: _service_replaced(fx))
        status, _headers, body = await fx.get(client, refs[6])
        assert status == 404 and json.loads(body) == NOT_FOUND
        assert fx.p2_in == 1 and not png_signature(body)
        seen["replacement"] = fx.service
        assert seen["original"] is not seen["replacement"]
        assert not seen["original"].closed  # Slot replacement is not an owner close.
        seen["workers"] = tuple(seen["original"]._executor._threads)
        assert seen["workers"] and all(worker.is_alive() for worker in seen["workers"])
        seen["releases"] = _observe_first_fixture_gate_release(fx)

    fx.run(scenario)
    assert seen["releases"] == [(True, True)]
    assert seen["original"] in fx.owned_media_services
    assert seen["original"].closed and seen["replacement"].closed
    assert all(not worker.is_alive() for worker in seen["workers"])


def test_fixture_releases_and_joins_held_media_worker_when_scenario_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = Fx(tmp_path, monkeypatch)
    seen: dict[str, Any] = {}

    async def scenario(client: TestClient) -> None:
        await fx.rig.pair(client)
        refs = await fx.mint(client)
        seen["releases"] = _observe_first_fixture_gate_release(fx)
        request = asyncio.create_task(fx.get(client, refs[6]))
        await until(lambda: fx.p1_in == 1)
        seen["service"] = fx.service
        seen["future"] = fx.starts[0][2]
        seen["workers"] = tuple(fx.service._executor._threads)
        assert not seen["future"].done() and not seen["future"].cancelled()
        assert seen["workers"] and not request.done()
        raise RuntimeError("owned fixture scenario failed")

    with pytest.raises(RuntimeError, match=r"^owned fixture scenario failed$"):
        fx.run(scenario)
    assert seen["releases"] == [(True, True)]
    assert fx.p1_gate is not None and fx.p1_gate.is_set()
    assert seen["service"].closed
    assert seen["future"].done() and not seen["future"].cancelled()
    assert all(not worker.is_alive() for worker in seen["workers"])
