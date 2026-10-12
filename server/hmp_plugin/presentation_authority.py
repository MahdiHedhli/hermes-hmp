"""Parent-only BI1 authority custody and JobOwner ordering adapter.

No route imports this module. The real native-owned read-only service is unbound. A
CapturedLease, native-binding string, token digest, header pair or child frame is never
an authorization grant. The service must reauthenticate the original headers and full
native policy at every phase before this adapter may be bound to a route.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

from .presentation_jobs import (
    JOB_SECONDS,
    MAX_PROCESSES,
    MAX_WAITING,
    AuthorityPort,
    CapturedLease,
    FrameError,
    JobHandle,
    JobOwner,
    State,
)

MAX_RECORDS = MAX_WAITING + MAX_PROCESSES
_HEADER_CEILING = 8192
_PHASES = frozenset({"INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"})
_HEADER_MINT = object()


def _cancel_requested() -> bool:
    """Treat a swallowed task cancellation as unresolved native ownership."""
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return False
    return task is not None and task.cancelling() > 0


class AuthorityRefusalError(Exception):
    """A closed parent-side refusal with no credential or native exception text."""

    def __init__(self) -> None:
        super().__init__("BI1_AUTHORITY_REFUSED")


@dataclass(frozen=True, repr=False, init=False)
class OriginalHeaders:
    """Exact strings returned by existing request_ctx.single_header, parent custody only."""

    __slots__ = ("_mint", "authorization", "instance")

    def __init__(self, authorization: str, instance: str, *, _mint: object = None) -> None:
        if (
            _mint is not _HEADER_MINT
            or type(authorization) is not str
            or type(instance) is not str
            or not authorization
            or not instance
            or not instance.isascii()
            or len(authorization) > _HEADER_CEILING
            or len(instance) > 256
            or any(c in authorization for c in "\r\n\x00")
            or any(c in instance for c in "\r\n\x00")
        ):
            raise AuthorityRefusalError
        object.__setattr__(self, "authorization", authorization)
        object.__setattr__(self, "instance", instance)
        object.__setattr__(self, "_mint", _HEADER_MINT)

    @classmethod
    def from_request(cls, request: object) -> OriginalHeaders:
        # Keep duplicate/missing-header semantics in the existing HMP parser.
        from .auth import bearer_token
        from .request_ctx import single_header

        authorization = single_header(request, "Authorization")
        instance = single_header(request, "HMP-Instance")
        if bearer_token(authorization) is None:
            raise AuthorityRefusalError
        return cls(authorization, instance, _mint=_HEADER_MINT)

    def __repr__(self) -> str:
        return "<OriginalHeaders redacted>"


class OpaqueOperation:
    """Object identity is the lookup key. Its printable value conveys no authority."""

    __slots__ = ()


class ListenerFence:
    """An explicit local listener-lifetime fence; not native policy authority."""

    __slots__ = ("_epoch", "_retired")

    def __init__(self, epoch: int) -> None:
        if type(epoch) is not int or epoch < 1:
            raise AuthorityRefusalError
        self._epoch = epoch
        self._retired = False

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def current(self) -> bool:
        return not self._retired

    def retire(self) -> None:
        self._retired = True


@dataclass(frozen=True, repr=False)
class NativeObservation:
    """Returned only by a future owned service after its complete native checks."""

    iid: str
    device_id: str
    user_id: str
    family_id: str
    profile: str
    native_home: str
    listener: object
    store: object
    bridge: object
    identity: object
    native_owner: object
    allowed: bool


class NativeReadOnlyService(Protocol):
    async def observe(self, record: _Record, phase: str) -> NativeObservation | None: ...

    async def drain(self, record: _Record) -> bool: ...


class UnboundNativeReadOnlyService:
    async def observe(self, record: _Record, phase: str) -> None:
        del record, phase
        return None

    async def drain(self, record: _Record) -> bool:
        del record
        # This port dispatched no native work, so refusal has a known closed owner.
        return True


@dataclass(repr=False)
class _Permit:
    operation: OpaqueOperation
    handle: JobHandle
    child: object
    challenge: str
    phase: str
    epoch: int
    used: bool = False


@dataclass(frozen=True, repr=False)
class _NativeClaim:
    phase: str


@dataclass(repr=False)
class _Record:
    operation: OpaqueOperation
    handle: JobHandle
    lease: CapturedLease
    headers: OriginalHeaders | None
    listener: object
    fence: ListenerFence
    fence_epoch: int
    store: object
    bridge: object
    identity: object
    native_owner: object
    owner: JobOwner
    deadline: float
    child: object | None = None
    initial_home: str | None = None
    initial_complete: bool = False
    native_drained: bool = False
    permit: _Permit | None = None
    native_claim: _NativeClaim | None = None
    policy_work: object | None = None


class _OwnerAuthority(AuthorityPort):
    def __init__(self, adapter: ParentAuthorityAdapter) -> None:
        self.adapter = adapter

    async def reauthenticate(self, lease: CapturedLease, stage: str) -> bool:
        record = self.adapter._by_lease.get(id(lease))
        if record is None or record.lease is not lease:
            return False
        if stage == "BEFORE":
            return await self.adapter._observe(record, "BEFORE")
        if stage == "AFTER":
            if not await self.adapter._observe(record, "PRE_EMIT"):
                return False
            if record.child is None:
                return False
            record.permit = _Permit(
                record.operation,
                record.handle,
                record.child,
                record.owner.challenge(record.handle),
                "PRE_EMIT",
                record.fence_epoch,
            )
            return True
        return False


class ParentAuthorityAdapter:
    """Wrap existing JobOwner; no second queue, child supervisor or native algorithm."""

    def __init__(
        self,
        iid: str,
        *,
        service: NativeReadOnlyService | None = None,
        clock: Callable[[], float] = time.monotonic,
        challenge_source: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock
        self._service = service if service is not None else UnboundNativeReadOnlyService()
        self._by_operation: dict[OpaqueOperation, _Record] = {}
        self._by_lease: dict[int, _Record] = {}
        self._disabled = False
        authority = _OwnerAuthority(self)
        if challenge_source is None:
            self.owner = JobOwner(iid, authority=authority, clock=clock)
        else:
            self.owner = JobOwner(
                iid, authority=authority, clock=clock, challenge_source=challenge_source
            )

    @property
    def disabled(self) -> bool:
        return self._disabled or self.owner.disabled

    def _record(self, operation: OpaqueOperation) -> _Record:
        if type(operation) is not OpaqueOperation:
            raise AuthorityRefusalError
        record = self._by_operation.get(operation)
        if record is None or record.operation is not operation:
            raise AuthorityRefusalError
        return record

    def reserve(
        self,
        lease: CapturedLease,
        operation: str,
        headers: OriginalHeaders,
        *,
        listener: object,
        fence: ListenerFence,
        store: object,
        bridge: object,
        identity: object,
        native_owner: object,
    ) -> OpaqueOperation:
        """Reserve JobOwner's own slot before retaining the exact original headers."""
        if (
            self.disabled
            or type(lease) is not CapturedLease
            or type(headers) is not OriginalHeaders
            or headers._mint is not _HEADER_MINT
            or type(fence) is not ListenerFence
            or not fence.current
            or fence.epoch != lease.epoch
            or headers.instance != lease.iid
            or any(x is None for x in (listener, store, bridge, identity, native_owner))
            or len(self._by_operation) >= MAX_RECORDS
            or id(lease) in self._by_lease
        ):
            raise AuthorityRefusalError
        try:
            now = self._clock()
        except Exception:
            raise AuthorityRefusalError from None
        if (
            type(now) not in (float, int)
            or not 0 <= now < float("inf")
            or not now + JOB_SECONDS < float("inf")
        ):
            raise AuthorityRefusalError
        try:
            handle = self.owner.queue(lease, operation)
        except FrameError:
            raise AuthorityRefusalError from None
        opaque = OpaqueOperation()
        record = _Record(
            opaque,
            handle,
            lease,
            headers,
            listener,
            fence,
            fence.epoch,
            store,
            bridge,
            identity,
            native_owner,
            self.owner,
            now + JOB_SECONDS,
        )
        self._by_operation[opaque] = record
        self._by_lease[id(lease)] = record
        return opaque

    def handle(self, operation: OpaqueOperation) -> JobHandle:
        return self._record(operation).handle

    def _current(self, record: _Record) -> bool:
        if self.disabled or self._by_operation.get(record.operation) is not record:
            return False
        if not record.fence.current or record.fence.epoch != record.fence_epoch:
            return False
        if record.owner.epoch != record.lease.epoch:
            return False
        try:
            now = self._clock()
        except Exception:
            return False
        # The clock is foreign code: revalidate local authority after it returns.
        return (
            type(now) in (float, int)
            and 0 <= now < record.deadline
            and not self.disabled
            and self._by_operation.get(record.operation) is record
            and record.fence.current
            and record.fence.epoch == record.fence_epoch
            and record.owner.epoch == record.lease.epoch
            and not record.owner.disabled
        )

    def _observation_matches(self, record: _Record, value: object) -> bool:
        if type(value) is not NativeObservation or value.allowed is not True:
            return False
        lease = record.lease
        if (
            type(value.iid) is not str
            or type(value.device_id) is not str
            or type(value.user_id) is not str
            or type(value.family_id) is not str
            or type(value.profile) is not str
            or value.iid != lease.iid
            or value.device_id != lease.device_id
            or value.user_id != lease.user_id
            or value.family_id != lease.family_id
            or value.profile != lease.profile
            or type(value.native_home) is not str
            or not value.native_home
            or value.listener is not record.listener
            or value.store is not record.store
            or value.bridge is not record.bridge
            or value.identity is not record.identity
            or value.native_owner is not record.native_owner
        ):
            return False
        return record.initial_home is None or value.native_home == record.initial_home

    def _claim_native(self, record: _Record, phase: str) -> _NativeClaim | None:
        # Claim synchronously, before service code can suspend or dispatch work.
        if record.native_claim is not None:
            self._unknown(record)
            return None
        claim = _NativeClaim(phase)
        record.native_claim = claim
        return claim

    def _phase_state(self, record: _Record, phase: str) -> bool:
        required = {
            "INITIAL": State.QUEUED,
            "BEFORE": State.QUEUED,
            "PRE_GO": State.STARTING,
            "PRE_EMIT": State.COMPLETE,
        }.get(phase)
        if required is None:
            return False
        try:
            return record.owner.inspect(record.handle)[0] is required
        except FrameError:
            return False

    async def _observe(self, record: _Record, phase: str) -> bool:
        if record.native_claim is not None:
            self._unknown(record)
            return False
        if phase not in _PHASES or not self._current(record):
            return False
        if phase != "INITIAL" and not record.initial_complete:
            return False
        if not self._phase_state(record, phase):
            return False
        claim = self._claim_native(record, phase)
        if claim is None:
            return False
        try:
            observed = await self._service.observe(record, phase)
        except Exception:
            self._unknown(record)
            return False
        except BaseException:
            self._unknown(record)
            raise
        if record.native_claim is not claim or self.disabled or _cancel_requested():
            self._unknown(record)
            return False
        # The service returned normally; this exact native invocation is known closed.
        record.native_claim = None
        if (
            not self._current(record)
            or not self._phase_state(record, phase)
            or not self._observation_matches(record, observed)
        ):
            return False
        if phase == "INITIAL":
            record.initial_home = observed.native_home
            record.initial_complete = True
        return True

    def _unknown(self, record: _Record) -> None:
        self._disabled = True
        record.permit = None
        record.fence.retire()
        with suppress(FrameError):
            record.owner.unknown(record.handle)

    async def initialize(self, operation: OpaqueOperation) -> bool:
        record = self._record(operation)
        if record.owner.inspect(record.handle)[0] is not State.QUEUED:
            raise AuthorityRefusalError
        try:
            if not await self._observe(record, "INITIAL"):
                record.owner.cancel(record.handle)
                return False
            await record.owner.authorize(record.handle)
        except BaseException:
            self._unknown(record)
            raise
        return record.owner.inspect(record.handle)[0] is State.AUTHORIZED and self._current(record)

    def start(self, operation: OpaqueOperation) -> None:
        record = self._record(operation)
        if not self._current(record):
            record.owner.cancel(record.handle)
            return
        record.owner.start(record.handle)

    def bind_child(self, operation: OpaqueOperation, child: object) -> None:
        record = self._record(operation)
        record.owner.bind_child(record.handle, child)
        if record.owner.inspect(record.handle)[0] in (State.STARTING, State.DRAINING):
            record.child = child

    def _consume(self, record: _Record, permit: _Permit, phase: str) -> bool:
        if (
            record.permit is not permit
            or permit.used
            or permit.operation is not record.operation
            or permit.handle is not record.handle
            or permit.child is not record.child
            or permit.phase != phase
            or permit.epoch != record.fence_epoch
            or permit.challenge != record.owner.challenge(record.handle)
            or not self._current(record)
        ):
            return False
        permit.used = True
        record.permit = None
        return True

    async def go_inline(
        self,
        operation: OpaqueOperation,
        child: object,
        send_go: Callable[[JobHandle, object, str], None],
    ) -> bool:
        record = self._record(operation)
        if (
            child is None
            or child is not record.child
            or record.owner.inspect(record.handle)[0] is not State.STARTING
            or not self._current(record)
            or not record.initial_complete
        ):
            record.owner.cancel(record.handle)
            return False
        if not await self._observe(record, "PRE_GO"):
            record.owner.cancel(record.handle)
            return False
        if (
            child is not record.child
            or record.owner.inspect(record.handle)[0] is not State.STARTING
            or not self._current(record)
        ):
            record.owner.cancel(record.handle)
            return False
        permit = _Permit(
            operation,
            record.handle,
            child,
            record.owner.challenge(record.handle),
            "PRE_GO",
            record.fence_epoch,
        )
        record.permit = permit
        if not self._consume(record, permit, "PRE_GO"):
            record.owner.cancel(record.handle)
            return False
        if inspect.iscoroutinefunction(send_go):
            self._unknown(record)
            return False
        record.owner.go(record.handle, child, permit.challenge)
        if record.owner.inspect(record.handle)[0] is not State.RUNNING:
            self._unknown(record)
            return False
        try:
            result = send_go(record.handle, child, permit.challenge)
        except Exception:
            self._unknown(record)
            return False
        if result is not None:
            if inspect.iscoroutine(result):
                result.close()
            self._unknown(record)
            return False
        return True

    async def reauthorize(self, operation: OpaqueOperation) -> bool:
        record = self._record(operation)
        if record.owner.inspect(record.handle)[0] is not State.COMPLETE:
            return False
        await record.owner.reauthorize(record.handle)
        state = record.owner.inspect(record.handle)[0]
        if state is not State.REAUTHORIZED or record.permit is None or not self._current(record):
            record.permit = None
            return False
        return True

    def emit_inline(
        self,
        operation: OpaqueOperation,
        sink: Callable[[dict[str, object], bytes], None],
    ) -> bool:
        record = self._record(operation)
        permit = record.permit
        if (
            permit is None
            or permit.phase != "PRE_EMIT"
            or record.owner.inspect(record.handle)[0] is not State.REAUTHORIZED
        ):
            return False

        # JobOwner invokes this memory-only predicate immediately before its synchronous sink.
        def still_current(lease: CapturedLease) -> bool:
            return lease is record.lease and self._consume(record, permit, "PRE_EMIT")

        record.owner.emit_inline(record.handle, still_current, sink)
        return record.owner.inspect(record.handle)[0] is State.EMIT

    def cancel(self, operation: OpaqueOperation) -> None:
        record = self._record(operation)
        if record.native_claim is not None:
            # Native completion is not established by cancellation of the awaiter.
            self._unknown(record)
            return
        record.fence.retire()
        record.permit = None
        record.owner.cancel(record.handle)

    async def retire_known(self, operation: OpaqueOperation) -> bool:
        """Release credentials only after both owner planes report known closure."""
        record = self._record(operation)
        try:
            state, _, credit_released = record.owner.inspect(record.handle)
        except FrameError:
            self._unknown(record)
            return False
        if state not in (State.REFUSED, State.EMIT) or not credit_released:
            return False
        claim = self._claim_native(record, "DRAIN")
        if claim is None:
            return False
        try:
            drained = await self._service.drain(record)
        except Exception:
            self._unknown(record)
            return False
        except BaseException:
            self._unknown(record)
            raise
        if record.native_claim is not claim or self.disabled or _cancel_requested():
            self._unknown(record)
            return False
        if drained is not True:
            self._unknown(record)
            return False
        record.native_claim = None
        try:
            state, _, credit_released = record.owner.inspect(record.handle)
        except FrameError:
            self._unknown(record)
            return False
        if state not in (State.REFUSED, State.EMIT) or not credit_released:
            self._unknown(record)
            return False
        record.native_drained = True
        record.headers = None  # drop immutable string references after both owners close
        self._by_operation.pop(operation)
        self._by_lease.pop(id(record.lease), None)
        return True
