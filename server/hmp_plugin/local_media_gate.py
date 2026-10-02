"""Local-media process qualification gate (S6a; ROOT_DECISIONS "S6 media qualification design").

No route consumes it and the shipped manifest has no entries, so every call returns the constant
closed callback. Since S6b only `adapter.py` imports it, function-locally and only for a SUPPORTED
read result with an exact `BuildIdentity`; no flag selects it and it runs whether or not any media
flag is set. It imports only `compat` and the standard library: never `adapter`, `bridge`, `server`,
`request_ctx` or any Hermes module (the dependency probe lives in `compat`). Module import does no
filesystem or native access; the only import-time effect is one atomic `setdefault` of the process
anchor below.

What a listener callback proves, at each call: the listed native files, the listed HMP top-level
sources and the Git SHA hash to the values in a currently present exact manifest entry, they equal
what the FIRST supported factory of this OS process captured, and the dependency probe passes. It
does not prove loaded bytecode equals disk (first import before capture, lazy imports after it,
`.pyc` content, ABA edits), native callee closure, providers, C extensions, site-packages, the
interpreter, or that the local unauthenticated manifest is authentic. Nothing here is a sandbox,
deadline or tamper-proof claim; same-account code can alter the anchor. Source reads are bounded
(per file and per invocation) but kernel/FUSE/NFS latency, default-executor capacity and the
inherited Git-metadata resolver (`compat.resolve_git_head_sha`) are not bounded by time or size.

Process anchor. The first supported factory fixes the baseline for the whole OS process, across
Hermes module evictions, reloads and homes: a plugin reload cannot re-baseline, and a different
native root or plugin directory closes later listeners. Only a full process restart clears it.
It lives in `sys.__dict__` under a stable, unversioned key, holds only stdlib primitives (no
plugin class, callable, module, `Path`, label or receipt), and is never repaired, replaced, reset
or deleted: a foreign, malformed or incompatible anchor yields the constant closed callback and is
left untouched. Layout, validated on EVERY read (a change needs a new schema literal, which closes
against an existing anchor):

    anchor   = (1, _thread.LockType, [cell])            exact tuple, exact int, exact lock, 1-list
    cell     = None | "closed" | baseline
    baseline = ("b1", native_root, plugin_dir, read_files, read_fp, native_files, native_fp,
                git_sha, hmp_files, hmp_fp)             exact str / sorted tuples / strict hex

The only transitions are `None` to `"closed"` or `None` to a baseline, once, under the anchor lock.
The lock covers only a short read/compare/write; it is never held over manifest work, hashing,
preload, an import or the dependency probe (an abandoned or concurrent Hermes loader thread may
hold an import lock). Under a free-threaded interpreter nothing is created or read: closed.

Preload policy. The optional `preload` callable is supplied by the adapter (S6b). It is called
only after an exact manifest match, outside the lock, and must return an exact non-empty tuple of
the module objects THIS load actually bound. The gate checks those objects (never names looked up
in `sys.modules`). `preload=None` can therefore never admit anything: with a matching entry it
closes. There is no bypass, baseline parameter, setter or reset.
"""

from __future__ import annotations

import _thread
import contextlib
import hashlib
import importlib.machinery
import json
import os
import re
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Final

from . import compat

MEDIA_COMPAT_FILE: Final = "local_media_supported_builds.json"
MEDIA_MANIFEST_FORMAT: Final = "hmp-local-media-1"
ANCHOR_KEY: Final = "_hermes_hmp_local_media_process_state"
ANCHOR_SCHEMA: Final = 1
BASELINE_TAG: Final = "b1"

MAX_MANIFEST_BYTES: Final = 256 * 1024
MAX_NATIVE_PATHS: Final = 256
MAX_HMP_PATHS: Final = 256
MAX_BUILDS: Final = 128
MAX_TEXT_CHARS: Final = 256
MAX_PATH_BYTES: Final = 1024
MAX_DIR_ENTRIES: Final = 512
MAX_FILE_BYTES: Final = 8 * 1024 * 1024
MAX_TOTAL_BYTES: Final = 64 * 1024 * 1024
_READ_CHUNK: Final = 1024 * 1024
_MAX_ROOT_CHARS: Final = 4096

_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_CLOSED_CELL: Final = "closed"

# The media lane's own probe table: every read dependency, plus the title and compression-lineage
# APIs the media qualification query path reaches (`bridge.REACHED_METHODS["db"]`). Both resolve
# through `SessionDB`'s mixins to `hermes_state_titles.py` and `hermes_state_compression.py`, files
# of the preliminary native inventory. The profile/home/context reach of the media path is
# `_routed_profile_home` and `_profile_runtime_scope`, already in `READ_DEPENDENCIES`. The callees
# of those and of the image producer are NOT covered (callee closure is open); no entry exists.
MEDIA_DEPENDENCIES: Final[tuple[compat.DependencySpec, ...]] = (
    *compat.READ_DEPENDENCIES,
    compat.DependencySpec("hermes_state", "SessionDB.get_session_by_title", gap="E-GAP-6/7"),
    compat.DependencySpec("hermes_state", "SessionDB.get_compression_lineage", gap="E-GAP-6/7"),
)


class _RefusedError(Exception):
    """An internal refusal. It is never raised to a caller and never carries data."""


# --------------------------------------------------------------------------------------------
# The process anchor. The ONLY import-time effect of this module; it never takes the lock.
# --------------------------------------------------------------------------------------------


def _gil_guard_ok() -> bool:
    """True when the interpreter is known to run with the GIL (the attribute is absent before 3.13).
    A free-threaded or undecidable interpreter is unqualified and fails closed."""
    probe = getattr(sys, "_is_gil_enabled", None)
    if probe is None:
        return True
    try:
        return bool(callable(probe) and probe() is True)
    except Exception:
        return False


if _gil_guard_ok():
    sys.__dict__.setdefault(ANCHOR_KEY, (ANCHOR_SCHEMA, _thread.allocate_lock(), [None]))


# --------------------------------------------------------------------------------------------
# Strict manifest (hmp-local-media-1).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MediaBuildEntry:
    label: str
    git_sha: str | None
    native_fingerprint: str
    hmp_fingerprint: str
    source_sha: str | None  # provenance only; never used for matching
    qualified_by: str
    qualified_at: str


@dataclass(frozen=True, slots=True)
class MediaManifest:
    native_files: tuple[str, ...]
    hmp_files: tuple[str, ...]
    builds: tuple[MediaBuildEntry, ...]


@dataclass(frozen=True, slots=True)
class MediaProcessBaseline:
    """A decoded VIEW of the anchor's baseline tuple. It is never the persistent value."""

    native_root: str
    plugin_dir: str
    read_files: tuple[str, ...]
    read_fingerprint: str
    native_files: tuple[str, ...]
    native_fingerprint: str
    git_sha: str | None
    hmp_files: tuple[str, ...]
    hmp_fingerprint: str


_ENTRY_KEYS: Final = frozenset(
    {
        "label",
        "git_sha",
        "native_fingerprint",
        "hmp_fingerprint",
        "source_sha",
        "qualified_by",
        "qualified_at",
    }
)
_MANIFEST_KEYS: Final = frozenset({"format", "native_files", "hmp_files", "builds"})


def _valid_text(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= MAX_TEXT_CHARS:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _valid_hex(value: object, pattern: re.Pattern[str], *, optional: bool) -> bool:
    if value is None:
        return optional
    return type(value) is str and pattern.fullmatch(value) is not None


def _valid_rel(value: object) -> bool:
    """Safe relative POSIX path: bounded UTF-8, no absolute/traversal/backslash/NUL/controls."""
    if type(value) is not str or not value:
        return False
    try:
        if len(value.encode("utf-8")) > MAX_PATH_BYTES:
            return False
    except UnicodeEncodeError:
        return False
    if "\\" in value or value.startswith("/"):
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _valid_rel_list(value: object, limit: int) -> bool:
    """A sorted, unique list/tuple of safe paths within the count bound."""
    if type(value) not in (list, tuple) or len(value) > limit:
        return False
    items = list(value)  # type: ignore[call-overload]
    return all(_valid_rel(p) for p in items) and items == sorted(set(items))


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _no_constants(_name: str) -> Any:
    raise ValueError("non-finite number")


def _parse_json(data: bytes) -> Any:
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_no_duplicate_keys,
        parse_constant=_no_constants,
    )


def _parse_entry(raw: object) -> MediaBuildEntry:
    if type(raw) is not dict or set(raw) != _ENTRY_KEYS:
        raise ValueError("bad media build entry")
    ok = (
        _valid_text(raw["label"])
        and _valid_text(raw["qualified_by"])
        and _valid_text(raw["qualified_at"])
        and _valid_hex(raw["git_sha"], _HEX40, optional=True)
        and _valid_hex(raw["source_sha"], _HEX40, optional=True)
        and _valid_hex(raw["native_fingerprint"], _HEX64, optional=False)
        and _valid_hex(raw["hmp_fingerprint"], _HEX64, optional=False)
    )
    if not ok:
        raise ValueError("bad media build entry")
    return MediaBuildEntry(
        label=raw["label"],
        git_sha=raw["git_sha"],
        native_fingerprint=raw["native_fingerprint"],
        hmp_fingerprint=raw["hmp_fingerprint"],
        source_sha=raw["source_sha"],
        qualified_by=raw["qualified_by"],
        qualified_at=raw["qualified_at"],
    )


def parse_media_manifest(data: bytes) -> MediaManifest:
    """Strictly parse manifest bytes. Anything unexpected raises `ValueError`."""
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest too large")
    raw = _parse_json(data)
    if type(raw) is not dict or set(raw) != _MANIFEST_KEYS:
        raise ValueError("bad manifest keys")
    if type(raw["format"]) is not str or raw["format"] != MEDIA_MANIFEST_FORMAT:
        raise ValueError("bad manifest format")
    native, hmp, builds = raw["native_files"], raw["hmp_files"], raw["builds"]
    if type(builds) is not list or len(builds) > MAX_BUILDS:
        raise ValueError("bad builds")
    if not _valid_rel_list(native, MAX_NATIVE_PATHS) or not _valid_rel_list(hmp, MAX_HMP_PATHS):
        raise ValueError("bad file list")
    if any("/" in p or not p.endswith(".py") or p == ".py" for p in hmp):
        raise ValueError("hmp files must be top-level .py sources")
    if builds and (not native or not hmp):
        raise ValueError("entries need file lists")
    return MediaManifest(
        native_files=tuple(native),
        hmp_files=tuple(hmp),
        builds=tuple(_parse_entry(b) for b in builds),
    )


def load_media_manifest(path: Path) -> MediaManifest:
    """Bounded, no-follow read of the media manifest, then the strict parse. Raises on any fault.
    Never uses `compat.load_read_compat_list` (unbounded and extra-key-tolerant)."""
    data = _read_one(Path(path), MAX_MANIFEST_BYTES)
    return parse_media_manifest(data)


def _load_read_files(path: Path) -> tuple[str, ...]:
    """Extract only `bridge_files` from a format-1 read list with bounded I/O. The compat parser
    stays authoritative for the read gate itself; this is not a replacement."""
    raw = _parse_json(_read_one(Path(path), MAX_MANIFEST_BYTES))
    if type(raw) is not dict or type(raw.get("format")) is not int or raw["format"] != 1:
        raise ValueError("bad read list")
    files = raw.get("bridge_files")
    if not _valid_rel_list(files, MAX_NATIVE_PATHS) or not files:
        raise ValueError("bad read list")
    return tuple(files)


def match_media_build(
    builds: Sequence[MediaBuildEntry],
    *,
    git_sha: str | None,
    native_fingerprint: str,
    hmp_fingerprint: str,
) -> MediaBuildEntry | None:
    """CS-19 semantics (a git install matches only that SHA, a no-git install only `null`) plus
    BOTH fingerprints. `source_sha` plays no part."""
    for entry in builds:
        if (
            entry.git_sha == git_sha
            and entry.native_fingerprint == native_fingerprint
            and entry.hmp_fingerprint == hmp_fingerprint
        ):
            return entry
    return None


# --------------------------------------------------------------------------------------------
# Bounded source reads and the shared pure digest.
# --------------------------------------------------------------------------------------------


def fingerprint_pairs(pairs: Mapping[str, bytes]) -> str:
    """SHA-256 over `path\\0len\\0bytes` for each path in sorted order: byte-compatible with
    `compat.compute_read_bridge_fingerprint`. Tooling and runtime share this one function."""
    digest = hashlib.sha256()
    for rel in sorted(pairs):
        data = pairs[rel]
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


class _Budget:
    """Aggregate source bytes for ONE qualifier invocation (every read, brackets included),
    charged before reading."""

    def __init__(self) -> None:
        self._left = MAX_TOTAL_BYTES

    def charge(self, size: int) -> None:
        if size > self._left:
            raise _RefusedError
        self._left -= size


def _flags() -> tuple[int, int]:
    names = ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")
    values = [getattr(os, n, None) for n in names]
    if None in values or os.open not in os.supports_dir_fd or os.scandir not in os.supports_fd:
        raise _RefusedError
    nofollow, directory, cloexec, nonblock = values
    return (
        os.O_RDONLY | directory | nofollow | cloexec,
        os.O_RDONLY | nonblock | nofollow | cloexec,
    )


def _read_fd(fd: int, count: int) -> bytes:
    return os.read(fd, count)


def _identity(st: os.stat_result) -> tuple[int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _read_exact(fd: int, size: int) -> bytes:
    """At most `size + 1` bytes are requested so growth is seen; anything but exactly `size`
    bytes refuses."""
    chunks: list[bytes] = []
    got = 0
    while got < size + 1:
        piece = _read_fd(fd, min(_READ_CHUNK, size + 1 - got))
        if type(piece) is not bytes:
            raise _RefusedError
        if not piece:
            break
        chunks.append(piece)
        got += len(piece)
    if got != size:
        raise _RefusedError
    return b"".join(chunks)


def _close(fds: list[int]) -> None:
    for fd in reversed(fds):
        with contextlib.suppress(OSError):
            os.close(fd)


def _read_leaf(
    root_fd: int, rel: str, cap: int, budget: _Budget | None, dir_flags: int, leaf_flags: int
) -> bytes:
    """One regular file below `root_fd`: every intermediate component is opened relative to the
    previous directory fd without following links, the leaf non-blocking without following, type
    and size are checked before any read, and the same stat identity must hold afterwards."""
    if not _valid_rel(rel):
        raise _RefusedError
    parts = rel.split("/")
    held: list[int] = []
    try:
        current = root_fd
        for part in parts[:-1]:
            current = os.open(part, dir_flags, dir_fd=current)
            held.append(current)
        fd = os.open(parts[-1], leaf_flags, dir_fd=current)
        held.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise _RefusedError
        if budget is not None:
            budget.charge(before.st_size)
        data = _read_exact(fd, before.st_size)
        if _identity(os.fstat(fd)) != _identity(before):
            raise _RefusedError
        return data
    finally:
        _close(held)


def _read_one(path: Path, cap: int) -> bytes:
    """One bounded no-follow file read for a manifest-style file (the parent is resolved once)."""
    dir_flags, leaf_flags = _flags()
    parent = path.parent.resolve()
    root_fd = os.open(os.fspath(parent), dir_flags)
    try:
        return _read_leaf(root_fd, path.name, cap, None, dir_flags, leaf_flags)
    finally:
        _close([root_fd])


def _read_set(
    root: Path, rels: Sequence[str], budget: _Budget, *, plugin_listing: bool = False
) -> dict[str, bytes]:
    dir_flags, leaf_flags = _flags()
    root_fd = os.open(os.fspath(root), dir_flags)
    try:
        if plugin_listing:
            _check_plugin_dir(root_fd, frozenset(rels), dir_flags)
        return {
            rel: _read_leaf(root_fd, rel, MAX_FILE_BYTES, budget, dir_flags, leaf_flags)
            for rel in rels
        }
    finally:
        _close([root_fd])


def _scan_names(dir_fd: int) -> list[os.DirEntry[str]]:
    entries: list[os.DirEntry[str]] = []
    with os.scandir(dir_fd) as it:
        for entry in it:
            if len(entries) >= MAX_DIR_ENTRIES:
                raise _RefusedError
            entries.append(entry)
    return entries


def _check_plugin_dir(plugin_fd: int, listed: frozenset[str], dir_flags: int) -> None:
    """Directory-set equality for importable forms. Any unlisted entry that ends in a suffix in
    `importlib.machinery.all_suffixes()` (source, extension, sourceless bytecode) refuses; so does
    any unlisted non-regular entry or subdirectory other than a `__pycache__` directory, which must
    itself hold only regular files. `.pyc` CONTENT is a stated residual."""
    suffixes = tuple(importlib.machinery.all_suffixes())
    has_cache = False
    for entry in _scan_names(plugin_fd):
        name = entry.name
        if name in listed:
            continue  # the reader requires a regular, non-linked file
        if name == "__pycache__":
            has_cache = True
            continue
        if name.endswith(suffixes) or not entry.is_file(follow_symlinks=False):
            raise _RefusedError
    if not has_cache:
        return
    cache_fd = os.open("__pycache__", dir_flags, dir_fd=plugin_fd)  # a link or file refuses
    try:
        if any(not e.is_file(follow_symlinks=False) for e in _scan_names(cache_fd)):
            raise _RefusedError
    finally:
        _close([cache_fd])


# --------------------------------------------------------------------------------------------
# Measurement, anchor access and the factory.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Measured:
    read_fingerprint: str
    native_fingerprint: str
    git_sha: str | None
    hmp_fingerprint: str


def _measure(
    root: Path,
    plugin_dir: Path,
    native_files: Sequence[str],
    read_files: Sequence[str],
    hmp_files: Sequence[str],
    budget: _Budget,
) -> _Measured:
    native = _read_set(root, native_files, budget)
    read_fingerprint = fingerprint_pairs({rel: native[rel] for rel in read_files})
    git_sha = compat.resolve_git_head_sha(root)  # inherited resolver: unbounded, a stated residual
    hmp = _read_set(plugin_dir, hmp_files, budget, plugin_listing=True)
    return _Measured(read_fingerprint, fingerprint_pairs(native), git_sha, fingerprint_pairs(hmp))


def _resolve_root(hermes_root: Path | None) -> Path:
    root = hermes_root if hermes_root is not None else compat.locate_hermes_root()
    if root is None:
        raise _RefusedError
    return Path(root).resolve()


def _resolve_plugin_dir(plugin_dir: Path | None) -> Path:
    return (plugin_dir if plugin_dir is not None else Path(__file__).parent).resolve()


def _manifest_path(manifest_path: Path | None) -> Path:
    return (
        manifest_path if manifest_path is not None else Path(__file__).with_name(MEDIA_COMPAT_FILE)
    )


def _read_list_path(read_compat_path: Path | None) -> Path:
    if read_compat_path is not None:
        return read_compat_path
    return Path(__file__).with_name(compat.READ_COMPAT_FILE)


def _check_origins(
    modules: object, plugin_dir: Path, hmp_files: frozenset[str], package: str | None
) -> None:
    """The module objects this load bound, NEVER names looked up in `sys.modules`. Each must have
    equal spec origin and file, a resolved file exactly `plugin_dir/<stem>.py` that is listed (its
    own directory resolving to `plugin_dir`, its basename unchanged by resolution, the leaf not a
    link), an exact `SourceFileLoader` whose path and name equal the spec's origin and name, and the
    name this package would give it. Narrowing only: it does not
    attest bytecode against disk."""
    if type(modules) is not tuple or not modules or not isinstance(package, str) or not package:
        raise _RefusedError
    seen: set[int] = set()
    for module in modules:
        if type(module) is not ModuleType or id(module) in seen:
            raise _RefusedError
        seen.add(id(module))
        spec = getattr(module, "__spec__", None)
        file = getattr(module, "__file__", None)
        if spec is None or type(file) is not str or type(spec.origin) is not str:
            raise _RefusedError
        loader = spec.loader
        if spec.origin != file or type(loader) is not importlib.machinery.SourceFileLoader:
            raise _RefusedError
        if loader.path != spec.origin or loader.name != spec.name:
            raise _RefusedError
        lexical = Path(file)
        resolved = lexical.resolve()
        if resolved.name not in hmp_files or resolved != plugin_dir / resolved.name:
            raise _RefusedError
        # The file must sit in the plugin directory itself (a whole-directory alias is fine), under
        # its own name, and not be a link: a leaf symlink from elsewhere is refused.
        if (
            lexical.name != resolved.name
            or Path(os.path.realpath(lexical.parent)) != plugin_dir
            or lexical.is_symlink()
        ):
            raise _RefusedError
        expected = package if resolved.stem == "__init__" else f"{package}.{resolved.stem}"
        if module.__name__ != expected or spec.name != expected:
            raise _RefusedError


def _closed() -> bool:
    return False


def _classify(value: object) -> tuple[str, object]:
    """('empty'|'closed'|'baseline'|'foreign', payload). Exact types, full layout, every read."""
    if value is None:
        return ("empty", None)
    if type(value) is str:
        return ("closed", None) if value == _CLOSED_CELL else ("foreign", None)
    return ("baseline", value) if _valid_baseline(value) else ("foreign", None)


def _valid_baseline(v: object) -> bool:
    if type(v) is not tuple or len(v) != 10 or type(v[0]) is not str or v[0] != BASELINE_TAG:
        return False
    roots_ok = all(type(p) is str and 0 < len(p) <= _MAX_ROOT_CHARS for p in (v[1], v[2]))
    return (
        roots_ok
        and type(v[3]) is tuple
        and type(v[5]) is tuple
        and type(v[8]) is tuple
        and _valid_rel_list(v[3], MAX_NATIVE_PATHS)
        and _valid_rel_list(v[5], MAX_NATIVE_PATHS)
        and _valid_rel_list(v[8], MAX_HMP_PATHS)
        and bool(v[3])
        and bool(v[5])
        and bool(v[8])
        and set(v[3]) <= set(v[5])
        and _valid_hex(v[4], _HEX64, optional=False)
        and _valid_hex(v[6], _HEX64, optional=False)
        and _valid_hex(v[7], _HEX40, optional=True)
        and _valid_hex(v[9], _HEX64, optional=False)
    )


def _anchor_parts() -> tuple[Any, list[object]] | None:
    """The lock and cell of a well-formed anchor, or None. Never creates or repairs one."""
    anchor = sys.__dict__.get(ANCHOR_KEY)
    if type(anchor) is not tuple or len(anchor) != 3:
        return None
    schema, lock, cell = anchor
    if type(schema) is not int or schema != ANCHOR_SCHEMA:
        return None
    if type(lock) is not _thread.LockType or type(cell) is not list or len(cell) != 1:
        return None
    return lock, cell


def _read_cell(lock: Any, cell: list[object]) -> tuple[str, object]:
    with lock:
        value = cell[0]
    return _classify(value)


def _first_transition(lock: Any, cell: list[object], new: object) -> tuple[str, object]:
    """The single write site: `None` to `new`, once, under the lock. Returns the cell as it is."""
    with lock:
        if cell[0] is None:
            cell[0] = new
        value = cell[0]
    return _classify(value)


def _capture(
    read_identity: compat.BuildIdentity,
    preload: Callable[[], tuple[ModuleType, ...]] | None,
    hermes_root: Path | None,
    plugin_dir: Path | None,
    manifest_path: Path | None,
    read_compat_path: Path | None,
) -> tuple[object, ...] | None:
    """The candidate baseline tuple for the disk right now, or None. Runs unlocked. An empty
    manifest returns before any source is located, read, preloaded or imported."""
    manifest = load_media_manifest(_manifest_path(manifest_path))
    if not manifest.builds:
        return None
    read_files = _load_read_files(_read_list_path(read_compat_path))
    if not set(read_files) <= set(manifest.native_files):
        return None
    root = _resolve_root(hermes_root)
    pdir = _resolve_plugin_dir(plugin_dir)
    budget = _Budget()  # one budget for the whole invocation, brackets included
    before = _measure(root, pdir, manifest.native_files, read_files, manifest.hmp_files, budget)
    if (
        before.read_fingerprint != read_identity.fingerprint
        or before.git_sha != read_identity.git_sha
    ):
        return None
    entry = match_media_build(
        manifest.builds,
        git_sha=before.git_sha,
        native_fingerprint=before.native_fingerprint,
        hmp_fingerprint=before.hmp_fingerprint,
    )
    if entry is None or preload is None:
        return None  # an absent preload can never prove origins: closed, no bypass
    modules = preload()
    after = _measure(root, pdir, manifest.native_files, read_files, manifest.hmp_files, budget)
    if after != before:
        return None
    _check_origins(modules, pdir, frozenset(manifest.hmp_files), __package__)
    return (
        BASELINE_TAG,
        str(root),
        str(pdir),
        tuple(read_files),
        before.read_fingerprint,
        manifest.native_files,
        before.native_fingerprint,
        before.git_sha,
        manifest.hmp_files,
        before.hmp_fingerprint,
    )


def _decode(v: tuple[Any, ...]) -> MediaProcessBaseline:
    return MediaProcessBaseline(v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], v[9])


def media_listener_qualifier(
    read_identity: compat.BuildIdentity | None,
    *,
    preload: Callable[[], tuple[ModuleType, ...]] | None = None,
    hermes_root: Path | None = None,
    plugin_dir: Path | None = None,
    manifest_path: Path | None = None,
    read_compat_path: Path | None = None,
) -> Callable[[], bool]:
    """Build a listener's media admission callback (BLOCKING: reads files; call off the loop).

    Independent of any live media flag. Precondition (S6b): call only when the read `CompatResult`
    has `supported is True`; a `BuildIdentity` alone (also set on unsupported results) does not
    prove a supported read, and the gate does not check the read list's entries. The returned
    callback returns an exact `bool` and never logs; neither it nor this factory lets an
    `Exception` escape (a `BaseException` such as `KeyboardInterrupt` is not caught).

    Order: an unknown read identity or a free-threaded interpreter closes with no anchor access; a
    foreign anchor or a latched `"closed"` cell closes with no work; an
    empty manifest then latches closed before any source is located. A first call whose capture
    equals nothing yet writes the one baseline (or `"closed"`); a later capture that differs from
    the fixed cell gets the constant closed callback for that listener's life. A callback that was
    bound to a matching capture closes on any later mismatch and reopens only after a fresh check
    equals the same baseline again.

    The keyword parameters are test seams for synthetic roots; none can supply or reset a baseline.
    """
    try:
        if type(read_identity) is not compat.BuildIdentity or not _gil_guard_ok():
            return _closed
        parts = _anchor_parts()
        if parts is None:
            return _closed
        lock, cell = parts
        kind, _ = _read_cell(lock, cell)
        if kind in ("closed", "foreign"):
            return _closed
        try:
            candidate = _capture(
                read_identity, preload, hermes_root, plugin_dir, manifest_path, read_compat_path
            )
            if candidate is not None and not _valid_baseline(candidate):
                candidate = None
        except Exception:
            candidate = None
        kind, fixed = _first_transition(
            lock, cell, _CLOSED_CELL if candidate is None else candidate
        )
        if kind != "baseline" or candidate is None or candidate != fixed:
            return _closed
        baseline = _decode(candidate)  # type: ignore[arg-type]
    except Exception:
        return _closed

    def qualified() -> bool:
        try:
            return _check_current(
                baseline, candidate, hermes_root, plugin_dir, manifest_path, read_compat_path
            )
        except Exception:
            return False

    return qualified


def _check_current(
    baseline: MediaProcessBaseline,
    fixed: tuple[object, ...],
    hermes_root: Path | None,
    plugin_dir: Path | None,
    manifest_path: Path | None,
    read_compat_path: Path | None,
) -> bool:
    if not _gil_guard_ok():
        return False
    parts = _anchor_parts()
    if parts is None:
        return False
    kind, current = _read_cell(*parts)
    if kind != "baseline" or current != fixed:
        return False
    manifest = load_media_manifest(_manifest_path(manifest_path))
    if not manifest.builds:
        return False
    read_files = _load_read_files(_read_list_path(read_compat_path))
    if (
        manifest.native_files != baseline.native_files
        or manifest.hmp_files != baseline.hmp_files
        or read_files != baseline.read_files
    ):
        return False
    root = _resolve_root(hermes_root)
    pdir = _resolve_plugin_dir(plugin_dir)
    if str(root) != baseline.native_root or str(pdir) != baseline.plugin_dir:
        return False
    fresh = _measure(root, pdir, manifest.native_files, read_files, manifest.hmp_files, _Budget())
    if (
        fresh.read_fingerprint != baseline.read_fingerprint
        or fresh.native_fingerprint != baseline.native_fingerprint
        or fresh.git_sha != baseline.git_sha
        or fresh.hmp_fingerprint != baseline.hmp_fingerprint
    ):
        return False
    entry = match_media_build(
        manifest.builds,
        git_sha=fresh.git_sha,
        native_fingerprint=fresh.native_fingerprint,
        hmp_fingerprint=fresh.hmp_fingerprint,
    )
    if entry is None:
        return False
    # No probe cache: every check probes freshly (the cost is measured later, not hidden here).
    missing = compat.probe_read_dependencies(
        hermes_root=root, bridge_files=baseline.native_files, specs=MEDIA_DEPENDENCIES
    )
    return len(tuple(missing)) == 0
