"""Real disposable exec through a pinned native command-builder source fixture."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from .test_presentation_gateway_entry import BOOTSTRAP, PACKAGE, SCRIPT

DATA = Path(__file__).with_name("data")
REEXEC = r'''
if mutation == "reexec" and not getattr(sys, "_hermes_relaunched", False):
    import json, os
    from pathlib import Path
    from native_relaunch import relaunch_command
    assert entry._OWNER._activation is None and not entry._OWNER._ready
    Path(sys.argv[2], "before-exec.json").write_text(json.dumps({
        "argv": sys.argv, "original": sys.orig_argv, "pid": os.getpid()}))
    Path(sys.argv[2], "before-exec.json").chmod(0o600)
    command = relaunch_command(Path(sys.executable), Path(sys.argv[2]),
                               sys.argv, sys.orig_argv,
                               getattr(sys.modules["__main__"].__spec__, "name", None))
    assert command[0] == sys.executable and "-B" in command and "-I" in command
    os.execv(command[0], command)
    raise AssertionError("exec unexpectedly returned")
'''
AFTER = r'''
from pathlib import Path
assert getattr(sys, "_hermes_relaunched", False) is True
assert "-c" in sys.orig_argv  # actual reconstructed native invocation
checkpoint = json.loads(Path(root, "before-exec.json").read_text())
assert checkpoint["argv"] == sys.argv and checkpoint["pid"] == entry.os.getpid()
assert checkpoint["original"] != sys.orig_argv  # image invocation changed
assert owner._activation._scope.bootstrap is sys.modules["hermes_bootstrap"]
'''


@pytest.mark.parametrize("kind", ["script", "module"])
def test_native_relaunch_returns_through_original_entry(tmp_path, kind):
    fixture = (DATA / "native_relaunch_ed1afb.py.txt").read_bytes()
    meta = json.loads((DATA / "native_relaunch_ed1afb.json").read_text())
    assert hashlib.sha256(fixture).hexdigest() == meta["fixtureSha256"]
    root = tmp_path / "native"
    (root / "pm").mkdir(parents=True)
    (root / "pm/__init__.py").write_text("")
    (root / "pm/environments.py").write_text("def activate_dependencies():\n    pass\n")
    (root / "native_relaunch.py").write_bytes(fixture)
    bootstrap = BOOTSTRAP.replace("entry.bootstrap_effect_count = 1", REEXEC
                                  + "\nentry.bootstrap_effect_count = 1")
    # The source helper needs mutation before the point at which bootstrap may exec.
    bootstrap = bootstrap.replace("assert entry._OWNER is not None", "mutation = sys.argv[4]\n"
                                  + "assert entry._OWNER is not None")
    (root / "hermes_bootstrap.py").write_text(bootstrap)
    environment = tmp_path / "generation/lib/python3.14/site-packages"
    environment.mkdir(parents=True)
    script = (tmp_path / "entry.py" if kind == "script" else root / "paired_entry.py")
    body = SCRIPT.replace('mutation != "normal"', 'mutation not in ("normal", "reexec")')
    body = body.replace('mutation == "normal"', 'mutation in ("normal", "reexec")')
    script.write_text(body + AFTER)
    arguments = [str(PACKAGE), str(root), str(environment), "reexec"]
    if kind == "script":
        command = [os.sys.executable, "-I", "-B", str(script), *arguments]
    else:
        launcher = ("import sys,runpy; sys.path.insert(0," + repr(str(root)) + "); "
                    "sys.argv=" + repr(["paired_entry", *arguments]) + "; "
                    "runpy.run_module('paired_entry',run_name='__main__',alter_sys=True)")
        command = [os.sys.executable, "-I", "-B", "-c", launcher]
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=20,
        env={"LANG": "C", "LC_ALL": "C"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["case"] == "reexec"
