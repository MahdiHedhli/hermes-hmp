"""Explicit listener-owned AT1 composition; inert until a caller constructs it."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from .approval_test_answers import TestAnswers
from .approval_test_host_codec import HostBeginRequest, HostGeneration
from .approval_test_host_transport import HostIpcEndpoint
from .approval_test_operator import OperatorHandler
from .approval_test_producer import (
    ApprovalTestProducer,
    NativeApprovalBindings,
    TargetBinding,
    TestStatus,
)
from .approval_test_projection import TestProjection
from .prompts import PromptStore


class TestService:
    def __init__(
        self,
        generation: HostGeneration,
        native: NativeApprovalBindings,
        store: PromptStore,
        *,
        wall_clock: Callable[[], float],
        admit: Callable[[HostBeginRequest], Awaitable[TargetBinding | None]],
        current: Callable[[TargetBinding], Awaitable[bool]],
    ) -> None:
        self._generation = generation
        self._endpoint: HostIpcEndpoint | None = None
        loop = asyncio.get_running_loop()
        self.projection = TestProjection(store, wall_clock=wall_clock, monotonic=loop.time)
        self.producer = ApprovalTestProducer(
            loop=loop,
            native=native,
            publish=self.projection.publish,
            remove=self.projection.remove,
        )
        async def generation_admit(request):
            if type(request) is not HostBeginRequest or request.generation != self._generation:
                return None
            target = await admit(request)
            if target is None or target.instance_id != self._generation.iid:
                return None
            if (target.device_id, target.profile, target.session_id) != (
                request.device_id, request.profile, request.session_id,
            ):
                return None
            return target

        self.operator = OperatorHandler(
            generation,
            self.producer,
            admit=generation_admit,
            current=current,
            owns_notice=self.projection.owns_notice,
        )

        async def notice_current(notice):
            return await current(
                TargetBinding(
                    notice.instance_id,
                    notice.user_id,
                    notice.profile,
                    notice.session_id,
                    notice.device_id,
                )
            )

        self.answers = TestAnswers(
            self.projection,
            self.producer,
            current=notice_current,
            handle_for=self.operator.handle_for_notice,
        )

    def start(self, listener_record: Path) -> None:
        if self._endpoint is not None:
            raise RuntimeError("approval test unavailable")
        endpoint = HostIpcEndpoint(listener_record, self._generation, self.operator)
        self._endpoint = endpoint
        endpoint.start()

    async def close(self) -> None:
        endpoint = self._endpoint
        if endpoint is not None and await endpoint.close() is not True:
            raise RuntimeError("approval test cleanup unavailable")
        await self.shutdown()

    async def shutdown(self) -> None:
        await self.operator.shutdown()
        outcome = await self.producer.close()
        if outcome.status in (
            TestStatus.PENDING,
            TestStatus.CLEANUP_PENDING,
            TestStatus.UNAVAILABLE,
        ):
            raise RuntimeError("approval test cleanup unavailable")
