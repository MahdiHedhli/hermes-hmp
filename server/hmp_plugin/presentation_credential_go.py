"""Fixed GO commitment from actual original native GO_INTENT; no wire authority."""

from __future__ import annotations

import asyncio
import hashlib
from typing import NamedTuple

from .presentation_broker_codec import encode_frame
from .presentation_broker_service import SocketChannel
from .presentation_clock import NativeClockOwner
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_phase import check_commitment, check_complete_frame
from .presentation_credential_ready_read import _EXPECTED
from .presentation_credential_ready_transition import NativeReadyTransition
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError, RemotePhase
from .presentation_remote import RemoteOperationOwner, _GoAdmission
from .presentation_remote_cleanup import _TASK, _TaskAllocation


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_GO_COMMITMENT_REFUSED")


class _GoCommitmentScope(NamedTuple):
    producer: object
    transition: object
    ready_scope: object
    admission: object
    frame: bytes
    expected: tuple
    pins: tuple

    def __repr__(self):
        return "<GoCommitmentScope original-native-intent redacted>"


class NativeGoCommitment:
    @classmethod
    def retain(cls, producer):
        _require(cls is NativeGoCommitment and type(producer) is NativePhaseWorkOwner
                 and type(producer._refs) is tuple and len(producer._refs) == 12
                 and producer._refs is producer._refs_snapshot
                 and type(producer._refs[6]) is _TaskAllocation
                 and asyncio.current_task() is producer._refs[6].task
                 and _TASK.cancelling(producer._refs[6].task) == 0
                 and producer._go_commitment is None and producer._go_commitment_snapshot is None)
        transition = producer._ready_transition_snapshot
        _require(type(transition) is NativeReadyTransition
                 and producer._ready_transition is transition)
        ready = NativeReadyTransition._metadata(transition)
        b = ready.read_scope.write_scope
        _require(ready.producer is producer and b.producer is producer
                 and transition._complete is True and transition._failed is False
                 and type(b.remote._go_admission_snapshot) is _GoAdmission)
        expected = dict(ready.read_scope.expected)
        expected.update(phase="GO", role="gateway", direction="g2b", sequence=1)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _GoCommitmentScope(
            producer, transition, ready, b.remote._go_admission_snapshot,
            encode_frame(b.intent.binding, "GO", 1, b"", version=2),
            tuple(sorted(expected.items())), (b.refs[5].own_public, b.refs[5].peer_public))
        owner._attempted = owner._complete = owner._failed = False
        owner._raw = owner._raw_snapshot = None
        producer._go_commitment = producer._go_commitment_snapshot = owner
        try:
            NativeGoCommitment._guard(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_GO_COMMITMENT_REFUSED") from None

    def __repr__(self):
        return "<NativeGoCommitment signed-data-only redacted>"

    def _metadata(self):
        _require(type(self) is NativeGoCommitment and type(self._scope) is _GoCommitmentScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.producer) is NativePhaseWorkOwner
                 and type(s.transition) is NativeReadyTransition
                 and NativeReadyTransition._metadata(s.transition) is s.ready_scope
                 and s.ready_scope.producer is s.producer
                 and s.transition._complete is True and s.transition._failed is False
                 and s.producer._go_commitment is self
                 and s.producer._go_commitment_snapshot is self
                 and type(s.admission) is _GoAdmission
                 and type(s.frame) is bytes and type(s.expected) is tuple
                 and len(s.expected) == len(_EXPECTED)
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in s.expected)
                 and {row[0] for row in s.expected} == _EXPECTED
                 and type(s.pins) is tuple and len(s.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in s.pins)
                 and all(type(v) is bool for v in (self._attempted, self._complete, self._failed))
                 and self._raw is self._raw_snapshot)
        b = s.ready_scope.read_scope.write_scope
        fixed_expected = dict(s.ready_scope.read_scope.expected)
        fixed_expected.update(phase="GO", role="gateway", direction="g2b", sequence=1)
        _require(s.expected == tuple(sorted(fixed_expected.items())))
        _require(b.producer is s.producer and b.remote._go_admission is s.admission
                 and b.remote._go_admission_snapshot is s.admission
                 and s.admission.remote is b.remote and s.admission.work is b.allocation
                 and s.admission.packet is b.intent.packet
                 and s.admission.binding is b.intent.binding
                 and type(s.admission.end_ns) is int and type(b.intent.end_ns) is int
                 and s.admission.end_ns == b.intent.end_ns
                 and s.frame == encode_frame(b.intent.binding, "GO", 1, b"", version=2)
                 and s.pins == (b.refs[5].own_public, b.refs[5].peer_public))
        if self._complete:
            _require(self._attempted is True and type(self._raw) is bytes
                     and 0 < len(self._raw) <= 2048)
        else:
            _require(self._raw is None)
        return s

    def _guard(self):
        s = NativeGoCommitment._metadata(self)
        b = s.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0 and self._failed is False)
        _require(NativePhaseWorkOwner._material_local(s.producer)[0] is b.remote)
        RemoteOperationOwner._check(b.remote, RemotePhase.GO_INTENT)
        _require(b.remote._go_admission_used is True
                 and b.channel._go_write_intent is None and b.channel._go_write_fact is None
                 and b.channel._writing is False and b.channel._reading is False)
        SocketChannel._check(b.channel)
        _require(SocketChannel._qualified_clock(b.channel) is b.refs[8])
        now = NativeClockOwner.sample(b.refs[8])
        _require(NativeGoCommitment._metadata(self) is s)
        _require(NativePhaseWorkOwner._material_local(s.producer)[0] is b.remote)
        RemoteOperationOwner._check(b.remote, RemotePhase.GO_INTENT)
        _require(type(now) is int and 0 <= now < b.intent.end_ns
                 and NativeGoCommitment._metadata(self) is s)
        return s

    def _ready_current(self):
        s = NativeGoCommitment._guard(self)
        r, fact = s.ready_scope.read_scope, s.ready_scope.read_fact
        checked = check_commitment(fact.raw, sender_public=r.pins[0], receiver_public=r.pins[1],
                                   expected=dict(r.expected))
        check_complete_frame(checked, fact.frame, binding=r.write_scope.intent.binding)
        _require(NativeGoCommitment._guard(self) is s)
        return s

    def prepare(self):
        s = NativeGoCommitment._metadata(self)
        b = s.ready_scope.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and self._attempted is False and self._failed is False)
        self._attempted = True
        try:
            _require(NativeGoCommitment._ready_current(self) is s)
            statement = dict(s.expected)
            statement.update(v=1, family="phase", alg="Ed25519",
                key_id=hashlib.sha256(s.pins[0]).hexdigest(),
                peer_key_id=hashlib.sha256(s.pins[1]).hexdigest(),
                frame_sha256=hashlib.sha256(s.frame).hexdigest(), frame_length=len(s.frame))
            data = signing_bytes(statement)
            _require(NativeGoCommitment._ready_current(self) is s)
            raw = encode_record(statement, b.refs[4].sign(data))
            _require(NativeGoCommitment._ready_current(self) is s)
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            check_complete_frame(checked, s.frame, binding=b.intent.binding)
            _require(NativeGoCommitment._ready_current(self) is s)
            self._raw = self._raw_snapshot = raw
            self._complete = True
            return raw  # signed GO data only, not GO_SENT/native write/worker receipt
        except BaseException:
            self._failed = True
            raise
