#!/usr/bin/env python3
"""The F1 acceptance interceptor (T065; research R12, CS-1, CS-6; contract TR-1/TR-2).

Stands in for a malicious or wrong network peer during the `HMP_ACCEPTANCE` build's RV-1 matrix
(T079, T083, T084). The acceptance panel drives the *production* pairing/token/API code paths
(CS-1) against this process instead of a real Hermes instance, so the matrix proves the client's
pin check (TR-2) -- not the interceptor's own correctness -- is what stands between the app and a
wrong or hostile peer.

Three modes, selected with `--mode`:

  * `wrong-key`   -- every connection gets a self-signed leaf over a fresh key that is not the
                     pin (TR-1's own certificate shape, wrong key, no CA involved).
  * `trusted-ca`  -- every connection gets a leaf signed by this run's one test CA (T065's
                     `make_test_ca.py`), again over a fresh key that is not the pin. Proves TR-2's
                     pin check is mandatory even when the platform's own chain validation would
                     otherwise succeed.
  * `pass-then-intercept` -- the first `--pass-count` connections (N) are forwarded, byte for
                     byte, as a raw TCP relay to a genuine fixture instance given by `--upstream`
                     (whose `iid` is the pin); connection N+1 onward is intercepted with the
                     `trusted-ca` leaf. This is what proves a *pooled or reconnected* connection
                     is checked too (CS-1), not just the first one of a run.

Every accepted connection is logged as one JSON line: the peer address, the TLS handshake
outcome, the negotiated TLS version (terminated connections only -- a raw relay never decrypts,
so it cannot observe this), whether the client's ClientHello offered session resumption, and the
number of application bytes read from the client. `early_data_bytes` is always logged as `0`: this
process's server-side TLS context never issues a session ticket that enables 0-RTT, so a
compliant client never has anything to attempt it with, and Python's standard-library `ssl`
module has no API to read TLS 1.3 early-data records as a stream distinct from ordinary
post-handshake application data in any case -- there is nothing this tool could accumulate into
that field beyond the fixed zero it already reports.

**Binding.** Every run always binds loopback (`127.0.0.1`, `::1`), plus whatever `--bind`
addresses are passed explicitly on the command line (e.g. the Mac's tailnet address, at physical-
device run time). No address is ever hard-coded here.

**TLS floor.** Every server-side context this module builds sets `minimum_version =
ssl.TLSVersion.TLSv1_3` (contract TR-1: "TLS 1.3 only").

Self-test: `python3 -m pytest tools/acceptance/tests/`.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import selectors
import socket
import ssl
import sys
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import make_test_ca  # noqa: E402 -- must follow the sys.path.insert above (local sibling import)

DEFAULT_LOOPBACK: tuple[str, ...] = ("127.0.0.1", "::1")
DEFAULT_RECV_TIMEOUT_S = 10.0
RECV_BUFSIZE = 65536
LISTEN_BACKLOG = 16

MODES = ("wrong-key", "trusted-ca", "pass-then-intercept")


# --------------------------------------------------------------------------------------------
# Best-effort ClientHello peek (diagnostic only; never gates the connection).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ClientHelloInfo:
    resumption_offered: bool
    session_id_present: bool
    supported_versions: tuple[str, ...]
    parsed: bool  # False if the peeked bytes were not a complete, parseable ClientHello


_UNPARSED = ClientHelloInfo(False, False, (), parsed=False)

_TLS_VERSION_NAMES = {
    (3, 1): "TLSv1.0",
    (3, 2): "TLSv1.1",
    (3, 3): "TLSv1.2",
    (3, 4): "TLSv1.3",
}


def _version_name(major: int, minor: int) -> str:
    return _TLS_VERSION_NAMES.get((major, minor), f"0x{major:02x}{minor:02x}")


def peek_client_hello(sock: socket.socket, *, bufsize: int = 8192) -> ClientHelloInfo:
    """Peek (never consume) the initial bytes on `sock` and try to parse a TLS ClientHello out
    of them, purely to log whether the client offered session resumption before the real
    handshake (via `ssl.SSLContext.wrap_socket`, which reads and consumes the same bytes
    normally) proceeds. Never raises; an unparseable peek just means less detail in the log."""
    try:
        data = sock.recv(bufsize, socket.MSG_PEEK)
    except OSError:
        return _UNPARSED
    return _parse_client_hello(data)


def _parse_client_hello(data: bytes) -> ClientHelloInfo:
    try:
        if len(data) < 5 or data[0] != 0x16:  # TLS record type: handshake
            return _UNPARSED
        record_len = int.from_bytes(data[3:5], "big")
        body = data[5 : 5 + record_len]
        if len(body) < 4 or body[0] != 0x01:  # handshake type: ClientHello
            return _UNPARSED
        hs_len = int.from_bytes(body[1:4], "big")
        ch = body[4 : 4 + hs_len]
        if len(ch) < hs_len:
            return _UNPARSED  # truncated by the peek buffer size; not a parse failure per se

        pos = 2 + 32  # legacy_version, random
        session_id_len = ch[pos]
        pos += 1
        session_id_present = session_id_len > 0
        pos += session_id_len
        cipher_suites_len = int.from_bytes(ch[pos : pos + 2], "big")
        pos += 2 + cipher_suites_len
        compression_len = ch[pos]
        pos += 1 + compression_len
        if pos + 2 > len(ch):
            return ClientHelloInfo(False, session_id_present, (), parsed=True)

        extensions_len = int.from_bytes(ch[pos : pos + 2], "big")
        pos += 2
        extensions_end = min(pos + extensions_len, len(ch))

        resumption_offered = False
        supported_versions: list[str] = []
        while pos + 4 <= extensions_end:
            ext_type = int.from_bytes(ch[pos : pos + 2], "big")
            ext_len = int.from_bytes(ch[pos + 2 : pos + 4], "big")
            ext_data = ch[pos + 4 : pos + 4 + ext_len]
            # pre_shared_key (0x0029, TLS 1.3 PSK/resumption) or a non-empty session_ticket
            # (0x0023, the old-style hint some clients still send alongside it).
            if ext_len > 0 and ext_type in (0x0029, 0x0023):
                resumption_offered = True
            elif ext_type == 0x002B and ext_data:  # supported_versions
                n = ext_data[0]
                versions = ext_data[1 : 1 + n]
                for i in range(0, len(versions) - 1, 2):
                    supported_versions.append(_version_name(versions[i], versions[i + 1]))
            pos += 4 + ext_len

        return ClientHelloInfo(
            resumption_offered, session_id_present, tuple(supported_versions), True
        )
    except (IndexError, ValueError):
        return _UNPARSED


# --------------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------------


class JsonLogger:
    """Thread-safe one-JSON-object-per-line writer. Never buffers a whole run in memory: each
    `log()` call is flushed immediately, so a killed/crashed run still has every connection
    logged up to that point."""

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._lock = threading.Lock()

    def log(self, **fields: Any) -> None:
        record = {"ts": dt.datetime.now(dt.UTC).isoformat()}
        record.update(fields)
        line = json.dumps(record, sort_keys=True, default=str)
        with self._lock:
            self._stream.write(line + "\n")
            self._stream.flush()


def _peer_str(sock: socket.socket) -> str:
    try:
        addr = sock.getpeername()
    except OSError:
        return "unknown"
    host, port = addr[0], addr[1]
    return f"[{host}]:{port}" if ":" in host else f"{host}:{port}"


# --------------------------------------------------------------------------------------------
# Connection counting (global, across every bind address -- "connection N+1" in
# pass-then-intercept counts the whole run, not any one listening socket).
# --------------------------------------------------------------------------------------------


class ConnectionCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._n = 0

    def next(self) -> int:
        with self._lock:
            self._n += 1
            return self._n


# --------------------------------------------------------------------------------------------
# TLS context construction
# --------------------------------------------------------------------------------------------


def build_server_tls_context(cert_path: Path, key_path: Path) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    return ctx


# --------------------------------------------------------------------------------------------
# Per-connection handlers
# --------------------------------------------------------------------------------------------


def _handle_terminate(
    raw_sock: socket.socket,
    *,
    connection_index: int,
    mode: str,
    tls_ctx: ssl.SSLContext,
    logger: JsonLogger,
    recv_timeout_s: float,
) -> None:
    """Terminate TLS ourselves with `tls_ctx`'s leaf. Used by `wrong-key`, `trusted-ca`, and the
    intercepted tail of `pass-then-intercept`. Logs zero `app_bytes` whenever the handshake fails
    outright (no application data can flow before a handshake completes) or whenever the peer
    completes the handshake and then writes nothing before closing -- which is exactly what a
    conforming client does on a pin mismatch (TR-2: the pin is checked "before the first
    application byte is written")."""
    peer = _peer_str(raw_sock)
    hello_info = peek_client_hello(raw_sock)
    tls_version: str | None = None
    session_resumed: bool | None = None
    app_bytes = 0

    try:
        raw_sock.settimeout(recv_timeout_s)
        tls_sock = tls_ctx.wrap_socket(raw_sock, server_side=True)
    except (ssl.SSLError, OSError) as exc:
        logger.log(
            connection_index=connection_index, mode=mode, peer=peer, disposition="intercepted",
            handshake_outcome=f"failed:{type(exc).__name__}:{exc}", tls_version=None,
            resumption_offered=hello_info.resumption_offered,
            client_hello_parsed=hello_info.parsed, session_resumed=None,
            early_data_bytes=0, app_bytes=0,
        )
        with contextlib.suppress(OSError):
            raw_sock.close()
        return

    try:
        tls_version = tls_sock.version()
        session_resumed = bool(tls_sock.session_reused)
        tls_sock.settimeout(recv_timeout_s)
        while True:
            try:
                chunk = tls_sock.recv(RECV_BUFSIZE)
            except (TimeoutError, ssl.SSLError, OSError):
                break
            if not chunk:
                break
            app_bytes += len(chunk)
    finally:
        logger.log(
            connection_index=connection_index, mode=mode, peer=peer, disposition="intercepted",
            handshake_outcome="accepted", tls_version=tls_version,
            resumption_offered=hello_info.resumption_offered,
            client_hello_parsed=hello_info.parsed, session_resumed=session_resumed,
            early_data_bytes=0, app_bytes=app_bytes,
        )
        with contextlib.suppress(OSError):
            tls_sock.close()


def _relay(src: socket.socket, dst: socket.socket, counted: list[int]) -> None:
    try:
        while True:
            chunk = src.recv(RECV_BUFSIZE)
            if not chunk:
                break
            counted[0] += len(chunk)
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            dst.shutdown(socket.SHUT_WR)


def _handle_forward(
    raw_sock: socket.socket,
    *,
    connection_index: int,
    mode: str,
    upstream_host: str,
    upstream_port: int,
    logger: JsonLogger,
    recv_timeout_s: float,
) -> None:
    """Raw byte-for-byte TCP relay to the genuine fixture instance. This process never
    terminates TLS for a forwarded connection, so `tls_version`/`session_resumed` cannot be
    observed here and are logged as `null`; `app_bytes` is the exact count of bytes read from
    the client and relayed upstream (client -> upstream), and `upstream_bytes` the exact count
    of the reply relayed back."""
    peer = _peer_str(raw_sock)
    hello_info = peek_client_hello(raw_sock)
    client_to_upstream = [0]
    upstream_to_client = [0]

    try:
        upstream_sock = socket.create_connection(
            (upstream_host, upstream_port), timeout=recv_timeout_s
        )
    except OSError as exc:
        logger.log(
            connection_index=connection_index, mode=mode, peer=peer, disposition="forwarded",
            handshake_outcome=f"upstream_unreachable:{type(exc).__name__}:{exc}", tls_version=None,
            resumption_offered=hello_info.resumption_offered,
            client_hello_parsed=hello_info.parsed, session_resumed=None,
            early_data_bytes=0, app_bytes=0, upstream_bytes=0,
        )
        with contextlib.suppress(OSError):
            raw_sock.close()
        return

    raw_sock.settimeout(recv_timeout_s)
    upstream_sock.settimeout(recv_timeout_s)

    t_up = threading.Thread(
        target=_relay, args=(raw_sock, upstream_sock, client_to_upstream), daemon=True
    )
    t_down = threading.Thread(
        target=_relay, args=(upstream_sock, raw_sock, upstream_to_client), daemon=True
    )
    t_up.start()
    t_down.start()
    t_up.join()
    t_down.join()

    logger.log(
        connection_index=connection_index, mode=mode, peer=peer, disposition="forwarded",
        handshake_outcome="forwarded", tls_version=None,
        resumption_offered=hello_info.resumption_offered,
        client_hello_parsed=hello_info.parsed, session_resumed=None,
        early_data_bytes=0, app_bytes=client_to_upstream[0], upstream_bytes=upstream_to_client[0],
    )
    for s in (raw_sock, upstream_sock):
        with contextlib.suppress(OSError):
            s.close()


# --------------------------------------------------------------------------------------------
# Bind-address / listener plumbing
# --------------------------------------------------------------------------------------------


def resolve_bind_addresses(explicit: Sequence[str]) -> list[str]:
    """Loopback is always bound and cannot be removed; `explicit` (from `--bind`, e.g. a tailnet
    address at physical-device run time) is appended, de-duplicated, preserving order. No address
    is ever hard-coded beyond the two loopback literals."""
    addrs = list(DEFAULT_LOOPBACK)
    for addr in explicit:
        if addr not in addrs:
            addrs.append(addr)
    return addrs


def _open_listeners(bind_addrs: Sequence[str], port: int) -> tuple[list[socket.socket], int]:
    """Bind every address on the same port. If `port` is 0, the first bind picks an OS-assigned
    ephemeral port, and every subsequent address binds that exact port number (needed so a
    caller can reach any of the bound addresses at one consistent port)."""
    sockets: list[socket.socket] = []
    actual_port = port
    try:
        for addr in bind_addrs:
            family = socket.AF_INET6 if ":" in addr else socket.AF_INET
            s = socket.socket(family, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((addr, actual_port))
            if actual_port == 0:
                actual_port = s.getsockname()[1]
            s.listen(LISTEN_BACKLOG)
            sockets.append(s)
    except OSError:
        for s in sockets:
            s.close()
        raise
    return sockets, actual_port


# --------------------------------------------------------------------------------------------
# Run configuration and main loop
# --------------------------------------------------------------------------------------------


@dataclass
class InterceptorConfig:
    mode: str
    bind_addrs: list[str]
    port: int
    log: JsonLogger
    max_connections: int | None = None
    recv_timeout_s: float = DEFAULT_RECV_TIMEOUT_S
    # trusted-ca / pass-then-intercept (and wrong-key, which uses it to hold its self-signed leaf)
    ca_dir: Path | None = None
    sans: list[str] = field(default_factory=list)
    # pass-then-intercept only
    upstream_host: str | None = None
    upstream_port: int | None = None
    pass_count: int = 1


def run_interceptor(config: InterceptorConfig) -> int:
    if config.mode not in MODES:
        raise ValueError(f"unknown mode: {config.mode!r} (expected one of {MODES})")

    wrongkey_leaf: make_test_ca.TestLeaf | None = None
    ca: make_test_ca.TestCA | None = None
    trusted_leaf: make_test_ca.TestLeaf | None = None
    if config.mode == "wrong-key":
        wrongkey_leaf = make_test_ca.generate_self_signed_leaf(config.ca_dir, sans=config.sans)
    else:
        ca = make_test_ca.load_or_generate_ca(config.ca_dir)
        trusted_leaf = make_test_ca.generate_leaf(ca, config.ca_dir, sans=config.sans)

    sockets, actual_port = _open_listeners(config.bind_addrs, config.port)
    config.log.log(
        event="listening", mode=config.mode, bind_addrs=config.bind_addrs, port=actual_port,
        ca_fingerprint_sha256=(ca.fingerprint_sha256 if ca is not None else None),
    )

    counter = ConnectionCounter()
    threads: list[threading.Thread] = []

    def handle(raw_sock: socket.socket) -> None:
        idx = counter.next()
        if config.mode == "wrong-key":
            assert wrongkey_leaf is not None
            ctx = build_server_tls_context(wrongkey_leaf.cert_path, wrongkey_leaf.key_path)
            _handle_terminate(
                raw_sock, connection_index=idx, mode=config.mode, tls_ctx=ctx,
                logger=config.log, recv_timeout_s=config.recv_timeout_s,
            )
        elif config.mode == "trusted-ca":
            assert trusted_leaf is not None
            ctx = build_server_tls_context(trusted_leaf.cert_path, trusted_leaf.key_path)
            _handle_terminate(
                raw_sock, connection_index=idx, mode=config.mode, tls_ctx=ctx,
                logger=config.log, recv_timeout_s=config.recv_timeout_s,
            )
        else:  # pass-then-intercept
            assert trusted_leaf is not None
            assert config.upstream_host is not None and config.upstream_port is not None
            if idx <= config.pass_count:
                _handle_forward(
                    raw_sock, connection_index=idx, mode=config.mode,
                    upstream_host=config.upstream_host, upstream_port=config.upstream_port,
                    logger=config.log, recv_timeout_s=config.recv_timeout_s,
                )
            else:
                ctx = build_server_tls_context(trusted_leaf.cert_path, trusted_leaf.key_path)
                _handle_terminate(
                    raw_sock, connection_index=idx, mode=config.mode, tls_ctx=ctx,
                    logger=config.log, recv_timeout_s=config.recv_timeout_s,
                )

    sel = selectors.DefaultSelector()
    for s in sockets:
        sel.register(s, selectors.EVENT_READ)

    accepted = 0
    stop = False
    try:
        while not stop:
            for key, _mask in sel.select(timeout=1.0):
                srv_sock: socket.socket = key.fileobj  # type: ignore[assignment]
                try:
                    conn, _addr = srv_sock.accept()
                except OSError:
                    continue
                accepted += 1
                th = threading.Thread(target=handle, args=(conn,), daemon=True)
                th.start()
                threads.append(th)
                if config.max_connections is not None and accepted >= config.max_connections:
                    stop = True
                    break
    finally:
        sel.close()
        for s in sockets:
            with contextlib.suppress(OSError):
                s.close()

    for th in threads:
        th.join(timeout=config.recv_timeout_s * 3)

    return 0


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument(
        "--bind", action="append", default=[],
        help="Additional bind address (e.g. a tailnet address, at physical-device run time). "
             "Repeatable. Loopback (127.0.0.1, ::1) is always bound too and cannot be disabled.",
    )
    parser.add_argument(
        "--port", type=int, default=0, help="TCP port on every bind address (default: OS-assigned)."
    )
    parser.add_argument(
        "--ca-dir", type=Path, default=None,
        help="Scratch directory holding (or to receive) the per-run test CA/leaf material (CS-6). "
             "Required for trusted-ca and pass-then-intercept. For wrong-key it only holds the "
             "self-signed leaf and defaults to a fresh temp directory if omitted.",
    )
    parser.add_argument(
        "--san", action="append", default=[],
        help="Additional SAN entry for generated leaf certificates. Repeatable.",
    )
    parser.add_argument(
        "--upstream", default=None,
        help="host:port of the genuine fixture instance (pass-then-intercept only).",
    )
    parser.add_argument(
        "--pass-count", type=int, default=1,
        help="Number of connections forwarded before interception begins (pass-then-intercept "
             "only; the 'N' in 'connection N+1 onwards is intercepted').",
    )
    parser.add_argument(
        "--max-connections", type=int, default=None,
        help="Stop accepting after this many connections.",
    )
    parser.add_argument(
        "--recv-timeout", type=float, default=DEFAULT_RECV_TIMEOUT_S,
        help="Socket read timeout in seconds.",
    )
    parser.add_argument(
        "--log-file", type=Path, default=None,
        help="Append JSON-lines connection log here instead of stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.mode in ("trusted-ca", "pass-then-intercept") and args.ca_dir is None:
        print(f"--ca-dir is required for mode {args.mode!r}", file=sys.stderr)
        return 2

    upstream_host: str | None = None
    upstream_port: int | None = None
    if args.mode == "pass-then-intercept":
        if not args.upstream:
            print("--upstream host:port is required for pass-then-intercept", file=sys.stderr)
            return 2
        host, sep, port_s = args.upstream.rpartition(":")
        if not sep or not host or not port_s.isdigit():
            print(f"--upstream must be host:port, got {args.upstream!r}", file=sys.stderr)
            return 2
        upstream_host, upstream_port = host, int(port_s)

    ca_dir = args.ca_dir
    if ca_dir is None:
        assert args.mode == "wrong-key"
        ca_dir = Path(tempfile.mkdtemp(prefix="hmp-acceptance-wrongkey-"))

    stream = args.log_file.open("a", encoding="utf-8") if args.log_file else sys.stdout
    logger = JsonLogger(stream)

    config = InterceptorConfig(
        mode=args.mode,
        bind_addrs=resolve_bind_addresses(args.bind),
        port=args.port,
        log=logger,
        max_connections=args.max_connections,
        recv_timeout_s=args.recv_timeout,
        ca_dir=ca_dir,
        sans=args.san,
        upstream_host=upstream_host,
        upstream_port=upstream_port,
        pass_count=args.pass_count,
    )
    try:
        return run_interceptor(config)
    except KeyboardInterrupt:
        return 0
    except make_test_ca.ScratchOnlyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
