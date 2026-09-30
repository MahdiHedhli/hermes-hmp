"""Tests for the ad-hoc exact candidate path of tools/compat/run_matrix.py (`--candidate-sha`).

Everything runs against throwaway synthetic git clones and extractions in `tmp_path`, with the
account home replaced by a fake directory; the real `_refs` clones, a real Hermes, a real gateway
and the live `~/.hermes` are never involved. The expensive stages (self-check, the pytest read
suite, the SC-007 subprocess) are replaced with fakes wherever a test is about what the matrix does
with their results; the SC-007 end-to-end test runs the real check script, which only reads bridge
files as data.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "run_matrix", Path(__file__).resolve().parents[1] / "run_matrix.py"
)
rm = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["run_matrix"] = rm
_SPEC.loader.exec_module(rm)

from hmp_plugin.compat import (  # noqa: E402 -- run_matrix put server/ on sys.path
    compute_read_bridge_fingerprint,
    load_read_compat_list,
)

safety = rm.safety
BRIDGE_FILES = list(load_read_compat_list(rm.READ_COMPAT_PATH).bridge_files)
SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "fedcba9876543210fedcba9876543210fedcba98"
GENERATED = datetime(2026, 9, 29, 12, 30, 45, tzinfo=UTC)
ALL_CHECKS = (
    "clone_commit_matches", "extraction_metadata_valid", "extraction_metadata_commit_matches",
    "interpreter_matches", "source_fingerprint_matches", "selfcheck_passed",
    "read_suite_passed", "sc007_passed", "sc007_bound_to_candidate", "source_unchanged_after_run",
)
SUITE_FILE = "tests/integration/test_reads_fixture.py"
REAL_RUN = subprocess.run  # for fakes that let git through


@pytest.fixture(autouse=True)
def account_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake account home, so no test depends on where the real one (or pytest's tmp) is."""
    home = (tmp_path / "account_home").resolve()
    home.mkdir()
    monkeypatch.setattr(safety, "real_user_home", lambda: home)
    return home


_GIT_IDENTITY = ("-c", "user.email=t@example.invalid", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false")


def _git(clone: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(clone), *_GIT_IDENTITY, *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _privatize(root: Path) -> None:
    """Directories 0700, files 0600 (whatever the runner's umask): the shape an extraction has."""
    for path in [root, *root.rglob("*")]:
        if path.is_symlink():
            continue
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def _base_interpreter(tmp_path: Path) -> Path:
    """A stand-in system interpreter outside the fake home (never executed by these tests)."""
    python = tmp_path / "sys_python" / "bin" / "python3.14"
    if not python.exists():
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\nexit 1\n")
        os.chmod(python, 0o755)  # noqa: S103 - a system-like interpreter
        os.chmod(python.parent, 0o755)  # noqa: S103 - a system-like bin directory
    return python


def _link_venv(src: Path, target: Path) -> None:
    """What `uv sync` leaves: `.venv/bin/python*` linking to the base, and `pyvenv.cfg`."""
    venv = src / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(target)
    (venv / "bin" / "python3").symlink_to("python")
    (venv / "pyvenv.cfg").write_text(f"home = {target.parent}\n")


class World:
    """A synthetic clone at `refs/hermes-agent` and its (fake) `candidate` extraction, whose
    `.venv` links to a stand-in base interpreter outside the fake home."""

    def __init__(self, tmp_path: Path, python: str = "3.14", recorded: str = "3.14.2") -> None:
        self.python, self.recorded = python, recorded
        self.tmp = tmp_path
        self.refs = tmp_path / "refs"
        self.clone = self.refs / "hermes-agent"
        self.builds = tmp_path / "builds"
        self.build_dir = self.builds / "candidate"
        self.src = self.build_dir / "src"
        self.interpreter = _base_interpreter(tmp_path)
        self.files = {rel: f"# {rel}\n".encode() for rel in BRIDGE_FILES}
        self.files["uv.lock"] = b"version = 1\n"
        subprocess.run(["git", "init", "-q", str(self.clone)], check=True)
        for root in (self.clone, self.src):
            for rel, data in self.files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(data)
        _git(self.clone, "add", "-A")
        _git(self.clone, "commit", "-q", "-m", "candidate")
        self.sha = _git(self.clone, "rev-parse", "HEAD")
        _link_venv(self.src, self.interpreter.resolve())
        self.write_metadata()
        _privatize(self.builds)

    def write_metadata(self, **overrides: object) -> None:
        meta = {
            "label": "candidate", "ref": self.sha, "commit": self.sha,
            "python_requested": self.python, "python_version": self.recorded,
            "python_base_interpreter": str(self.interpreter.resolve()),
            "uv_lock_sha256": hashlib.sha256(self.files["uv.lock"]).hexdigest(),
            "imports_ok": True, "extraction_ok": True,
        }
        meta.update(overrides)
        (self.build_dir / "build-metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    def fingerprint(self) -> str | None:
        return compute_read_bridge_fingerprint(self.src, BRIDGE_FILES)

    def verify(self, sha: str | None = None, python: str | None = None, live: str | None = None,
               base: str = "/usr", **kwargs):
        """`verify_candidate` with both interpreter runs faked: the base probe (`base_probe`,
        answering for whatever real path it is given) and the venv probe (`probe`)."""
        info = {
            "version": live or self.recorded,
            "base_prefix": base,
            "base_executable": f"{base}/bin/python3",
        }
        kwargs.setdefault("interpreter", self.interpreter)

        def base_probe(interpreter, _python, _env):
            return {"version": self.recorded}, {Path(interpreter)}

        with (
            mock.patch.object(rm.extract_mod, "interpreter_info", return_value=info) as probe,
            mock.patch.object(
                rm.extract_mod, "probe_base_interpreter", side_effect=base_probe
            ) as base_probe_mock,
        ):
            self.probe, self.base_probe = probe, base_probe_mock
            return rm.verify_candidate(
                self.builds, self.refs, sha or self.sha, python or self.python, **kwargs
            )


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


# ---- verify_candidate: metadata commit, interpreter, source fingerprint ------------------------


def test_verify_accepts_a_consistent_extraction(world: World) -> None:
    checks, fingerprint = world.verify()
    assert checks == {
        "clone_commit_matches": True, "extraction_metadata_valid": True,
        "extraction_metadata_commit_matches": True, "interpreter_matches": True,
        "source_fingerprint_matches": True,
    }
    assert fingerprint is not None and fingerprint == world.fingerprint()


def test_verify_rejects_a_sha_the_clone_does_not_have(world: World) -> None:
    checks, fingerprint = world.verify(sha=OTHER_SHA)
    assert checks["clone_commit_matches"] is False
    assert checks["extraction_metadata_commit_matches"] is False
    assert fingerprint is None


def test_verify_rejects_metadata_recording_a_different_commit(world: World) -> None:
    world.write_metadata(commit=OTHER_SHA)
    checks, fingerprint = world.verify()
    assert checks["extraction_metadata_commit_matches"] is False
    assert fingerprint is None
    world.write_metadata(ref=OTHER_SHA)  # commit right, ref wrong
    checks, fingerprint = world.verify()
    assert checks["extraction_metadata_commit_matches"] is False and fingerprint is None


@pytest.mark.parametrize(
    "override",
    [{"label": "stock-base"}, {"extraction_ok": False}, {"imports_ok": False},
     {"extraction_ok": "true"}],
)
def test_verify_rejects_unqualified_or_foreign_metadata(world: World, override: dict) -> None:
    world.write_metadata(**override)
    checks, fingerprint = world.verify()
    assert checks["extraction_metadata_valid"] is False
    assert fingerprint is None


@pytest.mark.parametrize("content", [None, "not json", "[]", "null"])
def test_verify_fails_closed_on_missing_or_malformed_metadata(world: World, content) -> None:
    path = world.build_dir / "build-metadata.json"
    if content is None:
        path.unlink()
    else:
        path.write_text(content, encoding="utf-8")
    checks, fingerprint = world.verify()
    assert checks["extraction_metadata_valid"] is False
    assert checks["extraction_metadata_commit_matches"] is False
    assert fingerprint is None


def test_verify_treats_a_symlinked_or_special_metadata_file_as_missing(world: World) -> None:
    path = world.build_dir / "build-metadata.json"
    real = world.tmp / "elsewhere.json"
    real.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(real)
    checks, fingerprint = world.verify()
    assert checks["extraction_metadata_valid"] is False and fingerprint is None
    if hasattr(os, "mkfifo"):  # opening a FIFO for reading must not hang the matrix
        path.unlink()
        os.mkfifo(path)
        checks, fingerprint = world.verify()
        assert checks["extraction_metadata_valid"] is False and fingerprint is None


def test_verify_rejects_a_different_requested_interpreter(world: World) -> None:
    checks, fingerprint = world.verify(python="3.13")
    assert checks["interpreter_matches"] is False and fingerprint is None


def test_verify_rejects_a_venv_interpreter_that_contradicts_the_metadata(world: World) -> None:
    checks, fingerprint = world.verify(live="3.11.9")
    assert checks["interpreter_matches"] is False and fingerprint is None


def test_verify_rejects_metadata_version_outside_the_request(tmp_path: Path) -> None:
    w = World(tmp_path, python="3.14", recorded="3.11.9")
    checks, fingerprint = w.verify()
    assert checks["interpreter_matches"] is False and fingerprint is None


def test_verify_rejects_an_extraction_whose_bridge_source_was_altered(world: World) -> None:
    target = world.src / BRIDGE_FILES[0]
    target.write_bytes(target.read_bytes() + b"# tampered\n")
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


def test_verify_rejects_an_extraction_whose_lockfile_changed(world: World) -> None:
    (world.src / "uv.lock").write_bytes(b"version = 2\n")
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


def test_verify_rejects_an_extraction_missing_a_bridge_file(world: World) -> None:
    (world.src / BRIDGE_FILES[0]).unlink()
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


def test_verify_rejects_a_missing_clone(world: World, tmp_path: Path) -> None:
    empty = tmp_path / "empty_refs"
    empty.mkdir()
    with mock.patch.object(rm.extract_mod, "interpreter_info", return_value={"version": "3.14.2"}):
        checks, fingerprint = rm.verify_candidate(world.builds, empty, world.sha, "3.14")
    assert checks["clone_commit_matches"] is False
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


# ---- verify_candidate: the whole tracked tree, before any candidate Python runs ----------------


def _tracked_file_changes_only_in_content(w: World) -> None:
    (w.src / "uv.lock").write_bytes(b"version = 3\n")


def _tracked_file_gains_exec_bit(w: World) -> None:
    os.chmod(w.src / BRIDGE_FILES[-1], 0o700)


def _untracked_top_level_module(w: World) -> None:
    (w.src / "sitecustomize.py").write_text("import os\n")


def _untracked_module_in_a_package(w: World) -> None:
    (w.src / "gateway" / "evil.py").write_text("import os\n")


def _untracked_pth(w: World) -> None:
    (w.src / "evil.pth").write_text("import os\n")


def _untracked_pycache(w: World) -> None:
    (w.src / "__pycache__").mkdir()
    (w.src / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"\0")


def _untracked_git_dir(w: World) -> None:
    (w.src / ".git").mkdir()


def _egg_info_with_code(w: World) -> None:
    (w.src / "hermes.egg-info").mkdir()
    (w.src / "hermes.egg-info" / "hook.py").write_text("import os\n")


def _bridge_file_is_a_symlink_to_identical_bytes(w: World) -> None:
    real = w.tmp / "identical.py"
    real.write_bytes((w.src / BRIDGE_FILES[0]).read_bytes())
    (w.src / BRIDGE_FILES[0]).unlink()
    (w.src / BRIDGE_FILES[0]).symlink_to(real)


def _tracked_directory_is_a_symlink(w: World) -> None:
    elsewhere = w.tmp / "elsewhere"
    (w.src / "gateway").rename(elsewhere)
    (w.src / "gateway").symlink_to(elsewhere)


def _group_writable_file(w: World) -> None:
    os.chmod(w.src / "uv.lock", 0o660)


def _venv_is_a_symlink(w: World) -> None:
    (w.src / ".venv").rename(w.tmp / "elsewhere")
    (w.src / ".venv").symlink_to(w.tmp / "elsewhere")


_TREE_TAMPERINGS = [
    _tracked_file_changes_only_in_content, _tracked_file_gains_exec_bit,
    _untracked_top_level_module, _untracked_module_in_a_package, _untracked_pth,
    _untracked_pycache, _untracked_git_dir, _egg_info_with_code,
    _bridge_file_is_a_symlink_to_identical_bytes, _tracked_directory_is_a_symlink,
    _group_writable_file, _venv_is_a_symlink,
]


@pytest.mark.parametrize("tamper", _TREE_TAMPERINGS, ids=lambda f: f.__name__)
def test_verify_rejects_any_unverifiable_tree_without_running_its_interpreter(
    world: World, tamper
) -> None:
    tamper(world)
    problems: list[str] = []
    checks, fingerprint = world.verify(problems=problems)
    assert checks["source_fingerprint_matches"] is False
    assert checks["interpreter_matches"] is False
    assert fingerprint is None and problems
    world.probe.assert_not_called()  # the venv interpreter of an unverified tree never runs
    world.base_probe.assert_not_called()  # ... and no interpreter at all runs before the proof


def test_verify_runs_the_interpreter_only_after_the_tree_is_proven_and_with_the_given_env(
    world: World,
) -> None:
    env = {"PATH": "/usr/bin", "HOME": str(world.tmp / "scratch_home")}
    checks, fingerprint = world.verify(env=env)
    assert fingerprint is not None and checks["interpreter_matches"] is True
    world.probe.assert_called_once_with(world.src, env)
    world.base_probe.assert_called_once_with(world.interpreter.resolve(), world.python, env)


# ---- F2: the venv's interpreter is resolved and inspected before it is ever executed -----------


def _home_python(account_home: Path) -> Path:
    python = account_home / ".local" / "share" / "uv" / "python" / "bin" / "python3.14"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit 1\n")
    os.chmod(python, 0o755)  # noqa: S103 - an executable fixture that is never executed
    return python


def _relink_venv_python(world: World, name: str, target: Path) -> None:
    link = world.src / ".venv" / "bin" / name
    if os.path.lexists(link):
        link.unlink()
    link.symlink_to(target)


def test_verify_never_executes_a_venv_python_symlinked_into_the_home(
    world: World, account_home: Path
) -> None:
    """The symlink-to-home negative: zero subprocess calls to that interpreter, and in fact none
    to the venv at all, because `.venv/bin/python*` is resolved before anything runs."""
    home_python = _home_python(account_home)
    _relink_venv_python(world, "python", home_python)
    base = world.interpreter.resolve()
    seen: list[list[str]] = []

    def fake_run(cmd, *a, **kw):
        if cmd[0] == "git":
            return REAL_RUN(cmd, *a, **kw)
        seen.append(list(cmd))
        info = {"version": world.recorded, "executable": str(base), "base_prefix": "/usr",
                "base_executable": str(base)}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(info), stderr="")

    problems: list[str] = []
    with mock.patch.object(subprocess, "run", fake_run):  # the REAL base probe and venv probe
        checks, fingerprint = rm.verify_candidate(
            world.builds, world.refs, world.sha, world.python,
            interpreter=world.interpreter, problems=problems,
        )
    assert checks["interpreter_matches"] is False and fingerprint is None
    assert any("real user home" in p for p in problems)
    assert [c[0] for c in seen] == [str(base)]  # only the validated base interpreter ran
    for cmd in seen:
        assert not os.path.realpath(cmd[0]).startswith(str(account_home))
        assert ".venv" not in cmd[0]


@pytest.mark.parametrize(
    "tamper", ["sibling_into_home", "pyvenv_home_in_home", "other_interpreter", "no_pyvenv_cfg"]
)
def test_verify_refuses_a_venv_that_does_not_lead_only_to_the_given_interpreter(
    world: World, account_home: Path, tamper: str
) -> None:
    if tamper == "sibling_into_home":  # `python` is fine, `python3.14` (shebangs) is not
        _relink_venv_python(world, "python3.14", _home_python(account_home))
    elif tamper == "pyvenv_home_in_home":
        (world.src / ".venv" / "pyvenv.cfg").write_text(f"home = {account_home / 'py'}\n")
    elif tamper == "other_interpreter":
        other = world.tmp / "other" / "python3.14"
        other.parent.mkdir()
        other.write_text("#!/bin/sh\n")
        os.chmod(other, 0o755)  # noqa: S103 - an executable fixture that is never executed
        _relink_venv_python(world, "python", other)
    else:
        (world.src / ".venv" / "pyvenv.cfg").unlink()
    problems: list[str] = []
    checks, fingerprint = world.verify(problems=problems)
    assert checks["interpreter_matches"] is False and fingerprint is None
    assert any(p.startswith("interpreter:") for p in problems)
    world.probe.assert_not_called()  # the venv's interpreter never ran


def test_verify_fails_closed_without_an_interpreter_or_with_one_in_the_home(
    world: World, account_home: Path
) -> None:
    problems: list[str] = []
    checks, fingerprint = world.verify(interpreter=None, problems=problems)
    assert checks["interpreter_matches"] is False and fingerprint is None
    assert any("--candidate-interpreter" in p for p in problems)
    world.base_probe.assert_not_called()
    world.probe.assert_not_called()
    link = world.tmp / "usr-local-python3.14"
    link.symlink_to(_home_python(account_home))
    checks, fingerprint = world.verify(interpreter=link)
    assert checks["interpreter_matches"] is False and fingerprint is None
    world.base_probe.assert_not_called()  # validated without being run, and refused
    world.probe.assert_not_called()


def test_main_refuses_an_interpreter_symlinked_into_the_home_before_anything_runs(
    tmp_path: Path, account_home: Path
) -> None:
    link = tmp_path / "usr-local-python3.14"
    link.symlink_to(_home_python(account_home))
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--candidate-interpreter", str(link))
    with (
        mock.patch.object(rm, "run_candidate") as run,
        mock.patch.object(subprocess, "run") as spawned,
        mock.patch.object(subprocess, "Popen") as popen,
        pytest.raises(SystemExit, match="real user home"),
    ):
        rm.main(argv)
    run.assert_not_called()
    spawned.assert_not_called()
    popen.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_verify_rejects_metadata_recording_another_base_interpreter(world: World) -> None:
    world.write_metadata(python_base_interpreter="/opt/other/python3.14")
    checks, fingerprint = world.verify()
    assert checks["interpreter_matches"] is False and fingerprint is None


def test_verify_tolerates_the_known_generated_pieces_of_an_extraction(world: World) -> None:
    (world.src / ".venv" / "lib").mkdir(parents=True)
    (world.src / ".venv" / "lib" / "site.py").write_text("not inspected\n")
    egg = world.src / "hermes_agent.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_text("Name: hermes\n")
    _privatize(egg)  # whatever the runner's umask
    _, fingerprint = world.verify()
    assert fingerprint == world.fingerprint()


def test_verify_refuses_a_symlinked_source_or_build_directory(world: World) -> None:
    real_build = world.tmp / "real_build"
    world.build_dir.rename(real_build)
    world.build_dir.symlink_to(real_build)
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None
    world.build_dir.unlink()
    real_build.rename(world.build_dir)
    real_src = world.tmp / "real_src"
    world.src.rename(real_src)
    world.src.symlink_to(real_src)
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


def test_verify_refuses_a_builds_directory_others_can_write(world: World) -> None:
    os.chmod(world.builds, 0o777)  # noqa: S103 - intentional unsafe-mode fixture
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None
    os.chmod(world.builds, 0o700)
    os.chmod(world.build_dir, 0o775)  # noqa: S103 - intentional unsafe-mode fixture
    checks, fingerprint = world.verify()
    assert checks["source_fingerprint_matches"] is False and fingerprint is None


def test_verify_refuses_a_clone_that_leads_into_the_live_hermes_home(
    world: World, tmp_path: Path, account_home: Path
) -> None:
    (account_home / ".hermes").symlink_to(world.refs)  # the "live" home now IS the clone's refs
    problems: list[str] = []
    checks, fingerprint = world.verify(problems=problems)
    assert checks["clone_commit_matches"] is False
    assert checks["source_fingerprint_matches"] is False and fingerprint is None
    assert any("live Hermes home" in p for p in problems)


# ---- selfcheck: an exit-0 SKIP is not a pass ---------------------------------------------------


@pytest.mark.parametrize(
    ("ok", "log", "expected"),
    [
        (True, "OK: 'candidate' reads back through the read path exactly as built.\n", True),
        (True, "SKIP: server/hmp_plugin/reads.py is still the T030 stub\n", False),
        (True, "", False),
        (True, "OK: 'stock-base' reads back through the read path.\n", False),
        (False, "OK: 'candidate' reads back through the read path.\n", False),
        (True, "SKIP: x\nOK: 'candidate' reads back\n", False),
    ],
)
def test_selfcheck_really_ran(ok: bool, log: str, expected: bool) -> None:
    assert rm.selfcheck_really_ran(ok, log, "candidate") is expected


# ---- read suite: exact node ids, never -k, never zero tests, nothing unparseable ---------------


def _collected(*lines: str, count: int | None = None) -> str:
    n = len(lines) if count is None else count
    return "\n".join(lines) + f"\n\n{n} tests collected in 0.02s\n"


_COLLECTED_IDS = (
    f"{SUITE_FILE}::test_append_gives_rows[stock-base]",
    f"{SUITE_FILE}::test_append_gives_rows[experimental]",
    f"{SUITE_FILE}::test_append_gives_rows[candidate]",
    f"{SUITE_FILE}::test_new_session[stock-base]",
    f"{SUITE_FILE}::test_new_session[candidate]",
)
_COLLECTED = _collected(*_COLLECTED_IDS)
_CANDIDATE_IDS = [
    f"{SUITE_FILE}::test_append_gives_rows[candidate]",
    f"{SUITE_FILE}::test_new_session[candidate]",
]


def test_parse_collected_ids_returns_every_parametrized_node_id() -> None:
    parsed = rm.parse_collected_ids(_COLLECTED)
    assert parsed is not None and len(parsed) == 5
    assert (f"{SUITE_FILE}::test_new_session[candidate]", "test_new_session", "candidate") in parsed
    # warnings after the summary are none of its business
    noisy = _COLLECTED + "\n=== warnings summary ===\nsome.py::thing: UserWarning\n"
    assert rm.parse_collected_ids(noisy) == parsed


@pytest.mark.parametrize(
    "output",
    [
        _collected(f"{SUITE_FILE}::test_plain"),  # collected, but not parametrized
        _collected(f"{SUITE_FILE}::test_a[candidate]", "garbage line that is no node id"),
        _collected("m.py::test_a[candidate]"),  # a different file than the read suite
        _collected(f"{SUITE_FILE}::test_a[candidate]", count=2),  # summary disagrees: one unparsed
        _collected(f"{SUITE_FILE}::test_a[candidate]", f"{SUITE_FILE}::test_b[x", count=2),
        _collected(f"{SUITE_FILE}::test_a[candidate]", f"{SUITE_FILE}::Class::test_b[x]", count=2),
        f"{SUITE_FILE}::test_a[candidate]\n",  # no summary at all
        "no tests collected in 0.01s\n",
        "",
    ],
)
def test_parse_collected_ids_fails_closed_on_anything_it_cannot_parse(output: str) -> None:
    assert rm.parse_collected_ids(output) is None


def test_select_exact_node_ids_matches_the_parameter_exactly() -> None:
    assert rm.select_exact_node_ids(rm.parse_collected_ids(_COLLECTED), "candidate") == (
        _CANDIDATE_IDS
    )
    lookalikes = _collected(*(
        f"{SUITE_FILE}::test_a[{p}]"
        for p in ("candidate2", "my-candidate", "candidate-x", "Candidate", "stock-base")
    ))
    assert rm.select_exact_node_ids(rm.parse_collected_ids(lookalikes), "candidate") is None


def test_select_exact_node_ids_fails_closed_on_zero_or_partial_coverage() -> None:
    no_candidate = _collected(*(line for line in _COLLECTED_IDS if "[candidate]" not in line))
    assert rm.select_exact_node_ids(rm.parse_collected_ids(no_candidate), "candidate") is None
    assert rm.select_exact_node_ids([], "candidate") is None
    partial = _collected(f"{SUITE_FILE}::test_a[candidate]", f"{SUITE_FILE}::test_b[stock-base]")
    assert rm.select_exact_node_ids(rm.parse_collected_ids(partial), "candidate") is None


def _junit(tests: int, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    return (
        '<?xml version="1.0"?><testsuites><testsuite name="pytest" '
        f'errors="{errors}" failures="{failures}" skipped="{skipped}" tests="{tests}">'
        "</testsuite></testsuites>"
    )


def _run_suite(tmp_path: Path, *, collected: str = _COLLECTED, junit: str | None = None,
               collect_rc: int = 0, run_rc: int = 0, env: dict | None = None):
    calls: list[tuple[list[str], dict]] = []

    def fake_run(cmd, **kw):
        calls.append((list(cmd), kw))
        if "--collect-only" in cmd:
            return subprocess.CompletedProcess(cmd, collect_rc, stdout=collected, stderr="")
        path = next(a for a in cmd if a.startswith("--junitxml=")).split("=", 1)[1]
        if junit is not None:
            Path(path).write_text(junit, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, run_rc, stdout="", stderr="")

    with mock.patch.object(rm.subprocess, "run", fake_run):
        result = rm.run_read_suite_exact(
            "candidate", tmp_path / "b", tmp_path, env if env is not None else {"X": "1"}
        )
    return result, [c for c, _kw in calls], [kw for _c, kw in calls]


def test_read_suite_runs_exactly_the_selected_node_ids_without_k(tmp_path: Path) -> None:
    (passed, ran, _log), calls, kws = _run_suite(tmp_path, junit=_junit(2), env={"X": "1"})
    assert passed is True and ran == 2
    assert len(calls) == 2
    for cmd in calls:
        assert "-k" not in cmd and not any(a.startswith("-k") for a in cmd)
        assert "addopts=" in cmd  # `-o addopts=` -- no ambient pytest options
    assert calls[1][-2:] == _CANDIDATE_IDS
    assert str(rm.READ_SUITE) not in calls[1]  # whole-file selection would run other builds too
    assert all(kw["env"] == {"X": "1"} for kw in kws)  # the scrubbed env, not the ambient one


def test_read_suite_uses_a_private_basetemp_under_scratch(tmp_path: Path) -> None:
    stale = tmp_path / "pytest-basetemp" / "old"
    stale.mkdir(parents=True)
    (passed, *_), calls, _ = _run_suite(tmp_path, junit=_junit(2))
    assert passed is True
    assert f"--basetemp={tmp_path / 'pytest-basetemp'}" in calls[1]
    assert not any(a.startswith("--basetemp") for a in calls[0])
    assert not stale.exists()  # a previous run's temp files are never evidence or clutter


def test_read_suite_refuses_a_symlinked_basetemp_and_deletes_nothing(tmp_path: Path) -> None:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("x")
    (tmp_path / "pytest-basetemp").symlink_to(victim)
    (passed, ran, _log), calls, _ = _run_suite(tmp_path, junit=_junit(2))
    assert (passed, ran) == (False, 0) and len(calls) == 1  # never reached the run step
    assert (victim / "keep").exists()


@pytest.mark.parametrize(
    "junit",
    [
        None, "<not xml", "<testsuites/>", _junit(0), _junit(1), _junit(3),
        _junit(2, skipped=2), _junit(2, skipped=1), _junit(2, failures=1), _junit(2, errors=1),
    ],
)
def test_read_suite_fails_closed_unless_every_selected_test_ran_and_passed(
    tmp_path: Path, junit: str | None
) -> None:
    (passed, _ran, _log), _calls, _kws = _run_suite(tmp_path, junit=junit)
    assert passed is False


def test_read_suite_fails_when_pytest_itself_fails_despite_clean_junit(tmp_path: Path) -> None:
    (passed, *_), _, _ = _run_suite(tmp_path, junit=_junit(2), run_rc=1)
    assert passed is False


def test_read_suite_with_no_candidate_tests_never_reaches_the_run_step(tmp_path: Path) -> None:
    only_listed = _collected(*(line for line in _COLLECTED_IDS if "[candidate]" not in line))
    (passed, ran, _log), calls, _ = _run_suite(tmp_path, collected=only_listed, junit=_junit(0))
    assert (passed, ran) == (False, 0)
    assert len(calls) == 1 and "--collect-only" in calls[0]


def test_read_suite_fails_when_any_collected_test_cannot_be_parsed(tmp_path: Path) -> None:
    hostile = _collected(*_COLLECTED_IDS, f"{SUITE_FILE}::test_unparametrized")
    (passed, ran, log), calls, _ = _run_suite(tmp_path, collected=hostile, junit=_junit(2))
    assert (passed, ran) == (False, 0) and len(calls) == 1
    assert "could not be parsed" in log


def test_read_suite_collection_failure_is_a_failure(tmp_path: Path) -> None:
    (passed, ran, _log), calls, _ = _run_suite(tmp_path, collect_rc=2, junit=_junit(2))
    assert (passed, ran) == (False, 0) and len(calls) == 1


def test_stale_junit_from_an_earlier_run_is_not_evidence(tmp_path: Path) -> None:
    (tmp_path / "read-suite-junit.xml").write_text(_junit(2), encoding="utf-8")
    (passed, *_), _, _ = _run_suite(tmp_path, junit=None)  # this run wrote no report
    assert passed is False


# ---- read suite opt-in: `candidate` is parametrized only when explicitly asked -----------------


def _reads_fixture_builds(opt_in: str | None, tmp_path: Path) -> tuple[str, ...]:
    builds = tmp_path / "opt_in_builds"
    (builds / "candidate" / "src").mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "reads_fixture_opt_in_probe", rm.READ_SUITE
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, {"HMP_HERMES_BUILDS_DIR": str(builds)}):
        if opt_in is None:
            os.environ.pop(rm.CANDIDATE_OPT_IN_ENV, None)
        else:
            os.environ[rm.CANDIDATE_OPT_IN_ENV] = opt_in
        spec.loader.exec_module(module)
    return tuple(module.BUILDS)


def test_the_read_suite_never_parametrizes_candidate_without_the_explicit_opt_in(
    tmp_path: Path,
) -> None:
    for value in (None, "", "0", "true", "yes", "2"):
        assert "candidate" not in _reads_fixture_builds(value, tmp_path)
    assert "candidate" in _reads_fixture_builds("1", tmp_path)
    assert rm.CANDIDATE_OPT_IN_ENV == "HMP_ENABLE_CANDIDATE_BUILD"


# ---- SC-007 bound to the candidate tree --------------------------------------------------------

_SC007_OK = json.dumps({
    "status": "unsupported", "why": "hermes_build_unsupported", "probe_calls": 0,
    "pristine_status": "supported", "pristine_entry": "candidate", "pristine_probe_calls": 1,
    "bridge_imported": False, "origin_ok": True,
})


def _sc007_output(**over: object) -> str:
    return json.dumps({**json.loads(_SC007_OK), **over}) + "\n"


def _sc007(world: World, scratch: Path, stdout: str = _SC007_OK + "\n", **kwargs):
    """Run `unsupported_path_check` with the check subprocess faked; return (result, cmd, kw)."""
    seen: dict = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = list(cmd), kw
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    kwargs.setdefault("expected_fingerprint", world.fingerprint())
    with mock.patch.object(rm.subprocess, "run", fake_run):
        result = rm.unsupported_path_check(world.builds, "candidate", scratch, **kwargs)
    return result, seen.get("cmd"), seen.get("kw")


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    return safety.ensure_private_dir(tmp_path / "scratch")


def test_sc007_checks_copies_of_the_bridge_files_against_a_scratch_list(
    world: World, scratch: Path
) -> None:
    committed = rm.READ_COMPAT_PATH.read_bytes()
    seen: dict = {}

    def fake_run(cmd, **kw):
        server, mutant, pristine, list_path, mode = cmd[4:9]
        seen.update(
            server=server, mode=mode, list=json.loads(Path(list_path).read_text()),
            list_mode=stat.S_IMODE(Path(list_path).stat().st_mode),
            mutant_fp=compute_read_bridge_fingerprint(Path(mutant), BRIDGE_FILES),
            pristine_fp=compute_read_bridge_fingerprint(Path(pristine), BRIDGE_FILES),
            mutant_files=sorted(p.name for p in Path(mutant).iterdir()),
            cmd=list(cmd), kw=kw,
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=_SC007_OK + "\n", stderr="")

    env = {"PATH": "/usr/bin", "HOME": str(scratch / "home")}
    with mock.patch.object(rm.subprocess, "run", fake_run):
        result = rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint=world.fingerprint(),
            env=env, source_sha=world.sha,
        )
    assert result["ok"] is True and result["label"] == "candidate"
    assert result["source_matches_expected"] is True and result["pristine_supported"] is True
    assert result["status"] == "unsupported" and result["bridge_imported"] is False
    # the pristine copy IS the verified candidate, the mutated copy is not
    assert seen["pristine_fp"] == world.fingerprint()
    assert seen["mutant_fp"] not in (None, world.fingerprint())
    assert seen["mode"] == "candidate" and seen["server"] == str(rm.SERVER_DIR)
    # the scratch list lists ONLY the candidate's own verified fingerprint, as one exact row
    assert seen["list"]["bridge_files"] == BRIDGE_FILES
    assert seen["list"]["builds"] == [{
        "label": "candidate", "fingerprint": world.fingerprint(), "git_sha": None,
        "source_sha": world.sha, "qualified_by": mock.ANY, "qualified_at": mock.ANY,
    }]
    assert seen["list_mode"] == 0o600
    assert seen["mutant_files"] == sorted({rel.split("/")[0] for rel in BRIDGE_FILES})
    # nothing was committed or edited, and the check cannot see the candidate tree at all
    assert rm.READ_COMPAT_PATH.read_bytes() == committed
    assert str(world.src) not in " ".join(seen["cmd"])
    assert seen["cmd"][:3] == [sys.executable, "-I", "-c"]  # isolated: no PYTHON*, no cwd path
    assert seen["kw"]["env"] == env
    assert Path(seen["kw"]["cwd"]).is_relative_to(scratch)


def test_sc007_mutation_changes_exactly_one_byte(world: World, scratch: Path) -> None:
    seen: dict = {}

    def fake_run(cmd, **kw):
        seen["mutant"] = Path(cmd[5])
        return subprocess.CompletedProcess(cmd, 0, stdout=_SC007_OK + "\n", stderr="")

    with mock.patch.object(rm.subprocess, "run", fake_run):
        rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint=world.fingerprint()
        )
    changed = 0
    for rel in BRIDGE_FILES:
        before, after = (world.src / rel).read_bytes(), (seen["mutant"] / rel).read_bytes()
        assert len(before) == len(after)
        changed += sum(a != b for a, b in zip(before, after, strict=True))
    assert changed == 1


def test_flip_one_byte_handles_empty_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.write_bytes(b"")
    rm._flip_one_byte(empty)
    assert empty.read_bytes() == b"\0"
    full = tmp_path / "full"
    full.write_bytes(b"abc")
    rm._flip_one_byte(full)
    assert full.read_bytes() == b"abb"


def test_sc007_refuses_a_tree_that_is_not_the_verified_candidate(
    world: World, scratch: Path
) -> None:
    with mock.patch.object(rm.subprocess, "run", side_effect=AssertionError("must not run")):
        result = rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint="0" * 64
        )
    assert result["ok"] is False and result["source_matches_expected"] is False


@pytest.mark.parametrize(
    "output",
    [
        _sc007_output(status="supported", why=None),  # the mutated copy was NOT refused
        _sc007_output(why="read_dependency_missing"),  # refused for the wrong reason
        _sc007_output(bridge_imported=True),  # a bridge import happened
        _sc007_output(bridge_imported=None),
        _sc007_output(origin_ok=False),  # HMP was not imported from the reviewed server dir
        _sc007_output(probe_calls=1),  # the mutated copy reached the dependency probe
        _sc007_output(pristine_status="unsupported"),  # the pristine candidate is not supported
        _sc007_output(pristine_entry="stock-base"),  # ... matched some other row
        _sc007_output(pristine_entry=None),
        _sc007_output(pristine_probe_calls=0),
        "",  # the check crashed
        "not json\n",
    ],
)
def test_sc007_only_passes_when_refusal_and_pristine_support_are_both_proven(
    world: World, scratch: Path, output: str
) -> None:
    result, _cmd, _kw = _sc007(world, scratch, stdout=output)
    assert result["ok"] is False


def test_sc007_listed_call_keeps_its_old_signature_and_uses_the_committed_list(
    world: World, scratch: Path
) -> None:
    result, cmd, _kw = _sc007(world, scratch, expected_fingerprint=None)
    assert result["ok"] is True and result["source_matches_expected"] is None
    assert result["pristine_supported"] is None
    assert cmd[8] == "listed" and cmd[7] == str(rm.READ_COMPAT_PATH)
    # a listed check needs no pristine verdict
    result, _cmd, _kw = _sc007(
        world, scratch, expected_fingerprint=None,
        stdout=_sc007_output(pristine_status=None, pristine_entry=None, pristine_probe_calls=None),
    )
    assert result["ok"] is True


def test_sc007_never_follows_a_symlinked_bridge_file(world: World, scratch: Path) -> None:
    secret = world.tmp / "secret.txt"
    secret.write_text("TOP SECRET")
    target = world.src / BRIDGE_FILES[0]
    target.unlink()
    target.symlink_to(secret)
    with mock.patch.object(rm.subprocess, "run", side_effect=AssertionError("must not run")):
        result = rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint="0" * 64
        )
    assert result["ok"] is False and "not a regular file" in result["stderr_tail"]
    assert "TOP SECRET" not in "".join(
        p.read_text() for p in scratch.rglob("*") if p.is_file()
    )


def test_sc007_never_follows_a_symlinked_directory_or_reads_the_venv(
    world: World, scratch: Path
) -> None:
    (world.src / ".venv" / "lib").mkdir(parents=True)
    (world.src / ".venv" / "lib" / "evil.py").write_text("import os\n")
    elsewhere = world.tmp / "elsewhere"
    (world.src / "gateway").rename(elsewhere)
    (world.src / "gateway").symlink_to(elsewhere)
    with mock.patch.object(rm.subprocess, "run", side_effect=AssertionError("must not run")):
        result = rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint=world.fingerprint()
        )
    assert result["ok"] is False and "not a real directory" in result["stderr_tail"]
    assert not list(scratch.rglob("evil.py"))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs FIFOs")
def test_sc007_refuses_unsafe_bridge_file_types_without_blocking(
    world: World, scratch: Path
) -> None:
    fingerprint = world.fingerprint()  # before the FIFO exists: reading a FIFO would block
    fifo = world.src / BRIDGE_FILES[0]
    fifo.unlink()
    os.mkfifo(fifo)
    with mock.patch.object(rm.subprocess, "run", side_effect=AssertionError("must not run")):
        result = rm.unsupported_path_check(
            world.builds, "candidate", scratch, expected_fingerprint=fingerprint
        )
    assert result["ok"] is False and "not a regular file" in result["stderr_tail"]


def test_sc007_scratch_is_private_and_stale_copies_are_removed(
    world: World, scratch: Path
) -> None:
    stale = scratch / "sc007" / "mutant" / "stale.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale")
    _sc007(world, scratch)
    assert not stale.exists()
    for path in (scratch / "sc007", scratch / "sc007" / "mutant", scratch / "sc007" / "pristine"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for path in (scratch / "sc007").rglob("*"):
        if path.is_file():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_sc007_end_to_end_lists_the_pristine_copy_and_refuses_the_mutated_one(
    world: World, scratch: Path
) -> None:
    """The real check script under `python -I`: nothing mocked but the environment."""
    committed = rm.READ_COMPAT_PATH.read_bytes()
    result = rm.unsupported_path_check(
        world.builds, "candidate", scratch, expected_fingerprint=world.fingerprint(),
        env=safety.minimal_env(), source_sha=world.sha,
    )
    assert result["ok"] is True, result
    assert (result["status"], result["why"]) == ("unsupported", "hermes_build_unsupported")
    assert result["bridge_imported"] is False and result["pristine_supported"] is True
    assert result["source_matches_expected"] is True and result["stderr_tail"] == ""
    assert rm.READ_COMPAT_PATH.read_bytes() == committed  # the committed list is never edited
    scratch_list = json.loads(
        (scratch / "sc007" / "provisional_read_compat_builds.json").read_text()
    )
    assert [b["label"] for b in scratch_list["builds"]] == ["candidate"]
    assert scratch_list["builds"][0]["fingerprint"] == world.fingerprint()


# ---- run_candidate: staging, binding and the public report shape -------------------------------

FINGERPRINT = "ab" * 32
_VERIFIED = {
    "clone_commit_matches": True, "extraction_metadata_valid": True,
    "extraction_metadata_commit_matches": True, "interpreter_matches": True,
    "source_fingerprint_matches": True,
}
_SELFCHECK_OK = "OK: 'candidate' reads back through the plugin's read path exactly as built.\n"
_SC007_RESULT = {
    "label": "candidate", "ok": True, "status": "unsupported", "why": "hermes_build_unsupported",
    "bridge_imported": False, "source_matches_expected": True, "pristine_supported": True,
    "stderr_tail": "",
}


class Stages:
    """Patches every expensive stage of `run_candidate`; each fake is a Mock for call assertions."""

    def __init__(self, **over: object) -> None:
        self.verify = mock.Mock(return_value=(dict(_VERIFIED), FINGERPRINT))
        self.selfcheck = mock.Mock(return_value=(True, _SELFCHECK_OK))
        self.suite = mock.Mock(return_value=(True, 7, "suite log"))
        self.sc007 = mock.Mock(return_value=dict(_SC007_RESULT))
        self.recheck = mock.Mock(return_value=True)
        for name, value in over.items():
            setattr(self, name, value)
        self.patches = [
            mock.patch.object(rm, "verify_candidate", self.verify),
            mock.patch.object(rm, "recheck_source", self.recheck),
            mock.patch.object(rm, "run_selfcheck", self.selfcheck),
            mock.patch.object(rm, "run_read_suite_exact", self.suite),
            mock.patch.object(rm, "unsupported_path_check", self.sc007),
            mock.patch.object(rm, "hmp_source_info", return_value={
                "commit": SHA, "version": "1.0.0-f1", "worktree_dirty": False}),
        ]

    def __enter__(self) -> Stages:
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        for p in self.patches:
            p.stop()


def _run(tmp_path: Path) -> dict:
    return rm.run_candidate(
        SHA, "3.14", tmp_path / "refs", tmp_path / "builds", tmp_path / "out", now=GENERATED
    )


def test_a_fully_passing_candidate_reports_every_stage_and_binds_sc007(tmp_path: Path) -> None:
    with Stages() as st:
        report = _run(tmp_path)
    assert report["candidate_passed"] is True and report["failed_stage"] is None
    assert all(report["checks"][name] is True for name in ALL_CHECKS)
    assert report["read_suite_tests_run"] == 7
    # Every stage targets the fixed label; SC-007 gets the fingerprint the verification produced.
    env = st.selfcheck.call_args.args[3]
    assert st.selfcheck.call_args.args[0] == "candidate"
    assert st.suite.call_args.args[0] == "candidate"
    assert st.sc007.call_args.args[:2] == (tmp_path / "builds", "candidate")
    assert st.sc007.call_args.kwargs == {
        "expected_fingerprint": FINGERPRINT, "env": env, "source_sha": SHA,
    }
    assert st.verify.call_args.args == (tmp_path / "builds", tmp_path / "refs", SHA, "3.14")
    assert st.verify.call_args.kwargs["env"] == env  # the interpreter probe is scrubbed too


def test_stages_run_in_order_and_stop_at_the_first_failure(tmp_path: Path) -> None:
    with Stages(verify=mock.Mock(
        return_value=({**_VERIFIED, "extraction_metadata_commit_matches": False}, None)
    )) as st:
        report = _run(tmp_path)
    assert report["failed_stage"] == "extraction_verification"
    assert report["checks"]["extraction_metadata_commit_matches"] is False
    for later in (st.selfcheck, st.suite, st.sc007):
        later.assert_not_called()
    assert report["sc007"]["ran"] is False and report["candidate"]["fingerprint"] is None

    for name, stage in (("selfcheck", "selfcheck"), ("suite", "read_suite")):
        failing = mock.Mock(return_value=(False, "FAIL") if name == "selfcheck"
                            else (False, 0, "log"))
        with Stages(**{name: failing}) as st:
            report = _run(tmp_path)
        assert report["failed_stage"] == stage and report["candidate_passed"] is False
        st.sc007.assert_not_called()


def test_a_selfcheck_skip_is_not_a_pass(tmp_path: Path) -> None:
    with Stages(selfcheck=mock.Mock(return_value=(True, "SKIP: reads.py is a stub\n"))) as st:
        report = _run(tmp_path)
    assert report["checks"]["selfcheck_passed"] is False
    assert report["failed_stage"] == "selfcheck" and report["candidate_passed"] is False
    st.suite.assert_not_called()


@pytest.mark.parametrize(
    "override",
    [
        {"label": "stock-base"},  # ran against some other build
        {"source_matches_expected": False},  # copy was not the verified candidate
        {"source_matches_expected": None},  # nothing proved the copy
        {"pristine_supported": False},  # the scratch list did not list/support the candidate
        {"pristine_supported": None},  # nothing proved it did
        {"ok": False},  # gate did not refuse the mutant
    ],
)
def test_sc007_only_passes_when_bound_to_the_verified_candidate(
    tmp_path: Path, override: dict
) -> None:
    with Stages(sc007=mock.Mock(return_value={**_SC007_RESULT, **override})):
        report = _run(tmp_path)
    assert report["checks"]["sc007_passed"] is False
    assert report["failed_stage"] == "sc007" and report["candidate_passed"] is False


def test_report_shape_records_provenance_and_named_booleans(tmp_path: Path) -> None:
    with Stages():
        report = _run(tmp_path)
    assert list(report) == [
        "format", "mode", "generated_at", "hmp_source", "matrix_runtime", "candidate",
        "runtime_dependencies", "checks", "read_suite_tests_run", "sc007", "failed_stage",
        "candidate_passed", "assurance",
    ]
    assert "non-adversarial compatibility evidence only" in report["assurance"]
    assert "not an attestation" in report["assurance"] and "not a sandbox" in report["assurance"]
    assert report["format"] == 1 and report["mode"] == "candidate"
    assert report["generated_at"] == "2026-09-29T12:30:45Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", report["generated_at"])
    assert report["hmp_source"] == {"commit": SHA, "version": "1.0.0-f1", "worktree_dirty": False}
    assert set(report["matrix_runtime"]) == {"os", "python"}
    assert re.fullmatch(r"3\.\d+", report["matrix_runtime"]["python"])  # coarse: no patch level
    assert report["candidate"] == {
        "label": "candidate", "commit": SHA, "python_requested": "3.14",
        "fingerprint": FINGERPRINT,
    }
    assert set(report["checks"]) == set(ALL_CHECKS)
    assert all(isinstance(v, bool) for v in report["checks"].values())
    assert report["sc007"] == {
        "label": "candidate", "ran": True, "ok": True, "status": "unsupported",
        "why": "hermes_build_unsupported", "bridge_imported": False,
    }
    # The report is public: it has to survive a JSON round trip unchanged.
    assert json.loads(json.dumps(report)) == report


def test_report_leaks_no_paths_secrets_transcripts_or_logs(tmp_path: Path) -> None:
    secret = "sk-ant-SECRET-1234"
    noisy = f"OK: 'candidate' x\nAuthorization: Bearer {secret}\nHOME={tmp_path}\n"
    raw_sc007 = {
        **_SC007_RESULT, "status": f"private-path/{secret}", "why": "A B C",
        "stderr_tail": f"Traceback in {tmp_path}: {secret}",
    }
    with (
        mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": secret}),
        Stages(
            selfcheck=mock.Mock(return_value=(True, noisy)),
            suite=mock.Mock(return_value=(True, 3, f"pytest output {secret} {tmp_path}")),
            sc007=mock.Mock(return_value=raw_sc007),
            verify=mock.Mock(return_value=(dict(_VERIFIED), FINGERPRINT)),
        ),
    ):
        report = _run(tmp_path)
    text = json.dumps(report)
    for needle in (secret, str(tmp_path), "Traceback", "Bearer", "pytest output"):
        assert needle not in text
    strings = [v for v in _walk(report) if isinstance(v, str)]
    assert strings and all("/" not in s for s in strings)
    assert report["sc007"]["status"] is None and report["sc007"]["why"] is None
    # ...but the operator still gets the detail, privately, in the scratch directory.
    assert secret in (tmp_path / "out" / "candidate" / "read-suite.log").read_text()


def _walk(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)
    else:
        yield value


def test_run_candidate_uses_a_scrubbed_private_environment_for_every_subprocess(
    tmp_path: Path,
) -> None:
    poison = {
        "OPENAI_API_KEY": "sk-x", "HTTPS_PROXY": "http://p", "GIT_DIR": "/elsewhere",
        "PYTHONPATH": "/evil", "PYTEST_ADDOPTS": "--evil", "HOME": "/real/home",
        "HERMES_HOME": "/real/home/.hermes", "XDG_STATE_HOME": "/real/state", "TMPDIR": "/real/tmp",
    }
    with mock.patch.dict(os.environ, poison), Stages() as st:
        _run(tmp_path)
    env = st.selfcheck.call_args.args[3]
    assert st.suite.call_args.args[3] is env and st.sc007.call_args.kwargs["env"] is env
    scratch = tmp_path / "out" / "candidate"
    for key in ("HOME", "HERMES_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "TMPDIR", "UV_CACHE_DIR"):
        assert Path(env[key]).is_relative_to(scratch / "env"), key
    for key in ("OPENAI_API_KEY", "HTTPS_PROXY", "GIT_DIR", "PYTHONPATH", "PYTEST_ADDOPTS"):
        assert key not in env
    assert "/real/" not in " ".join(env.values())
    assert env["HMP_HERMES_BUILDS_DIR"] == str(tmp_path / "builds")
    assert env["HMP_ENABLE_CANDIDATE_BUILD"] == "1"  # the read suite's explicit opt-in


def test_run_candidate_creates_only_private_dirs_and_files(tmp_path: Path) -> None:
    with Stages():
        _run(tmp_path)
    out = tmp_path / "out"
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    for path in [out / "candidate", *(out / "candidate").rglob("*")]:
        mode = stat.S_IMODE(path.lstat().st_mode)
        assert mode == (0o700 if path.is_dir() else 0o600), path
    logs = {p.name for p in (out / "candidate").iterdir() if p.is_file()}
    assert logs == {
        "verification.log", "selfcheck.log", "read-suite.log", "sc007.log",
        "post-run-verification.log",
    }


def test_run_candidate_runs_stages_under_a_private_umask_and_restores_it(tmp_path: Path) -> None:
    seen: list[int] = []

    def selfcheck(*_a, **_kw):
        current = os.umask(0o077)
        os.umask(current)
        seen.append(current)
        return True, _SELFCHECK_OK

    previous = os.umask(0o022)
    try:
        with Stages(selfcheck=selfcheck):
            _run(tmp_path)
        after = os.umask(0o022)
    finally:
        os.umask(previous)
    assert seen == [0o077]  # children the stages start inherit it
    assert after == 0o022


def test_run_candidate_removes_a_stale_selfcheck_fixture(tmp_path: Path) -> None:
    stale = tmp_path / "out" / "candidate" / "selfcheck" / "homes" / "old"
    stale.mkdir(parents=True)
    with Stages() as st:
        _run(tmp_path)
    assert not stale.exists()
    assert st.selfcheck.call_args.args[1] == tmp_path / "out" / "candidate" / "selfcheck"


@pytest.mark.parametrize(
    "make",
    [
        lambda t: {"out": _link(t, "out_link", t / "out")},  # symlinked --out
        lambda t: {"builds_dir": _link(t, "builds_link", t / "builds")},
        lambda t: {"out": t / "builds" / "scratch"},  # scratch inside the extracted builds
        lambda t: {"out": t / "refs" / "scratch"},  # scratch inside the refs dir
        lambda t: {"builds_dir": t / "out" / "builds"},  # builds inside scratch
        lambda t: {"out": rm.REPO_ROOT / "scratch"},  # scratch inside the repository
        lambda t: {"out": t / "account_home" / "scratch"},  # inside the real home
        lambda t: {"refs_dir": t / "account_home" / ".hermes" / "refs"},  # live ~/.hermes
        lambda t: {"builds_dir": t / "account_home" / ".hermes" / "builds"},
    ],
)
def test_run_candidate_refuses_unsafe_layouts_before_running_anything(
    tmp_path: Path, make
) -> None:
    (tmp_path / "out").mkdir()
    (tmp_path / "builds").mkdir()
    (tmp_path / "refs").mkdir()
    args = {"refs_dir": tmp_path / "refs", "builds_dir": tmp_path / "builds",
            "out": tmp_path / "out"}
    args.update(make(tmp_path))
    with Stages() as st, pytest.raises(SystemExit, match="refusing"):
        rm.run_candidate(SHA, "3.14", args["refs_dir"], args["builds_dir"], args["out"])
    for stage in (st.verify, st.selfcheck, st.suite, st.sc007):
        stage.assert_not_called()


def _link(tmp_path: Path, name: str, target: Path) -> Path:
    target.mkdir(exist_ok=True)
    link = tmp_path / name
    link.symlink_to(target)
    return link


def test_hmp_source_info_shape() -> None:
    info = rm.hmp_source_info()
    assert set(info) == {"commit", "version", "worktree_dirty"}
    assert info["commit"] is None or re.fullmatch(r"[0-9a-f]{40}", info["commit"])
    assert isinstance(info["version"], str) and isinstance(info["worktree_dirty"], bool)


def test_hmp_source_info_runs_git_hardened_and_without_inherited_git_variables() -> None:
    seen: list[dict] = []
    real_run = subprocess.run

    def spy(cmd, **kw):
        seen.append({"cmd": list(cmd), "env": kw.get("env")})
        return real_run(cmd, **kw)

    with (
        mock.patch.dict(os.environ, {"GIT_DIR": "/elsewhere", "GIT_WORK_TREE": "/elsewhere"}),
        mock.patch.object(rm.subprocess, "run", spy),
    ):
        rm.hmp_source_info()
    assert seen
    for call in seen:
        assert "--no-optional-locks" in call["cmd"] and "--no-replace-objects" in call["cmd"]
        assert "core.fsmonitor=" in call["cmd"]
        assert "GIT_DIR" not in call["env"] and "GIT_WORK_TREE" not in call["env"]


# ---- CLI: selection and rejection --------------------------------------------------------------


def _argv(tmp_path: Path, *extra: str, interpreter: bool = True) -> list[str]:
    """CLI arguments; a candidate run gets `--candidate-interpreter` (a stand-in base Python
    outside the fake home) unless `interpreter=False` or the test names its own."""
    (tmp_path / "builds").mkdir(exist_ok=True)
    argv = ["--out", str(tmp_path / "out"), "--builds-dir", str(tmp_path / "builds"), *extra]
    if interpreter and "--candidate-sha" in extra and "--candidate-interpreter" not in extra:
        argv += ["--candidate-interpreter", str(_base_interpreter(tmp_path))]
    return argv


def _refs(tmp_path: Path) -> str:
    (tmp_path / "refs").mkdir(exist_ok=True)
    return str(tmp_path / "refs")


def _passing_report(passed: bool = True) -> dict:
    return {"candidate_passed": passed, "failed_stage": None if passed else "selfcheck"}


def test_main_runs_only_the_candidate_and_never_touches_listed_builds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    json_out = tmp_path / "out" / "report.json"
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--candidate-python", "3.14.1", "--json-out", str(json_out))
    with (
        mock.patch.object(rm, "run_candidate", return_value=_passing_report()) as run,
        mock.patch.object(rm, "load_build_specs") as specs,
        mock.patch.object(rm, "process_build") as process,
    ):
        assert rm.main(argv) == 0
    run.assert_called_once_with(
        SHA, "3.14.1", tmp_path / "refs", tmp_path / "builds", tmp_path / "out",
        interpreter=str(_base_interpreter(tmp_path)),
    )
    specs.assert_not_called()
    process.assert_not_called()
    assert json.loads(json_out.read_text()) == _passing_report()
    assert stat.S_IMODE(json_out.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "out").stat().st_mode) == 0o700
    captured = capsys.readouterr()
    assert json.loads(captured.out) == _passing_report()
    assert "isolated VM, container or user account" in captured.err


def test_main_candidate_defaults_to_the_same_python_as_extract(tmp_path: Path) -> None:
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA)
    with mock.patch.object(rm, "run_candidate", return_value=_passing_report()) as run:
        rm.main(argv)
    assert run.call_args.args[1] == rm.extract_mod.DEFAULT_PYTHON


def test_main_exit_status_follows_the_candidate_verdict(tmp_path: Path) -> None:
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA)
    with mock.patch.object(rm, "run_candidate", return_value=_passing_report(False)):
        assert rm.main(argv) == 1


@pytest.mark.parametrize(
    "extra",
    [
        ["--candidate-sha", SHA, "--builds", "stock-base", "--refs-dir", "R"],
        ["--candidate-sha", SHA],  # --refs-dir is mandatory for a candidate
        ["--candidate-python", "3.14", "--refs-dir", "R"],  # python without a candidate
        ["--candidate-interpreter", "/usr/bin/python3", "--refs-dir", "R"],  # ... interpreter
        ["--candidate-sha", SHA, "--refs-dir", "R", "NO-INTERPRETER"],  # it is mandatory
    ],
)
def test_main_rejects_unsafe_candidate_combinations(tmp_path: Path, extra: list[str]) -> None:
    with_interpreter = "NO-INTERPRETER" not in extra
    extra = [_refs(tmp_path) if a == "R" else a for a in extra if a != "NO-INTERPRETER"]
    with (
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit) as exc,
    ):
        rm.main(_argv(tmp_path, *extra, interpreter=with_interpreter))
    assert exc.value.code == 2
    run.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        ["--candidate-sha", "HEAD"],
        ["--candidate-sha", SHA.upper()],
        ["--candidate-sha", SHA[:12]],
        ["--candidate-sha", SHA + "\n"],
        ["--candidate-sha", SHA, "--candidate-python", "3"],
        ["--candidate-sha", SHA, "--candidate-python", "/usr/bin/python3"],
    ],
)
def test_main_rejects_malformed_candidate_values(tmp_path: Path, extra: list[str]) -> None:
    with mock.patch.object(rm, "run_candidate") as run, pytest.raises(SystemExit):
        rm.main(_argv(tmp_path, "--refs-dir", _refs(tmp_path), *extra))
    run.assert_not_called()


def test_main_candidate_needs_an_extracted_builds_dir(tmp_path: Path) -> None:
    argv = ["--out", str(tmp_path / "out"), "--builds-dir", str(tmp_path / "missing"),
            "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
            "--candidate-interpreter", str(_base_interpreter(tmp_path))]
    with mock.patch.object(rm, "run_candidate") as run:
        assert rm.main(argv) == 2
    run.assert_not_called()


def test_main_candidate_refuses_scratch_dirs_in_the_real_home(
    tmp_path: Path, account_home: Path
) -> None:
    (account_home / "builds").mkdir()
    argv = ["--out", str(tmp_path / "out"), "--builds-dir", str(account_home / "builds"),
            "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
            "--candidate-interpreter", str(_base_interpreter(tmp_path))]
    with (
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        rm.main(argv)
    run.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_main_candidate_real_home_checks_ignore_the_home_variable(
    tmp_path: Path, account_home: Path
) -> None:
    # HOME points at a scratch dir (as in every candidate subprocess); the account home is
    # elsewhere. Placing --out in the account home is refused whatever HOME says.
    (tmp_path / "builds").mkdir()
    argv = ["--out", str(account_home / "out"), "--builds-dir", str(tmp_path / "builds"),
            "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
            "--candidate-interpreter", str(_base_interpreter(tmp_path))]
    with (
        mock.patch.dict(os.environ, {"HOME": str(tmp_path / "builds")}),
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit, match="inside the real user home"),
    ):
        rm.main(argv)
    run.assert_not_called()


def test_main_candidate_refuses_the_live_hermes_home_as_refs_dir(
    tmp_path: Path, account_home: Path
) -> None:
    live = account_home / ".hermes"
    live.mkdir()
    with (
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit, match="live Hermes home"),
    ):
        rm.main(_argv(tmp_path, "--refs-dir", str(live), "--candidate-sha", SHA))
    run.assert_not_called()


def test_main_candidate_refuses_a_symlinked_out_dir(tmp_path: Path) -> None:
    real = tmp_path / "real_out"
    real.mkdir()
    (tmp_path / "out").symlink_to(real)
    with (
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit, match="symlink"),
    ):
        rm.main(_argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA))
    run.assert_not_called()


@pytest.mark.parametrize(
    ("where", "message"),
    [
        ("elsewhere/report.json", "inside the private scratch"),  # outside --out
        ("out", "inside the private scratch"),  # --out itself
        ("out/linked.json", "symlink"),  # a symlink at the report path
        ("out/linkdir/report.json", "symlink"),  # a symlinked directory in front of it
        ("out/adir", "not a regular file"),
    ],
)
def test_main_candidate_json_out_must_be_a_private_regular_file_in_scratch(
    tmp_path: Path, where: str, message: str
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "linked.json").symlink_to(elsewhere / "victim.json")
    (out / "linkdir").symlink_to(elsewhere)
    (out / "adir").mkdir()
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--json-out", str(tmp_path / where))
    with (
        mock.patch.object(rm, "run_candidate") as run,
        pytest.raises(SystemExit, match=message),
    ):
        rm.main(argv)
    run.assert_not_called()  # nothing ran: refused before the first stage
    assert not (elsewhere / "victim.json").exists()


def test_main_candidate_json_out_never_writes_through_a_symlink_or_over_a_hardlink(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "victim.json"
    victim.write_text("keep")
    out = tmp_path / "out"
    out.mkdir()
    os.link(victim, out / "report.json")  # a hard link to a file outside scratch
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--json-out", str(out / "report.json"))
    with (
        mock.patch.object(rm, "run_candidate", return_value=_passing_report()),
        pytest.raises(SystemExit, match="cannot write --json-out"),
    ):
        rm.main(argv)
    assert victim.read_text() == "keep"


def test_main_candidate_json_out_replaces_our_own_previous_report(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.json").write_text("old")
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--json-out", str(out / "report.json"))
    with mock.patch.object(rm, "run_candidate", return_value=_passing_report()):
        assert rm.main(argv) == 0
    assert json.loads((out / "report.json").read_text()) == _passing_report()
    assert stat.S_IMODE((out / "report.json").stat().st_mode) == 0o600


def test_listed_build_mode_is_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = rm.BuildSpec("stock-base", "hermes-agent", "04fa849e70", False)
    qualified = {"label": "stock-base", "qualified": True, "fingerprint": "f", "git_sha": None,
                 "source_sha": "s"}
    sc007 = {"ok": True, "status": "unsupported"}
    with (
        mock.patch.object(rm, "load_build_specs", return_value=[spec]),
        mock.patch.object(rm, "process_build", return_value=qualified) as process,
        mock.patch.object(rm, "unsupported_path_check", return_value=sc007) as check,
        mock.patch.object(rm, "run_candidate") as run,
    ):
        code = rm.main(_argv(tmp_path, "--builds", "stock-base"))
    assert code == 0
    run.assert_not_called()
    process.assert_called_once()
    assert check.call_args.args[1] == "stock-base"
    matrix = json.loads(capsys.readouterr().out)
    assert set(matrix) == {
        "format", "results", "candidate_entries", "sc007_unsupported_path_check"
    }
    assert matrix["candidate_entries"] == [
        {"label": "stock-base", "fingerprint": "f", "git_sha": None, "source_sha": "s"}
    ]


def test_builds_yaml_cannot_claim_the_reserved_candidate_label(tmp_path: Path) -> None:
    manifest = tmp_path / "builds.yaml"
    manifest.write_text(
        "format: 1\nbuilds:\n  - label: candidate\n    clone: c\n    ref: HEAD\n", encoding="utf-8"
    )
    with (
        mock.patch.object(rm, "BUILDS_YAML", manifest),
        pytest.raises(SystemExit, match="reserved label"),
    ):
        rm.load_build_specs()
    assert "candidate" not in {s.label for s in rm.load_build_specs()}


# ---- M1: the tracked tree, fingerprint and lockfile are proven again after SC-007 ---------------


def _recheck(world: World, expected: str | None = None, sha: str | None = None, **kwargs) -> bool:
    return rm.recheck_source(
        world.builds, world.refs, sha or world.sha, expected or world.fingerprint(), **kwargs
    )


def test_recheck_accepts_an_unchanged_extraction_and_runs_no_interpreter(world: World) -> None:
    with mock.patch.object(rm.extract_mod, "interpreter_info") as probe:
        assert _recheck(world) is True
    probe.assert_not_called()  # a pure read of the tree, the clone and the metadata


@pytest.mark.parametrize("tamper", _TREE_TAMPERINGS, ids=lambda f: f.__name__)
def test_recheck_catches_every_drift_the_first_verification_would(world: World, tamper) -> None:
    tamper(world)
    problems: list[str] = []
    assert _recheck(world, problems=problems) is False
    assert problems


def test_recheck_catches_a_changed_fingerprint_lockfile_metadata_or_clone(world: World) -> None:
    problems: list[str] = []
    assert _recheck(world, expected="cd" * 32, problems=problems) is False  # not the verified one
    assert any("differs" in p for p in problems)
    assert _recheck(world, sha=OTHER_SHA) is False  # the clone does not have that commit
    world.write_metadata(uv_lock_sha256="0" * 64)  # the lock the extraction recorded is not it
    assert _recheck(world) is False
    world.write_metadata(commit=OTHER_SHA)
    assert _recheck(world) is False
    (world.build_dir / "build-metadata.json").unlink()
    assert _recheck(world) is False


def test_recheck_treats_symlinked_metadata_as_changed(world: World) -> None:
    path = world.build_dir / "build-metadata.json"
    real = world.tmp / "elsewhere.json"
    real.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(real)
    assert _recheck(world) is False


def test_recheck_refuses_a_group_writable_build_directory(world: World) -> None:
    os.chmod(world.build_dir, 0o775)  # noqa: S103 - intentional unsafe-mode fixture
    assert _recheck(world) is False
    os.chmod(world.build_dir, 0o700)
    assert _recheck(world) is True


def test_run_candidate_reverifies_after_sc007_and_binds_the_recheck_to_the_verified_tree(
    tmp_path: Path,
) -> None:
    with Stages() as st:
        report = _run(tmp_path)
    assert report["checks"]["source_unchanged_after_run"] is True
    assert report["candidate_passed"] is True and report["failed_stage"] is None
    st.recheck.assert_called_once()
    assert st.recheck.call_args.args == (tmp_path / "builds", tmp_path / "refs", SHA, FINGERPRINT)
    assert (tmp_path / "out" / "candidate" / "post-run-verification.log").is_file()
    # ... and it runs last: after SC-007, which ran after the self-check and the read suite
    order = [st.selfcheck, st.suite, st.sc007, st.recheck]
    assert all(m.call_count == 1 for m in order)


def test_a_failed_recheck_fails_the_run_even_though_every_earlier_stage_passed(
    tmp_path: Path,
) -> None:
    with Stages(recheck=mock.Mock(return_value=False)):
        report = _run(tmp_path)
    assert report["failed_stage"] == "post_run_verification"
    assert report["checks"]["source_unchanged_after_run"] is False
    assert report["checks"]["sc007_passed"] is True and report["checks"]["selfcheck_passed"]
    assert report["candidate_passed"] is False


def test_the_recheck_is_not_reached_when_an_earlier_stage_failed(tmp_path: Path) -> None:
    with Stages(sc007=mock.Mock(return_value={**_SC007_RESULT, "ok": False})) as st:
        report = _run(tmp_path)
    assert report["failed_stage"] == "sc007"
    st.recheck.assert_not_called()
    assert report["checks"]["source_unchanged_after_run"] is False


def _world_stages(world: World, tmp_path: Path, **over: object) -> Stages:
    """Stages for `world`, with the REAL recheck (the other stages are fakes)."""
    return Stages(
        verify=mock.Mock(return_value=(dict(_VERIFIED), world.fingerprint())),
        recheck=rm.recheck_source,
        **over,
    )


def test_drift_written_into_the_tree_by_a_stage_is_caught_by_the_real_recheck(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)

    def selfcheck(*_a, **_kw):
        (world.src / "stray.pth").write_text("import os\n")  # a stage wrote into the tree
        return True, _SELFCHECK_OK

    with _world_stages(world, tmp_path, selfcheck=selfcheck):
        report = rm.run_candidate(
            world.sha, "3.14", world.refs, world.builds, tmp_path / "out", now=GENERATED
        )
    assert report["failed_stage"] == "post_run_verification" and not report["candidate_passed"]
    problems = (tmp_path / "out" / "candidate" / "post-run-verification.log").read_text()
    assert "stray.pth" in problems


def test_an_untouched_tree_passes_the_real_recheck(tmp_path: Path) -> None:
    world = World(tmp_path)
    with _world_stages(world, tmp_path):
        report = rm.run_candidate(
            world.sha, "3.14", world.refs, world.builds, tmp_path / "out", now=GENERATED
        )
    assert report["failed_stage"] is None and report["candidate_passed"] is True
    assert report["checks"]["source_unchanged_after_run"] is True


def test_the_verdict_line_and_report_say_a_pass_is_only_non_adversarial_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA)
    with mock.patch.object(rm, "run_candidate", return_value=_passing_report()):
        assert rm.main(argv) == 0
    err = capsys.readouterr().err
    assert "PASSED (non-adversarial compatibility evidence only" in err
    assert "not an attestation" in err and "not a sandbox" in err
    assert "protects the host, not this harness" in err


# ---- M2: the venv's base interpreter must be outside the real home ------------------------------


def test_verify_rejects_a_venv_whose_base_interpreter_is_in_the_real_home(
    world: World, account_home: Path
) -> None:
    problems: list[str] = []
    in_home = str(account_home / ".pyenv" / "3.14")
    checks, fingerprint = world.verify(base=in_home, problems=problems)
    assert checks["interpreter_matches"] is False and fingerprint is None
    assert any("interpreter" in p and "real user home" in p for p in problems)
    checks, fingerprint = world.verify()  # control: a system base is fine
    assert checks["interpreter_matches"] is True and fingerprint is not None


# ---- M3: every matrix run starts from a fresh scratch environment -------------------------------


def test_run_candidate_starts_every_run_from_a_fresh_scratch_environment(tmp_path: Path) -> None:
    scratch = tmp_path / "out" / "candidate"
    env_root = scratch / "env"
    stale = [
        env_root / "pycache" / "agent.cpython-314.pyc",
        env_root / "cache" / "uv" / "wheels" / "old.whl",
        env_root / "home" / ".netrc",
        env_root / "tmp" / "leftover",
        env_root / "config" / "c",
        env_root / "data" / "d",
        env_root / "state" / "s",
        env_root / "runtime" / "r",
        env_root / "hermes_home" / "state.db",
    ]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale")
    (scratch / "operator-note.txt").write_text("keep")
    seen: list[list[bool]] = []

    def verify(*_a, **_kw):  # the first stage that would run candidate code
        seen.append([path.exists() for path in stale])
        return dict(_VERIFIED), FINGERPRINT

    with Stages(verify=mock.Mock(side_effect=verify)):
        _run(tmp_path)
    assert seen == [[False] * len(stale)]
    assert (scratch / "operator-note.txt").read_text() == "keep"


def test_run_candidate_refuses_a_symlinked_scratch_dir_before_running_any_stage(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("precious")
    env_root = tmp_path / "out" / "candidate" / "env"
    env_root.mkdir(parents=True)
    (env_root / "tmp").symlink_to(victim)
    with Stages() as st, pytest.raises(SystemExit, match="symlink"):
        _run(tmp_path)
    st.verify.assert_not_called()
    assert (victim / "keep").read_text() == "precious"


def test_run_candidate_never_deletes_source_refs_builds_or_the_repository(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    (tmp_path / "out" / "candidate" / "env" / "home").mkdir(parents=True)
    with _world_stages(world, tmp_path):
        rm.run_candidate(
            world.sha, "3.14", world.refs, world.builds, tmp_path / "out", now=GENERATED
        )
    assert (world.src / "uv.lock").is_file() and (world.clone / ".git").is_dir()
    assert (world.build_dir / "build-metadata.json").is_file()
    assert (rm.REPO_ROOT / ".git").exists() and rm.SERVER_DIR.is_dir()


# ---- --json-out: validated at the start and again right before the report is written -----------


def test_json_out_is_revalidated_after_the_run_and_a_swapped_in_symlink_is_refused(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target = out / "report.json"

    def run(*_a, **_kw):  # the candidate ran as this user: it swaps a symlink into place
        target.symlink_to(elsewhere / "victim.json")
        return _passing_report()

    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--json-out", str(target))
    with (
        mock.patch.object(rm, "run_candidate", side_effect=run),
        pytest.raises(SystemExit, match="cannot write --json-out"),
    ):
        rm.main(argv)
    assert not (elsewhere / "victim.json").exists()


def test_json_out_directory_swapped_for_a_symlink_during_the_run_is_refused(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    (out / "sub").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    def run(*_a, **_kw):
        (out / "sub").rmdir()
        (out / "sub").symlink_to(elsewhere)
        return _passing_report()

    argv = _argv(tmp_path, "--refs-dir", _refs(tmp_path), "--candidate-sha", SHA,
                 "--json-out", str(out / "sub" / "report.json"))
    with (
        mock.patch.object(rm, "run_candidate", side_effect=run),
        pytest.raises(SystemExit, match=r"cannot write --json-out.*symlink"),
    ):
        rm.main(argv)
    assert not (elsewhere / "report.json").exists()


# ---- runtime dependencies are reported, not assumed to be locked -------------------------------


def _venv_with(src: Path, *dist_infos: str, python: str = "python3.14") -> None:
    site = src / ".venv" / "lib" / python / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    for name in dist_infos:
        (site / name).mkdir()


_NO_DEPS = {"aiohttp": None, "cryptography": None, "qrcode": None}


def test_runtime_dependency_versions_come_from_dist_info_names_and_execute_nothing(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    _venv_with(
        src, "aiohttp-3.9.5.dist-info", "cryptography-42.0.5.dist-info", "qrcode-7.4.2.dist-info",
        "other-1.0.dist-info", "aiohttp_extras-9.dist-info",
    )
    with (
        mock.patch.object(subprocess, "run") as run,
        mock.patch.object(subprocess, "Popen") as popen,
    ):
        assert rm.runtime_dependency_versions(src) == {
            "aiohttp": "3.9.5", "cryptography": "42.0.5", "qrcode": "7.4.2",
        }
    run.assert_not_called()
    popen.assert_not_called()
    assert rm.RUNTIME_DEPENDENCIES == ("aiohttp", "cryptography", "qrcode")


def test_runtime_dependency_versions_are_none_when_absent_ambiguous_or_odd(
    tmp_path: Path,
) -> None:
    assert rm.runtime_dependency_versions(tmp_path / "missing") == _NO_DEPS
    src = tmp_path / "src"
    _venv_with(src, "aiohttp-3.9.5.dist-info", "qrcode-bad version.dist-info")
    _venv_with(src, "aiohttp-3.10.0.dist-info", python="python3.13")  # two versions: ambiguous
    assert rm.runtime_dependency_versions(src) == _NO_DEPS


def test_runtime_dependency_versions_follow_no_symlink(tmp_path: Path) -> None:
    real = tmp_path / "real"
    _venv_with(real, "aiohttp-3.9.5.dist-info")
    linked_venv = tmp_path / "linked_venv"
    linked_venv.mkdir()
    (linked_venv / ".venv").symlink_to(real / ".venv")
    assert rm.runtime_dependency_versions(linked_venv) == _NO_DEPS

    linked_dist = tmp_path / "linked_dist"
    _venv_with(linked_dist)
    (tmp_path / "elsewhere-dist").mkdir()
    site = linked_dist / ".venv" / "lib" / "python3.14" / "site-packages"
    (site / "qrcode-7.4.2.dist-info").symlink_to(tmp_path / "elsewhere-dist")
    assert rm.runtime_dependency_versions(linked_dist) == _NO_DEPS

    linked_site = tmp_path / "linked_site"
    (linked_site / ".venv" / "lib" / "python3.14").mkdir(parents=True)
    (tmp_path / "elsewhere-site").mkdir()
    (tmp_path / "elsewhere-site" / "aiohttp-3.9.5.dist-info").mkdir()
    (linked_site / ".venv" / "lib" / "python3.14" / "site-packages").symlink_to(
        tmp_path / "elsewhere-site"
    )
    assert rm.runtime_dependency_versions(linked_site) == _NO_DEPS


def test_the_report_carries_the_installed_runtime_dependency_versions(tmp_path: Path) -> None:
    _venv_with(
        tmp_path / "builds" / "candidate" / "src", "aiohttp-3.9.5.dist-info",
        "cryptography-42.0.5.dist-info",
    )
    with Stages():
        report = _run(tmp_path)
    assert report["runtime_dependencies"] == {
        "aiohttp": "3.9.5", "cryptography": "42.0.5", "qrcode": None,
    }
    text = json.dumps(report["runtime_dependencies"])
    assert "/" not in text and str(tmp_path) not in text
