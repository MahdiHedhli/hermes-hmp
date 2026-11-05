"""Exclusive selected-v2 CANCEL reader/adoption; no dispatch or release authority.

Service activation and gateway sender remain separate coupled gates. Wire bytes
are read only on the original enrolled channel under its qualified clock domain.
"""
from __future__ import annotations

import asyncio
import os
import socket
import threading

from .presentation_broker_codec import (
    BrokerBinding,
    BrokerFrame,
    BrokerHeader,
    _row,
    decode_header,
    header_size,
)
from .presentation_broker_lifecycle import OperationGrammar
from .presentation_broker_registry import BrokerRegistry, BrokerTicket, _Record
from .presentation_broker_service import _SOCKET_FILENO, _SOCKET_TIMEOUT, SocketChannel
from .presentation_cancel_budget import MAX_NS, CancellationBudget, CancellationWindow
from .presentation_clock import NativeClockOwner, _PeerClockRefusedError
from .presentation_jobs import FrameError
from .presentation_remote_cleanup import _LOOP, _TASK, _initialize_task, _TaskAllocation, _TaskSlot


def _refuse():
    raise FrameError("BI1_BROKER_CANCELLATION_REFUSED")


class BrokerCancellationOwner:
    """One retained native task, one stream cursor, one existing registry budget."""

    @classmethod
    def retain(cls, channel, registry, ticket, grammar):
        if (cls is not BrokerCancellationOwner or type(channel) is not SocketChannel
                or channel._cancel_receiver is not None
                or channel._cancel_receiver_snapshot is not None):
            _refuse()
        owner = BrokerCancellationOwner.__new__(BrokerCancellationOwner)
        channel._cancel_receiver = channel._cancel_receiver_snapshot = owner
        BrokerCancellationOwner.__init__(owner, channel, registry, ticket, grammar)
        return owner

    def __init__(self, channel, registry, ticket, grammar):
        self._channel = self._channel_snapshot = channel
        self._registry = self._registry_snapshot = registry
        self._ticket = self._ticket_snapshot = ticket
        self._grammar = self._grammar_snapshot = grammar
        self._initialized = self._failed = self._retired = self._sampling = False
        self._adopted = self._cancel_attempted = self._joined = False
        self._slot = self._slot_snapshot = _TaskSlot()
        self._allocation = self._allocation_snapshot = None
        self._task_initialized = self._task_initialized_snapshot = None
        self._scope = self._scope_snapshot = None
        self._failure_origin = self._failure_origin_snapshot = (
            grammar if type(grammar) is OperationGrammar else None, None)
        self._buffer = self._buffer_snapshot = bytearray()
        self._frame = self._frame_snapshot = None
        self._frame_seal = self._frame_seal_snapshot = None
        self._timeout = self._timeout_snapshot = None
        self._loop = self._loop_snapshot = asyncio.get_running_loop()
        self._context = self._context_snapshot = (os.getpid(), os.geteuid(), threading.get_ident())
        try:
            if type(registry) is not BrokerRegistry or type(ticket) is not BrokerTicket:
                _refuse()
            # Capture original failure custody under the existing registry lock,
            # before comparing mutable transport/grammar metadata or allocating tasks.
            BrokerRegistry._enter(registry)
            try:
                record = BrokerRegistry._record(registry, ticket)
                self._failure_origin = self._failure_origin_snapshot = (
                    self._failure_origin_snapshot[0], record.cleanup_budget_snapshot)
            finally:
                registry._lock.release()
            if type(channel) is not SocketChannel or type(grammar) is not OperationGrammar:
                _refuse()
            SocketChannel._bindings(channel)
            if not OperationGrammar._configured(grammar):
                _refuse()
            if (type(self._loop) is not _LOOP
                    or asyncio.BaseEventLoop.get_task_factory(self._loop) is not None
                    or channel._cancel_receiver is not self
                    or channel._cancel_receiver_snapshot is not self
                    or channel._role != "broker" or channel._enrollment.protocol_version != 2
                    or channel._reading is not False or channel._writing is not False
                    or grammar._role != "broker" or grammar._version != 2
                    or grammar._mode != "operation" or grammar._begun is not True
                    or grammar._client_next != 1 or grammar._cancel is not False
                    or grammar._failed is not False):
                _refuse()
            clock = SocketChannel._qualified_clock(channel)
            if (type(record) is not _Record or type(record.cleanup_budget) is not CancellationBudget
                    or record.cleanup_budget is not record.cleanup_budget_snapshot
                    or grammar._binding != record.binding):
                _refuse()
            self._scope = self._scope_snapshot = (
                record, record.binding, record.deadline_ns, record.cleanup_budget,
                registry._records, channel._values_snapshot, clock, clock._domain_snapshot,
                clock._domain_values, clock._qualification_snapshot)
            self._slot.coroutine = self._slot.coroutine_snapshot = (
                BrokerCancellationOwner._read(self))
            self._slot.task = self._slot.task_snapshot = _TASK.__new__(_TASK)
            self._allocation = self._allocation_snapshot = _TaskAllocation(
                self._slot.task, self._slot.coroutine)
            _initialize_task(self._slot, self._loop)
            self._task_initialized = self._task_initialized_snapshot = object()
            self._initialized = True
            BrokerCancellationOwner._guard(self)
        except BaseException:
            self._failed = True
            # No unqualified clock, no assumption that a failed initializer did
            # nothing: retire original work and retain any partial native task.
            origin = self._failure_origin_snapshot
            if type(origin) is tuple and len(origin) == 2:
                if type(origin[0]) is OperationGrammar:
                    OperationGrammar.invalidate(origin[0])
                if type(origin[1]) is CancellationBudget:
                    CancellationBudget.refuse(origin[1])
            raise FrameError("BI1_BROKER_CANCELLATION_REFUSED") from None

    def __repr__(self):
        return "<BrokerCancellationOwner redacted>"

    def _guard(self, *, reader=False, cleanup=False):
        c, reg, ticket = self._channel, self._registry, self._ticket
        g, scope = self._grammar, self._scope
        if type(c) is not SocketChannel:
            _refuse()
        SocketChannel._bindings(c)  # exact enrollment types before any field/property reads
        if (self._initialized is not True
                or (self._failed is not False and not (cleanup and self._failed is True))
                or type(c) is not SocketChannel or c is not self._channel_snapshot
                or type(reg) is not BrokerRegistry or reg is not self._registry_snapshot
                or type(ticket) is not BrokerTicket or ticket is not self._ticket_snapshot
                or type(g) is not OperationGrammar or g is not self._grammar_snapshot
                or type(scope) is not tuple or len(scope) != 10 or scope is not self._scope_snapshot
                or type(scope[0]) is not _Record or type(scope[3]) is not CancellationBudget
                or self._failure_origin is not self._failure_origin_snapshot
                or type(self._failure_origin) is not tuple or len(self._failure_origin) != 2
                or self._failure_origin[0] is not g or self._failure_origin[1] is not scope[3]
                or type(reg._records) is not dict or reg._records is not scope[4]
                or reg._records.get(ticket) is not scope[0]
                or scope[0].binding is not scope[1] or scope[0].deadline_ns is not scope[2]
                or scope[0].cleanup_budget is not scope[3]
                or scope[0].cleanup_budget_snapshot is not scope[3]
                or c._cancel_receiver is not self or c._cancel_receiver_snapshot is not self
                or c._role != "broker" or c._remote_owner is not None
                or c._terminal_owner is not None
                or c._socket is not c._socket_snapshot or type(c._socket) is not socket.socket
                or c._values_snapshot is not scope[5]
                or c._enrollment.protocol_version != 2 or c._clock_owner is not scope[6]
                or c._clock_owner_snapshot is not scope[6] or type(scope[6]) is not NativeClockOwner
                or scope[6]._domain is not scope[7] or scope[6]._domain_snapshot is not scope[7]
                or scope[6]._domain_values is not scope[8]
                or scope[6]._qualification is not scope[9]
                or scope[6]._qualification_snapshot is not scope[9]
                or type(self._loop) is not _LOOP or self._loop is not self._loop_snapshot
                or asyncio.get_running_loop() is not self._loop
                or asyncio.BaseEventLoop.get_task_factory(self._loop) is not None
                or type(self._context) is not tuple or self._context is not self._context_snapshot
                or len(self._context) != 3 or any(type(v) is not int for v in self._context)
                or self._context != (os.getpid(), os.geteuid(), threading.get_ident())
                or any(type(v) is not bool for v in (self._retired, self._sampling, self._adopted,
                                                     self._cancel_attempted, self._joined))
                or type(self._buffer) is not bytearray or self._buffer is not self._buffer_snapshot
                or len(self._buffer) > 8 + 1024 + 16
                or self._slot is not self._slot_snapshot or type(self._slot) is not _TaskSlot
                or type(self._allocation) is not _TaskAllocation
                or self._allocation is not self._allocation_snapshot
                or self._slot.task is not self._allocation.task
                or self._slot.task_snapshot is not self._allocation.task
                or self._slot.coroutine is not self._allocation.coroutine
                or self._slot.coroutine_snapshot is not self._allocation.coroutine
                or self._slot.initialized is not True or self._slot.attempted is not True
                or type(self._task_initialized) is not object
                or self._task_initialized is not self._task_initialized_snapshot
                or type(self._allocation.task) is not _TASK
                or _TASK.get_coro(self._allocation.task) is not self._allocation.coroutine
                or self._timeout is not self._timeout_snapshot
                or (self._timeout is not None and type(self._timeout) is not asyncio.Timeout)
                or not OperationGrammar._configured(g)
                or g._binding != scope[1] or g._version != 2):
            _refuse()
        if reader and (asyncio.current_task() is not self._allocation.task
                       or _TASK.cancelling(self._allocation.task)):
            _refuse()
        original, _, _, failed = CancellationBudget.inspect(scope[3])
        if original != scope[2] or failed:
            _refuse()
        seal = self._frame_seal
        if self._frame is not self._frame_snapshot or seal is not self._frame_seal_snapshot:
            _refuse()
        if self._frame is not None:
            if (type(seal) is not tuple or len(seal) != 3
                    or type(self._frame) is not BrokerFrame or self._frame is not seal[0]
                    or type(self._frame.header) is not BrokerHeader
                    or self._frame.header is not seal[1]
                    or type(self._frame.body) is not bytes or self._frame.body is not seal[2]
                    or type(self._frame.header.binding) is not BrokerBinding):
                _refuse()
            _row(self._frame.header)
            h = self._frame.header
            if (h.binding != scope[1] or h.kind != "CANCEL" or h.sequence != 1
                    or h.version != 2 or h.body_length != 16 or len(self._frame.body) != 16):
                _refuse()
        if cleanup and c._closed_known is True:
            # Concrete SocketChannel.close already proved this exact local
            # socket closed. Sampling retained clock FDs between the two close
            # primitives must not inspect a socket FD that is now closed.
            if reader or _SOCKET_FILENO(c._socket_snapshot) != -1:
                _refuse()
        else:
            SocketChannel._local_integrity(c)
            timeout = _SOCKET_TIMEOUT(c._socket)
            if (os.get_blocking(c._fd) is not False
                    or type(timeout) is not float or timeout != 0.0):
                _refuse()
        if SocketChannel._qualified_clock(c) is not scope[6]:
            _refuse()

    def _local_cause(self):
        # Retire before native cleanup sampling; no GO/launch can be restored.
        self._retired = True
        scope = self._scope_snapshot
        if type(scope) is not tuple or len(scope) != 10:
            self._failed = True
            return
        if type(self._grammar_snapshot) is OperationGrammar:
            OperationGrammar.invalidate(self._grammar_snapshot)
        try:
            BrokerCancellationOwner._guard(self, cleanup=True)
            if self._sampling:
                _refuse()
            self._sampling = True
            now = NativeClockOwner.cleanup_sample(scope[6])
            BrokerCancellationOwner._guard(self, cleanup=True)
            CancellationBudget.local(scope[3], now)
        except BaseException:
            self._failed = True
            if type(scope[3]) is CancellationBudget:
                CancellationBudget.refuse(scope[3])
        finally:
            self._sampling = False

    def _remaining(self):
        BrokerCancellationOwner._guard(self, reader=True)
        budget, clock, deadline = self._scope[3], self._scope[6], self._scope[2]
        _, _, end, failed = CancellationBudget.inspect(budget)
        if failed or self._sampling:
            _refuse()
        self._sampling = True
        try:
            if not self._retired and end is None:
                try:
                    now = NativeClockOwner.sample(clock)
                except (asyncio.CancelledError, _PeerClockRefusedError):
                    raise  # known task/peer-only failure can retire original local cleanup
                except BaseException:
                    self._failed = True
                    CancellationBudget.refuse(budget)
                    raise  # generic work-clock failure is not expiry/cleanup eligibility
                BrokerCancellationOwner._guard(self, reader=True)
                if type(now) is not int or not 0 <= now <= MAX_NS:
                    self._failed = True
                    CancellationBudget.refuse(budget)
                    _refuse()
                if now < deadline:
                    return (deadline - now) / 1_000_000_000
                # Known expiry only; a native sampling error is not an expiry.
                self._sampling = False
                BrokerCancellationOwner._local_cause(self)
                BrokerCancellationOwner._guard(self, reader=True)
                self._sampling = True
            else:
                self._retired = True
                OperationGrammar.invalidate(self._grammar_snapshot)
            now = NativeClockOwner.cleanup_sample(clock)
            BrokerCancellationOwner._guard(self, reader=True)
            remaining = CancellationBudget.remaining_ns(budget, now)
            if not remaining:
                _refuse()
            return remaining / 1_000_000_000
        finally:
            self._sampling = False

    async def _exact(self, count):
        if type(count) is not int or not 0 < count <= 8 + 1024 + 16:
            _refuse()
        target = len(self._buffer) + count
        if target > 8 + 1024 + 16:
            _refuse()
        while len(self._buffer) < target:
            BrokerCancellationOwner._remaining(self)
            end = CancellationBudget.inspect(self._scope[3])[2]
            cutoff = self._scope[2] if end is None else end
            self._timeout = self._timeout_snapshot = asyncio.timeout_at(cutoff / 1_000_000_000)
            try:
                async with self._timeout:
                    part = await _LOOP.sock_recv(
                        self._loop, self._channel._socket, target - len(self._buffer))
            except TimeoutError:
                # Preserve partial bytes and sample the same absolute budget.
                BrokerCancellationOwner._remaining(self)
                continue
            BrokerCancellationOwner._guard(self, reader=True)
            if type(part) is not bytes or not part:
                _refuse()
            self._buffer.extend(part)
        return bytes(self._buffer[target - count:target])

    async def _read(self):
        if self._initialized is not True or self._failed is not False:
            return None  # partial initializer remains retained, no bytes read
        try:
            BrokerCancellationOwner._guard(self, reader=True)
            if self._channel._reading is not False:
                _refuse()
            self._channel._reading = True
            prefix = await BrokerCancellationOwner._exact(self, 8)
            raw = prefix + await BrokerCancellationOwner._exact(self, header_size(prefix))
            header = decode_header(raw, expected=self._scope[1], expected_version=2)
            if header.kind != "CANCEL" or header.sequence != 1 or header.body_length != 16:
                _refuse()
            # A validated CANCEL header is a local revocation hint. Retire work
            # before waiting for its body, but adopt nothing or abort resources
            # until the complete original window is semantically validated.
            BrokerCancellationOwner._local_cause(self)
            BrokerCancellationOwner._guard(self, reader=True)
            body = await BrokerCancellationOwner._exact(self, 16)
            self._frame = self._frame_snapshot = BrokerFrame(header, body)
            self._frame_seal = self._frame_seal_snapshot = (self._frame, header, body)
            OperationGrammar.observe(self._grammar, self._frame, sender="client")
            self._retired = True  # before cleanup native boundary / adoption
            window = CancellationWindow.decode(body)
            now = NativeClockOwner.cleanup_sample(self._scope[6])
            BrokerCancellationOwner._guard(self, reader=True)
            CancellationBudget.inherit(self._scope[3], window, now)
            self._adopted = True
            return self._frame
        except BaseException:
            BrokerCancellationOwner._local_cause(self)
            self._failed = True
            raise
        finally:
            # Only original channel metadata; no stream or resource closure.
            c = self._channel_snapshot
            if type(c) is SocketChannel and c._cancel_receiver_snapshot is self:
                c._reading = False

    def abort(self):
        BrokerCancellationOwner._local_cause(self)
        allocation = self._allocation_snapshot
        if (self._cancel_attempted is False and type(allocation) is _TaskAllocation
                and type(allocation.task) is _TASK
                and type(self._task_initialized) is object
                and self._task_initialized is self._task_initialized_snapshot
                and not _TASK.done(allocation.task)):
            self._cancel_attempted = True
            _TASK.cancel(allocation.task)

    def cleanup_remaining(self):
        """Original local cleanup time after a failed/completed read; no new IO grant."""
        BrokerCancellationOwner._guard(self, cleanup=True)
        if self._retired is not True or self._sampling is not False:
            _refuse()
        self._sampling = True
        try:
            now = NativeClockOwner.cleanup_sample(self._scope[6])
            BrokerCancellationOwner._guard(self, cleanup=True)
            return CancellationBudget.remaining_ns(self._scope[3], now) / 1_000_000_000
        finally:
            self._sampling = False

    async def join(self):
        """Actual task join only, never socket/native/registry closure."""
        allocation = self._allocation_snapshot
        if (type(allocation) is not _TaskAllocation or type(allocation.task) is not _TASK
                or type(self._task_initialized) is not object
                or self._task_initialized is not self._task_initialized_snapshot):
            return False
        if _TASK.done(allocation.task):
            self._joined = True
            return True
        BrokerCancellationOwner.abort(self)
        try:
            remaining = BrokerCancellationOwner.cleanup_remaining(self)
            if remaining:
                await asyncio.wait((allocation.task,), timeout=remaining)
            self._joined = _TASK.done(allocation.task)
            return self._joined
        except BaseException:
            return False
