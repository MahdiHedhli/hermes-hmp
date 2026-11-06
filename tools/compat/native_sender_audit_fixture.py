"""Build/run the fixed own-task C experiment; never a production issuer.

No automatic retry or deletion after uncertainty. Only new private artifact
directories and exact owned compiler/helper processes are used. Source review
must precede the first native helper execution; syntax checks do not run it.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

_SOURCE = Path(__file__).with_suffix(".c")
_POPEN = subprocess.Popen
_RETAINED = []
_LIMIT = 65536
_BOOLS = frozenset({
    "observed", "receipt_after_sender_exit", "body_pid_ignored", "extended_body_refused",
    "kernel_sender_matches_owned_child", "sender_version_consistent",
    "destination_assigned_by_spawn", "parent_exception_policy_unchanged",
    "parent_before_refs_released", "parent_after_refs_released",
    "spawn_attributes_destroyed", "own_receive_right_released", "own_send_right_released",
    "exact_child_wait_known", "child_exit0_after_local_cleanup", "child_cleanup_report_valid",
    "own_child_policy_known", "signal_permission_retired",
    "child_reported_assignment_cleared", "child_reported_refs_released",
    "child_reported_destination_shape", "cleanup_known", "production_qualified",
    "observation_within_deadline", "cleanup_resources_known", "cleanup_within_deadline",
    "late_cleanup", "settlement_only_used",
    "unexpected_message_received", "unexpected_message_destroy_attempted",
    "receive_copyout_unknown",
})
_FALSES = frozenset({"production_qualified", "late_cleanup", "settlement_only_used",
                    "unexpected_message_received", "unexpected_message_destroy_attempted",
                    "receive_copyout_unknown"})
_FIELDS = _BOOLS | {"schema", "stage", "messages_received", "mach_error", "spawn_error"}


class NativeSenderFixtureError(RuntimeError):
    def __init__(self):
        super().__init__("native_sender_fixture_refused")


def _require(value):
    if value is not True:
        raise NativeSenderFixtureError


def _pairs(items):
    value = {}
    for key, item in items:
        _require(key not in value)
        value[key] = item
    return value


def validate_observation(raw):
    """Closed diagnostic success schema, never an authentication API."""
    _require(type(raw) is bytes and 0 < len(raw) <= _LIMIT)
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, RecursionError, UnicodeDecodeError):
        raise NativeSenderFixtureError from None
    _require(type(value) is dict and value.keys() == _FIELDS)
    _require(all(type(value[key]) is bool for key in _BOOLS))
    _require(all(value[key] is False for key in _FALSES)
             and all(value[key] is True for key in _BOOLS - _FALSES))
    _require(type(value["schema"]) is int and value["schema"] == 2
             and type(value["stage"]) is str and value["stage"] == "observed"
             and type(value["messages_received"]) is int and value["messages_received"] == 2
             and type(value["mach_error"]) is int and value["mach_error"] == 0
             and type(value["spawn_error"]) is int and value["spawn_error"] == 0)
    return value


def _digest(path, limit=512 * 1024 * 1024):
    value, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while part := stream.read(1024 * 1024):
            total += len(part)
            _require(total <= limit)
            value.update(part)
    return value.hexdigest()


def _read(path, limit=_LIMIT):
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
             and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= limit)
    return path.read_bytes()


def _save(path, value):
    temporary = path.with_suffix(".new")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    os.replace(temporary, path)


def _owned(command, directory, role, receipt, *, stdout_limit=_LIMIT):
    _require(type(stdout_limit) is int and _LIMIT <= stdout_limit <= 8 * 1024 * 1024)
    state = {"process": _POPEN.__new__(_POPEN), "command": tuple(command), "wait_known": False}
    _RETAINED.append(state)  # includes partial Popen construction, before effects
    record = {"role": role, "command": list(command), "wait_known": False}
    receipt["commands"].append(record)
    _save(directory / "receipt.json", receipt)
    stdout, stderr = directory / (role + ".stdout"), directory / (role + ".stderr")
    out = os.open(stdout, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        err = os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            _POPEN.__init__(state["process"], command, stdin=subprocess.DEVNULL, stdout=out,
                stderr=err, env={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                close_fds=True)
            # Private diagnostics, never authority to signal a numeric PID.
            record["process_pid"] = state["process"].pid
            # Timeout refuses the experiment permanently. Finalization retains
            # and observes this same helper; it cannot leave a nested child behind.
            code = state["process"].wait(timeout=12)
            state["wait_known"] = record["wait_known"] = True
            record["returncode"] = code
        finally:
            if (getattr(state["process"], "_child_created", False) is True
                    and not state["wait_known"]):
                record["settlement_only_used"] = True
                record["settlement_wait_active"] = True
                while not state["wait_known"]:
                    try:
                        _save(directory / "receipt.json", receipt)
                    except OSError:
                        state["diagnostic_write_failed"] = True  # actual owner still retained
                    try:
                        code = state["process"].wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        continue  # no new process, work, admission or permission
                    except OSError:
                        record["wait_observation_error"] = True
                        time.sleep(0.1)  # retain the owner; never infer terminal from an error
                        continue
                    state["wait_known"] = record["wait_known"] = True
                    record["returncode"] = code
                record["settlement_wait_active"] = False
            os.close(err)
    finally:
        try:
            os.close(out)
            _save(directory / "receipt.json", receipt)
        finally:
            if state["wait_known"]:
                for index, retained in enumerate(_RETAINED):
                    if retained is state:
                        del _RETAINED[index]
                        break
    record["stdout_sha256"], record["stderr_sha256"] = _digest(stdout), _digest(stderr)
    _save(directory / "receipt.json", receipt)
    _require(code == 0 and not record.get("settlement_only_used", False))
    return _read(stdout, stdout_limit)


def _selected_path(raw):
    value = raw.decode("utf-8").strip()
    _require(0 < len(value) < 512 and value.startswith("/")
             and not any(ord(character) < 32 or ord(character) == 127 for character in value))
    return Path(value).resolve(strict=True)


def _libraries(raw, binary):
    """Only the selected OS library identities; not a full loaded-image audit."""
    _require(type(raw) is bytes and 0 < len(raw) <= _LIMIT)
    lines = raw.decode("utf-8").splitlines()
    _require(len(lines) == 3 and lines[0] == str(binary) + ":")
    observed = []
    for line in lines[1:]:
        path, separator, _ = line.strip().partition(" (compatibility version ")
        _require(bool(separator))
        observed.append(path)
    _require(set(observed) == {"/usr/lib/libbsm.0.dylib", "/usr/lib/libSystem.B.dylib"})
    return observed


def run_fixture(directory):
    """One fresh build/run, keeping artifacts even after known success."""
    _require(sys.platform == "darwin" and os.geteuid() != 0
             and type(directory) is type(Path()) and directory.is_absolute())
    _require(signal.getsignal(signal.SIGCHLD) is signal.SIG_DFL)
    info = directory.lstat()
    _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
             and stat.S_IMODE(info.st_mode) == 0o700 and not any(directory.iterdir()))
    receipt = {"schema": 1, "commands": [], "production_qualified": False,
               "source_sha256": _digest(_SOURCE), "observation": None}
    _save(directory / "receipt.json", receipt)
    compiler = _selected_path(_owned(["/usr/bin/xcrun", "--find", "clang"], directory,
                                     "compiler", receipt))
    sdk = _selected_path(_owned(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"],
                               directory, "sdk", receipt))
    receipt["compiler_sha256"] = _digest(compiler)
    receipt["sdk_headers"] = {name: _digest(sdk / "usr/include" / name) for name in (
        "mach/message.h", "mach/task.h", "mach/mach_port.h", "bsm/libbsm.h", "spawn.h",
        "mach/exception_types.h", "mach/thread_status.h")}
    _owned([str(compiler), "--version"], directory, "compiler_version", receipt)
    binary = directory / "native-sender"
    _require(not binary.exists())
    _owned([str(compiler), "-std=c11", "-Wall", "-Wextra", "-Werror", "-isysroot", str(sdk),
            str(_SOURCE), "-lbsm", "-o", str(binary)], directory, "build", receipt)
    os.chmod(binary, 0o700)
    receipt["binary_sha256"] = _digest(binary)
    libraries = _owned(["/usr/bin/otool", "-L", str(binary)], directory,
                       "linked_libraries", receipt)
    receipt["linked_os_libraries"] = _libraries(libraries, binary)
    _require(_digest(_SOURCE) == receipt["source_sha256"])
    raw = _owned([str(binary)], directory, "native_observation", receipt)
    value = validate_observation(raw)
    _require(_digest(binary) == receipt["binary_sha256"]
             and _digest(compiler) == receipt["compiler_sha256"]
             and _digest(_SOURCE) == receipt["source_sha256"]
             and all(_digest(sdk / "usr/include" / name) == digest
                     for name, digest in receipt["sdk_headers"].items()))
    receipt["observation"] = value
    receipt["source_binary_sdk_unchanged"] = True
    _save(directory / "receipt.json", receipt)
    return receipt
