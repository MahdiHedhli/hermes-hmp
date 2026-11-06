"""Fixed CANCEL signature from original cleanup preparation; no socket authority."""

from __future__ import annotations

import asyncio
import hashlib
from typing import NamedTuple

from .presentation_broker_codec import decode_header, encode_frame, header_size
from .presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_phase import _EXPECTED, check_commitment, check_complete_frame
from .presentation_credential_ready_transition import NativeReadyTransition
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError
from .presentation_remote_cleanup import _TASK, RemoteCleanupOwner, _TaskAllocation


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_CANCEL_COMMITMENT_REFUSED")


class _CancelCommitmentScope(NamedTuple):
    cleanup: object
    producer: object
    cleanup_refs: tuple
    work_refs: tuple
    allocation: object
    transition: object
    ready_scope: object
    pins: tuple

    def __repr__(self):
        return "<CancelCommitmentScope original-cleanup redacted>"


class NativeCancelCommitment:
    @classmethod
    def retain(cls, cleanup):
        _require(cls is NativeCancelCommitment and type(cleanup) is RemoteCleanupOwner
                 and type(cleanup._allocations_snapshot) is tuple
                 and len(cleanup._allocations_snapshot) == 2
                 and cleanup._allocations is cleanup._allocations_snapshot
                 and type(cleanup._allocations_snapshot[0]) is _TaskAllocation
                 and type(cleanup._allocations_snapshot[0].task) is _TASK
                 and asyncio.current_task() is cleanup._allocations_snapshot[0].task
                 and _TASK.cancelling(cleanup._allocations_snapshot[0].task) == 0
                 and cleanup._credential_cancel_commitment is None
                 and cleanup._credential_cancel_commitment_snapshot is None
                 and cleanup._cancel_write_attempted is False
                 and cleanup._cancel_write_completed is False
                 and cleanup._cancel_wire is None and cleanup._cancel_wire_snapshot is None
                 and cleanup._cancel_end is None and cleanup._cancel_end_snapshot is None
                 and cleanup._cancel_sequence is None and cleanup._cancel_sequence_snapshot is None)
        producer = cleanup._credential_work_snapshot
        _require(type(producer) is NativePhaseWorkOwner and cleanup._credential_work is producer
                 and type(producer._refs_snapshot) is tuple and len(producer._refs_snapshot) == 12
                 and producer._refs is producer._refs_snapshot
                 and type(cleanup._refs_snapshot) is tuple and len(cleanup._refs_snapshot) == 12
                 and cleanup._refs is cleanup._refs_snapshot)
        transition = producer._ready_transition_snapshot
        _require(type(transition) is NativeReadyTransition
                 and producer._ready_transition is transition)
        ready = NativeReadyTransition._metadata(transition)
        b = ready.read_scope.write_scope
        _require(ready.producer is producer and b.producer is producer
                 and transition._complete is True and transition._failed is False
                 and cleanup._refs_snapshot[3] is b.channel)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _CancelCommitmentScope(
            cleanup, producer, cleanup._refs_snapshot, producer._refs_snapshot,
            cleanup._allocations_snapshot[0], transition, ready,
            (b.refs[5].own_public, b.refs[5].peer_public))
        owner._attempted = owner._prepared = owner._complete = owner._failed = False
        owner._frame = owner._frame_snapshot = None
        owner._end = owner._end_snapshot = None
        owner._sequence = owner._sequence_snapshot = None
        owner._expected = owner._expected_snapshot = None
        owner._raw = owner._raw_snapshot = None
        owner._writer = owner._writer_snapshot = None
        cleanup._credential_cancel_commitment = owner
        cleanup._credential_cancel_commitment_snapshot = owner
        try:
            NativeCancelCommitment._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_CANCEL_COMMITMENT_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<NativeCancelCommitment original-window signed-data-only redacted>"

    def _metadata(self):
        _require(type(self) is NativeCancelCommitment
                 and type(self._scope) is _CancelCommitmentScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.cleanup) is RemoteCleanupOwner and type(s.producer) is NativePhaseWorkOwner
                 and type(s.cleanup_refs) is tuple and len(s.cleanup_refs) == 12
                 and type(s.work_refs) is tuple and len(s.work_refs) == 12
                 and s.cleanup._refs is s.cleanup_refs
                 and s.cleanup._refs_snapshot is s.cleanup_refs
                 and s.producer._refs is s.work_refs and s.producer._refs_snapshot is s.work_refs
                 and type(s.transition) is NativeReadyTransition
                 and NativeReadyTransition._metadata(s.transition) is s.ready_scope
                 and s.ready_scope.producer is s.producer
                 and s.transition._complete is True and s.transition._failed is False
                 and s.cleanup._credential_cancel_commitment is self
                 and s.cleanup._credential_cancel_commitment_snapshot is self
                 and type(s.allocation) is _TaskAllocation and type(s.allocation.task) is _TASK
                 and type(s.cleanup._allocations_snapshot) is tuple
                 and len(s.cleanup._allocations_snapshot) == 2
                 and s.cleanup._allocations is s.cleanup._allocations_snapshot
                 and s.cleanup._allocations_snapshot[0] is s.allocation
                 and type(s.pins) is tuple and len(s.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in s.pins)
                 and self._frame is self._frame_snapshot and self._end is self._end_snapshot
                 and self._sequence is self._sequence_snapshot
                 and self._expected is self._expected_snapshot and self._raw is self._raw_snapshot
                 and all(type(v) is bool for v in (
                     self._attempted, self._prepared, self._complete, self._failed)))
        b = s.ready_scope.read_scope.write_scope
        _require(b.refs is s.work_refs and s.cleanup_refs[3] is b.channel
                 and s.work_refs[0] is s.cleanup and s.work_refs[1] is b.remote
                 and s.pins == (b.refs[5].own_public, b.refs[5].peer_public))
        if self._prepared:
            _require(self._attempted is True and type(self._frame) is bytes
                     and 0 < len(self._frame) <= 1048 and type(self._end) is int
                     and type(self._sequence) is int and self._sequence in (1, 2)
                     and self._frame is s.cleanup._cancel_wire_snapshot
                     and s.cleanup._cancel_wire is self._frame
                     and type(s.cleanup._cancel_end_snapshot) is int
                     and type(s.cleanup._cancel_sequence_snapshot) is int
                     and self._end == s.cleanup._cancel_end_snapshot
                     and self._sequence == s.cleanup._cancel_sequence_snapshot
                     and s.cleanup._cancel_write_attempted is True
                     and type(self._expected) is tuple and len(self._expected) == len(_EXPECTED)
                     and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                             and type(row[1]) is (
                                 int if row[0] in ("sequence", "work_end_ns") else str)
                             for row in self._expected)
                     and {row[0] for row in self._expected} == _EXPECTED)
            fixed = dict(s.ready_scope.read_scope.expected)
            fixed.update(phase="CANCEL", role="gateway", direction="g2b", sequence=self._sequence)
            _require(self._expected == tuple(sorted(fixed.items())))
            end_header = 8 + header_size(self._frame[:8])
            header = decode_header(self._frame[:end_header], expected=b.intent.binding,
                                   expected_version=2)
            window = CancellationWindow.decode(self._frame[end_header:])
            _require(header.kind == "CANCEL" and header.sequence == self._sequence
                     and header.body_length == 16 and window.end_ns == self._end
                     and window.start_ns == self._end - CLEANUP_NS
                     and self._frame == encode_frame(b.intent.binding, "CANCEL", self._sequence,
                                                      window.encode(), version=2)
                     and self._sequence == (
                         2 if b.channel._go_write_fact_snapshot is not None else 1))
        else:
            _require(self._frame is None and self._end is None and self._sequence is None
                     and self._expected is None)
        _require(type(s.cleanup._cancel_write_completed) is bool)
        if s.cleanup._cancel_write_completed:
            from .presentation_credential_cancel_write import NativeCancelWriter
            _require(type(self._writer_snapshot) is NativeCancelWriter
                     and self._writer is self._writer_snapshot)
            NativeCancelWriter._native_completed(self._writer_snapshot, self)
        if self._complete:
            _require(self._prepared is True and type(self._raw) is bytes
                     and 0 < len(self._raw) <= 2048)
        else:
            _require(self._raw is None)
        return s

    def _guard(self):
        s = NativeCancelCommitment._metadata(self)
        b = s.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0 and self._failed is False
                 and s.cleanup._cancel_write_completed is False)
        material = NativePhaseWorkOwner._cleanup_material(s.producer, s.cleanup)
        _require(material[0] is b.remote and material[2] is b.channel)
        remaining = RemoteCleanupOwner._remaining(s.cleanup)
        _require(NativeCancelCommitment._metadata(self) is s)
        NativePhaseWorkOwner._cleanup_material(s.producer, s.cleanup)
        _require(type(remaining) is float and remaining > 0
                 and NativeCancelCommitment._metadata(self) is s)
        original, _, end, failed = CancellationBudget.inspect(s.cleanup_refs[8])
        _require(type(original) is int and original == b.intent.end_ns
                 and type(end) is int and failed is False
                 and (not self._prepared or end == self._end))
        return s

    def _ready_current(self):
        s = NativeCancelCommitment._guard(self)
        r, fact = s.ready_scope.read_scope, s.ready_scope.read_fact
        checked = check_commitment(fact.raw, sender_public=r.pins[0], receiver_public=r.pins[1],
                                   expected=dict(r.expected))
        check_complete_frame(checked, fact.frame, binding=r.write_scope.intent.binding)
        _require(NativeCancelCommitment._guard(self) is s)
        return s

    def prepare(self):
        s = NativeCancelCommitment._metadata(self)
        b = s.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0
                 and self._attempted is False and self._failed is False)
        self._attempted = True
        try:
            _require(NativeCancelCommitment._ready_current(self) is s)
            frame = RemoteCleanupOwner._prepare_cancel(s.cleanup, b.channel)
            # Native preparation is already consumed even if subsequent checks fail.
            _require(type(frame) is bytes and frame is s.cleanup._cancel_wire_snapshot)
            self._frame = self._frame_snapshot = frame
            self._end = self._end_snapshot = s.cleanup._cancel_end_snapshot
            self._sequence = self._sequence_snapshot = s.cleanup._cancel_sequence_snapshot
            fixed = dict(s.ready_scope.read_scope.expected)
            fixed.update(phase="CANCEL", role="gateway", direction="g2b", sequence=self._sequence)
            self._expected = self._expected_snapshot = tuple(sorted(fixed.items()))
            self._prepared = True
            _require(NativeCancelCommitment._ready_current(self) is s)
            statement = dict(self._expected)
            statement.update(v=1, family="phase", alg="Ed25519",
                key_id=hashlib.sha256(s.pins[0]).hexdigest(),
                peer_key_id=hashlib.sha256(s.pins[1]).hexdigest(),
                frame_sha256=hashlib.sha256(frame).hexdigest(), frame_length=len(frame))
            data = signing_bytes(statement)
            _require(NativeCancelCommitment._ready_current(self) is s)
            raw = encode_record(statement, s.work_refs[4].sign(data))
            _require(NativeCancelCommitment._ready_current(self) is s)
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(self._expected))
            check_complete_frame(checked, frame, binding=b.intent.binding)
            _require(NativeCancelCommitment._ready_current(self) is s)
            self._raw = self._raw_snapshot = raw
            self._complete = True
            return raw  # no socket write/completion/remote custody evidence
        except BaseException:
            self._failed = True
            raise
