"""Selected-device synthetic card projection; caller admission remains external.

This module cannot start a native waiter, grant access or register an endpoint.
The listener-owned handler must revalidate current authority before calling it.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from .approval_test_producer import TestNotice
from .prompts import PromptRow, PromptStore


class TestProjection:
    def __init__(self, store: PromptStore, *, wall_clock: Callable[[], float],
                 monotonic: Callable[[], float]) -> None:
        self._store = store
        self._wall_clock = wall_clock
        self._monotonic = monotonic
        self._owned: dict[str, tuple[TestNotice, PromptRow]] = {}

    def publish(self, notice: TestNotice) -> bool:
        if type(notice) is not TestNotice or notice.request_id in self._owned:
            return False
        remaining = notice.deadline_monotonic - self._monotonic()
        if not math.isfinite(remaining) or remaining <= 0:
            return False
        row = PromptRow(
            iid=notice.instance_id, user_id=notice.user_id, profile=notice.profile,
            request_id=notice.request_id, kind="approval", surface="phone_chat",
            choices=notice.choices, command=notice.command, description=notice.description,
            target_device_id=notice.device_id,
            expires_at=math.ceil(self._wall_clock() + remaining),
        )
        self._store.put(row)
        key = (row.iid, row.user_id, row.profile, row.request_id)
        if self._store.get(key) is not row:
            return False
        self._owned[notice.request_id] = (notice, row)
        return True

    def remove(self, notice: TestNotice) -> bool:
        owned = self._owned.get(notice.request_id)
        if owned is None:
            return True
        if owned[0] is not notice:
            return False
        if not self._store.withdraw_target_row(owned[1], int(self._wall_clock())):
            return False
        del self._owned[notice.request_id]
        return True
