"""Listener-owned operator lifecycle; construction confers no admission authority."""
from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncGenerator, Awaitable, Callable

from .approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
    HostResponse,
)
from .approval_test_producer import ApprovalTestProducer, TargetBinding, TestStatus


class OperatorHandler:
    def __init__(self, generation: HostGeneration, producer: ApprovalTestProducer, *,
                 admit: Callable[[HostBeginRequest], Awaitable[TargetBinding | None]]) -> None:
        self._generation = generation
        self._producer = producer
        self._admit = admit
        self._active: tuple[HostBeginRequest, str, TargetBinding] | None = None
        self._operation_id: str | None = None
        self._deadline = 0.0
        self._admission_done = asyncio.Event()
        self._admission_done.set()
        self._admitting = False
        self._closing = False
        self._shutdown_task: asyncio.Task[None] | None = None

    async def _join(self, handle: str, target: TargetBinding) -> None:
        while True:
            outcome = await self._producer.wait_outcome(handle, target.device_id, timeout=1)
            if outcome.status not in (TestStatus.PENDING, TestStatus.CLEANUP_PENDING):
                return

    async def responses(self, request) -> AsyncGenerator[HostResponse, None]:
        if type(request) is HostOperationRequest:
            active = self._active
            if (self._closing or request.generation != self._generation or active is None
                    or request.operation_id != self._operation_id):
                yield HostResponse("unavailable")
                return
            if request.op == "cancel":
                outcome = await self._producer.cancel_test(active[1], active[2].device_id)
                yield HostResponse("cancel_requested", operation_id=request.operation_id,
                                   state=outcome.status.value)
            else:
                outcome = await self._producer.outcome(active[1], active[2].device_id)
                remaining = max(0, min(60000, int(
                    (self._deadline - asyncio.get_running_loop().time()) * 1000)))
                yield HostResponse("status", operation_id=request.operation_id,
                                   state=outcome.status.value, remaining_ms=remaining)
            return
        if (self._closing or type(request) is not HostBeginRequest
                or request.generation != self._generation or self._active is not None
                or self._admitting):
            yield HostResponse("unavailable")
            return
        self._admitting = True
        self._admission_done.clear()
        handle = None
        target = None
        try:
            try:
                target = await self._admit(request)
                if target is not None and not self._closing and self._active is None:
                    handle = await self._producer.begin_test(target, request.timeout_ms)
            except Exception:
                handle = None
        finally:
            self._admitting = False
            self._admission_done.set()
        if target is None or type(handle) is not str:
            yield HostResponse("unavailable")
            return
        self._active = (request, handle, target)
        operation_id = secrets.token_hex(16)
        self._operation_id = operation_id
        self._deadline = asyncio.get_running_loop().time() + request.timeout_ms / 1000
        try:
            if self._closing:
                yield HostResponse("unavailable")
                return
            yield HostResponse("accepted", operation_id=operation_id, timeout_ms=request.timeout_ms)
            await self._join(handle, target)
            outcome = await self._producer.outcome(handle, target.device_id)
            yield HostResponse("completed", operation_id=operation_id, state=outcome.status.value)
        finally:
            await self._producer.cancel_test(handle, target.device_id)
            cleanup = asyncio.create_task(self._join(handle, target))
            cancelled = False
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    cancelled = True
            cleanup.result()
            self._active = None
            self._operation_id = None
            if cancelled:
                raise asyncio.CancelledError

    async def write_failed(self, request: HostBeginRequest) -> None:
        active = self._active
        if active is not None and active[0] is request:
            await self._producer.cancel_test(active[1], active[2].device_id)

    async def _shutdown_owned(self) -> None:
        await self._admission_done.wait()
        active = self._active
        if active is not None:
            await self._producer.cancel_test(active[1], active[2].device_id)
            await self._join(active[1], active[2])

    async def shutdown(self) -> None:
        self._closing = True
        if self._shutdown_task is None:
            self._shutdown_task = asyncio.create_task(self._shutdown_owned())
        cancelled = False
        while not self._shutdown_task.done():
            try:
                await asyncio.shield(self._shutdown_task)
            except asyncio.CancelledError:
                cancelled = True
        self._shutdown_task.result()
        if cancelled:
            raise asyncio.CancelledError
