"""Isolation and verification helpers for the ad-hoc exact `candidate` build.

Shared by `extract.py`, `tools/compat/run_matrix.py` and the fixture tools. Nothing here runs
candidate code; it is the reviewed side of the boundary:

  - the REAL account home (`pwd`/`getuid` on POSIX, the shell's known-folder API on Windows) is
    what every "not inside the real home / live `~/.hermes`" check compares against. It is never
    read from `$HOME`, which the candidate environment deliberately points at private scratch;
  - every candidate subprocess gets a scrubbed environment (`scrubbed_env`): an allowlist of
    essentials plus HOME, HERMES_HOME, XDG_*, TMPDIR and caches all inside private scratch;
  - git is only ever run through `run_git`: `GIT_*` stripped, replace refs, optional locks,
    fsmonitor, hooks, every transport protocol and lazy fetching disabled, and the clone's git
    dirs proven not to lead into `~/.hermes` and not to be a partial (promisor) clone;
  - the only interpreter a candidate venv may be built on is an explicit absolute path, proven
    (`validate_base_interpreter`: lstat/readlink/realpath and `pyvenv.cfg`, nothing executed)
    to be a base interpreter that neither lies in nor links through the real home; a venv's
    `bin/python*` and `pyvenv.cfg` are checked the same way (`validate_venv_interpreters`)
    before its interpreter is executed;
  - the extracted tree is written from raw git blobs (`write_tree_exact`) and proven, byte for
    byte and mode for mode, to be the commit (`verify_tree_matches_commit`) before any candidate
    Python is executed;
  - files are copied without following symlinks, and private files are created 0600 in 0700 dirs.

This is NOT a sandbox and NOT an attestation. Extraction (`uv sync`: build backends and `.pth`
files), the fixture gateway and the read suite execute the candidate's Python and its locked
dependencies as the current user. Pointing HOME/XDG_*/TMPDIR at scratch only changes where
well-behaved code looks; it contains nothing: same-user code can still read the real home
(including a live `~/.hermes`) by absolute path, write anywhere that user can write (including
the scratch directories, the checked tree and the harness's own results) and forge any check made
here after it has run. The checks narrow honest mistakes and catch accidental drift; a pass is
non-adversarial compatibility evidence only. An isolated VM, container or user account protects
the HOST from the candidate; it does not protect this harness's results from code running as the
same user inside it (docs/INSTALL.md).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

CANDIDATE_LABEL = "candidate"  # fixed: an ad-hoc candidate can never pick its own label
CANDIDATE_CLONE = "hermes-agent"  # fixed: ... nor its own clone directory under --refs-dir
# The only ambient variables a candidate subprocess may inherit. Everything else -- notably
# provider API keys, tokens, proxies and every HERMES_*/XDG_*/GIT_*/PYTHON* variable -- is dropped.
ENV_ALLOWLIST = ("PATH", "LANG", "LANGUAGE", "TERM", "SSL_CERT_FILE", "SSL_CERT_DIR")
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
# The private scratch subdirectories `scrubbed_env` creates under its root (HOME, XDG_*, TMPDIR,
# the bytecode prefix and the caches all live in these; uv's cache is `cache/uv`).
ENV_DIR_NAMES = ("home", "cache", "tmp", "config", "data", "state", "runtime", "pycache")
_MAX_ALTERNATES_DEPTH = 8
LIVE_HERMES_DIRNAME = ".hermes"
VENV_DIRNAME = ".venv"
PYVENV_CFG = "pyvenv.cfg"
_MAX_PYVENV_CFG_BYTES = 64 * 1024
_MAX_LINK_HOPS = 40
# `pyvenv.cfg` keys whose value is a path the venv's interpreter (or `site`) uses to find its base.
_PYVENV_PATH_KEYS = ("home", "executable", "base-executable", "base-prefix", "base-exec-prefix")
# Reads of a bridge file / symlink target are bounded so a hostile tree cannot exhaust memory.
MAX_BRIDGE_FILE_BYTES = 16 * 1024 * 1024
_DEFAULT_PATH = "/usr/bin:/bin"
_GENERATED_CODE_SUFFIXES = frozenset(
    {".py", ".pyc", ".pyi", ".pth", ".so", ".pyd", ".dylib", ".dll", ".sh", ".js"}
)
_TREE_KINDS = {"100644": "blob", "100755": "blob", "120000": "blob", "160000": "commit"}
_MAX_PROBLEMS = 25
# Never follow a symlink at the leaf, never block on a FIFO.
READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)


class SafetyError(Exception):
    """A path, environment or source-tree invariant was violated. Callers translate this into
    their own refusal type (`SystemExit` in the CLI tools, `FixtureSafetyError` in the fixtures)."""


# ---- the real account home --------------------------------------------------------------------


def _windows_profile_dir() -> str:  # pragma: no cover -- Windows only
    import ctypes
    from ctypes import wintypes

    class _Guid(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    # FOLDERID_Profile {5E6C858F-0E22-4760-9AFE-EA3317B67173}
    guid = _Guid(
        0x5E6C858F, 0x0E22, 0x4760,
        (ctypes.c_ubyte * 8)(0x9A, 0xFE, 0xEA, 0x33, 0x17, 0xB6, 0x71, 0x73),
    )
    out = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(  # type: ignore[attr-defined]
        ctypes.byref(guid), 0, None, ctypes.byref(out)
    )
    try:
        if result != 0 or not out.value:
            raise SafetyError("cannot determine the real user profile directory; refusing")
        return out.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)  # type: ignore[attr-defined]


def real_user_home() -> Path:
    """The account's real home directory, from the OS account database -- NOT `$HOME`/`~`, which
    a candidate environment (or a careless caller) may have pointed elsewhere. Fails closed."""
    try:
        if sys.platform == "win32":
            raw = _windows_profile_dir()
        else:
            import pwd

            raw = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError, ImportError, AttributeError) as exc:
        raise SafetyError("cannot determine the real account home directory; refusing") from exc
    if not raw or not os.path.isabs(raw):
        raise SafetyError("cannot determine the real account home directory; refusing")
    return Path(raw).resolve()


def live_hermes_home() -> Path:
    return real_user_home() / LIVE_HERMES_DIRNAME


# ---- path containment -------------------------------------------------------------------------


def is_within(path: Path | str, root: Path | str) -> bool:
    """True if `path` is `root` or lies under it, after resolving symlinks. Also compares by
    file identity (`samefile`) so a case-insensitive filesystem or a bind alias cannot slip by."""
    resolved = Path(path).resolve()
    base = Path(root).resolve()
    for candidate in (resolved, *resolved.parents):
        try:
            same = candidate == base or (
                candidate.exists() and base.exists() and os.path.samefile(candidate, base)
            )
        except OSError:
            same = False
        if same:
            return True
    return False


def overlaps(a: Path | str, b: Path | str) -> bool:
    return is_within(a, b) or is_within(b, a)


def assert_outside_real_home(path: Path | str, what: str) -> None:
    """Refuse a path inside the real home, or that contains it (e.g. `/Users`)."""
    home = real_user_home()
    resolved = Path(path).resolve()
    if is_within(resolved, home):
        raise SafetyError(
            f"refusing: {what} ({resolved}) is inside the real user home ({home}). "
            "Use a scratch/tmp directory instead."
        )
    if is_within(home, resolved):
        raise SafetyError(
            f"refusing: {what} ({resolved}) contains the real user home ({home}). "
            "Use a scratch/tmp directory instead."
        )


def assert_not_live_hermes(path: Path | str, what: str, *, contains_ok: bool = False) -> None:
    """Refuse the owner's live `~/.hermes` (or anything inside it, or, unless `contains_ok`,
    anything that contains it) as a source or destination."""
    live = live_hermes_home()
    resolved = Path(path).resolve()
    if is_within(resolved, live):
        raise SafetyError(f"refusing: {what} ({resolved}) is inside the live Hermes home ({live}).")
    if not contains_ok and is_within(live, resolved):
        raise SafetyError(f"refusing: {what} ({resolved}) contains the live Hermes home ({live}).")


def assert_disjoint(items: Sequence[tuple[str, Path | str]]) -> None:
    for i, (what_a, a) in enumerate(items):
        for what_b, b in items[i + 1 :]:
            if overlaps(a, b):
                raise SafetyError(f"refusing: {what_a} and {what_b} overlap.")


def assert_leaf_not_symlink(path: Path | str, what: str) -> None:
    """The path itself (as given, not resolved) must not be a symlink. Ancestors may be: `/tmp`
    is a symlink on macOS."""
    if Path(os.path.abspath(path)).is_symlink():
        raise SafetyError(f"refusing: {what} ({os.path.abspath(path)}) is a symlink.")


def _current_uid() -> int | None:
    return os.getuid() if hasattr(os, "getuid") else None


def _owned_by_me(st: os.stat_result) -> bool:
    uid = _current_uid()
    return uid is None or st.st_uid == uid


def assert_trusted_dir(path: Path | str, what: str) -> None:
    """An existing real directory owned by the current user that no one else can write to."""
    p = Path(os.path.abspath(path))
    try:
        st = p.lstat()
    except OSError as exc:
        raise SafetyError(f"refusing: {what} ({p}) is not accessible: {exc.strerror}") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise SafetyError(f"refusing: {what} ({p}) is not a real directory.")
    if not _owned_by_me(st):
        raise SafetyError(f"refusing: {what} ({p}) is not owned by the current user.")
    if st.st_mode & 0o022:
        raise SafetyError(f"refusing: {what} ({p}) is writable by group or others.")


def ensure_private_dir(path: Path | str, what: str = "directory") -> Path:
    """Create (or tighten) `path` as a real directory, owned by us, mode 0700. Never follows a
    symlink at the leaf."""
    p = Path(os.path.abspath(path))
    if p.is_symlink():
        raise SafetyError(f"refusing: {what} ({p}) is a symlink.")
    if p.exists() or os.path.lexists(p):
        st = p.lstat()
        if not stat.S_ISDIR(st.st_mode):
            raise SafetyError(f"refusing: {what} ({p}) exists and is not a directory.")
        if not _owned_by_me(st):
            raise SafetyError(f"refusing: {what} ({p}) is not owned by the current user.")
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.mkdir(p, 0o700)
    os.chmod(p, 0o700)
    return p


def write_private_file(path: Path | str, data: bytes | str) -> Path:
    """Write `data` to a NEW regular file, mode 0600, never through a symlink. An existing regular
    file of ours (single link) is replaced; anything else at the path is refused."""
    p = Path(os.path.abspath(path))
    try:
        st = p.lstat()
    except FileNotFoundError:
        pass
    else:
        if not stat.S_ISREG(st.st_mode):
            raise SafetyError(f"refusing: {p} exists and is not a regular file.")
        if not _owned_by_me(st) or st.st_nlink != 1:
            raise SafetyError(f"refusing: {p} is not a private single-link file of ours.")
        p.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(p, flags, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fd = -1
            fh.write(data.encode("utf-8") if isinstance(data, str) else data)
    finally:
        if fd != -1:
            os.close(fd)
    return p


def read_regular_file(path: Path | str, limit: int) -> bytes | None:
    """The bytes of a regular file of at most `limit` bytes, or `None` if nothing exists there.
    A symlink (checked before and again at open), FIFO, device, directory or an oversized file is
    refused, never followed, read or waited on."""
    p = Path(os.path.abspath(path))
    try:
        st = p.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(st.st_mode):
        raise SafetyError(f"refusing: {p} is a symlink.")
    if not stat.S_ISREG(st.st_mode):
        raise SafetyError(f"refusing: {p} is not a regular file.")
    try:
        fd = os.open(p, READ_FLAGS)
    except OSError as exc:  # e.g. it became a symlink between the check and the open
        raise SafetyError(f"refusing: cannot open {p} without following a link.") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_ino, opened.st_dev) != (
            st.st_ino, st.st_dev
        ):
            raise SafetyError(f"refusing: {p} changed while being read.")
        with os.fdopen(fd, "rb", closefd=False) as fh:
            data = fh.read(limit + 1)
    finally:
        os.close(fd)
    if len(data) > limit:
        raise SafetyError(f"refusing: {p} is unexpectedly large.")
    return data


def remove_private_tree(path: Path | str, within: Path | str) -> None:
    """Delete a scratch directory tree we created earlier. Refuses symlinks, anything outside
    `within`, and anything that is not a directory."""
    p = Path(os.path.abspath(path))
    if not os.path.lexists(p):
        return
    if p.is_symlink():
        raise SafetyError(f"refusing to remove symlink {p}")
    if not stat.S_ISDIR(p.lstat().st_mode):
        raise SafetyError(f"refusing to remove non-directory {p}")
    if p == Path(os.path.abspath(within)) or not is_within(p, within):
        raise SafetyError(f"refusing to remove {p}: not strictly inside {within}")
    shutil.rmtree(p)


# ---- interpreters: nothing in the real home is ever executed ----------------------------------


def _lexically_within(path: str, root: Path) -> bool:
    parts = Path(os.path.normpath(path)).parts
    return parts[: len(root.parts)] == root.parts


def link_chain(path: Path | str) -> list[str]:
    """`path` (made absolute, NOT resolved) followed by every symlink hop an exec of it passes
    through, each hop's target joined to the directory of the link that names it. Reads links
    only; a missing path, a link loop or an absurdly long chain is a `SafetyError`."""
    current = os.path.abspath(path)
    chain = [current]
    for _ in range(_MAX_LINK_HOPS):
        try:
            st = os.lstat(current)
        except OSError as exc:
            raise SafetyError(f"refusing: {current} does not exist or is not accessible") from exc
        if not stat.S_ISLNK(st.st_mode):
            return chain
        current = os.path.normpath(os.path.join(os.path.dirname(current), os.readlink(current)))
        chain.append(current)
    raise SafetyError(f"refusing: {path} is a symlink chain that is too long (or a loop)")


def assert_chain_outside_real_home(path: Path | str, what: str) -> Path:
    """`path`, every symlink hop after it and its fully resolved real path all lie outside the
    real home -- lexically, resolved, and by each hop's resolved directory (a directory symlink
    into the home that holds a link back out) -- so executing `path` cannot land on, or pass
    through, anything in the home. Returns the real path."""
    home = real_user_home()
    for hop in link_chain(path):
        if (
            _lexically_within(hop, home)
            or is_within(hop, home)
            or is_within(os.path.dirname(hop), home)
        ):
            raise SafetyError(
                f"refusing: {what} ({path}) is, or links through, a path inside the real user "
                f"home ({home}); nothing in the home is ever executed for a candidate."
            )
    final = Path(os.path.realpath(path))
    if is_within(final, home):
        raise SafetyError(
            f"refusing: {what} ({path}) resolves to {final}, inside the real user home ({home})."
        )
    return final


def _assert_safe_executable(final: Path, what: str) -> None:
    try:
        st = os.lstat(final)
    except OSError as exc:
        raise SafetyError(f"refusing: {what} ({final}) is not accessible") from exc
    if not stat.S_ISREG(st.st_mode):
        raise SafetyError(f"refusing: {what} ({final}) is not a regular file.")
    if not st.st_mode & 0o111:
        raise SafetyError(f"refusing: {what} ({final}) is not executable.")
    if st.st_mode & 0o022:
        raise SafetyError(f"refusing: {what} ({final}) is writable by group or others.")
    if st.st_uid not in (0, _current_uid()) and _current_uid() is not None:
        raise SafetyError(f"refusing: {what} ({final}) is owned by another user.")


def validate_base_interpreter(path: Path | str, what: str = "the candidate interpreter") -> Path:
    """Prove, WITHOUT executing anything (lstat, readlink, realpath only), that `path` is an
    acceptable base interpreter for a candidate venv, and return its real path -- the path callers
    then execute. It must be an absolute path; it, every symlink hop and its real path must lie
    outside the real home (`assert_chain_outside_real_home`); the real path must be a regular,
    executable file owned by root or the current user and writable by no one else, in a directory
    whose own parent directory no one else can write either (sticky bit or not: both are
    `pyvenv.cfg` lookup locations); and it must not be a virtual environment's interpreter:
    a `pyvenv.cfg` beside or one level above ANY hop (Python's own lookup) would let it take its
    base, stdlib and site-packages from wherever that file says."""
    raw = os.fspath(path)
    if not raw or not os.path.isabs(raw):
        raise SafetyError(f"refusing: {what} must be an absolute path (got {raw!r}).")
    final = assert_chain_outside_real_home(raw, what)
    _assert_safe_executable(final, what)
    # The interpreter's directory and its parent are both `pyvenv.cfg` lookup locations. A sticky
    # bit only stops others deleting files: they could still create a `pyvenv.cfg` there.
    for lookup in (final.parent, final.parent.parent):
        if os.lstat(lookup).st_mode & 0o022:
            raise SafetyError(
                f"refusing: {lookup}, a directory where Python looks for a {PYVENV_CFG} for "
                f"{what}, is writable by others."
            )
    for hop in [*link_chain(raw), str(final)]:
        directory = os.path.dirname(hop)
        for cfg_dir in (directory, os.path.dirname(directory)):
            if os.path.lexists(os.path.join(cfg_dir, PYVENV_CFG)):
                raise SafetyError(
                    f"refusing: {what} ({raw}) is a virtual environment's interpreter "
                    f"({os.path.join(cfg_dir, PYVENV_CFG)}); give a base (system or VM) Python."
                )
    return final


def _parse_pyvenv_cfg(raw: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw.decode("utf-8", "strict").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip().lower()] = value.strip()
    return values


def validate_venv_interpreters(
    venv_dir: Path | str, allowed: Iterable[Path | str] | None = None
) -> None:
    """Prove, WITHOUT executing anything, that running any interpreter of the venv `venv_dir`
    cannot execute, or take its base from, anything in the real home. `.venv` and `.venv/bin`
    must be real directories; `pyvenv.cfg` must be a regular file whose `home` (required) and any
    other base path (`executable`, `base-executable`, `base-prefix`, `base-exec-prefix`) is
    absolute and outside the home; and EVERY `bin/python*` entry (not just the one about to run:
    shebangs and tools use the others) must, through every symlink hop, stay outside the home and
    resolve to a regular executable no one else can write. With `allowed` (the real paths of
    interpreters already proven by `validate_base_interpreter`), each must also resolve to one of
    them. Raises `SafetyError` otherwise (fail closed)."""
    venv = Path(os.path.abspath(venv_dir))
    home = real_user_home()
    for what, directory in (("the venv", venv), ("the venv's bin directory", venv / "bin")):
        try:
            st = directory.lstat()
        except OSError as exc:
            raise SafetyError(f"refusing: {what} ({directory}) is missing") from exc
        if not stat.S_ISDIR(st.st_mode):
            raise SafetyError(f"refusing: {what} ({directory}) is not a real directory.")
    raw = read_regular_file(venv / PYVENV_CFG, _MAX_PYVENV_CFG_BYTES)
    if raw is None:
        raise SafetyError(f"refusing: {venv} has no {PYVENV_CFG}")
    try:
        cfg = _parse_pyvenv_cfg(raw)
    except UnicodeDecodeError as exc:
        raise SafetyError(f"refusing: {venv / PYVENV_CFG} is not UTF-8") from exc
    if not cfg.get("home"):
        raise SafetyError(f"refusing: {venv / PYVENV_CFG} names no `home`")
    for key in _PYVENV_PATH_KEYS:
        value = cfg.get(key)
        if value is None:
            continue
        if not os.path.isabs(value) or _lexically_within(value, home) or is_within(value, home):
            raise SafetyError(
                f"refusing: {venv / PYVENV_CFG} `{key}` ({value}) is not an absolute path outside "
                f"the real user home ({home})."
            )
    names = sorted(name for name in os.listdir(venv / "bin") if name.startswith("python"))
    if not names:
        raise SafetyError(f"refusing: {venv / 'bin'} has no python interpreter")
    permitted = None if allowed is None else {os.path.realpath(a) for a in allowed}
    for name in names:
        what = f"the venv's bin/{name}"
        final = assert_chain_outside_real_home(venv / "bin" / name, what)
        _assert_safe_executable(final, what)
        if permitted is not None and str(final) not in permitted:
            raise SafetyError(
                f"refusing: {what} resolves to {final}, not to the validated candidate "
                "interpreter."
            )


# ---- scrubbed environments --------------------------------------------------------------------


def _leads_into_live_hermes(directory: str, live: Path) -> bool:
    """True if any symlink directly inside `directory` resolves, through its whole chain, into the
    live Hermes home (the installed `hermes` is typically such a link, e.g. `~/.local/bin/hermes`).
    Only the directory's own entries are listed; a link that cannot be resolved (an error while
    following it) counts as leading in (fail closed); a dangling link does not."""
    try:
        with os.scandir(directory) as entries:
            for dirent in entries:
                if not dirent.is_symlink():
                    continue
                try:
                    if is_within(dirent.path, live):
                        return True
                except (OSError, RuntimeError):
                    return True
    except OSError:
        return False  # not a listable directory: nothing on PATH can be found in it anyway
    return False


def sanitized_path(value: str | None, *, strict: bool = True) -> str:
    """`PATH` without empty/relative entries (a `.` entry would let the candidate's own working
    directory shadow `git`/`uv`) and without anything inside the live Hermes home.

    With `strict` (the default, and always for a candidate) it also drops every entry that
    contains a symlink resolving, through any chain, into the live Hermes home: a directory
    outside `~/.hermes` that holds a `hermes` link to it would otherwise let a bare `hermes` name
    reach the owner's live install. Such an entry may also hold tools we need (a `uv` next to that
    link), so those are resolved first with `find_executable`/`require_uv` and run by absolute
    path. `strict=False` (only the unchanged listed-build extraction) keeps such an entry. A
    wrapper script or copy named `hermes` is not detected: PATH filtering is hygiene, not a
    sandbox."""
    live = live_hermes_home()
    kept = []
    for entry in (value or _DEFAULT_PATH).split(os.pathsep):
        if not entry or not os.path.isabs(entry) or is_within(entry, live):
            continue
        if strict and _leads_into_live_hermes(entry, live):
            continue
        kept.append(entry)
    return os.pathsep.join(kept) or _DEFAULT_PATH


def find_executable(name: str, path_value: str | None = None) -> str | None:
    """Absolute path of the first `name` on `path_value` (default: the caller's `PATH`), skipping
    relative entries and anything in, or resolving into, the live Hermes home. The result is run
    by absolute path, so it works even when its directory is not on the scrubbed `PATH`."""
    live = live_hermes_home()
    raw = os.environ.get("PATH") if path_value is None else path_value
    for entry in (raw or _DEFAULT_PATH).split(os.pathsep):
        if not entry or not os.path.isabs(entry) or is_within(entry, live):
            continue
        found = shutil.which(name, path=entry)
        if found and not is_within(found, live):
            return os.path.abspath(found)
    return None


def require_uv() -> str:
    """Absolute path of `uv`, or a `SafetyError` saying how to set it up. A `uv` inside (or
    linking into) `~/.hermes` is never used, and none is found through the scrubbed `PATH`."""
    found = find_executable("uv")
    if found is None:
        raise SafetyError(
            "refusing: `uv` was not found on PATH (entries inside or linking into ~/.hermes are "
            "ignored). Install uv (https://docs.astral.sh/uv/) into a directory on PATH that is "
            "not ~/.hermes, then rerun."
        )
    return found


def minimal_env(*, strict_path: bool = True) -> dict[str, str]:
    """The allowlisted essentials only: no HOME, no scratch. For probes that never need either
    (`python -I -S -c ...`)."""
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    env["PATH"] = sanitized_path(env.get("PATH"), strict=strict_path)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _scratch_env_paths(
    root: Path | str, hermes_home: Path | str | None
) -> tuple[Path, dict[str, Path], Path]:
    base = Path(os.path.abspath(root))
    dirs = {name: base / name for name in ENV_DIR_NAMES}
    hermes = Path(os.path.abspath(hermes_home)) if hermes_home is not None else base / "hermes_home"
    return base, dirs, hermes


def reset_scratch_env(root: Path | str, hermes_home: Path | str | None = None) -> None:
    """Delete the previous run's scratch environment under `root` -- HOME, the caches (uv's
    included), the XDG_* directories, TMPDIR, the bytecode prefix and `hermes_home` -- so a
    candidate run starts from empty directories and can never consume a stale bytecode file, cache
    entry or home left by an earlier run. Call it once, at the start of a run, before
    `scrubbed_env` (which only creates what is missing and is also called while a run's processes
    are alive).

    Only those named subdirectories are removed, each through `remove_private_tree` (it refuses
    symlinks, non-directories and anything not strictly inside `root`); the root itself and
    everything beside them (an extracted `src`, refs, the repository, listed-build data) is never
    touched. Every path is checked against the real home and `~/.hermes` before anything is
    deleted, and a symlinked root is refused."""
    base, dirs, hermes = _scratch_env_paths(root, hermes_home)
    doomed = [(f"scratch {name}", path) for name, path in dirs.items()]
    if hermes != base and is_within(hermes, base):  # a HERMES_HOME elsewhere is not ours to delete
        doomed.append(("HERMES_HOME", hermes))
    for what, path in [("scratch environment root", base), *doomed, ("HERMES_HOME", hermes)]:
        assert_outside_real_home(path, what)
        assert_not_live_hermes(path, what)
    if os.path.lexists(base):
        assert_leaf_not_symlink(base, "scratch environment root")
    for _what, path in doomed:
        remove_private_tree(path, base)


def scrubbed_env(
    root: Path | str, hermes_home: Path | str | None = None, *, strict_path: bool = True
) -> dict[str, str]:
    """The environment for every candidate subprocess. HOME, HERMES_HOME, XDG_*, TMPDIR and every
    cache point at private (0700) directories under `root`; nothing else is inherited except the
    allowlist. Every directory is checked against the real home before any is created. `PATH` is
    `sanitized_path(..., strict=strict_path)`; only the unchanged listed-build extraction passes
    `strict_path=False`."""
    base, dirs, hermes = _scratch_env_paths(root, hermes_home)
    checks = [("scratch environment root", base)]
    checks += [(f"scratch {name}", path) for name, path in dirs.items()]
    checks.append(("HERMES_HOME", hermes))
    for what, path in checks:  # validate everything before creating anything
        assert_outside_real_home(path, what)
        assert_not_live_hermes(path, what)
    for what, path in checks:
        ensure_private_dir(path, what)

    env = minimal_env(strict_path=strict_path)
    env["HOME"] = str(dirs["home"])
    env["HERMES_HOME"] = str(hermes)
    env["XDG_CACHE_HOME"] = str(dirs["cache"])
    env["XDG_CONFIG_HOME"] = str(dirs["config"])
    env["XDG_DATA_HOME"] = str(dirs["data"])
    env["XDG_STATE_HOME"] = str(dirs["state"])
    env["XDG_RUNTIME_DIR"] = str(dirs["runtime"])
    for var in ("TMPDIR", "TMP", "TEMP"):
        env[var] = str(dirs["tmp"])
    env["UV_CACHE_DIR"] = str(dirs["cache"] / "uv")
    env["UV_PYTHON_DOWNLOADS"] = "never"
    # Bytecode is written to scratch, never into the (verified) source tree, and a stale
    # in-tree `__pycache__` is never consulted.
    env["PYTHONPYCACHEPREFIX"] = str(dirs["pycache"])
    env.update(git_env_settings())
    return env


def git_env_settings() -> dict[str, str]:
    """`GIT_*` settings shared by our own git calls and by the candidate's environment."""
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }


# ---- git, hardened ----------------------------------------------------------------------------

# Global git options for every command we run against a clone we do not fully trust: no replace
# refs (they can swap any object), no optional locks (nothing may write into the clone, not even
# an index refresh), no fsmonitor (a config value that runs a command on `git status`), no hooks,
# and no transport at all (`protocol.allow=never`): every command here only reads the local object
# database, so nothing -- in particular a partial clone's lazy fetch of a missing blob through its
# promisor remote -- may reach the network or another repository. Signatures are never verified
# (`log.showSignature=false`: `git reflog show` would otherwise run a configured `gpg.program`).
_NO_PROTOCOL = "hmp-no-such-protocol"
GIT_HARDENING = (
    "--no-replace-objects",
    "--no-optional-locks",
    "-c", "core.fsmonitor=",
    "-c", f"core.hooksPath={os.devnull}",
    "-c", "protocol.allow=never",
    "-c", "log.showSignature=false",
)


def git_env() -> dict[str, str]:
    """A fresh git environment: NOTHING inherited except a sanitized PATH -- in particular no
    `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_CONFIG_*`,
    `GIT_EXEC_PATH`, `GIT_SSH_COMMAND` or `GIT_REPLACE_REF_BASE` -- and no HOME (so no user git
    config either)."""
    env = {
        "PATH": sanitized_path(os.environ.get("PATH")),
        "LC_ALL": "C",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_ATTR_NOSYSTEM": "1",
        # Never lazily fetch a missing object from a promisor remote (git >= 2.44 honours this;
        # `protocol.allow=never` above and the partial-clone refusal in `resolve_clone_git_dirs`
        # cover older git).
        "GIT_NO_LAZY_FETCH": "1",
        # Allow no transport whatever the clone's config says: a `protocol.file.allow=always` in
        # a partial clone's config cannot re-enable one if the partial-clone detection missed it
        # (this variable is consulted before any `protocol.*.allow` setting, and no protocol has
        # this name).
        "GIT_ALLOW_PROTOCOL": _NO_PROTOCOL,
    }
    env.update(git_env_settings())
    return env


def git_argv(clone: Path | str, *args: str) -> list[str]:
    return ["git", *GIT_HARDENING, "-C", str(clone), *args]


def run_git(clone: Path | str, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        git_argv(clone, *args),
        capture_output=True,
        text=text,
        check=False,
        env=git_env(),
    )


def resolve_clone_git_dirs(clone: Path | str) -> tuple[Path, Path]:
    """`(git dir, common dir)` of `clone`, both resolved, and proven not to lead into the live
    Hermes home -- through a symlinked clone, a `.git` pointer file, a `commondir`, an objects
    `alternates` entry (also through a whole chain of alternates) or a `core.worktree` -- and not
    to be a partial clone (`assert_not_partial_clone`). Raises `SafetyError` otherwise (fail
    closed)."""
    clone_path = Path(clone)
    assert_not_live_hermes(clone_path, "the Hermes clone", contains_ok=True)
    if not (clone_path / ".git").exists():
        raise SafetyError(f"refusing: no git clone at {clone_path}")
    proc = run_git(clone_path, "rev-parse", "--absolute-git-dir", "--git-common-dir")
    lines = proc.stdout.splitlines() if proc.returncode == 0 else []
    if len(lines) != 2:
        raise SafetyError(f"refusing: cannot resolve the git directory of {clone_path}")
    git_dir = Path(lines[0]).resolve()
    common = Path(lines[1])
    common = (common if common.is_absolute() else clone_path.resolve() / common).resolve()
    dirs = (("the clone's git directory", git_dir), ("its common git directory", common))
    for what, path in dirs:
        if not path.is_dir():
            raise SafetyError(f"refusing: {what} ({path}) is not a directory")
        assert_not_live_hermes(path, what, contains_ok=True)
    objects = common / "objects"
    assert_not_live_hermes(objects, "the object directory", contains_ok=True)
    _check_alternates(objects, {objects.resolve()}, 0)
    worktree = run_git(clone_path, "config", "--get", "core.worktree")
    if worktree.returncode == 0 and worktree.stdout.strip():
        target = Path(worktree.stdout.strip())
        target = target if target.is_absolute() else git_dir / target
        assert_not_live_hermes(target, "core.worktree", contains_ok=True)
    assert_not_partial_clone(clone_path, common)
    return git_dir, common


def assert_not_partial_clone(clone: Path | str, common_dir: Path | str) -> None:
    """Refuse a partial (blobless/treeless, "promisor") clone: in one, a missing object is fetched
    on demand from the promisor remote, so even `git cat-file` would reach the network. Refused
    when the effective config sets `extensions.partialClone`, marks any remote as a promisor or
    gives it a `partialclonefilter`, or when the object store holds any `*.promisor` pack (objects
    promised by a remote that may be missing locally). Reads config and lists files only; the
    config read itself runs with every transport and lazy fetching disabled."""
    proc = run_git(clone, "config", "--null", "--list", text=False)
    if proc.returncode != 0:
        raise SafetyError("refusing: cannot read the clone's git config")
    for record in proc.stdout.split(b"\0"):
        key, _, value = record.decode("utf-8", "replace").partition("\n")
        key = key.lower()
        section, _, name = key.rpartition(".")
        if key == "extensions.partialclone":
            raise SafetyError("refusing: the clone is a partial clone (extensions.partialClone)")
        disabled = value.strip().lower() in ("false", "no", "off", "0")
        if section.startswith("remote.") and (
            name == "partialclonefilter" or (name == "promisor" and not disabled)
        ):
            raise SafetyError(f"refusing: the clone has a promisor remote ({key})")
    pack_dir = Path(common_dir) / "objects" / "pack"
    try:
        promised = [n for n in os.listdir(pack_dir) if n.endswith(".promisor")]
    except FileNotFoundError:
        promised = []
    except OSError as exc:
        raise SafetyError("refusing: cannot list the clone's pack directory") from exc
    if promised:
        raise SafetyError("refusing: the clone holds promisor packs (a partial clone)")


def _check_alternates(objects_dir: Path, seen: set[Path], depth: int) -> None:
    """Every object directory an `alternates`/`http-alternates` file of `objects_dir` names -- and,
    recursively, every one THOSE name (git follows the chain) -- must stay out of the live Hermes
    home. Relative entries are relative to the objects directory that names them. A quoted entry
    (git's C-style quoting) cannot be checked reliably and is refused; so is a chain deeper than
    any sane repository has."""
    if depth > _MAX_ALTERNATES_DEPTH:
        raise SafetyError("refusing: the git alternates chain is too deep")
    for name in ("alternates", "http-alternates"):
        listing = objects_dir / "info" / name
        if not listing.is_file():
            continue
        try:
            lines = listing.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            raise SafetyError(f"refusing: cannot read a git {name} file") from exc
        for line in lines:
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            if entry.startswith('"'):
                raise SafetyError(f"refusing: a quoted git {name} entry cannot be checked")
            target = Path(entry)
            target = target if target.is_absolute() else objects_dir / target
            assert_not_live_hermes(target, f"a git {name} entry", contains_ok=True)
            resolved = target.resolve()
            if resolved not in seen:
                seen.add(resolved)
                _check_alternates(resolved, seen, depth + 1)


# ---- exact tree extraction and verification ---------------------------------------------------


@dataclass(frozen=True)
class TreeEntry:
    mode: str  # git mode: 100644 | 100755 | 120000 | 160000
    oid: str
    path: str  # relative, '/'-separated


def check_relative_path(path: str, what: str = "path") -> None:
    """A tracked/bridge path must be relative, normalized, and never touch `.git` or `.venv`."""
    if not path or "\0" in path or "\\" in path or path.startswith("/"):
        raise SafetyError(f"refusing: unsafe {what} {path!r}")
    parts = path.split("/")
    for part in parts:
        if part in ("", ".", "..") or part.lower() in (".git", VENV_DIRNAME):
            raise SafetyError(f"refusing: unsafe {what} {path!r}")


def list_commit_tree(clone: Path | str, commit: str) -> list[TreeEntry]:
    """Every file, symlink and gitlink of `commit`, straight from its tree object."""
    if not isinstance(commit, str) or FULL_SHA_RE.fullmatch(commit) is None:
        raise SafetyError("refusing: commit must be a full 40-character lowercase hex SHA")
    proc = run_git(clone, "ls-tree", "-r", "-z", "--full-tree", commit, text=False)
    if proc.returncode != 0:
        raise SafetyError("refusing: cannot list the commit's tree")
    entries: list[TreeEntry] = []
    seen: set[str] = set()
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        parts = meta.split(b" ")
        if len(parts) != 3:
            raise SafetyError("refusing: malformed tree entry")
        mode, kind, oid = (p.decode("ascii", "replace") for p in parts)
        if _TREE_KINDS.get(mode) != kind or FULL_SHA_RE.fullmatch(oid) is None:
            raise SafetyError(f"refusing: unsupported tree entry (mode {mode}, type {kind})")
        path = os.fsdecode(raw_path)
        check_relative_path(path, "tracked path")
        if path in seen:
            raise SafetyError("refusing: duplicate tree entry")
        seen.add(path)
        entries.append(TreeEntry(mode, oid, path))
    if not entries:
        raise SafetyError("refusing: the commit's tree is empty")
    return entries


class BlobReader:
    """Raw blobs from one `git cat-file --batch` process: no smudge filters, no `export-subst`,
    no end-of-line conversion -- exactly the bytes the object hashes to."""

    def __init__(self, clone: Path | str) -> None:
        self._proc = subprocess.Popen(
            git_argv(clone, "cat-file", "--batch"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=git_env(),
        )

    def __enter__(self) -> BlobReader:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._proc.stdin is not None:
            self._proc.stdin.close()
        if self._proc.stdout is not None:
            self._proc.stdout.close()
        self._proc.wait(timeout=30)

    def read(self, oid: str, limit: int | None = None) -> bytes:
        if FULL_SHA_RE.fullmatch(oid) is None:
            raise SafetyError("refusing: malformed object id")
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(oid.encode("ascii") + b"\n")
        self._proc.stdin.flush()
        header = self._proc.stdout.readline().split()
        if len(header) != 3 or header[0].decode("ascii", "replace") != oid or header[1] != b"blob":
            raise SafetyError("refusing: object is missing or not a blob")
        size = int(header[2])
        if limit is not None and size > limit:
            raise SafetyError("refusing: blob is unexpectedly large")
        data = self._proc.stdout.read(size)
        if len(data) != size or self._proc.stdout.read(1) != b"\n":
            raise SafetyError("refusing: truncated blob")
        return data


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _mkdirs_private(root: Path, rel_parent: str) -> None:
    current = root
    for part in [p for p in rel_parent.split("/") if p]:
        current = current / part
        if current.is_symlink():
            raise SafetyError("refusing: a directory in the source tree is a symlink")
        if not current.exists():
            os.mkdir(current, 0o700)


def write_tree_exact(clone: Path | str, commit: str, dest: Path | str) -> list[TreeEntry]:
    """Write the exact tree of `commit` into the (new or empty) directory `dest`: files 0600/0700
    from raw blobs, symlinks as recorded, gitlinks as empty directories. Returns the entries so
    the caller can verify. The clone is only read."""
    entries = list_commit_tree(clone, commit)
    root = Path(os.path.abspath(dest))
    ensure_private_dir(root, "source directory")
    if any(root.iterdir()):
        raise SafetyError(f"refusing: {root} is not empty")
    try:
        with BlobReader(clone) as reader:
            _write_entries(reader, entries, root)
    except (OSError, ValueError) as exc:  # a collision, a bad link target, a full disk ...
        raise SafetyError(f"refusing: cannot write the exact source tree: {exc}") from exc
    for entry in entries:
        if entry.mode == "120000":
            _assert_link_contained(root, root / entry.path)
    return entries


def _write_entries(reader: BlobReader, entries: Sequence[TreeEntry], root: Path) -> None:
    for entry in entries:
        if entry.mode in ("120000", "160000"):
            continue
        _mkdirs_private(root, entry.path.rpartition("/")[0])
        data = reader.read(entry.oid)
        mode = 0o700 if entry.mode == "100755" else 0o600
        fd = os.open(
            root / entry.path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            mode,
        )
        with os.fdopen(fd, "wb") as fh:
            if hasattr(os, "fchmod"):
                os.fchmod(fh.fileno(), mode)
            fh.write(data)
    for entry in entries:
        if entry.mode == "160000":
            _mkdirs_private(root, entry.path)
        elif entry.mode == "120000":
            _mkdirs_private(root, entry.path.rpartition("/")[0])
            link_target = reader.read(entry.oid, limit=4096).decode("utf-8", "strict")
            if not link_target or "\0" in link_target:
                raise SafetyError("refusing: unsafe symlink target")
            os.symlink(link_target, root / entry.path)


def _assert_link_contained(root: Path, link: Path) -> None:
    """A tracked symlink must resolve, physically and through any chain, inside the tree."""
    try:
        resolved = link.resolve()
    except (OSError, RuntimeError) as exc:  # loops
        raise SafetyError("refusing: a tracked symlink does not resolve") from exc
    if not is_within(resolved, root):
        raise SafetyError("refusing: a tracked symlink leaves the source tree")


def _file_problems(st: os.stat_result, rel: str) -> list[str]:
    problems = []
    if not _owned_by_me(st):
        problems.append(f"{rel}: not owned by the current user")
    if st.st_mode & 0o7000:
        problems.append(f"{rel}: setuid/setgid/sticky bit")
    if st.st_mode & 0o022:
        problems.append(f"{rel}: writable by group or others")
    return problems


def _hash_regular_file(path: Path) -> tuple[str, os.stat_result]:
    fd = os.open(path, READ_FLAGS)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise SafetyError("not a regular file")
        digest = hashlib.sha1(b"blob %d\0" % st.st_size, usedforsecurity=False)
        with os.fdopen(fd, "rb", closefd=False) as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest(), st
    finally:
        os.close(fd)


def verify_tree_matches_commit(src: Path | str, entries: Sequence[TreeEntry]) -> list[str]:
    """Prove the directory `src` is exactly the tracked tree `entries` (from `list_commit_tree`),
    plus only the known generated pieces: a top-level `.venv` (not descended into -- it is
    whatever `uv sync --locked` created) and top-level `*.egg-info` metadata directories with no
    code files. Every tracked file's blob id and exec bit, every tracked symlink's target,
    every directory and the absence of anything else are checked. Returns the (bounded) list of
    problems; empty means the tree is exactly the commit. Never follows a symlink."""
    root = Path(os.path.abspath(src))
    problems: list[str] = []

    def note(message: str) -> None:
        if len(problems) < _MAX_PROBLEMS:
            problems.append(message)

    try:
        root_st = root.lstat()
    except OSError:
        return ["source directory is not accessible"]
    if not stat.S_ISDIR(root_st.st_mode):
        return ["source directory is not a real directory (symlink or other file type)"]
    for message in _file_problems(root_st, "."):
        note(message)

    tracked = {e.path: e for e in entries}
    tracked_dirs: set[str] = set()
    for e in entries:
        parts = e.path.split("/")
        tracked_dirs.update("/".join(parts[:i]) for i in range(1, len(parts)))
    seen: set[str] = set()

    def walk(directory: Path, rel_dir: str) -> None:
        try:
            listing = sorted(os.scandir(directory), key=lambda d: d.name)
        except OSError:
            note(f"{rel_dir or '.'}: cannot list directory")
            return
        for dirent in listing:
            rel = f"{rel_dir}/{dirent.name}" if rel_dir else dirent.name
            try:
                st = dirent.stat(follow_symlinks=False)
            except OSError:
                note(f"{rel}: cannot stat")
                continue
            path = Path(dirent.path)
            entry = tracked.get(rel)
            if rel == VENV_DIRNAME and entry is None and not rel_dir:
                if not stat.S_ISDIR(st.st_mode) or not _owned_by_me(st):
                    note(f"{rel}: not a real directory owned by the current user")
                continue
            if entry is not None:
                seen.add(rel)
                check_entry(path, rel, st, entry)
            elif rel in tracked_dirs:
                if not stat.S_ISDIR(st.st_mode):
                    note(f"{rel}: expected a directory")
                    continue
                for message in _file_problems(st, rel):
                    note(message)
                walk(path, rel)
            elif not rel_dir and rel.endswith(".egg-info") and stat.S_ISDIR(st.st_mode):
                check_generated(path, rel)
            else:
                note(f"{rel}: untracked and not a known generated path")

    def check_entry(path: Path, rel: str, st: os.stat_result, entry: TreeEntry) -> None:
        if entry.mode == "160000":
            if not stat.S_ISDIR(st.st_mode) or os.listdir(path):
                note(f"{rel}: gitlink must be an empty directory")
            return
        if entry.mode == "120000":
            if not stat.S_ISLNK(st.st_mode):
                note(f"{rel}: expected a symlink")
                return
            try:
                target = os.readlink(path)
                if git_blob_id(os.fsencode(target)) != entry.oid:
                    note(f"{rel}: symlink target differs from the commit")
                _assert_link_contained(root, path)
            except (OSError, SafetyError):
                note(f"{rel}: symlink is unreadable or leaves the source tree")
            return
        if not stat.S_ISREG(st.st_mode):
            note(f"{rel}: expected a regular file")
            return
        for message in _file_problems(st, rel):
            note(message)
        if st.st_nlink != 1:
            note(f"{rel}: has multiple hard links")
        if bool(st.st_mode & 0o100) != (entry.mode == "100755"):
            note(f"{rel}: executable bit differs from the commit")
        try:
            blob_id, _ = _hash_regular_file(path)
        except (OSError, SafetyError):
            note(f"{rel}: unreadable")
            return
        if blob_id != entry.oid:
            note(f"{rel}: contents differ from the commit")

    def check_generated(directory: Path, rel_dir: str) -> None:
        for message in _file_problems(directory.lstat(), rel_dir):
            note(message)
        try:
            listing = sorted(os.scandir(directory), key=lambda d: d.name)
        except OSError:
            note(f"{rel_dir}: cannot list directory")
            return
        for dirent in listing:
            rel = f"{rel_dir}/{dirent.name}"
            st = dirent.stat(follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                check_generated(Path(dirent.path), rel)
            elif not stat.S_ISREG(st.st_mode):
                note(f"{rel}: generated metadata must be regular files")
            elif st.st_mode & 0o100 or Path(dirent.name).suffix.lower() in _GENERATED_CODE_SUFFIXES:
                note(f"{rel}: generated metadata contains code")
            else:
                for message in _file_problems(st, rel):
                    note(message)

    walk(root, "")
    for rel in sorted(set(tracked) - seen):
        note(f"{rel}: missing from the extracted tree")
    return problems


# ---- bridge-file copies -----------------------------------------------------------------------


def copy_regular_files(src_root: Path | str, rels: Iterable[str], dest_root: Path | str) -> None:
    """Copy exactly the files `rels` from `src_root` into a private `dest_root`, never following
    a symlink and never reading a `.venv`/`.git` path. Every directory on the way must be a real
    directory and every file a regular file (a FIFO, device, socket, directory or symlink is
    refused before it is opened). Files land 0600 in 0700 directories."""
    src = Path(os.path.abspath(src_root))
    dest = ensure_private_dir(dest_root, "SC-007 copy")
    for rel in rels:
        check_relative_path(rel, "bridge file")
        current = src
        parts = rel.split("/")
        for part in parts[:-1]:
            current = current / part
            st = current.lstat()
            if not stat.S_ISDIR(st.st_mode):
                raise SafetyError(f"refusing: {rel}: a parent is not a real directory")
        source = src / rel
        st = source.lstat()
        if not stat.S_ISREG(st.st_mode):
            raise SafetyError(f"refusing: {rel} is not a regular file")
        if st.st_size > MAX_BRIDGE_FILE_BYTES:
            raise SafetyError(f"refusing: {rel} is unexpectedly large")
        fd = os.open(source, READ_FLAGS)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_ino, opened.st_dev) != (
                st.st_ino, st.st_dev
            ):
                raise SafetyError(f"refusing: {rel} changed while being copied")
            with os.fdopen(fd, "rb", closefd=False) as fh:
                data = fh.read(MAX_BRIDGE_FILE_BYTES + 1)
        finally:
            os.close(fd)
        if len(data) > MAX_BRIDGE_FILE_BYTES:
            raise SafetyError(f"refusing: {rel} is unexpectedly large")
        target_dir = dest
        for part in parts[:-1]:
            target_dir = ensure_private_dir(target_dir / part, "SC-007 copy directory")
        write_private_file(target_dir / parts[-1], data)


# ---- layouts ----------------------------------------------------------------------------------


def validate_candidate_layout(
    *,
    repo_root: Path | str,
    builds_dir: Path | str,
    refs_dir: Path | str,
    out: Path | str | None = None,
    json_out: Path | str | None = None,
    interpreter: Path | str | None = None,
) -> Path | None:
    """Refuse every unsafe placement of the candidate's directories before anything is created:
    scratch/build dirs (or the derived `candidate` and `src` dirs) that are symlinks, that lie in
    or contain the real home, that overlap each other, the repository or the refs directory, a
    refs directory inside the live Hermes home, and a `--json-out` that is not a regular file (a
    symlink, or anything else, is refused; an existing regular file is later replaced by
    `write_private_file`) inside the scratch `--out`, in a directory that is not itself a symlink.
    With `interpreter` (`--candidate-interpreter`), it must pass `validate_base_interpreter` and
    neither it nor any symlink hop may lie in the builds, refs, scratch or repository directories
    (anything there is candidate- or harness-controlled); its real path is returned.
    The callers validate at the start of a run and again right before writing the report."""
    checks: list[tuple[str, Path | str]] = [("--builds-dir", builds_dir)]
    if out is not None:
        checks.append(("--out", out))
    for what, path in checks:
        assert_leaf_not_symlink(path, what)
        assert_outside_real_home(path, what)
        assert_not_live_hermes(path, what)
    assert_not_live_hermes(refs_dir, "--refs-dir", contains_ok=True)
    build_dir = Path(os.path.abspath(builds_dir)) / CANDIDATE_LABEL
    for what, path in (("the candidate build directory", build_dir),
                       ("the candidate source directory", build_dir / "src")):
        assert_leaf_not_symlink(path, what)
    if out is not None:
        scratch = Path(os.path.abspath(out)) / CANDIDATE_LABEL
        assert_leaf_not_symlink(scratch, "the scratch directory")
    disjoint: list[tuple[str, Path | str]] = [
        ("--builds-dir", builds_dir), ("--refs-dir", refs_dir), ("the repository", repo_root),
    ]
    if out is not None:
        disjoint.append(("--out", out))
    assert_disjoint(disjoint)
    if json_out is not None:
        if out is None:
            raise SafetyError("refusing: --json-out needs a scratch --out")
        target = Path(os.path.abspath(json_out))
        assert_leaf_not_symlink(target, "--json-out")
        assert_leaf_not_symlink(target.parent, "the --json-out directory")
        if target.resolve() == Path(out).resolve() or not is_within(target.parent, out):
            raise SafetyError(
                "refusing: --json-out must be a file inside the private scratch --out directory"
            )
        for what, other in (("the repository", repo_root), ("--refs-dir", refs_dir),
                            ("--builds-dir", builds_dir)):
            if overlaps(target, other):
                raise SafetyError(f"refusing: --json-out overlaps {what}")
        assert_outside_real_home(target, "--json-out")
        assert_not_live_hermes(target, "--json-out")
        if os.path.lexists(target) and not stat.S_ISREG(target.lstat().st_mode):
            raise SafetyError("refusing: --json-out exists and is not a regular file")
    if interpreter is None:
        return None
    final = validate_base_interpreter(interpreter, "--candidate-interpreter")
    for hop in [*link_chain(interpreter), str(final)]:
        for what, directory in disjoint:
            # A symlink planted inside a candidate-controlled directory can resolve outside it.
            # Check both the name exec would traverse and its resolved destination.
            # `is_within(hop, ...)` resolves a link to its destination, so the directory holding
            # the link is checked too: it may be spelled through an alias (/tmp for /private/tmp,
            # a symlinked parent) that the lexical check does not see.
            if (
                _lexically_within(hop, Path(os.path.abspath(directory)))
                or is_within(hop, directory)
                or is_within(os.path.dirname(hop), directory)
            ):
                raise SafetyError(f"refusing: --candidate-interpreter lies inside {what}")
    return final
