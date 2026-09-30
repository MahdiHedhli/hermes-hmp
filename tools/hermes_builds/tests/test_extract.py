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

import hashlib
import importlib.util
import json
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


def _write_manifest(tmp_path: Path, python_line: str) -> Path:
    manifest = tmp_path / "builds.yaml"
    manifest.write_text(
        "format: 1\nbuilds:\n  - label: b\n    clone: c\n    ref: HEAD\n"
        f"    optional: false\n{python_line}",
        encoding="utf-8",
    )
    return manifest


def _load_with(tmp_path: Path, python_line: str) -> list:
    with mock.patch.object(extract, "BUILDS_YAML", _write_manifest(tmp_path, python_line)):
        return extract.load_builds()


def test_python_defaults_to_311(tmp_path: Path) -> None:
    assert _load_with(tmp_path, "")[0].python == "3.11"
    # The committed manifest adds no per-build override yet.
    assert {b.python for b in extract.load_builds()} == {"3.11"}


@pytest.mark.parametrize("version", ["3.14", "3.14.0", "3.11.4"])
def test_python_accepts_quoted_versions(tmp_path: Path, version: str) -> None:
    assert _load_with(tmp_path, f'    python: "{version}"\n')[0].python == version


@pytest.mark.parametrize(
    "line",
    [
        "    python: 3.14\n",  # unquoted -> YAML float
        "    python: 3.10\n",  # would silently become 3.1
        "    python: 3\n",
        '    python: "3"\n',
        '    python: "3.x"\n',
        '    python: "python3.14"\n',
        '    python: ">=3.14"\n',
        '    python: "3.14.0.1"\n',
        '    python: "2.7"\n',
        '    python: " 3.14"\n',
        '    python: "3.14\\n"\n',
        "    python: true\n",
        "    python: null\n",
    ],
)
def test_python_rejects_malformed_values(tmp_path: Path, line: str) -> None:
    with pytest.raises(SystemExit, match="invalid python"):
        _load_with(tmp_path, line)


_SECRETS = {
    "OPENAI_API_KEY": "sk-real", "ANTHROPIC_API_KEY": "sk-ant-real", "GITHUB_TOKEN": "ghp_x",
    "HERMES_HOME": "/somewhere", "AWS_SECRET_ACCESS_KEY": "aws", "OPENROUTER_API_KEY": "or",
    "HTTPS_PROXY": "http://user:pw@proxy",
}
_ESSENTIALS = {"PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8", "SSL_CERT_FILE": "/etc/ca.pem"}


def test_scratch_env_is_allowlisted_and_scratch(tmp_path: Path) -> None:
    build_dir = tmp_path / "b"
    with mock.patch.dict(extract.os.environ, {**_SECRETS, **_ESSENTIALS}, clear=True):
        env = extract.scratch_env(build_dir, build_dir / "hermes_home")
    for key in _SECRETS:
        assert key not in env or key == "HERMES_HOME"
    assert env["HERMES_HOME"] == str(build_dir / "hermes_home")
    assert {k: env[k] for k in _ESSENTIALS} == _ESSENTIALS
    assert env["HOME"] == str(build_dir / "home")
    assert env["UV_CACHE_DIR"].startswith(str(build_dir))
    assert env["XDG_CACHE_HOME"].startswith(str(build_dir))
    assert env["UV_PYTHON_DOWNLOADS"] == "never"
    assert env["TMPDIR"] == str(build_dir / "tmp")
    assert "sk-real" not in " ".join(env.values())


def test_scratch_env_refuses_hermes_home_in_real_home(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    build_dir = tmp_path / "elsewhere"
    with (
        mock.patch.object(extract.Path, "home", return_value=fake_home),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.scratch_env(build_dir, fake_home / ".hermes")
    # Validation happens before any directory is created.
    assert not build_dir.exists()
    assert not (fake_home / ".hermes").exists()


def _run_process_build(
    tmp_path: Path, python: str, actual: str = "3.14.0", fail_import: str | None = None
):
    """Run process_build against a synthetic clone with every non-git subprocess faked."""
    refs = tmp_path / "_refs"
    clone = refs / "c"
    lock = b"version = 1\n"
    if not clone.exists():
        _init_repo(clone)
        (clone / "uv.lock").write_bytes(lock)
        subprocess.run(["git", "-C", str(clone), "add", "uv.lock"], check=True)
        subprocess.run(
            ["git", "-C", str(clone), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
             "commit", "-q", "-m", "lock"], check=True,
        )
    real_run = subprocess.run
    calls: list[tuple[list[str], dict]] = []

    def fake_run(cmd, *a, **kw):
        if cmd[0] == "git":
            return real_run(cmd, *a, **kw)
        calls.append((cmd, kw))
        out, code = "", 0
        if cmd[-1] == extract._INFO_SCRIPT:
            out = json.dumps({"version": actual, "implementation": "CPython",
                              "gil_disabled": False, "executable": cmd[0]})
        elif cmd[:2] == ["uv", "--version"]:
            out = "uv 9.9.9 (test)\n"
        elif cmd[-1] == fail_import:
            code = 1
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")

    build = extract.Build("b", "c", "HEAD", False, python)
    before = extract.clone_snapshot(clone)
    with (
        mock.patch.dict(extract.os.environ, {**_SECRETS, **_ESSENTIALS}, clear=True),
        mock.patch.object(extract.subprocess, "run", fake_run),
        mock.patch.object(extract.shutil, "which", return_value="/usr/bin/uv"),
    ):
        ok = extract.process_build(build, refs, tmp_path / "out", skip_venv=False)
    return ok, calls, before, extract.clone_snapshot(clone), tmp_path / "out" / "b", lock


def test_process_build_default_python_locked_no_downloads(tmp_path: Path) -> None:
    ok, calls, *_ = _run_process_build(tmp_path, "3.11", actual="3.11.9")
    assert ok
    assert calls[0][0] == [
        "uv", "sync", "--locked", "--no-python-downloads", "--python", "3.11"
    ]


def test_process_build_selects_314_and_uses_venv_python_for_import(tmp_path: Path) -> None:
    ok, calls, _, _, build_dir, _ = _run_process_build(tmp_path, "3.14")
    assert ok
    assert calls[0][0][-2:] == ["--python", "3.14"]
    src = build_dir / "src"
    imports = [c for c in calls if c[0][-1] in ("import agent", "import hermes_cli")]
    assert [c[0][-1] for c in imports] == ["import agent", "import hermes_cli"]
    for cmd, kw in imports:
        assert cmd[0] == str(src / ".venv" / "bin" / "python")
        assert "uv" not in cmd
        assert kw["cwd"] == src
        assert kw["env"]["HERMES_HOME"] == str(build_dir / "hermes_home")
    for _cmd, kw in calls:
        for key in _SECRETS:
            assert key not in kw["env"] or key == "HERMES_HOME"
        assert kw["env"]["HOME"] == str(build_dir / "home")
        assert kw["env"]["UV_PYTHON_DOWNLOADS"] == "never"


def test_process_build_writes_nonsecret_metadata(tmp_path: Path) -> None:
    ok, _, _, _, build_dir, lock = _run_process_build(tmp_path, "3.14", actual="3.14.1")
    assert ok
    text = (build_dir / "build-metadata.json").read_text()
    meta = json.loads(text)
    assert meta["python_version"] == "3.14.1"
    assert meta["python_requested"] == "3.14"
    assert meta["uv_lock_sha256"] == hashlib.sha256(lock).hexdigest()
    assert meta["label"] == "b" and len(meta["commit"]) == 40
    assert meta["imports_ok"] is True and meta["extraction_ok"] is True
    assert meta["python_implementation"] == "CPython"
    assert meta["python_gil_disabled"] is False
    assert meta["python_executable"].endswith(".venv/bin/python")
    assert meta["uv_version"] == "uv 9.9.9 (test)"
    assert not any(v in text for v in ("sk-real", "ghp_x", "user:pw"))


def test_process_build_fails_on_interpreter_mismatch(tmp_path: Path) -> None:
    ok, _, _, _, build_dir, _ = _run_process_build(tmp_path, "3.14", actual="3.11.9")
    assert not ok
    assert not (build_dir / "build-metadata.json").exists()


def test_uv_version_uses_sanitized_env(tmp_path: Path) -> None:
    _, calls, *_ = _run_process_build(tmp_path, "3.14")
    ((_cmd, kw),) = [c for c in calls if c[0][:2] == ["uv", "--version"]]
    for key in _SECRETS:
        assert key not in kw["env"] or key == "HERMES_HOME"


def test_failed_import_writes_no_success_metadata(tmp_path: Path) -> None:
    ok, _, _, _, build_dir, _ = _run_process_build(
        tmp_path, "3.14", fail_import="import hermes_cli"
    )
    assert not ok
    assert not (build_dir / "build-metadata.json").exists()


def test_rerun_failure_removes_stale_success_metadata(tmp_path: Path) -> None:
    ok, _, _, _, build_dir, _ = _run_process_build(tmp_path, "3.14")
    assert ok and (build_dir / "build-metadata.json").exists()
    (build_dir / "hermes_home" / "junk").write_text("x")
    ok, _, _, _, build_dir, _ = _run_process_build(tmp_path, "3.14", fail_import="import agent")
    assert not ok
    assert not (build_dir / "build-metadata.json").exists()
    assert not (build_dir / "hermes_home" / "junk").exists()


def test_stale_state_cleared_even_when_skipped_or_clone_missing(tmp_path: Path) -> None:
    out = tmp_path / "out"
    build_dir = out / "b"
    (build_dir / "hermes_home").mkdir(parents=True)
    (build_dir / "build-metadata.json").write_text("{}")
    build = extract.Build("b", "missing", "HEAD", True)
    assert extract.process_build(build, tmp_path / "_refs", out, skip_venv=False)
    assert not (build_dir / "build-metadata.json").exists()
    assert not (build_dir / "hermes_home").exists()


def test_clean_build_state_refuses_symlinks_and_real_home(tmp_path: Path) -> None:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("x")
    build_dir = tmp_path / "out" / "b"
    build_dir.mkdir(parents=True)
    (build_dir / "hermes_home").symlink_to(victim)
    with pytest.raises(SystemExit, match="symlink"):
        extract.clean_build_state(build_dir)
    assert (victim / "keep").exists()
    with (
        mock.patch.object(extract.Path, "home", return_value=tmp_path),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.clean_build_state(build_dir)
    assert (victim / "keep").exists()


def test_process_build_leaves_clone_untouched(tmp_path: Path) -> None:
    _, _, before, after, _, _ = _run_process_build(tmp_path, "3.14")
    assert before == after


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
