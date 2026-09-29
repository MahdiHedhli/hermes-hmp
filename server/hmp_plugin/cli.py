"""`hermes hmp …` operator CLI (server-modules.md "Operator CLI (F1 subset)"). T032.

Refusals and rules:
- **TTY and session (PR1-2, PR3-2).** Every mutating command refuses without an interactive TTY
  (stdin and stdout), and refuses when any `HERMES_SESSION_*` variable is set, which is how a Hermes
  agent's own shell looks. These are mitigations, not a boundary (SEC-1): same-user code can write
  the store directly.
- **Named profile (ID-2).** HMP's identity lives only under the default profile. Under a named
  profile every command that needs the store or the identity refuses (`NamedProfileError`).
- **Load-only identity.** The CLI never creates HMP state and never creates or re-keys the
  identity implicitly: it uses `identity.load_existing`, checked against a read-only view of the
  store before the store is opened. A clone, another host, another root or a missing identity
  refuses ("start the Hermes gateway with HMP once, then retry") and changes nothing. Only the
  gateway's adapter creates the identity. `instance rotate-key` (PR7-2) is the one explicit
  re-key, and it too requires the identity to be current here first.
- **`pair offer` (PR1-1..PR1-4).**
  - It is refused on a build that is not read-compatible (GU-2c; the same gate as the listener).
  - `ep` comes only from the running listener's actual bind (PR1-4). The adapter writes that bind to
    a runtime record next to the store, mode 0600, atomically, and removes it when the listener
    stops. The command refuses when the record is missing, unsafe, stale (its process is gone) or
    for another instance key.
  - `S` is rendered once, inside a QR code, only to the TTY. It is never printed as text, logged or
    stored; only `secret_hash("HMP1-OFFER", S)` is stored.
  - The QR renderer must be importable **before** anything is minted.
  - **One-command flow (owner requirement, 2026-09-27; compare-and-confirm per OD-F7,
    2026-09-27).** After the QR, unless `--no-wait`, the command stays running and walks the
    operator through the rest: it polls the store (the same read path as `pair list`) for a
    request against this offer's own `oid`, prints the sanitized device name once one arrives,
    then shows the code this pairing expects -- the same value `_sas_of` computes for `pair list`
    and `pair confirm` -- large and clearly, and asks "Does the phone show this code? [y/N]". `y`
    confirms through the same activation internals `pair confirm` uses (`_do_confirm`); `n` (or
    anything else that is not `y`/`yes`, including a blank line) runs the same `_cmd_deny` used by
    `pair deny`. This **replaces** typing the full 20-character SAS in the interactive flow
    (OD-F7): the operator's own visual compare against the phone's screen is what HMP_V1 PR4-2's
    "confirmation" now means here, not a machine string-compare of operator input against a value
    the operator never sees independently -- see `reviews/security.md`'s addendum for the
    documented rubber-stamp risk this accepts. `pair confirm --sas <SAS>` is unchanged: the
    typed-SAS constant-time compare, durable mismatch counter and burn limit stay exactly as they
    were for that non-interactive and scripted path. Every stopping point (offer expiry, the
    pairing's own `confirm_by`, Ctrl-C) prints what changed and how to resume with the old
    two-step commands (`pair list` / `pair confirm` / `pair deny`); Ctrl-C never leaves the store
    in a half-mutated state, since it can only land between whole read/write operations the
    confirm/deny paths already make atomic. `--no-wait` keeps the original print-and-exit behavior
    for scripts.
  - **In-terminal bot access (OD-F8, 2026-09-27).** Right after "Paired ✓", unless `--no-grant`,
    the same run asks the operator to allow the phone to use the served bots: it lists them (from
    the listener record's `profiles`, written by the adapter from the bridge's own
    `served_profiles()` -- S1 forbids this CLI from asking Hermes directly), asks
    "Allow ⟨label⟩ to use all of these? [Y/n/pick]", then waits up to `BOT_GRANT_WAIT_S`,
    polling `hermes -p <profile> pairing list` for this user's own pending `hmp` requests
    (the app auto-sends P6 `authorize` right after pairing, HMP_V1 PR6-1) and approving each with
    `hermes -p <profile> pairing approve hmp <request_id>` -- Hermes's own public CLI, run as a
    subprocess (`_default_run_hermes_cli`; S1 forbids importing `gateway.pairing` from this
    process). This reverses the earlier rule that the plugin never creates bot grants: it still
    never writes Hermes's approved-users files itself, and it only ever approves a *pending
    request* that already carries this pairing's own `user_id` -- the same public
    `pairing approve` an operator would type by hand. A record from an older gateway with no
    `profiles` field, or every bot declined, falls back to the placeholder next-steps text
    (`_print_next_steps`), as before this requirement.
- **`pair list` (PR3-1).** It shows at most the first SAS group. The device-claimed name is quoted
  and labelled unverified.
- **`pair confirm` (PR3-2..PR3-4).**
  - The SAS is compared in constant time. Each mismatch is counted durably, and the
    `SAS_MAX_MISMATCHES`-th one denies the pairing. The expected SAS is never printed.
  - `--new-user` is the default.
  - `--user` must have the `hmpu_` format, must exist, and must equal the offer's intended user.
    First it prints that user's devices, the bots HMP has asked access to, and instance-wide env
    allowlist membership. Only then does it proceed, and only with `--yes-share`.
  - Activation goes through `pairing.confirm_pairing`, which re-checks `PENDING` in the same
    transaction (PR3-4). Denial goes through `pairing.deny_pairing`.
- **`devices revoke` (PR7-1)** revokes the device and every token family atomically. For a user's
  last device it prints the Hermes `pairing revoke` commands, and never runs them.
- **`instance rotate-key` (PR7-2)** makes a new key, revokes every device, and expires every open
  offer and pending pairing.
- **`compat`** prints the build identity, the list match and the probe outcome. There are no
  secrets in any of them.

Grants that live in Hermes's own pairing stores cannot be read without a Hermes internal, and
only `bridge.py` may import one (PR-2). So the "grants" the CLI prints are the bots this user asked
access to through HMP (their `chats` rows), with the Hermes command that shows the real state
(`HERMES_API_GAP`, E-GAP-31).

Importing this module imports only the standard library. It runs inside every `hermes` CLI start,
and the adapter uses its listener-record helpers.
"""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import os
import re
import secrets
import shlex
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TextIO

SUBCOMMAND_DEST = "hmp_command"

# (group, action) pairs that mutate state: TTY + HERMES_SESSION_* refusals apply.
MUTATING_COMMANDS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("pair", "offer"),
        ("pair", "confirm"),
        ("pair", "deny"),
        ("devices", "revoke"),
        ("instance", "rotate-key"),
    }
)

SESSION_ENV_PREFIX = "HERMES_SESSION_"
USER_ID_RE = re.compile(r"hmpu_[0-9a-f]{32}")
OPERATOR_LABEL_MAX_BYTES = 64
_DROPPED_LABEL_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp", "Co", "Cn"})
INSTANCE_WIDE_ALLOWLIST_ENVS: tuple[str, ...] = ("GATEWAY_ALLOWED_USERS", "HMP_ALLOWED_USERS")

NOT_READY = (
    "refused: there is no current HMP instance identity here; "
    "start the Hermes gateway with HMP once, then retry"
)

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_ENVIRONMENT = 2
EXIT_INTERRUPTED = 130  # Ctrl-C during `pair offer`'s interactive wait/confirm (128 + SIGINT)

# `pair offer`'s interactive wait: how often it polls the store for the P2 claim against this
# offer's own `oid` (PR2-5).
OFFER_POLL_INTERVAL_S = 1.0

# OD-F8 (2026-09-27): after "Paired ✓", how long the one-command flow waits for the phone's P6
# authorize requests to show up in Hermes's own `pairing list`, and how often it polls for them.
BOT_GRANT_WAIT_S = 90
BOT_GRANT_POLL_INTERVAL_S = 2.0

# OD-F8: the one subprocess entry point into Hermes's own public CLI, always given this timeout.
HERMES_CLI_TIMEOUT_S = 5.0

# Mirrors `hermes_cli.main._PROFILE_NAME_RE` / `hermes_cli.profiles._PROFILE_ID_RE` exactly (SR-1
# pattern: this CLI runs in a separate process and may not import Hermes, S1, so the rule is
# reproduced rather than imported). A served profile name that does not match this is dropped
# before it ever reaches a `-p <profile>` argv or an f-string shell command (OD-F8).
_PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# --------------------------------------------------------------------------------------------------
# PR1-4: the listener's runtime record (written by the adapter, read by `pair offer`)
# --------------------------------------------------------------------------------------------------

LISTENER_RECORD_FILENAME = "listener.json"
LISTENER_RECORD_FORMAT = 1
RECORD_MODE = 0o600
MAX_RECORD_BYTES = 4_096  # generous bound for a small, fixed-shape JSON record


class ListenerRecordError(RuntimeError):
    """The runtime record is missing, unsafe, stale or for another key. The text is fixed."""


@dataclass(frozen=True)
class ListenerRecord:
    host: str
    port: int
    iid: str
    pid: int
    nonce: str
    # OD-F8 (2026-09-27): the profiles this instance serves, `(profile, display_name)`, so
    # `pair offer`'s one-command flow can list bots by name without importing Hermes (S1). `None`
    # on a record written by an older gateway that never had this field -- the caller then falls
    # back to the generic placeholder next-steps text, as before this field existed.
    profiles: tuple[tuple[str, str], ...] | None = None


def listener_record_path(anchor_dir: Path) -> Path:
    """Next to the HMP store (`server.store_path`), inside the default profile's plugin data."""
    return Path(anchor_dir).parent / LISTENER_RECORD_FILENAME


def write_listener_record(
    path: Path,
    *,
    host: str,
    port: int,
    iid: str,
    nonce: str | None = None,
    profiles: Sequence[tuple[str, str]] | None = None,
) -> None:
    """Atomically write the record: a new 0600 temp file in the same directory, fsync, rename.

    `nonce` (SR-7): a fresh value per listener start, generated here when the caller does not
    supply one. It is part of what `read_listener_record` reads back and treats as opaque (never
    compared across CLI invocations, which are stateless); its role is to make each incarnation
    of the record distinguishable, and it is folded into `remove_listener_record`'s race-safety
    check alongside the inode compare.

    `profiles` (OD-F8, 2026-09-27): the served `(profile, display_name)` pairs, from the bridge's
    `served_profiles()` and the same display-name rule the roster uses
    (`reads._fallback_display_name`). The adapter passes this only when the build is SUPPORTED (it
    has a bridge); omitted (`None`) otherwise, so an unsupported-build listener's record looks
    exactly as it did before this field existed.
    """
    body = json.dumps(
        {
            "format": LISTENER_RECORD_FORMAT,
            "host": host,
            "port": port,
            "iid": iid,
            "pid": os.getpid(),
            "nonce": nonce if nonce is not None else secrets.token_hex(16),
            "profiles": [[p, d] for p, d in profiles] if profiles is not None else None,
        }
    ).encode("utf-8")
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, RECORD_MODE)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, RECORD_MODE)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _read_fd(fd: int, *, limit: int = MAX_RECORD_BYTES) -> bytes | None:
    """Every byte from `fd` (already `O_NOFOLLOW`-opened), or `None` if it exceeds `limit`."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(fd, 65_536)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _check_listener_dir_safety(parent: Path) -> None:
    """SR-7: the record's directory itself must be owned by this user and not group- or
    world-writable, so the `O_NOFOLLOW` open below is opening a file this user's own writes
    control, not one a same-directory-writable attacker could have swapped in."""
    try:
        st = os.lstat(parent)
    except FileNotFoundError as exc:
        raise ListenerRecordError("the HMP listener is not running") from exc
    except OSError as exc:
        raise ListenerRecordError("the listener record directory is unsafe") from exc
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise ListenerRecordError("the listener record directory is unsafe")
    if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ListenerRecordError("the listener record directory is unsafe")


def remove_listener_record(path: Path) -> None:
    """Remove the record if this process wrote it (a record of another process is left alone).

    SR-7 race safety: the pid is read from an `O_NOFOLLOW`-opened descriptor (`fstat`, never a
    second, path-based read that could see a different file than the one just checked), and the
    descriptor's `(st_dev, st_ino)` is compared against a fresh `lstat` of the path again,
    immediately before unlinking -- closing most of the window in which a fresh writer's
    `os.replace` (PR1-4's own atomic record write) could otherwise make this process delete the
    NEW record instead of nothing.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return
        raw = _read_fd(fd)
    finally:
        os.close(fd)
    if raw is None:
        return
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return
    if not (isinstance(data, dict) and data.get("pid") == os.getpid()):
        return
    with contextlib.suppress(OSError):
        current = os.lstat(path)
        if (current.st_dev, current.st_ino) == (st.st_dev, st.st_ino):
            os.unlink(path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # another OS user's process: not our listener
        return False
    return True


# --------------------------------------------------------------------------------------------------
# OD-F8 (2026-09-27): the one subprocess entry point into Hermes's own public CLI. S1 restricts
# Hermes imports to `bridge.py`, and this process is `hermes hmp` itself, a separate `hermes`
# invocation from the one that would hold any pending request -- so the only way to list and
# approve this user's pending `hmp` requests is `hermes -p <profile> pairing list` /
# `pairing approve`, run exactly as the operator would type them: a fixed argv list, never
# `shell=True`, no string interpolation into a shell command line anywhere in this module. Kept in
# these two small functions so the security-scan finding they add has one exact location
# (`LIVE_LOCAL_PAIRING.md` "known findings").
#
# **Resolution (SHOULD-FIX, independent review of OD-F8).** The basename check on `sys.argv[0]`
# never actually fired: the real installed launcher (`~/.hermes/hermes-agent/.hermes/bin/hermes`,
# read at review time -- not imported here, SR-1) is a `sh` script that execs
# `<store python> -I -c '<bootstrap>' "$@"`, so by the time `hermes_cli.main.main()` (and this
# plugin) runs, `sys.argv[0]` is `"-c"`, not `"hermes"`. Every real invocation therefore fell
# straight through to `shutil.which("hermes")`, an ambient `$PATH` lookup, with the child then
# inheriting this whole process's environment. Investigating that launcher also showed there is no
# bare `python -m hermes_cli.main` supported entry: the bootstrap first inserts the installation's
# own directory onto `sys.path`, sets `HERMES_HOME`, and imports `hermes_bootstrap` (dependency
# generation selection) before ever importing `hermes_cli.main` -- reconstructing that here would
# both duplicate it (SR-1 disfavors reproducing anything but a small constant/pattern) and risk
# silently diverging from it. `_repo_root_from_sys_path` instead reads a fact already true of PR-2's
# own process: `hermes hmp ...` only ever runs as a plugin subcommand dispatched from inside
# `hermes_cli.main`, so this interpreter's `sys.path` already carries the exact directory that
# launcher inserted for its own installation. `<that directory>/.hermes/bin/hermes` is the
# convention this installed launcher was found at (mirrors `hermes_cli._launchers`'s own
# `installation_command`, again read, not imported); running it is running "the exact launcher
# that started this process," evidenced by this process's own already-resolved state rather than
# trusted from an ambient, attacker-adjustable `$PATH`. A standard console-script sibling of this
# interpreter (`sys.executable`'s own directory, the shape a `pip`/venv install of `hermes_cli`
# produces) is tried next, still with no `$PATH` lookup. `shutil.which("hermes")` is the last
# resort, and the only one of the three that even looks at `$PATH`. Every candidate, from every
# tier, passes through `_is_safe_executable` before it is ever accepted: an absolute path outside
# the current working directory, a regular file (never a symlink -- `lstat`, not `stat`), owned by
# this OS user or root, and not group- or world-writable. None of this is a trust boundary by
# itself (SEC-1: a same-user attacker who can plant such a file could usually also just edit this
# module), but it closes the specific hole the review named: a lower-privileged or path-order
# attacker's file on `$PATH`, or a relative/cwd-local one, silently standing in for Hermes's own
# CLI.
# --------------------------------------------------------------------------------------------------


def _repo_root_from_sys_path() -> Path | None:
    """Stdlib-only, no Hermes import (the module docstring's invariant): the `sys.path` entry, if
    any, that this process's own `hermes` launcher inserted for its installation -- identified
    purely by filesystem evidence (it contains `hermes_cli/main.py`), never by importing it. `hermes
    hmp ...` (this file) only ever runs as a plugin subcommand of `hermes_cli.main`, so when this
    process is a real `hermes` invocation such an entry is already on `sys.path` before this
    function is ever called; a test harness or an unusual embedding that lacks one gets `None`."""
    for entry in sys.path:
        if not entry:
            continue
        try:
            candidate = Path(entry)
            if (candidate / "hermes_cli" / "main.py").is_file():
                return candidate.resolve()
        except OSError:
            continue
    return None


def _is_safe_executable(path: Path, *, cwd: Path) -> bool:
    """Hardened acceptance for any path this module is about to exec as `hermes`, whichever of the
    three resolution tiers found it: absolute (never a bare name resolved by the shell), not
    inside the current working directory (a relative `$PATH` entry, or `.` on it, could otherwise
    point an attacker-writable file here), a regular file found by `lstat` -- never a symlink,
    which could point anywhere after this check ran -- owned by this OS user or root, and not
    group- or world-writable."""
    if not path.is_absolute():
        return False
    try:
        path.relative_to(cwd)
    except ValueError:
        pass
    else:
        return False
    try:
        st = path.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(st.st_mode):
        return False
    if st.st_uid not in (os.getuid(), 0):
        return False
    return not st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)


def _default_resolve_hermes_executable() -> str | None:
    """The `hermes` entry point to invoke, in the order documented above. `None` when nothing safe
    resolves -- the caller then falls back to printing the manual commands rather than guessing a
    path."""
    cwd = Path.cwd()
    candidates: list[Path] = []
    repo_root = _repo_root_from_sys_path()
    if repo_root is not None:
        candidates.append(repo_root / ".hermes" / "bin" / "hermes")
    with contextlib.suppress(OSError):
        candidates.append(Path(sys.executable).resolve().parent / "hermes")
    for candidate in candidates:
        if _is_safe_executable(candidate, cwd=cwd):
            return str(candidate)
    which = shutil.which("hermes")
    if which is not None:
        candidate = Path(which)
        if _is_safe_executable(candidate, cwd=cwd):
            return str(candidate)
    return None


# The minimal environment forwarded to the `hermes` subprocess (SHOULD-FIX, independent review of
# OD-F8): never the full parent environment. `PATH` so the launcher script's own `#!/bin/sh` shebang
# and its internal `python3` resolution work; `HOME` because Hermes's own config/data path
# resolution and the interpreter's user-site paths key off it; `HERMES_HOME`, only when the
# operator's own shell already set it, so a non-default Hermes root is honored, matching what the
# operator's own interactive `hermes` invocation would see; `LANG`/`LC_*` so the child's text
# (which this module decodes with `text=True`) is encoded the way the operator's terminal expects;
# `TMPDIR` because some installs stage temporary files at startup. Nothing else: no ambient proxy
# config, no debug/tracing vars, no unrelated secrets that happened to be in this operator's shell.
_ENV_ALLOWLIST_EXACT: tuple[str, ...] = ("PATH", "HOME", "HERMES_HOME", "TMPDIR", "LANG")
_ENV_ALLOWLIST_PREFIXES: tuple[str, ...] = ("LC_",)


def _minimal_hermes_env(environ: Mapping[str, str]) -> dict[str, str]:
    """The allow-listed subset of `environ` passed to the `hermes` subprocess. Order-independent,
    case-sensitive (env var names are case-sensitive on every platform this runs on)."""
    out = {name: environ[name] for name in _ENV_ALLOWLIST_EXACT if name in environ}
    for name, value in environ.items():
        if name in out:
            continue
        if any(name.startswith(prefix) for prefix in _ENV_ALLOWLIST_PREFIXES):
            out[name] = value
    return out


def _default_run_hermes_cli(
    exe: str, argv: list[str], *, timeout: float, environ: Mapping[str, str]
) -> subprocess.CompletedProcess[str] | None:
    """THE subprocess call (there is exactly one `subprocess.run` in this module). Fixed argv
    list, `shell=False` (the default, never passed as True), a tight timeout, and an allow-listed
    environment (`_minimal_hermes_env`) -- never the full parent environment. `None` on any failure
    to start, a non-zero-length stderr is not treated specially -- the caller reads `returncode` --
    and on timeout: the caller treats that the same as "nothing happened yet" and keeps polling or
    reports it, never raises out of the interactive flow."""
    try:
        return subprocess.run(  # noqa: S603 - fixed argv, shell=False, no untrusted interpolation
            [exe, *argv],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_minimal_hermes_env(environ),
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _valid_profile_name(name: str) -> bool:
    """Mirrors Hermes's own profile-name rule (`_PROFILE_NAME_RE`)."""
    return isinstance(name, str) and _PROFILE_NAME_RE.fullmatch(name) is not None


def read_listener_record(
    path: Path, *, iid: str, pid_alive: Callable[[int], bool] = _pid_alive
) -> ListenerRecord:
    """The record, checked: its directory is safe (`_check_listener_dir_safety`), the record
    itself is a regular file owned by this user with mode 0600 -- checked by `fstat` on the
    descriptor `O_NOFOLLOW` opened it with, never a second, path-based read that could see a
    different file (SR-7) -- well-formed, for `iid`, and written by a process that is still
    running."""
    _check_listener_dir_safety(path.parent)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as exc:
        raise ListenerRecordError("the HMP listener is not running") from exc
    except OSError as exc:  # ELOOP (a symlink) or another open-time fault
        raise ListenerRecordError("the listener record is unsafe") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ListenerRecordError("the listener record is not a regular file")
        if stat.S_IMODE(st.st_mode) != RECORD_MODE or st.st_uid != os.getuid():
            raise ListenerRecordError("the listener record has unsafe ownership or permissions")
        raw = _read_fd(fd)
    finally:
        os.close(fd)
    if raw is None:
        raise ListenerRecordError("the listener record is malformed")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ListenerRecordError("the listener record is unreadable") from exc
    if not isinstance(data, dict) or data.get("format") != LISTENER_RECORD_FORMAT:
        raise ListenerRecordError("the listener record is malformed")
    host, port, rec_iid, pid = data.get("host"), data.get("port"), data.get("iid"), data.get("pid")
    nonce = data.get("nonce")
    try:
        ipaddress.ip_address(host)  # type: ignore[arg-type]
    except ValueError as exc:
        raise ListenerRecordError("the listener record is malformed") from exc
    for value, lo, hi in ((port, 1, 65_535), (pid, 1, 2**31)):
        if type(value) is not int or not lo <= value <= hi:
            raise ListenerRecordError("the listener record is malformed")
    if not isinstance(rec_iid, str):
        raise ListenerRecordError("the listener record is malformed")
    if not isinstance(nonce, str) or not nonce:
        raise ListenerRecordError("the listener record is malformed")
    if rec_iid != iid:
        raise ListenerRecordError("the listener record is for another instance key")
    if not pid_alive(pid):  # type: ignore[arg-type]
        raise ListenerRecordError("the listener record is stale")
    profiles = _parse_record_profiles(data.get("profiles"))
    return ListenerRecord(
        host=str(host),
        port=int(port),
        iid=rec_iid,  # type: ignore[arg-type]
        pid=int(pid),  # type: ignore[arg-type]
        nonce=nonce,
        profiles=profiles,
    )


def _parse_record_profiles(raw: object) -> tuple[tuple[str, str], ...] | None:
    """OD-F8: `None` when the field is absent or explicitly `null` (an older gateway, or an
    unsupported build that has no bridge to enumerate profiles from) -- tolerated, not an error.
    Present but malformed is a malformed record (fails closed the same as every other field)."""
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ListenerRecordError("the listener record is malformed")
    out: list[tuple[str, str]] = []
    for entry in raw:
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or not all(isinstance(v, str) and v for v in entry)
        ):
            raise ListenerRecordError("the listener record is malformed")
        out.append((entry[0], entry[1]))
    return tuple(out)


def _default_verify_listener_live(
    record: ListenerRecord, iid: str, *, timeout: float = 2.0
) -> bool:
    """SR-7: a live, TLS-pinned confirmation that the record's endpoint is actually this
    instance's own listener right now, not a stale record whose pid was reused by an unrelated
    process (`pid_alive(pid)` alone cannot tell those apart: any same-user process with that pid
    passes it). The TLS pin equals `iid` in this system (both are the certificate's SPKI
    fingerprint), so the handshake itself is already an identity check; the `/ready` body's own
    `iid` is checked too, as a second, protocol-level confirmation. Any failure -- refused
    connection, TLS/pin mismatch, timeout, or a malformed or mismatched response -- answers False
    (fail closed): `pair offer` then refuses rather than minting a QR for a dead or wrong
    endpoint. Display/diagnostic use only (PR0-1): never trust `/ready` beyond this check."""
    import http.client
    import ssl as _ssl

    from . import crypto
    from .contract import PATH_PREFIX
    from .identity import new_stdlib_ssl_context, set_ssl_context_attr

    # The pin is the only trust here. The context is the standard library's own class, so a host's
    # process-wide client-trust injection (e.g. truststore) cannot add a platform-trust evaluation
    # of the self-signed instance certificate, which fails and would make this check always False.
    ctx = new_stdlib_ssl_context(_ssl.PROTOCOL_TLS_CLIENT)
    set_ssl_context_attr(ctx, "check_hostname", False)
    set_ssl_context_attr(ctx, "verify_mode", _ssl.CERT_NONE)
    conn = http.client.HTTPSConnection(record.host, record.port, timeout=timeout, context=ctx)
    try:
        conn.connect()
        sock = conn.sock
        peer = sock.getpeercert(binary_form=True) if sock is not None else None  # type: ignore[union-attr]
        if peer is None or crypto.spki_fingerprint(crypto.certificate_spki(peer)) != iid:
            return False
        conn.request("GET", PATH_PREFIX + "/ready")
        resp = conn.getresponse()
        if resp.status != 200:
            return False
        raw = resp.read(MAX_RECORD_BYTES)
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, _ssl.SSLError, ValueError, AttributeError):
        return False
    finally:
        conn.close()
    return isinstance(payload, dict) and payload.get("iid") == iid


def endpoint_for(host: str, port: int) -> str:
    """`https://<bound address>:<port>` (PR1-3, PR1-4). IPv6 literals are bracketed."""
    addr = ipaddress.ip_address(host)
    literal = f"[{addr.compressed}]" if addr.version == 6 else addr.compressed
    return f"https://{literal}:{port}"


# --------------------------------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------------------------------


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """`setup_fn` for `register_cli_command`: builds `hermes hmp …`."""
    groups = parser.add_subparsers(dest=SUBCOMMAND_DEST)

    pair = groups.add_parser("pair", help="Pairing offers and confirmations").add_subparsers(
        dest="pair_command"
    )
    offer = pair.add_parser("offer", help="Create a single-use pairing offer (PR1-1)")
    offer.add_argument("--label")
    offer.add_argument("--user")
    offer.add_argument(
        "--no-wait",
        action="store_true",
        help="Print the QR and exit (old behavior); do not wait for a scan or prompt for a code.",
    )
    offer.add_argument(
        "--no-grant",
        action="store_true",
        help=(
            "Skip the after-pairing prompt that offers to allow the phone's bots (OD-F8); print "
            "the manual next steps instead. Has no effect with --no-wait."
        ),
    )
    pair.add_parser("list", help="List pending pairings (PR3-1)")
    confirm = pair.add_parser("confirm", help="Confirm a pairing by its SAS (PR3-2)")
    confirm.add_argument("pairing_id")
    confirm.add_argument("--sas", required=True)
    confirm.add_argument("--label", required=True)
    who = confirm.add_mutually_exclusive_group()
    who.add_argument("--new-user", action="store_true")
    who.add_argument("--user")
    confirm.add_argument("--yes-share", action="store_true")
    deny = pair.add_parser("deny", help="Deny a pairing")
    deny.add_argument("pairing_id")

    devices = groups.add_parser("devices", help="Enrolled devices").add_subparsers(
        dest="devices_command"
    )
    devices.add_parser("list", help="List devices")
    revoke = devices.add_parser("revoke", help="Revoke a device and its tokens (PR7-1)")
    revoke.add_argument("device_id")

    instance = groups.add_parser("instance", help="Instance identity").add_subparsers(
        dest="instance_command"
    )
    instance.add_parser("show", help="Show the instance fingerprint")
    instance.add_parser("rotate-key", help="Rotate the instance key; revokes every device (PR7-2)")

    groups.add_parser("compat", help="Show build identity, list match and probe result (GU-2c)")


# --------------------------------------------------------------------------------------------------
# Environment (injectable for tests)
# --------------------------------------------------------------------------------------------------


def _default_compat() -> Any:
    from . import compat

    try:
        return compat.default_gate().evaluate()
    except Exception:  # the gate fails closed on its own; this guards its loader
        return compat.CompatResult(compat.CompatStatus.UNSUPPORTED)


def _default_qr_factory() -> Any:
    """The QR renderer. An ImportError here refuses the offer before anything is minted."""
    import qrcode

    return qrcode


@dataclass
class CliEnv:
    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    stdin: TextIO = field(default_factory=lambda: sys.stdin)
    stdout: TextIO = field(default_factory=lambda: sys.stdout)
    stderr: TextIO = field(default_factory=lambda: sys.stderr)
    clock: Callable[[], int] = field(default=lambda: int(time.time()))
    compat: Callable[[], Any] = _default_compat
    qr_factory: Callable[[], Any] = _default_qr_factory
    pid_alive: Callable[[int], bool] = _pid_alive
    # `pair offer`'s interactive wait loop: injectable so tests never sleep for real. Tests also use
    # it to raise `KeyboardInterrupt` mid-poll to simulate Ctrl-C.
    sleep: Callable[[float], None] = time.sleep
    # SR-7: `pair offer`'s live, TLS-pinned liveness/identity check of the listener record's
    # endpoint (`_default_verify_listener_live`), injectable for tests.
    verify_listener_live: Callable[[ListenerRecord, str], bool] = _default_verify_listener_live
    # `identity.resolve_custody` / `load_existing` / `rotate_key` keyword arguments (tests only).
    identity_kwargs: dict[str, Any] = field(default_factory=dict)
    # OD-F8: resolves the `hermes` executable, and the one subprocess call into it. Both
    # injectable so a unit test never spawns a real process -- a FAKE runner stands in.
    hermes_executable: Callable[[], str | None] = _default_resolve_hermes_executable
    run_hermes_cli: Callable[..., subprocess.CompletedProcess[str] | None] = _default_run_hermes_cli

    def interactive(self) -> bool:
        try:
            return bool(self.stdin.isatty() and self.stdout.isatty())
        except (AttributeError, ValueError):
            return False


class RefusedError(Exception):
    def __init__(self, message: str, code: int = EXIT_REFUSED) -> None:
        super().__init__(message)
        self.code = code


def _command(args: argparse.Namespace) -> tuple[str | None, str | None]:
    group = getattr(args, SUBCOMMAND_DEST, None)
    action = getattr(args, f"{group}_command", None) if group else None
    return group, action


def _check_mutation_allowed(env: CliEnv) -> None:
    """PR1-2 / PR3-2 mitigations (SEC-1)."""
    if any(name.startswith(SESSION_ENV_PREFIX) for name in env.environ):
        raise RefusedError("refused: run this from an operator shell, not a Hermes session")
    if not env.interactive():
        raise RefusedError("refused: this command needs an interactive terminal")


@dataclass
class _Context:
    env: CliEnv
    custody: Any
    store: Any

    @property
    def out(self) -> TextIO:
        return self.env.stdout

    def now(self) -> int:
        return int(self.env.clock())


class _ReadOnlyEpoch:
    """The store's revocation epoch, read through a read-only SQLite connection, so the CLI can
    check the identity before it opens the store for writing."""

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()

    def _read(self, query: str) -> int:
        uri = self._path.as_uri() + f"?{query}"
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute("SELECT store_revocation_epoch FROM meta WHERE id = 1").fetchone()
        finally:
            conn.close()
        return int(row[0]) if row else 0

    def revocation_epoch(self) -> int:
        # Without a WAL file the database is fully checkpointed, and even a `mode=ro` open
        # would create the WAL side files, so read it as immutable. With one (the gateway has
        # the store open), a read-only connection sees the committed WAL content.
        if not self._path.with_name(self._path.name + "-wal").exists():
            return self._read("mode=ro&immutable=1")
        return self._read("mode=ro")


@contextlib.contextmanager
def _open(env: CliEnv, *, needs_identity: bool = False) -> Any:
    from . import identity, server
    from .store import Store

    kw = env.identity_kwargs
    try:
        custody = identity.resolve_custody(
            env=kw.get("env", env.environ),
            hermes_root=kw.get("hermes_root"),
            binding_root=kw.get("binding_root"),
        )
    except identity.NamedProfileError as exc:  # ID-2
        raise RefusedError(
            "refused: HMP runs only under the default profile; run this without -p/--profile",
            EXIT_ENVIRONMENT,
        ) from exc
    except identity.IdentityError as exc:
        raise RefusedError("refused: the HMP custody location is unsafe", EXIT_ENVIRONMENT) from exc
    path = server.store_path(custody.anchor_dir)
    if not path.is_file():  # the CLI never creates HMP state; the gateway does
        raise RefusedError(NOT_READY, EXIT_ENVIRONMENT)
    if needs_identity:
        # Refuse a clone, another host or another root before anything is opened for writing.
        try:
            identity.load_existing(_ReadOnlyEpoch(path), **_identity_kw(env))
        except (identity.IdentityError, sqlite3.Error) as exc:
            raise RefusedError(NOT_READY, EXIT_ENVIRONMENT) from exc
    store = Store(path)
    store.migrate()
    try:
        yield _Context(env=env, custody=custody, store=store)
    finally:
        store.close()


def _identity_kw(env: CliEnv) -> dict[str, Any]:
    kw = env.identity_kwargs
    return {k: kw[k] for k in ("env", "hermes_root", "binding_root", "host_id") if k in kw}


def _load_identity(ctx: _Context) -> Any:
    """The current identity, load only (`identity.load_existing`). The CLI never creates or
    re-keys it implicitly: a clone, a host change, another root or a missing identity refuses,
    and nothing on disk or in the store changes. Only the gateway's adapter creates it."""
    from . import identity

    try:
        return identity.load_existing(ctx.store, **_identity_kw(ctx.env))
    except identity.IdentityError as exc:
        raise RefusedError(NOT_READY, EXIT_ENVIRONMENT) from exc


def _query(store: Any, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
    with store.transaction() as conn:
        return list(conn.execute(sql, params).fetchall())


def _short(value: str) -> str:
    return "-".join(value[i : i + 5] for i in range(0, 20, 5))


# --------------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------------


def _user_exists(store: Any, user_id: str) -> bool:
    return bool(_query(store, "SELECT 1 FROM users WHERE user_id = ?", (user_id,)))


def _cmd_offer(ctx: _Context, args: argparse.Namespace) -> int:
    from . import crypto, wire
    from .contract import OFFER_TTL_S, PROTOCOL_VERSION, TAG_OFFER, QrOffer

    result = ctx.env.compat()
    if not getattr(result, "supported", False):
        why = getattr(getattr(result, "why", None), "value", None) or "hermes_build_unsupported"
        raise RefusedError(f"refused: this Hermes build is not read-compatible ({why})")
    user = args.user
    if user is not None and (
        USER_ID_RE.fullmatch(user) is None or not _user_exists(ctx.store, user)
    ):
        raise RefusedError("refused: --user must name an existing hmpu_ user")
    label = args.label
    if label is not None:
        _check_label(label)

    ident = _load_identity(ctx)
    try:
        record = read_listener_record(
            listener_record_path(ctx.custody.anchor_dir), iid=ident.iid, pid_alive=ctx.env.pid_alive
        )
    except ListenerRecordError as exc:
        raise RefusedError(
            f"refused: {exc}; start the gateway with the hmp platform enabled"
        ) from exc
    if not ctx.env.verify_listener_live(record, ident.iid):
        # SR-7: `pid_alive(pid)` alone cannot tell "our listener is still running" from "this pid
        # was reused by an unrelated same-user process" after an unclean exit. A live, TLS-pinned
        # `/ready` round trip is the authoritative check before anything is minted into a QR code.
        raise RefusedError(
            "refused: the listener record is stale; start the gateway with the hmp platform enabled"
        )
    ep = endpoint_for(record.host, record.port)
    try:
        wire.require_endpoint(ep)
    except wire.WireError as exc:
        raise RefusedError(
            "refused: the listener is bound to an address a phone cannot use; bind it to the "
            "host's tailnet address (platforms.hmp.extra.bind)"
        ) from exc
    try:
        qr_module = ctx.env.qr_factory()
    except ImportError as exc:
        raise RefusedError(
            "refused: the 'qrcode' package is not installed; nothing was created"
        ) from exc

    now = ctx.now()
    oid = wire.b64u_encode(crypto.random_bytes(16))
    s = crypto.random_bytes(32)
    exp = now + OFFER_TTL_S
    payload = wire.encode_qr_payload(
        QrOffer(
            v=PROTOCOL_VERSION, iid=ident.iid, ep=(ep,), oid=oid, s=wire.b64u_encode(s), exp=exp
        ),
        now=now,
    )
    ctx.store.insert_offer(oid, crypto.secret_hash(TAG_OFFER, s), exp, intended_user_id=user)
    ctx.store.write_audit(now, "offer_create", "ok", id_prefix8=oid[:8])
    del s
    out = ctx.out
    if not ctx.env.interactive():  # re-checked right before S is shown (PR1-2)
        raise RefusedError("refused: the terminal went away; the offer was created but never shown")
    qr = qr_module.QRCode(border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr.print_ascii(out=out, invert=True)
    del payload
    if label:
        out.write(f"Offer label: {label}\n")
    out.write(f"Instance: {_short(ident.iid)}\n")
    out.write(f"Endpoint: {ep}\n")
    out.write(f"Scan with Hermes Bot Mobile within {OFFER_TTL_S // 60} minutes. Single use.\n")
    if args.no_wait:
        return EXIT_OK
    return _wait_for_scan_and_confirm(
        ctx, oid=oid, exp=exp, label=label, user=user, grant=not args.no_grant
    )


# --------------------------------------------------------------------------------------------------
# `pair offer`'s one-command flow (owner requirement, 2026-09-27): wait for the P2 claim, prompt for
# the typed SAS, confirm or deny, then print what to do next. Every step reuses the same store path
# and the same functions `pair list` / `pair confirm` / `pair deny` use -- nothing here re-derives
# the SAS, the mismatch accounting or the confirm/deny transactions.
# --------------------------------------------------------------------------------------------------


def _resume_hint(pairing_id: str | None, label: str | None) -> str:
    """How to pick this up again with the old two-step commands. `pairing_id` is `None` when
    nothing was ever claimed (or the claim's own `confirm_by` has passed, so it is no longer
    reachable through `pair confirm` either) -- then the only way forward is a new offer."""
    if pairing_id is not None:
        return (
            "Resume with the two-step commands:\n"
            "  hermes hmp pair list\n"
            "  hermes hmp pair confirm --sas <code shown on the phone> --label "
            f"{label or '<label>'} -- {pairing_id}\n"
            f"  or deny it: hermes hmp pair deny -- {pairing_id}\n"
        )
    offer_cmd = "hermes hmp pair offer" + (f" --label {label}" if label else "")
    return f"Make a new offer: {offer_cmd}\n"


def _label_for_confirm(offer_label: str | None, device_name_sanitized: str) -> str:
    """The offer's own `--label`, or (when the operator minted the offer without one) a stand-in
    derived from the device's own sanitized name -- already NFC, already dropped of the same
    control/format categories `_check_label` drops, and already bounded to
    `DEVICE_NAME_MAX_BYTES` (== `OPERATOR_LABEL_MAX_BYTES`). The one case that can still fail
    `_check_label` is an all-whitespace name (space is not a dropped category), so that falls back
    to a fixed, always-valid label."""
    if offer_label:
        return offer_label
    try:
        _check_label(device_name_sanitized)
    except RefusedError:
        return "phone"
    return device_name_sanitized


def _poll_for_request(ctx: _Context, oid: str, exp: int) -> Any:
    """The pairing this offer's `oid` was claimed into (PR2-5), or `None` once the offer's own
    `exp` passes first. The query is `pair list`'s own shape, narrowed to this offer. Raises
    `KeyboardInterrupt` (uncaught here) on Ctrl-C during a poll sleep."""
    from .pairing import STATE_AWAITING

    while True:
        rows = _query(
            ctx.store,
            "SELECT pairing_id, device_pub, device_name_sanitized, confirm_by FROM pairings "
            "WHERE oid = ? AND state = ? ORDER BY confirm_by",
            (oid, STATE_AWAITING),
        )
        if rows:
            return rows[0]
        if ctx.now() >= exp:
            return None
        ctx.env.sleep(OFFER_POLL_INTERVAL_S)


def _print_next_steps(ctx: _Context) -> None:
    """The generic placeholder next steps, used when OD-F8's in-terminal grant did not run at all
    (`--no-grant`) or had nothing to offer (no `profiles` in the listener record -- an older
    gateway, or the build is unsupported and has no bridge to enumerate them from; `<profile>`
    then stays a literal placeholder, S1)."""
    out = ctx.out
    out.write("\nNext steps:\n")
    out.write("  On the phone, open a bot and tap Request access.\n")
    out.write("  Then approve it here: hermes -p <profile> pairing list, then\n")
    out.write("    hermes -p <profile> pairing approve hmp <request_id>\n")


# --------------------------------------------------------------------------------------------------
# OD-F8 (2026-09-27): in-terminal bot access, right after "Paired ✓". See the module docstring.
# --------------------------------------------------------------------------------------------------


DISPLAY_NAME_MAX_BYTES = OPERATOR_LABEL_MAX_BYTES
_DISPLAY_NAME_PLACEHOLDER = "(unnamed)"


def _sanitize_display_name(raw: str) -> str:
    """NIT fix, independent review of OD-F8: a served profile's display name comes from the
    listener record, which the adapter fills from the bridge's own `served_profiles()`
    (`_fallback_display_name`) -- operator/bot configuration, not device-claimed input like
    `device_name_sanitized`, but nothing validates it either before `_parse_record_profiles`
    accepts any non-empty string, and it is written straight to the operator's terminal
    (`_prompt_grant_selection`'s prompt, the per-bot `pick` line, the `✓`/`⚠` result lines, and the
    manual fallback commands). Drops the same control/format categories `_check_label` refuses an
    offer label for -- C0/C1 controls including ESC (a terminal escape sequence could otherwise
    move the cursor, rewrite prior output, or worse), plus format/line/paragraph-separator/
    private-use/unassigned code points -- then caps the result at `DISPLAY_NAME_MAX_BYTES` UTF-8
    bytes without splitting a multi-byte character. Unlike `_check_label`, this never raises: a
    malformed display name should render safely, not abort the grant flow, so a name reduced to
    nothing by stripping falls back to a fixed placeholder rather than printing an empty label next
    to a profile id."""
    cleaned = "".join(ch for ch in raw if unicodedata.category(ch) not in _DROPPED_LABEL_CATEGORIES)
    cleaned = cleaned.encode("utf-8")[:DISPLAY_NAME_MAX_BYTES].decode("utf-8", errors="ignore")
    cleaned = cleaned.strip()
    return cleaned or _DISPLAY_NAME_PLACEHOLDER


def _served_bots(ctx: _Context) -> list[tuple[str, str]] | None:
    """The instance's served `(profile, display_name)` pairs from the listener record, or `None`
    when the record has none (an older gateway, or an unsupported build) -- the caller then falls
    back to `_print_next_steps`. A profile name that fails Hermes's own naming rule is dropped
    (defence in depth: it must never reach a `-p <profile>` argv or the fallback command text).
    Every display name is sanitized (`_sanitize_display_name`) before this function ever returns
    it, so every caller downstream -- the prompt, the `pick` sub-prompt, the result lines, the
    manual fallback text -- is safe by construction."""
    try:
        ident = _load_identity(ctx)
        record = read_listener_record(
            listener_record_path(ctx.custody.anchor_dir), iid=ident.iid, pid_alive=ctx.env.pid_alive
        )
    except (ListenerRecordError, RefusedError):
        return None
    if not record.profiles:
        return None
    bots = [(p, _sanitize_display_name(d)) for p, d in record.profiles if _valid_profile_name(p)]
    return bots or None


def _prompt_grant_selection(ctx: _Context, bots: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """"Allow ⟨label⟩ to use all of these? [y/n/pick]" (OD-F8; NIT fix, independent review). No
    bracket default any more: only an explicit `y`/`yes` is every bot; `n`/`no` (or EOF) is none;
    `pick` asks per bot, `[y/N]` each, defaulting to no for anything but `y`/`yes`. A blank line --
    previously silently treated the same as `y`, so a paste ending in a stray empty line could
    grant every served bot without the operator ever answering this prompt -- re-asks instead, the
    same "Please answer y or n." pattern the compare-and-confirm SAS prompt already uses for
    unrecognized input."""
    out = ctx.out
    out.write("\n")
    for profile, display in bots:
        out.write(f"  {display} ({profile})\n")
    out.write("Allow the phone to use all of these? [y/n/pick] ")
    out.flush()
    while True:
        line = ctx.env.stdin.readline()
        if line == "":  # EOF: treat as declining, never as "yes" (fail closed on a grant)
            return []
        text = line.strip().lower()
        if text in ("y", "yes"):
            return bots
        if text in ("n", "no"):
            return []
        if text == "pick":
            chosen: list[tuple[str, str]] = []
            for profile, display in bots:
                out.write(f"  Allow {display} ({profile})? [y/N] ")
                out.flush()
                answer = ctx.env.stdin.readline()
                if answer.strip().lower() in ("y", "yes"):
                    chosen.append((profile, display))
            return chosen
        out.write("Type y, n or pick: ")
        out.flush()


def _combined_approve_command(profiles: list[str], user_id: str) -> str:
    """One combined POSIX shell command approving `user_id`'s pending `hmp` requests across every
    profile still waiting at the OD-F8 timeout -- the exact same shape as `authorize.py`'s
    single-profile `approve_command` (PR6-4), looped over `profiles`; mirrors the app's own
    `combinedApproveCommand`
    (`mobile/app/lib/screens/home/request_access_all_screen.dart`)."""
    quoted_profiles = " ".join(shlex.quote(p) for p in profiles)
    u = shlex.quote(user_id)
    return (
        f"for p in {quoted_profiles}; do "
        'hermes -p "$p" pairing list | '
        f"awk -v u={u} '$1==\"hmp\" && $3==u {{print $2}}' | "
        'while read -r id; do hermes -p "$p" pairing approve hmp "$id"; done; '
        "done"
    )


# Exactly Hermes's own request-id shape (`hermes_cli/pairing.py` mints these; `store.py`'s HMP side
# mirrors the same 16-hex convention). Used only to validate a `pairing list` row, never to build
# one. Unparenthesized here; `_pending_hmp_row_re` wraps it in a capturing group.
REQUEST_ID_RE = re.compile(r"[0-9a-f]{16}")


def _pending_hmp_row_re(user_id: str) -> re.Pattern[str]:
    """A strict WHOLE-line pattern (SHOULD-FIX, independent review of OD-F8) for one `pairing
    list` row, in the Hermes printer's own column order (`hermes_cli/pairing.py:35-37`, read at
    review time): platform `hmp`, a request id of exactly 16 lowercase hex digits, then this
    pairing's own `user_id` byte-for-byte (already `hmpu_` + 32 hex, `USER_ID_RE`), then at least
    the printer's own trailing name/age content -- never end-of-line right after the user id, which
    the real printer never produces. Built fresh per call (`user_id` varies; this is not a hot
    loop) with `re.escape`, so nothing in `user_id` can itself act as regex syntax. The old parser
    kept a line merely because its first whitespace-split field was `hmp` and its third equalled
    `user_id`, with no shape check on the request id and no requirement that these be the ONLY
    three leading fields -- so a single `pairing list` row whose `user_name` field contains a raw
    newline (stored from the inbound sender with no sanitizer, `gateway/run_inbound.py`, and
    printed unescaped, `hermes_cli/pairing.py`'s `_cmd_list`) could splice a second, fully
    attacker-chosen `hmp <id> <user_id>` line into this CLI's own `pairing list` stdout, which the
    old parser accepted exactly as if Hermes itself had printed it. This pattern alone does not
    remove that risk when the attacker already knows a real `user_id` (`pair offer --user`, per the
    review): a forged row can still be built to match it byte-for-byte. `_list_pending_hmp_requests`
    additionally never treats more than one exact match as safe to approve (see there)."""
    return re.compile(
        r"^\s*hmp\s+(" + REQUEST_ID_RE.pattern + r")\s+" + re.escape(user_id) + r"\s+\S.*$"
    )


def _list_pending_hmp_requests(
    env: CliEnv, exe: str, profile: str, user_id: str
) -> list[str] | None:
    """This user's own pending `hmp` request ids on `profile`, read from `hermes -p <profile>
    pairing list`'s own table, kept only when the WHOLE line matches `_pending_hmp_row_re`.
    `None` when the command could not be run, timed out, exited non-zero, or `user_id` is not
    itself the expected `hmpu_` shape (defensive: never build a row pattern from an unvalidated
    value) -- distinct from an empty list, which means the command ran and found nothing pending.
    A caller with more than one entry MUST NOT approve any of them (see `_grant_bot_access`): two
    exact matches for the same `(profile, user_id)` in one `pairing list` call means either a
    genuine ambiguity in Hermes's own pending set, or a forged extra row, and this function cannot
    tell those apart -- fail closed and let the operator resolve it by hand."""
    if not USER_ID_RE.fullmatch(user_id):
        return None
    result = env.run_hermes_cli(
        exe, ["-p", profile, "pairing", "list"], timeout=HERMES_CLI_TIMEOUT_S, environ=env.environ
    )
    if result is None or result.returncode != 0:
        return None
    row_re = _pending_hmp_row_re(user_id)
    ids: list[str] = []
    for line in result.stdout.splitlines():
        match = row_re.fullmatch(line)
        if match:
            ids.append(match.group(1))
    return ids


def _approve_hmp_request(env: CliEnv, exe: str, profile: str, request_id: str) -> bool:
    result = env.run_hermes_cli(
        exe,
        ["-p", profile, "pairing", "approve", "hmp", request_id],
        timeout=HERMES_CLI_TIMEOUT_S,
        environ=env.environ,
    )
    return result is not None and result.returncode == 0


def _grant_bot_access(ctx: _Context, *, user_id: str) -> None:
    """Step (b)-(d) of OD-F8: list, ask, wait and approve. Falls back to `_print_next_steps`
    whenever there is nothing to offer, nothing chosen, or no `hermes` executable to run."""
    out = ctx.out
    bots = _served_bots(ctx)
    if bots is None:
        _print_next_steps(ctx)
        return
    chosen = _prompt_grant_selection(ctx, bots)
    if not chosen:
        _print_next_steps(ctx)
        return
    exe = ctx.env.hermes_executable()
    if exe is None:
        out.write(
            "\nCouldn't find a safe way to run Hermes's own CLI; approve these manually once the "
            "phone has requested access:\n"
        )
        for profile, display in chosen:
            out.write(f"  {display}: hermes -p {profile} pairing list, then\n")
            out.write(f"    hermes -p {profile} pairing approve hmp <request_id>\n")
        return

    remaining = dict(chosen)
    out.write(
        "\nWaiting for the phone to request access to each bot… (Ctrl-C to stop waiting)\n"
    )
    deadline = ctx.now() + BOT_GRANT_WAIT_S
    try:
        while remaining and ctx.now() < deadline:
            for profile in list(remaining):
                ids = _list_pending_hmp_requests(ctx.env, exe, profile, user_id)
                if not ids:
                    continue
                if len(ids) > 1:
                    # SHOULD-FIX (independent review of OD-F8): more than one row for the same
                    # (profile, user_id) in one `pairing list` call is never safe to auto-approve --
                    # a genuine ambiguity in Hermes's own pending set, or a forged extra row
                    # (`_pending_hmp_row_re`'s own docstring), look identical from here. Approve
                    # none of them, stop waiting on this profile, and say so plainly so the operator
                    # resolves it by hand rather than the CLI guessing.
                    display = remaining.pop(profile)
                    out.write(
                        f"  ⚠ {display} ({profile}): more than one pending request for this "
                        "user -- not approving any of them automatically. Check and approve the "
                        f"right one yourself: hermes -p {profile} pairing list, then\n"
                        f"    hermes -p {profile} pairing approve hmp <request_id>\n"
                    )
                    continue
                (request_id,) = ids
                if _approve_hmp_request(ctx.env, exe, profile, request_id):
                    out.write(f"  ✓ {remaining.pop(profile)} ({profile})\n")
            if remaining:
                ctx.env.sleep(BOT_GRANT_POLL_INTERVAL_S)
    except KeyboardInterrupt:
        out.write("\nStopped waiting.\n")
    if remaining:
        out.write("Still waiting for the phone to request access to:\n")
        for profile, display in remaining.items():
            out.write(f"  {display} ({profile})\n")
        out.write(
            "Tap Request access to all on the phone, or approve them all with one command:\n"
        )
        out.write(f"  {_combined_approve_command(list(remaining), user_id)}\n")


def _wait_for_scan_and_confirm(
    ctx: _Context, *, oid: str, exp: int, label: str | None, user: str | None, grant: bool = True
) -> int:
    out = ctx.out
    out.write("Waiting for the phone to scan… (Ctrl-C to cancel)\n")
    try:
        row = _poll_for_request(ctx, oid, exp)
    except KeyboardInterrupt:
        out.write("\nCancelled before any phone scanned.\n")
        out.write(_resume_hint(None, label))
        return EXIT_INTERRUPTED
    if row is None:
        out.write("Offer expired before it was scanned.\n")
        out.write(_resume_hint(None, label))
        return EXIT_OK

    pairing_id = str(row["pairing_id"])
    confirm_by = int(row["confirm_by"])
    device_name_sanitized = str(row["device_name_sanitized"])
    confirm_label = _label_for_confirm(label, device_name_sanitized)
    out.write(
        f"A phone is waiting: {json.dumps(device_name_sanitized, ensure_ascii=True)} "
        "(unverified, device-claimed)\n"
    )

    while True:
        if ctx.now() > confirm_by:
            out.write("The confirm window for this phone has closed.\n")
            out.write(_resume_hint(None, label))
            return EXIT_OK
        # OD-F7 (2026-09-27): compare-and-confirm replaces typing the SAS in this interactive
        # flow. The device row is re-read each loop (a mismatch never happens here -- there is no
        # typed value to mismatch -- but a re-prompt after "garbage" input must still show the
        # current, correct code, and the row could in principle have moved on between prompts).
        expected = _sas_of(bytes(row["device_pub"]))
        out.write("\nExpected code:\n")
        out.write(f"  {expected}\n")
        out.write("Does the phone show this code? [y/N] ")
        out.flush()
        try:
            line = ctx.env.stdin.readline()
        except KeyboardInterrupt:
            out.write("\nCancelled. The pairing is still pending.\n")
            out.write(_resume_hint(pairing_id, confirm_label))
            return EXIT_INTERRUPTED
        if line == "":  # EOF: stdin closed under us, not a normal answer
            out.write("\nInput closed. The pairing is still pending.\n")
            out.write(_resume_hint(pairing_id, confirm_label))
            return EXIT_INTERRUPTED
        text = line.strip().lower()
        if text not in ("y", "yes", "n", "no", ""):
            out.write("Please answer y or n.\n")
            continue
        if text in ("n", "no", ""):
            _cmd_deny(ctx, argparse.Namespace(pairing_id=pairing_id))
            return EXIT_OK
        ns = argparse.Namespace(
            pairing_id=pairing_id,
            # The operator's own visual compare against the phone IS the confirmation (OD-F7);
            # `_do_confirm` still runs the full constant-time compare, just against the value this
            # same process just showed, so a concurrent change to the pairing (e.g. it was denied
            # elsewhere between the prompt and the answer) is still caught by its own re-check of
            # `AWAITING`, never silently accepted.
            sas=expected,
            label=confirm_label,
            user=user,
            yes_share=user is not None,  # the operator already chose this user at offer time
        )
        try:
            _, user_id = _do_confirm(ctx, ns)
        except KeyboardInterrupt:
            out.write("\nCancelled. The pairing is still pending.\n")
            out.write(_resume_hint(pairing_id, confirm_label))
            return EXIT_INTERRUPTED
        except RefusedError as exc:
            message = str(exc)
            out.write(f"{message}\n")
            if "now denied" in message:
                return EXIT_REFUSED
            if "no such pending pairing" in message:
                out.write(_resume_hint(None, label))
                return EXIT_OK
            # A concurrent change made the once-valid comparison stale; re-prompt (SR-2's shape,
            # kept for any other recoverable refusal `_do_confirm` may raise).
            continue
        out.write(f"Paired ✓ {confirm_label}\n")
        if grant:
            _grant_bot_access(ctx, user_id=user_id)
        else:
            _print_next_steps(ctx)
        return EXIT_OK


def _sas_of(device_pub: bytes) -> str:
    from . import crypto

    return crypto.device_sas(crypto.spki_fingerprint(device_pub))


def _cmd_list(ctx: _Context, _args: argparse.Namespace) -> int:
    from .pairing import STATE_AWAITING

    rows = _query(
        ctx.store,
        "SELECT pairing_id, device_pub, device_name_sanitized, confirm_by FROM pairings "
        "WHERE state = ? AND confirm_by >= ? ORDER BY confirm_by",
        (STATE_AWAITING, ctx.now()),
    )
    out = ctx.out
    if not rows:
        out.write("No pending pairings.\n")
        return EXIT_OK
    for row in rows:
        first_group = _sas_of(bytes(row["device_pub"])).split("-", 1)[0]  # PR3-1: first group
        name = json.dumps(str(row["device_name_sanitized"]), ensure_ascii=True)
        left = max(0, int(row["confirm_by"]) - ctx.now())
        pid = row["pairing_id"]
        out.write(
            f"{pid}  SAS {first_group}-...  name {name} (unverified, device-claimed)"
            f"  confirm within {left}s\n"
        )
        # The id is b64u and may start with "-": it always goes after "--".
        out.write(
            f"  confirm: hermes hmp pair confirm --sas <full SAS> --label <label> -- {pid}\n"
            f"  deny:    hermes hmp pair deny -- {pid}\n"
        )
    return EXIT_OK


def _check_label(label: str) -> None:
    if not label or len(label.encode("utf-8")) > OPERATOR_LABEL_MAX_BYTES:
        raise RefusedError(f"refused: a label is 1-{OPERATOR_LABEL_MAX_BYTES} bytes")
    if any(unicodedata.category(ch) in _DROPPED_LABEL_CATEGORIES for ch in label):
        raise RefusedError("refused: a label may not contain control or format characters")
    if unicodedata.normalize("NFC", label) != label or not label.strip():
        raise RefusedError("refused: a label must be NFC text that is not blank")


def _canonical_sas(text: str) -> str:
    """The SAS as typed, with spaces and hyphens removed and in upper case."""
    return "".join(text.split()).replace("-", "").upper()


def _decode_json_list_literal(raw: str) -> object:
    """Mirrors Hermes's `gateway.platforms._shared.decode_json_list_literal`: a value written by
    `hermes config set` may be a JSON list literal string (e.g. `'["hmpu_…"]'`). Malformed JSON
    passes through unchanged and falls to the comma-split path (SR-1)."""
    if raw.lstrip()[:1] == "[":
        try:
            loaded = json.loads(raw)
        except ValueError:
            return raw
        if isinstance(loaded, list):
            return loaded
    return raw


def _coerce_allow_set(raw: str) -> set[str]:
    """Mirrors Hermes's `gateway.authz_mixin._coerce_allow_set` exactly (SR-1): a JSON list
    literal, or a comma-separated scalar. Parsing this any other way (a bare comma split) misses
    the JSON-list form and makes the CLI under-report an instance-wide grant."""
    decoded = _decode_json_list_literal(raw)
    if isinstance(decoded, list):
        return {str(part).strip() for part in decoded if str(part).strip()}
    return {part.strip() for part in str(decoded).split(",") if part.strip()}


def _env_allowlisted(env: CliEnv, user_id: str) -> bool:
    """Instance-wide env allowlist membership, as this operator shell sees it (E-GAP-31). This
    sees only this process's own environment: it cannot see `platforms.hmp.extra.allow_from`
    (config-based grants) or a gateway-bridged value from another profile's environment (SR-1) --
    `CONFIG_ALLOWLIST_NOT_CHECKED_NOTE` is printed alongside this result for that reason."""
    for name in INSTANCE_WIDE_ALLOWLIST_ENVS:
        members = _coerce_allow_set(env.environ.get(name, ""))
        if user_id in members or "*" in members:
            return True
    return False


CONFIG_ALLOWLIST_NOT_CHECKED_NOTE = (
    "NOT CHECKED: this CLI cannot read config-based allowlists (platforms.hmp.extra.allow_from) "
    "or values the gateway bridges into its own environment from another profile's config; check "
    "them with 'hermes -p <profile> config get platforms.hmp.extra.allow_from'."
)


def _requested_profiles(store: Any, user_id: str) -> list[str]:
    rows = _query(store, "SELECT profile FROM chats WHERE user_id = ? ORDER BY profile", (user_id,))
    return [str(r["profile"]) for r in rows]


def _print_user_share(ctx: _Context, user_id: str) -> None:
    """PR3-3: what joining this user shares with the new device."""
    out = ctx.out
    out.write(f"User {user_id} already has:\n")
    devices = _query(
        ctx.store,
        "SELECT device_id, label, state FROM devices WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    )
    for d in devices or []:
        out.write(f"  device {d['device_id']}  {json.dumps(str(d['label']))}  {d['state']}\n")
    if not devices:
        out.write("  no devices\n")
    profiles = _requested_profiles(ctx.store, user_id)
    for p in profiles:
        out.write(f"  requested access to bot {p} (check: hermes -p {p} pairing list)\n")
    if _env_allowlisted(ctx.env, user_id):
        out.write("  INSTANCE-WIDE: this user is in an env allowlist, which covers every bot\n")
    out.write(f"  {CONFIG_ALLOWLIST_NOT_CHECKED_NOTE}\n")
    out.write("Every grant of this user will also apply to the new device.\n")


def _record_sas_mismatch(ctx: _Context, pairing_id: str) -> int:
    """SR-2: increment the mismatch count and, at `SAS_MAX_MISMATCHES`, deny the pairing -- both
    in the ONE transaction, so a crash between "the third mismatch committed" and "the pairing
    denied" cannot happen. Returns the count after the increment."""
    from .contract import SAS_MAX_MISMATCHES
    from .pairing import STATE_AWAITING, STATE_DENIED

    with ctx.store.transaction() as conn:
        conn.execute(
            "UPDATE pairings SET sas_mismatches = sas_mismatches + 1 "
            "WHERE pairing_id = ? AND state = ?",
            (pairing_id, STATE_AWAITING),
        )
        row = conn.execute(
            "SELECT sas_mismatches FROM pairings WHERE pairing_id = ?", (pairing_id,)
        ).fetchone()
        count = int(row["sas_mismatches"]) if row is not None else 0
        conn.execute(
            "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
            (ctx.now(), "pair_confirm", pairing_id[:8], "sas_mismatch"),
        )
        if count >= SAS_MAX_MISMATCHES:
            conn.execute(
                "UPDATE pairings SET state = ? WHERE pairing_id = ? AND state = ?",
                (STATE_DENIED, pairing_id, STATE_AWAITING),
            )
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
                (ctx.now(), "pair_deny", pairing_id[:8], "denied"),
            )
    return count


def _delete_orphan_user(store: Any, user_id: str) -> None:
    """SR-8: best-effort cleanup of a `hmpu_` row this command minted but could not attach a
    device to. Never masks the original failure with a cleanup error."""
    with contextlib.suppress(Exception), store.transaction() as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def _do_confirm(ctx: _Context, args: argparse.Namespace) -> tuple[str, str]:
    """The `pair confirm` activation itself (PR3-2..PR3-4): SAS check, the `--user` share rules,
    `confirm_pairing`. Returns `(device_id, user_id)`. Shared by `_cmd_confirm` (the `pair
    confirm` subcommand, typed `--sas`) and the one-command flow's compare-and-confirm (OD-F7,
    `args.sas` is the value this same process just showed the operator, not typed input) -- one
    activation path, so both stay identical in every rule except how `args.sas` was obtained."""
    from . import crypto
    from .contract import SAS_MAX_MISMATCHES
    from .pairing import STATE_AWAITING, confirm_pairing, deny_pairing

    _check_label(args.label)
    rows = _query(
        ctx.store,
        "SELECT p.device_pub, p.confirm_by, p.sas_mismatches, o.intended_user_id "
        "FROM pairings p JOIN offers o ON o.oid = p.oid WHERE p.pairing_id = ? AND p.state = ?",
        (args.pairing_id, STATE_AWAITING),
    )
    if not rows or ctx.now() > int(rows[0]["confirm_by"]):
        raise RefusedError("refused: no such pending pairing")
    row = rows[0]

    if int(row["sas_mismatches"]) >= SAS_MAX_MISMATCHES:
        # SR-2: the count already reached the limit while the pairing is still AWAITING -- a
        # process that died between the third increment and the deny left it this way. Deny it
        # now, before comparing, rather than letting a correct SAS activate a device past the
        # limit.
        deny_pairing(ctx.store, args.pairing_id, now=ctx.now())
        raise RefusedError("refused: SAS mismatch; the pairing is now denied")

    expected = _sas_of(bytes(row["device_pub"]))
    if not crypto.constant_time_equal(_canonical_sas(args.sas), _canonical_sas(expected)):
        count = _record_sas_mismatch(ctx, args.pairing_id)
        if count >= SAS_MAX_MISMATCHES:
            raise RefusedError("refused: SAS mismatch; the pairing is now denied")
        raise RefusedError(f"refused: SAS mismatch ({count} of {SAS_MAX_MISMATCHES})")

    intended = row["intended_user_id"]
    if args.user is not None:
        if USER_ID_RE.fullmatch(args.user) is None or not _user_exists(ctx.store, args.user):
            raise RefusedError("refused: --user must name an existing hmpu_ user")
        if intended != args.user:
            raise RefusedError("refused: --user does not match the user this offer was made for")
        _print_user_share(ctx, args.user)
        if not args.yes_share:
            raise RefusedError("refused: re-run with --yes-share to share these grants")
        user_id, created = args.user, False
    else:
        if intended is not None:
            raise RefusedError("refused: this offer was made for an existing user; pass --user")
        user_id, created = "hmpu_" + crypto.random_bytes(16).hex(), True
        ctx.store.insert_user(user_id, args.label, ctx.now())
    try:
        device_id = confirm_pairing(
            ctx.store, args.pairing_id, user_id=user_id, label=args.label, now=ctx.now()
        )
    except LookupError as exc:
        if created:
            _delete_orphan_user(ctx.store, user_id)
        raise RefusedError("refused: the pairing is no longer pending") from exc
    except Exception:
        # SR-8: `insert_user` and `confirm_pairing` run in separate transactions. Cleanup must
        # not be limited to the one expected failure mode (`LookupError`, "no longer pending");
        # any other failure here (e.g. an IntegrityError) must not leave an unused `hmpu_` row.
        if created:
            _delete_orphan_user(ctx.store, user_id)
        raise
    return device_id, user_id


def _cmd_confirm(ctx: _Context, args: argparse.Namespace) -> int:
    device_id, user_id = _do_confirm(ctx, args)
    ctx.out.write(f"Confirmed. Device {device_id}, user {user_id}.\n")
    return EXIT_OK


def _cmd_deny(ctx: _Context, args: argparse.Namespace) -> int:
    from .pairing import deny_pairing

    if not deny_pairing(ctx.store, args.pairing_id, now=ctx.now()):
        raise RefusedError("refused: no such pending pairing")
    ctx.out.write("Denied.\n")
    return EXIT_OK


def _cmd_devices_list(ctx: _Context, _args: argparse.Namespace) -> int:
    rows = _query(
        ctx.store,
        "SELECT device_id, user_id, label, state, created_at FROM devices ORDER BY created_at",
    )
    if not rows:
        ctx.out.write("No devices.\n")
    for r in rows:
        ctx.out.write(
            f"{r['device_id']}  {r['user_id']}  {json.dumps(str(r['label']))}  {r['state']}\n"
        )
    return EXIT_OK


def _cmd_devices_revoke(ctx: _Context, args: argparse.Namespace) -> int:
    from .revoke import last_device_hint, revoke_device

    result = revoke_device(ctx.store, args.device_id, now=ctx.now())
    if not result.found:
        raise RefusedError("refused: no such device")
    ctx.out.write(f"Revoked {args.device_id} and all of its tokens.\n")
    if result.last_device and result.user_id is not None:
        hint = last_device_hint(
            result.user_id,
            _requested_profiles(ctx.store, result.user_id),
            env_allowlisted=_env_allowlisted(ctx.env, result.user_id),
        )
        ctx.out.write(
            "That was the user's last device. HMP does not change Hermes grants; to remove "
            "them, run:\n"
        )
        for line in hint:
            ctx.out.write(f"  {line}\n")
        ctx.out.write(f"  {CONFIG_ALLOWLIST_NOT_CHECKED_NOTE}\n")
    return EXIT_OK


def _cmd_show(ctx: _Context, _args: argparse.Namespace) -> int:
    iid = _load_identity(ctx).iid
    ctx.out.write(f"Instance fingerprint: {_short(iid)}\n")
    ctx.out.write(f"Instance id: {iid}\n")
    try:
        record = read_listener_record(
            listener_record_path(ctx.custody.anchor_dir), iid=iid, pid_alive=ctx.env.pid_alive
        )
        ctx.out.write(f"Listener: {endpoint_for(record.host, record.port)}\n")
    except ListenerRecordError as exc:
        ctx.out.write(f"Listener: not available ({exc})\n")
    return EXIT_OK


def _cmd_rotate(ctx: _Context, _args: argparse.Namespace) -> int:
    from . import identity

    # PR7-2 is the one explicit re-key the operator may ask for, and only of the identity that
    # is current here: a clone, another host or another root refuses before anything changes.
    # SR-9: that currency check runs under `rotate_key`'s own custody lock (`require_current`),
    # not as a separate unlocked check beforehand -- a concurrent gateway re-key between the two
    # could otherwise be silently rotated over.
    try:
        new = identity.rotate_key(ctx.store, require_current=True, **_identity_kw(ctx.env))
    except identity.IdentityError as exc:
        raise RefusedError(NOT_READY, EXIT_ENVIRONMENT) from exc
    ctx.out.write(
        f"New instance fingerprint: {_short(new.iid)}. Every device is revoked, and every open "
        "offer and pending pairing expired. A running gateway stops serving the old key.\n"
    )
    return EXIT_OK


def _cmd_compat(env: CliEnv) -> int:
    result = env.compat()
    out = env.stdout
    status = getattr(getattr(result, "status", None), "value", "unsupported")
    out.write(f"Read compatibility: {status}\n")
    why = getattr(getattr(result, "why", None), "value", None)
    if why:
        out.write(f"Reason: {why}\n")
    ident = getattr(result, "identity", None)
    if ident is not None:
        out.write(f"Git SHA: {ident.git_sha or 'none (no git metadata)'}\n")
        out.write(f"Read-bridge fingerprint: {ident.fingerprint}\n")
    else:
        out.write("Build identity: unidentifiable\n")
    entry = getattr(result, "entry", None)
    out.write(f"List match: {entry.label if entry is not None else 'none'}\n")
    probe = (
        "passed"
        if getattr(result, "supported", False)
        else ("failed" if why == "hermes_read_dependency_missing" else "not run")
    )
    out.write(f"Dependency probe: {probe}\n")
    if getattr(result, "supported", False):
        from . import compat

        send_ready = compat.direct_send_build_qualified(ident)
        out.write(f"Guarded send qualification: {'qualified' if send_ready else 'unqualified'}\n")
    if status != "supported":
        out.write(
            "For an older Hermes install, update to v0.21.5 (v2026.9.24). "
            "If already newer, update HMP after that release is qualified; "
            "see github.com/MahdiHedhli/hermes-hmp/blob/main/docs/RELEASE_COMPAT_WATCH.md.\n"
        )
    return EXIT_OK


_STORE_COMMANDS: dict[tuple[str, str], Callable[[_Context, argparse.Namespace], int]] = {
    ("pair", "offer"): _cmd_offer,
    ("pair", "list"): _cmd_list,
    ("pair", "confirm"): _cmd_confirm,
    ("pair", "deny"): _cmd_deny,
    ("devices", "list"): _cmd_devices_list,
    ("devices", "revoke"): _cmd_devices_revoke,
    ("instance", "show"): _cmd_show,
    ("instance", "rotate-key"): _cmd_rotate,
}


# Commands that use the instance identity: checked load-only before the store is opened.
IDENTITY_COMMANDS: frozenset[tuple[str, str]] = frozenset(
    {("pair", "offer"), ("instance", "show"), ("instance", "rotate-key")}
)


# Keep this annotation: Hermes's current plugin scanner misreads a union type
# on this parameter as a command that prints the process environment.
def dispatch(args: argparse.Namespace, env: Optional[CliEnv] = None) -> int:  # noqa: UP045
    """`handler_fn` for `register_cli_command`."""
    env = env if env is not None else CliEnv()
    group, action = _command(args)
    try:
        if group == "compat":
            return _cmd_compat(env)
        handler = _STORE_COMMANDS.get((group or "", action or ""))
        if handler is None:
            env.stderr.write("usage: hermes hmp {pair,devices,instance,compat} ...\n")
            return EXIT_ENVIRONMENT
        if (group, action) in MUTATING_COMMANDS:
            _check_mutation_allowed(env)
        with _open(env, needs_identity=(group, action) in IDENTITY_COMMANDS) as ctx:
            return handler(ctx, args)
    except RefusedError as refusal:
        env.stderr.write(f"hermes hmp: {refusal}\n")
        return refusal.code
