"""The fixture tools' isolation for the ad-hoc `candidate` build: real-home checks against the
account home (never `$HOME`), and a scrubbed, private environment for every process the fixture
tools start once the candidate is the build under test -- whoever launched them.

Nothing here starts a process: `subprocess` is mocked wherever a call would be made.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from unittest import mock

import _fixture_common as fc
import pytest
import selfcheck
import yaml

_POISON = {
    "OPENAI_API_KEY": "sk-real", "ANTHROPIC_API_KEY": "sk-ant", "HTTPS_PROXY": "http://u:p@h",
    "GIT_DIR": "/elsewhere/.git", "GIT_SSH_COMMAND": "evil", "PYTHONPATH": "/evil",
    "HERMES_HOME": "/real/.hermes", "XDG_STATE_HOME": "/real/state", "HOME": "/real/home",
    "TMPDIR": "/real/tmp",
}
_OPT_IN = {fc.CANDIDATE_OPT_IN_ENV: "1"}  # what `run_matrix.py --candidate-sha` sets
_ESSENTIALS = {"PATH": "/usr/bin:/bin", "LANG": "C", **_OPT_IN}


@pytest.fixture(autouse=True)
def isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = (tmp_path / "account_home").resolve()
    home.mkdir()
    monkeypatch.setattr(fc.safety, "real_user_home", lambda: home)
    monkeypatch.setattr(fc, "_CANDIDATE_ENV_ROOT", None)  # restored after each test
    monkeypatch.setenv(fc.CANDIDATE_OPT_IN_ENV, "1")  # tests of the gate itself remove it
    previous = os.umask(0o022)
    yield home
    os.umask(previous)


def _build(tmp_path: Path) -> fc.BuildInfo:
    return fc.BuildInfo(
        "candidate", tmp_path / "b" / "candidate" / "src", tmp_path / "venv" / "bin" / "python3"
    )


def test_real_home_checks_use_the_account_home_not_the_home_variable(
    tmp_path: Path, isolation: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "scratch_home"))  # what a candidate process has
    fc.assert_outside_real_home(tmp_path / "scratch_home" / "out", "out")
    with pytest.raises(fc.FixtureSafetyError, match="inside the real user home"):
        fc.assert_outside_real_home(isolation / "Documents" / "out", "out")
    with pytest.raises(fc.FixtureSafetyError, match=r"touches the real ~/\.hermes"):
        fc.assert_never_real_hermes_dir(isolation / ".hermes" / "profiles" / "x", "home")
    with pytest.raises(fc.FixtureSafetyError, match=r"touches the real ~/\.hermes"):
        fc.assert_never_real_hermes_dir(isolation, "home")  # an ancestor of ~/.hermes
    fc.assert_never_real_hermes_dir(tmp_path / "scratch", "home")


def test_listed_builds_keep_their_environment_apart_from_hermes_xdg_and_git_variables() -> None:
    inherited = {**_ESSENTIALS, "OPENAI_API_KEY": "k", "HERMES_X": "1", "XDG_Y": "1",
                 "GIT_DIR": "/x", "HOME": "/h", "PYTHONPATH": "/kept-as-before"}
    with mock.patch.dict(os.environ, inherited, clear=True):
        env = fc.clean_hermes_env(extra={"HERMES_HOME": "/hh"})
    assert env == {**_ESSENTIALS, "OPENAI_API_KEY": "k", "HOME": "/h",
                   "PYTHONPATH": "/kept-as-before", "HERMES_HOME": "/hh"}


def test_candidate_isolation_ignores_the_callers_environment(tmp_path: Path) -> None:
    out = tmp_path / "out"
    with mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True):
        fc.enable_candidate_isolation(out)
        env = fc.clean_hermes_env(extra={
            "HERMES_HOME": str(out / "homes" / "A"), "XDG_STATE_HOME": str(out / "xdg" / "A"),
        })
    joined = " ".join(env.values())
    for needle in ("sk-", "u:p@h", "evil", "/real/", "/elsewhere"):
        assert needle not in joined
    for key in ("OPENAI_API_KEY", "HTTPS_PROXY", "GIT_DIR", "GIT_SSH_COMMAND", "PYTHONPATH"):
        assert key not in env
    scratch = out / "_candidate_env"
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "TMPDIR",
                "UV_CACHE_DIR", "PYTHONPYCACHEPREFIX"):
        assert Path(env[key]).is_relative_to(scratch), key
    assert env["HERMES_HOME"] == str(out / "homes" / "A")  # the per-instance values win
    assert env["XDG_STATE_HOME"] == str(out / "xdg" / "A")
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    assert stat.S_IMODE(Path(env["HOME"]).stat().st_mode) == 0o700
    private = os.umask(0o077)
    os.umask(private)
    assert private == 0o077  # everything the candidate's processes create is private


def test_candidate_isolation_refuses_an_out_dir_in_the_real_home(
    tmp_path: Path, isolation: Path
) -> None:
    with pytest.raises(fc.FixtureSafetyError, match="inside the real user home"):
        fc.enable_candidate_isolation(isolation / "out")
    assert fc._CANDIDATE_ENV_ROOT is None and not (isolation / "out").exists()


def test_candidate_isolation_refuses_a_symlinked_out_dir(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    os.chmod(real, 0o755)  # noqa: S103 - intentional unsafe-mode fixture
    (tmp_path / "out").symlink_to(real)
    with pytest.raises(fc.FixtureSafetyError, match="symlink"):
        fc.enable_candidate_isolation(tmp_path / "out")
    assert fc._CANDIDATE_ENV_ROOT is None
    assert stat.S_IMODE(real.stat().st_mode) == 0o755 and not list(real.iterdir())


def test_uv_pip_install_gets_the_scrubbed_environment(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True):
        fc.enable_candidate_isolation(tmp_path / "out")
        with (
            mock.patch.object(fc.subprocess, "run") as run,
            mock.patch.object(fc.safety, "require_uv", return_value="/opt/uv/bin/uv"),
        ):
            fc.ensure_runtime_deps(_build(tmp_path))
    env = run.call_args.kwargs["env"]
    assert "OPENAI_API_KEY" not in env and "HTTPS_PROXY" not in env and "GIT_DIR" not in env
    assert Path(env["HOME"]).is_relative_to(tmp_path / "out" / "_candidate_env")
    # uv is run by the absolute path found before the PATH scrub, not looked up on the scrubbed one
    assert run.call_args.args[0][:3] == ["/opt/uv/bin/uv", "pip", "install"]


def test_listed_builds_keep_running_a_bare_uv(tmp_path: Path) -> None:
    assert fc.uv_command() == "uv"
    with mock.patch.object(fc.subprocess, "run") as run:
        fc.ensure_runtime_deps(_build(tmp_path))
    assert run.call_args.args[0][:3] == ["uv", "pip", "install"]


def test_candidate_without_a_safe_uv_is_refused_with_a_setup_instruction(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, _ESSENTIALS, clear=True):
        fc.enable_candidate_isolation(tmp_path / "out")
        with (
            mock.patch.object(fc.safety, "find_executable", return_value=None),
            mock.patch.object(fc.subprocess, "run") as run,
            pytest.raises(fc.FixtureSafetyError, match=r"`uv` was not found on PATH.*Install uv"),
        ):
            fc.ensure_runtime_deps(_build(tmp_path))
    run.assert_not_called()


# ---- the fixture tools will not start the candidate without the explicit opt-in --------------


@pytest.mark.parametrize("value", [None, "", "0", "true", "yes", "2", " 1"])
def test_the_fixture_tools_refuse_the_candidate_without_the_explicit_opt_in(
    tmp_path: Path, value: str | None
) -> None:
    environ = {**_ESSENTIALS}
    environ.pop(fc.CANDIDATE_OPT_IN_ENV)
    if value is not None:
        environ[fc.CANDIDATE_OPT_IN_ENV] = value
    with (
        mock.patch.dict(os.environ, environ, clear=True),
        pytest.raises(fc.FixtureSafetyError, match=r"unsafe developer path.*HMP_ENABLE_CANDIDATE"),
    ):
        fc.enable_candidate_isolation(tmp_path / "out")
    assert fc._CANDIDATE_ENV_ROOT is None
    assert not (tmp_path / "out").exists()  # nothing was created, nothing was started


def test_the_gate_message_points_at_the_verifying_tool(tmp_path: Path) -> None:
    with (
        mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=True),
        pytest.raises(fc.FixtureSafetyError) as exc,
    ):
        fc.require_candidate_gate("mutate.py")
    text = str(exc.value)
    assert "run_matrix.py" in text and "--candidate-sha" in text and "isolated VM" in text


def test_selfcheck_refuses_the_candidate_without_the_opt_in_and_starts_nothing(
    tmp_path: Path,
) -> None:
    with (
        mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=True),
        mock.patch.object(selfcheck.subprocess, "Popen") as popen,
        pytest.raises(fc.FixtureSafetyError, match="unsafe developer path"),
    ):
        selfcheck.run_selfcheck("candidate", tmp_path / "out", {"instances": []})
    popen.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_build_fixture_and_mutate_refuse_the_candidate_without_the_opt_in(
    tmp_path: Path,
) -> None:
    import build_fixture
    import mutate

    out = tmp_path / "out"
    out.mkdir()
    (out / "fixture_meta.json").write_text(
        '{"build": {"label": "candidate", "src_dir": "/x/src", "venv_python": "/x/py"}, '
        '"instances": []}',
        encoding="utf-8",
    )
    entries = [
        (build_fixture.main, ["--build", "candidate", "--builds-dir", str(tmp_path / "b"),
                              "--out", str(out)]),
        (mutate.main, ["--out", str(out), "--instance", "A", "--mutation", "append"]),
    ]
    for main, argv in entries:
        with (
            mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=True),
            mock.patch.object(fc, "ensure_runtime_deps") as deps,
            mock.patch.object(fc, "resolve_build") as resolve,
            mock.patch.object(fc.subprocess, "run") as run,
            pytest.raises(fc.FixtureSafetyError, match="unsafe developer path"),
        ):
            main(argv)
        deps.assert_not_called()
        resolve.assert_not_called()
        run.assert_not_called()


def test_the_isolation_of_a_build_starts_from_a_fresh_scratch_environment(tmp_path: Path) -> None:
    out = tmp_path / "out"
    env_root = out / "_candidate_env"
    stale = [
        env_root / "pycache" / "x.pyc", env_root / "cache" / "uv" / "w", env_root / "home" / "h",
        env_root / "tmp" / "t", env_root / "hermes_home" / "s",
    ]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale")
    instance_home = out / "homes" / "A" / "state.db"  # fixture data is not scratch environment
    instance_home.parent.mkdir(parents=True)
    instance_home.write_text("keep")
    with mock.patch.dict(os.environ, _ESSENTIALS, clear=True):
        fc.enable_candidate_isolation(out, fresh=True)
    assert not any(path.exists() for path in stale)
    assert instance_home.read_text() == "keep"
    assert (env_root / "home").is_dir()  # recreated, empty, private


def test_re_entering_a_running_fixture_does_not_wipe_its_environment(tmp_path: Path) -> None:
    out = tmp_path / "out"
    live = out / "_candidate_env" / "tmp" / "gateway.sock"
    live.parent.mkdir(parents=True)
    live.write_text("in use by a running gateway")
    with mock.patch.dict(os.environ, _ESSENTIALS, clear=True):
        fc.enable_candidate_isolation(out)  # what mutate.py does
    assert live.read_text() == "in use by a running gateway"


def test_a_symlinked_scratch_dir_in_the_fixture_environment_is_refused_not_followed(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("precious")
    out = tmp_path / "out"
    (out / "_candidate_env").mkdir(parents=True)
    (out / "_candidate_env" / "cache").symlink_to(victim)
    with mock.patch.dict(os.environ, _ESSENTIALS, clear=True):
        with pytest.raises(fc.FixtureSafetyError, match="symlink"):
            fc.enable_candidate_isolation(out, fresh=True)
        with pytest.raises(fc.FixtureSafetyError, match="symlink"):
            fc.enable_candidate_isolation(out)
    assert (victim / "keep").read_text() == "precious"
    assert fc._CANDIDATE_ENV_ROOT is None


def test_the_fixture_path_drops_a_directory_that_links_into_the_live_hermes_home(
    tmp_path: Path, isolation: Path
) -> None:
    live = isolation / ".hermes" / "bin"
    live.mkdir(parents=True)
    (live / "hermes").write_text("")
    bin_dir = tmp_path / "local-bin"
    bin_dir.mkdir()
    (bin_dir / "hermes").symlink_to(live / "hermes")
    path = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
    with mock.patch.dict(os.environ, {**_ESSENTIALS, "PATH": path}, clear=True):
        fc.enable_candidate_isolation(tmp_path / "out")
        env = fc.clean_hermes_env()
    assert env["PATH"] == "/usr/bin:/bin"


def test_seed_and_pairing_scripts_get_the_scrubbed_environment(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True):
        fc.enable_candidate_isolation(tmp_path / "out")
        with mock.patch.object(fc.subprocess, "run") as run:
            run.return_value.returncode = 0
            fc.run_seed_script(_build(tmp_path), tmp_path / "seed.py", "--x")
    env = run.call_args.kwargs["env"]
    assert env["PYTHONPATH"] == str(fc.SERVER_DIR)  # the caller's PYTHONPATH is gone
    for key in ("OPENAI_API_KEY", "HTTPS_PROXY", "GIT_DIR", "GIT_SSH_COMMAND"):
        assert key not in env
    assert Path(env["HOME"]).is_relative_to(tmp_path / "out" / "_candidate_env")


def test_gateway_env_is_scrubbed_but_carries_the_instance_paths(tmp_path: Path) -> None:
    out = tmp_path / "out"
    paths = fc.instance_paths(out, "A")
    with mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True):
        fc.enable_candidate_isolation(out)
        with mock.patch.object(fc.subprocess, "run") as run:
            run.return_value.returncode = 0
            fc.run_hermes_cli(_build(tmp_path), paths, "profile", "list")
    env = run.call_args.kwargs["env"]
    assert env["HERMES_HOME"] == str(paths.home) and env["XDG_STATE_HOME"] == str(paths.xdg_state)
    assert "OPENAI_API_KEY" not in env and "GIT_DIR" not in env
    assert Path(env["HOME"]).is_relative_to(out / "_candidate_env")


def _base_python(tmp_path: Path) -> Path:
    """A stand-in system interpreter outside the fake home (never executed here)."""
    base = tmp_path / "sys_python" / "python3.14"
    if not base.exists():
        base.parent.mkdir(parents=True)
        base.write_text("#!/bin/sh\nexit 1\n")
        os.chmod(base, 0o755)  # noqa: S103 - a system-like interpreter
        os.chmod(base.parent, 0o755)  # noqa: S103 - a system-like bin directory
    return base


def _tree(builds: Path, label: str = "candidate", target: Path | None = None) -> Path:
    """`<builds>/<label>/src` with a `.venv` shaped like uv's: `bin/python3` linking to a base
    interpreter (default: the stand-in outside the home) and a `pyvenv.cfg` naming its dir."""
    target = target or _base_python(builds.parent)
    venv = builds / label / "src" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python3").symlink_to(target)
    (venv / "pyvenv.cfg").write_text(f"home = {target.parent}\n")
    return builds / label


def test_resolve_build_accepts_a_real_candidate_tree_only_once_isolated(tmp_path: Path) -> None:
    _tree(tmp_path / "builds")
    with pytest.raises(fc.FixtureSafetyError, match="only resolved after"):
        fc.resolve_build(tmp_path / "builds", "candidate")  # never with the caller's env
    fc.enable_candidate_isolation(tmp_path / "out")
    build = fc.resolve_build(tmp_path / "builds", "candidate")
    assert build.label == "candidate" and build.src_dir == (
        tmp_path / "builds" / "candidate" / "src"
    ).resolve()


def test_resolve_build_refuses_the_candidate_without_the_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tree(tmp_path / "builds")
    fc.enable_candidate_isolation(tmp_path / "out")
    monkeypatch.delenv(fc.CANDIDATE_OPT_IN_ENV)
    with pytest.raises(fc.FixtureSafetyError, match="unsafe developer path"):
        fc.resolve_build(tmp_path / "builds", "candidate")


@pytest.mark.parametrize("linked", ["builds", "builds/candidate", "builds/candidate/src"])
def test_resolve_build_refuses_a_symlinked_candidate_build_tree(
    tmp_path: Path, linked: str
) -> None:
    _tree(tmp_path / "real")
    real = tmp_path / "real"
    if linked == "builds":
        (tmp_path / "builds").symlink_to(real)
    elif linked == "builds/candidate":
        (tmp_path / "builds").mkdir()
        (tmp_path / "builds" / "candidate").symlink_to(real / "candidate")
    else:
        (tmp_path / "builds" / "candidate").mkdir(parents=True)
        (tmp_path / "builds" / "candidate" / "src").symlink_to(real / "candidate" / "src")
    fc.enable_candidate_isolation(tmp_path / "out")
    with pytest.raises(fc.FixtureSafetyError, match="symlink"):
        fc.resolve_build(tmp_path / "builds", "candidate")


def test_resolve_build_refuses_a_candidate_venv_that_leads_into_the_home(
    tmp_path: Path, isolation: Path
) -> None:
    home_python = isolation / ".pyenv" / "bin" / "python3.14"
    home_python.parent.mkdir(parents=True)
    home_python.write_text("#!/bin/sh\n")
    os.chmod(home_python, 0o755)  # noqa: S103 - an executable fixture that is never executed
    _tree(tmp_path / "builds", target=home_python)
    fc.enable_candidate_isolation(tmp_path / "out")
    with pytest.raises(fc.FixtureSafetyError, match="real user home"):
        fc.resolve_build(tmp_path / "builds", "candidate")


# ---- F1: the candidate is recognised by identity, never by spelling ----------------------------

_MALFORMED_LABELS = [
    "candidate/", "./candidate", "Candidate", "CANDIDATE", "cAndidate", "../builds/candidate",
    "candidate/src/..", "candidate/.", " candidate", "candidate ", "candidate\n", "", ".", "..",
    "-candidate", "stock-base/../candidate", "a" * 65,
]


@pytest.mark.parametrize("label", _MALFORMED_LABELS)
def test_malformed_labels_are_refused_before_any_path_is_touched(
    tmp_path: Path, label: str
) -> None:
    _tree(tmp_path / "builds")
    fc.enable_candidate_isolation(tmp_path / "out")
    for check in (fc.check_build_label, lambda x: fc.classify_build(tmp_path / "builds", x),
                  lambda x: fc.resolve_build(tmp_path / "builds", x)):
        with pytest.raises(fc.FixtureSafetyError, match="malformed build label"):
            check(label)


def _alias(tmp_path: Path, how: str) -> Path:
    """A `builds` dir holding the candidate and `cand-alias`, which leads to it in some way."""
    builds = tmp_path / "builds"
    cand = _tree(builds)
    alias = builds / "cand-alias"
    if how == "symlink":
        alias.symlink_to(cand)
    elif how == "relative_symlink":
        alias.symlink_to("candidate")
    elif how == "case_symlink":  # the same directory on a case-insensitive filesystem
        alias.symlink_to(builds / "CANDIDATE")
    elif how == "symlinked_src":
        alias.mkdir()
        (alias / "src").symlink_to(cand / "src")
    elif how == "symlinked_venv":
        (alias / "src").mkdir(parents=True)
        (alias / "src" / ".venv").symlink_to(cand / "src" / ".venv")
    elif how == "renamed_copy":
        (cand / "build-metadata.json").write_text(json.dumps({"label": "candidate"}))
        shutil.copytree(cand, alias, symlinks=True)
    elif how == "other_builds_dir":
        alias.symlink_to(_tree(tmp_path / "other_builds"))
    return builds


_ALIASES = ["symlink", "relative_symlink", "case_symlink", "symlinked_src", "symlinked_venv",
            "renamed_copy", "other_builds_dir"]


@pytest.mark.parametrize("how", _ALIASES)
def test_a_listed_label_that_leads_to_the_candidate_tree_is_refused(
    tmp_path: Path, how: str
) -> None:
    builds = _alias(tmp_path, how)
    fc.enable_candidate_isolation(tmp_path / "out")  # even with the gate open and isolated
    assert fc.is_candidate_tree(builds, "cand-alias") is True
    with pytest.raises(fc.FixtureSafetyError, match="leads to the ad-hoc `candidate`"):
        fc.resolve_build(builds, "cand-alias")


@pytest.mark.parametrize("how", _ALIASES)
def test_no_entry_point_runs_the_candidate_under_an_alias(
    tmp_path: Path, how: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import build_fixture
    import mutate

    builds = _alias(tmp_path, how)
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.delenv(fc.CANDIDATE_OPT_IN_ENV)  # the caller has NOT opted in
    with (
        mock.patch.object(fc.subprocess, "run") as run,
        mock.patch.object(selfcheck.subprocess, "Popen") as popen,
        mock.patch.object(fc, "ensure_runtime_deps") as deps,
        mock.patch.object(fc, "enable_candidate_isolation") as isolate,
    ):
        with pytest.raises(fc.FixtureSafetyError, match="leads to the ad-hoc"):
            build_fixture.main(["--build", "cand-alias", "--builds-dir", str(builds),
                                "--out", str(out)])
        with pytest.raises(fc.FixtureSafetyError, match="leads to the ad-hoc"):
            selfcheck.run_selfcheck("cand-alias", out, {"instances": []}, builds_dir=builds)
        with (
            mock.patch.dict(os.environ, {"HMP_HERMES_BUILDS_DIR": str(builds)}),
            pytest.raises(fc.FixtureSafetyError, match="leads to the ad-hoc"),
        ):
            selfcheck.run_selfcheck("cand-alias", out, {"instances": []})
        src = builds / "cand-alias" / "src"
        (out / "fixture_meta.json").write_text(json.dumps({
            "build": {"label": "cand-alias", "src_dir": str(src),
                      "venv_python": str(src / ".venv" / "bin" / "python3")},
            "instances": [],
        }))
        with pytest.raises(fc.FixtureSafetyError, match="leads to the ad-hoc"):
            mutate.main(["--out", str(out), "--instance", "A", "--mutation", "append"])
    for spy in (run, popen, deps, isolate):
        spy.assert_not_called()


def test_mutate_refuses_a_record_whose_label_does_not_match_its_tree(tmp_path: Path) -> None:
    import mutate

    builds = tmp_path / "builds"
    src = _tree(builds) / "src"
    out = tmp_path / "out"
    out.mkdir()
    (out / "fixture_meta.json").write_text(json.dumps({  # "stock-base", but the candidate's tree
        "build": {"label": "stock-base", "src_dir": str(src.resolve()),
                  "venv_python": str(src.resolve() / ".venv" / "bin" / "python3")},
        "instances": [],
    }))
    with (
        mock.patch.object(fc, "ensure_runtime_deps") as deps,
        mock.patch.object(fc.subprocess, "run") as run,
        pytest.raises(fc.FixtureSafetyError, match="build record is not"),
    ):
        mutate.main(["--out", str(out), "--instance", "A", "--mutation", "append"])
    deps.assert_not_called()
    run.assert_not_called()


def test_every_listed_label_is_well_formed_and_resolves_as_before(tmp_path: Path) -> None:
    labels = [b["label"] for b in yaml.safe_load(fc.BUILDS_YAML.read_text())["builds"]]
    assert labels and "candidate" not in labels
    builds = tmp_path / "builds"
    _tree(builds)  # a candidate beside them changes nothing for the listed builds
    for label in labels:
        assert fc.check_build_label(label) == label
        python = builds / label / "src" / ".venv" / "bin" / "python3"
        python.parent.mkdir(parents=True)
        python.write_text("")  # listed builds: no venv inspection, no gate, no isolation
        assert fc.classify_build(builds, label) is False
        build = fc.resolve_build(builds, label)
        assert build.label == label
        assert build.venv_python == (builds / label / "src").resolve() / ".venv" / "bin" / "python3"
    assert fc._CANDIDATE_ENV_ROOT is None


def test_selfcheck_starts_the_candidate_fixture_with_a_scrubbed_private_environment(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    with (
        mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True),
        mock.patch.object(selfcheck.subprocess, "Popen") as popen,
    ):
        failures = selfcheck.run_selfcheck(
            "candidate", out, {"instances": []}, builds_dir=tmp_path / "builds"
        )
    assert failures == []
    env = popen.call_args.kwargs["env"]
    assert "OPENAI_API_KEY" not in env and "GIT_DIR" not in env and "PYTHONPATH" not in env
    assert Path(env["HOME"]).is_relative_to(out.resolve() / "_selfcheck_env")
    assert env[fc.CANDIDATE_OPT_IN_ENV] == "1"  # the builder it starts passes the same gate


def test_selfcheck_starts_the_candidate_from_a_fresh_scratch_environment(tmp_path: Path) -> None:
    out = (tmp_path / "out").resolve()
    stale = out / "_selfcheck_env" / "pycache" / "x.cpython-314.pyc"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale")
    seen: list[bool] = []

    def popen(*_a, **_kw):
        seen.append(stale.exists())  # checked at the moment the candidate's builder is launched
        return mock.MagicMock()

    with (
        mock.patch.dict(os.environ, {**_POISON, **_ESSENTIALS}, clear=True),
        mock.patch.object(selfcheck.subprocess, "Popen", side_effect=popen),
    ):
        selfcheck.run_selfcheck("candidate", out, {"instances": []}, builds_dir=tmp_path / "b")
    assert seen == [False]


def test_selfcheck_leaves_listed_builds_on_the_callers_environment(tmp_path: Path) -> None:
    with mock.patch.object(selfcheck.subprocess, "Popen") as popen:
        selfcheck.run_selfcheck("stock-base", tmp_path / "out", {"instances": []})
    assert popen.call_args.kwargs["env"] is None
