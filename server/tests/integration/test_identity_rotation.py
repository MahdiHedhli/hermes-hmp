"""T022 integration: after `rotate-key`, a pre-rotation client sees a pin mismatch or a connection
failure, never a `200` (PR7-6, TR-3).

A real TLS 1.3 listener (aiohttp) serves with `identity.server_ssl_context()` on loopback. It
follows the PR7-6 sequence using only the identity API: every request checks `still_current()`, and
a watchdog checks it every `WATCH_S`; once it turns False the listener closes, then (variant B)
restarts under the reloaded key. The rotation runs through a separate `rotate_key` call, as the
operator CLI would. The client is a minimal Python reference client that checks the peer SPKI
against its pinned `iid` after the handshake and before writing a byte (TR-2). The full gateway
version of this test is part of T035.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from pathlib import Path

from aiohttp import web

from hmp_plugin import crypto, identity
from hmp_plugin.identity import HostId

WATCH_S = 0.05
HOST = HostId("test-source", "synthetic-host-a")


class Store:
    def __init__(self) -> None:
        self.epoch = 0

    def revocation_epoch(self) -> int:
        return self.epoch

    def revoke_all_for_identity_change(self, now: int) -> int:
        self.epoch += 1
        return self.epoch


def _kwargs(tmp: Path) -> dict[str, object]:
    root = tmp / "hermes"
    return {
        "env": {"HERMES_HOME": str(root)},
        "hermes_root": root,
        "binding_root": tmp / "state" / "hermes-hmp",
        "host_id": lambda: HOST,
    }


def pinned_get(port: int, pin: str) -> str:
    """Return the HTTP status line's code, `pin_mismatch`, or `connection_failure`."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # trust comes from the pin alone (TR-2)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=2) as raw,
            ctx.wrap_socket(raw) as tls,
        ):
            peer = tls.getpeercert(binary_form=True)
            if peer is None or crypto.spki_fingerprint(crypto.certificate_spki(peer)) != pin:
                return "pin_mismatch"  # close without writing
            tls.sendall(b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n")
            head = tls.recv(64)
    except (OSError, ssl.SSLError):
        return "connection_failure"
    if not head.startswith(b"HTTP/1.1 "):
        return "connection_failure"
    return head.split(b" ")[1].decode("ascii")


class Listener:
    """A minimal PR7-6 listener around one loaded identity."""

    def __init__(self, ident: identity.LoadedIdentity, port: int = 0) -> None:
        self.ident = ident
        self.port = port
        self.closed = asyncio.Event()
        self._runner: web.AppRunner | None = None
        self._watch: asyncio.Task[None] | None = None
        self._stopping: asyncio.Task[None] | None = None

    async def start(self) -> None:
        @web.middleware
        async def current_key_only(request: web.Request, handler):  # type: ignore[no-untyped-def]
            if not self.ident.still_current():
                if request.transport is not None:
                    request.transport.abort()  # no status for pre-rotation clients (PR7-6 step 5)
                self._stopping = asyncio.get_running_loop().create_task(self.stop())
                return web.Response(status=503)  # never written: the transport is gone
            return await handler(request)

        async def ready(_: web.Request) -> web.Response:
            return web.json_response({"iid": self.ident.iid})

        app = web.Application(middlewares=[current_key_only])
        app.router.add_get("/hmp/v1/ready", ready)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner, "127.0.0.1", self.port, ssl_context=self.ident.server_ssl_context()
        )
        await site.start()
        server = site._server  # read the bound port (test only)
        assert server is not None
        self.port = server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        self._watch = asyncio.get_running_loop().create_task(self._watchdog())

    async def _watchdog(self) -> None:
        # The PR7-6 watchdog polls on-disk state by design; there is no event to wait on.
        while self.ident.still_current():  # noqa: ASYNC110
            await asyncio.sleep(WATCH_S)
        await self.stop()

    async def stop(self) -> None:
        if self._runner is not None:
            runner, self._runner = self._runner, None
            await runner.cleanup()
        self.closed.set()


async def _get(port: int, pin: str) -> str:
    return await asyncio.get_running_loop().run_in_executor(None, pinned_get, port, pin)


def test_rotation_listener_stays_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = Store()
        running = identity.load_or_create(store, **_kwargs(tmp_path))
        pin = running.iid
        listener = Listener(running)
        await listener.start()
        assert await _get(listener.port, pin) == "200"

        identity.rotate_key(store, **_kwargs(tmp_path))  # the operator CLI
        # Immediately, before or after the watchdog notices: never a 200.
        assert await _get(listener.port, pin) in ("connection_failure", "pin_mismatch")
        await asyncio.wait_for(listener.closed.wait(), timeout=4 * WATCH_S + 2)
        assert await _get(listener.port, pin) == "connection_failure"

    asyncio.run(scenario())


def test_rotation_listener_restarts_under_new_key(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = Store()
        running = identity.load_or_create(store, **_kwargs(tmp_path))
        old_pin = running.iid
        listener = Listener(running)
        await listener.start()
        assert await _get(listener.port, old_pin) == "200"

        identity.rotate_key(store, **_kwargs(tmp_path))
        await asyncio.wait_for(listener.closed.wait(), timeout=4 * WATCH_S + 2)

        # PR7-6 step 3: restart under the new key, on the same port.
        reloaded = identity.load_or_create(store, **_kwargs(tmp_path))
        assert reloaded.iid != old_pin
        restarted = Listener(reloaded, port=listener.port)
        await restarted.start()
        try:
            for _ in range(3):
                assert await _get(restarted.port, old_pin) == "pin_mismatch"
            assert await _get(restarted.port, reloaded.iid) == "200"  # a re-paired client
        finally:
            await restarted.stop()

    asyncio.run(scenario())
