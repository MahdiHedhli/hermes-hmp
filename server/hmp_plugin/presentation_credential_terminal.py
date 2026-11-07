"""Original signed RESULT producer's one-shot TERMINAL/2 envelope; no IO.

This is bounded signed DATA, not trusted runtime qualification, transport,
terminal acceptance, ACK or native release. It never retains image bytes.
"""
from __future__ import annotations

import hashlib
from typing import NamedTuple

from .presentation_broker_codec import TERMINAL_LIMIT, BrokerHeader, encode_frame
from .presentation_credential_codec import RECORD_LIMIT, encode_record, signing_bytes
from .presentation_credential_phase import (
    _EXPECTED,
    ConsistentCommitment,
    check_commitment,
    check_complete_frame,
)
from .presentation_credential_result_completed import current as completed_result
from .presentation_credential_result_write import _ResultTransfer
from .presentation_jobs import FrameError
from .presentation_terminal_claim import (
    _HANDOFF_MINT,
    CLAIM_LIMIT,
    LocalStartedProducer,
    StartedClaim,
    TerminalHandoff,
    _FrozenLocalHandoff,
    _ProducerScope,
    _values,
    decode_handoff,
)

_SHA256 = hashlib.sha256


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_TERMINAL_EXPORT_REFUSED")


class _Scope(NamedTuple):
    local: LocalStartedProducer
    producer_scope: _ProducerScope
    claim: object
    transfer: _ResultTransfer
    refs: tuple
    expected: tuple
    pins: tuple

    def __repr__(self):
        return "<SignedTerminalScope original-service redacted>"


class _FrozenTerminal(NamedTuple):
    owner: object
    scope: _Scope
    handoff: _FrozenLocalHandoff
    raw: bytes
    frame: bytes
    checked: ConsistentCommitment

    def __repr__(self):
        return "<SignedTerminalEnvelope bounded-DATA no-IO-or-release>"


class CredentialTerminalProducer:
    @classmethod
    def retain(cls, local):
        _require(cls is CredentialTerminalProducer and type(local) is LocalStartedProducer)
        LocalStartedProducer._metadata_guard(local)  # original service actor before latch
        _require(local._signed_exporter is None and local._signed_exporter_origin is None
                 and local._signed_exporter_cell is None and local._handoff_attempted is False)
        s, transfer = local._scope_snapshot, local._transfer_snapshot
        _require(type(s) is _ProducerScope and type(transfer) is _ResultTransfer)
        result = transfer.scope.result_scope
        rows = result.expected
        _require(type(rows) is tuple and len(rows) == len(_EXPECTED)
                 and all(type(r) is tuple and len(r) == 2 and type(r[0]) is str
                         and type(r[1]) is (int if r[0] in ("sequence", "work_end_ns") else str)
                         for r in rows) and {r[0] for r in rows} == _EXPECTED
                 and type(result.pins) is tuple and len(result.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in result.pins))
        expected = dict(rows)
        _require(expected["phase"] == "RESULT" and expected["sequence"] == 1)
        expected.update(phase="TERMINAL", sequence=2)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_origin = _Scope(local, s, local._claim_snapshot,
            transfer, result.refs, tuple(sorted(expected.items())), result.pins)
        owner._scope_cell = (owner, owner._scope_origin)
        owner._attempted = owner._failed = owner._complete = False
        owner._handoff = owner._handoff_origin = owner._handoff_cell = None
        owner._frozen = owner._frozen_origin = owner._frozen_cell = None
        local._signed_exporter = local._signed_exporter_origin = owner
        local._signed_exporter_cell = (local, owner)
        failed = False
        try:
            CredentialTerminalProducer._current(owner)
            return owner
        except BaseException:
            owner._failed = failed = True
        if failed:
            raise FrameError("BI1_SIGNED_TERMINAL_ACQUISITION_UNKNOWN") from None

    def __repr__(self):
        return "<CredentialTerminalProducer one-shot no-transport redacted>"

    def _metadata(self):
        _require(type(self) is CredentialTerminalProducer and type(self._scope_origin) is _Scope
                 and self._scope is self._scope_origin
                 and type(self._scope_cell) is tuple and len(self._scope_cell) == 2
                 and self._scope_cell[0] is self and self._scope_cell[1] is self._scope_origin
                 and self._failed is False
                 and all(type(v) is bool for v in (self._attempted, self._complete)))
        s = self._scope_origin
        _require(type(s.local) is LocalStartedProducer
                 and s.local._signed_exporter is self and s.local._signed_exporter_origin is self
                 and type(s.local._signed_exporter_cell) is tuple
                 and len(s.local._signed_exporter_cell) == 2
                 and s.local._signed_exporter_cell[0] is s.local
                 and s.local._signed_exporter_cell[1] is self
                 and s.local._scope is s.producer_scope
                 and s.local._scope_snapshot is s.producer_scope
                 and s.local._claim_snapshot is s.claim and type(s.claim) is StartedClaim
                 and s.local._transfer_snapshot is s.transfer
                 and type(s.transfer) is _ResultTransfer
                 and s.transfer.scope.result_scope.refs is s.refs
                 and s.transfer.scope.result_scope.pins is s.pins)
        LocalStartedProducer._metadata_guard(s.local)
        if self._handoff_origin is not None:
            handoff = self._handoff_origin
            _require(type(handoff) is _FrozenLocalHandoff and handoff.mint is _HANDOFF_MINT
                     and self._handoff is handoff
                     and type(self._handoff_cell) is tuple and len(self._handoff_cell) == 2
                     and self._handoff_cell[0] is self and self._handoff_cell[1] is handoff
                     and s.local._handoff is handoff and s.local._handoff_snapshot is handoff
                     and handoff.producer is s.local and handoff.scope is s.producer_scope
                     and handoff.claim is s.claim and handoff.cleanup_end is None
                     and handoff.budget is s.producer_scope.control_scope[3]
                     and s.local._handoff_failed is False
                     and type(handoff.wire) is bytes and 0 < len(handoff.wire) <= CLAIM_LIMIT)
        if self._complete:
            f = self._frozen_origin
            _require(type(f) is _FrozenTerminal and self._frozen is f
                     and type(self._frozen_cell) is tuple and len(self._frozen_cell) == 2
                     and self._frozen_cell[0] is self and self._frozen_cell[1] is f
                     and f.owner is self and f.scope is s and f.handoff is self._handoff_origin
                     and type(f.raw) is bytes and 0 < len(f.raw) <= RECORD_LIMIT
                     and type(f.frame) is bytes and 0 < len(f.frame) <= TERMINAL_LIMIT + 1032
                     and type(f.checked) is ConsistentCommitment)
        return s

    def _current(self):
        s = CredentialTerminalProducer._metadata(self)
        _require(LocalStartedProducer._current(s.local) is False)
        _require(completed_result(s.transfer.owner) is s.transfer)
        _require(CredentialTerminalProducer._metadata(self) is s)
        return s

    def prepare(self):
        s = CredentialTerminalProducer._metadata(self)
        _require(self._attempted is False)
        self._attempted = True
        failed = False
        raw = frame = statement = None
        try:
            _require(CredentialTerminalProducer._current(self) is s)
            handoff = s.local.freeze_handoff_data()
            self._handoff = self._handoff_origin = handoff
            self._handoff_cell = (self, handoff)
            _require(CredentialTerminalProducer._current(self) is s)
            decoded = decode_handoff(handoff.wire)
            _require(type(decoded) is TerminalHandoff and type(decoded.claim) is StartedClaim)
            _values(decoded.claim)
            _values(s.claim)
            _require(decoded.claim == s.claim and decoded.cleanup is None)
            handoff_sha = _SHA256(handoff.wire).hexdigest()
            _require(type(handoff_sha) is str and type(handoff.sha256) is str
                     and handoff_sha == handoff.sha256)
            _require(CredentialTerminalProducer._current(self) is s)
            frame = encode_frame(s.producer_scope.record.binding, "TERMINAL", 2,
                                 handoff.wire, version=2)
            _require(type(frame) is bytes and len(frame) <= TERMINAL_LIMIT + 1032)
            digest = _SHA256(frame).hexdigest()
            _require(type(digest) is str and len(digest) == 64)
            statement = dict(s.expected)
            statement.update(v=1, family="phase", alg="Ed25519",
                key_id=_SHA256(s.pins[0]).hexdigest(),
                peer_key_id=_SHA256(s.pins[1]).hexdigest(),
                frame_sha256=digest, frame_length=len(frame))
            data = signing_bytes(statement)
            _require(CredentialTerminalProducer._current(self) is s)
            raw = encode_record(statement, s.refs[12].sign(data))
            _require(CredentialTerminalProducer._current(self) is s)
            _require(type(raw) is bytes and 0 < len(raw) <= RECORD_LIMIT)
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            _require(type(checked) is ConsistentCommitment)
            header = check_complete_frame(checked, frame, binding=s.producer_scope.record.binding)
            _require(type(header) is BrokerHeader and type(header.kind) is str
                     and type(header.sequence) is int and type(header.body_length) is int
                     and header.kind == "TERMINAL" and header.sequence == 2
                     and header.body_length == len(handoff.wire)
                     and frame[-len(handoff.wire):] == handoff.wire)
            _require(CredentialTerminalProducer._current(self) is s)
            frozen = _FrozenTerminal(self, s, handoff, raw, frame, checked)
            self._frozen = self._frozen_origin = frozen
            self._frozen_cell = (self, frozen)
            self._complete = True
            return frozen
        except BaseException:
            self._failed = failed = True
        finally:
            raw = frame = statement = None
        if failed:
            raise FrameError("BI1_SIGNED_TERMINAL_PREPARE_UNKNOWN") from None
