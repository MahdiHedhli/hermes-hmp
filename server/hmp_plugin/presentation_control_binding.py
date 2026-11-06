"""Prepared original controller allocation/key binding; no signed reader yet.

This source-only handoff cannot read bytes, mint GO/CANCEL receipts or authorize
resources. Prepared native Task allocation is not a runnable signed transport.
"""

from __future__ import annotations

import asyncio

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
        PreparedControlBinding._allocation_current(self)
        PreparedControlBinding.creator_current(self)
        self._bound = True

    def reader_closed(self):
        """Intentional hard stop until the actual signed cursor is implemented."""
        from .presentation_remote_cleanup import _TASK

        _require(type(self) is PreparedControlBinding and self._bound is True)
        PreparedControlBinding._allocation_current(self)
        _require(
            asyncio.current_task() is self._allocation.task
            and _TASK.cancelling(self._allocation.task) == 0
        )
        # There is deliberately no boolean that enables old raw GO/CANCEL IO.
        raise FrameError("BI1_SIGNED_CONTROL_READER_NOT_IMPLEMENTED")
