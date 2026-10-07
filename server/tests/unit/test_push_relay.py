"""Local verified HTTPS transport and independently framed signature evidence.

All identities, keys, certificates, destinations and responses are synthetic.
No provider delivery or device behavior is inferred from these tests.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import ipaddress
import json
import socket
import ssl
import struct
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.x509.oid import NameOID

from hmp_plugin import push_relay
from hmp_plugin.push_config import RelayConfig
from hmp_plugin.push_dispatch import RelayAttempt

ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
VECTORS = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "docs/architecture/contracts/vectors/hmp_push_relay_vectors.json"
    ).read_text()
)


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class Identity:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.spki = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.iid = (
            base64.b32encode(hashlib.sha256(self.spki).digest()).rstrip(b"=").decode().lower()
        )
        self.current = True

    def still_current(self):
        return self.current

    def private_key(self):
        return self.key


@pytest.fixture
def identity():
    return Identity()


def attempt(identity, url="https://relay.invalid/base", pins=None, **changes):
    return replace(
        RelayAttempt(
            RelayConfig(url, "synthetic-relay", ("test-kid",), pins),
            identity.iid,
            bytes(range(32)),
            bytes(range(32, 64)),
            bytes(range(64, 88)),
            "apns",
            "apns_token",
            "sandbox",
            "test-kid",
            b"synthetic-seal" * 7,
            330,
            1700000000,
            bytes(range(16)),
        ),
        **changes,
    )


def independent_transcript(body):
    """Manual TR encoder; no plugin framing, fingerprint, signature or wire helper."""
    spki = decode(body["iid_spki"])
    iid = base64.b32encode(hashlib.sha256(spki).digest()).rstrip(b"=").decode().lower()
    fields = (
        body["aud"],
        iid,
        struct.pack(">Q", body["ts"]),
        decode(body["nonce"]),
        body["kid"],
        body["platform"],
        body["addr_kind"],
        body.get("env", ""),
        hashlib.sha256(decode(body["sealed"])).digest(),
        decode(body["route"]),
        decode(body["hint"]),
        decode(body["collapse"]),
        struct.pack(">Q", body["ttl_s"]),
        body["kind"],
    )
    encoded = [v.encode("utf-8") if isinstance(v, str) else v for v in fields]
    return b"HMP1-PUSH-RELAY" + b"".join(struct.pack(">I", len(v)) + v for v in encoded)


@pytest.mark.parametrize(
    "platform,kind,env",
    [
        ("apns", "apns_token", "sandbox"),
        ("apns", "apns_token", "production"),
        ("fcm", "fcm_token", None),
        ("fcm", "fcm_fid", None),
    ],
)
def test_independent_signature_transcript_and_der(identity, platform, kind, env):
    raw, header = push_relay.signed_request(
        identity, attempt(identity, platform=platform, addr_kind=kind, env=env)
    )
    body = json.loads(raw)
    assert len(raw) <= 4096 and "iid" not in body and ("env" in body) == (env is not None)
    signature = decode(header)
    assert b64(signature) == header
    r, s = utils.decode_dss_signature(signature)
    assert 0 < r < ORDER and 0 < s < ORDER
    assert utils.encode_dss_signature(r, s) == signature  # exact minimal DER, no trailing bytes
    transcript = independent_transcript(body)
    verifier = serialization.load_der_public_key(decode(body["iid_spki"]))
    verifier.verify(signature, transcript, ec.ECDSA(hashes.SHA256()))
    # The independent vetted generator supplies both canonical low-S and high-S vectors.
    generated = identity.key.sign(transcript, ec.ECDSA(hashes.SHA256()))
    gr, gs = utils.decode_dss_signature(generated)
    for alternate in (min(gs, ORDER - gs), max(gs, ORDER - gs)):
        verifier.verify(
            utils.encode_dss_signature(gr, alternate), transcript, ec.ECDSA(hashes.SHA256())
        )
    for field in (
        "aud",
        "platform",
        "addr_kind",
        "env",
        "route",
        "hint",
        "collapse",
        "sealed",
        "kid",
        "ttl_s",
        "ts",
        "nonce",
        "kind",
        "iid_spki",
    ):
        changed = dict(body)
        if field == "iid_spki":
            changed[field] = b64(Identity().spki)
        elif field in ("ttl_s", "ts"):
            changed[field] = body[field] + 1
        else:
            changed[field] = (
                b64(b"changed")
                if field in ("route", "hint", "collapse", "sealed", "nonce")
                else "changed"
            )
        with pytest.raises(InvalidSignature):
            verifier.verify(signature, independent_transcript(changed), ec.ECDSA(hashes.SHA256()))


@pytest.mark.parametrize(
    "changes",
    [
        {"iid": "wrong"},
        {"route": b"short"},
        {"hint": b"short"},
        {"collapse": b"short"},
        {"nonce": b"short"},
        {"sealed": b"x" * 81},
        {"sealed": b"x" * 1106},
        {"ttl_s": True},
        {"ttl_s": 59},
        {"ttl_s": 901},
        {"ts": -1},
        {"ts": 2**53},
        {"platform": "unknown"},
        {"addr_kind": "fcm_token"},
        {"env": None},
        {"kid": "unknown"},
    ],
)
def test_invalid_request_never_signed(identity, changes):
    with pytest.raises(ValueError):
        push_relay.signed_request(identity, attempt(identity, **changes))


@pytest.fixture
def certificates(tmp_path):
    ca_key = ec.generate_private_key(ec.SECP256R1())
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic root")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )

    def create(*, correct_name=True, trusted=True):
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic leaf")])
        san = (
            [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            if correct_name
            else [x509.DNSName("wrong.invalid")]
        )
        leaf = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(ca_name if trusted else name)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName(san), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    ca_key.public_key() if trusted else leaf_key.public_key()
                ),
                critical=False,
            )
            .sign(ca_key if trusted else leaf_key, hashes.SHA256())
        )
        pem, key = tmp_path / "leaf.pem", tmp_path / "leaf.key"
        pem.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
        key.write_bytes(
            leaf_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        key.chmod(0o600)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(pem, key)

        def trust():
            ctx = ssl.create_default_context()
            ctx.load_verify_locations(cadata=ca.public_bytes(serialization.Encoding.PEM).decode())
            return ctx

        def pin(key):
            return hashlib.sha256(
                key.public_bytes(
                    serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
                )
            ).digest()

        return context, trust, pin(leaf_key.public_key()), pin(ca_key.public_key())

    return create


@contextlib.asynccontextmanager
async def endpoint(
    context, *, status=202, body=b'{"result":"accepted"}', extra=b"", slow=None, chunked=False
):
    requests, tasks = [], set()

    async def receive(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        try:
            header = await reader.readuntil(b"\r\n\r\n")
            length = next(
                int(h.split(b":", 1)[1])
                for h in header.split(b"\r\n")
                if h.lower().startswith(b"content-length:")
            )
            requests.append((header, await reader.readexactly(length)))
            if slow is not None:
                await slow.wait()
            payload = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n" if chunked else body
            size_header = (
                b"Transfer-Encoding: chunked\r\n"
                if chunked
                else f"Content-Length: {len(body)}\r\n".encode()
            )
            writer.write(
                f"HTTP/1.1 {status} Synthetic\r\n".encode()
                + size_header
                + extra
                + b"Connection: close\r\n\r\n"
                + payload
            )
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            tasks.discard(task)

    service = await asyncio.start_server(receive, "127.0.0.1", 0, ssl=context)
    port = service.sockets[0].getsockname()[1]
    try:
        yield f"https://127.0.0.1:{port}/base", requests
    finally:
        service.close()
        await service.wait_closed()
        for task in list(tasks):
            task.cancel()
        await asyncio.gather(*list(tasks), return_exceptions=True)


@pytest.mark.parametrize("pins", ["none", "leaf", "rotating", "issuer", "mismatch"])
def test_real_tls_leaf_pin_before_http_bytes(identity, certificates, pins):
    async def scenario():
        tls, trust, leaf, issuer = certificates()
        configured = {
            "none": None,
            "leaf": (leaf,),
            "rotating": (b"x" * 32, leaf),
            "issuer": (issuer,),
            "mismatch": (b"x" * 32,),
        }[pins]
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls) as (url, seen):
            result = await client.send(attempt(identity, url, configured))
            if pins in ("issuer", "mismatch"):
                assert result == "prewrite_failure" and seen == []
            else:
                assert result == "accepted" and len(seen) == 1
                header, raw = seen[0]
                assert header.startswith(b"POST /base/v1/push HTTP/1.1\r\n")
                signature = next(
                    h.split(b":", 1)[1].strip().decode()
                    for h in header.split(b"\r\n")
                    if h.lower().startswith(b"hmp-relay-signature:")
                )
                identity.key.public_key().verify(
                    decode(signature),
                    independent_transcript(json.loads(raw)),
                    ec.ECDSA(hashes.SHA256()),
                )
        await client.close()
        assert client.closed and not client._sessions

    asyncio.run(scenario())


@pytest.mark.parametrize("correct_name,trusted", [(False, True), (True, False)])
def test_matching_pin_does_not_replace_chain_or_hostname(
    identity, certificates, correct_name, trusted
):
    async def scenario():
        tls, trust, leaf, _ = certificates(correct_name=correct_name, trusted=trusted)
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls) as (url, seen):
            assert await client.send(attempt(identity, url, (leaf,))) == "prewrite_failure"
            assert seen == []
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("status,result", list(push_relay._RESULTS.items()))
def test_closed_status_results_and_proxy_env_ignored(
    identity, certificates, monkeypatch, status, result
):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")

    async def scenario():
        tls, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls, status=status, body=json.dumps({"result": result}).encode()) as (
            url,
            seen,
        ):
            assert await client.send(attempt(identity, url)) == result and len(seen) == 1
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "status,body,extra",
    [
        (302, b"{}", b"Location: https://127.0.0.1:1/leak\r\n"),
        (200, b'{"result":"accepted"}', b""),
        (202, b'{"result":"unknown"}', b""),
        (202, b'{"result":"accepted","extra":"private-canary"}', b""),
        (202, b'{"result":"accepted","result":"accepted"}', b""),
        (202, b"\xff", b""),
        (202, b"x" * 1025, b""),
        (202, b'{"result":"accepted"}', b"Content-Encoding: gzip\r\n"),
        (410, b'{"result":"accepted"}', b""),
    ],
)
def test_uncertain_responses_never_echo_or_retry(
    identity, certificates, caplog, status, body, extra
):
    async def scenario():
        tls, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls, status=status, body=body, extra=extra) as (url, seen):
            assert await client.send(attempt(identity, url)) == "ambiguous"
            assert len(seen) == 1
        await client.close()

    asyncio.run(scenario())
    assert "private-canary" not in caplog.text


def test_postwrite_timeout_is_not_prewrite(identity, certificates, monkeypatch):
    monkeypatch.setattr(push_relay, "TOTAL_S", 0.1)

    async def scenario():
        tls, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls, slow=asyncio.Event()) as (url, seen):
            assert await client.send(attempt(identity, url)) == "postwrite_timeout"
            assert len(seen) == 1
        await client.close()

    asyncio.run(scenario())


def test_tcp_refusal_is_certain_prewrite_and_does_not_retry(identity, certificates):
    async def scenario():
        _, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        # Reserve a local socket without listening, so no other process can take
        # this destination between selection and the expected TCP refusal.
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
            assert (
                await client.send(attempt(identity, f"https://127.0.0.1:{port}"))
                == "prewrite_failure"
            )
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "body,extra",
    [
        (b"x" * 1025, b""),
        (b'{"result":"accepted"}', b"X-Large: " + b"x" * 1100 + b"\r\n"),
    ],
)
def test_chunked_and_headers_bounded(identity, certificates, body, extra):
    async def scenario():
        tls, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls, body=body, extra=extra, chunked=True) as (url, seen):
            assert await client.send(attempt(identity, url)) == "ambiguous"
            assert len(seen) == 1
        await client.close()

    asyncio.run(scenario())


def test_close_interrupts_session_without_retry_or_raw_logs(identity, certificates, caplog):
    async def scenario():
        tls, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        async with endpoint(tls, slow=asyncio.Event()) as (url, seen):
            sending = asyncio.create_task(client.send(attempt(identity, url)))
            async with asyncio.timeout(3):
                while not seen:  # noqa: ASYNC110 - bounded observation of test HTTP arrival
                    await asyncio.sleep(0.005)
            await client.close()
            assert await sending == "ambiguous"
            assert len(seen) == 1 and not client._sessions
            assert await client.send(attempt(identity, url)) == "ambiguous"

    asyncio.run(scenario())
    assert b64(bytes(range(32))) not in caplog.text and "synthetic-seal" not in caplog.text


def test_identity_change_during_trust_setup_prevents_http(identity, certificates):
    async def scenario():
        tls, trust, _, _ = certificates()

        def changed():
            context = trust()
            identity.current = False
            return context

        client = push_relay.RelayClient(identity, _ssl_factory=changed)
        async with endpoint(tls) as (url, seen):
            assert await client.send(attempt(identity, url)) == "ambiguous" and seen == []
        await client.close()

    asyncio.run(scenario())


def test_failed_session_construction_closes_connector(identity, certificates, monkeypatch):
    closed = []
    real = push_relay._PinnedConnector

    class Connector(real):
        async def close(self, *args, **kwargs):
            closed.append(True)
            await super().close(*args, **kwargs)

    def failed_session(**kwargs):
        raise ValueError("synthetic construction failure")

    monkeypatch.setattr(push_relay, "_PinnedConnector", Connector)
    monkeypatch.setattr(push_relay.aiohttp, "ClientSession", failed_session)

    async def scenario():
        _, trust, _, _ = certificates()
        client = push_relay.RelayClient(identity, _ssl_factory=trust)
        assert await client.send(attempt(identity)) == "ambiguous"
        assert closed == [True] and not client._sessions
        await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("vector", VECTORS["cases"], ids=lambda v: v["label"])
def test_independent_fixed_signature_vectors(vector):
    assert VECTORS["synthetic_only"] is True
    private = ec.derive_private_key(int(VECTORS["test_private_scalar_hex"], 16), ec.SECP256R1())
    ident = Identity()
    ident.key = private
    ident.spki = private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    ident.iid = base64.b32encode(hashlib.sha256(ident.spki).digest()).rstrip(b"=").decode().lower()
    assert ident.iid == VECTORS["iid"]
    assert ident.spki.hex() == VECTORS["spki_der_hex"]
    body, raw_fields = vector["wire_fields"], vector["raw_fields_hex"]
    config = RelayConfig("https://relay.invalid/base", body["aud"], (body["kid"],), None)
    selected = RelayAttempt(
        config,
        ident.iid,
        bytes.fromhex(raw_fields["route"]),
        bytes.fromhex(raw_fields["hint"]),
        bytes.fromhex(raw_fields["collapse"]),
        body["platform"],
        body["addr_kind"],
        body.get("env"),
        body["kid"],
        bytes.fromhex(raw_fields["sealed"]),
        body["ttl_s"],
        body["ts"],
        bytes.fromhex(raw_fields["nonce"]),
    )
    raw, signature = push_relay.signed_request(ident, selected)
    assert json.loads(raw) == body
    expected = bytes.fromhex(vector["transcript_hex"])
    assert independent_transcript(body) == expected
    assert hashlib.sha256(expected).hexdigest() == vector["transcript_sha256"]
    private.public_key().verify(decode(signature), expected, ec.ECDSA(hashes.SHA256()))
    for name in ("signature_der_b64u", "high_s_signature_der_b64u"):
        private.public_key().verify(decode(vector[name]), expected, ec.ECDSA(hashes.SHA256()))


DER_CASES = [
    (group["name"], value)
    for group in VECTORS["strict_der_vectors"]
    for value in group["der_cases"]
]


@pytest.mark.parametrize(
    "name,value", DER_CASES, ids=[f"{name}-{value['label']}" for name, value in DER_CASES]
)
def test_independent_der_contract_vectors(name, value):
    """Vetted primitive/reference evidence, not a test of the separate relay verifier."""
    vector = next(v for v in VECTORS["cases"] if v["label"] == name)
    signature = bytes.fromhex(value["signature_der_hex"])
    try:
        r, s = utils.decode_dss_signature(signature)
    except ValueError:
        result = "400"
    else:
        if utils.encode_dss_signature(r, s) != signature or not (0 < r < ORDER and 0 < s < ORDER):
            result = "400"
        else:
            verifier = serialization.load_der_public_key(bytes.fromhex(VECTORS["spki_der_hex"]))
            try:
                verifier.verify(
                    signature, bytes.fromhex(vector["transcript_hex"]), ec.ECDSA(hashes.SHA256())
                )
            except InvalidSignature:
                result = "401"
            else:
                result = "accept"
    assert result == value["expected"].split(";", 1)[0]
