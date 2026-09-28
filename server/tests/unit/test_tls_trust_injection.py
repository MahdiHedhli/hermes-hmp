"""TR-1 under a host's process-wide client-trust injection.

Some Hermes builds call `truststore.inject_into_ssl()` at process start. That replaces the
`ssl.SSLContext` module global for the whole process with truststore's client-trust class, which
also runs platform peer-certificate verification on the server side of every handshake (on macOS
every handshake then fails, because there is no client certificate to verify). HMP's listener
context must not be affected: it is built from the standard library's own class and keeps exactly
the TR-1 configuration (TLS 1.3 minimum and maximum, no session tickets, the instance certificate
and key, no client-certificate request, the default server options plus `OP_NO_TICKET`).

Each case runs a real TLS 1.3 handshake against a real `HmpServer` on loopback, once without and
once with the injection active in this test process, and asserts the negotiated properties. The
injection is always removed in teardown (`truststore.extract_from_ssl()`), so it never leaks into
other tests.

`truststore` is a test-only dependency (server/pyproject.toml `[dev]`); the plugin never imports it.
"""

from __future__ import annotations

import asyncio
import json
import socket
import ssl
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import truststore

from hmp_plugin import cli, crypto, server

from .hmp_kit import Env

# Captured when this module is imported, before any test here injects anything.
_STDLIB_SSL_CONTEXT = ssl.SSLContext
assert _STDLIB_SSL_CONTEXT.__module__ == "ssl", "ssl.SSLContext was already replaced at import"

# The options a default TLS server context carries, plus TR-1's OP_NO_TICKET: exactly what the
# listener set before this fix, on a process without any injection.
_EXPECTED_OPTIONS = _STDLIB_SSL_CONTEXT(ssl.PROTOCOL_TLS_SERVER).options | ssl.OP_NO_TICKET

_CERTIFICATE = 11  # TLS HandshakeType certificate (the server's own, always sent)
_CERTIFICATE_REQUEST = 13  # TLS HandshakeType certificate_request
_NEW_SESSION_TICKET = 4  # TLS HandshakeType new_session_ticket
_HANDSHAKE = 22  # TLS ContentType handshake


@dataclass
class _Client:
    """A pinning TLS client (TR-2), built from the standard library class before any injection,
    that records every handshake message it receives."""

    ctx: ssl.SSLContext
    received: list[int] = field(default_factory=list)


@pytest.fixture
def client() -> _Client:
    ctx = _STDLIB_SSL_CONTEXT(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # trust comes from the pin alone (TR-2)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2  # let the server alone choose the version
    received: list[int] = []

    def on_message(
        _conn: Any, direction: str, _version: Any, content_type: Any, msg_type: Any, _data: Any
    ) -> None:
        if direction == "read" and int(content_type) == _HANDSHAKE:
            received.append(int(msg_type))

    # A private stdlib debug hook (the one CPython's own ssl tests use). It is set here, before
    # any injection, because the stdlib setter resolves the `ssl.SSLContext` global.
    ctx._msg_callback = on_message  # type: ignore[attr-defined]
    return _Client(ctx, received)


@pytest.fixture(params=["no_injection", "truststore_injected"])
def injection(request: pytest.FixtureRequest, client: _Client) -> Iterator[str]:
    del client  # built first, so the client side never sees the injection
    assert ssl.SSLContext is _STDLIB_SSL_CONTEXT, "an earlier test leaked an ssl injection"
    try:
        if request.param == "truststore_injected":
            truststore.inject_into_ssl()
            assert ssl.SSLContext is not _STDLIB_SSL_CONTEXT
        yield request.param
    finally:
        truststore.extract_from_ssl()
        assert ssl.SSLContext is _STDLIB_SSL_CONTEXT


def _exchange(port: int, client: _Client) -> dict[str, Any]:
    with (
        socket.create_connection(("127.0.0.1", port), timeout=3) as raw,
        client.ctx.wrap_socket(raw) as tls,
    ):
        peer = tls.getpeercert(binary_form=True)
        assert peer is not None
        tls.sendall(b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n")
        chunks = []
        while data := tls.recv(65536):
            chunks.append(data)
        session = tls.session
        return {
            "version": tls.version(),
            "cipher_protocol": tls.cipher()[1] if tls.cipher() else None,
            "pin": crypto.spki_fingerprint(crypto.certificate_spki(peer)),
            "response": b"".join(chunks),
            "has_ticket": session.has_ticket if session is not None else False,
        }


def test_listener_negotiates_tr1_with_and_without_trust_injection(
    tmp_path: Path, client: _Client, injection: str
) -> None:
    env = Env(tmp_path)  # after the injection, as in a host process that injected at startup
    listener_contexts: list[ssl.SSLContext] = []
    real_server_ssl_context = server.server_ssl_context

    def capture(*args: Any, **kwargs: Any) -> ssl.SSLContext:
        ctx = real_server_ssl_context(*args, **kwargs)
        listener_contexts.append(ctx)
        return ctx

    async def main() -> dict[str, Any]:
        srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0))
        with mock.patch.object(server, "server_ssl_context", side_effect=capture):
            await srv.start()
        try:
            assert srv.bound is not None
            port = srv.bound[1]
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: _exchange(port, client)
            )
        finally:
            await srv.stop(notify=False)

    result = asyncio.run(main())

    # What the real handshake negotiated.
    assert result["version"] == "TLSv1.3"
    assert result["cipher_protocol"] == "TLSv1.3"
    assert result["pin"] == env.iid  # the instance certificate over the instance key
    assert result["response"].startswith(b"HTTP/1.1 200 ")
    body = json.loads(result["response"].split(b"\r\n\r\n", 1)[1])
    assert body["iid"] == env.iid
    assert _CERTIFICATE_REQUEST not in client.received  # no client certificate requested
    assert _NEW_SESSION_TICKET not in client.received  # no session tickets
    assert result["has_ticket"] is False
    assert _CERTIFICATE in client.received, "the hook did not see the server Certificate"

    # The context the listener actually served with: the standard library's own class (never the
    # injected one), configured exactly as TR-1 requires.
    assert len(listener_contexts) == 1
    ctx = listener_contexts[0]
    assert type(ctx) is _STDLIB_SSL_CONTEXT, f"{injection}: {type(ctx)!r}"
    assert ctx.protocol == ssl.PROTOCOL_TLS_SERVER
    assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3
    assert ctx.maximum_version == ssl.TLSVersion.TLSv1_3
    assert ctx.options == _EXPECTED_OPTIONS
    assert ctx.num_tickets == 0
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.post_handshake_auth is False
    assert ctx.sni_callback is not None  # the PR7-6 handshake guard


def test_operator_liveness_check_with_and_without_trust_injection(
    tmp_path: Path, injection: str
) -> None:
    """SR-7: `pair offer`'s pinned liveness check (`cli._default_verify_listener_live`) runs in the
    host's CLI process, where the injection is also active. Its client context must stay a plain,
    pin-only stdlib context: under injection, a platform-trust evaluation of the self-signed
    instance certificate fails, and the check would answer False for the real listener."""
    env = Env(tmp_path)

    async def main() -> tuple[bool, bool]:
        srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0))
        await srv.start()
        try:
            assert srv.bound is not None
            record = cli.ListenerRecord(
                host="127.0.0.1", port=srv.bound[1], iid=env.iid, pid=1, nonce="n"
            )
            own = await asyncio.to_thread(cli._default_verify_listener_live, record, env.iid)
            other = await asyncio.to_thread(cli._default_verify_listener_live, record, "z" * 52)
            return own, other
        finally:
            await srv.stop(notify=False)

    own, other = asyncio.run(main())
    assert own is True, injection
    assert other is False, injection


def test_injection_is_not_left_behind() -> None:
    """The fixture's teardown restored the standard library class (run after the cases above)."""
    assert ssl.SSLContext is _STDLIB_SSL_CONTEXT
