"""Owned HTTP writes: real aiohttp peer plus explicit synthetic async fault ports.

No production adapter/TLS/client/device qualification. Fake peer copies are test
receiver data, not a claim about native transport allocation/RSS.
"""

import asyncio
import hashlib
import json
from itertools import pairwise
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from multidict import CIMultiDict

from hmp_plugin import presentation_native_http as http
from hmp_plugin.presentation_native_http import NativePresentationStreamAbortedError
from hmp_plugin.presentation_native_service import NativePresentationUnavailableError

from .test_presentation_native_service import bind, submit, until
from .test_presentation_native_service import env as env
from .test_presentation_raster import chunk, png


class Transport:
    def __init__(self, *, fail=False):
        self.closed = False
        self.aborts = 0
        self.fail = fail
        self.buffer = bytearray()

    def is_closing(self):
        return self.closed

    def get_write_buffer_size(self):
        return len(self.buffer)

    def abort(self):
        self.aborts += 1
        if self.fail:
            raise OSError("synthetic abort acknowledgement lost")
        self.closed = True
        self.buffer.clear()


class Response:
    def __init__(self, *, status, headers):
        self.status, self.headers = status, headers
        self.content_type = self.content_length = None
        self.prepares = self.eofs = 0
        self.peer = bytearray()
        self.compression = self.chunked = False
        self._send_headers_immediately = True
        self._payload_writer = SimpleNamespace(
            _compress=None,
            chunked=False,
            _on_chunk_sent=None,
            _headers_buf=None,
            _headers_written=True,
        )

    async def prepare(self, request):
        self.prepares += 1

    async def write(self, data):
        self.peer.extend(data)

    async def write_eof(self):
        self.eofs += 1


def request(env, *, revision=None, transport=None):
    return SimpleNamespace(
        method="GET",
        match_info={"p": "belac", "revision": revision},
        headers=CIMultiDict({"Authorization": env.authorization, "HMP-Instance": env.iid}),
        transport=Transport() if transport is None else transport,
    )


def avatar(env, *, large=False):
    assets = env.homes["belac"] / "assets"
    assets.mkdir(mode=0o700)
    image = png(extra=chunk(b"tEXt", b"x" * 150_000)) if large else png()
    path = assets / "avatar.png"
    path.write_bytes(image)
    path.chmod(0o600)
    # Temporary macOS wheel inheritance is not the native service group policy.
    import os

    for item in (assets, path):
        os.chown(item, os.geteuid(), os.getegid())
    return image, hashlib.sha256(image).hexdigest()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["metadata", "avatar"])
async def test_actual_aiohttp_get_delivers_closed_json_or_exact_static_bytes(env, kind):
    _, service = bind(env)
    image, revision = avatar(env)
    app = web.Application()
    operations = []

    async def handler(req):
        handle = submit(env, service, kind=kind, revision=revision if kind == "avatar" else None)
        op = service._ops[handle]
        operations.append(op)
        try:
            assert await service.wait(handle) == "ready"
            return await service.emit(handle, req)
        finally:
            service.abandon(handle)

    path = (
        "/bots/{p}/presentation"
        if kind == "metadata"
        else "/bots/{p}/presentation/avatar/{revision}"
    )
    app.router.add_get(path, handler, allow_head=False)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        url = "/bots/belac/presentation" + ("/avatar/" + revision if kind == "avatar" else "")
        response = await client.get(
            url, headers={"Authorization": env.authorization, "HMP-Instance": env.iid}
        )
        data = await response.read()
        assert response.status == 200 and response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.content_length == len(data)
        if kind == "metadata":
            assert response.content_type == "application/json"
            assert json.loads(data)["avatar"]["revision"] == revision
        else:
            assert response.content_type == "image/png" and data == image
        await until(lambda: not service._ops)
        op = operations[0]
        assert op.writer.task.result() == "sent" and op.writer.signal.result() is None
        assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    finally:
        await client.close()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", ["profile", "instance", "duplicate", "method"])
async def test_second_boundary_rejects_wrong_request_scope_before_prepare(env, wrong):
    _, service = bind(env)
    service._response_type = Response
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env)
    if wrong == "profile":
        req.match_info["p"] = "other"
    elif wrong == "instance":
        req.headers["HMP-Instance"] = "b" * 52
    elif wrong == "duplicate":
        req.headers.add("Authorization", env.authorization)
    else:
        req.method = "POST"
    with pytest.raises(NativePresentationUnavailableError):
        await service.emit(handle, req)
    assert op.writer is None and op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_write_budget_is_separate_from_closed_original_two_second_acquisition(env):
    _, service = bind(env)
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowPrepare(Response):
        async def prepare(self, req):
            self.prepares += 1
            entered.set()
            await release.wait()

    service._response_type = SlowPrepare
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    task = asyncio.create_task(service.emit(handle, request(env)))
    try:
        await entered.wait()
        assert 27.0 < op.writer.deadline - op.deadline <= 30.0
        await asyncio.sleep(2.05)  # actual acquisition deadline passes during prepare
        assert service._clock() > op.deadline and not op.retired and op.result is not None
        release.set()
        response = await task
        assert response.prepares == response.eofs == 1
        assert op.memory.snapshot()[:2] == (0, 0)
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_cancellation_does_not_release_noncooperative_actual_async_writer(env):
    owner, service = bind(env)
    entered, release = asyncio.Event(), asyncio.Event()

    class Stuck(Response):
        async def write(self, data):
            entered.set()
            while not release.is_set():
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    continue

    service._response_type = Stuck
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env)
    task = asyncio.create_task(service.emit(handle, req))
    try:
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert op.retired and not op.writer.task.done() and op.result is not None
        assert op.memory.snapshot()[0] > 0 and req.transport.aborts == 1
        assert await service.close_and_join(0.02) is False
        with pytest.raises(NativePresentationUnavailableError):
            owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    finally:
        release.set()
        assert await service.close_and_join() is True
        assert op.writer.task.done() and op.writer.task.result() == "aborted"
        assert op.result is None and op.memory.snapshot()[:2] == (0, 0)


@pytest.mark.asyncio
async def test_observed_device_revocation_between_chunks_aborts_without_second_body(env):
    _, service = bind(env)
    _, revision = avatar(env, large=True)

    class Revoke(Response):
        async def write(self, data):
            self.peer.extend(data)
            env.store.revoke_family("family", 1001)

    service._response_type = Revoke
    handle = submit(env, service, kind="avatar", revision=revision)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env, revision=revision)
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, req)
    response = op.writer.response
    assert len(response.peer) == 65_536 and response.prepares == 1 and response.eofs == 0
    assert req.transport.aborts == 1 and op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_unknown_abort_retains_result_stream_credit_and_blocks_replacement(env):
    owner, service = bind(env)

    class Broken(Response):
        async def write(self, data):
            raise OSError("synthetic network fault")

    service._response_type = Broken
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    transport = Transport(fail=True)
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, request(env, transport=transport))
    assert op.writer.task.done() and op.writer.abort_unknown and not op.writer.settled
    assert op.result is not None and op.memory.snapshot()[0] > 2 * 65_536
    assert await service.close_and_join(0.02) is False and transport.aborts == 1
    with pytest.raises(NativePresentationUnavailableError):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    # Fixture-only payload disposal; unresolved service debt is not reset.
    op.result.discard()
    while op.writer._leases:
        op.memory.release(op.writer._leases.pop())


@pytest.mark.asyncio
async def test_actual_thirty_second_prepare_deadline_aborts_and_settles_known_writer(env):
    _, service = bind(env)
    entered = asyncio.Event()

    class NeverPrepare(Response):
        async def prepare(self, req):
            self.prepares += 1
            entered.set()
            await asyncio.Event().wait()

    service._response_type = NeverPrepare
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env)
    started = service._clock()
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, req)
    assert entered.is_set() and 29.5 <= service._clock() - started < 35.0
    assert req.transport.aborts == 1
    assert await service.close_and_join() is True
    assert op.writer.task.done() and op.result is None and op.memory.snapshot()[:2] == (0, 0)


@pytest.mark.asyncio
async def test_retained_native_error_future_has_no_completed_write_chunk_frame_alias(env):
    _, service = bind(env)
    retained = []

    class FailedDrain(Response):
        async def write(self, data):
            future = asyncio.get_running_loop().create_future()
            future.set_exception(OSError("synthetic retained drain error"))
            retained.append(future)
            await future

    service._response_type = FailedDrain
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, request(env))
    error = retained[0].exception()
    assert error.__traceback__ is None and op.writer.task.result() == "aborted"
    assert op.writer._chunk_ref is None
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


def test_error_detachment_follows_cause_and_suppressed_context_without_mutating_frames():
    def write(data):
        try:
            raise OSError("synthetic frame")
        except OSError as error:
            return error

    cause, context = write(b"SYNTHETIC_CAUSE"), write(b"SYNTHETIC_CONTEXT")
    outer = ValueError("synthetic wrapper")
    outer.__cause__, outer.__context__ = cause, context
    outer.__suppress_context__ = True
    context.__context__ = outer  # finite identity cycle, not an infinite walk
    assert http._detach_error_tracebacks(outer)
    assert outer.__traceback__ is cause.__traceback__ is context.__traceback__ is None


def test_error_chain_beyond_cleanup_limit_is_not_known_settled():
    errors = [ValueError("synthetic") for _ in range(9)]
    for left, right in pairwise(errors):
        left.__cause__ = right
    assert http._detach_error_tracebacks(errors[0]) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["unknown", "raises"])
async def test_unproven_error_frame_cleanup_retains_task_result_and_stream_debt(
    env, monkeypatch, fault
):
    owner, service = bind(env)

    class Failed(Response):
        async def write(self, data):
            raise OSError("synthetic write failure")

    def unproven(error):
        if fault == "raises":
            raise MemoryError("synthetic cleanup fault")
        return False

    monkeypatch.setattr(http, "_detach_error_tracebacks", unproven)
    service._response_type = Failed
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, request(env))
    assert op.writer.task.done() and op.writer.task.exception() is None
    assert op.writer.task.result() == "aborted" and op.writer.signal.result() is None
    assert op.writer.task_unknown and not op.writer.settled and op.result is not None
    assert op.memory.snapshot()[0] > 2 * 65_536
    assert await service.close_and_join(0.02) is False
    with pytest.raises(NativePresentationUnavailableError):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    op.result.discard()  # fixture-only disposal; unknown service debt remains
    while op.writer._leases:
        op.memory.release(op.writer._leases.pop())


@pytest.mark.asyncio
async def test_response_construction_failure_has_no_network_effect_or_late_abort(env):
    _, service = bind(env)

    def failed_response(**kwargs):
        raise MemoryError("synthetic constructor failure")

    service._response_type = failed_response
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env)
    with pytest.raises(NativePresentationUnavailableError):
        await service.emit(handle, req)
    assert op.writer.settled and op.writer.task is None
    op.writer.abort()  # even a late callback cannot close a reused connection
    assert req.transport.aborts == 0
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("alias", ["original", "slice"])
async def test_native_foreign_suspended_consumer_keeps_actual_exporter_credit_until_drop(
    env, alias
):
    owner, service = bind(env)
    entered, release = asyncio.Event(), asyncio.Event()
    consumers, errors = [], []

    async def foreign(data):
        try:
            try:
                raise OSError("synthetic foreign frame")
            except OSError as error:
                errors.append(error)
            entered.set()
            await release.wait()
            assert len(data) > 0  # frame/data was NOT cleared/closed by another task
        finally:
            data = None

    class Foreign(Response):
        async def write(self, data):
            consumers.append(
                asyncio.create_task(foreign(data if alias == "original" else data[1:]))
            )
            await entered.wait()
            error = OSError("synthetic failed native write with retained consumer")
            error.__context__ = errors[0]
            raise error

    service._response_type = Foreign
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    try:
        with pytest.raises(NativePresentationStreamAbortedError):
            await service.emit(handle, request(env))
        assert op.writer.task.done() and op.writer.task.result() == "aborted"
        assert not consumers[0].done() and consumers[0].get_coro().cr_frame is not None
        assert errors[0].__traceback__ is None
        assert op.writer._chunk_ref() is not None and not op.writer.settled
        assert op.result is not None and op.memory.snapshot()[0] > 2 * 65_536
        assert await service.close_and_join(0.02) is False
        with pytest.raises(NativePresentationUnavailableError):
            owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    finally:
        release.set()
        await asyncio.gather(*consumers)
        await until(lambda: not service._ops)
        assert await service.close_and_join() is True
        assert op.writer._chunk_ref is None and op.result is None
        assert op.memory.snapshot()[:2] == (0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["compression", "chunked", "body_hook", "deferred_headers"])
async def test_unqualified_native_copy_channels_abort_before_any_body(env, mode):
    _, service = bind(env)

    class Unqualified(Response):
        async def prepare(self, req):
            self.prepares += 1
            if mode == "compression":
                self.compression = True
            elif mode == "chunked":
                self._payload_writer.chunked = True
            elif mode == "body_hook":
                self._payload_writer._on_chunk_sent = lambda data: None
            else:
                self._payload_writer._headers_buf = b"synthetic deferred headers"

    service._response_type = Unqualified
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    req = request(env)
    with pytest.raises(NativePresentationStreamAbortedError):
        await service.emit(handle, req)
    assert not op.writer.response.peer and req.transport.aborts == 1
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_independent_native_plaintext_copy_drains_before_next_chunk_and_release(env):
    _, service = bind(env)
    image, revision = avatar(env, large=True)
    transport = Transport()
    entered = asyncio.Event()

    class Buffered(Response):
        async def write(self, data):
            if not self.peer:
                transport.buffer.extend(data)  # actual independent native-copy fixture
                entered.set()
            self.peer.extend(data)

    service._response_type = Buffered
    handle = submit(env, service, kind="avatar", revision=revision)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    task = asyncio.create_task(
        service.emit(handle, request(env, revision=revision, transport=transport))
    )
    try:
        await entered.wait()
        await asyncio.sleep(0.02)
        assert op.writer._chunk_ref is None  # original exporter gone, copy still pending
        assert len(transport.buffer) == len(op.writer.response.peer) == 65_536
        assert not task.done() and op.result is not None and op.memory.snapshot()[0] > 0
        transport.buffer.clear()
        response = await task
        assert bytes(response.peer) == image and response.eofs == 1
        assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    finally:
        transport.buffer.clear()
        assert await service.close_and_join() is True
