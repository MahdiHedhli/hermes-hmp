"""Original controller allocation/key binding; no phase or resource permit.

This source-only handoff cannot read bytes, mint GO/CANCEL receipts or authorize
resources. Prepared native Task allocation is not a runnable signed transport.
"""

from __future__ import annotations

import asyncio
import os
import threading

from .presentation_credential_queued import CredentialQueuedOwner
from .presentation_jobs import FrameError


def _require(value):
    if value is not True:
        raise FrameError("BI1_CONTROL_CREDENTIAL_BINDING_REFUSED")


class PreparedControlBinding:
    """One original creator and actual controller allocation, no IO permission."""

    def __init__(self, queued, control):
        from .presentation_broker_cancel import BrokerCancellationOwner

        _require(type(self) is PreparedControlBinding and "_initialized" not in vars(self))
        self._initialized = self._bound = False
        self._allocation = self._slot = None
        self._scope = self._scope_snapshot = None
        _require(type(queued) is CredentialQueuedOwner and type(control) is BrokerCancellationOwner)
        native = CredentialQueuedOwner.current_queued(queued)
        _require(
            type(queued._refs) is tuple
            and len(queued._refs) == 19
            and queued._refs is queued._refs_snapshot
        )
        self._refs = self._refs_snapshot = queued._refs_snapshot
        self._queued = self._queued_snapshot = queued
        self._control = self._control_snapshot = control
        self._creator = self._refs[15]
        self._loop = self._refs[16]
        self._native = native
        self._context = self._context_snapshot = queued._context_snapshot
        self._key_values = self._key_values_snapshot = queued._key_values_snapshot
        self._initialized = True
        PreparedControlBinding.creator_current(self)

    def __repr__(self):
        return "<PreparedControlBinding no-IO context-redacted>"

    def creator_current(self):
        from .presentation_broker_cancel import BrokerCancellationOwner

        _require(
            type(self) is PreparedControlBinding
            and self._initialized is True
            and type(self._queued) is CredentialQueuedOwner
            and self._queued is self._queued_snapshot
            and type(self._control) is BrokerCancellationOwner
            and self._control is self._control_snapshot
            and type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
            and type(self._creator) is asyncio.Task
            and asyncio.current_task() is self._creator
            and type(self._loop) is asyncio.SelectorEventLoop
            and asyncio.get_running_loop() is self._loop
            and self._queued._refs_snapshot is self._refs
        )
        original = self._refs_snapshot
        queued, control, creator, loop = (
            self._queued_snapshot,
            self._control_snapshot,
            self._creator,
            self._loop,
        )
        _require(CredentialQueuedOwner.current_queued(queued) is self._native)
        _require(
            self._refs is original
            and self._refs_snapshot is original
            and self._queued is queued
            and self._queued_snapshot is queued
            and self._control is control
            and self._control_snapshot is control
            and self._creator is creator
            and self._loop is loop
        )
        _require(queued._refs_snapshot is original)
        connection, registry, ticket, channel, grammar = (
            original[1],
            original[2],
            original[3],
            original[14],
            original[18],
        )
        _require(
            control._credential_binding is self
            and control._credential_binding_snapshot is self
            and connection.cancel_owner is control
            and channel._cancel_receiver is control
            and channel._cancel_receiver_snapshot is control
            and control._channel_snapshot is channel
            and control._registry_snapshot is registry
            and control._ticket_snapshot is ticket
            and control._grammar_snapshot is grammar
            and type(self._bound) is bool
        )
        if self._bound is True:
            PreparedControlBinding._allocation_current(self)

    def _allocation_current(self):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_remote_cleanup import _TASK, _TaskAllocation, _TaskSlot

        _require(
            type(self) is PreparedControlBinding
            and self._initialized is True
            and type(self._control) is BrokerCancellationOwner
            and self._control is self._control_snapshot
        )
        control = self._control_snapshot
        _require(
            control._credential_binding is self and control._credential_binding_snapshot is self
        )
        _require(
            type(self._scope) is tuple
            and len(self._scope) == 10
            and self._scope is self._scope_snapshot
            and control._scope is self._scope
            and control._scope_snapshot is self._scope
        )
        allocation, slot = self._allocation, self._slot
        _require(
            type(allocation) is _TaskAllocation
            and type(slot) is _TaskSlot
            and control._allocation is allocation
            and control._allocation_snapshot is allocation
            and control._slot is slot
            and control._slot_snapshot is slot
            and slot.initialized is True
            and slot.attempted is True
            and type(allocation.task) is _TASK
            and slot.task is allocation.task
            and slot.task_snapshot is allocation.task
            and slot.coroutine is allocation.coroutine
            and slot.coroutine_snapshot is allocation.coroutine
            and _TASK.get_coro(allocation.task) is allocation.coroutine
            and _TASK.get_loop(allocation.task) is self._loop
        )

    def bind_original_allocation(self):
        PreparedControlBinding.creator_current(self)
        _require(self._bound is False)
        control = self._control_snapshot
        self._allocation = control._allocation_snapshot
        self._slot = control._slot_snapshot
        scope = control._scope_snapshot
        _require(type(scope) is tuple and len(scope) == 10 and control._scope is scope)
        self._scope = self._scope_snapshot = scope
        PreparedControlBinding._allocation_current(self)
        PreparedControlBinding.creator_current(self)
        self._bound = True

    def _actor_local(self, *, reader):
        from .presentation_broker_registry import BrokerRegistry, _Record
        from .presentation_broker_service import BrokerServiceSpine, SocketChannel, _Connection
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_clock import NativeClockOwner
        from .presentation_credential_begin import CredentialBeginReceiver
        from .presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles, _HeldFile
        from .presentation_credential_handshake import CredentialHandshakeOwner
        from .presentation_credential_phase import ConsistentBeginInput
        from .presentation_remote_cleanup import _TASK
        from .presentation_terminal_claim import _InputReceipt

        _require(
            type(self) is PreparedControlBinding
            and self._initialized is True
            and self._bound is True
        )
        _require(type(reader) is bool)
        PreparedControlBinding._allocation_current(self)
        actor = self._allocation.task if reader else self._creator
        _require(
            type(actor) is _TASK
            and asyncio.current_task() is actor
            and _TASK.cancelling(actor) == 0
            and type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
            and type(self._queued) is CredentialQueuedOwner
            and self._queued is self._queued_snapshot
            and self._queued._refs_snapshot is self._refs
            and self._queued._initialized is True
            and self._queued._refused is False
        )
        refs = self._refs_snapshot
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
            creator,
            loop,
            budget,
            grammar,
        ) = refs
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
            and type(budget) is CancellationBudget
            and type(result) is ConsistentBeginInput
            and type(packet) is bytes
        )
        _require(
            type(self._context) is tuple
            and len(self._context) == 3
            and self._context is self._context_snapshot
            and all(type(v) is int for v in self._context)
            and self._context == (os.getpid(), os.geteuid(), threading.get_ident())
            and creator is self._creator
            and type(creator) is _TASK
            and loop is self._loop
            and type(loop) is asyncio.SelectorEventLoop
            and asyncio.get_running_loop() is loop
            and asyncio.BaseEventLoop.get_task_factory(loop) is None
        )
        control = self._control_snapshot
        _require(
            spine._registry is registry
            and spine._registry_snapshot is registry
            and spine._refused is False
            and spine._stopping is False
            and type(spine._records) is list
            and spine._records is spine._records_snapshot
            and sum(owned is connection for owned in spine._records_snapshot) == 1
            and connection.task is creator
            and connection.ticket is ticket
            and connection.credential_work is self._queued
            and connection.credential_work_snapshot is self._queued
            and connection.credential_adoption_complete is True
            and connection.credential_adoption_failed is False
            and connection.channel is channel
            and connection.channel_snapshot is channel
            and connection.cancel_owner is control
            and channel._cancel_receiver is control
            and channel._cancel_receiver_snapshot is control
            and channel._credential_handshake is handshake
            and channel._credential_handshake_snapshot is handshake
            and channel._credential_begin_receiver is receiver
            and channel._credential_begin_receiver_snapshot is receiver
            and receiver._handshake_snapshot is handshake
            and receiver._result is result
            and receiver._result_snapshot is result
            and result.packet is packet
            and receiver._complete is True
            and receiver._failed is False
            and handshake._task is creator
            and handshake._loop is loop
            and handshake._complete is True
            and handshake._refused is False
            and handshake._io_unknown is False
            and control._channel_snapshot is channel
            and control._registry_snapshot is registry
            and control._ticket_snapshot is ticket
            and control._grammar_snapshot is grammar
            and connection.grammar is grammar
            and connection.credential_grammar_snapshot is grammar
            and BrokerRegistry._record(registry, ticket) is native
            and self._native is native
            and native.input_receipt is receipt
            and native.input_receipt_snapshot is receipt
            and native.cleanup_budget is budget
            and native.cleanup_budget_snapshot is budget
            and control._scope_snapshot[0] is native
            and control._scope_snapshot[3] is budget
            and control._scope_snapshot[6] is clock
        )
        _require(
            type(self._key_values) is tuple
            and len(self._key_values) == 6
            and self._key_values is self._key_values_snapshot
            and all(type(v) is str for v in self._key_values[:3])
            and all(type(v) is bytes and len(v) == 32 for v in self._key_values[3:5])
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
            and handshake._key is key
            and handshake._key_origin is key
            and handshake._selection is selection
            and handshake._selection_origin is selection
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
        return refs

    def _reader_local(self):
        return PreparedControlBinding._actor_local(self, reader=True)

    def _creator_local(self):
        return PreparedControlBinding._actor_local(self, reader=False)

    def _material_current(self, *, reader):
        from .presentation_broker_registry import BrokerRegistry
        from .presentation_broker_service import BrokerServiceSpine, SocketChannel

        _require(type(reader) is bool)
        refs = PreparedControlBinding._actor_local(self, reader=reader)
        BrokerServiceSpine._current(refs[0])
        _require(PreparedControlBinding._actor_local(self, reader=reader) is refs)
        SocketChannel._check(refs[14])
        _require(PreparedControlBinding._actor_local(self, reader=reader) is refs)
        BrokerRegistry._check(refs[2])
        _require(PreparedControlBinding._actor_local(self, reader=reader) is refs)

    def reader_material_current(self):
        """Original reader's live role material only; no phase/time/IO permit."""
        PreparedControlBinding._material_current(self, reader=True)

    def creator_material_current(self):
        """Original service creator material; never borrows reader IO authority."""
        PreparedControlBinding._material_current(self, reader=False)

    def reader_closed(self):
        """Intentional hard stop until the actual signed cursor is implemented."""
        from .presentation_remote_cleanup import _TASK

        _require(type(self) is PreparedControlBinding and self._bound is True)
        PreparedControlBinding._allocation_current(self)
        _require(
            asyncio.current_task() is self._allocation.task
            and _TASK.cancelling(self._allocation.task) == 0
        )
        PreparedControlBinding.reader_material_current(self)
        # There is deliberately no boolean that enables old raw GO/CANCEL IO.
        raise FrameError("BI1_SIGNED_CONTROL_READER_NOT_IMPLEMENTED")
