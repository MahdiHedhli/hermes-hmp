"""One owned-label actual-reader crash fixture; never production admission.

Explicit --run-local-fixture only, no existing service or Hermes home. Unknown
child/observer/manager cleanup preserves the durable lock and prohibits reruns.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import plistlib
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_LOCK = Path("/private/tmp/hermes-character-broker-crash-fixture.lock")
_POINTER = Path("/private/tmp/hermes-character-broker-crash-fixture-current.json")


def _load(name: str, filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load("_character_crash_probe", "launchd_reader_containment_probe.py")
observer = _load("_character_crash_observer", "darwin_process_exit_observer.py")


def _require(value: bool, code: str) -> None:
    if value is not True:
        raise probe.ProbeRefusedError(code)


def _prepare(root: Path):
    import yaml  # controller dependency, copied as inert source for the fixed reader

    root.mkdir(mode=0o700)
    plugin, parser = root / "plugin", root / "yaml"
    plugin.mkdir(mode=0o700)
    parser.mkdir(mode=0o700)
    repository = Path(__file__).resolve().parents[2]
    for source, target in ((repository / "server/hmp_plugin", plugin),
                           (Path(yaml.__file__).parent, parser)):
        for path in source.glob("*.py"):
            destination = target / path.name
            shutil.copyfile(path, destination)
            destination.chmod(0o600)
    oracle = root / "oracle.py"
    probe._private_write(oracle, Path(__file__).with_name(
        "presentation_broker_crash_oracle.py").read_bytes(), exclusive=True)
    manifest = root / "manifest.json"
    python = str(Path(sys.executable).resolve(strict=True))
    inventory = repository / "tools/compat/presentation_broker_install_inventory.py"
    result = subprocess.run([python, "-I", "-B", "-S", str(inventory), str(plugin),
                             str(parser), "d" * 64, str(manifest)],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
                            env={"LANG": "C", "LC_ALL": "C"})
    _require(result.returncode == 0, "fixture_inventory_failed")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    bootstrap_digest = hashlib.sha256((plugin / "presentation_broker_bootstrap.py").read_bytes()
                                     ).hexdigest()
    nonce = secrets.token_hex(16)
    label = probe._PREFIX + secrets.token_hex(16)
    argv = ("/usr/bin/env", "-i", "LANG=C", "LC_ALL=C", python, "-I", "-B", "-S",
            str(oracle), str(plugin), str(manifest), digest, bootstrap_digest,
            str(root / "s"), nonce, str(os.getpid()))
    out, err = root / "stdout.log", root / "stderr.log"
    for path in (out, err):
        probe._private_write(path, b"", exclusive=True)
    plist = root / "job.plist"
    policy = {"Label": label, "Program": "/usr/bin/env", "ProgramArguments": list(argv),
              "RunAtLoad": True, "KeepAlive": False, "AbandonProcessGroup": False,
              "ExitTimeOut": 1, "StandardOutPath": str(out), "StandardErrorPath": str(err)}
    probe._private_write(plist, plistlib.dumps(policy), exclusive=True)
    hashes = tuple((str(p), hashlib.sha256(p.read_bytes()).hexdigest())
                   for p in (oracle, manifest, plist))
    return probe.Case(root, label, f"gui/{os.geteuid()}", nonce, "actual", argv, plist, hashes)


def _remaining(end_ns: int) -> float:
    now = time.monotonic_ns()
    _require(type(end_ns) is int and now < end_ns, "fixture_protocol_deadline")
    return (end_ns - now) / 1_000_000_000


def _send(connection: socket.socket, value: bytes, end_ns: int) -> None:
    connection.settimeout(_remaining(end_ns))
    connection.sendall(value)
    _remaining(end_ns)


def _receive_line(connection: socket.socket, end_ns: int, limit: int = 1024) -> bytes:
    value = bytearray()
    while not value.endswith(b"\n"):
        connection.settimeout(_remaining(end_ns))
        part = connection.recv(1)
        _remaining(end_ns)
        _require(bool(part) and len(value) < limit, "fixture_control_frame_refused")
        value.extend(part)
    return bytes(value)


def _hello(raw: bytes, case, broker_pid: int) -> dict:
    def pairs(rows):
        result = {}
        for key, value in rows:
            _require(key not in result, "duplicate_fixture_key")
            result[key] = value
        return result
    row = json.loads(raw, object_pairs_hook=pairs)
    keys = {"kind", "nonce", "pid", "pgid", "child", "child_pgid", "input_sent",
            "go_sent", "child_retained_unreaped"}
    _require(type(row) is dict and row.keys() == keys, "fixture_hello_shape")
    _require(row["kind"] == "actual_reader_broker" and row["nonce"] == case.nonce,
             "fixture_hello_scope")
    _require(all(type(row[k]) is int and row[k] > 1
                 for k in ("pid", "pgid", "child", "child_pgid")), "fixture_hello_numbers")
    _require(row["pid"] == broker_pid and row["child"] != broker_pid
             and row["pgid"] == row["child_pgid"] and row["pgid"] != os.getpgrp()
             and os.getpgid(broker_pid) == row["pgid"]
             and os.getpgid(row["child"]) == row["child_pgid"], "fixture_group_identity")
    _require(row["input_sent"] is False and row["go_sent"] is False
             and row["child_retained_unreaped"] is True, "fixture_reader_contract")
    return row


def _observe(owners: dict, binding: object, record: dict, *, cleanup: bool) -> None:
    for kind, owner in owners.items():
        if record.get(kind + "_kernel_exit_observed_ns") is None:
            fact = owner.poll(binding, cleanup=cleanup)
            if fact is not None:
                record[kind + "_kernel_exit_observed_ns"] = fact.observed_at_ns


def _both_exited(record: dict) -> bool:
    return all(type(record.get(k + "_kernel_exit_observed_ns")) is int
               for k in ("broker", "reader"))


def _run(case, record: dict, receipt: Path, state: dict) -> None:
    owners, binding = {}, object()
    connection = None
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe._verify_case(case)
        pre = probe._query_result(case, probe._command(case, "print"))
        record["preflight"] = pre
        _require(pre["absent"], "new_label_absence_unknown")
        address = str(case.root / "s")
        _require(len(address.encode()) < 104, "fixture_socket_path_too_long")
        listener.bind(address)
        os.chmod(address, 0o600)
        listener.listen(1)
        startup_end = time.monotonic_ns() + 8_000_000_000
        record["startup_end_ns"] = startup_end
        record["submission_attempted"] = True
        probe._save(receipt, state)  # durable intent before the single bootstrap attempt
        result = probe._command(case, "bootstrap")
        record["bootstrap_returncode"] = result.returncode
        _require(result.returncode == 0, "bootstrap_failed_or_ambiguous")
        listener.settimeout(_remaining(startup_end))
        connection, _ = listener.accept()
        _remaining(startup_end)
        peer = probe._kernel_peer(connection)
        query = probe._query_result(case, probe._command(case, "print"))
        record["verified_job"] = query
        _require(query["owned"] and query["pid"] == peer.pid, "broker_job_peer_mismatch")
        probe._verify_case(case)
        _send(connection, b"ARM " + case.nonce.encode("ascii") + b"\n", startup_end)
        hello = _hello(_receive_line(connection, startup_end), case, peer.pid)
        record["identities"] = hello
        _remaining(startup_end)
        now = time.monotonic_ns()
        record["observation_end_ns"] = now + 4_000_000_000
        record["cleanup_end_ns"] = now + 12_000_000_000
        for kind, pid in (("broker", hello["pid"]), ("reader", hello["child"])):
            try:
                owners[kind] = observer.ProcessExitObserver(binding, pid,
                    observe_end_ns=record["observation_end_ns"],
                    cleanup_end_ns=record["cleanup_end_ns"])
            except observer.ObserverAcquisitionError as error:
                owners[kind] = error.failed_owner
                raise
        for owner in owners.values():
            owner.ensure_pending(binding)
        record["crash_requested_ns"] = time.monotonic_ns()
        probe._save(receipt, state)
        _require(time.monotonic_ns() < record["observation_end_ns"], "stimulus_budget_expired")
        _send(connection, b"CRASH " + case.nonce.encode("ascii") + b"\n",
              record["observation_end_ns"])
        record["crash_acknowledged"] = _receive_line(
            connection, record["observation_end_ns"]) == b"CRASH_ACK\n"
        _require(record["crash_acknowledged"], "crash_ack_unknown")
        record["broker_control_eof"] = probe._eof(
            connection, min(1, _remaining(record["observation_end_ns"])))
        _remaining(record["observation_end_ns"])
        while time.monotonic_ns() < record["observation_end_ns"] and not _both_exited(record):
            _observe(owners, binding, record, cleanup=False)
            time.sleep(0.001)
        record["actual_reader_exit_within_window"] = _both_exited(record)
        record["manager_kill_causality_proven"] = False
        record["reader_output_eof"] = None  # read ends belonged to broker; not transferred
    finally:
        # Cleanup planes are independent: a socket/diagnostic/manager error must
        # not prevent another still-authorized local disposal. Errors preserve
        # lock/debt and never become observations of success.
        errors = []
        for kind, local in (("control_socket", connection), ("listener", listener)):
            if local is not None:
                try:
                    local.close()
                except BaseException:
                    errors.append(kind + "_close_unknown")
        if record.get("submission_attempted"):
            try:
                probe._cleanup(case, record, receipt, state)
            except BaseException:
                record["cleanup"] = "unknown"
                errors.append("manager_cleanup_unknown")
            end = record.get("cleanup_end_ns", 0)
            while len(owners) == 2 and time.monotonic_ns() < end and not _both_exited(record):
                try:
                    _observe(owners, binding, record, cleanup=True)
                except BaseException:
                    errors.append("kernel_cleanup_unknown")
                    break
                time.sleep(0.001)
            record["kernel_cleanup_known"] = _both_exited(record)
        else:
            record["cleanup"] = "not_submitted"
            record["kernel_cleanup_known"] = True
        closes = []
        for owner in owners.values():
            try:
                closes.append(owner.close(binding) is True)
            except BaseException:
                closes.append(False)
                errors.append("monitor_close_unknown")
        record["observer_local_close_known"] = all(closes)
        record["cleanup_errors"] = errors
        record["cleanup_known"] = (record["cleanup"] in ("known_absent", "not_submitted")
                                   and record["kernel_cleanup_known"]
                                   and record["observer_local_close_known"] and not errors)
        probe._save(receipt, state)



def main() -> int:
    _require(sys.argv[1:] == ["--run-local-fixture"] and sys.platform == "darwin"
             and os.geteuid() > 0, "explicit_nonroot_darwin_fixture_required")
    fd = os.open(_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    root = Path(tempfile.mkdtemp(prefix="hbr-crash-", dir="/private/tmp"))
    receipt = root / "receipt.json"
    record = {"submission_attempted": False, "cleanup_known": False}
    state = {"scope": "instrumented broker / actual fixed reader / no-input no-GO",
             "production_qualified": False, "record": record, "status": "preparing"}
    probe._save(_POINTER, {"root": str(root), "receipt": str(receipt)})
    probe._save(receipt, state)
    try:
        case = _prepare(root / "a")
        record.update(label=case.label, target=case.target, hashes=dict(case.hashes))
        state["status"] = "active"
        _run(case, record, receipt, state)
        _require(record.get("actual_reader_exit_within_window") is True,
                 "actual_reader_exit_not_observed_within_window")
        state["status"] = "terminal_observed"
    except BaseException as error:
        state["status"] = "terminal_refused"
        state["error"] = (str(error) if type(error) is probe.ProbeRefusedError
                          else type(error).__name__)
    probe._save(receipt, state)
    if state["status"] == "terminal_observed" and record["cleanup_known"]:
        _LOCK.unlink()
    print(json.dumps({"status": state["status"], "receipt": str(receipt),
                      "cleanup_known": record["cleanup_known"], "production_qualified": False}))
    return 0 if state["status"] == "terminal_observed" and record["cleanup_known"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
