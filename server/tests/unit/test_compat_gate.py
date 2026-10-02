"""Minimum-version eligibility (owner policy 2026-10-01; GU-2, GU-2c, ERR-2a).

`evaluate_eligibility` reads the version from files, refuses only a version that declares itself
below a feature's floor (importing nothing), and otherwise probes each feature's own Hermes
dependencies. A tested-sample match is evidence and never changes availability. The version
reader, probe and evidence matcher are injected here; their real implementations are covered in
`test_hermes_version.py` and `test_compat.py`.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest

from hmp_plugin import compat
from hmp_plugin.compat import (
    CompatGate,
    CompatStatus,
    DependencySpec,
    Feature,
    Unavailable,
    evaluate_eligibility,
    locate_hermes_root,
)
from hmp_plugin.contract import OtherWhy
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource

HERMES_TOP_LEVEL = ("hermes_constants", "gateway", "hermes_state")

SEMVER_OLD = HermesVersion(Scheme.SEMVER, (0, 21, 3), VersionSource.LITERAL)
SEMVER_READ_ONLY = HermesVersion(Scheme.SEMVER, (0, 21, 4), VersionSource.LITERAL)
SEMVER_FLOOR = HermesVersion(Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL)
SEMVER_NEWER = HermesVersion(Scheme.SEMVER, (0, 99, 0), VersionSource.LITERAL)
CALVER_CA705 = HermesVersion(Scheme.CALVER, (2026, 9, 24, 0), VersionSource.RELEASE_DATE)
UNKNOWN = HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN)

TABLES: Mapping[str, Sequence[DependencySpec]] = {
    "read": compat.READ_CORE_DEPENDENCIES,
    "session_browsing": compat.SESSION_BROWSING_DEPENDENCIES,
    "send": compat.DIRECT_SEND_DEPENDENCIES,
    "jobs": compat.CRON_DEPENDENCIES,
    "model": compat.MODEL_DEPENDENCIES,
}


@pytest.fixture()
def fake_hermes(tmp_path: Path) -> Iterator[Path]:
    """A synthetic, importable Hermes tree on sys.path."""
    root = tmp_path / "hermes-src"
    (root / "gateway").mkdir(parents=True)
    stub = "LOADED = True\n"
    (root / "hermes_constants.py").write_text(stub)
    (root / "hermes_state.py").write_text(stub)
    (root / "gateway" / "__init__.py").write_text(stub)
    (root / "gateway" / "run.py").write_text(stub)
    sys.path.insert(0, str(root))
    for name in HERMES_TOP_LEVEL:
        sys.modules.pop(name, None)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        for name in list(sys.modules):
            if name.split(".")[0] in HERMES_TOP_LEVEL:
                del sys.modules[name]


class Probe:
    """Records which table each call asked about; imports a Hermes module like the real one."""

    def __init__(
        self, missing: Mapping[str, Sequence[str]] | None = None, *, imports: bool = False
    ) -> None:
        self.calls: list[str] = []
        self.missing = missing or {}
        self.imports = imports  # only with the `fake_hermes` tree on sys.path

    def __call__(self, _root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
        name = next(k for k, v in TABLES.items() if v is specs)
        self.calls.append(name)
        if self.imports:
            importlib.import_module("gateway.run")
        return self.missing.get(name, ())


def _hermes_modules() -> set[str]:
    return {m for m in sys.modules if m.split(".")[0] in HERMES_TOP_LEVEL}


def evaluate(
    version: HermesVersion = SEMVER_FLOOR,
    probe: Probe | None = None,
    *,
    evidence: Mapping[Feature, str | None] | None = None,
    root: Path | None = Path("/nonexistent-hermes-root"),
) -> compat.Eligibility:
    return evaluate_eligibility(
        root_locator=lambda: root,
        version_reader=lambda _root: version,
        probe=probe or Probe(),
        evidence=lambda _root: evidence or {},
    )


def test_locate_root_imports_nothing(fake_hermes: Path) -> None:
    before = set(sys.modules)
    assert locate_hermes_root() == fake_hermes
    assert set(sys.modules) == before


def test_e1_below_read_floor_refuses_everything_and_imports_no_hermes_module(
    fake_hermes: Path,
) -> None:
    before = set(sys.modules)
    probe = Probe(imports=True)
    eligibility = evaluate(SEMVER_OLD, probe, root=fake_hermes)
    assert not any(eligibility.available(f) for f in Feature)
    assert eligibility.features[Feature.READ].reason is Unavailable.VERSION_BELOW_FLOOR
    assert probe.calls == []
    assert _hermes_modules() == set()
    assert set(sys.modules) - before == set()


def test_read_only_release_serves_read_and_browsing_but_not_the_write_features() -> None:
    probe = Probe()
    eligibility = evaluate(SEMVER_READ_ONLY, probe)
    assert eligibility.available(Feature.READ)
    assert eligibility.available(Feature.SESSION_BROWSING)
    for feature in (Feature.SEND, Feature.JOBS, Feature.MODEL):
        assert eligibility.features[feature].reason is Unavailable.VERSION_BELOW_FLOOR
    assert probe.calls == ["read", "session_browsing"]  # below-floor features are not probed


@pytest.mark.parametrize("version", [SEMVER_FLOOR, SEMVER_NEWER, CALVER_CA705, UNKNOWN])
def test_e2_e3_unlisted_newer_and_unknown_versions_are_attempted(
    fake_hermes: Path, version: HermesVersion
) -> None:
    """The old unlisted-build refusal is inverted: a passing probe is enough."""
    probe = Probe(imports=True)
    eligibility = evaluate(version, probe, root=fake_hermes, evidence={})
    assert "gateway.run" in sys.modules
    assert all(eligibility.available(f) for f in Feature)
    assert probe.calls == ["read", "session_browsing", "send", "jobs", "model"]


def test_e3_unknown_version_closes_only_the_feature_whose_probe_fails() -> None:
    eligibility = evaluate(UNKNOWN, Probe({"model": ["hermes_cli.config.load_config"]}))
    assert eligibility.available(Feature.READ)
    assert eligibility.available(Feature.SEND)
    assert eligibility.available(Feature.JOBS)
    model = eligibility.features[Feature.MODEL]
    assert (model.available, model.reason) == (False, Unavailable.DEPENDENCY_MISSING)
    assert model.missing == ("hermes_cli.config.load_config",)


def test_e6_e7_e8_each_write_feature_fails_alone() -> None:
    for broken, expected_open in (
        ("jobs", {Feature.READ, Feature.SESSION_BROWSING, Feature.SEND, Feature.MODEL}),
        ("model", {Feature.READ, Feature.SESSION_BROWSING, Feature.SEND, Feature.JOBS}),
        ("send", {Feature.READ, Feature.SESSION_BROWSING, Feature.JOBS, Feature.MODEL}),
        ("session_browsing", {Feature.READ, Feature.SEND, Feature.JOBS, Feature.MODEL}),
    ):
        eligibility = evaluate(SEMVER_FLOOR, Probe({broken: ["x.y"]}))
        assert {f for f in Feature if eligibility.available(f)} == expected_open, broken


def test_missing_get_session_disables_send_and_browsing_but_not_core_jobs_or_model() -> None:
    """`bridge.resolve_bot_chat` (send) walks the compression chain with `SessionDB.get_session`,
    so both send and session browsing need it; read core, jobs and model do not."""
    label = "hermes_state.SessionDB.get_session"

    class ByLabel(Probe):
        def __call__(self, root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
            super().__call__(root, specs)
            return tuple(
                f"{s.module}.{s.qualname}"
                for s in specs
                if f"{s.module}.{s.qualname}" == label
            )

    eligibility = evaluate(SEMVER_FLOOR, ByLabel())
    assert {f for f in Feature if eligibility.available(f)} == {
        Feature.READ, Feature.JOBS, Feature.MODEL,
    }
    for feature in (Feature.SEND, Feature.SESSION_BROWSING):
        status = eligibility.features[feature]
        assert (status.reason, status.missing) == (Unavailable.DEPENDENCY_MISSING, (label,))


def test_e9_missing_core_read_dependency_requires_read_for_everything_else() -> None:
    probe = Probe({"read": ["gateway.run.GatewayRunner"]})
    eligibility = evaluate(SEMVER_NEWER, probe)
    read = eligibility.features[Feature.READ]
    assert (read.available, read.reason) == (False, Unavailable.DEPENDENCY_MISSING)
    assert read.missing == ("gateway.run.GatewayRunner",)
    for feature in Feature:
        if feature is not Feature.READ:
            assert eligibility.features[feature].reason is Unavailable.REQUIRES_READ
    assert probe.calls == ["read"]


def test_a_probe_exception_closes_only_that_feature() -> None:
    class Flaky(Probe):
        def __call__(self, root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
            if specs is compat.CRON_DEPENDENCIES:
                raise RuntimeError("secret-looking exception text")
            return super().__call__(root, specs)

    eligibility = evaluate(SEMVER_FLOOR, Flaky())
    assert eligibility.features[Feature.JOBS].reason is Unavailable.PROBE_FAILED
    assert eligibility.features[Feature.JOBS].missing == ()  # exception text is never kept
    assert eligibility.available(Feature.READ) and eligibility.available(Feature.MODEL)


def test_no_root_makes_everything_unavailable() -> None:
    eligibility = evaluate(root=None)
    assert {st.reason for st in eligibility.features.values()} == {Unavailable.HERMES_NOT_FOUND}
    assert eligibility.version.scheme is Scheme.UNKNOWN


def test_a_broken_locator_or_version_reader_fails_closed_without_raising() -> None:
    def broken_locator() -> Path:
        raise OSError("x")

    gone = evaluate_eligibility(root_locator=broken_locator)
    assert not gone.available(Feature.READ)

    def broken_reader(_root: Path) -> HermesVersion:
        raise RuntimeError("x")

    unknown = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=broken_reader,
        probe=Probe(),
        evidence=lambda _r: {},
    )
    assert unknown.version.scheme is Scheme.UNKNOWN and unknown.available(Feature.READ)


@pytest.mark.parametrize("version", [SEMVER_FLOOR, UNKNOWN, SEMVER_READ_ONLY])
def test_e11_evidence_never_changes_availability(version: HermesVersion) -> None:
    missing = {"jobs": ["a.b"]}
    tested = evaluate(version, Probe(missing), evidence=dict.fromkeys(Feature, "tested-sample"))
    untested = evaluate(version, Probe(missing), evidence={})
    broken = evaluate_eligibility(
        root_locator=lambda: Path("/nonexistent-hermes-root"),
        version_reader=lambda _r: version,
        probe=Probe(missing),
        evidence=lambda _r: (_ for _ in ()).throw(RuntimeError("x")),
    )
    for feature in Feature:
        assert tested.available(feature) == untested.available(feature) == broken.available(feature)
    assert tested.features[Feature.READ].tested_label == "tested-sample"
    assert untested.features[Feature.READ].tested_label is None


def test_the_feature_set_has_no_media_or_approval_member() -> None:
    assert {f.value for f in Feature} == {"read", "session_browsing", "send", "jobs", "model"}


def test_gate_result_maps_to_the_existing_err_2a_values(fake_hermes: Path) -> None:
    def gate(version: HermesVersion, probe: Probe | None = None, root: Path | None = fake_hermes):
        return CompatGate(
            root_locator=lambda: root,
            version_reader=lambda _r: version,
            probe=probe or Probe(),
            evidence=lambda _r: {},
        ).evaluate()

    ok = gate(SEMVER_FLOOR)
    assert ok.supported and ok.why is None and ok.eligibility is not None
    assert (gate(SEMVER_OLD).status, gate(SEMVER_OLD).why) == (
        CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED,
    )
    assert gate(UNKNOWN, root=None).why is OtherWhy.HERMES_BUILD_UNSUPPORTED
    assert gate(UNKNOWN, Probe({"read": ["a.b"]})).why is OtherWhy.HERMES_READ_DEPENDENCY_MISSING


def test_default_gate_evidence_path_never_changes_availability(
    tmp_path: Path, fake_hermes: Path
) -> None:
    """The synthetic tree has none of Hermes's real internals, so the real probe fails closed;
    the point is that pointing evidence at another list changes nothing about that outcome."""
    (tmp_path / "builds.json").write_text(
        '{"format": 1, "bridge_files": [], "builds": []}', encoding="utf-8"
    )
    plain = compat.default_gate().evaluate()
    pointed = compat.default_gate(read_compat_path=tmp_path / "builds.json").evaluate()
    assert plain.status is pointed.status and plain.why is pointed.why
    assert plain.eligibility is not None and pointed.eligibility is not None
    for feature in Feature:
        assert plain.eligibility.available(feature) == pointed.eligibility.available(feature)


def test_e12_eligibility_hashes_nothing_after_it_has_been_computed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The result is a plain value computed once; reading it later touches no file."""
    eligibility = evaluate(SEMVER_FLOOR)
    reads: list[Path] = []
    monkeypatch.setattr(
        compat.GitFingerprintReader, "read", lambda self, root: reads.append(root)
    )
    assert eligibility.available(Feature.JOBS) and eligibility.available(Feature.MODEL)
    assert reads == []


def test_compat_module_source_never_names_bridge() -> None:
    src = (Path(__file__).resolve().parents[2] / "hmp_plugin" / "compat.py").read_text()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith(("#", '"')))
    assert "import bridge" not in code and ".bridge" not in code
