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
import os
import stat
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
        mock.patch.object(extract.safety, "real_user_home", return_value=Path("/fake/home/owner")),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.assert_outside_real_home(Path("/fake/home/owner"), "HERMES_HOME")


def test_assert_outside_real_home_refuses_nested_path() -> None:
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=Path("/fake/home/owner")),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.assert_outside_real_home(
            Path("/fake/home/owner/.hermes/profiles/default"), "HERMES_HOME"
        )


def test_assert_outside_real_home_allows_scratch() -> None:
    with mock.patch.object(extract.safety, "real_user_home", return_value=Path("/fake/home/owner")):
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
    assert labels == {"stock-base", "experimental", "upstream", "owner-local"}
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
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.scratch_env(build_dir, fake_home / ".hermes")
    # Validation happens before any directory is created.
    assert not build_dir.exists()
    assert not (fake_home / ".hermes").exists()


def _base_interpreter(tmp_path: Path) -> Path:
    """A stand-in system interpreter outside the fake home (its runs are always faked)."""
    python = tmp_path / "sys_python" / "bin" / "python3.14"
    if not python.exists():
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\nexit 1\n")
        os.chmod(python, 0o755)  # noqa: S103 - a system-like interpreter
        os.chmod(python.parent, 0o755)  # noqa: S103 - a system-like bin directory
    return python


def _fake_venv(src: Path, target: Path) -> None:
    """What `uv sync` leaves behind: `.venv/bin/python*` linking to the base, and `pyvenv.cfg`."""
    venv = src / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(target)
    (venv / "bin" / "python3").symlink_to("python")
    (venv / "pyvenv.cfg").write_text(f"home = {target.parent}\n")


def _run_process_build(
    tmp_path: Path, python: str, actual: str = "3.14.0", fail_import: str | None = None,
    candidate: bool = False, on_call=None, base_in_home: bool = False,
    extra_env: dict[str, str] | None = None, real_which: bool = False,
    interpreter: Path | None = None, venv_target: Path | None = None,
    probe_reports_home: bool = False,
):
    """Run process_build against a synthetic clone with every non-git subprocess faked, under a
    fake account home (`tmp_path/account_home`). `candidate=True` uses the ad-hoc candidate Build
    (fixed label/clone, exact HEAD sha) with `interpreter` (default: a stand-in system Python
    outside the home) as `--candidate-interpreter`. `on_call(cmd)` sees every faked (non-git)
    command before it answers; the faked `uv sync` builds a `.venv` whose `bin/python` links to
    `venv_target` (default: the interpreter). `base_in_home` makes the venv's interpreter report a
    base inside the fake home, `probe_reports_home` makes the base interpreter's own probe do so;
    `real_which` leaves `shutil.which` alone (default: `uv` is always `/usr/bin/uv`)."""
    account_home = (tmp_path / "account_home").resolve()
    account_home.mkdir(exist_ok=True)
    home_prefix = str(account_home / ".pyenv" / "3.14")
    if candidate and interpreter is None:
        interpreter = _base_interpreter(tmp_path)
    refs = tmp_path / "_refs"
    clone = refs / (extract.CANDIDATE_CLONE if candidate else "c")
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
        if on_call is not None:
            on_call(cmd)
        out, code = "", 0
        if cmd[-1] == extract._INFO_SCRIPT:
            in_venv = ".venv" in cmd[0]
            prefix = home_prefix if (base_in_home if in_venv else probe_reports_home) else "/usr"
            out = json.dumps({"version": actual, "implementation": "CPython",
                              "gil_disabled": False, "executable": cmd[0],
                              "base_prefix": prefix, "base_executable": prefix + "/bin/python3"})
        elif cmd[1:] == ["--version"]:
            out = "uv 9.9.9 (test)\n"
        elif cmd[1:2] == ["sync"]:
            target = venv_target or (interpreter.resolve() if interpreter else Path("/usr/bin/x"))
            _fake_venv(Path(kw["cwd"]), target)
        elif cmd[-1] == fail_import:
            code = 1
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")

    if candidate:
        head = subprocess.run(
            ["git", "-C", str(clone), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        build = extract.candidate_build(head, python, interpreter)
    else:
        build = extract.Build("b", "c", "HEAD", False, python)
    before = extract.clone_snapshot(clone)
    which = (
        mock.patch.object(extract.shutil, "which", extract.shutil.which)
        if real_which
        else mock.patch.object(extract.shutil, "which", return_value="/usr/bin/uv")
    )
    with (
        mock.patch.dict(extract.os.environ, {**_SECRETS, **_ESSENTIALS, **(extra_env or {})},
                        clear=True),
        mock.patch.object(extract.subprocess, "run", fake_run),
        mock.patch.object(extract.safety, "real_user_home", return_value=account_home),
        which,
    ):
        ok = extract.process_build(build, refs, tmp_path / "out", skip_venv=False)
    build_dir = tmp_path / "out" / build.label
    return ok, calls, before, extract.clone_snapshot(clone), build_dir, lock


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
        mock.patch.object(extract.safety, "real_user_home", return_value=tmp_path),
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.clean_build_state(build_dir)
    assert (victim / "keep").exists()


def test_process_build_leaves_clone_untouched(tmp_path: Path) -> None:
    _, _, before, after, _, _ = _run_process_build(tmp_path, "3.14")
    assert before == after


# ---- ad-hoc exact candidate (--candidate-sha / --candidate-python) -----------------------------

_SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize(
    "value",
    [
        _SHA[:-1],  # 39 chars
        _SHA + "0",  # 41 chars
        _SHA[:7],  # abbreviation
        _SHA.upper(),
        _SHA + "\n",  # `$` would accept this; fullmatch must not
        " " + _SHA,
        "-" + _SHA[1:],  # option-shaped
        "HEAD",
        "main",
        "v2026.9.21",
        "g" * 40,
        "",
        None,
        1234,
    ],
)
def test_candidate_sha_rejects_anything_but_full_lowercase_hex(value: object) -> None:
    with pytest.raises(SystemExit, match="invalid --candidate-sha"):
        extract.parse_candidate_sha(value)
    with pytest.raises(SystemExit, match="invalid --candidate-sha"):
        extract.candidate_build(value)


def test_candidate_build_has_fixed_label_clone_and_validated_python() -> None:
    build = extract.candidate_build(_SHA)
    assert (build.label, build.clone, build.ref) == ("candidate", "hermes-agent", _SHA)
    assert build.exact is True and build.optional is False
    assert build.python == extract.DEFAULT_PYTHON and build.interpreter is None
    assert extract.candidate_build(_SHA, "3.14.1").python == "3.14.1"
    assert extract.candidate_build(_SHA, "3.14", Path("/usr/bin/python3")).interpreter == (
        "/usr/bin/python3"
    )
    for bad in ("3", "3.x", "3.14\n", ">=3.14", 3.14, None, "/usr/bin/python3"):
        with pytest.raises(SystemExit, match="invalid python"):
            extract.candidate_build(_SHA, bad)


def test_listed_builds_are_never_exact_and_cannot_use_the_reserved_label(tmp_path: Path) -> None:
    assert not any(b.exact for b in extract.load_builds())
    manifest = tmp_path / "builds.yaml"
    manifest.write_text(
        "format: 1\nbuilds:\n  - label: candidate\n    clone: c\n    ref: HEAD\n",
        encoding="utf-8",
    )
    with (
        mock.patch.object(extract, "BUILDS_YAML", manifest),
        pytest.raises(SystemExit, match="reserved label"),
    ):
        extract.load_builds()


def _main_capturing_builds(argv: list[str]) -> list:
    seen: list = []

    def fake_process_build(build, refs_dir, out_root, skip_venv):
        seen.append((build, refs_dir, out_root, skip_venv))
        return True

    with mock.patch.object(extract, "process_build", fake_process_build):
        assert extract.main(argv) == 0
    return seen


def test_main_extracts_exactly_the_candidate_from_the_supplied_refs_dir(tmp_path: Path) -> None:
    refs = tmp_path / "refs"
    refs.mkdir()
    python = _base_interpreter(tmp_path)
    with mock.patch.object(
        extract.safety, "real_user_home", return_value=(tmp_path / "account_home").resolve()
    ):
        seen = _main_capturing_builds(
            ["--out", str(tmp_path / "out"), "--refs-dir", str(refs),
             "--candidate-sha", _SHA, "--candidate-python", "3.14.1",
             "--candidate-interpreter", str(python)]
        )
    ((build, refs_dir, _out, _skip),) = seen  # not the four listed builds
    assert (build.label, build.clone, build.ref, build.python, build.interpreter) == (
        "candidate", "hermes-agent", _SHA, "3.14.1", str(python)
    )
    assert refs_dir == refs


def test_main_without_candidate_still_runs_listed_builds(tmp_path: Path) -> None:
    seen = _main_capturing_builds(
        ["--out", str(tmp_path / "out"), "--refs-dir", str(tmp_path), "--builds", "stock-base"]
    )
    assert [b.label for b, *_ in seen] == ["stock-base"]


@pytest.mark.parametrize(
    "extra",
    [
        ["--candidate-sha", _SHA, "--builds", "stock-base"],  # cannot mix with listed builds
        ["--candidate-sha", _SHA],  # --refs-dir is mandatory, never walked-up for a candidate
        ["--candidate-python", "3.14"],  # python without a candidate
        ["--candidate-interpreter", "/usr/bin/python3"],  # interpreter without a candidate
        ["--candidate-sha", _SHA, "--refs-dir", "R"],  # a venv needs an explicit interpreter
    ],
)
def test_main_rejects_unsafe_candidate_combinations(tmp_path: Path, extra: list[str]) -> None:
    argv = ["--out", str(tmp_path / "out"), *[str(tmp_path) if a == "R" else a for a in extra]]
    if "--refs-dir" not in argv and "--builds" in argv:
        argv += ["--refs-dir", str(tmp_path)]
    with (
        mock.patch.object(extract, "process_build") as process,
        pytest.raises(SystemExit) as exc,
    ):
        extract.main(argv)
    assert exc.value.code == 2
    process.assert_not_called()
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "extra", [["--candidate-sha", "main"], ["--candidate-sha", _SHA, "--candidate-python", "3"]]
)
def test_main_rejects_malformed_candidate_values(tmp_path: Path, extra: list[str]) -> None:
    argv = ["--out", str(tmp_path / "out"), "--refs-dir", str(tmp_path), "--skip-venv", *extra]
    with mock.patch.object(extract, "process_build") as process, pytest.raises(SystemExit):
        extract.main(argv)
    process.assert_not_called()


def test_main_refuses_live_hermes_home_as_refs_dir(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    live = fake_home / ".hermes" / "refs"
    live.mkdir(parents=True)
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home),
        mock.patch.object(extract, "process_build") as process,
        pytest.raises(SystemExit, match="live Hermes home"),
    ):
        extract.main(
            ["--out", str(tmp_path / "out"), "--refs-dir", str(live), "--candidate-sha", _SHA,
             "--skip-venv"]
        )
    process.assert_not_called()


def _candidate_repo(tmp_path: Path) -> tuple[Path, str]:
    refs = tmp_path / "_refs"
    _init_repo(refs / "hermes-agent")
    sha = subprocess.run(
        ["git", "-C", str(refs / "hermes-agent"), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return refs, sha


def test_process_build_candidate_extracts_the_exact_commit_and_records_it(
    tmp_path: Path,
) -> None:
    ok, calls, before, after, build_dir, _ = _run_process_build(
        tmp_path, "3.14", actual="3.14.2", candidate=True
    )
    assert ok and before == after
    assert build_dir.name == "candidate"
    # Nothing is discovered: the explicit interpreter, validated without running it, is probed
    # once in isolated mode; `uv sync` then gets its real path, and uv runs by absolute path.
    base = str(_base_interpreter(tmp_path).resolve())
    assert calls[0][0] == [base, "-I", "-S", "-c", extract._INFO_SCRIPT]
    assert calls[1][0] == [
        "/usr/bin/uv", "sync", "--locked", "--no-python-downloads", "--python", base,
    ]
    assert not any(c[0][1:3] == ["python", "find"] for c in calls)
    meta = json.loads((build_dir / "build-metadata.json").read_text())
    assert meta["label"] == "candidate"
    assert meta["commit"] == meta["ref"] and len(meta["commit"]) == 40
    assert meta["python_requested"] == "3.14" and meta["python_version"] == "3.14.2"
    assert meta["python_base_interpreter"] == base
    assert (build_dir / "src" / "README.md").read_text() == "hello\n"


def test_process_build_candidate_interpreter_mismatch_stops_before_uv(tmp_path: Path) -> None:
    ran: list[list[str]] = []
    with pytest.raises(SystemExit, match=r"not the requested 3.14"):
        _run_process_build(
            tmp_path, "3.14", actual="3.11.9", candidate=True, on_call=ran.append
        )
    assert [c[1:3] for c in ran] == [["-I", "-S"]]  # only the base probe ran; no uv, no venv
    assert not (tmp_path / "out" / "candidate" / "build-metadata.json").exists()


def test_process_build_candidate_unknown_sha_fails_without_touching_anything(
    tmp_path: Path,
) -> None:
    refs, _ = _candidate_repo(tmp_path)
    before = extract.clone_snapshot(refs / "hermes-agent")
    build = extract.candidate_build(_SHA)  # well-formed, but not in the clone
    with pytest.raises(SystemExit, match="does not resolve locally"):
        extract.process_build(build, refs, tmp_path / "out", skip_venv=True)
    assert extract.clone_snapshot(refs / "hermes-agent") == before
    assert not (tmp_path / "out" / "candidate" / "src").exists()


def test_process_build_candidate_requires_the_fixed_clone_name(tmp_path: Path) -> None:
    refs = tmp_path / "_refs"
    _init_repo(refs / "some-other-clone")
    sha = subprocess.run(
        ["git", "-C", str(refs / "some-other-clone"), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    with pytest.raises(SystemExit, match="no git clone"):
        extract.process_build(
            extract.candidate_build(sha), refs, tmp_path / "out", skip_venv=True
        )


def test_process_build_candidate_refuses_a_sha_that_peels_to_another_commit(
    tmp_path: Path,
) -> None:
    refs, commit = _candidate_repo(tmp_path)
    clone = refs / "hermes-agent"
    subprocess.run(
        ["git", "-C", str(clone), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "tag", "-a", "-m", "t", "v-test", commit],
        check=True,
    )
    tag_object = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "v-test"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert tag_object != commit
    with pytest.raises(SystemExit, match="different object"):
        extract.process_build(
            extract.candidate_build(tag_object), refs, tmp_path / "out", skip_venv=True
        )
    assert not (tmp_path / "out" / "candidate" / "src").exists()


# ---- candidate isolation: scrubbed environment, private paths, exact and hardened extraction ----


def test_scratch_env_gives_every_home_xdg_tmp_and_cache_dir_private_scratch(
    tmp_path: Path,
) -> None:
    build_dir = tmp_path / "b"
    with mock.patch.dict(
        extract.os.environ,
        {**_SECRETS, **_ESSENTIALS, "XDG_DATA_HOME": "/real/data", "TMPDIR": "/real/tmp",
         "PYTHONPATH": "/evil", "GIT_DIR": "/elsewhere", "HOME": "/real/home"},
        clear=True,
    ):
        env = extract.scratch_env(build_dir, build_dir / "hermes_home")
    for key in ("HOME", "HERMES_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "TMPDIR", "UV_CACHE_DIR",
                "PYTHONPYCACHEPREFIX"):
        assert Path(env[key]).is_relative_to(build_dir), key
    for key in ("PYTHONPATH", "GIT_DIR", "HTTPS_PROXY", "OPENAI_API_KEY"):
        assert key not in env
    assert "/real/" not in " ".join(env.values())
    assert stat.S_IMODE(Path(env["HOME"]).stat().st_mode) == 0o700


def test_scratch_env_real_home_check_ignores_the_home_variable(tmp_path: Path) -> None:
    fake_home = tmp_path / "account_home"
    fake_home.mkdir()
    build_dir = tmp_path / "elsewhere"
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home),
        mock.patch.dict(extract.os.environ, {"HOME": str(build_dir)}),
    ):
        extract.scratch_env(build_dir, build_dir / "hermes_home")  # HOME is not the real home
        with pytest.raises(SystemExit, match="inside the real user home"):
            extract.scratch_env(tmp_path / "other", fake_home / ".hermes")


def test_assert_outside_real_home_uses_the_account_home_not_home_var(tmp_path: Path) -> None:
    fake_home = tmp_path / "account_home"
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home),
        mock.patch.dict(extract.os.environ, {"HOME": str(tmp_path / "scratch_home")}),
    ):
        extract.assert_outside_real_home(tmp_path / "scratch_home" / "out", "--out")
        with pytest.raises(SystemExit, match="inside the real user home"):
            extract.assert_outside_real_home(fake_home / "out", "--out")
        with pytest.raises(SystemExit, match="contains the real user home"):
            extract.assert_outside_real_home(tmp_path, "--out")


def test_interpreter_info_probes_in_isolated_mode_without_site(tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd, **_kw):
        seen.append(list(cmd))
        out = json.dumps({"version": "3.14.1"})
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    with mock.patch.object(extract.subprocess, "run", fake_run):
        assert extract.interpreter_info(tmp_path, {})["version"] == "3.14.1"
    assert seen[0][1:4] == ["-I", "-S", "-c"]  # no .pth, sitecustomize, user site or PYTHON*


def test_git_ignores_inherited_git_variables(tmp_path: Path) -> None:
    clone = tmp_path / "a"
    other = tmp_path / "b"
    _init_repo(clone)
    _init_repo(other)
    (other / "extra").write_text("x")
    subprocess.run(["git", "-C", str(other), "add", "extra"], check=True)
    subprocess.run(
        ["git", "-C", str(other), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "commit", "-q", "-m", "two"], check=True,
    )
    expected = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    with mock.patch.dict(
        extract.os.environ, {"GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}
    ):
        assert extract.git(clone, "rev-parse", "HEAD").stdout.strip() == expected
        assert extract.clone_snapshot(clone)[0] == expected


def _spy_processes() -> tuple[list, object, object]:
    seen: list = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def run(cmd, *a, **kw):
        seen.append(("run", list(cmd), kw.get("env")))
        return real_run(cmd, *a, **kw)

    def popen(cmd, *a, **kw):
        seen.append(("popen", list(cmd), kw.get("env")))
        return real_popen(cmd, *a, **kw)

    return (
        seen,
        mock.patch.object(extract.subprocess, "run", run),
        mock.patch.object(extract.subprocess, "Popen", popen),
    )


def test_candidate_extraction_uses_raw_blobs_and_only_hardened_object_database_git(
    tmp_path: Path,
) -> None:
    refs = tmp_path / "_refs"
    clone = refs / "hermes-agent"
    _init_repo(clone)
    (clone / ".gitattributes").write_text("secret.txt export-ignore\n*.txt text eol=crlf\n")
    (clone / "secret.txt").write_text("kept\n")
    subprocess.run(["git", "-C", str(clone), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(clone), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "commit", "-q", "-m", "attrs"], check=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    seen, spy_run, spy_popen = _spy_processes()
    poison = {"GIT_DIR": str(tmp_path / "poison"), "GIT_WORK_TREE": str(tmp_path / "poison"),
              "GIT_INDEX_FILE": str(tmp_path / "poison" / "index")}
    with mock.patch.dict(extract.os.environ, poison), spy_run, spy_popen:
        assert extract.process_build(
            extract.candidate_build(sha), refs, tmp_path / "out", skip_venv=True
        )
    src = tmp_path / "out" / "candidate" / "src"
    assert (src / "secret.txt").read_bytes() == b"kept\n"  # `git archive` would have dropped it
    assert seen
    for _kind, argv, env in seen:
        assert argv[0] == "git"
        assert "--no-replace-objects" in argv and "--no-optional-locks" in argv
        assert "core.fsmonitor=" in argv
        assert "protocol.allow=never" in argv  # no transport: nothing is ever lazily fetched
        assert not {"archive", "status", "checkout", "fetch", "add", "commit"} & set(argv)
        assert env is not None and not {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"} & set(env)
        assert env["GIT_NO_LAZY_FETCH"] == "1"
        assert "HOME" not in env
    assert any("cat-file" in argv for _k, argv, _e in seen)


def test_candidate_extraction_stops_if_the_written_tree_is_not_the_commit(tmp_path: Path) -> None:
    refs, sha = _candidate_repo(tmp_path)
    with (
        mock.patch.object(
            extract.safety, "verify_tree_matches_commit", return_value=["README.md: differs"]
        ),
        pytest.raises(SystemExit, match="not exactly commit"),
    ):
        extract.process_build(
            extract.candidate_build(sha), refs, tmp_path / "out", skip_venv=False
        )
    assert not (tmp_path / "out" / "candidate" / "build-metadata.json").exists()


def test_process_build_candidate_creates_only_private_paths_and_restores_the_umask(
    tmp_path: Path,
) -> None:
    previous = extract.os.umask(0o022)
    try:
        ok, _, _, _, build_dir, _ = _run_process_build(
            tmp_path, "3.14", actual="3.14.2", candidate=True
        )
        after = extract.os.umask(0o022)
    finally:
        extract.os.umask(previous)
    assert ok and after == 0o022
    for path in [build_dir, *build_dir.rglob("*")]:
        if not path.is_symlink():
            assert stat.S_IMODE(path.lstat().st_mode) & 0o077 == 0, path
    assert stat.S_IMODE((build_dir / "build-metadata.json").stat().st_mode) == 0o600


def test_process_build_candidate_subprocesses_all_get_the_scrubbed_environment(
    tmp_path: Path,
) -> None:
    ok, calls, _, _, build_dir, _ = _run_process_build(tmp_path, "3.14", candidate=True)
    assert ok and calls
    for _cmd, kw in calls:
        env = kw["env"]
        assert not set(_SECRETS) - {"HERMES_HOME"} & set(env)
        for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                    "XDG_STATE_HOME", "TMPDIR", "PYTHONPYCACHEPREFIX"):
            assert Path(env[key]).is_relative_to(build_dir), key


@pytest.mark.parametrize("linked", ["candidate", "src"])
def test_process_build_candidate_refuses_a_symlinked_build_or_source_dir(
    tmp_path: Path, linked: str
) -> None:
    refs, sha = _candidate_repo(tmp_path)
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("x")
    out = tmp_path / "out"
    if linked == "candidate":
        out.mkdir()
        (out / "candidate").symlink_to(victim)
    else:
        (out / "candidate").mkdir(parents=True)
        (out / "candidate" / "src").symlink_to(victim)
    with pytest.raises(SystemExit, match="symlink"):
        extract.process_build(extract.candidate_build(sha), refs, out, skip_venv=True)
    assert (victim / "keep").exists() and sorted(p.name for p in victim.iterdir()) == ["keep"]


def test_process_build_candidate_refuses_a_clone_that_leads_into_the_live_hermes_home(
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "account_home"
    live_clone = fake_home / ".hermes" / "hermes-agent"
    _init_repo(live_clone)
    sha = subprocess.run(
        ["git", "-C", str(live_clone), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    refs = tmp_path / "_refs"
    refs.mkdir()
    (refs / "hermes-agent").symlink_to(live_clone)
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home.resolve()),
        pytest.raises(SystemExit, match="live Hermes home"),
    ):
        extract.process_build(
            extract.candidate_build(sha), refs, tmp_path / "out", skip_venv=True
        )
    assert not (tmp_path / "out" / "candidate" / "src").exists()


def _candidate_main(tmp_path: Path, out: Path, refs: Path):
    # `--skip-venv`: these tests are about placement, not the interpreter (tested below).
    return ["--out", str(out), "--refs-dir", str(refs), "--candidate-sha", _SHA, "--skip-venv"]


def test_main_candidate_makes_out_private_and_warns_about_executing_the_candidate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    refs = tmp_path / "refs"
    refs.mkdir()
    _main_capturing_builds(_candidate_main(tmp_path, tmp_path / "out", refs))
    assert stat.S_IMODE((tmp_path / "out").stat().st_mode) == 0o700
    assert "isolated VM, container or user account" in capsys.readouterr().err


@pytest.mark.parametrize(
    "layout",
    [
        lambda t: (_link(t, "out_link", t / "real_out"), t / "refs"),  # symlinked --out
        lambda t: (t / "refs" / "out", t / "refs"),  # scratch inside the refs dir
        lambda t: (t / "out", t / "out" / "refs"),  # refs dir inside scratch
        lambda t: (extract.REPO_ROOT / "scratch", t / "refs"),  # scratch inside the repository
    ],
)
def test_main_candidate_refuses_symlinked_and_overlapping_directories(
    tmp_path: Path, layout
) -> None:
    (tmp_path / "refs").mkdir()
    out, refs = layout(tmp_path)
    with (
        mock.patch.object(extract, "process_build") as process,
        pytest.raises(SystemExit, match=r"symlink|overlap"),
    ):
        extract.main(_candidate_main(tmp_path, out, refs))
    process.assert_not_called()
    assert not (extract.REPO_ROOT / "scratch").exists()


def _link(tmp_path: Path, name: str, target: Path) -> Path:
    target.mkdir(exist_ok=True)
    link = tmp_path / name
    link.symlink_to(target)
    return link


def test_main_candidate_refuses_out_in_the_account_home_whatever_home_var_says(
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "account_home"
    fake_home.mkdir()
    refs = tmp_path / "refs"
    refs.mkdir()
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=fake_home),
        mock.patch.dict(extract.os.environ, {"HOME": str(tmp_path / "scratch_home")}),
        mock.patch.object(extract, "process_build") as process,
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        extract.main(_candidate_main(tmp_path, fake_home / "out", refs))
    process.assert_not_called()
    assert not (fake_home / "out").exists()


# ---- M2/F2: no interpreter in the real home is ever executed for a candidate --------------------


def _fake_home(tmp_path: Path) -> Path:
    home = (tmp_path / "account_home").resolve()
    home.mkdir(exist_ok=True)
    return home


def _managed_dir(home: Path) -> Path:
    managed = home / ".local" / "share" / "uv" / "python"
    managed.mkdir(parents=True)
    return managed


def _home_python(home: Path) -> Path:
    python = home / ".local" / "share" / "uv" / "python" / "cpython-3.14" / "bin" / "python3.14"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("#!/bin/sh\nexit 1\n")
    os.chmod(python, 0o755)  # noqa: S103 - an executable fixture that is never executed
    return python


@pytest.mark.parametrize("configured", ["explicit", "default", "none"])
def test_candidate_scratch_env_never_passes_on_an_interpreter_directory(
    tmp_path: Path, configured: str
) -> None:
    home = _fake_home(tmp_path)
    environ = dict(_ESSENTIALS)
    if configured == "explicit":
        outside = tmp_path / "opt-uv-python"
        outside.mkdir()
        environ["UV_PYTHON_INSTALL_DIR"] = str(outside)
    elif configured == "default":
        _managed_dir(home)
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.dict(extract.os.environ, environ, clear=True),
    ):
        env = extract.scratch_env(tmp_path / "b", None, candidate=True)
    assert "UV_PYTHON_INSTALL_DIR" not in env  # the interpreter is explicit, never discovered


def test_listed_scratch_env_still_passes_on_the_callers_default_uv_python_dir(
    tmp_path: Path,
) -> None:
    home = _fake_home(tmp_path)
    managed = _managed_dir(home)
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.dict(extract.os.environ, _ESSENTIALS, clear=True),
    ):
        env = extract.scratch_env(tmp_path / "b", None)
    assert env["UV_PYTHON_INSTALL_DIR"] == str(managed)  # listed builds: behaviour unchanged


def _link_into_home(tmp_path: Path, home: Path) -> Path:
    """`/usr/local/bin/python3.14`-style path OUTSIDE the home that is a symlink to a uv-managed
    interpreter INSIDE it: what `uv python find` on a PATH without home entries could answer."""
    link = tmp_path / "usr-local-bin" / "python3.14"
    link.parent.mkdir(parents=True)
    link.symlink_to(_home_python(home))
    return link


def test_process_build_candidate_never_executes_an_interpreter_symlinked_into_the_home(
    tmp_path: Path,
) -> None:
    home = _fake_home(tmp_path)
    link = _link_into_home(tmp_path, home)
    ran: list[list[str]] = []
    with pytest.raises(SystemExit, match="real user home"):
        _run_process_build(
            tmp_path, "3.14", candidate=True, interpreter=link, on_call=ran.append
        )
    assert ran == []  # zero subprocess calls: no probe, no uv, nothing of the candidate
    assert not (tmp_path / "out" / "candidate" / "build-metadata.json").exists()


def test_main_candidate_refuses_an_interpreter_symlinked_into_the_home_running_nothing(
    tmp_path: Path,
) -> None:
    home = _fake_home(tmp_path)
    link = _link_into_home(tmp_path, home)
    refs = tmp_path / "refs"
    refs.mkdir()
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.object(extract.subprocess, "run") as run,
        mock.patch.object(extract.subprocess, "Popen") as popen,
        mock.patch.object(extract.safety.subprocess, "run") as safety_run,
        mock.patch.object(extract, "process_build") as process,
        pytest.raises(SystemExit, match="real user home"),
    ):
        extract.main(["--out", str(tmp_path / "out"), "--refs-dir", str(refs),
                      "--candidate-sha", _SHA, "--candidate-interpreter", str(link)])
    for spy in (run, popen, safety_run, process):
        spy.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_process_build_candidate_refuses_a_venv_whose_python_was_relinked_into_the_home(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The base interpreter is fine, but after `uv sync` (which runs the candidate's build
    # backends) the venv's `bin/python` leads into the home: it must never be executed.
    home = _fake_home(tmp_path)
    ran: list[list[str]] = []
    ok, _, _, _, build_dir, _ = _run_process_build(
        tmp_path, "3.14", candidate=True, venv_target=_home_python(home), on_call=ran.append
    )
    assert not ok and not (build_dir / "build-metadata.json").exists()
    assert not any(".venv" in c[0] for c in ran)  # the venv interpreter never ran
    assert "real user home" in capsys.readouterr().err


def test_process_build_candidate_refuses_a_venv_on_another_interpreter(tmp_path: Path) -> None:
    other = tmp_path / "other_python" / "python3.14"
    other.parent.mkdir()
    other.write_text("#!/bin/sh\nexit 1\n")
    os.chmod(other, 0o755)  # noqa: S103 - an executable fixture that is never executed
    ran: list[list[str]] = []
    ok, *_ = _run_process_build(
        tmp_path, "3.14", candidate=True, venv_target=other, on_call=ran.append
    )
    assert not ok and not any(".venv" in c[0] for c in ran)


def test_process_build_candidate_without_an_interpreter_stops_before_uv(tmp_path: Path) -> None:
    refs, sha = _candidate_repo(tmp_path)
    ran: list[list[str]] = []
    real_run = subprocess.run

    def only_git(cmd, *a, **kw):
        if cmd[0] != "git":
            ran.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
        return real_run(cmd, *a, **kw)

    with (
        mock.patch.object(extract.subprocess, "run", only_git),
        mock.patch.object(extract.safety, "require_uv", return_value="/usr/bin/uv"),
        mock.patch.object(
            extract.safety, "real_user_home", return_value=_fake_home(tmp_path)
        ),
        pytest.raises(SystemExit, match="--candidate-interpreter"),
    ):
        extract.process_build(extract.candidate_build(sha), refs, tmp_path / "out", False)
    assert ran == []


def test_process_build_listed_build_ignores_the_home_uv_python_dir_rule(tmp_path: Path) -> None:
    managed = _managed_dir(_fake_home(tmp_path))
    ok, calls, *_ = _run_process_build(tmp_path, "3.14")
    assert ok
    assert calls[0][1]["env"]["UV_PYTHON_INSTALL_DIR"] == str(managed)
    assert calls[0][0][-2:] == ["--python", "3.14"]  # a version request, as before


def _answering(info: dict | None, seen: list | None = None):
    def fake(cmd, **kw):
        if seen is not None:
            seen.append((list(cmd), kw))
        out = json.dumps(info) if info is not None else ""
        return subprocess.CompletedProcess(cmd, 0 if info else 1, stdout=out, stderr="")

    return fake


def test_probe_base_interpreter_runs_only_the_validated_real_path_in_isolated_mode(
    tmp_path: Path,
) -> None:
    home = _fake_home(tmp_path)
    python = _base_interpreter(tmp_path)
    info = {"version": "3.14.2", "executable": str(python), "base_prefix": "/usr",
            "base_executable": str(python)}
    seen: list = []
    env = {"PATH": "/usr/bin", "TMPDIR": str(tmp_path)}
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.object(extract.subprocess, "run", _answering(info, seen)),
    ):
        reported, allowed = extract.probe_base_interpreter(python.resolve(), "3.14", env)
    assert reported == info and allowed == {python.resolve()}
    ((cmd, kw),) = seen
    assert cmd == [str(python.resolve()), "-I", "-S", "-c", extract._INFO_SCRIPT]
    assert kw["env"] is env and kw["cwd"] == str(tmp_path)


@pytest.mark.parametrize(
    ("info", "message"),
    [
        ({"version": "3.11.9", "base_prefix": "/usr", "base_executable": "/usr/bin/python3"},
         "not the requested"),
        ({"version": "3.14.2", "base_prefix": "HOME", "base_executable": "/usr/bin/python3"},
         "real user home"),
        ({"version": "3.14.2"}, "did not report its base_prefix"),
        (None, "did not report its version"),
    ],
)
def test_probe_base_interpreter_refuses_a_wrong_version_or_a_base_in_the_home(
    tmp_path: Path, info: dict | None, message: str
) -> None:
    home = _fake_home(tmp_path)
    if info is not None and info.get("base_prefix") == "HOME":
        info = {**info, "base_prefix": str(home / ".pyenv")}
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.object(extract.subprocess, "run", _answering(info)),
        pytest.raises(extract.safety.SafetyError, match=message),
    ):
        extract.probe_base_interpreter(_base_interpreter(tmp_path), "3.14", {})


def test_probe_base_interpreter_never_runs_a_path_leading_into_the_home(tmp_path: Path) -> None:
    home = _fake_home(tmp_path)
    link = _link_into_home(tmp_path, home)
    with (
        mock.patch.object(extract.safety, "real_user_home", return_value=home),
        mock.patch.object(extract.subprocess, "run") as run,
        pytest.raises(extract.safety.SafetyError, match="real user home"),
    ):
        extract.probe_base_interpreter(link, "3.14", {})
    run.assert_not_called()


def test_check_interpreter_outside_home(tmp_path: Path) -> None:
    home = _fake_home(tmp_path)
    (home / "py").mkdir()
    link = tmp_path / "sys-prefix"
    link.symlink_to(home / "py")
    outside = {"base_prefix": "/usr", "base_executable": "/usr/bin/python3"}
    with mock.patch.object(extract.safety, "real_user_home", return_value=home):
        assert extract.check_interpreter_outside_home(outside) is None
        for bad in (
            {**outside, "base_prefix": str(home / "py")},
            {**outside, "base_executable": str(home / "py" / "python3")},
            {**outside, "base_prefix": str(link)},  # a link into the home
            {"base_prefix": "/usr"},  # not reported: cannot be shown to be outside
            {**outside, "base_executable": ""},
        ):
            assert extract.check_interpreter_outside_home(bad)


def test_process_build_candidate_refuses_a_venv_built_on_a_home_interpreter(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ok, calls, _, _, build_dir, _ = _run_process_build(
        tmp_path, "3.14", actual="3.14.2", candidate=True, base_in_home=True
    )
    assert not ok and not (build_dir / "build-metadata.json").exists()
    assert not any(
        c[0][-1] in {f"import {module}" for module in extract.SANITY_IMPORTS}
        for c in calls
    )  # candidate modules were never imported
    assert "outside the real home" in capsys.readouterr().err


# ---- M3: every candidate extraction starts from a fresh scratch environment --------------------

_ENV_DIRS = ("home", "cache", "tmp", "config", "data", "state", "runtime", "pycache")


def test_candidate_extraction_deletes_the_previous_scratch_environment_before_any_subprocess(
    tmp_path: Path,
) -> None:
    ok, *_, build_dir, _ = _run_process_build(tmp_path, "3.14", candidate=True)
    assert ok
    stale = [
        build_dir / "pycache" / "agent.cpython-314.pyc",
        build_dir / "cache" / "uv" / "wheels" / "stale.whl",
        *(build_dir / name / "stale" for name in _ENV_DIRS if name not in ("pycache", "cache")),
        build_dir / "hermes_home" / "state.db",
    ]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale")
    beside = build_dir / "operator-notes.txt"  # not part of the scratch environment
    beside.write_text("keep")
    first_call_sees: list[list[bool]] = []

    def on_call(cmd) -> None:
        if not first_call_sees:
            first_call_sees.append([path.exists() for path in stale])

    ok, *_ = _run_process_build(tmp_path, "3.14", candidate=True, on_call=on_call)
    assert ok
    assert first_call_sees == [[False] * len(stale)]  # gone before the first candidate command
    assert beside.read_text() == "keep"


def test_candidate_extraction_refuses_a_symlinked_scratch_dir_and_deletes_nothing(
    tmp_path: Path,
) -> None:
    ok, *_, build_dir, _ = _run_process_build(tmp_path, "3.14", candidate=True)
    assert ok
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("precious")
    (build_dir / "cache").rename(tmp_path / "old-cache")
    (build_dir / "cache").symlink_to(victim)
    ran: list[list[str]] = []
    with pytest.raises(SystemExit, match="symlink"):
        _run_process_build(tmp_path, "3.14", candidate=True, on_call=ran.append)
    assert ran == []
    assert (victim / "keep").read_text() == "precious"


def test_listed_build_extraction_keeps_its_scratch_environment_between_runs(
    tmp_path: Path,
) -> None:
    ok, *_, build_dir, _ = _run_process_build(tmp_path, "3.14")
    assert ok
    (build_dir / "cache").mkdir(exist_ok=True)
    (build_dir / "cache" / "warm").write_text("kept")  # a listed build's cache is not reset
    ok, *_ = _run_process_build(tmp_path, "3.14")
    assert ok and (build_dir / "cache" / "warm").read_text() == "kept"


# ---- M4: build-metadata.json is written like every other private file --------------------------


def _metadata_call(tmp_path: Path, build_dir: Path):
    src = build_dir / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "uv.lock").write_bytes(b"version = 1\n")
    build = extract.Build("candidate", "hermes-agent", _SHA, False, "3.14", True)
    return extract.write_build_metadata(
        build, _SHA, src, build_dir, {"version": "3.14.0"}, "uv 9", {"agent": True}
    )


@pytest.mark.parametrize("plant", ["symlink", "dangling_symlink", "hard_link", "directory"])
def test_write_build_metadata_refuses_anything_planted_at_the_path_and_never_touches_the_target(
    tmp_path: Path, plant: str
) -> None:
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    target = tmp_path / "victim.txt"
    meta = build_dir / "build-metadata.json"
    if plant == "symlink":
        target.write_text("precious")
        meta.symlink_to(target)
    elif plant == "dangling_symlink":
        meta.symlink_to(target)
    elif plant == "hard_link":
        target.write_text("precious")
        os.link(target, meta)
    else:
        meta.mkdir()
    with pytest.raises(SystemExit, match=r"cannot write build-metadata\.json"):
        _metadata_call(tmp_path, build_dir)
    if plant in ("symlink", "hard_link"):
        assert target.read_text() == "precious"
    else:
        assert not target.exists()
    assert os.path.lexists(meta)  # refused, not replaced


def test_write_build_metadata_writes_a_new_private_file(tmp_path: Path) -> None:
    path = _metadata_call(tmp_path, tmp_path / "b")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and not path.is_symlink()
    assert json.loads(path.read_text())["commit"] == _SHA


@pytest.mark.parametrize("candidate", [True, False])
def test_a_symlink_planted_during_extraction_cannot_redirect_the_metadata(
    tmp_path: Path, candidate: bool
) -> None:
    target = tmp_path / "victim.txt"
    target.write_text("precious")
    meta = tmp_path / "out" / ("candidate" if candidate else "b") / "build-metadata.json"

    def plant(cmd) -> None:  # what a build backend or an import could do, after the clean-up
        if cmd[1:] == ["--version"] and not os.path.lexists(meta):
            meta.symlink_to(target)

    with pytest.raises(SystemExit, match=r"cannot write build-metadata\.json"):
        _run_process_build(tmp_path, "3.14", candidate=candidate, on_call=plant)
    assert target.read_text() == "precious"
    assert meta.is_symlink()


# ---- M5: PATH entries that lead into the live ~/.hermes are not usable by a candidate ----------


def _hermes_linking_bin(tmp_path: Path, home: Path) -> Path:
    """A PATH directory OUTSIDE ~/.hermes that holds a working `uv` and a `hermes` that reaches the
    live install only through a chain of two symlinks."""
    live = home / ".hermes" / "hermes-agent" / "venv" / "bin"
    live.mkdir(parents=True)
    (live / "hermes").write_text("#!/bin/sh\n")
    bin_dir = tmp_path / "local-bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text("#!/bin/sh\n")
    uv.chmod(0o755)
    (bin_dir / "hermes-real").symlink_to(live / "hermes")
    (bin_dir / "hermes").symlink_to(bin_dir / "hermes-real")
    return bin_dir


def test_candidate_runs_a_uv_from_a_hermes_linking_dir_by_absolute_path_off_a_scrubbed_path(
    tmp_path: Path,
) -> None:
    bin_dir = _hermes_linking_bin(tmp_path, _fake_home(tmp_path))
    path = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
    ok, calls, *_ = _run_process_build(
        tmp_path, "3.14", candidate=True, real_which=True, extra_env={"PATH": path}
    )
    assert ok
    ((sync, _kw),) = [c for c in calls if c[0][1:2] == ["sync"]]
    assert sync[0] == str(bin_dir / "uv")  # found before the scrub, run by absolute path
    for cmd, kw in calls:
        assert str(bin_dir) not in kw["env"]["PATH"].split(os.pathsep), cmd
        assert Path(cmd[0]).name != "hermes"


def test_listed_build_keeps_its_path_entries_and_runs_a_bare_uv(tmp_path: Path) -> None:
    bin_dir = _hermes_linking_bin(tmp_path, _fake_home(tmp_path))
    path = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
    ok, calls, *_ = _run_process_build(
        tmp_path, "3.14", real_which=True, extra_env={"PATH": path}
    )
    assert ok and calls[0][0][0] == "uv"
    assert str(bin_dir) in calls[0][1]["env"]["PATH"].split(os.pathsep)  # unchanged behaviour


def test_candidate_extraction_stops_with_a_setup_instruction_when_no_safe_uv_exists(
    tmp_path: Path,
) -> None:
    ran: list[list[str]] = []
    with (
        mock.patch.object(extract.safety, "find_executable", return_value=None),
        pytest.raises(SystemExit, match=r"`uv` was not found on PATH.*Install uv"),
    ):
        _run_process_build(tmp_path, "3.14", candidate=True, on_call=ran.append)
    assert ran == []  # nothing ran, in particular no `hermes` and no `uv` from ~/.hermes
    assert not (tmp_path / "out" / "candidate" / "build-metadata.json").exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
