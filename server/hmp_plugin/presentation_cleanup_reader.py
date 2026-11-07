"""Original post-GO cleanup reader; decoded terminal DATA is never acceptance.

No new Task, work allowance, ACK, native release or image emission. Original
write quiescence permits the existing cleanup actor's one CANCEL, not closure.
"""
from __future__ import annotations

import asyncio
import errno
import os
import socket
from typing import NamedTuple

from .presentation_authority import AuthorityRefusalError
from .presentation_broker_codec import (
    TERMINAL_LIMIT,
    BrokerHeader,
    _binding,
    _row,
    decode_header,
    header_size,
)
from .presentation_broker_service import SocketChannel, _PreResultCursor, _PreResultScope
from .presentation_cancel_budget import CancellationBudget, CancellationWindow
from .presentation_jobs import OUTPUT_LIMIT, JobOwner, RemotePhase, State
from .presentation_readiness import ReadinessWakeError, SelectorReadiness, _scheduler_safe
from .presentation_remote_cleanup import (
    _FUTURE,
    _TASK,
    RemoteCleanupOwner,
    _initialize_future,
    _ReadyFact,
)
from .presentation_result_transport import RemoteResultOwner, _ReaderScope, _ResultCursor
from .presentation_terminal_claim import decode_handoff

_TIMEOUT = socket.socket.gettimeout
_RECV = socket.socket.recv
_MINT = object()
_LIMIT = OUTPUT_LIMIT + TERMINAL_LIMIT + 2 * 1032


def _require(value):
    if value is not True:
        raise AuthorityRefusalError


class CleanupReadSwitch(BaseException):
    def __init__(self, reader):
        super().__init__()
        self.reader = reader

    def __repr__(self):
        return "<CleanupReadSwitch metadata-only>"


class _Request(NamedTuple):
    reader: RemoteResultOwner
    scope: _ReaderScope
    cursor: _ResultCursor
    channel: SocketChannel
    write: object
    outer: bytearray
    mode: str = "result"
    state: object = None
    ready: object = None
    phase: object = None


class _PreState(NamedTuple):
    received: int
    target: int
    header: object
    done: bool
    waiter: object
    waiter_attempted: object
    waiter_retired: object


class _ReadFact(NamedTuple):
    mint: object
    gate: object
    owner: object
    work: object
    request: _Request
    budget: object
    clock: object
    outer: bytearray
    mode: str
    write: object

    def __repr__(self):
        return "<CleanupReadFact no-join no-release redacted>"


class _Change(NamedTuple):
    future: object
    epoch: int
    generation: int
    end: int

    def __repr__(self):
        return "<CleanupReadChange metadata-only redacted>"


class CleanupReadGate:
    def __init__(self, owner):
        _require(type(self) is CleanupReadGate and type(owner) is RemoteCleanupOwner)
        self._owner = self._owner_origin = owner
        self._refs = owner._refs_snapshot
        self._initialized = self._failed = self._requested = self._activated = False
        self._request = self._request_origin = None
        self._capture_attempted = self._capture_failed = False
        self._capture_kind = self._capture_receiver = self._capture_cause = None
        self._signed_capture = self._signed_capture_origin = None
        self._signed_capture_allocation_origin = None
        self._preflight = self._preflight_origin = None
        self._fact = self._fact_origin = None
        self._notice = self._notice_origin = _FUTURE.__new__(_FUTURE)
        self._notice_initialized = False
        self._notice_allocation = (self, self._notice_origin, owner._loop_snapshot)
        self._change = self._change_origin = None
        self._change_allocation = None
        self._change_initialized = self._change_active = self._changing = False
        self._epoch = self._generation = 0
        self._intent = self._io_unknown = self._done = self._eof = False
        self._received = self._remaining_body = 0
        self._outer = self._outer_origin = self._header = None
        self._pending = self._waiter = self._terminal_data = None
        _require(type(owner) is RemoteCleanupOwner and type(self._refs) is tuple
                 and len(self._refs) == 12 and owner._read_gate is self
                 and owner._read_gate_snapshot is self)
        _scheduler_safe(owner._loop_snapshot)
        _initialize_future(self._notice_origin, owner._loop_snapshot)
        self._notice_initialized = self._initialized = True

    def __repr__(self):
        return "<CleanupReadGate no-authority redacted>"

    def guard(self):
        _require(type(self) is CleanupReadGate)
        o = self._owner
        _require(type(self) is CleanupReadGate and type(o) is RemoteCleanupOwner
                 and o is self._owner_origin and o._read_gate is self
                 and o._read_gate_snapshot is self and self._refs is o._refs_snapshot
                 and self._initialized is True and self._notice_initialized is True
                 and type(self._notice_allocation) is tuple and len(self._notice_allocation) == 3
                 and self._notice_allocation[0] is self
                 and self._notice_allocation[1] is self._notice_origin
                 and self._notice_allocation[2] is o._loop_snapshot
                 and self._notice is self._notice_origin and type(self._notice) is _FUTURE
                 and _FUTURE.get_loop(self._notice_origin) is o._loop_snapshot
                 and not _FUTURE.cancelled(self._notice)
                 and all(type(v) is bool for v in (
                     self._failed, self._requested, self._activated, self._change_initialized,
                     self._change_active, self._changing, self._intent, self._io_unknown,
                     self._done, self._eof, self._capture_attempted, self._capture_failed))
                 and self._preflight is self._preflight_origin
                 and (self._capture_kind is None or (type(self._capture_kind) is str
                      and self._capture_kind in ("none", "pre", "result", "signed")))
                 and self._request is self._request_origin
                 and self._fact is self._fact_origin
                 and self._change is self._change_origin
                 and type(self._epoch) is int and 0 <= self._epoch < 1 << 63
                 and type(self._generation) is int and 0 <= self._generation < 1 << 63)
        _require(self._signed_capture is self._signed_capture_origin)
        if self._signed_capture_origin is not None:
            from .presentation_credential_cleanup_capture import inspect_signed_cleanup
            allocation = self._signed_capture_allocation_origin
            _require(self._capture_kind == "signed" and type(allocation) is tuple
                     and len(allocation) == 2 and allocation[0] is self
                     and allocation[1] is self._signed_capture_origin)
            inspect_signed_cleanup(self._signed_capture_origin, self, o)
        else:
            _require(self._signed_capture_allocation_origin is None)
        if self._preflight is not None:
            _require(self._capture_kind == "pre" and type(self._preflight) is _Request)
            CleanupReadGate._pre_seal(self, self._preflight)
        if self._request is not None:
            r = self._request
            _require(type(r) is _Request and type(r.mode) is str
                     and r.mode in ("result", "ready", "ready_wait"))
            if r.mode == "result":
                _require(r.state is None and r.ready is None and r.phase is None)
                _require(type(r.reader) is RemoteResultOwner
                         and type(r.scope) is _ReaderScope and type(r.cursor) is _ResultCursor
                         and type(r.channel) is SocketChannel and r.channel is self._refs[3]
                         and r.reader._scope is r.scope and r.reader._scope_snapshot is r.scope
                         and r.reader._cursor_origin is r.cursor and r.reader._cursor is r.cursor
                         and r.reader._cursor_snapshot is r.cursor and r.cursor.scope is r.scope
                         and r.scope.cleanup is o and r.scope.channel is r.channel
                         and r.scope.record is self._refs[2]
                         and r.scope.remote is o._remote_snapshot
                         and r.scope.task is o._allocations_snapshot[1].task
                         and r.reader._failure_cleanup_origin is o
                         and r.reader._io_channel_origin is r.channel
                         and r.channel._result_receiver_snapshot is r.reader
                         and r.channel._result_receiver is r.reader
                         and r.write is o._write_fact_snapshot
                         and type(r.outer) is bytearray
                         and type(r.cursor._data_origin) is tuple
                         and len(r.cursor._data_origin) == 3
                         and r.cursor._data_origin[1] is r.outer)
            else:
                _require(r is self._preflight_origin and r.write is None)
                CleanupReadGate._pre_seal(self, r)
        if self._fact is not None:
            f = self._fact
            _require(type(f) is _ReadFact and f.mint is _MINT and f.gate is self
                     and f.owner is o and f.work is o._allocations_snapshot[1]
                     and f.request is self._request_origin
                     and type(f.mode) is str and f.mode == f.request.mode
                     and f.write is o._write_fact_snapshot and f.write is not None
                     and f.budget is self._refs[8] and f.clock is self._refs[4]
                     and self._activated is True and _FUTURE.done(self._notice)
                     and _FUTURE.result(self._notice) is f
                     and type(self._outer) is bytearray and self._outer is self._outer_origin
                     and f.outer is f.request.outer and self._outer is f.outer
                     and len(self._outer) <= 1032
                     and type(self._received) is int and 0 <= self._received <= _LIMIT
                     and type(self._remaining_body) is int
                     and 0 <= self._remaining_body <= OUTPUT_LIMIT)
            if self._header is not None:
                _require(type(self._header) is BrokerHeader)
                _row(self._header)
                _binding(o._cancel_scope_snapshot[0])
                _require(self._header.version == 2
                         and self._header.binding == o._cancel_scope_snapshot[0]
                         and self._header.kind in (("RESULT", "TERMINAL")
                         if f.mode == "result" else ("READY", "TERMINAL")))
        else:
            _require(not _FUTURE.done(self._notice))
        if self._change is not None:
            c = self._change
            _require(type(self._change_allocation) is tuple
                     and len(self._change_allocation) == 3
                     and self._change_allocation[0] is self
                     and self._change_allocation[1] is self._fact_origin
                     and self._change_allocation[2] is c
                     and type(c) is _Change and type(c.future) is _FUTURE
                     and type(c.epoch) is int and c.epoch == self._epoch
                     and type(c.generation) is int and 0 <= c.generation <= self._generation
                     and type(c.end) is int and c.end > 0)
            if self._change_initialized:
                _require(_FUTURE.get_loop(c.future) is o._loop_snapshot
                         and not _FUTURE.cancelled(c.future))

    def _pre_seal(self, r):
        """Callback-free original cursor seals; consumed counters remain frozen."""
        o = self._owner_origin
        _require(type(r) is _Request and type(r.mode) is str
                 and r.mode in ("ready", "ready_wait")
                 and type(r.reader) is _PreResultCursor and r.cursor is r.reader
                 and type(r.scope) is _PreResultScope and type(r.state) is _PreState
                 and type(r.outer) is bytearray and r.channel is self._refs[3]
                 and r.write is None)
        c, scope, state = r.cursor, r.scope, r.state
        _require(c._initialized is True and c._io_unknown is False and c._intent is False
                 and type(c._done) is bool and type(c._cleanup_switched) is bool
                 and c._scope is scope and c._scope_snapshot is scope and c._scope_origin is scope
                 and c._buffer is r.outer and c._buffer_origin is r.outer
                 and scope.buffer is r.outer
                 and c._pending is None and c._waiter is state.waiter
                 and scope.channel is r.channel and scope.sock is r.channel._socket_snapshot
                 and scope.owner is o._remote_snapshot
                 and scope.task is o._allocations_snapshot[1].task
                 and scope.loop is o._loop_snapshot and type(scope.context) is tuple
                 and len(scope.context) == 2 and all(type(v) is int for v in scope.context)
                 and scope.context == o._context_snapshot[::2]
                 and scope.expected is o._cancel_scope_snapshot[0]
                 and type(scope.end) is int and scope.end == self._refs[9]
                 and r.channel._pre_result_cursor is c
                 and r.channel._pre_result_cursor_snapshot is c
                 and r.channel._pre_result_cursor_origin is c
                 and type(state.received) is int and type(state.target) is int
                 and 0 <= state.received <= state.target <= 1032
                 and type(state.done) is bool and c._done is state.done
                 and type(c._received) is int and c._received == state.received
                 and type(c._target) is int and c._target == state.target
                 and c._header is state.header and c._header_snapshot is state.header
                 and o._go_attempted is False
                 and o._remote_snapshot._go_admission is None
                 and o._remote_snapshot._go_admission_snapshot is None
                 and o._remote_snapshot._go_admission_used is False
                 and r.channel._go_write_intent is None
                 and r.channel._go_write_intent_snapshot is None
                 and r.channel._go_write_fact is None and r.channel._go_write_fact_snapshot is None
                 and type(o._go_barriers_snapshot.request) is _FUTURE
                 and not _FUTURE.done(o._go_barriers_snapshot.request)
                 and not _FUTURE.cancelled(o._go_barriers_snapshot.request))
        if state.header is not None:
            _row(state.header)
            _binding(scope.expected)
            _require(state.header.binding == scope.expected and state.header.kind == "READY"
                     and state.header.version == 2 and state.header.sequence == 0
                     and state.header.body_length == 0)
        if state.waiter is not None:
            _require(type(state.waiter) is SelectorReadiness
                     and state.waiter._initialized is True
                     and state.waiter._unknown is False
                     and type(state.waiter_attempted) is bool
                     and type(state.waiter_retired) is bool
                     and type(state.waiter._attempted) is bool
                     and type(state.waiter._retired) is bool
                     and state.waiter._attempted is state.waiter_attempted
                     and (state.waiter_retired is False or state.waiter._retired is True))
        else:
            _require(state.waiter_attempted is None and state.waiter_retired is None)
        if r.mode == "ready_wait":
            _require(r.phase is RemotePhase.READY and state.done
                     and r.ready is o._ready_fact_snapshot
                     and type(r.ready) is _ReadyFact and r.ready is o._ready_fact
                     and r.ready.work is o._allocations_snapshot[1]
                     and r.ready.channel is r.channel and r.ready.remote is scope.owner
                     and r.ready.future is o._barriers_snapshot.ready
                     and type(r.ready.future) is _FUTURE and _FUTURE.done(r.ready.future)
                     and _FUTURE.result(r.ready.future) is True and state.header is not None
                     and state.received == state.target)
            if state.waiter is not None:
                _require(state.waiter._attempted is True and state.waiter._retired is True)
        else:
            _require(r.phase is RemotePhase.BEGIN_INTENT and not state.done and r.ready is None
                     and o._ready_fact is None and o._ready_fact_snapshot is None)
            future = o._barriers_snapshot.ready
            _require(type(future) is _FUTURE and not _FUTURE.cancelled(future)
                     and (not _FUTURE.done(future) or _FUTURE.result(future) is False))

    def capture(self):
        """One metadata-only pre-poison snapshot; never IO or write permission."""
        _require(self._capture_attempted is False)
        self._capture_attempted = True
        self._capture_kind = "none"
        o = self._owner_origin
        try:
            _require(type(o) is RemoteCleanupOwner and o is self._owner
                     and o._read_gate is self and o._read_gate_snapshot is self)
            RemoteCleanupOwner._guard(o)
            channel = self._refs[3]
            self._capture_cause = o._barriers_snapshot.cause
            _require(type(self._capture_cause) is _FUTURE
                     and not _FUTURE.done(self._capture_cause))
            signed = getattr(channel, "_credential_result_receiver_snapshot", None)
            if (signed is not None
                    or getattr(channel, "_credential_result_receiver", None) is not None):
                from .presentation_credential_cleanup_capture import capture_signed_cleanup
                self._capture_kind = "signed"  # never reinterpret as a legacy unsigned cursor
                self._capture_receiver = signed
                captured = capture_signed_cleanup(self, o, signed)
                self._signed_capture = self._signed_capture_origin = captured
                self._signed_capture_allocation_origin = (self, captured)
                return
            self._capture_receiver = channel._result_receiver_snapshot
            if self._capture_receiver is not None:
                self._capture_kind = "result"
                return
            cursor = channel._pre_result_cursor_origin
            if cursor is None:
                return
            self._capture_kind = "pre"  # failure cannot become a later RESULT selection
            if (type(cursor) is not _PreResultCursor or cursor._initialized is not True
                    or cursor._io_unknown is not False or cursor._intent is not False
                    or cursor._pending is not None or type(cursor._done) is not bool
                    or channel._writing is not False):
                return
            owner, handle, _ = self._refs[11]
            phase = JobOwner.inspect_remote(owner, handle)
            _require(JobOwner.inspect(owner, handle)[0] is State.STARTING)
            mode = "ready_wait" if cursor._done else "ready"
            scope = cursor._scope_origin
            waiter = cursor._waiter
            attempted = retired = None
            if waiter is not None:
                _require(type(waiter) is SelectorReadiness)
                attempted, retired = waiter._attempted, waiter._retired
            state = _PreState(cursor._received, cursor._target, cursor._header,
                              cursor._done, waiter, attempted, retired)
            r = _Request(cursor, scope, cursor, channel, None, cursor._buffer_origin,
                         mode, state, o._ready_fact_snapshot, phase)
            CleanupReadGate._pre_seal(self, r)
            _require(channel._reading is (mode == "ready")
                     and len(r.outer) == (state.received if mode == "ready" else 0)
                     and not _TASK.done(scope.task) and not _TASK.cancelling(scope.task)
                     and cursor._cleanup_switched is False
                     and RemoteCleanupOwner._can_cancel(o, note_unknown=False))
            if state.waiter is not None:
                _require(type(state.waiter) is SelectorReadiness
                         and state.waiter._initialized is True and state.waiter._unknown is False
                         and type(state.waiter._attempted) is bool
                         and type(state.waiter._retired) is bool
                         and (mode != "ready_wait" or state.waiter._retired is True))
            self._preflight = self._preflight_origin = r
        except BaseException:
            self._capture_failed = True
            self._preflight = self._preflight_origin = None

    def request(self):
        """Select cooperative post-GO only from original known local custody."""
        CleanupReadGate.guard(self)
        o = self._owner_origin
        if self._failed or o._unknown or self._capture_failed:
            return False
        if self._capture_kind == "signed":
            # Progress DATA only. A typed current cooperative continuation is not qualified yet.
            return False
        if self._capture_kind == "pre":
            r = self._preflight_origin
            if r is None:
                return False
            CleanupReadGate._pre_seal(self, r)
            owner, handle, _ = self._refs[11]
            _, _, end, failed = CancellationBudget.inspect(self._refs[8])
            _require(o._intent is True and o._remote_snapshot._failed is True
                     and JobOwner.inspect(owner, handle)[0] is State.UNKNOWN
                     and JobOwner.inspect_remote(owner, handle) is RemotePhase.UNKNOWN
                     and self._capture_cause is o._barriers_snapshot.cause
                     and type(self._capture_cause) is _FUTURE
                     and not _FUTURE.done(self._capture_cause)
                     and type(end) is int and failed is False
                     and r.channel._reading is (r.mode == "ready")
                     and r.channel._writing is False and r.reader._cleanup_switched is False
                     and len(r.outer) == (r.state.received if r.mode == "ready" else 0))
            waiter = r.state.waiter
            if waiter is not None:
                SelectorReadiness._native(waiter, actor=False)
                handle, _ = SelectorReadiness._slots(waiter)
                SelectorReadiness._guard(waiter, actor=False)
                RemoteCleanupOwner._guard(o)
                if waiter._attempted is True and waiter._retired is False:
                    SelectorReadiness._owned(waiter, handle)
                else:
                    # Retired/no-registration flags cannot hide a live read
                    # subscription. Observe absence, without removing any slot.
                    _require(handle is None)
                    if waiter._attempted is False:
                        _require(waiter._retired is False and waiter._handle_snapshot is None)
            CleanupReadGate._pre_seal(self, r)
            RemoteCleanupOwner._guard(o)
            _, _, current_end, current_failed = CancellationBudget.inspect(self._refs[8])
            _require(o._intent is True and o._unknown is False
                     and o._remote_snapshot._failed is True
                     and type(current_end) is int and current_end == end
                     and current_failed is False
                     and self._capture_cause is o._barriers_snapshot.cause
                     and type(self._capture_cause) is _FUTURE
                     and not _FUTURE.done(self._capture_cause)
                     and not _FUTURE.cancelled(self._capture_cause))
            self._request = self._request_origin = r
            self._requested = True
            CleanupReadGate.guard(self)
            return True
        if (self._capture_kind != "result" or o._write_fact_snapshot is None
                or self._capture_receiver is not self._refs[3]._result_receiver_snapshot):
            return False
        RemoteCleanupOwner._quiescence_binding(o)
        reader = self._capture_receiver
        if (type(reader) is not RemoteResultOwner or reader._initialized is not True
                or reader._attempted is not True or reader._failed is not False
                or self._refs[3]._reading is not True or self._refs[3]._writing is not False
                or _TASK.done(o._allocations_snapshot[1].task)
                or _TASK.cancelling(o._allocations_snapshot[1].task)):
            return False
        cursor = reader._cursor_origin
        if type(cursor) is not _ResultCursor:
            return False
        _ResultCursor.guard(cursor, reader)
        if cursor.recv_intent or cursor.commit_intent or cursor.io_unknown:
            return False
        waiter = cursor.waiter
        if waiter is not None:
            _require(type(waiter) is SelectorReadiness)
            SelectorReadiness._native(waiter, actor=False)
            if waiter._attempted is True and waiter._retired is False:
                handle, _ = SelectorReadiness._slots(waiter)
                SelectorReadiness._owned(waiter, handle)
        r = _Request(reader, reader._scope_snapshot, cursor, self._refs[3],
                     o._write_fact_snapshot, cursor._data_origin[1])
        _require(r.scope.cleanup is o and r.scope.task is o._allocations_snapshot[1].task
                 and reader._failure_cleanup_origin is o and reader._io_channel_origin is r.channel)
        self._request = self._request_origin = r
        self._requested = True
        CleanupReadGate.guard(self)
        return True

    def switch(self, reader):
        CleanupReadGate.guard(self)
        if not self._requested:
            return
        o = self._owner_origin
        _require(o._intent is True and o._unknown is False and not self._failed
                 and self._request.reader is reader and not self._activated
                 and asyncio.current_task() is o._allocations_snapshot[1].task
                 and not _TASK.cancelling(o._allocations_snapshot[1].task))
        _, _, end, failed = CancellationBudget.inspect(self._refs[8])
        _require(type(end) is int and failed is False)
        if self._request.mode != "result":
            _require(type(reader) is _PreResultCursor and reader._cleanup_switched is False)
            reader._cleanup_switched = True
        raise CleanupReadSwitch(reader)

    def activate(self, reader):
        RemoteCleanupOwner._guard(self._owner_origin)
        CleanupReadGate.guard(self)
        o, r = self._owner_origin, self._request_origin
        _require(self._requested and not self._activated and not self._failed
                 and r.reader is reader
                 and asyncio.current_task() is o._allocations_snapshot[1].task
                 and not _TASK.cancelling(o._allocations_snapshot[1].task)
                 and o._intent and not o._unknown)
        self._activated = True  # transition attempt is irreversible before effects
        cursor = r.cursor
        if r.mode == "result":
            _ResultCursor.guard(cursor, reader)
            _require(not cursor.io_unknown and not cursor.recv_intent and not cursor.commit_intent)
            self._outer = self._outer_origin = r.outer
            self._received = cursor.received
            self._header = reader._header_snapshot
            if cursor.pending is not None and self._header is None:
                self._intent = True
                self._outer_origin.extend(cursor.pending)
                cursor.outer_committed += len(cursor.pending)
                self._intent = False
            cursor.pending = None  # revoked discard, never another candidate
            if self._header is not None:
                _row(self._header)
                _require(self._header.kind == "RESULT" and self._header.sequence == 1
                         and self._header.version == 2
                         and self._header.binding == o._cancel_scope_snapshot[0]
                         and 0 <= cursor.body_received <= self._header.body_length <= OUTPUT_LIMIT)
                self._remaining_body = self._header.body_length - cursor.body_received
        else:
            CleanupReadGate._pre_seal(self, r)
            _require(cursor._cleanup_switched is True)
            self._outer = self._outer_origin = r.outer
            self._received = r.state.received
            self._header = r.state.header if r.mode == "ready" else None
            if r.mode == "ready_wait":
                _require(r.channel._reading is False and len(r.outer) == 0)
                self._intent = True
                r.channel._reading = True
                self._intent = False
            else:
                _require(r.channel._reading is True)
        _require(RemoteCleanupOwner._publish_write_quiescence(o))
        _require(RemoteCleanupOwner._remaining(o) > 0)
        f = _ReadFact(_MINT, self, o, o._allocations_snapshot[1], r,
                      self._refs[8], self._refs[4], r.outer, r.mode, o._write_fact_snapshot)
        self._fact = self._fact_origin = f
        _scheduler_safe(o._loop_snapshot)
        _FUTURE.set_result(self._notice_origin, f)
        CleanupReadGate.guard(self)

    def permits_cancel(self):
        CleanupReadGate.guard(self)
        o = self._owner_origin
        _require(self._fact is not None and self._activated and not self._failed
                 and not self._io_unknown and not self._intent and not self._changing
                 and o._intent is True and o._unknown is False)
        _require(self._refs[3]._reading is (not self._done))
        return True

    def _current(self):
        o = self._owner_origin
        RemoteCleanupOwner._guard(o)
        CleanupReadGate.guard(self)
        _require(self._fact is not None and not self._failed and not self._changing
                 and not self._io_unknown and not self._intent and not self._done
                 and o._intent is True and o._unknown is False
                 and asyncio.current_task() is o._allocations_snapshot[1].task
                 and not _TASK.cancelling(o._allocations_snapshot[1].task))
        _require(RemoteCleanupOwner._remaining(o) > 0)
        CleanupReadGate.guard(self)
        _require(not self._failed and not self._changing and o._unknown is False)
        end = CancellationBudget.inspect(self._refs[8])[2]
        generation = self._generation
        _require(type(end) is int)
        channel = self._refs[3]
        SocketChannel._local_integrity(channel)
        _require(os.get_blocking(channel._fd_snapshot) is False)
        timeout = _TIMEOUT(channel._socket_snapshot)
        _require(type(timeout) is float and timeout == 0.0)
        CleanupReadGate.guard(self)
        _, last, current_end, failed = CancellationBudget.inspect(self._refs[8])
        _require(failed is False and current_end == end and type(last) is int
                 and last < end and self._generation == generation)
        return end

    def _signal_change(self, future):
        _require(self._change_initialized is True and self._change_active is True
                 and future is self._change_origin.future and type(future) is _FUTURE
                 and _FUTURE.get_loop(future) is self._owner_origin._loop_snapshot)
        _scheduler_safe(self._owner_origin._loop_snapshot)
        _FUTURE.set_result(future, None)

    def _arm_change(self, end):
        CleanupReadGate._current(self)
        _require(not self._change_active and not self._failed and self._epoch < (1 << 63) - 1)
        self._epoch += 1
        future = _FUTURE.__new__(_FUTURE)
        self._change_initialized = False
        self._change = self._change_origin = _Change(future, self._epoch, self._generation, end)
        self._change_allocation = (self, self._fact_origin, self._change_origin)
        self._change_active = True  # retained before initialization; uncertainty cannot retry
        try:
            _scheduler_safe(self._owner_origin._loop_snapshot)
            _initialize_future(future, self._owner_origin._loop_snapshot)
            self._change_initialized = True
            current = CancellationBudget.inspect(self._refs[8])[2]
            if current != end or self._change.generation != self._generation:
                CleanupReadGate._signal_change(self, future)  # no missed shortening
            return future
        except BaseException:
            self._failed = self._owner_origin._unknown = True
            raise

    def inherit(self, window):
        """Owned stop/min publication only; not sender/terminal qualification."""
        o = self._owner_origin
        RemoteCleanupOwner._guard(o)
        CleanupReadGate.guard(self)
        _require(self._fact is not None and not self._failed and not self._changing
                 and asyncio.current_task() in (o._caller_snapshot,
                     o._allocations_snapshot[0].task, o._allocations_snapshot[1].task)
                 and type(window) is CancellationWindow)
        self._changing = True  # no reader IO may cross an incomplete publication
        try:
            RemoteCleanupOwner._remaining(o)
            now = CancellationBudget.inspect(self._refs[8])[1]
            _require(type(now) is int)
            CleanupReadGate.guard(self)
            old_end = CancellationBudget.inspect(self._refs[8])[2]
            CancellationWindow.__post_init__(window)
            _require(type(old_end) is int and window.start_ns <= now
                     and window.start_ns <= self._refs[9])
            if window.end_ns < old_end:
                _require(self._generation < (1 << 63) - 1)
                self._generation += 1
                if self._change_active:
                    _require(self._change_initialized)
                    future = self._change_origin.future
                    if not _FUTURE.done(future):
                        CleanupReadGate._signal_change(self, future)
                CancellationBudget.inherit(self._refs[8], window, now)
                _require(CancellationBudget.inspect(self._refs[8])[2] == window.end_ns)
            self._changing = False
            RemoteCleanupOwner._guard(o)
            CleanupReadGate.guard(self)
        except BaseException:
            self._failed = o._unknown = True
            CancellationBudget.refuse(self._refs[8])
            raise

    def _retired_wait(self, waiter, *, allow_unattempted=False):
        """Latch uncertain registration debt before any later cleanup sampling."""
        known = (getattr(waiter, "_initialized", False) is True
                 and getattr(waiter, "_unknown", True) is False
                 and type(getattr(waiter, "_attempted", None)) is bool
                 and (getattr(waiter, "_retired", False) is True
                      or (allow_unattempted
                          and getattr(waiter, "_attempted", None) is False)))
        if not known:
            self._io_unknown = True
        _require(known)

    async def _recv(self, count):
        _require(type(count) is int and 0 < count <= 65536)
        while True:
            end = CleanupReadGate._current(self)
            received = self._received
            remaining, header = self._remaining_body, self._header
            outer = self._fact_origin.outer
            self._intent = True
            try:
                part = _RECV(self._refs[3]._socket_snapshot, count)
            except BlockingIOError as error:
                if (type(error) is not BlockingIOError or type(error.errno) is not int
                        or error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK)):
                    raise
                self._intent = False
                notice = CleanupReadGate._arm_change(self, end)
                waiter = SelectorReadiness.__new__(SelectorReadiness)
                self._waiter = waiter
                try:
                    SelectorReadiness.__init__(waiter, self._refs[3]._socket_snapshot)
                    await SelectorReadiness.wait(waiter, end, wake=notice)
                except (ReadinessWakeError, TimeoutError):
                    CleanupReadGate._retired_wait(self, waiter, allow_unattempted=True)
                    self._change_active = False
                    CleanupReadGate._current(self)
                    continue
                except BaseException:
                    CleanupReadGate._retired_wait(self, waiter, allow_unattempted=True)
                    raise
                CleanupReadGate._retired_wait(self, waiter)
                self._change_active = False
                continue
            self._pending = part
            CleanupReadGate.guard(self)
            _require(type(part) is bytes and self._outer_origin is outer
                     and self._header is header
                     and type(self._received) is int and self._received == received
                     and type(self._remaining_body) is int and self._remaining_body == remaining
                     and len(part) <= count and received + len(part) <= _LIMIT)
            self._received = received + len(part)
            self._intent = False
            if not part:
                self._eof = True
                return None
            return part

    async def _header_bytes(self):
        CleanupReadGate.guard(self)
        outer = self._fact_origin.outer
        part = None
        try:
            for target in (8, None):
                if target is None:
                    target = 8 + header_size(bytes(outer[:8]))
                while len(outer) < target:
                    part = await CleanupReadGate._recv(self, target - len(outer))
                    if part is None:
                        return None
                    self._intent = True
                    CleanupReadGate.guard(self)
                    _require(self._outer_origin is outer)
                    outer.extend(part)
                    self._pending = part = None
                    self._intent = False
            return decode_header(bytes(outer),
                expected=self._owner_origin._cancel_scope_snapshot[0], expected_version=2)
        finally:
            part = None

    async def drain(self):
        _require(type(self._fact_origin) is _ReadFact)
        original_outer = self._fact_origin.outer
        part = body = None
        try:
            CleanupReadGate._current(self)
            mode = self._fact_origin.mode
            if mode == "result":
                if self._header is None:
                    self._header = await CleanupReadGate._header_bytes(self)
                    if self._header is None:
                        return False
                    _require(self._header.kind in ("RESULT", "TERMINAL")
                             and self._header.sequence == 1)
                    self._remaining_body = self._header.body_length
                if self._header.kind == "RESULT":
                    _require(4 <= self._header.body_length <= OUTPUT_LIMIT)
                    while self._remaining_body:
                        remaining = self._remaining_body
                        _require(type(remaining) is int)
                        part = await CleanupReadGate._recv(self, min(remaining, 65536))
                        if part is None:
                            return False  # torn RESULT is EOF/debt, never a scan for TERMINAL
                        self._intent = True
                        CleanupReadGate.guard(self)
                        _require(type(self._remaining_body) is int
                                 and self._remaining_body == remaining)
                        self._remaining_body = remaining - len(part)
                        self._pending = part = None
                        self._intent = False
                    self._intent = True
                    original_outer[:] = b"\x00" * len(original_outer)
                    original_outer.clear()
                    self._intent = False
                    self._header = await CleanupReadGate._header_bytes(self)
                    if self._header is None:
                        return False
                    _require(self._header.kind == "TERMINAL" and self._header.sequence == 2)
            else:
                expected = 1 if mode == "ready_wait" else 0
                if self._header is None:
                    self._header = await CleanupReadGate._header_bytes(self)
                    if self._header is None:
                        return False
                if mode == "ready" and self._header.kind == "READY":
                    _require(self._header.sequence == 0 and self._header.body_length == 0)
                    self._intent = True
                    original_outer[:] = b"\x00" * len(original_outer)
                    original_outer.clear()
                    self._intent = False
                    self._header = await CleanupReadGate._header_bytes(self)
                    if self._header is None:
                        return False
                    expected = 1
                _require(self._header.kind == "TERMINAL" and self._header.sequence == expected)
            _require(self._header.kind == "TERMINAL"
                     and 0 < self._header.body_length <= TERMINAL_LIMIT)
            terminal_header = self._header
            terminal_length = terminal_header.body_length
            body = bytearray()
            while len(body) < terminal_length:
                part = await CleanupReadGate._recv(self, terminal_length - len(body))
                _require(self._header is terminal_header)
                if part is None:
                    return False
                body.extend(part)
                self._pending = part = None
            self._terminal_data = decode_handoff(bytes(body))  # DATA ONLY, never ACK/acceptance
            self._owner_origin._unknown = True  # no subsequent IO from unqualified sender stamp
            return False
        except BaseException:
            if self._intent is not False:
                self._io_unknown = True
            self._failed = self._owner_origin._unknown = True
            return False
        finally:
            if type(body) is bytearray:
                body[:] = b"\x00" * len(body)
                body.clear()
            part = body = self._pending = None
            self._done = True
            original_outer[:] = b"\x00" * len(original_outer)
            original_outer.clear()
            if not self._io_unknown and not self._intent:
                self._refs[3]._reading = False
