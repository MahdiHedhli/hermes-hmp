"""Enrolled private socket service spine; NO production admission or GO.

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
import time
from dataclasses import dataclass

from .presentation_broker_codec import (
    BrokerBinding,
    BrokerFrame,
    BrokerHeader,
    _binding,
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


class SocketChannel:
    """Exclusive exact native socket, bounded no-GO spine frames, no retry.

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
        self._close_fact = self._close_fact_snapshot = None
        self._terminal_owner = self._terminal_owner_snapshot = None
        self._remote_owner = self._remote_owner_snapshot = None
        self._cancel_receiver = self._cancel_receiver_snapshot = None
        self._clock_owner = self._clock_owner_snapshot = None
        self._clock_closed_known = False
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
                 self._integrity_lost, self._clock_closed_known)))
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

    def close_clock(self) -> bool:
        """Distinct local clock-FD fact; socket close alone never establishes it."""
        try:
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
        from .presentation_remote import RemoteOperationOwner

        self._bindings()
        _require(type(owner) is RemoteOperationOwner and self._role == "gateway"
                 and self._remote_owner is None and self._terminal_owner is None
                 and not self._reading and not self._writing)
        self._remote_owner = self._remote_owner_snapshot = owner
        self._check()  # failed authentication leaves the same allocation retained

    def _authorize_io(self, owner, direction, binding, end_ns, frame=None):
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
        except BaseException:
            self._refused = True
            raise
        finally:
            self._writing = False

    def close(self) -> bool:
        try:
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
        self.channel = None
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
    admission/READY/cancellation/STATUS, but deliberately cannot relay GO, send
    RESULT or release a started reservation. It is not a runnable production CLI.
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
                record.channel = error.failed_owner
                raise
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
        frame = BrokerFrame(BrokerHeader(binding, kind, sequence, 0), b"")
        record.grammar.observe(frame, sender="broker")
        await record.channel.send(frame, end_ns)

    async def _dispatch(self, record: _Connection, admission_end_ns: int) -> None:
        channel = record.channel
        # Selected framing is not permission to renew cleanup or start work.
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

    async def _retire_connection(self, record: _Connection) -> None:
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
