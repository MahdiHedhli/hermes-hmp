"""Unwired listener-private AT1 HostHandler and phone projection/control ports.

Only a reviewed listener binder may supply current-generation/native/gate ports.
No HTTP/CLI registration, PromptStore, push, real-session lease or native import.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import secrets
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from . import request_ctx
from .approval_test_authority import ApprovalTestAuthority, SelectedTarget
from .approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
    HostResponse,
)
from .approval_test_producer import (
    TestBeginReceipt,
    TestCleanupReceipt,
    TestControlReceipt,
    TestNotice,
    TestOutcome,
    TestStatus,
)
from .auth import AuthContext

_ID = re.compile(r'[0-9a-f]{32}\Z')
_HANDLE = re.compile(r'[0-9a-f]{64}\Z')
_COMMAND = 'Synthetic approval test — no action will run'
_DESCRIPTION = 'Choose once to acknowledge this test card, or deny. No command or tool will run.'
_TERMINAL = frozenset({TestStatus.ONCE_ACKNOWLEDGED, TestStatus.DENIED, TestStatus.CANCELLED,
                       TestStatus.EXPIRED, TestStatus.UNAVAILABLE})


@dataclass(frozen=True, slots=True, repr=False)
class TestCard:
    test_id: str
    title: Literal['Synthetic approval test'] = 'Synthetic approval test'
    message: Literal['No action will run.'] = 'No action will run.'
    choices: tuple[Literal['once'], Literal['deny']] = ('once', 'deny')


@dataclass(frozen=True, slots=True, repr=False)
class LocalOperationIdentity:
    generation: HostGeneration
    operation_id: str
    phone_test_id: str
    closure_token: object


@dataclass(slots=True, repr=False)
class _Operation:
    identity: LocalOperationIdentity
    request: HostBeginRequest
    selected: SelectedTarget | None = None
    producer: Any = None
    begin: TestBeginReceipt | None = None
    notice: TestNotice | None = None
    removed_notice: TestNotice | None = None
    fenced: bool = False
    close_requested: bool = False
    cleanup: asyncio.Task[TestCleanupReceipt | None] | None = None


@dataclass(frozen=True, slots=True, repr=False)
class _Terminal:
    identity: LocalOperationIdentity
    outcome: TestOutcome
    retain_until: float


class ApprovalTestService:
    def __init__(
        self, ctx: Any, generation: HostGeneration, *,
        generation_current: Callable[[], bool],
        approvals_gate: Callable[..., Awaitable[Any]],
        producer_factory: Callable[..., Any],
        native_current: Callable[[], bool],
    ) -> None:
        self._ctx = ctx
        self._generation = generation
        self._loop = asyncio.get_running_loop()
        self._generation_current = generation_current
        self._factory = producer_factory
        self._retired = False
        self._operation: _Operation | None = None
        self._terminal: _Terminal | None = None
        self._terminal_timer: asyncio.TimerHandle | None = None
        self._shutdown_task: asyncio.Task[None] | None = None
        self._authority = ApprovalTestAuthority(
            ctx, generation, current=self._current, approvals_gate=approvals_gate,
            native_current=native_current,
        )

    def _current(self) -> bool:
        try:
            return (
                asyncio.get_running_loop() is self._loop and not self._retired
                and self._generation_current() is True
            )
        except Exception:
            return False

    def _host_current(self) -> bool:
        try:
            return (self._current() and self._generation.pid == os.getpid()
                    and self._ctx.iid == self._generation.iid
                    and self._ctx.identity.still_current() is True)
        except Exception:
            return False

    def _owns(self, op: _Operation) -> bool:
        return self._operation is op and op.identity.generation is self._generation

    def _local(self, op: _Operation, request: Any = None, auth: AuthContext | None = None) -> bool:
        return self._owns(op) and self._authority.local_current(
            self._ctx, self._generation, op.selected, request, auth,
        )

    def _visible(self, op: _Operation) -> bool:
        return (
            self._owns(op) and not op.fenced and op.begin is not None and op.notice is not None
            and op.notice.deadline_monotonic == op.begin.deadline_monotonic
            and self._loop.time() < op.begin.deadline_monotonic
        )

    def publish(self, token: object, notice: TestNotice) -> bool:
        op = self._operation
        if (
            not self._current() or op is None or op.identity.closure_token is not token
            or op.fenced or op.selected is None or type(notice) is not TestNotice
            or op.notice is not None or op.removed_notice is not None
        ):
            return False
        target = op.selected.binding
        if (
            (
                notice.instance_id, notice.user_id, notice.profile,
                notice.session_id, notice.device_id,
            ) != (
                target.instance_id, target.user_id, target.profile,
                target.session_id, target.device_id,
            )
            or type(notice.request_id) is not str or _ID.fullmatch(notice.request_id) is None
            or notice.command != _COMMAND or notice.description != _DESCRIPTION
            or type(notice.choices) is not tuple or notice.choices != ('once', 'deny')
            or type(notice.deadline_monotonic) not in (int, float)
            or not math.isfinite(notice.deadline_monotonic)
            or notice.deadline_monotonic <= self._loop.time()
            or notice.deadline_monotonic > self._loop.time() + op.request.timeout_ms/1000
            or (op.begin is not None and notice.deadline_monotonic != op.begin.deadline_monotonic)
        ):
            return False
        op.notice = notice  # Provisional until the typed begin receipt is committed.
        return True

    def remove(self, token: object, notice: TestNotice) -> bool:
        op = self._operation
        if (
            asyncio.get_running_loop() is not self._loop or op is None
            or not self._owns(op) or op.identity.closure_token is not token
            or type(notice) is not TestNotice
        ):
            return False
        if op.notice is notice:
            op.notice = None
            op.removed_notice = notice
            return True
        if op.notice is None and op.removed_notice is notice:
            return True
        # An exact callback rejected before insertion is already absent. Bind that
        # fact to this token/notice only; it cannot remove or adopt another row.
        if op.notice is None and op.removed_notice is None and op.selected is not None:
            target = op.selected.binding
            if (
                notice.instance_id, notice.user_id, notice.profile,
                notice.session_id, notice.device_id,
            ) == (
                target.instance_id, target.user_id, target.profile,
                target.session_id, target.device_id,
            ) and type(notice.request_id) is str and _ID.fullmatch(notice.request_id):
                op.removed_notice = notice
                return True
        return False

    async def _close(self, op: _Operation) -> None:
        op.fenced = True
        if op.producer is not None and not op.close_requested:
            op.close_requested = True
            await op.producer.close()  # Reviewed producer decision has no suspension.

    def _cleanup(self, op: _Operation) -> asyncio.Task[TestCleanupReceipt | None]:
        op.fenced = True
        if op.cleanup is not None:
            return op.cleanup

        async def owned() -> TestCleanupReceipt | None:
            try:
                await self._close(op)
                if op.producer is None:
                    # No producer was constructed/admitted; authority debt is owned separately.
                    if self._owns(op):
                        self._operation = None
                    return None
                receipt = await op.producer.close_and_join()
                if (
                    type(receipt) is not TestCleanupReceipt or receipt.joined is not True
                    or type(receipt.outcome) is not TestOutcome
                    or type(receipt.outcome.status) is not TestStatus
                    or receipt.outcome.status not in _TERMINAL
                    or op.notice is not None
                ):
                    raise RuntimeError('approval test cleanup unavailable')
                if self._owns(op):
                    self._terminal = _Terminal(op.identity, receipt.outcome, self._loop.time()+60)
                    retained = self._terminal
                    if self._terminal_timer is not None:
                        self._terminal_timer.cancel()
                    def expire() -> None:
                        if self._terminal is retained:
                            self._terminal = None
                            self._terminal_timer = None
                    self._terminal_timer = self._loop.call_later(60, expire)
                    self._operation = None
                return receipt
            except BaseException:
                # Failed or observer-cancelled cleanup never releases this operation/dependencies.
                # No retry/native mutation is issued and no joined receipt is fabricated.
                await self._loop.create_future()
                return None

        op.cleanup = self._loop.create_task(owned())
        return op.cleanup

    async def _invalidate(self, op: _Operation) -> None:
        try:
            await self._close(op)
        finally:
            self._cleanup(op)

    @staticmethod
    def _unavailable() -> TestControlReceipt:
        return TestControlReceipt('unavailable', TestOutcome(TestStatus.UNAVAILABLE))

    async def _phone(
        self, request: Any, *, phone_id: str | None = None, profile: str | None = None,
    ) -> tuple[_Operation, AuthContext] | None:
        op = self._operation
        if op is None or op.selected is None:
            return None
        if not self._visible(op):
            if op.begin is not None and self._loop.time() >= op.begin.deadline_monotonic:
                await self._invalidate(op)
            return None
        # A foreign ID/profile/device is not a cancellation capability.
        if phone_id is not None and phone_id != op.identity.phone_test_id:
            return None
        if profile is not None and profile != op.selected.binding.profile:
            return None
        try:
            auth = request_ctx.bearer(request)
            if request_ctx.context(request) is not self._ctx or (
                auth.device_id != op.selected.binding.device_id
                or auth.user_id != op.selected.binding.user_id
            ):
                return None
        except Exception:
            return None
        if not await self._authority.recheck_current_target(
            self._ctx, self._generation, op.selected, request, auth,
        ):
            await self._invalidate(op)
            return None
        if not self._visible(op) or not self._local(op, request, auth):
            await self._invalidate(op)
            return None
        outcome = await op.producer.outcome(op.begin.handle, op.selected.binding.device_id)
        if type(outcome) is not TestOutcome or outcome.status is not TestStatus.PENDING:
            await self._invalidate(op)
            return None
        if not self._visible(op) or not self._local(op, request, auth):
            await self._invalidate(op)
            return None
        return op, auth

    async def phone_card(self, request: Any, profile: str | None = None) -> TestCard | None:
        found = await self._phone(request, profile=profile)
        if found is None:
            return None
        op, auth = found
        if not self._visible(op) or not self._local(op, request, auth):
            await self._invalidate(op)
            return None
        return TestCard(op.identity.phone_test_id)

    async def _control(self, request: Any, phone_id: str, choice: str | None) -> TestControlReceipt:
        if type(phone_id) is not str or _ID.fullmatch(phone_id) is None:
            return self._unavailable()
        found = await self._phone(request, phone_id=phone_id)
        if found is None:
            return self._unavailable()
        op, auth = found
        if not self._visible(op) or not self._local(op, request, auth):
            await self._invalidate(op)
            return self._unavailable()
        # No suspension after final checks and through the exact producer intent decision.
        if choice is None:
            receipt = await op.producer.cancel_test(op.begin.handle, auth.device_id)
        else:
            receipt = await op.producer.answer_test(op.begin.handle, auth.device_id, choice)
        op.fenced = True
        if (
            type(receipt) is not TestControlReceipt
            or receipt.admission not in ('accepted', 'duplicate')
            or type(receipt.outcome) is not TestOutcome
            or type(receipt.outcome.status) is not TestStatus
        ):
            await self._invalidate(op)
            return self._unavailable()
        return receipt

    async def phone_answer(
        self, request: Any, phone_test_id: str, choice: Literal['once', 'deny'],
    ) -> TestControlReceipt:
        if type(choice) is not str or choice not in ('once', 'deny'):
            return self._unavailable()
        return await self._control(request, phone_test_id, choice)

    async def phone_cancel(self, request: Any, phone_test_id: str) -> TestControlReceipt:
        return await self._control(request, phone_test_id, None)

    def _remaining(self, op: _Operation) -> int:
        if op.begin is None:
            return 0
        return min(
            op.begin.timeout_ms,
            math.ceil(max(0, op.begin.deadline_monotonic-self._loop.time())*1000),
        )

    async def responses(
        self, request: HostBeginRequest | HostOperationRequest,
    ) -> AsyncGenerator[HostResponse, None]:
        if (
            type(request) not in (HostBeginRequest, HostOperationRequest)
            or request.generation != self._generation
        ):
            yield HostResponse('unavailable')
            return
        if not self._host_current():
            if self._operation is not None:
                await self._invalidate(self._operation)
            yield HostResponse('unavailable')
            return
        if type(request) is HostOperationRequest:
            op = self._operation
            if (
                op is not None and request.operation_id == op.identity.operation_id
                and op.begin is not None
            ):
                if request.op == 'cancel':
                    await self._invalidate(op)
                    yield HostResponse('cancel_requested', request.operation_id, 'cleanup_pending')
                elif request.op == 'status':
                    observed = await op.producer.outcome(
                        op.begin.handle, op.selected.binding.device_id
                    )
                    if (
                        not self._owns(op) or not self._host_current()
                        or type(observed) is not TestOutcome
                        or type(observed.status) is not TestStatus
                    ):
                        yield HostResponse('unavailable')
                        return
                    if observed.status is not TestStatus.PENDING:
                        op.fenced = True
                    # Public producer cleanup/terminal observation is not an owned joined receipt.
                    state = 'cleanup_pending' if op.fenced else 'pending'
                    yield HostResponse(
                        'status', request.operation_id, state, remaining_ms=self._remaining(op)
                    )
                else:
                    yield HostResponse('unavailable')
                return
            terminal = self._terminal
            if terminal is not None and self._loop.time() >= terminal.retain_until:
                self._terminal = terminal = None
            if (
                terminal is not None and request.op == 'status'
                and request.operation_id == terminal.identity.operation_id
            ):
                yield HostResponse(
                    'status', request.operation_id, terminal.outcome.status.value, remaining_ms=0
                )
            else:
                yield HostResponse('unavailable')
            return
        if self._operation is not None or not self._authority.local_current(
            self._ctx, self._generation, None, None, None
        ):
            yield HostResponse('unavailable')
            return
        identity = LocalOperationIdentity(
            self._generation, secrets.token_hex(16), secrets.token_hex(16), object()
        )
        op = _Operation(identity, request)
        self._operation = op  # Reserve before any selection, producer creation or callback.
        self._terminal = None
        if self._terminal_timer is not None:
            self._terminal_timer.cancel()
            self._terminal_timer = None
        try:
            selected = await self._authority.select_current_target(
                self._ctx, self._generation, request
            )
            if selected is None or not self._owns(op):
                yield HostResponse('unavailable')
                return
            op.selected = selected
            if not self._local(op):
                yield HostResponse('unavailable')
                return
            token = identity.closure_token
            op.producer = self._factory(
                publish=lambda notice: self.publish(token, notice),
                remove=lambda notice: self.remove(token, notice),
            )
            if not self._local(op):
                yield HostResponse('unavailable')
                return
            receipt = await op.producer.begin_test(selected.binding, request.timeout_ms)
            if (
                type(receipt) is not TestBeginReceipt or type(receipt.handle) is not str
                or _HANDLE.fullmatch(receipt.handle) is None
                or type(receipt.timeout_ms) is not int or receipt.timeout_ms != request.timeout_ms
                or type(receipt.deadline_monotonic) not in (int, float)
                or not math.isfinite(receipt.deadline_monotonic)
                or receipt.deadline_monotonic <= self._loop.time()
                or receipt.deadline_monotonic > self._loop.time() + request.timeout_ms/1000
                or (
                    op.notice is not None
                    and op.notice.deadline_monotonic != receipt.deadline_monotonic
                )
                or not self._local(op)
            ):
                yield HostResponse('unavailable')
                return
            op.begin = receipt
            yield HostResponse('accepted', identity.operation_id, timeout_ms=receipt.timeout_ms)
            observed = await op.producer.wait_outcome(
                receipt.handle, selected.binding.device_id, timeout=None
            )
            if not self._owns(op) or type(observed) is not TestOutcome:
                return
            joined = await asyncio.shield(self._cleanup(op))
            if (
                type(joined) is TestCleanupReceipt and self._host_current()
                and op.identity.generation is self._generation
            ):
                yield HostResponse('completed', identity.operation_id, joined.outcome.status.value)
        finally:
            # Owner task survives generator/write/observer cancellation. The operation stays
            # reserved until its actual typed cleanup receipt, including a withheld begin handle.
            await asyncio.shield(self._cleanup(op))

    async def write_failed(self, request: HostBeginRequest) -> None:
        op = self._operation
        if op is not None and op.request is request:
            try:
                await self._close(op)
            finally:
                await asyncio.shield(self._cleanup(op))

    async def shutdown(self) -> None:
        self._retired = True
        if self._shutdown_task is None:
            async def owned() -> None:
                op = self._operation
                if op is not None:
                    await asyncio.shield(self._cleanup(op))
                await self._authority.shutdown()
            self._shutdown_task = self._loop.create_task(owned())
        await asyncio.shield(self._shutdown_task)
