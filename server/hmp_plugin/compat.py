"""Minimum-version eligibility (owner policy 2026-10-01; GU-2, GU-2c, ERR-2a).

`evaluate_eligibility()` is the single runtime decision for every Hermes-dependent feature. Its
order is mandatory:

1. Locate the Hermes source root with `importlib.util.find_spec("hermes_constants").origin`.
   This imports nothing. No root means every feature is unavailable (`hermes_not_found`).
2. Read the Hermes version with file reads only (`hermes_version.read_hermes_version`).
3. A feature whose own floor the version declares itself below is unavailable
   (`hermes_version_below_floor`). When read is below its floor, return at once **without
   importing any Hermes module**. An unknown, unreleased or newer version is never refused on
   version grounds: it is attempted, subject to the probes below.
4. Probe the read core dependencies (import and signature inspection, no calls). If one is
   actually missing, read is unavailable and every other feature is `requires_read`: they all use
   the bridge's authorization, profile-home and profile-scope primitives.
5. Independently probe each other feature's own dependencies. One feature's missing dependency
   never closes another.
6. Exact build fingerprints and git SHAs are read only as test evidence (`tested_label`). No gate
   reads that field.

`probe_dependencies` is the only function outside `bridge.py` allowed to import Hermes modules
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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from . import hermes_version
from .contract import OtherWhy

# The tested-sample manifests are EVIDENCE only (owner policy 2026-10-01): they describe the
# builds a fixture or native run covered and never admit or refuse a build at runtime.
READ_COMPAT_FILE = "read_compat_builds.json"  # tested read samples
WRITE_SUPPORTED_FILE = "write_supported_builds.json"  # GU-2a matrix (stays empty in F1)
DIRECT_SEND_COMPAT_FILE = "direct_send_supported_builds.json"  # tested send samples
CRON_COMPAT_FILE = "mobile_cron_supported_builds.json"  # tested jobs samples
MODEL_COMPAT_FILE = "mobile_model_supported_builds.json"  # tested model samples

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
    entry: BuildEntry | None = None  # tested-sample evidence only; never read by a gate
    eligibility: Eligibility | None = None

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
    subprocess). `None` means no `.git` at all (a valid "no git metadata" install). Any other
    failure (a `.git` file pointer, loose ref, or `packed-refs` that cannot be resolved) raises
    `ValueError` — R8 step 5 treats that as unidentifiable, never as "no git"."""
    if not (root / ".git").exists():
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
    """One Hermes internal a feature may reach: a module path, and an optional dotted attribute
    chain within it (e.g. `"GatewayRunner.served_profile_names"` -- a class then one of its
    methods, resolved by `getattr` chaining, never by instantiating anything). `gap` is the
    HMP_V1.md §12 gap id, kept only for diagnostics.

    `params` names parameters the callable must declare as real `POSITIONAL_OR_KEYWORD` or
    `KEYWORD_ONLY` parameters. A `**kwargs` catch-all never satisfies a name: a writer that
    silently swallowed `paused` would create an active job. `min_positional` is the number of
    leading positional parameters the callable must accept."""

    module: str
    qualname: str | None = None
    gap: str = ""
    params: frozenset[str] = frozenset()
    min_positional: int = 0


# HMP_V1.md §12 "Hermes internals used" by the read/roster/authorize bridge. If any row here is
# actually missing, the bridge cannot authorize or route anything and read is unavailable.
READ_CORE_DEPENDENCIES: tuple[DependencySpec, ...] = (
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
)

# Session browsing (amendment A1, SES-1/SES-2) depends on two further SessionDB methods. Their
# absence closes only the session routes (404), never the rest of read.
SESSION_BROWSING_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec("hermes_state", "SessionDB.list_sessions_rich", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_session", gap="E-GAP-6/7"),
)

# Everything the read bridge and session browsing reach (kept for tooling and the reach test).
READ_DEPENDENCIES: tuple[DependencySpec, ...] = (
    READ_CORE_DEPENDENCIES + SESSION_BROWSING_DEPENDENCIES
)

# Amendment F2 (direct send, HMP_V1.md §7a DS-4/GAP-2).
DIRECT_SEND_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec(
        "hermes_cli.active_sessions", "active_session_registry_snapshot", gap="E-GAP-6/7"
    ),
    DependencySpec("hermes_state", "SessionDB.get_session", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_session_by_title", gap="E-GAP-6/7"),
    DependencySpec("hermes_state", "SessionDB.get_compression_lineage", gap="E-GAP-6/7"),
)

# Mobile jobs (`bridge.create_mobile_cron` / `edit_mobile_cron`). The scheduler wrapper forwards
# `**kwargs` to `cron.jobs.create_job`, so the named-parameter check (`paused` above all) is made on
# the writer that actually defines them. `HermesApi.create_mobile_cron` always passes `paused=True`.
CRON_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec("cron.scheduler", "create_job_with_scheduler_registration"),
    DependencySpec(
        "cron.jobs",
        "create_job",
        params=frozenset(
            {"name", "schedule", "prompt", "deliver", "paused", "repeat", "context_from"}
        ),
    ),
    DependencySpec("tools.cronjob_prompt_scan", "_scan_cron_prompt"),
    DependencySpec("cron.jobs", "get_job"),
    DependencySpec("cron.jobs", "update_job"),
    DependencySpec("cron.lifecycle_guard", "check_gateway_lifecycle"),
    DependencySpec("cron.scheduler", "_notify_provider_jobs_changed"),
)

# Bot default model (`bridge.model_config` / `write_profile_model`). `fastapi` is a third-party
# package and is deliberately not probed: a missing one fails the call and is already mapped to
# `model_unavailable`.
MODEL_DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec("hermes_cli.config", "load_config"),
    DependencySpec(
        "hermes_cli.web_routers.profiles", "_write_profile_model", min_positional=3
    ),
)


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


_THIRD_PARTY_DIRS = frozenset({"site-packages", "dist-packages"})


def _stdlib_dir() -> Path:
    path = sysconfig.get_paths().get("stdlib")
    return Path(path).resolve() if path else Path(os.devnull)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _hermes_home_plugins() -> Path | None:
    home = os.environ.get("HERMES_HOME")
    if not home:
        return None
    try:
        return (Path(home) / "plugins").resolve()
    except OSError:
        return None


def _source_contained(
    source: str | None, root: Path, stdlib_dir: Path, plugins_dir: Path | None
) -> bool:
    """CS-21 containment: a source file counts only when it lives in the Hermes tree or the
    standard library, outside any `site-packages`/`dist-packages` directory and outside the Hermes
    home's `plugins` directory. This rejects a shadow module installed into the environment or
    shipped by another plugin, and does not depend on which Hermes file defines the symbol."""
    if source is None:
        return False
    try:
        resolved = Path(source).resolve()
    except OSError:
        return False
    if plugins_dir is not None and _is_under(resolved, plugins_dir):
        return False
    for base in (root, stdlib_dir):
        if _is_under(resolved, base):
            return not _THIRD_PARTY_DIRS & set(resolved.relative_to(base).parts)
    return False


def _chain_contained(
    files: Sequence[str], root: Path, stdlib_dir: Path, plugins_dir: Path | None
) -> bool:
    """Every layer's file must be contained (SR-3): a decorator living outside the Hermes tree
    must never pass just because the innermost function it wraps is inside it."""
    return all(_source_contained(f, root, stdlib_dir, plugins_dir) for f in files)


def _signature_satisfies(obj: object, spec: DependencySpec) -> bool:
    """The callable's own signature: required parameter names are real named parameters (a
    `**kwargs` never counts) and enough leading positional parameters exist."""
    try:
        parameters = inspect.signature(obj).parameters  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if spec.params:
        named = {
            name
            for name, p in parameters.items()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        }
        if not spec.params <= named:
            return False
    if spec.min_positional:
        positional = [
            p
            for p in parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional) < spec.min_positional:
            return False
    return True


def probe_dependencies(
    *,
    hermes_root: Path | None = None,
    specs: Sequence[DependencySpec] = READ_CORE_DEPENDENCIES,
) -> Sequence[str]:
    """Import each dependency and check its signature shape without calling it, and that
    `inspect.getsourcefile` of everything reached is contained in the Hermes tree or the standard
    library (CS-21). Returns the label of each dependency that is missing, mis-shaped, or resolves
    outside that containment. With no locatable Hermes root nothing can be contained, so every
    label is reported. The only function outside `bridge.py` allowed to import Hermes modules
    dynamically (`tools/ci/check_plugin_surface.py` enforces that); the eligibility function calls
    it only when a feature's version floor is met.
    """
    root = hermes_root if hermes_root is not None else locate_hermes_root()
    labels = [f"{s.module}.{s.qualname}" if s.qualname else s.module for s in specs]
    if root is None:
        return tuple(labels)
    resolved_root = root.resolve()
    stdlib_dir = _stdlib_dir()
    plugins_dir = _hermes_home_plugins()
    missing: list[str] = []

    for spec, label in zip(specs, labels, strict=True):
        try:
            module = importlib.import_module(spec.module)
        except Exception:
            missing.append(label)
            continue

        if not _source_contained(
            _safe_getsourcefile(module), resolved_root, stdlib_dir, plugins_dir
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
        if not _signature_satisfies(obj, spec):  # shape only; never called
            missing.append(label)
            continue

        # SR-3: an undeterminable chain (a cycle, or any layer whose file cannot be found -- a
        # `functools.partial`, a callable instance, a C function) is MISSING. It never falls back
        # to `module_source`.
        chain_files = _wrapper_chain_source_files(obj)
        if chain_files is None or not _chain_contained(
            chain_files, resolved_root, stdlib_dir, plugins_dir
        ):
            missing.append(label)

    return tuple(missing)


def probe_direct_send_dependencies(*, hermes_root: Path | None = None) -> Sequence[str]:
    """DS-2(b)/GAP-2: the same probe run against `DIRECT_SEND_DEPENDENCIES`. A non-empty result
    means the guarded write gate stays closed -- never a partial "some send features work"."""
    return probe_dependencies(hermes_root=hermes_root, specs=DIRECT_SEND_DEPENDENCIES)


# --------------------------------------------------------------------------------------------
# Eligibility
# --------------------------------------------------------------------------------------------


class Feature(StrEnum):
    """The closed set of version-gated features. There is deliberately no media and no approvals
    member: reaching a floor never implies either is allowed."""

    READ = "read"
    SESSION_BROWSING = "session_browsing"
    SEND = "send"
    JOBS = "jobs"
    MODEL = "model"


class Unavailable(StrEnum):
    """Fixed reason codes; the only failure text that is ever logged or reported."""

    HERMES_NOT_FOUND = "hermes_not_found"
    VERSION_BELOW_FLOOR = "hermes_version_below_floor"
    DEPENDENCY_MISSING = "dependency_missing"
    PROBE_FAILED = "probe_failed"
    REQUIRES_READ = "requires_read"


@dataclass(frozen=True)
class FeatureStatus:
    available: bool
    reason: Unavailable | None = None
    # Labels from HMP's own dependency tables only; never Hermes-provided text.
    missing: tuple[str, ...] = ()
    # Evidence: the tested-sample label, or None. NEVER read by a gate.
    tested_label: str | None = None


@dataclass(frozen=True)
class Eligibility:
    version: hermes_version.HermesVersion
    git_sha: str | None  # evidence only
    features: Mapping[Feature, FeatureStatus]

    def available(self, feature: Feature) -> bool:
        status = self.features.get(feature)
        return status is not None and status.available

    def unavailable(self) -> tuple[tuple[Feature, FeatureStatus], ...]:
        return tuple((f, st) for f, st in self.features.items() if not st.available)


_PROBE_TABLES: Mapping[Feature, Sequence[DependencySpec]] = {
    Feature.SESSION_BROWSING: SESSION_BROWSING_DEPENDENCIES,
    Feature.SEND: DIRECT_SEND_DEPENDENCIES,
    Feature.JOBS: CRON_DEPENDENCIES,
    Feature.MODEL: MODEL_DEPENDENCIES,
}

_EVIDENCE_FILES: Mapping[Feature, str] = {
    Feature.READ: READ_COMPAT_FILE,
    Feature.SESSION_BROWSING: READ_COMPAT_FILE,
    Feature.SEND: DIRECT_SEND_COMPAT_FILE,
    Feature.JOBS: CRON_COMPAT_FILE,
    Feature.MODEL: MODEL_COMPAT_FILE,
}

# `Probe` takes the located root and the table; injectable so each step can be tested alone.
Probe = Callable[[Path, Sequence[DependencySpec]], Sequence[str]]
EvidenceMatcher = Callable[[Path], Mapping[Feature, str | None]]


def _default_probe(root: Path, specs: Sequence[DependencySpec]) -> Sequence[str]:
    return probe_dependencies(hermes_root=root, specs=specs)


def match_evidence(root: Path) -> Mapping[Feature, str | None]:
    """Tested-sample labels for display and tooling. File reads only; any failure is None. The
    result is evidence: no availability decision reads it."""
    labels: dict[Feature, str | None] = {}
    cache: dict[str, str | None] = {}
    for feature, filename in _EVIDENCE_FILES.items():
        if filename not in cache:
            try:
                tested = load_read_compat_list(Path(__file__).with_name(filename))
                identity = GitFingerprintReader(getattr(tested, "bridge_files")).read(root)  # noqa: B009
                entry = match_build(identity, tested.builds) if identity is not None else None
                cache[filename] = entry.label if entry is not None else None
            except Exception:
                cache[filename] = None
        labels[feature] = cache[filename]
    return labels


def _floor(feature: Feature) -> hermes_version.Floor:
    return hermes_version.FEATURE_FLOORS[feature.value]


def evaluate_eligibility(
    *,
    root_locator: Callable[[], Path | None] = locate_hermes_root,
    version_reader: Callable[[Path], hermes_version.HermesVersion] = (
        hermes_version.read_hermes_version
    ),
    probe: Probe = _default_probe,
    evidence: EvidenceMatcher = match_evidence,
) -> Eligibility:
    """Decide, once, which features this Hermes install can serve. Never raises."""
    features: dict[Feature, FeatureStatus] = {}
    try:
        root = root_locator()
    except Exception:
        root = None
    if root is None:
        gone = FeatureStatus(False, Unavailable.HERMES_NOT_FOUND)
        return Eligibility(hermes_version.UNKNOWN_VERSION, None, dict.fromkeys(Feature, gone))

    try:
        version = version_reader(root)
    except Exception:
        version = hermes_version.UNKNOWN_VERSION

    below = {
        f: hermes_version.classify(version, _floor(f)) is hermes_version.FloorStatus.BELOW_FLOOR
        for f in Feature
    }
    for feature in Feature:
        if below[feature]:
            features[feature] = FeatureStatus(False, Unavailable.VERSION_BELOW_FLOOR)

    def run(table: Sequence[DependencySpec]) -> tuple[str, ...] | None:
        """Missing labels, or None when the probe itself failed."""
        try:
            return tuple(probe(root, table))
        except Exception:
            return None

    if not below[Feature.READ]:
        core = run(READ_CORE_DEPENDENCIES)
        if core is None or core:
            features[Feature.READ] = FeatureStatus(
                False,
                Unavailable.PROBE_FAILED if core is None else Unavailable.DEPENDENCY_MISSING,
                core or (),
            )
            for feature in Feature:
                features.setdefault(feature, FeatureStatus(False, Unavailable.REQUIRES_READ))
        else:
            features[Feature.READ] = FeatureStatus(True)
            for feature, table in _PROBE_TABLES.items():
                if below[feature]:
                    continue
                missing = run(table)
                if missing is None:
                    features[feature] = FeatureStatus(False, Unavailable.PROBE_FAILED)
                elif missing:
                    features[feature] = FeatureStatus(
                        False, Unavailable.DEPENDENCY_MISSING, missing
                    )
                else:
                    features[feature] = FeatureStatus(True)
    else:
        # Read is below its floor: nothing else is probed, so no Hermes module is imported.
        for feature in Feature:
            features.setdefault(feature, FeatureStatus(False, Unavailable.REQUIRES_READ))

    git_sha: str | None
    try:
        git_sha = resolve_git_head_sha(root)
    except Exception:
        git_sha = None
    try:
        labels = evidence(root)
    except Exception:
        labels = {}
    resolved = {
        f: FeatureStatus(st.available, st.reason, st.missing, labels.get(f))
        for f, st in features.items()
    }
    return Eligibility(version, git_sha, {f: resolved[f] for f in Feature})


_READ_WHY: Mapping[Unavailable, OtherWhy] = {
    Unavailable.HERMES_NOT_FOUND: OtherWhy.HERMES_BUILD_UNSUPPORTED,
    Unavailable.VERSION_BELOW_FLOOR: OtherWhy.HERMES_BUILD_UNSUPPORTED,
    Unavailable.DEPENDENCY_MISSING: OtherWhy.HERMES_READ_DEPENDENCY_MISSING,
    Unavailable.PROBE_FAILED: OtherWhy.HERMES_READ_DEPENDENCY_MISSING,
}


def read_why(status: FeatureStatus) -> OtherWhy:
    """The existing ERR-2a `why` for a failed read. No new wire value."""
    return _READ_WHY.get(status.reason, OtherWhy.HERMES_BUILD_UNSUPPORTED)  # type: ignore[arg-type]


class CompatGate:
    """The `Compat` implementation: a thin wrapper that evaluates eligibility and exposes its
    read view as a `CompatResult`. The pieces are injectable so each step can be tested alone."""

    def __init__(
        self,
        *,
        root_locator: Callable[[], Path | None] = locate_hermes_root,
        version_reader: Callable[[Path], hermes_version.HermesVersion] = (
            hermes_version.read_hermes_version
        ),
        probe: Probe = _default_probe,
        evidence: EvidenceMatcher = match_evidence,
    ) -> None:
        self._kwargs = {
            "root_locator": root_locator,
            "version_reader": version_reader,
            "probe": probe,
            "evidence": evidence,
        }

    def evaluate(self) -> CompatResult:
        eligibility = evaluate_eligibility(**self._kwargs)  # type: ignore[arg-type]
        read = eligibility.features[Feature.READ]
        if read.available:
            return CompatResult(CompatStatus.SUPPORTED, None, eligibility=eligibility)
        return CompatResult(CompatStatus.UNSUPPORTED, read_why(read), eligibility=eligibility)


def default_gate(*, read_compat_path: Path | None = None) -> CompatGate:
    """The production gate. `read_compat_path` is accepted for tooling that points evidence at
    another tested-sample list; it never changes availability."""
    if read_compat_path is None:
        return CompatGate()

    def evidence(root: Path) -> Mapping[Feature, str | None]:
        labels = dict(match_evidence(root))
        try:
            tested = load_read_compat_list(read_compat_path)
            identity = GitFingerprintReader(getattr(tested, "bridge_files")).read(root)  # noqa: B009
            entry = match_build(identity, tested.builds) if identity is not None else None
            labels[Feature.READ] = entry.label if entry is not None else None
        except Exception:
            labels[Feature.READ] = None
        return labels

    return CompatGate(evidence=evidence)
