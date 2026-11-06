"""Original work-task BEGIN signature producer; no transport or GO permission.

Only the retained native cleanup allocation may prepare its original reserved
BEGIN. Signed data is not a completed write or native publication receipt.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import threading

from .presentation_broker_codec import encode_frame
from .presentation_broker_service import SocketChannel, _BeginWriteIntent
from .presentation_clock import NativeClockOwner
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles, _HeldFile
from .presentation_credential_handshake import CredentialHandshakeOwner
from .presentation_credential_scope import derive_input_scope
from .presentation_credential_transcript import ConsistentTranscript, check_transcript
from .presentation_jobs import FrameError, RemotePhase


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_WORK_REFUSED")


class NativePhaseWorkOwner:
    """One original work allocation and one fixed signing attempt, no IO."""

    def __init__(self, cleanup):
        from .presentation_remote_cleanup import _FUTURE, RemoteCleanupOwner

        _require(type(self) is NativePhaseWorkOwner and "_ready" not in vars(self))
        self._ready = self._attempted = self._failed = False
        self._writer = self._writer_snapshot = None
        self._ready_transition = self._ready_transition_snapshot = None
        self._go_commitment = self._go_commitment_snapshot = None
        self._exchange_attempted = self._exchange_complete = self._exchange_failed = False
        self._record = self._record_snapshot = None
        self._intent = self._intent_snapshot = None
        self._cleanup = cleanup
        _require(type(cleanup) is RemoteCleanupOwner)
        RemoteCleanupOwner._guard(cleanup)
        remote = cleanup._remote_snapshot
        handshake = remote._credential_handshake_snapshot
        _require(type(handshake) is CredentialHandshakeOwner)
        CredentialHandshakeOwner._guard(handshake)
        RemoteCleanupOwner._guard(cleanup)
        _require(asyncio.current_task() is cleanup._caller_snapshot is handshake._task)
        _require(cleanup._credential_work is self and cleanup._credential_work_snapshot is self)
        _require(not _FUTURE.done(cleanup._start_snapshot))
        self._refs = (
            cleanup,
            remote,
            handshake,
            handshake._keys,
            handshake._key_origin,
            handshake._selection_origin,
            cleanup._allocations_snapshot[1],
            cleanup._slots_snapshot[1],
            handshake._clock_origin,
            handshake._native_input_snapshot,
            remote._channel_snapshot,
            handshake._transcript_snapshot,
        )
        self._refs_snapshot = self._refs
        self._context = self._context_snapshot = (os.getpid(), os.geteuid(), threading.get_ident())
        self._records = self._records_snapshot = tuple(handshake._records)
        self._common = self._common_snapshot = tuple(sorted(handshake._common.items()))
        self._selection_values = self._selection_values_snapshot = handshake._selection_values
        result = check_transcript(
            self._records,
            gateway_public=self._selection_values[3],
            broker_public=self._selection_values[4],
            expected_context=dict(self._common),
        )
        _require(type(handshake._transcript_snapshot) is ConsistentTranscript)
        self._transcript_values = (
            result.channel,
            result.transcript_sha256,
            result.gateway_boot,
            result.broker_boot,
        )
        self._transcript_values_snapshot = self._transcript_values
        # Crypto and clock boundaries cannot replace retained native allocations.
        CredentialHandshakeOwner._guard(handshake)
        RemoteCleanupOwner._guard(cleanup)
        _require(
            type(self._refs) is tuple
            and len(self._refs) == 12
            and self._refs is self._refs_snapshot
        )
        _require(
            cleanup._allocations_snapshot[1] is self._refs[6]
            and cleanup._slots_snapshot[1] is self._refs[7]
            and asyncio.current_task() is cleanup._caller_snapshot is handshake._task
            and not _FUTURE.done(cleanup._start_snapshot)
        )
        self._ready = True

    def __repr__(self):
        return "<NativePhaseWorkOwner payload-and-credentials-redacted>"

    def _material_local(self):
        from .presentation_remote import RemoteOperationOwner
        from .presentation_remote_cleanup import RemoteCleanupOwner

        _require(
            type(self) is NativePhaseWorkOwner
            and self._ready is True
            and self._failed is False
            and type(self._attempted) is bool
        )
        _require(
            type(self._refs) is tuple
            and len(self._refs) == 12
            and self._refs is self._refs_snapshot
        )
        (
            cleanup,
            remote,
            handshake,
            keys,
            key,
            selection,
            allocation,
            slot,
            clock,
            join,
            channel,
            transcript,
        ) = self._refs
        _require(
            type(cleanup) is RemoteCleanupOwner
            and cleanup is self._cleanup
            and cleanup._credential_work is self
            and cleanup._credential_work_snapshot is self
        )
        _require(
            type(handshake) is CredentialHandshakeOwner
            and type(remote) is RemoteOperationOwner
            and type(selection) is RoleKeySelection
        )
        RemoteCleanupOwner.authorize_work(cleanup)
        _require(
            self._context is self._context_snapshot
            and type(self._context) is tuple
            and len(self._context) == 3
            and all(type(v) is int for v in self._context)
            and self._context == (os.getpid(), os.geteuid(), threading.get_ident())
        )
        _require(
            cleanup._remote_snapshot is remote
            and cleanup._allocations_snapshot[1] is allocation
            and cleanup._slots_snapshot[1] is slot
            and asyncio.current_task() is allocation.task
            and cleanup._caller_snapshot is handshake._task
            and type(handshake._task) is asyncio.Task
            and asyncio.Task.cancelling(handshake._task) == 0
        )
        _require(
            type(handshake) is CredentialHandshakeOwner
            and remote._credential_handshake is handshake
            and remote._credential_handshake_snapshot is handshake
            and handshake._refused is False
            and handshake._io_unknown is False
            and handshake._complete is True
            and handshake._keys is keys
            and type(keys) is StartupRoleKeyFiles
            and keys._ready is True
            and keys._refused is False
            and keys._private_key is key
            and handshake._key is key
            and handshake._key_origin is key
            and keys._selection is selection
            and handshake._selection is selection
            and handshake._selection_origin is selection
        )
        _require(
            type(selection) is RoleKeySelection
            and self._selection_values is self._selection_values_snapshot
            and type(self._selection_values) is tuple
            and len(self._selection_values) == 5
            and all(type(v) is str for v in self._selection_values[:3])
            and all(type(v) is bytes for v in self._selection_values[3:])
        )
        _require(
            type(keys._process) is tuple
            and len(keys._process) == 2
            and all(type(v) is int for v in keys._process)
            and type(keys._records) is list
            and len(keys._records) <= 68
            and all(
                type(held) is _HeldFile
                and held.closed is True
                and held.close_attempted is True
                and held.unknown is False
                for held in keys._records
            )
        )
        _require(
            self._common is self._common_snapshot
            and type(self._common) is tuple
            and len(self._common) == 6
            and all(
                type(row) is tuple
                and len(row) == 2
                and type(row[0]) is str
                and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                for row in self._common
            )
            and self._records is self._records_snapshot
            and type(self._records) is tuple
            and len(self._records) == 4
            and all(type(v) is bytes and len(v) <= 2048 for v in self._records)
        )
        _require(
            type(transcript) is ConsistentTranscript
            and self._transcript_values is self._transcript_values_snapshot
            and type(self._transcript_values) is tuple
            and len(self._transcript_values) == 4
            and all(type(v) is str for v in self._transcript_values)
            and all(
                type(v) is str
                for v in (
                    transcript.channel,
                    transcript.transcript_sha256,
                    transcript.gateway_boot,
                    transcript.broker_boot,
                )
            )
            and (
                transcript.channel,
                transcript.transcript_sha256,
                transcript.gateway_boot,
                transcript.broker_boot,
            )
            == self._transcript_values
        )
        # Typed primitive values before comparison; no caller statement is admitted.
        _require(
            all(type(v) is str for v in (selection.directory, selection.role, selection.generation))
            and type(selection.own_public) is bytes
            and type(selection.peer_public) is bytes
        )
        _require(
            self._transcript_values is self._transcript_values_snapshot
            and type(self._transcript_values) is tuple
            and len(self._transcript_values) == 4
            and all(type(v) is str for v in self._transcript_values)
        )
        _require(
            (
                selection.directory,
                selection.role,
                selection.generation,
                selection.own_public,
                selection.peer_public,
            )
            == self._selection_values
            and selection.role == "gateway"
            and keys._process == self._context[:2]
            and type(keys._boot) is str
            and type(handshake._boot) is str
            and keys._boot is handshake._boot
            and keys._boot == self._transcript_values[2]
        )
        _require(
            type(handshake._common) is dict
            and all(
                type(k) is str and type(v) is (int if k == "work_end_ns" else str)
                for k, v in handshake._common.items()
            )
            and handshake._common is handshake._common_snapshot
            and tuple(sorted(handshake._common.items())) == self._common
            and type(handshake._records) is list
            and all(type(v) is bytes for v in handshake._records)
            and tuple(handshake._records) == self._records
            and handshake._transcript is transcript
            and handshake._transcript_snapshot is transcript
            and remote._binding_snapshot.channel == self._transcript_values[0]
        )
        _require(
            type(channel) is SocketChannel
            and channel is remote._channel_snapshot
            and handshake._clock is clock
            and handshake._clock_origin is clock
            and type(clock) is NativeClockOwner
            and remote._clock_owner_snapshot is clock
        )
        CredentialHandshakeOwner._released(handshake, channel)
        CredentialHandshakeOwner._native_input_local(handshake, remote, join)
        _require(self._record is self._record_snapshot and self._intent is self._intent_snapshot)
        return remote, handshake, channel, clock

    def _local(self):
        remote, handshake, channel, clock = NativePhaseWorkOwner._material_local(self)
        CredentialHandshakeOwner._native_join_fence(
            handshake, remote, phase=RemotePhase.BEGIN_INTENT)
        return remote, handshake, channel, clock

    def _ready_local(self):
        """Fixed post-transition material/current join; never a caller-selected phase."""
        from .presentation_credential_ready_transition import NativeReadyTransition

        remote, handshake, channel, clock = NativePhaseWorkOwner._material_local(self)
        transition = self._ready_transition_snapshot
        _require(type(transition) is NativeReadyTransition and self._ready_transition is transition)
        NativeReadyTransition._post_local(transition, self)
        CredentialHandshakeOwner._native_join_fence(handshake, remote, phase=RemotePhase.READY)
        NativeReadyTransition._post_local(transition, self)
        return remote, handshake, channel, clock

    def _guard(self):
        from .presentation_remote import RemoteOperationOwner

        remote, handshake, channel, clock = self._local()
        RemoteOperationOwner._check(remote, RemotePhase.BEGIN_INTENT)
        SocketChannel._check(channel)
        _require(SocketChannel._qualified_clock(channel) is clock)
        now = NativeClockOwner.sample(clock)
        remote, handshake, channel, _ = self._local()
        _require(
            type(now) is int and type(remote._end_snapshot) is int and now < remote._end_snapshot
        )
        intent = channel._begin_write_intent_snapshot
        writer = self._writer
        _require(writer is self._writer_snapshot)
        writing = False
        if writer is not None:
            from .presentation_credential_begin_write import NativeBeginWriter
            _require(type(writer) is NativeBeginWriter)
            writing = NativeBeginWriter._producer_active(writer, self)
        _require(
            type(intent) is _BeginWriteIntent
            and channel._begin_write_intent is intent
            and intent.remote is remote
            and intent.channel is channel
            and intent.socket is channel._socket_snapshot
            and intent.values is channel._values_snapshot
            and intent.identity is channel._identity_snapshot
            and channel._socket is channel._socket_snapshot is remote._seal_snapshot[9]
            and channel._values is channel._values_snapshot is remote._seal_snapshot[8]
            and channel._identity is channel._identity_snapshot is remote._seal_snapshot[10]
            and channel._work_write_retired is False
            and channel._refused is False
            and channel._close_attempted is False
            and channel._terminal_owner is None
            and intent.binding is remote._binding_snapshot
            and intent.packet is remote._packet_snapshot
            and type(intent.end_ns) is int
            and intent.end_ns == remote._end_snapshot
            and type(intent.version) is int
            and intent.version == 2
            and channel._begin_write_fact is None
            and channel._begin_write_fact_snapshot is None
            and channel._writing is writing
            and channel._reading is False
            and remote._send_claimed is True
            and remote._send_completed is False
            and remote._receive_claimed is False
        )
        _require(self._intent_snapshot is None or self._intent_snapshot is intent)
        return remote, handshake, intent

    def prepare_begin(self):
        """Sign only the original reserved BEGIN once; never send or retry."""
        _require(type(self) is NativePhaseWorkOwner)
        _require(self._attempted is False)
        self._attempted = True  # before native callbacks or cryptographic work
        try:
            remote, _handshake, intent = self._guard()
            self._intent = self._intent_snapshot = intent
            binding = remote._binding_snapshot
            frame = encode_frame(binding, "BEGIN", 0, remote._packet_snapshot, version=2)
            scope = derive_input_scope(remote._packet_snapshot, binding)
            transcript = self._refs[11]
            selection = self._refs[5]
            statement = dict(self._common)
            statement.pop("clock_domain")
            statement.update(
                v=1,
                family="phase",
                alg="Ed25519",
                phase="BEGIN",
                role="gateway",
                direction="g2b",
                key_id=hashlib.sha256(selection.own_public).hexdigest(),
                peer_key_id=hashlib.sha256(selection.peer_public).hexdigest(),
                gateway_boot=transcript.gateway_boot,
                broker_boot=transcript.broker_boot,
                channel=transcript.channel,
                transcript_sha256=transcript.transcript_sha256,
                sequence=0,
                input_sha256=scope.input_sha256,
                scope_sha256=scope.scope_sha256,
                frame_sha256=hashlib.sha256(frame).hexdigest(),
                frame_length=len(frame),
            )
            signing_data = signing_bytes(statement)
            self._guard()  # preparation may not retire authority before key use
            _require(self._attempted is True and self._record_snapshot is None)
            raw = encode_record(statement, self._refs[4].sign(signing_data))
            self._guard()  # no crypto callback can retire authority then publish a record
            _require(
                self._attempted is True
                and self._record_snapshot is None
                and type(raw) is bytes
                and len(raw) <= 2048
            )
            self._record = self._record_snapshot = raw
            return raw  # signed data only; no write-completion/GO permission
        except BaseException:
            self._failed = True
            raise


    async def exchange_ready(self):
        """Compose signed BEGIN/READY on original work only; no GO/startup authority."""
        from .presentation_credential_begin_write import NativeBeginWriter
        from .presentation_credential_ready_read import NativeReadyReceiver
        from .presentation_credential_ready_transition import NativeReadyTransition
        from .presentation_remote_cleanup import _TaskAllocation

        _require(type(self) is NativePhaseWorkOwner
                 and type(self._refs) is tuple and len(self._refs) == 12
                 and self._refs is self._refs_snapshot
                 and type(self._refs[6]) is _TaskAllocation
                 and asyncio.current_task() is self._refs[6].task)
        NativePhaseWorkOwner._local(self)  # original task, not a caller/cleanup borrower
        _require(self._exchange_attempted is False and self._exchange_failed is False
                 and self._exchange_complete is False)
        self._exchange_attempted = True  # before the first callback/native IO
        try:
            writer = NativeBeginWriter.retain(self)
            await NativeBeginWriter.write_begin(writer)
            receiver = NativeReadyReceiver.retain(writer)
            await NativeReadyReceiver.run(receiver)
            transition = NativeReadyTransition.retain(receiver)
            await NativeReadyTransition.run(transition)
            receipt = NativeReadyTransition.current_phase(transition)
            _require(self._exchange_attempted is True and self._exchange_failed is False
                     and self._exchange_complete is False)
            self._exchange_complete = True
            return receipt  # native READY only, never GO or resource admission
        except BaseException:
            self._exchange_failed = True
            raise


    async def exchange_go(self):
        """Fixed signed GO on actual native admission; original work task only."""
        from .presentation_credential_go import NativeGoCommitment
        from .presentation_credential_go_write import NativeGoWriter

        commitment = NativeGoCommitment.retain(self)
        NativeGoCommitment.prepare(commitment)
        writer = NativeGoWriter.retain(commitment)
        await NativeGoWriter.write_go(writer)
        NativeGoWriter.current_written(writer)
        return writer  # original full-write proof only; no native GO_SENT mutation
