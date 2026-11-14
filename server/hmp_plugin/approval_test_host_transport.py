"""AT1 private operator transport; deliberately not registered or wired to a gateway.

Kernel peer identity authenticates the local OS user only. The future listener-owned
handler must prove current target-phone/profile/session authority separately. No
phone credential, native waiter, grant, PromptStore or public listener is used here.
"""

from __future__ import annotations

import asyncio
import contextlib
import ctypes
import inspect
import os
import socket
import stat
import struct
import sys
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from types import AsyncGeneratorType
from typing import Protocol

from .approval_test_host_codec import (
    RESPONSE_CAP,
    HostBeginRequest,
    HostCodecError,
    HostGeneration,
    HostOperationRequest,
    HostRequestFrameDecoder,
    HostResponse,
    decode_host_response_frame,
    encode_host_request,
    encode_host_response,
    unavailable_response_frame,
)

FRAME_SECONDS = 2.0
CONNECTION_CAP = 4
_SOCKET_NAME = "approval-test.sock"
_PEER_STRUCT = struct.Struct("iII")
HostRequest = HostBeginRequest | HostOperationRequest


class HostTransportError(ValueError):
    """Fixed local failure; contains no socket path, selectors or underlying cause."""

    def __init__(self) -> None:
        super().__init__("approval test unavailable")


class HostHandler(Protocol):
    """Future reviewed listener port, not authority conferred by this transport.

    responses must be an async generator whose finally joins actual cleanup.
    shutdown must keep
    its dependencies alive until that cleanup finishes. Neither a consumer's EOF
    nor cancellation of a close observer proves producer settlement.
    """

    def responses(self, request: HostRequest) -> AsyncGenerator[HostResponse, None]: ...

    async def write_failed(self, request: HostBeginRequest) -> None: ...

    async def shutdown(self) -> None: ...


def peer_uid(peer: socket.socket) -> int:
    """Kernel UID, never caller data. Unsupported platforms refuse without fallback."""
    uid: int | None = None
    try:
        if peer.family != socket.AF_UNIX or os.getuid() != os.geteuid():
            raise OSError()
        if sys.platform.startswith("linux") and hasattr(socket, "SO_PEERCRED"):
            raw = peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, _PEER_STRUCT.size)
            pid, candidate, _gid = _PEER_STRUCT.unpack(raw)
            if pid > 0:
                uid = candidate
        elif sys.platform == "darwin":
            # Darwin uid_t/gid_t are unsigned32. Resolve only libc's current-process
            # getpeereid symbol; no library path or symbol comes from input.
            native = ctypes.CDLL(None, use_errno=True).getpeereid
            native.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint),
                               ctypes.POINTER(ctypes.c_uint)]
            native.restype = ctypes.c_int
            candidate, gid = ctypes.c_uint(), ctypes.c_uint()
            if native(peer.fileno(), ctypes.byref(candidate), ctypes.byref(gid)) == 0:
                uid = candidate.value
    except (OSError, AttributeError, ValueError, struct.error):
        uid = None
    if uid is None:
        raise HostTransportError()
    return uid


def _authenticate(peer: socket.socket) -> None:
    if peer_uid(peer) != os.getuid():
        raise HostTransportError()


@dataclass(frozen=True, slots=True)
class _Identity:
    device: int
    inode: int
    uid: int
    kind: int


def _identity(value: os.stat_result) -> _Identity:
    return _Identity(value.st_dev, value.st_ino, value.st_uid, stat.S_IFMT(value.st_mode))


def _parent_identity(parent: Path) -> _Identity:
    value: os.stat_result | None = None
    with contextlib.suppress(OSError):
        value = os.lstat(parent)
    if (value is None or not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid()
            or stat.S_IMODE(value.st_mode) & 0o077 or os.getuid() != os.geteuid()):
        raise HostTransportError()
    return _identity(value)


def _socket_path(record: Path) -> tuple[Path, _Identity]:
    # Never resolve a symlink or create/widen the listener's private directory.
    if (not isinstance(record, Path) or not record.is_absolute()
            or record.name != "listener.json" or ".." in record.parts):
        raise HostTransportError()
    path = record.parent / _SOCKET_NAME
    limit = 107 if sys.platform.startswith("linux") else 103 if sys.platform == "darwin" else 0
    if not limit or len(os.fsencode(path)) > limit:
        raise HostTransportError()
    return path, _parent_identity(path.parent)


def _socket_identity(path: Path) -> _Identity:
    value: os.stat_result | None = None
    with contextlib.suppress(OSError):
        value = os.lstat(path)
    if (value is None or not stat.S_ISSOCK(value.st_mode) or value.st_uid != os.getuid()
            or stat.S_IMODE(value.st_mode) != 0o600):
        raise HostTransportError()
    return _identity(value)


def _unlink_owned(path: Path, parent: _Identity, created: _Identity) -> bool:
    """Point-in-time inode fence; same-UID hostile processes are outside this boundary."""
    try:
        if _parent_identity(path.parent) != parent or _identity(os.lstat(path)) != created:
            return False
        os.unlink(path)
    except (OSError, HostTransportError):
        return False
    return True


async def _request(peer: socket.socket, generation: HostGeneration) -> HostRequest:
    decoder = HostRequestFrameDecoder()
    loop = asyncio.get_running_loop()
    # The entire frame AND EOF share one deadline; trickling bytes cannot reset it.
    async with asyncio.timeout(FRAME_SECONDS):
        while True:
            chunk = await loop.sock_recv(peer, 256)
            if not chunk:
                return decoder.finish(eof=True, current=generation)
            decoder.feed(chunk)


async def _write(peer: socket.socket, frame: bytes) -> None:
    async with asyncio.timeout(FRAME_SECONDS):
        await asyncio.get_running_loop().sock_sendall(peer, frame)


def _reply_order(request: HostRequest, replies: list[HostResponse], reply: HostResponse) -> None:
    # Encode validation runs before this state check and before any outgoing byte.
    if not replies and reply.result == "unavailable":
        return
    if type(request) is HostBeginRequest:
        if not replies and reply.result == "accepted" and reply.timeout_ms == request.timeout_ms:
            return
        if (len(replies) == 1 and replies[0].result == "accepted"
                and reply.result == "completed" and reply.operation_id == replies[0].operation_id):
            return
    elif (not replies and reply.operation_id == request.operation_id
          and reply.result == ("status" if request.op == "status" else "cancel_requested")):
        return
    raise HostTransportError()


def _reply_complete(request: HostRequest, replies: list[HostResponse]) -> bool:
    if len(replies) == 1 and replies[0].result == "unavailable":
        return True
    return (len(replies) == 2 and replies[-1].result == "completed"
            if type(request) is HostBeginRequest else len(replies) == 1)


class HostIpcEndpoint:
    """One listener-generation-owned local endpoint; no factory/CLI registration yet."""

    def __init__(self, record: Path, generation: HostGeneration, handler: HostHandler) -> None:
        if type(generation) is not HostGeneration or generation.pid != os.getpid():
            raise HostTransportError()
        self._path, self._parent = _socket_path(record)
        self._generation = generation
        self._handler = handler
        self._socket: socket.socket | None = None
        self._created: _Identity | None = None
        self._accept_task: asyncio.Task[None] | None = None
        self._connections: set[asyncio.Task[None]] = set()
        self._close_task: asyncio.Task[bool] | None = None
        self._closing = False
        self._started = False
        self._begin_active = False
        self._retired = False
        self._cleanup: dict[asyncio.Task[None], asyncio.Task[bool]] = {}

    def start(self) -> None:
        """Explicit activation only. Never called by package import or current adapter."""
        if self._started or self._closing or _parent_identity(self._path.parent) != self._parent:
            raise HostTransportError()
        loop = asyncio.get_running_loop()
        # Verify the platform primitive before exposing even a local listening socket.
        first = second = None
        failed = False
        try:
            first, second = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            _authenticate(first)
        except (OSError, HostTransportError):
            failed = True
        finally:
            if first is not None:
                first.close()
            if second is not None:
                second.close()
        if failed:
            raise HostTransportError()
        peer = None
        failed = False
        try:
            peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # bind refuses every pre-existing sidecar; no unlink/startup recovery.
            peer.bind(os.fspath(self._path))
            value = os.lstat(self._path)
            if not stat.S_ISSOCK(value.st_mode) or value.st_uid != os.getuid():
                raise HostTransportError()
            self._created = _identity(value)
            if _parent_identity(self._path.parent) != self._parent:
                raise HostTransportError()
            os.chmod(self._path, 0o600)
            if _socket_identity(self._path) != self._created:
                raise HostTransportError()
            peer.listen(CONNECTION_CAP)
            peer.setblocking(False)
        except (OSError, ValueError, HostTransportError):
            failed = True
        if failed:
            if peer is not None:
                peer.close()
            if self._created is not None:
                _unlink_owned(self._path, self._parent, self._created)
            raise HostTransportError()
        self._started = True
        self._socket = peer
        self._accept_task = loop.create_task(self._accept())

    async def _accept(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._closing:
            try:
                peer, _address = await loop.sock_accept(self._socket)
            except OSError:
                return
            if self._closing or len(self._connections) >= CONNECTION_CAP:
                peer.close()
                continue
            task = loop.create_task(self._serve(peer))
            self._connections.add(task)
            task.add_done_callback(self._connection_done)

    def _connection_done(self, task: asyncio.Task[None]) -> None:
        if task not in self._cleanup:
            self._connections.discard(task)
        # Retrieve failures without default-loop raw exception/body logging.
        if not task.cancelled():
            task.exception()

    async def _join_lease(self, lease: AsyncGenerator[HostResponse, None]) -> bool:
        try:
            await lease.aclose()
        except (Exception, asyncio.CancelledError):
            return False
        return True

    def _cleanup_done(self, connection: asyncio.Task[None], owns_begin: bool,
                      cleanup: asyncio.Task[bool]) -> None:
        joined = not cleanup.cancelled() and cleanup.exception() is None and cleanup.result()
        if not joined or self._retired:
            # Unknown cleanup retains both connection debt and the begin slot.
            # Retire the whole generation; no later operation can claim recovery.
            self._retired = True
            return
        self._cleanup.pop(connection, None)
        if owns_begin:
            self._begin_active = False
        if connection.done():
            self._connections.discard(connection)

    async def _serve(self, peer: socket.socket) -> None:
        replies: list[HostResponse] = []
        write_lost = False
        owns_begin = False
        lease: AsyncGenerator[HostResponse, None] | None = None
        try:
            _authenticate(peer)  # No request bytes decoded before peer UID succeeds.
            request = await _request(peer, self._generation)
            if self._closing or self._retired:
                raise HostTransportError()
            if type(request) is HostBeginRequest:
                if self._begin_active:
                    raise HostTransportError()
                self._begin_active = True
                owns_begin = True
            # Calling an async-generator function cannot execute its body before
            # we retain the close/join port. Generic iterators have no such lease.
            if not inspect.isasyncgenfunction(self._handler.responses):
                raise HostTransportError()
            lease = self._handler.responses(request)
            if type(lease) is not AsyncGeneratorType:
                raise HostTransportError()
            while True:
                try:
                    reply = await anext(lease)
                except StopAsyncIteration:
                    break
                except (Exception, asyncio.CancelledError):
                    # An iterator failure may itself be a failed finalizer. A
                    # later no-op aclose of an exhausted generator is not proof.
                    self._retired = True
                    raise
                frame = encode_host_response(reply)
                _reply_order(request, replies, reply)
                replies.append(reply)
                if reply.result == "accepted" and not write_lost:
                    try:
                        await _write(peer, frame)
                    except (OSError, TimeoutError):
                        write_lost = True
                        if type(request) is HostBeginRequest:
                            await self._handler.write_failed(request)
                # Continue the handler lease after a real failed write; never infer
                # cleanup or capacity release from the client's disappearance.
            if not _reply_complete(request, replies):
                raise HostTransportError()
            # Only admission can be emitted while the handler is still running.
            # Buffer the final reply until its lease actually returns: a yielded
            # completed value alone cannot prove cleanup has finished.
            if not write_lost:
                try:
                    await _write(peer, encode_host_response(replies[-1]))
                except (OSError, TimeoutError):
                    if type(request) is HostBeginRequest:
                        await self._handler.write_failed(request)
        except Exception:
            if not replies:
                with contextlib.suppress(OSError, TimeoutError):
                    await _write(peer, unavailable_response_frame())
        finally:
            peer.close()
            if lease is not None:
                connection = asyncio.current_task()
                assert connection is not None
                cleanup = asyncio.get_running_loop().create_task(self._join_lease(lease))
                self._cleanup[connection] = cleanup
                cleanup.add_done_callback(
                    lambda done: self._cleanup_done(connection, owns_begin, done)
                )
                # The owned join survives a cancelled connection observer. Its
                # callback releases capacity only after a proven successful join.
                await asyncio.shield(cleanup)
            elif owns_begin:
                self._begin_active = False

    async def close(self) -> bool:
        """Stop accepts, request owner cleanup and JOIN leases before owned unlink.

        A cancelled observer does not cancel the owned teardown or connection tasks.
        Non-returning owner cleanup retains this generation/socket sidecar; no force
        kill or success timeout is provided.
        """
        if self._close_task is None:
            self._closing = True
            self._close_task = asyncio.get_running_loop().create_task(self._close())
        return await asyncio.shield(self._close_task)

    async def _close(self) -> bool:
        if self._socket is not None:
            self._socket.close()
        if self._accept_task is not None:
            self._accept_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._accept_task
        failed = False
        try:
            await self._handler.shutdown()
            # Never cancel admitted cleanup just because shutdown or its observer waits.
            if self._connections:
                results = await asyncio.gather(*tuple(self._connections), return_exceptions=True)
                failed = any(isinstance(result, BaseException) for result in results)
            if self._cleanup:
                results = await asyncio.gather(*tuple(self._cleanup.values()),
                                               return_exceptions=True)
                failed = failed or any(result is not True for result in results)
            if self._retired:
                failed = True
        except (Exception, asyncio.CancelledError):
            failed = True
        if failed:
            # Unknown cleanup leaves the owned sidecar blocking another generation.
            raise HostTransportError()
        if self._created is None:
            return True
        return _unlink_owned(self._path, self._parent, self._created)


async def _response(peer: socket.socket, *, held_completion: bool) -> HostResponse:
    loop = asyncio.get_running_loop()
    # A begin lease can wait indefinitely for actual cleanup. Once the first byte
    # arrives, the rest of that frame has the same fixed two-second budget.
    first = await loop.sock_recv(peer, 1) if held_completion else b""
    async with asyncio.timeout(FRAME_SECONDS):
        header = bytearray(first)
        while len(header) < 4:
            chunk = await loop.sock_recv(peer, 4 - len(header))
            if not chunk:
                raise HostTransportError()
            header.extend(chunk)
        length = int.from_bytes(header, "big")
        if not 1 <= length <= RESPONSE_CAP:
            raise HostTransportError()
        payload = bytearray()
        while len(payload) < length:
            chunk = await loop.sock_recv(peer, length - len(payload))
            if not chunk:
                raise HostTransportError()
            payload.extend(chunk)
        return decode_host_response_frame(bytes(header + payload))


async def host_exchange(record: Path, request: HostRequest) -> AsyncIterator[HostResponse]:
    """One same-UID local lease, no retry, detachment, bearer or producer authority.

    The future CLI must independently validate/reread its private listener record,
    current generation and TTY/session guards. Constructing request DATA does not
    prove that prerequisite. Closing this iterator is NOT host cancellation.
    """
    path, parent = _socket_path(record)
    created = _socket_identity(path)
    frame = encode_host_request(request)
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    peer.setblocking(False)
    loop = asyncio.get_running_loop()
    replies: list[HostResponse] = []
    failed = False
    try:
        async with asyncio.timeout(FRAME_SECONDS):
            await loop.sock_connect(peer, os.fspath(path))
        _authenticate(peer)  # Authenticate the server BEFORE sending selectors.
        if _parent_identity(path.parent) != parent or _socket_identity(path) != created:
            raise HostTransportError()
        await _write(peer, frame)
        peer.shutdown(socket.SHUT_WR)  # Expected framing EOF, not cancellation.
        while True:
            reply = await _response(peer, held_completion=bool(replies))
            _reply_order(request, replies, reply)
            replies.append(reply)
            if _reply_complete(request, replies):
                async with asyncio.timeout(FRAME_SECONDS):
                    if await loop.sock_recv(peer, 1):
                        raise HostTransportError()
                yield reply
                break
            yield reply
    except (OSError, TimeoutError, HostCodecError, HostTransportError):
        failed = True
    finally:
        peer.close()
    if failed:
        raise HostTransportError()
