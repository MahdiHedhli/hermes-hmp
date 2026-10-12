"""Inert synthetic answer coordinator; no endpoint or native binding registration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from .approval_test_producer import TestNotice, TestOutcome
from .approval_test_projection import TestProjection, settled_answer_verdict
from .prompts import PromptRow


class AnswerProducer(Protocol):
    async def answer_test(self, handle: str, authenticated_device_id: str,
                          choice: str) -> TestOutcome: ...
    async def wait_outcome(self, handle: str, authenticated_device_id: str,
                           timeout: float | None = None) -> TestOutcome: ...  # noqa: ASYNC109


class TestAnswers:
    def __init__(self, projection: TestProjection, producer: AnswerProducer, *,
                 current: Callable[[TestNotice], Awaitable[bool]],
                 handle_for: Callable[[TestNotice], str | None]) -> None:
        self._projection = projection
        self._producer = producer
        self._current = current
        self._handle_for = handle_for

    async def resolve(self, row: PromptRow, device_id: str, choice: str) -> str:
        notice = self._projection.notice_for_answer(row, device_id)
        if notice is None or choice not in ("once", "deny"):
            return "stale"
        if await self._current(notice) is not True:
            return "stale"
        # The authority await may cross withdrawal, expiry or generation retirement.
        if self._projection.notice_for_answer(row, device_id) is not notice:
            return "stale"
        handle = self._handle_for(notice)
        if type(handle) is not str or not handle:
            return "unavailable"
        await self._producer.answer_test(handle, device_id, choice)
        outcome = await self._producer.wait_outcome(handle, device_id, timeout=2)
        if await self._current(notice) is not True:
            return "unavailable"
        return settled_answer_verdict(outcome, choice)
