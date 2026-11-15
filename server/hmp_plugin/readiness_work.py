"""Owned HTTP read activities; timeout is not worker retirement.

No wire/permission authority. Integration must keep post-worker Store users inside
activity(), stop admission, and await drain before closing original dependencies.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import contextvars
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from .contract import HmpError
from .readiness import ReadinessUnavailableError

_CALLER: contextvars.ContextVar[Any] = contextvars.ContextVar("hmp_read_caller", default=None)
_WORKER: contextvars.ContextVar[Any] = contextvars.ContextVar("hmp_read_worker", default=None)


class ReadActivityUnavailableError(Exception):
    def __init__(self) -> None:
        super().__init__("readiness activity unavailable")


@dataclass(eq=False)
class _Activity:
    caller: Any
    bridge: Any
    generation: Any
    future: concurrent.futures.Future[Any] | None = None
    caller_done: bool = False
    worker_done: bool = False
    unknown: bool = False
    release_attempted: bool = False


class ReadinessReadService:
    """One exact context/budget/Store owner, never a replacement on that context."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx
        self._store = ctx.store
        self._identity = ctx.identity
        self._budget = ctx.read_worker_budget
        self._bridge = ctx.bridge
        self._generation = ctx.readiness_generation
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="hmp-readiness",
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._activities: set[_Activity] = set()
        self._closed = False
        self._shutdown_attempted = False
        self._shutdown_failed = False
        self._drained = asyncio.Event()
        self._marshal_failed = threading.Event()
        self._source_lost = threading.Event()

    def is_for(self, ctx: Any) -> bool:
        if ctx is not self._ctx:
            return False
        bound = (ctx.store is self._store and ctx.identity is self._identity
                 and ctx.read_worker_budget is self._budget and ctx.bridge is self._bridge
                 and ctx.readiness_generation == self._generation)
        if not bound:
            self._source_lost.set()
        return (bound and not self._closed and not self._marshal_failed.is_set()
                and not self._source_lost.is_set())

    def _bind_loop(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        if self._loop is not loop:
            raise ReadActivityUnavailableError()
        return loop

    def _current(self, op: _Activity) -> bool:
        bound = (self._ctx.store is self._store and self._ctx.identity is self._identity
                 and self._ctx.read_worker_budget is self._budget
                 and self._ctx.bridge is self._bridge and op.bridge is self._bridge
                 and self._ctx.readiness_generation == self._generation
                 and op.generation == self._generation)
        if not bound:
            self._source_lost.set()
        return bound and not self._source_lost.is_set()

    def _unknown(self, op: _Activity, *, poison: bool = False) -> None:
        op.unknown = True
        self._closed = True
        if poison:
            with self._budget.lock:
                self._budget.poisoned = True

    def _retire(self, op: _Activity) -> None:
        if (op not in self._activities or op.unknown or op.release_attempted
                or not op.worker_done or not op.caller_done):
            return
        op.release_attempted = True  # no repeated ambiguous ledger effect
        try:
            self._budget.release(operator=False)
            with self._budget.lock:
                if self._budget.poisoned:
                    raise ReadActivityUnavailableError()
        except BaseException:
            self._unknown(op, poison=True)
            return
        self._activities.remove(op)
        if (self._closed and self._shutdown_attempted and not self._activities
                and not self._shutdown_failed):
            self._drained.set()

    def _worker_ended(self, op: _Activity, future: concurrent.futures.Future[Any]) -> None:
        if op not in self._activities or op.future is not future or op.worker_done:
            return
        if not future.done():
            self._unknown(op)
            return
        op.worker_done = True
        self._retire(op)

    def _notice(self, op: _Activity, future: concurrent.futures.Future[Any]) -> None:
        # This can run inline during registration, or on the actual SDK worker.
        try:
            assert self._loop is not None
            self._loop.call_soon_threadsafe(self._worker_ended, op, future)
        except BaseException:
            # Never mutate loop-owned bookkeeping or touch Store from this callback.
            # Its still-rooted activity cannot be retired without this notification.
            self._marshal_failed.set()
            return

    def _invoke(self, op: _Activity, function: Callable[[], Any]) -> Any:
        token = _WORKER.set(self)
        try:
            if not self._current(op):
                raise ReadActivityUnavailableError()
            value = function()
            if not self._current(op):
                raise ReadActivityUnavailableError()
            return value
        except (HmpError, ReadinessUnavailableError, ReadActivityUnavailableError):
            raise
        except BaseException:
            # Arbitrary reader exception text never enters an asyncio Future/log.
            raise ReadActivityUnavailableError() from None
        finally:
            _WORKER.reset(token)

    @asynccontextmanager
    async def activity(self, function: Callable[[], Any], *, deadline: float) -> AsyncIterator[Any]:
        loop = self._bind_loop()
        if self._marshal_failed.is_set() or self._source_lost.is_set():
            self._closed = True
        if self._closed or time.monotonic() >= deadline:
            raise ReadActivityUnavailableError()
        op = _Activity(asyncio.current_task(), self._bridge, self._generation)
        if not self._current(op):
            raise ReadActivityUnavailableError()
        token = _CALLER.set((self, op))
        try:
            execution_context = contextvars.copy_context()
            try:
                self._activities.add(op)  # before possibly effectful capacity acquisition
            except BaseException:
                self._activities.discard(op)  # capacity acquisition was never called
                raise ReadActivityUnavailableError() from None
            try:
                reserved = self._budget.reserve(operator=False)
            except BaseException:
                self._unknown(op, poison=True)
                raise ReadActivityUnavailableError() from None
            if reserved is False:
                self._activities.remove(op)
                raise ReadActivityUnavailableError()
            if reserved is not True:
                self._unknown(op, poison=True)
                raise ReadActivityUnavailableError()
            try:
                original = self._pool.submit(execution_context.run, self._invoke, op, function)
                op.future = original  # before even an inline completion callback
                if not isinstance(original, concurrent.futures.Future):
                    raise ReadActivityUnavailableError()
                original.add_done_callback(lambda future: self._notice(op, future))
            except BaseException:
                self._unknown(op)
                raise ReadActivityUnavailableError() from None
            wrapped = asyncio.wrap_future(original, loop=loop)

            def consume(done: asyncio.Future[Any]) -> None:
                with contextlib.suppress(BaseException):
                    done.exception()

            wrapped.add_done_callback(consume)
            value = await asyncio.wait_for(
                asyncio.shield(wrapped), max(0.0, deadline - time.monotonic()),
            )
            if self._marshal_failed.is_set() or self._source_lost.is_set():
                self._closed = True
            if self._closed or not self._current(op) or time.monotonic() >= deadline:
                raise ReadActivityUnavailableError()
            yield value  # post-await authority/readback/serialization still owns Store
        finally:
            if asyncio.current_task() is not op.caller:
                self._unknown(op)
                raise ReadActivityUnavailableError()
            try:
                _CALLER.reset(token)
            except BaseException:
                self._unknown(op)
                raise ReadActivityUnavailableError() from None
            op.caller_done = True
            self._retire(op)

    def stop(self) -> int:
        self._bind_loop()
        self._closed = True
        if self._shutdown_failed:
            raise ReadActivityUnavailableError()
        if not self._shutdown_attempted:
            self._shutdown_attempted = True
            try:
                self._pool.shutdown(wait=False, cancel_futures=False)
            except BaseException:
                self._shutdown_failed = True
                raise ReadActivityUnavailableError() from None
        if not self._activities:
            self._drained.set()
        return len(self._activities)

    @property
    def drained(self) -> bool:
        return (self._closed and self._shutdown_attempted and not self._activities
                and not self._shutdown_failed)

    async def wait_drained(self) -> None:
        self._bind_loop()
        caller = _CALLER.get()
        if (_WORKER.get() is self or
                (caller is not None and caller[0] is self
                 and caller[1].caller is asyncio.current_task())):
            raise ReadActivityUnavailableError()
        if not self._closed or not self._shutdown_attempted or self._shutdown_failed:
            raise ReadActivityUnavailableError()
        await self._drained.wait()
