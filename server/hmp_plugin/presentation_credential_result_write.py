"""Original-service counted signed RESULT delivery; never terminal/publication."""
from __future__ import annotations

import asyncio
import errno
import os
import socket
from contextlib import suppress
from typing import NamedTuple

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_codec import BrokerFrame, decode_header
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_service import SocketChannel
from .presentation_cancel_budget import CancellationBudget
from .presentation_credential_ready import CredentialReadyWriter
from .presentation_credential_result import CredentialResultProducer, _ResultScope
from .presentation_jobs import OUTPUT_LIMIT, FrameError
from .presentation_readiness import SelectorReadiness, SelectorWriteReadiness
from .presentation_remote_cleanup import _TASK, _TaskAllocation

_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_RESULT_WRITE_REFUSED")


class _WriteScope(NamedTuple):
    producer: object
    result_scope: object
    channel: object
    sock: object
    ready: object
    task: object
    raw: bytes
    header: bytes
    length: int
    digest: str

    def __repr__(self):
        return "<SignedResultWriteScope payload-free redacted>"


class _ResultTransfer(NamedTuple):
    mint: object
    owner: object
    scope: _WriteScope
    count: int

    def __repr__(self):
        return "<SignedResultTransfer local-write-only redacted>"


class CredentialResultWriter:
    @classmethod
    def retain(cls, producer):
        _require(cls is CredentialResultWriter and type(producer) is CredentialResultProducer)
        s = CredentialResultProducer._local(producer)
        _require(asyncio.current_task() is s.refs[15] and _TASK.cancelling(s.refs[15]) == 0)
        f = producer._frozen_snapshot
        _require(producer._complete is True and producer._writer is None
                 and producer._writer_snapshot is None)
        channel = s.refs[14]
        ready = s.relay_fact.scope.ready_writer
        _require(type(channel) is SocketChannel and type(ready) is CredentialReadyWriter
                 and channel._credential_result_writer is None
                 and channel._credential_result_writer_snapshot is None
                 and channel._writing is False)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _WriteScope(
            producer, s, channel, channel._socket_snapshot, ready, s.refs[15],
            f.raw, f.header, len(f.payload), f.frame_sha)
        owner._payload = owner._payload_snapshot = f.payload
        owner._attempted = owner._active = owner._inflight = False
        owner._failed = owner._unknown = owner._complete = owner._retired = False
        owner._cancel_requested = owner._grammar_attempted = False
        owner._offset = owner._offset_snapshot = 0
        owner._waiter = owner._waiter_origin = None
        owner._fact = owner._fact_snapshot = None
        producer._writer = producer._writer_snapshot = owner
        channel._credential_result_writer = channel._credential_result_writer_snapshot = owner
        failed = False
        try:
            CredentialResultWriter._current(owner)
        except BaseException:
            failed = True
            owner._failed = owner._retired = True
            owner._payload = owner._payload_snapshot = None
            CredentialResultProducer.release_after_write(producer, owner)
        finally:
            f = None
        if failed:
            raise FrameError("BI1_CREDENTIAL_RESULT_WRITER_ACQUISITION_REFUSED") from None
        return owner

    def __repr__(self):
        return "<CredentialResultWriter progress-redacted>"

    def _ready_writing(self, ready):
        """Pure exact historical READY-to-RESULT write-slot handoff."""
        _require(type(self) is CredentialResultWriter and type(self._scope) is _WriteScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.producer) is CredentialResultProducer
                 and type(s.result_scope) is _ResultScope
                 and s.producer._writer is self and s.producer._writer_snapshot is self
                 and s.producer._scope_snapshot is s.result_scope
                 and type(s.ready) is CredentialReadyWriter and s.ready is ready
                 and type(s.channel) is SocketChannel
                 and s.channel._credential_result_writer is self
                 and s.channel._credential_result_writer_snapshot is self
                 and s.result_scope.relay_fact.scope.ready_writer is ready
                 and s.result_scope.refs[14] is s.channel and type(self._active) is bool)
        return self._active

    def _local(self):
        _require(type(self) is CredentialResultWriter and type(self._scope) is _WriteScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(CredentialResultWriter._ready_writing(self, s.ready) is self._active
                 and type(s.sock) is socket.socket
                 and s.channel._socket is s.sock and s.channel._socket_snapshot is s.sock
                 and type(s.task) is _TASK and s.task is s.result_scope.refs[15]
                 and asyncio.current_task() is s.task and _TASK.cancelling(s.task) == 0
                 and type(s.raw) is bytes and 0 < len(s.raw) <= 2048
                 and type(s.header) is bytes and 8 < len(s.header) <= 1032
                 and type(s.length) is int and 4 <= s.length <= OUTPUT_LIMIT
                 and type(s.digest) is str and len(s.digest) == 64
                 and self._payload is self._payload_snapshot
                 and type(self._payload) is bytes and len(self._payload) == s.length
                 and type(self._offset) is int and self._offset is self._offset_snapshot
                 and 0 <= self._offset <= len(s.raw) + len(s.header) + s.length
                 and self._waiter is self._waiter_origin
                 and self._fact is self._fact_snapshot
                 and all(type(v) is bool for v in (
                     self._attempted, self._active, self._inflight, self._failed,
                     self._unknown, self._complete, self._retired, self._cancel_requested,
                     self._grammar_attempted))
                 and self._failed is False and self._unknown is False
                 and self._retired is False and s.channel._writing is self._active)
        if self._complete:
            f = self._fact_snapshot
            _require(type(f) is _ResultTransfer and f.mint is _MINT and f.owner is self
                     and f.scope is s and type(f.count) is int and f.count == self._offset
                     and self._offset == len(s.raw) + len(s.header) + s.length)
        else:
            _require(self._fact_snapshot is None)
        return s

    def _current(self):
        s = CredentialResultWriter._local(self)
        _require(CredentialResultProducer._current(s.producer) is s.result_scope)
        f = s.producer._frozen_snapshot
        _require(f is not None and f.raw is s.raw and f.header is s.header
                 and f.payload is self._payload_snapshot and f.frame_sha == s.digest)
        SocketChannel._check(s.channel)
        _require(CredentialResultWriter._local(self) is s)
        # Last callbacks must not leave a stale key/control/actor or descriptor.
        _require(CredentialResultProducer._current(s.producer) is s.result_scope)
        fd = _FILENO(s.sock)
        row = os.fstat(fd)
        _require(fd == s.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, row.st_mode & 0o170000)
                     == s.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(s.sock) == 0.0
                 and os.get_inheritable(fd) is False)
        _require(CredentialResultProducer._tail(s.producer) is s.result_scope
                 and CredentialResultWriter._local(self) is s)
        return s

    def withdraw_from_producer(self, producer):
        """Pure payload withdrawal, no task cancellation or authority acquisition."""
        if (type(self) is CredentialResultWriter and type(self._scope_snapshot) is _WriteScope
                and self._scope is self._scope_snapshot
                and self._scope_snapshot.producer is producer
                and type(producer) is CredentialResultProducer
                and producer._writer is self and producer._writer_snapshot is self
                and producer._retired is True):
            self._retired = True
            self._payload = self._payload_snapshot = None

    def retire_from_control(self, control):
        s = self._scope_snapshot
        if (type(s) is not _WriteScope or self._scope is not s
                or type(s.result_scope) is not _ResultScope
                or s.result_scope.control is not control
                or type(control) is not BrokerCancellationOwner
                or self._retired is not True or self._active is not True
                or self._complete is not False or self._failed is not False
                or self._cancel_requested is not False
                or type(s.task) is not _TASK or _TASK.done(s.task)
                or type(control._allocation_snapshot) is not _TaskAllocation
                or asyncio.current_task() is not control._allocation_snapshot.task
                or s.channel._credential_result_writer_snapshot is not self
                or s.channel._credential_result_writer is not self):
            return
        _, _, end, failed = CancellationBudget.inspect(s.result_scope.refs[17])
        if end is None and failed is not True:
            return
        self._cancel_requested = True
        _TASK.cancel(s.task)

    def _settled(self):
        _require(self._inflight is False and self._unknown is False)
        w = self._waiter_origin
        if w is not None:
            _require(type(w) is SelectorWriteReadiness and self._waiter is w)
            SelectorReadiness._guard(w, actor=False)
            _require(w._retired is True and w._unknown is False)

    async def send(self):
        held = chunk = None
        failed = cancelled = False
        s = CredentialResultWriter._local(self)
        _require(self._attempted is False and self._active is False)
        self._attempted = self._active = True
        s.channel._writing = True
        try:
            _require(CredentialResultWriter._current(self) is s)
            header = decode_header(s.header, expected=s.result_scope.refs[4].binding,
                                   expected_version=2)
            self._grammar_attempted = True
            OperationGrammar.observe(s.result_scope.refs[18],
                BrokerFrame(header, self._payload_snapshot), sender="broker")
            _require(CredentialResultWriter._current(self) is s)
            held = self._payload_snapshot
            total = len(s.raw) + len(s.header) + s.length
            while self._offset < total:
                _require(CredentialResultWriter._current(self) is s and self._payload is held)
                before = self._offset
                if before < len(s.raw):
                    chunk = s.raw[before:]
                elif before < len(s.raw) + len(s.header):
                    chunk = s.header[before - len(s.raw):]
                else:
                    offset = before - len(s.raw) - len(s.header)
                    chunk = memoryview(held)[offset:offset + 65536]
                _require(CredentialResultWriter._current(self) is s and self._payload is held)
                self._inflight = True
                try:
                    count = _SEND(s.sock, chunk)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._offset is before and self._offset_snapshot is before
                             and self._inflight is True)
                    self._inflight = False
                    chunk = None
                    waiter = SelectorWriteReadiness.__new__(SelectorWriteReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorWriteReadiness.__init__(waiter, s.sock)
                    await SelectorReadiness.wait(waiter, s.result_scope.refs[4].deadline_ns)
                    CredentialResultWriter._settled(self)
                    continue
                _require(type(count) is int and 0 <= count <= len(chunk))
                same = (self._offset is before and self._offset_snapshot is before
                        and self._scope is s and self._scope_snapshot is s
                        and self._inflight is True)
                self._offset = self._offset_snapshot = before + count
                self._inflight = False
                chunk = None
                if not same:
                    self._unknown = True
                    raise FrameError("BI1_CREDENTIAL_RESULT_WRITE_STATE_UNKNOWN")
                _require(count > 0)
                _require(CredentialResultWriter._current(self) is s and self._payload is held)
            _require(CredentialResultWriter._current(self) is s and self._payload is held)
            CredentialResultWriter._settled(self)
            _require(CredentialResultWriter._current(self) is s and self._payload is held)
            # No native/callback boundary remains before this tentative local fact.
            self._fact = self._fact_snapshot = _ResultTransfer(_MINT, self, s, self._offset)
            self._complete = True
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            if failed:
                self._failed = True
                if self._inflight:
                    self._unknown = True
                with suppress(BaseException):
                    BrokerCancellationOwner._local_cause(s.result_scope.control)
            CredentialResultProducer.release_after_write(s.producer, self)
            held = chunk = None
            self._payload = self._payload_snapshot = None
            try:
                if failed:
                    CredentialResultWriter._settled(self)
                # Success settled before its final current fence and fact.
                # No native callbacks remain after completion publication.
                self._active = False
                s.channel._writing = False
            except BaseException:
                self._unknown = True
                failed = True
                self._failed = True
                self._complete = False
                self._fact = self._fact_snapshot = None
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_CREDENTIAL_RESULT_DELIVERY_REFUSED") from None
        return self._fact_snapshot  # local counted delivery only; never terminal ACK
