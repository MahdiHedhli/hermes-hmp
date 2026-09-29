"""Offline release-check fixtures: no GitHub, Hermes, or live home is touched."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import pytest

from hmp_plugin import cli, compat, update_check

OLD = "a" * 40
NEW = "b" * 40
HERMES = "c" * 40


def _git_root(path: Path, sha: str) -> Path:
    path.mkdir()
    (path / ".git").mkdir()
    (path / ".git" / "HEAD").write_text(sha, encoding="utf-8")
    return path


def _manifest(root: Path, *, malicious: bool = False) -> dict[str, str]:
    files = ["../secret.py"] if malicious else ["bridge.py"]
    data = {
        "format": 1,
        "bridge_files": files,
        "builds": [
            {
                "fingerprint": compat.compute_read_bridge_fingerprint(root, ["bridge.py"]),
                "git_sha": HERMES,
                "label": "fixture",
                "qualified_by": "fixture",
                "qualified_at": "2026-09-29",
            }
        ],
    }
    return {"encoding": "base64", "content": base64.b64encode(json.dumps(data).encode()).decode()}


def test_no_published_release_does_not_look_up_candidate_or_change_pin(tmp_path: Path) -> None:
    plugin = _git_root(tmp_path / "plugin", OLD)
    calls: list[str] = []

    def get(path: str) -> dict[str, object]:
        calls.append(path)
        raise update_check.UpdateCheckError("not found", status=404)

    result = update_check.check_update(get=get, plugin_root=plugin)
    assert result.installed_sha == OLD
    assert result.release_sha is None
    assert calls == ["/releases/latest"]
    assert (plugin / ".git" / "HEAD").read_text() == OLD


def test_new_release_reports_exact_pin_and_manifest_match(tmp_path: Path) -> None:
    plugin = _git_root(tmp_path / "plugin", OLD)
    hermes = _git_root(tmp_path / "hermes", HERMES)
    (hermes / "bridge.py").write_text("fixture\n", encoding="utf-8")
    manifest = _manifest(hermes)

    def get(path: str) -> dict[str, object]:
        if path == "/releases/latest":
            return {"tag_name": "v1.2.3"}
        if path == "/git/ref/tags/v1.2.3":
            return {"object": {"type": "tag", "sha": "d" * 40}}
        if path == "/git/tags/" + "d" * 40:
            return {"object": {"type": "commit", "sha": NEW}}
        if path == f"/compare/{OLD}...{NEW}":
            return {"status": "ahead"}
        if path.startswith("/contents/server/hmp_plugin/"):
            assert path.endswith("?ref=" + NEW)
            return manifest
        raise AssertionError(path)

    result = update_check.check_update(get=get, plugin_root=plugin, hermes_root=hermes)
    assert result.release_sha == NEW
    assert result.pin_status == "newer release available"
    assert result.hermes_sha == HERMES
    assert all(value.startswith("listed") for value in result.compatibility.values())
    assert len(result.compatibility) == 4


def test_candidate_with_parent_path_is_unknown_without_reading_it(tmp_path: Path) -> None:
    hermes = _git_root(tmp_path / "hermes", HERMES)
    (hermes / "bridge.py").write_text("fixture", encoding="utf-8")
    with pytest.raises(update_check.UpdateCheckError, match="invalid release compatibility"):
        update_check._manifest(_manifest(hermes, malicious=True))


def test_bad_tag_is_refused_before_followup_requests(tmp_path: Path) -> None:
    plugin = _git_root(tmp_path / "plugin", OLD)
    calls: list[str] = []

    def get(path: str) -> dict[str, object]:
        calls.append(path)
        return {"tag_name": "../other-repo"}

    with pytest.raises(update_check.UpdateCheckError, match="invalid release tag"):
        update_check.check_update(get=get, plugin_root=plugin)
    assert calls == ["/releases/latest"]


def test_compare_api_path_is_accepted_but_parent_segments_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Opener:
        def open(self, request: object, timeout: int) -> io.BytesIO:
            assert timeout == 5
            assert request.full_url == f"{update_check.API}/compare/{OLD}...{NEW}"
            return io.BytesIO(b'{"status":"ahead"}')

    monkeypatch.setattr(update_check.urllib.request, "build_opener", lambda *_: Opener())
    assert update_check.fetch_json(f"/compare/{OLD}...{NEW}")["status"] == "ahead"
    with pytest.raises(update_check.UpdateCheckError, match="invalid update request"):
        update_check.fetch_json("/contents/../private")


def test_cli_check_is_read_only_and_reports_no_release() -> None:
    out = io.StringIO()
    err = io.StringIO()
    result = update_check.UpdateResult(OLD, None, None, "no release", None, {})
    env = cli.CliEnv(stdout=out, stderr=err, update_check=lambda: result)
    args = type("Args", (), {"hmp_command": "update", "update_command": "check"})()
    assert cli.dispatch(args, env) == cli.EXIT_OK
    assert "Latest published HMP release: none" in out.getvalue()
    assert err.getvalue() == ""
