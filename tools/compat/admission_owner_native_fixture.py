"""Private own-right lifecycle harness; no public CLI or production admission."""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import stat
import sys
from pathlib import Path

_HELPER = Path(__file__).with_name("native_sender_audit_fixture.py")
_SPEC = importlib.util.spec_from_file_location("_hmp_admission_retained_commands", _HELPER)
commands = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = commands
_SPEC.loader.exec_module(commands)
_ROOT = Path(__file__).resolve().parents[2]
_SOURCES = (_ROOT / "native/hmp_admission_owner.c", _ROOT / "native/hmp_admission_owner.h",
            Path(__file__).with_suffix(".c"), Path(__file__).resolve(), _HELPER)
_FIELDS = frozenset(("initialized", "own_rights", "thread_joined", "wrong_thread_refused",
                     "dead_name_observed", "close_known", "idempotent_close", "name_absent",
                     "disposed"))


def validate(raw):
    commands._require(type(raw) is bytes and 0 < len(raw) <= 4096)
    row = json.loads(raw.decode("utf-8"), object_pairs_hook=commands._pairs)
    commands._require(type(row) is dict
                      and set(row) == _FIELDS | {"schema", "production_qualified"})
    commands._require(type(row["schema"]) is int and row["schema"] == 1)
    commands._require(row["production_qualified"] is False)
    commands._require(all(row[k] is True for k in _FIELDS))
    return row


def run_fixture(directory):
    commands._require(sys.platform == "darwin" and os.geteuid() != 0)
    commands._require(type(directory) is type(Path()) and directory.is_absolute())
    commands._require(signal.getsignal(signal.SIGCHLD) is signal.SIG_DFL)
    info = directory.lstat()
    commands._require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                      and stat.S_IMODE(info.st_mode) == 0o700 and not any(directory.iterdir()))
    pins = {str(p): commands._digest(p) for p in _SOURCES}
    receipt = {"schema": 1, "commands": [], "source_hashes": pins,
               "production_qualified": False, "observation": None}
    commands._save(directory / "receipt.json", receipt)
    compiler = commands._selected_path(commands._owned(
        ["/usr/bin/xcrun", "--find", "clang"], directory, "compiler", receipt))
    sdk = commands._selected_path(commands._owned(
        ["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"], directory, "sdk", receipt))
    receipt["compiler_sha256"] = commands._digest(compiler)
    receipt["sdk_headers"] = {p: commands._digest(sdk / "usr/include" / p) for p in (
        "mach/mach.h", "mach/mach_port.h", "mach/port.h", "pthread.h")}
    binary = directory / "native-owner"
    commands._owned([str(compiler), "-std=c11", "-Wall", "-Wextra", "-Werror", "-pthread",
        "-isysroot", str(sdk), "-I", str(_ROOT / "native"), str(Path(__file__).with_suffix(".c")),
        "-o", str(binary)], directory, "build", receipt)
    os.chmod(binary, 0o700)
    receipt["binary_sha256"] = commands._digest(binary)
    raw = commands._owned(["/usr/bin/otool", "-L", str(binary)], directory, "libraries", receipt)
    lines = raw.decode("utf-8").splitlines()
    commands._require(len(lines) == 2 and lines[0] == str(binary) + ":" and
        lines[1].strip().startswith("/usr/lib/libSystem.B.dylib (compatibility version "))
    raw = commands._owned([str(binary)], directory, "native_observation", receipt)
    receipt["observation"] = validate(raw)
    commands._require(all(commands._digest(Path(p)) == value for p, value in pins.items()))
    commands._require(commands._digest(binary) == receipt["binary_sha256"])
    commands._require(commands._digest(compiler) == receipt["compiler_sha256"])
    commands._require(all(commands._digest(sdk / "usr/include" / p) == value
                          for p, value in receipt["sdk_headers"].items()))
    receipt["source_binary_sdk_unchanged"] = True
    commands._save(directory / "receipt.json", receipt)
    return receipt
