"""The jobs fixture's test-only build admission edits a scratch plugin copy and nothing else."""

from __future__ import annotations

import json
from pathlib import Path

import _fixture_common as fc
import direct_send_fixture as dsf
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_MANIFEST = REPO_ROOT / "server" / "hmp_plugin" / "mobile_cron_supported_builds.json"


def _instance(tmp_path: Path) -> tuple[fc.BuildInfo, fc.InstancePaths, Path]:
    files = json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))["bridge_files"]
    src = tmp_path / "build" / "src"
    for rel in files:
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"# {rel}\n", encoding="utf-8")
    out = tmp_path / "out"
    scratch = out / "_hmp_plugin"
    scratch.mkdir(parents=True)
    (scratch / "mobile_cron_supported_builds.json").write_text(
        PRODUCTION_MANIFEST.read_text(encoding="utf-8"), encoding="utf-8"
    )
    home = out / "A" / "home"
    (home / "plugins").mkdir(parents=True)
    (home / "plugins" / "hmp").symlink_to(scratch)
    build = fc.BuildInfo(label="x", src_dir=src, venv_python=src / "python")
    paths = fc.InstancePaths(home=home, xdg_state=out / "A" / "xdg", out_dir=out)
    return build, paths, scratch / "mobile_cron_supported_builds.json"


def test_admission_is_one_test_only_entry_and_closing_empties_the_list(tmp_path: Path) -> None:
    before = PRODUCTION_MANIFEST.read_bytes()
    build, paths, manifest = _instance(tmp_path)

    dsf.set_jobs_test_admission(build, paths, admitted=True)
    entries = json.loads(manifest.read_text(encoding="utf-8"))["builds"]
    assert [e["label"] for e in entries] == [dsf.JOBS_TEST_ADMISSION_LABEL]
    assert "test-only" in entries[0]["qualified_by"]

    # Admitted entry is accepted by the real gate for this tree, and a small change closes it.
    from hmp_plugin import mobile_cron

    assert mobile_cron.qualified_build(root=build.src_dir, builds_path=manifest)
    changed = build.src_dir / "cron" / "jobs.py"
    changed.write_text(changed.read_text(encoding="utf-8") + "#\n", encoding="utf-8")
    assert not mobile_cron.qualified_build(root=build.src_dir, builds_path=manifest)

    dsf.set_jobs_test_admission(build, paths, admitted=False)
    assert json.loads(manifest.read_text(encoding="utf-8"))["builds"] == []
    assert PRODUCTION_MANIFEST.read_bytes() == before


def test_admission_refuses_a_plugin_dir_outside_the_scratch_out_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build, paths, _ = _instance(tmp_path)
    elsewhere = fc.InstancePaths(
        home=paths.home, xdg_state=paths.xdg_state, out_dir=tmp_path / "another-out"
    )
    with pytest.raises(fc.FixtureSafetyError):
        dsf.set_jobs_test_admission(build, elsewhere, admitted=True)
    # Point the link at an owned COPY of the tracked plugin dir: were the guard to regress, the
    # write would land in the copy, never in the tracked manifest.
    # The copy stands in for the tracked tree (`SERVER_DIR`) and `--out` encloses it, so only the
    # "under server/" branch of the guard can refuse it.
    monkeypatch.setattr(fc, "SERVER_DIR", tmp_path / "tracked-copy" / "server")
    tracked = fc.InstancePaths(
        home=paths.home, xdg_state=paths.xdg_state, out_dir=tmp_path / "tracked-copy"
    )
    tracked_copy = tmp_path / "tracked-copy" / "server" / "hmp_plugin"
    tracked_copy.mkdir(parents=True)
    copied = tracked_copy / "mobile_cron_supported_builds.json"
    copied.write_bytes(PRODUCTION_MANIFEST.read_bytes())
    (paths.home / "plugins" / "hmp").unlink()
    (paths.home / "plugins" / "hmp").symlink_to(tracked_copy)
    before = PRODUCTION_MANIFEST.read_bytes()
    with pytest.raises(fc.FixtureSafetyError):
        dsf.set_jobs_test_admission(build, tracked, admitted=True)
    assert copied.read_bytes() == before
    assert PRODUCTION_MANIFEST.read_bytes() == before


def test_candidate_label_is_opt_in_unique_and_harmless(tmp_path: Path) -> None:
    defaults = ("stock-base", "experimental", "owner-local")
    (tmp_path / "cand-1.0" / "src").mkdir(parents=True)
    (tmp_path / "owner-local" / "src").mkdir(parents=True)
    (tmp_path / "nosrc").mkdir()
    pick = lambda label: dsf.candidate_build_labels(label, str(tmp_path), defaults)  # noqa: E731

    assert pick("cand-1.0") == ("cand-1.0",)
    assert pick("") == ()  # not opted in
    assert dsf.candidate_build_labels("cand-1.0", "", defaults) == ()
    assert pick("owner-local") == ()  # a default label is never re-added or aliased
    assert pick("nosrc") == ()  # src must be extracted
    for bad in ("../cand-1.0", "cand-1.0/", "a..b", "-x", ".x", "x y", str(tmp_path / "cand-1.0")):
        assert pick(bad) == (), bad
