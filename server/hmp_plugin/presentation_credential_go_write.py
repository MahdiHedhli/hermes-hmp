"""Original-task fixed signed GO write; no production dispatch or worker relay."""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import stat
from typing import NamedTuple

from .presentation_broker_service import (
    _BEGIN_WRITE_MINT,
    _GO_WRITE_MINT,
    _BeginWriteFact,
    _GoWriteFact,
    _GoWriteIntent,
)
from .presentation_credential_go import NativeGoCommitment
from .presentation_credential_phase import check_commitment, check_complete_frame
from .presentation_jobs import FrameError
from .presentation_readiness import SelectorReadiness, SelectorWriteReadiness
from .presentation_remote_cleanup import _TASK, RemoteCleanupOwner

_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_GO_WRITE_REFUSED")


class _GoWriterScope(NamedTuple):
    commitment: object
    signed_scope: object
    raw: bytes
    wire: bytes
    intent: object

    def __repr__(self):
        return "<GoWriterScope signed-wire redacted>"


class NativeGoWriter:
    @classmethod
    def retain(cls, commitment):
        _require(cls is NativeGoWriter and type(commitment) is NativeGoCommitment)
        signed = NativeGoCommitment._metadata(commitment)
        b = signed.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and commitment._complete is True and commitment._failed is False
                 and commitment._writer is None and commitment._writer_snapshot is None
                 and b.channel._credential_go_writer is None
                 and b.channel._credential_go_writer_snapshot is None)
        begin = b.channel._begin_write_fact_snapshot
        _require(type(begin) is _BeginWriteFact and begin.mint is _BEGIN_WRITE_MINT
                 and begin.intent is b.intent and b.channel._begin_write_fact is begin)
        intent = _GoWriteIntent(begin, b.allocation, signed.admission, signed.frame, object())
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _GoWriterScope(
            commitment, signed, commitment._raw_snapshot,
            commitment._raw_snapshot + signed.frame, intent)
        owner._attempted = owner._active = owner._inflight = False
        owner._intent_published = False
        owner._failed = owner._unknown = owner._complete = False
        owner._offset = owner._offset_snapshot = 0
        owner._waiter = owner._waiter_origin = None
        owner._fact = owner._fact_snapshot = None
        commitment._writer = commitment._writer_snapshot = owner
        b.channel._credential_go_writer = b.channel._credential_go_writer_snapshot = owner
        try:
            _require(NativeGoCommitment._guard(commitment) is signed)
            _require(commitment._writer is owner and commitment._writer_snapshot is owner
                     and b.channel._credential_go_writer is owner
                     and b.channel._credential_go_writer_snapshot is owner
                     and b.channel._go_write_intent is None
                     and b.channel._go_write_intent_snapshot is None
                     and b.channel._go_write_fact is None
                     and b.channel._go_write_fact_snapshot is None)
            b.channel._go_write_intent = b.channel._go_write_intent_snapshot = intent
            owner._intent_published = True
            NativeGoWriter._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_GO_WRITER_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<NativeGoWriter original-work redacted>"

    def _begin_writing(self, begin_writer):
        """Pure reciprocal IO-slot description; no current phase authority."""
        from .presentation_credential_begin_write import (
            NativeBeginWriter,
            _BeginWriterScope,
            _SignedBeginWriteComplete,
        )
        from .presentation_credential_go import _GoCommitmentScope
        from .presentation_credential_ready_read import _ReadyReadScope
        from .presentation_credential_ready_transition import _ReadyTransitionScope

        _require(type(self) is NativeGoWriter and type(self._scope) is _GoWriterScope
                 and self._scope is self._scope_snapshot
                 and type(begin_writer) is NativeBeginWriter)
        s = self._scope_snapshot
        _require(type(s.signed_scope) is _GoCommitmentScope
                 and type(s.signed_scope.ready_scope) is _ReadyTransitionScope
                 and type(s.signed_scope.ready_scope.read_scope) is _ReadyReadScope)
        b = s.signed_scope.ready_scope.read_scope.write_scope
        _require(type(b) is _BeginWriterScope and begin_writer._scope_snapshot is b
                 and b.channel._credential_go_writer is self
                 and b.channel._credential_go_writer_snapshot is self
                 and type(s.commitment) is NativeGoCommitment
                 and s.commitment._writer is self and s.commitment._writer_snapshot is self
                 and s.commitment._scope_snapshot is s.signed_scope
                 and type(s.intent) is _GoWriteIntent
                 and type(begin_writer._completion_snapshot) is _SignedBeginWriteComplete
                 and s.intent.begin is begin_writer._completion_snapshot.native
                 and s.intent.work is b.allocation
                 and s.intent.admission is s.signed_scope.admission
                 and type(self._active) is bool and type(self._intent_published) is bool)
        if self._intent_published:
            _require(b.channel._go_write_intent is s.intent
                     and b.channel._go_write_intent_snapshot is s.intent)
        else:
            _require(self._active is False and self._attempted is False
                     and b.channel._go_write_intent is None
                     and b.channel._go_write_intent_snapshot is None)
        return self._active

    def _metadata(self):
        _require(type(self) is NativeGoWriter and type(self._scope) is _GoWriterScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.commitment) is NativeGoCommitment
                 and NativeGoCommitment._metadata(s.commitment) is s.signed_scope
                 and s.commitment._complete is True and s.commitment._failed is False
                 and s.commitment._writer is self and s.commitment._writer_snapshot is self
                 and type(s.raw) is bytes and s.raw is s.commitment._raw_snapshot
                 and type(s.wire) is bytes and 0 < len(s.wire) <= 3080
                 and s.wire == s.raw + s.signed_scope.frame
                 and type(s.intent) is _GoWriteIntent
                 and s.intent.admission is s.signed_scope.admission
                 and s.intent.wire is s.signed_scope.frame and type(s.intent.token) is object)
        b = s.signed_scope.ready_scope.read_scope.write_scope
        _require(s.intent.begin is b.channel._begin_write_fact_snapshot
                 and type(s.intent.begin) is _BeginWriteFact
                 and s.intent.begin.mint is _BEGIN_WRITE_MINT and s.intent.begin.intent is b.intent
                 and s.intent.work is b.allocation
                 and b.channel._credential_go_writer is self
                 and b.channel._credential_go_writer_snapshot is self
                 and b.channel._go_write_intent is s.intent
                 and b.channel._go_write_intent_snapshot is s.intent
                 and self._offset is self._offset_snapshot and type(self._offset) is int
                 and 0 <= self._offset <= len(s.wire)
                 and self._waiter is self._waiter_origin
                 and self._fact is self._fact_snapshot
                 and all(type(v) is bool for v in (self._attempted, self._active, self._inflight,
                                                   self._failed, self._unknown, self._complete)))
        writing = self._active
        cancel_writer = getattr(b.channel, "_credential_cancel_writer_snapshot", None)
        if self._complete and self._active is False and cancel_writer is not None:
            from .presentation_credential_cancel_write import NativeCancelWriter
            _require(type(cancel_writer) is NativeCancelWriter)
            writing = NativeCancelWriter._go_writing(cancel_writer, self)
        _require(b.channel._writing is writing)
        if self._complete:
            _require(type(self._fact) is _GoWriteFact and self._fact.mint is _GO_WRITE_MINT
                     and self._fact.intent is s.intent and self._offset == len(s.wire)
                     and b.channel._go_write_fact is self._fact
                     and b.channel._go_write_fact_snapshot is self._fact)
        else:
            _require(self._fact is None and b.channel._go_write_fact is None
                     and b.channel._go_write_fact_snapshot is None)
        return s

    def _intent_current(self):
        s = NativeGoWriter._metadata(self)
        signed = s.signed_scope
        b = signed.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and self._failed is False and self._unknown is False)
        _require(NativeGoCommitment._material_guard(s.commitment) is signed)
        r, fact = signed.ready_scope.read_scope, signed.ready_scope.read_fact
        ready = check_commitment(fact.raw, sender_public=r.pins[0], receiver_public=r.pins[1],
                                 expected=dict(r.expected))
        check_complete_frame(ready, fact.frame, binding=b.intent.binding)
        checked = check_commitment(s.raw, sender_public=signed.pins[0],
                                   receiver_public=signed.pins[1], expected=dict(signed.expected))
        check_complete_frame(checked, signed.frame, binding=b.intent.binding)
        _require(NativeGoCommitment._material_guard(s.commitment) is signed)
        fd = _FILENO(b.sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == b.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                     == b.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(b.sock) == 0.0
                 and os.get_inheritable(fd) is False
                 and NativeGoWriter._metadata(self) is s)
        return s

    def _guard(self):
        s = NativeGoWriter._intent_current(self)
        _require(self._complete is False)
        return s

    def current_written(self):
        s = NativeGoWriter._metadata(self)
        _require(self._complete is True and self._failed is False and self._active is False)
        NativeGoWriter._settled(self)
        _require(NativeGoWriter._intent_current(self) is s)
        return self._fact_snapshot  # original native write proof, never execution

    def current_sent(self):
        s = NativeGoWriter._metadata(self)
        _require(self._complete is True and self._failed is False and self._active is False)
        NativeGoWriter._settled(self)
        signed = s.signed_scope
        b = signed.ready_scope.read_scope.write_scope
        _require(NativeGoCommitment._sent_guard(s.commitment) is signed)
        r, fact = signed.ready_scope.read_scope, signed.ready_scope.read_fact
        ready = check_commitment(fact.raw, sender_public=r.pins[0], receiver_public=r.pins[1],
                                 expected=dict(r.expected))
        check_complete_frame(ready, fact.frame, binding=b.intent.binding)
        checked = check_commitment(s.raw, sender_public=signed.pins[0],
                                   receiver_public=signed.pins[1], expected=dict(signed.expected))
        check_complete_frame(checked, signed.frame, binding=b.intent.binding)
        _require(NativeGoCommitment._sent_guard(s.commitment) is signed
                 and NativeGoWriter._metadata(self) is s)
        return self._fact_snapshot  # GO_SENT is local transmission, no broker receipt

    def _settled(self):
        NativeGoWriter._metadata(self)
        _require(self._inflight is False and self._unknown is False)
        if self._waiter_origin is not None:
            waiter = self._waiter_origin
            _require(type(waiter) is SelectorWriteReadiness)
            SelectorReadiness._guard(waiter, actor=False)
            _require(waiter._retired is True and waiter._unknown is False)

    async def write_go(self):
        s = NativeGoWriter._metadata(self)
        b = s.signed_scope.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and self._attempted is False and self._failed is False
                 and self._complete is False and self._active is False)
        self._attempted = self._active = True
        b.channel._writing = True
        try:
            while self._offset < len(s.wire):
                _require(NativeGoWriter._guard(self) is s)
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
                    await SelectorReadiness.wait(waiter, b.intent.end_ns)
                    NativeGoWriter._settled(self)
                    continue
                _require(type(count) is int and 0 <= count <= len(data))
                same = (self._scope is s and self._scope_snapshot is s
                        and self._offset is before and self._offset_snapshot is before
                        and self._inflight is True)
                self._offset = self._offset_snapshot = before + count
                self._inflight = False
                if not same:
                    self._unknown = True
                    raise FrameError("BI1_CREDENTIAL_GO_WRITE_STATE_UNKNOWN")
                _require(count > 0 and NativeGoWriter._guard(self) is s)
            _require(NativeGoWriter._guard(self) is s)
            NativeGoWriter._settled(self)
            _require(NativeGoWriter._guard(self) is s)
            fact = _GoWriteFact(_GO_WRITE_MINT, s.intent)
            self._fact = self._fact_snapshot = fact
            b.channel._go_write_fact = b.channel._go_write_fact_snapshot = fact
            self._complete = True
        except BaseException:
            self._failed = True
            raise
        finally:
            try:
                NativeGoWriter._settled(self)
                self._active = False
                b.channel._writing = False
            except BaseException:
                self._unknown = True

    def _released(self, channel):
        """Historical local IO after actual original work join; never remote credit."""
        s = NativeGoWriter._metadata(self)
        b = s.signed_scope.ready_scope.read_scope.write_scope
        _require(channel is b.channel and _TASK.done(b.allocation.task)
                 and self._active is False and channel._writing is False)
        cleanup = b.refs[0]
        _require(type(cleanup) is RemoteCleanupOwner
                 and b.remote._cleanup_owner is cleanup
                 and b.remote._cleanup_owner_snapshot is cleanup
                 and type(cleanup._allocations_snapshot) is tuple
                 and len(cleanup._allocations_snapshot) == 2
                 and cleanup._allocations is cleanup._allocations_snapshot
                 and cleanup._allocations_snapshot[1] is b.allocation)
        NativeGoWriter._settled(self)
        # The held scope/fact proof above is historical local IO only. Do not
        # invoke the old live native helper or follow unsealed cleanup metadata.
