"""Original signed cursor body validation; private candidate, never native release."""
from __future__ import annotations

import asyncio
import errno
import hashlib
import os
import socket
import stat
from typing import NamedTuple

from .presentation_authority import ParentAuthorityAdapter
from .presentation_broker_service import SocketChannel
from .presentation_clock import NativeClockOwner
from .presentation_credential_begin_write import _BeginWriterScope
from .presentation_credential_phase import check_commitment
from .presentation_credential_result_read import NativeResultEnvelopeReceiver, _ResultReadScope
from .presentation_credential_stream import CommittedFrameDigest
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError, JobOwner, RemotePhase, State, _Job
from .presentation_output_v2 import BoundedResultBufferV2, compare_parent_snapshot
from .presentation_parent_policy import ParentPolicySnapshot
from .presentation_readiness import (
    _CANCEL_RETIREMENT_MINT,
    SelectorReadiness,
    _CancelledWaitRetirement,
    _ReadinessCancelledError,
    _WakeBinding,
)
from .presentation_readiness import (
    _Scope as _ReadinessScope,
)
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _FUTURE, _TASK, RemoteCleanupOwner, _TaskAllocation
from .presentation_result_transport import _candidate_header_wire

_RECV = socket.socket.recv
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_HASH = type(hashlib.sha256())
_MINT = object()
_RETIRE_MINT = object()
_ADOPT_MINT = object()
_NOTICE_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_RESULT_BODY_REFUSED")


class _BodyScope(NamedTuple):
    envelope: object
    envelope_scope: object
    envelope_fact: object
    job: object
    buffer: object
    accumulator: object
    custody: tuple
    context: tuple
    expected: object
    challenge: str
    epoch: int

    def __repr__(self):
        return "<SignedBodyScope original-custody redacted>"


class _BodyCandidate(NamedTuple):
    mint: object
    owner: object
    scope: object
    candidate_id: int
    header_id: int
    body_id: int
    header_wire: bytes
    frame_sha256: str
    body_wire_sha256: str
    received: int

    def __repr__(self):
        return "<SignedBodyCandidate private-only no-release redacted>"


class _BodyAdoption(NamedTuple):
    mint: object
    owner: object
    scope: object
    candidate_fact: object
    token: object

    def __repr__(self):
        return "<SignedBodyAdoption private-native-candidate no-release>"


class _BodyNotice(NamedTuple):
    mint: object
    owner: object
    scope: object
    adoption: object
    allocation: tuple

    def __repr__(self):
        return "<SignedResultNotice private-readiness no-data-release>"


class _BodyWait(NamedTuple):
    scope: object
    waiter: object
    native_scope: object
    future: object
    end: int
    received: int
    committed: int
    allocation: tuple
    buffer_meta: tuple
    hash_value: str
    stream_received: int

    def __repr__(self):
        return "<BodyWait original-progress no-payload>"


class _BodyRetirement(NamedTuple):
    mint: object
    owner: object
    wait: _BodyWait
    native: object

    def __repr__(self):
        return "<BodyRetirement local-only payload-free>"


class NativeResultBodyOwner:
    @classmethod
    def retain(cls, envelope):
        _require(cls is NativeResultBodyOwner and type(envelope) is NativeResultEnvelopeReceiver)
        e = NativeResultEnvelopeReceiver._metadata(envelope)
        b = e.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and envelope._complete is True and envelope._failed is False
                 and envelope._active is False and envelope._io_unknown is False
                 and envelope._body_owner is None and envelope._body_owner_snapshot is None
                 and b.remote._signed_result_owner is None
                 and b.remote._signed_result_owner_snapshot is None)
        job, custody = b.remote._job_origin_snapshot, b.remote._output_custody_snapshot
        _require(type(job) is _Job and type(custody) is tuple and len(custody) == 3
                 and custody[0] is job and type(custody[1]) is BoundedResultBufferV2
                 and type(custody[2]) is bytearray
                 and job.output_buffer is custody[1] and custody[1]._buffer is custody[2]
                 and not custody[2] and custody[1]._done is False
                 and type(job.parent_result_context) is tuple
                 and len(job.parent_result_context) == 2
                 and type(job.parent_result_context[0]) is str
                 and type(job.parent_result_context[1]) is ParentPolicySnapshot
                 and job._remote_candidate_custody_origin is None
                 and job._remote_candidate_custody_snapshot is None)
        row = decode_input_v3(b.intent.packet)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_origin = _BodyScope(
            envelope, e, envelope._completion_origin, job, custody[1], custody[2], custody,
            job.parent_result_context, row["expected_avatar_sha"], row["challenge"], row["epoch"])
        owner._candidate_job_origin = job
        owner._wipe_custody_origin = custody
        owner._initialized = owner._attempted = owner._active = False
        owner._adopted = owner._adoption_attempted = False
        owner._adoption = owner._adoption_origin = None
        owner._adoption_allocation_origin = None
        owner._token = owner._token_origin = None
        owner._notice_attempted = owner._notified = False
        owner._notice = owner._notice_snapshot = owner._notice_fact_allocation_origin = None
        cleanup = b.refs[0]
        _require(type(cleanup) is RemoteCleanupOwner
                 and type(cleanup._result_barrier_snapshot) is tuple
                 and len(cleanup._result_barrier_snapshot) == 1
                 and type(cleanup._result_barrier_snapshot[0]) is _FUTURE)
        owner._notice_allocation_origin = (cleanup, cleanup._result_barrier_snapshot,
            cleanup._result_barrier_snapshot[0], b.allocation, cleanup._caller_snapshot)
        b.remote._signed_result_owner = b.remote._signed_result_owner_snapshot = owner
        owner._failed = owner._retired = owner._validated = owner._io_unknown = False
        owner._read_intent = owner._commit_intent = owner._finish_attempted = False
        owner._received = owner._received_snapshot = 0
        owner._committed = owner._committed_snapshot = 0
        owner._pending = owner._pending_snapshot = None
        owner._waiter = owner._waiter_origin = None
        owner._stream = owner._stream_origin = None
        owner._hash = owner._hash_origin = None
        owner._candidate = owner._candidate_snapshot = None
        owner._fact = owner._fact_snapshot = None
        owner._cancel_receipt = owner._cancel_receipt_snapshot = None
        owner._initialization = owner._initialization_origin = None
        envelope._body_owner = envelope._body_owner_snapshot = owner
        job._remote_candidate_custody_origin = job._remote_candidate_custody_snapshot = (owner, job)
        failed = False
        try:
            NativeResultBodyOwner._current(owner)
            checked = check_commitment(owner._scope_origin.envelope_fact.raw,
                sender_public=e.pins[0], receiver_public=e.pins[1], expected=dict(e.expected))
            stream = CommittedFrameDigest.__new__(CommittedFrameDigest)
            owner._stream = owner._stream_origin = stream
            allocation = (owner._scope_origin, stream, None)
            owner._initialization = owner._initialization_origin = allocation
            CommittedFrameDigest.__init__(stream, checked, owner._scope_origin.envelope_fact.frame,
                                         binding=b.intent.binding)
            own_hash = hashlib.sha256()
            _require(owner._initialization is allocation
                     and owner._initialization_origin is allocation
                     and owner._stream is stream and owner._stream_origin is stream)
            owner._hash = owner._hash_origin = own_hash
            owner._initialization = owner._initialization_origin = (
                owner._scope_origin, stream, own_hash)
            NativeResultBodyOwner._current(owner)
            owner._initialized = True
        except BaseException:
            failed = True
            owner._failed = True
            NativeResultBodyOwner.wipe(owner)
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_BODY_ACQUISITION_REFUSED") from None
        return owner

    def __repr__(self):
        return "<NativeResultBodyOwner private-candidate-redacted>"

    def _envelope_reading(self, envelope):
        _require(type(self) is NativeResultBodyOwner and type(self._scope) is _BodyScope
                 and self._scope is self._scope_origin)
        s = self._scope_origin
        _require(type(envelope) is NativeResultEnvelopeReceiver and s.envelope is envelope
                 and type(s.envelope_scope) is _ResultReadScope
                 and envelope._scope_origin is s.envelope_scope
                 and envelope._body_owner is self and envelope._body_owner_snapshot is self
                 and type(s.envelope_scope.write_scope) is _BeginWriterScope
                 and type(s.envelope_scope.write_scope.channel) is SocketChannel
                 and s.envelope_scope.write_scope.channel._credential_result_receiver is envelope
                 and s.envelope_scope.write_scope.channel._credential_result_receiver_snapshot
                     is envelope and type(self._active) is bool)
        return self._active  # fixed original read claim, never authority

    def _metadata(self):
        """Retained data joins only; no actor, authority or publication grant."""
        _require(type(self) is NativeResultBodyOwner and type(self._scope) is _BodyScope
                 and self._scope is self._scope_origin)
        s = self._scope_origin
        _require(type(s.envelope) is NativeResultEnvelopeReceiver
                 and NativeResultBodyOwner._envelope_reading(self, s.envelope) is self._active
                 and NativeResultEnvelopeReceiver._metadata(s.envelope) is s.envelope_scope
                 and s.envelope._completion_origin is s.envelope_fact
                 and s.envelope._complete is True and s.envelope._failed is False
                 and s.envelope._active is False
                 and type(s.job) is _Job and type(s.buffer) is BoundedResultBufferV2
                 and type(s.accumulator) is bytearray and s.buffer._buffer is s.accumulator
                 and s.custody is self._wipe_custody_origin
                 and s.custody is s.envelope_scope.write_scope.remote._output_custody_snapshot
                 and s.job is self._candidate_job_origin and s.job.output_buffer is s.buffer
                 and s.job.remote_output_origin is s.buffer
                 and s.job.parent_result_context is s.context
                 and type(s.context) is tuple and len(s.context) == 2 and type(s.context[0]) is str
                 and type(s.context[1]) is ParentPolicySnapshot
                 and s.job.state is State.RUNNING
                 and type(s.job._remote_candidate_custody_snapshot) is tuple
                 and len(s.job._remote_candidate_custody_snapshot) == 2
                 and s.job._remote_candidate_custody_snapshot[0] is self
                 and s.job._remote_candidate_custody_snapshot[1] is s.job
                 and s.job._remote_candidate_custody_origin
                     is s.job._remote_candidate_custody_snapshot
                 and all(type(v) is bool for v in (self._initialized, self._attempted, self._active,
                     self._failed, self._retired, self._validated, self._io_unknown,
                     self._read_intent, self._commit_intent, self._finish_attempted,
                     self._adopted, self._adoption_attempted,
                     self._notice_attempted, self._notified))
                 and self._failed is False and self._retired is False and self._io_unknown is False
                 and type(self._received) is int and self._received is self._received_snapshot
                 and type(self._committed) is int and self._committed is self._committed_snapshot
                 and 0 <= self._committed <= self._received <= s.envelope_fact.header.body_length
                 and self._pending is self._pending_snapshot
                 and (self._pending is None or type(self._pending) is bytes)
                 and self._waiter is self._waiter_origin
                 and self._stream is self._stream_origin
                 and (self._stream is None or type(self._stream) is CommittedFrameDigest)
                 and self._hash is self._hash_origin
                 and (self._hash is None or type(self._hash) is _HASH)
                 and self._candidate is self._candidate_snapshot
                 and self._fact is self._fact_snapshot)
        allocation = self._initialization_origin
        _require(self._initialization is allocation)
        if allocation is not None:
            _require(type(allocation) is tuple and len(allocation) == 3 and allocation[0] is s
                     and type(allocation[1]) is CommittedFrameDigest
                     and self._stream is allocation[1] and self._stream_origin is allocation[1]
                     and self._hash is allocation[2] and self._hash_origin is allocation[2]
                     and (allocation[2] is None or type(allocation[2]) is _HASH))
        if self._initialized:
            _require(type(allocation) is tuple and len(allocation) == 3
                     and type(allocation[2]) is _HASH)
        remote = s.envelope_scope.write_scope.remote
        _require(remote._signed_result_owner is self
                 and remote._signed_result_owner_snapshot is self
                 and self._token is self._token_origin
                 and self._adoption is self._adoption_origin)
        allocation = self._adoption_allocation_origin
        if allocation is not None:
            _require(type(allocation) is tuple and len(allocation) == 3
                     and allocation[0] is s and type(allocation[1]) is _BodyAdoption
                     and type(allocation[2]) is object
                     and self._adoption_origin is allocation[1]
                     and self._token_origin is allocation[2])
        else:
            _require(self._adoption_origin is None and self._token_origin is None)
        if self._adopted:
            _require(self._adoption_attempted is True and self._validated is True
                     and type(self._adoption_origin) is _BodyAdoption
                     and self._adoption_origin.mint is _ADOPT_MINT
                     and self._adoption_origin.owner is self and self._adoption_origin.scope is s
                     and self._adoption_origin.candidate_fact is self._fact_snapshot
                     and type(self._token_origin) is object
                     and self._adoption_origin.token is self._token_origin
                     and s.job.result is self._candidate_snapshot
                     and s.job.remote_result_token is self._token_origin
                     and s.job.remote_phase is RemotePhase.RESULT_VALIDATED)
        else:
            _require(s.job.result is None and s.job.remote_result_token is None
                     and s.job.remote_phase is RemotePhase.GO_SENT)
        row = decode_input_v3(s.envelope_scope.write_scope.intent.packet)
        _require(type(s.challenge) is str and type(s.epoch) is int
                 and s.challenge == row["challenge"] and s.epoch == row["epoch"]
                 and (s.expected is None or type(s.expected) is str)
                 and s.expected == row["expected_avatar_sha"]
                 and s.buffer._done is self._finish_attempted)
        return s

    def _local(self):
        s = NativeResultBodyOwner._metadata(self)
        _require(NativeResultBodyOwner._actor(self) is s)
        return s

    def _current(self):
        s = NativeResultBodyOwner._local(self)
        _require(NativeResultEnvelopeReceiver.current_envelope(s.envelope) is s.envelope_fact)
        _require(NativeResultBodyOwner._local(self) is s)
        return s

    def _candidate_metadata(self):
        """Recheck minted private data only; this grants no actor or native authority."""
        s = NativeResultBodyOwner._metadata(self)
        candidate, fact = self._candidate_snapshot, self._fact_snapshot
        _require(self._validated is True and self._active is False
                 and self._attempted is True and self._finish_attempted is True
                 and type(candidate) is tuple and len(candidate) == 2
                 and type(candidate[0]) is dict and type(candidate[1]) is bytes
                 and type(fact) is _BodyCandidate and fact.mint is _MINT
                 and fact.owner is self and fact.scope is s
                 and all(type(v) is int for v in (
                     fact.candidate_id, fact.header_id, fact.body_id, fact.received))
                 and type(fact.frame_sha256) is str and len(fact.frame_sha256) == 64
                 and type(fact.body_wire_sha256) is str and len(fact.body_wire_sha256) == 64
                 and type(self._stream_origin._commitment_values) is tuple
                 and len(self._stream_origin._commitment_values) == 3
                 and type(self._stream_origin._commitment_values[0]) is bytes
                 and type(self._stream_origin._commitment_values[1]) is str
                 and type(self._stream_origin._commitment_values[2]) is int
                 and fact.candidate_id == id(candidate)
                 and fact.header_id == id(candidate[0]) and fact.body_id == id(candidate[1])
                 and type(fact.header_wire) is bytes
                 and _candidate_header_wire(candidate[0]) == fact.header_wire
                 and fact.received == self._received_snapshot == self._committed_snapshot
                 and fact.received == s.envelope_fact.header.body_length
                 and fact.body_wire_sha256 == self._hash_origin.hexdigest()
                 and self._stream_origin._finished is True
                 and fact.frame_sha256 == self._stream_origin._commitment_values[1]
                 and not s.accumulator and s.buffer._done is True)
        return fact

    def _candidate_local(self):
        NativeResultBodyOwner._actor(self)
        return NativeResultBodyOwner._candidate_metadata(self)

    def _actor_scope(self):
        # A foreign actor cannot consume the original actor's private candidate.
        _require(type(self) is NativeResultBodyOwner and type(self._scope_origin) is _BodyScope
                 and self._scope is self._scope_origin)
        s = self._scope_origin
        _require(type(s.envelope) is NativeResultEnvelopeReceiver
                 and type(s.envelope_scope) is _ResultReadScope
                 and s.envelope._scope_origin is s.envelope_scope
                 and s.envelope._body_owner_snapshot is self
                 and type(s.envelope_scope.write_scope) is _BeginWriterScope
                 and type(s.envelope_scope.write_scope.allocation) is _TaskAllocation
                 and type(s.envelope_scope.write_scope.allocation.task) is _TASK)
        return s

    def _actor(self):
        s = NativeResultBodyOwner._actor_scope(self)
        _require(asyncio.current_task() is s.envelope_scope.write_scope.allocation.task
                 and _TASK.cancelling(asyncio.current_task()) == 0)
        return s

    def _caller_actor(self):
        s = NativeResultBodyOwner._actor_scope(self)
        b = s.envelope_scope.write_scope
        _require(type(b.refs) is tuple and len(b.refs) == 12
                 and type(b.refs[0]) is RemoteCleanupOwner)
        RemoteCleanupOwner.authorize_result_caller(b.refs[0])
        return s

    def current_candidate(self):
        """Private data identity under current original-work authority, not release."""
        s = NativeResultBodyOwner._actor(self)
        _require(self._adopted is False)
        fact = checked = None
        failed = False
        try:
            fact = NativeResultBodyOwner._candidate_local(self)
            NativeResultBodyOwner._settled(self)
            s = NativeResultBodyOwner._current(self)
            checked = check_commitment(s.envelope_fact.raw,
                sender_public=s.envelope_scope.pins[0],
                receiver_public=s.envelope_scope.pins[1],
                expected=dict(s.envelope_scope.expected))
            _require(NativeResultBodyOwner._candidate_local(self) is fact
                     and fact.frame_sha256 == checked.frame_sha256)
            return fact
        except BaseException:
            failed = True
            self._failed = True
            NativeResultBodyOwner.wipe(self)
        finally:
            fact = s = checked = None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_CANDIDATE_REFUSED") from None

    def adopt(self):
        """One original-task native candidate transition; no notice or release."""
        s = NativeResultBodyOwner._actor(self)
        _require(self._adoption_attempted is False and self._adopted is False)
        self._adoption_attempted = True
        failed = False
        fact = adoption = candidate = None
        try:
            fact = NativeResultBodyOwner.current_candidate(self)
            candidate = self._candidate_snapshot
            self._token = self._token_origin = object()
            adoption = _BodyAdoption(_ADOPT_MINT, self, s, fact, self._token_origin)
            self._adoption = self._adoption_origin = adoption
            self._adoption_allocation_origin = (s, adoption, self._token_origin)
            _require(NativeResultBodyOwner.current_candidate(self) is fact
                     and self._adoption_attempted is True and self._adopted is False
                     and self._adoption is adoption and self._adoption_origin is adoption
                     and adoption.token is self._token is self._token_origin
                     and self._candidate_snapshot is candidate
                     and NativeResultBodyOwner._candidate_local(self) is fact)
            # Pure original-object installation after the final current authority fence.
            s.job.result = candidate
            s.job.remote_result_token = adoption.token
            s.job.remote_phase = RemotePhase.RESULT_VALIDATED
            self._adopted = True
            return True
        except BaseException:
            failed = True
            self._failed = True
            NativeResultBodyOwner.wipe(self)
        finally:
            fact = adoption = candidate = s = None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_ADOPTION_REFUSED") from None

    def _adoption_local(self):
        s = NativeResultBodyOwner._local(self)
        _require(self._adopted is True and self._active is False)
        NativeResultBodyOwner._candidate_local(self)
        return s

    def _adoption_metadata(self):
        s = NativeResultBodyOwner._metadata(self)
        _require(self._adopted is True and self._active is False)
        NativeResultBodyOwner._candidate_metadata(self)
        return s

    def current_adopted(self):
        """Fixed post-adoption authority; never resets native phase to GO_SENT."""
        s = NativeResultBodyOwner._actor(self)
        _require(self._adopted is True)
        failed = False
        b = fact = checked = None
        try:
            _require(NativeResultBodyOwner._adoption_local(self) is s)
            b = s.envelope_scope.write_scope
            fact = self._adoption_origin
            NativeResultBodyOwner._settled(self)
            RemoteOperationOwner._check(b.remote, RemotePhase.RESULT_VALIDATED)
            SocketChannel._check(b.channel)
            _require(SocketChannel._qualified_clock(b.channel) is b.refs[8])
            now = NativeClockOwner.sample(b.refs[8])
            _require(NativePhaseWorkOwner._material_local(b.producer)[0] is b.remote
                     and NativeResultBodyOwner._adoption_local(self) is s
                     and type(now) is int and 0 <= now < b.intent.end_ns)
            checked = check_commitment(s.envelope_fact.raw,
                sender_public=s.envelope_scope.pins[0], receiver_public=s.envelope_scope.pins[1],
                expected=dict(s.envelope_scope.expected))
            _require(fact.candidate_fact.frame_sha256 == checked.frame_sha256)
            fd = _FILENO(b.sock)
            row = os.fstat(fd)
            _require(type(fd) is int and fd == b.channel._fd_snapshot
                     and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                         == b.channel._identity_snapshot
                     and os.get_blocking(fd) is False and _TIMEOUT(b.sock) == 0.0
                     and os.get_inheritable(fd) is False)
            RemoteOperationOwner._result_validated_local(b.remote, b.channel, b.intent.end_ns)
            _require(NativeResultBodyOwner._adoption_local(self) is s
                     and self._adoption_origin is fact)
            return fact
        except BaseException:
            failed = True
            self._failed = True
            NativeResultBodyOwner.wipe(self)
        finally:
            s = b = fact = checked = None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_ADOPTED_REFUSED") from None

    def _caller_current(self):
        s = NativeResultBodyOwner._caller_actor(self)
        _require(NativeResultBodyOwner._adoption_metadata(self) is s)
        b, fact = s.envelope_scope.write_scope, self._adoption_origin
        NativeResultBodyOwner._settled(self)
        material = NativePhaseWorkOwner._result_caller_material(b.producer)
        _require(material[0] is b.remote and material[2] is b.channel)
        record = b.remote._record_snapshot
        _require(ParentAuthorityAdapter._current(b.remote._authority_snapshot, record)
                 and JobOwner._current(record.owner, s.job)
                 and ParentAuthorityAdapter._current(b.remote._authority_snapshot, record))
        RemoteOperationOwner._work_now(b.remote)
        SocketChannel._check(b.channel)
        _require(SocketChannel._qualified_clock(b.channel) is b.refs[8])
        now = NativeClockOwner.sample(b.refs[8])
        _require(type(now) is int and 0 <= now < b.intent.end_ns)
        checked = check_commitment(s.envelope_fact.raw,
            sender_public=s.envelope_scope.pins[0], receiver_public=s.envelope_scope.pins[1],
            expected=dict(s.envelope_scope.expected))
        _require(fact.candidate_fact.frame_sha256 == checked.frame_sha256)
        fd = _FILENO(b.sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == b.channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode))
                     == b.channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(b.sock) == 0.0
                 and os.get_inheritable(fd) is False)
        RemoteOperationOwner._result_notification_local(b.remote, b.channel, b.intent.end_ns)
        _require(NativeResultBodyOwner._adoption_metadata(self) is s
                 and self._adoption_origin is fact)
        return fact

    def _notice_metadata(self):
        s = NativeResultBodyOwner._adoption_metadata(self)
        a = self._notice_allocation_origin
        _require(type(a) is tuple and len(a) == 5 and type(a[0]) is RemoteCleanupOwner)
        RemoteCleanupOwner._guard(a[0])
        _require(type(a[1]) is tuple and len(a[1]) == 1 and type(a[2]) is _FUTURE
                 and a[1][0] is a[2] and a[0]._result_barrier_snapshot is a[1]
                 and a[0]._result_barrier is a[1] and a[0]._result_notice_snapshot is a[2]
                 and type(a[3]) is _TaskAllocation
                 and a[3] is s.envelope_scope.write_scope.allocation
                 and a[0]._allocations_snapshot[1] is a[3]
                 and type(a[4]) is _TASK and a[0]._caller_snapshot is a[4]
                 and a[0] is s.envelope_scope.write_scope.refs[0]
                 and self._notice is self._notice_snapshot)
        cell = self._notice_fact_allocation_origin
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is s
                 and type(cell[1]) is _BodyNotice and cell[1] is self._notice_snapshot
                 and cell[1].mint is _NOTICE_MINT and cell[1].owner is self
                 and cell[1].scope is s and cell[1].adoption is self._adoption_origin
                 and cell[1].allocation is a and self._notice_attempted is True)
        return cell[1]

    def notify(self):
        """Original-work one-shot readiness notification; no result data or release."""
        s = NativeResultBodyOwner._actor(self)
        _require(self._notice_attempted is False and self._notified is False)
        self._notice_attempted = True
        failed = False
        a = fact = None
        try:
            NativeResultBodyOwner.current_adopted(self)
            a = self._notice_allocation_origin
            _require(type(a) is tuple and len(a) == 5 and type(a[0]) is RemoteCleanupOwner
                     and a[0]._go_notice_fact is not None and type(a[2]) is _FUTURE
                     and not _FUTURE.done(a[2]) and a[0]._result_token_snapshot is None)
            fact = _BodyNotice(_NOTICE_MINT, self, s, self._adoption_origin, a)
            self._notice = self._notice_snapshot = fact
            self._notice_fact_allocation_origin = (s, fact)
            from .presentation_broker_cancel import _native_future_methods
            from .presentation_readiness import _scheduler_safe
            _native_future_methods(a[2])
            _scheduler_safe(s.envelope_scope.write_scope.loop)
            NativeResultBodyOwner.current_adopted(self)
            _require(NativeResultBodyOwner._notice_metadata(self) is fact)
            # The last native currentness callback can change scheduler/Future dispatch.
            _native_future_methods(a[2])
            _scheduler_safe(s.envelope_scope.write_scope.loop)
            _require(NativeResultBodyOwner._actor(self) is s
                     and NativeResultBodyOwner._notice_metadata(self) is fact
                     and self._notice_attempted is True and self._notified is False
                     and a[0]._result_token_snapshot is None and a[0]._result_token is None
                     and not _FUTURE.done(a[2]))
            a[0]._result_token = a[0]._result_token_snapshot = self._token_origin
            self._notified = True  # one-shot intent before possibly partial native scheduling
            _FUTURE.set_result(a[2], True)
            return True
        except BaseException:
            failed = True
            self._failed = True
            NativeResultBodyOwner.wipe(self)
        finally:
            s = a = fact = None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_NOTIFICATION_REFUSED") from None

    def current_notice(self):
        """Original-caller current readiness only; no image/header/token returned."""
        NativeResultBodyOwner._caller_actor(self)
        failed = False
        fact = a = None
        try:
            _require(self._notified is True)
            fact = NativeResultBodyOwner._notice_metadata(self)
            a = fact.allocation
            _require(_FUTURE.done(a[2]) and not _FUTURE.cancelled(a[2])
                     and _FUTURE.result(a[2]) is True
                     and a[0]._result_token is self._token_origin
                     and a[0]._result_token_snapshot is self._token_origin)
            NativeResultBodyOwner._caller_current(self)
            _require(NativeResultBodyOwner._notice_metadata(self) is fact
                     and a[0]._result_token is self._token_origin
                     and a[0]._result_token_snapshot is self._token_origin)
            return True
        except BaseException:
            failed = True
            self._failed = True
            NativeResultBodyOwner.wipe(self)
        finally:
            fact = a = None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_NOTICE_CURRENT_REFUSED") from None

    def discard(self):
        """Pure first-cause withdrawal under the original job's typed custody hook."""
        _require(type(self) is NativeResultBodyOwner)
        self._retired = True
        origin = self._wipe_custody_origin
        if (type(origin) is tuple and len(origin) == 3
                and type(origin[0]) is _Job and origin[0] is self._candidate_job_origin):
            origin[0].result = None
            origin[0].remote_result_token = None
        allocation = self._notice_allocation_origin
        if (type(allocation) is tuple and len(allocation) == 5
                and type(allocation[0]) is RemoteCleanupOwner
                and type(allocation[0]._remote_snapshot) is RemoteOperationOwner
                and allocation[0]._remote_snapshot._job_origin_snapshot
                    is self._candidate_job_origin):
            allocation[0]._result_token = allocation[0]._result_token_snapshot = None
        self._notice = self._notice_snapshot = self._notice_fact_allocation_origin = None
        self._token = self._token_origin = None
        self._adoption = self._adoption_origin = None
        self._adoption_allocation_origin = None
        self._candidate = self._candidate_snapshot = None
        self._fact = self._fact_snapshot = None
        self._pending = self._pending_snapshot = None

    def wipe(self):
        origin = self._wipe_custody_origin
        if (type(origin) is tuple and len(origin) == 3
                and origin[0] is self._candidate_job_origin and type(origin[0]) is _Job
                and type(origin[1]) is BoundedResultBufferV2 and type(origin[2]) is bytearray):
            origin[2][:] = b"\x00" * len(origin[2])
            origin[2].clear()
            origin[1]._done = True
        NativeResultBodyOwner.discard(self)

    def _settled(self):
        _require(self._read_intent is False and self._commit_intent is False
                 and self._pending is None and self._io_unknown is False)
        w = self._waiter_origin
        if w is not None:
            _require(type(w) is SelectorReadiness and self._waiter is w)
            SelectorReadiness._guard(w, actor=False)
            _require(w._retired is True and w._unknown is False)

    def _retirement_local(self, retirement, *, released=False):
        _require(type(self) is NativeResultBodyOwner and type(retirement) is _BodyRetirement
                 and retirement.mint is _RETIRE_MINT and retirement.owner is self
                 and type(retirement.wait) is _BodyWait and type(released) is bool)
        h, f = retirement.wait, retirement.native
        _require(type(h.scope) is _BodyScope and self._scope is h.scope
                 and self._scope_origin is h.scope and type(h.waiter) is SelectorReadiness
                 and self._waiter is h.waiter and self._waiter_origin is h.waiter
                 and type(h.native_scope) is _ReadinessScope
                 and type(f) is _CancelledWaitRetirement and f.mint is _CANCEL_RETIREMENT_MINT
                 and f.owner is h.waiter and f.scope is h.native_scope and f.future is h.future
                 and type(f.binding) is _WakeBinding and f.end is h.end
                 and f.binding.scope is h.native_scope and f.binding.future is None
                 and f.binding.end is h.end and type(h.end) is int
                 and type(h.received) is int and type(h.committed) is int
                 and self._received is h.received and self._received_snapshot is h.received
                 and self._committed is h.committed and self._committed_snapshot is h.committed
                 and h.received == h.committed and self._read_intent is False
                 and self._commit_intent is False and self._pending is None
                 and self._pending_snapshot is None and self._io_unknown is False
                 and self._initialization is h.allocation
                 and self._initialization_origin is h.allocation
                 and type(h.allocation) is tuple and len(h.allocation) == 3
                 and h.allocation[0] is h.scope
                 and type(h.allocation[1]) is CommittedFrameDigest
                 and type(h.allocation[2]) is _HASH
                 and self._stream is h.allocation[1] and self._stream_origin is h.allocation[1]
                 and self._hash is h.allocation[2] and self._hash_origin is h.allocation[2])
        s, w, b = h.scope, h.waiter, h.scope.envelope_scope.write_scope
        _require(type(s.buffer) is BoundedResultBufferV2 and type(s.accumulator) is bytearray
                 and s.buffer._buffer is s.accumulator and self._wipe_custody_origin is s.custody
                 and type(s.custody) is tuple and len(s.custody) == 3
                 and s.custody[0] is s.job and s.custody[1] is s.buffer
                 and s.custody[2] is s.accumulator and s.job is self._candidate_job_origin
                 and type(h.buffer_meta) is tuple and len(h.buffer_meta) == 2
                 and s.buffer._header_size is h.buffer_meta[0]
                 and s.buffer._body_size is h.buffer_meta[1]
                 and type(h.hash_value) is str and len(h.hash_value) == 64
                 and self._hash_origin.hexdigest() == h.hash_value
                 and self._stream_origin._received is h.stream_received
                 and self._stream_origin._received_snapshot is h.stream_received
                 and h.native_scope.task is b.allocation.task and h.native_scope.sock is b.sock
                 and h.native_scope.loop is b.loop and h.native_scope.interest == "read"
                 and h.end is b.intent.end_ns
                 and w._origin_scope is h.native_scope and w._scope_snapshot is h.native_scope
                 and w._future_origin is h.future and w._future_snapshot is h.future
                 and w._wake_binding_origin is f.binding and w._wake_binding is f.binding
                 and w._handle_snapshot is f.handle and w._handle_args_snapshot is f.handle_args)
        _require(w._attempted is True and w._retired is True and w._unknown is False)
        if released:
            _require(self._cancel_receipt is retirement
                     and self._cancel_receipt_snapshot is retirement
                     and self._retired is True and self._failed is True and self._active is False
                     and _TASK.done(b.allocation.task) and _TASK.cancelled(b.allocation.task)
                     and s.buffer._done is True and not s.accumulator)
        else:
            _require(asyncio.current_task() is b.allocation.task
                     and _TASK.cancelling(b.allocation.task) > 0
                     and self._attempted is True and self._active is True
                     and self._failed is False and self._validated is False)
            if self._retired:
                _require(s.envelope_scope.write_scope.remote._cleanup_owner_snapshot._intent is True
                         and s.job.emit_revoked is True and s.buffer._done is True
                         and not s.accumulator)
            else:
                _require(s.buffer._done is False and len(s.accumulator) == h.committed)
        # No native/scheduler callback may alter the retained body wait after checks.
        _require(self._scope_origin is s and self._scope is s
                 and self._received is h.received and self._received_snapshot is h.received
                 and self._committed is h.committed and self._committed_snapshot is h.committed
                 and self._pending is None and self._pending_snapshot is None
                 and self._read_intent is False and self._commit_intent is False
                 and self._initialization_origin is h.allocation
                 and self._stream_origin is h.allocation[1]
                 and self._hash_origin is h.allocation[2])
        return retirement

    def _retirement_current(self, retirement, *, released=False):
        NativeResultBodyOwner._retirement_local(self, retirement, released=released)
        waiter = retirement.wait.waiter
        SelectorReadiness._guard(waiter, actor=not released)
        SelectorReadiness._wake_guard(waiter)
        # Repeat every held wait/progress/custody predicate after the final boundary.
        return NativeResultBodyOwner._retirement_local(self, retirement, released=released)

    async def _read(self, count):
        part = None
        s = NativeResultBodyOwner._current(self)
        b = s.envelope_scope.write_scope
        _require(type(count) is int and 0 < count <= 65536 and self._pending is None)
        try:
            while True:
                _require(NativeResultBodyOwner._current(self) is s)
                before = self._received_snapshot
                committed = self._committed_snapshot
                allocation = self._initialization_origin
                buffer_meta = (s.buffer._header_size, s.buffer._body_size)
                self._read_intent = True
                try:
                    part = _RECV(b.sock, count)
                except BlockingIOError as error:
                    _require(type(error) is BlockingIOError and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._scope is s and self._scope_origin is s
                             and self._received is before and self._received_snapshot is before
                             and self._committed is committed
                             and self._committed_snapshot is committed
                             and self._initialization_origin is allocation
                             and self._read_intent is True and self._pending is None
                             and self._commit_intent is False)
                    self._read_intent = False
                    waiter = SelectorReadiness.__new__(SelectorReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorReadiness.__init__(waiter, b.sock)
                    native_scope, future = waiter._origin_scope, waiter._future_origin
                    SelectorReadiness._guard(waiter)
                    NativeResultBodyOwner._current(self)
                    _require(self._received is before and self._received_snapshot is before
                             and self._committed is committed
                             and self._committed_snapshot is committed
                             and self._scope is s and self._scope_origin is s
                             and self._initialization_origin is allocation
                             and self._initialization is allocation
                             and self._pending is None and self._pending_snapshot is None
                             and self._read_intent is False and self._commit_intent is False
                             and waiter._origin_scope is native_scope
                             and waiter._scope_snapshot is native_scope
                             and waiter._future_origin is future
                             and waiter._future_snapshot is future
                             and s.buffer._header_size is buffer_meta[0]
                             and s.buffer._body_size is buffer_meta[1]
                             and len(s.accumulator) == committed)
                    hold = _BodyWait(s, waiter, native_scope, future,
                        b.intent.end_ns, before, committed,
                        allocation, buffer_meta,
                        self._hash_origin.hexdigest(), self._stream_origin._received_snapshot)
                    try:
                        await SelectorReadiness.wait(waiter, hold.end)
                    except _ReadinessCancelledError as error:
                        _require(type(error) is _ReadinessCancelledError)
                        retirement = _BodyRetirement(_RETIRE_MINT, self, hold, error.retirement)
                        try:
                            NativeResultBodyOwner._retirement_current(self, retirement)
                        except BaseException:
                            self._io_unknown = True
                            raise FrameError("BI1_SIGNED_BODY_CANCEL_RETIREMENT_UNKNOWN") from None
                        self._cancel_receipt = self._cancel_receipt_snapshot = retirement
                        raise asyncio.CancelledError from None
                    _require(self._waiter is waiter and self._waiter_origin is waiter
                             and waiter._origin_scope is native_scope
                             and waiter._scope_snapshot is native_scope
                             and waiter._future_origin is future
                             and waiter._future_snapshot is future)
                    NativeResultBodyOwner._settled(self)
                    continue
                _require(type(part) is bytes)
                same = (self._scope is s and self._scope_origin is s
                        and self._received is before and self._received_snapshot is before
                        and self._read_intent is True and self._pending is None)
                self._pending = self._pending_snapshot = part
                self._received = self._received_snapshot = before + len(part)
                self._read_intent = False
                if not same:
                    self._io_unknown = True
                _require(same and 0 < len(part) <= count)
                _require(NativeResultBodyOwner._current(self) is s)
                return part
        finally:
            part = None

    async def receive(self):
        candidate = part = digest = header_wire = None
        s = NativeResultBodyOwner._local(self)
        _require(self._initialized is True and self._attempted is False and self._active is False)
        self._attempted = self._active = True
        s.envelope_scope.write_scope.channel._reading = True
        failed = cancelled = False
        try:
            NativeResultBodyOwner._current(self)
            remaining = s.envelope_fact.header.body_length
            while remaining:
                part = await NativeResultBodyOwner._read(self, min(65536, remaining))
                self._commit_intent = True
                BoundedResultBufferV2.feed(s.buffer, part)
                NativeResultBodyOwner._current(self)
                CommittedFrameDigest.feed(self._stream_origin, part)
                NativeResultBodyOwner._current(self)
                self._hash_origin.update(part)
                NativeResultBodyOwner._current(self)
                self._committed = self._committed_snapshot = self._committed + len(part)
                self._pending = self._pending_snapshot = None
                self._commit_intent = False
                remaining -= len(part)
                part = None
                NativeResultBodyOwner._current(self)
            digest = CommittedFrameDigest.finish(self._stream_origin)
            NativeResultBodyOwner._current(self)
            _require(hashlib.sha256(s.accumulator).hexdigest() == self._hash_origin.hexdigest())
            NativeResultBodyOwner._current(self)
            self._finish_attempted = True
            candidate = BoundedResultBufferV2.finish(s.buffer, s.challenge, s.epoch)
            NativeResultBodyOwner._current(self)
            compare_parent_snapshot(candidate[0], snapshot=s.context[1], parent_home=s.context[0])
            _require(candidate[0]["outcome"] == "OK" and candidate[0]["cleanup"] == {
                "known_fds_closed": True, "unknown_close": False}
                and (s.expected is None or candidate[0]["avatar_sha"] == s.expected))
            header_wire = _candidate_header_wire(candidate[0])
            body_sha = self._hash_origin.hexdigest()
            NativeResultBodyOwner._settled(self)
            NativeResultBodyOwner._current(self)
            _require(_candidate_header_wire(candidate[0]) == header_wire)
            self._candidate = self._candidate_snapshot = candidate
            self._fact = self._fact_snapshot = _BodyCandidate(
                _MINT, self, s, id(candidate), id(candidate[0]), id(candidate[1]), header_wire,
                digest.frame_sha256, body_sha, self._received_snapshot)
            self._validated = True  # private candidate only; native phase stays GO_SENT
            s.accumulator[:] = b"\x00" * len(s.accumulator)
            s.accumulator.clear()
        except asyncio.CancelledError:
            failed = cancelled = True
            if self._cancel_receipt_snapshot is None:
                self._io_unknown = True
        except BaseException:
            failed = True
        finally:
            candidate = part = digest = header_wire = None
            if failed:
                self._failed = True
                if self._read_intent or self._commit_intent:
                    self._io_unknown = True
                NativeResultBodyOwner.wipe(self)
            try:
                if failed:
                    NativeResultBodyOwner._settled(self)
                self._active = False
                s.envelope_scope.write_scope.channel._reading = False
            except BaseException:
                self._io_unknown = True
                failed = True
                self._failed = True
                self._validated = False
                NativeResultBodyOwner.wipe(self)
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_SIGNED_RESULT_BODY_VALIDATION_REFUSED") from None
        return True

    def _released(self, envelope):
        _require(type(self) is NativeResultBodyOwner and type(self._scope_origin) is _BodyScope
                 and self._scope is self._scope_origin and self._scope_origin.envelope is envelope
                 and self._active is False)
        s = self._scope_origin
        b = s.envelope_scope.write_scope
        _require(_TASK.done(b.allocation.task))
        w = self._waiter_origin
        _require(w is None or type(w) is SelectorReadiness)
        held = None if w is None else (w._origin_scope, w._future_origin,
            w._wake_binding_origin, w._handle_snapshot, w._handle_args_snapshot)
        allocation = self._initialization_origin
        receipt = self._cancel_receipt_snapshot
        try:
            NativeResultBodyOwner._settled(self)
            _require(self._cancel_receipt is receipt and self._cancel_receipt_snapshot is receipt)
            if receipt is not None:
                NativeResultBodyOwner._retirement_current(self, receipt, released=True)
            _require(self._scope is s and self._scope_origin is s and self._active is False
                     and self._read_intent is False and self._commit_intent is False
                     and self._pending is None and self._pending_snapshot is None
                     and self._io_unknown is False and self._waiter is w
                     and self._waiter_origin is w and self._initialization is allocation
                     and self._initialization_origin is allocation
                     and type(allocation) is tuple and len(allocation) == 3 and allocation[0] is s
                     and self._stream is allocation[1] and self._stream_origin is allocation[1]
                     and self._hash is allocation[2] and self._hash_origin is allocation[2]
                     and type(s.buffer) is BoundedResultBufferV2
                     and s.buffer._buffer is s.accumulator
                     and self._wipe_custody_origin is s.custody
                     and s.job is self._candidate_job_origin)
            if w is not None:
                _require(w._origin_scope is held[0] and w._scope_snapshot is held[0]
                         and w._future is held[1] and w._future_origin is held[1]
                         and w._future_snapshot is held[1]
                         and w._wake_binding is held[2] and w._wake_binding_origin is held[2]
                         and w._handle is held[3] and w._handle_snapshot is held[3]
                         and w._handle_args is held[4] and w._handle_args_snapshot is held[4])
        except BaseException:
            self._io_unknown = True
            raise FrameError("BI1_SIGNED_BODY_LOCAL_RETIREMENT_UNKNOWN") from None
