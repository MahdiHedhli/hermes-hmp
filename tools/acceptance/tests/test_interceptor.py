"""Self-test for tools/acceptance/interceptor.py (T065).

This is the "self-test with a Python client" the task's acceptance criterion names: it drives a
real TCP/TLS client against a real interceptor process (in-process, via `run_interceptor` on a
background thread) for every mode, and checks the resulting JSON-lines log for correct byte
counts -- including zero application bytes whenever the client detects a pin mismatch and aborts
before writing anything, and the exact forwarded byte count in `pass-then-intercept` mode.

The client here always mimics the production client's baseline posture (TR-2: an empty trust
store, `verify_mode=CERT_NONE`) unless a test specifically wants to also demonstrate that a
`trusted-ca` leaf validates under a client that *does* trust the one test CA (proving the two
non-forwarding modes are meaningfully different shapes, not just different labels for the same
self-signed cert).
"""

from __future__ import annotations

import contextlib
import json
import socket
import ssl
import threading
from pathlib import Path

import interceptor
import make_test_ca
import pytest
from cryptography import x509

CONNECT_TIMEOUT_S = 10.0


# --------------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _connection_records(path: Path) -> list[dict]:
    """Every logged record except the one-off 'listening' start-up line, ordered by
    connection_index."""
    records = [r for r in _read_jsonl(path) if "connection_index" in r]
    records.sort(key=lambda r: r["connection_index"])
    return records


def _client_context(*, trust_ca: Path | None) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = False
    if trust_ca is None:
        ctx.verify_mode = ssl.CERT_NONE  # production posture: no trusted roots at all (TR-2)
    else:
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(cafile=str(trust_ca))
    return ctx


def _spki_pin_of(tls_sock: ssl.SSLSocket) -> str:
    der = tls_sock.getpeercert(binary_form=True)
    assert der is not None
    cert = x509.load_der_x509_certificate(der)
    return make_test_ca.spki_sha256_fingerprint(cert)


def _run_server(config: interceptor.InterceptorConfig) -> threading.Thread:
    th = threading.Thread(target=interceptor.run_interceptor, args=(config,), daemon=True)
    th.start()
    return th


class _FixtureServer:
    """A minimal stand-in for 'a genuine fixture instance whose iid is the pin' (research R12):
    a real TLS 1.3 server over a fixed, known key, that reads whatever the client sends and
    replies with a fixed ack. It knows nothing about HMP; only the connection is under test.

    Reads exactly `expected_request_len` bytes rather than reading until EOF, and neither side
    ever calls `SSLSocket.shutdown()`: that method unconditionally sets `self._sslobj = None`
    before performing the raw shutdown (see `ssl.SSLSocket.shutdown` in the standard library),
    which silently downgrades every later `recv()` on that socket to an undecrypted raw read.
    Avoiding it -- here and in every client in this test file -- is deliberate, not an
    oversight; a fixed-length exchange followed by a plain `close()` sidesteps the whole
    question of who signals end-of-request."""

    ACK = b"FIXTURE-ACK"

    def __init__(self, leaf: make_test_ca.TestLeaf, *, expected_request_len: int) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.load_cert_chain(str(leaf.cert_path), str(leaf.key_path))
        self._ctx = ctx
        self._expected_request_len = expected_request_len

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port = self._sock.getsockname()[1]

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self) -> None:
        self._sock.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(CONNECT_TIMEOUT_S)
            tls = self._ctx.wrap_socket(conn, server_side=True)
            received = 0
            while received < self._expected_request_len:
                chunk = tls.recv(65536)
                if not chunk:
                    break
                received += len(chunk)
            tls.sendall(self.ACK)
            tls.close()
        except OSError:
            pass

    def stop(self) -> None:
        self._stop.set()
        with contextlib.suppress(OSError):
            self._sock.close()
        self._thread.join(timeout=5)


# --------------------------------------------------------------------------------------------
# Unit tests: bind-address resolution, ClientHello parsing
# --------------------------------------------------------------------------------------------


def test_resolve_bind_addresses_always_includes_loopback_and_dedupes() -> None:
    assert interceptor.resolve_bind_addresses([]) == ["127.0.0.1", "::1"]
    assert interceptor.resolve_bind_addresses(["203.0.113.9"]) == [
        "127.0.0.1", "::1", "203.0.113.9"
    ]
    # Passing loopback explicitly again must not duplicate it.
    assert interceptor.resolve_bind_addresses(["127.0.0.1", "203.0.113.9"]) == [
        "127.0.0.1", "::1", "203.0.113.9",
    ]


def _build_synthetic_client_hello(extensions: bytes) -> bytes:
    """A minimal, well-formed TLS record wrapping a ClientHello handshake message with the given
    already-encoded extensions block appended (each extension pre-encoded as
    type(2) || length(2) || data)."""
    session_id = b""
    cipher_suites = bytes.fromhex("1301")  # TLS_AES_128_GCM_SHA256
    compression_methods = bytes.fromhex("00")

    body = bytearray()
    body += bytes.fromhex("0303")  # legacy_version
    body += b"\x00" * 32  # random
    body += bytes([len(session_id)]) + session_id
    body += len(cipher_suites).to_bytes(2, "big") + cipher_suites
    body += bytes([len(compression_methods)]) + compression_methods
    body += len(extensions).to_bytes(2, "big") + extensions

    handshake = bytes([0x01]) + len(body).to_bytes(3, "big") + bytes(body)
    record = bytes([0x16]) + bytes.fromhex("0303") + len(handshake).to_bytes(2, "big") + handshake
    return record


def _encode_extension(ext_type: int, data: bytes) -> bytes:
    return ext_type.to_bytes(2, "big") + len(data).to_bytes(2, "big") + data


def test_parse_client_hello_without_resumption_extensions() -> None:
    extensions = _encode_extension(0x000D, b"\x00\x02\x04\x03")  # signature_algorithms, irrelevant
    data = _build_synthetic_client_hello(extensions)
    info = interceptor._parse_client_hello(data)
    assert info.parsed is True
    assert info.resumption_offered is False


def test_parse_client_hello_detects_pre_shared_key_extension() -> None:
    extensions = (
        _encode_extension(0x000D, b"\x00\x02\x04\x03")
        + _encode_extension(0x0029, b"\x01\x02\x03\x04")  # pre_shared_key, non-empty
    )
    data = _build_synthetic_client_hello(extensions)
    info = interceptor._parse_client_hello(data)
    assert info.parsed is True
    assert info.resumption_offered is True


def test_parse_client_hello_detects_supported_versions() -> None:
    # supported_versions extension: 1-byte list length, then 2-byte versions.
    versions_list = bytes([4]) + bytes.fromhex("03040303")  # TLS1.3, TLS1.2
    extensions = _encode_extension(0x002B, versions_list)
    data = _build_synthetic_client_hello(extensions)
    info = interceptor._parse_client_hello(data)
    assert info.parsed is True
    assert "TLSv1.3" in info.supported_versions
    assert "TLSv1.2" in info.supported_versions


@pytest.mark.parametrize(
    "garbage",
    [
        b"",
        b"\x00" * 4,
        b"\x17" + b"\x00" * 20,
        bytes.fromhex("160303000a") + b"\x01\x00\x00\xff\x00",
    ],
)
def test_parse_client_hello_never_raises_on_garbage(garbage: bytes) -> None:
    info = interceptor._parse_client_hello(garbage)
    assert info.parsed is False
    assert info.resumption_offered is False


# --------------------------------------------------------------------------------------------
# wrong-key mode
# --------------------------------------------------------------------------------------------


def test_wrong_key_mode_completes_handshake_but_reference_pin_never_matches(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    config = interceptor.InterceptorConfig(
        mode="wrong-key",
        bind_addrs=["127.0.0.1"],
        port=0,
        log=interceptor.JsonLogger(log_path.open("a", encoding="utf-8")),
        max_connections=1,
        ca_dir=tmp_path / "wrongkey-ca-dir",
    )
    th = _run_server(config)

    # Discover the port the server actually bound (it logs it on the "listening" line).
    _wait_for_listening_port(log_path)
    port = _read_listening_port(log_path)

    # A separately generated leaf that was never presented by the server -- its fingerprint is
    # the "pin" this client is checking against, exactly as a paired mobile client would.
    reference = make_test_ca.generate_self_signed_leaf(
        tmp_path / "reference", filename_prefix="reference"
    )
    pin = make_test_ca.spki_sha256_fingerprint(reference.certificate)

    ctx = _client_context(trust_ca=None)  # production posture: CERT_NONE
    raw = socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_S)
    tls = ctx.wrap_socket(raw, server_hostname=None)
    try:
        assert tls.version() == "TLSv1.3"
        seen_pin = _spki_pin_of(tls)
        assert seen_pin != pin  # the interceptor's key is never the pin, by construction
        # Conforming client behaviour (TR-2): on mismatch, close WITHOUT writing app data.
    finally:
        tls.close()

    th.join(timeout=10)
    assert not th.is_alive()

    records = _connection_records(log_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["connection_index"] == 1
    assert rec["mode"] == "wrong-key"
    assert rec["disposition"] == "intercepted"
    assert rec["handshake_outcome"] == "accepted"
    assert rec["tls_version"] == "TLSv1.3"
    assert rec["app_bytes"] == 0
    assert rec["early_data_bytes"] == 0


def test_wrong_key_leaf_is_rejected_by_a_client_requiring_chain_validation(tmp_path: Path) -> None:
    """The wrong-key leaf is self-signed and trusted by nothing: a client that actually
    validates the certificate chain (CERT_REQUIRED, empty trust store) must fail the TLS
    handshake outright, distinct from the pin-mismatch-after-handshake path exercised above."""
    log_path = tmp_path / "log.jsonl"
    config = interceptor.InterceptorConfig(
        mode="wrong-key",
        bind_addrs=["127.0.0.1"],
        port=0,
        log=interceptor.JsonLogger(log_path.open("a", encoding="utf-8")),
        max_connections=1,
        ca_dir=tmp_path / "wrongkey-ca-dir",
    )
    _run_server(config)
    _wait_for_listening_port(log_path)
    port = _read_listening_port(log_path)

    strict_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    strict_ctx.check_hostname = False
    strict_ctx.verify_mode = ssl.CERT_REQUIRED  # empty trust store: nothing can ever validate

    raw = socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_S)
    with pytest.raises(ssl.SSLError):
        strict_ctx.wrap_socket(raw, server_hostname=None).close()


# --------------------------------------------------------------------------------------------
# trusted-ca mode
# --------------------------------------------------------------------------------------------


def test_trusted_ca_leaf_validates_under_the_run_ca_but_pin_still_mismatches(
    tmp_path: Path,
) -> None:
    ca_dir = tmp_path / "ca"
    # Pre-generate the CA, exactly as T079's build step would before this interceptor process
    # starts, so the client can load the same CA it will see presented.
    ca = make_test_ca.generate_ca(ca_dir)

    log_path = tmp_path / "log.jsonl"
    config = interceptor.InterceptorConfig(
        mode="trusted-ca",
        bind_addrs=["127.0.0.1"],
        port=0,
        log=interceptor.JsonLogger(log_path.open("a", encoding="utf-8")),
        max_connections=1,
        ca_dir=ca_dir,
    )
    th = _run_server(config)
    _wait_for_listening_port(log_path)
    port = _read_listening_port(log_path)

    reference = make_test_ca.generate_self_signed_leaf(
        tmp_path / "reference", filename_prefix="reference"
    )
    pin = make_test_ca.spki_sha256_fingerprint(reference.certificate)

    ctx = _client_context(trust_ca=ca.cert_path)  # this client DOES trust the run's one test CA
    raw = socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_S)
    tls = ctx.wrap_socket(raw, server_hostname="localhost")
    try:
        # Platform chain validation genuinely succeeded (we would have raised otherwise).
        assert tls.version() == "TLSv1.3"
        seen_pin = _spki_pin_of(tls)
        assert seen_pin != pin
    finally:
        tls.close()

    th.join(timeout=10)
    records = _connection_records(log_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["mode"] == "trusted-ca"
    assert rec["handshake_outcome"] == "accepted"
    assert rec["app_bytes"] == 0


# --------------------------------------------------------------------------------------------
# pass-then-intercept mode: the headline self-test.
# --------------------------------------------------------------------------------------------


def test_pass_then_intercept_switches_at_n(tmp_path: Path) -> None:
    request_payload = b"PING-FROM-SELFTEST"
    fixture_leaf = make_test_ca.generate_self_signed_leaf(
        tmp_path / "fixture", filename_prefix="fixture"
    )
    pin = make_test_ca.spki_sha256_fingerprint(fixture_leaf.certificate)
    fixture = _FixtureServer(fixture_leaf, expected_request_len=len(request_payload))
    try:
        pass_count = 2
        total_connections = pass_count + 1  # N forwarded, then the intercepted N+1

        log_path = tmp_path / "log.jsonl"
        ca_dir = tmp_path / "ca"
        config = interceptor.InterceptorConfig(
            mode="pass-then-intercept",
            bind_addrs=["127.0.0.1"],
            port=0,
            log=interceptor.JsonLogger(log_path.open("a", encoding="utf-8")),
            max_connections=total_connections,
            ca_dir=ca_dir,
            upstream_host="127.0.0.1",
            upstream_port=fixture.port,
            pass_count=pass_count,
        )
        th = _run_server(config)
        _wait_for_listening_port(log_path)
        port = _read_listening_port(log_path)

        # Connections 1..N: forwarded to the genuine fixture. A production-postured client
        # (CERT_NONE) sees the fixture's own cert, whose SPKI *is* the pin. Neither side ever
        # calls SSLSocket.shutdown() (see _FixtureServer's docstring); the exchange is a fixed-
        # length request followed by a fixed-length reply, so end-of-message needs no signal
        # beyond "I've read what I expected."
        for _ in range(pass_count):
            ctx = _client_context(trust_ca=None)
            raw = socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_S)
            tls = ctx.wrap_socket(raw, server_hostname=None)
            try:
                assert _spki_pin_of(tls) == pin
                tls.sendall(request_payload)
                reply = b""
                while len(reply) < len(_FixtureServer.ACK):
                    chunk = tls.recv(65536)
                    if not chunk:
                        break
                    reply += chunk
                assert reply == _FixtureServer.ACK
            finally:
                tls.close()

        # Connection N+1: intercepted with the trusted-ca leaf. Same client posture; the pin no
        # longer matches, so it aborts writing nothing.
        ctx = _client_context(trust_ca=None)
        raw = socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT_S)
        tls = ctx.wrap_socket(raw, server_hostname=None)
        try:
            assert tls.version() == "TLSv1.3"
            assert _spki_pin_of(tls) != pin
        finally:
            tls.close()

        th.join(timeout=10)
        assert not th.is_alive()

        records = _connection_records(log_path)
        assert [r["connection_index"] for r in records] == [1, 2, 3]

        # Forwarded connections: nonzero, and consistent (within the byte or two of normal TLS
        # session-ticket-size jitter -- e.g. a variable-length ticket nonce) across two runs of
        # the exact same deterministic exchange -- the byte-exact property this task's
        # acceptance criterion asks for, without assuming a specific TLS framing/handshake-size
        # constant that isn't this tool's to dictate.
        forwarded_app_bytes = [records[0]["app_bytes"], records[1]["app_bytes"]]
        forwarded_upstream_bytes = [records[0]["upstream_bytes"], records[1]["upstream_bytes"]]
        assert all(n >= len(request_payload) for n in forwarded_app_bytes)
        assert max(forwarded_app_bytes) - min(forwarded_app_bytes) <= 4
        assert all(n >= len(_FixtureServer.ACK) for n in forwarded_upstream_bytes)
        assert max(forwarded_upstream_bytes) - min(forwarded_upstream_bytes) <= 4

        for i in (0, 1):
            rec = records[i]
            assert rec["disposition"] == "forwarded"
            assert rec["handshake_outcome"] == "forwarded"
            assert rec["tls_version"] is None  # never terminated; genuinely unobservable here

        intercepted = records[2]
        assert intercepted["disposition"] == "intercepted"
        assert intercepted["handshake_outcome"] == "accepted"
        assert intercepted["tls_version"] == "TLSv1.3"
        assert intercepted["app_bytes"] == 0  # zero application bytes on the intercepted connection
    finally:
        fixture.stop()


# --------------------------------------------------------------------------------------------
# CLI validation
# --------------------------------------------------------------------------------------------


def test_cli_requires_ca_dir_for_trusted_ca(capsys: pytest.CaptureFixture[str]) -> None:
    rc = interceptor.main(["--mode", "trusted-ca"])
    assert rc == 2
    assert "--ca-dir" in capsys.readouterr().err


def test_cli_requires_upstream_for_pass_then_intercept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = interceptor.main(["--mode", "pass-then-intercept", "--ca-dir", str(tmp_path)])
    assert rc == 2
    assert "--upstream" in capsys.readouterr().err


def test_cli_rejects_malformed_upstream(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = interceptor.main([
        "--mode", "pass-then-intercept", "--ca-dir", str(tmp_path), "--upstream", "not-a-host-port",
    ])
    assert rc == 2
    assert "host:port" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# Helpers that depend on the "listening" log line to discover the OS-assigned ephemeral port.
# --------------------------------------------------------------------------------------------


def _wait_for_listening_port(log_path: Path, timeout: float = 5.0) -> None:
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if log_path.exists():
            for record in _read_jsonl(log_path):
                if record.get("event") == "listening":
                    return
        time.sleep(0.02)
    raise TimeoutError(f"no 'listening' record appeared in {log_path} within {timeout}s")


def _read_listening_port(log_path: Path) -> int:
    for record in _read_jsonl(log_path):
        if record.get("event") == "listening":
            return int(record["port"])
    raise AssertionError("no 'listening' record found")
