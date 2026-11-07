"""Original-task signed RESULT envelope cursor, never a completed image result.

Only bounded HBA1 and outer header reads. Body/native validation and cleanup
continuation remain separate; no production caller or publication is enabled.
"""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import stat
import threading
from typing import NamedTuple

from .presentation_broker_codec import HEADER_LIMIT, BrokerHeader, encode_header, header_size
from .presentation_broker_service import SocketChannel
from .presentation_clock import NativeClockOwner
from .presentation_credential_begin_write import _BeginWriterScope
from .presentation_credential_codec import RECORD_LIMIT, payload_size
from .presentation_credential_files import RoleKeySelection
from .presentation_credential_go_write import NativeGoWriter, _GoWriterScope
from .presentation_credential_phase import (
    _EXPECTED,
    check_commitment,
    check_committed_header,
)
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import OUTPUT_LIMIT, FrameError, RemotePhase, State, _Job
from .presentation_readiness import (
    _CANCEL_RETIREMENT_MINT,
    SelectorReadiness,
    _CancelledWaitRetirement,
    _ReadinessCancelledError,
)
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _TASK

_RECV = socket.socket.recv
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_LIMIT = RECORD_LIMIT + 8 + HEADER_LIMIT
_RESULT_READ_MINT = object()
_RESULT_CANCEL_MINT = object()


class _ResultWaitRetirement(NamedTuple):
    mint: object
    scope: object
    readiness: object
    consumed: int
    target: int
    values: bytes

    def __repr__(self):
        return "<ResultWaitRetirement local-only redacted>"


class _ResultReadRetirement(NamedTuple):
    mint: object
    scope: object
    readiness: object
    consumed: int
    target: int

    def __repr__(self):
        return "<ResultReadRetirement payload-free local-only>"


class _OwnedResultWaitCancelled(asyncio.CancelledError):
    def __init__(self, receipt):
        super().__init__()
        self.receipt = receipt



def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_RESULT_READ_REFUSED")


class _ResultReadScope(NamedTuple):
    owner: object
    writer: object
    write_scope: _BeginWriterScope
    go_scope: _GoWriterScope
    expected: tuple
    pins: tuple
    buffer: bytearray

    def __repr__(self):
        return "<ResultReadScope original-work redacted>"


class _ResultReadComplete(NamedTuple):
    mint: object
    owner: object
    scope: _ResultReadScope
    raw: bytes
    frame: bytes
    header: BrokerHeader
    buffer: bytearray
    count: int
    target: int

    def __repr__(self):
        return "<ResultEnvelopeComplete no-body-validation redacted>"


class NativeResultEnvelopeReceiver:
    """One original signed envelope cursor, never a body/result adoption authority."""

    @classmethod
    def retain(cls, writer):
        _require(cls is NativeResultEnvelopeReceiver and type(writer) is NativeGoWriter)
        go_scope = NativeGoWriter._metadata(writer)
        base = go_scope.signed_scope.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is base.allocation.task
                 and _TASK.cancelling(base.allocation.task) == 0
                 and writer._complete is True and writer._failed is False
                 and writer._unknown is False and writer._active is False
                 and writer._inflight is False
                 and writer._result_receiver is None and writer._result_receiver_snapshot is None
                 and base.channel._credential_result_receiver is None
                 and base.channel._credential_result_receiver_snapshot is None
                 and base.channel._reading is False
                 and base.remote._send_completed is True and base.remote._receive_claimed is True)
        # Pure premature-phase refusal must not consume/poison the original owner.
        RemoteOperationOwner._retained_local(base.remote)
        job = base.remote._job_origin_snapshot
        _require(type(job) is _Job and job.state is State.RUNNING
                 and job.remote_phase is RemotePhase.GO_SENT and job.go_sent is True
                 and base.remote._go_admission_used is True)
        expected = dict(go_scope.signed_scope.expected)
        expected.update(phase="RESULT", role="broker", direction="b2g", sequence=1)
        owner = cls.__new__(cls)
        owner._base = owner._base_origin = base
        owner._writer = owner._writer_origin = writer
        owner._initialized = owner._started = owner._active = owner._complete = False
        owner._failed = owner._io_unknown = owner._read_intent = False
        owner._admission_attempted = True
        owner._send_joined = owner._claim_attempted = owner._claim_complete = True
        owner._buffer = owner._buffer_origin = bytearray()
        owner._buffer_values = b""
        owner._consumed = owner._consumed_origin = 0
        owner._target = owner._target_origin = 0
        owner._pending = owner._pending_origin = None
        owner._waiter = owner._waiter_origin = None
        owner._last_read = None
        owner._completion = owner._completion_origin = None
        owner._body_owner = owner._body_owner_snapshot = None
        owner._cancel_release = owner._cancel_release_origin = None
        owner._scope = owner._scope_origin = _ResultReadScope(
            owner, writer, base, go_scope, tuple(sorted(expected.items())),
            (base.refs[5].peer_public, base.refs[5].own_public), owner._buffer_origin)
        writer._result_receiver = writer._result_receiver_snapshot = owner
        base.channel._credential_result_receiver = owner
        base.channel._credential_result_receiver_snapshot = owner
        failed = False
        try:
            NativeGoWriter.current_sent(writer)
            NativeResultEnvelopeReceiver._guard(owner)
            owner._initialized = True
        except BaseException:
            owner._failed = True
            failed = True
        if failed:
            raise FrameError("BI1_CREDENTIAL_RESULT_ENVELOPE_ACQUISITION_REFUSED") from None
        return owner

    def __repr__(self):
        return "<NativeResultEnvelopeReceiver bounded-header-only cursor-redacted>"

    def _ready_reading(self, ready):
        """Pure reciprocal historical READY-to-RESULT read-claim description."""
        from .presentation_credential_go import _GoCommitmentScope
        from .presentation_credential_ready_read import NativeReadyReceiver, _ReadyReadScope
        from .presentation_credential_ready_transition import _ReadyTransitionScope

        _require(type(self) is NativeResultEnvelopeReceiver
                 and type(self._scope) is _ResultReadScope and self._scope is self._scope_origin)
        s = self._scope_origin
        _require(type(s.go_scope) is _GoWriterScope
                 and type(s.go_scope.signed_scope) is _GoCommitmentScope
                 and type(s.go_scope.signed_scope.ready_scope) is _ReadyTransitionScope
                 and type(s.go_scope.signed_scope.ready_scope.read_scope) is _ReadyReadScope
                 and type(ready) is NativeReadyReceiver
                 and s.go_scope.signed_scope.ready_scope.receiver is ready
                 and ready._scope_origin is s.go_scope.signed_scope.ready_scope.read_scope
                 and type(s.write_scope) is _BeginWriterScope
                 and ready._scope_origin.write_scope is s.write_scope
                 and type(s.writer) is NativeGoWriter
                 and s.writer._scope_snapshot is s.go_scope
                 and s.writer._result_receiver is self
                 and s.writer._result_receiver_snapshot is self
                 and type(s.write_scope.channel) is SocketChannel
                 and s.write_scope.channel._credential_result_receiver is self
                 and s.write_scope.channel._credential_result_receiver_snapshot is self
                 and type(self._active) is bool)
        return NativeResultEnvelopeReceiver._reading_claim(self)

    def _reading_claim(self):
        _require(type(self) is NativeResultEnvelopeReceiver and type(self._active) is bool)
        owner = self._body_owner_snapshot
        _require(self._body_owner is owner)
        if self._complete is True and self._active is False and owner is not None:
            from .presentation_credential_result_body import NativeResultBodyOwner
            _require(type(owner) is NativeResultBodyOwner)
            return NativeResultBodyOwner._envelope_reading(owner, self)
        return self._active  # fixed original read claim only

    def _metadata(self):
        _require(type(self) is NativeResultEnvelopeReceiver
                 and type(self._scope) is _ResultReadScope
                 and self._scope is self._scope_origin)
        s, b = self._scope_origin, self._base_origin
        _require(s.owner is self and type(s.writer) is NativeGoWriter
                 and type(b) is _BeginWriterScope and self._base is b
                 and s.write_scope is b and s.writer is self._writer is self._writer_origin
                 and type(s.go_scope) is _GoWriterScope
                 and NativeGoWriter._metadata(s.writer) is s.go_scope
                 and s.go_scope.signed_scope.ready_scope.read_scope.write_scope is b
                 and s.writer._result_receiver is self
                 and s.writer._result_receiver_snapshot is self
                 and s.writer._complete is True and s.writer._failed is False
                 and s.writer._unknown is False and s.writer._active is False
                 and s.writer._inflight is False
                 and b.channel._credential_result_receiver is self
                 and b.channel._credential_result_receiver_snapshot is self
                 and b.context == (os.getpid(), os.geteuid(), threading.get_ident())
                 and asyncio.get_running_loop() is b.loop
                 and type(s.expected) is tuple and len(s.expected) == len(_EXPECTED)
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in s.expected)
                 and {row[0] for row in s.expected} == _EXPECTED
                 and type(b.refs[5]) is RoleKeySelection
                 and type(b.refs[5].peer_public) is bytes and len(b.refs[5].peer_public) == 32
                 and type(b.refs[5].own_public) is bytes and len(b.refs[5].own_public) == 32
                 and type(s.pins) is tuple and len(s.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in s.pins)
                 and s.pins == (b.refs[5].peer_public, b.refs[5].own_public)
                 and all(type(v) is bool for v in (
                     self._initialized, self._started, self._active, self._complete, self._failed,
                     self._io_unknown, self._read_intent, self._admission_attempted,
                     self._send_joined, self._claim_attempted, self._claim_complete))
                 and type(s.buffer) is bytearray
                 and self._buffer is s.buffer and self._buffer_origin is s.buffer
                 and type(self._buffer_values) is bytes
                 and bytes(self._buffer) == self._buffer_values
                 and type(self._consumed) is int and self._consumed is self._consumed_origin
                 and type(self._target) is int and self._target is self._target_origin
                 and 0 <= len(self._buffer) <= self._consumed <= self._target <= _LIMIT
                 and self._pending is self._pending_origin
                 and self._waiter is self._waiter_origin
                 and b.channel._reading is NativeResultEnvelopeReceiver._reading_claim(self)
                 and self._completion is self._completion_origin)
        _require(self._cancel_release is self._cancel_release_origin)
        if self._cancel_release_origin is not None:
            stopped = self._cancel_release_origin
            _require(type(stopped) is _ResultReadRetirement
                     and stopped.mint is _RESULT_CANCEL_MINT and stopped.scope is s
                     and self._failed is True and self._active is False
                     and self._complete is False and self._io_unknown is False
                     and self._pending is None and self._pending_origin is None
                     and self._read_intent is False
                     and self._consumed is stopped.consumed and self._target is stopped.target
                     and len(self._buffer) == 0 and self._buffer_values == b"")
        elif self._pending is None:
            _require(len(self._buffer) == self._consumed)
        else:
            _require(type(self._pending) is bytes
                     and len(self._buffer) + len(self._pending) == self._consumed)
        if self._complete:
            fact = self._completion_origin
            _require(type(fact) is _ResultReadComplete and fact.mint is _RESULT_READ_MINT
                     and fact.owner is self and fact.scope is s
                     and fact.buffer is self._buffer_origin
                     and type(fact.raw) is bytes and type(fact.frame) is bytes
                     and type(fact.header) is BrokerHeader
                     and type(fact.header.kind) is str and fact.header.kind == "RESULT"
                     and type(fact.header.sequence) is int and fact.header.sequence == 1
                     and type(fact.header.body_length) is int
                     and 4 <= fact.header.body_length <= OUTPUT_LIMIT
                     and type(fact.header.version) is int and fact.header.version == 2
                     and fact.frame == encode_header(fact.header)
                     and type(fact.count) is int and type(fact.target) is int
                     and fact.count == fact.target == self._consumed == self._target
                     and bytes(fact.buffer) == fact.raw + fact.frame)
        else:
            _require(self._completion is None)
        expected = dict(s.go_scope.signed_scope.expected)
        expected.update(phase="RESULT", role="broker", direction="b2g", sequence=1)
        _require(s.expected == tuple(sorted(expected.items())))
        return s

    def _guard(self):
        s = NativeResultEnvelopeReceiver._metadata(self)
        b = s.write_scope
        _require(self._failed is False and self._io_unknown is False
                 and asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and self._admission_attempted is True)
        _require(NativePhaseWorkOwner._material_local(b.producer)[0] is b.remote)
        _require(NativeResultEnvelopeReceiver._metadata(self) is s)
        RemoteOperationOwner._check(b.remote, RemotePhase.GO_SENT)
        SocketChannel._check(b.channel)
        _require(SocketChannel._qualified_clock(b.channel) is b.refs[8])
        now = NativeClockOwner.sample(b.refs[8])
        _require(NativeResultEnvelopeReceiver._metadata(self) is s)
        _require(NativePhaseWorkOwner._material_local(b.producer)[0] is b.remote)
        _require(NativeResultEnvelopeReceiver._metadata(self) is s
                 and type(now) is int and 0 <= now < b.intent.end_ns
                 and b.remote._send_claimed is True
                 and b.remote._send_completed is self._send_joined
                 and b.remote._receive_claimed is self._claim_complete)
        fd = _FILENO(b.sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == b.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                     == b.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(b.sock) == 0.0
                 and os.get_inheritable(fd) is False)
        RemoteOperationOwner._result_intent_local(b.remote, b.channel, b.intent.end_ns)
        _require(NativeResultEnvelopeReceiver._metadata(self) is s)
        return s

    async def _take(self, target):
        part = values = None
        try:
            s = NativeResultEnvelopeReceiver._guard(self)
            b, original = s.write_scope, self._buffer_origin
            _require(type(target) is int and self._target <= target <= _LIMIT
                     and self._pending is None and self._read_intent is False)
            self._target = self._target_origin = target
            while len(original) < target:
                consumed, values = self._consumed_origin, bytes(original)
                _require(NativeResultEnvelopeReceiver._guard(self) is s)
                _require(self._buffer is original and self._buffer_origin is original
                         and self._target is target and self._target_origin is target
                         and self._consumed is consumed and self._consumed_origin is consumed
                         and bytes(original) == values and self._pending is None
                         and self._read_intent is False)
                wanted = target - len(original)
                self._read_intent = True
                try:
                    part = _RECV(b.sock, wanted)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._scope is s and self._scope_origin is s
                             and self._buffer is original and self._buffer_origin is original
                             and self._target is target and self._target_origin is target
                             and self._consumed is consumed and self._consumed_origin is consumed
                             and self._read_intent is True and self._pending is None)
                    self._read_intent = False
                    waiter = SelectorReadiness.__new__(SelectorReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorReadiness.__init__(waiter, b.sock)
                    origin, future = waiter._origin_scope, waiter._future_origin
                    cutoff = b.intent.end_ns
                    try:
                        await SelectorReadiness.wait(waiter, cutoff)
                    except _ReadinessCancelledError as error:
                        _require(type(error) is _ReadinessCancelledError)
                        fact = error.retirement
                        _require(type(fact) is _CancelledWaitRetirement
                                 and fact.mint is _CANCEL_RETIREMENT_MINT
                                 and fact.owner is waiter and fact.scope is origin
                                 and fact.future is future and fact.end is cutoff)
                        raise _OwnedResultWaitCancelled(_ResultWaitRetirement(
                            _RESULT_CANCEL_MINT, s, fact, consumed, target, values)) from None
                    _require(self._waiter_origin is waiter and waiter._retired is True
                             and waiter._unknown is False)
                    _require(NativeResultEnvelopeReceiver._guard(self) is s)
                    continue
                _require(type(part) is bytes and len(part) <= wanted)
                same = (self._consumed is consumed and self._consumed_origin is consumed
                        and self._scope is s and self._scope_origin is s
                        and self._pending is None and self._pending_origin is None
                        and self._read_intent is True
                        and self._target is target and self._target_origin is target)
                self._pending = self._pending_origin = part
                committed = consumed + len(part)
                self._last_read = (consumed, len(part), committed)
                self._consumed = self._consumed_origin = committed
                _require(same and NativeResultEnvelopeReceiver._guard(self) is s)
                _require(self._buffer is original and self._buffer_origin is original
                         and self._pending is part and self._pending_origin is part
                         and self._read_intent is True and bytes(original) == values
                         and len(part) > 0
                         and self._target is target and self._target_origin is target
                         and self._consumed is committed and self._consumed_origin is committed)
                bytearray.extend(original, part)
                self._buffer_values = bytes(original)
                self._pending = self._pending_origin = None
                self._read_intent = False
            return bytes(original)
        finally:
            part = values = None

    def _cancelled_wait_current(self, receipt, *, released=False):
        """Original local read retirement; no live role/work/native authority."""
        s = NativeResultEnvelopeReceiver._metadata(self)
        b = s.write_scope
        _require(type(released) is bool)
        _require(type(receipt) is (_ResultReadRetirement if released else _ResultWaitRetirement)
                 and receipt.mint is _RESULT_CANCEL_MINT and receipt.scope is s
                 and type(receipt.consumed) is int and type(receipt.target) is int
                 and self._started is True and self._complete is False
                 and self._io_unknown is False and self._read_intent is False
                 and self._pending is None and self._pending_origin is None
                 and self._consumed is receipt.consumed and self._target is receipt.target)
        if released:
            _require(self._cancel_release is receipt and self._cancel_release_origin is receipt
                     and _TASK.done(b.allocation.task) and _TASK.cancelled(b.allocation.task)
                     and self._failed is True and self._active is False)
        else:
            _require(type(receipt.values) is bytes and self._buffer_values == receipt.values
                     and bytes(s.buffer) == receipt.values and len(s.buffer) == receipt.consumed)
            _require(asyncio.current_task() is b.allocation.task
                     and _TASK.cancelling(b.allocation.task) > 0
                     and self._failed is False and self._active is True
                     and self._cancel_release is None and self._cancel_release_origin is None)
        fact = receipt.readiness
        _require(type(fact) is _CancelledWaitRetirement
                 and fact.mint is _CANCEL_RETIREMENT_MINT
                 and type(fact.owner) is SelectorReadiness
                 and self._waiter is fact.owner and self._waiter_origin is fact.owner)
        waiter = fact.owner
        SelectorReadiness._guard(waiter, actor=not released)
        SelectorReadiness._wake_guard(waiter)
        _require(waiter._origin_scope is fact.scope and waiter._scope_snapshot is fact.scope
                 and waiter._future_origin is fact.future
                 and waiter._wake_binding_origin is fact.binding
                 and waiter._handle_snapshot is fact.handle
                 and waiter._handle_args_snapshot is fact.handle_args
                 and fact.scope.sock is b.sock and fact.scope.task is b.allocation.task
                 and fact.scope.loop is b.loop and fact.scope.interest == "read"
                 and waiter._attempted is True and waiter._retired is True
                 and waiter._unknown is False and fact.binding.scope is fact.scope
                 and fact.binding.future is None and fact.binding.end is fact.end
                 and fact.end is b.intent.end_ns)
        # Guard callbacks cannot replace the original cursor or actor.
        _require(NativeResultEnvelopeReceiver._metadata(self) is s
                 and self._consumed is receipt.consumed and self._target is receipt.target
                 and self._read_intent is False
                 and self._pending is None and self._io_unknown is False)
        if not released:
            _require(type(receipt.values) is bytes and self._buffer_values == receipt.values
                     and bytes(s.buffer) == receipt.values and len(s.buffer) == receipt.consumed)
            _require(asyncio.current_task() is b.allocation.task
                     and _TASK.cancelling(b.allocation.task) > 0
                     and self._failed is False and self._active is True)
            return _ResultReadRetirement(_RESULT_CANCEL_MINT, s, fact,
                                        receipt.consumed, receipt.target)
        return receipt

    async def run(self):
        s = NativeResultEnvelopeReceiver._metadata(self)
        _require(asyncio.current_task() is s.write_scope.allocation.task
                 and self._initialized is True and self._claim_complete is True
                 and self._started is False and self._failed is False and self._io_unknown is False)
        self._started = self._active = True
        s.write_scope.channel._reading = True
        original = self._buffer_origin
        prefix = raw = framed = header = checked = None
        failed = cancelled = False
        retirement = None
        try:
            _require(NativeResultEnvelopeReceiver._guard(self) is s)
            prefix = await NativeResultEnvelopeReceiver._take(self, 8)
            raw = await NativeResultEnvelopeReceiver._take(self, 8 + payload_size(prefix))
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            _require(NativeResultEnvelopeReceiver._guard(self) is s)
            auth_end = len(raw)
            framed = await NativeResultEnvelopeReceiver._take(self, auth_end + 8)
            header_end = auth_end + 8 + header_size(framed[auth_end:])
            framed = await NativeResultEnvelopeReceiver._take(self, header_end)
            header = check_committed_header(checked, framed[auth_end:],
                                            binding=s.write_scope.intent.binding)
            _require(header.kind == "RESULT" and header.sequence == 1
                     and 4 <= header.body_length <= OUTPUT_LIMIT and header.version == 2)
            _require(NativeResultEnvelopeReceiver._guard(self) is s
                     and self._buffer_origin is original
                     and bytes(original) == framed and self._read_intent is False
                     and self._pending is None)
            self._completion = self._completion_origin = _ResultReadComplete(
                _RESULT_READ_MINT, self, s, raw, framed[auth_end:], header, original,
                self._consumed_origin, self._target_origin)
            self._complete = True
        except _OwnedResultWaitCancelled as stopped:
            failed = cancelled = True
            try:
                _require(type(stopped) is _OwnedResultWaitCancelled)
                retirement = NativeResultEnvelopeReceiver._cancelled_wait_current(
                    self, stopped.receipt)
            except BaseException:
                retirement = None
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            prefix = raw = framed = header = checked = None
            if failed:
                self._failed = True
                self._io_unknown = retirement is None
                if retirement is None:
                    bytearray.clear(original)
                    self._buffer_values = b""
                    self._pending = self._pending_origin = None
                else:
                    bytearray.clear(original)
                    self._buffer_values = b""
                    self._pending = self._pending_origin = None
                    self._cancel_release = self._cancel_release_origin = retirement
                    self._active = False
                    s.write_scope.channel._reading = False
            if self._complete and not self._io_unknown and not self._read_intent:
                self._active = False
                s.write_scope.channel._reading = False
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_CREDENTIAL_RESULT_READ_REFUSED") from None

    def current_envelope(self):
        s = NativeResultEnvelopeReceiver._metadata(self)
        _require(asyncio.current_task() is s.write_scope.allocation.task
                 and self._complete is True and self._active is False)
        try:
            _require(NativeResultEnvelopeReceiver._guard(self) is s)
            fact = self._completion_origin
            checked = check_commitment(fact.raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            header = check_committed_header(checked, fact.frame,
                                            binding=s.write_scope.intent.binding)
            _require(header.kind == "RESULT" and 4 <= header.body_length <= OUTPUT_LIMIT
                     and NativeResultEnvelopeReceiver._guard(self) is s
                     and self._completion_origin is fact)
            return fact  # authenticated envelope only, never body digest/result validation
        except BaseException:
            self._failed = True
            raise

    def _released(self, channel):
        s = NativeResultEnvelopeReceiver._metadata(self)
        if self._body_owner_snapshot is not None:
            from .presentation_credential_result_body import NativeResultBodyOwner
            _require(type(self._body_owner_snapshot) is NativeResultBodyOwner)
            NativeResultBodyOwner._released(self._body_owner_snapshot, self)
        if self._cancel_release_origin is not None:
            _require(channel is s.write_scope.channel)
            NativeResultEnvelopeReceiver._cancelled_wait_current(
                self, self._cancel_release_origin, released=True)
            return
        _require(channel is s.write_scope.channel and _TASK.done(s.write_scope.allocation.task)
                 and self._active is False and self._io_unknown is False
                 and self._read_intent is False and self._pending is None)
        waiter = self._waiter_origin
        if waiter is not None:
            _require(type(waiter) is SelectorReadiness)
            SelectorReadiness._guard(waiter, actor=False)
            _require(waiter._retired is True and waiter._unknown is False)
