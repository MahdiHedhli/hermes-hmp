"""Fixed signed BEGIN transport on the original native work allocation.

Source-only; no production caller, READY reader, worker GO or resource admission.
The same previously reserved native intent survives every write/failure boundary.
"""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import stat
import threading
from typing import NamedTuple

from .presentation_broker_codec import BrokerFrame, BrokerHeader, encode_frame
from .presentation_broker_service import (
    _BEGIN_WRITE_MINT,
    SocketChannel,
    _BeginWriteFact,
    _BeginWriteIntent,
)
from .presentation_credential_phase import check_commitment, check_complete_frame
from .presentation_credential_scope import derive_input_scope
from .presentation_credential_transcript import check_transcript
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import INPUT_LIMIT, FrameError
from .presentation_readiness import SelectorReadiness, SelectorWriteReadiness
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _TASK, RemoteCleanupOwner, _TaskAllocation, _TaskSlot

_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_PACKET_LIMIT = INPUT_LIMIT + 4
_LIMIT = 2048 + 8 + 1024 + _PACKET_LIMIT
_SIGNED_BEGIN_WRITE_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_BEGIN_WRITE_REFUSED")


class _BeginWriterScope(NamedTuple):
    producer: object
    refs: tuple
    remote: object
    channel: object
    sock: object
    intent: _BeginWriteIntent
    raw: bytes
    frame: BrokerFrame
    frame_bytes: bytes
    wire: bytes
    allocation: object
    loop: object
    context: tuple

    def __repr__(self):
        return "<BeginWriterScope original-work signed-wire-redacted>"


class _SignedBeginWriteComplete(NamedTuple):
    mint: object
    owner: object
    scope: _BeginWriterScope
    native: _BeginWriteFact
    count: int

    def __repr__(self):
        return "<SignedBeginWriteComplete no-GO redacted>"


class NativeBeginWriter:
    """One original native work-task write; never another reserve/authorize-send."""

    @classmethod
    def retain(cls, producer):
        _require(cls is NativeBeginWriter and type(producer) is NativePhaseWorkOwner)
        _require(type(producer._refs) is tuple and len(producer._refs) == 12
                 and producer._refs is producer._refs_snapshot)
        refs = producer._refs_snapshot
        cleanup, remote, allocation, slot, channel = refs[0], refs[1], refs[6], refs[7], refs[10]
        _require(type(cleanup) is RemoteCleanupOwner and type(remote) is RemoteOperationOwner
                 and type(allocation) is _TaskAllocation and type(allocation.task) is _TASK
                 and type(slot) is _TaskSlot and type(channel) is SocketChannel
                 and type(cleanup._caller_snapshot) is _TASK
                 and type(cleanup._loop_snapshot) is asyncio.SelectorEventLoop
                 and asyncio.get_running_loop() is cleanup._loop_snapshot
                 and asyncio.current_task() is allocation.task
                 and _TASK.get_loop(allocation.task) is cleanup._loop_snapshot
                 and _TASK.get_coro(allocation.task) is allocation.coroutine
                 and _TASK.cancelling(allocation.task) == 0
                 and _TASK.cancelling(cleanup._caller_snapshot) == 0
                 and producer._cleanup is cleanup and producer._ready is True
                 and cleanup._credential_work is producer
                 and cleanup._credential_work_snapshot is producer
                 and cleanup._remote is remote and cleanup._remote_snapshot is remote
                 and type(cleanup._allocations_snapshot) is tuple
                 and len(cleanup._allocations_snapshot) == 2
                 and cleanup._allocations is cleanup._allocations_snapshot
                 and cleanup._allocations_snapshot[1] is allocation
                 and type(cleanup._slots_snapshot) is tuple and len(cleanup._slots_snapshot) == 2
                 and cleanup._slots is cleanup._slots_snapshot
                 and cleanup._slots_snapshot[1] is slot
                 and slot.task is allocation.task and slot.task_snapshot is allocation.task
                 and slot.coroutine is allocation.coroutine
                 and slot.coroutine_snapshot is allocation.coroutine
                 and remote._channel is channel and remote._channel_snapshot is channel
                 and remote._cleanup_owner is cleanup and remote._cleanup_owner_snapshot is cleanup
                 and type(producer._context) is tuple and len(producer._context) == 3
                 and producer._context is producer._context_snapshot
                 and all(type(v) is int for v in producer._context)
                 and producer._context == (os.getpid(), os.geteuid(), threading.get_ident()))
        intent = producer._intent_snapshot
        _require(type(intent) is _BeginWriteIntent and producer._intent is intent
                 and channel._begin_write_intent is intent
                 and channel._begin_write_intent_snapshot is intent
                 and type(intent.packet) is bytes and len(intent.packet) <= _PACKET_LIMIT)
        _require(producer._attempted is True and producer._failed is False
                 and type(producer._record) is bytes
                 and producer._record is producer._record_snapshot
                 and producer._intent is intent and producer._intent_snapshot is intent
                 and producer._writer is None and producer._writer_snapshot is None
                 and channel._credential_begin_writer is None
                 and channel._credential_begin_writer_snapshot is None)
        frame = BrokerFrame(BrokerHeader(intent.binding, "BEGIN", 0, len(intent.packet), 2),
                            intent.packet)
        encoded = encode_frame(intent.binding, "BEGIN", 0, intent.packet, version=2)
        scope = _BeginWriterScope(producer, refs, remote, channel, intent.socket,
                                  intent, producer._record, frame, encoded,
                                  producer._record + encoded, refs[6], refs[0]._loop_snapshot,
                                  (os.getpid(), os.geteuid(), threading.get_ident()))
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = scope
        owner._attempted = owner._active = owner._inflight = False
        owner._failed = owner._unknown = owner._complete = False
        owner._completion_attempted = False
        owner._offset = owner._offset_snapshot = 0
        owner._waiter = owner._waiter_origin = None
        owner._ready_receiver = owner._ready_receiver_snapshot = None
        owner._completion = owner._completion_snapshot = None
        producer._writer = producer._writer_snapshot = owner
        channel._credential_begin_writer = channel._credential_begin_writer_snapshot = owner
        try:
            NativeBeginWriter._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_BEGIN_WRITER_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<NativeBeginWriter original-work progress-redacted>"

    def _metadata(self):
        _require(type(self) is NativeBeginWriter and type(self._scope) is _BeginWriterScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.producer) is NativePhaseWorkOwner
                 and type(s.refs) is tuple and len(s.refs) == 12
                 and s.producer._refs is s.refs and s.producer._refs_snapshot is s.refs
                 and type(s.remote) is RemoteOperationOwner
                 and type(s.channel) is SocketChannel and type(s.sock) is socket.socket
                 and type(s.intent) is _BeginWriteIntent
                 and type(s.intent.packet) is bytes and len(s.intent.packet) <= _PACKET_LIMIT
                 and type(s.intent.token) is object and type(s.frame) is BrokerFrame
                 and type(s.frame.header) is BrokerHeader
                 and type(s.allocation) is _TaskAllocation and type(s.allocation.task) is _TASK
                 and type(s.loop) is asyncio.SelectorEventLoop
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context)
                 and s.context == (os.getpid(), os.geteuid(), threading.get_ident())
                 and asyncio.get_running_loop() is s.loop
                 and _TASK.get_loop(s.allocation.task) is s.loop
                 and _TASK.get_coro(s.allocation.task) is s.allocation.coroutine
                 and s.refs[6] is s.allocation and s.refs[1] is s.remote
                 and s.refs[10] is s.channel
                 and s.producer._writer is self and s.producer._writer_snapshot is self
                 and s.channel._credential_begin_writer is self
                 and s.channel._credential_begin_writer_snapshot is self
                 and s.channel._socket is s.sock and s.channel._socket_snapshot is s.sock
                 and s.remote._channel_snapshot is s.channel
                 and s.channel._remote_owner is s.remote
                 and s.channel._remote_owner_snapshot is s.remote
                 and s.channel._credential_handshake is s.refs[2]
                 and s.channel._credential_handshake_snapshot is s.refs[2]
                 and s.remote._credential_handshake is s.refs[2]
                 and s.remote._credential_handshake_snapshot is s.refs[2]
                 and s.intent.socket is s.sock and s.intent.channel is s.channel
                 and s.intent.remote is s.remote
                 and s.channel._begin_write_intent is s.intent
                 and s.channel._begin_write_intent_snapshot is s.intent
                 and s.producer._intent is s.intent and s.producer._intent_snapshot is s.intent
                 and s.producer._record is s.raw and s.producer._record_snapshot is s.raw
                 and type(s.raw) is bytes and 0 < len(s.raw) <= 2048
                 and type(s.frame_bytes) is bytes and type(s.wire) is bytes
                 and 0 < len(s.wire) <= _LIMIT and s.wire == s.raw + s.frame_bytes
                 and s.frame.body is s.intent.packet
                 and s.frame.header.binding is s.intent.binding
                 and type(s.frame.header.kind) is str
                 and type(s.frame.header.sequence) is int
                 and type(s.frame.header.body_length) is int
                 and type(s.frame.header.version) is int
                 and s.frame.header.kind == "BEGIN" and s.frame.header.sequence == 0
                 and s.frame.header.body_length == len(s.intent.packet)
                 and s.frame.header.version == 2
                 and s.frame_bytes == encode_frame(s.intent.binding, "BEGIN", 0,
                                                   s.intent.packet, version=2)
                 and self._offset is self._offset_snapshot and type(self._offset) is int
                 and 0 <= self._offset <= len(s.wire)
                 and self._waiter is self._waiter_origin
                 and self._completion is self._completion_snapshot
                 and all(type(v) is bool for v in (
                     self._attempted, self._active, self._inflight, self._failed,
                     self._unknown, self._complete, self._completion_attempted)))
        writing = self._active
        go_writer = getattr(s.channel, "_credential_go_writer_snapshot", None)
        if self._complete and self._active is False and go_writer is not None:
            from .presentation_credential_go_write import NativeGoWriter
            _require(type(go_writer) is NativeGoWriter)
            writing = NativeGoWriter._begin_writing(go_writer, self)
        _require(s.channel._writing is writing)
        fact = self._completion_snapshot
        if self._complete:
            _require(type(fact) is _SignedBeginWriteComplete
                     and fact.mint is _SIGNED_BEGIN_WRITE_MINT and fact.owner is self
                     and fact.scope is s and type(fact.count) is int
                     and fact.count == self._offset == len(s.wire)
                     and type(fact.native) is _BeginWriteFact
                     and fact.native.mint is _BEGIN_WRITE_MINT
                     and fact.native.intent is s.intent and self._completion_attempted is True
                     and s.channel._begin_write_fact is fact.native
                     and s.channel._begin_write_fact_snapshot is fact.native)
        else:
            _require(fact is None and s.channel._begin_write_fact is None
                     and s.channel._begin_write_fact_snapshot is None)
        return s

    def _producer_active(self, producer):
        s = NativeBeginWriter._metadata(self)
        _require(s.producer is producer and self._failed is False and self._unknown is False
                 and asyncio.current_task() is s.allocation.task)
        if self._active:
            _require(self._attempted is True and self._complete is False)
        return self._active

    def _guard(self):
        s = NativeBeginWriter._metadata(self)
        _require(self._failed is False and self._unknown is False and self._complete is False
                 and asyncio.current_task() is s.allocation.task)
        remote, _handshake, intent = NativePhaseWorkOwner._guard(s.producer)
        _require(remote is s.remote and intent is s.intent
                 and NativeBeginWriter._metadata(self) is s)
        # Last concrete nonblocking/descriptor check follows peer/clock hooks.
        fd = _FILENO(s.sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == s.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                     == s.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(s.sock) == 0.0
                 and os.get_inheritable(fd) is False)
        _require(NativeBeginWriter._metadata(self) is s)
        return s

    def _settled(self):
        NativeBeginWriter._metadata(self)
        _require(self._inflight is False and self._unknown is False)
        waiter = self._waiter_origin
        if waiter is not None:
            _require(type(waiter) is SelectorWriteReadiness)
            SelectorReadiness._guard(waiter, actor=False)
            _require(waiter._retired is True and waiter._unknown is False)

    async def write_begin(self):
        s = NativeBeginWriter._metadata(self)
        _require(asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0
                 and self._failed is False and self._unknown is False
                 and self._complete is False and self._attempted is False and self._active is False
                 and self._completion_attempted is False and self._completion is None)
        self._attempted = self._active = True
        s.channel._writing = True
        try:
            NativeBeginWriter._guard(self)
            producer = s.producer
            transcript = check_transcript(producer._records,
                gateway_public=s.refs[5].own_public, broker_public=s.refs[5].peer_public,
                expected_context=dict(producer._common))
            scope = derive_input_scope(s.intent.packet, s.intent.binding)
            expected = dict(producer._common)
            expected.pop("clock_domain")
            expected.update(phase="BEGIN", role="gateway", direction="g2b", sequence=0,
                gateway_boot=transcript.gateway_boot, broker_boot=transcript.broker_boot,
                channel=transcript.channel, transcript_sha256=transcript.transcript_sha256,
                input_sha256=scope.input_sha256, scope_sha256=scope.scope_sha256)
            checked = check_commitment(s.raw, sender_public=s.refs[5].own_public,
                                       receiver_public=s.refs[5].peer_public, expected=expected)
            check_complete_frame(checked, s.frame_bytes, binding=s.intent.binding)
            while self._offset < len(s.wire):
                _require(NativeBeginWriter._guard(self) is s and self._inflight is False)
                before = self._offset
                data = s.wire[before:]
                self._inflight = True
                try:
                    count = _SEND(s.sock, data)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._scope is s and self._scope_snapshot is s
                             and self._offset is before and self._offset_snapshot is before
                             and self._inflight is True)
                    self._inflight = False
                    waiter = SelectorWriteReadiness.__new__(SelectorWriteReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorWriteReadiness.__init__(waiter, s.sock)
                    await SelectorReadiness.wait(waiter, s.intent.end_ns)
                    NativeBeginWriter._settled(self)
                    _require(NativeBeginWriter._guard(self) is s)
                    continue
                _require(type(count) is int and 0 <= count <= len(data))
                same = (self._scope is s and self._scope_snapshot is s
                        and self._offset is before and self._offset_snapshot is before
                        and self._inflight is True)
                self._offset = self._offset_snapshot = before + count
                self._inflight = False
                if not same:
                    self._unknown = True
                    raise FrameError("BI1_CREDENTIAL_BEGIN_WRITE_STATE_UNKNOWN")
                _require(count > 0)
                _require(NativeBeginWriter._guard(self) is s)
            _require(NativeBeginWriter._guard(self) is s)
            self._completion_attempted = True
            RemoteOperationOwner._authorize_send_completion(
                s.remote, s.channel, s.frame, s.intent.end_ns)
            _require(NativeBeginWriter._guard(self) is s)
            native = _BeginWriteFact(_BEGIN_WRITE_MINT, s.intent)
            self._completion = self._completion_snapshot = _SignedBeginWriteComplete(
                _SIGNED_BEGIN_WRITE_MINT, self, s, native, self._offset)
            s.channel._begin_write_fact = s.channel._begin_write_fact_snapshot = native
            self._complete = True
        except BaseException:
            self._failed = True
            raise
        finally:
            try:
                NativeBeginWriter._settled(self)
                self._active = False
                s.channel._writing = False
            except BaseException:
                self._unknown = True

    def _released(self, channel):
        """Historical local IO only after original work task joined; no remote credit."""
        s = NativeBeginWriter._metadata(self)
        _require(channel is s.channel and self._active is False
                 and channel._writing is False and _TASK.done(s.allocation.task))
        NativeBeginWriter._settled(self)
