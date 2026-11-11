"""Production routes on real plaintext/TLS peers; synthetic native bridge only.

Bounded TLS success/peer-close observations do not qualify adapter startup,
arbitrary native SSL faults, process RSS, image decoding or a physical client.
"""

import asyncio
import contextvars
import hashlib
from types import SimpleNamespace

import pytest
from aiohttp import ClientPayloadError, Fingerprint, web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import presentation_native_http as native_http
from hmp_plugin import presentation_native_service as native_service
from hmp_plugin import presentation_routes as routes
from hmp_plugin import server
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import AuthzState
from hmp_plugin.presentation_native_http import NativePresentationStreamAbortedError
from hmp_plugin.request_ctx import ServerContext
from hmp_plugin.server import build_app
from hmp_plugin.wire import b64u_encode

from .hmp_kit import Env
from .test_presentation_native_http import avatar
from .test_presentation_native_service import bind, submit, until
from .test_presentation_native_service import env as env
from .test_presentation_raster import png


async def client_for(env, *, ssl_context=None):
    original = env.ctx
    if not hasattr(original.identity, "iid"):
        original.identity.iid = env.iid
    env.ctx = ServerContext(
        identity=original.identity,
        store=env.store,
        compat=CompatResult(CompatStatus.SUPPORTED),
        bridge=original.bridge,
        clock=original.now,
        reads=SimpleNamespace(roster=lambda user_id: {"bots": []}),
    )
    env.ctx.presentation_available = lambda: True
    app = build_app(env.ctx)
    listener = TestServer(app)
    await listener.start_server(ssl=ssl_context)
    client = TestClient(listener)
    await client.start_server()
    return client


def headers(env):
    return {"Authorization": env.authorization, "HMP-Instance": env.iid}


@pytest.mark.asyncio
async def test_startup_mode_probe_checks_actual_installed_defaults_without_io():
    assert native_http.native_http_mode_available() is True


@pytest.mark.asyncio
async def test_actual_service_binding_refuses_failed_http_probe_before_native_work(
    env, monkeypatch
):
    monkeypatch.setattr(native_service, "native_http_mode_available", lambda: False)
    owner = native_service.NativePresentationOwner()
    with pytest.raises(
        native_service.NativePresentationUnavailableError, match="http_mode_unavailable"
    ):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    assert owner._service is None and not env.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["response", "writer", "headers", "hook", "method"])
async def test_startup_mode_probe_refuses_missing_or_incompatible_api(monkeypatch, fault):
    original = native_http.NATIVE_WRITER_TYPE
    writes = []

    def writer(protocol, loop):
        result = original(protocol, loop)
        if fault == "writer":
            raise RuntimeError("synthetic constructor failure")
        if fault == "headers":
            result._headers_buf = b"synthetic"
        if fault == "hook":
            result._on_chunk_sent = lambda body: writes.append(body)
        if fault == "method":
            result.send_headers = None
        return result

    if fault == "response":
        monkeypatch.setattr(native_http, "NATIVE_RESPONSE_TYPE", lambda **kwargs: object())
    else:
        monkeypatch.setattr(native_http, "NATIVE_WRITER_TYPE", writer)
    assert native_http.native_http_mode_available() is False
    assert not writes


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", [None, "after_write", "tls_outgoing"])
async def test_real_tls13_pinned_multi_chunk_delivery_and_actual_writer_settlement(
    env, tmp_path, fault
):
    """Synthetic local identity/bridge; native TLS transport and writer, no decoder claim."""
    tls = Env(tmp_path / "isolated-tls-identity")
    try:
        env.iid = tls.iid
        env.ctx.iid = tls.iid
        env.ctx.identity = tls.identity
        token = b"B" * 32
        env.authorization = "Bearer " + b64u_encode(token)
        env.store.insert_access_token(
            hashlib.sha256(token).digest(), "family", "device", env.iid, 100000
        )
        image, revision = avatar(env, large=True)
        pin = Fingerprint(hashlib.sha256(tls.identity.certificate_der()).digest())
        async with await client_for(
            env, ssl_context=server.server_ssl_context(tls.identity)
        ) as client:
            _, service = bind(env)
            env.ctx.presentation_service = service
            operations, transports, protocols = [], [], []
            actual_emit = service.emit
            first_write = asyncio.Event()
            held_write = asyncio.Event()
            writes = []

            class PausedResponse(web.StreamResponse):
                async def write(self, data):
                    if fault == "tls_outgoing":
                        protocols[0].pause_writing()
                    writes.append(len(data))
                    first_write.set()
                    await super().write(data)
                    if fault != "tls_outgoing":
                        await held_write.wait()

            if fault:
                # Hold the caller after native write, or pause the actual SSL
                # protocol's encrypted outgoing queue without faking SSL writes.
                service._response_type = PausedResponse

            async def observe(handle, request):
                operations.append(service._ops[handle])
                transports.append(request.transport)
                protocols.append(request.transport._ssl_protocol)
                assert request.transport.get_extra_info("ssl_object").version() == "TLSv1.3"
                return await actual_emit(handle, request)

            service.emit = observe
            response = await client.get(
                "/hmp/v1/bots/belac/presentation/avatar/" + revision, headers=headers(env), ssl=pin
            )
            assert response.status == 200
            if fault:
                await asyncio.wait_for(first_write.wait(), 2)
                if fault == "tls_outgoing":
                    await until(lambda: protocols[0]._outgoing.pending >= 65536)
                    op = operations[0]
                    await until(lambda: op.writer._chunk_ref is None)
                    assert op.memory.snapshot()[0] > 0 and service._ops
                    assert not op.writer.task.done() and writes == [65536]
                    assert protocols[0]._write_buffer_size == 0
                response.close()
                # Close only the peer session. TestClient.close also tears down
                # the server and would weaken this isolated-disconnect proof.
                await client.session.close()
                assert not client.server.closed
            else:
                assert await response.read() == image
            assert response.content_length == len(image) and len(image) > 2 * 65536
            op = operations[0]
            # The peer receiving bytes alone is insufficient: observe the real
            # sender task, exporter lifetime and native TLS output backlog too.
            await until(lambda: not service._ops)
            assert op.writer.task.done()
            assert op.writer.task.result() == ("aborted" if fault else "sent")
            if fault:
                assert writes == [65536] and op.writer.abort_attempted
                assert transports[0].is_closing()
                # A closed SSL transport detaches its protocol; asking its
                # buffer getter afterward is invalid, not a zero-size proof.
                assert not protocols[0]._write_backlog
                assert protocols[0]._outgoing.pending == 0
                assert not client.server.closed
            else:
                assert transports[0].get_write_buffer_size() == 0
            assert op.writer._chunk_ref is None and op.writer.settled
            assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
            assert await service.close_and_join()
    finally:
        tls.store.close()


@pytest.mark.asyncio
async def test_original_native_context_survives_caller_scope_change_and_is_released(env):
    scope = contextvars.ContextVar("synthetic_profile", default="wrong")
    observations = []
    env.gate = lambda profile: observations.append(scope.get())
    _, service = bind(env)
    token = scope.set("original-belac")
    try:
        handle = submit(env, service)
    finally:
        scope.reset(token)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    assert observations and set(observations) == {"original-belac"}
    assert op.joined and op.native_context is None
    service.abandon(handle)
    assert await service.close_and_join()


@pytest.mark.asyncio
async def test_unbound_route_authenticates_before_optional_capability_diagnostics(env):
    async with await client_for(env) as client:
        response = await client.get("/hmp/v1/bots/belac/presentation")
        assert response.status == 401
        response = await client.get("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == 503
        assert (await response.json())["error"]["code"] == "presentation_unavailable"
        assert not env.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["?unexpected=1", "/avatar/not-a-revision"])
async def test_invalid_input_does_not_start_native_lookup(env, suffix):
    async with await client_for(env) as client:
        _, service = bind(env)
        env.ctx.presentation_service = service
        response = await client.get(
            "/hmp/v1/bots/belac/presentation" + suffix, headers=headers(env)
        )
        assert response.status == 400
        assert not env.calls and not service._ops
        assert await service.close_and_join()


@pytest.mark.asyncio
async def test_roster_capability_requires_current_exact_bound_service(env):
    assert routes.bound_service(SimpleNamespace()) is None
    ctx = env.ctx
    ctx.presentation_service = None
    ctx.presentation_available = lambda: True
    original = {"bots": [], "capabilities": {"other": 2, "bot_presentation": 1}}
    assert routes.roster_capability(ctx, original)["capabilities"] == {"other": 2}
    _, service = bind(env)
    ctx.presentation_service = service
    assert routes.roster_capability(ctx, original)["capabilities"] == original["capabilities"]
    ctx.presentation_available = lambda: False
    assert routes.roster_capability(ctx, original)["capabilities"] == {"other": 2}
    ctx.presentation_available = lambda: True
    alien = SimpleNamespace(presentation_service=service, presentation_available=lambda: True)
    assert routes.roster_capability(alien, original)["capabilities"] == {"other": 2}
    assert original["capabilities"]["bot_presentation"] == 1
    assert await service.close_and_join()
    assert routes.roster_capability(ctx, original)["capabilities"] == {"other": 2}


@pytest.mark.asyncio
async def test_actual_metadata_and_revision_bound_avatar_route(env):
    assets = env.homes["belac"] / "assets"
    assets.mkdir(mode=0o700)
    image = png()
    avatar = assets / "avatar.png"
    avatar.write_bytes(image)
    avatar.chmod(0o600)
    async with await client_for(env) as client:
        _, service = bind(env)
        env.ctx.presentation_service = service
        response = await client.get("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == 200
        metadata = await response.json()
        assert metadata["display_name"] == "Synthetic native fixture"
        revision = metadata["avatar"]["revision"]
        response = await client.get(
            "/hmp/v1/bots/belac/presentation/avatar/" + revision, headers=headers(env)
        )
        assert response.status == 200 and await response.read() == image
        response = await client.get(
            "/hmp/v1/bots/belac/presentation/avatar/" + "0" * 64, headers=headers(env)
        )
        assert response.status == 404
        assert await service.close_and_join()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state,status",
    [
        (AuthzState.PENDING_OPERATOR, 403),
        (AuthzState.NOT_SERVED, 409),
        (AuthzState.NOT_ROUTED, 409),
        (AuthzState.UNVERIFIABLE, 503),
    ],
)
async def test_actual_route_preserves_native_bot_authorization_refusals(env, state, status):
    env.states["belac"] = state
    async with await client_for(env) as client:
        _, service = bind(env)
        env.ctx.presentation_service = service
        response = await client.get("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == status
        body = await response.json()
        assert body["error"]["authz"] == state.value
        assert not env.calls
        assert await service.close_and_join()


@pytest.mark.asyncio
async def test_prepared_stream_failure_aborts_without_second_json_body(env, monkeypatch):
    shaped = []
    original = server.error_response

    def record(error):
        shaped.append(error.code)
        return original(error)

    monkeypatch.setattr(server, "error_response", record)
    async with await client_for(env) as client:
        _, service = bind(env)
        env.ctx.presentation_service = service

        async def broken_emit(handle, request):
            response = web.StreamResponse(headers={"Content-Length": "1000"})
            await response.prepare(request)
            await response.write(b"synthetic-partial")
            raise NativePresentationStreamAbortedError()

        monkeypatch.setattr(service, "emit", broken_emit)
        response = await client.get("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == 200
        with pytest.raises(ClientPayloadError):
            await asyncio.wait_for(response.read(), 2)
        assert not shaped
        assert await service.close_and_join()


@pytest.mark.asyncio
async def test_actual_app_roster_negotiation_method_and_rate_controls(env):
    async with await client_for(env) as client:
        response = await client.get("/hmp/v1/bots", headers=headers(env))
        assert await response.json() == {"bots": []}
        _, service = bind(env)
        env.ctx.presentation_service = service
        response = await client.get("/hmp/v1/bots", headers=headers(env))
        assert (await response.json())["capabilities"]["bot_presentation"] == 1
        response = await client.head("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == 404 and not env.calls
        # Exhaust only this actor's presentation bucket, never a generic auth or
        # chat bucket; the next request must refuse before native observation.
        for _ in range(routes.RATE_READ_PER_MIN_PER_DEVICE_ID):
            env.ctx.limiter.allow(
                "bots_presentation", "device", routes.RATE_READ_PER_MIN_PER_DEVICE_ID, env.ctx.now()
            )
        response = await client.get("/hmp/v1/bots/belac/presentation", headers=headers(env))
        assert response.status == 429 and not env.calls and not service._ops
        assert await service.close_and_join()
