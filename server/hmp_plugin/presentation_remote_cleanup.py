"""Retained selected-v2 work/cleanup and one CANCEL; no native or remote release.

Default native selector/task runtime only. Local close observations never prove
broker/child/native closure or a production synchronous-syscall deadline.
"""
from __future__ import annotations

import asyncio
import os
import threading
from contextlib import suppress
from dataclasses import dataclass
from types import CoroutineType
from typing import NamedTuple

from .presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    ParentAuthorityAdapter,
    _Record,
)
from .presentation_broker_codec import BrokerBinding, _binding, encode_frame
from .presentation_broker_service import (
    _BEGIN_WRITE_MINT,
    _SOCKET_TIMEOUT,
    SocketChannel,
    _BeginWriteFact,
    _BeginWriteIntent,
    _task_allows_work,
)
from .presentation_cancel_budget import CLEANUP_NS, CancellationBudget, CancellationWindow
from .presentation_clock import NativeClockOwner

_TASK = asyncio.Task
_FUTURE = asyncio.Future
_LOOP = asyncio.SelectorEventLoop


class _TaskAllocation(NamedTuple):
    task: object
    coroutine: object


class _BarrierAllocation(NamedTuple):
    start: object
    cause: object


@dataclass(eq=False, repr=False)
class _TaskSlot:
    task: object = None
    task_snapshot: object = None
    coroutine: object = None
    coroutine_snapshot: object = None
    attempted: bool = False
    initialized: bool = False


def _initialize_future(future, loop):
    _FUTURE.__init__(future, loop=loop)


def _initialize_task(slot, loop):
    """Allocation and coroutine are already retained before this native boundary."""
    slot.attempted = True
    _TASK.__init__(slot.task, slot.coroutine, loop=loop)
    slot.initialized = True


class RemoteCleanupOwner:
    """Exactly one retained work task and cleanup task per selected-v2 owner."""

    def __init__(self, remote):
        from .presentation_remote import RemoteOperationOwner

        self._remote = self._remote_snapshot = remote
        self._initialized = self._run_attempted = self._intent = False
        self._unknown = self._work_joined = self._socket_closed = self._clock_closed = False
        self._cancel_attempted = self._sampling = False
        self._cancel_write_attempted = self._cancel_write_completed = False
        self._cancel_scope = self._cancel_scope_snapshot = None
        self._cancel_wire = self._cancel_wire_snapshot = None
        self._cancel_end = self._cancel_end_snapshot = None
        self._cancel_timeout = self._cancel_timeout_snapshot = None
        self._loop = self._loop_snapshot = None
        self._context = self._context_snapshot = None
        self._caller = self._caller_snapshot = None
        self._refs = self._refs_snapshot = None
        self._start = self._cause = self._start_snapshot = self._cause_snapshot = None
        self._start_initialized = self._cause_initialized = False
        self._slots = self._slots_snapshot = (_TaskSlot(), _TaskSlot())
        self._allocations = self._allocations_snapshot = (None, None)
        self._barriers = self._barriers_snapshot = _BarrierAllocation(None, None)
        try:
            if type(remote) is not RemoteOperationOwner or remote._protocol != 2:
                raise AuthorityRefusalError
            self._loop = self._loop_snapshot = asyncio.get_running_loop()
            self._context = self._context_snapshot = (
                os.getpid(), os.geteuid(), threading.get_ident())
            self._caller = self._caller_snapshot = asyncio.current_task()
            if (type(self._loop) is not _LOOP or type(self._caller) is not _TASK
                    or asyncio.BaseEventLoop.get_task_factory(self._loop) is not None):
                raise AuthorityRefusalError
            RemoteOperationOwner._retained_local(remote)
            RemoteOperationOwner._clock_binding(remote)
            if remote._cleanup_owner is not self or remote._cleanup_owner_snapshot is not self:
                raise AuthorityRefusalError
            self._refs = self._refs_snapshot = RemoteCleanupOwner._references(self)
            self._cancel_scope = self._cancel_scope_snapshot = (
                remote._binding_snapshot, remote._values_snapshot)
            self._start = self._start_snapshot = _FUTURE.__new__(_FUTURE)
            self._barriers = self._barriers_snapshot = _BarrierAllocation(self._start, None)
            _initialize_future(self._start, self._loop)
            self._start_initialized = True
            self._cause = self._cause_snapshot = _FUTURE.__new__(_FUTURE)
            self._barriers = self._barriers_snapshot = _BarrierAllocation(self._start, self._cause)
            _initialize_future(self._cause, self._loop)
            self._cause_initialized = True
            # Cleanup is retained first. Both fixed coroutines remain gated until
            # all initialization and reciprocal ownership checks have succeeded.
            functions = (RemoteCleanupOwner._cleanup, RemoteCleanupOwner._work)
            for index, function in enumerate(functions):
                slot = self._slots[index]
                slot.coroutine = slot.coroutine_snapshot = function(self)
                slot.task = slot.task_snapshot = _TASK.__new__(_TASK)
                allocation = _TaskAllocation(slot.task, slot.coroutine)
                allocations = list(self._allocations_snapshot)
                allocations[index] = allocation
                self._allocations = self._allocations_snapshot = tuple(allocations)
                _initialize_task(slot, self._loop)
            self._initialized = True
            RemoteCleanupOwner._guard(self)
        except BaseException:
            self._unknown = True
            # Never infer that failed initialization scheduled nothing. Closed
            # barriers prevent work even if an ambiguous task eventually runs.
            if self._start_initialized and not _FUTURE.done(self._start_snapshot):
                _FUTURE.set_result(self._start_snapshot, False)
            if self._cause_initialized and not _FUTURE.done(self._cause_snapshot):
                _FUTURE.set_result(self._cause_snapshot, None)
            if type(remote) is RemoteOperationOwner:
                budget = remote._cleanup_budget_snapshot
                if type(budget) is CancellationBudget:
                    CancellationBudget.refuse(budget)
                RemoteOperationOwner._poison(remote)
            raise AuthorityRefusalError from None

    def __repr__(self):
        return "<RemoteCleanupOwner redacted>"

    def _references(self):
        r = self._remote_snapshot
        record = r._record_snapshot
        return (r._authority_snapshot, r._operation_snapshot, record, r._channel_snapshot,
                r._clock_owner_snapshot, r._clock_domain_snapshot,
                r._clock_domain_values_snapshot, r._clock_qualification_snapshot,
                r._cleanup_budget_snapshot, r._end_snapshot, r._seal_snapshot,
                record._custody_snapshot)

    def _guard(self):
        from .presentation_remote import RemoteOperationOwner

        r = self._remote
        if (self._initialized is not True or type(r) is not RemoteOperationOwner
                or r is not self._remote_snapshot
                or type(self._refs) is not tuple or len(self._refs) != 12
                or self._refs is not self._refs_snapshot
                or self._slots is not self._slots_snapshot
                or type(self._slots) is not tuple or len(self._slots) != 2
                or any(type(slot) is not _TaskSlot for slot in self._slots)
                or self._allocations is not self._allocations_snapshot
                or type(self._allocations) is not tuple or len(self._allocations) != 2
                or any(type(a) is not _TaskAllocation for a in self._allocations)
                or self._barriers is not self._barriers_snapshot
                or type(self._barriers) is not _BarrierAllocation
                or self._start is not self._barriers.start
                or self._cause is not self._barriers.cause
                or self._caller is not self._caller_snapshot or type(self._caller) is not _TASK
                or type(self._loop) is not _LOOP or self._loop is not self._loop_snapshot
                or asyncio.get_running_loop() is not self._loop
                or self._context is not self._context_snapshot
                or type(self._context) is not tuple or len(self._context) != 3
                or any(type(v) is not int for v in self._context)
                or self._context != (os.getpid(), os.geteuid(), threading.get_ident())
                or any(type(v) is not bool for v in (
                    self._run_attempted, self._intent, self._unknown, self._work_joined,
                    self._socket_closed, self._clock_closed, self._cancel_attempted,
                    self._sampling, self._cancel_write_attempted, self._cancel_write_completed))
                or asyncio.BaseEventLoop.get_task_factory(self._loop) is not None
                or r._cleanup_owner is not self or r._cleanup_owner_snapshot is not self
                or type(r._record) is not _Record or r._record is not self._refs[2]
                or r._record_snapshot is not self._refs[2]
                or r._channel is not self._refs[3]
                or r._clock_owner is not self._refs[4]
                or r._clock_domain is not self._refs[5]
                or r._clock_domain_values is not self._refs[6]
                or r._clock_qualification is not self._refs[7]
                or r._cleanup_budget is not self._refs[8]
                or r._end is not self._refs[9]
                or r._seal is not self._refs[10]
                or type(self._start) is not _FUTURE or self._start is not self._start_snapshot
                or type(self._cause) is not _FUTURE or self._cause is not self._cause_snapshot
                or self._start_initialized is not True or self._cause_initialized is not True
                or _FUTURE.cancelled(self._start) or _FUTURE.cancelled(self._cause)):
            raise AuthorityRefusalError
        if not all(x is y for x, y in zip(
                RemoteCleanupOwner._references(self), self._refs, strict=True)):
            raise AuthorityRefusalError
        for slot, allocation in zip(self._slots, self._allocations, strict=True):
            if (type(slot.task) is not _TASK or slot.task is not slot.task_snapshot
                    or slot.task is not allocation.task
                    or slot.coroutine is not allocation.coroutine
                    or type(slot.coroutine) is not CoroutineType
                    or slot.coroutine is not slot.coroutine_snapshot
                    or slot.attempted is not True or slot.initialized is not True
                    or _TASK.get_coro(slot.task) is not slot.coroutine):
                raise AuthorityRefusalError
        scope = self._cancel_scope
        if (type(scope) is not tuple or len(scope) != 2 or scope is not self._cancel_scope_snapshot
                or type(scope[0]) is not BrokerBinding or type(scope[1]) is not tuple
                or len(scope[1]) != 5 or any(type(v) is not str for v in scope[1])
                or r._binding is not scope[0] or r._binding_snapshot is not scope[0]
                or r._values is not scope[1] or r._values_snapshot is not scope[1]
                or self._cancel_wire is not self._cancel_wire_snapshot
                or (self._cancel_wire is not None and type(self._cancel_wire) is not bytes)
                or self._cancel_end is not self._cancel_end_snapshot
                or (self._cancel_end is not None and type(self._cancel_end) is not int)
                or self._cancel_timeout is not self._cancel_timeout_snapshot
                or (self._cancel_timeout is not None
                    and type(self._cancel_timeout) is not asyncio.Timeout)):
            raise AuthorityRefusalError
        _binding(scope[0])
        b = scope[0]
        if (b.iid, b.listener, b.broker, b.channel, b.operation) != scope[1]:
            raise AuthorityRefusalError
        original, _, _, failed = CancellationBudget.inspect(self._refs[8])
        if original != self._refs[9] or failed:
            raise AuthorityRefusalError

    def request(self):
        """Latch/revoke before clock boundaries; freeze before owned cancellation."""
        from .presentation_remote import RemoteOperationOwner

        if self._initialized is not True:
            self._unknown = True
            return
        if (self._intent is True and self._work_joined is True
                and self._socket_closed is True and self._clock_closed is True):
            return  # completed local facts do not sample a retired clock again
        first = self._intent is False
        self._intent = True
        # Original custody only: failed work or drift cannot choose the fence.
        refs = self._refs_snapshot
        if type(refs) is not tuple or len(refs) != 12:
            self._unknown = True
            return
        custody = refs[11]
        if (type(custody) is tuple and len(custody) == 3
                and type(custody[2]) is ListenerFence):
            ListenerFence.retire(custody[2])
        if type(self._remote_snapshot) is not RemoteOperationOwner:
            self._unknown = True
            return
        RemoteOperationOwner._poison(self._remote_snapshot)
        try:
            RemoteCleanupOwner._guard(self)
            if self._clock_closed or self._sampling:
                raise AuthorityRefusalError
            self._sampling = True
            RemoteOperationOwner._clock_binding(self._remote_snapshot)
            now = NativeClockOwner.cleanup_sample(self._refs[4])
            RemoteCleanupOwner._guard(self)
            RemoteOperationOwner._clock_binding(self._remote_snapshot)
            CancellationBudget.local(self._refs[8], now)
        except BaseException:
            self._unknown = True
            if type(refs[8]) is CancellationBudget:
                CancellationBudget.refuse(refs[8])
        finally:
            self._sampling = False
        if first:
            allocations = self._allocations_snapshot
            if (type(allocations) is tuple and len(allocations) == 2
                    and type(allocations[1]) is _TaskAllocation):
                work = allocations[1].task
                if (type(work) is _TASK and asyncio.current_task() is not work
                        and not _TASK.done(work)):
                    self._cancel_attempted = True  # intent before native Task.cancel
                    _TASK.cancel(work)
        barriers = self._barriers_snapshot
        if (self._cause_initialized and type(barriers) is _BarrierAllocation
                and type(barriers.cause) is _FUTURE and not _FUTURE.done(barriers.cause)):
            _FUTURE.set_result(barriers.cause, None)

    def _remaining(self):
        from .presentation_remote import RemoteOperationOwner

        RemoteCleanupOwner._guard(self)
        if self._sampling or self._clock_closed:
            raise AuthorityRefusalError
        self._sampling = True
        try:
            RemoteOperationOwner._clock_binding(self._remote_snapshot)
            now = NativeClockOwner.cleanup_sample(self._refs[4])
            RemoteCleanupOwner._guard(self)
            RemoteOperationOwner._clock_binding(self._remote_snapshot)
            return CancellationBudget.remaining_ns(self._refs[8], now) / 1_000_000_000
        finally:
            self._sampling = False

    def _can_cancel(self):
        RemoteCleanupOwner._guard(self)
        c, r = self._refs[3], self._remote_snapshot
        fact = c._begin_write_fact_snapshot
        if fact is None:
            if r._send_completed is True:
                self._unknown = True  # a mutable completion flag is not native write evidence
            return False
        if (type(fact) is not _BeginWriteFact or c._begin_write_fact is not fact
                or fact.mint is not _BEGIN_WRITE_MINT
                or type(fact.intent) is not _BeginWriteIntent
                or fact.intent is not c._begin_write_intent_snapshot
                or c._begin_write_intent is not fact.intent):
            raise AuthorityRefusalError
        intent = fact.intent
        if (intent.remote is not r or intent.channel is not c
                or intent.socket is not c._socket_snapshot
                or intent.values is not c._values_snapshot
                or intent.identity is not c._identity_snapshot
                or intent.binding is not self._cancel_scope[0]
                or intent.packet is not r._packet_snapshot
                or type(intent.end_ns) is not int or intent.end_ns != self._refs[9]
                or type(intent.version) is not int or intent.version != 2
                or type(intent.token) is not object):
            raise AuthorityRefusalError
        return r._send_completed is True

    def _cancel_actor(self, channel):
        RemoteCleanupOwner._guard(self)
        if (channel is not self._refs[3] or type(channel) is not SocketChannel
                or channel._role != "gateway" or channel._remote_owner is not self._remote_snapshot
                or channel._remote_owner_snapshot is not self._remote_snapshot
                or channel._terminal_owner is not None or channel._cancel_receiver is not None
                or self._intent is not True or self._unknown is not False
                or self._work_joined is not True
                or asyncio.current_task() is not self._allocations_snapshot[0].task
                or _TASK.cancelling(self._allocations_snapshot[0].task)
                or not _TASK.done(self._allocations_snapshot[1].task)
                or channel._reading is not False
                or not RemoteCleanupOwner._can_cancel(self)):
            raise AuthorityRefusalError
        SocketChannel._local_integrity(channel)
        timeout = _SOCKET_TIMEOUT(channel._socket)
        if (os.get_blocking(channel._fd) is not False
                or type(timeout) is not float or timeout != 0.0):
            raise AuthorityRefusalError

    def _prepare_cancel(self, channel):
        RemoteCleanupOwner._cancel_actor(self, channel)
        if (self._cancel_write_attempted is not False or self._cancel_wire is not None
                or channel._writing is not False):
            raise AuthorityRefusalError
        if RemoteCleanupOwner._remaining(self) <= 0:
            raise AuthorityRefusalError
        RemoteCleanupOwner._cancel_actor(self, channel)
        if (self._cancel_write_attempted is not False or channel._writing is not False
                or self._cancel_wire is not None):
            raise AuthorityRefusalError
        _, _, end, failed = CancellationBudget.inspect(self._refs[8])
        if failed or type(end) is not int:
            raise AuthorityRefusalError
        self._cancel_write_attempted = True  # intent before any encoding/timeout/IO attempt
        self._cancel_end = self._cancel_end_snapshot = end
        window = CancellationWindow(end - CLEANUP_NS, end)
        self._cancel_wire = self._cancel_wire_snapshot = encode_frame(
            self._cancel_scope[0], "CANCEL", 1, window.encode(), version=2)
        return self._cancel_wire

    def _cancel_remaining(self, channel):
        RemoteCleanupOwner._cancel_actor(self, channel)
        if (self._cancel_write_attempted is not True or self._cancel_write_completed is not False
                or channel._writing is not True or type(self._cancel_wire) is not bytes):
            raise AuthorityRefusalError
        remaining = RemoteCleanupOwner._remaining(self)
        RemoteCleanupOwner._cancel_actor(self, channel)
        if (channel._writing is not True or remaining <= 0
                or CancellationBudget.inspect(self._refs[8])[2] != self._cancel_end):
            raise AuthorityRefusalError
        return remaining

    async def _work(self):
        from .presentation_remote import RemoteOperationOwner

        if self._initialized is not True or self._unknown is not False:
            return False  # partial initialization never opens work
        try:
            RemoteCleanupOwner._guard(self)
            allowed = await self._barriers_snapshot.start
            RemoteCleanupOwner._guard(self)
            if allowed is not True or self._intent:
                raise AuthorityRefusalError
            return await RemoteOperationOwner._begin_ready_exchange(self._remote_snapshot)
        except BaseException:
            RemoteCleanupOwner.request(self)
            raise

    async def _cleanup(self):
        from .presentation_remote import RemoteOperationOwner

        if self._initialized is not True or self._unknown is not False:
            return False  # partial native allocations remain retained unknown
        try:
            RemoteCleanupOwner._guard(self)
            if self._intent is False:
                try:
                    now = RemoteOperationOwner._work_now(self._remote_snapshot)
                    timeout = (self._refs[9] - now) / 1_000_000_000
                    await asyncio.wait((self._barriers_snapshot.cause,), timeout=timeout)
                except asyncio.CancelledError:
                    RemoteCleanupOwner.request(self)
                    raise  # cancellation of cleanup itself is unknown, never a replacement
                except BaseException:
                    RemoteCleanupOwner.request(self)
            # A cause can precede the first cleanup task step. Never sample a
            # work clock again after retirement; use only the original cleanup clock.
            RemoteCleanupOwner.request(self)  # deadline or earlier event; never a new timer
            if self._unknown or RemoteCleanupOwner._remaining(self) <= 0:
                self._unknown = True
                return False
            work = self._allocations_snapshot[1].task
            if not _TASK.done(work):
                await asyncio.wait((work,), timeout=RemoteCleanupOwner._remaining(self))
            RemoteCleanupOwner._guard(self)
            if not _TASK.done(work):
                self._unknown = True
                return False
            self._work_joined = True
            with suppress(BaseException):
                _TASK.result(work)  # observe/retrieve; no publication or release
            channel = self._refs[3]
            if (RemoteCleanupOwner._remaining(self) <= 0 or channel._reading is not False
                    or channel._writing is not False):
                self._unknown = True
                return False
            if RemoteCleanupOwner._can_cancel(self):
                await SocketChannel.send_cancel(channel, self)
                RemoteCleanupOwner._guard(self)
                if RemoteCleanupOwner._remaining(self) <= 0:
                    self._unknown = True
                    return False
            self._socket_closed = SocketChannel.close(channel) is True
            if not self._socket_closed or RemoteCleanupOwner._remaining(self) <= 0:
                self._unknown = True
                return False
            self._clock_closed = SocketChannel.close_clock(channel) is True
            if not self._clock_closed:
                self._unknown = True
            return self._socket_closed and self._clock_closed
        except BaseException:
            self._unknown = True
            return False

    def authorize_work(self):
        RemoteCleanupOwner._guard(self)
        if (self._intent or self._unknown
                or asyncio.current_task() is not self._allocations_snapshot[1].task):
            raise AuthorityRefusalError
        _task_allows_work()

    async def run(self):

        try:
            RemoteCleanupOwner._guard(self)
            _task_allows_work()
            if self._run_attempted or asyncio.current_task() is not self._caller:
                raise AuthorityRefusalError
            self._run_attempted = True
            _FUTURE.set_result(self._barriers_snapshot.start, True)
            result = await asyncio.shield(self._allocations_snapshot[1].task)
            _task_allows_work()
            RemoteCleanupOwner._guard(self)
            record, authority = self._refs[2], self._refs[0]
            custody = self._refs[11]
            if (type(authority) is not ParentAuthorityAdapter
                    or type(custody) is not tuple or len(custody) != 3
                    or record.owner is not custody[0] or record.handle is not custody[1]
                    or record.fence is not custody[2]
                    or result is not True or self._intent
                    or not ParentAuthorityAdapter._current(authority, record)):
                raise AuthorityRefusalError
            RemoteCleanupOwner._guard(self)
            _task_allows_work()
            return True
        except BaseException:
            RemoteCleanupOwner.request(self)
            raise
