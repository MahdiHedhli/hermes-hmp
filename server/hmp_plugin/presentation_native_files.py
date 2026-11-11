"""Fixed native presentation source transaction; no HTTP or authentication API.

The service must issue a registered claim only after real native authorization.
This reader never adopts an OwnedWorkerRead/GO marker. Results are unparsed,
private bytes; neither a result nor a claim can authorize response emission.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field

from .presentation_budget import PresentationWorkLedger
from .presentation_memory import PresentationMemoryBudget
from .presentation_native_claim import NativeReadClaim, NativeReadRegistry, NativeSourceError

PROFILE_MAX = 65_536
AVATAR_MAX = 2_000_000
AVATARS = ("avatar.png", "avatar.jpg", "avatar.webp")


class PosixPresentationOps:
    """Actual backend selected at native listener setup, never by a request."""

    def __init__(self):
        names = ("O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
        if (
            os.name != "posix"
            or any(not hasattr(os, name) for name in names)
            or os.open not in os.supports_dir_fd
            or os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks
        ):
            raise NativeSourceError("native_source_platform_unavailable")
        self.directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        self.file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        self.open, self.stat, self.fstat = os.open, os.stat, os.fstat
        self.read, self.close = os.read, os.close
        self.ids = lambda: (os.geteuid(), os.getegid())


def _signature(info):
    if type(info) is not os.stat_result:
        raise NativeSourceError()
    row = (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_gid,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    if any(type(value) is not int or value < 0 for value in row):
        raise NativeSourceError()
    return row


@dataclass(eq=False, repr=False)
class NativeSourceFiles:
    """Actual reader return, not parsed data or emission permission.

    Owner must drop aliases before calling discard. No future/exception/log may
    retain the payload; service integration must enforce actual mailbox custody.
    """

    metadata: bytes | None
    avatar: bytes | None
    avatar_name: str | None
    metadata_signature: tuple | None
    avatar_signature: tuple | None
    directories: tuple
    _memory: PresentationMemoryBudget = field(repr=False)
    _leases: list = field(repr=False)

    def __repr__(self):
        return "<NativePresentationSource private>"

    def __copy__(self):
        raise TypeError("native source cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("native source cannot be copied")

    def __reduce__(self):
        raise TypeError("native source cannot be serialized")

    def discard(self):
        self.metadata = self.avatar = None
        while self._leases:
            self._memory.release(self._leases.pop())


class NativePresentationFileReader:
    """One fixed transaction under original native claim/work/memory ownership.

    `ops` is an internal bootstrap dependency/test port. The eventual production
    factory must select PosixPresentationOps itself; it is never request input.
    """

    def __init__(self, registry: NativeReadRegistry, ops=None):
        if type(registry) is not NativeReadRegistry:
            raise NativeSourceError()
        self._registry = registry
        self._ops = PosixPresentationOps() if ops is None else ops

    def read(
        self,
        claim: NativeReadClaim,
        ledger: PresentationWorkLedger,
        memory: PresentationMemoryBudget,
    ) -> NativeSourceFiles:
        if (
            type(claim) is not NativeReadClaim
            or type(ledger) is not PresentationWorkLedger
            or type(memory) is not PresentationMemoryBudget
        ):
            raise NativeSourceError()
        registry = self._registry
        if type(claim._owner) is not NativeReadRegistry or claim._owner is not registry:
            raise NativeSourceError()
        _profile, deadline, home, uid, gid = registry._check(claim)
        if ledger.clock is not registry._clock or ledger.deadline != deadline:
            raise NativeSourceError()
        if self._ops.ids() != (uid, gid):
            raise NativeSourceError()
        registry._start_read(claim)
        try:
            tx = _NativeTransaction(self._ops, claim, ledger, memory, home, uid, gid)
        except BaseException:
            registry._end_read(claim, unknown=False)
            raise NativeSourceError() from None
        result = None
        error = None
        try:
            ledger.begin_file()
            result = tx.run()
        except BaseException as caught:
            error = caught
        finally:
            tx.close_all()
            registry._end_read(claim, unknown=tx.unknown)
        if error is not None or tx.unknown:
            if result is not None:
                result.discard()
            tx.discard_buffers()
            # Never export a native exception/traceback holding source bytes.
            error = None
            raise NativeSourceError(
                "native_source_close_unknown" if tx.unknown else "native_source_unavailable"
            ) from None
        try:
            registry._check(claim)
            ledger.tick()
        except BaseException:
            if result is not None:
                result.discard()
            tx.discard_buffers()
            raise NativeSourceError() from None
        if result is None:
            raise NativeSourceError()
        return result


class _NativeTransaction:
    def __init__(self, ops, claim, ledger, memory, home, uid, gid):
        self.ops, self.claim, self.work, self.memory = ops, claim, ledger, memory
        self.home, self.uid, self.gid = home, uid, gid
        self.owned = []
        self.chain = []
        self.assets = None
        self.assets_signature = None
        self.unknown = False
        self.leases = []

    def tick(self):
        if self.unknown:
            raise NativeSourceError("native_source_close_unknown")
        self.claim._owner._check(self.claim)
        self.work.tick()

    def named(self, parent, name):
        self.tick()
        self.work.charge_path_bytes(len(name.encode("utf-8")))
        self.work.charge_metadata()
        try:
            return _signature(self.ops.stat(name, dir_fd=parent, follow_symlinks=False))
        except FileNotFoundError:
            return None

    def held(self, fd):
        self.tick()
        self.work.charge_metadata()
        return _signature(self.ops.fstat(fd))

    def opening(self, parent, name, flags):
        self.tick()
        self.work.charge_path_bytes(len(name.encode("utf-8")))
        self.work.charge_open()
        if len(self.owned) >= 34:
            raise NativeSourceError()
        try:
            fd = self.ops.open(name, flags, dir_fd=parent)
        except OSError:
            raise NativeSourceError() from None
        except BaseException:
            self.unknown = True
            raise NativeSourceError() from None
        if type(fd) is not int or fd < 0 or fd in self.owned:
            self.unknown = True
            raise NativeSourceError()
        try:
            self.owned.append(fd)
        except BaseException:
            try:
                if self.ops.close(fd) is not None:
                    self.unknown = True
            except BaseException:
                self.unknown = True
            raise
        return fd

    def closing(self, fd):
        self.owned.remove(fd)  # Never retry an ambiguous number after reuse.
        try:
            if self.ops.close(fd) is not None:
                self.unknown = True
        except BaseException:
            self.unknown = True

    def close_all(self):
        # Deadline/retirement cannot prevent closing original retained handles.
        while self.owned:
            self.closing(self.owned[-1])

    def directory(self, row, *, home=False):
        if (
            row is None
            or not stat.S_ISDIR(row[2])
            or row[3] not in (0, self.uid)
            or row[2] & (stat.S_ISUID | stat.S_ISGID)
        ):
            raise NativeSourceError()
        mode = stat.S_IMODE(row[2])
        sticky_ancestor = not home and row[3] == 0 and bool(mode & stat.S_ISVTX)
        if mode & 0o022 and not sticky_ancestor:
            raise NativeSourceError()
        if home and (row[3] != self.uid or row[4] != self.gid or mode not in (0o700, 0o750, 0o755)):
            raise NativeSourceError()

    def open_chain(self):
        parts = self.home.split("/")[1:]
        for index, name in enumerate(("/", *parts)):
            parent = None if not self.chain else self.chain[-1][0]
            before = self.named(parent, name)
            self.directory(before, home=index == len(parts))
            fd = self.opening(parent, name, self.ops.directory_flags)
            if self.held(fd)[:5] != before[:5]:
                raise NativeSourceError()
            self.chain.append((fd, parent, name, before[:5]))
        return self.chain[-1][0]

    def verify_chain(self):
        for fd, parent, name, expected in self.chain:
            held, named = self.held(fd), self.named(parent, name)
            if named is None or held[:5] != expected or named[:5] != expected:
                raise NativeSourceError()
            self.directory(held, home=fd == self.chain[-1][0])
        if self.assets is not None:
            named, held = self.named(self.chain[-1][0], "assets"), self.held(self.assets)
            if named is None or named[:5] != self.assets_signature or held[:5] != named[:5]:
                raise NativeSourceError()
            self.directory(held, home=True)

    def leaf(self, row, maximum):
        if row is None:
            return
        if (
            not stat.S_ISREG(row[2])
            or row[5] != 1
            or row[3:5] != (self.uid, self.gid)
            or stat.S_IMODE(row[2]) not in (0o600, 0o640, 0o644)
            or not 1 <= row[6] <= maximum
        ):
            raise NativeSourceError()

    def presence(self, home):
        metadata = self.named(home, "profile.yaml")
        self.leaf(metadata, PROFILE_MAX)
        assets = self.named(home, "assets")
        if self.assets is None:
            if assets is not None:
                raise NativeSourceError()
            return metadata, None, None
        if assets is None or assets[:5] != self.assets_signature:
            raise NativeSourceError()
        found = [
            (name, row) for name in AVATARS if (row := self.named(self.assets, name)) is not None
        ]
        if len(found) > 1:
            raise NativeSourceError()
        if not found:
            return metadata, None, None
        name, row = found[0]
        self.leaf(row, AVATAR_MAX)
        return metadata, name, row

    def read_leaf(self, parent, name, signature, maximum):
        self.verify_chain()
        if self.named(parent, name) != signature:
            raise NativeSourceError()
        self.leaf(signature, maximum)
        fd = self.opening(parent, name, self.ops.file_flags)
        chunks, leases = [], []
        conversion = None
        body = None
        try:
            if self.held(fd) != signature:
                raise NativeSourceError()
            remaining = signature[6]
            while remaining:
                self.tick()
                count = min(remaining, 8192 if maximum == PROFILE_MAX else 65536)
                self.work.charge_read_bytes(count)
                ticket = self.memory.reserve("file", count)
                leases.append(ticket)
                data = self.ops.read(fd, count)
                if type(data) is not bytes or not data or len(data) > count:
                    raise NativeSourceError()
                chunks.append(data)
                remaining -= len(data)
            self.tick()
            self.work.charge_read_bytes(1)
            # Even a refused growth byte is owned before the result is checked.
            leases.append(self.memory.reserve("file", 1))
            extra = self.ops.read(fd, 1)
            if type(extra) is not bytes or extra != b"":
                raise NativeSourceError()
            if self.held(fd) != signature or self.named(parent, name) != signature:
                raise NativeSourceError()
            conversion = self.memory.reserve("conversion", signature[6])
            body = b"".join(chunks)
            if len(body) != signature[6]:
                raise NativeSourceError()
            self.leases.append(conversion)
            conversion = None
            return body
        except BaseException:
            body = None
            raise
        finally:
            chunks.clear()
            data = extra = b""
            while leases:
                self.memory.release(leases.pop())
            if conversion is not None:
                self.memory.release(conversion)
            self.closing(fd)

    def discard_buffers(self):
        while self.leases:
            self.memory.release(self.leases.pop())

    def run(self):
        metadata = avatar = repeated = original = result = None
        try:
            home = self.open_chain()
            assets = self.named(home, "assets")
            if assets is not None:
                self.directory(assets, home=True)
                self.assets = self.opening(home, "assets", self.ops.directory_flags)
                if self.held(self.assets)[:5] != assets[:5]:
                    raise NativeSourceError()
                self.assets_signature = assets[:5]
            expected = self.presence(home)
            metadata_sig, avatar_name, avatar_sig = expected
            metadata = (
                None
                if metadata_sig is None
                else self.read_leaf(home, "profile.yaml", metadata_sig, PROFILE_MAX)
            )
            avatar = (
                None
                if avatar_sig is None
                else self.read_leaf(self.assets, avatar_name, avatar_sig, AVATAR_MAX)
            )
            if self.presence(home) != expected:
                raise NativeSourceError()
            for parent, name, signature, maximum, original in (
                (home, "profile.yaml", metadata_sig, PROFILE_MAX, metadata),
                (self.assets, avatar_name, avatar_sig, AVATAR_MAX, avatar),
            ):
                if signature is not None:
                    repeated = self.read_leaf(parent, name, signature, maximum)
                    if repeated != original:
                        raise NativeSourceError()
                    repeated = None
                    self.memory.release(self.leases.pop())
            self.verify_chain()
            if self.presence(home) != expected:
                raise NativeSourceError()
            result = NativeSourceFiles(
                metadata,
                avatar,
                avatar_name,
                metadata_sig,
                avatar_sig,
                tuple(row[3] for row in self.chain),
                self.memory,
                self.leases,
            )
            self.leases = []
            return result
        except BaseException:
            metadata = avatar = repeated = original = result = None
            raise
