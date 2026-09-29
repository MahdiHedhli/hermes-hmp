"""Tests for tools/hermes_builds/extract.py (T004).

Runnable via pytest (`python -m pytest tools/hermes_builds/tests`). Covers the two things
T004's Accept line names directly:

  - the tool refuses any HERMES_HOME (or --out) inside the real user home;
  - `git archive`-based extraction leaves the source clone's `git status` and HEAD reflog
    unchanged.

The second point is proven against a throwaway synthetic git repo created in a temp directory,
not the real `_refs` clones — this test must not depend on the owner's machine having them
checked out, and never wants to be the thing that mutates them if a bug slips through.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "extract", Path(__file__).resolve().parents[1] / "extract.py"
)
extract = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["extract"] = extract  # dataclass field resolution needs the module registered first
_SPEC.loader.exec_module(extract)


def test_assert_outside_real_home_refuses_home_itself() -> None:
    with (
        mock.patch.object(extract.Path, "home", return_value=Path("/fake/home/owner")),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.assert_outside_real_home(Path("/fake/home/owner"), "HERMES_HOME")


def test_assert_outside_real_home_refuses_nested_path() -> None:
    with (
        mock.patch.object(extract.Path, "home", return_value=Path("/fake/home/owner")),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.assert_outside_real_home(
            Path("/fake/home/owner/.hermes/profiles/default"), "HERMES_HOME"
        )


def test_assert_outside_real_home_allows_scratch() -> None:
    with mock.patch.object(extract.Path, "home", return_value=Path("/fake/home/owner")):
        # Must not raise.
        extract.assert_outside_real_home(Path("/private/tmp/some-scratch-dir"), "HERMES_HOME")


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("hello\n")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "commit", "-q", "-m", "initial"],
        check=True,
    )


def test_extract_tree_is_read_only_on_the_source_clone() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        clone = root / "synthetic_clone"
        _init_repo(clone)
        head = subprocess.run(
            ["git", "-C", str(clone), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

        before = extract.clone_snapshot(clone)
        dest = root / "extracted"
        extract.extract_tree(clone, head, dest)
        after = extract.clone_snapshot(clone)

        assert before == after
        assert (dest / "README.md").read_text() == "hello\n"


def test_ref_resolves_never_fetches_and_returns_none_for_unknown_ref() -> None:
    with tempfile.TemporaryDirectory() as d:
        clone = Path(d) / "synthetic_clone"
        _init_repo(clone)
        assert extract.ref_resolves(clone, "does-not-exist") is None


def test_load_builds_matches_the_committed_manifest() -> None:
    builds = extract.load_builds()
    labels = {b.label for b in builds}
    assert labels == {
        "stock-base", "experimental", "upstream", "v921-git",
        "v924-archive", "v924-git", "omarchy-y520-git", "owner-local",
    }
    upstream = next(b for b in builds if b.label == "upstream")
    assert upstream.optional is True
    # A machine-local build: optional, so its absent clone is skipped everywhere else.
    owner_local = next(b for b in builds if b.label == "owner-local")
    assert owner_local.optional is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
