"""Default-model owner boundary and catalog projection."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import mobile_model, wire
from hmp_plugin.compat import compute_read_bridge_fingerprint
from hmp_plugin.contract import PATH_PREFIX, AuthzState, DirectSendEndpoint, ErrorCode, HmpError

from .hmp_kit import Env, get, pair, run


def test_model_selection_rejects_extra_fields_and_controls() -> None:
    assert mobile_model.selection({"provider": "custom:local", "model": "org/model"}) == (
        "custom:local", "org/model",
    )
    for body in (
        {"provider": "x", "model": "m", "api_key": "synthetic"},
        {"provider": "../other", "model": "m"},
        {"provider": "x", "model": "m\nnext"},
        {"provider": "x", "model": ""},
    ):
        with pytest.raises(HmpError) as exc:
            mobile_model.selection(body)
        assert exc.value.code is ErrorCode.BAD_REQUEST


def test_catalog_projection_drops_internal_fields_and_unconfigured_rows() -> None:
    result = mobile_model.project_options({"providers": [
        {"slug": "nous", "name": "Nous", "authenticated": True,
         "models": ["nous/model-a"], "base_url": "private-endpoint",
         "api_key": "synthetic-secret", "pricing": {"internal": "private"}},
        {"slug": "other", "name": "Other", "authenticated": False,
         "models": ["other/model-b"]},
    ], "config": {"secrets": "private"}})
    assert result == {"providers": [{
        "provider": "nous", "name": "Nous", "models": ["nous/model-a"],
    }]}
    assert "private" not in str(result)
    with pytest.raises(HmpError):
        mobile_model.project_options({"providers": [
            {"slug": "bad", "authenticated": True, "models": ["x\nkey"]},
        ]})


def test_current_projection_rejects_unbounded_or_non_text_values() -> None:
    assert mobile_model.project_current({"provider": "nous", "model": "nous/model"}) == {
        "provider": "nous", "model": "nous/model",
    }
    for value in ({"provider": "nous", "model": 3},
                  {"provider": "nous", "model": "x" * 241}):
        with pytest.raises(HmpError) as exc:
            mobile_model.project_current(value)
        assert exc.value.code is ErrorCode.MODEL_UNAVAILABLE


def test_model_fingerprint_fails_closed_after_source_change(tmp_path: Path) -> None:
    (tmp_path / "writer.py").write_text("approved", encoding="utf-8")
    fingerprint = compute_read_bridge_fingerprint(tmp_path, ["writer.py"])
    builds = tmp_path / "builds.json"
    builds.write_text(json.dumps({
        "format": 1, "bridge_files": ["writer.py"],
        "builds": [{"fingerprint": fingerprint, "git_sha": None,
                    "qualified_by": "test"}],
    }), encoding="utf-8")
    assert mobile_model.qualified_build(root=tmp_path, builds_path=builds)
    (tmp_path / "writer.py").write_text("changed", encoding="utf-8")
    assert not mobile_model.qualified_build(root=tmp_path, builds_path=builds)


def test_model_routes_reject_non_owner_disabled_and_unqualified(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls: list[str] = []
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.bridge.profile_default_model = lambda p: calls.append(p)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        url = "/bots/default/model/default"
        status, _ = await get(client, url, headers=env.headers(dev))
        assert status == 404 and not calls
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, _ = await get(client, url, headers=env.headers(dev))
        assert status == 503 and not calls
        env.ctx.model_flag = lambda: True
        env.ctx.model_qualified = lambda: False
        status, _ = await get(client, url, headers=env.headers(dev))
        assert status == 503 and not calls
        env.ctx.model_qualified = lambda: True
        env.bridge.authz_state = lambda *_: AuthzState.PENDING_OPERATOR
        status, _ = await get(client, url, headers=env.headers(dev))
        assert status == 403 and not calls

    run(env, scenario)


def test_model_routes_use_exact_profile_and_do_not_retry_write(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls: list[tuple[str, ...]] = []
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.bridge.profile_default_model = lambda p: (
        calls.append(("read", p)) or {"provider": "nous", "model": "old"}
    )
    env.bridge.set_profile_default_model = lambda p, provider, model: (
        calls.append(("write", p, provider, model))
        or {"provider": provider, "model": model}
    )
    env.ctx.model_flag = lambda: True
    env.ctx.model_qualified = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        headers = env.headers(dev)
        status, data = await get(client, "/bots/other/model/default", headers=headers)
        assert status == 200 and data == {"provider": "nous", "model": "old"}
        response = await client.put(
            PATH_PREFIX + "/bots/other/model/default",
            data=wire.dump_json({"provider": "nous", "model": "new"}), headers=headers,
        )
        assert response.status == 200
        assert await response.json() == {"provider": "nous", "model": "new"}
        assert calls == [("read", "other"), ("write", "other", "nous", "new")]
        response = await client.put(
            PATH_PREFIX + "/bots/other/model/default",
            data=wire.dump_json({"provider": "nous", "model": "new", "url": "bad"}),
            headers=headers,
        )
        assert response.status == 400
        assert calls == [("read", "other"), ("write", "other", "nous", "new")]

    run(env, scenario)


@pytest.mark.asyncio
async def test_options_pins_loopback_and_drops_raw_data() -> None:
    async def catalog(request: web.Request) -> web.Response:
        assert request.path == "/p/other/api/model/options"
        assert request.query == {"refresh": "false"}
        assert request.headers["Authorization"] == "Bearer " + "x" * 24
        return web.json_response({"providers": [
            {"slug": "nous", "name": "Nous", "authenticated": True,
             "models": ["nous/model"], "api_key": "synthetic-secret"},
        ]})

    app = web.Application()
    app.router.add_get("/p/other/api/model/options", catalog)
    server = TestServer(app)
    await server.start_server()
    try:
        endpoint = DirectSendEndpoint("127.0.0.1", server.port, "x" * 24, "/p/other")
        assert await mobile_model.options(endpoint) == {"providers": [{
            "provider": "nous", "name": "Nous", "models": ["nous/model"],
        }]}
        with pytest.raises(HmpError) as exc:
            await mobile_model.options(SimpleNamespace(
                host="example.com", port=server.port, api_key="x" * 24, path_prefix="",
            ))
        assert exc.value.code is ErrorCode.MODEL_UNAVAILABLE
    finally:
        await server.close()
