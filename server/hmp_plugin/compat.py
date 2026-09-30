"""Read-compatibility gate (GU-2c, ERR-2a; research R8). Implementation: T023.

`CompatGate.evaluate()` runs before anything imports `bridge.py`. Its order is mandatory
(controller ruling on T013):

1. Locate the Hermes source root with `importlib.util.find_spec("hermes_constants").origin`.
   This imports nothing.
2. Compute the build identity with file reads only: the read-bridge fingerprint, always, plus the
   git SHA when the install has git metadata (research R8 steps 2-3).
3. If the build is unidentifiable, or `match_build` (the CS-19 rule, fixed in this module) finds no
   entry in `read_compat_builds.json`, return UNSUPPORTED (`hermes_build_unsupported`) at once,
   **without importing any Hermes module**. An unlisted build never has a Hermes internal imported
   by HMP ("never a guessed call", GU-2c).
4. Only for a listed build, run the dependency probe (`probe_read_dependencies`: import and
   signature inspection, no calls). A failure is UNSUPPORTED (`hermes_read_dependency_missing`).
5. Otherwise SUPPORTED, and only then may the bridge be imported and constructed.

`probe_read_dependencies` is the only function outside `bridge.py` allowed to import Hermes modules
dynamically. `tools/ci/check_plugin_surface.py` enforces that. This module never imports `bridge`.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import sysconfig
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .contract import OtherWhy
from .logging_policy import log_event

READ_COMPAT_FILE = "read_compat_builds.json"  # GU-2c list (starts empty; populated by T064)
WRITE_SUPPORTED_FILE = "write_supported_builds.json"  # GU-2a matrix (stays empty in F1)

# The runtime packages the plugin needs, as Hermes provides them (research R7).
RUNTIME_DEPENDENCIES: tuple[str, ...] = ("aiohttp", "cryptography")

# The module whose location marks the Hermes source root (research R8 step 1).
HERMES_ROOT_MARKER_MODULE = "hermes_constants"


class CompatStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


_SHA_RE = re.compile(r"[0-9a-f]{40}")
_FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")


def _check_hex(name: str, value: object, pattern: re.Pattern[str], optional: bool) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name} must be {'absent or ' if optional else ''}lowercase hex")


@dataclass(frozen=True)
class BuildIdentity:
    """GU-2c build identity of the running Hermes install (research R8 steps 2-3).

    The fingerprint is always present: it is always computed, and a missing listed file makes the
    build unidentifiable, so there is no identity at all (R8 step 5). A git SHA without a
    fingerprint is therefore not a valid identity and is rejected here (CS-19, IR-5).
    """

    fingerprint: str  # 64 lowercase hex over the read-bridge file list
    git_sha: str | None = None  # 40 lowercase hex from git metadata (no subprocess); None = no .git

    def __post_init__(self) -> None:
        _check_hex("fingerprint", self.fingerprint, _FINGERPRINT_RE, optional=False)
        _check_hex("git_sha", self.git_sha, _SHA_RE, optional=True)


@dataclass(frozen=True)
class BuildEntry:
    """One `read_compat_builds.json` entry (data-model.md)."""

    fingerprint: str
    git_sha: str | None  # None = a fingerprint-only entry (for installs without .git)
    label: str
    qualified_by: str
    qualified_at: str
    source_sha: str | None = None  # provenance only; never used for matching (R8 step 4)

    def __post_init__(self) -> None:
        _check_hex("fingerprint", self.fingerprint, _FINGERPRINT_RE, optional=False)
        _check_hex("git_sha", self.git_sha, _SHA_RE, optional=True)
        _check_hex("source_sha", self.source_sha, _SHA_RE, optional=True)


@dataclass(frozen=True)
class ReadCompatList:
    """The parsed `read_compat_builds.json`: data only. Matching is `match_build`'s job."""

    format: int
    bridge_files: tuple[str, ...]
    builds: tuple[BuildEntry, ...]


def match_build(identity: BuildIdentity, builds: Sequence[BuildEntry]) -> BuildEntry | None:
    """The CS-19 matching rule (research R8 step 4). Pure; the gate always uses this.

    - A git install (``identity.git_sha`` set) matches only an entry with that same `git_sha`
      whose fingerprint also equals the computed one. Fingerprint-only entries are never
      consulted, so a listed fingerprint never qualifies a git install at an unlisted SHA.
    - An install without git metadata matches only a fingerprint-only entry (`git_sha` None)
      with the same fingerprint. `source_sha` is provenance and plays no part.
    """
    for entry in builds:
        if entry.fingerprint != identity.fingerprint:
            continue
        if entry.git_sha == identity.git_sha:  # both None, or the same SHA
            return entry
    return None


@dataclass(frozen=True)
class CompatResult:
    status: CompatStatus
    why: OtherWhy | None = None  # an ERR-2a value when UNSUPPORTED
    identity: BuildIdentity | None = None
    entry: BuildEntry | None = None

    @property
    def supported(self) -> bool:
        return self.status is CompatStatus.SUPPORTED


class Compat(Protocol):
    """server-modules.md "Key protocols"."""

    def evaluate(self) -> CompatResult:
        """SUPPORTED | UNSUPPORTED(build_unsupported | read_dependency_missing)."""
        ...


class BuildIdentityReader(Protocol):
    def read(self, hermes_root: Path) -> BuildIdentity | None:
        """File reads only. `None` means unidentifiable. Implementation: T023."""
        ...


def load_read_compat_list(path: Path) -> ReadCompatList:
    """Parse `read_compat_builds.json` into data. Any malformed content raises."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: cannot read read-compat list: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") != 1:
        raise ValueError(f"{path}: missing or unsupported 'format'")
    bridge_files = raw.get("bridge_files")
    if not isinstance(bridge_files, list) or not all(isinstance(f, str) for f in bridge_files):
        raise ValueError(f"{path}: 'bridge_files' must be a list of strings")
    builds_raw = raw.get("builds")
    if not isinstance(builds_raw, list):
        raise ValueError(f"{path}: 'builds' must be a list")
    builds = tuple(_parse_build_entry(path, b) for b in builds_raw)
    return ReadCompatList(format=1, bridge_files=tuple(bridge_files), builds=builds)


def _parse_build_entry(path: Path, raw: object) -> BuildEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: each build entry must be an object")
    try:
        return BuildEntry(
            fingerprint=raw["fingerprint"],
            git_sha=raw.get("git_sha"),
            label=raw["label"],
            qualified_by=raw["qualified_by"],
            qualified_at=raw["qualified_at"],
            source_sha=raw.get("source_sha"),
        )
    except KeyError as exc:
        raise ValueError(f"{path}: build entry missing required field {exc}") from exc


# A dependency probe returns the names of missing or mis-shaped dependencies (empty = all present).
DependencyProbe = Callable[[], Sequence[str]]


def locate_hermes_root() -> Path | None:
    """Research R8 step 1: the Hermes source root, found without importing anything."""
    try:
        spec = importlib.util.find_spec(HERMES_ROOT_MARKER_MODULE)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    origin = Path(spec.origin)
    if not origin.is_file():
        return None
    return origin.parent


def runtime_dependencies_present() -> bool:
    """Passive `check_fn` for `register_platform`: are the runtime packages importable?"""
    try:
        return all(importlib.util.find_spec(name) is not None for name in RUNTIME_DEPENDENCIES)
    except (ImportError, ValueError):
        return False


# --------------------------------------------------------------------------------------------
# Research R8 steps 2-5: the real, file-reads-only build identity reader.
# --------------------------------------------------------------------------------------------

_UNRESOLVABLE = object()  # sentinel: `.git` exists but could not be resolved (R8 step 5)


class _GitDirs:
    """The worktree-local git dir (holds `HEAD`) and the common git dir (holds `refs`,
    `packed-refs` and `objects`) — the same directory unless `<root>/.git` points at a linked
    worktree (a `commondir` file)."""

    __slots__ = ("common", "worktree")

    def __init__(self, worktree: Path, common: Path) -> None:
        self.worktree = worktree
        self.common = common


def _resolve_gitdir(root: Path) -> _GitDirs:
    """`<root>/.git` as either a directory (a normal clone) or a file (`gitdir: <path>`, e.g. a
    linked worktree or a submodule) — file reads only, never a subprocess."""
    git_path = root / ".git"
    if git_path.is_dir():
        worktree = git_path
    elif git_path.is_file():
        text = git_path.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            raise ValueError(f"malformed .git file at {git_path}")
        pointed = text[len("gitdir:") :].strip()
        pointed_path = Path(pointed)
        worktree = (pointed_path if pointed_path.is_absolute() else root / pointed_path).resolve()
        if not worktree.is_dir():
            raise ValueError(f"gitdir {worktree} (from {git_path}) does not exist")
    else:
        raise ValueError(f"no .git at {root}")

    commondir_file = worktree / "commondir"
    if commondir_file.is_file():
        commondir = commondir_file.read_text(encoding="utf-8").strip()
        commondir_path = Path(commondir)
        common = (commondir_path if commondir_path.is_absolute() else worktree / commondir_path)
        return _GitDirs(worktree=worktree, common=common.resolve())
    return _GitDirs(worktree=worktree, common=worktree)


def _resolve_ref(dirs: _GitDirs, ref: str, *, _seen: frozenset[str] = frozenset()) -> str:
    """A ref such as `refs/heads/main` to a 40-hex commit SHA: a loose ref file (checked in the
    worktree-local dir first, then the common dir), falling back to `packed-refs` in the common
    dir. Follows a chain of symbolic refs, with a cycle guard."""
    if ref in _seen:
        raise ValueError(f"ref cycle detected at {ref!r}")
    for base in (dirs.worktree, dirs.common):
        loose = base / ref
        if loose.is_file():
            text = loose.read_text(encoding="utf-8").strip()
            if text.startswith("ref:"):
                return _resolve_ref(dirs, text[len("ref:") :].strip(), _seen=_seen | {ref})
            if _SHA_RE.fullmatch(text):
                return text
            raise ValueError(f"malformed ref file {loose}")
    packed = dirs.common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line[0] in "#^":
                continue
            sha, _, packed_ref = line.partition(" ")
            if packed_ref == ref and _SHA_RE.fullmatch(sha):
                return sha
    raise ValueError(f"unresolvable ref {ref!r}")


def resolve_git_head_sha(root: Path) -> str | None:
    """Research R8 step 2: HEAD resolved to a 40-hex SHA by reading git metadata only (no
    subprocess). `None` means `<root>/.git` itself is absent (`lstat` raises ENOENT): a valid
    "no git metadata" install. A present `.git` that cannot be resolved (a dangling symlink, an
    unreadable entry, a bad `.git` file pointer, loose ref, or `packed-refs`) raises `OSError` or
    `ValueError` — R8 step 5 treats that as unidentifiable, never as "no git"."""
    try:
        (root / ".git").lstat()  # lstat, not exists(): a dangling link is present, not absent
    except FileNotFoundError:
        return None
    dirs = _resolve_gitdir(root)
    head_text = (dirs.worktree / "HEAD").read_text(encoding="utf-8").strip()
    if not head_text:
        raise ValueError(f"empty HEAD at {dirs.worktree}")
    if head_text.startswith("ref:"):
        return _resolve_ref(dirs, head_text[len("ref:") :].strip())
    if _SHA_RE.fullmatch(head_text):
        return head_text  # detached HEAD
    raise ValueError(f"HEAD at {dirs.worktree} is neither a ref nor a SHA: {head_text!r}")


def compute_read_bridge_fingerprint(root: Path, bridge_files: Sequence[str]) -> str | None:
    """Research R8 step 3: SHA-256 over `path\\0len\\0bytes` for each file in `bridge_files`
    (sorted, so file order in the list never matters), read relative to `root`. `None` if any
    listed file is missing (R8 step 5: a missing listed file makes the build unidentifiable)."""
    digest = hashlib.sha256()
    for rel in sorted(bridge_files):
        try:
            data = (root / rel).read_bytes()
        except OSError:
            return None
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


class GitFingerprintReader:
    """The real `BuildIdentityReader` (research R8 steps 2-5): always computes the read-bridge
    fingerprint over `bridge_files`, and resolves a git SHA when `.git` is present. File reads
    only — no subprocess, no Hermes import. Returns `None` (unidentifiable) whenever any step
    fails or a listed file is missing, per R8 step 5's fail-closed rule."""

    def __init__(self, bridge_files: Sequence[str]) -> None:
        self._bridge_files = tuple(bridge_files)

    def read(self, hermes_root: Path) -> BuildIdentity | None:
        fingerprint = compute_read_bridge_fingerprint(hermes_root, self._bridge_files)
        if fingerprint is None:
            return None
        try:
            git_sha = resolve_git_head_sha(hermes_root)
        except (OSError, ValueError):
            return None  # `.git` present but unresolvable: unidentifiable (R8 step 5)
        try:
            return BuildIdentity(fingerprint=fingerprint, git_sha=git_sha)
        except ValueError:
            return None


@dataclass(frozen=True)
class DependencySpec:
    """One §12 internal the read bridge may reach: a module path, and an optional dotted
    attribute chain within it (e.g. `"GatewayRunner.served_profile_names"` — a class then one of
    its methods, resolved by `getattr` chaining, never by instantiating anything). `gap` is the
    HMP_V1.md §12 gap id, kept only for diagnostics."""

    module: str
    qualname: str | None = None
    gap: str = ""


# HMP_V1.md §12 "Hermes internals used", narrowed to the F1 read/roster/authorize subset (F1
# registers no write, submit, approval or clarify route — FR-053 — so the §12 rows that exist only
# for those, e.g. `tools.approval`/`tools.clarify_gateway`/`gateway.platforms.event`, are not
# reached by this build and are intentionally not probed here). `bridge.py` (T028) is free to
# extend this table as its actual reach is finalized; that never changes `CompatGate`'s evaluation
# order (server-modules.md "Startup order") since the probe is injected.
READ_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec("gateway.run", "GatewayRunner", gap="E-GAP-14"),
    DependencySpec(
        "gateway.run", "GatewayRunner._is_user_authorized_for_source", gap="E-GAP-22/25"
    ),
    DependencySpec("gateway.run", "_profile_runtime_scope", gap="E-GAP-14"),
    DependencySpec("gateway.run", "_async_profile_runtime_scope", gap="E-GAP-14"),
    DependencySpec(
        "gateway.run_profile_reconcile",
        "GatewayProfileReconcileMixin.served_profile_names",
        gap="E-GAP-14",
    ),
    DependencySpec(
        "gateway.run_adapters",
        "GatewayAdapterLifecycleMixin._routed_profile_home",
        gap="E-GAP-14/22/25",
    ),
    DependencySpec(
        "gateway.authz_mixin",
        "GatewayAuthorizationMixin._authorization_home_for_source",
        gap="E-GAP-22",
    ),
    DependencySpec("hermes_state_registry", "acquire", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB", gap="E-GAP-6/7"),
    DependencySpec("gateway.session", "build_session_key", gap="E-GAP-6"),
    DependencySpec("gateway.session", "SessionStore", gap="E-GAP-6"),
    DependencySpec("gateway.session", "SessionStore.lookup_by_session_key", gap="E-GAP-6"),
    DependencySpec("gateway.config", "load_gateway_config", gap="E-GAP-14"),
    DependencySpec("gateway.config", "Platform", gap="E-GAP-14"),
    DependencySpec("gateway.platforms._shared", "get_scoped_secret", gap="E-GAP-31"),
    DependencySpec("gateway.platforms._shared", "platform_gate_env", gap="E-GAP-31"),
    # T028: the rest of the bridge's real reach (`bridge.REACHED_METHODS` and `HermesApi`).
    DependencySpec("gateway.run", "GatewayRunner.served_profile_names", gap="E-GAP-14"),
    DependencySpec("gateway.run", "GatewayRunner._routed_profile_home", gap="E-GAP-14/22/25"),
    DependencySpec("gateway.platforms.base", "BasePlatformAdapter.build_source", gap="E-GAP-14"),
    DependencySpec("gateway.platforms.base", "BasePlatformAdapter.handle_message", gap="P6"),
    DependencySpec("gateway.platforms.event", "MessageEvent", gap="P2/P3 API"),
    DependencySpec("gateway.platforms.event", "MessageType", gap="P2/P3 API"),
    DependencySpec("hermes_state_registry", "release", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_messages", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_active_message_ids", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.resolve_resume_session_id", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_compression_chain", gap="E-GAP-6/7"),
    # Amendment A1 (session browsing, OD-F9/OD-F10; SES-1/SES-2). Both resolve, via
    # `inspect.getsourcefile`, to `hermes_state_sessions.py` -- already in `bridge_files` (it is
    # what `SessionDB.get_compression_chain`, `resolve_resume_session_id` and `get_active_message_
    # ids` above already require containment of via the sibling-mixin argument, and it is where
    # `get_compression_chain` itself and `get_session`/`list_sessions_rich` are all defined). No
    # file needs to be added to `bridge_files` for these two entries (A1 design doc §1.5): CS-21
    # containment is a property of `inspect.getsourcefile`, not of which entries name a file, and
    # this file is already listed. Fingerprints are therefore unchanged by this addition.
    DependencySpec("hermes_state", "SessionDB.list_sessions_rich", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_session", gap="E-GAP-6/7"),
)

# Amendment F2 (direct send, HMP_V1.md §7a DS-4/GAP-2): probed only when the owner-dogfood
# `direct_send` flag is on (gate.py's own `direct_send_gate`), never as part of the F1 startup
# gate above -- `CompatGate.evaluate()` itself is unchanged (server-modules.md "Startup order").
# `get_session_by_title` resolves, via `inspect.getsourcefile`, to the same `hermes_state_sessions.
# py` `get_session`/`list_sessions_rich` above already require containment of (A1's own
# reasoning, reused verbatim here) -- no NEW `bridge_files` entry for it. Only
# `active_session_registry_snapshot` is genuinely new: `hermes_cli/active_sessions.py` is not in
# the committed `bridge_files` list and must be added there for this probe to ever pass containment
# (`direct_send_supported_builds.json`, not `read_compat_builds.json` -- this is a write-path
# dependency, never needed for F1's reads).
# Review BLOCKER #2 (round 2): `get_compression_lineage` resolves, via `inspect.getsourcefile`, to
# `hermes_state_compression.py` -- already in `bridge_files` (required by `READ_DEPENDENCIES`'s own
# `SessionDB.get_compression_chain` entry above). No new `bridge_files` entry needed for it either.
DIRECT_SEND_DEPENDENCIES: tuple[DependencySpec, ...] = (
    # F3 security behavior reached indirectly through Phone delivery and loopback HTTP.
    # Keep the defining modules AND delegated implementations in the fingerprint; import
    # signatures alone cannot prove these contracts. tools/compat/approval_probes.py exercises
    # the control gate and exact-ID resolution during qualification.
    DependencySpec("gateway.platforms.event", "MessageEvent.is_command", gap="F3 control"),
    DependencySpec(
        "gateway.platforms.base", "BasePlatformAdapter.handle_message", gap="F3 control"
    ),
    DependencySpec("gateway.run_busy", "GatewayBusySessionMixin", gap="F3 busy control"),
    DependencySpec("gateway.run_inbound", "GatewayInboundMixin", gap="F3 clarify control"),
    DependencySpec("gateway.run_turn_runner", "TurnRunner", gap="F3 prompt delivery"),
    DependencySpec("tools.approval_gateway_wait", "_poll_event", gap="F3 timeout"),
    DependencySpec("tools.approval_human_wait", "human_wait_window", gap="F3 wait lifecycle"),
    DependencySpec("tools.interrupt", "is_interrupted", gap="F3 interrupted wait"),
    DependencySpec("gateway.platforms.api_server", "APIServerAdapter", gap="F3 stream/auth"),
    DependencySpec("gateway.platforms.api_server_runs", "_handle_run_approval", gap="F3 exact ID"),
    DependencySpec("gateway.platforms.api_server_room_grants", gap="F3 run authorization"),
    DependencySpec("gateway.platforms.api_server_run_idempotency", gap="F3 run ownership"),
    DependencySpec("hermes_cli.profiles", gap="F3 profile scoping"),
    DependencySpec("hermes_constants", "get_hermes_home", gap="F3 profile home"),
    DependencySpec("gateway.pairing", "PairingStore.is_approved", gap="F3 authorization"),
    DependencySpec("agent.secret_scope", gap="F3 scoped API key"),
    DependencySpec("hermes_cli.auth", "has_usable_secret", gap="F3 scoped API key"),
    DependencySpec(
        "hermes_cli.active_sessions", "active_session_registry_snapshot", gap="E-GAP-6/7"
    ),
    DependencySpec("hermes_state", "SessionDB.get_session_by_title", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_compression_lineage", gap="E-GAP-6/7"),
    # Amendment F3 (HMP_V1.md §7b AP-4/AP-9). Probed only with the direct-send gate, and only
    # after `direct_send_supported_builds.json` still matches. Not part of the read probe.
    DependencySpec("tools.approval", "resolve_gateway_approval", gap="E-GAP-9"),
    DependencySpec("tools.approval", "list_gateway_approvals", gap="E-GAP-9"),
    DependencySpec("tools.clarify_gateway", "resolve_gateway_clarify", gap="E-GAP-9/20"),
    DependencySpec("tools.clarify_gateway", "mark_awaiting_text", gap="E-GAP-9/20"),
    DependencySpec("tools.clarify_gateway", "get_clarify_timeout", gap="E-GAP-9/20"),
    DependencySpec("tools.approval_context", "_get_approval_timeout", gap="E-GAP-9"),
)

_DIRECT_SEND_LIST = Path(__file__).resolve().parent / "direct_send_supported_builds.json"
_direct_send_qualified_cache: bool | None = None


def direct_send_build_qualified() -> bool:
    """T4: fingerprint + probe against `direct_send_supported_builds.json`.

    A stale fingerprint (the F3 `bridge_files` growth, before a human requalifies the row)
    returns False and does not import the new modules. The result is cached for the process.
    """
    global _direct_send_qualified_cache
    if _direct_send_qualified_cache is not None:
        return _direct_send_qualified_cache
    ok = _direct_send_build_qualified()
    _direct_send_qualified_cache = ok
    if not ok:
        log_event("direct_send", outcome="unqualified")
    return ok


def _direct_send_build_qualified() -> bool:
    try:
        compat_list = load_read_compat_list(_DIRECT_SEND_LIST)
    except (OSError, ValueError):
        return False
    root = locate_hermes_root()
    if root is None:
        return False
    # getattr, not `.bridge_files`: compat.py's source must not contain the substring ".bridge".
    files = getattr(compat_list, "bridge_files")  # noqa: B009
    identity = GitFingerprintReader(files).read(root)
    if identity is None or match_build(identity, compat_list.builds) is None:
        return False
    missing = probe_direct_send_dependencies(hermes_root=root, bridge_files=files)
    return not missing


def probe_direct_send_dependencies(
    *,
    hermes_root: Path | None = None,
    bridge_files: Sequence[str] = (),
) -> Sequence[str]:
    """DS-2(b)/GAP-2: the same shape-and-containment probe as `probe_read_dependencies`, run
    against `DIRECT_SEND_DEPENDENCIES` instead. Non-empty result means the guarded write gate
    must stay closed for this build -- never a partial "some direct-send features work"."""
    return probe_read_dependencies(
        hermes_root=hermes_root, bridge_files=bridge_files, specs=DIRECT_SEND_DEPENDENCIES
    )


# Draft approval qualification lane (specs/004-approval-qualification-lane). Independent of both
# the read and the guarded-send lanes: its own dependency table, its own list file, its own gate.
# `approval_supported_builds.json` ships EMPTY, so `approval_build_qualified` is False for every
# build until a human qualifies one with behavioral evidence. The adapter binds this gate (with
# `result.supported`) into the prompt routes, the send-stream binding and the producer hooks, and
# `hermes hmp compat` reports it read-only. The send dependencies remain unchanged.
APPROVAL_COMPAT_FILE = "approval_supported_builds.json"

APPROVAL_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec("agent.secret_scope", gap="F3 scoped API key"),
    DependencySpec("tools.approval", "resolve_gateway_approval", gap="E-GAP-9"),
    DependencySpec("tools.approval", "list_gateway_approvals", gap="E-GAP-9"),
    DependencySpec("tools.approval_context", "_get_approval_timeout", gap="E-GAP-9"),
    DependencySpec("tools.approval_gateway_wait", "_poll_event", gap="F3 timeout"),
    DependencySpec("tools.approval_human_wait", "human_wait_window", gap="F3 wait lifecycle"),
    DependencySpec("tools.interrupt", "is_interrupted", gap="F3 interrupted wait"),
    DependencySpec("tools.clarify_gateway", "resolve_gateway_clarify", gap="E-GAP-9/20"),
    DependencySpec("tools.clarify_gateway", "mark_awaiting_text", gap="E-GAP-9/20"),
    DependencySpec("tools.clarify_gateway", "get_clarify_timeout", gap="E-GAP-9/20"),
    DependencySpec("gateway.platforms.event", "MessageEvent.is_command", gap="F3 control"),
    DependencySpec(
        "gateway.platforms.base", "BasePlatformAdapter.handle_message", gap="F3 control"
    ),
    DependencySpec("gateway.run_busy", "GatewayBusySessionMixin", gap="F3 busy control"),
    DependencySpec("gateway.run_inbound", "GatewayInboundMixin", gap="F3 clarify control"),
    DependencySpec("gateway.run_turn_runner", "TurnRunner", gap="F3 prompt delivery"),
    DependencySpec("gateway.platforms.api_server", "APIServerAdapter", gap="F3 stream/auth"),
    DependencySpec("gateway.platforms.api_server_runs", "_handle_run_approval", gap="F3 exact ID"),
    DependencySpec("gateway.platforms.api_server_room_grants", gap="F3 run authorization"),
    DependencySpec("gateway.platforms.api_server_run_idempotency", gap="F3 run ownership"),
    DependencySpec("gateway.pairing", "PairingStore.is_approved", gap="F3 authorization"),
    DependencySpec("hermes_cli.auth", "has_usable_secret", gap="F3 scoped API key"),
    DependencySpec("hermes_cli.profiles", gap="F3 profile scoping"),
    DependencySpec("hermes_constants", "get_hermes_home", gap="F3 profile home"),
)


def probe_approval_dependencies(
    *,
    hermes_root: Path | None = None,
    bridge_files: Sequence[str] = (),
) -> Sequence[str]:
    """The shape-and-containment probe run against `APPROVAL_DEPENDENCIES`. Non-empty means the
    approval lane stays closed for this build."""
    return probe_read_dependencies(
        hermes_root=hermes_root, bridge_files=bridge_files, specs=APPROVAL_DEPENDENCIES
    )


def _load_approval_manifest(compat_path: Path | None) -> ReadCompatList:
    path = (
        compat_path if compat_path is not None else Path(__file__).with_name(APPROVAL_COMPAT_FILE)
    )
    return load_read_compat_list(path)


def approval_build_qualified(
    read_identity: BuildIdentity | None,
    *,
    hermes_root: Path | None = None,
    compat_path: Path | None = None,
) -> bool:
    """One-shot, INFORMATIONAL exact check of the source currently on disk (`hermes hmp compat`).

    This is NOT listener-bound admission: it has no startup baseline, so it cannot notice that the
    files on disk changed after a process started. Production routes use
    `approval_listener_qualifier` instead. Order matters: the list is loaded and checked for an
    entry first, so an empty list (the shipped state) returns False before any Hermes file is read
    or module imported. The approval fingerprint is then recomputed over this lane's own
    `bridge_files`, the Git SHA must equal the read identity's, an exact list entry must match, and
    only then are `APPROVAL_DEPENDENCIES` probed. A malformed or missing list, a missing listed
    file, a moved SHA, no exact match or any probe error returns False. Never consults the
    guarded-send list or gate.
    """
    if not isinstance(read_identity, BuildIdentity):
        return False
    try:
        qualified = _load_approval_manifest(compat_path)
        if not qualified.builds:
            return False
        root = hermes_root if hermes_root is not None else locate_hermes_root()
        if root is None:
            return False
        approval_files = getattr(qualified, "bridge_files")  # noqa: B009
        if not approval_files:
            return False
        identity = GitFingerprintReader(approval_files).read(root)
        if identity is None or identity.git_sha != read_identity.git_sha:
            return False
        if match_build(identity, qualified.builds) is None:
            return False
        return not probe_approval_dependencies(hermes_root=root, bridge_files=approval_files)
    except Exception:
        return False


@dataclass(frozen=True)
class ApprovalProcessBaseline:
    """What this PROCESS admitted approvals with: the exact source root, the ordered read and
    approval file lists, the read and approval fingerprints and the git SHA. A callback opens only
    while the CURRENT source still equals this, so an in-place change to another (even
    also-qualified) build stays closed until the gateway process restarts."""

    root: Path
    read_files: tuple[str, ...]
    read_fingerprint: str
    files: tuple[str, ...]
    fingerprint: str
    git_sha: str | None


# The process-level admission latch, independent of the probe cache below. `None` = not yet
# initialised; `(None,)` = closed for the life of the process; `(baseline,)` = the one baseline any
# later listener must equal. It is written once, under the lock, by the FIRST supported factory
# call, so a listener reconnect can never redefine the startup source. There is deliberately no
# public reset and no env override: only a full gateway process restart (a fresh import of this
# module) clears it, and tests monkeypatch it. It cannot defend against an in-process unload or
# reimport of this module, which resets it (a documented limit, not claimed protection).
_approval_process_latch: tuple[ApprovalProcessBaseline | None] | None = None
_approval_latch_lock = threading.Lock()


# Successful dependency probes only, oldest first. Isolated from `_direct_send_qualified_cache`.
# The key is the full source identity, so a changed file, SHA, list or root can never reuse a pass;
# the manifest, fingerprint and SHA are still recomputed on EVERY callback (no TTL on revocation).
_APPROVAL_PROBE_CACHE_MAX = 8
_approval_probe_cache: dict[tuple[str, tuple[str, ...], str, str | None], None] = {}
_approval_probe_lock = threading.Lock()


def _approval_probe_passed(
    root: Path, files: tuple[str, ...], fingerprint: str, git_sha: str | None
) -> bool:
    key = (str(root), files, fingerprint, git_sha)
    with _approval_probe_lock:
        if key in _approval_probe_cache:
            del _approval_probe_cache[key]  # re-inserted below to refresh recency
            _approval_probe_cache[key] = None
            return True
        if probe_approval_dependencies(hermes_root=root, bridge_files=files):
            return False  # failures are never cached: the next callback probes again
        _approval_probe_cache[key] = None
        while len(_approval_probe_cache) > _APPROVAL_PROBE_CACHE_MAX:
            del _approval_probe_cache[next(iter(_approval_probe_cache))]
        return True


def _approval_closed() -> bool:
    return False


def _capture_approval_baseline(
    read_identity: BuildIdentity,
    hermes_root: Path | None,
    compat_path: Path | None,
    read_compat_path: Path | None,
) -> ApprovalProcessBaseline | None:
    """The candidate baseline for the source on disk right now, or None when any admission
    precondition fails. The approval list is checked for an entry BEFORE any Hermes file is
    located, read or imported."""
    try:
        startup = _load_approval_manifest(compat_path)
        files = tuple(getattr(startup, "bridge_files"))  # noqa: B009
        if not startup.builds or not files:
            return None
        read_list = load_read_compat_list(
            read_compat_path if read_compat_path is not None else _DEFAULT_READ_COMPAT_PATH
        )
        read_files = tuple(getattr(read_list, "bridge_files"))  # noqa: B009
        if not read_files or not set(read_files) <= set(files):
            return None
        root = hermes_root if hermes_root is not None else locate_hermes_root()
        if root is None:
            return None
        root = root.resolve()
        # Cross-check the read gate's identity against the same read files read fresh now. This
        # narrows the window since the compat evaluation; it does not make it atomic.
        fresh_read = GitFingerprintReader(read_files).read(root)
        if (
            fresh_read is None
            or fresh_read.fingerprint != read_identity.fingerprint
            or fresh_read.git_sha != read_identity.git_sha
        ):
            return None
        started = GitFingerprintReader(files).read(root)
        if started is None or started.git_sha != read_identity.git_sha:
            return None
        # A source that started unlisted can never be opened by a later manifest edit.
        if match_build(started, startup.builds) is None:
            return None
        return ApprovalProcessBaseline(
            root, read_files, fresh_read.fingerprint, files, started.fingerprint, started.git_sha
        )
    except Exception:
        return None


def approval_listener_qualifier(
    read_identity: BuildIdentity | None,
    *,
    hermes_root: Path | None = None,
    compat_path: Path | None = None,
    read_compat_path: Path | None = None,
) -> Callable[[], bool]:
    """Build a listener's approval admission callback, only for a supported read build (blocking:
    it may read files).

    The FIRST call in a process fixes the process-level baseline (`_approval_process_latch`); a
    later call (a listener reconnect) opens only if the source now on disk equals that baseline
    exactly, and never redefines it. An empty, malformed or missing manifest, an unlisted startup
    source, an unidentifiable source, a read fingerprint or SHA that differs from `read_identity`,
    or approval files that do not cover the read files make the first call latch the process
    CLOSED: adding a manifest entry then needs a full gateway process restart, not a listener
    restart. With an empty list no Hermes file is inspected or imported.

    The returned callback, per call: reloads the manifest, recomputes the fingerprint and SHA,
    requires root, ordered list, fingerprint and SHA to equal the baseline, requires a current
    exact list entry (so removal closes at once and restoring the startup entry may reopen), then
    runs the probe once per identity via a bounded success-only cache. Any error is False.
    """
    global _approval_process_latch
    if not isinstance(read_identity, BuildIdentity):
        return _approval_closed
    with _approval_latch_lock:
        latch = _approval_process_latch
        if latch is not None and latch[0] is None:
            return _approval_closed
        candidate = _capture_approval_baseline(
            read_identity, hermes_root, compat_path, read_compat_path
        )
        if latch is None:
            _approval_process_latch = (candidate,)
        if candidate is None or (latch is not None and candidate != latch[0]):
            return _approval_closed
        baseline = candidate

    def qualified() -> bool:
        try:
            current = _load_approval_manifest(compat_path)
            current_files = tuple(getattr(current, "bridge_files"))  # noqa: B009
            if not current.builds or current_files != baseline.files:
                return False
            now_root = hermes_root if hermes_root is not None else locate_hermes_root()
            if now_root is None or now_root.resolve() != baseline.root:
                return False
            fresh = GitFingerprintReader(current_files).read(baseline.root)
            if (
                fresh is None
                or fresh.fingerprint != baseline.fingerprint
                or fresh.git_sha != baseline.git_sha
                or match_build(fresh, current.builds) is None
            ):
                return False
            return _approval_probe_passed(
                baseline.root, current_files, fresh.fingerprint, fresh.git_sha
            )
        except Exception:
            return False

    return qualified


def _resolve_qualname(module: object, qualname: str) -> object:
    obj: object = module
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


def _safe_getsourcefile(obj: object) -> str | None:
    """The file that defines `obj` (module-level objects only; never unwraps -- a module has no
    `__wrapped__` chain to walk)."""
    try:
        return inspect.getsourcefile(obj)  # type: ignore[arg-type]
    except TypeError:
        return None


def _wrapper_chain_source_files(
    obj: object, *, _seen: frozenset[int] = frozenset()
) -> tuple[str, ...] | None:
    """SR-3 (CS-21): every source file in `obj`'s `__wrapped__` chain, outermost first -- what
    actually runs is the OUTERMOST wrapper, not just the innermost function `inspect.unwrap`
    resolves to, so every layer must be checked, not only the last one. `None` (never a fallback
    to some other file) when any layer's file cannot be determined, or a `__wrapped__` cycle is
    found."""
    if id(obj) in _seen:
        return None  # a cycle: `inspect.unwrap` would raise ValueError here; treat it as missing
    try:
        source = inspect.getsourcefile(obj)  # type: ignore[arg-type]
    except TypeError:
        return None
    if source is None:
        return None
    wrapped = getattr(obj, "__wrapped__", None)
    if wrapped is None:
        return (source,)
    rest = _wrapper_chain_source_files(wrapped, _seen=_seen | {id(obj)})
    if rest is None:
        return None
    return (source, *rest)


def _stdlib_dir() -> Path:
    path = sysconfig.get_paths().get("stdlib")
    return Path(path).resolve() if path else Path(os.devnull)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _source_in_bridge_files(source: str | None, root: Path, allowed: frozenset[str]) -> bool:
    if source is None:
        return False
    try:
        rel = Path(source).resolve().relative_to(root)
    except ValueError:
        return False
    return rel.as_posix() in allowed


def _chain_contained(
    files: Sequence[str], root: Path, allowed: frozenset[str], stdlib_dir: Path
) -> bool:
    """Every layer's file must be in `bridge_files`, or under the stdlib (SR-3): a Hermes-defined
    decorator (e.g. `functools.wraps`-based) living outside `bridge_files` must never pass just
    because the innermost function it wraps happens to be listed."""
    for source in files:
        if _source_in_bridge_files(source, root, allowed):
            continue
        try:
            resolved = Path(source).resolve()
        except OSError:
            return False
        if not _is_under(resolved, stdlib_dir):
            return False
    return True


def probe_read_dependencies(
    *,
    hermes_root: Path | None = None,
    bridge_files: Sequence[str] = (),
    specs: Sequence[DependencySpec] = READ_DEPENDENCIES,
) -> Sequence[str]:
    """Research R8 step 6: import each bridge dependency and check its signature shape without
    calling it, and (when `bridge_files` is given) that `inspect.getsourcefile` of everything
    reached is contained in it (CS-21). Returns the label of each dependency that is missing,
    mis-shaped, or resolves outside `bridge_files`. The only function outside `bridge.py` allowed
    to import Hermes modules dynamically (`tools/ci/check_plugin_surface.py` enforces that); it is
    called only after a listed build has matched (`CompatGate.evaluate` step 4).

    `hermes_root` defaults to `locate_hermes_root()`; `bridge_files` defaults to empty, which
    skips the containment check (there is nothing to contain it in) — `default_gate()` always
    supplies both from the loaded `read_compat_builds.json`.
    """
    root = hermes_root if hermes_root is not None else locate_hermes_root()
    resolved_root = root.resolve() if root is not None else None
    allowed = frozenset(bridge_files)
    missing: list[str] = []

    for spec in specs:
        label = f"{spec.module}.{spec.qualname}" if spec.qualname else spec.module
        try:
            module = importlib.import_module(spec.module)
        except Exception:
            missing.append(label)
            continue

        module_source = _safe_getsourcefile(module)
        if (
            allowed
            and resolved_root is not None
            and not _source_in_bridge_files(module_source, resolved_root, allowed)
        ):
            missing.append(label)
            continue

        if spec.qualname is None:
            continue

        try:
            obj = _resolve_qualname(module, spec.qualname)
        except AttributeError:
            missing.append(label)
            continue

        if not (inspect.isclass(obj) or callable(obj)):
            missing.append(label)
            continue
        try:
            inspect.signature(obj)  # shape only; never called
        except (TypeError, ValueError):
            missing.append(label)
            continue

        if allowed and resolved_root is not None:
            chain_files = _wrapper_chain_source_files(obj)
            # SR-3: an undeterminable chain (a cycle, or any layer whose file cannot be found --
            # a `functools.partial`, a callable instance, a C function) is MISSING. It never
            # falls back to `module_source`: that fallback is exactly what let an
            # unidentifiable object pass just because its enclosing module happened to be listed.
            if chain_files is None or not _chain_contained(
                chain_files, resolved_root, allowed, _stdlib_dir()
            ):
                missing.append(label)

    return tuple(missing)


class CompatGate:
    """The `Compat` implementation. The evaluation order and the CS-19 matching rule are fixed
    here. The identity reader, the list data and the probe are injected so each step can be
    tested alone."""

    def __init__(
        self,
        identity_reader: BuildIdentityReader,
        compat_list: ReadCompatList,
        probe: DependencyProbe = probe_read_dependencies,
        root_locator: Callable[[], Path | None] = locate_hermes_root,
    ) -> None:
        self._identity_reader = identity_reader
        self._compat_list = compat_list
        self._probe = probe
        self._root_locator = root_locator

    def evaluate(self) -> CompatResult:
        unsupported = CompatStatus.UNSUPPORTED
        build_unsupported = OtherWhy.HERMES_BUILD_UNSUPPORTED

        # Steps 1-3: file reads only. Any failure is an unidentifiable build (fail closed).
        try:
            root = self._root_locator()
            identity = self._identity_reader.read(root) if root is not None else None
            if not isinstance(identity, BuildIdentity):
                return CompatResult(unsupported, build_unsupported)
            identity.__post_init__()  # re-validate: never trust the injected reader's object
            entry = match_build(identity, self._compat_list.builds)
        except Exception:
            return CompatResult(unsupported, build_unsupported)
        if entry is None:
            return CompatResult(unsupported, build_unsupported, identity)

        # Step 4: listed build only.
        try:
            missing = self._probe()
        except Exception:
            missing = ("<probe failed>",)
        if missing:
            return CompatResult(
                unsupported, OtherWhy.HERMES_READ_DEPENDENCY_MISSING, identity, entry
            )
        return CompatResult(CompatStatus.SUPPORTED, None, identity, entry)


_DEFAULT_READ_COMPAT_PATH = Path(__file__).with_name(READ_COMPAT_FILE)


def default_gate(*, read_compat_path: Path | None = None) -> CompatGate:
    """The production gate: `GitFingerprintReader` over the on-disk `read_compat_builds.json`
    (defaulting to the file next to this module), and a probe that checks CS-21 containment
    against that same file's `bridge_files` list."""
    path = read_compat_path if read_compat_path is not None else _DEFAULT_READ_COMPAT_PATH
    compat_list = load_read_compat_list(path)
    # `getattr(...)`, not `compat_list.bridge_files`: `test_compat_module_source_never_names_
    # bridge` greps this file's source for the literal substring ".bridge" as a cheap guard
    # against a `bridge.py` import creeping in, and a dotted access on the `bridge_files` field
    # would otherwise false-positive that check.
    bridge_files = getattr(compat_list, "bridge_files")  # noqa: B009
    reader = GitFingerprintReader(bridge_files)

    def probe() -> Sequence[str]:
        return probe_read_dependencies(bridge_files=bridge_files)

    return CompatGate(reader, compat_list, probe)
