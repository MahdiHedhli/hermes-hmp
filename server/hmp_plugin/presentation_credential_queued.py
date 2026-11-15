"""Original adopted broker connection's pre-resource current check; no GO grant.

No production factory/resource caller uses this owner yet. An opaque registry
ticket or historical adoption flag alone cannot admit credential work.
"""

from __future__ import annotations

import asyncio
import os
import threading

from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_registry import BrokerRegistry, _Record, _State
from .presentation_broker_service import BrokerServiceSpine, SocketChannel, _Connection
from .presentation_cancel_budget import CancellationBudget
from .presentation_clock import NativeClockOwner
from .presentation_credential_begin import CredentialBeginReceiver
from .presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles, _HeldFile
from .presentation_credential_handshake import CredentialHandshakeOwner
from .presentation_credential_phase import ConsistentBeginInput
from .presentation_jobs import FrameError
from .presentation_terminal_claim import _InputReceipt, input_current


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_QUEUED_REFUSED")


class CredentialQueuedOwner:
    """One adopted original task/scope; only the pre-resource queued phase."""

    def __init__(self, spine, connection):
        _require(type(self) is CredentialQueuedOwner and "_initialized" not in vars(self))
        self._initialized = self._refused = False
        self._refs = self._refs_snapshot = None
        _require(type(spine) is BrokerServiceSpine and type(connection) is _Connection)
        _require(
            connection.credential_work is self
            and connection.credential_work_snapshot is self
            and connection.credential_adoption_attempted is True
            and connection.credential_adoption_complete is False
            and connection.credential_adoption_failed is False
        )
        channel = connection.channel_snapshot
        _require(type(channel) is SocketChannel and connection.channel is channel)
        receiver = channel._credential_begin_receiver_snapshot
        _require(type(receiver) is CredentialBeginReceiver)
        result = CredentialBeginReceiver._completed_current(receiver)
        BrokerServiceSpine._current(spine)
        _require(CredentialBeginReceiver._completed_current(receiver) is result)
        registry = spine._registry_snapshot
        _require(type(registry) is BrokerRegistry and spine._registry is registry)
        native = BrokerRegistry._record(registry, connection.ticket)
        budget = native.cleanup_budget_snapshot
        _require(type(budget) is CancellationBudget and native.cleanup_budget is budget)
        candidate = native.input_receipt_snapshot
        _require(
            type(candidate) is _InputReceipt
            and native.input_receipt is candidate
            and type(candidate.challenge) is str
            and type(candidate.epoch) is int
            and type(candidate.input_sha) is str
            and type(candidate.worker_source_sha) is str
            and (
                candidate.expected_avatar_sha is None or type(candidate.expected_avatar_sha) is str
            )
        )
        receipt = input_current(native, result.packet)
        _require(connection.channel is channel and connection.channel_snapshot is channel)
        handshake = receiver._handshake_snapshot
        _require(type(handshake) is CredentialHandshakeOwner)
        grammar = connection.credential_grammar_snapshot
        _require(type(grammar) is OperationGrammar and connection.grammar is grammar)
        self._refs = self._refs_snapshot = (
            spine,
            connection,
            registry,
            connection.ticket,
            native,
            receipt,
            receiver,
            result,
            result.packet,
            handshake,
            handshake._keys,
            handshake._selection_origin,
            handshake._key_origin,
            handshake._clock_origin,
            connection.channel_snapshot,
            connection.task,
            asyncio.get_running_loop(),
            budget,
            grammar,
        )
        self._context = self._context_snapshot = (os.getpid(), os.geteuid(), threading.get_ident())
        selected = handshake._selection_origin
        self._key_values = self._key_values_snapshot = (
            selected.directory,
            selected.role,
            selected.generation,
            selected.own_public,
            selected.peer_public,
            handshake._boot,
        )
        self._end = self._end_snapshot = native.deadline_ns
        CredentialQueuedOwner._retained(self)
        BrokerServiceSpine._current(spine)
        _require(CredentialBeginReceiver._completed_current(receiver) is result)
        CredentialQueuedOwner._retained(self)
        _require(connection.credential_adoption_complete is False)
        self._initialized = True

    def __repr__(self):
        return "<CredentialQueuedOwner original-scope-redacted>"

    def _retained(self):
        _require(
            type(self) is CredentialQueuedOwner
            and self._refused is False
            and type(self._initialized) is bool
            and type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
        )
        (
            spine,
            connection,
            registry,
            ticket,
            native,
            receipt,
            receiver,
            result,
            packet,
            handshake,
            keys,
            selection,
            key,
            clock,
            channel,
            task,
            loop,
            budget,
            grammar,
        ) = self._refs
        _require(
            type(spine) is BrokerServiceSpine
            and type(connection) is _Connection
            and type(registry) is BrokerRegistry
            and type(native) is _Record
            and type(receipt) is _InputReceipt
            and type(receiver) is CredentialBeginReceiver
            and type(handshake) is CredentialHandshakeOwner
            and type(keys) is StartupRoleKeyFiles
            and type(selection) is RoleKeySelection
            and type(clock) is NativeClockOwner
            and type(channel) is SocketChannel
            and type(task) is asyncio.Task
            and type(loop) is asyncio.SelectorEventLoop
            and type(packet) is bytes
            and type(budget) is CancellationBudget
            and type(grammar) is OperationGrammar
            and type(result) is ConsistentBeginInput
        )
        _require(
            type(self._context) is tuple
            and len(self._context) == 3
            and self._context is self._context_snapshot
            and all(type(v) is int for v in self._context)
            and self._context == (os.getpid(), os.geteuid(), threading.get_ident())
            and asyncio.current_task() is task
            and asyncio.Task.cancelling(task) == 0
            and asyncio.get_running_loop() is loop
            and asyncio.BaseEventLoop.get_task_factory(loop) is None
        )
        BrokerServiceSpine._metadata(spine)
        _require(
            spine._registry is registry
            and spine._registry_snapshot is registry
            and spine._refused is False
            and spine._stopping is False
            and spine._integrity_lost is False
            and registry._poisoned is False
            and sum(owned is connection for owned in spine._records_snapshot) == 1
            and connection.credential_work is self
            and connection.credential_work_snapshot is self
            and connection.credential_adoption_attempted is True
            and connection.credential_adoption_failed is False
            and connection.ticket is ticket
            and connection.task is task
            and connection.channel is channel
            and connection.channel_snapshot is channel
            and connection.socket is channel._socket_snapshot
            and connection.local_closed is False
            and connection.clock_closed is False
            and channel._enrollment_snapshot is spine._enrollment_snapshot
            and channel._refused is False
            and channel._close_attempted is False
            and channel._reading is False
            and channel._writing is False
            and channel._terminal_owner is None
            and channel._work_write_retired is False
            and channel._credential_begin_receiver is receiver
            and channel._credential_begin_receiver_snapshot is receiver
            and receiver._handshake_snapshot is handshake
            and handshake._task is task
            and receiver._result is result
            and receiver._result_snapshot is result
            and result.packet is packet
        )
        _require(
            connection.grammar is grammar
            and connection.credential_grammar_snapshot is grammar
            and grammar._binding is receiver._binding_snapshot
            and OperationGrammar._configured(grammar) is True
            and type(grammar._version) is int
            and grammar._version == 2
            and type(grammar._role) is str
            and grammar._role == "broker"
            and type(grammar._mode) is str
            and grammar._mode == "operation"
            and grammar._begun is True
            and grammar._ready is False
            and grammar._go is False
            and grammar._cancel is False
            and grammar._invalidated is False
            and grammar._failed is False
            and grammar._result_seen is False
            and grammar._terminal_message is None
            and grammar._terminal_syntax is None
            and grammar._acked_message is False
            and type(grammar._client_next) is int
            and grammar._client_next == 1
            and type(grammar._broker_next) is int
            and grammar._broker_next == 0
        )
        CredentialBeginReceiver._metadata(receiver)
        CredentialBeginReceiver._released(receiver, channel)
        _require(
            type(self._key_values) is tuple
            and len(self._key_values) == 6
            and self._key_values is self._key_values_snapshot
            and all(type(v) is str for v in self._key_values[:3])
            and all(type(v) is bytes for v in self._key_values[3:5])
            and type(self._key_values[5]) is str
            and all(
                type(v) is str for v in (selection.directory, selection.role, selection.generation)
            )
            and type(selection.own_public) is bytes
            and type(selection.peer_public) is bytes
            and type(keys._boot) is str
            and (
                selection.directory,
                selection.role,
                selection.generation,
                selection.own_public,
                selection.peer_public,
                keys._boot,
            )
            == self._key_values
            and selection.role == "broker"
            and keys._ready is True
            and keys._refused is False
            and keys._private_key is key
            and keys._selection is selection
            and handshake._keys is keys
            and handshake._refused is False
            and handshake._io_unknown is False
            and handshake._complete is True
            and type(handshake._boot) is str
            and handshake._boot == self._key_values[5]
            and handshake._selection is selection
            and handshake._selection_origin is selection
            and handshake._key is key
            and handshake._key_origin is key
            and type(keys._process) is tuple
            and len(keys._process) == 2
            and all(type(v) is int for v in keys._process)
            and keys._process == self._context[:2]
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
            BrokerRegistry._record(registry, ticket) is native
            and native.input_receipt is receipt
            and native.input_receipt_snapshot is receipt
            and native.input_bind_attempted is True
            and native.cleanup_budget is budget
            and native.cleanup_budget_snapshot is budget
            and native.unknown is False
            and native.state is _State.QUEUED
            and native.managed is False
            and native.start_attempted is False
            and native.resources is None
            and native.resources_snapshot is None
            and native.resources_ready is False
            and type(self._end) is int
            and self._end is self._end_snapshot
            and type(native.deadline_ns) is int
            and native.deadline_ns == self._end
            and receiver._expected["work_end_ns"] == self._end
            and handshake._clock is clock
            and handshake._clock_origin is clock
        )

    def current_queued(self):
        """Check only original queued input under original work end; no effects."""
        _require(type(self) is CredentialQueuedOwner)
        _require(
            type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
        )
        original_refs = self._refs_snapshot
        failed = False
        try:
            CredentialQueuedOwner._retained(self)
            _require(self._refs is original_refs and self._refs_snapshot is original_refs)
            (
                spine,
                connection,
                registry,
                _,
                native,
                receipt,
                _,
                _,
                packet,
                _,
                _,
                _,
                _,
                clock,
                channel,
                _,
                _,
                _,
                _,
            ) = original_refs
            _require(self._initialized is True and connection.credential_adoption_complete is True)
            BrokerServiceSpine._current(spine)
            SocketChannel._check(channel)
            _require(SocketChannel._qualified_clock(channel) is clock)
            BrokerRegistry._check(registry)
            CredentialQueuedOwner._retained(self)
            _require(self._refs is original_refs and self._refs_snapshot is original_refs)
            _require(
                input_current(native, packet) is receipt and BrokerRegistry._work_budget(native)
            )
            now = NativeClockOwner.sample(clock)
            CredentialQueuedOwner._retained(self)
            _require(
                input_current(native, packet) is receipt and BrokerRegistry._work_budget(native)
            )
            CredentialQueuedOwner._retained(self)
            _require(
                self._refs is original_refs
                and self._refs_snapshot is original_refs
                and type(now) is int
                and now < self._end
                and connection.credential_adoption_complete is True
            )
            return native  # original queued record, not resource/GO permission
        except BaseException:
            failed = True
        if failed:
            self._refused = True
            raise FrameError("BI1_CREDENTIAL_QUEUED_REFUSED") from None
