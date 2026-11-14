"""Owned directory-only policy observation; not native permission/thread proof.

The future native binder must reserve the exact job slice and authenticate before
calling run, retain its actual thread, reauthenticate afterward and seal once.
"""

from __future__ import annotations

import os
import stat
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .presentation_budget import PresentationWorkLedger
from .presentation_files import DirectoryRule, FileOps, _components, _nine, _prefixes
from .presentation_jobs import _PROFILE, FrameError


@dataclass
class _HeldDirectory:
    fd: int
    parent: int | None
    name: str
    signature: tuple[int, ...]
    rule: DirectoryRule
    close_attempted: bool = False
    closed: bool = False


@dataclass(frozen=True)
class ParentPolicySnapshot:
    rules: tuple[DirectoryRule, ...]
    chain: tuple[tuple[int, ...], ...]
    counts: Mapping[str, int]


class ParentPolicyReadOwner:
    def __init__(
        self,
        *,
        root: str,
        home: str,
        profile: str,
        uid: int,
        gid: int,
        ledger: PresentationWorkLedger,
        fs: FileOps,
        current: Callable[[], bool],
    ):
        if type(root) is not str or type(home) is not str or len(root) > 4096 or len(home) > 4096:
            raise FrameError("BI1_PARENT_SCOPE_REFUSED")
        roots, homes = _components(root), _components(home)
        if (
            not roots
            or type(profile) is not str
            or _PROFILE.fullmatch(profile) is None
            or homes != (roots if profile == "default" else (*roots, "profiles", profile))
            or type(uid) is not int
            or not 1 <= uid < 1 << 31
            or type(gid) is not int
            or not 0 <= gid < 1 << 31
            or (os.geteuid(), os.getegid()) != (uid, gid)
            or type(ledger) is not PresentationWorkLedger
        ):
            raise FrameError("BI1_PARENT_SCOPE_REFUSED")
        self._root, self._home = root, home
        self._uid, self._gid = uid, gid
        self._paths = _prefixes(homes)
        self._names = ("/", *homes)
        self._ledger, self._fs, self._current = ledger, fs, current
        self._held: list[_HeldDirectory] = []
        self._lock = threading.Lock()
        self._attempted = False
        self._pending_fd: object = None
        self._pending_close_attempted = False
        self.uncertain = False
        self._unknown_acquisition: object = None
        self._failure: BaseException | None = None
        self._cleanup_errors: list[BaseException] = []

    @property
    def descriptors_closed(self) -> bool:
        return (
            not self.uncertain
            and self._pending_fd is None
            and all(row.closed for row in self._held)
        )

    def _tick(self) -> None:
        current = self._current()
        self._ledger.tick()
        if self.uncertain or current is not True:
            raise FrameError("BI1_PARENT_CURRENT_REFUSED")

    def _stat(self, name: str, parent: int | None) -> tuple[int, ...]:
        self._ledger.charge_path_bytes(len(name.encode("utf-8")))
        self._ledger.charge_metadata()
        self._tick()
        row = self._fs.stat(name, dir_fd=parent, follow_symlinks=False)
        self._tick()
        return _nine(row)

    def _held_stat(self, fd: int) -> tuple[int, ...]:
        self._ledger.charge_metadata()
        self._tick()
        row = self._fs.fstat(fd)
        self._tick()
        return _nine(row)

    def _rule(self, path: str, sig: tuple[int, ...]) -> DirectoryRule:
        if any(value >= 1 << 63 for value in sig):
            raise FrameError("BI1_PARENT_POLICY_REFUSED")
        mode, uid, gid = sig[2:5]
        permissions = stat.S_IMODE(mode)
        if (
            not stat.S_ISDIR(mode)
            or uid not in (0, self._uid)
            or gid >= 1 << 31
            or permissions not in (0o700, 0o750, 0o755)
            or (path == "/" and (uid, gid) != (0, 0))
            or (path in (self._root, self._home) and (uid, gid) != (self._uid, self._gid))
        ):
            raise FrameError("BI1_PARENT_POLICY_REFUSED")
        return DirectoryRule(path, uid, gid, (permissions,))

    def run(self) -> ParentPolicySnapshot:
        if not self._lock.acquire(blocking=False):
            self.uncertain = True
            raise FrameError("BI1_PARENT_REENTRY")
        try:
            return self._run_owned()
        except BaseException as error:
            if self._failure is None:
                self._failure = error
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_PARENT_READ_REFUSED") from None
        finally:
            self._lock.release()

    def _run_owned(self) -> ParentPolicySnapshot:
        try:
            if self._attempted:
                self.uncertain = True
                raise FrameError("BI1_PARENT_REPLAY_REFUSED")
            self._attempted = True
            self._tick()
            self._ledger.begin_parent_policy()
            parent = None
            for path, name in zip(self._paths, self._names, strict=True):
                named = self._stat(name, parent)
                rule = self._rule(path, named)
                self._ledger.charge_path_bytes(len(name.encode("utf-8")))
                self._ledger.charge_open()
                self._tick()
                try:
                    fd = self._fs.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=parent,
                    )
                except BaseException as error:
                    self._unknown_acquisition = error
                    self.uncertain = True
                    raise FrameError("BI1_PARENT_OPEN_UNCERTAIN") from None
                self._pending_fd = fd
                if type(fd) is not int or fd < 0:
                    self._unknown_acquisition = fd
                    self.uncertain = True
                    raise FrameError("BI1_PARENT_OPEN_UNCERTAIN")
                held = _HeldDirectory(fd, parent, name, named, rule)
                self._held.append(held)  # retain before checks or subsequent IO
                self._pending_fd = None
                self._tick()
                if self._held_stat(fd) != named:
                    raise FrameError("BI1_PARENT_CHANGED")
                parent = fd
            for held in self._held:
                if (
                    self._held_stat(held.fd) != held.signature
                    or self._stat(held.name, held.parent) != held.signature
                ):
                    raise FrameError("BI1_PARENT_CHANGED")
                self._rule(held.rule.path, held.signature)
        finally:
            if (
                type(self._pending_fd) is int
                and self._pending_fd >= 0
                and not self._pending_close_attempted
            ):
                self._pending_close_attempted = True
                try:
                    self._fs.close(self._pending_fd)
                    self._pending_fd = None
                except BaseException as error:
                    self.uncertain = True
                    self._cleanup_errors.append(error)
            for held in reversed(self._held):
                if held.close_attempted:
                    continue
                held.close_attempted = True
                try:
                    self._fs.close(held.fd)
                    held.closed = True
                except BaseException as error:
                    self.uncertain = True
                    self._cleanup_errors.append(error)
        if not self.descriptors_closed:
            raise FrameError("BI1_PARENT_CLOSE_UNCERTAIN")
        self._tick()
        counts = PresentationWorkLedger.validate_parent_counts(self._home, self._ledger.snapshot())
        snapshot = ParentPolicySnapshot(
            tuple(row.rule for row in self._held),
            tuple(row.signature for row in self._held),
            MappingProxyType(counts),
        )
        self._tick()
        return snapshot
