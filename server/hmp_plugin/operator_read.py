"""Bounded, read-only host Controls decision context over a local Unix socket.

This endpoint never grants Controls. A TTY caller must independently verify its
listener, repeat the read after confirmation, and use Store's final origin/CAS gate.
"""
from __future__ import annotations

import asyncio
import contextlib
import ctypes
import json
import os
import re
import socket
import stat
import struct
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contract import AuthzState
from .controls_requests import ControlsRequestStore

SOCKET_NAME = "controls-operator.sock"
MAX_REQUEST = 512
MAX_RESPONSE = 16_384
MAX_PROFILES = 20
MAX_SAFE_INTEGER = 9_007_199_254_740_991
DEADLINE_S = 2.0
_REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_IID = re.compile(r"[a-z2-7]{52}\Z", re.ASCII)
_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
_NONCE = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)


def _safe_ijson(value: object) -> bool:
    if value is None or type(value) in (str, bool):
        return True
    if type(value) is int:
        return -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER
    if isinstance(value, list):
        return len(value) <= 64 and all(_safe_ijson(item) for item in value)
    if isinstance(value, dict):
        return len(value) <= 64 and all(
            isinstance(key, str) and _safe_ijson(child) for key, child in value.items()
        )
    return False


class OperatorUnavailableError(RuntimeError):
    """Closed refusal, with no source exception or private path in its message."""


def _closed_json(raw: bytes, keys: frozenset[str]) -> dict[str, Any]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeError, ValueError) as exc:
        raise OperatorUnavailableError("operator context unavailable") from exc
    if not isinstance(value, dict) or frozenset(value) != keys:
        raise OperatorUnavailableError("operator context unavailable")
    return value


def _parent_fd(path: Path) -> tuple[int, os.stat_result]:
    """Walk trusted ancestors without symlinks, then hold the exact private parent.

    Root-owned non-writable ancestors are allowed; a root-owned sticky temporary
    directory must lead directly into a current-user 0700 suffix. User-owned
    ancestors may be readable but cannot be writable by another account. The
    final directory must be 0700, and its named identity is rechecked at use.
    """
    parent = path.parent
    if not parent.is_absolute():
        raise OperatorUnavailableError("operator directory unavailable")
    # Both flags are required for the supported Darwin/Linux host contract.
    # An unsupported platform must refuse rather than follow a substituted path.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    must_private_next = False
    try:
        for part in parent.parts[1:]:
            if part in ("", ".", ".."):
                raise OperatorUnavailableError("operator directory unavailable")
            named = os.stat(part, dir_fd=fd, follow_symlinks=False)
            child = os.open(part, flags, dir_fd=fd)
            try:
                held = os.fstat(child)
                if ((named.st_dev, named.st_ino) != (held.st_dev, held.st_ino)
                        or not stat.S_ISDIR(held.st_mode)):
                    raise OperatorUnavailableError("operator directory unavailable")
                mode = stat.S_IMODE(held.st_mode)
                sticky_root_tmp = held.st_uid == 0 and bool(mode & stat.S_ISVTX)
                if must_private_next:
                    if held.st_uid != os.getuid() or mode != 0o700:
                        raise OperatorUnavailableError("operator directory unavailable")
                    must_private_next = False
                elif sticky_root_tmp:
                    if not mode & stat.S_IWOTH:
                        raise OperatorUnavailableError("operator directory unavailable")
                    must_private_next = True
                elif (held.st_uid not in {0, os.getuid()}
                      or mode & (stat.S_IWGRP | stat.S_IWOTH)):
                    raise OperatorUnavailableError("operator directory unavailable")
            except BaseException:
                os.close(child)
                raise
            # Transfer the validated child before closing the previous parent.
            # The outer handler now owns exactly fd if that close raises.
            previous_parent = fd
            fd = child
            os.close(previous_parent)
        held, named = os.fstat(fd), os.lstat(parent)
        if (must_private_next or (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino)
                or not stat.S_ISDIR(held.st_mode) or held.st_uid != os.getuid()
                or stat.S_IMODE(held.st_mode) != 0o700):
            raise OperatorUnavailableError("operator directory unavailable")
        return fd, held
    except BaseException:
        os.close(fd)
        raise


def _entry(fd: int) -> os.stat_result:
    return os.stat(SOCKET_NAME, dir_fd=fd, follow_symlinks=False)


def _peer_uid(sock: socket.socket) -> int:
    if sys.platform == "darwin":
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        libc = ctypes.CDLL(None, use_errno=True)
        func = libc.getpeereid
        func.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint))
        func.restype = ctypes.c_int
        if func(sock.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            raise OperatorUnavailableError("operator peer unavailable")
        return int(uid.value)
    if sys.platform.startswith("linux"):
        layout = struct.Struct("=iII")  # native-endian 32-bit pid_t, uid_t, gid_t
        if layout.size != 12 or not hasattr(socket, "SO_PEERCRED"):
            raise OperatorUnavailableError("operator peer unavailable")
        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, layout.size)
        if len(raw) != layout.size:
            raise OperatorUnavailableError("operator peer unavailable")
        _pid, uid, _gid = layout.unpack(raw)
        if uid > 0xFFFFFFFF:
            raise OperatorUnavailableError("operator peer unavailable")
        return uid
    raise OperatorUnavailableError("operator platform unsupported")


def _request(raw: bytes, *, iid: str, nonce: str) -> tuple[str, str]:
    obj = _closed_json(
        raw, frozenset({"protocol", "operation", "request_id", "iid", "nonce", "challenge"}),
    )
    if (type(obj["protocol"]) is not int or obj["protocol"] != 1
            or obj["operation"] != "host_controls_decision_context"
            or not isinstance(obj["request_id"], str)
            or _REQUEST_ID.fullmatch(obj["request_id"]) is None
            or obj["iid"] != iid or obj["nonce"] != nonce
            or not isinstance(obj["challenge"], str)
            or _NONCE.fullmatch(obj["challenge"]) is None):
        raise OperatorUnavailableError("operator context unavailable")
    return obj["request_id"], obj["challenge"]


def _source_snapshot(
    ctx: Any, record: Any, deadline: float, generation: str,
) -> tuple[dict[str, object], frozenset[str]]:
    from . import server

    def checkpoint() -> None:
        if (time.monotonic() >= deadline or ctx.readiness_generation != generation
                or ctx.identity.still_current() is not True):
            raise OperatorUnavailableError("operator context unavailable")

    checkpoint()
    bridge = ctx.bridge
    if bridge is None:
        raise OperatorUnavailableError("operator context unavailable")
    served = bridge.served_profiles()
    if (not isinstance(served, (tuple, list)) or not 1 <= len(served) <= MAX_PROFILES
            or any(not isinstance(p, str) or _PROFILE.fullmatch(p) is None for p in served)
            or len(set(served)) != len(served)):
        raise OperatorUnavailableError("operator profile set unavailable")
    authorized: list[str] = []
    for profile in sorted(served):
        checkpoint()
        state = bridge.authz_state(record.origin.user_id, profile)
        if (not isinstance(state, AuthzState)
                or state in {AuthzState.UNVERIFIABLE, AuthzState.REFUSED_ALLOW_ALL,
                             AuthzState.NOT_ROUTED, AuthzState.NOT_SERVED}):
            raise OperatorUnavailableError("operator authorization unavailable")
        if state is AuthzState.AUTHORIZED:
            authorized.append(profile)
    if record.bot_profile not in authorized:
        raise OperatorUnavailableError("operator initiating profile unavailable")
    statuses = server._readiness_feature_statuses(ctx)
    settings = server._readiness_host_settings(ctx)
    owner_reader = ctx.readiness_owner_device_ids
    if owner_reader is None:
        raise OperatorUnavailableError("operator owner policy unavailable")
    owners = owner_reader()
    if not isinstance(owners, frozenset) or any(not isinstance(x, str) for x in owners):
        raise OperatorUnavailableError("operator owner policy unavailable")
    api: dict[str, str] = {}
    for profile in authorized:
        checkpoint()
        state = bridge.readiness_profile_api_state(profile, checkpoint=checkpoint)
        if state not in {"configured", "missing"}:
            raise OperatorUnavailableError("operator profile API unavailable")
        api[profile] = state
    checkpoint()
    public = {
        "served_profiles": sorted(served),
        "authorized_profiles": authorized,
        "profile_api": api,
        "host_settings": settings,
        "eligibility": {name: [*statuses[name]] for name in ("jobs", "model")},
        "approval_owner_allowlisted": record.origin.device_id in owners,
    }
    return public, owners


def _collect(ctx: Any, request_id: str, challenge: str, nonce: str,
             generation: str, deadline: float) -> dict[str, object]:
    if ctx.identity.still_current() is not True or ctx.readiness_generation != generation:
        raise OperatorUnavailableError("operator context unavailable")
    requests = ControlsRequestStore(ctx.store)
    first = requests.host_record(request_id, now=ctx.now(), current_iid=ctx.iid)
    if first.code != "ok" or first.record is None:
        raise OperatorUnavailableError("operator request unavailable")
    start, owner_before = _source_snapshot(ctx, first.record, deadline, generation)
    second = requests.host_record(request_id, now=ctx.now(), current_iid=ctx.iid)
    if second.code != "ok" or second.record != first.record:
        raise OperatorUnavailableError("operator request changed")
    end, owner_after = _source_snapshot(ctx, second.record, deadline, generation)
    if start != end or owner_before != owner_after:
        raise OperatorUnavailableError("operator context changed")
    sampled = int(time.monotonic() * 1_000)
    if sampled >= int(deadline * 1_000):
        raise OperatorUnavailableError("operator context expired")
    return {
        "protocol": 1, "operation": "host_controls_decision_context",
        "request_id": request_id, "challenge": challenge, "iid": ctx.iid,
        "nonce": nonce, "generation": generation,
        "record": asdict(second.record), "sources": end,
        "sample_ms": sampled, "expires_ms": int(deadline * 1_000),
    }


class OperatorReadService:
    def __init__(self, ctx: Any, anchor_dir: Path, nonce: str) -> None:
        self.ctx = ctx
        self.path = Path(anchor_dir).parent / SOCKET_NAME
        self.nonce = nonce
        self._fd: int | None = None
        self._inode: tuple[int, int] | None = None
        self._server: asyncio.AbstractServer | None = None
        self._clients: set[asyncio.Task[Any]] = set()
        self._stopping = False
        self._active = 0
        self._drained = asyncio.Event()
        self._outstanding = 0

    async def start(self) -> None:
        if _NONCE.fullmatch(self.nonce) is None or len(os.fsencode(self.path)) >= 104:
            raise OperatorUnavailableError("operator socket path unavailable")
        fd, parent = _parent_fd(self.path)
        created: tuple[int, int] | None = None
        try:
            try:
                _entry(fd)
            except FileNotFoundError:
                pass
            else:
                raise OperatorUnavailableError("operator socket already exists")
            def bound_identity() -> tuple[int, int] | None:
                named_parent = os.lstat(self.path.parent)
                held_parent = os.fstat(fd)
                named = os.lstat(self.path)
                held_entry = _entry(fd)
                if ((parent.st_dev, parent.st_ino)
                    != (held_parent.st_dev, held_parent.st_ino)
                    or (parent.st_dev, parent.st_ino)
                    != (named_parent.st_dev, named_parent.st_ino)
                    or (named.st_dev, named.st_ino) != created
                    or (held_entry.st_dev, held_entry.st_ino) != created
                    or not stat.S_ISSOCK(named.st_mode) or named.st_uid != os.getuid()
                    or stat.S_IMODE(named.st_mode) & 0o077):
                    return None
                return named.st_dev, named.st_ino

            raw = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                previous = os.umask(0o077)
                try:
                    raw.bind(str(self.path))
                    bound = _entry(fd)
                    created = (bound.st_dev, bound.st_ino)
                finally:
                    os.umask(previous)
                if bound_identity() is None:
                    raise OperatorUnavailableError("operator socket unsafe")
                raw.listen(2)
                raw.setblocking(False)
                listener = await asyncio.start_unix_server(
                    self._handle, sock=raw, limit=MAX_REQUEST,
                )
            except BaseException:
                raw.close()
                raise
            verified = bound_identity()
            if verified is None:
                listener.close()
                await listener.wait_closed()
                raise OperatorUnavailableError("operator socket unsafe")
            self._fd, self._server = fd, listener
            self._inode = verified
        except BaseException:
            if created is not None:
                with contextlib.suppress(OSError):
                    current = _entry(fd)
                    if (current.st_dev, current.st_ino) == created:
                        os.unlink(SOCKET_NAME, dir_fd=fd)
            os.close(fd)
            raise

    async def stop(self) -> int:
        self._stopping = True
        listener, self._server = self._server, None
        if listener is not None:
            listener.close()
            await listener.wait_closed()
        if self._clients:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    asyncio.gather(*tuple(self._clients), return_exceptions=True), 2.0,
                )
        fd, self._fd = self._fd, None
        if fd is not None:
            try:
                if self._inode == (_entry(fd).st_dev, _entry(fd).st_ino):
                    os.unlink(SOCKET_NAME, dir_fd=fd)
            except FileNotFoundError:
                pass
            finally:
                os.close(fd)
        debt = self._outstanding
        if debt == 0:
            self._drained.set()
        return debt

    async def wait_drained(self) -> None:
        """A timed-out synchronous callback retains its Store until it actually returns."""
        await self._drained.wait()

    async def _context(self, request_id: str, challenge: str) -> dict[str, object]:
        ctx = self.ctx
        if self._stopping or not ctx.read_worker_budget.reserve(operator=True):
            raise OperatorUnavailableError("operator capacity unavailable")
        self._outstanding += 1
        generation = ctx.readiness_generation
        deadline = time.monotonic() + DEADLINE_S
        try:
            work = asyncio.create_task(asyncio.to_thread(
                _collect, ctx, request_id, challenge, self.nonce, generation, deadline,
            ))
        except BaseException:
            ctx.read_worker_budget.release(operator=True)
            self._outstanding -= 1
            raise
        def release(done: asyncio.Task[Any]) -> None:
            with contextlib.suppress(BaseException):
                done.exception()
            ctx.read_worker_budget.release(operator=True)
            self._outstanding -= 1
            if self._stopping and self._outstanding == 0:
                self._drained.set()
        work.add_done_callback(release)
        try:
            return await asyncio.wait_for(asyncio.shield(work), DEADLINE_S)
        except (TimeoutError, asyncio.CancelledError):
            raise OperatorUnavailableError("operator context unavailable") from None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        self._clients.add(task)
        self._active += 1
        try:
            if self._stopping or self._active > 2:
                return
            sock = writer.get_extra_info("socket")
            if sock is None or _peer_uid(sock) != os.getuid():
                return
            raw = await asyncio.wait_for(reader.readline(), DEADLINE_S)
            if not raw.endswith(b"\n") or len(raw) > MAX_REQUEST:
                return
            request_id, challenge = _request(raw[:-1], iid=self.ctx.iid, nonce=self.nonce)
            payload = await self._context(request_id, challenge)
            if not _safe_ijson(payload):
                return
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                              allow_nan=False).encode("ascii") + b"\n"
            if len(body) > MAX_RESPONSE or self._stopping:
                return
            writer.write(body)
            await asyncio.wait_for(writer.drain(), DEADLINE_S)
        except (Exception, asyncio.CancelledError):
            # Deliberate empty-response refusal; no private exception text is exposed.
            # The existing finally block still closes the writer and releases client state.
            return
        finally:
            self._active -= 1
            self._clients.discard(task)
            writer.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(writer.wait_closed(), DEADLINE_S)


def read_context(path: Path, *, iid: str, nonce: str, request_id: str) -> dict[str, Any]:
    """CLI-side fresh read. Caller checks TTY, listener and TLS identity first."""
    if (_IID.fullmatch(iid) is None or _NONCE.fullmatch(nonce) is None
            or _REQUEST_ID.fullmatch(request_id) is None):
        raise OperatorUnavailableError("operator context unavailable")
    fd, parent = _parent_fd(path)
    try:
        before = _entry(fd)
        if (not stat.S_ISSOCK(before.st_mode) or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) & 0o077):
            raise OperatorUnavailableError("operator socket unsafe")
        challenge = os.urandom(16).hex()
        request = json.dumps({
            "protocol": 1, "operation": "host_controls_decision_context", "request_id": request_id,
            "iid": iid, "nonce": nonce, "challenge": challenge,
        }, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(DEADLINE_S)
            client.connect(str(path))
            if _peer_uid(client) != os.getuid():
                raise OperatorUnavailableError("operator peer unavailable")
            after = _entry(fd)
            named_parent, named_entry = os.lstat(path.parent), os.lstat(path)
            if ((after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
                    or (named_entry.st_dev, named_entry.st_ino)
                    != (before.st_dev, before.st_ino)
                    or (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
                    != (parent.st_dev, parent.st_ino)
                    or (named_parent.st_dev, named_parent.st_ino)
                    != (parent.st_dev, parent.st_ino)):
                raise OperatorUnavailableError("operator socket changed")
            client.sendall(request)
            chunks = bytearray()
            while len(chunks) <= MAX_RESPONSE:
                block = client.recv(min(4096, MAX_RESPONSE + 1 - len(chunks)))
                if not block:
                    break
                chunks.extend(block)
                if b"\n" in block:
                    break
        if len(chunks) > MAX_RESPONSE or chunks.count(b"\n") != 1 or not chunks.endswith(b"\n"):
            raise OperatorUnavailableError("operator response unavailable")
        result = _closed_json(bytes(chunks[:-1]), frozenset({
            "protocol", "operation", "request_id", "challenge", "iid", "nonce", "generation",
            "record", "sources", "sample_ms", "expires_ms",
        }))
        generation = result["generation"]
        if (type(result["protocol"]) is not int or result["protocol"] != 1
                or result["operation"] != "host_controls_decision_context"
                or result["request_id"] != request_id or result["challenge"] != challenge
                or result["iid"] != iid or result["nonce"] != nonce
                or not isinstance(generation, str) or _NONCE.fullmatch(generation) is None
                or type(result["sample_ms"]) is not int
                or type(result["expires_ms"]) is not int
                or not 0 <= result["sample_ms"] < result["expires_ms"]
                or result["expires_ms"] - result["sample_ms"] > 2_000
                or not isinstance(result["record"], dict)
                or not isinstance(result["sources"], dict)):
            raise OperatorUnavailableError("operator response unavailable")
        source = result["sources"]
        if frozenset(source) != frozenset({
            "served_profiles", "authorized_profiles", "profile_api", "host_settings",
            "eligibility", "approval_owner_allowlisted",
        }):
            raise OperatorUnavailableError("operator response unavailable")
        served, authorized = source["served_profiles"], source["authorized_profiles"]
        if (not isinstance(served, list) or not isinstance(authorized, list)
                or not 1 <= len(served) <= MAX_PROFILES or served != sorted(set(served))
                or any(not isinstance(x, str) or _PROFILE.fullmatch(x) is None for x in served)
                or authorized != sorted(set(authorized)) or not set(authorized) <= set(served)
                or type(source["approval_owner_allowlisted"]) is not bool):
            raise OperatorUnavailableError("operator response unavailable")
        api, settings, eligibility = (
            source["profile_api"], source["host_settings"], source["eligibility"]
        )
        if (not isinstance(api, dict) or set(api) != set(authorized)
                or any(value not in {"configured", "missing"} for value in api.values())
                or not isinstance(settings, dict) or set(settings) != {"jobs", "model"}
                or any(value not in {"enabled", "disabled"} for value in settings.values())
                or not isinstance(eligibility, dict) or set(eligibility) != {"jobs", "model"}
                or any(not isinstance(value, list) or len(value) != 2
                       or not isinstance(value[0], str)
                       or (value[1] is not None and not isinstance(value[1], str))
                       for value in eligibility.values())
                or not result["sample_ms"] <= int(time.monotonic() * 1_000)
                < result["expires_ms"]
                or not _safe_ijson(result)):
            raise OperatorUnavailableError("operator response unavailable")
        return result
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise OperatorUnavailableError("operator context unavailable") from exc
    finally:
        os.close(fd)
