"""Instrumented launchd shared/new-group control, never production admission.

The fixed reader ignores stdin entirely and waits on a controller-owned socket
with its own bounded timeout. One pair of new labels only; uncertainty preserves
lock/debt and stops the next case. No existing service or numeric PID signal.
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path

# Fixed sibling modules only; no plugin initializer or native home is imported.

_SPEC = importlib.util.spec_from_file_location("_manager_actual_fixture",
    Path(__file__).with_name("presentation_broker_crash_fixture.py"))
actual = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = actual
_SPEC.loader.exec_module(actual)
probe, observer = actual.probe, actual.observer
_LOCK = Path("/private/tmp/hermes-character-manager-control.lock")
_POINTER = Path("/private/tmp/hermes-character-manager-control-current.json")


def _eligible(case, broker: dict, reader: dict, query: dict) -> None:
    actual._require(query.get("owned") is True and query.get("pid") == broker["pid"]
                    and broker["child"] == reader["pid"], "manager_job_child_binding")
    group = os.getpgrp()
    actual._require(broker["pgid"] != group and reader["pgid"] != group,
                    "manager_controller_group")
    actual._require((reader["pgid"] == broker["pgid"]) is (case.mode == "shared"),
                    "manager_group_geometry")
    actual._require(reader["deadline_ns"] - time.monotonic_ns() >= 9_000_000_000,
                    "manager_independent_lifetime")


def _interpret(case, record: dict) -> bool:
    actual._require(record["window_end_ns"] < record["reader_deadline_ns"] - 1_000_000_000,
                    "manager_timeout_confounded")
    actual._require(type(record.get("broker_kernel_exit_observed_ns")) is int,
                    "manager_broker_exit_unknown")
    reader_exited = type(record.get("reader_kernel_exit_observed_ns")) is int
    return reader_exited is (case.mode == "shared")


def _run(case, record: dict, receipt: Path, state: dict) -> None:
    peers, rows, owners, binding = {}, {}, {}, object()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe._verify_case(case)
        pre = probe._query_result(case, probe._command(case, "print"))
        actual._require(pre["absent"], "manager_new_label_absence_unknown")
        address = str(case.root / "s")
        actual._require(len(address.encode()) < 104, "manager_socket_path_too_long")
        listener.bind(address)
        os.chmod(address, 0o600)
        listener.listen(2)
        startup_end = time.monotonic_ns() + 8_000_000_000
        record["submission_attempted"] = True
        probe._save(receipt, state)
        result = probe._command(case, "bootstrap")
        record["bootstrap_returncode"] = result.returncode
        actual._require(result.returncode == 0, "manager_bootstrap_ambiguous")
        for _ in range(2):
            listener.settimeout(actual._remaining(startup_end))
            connection, _ = listener.accept()
            # Retain every accepted local descriptor before parsing; even an
            # invalid hello must not skip its local close in finally.
            pending_key = "pending" + str(len(peers))
            peers[pending_key] = connection
            connection.settimeout(actual._remaining(startup_end))
            raw = actual._receive_line(connection, startup_end, limit=512)
            # Validate bounded shape and actual connection kernel credentials.
            row = _hello(raw, connection, case)
            actual._require(row["kind"] not in rows, "manager_duplicate_peer")
            peers[row["kind"]] = peers.pop(pending_key)
            rows[row["kind"]] = row
        query = probe._query_result(case, probe._command(case, "print"))
        _eligible(case, rows["broker"], rows["reader"], query)
        record["verified_job"] = query
        record["identities"] = rows
        record["reader_deadline_ns"] = rows["reader"]["deadline_ns"]
        now = time.monotonic_ns()
        record["observation_end_ns"] = now + 4_000_000_000
        record["cleanup_end_ns"] = now + 18_000_000_000
        for kind in ("broker", "reader"):
            try:
                owners[kind] = observer.ProcessExitObserver(binding, rows[kind]["pid"],
                    observe_end_ns=record["observation_end_ns"],
                    cleanup_end_ns=record["cleanup_end_ns"])
            except observer.ObserverAcquisitionError as error:
                owners[kind] = error.failed_owner
                raise
        for owner in owners.values():
            owner.ensure_pending(binding)
        _eligible(case, rows["broker"], rows["reader"], query)
        record["crash_requested_ns"] = time.monotonic_ns()
        probe._save(receipt, state)
        actual._send(peers["broker"], b"k", record["observation_end_ns"])
        peers["broker"].settimeout(actual._remaining(record["observation_end_ns"]))
        ack = peers["broker"].recv(1)
        actual._remaining(record["observation_end_ns"])
        actual._require(ack == b"k", "manager_crash_ack_unknown")
        record["crash_acknowledged"] = True
        window_end = time.monotonic_ns() + 2_000_000_000
        actual._require(window_end < record["observation_end_ns"], "manager_window_budget")
        while time.monotonic_ns() < window_end:
            actual._observe(owners, binding, record, cleanup=False)
            time.sleep(0.001)
        record["window_end_ns"] = time.monotonic_ns()
        actual._require(record["window_end_ns"] < record["observation_end_ns"],
                        "manager_window_expired")
        # Freeze outcome before any controller stop or close. This is a distinct
        # instrumented control, never an unmodified-reader or exit-status claim.
        record["expected_control_observed"] = _interpret(case, record)
        record["reader_exit_observed_during_window"] = type(record.get(
            "reader_kernel_exit_observed_ns")) is int
        record["reader_control_held_open_through_window"] = True
        record["stdin_is_not_reader_input"] = True
    finally:
        errors = []
        # Only the verified reader's already-owned connection can request its
        # voluntary cleanup. No kqueue fact or PID authorizes a signal.
        if "reader" in rows and "reader" in peers:
            record["reader_stop_attempted_ns"] = time.monotonic_ns()
            try:
                actual._send(peers["reader"], b"x", record.get("cleanup_end_ns", 0))
            except BaseException:
                if type(record.get("reader_kernel_exit_observed_ns")) is not int:
                    errors.append("reader_stop_unknown")
        for local in (*peers.values(), listener):
            try:
                local.close()
            except BaseException:
                errors.append("local_socket_close_unknown")
        if record.get("submission_attempted"):
            try:
                probe._cleanup(case, record, receipt, state)
            except BaseException:
                record["cleanup"] = "unknown"
                errors.append("manager_cleanup_unknown")
            while (len(owners) == 2 and time.monotonic_ns() < record.get("cleanup_end_ns", 0)
                   and not actual._both_exited(record)):
                try:
                    actual._observe(owners, binding, record, cleanup=True)
                except BaseException:
                    errors.append("kernel_cleanup_unknown")
                    break
                time.sleep(0.001)
            record["kernel_cleanup_known"] = actual._both_exited(record)
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
        record["cleanup_errors"] = errors
        record["monitor_cleanup_known"] = all(closes)
        record["cleanup_known"] = (record["cleanup"] in ("known_absent", "not_submitted")
            and record["kernel_cleanup_known"] and all(closes) and not errors)
        probe._save(receipt, state)


def _hello(raw: bytes, connection: socket.socket, case) -> dict:
    def pairs(items):
        row = {}
        for key, value in items:
            actual._require(key not in row, "manager_duplicate_key")
            row[key] = value
        return row
    value = json.loads(raw, object_pairs_hook=pairs)
    actual._require(type(value) is dict, "manager_hello_shape")
    kind = value.get("kind")
    keys = {"kind", "nonce", "pid", "pgid", "deadline_ns" if kind == "reader" else "child"}
    actual._require(kind in ("broker", "reader") and value.keys() == keys
                    and value["nonce"] == case.nonce, "manager_hello_scope")
    actual._require(all(type(value[k]) is int and value[k] > 1
                        for k in keys - {"kind", "nonce"}), "manager_hello_numbers")
    peer = probe._kernel_peer(connection)
    actual._require(peer.pid == value["pid"] and os.getpgid(peer.pid) == value["pgid"],
                    "manager_kernel_peer_mismatch")
    return value


def main() -> int:
    actual._require(sys.argv[1:] == ["--run-local-fixture"] and sys.platform == "darwin"
                    and os.geteuid() > 0, "explicit_nonroot_darwin_fixture_required")
    fd = os.open(_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    root = Path(tempfile.mkdtemp(prefix="hbr-manager-", dir="/private/tmp"))
    receipt = root / "receipt.json"
    state = {"scope": "instrumented independent-socket reader shared/new-group control",
             "production_qualified": False, "cases": [], "status": "preparing"}
    probe._save(_POINTER, {"root": str(root), "receipt": str(receipt)})
    probe._save(receipt, state)
    try:
        for mode in ("new", "shared"):
            case = probe._make_case(root / mode[0], mode)
            record = {"mode": mode, "label": case.label, "target": case.target,
                      "hashes": dict(case.hashes), "cleanup_known": False}
            state["cases"].append(record)
            state["status"] = "active"
            _run(case, record, receipt, state)
            actual._require(record.get("expected_control_observed") is True
                            and record["cleanup_known"] is True, "manager_control_refused")
        state["status"] = "terminal_observed"
    except BaseException as error:
        state["status"] = "terminal_refused"
        state["error"] = (str(error) if type(error) is probe.ProbeRefusedError
                          else type(error).__name__)
    probe._save(receipt, state)
    if state["status"] == "terminal_observed":
        _LOCK.unlink()
    print(json.dumps({"status": state["status"], "receipt": str(receipt),
                      "production_qualified": False}))
    return 0 if state["status"] == "terminal_observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
