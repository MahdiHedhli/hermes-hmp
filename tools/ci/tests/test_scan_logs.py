"""Acceptance test for tools/ci/scan_logs.py (T033).

Runnable directly (`python3 tools/ci/tests/test_scan_logs.py`) or via pytest. Demonstrates the
Accept line from specs/001-connect-and-browse/tasks.md T033 — "the scanner catches every seeded
leak; the server unit-test logs scan clean" — plus a subprocess-level CLI smoke test (files and
stdin), matching the sibling `test_scan_private.py`'s style.
"""

from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(
    subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
)
SCANNER = REPO_ROOT / "tools" / "ci" / "scan_logs.py"

_SPEC = importlib.util.spec_from_file_location("scan_logs", SCANNER)
scan_logs = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(scan_logs)

_SERVER_SRC = REPO_ROOT / "server"
if str(_SERVER_SRC) not in sys.path:
    sys.path.insert(0, str(_SERVER_SRC))


def run_scanner(
    *args: str, stdin: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    full_env = None
    if env is not None:
        import os

        full_env = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(SCANNER), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=full_env,
    )


# One seeded line per signal T033 names, each built from separated fragments so this file's own
# committed source is never itself a matchable finding.
def _seeded_bad_lines() -> dict[str, str]:
    b64u_secret = "".join(["A"] * 22)  # 22-char run: the shortest real wire secret's b64u length
    sas = "-".join(["ABCDE"] * 4)
    hmp1 = "hmp1:" + "{" + '"v":1' + "}"
    bearer = "Authorization: " + "Bearer" + " " + "abc123.def456-token"
    pairing_code = "H7K9M2P4"  # 8 chars, all in gateway/pairing.py's ALPHABET
    fixture_label = "[F1" + " SYNTHETIC] some seeded row"
    device_prefix = "f1-fixture-device-" + "0001"
    operator_prefix = "f1-fixture-label-" + "op1"
    cgnat_ip = "100" + "." + "65" + "." + "12" + "." + "34"  # inside 100\x2e64.0.0/10
    home_ip = "192" + "." + "168" + "." + "1" + "." + "42"  # RFC 1918
    return {
        "TOKEN_B64U": f"nonce={b64u_secret}",
        "SAS_GROUP": f"sas shown: {sas}",
        "HMP1_PAYLOAD": f"scanned {hmp1}",
        "BEARER": bearer,
        "HERMES_PAIRING_CODE": f"code entered: {pairing_code}",
        "TAILNET": f"peer={cgnat_ip}",
        "HOME_IP": f"peer={home_ip}",
        "FIXTURE_LABEL": fixture_label,
        "FIXTURE_DEVICE_PREFIX": f"device_name={device_prefix}",
        "FIXTURE_OPERATOR_LABEL_PREFIX": f"label={operator_prefix}",
    }


def test_seeded_bad_sample_fails() -> None:
    lines = _seeded_bad_lines()
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.log"
        bad.write_text("\n".join(lines.values()) + "\n")
        result = run_scanner(str(bad))
        assert result.returncode == 1, result.stdout + result.stderr
        for rule in lines:
            assert rule in result.stdout, f"missing {rule} finding:\n{result.stdout}"


def test_each_signal_individually() -> None:
    for rule, line in _seeded_bad_lines().items():
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.log"
            bad.write_text(line + "\n")
            result = run_scanner(str(bad))
            assert result.returncode == 1, f"{rule} not detected:\n{line}\n{result.stdout}"
            assert rule in result.stdout, f"{rule} not detected:\n{line}\n{result.stdout}"


def test_token_b64u_catches_standard_base64_with_plus_slash_and_padding() -> None:
    # SEC-11: standard base64's `+`/`/` used to act as a delimiter for TOKEN_B64U, splitting one
    # long secret into several separate runs that could each fall under the 20-character minimum
    # -- e.g. a 30-byte secret encoded as standard base64 with a `+` or `/` near the middle.
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.log"
        # 40 base64 characters (30 raw bytes), containing '+', '/' and '=' padding, with no run
        # of 20+ base64url-only characters on either side of the '+'/'/' -- this could only ever
        # be caught as ONE finding if '+' and '/' are themselves part of the matched charset.
        standard_b64 = "QUFBQUFBQUFBQUFBQUFBQU" + "+" + "/" + "QUFBQUFBQUFBQUFBQUFB=="
        bad.write_text(f"signature={standard_b64}\n")
        result = run_scanner(str(bad))
        assert result.returncode == 1, result.stdout + result.stderr
        assert "TOKEN_B64U" in result.stdout


def test_hermes_pairing_code_is_case_insensitive() -> None:
    # SEC-11: a lowercase pairing code (the operator's terminal or a log line may render it in
    # either case) must be caught, not only the uppercase form gateway/pairing.py itself emits.
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.log"
        pairing_code = "h7k9m2p4"  # lowercase form of the seeded uppercase code above
        bad.write_text(f"code entered: {pairing_code}\n")
        result = run_scanner(str(bad))
        assert result.returncode == 1, result.stdout + result.stderr
        assert "HERMES_PAIRING_CODE" in result.stdout


def test_hermes_pairing_code_ignores_dictionary_words_without_digits() -> None:
    # Regression found after SEC-11 shipped: making HERMES_PAIRING_CODE case-insensitive also
    # matched ordinary English words that happen to be exactly 8 letters, all drawn from the
    # alphabet's 24 letters (it excludes only I and O) -- captured Hermes SQLite/watchdog log
    # lines flagged "embedded", "database", "escalate" and "tampered" this way, none of them a
    # real pairing code. A real code contains at least one of the alphabet's 8 digits with ~90%
    # probability; no dictionary word ever does. This is exactly the seeded false-positive shape
    # that used to require baseline entries in scan_logs_baseline.txt (now removed).
    with tempfile.TemporaryDirectory() as d:
        good = Path(d) / "clean.log"
        good.write_text(
            "the embedded database needs to escalate before the watchdog is tampered with\n"
            "EMBEDDED DATABASE ESCALATE TAMPERED\n"  # same words, uppercase
        )
        result = run_scanner(str(good))
        assert result.returncode == 0, result.stdout + result.stderr
        assert "HERMES_PAIRING_CODE" not in result.stdout


def test_hermes_pairing_code_with_digit_still_matches_case_insensitively() -> None:
    # The digit requirement must not silently reintroduce the case-sensitivity SEC-11 removed: a
    # real, lowercase-rendered code that DOES contain a digit is still caught.
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.log"
        bad.write_text("code entered: h7k9m2p4\n")
        result = run_scanner(str(bad))
        assert result.returncode == 1, result.stdout + result.stderr
        assert "HERMES_PAIRING_CODE" in result.stdout


def test_clean_log_passes() -> None:
    with tempfile.TemporaryDirectory() as d:
        good = Path(d) / "good.log"
        good.write_text(
            "event=ready outcome=ok\n"
            "event=pair_complete outcome=ok device_id=dev_abcd\n"
            "POST /hmp/v1/bots/{p}/authorize 200 0.012\n"
        )
        result = run_scanner(str(good))
        assert result.returncode == 0, result.stdout + result.stderr


def test_stdin_mode() -> None:
    result = run_scanner("-", stdin="event=ready outcome=ok\n")
    assert result.returncode == 0, result.stdout + result.stderr

    bad_stdin = "Authorization: " + "Bearer" + " " + "sometoken123\n"
    result = run_scanner("-", stdin=bad_stdin)
    assert result.returncode == 1
    assert "BEARER" in result.stdout


def test_no_args_defaults_to_default_scan_dir_and_is_clean_when_absent() -> None:
    # A no-arg run against a repo root with no DEFAULT_SCAN_DIR (docs/research/f1-acceptance/) at
    # all must be a clean no-op, not a usage error -- this is exactly how
    # tools/ci/check_all.sh's generic no-arg checker loop invokes every tools/ci scanner (see
    # check_icon.py, check_network_paths.py). Points the scanner at an empty temporary directory
    # via HMP_SCAN_LOGS_REPO_ROOT rather than relying on this worktree's own
    # docs/research/f1-acceptance/ happening to be absent or empty -- other tasks populate it, so
    # asserting against the real tree here would be flaky.
    with tempfile.TemporaryDirectory() as d:
        result = run_scanner(env={"HMP_SCAN_LOGS_REPO_ROOT": d})
        assert result.returncode == 0, result.stdout + result.stderr
        assert "nothing to scan" in result.stdout


def test_default_scan_skips_markdown_and_scans_txt() -> None:
    with tempfile.TemporaryDirectory() as d:
        scan_dir = Path(d) / "docs" / "research" / "f1-acceptance"
        scan_dir.mkdir(parents=True)
        bad = "Authorization: " + "Bearer" + " " + "some-captured-secret-token\n"
        (scan_dir / "report.md").write_text(bad)  # would trip BEARER if scanned
        (scan_dir / "capture.txt").write_text(bad)
        result = run_scanner(env={"HMP_SCAN_LOGS_REPO_ROOT": d})
        assert result.returncode == 1, result.stdout + result.stderr
        assert "capture.txt" in result.stdout
        assert "report.md" not in result.stdout


def test_baseline_loading_parses_glob_rule_count_and_reason() -> None:
    with tempfile.TemporaryDirectory() as d:
        script_dir = Path(d)
        (script_dir / "scan_logs_baseline.txt").write_text(
            "# a comment\n"
            "\n"
            "docs/research/f1-acceptance/a/*.txt  TOKEN_B64U  1  # reviewed public test material\n"
        )
        entries = scan_logs.load_baseline(script_dir)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.glob == "docs/research/f1-acceptance/a/*.txt"
        assert entry.rule == "TOKEN_B64U"
        assert entry.count == 1
        assert entry.reason == "reviewed public test material"
        assert entry.regex.match("docs/research/f1-acceptance/a/x.txt")
        assert not entry.regex.match("docs/research/f1-acceptance/a/b/x.txt")  # * does not cross /


def test_baseline_loading_rejects_the_old_glob_only_format() -> None:
    # SEC-11: the pre-fix "<glob>  # <reason>" format (no rule, no count) is now malformed --
    # every field is required, so a stale baseline entry cannot silently keep suppressing
    # whatever it used to under the new, stricter per-rule/per-count matching.
    with tempfile.TemporaryDirectory() as d:
        script_dir = Path(d)
        (script_dir / "scan_logs_baseline.txt").write_text(
            "docs/research/f1-acceptance/a/*.txt  # reviewed public test material\n"
        )
        entries = scan_logs.load_baseline(script_dir)
        assert entries == []


def test_baseline_suppresses_only_the_matching_rule_at_the_matching_count() -> None:
    # SEC-11: a baseline entry scoped to one rule must not suppress a different rule's finding
    # in the same file -- the pre-fix bug, where a baseline glob suppressed every rule.
    with tempfile.TemporaryDirectory() as d:
        script_dir = Path(d)
        (script_dir / "scan_logs_baseline.txt").write_text(
            "bad.log  TOKEN_B64U  1  # reviewed, only TOKEN_B64U was reviewed here\n"
        )
        baseline = scan_logs.load_baseline(script_dir)
        allowed_token = "".join(["A"] * 22)
        all_findings = [
            ("bad.log", "bad.log", 1, "TOKEN_B64U", allowed_token),
            ("bad.log", "bad.log", 2, "BEARER", "Bearer some-secret-token-value"),
        ]
        real, suppressed, mismatches = scan_logs.apply_baseline(all_findings, baseline)
        assert mismatches == []
        assert suppressed == {("bad.log", "TOKEN_B64U"): 1}
        assert real == [("bad.log", 2, "BEARER", "Bearer some-secret-token-value")]


def test_baseline_count_mismatch_is_not_suppressed() -> None:
    # SEC-11: a re-capture that produces a DIFFERENT count than what was reviewed must not be
    # silently suppressed at the old (now stale) count -- exactly the "later re-capture hides a
    # real leak" scenario the fix closes. Two hits now, where the baseline was pinned at one.
    with tempfile.TemporaryDirectory() as d:
        script_dir = Path(d)
        (script_dir / "scan_logs_baseline.txt").write_text(
            "capture.log  TOKEN_B64U  1  # pinned at one hit\n"
        )
        baseline = scan_logs.load_baseline(script_dir)
        token = "".join(["B"] * 22)
        all_findings = [
            ("capture.log", "capture.log", 1, "TOKEN_B64U", token),
            ("capture.log", "capture.log", 2, "TOKEN_B64U", token + "Z"),
        ]
        real, suppressed, mismatches = scan_logs.apply_baseline(all_findings, baseline)
        assert suppressed == {}
        assert mismatches == [("capture.log", "TOKEN_B64U", "capture.log", 1, 2)]
        # Neither hit is suppressed: both surface as real findings, not just the "extra" one.
        assert len(real) == 2


def test_real_baseline_suppresses_t045_evidence_and_real_tree_scans_clean() -> None:
    # tools/ci/scan_logs_baseline.txt carries a reviewed entry for the T045 android evidence
    # (public device key + signature, only token-*shaped*, not a secret). The real tree must
    # scan clean via that baseline, not by weakening TOKEN_B64U.
    result = run_scanner()
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = REPO_ROOT / "docs" / "research" / "f1-acceptance" / "android" / "evidence"
    if (evidence / "t045-server-verification.txt").is_file():
        assert "suppressed" in result.stdout
        assert "t045-server-verification.txt" in result.stdout


def test_no_args_scans_default_dir_when_present() -> None:
    default_dir = REPO_ROOT / "docs" / "research" / "f1-acceptance"
    already_existed = default_dir.is_dir()
    marker = default_dir / "_scan_logs_test_marker.log"
    default_dir.mkdir(parents=True, exist_ok=True)
    bad = "Authorization: " + "Bearer" + " " + "some-captured-secret-token\n"
    marker.write_text(bad)
    try:
        result = run_scanner()
        assert result.returncode == 1, result.stdout + result.stderr
        assert "BEARER" in result.stdout
    finally:
        marker.unlink()
        if not already_existed:
            default_dir.rmdir()


def test_redaction_never_prints_full_value() -> None:
    lines = _seeded_bad_lines()
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.log"
        bad.write_text(lines["TOKEN_B64U"] + "\n")
        result = run_scanner(str(bad))
        secret = "A" * 22
        assert secret not in result.stdout


# --------------------------------------------------------------------------------------------
# Integration with logging_policy.py (T033 Accept: "the server unit-test logs scan clean").
# --------------------------------------------------------------------------------------------


def test_log_event_output_scans_clean() -> None:
    from hmp_plugin.logging_policy import LOGGER_NAME, log_event

    logger = logging.getLogger(LOGGER_NAME)
    stream = __import__("io").StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    old_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        log_event("pair_complete", outcome="ok", device_id="dev_abcdefghijklmnop12345678901234")
        log_event("token_refresh", outcome="revoked", family_id="fam_abcdefghijklmnopqrstuvwxyz")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)

    manifest = REPO_ROOT / "fixtures" / "f1" / "instances.yaml"
    rules = scan_logs.build_rules(manifest)
    findings = scan_logs.scan_text(stream.getvalue(), rules)
    assert findings == [], (stream.getvalue(), findings)


def test_access_logger_output_scans_clean() -> None:
    from hmp_plugin.logging_policy import AllowListedAccessLogger

    stream = __import__("io").StringIO()
    access_logger = logging.getLogger("test.scan_logs.access")
    handler = logging.StreamHandler(stream)
    access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    try:
        al = AllowListedAccessLogger(logger=access_logger)

        req = SimpleNamespace(
            method="POST",
            headers={"Authorization": "Bearer some-secret-token-value-1234567890"},
            query_string="access_token=some-secret-query-value-1234567890",
            match_info=SimpleNamespace(
                route=SimpleNamespace(
                    resource=SimpleNamespace(canonical="/hmp/v1/bots/{p}/authorize")
                )
            ),
        )
        resp = SimpleNamespace(status=200)

        al.log(req, resp, 0.05)
    finally:
        access_logger.removeHandler(handler)

    manifest = REPO_ROOT / "fixtures" / "f1" / "instances.yaml"
    rules = scan_logs.build_rules(manifest)
    findings = scan_logs.scan_text(stream.getvalue(), rules)
    assert findings == [], (stream.getvalue(), findings)


if __name__ == "__main__":
    test_seeded_bad_sample_fails()
    test_each_signal_individually()
    test_token_b64u_catches_standard_base64_with_plus_slash_and_padding()
    test_hermes_pairing_code_is_case_insensitive()
    test_hermes_pairing_code_ignores_dictionary_words_without_digits()
    test_hermes_pairing_code_with_digit_still_matches_case_insensitively()
    test_clean_log_passes()
    test_stdin_mode()
    test_no_args_defaults_to_default_scan_dir_and_is_clean_when_absent()
    test_default_scan_skips_markdown_and_scans_txt()
    test_baseline_loading_parses_glob_rule_count_and_reason()
    test_baseline_loading_rejects_the_old_glob_only_format()
    test_baseline_suppresses_only_the_matching_rule_at_the_matching_count()
    test_baseline_count_mismatch_is_not_suppressed()
    test_real_baseline_suppresses_t045_evidence_and_real_tree_scans_clean()
    test_no_args_scans_default_dir_when_present()
    test_redaction_never_prints_full_value()
    test_log_event_output_scans_clean()
    test_access_logger_output_scans_clean()
    print("OK: scan_logs catches every seeded leak and passes on clean/allow-listed output.")
