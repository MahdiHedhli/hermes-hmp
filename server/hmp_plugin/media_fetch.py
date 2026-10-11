"""The authenticated local image fetch route (spec 011 S5; HMP v1 §7e LM-10..LM-16).

`GET /hmp/v1/bots/{p}/media/{ref}` is always registered. This module is the route's orchestrator
and the per-listener `MediaFetchService` (the one dedicated executor, the permits and the lease
bookkeeping). It imports no `local_media_*` module: every accepted module it reaches comes from
the references the listener bound at open (`ServerContext.media_snapshot`), and the listener
binder (`adapter._media_fetch_bind`) proves this module's namespace, the service class and the
carrier module are the very objects the bridge and the route run. Nothing here re-imports,
attests or touches the filesystem per request.

Order (LM-10): bearer, non-owner `404` (before the gate), query/body/transfer-encoding `400`,
rate limit, the initial per-bot grant (ERR-3, shared default executor), flag + availability
snapshot `503`, ref lookup `404`, then nonblocking permits `429`. Phase one (read, validate,
hash) and phase two (final native check) run on the service's own 4-worker executor with the
caller's `ContextVar`s copied into each, and share ONE monotonic 20 s deadline that starts at the
phase-one submission. No native call, file read or import ever runs on the event loop.

Lifetimes (LM-13). A buffer (instance) permit and the device permit belong to one `_Lease`. The
lease is released only when the handler's `finally` has passed AND every submitted phase future's
done callback has run (a phase two that never started counts as done). A worker permit is released
only by its own `concurrent.futures.Future` done callback, never by cancelling anything: a timeout
or a cancelled client leaves the actual worker running with its permits held. The worker wrapper
hands its 8 MiB payload to the lease's lock-protected mailbox and RETURNS only a bool, so no
completed future ever retains the payload; if the handler's `finally` already passed, the worker
drops the payload and publishes nothing. Callbacks hold the lease, never the payload.

The final section (LM-12) is synchronous: fresh bearer, owner, flag, availability snapshot, bound
service identity, registry entry and first-served compare-and-set, with no `await` before the
response is prepared. Streaming uses one 30 s deadline over `prepare`, every 64 KiB slice and EOF;
after `prepare` a timeout, cancellation or error aborts the transport and returns only after that.
A grant or tip change after the last native check and before `prepare` is a stated residual.

Logging: closed enum outcomes only (LM-16); never a ref, path, name, size, digest or exception text.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Final

from aiohttp import web

from . import media_payload
from .contract import (
    MEDIA_FETCH_PER_MIN,
    MEDIA_PERMITS_PER_DEVICE,
    MEDIA_PERMITS_PER_INSTANCE,
    MEDIA_WORKER_WAIT_S,
    MEDIA_WORKERS,
    MEDIA_WRITE_DEADLINE_S,
    ErrorCode,
    HmpError,
)
from .logging_policy import log_event
from .reads import require_bot_authorized
from .request_ctx import bearer, context

STREAM_SLICE_BYTES: Final = 64 * 1024
RATE_BUCKET: Final = "media_fetch"

# Closed `start` statuses and log outcomes.
STARTED: Final = "started"
BUSY: Final = "busy"
CLOSED: Final = "closed"
SUBMISSION_FAILED: Final = "submission_failed"
_LOG_EVENT: Final = "media_fetch"


class MediaServiceRefusal(Exception):  # noqa: N818 - a closed, content-free refusal
    """A bad service limit (a programming error). Fixed text, no parameters."""

    def __init__(self) -> None:
        super().__init__("media fetch service refused")

    def __reduce__(self) -> tuple[type[MediaServiceRefusal], tuple[()]]:
        return (MediaServiceRefusal, ())


class _Lease:
    """One request's buffer + device permit, its pending phase futures and its payload mailbox.

    Every field changes under the service lock. The mailbox holds the payload only while the
    handler is live; `finish()` clears it and a late worker can never publish into a finished
    lease."""

    __slots__ = ("_device", "_finished", "_payload", "_pending", "_released", "_service")

    def __init__(self, service: MediaFetchService, device_id: str) -> None:
        self._service = service
        self._device = device_id
        self._pending = 0
        self._finished = False
        self._released = False
        self._payload: Any = None

    # -- worker side ----------------------------------------------------------------------------

    def _publish(self, payload: Any) -> bool:
        """Hand a phase-one payload to the live handler; refuse (the caller drops it) after
        `finish()`. Returns only a bool."""
        with self._service._lock:
            if self._finished or self._payload is not None:
                return False
            self._payload = payload
            return True

    def _done(self, _future: Future[bool]) -> None:
        """The actual future's done callback: the only place a worker permit comes back. It never
        touches the future's result, so it can hold no payload."""
        with self._service._lock:
            self._pending -= 1
            self._service._workers_active -= 1
            self._release_if_ready()

    def _release_if_ready(self) -> None:
        """Service lock held. Buffer and device permits return only after BOTH the handler's
        `finally` and every submitted phase future's done callback."""
        if self._finished and self._pending == 0 and not self._released:
            self._released = True
            self._service._instance_used -= 1
            used = self._service._device_used
            used[self._device] -= 1
            if used[self._device] <= 0:
                del used[self._device]

    # -- handler side ---------------------------------------------------------------------------

    def start(
        self, call: Callable[[], Any], payload_type: type | None
    ) -> tuple[str, Future[bool] | None]:
        """Submit one phase job. Needs a worker permit WITHOUT waiting (`busy` otherwise) and never
        submits before it holds one. The caller's `ContextVar`s are copied into the job. A job that
        returns an exact `payload_type` instance publishes it to the mailbox; the future's own
        result is only a bool. A submission failure unwinds its permits exactly."""
        service = self._service
        with service._lock:
            if service._closed or self._finished:
                return CLOSED, None
            if service._workers_active >= service._worker_cap:
                return BUSY, None
            service._workers_active += 1
            self._pending += 1
        run = _runner(self, call, payload_type)
        copied = contextvars.copy_context()
        try:
            future: Future[bool] = service._executor.submit(copied.run, run)
        except BaseException:
            with service._lock:
                self._pending -= 1
                service._workers_active -= 1
                self._release_if_ready()
            return SUBMISSION_FAILED, None
        future.add_done_callback(self._done)
        return STARTED, future

    def take(self) -> Any:
        """Move the published payload out of the mailbox (or `None`)."""
        with self._service._lock:
            payload, self._payload = self._payload, None
            return payload

    def finish(self) -> None:
        """The handler's `finally` has passed: clear the mailbox, then release if no phase future
        is still actually running."""
        with self._service._lock:
            self._payload = None
            self._finished = True
            self._release_if_ready()


def _runner(
    lease: _Lease, call: Callable[[], Any], payload_type: type | None
) -> Callable[[], bool]:
    """The worker wrapper. It returns a bool and nothing else: a payload goes only to the lease
    mailbox, and every failure drops it."""

    def run() -> bool:
        payload = None
        try:
            payload = call()
            if payload_type is None:
                return payload is True
            if type(payload) is not payload_type:
                return False
            return lease._publish(payload)
        except BaseException:  # the worker never raises: a native or file fault is just False
            return False
        finally:
            payload = None

    return run


class MediaFetchService:
    """One per app/listener (never module-global): the dedicated 4-worker executor, the nonblocking
    worker permit (at most 4 actually concurrent futures), the 2-per-device and 4-per-instance
    buffer leases, and the admission switch. `close()` stops admissions and calls
    `executor.shutdown(wait=False)` without cancelling anything: pending actual futures keep their
    lifecycle and their permits. Threads start lazily on the first submission."""

    def __init__(
        self,
        *,
        _worker_cap: int = MEDIA_WORKERS,
        _device_cap: int = MEDIA_PERMITS_PER_DEVICE,
        _instance_cap: int = MEDIA_PERMITS_PER_INSTANCE,
    ) -> None:
        for value, limit in (
            (_worker_cap, MEDIA_WORKERS),
            (_device_cap, MEDIA_PERMITS_PER_DEVICE),
            (_instance_cap, MEDIA_PERMITS_PER_INSTANCE),
        ):
            if type(value) is not int or not 1 <= value <= limit:  # lower-only test seams
                raise MediaServiceRefusal from None
        self._lock = threading.Lock()
        self._closed = False
        self._worker_cap = _worker_cap
        self._device_cap = _device_cap
        self._instance_cap = _instance_cap
        self._workers_active = 0
        self._instance_used = 0
        self._device_used: dict[str, int] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=MEDIA_WORKERS, thread_name_prefix="hmp-media"
        )

    def __repr__(self) -> str:
        return "MediaFetchService()"

    __str__ = __repr__

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def close(self) -> None:
        """Close admissions and release the executor without waiting or cancelling."""
        with self._lock:
            already, self._closed = self._closed, True
        if not already:
            self._executor.shutdown(wait=False)

    def lease(self, device_id: str) -> _Lease | None:
        """A buffer + device lease, or `None` (no waiting) when closed or a limit is reached."""
        with self._lock:
            if self._closed:
                return None
            if (
                self._instance_used >= self._instance_cap
                or self._device_used.get(device_id, 0) >= self._device_cap
            ):
                return None
            self._instance_used += 1
            self._device_used[device_id] = self._device_used.get(device_id, 0) + 1
            return _Lease(self, device_id)

    def stats(self) -> tuple[int, int, int]:
        """`(instance leases, active workers, devices with a lease)` for tests and diagnostics."""
        with self._lock:
            return self._instance_used, self._workers_active, len(self._device_used)


MEDIA_SERVICE_KEY: web.AppKey[MediaFetchService] = web.AppKey("hmp_media_fetch", MediaFetchService)


async def close_service(app: web.Application) -> None:
    """`on_cleanup`: close admissions on this app's own service."""
    service = app.get(MEDIA_SERVICE_KEY)
    if service is not None:
        service.close()


def _not_found() -> HmpError:
    return HmpError(ErrorCode.NOT_FOUND)


def _not_started(status: str) -> HmpError:
    """Busy is `429`, admission closure is `503`, and a failed phase submission is `404`."""
    if status == BUSY:
        return HmpError(ErrorCode.RATE_LIMITED)
    if status == CLOSED:
        return HmpError(ErrorCode.MEDIA_UNAVAILABLE)
    return _not_found()


def _service_ok(service: Any, bound: Any) -> bool:
    """The route is running in the bound orchestrator namespace and the app's service is that
    namespace's exact class, still admitting."""
    fetch = bound.fetch_module
    cls = vars(fetch).get("MediaFetchService") if vars(fetch) is globals() else None
    return cls is not None and type(service) is cls and not service.closed


def _shaped_badly(request: web.Request) -> bool:
    """LM-10 step 3: any query, body or transfer-encoding."""
    return bool(
        request.query_string
        or "?" in request.raw_path
        or request.body_exists
        or (request.content_length or 0) > 0
        or "Transfer-Encoding" in request.headers
    )


async def _wait(future: Future[bool], deadline: float) -> bool | None:
    """The phase future's bool, or `None` when the shared deadline passes. The actual future is
    never cancelled: the shielded wrapper dies with the awaiter and the worker keeps running."""
    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        return None
    wrapped = asyncio.wrap_future(future)
    try:
        return bool(await asyncio.wait_for(asyncio.shield(wrapped), remaining))
    except TimeoutError:
        return None


async def serve(request: web.Request) -> web.StreamResponse:
    """`GET /hmp/v1/bots/{p}/media/{ref}`. See the module docstring for the order."""
    who = bearer(request)  # 1
    ctx = context(request)
    if not ctx.is_approval_owner_device(who.device_id):  # 2: before the gate
        raise _not_found()
    if _shaped_badly(request):  # 3
        raise HmpError(ErrorCode.BAD_REQUEST)
    ctx.limiter.check(RATE_BUCKET, who.device_id, MEDIA_FETCH_PER_MIN, ctx.now())  # 4
    profile, ref = request.match_info["p"], request.match_info["ref"]
    bridge = ctx.bridge
    if bridge is None:
        raise HmpError(ErrorCode.MEDIA_UNAVAILABLE)
    # 5: the initial per-bot grant, ERR-3 unchanged, on the shared default executor.
    await asyncio.to_thread(require_bot_authorized, bridge, who.user_id, profile)
    service = request.app.get(MEDIA_SERVICE_KEY)
    bound = ctx.media_snapshot() if ctx.media_enabled() else None  # 6
    if bound is None or not _service_ok(service, bound):
        raise HmpError(ErrorCode.MEDIA_UNAVAILABLE)
    try:  # 7
        caller = bound.registry_module.Caller(who.device_id, who.user_id, ctx.iid, profile)
        entry = bound.registry.lookup(ref, caller)
    except Exception:
        entry = None
    if entry is None:
        raise _not_found()
    lease = service.lease(who.device_id)  # 8
    if lease is None:
        raise HmpError(ErrorCode.RATE_LIMITED)
    payload: Any = None
    try:
        binding = entry.binding
        registry_module, chain = bound.registry_module, bound.chain
        # The ONE shared deadline starts at the phase-one submission: taken before `start`, so a
        # `submit` that has to create the executor's first thread spends the budget too.
        deadline = asyncio.get_running_loop().time() + MEDIA_WORKER_WAIT_S
        status, future = lease.start(
            lambda: bridge.media_fetch_phase_one(
                binding, chain, registry_module, bound.raster_module
            ),
            bound.payload_module.MediaPayload,
        )
        if future is None:
            raise _not_started(status)
        if await _wait(future, deadline) is not True:
            log_event(_LOG_EVENT, outcome="phase_one_refused")
            raise _not_found()
        payload = lease.take()
        if payload is None:
            raise _not_found()
        status, future = lease.start(
            lambda: bridge.media_fetch_phase_two(binding, chain, registry_module), None
        )
        if future is None:
            raise _not_started(status)
        if await _wait(future, deadline) is not True:
            log_event(_LOG_EVENT, outcome="phase_two_refused")
            raise _not_found()
        # LM-12: from here to `prepare` there is no await, native call, file read or import.
        response = _final_section(request, ctx, who, bound, service, ref, caller, entry, payload)
        return await _stream(request, response, payload)
    finally:
        payload = None
        lease.finish()


def _final_section(
    request: web.Request,
    ctx: Any,
    who: Any,
    bound: Any,
    service: Any,
    ref: str,
    caller: Any,
    entry: Any,
    payload: Any,
) -> web.StreamResponse:
    """Synchronous. The fresh bearer (existing `401` codes), owner, flag, availability snapshot,
    bound service, live registry entry and first-served CAS; any failure is `404`.

    `payload` is an argument of this frame, and a raised exception's traceback keeps the frame (and
    so its locals) alive after the handler is done: the `finally` drops the alias on every exit so
    a retained traceback can never hold the 8 MiB buffer once the permits are back."""
    try:
        again = bearer(request)
        if again.device_id != who.device_id or again.user_id != who.user_id:
            raise _not_found()
        if not ctx.is_approval_owner_device(again.device_id) or not ctx.media_enabled():
            raise _not_found()
        final = ctx.media_snapshot()
        if final is None or not final.same_as(bound):
            raise _not_found()
        if request.app.get(MEDIA_SERVICE_KEY) is not service or not _service_ok(service, final):
            raise _not_found()
        # The bound carrier module is this module's own import; the payload is exactly its class.
        if (
            final.payload_module is not media_payload
            or type(payload) is not media_payload.MediaPayload
        ):
            raise _not_found()
        live = final.registry.lookup(ref, caller)
        if live is None or live.binding is not entry.binding:
            raise _not_found()
        outcome = final.registry.record_first_served(ref, live, caller, payload.sha256)
        first_serve = final.registry_module.FirstServe
        if outcome is not first_serve.RECORDED and outcome is not first_serve.UNCHANGED:
            raise _not_found()
        response = web.StreamResponse(status=200)
        response.headers["Content-Type"] = payload.mime
        response.content_length = payload.size
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    finally:
        payload = None


async def _stream(
    request: web.Request, response: web.StreamResponse, payload: Any
) -> web.StreamResponse:
    """`prepare`, 64 KiB slices and EOF under ONE 30 s deadline.

    Before `prepare` has started, an unexpected failure is not swallowed: it propagates to the
    existing error middleware (standard ERR-1 `500`). Once `prepare` has started, a timeout,
    cancellation or error aborts the transport and no second body (JSON or otherwise) is written.
    The `finally` drops the `payload` argument and the `data` alias, so a traceback the framework
    or a caller retains never keeps the buffer."""
    data = payload.data
    payload = None
    size = len(data)
    deadline = asyncio.get_running_loop().time() + MEDIA_WRITE_DEADLINE_S
    try:
        async with asyncio.timeout_at(deadline):
            await response.prepare(request)
            for start in range(0, size, STREAM_SLICE_BYTES):
                await response.write(data[start : start + STREAM_SLICE_BYTES])
            await response.write_eof()
    except asyncio.CancelledError:
        _abort(request)
        raise
    except Exception:
        if not response.prepared:  # nothing is on the wire: the standard ERR-1 500 applies
            raise
        _abort(request)
        log_event(_LOG_EVENT, outcome="stream_aborted")
    finally:
        data = b""
        payload = None
    return response


def _abort(request: web.Request) -> None:
    transport = request.transport
    if transport is not None:
        transport.abort()


__all__ = [
    "BUSY",
    "CLOSED",
    "MEDIA_SERVICE_KEY",
    "STARTED",
    "STREAM_SLICE_BYTES",
    "MediaFetchService",
    "close_service",
    "serve",
]
