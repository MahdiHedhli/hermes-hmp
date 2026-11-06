"""Fixed broker READY signing from actual original resource/input-write facts.

Source-only, no production caller. This owner starts no resources, writes no
socket bytes, observes no READY grammar and grants no GO/native publication.
"""

from __future__ import annotations

import hashlib
import os
import threading
from io import FileIO

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_codec import encode_frame
from .presentation_broker_resources import BrokerReaderResources
from .presentation_clock import NativeClockOwner
from .presentation_control_pipe import (
    _INPUT_WRITE_MINT,
    ControlInputWriteObservation,
    OwnedControlPipe,
)
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_control import CredentialCancelAdoption, CredentialGoPhase
from .presentation_credential_scope import InputScopeDigest, derive_input_scope
from .presentation_credential_transcript import ConsistentTranscript, check_transcript
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_READY_REFUSED")


def _context_shape(value):
    return (
        type(value) is tuple
        and len(value) == 5
        and type(value[0]) is str
        and type(value[1]) is int
        and type(value[2]) is str
        and type(value[3]) is tuple
        and all(
            type(v) is tuple and len(v) == 2 and type(v[0]) is str and type(v[1]) is int
            for v in value[3]
        )
        and (value[4] is None or type(value[4]) is str)
    )


class CredentialReadyProducer:
    """One original service actor and fixed READY signature attempt; no IO permit."""

    @classmethod
    def retain(cls, control):
        _require(cls is CredentialReadyProducer and type(control) is BrokerCancellationOwner)
        adoption = control._signed_cancel_snapshot
        _require(type(adoption) is CredentialCancelAdoption)
        _require(type(adoption._refs_snapshot) is tuple and len(adoption._refs_snapshot) == 19)
        scope = CredentialCancelAdoption._consume_scope(adoption, adoption._refs_snapshot[0])
        _require(control._credential_ready is None and control._credential_ready_snapshot is None)
        owner = cls.__new__(cls)
        control._credential_ready = control._credential_ready_snapshot = owner
        owner._ready = owner._attempted = owner._failed = False
        owner._record = owner._record_snapshot = None
        owner._refs = owner._refs_snapshot = None
        try:
            _require(CredentialCancelAdoption._creator_current(adoption, scope[0]) is scope)
            resources = scope[4].resources_snapshot
            _require(type(resources) is BrokerReaderResources)
            pipe = resources._control_snapshot
            _require(type(pipe) is OwnedControlPipe)
            fact = pipe._input_write_observation_origin
            _require(type(fact) is ControlInputWriteObservation)
            owner._refs = owner._refs_snapshot = (
                control,
                adoption,
                control._signed_go_snapshot,
                control._credential_binding_snapshot,
                scope,
                resources,
                pipe,
                fact,
                resources._process_snapshot,
            )
            owner._records = scope[6]._records_snapshot
            owner._common = scope[6]._common_snapshot
            row = decode_input_v3(scope[8])
            owner._input_values = owner._input_values_snapshot = (
                row["challenge"],
                row["epoch"],
                row["home"],
                tuple(sorted(row["parent_work_counts"].items())),
                row["expected_avatar_sha"],
            )
            owner._packet_sha = hashlib.sha256(scope[8]).hexdigest()
            CredentialReadyProducer._guard(owner)
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = True
            raise FrameError("BI1_CREDENTIAL_READY_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<CredentialReadyProducer no-write record-redacted>"

    def _local(self):
        from .presentation_broker_child import BrokerChildOwner
        from .presentation_broker_lifecycle import OperationGrammar
        from .presentation_broker_registry import _State
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_control_binding import PreparedControlBinding
        from .presentation_go import GoHandoff

        _require(
            type(self) is CredentialReadyProducer
            and self._failed is False
            and type(self._ready) is bool
            and type(self._attempted) is bool
            and type(self._refs) is tuple
            and len(self._refs) == 9
            and self._refs is self._refs_snapshot
        )
        control, adoption, phase, binding, scope, resources, pipe, fact, process = self._refs
        _require(
            type(control) is BrokerCancellationOwner
            and type(adoption) is CredentialCancelAdoption
            and type(phase) is CredentialGoPhase
            and type(binding) is PreparedControlBinding
            and type(scope) is tuple
            and len(scope) == 19
            and type(resources) is BrokerReaderResources
            and type(pipe) is OwnedControlPipe
            and type(fact) is ControlInputWriteObservation
            and type(process) is BrokerChildOwner
        )
        _require(
            control._credential_ready is self
            and control._credential_ready_snapshot is self
            and adoption._control_snapshot is control
            and adoption._refs_snapshot is scope
            and control._signed_go is phase
            and control._signed_go_snapshot is phase
            and control._credential_binding_snapshot is binding
            and binding._refs_snapshot is scope
        )
        PreparedControlBinding._creator_local(binding)
        CredentialCancelAdoption._local(adoption, creator=True)
        _require(
            type(self._records) is tuple
            and len(self._records) == 4
            and all(type(v) is bytes and len(v) <= 2048 for v in self._records)
            and scope[6]._records_snapshot is self._records
            and type(scope[9]._records) is list
            and all(type(v) is bytes for v in scope[9]._records)
            and tuple(scope[9]._records) == self._records
            and type(self._common) is tuple
            and len(self._common) == 6
            and all(
                type(v) is tuple
                and len(v) == 2
                and type(v[0]) is str
                and type(v[1]) is (int if v[0] == "work_end_ns" else str)
                for v in self._common
            )
            and scope[6]._common_snapshot is self._common
            and type(scope[9]._common) is dict
            and all(
                type(k) is str and type(v) is (int if k == "work_end_ns" else str)
                for k, v in scope[9]._common.items()
            )
            and tuple(sorted(scope[9]._common.items())) == self._common
        )
        native, packet, grammar = scope[4], scope[8], scope[18]
        _require(
            native.state is _State.ACTIVE
            and native.managed is True
            and native.start_attempted is True
            and native.resources_ready is True
            and native.unknown is False
            and native.resources is resources
            and native.resources_snapshot is resources
            and native.owner is process
            and native.owner_snapshot is process
            and resources._operation is native
            and resources._operation_snapshot is native
            and resources._process is process
            and resources._process_snapshot is process
            and resources._control is pipe
            and resources._control_snapshot is pipe
            and resources._cleanup_budget_snapshot is scope[17]
            and type(resources._phase) is str
            and resources._phase == "RUNNING"
            and resources._invalidated is False
            and resources._poisoned is False
            and resources._start_attempted is True
            and resources._input_attempted is True
            and resources._go_attempted is False
            and resources._wait is None
            and process._wait is None
            and process._launch_attempted is True
            and process._constructor_returned is True
            and process._signals_retired is False
            and process._uncertain is False
            and resources._input_context is resources._input_snapshot
        )
        context = resources._input_context
        _require(
            _context_shape(context)
            and _context_shape(self._input_values)
            and self._input_values is self._input_values_snapshot
            and context == self._input_values
        )
        _require(
            fact.mint is _INPUT_WRITE_MINT
            and fact.owner is pipe
            and type(fact.stream) is FileIO
            and fact.stream is pipe._stream_snapshot
            and pipe._stream is fact.stream
            and fact.handle is native
            and fact.child is process
            and pipe._handle_snapshot is native
            and pipe._handle is native
            and pipe._child_snapshot is process
            and pipe._child is process
            and type(fact.identity) is tuple
            and len(fact.identity) == 3
            and all(type(v) is int for v in fact.identity)
            and fact.identity is pipe._identity_snapshot
            and pipe._identity is fact.identity
            and type(fact.context) is tuple
            and len(fact.context) == 2
            and all(type(v) is int for v in fact.context)
            and fact.context == (os.getpid(), threading.get_ident())
            and type(fact.packet_sha256) is str
            and type(self._packet_sha) is str
            and fact.packet_sha256 == self._packet_sha
            and type(fact.packet_length) is int
            and fact.packet_length == len(packet)
            and pipe._input_write_observation is fact
            and pipe._input_write_observation_origin is fact
            and pipe._input_ready is True
            and pipe._input_attempted is True
            and pipe.uncertain is False
            and pipe.closed is False
            and pipe._resource_uncertain is False
            and pipe._work_refused is False
            and pipe._close_attempted is False
            and type(pipe._go) is GoHandoff
            and pipe._go._attempted is False
            and pipe._go._poisoned is False
        )
        _require(type(grammar) is OperationGrammar and OperationGrammar._configured(grammar))
        _require(
            control._retired is False
            and control._failed is False
            and control._go_receipt_snapshot is None
            and phase._attempted is False
            and grammar._ready is False
            and grammar._go is False
            and grammar._cancel is False
            and grammar._invalidated is False
            and grammar._client_next == 1
            and grammar._broker_next == 0
            and control._notice_attempted is False
            and CancellationBudget.inspect(scope[17])[2:] == (None, False)
        )
        return self._refs_snapshot

    def _guard(self):
        from .presentation_broker_child import BrokerChildOwner
        from .presentation_terminal_claim import input_current

        refs = CredentialReadyProducer._local(self)
        _control, adoption, _phase, _binding, scope, resources, pipe, _fact, process = refs
        _require(CredentialCancelAdoption._creator_current(adoption, scope[0]) is scope)
        _require(CredentialReadyProducer._local(self) is refs)
        BrokerReaderResources._check(resources)
        _require(CredentialReadyProducer._local(self) is refs)
        _require(BrokerChildOwner.poll_wait(process) is False)
        _require(CredentialReadyProducer._local(self) is refs)
        OwnedControlPipe._fd(pipe)
        _require(CredentialReadyProducer._local(self) is refs)
        _require(input_current(scope[4], scope[8]) is scope[5])
        _require(hashlib.sha256(scope[8]).hexdigest() == self._packet_sha)
        now = NativeClockOwner.sample(scope[13])
        _require(CredentialReadyProducer._local(self) is refs)
        _require(CredentialCancelAdoption._creator_current(adoption, scope[0]) is scope)
        _require(CredentialReadyProducer._local(self) is refs)
        _require(type(now) is int and 0 <= now < scope[4].deadline_ns)
        # Late clock/material callbacks must not leave a stale descriptor or
        # dead child behind a Python-only seal. End on concrete pipe validation.
        OwnedControlPipe._fd(pipe)
        _require(CredentialReadyProducer._local(self) is refs)
        _require(BrokerChildOwner.poll_wait(process) is False)
        _require(CredentialReadyProducer._local(self) is refs)
        OwnedControlPipe._fd(pipe)
        _require(CredentialReadyProducer._local(self) is refs)
        return refs

    def prepare_ready(self):
        """Sign fixed READY only once, from original current resource/write facts."""
        _require(
            type(self) is CredentialReadyProducer
            and self._ready is True
            and self._attempted is False
        )
        self._attempted = True
        try:
            refs = CredentialReadyProducer._guard(self)
            scope = refs[4]
            # Independently reverify the original four-record transcript and
            # derive the input digest; never sign a mutable BEGIN claim object.
            common = dict(self._common)
            transcript = check_transcript(
                self._records,
                gateway_public=scope[11].peer_public,
                broker_public=scope[11].own_public,
                expected_context=common,
            )
            digest = derive_input_scope(scope[8], scope[4].binding)
            _require(type(transcript) is ConsistentTranscript and type(digest) is InputScopeDigest)
            _require(
                all(
                    type(v) is str
                    for v in (
                        transcript.channel,
                        transcript.gateway_boot,
                        transcript.broker_boot,
                        transcript.transcript_sha256,
                        digest.input_sha256,
                        digest.scope_sha256,
                    )
                )
            )
            _require(
                transcript.channel == scope[4].binding.channel
                and common["work_end_ns"] == scope[4].deadline_ns
                and common["iid"] == scope[4].binding.iid
                and common["listener"] == scope[4].binding.listener
                and common["generation"] == scope[11].generation
                and transcript.broker_boot == scope[10]._boot
            )
            statement = dict(common)
            statement.pop("clock_domain")
            statement.update(
                gateway_boot=transcript.gateway_boot,
                broker_boot=transcript.broker_boot,
                channel=transcript.channel,
                transcript_sha256=transcript.transcript_sha256,
                input_sha256=digest.input_sha256,
                scope_sha256=digest.scope_sha256,
            )
            selection = scope[11]
            frame = encode_frame(scope[4].binding, "READY", 0, b"", version=2)
            statement.update(
                v=1,
                family="phase",
                alg="Ed25519",
                phase="READY",
                role="broker",
                direction="b2g",
                sequence=0,
                key_id=hashlib.sha256(selection.own_public).hexdigest(),
                peer_key_id=hashlib.sha256(selection.peer_public).hexdigest(),
                frame_sha256=hashlib.sha256(frame).hexdigest(),
                frame_length=len(frame),
            )
            data = signing_bytes(statement)
            _require(CredentialReadyProducer._guard(self) is refs)
            raw = encode_record(statement, scope[12].sign(data))
            _require(CredentialReadyProducer._guard(self) is refs)
            _require(
                self._record is None
                and self._record_snapshot is None
                and type(raw) is bytes
                and len(raw) <= 2048
            )
            self._record = self._record_snapshot = raw
            return raw
        except BaseException:
            self._failed = True
            raise FrameError("BI1_CREDENTIAL_READY_SIGNING_REFUSED") from None
