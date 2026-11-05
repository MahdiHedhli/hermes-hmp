"""Native-owned remote BEGIN/READY binding; no GO/result/release or live route.

Original request credentials and policy remain in ParentAuthorityAdapter. The
broker connection is a separate custody plane; it is never a local process.
"""
from __future__ import annotations

import asyncio
import os
import time
from contextlib import suppress

from .presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    OpaqueOperation,
    ParentAuthorityAdapter,
    _Record,
)
from .presentation_broker_codec import BrokerBinding, BrokerFrame, BrokerHeader, _binding
from .presentation_broker_service import SocketChannel, _task_allows_work
from .presentation_cancel_budget import CancellationBudget
from .presentation_clock import ClockDomain, NativeClockOwner
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import CapturedLease, JobHandle, JobOwner, RemotePhase, State
from .presentation_parent_policy import ParentPolicyReadOwner
from .presentation_policy_binding import NativePolicyWork
from .presentation_policy_thread import PolicyThreadOwner


class RemoteOperationOwner:
    """One existing reservation and one immutable input3 transfer, no replay.

    Only ParentAuthorityAdapter.bind_remote may retain and initialize this owner.
    The shared slot exists before initialization; even a partial owner is debt.
    No method forwards GO, reads RESULT or claims remote terminal custody.
    """
    def __init__(self, authority, operation, channel, binding, packet):
        self._authority = self._authority_snapshot = authority
        self._operation = self._operation_snapshot = operation
        self._channel = self._channel_snapshot = channel
        self._binding = self._binding_snapshot = binding
        self._packet = self._packet_snapshot = packet
        self._failed = False
        self._begin_attempted = False
        self._send_claimed = self._send_completed = self._receive_claimed = False
        self._initialized = False
        self._record = self._record_snapshot = None
        self._seal = self._seal_snapshot = None
        self._loop = self._loop_snapshot = None
        self._context = self._context_snapshot = None
        self._cleanup_owner = self._cleanup_owner_snapshot = None
        self._cleanup_budget = self._cleanup_budget_snapshot = None
        self._protocol = self._protocol_snapshot = None
        self._clock_owner = self._clock_owner_snapshot = None
        self._clock_domain = self._clock_domain_snapshot = None
        self._clock_domain_values = self._clock_domain_values_snapshot = None
        self._clock_qualification = self._clock_qualification_snapshot = None
        try:
            self._loop = self._loop_snapshot = asyncio.get_running_loop()
            self._context = self._context_snapshot = (os.getpid(), os.geteuid())
            if (type(authority) is not ParentAuthorityAdapter
                    or type(operation) is not OpaqueOperation
                    or type(channel) is not SocketChannel
                    or channel._role != "gateway" or channel._terminal_owner is not None
                    or type(binding) is not BrokerBinding or type(packet) is not bytes):
                raise AuthorityRefusalError
            record = authority._record(operation)
            self._record = self._record_snapshot = record
            work = record.policy_work
            if (record.remote_operation is not self or type(work) is not NativePolicyWork
                    or work._authority is not authority or work._record is not record
                    or work._packet is not packet or work._packet_snapshot is not packet
                    or work._postchecked is not True or work._transfer_attempted is not True
                    or type(work._thread) is not PolicyThreadOwner
                    or type(work._policy) is not ParentPolicyReadOwner
                    or work._thread.joined is not True
                    or work.resources_closed is not True):
                raise AuthorityRefusalError
            snapshot = work.observed_snapshot()  # exact joined/postchecked parent policy
            job = record.owner._resolve(record.handle)
            home, retained = job.parent_result_context
            if (home != work._scope[1] or retained.chain != snapshot.chain
                    or dict(retained.counts) != dict(snapshot.counts)):
                raise AuthorityRefusalError
            row = decode_input_v3(packet)
            _binding(binding)
            scope = channel._enrollment.scope
            if ((binding.iid, binding.listener, binding.broker)
                    != (scope.iid, scope.listener, scope.broker)):
                raise AuthorityRefusalError
            self._row = self._row_snapshot = row
            self._values = self._values_snapshot = (
                binding.iid, binding.listener, binding.broker, binding.channel, binding.operation)
            self._end = self._end_snapshot = int(record.deadline * 1_000_000_000)
            budget = record.cleanup_budget
            if (type(budget) is not CancellationBudget
                    or budget is not record.cleanup_budget_snapshot
                    or CancellationBudget.inspect(budget) != (self._end, None, None, False)):
                raise AuthorityRefusalError
            self._cleanup_budget = self._cleanup_budget_snapshot = budget
            self._protocol = self._protocol_snapshot = channel._enrollment.protocol_version
            if self._protocol == 2:
                clock = SocketChannel._qualified_clock(channel)
                self._clock_owner = self._clock_owner_snapshot = clock
                self._clock_domain = self._clock_domain_snapshot = clock._domain_snapshot
                self._clock_domain_values = self._clock_domain_values_snapshot = (
                    clock._domain_values)
                self._clock_qualification = self._clock_qualification_snapshot = (
                    clock._qualification)
            RemoteOperationOwner._clock_binding(self)
            root, native_home, profile, uid, gid = work._scope
            if (row["iid"] != record.lease.iid or binding.iid != record.lease.iid
                    or row["profile"] != record.lease.profile or profile != record.lease.profile
                    or row["challenge"] != record.owner.challenge(record.handle)
                    or row["epoch"] != record.lease.epoch or row["operation"] != job.operation
                    or row["deadline_ns"] != self._end or row["root"] != root
                    or row["home"] != native_home or native_home != record.initial_home
                    or row["uid"] != uid or row["gid"] != gid):
                raise AuthorityRefusalError
            self._lease_values = self._lease_values_snapshot = self._lease_tuple(record.lease)
            self._seal = self._seal_snapshot = self._references()
            channel.claim_remote(self)  # monotonic ownership before any exchange effect
            self._initialized = True
            self._check(RemotePhase.BOUND)
        except BaseException:
            self._poison()
            raise

    @staticmethod
    def _lease_tuple(lease):
        if type(lease) is not CapturedLease or type(lease.profile) is not str:
            raise AuthorityRefusalError
        CapturedLease.__post_init__(lease)
        return (lease.iid, lease.device_id, lease.user_id, lease.family_id,
                lease.profile, lease.credential_digest, lease.native_binding, lease.epoch)

    def _references(self):
        r, c = self._record, self._channel
        if (type(r.owner) is not JobOwner or r.owner is not self._authority.owner
                or type(r.handle) is not JobHandle or type(r.policy_work) is not NativePolicyWork):
            raise AuthorityRefusalError
        job, work = r.owner._resolve(r.handle), r.policy_work
        return (r.owner, r.handle, r.lease, r.remote_slot, work,
                job.parent_result_context, r.deadline, c._enrollment,
                c._values, c._socket, c._identity, c._endpoint, c._observation,
                work._thread, work._policy, work._scope, r.listener, r.fence,
                r.fence_epoch, r.store, r.bridge, r.identity, r.native_owner, r.headers,
                r._custody_snapshot, r.cleanup_budget, self._protocol,
                self._clock_owner, self._clock_domain, self._clock_domain_values,
                self._clock_qualification)

    def _clock_binding(self):
        """Original selection/domain only; no new clock or cleanup authority."""
        c = self._channel_snapshot
        if type(c) is not SocketChannel:
            raise AuthorityRefusalError
        SocketChannel._bindings(c)
        if (self._channel is not c
                or type(self._protocol) is not int or self._protocol not in (1, 2)
                or self._protocol is not self._protocol_snapshot
                or c._enrollment.protocol_version != self._protocol
                or c._values_snapshot[-1] != self._protocol
                or self._clock_owner is not self._clock_owner_snapshot
                or self._clock_domain is not self._clock_domain_snapshot
                or self._clock_domain_values is not self._clock_domain_values_snapshot
                or self._clock_qualification is not self._clock_qualification_snapshot):
            raise AuthorityRefusalError
        if self._protocol == 1:
            if any(v is not None for v in (self._clock_owner, self._clock_domain,
                                          self._clock_domain_values, self._clock_qualification,
                                          c._clock_owner, c._clock_owner_snapshot)):
                raise AuthorityRefusalError
            return
        clock, domain, values = self._clock_owner, self._clock_domain, self._clock_domain_values
        if (type(clock) is not NativeClockOwner
                or SocketChannel._qualified_clock(c) is not clock
                or type(domain) is not ClockDomain
                or clock._domain is not domain or clock._domain_snapshot is not domain
                or type(values) is not tuple or len(values) != 4
                or clock._domain_values is not values
                or type(self._clock_qualification) is not object
                or clock._qualification is not self._clock_qualification
                or clock._qualification_snapshot is not self._clock_qualification
                or type(domain.platform) is not str or type(domain.implementation) is not str
                or type(domain.boot) is not bytes
                or (domain.namespace is not None and (type(domain.namespace) is not tuple
                    or len(domain.namespace) != 2
                    or any(type(v) is not int for v in domain.namespace)))
                or any(x is not y for x, y in zip(
                    (domain.platform, domain.implementation, domain.boot, domain.namespace),
                    values, strict=True))):
            raise AuthorityRefusalError

    def _retained_local(self):
        """Callback-free reference fence before owner/policy methods after native IO."""
        a, r, c, seal = self._authority, self._record, self._channel, self._seal
        if (type(a) is not ParentAuthorityAdapter or a is not self._authority_snapshot
                or type(r) is not _Record or r is not self._record_snapshot
                or type(c) is not SocketChannel or c is not self._channel_snapshot
                or self._cleanup_owner is not self._cleanup_owner_snapshot
                or type(seal) is not tuple or seal is not self._seal_snapshot or len(seal) != 31
                or type(r.owner) is not JobOwner or type(r.handle) is not JobHandle
                or type(r.fence) is not ListenerFence or type(r.policy_work) is not NativePolicyWork
                or a._clock is not time.monotonic or r.owner._clock is not time.monotonic):
            raise AuthorityRefusalError
        work = r.policy_work
        # Index5 is a resolved JobOwner context: never resolve it until these
        # callback-free local references have passed. _references checks it later.
        current = (r.owner, r.handle, r.lease, r.remote_slot, work,
                   seal[5], r.deadline, c._enrollment, c._values, c._socket,
                   c._identity, c._endpoint, c._observation, work._thread, work._policy,
                   work._scope, r.listener, r.fence, r.fence_epoch, r.store, r.bridge,
                   r.identity, r.native_owner, r.headers, r._custody_snapshot,
                   r.cleanup_budget, self._protocol, self._clock_owner, self._clock_domain,
                   self._clock_domain_values, self._clock_qualification)
        if (not all(x is y for x, y in zip(current, seal, strict=True))
                or r.cleanup_budget is not r.cleanup_budget_snapshot
                or self._failed is not False):
            raise AuthorityRefusalError

    def _work_now(self):
        RemoteOperationOwner._retained_local(self)
        RemoteOperationOwner._clock_binding(self)
        now = (NativeClockOwner.sample(self._clock_owner) if self._protocol == 2
               else time.monotonic_ns())
        RemoteOperationOwner._retained_local(self)
        RemoteOperationOwner._clock_binding(self)
        _task_allows_work()
        if (type(self._end) is not int or self._end is not self._end_snapshot
                or type(now) is not int or not 0 <= now < self._end):
            raise AuthorityRefusalError
        return now

    def __repr__(self):
        return "<RemoteOperationOwner redacted>"

    def _poison(self):
        if self._failed is True:
            return
        self._failed = True
        authority, operation = self._authority_snapshot, self._operation_snapshot
        if type(authority) is ParentAuthorityAdapter and type(operation) is OpaqueOperation:
            # Existing slot/record remains retained even after metadata refusal.
            with suppress(AuthorityRefusalError, ValueError):
                record = self._record_snapshot
                if record is None:
                    record = authority._record(operation)
                authority._unknown(record)

    def _check(self, phase: RemotePhase):
        try:
            _task_allows_work()
            if self._protocol == 2 and self._cleanup_owner_snapshot is not None:
                from .presentation_remote_cleanup import RemoteCleanupOwner

                owner = self._cleanup_owner_snapshot
                if type(owner) is not RemoteCleanupOwner or self._cleanup_owner is not owner:
                    raise AuthorityRefusalError
                RemoteCleanupOwner.authorize_work(owner)
            a, r, c = self._authority, self._record, self._channel
            if (self._failed is not False or self._initialized is not True
                    or type(self._begin_attempted) is not bool
                    or any(type(v) is not bool for v in (self._send_claimed, self._send_completed,
                                                       self._receive_claimed))
                    or (self._send_completed and not self._send_claimed)
                    or (self._receive_claimed and not self._send_completed)
                    or type(a) is not ParentAuthorityAdapter or a is not self._authority_snapshot
                    or self._operation is not self._operation_snapshot
                    or r is not self._record_snapshot or a._record(self._operation) is not r
                    or type(r.owner) is not JobOwner or r.owner is not a.owner
                    or type(r.handle) is not JobHandle
                    or type(r.policy_work) is not NativePolicyWork
                    or c is not self._channel_snapshot or type(c) is not SocketChannel
                    or c._terminal_owner is not None or c._role != "gateway"
                    or c._remote_owner is not self or c._remote_owner_snapshot is not self
                    or self._binding is not self._binding_snapshot
                    or self._packet is not self._packet_snapshot or type(self._packet) is not bytes
                    or self._row is not self._row_snapshot or type(self._row) is not dict
                    or self._values is not self._values_snapshot or type(self._values) is not tuple
                    or len(self._values) != 5 or any(type(v) is not str for v in self._values)
                    or self._seal is not self._seal_snapshot or type(self._seal) is not tuple
                    or len(self._seal) != 31
                    or type(self._cleanup_budget) is not CancellationBudget
                    or self._cleanup_budget is not self._cleanup_budget_snapshot
                    or r.cleanup_budget is not self._cleanup_budget
                    or r.cleanup_budget is not r.cleanup_budget_snapshot
                    or self._lease_values is not self._lease_values_snapshot
                    or type(self._lease_values) is not tuple or len(self._lease_values) != 8
                    or self._end is not self._end_snapshot or type(self._end) is not int
                    or self._loop is not self._loop_snapshot
                    or asyncio.get_running_loop() is not self._loop
                    or self._context is not self._context_snapshot
                    or type(self._context) is not tuple
                    or len(self._context) != 2 or any(type(v) is not int for v in self._context)
                    or (os.getpid(), os.geteuid()) != self._context
                    or a._clock is not time.monotonic or r.owner._clock is not time.monotonic
                    or r.remote_operation is not self or r.child is not None
                    or r.process_owner is not None or r.reader_supervisor is not None
                    or r.native_claim is not None or r.initial_complete is not True
                    or r.owner.inspect(r.handle)[0] is not State.STARTING
                    or r.owner.inspect_remote(r.handle) is not phase):
                raise AuthorityRefusalError
            work = r.policy_work
            job = r.owner._resolve(r.handle)
            current = self._references()
            if (not all(x is y for x, y in zip(current, self._seal, strict=True))
                    or type(work) is not NativePolicyWork or work._packet is not self._packet
                    or work._invalid is not False or work._transfer_attempted is not True
                    or work._packet_snapshot is not self._packet or work._postchecked is not True
                    or self._lease_tuple(r.lease) != self._lease_values
                    or work.resources_closed is not True or not a._current(r)
                    or not r.owner._current(job) or not a._current(r)):
                raise AuthorityRefusalError
            _binding(self._binding)
            b = self._binding
            if ((b.iid, b.listener, b.broker, b.channel, b.operation) != self._values
                    or decode_input_v3(self._packet) != self._row
                    or r.initial_home != self._row["home"]
                    or int(r.deadline * 1_000_000_000) != self._end
                    or RemoteOperationOwner._work_now(self) >= self._end):
                raise AuthorityRefusalError
            c._check()  # original enrolled peer/endpoint, never status-terminal fallback
            c._local_integrity()
            c._endpoint.validates(c._observation)
            if (r.remote_operation is not self or not a._current(r)
                    or self._failed is not False
                    or not all(x is y for x, y in zip(self._references(), self._seal, strict=True))
                    or self._lease_tuple(r.lease) != self._lease_values
                    or work._invalid is not False or work._packet is not self._packet
                    or r.owner.inspect_remote(r.handle) is not phase
                    or c._remote_owner is not self or self._packet is not self._packet_snapshot):
                raise AuthorityRefusalError
            _task_allows_work()
            now = RemoteOperationOwner._work_now(self)
            _task_allows_work()  # native/clock callbacks cannot revive pending cancellation
            if (now >= self._end or r.owner.inspect_remote(r.handle) is not phase
                    or not a._current(r) or self._failed is not False
                    or not all(x is y for x, y in zip(
                        self._references(), self._seal, strict=True))):
                raise AuthorityRefusalError
        except BaseException:
            self._poison()
            raise

    def _authorize_channel(self, channel, direction, binding, end_ns, frame):
        """Linear channel I/O claims; no generic owner token can send GO or results."""
        try:
            self._check(RemotePhase.BEGIN_INTENT)
            if (channel is not self._channel_snapshot or binding is not self._binding_snapshot
                    or type(end_ns) is not int or end_ns != self._end):
                raise AuthorityRefusalError
            if direction == "send":
                if (self._send_claimed or type(frame) is not BrokerFrame
                        or type(frame.header) is not BrokerHeader
                        or type(frame.header.kind) is not str or frame.header.kind != "BEGIN"
                        or type(frame.header.sequence) is not int or frame.header.sequence != 0
                        or type(frame.header.version) is not int
                        or frame.header.version != self._protocol
                        or type(frame.header.body_length) is not int
                        or frame.body is not self._packet_snapshot
                        or frame.header.body_length != len(self._packet_snapshot)):
                    raise AuthorityRefusalError
                self._send_claimed = True
            elif direction == "receive":
                if self._receive_claimed or not self._send_completed or frame is not None:
                    raise AuthorityRefusalError
                self._receive_claimed = True
            else:
                raise AuthorityRefusalError
        except BaseException:
            self._poison()
            raise

    def _authorize_send_completion(self, channel, frame, end_ns):
        RemoteOperationOwner._check(self, RemotePhase.BEGIN_INTENT)
        if (channel is not self._channel_snapshot or self._send_claimed is not True
                or self._send_completed is not False or self._receive_claimed is not False
                or type(frame) is not BrokerFrame or type(frame.header) is not BrokerHeader
                or frame.header.binding is not self._binding_snapshot
                or frame.body is not self._packet_snapshot
                or type(frame.header.kind) is not str or frame.header.kind != "BEGIN"
                or type(frame.header.version) is not int or frame.header.version != self._protocol
                or type(frame.header.sequence) is not int or frame.header.sequence != 0
                or type(frame.header.body_length) is not int
                or frame.header.body_length != len(self._packet_snapshot)
                or type(end_ns) is not int or end_ns != self._end_snapshot):
            self._poison()
            raise AuthorityRefusalError

    async def begin_ready(self) -> bool:
        """Selected v2 retains independent cleanup before any exchange effect."""
        if self._protocol == 1:
            return await RemoteOperationOwner._begin_ready_exchange(self)
        from .presentation_remote_cleanup import RemoteCleanupOwner

        try:
            if self._cleanup_owner is not None or self._cleanup_owner_snapshot is not None:
                retained = self._cleanup_owner_snapshot
                if type(retained) is RemoteCleanupOwner:
                    RemoteCleanupOwner.request(retained)
                raise AuthorityRefusalError
            self._check(RemotePhase.BOUND)
            owner = RemoteCleanupOwner.__new__(RemoteCleanupOwner)
            self._cleanup_owner = self._cleanup_owner_snapshot = owner
            RemoteCleanupOwner.__init__(owner, self)
            return await RemoteCleanupOwner.run(owner)
        except BaseException:
            self._poison()
            raise

    async def _begin_ready_exchange(self) -> bool:
        """Fresh native check, one input BEGIN and one READY; no work permission."""
        try:
            if self._begin_attempted:
                raise AuthorityRefusalError
            self._begin_attempted = True
            self._check(RemotePhase.BOUND)
            if not await self._authority._observe(self._record, "PRE_GO"):
                raise AuthorityRefusalError
            self._check(RemotePhase.BOUND)
            self._record.owner.remote_transition(
                self._record.handle, self, RemotePhase.BEGIN_INTENT)
            self._check(RemotePhase.BEGIN_INTENT)
            frame = BrokerFrame(BrokerHeader(self._binding, "BEGIN", 0, len(self._packet),
                                            self._protocol),
                                self._packet)
            await SocketChannel.send(self._channel, frame, self._end, owner=self)
            self._send_completed = True
            self._check(RemotePhase.BEGIN_INTENT)
            ready = await SocketChannel.receive(
                self._channel, self._end, expected=self._binding, owner=self)
            self._check(RemotePhase.BEGIN_INTENT)
            if (type(ready.header.version) is not int or ready.header.version != self._protocol
                    or ready.header.kind != "READY" or ready.header.sequence != 0
                    or ready.body != b""):
                raise AuthorityRefusalError
            if not await self._authority._observe(self._record, "PRE_GO"):
                raise AuthorityRefusalError
            self._check(RemotePhase.BEGIN_INTENT)
            self._record.owner.remote_transition(self._record.handle, self, RemotePhase.READY)
            self._check(RemotePhase.READY)
            return True
        except asyncio.CancelledError:
            self._poison()
            raise
        except Exception:
            self._poison()
            raise AuthorityRefusalError from None
        except BaseException:
            self._poison()
            raise
