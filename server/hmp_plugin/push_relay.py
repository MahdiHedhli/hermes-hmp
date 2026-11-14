"""PN-REL HTTPS/signature client; navigation-only bytes, no provider credentials.

Each attempt owns one session and verified TLS connection. There is no redirect,
proxy, cookie, trust fallback or automatic retry. The dispatcher owns retry/CAS.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import ssl
from collections.abc import Callable

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from . import crypto, wire
from .identity import InstanceIdentity
from .push_config import RelayConfig, evaluate
from .push_dispatch import RelayAttempt

REQUEST_CAP = 4096
RESPONSE_CAP = 1024
CONNECT_S = 5
TOTAL_S = 10

_RESULTS = {
    202: "accepted",
    410: "provider_gone",
    422: "sealed_invalid",
    409: "replayed",
    429: "rate_limited",
    401: "unauthorized",
    400: "bad_request",
    502: "provider_unavailable",
    503: "unavailable",
}


def _checked_config(config: RelayConfig) -> RelayConfig:
    block = {
        "enabled": True,
        "relay_url": config.url,
        "relay_audience": config.audience,
        "relay_kids": list(config.kids),
    }
    if config.spki_pins is not None:
        block["relay_spki_pins"] = [wire.b64u_encode(pin) for pin in config.spki_pins]
    parsed = evaluate(block, direct_send=True, approvals=True, phone_chat=False)
    if not parsed.available or parsed.relay != config:
        raise ValueError("invalid relay configuration")
    return config


def signed_request(identity: InstanceIdentity, attempt: RelayAttempt) -> tuple[bytes, str]:
    """Closed bounded wire shape and TR framing over raw R/K/C and derived iid."""
    config = _checked_config(attempt.relay)
    if not identity.still_current():
        raise ValueError("identity unavailable")
    key = identity.private_key()
    spki = crypto.spki_der(key.public_key())
    iid = crypto.spki_fingerprint(spki)
    if iid != identity.iid or iid != attempt.iid:
        raise ValueError("identity mismatch")
    for value, length in (
        (attempt.route, 32),
        (attempt.hint, 32),
        (attempt.collapse, 24),
        (attempt.nonce, 16),
    ):
        if type(value) is not bytes or len(value) != length:
            raise ValueError("invalid relay bytes")
    if type(attempt.sealed) is not bytes or not 82 <= len(attempt.sealed) <= 1105:
        raise ValueError("invalid relay seal")
    wire.require_int(attempt.ts, minimum=0, maximum=2**53 - 1)
    wire.require_int(attempt.ttl_s, minimum=60, maximum=900)
    if attempt.kid not in config.kids:
        raise ValueError("relay kid unavailable")
    if attempt.platform == "apns":
        valid = attempt.addr_kind == "apns_token" and attempt.env in ("sandbox", "production")
    elif attempt.platform == "fcm":
        valid = attempt.addr_kind in ("fcm_token", "fcm_fid") and attempt.env is None
    else:
        valid = False
    if not valid:
        raise ValueError("invalid provider combination")
    body = {
        "v": 1,
        "kind": "approval",
        "aud": config.audience,
        "iid_spki": wire.b64u_encode(spki),
        "ts": attempt.ts,
        "nonce": wire.b64u_encode(attempt.nonce),
        "kid": attempt.kid,
        "platform": attempt.platform,
        "addr_kind": attempt.addr_kind,
        "sealed": wire.b64u_encode(attempt.sealed),
        "route": wire.b64u_encode(attempt.route),
        "hint": wire.b64u_encode(attempt.hint),
        "collapse": wire.b64u_encode(attempt.collapse),
        "ttl_s": attempt.ttl_s,
    }
    if attempt.env is not None:
        body["env"] = attempt.env
    raw = wire.dump_json(body)
    if len(raw) > REQUEST_CAP:
        raise ValueError("relay body too large")
    transcript = b"HMP1-PUSH-RELAY" + crypto.length_prefixed(
        config.audience,
        iid,
        attempt.ts,
        attempt.nonce,
        attempt.kid,
        attempt.platform,
        attempt.addr_kind,
        attempt.env or "",
        hashlib.sha256(attempt.sealed).digest(),
        attempt.route,
        attempt.hint,
        attempt.collapse,
        attempt.ttl_s,
        "approval",
    )
    return raw, wire.b64u_encode(crypto.sign(key, transcript))


def _trust_context() -> ssl.SSLContext:
    return ssl.create_default_context(ssl.Purpose.SERVER_AUTH)


class _PinnedConnector(aiohttp.TCPConnector):
    """Check the verified leaf before ClientRequest.send can write any HTTP byte.

    This hook is tested against the committed aiohttp lock. Standard chain/name
    verification happens in super(); a pin is an additional constraint only.
    """

    def __init__(self, context: ssl.SSLContext, pins: tuple[bytes, ...] | None):
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ValueError("relay trust is not verified")
        super().__init__(ssl=context, limit=1, force_close=True, use_dns_cache=False)
        self._pins = pins

    async def _create_connection(self, req, traces, timeout):  # noqa: ASYNC109 - inherited aiohttp hook
        proto = await super()._create_connection(req, traces, timeout)
        try:
            if not req.is_ssl() or req.proxy is not None:
                raise ValueError("relay connection is not direct TLS")
            transport = proto.transport
            tls = transport.get_extra_info("ssl_object") if transport is not None else None
            if tls is None:
                raise ValueError("relay certificate unavailable")
            if self._pins is not None:
                cert = x509.load_der_x509_certificate(tls.getpeercert(binary_form=True))
                spki = cert.public_key().public_bytes(
                    serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
                )
                digest = hashlib.sha256(spki).digest()
                if not any(crypto.constant_time_equal(digest, pin) for pin in self._pins):
                    raise ValueError("relay certificate rejected")
        except Exception as exc:
            if proto.transport is not None:
                proto.transport.close()
            raise aiohttp.ClientConnectorSSLError(
                req.connection_key, ssl.SSLError("relay certificate rejected")
            ) from exc
        return proto


class RelayClient:
    def __init__(
        self,
        identity: InstanceIdentity,
        *,
        _ssl_factory: Callable[[], ssl.SSLContext] = _trust_context,
    ) -> None:
        self.identity, self._ssl_factory = identity, _ssl_factory
        self.closed = False
        self._sessions: set[aiohttp.ClientSession] = set()

    async def send(self, attempt: RelayAttempt) -> str:
        # Mark possible write BEFORE aiohttp writes headers. An after-write trace
        # could miss a partial write and wrongly permit retry after a provider attempt.
        written = False

        class MarkedRequest(aiohttp.ClientRequest):
            async def send(self, conn):
                nonlocal written
                written = True
                return await super().send(conn)

        session = None
        connector = None
        try:
            if self.closed:
                return "ambiguous"
            raw, signature = signed_request(self.identity, attempt)
            context = await asyncio.to_thread(self._ssl_factory)
            if self.closed or not self.identity.still_current():
                return "ambiguous"
            connector = _PinnedConnector(context, attempt.relay.spki_pins)
            session = aiohttp.ClientSession(
                connector=connector,
                trust_env=False,
                cookie_jar=aiohttp.DummyCookieJar(),
                request_class=MarkedRequest,
                auto_decompress=False,
                timeout=aiohttp.ClientTimeout(
                    total=TOTAL_S,
                    connect=CONNECT_S,
                    sock_connect=CONNECT_S,
                    ceil_threshold=float("inf"),
                ),
                max_line_size=1024,
                max_field_size=1024,
                max_headers=32,
            )
            self._sessions.add(session)
            async with session.post(
                attempt.relay.url.rstrip("/") + "/v1/push",
                data=raw,
                headers={"Content-Type": "application/json", "HMP-Relay-Signature": signature},
                allow_redirects=False,
            ) as response:
                if response.status not in _RESULTS or response.headers.get("Content-Encoding"):
                    return "ambiguous"
                if response.content_length is not None and response.content_length > RESPONSE_CAP:
                    return "ambiguous"
                data = bytearray()
                while len(data) <= RESPONSE_CAP:
                    chunk = await response.content.read(RESPONSE_CAP + 1 - len(data))
                    if not chunk:
                        break
                    data.extend(chunk)
                result = wire.parse_body(bytes(data), max_bytes=RESPONSE_CAP, max_depth=2)
                expected = _RESULTS[response.status]
                return expected if result == {"result": expected} else "ambiguous"
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientConnectorError, aiohttp.ConnectionTimeoutError):
            return "ambiguous" if written else "prewrite_failure"
        except TimeoutError:
            return "postwrite_timeout" if written else "prewrite_failure"
        except Exception:
            # Includes malformed/oversize/unknown responses and uncertain losses.
            # Never echo or log relay/provider text, URLs, handles or key material.
            return "ambiguous"
        finally:
            if session is not None:
                self._sessions.discard(session)
                with contextlib.suppress(Exception):
                    await session.close()
            elif connector is not None:
                with contextlib.suppress(Exception):
                    await connector.close()

    async def close(self) -> None:
        self.closed = True
        sessions, self._sessions = self._sessions, set()
        if sessions:
            await asyncio.gather(*(session.close() for session in sessions), return_exceptions=True)
