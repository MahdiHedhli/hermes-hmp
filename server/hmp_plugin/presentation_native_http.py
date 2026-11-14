"""Actual owned HTTP write task. No routes, native lookup or acquisition renewal.

The service adopts this owner before start. Its task returns a closed status;
raw body/chunk aliases are cleared before completion. Cancellation requests abort
but never prove an async writer settled. Kernel/TLS bytes already sent cannot be
recalled; this is application ownership/currentness, not atomic revocation.
"""

from __future__ import annotations

import asyncio
import weakref
from contextlib import suppress

from aiohttp import web
from aiohttp.http_writer import StreamWriter


def native_http_mode_available():
    """Startup-only API/default-mode probe, with no socket or body operation.

    This does not certify TLS allocation/drain or grant request authority. Actual
    prepared responses still repeat their mode/currentness checks on each write.
    Missing private APIs disable this optional service, never other HMP features.
    """
    try:
        loop = asyncio.get_running_loop()
        response = NATIVE_RESPONSE_TYPE(status=200)
        response.content_length = 0
        writer = NATIVE_WRITER_TYPE(None, loop)
        return (
            response.compression is False
            and response.chunked is False
            and response.content_length == 0
            and response._send_headers_immediately is True
            and response._payload_writer is None
            and writer._compress is None
            and writer.chunked is False
            and writer._on_chunk_sent is None
            and writer._headers_buf is None
            and writer._headers_written is False
            and all(
                callable(getattr(writer, name, None))
                for name in ("write", "write_eof", "write_headers", "send_headers", "drain")
            )
        )
    except Exception:
        return False


def _detach_error_tracebacks(error):
    """Detach bounded native error roots; NEVER clear/close another frame.

    This does not prove buffer destruction. Actual native exporter weakref death
    plus sender termination governs release, including active foreign consumers.
    """
    seen, pending = [], [error]
    while pending:
        error = pending.pop()
        if error is None or any(error is prior for prior in seen):
            continue
        if len(seen) >= 8:
            return False
        seen.append(error)
        pending.extend((error.__cause__, error.__context__))
    for error in seen:
        error.__traceback__ = None
    return True


class _StreamChunk(bytearray):
    """Actual one-chunk exporter; bytearray subclasses support native weakrefs."""


class NativePresentationStreamAbortedError(ConnectionError):
    def __init__(self):
        super().__init__("presentation stream aborted")


class NativePresentationHttpWrite:
    def __init__(self):
        self.task = self.signal = self.response = self.transport = None
        self.request = self._service = self._op = None
        self._coroutine = self._timer = None
        self._leases = []
        self.deadline = 0.0
        self.status = "aborted"
        self.entered = self.registered = self.attempted = self.settled = False
        self.start_unknown = self.abort_unknown = self.task_unknown = False
        self.abort_attempted = False
        self._chunk_ref = self._chunk_signal = self._loop = None
        self._task_finished = False
        self.length = None

    @property
    def unknown(self):
        return self.start_unknown or self.abort_unknown or self.task_unknown

    def start(self, service, op, request, mime, length):
        self._service, self._op, self.request = service, op, request
        self._loop = service._loop
        try:
            self.signal = service._loop.create_future()
            self.deadline = service._clock() + 30.0
            self.transport = request.transport
            self.response = service._response_type(
                status=200,
                headers={
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "Content-Security-Policy": "default-src 'none'; sandbox",
                },
            )
            self.response.content_type = mime
            self.response.content_length = length
            self.length = length
            self._leases.append(op.memory.reserve("stream", 2 * 65_536))
            self._timer = service._loop.call_at(self.deadline, self.abort)
            self._coroutine = self._run()
        except BaseException:
            if self._timer is not None:
                self._timer.cancel()
            self.settled = True  # no task/prepare was attempted
            if self.signal is not None:
                self.signal.set_result(None)
            return False
        try:
            task = service._loop.create_task(self._coroutine)
            self._register(task)
        except BaseException:
            self.start_unknown = True
            return False  # retained; possible launch is not a failed-start proof
        return True

    def _register(self, task):
        if not isinstance(task, asyncio.Task) or (self.task is not None and task is not self.task):
            raise NativePresentationStreamAbortedError()
        self.task = task
        if not self.registered:
            self.registered = True
            task.add_done_callback(self._done)

    async def _run(self):
        body = chunk = buffer = None
        status = "aborted"
        try:
            # Observed target entry also handles native eager-task execution.
            self._register(asyncio.current_task())
            self.entered = True
            self._check()
            op = self._op
            body = op.result.metadata if op.kind == "metadata" else op.result.avatar
            if type(body) is not bytes:
                raise NativePresentationStreamAbortedError()
            self.attempted = True
            await self.response.prepare(self.request)
            self._check()
            self._mode_current()
            await self._flush_transport()
            for start in range(0, len(body), 65_536):
                self._check()
                self._mode_current()
                if self._chunk_ref is not None:
                    raise NativePresentationStreamAbortedError()
                self._chunk_signal = self._loop.create_future()
                # Copy only this actual <=64KiB exporter, not a bytes witness.
                buffer = _StreamChunk(memoryview(body)[start : start + 65_536])
                self._chunk_ref = weakref.ref(buffer, self._chunk_released)
                chunk = memoryview(buffer)
                buffer = None
                await self.response.write(chunk)
                chunk = None
                # Never create another application chunk while native code may
                # retain this exporter. Same fixed30s budget, no renewed credit.
                await asyncio.wait_for(
                    asyncio.shield(self._chunk_signal),
                    max(0.0, self.deadline - self._service._clock()),
                )
                await self._flush_transport()
                self._check()
            self._check()
            await self.response.write_eof()
            self._check(transport_required=False)
            status = "sent"
        except BaseException as error:
            try:
                cleared = _detach_error_tracebacks(error)
            except BaseException:
                cleared = False
            if not cleared:
                self.task_unknown = True
            status = "aborted"
        finally:
            # Drop direct payload aliases even if error-frame cleanup faults.
            body = chunk = buffer = op = None
        if status != "sent":
            self.abort()
        return status

    def _check(self, *, transport_required=True):
        if not self._service._write_current(self._op, self, transport_required=transport_required):
            raise NativePresentationStreamAbortedError()

    def _mode_current(self):
        # Fixed content-length, uncompressed immediate-header path only. A raw
        # body hook/compressor/header-coalescer is a separate unbounded channel,
        # not something exporter death can qualify. Native TLS/kernel copies are
        # outside this application-payload/RSS claim.
        response = self.response
        writer = response._payload_writer
        if (
            response.compression is not False
            or response.chunked is not False
            or response.content_length != self.length
            or response._send_headers_immediately is not True
            or writer._compress is not None
            or writer.chunked is not False
            or writer._on_chunk_sent is not None
            or writer._headers_buf is not None
            or writer._headers_written is not True
        ):
            raise NativePresentationStreamAbortedError()

    async def _flush_transport(self):
        # drain() resumes at a nonzero low watermark. Observe zero before a
        # new chunk / EOF so a previous native plaintext copy cannot accumulate
        # outside the retained128KiB stream allowance. No transport limits are
        # changed; native TLS/kernel memory is not an application RSS claim.
        while True:
            self._check()
            size = self.transport.get_write_buffer_size()
            if type(size) is not int or size < 0:
                raise NativePresentationStreamAbortedError()
            if size == 0:
                return
            await asyncio.sleep(0.005)

    def abort(self):
        if self.settled:
            return
        if not self.abort_attempted:
            self.abort_attempted = True
            try:
                if self.transport is not None and self.transport.abort() is not None:
                    self.abort_unknown = True
            except BaseException:
                self.abort_unknown = True
        task = self.task
        if task is not None and not task.done() and task is not asyncio.current_task():
            # No release follows cancellation; only _done observes termination.
            with suppress(BaseException):
                task.cancel()

    def _done(self, task):
        if task is not self.task or not task.done():
            self.task_unknown = True
            return
        if self.entered:
            self.start_unknown = False  # original target + actual Task termination
        if task.cancelled():
            self.status = "aborted"
            self.abort()
        elif task.exception() is not None:
            self.task_unknown = True
            self.abort()
        else:
            self.status = task.result()  # closed string only, never a payload
        self._task_finished = True
        if self._timer is not None:
            self._timer.cancel()
        self.request = self._coroutine = None
        if not self.signal.done():
            self.signal.set_result(None)
        self._update_settled()

    def _chunk_released(self, reference):
        # Native weakref callback holds no exporter/view/payload witness.
        with suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._observe_chunk, reference)

    def _observe_chunk(self, reference):
        if reference is not self._chunk_ref or reference() is not None:
            return
        self._chunk_ref = None
        if self._chunk_signal is not None and not self._chunk_signal.done():
            self._chunk_signal.set_result(None)
        if self._task_finished:
            self._update_settled()

    def _update_settled(self):
        self.settled = self._task_finished and not self.unknown and self._chunk_ref is None
        self._service._writer_finished(self._op.handle)

    def release(self):
        if (
            not self.settled
            or self.unknown
            or self._chunk_ref is not None
            or (self.task is not None and not self.task.done())
        ):
            raise NativePresentationStreamAbortedError()
        while self._leases:
            self._op.memory.release(self._leases.pop())
        if self._timer is not None:
            self._timer.cancel()
        self.request = self._coroutine = self.transport = None
        self._op = self._service = None


# Bound at native service construction, not selected by a request.
NATIVE_RESPONSE_TYPE = web.StreamResponse
NATIVE_WRITER_TYPE = StreamWriter
