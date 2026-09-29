"""The release gate must reject missing evidence even if a model says PASS."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "check_release_review.py"
_SPEC = importlib.util.spec_from_file_location("check_release_review", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

SHA = "a" * 40


def _review(**changes: object) -> str:
    payload = {
        "verdict": "PASS",
        "reviewed_sha": SHA,
        "summary": "No blockers",
        "findings": [],
    }
    payload.update(changes)
    return json.dumps(payload)


def test_exact_commit_pass_with_no_blockers() -> None:
    assert _GATE.validate_review(_review(), SHA) == ("PASS", 0)
    assert _GATE.validate_review(
        _review(
            findings=[
                {
                    "severity": "medium",
                    "file": "server/x.py",
                    "line": 12,
                    "detail": "Risk",
                }
            ]
        ),
        SHA,
    ) == ("PASS", 1)


@pytest.mark.parametrize(
    ("raw", "sha"),
    [
        ("", SHA),
        (_review(), ""),
        (_review(reviewed_sha="b" * 40), SHA),
        (_review(summary=""), SHA),
        (_review(findings="none"), SHA),
        (_review(verdict="OPEN"), SHA),
        (_review(verdict="REJECT"), SHA),
        (
            _review(
                findings=[
                    {
                        "severity": "high",
                        "file": "server/x.py",
                        "line": 12,
                        "detail": "Risk",
                    }
                ]
            ),
            SHA,
        ),
        (
            _review(
                findings=[
                    {
                        "severity": "low",
                        "file": "server/x.py",
                        "line": 0,
                        "detail": "Risk",
                    }
                ]
            ),
            SHA,
        ),
    ],
)
def test_missing_or_blocking_evidence_fails(raw: str, sha: str) -> None:
    with pytest.raises(ValueError):
        _GATE.validate_review(raw, sha)
