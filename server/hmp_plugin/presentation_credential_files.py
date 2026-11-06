"""Bounded startup-only role key custody, not runtime or operation admission.

Operator selection/inventory and authorized installation precede this loader.
No request path calls it. Root/local administrator and installed runtime remain
trusted; private modes do not isolate hostile same-UID code or fork snapshots.
No signing API or credential generation is exposed here.
"""

from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .presentation_jobs import FrameError


class CredentialAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_CREDENTIAL_FILES_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_FILES_REFUSED")


def _identity(row):
    stable = (row.st_dev, row.st_ino, row.st_mode, row.st_uid, row.st_gid)
    # Shared ancestors can gain unrelated entries. Their name/inode/type/owner/
    # mode join matters; incidental directory size/mtime/link count is not key
    # selection. Each fixed key leaf separately retains full metadata below.
    if stat.S_ISDIR(row.st_mode):
        return stable
    return (*stable, row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns)


@dataclass(repr=False)
class _HeldFile:
    fd: int | None = None
    identity: tuple | None = None
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False


@dataclass(frozen=True, repr=False)
class RoleKeySelection:
    """Operator-selected data; does not attest an admitted runtime inventory."""

    directory: str
    role: str
    generation: str
    own_public: bytes = field(repr=False)
    peer_public: bytes = field(repr=False)


class StartupRoleKeyFiles:
    """Partial FD owner retained on every failure; no signer or permission token.

    Successful loading closes all original descriptors before marking ready.
    A failed close is never retried against a potentially reused descriptor.
    The paired startup factory must retain this exact object and separately
    establish runtime/source generation, key retirement and phase ownership.
    """

    def __init__(self, selection: RoleKeySelection):
        if type(self) is not StartupRoleKeyFiles or "_initialized" in vars(self):
            raise CredentialAcquisitionError(self) from None
        self._initialized = True
        self._selection = selection
        self._records = []
        self._refused = False
        self._ready = False
        self._private_key = None
        self._boot = None
        self._process = (os.getpid(), os.geteuid())
        values = []
        seed = data = key = own_public = peer_public = derived = None
        failed = False
        try:
            _require(type(selection) is RoleKeySelection and os.name == "posix")
            _require(
                type(selection.directory) is str
                and selection.directory.startswith("/")
                and 1 < len(selection.directory.encode("utf-8")) <= 4096
                and all(32 <= ord(c) != 127 for c in selection.directory)
            )
            parts = selection.directory[1:].split("/")
            _require(len(parts) <= 64 and all(p not in ("", ".", "..") for p in parts))
            _require(type(selection.role) is str and selection.role in ("gateway", "broker"))
            _require(
                type(selection.generation) is str
                and len(selection.generation) == 64
                and all(c in "0123456789abcdef" for c in selection.generation)
            )
            _require(
                all(
                    type(key) is bytes and len(key) == 32
                    for key in (selection.own_public, selection.peer_public)
                )
            )
            _require(selection.own_public != selection.peer_public)
            uid = os.geteuid()
            _require(type(uid) is int and uid > 0)
            parent = None
            directories = []
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            for index, name in enumerate(("/", *parts)):
                held = self._open(name, flags, parent)
                row = os.fstat(held.fd)
                mode = stat.S_IMODE(row.st_mode)
                _require(stat.S_ISDIR(row.st_mode) and row.st_nlink >= 1)
                if index == len(parts):
                    _require(row.st_uid == uid and mode == 0o700)
                else:
                    _require(
                        row.st_uid in (0, uid)
                        and not mode & (stat.S_ISUID | stat.S_ISGID)
                        and (not mode & 0o022 or (row.st_uid == 0 and bool(mode & stat.S_ISVTX)))
                    )
                directories.append((name, parent, held))
                parent = held.fd
            key_rows = []
            for name in ("own.seed", "own.pub", "peer.pub"):
                held = self._open(
                    name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, parent
                )
                row = os.fstat(held.fd)
                _require(
                    stat.S_ISREG(row.st_mode)
                    and row.st_uid == uid
                    and stat.S_IMODE(row.st_mode) == 0o600
                    and row.st_nlink == 1
                    and row.st_size == 32
                )
                data = os.read(held.fd, 33)
                _require(type(data) is bytes and len(data) == 32 and os.read(held.fd, 1) == b"")
                _require(_identity(os.fstat(held.fd)) == held.identity)
                key_rows.append((name, held))
                values.append(data)
            seed, own_public, peer_public = values
            key = Ed25519PrivateKey.from_private_bytes(seed)
            derived = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            _require(
                derived == own_public == selection.own_public
                and peer_public == selection.peer_public
            )
            # Check path-to-original-descriptor joins after all bounded reads.
            for name, original_parent, held in directories:
                _require(
                    _identity(os.stat(name, dir_fd=original_parent, follow_symlinks=False))
                    == held.identity
                )
            for name, held in key_rows:
                _require(
                    _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == held.identity
                )
            _require(self.close_local() is True and self._process == (os.getpid(), os.geteuid()))
            boot = secrets.token_bytes(32)
            _require(type(boot) is bytes and len(boot) == 32)
            _require(self._refused is False and self._ready is False)
            self._boot = boot.hex()
            self._private_key = key
            self._ready = True
            # No zeroization claim: Python/crypto allocator copies can remain.
        except BaseException:
            self._refused = True
            self._private_key = None
            self.close_local()
            failed = True
        finally:
            # Drop reachable aliases before any outward exception retains this
            # constructor frame. This is not allocator/crypto zeroization.
            values.clear()
            seed = data = key = own_public = peer_public = derived = None
        if failed:
            # Outside the except block: do not chain a key-bearing inner error.
            raise CredentialAcquisitionError(self) from None

    def __repr__(self):
        return "<StartupRoleKeyFiles credentials-redacted>"

    def _open(self, name, flags, parent):
        held = _HeldFile()
        self._records.append(held)  # retain before native allocation
        held.fd = os.open(name, flags, dir_fd=parent)
        _require(type(held.fd) is int and held.fd >= 0 and os.get_inheritable(held.fd) is False)
        held.identity = _identity(os.fstat(held.fd))
        return held

    def close_local(self) -> bool:
        """Only original local descriptor closure; no channel/custody release."""
        if self._process != (os.getpid(), os.geteuid()):
            self._refused = True
            return False
        known = True
        for held in reversed(self._records):
            if held.fd is None or held.closed:
                continue
            if held.close_attempted or held.unknown:
                known = False
                continue
            held.close_attempted = True
            try:
                if held.identity is not None:
                    _require(_identity(os.fstat(held.fd)) == held.identity)
                os.close(held.fd)
                held.closed = True
            except BaseException:
                held.unknown = True
                known = False
        return known

    def retire(self) -> None:
        """Irreversible local retirement; never reloads or repairs this owner."""
        self._refused = True
        self._ready = False
        self._private_key = None
