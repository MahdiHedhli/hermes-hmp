"""Evidence-only run of the session-chat approval probe against one real Hermes checkout.

Skipped unless `HMP_APPROVAL_PROBE_SRC` (Hermes source) and `HMP_APPROVAL_PROBE_PYTHON` (that
build's interpreter) are set; `HMP_APPROVAL_PROBE_AIOHTTP` may name a scratch aiohttp overlay when
the interpreter lacks the messaging extra. The probe opens no socket, runs no command, and uses a
disposable HERMES_HOME. A pass is evidence for that exact source only, never a compatibility
claim or an allowlist entry.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROBE = REPO_ROOT / "tools" / "compat" / "session_chat_approval_probe.py"
SRC = os.environ.get("HMP_APPROVAL_PROBE_SRC")
PYTHON = os.environ.get("HMP_APPROVAL_PROBE_PYTHON")
OVERLAY = os.environ.get("HMP_APPROVAL_PROBE_AIOHTTP")

# Every property the probe must positively report; an empty or shrunken result is a failure.
REQUIRED = {
    "request.emitted_once",
    "request.request_id_nonempty",
    "request.run_id_nonempty",
    "request.choices_offer_once_and_deny",
    "request.model_blocked_not_executed",
    "wrong_request_id.rejected",
    "wrong_run_id.rejected",
    "wrong_key.rejected",
    "wrong_profile.rejected_no_profile_key",
    "wrong_profile.rejected_by_run_ownership",
    "wrong_answers.left_pending",
    "deny.accepted_exact_id",
    "deny.guard_not_approved",
    "deny.no_execution",
    "deny.no_leaked_state",
    "replay.rejected",
    "once.accepted_exact_id",
    "once.guard_approved_fake_executor_only",
    "disconnect.handler_returned",
    "disconnect.agent_interrupted",
    "disconnect.guard_not_approved",
    "disconnect.no_execution",
    "disconnect.no_leaked_state",
    "disconnect.late_answer_rejected",
    "guard.synthetic_command_is_dangerous",
    "request.status_waiting",
    "request.pending_exactly_one",
    "request.status_carries_same_id",
    "invalid_choice.rejected",
    "deny.stream_terminal",
    "once.no_leaked_state",
    "disconnect.turn_finished",
}


@pytest.mark.skipif(
    not (SRC and PYTHON), reason="set HMP_APPROVAL_PROBE_SRC and HMP_APPROVAL_PROBE_PYTHON"
)
def test_real_session_chat_approval_probe() -> None:
    assert SRC is not None and PYTHON is not None
    args = [PYTHON, str(PROBE), "--hermes-src", SRC]
    if OVERLAY:
        args += ["--aiohttp-overlay", OVERLAY]
    proc = subprocess.run(
        args, capture_output=True, text=True, check=False, cwd=REPO_ROOT, timeout=300
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    report = json.loads(proc.stdout)
    failed = sorted(name for name, ok in report["checks"].items() if not ok)
    assert not failed, failed
    assert report["duplicates"] == []
    assert len(REQUIRED) == 32
    assert set(report["checks"]) >= REQUIRED, sorted(REQUIRED - set(report["checks"]))
    assert report["ok"] is True
