"""Original service fixed worker-GO relay; local delivery only, no result/release."""

from __future__ import annotations

import asyncio
import os
import threading
from io import FileIO
from typing import NamedTuple

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_child import BrokerChildOwner
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_registry import BrokerRegistry, _State
from .presentation_broker_resources import BrokerReaderResources
from .presentation_cancel_budget import CancellationBudget
from .presentation_control_binding import PreparedControlBinding
from .presentation_control_pipe import (
    _INPUT_WRITE_MINT,
    ControlCloseObservation,
    ControlInputWriteObservation,
    OwnedControlPipe,
)
from .presentation_credential_control import CredentialCancelAdoption, CredentialGoPhase
from .presentation_credential_ready import (
    CredentialReadyProducer,
    CredentialReadyWriter,
    _context_shape,
)
from .presentation_go import GoHandoff
from .presentation_jobs import INPUT_LIMIT, FrameError
from .presentation_remote_cleanup import _TASK

_RELAY_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_GO_RELAY_REFUSED")


def _input_shape(fact):
    """Historical field types only; never input-write or relay permission."""
    _require(type(fact) is ControlInputWriteObservation
             and type(fact.packet_sha256) is str and len(fact.packet_sha256) == 64
             and all(c in "0123456789abcdef" for c in fact.packet_sha256)
             and type(fact.packet_length) is int and 4 <= fact.packet_length <= INPUT_LIMIT + 4
             and type(fact.identity) is tuple and len(fact.identity) == 3
             and all(type(v) is int and v >= 0 for v in fact.identity)
             and type(fact.context) is tuple and len(fact.context) == 2
             and all(type(v) is int and v > 0 for v in fact.context)
             and type(fact.stream) is FileIO)


class _RelayScope(NamedTuple):
    control: object
    phase: object
    adoption: object
    refs: tuple
    receipt: object
    producer: object
    ready_writer: object
    ready_refs: tuple
    resources: object
    pipe: object
    process: object
    go: object
    input_fact: object
    wire: bytes

    def __repr__(self):
        return "<CredentialGoRelayScope original-service redacted>"


class _RelayFact(NamedTuple):
    mint: object
    owner: object
    scope: _RelayScope
    count: int
    close: object

    def __repr__(self):
        return "<CredentialGoRelayFact local-control-only>"


class _RelayWriteIntent(NamedTuple):
    mint: object
    owner: object
    scope: _RelayScope
    pipe: object
    fd: int
    data: bytes

    def __repr__(self):
        return "<CredentialGoWriteIntent original-native-call>"


class CredentialGoRelay:
    @classmethod
    def retain(cls, control):
        _require(cls is CredentialGoRelay and type(control) is BrokerCancellationOwner)
        adoption, phase = control._signed_cancel_snapshot, control._signed_go_snapshot
        _require(type(adoption) is CredentialCancelAdoption and type(phase) is CredentialGoPhase
                 and type(adoption._refs_snapshot) is tuple and len(adoption._refs_snapshot) == 19)
        refs = CredentialCancelAdoption._consume_scope(adoption, adoption._refs_snapshot[0])
        producer = control._credential_ready_snapshot
        _require(type(producer) is CredentialReadyProducer
                 and type(producer._refs_snapshot) is tuple and len(producer._refs_snapshot) == 9
                 and control._credential_go_relay is None
                 and control._credential_go_relay_snapshot is None
                 and control._go_relay_intent is False and control._go_relay_completed is False)
        r = producer._refs_snapshot
        _require(type(r[5]) is BrokerReaderResources and type(r[6]) is OwnedControlPipe
                 and type(r[8]) is BrokerChildOwner and type(r[6]._go) is GoHandoff
                 and r[6]._credential_go_relay is None
                 and r[6]._credential_go_relay_snapshot is None
                 and type(producer._writer_snapshot) is CredentialReadyWriter
                 and type(refs[5].challenge) is str and len(refs[5].challenge) == 64)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _RelayScope(
            control, phase, adoption, refs, phase._receipt, producer, producer._writer_snapshot,
            r, r[5], r[6], r[8], r[6]._go, r[7], refs[5].challenge.encode("ascii") + b"\n")
        owner._attempted = owner._failed = owner._complete = False
        owner._write_intent = owner._write_returned = owner._write_unknown = False
        owner._write_claim = owner._write_claim_snapshot = None
        owner._count = owner._count_snapshot = None
        owner._fact = owner._fact_snapshot = None
        control._credential_go_relay = control._credential_go_relay_snapshot = owner
        r[6]._credential_go_relay = r[6]._credential_go_relay_snapshot = owner
        try:
            CredentialGoRelay._current(owner)
            _require(owner._scope_snapshot.resources._go_attempted is False
                     and owner._scope_snapshot.go._attempted is False)
            return owner
        except BaseException:
            owner._failed = True
            raise

    def __repr__(self):
        return "<CredentialGoRelay local-write-only redacted>"

    def _local(self):
        _require(type(self) is CredentialGoRelay and type(self._scope) is _RelayScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.control) is BrokerCancellationOwner and type(s.phase) is CredentialGoPhase
                 and type(s.adoption) is CredentialCancelAdoption
                 and type(s.refs) is tuple and len(s.refs) == 19
                 and type(s.resources) is BrokerReaderResources and type(s.pipe) is OwnedControlPipe
                 and type(s.process) is BrokerChildOwner and type(s.go) is GoHandoff
                 and type(s.producer) is CredentialReadyProducer
                 and type(s.ready_writer) is CredentialReadyWriter
                 and type(s.ready_refs) is tuple and len(s.ready_refs) == 9
                 and s.control._credential_go_relay is self
                 and s.control._credential_go_relay_snapshot is self
                 and s.pipe._credential_go_relay is self
                 and s.pipe._credential_go_relay_snapshot is self
                 and s.adoption._refs_snapshot is s.refs
                 and s.control._signed_go_snapshot is s.phase
                 and s.phase._receipt is s.receipt and s.phase._notified is True
                 and s.phase._creator_refused is False
                 and s.control._credential_ready is s.producer
                 and s.control._credential_ready_snapshot is s.producer
                 and s.producer._refs is s.ready_refs and s.producer._refs_snapshot is s.ready_refs
                 and s.producer._failed is False and s.producer._writer is s.ready_writer
                 and s.producer._writer_snapshot is s.ready_writer
                 and s.ready_refs[0] is s.control and s.ready_refs[1] is s.adoption
                 and s.ready_refs[2] is s.phase
                 and s.ready_refs[3] is s.control._credential_binding_snapshot
                 and s.ready_refs[4] is s.refs
                 and s.ready_refs[5] is s.resources and s.ready_refs[6] is s.pipe
                 and s.ready_refs[7] is s.input_fact and s.ready_refs[8] is s.process)
        _input_shape(s.input_fact)  # before hash equality or descriptor indexing
        binding = s.control._credential_binding_snapshot
        _require(PreparedControlBinding._creator_local(binding) is s.refs)
        CredentialGoPhase._local(s.phase)
        _require(CredentialReadyWriter._local(s.ready_writer)[1] is s.ready_refs
                 and s.ready_writer._complete is True and s.ready_writer._active is False
                 and s.ready_writer._inflight is False
                 and s.ready_writer._intent_snapshot is not None
                 and s.ready_writer._offset == len(s.ready_writer._intent_snapshot.wire)
                 and s.ready_writer._grammar_attempted is True
                 and s.refs[4].state is _State.ACTIVE and s.refs[4].unknown is False
                 and s.refs[4].resources is s.resources
                 and s.refs[4].resources_snapshot is s.resources
                 and s.refs[4].owner is s.process and s.refs[4].owner_snapshot is s.process
                 and s.resources._operation is s.refs[4]
                 and s.resources._operation_snapshot is s.refs[4]
                 and s.resources._process is s.process
                 and s.resources._process_snapshot is s.process
                 and s.resources._control is s.pipe and s.resources._control_snapshot is s.pipe
                 and type(s.resources._phase) is str and s.resources._phase == "RUNNING"
                 and s.resources._invalidated is False
                 and s.resources._poisoned is False
                 and s.resources._cleanup_budget_snapshot is s.refs[17]
                 and s.resources._cleanup_budget is s.refs[17]
                 and s.pipe._go is s.go and s.go._poisoned is False
                 and type(s.input_fact) is ControlInputWriteObservation
                 and s.input_fact.mint is _INPUT_WRITE_MINT and s.input_fact.owner is s.pipe
                 and s.pipe._input_write_observation_origin is s.input_fact
                 and s.pipe._input_write_observation is s.input_fact
                 and s.input_fact.handle is s.refs[4] and s.input_fact.child is s.process
                 and type(s.input_fact.packet_sha256) is str
                 and type(s.refs[5].input_sha) is str
                 and s.input_fact.packet_sha256 == s.refs[5].input_sha
                 and type(s.input_fact.packet_length) is int
                 and type(s.refs[8]) is bytes and s.input_fact.packet_length == len(s.refs[8])
                 and type(s.input_fact.identity) is tuple and len(s.input_fact.identity) == 3
                 and all(type(v) is int for v in s.input_fact.identity)
                 and s.input_fact.identity is s.pipe._identity_snapshot
                 and s.pipe._identity is s.input_fact.identity
                 and type(s.input_fact.context) is tuple and len(s.input_fact.context) == 2
                 and all(type(v) is int for v in s.input_fact.context)
                 and s.input_fact.context == (os.getpid(), threading.get_ident())
                 and type(s.input_fact.stream) is FileIO
                 and s.input_fact.stream is s.pipe._stream_snapshot
                 and s.pipe._stream is s.input_fact.stream
                 and s.pipe._handle is s.refs[4] and s.pipe._handle_snapshot is s.refs[4]
                 and s.pipe._child is s.process and s.pipe._child_snapshot is s.process
                 and _context_shape(s.resources._input_context)
                 and _context_shape(s.producer._input_values_snapshot)
                 and s.resources._input_context is s.resources._input_snapshot
                 and s.resources._input_context == s.producer._input_values_snapshot
                 and s.pipe._input_ready is True and s.pipe._input_attempted is True
                 and type(s.wire) is bytes and len(s.wire) == 65
                 and type(s.pipe._challenge) is str
                 and s.wire == s.pipe._challenge.encode("ascii") + b"\n"
                 and all(type(v) is bool for v in (
                     self._attempted, self._failed, self._complete, self._write_intent,
                     self._write_returned, self._write_unknown))
                 and self._count is self._count_snapshot and self._fact is self._fact_snapshot
                 and self._write_claim is self._write_claim_snapshot
                 and type(s.refs[18]) is OperationGrammar
                 and OperationGrammar._configured(s.refs[18])
                 and s.refs[18]._ready is True and s.refs[18]._go is True
                 and s.refs[18]._cancel is False and s.refs[18]._invalidated is False
                 and type(s.refs[18]._client_next) is int and s.refs[18]._client_next == 2
                 and type(s.refs[18]._broker_next) is int and s.refs[18]._broker_next == 1)
        return s

    def _tail(self):
        s = CredentialGoRelay._local(self)
        keys, handshake = s.refs[10], s.refs[9]
        _require(keys._ready is True and keys._refused is False
                 and keys._private_key is s.refs[12] and keys._selection is s.refs[11]
                 and handshake._keys is keys and handshake._key_origin is s.refs[12]
                 and handshake._refused is False and handshake._io_unknown is False
                 and s.control._retired is False and s.control._failed is False
                 and s.control._io_unknown is False
                 and s.phase._creator_refused is False
                 and asyncio.current_task() is s.refs[15] and _TASK.cancelling(s.refs[15]) == 0
                 and self._failed is False)
        original, cause, end, failed = CancellationBudget.inspect(s.refs[17])
        _require(type(original) is int and original == s.refs[4].deadline_ns
                 and cause is None and end is None and failed is False)
        return s

    def _current(self):
        s = CredentialGoRelay._local(self)
        _require(s.phase.creator_current() is s.receipt)
        CredentialReadyWriter._settled(s.ready_writer)
        BrokerReaderResources._check(s.resources)
        _require(CredentialGoRelay._tail(self) is s)
        return s

    def _presend(self, pipe, fd, data):
        """Fixed final native-write fence, never a caller-selected callback."""
        s = CredentialGoRelay._tail(self)
        _require(pipe is s.pipe and type(fd) is int and fd == s.input_fact.identity[0]
                 and type(data) is bytes and data == s.wire
                 and self._attempted is True and self._complete is False
                 and self._write_intent is False and self._write_returned is False
                 and s.control._go_relay_intent is True and s.control._go_relay_completed is False
                 and s.resources._go_attempted is True and s.go._attempted is True
                 and pipe.closed is False and pipe.uncertain is False
                 and pipe._resource_uncertain is False and pipe._work_refused is False)
        _require(self._write_claim is None and self._write_claim_snapshot is None)
        claim = _RelayWriteIntent(_RELAY_MINT, self, s, pipe, fd, data)
        self._write_claim = self._write_claim_snapshot = claim
        self._write_intent = True  # before the sole native syscall
        return claim

    def _record_write(self, claim, count):
        """Credit the original native return before checking mutable owner aliases."""
        _require(type(self) is CredentialGoRelay and type(claim) is _RelayWriteIntent
                 and claim.mint is _RELAY_MINT and claim.owner is self
                 and type(claim.scope) is _RelayScope and type(claim.pipe) is OwnedControlPipe
                 and claim.scope.pipe is claim.pipe and type(claim.fd) is int
                 and type(claim.data) is bytes and len(claim.data) == 65)
        same = (self._write_returned is False and self._count is None
                and self._count_snapshot is None and self._write_intent is True
                and self._write_claim is claim and self._write_claim_snapshot is claim)
        self._write_returned = True
        if type(count) is not int or not 0 <= count <= len(claim.data):
            self._write_unknown = True
            raise FrameError("BI1_CREDENTIAL_GO_RELAY_WRITE_UNKNOWN")
        self._count = self._count_snapshot = count  # actual return survives later drift
        if (not same or self._scope is not claim.scope or self._scope_snapshot is not claim.scope
                or claim.pipe._credential_go_relay is not self
                or claim.pipe._credential_go_relay_snapshot is not self):
            self._write_unknown = True
            raise FrameError("BI1_CREDENTIAL_GO_RELAY_WRITE_STATE_UNKNOWN")

    def relay(self):
        s = CredentialGoRelay._local(self)
        _require(self._attempted is False and self._failed is False and self._complete is False
                 and s.control._go_relay_intent is False and s.control._go_relay_completed is False
                 and s.resources._go_attempted is False and s.go._attempted is False)
        self._attempted = s.control._go_relay_intent = True  # before native effects
        try:
            _require(CredentialGoRelay._current(self) is s)
            BrokerRegistry.relay_resource_go(s.refs[2], s.refs[3])
            _require(CredentialGoRelay._current(self) is s)
            closed = s.pipe.close_observation(s.refs[4], s.process)
            _require(CredentialGoRelay._tail(self) is s
                     and self._write_intent is True and self._write_returned is True
                     and self._write_unknown is False and type(self._count) is int
                     and self._count == len(s.wire)
                     and s.resources._go_attempted is True and s.go._attempted is True
                     and s.pipe.closed is True and s.pipe.uncertain is False
                     and type(closed) is ControlCloseObservation)
            self._fact = self._fact_snapshot = _RelayFact(_RELAY_MINT, self, s, self._count, closed)
            self._complete = s.control._go_relay_completed = True
            return self._fact  # local control delivery only, never execution/result ACK
        except BaseException:
            self._failed = True
            raise
