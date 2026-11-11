"""Admission refusals execute no native imports and create no instance files."""

import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[3] / "tools/compat/approval_test_native_ipc_fixture.py"


@pytest.mark.parametrize(
    "case", ("optimized", "nonisolated", "wrong_home", "nonfresh", "public_root")
)
def test_fixture_admission_fails_before_instance_creation(tmp_path, case):
    root = (tmp_path / "fixture-root").resolve()
    root.mkdir(mode=0o700)
    (root / "tmp").mkdir(mode=0o700)
    for name in ("fixture.py", "controller.json", "child.log"):
        (root / name).write_bytes(b"SYNTHETIC_ADMISSION_WITNESS")
    if case == "nonfresh":
        (root / "unexpected").write_bytes(b"RETAIN_THIS_FILE")
    if case == "public_root":
        root.chmod(0o755)
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root / "user-home"),
        "HERMES_HOME": str(root / ("wrong-home" if case == "wrong_home" else "home")),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    flags = ["-B"] if case == "nonisolated" else ["-I", "-B"]
    if case == "optimized":
        flags.append("-O")
    try:
        result = subprocess.run(
            [
                sys.executable,
                *flags,
                str(FIXTURE),
                str(root),
                str(tmp_path / "export"),
                "12345",
                "matrix",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert (
            "refusing fixture flags or arguments" in result.stderr
            if case in ("optimized", "nonisolated")
            else "refusing nonprivate or nonfresh fixture root/source" in result.stderr
        )
        assert not result.stdout
        assert {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()} == before
        assert not any(
            (root / name).exists() for name in ("home", "user-home", "runtime", "report.json")
        )
    finally:
        root.chmod(0o700)
