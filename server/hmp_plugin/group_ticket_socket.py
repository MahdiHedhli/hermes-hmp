"""Unactivated one-shot POSIX control exchange; native binding/auth stays external.

Only the future original adapter owner may supply previously verified native
endpoint DATA. Same OS UID and echoed IDs are not original-process or phone
identity. The adapter must retain ONE registry across replacement and shutdown.
No discovery, gateway start, helper thread, child I/O task or retry is performed.
"""

from __future__ import annotations

import asyncio
import ctypes
import math
import os
import socket
import struct
import sys
from contextlib import suppress
from dataclasses import dataclass

from .group_ticket_codec import (
    GroupTicketCodecRefusalError,
    NativeGroupTicketGrant,
    build_group_ticket_request,
    parse_group_ticket_reply,
)

_BODY_LIMIT = 65_536
_REASONS = frozenset(
    {
        "unavailable",
        "wrong_loop",
        "busy",
        "retired",
        "already_attempted",
        "invalid_binding",
        "invalid_deadline",
        "expired",
        "peer_refused",
        "unsupported_peer",
        "transport_failed",
        "invalid_reply",
        "creation_unknown",
        "close_unknown",
        "completion_unknown",
        "self_drain",
    }
)


class GroupTicketSocketError(ValueError):
    """Fixed diagnostic only; mint uncertainty must not become an automatic retry."""

    def __init__(self, reason: str, *, mint_may_have_occurred: bool = False) -> None:
        super().__init__("Native group connection unavailable.")
        self.reason = reason if type(reason) is str and reason in _REASONS else "unavailable"
        self.mint_may_have_occurred = mint_may_have_occurred is True


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise GroupTicketSocketError("invalid_deadline")
    try:
        result = float(value)
    except OverflowError:
        raise GroupTicketSocketError("invalid_deadline") from None
    if not math.isfinite(result) or result < 0 or (type(value) is int and result != value):
        raise GroupTicketSocketError("invalid_deadline")
    return result


def _create_socket() -> socket.socket:
    return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)


def _linux_peer_uid(raw: bytes) -> int:
    """Linux struct ucred fields are __u32 (kernel include/linux/socket.h)."""
    return struct.unpack("3I", raw)[1]


def _peer_identity(peer: socket.socket) -> tuple[int, int] | None:
    """Actual kernel identity; unsupported systems do not fall back to pathname trust."""
    if sys.platform == "linux" and hasattr(socket, "SO_PEERCRED"):
        raw = peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3I"))
        pid, uid, _gid = struct.unpack("3I", raw)
        return uid, pid
    if sys.platform == "darwin":
        library = ctypes.CDLL(None, use_errno=True)
        function = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
            use_errno=True,
        )(("getpeereid", library))
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        if function(peer.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            raise OSError(ctypes.get_errno(), "peer identity unavailable")
        # Pinned XNU bsd/sys/un.h: SOL_LOCAL=0, LOCAL_PEERPID=2.
        # pid_t is a signed 32-bit value; refuse unsupported ABI/unknown peer.
        if struct.calcsize("i") != 4:
            return None
        raw_pid = peer.getsockopt(0, 2, 4)
        pid = struct.unpack("i", raw_pid)[0]
        return uid.value, pid
    return None


@dataclass(frozen=True, slots=True)
class GroupTicketSocketSnapshot:
    attempted: bool
    retired: bool
    phase: str
    exchange_cleanup_finished: bool
    socket_close_known: bool
    same_uid_observed: bool
    expected_pid_observed: bool
    send_may_have_occurred: bool
    registry_slot_retained: bool


@dataclass(frozen=True, slots=True)
class GroupTicketRegistrySnapshot:
    registered: int
    settlement_unknown: bool
    retired: bool


class GroupTicketSocketRegistry:
    """Retained, loop-confined I/O budget; not native/grant/all-reference settlement."""

    def __init__(self, *, capacity: int) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 16:
            raise GroupTicketSocketError("invalid_binding")
        if os.name != "posix" or not hasattr(socket, "AF_UNIX"):
            raise GroupTicketSocketError("unsupported_peer")
        loop = None
        with suppress(RuntimeError):
            loop = asyncio.get_running_loop()
        if loop is None:
            raise GroupTicketSocketError("wrong_loop")
        self._loop = loop
        self._capacity = capacity
        self._owners: dict[object, _TicketSocketExchange] = {}
        self._bindings: dict[tuple[str, str, str], _TicketSocketExchange] = {}
        self._settlement_unknown: _TicketSocketExchange | None = None
        self._retired = False

    def _confined(self) -> None:
        current = None
        with suppress(RuntimeError):
            current = asyncio.get_running_loop()
        if current is not self._loop:
            raise GroupTicketSocketError("wrong_loop")

    def prepare(
        self,
        *,
        socket_path: str,
        expected_peer_pid: int,
        profile_id: str,
        instance_id: str,
        max_seconds: float,
        deadline: float,
    ) -> _TicketSocketExchange:
        """Internal DATA only. Original native path/PID/generation custody is external.

        PID comparison is mandatory but does not defeat PID reuse or prove that
        the caller obtained its expected value from the original native owner.
        """
        self._confined()
        if self._retired:
            raise GroupTicketSocketError("retired")
        if type(expected_peer_pid) is not int or not 1 <= expected_peer_pid <= 2_147_483_647:
            raise GroupTicketSocketError("invalid_binding")
        request = None
        with suppress(GroupTicketCodecRefusalError):
            request = build_group_ticket_request(profile_id=profile_id, instance_id=instance_id)
        if request is None:
            raise GroupTicketSocketError("invalid_binding")
        if (
            type(socket_path) is not str
            or not 1 <= len(socket_path) <= 100
            or not socket_path.startswith("/")
            or "\x00" in socket_path
            or any(part in {".", ".."} for part in socket_path.split("/"))
        ):
            raise GroupTicketSocketError("invalid_binding")
        try:
            path_bytes = socket_path.encode("utf-8")
        except UnicodeError:
            path_bytes = b""
        if not 1 <= len(path_bytes) <= 100:
            raise GroupTicketSocketError("invalid_binding")
        budget = _number(max_seconds)
        if not 0 < budget <= 30:
            raise GroupTicketSocketError("invalid_deadline")
        end = _number(deadline)
        now = self._loop.time()
        if end <= now:
            raise GroupTicketSocketError("expired")
        if end - now > budget:
            raise GroupTicketSocketError("invalid_deadline")
        key = (socket_path, profile_id, instance_id)
        if (
            self._settlement_unknown is not None
            or len(self._owners) >= self._capacity
            or key in self._bindings
        ):
            raise GroupTicketSocketError("busy")
        owner = _TicketSocketExchange(self, key, request, end, expected_peer_pid)
        self._owners[owner._token] = owner
        self._bindings[key] = owner
        return owner

    def _registered(self, owner: _TicketSocketExchange) -> bool:
        return self._owners.get(owner._token) is owner and self._bindings.get(owner._key) is owner

    def _settle(self, owner: _TicketSocketExchange) -> bool:
        if not self._registered(owner) or self._settlement_unknown is not None:
            return False
        # Retain the actual owner even if a prefix of registry removal fails.
        self._settlement_unknown = owner
        del self._owners[owner._token]
        del self._bindings[owner._key]
        self._settlement_unknown = None
        return True

    def _retained(self) -> tuple[_TicketSocketExchange, ...]:
        owners = tuple(self._owners.values())
        debt = self._settlement_unknown
        if debt is not None and not any(owner is debt for owner in owners):
            owners += (debt,)
        return owners

    def retire(self) -> None:
        self._confined()
        self._retired = True
        for owner in self._retained():
            owner.retire()

    async def drain(self) -> bool:
        self.retire()
        owners = self._retained()
        current = asyncio.current_task()
        if any(owner._task is current and not owner._cleanup_finished for owner in owners):
            raise GroupTicketSocketError("self_drain")
        if any(owner._done.cancelled() for owner in owners):
            return False
        if owners:
            outcomes = await asyncio.gather(
                *(asyncio.shield(owner._done) for owner in owners), return_exceptions=True
            )
            if not all(outcome is True for outcome in outcomes):
                return False
        return not self._owners and not self._bindings and self._settlement_unknown is None

    def snapshot(self) -> GroupTicketRegistrySnapshot:
        self._confined()
        return GroupTicketRegistrySnapshot(
            len(self._owners), self._settlement_unknown is not None, self._retired
        )


class _TicketSocketExchange:
    """Registry-issued one-shot child. No public endpoint/credential API is activated."""

    def __init__(
        self,
        registry: GroupTicketSocketRegistry,
        key: tuple[str, str, str],
        request: bytes,
        deadline: float,
        expected_peer_pid: int,
    ) -> None:
        self._registry, self._key, self._request, self._deadline = registry, key, request, deadline
        self._expected_peer_pid = expected_peer_pid
        self._same_pid = False
        self._token = object()
        self._done = registry._loop.create_future()
        self._task: asyncio.Task | None = None
        self._peer: socket.socket | None = None
        self._attempted = self._retired = self._creation_attempted = False
        self._same_uid = self._send_attempted = self._cleanup_finished = self._settled = False
        self._close_known = True  # No socket construction has been attempted yet.
        self._phase = "prepared"

    def _error(self, reason: str) -> GroupTicketSocketError:
        return GroupTicketSocketError(reason, mint_may_have_occurred=self._send_attempted)

    def _current(self, deadline: float) -> None:
        if self._retired or self._registry._retired:
            raise self._error("retired")
        if self._registry._loop.time() >= deadline:
            raise self._error("expired")

    async def _read_line(self, deadline: float) -> bytes:
        data = bytearray()
        try:
            while True:
                self._current(deadline)
                room = _BODY_LIMIT + 1 - len(data)
                if room <= 0:
                    raise self._error("invalid_reply")
                chunk = await self._registry._loop.sock_recv(self._peer, min(4096, room))
                self._current(deadline)
                if not chunk:
                    raise self._error("invalid_reply")
                data.extend(chunk)
                if b"\n" in chunk:
                    return bytes(data)
        finally:
            data.clear()

    def _finish(self) -> None:
        # Default to retained debt BEFORE close; no exception path can imply closure.
        known = not self._creation_attempted
        self._phase = "closing" if self._peer is not None else "creation_unknown"
        try:
            if self._peer is not None:
                try:
                    self._peer.close()
                except Exception:
                    known = False  # Retain original object/debt; never retry close.
                else:
                    known = True
                    self._peer = None
        finally:
            self._close_known = known
            self._cleanup_finished = True
            self._phase = (
                "closed"
                if known
                else ("close_unknown" if self._peer is not None else "creation_unknown")
            )
            try:
                if not self._done.done():
                    self._done.set_result(known)
                completion = known and not self._done.cancelled() and self._done.result() is True
                if completion:
                    self._settled = self._registry._settle(self)
                if known and not self._settled:
                    self._phase = "completion_unknown"
            except Exception:
                self._phase = "completion_unknown"

    async def exchange(self, *, deadline: float | None = None) -> NativeGroupTicketGrant:
        self._registry._confined()
        if self._retired or self._registry._retired:
            raise self._error("retired")
        if self._attempted or not self._registry._registered(self):
            raise self._error("already_attempted")
        self._attempted = True
        self._task = asyncio.current_task()
        reason = None
        grant = None
        raw = b""
        try:
            end = self._deadline
            if deadline is not None and _number(deadline) != end:
                raise self._error("invalid_deadline")
            if self._task is None:
                raise self._error("unavailable")
            self._current(end)
            async with asyncio.timeout_at(end):
                self._current(end)
                self._phase = "constructing"
                self._creation_attempted = True
                self._close_known = False
                self._peer = _create_socket()
                self._peer.setblocking(False)
                self._phase = "connecting"
                self._current(end)
                await self._registry._loop.sock_connect(self._peer, self._key[0])
                self._current(end)
                identity = _peer_identity(self._peer)
                if type(identity) is not tuple or len(identity) != 2:
                    raise self._error("unsupported_peer")
                uid, pid = identity
                if type(uid) is not int or type(pid) is not int or pid <= 0:
                    raise self._error("unsupported_peer")
                if uid != os.getuid():  # windows-footgun: ok — constructor requires POSIX
                    raise self._error("peer_refused")
                self._same_uid = True
                if pid != self._expected_peer_pid:
                    raise self._error("peer_refused")
                self._same_pid = True
                self._current(end)
                self._phase = "sending"
                self._send_attempted = True
                await self._registry._loop.sock_sendall(self._peer, self._request)
                self._phase = "reading"
                raw = await self._read_line(end)
                self._current(end)
                grant = parse_group_ticket_reply(
                    raw, profile_id=self._key[1], instance_id=self._key[2]
                )
                raw = b""
                self._current(end)
        except asyncio.CancelledError:
            self._phase = "cancelled"
            raise
        except TimeoutError:
            reason = "expired"
        except GroupTicketCodecRefusalError:
            reason = "invalid_reply"
        except GroupTicketSocketError as error:
            reason = error.reason
        except Exception:
            reason = "transport_failed"
        finally:
            raw = b""
            self._finish()
        if not self._settled:
            grant = None
            raise self._error(self._phase if self._phase in _REASONS else "close_unknown")
        if reason is not None:
            grant = None
            raise self._error(reason)
        try:
            self._current(end)
        except GroupTicketSocketError:
            grant = None
            raise
        return grant

    def retire(self) -> None:
        self._registry._confined()
        self._retired = True
        if not self._attempted and not self._cleanup_finished:
            self._finish()

    def snapshot(self) -> GroupTicketSocketSnapshot:
        self._registry._confined()
        return GroupTicketSocketSnapshot(
            self._attempted,
            self._retired,
            self._phase,
            self._cleanup_finished,
            self._close_known,
            self._same_uid,
            self._same_pid,
            self._send_attempted,
            self._registry._registered(self) or self._registry._settlement_unknown is self,
        )
