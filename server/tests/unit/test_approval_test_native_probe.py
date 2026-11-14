"""Probe admission refusals only; never import or invoke native Hermes."""

import os
import pwd
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "tools/compat/approval_test_native_probe.py"


def test_os_account_live_source_refused_when_path_home_is_redirected(tmp_path):
    fake_home = tmp_path / "fixture-home"
    fake_home.mkdir(mode=0o700)
    native = Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".hermes/hermes-agent"
    prelude = (
        "import pathlib,runpy,sys; "
        f"pathlib.Path.home=classmethod(lambda cls:pathlib.Path({str(fake_home)!r})); "
        f"sys.argv=[{str(_SCRIPT)!r},'--hermes-src',{str(native)!r},"
        f"'--dependencies-dir',{str(tmp_path)!r}]; "
        f"runpy.run_path({str(_SCRIPT)!r},run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-S", "-c", prelude],
        env={"LANG": "C", "LC_ALL": "C", "HERMES_HOME": str(fake_home)},
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2
    assert b"refusing live source/home" in result.stderr


def test_optimized_probe_cannot_skip_assertions(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-S",
            "-O",
            str(_SCRIPT),
            "--hermes-src",
            str(tmp_path),
            "--dependencies-dir",
            str(tmp_path),
        ],
        env={"LANG": "C", "LC_ALL": "C", "HERMES_HOME": str(tmp_path)},
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2 and b"assertions must be enabled" in result.stderr
