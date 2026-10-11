"""`local_media` eligibility member and its offline issue draft (spec 011, M2: A1-A6, A13).

Owner policy 2026-10-01 and root decisions D-M2, D-M3, D-M8. `local_media` depends on `read` alone,
uses the write floor, probes exactly three native `SessionDB` callables, and reads no build list,
manifest, fingerprint or Git SHA. Its only reportable offline failure code is `media_unavailable`.
Everything here is synthetic: no live Hermes home, network, provider or device is touched.
"""

from __future__ import annotations

import argparse
import builtins
import inspect
import io
import json
import re
import socket
import sys
import textwrap
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import cli, compat, hermes_version, issue_draft
from hmp_plugin.compat import (
    CompatResult,
    CompatStatus,
    DependencySpec,
    Eligibility,
    Feature,
    FeatureStatus,
    Unavailable,
    evaluate_eligibility,
)
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource

MEDIA = Feature.LOCAL_MEDIA
MEDIA_LABELS = (
    "hermes_state.SessionDB.get_session",
    "hermes_state.SessionDB.get_session_by_title",
    "hermes_state.SessionDB.get_compression_lineage",
)
LINEAGE = MEDIA_LABELS[2]

SEMVER_OLD = HermesVersion(Scheme.SEMVER, (0, 21, 3), VersionSource.LITERAL)
SEMVER_READ_ONLY = HermesVersion(Scheme.SEMVER, (0, 21, 4), VersionSource.LITERAL)
SEMVER_FLOOR = HermesVersion(Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL)
SEMVER_UNLISTED = HermesVersion(Scheme.SEMVER, (0, 21, 6), VersionSource.LITERAL)
SEMVER_NEWER = HermesVersion(Scheme.SEMVER, (0, 99, 0), VersionSource.LITERAL)
CALVER_FLOOR = HermesVersion(Scheme.CALVER, (2026, 9, 24, 0), VersionSource.RELEASE_DATE)
CALVER_NEWER = HermesVersion(Scheme.CALVER, (2027, 1, 5, 0), VersionSource.RELEASE_DATE)
CALVER_OLD = HermesVersion(Scheme.CALVER, (2026, 9, 21, 0), VersionSource.RELEASE_DATE)
UNKNOWN = HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN)

TABLES: Mapping[str, Sequence[DependencySpec]] = {
    "read": compat.READ_CORE_DEPENDENCIES,
    "session_browsing": compat.SESSION_BROWSING_DEPENDENCIES,
    "send": compat.DIRECT_SEND_DEPENDENCIES,
    "jobs": compat.CRON_DEPENDENCIES,
    "model": compat.MODEL_DEPENDENCIES,
    "phone_chat": compat.PHONE_CHAT_DEPENDENCIES,
    "local_media": compat.LOCAL_MEDIA_DEPENDENCIES,
}
SIBLINGS = tuple(f for f in Feature if f is not MEDIA)


class Probe:
    """A table-keyed probe double: records each table asked about; never imports anything."""

    def __init__(self, missing: Mapping[str, Sequence[str]] | None = None) -> None:
        self.calls: list[str] = []
        self.missing = missing or {}

    def __call__(self, _root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
        name = next(k for k, v in TABLES.items() if v is specs)
        self.calls.append(name)
        return self.missing.get(name, ())


def evaluate(
    version: HermesVersion = SEMVER_FLOOR, probe: Probe | None = None
) -> Eligibility:
    return evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _root: version,
        probe=probe or Probe(),
        evidence=lambda _root: {},
    )


# ---- the table and floor are exactly the decided ones -----------------------------------------


def test_the_member_table_and_floor_are_exactly_the_decided_ones() -> None:
    assert Feature.LOCAL_MEDIA.value == "local_media"
    assert tuple(s.label for s in compat.LOCAL_MEDIA_DEPENDENCIES) == MEDIA_LABELS
    # Each native instance method is called with one positional argument in bridge.py.
    # Require self plus that argument using the existing signature discipline.
    for name, table in TABLES.items():
        if name != "local_media":
            assert table is not compat.LOCAL_MEDIA_DEPENDENCIES
    for spec in compat.LOCAL_MEDIA_DEPENDENCIES:
        assert (spec.params, spec.min_positional, spec.dataclass_field) == (frozenset(), 2, None)
    floors = hermes_version.FEATURE_FLOORS
    assert floors["local_media"] is hermes_version._WRITE_FLOOR
    assert (floors["local_media"].semver, floors["local_media"].calver) == (
        (0, 21, 5),
        (2026, 9, 24, 0),
    )


# ---- A1: at or above the floor, all rows present: available, no list/manifest/SHA read ---------


@pytest.mark.parametrize("version", [SEMVER_FLOOR, CALVER_FLOOR])
def test_a1_available_at_the_floor_and_reads_no_build_list_manifest_or_fingerprint(
    version: HermesVersion, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []
    real_open = builtins.open

    def spy(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)  # `Path.read_text`/`read_bytes` go through `io.open`
    fingerprint_calls: list[Path] = []
    monkeypatch.setattr(
        compat.GitFingerprintReader, "read", lambda self, root: fingerprint_calls.append(root)
    )
    probe = Probe()
    # The approvals stream-hook diagnostic is a bounded read of one api_server file (spec 034, no
    # gate); stub it so the spy sees only what the media member and the version/probe path read.
    eligibility = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _root: version,
        probe=probe,
        evidence=lambda _root: {},
        hook_probe=lambda _root: None,
    )
    status = eligibility.features[MEDIA]
    assert status == FeatureStatus(True)
    assert "local_media" in probe.calls
    assert opened == [] and fingerprint_calls == []


def test_a1_the_default_evidence_matcher_never_labels_or_reads_for_the_media_member() -> None:
    assert MEDIA not in compat._EVIDENCE_FILES
    labels = compat.match_evidence(Path("/nonexistent-hermes-root"))
    assert MEDIA not in labels
    # Even when the evidence matcher claims every member is a tested sample, media stays unlabelled
    # and its availability is unchanged.
    tested = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _r: SEMVER_FLOOR,
        probe=Probe(),
        evidence=lambda _r: dict.fromkeys(SIBLINGS, "tested-sample"),
    )
    assert tested.features[MEDIA] == FeatureStatus(True)


def test_a1_no_media_code_path_references_a_manifest_or_build_list() -> None:
    names = {*compat._EVIDENCE_FILES.values()}
    assert not {n for n in names if "media" in n}
    source = Path(compat.__file__).read_text(encoding="utf-8")
    start = source.index("LOCAL_MEDIA_DEPENDENCIES: tuple")
    block = source[start : source.index("# Mobile jobs", start)]
    assert not re.search(r"json|manifest|fingerprint|git_sha|builds", block, re.IGNORECASE)


# ---- A2: unknown, 0.0.0, unlisted, newer and development versions are attempted ----------------


@pytest.mark.parametrize(
    "version", [UNKNOWN, SEMVER_UNLISTED, SEMVER_NEWER, CALVER_NEWER, CALVER_FLOOR]
)
def test_a2_unknown_unlisted_and_newer_versions_are_attempted(version: HermesVersion) -> None:
    probe = Probe()
    eligibility = evaluate(version, probe)
    assert eligibility.features[MEDIA] == FeatureStatus(True)
    assert "local_media" in probe.calls  # attempted, not refused on version grounds


@pytest.mark.parametrize(
    ("stamp", "literal", "release_date"),
    [
        ("0.0.0", None, None),  # Hermes's own placeholder
        ("0.21.5-dev", "0.21.5.dev0", None),  # a development tag: not a plain semver, so unknown
        (None, None, None),
        (None, "not-a-version", "not-a-date"),
    ],
)
def test_a2_placeholder_development_and_missing_metadata_are_attempted_through_the_real_reader(
    tmp_path: Path, stamp: str | None, literal: str | None, release_date: str | None
) -> None:
    root = tmp_path / "hermes-src"
    (root / "hermes_cli").mkdir(parents=True)
    if stamp is not None:
        (root / "install-stamp.json").write_text(json.dumps({"baseVersion": stamp}))
    body = ""
    if literal is not None:
        body += f"__version__ = {literal!r}\n"
    if release_date is not None:
        body += f"__release_date__ = {release_date!r}\n"
    (root / "hermes_cli" / "__init__.py").write_text(body)
    probe = Probe()
    eligibility = evaluate_eligibility(
        root_locator=lambda: root,
        version_reader=hermes_version.read_hermes_version,
        probe=probe,
        evidence=lambda _r: {},
    )
    assert eligibility.version.scheme is Scheme.UNKNOWN
    assert eligibility.features[MEDIA] == FeatureStatus(True)
    assert "local_media" in probe.calls


# ---- A3: below the floor: unavailable, floor checked before any media probe --------------------


@pytest.mark.parametrize("version", [SEMVER_OLD, SEMVER_READ_ONLY, CALVER_OLD])
def test_a3_below_the_floor_is_unavailable_and_its_rows_are_never_probed(
    version: HermesVersion,
) -> None:
    probe = Probe()
    eligibility = evaluate(version, probe)
    assert eligibility.features[MEDIA] == FeatureStatus(False, Unavailable.VERSION_BELOW_FLOOR)
    assert "local_media" not in probe.calls  # the floor decides before any media probe


def test_a3_a_below_floor_media_row_is_not_imported(tmp_path: Path) -> None:
    """With the real probe on a synthetic tree whose `hermes_state` would trip on import, a version
    below the media floor imports nothing for media (read-only release: read still probes)."""
    root = tmp_path / "hermes-src"
    root.mkdir()
    (root / "hermes_constants.py").write_text("")
    (root / "hermes_state.py").write_text("raise RuntimeError('imported')\n")
    for name in ("hermes_state",):
        sys.modules.pop(name, None)
    probed: list[tuple[str, ...]] = []

    def recording(root_: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
        probed.append(tuple(s.module for s in specs))
        return ()

    evaluate_eligibility(
        root_locator=lambda: root,
        version_reader=lambda _r: SEMVER_READ_ONLY,
        probe=recording,
        evidence=lambda _r: {},
    )
    assert ("hermes_state",) * 3 not in probed  # the media table was never handed to the probe
    assert "hermes_state" not in sys.modules


# ---- A4: a missing compression callable isolates media -----------------------------------------


def test_a4_a_missing_compression_row_closes_only_media_with_fixed_labels() -> None:
    eligibility = evaluate(SEMVER_FLOOR, Probe({"local_media": [LINEAGE]}))
    status = eligibility.features[MEDIA]
    assert (status.available, status.reason, status.missing) == (
        False,
        Unavailable.DEPENDENCY_MISSING,
        (LINEAGE,),
    )
    for feature in SIBLINGS:
        assert eligibility.features[feature] == FeatureStatus(True), feature


def test_a4_a_probe_failure_closes_only_media_and_keeps_no_exception_text() -> None:
    class Flaky(Probe):
        def __call__(self, root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
            if specs is compat.LOCAL_MEDIA_DEPENDENCIES:
                raise RuntimeError("canary exception text")
            return super().__call__(root, specs)

    eligibility = evaluate(SEMVER_FLOOR, Flaky())
    assert eligibility.features[MEDIA] == FeatureStatus(False, Unavailable.PROBE_FAILED)
    assert all(eligibility.available(f) for f in SIBLINGS)


def test_a4_each_sibling_table_missing_never_closes_media() -> None:
    for name in ("session_browsing", "send", "jobs", "model", "phone_chat"):
        eligibility = evaluate(SEMVER_FLOOR, Probe({name: ["x.y"]}))
        assert eligibility.features[MEDIA] == FeatureStatus(True), name


@pytest.fixture()
def synthetic_hermes(tmp_path: Path) -> Iterator[Path]:
    """A synthetic Hermes tree (`hermes_constants` marks the root) plus a sibling site-packages."""
    root = tmp_path / "hermes-src"
    root.mkdir()
    (root / "hermes_constants.py").write_text("")
    (tmp_path / "site-packages").mkdir()
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(tmp_path / "site-packages"))
    for name in ("hermes_state", "shadow_impl"):
        sys.modules.pop(name, None)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        sys.path.remove(str(tmp_path / "site-packages"))
        for name in ("hermes_state", "shadow_impl"):
            sys.modules.pop(name, None)


def _write_state(root: Path, body: str) -> None:
    (root / "hermes_state.py").write_text(textwrap.dedent(body))
    sys.modules.pop("hermes_state", None)


_COMPLETE = """
    class SessionDB:
        def get_session(self, session_id): ...
        def get_session_by_title(self, title): ...
        def get_compression_lineage(self, session_id): ...
"""


def test_a4_the_real_probe_passes_a_complete_synthetic_tree(synthetic_hermes: Path) -> None:
    _write_state(synthetic_hermes, _COMPLETE)
    assert compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.LOCAL_MEDIA_DEPENDENCIES
    ) == ()


def test_a4_the_real_probe_reports_only_the_absent_callable(synthetic_hermes: Path) -> None:
    _write_state(
        synthetic_hermes,
        """
        class SessionDB:
            def get_session(self, session_id): ...
            def get_session_by_title(self, title): ...
        """,
    )
    assert compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.LOCAL_MEDIA_DEPENDENCIES
    ) == (LINEAGE,)


def test_a4_a_callable_resolved_from_site_packages_is_missing(
    synthetic_hermes: Path,
) -> None:
    (synthetic_hermes.parent / "site-packages" / "shadow_impl.py").write_text(
        "def lineage(self, session_id): ...\n"
    )
    _write_state(
        synthetic_hermes,
        """
        from shadow_impl import lineage

        class SessionDB:
            def get_session(self, session_id): ...
            def get_session_by_title(self, title): ...
            get_compression_lineage = lineage
        """,
    )
    assert compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.LOCAL_MEDIA_DEPENDENCIES
    ) == (LINEAGE,)


def test_a4_native_rows_shared_with_send_are_probed_independently(
    synthetic_hermes: Path,
) -> None:
    """A genuinely absent shared API affects both tables; a media-only probe failure does not."""
    _write_state(
        synthetic_hermes,
        """
        class SessionDB:
            def get_session(self, session_id): ...
            def get_session_by_title(self, title): ...
        """,
    )
    shared = {s.label for s in compat.DIRECT_SEND_DEPENDENCIES} & set(MEDIA_LABELS)
    assert shared == set(MEDIA_LABELS)
    media_missing = compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.LOCAL_MEDIA_DEPENDENCIES
    )
    send_missing = compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.DIRECT_SEND_DEPENDENCIES
    )
    assert media_missing == (LINEAGE,)
    assert LINEAGE in send_missing


@pytest.mark.parametrize("label", MEDIA_LABELS)
@pytest.mark.parametrize("signature", ["self, **kwargs", "self, *, value", "self, *args"])
def test_a4_a_callable_without_the_positional_argument_is_missing(
    synthetic_hermes: Path, label: str, signature: str,
) -> None:
    method = label.rsplit(".", 1)[1]
    original = f"def {method}(self, "
    lines = _COMPLETE.splitlines()
    lines = [
        f"        def {method}({signature}): ..." if original in line else line
        for line in lines
    ]
    _write_state(synthetic_hermes, "\n".join(lines))
    assert compat.probe_dependencies(
        hermes_root=synthetic_hermes, specs=compat.LOCAL_MEDIA_DEPENDENCIES
    ) == (label,)


# ---- A5: send unavailable or the direct-send switch off never closes media ---------------------


def test_a5_send_closed_leaves_media_open() -> None:
    eligibility = evaluate(SEMVER_FLOOR, Probe({"send": [LINEAGE]}))
    assert eligibility.features[Feature.SEND].reason is Unavailable.DEPENDENCY_MISSING
    for member in (Feature.APPROVALS, Feature.PHONE_CHAT):
        assert eligibility.features[member].reason is Unavailable.REQUIRES_SEND
    assert eligibility.features[MEDIA] == FeatureStatus(True)  # no `requires_send`


def test_a5_send_and_session_browsing_both_closed_leave_media_open() -> None:
    eligibility = evaluate(
        SEMVER_FLOOR, Probe({"send": ["x.y"], "session_browsing": ["x.y"]})
    )
    assert eligibility.features[MEDIA] == FeatureStatus(True)


def test_a5_eligibility_takes_no_direct_send_switch_input() -> None:
    """The host's `direct_send.enabled` switch is not an eligibility input at all, so media can
    never depend on it: the evaluator's injectable seams are exactly these."""
    params = set(inspect.signature(evaluate_eligibility).parameters)
    assert params == {"root_locator", "version_reader", "probe", "evidence", "hook_probe"}
    source = Path(compat.__file__).read_text(encoding="utf-8")
    assert "direct_send.enabled" not in source and "REQUIRES_SEND" not in source.split(
        "_PROBE_TABLES"
    )[1].split("# Spec 034")[0]


# ---- A6: read core missing: requires_read, no media probe or import ----------------------------


def test_a6_missing_read_core_gives_requires_read_and_never_probes_media() -> None:
    probe = Probe({"read": ["gateway.run.GatewayRunner"]})
    eligibility = evaluate(SEMVER_NEWER, probe)
    assert eligibility.features[MEDIA] == FeatureStatus(False, Unavailable.REQUIRES_READ)
    assert eligibility.features[MEDIA].missing == ()
    assert probe.calls == ["read"]


def test_a6_a_failed_read_probe_also_gives_requires_read_with_no_media_probe() -> None:
    class Flaky(Probe):
        def __call__(self, root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
            if specs is compat.READ_CORE_DEPENDENCIES:
                raise RuntimeError("canary exception text")
            return super().__call__(root, specs)

    probe = Flaky()
    eligibility = evaluate(SEMVER_FLOOR, probe)
    assert eligibility.features[Feature.READ].reason is Unavailable.PROBE_FAILED
    assert eligibility.features[MEDIA] == FeatureStatus(False, Unavailable.REQUIRES_READ)
    assert probe.calls == []


def test_a6_the_compat_result_still_reflects_read_alone() -> None:
    def gate(missing: Mapping[str, Sequence[str]]) -> CompatResult:
        return compat.CompatGate(
            root_locator=lambda: Path("/nonexistent-hermes-root"),
            version_reader=lambda _r: SEMVER_FLOOR,
            probe=Probe(missing),
            evidence=lambda _r: {},
        ).evaluate()

    assert gate({"local_media": [LINEAGE]}).status is CompatStatus.SUPPORTED
    assert gate({"read": ["a.b"]}).status is CompatStatus.UNSUPPORTED


# ---- compat output through the existing CLI layout ---------------------------------------------

CANARIES = (
    "canary-profile-name",
    "hmpd_canary_device_id",
    "/canary/hermes-home/path",
    "canary-host.internal",
    "sk-canary-api-key",
    "canary exception text",
)


def _eligibility(
    version: HermesVersion = CALVER_FLOOR,
    failed: dict[Feature, tuple[Unavailable, tuple[str, ...]]] | None = None,
) -> Eligibility:
    failed = failed or {}
    return Eligibility(
        version,
        "0123456789abcdef0123456789abcdef01234567",
        {
            f: (FeatureStatus(False, *failed[f]) if f in failed else FeatureStatus(True))
            for f in Feature
        },
    )


class Run:
    def __init__(self, el: Eligibility) -> None:
        read = el.features[Feature.READ]
        self.result = (
            CompatResult(CompatStatus.SUPPORTED, eligibility=el)
            if read.available
            else CompatResult(CompatStatus.UNSUPPORTED, compat.read_why(read), eligibility=el)
        )
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
    def boom(*_a: Any, **_k: Any) -> None:
        raise AssertionError("network use is forbidden")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)


def test_compat_output_lists_the_member_and_its_floor_in_the_existing_layout() -> None:
    run = Run(_eligibility())
    assert run() == 0
    assert "local_media: available" in run.out
    assert (
        "send, jobs, model, approvals, phone chat and local media 0.21.5 (2026.9.24)" in run.out
    )
    # The member appears after the existing ones, on its own line, in `Feature` order.
    lines = [line for line in run.out.splitlines() if line.endswith(": available")]
    assert [line.split(":")[0] for line in lines] == [f.value for f in Feature]


def test_compat_output_names_only_the_fixed_label_for_a_missing_row() -> None:
    el = _eligibility(
        failed={MEDIA: (Unavailable.DEPENDENCY_MISSING, (LINEAGE, "canary/evil/path"))}
    )
    run = Run(el)
    assert run() == 0
    assert f"local_media: unavailable (dependency_missing: {LINEAGE})" in run.out
    assert "canary" not in run.out
    assert "read: available" in run.out and "send: available" in run.out


# ---- A13: offline issue draft: `media_unavailable` is the only reportable media code -----------

DRAFT_ARGV = ("--issue-draft", "--feature", "local_media", "--failure-code", "media_unavailable")
_REF_LIKE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])")
_DIGEST_LIKE = re.compile(r"[0-9a-f]{64}")


def test_a13_media_unavailable_makes_a_bounded_reviewed_offline_draft() -> None:
    run = Run(_eligibility())
    assert run(*DRAFT_ARGV) == 0
    out = run.out
    assert out.startswith("Title: HMP: local_media failure (media_unavailable), Hermes 2026.9.24")
    assert "- reported_feature: local_media" in out
    assert "- reported_failure_code: media_unavailable" in out
    assert "- report_origin: operator" in out
    assert "Reported by the operator, not automatically observed" in out
    assert "HMP did not observe the failure" in out
    assert issue_draft.REVIEW_LINE in out and issue_draft.PASTE_LINE in out
    assert "Observed by HMP" not in out  # nothing was statically observed
    assert run.stderr.getvalue() == ""


def test_a13_the_draft_leaks_no_path_ref_digest_profile_device_or_environment_value() -> None:
    el = _eligibility(
        failed={MEDIA: (Unavailable.DEPENDENCY_MISSING, (LINEAGE, *CANARIES))}
    )
    run = Run(el)
    assert run(*DRAFT_ARGV) == 0
    for canary in CANARIES:
        assert canary not in run.out
        assert canary not in run.stderr.getvalue()
    assert _REF_LIKE.search(run.out) is None
    assert _DIGEST_LIKE.search(run.out) is None
    assert "/private" not in run.out and "/Users" not in run.out
    # An observed missing row appears only as HMP's own fixed label.
    assert f"missing: {LINEAGE}" in run.out and "reason: dependency_missing" in run.out


def test_a13_a_dependency_label_from_another_feature_is_dropped_for_media() -> None:
    other = "hermes_state.SessionDB.list_sessions_rich"  # a session-browsing label
    el = _eligibility(failed={MEDIA: (Unavailable.DEPENDENCY_MISSING, (other,))})
    run = Run(el)
    assert run("--issue-draft") == 0
    assert other not in run.out
    assert "- feature: local_media" in run.out and "missing: none" in run.out
    assert "Title: HMP: local_media unavailable on this Hermes, Hermes 2026.9.24" in run.out


@pytest.mark.parametrize(
    "code", ["not_found", "forbidden", "unauthorized", "not_routed", "revoked"]
)
def test_a13_permission_and_routing_outcomes_are_explained_and_never_drafted(code: str) -> None:
    run = Run(_eligibility())
    assert run("--issue-draft", "--feature", "local_media", "--failure-code", code) == 0
    assert f"`{code}` on local_media is a permission, routing or setting outcome" in run.out
    assert "No issue draft was prepared" in run.out
    assert "Title:" not in run.out and "reported_feature" not in run.out


@pytest.mark.parametrize(
    "code",
    [
        "write_gate_closed",  # a sibling's code
        "cron_unavailable",
        "other",
        "bad_request",
        "canary exception text",
        "",
    ],
)
def test_a13_every_other_code_is_refused_without_echo(code: str) -> None:
    run = Run(_eligibility())
    assert run("--issue-draft", "--feature", "local_media", "--failure-code", code) == (
        cli.EXIT_ENVIRONMENT
    )
    assert run.out == ""
    error = run.stderr.getvalue()
    assert error.startswith("hermes hmp: refused:")
    assert not code or code not in error.replace("local_media", "")


def test_a13_media_unavailable_is_not_reportable_for_any_other_feature() -> None:
    for feature in issue_draft.FEATURES:
        if feature == "local_media":
            continue
        run = Run(_eligibility())
        argv = ("--issue-draft", "--feature", feature, "--failure-code", "media_unavailable")
        assert run(*argv) == cli.EXIT_ENVIRONMENT, feature
        assert run.out == ""


def test_a13_the_reportable_set_for_media_is_exactly_media_unavailable() -> None:
    assert issue_draft.REPORTABLE_CODES["local_media"] == frozenset({"media_unavailable"})
    assert "local_media" in issue_draft.FEATURES
    report = issue_draft.check_report_request("local_media", "media_unavailable")
    assert isinstance(report, issue_draft.OperatorReport)
    assert isinstance(
        issue_draft.check_report_request("local_media", "not_found"), issue_draft.OwnReason
    )
    assert isinstance(
        issue_draft.check_report_request("local_media", "rate_limited"), issue_draft.OwnReason
    )


def test_a13_a_declared_report_does_not_change_availability_or_claim_attestation() -> None:
    """The CLI is offline: it cannot attest that an owner device with the flag on saw the error. The
    draft states it is the operator's report and does not alter the computed eligibility."""
    el = _eligibility()
    before = {f: el.features[f] for f in Feature}
    run = Run(el)
    assert run(*DRAFT_ARGV) == 0
    assert {f: el.features[f] for f in Feature} == before
    lowered = run.out.lower()
    for claim in ("verified", "attested", "owner device", "flag on", "confirmed"):
        assert claim not in lowered
    assert "report_origin: operator" in run.out


def test_the_help_text_lists_the_member_as_a_feature_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = argparse.ArgumentParser(prog="hermes hmp")
    cli.setup_parser(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["compat", "--help"])
    assert "local_media" in " ".join(capsys.readouterr().out.split())


def test_a13_rate_limit_has_its_own_explanation_without_a_draft_or_retry() -> None:
    run = Run(_eligibility())
    assert run("--issue-draft", "--feature", "local_media", "--failure-code", "rate_limited") == 0
    assert "is a rate-limit outcome" in run.out
    assert "No issue draft was prepared" in run.out
    assert "does not retry" in run.out
    assert "permission, routing" not in run.out
    assert "Title:" not in run.out and "reported_feature" not in run.out
    assert run.stderr.getvalue() == ""
    for feature in issue_draft.FEATURES:
        if feature != "local_media":
            with pytest.raises(issue_draft.ReportRequestError):
                issue_draft.check_report_request(feature, "rate_limited")
