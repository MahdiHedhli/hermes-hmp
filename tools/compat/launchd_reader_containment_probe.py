"""One-shot own-label Darwin fixture. Never an HMP/production containment receipt.

Run explicitly with --run-local-fixture after reviewing the containment decision.
No whole-domain operations, PID/group signals from the controller, Hermes home,
provider environment or existing job is touched. Unknown cleanup retains its lock.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.machinery
import json
import os
import plistlib
import re
import secrets
import select
import socket
import subprocess
import sys
import tempfile
import time
import types
from dataclasses import dataclass
from pathlib import Path

_PREFIX = "app.hermesbotmobile.containment."
_LABEL = re.compile(re.escape(_PREFIX) + r"[0-9a-f]{32}\Z")
_LOCK = Path("/private/tmp/hermes-reader-containment-probe.lock")
_POINTER = Path("/private/tmp/hermes-reader-containment-probe-current.json")
_WINDOW = 2.0
_MIN_REMAINING_NS = 9_000_000_000

_READER = r"""import json,os,socket,sys,time
address,nonce=sys.argv[1:]
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.settimeout(12)
s.connect(address)
deadline=time.monotonic_ns()+12_000_000_000
row={"kind":"reader","nonce":nonce,"pid":os.getpid(),"pgid":os.getpgrp(),"deadline_ns":deadline}
s.sendall(json.dumps(row,separators=(",",":")).encode()+b"\n")
try:
    s.recv(1)
finally:
    s.close()
"""

_BROKER = r"""import json,os,signal,socket,subprocess,sys
reader,address,nonce,mode=sys.argv[1:]
if mode not in ("new","shared"): raise SystemExit(2)
s=None
child=None
armed=False
try:
    child=subprocess.Popen([sys.executable,"-I","-B","-S",reader,address,nonce],env={"LANG":"C","LC_ALL":"C"},close_fds=True,start_new_session=mode=="new")
    s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect(address)
    row={"kind":"broker","nonce":nonce,"pid":os.getpid(),"pgid":os.getpgrp(),"child":child.pid}
    s.sendall(json.dumps(row,separators=(",",":")).encode()+b"\n")
    if s.recv(1)==b"k":
        armed=True
        s.sendall(b"k")
        os.kill(os.getpid(),signal.SIGKILL)
        raise RuntimeError("self-kill unexpectedly returned")
finally:
    if s is not None: s.close()
    if not armed and child is not None:
        if child.poll() is None: child.terminate()
        child.wait(timeout=3)
"""


class ProbeRefusedError(RuntimeError):
    pass


def _refuse(code: str) -> None:
    raise ProbeRefusedError(code)


def _private_write(path: Path, body: bytes, *, exclusive: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def _save(path: Path, value: dict) -> None:
    _private_write(path, (json.dumps(value, indent=2) + "\n").encode())


@dataclass(frozen=True)
class Case:
    root: Path
    label: str
    domain: str
    nonce: str
    mode: str
    argv: tuple[str, ...]
    plist: Path
    hashes: tuple[tuple[str, str], ...]

    @property
    def target(self) -> str:
        if (
            self.domain != f"gui/{os.geteuid()}"
            or os.geteuid() <= 0
            or _LABEL.fullmatch(self.label) is None
        ):
            _refuse("invalid_owned_target")
        return self.domain + "/" + self.label


def _make_case(root: Path, mode: str) -> Case:
    if mode not in ("new", "shared"):
        _refuse("invalid_fixture_mode")
    root.mkdir(mode=0o700)
    nonce = secrets.token_hex(16)
    label = _PREFIX + secrets.token_hex(16)
    reader, broker = root / "reader.py", root / "broker.py"
    for path, source in ((reader, _READER), (broker, _BROKER)):
        compile(source, str(path), "exec")  # fixed literal fixtures, never executes them here
        _private_write(path, source.encode(), exclusive=True)
    out, err = root / "stdout.log", root / "stderr.log"
    _private_write(out, b"", exclusive=True)
    _private_write(err, b"", exclusive=True)
    argv = (
        "/usr/bin/env",
        "-i",
        "LANG=C",
        "LC_ALL=C",
        sys.executable,
        "-I",
        "-B",
        "-S",
        str(broker),
        str(reader),
        str(root / "s"),
        nonce,
        mode,
    )
    value = {
        "Label": label,
        "Program": "/usr/bin/env",
        "ProgramArguments": list(argv),
        "RunAtLoad": True,
        "KeepAlive": False,
        "AbandonProcessGroup": False,
        "ExitTimeOut": 1,
        "StandardOutPath": str(out),
        "StandardErrorPath": str(err),
    }
    plist = root / "job.plist"
    _private_write(plist, plistlib.dumps(value), exclusive=True)
    hashes = tuple(
        (str(path), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in (reader, broker, plist)
    )
    return Case(root, label, f"gui/{os.geteuid()}", nonce, mode, argv, plist, hashes)


def _verify_case(case: Case) -> None:
    _ = case.target
    if case.root.resolve(strict=True) != case.root or case.root.stat().st_uid != os.geteuid():
        _refuse("fixture_root_changed")
    if case.root.stat().st_mode & 0o777 != 0o700:
        _refuse("fixture_root_mode")
    for name, digest in case.hashes:
        path = Path(name)
        if (
            path.parent != case.root
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_uid != os.geteuid()
            or path.stat().st_mode & 0o777 != 0o600
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            _refuse("fixture_input_changed")
    value = plistlib.loads(case.plist.read_bytes())
    if (
        value["Label"] != case.label
        or value["ProgramArguments"] != list(case.argv)
        or value["RunAtLoad"] is not True
        or value["KeepAlive"] is not False
        or value["AbandonProcessGroup"] is not False
    ):
        _refuse("fixture_job_policy_changed")


def _command(case: Case, verb: str) -> subprocess.CompletedProcess:
    if verb not in ("print", "bootstrap", "bootout"):
        _refuse("command_not_allowlisted")
    target = case.target
    args = ["/bin/launchctl", verb]
    args += [case.domain, str(case.plist)] if verb == "bootstrap" else [target]
    return subprocess.run(
        args,
        capture_output=True,
        timeout=5,
        check=False,
        stdin=subprocess.DEVNULL,
        env={"LANG": "C", "LC_ALL": "C"},
    )


def _query_result(case: Case, result: subprocess.CompletedProcess) -> dict:
    # Never persist/print raw output: launchctl can show inherited environment.
    if len(result.stdout) > 131072 or len(result.stderr) > 16384:
        _refuse("job_query_too_large")
    err = result.stderr.decode("utf-8", "replace")
    absent = result.returncode != 0 and "Could not find service" in err and case.label in err
    if absent:
        return {"absent": True, "owned": False, "returncode": result.returncode}
    if result.returncode != 0:
        return {"absent": False, "owned": False, "returncode": result.returncode}
    text = result.stdout.decode("utf-8", "strict")
    lines = text.splitlines()
    args: list[str] = []
    for index, line in enumerate(lines):
        if line == "\targuments = {":
            for item in lines[index + 1 :]:
                if item == "\t}":
                    break
                if not item.startswith("\t\t"):
                    _refuse("job_arguments_unknown")
                args.append(item[2:])
            break
    pid = re.findall(r"^\tpid = ([1-9][0-9]*)$", text, re.MULTILINE)
    code = re.findall(r"^\tlast exit code = (-?[0-9]+)$", text, re.MULTILINE)
    owned = "\tprogram = /usr/bin/env" in lines and tuple(args) == case.argv
    return {
        "absent": False,
        "owned": owned,
        "returncode": result.returncode,
        "pid": int(pid[0]) if len(pid) == 1 else None,
        "reported_last_exit_code": int(code[0]) if len(code) == 1 else None,
    }


def _kernel_peer(sock: socket.socket):
    # Own-source namespace only; never import plugin initializer/Hermes/providers.
    name = "_hmp_containment_probe"
    if name not in sys.modules:
        root = str(Path(__file__).resolve().parents[2] / "server" / "hmp_plugin")
        package = types.ModuleType(name)
        package.__package__, package.__path__ = name, [root]
        package.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
        package.__spec__.submodule_search_locations = [root]
        sys.modules[name] = package
    from _hmp_containment_probe.presentation_broker_peer import observe_peer

    return observe_peer(sock, expected_uid=os.geteuid())


def _hello(sock: socket.socket, case: Case) -> dict:
    sock.settimeout(3)
    data = bytearray()
    while not data.endswith(b"\n"):
        chunk = sock.recv(1)
        if not chunk or len(data) >= 512:
            _refuse("fixture_hello_refused")
        data.extend(chunk)
    value = json.loads(bytes(data))
    if type(value) is not dict or value.get("nonce") != case.nonce:
        _refuse("fixture_nonce_mismatch")
    kind = value.get("kind")
    keys = {"kind", "nonce", "pid", "pgid", "deadline_ns" if kind == "reader" else "child"}
    if kind not in ("broker", "reader") or value.keys() != keys:
        _refuse("fixture_hello_shape")
    if any(type(value[k]) is not int or value[k] <= 0 for k in keys - {"kind", "nonce"}):
        _refuse("fixture_hello_numbers")
    observed = _kernel_peer(sock)
    if observed.pid != value["pid"] or os.getpgid(observed.pid) != value["pgid"]:
        _refuse("fixture_kernel_identity_mismatch")
    return value


def _eof(sock: socket.socket, seconds: float) -> bool:
    if not select.select([sock], [], [], seconds)[0]:
        return False
    if sock.recv(1) != b"":
        _refuse("unexpected_fixture_bytes")
    return True


def _stop_reader(connection: socket.socket, record: dict) -> None:
    record["explicit_reader_stop_ns"] = time.monotonic_ns()
    with contextlib.suppress(OSError):
        connection.sendall(b"x")
    try:
        closed = _eof(connection, 2)
        record["reader_communication_cleanup"] = "eof" if closed else "unknown"
    except (OSError, ProbeRefusedError):
        record["reader_communication_cleanup"] = "unknown"
    record["reader_cleanup_observed_ns"] = time.monotonic_ns()


def _cleanup(case: Case, record: dict, receipt: Path, state: dict) -> None:
    if not record.get("submission_attempted"):
        record["cleanup"] = "not_submitted"
        _save(receipt, state)
        return
    record["cleanup"] = "unknown"
    _save(receipt, state)
    _verify_case(case)
    query = _query_result(case, _command(case, "print"))
    record["cleanup_query"] = query
    if query["absent"]:
        record["cleanup"] = "known_absent"
    elif query["owned"]:
        record["bootout_attempted"] = True
        _save(receipt, state)
        record["bootout_returncode"] = _command(case, "bootout").returncode
        post = _query_result(case, _command(case, "print"))
        record["cleanup_post"] = post
        record["cleanup"] = "known_absent" if post["absent"] else "unknown"
    else:
        record["cleanup"] = "unknown_ownership"
    _save(receipt, state)


def _case(case: Case, record: dict, receipt: Path, state: dict) -> None:
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    peers: dict[str, socket.socket] = {}
    submitted = False
    try:
        _verify_case(case)
        pre = _query_result(case, _command(case, "print"))
        record["preflight"] = pre
        if not pre["absent"]:
            _refuse("fresh_label_not_known_absent")
        address = str(case.root / "s")
        if len(address.encode()) >= 104:
            _refuse("fixture_socket_path_too_long")
        listener.bind(address)
        listener.listen(2)
        listener.settimeout(5)
        record["reader_communication_cleanup"] = "unknown"
        record["cleanup"] = "pending"
        record["submission_attempted"] = True
        _save(receipt, state)  # durable intent before the only bootstrap attempt
        submitted = True
        result = _command(case, "bootstrap")
        record["bootstrap_returncode"] = result.returncode
        _save(receipt, state)
        if result.returncode != 0:
            _refuse("bootstrap_failed_or_ambiguous")
        rows = {}
        for _ in range(2):
            connection, _ = listener.accept()
            try:
                row = _hello(connection, case)
                if row["kind"] in rows:
                    _refuse("duplicate_fixture_peer")
                peers[row["kind"]], rows[row["kind"]] = connection, row
            except BaseException:
                connection.close()
                raise
        query = _query_result(case, _command(case, "print"))
        record["job_verified_query"] = query
        broker, reader = rows["broker"], rows["reader"]
        if not query["owned"] or query["pid"] != broker["pid"] or broker["child"] != reader["pid"]:
            _refuse("job_or_child_identity_refused")
        controller_group = os.getpgrp()
        if (
            broker["pgid"] == controller_group
            or reader["pgid"] == controller_group
            or (case.mode == "shared" and reader["pgid"] != broker["pgid"])
            or (case.mode == "new" and reader["pgid"] == broker["pgid"])
        ):
            _refuse("fixture_group_layout_refused")
        record["identities"] = rows
        record["groups_independent_of_controller"] = True
        record["remaining_ns_before_stimulus"] = reader["deadline_ns"] - time.monotonic_ns()
        if record["remaining_ns_before_stimulus"] < _MIN_REMAINING_NS:
            _refuse("insufficient_independent_reader_lifetime")
        record["crash_requested_ns"] = time.monotonic_ns()
        _save(receipt, state)
        if reader["deadline_ns"] - time.monotonic_ns() < _MIN_REMAINING_NS:
            _refuse("reader_lifetime_consumed_before_stimulus")
        peers["broker"].settimeout(0.5)
        peers["broker"].sendall(b"k")
        peers["broker"].settimeout(2)
        record["crash_stimulus_ack"] = peers["broker"].recv(1) == b"k"
        record["crash_ack_ns"] = time.monotonic_ns()
        if not record["crash_stimulus_ack"]:
            _refuse("crash_not_acknowledged")
        record["broker_socket_eof"] = _eof(peers["broker"], 2)
        record["broker_eof_observed_ns"] = time.monotonic_ns()
        if not record["broker_socket_eof"]:
            _refuse("broker_communication_still_open")
        record["reader_window_start_ns"] = time.monotonic_ns()
        record["reader_socket_eof_within_window"] = _eof(peers["reader"], _WINDOW)
        record["reader_window_end_ns"] = time.monotonic_ns()
        if record["reader_window_end_ns"] >= reader["deadline_ns"] - 1_000_000_000:
            _refuse("reader_deadline_confounds_observation")
        record["expected_observation"] = record["reader_socket_eof_within_window"] is (
            case.mode == "shared"
        )
        record["observation_scope"] = (
            "communication EOF timing only; not permanent process/group closure"
        )
        _save(receipt, state)
    finally:
        # Stop/close only previously verified synthetic peer connections. Never signal their PIDs.
        for kind, connection in peers.items():
            if kind == "reader":
                _stop_reader(connection, record)
            else:
                with contextlib.suppress(OSError):
                    connection.sendall(b"x")
            connection.close()
        listener.close()
        if submitted:
            _cleanup(case, record, receipt, state)


def main() -> int:
    if sys.argv[1:] != ["--run-local-fixture"] or sys.platform != "darwin" or os.geteuid() <= 0:
        _refuse("explicit_nonroot_darwin_fixture_required")
    fd = os.open(_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    root = Path(tempfile.mkdtemp(prefix="hbr-launchd-", dir="/private/tmp"))
    receipt = root / "receipt.json"
    state = {
        "scope": "temporary synthetic launchd fixture only",
        "status": "preparing",
        "root": str(root),
        "receipt": str(receipt),
        "controller_pid": os.getpid(),
        "cases": [],
    }
    _save(_POINTER, {"root": str(root), "receipt": str(receipt)})
    _save(receipt, state)
    error = None
    try:
        for mode in ("new", "shared"):
            case = _make_case(root / mode[0], mode)
            record = {
                "mode": mode,
                "label": case.label,
                "target": case.target,
                "plist": str(case.plist),
                "hashes": dict(case.hashes),
                "cleanup": "not_submitted",
            }
            state["cases"].append(record)
            state["status"] = "fixture_active"
            _save(receipt, state)
            _case(case, record, receipt, state)
            if (
                not record.get("expected_observation")
                or record["cleanup"] != "known_absent"
                or record.get("reader_communication_cleanup") != "eof"
            ):
                _refuse("unexpected_observation_or_cleanup")
    except BaseException as failure:
        error = failure.args[0] if type(failure) is ProbeRefusedError else type(failure).__name__
    jobs_clean = all(c["cleanup"] in ("not_submitted", "known_absent") for c in state["cases"])
    communication_clean = all(
        not c.get("submission_attempted") or c.get("reader_communication_cleanup") == "eof"
        for c in state["cases"]
    )
    clean = jobs_clean and communication_clean
    if not clean and error is None:
        error = "cleanup_not_known"
    state["status"] = "terminal_observed" if error is None else "terminal_refused"
    state["error"] = error
    state["all_own_jobs_removed_or_not_submitted"] = jobs_clean
    state["verified_reader_communication_cleanup"] = communication_clean
    state["production_containment_certified"] = False
    _save(receipt, state)
    if clean:
        _LOCK.unlink()
    print(
        json.dumps(
            {
                "status": state["status"],
                "receipt": str(receipt),
                "cleanup_known": clean,
                "production_containment_certified": False,
            }
        )
    )
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
