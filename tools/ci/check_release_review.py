"""Fail closed on an incomplete or non-passing exact-commit release source review.

The review JSON comes from the read-only Codex action. Never print finding details:
they can quote source material that should not be copied into public CI logs.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping

SEVERITIES = frozenset({"blocker", "high", "medium", "low"})


def validate_review(raw: str, expected_sha: str) -> tuple[str, int]:
    if re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        raise ValueError("release candidate commit SHA is missing or invalid")
    if len(raw) > 1_000_000:
        raise ValueError("review output exceeds size limit")
    try:
        result = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("review output is missing or invalid JSON") from exc
    if not isinstance(result, Mapping):
        raise ValueError("review output must be an object")
    if result.get("reviewed_sha") != expected_sha:
        raise ValueError("reviewed commit does not match this release candidate")
    verdict = result.get("verdict")
    if verdict not in {"PASS", "REJECT", "OPEN"}:
        raise ValueError("review verdict is missing or invalid")
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("review summary is missing or invalid")
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise ValueError("review findings are missing or invalid")
    high_findings = 0
    for finding in findings:
        if (
            not isinstance(finding, Mapping)
            or finding.get("severity") not in SEVERITIES
        ):
            raise ValueError("review finding is malformed")
        if (
            not isinstance(finding.get("file"), str)
            or not finding["file"]
            or type(finding.get("line")) is not int
            or finding["line"] < 1
        ):
            raise ValueError("review finding location is malformed")
        if not isinstance(finding.get("detail"), str) or not finding["detail"].strip():
            raise ValueError("review finding detail is malformed")
        if finding["severity"] in {"blocker", "high"}:
            high_findings += 1
    if verdict != "PASS" or high_findings:
        raise ValueError("release source review did not pass")
    return verdict, len(findings)


def main() -> int:
    try:
        verdict, finding_count = validate_review(
            os.environ.get("REVIEW_JSON", ""), os.environ.get("REVIEWED_SHA", "")
        )
    except ValueError as exc:
        print(f"Release source review rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Release source review: {verdict}; {finding_count} non-blocking finding(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
