#!/usr/bin/env python3
"""G3 filesystem safety prototype for host-local generated images (research leaf, not product).

Test tooling: `server/hmp_plugin` never imports it. It reads one candidate file from
`<profile home>/cache/images/<candidate>` through pinned directory descriptors and returns the
bytes only to an in-process caller. It defines no media reference, route, grant, token, schema,
wire shape or public API, and it reads nothing from any Hermes install.

Trust model:

- `profile_home` is the caller's already-selected, already-resolved profile home. The caller
  owns resolving and pinning it; this leaf opens it with O_NOFOLLOW on the final component and
  never resolves it. Ancestors of the home are trusted as the caller supplied them.
- `candidate` is untrusted. Root decision: **flat only**. Native producers and the inbound
  cache write top-level files of `cache/images` (name shapes in the G3 delivery-paths note), so
  the candidate must be exactly one component. Nesting, absolute strings, `.`/`..`, empty,
  control/format characters, backslashes and over-long names are refused. Nested names would need a
  separate reviewed amendment; no other root (legacy `image_cache`, `cache/documents`,
  another profile) is ever consulted or used as a fallback.

Method: open home, `cache`, `images` each with O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC relative to the
previous descriptor; open the file relative to `images` with O_NOFOLLOW|O_NONBLOCK; `fstat`
(regular, one link, 0 < size <= bound); bounded read of at most bound+1 bytes; `fstat` again;
then re-`lstat` every path component against the pinned identities. Any difference refuses and
the buffer is discarded. Every descriptor is closed on every path. Platforms without these
primitives get `unsupported_platform` and no path-based fallback.

The bytes are **unvalidated raster bytes**: no decoder, magic check, MIME, dimension or animation
policy runs here (that policy is still under review) and nothing here qualifies them. Device and
inode numbers are compared internally only; the public report holds closed outcomes, one byte
count and booleans. `_hooks` and `_chunk_size` are test seams, not a product contract.
"""

from __future__ import annotations

import contextlib
import enum
import errno
import os
import stat
import sys
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

MAX_BYTES = 8 * 1024 * 1024
MAX_NAME_BYTES = 128
READ_CHUNK = 64 * 1024
CACHE_COMPONENTS = ("cache", "images")
BYTES_LABEL = "unvalidated_raster_bytes"

HOOK_NAMES = frozenset(
    {
        "after_dirs_pinned",
        "after_file_open",
        "after_first_fstat",
        "after_chunk",
        "before_second_fstat",
        "before_revalidate",
    }
)


class Outcome(enum.StrEnum):
    OK = "ok"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    PROFILE_HOME_INVALID = "profile_home_invalid"
    PROFILE_HOME_UNAVAILABLE = "profile_home_unavailable"
    CANDIDATE_TYPE = "candidate_type"
    CANDIDATE_EMPTY = "candidate_empty"
    CANDIDATE_CONTROL = "candidate_control"
    CANDIDATE_ABSOLUTE = "candidate_absolute"
    CANDIDATE_DOT = "candidate_dot"
    CANDIDATE_NESTED = "candidate_nested"
    CANDIDATE_TOO_LONG = "candidate_too_long"
    UNAVAILABLE = "unavailable"  # cache, images or file absent: swept or never there
    ANCESTOR_REFUSED = "ancestor_refused"  # symlink or non-directory on the pinned walk
    SYMLINK_REFUSED = "symlink_refused"
    NOT_REGULAR = "not_regular"
    HARDLINKED = "hardlinked"
    EMPTY = "empty"
    OVERSIZE = "oversize"
    CHANGED_DURING_READ = "changed_during_read"
    BINDING_LOST = "binding_lost"
    OPEN_FAILED = "open_failed"
    READ_FAILED = "read_failed"


@dataclass(frozen=True, repr=False)
class ReadResult:
    """Closed outcome plus, on success only, a private buffer of unvalidated raster bytes."""

    outcome: Outcome
    byte_count: int = 0
    _buffer: bytes | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        return f"ReadResult(outcome={self.outcome.value!r})"

    def unvalidated_raster_bytes(self) -> bytes:
        """In-process handoff only. The bytes are not decoded, typed or qualified."""
        if self._buffer is None:
            raise ValueError("no bytes: outcome is not ok")
        return self._buffer

    def public_report(self) -> dict[str, Any]:
        """Closed metadata only: no bytes, name, path, device/inode, MIME or raster claim."""
        return {
            "outcome": self.outcome.value,
            "byte_count": self.byte_count,
            "bytes_label": BYTES_LABEL,
            "raster_validated": False,
            "binding_held": self.outcome is Outcome.OK,
        }


def _refuse(outcome: Outcome) -> ReadResult:
    return ReadResult(outcome)


# Captured at import so the capability check names the real primitives, not a wrapper.
_OS_OPEN = os.open
_OS_STAT = os.stat


def platform_supported() -> bool:
    """True only where descriptor-relative no-follow opens and lstat exist; never a fallback."""
    if os.name != "posix" or sys.platform == "win32":
        return False
    needed = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK", "O_RDONLY")
    if not all(hasattr(os, name) for name in needed):
        return False
    return (
        _OS_OPEN in os.supports_dir_fd
        and _OS_STAT in os.supports_dir_fd
        and _OS_STAT in os.supports_follow_symlinks
        and hasattr(os, "fstat")
    )


def classify_candidate(candidate: object) -> Outcome | None:
    """Return the refusal for an untrusted candidate, or None for one flat acceptable name."""
    if (
        type(candidate) is not str
    ):  # exact type: a str subclass could override the grammar's methods
        return Outcome.CANDIDATE_TYPE
    if not candidate:
        return Outcome.CANDIDATE_EMPTY
    for char in candidate:
        if unicodedata.category(char)[0] == "C" or unicodedata.category(char) in (
            "Zl",
            "Zp",
        ):
            return Outcome.CANDIDATE_CONTROL
    if candidate.startswith("/"):
        return Outcome.CANDIDATE_ABSOLUTE
    if "/" in candidate or "\\" in candidate:
        parts = candidate.replace("\\", "/").split("/")
        if any(part in (".", "..") for part in parts):
            return Outcome.CANDIDATE_DOT
        return Outcome.CANDIDATE_NESTED
    if candidate in (".", ".."):
        return Outcome.CANDIDATE_DOT
    if len(candidate.encode("utf-8")) > MAX_NAME_BYTES:
        return Outcome.CANDIDATE_TOO_LONG
    return None


_DIR_FLAGS = (
    getattr(os, "O_RDONLY", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_FILE_FLAGS = (
    getattr(os, "O_RDONLY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_CLOEXEC", 0)
)


class _FstatFailedError(Exception):
    """An `fstat` on a held descriptor raised OSError; surfaces as one closed refusal."""


def _fstat(fd: int) -> os.stat_result:
    try:
        return os.fstat(fd)
    except OSError:
        raise _FstatFailedError from None


def _identity(st: os.stat_result) -> tuple[int, int]:
    return (st.st_dev, st.st_ino)


def _signature(st: os.stat_result) -> tuple[int, ...]:
    return (
        st.st_dev,
        st.st_ino,
        st.st_mode,
        st.st_nlink,
        st.st_size,
        st.st_mtime_ns,
        st.st_ctime_ns,
    )


def _dir_open_outcome(exc: OSError, *, home: bool) -> Outcome:
    if exc.errno == errno.ENOENT:
        return Outcome.PROFILE_HOME_UNAVAILABLE if home else Outcome.UNAVAILABLE
    if exc.errno in (errno.ELOOP, errno.ENOTDIR):
        return Outcome.PROFILE_HOME_INVALID if home else Outcome.ANCESTOR_REFUSED
    return Outcome.OPEN_FAILED


def _file_open_outcome(exc: OSError) -> Outcome:
    if exc.errno == errno.ENOENT:
        return Outcome.UNAVAILABLE
    if exc.errno == errno.ELOOP:
        return Outcome.SYMLINK_REFUSED
    if exc.errno in (errno.ENXIO, errno.EOPNOTSUPP, errno.ENODEV):
        return Outcome.NOT_REGULAR  # a socket or device node
    return Outcome.OPEN_FAILED


def read_profile_cache_image(
    profile_home: str | os.PathLike[str],
    candidate: str,
    *,
    max_bytes: int = MAX_BYTES,
    _hooks: Mapping[str, Callable[[], None]] | None = None,
    _chunk_size: int = READ_CHUNK,
) -> ReadResult:
    """Read `<profile_home>/cache/images/<candidate>` or return a closed refusal."""
    if not 0 < max_bytes <= MAX_BYTES or _chunk_size <= 0:
        raise ValueError("bounds out of range")
    hooks = dict(_hooks or {})
    if not hooks.keys() <= HOOK_NAMES:
        raise ValueError("unknown test hook")

    def fire(name: str) -> None:
        callback = hooks.get(name)
        if callback is not None:
            callback()

    if not platform_supported():
        return _refuse(Outcome.UNSUPPORTED_PLATFORM)
    refusal = classify_candidate(candidate)
    if refusal is not None:
        return _refuse(refusal)
    try:
        home_path = os.fspath(profile_home)
    except TypeError:
        return _refuse(Outcome.PROFILE_HOME_INVALID)
    if not isinstance(home_path, str) or not os.path.isabs(home_path) or "\0" in home_path:
        return _refuse(Outcome.PROFILE_HOME_INVALID)

    fds: list[int] = []

    def open_tracked(name: str, flags: int, dir_fd: int | None = None) -> int:
        fd = os.open(name, flags, dir_fd=dir_fd)
        fds.append(fd)
        return fd

    try:
        return _read_pinned(home_path, candidate, max_bytes, _chunk_size, fire, open_tracked)
    except _FstatFailedError:
        return _refuse(Outcome.READ_FAILED)
    finally:
        for fd in reversed(fds):
            with contextlib.suppress(OSError):
                os.close(fd)


def _read_pinned(
    home_path: str,
    candidate: str,
    max_bytes: int,
    chunk_size: int,
    fire: Callable[[str], None],
    open_tracked: Callable[..., int],
) -> ReadResult:
    # Pin home, cache, images by descriptor. Each step is relative to the previous descriptor.
    try:
        home_fd = open_tracked(home_path, _DIR_FLAGS)
    except OSError as exc:
        return _refuse(_dir_open_outcome(exc, home=True))
    home_identity = _identity(_fstat(home_fd))
    children: list[tuple[int, str, tuple[int, int]]] = []  # (parent fd, name, identity)
    parent_fd = home_fd
    for name in CACHE_COMPONENTS:
        try:
            fd = open_tracked(name, _DIR_FLAGS, parent_fd)
        except OSError as exc:
            return _refuse(_dir_open_outcome(exc, home=False))
        children.append((parent_fd, name, _identity(_fstat(fd))))
        parent_fd = fd
    images_fd = parent_fd
    fire("after_dirs_pinned")

    try:
        file_fd = open_tracked(candidate, _FILE_FLAGS, images_fd)
    except OSError as exc:
        return _refuse(_file_open_outcome(exc))
    fire("after_file_open")

    before = _fstat(file_fd)
    fire("after_first_fstat")
    if not stat.S_ISREG(before.st_mode):
        return _refuse(Outcome.NOT_REGULAR)
    if before.st_nlink != 1:
        return _refuse(Outcome.HARDLINKED)
    if before.st_size <= 0:
        return _refuse(Outcome.EMPTY)
    if before.st_size > max_bytes:
        return _refuse(Outcome.OVERSIZE)

    buffer = bytearray()
    limit = before.st_size + 1  # one past the observed size (<= max_bytes + 1): growth is seen
    try:
        while len(buffer) < limit:
            chunk = os.read(file_fd, min(chunk_size, limit - len(buffer)))
            if not chunk:
                break
            buffer += chunk
            fire("after_chunk")
    except OSError:
        return _refuse(Outcome.READ_FAILED)
    if len(buffer) != before.st_size:
        return _refuse(Outcome.CHANGED_DURING_READ)

    fire("before_second_fstat")
    if _signature(_fstat(file_fd)) != _signature(before):
        return _refuse(Outcome.CHANGED_DURING_READ)

    fire("before_revalidate")
    if not _binding_holds(
        home_path, home_identity, children, images_fd, candidate, before, file_fd
    ):
        return _refuse(Outcome.BINDING_LOST)
    return ReadResult(Outcome.OK, len(buffer), bytes(buffer))


def _binding_holds(
    home_path: str,
    home_identity: tuple[int, int],
    children: list[tuple[int, str, tuple[int, int]]],
    images_fd: int,
    candidate: str,
    opened: os.stat_result,
    file_fd: int,
) -> bool:
    """Every name still leads to the descriptor we hold, whose file still has its first signature.

    Compared internally, never reported. Not atomic: a change after this check is not excluded.
    """
    try:
        if _identity(os.stat(home_path, follow_symlinks=False)) != home_identity:
            return False
        for parent_fd, name, identity in children:
            if _identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != identity:
                return False
        now = os.stat(candidate, dir_fd=images_fd, follow_symlinks=False)
        held = os.fstat(file_fd)
    except OSError:
        return False
    return (
        stat.S_ISREG(now.st_mode)
        and _signature(now) == _signature(opened)
        and _signature(held) == _signature(opened)
    )
