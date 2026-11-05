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
from .presentation_broker_service import SocketChannel
from .presentation_cancel_budget import CancellationBudget, CancellationWindow
from .presentation_jobs import OUTPUT_LIMIT
from .presentation_readiness import ReadinessWakeError, SelectorReadiness, _scheduler_safe
from .presentation_remote_cleanup import (
    _FUTURE,
    _TASK,
    RemoteCleanupOwner,
    _initialize_future,
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


class _ReadFact(NamedTuple):
    mint: object
    gate: object
    owner: object
    work: object
    request: _Request
    budget: object
    clock: object
    outer: bytearray

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
                     self._done, self._eof))
                 and self._request is self._request_origin
                 and self._fact is self._fact_origin
                 and self._change is self._change_origin
                 and type(self._epoch) is int and 0 <= self._epoch < 1 << 63
                 and type(self._generation) is int and 0 <= self._generation < 1 << 63)
        if self._request is not None:
            r = self._request
            _require(type(r) is _Request and type(r.reader) is RemoteResultOwner
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
                     and type(r.cursor._data_origin) is tuple and len(r.cursor._data_origin) == 3
                     and r.cursor._data_origin[1] is r.outer)
        if self._fact is not None:
            f = self._fact
            _require(type(f) is _ReadFact and f.mint is _MINT and f.gate is self
                     and f.owner is o and f.work is o._allocations_snapshot[1]
                     and f.request is self._request_origin
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
                         and self._header.kind in ("RESULT", "TERMINAL"))
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

    def request(self):
        """Select cooperative post-GO only from original known local custody."""
        CleanupReadGate.guard(self)
        o = self._owner_origin
        if self._failed or o._unknown or o._write_fact_snapshot is None:
            return False
        RemoteCleanupOwner._quiescence_binding(o)
        reader = self._refs[3]._result_receiver_snapshot
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
        cursor.pending = None  # received body bytes are revoked discard, never another candidate
        if self._header is not None:
            _row(self._header)
            _require(self._header.kind == "RESULT" and self._header.sequence == 1
                     and self._header.version == 2
                     and self._header.binding == o._cancel_scope_snapshot[0]
                     and 0 <= cursor.body_received <= self._header.body_length <= OUTPUT_LIMIT)
            self._remaining_body = self._header.body_length - cursor.body_received
        _require(RemoteCleanupOwner._publish_write_quiescence(o))
        _require(RemoteCleanupOwner._remaining(o) > 0)
        f = _ReadFact(_MINT, self, o, o._allocations_snapshot[1], r,
                      self._refs[8], self._refs[4], r.outer)
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
