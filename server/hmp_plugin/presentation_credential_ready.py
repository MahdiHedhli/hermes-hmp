"""Fixed broker READY signing from actual original resource/input-write facts.

Source-only, no production caller. The producer signs only. Its retained writer
can send fixed READY and record grammar/completion; neither starts resources nor
grants worker GO, native publication or production admission.
"""

from __future__ import annotations

import asyncio
import errno
import hashlib
import os
import socket
import threading
from io import FileIO
from typing import NamedTuple

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
        owner._writer = owner._writer_snapshot = None
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
        writer = self._writer
        _require(writer is self._writer_snapshot)
        ready_intent = (False if writer is None else
                        CredentialReadyWriter._producer_phase(writer, self, grammar))
        _require(
            control._retired is False
            and control._failed is False
            and control._go_receipt_snapshot is None
            and phase._attempted is False
            and grammar._ready is ready_intent
            and grammar._go is False
            and grammar._cancel is False
            and grammar._invalidated is False
            and grammar._client_next == 1
            and grammar._broker_next == (1 if ready_intent else 0)
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


_SEND = socket.socket.send
_FILENO = socket.socket.fileno
_TIMEOUT = socket.socket.gettimeout
_FUTURE = asyncio.Future
_READY_WRITE_MINT = object()


class _ReadyWriteIntent(NamedTuple):
    mint: object
    owner: object
    producer: object
    grammar: object
    raw: bytes
    frame: bytes
    wire: bytes

    def __repr__(self):
        return "<ReadyWriteIntent fixed-READY redacted>"


class CredentialReadyWriter:
    """One fixed original-service READY write; no resource admission or GO relay."""

    @classmethod
    def retain(cls, producer):
        from .presentation_readiness import _scheduler_safe

        _require(cls is CredentialReadyWriter and type(producer) is CredentialReadyProducer)
        refs = CredentialReadyProducer._local(producer)
        _require(producer._ready is True and producer._attempted is True
                 and type(producer._record) is bytes
                 and producer._record is producer._record_snapshot
                 and producer._writer is None)
        scope, channel = refs[4], refs[4][14]
        _require(channel._credential_ready_writer is None
                 and channel._credential_ready_writer_snapshot is None
                 and channel._writing is False)
        owner = cls.__new__(cls)
        owner._refs = owner._refs_snapshot = (producer, refs, scope, channel,
                                              channel._socket_snapshot)
        owner._raw = producer._record
        owner._intent = owner._intent_snapshot = None
        owner._future = owner._future_origin = None
        owner._initialized = owner._future_initialized = False
        owner._attempted = owner._active = owner._inflight = False
        owner._failed = owner._unknown = owner._complete = False
        owner._grammar_attempted = False
        owner._offset = owner._offset_snapshot = 0
        owner._waiter = owner._waiter_origin = None
        producer._writer = producer._writer_snapshot = owner
        channel._credential_ready_writer = channel._credential_ready_writer_snapshot = owner
        try:
            owner._future = owner._future_origin = _FUTURE.__new__(_FUTURE)
            allocation = (owner._future_origin,)
            owner._refs = owner._refs_snapshot = (*owner._refs, allocation)
            CredentialReadyProducer._guard(producer)
            _scheduler_safe(scope[16])
            _FUTURE.__init__(owner._future_origin, loop=scope[16])
            owner._future_initialized = True
            _scheduler_safe(scope[16])
            owner._initialized = True
            CredentialReadyWriter._guard(owner)
            return owner
        except BaseException:
            owner._failed = owner._unknown = True
            raise FrameError("BI1_CREDENTIAL_READY_WRITER_ACQUISITION_REFUSED") from None

    def __repr__(self):
        return "<CredentialReadyWriter fixed-READY progress-redacted>"

    def _metadata(self):
        from .presentation_broker_cancel import _native_future_methods
        from .presentation_broker_service import SocketChannel

        _require(type(self) is CredentialReadyWriter and type(self._refs) is tuple
                 and len(self._refs) == 6 and self._refs is self._refs_snapshot)
        producer, refs, scope, channel, sock, allocation = self._refs
        _require(type(producer) is CredentialReadyProducer and type(refs) is tuple
                 and len(refs) == 9 and producer._refs_snapshot is refs
                 and type(scope) is tuple and len(scope) == 19 and refs[4] is scope
                 and type(channel) is SocketChannel and scope[14] is channel
                 and type(sock) is socket.socket and channel._socket is sock
                 and channel._socket_snapshot is sock
                 and producer._writer is self and producer._writer_snapshot is self
                 and channel._credential_ready_writer is self
                 and channel._credential_ready_writer_snapshot is self
                 and producer._record is self._raw and producer._record_snapshot is self._raw
                 and type(self._raw) is bytes and 0 < len(self._raw) <= 2048
                 and asyncio.get_running_loop() is scope[16]
                 and type(refs[7]) is ControlInputWriteObservation
                 and type(refs[7].context) is tuple and len(refs[7].context) == 2
                 and all(type(v) is int for v in refs[7].context)
                 and refs[7].context == (os.getpid(), threading.get_ident())
                 and channel._writing is self._active
                 and type(self._offset) is int and self._offset is self._offset_snapshot
                 and 0 <= self._offset <= 3096
                 and self._intent is self._intent_snapshot
                 and type(allocation) is tuple and len(allocation) == 1
                 and type(allocation[0]) is _FUTURE
                 and self._future is allocation[0] and self._future_origin is allocation[0]
                 and self._waiter is self._waiter_origin
                 and all(type(v) is bool for v in (
                     self._initialized, self._future_initialized, self._attempted,
                     self._active, self._inflight, self._failed, self._unknown,
                     self._complete, self._grammar_attempted)))
        if self._future_initialized:
            _require(type(self._future_origin) is _FUTURE
                     and _FUTURE.get_loop(self._future_origin) is scope[16])
            _native_future_methods(self._future_origin)
        intent = self._intent_snapshot
        if intent is not None:
            _require(type(intent) is _ReadyWriteIntent and intent.mint is _READY_WRITE_MINT
                     and intent.owner is self and intent.producer is producer
                     and intent.grammar is scope[18] and intent.raw is self._raw
                     and type(intent.frame) is bytes and type(intent.wire) is bytes
                     and intent.wire == intent.raw + intent.frame
                     and len(intent.wire) <= 3096 and self._offset <= len(intent.wire)
                     and intent.frame == encode_frame(scope[4].binding, "READY", 0,
                                                       b"", version=2))
        else:
            _require(self._offset == 0 and self._grammar_attempted is False)
        return self._refs_snapshot

    def _producer_phase(self, producer, grammar):
        _require(CredentialReadyWriter._metadata(self)[0] is producer
                 and self._refs_snapshot[2][18] is grammar and self._failed is False)
        if self._grammar_attempted:
            _require(type(self._intent_snapshot) is _ReadyWriteIntent
                     and self._offset == len(self._intent_snapshot.wire)
                     and self._inflight is False)
        return self._grammar_attempted

    def _local(self):
        refs = CredentialReadyWriter._metadata(self)
        _require(self._initialized is True and self._future_initialized is True
                 and self._failed is False and self._unknown is False
                 and asyncio.current_task() is refs[2][15]
                 and not _FUTURE.cancelled(self._future_origin)
                 and (_FUTURE.result(self._future_origin) is True if self._complete
                      else not _FUTURE.done(self._future_origin)))
        return refs

    def _guard(self):
        from .presentation_broker_service import SocketChannel

        refs = CredentialReadyWriter._local(self)
        producer, original, _scope, channel, sock, _allocation = refs
        _require(CredentialReadyProducer._guard(producer) is original)
        _require(CredentialReadyWriter._local(self) is refs)
        SocketChannel._check(channel)
        _require(CredentialReadyWriter._local(self) is refs)
        # Peer/clock callbacks must not leave a blocking or rebound native socket.
        fd = _FILENO(sock)
        row = os.fstat(fd)
        _require(type(fd) is int and fd == channel._fd_snapshot
                 and (fd, row.st_dev, row.st_ino, row.st_mode & 0o170000)
                     == channel._identity_snapshot
                 and os.get_blocking(fd) is False and _TIMEOUT(sock) == 0.0
                 and os.get_inheritable(fd) is False)
        _require(CredentialReadyWriter._local(self) is refs)
        return refs

    def _settled(self):
        from .presentation_readiness import SelectorReadiness, SelectorWriteReadiness

        CredentialReadyWriter._metadata(self)
        _require(self._inflight is False and self._unknown is False)
        waiter = self._waiter_origin
        if waiter is not None:
            _require(type(waiter) is SelectorWriteReadiness)
            SelectorReadiness._guard(waiter, actor=False)
            _require(waiter._retired is True and waiter._unknown is False)

    async def write_ready(self):
        from .presentation_broker_cancel import _native_future_methods
        from .presentation_broker_codec import BrokerFrame, decode_header, header_size
        from .presentation_broker_lifecycle import OperationGrammar
        from .presentation_credential_phase import check_commitment, check_complete_frame
        from .presentation_readiness import (
            SelectorReadiness,
            SelectorWriteReadiness,
            _scheduler_safe,
        )

        refs = CredentialReadyWriter._local(self)
        _require(self._attempted is False and self._active is False
                 and refs[3]._writing is False and self._intent is None)
        future = self._future_origin
        self._attempted = self._active = True
        refs[3]._writing = True
        try:
            _require(CredentialReadyWriter._guard(self) is refs)
            producer, _original, scope, _channel, sock, _allocation = refs
            common = dict(producer._common)
            transcript = check_transcript(producer._records,
                gateway_public=scope[11].peer_public, broker_public=scope[11].own_public,
                expected_context=common)
            digest = derive_input_scope(scope[8], scope[4].binding)
            expected = dict(common)
            expected.pop("clock_domain")
            expected.update(phase="READY", role="broker", direction="b2g", sequence=0,
                gateway_boot=transcript.gateway_boot, broker_boot=transcript.broker_boot,
                channel=transcript.channel, transcript_sha256=transcript.transcript_sha256,
                input_sha256=digest.input_sha256, scope_sha256=digest.scope_sha256)
            commitment = check_commitment(self._raw, sender_public=scope[11].own_public,
                receiver_public=scope[11].peer_public, expected=expected)
            frame = encode_frame(scope[4].binding, "READY", 0, b"", version=2)
            check_complete_frame(commitment, frame, binding=scope[4].binding)
            _require(CredentialReadyWriter._guard(self) is refs)
            self._intent = self._intent_snapshot = _ReadyWriteIntent(
                _READY_WRITE_MINT, self, producer, scope[18], self._raw, frame, self._raw + frame)
            intent = self._intent_snapshot
            while self._offset < len(intent.wire):
                _require(CredentialReadyWriter._guard(self) is refs)
                _require(self._intent_snapshot is intent and self._inflight is False)
                before = self._offset
                remaining = intent.wire[before:]
                self._inflight = True
                try:
                    count = _SEND(sock, remaining)
                except BlockingIOError as error:
                    # Only the exact native would-block result proves zero bytes.
                    _require(type(error) is BlockingIOError
                             and type(error.errno) is int
                             and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                             and self._offset is before and self._offset_snapshot is before
                             and self._intent is intent and self._intent_snapshot is intent
                             and self._inflight is True)
                    self._inflight = False
                    waiter = SelectorWriteReadiness.__new__(SelectorWriteReadiness)
                    self._waiter = self._waiter_origin = waiter
                    SelectorWriteReadiness.__init__(waiter, sock)
                    await SelectorReadiness.wait(waiter, scope[4].deadline_ns)
                    CredentialReadyWriter._settled(self)
                    _require(CredentialReadyWriter._guard(self) is refs)
                    continue
                _require(type(count) is int and 0 <= count <= len(remaining))
                # Capture actual progress before any current-material callback.
                same = (self._offset is before and self._offset_snapshot is before
                        and self._intent is intent and self._intent_snapshot is intent
                        and self._inflight is True)
                self._offset = self._offset_snapshot = before + count
                self._inflight = False
                if not same:
                    self._unknown = True
                    raise FrameError("BI1_CREDENTIAL_READY_WRITE_STATE_UNKNOWN")
                _require(count > 0)  # known zero is terminal refusal, never a retry
                _require(CredentialReadyWriter._guard(self) is refs)
            _require(CredentialReadyWriter._guard(self) is refs)
            self._grammar_attempted = True
            end = 8 + header_size(frame[:8])
            header = decode_header(frame[:end], expected=scope[4].binding, expected_version=2)
            OperationGrammar.observe(scope[18], BrokerFrame(header, b""), sender="broker")
            _require(CredentialReadyWriter._guard(self) is refs)
            _scheduler_safe(scope[16])
            _require(CredentialReadyWriter._guard(self) is refs)
            self._complete = True
            _FUTURE.set_result(future, True)
            return None
        except BaseException:
            self._failed = True
            raise
        finally:
            try:
                CredentialReadyWriter._settled(self)
                self._active = False
                refs[3]._writing = False
            except BaseException:
                self._unknown = True  # retain native write/registration debt
            if not _FUTURE.done(future):
                try:
                    _scheduler_safe(refs[2][16])
                    _native_future_methods(future)
                    _FUTURE.set_result(future, False)
                except BaseException:
                    self._unknown = True

    async def join_control(self, control):
        """Original controller joins this exact write, never an arbitrary Future."""
        from .presentation_control_binding import PreparedControlBinding

        refs = CredentialReadyWriter._metadata(self)
        _require(refs[1][0] is control and self._initialized is True
                 and self._future_initialized is True)
        binding = refs[1][3]
        PreparedControlBinding._reader_local(binding)
        future = self._future_origin
        async with asyncio.timeout_at(refs[2][4].deadline_ns / 1_000_000_000):
            await asyncio.wait((future,), return_when=asyncio.FIRST_COMPLETED)
        _require(CredentialReadyWriter._metadata(self) is refs)
        PreparedControlBinding.reader_material_current(binding)
        _require(CredentialReadyWriter._metadata(self) is refs
                 and self._future_origin is future and _FUTURE.result(future) is True
                 and self._complete is True and self._failed is False
                 and self._active is False and self._unknown is False
                 and self._inflight is False and type(self._intent_snapshot) is _ReadyWriteIntent
                 and self._offset == len(self._intent_snapshot.wire)
                 and self._grammar_attempted is True)

    def _released(self, channel):
        """Known local IO retirement only; no role/key or protocol success claim."""
        refs = CredentialReadyWriter._metadata(self)
        _require(refs[3] is channel and self._active is False and channel._writing is False)
        CredentialReadyWriter._settled(self)
