"""Retained native common-clock observations; never authorization or drain proof.

Trusted installation, exclusive FD ownership, no namespace/provider mutation and
the existing channel/runtime premises remain required. No wire value attests a
clock. Nothing here sends, launches, signals, reaps or selects protocol v2.
"""

from __future__ import annotations

import ctypes
import errno
import os
import re
import select
import socket
import sys
import threading
import time
from dataclasses import dataclass, field

from .presentation_broker_peer import PeerObservation
from .presentation_broker_service import SocketChannel
from .presentation_cancel_budget import MAX_NS
from .presentation_jobs import FrameError

_CLOCK_INFO = time.get_clock_info
_MONOTONIC_NS = time.monotonic_ns
_GETSOCKOPT = socket.socket.getsockopt
_PROCFS = 0x9FA0
_NSFS = 0x6E736673
_PIDFD_FS = frozenset((0x09041934, 0x50494446))  # anon_inodefs, later pidfs
# Linux v6.6 UAPI asm-generic/socket.h. No numeric-PID fallback.
_SO_PEERPIDFD = 77
_UUID = re.compile(rb"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")


def _require(value: bool) -> None:
    if value is not True:
        raise FrameError("BI1_NATIVE_CLOCK_UNAVAILABLE")


def _uuid(value: bytes) -> bytes:
    _require(type(value) is bytes and _UUID.fullmatch(value) is not None)
    return value.lower()


def _darwin_boot() -> bytes:
    api = ctypes.CDLL(None, use_errno=True).sysctlbyname
    api.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                    ctypes.c_void_p, ctypes.c_size_t]
    api.restype = ctypes.c_int
    # Fixed capacity; kernel cannot request an unbounded allocation.
    buffer = ctypes.create_string_buffer(64)
    length = ctypes.c_size_t(len(buffer))
    _require(api(b"kern.bootsessionuuid", buffer, ctypes.byref(length), None, 0) == 0)
    _require(length.value == 37 and buffer.raw[36:37] == b"\0")
    return _uuid(buffer.raw[:36])


def _filesystem(fd: int) -> int:
    # Deliberate 64-bit libc ABI boundary; unsupported ABI refuses, never guesses.
    _require(ctypes.sizeof(ctypes.c_void_p) == 8 and ctypes.sizeof(ctypes.c_long) == 8)
    api = ctypes.CDLL(None, use_errno=True).fstatfs
    api.argtypes = [ctypes.c_int, ctypes.c_void_p]
    api.restype = ctypes.c_int
    buffer = (ctypes.c_long * 32)()
    _require(api(fd, ctypes.byref(buffer)) == 0)
    return buffer[0]


def _identity(fd: int) -> tuple[int, int, int]:
    _require(type(fd) is int and fd >= 0 and os.get_inheritable(fd) is False)
    row = os.fstat(fd)
    return row.st_dev, row.st_ino, row.st_mode


def _ints(value: object, count: int) -> bool:
    return (type(value) is tuple and len(value) == count
            and all(type(v) is int for v in value))


@dataclass(repr=False)
class _Descriptor:
    fd: int | None = None
    original_fd: int | None = None
    identity: tuple[int, int, int] | None = None
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False
    no_fd_known: bool = False


@dataclass(frozen=True, repr=False)
class ClockDomain:
    platform: str
    implementation: str
    boot: bytes = field(repr=False)
    namespace: tuple[int, int] | None = field(repr=False)


class ClockAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_NATIVE_CLOCK_UNKNOWN")
        self.failed_owner = owner


class NativeClockOwner:
    """Synchronous retained observer bound to an existing authenticated channel.

    Constructor failures expose this partial owner. Caller retains it until all
    local descriptor closes are known. That observation releases no channel,
    process, registry credit or native credential.
    """

    def __init__(self, channel: SocketChannel):
        self._channel = self._channel_snapshot = channel
        self._context = self._context_snapshot = (os.getpid(), os.geteuid(), threading.get_ident())
        self._platform = self._platform_snapshot = sys.platform
        self._records: list[_Descriptor] = []
        self._records_snapshot = self._records
        self._record_refs: tuple[_Descriptor, ...] = ()
        self._seals: tuple[tuple[_Descriptor, int, tuple[int, int, int]], ...] = ()
        self._seals_snapshot = self._seals
        self._refused = self._closing = False
        self._closed_known = False
        self._sampling = self._close_running = self._close_reentered = False
        self._domain: ClockDomain | None = None
        self._peer = self._peer_values = self._channel_values = self._channel_identity = None
        self._proc = self._pidfd = self._bootfd = self._ownns = self._peerns = None
        self._last_ns: int | None = None
        try:
            _require(type(channel) is SocketChannel and self._platform in ("darwin", "linux"))
            self._peer = channel._check()
            _require(type(self._peer) is PeerObservation)
            self._peer_values = (self._peer.uid, self._peer.pid)
            self._channel_values = channel._values_snapshot
            self._channel_identity = channel._identity_snapshot
            implementation = self._implementation()
            if self._platform == "darwin":
                domain = ClockDomain(self._platform, implementation, _darwin_boot(), None)
            else:
                self._linux_initialize()
                domain = ClockDomain(self._platform, implementation, self._linux_boot(),
                                     self._ownns.identity[:2])
            self._domain = self._domain_snapshot = domain
            self.sample()
        except BaseException:
            self._refused = True
            raise ClockAcquisitionError(self) from None

    def __repr__(self) -> str:
        return "<NativeClockOwner>"

    def _implementation(self) -> str:
        _require(time.monotonic_ns is _MONOTONIC_NS and time.get_clock_info is _CLOCK_INFO)
        info = _CLOCK_INFO("monotonic")
        expected = ("mach_absolute_time()" if self._platform == "darwin"
                    else "clock_gettime(CLOCK_MONOTONIC)")
        _require(info.monotonic is True and info.adjustable is False
                 and type(info.implementation) is str and info.implementation == expected)
        return expected

    def _slot(self) -> _Descriptor:
        record = _Descriptor()
        self._records.append(record)
        self._record_refs = tuple(self._records)
        return record

    def _seal(self, record: _Descriptor) -> _Descriptor:
        record.original_fd = record.fd
        record.identity = _identity(record.fd)
        self._seals = self._seals_snapshot = (*self._seals, (record, record.fd, record.identity))
        return record

    def _open(self, name: str, flags: int, *, parent: int | None = None) -> _Descriptor:
        record = self._slot()  # retain before native acquisition and fstat
        try:
            record.fd = record.original_fd = os.open(name, flags | os.O_CLOEXEC, dir_fd=parent)
        except OSError:
            record.no_fd_known = True
            raise
        return self._seal(record)

    def _live(self) -> None:
        _require(self._pidfd is not None)
        poll = select.poll()
        poll.register(self._pidfd.fd, select.POLLIN | select.POLLHUP | select.POLLERR)
        _require(poll.poll(0) == [])

    def _linux_initialize(self) -> None:
        _require(os.uname().machine in ("x86_64", "aarch64"))
        self._proc = self._open("/proc", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        _require(_filesystem(self._proc.fd) == _PROCFS)
        # The kernel returns a reference to this socket's original process, not
        # whichever process currently occupies a numeric SO_PEERCRED PID.
        self._pidfd = self._slot()
        try:
            self._pidfd.fd = self._pidfd.original_fd = _GETSOCKOPT(
                self._channel._socket_snapshot, socket.SOL_SOCKET, _SO_PEERPIDFD
            )
        except OSError:
            self._pidfd.no_fd_known = True
            raise
        self._seal(self._pidfd)
        _require(_filesystem(self._pidfd.fd) in _PIDFD_FS)
        self._live()
        self._bootfd = self._open("sys/kernel/random/boot_id", os.O_RDONLY | os.O_NOFOLLOW,
                                  parent=self._proc.fd)
        _require(_filesystem(self._bootfd.fd) == _PROCFS)
        # Deliberate kernel namespace-link following; O_NOFOLLOW would refuse
        # nsfs itself. There are no caller-selected path components.
        self._ownns = self._open("self/ns/time", os.O_RDONLY, parent=self._proc.fd)
        self._peerns = self._open(f"{self._peer.pid}/ns/time", os.O_RDONLY,
                                  parent=self._proc.fd)
        _require(_filesystem(self._ownns.fd) == _NSFS
                 and _filesystem(self._peerns.fd) == _NSFS
                 and self._ownns.identity[:2] == self._peerns.identity[:2])
        self._linux_current()

    def _linux_boot(self) -> bytes:
        os.lseek(self._bootfd.fd, 0, os.SEEK_SET)
        value = os.read(self._bootfd.fd, 38)
        _require(len(value) == 37 and value[-1:] == b"\n")
        return _uuid(value[:-1])

    def _linux_current(self) -> None:
        self._live()
        _require(_filesystem(self._proc.fd) == _PROCFS
                 and _filesystem(self._bootfd.fd) == _PROCFS
                 and _filesystem(self._pidfd.fd) in _PIDFD_FS)
        for path, held in (("self/ns/time", self._ownns),
                           (f"{self._peer.pid}/ns/time", self._peerns)):
            row = os.stat(path, dir_fd=self._proc.fd, follow_symlinks=True)
            _require((row.st_dev, row.st_ino, row.st_mode) == held.identity
                     and _filesystem(held.fd) == _NSFS)
        self._live()

    def _local_ownership(self) -> None:
        _require(all(type(v) is bool for v in (self._refused, self._closing,
                 self._closed_known, self._sampling, self._close_running, self._close_reentered)))
        _require(_ints(self._context_snapshot, 3) and self._context is self._context_snapshot
                 and (os.getpid(), os.geteuid(), threading.get_ident()) == self._context
                 and type(self._platform_snapshot) is str
                 and self._platform is self._platform_snapshot
                 and type(sys.platform) is str and sys.platform == self._platform
                 and type(self._records_snapshot) is list
                 and self._records is self._records_snapshot
                 and type(self._record_refs) is tuple
                 and type(self._seals_snapshot) is tuple
                 and self._seals is self._seals_snapshot
                 and len(self._records) == len(self._record_refs)
                 and all(a is b for a, b in zip(self._records, self._record_refs, strict=True))
                 and len(self._seals) <= len(self._record_refs))
        for record in self._record_refs:
            _require(type(record) is _Descriptor)
            _require(all(type(v) is bool for v in (record.close_attempted, record.closed,
                                                  record.unknown, record.no_fd_known)))
            _require((record.fd is None or (type(record.fd) is int and record.fd >= 0))
                     and (record.original_fd is None or
                          (type(record.original_fd) is int and record.original_fd >= 0))
                     and (record.identity is None or _ints(record.identity, 3)))
        for index, seal in enumerate(self._seals):
            _require(type(seal) is tuple and len(seal) == 3
                     and seal[0] is self._record_refs[index]
                     and type(seal[1]) is int and seal[1] >= 0 and _ints(seal[2], 3))
            record, fd, identity = seal
            _require(record.fd == fd == record.original_fd and record.identity is identity)

    def _bindings(self) -> None:
        self._local_ownership()
        _require(len(self._records) == len(self._seals))
        for record, fd, identity in self._seals:
            _require(record.close_attempted is False and record.unknown is False
                     and record.closed is False)
            observed = _identity(fd)
            _require(_ints(observed, 3) and observed == identity)
        self._local_ownership()
        _require(not self._refused and not self._closing and not self._closed_known
                 and self._channel is self._channel_snapshot
                 and type(self._channel) is SocketChannel
                 and type(self._channel_values) is tuple and len(self._channel_values) == 8
                 and _ints(self._channel_identity, 4)
                 and self._channel._values_snapshot is self._channel_values
                 and self._channel._identity_snapshot is self._channel_identity
                 and _ints(self._peer_values, 2)
                 and type(self._peer) is PeerObservation
                 and type(self._peer.uid) is int and type(self._peer.pid) is int
                 and (self._peer.uid, self._peer.pid) == self._peer_values
                 and self._domain is self._domain_snapshot
                 and type(self._domain) is ClockDomain
                 and (self._last_ns is None or
                      (type(self._last_ns) is int and 0 <= self._last_ns <= MAX_NS)))
        domain = self._domain
        _require(type(domain.platform) is str and type(domain.implementation) is str
                 and type(domain.boot) is bytes
                 and (domain.namespace is None or _ints(domain.namespace, 2)))
        _require(len(self._records) == len(self._seals))
        if self._platform == "linux":
            _require(len(self._record_refs) == 5
                     and self._proc is self._record_refs[0]
                     and self._pidfd is self._record_refs[1]
                     and self._bootfd is self._record_refs[2]
                     and self._ownns is self._record_refs[3]
                     and self._peerns is self._record_refs[4])

    def _peer_matches(self, peer: PeerObservation) -> None:
        _require(type(peer) is PeerObservation and type(peer.uid) is int
                 and type(peer.pid) is int and (peer.uid, peer.pid) == self._peer_values)

    def sample(self) -> int:
        try:
            _require(type(self._sampling) is bool and self._sampling is False)
            self._sampling = True
            self._bindings()
            implementation = self._implementation()
            self._bindings()
            _require(type(implementation) is str and implementation == self._domain.implementation)
            peer = self._channel._check()
            self._bindings()
            self._peer_matches(peer)
            if self._platform == "linux":
                self._linux_current()
                boot = self._linux_boot()
            else:
                boot = _darwin_boot()
            self._bindings()
            _require(type(boot) is bytes and boot == self._domain.boot)
            # Recheck the original channel/context after native boundaries.
            peer = self._channel._check()
            self._bindings()
            self._peer_matches(peer)
            value = _MONOTONIC_NS()
            # Native boundaries can be instrumented and reenter. A swallowed
            # refusal/close cannot be followed by publication of a clock sample.
            self._bindings()
            _require(type(value) is int and 0 <= value <= MAX_NS
                     and (self._last_ns is None or value >= self._last_ns))
            self._last_ns = value
            return value
        except BaseException:
            self._refused = True
            raise FrameError("BI1_NATIVE_CLOCK_UNAVAILABLE") from None
        finally:
            self._sampling = False

    def close_local(self) -> bool:
        """One close intent per owned FD; ambiguity stays retained, never retry."""
        self._local_ownership()
        if self._close_running:
            self._close_reentered = True
            raise FrameError("BI1_NATIVE_CLOCK_UNAVAILABLE")
        self._refused = self._closing = self._close_running = True
        for record in self._record_refs:
            if record.close_attempted or record.closed or record.unknown:
                continue
            if record.fd is None:
                record.closed = record.no_fd_known
                record.unknown = not record.no_fd_known
                continue
            try:
                fd, identity = record.original_fd, record.identity
                _require(type(fd) is int and fd >= 0 and _ints(identity, 3))
                observed = _identity(fd)
                self._local_ownership()
                _require(_ints(observed, 3) and observed == identity
                         and record.fd == fd and record.identity is identity
                         and not self._close_reentered)
                record.close_attempted = True
                os.close(fd)
                try:
                    os.fstat(fd)
                except OSError as error:
                    _require(error.errno == errno.EBADF)
                else:
                    _require(False)
                self._local_ownership()
                _require(not self._close_reentered)
                record.closed = True
            except BaseException:
                record.unknown = True
        self._close_running = False
        self._local_ownership()
        self._closed_known = (not self._close_reentered
                              and all(r.closed and not r.unknown for r in self._record_refs))
        return self._closed_known
