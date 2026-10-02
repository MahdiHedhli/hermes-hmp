"""`build_fixture.require_read_eligible`: the fixture builder asks the production minimum-version
read gate (`compat.default_gate()` via `fixture_seed.py compat-identity`) whether a build serves
reads. It neither requires a fingerprint (identity is null for an eligible build) nor writes any
per-build manifest. Pure unit tests: the production gate runs in-process with injected fakes, and
no Hermes build, gateway or network is touched."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import _fixture_common as fc
import build_fixture as bf
import fixture_seed as fs
import pytest

from hmp_plugin import compat
from hmp_plugin.hermes_version import HermesVersion, Scheme, VersionSource

BELOW_FLOOR = HermesVersion(Scheme.SEMVER, (0, 21, 3), VersionSource.LITERAL)
NEWER = HermesVersion(Scheme.SEMVER, (0, 99, 0), VersionSource.LITERAL)
BUILD = fc.BuildInfo(
    label="synthetic", src_dir=Path("/nonexistent"), venv_python=Path(sys.executable)
)
SECRET = "sk-synthetic-child-supplied-value"


def _gate_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *, version, missing=()
) -> str:
    """Run the real `cmd_compat_identity` over the real `CompatGate`, with only the Hermes-facing
    readers injected, and return what the child would print."""
    monkeypatch.setattr(
        compat,
        "default_gate",
        lambda: compat.CompatGate(
            root_locator=lambda: Path("/synthetic-hermes-root"),
            version_reader=lambda root: version,
            probe=lambda root, table: tuple(missing),
            evidence=lambda root: {},
            hook_probe=lambda root: None,
        ),
    )
    fs.cmd_compat_identity(SimpleNamespace())
    return capsys.readouterr().out


def _seed_returns(monkeypatch: pytest.MonkeyPatch, stdout: str) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    def fake(build, script, *args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(fc, "run_seed_script", fake)
    return calls


def _snapshot(root: Path) -> dict[str, bytes]:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return {str(p.relative_to(root)): p.read_bytes() for p in files}


def test_eligible_build_with_no_fingerprint_passes_and_writes_nothing(
    tmp_path, monkeypatch, capsys
) -> None:
    out = _gate_answer(monkeypatch, capsys, version=NEWER)
    answer = json.loads(out)
    assert answer["supported"] is True and answer["fingerprint"] is None  # the evidence flow
    assert answer["read_reason"] is None and answer["read_missing"] == []

    plugin_copy = bf.refresh_fixture_plugin_copy(tmp_path)
    compat_file = plugin_copy / "read_compat_builds.json"
    data = json.loads(compat_file.read_text(encoding="utf-8"))
    data["builds"] = []  # an empty (unlisted) manifest
    compat_file.write_text(json.dumps(data), encoding="utf-8")
    before = _snapshot(tmp_path)

    calls = _seed_returns(monkeypatch, out)
    bf.require_read_eligible(BUILD)

    assert calls == [("compat-identity",)]
    assert _snapshot(tmp_path) == before
    assert json.loads(compat_file.read_text(encoding="utf-8"))["builds"] == []


def test_below_the_minimum_version_fails_closed_with_a_fixed_reason(
    monkeypatch, capsys
) -> None:
    out = _gate_answer(monkeypatch, capsys, version=BELOW_FLOOR)
    answer = json.loads(out)
    assert answer["supported"] is False
    assert answer["read_reason"] == compat.Unavailable.VERSION_BELOW_FLOOR.value
    _seed_returns(monkeypatch, out)
    with pytest.raises(fc.FixtureSafetyError, match="hermes_version_below_floor"):
        bf.require_read_eligible(BUILD)


def test_a_missing_read_api_fails_closed_without_echoing_labels(monkeypatch, capsys) -> None:
    out = _gate_answer(monkeypatch, capsys, version=NEWER, missing=("synthetic.read_helper",))
    answer = json.loads(out)
    assert answer["supported"] is False
    assert answer["read_reason"] == compat.Unavailable.DEPENDENCY_MISSING.value
    _seed_returns(monkeypatch, out)
    with pytest.raises(fc.FixtureSafetyError, match=r"dependency_missing \(1 missing") as raised:
        bf.require_read_eligible(BUILD)
    assert "synthetic.read_helper" not in str(raised.value)


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "not json",
        "[]",
        "null",
        '{"ok": false, "error": "x"}',
        '{"ok": true}',
        '{"ok": true, "supported": "true"}',
        '{"ok": true, "supported": 1}',
        '{"supported": true}',
    ],
)
def test_malformed_or_incomplete_helper_output_fails_closed(monkeypatch, stdout) -> None:
    _seed_returns(monkeypatch, stdout)
    with pytest.raises(fc.FixtureSafetyError):
        bf.require_read_eligible(BUILD)


def test_child_supplied_reason_text_is_never_echoed(monkeypatch) -> None:
    answer = {"ok": True, "supported": False, "read_reason": SECRET, "read_missing": [SECRET * 20]}
    _seed_returns(monkeypatch, json.dumps(answer))
    with pytest.raises(fc.FixtureSafetyError) as raised:
        bf.require_read_eligible(BUILD)
    assert SECRET not in str(raised.value)
    assert "unknown" in str(raised.value)


def test_a_failing_helper_process_fails_closed(tmp_path, monkeypatch) -> None:
    stub = tmp_path / "stub_seed.py"
    stub.write_text("import sys; sys.exit(3)\n", encoding="utf-8")
    monkeypatch.setattr(bf, "FIXTURE_SEED", stub)
    with pytest.raises(RuntimeError):
        bf.require_read_eligible(BUILD)


def test_the_legacy_fingerprint_bootstrap_is_gone() -> None:
    assert not hasattr(bf, "bootstrap_compat_entry")
    assert not hasattr(bf, "_resolve_source_sha")


def _main_with_stubs(tmp_path, monkeypatch, *, eligible: bool) -> list[str]:
    events: list[str] = []
    monkeypatch.setattr(fc, "assert_outside_real_home", lambda *a, **k: None)
    monkeypatch.setattr(
        fc, "load_and_validate_manifest", lambda *a, **k: {"instances": [{"key": "A"}]}
    )
    monkeypatch.setattr(fc, "resolve_build", lambda *a, **k: BUILD)
    monkeypatch.setattr(fc, "ensure_runtime_deps", lambda *a, **k: None)
    monkeypatch.setattr(bf, "refresh_fixture_plugin_copy", lambda out: tmp_path)

    def gate(build):
        events.append("gate")
        if not eligible:
            raise fc.FixtureSafetyError("not read-eligible")

    monkeypatch.setattr(bf, "require_read_eligible", gate)
    monkeypatch.setattr(
        bf, "build_instance_if_needed", lambda *a, **k: events.append("build") or {"key": "A"}
    )
    monkeypatch.setattr(bf, "write_fixture_meta", lambda *a, **k: events.append("meta"))
    return events


def test_main_builds_nothing_when_the_build_is_not_read_eligible(tmp_path, monkeypatch) -> None:
    events = _main_with_stubs(tmp_path, monkeypatch, eligible=False)
    with pytest.raises(fc.FixtureSafetyError):
        bf.main(["--build", "b", "--out", str(tmp_path / "out"), "--builds-dir", str(tmp_path)])
    assert events == ["gate"]


def test_main_builds_after_the_gate_when_eligible(tmp_path, monkeypatch, capsys) -> None:
    events = _main_with_stubs(tmp_path, monkeypatch, eligible=True)
    code = bf.main(["--build", "b", "--out", str(tmp_path / "out"), "--builds-dir", str(tmp_path)])
    assert code == 0 and events == ["gate", "build", "meta"]
