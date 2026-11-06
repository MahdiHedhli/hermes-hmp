"""Execute actual owner C transitions against a deterministic model Mach ABI.

This checks causal native-boundary interruptions, not the kernel ABI or a native
handshake. Model ports are integers in the fake header, never operating-system
rights. The production source is included directly, so fixes exercise its code.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]


def test_retained_owner_native_boundary_model(tmp_path):
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("C compiler unavailable; not native qualification")
    fixture = _ROOT / "server/tests/fixtures/admission_native_model"
    binary = tmp_path / "owner-model"
    env = {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"}
    built = subprocess.run(
        [cc, "-std=c11", "-D_POSIX_C_SOURCE=200809L", "-Wall", "-Wextra", "-Werror",
         "-pthread", "-I", str(fixture), "-I", str(_ROOT / "native"),
         str(fixture / "model.c"), "-o", str(binary)],
        env=env, capture_output=True, timeout=30, check=False,
    )
    assert built.returncode == 0, built.stderr.decode(errors="replace")
    result = subprocess.run([str(binary)], env=env, capture_output=True,
                            timeout=5, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout == b"70 causal model scenarios passed; no native Mach calls\n"
