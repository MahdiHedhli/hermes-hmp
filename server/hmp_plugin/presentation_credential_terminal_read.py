"""Normal original-work TERMINAL/2 reception and correlation DATA, never release.

The RESULT candidate stays private/GO_SENT. No cleanup reservation is fabricated;
normal readiness uses the original work deadline and owns its distinct interest.
"""
from __future__ import annotations

import asyncio
import errno
import hashlib
import json
import os
import socket
from typing import NamedTuple

from .presentation_broker_codec import HEADER_LIMIT, TERMINAL_LIMIT
from .presentation_cancel_budget import CancellationBudget
from .presentation_credential_codec import RECORD_LIMIT, payload_size
from .presentation_credential_frame_discard import CommittedFrameDiscard, DiscardedFrame
from .presentation_credential_phase import _EXPECTED, ConsistentCommitment
from .presentation_credential_result_body import NativeResultBodyOwner, _BodyCandidate, _BodyScope
from .presentation_credential_stream import (
    CommittedFrameDigest,
    ConsistentFrameDigest,
    SignedCleanupAuthPrefix,
)
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError
from .presentation_readiness import SelectorReadiness
from .presentation_readiness import _Scope as ReadinessScope
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _FUTURE, _TASK
from .presentation_terminal_claim import (
    StartedClaim,
    TerminalHandoff,
    _values,
    claim_binding,
    decode_handoff,
    encode_handoff,
)

_RECV = socket.socket.recv
_FILENO = socket.socket.fileno
_FSTAT = os.fstat
_TIMEOUT = socket.socket.gettimeout
_SHA256 = hashlib.sha256
_LIMIT = RECORD_LIMIT + 8 + HEADER_LIMIT + TERMINAL_LIMIT


def _require(value):
    if value is not True:
        raise FrameError("BI1_NORMAL_TERMINAL_READ_REFUSED")


class _Scope(NamedTuple):
    body: NativeResultBodyOwner
    body_scope: _BodyScope
    candidate: _BodyCandidate
    write: object
    sock: socket.socket
    identity: tuple
    expected: tuple
    pins: tuple

    def __repr__(self):
        return "<NormalTerminalScope original-private-candidate redacted>"


class _Fact(NamedTuple):
    owner: object
    scope: _Scope
    frame: DiscardedFrame
    handoff: TerminalHandoff
    received: int

    def __repr__(self):
        return "<NormalTerminalCorrelation DATA no-acceptance-ACK-or-release>"


class NativeTerminalReceiver:
    @classmethod
    def retain(cls, body):
        _require(cls is NativeTerminalReceiver and type(body) is NativeResultBodyOwner)
        NativeResultBodyOwner._actor(body)  # wrong actor must not consume the original slot
        _require(body._terminal_reader is None and body._terminal_reader_origin is None
                 and body._terminal_reader_cell is None and body._adopted is False)
        candidate = NativeResultBodyOwner._candidate_metadata(body)
        s = body._scope_origin
        write = s.envelope_scope.write_scope
        rows = s.envelope_scope.expected
        _require(type(rows) is tuple and len(rows) == len(_EXPECTED)
                 and all(type(r) is tuple and len(r) == 2 and type(r[0]) is str
                         and type(r[1]) is (int if r[0] in ("sequence", "work_end_ns") else str)
                         for r in rows) and {r[0] for r in rows} == _EXPECTED)
        expected = dict(rows)
        _require(expected["sequence"] == 1 and expected["phase"] == "RESULT")
        expected.pop("phase")
        expected["sequence"] = 2
        owner = cls.__new__(cls)
        owner._scope = owner._scope_origin = _Scope(
            body,
            s,
            candidate,
            write,
            write.sock,
            write.channel._identity_snapshot,
            tuple(sorted(expected.items())),
            s.envelope_scope.pins,
        )
        owner._scope_cell = (owner, owner._scope_origin)
        owner._initialized = owner._attempted = owner._active = owner._failed = False
        owner._unknown = owner._inflight = owner._complete = False
        owner._received = owner._received_origin = 0
        owner._count_cell = (owner, owner._scope_origin, 0)
        owner._pending = owner._pending_cell = None
        owner._credit = owner._credit_origin = (0, 0)
        owner._credit_cell = (owner, owner._credit_origin)
        owner._feeding = owner._auth_finished = owner._frame_ready = False
        owner._auth_finish_cell = owner._checked_values = None
        owner._waiter = owner._waiter_cell = None
        owner._auth = owner._auth_cell = owner._checked = owner._checked_cell = None
        owner._auth_allocation_origin = owner._frame_allocation_origin = None
        owner._frame = owner._frame_cell = owner._fact = owner._fact_cell = None
        owner._frame_done = owner._frame_done_cell = None
        owner._fact_origin = owner._fact_cell_origin = None
        body._terminal_reader = body._terminal_reader_origin = owner
        body._terminal_reader_cell = (body, owner)
        failed = False
        try:
            NativeTerminalReceiver._current(owner)
            parser = SignedCleanupAuthPrefix.__new__(SignedCleanupAuthPrefix)
            owner._auth, owner._auth_cell = parser, (owner, parser)
            owner._auth_allocation_origin = owner._auth_cell
            original_auth_cell = owner._auth_cell
            SignedCleanupAuthPrefix.__init__(parser, b"", sender_public=owner._scope_origin.pins[0],
                receiver_public=owner._scope_origin.pins[1], expected_context=dict(expected))
            _require(owner._auth is parser and owner._auth_cell is original_auth_cell)
            owner._initialized = True
            NativeTerminalReceiver._current(owner)
            return owner
        except BaseException:
            owner._failed = failed = True
            NativeResultBodyOwner.wipe(body)
        if failed:
            raise FrameError("BI1_NORMAL_TERMINAL_ACQUISITION_UNKNOWN") from None

    def __repr__(self):
        return "<NativeTerminalReceiver original-work bounded-count redacted>"

    def reading_for_body(self, body):
        """Pure fixed read-slot handoff, no recursive body/envelope currentness."""
        _require(type(self) is NativeTerminalReceiver and type(self._scope_origin) is _Scope
                 and self._scope is self._scope_origin
                 and type(self._scope_cell) is tuple and len(self._scope_cell) == 2
                 and self._scope_cell[0] is self and self._scope_cell[1] is self._scope_origin)
        s = self._scope_origin
        _require(
            type(body) is NativeResultBodyOwner
            and s.body is body
            and body._scope_origin is s.body_scope
            and body._scope is s.body_scope
            and body._terminal_reader is self
            and body._terminal_reader_origin is self
            and type(body._terminal_reader_cell) is tuple
            and len(body._terminal_reader_cell) == 2
            and body._terminal_reader_cell[0] is body
            and body._terminal_reader_cell[1] is self
            and body._active is False
            and type(self._active) is bool
        )
        return self._active

    def _metadata(self):
        _require(type(self) is NativeTerminalReceiver and type(self._scope_origin) is _Scope)
        s = self._scope_origin
        _require(NativeTerminalReceiver.reading_for_body(self, s.body) is self._active
                 and s.write is s.body_scope.envelope_scope.write_scope
                 and s.sock is s.write.sock and s.pins is s.body_scope.envelope_scope.pins
                 and s.body._validated is True and s.body._failed is False
                 and s.body._retired is False and s.body._io_unknown is False
                 and type(s.candidate) is _BodyCandidate
                 and s.body._fact_snapshot is s.candidate and s.body._adopted is False
                 and all(type(v) is bool for v in (self._initialized, self._attempted,
                     self._active, self._failed, self._unknown, self._inflight, self._complete))
                 and self._failed is False and self._unknown is False
                 and type(self._received) is int and self._received is self._received_origin
                 and 0 <= self._received <= _LIMIT
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and type(self._count_cell[2]) is int and self._count_cell[2] == self._received
                 and type(s.identity) is tuple and len(s.identity) == 4
                 and all(type(v) is int for v in s.identity)
                 and s.write.channel._identity_snapshot is s.identity
                 and s.write.channel._socket_snapshot is s.sock
                 and s.write.channel._socket is s.sock
                 and s.write.channel._reading is self._active)
        _require(self._feeding is False and type(self._credit) is tuple
                 and len(self._credit) == 2 and self._credit is self._credit_origin
                 and all(type(v) is int and v >= 0 for v in self._credit)
                 and type(self._credit_cell) is tuple and len(self._credit_cell) == 2
                 and self._credit_cell[0] is self and self._credit_cell[1] is self._credit
                 and all(type(v) is bool for v in (self._auth_finished, self._frame_ready)))
        pending = 0
        if self._pending is None:
            _require(self._pending_cell is None)
        else:
            _require(type(self._pending) is bytes and type(self._pending_cell) is tuple
                     and len(self._pending_cell) == 3 and self._pending_cell[0] is self
                     and self._pending_cell[1] is self._pending
                     and type(self._pending_cell[2]) is int
                     and self._pending_cell[2] == self._received)
            pending = len(self._pending)
        _require(self._received == sum(self._credit) + pending)
        if self._initialized:
            auth = self._auth
            _require(type(auth) is SignedCleanupAuthPrefix and type(self._auth_cell) is tuple
                     and len(self._auth_cell) == 2 and self._auth_cell[0] is self
                     and self._auth_cell[1] is auth
                     and self._auth_cell is self._auth_allocation_origin)
            if not self._auth_finished:
                SignedCleanupAuthPrefix._guard(auth)
                _require(auth._pins_origin == s.pins and auth._expected_origin == s.expected
                         and len(auth._buffer_origin) == self._credit[0])
                if auth._header_done:
                    _require(auth._target == 8 + payload_size(bytes(auth._buffer_origin[:8])))
            else:
                c = self._checked
                cell = self._auth_finish_cell
                _require(
                    auth._finished is True
                    and auth._failed is False
                    and type(auth._buffer_origin) is bytearray
                    and len(auth._buffer_origin) == 0
                    and type(c) is ConsistentCommitment
                    and type(cell) is tuple
                    and len(cell) == 4
                    and cell[0] is self
                    and cell[1] is auth
                    and cell[2] is c
                    and type(cell[3]) is int
                    and cell[3] == self._credit[0]
                    and type(self._checked_cell) is tuple
                    and len(self._checked_cell) == 2
                    and self._checked_cell[0] is self
                    and self._checked_cell[1] is c
                    and type(c.canonical_json) is bytes
                    and type(c.frame_sha256) is str
                    and type(c.frame_length) is int
                    and type(self._checked_values) is tuple and len(self._checked_values) == 3
                    and type(self._checked_values[0]) is bytes
                    and type(self._checked_values[1]) is str
                    and type(self._checked_values[2]) is int
                    and len(c.canonical_json) + 72 == self._credit[0]
                    and (c.canonical_json, c.frame_sha256, c.frame_length) == self._checked_values
                )
            if self._frame_ready:
                frame = self._frame
                _require(type(frame) is CommittedFrameDiscard and type(self._frame_cell) is tuple
                         and len(self._frame_cell) == 2 and self._frame_cell[0] is self
                         and self._frame_cell[1] is frame
                         and self._frame_cell is self._frame_allocation_origin
                         and frame._claim_origin is self._checked)
                if frame._finished is False:
                    CommittedFrameDiscard._owned(frame)
                else:
                    data = self._frame_done
                    _require(
                        frame._finished is True
                        and frame._failed is False
                        and frame._inflight is False
                        and frame._finish_attempted is True
                        and frame._finish_returned is True
                        and type(data) is DiscardedFrame
                        and type(self._frame_done_cell) is tuple
                        and len(self._frame_done_cell) == 3
                        and self._frame_done_cell[0] is self
                        and self._frame_done_cell[1] is frame
                        and self._frame_done_cell[2] is data
                        and frame._fact is data
                        and type(frame._fact_allocation) is tuple
                        and len(frame._fact_allocation) == 2
                        and frame._fact_allocation[0] is frame
                        and frame._fact_allocation[1] is data
                        and type(data.terminal) is bytes
                        and 1 <= len(data.terminal) <= TERMINAL_LIMIT
                        and type(data.phase) is str
                        and data.phase == "TERMINAL"
                        and type(data.sequence) is int
                        and data.sequence == 2
                        and type(data.digest) is ConsistentFrameDigest
                        and frame._digest is data.digest
                        and type(data.digest.frame_sha256) is str
                        and data.digest.frame_sha256 == self._checked.frame_sha256
                        and type(data.digest.frame_length) is int
                        and data.digest.frame_length == self._credit[1]
                        and type(frame._terminal_origin) is bytearray
                        and len(frame._terminal_origin) == 0
                        and type(frame._stream_origin) is CommittedFrameDigest
                        and frame._stream_origin._finished is True
                    )
                _require(type(frame._buffer_origin) is bytearray)
                count = len(frame._buffer_origin)
                if frame._stream_origin is not None:
                    _require(type(frame._stream_origin) is CommittedFrameDigest
                             and type(frame._stream_origin._received) is int
                             and 0 <= frame._stream_origin._received <= TERMINAL_LIMIT)
                    count += frame._stream_origin._received
                _require(count == self._credit[1])
        return s

    def _settled(self, *, actor=True):
        _require(self._inflight is False and self._pending is None and self._pending_cell is None)
        if self._waiter is not None:
            cell = self._waiter_cell
            _require(type(cell) is tuple and len(cell) == 4 and cell[0] is self
                     and cell[1] is self._waiter and type(self._waiter) is SelectorReadiness
                     and type(cell[2]) is ReadinessScope and type(cell[3]) is _FUTURE
                     and self._waiter._origin_scope is cell[2]
                     and self._waiter._future_origin is cell[3]
                     and cell[2].sock is self._scope_origin.sock
                     and cell[2].task is self._scope_origin.write.allocation.task)
            SelectorReadiness._guard(self._waiter, actor=actor)
            _require(self._waiter._retired is True and self._waiter._unknown is False)

    def _current(self):
        s = NativeTerminalReceiver._metadata(self)
        _require(NativeResultBodyOwner.current_candidate(s.body) is s.candidate)
        fd = _FILENO(s.sock)
        _require(type(fd) is int and fd >= 0)
        row = _FSTAT(fd)
        _require(type(row) is os.stat_result and type(row.st_mode) is int
                 and type(row.st_dev) is int and type(row.st_ino) is int)
        timeout = _TIMEOUT(s.sock)
        _require(s.write.channel._identity_snapshot is s.identity
                 and (fd, row.st_dev, row.st_ino, row.st_mode & 0o170000) == s.identity
                 and os.get_blocking(fd) is False and os.get_inheritable(fd) is False
                 and type(timeout) is float and timeout == 0.0
                 and NativeTerminalReceiver._metadata(self) is s)
        _require(NativePhaseWorkOwner._retained_material(s.write.producer)[0] is s.write.remote)
        RemoteOperationOwner._result_intent_local(s.write.remote, s.write.channel,
                                                 s.write.intent.end_ns)
        _, cause, end, broken = CancellationBudget.inspect(s.write.remote._cleanup_budget_snapshot)
        _require(cause is None and end is None and broken is False)
        if self._frame_done is not None:
            frame = self._frame
            _require(type(frame._header_allocation) is tuple and len(frame._header_allocation) == 3
                     and frame._header_allocation[0] is frame
                     and type(frame._header_allocation[2]) is bytes)
            data, prefix = self._frame_done, frame._header_allocation[2]
            actual = _SHA256(prefix + data.terminal).hexdigest()
            _require(NativeTerminalReceiver._metadata(self) is s
                     and self._frame_done is data and type(actual) is str
                     and actual == self._checked.frame_sha256)
        NativeTerminalReceiver._tail(self, s)
        return s

    def _tail(self, s):
        _require(NativePhaseWorkOwner._retained_material(s.write.producer)[0] is s.write.remote)
        RemoteOperationOwner._result_intent_local(s.write.remote, s.write.channel,
                                                 s.write.intent.end_ns)
        _require(NativeTerminalReceiver._metadata(self) is s)
        _, cause, end, broken = CancellationBudget.inspect(s.write.remote._cleanup_budget_snapshot)
        _require(cause is None and end is None and broken is False
                 and asyncio.current_task() is s.write.allocation.task
                 and _TASK.cancelling(s.write.allocation.task) == 0)

    async def _read(self, count):
        s = NativeTerminalReceiver._current(self)
        _require(type(count) is int and 0 < count <= 65536
                 and self._pending is None and self._inflight is False)
        part = None
        try:
            while True:
                NativeTerminalReceiver._settled(self)
                _require(NativeTerminalReceiver._current(self) is s)
                before, cell = self._received, self._count_cell
                self._inflight = True
                try:
                    _require(_RECV is socket.socket.recv)
                    part = _RECV(s.sock, count)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and NativeTerminalReceiver._metadata(self) is s
                             and self._received is before and self._count_cell is cell)
                    self._inflight = False
                    waiter = SelectorReadiness.__new__(SelectorReadiness)
                    self._waiter = waiter
                    self._waiter_cell = (self, waiter, None, None)
                    SelectorReadiness.__init__(waiter, s.sock)
                    self._waiter_cell = (self, waiter, waiter._origin_scope, waiter._future_origin)
                    wait_cell = self._waiter_cell
                    _require(NativeTerminalReceiver._current(self) is s)
                    await SelectorReadiness.wait(waiter, s.write.intent.end_ns,
                        wake=s.write.refs[0]._barriers_snapshot.cause)
                    _require(self._waiter is waiter and self._waiter_cell is wait_cell)
                    NativeTerminalReceiver._settled(self)
                    continue
                _require(type(part) is bytes)
                same = (self._scope is s and self._scope_origin is s
                        and self._received is before and self._received_origin is before
                        and self._count_cell is cell and self._inflight is True)
                self._received = self._received_origin = before + len(part)
                self._count_cell = (self, s, self._received)
                self._pending, self._pending_cell = part, (self, part, self._received)
                self._inflight = False
                _require(same and 0 < len(part) <= count and self._received <= _LIMIT)
                pending_cell = self._pending_cell
                _require(NativeTerminalReceiver._current(self) is s
                         and self._pending is part and self._pending_cell is pending_cell)
                return part
        finally:
            part = None

    def _correlate(self, raw):
        s = NativeTerminalReceiver._current(self)
        handoff = decode_handoff(raw)
        _require(type(handoff) is TerminalHandoff and type(handoff.claim) is StartedClaim)
        c = handoff.claim
        _values(c)
        packet = s.write.intent.packet
        row = decode_input_v3(packet)
        expected = dict(s.expected)
        domain = s.write.remote._clock_domain_values_snapshot
        _require(type(domain) is tuple and len(domain) == 4 and type(domain[0]) is str
                 and type(domain[1]) is str and type(domain[2]) is bytes
                 and (domain[3] is None or (type(domain[3]) is tuple and len(domain[3]) == 2
                      and all(type(v) is int for v in domain[3]))))
        domain_wire = json.dumps((domain[0], domain[1], domain[2].hex(), domain[3]),
                                separators=(",", ":"), ensure_ascii=True).encode("ascii")
        _require((c.binding, c.profile, c.operation_kind, c.deadline_ns, c.challenge, c.epoch,
                  c.input_sha256, c.worker_source_sha256, c.installation_generation,
                  c.clock_domain_sha256, c.result_sha256) == (
            claim_binding(s.write.intent.binding), row["profile"], row["operation"],
            row["deadline_ns"], row["challenge"], row["epoch"], _SHA256(packet).hexdigest(),
            row["source_manifest_sha"], expected["generation"], _SHA256(domain_wire).hexdigest(),
            s.candidate.body_wire_sha256) and c.outcome == "OK" and c.exit_code == 0)
        _require(NativeTerminalReceiver._current(self) is s)
        return handoff

    async def receive(self):
        s = NativeTerminalReceiver._metadata(self)
        NativeResultBodyOwner._actor(s.body)
        _require(self._initialized is True and self._attempted is False and self._active is False)
        self._attempted = self._active = True
        s.write.channel._reading = True
        own_cell, body_cell = self._scope_cell, s.body._terminal_reader_cell
        failed = cancelled = False
        part = auth = checked = frame = data = handoff = fact = None
        original_auth_cell = self._auth_allocation_origin
        original_frame_cell = None
        try:
            _require(NativeTerminalReceiver._current(self) is s)
            auth = self._auth
            _require(type(auth) is SignedCleanupAuthPrefix
                     and type(self._auth_cell) is tuple and len(self._auth_cell) == 2
                     and self._auth_cell[0] is self and self._auth_cell[1] is auth
                     and self._auth_cell is original_auth_cell)
            while SignedCleanupAuthPrefix.needed.fget(auth):
                part = await NativeTerminalReceiver._read(
                    self, SignedCleanupAuthPrefix.needed.fget(auth)
                )
                credit, credit_cell, pending_cell = (
                    self._credit,
                    self._credit_cell,
                    self._pending_cell,
                )
                self._feeding = True
                SignedCleanupAuthPrefix.feed(auth, part)
                _require(
                    self._scope is s
                    and self._scope_origin is s
                    and self._scope_cell is own_cell
                    and self._feeding is True
                    and self._credit is credit
                    and self._credit_origin is credit
                    and self._credit_cell is credit_cell
                    and self._pending is part
                    and self._pending_cell is pending_cell
                    and self._auth is auth
                    and self._auth_cell is original_auth_cell
                )
                self._credit = self._credit_origin = (credit[0] + len(part), credit[1])
                self._credit_cell = (self, self._credit)
                part = self._pending = self._pending_cell = None
                self._feeding = False
                NativeTerminalReceiver._current(self)
            target = self._credit[0]
            self._feeding = True
            checked = SignedCleanupAuthPrefix.finish(auth)
            self._checked, self._checked_cell = checked, (self, checked)
            _require(type(checked) is ConsistentCommitment)
            self._checked_values = (
                checked.canonical_json,
                checked.frame_sha256,
                checked.frame_length,
            )
            self._auth_finish_cell = (self, auth, checked, target)
            self._auth_finished = True
            self._feeding = False
            frame = CommittedFrameDiscard.__new__(CommittedFrameDiscard)
            self._frame, self._frame_cell = frame, (self, frame)
            self._frame_allocation_origin = self._frame_cell
            original_frame_cell = self._frame_cell
            CommittedFrameDiscard.__init__(frame, checked, binding=s.write.intent.binding,
                                          phase="TERMINAL", sequence=2)
            _require(self._frame is frame and self._frame_cell is original_frame_cell)
            self._frame_ready = True
            while CommittedFrameDiscard.needed.fget(frame):
                part = await NativeTerminalReceiver._read(
                    self, CommittedFrameDiscard.needed.fget(frame)
                )
                credit, credit_cell, pending_cell = (
                    self._credit,
                    self._credit_cell,
                    self._pending_cell,
                )
                self._feeding = True
                CommittedFrameDiscard.feed(frame, part)
                _require(
                    self._scope is s
                    and self._scope_origin is s
                    and self._scope_cell is own_cell
                    and self._feeding is True
                    and self._credit is credit
                    and self._credit_origin is credit
                    and self._credit_cell is credit_cell
                    and self._pending is part
                    and self._pending_cell is pending_cell
                    and self._frame is frame
                    and self._frame_cell is original_frame_cell
                )
                self._credit = self._credit_origin = (credit[0], credit[1] + len(part))
                self._credit_cell = (self, self._credit)
                part = self._pending = self._pending_cell = None
                self._feeding = False
                NativeTerminalReceiver._current(self)
            self._feeding = True
            data = CommittedFrameDiscard.finish(frame)
            _require(self._scope_origin is s and self._frame is frame
                     and self._frame_cell is original_frame_cell
                     and self._frame_allocation_origin is original_frame_cell)
            _require(type(data) is DiscardedFrame and type(data.terminal) is bytes)
            self._frame_done = data
            self._frame_done_cell = (self, frame, data)
            self._feeding = False
            handoff = NativeTerminalReceiver._correlate(self, data.terminal)
            NativeTerminalReceiver._settled(self)
            _require(NativeTerminalReceiver._current(self) is s)
            fact = _Fact(self, s, data, handoff, self._received)
            _require(type(fact) is _Fact and fact.owner is self and fact.scope is s
                     and fact.frame is data and fact.handoff is handoff
                     and type(self._received) is int and type(self._received_origin) is int
                     and self._received is self._received_origin
                     and type(fact.received) is int and fact.received == self._received)
            self._fact = self._fact_origin = fact
            self._fact_cell = self._fact_cell_origin = (self, fact)
            fact_cell = self._fact_cell
            NativeTerminalReceiver._tail(self, s)
            _require(self._fact is fact and self._fact_cell is fact_cell
                     and self._scope is s and self._scope_origin is s
                     and self._scope_cell is own_cell)
            self._complete = True
        except BaseException as error:
            failed = self._failed = True
            cancelled = isinstance(error, asyncio.CancelledError)
            self._unknown = self._inflight or self._pending is not None
            try:
                NativeTerminalReceiver._settled(self)
            except BaseException:
                self._unknown = True
            self._fact = self._fact_origin = self._fact_cell = self._fact_cell_origin = None
            for allocation, cls, wipe in (
                (original_auth_cell, SignedCleanupAuthPrefix, SignedCleanupAuthPrefix._wipe_owned),
                (original_frame_cell, CommittedFrameDiscard, CommittedFrameDiscard._fail),
            ):
                if (type(allocation) is tuple and len(allocation) == 2
                        and allocation[0] is self and type(allocation[1]) is cls):
                    try:
                        wipe(allocation[1])
                    except BaseException:
                        self._unknown = True
            if self._unknown:
                s.body._io_unknown = True
            NativeResultBodyOwner.wipe(s.body)
        finally:
            part = auth = checked = frame = data = handoff = fact = None
            original_auth_cell = original_frame_cell = None
            credit = credit_cell = pending_cell = allocation = fact_cell = None
            self._pending = self._pending_cell = None
            if (
                self._unknown is False
                and self._scope is s
                and self._scope_origin is s
                and self._scope_cell is own_cell
                and s.body._terminal_reader is self
                and s.body._terminal_reader_origin is self
                and s.body._terminal_reader_cell is body_cell
                and s.write.channel._reading is True
            ):
                self._active = False
                s.write.channel._reading = False
            else:
                failed = self._failed = self._unknown = True
                self._complete = False
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_NORMAL_TERMINAL_RECEPTION_UNKNOWN") from None
        return self._fact

    def current_correlation(self):
        """Original work actor's resealed DATA; never native acceptance or ACK authority."""
        _require(type(self) is NativeTerminalReceiver and type(self._scope_origin) is _Scope)
        s = self._scope_origin
        NativeResultBodyOwner._actor(s.body)  # a foreign task cannot invalidate the owner
        fact = cell = wire = None
        failed = False
        try:
            fact, cell = self._fact_origin, self._fact_cell_origin
            _require(self._complete is True and self._active is False
                     and type(fact) is _Fact and self._fact is fact
                     and type(cell) is tuple and len(cell) == 2
                     and cell[0] is self and cell[1] is fact and self._fact_cell is cell
                     and fact.owner is self and fact.scope is s
                     and fact.frame is self._frame_done
                     and type(self._received) is int and type(self._received_origin) is int
                     and self._received is self._received_origin
                     and type(fact.received) is int and fact.received == self._received
                     and type(fact.handoff) is TerminalHandoff)
            _require(NativeTerminalReceiver._current(self) is s
                     and self._fact is fact and self._fact_origin is fact
                     and self._fact_cell is cell and self._fact_cell_origin is cell)
            wire = encode_handoff(fact.handoff.claim, fact.handoff.cleanup)
            _require(type(wire) is bytes and wire == fact.frame.terminal)
            NativeTerminalReceiver._settled(self)
            _require(NativeTerminalReceiver._current(self) is s
                     and self._fact is fact and self._fact_origin is fact
                     and self._fact_cell is cell and self._fact_cell_origin is cell)
            return fact
        except BaseException:
            self._failed = failed = True
            self._complete = False
            self._fact = self._fact_origin = self._fact_cell = self._fact_cell_origin = None
            NativeResultBodyOwner.wipe(s.body)
        finally:
            fact = cell = wire = None
        if failed:
            raise FrameError("BI1_NORMAL_TERMINAL_CORRELATION_REFUSED") from None

    def require_released(self, body):
        _require(
            type(self) is NativeTerminalReceiver
            and type(self._scope_origin) is _Scope
            and self._scope_origin.body is body
            and type(body) is NativeResultBodyOwner
            and self._scope is self._scope_origin
            and type(self._scope_cell) is tuple
            and len(self._scope_cell) == 2
            and self._scope_cell[0] is self
            and self._scope_cell[1] is self._scope_origin
            and body._terminal_reader is self
            and body._terminal_reader_origin is self
            and type(body._terminal_reader_cell) is tuple
            and len(body._terminal_reader_cell) == 2
            and body._terminal_reader_cell[0] is body
            and body._terminal_reader_cell[1] is self
            and self._active is False
            and self._unknown is False
            and _TASK.done(self._scope_origin.write.allocation.task)
        )
        NativeTerminalReceiver._settled(self, actor=False)
