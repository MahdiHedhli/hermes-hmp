"""Unwired media-lane retirement only, NOT whole-listener Store-close authority.

The adapter must separately retire HTTP/read/native borrowers before closing Store.
Cancellation or a timeout of this waiter never proves that original work ended.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading

from .media_operator_service import MediaOperatorMutationService
from .media_publication_actor import MediaPublicationActor


class MediaRetirementUnavailableError(RuntimeError):
    def __init__(self):
        super().__init__("media retirement unresolved; retain original Store")


class MediaOperatorRetirement:
    def __init__(self, service, actor):
        if (
            type(service) is not MediaOperatorMutationService
            or type(actor) is not MediaPublicationActor
            or service._executor._actor is not actor
            or asyncio.get_running_loop() is not actor._loop
        ):
            raise MediaRetirementUnavailableError()
        self._service, self._actor = service, actor
        self._ctx, self._executor = service._original_ctx, service._executor
        self._store, self._budget = self._ctx.store, service._budget
        self._operations, self._mutations = service._operations, actor._mutations
        self._publisher, self._failure = actor._publisher, actor._failed
        self._loop, self._thread = actor._loop, actor._thread
        self._completion = object()
        self._failed_completion = object()
        self._join_coro = None  # retain unknown creation; never guess that it was unqueued
        self._started = False
        self._task = None
        if not self._same():
            raise MediaRetirementUnavailableError()

    def _owner(self):
        if (
            threading.current_thread() is not self._thread
            or asyncio.get_running_loop() is not self._loop
        ):
            raise MediaRetirementUnavailableError()

    def _same(self):
        return (
            self._service._original_ctx is self._ctx
            and self._service.ctx is self._ctx
            and self._ctx.store is self._store
            and self._ctx.identity is self._executor._identity
            and self._ctx.bridge is self._executor._bridge
            and self._ctx.iid == self._executor._iid
            and self._ctx.readiness_generation == self._executor._generation
            and self._service.nonce == self._executor._nonce
            and self._service._loop is self._loop
            and self._ctx.read_worker_budget is self._budget
            and self._service._budget is self._budget
            and self._service._executor is self._executor
            and self._executor._store is self._store
            and self._executor._actor is self._actor
            and self._service._operations is self._operations
            and self._actor._mutations is self._mutations
            and self._actor._publisher is self._publisher
            and self._actor._failed is self._failure
            and self._actor._loop is self._loop
            and self._actor._thread is self._thread
            and self._store._mutation_observer is self._actor
        )

    async def _join(self):
        try:
            await self._service.stop()
            await self._service.wait_drained()
            await self._actor.wait_drained()
            if not self._same() or self._operations or self._mutations:
                return self._failed_completion
            return self._completion
        except BaseException:
            # A creation acknowledgement or error-consumer registration can be
            # lost. Even an abandoned original Task emits no private exception.
            return self._failed_completion

    async def stop(self):
        self._owner()
        if not self._started:
            self._started = True  # unknown task creation/close is never automatically replayed
            try:
                if not self._same():
                    raise MediaRetirementUnavailableError()
                self._service.close_admission()
                self._actor.close()  # invalidate publication before any shutdown await
                self._join_coro = self._join()
                self._task = asyncio.create_task(self._join_coro)

                def consume_error(task):
                    with contextlib.suppress(BaseException):
                        task.exception()  # reporting only, no retirement proof

                self._task.add_done_callback(consume_error)
            except BaseException:
                raise MediaRetirementUnavailableError() from None
        task = self._task
        if task is None:
            raise MediaRetirementUnavailableError()
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.cancelled():
                raise MediaRetirementUnavailableError() from None
            raise  # caller cancellation leaves the original retirement owner alive
        except BaseException:
            raise MediaRetirementUnavailableError() from None
        if result is not self._completion or not self.drained_for(self._store):
            raise MediaRetirementUnavailableError()

    def drained_for(self, store) -> bool:
        """Media-lane proof for THIS Store only; does not close or authorize closing it."""
        self._owner()
        task = self._task
        if (
            store is not self._store
            or not self._same()
            or task is None
            or not task.done()
            or task.cancelled()
        ):
            return False
        try:
            return (
                task.result() is self._completion and not self._operations and not self._mutations
            )
        except BaseException:
            return False
