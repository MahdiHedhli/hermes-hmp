"""Production route functions on a real plaintext peer; synthetic native bridge only.

These tests do not qualify adapter startup, TLS, or a physical client.
"""

import asyncio
import contextvars
from types import SimpleNamespace

import pytest
from aiohttp import ClientPayloadError, web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import presentation_routes as routes
from hmp_plugin import server
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import AuthzState
from hmp_plugin.presentation_native_http import NativePresentationStreamAbortedError
from hmp_plugin.request_ctx import ServerContext
from hmp_plugin.server import build_app

from .test_presentation_native_service import bind, submit
from .test_presentation_native_service import env as env
from .test_presentation_raster import png


async def client_for(env):
    original = env.ctx
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
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def headers(env):
    return {"Authorization": env.authorization, "HMP-Instance": env.iid}


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
