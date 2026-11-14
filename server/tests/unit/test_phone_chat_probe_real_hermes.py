"""Evidence-only run of the `phone_chat` probe against one real Hermes tree (spec 034 T11).

Skipped unless `HMP_APPROVAL_PROBE_SRC` (Hermes source) and `HMP_APPROVAL_PROBE_PYTHON` (that
build's interpreter) are set. The probe imports the real helper modules in an isolated home, calls
none of them, applies three mutants in memory only and opens no socket. A pass is sampled evidence
for that exact tree, never a compatibility claim or an allowlist entry; a later build is attempted
whatever this says.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROBE = REPO_ROOT / "tools" / "compat" / "phone_chat_probe.py"
SRC = os.environ.get("HMP_APPROVAL_PROBE_SRC")
PYTHON = os.environ.get("HMP_APPROVAL_PROBE_PYTHON")


@pytest.mark.skipif(
    not (SRC and PYTHON), reason="set HMP_APPROVAL_PROBE_SRC and HMP_APPROVAL_PROBE_PYTHON"
)
def test_real_phone_chat_probe_detects_each_capability_mutant() -> None:
    assert SRC is not None and PYTHON is not None
    proc = subprocess.run(
        [PYTHON, str(PROBE), "--hermes-src", SRC],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["baseline_missing"] == []
    assert report["restored_missing"] == []
    assert report["detected"] == {
        "no_allow_gateway_control": True,
        "resolver_without_request_id": True,
        "resolver_kwargs_only": True,
    }
    assert report["stream_hook"] in (True, False, None)  # a fact, never a requirement
    assert report["ok"] is True
