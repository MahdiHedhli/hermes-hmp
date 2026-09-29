"""The release watcher makes no network calls in these tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import watch_releases as watch


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_release_inventory_detects_new_tag_and_missing_bridge_files(tmp_path: Path) -> None:
    repo = tmp_path / "hermes"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci@example.invalid")
    _git(repo, "config", "user.name", "CI")
    (repo / "hermes_constants.py").write_text("old\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    _git(repo, "tag", watch.BASELINE_TAG)

    bridge_files = json.loads(watch.COMPAT.read_text(encoding="utf-8"))["bridge_files"]
    for rel in bridge_files:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {rel}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "new release")
    _git(repo, "tag", "-a", "v2026.10.1", "-m", "release")

    releases = [
        {"tag_name": watch.BASELINE_TAG, "published_at": "2026-08-31T00:00:00Z"},
        {"tag_name": "v2026.10.1", "published_at": "2026-10-01T00:00:00Z"},
    ]
    report = watch.build_report(repo, releases)
    assert report["latest_tag"] == "v2026.10.1"
    assert report["unreviewed_tags"] == ["v2026.10.1"]
    assert report["releases"][0]["status"] == "bridge_files_missing"
    assert report["releases"][1]["status"] == "unlisted_fingerprint"
    assert len(report["releases"][1]["fingerprint"]) == 64
    refs = watch.remote_tag_shas(str(repo))
    inventory = watch.build_report(None, releases, source_audit=False, refs=refs)
    assert inventory["releases"][0]["status"] == "retagged"
    assert inventory["releases"][1]["status"] == "new_release"
    assert inventory["unreviewed_tags"] == [watch.BASELINE_TAG, "v2026.10.1"]


def test_missing_baseline_refuses_partial_audit() -> None:
    try:
        watch.select_releases([{"tag_name": "v2026.10.1", "published_at": "2026-10-01T00:00:00Z"}])
    except ValueError as exc:
        assert "baseline release" in str(exc)
    else:
        raise AssertionError("missing baseline was accepted")


def test_tag_ref_cannot_be_an_option_or_path(tmp_path: Path) -> None:
    assert watch.inspect_tag(tmp_path, "--upload-pack=evil", [], [])["status"] == "invalid_tag"
    assert watch.inspect_tag(tmp_path, "v2026.9.24^{tree}", [], [])["status"] == "invalid_tag"
