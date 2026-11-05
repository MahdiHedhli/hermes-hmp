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
from .presentation_broker_peer import observe_peer
from .presentation_broker_registry import BrokerRegistry, RegistryStatus
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import INPUT_LIMIT, MAX_PROCESSES, MAX_WAITING, FrameError

_MAX_CONNECTIONS = MAX_PROCESSES + MAX_WAITING
_MAX_WIRE = 8 + 1024 + INPUT_LIMIT + 4
_SOCKET_CLOSE = socket.socket.close
_SOCKET_FILENO = socket.socket.fileno
_SOCKET_ACCEPT = socket.socket.accept


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
    return (type(value) is tuple and len(value) == 8
            and all(type(value[i]) is str for i in (0, 1, 2, 7))
            and all(type(value[i]) is int for i in (3, 4, 5, 6)))


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

    def validate(self) -> None:
        _require(type(self.scope) is BrokerBinding)
        _binding(self.scope)
        for value in (self.gateway_uid, self.service_uid):
            _require(type(value) is int and 1 <= value < (1 << 31))
        for value in (self.gateway_pid, self.service_pid):
            _require(type(value) is int and 1 < value < (1 << 31))
        _require(self.gateway_pid != self.service_pid)
        value = self.installation_generation
        _require(type(value) is str and len(value) == 64
                 and all(c in "0123456789abcdef" for c in value))

    def values(self) -> tuple:
        self.validate()
        b = self.scope
        return (b.iid, b.listener, b.broker, self.gateway_uid, self.gateway_pid,
                self.service_uid, self.service_pid, self.installation_generation)


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
                 self._integrity_lost)))
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

    def _check(self) -> None:
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
            observe_peer(self._socket, expected_uid=peer[0], expected_pid=peer[1])
        except BaseException:
            self._refused = True
            raise FrameError("BI1_BROKER_CHANNEL_REFUSED") from None

    def _remaining(self, end_ns: int) -> float:
        _task_allows_work()
        self._check()
        now = time.monotonic_ns()
        _require(type(end_ns) is int and now < end_ns)
        return (end_ns - now) / 1_000_000_000

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

    async def receive(self, end_ns: int, *, expected: BrokerBinding | None = None) -> BrokerFrame:
        self._bindings()
        _require(not self._reading and (self._role == "broker" or expected is not None))
        self._reading = True
        try:
            prefix = await self._exact(8, end_ns)
            raw = prefix + await self._exact(header_size(prefix), end_ns)
            header = (decode_scope_header(raw, expected_scope=self._enrollment.scope)
                      if expected is None else decode_header(raw, expected=expected))
            _require(header.kind != "RESULT" and header.body_length <= INPUT_LIMIT + 4)
            body = await self._exact(header.body_length, end_ns)
            self._remaining(end_ns)
            return BrokerFrame(header, body)
        except BaseException:
            self._refused = True
            raise
        finally:
            self._reading = False

    async def send(self, frame: BrokerFrame, end_ns: int) -> None:
        self._bindings()
        _require(not self._writing and type(frame) is BrokerFrame
                 and type(frame.header) is BrokerHeader and type(frame.header.kind) is str
                 and frame.header.kind != "RESULT")
        self._writing = True  # intent before any possibly partial write; no rollback/retry
        try:
            data = encode_frame(frame.header.binding, frame.header.kind,
                                frame.header.sequence, frame.body)
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


class _Connection:
    def __init__(self, sock):
        self.socket = sock  # retain accepted socket before authentication/initialization
        self.channel = None
        self.ticket = None
        self.grammar = None
        self.task = None
        self.local_closed = False
        self.control_task = None
        self.accept_unknown = False


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
        # Keep unknown local descriptors and all registry ownership reachable.
        # Known closed connection records can go; their registry tickets cannot.
        if record.local_closed:
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
