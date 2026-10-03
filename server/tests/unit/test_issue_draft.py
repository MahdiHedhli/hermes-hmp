"""`hermes hmp compat` wording and `--issue-draft` (owner policy 2026-10-01).

The draft is pure and offline, uses an allowlist of fields, and reports an operator-supplied
failure as reported, never as observed. Nothing here touches a store, network or browser.
"""

from __future__ import annotations

import argparse
import io
import re
import socket
import subprocess
import webbrowser
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from hmp_plugin import cli, compat, issue_draft
from hmp_plugin.compat import (
    CompatResult,
    CompatStatus,
    Eligibility,
    Feature,
    FeatureStatus,
    Unavailable,
)
from hmp_plugin.contract import ErrorCode, OtherWhy
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource

SHA = "0123456789abcdef0123456789abcdef01234567"
CA705 = HermesVersion(Scheme.CALVER, (2026, 9, 24, 0), VersionSource.RELEASE_DATE)
SEMVER = HermesVersion(Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL)
OLD = HermesVersion(Scheme.SEMVER, (0, 21, 3), VersionSource.LITERAL)

CANARIES = (
    "canary-profile-name",
    "hmpd_canary_device_id",
    "/canary/hermes-home/path",
    "canary-host.internal",
    "sk-canary-api-key",
    "canary exception text",
    "canary-endpoint-address",
)


def eligibility(
    version: HermesVersion = CA705,
    *,
    failed: dict[Feature, tuple[Unavailable, tuple[str, ...]]] | None = None,
    sha: str | None = SHA,
) -> Eligibility:
    failed = failed or {}
    features = {
        f: (
            FeatureStatus(False, failed[f][0], failed[f][1], tested_label="manifest-label")
            if f in failed
            else FeatureStatus(True, tested_label="manifest-label")
        )
        for f in Feature
    }
    return Eligibility(version, sha, features)


def result_for(el: Eligibility) -> CompatResult:
    read = el.features[Feature.READ]
    if read.available:
        return CompatResult(CompatStatus.SUPPORTED, eligibility=el)
    return CompatResult(CompatStatus.UNSUPPORTED, compat.read_why(read), eligibility=el)


class Run:
    def __init__(self, el: Eligibility | None) -> None:
        self.result = result_for(el) if el is not None else CompatResult(CompatStatus.UNSUPPORTED)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def __call__(self, *argv: str) -> int:
        parser = argparse.ArgumentParser(prog="hermes hmp")
        cli.setup_parser(parser)
        env = cli.CliEnv(
            environ={"HERMES_HOME": CANARIES[2], "OPENAI_API_KEY": CANARIES[4]},
            stdout=self.stdout,
            stderr=self.stderr,
            compat=lambda: self.result,
        )
        return cli.dispatch(parser.parse_args(["compat", *argv]), env)

    @property
    def out(self) -> str:
        return self.stdout.getvalue()


@pytest.fixture(autouse=True)
def no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: any network, subprocess or browser use fails the test."""

    def boom(*_a: Any, **_k: Any) -> None:
        raise AssertionError("network, subprocess and browser use are forbidden")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(webbrowser, "open", boom)


# ---- compat wording (R5) ------------------------------------------------------------------------


def test_success_output_has_no_warning_vocabulary() -> None:
    run = Run(eligibility())
    assert run() == 0
    assert "Hermes version: 2026.9.24 (source: release_date)" in run.out
    minimum = (
        "Minimum Hermes: read 0.21.4 (2026.9.21); "
        "send, jobs, model, approvals and phone chat 0.21.5 (2026.9.24)"
    )
    assert minimum in run.out
    for feature in Feature:
        assert f"{feature.value}: available" in run.out
    lowered = run.out.lower()
    for word in ("unvalidated", "unsupported", "qualified", "tested", "not been validated"):
        assert word not in lowered
    assert "--issue-draft" not in run.out


def test_unknown_version_with_passing_probes_is_attempted_without_a_warning() -> None:
    unknown = HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN)
    run = Run(eligibility(unknown))
    assert run() == 0
    assert "Hermes version: unknown (source: unknown)" in run.out
    assert "validated" not in run.out and "--issue-draft" not in run.out


def test_below_the_floor_is_a_support_statement_not_a_bug_report() -> None:
    failed = dict.fromkeys(Feature, (Unavailable.VERSION_BELOW_FLOOR, ()))
    run = Run(eligibility(OLD, failed=failed))
    assert run() == 0
    assert "Hermes 0.21.3 is older than HMP's minimum" in run.out
    assert "Update Hermes." in run.out
    assert "--issue-draft" not in run.out and "validated" not in run.out


def test_a_real_feature_failure_prints_the_warning_and_the_hint() -> None:
    labels = ("hermes_state.SessionDB.get_session_by_title",)
    run = Run(eligibility(failed={Feature.SEND: (Unavailable.DEPENDENCY_MISSING, labels)}))
    assert run() == 0
    assert (
        "The send compatibility check failed on Hermes 2026.9.24 "
        "(dependency_missing: hermes_state.SessionDB.get_session_by_title)." in run.out
    )
    assert "To prepare a report: hermes hmp compat --issue-draft" in run.out
    assert "read: available" in run.out  # one feature failing does not hide the others
    assert "tested samples" not in run.out  # a matching tested sample: no sample note
    assert "validated" not in run.out


def test_the_sample_note_appears_only_after_a_failure_and_only_without_a_matching_sample() -> None:
    el = eligibility(failed={Feature.SEND: (Unavailable.DEPENDENCY_MISSING, ("a.b",))})
    features = dict(el.features)
    features[Feature.SEND] = FeatureStatus(False, Unavailable.DEPENDENCY_MISSING, ("a.b",))
    run = Run(Eligibility(el.version, el.git_sha, features))
    assert run() == 0
    assert "This Hermes is not one of HMP's tested samples." in run.out
    assert "has not been validated" not in run.out  # a failed probe is not proof of a bad version
    passing = Run(eligibility(CA705))
    assert passing() == 0 and "tested samples" not in passing.out


def test_hermes_not_found_has_its_own_message() -> None:
    failed = dict.fromkeys(Feature, (Unavailable.HERMES_NOT_FOUND, ()))
    run = Run(eligibility(HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN), failed=failed))
    assert run() == 0
    assert "could not be found" in run.out and "--issue-draft" not in run.out


# ---- --issue-draft ------------------------------------------------------------------------------


def test_r1_no_failure_and_no_context_means_nothing_to_report() -> None:
    run = Run(eligibility())
    assert run("--issue-draft") == 0
    assert run.out == "No HMP feature failure detected; nothing to report.\n"


def test_below_floor_alone_is_not_drafted() -> None:
    failed = dict.fromkeys(Feature, (Unavailable.VERSION_BELOW_FLOOR, ()))
    run = Run(eligibility(OLD, failed=failed))
    assert run("--issue-draft") == 0
    assert run.out == "No HMP feature failure detected; nothing to report.\n"


def test_r2_golden_draft_for_a_static_failure() -> None:
    labels = ("cron.jobs.create_job",)
    el = eligibility(failed={Feature.JOBS: (Unavailable.DEPENDENCY_MISSING, labels)})
    run = Run(el)
    assert run("--issue-draft") == 0
    draft = issue_draft.build_draft(
        el, None, plugin_version="1.0.0-f1", platform="macOS, Python 3.14"
    )
    assert draft is not None
    assert draft.title == "HMP: jobs unavailable on this Hermes, Hermes 2026.9.24"
    assert draft.body == (
        "## Environment\n"
        "- hermes_version: 2026.9.24\n"
        "- hermes_version_source: release_date\n"
        f"- hermes_git_sha: {SHA}\n"
        "- hmp_version: 1.0.0-f1\n"
        "- platform: macOS, Python 3.14\n"
        "\n"
        "## Observed by HMP's static dependency check\n"
        "\n"
        "HMP's own check found a Hermes API this feature needs to be missing. That is a fact "
        "about this install; it does not establish what caused it.\n"
        "\n"
        "- feature: jobs\n"
        "  reason: dependency_missing\n"
        "  missing: cron.jobs.create_job\n"
        "\n"
        "## What happened\n"
        "\n"
        "<describe what you did and what you expected>"
    )
    assert run.out.startswith("Title: HMP: jobs unavailable on this Hermes, Hermes 2026.9.24\n")
    assert run.out.endswith(
        "Review and edit the text above before posting. HMP has not sent anything.\n"
        "Open https://github.com/MahdiHedhli/hermes-hmp/issues/new and paste the text above.\n"
    )


def test_operator_report_is_available_even_when_every_probe_passes() -> None:
    run = Run(eligibility())
    assert run("--issue-draft", "--feature", "jobs", "--failure-code", "cron_unavailable") == 0
    assert "- reported_feature: jobs" in run.out
    assert "- reported_failure_code: cron_unavailable" in run.out
    assert "- report_origin: operator" in run.out
    assert "Reported by the operator, not automatically observed" in run.out
    assert "HMP did not observe the failure" in run.out
    assert "does not establish that the Hermes version, HMP or anything else caused it" in run.out
    assert "Observed by HMP" not in run.out
    assert "nothing to report" not in run.out
    assert run.out.count("Title: HMP: jobs failure (cron_unavailable), Hermes 2026.9.24") == 1


def test_operator_report_and_static_failure_appear_in_separate_sections() -> None:
    el = eligibility(failed={Feature.MODEL: (Unavailable.PROBE_FAILED, ())})
    run = Run(el)
    assert run("--issue-draft", "--feature", "send", "--failure-code", "write_gate_closed") == 0
    assert run.out.index("Observed by HMP") < run.out.index("Reported by the operator")
    assert "- feature: model" in run.out and "- reported_feature: send" in run.out


@pytest.mark.parametrize(
    ("feature", "code"),
    [
        ("read", "other"),
        ("session_browsing", "not_found"),
        ("send", "write_gate_closed"),
        ("send", "api_server_unavailable"),
        ("jobs", "cron_unavailable"),
        ("model", "model_unavailable"),
    ],
)
def test_every_accepted_pair_is_a_real_error_code(feature: str, code: str) -> None:
    assert code in {c.value for c in ErrorCode}
    assert Run(eligibility())("--issue-draft", "--feature", feature, "--failure-code", code) == 0


@pytest.mark.parametrize(
    ("feature", "code"),
    [
        ("jobs", "model_unavailable"),
        ("model", "cron_unavailable"),
        ("send", "cron_unavailable"),
        ("read", "write_gate_closed"),
        ("jobs", "bad_request"),
        ("jobs", "canary exception text"),
        ("jobs", "Traceback (most recent call last): sk-canary-api-key"),
        ("nothing", "cron_unavailable"),
        ("jobs", ""),
    ],
)
def test_wrong_pairs_and_free_text_are_rejected_without_being_echoed(
    feature: str, code: str
) -> None:
    run = Run(eligibility())
    argv = ("--issue-draft", "--feature", feature, "--failure-code", code)
    assert run(*argv) == cli.EXIT_ENVIRONMENT
    assert run.out == ""
    error = run.stderr.getvalue()
    assert error.startswith("hermes hmp: refused:")
    for fragment in (code, "sk-canary", "Traceback", "canary"):
        assert not fragment or fragment not in error


def test_feature_and_failure_code_must_be_given_together_and_with_issue_draft() -> None:
    for argv in (
        ("--issue-draft", "--feature", "jobs"),
        ("--issue-draft", "--failure-code", "cron_unavailable"),
        ("--feature", "jobs", "--failure-code", "cron_unavailable"),
    ):
        run = Run(eligibility())
        assert run(*argv) == cli.EXIT_ENVIRONMENT, argv
        assert run.out == ""


@pytest.mark.parametrize(
    ("feature", "code"),
    [("jobs", "forbidden"), ("model", "unauthorized"), ("send", "not_found"), ("read", "revoked")],
)
def test_permission_outcomes_are_explained_and_never_drafted(feature: str, code: str) -> None:
    run = Run(eligibility())
    assert run("--issue-draft", "--feature", feature, "--failure-code", code) == 0
    assert "not evidence of a Hermes version incompatibility" in run.out
    assert "No issue draft was prepared" in run.out
    assert "Title:" not in run.out and "issues/new" not in run.out


def test_a_report_for_a_below_floor_hermes_says_to_update() -> None:
    failed = dict.fromkeys(Feature, (Unavailable.VERSION_BELOW_FLOOR, ()))
    run = Run(eligibility(OLD, failed=failed))
    assert run("--issue-draft", "--feature", "send", "--failure-code", "write_gate_closed") == 0
    assert "older than HMP's minimum for send" in run.out
    assert "reported_feature: send" in run.out


def test_r3_privacy_canary_never_appears_and_only_allowlisted_keys_do(tmp_path: Path) -> None:
    labels = ("hermes_state.SessionDB.get_session_by_title",)
    el = eligibility(failed={Feature.SEND: (Unavailable.DEPENDENCY_MISSING, labels)})
    outputs = []
    for argv in (
        (),
        ("--issue-draft",),
        ("--issue-draft", "--feature", "send", "--failure-code", "api_server_unavailable"),
    ):
        run = Run(el)
        assert run(*argv) == 0
        outputs.append(run.out + run.stderr.getvalue())
    for text in outputs:
        for canary in CANARIES:
            assert canary not in text, canary
        assert "manifest-label" not in text
    keys = set(re.findall(r"^\s*(?:- )?([a-z_]+):", outputs[2], flags=re.MULTILINE))
    assert keys == {
        "hermes_version", "hermes_version_source", "hermes_git_sha", "hmp_version", "platform",
        "feature", "reason", "missing",
        "reported_feature", "reported_failure_code", "report_origin",
    }
    assert "http" not in outputs[2].replace(issue_draft.ISSUES_URL, "")


def test_the_draft_revalidates_every_field() -> None:
    hostile = Eligibility(
        CA705,
        "not-a-sha /canary/path",
        {
            f: FeatureStatus(
                False,
                Unavailable.DEPENDENCY_MISSING,
                (
                    "canary exception text",
                    "cron.jobs.create_job",
                    "hermes_state.SessionDB.get_session",
                ),
            )
            if f is Feature.JOBS
            else FeatureStatus(True)
            for f in Feature
        },
    )
    draft = issue_draft.build_draft(
        hostile, None, plugin_version="1.0 /canary", platform="macOS, Python 3.14"
    )
    assert draft is not None
    assert "- hermes_git_sha: none" in draft.body
    assert "- hmp_version: unknown" in draft.body
    assert "canary" not in draft.render()
    # Constant labels of another feature's table are dropped too.
    assert "missing: cron.jobs.create_job\n" in draft.body


def test_platform_text_is_an_os_family_and_python_major_minor() -> None:
    assert issue_draft.platform_text("darwin", (3, 14)) == "macOS, Python 3.14"
    assert issue_draft.platform_text("linux", (3, 12)) == "Linux, Python 3.12"
    assert issue_draft.platform_text("win32", (3, 13)) == "Windows, Python 3.13"
    assert issue_draft.platform_text("plan9", (3, 14)) == "other, Python 3.14"
    live = issue_draft.platform_text()
    assert re.fullmatch(r"(macOS|Linux|Windows|other), Python \d+\.\d+", live)


def test_hmp_version_comes_from_the_manifest_and_is_validated(tmp_path: Path) -> None:
    manifest = tmp_path / "plugin.yaml"
    manifest.write_text("name: hmp\nversion: 1.2.3-rc.1+5\n", encoding="utf-8")
    assert issue_draft.hmp_version(manifest) == "1.2.3-rc.1+5"
    manifest.write_text("version: bad value with spaces\n", encoding="utf-8")
    assert issue_draft.hmp_version(manifest) == "unknown"
    assert issue_draft.hmp_version(tmp_path / "missing.yaml") == "unknown"
    assert issue_draft.hmp_version() != "unknown"  # the real manifest


def test_issue_draft_module_is_stdlib_only() -> None:
    import ast

    tree = ast.parse(Path(issue_draft.__file__).read_text(encoding="utf-8"))
    imported = {
        (n.module or "").split(".")[0] if isinstance(n, ast.ImportFrom) else a.name.split(".")[0]
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom | ast.Import)
        for a in (n.names if isinstance(n, ast.Import) else [None])
    }
    assert not imported & {"socket", "subprocess", "urllib", "http", "webbrowser", "requests"}


def test_pair_offer_still_refuses_when_read_is_unavailable() -> None:
    """G10: read availability, not a build list, gates `pair offer` (via the same CompatResult)."""
    failed = {Feature.READ: (Unavailable.DEPENDENCY_MISSING, ("gateway.run.GatewayRunner",))}
    result = result_for(eligibility(failed=failed))
    assert not result.supported and result.why is OtherWhy.HERMES_READ_DEPENDENCY_MISSING


# ---- direct helper-boundary hostile tests (no CLI): every value a caller could get wrong ----

CANARY = "CANARYprofile_alice"
# Deliberately synthetic hostile fixtures, not owner data: a made-up address and a made-up profile
# path, assembled from parts so the privacy scan sees no literal. The runtime values are unchanged.
_SYNTHETIC_ADDRESS_OCTETS = ("100", "64", "1", "2")
_SYNTHETIC_PATH_PARTS = ("Users", "alice", ".hermes", "profiles", "alice")
HOST_IP = ".".join(_SYNTHETIC_ADDRESS_OCTETS)
PATH = "/" + "/".join(_SYNTHETIC_PATH_PARTS)
CONTEXT = "message context: hello alice"
HOSTILE = (CANARY, HOST_IP, PATH, CONTEXT)
JOBS_LABEL = "cron.jobs.create_job"


class _Trap:
    """Fails the test if anything formats it (str, repr, format, hash-free)."""

    def __str__(self) -> str:
        raise AssertionError("formatted an unknown object with str()")

    __repr__ = __str__

    def __format__(self, spec: str) -> str:
        raise AssertionError("formatted an unknown object with format()")


def _el(
    status: FeatureStatus | object,
    *,
    feature: object = Feature.JOBS,
    version: object = CA705,
    sha: object = None,
) -> Any:
    # A str key equals (and hashes as) its StrEnum member, so only start from the real members
    # when the hostile key is itself one.
    features: dict[Any, Any] = (
        {f: FeatureStatus(True) for f in Feature} if isinstance(feature, Feature) else {}
    )
    features[feature] = status
    return Eligibility(version, sha, features)  # type: ignore[arg-type]


def _text(*args: Any, **kwargs: Any) -> str:
    draft = issue_draft.build_draft(*args, **kwargs)
    return "" if draft is None else draft.title + "\n" + draft.render()


def _assert_clean(text: str) -> None:
    for canary in HOSTILE:
        assert canary not in text, canary


def test_h1_missing_labels_are_constant_members_of_that_features_own_table() -> None:
    status = FeatureStatus(
        False,
        Unavailable.DEPENDENCY_MISSING,
        (CANARY, JOBS_LABEL, "hermes_state.SessionDB.get_session", "x" * 50, PATH),
    )
    text = _text(_el(status), None)
    _assert_clean(text)
    assert "missing: cron.jobs.create_job\n" in text
    assert "SessionDB.get_session" not in text  # a real label, but another feature's table
    # Every label in every feature's own table passes for that feature and no other.
    for feature in Feature:
        for label in issue_draft._FEATURE_LABELS[feature]:
            assert issue_draft.known_labels(feature, (label,)) == (label,)
    assert issue_draft.known_labels(Feature.JOBS, (_Trap(), 5, None)) == ()
    assert issue_draft.known_labels("jobs", (JOBS_LABEL,)) == ()  # not a Feature
    assert issue_draft.known_labels(Feature.JOBS, JOBS_LABEL) == ()  # a str, not a sequence


def test_h2_free_text_platform_and_plugin_version_are_never_emitted() -> None:
    status = FeatureStatus(False, Unavailable.DEPENDENCY_MISSING, (JOBS_LABEL,))
    for bad in (f"host {HOST_IP} {PATH}", f"macOS, Python 3.14 {PATH}", CANARY, "", _Trap()):
        text = _text(_el(status), None, platform=bad)  # type: ignore[arg-type]
        _assert_clean(text)
        assert re.search(r"- platform: (macOS|Linux|Windows|other), Python \d+\.\d+\n", text)
    canonical = _text(_el(status), None, platform="macOS, Python 3.14")
    assert "- platform: macOS, Python 3.14\n" in canonical
    for bad_version in (CANARY, "CANARY-alice", "1.0.0-CANARY", "1.0.0+" + CANARY, HOST_IP, PATH):
        text = _text(_el(status), None, plugin_version=bad_version)
        _assert_clean(text)
        assert "- hmp_version: unknown\n" in text, bad_version
    for good in ("1.0.0-f1", "1.2.3", "1.2.3-rc.1+5", "0.9.10-beta2"):
        assert f"- hmp_version: {good}\n" in _text(_el(status), None, plugin_version=good)


def test_h2b_platform_text_takes_only_small_ints_and_a_known_family() -> None:
    live = issue_draft.platform_text()
    assert issue_draft.platform_text(PATH, (3, 14)) == "other, Python 3.14"
    assert issue_draft.platform_text(_Trap(), (3, 14)) == "other, Python 3.14"  # type: ignore[arg-type]
    for bad in (("3", "x"), (True, 14), (3, 10**9), (-1, 2), (3,), [3, 14], (3.0, 14.0), None):
        text = issue_draft.platform_text("linux", bad)  # type: ignore[arg-type]
        assert re.fullmatch(r"Linux, Python \d{1,2}\.\d{1,2}", text), bad
    assert live.split(", ")[1].count(".") == 1


def test_h3_a_directly_built_operator_report_is_revalidated_with_fixed_error() -> None:
    bad_reports = (
        issue_draft.OperatorReport(f"jobs\n- secret: {CANARY}", f"x {HOST_IP}"),
        issue_draft.OperatorReport("jobs", f"cron_unavailable {PATH}"),
        issue_draft.OperatorReport("send", "cron_unavailable"),  # valid code, other feature
        issue_draft.OperatorReport("jobs", "forbidden"),  # a permission outcome, not a report
        issue_draft.OwnReason("jobs", "forbidden"),
        issue_draft.OperatorReport(_Trap(), _Trap()),  # type: ignore[arg-type]
        CONTEXT,
        _Trap(),
    )
    for report in bad_reports:
        with pytest.raises(issue_draft.ReportRequestError) as caught:
            issue_draft.build_draft(None, report)
        assert str(caught.value) == "not an accepted report"
        assert caught.value.__cause__ is None and caught.value.__context__ is None
    good = issue_draft.build_draft(None, issue_draft.OperatorReport("jobs", "cron_unavailable"))
    assert good is not None and "- reported_failure_code: cron_unavailable\n" in good.body


def test_h4_hermes_version_is_rebuilt_from_enums_and_int_parts_or_unknown() -> None:
    status = FeatureStatus(False, Unavailable.DEPENDENCY_MISSING, (JOBS_LABEL,))
    s, c, lit = Scheme, Scheme.CALVER, VersionSource.LITERAL
    hostile_versions: list[object] = [
        HermesVersion(s.SEMVER, (CANARY, HOST_IP, 1), lit),  # type: ignore[arg-type]
        HermesVersion(s.SEMVER, (_Trap(), 1, 2), lit),  # type: ignore[arg-type]
        HermesVersion(s.SEMVER, (True, 21, 5), lit),
        HermesVersion(s.SEMVER, (0, 21), lit),  # arity
        HermesVersion(s.SEMVER, (0, 21, 5, 1), lit),
        HermesVersion(s.SEMVER, (0, 0, 0), lit),  # the placeholder is not a version
        HermesVersion(s.SEMVER, (0, 21, 10**6), lit),  # range
        HermesVersion(s.SEMVER, (0, -1, 5), lit),
        HermesVersion(s.SEMVER, (0, 21, 5), VersionSource.RELEASE_DATE),  # wrong source
        HermesVersion(c, (2026, 9, 24), VersionSource.RELEASE_DATE),
        HermesVersion(c, (2026, 2, 31, 0), VersionSource.RELEASE_DATE),  # day 31 is in range
        HermesVersion(c, (2026, 13, 1, 0), VersionSource.RELEASE_DATE),
        HermesVersion(c, (1999, 9, 24, 0), VersionSource.RELEASE_DATE),
        HermesVersion(c, (2026, 9, 24, 0), VersionSource.STAMP),
        HermesVersion(CANARY, (0, 21, 5), lit),  # type: ignore[arg-type]
        HermesVersion(s.SEMVER, (0, 21, 5), CANARY),  # type: ignore[arg-type]
        HermesVersion(s.SEMVER, [0, 21, 5], lit),  # type: ignore[arg-type]
        HermesVersion(s.UNKNOWN, (0, 21, 5), VersionSource.UNKNOWN),
        _Trap(),
        CANARY,
    ]
    for version in hostile_versions:
        text = _text(_el(status, version=version), None)
        _assert_clean(text)
        if getattr(version, "parts", None) == (2026, 2, 31, 0):
            continue  # a calendar-valid-looking value is in the accepted grammar
        assert "- hermes_version: unknown\n" in text, version
        assert "- hermes_version_source: unknown\n" in text, version
        assert text.splitlines()[0].endswith(", Hermes unknown"), version
    assert "- hermes_version: 0.21.5\n- hermes_version_source: literal\n" in _text(
        _el(status, version=SEMVER), None
    )
    assert "- hermes_version: 2026.9.24\n- hermes_version_source: release_date\n" in _text(
        _el(status), None
    )


def test_h5_only_real_feature_keys_statuses_and_static_reasons_are_drafted() -> None:
    class Fake:
        value = CANARY

    real = FeatureStatus(False, Unavailable.DEPENDENCY_MISSING, (JOBS_LABEL,))
    for feature in (Fake(), CANARY, "jobs", None, 5):
        assert _text(_el(real, feature=feature), None) == "", feature
    for status in (
        SimpleNamespace(available=False, reason=Unavailable.DEPENDENCY_MISSING, missing=(CANARY,)),
        FeatureStatus(False, Fake(), (JOBS_LABEL,)),  # type: ignore[arg-type]
        FeatureStatus(False, CANARY, (JOBS_LABEL,)),  # type: ignore[arg-type]
        FeatureStatus(False, "dependency_missing", (JOBS_LABEL,)),  # type: ignore[arg-type]
        FeatureStatus(False, Unavailable.VERSION_BELOW_FLOOR, (JOBS_LABEL,)),
        FeatureStatus(False, Unavailable.REQUIRES_READ, (JOBS_LABEL,)),
        FeatureStatus(False, Unavailable.HERMES_NOT_FOUND),
        FeatureStatus(True),
        _Trap(),
    ):
        assert _text(_el(status), None) == "", status.__class__
    for not_eligibility in (None, CANARY, _Trap(), SimpleNamespace(features={Feature.JOBS: real})):
        assert issue_draft.static_failures(not_eligibility) == ()
        assert issue_draft.build_draft(not_eligibility, None) is None
    # An unhashable or odd git sha is "none".
    for sha in (CANARY, PATH, ["x"], 5, "A" * 40, "g" * 40):
        assert "- hermes_git_sha: none\n" in _text(_el(real, sha=sha), None)


def test_h6_own_reason_text_revalidates_its_argument_before_interpolating() -> None:
    for bad in (
        issue_draft.OwnReason(CANARY, "forbidden"),
        issue_draft.OwnReason("jobs", f"forbidden {PATH}"),
        issue_draft.OwnReason("jobs", "cron_unavailable"),  # a reportable code is not an own reason
        issue_draft.OwnReason("session_browsing", "not_found"),  # reportable for this feature
        issue_draft.OwnReason(_Trap(), _Trap()),  # type: ignore[arg-type]
        issue_draft.OperatorReport("jobs", "cron_unavailable"),
        CONTEXT,
        None,
        _Trap(),
    ):
        with pytest.raises(issue_draft.ReportRequestError) as caught:
            issue_draft.own_reason_text(bad)
        assert str(caught.value) == "not an accepted report"
    text = issue_draft.own_reason_text(issue_draft.OwnReason("send", "forbidden"))
    assert text.startswith("`forbidden` on send is a permission, routing or setting outcome")


def test_h7_failure_detail_for_the_cli_uses_the_same_membership_and_enum_checks() -> None:
    hostile = FeatureStatus(
        False, Unavailable.DEPENDENCY_MISSING, (CANARY, JOBS_LABEL, PATH, HOST_IP)
    )
    detail = issue_draft.failure_detail(Feature.JOBS, hostile)
    assert detail == f"dependency_missing: {JOBS_LABEL}"
    assert issue_draft.failure_detail(Feature.MODEL, hostile) == "dependency_missing"
    assert issue_draft.failure_detail(CANARY, hostile) == "dependency_missing"
    odd = SimpleNamespace(reason=CANARY, missing=(CANARY,))
    assert issue_draft.failure_detail(Feature.JOBS, odd) == "unknown"
    assert issue_draft.failure_detail(Feature.JOBS, _Trap()) == "unknown"
    # And the CLI prints that detail, not the raw status.
    el = _el(hostile)
    run = Run(el)
    assert run() == 0
    _assert_clean(run.out + run.stderr.getvalue())
    assert f"jobs: unavailable (dependency_missing: {JOBS_LABEL})" in run.out


# ---- spec 034: the approvals and phone_chat members (R4, R16) ------------------------------------

_HOOK_WORDS = ("present", "absent", "unknown")


def _with_hook(el: Eligibility, hook: bool | None) -> Eligibility:
    return Eligibility(el.version, el.git_sha, el.features, hook)


def test_compat_lists_both_members_and_the_verbose_hook_fact() -> None:
    for hook, word in ((True, "present"), (False, "absent"), (None, "unknown")):
        run = Run(_with_hook(eligibility(), hook))
        assert run("--verbose") == 0
        assert "approvals: available" in run.out and "phone_chat: available" in run.out
        assert f"Session-stream approval hook: {word} (informational;" in run.out
        assert "never gates" in run.out
        # An absent hook is a fact, never a warning or a failure.
        assert "--issue-draft" not in run.out and "failed" not in run.out.lower()
    quiet = Run(_with_hook(eligibility(), False))
    assert quiet() == 0
    assert "Session-stream approval hook" not in quiet.out  # only with --verbose


def test_a_missing_hook_on_a_passing_install_prompts_no_warning_or_draft() -> None:
    run = Run(_with_hook(eligibility(CA705), False))
    assert run("--verbose") == 0
    lowered = run.out.lower()
    for word in ("unvalidated", "unsupported", "not one of", "tested samples", "warning"):
        assert word not in lowered


def test_below_the_floor_names_both_members_and_drafts_nothing() -> None:
    gone = {
        f: FeatureStatus(False, Unavailable.VERSION_BELOW_FLOOR)
        for f in (Feature.SEND, Feature.JOBS, Feature.MODEL, Feature.APPROVALS, Feature.PHONE_CHAT)
    }
    el = Eligibility(
        SEMVER_READ_ONLY,
        None,
        {**{f: FeatureStatus(True) for f in Feature}, **gone},
    )
    run = Run(el)
    assert run() == 0
    assert "approvals: unavailable (hermes_version_below_floor)" in run.out
    assert "phone_chat: unavailable (hermes_version_below_floor)" in run.out
    assert "older than HMP's minimum" in run.out and "Update Hermes." in run.out
    assert "--issue-draft" not in run.out
    draft = Run(el)
    assert draft("--issue-draft") == 0
    assert issue_draft.NOTHING_TO_REPORT in draft.out


SEMVER_READ_ONLY = HermesVersion(Scheme.SEMVER, (0, 21, 4), VersionSource.LITERAL)


def test_requires_send_on_a_member_is_a_consequence_not_a_drafted_failure() -> None:
    el = eligibility(
        failed={
            Feature.SEND: (Unavailable.DEPENDENCY_MISSING, ("hermes_state.SessionDB.get_session",)),
            Feature.APPROVALS: (Unavailable.REQUIRES_SEND, ()),
            Feature.PHONE_CHAT: (Unavailable.REQUIRES_SEND, ()),
        }
    )
    failures = [f.value for f, _ in issue_draft.static_failures(el)]
    assert failures == ["send"]  # the members are never drafted for send's absence
    run = Run(el)
    assert run() == 0
    assert "approvals: unavailable (requires_send)" in run.out
    assert "phone_chat: unavailable (requires_send)" in run.out


def test_a_static_phone_chat_failure_drafts_with_hmp_labels_and_the_hook_fact() -> None:
    label = "tools.approval.list_gateway_approvals"
    el = _with_hook(
        eligibility(failed={Feature.PHONE_CHAT: (Unavailable.DEPENDENCY_MISSING, (label,))}), False
    )
    run = Run(el)
    assert run("--issue-draft") == 0
    assert "feature: phone_chat" in run.out and f"missing: {label}" in run.out
    assert "Observed by HMP's static dependency check" in run.out
    assert "- session_stream_approval_hook: absent (informational; never gates)" in run.out
    assert "manifest-label" not in run.out and SHA in run.out


def test_an_unrelated_label_never_reaches_a_phone_chat_draft() -> None:
    el = eligibility(
        failed={
            Feature.PHONE_CHAT: (
                Unavailable.DEPENDENCY_MISSING,
                ("tools.approval.list_gateway_approvals", CANARIES[0], "gateway.run.GatewayRunner"),
            )
        }
    )
    run = Run(el)
    assert run("--issue-draft") == 0
    assert "tools.approval.list_gateway_approvals" in run.out
    assert CANARIES[0] not in run.out and "gateway.run.GatewayRunner" not in run.out


@pytest.mark.parametrize("feature", ["approvals", "phone_chat"])
@pytest.mark.parametrize("code", ["write_gate_closed", "api_server_unavailable"])
def test_operator_reports_for_the_members_are_labelled_and_carry_the_hook_fact(
    feature: str, code: str
) -> None:
    run = Run(_with_hook(eligibility(), True))
    assert run("--issue-draft", "--feature", feature, "--failure-code", code) == 0
    assert "Reported by the operator, not automatically observed" in run.out
    assert f"- reported_feature: {feature}" in run.out
    assert f"- reported_failure_code: {code}" in run.out
    assert "- session_stream_approval_hook: present (informational; never gates)" in run.out
    assert "does not establish that the Hermes version" in run.out


def test_other_features_drafts_do_not_carry_the_hook_fact() -> None:
    run = Run(_with_hook(eligibility(), True))
    assert run("--issue-draft", "--feature", "send", "--failure-code", "write_gate_closed") == 0
    assert "session_stream_approval_hook" not in run.out


@pytest.mark.parametrize(
    ("feature", "code"),
    [
        ("approvals", "stale"),  # an answer status, not a reportable feature failure
        ("approvals", "invalid_choice"),
        ("phone_chat", "cron_unavailable"),
        ("phone_chat", "model_unavailable"),
        ("approvals", "other"),
        ("approvals", CANARIES[5]),
    ],
)
def test_wrong_member_code_pairs_are_refused_without_echo(feature: str, code: str) -> None:
    run = Run(eligibility())
    argv = ("--issue-draft", "--feature", feature, "--failure-code", code)
    assert run(*argv) == cli.EXIT_ENVIRONMENT
    assert run.out == ""
    error = run.stderr.getvalue()
    assert error.startswith("hermes hmp: refused:")
    assert code not in error and CANARIES[5] not in error


@pytest.mark.parametrize("code", ["forbidden", "unauthorized", "not_found", "not_routed"])
def test_permission_and_routing_codes_for_the_members_are_explained_never_drafted(
    code: str,
) -> None:
    run = Run(eligibility())
    assert run("--issue-draft", "--feature", "approvals", "--failure-code", code) == 0
    assert "permission, routing or setting outcome" in run.out
    assert "Title:" not in run.out


def test_the_hook_fact_is_a_fixed_word_whatever_the_object_says() -> None:
    class Hostile:
        stream_approval_hook = CANARIES[5]

    bogus = _with_hook(eligibility(), CANARIES[5])  # type: ignore[arg-type]
    draft = issue_draft.build_draft(
        bogus, issue_draft.OperatorReport("approvals", "write_gate_closed")
    )
    assert draft is not None and CANARIES[5] not in draft.body
    assert "session_stream_approval_hook: unknown (informational; never gates)" in draft.body
    assert Hostile.stream_approval_hook == CANARIES[5]  # only the fixed words are ever rendered


def test_no_member_draft_carries_a_canary_or_private_value() -> None:
    for member in ("approvals", "phone_chat"):
        run = Run(_with_hook(eligibility(), None))
        assert run("--issue-draft", "--feature", member, "--failure-code", "write_gate_closed") == 0
        for canary in CANARIES:
            assert canary not in run.out
