"""Listener-owned AT1 authority reads; no native imports or listener registration.

An observation deadline does not cancel an owned read or release its capacity.
The exact listener binder and approvals gate are production prerequisites.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import request_ctx, wire
from .approval_test_host_codec import HostBeginRequest, HostGeneration
from .approval_test_producer import TargetBinding
from .auth import AuthContext
from .contract import ApprovalTestTarget
from .reads import require_bot_authorized


# Frozen authority contract name; callers catch this exact type.
class AuthorityUnavailable(RuntimeError):  # noqa: N818
    def __init__(self) -> None:
        super().__init__('approval test unavailable')


@dataclass(frozen=True, slots=True, repr=False)
class SelectedTarget:
    binding: TargetBinding
    device_fingerprint: str
    profile_home: Path
    canonical_root: str
    canonical_tip: str


@dataclass(slots=True, repr=False)
class _ReadOwner:
    deadline: float
    abandoned: bool = False
    task: asyncio.Task[Any] | None = None


class ApprovalTestAuthority:
    """Four nonwaiting reservations, bound to one ctx/generation/owning loop."""

    def __init__(
        self, ctx: Any, generation: HostGeneration, *,
        current: Callable[[], bool],
        approvals_gate: Callable[..., Awaitable[Any]],
        native_current: Callable[[], bool],
    ) -> None:
        self._ctx = ctx
        self._generation = generation
        self._bridge = ctx.bridge
        self._store = ctx.store
        self._loop = asyncio.get_running_loop()
        self._current = current
        self._gate = approvals_gate
        self._native_current = native_current
        self._reads: list[_ReadOwner] = []
        self._retired = False

    def local_current(
        self, ctx: Any, generation: HostGeneration, selected: SelectedTarget | None,
        request: Any | None, expected_auth: AuthContext | None,
    ) -> bool:
        try:
            if (
                asyncio.get_running_loop() is not self._loop
                or ctx is not self._ctx or generation is not self._generation
                or ctx.bridge is not self._bridge or ctx.store is not self._store
                or self._retired or self._current() is not True
                or generation.pid != os.getpid() or ctx.iid != generation.iid
                or ctx.identity.still_current() is not True
                or self._native_current() is not True
                or ctx.is_approvals_available() is not True
                or ctx.direct_send_effective() is not True
            ):
                return False
            wire.require_iid(ctx.iid)
            if (request is None) != (expected_auth is None):
                return False
            if request is not None and (
                request_ctx.context(request) is not ctx
                or type(expected_auth) is not AuthContext
                or request_ctx.bearer(request) != expected_auth
            ):
                return False
            if selected is None:
                return request is None
            if type(selected) is not SelectedTarget:
                return False
            binding = selected.binding
            row = ctx.store.get_device(binding.device_id)
            if (
                row is None or row['state'] != 'ACTIVE'
                or row['device_id'] != binding.device_id
                or row['user_id'] != binding.user_id
                or row['device_fp'] != selected.device_fingerprint
                or binding.instance_id != generation.iid
                or ctx.is_approval_owner_device(binding.device_id) is not True
            ):
                return False
            return expected_auth is None or (
                expected_auth.device_id == binding.device_id
                and expected_auth.user_id == binding.user_id
            )
        except Exception:
            return False

    def _live(self, owner: _ReadOwner) -> bool:
        return not owner.abandoned and not self._retired and self._loop.time() < owner.deadline

    async def _read(self, owner: _ReadOwner, action: Callable[[], Any]) -> Any:
        """Own the actual worker through return and Thread.join; no observer owns it."""
        result: list[Any] = []
        failed: list[bool] = []

        def work() -> None:
            try:
                result.append(action())
            except BaseException:
                failed.append(True)

        worker = threading.Thread(target=work, name='hmp-at1-authority', daemon=False)
        try:
            worker.start()
        except BaseException:
            # A start implementation may raise after actually starting the worker.
            if not worker.is_alive() and worker.ident is None:
                return None
            failed.append(True)
        # Observe the actual owned worker, including start-then-raise; the real join below
        # owns release. A completion event alone cannot establish thread termination.
        while worker.is_alive():  # noqa: ASYNC110
            await asyncio.sleep(0.005)
        if worker.ident is not None:
            worker.join(timeout=0)
        if failed or not self._live(owner) or len(result) != 1:
            return None
        return result[0]

    async def _observe(
        self, operation: Callable[[_ReadOwner], Awaitable[Any]], deadline: float,
    ) -> Any:
        if self._retired or len(self._reads) >= 4:
            raise AuthorityUnavailable()
        if self._loop.time() >= deadline:
            return None
        owner = _ReadOwner(deadline)
        self._reads.append(owner)  # Same-loop reservation before any submission/await.

        async def owned() -> Any:
            try:
                return await operation(owner)
            except Exception:
                return None
            finally:
                # _read has actually joined; _gate was never observer-cancelled.
                self._reads.remove(owner)

        try:
            owner.task = self._loop.create_task(owned())
        except BaseException:
            self._reads.remove(owner)
            raise
        # Retrieve abandoned completion without logging exceptions or re-admitting it.
        owner.task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        try:
            done, _ = await asyncio.wait(
                {owner.task}, timeout=max(0, owner.deadline-self._loop.time())
            )
            if not done or not self._live(owner):
                owner.abandoned = True
                return None
            return owner.task.result()
        except asyncio.CancelledError:
            owner.abandoned = True
            raise

    def _target(self, selected: SelectedTarget) -> ApprovalTestTarget | None:
        bridge = self._ctx.bridge
        if selected.binding.profile not in bridge.served_profiles():
            return None
        require_bot_authorized(bridge, selected.binding.user_id, selected.binding.profile)
        value = bridge.approval_test_target(selected.binding.profile)
        if type(value) is not ApprovalTestTarget:
            return None
        return value

    @staticmethod
    def _same(selected: SelectedTarget, target: ApprovalTestTarget | None) -> bool:
        return target is not None and (
            target.profile_home == selected.profile_home
            and target.root_session_id == selected.canonical_root
            and target.live_tip_session_id == selected.canonical_tip
            and selected.binding.session_id == target.live_tip_session_id
        )

    async def select_current_target(
        self, ctx: Any, generation: HostGeneration, request: HostBeginRequest,
    ) -> SelectedTarget | None:
        deadline = self._loop.time() + 2.0
        if type(request) is not HostBeginRequest or request.generation != generation:
            return None
        if not self.local_current(ctx, generation, None, None, None):
            return None
        try:
            row = ctx.store.get_device(request.device_id)
            if row is None or row['state'] != 'ACTIVE':
                return None
            user, fingerprint = row['user_id'], row['device_fp']
            if type(user) is not str or not user or type(fingerprint) is not str or not fingerprint:
                return None
            binding = TargetBinding(
                ctx.iid, user, request.profile, request.session_id, request.device_id
            )
            initial = SelectedTarget(binding, fingerprint, Path('/'), '', request.session_id)
        except Exception:
            return None
        if not self.local_current(ctx, generation, initial, None, None):
            return None

        async def select(owner: _ReadOwner) -> SelectedTarget | None:
            target = await self._read(owner, lambda: self._target(initial))
            if (
                not self._live(owner) or type(target) is not ApprovalTestTarget
                or target.live_tip_session_id != request.session_id
                or not self.local_current(ctx, generation, initial, None, None)
            ):
                return None
            selected = SelectedTarget(binding, fingerprint, target.profile_home,
                                      target.root_session_id, target.live_tip_session_id)
            await self._gate(ctx, request.profile, member='bot_chat')
            if not self._live(owner) or not self.local_current(
                ctx, generation, selected, None, None
            ):
                return None
            final = await self._read(owner, lambda: self._target(selected))
            if self._live(owner) and self._same(selected, final) and self.local_current(
                ctx, generation, selected, None, None
            ):
                return selected
            return None

        selected = await self._observe(select, deadline)
        if type(selected) is SelectedTarget and self.local_current(
            ctx, generation, selected, None, None
        ):
            return selected
        return None

    async def recheck_current_target(
        self, ctx: Any, generation: HostGeneration, selected: SelectedTarget,
        request: Any | None, expected_auth: AuthContext | None,
    ) -> bool:
        deadline = self._loop.time() + 2.0
        if not self.local_current(ctx, generation, selected, request, expected_auth):
            return False

        async def check(owner: _ReadOwner) -> bool:
            first = await self._read(owner, lambda: self._target(selected))
            if not self._live(owner) or not self._same(selected, first) or not self.local_current(
                ctx, generation, selected, request, expected_auth
            ):
                return False
            await self._gate(ctx, selected.binding.profile, member='bot_chat')
            if not self._live(owner) or not self.local_current(
                ctx, generation, selected, request, expected_auth
            ):
                return False
            final = await self._read(owner, lambda: self._target(selected))
            return self._live(owner) and self._same(selected, final) and self.local_current(
                ctx, generation, selected, request, expected_auth
            )

        result = await self._observe(check, deadline)
        return result is True and self.local_current(
            ctx, generation, selected, request, expected_auth
        )

    async def shutdown(self) -> None:
        self._retired = True
        # Shielded observation: request cancellation cannot cancel any owned work.
        for owner in tuple(self._reads):
            owner.abandoned = True
            if owner.task is not None:
                await asyncio.shield(owner.task)
