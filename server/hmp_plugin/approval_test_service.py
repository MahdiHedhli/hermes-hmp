"""Explicit listener-owned AT1 composition; inert until a caller constructs it."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .approval_test_answers import TestAnswers
from .approval_test_host_codec import HostBeginRequest, HostGeneration
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
        loop = asyncio.get_running_loop()
        self.projection = TestProjection(store, wall_clock=wall_clock, monotonic=loop.time)
        self.producer = ApprovalTestProducer(
            loop=loop,
            native=native,
            publish=self.projection.publish,
            remove=self.projection.remove,
        )
        self.operator = OperatorHandler(
            generation,
            self.producer,
            admit=admit,
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

    async def shutdown(self) -> None:
        await self.operator.shutdown()
        outcome = await self.producer.close()
        if outcome.status in (
            TestStatus.PENDING,
            TestStatus.CLEANUP_PENDING,
            TestStatus.UNAVAILABLE,
        ):
            raise RuntimeError("approval test cleanup unavailable")
