"""Original-task native READY transition after current signed READY and fresh PRE_GO.

Source-only, no production caller or worker GO/resource/publication permission.
"""

from __future__ import annotations

import asyncio
from typing import NamedTuple

from .presentation_authority import ParentAuthorityAdapter
from .presentation_broker_service import SocketChannel
from .presentation_clock import NativeClockOwner
from .presentation_credential_phase import check_commitment, check_complete_frame
from .presentation_credential_ready_read import (
    _READY_READ_MINT,
    NativeReadyReceiver,
    _ReadyReadComplete,
    _ReadyReadScope,
)
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError, JobOwner, RemotePhase, State, _Job
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _TASK

_READY_TRANSITION_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_READY_TRANSITION_REFUSED")


class _ReadyTransitionScope(NamedTuple):
    receiver: object
    read_scope: _ReadyReadScope
    read_fact: _ReadyReadComplete
    producer: object

    def __repr__(self):
        return "<ReadyTransitionScope original-native-work redacted>"


class _NativeReadyFact(NamedTuple):
    mint: object
    owner: object
    scope: _ReadyTransitionScope

    def __repr__(self):
        return "<NativeReadyFact no-GO redacted>"


class NativeReadyTransition:
    @classmethod
    def retain(cls, receiver):
        _require(cls is NativeReadyTransition and type(receiver) is NativeReadyReceiver)
        read_scope = NativeReadyReceiver._metadata(receiver)
        b = read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0
                 and receiver._complete is True and receiver._failed is False
                 and receiver._io_unknown is False and receiver._active is False
                 and receiver._read_intent is False and receiver._pending is None
                 and receiver._transition is None and receiver._transition_snapshot is None
                 and b.producer._ready_transition is None
                 and b.producer._ready_transition_snapshot is None)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _ReadyTransitionScope(
            receiver, read_scope, receiver._completion_origin, b.producer)
        owner._attempted = owner._observe_attempted = owner._observed = False
        owner._native_attempted = owner._native_returned = False
        owner._complete = owner._failed = False
        owner._receipt = owner._receipt_snapshot = None
        receiver._transition = receiver._transition_snapshot = owner
        b.producer._ready_transition = b.producer._ready_transition_snapshot = owner
        return owner  # consumed partial owner before native callbacks

    def __repr__(self):
        return "<NativeReadyTransition original-work no-GO>"

    def _metadata(self):
        _require(type(self) is NativeReadyTransition
                 and type(self._scope) is _ReadyTransitionScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.receiver) is NativeReadyReceiver and type(s.read_scope) is _ReadyReadScope
                 and type(s.read_fact) is _ReadyReadComplete
                 and s.read_fact.mint is _READY_READ_MINT
                 and type(s.producer) is NativePhaseWorkOwner
                 and NativeReadyReceiver._metadata(s.receiver) is s.read_scope
                 and s.receiver._completion_origin is s.read_fact
                 and s.read_scope.write_scope.producer is s.producer
                 and s.receiver._transition is self and s.receiver._transition_snapshot is self
                 and s.producer._ready_transition is self
                 and s.producer._ready_transition_snapshot is self
                 and s.receiver._complete is True and s.receiver._failed is False
                 and s.receiver._io_unknown is False and s.receiver._active is False
                 and self._receipt is self._receipt_snapshot
                 and all(type(v) is bool for v in (
                     self._attempted, self._observe_attempted, self._observed,
                     self._native_attempted, self._native_returned, self._complete, self._failed)))
        if self._complete:
            _require(type(self._receipt) is _NativeReadyFact
                     and self._receipt.mint is _READY_TRANSITION_MINT
                     and self._receipt.owner is self and self._receipt.scope is s)
        else:
            _require(self._receipt is None)
        return s

    def _actor(self):
        s = NativeReadyTransition._metadata(self)
        b = s.read_scope.write_scope
        _require(asyncio.current_task() is b.allocation.task
                 and _TASK.cancelling(b.allocation.task) == 0)
        return s

    def _post_local(self, producer):
        s = NativeReadyTransition._actor(self)
        b = s.read_scope.write_scope
        _require(s.producer is producer and self._attempted is True
                 and self._observed is True and self._observe_attempted is True
                 and self._native_attempted is True and self._native_returned is True
                 and self._failed is False)
        # Actual native ledger state, not the signature/attempt flags, is mandatory.
        job = b.remote._job_origin_snapshot
        _require(type(job) is _Job)
        _require(job.remote_phase is RemotePhase.READY and job.state is State.STARTING
                 and job.go_sent is False and job.child is None
                 and b.remote._go_admission is None and b.remote._record_snapshot.child is None)
        return s

    def _post_guard(self):
        s = NativeReadyTransition._actor(self)
        b = s.read_scope.write_scope
        _require(NativePhaseWorkOwner._ready_local(s.producer)[0] is b.remote)
        _require(NativeReadyTransition._metadata(self) is s)
        RemoteOperationOwner._check(b.remote, RemotePhase.READY)
        SocketChannel._check(b.channel)
        _require(SocketChannel._qualified_clock(b.channel) is b.refs[8])
        now = NativeClockOwner.sample(b.refs[8])
        _require(NativeReadyTransition._metadata(self) is s)
        _require(NativePhaseWorkOwner._ready_local(s.producer)[0] is b.remote)
        _require(type(now) is int and 0 <= now < b.intent.end_ns
                 and NativeReadyTransition._metadata(self) is s)
        return s

    def _verified_post_ready(self):
        s = NativeReadyTransition._post_guard(self)
        fact, r = s.read_fact, s.read_scope
        checked = check_commitment(fact.raw, sender_public=r.pins[0], receiver_public=r.pins[1],
                                   expected=dict(r.expected))
        header = check_complete_frame(checked, fact.frame, binding=r.write_scope.intent.binding)
        _require(header.kind == "READY" and header.sequence == 0 and header.body_length == 0
                 and NativeReadyTransition._post_guard(self) is s)
        return s

    async def run(self):
        s = NativeReadyTransition._actor(self)
        _require(self._attempted is False and self._failed is False and self._complete is False)
        self._attempted = True
        b = s.read_scope.write_scope
        failed = cancelled = False
        try:
            _require(NativeReadyReceiver.current_ready(s.receiver) is s.read_fact
                     and NativeReadyTransition._metadata(self) is s)
            self._observe_attempted = True
            result = await ParentAuthorityAdapter._observe(
                b.remote._authority_snapshot, b.remote._record_snapshot, "PRE_GO")
            _require(result is True and NativeReadyTransition._metadata(self) is s)
            self._observed = True
            _require(NativeReadyReceiver.current_ready(s.receiver) is s.read_fact
                     and NativeReadyTransition._metadata(self) is s)
            self._native_attempted = True
            record = b.remote._record_snapshot
            JobOwner.remote_transition(record.owner, record.handle, b.remote, RemotePhase.READY)
            self._native_returned = True
            _require(NativeReadyTransition._verified_post_ready(self) is s)
            self._receipt = self._receipt_snapshot = _NativeReadyFact(
                _READY_TRANSITION_MINT, self, s)
            self._complete = True
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            if failed:
                self._failed = True  # no native rollback or retry, even after actual mutation
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_NATIVE_READY_TRANSITION_REFUSED") from None

    def current_phase(self):
        s = NativeReadyTransition._actor(self)
        _require(self._complete is True and self._failed is False)
        try:
            _require(NativeReadyTransition._verified_post_ready(self) is s)
            return self._receipt_snapshot  # READY only; never work/GO admission
        except BaseException:
            self._failed = True
            raise
