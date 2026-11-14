"""Worker-only, fixed-name BI1 presentation file transaction.

This module neither creates a worker nor authenticates a request.  The future
owned worker must bind an ``OwnedWorkerRead`` only after its reviewed GO frame.
Every filesystem operation is performed through the explicit ``fs`` argument;
there is no default OS backend and import performs no filesystem operation.
Returned bytes are unparsed and cannot be exposed as a BI1 response.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from .presentation_budget import PresentationWorkLedger

PROFILE_MAX = 65_536
AVATAR_MAX = 2_000_000
READ_CREDIT = 2 * (PROFILE_MAX + AVATAR_MAX) + 4
OPEN_CREDIT = 80
META_CREDIT = 1024
NAME_CREDIT = 32_768
FD_CREDIT = 34
MAX_COMPONENTS = 32  # Includes the absolute root directory.
MAX_PATH_BYTES = 4096
AVATARS = ("avatar.png", "avatar.jpg", "avatar.webp")
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
LEAF_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
_BOUND = object()


class PresentationReadError(Exception):
    """Closed refusal; labels contain no profile path or file content."""

    def __init__(self, label: str):
        super().__init__(label)
        self.label = label


class UnknownCloseError(PresentationReadError):
    """At least one close outcome is unknown; no descriptor number is retried."""

    def __init__(self, original: BaseException | None, labels: tuple[str, ...]):
        super().__init__("UNKNOWN_CLOSE")
        self.original = original
        self.close_labels = labels


@dataclass(frozen=True)
class DirectoryRule:
    path: str
    uid: int
    gid: int
    modes: tuple[int, ...]


@dataclass(frozen=True)
class OwnedWorkerRead:
    """Job-local scope; marker is not credential or native authorization."""

    root_path: str
    home_path: str
    profile: str | None
    service_uid: int
    service_gid: int
    directory_rules: tuple[DirectoryRule, ...]
    deadline: float
    challenge: str
    source_manifest_sha256: str
    _bound: object


def bind_owned_worker_read(
    *,
    root_path: str,
    home_path: str,
    profile: str | None,
    service_uid: int,
    service_gid: int,
    directory_rules: tuple[DirectoryRule, ...],
    deadline: float,
    challenge: str,
    source_manifest_sha256: str,
    worker_go_challenge: str,
) -> OwnedWorkerRead:
    """Bind only inside the future worker after its owned GO-frame check.

    The caller must supply the challenge observed on the worker's owned GO
    frame.  This equality is a local binding check, not native authority;
    no HMP route may call this until the owner/custody protocol is reviewed.
    """
    if type(worker_go_challenge) is not str or worker_go_challenge != challenge:
        raise PresentationReadError("WORKER_UNBOUND")
    if type(service_uid) is not int or type(service_gid) is not int:
        raise PresentationReadError("IDENTITY_SCHEMA")
    if service_uid <= 0 or service_gid < 0:
        raise PresentationReadError("IDENTITY_SCHEMA")
    if type(deadline) is not float or not 0 < deadline < float("inf"):
        raise PresentationReadError("DEADLINE_SCHEMA")
    if type(challenge) is not str or not 16 <= len(challenge) <= 128:
        raise PresentationReadError("CHALLENGE_SCHEMA")
    if type(source_manifest_sha256) is not str or not re.fullmatch(
        r"[0-9a-f]{64}", source_manifest_sha256
    ):
        raise PresentationReadError("SOURCE_SCHEMA")
    if profile is not None and (type(profile) is not str or not _PROFILE.fullmatch(profile)):
        raise PresentationReadError("PROFILE_SCHEMA")
    root = _components(root_path)
    home = _components(home_path)
    if profile is None:
        if home != root:
            raise PresentationReadError("HOME_GEOMETRY")
    elif home != (*root, "profiles", profile):
        raise PresentationReadError("HOME_GEOMETRY")
    if type(directory_rules) is not tuple:
        raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
    prefixes = _prefixes(home)
    if len(directory_rules) != len(prefixes):
        raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
    for expected, rule in zip(prefixes, directory_rules, strict=True):
        if type(rule) is not DirectoryRule or rule.path != expected:
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if type(rule.uid) is not int or type(rule.gid) is not int:
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if rule.uid not in (0, service_uid) or rule.gid < 0:
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if type(rule.modes) is not tuple or not rule.modes:
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if any(type(mode) is not int or mode not in (0o700, 0o750, 0o755) for mode in rule.modes):
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if expected == "/" and (rule.uid != 0 or rule.gid != 0):
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
        if expected in (root_path, home_path) and (
            rule.uid != service_uid or rule.gid != service_gid
        ):
            raise PresentationReadError("DIRECTORY_POLICY_SCHEMA")
    return OwnedWorkerRead(
        root_path,
        home_path,
        profile,
        service_uid,
        service_gid,
        directory_rules,
        deadline,
        challenge,
        source_manifest_sha256,
        _BOUND,
    )


def _components(path: str) -> tuple[str, ...]:
    if type(path) is not str or not path.startswith("/") or "\x00" in path:
        raise PresentationReadError("PATH_SCHEMA")
    encoded = path.encode("utf-8", errors="strict")
    if len(encoded) > MAX_PATH_BYTES or (path != "/" and path.endswith("/")):
        raise PresentationReadError("PATH_SCHEMA")
    parts = () if path == "/" else tuple(path[1:].split("/"))
    if len(parts) + 1 > MAX_COMPONENTS or any(p in ("", ".", "..") for p in parts):
        raise PresentationReadError("PATH_SCHEMA")
    return parts


def _prefixes(parts: tuple[str, ...]) -> tuple[str, ...]:
    rows = ["/"]
    for part in parts:
        rows.append(rows[-1].rstrip("/") + "/" + part)
    return tuple(rows)


class FileOps(Protocol):
    def open(self, path: str, flags: int, *, dir_fd: int | None = None) -> int: ...
    def stat(self, path: str, *, dir_fd: int | None = None, follow_symlinks: bool = False): ...
    def fstat(self, fd: int): ...
    def read(self, fd: int, size: int) -> bytes: ...
    def lseek(self, fd: int, offset: int, whence: int) -> int: ...
    def close(self, fd: int) -> None: ...


def _nine(row: object) -> tuple[int, ...]:
    names = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    try:
        values = tuple(getattr(row, key) for key in names)
    except (AttributeError, TypeError) as exc:
        raise PresentationReadError("METADATA_SCHEMA") from exc
    if any(type(value) is not int or value < 0 for value in values):
        raise PresentationReadError("METADATA_SCHEMA")
    return values


class _Budget:
    def __init__(
        self,
        deadline: float,
        clock: Callable[[], float],
        ledger: PresentationWorkLedger | None = None,
    ):
        self.ledger = ledger
        self.deadline = deadline
        self.clock = clock
        self.read_bytes = 0
        self.opens = 0
        self.metadata = 0
        self.name_bytes = 0
        self.live = 0
        self.peak_live = 0
        self.unknown_close = False

    def tick(self) -> None:
        now = self.clock()
        if type(now) is not float or not 0 <= now < self.deadline:
            raise PresentationReadError("DEADLINE")
        if self.unknown_close:
            raise PresentationReadError("UNKNOWN_CLOSE")

    def name(self, name: str) -> None:
        self.tick()
        length = len(name.encode("utf-8"))
        if self.name_bytes + length > NAME_CREDIT:
            raise PresentationReadError("NAME_CREDIT")
        if self.ledger is not None:
            self.ledger.charge_path_bytes(length)
        self.name_bytes += length

    def meta(self) -> None:
        self.tick()
        if self.metadata >= META_CREDIT:
            raise PresentationReadError("META_CREDIT")
        if self.ledger is not None:
            self.ledger.charge_metadata()
        self.metadata += 1

    def opening(self) -> None:
        self.tick()
        if self.opens >= OPEN_CREDIT or self.live >= FD_CREDIT:
            raise PresentationReadError("OPEN_CREDIT")
        if self.ledger is not None:
            self.ledger.charge_open()
        self.opens += 1

    def acquired(self) -> None:
        self.live += 1
        self.peak_live = max(self.live, self.peak_live)

    def read(self, amount: int) -> None:
        self.tick()
        if type(amount) is not int or amount < 1 or self.read_bytes + amount > READ_CREDIT:
            raise PresentationReadError("READ_CREDIT")
        if self.ledger is not None:
            self.ledger.charge_read_bytes(amount)
        self.read_bytes += amount

    def snapshot(self) -> dict[str, int]:
        return {
            "readBytesCharged": self.read_bytes,
            "opensCharged": self.opens,
            "metadataCharged": self.metadata,
            "nameBytesCharged": self.name_bytes,
            "peakTargetFDs": self.peak_live,
        }


class _Transaction:
    def __init__(self, fs: FileOps, budget: _Budget, scope: OwnedWorkerRead):
        self.fs = fs
        self.budget = budget
        self.scope = scope
        self.owned: list[int] = []
        self.chain: list[tuple[int, int | None, str, tuple[int, ...], DirectoryRule]] = []
        self.assets_fd: int | None = None
        self.assets_nine: tuple[int, ...] | None = None

    def _named(self, parent: int | None, name: str) -> tuple[int, ...] | None:
        self.budget.name(name)
        self.budget.meta()
        try:
            row = self.fs.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return None
        except BaseException as exc:
            raise PresentationReadError("NAMED_STAT") from exc
        return _nine(row)

    def _held(self, fd: int) -> tuple[int, ...]:
        self.budget.meta()
        try:
            return _nine(self.fs.fstat(fd))
        except BaseException as exc:
            raise PresentationReadError("HELD_STAT") from exc

    def _open(self, parent: int | None, name: str, flags: int) -> int:
        self.budget.name(name)
        self.budget.opening()
        try:
            fd = self.fs.open(name, flags, dir_fd=parent)
        except BaseException as exc:
            raise PresentationReadError("OPEN") from exc
        if type(fd) is not int or fd < 0 or fd in self.owned:
            raise PresentationReadError("FD_SCHEMA")
        try:
            self.owned.append(fd)  # Ownership precedes fstat/identity validation.
        except BaseException as original:
            try:
                self.fs.close(fd)
            except BaseException:
                self.budget.unknown_close = True
                raise UnknownCloseError(original, ("TARGET_FD_CLOSE",)) from original
            raise
        self.budget.acquired()
        return fd

    def _close_one(self, fd: int) -> None:
        if fd not in self.owned:
            raise PresentationReadError("FD_OWNERSHIP")
        self.owned.remove(fd)  # Ambiguous close number is never retried.
        try:
            self.fs.close(fd)
        except BaseException as exc:
            self.budget.unknown_close = True
            raise UnknownCloseError(exc, ("TARGET_FD_CLOSE",)) from exc
        self.budget.live -= 1

    def close_all(self, original: BaseException | None) -> None:
        failures: list[str] = []
        first_close_error: BaseException | None = None
        while self.owned:
            fd = self.owned.pop()
            try:
                self.fs.close(fd)
            except BaseException as exc:
                self.budget.unknown_close = True
                failures.append("TARGET_FD_CLOSE")
                if first_close_error is None:
                    first_close_error = exc
            else:
                self.budget.live -= 1
        if failures:
            cause = original if original is not None else first_close_error
            raise UnknownCloseError(cause, tuple(failures)) from cause

    def _check_dir(self, row: tuple[int, ...], rule: DirectoryRule) -> None:
        if stat.S_IFMT(row[2]) != stat.S_IFDIR:
            raise PresentationReadError("DIRECTORY_TYPE")
        if row[3] != rule.uid or row[4] != rule.gid or stat.S_IMODE(row[2]) not in rule.modes:
            raise PresentationReadError("DIRECTORY_POLICY")
        if stat.S_IMODE(row[2]) & 0o022:
            raise PresentationReadError("DIRECTORY_WRITE_MODE")

    def _open_chain(self) -> int:
        for i, rule in enumerate(self.scope.directory_rules):
            parent = self.chain[-1][0] if self.chain else None
            name = "/" if i == 0 else rule.path.rsplit("/", 1)[1]
            before = self._named(parent, name)
            if before is None:
                raise PresentationReadError("DIRECTORY_MISSING")
            self._check_dir(before, rule)
            fd = self._open(parent, name, DIR_FLAGS)
            held = self._held(fd)
            if held != before:
                raise PresentationReadError("DIRECTORY_BINDING")
            self.chain.append((fd, parent, name, held, rule))
        return self.chain[-1][0]

    def _verify_chain(self) -> None:
        for fd, parent, name, expected, rule in self.chain:
            held = self._held(fd)
            named = self._named(parent, name)
            if named != expected or held != expected:
                raise PresentationReadError("DIRECTORY_CHANGED")
            self._check_dir(held, rule)
        if self.assets_fd is not None:
            held = self._held(self.assets_fd)
            named = self._named(self.chain[-1][0], "assets")
            if named != self.assets_nine or held != self.assets_nine:
                raise PresentationReadError("ASSETS_CHANGED")

    def _assets(self, home_fd: int) -> None:
        before = self._named(home_fd, "assets")
        if before is None:
            return
        rule = DirectoryRule(
            self.scope.home_path.rstrip("/") + "/assets",
            self.scope.service_uid,
            self.scope.service_gid,
            (0o700, 0o750, 0o755),
        )
        self._check_dir(before, rule)
        fd = self._open(home_fd, "assets", DIR_FLAGS)
        held = self._held(fd)
        if before != held:
            raise PresentationReadError("ASSETS_BINDING")
        self.assets_fd = fd
        self.assets_nine = held

    def _presence(
        self, home_fd: int
    ) -> tuple[tuple[int, ...] | None, str | None, tuple[int, ...] | None]:
        profile_row = self._named(home_fd, "profile.yaml")
        if profile_row is not None:
            self._check_leaf(profile_row, PROFILE_MAX)
        assets_row = self._named(home_fd, "assets")
        if self.assets_fd is None:
            if assets_row is not None:
                raise PresentationReadError("ASSETS_CHANGED")
            return profile_row, None, None
        if assets_row != self.assets_nine:
            raise PresentationReadError("ASSETS_CHANGED")
        present = [
            (name, row)
            for name in AVATARS
            if (row := self._named(self.assets_fd, name)) is not None
        ]
        if len(present) > 1:
            raise PresentationReadError("MULTIPLE_AVATARS")
        if not present:
            return profile_row, None, None
        name, row = present[0]
        self._check_leaf(row, AVATAR_MAX)
        return profile_row, name, row

    def _check_leaf(self, row: tuple[int, ...], maximum: int) -> None:
        if stat.S_IFMT(row[2]) != stat.S_IFREG or row[5] != 1:
            raise PresentationReadError("LEAF_TYPE")
        if row[3] != self.scope.service_uid or row[4] != self.scope.service_gid:
            raise PresentationReadError("LEAF_OWNER")
        if stat.S_IMODE(row[2]) not in (0o600, 0o640, 0o644):
            raise PresentationReadError("LEAF_MODE")
        if not 1 <= row[6] <= maximum:
            raise PresentationReadError("LEAF_SIZE")

    def _read_leaf(
        self, parent: int, name: str, expected: tuple[int, ...], maximum: int
    ) -> tuple[bytes, str]:
        self._verify_chain()
        before = self._named(parent, name)
        if before != expected:
            raise PresentationReadError("LEAF_CHANGED")
        self._check_leaf(before, maximum)
        fd = self._open(parent, name, LEAF_FLAGS)
        original: BaseException | None = None
        body: bytes | None = None
        body_sha256: str | None = None
        try:
            if self._held(fd) != expected:
                raise PresentationReadError("LEAF_BINDING")
            remaining = expected[6]
            chunks: list[bytes] = []
            digest = hashlib.sha256()
            chunk_limit = 8192 if maximum == PROFILE_MAX else 65536
            while remaining:
                count = min(remaining, chunk_limit)
                self.budget.read(count)
                try:
                    part = self.fs.read(fd, count)
                except BaseException as exc:
                    raise PresentationReadError("BODY_READ") from exc
                if type(part) is not bytes or not part or len(part) > count:
                    raise PresentationReadError("BODY_TRUNCATED")
                digest.update(part)
                chunks.append(part)
                remaining -= len(part)
            self.budget.read(1)  # EOF byte is charged before the syscall.
            try:
                extra = self.fs.read(fd, 1)
            except BaseException as exc:
                raise PresentationReadError("EOF_READ") from exc
            if extra != b"":
                raise PresentationReadError("BODY_EXTENDED")
            if self._held(fd) != expected or self._named(parent, name) != expected:
                raise PresentationReadError("LEAF_CHANGED")
            body = b"".join(chunks)
            if len(body) != expected[6]:
                raise PresentationReadError("BODY_SIZE")
            body_sha256 = digest.hexdigest()
        except BaseException as exc:
            original = exc
        try:
            self._close_one(fd)
        except UnknownCloseError as close_error:
            cause = original if original is not None else close_error.original
            raise UnknownCloseError(cause, close_error.close_labels) from cause
        if original is not None:
            raise original
        if body is None or body_sha256 is None:
            raise PresentationReadError("BODY_MISSING")
        return body, body_sha256

    def run(self) -> FixedReadResult:
        home_fd = self._open_chain()
        self._assets(home_fd)
        self._verify_chain()
        first_profile, first_avatar_name, first_avatar = self._presence(home_fd)
        metadata = None
        avatar = None
        metadata_sha256 = None
        avatar_sha256 = None
        if first_profile is not None:
            metadata, metadata_sha256 = self._read_leaf(
                home_fd, "profile.yaml", first_profile, PROFILE_MAX
            )
        if first_avatar_name is not None and first_avatar is not None:
            if self.assets_fd is None:
                raise PresentationReadError("ASSETS_MISSING")
            avatar, avatar_sha256 = self._read_leaf(
                self.assets_fd, first_avatar_name, first_avatar, AVATAR_MAX
            )
        self._verify_chain()
        final_profile, final_avatar_name, final_avatar = self._presence(home_fd)
        if (final_profile, final_avatar_name, final_avatar) != (
            first_profile,
            first_avatar_name,
            first_avatar,
        ):
            raise PresentationReadError("PRESENCE_CHANGED")
        if metadata is not None:
            final_metadata, final_metadata_sha256 = self._read_leaf(
                home_fd, "profile.yaml", first_profile, PROFILE_MAX
            )
            if metadata != final_metadata or metadata_sha256 != final_metadata_sha256:
                raise PresentationReadError("METADATA_BODY_CHANGED")
        if avatar is not None and first_avatar_name is not None and first_avatar is not None:
            if self.assets_fd is None:
                raise PresentationReadError("ASSETS_MISSING")
            final_avatar, final_avatar_sha256 = self._read_leaf(
                self.assets_fd, first_avatar_name, first_avatar, AVATAR_MAX
            )
            if avatar != final_avatar or avatar_sha256 != final_avatar_sha256:
                raise PresentationReadError("AVATAR_BODY_CHANGED")
        self._verify_chain()
        last_profile, last_avatar_name, last_avatar = self._presence(home_fd)
        if (last_profile, last_avatar_name, last_avatar) != (
            first_profile,
            first_avatar_name,
            first_avatar,
        ):
            raise PresentationReadError("PRESENCE_CHANGED")
        self._verify_chain()
        return FixedReadResult(
            metadata=metadata,
            avatar=avatar,
            avatar_name=first_avatar_name,
            metadata_sha256=metadata_sha256,
            avatar_sha256=avatar_sha256,
            metadata_nine=first_profile,
            avatar_nine=first_avatar,
            directory_nines=tuple((rule.path, row) for _, _, _, row, rule in self.chain),
            budget=self.budget.snapshot(),
            raster_and_yaml_unvalidated=True,
            work_ledger=self.budget.ledger,
        )


@dataclass(frozen=True)
class FixedReadResult:
    metadata: bytes | None
    avatar: bytes | None
    avatar_name: str | None
    metadata_sha256: str | None
    avatar_sha256: str | None
    metadata_nine: tuple[int, ...] | None
    avatar_nine: tuple[int, ...] | None
    directory_nines: tuple[tuple[str, tuple[int, ...]], ...]
    budget: dict[str, int]
    raster_and_yaml_unvalidated: bool
    work_ledger: PresentationWorkLedger | None = field(default=None, repr=False)


def read_fixed_presentation_files(
    scope: OwnedWorkerRead,
    *,
    fs: FileOps,
    clock: Callable[[], float],
    ledger: PresentationWorkLedger | None = None,
) -> FixedReadResult:
    """Run one entire fixed-name transaction in the owning disposable worker.

    ``fs`` is mandatory: there is deliberately no implicit real-OS backend.
    This local marker only prevents accidental unbound calls; the parent native
    authority/custody protocol remains unimplemented and cannot be bypassed by
    treating this marker as an authentication credential.
    """
    if type(scope) is not OwnedWorkerRead or scope._bound is not _BOUND:
        raise PresentationReadError("WORKER_UNBOUND")
    if ledger is not None:
        if (
            type(ledger) is not PresentationWorkLedger
            or ledger.clock is not clock
            or ledger.deadline != scope.deadline
        ):
            raise PresentationReadError("WORK_SCOPE")
        ledger.begin_file()
    budget = _Budget(scope.deadline, clock, ledger)
    tx = _Transaction(fs, budget, scope)
    original: BaseException | None = None
    result: FixedReadResult | None = None
    try:
        result = tx.run()
    except BaseException as exc:
        original = exc
    try:
        tx.close_all(original)
    except UnknownCloseError as close_error:
        raise close_error
    if original is not None:
        raise original
    if result is None:
        raise PresentationReadError("RESULT_MISSING")
    if budget.live != 0:
        raise PresentationReadError("FD_LEDGER")
    budget.tick()  # A delayed final close or result copy cannot become success.
    return result
