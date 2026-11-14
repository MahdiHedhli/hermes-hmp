"""Counted original-service TERMINAL/2 writes; no reader, ACK or native release.

Only immediate nonblocking sends are supported. EAGAIN, partial uncertainty and
lost acknowledgements retain UNKNOWN rather than starting a fresh wait or replay.
"""
from __future__ import annotations

import asyncio
import os
import socket
from contextlib import suppress
from typing import NamedTuple

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_codec import BrokerFrame, decode_header, header_size
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_cancel_budget import CancellationBudget
from .presentation_control_binding import PreparedControlBinding
from .presentation_credential_result_write import CredentialResultWriter
from .presentation_credential_result_write import _WriteScope as ResultWriteScope
from .presentation_credential_terminal import CredentialTerminalProducer, _FrozenTerminal
from .presentation_credential_terminal import _Scope as TerminalScope
from .presentation_jobs import FrameError
from .presentation_remote_cleanup import _TASK

_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_FSTAT = os.fstat
_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_TERMINAL_WRITE_REFUSED")


class _Scope(NamedTuple):
    producer: CredentialTerminalProducer
    terminal: TerminalScope
    envelope: _FrozenTerminal
    signed: CredentialResultWriter
    channel: object
    sock: object
    identity: tuple
    task: object
    wire: bytes

    def __repr__(self):
        return "<TerminalWriteScope original-connection bounded-wire redacted>"


class _Transfer(NamedTuple):
    mint: object
    owner: object
    scope: _Scope
    count: int

    def __repr__(self):
        return "<SignedTerminalTransfer local-count-only no-ACK-or-release>"


class CredentialTerminalWriter:
    @classmethod
    def retain(cls, producer):
        _require(cls is CredentialTerminalWriter and type(producer) is CredentialTerminalProducer)
        s = CredentialTerminalProducer._metadata(producer)
        _require(asyncio.current_task() is s.refs[15] and _TASK.cancelling(s.refs[15]) == 0
                 and producer._complete is True and producer._writer is None
                 and producer._writer_origin is None and producer._writer_cell is None)
        signed, envelope = s.transfer.owner, producer._frozen_origin
        _require(type(signed) is CredentialResultWriter and type(envelope) is _FrozenTerminal
                 and signed._terminal_writer is None and signed._terminal_writer_origin is None
                 and signed._terminal_writer_cell is None)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_origin = _Scope(producer, s, envelope, signed,
            s.refs[14], s.refs[14]._socket_snapshot, s.refs[14]._identity_snapshot,
            s.refs[15], envelope.raw + envelope.frame)
        owner._scope_cell = (owner, owner._scope_origin)
        owner._attempted = owner._active = owner._inflight = False
        owner._failed = owner._unknown = owner._complete = owner._grammar_attempted = False
        owner._offset = owner._offset_origin = 0
        owner._count_cell = (owner, owner._scope_origin, 0)
        owner._fact = owner._fact_origin = owner._fact_cell = None
        owner._claim_cell = None
        producer._writer = producer._writer_origin = owner
        producer._writer_cell = (producer, owner)
        signed._terminal_writer = signed._terminal_writer_origin = owner
        signed._terminal_writer_cell = (signed, owner)
        failed = False
        try:
            CredentialTerminalWriter._current(owner)
            return owner
        except BaseException:
            owner._failed = failed = True
        if failed:
            raise FrameError("BI1_SIGNED_TERMINAL_WRITER_ACQUISITION_UNKNOWN") from None

    def __repr__(self):
        return "<CredentialTerminalWriter original-service count-redacted>"

    def writing_for_result(self, result):
        """Fixed write-slot handoff; deliberately no producer/currentness recursion."""
        _require(type(self) is CredentialTerminalWriter and type(self._scope_origin) is _Scope
                 and self._scope is self._scope_origin
                 and type(self._scope_cell) is tuple and len(self._scope_cell) == 2
                 and self._scope_cell[0] is self and self._scope_cell[1] is self._scope_origin)
        s = self._scope_origin
        _require(type(result) is CredentialResultWriter and s.signed is result
                 and type(result._scope_snapshot) is ResultWriteScope
                 and s.channel is result._scope_snapshot.channel
                 and type(s.terminal) is TerminalScope and s.terminal.transfer.owner is result
                 and result._terminal_writer is self and result._terminal_writer_origin is self
                 and type(result._terminal_writer_cell) is tuple
                 and len(result._terminal_writer_cell) == 2
                 and result._terminal_writer_cell[0] is result
                 and result._terminal_writer_cell[1] is self
                 and type(s.producer) is CredentialTerminalProducer
                 and s.producer._writer is self and s.producer._writer_origin is self
                 and type(s.producer._writer_cell) is tuple and len(s.producer._writer_cell) == 2
                 and s.producer._writer_cell[0] is s.producer
                 and s.producer._writer_cell[1] is self and type(self._active) is bool)
        return self._active

    def _local(self):
        _require(type(self) is CredentialTerminalWriter)
        s = self._scope_origin
        _require(type(s) is _Scope
                 and CredentialTerminalWriter.writing_for_result(self, s.signed) is self._active
                 and s.producer._scope_origin is s.terminal
                 and s.producer._frozen_origin is s.envelope
                 and type(s.envelope) is _FrozenTerminal
                 and type(s.wire) is bytes and s.wire == s.envelope.raw + s.envelope.frame
                 and len(s.wire) <= 2048 + 4096 + 1032
                 and type(s.identity) is tuple and len(s.identity) == 4
                 and all(type(v) is int for v in s.identity)
                 and s.channel._identity_snapshot is s.identity
                 and type(s.sock) is socket.socket
                 and s.channel._socket is s.sock and s.channel._socket_snapshot is s.sock
                 and type(s.task) is _TASK and s.task is s.terminal.refs[15]
                 and asyncio.current_task() is s.task and _TASK.cancelling(s.task) == 0
                 and all(type(v) is bool for v in (self._attempted, self._active, self._inflight,
                     self._failed, self._unknown, self._complete, self._grammar_attempted))
                 and self._failed is False and self._unknown is False
                 and s.channel._writing is self._active
                 and type(self._offset) is int and self._offset is self._offset_origin
                 and 0 <= self._offset <= len(s.wire)
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and type(self._count_cell[2]) is int and self._count_cell[2] == self._offset)
        if self._complete:
            f = self._fact_origin
            _require(type(f) is _Transfer and f.mint is _MINT and self._fact is f
                     and f.owner is self and f.scope is s and type(f.count) is int
                     and f.count == self._offset == len(s.wire)
                     and type(self._fact_cell) is tuple and len(self._fact_cell) == 2
                     and self._fact_cell[0] is self and self._fact_cell[1] is f)
        else:
            _require(self._fact is None and self._fact_origin is None and self._fact_cell is None)
        return s

    def _current(self):
        s = CredentialTerminalWriter._local(self)
        _require(CredentialTerminalProducer._current(s.producer) is s.terminal)
        fd = _FILENO(s.sock)
        _require(type(fd) is int and fd >= 0)
        row = _FSTAT(fd)
        _require(type(row) is os.stat_result and type(row.st_dev) is int
                 and type(row.st_ino) is int and type(row.st_mode) is int)
        timeout = _TIMEOUT(s.sock)
        _require(s.channel._identity_snapshot is s.identity
                 and type(s.channel._fd_snapshot) is int and fd == s.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, row.st_mode & 0o170000) == s.identity
                 and os.get_blocking(fd) is False and type(timeout) is float and timeout == 0.0
                 and os.get_inheritable(fd) is False)
        control = s.terminal.producer_scope.control
        binding = control._credential_binding_snapshot
        _require(PreparedControlBinding._creator_local(binding) is s.terminal.refs
                 and CredentialTerminalProducer._metadata(s.producer) is s.terminal
                 and CredentialTerminalWriter._local(self) is s)
        _, cause, end, broken = CancellationBudget.inspect(s.terminal.refs[17])
        _require(cause is None and end is None and broken is False
                 and control._retired is False and control._failed is False
                 and control._io_unknown is False
                 and s.terminal.producer_scope.resources._normal_complete is True
                 and s.terminal.producer_scope.resources._invalidated is False)
        return s

    async def send(self):
        s = CredentialTerminalWriter._local(self)
        _require(self._attempted is False and self._active is False)
        self._attempted = True
        self._claim_cell = (self, s, s.channel)
        claim_cell = self._claim_cell
        scope_cell, signed_cell = self._scope_cell, s.signed._terminal_writer_cell
        producer_cell = s.producer._writer_cell
        self._active = True
        s.channel._writing = True
        failed = cancelled = False
        chunk = None
        try:
            _require(CredentialTerminalWriter._current(self) is s)
            frame = s.envelope.frame
            end = 8 + header_size(frame[:8])
            header = decode_header(frame[:end], expected=s.terminal.producer_scope.record.binding,
                                   expected_version=2)
            self._grammar_attempted = True
            OperationGrammar.observe(s.terminal.refs[18], BrokerFrame(header, frame[end:]),
                                     sender="broker")
            while self._offset < len(s.wire):
                _require(CredentialTerminalWriter._current(self) is s)
                before = self._offset
                chunk = s.wire[before:before + 4096]
                self._inflight = True
                count = _SEND(s.sock, chunk)
                _require(type(count) is int and 0 < count <= len(chunk))
                same = (self._scope is s and self._scope_origin is s
                        and self._offset is before and self._offset_origin is before
                        and self._inflight is True)
                self._offset = self._offset_origin = before + count
                self._count_cell = (self, s, before + count)
                self._inflight = False
                chunk = None
                _require(same)
                _require(CredentialTerminalWriter._current(self) is s)
            _require(CredentialTerminalWriter._current(self) is s)
            fact = _Transfer(_MINT, self, s, self._offset)
            self._fact = self._fact_origin = fact
            self._fact_cell = (self, fact)
            self._complete = True
        except BaseException as error:
            cancelled = isinstance(error, asyncio.CancelledError)
            self._failed = self._unknown = failed = True
            with suppress(BaseException):
                BrokerCancellationOwner._local_cause(s.terminal.producer_scope.control)
        finally:
            chunk = None
            # Release only this original claim; do not overwrite competing ownership.
            if (self._claim_cell is claim_cell and self._scope is s and self._scope_origin is s
                    and self._scope_cell is scope_cell
                    and s.signed._terminal_writer is self
                    and s.signed._terminal_writer_origin is self
                    and s.signed._terminal_writer_cell is signed_cell
                    and s.producer._writer is self and s.producer._writer_origin is self
                    and s.producer._writer_cell is producer_cell and s.channel._writing is True):
                self._active = False
                s.channel._writing = False
            else:
                self._failed = self._unknown = failed = True
                self._complete = False
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_SIGNED_TERMINAL_DELIVERY_UNKNOWN") from None
        return self._fact_origin
