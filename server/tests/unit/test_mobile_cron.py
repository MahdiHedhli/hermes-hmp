"""Mobile cron boundary: owner gate, fixed body, profile scope, bounded loopback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import mobile_cron
from hmp_plugin.compat import compute_read_bridge_fingerprint
from hmp_plugin.contract import AuthzState, DirectSendEndpoint, ErrorCode, HmpError

from .hmp_kit import Env, get, pair, post, run

_TEST_KEY = "x" * 24


def _job(**changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "id": "a" * 12,
        "name": "Morning brief",
        "prompt": "Summarize status",
        "schedule_display": "every 1h",
        "enabled": False,
        "state": "paused",
        "next_run_at": None,
        "last_run_at": None,
        "last_status": None,
        "script": "/private/server-only.py",
        "last_error": "internal secret-bearing error",
    }
    result.update(changes)
    return result


def test_create_accepts_only_bounded_fields_and_forces_paused_local() -> None:
    assert mobile_cron.create_body(
        {"name": " brief ", "schedule": " every 1h ", "prompt": " summarize "}
    ) == {
        "name": "brief", "schedule": "every 1h", "prompt": "summarize",
        "deliver": "local", "paused": True,
    }
    for body in (
        {"name": "a", "schedule": "every 1h", "prompt": "p", "script": "sh"},
        {"name": "a", "schedule": "every 1h", "prompt": " "},
        {"name": "a", "schedule": "every 1h", "prompt": "p", "deliver": "origin"},
    ):
        with pytest.raises(HmpError) as exc:
            mobile_cron.create_body(body)
        assert exc.value.code is ErrorCode.BAD_REQUEST


def test_job_projection_omits_host_internals() -> None:
    projected = mobile_cron.project_job(_job())
    assert projected == {
        "id": "a" * 12, "name": "Morning brief", "prompt": "Summarize status",
        "schedule": "every 1h", "enabled": False, "state": "paused",
        "next_run_at": None, "last_run_at": None, "last_status": None,
    }
    assert "internal secret" not in str(projected)
    poisoned = mobile_cron.project_job(_job(
        last_status="key=synthetic-secret", state="x/y", next_run_at="not-a-time",
    ))
    assert poisoned["last_status"] is None
    assert poisoned["state"] is None
    assert poisoned["next_run_at"] is None


def test_unqualified_build_fails_closed(tmp_path: Path) -> None:
    assert not mobile_cron.qualified_build(root=tmp_path)


def test_cron_fingerprint_matches_only_exact_reviewed_bytes(tmp_path: Path) -> None:
    (tmp_path / "api.py").write_text("approved", encoding="utf-8")
    fingerprint = compute_read_bridge_fingerprint(tmp_path, ["api.py"])
    builds = tmp_path / "builds.json"
    builds.write_text(json.dumps({
        "format": 1, "bridge_files": ["api.py"], "builds": [{
            "fingerprint": fingerprint, "git_sha": None, "qualified_by": "test",
        }],
    }), encoding="utf-8")
    assert mobile_cron.qualified_build(root=tmp_path, builds_path=builds)
    (tmp_path / "api.py").write_text("changed", encoding="utf-8")
    assert not mobile_cron.qualified_build(root=tmp_path, builds_path=builds)
    builds.write_text(json.dumps({
        "format": 1, "bridge_files": ["/absolute.py"], "builds": [],
    }), encoding="utf-8")
    assert not mobile_cron.qualified_build(root=tmp_path, builds_path=builds)


def test_non_owner_and_disabled_flag_never_reach_upstream(tmp_path: Path, monkeypatch) -> None:
    env = Env(tmp_path)
    calls: list[str] = []
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.bridge.direct_send_endpoint = lambda p: calls.append(p)
    env.ctx.cron_qualified = lambda: True
    env.ctx.cron_flag = lambda: True

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, _ = await get(client, "/bots/default/jobs", headers=env.headers(dev))
        assert status == 404
        assert calls == []
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        env.ctx.cron_flag = lambda: False
        status, _ = await get(client, "/bots/default/jobs", headers=env.headers(dev))
        assert status == 503
        assert calls == []
        env.ctx.cron_flag = lambda: True
        env.bridge.authz_state = lambda *_: AuthzState.PENDING_OPERATOR
        status, _ = await get(client, "/bots/default/jobs", headers=env.headers(dev))
        assert status == 403
        assert calls == []
        env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
        env.ctx.cron_qualified = lambda: False
        status, _ = await get(client, "/bots/default/jobs", headers=env.headers(dev))
        assert status == 503
        assert calls == []

    run(env, scenario)


def test_owner_route_uses_fixed_loopback_profile_and_projects_result(tmp_path: Path) -> None:
    env = Env(tmp_path)
    received: list[tuple[str, str, dict[str, object] | None]] = []
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.cron_qualified = lambda: True
    env.ctx.cron_flag = lambda: True

    async def upstream(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == f"Bearer {_TEST_KEY}"
        body = await request.json() if request.method == "POST" else None
        received.append((request.method, request.path, body))
        if request.method == "GET":
            assert request.query == {"include_disabled": "true"}
            return web.json_response({"jobs": [_job()]})
        return web.json_response({"job": _job()})

    async def scenario(client: TestClient) -> None:
        upstream_app = web.Application()
        upstream_app.router.add_get("/p/default/api/jobs", upstream)
        upstream_app.router.add_post("/p/default/api/jobs", upstream)
        upstream_server = TestServer(upstream_app)
        await upstream_server.start_server()
        try:
            env.bridge.direct_send_endpoint = lambda profile: DirectSendEndpoint(
                host="127.0.0.1", port=upstream_server.port,
                api_key=_TEST_KEY, path_prefix="/p/default",
            )
            dev = await pair(env, client)
            env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
            status, data = await get(client, "/bots/default/jobs", headers=env.headers(dev))
            assert status == 200
            assert data == {"jobs": [mobile_cron.project_job(_job())]}
            status, data = await post(
                client, "/bots/default/jobs",
                {"name": "Morning brief", "schedule": "every 1h", "prompt": "Summarize status"},
                headers=env.headers(dev),
            )
            assert status == 200
            assert data == {"job": mobile_cron.project_job(_job())}
            assert received == [
                ("GET", "/p/default/api/jobs", None),
                ("POST", "/p/default/api/jobs", {
                    "name": "Morning brief", "schedule": "every 1h",
                    "prompt": "Summarize status", "deliver": "local", "paused": True,
                }),
            ]
        finally:
            await upstream_server.close()

    run(env, scenario)


@pytest.mark.asyncio
async def test_loopback_refuses_redirect_and_non_loopback_host() -> None:
    endpoint = SimpleNamespace(host="example.com", port=443, api_key="synthetic", path_prefix="")
    with pytest.raises(HmpError) as exc:
        await mobile_cron.call(endpoint, method="GET")
    assert exc.value.code is ErrorCode.CRON_UNAVAILABLE

    async def redirect(_request: web.Request) -> web.Response:
        raise web.HTTPFound("http://example.com")

    app = web.Application()
    app.router.add_get("/api/jobs", redirect)
    server = TestServer(app)
    await server.start_server()
    try:
        endpoint = SimpleNamespace(
            host="127.0.0.1", port=server.port,
            api_key="synthetic", path_prefix="",
        )
        with pytest.raises(HmpError) as exc:
            await mobile_cron.call(endpoint, method="GET")
        assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_loopback_bounds_errors_response_size_and_time(monkeypatch) -> None:
    async def upstream(request: web.Request) -> web.Response:
        if request.path.endswith("/oversize"):
            return web.Response(body=b"x" * (1_048_576 + 1))
        if request.path.endswith("/slow"):
            await asyncio.sleep(0.2)
            return web.json_response({"jobs": []})
        return web.Response(status=401, text="synthetic key failure")

    app = web.Application()
    app.router.add_get("/api/jobs", upstream)
    app.router.add_get("/p/oversize/api/jobs", upstream)
    app.router.add_get("/p/slow/api/jobs", upstream)
    server = TestServer(app)
    await server.start_server()
    try:
        for prefix in ("", "/p/oversize"):
            endpoint = SimpleNamespace(
                host="127.0.0.1", port=server.port,
                api_key=_TEST_KEY, path_prefix=prefix,
            )
            with pytest.raises(HmpError) as exc:
                await mobile_cron.call(endpoint, method="GET")
            assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
            assert "synthetic key failure" not in str(exc.value)
        monkeypatch.setattr(mobile_cron, "_TOTAL_TIMEOUT_S", 0.05)
        endpoint = SimpleNamespace(
            host="127.0.0.1", port=server.port,
            api_key=_TEST_KEY, path_prefix="/p/slow",
        )
        with pytest.raises(HmpError) as exc:
            await mobile_cron.call(endpoint, method="GET")
        assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
    finally:
        await server.close()


def test_list_rejects_unbounded_job_count() -> None:
    with pytest.raises(HmpError) as exc:
        mobile_cron.project_response("GET", {"jobs": [_job()] * 101})
    assert exc.value.code is ErrorCode.CRON_UNAVAILABLE
