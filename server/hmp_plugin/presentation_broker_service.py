"""Enrolled private control/result spine; no production admission or started release.

Trusted startup supplies both kernel identities and one immutable instance /
listener / broker-boot scope. It separately qualifies installation and manager
policy. A value object cannot attest that qualification. No self-enrollment,
restart/reset, socket creation/unlink, phone rights or remote closure claim.
"""
from __future__ import annotations

import asyncio
import contextlib
import errno
import os
import socket
import stat
import threading
import time
from dataclasses import dataclass
from typing import NamedTuple

from .presentation_broker_codec import (
    BrokerBinding,
    BrokerFrame,
    BrokerHeader,
    _binding,
    _row,
    decode_header,
    decode_scope_header,
    encode_frame,
    header_size,
)
from .presentation_broker_endpoint import BrokerEndpointOwner, EndpointObservation
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_peer import PeerObservation, observe_peer
from .presentation_broker_registry import BrokerRegistry, RegistryStatus
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import INPUT_LIMIT, MAX_PROCESSES, MAX_WAITING, FrameError
from .presentation_readiness import ReadinessWakeError, SelectorReadiness

_MAX_CONNECTIONS = MAX_PROCESSES + MAX_WAITING
_MAX_WIRE = 8 + 1024 + INPUT_LIMIT + 4
_SOCKET_CLOSE = socket.socket.close
_SOCKET_FILENO = socket.socket.fileno
_SOCKET_ACCEPT = socket.socket.accept
_SOCKET_SHUTDOWN = socket.socket.shutdown
_SOCKET_RECV = socket.socket.recv
_SOCKET_TIMEOUT = socket.socket.gettimeout


def _require(value: bool) -> None:
    if value is not True:
        raise FrameError("BI1_BROKER_SERVICE_REFUSED")


def _task_allows_work() -> None:
    # Python 3.11 wait_for may return a just-completed Future while the outer
    # task still carries cancellation. Readiness/progress never revives work.
    task = asyncio.current_task()
    _require(task is not None)
    pending = task.cancelling()
    _require(type(pending) is int and pending >= 0)
    if pending:
        raise asyncio.CancelledError


def _context_shape(value: object) -> bool:
    return (type(value) is tuple and len(value) == 2
            and all(type(v) is int for v in value))


def _values_shape(value: object) -> bool:
    return (type(value) is tuple and len(value) == 9
            and all(type(value[i]) is str for i in (0, 1, 2, 7))
            and all(type(value[i]) is int for i in (3, 4, 5, 6, 8))
            and value[8] in (1, 2))


def _identity_shape(value: object) -> bool:
    return (type(value) is tuple and len(value) == 4
            and all(type(v) is int for v in value))


@dataclass(frozen=True)
class StartupEnrollment:
    scope: BrokerBinding
    gateway_uid: int
    gateway_pid: int
    service_uid: int
    service_pid: int
    installation_generation: str
    protocol_version: int = 1

    def validate(self) -> None:
        _require(type(self.scope) is BrokerBinding)
        _binding(self.scope)
        for value in (self.gateway_uid, self.service_uid):
            _require(type(value) is int and 1 <= value < (1 << 31))
        for value in (self.gateway_pid, self.service_pid):
            _require(type(value) is int and 1 < value < (1 << 31))
        _require(self.gateway_pid != self.service_pid)
        _require(type(self.protocol_version) is int and self.protocol_version in (1, 2))
        value = self.installation_generation
        _require(type(value) is str and len(value) == 64
                 and all(c in "0123456789abcdef" for c in value))

    def values(self) -> tuple:
        self.validate()
        b = self.scope
        return (b.iid, b.listener, b.broker, self.gateway_uid, self.gateway_pid,
                self.service_uid, self.service_pid, self.installation_generation,
                self.protocol_version)


class ChannelAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_BROKER_CHANNEL_UNKNOWN")
        self.failed_owner = owner


_BEGIN_WRITE_MINT = object()


class _BeginWriteIntent(NamedTuple):
    remote: object
    channel: object
    socket: object
    values: tuple
    identity: tuple
    binding: BrokerBinding
    packet: bytes
    end_ns: int
    version: int
    token: object

    def __repr__(self):
        return "<BeginWriteIntent redacted>"


class _BeginWriteFact(NamedTuple):
    mint: object
    intent: _BeginWriteIntent

    def __repr__(self):
        return "<BeginWriteFact redacted>"


_GO_WRITE_MINT = object()


class _GoWriteIntent(NamedTuple):
    begin: _BeginWriteFact
    work: object
    admission: object
    wire: bytes
    token: object

    def __repr__(self):
        return "<GoWriteIntent redacted>"


class _GoWriteFact(NamedTuple):
    mint: object
    intent: _GoWriteIntent

    def __repr__(self):
        return "<GoWriteFact redacted>"



class _PreResultScope(NamedTuple):
    channel: object
    sock: object
    buffer: bytearray
    expected: object
    end: int
    owner: object
    task: object
    loop: object
    context: tuple

    def __repr__(self):
        return "<PreResultScope redacted>"


class _PreResultCursor:
    """One original-task selected-v2 BEGIN/READY frame, never cleanup permission."""

    def __init__(self, channel, end, expected, owner):
        self._initialized = self._io_unknown = self._intent = self._done = False
        self._cleanup_switched = False
        self._scope = self._scope_snapshot = self._scope_origin = None
        self._buffer = self._buffer_origin = bytearray()
        self._pending = self._waiter = None
        self._received = self._target = 0
        self._header = self._header_snapshot = None
        self._scope = self._scope_snapshot = self._scope_origin = _PreResultScope(
            channel, channel._socket_snapshot, self._buffer_origin, expected, end, owner,
            asyncio.current_task(), asyncio.get_running_loop(),
            (os.getpid(), threading.get_ident()))
        self._initialized = True
        _PreResultCursor._current(self)

    def __repr__(self):
        return "<PreResultCursor payload-redacted>"

    def _guard(self):
        s = self._scope
        _require(type(self) is _PreResultCursor and type(s) is _PreResultScope
                 and s is self._scope_snapshot and s is self._scope_origin
                 and type(s.channel) is SocketChannel
                 and s.channel._pre_result_cursor is self
                 and s.channel._pre_result_cursor_snapshot is self
                 and s.channel._pre_result_cursor_origin is self
                 and type(s.sock) is socket.socket and s.sock is s.channel._socket_snapshot
                 and type(s.end) is int and 0 < s.end < 1 << 63
                 and type(s.task) is asyncio.Task and asyncio.current_task() is s.task
                 and type(s.loop) is asyncio.SelectorEventLoop
                 and asyncio.get_running_loop() is s.loop
                 and asyncio.BaseEventLoop.get_task_factory(s.loop) is None
                 and type(s.context) is tuple and len(s.context) == 2
                 and all(type(v) is int for v in s.context)
                 and s.context == (os.getpid(), threading.get_ident())
                 and self._initialized is True and self._io_unknown is False
                 and all(type(v) is bool for v in (
                     self._intent, self._done, self._cleanup_switched))
                 and type(self._buffer) is bytearray and self._buffer is self._buffer_origin
                 and self._buffer is s.buffer
                 and type(self._received) is int and type(self._target) is int
                 and 0 <= self._received <= self._target <= _MAX_WIRE
                 and len(self._buffer) == self._received and self._pending is None
                 and (self._waiter is None or type(self._waiter) is SelectorReadiness)
                 and self._header is self._header_snapshot)
        if s.expected is not None:
            _require(type(s.expected) is BrokerBinding)
            _binding(s.expected)
        if self._header is not None:
            _require(type(self._header) is BrokerHeader)
            _row(self._header)
            _require(self._header.version == 2 and self._header.kind in ("BEGIN", "READY")
                     and self._header.body_length <= INPUT_LIMIT + 4)

    def _switch_cleanup(self):
        s = self._scope_origin
        _require(type(s) is _PreResultScope)
        if s.owner is not None:
            from .presentation_cleanup_reader import CleanupReadGate
            from .presentation_remote import RemoteOperationOwner
            from .presentation_remote_cleanup import RemoteCleanupOwner

            _require(type(s.owner) is RemoteOperationOwner and type(s.channel) is SocketChannel
                     and s.channel._remote_owner is s.owner
                     and s.channel._remote_owner_snapshot is s.owner
                     and s.owner._channel is s.channel and s.owner._channel_snapshot is s.channel)
            cleanup = s.owner._cleanup_owner_snapshot
            _require(type(cleanup) is RemoteCleanupOwner and s.owner._cleanup_owner is cleanup
                     and cleanup._remote_snapshot is s.owner)
            CleanupReadGate.switch(cleanup._read_gate_snapshot, self)

    def _current(self):
        _PreResultCursor._guard(self)
        _PreResultCursor._switch_cleanup(self)
        s = self._scope_origin
        try:
            if s.owner is not None:
                from .presentation_jobs import RemotePhase
                from .presentation_remote import RemoteOperationOwner

                _require(type(s.owner) is RemoteOperationOwner
                         and s.channel._remote_owner_snapshot is s.owner)
                RemoteOperationOwner._check(s.owner, RemotePhase.BEGIN_INTENT)
            else:
                _require(s.channel._remote_owner_snapshot is None)
            _PreResultCursor._guard(self)
            SocketChannel._remaining(s.channel, s.end)
        except BaseException:
            _PreResultCursor._switch_cleanup(self)
            raise
        _PreResultCursor._switch_cleanup(self)
        if s.owner is not None:
            RemoteOperationOwner._pre_result_local(s.owner, s.channel, s.end)
        _PreResultCursor._guard(self)

    async def _take(self, count):
        _PreResultCursor._current(self)
        _require(type(count) is int and 0 <= count <= _MAX_WIRE)
        start = self._received
        self._target = start + count
        _require(self._target <= _MAX_WIRE and not self._done and not self._intent)
        part = buffer = None
        try:
            while self._received < self._target:
                _PreResultCursor._current(self)
                s, buffer = self._scope_origin, self._buffer_origin
                received, target = self._received, self._target
                self._intent = True
                try:
                    part = _SOCKET_RECV(s.sock, target - received)
                except BlockingIOError as error:
                    if (type(error) is not BlockingIOError or type(error.errno) is not int
                            or error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK)):
                        raise
                    self._intent = False
                    _PreResultCursor._current(self)
                    waiter = SelectorReadiness.__new__(SelectorReadiness)
                    self._waiter = waiter
                    try:
                        SelectorReadiness.__init__(waiter, s.sock)
                        wake = (None if s.owner is None else
                                s.owner._cleanup_owner_snapshot._barriers_snapshot.cause)
                        await SelectorReadiness.wait(waiter, s.end, wake=wake)
                    except ReadinessWakeError:
                        if (waiter._initialized is not True or waiter._unknown is not False
                                or type(waiter._attempted) is not bool
                                or (waiter._attempted is True and waiter._retired is not True)):
                            self._io_unknown = True
                            _require(False)
                        _PreResultCursor._switch_cleanup(self)
                        raise
                    except BaseException:
                        if (getattr(waiter, "_initialized", False) is not True
                                or waiter._unknown is not False
                                or type(waiter._attempted) is not bool
                                or (waiter._attempted is True and waiter._retired is not True)):
                            self._io_unknown = True
                        raise
                    if (self._waiter is not waiter or waiter._initialized is not True
                        or waiter._attempted is not True or waiter._retired is not True
                            or waiter._unknown is not False):
                        self._io_unknown = True
                        _require(False)
                    continue
                self._pending = part
                _require(type(part) is bytes)
                prior_received, prior_target = self._received, self._target
                self._received = received + len(part)
                _require(len(part) <= target - received)
                buffer.extend(part)
                self._pending = None
                self._intent = False
                if (type(prior_received) is not int or prior_received != received
                        or type(prior_target) is not int or prior_target != target
                        or self._buffer is not buffer or self._buffer_origin is not buffer):
                    self._io_unknown = True
                    _require(False)
                _PreResultCursor._current(self)
                _require(bool(part))  # known zero-byte EOF, no invented progress
            return bytes(self._buffer_origin[start:self._target])
        finally:
            part = buffer = None

    async def frame(self):
        from .presentation_cleanup_reader import CleanupReadGate, CleanupReadSwitch

        switched = False
        scope = self._scope_origin
        _require(type(scope) is _PreResultScope and type(scope.buffer) is bytearray)
        original_buffer = scope.buffer
        prefix = raw = body = frame = None
        try:
            prefix = await _PreResultCursor._take(self, 8)
            raw = prefix + await _PreResultCursor._take(self, header_size(prefix))
            s = self._scope_origin
            header = (decode_scope_header(raw, expected_scope=s.channel._enrollment.scope,
                                          expected_version=2) if s.expected is None else
                      decode_header(raw, expected=s.expected, expected_version=2))
            _require(header.kind == ("BEGIN" if s.channel._role == "broker" else "READY")
                     and header.sequence == 0 and header.body_length <= INPUT_LIMIT + 4
                     and (header.kind != "READY" or header.body_length == 0))
            self._header = self._header_snapshot = header
            body = await _PreResultCursor._take(self, header.body_length)
            _PreResultCursor._current(self)
            frame = BrokerFrame(header, body)
            self._done = True
            return frame
        except CleanupReadSwitch as transition:
            _require(transition.reader is self and self._cleanup_switched is True
                     and scope.owner is not None)
            gate = scope.owner._cleanup_owner_snapshot._read_gate_snapshot
            CleanupReadGate.guard(gate)
            _require(gate._requested is True and gate._request_origin.reader is self
                     and gate._request_origin.mode == "ready")
            switched = True
            raise
        except BaseException:
            if self._intent is not False:
                self._io_unknown = True
            raise
        finally:
            prefix = raw = body = frame = None
            if not switched:
                self._pending = None
                original_buffer[:] = b"\x00" * len(original_buffer)
                original_buffer.clear()  # never follow replaced buffer slots on refusal


class SocketChannel:
    """Exclusive native socket, bounded frames and dedicated one-use GO, no retry.

    Endpoint owner/observation outlive every referencing channel. Caller retains
    this owner before initialize; partial native resources remain reachable.
    Only BEGIN and bodyless controls are admitted in this spine. RESULT/GO work
    awaits the separate reviewed authority/custody integration, never a fallback.
    """
    def __init__(self, sock: socket.socket, enrollment: StartupEnrollment, *, role: str,
                 endpoint: BrokerEndpointOwner, observation: EndpointObservation):
        self._socket = self._socket_snapshot = sock
        self._enrollment = self._enrollment_snapshot = enrollment
        self._role = self._role_snapshot = role
        self._endpoint = self._endpoint_snapshot = endpoint
        self._observation = self._observation_snapshot = observation
        self._values = self._values_snapshot = None
        self._context = self._context_snapshot = (os.getpid(), os.geteuid())
        self._integrity_lost = False
        self._fd = self._fd_snapshot = self._identity = self._identity_snapshot = None
        self._refused = self._close_attempted = self._closed_known = False
        self._reading = self._writing = self._closing = False
        self._work_write_retired = False
        self._close_fact = self._close_fact_snapshot = None
        self._terminal_owner = self._terminal_owner_snapshot = None
        self._remote_owner = self._remote_owner_snapshot = None
        self._cancel_receiver = self._cancel_receiver_snapshot = None
        self._begin_write_intent = self._begin_write_intent_snapshot = None
        self._begin_write_fact = self._begin_write_fact_snapshot = None
        self._go_write_intent = self._go_write_intent_snapshot = None
        self._go_write_fact = self._go_write_fact_snapshot = None
        self._result_writer = self._result_writer_snapshot = None
        self._result_receiver = self._result_receiver_snapshot = None
        self._pre_result_cursor = self._pre_result_cursor_snapshot = None
        self._pre_result_cursor_origin = None
        self._clock_owner = self._clock_owner_snapshot = None
        self._clock_closed_known = False
        self._credential_handshake = self._credential_handshake_snapshot = None
        try:
            _require(type(sock) is socket.socket and type(enrollment) is StartupEnrollment
                     and type(role) is str and role in ("gateway", "broker")
                     and type(endpoint) is BrokerEndpointOwner)
            self._values = self._values_snapshot = enrollment.values()
            uid, pid = ((enrollment.gateway_uid, enrollment.gateway_pid) if role == "gateway"
                        else (enrollment.service_uid, enrollment.service_pid))
            _require((os.geteuid(), os.getpid()) == (uid, pid))
            self._fd = self._fd_snapshot = _SOCKET_FILENO(sock)
            self._identity = self._identity_snapshot = self._descriptor()
            sock.setblocking(False)
            self._check()
            if enrollment.protocol_version == 2:
                from .presentation_clock import NativeClockOwner

                # Retain the allocation BEFORE initialization/native effects.
                self._clock_owner = self._clock_owner_snapshot = NativeClockOwner.__new__(
                    NativeClockOwner)
                NativeClockOwner.__init__(self._clock_owner, self)
                self._qualified_clock()
        except BaseException:
            self._refused = True
            raise ChannelAcquisitionError(self) from None

    def _descriptor(self) -> tuple:
        fd = _SOCKET_FILENO(self._socket)
        row = os.fstat(fd)
        _require(type(fd) is int and fd >= 0 and stat.S_ISSOCK(row.st_mode)
                 and os.get_inheritable(fd) is False)
        return fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode)

    def _bindings(self) -> None:
        _require(all(type(v) is bool for v in (self._refused, self._close_attempted,
                 self._closed_known, self._reading, self._writing, self._closing,
                 self._integrity_lost, self._clock_closed_known, self._work_write_retired)))
        _require(self._integrity_lost is False
                 and _context_shape(self._context_snapshot)
                 and self._context is self._context_snapshot
                 and (os.getpid(), os.geteuid()) == self._context_snapshot
                 and _values_shape(self._values_snapshot)
                 and self._values is self._values_snapshot
                 and self._enrollment is self._enrollment_snapshot
                 and type(self._enrollment) is StartupEnrollment
                 and self._enrollment.values() == self._values_snapshot
                 and type(self._role) is str and self._role is self._role_snapshot
                 and self._role in ("gateway", "broker")
                 and self._endpoint is self._endpoint_snapshot
                 and type(self._endpoint) is BrokerEndpointOwner
                 and self._observation is self._observation_snapshot
                 and type(self._observation) is EndpointObservation)
        _require(self._terminal_owner is self._terminal_owner_snapshot
                 and (self._terminal_owner is None
                      or type(self._terminal_owner) is TerminalStatusExchange))
        _require(self._remote_owner is self._remote_owner_snapshot)
        _require(self._begin_write_intent is self._begin_write_intent_snapshot
                 and (self._begin_write_intent is None
                      or type(self._begin_write_intent) is _BeginWriteIntent)
                 and self._begin_write_fact is self._begin_write_fact_snapshot
                 and (self._begin_write_fact is None
                      or (type(self._begin_write_fact) is _BeginWriteFact
                          and self._begin_write_fact.mint is _BEGIN_WRITE_MINT
                          and self._begin_write_fact.intent is self._begin_write_intent)))
        _require(self._go_write_intent is self._go_write_intent_snapshot
                 and (self._go_write_intent is None
                      or (type(self._go_write_intent) is _GoWriteIntent
                          and self._go_write_intent.begin is self._begin_write_fact_snapshot))
                 and self._go_write_fact is self._go_write_fact_snapshot
                 and (self._go_write_fact is None
                      or (type(self._go_write_fact) is _GoWriteFact
                          and self._go_write_fact.mint is _GO_WRITE_MINT
                          and self._go_write_fact.intent is self._go_write_intent_snapshot)))
        _require(self._result_writer is self._result_writer_snapshot
                 and self._result_receiver is self._result_receiver_snapshot)
        if self._result_writer is not None or self._result_receiver is not None:
            from .presentation_result_transport import BrokerResultWriter, RemoteResultOwner

            _require((self._result_writer is None or (self._role == "broker"
                         and type(self._result_writer) is BrokerResultWriter))
                     and (self._result_receiver is None or (self._role == "gateway"
                         and type(self._result_receiver) is RemoteResultOwner)))
        _require(self._cancel_receiver is self._cancel_receiver_snapshot)
        if self._cancel_receiver is not None:
            from .presentation_broker_cancel import BrokerCancellationOwner

            _require(type(self._cancel_receiver) is BrokerCancellationOwner
                     and self._role == "broker" and self._enrollment.protocol_version == 2
                     and self._remote_owner is None and self._terminal_owner is None)
        _require(self._clock_owner is self._clock_owner_snapshot)
        if self._clock_owner is not None:
            from .presentation_clock import NativeClockOwner

            _require(self._enrollment.protocol_version == 2
                     and type(self._clock_owner) is NativeClockOwner)
        if self._remote_owner is not None:
            from .presentation_remote import RemoteOperationOwner

            _require(type(self._remote_owner) is RemoteOperationOwner
                     and self._terminal_owner is None)
        if self._closed_known:
            _require(self._close_attempted and type(self._close_fact) is object
                     and self._close_fact is self._close_fact_snapshot)

    def _local_integrity(self) -> None:
        try:
            self._bindings()
            _require(self._integrity_lost is False
                     and self._socket is self._socket_snapshot
                     and type(self._socket) is socket.socket
                     and self._fd is self._fd_snapshot and type(self._fd) is int
                     and self._identity is self._identity_snapshot
                     and type(self._identity) is tuple and len(self._identity) == 4
                     and all(type(v) is int for v in self._identity)
                     and (os.getpid(), os.geteuid()) == self._context
                     and self._descriptor() == self._identity_snapshot)
        except BaseException:
            self._integrity_lost = True
            self._refused = True
            raise FrameError("BI1_BROKER_CHANNEL_INTEGRITY_LOST") from None

    def _check(self) -> PeerObservation:
        try:
            self._local_integrity()
            _require(not self._refused and not self._close_attempted
                     and self._socket is self._socket_snapshot
                     and type(self._socket) is socket.socket
                     and self._enrollment is self._enrollment_snapshot
                     and type(self._enrollment) is StartupEnrollment
                     and self._enrollment.values() == self._values
                     and self._role is self._role_snapshot
                     and self._endpoint is self._endpoint_snapshot
                     and self._observation is self._observation_snapshot
                     and self._descriptor() == self._identity)
            _require(os.get_blocking(self._fd) is False)
            timeout = _SOCKET_TIMEOUT(self._socket)
            _require(type(timeout) is float and timeout == 0.0)
            e = self._enrollment
            own = ((e.gateway_uid, e.gateway_pid) if self._role == "gateway"
                   else (e.service_uid, e.service_pid))
            _require((os.geteuid(), os.getpid()) == own)
            self._endpoint.validates(self._observation)
            expected_path = self._endpoint._directory_snapshot + "/presentation.sock"
            actual_path = (self._socket.getpeername() if self._role == "gateway"
                           else self._socket.getsockname())
            _require(actual_path == expected_path)
            peer = ((e.service_uid, e.service_pid) if self._role == "gateway"
                    else (e.gateway_uid, e.gateway_pid))
            return observe_peer(self._socket, expected_uid=peer[0], expected_pid=peer[1])
        except BaseException:
            self._refused = True
            raise FrameError("BI1_BROKER_CHANNEL_REFUSED") from None

    def _remaining(self, end_ns: int) -> float:
        _task_allows_work()
        self._check()
        if self._enrollment.protocol_version == 2:
            from .presentation_clock import NativeClockOwner

            clock = self._qualified_clock()
            now = NativeClockOwner.sample(clock)
            _require(self._qualified_clock() is clock)
        else:
            now = time.monotonic_ns()
        self._local_integrity()
        _task_allows_work()
        _require(type(end_ns) is int and now < end_ns)
        return (end_ns - now) / 1_000_000_000

    def _qualified_clock(self):
        from .presentation_clock import NativeClockOwner

        self._bindings()
        clock = self._clock_owner_snapshot
        _require(self._enrollment.protocol_version == 2
                 and clock is self._clock_owner and type(clock) is NativeClockOwner
                 and clock._channel_snapshot is self and clock._channel is self
                 and type(clock._qualification) is object
                 and clock._qualification is clock._qualification_snapshot
                 and self._clock_closed_known is False)
        return clock

    def _credential_external_idle(self):
        owner = getattr(self, "_credential_handshake", None)
        _require(owner is getattr(self, "_credential_handshake_snapshot", None))
        if owner is not None:
            from .presentation_credential_handshake import CredentialHandshakeOwner
            _require(type(owner) is CredentialHandshakeOwner)
            CredentialHandshakeOwner._released(owner, self)

    def close_clock(self) -> bool:
        """Distinct local clock-FD fact; socket close alone never establishes it."""
        try:
            self._credential_external_idle()
            self._bindings()
            _require(self._closed_known is True)
            if self._clock_owner_snapshot is None:
                _require(self._clock_owner is None)
                self._clock_closed_known = True
            else:
                from .presentation_clock import NativeClockOwner

                self._clock_closed_known = NativeClockOwner.close_local(
                    self._clock_owner_snapshot) is True
            self._bindings()
            return self._clock_closed_known
        except BaseException:
            return False  # partial/ambiguous allocation remains reachable

    async def _exact(self, count: int, end_ns: int) -> bytes:
        _require(type(count) is int and 0 <= count <= _MAX_WIRE)
        data = bytearray()
        loop = asyncio.get_running_loop()
        while len(data) < count:
            remaining = self._remaining(end_ns)  # validate before creating the IO coroutine
            part = await asyncio.wait_for(
                loop.sock_recv(self._socket, count - len(data)), remaining)
            self._remaining(end_ns)
            _require(type(part) is bytes and 0 < len(part) <= count - len(data))
            data.extend(part)
        return bytes(data)

    def claim_remote(self, owner) -> None:
        self._credential_external_idle()
        from .presentation_remote import RemoteOperationOwner

        self._bindings()
        _require(type(owner) is RemoteOperationOwner and self._role == "gateway"
                 and self._remote_owner is None and self._terminal_owner is None
                 and not self._reading and not self._writing)
        self._remote_owner = self._remote_owner_snapshot = owner
        self._check()  # failed authentication leaves the same allocation retained

    def _authorize_io(self, owner, direction, binding, end_ns, frame=None):
        self._credential_external_idle()
        if self._remote_owner is None:
            _require(owner is None)
            return
        from .presentation_remote import RemoteOperationOwner

        _require(owner is self._remote_owner and type(owner) is RemoteOperationOwner)
        RemoteOperationOwner._authorize_channel(owner, self, direction, binding, end_ns, frame)

    async def receive(self, end_ns: int, *, expected: BrokerBinding | None = None,
                      owner=None) -> BrokerFrame:
        self._bindings()
        _require(self._cancel_receiver is None)  # exclusive retained cancellation reader
        if self._terminal_owner is not None:
            self._refused = True
            raise FrameError("BI1_BROKER_TERMINAL_CHANNEL_ADOPTED")
        self._authorize_io(owner, "receive", expected, end_ns)
        _require(not self._reading and (self._role == "broker" or expected is not None))
        if self._enrollment.protocol_version == 2:
            _require(self._pre_result_cursor is None and self._pre_result_cursor_snapshot is None
                     and self._pre_result_cursor_origin is None)
            cursor = _PreResultCursor.__new__(_PreResultCursor)
            self._pre_result_cursor = self._pre_result_cursor_snapshot = cursor
            self._pre_result_cursor_origin = cursor
            self._reading = True
            switched = False
            from .presentation_cleanup_reader import CleanupReadGate, CleanupReadSwitch

            try:
                _PreResultCursor.__init__(cursor, self, end_ns, expected, owner)
                return await _PreResultCursor.frame(cursor)
            except CleanupReadSwitch as transition:
                _require(transition.reader is cursor and cursor._cleanup_switched is True
                         and owner is not None)
                gate = owner._cleanup_owner_snapshot._read_gate_snapshot
                CleanupReadGate.guard(gate)
                _require(gate._request_origin.reader is cursor and gate._requested is True)
                switched = True
                raise
            except BaseException:
                self._refused = True
                raise
            finally:
                if (not switched and getattr(cursor, "_initialized", False) is True
                        and cursor._io_unknown is False and cursor._intent is False):
                    self._reading = False
        self._reading = True
        try:
            prefix = await self._exact(8, end_ns)
            raw = prefix + await self._exact(header_size(prefix), end_ns)
            version = self._enrollment.protocol_version
            header = (decode_scope_header(raw, expected_scope=self._enrollment.scope,
                                          expected_version=version)
                      if expected is None else decode_header(raw, expected=expected,
                                                             expected_version=version))
            # v2 operation/cleanup integration is a separate admission gate.
            if version == 2:
                _require(header.kind in ("BEGIN", "READY"))
            _require(header.kind != "RESULT" and header.body_length <= INPUT_LIMIT + 4)
            body = await self._exact(header.body_length, end_ns)
            self._remaining(end_ns)
            return BrokerFrame(header, body)
        except BaseException:
            self._refused = True
            raise
        finally:
            self._reading = False

    async def send(self, frame: BrokerFrame, end_ns: int, *, owner=None) -> None:
        self._bindings()
        if self._terminal_owner is not None:
            self._refused = True
            raise FrameError("BI1_BROKER_TERMINAL_CHANNEL_ADOPTED")
        _require(not self._writing and type(frame) is BrokerFrame
                 and type(frame.header) is BrokerHeader and type(frame.header.kind) is str
                 and frame.header.kind != "RESULT")
        self._authorize_io(owner, "send", frame.header.binding, end_ns, frame)
        if owner is not None and self._enrollment.protocol_version == 2:
            _require(self._work_write_retired is False)
            _require(self._begin_write_intent is None and self._begin_write_fact is None)
            self._begin_write_intent = self._begin_write_intent_snapshot = _BeginWriteIntent(
                owner, self, self._socket_snapshot, self._values_snapshot, self._identity_snapshot,
                frame.header.binding, frame.body, end_ns, 2, object())
        self._writing = True  # intent before any possibly partial write; no rollback/retry
        try:
            _binding(frame.header.binding)
            b, scope = frame.header.binding, self._enrollment.scope
            _require((b.iid, b.listener, b.broker) == (scope.iid, scope.listener, scope.broker))
            version = self._enrollment.protocol_version
            _require(type(frame.header.version) is int and frame.header.version == version)
            if version == 2:
                _require(frame.header.kind in ("BEGIN", "READY"))
            data = encode_frame(frame.header.binding, frame.header.kind,
                                frame.header.sequence, frame.body, version=version)
            _require(len(data) <= _MAX_WIRE)
            remaining = self._remaining(end_ns)
            await asyncio.wait_for(asyncio.get_running_loop().sock_sendall(self._socket, data),
                                   remaining)
            self._remaining(end_ns)
            if owner is not None and version == 2:
                from .presentation_remote import RemoteOperationOwner

                RemoteOperationOwner._authorize_send_completion(owner, self, frame, end_ns)
                intent = self._begin_write_intent_snapshot
                _require(type(intent) is _BeginWriteIntent and self._begin_write_intent is intent
                         and intent.remote is owner and intent.channel is self
                         and intent.socket is self._socket_snapshot
                         and intent.values is self._values_snapshot
                         and intent.identity is self._identity_snapshot
                         and intent.binding is frame.header.binding and intent.packet is frame.body
                         and type(intent.end_ns) is int and intent.end_ns == end_ns
                         and intent.version == 2 and type(intent.token) is object)
                self._begin_write_fact = self._begin_write_fact_snapshot = _BeginWriteFact(
                    _BEGIN_WRITE_MINT, intent)
        except BaseException:
            self._refused = True
            raise
        finally:
            self._writing = False

    def _go_written(self, remote):
        from .presentation_remote import RemoteOperationOwner

        SocketChannel._bindings(self)
        _require(type(remote) is RemoteOperationOwner and self._remote_owner is remote
                 and self._remote_owner_snapshot is remote)
        intent, fact = self._go_write_intent_snapshot, self._go_write_fact_snapshot
        _require(type(intent) is _GoWriteIntent and type(fact) is _GoWriteFact
                 and fact.mint is _GO_WRITE_MINT and fact.intent is intent
                 and intent.begin is self._begin_write_fact_snapshot
                 and type(intent.begin) is _BeginWriteFact
                 and intent.begin.intent.remote is remote
                 and intent.work is remote._cleanup_owner_snapshot._allocations_snapshot[1]
                 and intent.admission is remote._go_admission_snapshot
                 and type(intent.wire) is bytes and type(intent.token) is object)

    async def send_go(self, remote):
        self._credential_external_idle()
        from .presentation_jobs import RemotePhase
        from .presentation_remote import RemoteOperationOwner
        from .presentation_remote_cleanup import _LOOP, RemoteCleanupOwner

        _require(type(remote) is RemoteOperationOwner)
        RemoteOperationOwner._check(remote, RemotePhase.GO_INTENT)
        cleanup = remote._cleanup_owner_snapshot
        _require(type(cleanup) is RemoteCleanupOwner
                 and RemoteCleanupOwner._can_cancel(cleanup)
                 and self is remote._channel_snapshot and self._writing is False
                 and self._reading is False and self._go_write_intent is None
                 and self._work_write_retired is False)
        data = encode_frame(remote._binding_snapshot, "GO", 1, version=2)
        intent = _GoWriteIntent(self._begin_write_fact_snapshot, cleanup._allocations_snapshot[1],
                                remote._go_admission_snapshot, data, object())
        self._go_write_intent = self._go_write_intent_snapshot = intent
        self._writing = True  # intent before any possibly partial native write
        try:
            async with asyncio.timeout_at(remote._end_snapshot / 1_000_000_000):
                RemoteOperationOwner._check(remote, RemotePhase.GO_INTENT)
                _require(self._go_write_intent_snapshot is intent and self._writing is True
                         and self._socket is self._socket_snapshot)
                await _LOOP.sock_sendall(cleanup._loop_snapshot, self._socket_snapshot, data)
            RemoteOperationOwner._check(remote, RemotePhase.GO_INTENT)
            _require(self._go_write_intent is intent and self._go_write_intent_snapshot is intent
                     and self._writing is True and data is intent.wire)
            self._go_write_fact = self._go_write_fact_snapshot = _GoWriteFact(
                _GO_WRITE_MINT, intent)
        except BaseException:
            self._refused = True
            RemoteOperationOwner._poison(remote)
            raise
        finally:
            self._writing = False

    async def send_cancel(self, owner) -> None:
        """One cleanup-only CANCEL; ordinary retired work IO stays refused."""
        from .presentation_remote_cleanup import _LOOP, RemoteCleanupOwner

        self._credential_external_idle()
        _require(type(owner) is RemoteCleanupOwner)
        data = RemoteCleanupOwner._prepare_cancel(owner, self)
        self._writing = True
        try:
            RemoteCleanupOwner._cancel_remaining(owner, self)
            _require(data is owner._cancel_wire_snapshot and owner._cancel_wire is data)
            owner._cancel_timeout = owner._cancel_timeout_snapshot = asyncio.timeout_at(
                owner._cancel_end_snapshot / 1_000_000_000)
            async with owner._cancel_timeout:
                RemoteCleanupOwner._cancel_remaining(owner, self)
                _require(data is owner._cancel_wire_snapshot and owner._cancel_wire is data)
                await _LOOP.sock_sendall(owner._loop_snapshot, self._socket, data)
            RemoteCleanupOwner._cancel_remaining(owner, self)
            _require(data is owner._cancel_wire_snapshot and owner._cancel_wire is data)
            owner._cancel_write_completed = True
        except BaseException:
            owner._unknown = True
            self._refused = True
            raise
        finally:
            self._writing = False

    def close(self) -> bool:
        try:
            self._credential_external_idle()
            self._bindings()
            if self._closing:
                self._integrity_lost = self._refused = True
                return False
            if self._close_attempted:
                _require(self._closed_known and type(self._close_fact) is object
                         and self._close_fact is self._close_fact_snapshot)
                fd = _SOCKET_FILENO(self._socket)
                self._bindings()
                return type(fd) is int and fd == -1
            self._closing = self._close_attempted = True
            _require(not self._reading and not self._writing)
            self._local_integrity()
            _SOCKET_CLOSE(self._socket)
            self._bindings()
            fd = _SOCKET_FILENO(self._socket)
            self._bindings()
            _require(type(fd) is int and fd == -1)
            try:
                os.fstat(self._fd)
            except OSError as error:
                self._bindings()
                _require(error.errno == errno.EBADF)
            else:
                raise FrameError("BI1_BROKER_CHANNEL_CLOSE_UNKNOWN")
            self._bindings()
            self._close_fact = self._close_fact_snapshot = object()
            self._closed_known = True
            self._bindings()
            return True
        except BaseException:
            self._integrity_lost = self._refused = True
            return False
        finally:
            self._closing = False


class TerminalStatusExchange:
    """One sealed bodyless STATUS exchange, never a generic peer-check fallback.

    Initial authentication is mandatory. Once adopted, this channel cannot carry
    ordinary frames. Terminal IO checks current local/generation integrity while
    allowing the authenticated peer to close. EOF is transport-only evidence.
    Caller retains this allocation before initializing; the channel retains it
    before any exchange IO. No native/registry/result authority is supplied.
    """
    def __init__(self, channel: SocketChannel, binding: BrokerBinding, end_ns: int):
        self._channel = self._channel_snapshot = channel
        self._binding = self._binding_snapshot = binding
        self._end = self._end_snapshot = end_ns
        self._failed = False
        self._phase = "initializing"
        self._completion = None
        self._shutdown_intent = self._shutdown_returned = False
        self._seal = self._seal_snapshot = None
        self._authentication = self._authentication_snapshot = None
        self._shutdown = self._shutdown_snapshot = _SOCKET_SHUTDOWN
        self._peek = self._peek_snapshot = _SOCKET_RECV
        self._timeout = self._timeout_snapshot = _SOCKET_TIMEOUT
        try:
            _require(type(channel) is SocketChannel and type(binding) is BrokerBinding)
            _require(channel._enrollment.protocol_version == 1)  # v2 lifecycle not yet joined
            _binding(binding)
            _require(channel._terminal_owner is None and channel._remote_owner is None
                     and not channel._reading and not channel._writing)
            channel._terminal_owner = channel._terminal_owner_snapshot = self
            self._authentication = self._authentication_snapshot = channel._check()
            # Initial auth is sealed below; failed partial owner is already retained.
            _require(type(end_ns) is int
                     and time.monotonic_ns() < end_ns <= time.monotonic_ns() + 2_000_000_000)
            scope = channel._enrollment.scope
            _require((binding.iid, binding.listener, binding.broker)
                     == (scope.iid, scope.listener, scope.broker))
            self._values = self._values_snapshot = (
                binding.iid, binding.listener, binding.broker, binding.channel, binding.operation)
            self._loop = self._loop_snapshot = asyncio.get_running_loop()
            self._seal = self._seal_snapshot = (
                channel._socket, channel._fd, channel._identity, channel._context,
                channel._endpoint, channel._observation, channel._enrollment, channel._values)
            self._phase = "gateway_new" if channel._role == "gateway" else "broker_new"
            self._remaining()
        except BaseException:
            self._failed = True
            if type(channel) is SocketChannel:
                channel._refused = True
            raise

    def _poison(self) -> None:
        self._failed = True
        if type(self._channel) is SocketChannel:
            self._channel._refused = True

    def _remaining(self) -> float:
        try:
            _task_allows_work()
            c = self._channel
            _require(self._failed is False
                     and self._authentication is self._authentication_snapshot
                     and type(self._authentication) is PeerObservation
                     and type(self._authentication.uid) is int
                     and type(self._authentication.pid) is int
                     and type(self._shutdown_intent) is bool
                     and type(self._shutdown_returned) is bool
                     and (self._completion is None or (type(self._completion) is str
                          and self._completion in ("queued_eof", "halfclose_eof", "gateway_eof")))
                     and c is self._channel_snapshot
                     and type(c) is SocketChannel and self._binding is self._binding_snapshot
                     and type(self._binding) is BrokerBinding
                     and self._seal is self._seal_snapshot and type(self._seal) is tuple
                     and len(self._seal) == 8 and self._values is self._values_snapshot
                     and type(self._values) is tuple and len(self._values) == 5
                     and all(type(v) is str for v in self._values)
                     and type(self._phase) is str
                     and self._phase in ("gateway_new", "broker_new", "request_write",
                         "gateway_reply", "reply_read", "gateway_closed_ack",
                         "gateway_halfclose", "closed_ack_write", "reply_write",
                         "broker_eof", "complete")
                     and self._end is self._end_snapshot and type(self._end) is int
                     and self._shutdown is self._shutdown_snapshot
                     and self._shutdown is _SOCKET_SHUTDOWN
                     and self._peek is self._peek_snapshot and self._peek is _SOCKET_RECV
                     and self._timeout is self._timeout_snapshot
                     and self._timeout is _SOCKET_TIMEOUT
                     and self._loop is self._loop_snapshot
                     and asyncio.get_running_loop() is self._loop
                     and c._terminal_owner is self and c._terminal_owner_snapshot is self
                     and not c._refused and not c._close_attempted)
            _binding(self._binding)
            b = self._binding
            _require((b.iid, b.listener, b.broker, b.channel, b.operation) == self._values)
            c._local_integrity()
            expected_peer = ((c._enrollment.service_uid, c._enrollment.service_pid)
                             if c._role == "gateway"
                             else (c._enrollment.gateway_uid, c._enrollment.gateway_pid))
            _require((self._authentication.uid, self._authentication.pid) == expected_peer)
            _require(os.get_blocking(c._fd) is False)  # kernel mode alone is insufficient
            timeout = self._timeout(c._socket)
            _require(type(timeout) is float and timeout == 0.0)  # no Python select wait
            # Reference seals prevent adopting another descriptor, context or
            # endpoint even when its primitive values happen to compare equal.
            current = (c._socket, c._fd, c._identity, c._context,
                       c._endpoint, c._observation, c._enrollment, c._values)
            _require(all(a is b for a, b in zip(current, self._seal, strict=True)))
            c._endpoint.validates(c._observation)
            now = time.monotonic_ns()
            _require(now < self._end)
            return (self._end - now) / 1_000_000_000
        except BaseException:
            self._poison()
            raise

    def _phase_is(self, phase: str) -> None:
        self._remaining()
        if self._phase != phase:
            self._poison()
            raise FrameError("BI1_BROKER_TERMINAL_SEQUENCE_REFUSED")

    async def _write(self, kind: str, sequence: int, *, live_peer=False) -> None:
        c = self._channel
        self._remaining()
        expected = {"request_write": ("gateway", ("STATUS",), 0, False),
                    "reply_write": ("broker", ("PENDING", "UNKNOWN"), 0, False),
                    "closed_ack_write": ("gateway", ("ACK",), 1, True)}
        rule = expected.get(self._phase)
        _require(rule is not None and c._role == rule[0] and type(kind) is str
                 and kind in rule[1] and type(sequence) is int and sequence == rule[2]
                 and type(live_peer) is bool and live_peer is rule[3]
                 and not c._writing and not c._reading)
        c._writing = True
        try:
            data = encode_frame(self._binding, kind, sequence)
            remaining = self._remaining()
            if live_peer:
                c._remaining(self._end)  # existing CLOSED ACK boundary, no relaxation
            await asyncio.wait_for(self._loop.sock_sendall(c._socket, data), remaining)
            self._remaining()
            if live_peer:
                c._remaining(self._end)
        except BaseException:
            self._poison()
            raise
        finally:
            c._writing = False

    async def _exact(self, count: int) -> bytes:
        _require(type(count) is int and 0 <= count <= 1032)
        data = bytearray()
        while len(data) < count:
            remaining = self._remaining()
            part = await asyncio.wait_for(
                self._loop.sock_recv(self._channel._socket, count - len(data)), remaining)
            self._remaining()
            _require(type(part) is bytes and 0 < len(part) <= count - len(data))
            data.extend(part)
        return bytes(data)

    async def _eof(self) -> None:
        remaining = self._remaining()
        part = await asyncio.wait_for(self._loop.sock_recv(self._channel._socket, 1), remaining)
        self._remaining()
        _require(type(part) is bytes and part == b"")

    async def request(self) -> None:
        self._phase_is("gateway_new")
        self._phase = "request_write"  # intent precedes possibly partial write
        await self._write("STATUS", 0)
        self._phase = "gateway_reply"

    async def receive_reply(self) -> BrokerFrame:
        self._phase_is("gateway_reply")
        c = self._channel
        self._phase = "reply_read"
        _require(not c._reading and not c._writing)
        c._reading = True
        try:
            prefix = await self._exact(8)
            raw = prefix + await self._exact(header_size(prefix))
            header = decode_header(raw, expected=self._binding)
            _require(header.sequence == 0 and header.body_length == 0
                     and header.kind in ("PENDING", "UNKNOWN", "CLOSED"))
            if header.kind == "CLOSED":
                c._remaining(self._end)  # retains existing peer/ACK requirements
                self._phase = "gateway_closed_ack"
            else:
                self._remaining()
                try:
                    queued = self._peek(c._socket, 1, socket.MSG_PEEK)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK))
                    queued = None
                self._remaining()
                _require(queued is None or (type(queued) is bytes and queued == b""))
                if queued is None:
                    self._phase = "gateway_halfclose"  # intent before one fallible effect
                    self._remaining()
                    self._shutdown_intent = True
                    self._shutdown(c._socket, socket.SHUT_WR)
                    self._remaining()
                    self._shutdown_returned = True
                    await self._eof()  # trailing data cannot become a valid terminal reply
                    self._completion = "halfclose_eof"
                else:
                    self._completion = "queued_eof"
                # Already-queued clean EOF needs no shutdown of a disconnected
                # socket. A failed/ambiguous shutdown above never takes this path.
                self._phase = "complete"
            return BrokerFrame(header, b"")
        except BaseException:
            self._poison()
            raise
        finally:
            c._reading = False

    async def acknowledge_closed(self) -> None:
        self._phase_is("gateway_closed_ack")
        self._phase = "closed_ack_write"
        await self._write("ACK", 1, live_peer=True)
        self._phase = "complete"

    async def reply_and_drain(self, kind: str) -> None:
        self._phase_is("broker_new")
        if type(kind) is not str or kind not in ("PENDING", "UNKNOWN"):
            self._poison()
            raise FrameError("BI1_BROKER_TERMINAL_KIND_REFUSED")
        self._phase = "reply_write"
        await self._write(kind, 0)
        self._phase = "broker_eof"
        c = self._channel
        _require(not c._reading and not c._writing)
        c._reading = True
        try:
            await self._eof()
            self._completion = "gateway_eof"
            self._phase = "complete"
        except BaseException:
            self._poison()
            raise
        finally:
            c._reading = False


class _Connection:
    def __init__(self, sock):
        self.socket = sock  # retain accepted socket before authentication/initialization
        self.channel = self.channel_snapshot = None
        self.cancel_owner = None
        self.result_writer = self.result_writer_snapshot = None
        self.ticket = None
        self.grammar = None
        self.task = None
        self.local_closed = False
        self.clock_closed = False
        self.control_task = None
        self.accept_unknown = False
        self.terminal = None


class ServiceAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_BROKER_SERVICE_START_UNKNOWN")
        self.failed_owner = owner


class BrokerServiceSpine:
    """One externally enrolled listener, shared replay/registry and retained debt.

    Adopt a private already-bound/listening socket from trusted startup. Never
    create/unlink endpoints or enroll from frames. This slice handles real
    admission/control/private-result paths, but cannot release a started
    reservation or publish data. It is not a runnable production CLI.
    """
    def __init__(self, listener: socket.socket, enrollment: StartupEnrollment, *,
                 endpoint: BrokerEndpointOwner, observation: EndpointObservation,
                 parser_package: str | None = None):
        self._listener = self._listener_snapshot = listener
        self._enrollment = self._enrollment_snapshot = enrollment
        self._endpoint = self._endpoint_snapshot = endpoint
        self._observation = self._observation_snapshot = observation
        self._records: list[_Connection] = []
        self._records_snapshot = self._records
        self._accepting = self._stopping = self._refused = self._integrity_lost = False
        self._registry = None
        self._accept_task = None
        self._accept_wait = None
        self._accept_registration_unknown = False
        self._context = self._context_snapshot = (os.getpid(), os.geteuid())
        self._values = self._values_snapshot = None
        self._listener_identity = self._listener_identity_snapshot = None
        try:
            self._initialize(listener, enrollment, endpoint, observation, parser_package)
        except BaseException:
            self._refused = True
            raise ServiceAcquisitionError(self) from None

    def _initialize(self, listener, enrollment, endpoint, observation, parser_package):
        _require(type(listener) is socket.socket and type(enrollment) is StartupEnrollment
                 and type(endpoint) is BrokerEndpointOwner)
        self._values = self._values_snapshot = enrollment.values()
        _require((os.geteuid(), os.getpid()) == (enrollment.service_uid, enrollment.service_pid))
        endpoint.validates(observation)
        _require(listener.family == socket.AF_UNIX
                 and listener.getsockname() == endpoint._directory_snapshot + "/presentation.sock")
        self._listener_identity = self._listener_identity_snapshot = self._descriptor(initial=True)
        listener.setblocking(False)
        # One registry per service lifetime, never per connection. Its replay
        # bitmap remains even after a terminal unlaunched tombstone is ACKed.
        registry = BrokerRegistry.__new__(BrokerRegistry)
        self._registry = registry
        registry.__init__(enrollment.scope, parser_package=parser_package)

    def _metadata(self) -> None:
        _require(_context_shape(self._context_snapshot)
                 and self._context is self._context_snapshot
                 and (os.getpid(), os.geteuid()) == self._context_snapshot
                 and _values_shape(self._values_snapshot)
                 and self._values is self._values_snapshot
                 and type(self._enrollment) is StartupEnrollment
                 and self._enrollment is self._enrollment_snapshot
                 and self._enrollment.values() == self._values_snapshot
                 and self._listener is self._listener_snapshot
                 and type(self._listener) is socket.socket
                 and type(self._records) is list and self._records is self._records_snapshot
                 and self._endpoint is self._endpoint_snapshot
                 and type(self._endpoint) is BrokerEndpointOwner
                 and self._observation is self._observation_snapshot
                 and type(self._observation) is EndpointObservation
                 and self._integrity_lost is False
                 and all(type(v) is bool for v in (self._accepting, self._stopping,
                         self._refused, self._integrity_lost, self._accept_registration_unknown)))

    def _descriptor(self, *, initial=False):
        self._metadata()
        if not initial:
            _require(_identity_shape(self._listener_identity_snapshot)
                     and self._listener_identity is self._listener_identity_snapshot)
        fd = _SOCKET_FILENO(self._listener)
        row = os.fstat(fd)
        _require(type(fd) is int and fd >= 0 and stat.S_ISSOCK(row.st_mode)
                 and os.get_inheritable(fd) is False)
        self._metadata()
        return fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode)

    def _local_integrity(self) -> None:
        try:
            self._metadata()
            _require(self._descriptor() == self._listener_identity_snapshot)
        except BaseException:
            self._integrity_lost = self._refused = True
            raise FrameError("BI1_BROKER_LISTENER_INTEGRITY_LOST") from None

    def _current(self) -> None:
        try:
            self._local_integrity()
            _require(not self._refused and not self._stopping
                     and self._listener is self._listener_snapshot
                     and self._descriptor() == self._listener_identity
                     and self._enrollment is self._enrollment_snapshot
                     and self._enrollment.values() == self._values
                     and (os.geteuid(), os.getpid()) == (
                         self._enrollment.service_uid, self._enrollment.service_pid))
            self._endpoint.validates(self._observation)
        except BaseException:
            self._refused = True
            raise FrameError("BI1_BROKER_SERVICE_GENERATION_REFUSED") from None

    async def _accept_owned(self, end_ns: int) -> _Connection:
        # Holder allocation AND service retention precede native accept. Its
        # socket slot already exists; no constructor/append follows the effect.
        self._current()
        record = _Connection(None)
        record.task = asyncio.current_task()
        self._records.append(record)
        loop = asyncio.get_running_loop()
        try:
            while True:
                _task_allows_work()
                self._current()
                _require(type(end_ns) is int and time.monotonic_ns() < end_ns)
                try:
                    sock, _ = _SOCKET_ACCEPT(self._listener)
                except BlockingIOError:
                    # No accepted FD. Await readiness only; a cancelled future
                    # can never discard an accepted socket result.
                    ready = loop.create_future()
                    self._accept_wait = ready
                    fd = self._listener_identity[0]
                    def readable(held=ready):
                        if not held.done():
                            held.set_result(None)
                    self._accept_registration_unknown = True
                    try:
                        loop.add_reader(fd, readable)
                        await asyncio.wait_for(ready,
                            max(0, (end_ns - time.monotonic_ns()) / 1_000_000_000))
                    finally:
                        self._local_integrity()
                        if self._descriptor() == self._listener_identity_snapshot:
                            removed = loop.remove_reader(fd)
                            if removed is True:
                                self._accept_registration_unknown = False
                                self._accept_wait = None
                        if self._accept_registration_unknown:
                            self._refused = True
                            raise FrameError("BI1_BROKER_ACCEPT_REGISTRATION_UNKNOWN")
                    continue
                except BaseException:
                    record.accept_unknown = True
                    raise
                record.socket = sock  # already-retained holder; no intervening await
                return record
        finally:
            if record.socket is None and record.accept_unknown is False:
                # Only before accept or exact native EAGAIN: no acquired socket.
                record.local_closed = True
                self._records.remove(record)

    async def serve_once(self, admission_end_ns: int) -> None:
        """Retain one accepted connection before checking peer or decoding bytes."""
        self._current()
        _require(not self._accepting and type(admission_end_ns) is int
                 and time.monotonic_ns() < admission_end_ns
                 <= time.monotonic_ns() + 2_000_000_000
                 and sum(not r.local_closed for r in self._records) < _MAX_CONNECTIONS)
        self._accepting = True
        self._accept_task = asyncio.current_task()
        owned_accept = True
        record = None
        try:
            record = await self._accept_owned(admission_end_ns)
            try:
                record.channel = SocketChannel(record.socket, self._enrollment, role="broker",
                    endpoint=self._endpoint, observation=self._observation)
            except ChannelAcquisitionError as error:
                record.channel = record.channel_snapshot = error.failed_owner
                raise
            record.channel_snapshot = record.channel
            self._current()
            self._accepting = False
            self._accept_task = None
            owned_accept = False
            await self._dispatch(record, admission_end_ns)
        finally:
            if owned_accept:
                self._accepting = False
                self._accept_task = None
            if record is not None:
                await self._retire_connection(record)

    async def _write(self, record: _Connection, binding: BrokerBinding, kind: str,
                     sequence: int, end_ns: int) -> None:
        # Grammar captures outgoing intent before a possibly partial send.
        frame = BrokerFrame(BrokerHeader(binding, kind, sequence, 0,
                                        self._enrollment.protocol_version), b"")
        record.grammar.observe(frame, sender="broker")
        await record.channel.send(frame, end_ns)

    async def _dispatch(self, record: _Connection, admission_end_ns: int) -> None:
        channel = record.channel
        if self._enrollment.protocol_version == 2:
            await BrokerServiceSpine._dispatch_v2(self, record, admission_end_ns)
            return
        _require(self._enrollment.protocol_version == 1)
        first = await channel.receive(admission_end_ns)
        binding, kind = first.header.binding, first.header.kind
        _require(kind in ("BEGIN", "STATUS"))
        mode = "status" if kind == "STATUS" else "operation"
        record.grammar = OperationGrammar(binding, role="broker", mode=mode)
        record.grammar.observe(first, sender="client")
        self._current()
        if mode == "status":
            status = self._registry.status(binding)
            response = {RegistryStatus.PENDING: "PENDING", RegistryStatus.UNKNOWN: "UNKNOWN",
                        RegistryStatus.CLOSED: "CLOSED"}[status]
            if status is not RegistryStatus.CLOSED:
                record.terminal = TerminalStatusExchange.__new__(TerminalStatusExchange)
                record.terminal.__init__(channel, binding, admission_end_ns)
                frame = BrokerFrame(BrokerHeader(binding, response, 0, 0), b"")
                record.grammar.observe(frame, sender="broker")
                await record.terminal.reply_and_drain(response)
                return  # transport EOF cannot acknowledge or release registry debt
            await self._write(record, binding, response, 0, admission_end_ns)
            if status is RegistryStatus.CLOSED:
                ack = await channel.receive(admission_end_ns, expected=binding)
                record.grammar.observe(ack, sender="client")
                _require(ack.header.kind == "ACK")
                self._current()
                self._registry.acknowledge(binding)
            return  # STATUS has no body replay, BEGIN, GO or work resumption
        row = decode_input_v3(first.body)
        _require(row["iid"] == binding.iid and time.monotonic_ns() < row["deadline_ns"]
                 <= admission_end_ns)
        deadline = row["deadline_ns"]
        record.ticket = self._registry.reserve(binding, row["profile"], row["operation"], deadline)
        self._current()
        record.control_task = asyncio.create_task(channel.receive(deadline, expected=binding))
        while not self._registry.resources_startable(record.ticket):
            self._current()
            _require(time.monotonic_ns() < deadline)
            if record.control_task.done():
                control = record.control_task.result()
                record.grammar.observe(control, sender="client")
                _require(control.header.kind == "CANCEL")
                record.grammar.invalidate()
                self._registry.seal_unlaunched(record.ticket)
                return
            await asyncio.sleep(0.001)
        await asyncio.sleep(0)  # observe already-delivered cancellation before launch
        if record.control_task.done():
            control = record.control_task.result()
            record.grammar.observe(control, sender="client")
            _require(control.header.kind == "CANCEL")
            record.grammar.invalidate()
            self._registry.seal_unlaunched(record.ticket)
            return
        _task_allows_work()
        self._current()
        self._registry.start_resources(record.ticket)
        self._registry.stage_resource_input(record.ticket, first.body)
        await self._write(record, binding, "READY", 0, deadline)
        control = await record.control_task
        record.grammar.observe(control, sender="client")
        # GO has no implicit native authorization. Until the distinct remote
        # owner/pre-GO integration is reviewed, every GO is refusal+cleanup.
        _require(control.header.kind == "CANCEL")
        record.grammar.invalidate()
        self._registry.abort_resources(record.ticket)
        # Started ownership remains PENDING even after exact local drain. No
        # CLOSED/ACK is manufactured; EOF tells the caller to reconcile STATUS.

    async def _v2_control(self, owner):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_remote_cleanup import _FUTURE, _TASK

        _require(type(owner) is BrokerCancellationOwner)
        try:
            BrokerCancellationOwner._guard(owner)
            task, notice = owner._allocation_snapshot.task, owner._cancel_future_snapshot
            await asyncio.wait((task, notice), return_when=asyncio.FIRST_COMPLETED)
            BrokerCancellationOwner._guard(owner)
            if not _FUTURE.done(notice):
                _TASK.result(task)  # original controller failure, never invent adoption
                _require(False)
            receipt = BrokerCancellationOwner.cancel_receipt(owner)
            _require(owner._adopted is True and receipt.frame is owner._frame_snapshot)
            return receipt.frame
        except asyncio.CancelledError:
            raise  # caller cancellation uses the existing original-controller retirement
        except BaseException:
            BrokerCancellationOwner.refuse_notice(owner)
            raise

    def _v2_work_current(self, owner):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_cancel_budget import CancellationBudget

        BrokerCancellationOwner._guard(owner)
        self._current()
        BrokerCancellationOwner._guard(owner)
        _, _, end, failed = CancellationBudget.inspect(owner._scope_snapshot[3])
        _require(owner._retired is False and end is None and not failed)
        _task_allows_work()

    async def _dispatch_v2(self, record, admission_end_ns):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_clock import NativeClockOwner
        from .presentation_remote_cleanup import _LOOP, _TASK

        loop = asyncio.get_running_loop()
        _require(type(loop) is _LOOP and type(asyncio.current_task()) is _TASK
                 and asyncio.BaseEventLoop.get_task_factory(loop) is None)
        channel = record.channel_snapshot
        _require(type(channel) is SocketChannel and record.channel is channel)
        first = await SocketChannel.receive(channel, admission_end_ns)
        _require(first.header.kind == "BEGIN")  # v2 STATUS/GO/result/release remain closed
        binding = first.header.binding
        record.grammar = OperationGrammar(binding, role="broker", protocol_version=2)
        OperationGrammar.observe(record.grammar, first, sender="client")
        row = decode_input_v3(first.body)
        clock = SocketChannel._qualified_clock(channel)
        now = NativeClockOwner.sample(clock)
        _require(SocketChannel._qualified_clock(channel) is clock
                 and row["iid"] == binding.iid and type(now) is int
                 and now < row["deadline_ns"] <= admission_end_ns)
        self._current()
        record.ticket = self._registry.reserve(binding, row["profile"], row["operation"],
                                              row["deadline_ns"])
        BrokerRegistry.bind_input_receipt_once(self._registry, record.ticket, first.body)
        try:
            owner = BrokerCancellationOwner.retain(channel, self._registry, record.ticket,
                                                   record.grammar)
        finally:
            record.cancel_owner = channel._cancel_receiver_snapshot  # includes partial initializer
        while True:
            BrokerCancellationOwner._guard(owner)
            if owner._retired is True or _TASK.done(owner._allocation_snapshot.task):
                await BrokerServiceSpine._v2_control(self, owner)
                self._registry.seal_unlaunched(record.ticket)
                return
            BrokerServiceSpine._v2_work_current(self, owner)
            if self._registry.resources_startable(record.ticket):
                break
            await asyncio.sleep(0.001)
        await asyncio.sleep(0)  # delivered CANCEL header gets first chance to retire work
        BrokerCancellationOwner._guard(owner)
        if owner._retired is True or _TASK.done(owner._allocation_snapshot.task):
            await BrokerServiceSpine._v2_control(self, owner)
            self._registry.seal_unlaunched(record.ticket)
            return
        BrokerServiceSpine._v2_work_current(self, owner)
        self._registry.start_resources(record.ticket)
        BrokerServiceSpine._v2_work_current(self, owner)
        self._registry.stage_resource_input(record.ticket, first.body)
        BrokerServiceSpine._v2_work_current(self, owner)
        try:
            await BrokerServiceSpine._write(self, record, binding, "READY", 0, row["deadline_ns"])
        except FrameError:
            # A newly arrived CANCEL header may retire the work clock during a
            # READY write. Finish that same receiver under its frozen interval;
            # no second read, READY retry or early resource effect is permitted.
            BrokerCancellationOwner._guard(owner)
            _require(owner._retired is True and not _TASK.cancelling(asyncio.current_task()))
        await asyncio.wait((owner._allocation_snapshot.task, owner._go_future_snapshot,
                            owner._cancel_future_snapshot),
                           return_when=asyncio.FIRST_COMPLETED)
        BrokerCancellationOwner._guard(owner)
        if owner._retired is False and owner._go_receipt_snapshot is not None:
            receipt = BrokerCancellationOwner.go_receipt(owner)
            BrokerServiceSpine._v2_work_current(self, owner)
            _require(BrokerCancellationOwner.go_receipt(owner) is receipt
                     and owner._go_relay_intent is False)
            owner._go_relay_intent = True  # before concrete resource/control effects
            self._registry.relay_resource_go(record.ticket)
            BrokerServiceSpine._v2_work_current(self, owner)
            _require(BrokerCancellationOwner.go_receipt(owner) is receipt)
            owner._go_relay_completed = True  # control write only, never execution ack
            from .presentation_result_transport import BrokerResultWriter

            writer = BrokerResultWriter.retain(self, record, first.body)
            while owner._retired is False and not _TASK.done(owner._allocation_snapshot.task):
                BrokerServiceSpine._v2_work_current(self, owner)
                if BrokerResultWriter.poll(writer):
                    sent = await BrokerResultWriter.send(writer)
                    if not sent:
                        if writer._cancel_requested is True:
                            await BrokerServiceSpine._v2_control(self, owner)
                        return  # original budget frozen; finally joins IO/reader and cleans locally
                    elif owner._retired is False:
                        from .presentation_terminal_claim import LocalStartedProducer

                        LocalStartedProducer.retain(self, record)
                    break
                await asyncio.sleep(0.001)
        await BrokerServiceSpine._v2_control(self, owner)
        self._registry.abort_resources(record.ticket)  # inherited minimum already adopted

    async def _retire_v2(self, record):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_remote_cleanup import _TASK

        channel = record.channel_snapshot
        if type(channel) is not SocketChannel or record.channel is not channel:
            self._refused = True
            return
        owner = channel._cancel_receiver_snapshot
        if owner is None:
            if record.ticket is not None:
                self._refused = True
                return  # reservation without a qualified receiver retains unknown debt
            # No operation/resource exists; first-frame IO has returned to its
            # own finally before local connection/clock retirement.
            record.local_closed = SocketChannel.close(channel)
            if record.local_closed:
                record.clock_closed = SocketChannel.close_clock(channel)
        else:
            if type(owner) is not BrokerCancellationOwner or record.cancel_owner is not owner:
                self._refused = True
                return
            BrokerCancellationOwner.abort(owner)  # original budget BEFORE native Task.cancel
            if not await BrokerCancellationOwner.join(owner):
                self._refused = True
                return  # partial/unjoined reader cannot lose its channel
            with contextlib.suppress(BaseException):
                _TASK.result(owner._allocation_snapshot.task)
            try:
                self._metadata()
                held = self._registry._record(record.ticket)
                _require(held is owner._scope_snapshot[0]
                         and held.cleanup_budget is owner._scope_snapshot[3])
                if held.resources is None:
                    if self._registry.status(held.binding) is not RegistryStatus.CLOSED:
                        self._registry.seal_unlaunched(record.ticket)
                else:
                    self._registry.abort_resources(record.ticket)  # memory revoke, no IO
                    while BrokerCancellationOwner.cleanup_remaining(owner) > 0:
                        if self._registry.poll_resource_cleanup(record.ticket):
                            break
                        await asyncio.sleep(0.001)
                if BrokerCancellationOwner.cleanup_remaining(owner) <= 0:
                    return  # no late socket/clock action and no renewed shutdown allowance
                if (held.terminal_producer is None and held.resources is not None
                        and held.resources._observation is not None):
                    from .presentation_terminal_claim import LocalStartedProducer

                    LocalStartedProducer.retain(self, record)
                record.local_closed = SocketChannel.close(channel)
                if record.local_closed and BrokerCancellationOwner.cleanup_remaining(owner) > 0:
                    record.clock_closed = SocketChannel.close_clock(channel)
            except BaseException:
                self._refused = True
                return
        if record.local_closed and record.clock_closed:
            self._records.remove(record)  # registry/native debt remains separate

    async def _retire_connection(self, record: _Connection) -> None:
        if (_values_shape(self._values_snapshot) and self._values_snapshot[8] == 2):
            await BrokerServiceSpine._retire_v2(self, record)
            return
        if record.grammar is not None:
            record.grammar.invalidate()  # before cleanup await; publication never revives
        if record.control_task is not None:
            if not record.control_task.done():
                record.control_task.cancel()
            # Connection is retired; registry closure is independently checked below.
            with contextlib.suppress(BaseException):
                await record.control_task
        if record.ticket is not None:
            try:
                held = self._registry._record(record.ticket)
                if held.resources is None:
                    if self._registry.status(held.binding) is not RegistryStatus.CLOSED:
                        self._registry.seal_unlaunched(record.ticket)
                else:
                    self._registry.abort_resources(record.ticket)
                retained = self._registry._record(record.ticket).resources
                end = None if retained is None else retained._cleanup_end_snapshot
                while type(end) is int and time.monotonic_ns() < end:
                    if self._registry.poll_resource_cleanup(record.ticket):
                        break
                    await asyncio.sleep(0.001)
            except BaseException:
                # Registry retains the exact uncertain owner; no slot release.
                self._refused = True
        if record.channel is not None:
            record.local_closed = record.channel.close()
            if record.local_closed:
                record.clock_closed = record.channel.close_clock()
        # Keep unknown local descriptors and all registry ownership reachable.
        # Known closed connection records can go; their registry tickets cannot.
        if record.local_closed and record.clock_closed:
            self._records.remove(record)

    async def stop_local_sockets(self) -> bool:
        """Retire local listener only; never claim remote/native/child closure."""
        try:
            self._metadata()
        except BaseException:
            self._refused = True
            return False
        if self._stopping:
            return False  # no repeated shutdown intents or close attempts
        _require(all(r.task is not asyncio.current_task() for r in self._records)
                 and self._accept_task is not asyncio.current_task())
        self._stopping = True
        tasks = {r.task for r in self._records if r.task is not None and not r.task.done()}
        if self._accept_task is not None and not self._accept_task.done():
            tasks.add(self._accept_task)
        for task in tasks:
            task.cancel()  # once; its finally owns cancellation/local cleanup
        if tasks:
            done, _pending = await asyncio.wait(tasks, timeout=0.25)
            for task in done:
                if not task.cancelled():
                    task.exception()  # consume diagnostic without exposing details
        for record in tuple(self._records):
            if record.task is None or record.task.done():
                await self._retire_connection(record)
        try:
            self._local_integrity()
            _require(self._listener is self._listener_snapshot
                     and self._descriptor() == self._listener_identity_snapshot)
            fd = self._listener_identity[0]
            _SOCKET_CLOSE(self._listener)
            _require(_SOCKET_FILENO(self._listener) == -1)
            try:
                os.fstat(fd)
            except OSError as error:
                _require(error.errno == errno.EBADF)
            else:
                return False
            return (not self._records and all(t.done() for t in tasks)
                    and not self._accept_registration_unknown)
            # Only local socket closure; registry and any pending tasks stay retained.
        except BaseException:
            self._refused = True
            return False
