"""Actual owned descriptors over private synthetic files; no installed artifacts/keys."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from .test_presentation_gateway_activation import MODULE, SCRIPT

ARTIFACT_MODULE = MODULE.with_name("presentation_startup_artifacts.py")
PREFIX = SCRIPT[:SCRIPT.rfind("print(json.dumps")]
SUFFIX = r'''
import hashlib, os, stat
from pathlib import Path
mutation = sys.argv[3]
fixture = Path(sys.argv[5])
payload = b"SYNTHETIC_CODE_ONLY\n"
leaf = fixture / "code.py"
leaf.write_bytes(payload)
leaf.chmod(0o600)
package = ModuleType("synthetic_startup")
package.__path__ = []
sys.modules[package.__name__] = package
sys.modules[package.__name__ + ".presentation_gateway_activation"] = m
artifact_spec = importlib.util.spec_from_file_location(
    package.__name__ + ".presentation_startup_artifacts", sys.argv[4])
a = importlib.util.module_from_spec(artifact_spec)
sys.modules[artifact_spec.name] = a
artifact_spec.loader.exec_module(a)
expected = (a.ExpectedArtifact(str(leaf), len(payload), hashlib.sha256(payload).hexdigest()),)
if mutation == "digest": expected = (expected[0]._replace(sha256="0" * 64),)
if mutation == "size": expected = (expected[0]._replace(size=True),)
if mutation == "duplicate": expected = expected + expected
if mutation == "path": expected = (expected[0]._replace(path=str(fixture) + "/./code.py"),)
if mutation == "symlink":
    target = fixture / "other.py"
    leaf.rename(target)
    leaf.symlink_to(target)
if mutation == "hardlink": os.link(leaf, fixture / "linked.py")
if mutation == "mode": leaf.chmod(0o666)
if mutation == "parent_mode": fixture.chmod(0o777)
if mutation == "ancestor_symlink":
    real = fixture / "real"
    real.mkdir(mode=0o700)
    moved = real / "code.py"
    leaf.rename(moved)
    link = fixture / "alias"
    link.symlink_to(real, target_is_directory=True)
    expected = (expected[0]._replace(path=str(link / "code.py")),)
if mutation == "empty":
    leaf.write_bytes(b"")
    expected = (expected[0]._replace(size=0, sha256=hashlib.sha256(b"").hexdigest()),)
if mutation == "multiple":
    second = fixture / "second.py"
    second.write_bytes(payload)
    second.chmod(0o600)
    expected += (expected[0]._replace(path=str(second)),)
close_calls = []
actual_close = a.os.close
actual_read = a.os.read
actual_open = a.os.open
opened = []
if mutation == "open_retired":
    def retire_after_open(name, flags, *, dir_fd=None):
        fd = actual_open(name, flags, dir_fd=dir_fd)
        opened.append(fd)
        if len(opened) == 2: owner.retire()
        return fd
    def counted_close(fd):
        close_calls.append(fd)
        actual_close(fd)
    a.os.open = retire_after_open
    a.os.close = counted_close
if mutation == "close_unknown":
    def uncertain_close(fd):
        close_calls.append(fd)
        actual_close(fd)
        if len(close_calls) == 1: raise OSError("synthetic lost close acknowledgement")
    a.os.close = uncertain_close
if mutation in ("read_unknown", "retired_after_read", "file_changed", "scope_after_read"):
    def changed_read(fd, count):
        result = actual_read(fd, count)
        if mutation == "read_unknown": raise OSError("synthetic lost read acknowledgement")
        if mutation == "retired_after_read": owner.retire()
        if mutation == "scope_after_read" and result:
            active = owner._artifact_owner
            active._scope = active._origin = active._origin._replace(expected=())
            active._cell = (active, active._origin)
        if mutation == "file_changed" and result:
            leaf.write_bytes(b"CHANGED_SYNTHETIC_CODE\n")
        return result
    a.os.read = changed_read
success = mutation in ("normal", "empty", "multiple")
if success:
    observed = a.StartupArtifactOwner.observe(owner, expected)
    assert observed._ready and not observed._failed and not observed._unknown
    assert observed._facts == expected
    assert observed._bytes_read == sum(row.size for row in expected)
    assert all(row.closed and row.close_attempted for row in observed._origin.records)
else:
    try:
        a.StartupArtifactOwner.observe(owner, expected)
    except a.ArtifactObservationError as error:
        observed = error.failed_owner
        assert str(error) == "BI1_STARTUP_ARTIFACTS_REFUSED"
        assert observed is owner._artifact_owner and observed._failed and not observed._ready
        assert observed._facts is None
    else: raise AssertionError("artifact mutation accepted")
    if mutation in ("close_unknown", "read_unknown", "retired_after_read", "scope_after_read",
                    "open_retired"):
        assert observed._unknown
    if mutation == "retired_after_read": assert observed._bytes_read == len(payload)
    assert all(row.closed or row.unknown for row in observed._origin.records)
    assert len(close_calls) == len(set(close_calls))
    if mutation == "open_retired":
        assert len(opened) == 2 and set(opened) == set(close_calls)
        assert all(row.closed and row.close_attempted for row in observed._origin.records)
try: a.StartupArtifactOwner.observe(owner, expected)
except Exception: pass
else: raise AssertionError("second artifact owner accepted")
assert "/" not in repr(observed).split("<", 1)[-1]
print(json.dumps({"mutation": mutation, "passed": True, "runtime_admitted": False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "empty", "multiple", "digest", "size", "duplicate", "path", "symlink",
    "hardlink", "mode", "parent_mode", "ancestor_symlink", "close_unknown", "read_unknown",
    "retired_after_read", "file_changed", "scope_after_read", "open_retired",
])
def test_owned_selected_artifact_observation(tmp_path, mutation):
    if os.name != "posix":
        pytest.skip("supported POSIX descriptors only")
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PREFIX + SUFFIX, str(MODULE), "normal", mutation,
         str(ARTIFACT_MODULE), str(tmp_path.resolve())],
        cwd=tmp_path, env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True,
        timeout=10, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "mutation": mutation, "passed": True, "runtime_admitted": False,
    }
