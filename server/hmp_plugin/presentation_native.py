"""Owned native authorization observations for desktop presentation.

Not registered with routes. Each observation authenticates original headers and
checks native bot authority before resolving its home. A deadline/cancelled
observer never releases an actual worker; drain requires its real termination.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .auth import Authenticator
from .presentation_authority import NativeObservation
from .presentation_jobs import MAX_PROCESSES
from .reads import require_bot_authorized


@dataclass
class _ReadOwner:
    task: asyncio.Task[Any] | None = None
    worker: threading.Thread | None = None
    started: bool = False
    joined: bool = False
    uncertain: bool = False


class PresentationNativeService:
    def __init__(
        self,
        ctx: Any,
        *,
        current: Callable[[], bool],
        native_current: Callable[[], bool],
        native_owner: object,
    ):
        if native_owner is None:
            raise ValueError("native owner required")
        self._native_owner = native_owner
        self._ctx = ctx
        self._loop = asyncio.get_running_loop()
        self._current = current
        self._native_current = native_current
        self._bridge = ctx.bridge
        self._store = ctx.store
        self._identity = ctx.identity
        self._reads: dict[object, _ReadOwner] = {}
        self._retired = False

    def _local(self, record: Any) -> bool:
        try:
            return (
                not self._retired
                and asyncio.get_running_loop() is self._loop
                and self._current() is True
                and self._native_current() is True
                and record.native_owner is self._native_owner
                and record.listener is self._ctx
                and record.store is self._store is self._ctx.store
                and record.bridge is self._bridge is self._ctx.bridge
                and record.identity is self._identity is self._ctx.identity
                and self._identity.still_current() is True
                and record.fence.current is True
                and record.fence.epoch == record.fence_epoch == record.lease.epoch
                and record.lease.iid == self._ctx.iid
                and record.headers is not None
                and self._loop.time() < record.deadline
            )
        except Exception:
            return False

    def _authenticate(self, record: Any) -> bool:
        who = Authenticator(self._store, self._ctx.iid, self._ctx.now).authenticate(
            record.headers.authorization, record.headers.instance
        )
        return (who.device_id, who.user_id, who.family_id) == (
            record.lease.device_id,
            record.lease.user_id,
            record.lease.family_id,
        )

    async def _owned_read(self, record: Any, owner: _ReadOwner) -> str | None:
        results: list[str] = []
        failures: list[bool] = []

        def work() -> None:
            try:
                require_bot_authorized(self._bridge, record.lease.user_id, record.lease.profile)
                # Existing version-bound bridge resolves the gateway's routing home;
                # the request supplies no path and no profile configuration is read.
                home = self._bridge._profile_home(record.lease.profile)
                if not isinstance(home, Path) or not home.is_absolute():
                    raise ValueError("invalid native home")
                require_bot_authorized(self._bridge, record.lease.user_id, record.lease.profile)
                if self._bridge._profile_home(record.lease.profile) != home:
                    raise ValueError("native routing changed")
                results.append(str(home))
            except BaseException:
                failures.append(True)

        worker = threading.Thread(target=work, name="hmp-bi1-authority", daemon=False)
        owner.worker = worker
        try:
            worker.start()
            owner.started = True
        except BaseException:
            # An exception cannot prove no delayed launch. Retain the owner and
            # refuse drain; do not reinterpret task completion as worker closure.
            owner.uncertain = True
            return None
        await self._join_worker(owner)
        if failures or len(results) != 1:
            return None
        return results[0]

    async def observe(self, record: Any, phase: str) -> NativeObservation | None:
        if phase not in {"INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"} or not self._local(record):
            return None
        if record.operation in self._reads or len(self._reads) >= MAX_PROCESSES:
            return None
        try:
            if not self._authenticate(record):
                return None
        except Exception:
            return None
        owner = _ReadOwner()
        self._reads[record.operation] = owner
        task = self._loop.create_task(self._owned_read(record, owner))
        owner.task = task
        try:
            home = await asyncio.shield(task)
            # The actual native read has returned and its thread has joined.
            if home is None or not self._local(record) or not self._authenticate(record):
                return None
            lease = record.lease
            return NativeObservation(
                lease.iid,
                lease.device_id,
                lease.user_id,
                lease.family_id,
                lease.profile,
                home,
                self._ctx,
                self._store,
                self._bridge,
                self._identity,
                record.native_owner,
                True,
            )
        finally:
            if owner.joined and not owner.uncertain:
                self._reads.pop(record.operation, None)

    async def _join_worker(self, owner: _ReadOwner) -> bool:
        if owner.uncertain:
            return False
        worker = owner.worker
        if worker is None or not owner.started:
            return False
        # Completion events do not establish Thread termination; join owns release.
        while worker.is_alive():  # noqa: ASYNC110
            await asyncio.sleep(0.005)
        worker.join(timeout=0)
        if worker.is_alive():
            return False
        owner.joined = True
        return True

    async def drain(self, record: Any) -> bool:
        return await self._drain_operation(record.operation)

    async def _drain_operation(self, operation: object) -> bool:
        owner = self._reads.get(operation)
        if owner is None:
            return True
        task = owner.task
        if task is None:
            return False
        if not task.done():
            await asyncio.shield(task)
        # A cancelled owned task is not a joined worker. The retained ledger
        # provides actual thread custody independently of asyncio task state.
        if not await self._join_worker(owner):
            return False
        self._reads.pop(operation, None)
        return True

    def retire(self) -> None:
        # Existing workers retain ownership until drain, even after retirement.
        self._retired = True

    async def close_and_join(self) -> bool:
        self.retire()
        pending = tuple(self._reads)
        for operation in pending:
            if not await self._drain_operation(operation):
                return False
        return not self._reads
