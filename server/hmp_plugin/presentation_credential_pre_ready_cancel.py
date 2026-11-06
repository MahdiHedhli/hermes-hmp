"""Fixed BEGIN-derived pre-READY CANCEL signature; no transport or settlement."""

from __future__ import annotations

import asyncio
import hashlib
from typing import NamedTuple

from .presentation_broker_codec import encode_frame
from .presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from .presentation_credential_begin_write import NativeBeginWriter, _BeginWriterScope
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_files import StartupRoleKeyFiles
from .presentation_credential_phase import _EXPECTED, check_commitment, check_complete_frame
from .presentation_credential_ready_read import NativeReadyReceiver, _ReadyReadRetirement
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError
from .presentation_remote_cleanup import _TASK, RemoteCleanupOwner, _TaskAllocation


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_PRE_READY_CANCEL_REFUSED")


class _PreReadyCancelScope(NamedTuple):
    cleanup: object
    producer: object
    writer: object
    begin: _BeginWriterScope
    receiver: object
    retirement: object
    allocation: object
    cleanup_refs: tuple
    expected: tuple
    pins: tuple

    def __repr__(self):
        return "<PreReadyCancelScope original-cleanup redacted>"


class NativePreReadyCancelCommitment:
    @classmethod
    def retain(cls, cleanup):
        _require(cls is NativePreReadyCancelCommitment and type(cleanup) is RemoteCleanupOwner
                 and type(cleanup._allocations_snapshot) is tuple
                 and len(cleanup._allocations_snapshot) == 2
                 and cleanup._allocations is cleanup._allocations_snapshot
                 and type(cleanup._allocations_snapshot[0]) is _TaskAllocation
                 and type(cleanup._allocations_snapshot[0].task) is _TASK
                 and asyncio.current_task() is cleanup._allocations_snapshot[0].task
                 and _TASK.cancelling(cleanup._allocations_snapshot[0].task) == 0
                 and cleanup._pre_ready_cancel_commitment is None
                 and cleanup._pre_ready_cancel_commitment_snapshot is None
                 and cleanup._credential_cancel_commitment is None
                 and cleanup._credential_cancel_commitment_snapshot is None
                 and cleanup._cancel_write_attempted is False
                 and cleanup._cancel_write_completed is False)
        producer = cleanup._credential_work_snapshot
        _require(type(producer) is NativePhaseWorkOwner and cleanup._credential_work is producer
                 and producer._ready_transition_snapshot is None
                 and producer._ready_transition is None
                 and type(producer._writer_snapshot) is NativeBeginWriter
                 and producer._writer is producer._writer_snapshot)
        writer = producer._writer_snapshot
        b = NativeBeginWriter._metadata(writer)
        receiver = writer._ready_receiver_snapshot
        _require(type(receiver) is NativeReadyReceiver and writer._ready_receiver is receiver)
        r = NativeReadyReceiver._metadata(receiver)
        _require(r.write_scope is b and r.writer is writer and b.producer is producer
                 and type(receiver._cancel_release_origin) is _ReadyReadRetirement)
        expected = dict(r.expected)
        expected.update(phase="CANCEL", role="gateway", direction="g2b", sequence=1)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _PreReadyCancelScope(
            cleanup, producer, writer, b, receiver, receiver._cancel_release_origin,
            cleanup._allocations_snapshot[0], cleanup._refs_snapshot,
            tuple(sorted(expected.items())), (b.refs[5].own_public, b.refs[5].peer_public))
        owner._attempted = owner._prepared = owner._complete = owner._failed = False
        owner._frame = owner._frame_snapshot = None
        owner._end = owner._end_snapshot = None
        owner._raw = owner._raw_snapshot = None
        # Retain before native guards/crypto. A refusal never permits replacement.
        cleanup._pre_ready_cancel_commitment = owner
        cleanup._pre_ready_cancel_commitment_snapshot = owner
        try:
            NativePreReadyCancelCommitment._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_PRE_READY_CANCEL_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<NativePreReadyCancelCommitment signed-data-only redacted>"

    def _metadata(self):
        _require(type(self) is NativePreReadyCancelCommitment
                 and type(self._scope) is _PreReadyCancelScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.cleanup) is RemoteCleanupOwner
                 and type(s.producer) is NativePhaseWorkOwner
                 and type(s.writer) is NativeBeginWriter and type(s.begin) is _BeginWriterScope
                 and NativeBeginWriter._metadata(s.writer) is s.begin
                 and type(s.receiver) is NativeReadyReceiver
                 and NativeReadyReceiver._metadata(s.receiver).write_scope is s.begin
                 and type(s.retirement) is _ReadyReadRetirement
                 and s.receiver._cancel_release_origin is s.retirement
                 and s.receiver._cancel_release is s.retirement
                 and s.begin.producer is s.producer and s.begin.refs is s.producer._refs_snapshot
                 and s.producer._writer is s.writer and s.producer._writer_snapshot is s.writer
                 and s.producer._ready_transition is None
                 and s.producer._ready_transition_snapshot is None
                 and type(s.cleanup_refs) is tuple and len(s.cleanup_refs) == 12
                 and s.cleanup._refs is s.cleanup_refs
                 and s.cleanup._refs_snapshot is s.cleanup_refs
                 and s.cleanup_refs[3] is s.begin.channel
                 and s.cleanup._pre_ready_cancel_commitment is self
                 and s.cleanup._pre_ready_cancel_commitment_snapshot is self
                 and s.cleanup._credential_cancel_commitment is None
                 and s.cleanup._credential_cancel_commitment_snapshot is None
                 and type(s.allocation) is _TaskAllocation and type(s.allocation.task) is _TASK
                 and s.cleanup._allocations is s.cleanup._allocations_snapshot
                 and type(s.cleanup._allocations_snapshot) is tuple
                 and len(s.cleanup._allocations_snapshot) == 2
                 and s.cleanup._allocations_snapshot[0] is s.allocation
                 and s.begin.channel._go_write_intent_snapshot is None
                 and s.begin.channel._go_write_intent is None
                 and s.begin.channel._go_write_fact_snapshot is None
                 and s.begin.channel._go_write_fact is None
                 and s.cleanup._cancel_write_completed is False
                 and all(type(v) is bool for v in (
                     self._attempted, self._prepared, self._complete, self._failed))
                 and self._frame is self._frame_snapshot and self._end is self._end_snapshot
                 and self._raw is self._raw_snapshot
                 and type(s.expected) is tuple and len(s.expected) == len(_EXPECTED)
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (
                             int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in s.expected)
                 and {row[0] for row in s.expected} == _EXPECTED
                 and type(s.pins) is tuple and len(s.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in s.pins)
                 and s.pins == (s.begin.refs[5].own_public, s.begin.refs[5].peer_public))
        expected = dict(s.receiver._scope_origin.expected)
        expected.update(phase="CANCEL", role="gateway", direction="g2b", sequence=1)
        _require(s.expected == tuple(sorted(expected.items())))
        if self._prepared:
            _require(self._attempted is True and type(self._end) is int
                     and type(self._frame) is bytes and 0 < len(self._frame) <= 1048
                     and self._frame is s.cleanup._cancel_wire_snapshot
                     and self._frame is s.cleanup._cancel_wire
                     and type(s.cleanup._cancel_end_snapshot) is int
                     and s.cleanup._cancel_end_snapshot == self._end
                     and s.cleanup._cancel_end is s.cleanup._cancel_end_snapshot
                     and type(s.cleanup._cancel_sequence_snapshot) is int
                     and s.cleanup._cancel_sequence_snapshot == 1
                     and s.cleanup._cancel_sequence is s.cleanup._cancel_sequence_snapshot
                     and s.cleanup._cancel_write_attempted is True
                     and self._frame == encode_frame(s.begin.intent.binding, "CANCEL", 1,
                         CancellationWindow(self._end - CLEANUP_NS, self._end).encode(), version=2))
        else:
            _require(self._frame is None and self._end is None)
        if self._complete:
            _require(self._prepared is True and type(self._raw) is bytes
                     and 0 < len(self._raw) <= 2048)
        else:
            _require(self._raw is None)
        return s

    def _guard(self):
        s = NativePreReadyCancelCommitment._metadata(self)
        _require(asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0 and self._failed is False)
        material = NativePhaseWorkOwner._cleanup_material(s.producer, s.cleanup)
        _require(material[0] is s.begin.remote and material[2] is s.begin.channel)
        NativeReadyReceiver._released(s.receiver, s.begin.channel)
        remaining = RemoteCleanupOwner._remaining(s.cleanup)
        _require(type(remaining) is float and remaining > 0)
        NativePhaseWorkOwner._cleanup_material(s.producer, s.cleanup)
        NativeReadyReceiver._released(s.receiver, s.begin.channel)
        retained = NativePhaseWorkOwner._retained_material(s.producer)
        _require(retained[0] is s.begin.remote and retained[2] is s.begin.channel)
        # The released-reader proof can cross native descriptor checks. Seal
        # retained role material afterwards without another native callback.
        keys, handshake = s.begin.refs[3], s.begin.refs[2]
        _require(type(keys) is StartupRoleKeyFiles and keys._ready is True
                 and keys._refused is False and keys._private_key is s.begin.refs[4]
                 and keys._selection is s.begin.refs[5]
                 and handshake._keys is keys and handshake._key is s.begin.refs[4]
                 and handshake._key_origin is s.begin.refs[4]
                 and handshake._selection is s.begin.refs[5]
                 and handshake._selection_origin is s.begin.refs[5]
                 and handshake._refused is False and handshake._io_unknown is False
                 and s.cleanup._intent is True and s.cleanup._unknown is False
                 and s.cleanup._work_joined is True and _TASK.done(s.begin.allocation.task)
                 and s.cleanup._refs is s.cleanup_refs
                 and s.cleanup._refs_snapshot is s.cleanup_refs
                 and s.cleanup._remote_snapshot is s.begin.remote
                 and s.begin.remote._cleanup_budget is s.cleanup_refs[8]
                 and s.begin.remote._cleanup_budget_snapshot is s.cleanup_refs[8])
        _require(NativePreReadyCancelCommitment._metadata(self) is s
                 and asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0)
        original, _, end, failed = CancellationBudget.inspect(s.cleanup_refs[8])
        _require(type(original) is int and original == s.begin.intent.end_ns
                 and type(end) is int and failed is False
                 and (not self._prepared or end == self._end))
        return s

    def _begin_current(self):
        s = NativePreReadyCancelCommitment._guard(self)
        expected = dict(s.expected)
        expected.update(phase="BEGIN", sequence=0)
        checked = check_commitment(s.begin.raw, sender_public=s.pins[0],
                                   receiver_public=s.pins[1], expected=expected)
        check_complete_frame(checked, s.begin.frame_bytes, binding=s.begin.intent.binding)
        _require(NativePreReadyCancelCommitment._guard(self) is s)
        return s

    def prepare(self):
        s = NativePreReadyCancelCommitment._metadata(self)
        _require(asyncio.current_task() is s.allocation.task
                 and _TASK.cancelling(s.allocation.task) == 0
                 and self._attempted is False and self._failed is False)
        self._attempted = True
        try:
            _require(NativePreReadyCancelCommitment._begin_current(self) is s)
            frame = RemoteCleanupOwner._prepare_cancel(s.cleanup, s.begin.channel)
            self._frame = self._frame_snapshot = frame
            self._end = self._end_snapshot = s.cleanup._cancel_end_snapshot
            self._prepared = True
            _require(NativePreReadyCancelCommitment._begin_current(self) is s)
            statement = dict(s.expected)
            statement.update(v=1, family="phase", alg="Ed25519",
                key_id=hashlib.sha256(s.pins[0]).hexdigest(),
                peer_key_id=hashlib.sha256(s.pins[1]).hexdigest(),
                frame_sha256=hashlib.sha256(frame).hexdigest(), frame_length=len(frame))
            data = signing_bytes(statement)
            _require(NativePreReadyCancelCommitment._begin_current(self) is s)
            raw = encode_record(statement, s.begin.refs[4].sign(data))
            _require(NativePreReadyCancelCommitment._begin_current(self) is s)
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            check_complete_frame(checked, frame, binding=s.begin.intent.binding)
            _require(NativePreReadyCancelCommitment._begin_current(self) is s)
            self._raw = self._raw_snapshot = raw
            self._complete = True
            return raw  # signed data only; no IO/native completion or remote settlement
        except BaseException:
            self._failed = True
            raise
