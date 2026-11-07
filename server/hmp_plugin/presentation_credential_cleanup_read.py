"""One bounded original-task native read; pending bytes are not frame credit.

No parser/digest advancement, new reader task/interest, signing or release. The
original work's exit retires pending payload and preserves unknown protocol debt.
"""
from __future__ import annotations

import asyncio
import os
import socket
import stat
from typing import NamedTuple

from .presentation_cleanup_reader import CleanupReadGate
from .presentation_credential_cleanup_notice import (
    SignedCleanupReader,
    SignedReadNotice,
    SignedStoppedCursor,
)
from .presentation_credential_cleanup_reservation import inspect_signed_reservation
from .presentation_credential_stream import CHUNK_LIMIT
from .presentation_jobs import FrameError
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
        _require(type(owner._attempted) is bool and owner._attempted is False)


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

    def _metadata(self):
        s = NativeCleanupRead._origin(self)
        _require(self._failed is False and self._unknown is False
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
        _require(self._initialized is True and self._attempted is False)
        self._attempted = True
        chunk = None
        failed = False
        try:
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
        _require(self._complete is True)
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
        if self._pending_allocation_origin is not None:
            # No qualified parser consumer yet: dropping pending bytes preserves
            # actual received counts and UNKNOWN, never a completed-frame fact.
            self._failed = self._unknown = True
            cleanup._unknown = True
            NativeCleanupRead._drop_pending(self)
