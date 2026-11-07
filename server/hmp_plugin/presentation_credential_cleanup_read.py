"""One original-task read and one-shot same-parser consumption.

A typed progress receipt is not frame credit. No new reader/interest, signing or
release. Original work exit retires payload and preserves unknown protocol debt.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import stat
import threading
from typing import NamedTuple

from .presentation_broker_codec import HEADER_LIMIT, TERMINAL_LIMIT
from .presentation_cleanup_reader import CleanupReadGate
from .presentation_credential_cleanup_notice import (
    SignedCleanupReader,
    SignedReadNotice,
    SignedStoppedCursor,
)
from .presentation_credential_cleanup_reservation import inspect_signed_reservation
from .presentation_credential_codec import JSON_LIMIT, RECORD_LIMIT, payload_size
from .presentation_credential_phase import ConsistentCommitment
from .presentation_credential_stream import (
    _HASH_TYPE,
    CHUNK_LIMIT,
    CommittedFrameDigest,
    SignedCleanupAuthPrefix,
    SignedResultDiscard,
)
from .presentation_jobs import OUTPUT_LIMIT, FrameError
from .presentation_readiness import _BACKEND, SelectorReadiness
from .presentation_readiness import _Scope as _ReadinessScope

_RECV = socket.socket.recv
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_FSTAT = os.fstat
_GET_BLOCKING = os.get_blocking
_GET_INHERITABLE = os.get_inheritable
_DONTWAIT_RAW = getattr(socket, "MSG_DONTWAIT", None)
_DONTWAIT = (int.__int__(_DONTWAIT_RAW)
             if type(_DONTWAIT_RAW) in (int, socket.MsgFlag) else None)
_BACKEND_FILENO = None if _BACKEND is None else _BACKEND.fileno
_MINT = object()
_WIRE_LIMIT = OUTPUT_LIMIT + TERMINAL_LIMIT + 2 * (RECORD_LIMIT + 8 + HEADER_LIMIT)
_HASH_COPY = _HASH_TYPE.copy
_HASH_UPDATE = _HASH_TYPE.update
_HASH_HEX = _HASH_TYPE.hexdigest


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_CLEANUP_READ_REFUSED")


class _ReadScope(NamedTuple):
    idle: SignedCleanupReader
    idle_scope: tuple
    cursor: SignedStoppedCursor
    notice: SignedReadNotice
    sock: socket.socket

    def __repr__(self):
        return "<NativeCleanupReadScope original-bound-reader redacted>"


class _ReadReceipt(NamedTuple):
    mint: object
    owner: object
    scope: _ReadScope
    count: int

    def __repr__(self):
        return "<NativeCleanupReadReceipt pending-only no-frame-or-release-credit>"


class _ParserSeal(NamedTuple):
    parser: object
    buffer: bytearray
    value: bytes
    pins: tuple
    expected: tuple
    context: tuple
    target: int
    header_done: object
    binding: object
    stream: object
    hasher: object
    received: int
    digest: object

    def __repr__(self):
        return "<ParserSeal original-parser progress redacted>"


class _ConsumeAttempt(NamedTuple):
    owner: object
    scope: _ReadScope

    def __repr__(self):
        return "<ConsumeAttempt original-reader one-shot>"


class _ConsumedReceipt(NamedTuple):
    mint: object
    owner: object
    scope: _ReadScope
    count: int
    before: _ParserSeal
    after: _ParserSeal

    def __repr__(self):
        return "<ConsumedReceipt parser-progress-only no-frame-or-release-credit>"


class _ProgressLedger(NamedTuple):
    owner: object
    ordinal: int
    received: int
    committed: int
    seal: _ParserSeal

    def __repr__(self):
        return "<ProgressLedger counts-and-parser-only>"


class _NextScope(NamedTuple):
    owner: object
    scope: _ReadScope
    before: _ProgressLedger
    ordinal: int

    def __repr__(self):
        return "<NextScope same-original-reader>"


class _NextReceipt(NamedTuple):
    owner: object
    ordinal: int
    count: int
    total_received: int
    total_committed: int
    after: _ParserSeal

    def __repr__(self):
        return "<NextReceipt parser-progress-only no-frame-or-release>"


class _NextRead:
    # Step DATA, never a replacement reader, task, selector or socket owner.
    def __repr__(self):
        return "<NextRead bounded-step payload-redacted>"


class _AuthScope(NamedTuple):
    owner: object
    scope: _ReadScope
    before: _ParserSeal
    progress: object
    step: object
    ledger: object
    receipt: object
    count: int
    total_received: int

    def __repr__(self):
        return "<AuthScope original-completed-record redacted>"


class _AuthReceipt(NamedTuple):
    owner: object
    scope: _AuthScope
    checked: ConsistentCommitment
    values: tuple
    count: int
    total_received: int

    @property
    def phase(self):
        return self.values[3]

    def __repr__(self):
        return "<AuthReceipt authenticated-phase-DATA no-transition-permission>"


class _AuthAttempt:
    def __repr__(self):
        return "<AuthAttempt original-parser one-shot redacted>"


def owned_native_read(notice):
    """Independent allocation discovery only; never currentness or IO admission."""
    _require(type(notice) is SignedReadNotice)
    cell = notice._cursor_allocation_origin
    if cell is None:
        return None
    _require(type(cell) is tuple and len(cell) == 2 and cell[0] is notice
             and type(cell[1]) is SignedStoppedCursor)
    cursor = cell[1]
    cell = cursor._reader_allocation_origin
    if cell is None:
        return None
    _require(type(cell) is tuple and len(cell) == 2 and cell[0] is cursor
             and type(cell[1]) is SignedCleanupReader)
    idle = cell[1]
    cell = idle._native_read_allocation_origin
    if cell is None:
        return None
    _require(type(cell) is tuple and len(cell) == 2 and cell[0] is idle
             and type(cell[1]) is NativeCleanupRead)
    return cell[1]


def require_unadvanced_notice(notice):
    owner = owned_native_read(notice)
    if owner is not None:
        _require(type(owner._attempted) is bool and owner._attempted is False
                 and owner._auth_allocation_origin is None)


def retire_pending_on_work_exit(gate, cleanup):
    """Memory retirement on the actual original task, without native authority."""
    _require(type(gate) is CleanupReadGate)
    cell = gate._signed_notice_allocation_origin
    if cell is None:
        return
    _require(type(cell) is tuple and len(cell) == 2 and cell[0] is gate
             and type(cell[1]) is SignedReadNotice)
    owner = owned_native_read(cell[1])
    if owner is not None:
        NativeCleanupRead._retire_on_work_exit(owner, cleanup)


class NativeCleanupRead:
    @classmethod
    def retain(cls, idle):
        _require(cls is NativeCleanupRead and type(idle) is SignedCleanupReader)
        scope = SignedCleanupReader._metadata(idle)
        cursor = idle._cursor_origin
        notice = cursor._notice_origin
        reservation = SignedReadNotice._actor(notice)
        _require(idle._admitted is True and idle._native_read is None
                 and idle._native_read_origin is None
                 and idle._native_read_allocation_origin is None)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_origin = _ReadScope(
            idle, scope, cursor, notice, reservation.capture.scope.write_scope.sock)
        owner._scope_allocation_origin = (owner, owner._scope_origin)
        owner._initialized = owner._attempted = owner._inflight = owner._reading_owned = False
        owner._failed = owner._unknown = owner._complete = owner._returned = False
        owner._count_known = False
        owner._consume_attempted = owner._consume_returned = owner._consume_complete = False
        owner._consume_allocation_origin = None
        owner._consume_attempt_allocation_origin = None
        owner._next_read = owner._next_read_origin = owner._next_read_allocation_origin = None
        owner._ledger = owner._ledger_origin = owner._ledger_allocation_origin = None
        owner._auth = owner._auth_origin = owner._auth_allocation_origin = None
        owner._frame = owner._frame_origin = owner._frame_allocation_origin = None
        owner._body_finish = owner._body_finish_origin = owner._body_finish_allocation = None
        owner._terminal = owner._terminal_origin = owner._terminal_allocation = None
        owner._payload_seed = owner._payload_seed_origin = owner._payload_seed_cell = None
        owner._terminal_frame = owner._terminal_frame_origin = owner._terminal_frame_allocation = (
            None
        )
        owner._progress = owner._progress_origin = owner._progress_allocation_origin = None
        owner._received = owner._received_origin = 0
        owner._native_count_allocation_origin = None
        owner._pending = owner._pending_origin = owner._pending_allocation_origin = None
        owner._fact = owner._fact_origin = owner._fact_allocation_origin = None
        idle._native_read = idle._native_read_origin = owner
        idle._native_read_allocation_origin = (idle, owner)
        failed = False
        try:
            _require(SignedCleanupReader.current_idle(idle) is idle._fact_origin)
            NativeCleanupRead._current_work(owner)
            owner._initialized = True
            if reservation.capture.body is not None:
                from .presentation_credential_cleanup_payload import initialize
                initialize(owner)
            return owner
        except BaseException:
            failed = owner._failed = owner._unknown = True
            notice._failed = notice._unknown = True
            reservation.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_READ_ACQUISITION_UNKNOWN") from None

    def __repr__(self):
        return "<NativeCleanupRead one-bounded-original-read payload-redacted>"

    def _origin(self):
        _require(type(self) is NativeCleanupRead
                 and type(self._scope) is _ReadScope and self._scope is self._scope_origin
                 and type(self._scope_allocation_origin) is tuple
                 and len(self._scope_allocation_origin) == 2
                 and self._scope_allocation_origin[0] is self
                 and self._scope_allocation_origin[1] is self._scope)
        s = self._scope_origin
        _require(type(s.idle) is SignedCleanupReader
                 and s.idle._native_read is self and s.idle._native_read_origin is self
                 and type(s.idle._native_read_allocation_origin) is tuple
                 and len(s.idle._native_read_allocation_origin) == 2
                 and s.idle._native_read_allocation_origin[0] is s.idle
                 and s.idle._native_read_allocation_origin[1] is self
                 and type(s.cursor) is SignedStoppedCursor and s.idle._cursor_origin is s.cursor
                 and type(s.notice) is SignedReadNotice and s.cursor._notice_origin is s.notice
                 and SignedCleanupReader._metadata(s.idle) is s.idle_scope)
        r = s.idle_scope[0].reservation
        inspect_signed_reservation(r, s.notice._gate)
        _require(type(s.sock) is socket.socket and s.sock is r.wait.scope.sock
                 and s.sock is r.capture.scope.write_scope.sock
                 and s.sock is r.capture.channel._socket)
        return s

    def _pending_attempt_metadata(self, scope):
        cell = self._consume_attempt_allocation_origin
        _require(type(self._consume_attempted) is bool)
        if self._consume_attempted is False:
            _require(cell is None)
        else:
            _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self
                     and type(cell[1]) is _ConsumeAttempt and cell[1].owner is self
                     and cell[1].scope is scope and self._consume_returned is False
                     and self._consume_complete is False)

    def _metadata(self):
        s = NativeCleanupRead._origin(self)
        NativeCleanupRead._pending_attempt_metadata(self, s)
        _require(self._consume_allocation_origin is None
                 and self._failed is False and self._unknown is False
                 and all(type(v) is bool for v in (
                     self._initialized, self._attempted, self._inflight, self._reading_owned,
                     self._complete, self._returned, self._count_known))
                 and type(self._received) is int and self._received is self._received_origin
                 and 0 <= self._received <= s.idle_scope[2]
                 and self._pending is self._pending_origin and self._fact is self._fact_origin)
        native_count = self._native_count_allocation_origin
        if native_count is None:
            _require(self._count_known is False and self._received == 0)
        else:
            _require(type(native_count) is tuple and len(native_count) == 2
                     and native_count[0] is self and type(native_count[1]) is int
                     and native_count[1] is self._received_origin and self._count_known is True)
        cell = self._pending_allocation_origin
        if cell is None:
            _require(self._pending_origin is None and self._received == 0)
        else:
            _require(type(cell) is tuple and len(cell) == 3 and cell[0] is self
                     and type(cell[1]) is bytes and cell[1] is self._pending_origin
                     and type(cell[2]) is int and cell[2] == self._received == len(cell[1])
                     and self._returned is True and self._count_known is True)
        fact, allocation = self._fact_origin, self._fact_allocation_origin
        if fact is None:
            _require(allocation is None and self._complete is False)
        else:
            _require(type(fact) is _ReadReceipt and fact.mint is _MINT and fact.owner is self
                     and fact.scope is s and type(fact.count) is int
                     and fact.count == self._received
                     and type(allocation) is tuple and len(allocation) == 2
                     and allocation[0] is self and allocation[1] is fact)
        if self._complete is True:
            _require(self._initialized is True and self._attempted is True
                     and self._returned is True and self._count_known is True
                     and self._inflight is False and self._reading_owned is False
                     and fact is not None and self._received > 0)
        _require(SignedStoppedCursor._metadata(s.cursor) is s.idle_scope[0])
        actual, _, end = SignedReadNotice._ready_metadata(s.notice)
        _require(actual is s.idle_scope[0] and end <= s.idle_scope[4])
        return s

    def _current_work(self):
        s = NativeCleanupRead._metadata(self)
        _require(self._inflight is False and self._reading_owned is False)
        _require(SignedReadNotice._current(s.notice)[0] is s.idle_scope[0].stop)
        _require(NativeCleanupRead._metadata(self) is s)
        if self._returned is True:
            NativeCleanupRead._final_socket_fence(self, s)
            SignedReadNotice._role_seal(s.notice)
            _require(SignedReadNotice._actor(s.notice) is s.idle_scope[0].reservation
                     and NativeCleanupRead._metadata(self) is s)
        return s

    @staticmethod
    def _receive(sock, count):
        return _RECV(sock, count, _DONTWAIT)

    def _final_socket_fence(self, scope):
        r = scope.idle_scope[0].reservation
        # Fixed C probes AFTER the final cleanup-clock callback. Do not redispatch
        # through socket instance methods or another clock/peer validator.
        held = r.wait.scope
        _require(type(held) is _ReadinessScope
                 and held is r.wait.owner._origin_scope
                 and held is r.wait.owner._scope_snapshot
                 and _BACKEND is not None and type(held.backend) is _BACKEND
                 and type(held.backend_fd) is int
                 and type(held.backend_identity) is tuple and len(held.backend_identity) == 3
                 and all(type(v) is int for v in held.backend_identity)
                 and _BACKEND_FILENO(held.backend) == held.backend_fd)
        backend = _FSTAT(held.backend_fd)
        _require((backend.st_dev, backend.st_ino, stat.S_IFMT(backend.st_mode))
                 == held.backend_identity)
        _require(type(held.fd) is int and type(held.identity) is tuple
                 and len(held.identity) == 3 and all(type(v) is int for v in held.identity)
                 and held.sock is scope.sock and _FILENO(scope.sock) == held.fd)
        row = _FSTAT(held.fd)
        _require((row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode)) == held.identity
                 and stat.S_ISSOCK(row.st_mode)
                 and _GET_BLOCKING(held.fd) is False
                 and _GET_INHERITABLE(held.fd) is False)
        timeout = _TIMEOUT(scope.sock)  # fixed C descriptor, no instance dispatch
        _require(type(timeout) is float and timeout == 0.0)

    def _dispatch_metadata(self, scope):
        # Pure original joins after FD/mode checks; no clock/peer callback here.
        _require(NativeCleanupRead._metadata(self) is scope
                 and self._inflight is False and self._reading_owned is False
                 and self._initialized is True and self._attempted is True
                 and self._failed is False and self._unknown is False
                 and self._returned is False and self._count_known is False
                 and type(self._received) is int and self._received is self._received_origin
                 and self._received == 0 and self._pending_allocation_origin is None)
        r = SignedReadNotice._actor(scope.notice)
        _require(r.capture.channel._reading is False and r.capture.channel._writing is False)
        SignedReadNotice._role_seal(scope.notice)
        from .presentation_cancel_budget import CancellationBudget
        _, _, end, failed = CancellationBudget.inspect(r.budget)
        _require(type(end) is int and 0 < end <= scope.idle_scope[4] and failed is False)
        cursor, parser = scope.cursor, scope.idle_scope[1]
        state = cursor._parser_state_origin
        if r.capture.body is None:
            _require(type(state) is tuple and len(state) == 4
                     and type(state[0]) is bytearray and type(state[1]) is bytes
                     and type(state[2]) is int and type(state[3]) is bool
                     and parser._buffer is state[0] and parser._buffer_origin is state[0]
                     and bytes(state[0]) == state[1]
                     and parser._target is state[2] and parser._target_origin is state[2]
                     and parser._header_done is state[3]
                     and parser._header_done_origin is state[3]
                     and parser._failed is False and parser._finished is False
                     and state[2] - len(state[0]) == scope.idle_scope[2])
        else:
            body = r.capture.body
            _require(type(state) is tuple and len(state) == 5
                     and parser._stream is body.allocation[1]
                     and parser._stream_origin is body.allocation[1]
                     and state[0] is body.allocation[1]
                     and state[0]._received is body.committed
                     and state[0]._received_snapshot is body.committed
                     and type(state[0]._body_length) is int
                     and min(CHUNK_LIMIT, state[0]._body_length - body.committed)
                     == scope.idle_scope[2])

    def _clear_owned_reading(self, scope):
        # Pure syscall-return retirement, not a new FD/currentness permission.
        cell = self._scope_allocation_origin
        read_cell = scope.idle._native_read_allocation_origin
        if (type(self) is NativeCleanupRead and type(cell) is tuple and len(cell) == 2
                and cell[0] is self and cell[1] is scope
                and self._scope is scope and self._scope_origin is scope
                and self._reading_owned is True and self._inflight is True
                and type(read_cell) is tuple and len(read_cell) == 2
                and read_cell[0] is scope.idle and read_cell[1] is self):
            channel = scope.idle_scope[0].reservation.capture.channel
            if channel._socket is scope.sock and channel._reading is True:
                channel._reading = False
                self._reading_owned = self._inflight = False
                return True
        return False

    def run_once(self):
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._actor(s.notice)
        _require(self._initialized is True and self._attempted is False
                 and self._auth_allocation_origin is None)
        self._attempted = True
        chunk = None
        failed = False
        try:
            if self._payload_seed_origin is not None:
                from .presentation_credential_cleanup_payload import current_seed
                current_seed(self)
            _require(NativeCleanupRead._current_work(self) is s)
            count = s.idle_scope[2]
            _require(type(count) is int and 0 < count <= CHUNK_LIMIT
                     and _RECV is socket.socket.recv)
            channel = r.capture.channel
            _require(channel._reading is False and channel._writing is False
                     and type(_DONTWAIT) is int and _DONTWAIT > 0)
            NativeCleanupRead._final_socket_fence(self, s)
            NativeCleanupRead._dispatch_metadata(self, s)
            self._reading_owned = self._inflight = True
            channel._reading = True
            chunk = NativeCleanupRead._receive(s.sock, count)
            self._returned = True
            if type(chunk) is bytes:
                self._received = self._received_origin = len(chunk)
                self._native_count_allocation_origin = (self, self._received)
                self._count_known = True
                self._pending = self._pending_origin = chunk
                self._pending_allocation_origin = (self, chunk, self._received)
            _require(NativeCleanupRead._clear_owned_reading(self, s))
            _require(type(chunk) is bytes and 0 < self._received <= count)
            # Native bytes are recorded BEFORE any mutable metadata/currentness
            # callback. The parser/digest and image accumulator remain untouched.
            _require(NativeCleanupRead._current_work(self) is s)
            fact = _ReadReceipt(_MINT, self, s, self._received)
            self._fact = self._fact_origin = fact
            self._fact_allocation_origin = (self, fact)
            _require(NativeCleanupRead._current_work(self) is s)
            self._complete = True
            return fact
        except BaseException:
            failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
        finally:
            chunk = None
            if self._reading_owned is True:
                NativeCleanupRead._clear_owned_reading(self, s)
            if failed:
                NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_READ_UNKNOWN") from None

    def current_pending(self):
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._actor(s.notice)
        _require(self._complete is True and self._consume_attempted is False)
        failed = False
        try:
            NativeCleanupRead._current_work(self)
            return self._fact_origin
        except BaseException:
            failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
            NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_PENDING_UNKNOWN") from None

    def current_for_cleanup(self):
        _require(type(self) is NativeCleanupRead and type(self._consume_attempted) is bool)
        if self._consume_attempted or self._auth_allocation_origin is not None:
            return NativeCleanupRead.current_progress_for_cleanup(self)
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._cleanup_actor(s.notice)
        _require(self._complete is True)
        failed = False
        try:
            NativeCleanupRead._metadata(self)
            SelectorReadiness._native(r.wait.owner, actor=False)
            _require(SelectorReadiness._slots(r.wait.owner)[0] is None)
            SignedReadNotice._role_seal(s.notice)
            from .presentation_remote_cleanup import RemoteCleanupOwner
            _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
            NativeCleanupRead._final_socket_fence(self, s)
            SignedReadNotice._role_seal(s.notice)
            _require(SignedReadNotice._cleanup_actor(s.notice) is r)
            _require(NativeCleanupRead._metadata(self) is s)
            return self._fact_origin
        except BaseException:
            failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
            NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_PENDING_OBSERVER_UNKNOWN") from None

    @staticmethod
    def _parser_seal(parser):
        if type(parser) is SignedCleanupAuthPrefix:
            SignedCleanupAuthPrefix._guard(parser)
            return _ParserSeal(parser, parser._buffer_origin, bytes(parser._buffer_origin),
                parser._pins_origin, parser._expected_origin, parser._context_origin,
                parser._target_origin, parser._header_done_origin, None, None, None, 0, None)
        _require(type(parser) is SignedResultDiscard)
        SignedResultDiscard._guard(parser)
        _require(parser._stage == "body" and type(parser._stream_origin) is CommittedFrameDigest)
        stream = parser._stream_origin
        CommittedFrameDigest._guard(stream)
        _require(type(stream._hasher_origin) is _HASH_TYPE)
        return _ParserSeal(parser, parser._buffer_origin, bytes(parser._buffer_origin),
            parser._pins_origin, parser._expected_origin, parser._context,
            parser._target_origin, None, parser._binding_origin, stream,
            stream._hasher_origin, stream._received, _HASH_HEX(stream._hasher_origin))

    @staticmethod
    def _same_parser(actual, expected):
        _require(type(actual) is _ParserSeal and type(expected) is _ParserSeal
                 and actual.parser is expected.parser and actual.buffer is expected.buffer
                 and actual.pins is expected.pins and actual.expected is expected.expected
                 and actual.context is expected.context and actual.binding is expected.binding
                 and actual.stream is expected.stream and actual.hasher is expected.hasher
                 and type(actual.value) is bytes and type(expected.value) is bytes
                 and actual.value == expected.value
                 and type(actual.target) is int and type(expected.target) is int
                 and actual.target == expected.target
                 and actual.header_done is expected.header_done
                 and type(actual.received) is int and type(expected.received) is int
                 and actual.received == expected.received
                 and type(actual.digest) is type(expected.digest)
                 and actual.digest == expected.digest)

    def _consumption_metadata(self):
        s = NativeCleanupRead._origin(self)
        attempt = self._consume_attempt_allocation_origin
        _require(type(attempt) is tuple and len(attempt) == 2 and attempt[0] is self
                 and type(attempt[1]) is _ConsumeAttempt and attempt[1].owner is self
                 and attempt[1].scope is s)
        cell = self._consume_allocation_origin
        _require(type(cell) is tuple and len(cell) == 8 and cell[0] is self and cell[1] is s
                 and cell[7] is attempt[1]
                 and type(cell[2]) is _ParserSeal and cell[2].parser is s.idle_scope[1]
                 and cell[3] is self._native_count_allocation_origin
                 and type(cell[3]) is tuple and len(cell[3]) == 2
                 and cell[3][0] is self and type(cell[3][1]) is int
                 and cell[3][1] is self._received_origin
                 and type(cell[4]) is _ReadReceipt and cell[4] is self._fact_origin
                 and cell[4].scope is s and cell[4].owner is self
                 and type(cell[4].count) is int and cell[4].count == cell[3][1]
                 and cell[5] is s.idle_scope[0].stop
                 and cell[6] is s.cursor._parser_allocation_origin
                 and type(cell[6]) is tuple and len(cell[6]) == 3
                 and cell[6][0] is s.cursor and cell[6][1] is cell[2].parser
                 and self._fact is cell[4]
                 and type(self._fact_allocation_origin) is tuple
                 and len(self._fact_allocation_origin) == 2
                 and self._fact_allocation_origin[0] is self
                 and self._fact_allocation_origin[1] is cell[4]
                 and self._consume_attempted is True and self._consume_returned is True
                 and type(self._consume_complete) is bool
                 and self._complete is True and self._initialized is True
                 and self._attempted is True and self._returned is True
                 and self._count_known is True and type(self._received) is int
                 and self._received is self._received_origin
                 and 0 < self._received <= s.idle_scope[2]
                 and self._inflight is False and self._reading_owned is False
                 and self._failed is False and self._unknown is False)
        fact = self._progress_origin
        _require(type(fact) is _ConsumedReceipt and self._progress is fact
                 and fact.mint is _MINT and fact.owner is self and fact.scope is s
                 and type(fact.count) is int and fact.count == self._received
                 and fact.before is cell[2] and type(fact.after) is _ParserSeal
                 and type(self._progress_allocation_origin) is tuple
                 and len(self._progress_allocation_origin) == 2
                 and self._progress_allocation_origin[0] is self
                 and self._progress_allocation_origin[1] is fact)
        if self._consume_complete:
            _require(self._pending is None and self._pending_origin is None
                     and self._pending_allocation_origin is None)
        else:
            pending = self._pending_allocation_origin
            _require(type(pending) is tuple and len(pending) == 3 and pending[0] is self
                     and type(pending[1]) is bytes and pending[1] is self._pending
                     and pending[1] is self._pending_origin
                     and type(pending[2]) is int and pending[2] == len(pending[1]) == fact.count)
        notice = s.notice
        stop, end = SignedReadNotice._stop_binding_metadata(notice)
        _require(stop is cell[5] and end <= s.idle_scope[4]
                 and notice._fact_origin is s.idle_scope[0]
                 and notice._fact_origin.stop is stop)
        from .presentation_remote_cleanup import _FUTURE
        _require(_FUTURE.done(notice._future_origin)
                 and not _FUTURE.cancelled(notice._future_origin)
                 and _FUTURE.result(notice._future_origin) is notice._fact_origin)
        current_seal = NativeCleanupRead._continuation_seal(self, s, fact.after)
        authenticated = NativeCleanupRead._auth_metadata(self, s, current_seal)
        from .presentation_credential_cleanup_body import metadata as body_metadata
        completed_body = body_metadata(self, s, current_seal)
        if authenticated is None and completed_body is None:
            NativeCleanupRead._same_parser(
                NativeCleanupRead._parser_seal(cell[2].parser), current_seal)
        return s

    def _progress_work_current(self):
        if self._consume_complete is False and self._auth_origin is not None:
            return NativeCleanupRead._captured_auth_current(self, cleanup=False)
        s = NativeCleanupRead._consumption_metadata(self)
        r = SignedReadNotice._actor(s.notice)
        SelectorReadiness._native(r.wait.owner)
        _require(SelectorReadiness._slots(r.wait.owner)[0] is None)
        SignedReadNotice._role_seal(s.notice)
        from .presentation_remote_cleanup import RemoteCleanupOwner
        _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
        if self._payload_seed_origin is not None:
            from .presentation_credential_cleanup_payload import current_seed
            current_seed(self)
        NativeCleanupRead._final_socket_fence(self, s)
        SignedReadNotice._role_seal(s.notice)
        _require(SignedReadNotice._actor(s.notice) is r
                 and NativeCleanupRead._consumption_metadata(self) is s)
        body = self._body_finish_origin
        if body is not None and body.returned is True:
            return body.fact
        auth = self._auth_origin
        if auth is not None and auth.returned is True:
            return auth.fact
        step = self._next_read_origin
        return self._progress_origin if step is None or step.fact is None else step.fact

    def consume_pending(self):
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._actor(s.notice)
        # Wrong actor, duplicate or an already failed owner does not revive or
        # reset the original one-shot attempt, nor poison committed progress.
        _require(self._consume_attempted is False and self._complete is True
                 and self._failed is False and self._unknown is False
                 and self._consume_attempt_allocation_origin is None)
        attempt = _ConsumeAttempt(self, s)
        self._consume_attempt_allocation_origin = (self, attempt)
        self._consume_attempted = True
        failed = False
        chunk = pending = copy = None
        try:
            # First native/currentness boundary is already owned by this attempt.
            NativeCleanupRead._current_work(self)
            pending = self._pending_allocation_origin
            before = NativeCleanupRead._parser_seal(s.idle_scope[1])
            NativeCleanupRead._current_work(self)
            _require(self._pending_allocation_origin is pending and type(pending) is tuple
                     and pending[0] is self and type(pending[1]) is bytes
                     and pending[1] is self._pending_origin and pending[2] == self._received)
            NativeCleanupRead._same_parser(
                NativeCleanupRead._parser_seal(before.parser), before)
            _require(self._consume_attempt_allocation_origin[1] is attempt)
            self._consume_allocation_origin = (self, s, before,
                self._native_count_allocation_origin, self._fact_origin,
                s.idle_scope[0].stop, s.cursor._parser_allocation_origin, attempt)
            chunk = pending[1]
            if type(before.parser) is SignedCleanupAuthPrefix:
                value = before.value + chunk
                target, header_done = before.target, before.header_done
                if header_done is False and len(value) == 8:
                    target, header_done = 8 + payload_size(value), True
                expected = before._replace(value=value, target=target, header_done=header_done)
                SignedCleanupAuthPrefix.feed(before.parser, chunk)
            else:
                _require(type(before.parser) is SignedResultDiscard
                         and type(before.hasher) is _HASH_TYPE)
                copy = _HASH_COPY(before.hasher)
                _HASH_UPDATE(copy, chunk)
                expected = before._replace(received=before.received + len(chunk),
                                           digest=_HASH_HEX(copy))
                SignedResultDiscard.feed(before.parser, chunk)
                from .presentation_credential_cleanup_payload import feed as feed_payload
                feed_payload(self, chunk, expected.received)
            self._consume_returned = True
            after = NativeCleanupRead._parser_seal(before.parser)
            NativeCleanupRead._same_parser(after, expected)
            fact = _ConsumedReceipt(_MINT, self, s, self._received, before, after)
            self._progress = self._progress_origin = fact
            self._progress_allocation_origin = (self, fact)
            NativeCleanupRead._progress_work_current(self)
            NativeCleanupRead._drop_pending(self)
            self._consume_complete = True
            NativeCleanupRead._consumption_metadata(self)
            return fact
        except BaseException:
            failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
        finally:
            chunk = pending = copy = None
            if failed:
                NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_CONSUMPTION_UNKNOWN") from None

    def current_progress_for_cleanup(self):
        _require(type(self) is NativeCleanupRead)
        if self._terminal_frame_origin is not None:
            from .presentation_credential_cleanup_terminal_frame import current_for_cleanup
            return current_for_cleanup(self)
        if self._terminal_origin is not None:
            from .presentation_credential_cleanup_terminal import current_for_cleanup
            return current_for_cleanup(self)
        if self._frame_origin is not None:
            from .presentation_credential_cleanup_frame import current_frame_for_cleanup
            return current_frame_for_cleanup(self)
        return NativeCleanupRead._base_progress_for_cleanup(self)

    def _base_progress_for_cleanup(self):
        if self._consume_complete is False and self._auth_origin is not None:
            return NativeCleanupRead._captured_auth_current(self, cleanup=True)
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._cleanup_actor(s.notice)
        _require(self._consume_complete is True)
        failed = False
        try:
            NativeCleanupRead._consumption_metadata(self)
            SelectorReadiness._native(r.wait.owner, actor=False)
            _require(SelectorReadiness._slots(r.wait.owner)[0] is None)
            SignedReadNotice._role_seal(s.notice)
            from .presentation_remote_cleanup import RemoteCleanupOwner
            _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
            if self._payload_seed_origin is not None:
                from .presentation_credential_cleanup_payload import current_seed
                current_seed(self)
            NativeCleanupRead._final_socket_fence(self, s)
            SignedReadNotice._role_seal(s.notice)
            _require(SignedReadNotice._cleanup_actor(s.notice) is r
                     and NativeCleanupRead._consumption_metadata(self) is s)
            body = self._body_finish_origin
            if body is not None:
                _require(body.complete is True)
                return body.fact
            auth = self._auth_origin
            if auth is not None:
                _require(auth.complete is True)
                return auth.fact
            step = self._next_read_origin
            _require(step is None or step.complete is True)
            return self._progress_origin if step is None else step.fact
        except BaseException:
            failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
            NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_PROGRESS_OBSERVER_UNKNOWN") from None

    def _continuation_seal(self, scope, initial):
        step = self._next_read_origin
        if step is None:
            _require(self._next_read is None and self._next_read_allocation_origin is None
                     and self._ledger is None and self._ledger_origin is None
                     and self._ledger_allocation_origin is None)
            return initial
        _require(type(step) is _NextRead and self._next_read is step
                 and type(self._next_read_allocation_origin) is tuple
                 and len(self._next_read_allocation_origin) == 2
                 and self._next_read_allocation_origin[0] is self
                 and self._next_read_allocation_origin[1] is step
                 and type(step.scope) is _NextScope and step.scope is step.scope_origin
                 and type(step.scope_allocation) is tuple and len(step.scope_allocation) == 2
                 and step.scope_allocation[0] is step
                 and step.scope_allocation[1] is step.scope
                 and step.scope.owner is self and step.scope.scope is scope
                 and type(step.scope.before) is _ProgressLedger)
        before, ledger = step.scope.before, self._ledger_origin
        _require(before.owner is self and type(before.ordinal) is int
                 and type(before.received) is int and type(before.committed) is int
                 and 0 <= before.ordinal < _WIRE_LIMIT
                 and 0 < before.received == before.committed <= _WIRE_LIMIT
                 and type(before.seal) is _ParserSeal
                 and type(step.scope.ordinal) is int
                 and step.scope.ordinal == before.ordinal + 1
                 and type(ledger) is _ProgressLedger and self._ledger is ledger
                 and type(self._ledger_allocation_origin) is tuple
                 and len(self._ledger_allocation_origin) == 2
                 and self._ledger_allocation_origin[0] is self
                 and self._ledger_allocation_origin[1] is ledger
                 and all(type(v) is int for v in ledger[1:4])
                 and type(ledger.seal) is _ParserSeal and ledger.owner is self
                 and type(step.received) is int
                 and all(type(v) is bool for v in (step.attempted, step.returned,
                     step.count_known, step.fed, step.complete, step.failed,
                     step.inflight, step.reading_owned))
                 and step.failed is False and step.inflight is False
                 and step.reading_owned is False)
        if not step.count_known:
            _require(step.count_cell is None and step.received == 0
                     and step.pending is None and step.returned is False and step.fed is False)
        else:
            _require(type(step.count_cell) is tuple and len(step.count_cell) == 2
                     and step.count_cell[0] is step and type(step.count_cell[1]) is int
                     and type(step.received) is int and step.received is step.count_cell[1]
                     and step.returned is True and step.attempted is True
                     and type(step.requested) is int
                     and 0 < step.received <= step.requested <= CHUNK_LIMIT
                     and before.received + step.received <= _WIRE_LIMIT)
        if step.complete:
            _require(step.pending is None and step.pending_cell is None
                     and ledger is step.committed_ledger and step.fed is True
                     and ledger.owner is self and ledger.ordinal == step.scope.ordinal
                     and ledger.received == before.received + step.received
                     and ledger.committed == before.committed + step.received
                     and ledger.seal is step.after)
        else:
            _require(ledger is before)
            if step.count_known:
                _require(type(step.pending_cell) is tuple and len(step.pending_cell) == 3
                         and step.pending_cell[0] is step and type(step.pending) is bytes
                         and step.pending_cell[1] is step.pending
                         and type(step.pending_cell[2]) is int
                         and step.pending_cell[2] == len(step.pending) == step.received)
        if step.fed:
            _require(type(step.after) is _ParserSeal and type(step.fact) is _NextReceipt
                     and type(step.fact_cell) is tuple and len(step.fact_cell) == 2
                     and step.fact_cell[0] is step and step.fact_cell[1] is step.fact
                     and all(type(v) is int for v in step.fact[1:5])
                     and step.fact.owner is self and step.fact.ordinal == step.scope.ordinal
                     and step.fact.count == step.received
                     and step.fact.total_received == before.received + step.received
                     and step.fact.total_committed == before.committed + step.received
                     and step.fact.after is step.after)
            return step.after
        _require(step.after is None and step.fact is None and step.fact_cell is None)
        return before.seal

    def read_and_consume_next(self):
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._actor(s.notice)
        _require(self._consume_complete is True and self._failed is False
                 and self._unknown is False and self._auth_origin is None
                 and self._body_finish_allocation is None)
        progress, allocation = self._progress_origin, self._progress_allocation_origin
        _require(type(progress) is _ConsumedReceipt and self._progress is progress
                 and progress.mint is _MINT and progress.owner is self and progress.scope is s
                 and type(progress.after) is _ParserSeal
                 and type(allocation) is tuple and len(allocation) == 2
                 and allocation[0] is self and allocation[1] is progress)
        NativeCleanupRead._continuation_seal(self, s, progress.after)
        previous = self._next_read_origin
        _require(previous is None or (type(previous) is _NextRead and previous.complete is True))
        if previous is None:
            before = _ProgressLedger(self, 0, self._received, self._received,
                                     self._progress_origin.after)
        else:
            before = self._ledger_origin
        boundary = before.seal
        if type(boundary.parser) is SignedCleanupAuthPrefix:
            _require(type(boundary.target) is int and type(boundary.value) is bytes)
            needed = boundary.target - len(boundary.value)
        else:
            _require(type(boundary.parser) is SignedResultDiscard
                     and type(boundary.stream) is CommittedFrameDigest
                     and type(boundary.stream._body_length) is int
                     and type(boundary.received) is int)
            needed = min(CHUNK_LIMIT, boundary.stream._body_length - boundary.received)
        # A completed record is a boundary, never an invitation to restart it.
        _require(type(needed) is int and 0 < needed <= CHUNK_LIMIT)
        step = _NextRead.__new__(_NextRead)
        step.scope = step.scope_origin = _NextScope(self, s, before, before.ordinal + 1)
        step.scope_allocation = (step, step.scope)
        step.attempted = step.returned = step.count_known = step.fed = step.complete = False
        step.failed = step.inflight = step.reading_owned = False
        step.received = 0
        step.requested = step.count_cell = step.pending = step.pending_cell = None
        step.after = step.fact = step.fact_cell = step.committed_ledger = None
        # This new bounded step replaces only a committed predecessor. Its scope
        # retains counts/seal, never the predecessor step or a linked receipt.
        self._ledger = self._ledger_origin = before
        self._ledger_allocation_origin = (self, before)
        self._next_read = self._next_read_origin = step
        self._next_read_allocation_origin = (self, step)
        chunk = copy = None
        failed = False
        try:
            NativeCleanupRead._progress_work_current(self)
            seal = before.seal
            parser = seal.parser
            if type(parser) is SignedCleanupAuthPrefix:
                needed = seal.target - len(seal.value)
            else:
                _require(type(parser) is SignedResultDiscard
                         and type(seal.stream) is CommittedFrameDigest)
                needed = min(CHUNK_LIMIT, seal.stream._body_length - seal.received)
            _require(type(needed) is int and 0 < needed <= CHUNK_LIMIT
                     and before.received + needed <= _WIRE_LIMIT)
            step.requested = needed
            channel = r.capture.channel
            _require(channel._reading is False and channel._writing is False)
            NativeCleanupRead._final_socket_fence(self, s)
            SignedReadNotice._role_seal(s.notice)
            _require(SignedReadNotice._actor(s.notice) is r
                     and NativeCleanupRead._consumption_metadata(self) is s
                     and _RECV is socket.socket.recv
                     and type(_DONTWAIT) is int and _DONTWAIT > 0)
            step.attempted = step.inflight = step.reading_owned = True
            channel._reading = True
            chunk = NativeCleanupRead._receive(s.sock, needed)
            step.returned = True
            if type(chunk) is bytes:
                step.received = len(chunk)
                step.count_cell = (step, step.received)
                step.count_known = True
                step.pending = chunk
                step.pending_cell = (step, chunk, step.received)
            allocation = self._next_read_allocation_origin
            _require(type(allocation) is tuple and len(allocation) == 2
                     and allocation[0] is self and allocation[1] is step
                     and step.reading_owned is True and step.inflight is True
                     and channel._socket is s.sock and channel._reading is True)
            channel._reading = False
            step.inflight = step.reading_owned = False
            NativeCleanupRead._progress_work_current(self)
            if type(parser) is SignedCleanupAuthPrefix:
                value = seal.value + chunk
                target, header_done = seal.target, seal.header_done
                if header_done is False and len(value) == 8:
                    target, header_done = 8 + payload_size(value), True
                expected = seal._replace(value=value, target=target, header_done=header_done)
                SignedCleanupAuthPrefix.feed(parser, chunk)
            else:
                copy = _HASH_COPY(seal.hasher)
                _HASH_UPDATE(copy, chunk)
                expected = seal._replace(received=seal.received + len(chunk),
                                         digest=_HASH_HEX(copy))
                SignedResultDiscard.feed(parser, chunk)
                from .presentation_credential_cleanup_payload import feed as feed_payload
                feed_payload(self, chunk, expected.received)
            step.after = NativeCleanupRead._parser_seal(parser)
            NativeCleanupRead._same_parser(step.after, expected)
            step.fact = _NextReceipt(self, step.scope.ordinal, step.received,
                before.received + step.received, before.committed + step.received, step.after)
            step.fact_cell = (step, step.fact)
            step.fed = True
            NativeCleanupRead._progress_work_current(self)
            ledger = _ProgressLedger(self, step.scope.ordinal,
                step.fact.total_received, step.fact.total_committed, step.after)
            step.committed_ledger = ledger
            self._ledger = self._ledger_origin = ledger
            self._ledger_allocation_origin = (self, ledger)
            step.pending = step.pending_cell = None
            step.complete = True
            NativeCleanupRead._consumption_metadata(self)
            if previous is not None:
                # Only the fully committed predecessor is retired, after the
                # successor commit is sealed. Break its private self-cells so
                # repeated short reads do not wait for cyclic GC to reclaim it.
                previous.scope_allocation = previous.count_cell = previous.fact_cell = None
                previous.failed = True
            return step.fact
        except BaseException:
            failed = step.failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
        finally:
            chunk = copy = None
            step.pending = step.pending_cell = None
            if (step.reading_owned is True and step.inflight is True
                    and type(self._next_read_allocation_origin) is tuple
                    and len(self._next_read_allocation_origin) == 2
                    and self._next_read_allocation_origin[0] is self
                    and self._next_read_allocation_origin[1] is step
                    and r.capture.channel._socket is s.sock
                    and r.capture.channel._reading is True):
                r.capture.channel._reading = False
                step.reading_owned = step.inflight = False
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_CONTINUATION_UNKNOWN") from None

    def _auth_metadata(self, scope, current_seal):
        auth = self._auth_origin
        if auth is None:
            _require(self._auth is None and self._auth_allocation_origin is None)
            return None
        _require(type(auth) is _AuthAttempt and self._auth is auth
                 and type(self._auth_allocation_origin) is tuple
                 and len(self._auth_allocation_origin) == 2
                 and self._auth_allocation_origin[0] is self
                 and self._auth_allocation_origin[1] is auth
                 and type(auth.scope) is _AuthScope and auth.scope is auth.scope_origin
                 and type(auth.scope_allocation) is tuple and len(auth.scope_allocation) == 2
                 and auth.scope_allocation[0] is auth and auth.scope_allocation[1] is auth.scope
                 and auth.scope.owner is self and auth.scope.scope is scope
                 and auth.scope.before is current_seal
                 and auth.scope.progress is self._progress_origin
                 and auth.scope.step is self._next_read_origin
                 and auth.scope.ledger is self._ledger_origin
                 and type(auth.scope.count) is int and type(auth.scope.total_received) is int
                 and all(type(v) is bool for v in (auth.returned, auth.complete, auth.failed))
                 and auth.failed is False)
        if auth.returned is False:
            _require(auth.complete is False and auth.checked is None
                     and auth.checked_cell is None and auth.fact is None and auth.fact_cell is None)
            return None
        held_scope = auth.scope
        before, checked = held_scope.before, auth.checked
        parser = before.parser
        _require(type(parser) is SignedCleanupAuthPrefix
                 and type(before.context) is tuple and len(before.context) == 2
                 and all(type(v) is int for v in before.context))
        live_context = (os.getpid(), threading.get_ident())
        # Native context sampling precedes the final pure alias/role seals.
        _require(self._auth is auth and self._auth_origin is auth
                 and type(self._auth_allocation_origin) is tuple
                 and len(self._auth_allocation_origin) == 2
                 and self._auth_allocation_origin[0] is self
                 and self._auth_allocation_origin[1] is auth
                 and auth.scope is held_scope and auth.scope_origin is held_scope
                 and type(auth.scope_allocation) is tuple and len(auth.scope_allocation) == 2
                 and auth.scope_allocation[0] is auth
                 and auth.scope_allocation[1] is held_scope and auth.checked is checked
                 and auth.returned is True and auth.failed is False
                 and held_scope.progress is self._progress_origin
                 and held_scope.step is self._next_read_origin
                 and held_scope.ledger is self._ledger_origin
                 and type(self._received) is int and self._received is self._received_origin
                 and (held_scope.progress is None or (
                     type(held_scope.progress) is _ConsumedReceipt
                     and NativeCleanupRead._continuation_seal(
                         self, scope, held_scope.progress.after) is current_seal)))
        SignedReadNotice._role_seal(scope.notice)
        _require(type(parser) is SignedCleanupAuthPrefix
                 and parser is scope.idle_scope[1]
                 and type(before.buffer) is bytearray and type(before.value) is bytes
                 and type(before.target) is int
                 and 73 <= len(before.value) == before.target <= RECORD_LIMIT
                 and before.header_done is True
                 and parser._initialized is True and parser._failed is False
                 and parser._finished is True and parser._buffer is before.buffer
                 and parser._buffer_origin is before.buffer and len(before.buffer) == 0
                 and parser._pins is before.pins and parser._pins_origin is before.pins
                 and parser._expected is before.expected
                 and parser._expected_origin is before.expected
                 and parser._context is before.context and parser._context_origin is before.context
                 and type(before.context) is tuple and len(before.context) == 2
                 and all(type(v) is int for v in before.context)
                 and before.context == live_context
                 and parser._target is before.target and parser._target_origin is before.target
                 and parser._header_done is True and parser._header_done_origin is True
                 and type(checked) is ConsistentCommitment
                 and type(auth.checked_cell) is tuple and len(auth.checked_cell) == 2
                 and auth.checked_cell[0] is auth and auth.checked_cell[1] is checked
                 and type(auth.values) is tuple and len(auth.values) == 4
                 and type(checked.canonical_json) is bytes
                 and 1 <= len(checked.canonical_json) <= JSON_LIMIT
                 and checked.canonical_json is auth.values[0]
                 and checked.canonical_json == before.value[8:-64]
                 and type(checked.frame_sha256) is str and checked.frame_sha256 is auth.values[1]
                 and type(checked.frame_length) is int and checked.frame_length is auth.values[2]
                 and type(auth.values[3]) is str and auth.values[3] in ("RESULT", "TERMINAL"))
        fact = auth.fact
        _require(type(fact) is _AuthReceipt and fact.owner is self and fact.scope is auth.scope
                 and fact.checked is checked and fact.values is auth.values
                 and type(auth.fact_cell) is tuple and len(auth.fact_cell) == 2
                 and auth.fact_cell[0] is auth and auth.fact_cell[1] is fact
                 and type(fact.count) is int and type(fact.total_received) is int
                 and fact.count == held_scope.count
                 and fact.total_received == held_scope.total_received)
        step, ledger = auth.scope.step, auth.scope.ledger
        if held_scope.progress is None:
            _require(step is None and ledger is None and held_scope.receipt is None
                     and fact.count == fact.total_received == 0)
        elif step is None:
            _require(auth.scope.receipt is self._progress_origin
                     and fact.count == self._received and fact.total_received == self._received)
        else:
            _require(type(step) is _NextRead and step.complete is True
                     and type(ledger) is _ProgressLedger
                     and auth.scope.receipt is step.fact
                     and fact.count == step.received and fact.total_received == ledger.received)
        return fact

    def _captured_auth_metadata(self, scope):
        """No post-cause receive/consume exists on this distinct captured path."""
        _require(self._initialized is True and self._failed is False and self._unknown is False
                 and all(type(v) is bool and v is False for v in (
                     self._attempted, self._returned, self._complete, self._count_known,
                     self._inflight, self._reading_owned, self._consume_attempted,
                     self._consume_returned, self._consume_complete))
                 and type(self._received) is int and self._received == 0
                 and self._received is self._received_origin
                 and all(v is None for v in (
                     self._native_count_allocation_origin, self._pending, self._pending_origin,
                     self._pending_allocation_origin, self._fact, self._fact_origin,
                     self._fact_allocation_origin, self._consume_allocation_origin,
                     self._consume_attempt_allocation_origin, self._progress,
                     self._progress_origin, self._progress_allocation_origin,
                     self._next_read, self._next_read_origin, self._next_read_allocation_origin,
                     self._ledger, self._ledger_origin, self._ledger_allocation_origin))
                 and scope.idle_scope[2] == 0)
        auth = self._auth_origin
        _require(type(auth) is _AuthAttempt and self._auth is auth
                 and type(self._auth_allocation_origin) is tuple
                 and len(self._auth_allocation_origin) == 2
                 and self._auth_allocation_origin[0] is self
                 and self._auth_allocation_origin[1] is auth
                 and type(auth.scope) is _AuthScope and auth.scope is auth.scope_origin
                 and type(auth.scope_allocation) is tuple and len(auth.scope_allocation) == 2
                 and auth.scope_allocation[0] is auth and auth.scope_allocation[1] is auth.scope
                 and auth.scope.owner is self and auth.scope.scope is scope
                 and type(auth.scope.before) is _ParserSeal)
        before = auth.scope.before
        _require(type(before.value) is bytes and type(before.buffer) is bytearray
                 and type(before.target) is int and type(before.header_done) is bool
                 and before.header_done is True)
        cursor, capture = scope.cursor, scope.idle_scope[0].reservation.capture
        state = cursor._parser_state_origin
        _require(capture.body is None and cursor._initialized is True and cursor._failed is False
                 and cursor._notice is scope.notice and cursor._notice_origin is scope.notice
                 and cursor._fact is scope.idle_scope[0]
                 and cursor._fact_origin is scope.idle_scope[0]
                 and type(state) is tuple and len(state) == 4
                 and cursor._parser_state is state
                 and type(cursor._parser_state_allocation_origin) is tuple
                 and len(cursor._parser_state_allocation_origin) == 3
                 and cursor._parser_state_allocation_origin[0] is cursor
                 and cursor._parser_state_allocation_origin[1] is before.parser
                 and cursor._parser_state_allocation_origin[2] is state
                 and type(state[0]) is bytearray and type(state[1]) is bytes
                 and type(state[2]) is int and state[3] is True
                 and before.parser is scope.idle_scope[1]
                 and cursor._parser is before.parser and cursor._parser_origin is before.parser
                 and before.buffer is state[0] and before.value == state[1]
                 and before.target is state[2] and before.header_done is True
                 and len(before.value) == before.target
                 and auth.scope.progress is None and auth.scope.step is None
                 and auth.scope.ledger is None and auth.scope.receipt is None
                 and type(auth.scope.count) is int and type(auth.scope.total_received) is int
                 and auth.scope.count == auth.scope.total_received == 0)
        stop, end = SignedReadNotice._stop_binding_metadata(scope.notice)
        _require(stop is scope.idle_scope[0].stop and end <= scope.idle_scope[4])
        from .presentation_remote_cleanup import _FUTURE
        _require(_FUTURE.done(scope.notice._future_origin)
                 and not _FUTURE.cancelled(scope.notice._future_origin)
                 and _FUTURE.result(scope.notice._future_origin) is scope.idle_scope[0])
        result = NativeCleanupRead._auth_metadata(self, scope, before)
        if result is None:
            NativeCleanupRead._same_parser(
                NativeCleanupRead._parser_seal(before.parser), before)
        return result

    def _captured_auth_current(self, *, cleanup):
        _require(type(cleanup) is bool)
        s = NativeCleanupRead._origin(self)
        r = (SignedReadNotice._cleanup_actor(s.notice) if cleanup
             else SignedReadNotice._actor(s.notice))
        NativeCleanupRead._captured_auth_metadata(self, s)
        SelectorReadiness._native(r.wait.owner, actor=not cleanup)
        _require(SelectorReadiness._slots(r.wait.owner)[0] is None)
        SignedReadNotice._role_seal(s.notice)
        from .presentation_remote_cleanup import RemoteCleanupOwner
        _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
        NativeCleanupRead._final_socket_fence(self, s)
        SignedReadNotice._role_seal(s.notice)
        _require((SignedReadNotice._cleanup_actor(s.notice) if cleanup
                  else SignedReadNotice._actor(s.notice)) is r)
        fact = NativeCleanupRead._captured_auth_metadata(self, s)
        return fact

    def finish_authentication(self):
        s = NativeCleanupRead._origin(self)
        r = SignedReadNotice._actor(s.notice)
        _require(self._failed is False and self._unknown is False and self._auth_origin is None
                 and self._auth is None and self._auth_allocation_origin is None)
        captured = self._consume_complete is False
        if captured:
            # Frozen original-parser validation before admitting any irreversible
            # verification. This route never creates native or consume receipts.
            _require(s.idle_scope[2] == 0 and s.idle_scope[0].reservation.capture.body is None)
            _require(NativeCleanupRead._metadata(self) is s)
            before = NativeCleanupRead._parser_seal(s.idle_scope[1])
            progress = step = receipt = None
            count = total = 0
        else:
            progress, cell = self._progress_origin, self._progress_allocation_origin
            _require(type(progress) is _ConsumedReceipt and self._progress is progress
                     and progress.owner is self and progress.scope is s and progress.mint is _MINT
                     and type(progress.after) is _ParserSeal
                     and type(cell) is tuple and len(cell) == 2
                     and cell[0] is self and cell[1] is progress)
            before = NativeCleanupRead._continuation_seal(self, s, progress.after)
            parser = before.parser
            # Pure completed-record admission precedes the irreversible attempt.
            _require(type(parser) is SignedCleanupAuthPrefix and parser is s.idle_scope[1]
                     and type(before.buffer) is bytearray and type(before.value) is bytes
                     and type(before.target) is int and before.header_done is True
                     and 73 <= len(before.value) == before.target <= RECORD_LIMIT
                     and parser._buffer is before.buffer and parser._buffer_origin is before.buffer
                     and bytes(before.buffer) == before.value)
            step = self._next_read_origin
            receipt = progress if step is None else step.fact
            _require(type(receipt) is (_ConsumedReceipt if step is None else _NextReceipt)
                     and type(receipt.count) is int)
            count = receipt.count
            total = count if step is None else receipt.total_received
            _require(type(total) is int and 0 < count <= total <= _WIRE_LIMIT)
        parser = before.parser
        _require(type(parser) is SignedCleanupAuthPrefix and parser is s.idle_scope[1]
                 and type(before.buffer) is bytearray and type(before.value) is bytes
                 and type(before.target) is int and before.header_done is True
                 and 73 <= len(before.value) == before.target <= RECORD_LIMIT
                 and parser._buffer is before.buffer and parser._buffer_origin is before.buffer
                 and bytes(before.buffer) == before.value)
        auth = _AuthAttempt.__new__(_AuthAttempt)
        auth_scope = _AuthScope(self, s, before, progress,
            step, self._ledger_origin, receipt, count, total)
        auth.scope = auth.scope_origin = auth_scope
        auth.scope_allocation = (auth, auth_scope)
        auth.returned = auth.complete = auth.failed = False
        auth.checked = auth.checked_cell = auth.values = auth.fact = auth.fact_cell = None
        self._auth = self._auth_origin = auth
        self._auth_allocation_origin = (self, auth)
        failed = False
        checked = value = None
        try:
            NativeCleanupRead._progress_work_current(self)
            checked = SignedCleanupAuthPrefix.finish(parser)
            auth.checked = checked
            auth.checked_cell = (auth, checked)
            auth.returned = True
            _require(type(checked) is ConsistentCommitment
                     and type(checked.canonical_json) is bytes
                     and 1 <= len(checked.canonical_json) <= JSON_LIMIT
                     and type(checked.frame_sha256) is str and type(checked.frame_length) is int)
            value = json.loads(checked.canonical_json)
            _require(type(value) is dict and value.get("family") == "phase"
                     and type(value.get("phase")) is str
                     and value["phase"] in ("RESULT", "TERMINAL")
                     and type(value.get("frame_sha256")) is str
                     and value["frame_sha256"] == checked.frame_sha256
                     and type(value.get("frame_length")) is int
                     and value["frame_length"] == checked.frame_length)
            auth.values = (checked.canonical_json, checked.frame_sha256,
                           checked.frame_length, value["phase"])
            auth.fact = _AuthReceipt(self, auth_scope, checked, auth.values, count, total)
            auth.fact_cell = (auth, auth.fact)
            NativeCleanupRead._progress_work_current(self)
            auth.complete = True
            if captured:
                NativeCleanupRead._captured_auth_metadata(self, s)
            else:
                NativeCleanupRead._consumption_metadata(self)
            return auth.fact
        except BaseException:
            failed = auth.failed = self._failed = self._unknown = True
            s.notice._failed = s.notice._unknown = True
            r.capture.cleanup._unknown = True
        finally:
            checked = value = None
            if failed:
                # Held actual bounded auth storage only, never a replacement buffer.
                before.buffer.clear()
                NativeCleanupRead._drop_pending(self)
        if failed:
            raise FrameError("BI1_NATIVE_CLEANUP_AUTHENTICATION_UNKNOWN") from None

    def start_terminal_frame(self):
        from .presentation_credential_cleanup_terminal_frame import start
        return start(self)

    def read_terminal_frame(self):
        from .presentation_credential_cleanup_terminal_frame import read_next
        return read_next(self)

    def finish_terminal_frame(self):
        from .presentation_credential_cleanup_terminal_frame import finish
        return finish(self)

    def begin_terminal(self):
        from .presentation_credential_cleanup_terminal import begin
        return begin(self)

    def read_terminal_auth(self):
        from .presentation_credential_cleanup_terminal import read_next
        return read_next(self)

    def finish_terminal_auth(self):
        from .presentation_credential_cleanup_terminal import finish
        return finish(self)

    def finish_body(self):
        from .presentation_credential_cleanup_body import finish_body
        return finish_body(self)

    def start_frame(self):
        from .presentation_credential_cleanup_frame import start_frame
        return start_frame(self)

    def read_frame_next(self):
        from .presentation_credential_cleanup_frame import read_frame_next
        return read_frame_next(self)

    def finish_frame(self):
        from .presentation_credential_cleanup_frame import finish_frame
        return finish_frame(self)

    def _drop_pending(self):
        _require(type(self) is NativeCleanupRead)
        self._pending = self._pending_origin = self._pending_allocation_origin = None

    def _retire_on_work_exit(self, cleanup):
        from .presentation_credential_cleanup_capture import SignedCleanupCapture
        from .presentation_credential_cleanup_notice import _SignedReadReady
        from .presentation_credential_cleanup_reservation import SignedReadReservation
        from .presentation_remote_cleanup import _TASK, RemoteCleanupOwner, _TaskAllocation

        _require(type(self) is NativeCleanupRead and type(cleanup) is RemoteCleanupOwner)
        cell = self._scope_allocation_origin
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(cell[1]) is _ReadScope)
        s = cell[1]
        _require(type(s.idle_scope) is tuple and len(s.idle_scope) == 5
                 and type(s.idle_scope[0]) is _SignedReadReady
                 and type(s.idle_scope[0].reservation) is SignedReadReservation)
        r = s.idle_scope[0].reservation
        _require(type(r.capture) is SignedCleanupCapture
                 and r.capture.cleanup is cleanup
                 and type(r.capture.work) is _TaskAllocation
                 and type(r.capture.work.task) is _TASK
                 and asyncio.current_task() is r.capture.work.task)
        if (self._pending_allocation_origin is not None or self._consume_attempted is True
                or self._auth_allocation_origin is not None):
            # No complete protocol drain yet: dropping pending bytes preserves
            # actual received counts and UNKNOWN, never a completed-frame fact.
            self._failed = self._unknown = True
            cleanup._unknown = True
            NativeCleanupRead._drop_pending(self)
            step_cell = self._next_read_allocation_origin
            if (type(step_cell) is tuple and len(step_cell) == 2
                    and step_cell[0] is self and type(step_cell[1]) is _NextRead):
                step_cell[1].pending = step_cell[1].pending_cell = None
            from .presentation_credential_cleanup_frame import retire_frame_pending
            retire_frame_pending(self)
            from .presentation_credential_cleanup_terminal import retire
            retire(self)
            from .presentation_credential_cleanup_terminal_frame import (
                retire as retire_terminal_frame,
            )
            retire_terminal_frame(self)
