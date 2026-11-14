"""Narrow kernel connection-credential observations, not code or custody proof.

Caller must exclusively own the connected socket throughout this synchronous
observation. Peer IDs are connection snapshots, never authority to signal a PID.
No broker service, endpoint qualification or native authorization is supplied.
"""

from __future__ import annotations

import os
import socket
import stat
import struct
import sys
from dataclasses import dataclass

from .presentation_jobs import FrameError

# Current Darwin SDK sys/un.h / sys/ucred.h ABI; unknown options/version refuse.
_DARWIN_LEVEL = 0
_DARWIN_CREDENTIALS = 1
_DARWIN_PID = 2
_XUCRED = struct.Struct("=IIh2x16I")
_PID = struct.Struct("=i")
_UCRED = struct.Struct("=iII")
_MAX_UID = (1 << 32) - 2
_MAX_PID = (1 << 31) - 1


def _fail() -> None:
    raise FrameError("BI1_BROKER_PEER_UNAVAILABLE")


@dataclass(frozen=True)
class PeerObservation:
    uid: int
    pid: int


def _ids(uid: int, pid: int) -> PeerObservation:
    if type(uid) is not int or not 0 <= uid <= _MAX_UID:
        _fail()
    if type(pid) is not int or not 1 <= pid <= _MAX_PID:
        _fail()
    return PeerObservation(uid, pid)


def _linux(data: bytes) -> PeerObservation:
    if type(data) is not bytes or len(data) != _UCRED.size:
        _fail()
    pid, uid, gid = _UCRED.unpack(data)
    if gid > _MAX_UID:
        _fail()
    return _ids(uid, pid)


def _darwin(credentials: bytes, process: bytes) -> PeerObservation:
    if (
        type(credentials) is not bytes
        or len(credentials) != _XUCRED.size
        or type(process) is not bytes
        or len(process) != _PID.size
    ):
        _fail()
    version, uid, groups, *_ = _XUCRED.unpack(credentials)
    if version != 0 or not 1 <= groups <= 16:
        _fail()
    return _ids(uid, _PID.unpack(process)[0])


def _descriptor(sock: socket.socket) -> tuple[int, int, int, int]:
    descriptor = sock.fileno()
    if type(descriptor) is not int or descriptor < 0:
        _fail()
    info = os.fstat(descriptor)
    if not stat.S_ISSOCK(info.st_mode):
        _fail()
    return descriptor, info.st_dev, info.st_ino, info.st_mode


def _api(name: str) -> int:
    value = getattr(socket, name, None)
    if type(value) is not int:
        _fail()
    return value


def observe_peer(
    sock: socket.socket,
    *,
    expected_uid: int,
    expected_pid: int | None = None,
) -> PeerObservation:
    """Match trusted startup expectations; no request-selected UID/PID or fallback.

    Descriptor checks detect observed replacement, not arbitrary same-UID fd
    tampering or current process liveness. Endpoint/code identity is a later gate.
    """
    if (
        type(sock) is not socket.socket
        or type(expected_uid) is not int
        or not 1 <= expected_uid <= _MAX_UID
        or (
            expected_pid is not None
            and (type(expected_pid) is not int or not 1 <= expected_pid <= _MAX_PID)
        )
    ):
        _fail()
    platform = sys.platform
    if platform not in ("darwin", "linux"):
        _fail()
    try:
        before = _descriptor(sock)
        if (
            sock.family != socket.AF_UNIX
            or sock.getsockopt(_api("SOL_SOCKET"), _api("SO_TYPE")) != socket.SOCK_STREAM
        ):
            _fail()
        # Darwin Unix sockets reject SO_ACCEPTCONN (ENOPROTOOPT). Select the
        # known platform API, never retry/fall back after an observation failure.
        if platform == "linux" and sock.getsockopt(_api("SOL_SOCKET"), _api("SO_ACCEPTCONN")) != 0:
            _fail()
        # Must be connected, not merely a local listening/bound descriptor.
        if type(sock.getpeername()) not in (str, bytes) or type(sock.getsockname()) not in (
            str,
            bytes,
        ):
            _fail()
        if platform == "darwin":
            result = _darwin(
                sock.getsockopt(_DARWIN_LEVEL, _DARWIN_CREDENTIALS, _XUCRED.size),
                sock.getsockopt(_DARWIN_LEVEL, _DARWIN_PID, _PID.size),
            )
        elif platform == "linux":
            result = _linux(sock.getsockopt(_api("SOL_SOCKET"), _api("SO_PEERCRED"), _UCRED.size))
        else:
            _fail()
        if before != _descriptor(sock):
            _fail()
        if result.uid != expected_uid or (expected_pid is not None and result.pid != expected_pid):
            _fail()
        return result
    except (OSError, ValueError, OverflowError, AttributeError, struct.error):
        raise FrameError("BI1_BROKER_PEER_UNAVAILABLE") from None
