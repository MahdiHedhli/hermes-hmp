"""One retained relay-close attempt; settlement is distinct from successful close."""
from __future__ import annotations

import asyncio
import inspect


class RelayCloseOwner:
    def __init__(self, relay):
        self.relay = self._origin = relay
        self.attempted = False
        self.coro = None
        self.operation = None
        self.task = None
        self._complete, self._failed = object(), object()

    def begin(self):
        if self.relay is not self._origin:
            raise RuntimeError("relay cleanup scope changed")
        if not self.attempted:
            self.attempted = True
            try:
                self.operation = self._origin.close()
                self.coro = self._run(self.operation)
                self.task = asyncio.get_running_loop().create_task(self.coro)
                self.task.add_done_callback(self._settled)
            except BaseException:
                raise RuntimeError("relay cleanup ownership unresolved") from None
        if self.task is None:
            raise RuntimeError("relay cleanup ownership unresolved")
        return self.task

    def _settled(self, task):
        if task is self.task and inspect.iscoroutine(self.operation):
            self.operation.close()  # actual Task settlement only, never guessed enqueue

    async def _run(self, operation):
        try:
            await operation
        except BaseException:
            return self._failed
        return self._complete

    @property
    def successful(self):
        task = self.task
        return (self.relay is self._origin and task is not None and task.done()
                and not task.cancelled() and task.result() is self._complete)

    async def close_bounded(self, timeout):
        task = self.begin()
        await asyncio.wait((task,), timeout=timeout)  # never cancel the actual close
        if self.task is not task or self.relay is not self._origin:
            raise RuntimeError("relay cleanup scope changed")

    async def wait_drained(self):
        task = self.begin()
        await asyncio.shield(task)
        if self.task is not task or not self.successful:
            raise RuntimeError("relay cleanup success unconfirmed")
