"""Tests for tools/hermes_builds/candidate_safety.py: the isolation and verification boundary of
the ad-hoc exact `candidate` build.

Everything runs against throwaway synthetic git repositories and directories in `tmp_path`, with
the account home replaced by a fake directory; a real Hermes, the real `_refs` clones and the
live `~/.hermes` are never involved and no candidate code is ever executed.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

_TOOL_DIR = Path(__file__).resolve().parents[1]
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

import candidate_safety as safety  # noqa: E402 -- after the sys.path bootstrap above

_REAL_USER_HOME = safety.real_user_home  # the unpatched function, for the tests of that function
_IDENT = ("-c", "user.email=t@example.invalid", "-c", "user.name=t", "-c", "commit.gpgsign=false")


@pytest.fixture(autouse=True)
def account_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake account home, so no test depends on where the real one (or pytest's tmp) is."""
    home = (tmp_path / "account_home").resolve()
    home.mkdir()
    monkeypatch.setattr(safety, "real_user_home", lambda: home)
    return home


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *_IDENT, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def make_repo(
    root: Path,
    files: dict[str, bytes],
    *,
    executable: tuple[str, ...] = (),
    symlinks: dict[str, str] | None = None,
) -> tuple[Path, str]:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for rel in executable:
        os.chmod(root / rel, 0o755)  # noqa: S103 - executable git fixture
    for rel, target in (symlinks or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, root / rel)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "c")
    return root, git(root, "rev-parse", "HEAD")


# ---- the real account home ---------------------------------------------------------------------


def test_real_user_home_is_the_account_database_home_not_the_home_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pwd = pytest.importorskip("pwd")
    monkeypatch.setenv("HOME", str(tmp_path / "candidate_home"))
    expected = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    assert _REAL_USER_HOME() == expected
    assert _REAL_USER_HOME() != (tmp_path / "candidate_home").resolve()


def test_real_user_home_fails_closed_without_an_account_entry() -> None:
    pytest.importorskip("pwd")
    with (
        mock.patch("pwd.getpwuid", side_effect=KeyError("no such uid")),
        pytest.raises(safety.SafetyError, match="cannot determine the real account home"),
    ):
        _REAL_USER_HOME()


def test_windows_uses_the_known_folder_api_not_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "spoofed"))
    monkeypatch.setattr(safety, "_windows_profile_dir", lambda: str(tmp_path / "profile"))
    assert _REAL_USER_HOME() == (tmp_path / "profile").resolve()


def test_home_checks_ignore_the_home_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, account_home: Path
) -> None:
    # A candidate process has HOME=<scratch>. A check against that would call the real home safe
    # and the scratch dir unsafe; the real checks compare against the account home.
    monkeypatch.setenv("HOME", str(tmp_path / "scratch_home"))
    safety.assert_outside_real_home(tmp_path / "scratch_home" / "out", "out")
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.assert_outside_real_home(account_home / "Documents" / "out", "out")
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.assert_outside_real_home(account_home, "out")
    with pytest.raises(safety.SafetyError, match="contains the real user home"):
        safety.assert_outside_real_home(account_home.parent, "out")


def test_live_hermes_home_is_refused_inside_and_optionally_around(account_home: Path) -> None:
    live = account_home / ".hermes"
    with pytest.raises(safety.SafetyError, match="inside the live Hermes home"):
        safety.assert_not_live_hermes(live / "hermes-agent", "refs", contains_ok=True)
    with pytest.raises(safety.SafetyError, match="contains the live Hermes home"):
        safety.assert_not_live_hermes(account_home, "scratch")
    safety.assert_not_live_hermes(account_home, "refs", contains_ok=True)  # an ancestor is fine


def test_is_within_follows_symlinks(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "sub").mkdir(parents=True)
    (tmp_path / "alias").symlink_to(real)
    assert safety.is_within(tmp_path / "alias" / "sub", real)
    assert safety.is_within(real, real)
    assert not safety.is_within(tmp_path / "other", real)
    assert safety.overlaps(real, real / "sub") and not safety.overlaps(real, tmp_path / "other")


# ---- private directories and files -------------------------------------------------------------


def test_ensure_private_dir_creates_0700_and_tightens(tmp_path: Path) -> None:
    fresh = safety.ensure_private_dir(tmp_path / "a" / "fresh")
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o700
    loose = tmp_path / "loose"
    loose.mkdir()
    os.chmod(loose, 0o755)  # noqa: S103 - intentional unsafe-mode fixture
    safety.ensure_private_dir(loose)
    assert stat.S_IMODE(loose.stat().st_mode) == 0o700


def test_ensure_private_dir_refuses_symlinks_and_files(tmp_path: Path) -> None:
    victim = tmp_path / "victim"
    victim.mkdir()
    os.chmod(victim, 0o755)  # noqa: S103 - intentional unsafe-mode fixture
    (tmp_path / "link").symlink_to(victim)
    with pytest.raises(safety.SafetyError, match="symlink"):
        safety.ensure_private_dir(tmp_path / "link")
    assert stat.S_IMODE(victim.stat().st_mode) == 0o755  # never chmod-ed through the link
    (tmp_path / "file").write_text("x")
    with pytest.raises(safety.SafetyError, match="not a directory"):
        safety.ensure_private_dir(tmp_path / "file")


def test_write_private_file_is_0600_and_replaces_only_our_regular_files(tmp_path: Path) -> None:
    target = safety.write_private_file(tmp_path / "f.json", "one")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600 and target.read_text() == "one"
    safety.write_private_file(target, b"two")
    assert target.read_text() == "two" and stat.S_IMODE(target.stat().st_mode) == 0o600


def test_write_private_file_refuses_symlink_directory_and_hardlink(tmp_path: Path) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    (tmp_path / "link").symlink_to(victim)
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.write_private_file(tmp_path / "link", "overwritten")
    assert victim.read_text() == "keep"
    (tmp_path / "dir").mkdir()
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.write_private_file(tmp_path / "dir", "x")
    os.link(victim, tmp_path / "hard")
    with pytest.raises(safety.SafetyError, match="single-link"):
        safety.write_private_file(tmp_path / "hard", "overwritten")
    assert victim.read_text() == "keep"


def test_remove_private_tree_only_removes_real_directories_strictly_inside(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    (scratch / "work" / "deep").mkdir(parents=True)
    safety.remove_private_tree(scratch / "work", scratch)
    assert not (scratch / "work").exists()
    safety.remove_private_tree(scratch / "missing", scratch)  # nothing to do
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep").write_text("x")
    (scratch / "link").symlink_to(victim)
    with pytest.raises(safety.SafetyError, match="symlink"):
        safety.remove_private_tree(scratch / "link", scratch)
    with pytest.raises(safety.SafetyError, match="not strictly inside"):
        safety.remove_private_tree(scratch, scratch)
    with pytest.raises(safety.SafetyError, match="not strictly inside"):
        safety.remove_private_tree(victim, scratch)
    assert (victim / "keep").exists()


# ---- scrubbed environments ---------------------------------------------------------------------

_INHERITED = {
    "OPENAI_API_KEY": "sk-openai", "ANTHROPIC_API_KEY": "sk-ant", "GITHUB_TOKEN": "ghp_x",
    "HTTPS_PROXY": "http://user:pw@proxy", "HERMES_HOME": "/somewhere/.hermes",
    "XDG_CONFIG_HOME": "/somewhere/config", "GIT_DIR": "/elsewhere/.git",
    "GIT_SSH_COMMAND": "evil-ssh", "PYTHONPATH": "/evil", "PYTHONSTARTUP": "/evil/startup.py",
    "PIP_INDEX_URL": "https://private", "UV_INDEX_URL": "https://private", "NETRC": "/x/.netrc",
    "HOME": "/real/home", "TMPDIR": "/real/tmp", "PYTEST_ADDOPTS": "--evil",
}
_EXPECTED_ENV_KEYS = {
    "PATH", "LANG", "HOME", "HERMES_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
    "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP", "UV_CACHE_DIR",
    "UV_PYTHON_DOWNLOADS", "PYTHONPYCACHEPREFIX", "PYTHONNOUSERSITE", "GIT_CONFIG_NOSYSTEM",
    "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT",
}
_PRIVATE_DIR_KEYS = (
    "HOME", "HERMES_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
    "XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP", "PYTHONPYCACHEPREFIX",
)


def test_scrubbed_env_is_a_fixed_allowlist_with_everything_private(tmp_path: Path) -> None:
    root = tmp_path / "scratch_env"
    inherited = {**_INHERITED, "PATH": "/usr/bin:/bin", "LANG": "C"}
    with mock.patch.dict(os.environ, inherited, clear=True):
        env = safety.scrubbed_env(root)
    assert set(env) == _EXPECTED_ENV_KEYS
    joined = " ".join(env.values())
    for needle in ("sk-", "ghp_", "user:pw", "evil", "/real/", "/somewhere/", "https://private"):
        assert needle not in joined
    for key in (*_PRIVATE_DIR_KEYS, "UV_CACHE_DIR"):
        assert Path(env[key]).is_relative_to(root), key
    for key in _PRIVATE_DIR_KEYS:
        assert stat.S_IMODE(Path(env[key]).stat().st_mode) == 0o700, key
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull and env["GIT_CONFIG_NOSYSTEM"] == "1"


def test_scrubbed_env_passes_only_the_allowlisted_essentials(tmp_path: Path) -> None:
    essentials = {
        "PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8", "LANGUAGE": "en", "TERM": "xterm",
        "SSL_CERT_FILE": "/etc/ca.pem", "SSL_CERT_DIR": "/etc/certs",
    }
    with mock.patch.dict(os.environ, {**_INHERITED, **essentials}, clear=True):
        env = safety.scrubbed_env(tmp_path / "scratch_env")
    assert {k: env[k] for k in essentials} == essentials
    assert set(env) == _EXPECTED_ENV_KEYS | (set(essentials) - {"PATH", "LANG"})


def test_scrubbed_env_path_drops_relative_entries_and_the_installed_hermes(
    tmp_path: Path, account_home: Path
) -> None:
    installed = account_home / ".hermes" / "hermes-agent" / "venv" / "bin"
    hostile = os.pathsep.join(["/usr/bin", "relative/bin", "", ".", str(installed), "/bin"])
    with mock.patch.dict(os.environ, {"PATH": hostile}, clear=True):
        assert safety.scrubbed_env(tmp_path / "scratch_env")["PATH"] == "/usr/bin:/bin"
    with mock.patch.dict(os.environ, {}, clear=True):
        assert safety.scrubbed_env(tmp_path / "scratch_env2")["PATH"] == "/usr/bin:/bin"


def test_scrubbed_env_refuses_the_real_home_and_creates_nothing(
    tmp_path: Path, account_home: Path
) -> None:
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.scrubbed_env(account_home / "scratch")
    assert not (account_home / "scratch").exists()
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.scrubbed_env(tmp_path / "scratch_env", hermes_home=account_home / ".hermes")
    assert not (tmp_path / "scratch_env").exists()
    assert not (account_home / ".hermes").exists()


def test_scrubbed_env_does_not_follow_a_symlinked_scratch_dir(tmp_path: Path) -> None:
    root = tmp_path / "scratch_env"
    root.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    os.chmod(victim, 0o755)  # noqa: S103 - intentional unsafe-mode fixture
    (root / "home").symlink_to(victim)
    with pytest.raises(safety.SafetyError, match="symlink"):
        safety.scrubbed_env(root)
    assert stat.S_IMODE(victim.stat().st_mode) == 0o755


# ---- hardened git ------------------------------------------------------------------------------


def test_git_env_inherits_no_git_variable_and_no_home() -> None:
    poison = {
        "GIT_DIR": "/x", "GIT_WORK_TREE": "/x", "GIT_INDEX_FILE": "/x",
        "GIT_OBJECT_DIRECTORY": "/x", "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor", "GIT_CONFIG_VALUE_0": "/x",
        "GIT_EXEC_PATH": "/x", "GIT_SSH_COMMAND": "evil", "GIT_REPLACE_REF_BASE": "refs/x/",
        "HOME": "/real/home", "PATH": "/usr/bin:/bin", "OPENAI_API_KEY": "sk-1",
    }
    with mock.patch.dict(os.environ, poison, clear=True):
        env = safety.git_env()
    assert {k for k in env if k.startswith("GIT_")} == {
        "GIT_NO_REPLACE_OBJECTS", "GIT_OPTIONAL_LOCKS", "GIT_ATTR_NOSYSTEM", "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT", "GIT_NO_LAZY_FETCH", "GIT_ALLOW_PROTOCOL",
    }
    assert env["GIT_NO_REPLACE_OBJECTS"] == "1" and env["GIT_OPTIONAL_LOCKS"] == "0"
    assert env["GIT_NO_LAZY_FETCH"] == "1"
    assert env["GIT_ALLOW_PROTOCOL"] == "hmp-no-such-protocol"
    assert "HOME" not in env and "OPENAI_API_KEY" not in env
    assert "evil" not in " ".join(env.values())


def test_git_argv_disables_replace_refs_optional_locks_fsmonitor_hooks_and_transports() -> None:
    argv = safety.git_argv("/clone", "status")
    assert argv[0] == "git" and argv[-3:] == ["-C", "/clone", "status"]
    assert "--no-replace-objects" in argv and "--no-optional-locks" in argv
    assert "core.fsmonitor=" in argv
    assert f"core.hooksPath={os.devnull}" in argv
    assert argv[argv.index("protocol.allow=never") - 1] == "-c"
    assert argv[argv.index("log.showSignature=false") - 1] == "-c"


def _commit_with_fake_signature(repo: Path) -> None:
    """Move HEAD (with a reflog entry) to a commit that carries a `gpgsig` header."""
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"], input="", check=True, capture_output=True, text=True
    ).stdout.strip()
    body = (
        f"tree {tree}\nauthor t <t@example.invalid> 0 +0000\n"
        "committer t <t@example.invalid> 0 +0000\n"
        "gpgsig -----BEGIN PGP SIGNATURE-----\n \n ZmFrZQ==\n"
        " -----END PGP SIGNATURE-----\n\nsigned\n"
    )
    oid = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=body, check=True, capture_output=True, text=True,
    ).stdout.strip()
    git(repo, "update-ref", "-m", "signed", "HEAD", oid)


def test_reflog_show_never_runs_the_clones_gpg_program(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "r", {"a.txt": b"1\n"})
    marker = tmp_path / "gpg-marker"
    gpg = tmp_path / "gpg.sh"
    gpg.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
    os.chmod(gpg, 0o755)  # noqa: S103 - executable gpg stand-in fixture
    _commit_with_fake_signature(repo)
    git(repo, "config", "gpg.program", str(gpg))
    git(repo, "config", "log.showSignature", "true")
    subprocess.run(["git", "-C", str(repo), "reflog", "show", "HEAD"], capture_output=True)
    if not marker.exists():
        pytest.skip("this git does not verify signatures in `reflog show`")
    marker.unlink()
    assert safety.run_git(repo, "reflog", "show", "HEAD").returncode == 0
    assert not marker.exists()


def test_run_git_ignores_a_poisoned_git_dir_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_a, sha_a = make_repo(tmp_path / "a", {"f": b"a\n"})
    repo_b, sha_b = make_repo(tmp_path / "b", {"f": b"b\n"})
    assert sha_a != sha_b
    monkeypatch.setenv("GIT_DIR", str(repo_b / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(repo_b))
    monkeypatch.setenv("GIT_INDEX_FILE", str(repo_b / ".git" / "index"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(repo_b / ".git" / "objects"))
    control = subprocess.run(
        ["git", "-C", str(repo_a), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    assert control == sha_b  # the poison works on a plain git call ...
    assert safety.run_git(repo_a, "rev-parse", "HEAD").stdout.strip() == sha_a  # ... and not here


def test_run_git_ignores_replace_refs(tmp_path: Path) -> None:
    repo, first = make_repo(tmp_path / "r", {"a.txt": b"one\n"})
    (repo / "a.txt").write_bytes(b"two\n")
    git(repo, "commit", "-qam", "two")
    second = git(repo, "rev-parse", "HEAD")
    git(repo, "replace", first, second)
    plain = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-p", f"{first}:a.txt"], capture_output=True, text=True
    ).stdout
    assert plain == "two\n"  # control: git honors replace refs by default
    (entry,) = safety.list_commit_tree(repo, first)
    assert entry.oid == safety.git_blob_id(b"one\n")
    with safety.BlobReader(repo) as reader:
        assert reader.read(entry.oid) == b"one\n"


def test_fsmonitor_hook_in_the_clones_config_is_never_run(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "r", {"a.txt": b"1\n"})
    marker = tmp_path / "marker"
    hook = tmp_path / "hook.sh"
    hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nprintf '\\0'\n")
    os.chmod(hook, 0o755)  # noqa: S103 - executable hook fixture
    git(repo, "config", "core.fsmonitor", str(hook))
    subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True)
    if not marker.exists():
        pytest.skip("this git does not run core.fsmonitor hooks on `status`")
    marker.unlink()
    assert safety.run_git(repo, "status", "--porcelain").returncode == 0
    assert not marker.exists()


# ---- the clone's git dirs must not lead into the live ~/.hermes --------------------------------


def test_clone_git_dirs_resolve_for_a_normal_clone(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    git_dir, common = safety.resolve_clone_git_dirs(repo)
    assert git_dir == common == (repo / ".git").resolve()


def test_a_clone_symlinked_into_the_live_hermes_home_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    live_clone, _ = make_repo(account_home / ".hermes" / "hermes-agent", {"a": b"1\n"})
    link = tmp_path / "refs" / "hermes-agent"
    link.parent.mkdir()
    link.symlink_to(live_clone)
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(link)


def test_a_git_file_pointing_into_the_live_hermes_home_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    live_clone, _ = make_repo(account_home / ".hermes" / "hermes-agent", {"a": b"1\n"})
    clone = tmp_path / "refs" / "hermes-agent"
    clone.mkdir(parents=True)
    (clone / ".git").write_text(f"gitdir: {live_clone / '.git'}\n")
    with pytest.raises(safety.SafetyError):
        safety.resolve_clone_git_dirs(clone)


def test_alternates_pointing_into_the_live_hermes_home_are_refused(
    tmp_path: Path, account_home: Path
) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    objects = account_home / ".hermes" / "hermes-agent" / ".git" / "objects"
    objects.mkdir(parents=True)
    info = repo / ".git" / "objects" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "alternates").write_text(f"{objects}\n")
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(repo)


def test_core_worktree_pointing_into_the_live_hermes_home_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    worktree = account_home / ".hermes" / "hermes-agent"
    worktree.mkdir(parents=True)
    git(repo, "config", "core.worktree", str(worktree))
    with pytest.raises(safety.SafetyError):
        safety.resolve_clone_git_dirs(repo)


def test_a_missing_clone_is_refused(tmp_path: Path) -> None:
    (tmp_path / "refs").mkdir()
    with pytest.raises(safety.SafetyError, match="no git clone"):
        safety.resolve_clone_git_dirs(tmp_path / "refs" / "hermes-agent")


# ---- partial clones: a missing object is never fetched ----------------------------------------


def _blobless_clone(tmp_path: Path, name: str) -> tuple[Path, str, str]:
    """A real `--filter=blob:none` clone of a local origin: every blob is promised, not present."""
    origin = tmp_path / "origin"
    if not origin.exists():
        make_repo(origin, {"a.txt": b"one\n"})
        git(origin, "config", "uploadpack.allowFilter", "true")
        git(origin, "config", "uploadpack.allowAnySHA1InWant", "true")
    sha = git(origin, "rev-parse", "HEAD")
    blob = git(origin, "rev-parse", f"{sha}:a.txt")
    clone = tmp_path / name / "hermes-agent"
    proc = subprocess.run(
        ["git", "clone", "-q", "--no-checkout", "--filter=blob:none", f"file://{origin}",
         str(clone)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        pytest.skip(f"this git cannot make a blobless clone: {proc.stderr.strip()}")
    return clone, sha, blob


def _has_object_locally(clone: Path, oid: str) -> bool:
    return subprocess.run(
        ["git", "-c", "protocol.allow=never", "-C", str(clone), "cat-file", "-e", oid],
        capture_output=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    ).returncode == 0


def test_a_blobless_partial_clone_is_refused(tmp_path: Path) -> None:
    clone, _sha, blob = _blobless_clone(tmp_path, "refs")
    assert not _has_object_locally(clone, blob)
    with pytest.raises(safety.SafetyError, match=r"partial clone|promisor"):
        safety.resolve_clone_git_dirs(clone)
    assert not _has_object_locally(clone, blob)  # checking it fetched nothing


def test_reading_a_promised_blob_never_lazily_fetches_it(tmp_path: Path) -> None:
    control, _sha, control_blob = _blobless_clone(tmp_path, "control")
    fetched = subprocess.run(
        ["git", "-C", str(control), "cat-file", "-p", control_blob], capture_output=True
    )
    if fetched.returncode != 0 or not _has_object_locally(control, control_blob):
        pytest.skip("this git does not lazily fetch in a partial clone; nothing to prove")
    clone, _sha, blob = _blobless_clone(tmp_path, "refs")  # a plain git read WOULD fetch here
    with safety.BlobReader(clone) as reader, pytest.raises(safety.SafetyError, match="missing"):
        reader.read(blob)
    assert not _has_object_locally(clone, blob)


def test_a_clone_config_cannot_re_enable_a_transport_for_a_lazy_fetch(tmp_path: Path) -> None:
    """`protocol.file.allow=always` beats `-c protocol.allow=never`, so `GIT_ALLOW_PROTOCOL` must
    hold on its own: GIT_NO_LAZY_FETCH is dropped here to model a partial clone that got past
    the detection on a git that predates it."""
    control, _sha, control_blob = _blobless_clone(tmp_path, "control")
    git(control, "config", "protocol.file.allow", "always")
    plain_env = {k: v for k, v in safety.git_env().items() if k != "GIT_NO_LAZY_FETCH"}
    del plain_env["GIT_ALLOW_PROTOCOL"]
    fetched = subprocess.run(
        safety.git_argv(control, "cat-file", "-p", control_blob), capture_output=True,
        env=plain_env,
    )
    if fetched.returncode != 0 or not _has_object_locally(control, control_blob):
        pytest.skip("the config override does not re-enable a lazy fetch on this git")
    clone, _sha, blob = _blobless_clone(tmp_path, "refs")
    git(clone, "config", "protocol.file.allow", "always")
    held_env = {k: v for k, v in safety.git_env().items() if k != "GIT_NO_LAZY_FETCH"}
    result = subprocess.run(
        safety.git_argv(clone, "cat-file", "-p", blob), capture_output=True, env=held_env
    )
    assert result.returncode != 0
    assert not _has_object_locally(clone, blob)


@pytest.mark.parametrize(
    "config",
    [
        [("core.repositoryformatversion", "1"), ("extensions.partialClone", "origin")],
        [("remote.origin.url", "https://example.invalid/x.git"),
         ("remote.origin.promisor", "true")],
        [("remote.origin.url", "https://example.invalid/x.git"),
         ("remote.origin.partialclonefilter", "blob:none")],
    ],
)
def test_partial_clone_configuration_is_refused(tmp_path: Path, config: list) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    for key, value in config:
        git(repo, "config", key, value)
    with pytest.raises(safety.SafetyError, match=r"partial clone|promisor|git config"):
        safety.resolve_clone_git_dirs(repo)


def test_a_disabled_promisor_flag_and_an_ordinary_remote_are_accepted(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    git(repo, "config", "remote.origin.url", "https://example.invalid/x.git")
    git(repo, "config", "remote.origin.promisor", "false")
    safety.resolve_clone_git_dirs(repo)


def test_promisor_packs_in_the_object_store_are_refused(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    pack = repo / ".git" / "objects" / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "pack-0000000000000000000000000000000000000000.promisor").write_text("")
    with pytest.raises(safety.SafetyError, match="promisor packs"):
        safety.resolve_clone_git_dirs(repo)


# ---- exact tree extraction ---------------------------------------------------------------------

_TREE_FILES = {
    "README.md": b"hello\n",
    "pkg/__init__.py": b"# init\n",
    "pkg/mod.py": b"x = 1\n",
    "bin/run.sh": b"#!/bin/sh\necho hi\n",
    "uv.lock": b"version = 1\n",
}


@pytest.fixture
def tree(tmp_path: Path) -> SimpleNamespace:
    repo, sha = make_repo(
        tmp_path / "refs" / "hermes-agent", _TREE_FILES,
        executable=("bin/run.sh",), symlinks={"pkg/link.py": "mod.py"},
    )
    dest = tmp_path / "builds" / "candidate" / "src"
    entries = safety.write_tree_exact(repo, sha, dest)
    return SimpleNamespace(repo=repo, sha=sha, dest=dest, entries=entries, tmp=tmp_path)


def test_write_tree_exact_writes_raw_blobs_with_private_modes(tree: SimpleNamespace) -> None:
    assert safety.verify_tree_matches_commit(tree.dest, tree.entries) == []
    for rel, data in _TREE_FILES.items():
        assert (tree.dest / rel).read_bytes() == data
    assert stat.S_IMODE((tree.dest / "README.md").stat().st_mode) == 0o600
    assert stat.S_IMODE((tree.dest / "bin" / "run.sh").stat().st_mode) == 0o700
    assert stat.S_IMODE((tree.dest / "pkg").stat().st_mode) == 0o700
    assert stat.S_IMODE(tree.dest.stat().st_mode) == 0o700
    assert os.readlink(tree.dest / "pkg" / "link.py") == "mod.py"
    assert {e.mode for e in tree.entries} == {"100644", "100755", "120000"}


def test_write_tree_exact_is_not_affected_by_export_attributes_or_eol_filters(
    tmp_path: Path,
) -> None:
    files = {
        ".gitattributes": (
            b"secret.txt export-ignore\nsubst.txt export-subst\n*.txt text eol=crlf\n"
        ),
        "secret.txt": b"kept\n",
        "subst.txt": b"$Format:%H$\n",
        "plain.txt": b"a\nb\n",
    }
    repo, sha = make_repo(tmp_path / "refs" / "hermes-agent", files)
    dest = tmp_path / "src"
    entries = safety.write_tree_exact(repo, sha, dest)
    for rel, data in files.items():  # `git archive` would drop, rewrite and CRLF-convert these
        assert (dest / rel).read_bytes() == data
    assert safety.verify_tree_matches_commit(dest, entries) == []


def test_write_tree_exact_refuses_a_symlink_that_leaves_the_tree(tmp_path: Path) -> None:
    for name, target in (("dotdot", "../../outside"), ("absolute", "/etc/passwd")):
        repo, sha = make_repo(
            tmp_path / name / "hermes-agent", {"a": b"1\n"}, symlinks={"bad": target}
        )
        with pytest.raises(safety.SafetyError, match="leaves the source tree"):
            safety.write_tree_exact(repo, sha, tmp_path / name / "src")


def test_write_tree_exact_refuses_a_chain_of_links_that_leaves_the_tree(tmp_path: Path) -> None:
    repo, sha = make_repo(
        tmp_path / "hermes-agent", {"a": b"1\n"}, symlinks={"one": "two", "two": "../escape"}
    )
    with pytest.raises(safety.SafetyError, match="source tree"):
        safety.write_tree_exact(repo, sha, tmp_path / "src")


def test_write_tree_exact_needs_an_empty_destination_and_a_full_sha(tree: SimpleNamespace) -> None:
    with pytest.raises(safety.SafetyError, match="is not empty"):
        safety.write_tree_exact(tree.repo, tree.sha, tree.dest)
    for bad in ("HEAD", tree.sha.upper(), tree.sha[:12], "--all"):
        with pytest.raises(safety.SafetyError, match="40-character"):
            safety.write_tree_exact(tree.repo, bad, tree.tmp / "other")


@pytest.mark.parametrize(
    "path",
    ["", "/abs/x", "../x", "a/../x", "a/./x", "a//b", ".git/config", "a/.GIT/x", ".venv/lib/x",
     "a/.VENV/x", "a\\b", "a\0b"],
)
def test_check_relative_path_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(safety.SafetyError, match="unsafe"):
        safety.check_relative_path(path)


def test_check_relative_path_accepts_ordinary_paths() -> None:
    for path in ("a", "gateway/platforms/base.py", "docs/.hidden", "x.venv"):
        safety.check_relative_path(path)


# ---- verifying the extracted tree against the commit -------------------------------------------


def _tamper_contents(t: SimpleNamespace) -> None:
    (t.dest / "pkg" / "mod.py").write_bytes(b"x = 2\n")


def _tamper_one_byte_keep_size(t: SimpleNamespace) -> None:
    (t.dest / "README.md").write_bytes(b"hellp\n")


def _add_exec_bit(t: SimpleNamespace) -> None:
    os.chmod(t.dest / "README.md", 0o700)


def _drop_exec_bit(t: SimpleNamespace) -> None:
    os.chmod(t.dest / "bin" / "run.sh", 0o600)


def _delete_file(t: SimpleNamespace) -> None:
    (t.dest / "README.md").unlink()


def _add_source_file(t: SimpleNamespace) -> None:
    (t.dest / "pkg" / "evil.py").write_text("import os\n")


def _add_sitecustomize(t: SimpleNamespace) -> None:
    (t.dest / "sitecustomize.py").write_text("import os\n")


def _add_pth(t: SimpleNamespace) -> None:
    (t.dest / "evil.pth").write_text("import os\n")


def _add_pycache(t: SimpleNamespace) -> None:
    (t.dest / "__pycache__").mkdir()
    (t.dest / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"\0")


def _venv_as_symlink(t: SimpleNamespace) -> None:
    (t.tmp / "elsewhere").mkdir()
    (t.dest / ".venv").symlink_to(t.tmp / "elsewhere")


def _egg_info_with_code(t: SimpleNamespace) -> None:
    (t.dest / "hermes.egg-info").mkdir()
    (t.dest / "hermes.egg-info" / "hook.py").write_text("import os\n")


def _egg_info_as_symlink(t: SimpleNamespace) -> None:
    (t.tmp / "elsewhere").mkdir()
    (t.dest / "hermes.egg-info").symlink_to(t.tmp / "elsewhere")


def _egg_info_nested_egg_info(t: SimpleNamespace) -> None:
    (t.dest / "pkg" / "x.egg-info").mkdir()  # only TOP-LEVEL egg-info is a known generated dir


def _file_to_symlink(t: SimpleNamespace) -> None:
    (t.dest / "README.md").unlink()
    (t.dest / "README.md").symlink_to(t.dest / "pkg" / "mod.py")


def _dir_to_symlink(t: SimpleNamespace) -> None:
    elsewhere = t.tmp / "elsewhere"
    shutil.copytree(t.dest / "pkg", elsewhere, symlinks=True)
    shutil.rmtree(t.dest / "pkg")
    (t.dest / "pkg").symlink_to(elsewhere)


def _link_retargeted(t: SimpleNamespace) -> None:
    (t.dest / "pkg" / "link.py").unlink()
    (t.dest / "pkg" / "link.py").symlink_to("__init__.py")


def _link_leaves_tree(t: SimpleNamespace) -> None:
    (t.dest / "pkg" / "link.py").unlink()
    (t.dest / "pkg" / "link.py").symlink_to("../../outside")


def _group_writable(t: SimpleNamespace) -> None:
    os.chmod(t.dest / "README.md", 0o660)


def _hard_linked(t: SimpleNamespace) -> None:
    os.link(t.dest / "README.md", t.tmp / "hardlink")


def _file_to_directory(t: SimpleNamespace) -> None:
    (t.dest / "README.md").unlink()
    (t.dest / "README.md").mkdir()


def _file_to_fifo(t: SimpleNamespace) -> None:
    (t.dest / "README.md").unlink()
    os.mkfifo(t.dest / "README.md")


def _extra_fifo(t: SimpleNamespace) -> None:
    os.mkfifo(t.dest / "pipe")


def _dotgit(t: SimpleNamespace) -> None:
    (t.dest / ".git").mkdir()


def _writable_directory(t: SimpleNamespace) -> None:
    os.chmod(t.dest / "pkg", 0o770)  # noqa: S103 - intentional unsafe-mode fixture


_TAMPERINGS = [
    (_tamper_contents, "contents differ"),
    (_tamper_one_byte_keep_size, "contents differ"),
    (_add_exec_bit, "executable bit differs"),
    (_drop_exec_bit, "executable bit differs"),
    (_delete_file, "missing from the extracted tree"),
    (_add_source_file, "untracked"),
    (_add_sitecustomize, "untracked"),
    (_add_pth, "untracked"),
    (_add_pycache, "untracked"),
    (_venv_as_symlink, "not a real directory"),
    (_egg_info_with_code, "contains code"),
    (_egg_info_as_symlink, "untracked"),
    (_egg_info_nested_egg_info, "untracked"),
    (_file_to_symlink, "expected a regular file"),
    (_dir_to_symlink, "expected a directory"),
    (_link_retargeted, "symlink target differs"),
    (_link_leaves_tree, "symlink"),
    (_group_writable, "writable by group or others"),
    (_hard_linked, "hard links"),
    (_file_to_directory, "expected a regular file"),
    (_dotgit, "untracked"),
    (_writable_directory, "writable by group or others"),
]
if hasattr(os, "mkfifo"):
    _TAMPERINGS += [(_file_to_fifo, "expected a regular file"), (_extra_fifo, "untracked")]


@pytest.mark.parametrize(("tamper", "needle"), _TAMPERINGS, ids=lambda v: getattr(v, "__name__", v))
def test_verify_tree_detects_any_deviation_from_the_commit(
    tree: SimpleNamespace, tamper, needle: str
) -> None:
    tamper(tree)
    problems = safety.verify_tree_matches_commit(tree.dest, tree.entries)
    assert any(needle in p for p in problems), problems


def test_verify_tree_tolerates_exactly_the_known_generated_pieces(tree: SimpleNamespace) -> None:
    (tree.dest / ".venv" / "lib").mkdir(parents=True)
    (tree.dest / ".venv" / "lib" / "anything.py").write_text("not inspected\n")
    egg = tree.dest / "hermes_agent.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_text("Name: hermes\n")
    (egg / "SOURCES.txt").write_text("pkg/mod.py\n")
    assert safety.verify_tree_matches_commit(tree.dest, tree.entries) == []


def test_verify_tree_refuses_a_symlinked_or_missing_source_directory(
    tree: SimpleNamespace,
) -> None:
    (tree.tmp / "alias").symlink_to(tree.dest)
    (problem,) = safety.verify_tree_matches_commit(tree.tmp / "alias", tree.entries)
    assert "not a real directory" in problem
    assert safety.verify_tree_matches_commit(tree.tmp / "nope", tree.entries) == [
        "source directory is not accessible"
    ]


def test_verify_tree_reports_a_bounded_number_of_problems(tree: SimpleNamespace) -> None:
    for i in range(200):
        (tree.dest / f"junk{i}.py").write_text("x")
    assert len(safety.verify_tree_matches_commit(tree.dest, tree.entries)) <= 25


# ---- copying bridge files without following anything ---------------------------------------------


@pytest.fixture
def bridge_src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "gateway" / "platforms").mkdir(parents=True)
    (src / "gateway" / "run.py").write_text("run\n")
    (src / "gateway" / "platforms" / "base.py").write_text("base\n")
    (src / "hermes_constants.py").write_text("const\n")
    return src


_RELS = ["gateway/run.py", "gateway/platforms/base.py", "hermes_constants.py"]


def test_copy_regular_files_copies_privately(bridge_src: Path, tmp_path: Path) -> None:
    dest = tmp_path / "copy"
    safety.copy_regular_files(bridge_src, _RELS, dest)
    for rel in _RELS:
        assert (dest / rel).read_bytes() == (bridge_src / rel).read_bytes()
        assert stat.S_IMODE((dest / rel).stat().st_mode) == 0o600
    assert stat.S_IMODE((dest / "gateway" / "platforms").stat().st_mode) == 0o700
    assert sorted(p.name for p in dest.iterdir()) == ["gateway", "hermes_constants.py"]


def test_copy_regular_files_never_follows_a_symlinked_file(
    bridge_src: Path, tmp_path: Path
) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    (bridge_src / "gateway" / "run.py").unlink()
    (bridge_src / "gateway" / "run.py").symlink_to(secret)
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.copy_regular_files(bridge_src, _RELS, tmp_path / "copy")
    copied = [p for p in (tmp_path / "copy").rglob("*") if p.is_file()]
    assert not any("TOP SECRET" in p.read_text() for p in copied)


def test_copy_regular_files_never_follows_a_symlinked_directory(
    bridge_src: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    shutil.copytree(bridge_src / "gateway", elsewhere)
    shutil.rmtree(bridge_src / "gateway")
    (bridge_src / "gateway").symlink_to(elsewhere)
    with pytest.raises(safety.SafetyError, match="not a real directory"):
        safety.copy_regular_files(bridge_src, _RELS, tmp_path / "copy")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs FIFOs")
def test_copy_regular_files_refuses_a_fifo_without_opening_it(
    bridge_src: Path, tmp_path: Path
) -> None:
    (bridge_src / "hermes_constants.py").unlink()
    os.mkfifo(bridge_src / "hermes_constants.py")  # opening this for reading would block forever
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.copy_regular_files(bridge_src, _RELS, tmp_path / "copy")


def test_copy_regular_files_refuses_a_directory_in_place_of_a_file(
    bridge_src: Path, tmp_path: Path
) -> None:
    (bridge_src / "hermes_constants.py").unlink()
    (bridge_src / "hermes_constants.py").mkdir()
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.copy_regular_files(bridge_src, _RELS, tmp_path / "copy")


@pytest.mark.parametrize(
    "rel", [".venv/lib/x.py", "a/.venv/x.py", ".git/config", "../outside", "/etc/passwd", "a/../b"]
)
def test_copy_regular_files_refuses_venv_git_and_escaping_paths(
    bridge_src: Path, tmp_path: Path, rel: str
) -> None:
    (bridge_src / ".venv" / "lib").mkdir(parents=True)
    (bridge_src / ".venv" / "lib" / "x.py").write_text("venv\n")
    with pytest.raises(safety.SafetyError, match="unsafe"):
        safety.copy_regular_files(bridge_src, [rel], tmp_path / "copy")
    assert not (tmp_path / "copy" / ".venv").exists()


def test_copy_regular_files_refuses_an_oversized_file(
    bridge_src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(safety, "MAX_BRIDGE_FILE_BYTES", 3)
    with pytest.raises(safety.SafetyError, match="unexpectedly large"):
        safety.copy_regular_files(bridge_src, ["hermes_constants.py"], tmp_path / "copy")


# ---- layouts ------------------------------------------------------------------------------------


@pytest.fixture
def layout(tmp_path: Path) -> SimpleNamespace:
    dirs = {name: tmp_path / name for name in ("builds", "refs", "out", "repo")}
    for path in dirs.values():
        path.mkdir()
    return SimpleNamespace(tmp=tmp_path, **dirs)


def _validate(layout: SimpleNamespace, **override) -> None:
    kwargs = {
        "repo_root": layout.repo, "builds_dir": layout.builds, "refs_dir": layout.refs,
        "out": layout.out,
    }
    kwargs.update(override)
    safety.validate_candidate_layout(**kwargs)


def test_layout_accepts_disjoint_scratch_dirs(layout: SimpleNamespace) -> None:
    _validate(layout)
    _validate(layout, json_out=layout.out / "report.json")


@pytest.mark.parametrize("which", ["builds_dir", "out"])
def test_layout_refuses_a_symlinked_builds_or_out_dir(layout: SimpleNamespace, which: str) -> None:
    link = layout.tmp / "link"
    link.symlink_to(layout.builds if which == "builds_dir" else layout.out)
    with pytest.raises(safety.SafetyError, match="symlink"):
        _validate(layout, **{which: link})


def test_layout_refuses_symlinked_candidate_build_source_and_scratch_dirs(
    layout: SimpleNamespace,
) -> None:
    elsewhere = layout.tmp / "elsewhere"
    elsewhere.mkdir()
    (layout.builds / "candidate").symlink_to(elsewhere)
    with pytest.raises(safety.SafetyError, match="candidate build directory"):
        _validate(layout)
    (layout.builds / "candidate").unlink()
    (layout.builds / "candidate").mkdir()
    (layout.builds / "candidate" / "src").symlink_to(elsewhere)
    with pytest.raises(safety.SafetyError, match="candidate source directory"):
        _validate(layout)
    (layout.builds / "candidate" / "src").unlink()
    (layout.out / "candidate").symlink_to(elsewhere)
    with pytest.raises(safety.SafetyError, match="scratch directory"):
        _validate(layout)


def test_layout_refuses_overlapping_directories(layout: SimpleNamespace) -> None:
    for override in (
        {"out": layout.builds},  # the same directory
        {"out": layout.builds / "scratch"},  # scratch inside the extracted builds
        {"builds_dir": layout.out / "builds"},  # builds inside scratch
        {"refs_dir": layout.out / "refs"},  # the clone inside scratch
        {"refs_dir": layout.builds},
        {"repo_root": layout.out / "repo"},  # the repository inside scratch
        {"out": layout.repo / "scratch"},  # scratch inside the repository
        {"builds_dir": layout.repo / "builds"},
    ):
        with pytest.raises(safety.SafetyError, match="overlap"):
            _validate(layout, **override)


def test_layout_refuses_paths_in_or_around_the_real_home(
    layout: SimpleNamespace, account_home: Path
) -> None:
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        _validate(layout, builds_dir=account_home / "builds")
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        _validate(layout, out=account_home / ".hermes" / "scratch")
    with pytest.raises(safety.SafetyError, match="contains the real user home"):
        _validate(layout, out=layout.tmp)


def test_layout_refuses_a_refs_dir_inside_the_live_hermes_home(
    layout: SimpleNamespace, account_home: Path
) -> None:
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        _validate(layout, refs_dir=account_home / ".hermes" / "refs")
    # a refs dir that merely lives in the real home (an ordinary checkout) is fine
    _validate(layout, refs_dir=account_home / "src" / "_refs")


def test_layout_json_out_must_be_a_new_regular_file_inside_scratch(layout: SimpleNamespace) -> None:
    elsewhere = layout.tmp / "elsewhere"
    elsewhere.mkdir()
    (layout.out / "linked.json").symlink_to(elsewhere / "target.json")
    (layout.out / "linkdir").symlink_to(elsewhere)
    (layout.out / "adir").mkdir()
    refused = [
        (layout.tmp / "report.json", "inside the private scratch"),  # outside --out
        (layout.out.parent / "elsewhere" / "report.json", "inside the private scratch"),
        (layout.out, "inside the private scratch"),  # the scratch directory itself
        (layout.out / "linked.json", "symlink"),
        (layout.out / "linkdir" / "report.json", "symlink"),
        (layout.out / "adir", "not a regular file"),
    ]
    for json_out, message in refused:
        with pytest.raises(safety.SafetyError, match=message):
            _validate(layout, json_out=json_out)
    with pytest.raises(safety.SafetyError, match="scratch"):
        safety.validate_candidate_layout(
            repo_root=layout.repo, builds_dir=layout.builds, refs_dir=layout.refs,
            json_out=layout.out / "r.json",
        )


def test_layout_json_out_overlapping_the_repo_refs_or_builds_is_refused(
    layout: SimpleNamespace,
) -> None:
    # --out itself may not contain any of them, so this is refused before json_out is looked at
    inner = layout.out / "inner"
    for name in ("repo_root", "refs_dir", "builds_dir"):
        with pytest.raises(safety.SafetyError, match="overlap"):
            _validate(layout, **{name: inner}, json_out=inner / "r.json")


# ---- recursive alternates ----------------------------------------------------------------------


def _alternate(objects_dir: Path, target: Path | str, name: str = "alternates") -> None:
    (objects_dir / "info").mkdir(parents=True, exist_ok=True)
    (objects_dir / "info" / name).write_text(f"{target}\n")


def _live_objects(account_home: Path) -> Path:
    objects = account_home / ".hermes" / "hermes-agent" / ".git" / "objects"
    objects.mkdir(parents=True)
    return objects


def test_a_chain_of_alternates_that_ends_in_the_live_hermes_home_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    live = _live_objects(account_home)
    hop = repo / ".git" / "hop-objects"
    hop.mkdir()
    _alternate(repo / ".git" / "objects", "../hop-objects")  # the first hop is relative, harmless
    _alternate(hop, live)  # the second hop leads into ~/.hermes
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(repo)


def test_a_second_hop_through_a_symlink_or_an_http_alternates_file_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    live = _live_objects(account_home)
    innocent = tmp_path / "innocent"
    innocent.symlink_to(live)  # a harmless-looking name that resolves into ~/.hermes
    hop = tmp_path / "hop" / "objects"
    hop.mkdir(parents=True)
    _alternate(repo / ".git" / "objects", hop)
    _alternate(hop, innocent)
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(repo)
    (hop / "info" / "alternates").unlink()
    _alternate(hop, live, name="http-alternates")
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(repo)


def test_an_objects_directory_that_is_a_symlink_into_the_live_hermes_home_is_refused(
    tmp_path: Path, account_home: Path
) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    live = _live_objects(account_home)
    shutil.rmtree(repo / ".git" / "objects")
    (repo / ".git" / "objects").symlink_to(live)
    with pytest.raises(safety.SafetyError, match="live Hermes home"):
        safety.resolve_clone_git_dirs(repo)


def test_a_cycle_of_harmless_alternates_terminates_and_is_accepted(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    objects = repo / ".git" / "objects"
    other = tmp_path / "other" / "objects"
    other.mkdir(parents=True)
    _alternate(objects, other)
    _alternate(other, objects)
    safety.resolve_clone_git_dirs(repo)  # neither raises nor loops


def test_an_absurdly_deep_or_a_quoted_alternates_chain_is_refused(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path / "refs" / "hermes-agent", {"a": b"1\n"})
    objects = repo / ".git" / "objects"
    chain = [tmp_path / f"o{i}" / "objects" for i in range(12)]
    for link in chain:
        link.mkdir(parents=True)
    for here, there in zip([objects, *chain], chain, strict=False):
        _alternate(here, there)
    with pytest.raises(safety.SafetyError, match="too deep"):
        safety.resolve_clone_git_dirs(repo)
    (objects / "info" / "alternates").write_text('"' + str(tmp_path / "x") + '"\n')
    with pytest.raises(safety.SafetyError, match="quoted"):
        safety.resolve_clone_git_dirs(repo)


# ---- a fresh scratch environment for every candidate run ----------------------------------------


def _scrubbed(root: Path, **kwargs):
    with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=True):
        return safety.scrubbed_env(root, **kwargs)


def _touch(*paths: Path) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


def test_reset_scratch_env_deletes_stale_bytecode_caches_and_homes_and_only_those(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    _scrubbed(root)
    stale = [
        root / "pycache" / "agent.cpython-314.pyc",
        root / "cache" / "uv" / "wheels" / "old.whl",
        root / "home" / ".netrc",
        root / "tmp" / "leftover",
        root / "hermes_home" / "state.db",
        *(root / name / "x" for name in safety.ENV_DIR_NAMES),
    ]
    beside = [root / "src" / "agent.py", root / "build-metadata.json", tmp_path / "refs" / "keep"]
    _touch(*stale, *beside)
    safety.reset_scratch_env(root)
    assert not any(path.exists() for path in stale)
    assert all(path.exists() for path in beside)  # the source, the record and refs are not ours
    assert root.is_dir()
    env = _scrubbed(root)  # recreated empty and private
    assert not list(Path(env["PYTHONPYCACHEPREFIX"]).iterdir())
    assert not list(Path(env["UV_CACHE_DIR"]).parent.iterdir())


def test_reset_scratch_env_handles_a_missing_root_and_a_custom_hermes_home(
    tmp_path: Path,
) -> None:
    safety.reset_scratch_env(tmp_path / "never-created")
    root = tmp_path / "root"
    inside = root / "my_home"
    outside = tmp_path / "elsewhere-home"
    _touch(inside / "a", outside / "b")
    safety.reset_scratch_env(root, hermes_home=inside)
    assert not inside.exists()
    safety.reset_scratch_env(root, hermes_home=outside)  # not under root: never ours to delete
    assert (outside / "b").exists()
    safety.reset_scratch_env(root, hermes_home=root)  # the root itself is never deleted
    assert root.is_dir()


def test_reset_scratch_env_refuses_symlinks_and_non_directories_and_deletes_nothing_through_them(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "victim"
    _touch(victim / "keep")
    root = tmp_path / "root"
    _scrubbed(root)
    (root / "cache").rmdir()
    (root / "cache").symlink_to(victim)
    with pytest.raises(safety.SafetyError, match="symlink"):
        safety.reset_scratch_env(root)
    assert (victim / "keep").exists()

    root2 = tmp_path / "root2"
    _scrubbed(root2)
    (root2 / "home").rmdir()
    (root2 / "home").write_text("a file, not a directory")
    with pytest.raises(safety.SafetyError, match="non-directory"):
        safety.reset_scratch_env(root2)
    assert (root2 / "home").read_text() == "a file, not a directory"

    real = tmp_path / "real_root"
    _touch(real / "home" / "keep")
    (tmp_path / "root_link").symlink_to(real)
    with pytest.raises(safety.SafetyError, match="symlink"):
        safety.reset_scratch_env(tmp_path / "root_link")
    assert (real / "home" / "keep").exists()


def test_reset_scratch_env_refuses_the_real_home_and_live_hermes_before_deleting_anything(
    tmp_path: Path, account_home: Path
) -> None:
    _touch(account_home / "scratch" / "home" / "keep")
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.reset_scratch_env(account_home / "scratch")
    assert (account_home / "scratch" / "home" / "keep").exists()
    root = tmp_path / "root"
    _touch(root / "home" / "keep", account_home / ".hermes" / "keep")
    with pytest.raises(safety.SafetyError, match="inside the real user home"):
        safety.reset_scratch_env(root, hermes_home=account_home / ".hermes")
    # everything is validated before anything is deleted: the scratch home survived too
    assert (root / "home" / "keep").exists() and (account_home / ".hermes" / "keep").exists()


# ---- PATH: entries that lead into the live ~/.hermes --------------------------------------------


def _hermes_link_dir(tmp_path: Path, account_home: Path, *, chain: bool) -> Path:
    """A PATH directory OUTSIDE ~/.hermes holding a working `uv` and a `hermes` symlink that
    reaches the live install (directly, or through a chain of links)."""
    live = account_home / ".hermes" / "hermes-agent" / "venv" / "bin"
    live.mkdir(parents=True)
    (live / "hermes").write_text("#!/bin/sh\n")
    directory = tmp_path / "local-bin"
    directory.mkdir()
    if chain:
        (directory / "hermes-1").symlink_to(live / "hermes")
        (directory / "hermes-2").symlink_to(directory / "hermes-1")
        (directory / "hermes").symlink_to(directory / "hermes-2")
    else:
        (directory / "hermes").symlink_to(live / "hermes")
    (directory / "uv").write_text("#!/bin/sh\n")
    os.chmod(directory / "uv", 0o755)  # noqa: S103 - executable fixture
    return directory


@pytest.mark.parametrize("chain", [False, True])
def test_strict_path_drops_a_directory_whose_hermes_link_reaches_the_live_install(
    tmp_path: Path, account_home: Path, chain: bool
) -> None:
    directory = _hermes_link_dir(tmp_path, account_home, chain=chain)
    value = os.pathsep.join(["/usr/bin", str(directory), "/bin"])
    assert safety.sanitized_path(value) == "/usr/bin:/bin"
    assert safety.sanitized_path(value, strict=True) == "/usr/bin:/bin"
    assert str(directory) in safety.sanitized_path(value, strict=False).split(os.pathsep)
    with mock.patch.dict(os.environ, {"PATH": value}, clear=True):
        assert safety.minimal_env()["PATH"] == "/usr/bin:/bin"
        assert safety.minimal_env(strict_path=False)["PATH"] == value
        assert safety.git_env()["PATH"] == "/usr/bin:/bin"
        assert safety.scrubbed_env(tmp_path / "r1")["PATH"] == "/usr/bin:/bin"  # strict by default
        assert safety.scrubbed_env(tmp_path / "r2", strict_path=False)["PATH"] == value


def test_strict_path_keeps_directories_whose_links_go_elsewhere(
    tmp_path: Path, account_home: Path
) -> None:
    (account_home / ".hermes").mkdir()
    directory = tmp_path / "tools"
    directory.mkdir()
    (tmp_path / "real-tool").write_text("")
    (directory / "tool").symlink_to(tmp_path / "real-tool")
    (directory / "dangling").symlink_to(tmp_path / "does-not-exist")
    assert safety.sanitized_path(str(directory)) == str(directory)


def test_find_executable_finds_uv_next_to_a_live_hermes_link_and_never_in_live_hermes(
    tmp_path: Path, account_home: Path
) -> None:
    directory = _hermes_link_dir(tmp_path, account_home, chain=True)
    value = os.pathsep.join([str(directory), "/usr/bin"])
    assert safety.find_executable("uv", value) == str(directory / "uv")
    with mock.patch.dict(os.environ, {"PATH": value}, clear=True):
        assert safety.require_uv() == str(directory / "uv")
        assert safety.sanitized_path(os.environ["PATH"]) == "/usr/bin"  # ... yet off the PATH

    live_bin = account_home / ".hermes" / "hermes-agent" / "venv" / "bin"
    (live_bin / "uv").write_text("#!/bin/sh\n")
    os.chmod(live_bin / "uv", 0o755)  # noqa: S103 - executable fixture
    linked = tmp_path / "linked-bin"
    linked.mkdir()
    (linked / "uv").symlink_to(live_bin / "uv")  # a `uv` that IS the live install's
    assert safety.find_executable("uv", os.pathsep.join([str(live_bin), str(linked)])) is None


def test_find_executable_ignores_relative_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "bin").mkdir()
    tool = tmp_path / "bin" / "uv"
    tool.write_text("#!/bin/sh\n")
    os.chmod(tool, 0o755)  # noqa: S103 - executable fixture
    monkeypatch.chdir(tmp_path)
    assert safety.find_executable("uv", "bin") is None
    assert safety.find_executable("uv", os.pathsep.join(["", ".", "bin"])) is None


def test_require_uv_says_how_to_set_it_up(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with (
        mock.patch.dict(os.environ, {"PATH": str(empty)}, clear=True),
        pytest.raises(safety.SafetyError, match=r"`uv` was not found on PATH.*Install uv"),
    ):
        safety.require_uv()


# ---- interpreters: nothing in the real home is ever executed -----------------------------------


def _interpreter(path: Path, mode: int = 0o755) -> Path:
    """A stand-in interpreter file (never executed by these tests)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 1\n")
    os.chmod(path, mode)
    os.chmod(path.parent, 0o755)  # noqa: S103 - a system-like bin directory
    return path


@pytest.fixture
def no_exec():
    """Every process start fails the test: validation must execute nothing."""
    with (
        mock.patch.object(safety.subprocess, "run", side_effect=AssertionError("executed")) as run,
        mock.patch.object(safety.subprocess, "Popen", side_effect=AssertionError("executed")),
    ):
        yield run


def test_a_base_interpreter_outside_the_home_is_accepted_by_its_real_path(
    tmp_path: Path, no_exec
) -> None:
    real = _interpreter(tmp_path / "usr" / "bin" / "python3.14")
    link = tmp_path / "usr" / "local" / "python3"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    assert safety.validate_base_interpreter(real) == real.resolve()
    assert safety.validate_base_interpreter(link) == real.resolve()


def _home_python(account_home: Path) -> Path:
    return _interpreter(account_home / ".pyenv" / "versions" / "3.14" / "bin" / "python3.14")


@pytest.mark.parametrize(
    "shape",
    ["in_home", "link_into_home", "chain_through_home", "dir_link_into_home",
     "dir_link_through_home", "relative"],
)
def test_an_interpreter_in_or_linking_through_the_home_is_refused_without_running_it(
    tmp_path: Path, account_home: Path, no_exec, shape: str
) -> None:
    outside = _interpreter(tmp_path / "opt" / "bin" / "python3.14")
    home_python = _home_python(account_home)
    path: Path | str
    if shape == "in_home":
        path = home_python
    elif shape == "link_into_home":
        path = tmp_path / "usr-bin-python3"
        path.symlink_to(home_python)
    elif shape == "chain_through_home":  # ends outside, but passes a link that lives in the home
        hop = account_home / "hop"
        hop.symlink_to(outside)
        path = tmp_path / "python3"
        path.symlink_to(hop)
    elif shape == "dir_link_into_home":
        (tmp_path / "pydir").symlink_to(home_python.parent)
        path = tmp_path / "pydir" / "python3.14"
    elif shape == "dir_link_through_home":  # a home directory holding a link back out
        (account_home / "stuff").mkdir()
        (account_home / "stuff" / "python3").symlink_to(outside)
        (tmp_path / "dirlink").symlink_to(account_home / "stuff")
        path = tmp_path / "dirlink" / "python3"
    else:
        path = "bin/python3"
    with pytest.raises(safety.SafetyError, match=r"real user home|absolute path"):
        safety.validate_base_interpreter(path)
    no_exec.assert_not_called()


@pytest.mark.parametrize("where", ["beside", "one_level_up", "beside_the_link"])
def test_a_venv_interpreter_is_refused_as_a_base(tmp_path: Path, no_exec, where: str) -> None:
    real = _interpreter(tmp_path / "venv" / "bin" / "python3")
    path = real
    if where == "beside":
        (real.parent / "pyvenv.cfg").write_text("home = /usr/bin\n")
    elif where == "one_level_up":
        (tmp_path / "venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
    else:
        other = _interpreter(tmp_path / "sys" / "python3")
        (tmp_path / "linkvenv" / "bin").mkdir(parents=True)
        (tmp_path / "linkvenv" / "pyvenv.cfg").write_text("home = /x\n")
        path = tmp_path / "linkvenv" / "bin" / "python3"
        path.symlink_to(other)
    with pytest.raises(safety.SafetyError, match="virtual environment"):
        safety.validate_base_interpreter(path)


def test_an_unsafe_interpreter_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(safety.SafetyError, match="does not exist"):
        safety.validate_base_interpreter(tmp_path / "missing")
    with pytest.raises(safety.SafetyError, match="not executable"):
        safety.validate_base_interpreter(_interpreter(tmp_path / "a" / "python3", 0o644))
    with pytest.raises(safety.SafetyError, match="writable by group or others"):
        safety.validate_base_interpreter(_interpreter(tmp_path / "b" / "python3", 0o775))
    (tmp_path / "c" / "python3").mkdir(parents=True)
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.validate_base_interpreter(tmp_path / "c" / "python3")
    loose = _interpreter(tmp_path / "d" / "python3")
    os.chmod(loose.parent, 0o777)  # noqa: S103 - intentional unsafe-mode fixture
    with pytest.raises(safety.SafetyError, match="writable by others"):
        safety.validate_base_interpreter(loose)


@pytest.mark.parametrize("where", ["parent", "directory"])
@pytest.mark.parametrize("mode", [0o777, 0o1777, 0o1775, 0o1757])
def test_an_interpreter_next_to_a_directory_others_can_write_is_refused_even_when_sticky(
    tmp_path: Path, no_exec, where: str, mode: int
) -> None:
    """The interpreter's directory and its parent are both `pyvenv.cfg` lookup locations; another
    user can create a file in a sticky directory too, so there is no `pyvenv.cfg` to find yet."""
    real = _interpreter(tmp_path / "shared" / "bin" / "python3.14")
    assert not (tmp_path / "shared" / safety.PYVENV_CFG).exists()
    assert not (real.parent / safety.PYVENV_CFG).exists()
    os.chmod(tmp_path / "shared" if where == "parent" else real.parent, mode)
    try:
        with pytest.raises(safety.SafetyError, match="writable by others"):
            safety.validate_base_interpreter(real)
    finally:
        os.chmod(tmp_path / "shared", 0o755)  # noqa: S103 - let pytest clean up
        os.chmod(real.parent, 0o755)  # noqa: S103
    no_exec.assert_not_called()


def test_an_interpreter_in_a_private_location_is_accepted(tmp_path: Path, no_exec) -> None:
    real = _interpreter(tmp_path / "private" / "bin" / "python3.14")
    os.chmod(tmp_path / "private", 0o755)  # noqa: S103 - a system-like prefix
    assert safety.validate_base_interpreter(real) == real.resolve()
    # A link reaches the same real path, so the same two directories are the ones checked.
    link = tmp_path / "usr" / "local" / "python3"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    assert safety.validate_base_interpreter(link) == real.resolve()


def _venv(root: Path, target: Path, home: str | None = None) -> Path:
    venv = root / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(target)
    (venv / "bin" / "python3").symlink_to("python")
    (venv / "pyvenv.cfg").write_text(f"home = {home or target.parent}\nversion_info = 3.14.2\n")
    return venv


def test_a_venv_on_a_validated_interpreter_is_accepted(tmp_path: Path, no_exec) -> None:
    base = _interpreter(tmp_path / "usr" / "bin" / "python3.14")
    venv = _venv(tmp_path / "src", base)
    safety.validate_venv_interpreters(venv)
    safety.validate_venv_interpreters(venv, {base.resolve()})
    other = _interpreter(tmp_path / "other" / "python3.14")
    with pytest.raises(safety.SafetyError, match="not to the validated candidate interpreter"):
        safety.validate_venv_interpreters(venv, {other})


@pytest.mark.parametrize(
    "tamper",
    ["extra_python_into_home", "cfg_home_in_home", "cfg_base_executable_in_home",
     "cfg_relative_home", "cfg_missing", "cfg_symlink", "cfg_without_home", "venv_symlink"],
)
def test_a_venv_leading_into_the_home_is_refused_before_anything_runs(
    tmp_path: Path, account_home: Path, no_exec, tamper: str
) -> None:
    base = _interpreter(tmp_path / "usr" / "bin" / "python3.14")
    venv = _venv(tmp_path / "src", base)
    cfg = venv / "pyvenv.cfg"
    home_python = _home_python(account_home)
    if tamper == "extra_python_into_home":  # `python` is fine; a sibling a shebang may use is not
        (venv / "bin" / "python3.14").symlink_to(home_python)
    elif tamper == "cfg_home_in_home":
        cfg.write_text(f"home = {home_python.parent}\n")
    elif tamper == "cfg_base_executable_in_home":
        cfg.write_text(f"home = {base.parent}\nbase-executable = {home_python}\n")
    elif tamper == "cfg_relative_home":
        cfg.write_text("home = bin\n")
    elif tamper == "cfg_missing":
        cfg.unlink()
    elif tamper == "cfg_symlink":
        real = tmp_path / "cfg"
        real.write_text(f"home = {base.parent}\n")
        cfg.unlink()
        cfg.symlink_to(real)
    elif tamper == "cfg_without_home":
        cfg.write_text("version_info = 3.14.2\n")
    else:
        moved = tmp_path / "elsewhere-venv"
        venv.rename(moved)
        venv.symlink_to(moved)
    with pytest.raises(safety.SafetyError):
        safety.validate_venv_interpreters(venv, {base.resolve()})
    no_exec.assert_not_called()


def test_the_candidate_layout_refuses_an_interpreter_inside_candidate_controlled_dirs(
    tmp_path: Path,
) -> None:
    for name in ("refs", "builds", "out"):
        (tmp_path / name).mkdir()
    layout = {"repo_root": tmp_path / "repo", "builds_dir": tmp_path / "builds",
              "refs_dir": tmp_path / "refs", "out": tmp_path / "out"}
    (tmp_path / "repo").mkdir()
    in_refs = _interpreter(tmp_path / "refs" / "hermes-agent" / "python3")
    with pytest.raises(safety.SafetyError, match="lies inside --refs-dir"):
        safety.validate_candidate_layout(**layout, interpreter=in_refs)
    outside = _interpreter(tmp_path / "sys" / "bin" / "python3.14")
    link = tmp_path / "builds" / "python3"  # a link planted in the builds dir, to a real python
    link.symlink_to(outside)
    with pytest.raises(safety.SafetyError, match="lies inside --builds-dir"):
        safety.validate_candidate_layout(**layout, interpreter=link)
    assert safety.validate_candidate_layout(**layout, interpreter=outside) == outside.resolve()
    assert safety.validate_candidate_layout(**layout) is None


@pytest.mark.parametrize("directory", ["builds", "refs", "out", "repo"])
def test_the_candidate_layout_refuses_a_planted_link_spelled_through_a_parent_alias(
    tmp_path: Path, directory: str
) -> None:
    """A link inside a candidate-controlled directory, reached through an alias of that directory
    (as `/tmp/x` for `/private/tmp/x`): neither the lexical check nor the link's destination
    shows where the link itself lives."""
    layout = {"repo_root": tmp_path / "repo", "builds_dir": tmp_path / "builds",
              "refs_dir": tmp_path / "refs", "out": tmp_path / "out"}
    for path in layout.values():
        path.mkdir()
    outside = _interpreter(tmp_path / "sys" / "bin" / "python3.14")
    controlled = tmp_path / directory
    (controlled / "python3").symlink_to(outside)
    alias = tmp_path / "alias"
    alias.symlink_to(controlled)
    with pytest.raises(safety.SafetyError, match="lies inside"):
        safety.validate_candidate_layout(**layout, interpreter=alias / "python3")


@pytest.mark.skipif(
    os.path.realpath("/tmp") == "/tmp" or not os.access("/tmp", os.W_OK),  # noqa: S108
    reason="/tmp is not an alias here",  # noqa: S108
)
def test_the_candidate_layout_refuses_a_planted_link_spelled_through_the_tmp_alias() -> None:
    import tempfile

    # This test intentionally uses the platform's public temporary-directory alias.
    with tempfile.TemporaryDirectory(dir="/tmp") as raw:
        root = Path(raw)
        layout = {"repo_root": root / "repo", "builds_dir": root / "builds",
                  "refs_dir": root / "refs", "out": root / "out"}
        for path in layout.values():
            path.mkdir()
        outside = _interpreter(root / "sys" / "bin" / "python3.14")
        (root / "builds" / "python3").symlink_to(outside)
        real_spelling = Path(os.path.realpath(root))
        with pytest.raises(safety.SafetyError, match="lies inside --builds-dir"):
            safety.validate_candidate_layout(
                repo_root=real_spelling / "repo", builds_dir=real_spelling / "builds",
                refs_dir=real_spelling / "refs", out=real_spelling / "out",
                interpreter=root / "builds" / "python3",
            )


# ---- reading a file that may have been replaced by a link ---------------------------------------


def test_read_regular_file_reads_only_real_regular_files(tmp_path: Path) -> None:
    assert safety.read_regular_file(tmp_path / "missing", 100) is None
    (tmp_path / "f").write_bytes(b"data")
    assert safety.read_regular_file(tmp_path / "f", 100) == b"data"
    with pytest.raises(safety.SafetyError, match="unexpectedly large"):
        safety.read_regular_file(tmp_path / "f", 3)
    (tmp_path / "d").mkdir()
    with pytest.raises(safety.SafetyError, match="not a regular file"):
        safety.read_regular_file(tmp_path / "d", 100)


def test_read_regular_file_refuses_symlinks_and_fifos_without_reading_or_blocking(
    tmp_path: Path,
) -> None:
    (tmp_path / "secret").write_bytes(b"do not read")
    (tmp_path / "link").symlink_to(tmp_path / "secret")
    (tmp_path / "dangling").symlink_to(tmp_path / "nowhere")
    for name in ("link", "dangling"):
        with pytest.raises(safety.SafetyError, match="symlink"):
            safety.read_regular_file(tmp_path / name, 100)
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_path / "fifo")
        with pytest.raises(safety.SafetyError, match="not a regular file"):
            safety.read_regular_file(tmp_path / "fifo", 100)
