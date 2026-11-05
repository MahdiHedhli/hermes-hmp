"""Bounded result2 candidates, never publication, native custody or release.

Original service/work tasks only. Normal failures return no payload or exception
traceback retaining a full candidate. Runtime qualification remains separate.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from contextlib import suppress
from typing import NamedTuple

from .presentation_authority import AuthorityRefusalError
from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_codec import (
    BrokerFrame,
    BrokerHeader,
    _row,
    decode_header,
    encode_header,
    header_size,
)
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_registry import BrokerRegistry, BrokerTicket, _Record
from .presentation_broker_resources import BrokerReaderResources
from .presentation_broker_service import (
    _SOCKET_TIMEOUT,
    BrokerServiceSpine,
    SocketChannel,
    _Connection,
)
from .presentation_cancel_budget import CancellationBudget
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import OUTPUT_LIMIT, RemotePhase, State, _Job
from .presentation_output_v2 import BoundedResultBufferV2, compare_parent_snapshot
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _LOOP, _TASK, RemoteCleanupOwner, _TaskAllocation


def _require(value):
    if value is not True:
        raise AuthorityRefusalError


def _native_io(channel):
    SocketChannel._local_integrity(channel)
    timeout = _SOCKET_TIMEOUT(channel._socket_snapshot)
    _require(os.get_blocking(channel._fd) is False
             and type(timeout) is float and timeout == 0.0)


class _WriterScope(NamedTuple):
    service: object
    connection: object
    channel: object
    registry: object
    ticket: object
    record: object
    resources: object
    control: object
    control_scope: tuple
    control_allocation: object
    grammar: object
    packet: bytes
    input_context: tuple
    task: object


_TRANSFER_MINT = object()


class _CompletedResultTransfer(NamedTuple):
    mint: object
    writer: object
    scope: _WriterScope
    sha256: str
    length: int

    def __repr__(self):
        return "<CompletedResultTransfer metadata-only redacted>"


class BrokerResultWriter:
    @classmethod
    def retain(cls, service, connection, packet):
        _require(cls is BrokerResultWriter and type(connection) is _Connection
                 and type(connection.channel_snapshot) is SocketChannel
                 and connection.result_writer is None
                 and connection.channel_snapshot._result_writer is None)
        owner = BrokerResultWriter.__new__(BrokerResultWriter)
        connection.result_writer = connection.result_writer_snapshot = owner
        channel = connection.channel_snapshot
        channel._result_writer = channel._result_writer_snapshot = owner
        BrokerResultWriter.__init__(owner, service, connection, packet)
        return owner

    def __init__(self, service, connection, packet):
        self._scope = self._scope_snapshot = None
        self._initialized = self._failed = self._take_attempted = self._write_attempted = False
        self._write_completed = self._cancel_requested = False
        self._transfer_fact = self._transfer_fact_snapshot = None
        self._payload = self._payload_snapshot = None
        self._timeout = self._timeout_snapshot = None
        control = connection.cancel_owner
        _require(type(service) is BrokerServiceSpine and type(control) is BrokerCancellationOwner)
        BrokerCancellationOwner._guard(control)
        record = control._scope_snapshot[0]
        _require(type(record.resources) is BrokerReaderResources
                 and type(record.resources._input_context) is tuple and type(packet) is bytes)
        row = decode_input_v3(packet)
        _require((row["profile"], row["operation"], row["deadline_ns"])
                 == (record.profile, record.kind, record.deadline_ns))
        self._scope = self._scope_snapshot = _WriterScope(
            service, connection, connection.channel_snapshot, service._registry,
            connection.ticket, record,
            record.resources, control, control._scope_snapshot, control._allocation_snapshot,
            connection.grammar, packet,
            record.resources._input_context, asyncio.current_task())
        self._initialized = True
        BrokerResultWriter._current(self)

    def __repr__(self):
        return "<BrokerResultWriter redacted>"

    def _guard(self):
        s = self._scope
        _require(self._initialized is True and s is self._scope_snapshot
                 and type(s) is _WriterScope and type(s.service) is BrokerServiceSpine
                 and type(s.connection) is _Connection and type(s.channel) is SocketChannel
                 and type(s.registry) is BrokerRegistry
                 and type(s.control) is BrokerCancellationOwner
                 and type(s.resources) is BrokerReaderResources
                 and type(s.grammar) is OperationGrammar
                 and type(s.ticket) is BrokerTicket and type(s.record) is _Record
                 and s.connection.ticket is s.ticket
                 and type(s.control_scope) is tuple and len(s.control_scope) == 10
                 and type(s.task) is _TASK and asyncio.current_task() is s.task
                 and s.service._registry is s.registry
                 and s.connection.channel is s.channel
                 and s.connection.channel_snapshot is s.channel
                 and s.connection.result_writer is self
                 and s.connection.result_writer_snapshot is self
                 and s.channel._result_writer is self and s.channel._result_writer_snapshot is self
                 and s.connection.cancel_owner is s.control and s.connection.grammar is s.grammar
                 and s.control._scope_snapshot is s.control_scope
                 and s.control_scope[0] is s.record and s.record.resources is s.resources
                 and s.record.resources_snapshot is s.resources
                 and s.resources._input_context is s.input_context
                 and s.resources._input_snapshot is s.input_context
                 and self._payload is self._payload_snapshot
                 and (self._payload is None or (type(self._payload) is bytes
                                               and 4 <= len(self._payload) <= OUTPUT_LIMIT))
                 and all(type(v) is bool for v in (self._failed, self._take_attempted,
                                                  self._write_attempted, self._write_completed,
                                                  self._cancel_requested))
                 and self._failed is False
                 and (self._write_attempted is False or self._write_completed is True
                      or s.channel._writing is True)
                 and self._timeout is self._timeout_snapshot
                 and (self._timeout is None or type(self._timeout) is asyncio.Timeout))
        fact = self._transfer_fact
        _require(fact is self._transfer_fact_snapshot
                 and (fact is None or (type(fact) is _CompletedResultTransfer
                      and fact.mint is _TRANSFER_MINT and fact.writer is self and fact.scope is s
                      and type(fact.sha256) is str and len(fact.sha256) == 64
                      and type(fact.length) is int and 4 <= fact.length <= OUTPUT_LIMIT
                      and self._write_completed is True)))
        BrokerCancellationOwner._guard(s.control)
        _require(s.control._go_relay_completed is True
                 and s.control._scope_snapshot is s.control_scope)

    def _current(self):
        BrokerResultWriter._guard(self)
        s = self._scope_snapshot
        BrokerServiceSpine._v2_work_current(s.service, s.control)
        BrokerResultWriter._guard(self)
        _native_io(s.channel)
        BrokerResultWriter._guard(self)

    def retire_from_control(self, control):
        """Freeze-before-cancel hook for this exact service writer task only."""
        s = self._scope_snapshot
        if (type(s) is not _WriterScope or self._scope is not s
                or self._initialized is not True or s.control is not control
                or type(control) is not BrokerCancellationOwner
                or type(s.connection) is not _Connection or type(s.channel) is not SocketChannel
                or s.connection.result_writer_snapshot is not self
                or s.channel._result_writer_snapshot is not self
                or s.control_scope is not control._scope_snapshot
                or type(s.control_scope) is not tuple or len(s.control_scope) != 10
                or type(s.record) is not _Record
                or s.record.cleanup_budget_snapshot is not s.control_scope[3]
                or control._allocation_snapshot is not s.control_allocation
                or type(s.control_allocation) is not _TaskAllocation
                or type(s.control_allocation.task) is not _TASK
                or asyncio.current_task() is not s.control_allocation.task
                or type(s.task) is not _TASK
                or self._write_attempted is not True or self._write_completed is not False
                or self._failed is not False or s.channel._writing is not True
                or self._cancel_requested is not False or _TASK.done(s.task)):
            return
        _, _, end, failed = CancellationBudget.inspect(s.control_scope[3])
        if end is None and failed is not True:
            return  # never cancel normal work before its original cause is frozen
        self._cancel_requested = True
        _TASK.cancel(s.task)  # original retained service task, never a new task/retry

    def poll(self):
        BrokerResultWriter._current(self)
        s = self._scope_snapshot
        result = BrokerRegistry.poll_resource_result(s.registry, s.ticket)
        BrokerResultWriter._current(self)
        _require(type(result) is bool)
        return result

    async def send(self):
        frame = held = chunk = None
        origin = self._scope_snapshot
        try:
            BrokerResultWriter._current(self)
            s = self._scope_snapshot
            _require(self._take_attempted is False and self._write_attempted is False)
            self._take_attempted = True
            held = BrokerRegistry.take_resource_candidate(s.registry, s.ticket)
            self._payload = self._payload_snapshot = held
            BrokerResultWriter._current(self)
            _require(self._payload is held and self._payload_snapshot is held)
            digest = hashlib.sha256(held).hexdigest()
            BrokerResultWriter._current(self)
            _require(self._payload is held and self._payload_snapshot is held)
            header = BrokerHeader(s.record.binding, "RESULT", 1, len(held), 2)
            frame = BrokerFrame(header, held)
            self._write_attempted = True  # no replay even if encoding/grammar fails
            OperationGrammar.observe(s.grammar, frame, sender="broker")
            prefix = encode_header(header)
            _require(s.channel._writing is False)
            s.channel._writing = True
            self._timeout = self._timeout_snapshot = asyncio.timeout_at(
                s.control_scope[2] / 1_000_000_000)
            async with self._timeout:
                BrokerResultWriter._current(self)
                _require(self._payload is held and self._payload_snapshot is held)
                await _LOOP.sock_sendall(
                    asyncio.get_running_loop(), s.channel._socket_snapshot, prefix)
                BrokerResultWriter._current(self)
                _require(self._payload is held and self._payload_snapshot is held)
                offset = 0
                while offset < len(held):
                    BrokerResultWriter._current(self)
                    _require(self._payload is held and self._payload_snapshot is held)
                    chunk = held[offset:offset + 65536]
                    await _LOOP.sock_sendall(
                        asyncio.get_running_loop(), s.channel._socket_snapshot, chunk)
                    BrokerResultWriter._current(self)
                    _require(s.channel._writing is True
                             and self._payload is held and self._payload_snapshot is held)
                    offset += len(chunk)
                    chunk = None
            BrokerResultWriter._current(self)
            _require(self._payload is held and self._payload_snapshot is held)
            self._write_completed = True  # local I/O only; no execution or release proof
            self._transfer_fact = self._transfer_fact_snapshot = _CompletedResultTransfer(
                _TRANSFER_MINT, self, s, digest, len(held))
            return True
        except BaseException:
            self._failed = True
            if type(origin) is _WriterScope and type(origin.control) is BrokerCancellationOwner:
                with suppress(BaseException):
                    BrokerCancellationOwner._local_cause(origin.control)
            return False
        finally:
            frame = held = chunk = None
            self._payload = self._payload_snapshot = None
            s = self._scope_snapshot
            if type(s) is _WriterScope and type(s.channel) is SocketChannel:
                s.channel._writing = False


class _ReaderScope(NamedTuple):
    remote: object
    record: object
    job: object
    buffer: object
    accumulator: bytearray
    context: tuple
    packet: bytes
    channel: object
    cleanup: object
    task: object
    deadline: int
    kind: str
    expected: object
    challenge: str
    epoch: int


class RemoteResultOwner:
    @classmethod
    def retain(cls, remote):
        _require(cls is RemoteResultOwner and type(remote) is RemoteOperationOwner)
        RemoteOperationOwner._retained_local(remote)
        channel = remote._channel_snapshot
        _require(remote._result_owner is None and remote._result_owner_snapshot is None
                 and channel._result_receiver is None)
        owner = RemoteResultOwner.__new__(RemoteResultOwner)
        remote._result_owner = remote._result_owner_snapshot = owner
        channel._result_receiver = channel._result_receiver_snapshot = owner
        RemoteResultOwner.__init__(owner, remote)
        return owner

    def __init__(self, remote):
        self._scope = self._scope_snapshot = None
        self._initialized = self._attempted = self._validated = self._failed = False
        self._token = self._token_snapshot = None
        self._timeout = self._timeout_snapshot = None
        self._header = self._header_snapshot = None
        RemoteOperationOwner._check(remote, RemotePhase.GO_SENT)
        cleanup = remote._cleanup_owner_snapshot
        RemoteCleanupOwner._guard(cleanup)
        job, record = remote._job_origin_snapshot, remote._record_snapshot
        row = decode_input_v3(remote._packet_snapshot)
        custody = remote._output_custody_snapshot
        _require(type(custody) is tuple and len(custody) == 3 and custody[0] is job
                 and type(custody[2]) is bytearray
                 and type(job.output_buffer) is BoundedResultBufferV2
                 and custody[1] is job.output_buffer and job.output_buffer._buffer is custody[2]
                 and job.remote_output_origin is job.output_buffer
                 and type(job.parent_result_context) is tuple
                 and row["operation"] == job.operation
                 and ((job.operation == "METADATA" and row["expected_avatar_sha"] is None)
                      or (job.operation == "AVATAR" and type(row["expected_avatar_sha"]) is str)))
        self._scope = self._scope_snapshot = _ReaderScope(
            remote, record, job, job.output_buffer, custody[2], job.parent_result_context,
            remote._packet_snapshot, remote._channel_snapshot, cleanup,
            cleanup._allocations_snapshot[1].task, remote._end_snapshot, row["operation"],
            row["expected_avatar_sha"], row["challenge"], row["epoch"])
        self._initialized = True
        RemoteResultOwner._current(self)

    def __repr__(self):
        return "<RemoteResultOwner redacted>"

    def _guard(self, *, work=True):
        s = self._scope
        _require(type(s) is _ReaderScope and s is self._scope_snapshot
                 and type(s.remote) is RemoteOperationOwner)
        RemoteOperationOwner._retained_local(s.remote)
        _require(self._initialized is True and type(s) is _ReaderScope
                 and s is self._scope_snapshot and type(s.remote) is RemoteOperationOwner
                 and type(s.job) is _Job and type(s.buffer) is BoundedResultBufferV2
                 and type(s.channel) is SocketChannel and type(s.cleanup) is RemoteCleanupOwner
                 and s.remote._result_owner is self and s.remote._result_owner_snapshot is self
                 and s.channel._result_receiver is self
                 and s.channel._result_receiver_snapshot is self
                 and s.remote._job_origin_snapshot is s.job
                 and s.remote._record_snapshot is s.record and s.remote._packet_snapshot is s.packet
                 and s.job.output_buffer is s.buffer and s.job.remote_output_origin is s.buffer
                 and type(s.accumulator) is bytearray and s.buffer._buffer is s.accumulator
                 and s.remote._output_custody_snapshot[2] is s.accumulator
                 and s.job.parent_result_context is s.context
                 and type(s.job.operation) is str and s.job.operation == s.kind
                 and type(s.job.challenge) is str and s.job.challenge == s.challenge
                 and s.job.lease is s.record.lease
                 and s.job.state is State.RUNNING
                 and all(type(v) is bool for v in (self._attempted, self._validated, self._failed))
                 and self._failed is False and self._token is self._token_snapshot
                 and self._timeout is self._timeout_snapshot
                 and (self._timeout is None or type(self._timeout) is asyncio.Timeout)
                 and self._header is self._header_snapshot)
        RemoteOperationOwner._retained_local(s.remote)
        RemoteCleanupOwner._guard(s.cleanup)
        _require(s.task is s.cleanup._allocations_snapshot[1].task
                 and (work is False or asyncio.current_task() is s.task))
        if self._header is not None:
            _require(type(self._header) is BrokerHeader)
            _row(self._header)
            _require(self._header.kind == "RESULT" and self._header.sequence == 1
                     and self._header.version == 2
                     and self._header.binding == s.remote._binding_snapshot
                     and 4 <= self._header.body_length <= OUTPUT_LIMIT)
        _require(self._validated is True or self._attempted is False or s.channel._reading is True)
        if self._validated:
            _require(type(self._token) is object and s.job.remote_result_token is self._token
                     and type(s.job.result) is tuple and len(s.job.result) == 2
                     and type(s.job.result[0]) is dict and type(s.job.result[1]) is bytes
                     and s.job.remote_phase is RemotePhase.RESULT_VALIDATED)
        else:
            _require(self._token is None and s.job.remote_result_token is None
                     and s.job.result is None and s.job.remote_phase is RemotePhase.GO_SENT)

    def _current(self):
        RemoteResultOwner._guard(self)
        s = self._scope_snapshot
        RemoteOperationOwner._check(s.remote, RemotePhase.GO_SENT)
        RemoteResultOwner._guard(self)
        _native_io(s.channel)
        RemoteResultOwner._guard(self)

    async def _read(self, count):
        RemoteResultOwner._current(self)
        s = self._scope_snapshot
        _require(type(count) is int and 0 < count <= 65536)
        self._timeout = self._timeout_snapshot = asyncio.timeout_at(s.deadline / 1_000_000_000)
        async with self._timeout:
            part = await _LOOP.sock_recv(
                asyncio.get_running_loop(), s.channel._socket_snapshot, count)
        RemoteResultOwner._current(self)
        _require(type(part) is bytes and 0 < len(part) <= count)
        return part

    async def _small(self, count):
        _require(type(count) is int and 0 < count <= 1024)
        data = bytearray()
        while len(data) < count:
            data.extend(await RemoteResultOwner._read(self, count - len(data)))
        return bytes(data)

    def wipe(self):
        s = self._scope_snapshot
        if type(s) is _ReaderScope:
            if type(s.accumulator) is bytearray:
                s.accumulator[:] = b"\x00" * len(s.accumulator)
                s.accumulator.clear()
            if type(s.buffer) is BoundedResultBufferV2:
                s.buffer._done = True
            if type(s.job) is _Job:
                s.job.result = None
                s.job.remote_result_token = None
        self._token = self._token_snapshot = None

    async def receive(self):
        candidate = part = None
        try:
            RemoteResultOwner._current(self)
            s = self._scope_snapshot
            _require(self._attempted is False and s.channel._reading is False)
            self._attempted = True
            s.channel._reading = True
            prefix = await RemoteResultOwner._small(self, 8)
            raw = prefix + await RemoteResultOwner._small(self, header_size(prefix))
            header = decode_header(raw, expected=s.remote._binding_snapshot, expected_version=2)
            _require(header.kind == "RESULT" and header.sequence == 1
                     and 4 <= header.body_length <= OUTPUT_LIMIT)
            self._header = self._header_snapshot = header
            remaining = header.body_length
            while remaining:
                part = await RemoteResultOwner._read(self, min(65536, remaining))
                BoundedResultBufferV2.feed(s.buffer, part)
                remaining -= len(part)
                part = None
                RemoteResultOwner._current(self)
            candidate = BoundedResultBufferV2.finish(s.buffer, s.challenge, s.epoch)
            compare_parent_snapshot(candidate[0], snapshot=s.context[1], parent_home=s.context[0])
            _require(candidate[0]["outcome"] == "OK"
                     and candidate[0]["cleanup"] == {
                         "known_fds_closed": True, "unknown_close": False}
                     and (s.expected is None or candidate[0]["avatar_sha"] == s.expected))
            RemoteResultOwner._current(self)
            # No native callback follows this final original-owner fence.
            s.job.result = candidate
            candidate = None  # transfer, never a second retained payload alias
            self._token = self._token_snapshot = object()
            s.job.remote_result_token = self._token
            s.job.remote_phase = RemotePhase.RESULT_VALIDATED  # still RUNNING, no custody fact
            self._validated = True
            BoundedResultBufferV2.wipe(s.buffer)
            RemoteResultOwner._guard(self)
            return True
        except BaseException:
            self._failed = True
            RemoteResultOwner.wipe(self)
            s = self._scope_snapshot
            if type(s) is _ReaderScope:
                RemoteCleanupOwner.request(s.cleanup)
            return False  # no decoder traceback/body retained by the work Task
        finally:
            candidate = part = None
            s = self._scope_snapshot
            if type(s) is _ReaderScope and type(s.channel) is SocketChannel:
                s.channel._reading = False
