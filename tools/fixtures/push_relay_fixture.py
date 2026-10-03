"""T029's disposable loopback HTTPS receiver, not a provider or HPKE implementation.

Only independently signature-verified requests are captured, in bounded memory.
No production relay framing/wire helpers are imported. Certificates are synthetic
and live in a fresh private directory outside the real home. There is one owned
server thread, bounded reads, no access log, and no other network destination.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import socketserver
import ssl
import struct
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import _fixture_common as fc
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

BODY_CAP = 4096
HEADER_CAP = 8192
CAPTURE_CAP = 64
CONNECTION_S = 2
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str, *, length: int | None = None) -> bytes:
    if type(value) is not str or not value or len(value) > 1500:
        raise ValueError("bad bytes")
    raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    if _b64(raw) != value or (length is not None and len(raw) != length):
        raise ValueError("bad bytes")
    return raw


def independent_transcript(body: dict) -> bytes:
    """Encode TR directly from the contract, never through the implementation under test."""
    required = {
        "v", "kind", "aud", "iid_spki", "ts", "nonce", "kid", "platform", "addr_kind",
        "sealed", "route", "hint", "collapse", "ttl_s",
    }
    if type(body) is not dict or set(body) not in (required, required | {"env"}):
        raise ValueError("bad shape")
    if type(body["v"]) is not int or body["v"] != 1 or body["kind"] != "approval":
        raise ValueError("bad kind")
    for field in ("aud", "kid", "platform", "addr_kind"):
        if type(body[field]) is not str or not 1 <= len(body[field]) <= 128:
            raise ValueError("bad text")
    if body["platform"] == "apns":
        if body["addr_kind"] != "apns_token" or body.get("env") not in ("sandbox", "production"):
            raise ValueError("bad provider")
    elif body["platform"] == "fcm":
        if body["addr_kind"] not in ("fcm_token", "fcm_fid") or "env" in body:
            raise ValueError("bad provider")
    else:
        raise ValueError("bad provider")
    if type(body["ts"]) is not int or not 0 <= body["ts"] < 2**53:
        raise ValueError("bad timestamp")
    if type(body["ttl_s"]) is not int or not 60 <= body["ttl_s"] <= 900:
        raise ValueError("bad ttl")
    spki = _decode(body["iid_spki"])
    iid = base64.b32encode(hashlib.sha256(spki).digest()).rstrip(b"=").decode("ascii").lower()
    sealed = _decode(body["sealed"])
    if not 82 <= len(sealed) <= 1105:
        raise ValueError("bad seal length")
    fields = (
        body["aud"], iid, struct.pack(">Q", body["ts"]), _decode(body["nonce"], length=16),
        body["kid"], body["platform"], body["addr_kind"], body.get("env", ""),
        hashlib.sha256(sealed).digest(), _decode(body["route"], length=32),
        _decode(body["hint"], length=32), _decode(body["collapse"], length=24),
        struct.pack(">Q", body["ttl_s"]), body["kind"],
    )
    raw_fields = (value.encode("utf-8") if isinstance(value, str) else value for value in fields)
    return b"HMP1-PUSH-RELAY" + b"".join(
        struct.pack(">I", len(value)) + value for value in raw_fields
    )


def verify_request(raw: bytes, signature: str) -> dict:
    """Check the independently framed signature, not admission, replay, HPKE or delivery."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    body = json.loads(raw, object_pairs_hook=unique_pairs)
    transcript = independent_transcript(body)
    spki = _decode(body["iid_spki"])
    verifier = serialization.load_der_public_key(spki)
    if not isinstance(verifier, ec.EllipticCurvePublicKey) or not isinstance(
        verifier.curve, ec.SECP256R1
    ):
        raise ValueError("bad signing key")
    if verifier.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    ) != spki:
        raise ValueError("bad signing key encoding")
    der = _decode(signature)
    r, s = utils.decode_dss_signature(der)
    if not 0 < r < P256_ORDER or not 0 < s < P256_ORDER:
        raise ValueError("bad signature range")
    if utils.encode_dss_signature(r, s) != der:
        raise ValueError("bad signature encoding")
    verifier.verify(der, transcript, ec.ECDSA(hashes.SHA256()))
    return body


def _certificates(root: Path) -> tuple[Path, Path, Path, bytes]:
    ca_key, leaf_key = (ec.generate_private_key(ec.SECP256R1()) for _ in range(2))
    now = datetime.now(UTC)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Disposable fixture CA")])
    ca = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        ).sign(ca_key, hashes.SHA256())
    )
    leaf = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Loopback fixture")]))
        .issuer_name(ca_name).public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ca_path, cert_path, key_path = (root / name for name in ("ca.pem", "leaf.pem", "leaf.key"))
    materials = (
        ca.public_bytes(serialization.Encoding.PEM), leaf.public_bytes(serialization.Encoding.PEM),
        leaf_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    for path, material in zip((ca_path, cert_path, key_path), materials, strict=True):
        # The containing directory was freshly created 0700; no existing file is followed.
        with path.open("xb") as handle:
            path.chmod(0o600)
            handle.write(material)
    spki = leaf_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return ca_path, cert_path, key_path, hashlib.sha256(spki).digest()


def _receive(sock: ssl.SSLSocket, deadline: float, size: int) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("fixture deadline")
    sock.settimeout(remaining)
    chunk = sock.recv(size)
    if not chunk:
        raise ValueError("incomplete request")
    return chunk


def _request(sock: ssl.SSLSocket, deadline: float) -> tuple[bytes, str]:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        data.extend(_receive(sock, deadline, min(512, HEADER_CAP + 1 - len(data))))
        if len(data) > HEADER_CAP:
            raise ValueError("headers too large")
    head, raw = bytes(data).split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    if lines[0] != b"POST /base/v1/push HTTP/1.1" or len(lines) > 33:
        raise ValueError("wrong request")
    headers = {}
    for line in lines[1:]:
        if len(line) > 1024 or line.startswith((b" ", b"\t")) or b":" not in line:
            raise ValueError("bad header")
        name, value = line.split(b":", 1)
        name = name.decode("ascii").lower()
        if name in headers:
            raise ValueError("duplicate header")
        headers[name] = value.decode("ascii").strip()
    size_text = headers.get("content-length", "")
    if not size_text.isascii() or not size_text.isdecimal() or len(size_text) > 5:
        raise ValueError("missing length")
    size = int(size_text)
    if not 1 <= size <= BODY_CAP or "transfer-encoding" in headers:
        raise ValueError("bad body length")
    if headers.get("content-type") != "application/json" or len(raw) > size:
        raise ValueError("bad body")
    while len(raw) < size:
        raw += _receive(sock, deadline, size - len(raw))
    return raw, headers["hmp-relay-signature"]


class FakeHttpsRelay:
    """One loopback listener, private CA, bounded captures, explicit owned teardown."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        fc.assert_outside_real_home(self.root, "fake relay certificates")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.ca_path, cert_path, key_path, self.leaf_pin = _certificates(self.root)
        self._lock = threading.Lock()
        self._records: list[bytes] = []
        self._statuses: dict[int, int] = {}
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_path, key_path)
        relay = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                deadline = time.monotonic() + CONNECTION_S
                self.request.settimeout(CONNECTION_S)
                try:
                    with context.wrap_socket(self.request, server_side=True) as tls:
                        try:
                            raw, signature = _request(tls, deadline)
                            verify_request(raw, signature)
                            with relay._lock:
                                if len(relay._records) < CAPTURE_CAP:
                                    relay._records.append(raw)
                                    status = 202
                                else:
                                    status = 429
                        except InvalidSignature:
                            status = 401
                        except (
                            ValueError, KeyError, TypeError, RecursionError, TimeoutError, OSError
                        ):
                            status = 400
                        with relay._lock:
                            relay._statuses[status] = relay._statuses.get(status, 0) + 1
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            return
                        tls.settimeout(remaining)
                        result = {
                            202: "accepted", 429: "rate_limited",
                            401: "unauthorized", 400: "bad_request",
                        }[status]
                        response = json.dumps({"result": result}).encode("ascii")
                        tls.sendall(
                            (
                                f"HTTP/1.1 {status} Fixture\r\n"
                                f"Content-Length: {len(response)}\r\n"
                                "Content-Type: application/json\r\nConnection: close\r\n\r\n"
                            ).encode("ascii") + response
                        )
                except (OSError, ValueError):
                    return

        self._server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        self.url = f"https://127.0.0.1:{self._server.server_address[1]}/base"
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05},
            name="synthetic-push-relay", daemon=True,
        )
        self._closed = False
        self._thread.start()

    def trust_context(self) -> ssl.SSLContext:
        # An additional synthetic CA only; chain and hostname verification remain enabled.
        return ssl.create_default_context(cafile=str(self.ca_path))

    def records(self) -> tuple[dict, ...]:
        with self._lock:
            return tuple(json.loads(raw) for raw in self._records)

    def status_count(self, status: int) -> int:
        with self._lock:
            return self._statuses.get(status, 0)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=CONNECTION_S + 1)
        if self.alive:
            raise RuntimeError("fixture relay did not stop")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
