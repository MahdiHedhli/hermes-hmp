"""Fixed signed CANCEL write on original cleanup task/window; no remote settlement."""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import stat
from typing import NamedTuple

from .presentation_broker_service import (
    _BEGIN_WRITE_MINT,
    _BeginWriteFact,
)
from .presentation_cancel_budget import CancellationBudget
from .presentation_credential_phase import check_commitment, check_complete_frame
from .presentation_credential_pre_ready_cancel import (
    NativePreReadyCancelCommitment,
    _PreReadyCancelScope,
)
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError
from .presentation_readiness import SelectorReadiness, SelectorWriteReadiness
from .presentation_remote_cleanup import _TASK

_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_PRE_READY_CANCEL_WRITE_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_PRE_READY_CANCEL_WRITE_REFUSED")


class _PreReadyCancelWriterScope(NamedTuple):
    signer: object
    signed_scope: _PreReadyCancelScope
    raw: bytes
    frame: bytes
    end: int
    sequence: int
    wire: bytes
    begin: object

    def __repr__(self):
        return "<CancelWriterScope original-window signed-wire redacted>"


class _PreReadyCancelWriteFact(NamedTuple):
    mint: object
    writer: object
    scope: _PreReadyCancelWriterScope
    count: int

    def __repr__(self):
        return "<CancelWriteFact local-transmission-only redacted>"


class NativePreReadyCancelWriter:
    @classmethod
    def retain(cls, signer):
        _require(cls is NativePreReadyCancelWriter
                 and type(signer) is NativePreReadyCancelCommitment)
        signed = NativePreReadyCancelCommitment._metadata(signer)
        b = signed.begin
        _require(asyncio.current_task() is signed.allocation.task
                 and _TASK.cancelling(signed.allocation.task) == 0
                 and signer._complete is True and signer._failed is False
                 and signer._writer is None and signer._writer_snapshot is None
                 and b.channel._credential_cancel_writer is None
                 and b.channel._credential_cancel_writer_snapshot is None)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _PreReadyCancelWriterScope(
            signer, signed, signer._raw_snapshot, signer._frame_snapshot,
            signer._end_snapshot, 1,
            signer._raw_snapshot + signer._frame_snapshot,
            b.channel._begin_write_fact_snapshot)
        owner._attempted = owner._active = owner._inflight = False
        owner._failed = owner._unknown = owner._complete = False
        owner._offset = owner._offset_snapshot = 0
        owner._waiter = owner._waiter_origin = None
        owner._fact = owner._fact_snapshot = None
        signer._writer = signer._writer_snapshot = owner
        b.channel._credential_cancel_writer = b.channel._credential_cancel_writer_snapshot = owner
        try:
            NativePreReadyCancelWriter._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_PRE_READY_CANCEL_WRITER_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<NativePreReadyCancelWriter original-cleanup redacted>"

    def _begin_writing(self, begin_writer):
        """Pure fixed BEGIN reciprocal handoff; no phase or IO permission."""
        from .presentation_credential_begin_write import (
            NativeBeginWriter,
            _BeginWriterScope,
            _SignedBeginWriteComplete,
        )

        _require(type(self) is NativePreReadyCancelWriter
                 and type(self._scope) is _PreReadyCancelWriterScope
                 and self._scope is self._scope_snapshot
                 and type(begin_writer) is NativeBeginWriter)
        s = self._scope_snapshot
        _require(type(s.signed_scope) is _PreReadyCancelScope
                 and type(s.signed_scope.begin) is _BeginWriterScope)
        b = s.signed_scope.begin
        _require(begin_writer._scope_snapshot is b
                 and b.channel._credential_cancel_writer is self
                 and b.channel._credential_cancel_writer_snapshot is self
                 and type(s.signer) is NativePreReadyCancelCommitment
                 and s.signer._writer is self and s.signer._writer_snapshot is self
                 and s.signer._scope_snapshot is s.signed_scope
                 and type(begin_writer._completion_snapshot) is _SignedBeginWriteComplete
                 and s.begin is begin_writer._completion_snapshot.native
                 and type(s.begin) is _BeginWriteFact and s.begin.mint is _BEGIN_WRITE_MINT
                 and b.channel._begin_write_fact is s.begin
                 and b.channel._begin_write_fact_snapshot is s.begin
                 and b.channel._go_write_intent is None
                 and b.channel._go_write_intent_snapshot is None
                 and b.channel._go_write_fact is None and b.channel._go_write_fact_snapshot is None
                 and type(self._active) is bool)
        return self._active

    def _native_completed(self, signer):
        """Callback-free reciprocal proof for the existing native completion bool."""
        _require(type(self) is NativePreReadyCancelWriter
                 and type(self._scope) is _PreReadyCancelWriterScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(signer) is NativePreReadyCancelCommitment and s.signer is signer
                 and type(s.signed_scope) is _PreReadyCancelScope
                 and signer._scope_snapshot is s.signed_scope
                 and signer._writer is self and signer._writer_snapshot is self
                 and self._complete is True and self._failed is False and self._unknown is False
                 and type(self._offset) is int and self._offset is self._offset_snapshot
                 and type(s.wire) is bytes and self._offset == len(s.wire)
                 and type(self._fact) is _PreReadyCancelWriteFact
                 and self._fact is self._fact_snapshot
                 and self._fact.mint is _PRE_READY_CANCEL_WRITE_MINT and self._fact.writer is self
                 and self._fact.scope is s and type(self._fact.count) is int
                 and self._fact.count == self._offset)

    def _metadata(self):
        _require(type(self) is NativePreReadyCancelWriter
                 and type(self._scope) is _PreReadyCancelWriterScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.signer) is NativePreReadyCancelCommitment
                 and NativePreReadyCancelCommitment._metadata(s.signer) is s.signed_scope
                 and s.signer._complete is True and s.signer._failed is False
                 and s.signer._writer is self and s.signer._writer_snapshot is self
                 and type(s.raw) is bytes and s.raw is s.signer._raw_snapshot
                 and type(s.frame) is bytes and s.frame is s.signer._frame_snapshot
                 and type(s.end) is int and s.end == s.signer._end_snapshot
                 and type(s.sequence) is int and s.sequence == 1
                 and type(s.wire) is bytes and 0 < len(s.wire) <= 3096
                 and s.wire == s.raw + s.frame
                 and self._offset is self._offset_snapshot and type(self._offset) is int
                 and 0 <= self._offset <= len(s.wire)
                 and self._waiter is self._waiter_origin and self._fact is self._fact_snapshot
                 and all(type(v) is bool for v in (self._attempted, self._active, self._inflight,
                                                   self._failed, self._unknown, self._complete)))
        b = s.signed_scope.begin
        _require(b.channel._credential_cancel_writer is self
                 and b.channel._credential_cancel_writer_snapshot is self
                 and b.channel._writing is self._active
                 and b.channel._begin_write_fact_snapshot is s.begin
                 and b.channel._go_write_fact_snapshot is None
                 and s.signed_scope.cleanup._cancel_write_completed is self._complete)
        if self._complete:
            NativePreReadyCancelWriter._native_completed(self, s.signer)
        else:
            _require(self._fact is None)
        return s

    def _guard(self):
        s = NativePreReadyCancelWriter._metadata(self)
        signed = s.signed_scope
        b = signed.begin
        _require(asyncio.current_task() is signed.allocation.task
                 and _TASK.cancelling(signed.allocation.task) == 0
                 and self._failed is False and self._unknown is False and self._complete is False)
        _require(NativePreReadyCancelCommitment._begin_current(s.signer) is signed)
        checked = check_commitment(s.raw, sender_public=signed.pins[0],
                                   receiver_public=signed.pins[1],
                                   expected=dict(signed.expected))
        check_complete_frame(checked, s.frame, binding=b.intent.binding)
        _require(NativePreReadyCancelCommitment._guard(s.signer) is signed)
        fd = _FILENO(b.sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == b.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                     == b.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(b.sock) == 0.0
                 and os.get_inheritable(fd) is False)
        material = NativePhaseWorkOwner._retained_material(signed.producer)
        _require(asyncio.current_task() is signed.allocation.task
                 and _TASK.cancelling(signed.allocation.task) == 0
                 and material[0] is b.remote and material[2] is b.channel
                 and signed.cleanup._intent is True and signed.cleanup._unknown is False
                 and signed.cleanup._work_joined is True)
        original, _, end, failed = CancellationBudget.inspect(signed.cleanup_refs[8])
        _require(type(original) is int and original == b.intent.end_ns
                 and type(end) is int and end == s.end and failed is False
                 and NativePreReadyCancelWriter._metadata(self) is s)
        return s

    def _settled(self):
        NativePreReadyCancelWriter._metadata(self)
        _require(self._inflight is False and self._unknown is False)
        if self._waiter_origin is not None:
            waiter = self._waiter_origin
            _require(type(waiter) is SelectorWriteReadiness)
            SelectorReadiness._guard(waiter, actor=False)
            _require(waiter._retired is True and waiter._unknown is False)

    async def write_cancel(self):
        s = NativePreReadyCancelWriter._metadata(self)
        signed = s.signed_scope
        b = signed.begin
        _require(asyncio.current_task() is signed.allocation.task
                 and _TASK.cancelling(signed.allocation.task) == 0
                 and self._attempted is False and self._failed is False
                 and self._complete is False and self._active is False)
        self._attempted = self._active = True
        b.channel._writing = True
        try:
            while self._offset < len(s.wire):
                _require(NativePreReadyCancelWriter._guard(self) is s)
                before = self._offset
                data = s.wire[before:]
                self._inflight = True
                try:
                    count = _SEND(b.sock, data)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._scope is s and self._scope_snapshot is s
                             and self._offset is before and self._offset_snapshot is before
                             and self._inflight is True)
                    self._inflight = False
                    waiter = SelectorWriteReadiness.__new__(SelectorWriteReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorWriteReadiness.__init__(waiter, b.sock)
                    await SelectorReadiness.wait(waiter, s.end)
                    NativePreReadyCancelWriter._settled(self)
                    continue
                _require(type(count) is int and 0 <= count <= len(data))
                same = (self._scope is s and self._scope_snapshot is s
                        and self._offset is before and self._offset_snapshot is before
                        and self._inflight is True)
                self._offset = self._offset_snapshot = before + count
                self._inflight = False
                if not same:
                    self._unknown = True
                    raise FrameError("BI1_CREDENTIAL_PRE_READY_CANCEL_WRITE_STATE_UNKNOWN")
                _require(count > 0 and NativePreReadyCancelWriter._guard(self) is s)
            NativePreReadyCancelWriter._settled(self)
            _require(NativePreReadyCancelWriter._guard(self) is s)
            self._fact = self._fact_snapshot = _PreReadyCancelWriteFact(
                _PRE_READY_CANCEL_WRITE_MINT, self, s, self._offset)
            self._complete = True
            signed.cleanup._cancel_write_completed = True
        except BaseException:
            self._failed = True
            raise
        finally:
            try:
                NativePreReadyCancelWriter._settled(self)
                self._active = False
                b.channel._writing = False
            except BaseException:
                self._unknown = True

    def _released(self, channel):
        s = NativePreReadyCancelWriter._metadata(self)
        b = s.signed_scope.begin
        allocation = s.signed_scope.allocation
        _require(_TASK.get_loop(allocation.task) is b.loop
                 and _TASK.get_coro(allocation.task) is allocation.coroutine
                 and channel is b.channel and self._active is False and channel._writing is False
                 and (asyncio.current_task() is s.signed_scope.allocation.task
                      or _TASK.done(s.signed_scope.allocation.task)))
        NativePreReadyCancelWriter._settled(self)
