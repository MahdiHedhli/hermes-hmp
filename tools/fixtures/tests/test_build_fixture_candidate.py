"""The fixture builder's provenance lookup for the ad-hoc `candidate` build (the only build that is
not in builds.yaml): its `source_sha` comes from its own extraction metadata, and only when that
metadata is well-formed. Listed builds keep resolving through builds.yaml and the `_refs` clones."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import _fixture_common as fc
import build_fixture
import pytest

SHA = "0123456789abcdef0123456789abcdef01234567"


def _write(build_dir: Path, meta: object) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    text = meta if isinstance(meta, str) else json.dumps(meta)
    (build_dir / "build-metadata.json").write_text(text, encoding="utf-8")


def test_candidate_source_sha_is_the_extraction_commit(tmp_path: Path) -> None:
    _write(tmp_path, {"label": "candidate", "commit": SHA})
    assert build_fixture._resolve_source_sha("candidate", tmp_path) == SHA


@pytest.mark.parametrize(
    "meta",
    [
        {"label": "stock-base", "commit": SHA},  # metadata of some other build
        {"commit": SHA},
        {"label": "candidate", "commit": SHA.upper()},
        {"label": "candidate", "commit": SHA[:12]},
        {"label": "candidate", "commit": "HEAD"},
        {"label": "candidate", "commit": None},
        {"label": "candidate"},
        "not json",
        "[]",
    ],
)
def test_candidate_source_sha_is_none_for_untrusted_metadata(tmp_path: Path, meta: object) -> None:
    _write(tmp_path, meta)
    assert build_fixture._resolve_source_sha("candidate", tmp_path) is None


def test_candidate_metadata_that_is_a_symlink_is_refused_and_never_read(tmp_path: Path) -> None:
    real = tmp_path / "elsewhere.json"
    real.write_text(json.dumps({"label": "candidate", "commit": SHA}), encoding="utf-8")
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    (build_dir / "build-metadata.json").symlink_to(real)
    with pytest.raises(fc.FixtureSafetyError, match="symlink"):
        build_fixture._resolve_source_sha("candidate", build_dir)
    (build_dir / "build-metadata.json").unlink()
    (build_dir / "build-metadata.json").symlink_to(tmp_path / "does-not-exist")  # dangling
    with pytest.raises(fc.FixtureSafetyError, match="symlink"):
        build_fixture._resolve_source_sha("candidate", build_dir)


def test_candidate_metadata_that_is_not_a_regular_file_or_is_huge_is_refused(
    tmp_path: Path,
) -> None:
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    meta = build_dir / "build-metadata.json"
    meta.mkdir()
    with pytest.raises(fc.FixtureSafetyError, match="not a regular file"):
        build_fixture._resolve_source_sha("candidate", build_dir)
    meta.rmdir()
    if hasattr(os, "mkfifo"):
        os.mkfifo(meta)  # opening it for reading would block forever
        with pytest.raises(fc.FixtureSafetyError, match="not a regular file"):
            build_fixture._resolve_source_sha("candidate", build_dir)
        meta.unlink()
    meta.write_bytes(b" " * (build_fixture._MAX_CANDIDATE_METADATA_BYTES + 1))
    with pytest.raises(fc.FixtureSafetyError, match="unexpectedly large"):
        build_fixture._resolve_source_sha("candidate", build_dir)


def test_bootstrap_stops_on_a_symlinked_candidate_metadata_file(tmp_path: Path) -> None:
    build_dir = tmp_path / "builds" / "candidate"
    src = build_dir / "src"
    src.mkdir(parents=True)
    real = tmp_path / "elsewhere.json"
    real.write_text(json.dumps({"label": "candidate", "commit": SHA}), encoding="utf-8")
    (build_dir / "build-metadata.json").symlink_to(real)
    plugin_copy = tmp_path / "plugin"
    plugin_copy.mkdir()
    (plugin_copy / "read_compat_builds.json").write_text('{"builds": []}', encoding="utf-8")
    build = fc.BuildInfo("candidate", src, src / ".venv" / "bin" / "python3")
    identity = mock.Mock(stdout=json.dumps({"fingerprint": "ab" * 32}))
    with (
        mock.patch.object(fc, "run_seed_script", return_value=identity),
        pytest.raises(fc.FixtureSafetyError, match="symlink"),
    ):
        build_fixture.bootstrap_compat_entry(build, plugin_copy)
    # nothing was added to the scratch compatibility list on the way
    assert json.loads((plugin_copy / "read_compat_builds.json").read_text()) == {"builds": []}


def test_candidate_source_sha_is_none_without_metadata_or_directory(tmp_path: Path) -> None:
    assert build_fixture._resolve_source_sha("candidate", tmp_path) is None
    assert build_fixture._resolve_source_sha("candidate") is None


def test_listed_builds_ignore_metadata_and_resolve_through_builds_yaml(tmp_path: Path) -> None:
    _write(tmp_path, {"label": "stock-base", "commit": SHA})
    assert build_fixture._resolve_source_sha("no-such-build", tmp_path) is None
    import extract

    with (
        mock.patch.object(extract, "find_refs_dir", return_value=tmp_path / "_refs"),
        mock.patch.object(extract, "ref_resolves", return_value="a" * 40) as resolves,
    ):
        assert build_fixture._resolve_source_sha("stock-base", tmp_path) == "a" * 40
    resolves.assert_called_once()
