"""Bounded result2 candidates, never publication, native custody or release.

Original service/work tasks only. Normal failures return no payload or exception
traceback retaining a full candidate. Runtime qualification remains separate.
"""
from __future__ import annotations

import asyncio
import errno
import hashlib
import json
import os
import socket
import struct
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
from .presentation_jobs import HEADER_LIMIT, OUTPUT_LIMIT, RemotePhase, State, _Job
from .presentation_output_v2 import (
    BoundedResultBufferV2,
    compare_parent_snapshot,
    validate_header_v2,
)
from .presentation_readiness import SelectorReadiness
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
        origin = None
        writing = False
        try:
            BrokerResultWriter._current(self)
            s = origin = self._scope_snapshot
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
            writing = True
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
            if (writing and type(origin) is _WriterScope
                    and type(origin.channel) is SocketChannel
                    and origin.channel._result_writer_snapshot is self):
                origin.channel._writing = False


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


def _candidate_header_wire(header):
    """Bound mutable-header traversal before validation/JSON; no foreign callbacks."""
    remaining = [HEADER_LIMIT, HEADER_LIMIT]

    def visit(value, depth):
        _require(depth <= 4 and remaining[0] > 0)
        remaining[0] -= 1
        if type(value) is str:
            _require(len(value) <= HEADER_LIMIT)
            try:
                remaining[1] -= len(value.encode("utf-8"))
            except UnicodeError:
                raise AuthorityRefusalError from None
            _require(remaining[1] >= 0)
        elif type(value) is int:
            _require(0 <= value < 1 << 63)
        elif value is None or type(value) is bool:
            pass
        elif type(value) is list:
            _require(len(value) <= remaining[0])
            for item in value:
                visit(item, depth + 1)
        elif type(value) is dict:
            _require(len(value) <= remaining[0] // 2)
            for key, item in value.items():
                _require(type(key) is str)
                visit(key, depth + 1)
                visit(item, depth + 1)
        else:
            _require(False)

    _require(type(header) is dict)
    visit(header, 0)
    validate_header_v2(header)
    raw = json.dumps(header, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                     allow_nan=False).encode("utf-8")
    _require(len(raw) <= HEADER_LIMIT)
    return struct.pack(">I", len(raw)) + raw


class _CandidateFact(NamedTuple):
    owner: object
    scope: _ReaderScope
    token: object
    candidate_id: int
    header_id: int
    body_id: int
    header_wire: bytes
    wire_sha256: str
    wire_length: int

    def __repr__(self):
        return "<CandidateFact metadata-only redacted>"


_SOCKET_RECV = socket.socket.recv
_HASH = type(hashlib.sha256())


class _ResultCursor:
    """Original-task receive progress; no cleanup-mode or resumption permission."""

    def __init__(self, owner, scope):
        self.owner, self.scope = owner, scope
        self.outer = self.outer_origin = bytearray()
        self.digest = self.digest_origin = hashlib.sha256()
        self.pending = None
        self.received = self.body_received = self.body_committed = 0
        self.outer_committed = self.outer_target = 0
        self.waiter = None
        self.recv_intent = self.commit_intent = self.io_unknown = False

    def __repr__(self):
        return "<ResultCursor payload-redacted>"

    def guard(self, owner):
        _require(type(self) is _ResultCursor and self.owner is owner
                 and owner._cursor is self and owner._cursor_snapshot is self
                 and owner._cursor_origin is self and self.scope is owner._scope_snapshot
                 and type(self.outer) is bytearray and self.outer is self.outer_origin
                 and len(self.outer) <= 1032
                 and type(self.digest) is _HASH and self.digest is self.digest_origin
                 and (self.pending is None or (type(self.pending) is bytes
                                              and 0 < len(self.pending) <= 65536))
                 and all(type(v) is int and 0 <= v <= OUTPUT_LIMIT + 1032
                         for v in (self.received, self.body_received, self.body_committed,
                                   self.outer_committed, self.outer_target))
                 and self.outer_committed <= self.outer_target <= 1032
                 and self.received == (self.outer_committed + self.body_committed
                                      + (0 if self.pending is None else len(self.pending)))
                 and len(self.outer) == self.outer_committed
                 and self.body_received == (self.body_committed +
                     (len(self.pending) if self.pending is not None
                      and owner._header_snapshot is not None else 0))
                 and self.body_committed <= self.body_received
                 and all(type(v) is bool for v in (
                     self.recv_intent, self.commit_intent, self.io_unknown))
                 and self.io_unknown is False
                 and (self.waiter is None or type(self.waiter) is SelectorReadiness))

    def wipe(self):
        # This original custody cell is independently retained; never follow a
        # substituted current cursor or mutable bytearray reference on refusal.
        self.pending = None
        if type(self.outer_origin) is bytearray:
            self.outer_origin[:] = b"\x00" * len(self.outer_origin)
            self.outer_origin.clear()


class RemoteResultOwner:
    @classmethod
    def retain(cls, remote):
        _require(cls is RemoteResultOwner and type(remote) is RemoteOperationOwner)
        RemoteOperationOwner._retained_local(remote)
        channel = remote._channel_snapshot
        _require(remote._result_owner is None and remote._result_owner_snapshot is None
                 and channel._result_receiver is None)
        job = remote._job_origin_snapshot
        _require(type(job) is _Job and job._remote_candidate_custody_origin is None
                 and job._remote_candidate_custody_snapshot is None)
        owner = RemoteResultOwner.__new__(RemoteResultOwner)
        owner._candidate_job_origin = job
        owner._failure_cleanup_origin = remote._cleanup_owner_snapshot
        owner._io_channel_origin = channel
        owner._wipe_custody_origin = remote._output_custody_snapshot
        job._remote_candidate_custody_origin = job._remote_candidate_custody_snapshot = (
            owner, job)  # metadata only, before init effects
        remote._result_owner = remote._result_owner_snapshot = owner
        channel._result_receiver = channel._result_receiver_snapshot = owner
        RemoteResultOwner.__init__(owner, remote)
        return owner

    def __init__(self, remote):
        self._scope = self._scope_snapshot = None
        self._initialized = self._attempted = self._validated = self._failed = False
        self._token = self._token_snapshot = None
        self._candidate = self._candidate_snapshot = None
        self._candidate_fact = self._candidate_fact_snapshot = None
        self._discarded = False
        self._timeout = self._timeout_snapshot = None
        self._header = self._header_snapshot = None
        self._cursor = self._cursor_snapshot = self._cursor_origin = None
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
        self._cursor = self._cursor_snapshot = self._cursor_origin = _ResultCursor(
            self, self._scope_snapshot)
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
                 and self._failed is False and self._discarded is False
                 and self._token is self._token_snapshot
                 and self._candidate is self._candidate_snapshot
                 and self._candidate_fact is self._candidate_fact_snapshot
                 and type(s.job._remote_candidate_custody_origin) is tuple
                 and len(s.job._remote_candidate_custody_origin) == 2
                 and (s.job._remote_candidate_custody_origin
                      is s.job._remote_candidate_custody_snapshot)
                 and self._candidate_job_origin is s.job
                 and self._failure_cleanup_origin is s.cleanup
                 and self._io_channel_origin is s.channel
                 and self._wipe_custody_origin is s.remote._output_custody_snapshot
                 and s.job._remote_candidate_custody_origin[0] is self
                 and s.job._remote_candidate_custody_origin[1] is s.job
                 and self._timeout is self._timeout_snapshot
                 and (self._timeout is None or type(self._timeout) is asyncio.Timeout)
                 and self._header is self._header_snapshot)
        _require(type(self._cursor) is _ResultCursor)
        _ResultCursor.guard(self._cursor, self)
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
            fact, candidate = self._candidate_fact_snapshot, self._candidate_snapshot
            _require(type(fact) is _CandidateFact and fact.owner is self and fact.scope is s
                     and type(self._token) is object and fact.token is self._token
                     and s.job.remote_result_token is self._token
                     and type(candidate) is tuple and len(candidate) == 2
                     and s.job.result is candidate
                     and type(candidate[0]) is dict and type(candidate[1]) is bytes
                     and all(type(v) is int for v in (
                         fact.candidate_id, fact.header_id, fact.body_id))
                     and id(candidate) == fact.candidate_id
                     and id(candidate[0]) == fact.header_id and id(candidate[1]) == fact.body_id
                     and type(fact.header_wire) is bytes
                     and len(fact.header_wire) <= HEADER_LIMIT + 4
                     and type(fact.wire_sha256) is str and len(fact.wire_sha256) == 64
                     and type(fact.wire_length) is int
                     and 4 <= fact.wire_length <= OUTPUT_LIMIT
                     and s.job.remote_phase is RemotePhase.RESULT_VALIDATED)
            _require(_candidate_header_wire(candidate[0]) == fact.header_wire)
        else:
            _require(self._token is None and self._candidate is None
                     and self._candidate_fact is None and s.job.remote_result_token is None
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
        s, cursor = self._scope_snapshot, self._cursor_origin
        _require(type(count) is int and 0 < count <= 65536
                 and cursor.pending is None and cursor.recv_intent is False
                 and cursor.commit_intent is False)
        while True:
            RemoteResultOwner._current(self)
            # Retain allocation BEFORE initialization/registration effects.
            waiter = SelectorReadiness.__new__(SelectorReadiness)
            cursor.waiter = waiter
            try:
                SelectorReadiness.__init__(waiter, s.channel._socket_snapshot)
                await SelectorReadiness.wait(waiter, s.deadline)
            except BaseException:
                if (getattr(waiter, "_initialized", False) is not True
                        or waiter._unknown is not False or type(waiter._attempted) is not bool
                        or (waiter._attempted is True and waiter._retired is not True)):
                    cursor.io_unknown = True
                raise
            if (cursor.waiter is not waiter or waiter._initialized is not True
                    or waiter._attempted is not True or waiter._retired is not True
                    or waiter._unknown is not False):
                cursor.io_unknown = True
                _require(False)
            RemoteResultOwner._current(self)
            received, body_received = cursor.received, cursor.body_received
            held_header = self._header_snapshot
            cursor.recv_intent = True
            try:
                part = _SOCKET_RECV(s.channel._socket_snapshot, count)
            except BlockingIOError as error:
                if (type(error) is not BlockingIOError or type(error.errno) is not int
                        or error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK)):
                    raise
                cursor.recv_intent = False  # exact zero-byte EAGAIN; same deadline
                continue
            # No guard, callback or await may interpose syscall and retained commit.
            cursor.pending = part
            _require(type(part) is bytes)  # never invoke a foreign length/coercion
            prior_received, prior_body = cursor.received, cursor.body_received
            cursor.received = received + len(part)
            cursor.body_received = body_received + (len(part) if held_header is not None else 0)
            cursor.recv_intent = False
            if (type(prior_received) is not int or prior_received != received
                    or type(prior_body) is not int or prior_body != body_received
                    or self._header_snapshot is not held_header):
                cursor.io_unknown = True
                _require(False)
            _require(0 < len(part) <= count)
            RemoteResultOwner._current(self)
            return part

    async def _small(self, count):
        RemoteResultOwner._current(self)
        cursor = self._cursor_origin
        _require(type(count) is int and 0 < count <= 1024)
        start, target = len(cursor.outer), len(cursor.outer) + count
        _require(target <= 1032)
        cursor.outer_target = target
        while len(cursor.outer) < target:
            part = await RemoteResultOwner._read(self, target - len(cursor.outer))
            cursor.commit_intent = True
            cursor.outer.extend(part)
            cursor.outer_committed += len(part)
            cursor.pending = None
            cursor.commit_intent = False
        return bytes(cursor.outer[start:target])

    def discard(self):
        """Drop only this owner's references; no native permission or foreign traversal."""
        _require(type(self) is RemoteResultOwner)
        self._candidate = self._candidate_snapshot = None
        self._candidate_fact = self._candidate_fact_snapshot = None
        self._token = self._token_snapshot = None
        self._discarded = True

    def wipe(self):
        # Separately retained original custody; never follow a substituted reader scope.
        origin = self._wipe_custody_origin
        if (type(origin) is tuple and len(origin) == 3
                and type(origin[0]) is _Job and origin[0] is self._candidate_job_origin
                and type(origin[1]) is BoundedResultBufferV2 and type(origin[2]) is bytearray):
            origin[2][:] = b"\x00" * len(origin[2])
            origin[2].clear()
            origin[1]._done = True
            origin[0].result = None
            origin[0].remote_result_token = None
        cursor = self._cursor_origin
        if type(cursor) is _ResultCursor and cursor.owner is self:
            _ResultCursor.wipe(cursor)
        RemoteResultOwner.discard(self)

    async def receive(self):
        candidate = part = digest = None
        cleanup, channel = self._failure_cleanup_origin, self._io_channel_origin
        reading = False
        try:
            RemoteResultOwner._current(self)
            s = self._scope_snapshot
            _require(self._attempted is False and s.channel._reading is False)
            self._attempted = True
            s.channel._reading = True
            reading = True
            prefix = await RemoteResultOwner._small(self, 8)
            raw = prefix + await RemoteResultOwner._small(self, header_size(prefix))
            header = decode_header(raw, expected=s.remote._binding_snapshot, expected_version=2)
            _require(header.kind == "RESULT" and header.sequence == 1
                     and 4 <= header.body_length <= OUTPUT_LIMIT)
            self._header = self._header_snapshot = header
            remaining = header.body_length
            cursor = self._cursor_origin
            digest = cursor.digest_origin
            while remaining:
                part = await RemoteResultOwner._read(self, min(65536, remaining))
                cursor.commit_intent = True
                BoundedResultBufferV2.feed(s.buffer, part)
                digest.update(part)
                cursor.body_committed += len(part)
                cursor.pending = None
                cursor.commit_intent = False
                remaining -= len(part)
                part = None
                RemoteResultOwner._current(self)
            candidate = BoundedResultBufferV2.finish(s.buffer, s.challenge, s.epoch)
            compare_parent_snapshot(candidate[0], snapshot=s.context[1], parent_home=s.context[0])
            _require(candidate[0]["outcome"] == "OK"
                     and candidate[0]["cleanup"] == {
                         "known_fds_closed": True, "unknown_close": False}
                     and (s.expected is None or candidate[0]["avatar_sha"] == s.expected))
            header_wire = _candidate_header_wire(candidate[0])
            wire_sha = digest.hexdigest()
            RemoteResultOwner._current(self)
            # One original immutable tuple/body, in the clearable receiver ownership cell.
            self._candidate = self._candidate_snapshot = candidate
            s.job.result = candidate
            candidate = None
            self._token = self._token_snapshot = object()
            self._candidate_fact = self._candidate_fact_snapshot = _CandidateFact(
                self, s, self._token, id(self._candidate), id(self._candidate[0]),
                id(self._candidate[1]), header_wire, wire_sha, header.body_length)
            s.job.remote_result_token = self._token
            s.job.remote_phase = RemotePhase.RESULT_VALIDATED  # still RUNNING, no custody fact
            self._validated = True
            BoundedResultBufferV2.wipe(s.buffer)
            RemoteResultOwner._guard(self)
            return True
        except BaseException:
            cursor = self._cursor_origin
            if type(cursor) is _ResultCursor and (cursor.recv_intent or cursor.commit_intent):
                cursor.io_unknown = True
            self._failed = True
            RemoteResultOwner.wipe(self)
            if (type(cleanup) is RemoteCleanupOwner and type(channel) is SocketChannel
                    and type(cleanup._refs_snapshot) is tuple and len(cleanup._refs_snapshot) == 12
                    and cleanup._refs_snapshot[3] is channel
                    and type(cleanup._remote_snapshot) is RemoteOperationOwner
                    and (cleanup._remote_snapshot._job_origin_snapshot
                         is self._candidate_job_origin)):
                RemoteCleanupOwner.request(cleanup)
            return False  # no decoder traceback/body retained by the work Task
        finally:
            candidate = part = digest = None
            if (reading and type(channel) is SocketChannel
                    and channel._result_receiver_snapshot is self
                    and type(self._cursor_origin) is _ResultCursor
                    and self._cursor_origin.io_unknown is False):
                channel._reading = False
