"""`hermes hmp routes add <profile>`: prepare the root route for one bot created after installation.

HMP can only reach a named profile once the default root `config.yaml` has an exact
`gateway.profile_routes` entry for it. Without it the bridge correctly answers `not_routed`. This
module is the explicit, host-only way to write that one route. It edits ONE file, the default root
`config.yaml`. It does not serve, reload or restart anything: the route is on disk afterwards, and
the gateway must be restarted before it can be in effect. See specs/005-new-profile-routing/.

The profile's own `config.yaml` is never written, backed up or touched. On the inspected Hermes
build (`ca705dbf7ef86425b381b542712aff310f1ee52c`), a multiplexing root serves every live named
profile without consulting that profile's own `gateway.multiplex_profiles`, and that per-profile
flag changes the profile's session namespace, so this command must not set it. The profile config
is still read and must be safe, plain YAML (a prerequisite inspection), and it must not change
while the command runs, but none of its values is required, interpreted or refused.

What it does not do, by design: authorize a user or device, create or approve a pairing request,
enable an API server, restart the gateway, contact Hermes, open the HMP store, change an existing
route, or turn on multiplexing at the root (the root `gateway.multiplex_profiles` must already be
boolean true; that is initial setup). It refuses, changing nothing, whenever an existing route or
a root `multiplex_profiles` value could conflict with the one it would add, instead of widening
any policy.

The module imports only the standard library at import time. PyYAML is imported lazily and only
here (tools/ci/check_plugin_surface.py S1). No Hermes import: the caller passes the custody-
resolved root (`identity.resolve_custody`).

Limits (SEC-1): same-user code can already edit these files. The checks below stop mistakes,
other-user symlink swaps and hostile config shapes; they are not a boundary against same-user code,
and there is no lock shared with Hermes, so a concurrent editor can still race the small window
between the final unchanged-check and the rename. A failure or interrupt once the rename may have
happened is reported from what the file holds afterwards; an edit by someone else is never undone.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "config.yaml"
BACKUP_SUFFIX = ".hmp-bak"
PROFILES_DIRNAME = "profiles"
MAX_CONFIG_BYTES = 1_048_576
BACKUP_MODE = 0o600
ROUTE_PLATFORM = "hmp"
RESERVED_PROFILE = "default"

# Mirrors Hermes's own rule (`cli._PROFILE_NAME_RE`); reproduced, not imported (S1).
PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_EXACT_ROUTE_KEYS = frozenset({"name", "platform", "profile", "guild_id", "enabled"})
_GLOB_CHARS = frozenset("*?[]{}")
_ABSENT = object()


class RoutesError(RuntimeError):
    """A refusal, or a failure with a stated final state. `partial` is True when the root file may
    have been left changed or in an unconfirmed state (the message says which); `interrupted` when
    Ctrl-C or an exit request arrived once the write had started. Messages are status-only, never
    config content."""

    def __init__(self, message: str, *, partial: bool = False, interrupted: bool = False) -> None:
        super().__init__(message)
        self.partial = partial
        self.interrupted = interrupted


@dataclass(frozen=True)
class Outcome:
    """What `add_route` did. File names are generic labels, never absolute paths."""

    profile: str
    route_added: bool
    backups: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.route_added


@dataclass(frozen=True)
class _Snapshot:
    path: Path
    label: str
    data: bytes
    sha256: str
    dev: int
    ino: int
    mode: int


def validate_profile_name(name: object) -> str:
    if not isinstance(name, str) or PROFILE_NAME_RE.fullmatch(name) is None:
        raise RoutesError("the profile name is not a valid Hermes profile name")
    if name == RESERVED_PROFILE:
        raise RoutesError("the default profile is the root; it needs no route")
    return name


# --------------------------------------------------------------------------------------------------
# Safe file access
# --------------------------------------------------------------------------------------------------


def _posix() -> bool:
    return hasattr(os, "geteuid")


def _unsafe_owner_or_mode(st: os.stat_result) -> bool:
    if not _posix():
        return False
    return st.st_uid != os.geteuid() or bool(st.st_mode & 0o022)


def _check_dir(path: Path, label: str) -> None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        raise RoutesError(f"{label} does not exist") from None
    except OSError:
        raise RoutesError(f"{label} cannot be inspected") from None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise RoutesError(f"{label} must be a real directory, not a symlink or file")
    if _unsafe_owner_or_mode(st):
        raise RoutesError(f"{label} must be owned by you and not group- or world-writable")


def _read_config(path: Path, label: str) -> _Snapshot:
    """One `O_NOFOLLOW` open; every check runs on that descriptor (no path re-resolution)."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise RoutesError(f"{label} does not exist") from None
    except OSError:
        raise RoutesError(f"{label} cannot be opened (a symlink is refused)") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise RoutesError(f"{label} must be a regular file")
        if _unsafe_owner_or_mode(st):
            raise RoutesError(f"{label} must be owned by you and not group- or world-writable")
        if st.st_size > MAX_CONFIG_BYTES:
            raise RoutesError(f"{label} is larger than {MAX_CONFIG_BYTES} bytes")
        with os.fdopen(fd, "rb", closefd=False) as fh:
            data = fh.read(MAX_CONFIG_BYTES + 1)
    finally:
        os.close(fd)
    if len(data) > MAX_CONFIG_BYTES:
        raise RoutesError(f"{label} is larger than {MAX_CONFIG_BYTES} bytes")
    return _Snapshot(
        path=path,
        label=label,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        dev=st.st_dev,
        ino=st.st_ino,
        mode=stat.S_IMODE(st.st_mode),
    )


def _unchanged(snap: _Snapshot) -> bool:
    try:
        now = _read_config(snap.path, snap.label)
    except (RoutesError, OSError):
        return False
    return (now.dev, now.ino, now.sha256, now.mode) == (snap.dev, snap.ino, snap.sha256, snap.mode)


def _fsync_dir(path: Path) -> None:
    with contextlib.suppress(OSError, AttributeError):
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    """Same-directory temp file (created 0600, `O_EXCL`, `O_NOFOLLOW`), fsync, chmod, rename."""
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    _fsync_dir(path.parent)


def _backup_target(snap: _Snapshot) -> Path:
    """`config.yaml.hmp-bak` beside the original. Refuses anything there that is not a regular
    file (never replaces a directory or follows a symlink)."""
    target = snap.path.with_name(snap.path.name + BACKUP_SUFFIX)
    try:
        st = os.lstat(target)
    except FileNotFoundError:
        return target
    if not stat.S_ISREG(st.st_mode):
        raise RoutesError(f"the backup location for {snap.label} is not a regular file")
    return target


def _write_backup(snap: _Snapshot, target: Path) -> str:
    """One private rolling backup: mode 0600, atomic, replaced on each change."""
    try:
        _atomic_write(target, snap.data, BACKUP_MODE)
    except OSError:
        raise RoutesError(f"the backup for {snap.label} could not be written") from None
    return f"{snap.label} -> {target.name}"


# --------------------------------------------------------------------------------------------------
# Strict YAML
# --------------------------------------------------------------------------------------------------


def _strict_loader(yaml: Any) -> Any:
    """SafeLoader that also rejects duplicate keys, aliases and merge keys, so the parsed value is
    unambiguous and re-emitting it cannot expand or reinterpret anything."""

    class _Strict(yaml.SafeLoader):  # type: ignore[misc]
        def compose_node(self, parent: Any, index: Any) -> Any:
            if self.check_event(yaml.events.AliasEvent):
                raise yaml.YAMLError("aliases are not supported")
            return super().compose_node(parent, index)

        def construct_mapping(self, node: Any, deep: bool = False) -> Any:
            seen: set[Any] = set()
            for key_node, _value_node in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    raise yaml.YAMLError("merge keys are not supported")
                key = self.construct_object(key_node, deep=True)
                try:
                    duplicate = key in seen
                    seen.add(key)
                except TypeError:
                    raise yaml.YAMLError("unsupported mapping key") from None
                if duplicate:
                    raise yaml.YAMLError("duplicate mapping key")
            return super().construct_mapping(node, deep=deep)

    return _Strict


def _parse(snap: _Snapshot) -> dict[Any, Any]:
    import yaml

    try:
        text = snap.data.decode("utf-8")
        doc = yaml.load(text, Loader=_strict_loader(yaml))  # noqa: S506 - strict SafeLoader
    except (UnicodeDecodeError, yaml.YAMLError, RecursionError, ValueError, TypeError):
        raise RoutesError(f"{snap.label} is not YAML this command can safely edit") from None
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise RoutesError(f"{snap.label} must hold a mapping at the top level")
    return doc


def _emit(doc: dict[Any, Any]) -> bytes:
    import yaml

    return yaml.safe_dump(
        doc, sort_keys=False, default_flow_style=False, allow_unicode=True, width=4096
    ).encode("utf-8")


def _verified_emit(doc: dict[Any, Any], snap: _Snapshot) -> bytes:
    """Emit, re-parse, and require the same value (type and order included) before any write."""
    data = _emit(doc)
    if len(data) > MAX_CONFIG_BYTES:
        raise RoutesError(f"the updated {snap.label} would be too large")
    again = _parse(_Snapshot(snap.path, snap.label, data, "", 0, 0, 0))
    try:
        same = repr(again) == repr(doc)
    except RecursionError:
        same = False
    if not same:
        raise RoutesError(f"the updated {snap.label} could not be verified; nothing was changed")
    return data


# --------------------------------------------------------------------------------------------------
# Planning (pure: no I/O)
# --------------------------------------------------------------------------------------------------


def _root_multiplex_is_enabled(doc: dict[Any, Any]) -> bool:
    """True when the root `gateway.multiplex_profiles` is already boolean `true`. Refuses any
    present top-level or nested value that is not boolean `true`. Only the root is ever asked: a
    profile's own value is neither read nor required."""
    gateway = doc.get("gateway")
    if gateway is not None and not isinstance(gateway, dict):
        raise RoutesError("root config.yaml: `gateway` must be a mapping")
    nested = gateway.get("multiplex_profiles", _ABSENT) if gateway else _ABSENT
    top = doc.get("multiplex_profiles", _ABSENT)
    for value in (top, nested):
        if value is not _ABSENT and value is not True:
            raise RoutesError(
                "root config.yaml: multiplex_profiles is present and is not boolean true "
                f"({type(value).__name__}); resolve it by hand, then retry"
            )
    return nested is True


def _ensure_gateway(doc: dict[Any, Any]) -> dict[Any, Any]:
    gateway = doc.get("gateway")
    if gateway is None:
        gateway = {}
        doc["gateway"] = gateway
    return gateway


def _plain(value: Any) -> str | None:
    """A plain literal: a string with no glob-like characters. Anything else may match widely."""
    if isinstance(value, str) and not (_GLOB_CHARS & set(value)):
        return value.strip().casefold()
    return None


def _may_match(value: Any, literal: str) -> bool:
    if value is None or value == "":
        return True
    plain = _plain(value)
    return plain is None or plain == literal


def _classify_route(route: Any, profile: str) -> str:
    """`none` (cannot match an HMP source for this bot), `exact` (this command's own route) or
    `conflict` (could match it, and is not the exact route)."""
    if not isinstance(route, dict):
        raise RoutesError("gateway.profile_routes entries must be mappings")
    if not (
        _may_match(route.get("platform"), ROUTE_PLATFORM)
        and _may_match(route.get("guild_id"), profile)
    ):
        return "none"
    extras = set(route) - _EXACT_ROUTE_KEYS  # any extra key, even null, is not this route
    name = route.get("name")
    exact = (
        route.get("platform") == ROUTE_PLATFORM
        and route.get("profile") == profile
        and route.get("guild_id") == profile
        and not extras
        and ("enabled" not in route or route["enabled"] is True)
        and (name is None or isinstance(name, str))
    )
    return "exact" if exact else "conflict"


@dataclass(frozen=True)
class _Plan:
    root_doc: dict[Any, Any]
    route_added: bool


def plan(root: dict[Any, Any], profile: str) -> _Plan:
    """Compute the new root document from a deep copy, or refuse. Never widens a policy, and
    never produces a change to anything but the root's `gateway.profile_routes`."""
    if "profile_routes" in root:
        raise RoutesError(
            "root config.yaml has a top-level profile_routes; its location is ambiguous, "
            "resolve it by hand, then retry"
        )
    if not _root_multiplex_is_enabled(root):
        raise RoutesError(
            "root config.yaml does not have gateway.multiplex_profiles: true; this command does "
            "not turn on multiplexing. Complete the initial setup in server/DEPLOYMENT.md first"
        )

    new_root = copy.deepcopy(root)
    root_gateway = _ensure_gateway(new_root)

    routes = root_gateway.get("profile_routes")
    if routes is None:
        routes = []
    if not isinstance(routes, list):
        raise RoutesError("root config.yaml: gateway.profile_routes must be a list")

    kinds = [_classify_route(route, profile) for route in routes]
    if "conflict" in kinds:
        raise RoutesError(
            f"an existing gateway.profile_routes entry could overlap the route for {profile}; "
            "this command never edits or widens existing routes, so resolve it by hand"
        )
    route_name = f"{profile}-route"
    route_added = "exact" not in kinds
    if route_added:
        if any(isinstance(r, dict) and r.get("name") == route_name for r in routes):
            raise RoutesError(f"a route named {route_name} already exists with other settings")
        root_gateway["profile_routes"] = [
            *routes,
            {
                "name": route_name,
                "platform": ROUTE_PLATFORM,
                "profile": profile,
                "guild_id": profile,
            },
        ]

    return _Plan(new_root, route_added)


# --------------------------------------------------------------------------------------------------
# The command's one entry point
# --------------------------------------------------------------------------------------------------


def _current_bytes(snap: _Snapshot) -> bytes | None:
    try:
        return _read_config(snap.path, snap.label).data
    except (RoutesError, OSError):
        return None


def _write_failure(exc: BaseException, root_snap: _Snapshot, new_root: bytes) -> RoutesError:
    """The root rename may have happened. Report what the file holds now, from its content alone.
    Nothing is restored: a file that holds neither the original nor this command's content was
    changed by someone else and is left exactly as found. Never includes config content or
    exception details."""
    interrupted = not isinstance(exc, Exception)
    current = _current_bytes(root_snap)
    if current == new_root:
        state, partial = (
            "now holds the new route (it is on disk; the running gateway is unchanged)",
            True,
        )
    elif current == root_snap.data:
        state, partial = "was not changed by this command", False
    else:
        state, partial = (
            "state could not be confirmed (neither its original nor this command's content)",
            True,
        )
    reason = "interrupted" if interrupted else "root config.yaml could not be written"
    note = ""
    if partial:
        note = (
            f" Its previous content is in {root_snap.path.name}{BACKUP_SUFFIX} beside it."
            " Run the command again to confirm."
        )
    return RoutesError(
        f"{reason}. root config.yaml {state}. profile config.yaml was not changed by this "
        f"command.{note}",
        partial=partial,
        interrupted=interrupted,
    )


def _prepare(hermes_root: Path, name: str) -> tuple[_Snapshot, _Snapshot, _Plan]:
    """Everything before the first write. A failure here changed nothing. The profile config is
    read and parsed as a prerequisite inspection only (path, owner, mode, size, strict YAML); no
    value in it is interpreted."""
    root = Path(os.path.realpath(hermes_root))
    profile_home = root / PROFILES_DIRNAME / name
    _check_dir(root, "the Hermes root")
    _check_dir(root / PROFILES_DIRNAME, "the profiles directory")
    _check_dir(profile_home, f"profile {name}")
    root_snap = _read_config(root / CONFIG_FILENAME, "root config.yaml")
    profile_snap = _read_config(profile_home / CONFIG_FILENAME, "profile config.yaml")
    _parse(profile_snap)
    return root_snap, profile_snap, plan(_parse(root_snap), name)


def add_route(hermes_root: Path, profile: str) -> Outcome:
    """Prepare the root route for `profile`, or refuse. `hermes_root` comes from
    `identity.resolve_custody` (the default root; a named profile never gets here)."""
    name = validate_profile_name(profile)
    try:
        root_snap, profile_snap, result = _prepare(hermes_root, name)
        # Emission is still before any write, so the same status-only refusal covers it.
        new_root = _verified_emit(result.root_doc, root_snap) if result.route_added else b""
    except (OSError, RecursionError, ImportError):
        # Nothing was written yet. Details are withheld: they can quote private config.
        raise RoutesError(
            "the configuration could not be read or processed (details withheld); "
            "nothing was changed"
        ) from None
    return _apply(name, root_snap, profile_snap, result, new_root)


def _apply(
    name: str,
    root_snap: _Snapshot,
    profile_snap: _Snapshot,
    result: _Plan,
    new_root: bytes,
) -> Outcome:
    if not result.route_added:
        return Outcome(profile=name, route_added=False, backups=())

    # The profile config is never written, but it is part of what was inspected: drift in either
    # file since the read refuses the run.
    both = (root_snap, profile_snap)
    if not all(_unchanged(s) for s in both):
        raise RoutesError("a config file changed while this command ran; nothing was changed")
    try:
        target = _backup_target(root_snap)  # refuse before writing anything
    except OSError:
        raise RoutesError("a backup location cannot be inspected; nothing was changed") from None
    backup = _write_backup(root_snap, target)

    # The backup write gives a concurrent editor time: recheck both immediately before the rename.
    if not all(_unchanged(s) for s in both):
        raise RoutesError(
            "a config file changed while this command ran; no config file was changed "
            "by this command"
        )
    try:
        _atomic_write(root_snap.path, new_root, root_snap.mode)
    except BaseException as exc:
        raise _write_failure(exc, root_snap, new_root) from None
    return Outcome(profile=name, route_added=True, backups=(backup,))
