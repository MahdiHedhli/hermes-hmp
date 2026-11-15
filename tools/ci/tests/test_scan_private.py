"""Acceptance test for tools/ci/scan_private.py (T002).

Runnable directly (`python3 tools/ci/tests/test_scan_private.py`) or via pytest. Demonstrates the
Accept line from specs/001-connect-and-browse/tasks.md T002 — "the scanner fails on a seeded bad
sample and passes on the tree" — using the full repository tree (`scan_private.py` with no
arguments), per the controller's ruling on the pre-existing docs/research/ findings this task
turned up: `tools/ci/private_scan_baseline.txt` lists exactly `docs/research/**` (private R0
evidence, sanitized only at publication, never fixed in place / never a history rewrite) and
nothing else, so every other tracked path must scan clean.

The seeded "bad" and "clean" sample strings below are built from separated fragments (joined only
at runtime) so that this test file's own committed *source* never contains a directly-matchable
email/tailnet-address/home-path/team-id substring — otherwise this very file, being tracked,
would be its own false-positive finding.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(
    subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
)
SCANNER = REPO_ROOT / "tools" / "ci" / "scan_private.py"


def run_scanner(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), *(str(p) for p in paths)],
        capture_output=True, text=True,
    )


def _bad_sample_text() -> str:
    local = "real" + "." + "person"
    domain = ".".join(["gmail", "com"])
    email = local + "@" + domain
    home = "/" + "Users" + "/" + "janedoe" + "/secrets/keys.pem"
    ip = ".".join(["100", "101", "102", "103"])
    host = ".".join(["host", "some-tailnet", "ts", "net"])
    team = "AB12CD34EF"
    return (
        f"contact: {email}\n"
        f"home: {home}\n"
        f"tailnet: {ip} and {host}\n"
        f"DEVELOPMENT_TEAM = {team};\n"
    )


def test_seeded_bad_sample_fails() -> None:
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad_sample.txt"
        bad.write_text(_bad_sample_text())
        result = run_scanner(bad)
        assert result.returncode == 1, result.stdout + result.stderr
        for rule in ("EMAIL", "HOME_PATH", "TAILNET", "TEAM_ID"):
            assert rule in result.stdout, f"missing {rule} finding:\n{result.stdout}"


def test_clean_sample_passes() -> None:
    with tempfile.TemporaryDirectory() as d:
        good = Path(d) / "good_sample.txt"
        good.write_text(
            "contact: support@example.com\n"
            "range: 100\x2e64.0.0/10, fd7a:115c:a1e0::/48 and *.ts.net\n"
            "path note: /Users/<user>/.local/share\n"
            'DEVELOPMENT_TEAM = "";\n'
        )
        result = run_scanner(good)
        assert result.returncode == 0, result.stdout + result.stderr


def test_slugged_home_path_fails() -> None:
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "scratch_export.txt"
        bad.write_text(
            "/private/tmp/session/-Users-" + "agentuser-Documents-Coding-project/scratchpad\n"
        )
        result = run_scanner(bad)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "HOME_PATH" in result.stdout


def test_full_tree_scan_clean_without_suppressions() -> None:
    """The public tree must scan clean without a baseline or synthetic allowlist."""
    result = run_scanner()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "scan_private: clean."


if __name__ == "__main__":
    test_seeded_bad_sample_fails()
    test_clean_sample_passes()
    test_slugged_home_path_fails()
    test_full_tree_scan_clean_without_suppressions()
    print(
        "OK: scan_private fails on a seeded bad sample and passes on the full tree "
        "(baseline-aware)."
    )
