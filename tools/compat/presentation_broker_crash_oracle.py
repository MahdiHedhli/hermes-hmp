"""Private instrumented broker for the actual-reader crash fixture only.

No host, native profile/input, GO or production service entry. The controller
inventories this exact file and supplies a separately expected installation hash.
After any retained owner exists, refusal retains it until external supervision.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path

_RETAINED: list[object] = []


def _require(value: bool) -> None:
    if value is not True:
        raise RuntimeError("fixture_oracle_refused")


def _remaining(end_ns: int) -> float:
    now = time.monotonic_ns()
    _require(type(end_ns) is int and now < end_ns)
    return (end_ns - now) / 1_000_000_000


def _send(connection: socket.socket, value: bytes, end_ns: int) -> None:
    connection.settimeout(_remaining(end_ns))
    connection.sendall(value)
    _remaining(end_ns)


def _receive_exact(connection: socket.socket, expected: bytes, end_ns: int) -> None:
    value = bytearray()
    while len(value) < len(expected):
        connection.settimeout(_remaining(end_ns))
        part = connection.recv(len(expected) - len(value))
        _remaining(end_ns)
        _require(bool(part))
        value.extend(part)
    _require(bytes(value) == expected)


def run(arguments: list[str]) -> None:
    _require(len(arguments) == 7)
    plugin, manifest, digest, bootstrap_digest, address, nonce, controller = arguments
    origin = time.monotonic_ns()
    startup_end, crash_end = origin + 8_000_000_000, origin + 18_000_000_000
    _require(len(nonce) == 32 and all(c in "0123456789abcdef" for c in nonce))
    _require(controller.isascii() and controller.isdecimal() and int(controller) > 1)
    # The verifier/interpreter origin is an explicitly trusted fixture input.
    bootstrap = Path(plugin) / "presentation_broker_bootstrap.py"
    _require(hashlib.sha256(bootstrap.read_bytes()).hexdigest() == bootstrap_digest)
    spec = importlib.util.spec_from_file_location("_fixture_verified_bootstrap", bootstrap)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    raw = Path(manifest).read_bytes()
    installation = module.VerifiedInstall(raw, digest)
    installation.current()
    module._namespace(plugin)
    from _hmp_presentation_broker.presentation_broker_codec import BrokerBinding
    from _hmp_presentation_broker.presentation_broker_lifecycle import operation_id
    from _hmp_presentation_broker.presentation_broker_peer import observe_peer
    from _hmp_presentation_broker.presentation_broker_registry import BrokerRegistry

    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    _RETAINED.append(connection)
    connection.settimeout(_remaining(startup_end))
    connection.connect(address)
    _remaining(startup_end)
    peer = observe_peer(connection, expected_uid=os.geteuid())
    _require(peer.pid == int(controller))
    # Authenticate controller before constructing any child; no ambient token.
    _receive_exact(connection, b"ARM " + nonce.encode("ascii") + b"\n", startup_end)
    scope = BrokerBinding("a" * 52, "b" * 32, os.urandom(32).hex(), "c" * 64, operation_id(1))
    registry = BrokerRegistry.__new__(BrokerRegistry)
    _RETAINED.append(registry)
    registry.__init__(scope, parser_package=installation._selection_snapshot[1])
    installation.current()
    deadline = time.monotonic_ns() + 1_900_000_000
    ticket = registry.reserve(scope, "default", "METADATA", deadline)
    installation.fence(deadline)
    registry.start_resources(ticket)
    # Instrumentation is read-only after the real start_resources call. No
    # replacement launch/reader, input, GO, wait, signal or resource abort.
    record = registry._record(ticket)
    owner = record.owner
    _require(owner._constructor_returned is True and owner._child is owner._child_snapshot)
    _require(owner._child.returncode is None and type(owner._pid_snapshot) is int)
    child = owner._pid_snapshot
    _require(owner._child.pid == child and owner._launch.start_new_session is False)
    _require(os.getpgid(child) == os.getpgrp() and child != os.getpid())
    report = {"kind": "actual_reader_broker", "nonce": nonce, "pid": os.getpid(),
              "pgid": os.getpgrp(), "child": child, "child_pgid": os.getpgid(child),
              "input_sent": False, "go_sent": False, "child_retained_unreaped": True}
    _send(connection, json.dumps(report, separators=(",", ":")).encode("ascii") + b"\n",
          startup_end)
    # Original work deadline is never renewed. This pause grants no work rights;
    # it only retains the child while the controller registers kernel observers.
    _receive_exact(connection, b"CRASH " + nonce.encode("ascii") + b"\n", crash_end)
    _send(connection, b"CRASH_ACK\n", crash_end)
    os.kill(os.getpid(), signal.SIGKILL)  # this synthetic broker only
    raise RuntimeError("self_kill_returned")


def main() -> int:
    try:
        run(sys.argv[1:])
    except BaseException:
        # No exception detail, environment, profile or manifest contents in logs.
        try:
            sys.stderr.write("CHARACTER_CRASH_ORACLE_REFUSED\n")
            sys.stderr.flush()
        except BaseException:
            if not _RETAINED:
                return 1  # otherwise diagnostics cannot drop a retained owner
        if not _RETAINED:
            return 1
    while True:
        time.sleep(1)  # external own-label supervisor retains/cleans unknown debt


if __name__ == "__main__":
    raise SystemExit(main())
