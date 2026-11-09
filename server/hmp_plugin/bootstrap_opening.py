"""Original component worker ownership only; partial listener recovery is separate."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib


class BootstrapUnresolvedError(RuntimeError):
    def __init__(self):
        super().__init__("bootstrap ownership unresolved; retain original resources")


class BootstrapOpening:
    def __init__(self, function, adapter):
        self.function, self.adapter = function, adapter
        self.ctx = self.store = self.close = self.server = None
        self.future = None
        self.started = False
        self.close_attempted = False
        self.closed = False
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _run(self):
        ctx = self.function(self.adapter)
        self.ctx = ctx  # retain immediately after the native function returns
        self.store = ctx.store
        self.close = self.store.close
        return ctx

    def start(self):
        if self.started:
            raise BootstrapUnresolvedError()
        self.started = True  # lost enqueue acknowledgement is never automatically replayed
        try:
            self.future = self.pool.submit(self._run)
        except BaseException:
            raise BootstrapUnresolvedError() from None

    async def wait(self):
        future = self.future
        if future is None:
            raise BootstrapUnresolvedError()
        wrapped = asyncio.wrap_future(future)

        def consume_error(done):
            with contextlib.suppress(BaseException):
                done.exception()  # reporting only, never resource-closure authority

        wrapped.add_done_callback(consume_error)
        try:
            ctx = await asyncio.shield(wrapped)
        finally:
            if future.done():
                self.pool.shutdown(wait=False, cancel_futures=False)
        if (
            self.future is not future
            or ctx is not self.ctx
            or self.ctx.store is not self.store
            or self.close is None
        ):
            raise BootstrapUnresolvedError()
        return ctx

    def close_unpublished(self, adapter):
        future, ctx, store, close = self.future, self.ctx, self.store, self.close
        original_adapter = self.adapter

        def rejoin():
            if (
                adapter is not original_adapter
                or self.adapter is not original_adapter
                or adapter._opening is not self
                or adapter._server is not None
                or self.server is not None
                or self.future is not future
                or self.ctx is not ctx
                or self.store is not store
                or self.close is not close
                or ctx is None
                or ctx.store is not store
                or close is None
            ):
                raise BootstrapUnresolvedError()

        rejoin()
        if (
            future is None
            or not future.done()
            or future.cancelled()
            or self.close_attempted
            or future.result() is not ctx
        ):
            raise BootstrapUnresolvedError()
        self.close_attempted = True  # any lost close acknowledgement prohibits replay
        adapter._close_generation(ctx)
        rejoin()
        if self.close_attempted is not True:
            raise BootstrapUnresolvedError()
        close()  # held original method, never a field reread after generation callbacks
        self.closed = True
