"""Pre-dispatch causals use only isolated stores and fake native mutations."""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import server, wire
from hmp_plugin.auth import Authenticator
from hmp_plugin.contract import PATH_PREFIX, AuthzState, ErrorCode, HmpError

from .hmp_kit import Env, pair, run


@pytest.mark.parametrize("operation", ["create", "edit", "model"])
@pytest.mark.parametrize("boundary", ["body", "worker"])
@pytest.mark.parametrize("change,status", [
    ("none", 200), ("controls", 404), ("family", 401), ("bot", 403),
    ("flag", 503), ("generation", 503), ("bridge", 503),
])
def test_write_requires_current_authority_at_body_and_worker(
    tmp_path: Path, monkeypatch, operation, boundary, change, status,
):
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.bridge.direct_send_endpoint = lambda _: object()
    env.ctx.cron_flag = env.ctx.model_flag = lambda: True
    env.ctx.cron_available = env.ctx.model_available = lambda: True
    calls = []
    raw_job = {"id": "abcdef123456", "name": "synthetic", "prompt": "synthetic",
               "schedule_display": "every 1h", "enabled": False}

    def mutation(*args):
        calls.append(args)
        return {"provider": "synthetic", "model": "new"} if operation == "model" else raw_job

    env.bridge.create_mobile_cron = mutation
    env.bridge.edit_mobile_cron = mutation
    env.bridge.set_profile_default_model = mutation

    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        headers = env.headers(dev)
        who = Authenticator(env.store, env.ctx.iid, env.ctx.now).authenticate(
            headers["Authorization"], headers["HMP-Instance"],
        )
        original_bridge = env.ctx.bridge

        def change_authority():
            if change == "controls":
                env.store.set_owner_controls(dev.device_id, allowed=False, now=env.ctx.now())
            elif change == "family":
                env.store.revoke_family(who.family_id, now=env.ctx.now())
            elif change == "bot":
                env.bridge.authz_state = lambda *_: AuthzState.PENDING_OPERATOR
            elif change == "flag":
                env.ctx.cron_flag = env.ctx.model_flag = lambda: False
            elif change == "generation":
                env.ctx.readiness_generation = "f" * 32
            elif change == "bridge":
                env.ctx.bridge = object()

        if boundary == "body":
            original_read = server.read_json_body

            async def body(request):
                result = await original_read(request)
                change_authority()
                return result

            monkeypatch.setattr(server, "read_json_body", body)
        else:
            original_thread = asyncio.to_thread

            async def thread(function, *args, **kwargs):
                if isinstance(getattr(function, "__self__", None), server._ControlsNativeWrite):
                    change_authority()
                return await original_thread(function, *args, **kwargs)

            monkeypatch.setattr(asyncio, "to_thread", thread)
        if operation == "model":
            method, path = "PUT", "/bots/default/model/default"
            body = {"provider": "synthetic", "model": "new"}
        elif operation == "edit":
            method, path = "PATCH", "/bots/default/jobs/abcdef123456"
            body = {"prompt": "synthetic"}
        else:
            method, path = "POST", "/bots/default/jobs"
            body = {"name": "synthetic", "prompt": "synthetic", "schedule": "every 1h"}
        try:
            response = await client.request(method, PATH_PREFIX + path,
                                            data=wire.dump_json(body), headers=headers)
            assert response.status == status
            assert len(calls) == (1 if status == 200 else 0)
            if calls:
                assert calls[0][0] == "default"
        finally:
            env.ctx.bridge = original_bridge

    run(env, scenario)


@pytest.mark.asyncio
async def test_cancelled_worker_never_dispatches_or_retries():
    async def wait():
        await asyncio.Event().wait()

    task = asyncio.create_task(wait())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    calls = []
    scope = SimpleNamespace(unavailable=ErrorCode.MODEL_UNAVAILABLE, check=lambda: None)
    handoff = server._ControlsNativeWrite(scope, task, lambda: calls.append(True), ())
    with pytest.raises(asyncio.CancelledError):
        await asyncio.to_thread(handoff.run)
    assert handoff.attempted and not handoff.started and not calls
    with pytest.raises(HmpError):
        handoff.run()
    assert not calls


@pytest.mark.asyncio
async def test_native_failure_retains_started_and_never_retries():
    calls = []
    scope = SimpleNamespace(unavailable=ErrorCode.MODEL_UNAVAILABLE, check=lambda: None)

    def native():
        calls.append(True)
        raise ValueError("synthetic-native-failure")

    handoff = server._ControlsNativeWrite(scope, asyncio.current_task(), native, ())
    ok, error = await asyncio.to_thread(handoff.run)
    assert not ok and isinstance(error, ValueError)
    assert handoff.attempted and handoff.started and calls == [True]
    with pytest.raises(HmpError):
        handoff.run()
    assert calls == [True]
    assert repr(handoff) == "<ControlsNativeWrite redacted>"


def test_removed_context_is_fixed_preflight_refusal(tmp_path):
    env = Env(tmp_path)
    app = env.app()
    scope = server._ControlsRequestScope(
        env.ctx, env.ctx.store, env.ctx.bridge, env.ctx.identity, env.ctx.iid,
        env.ctx.readiness_generation, "default", None, None, None, "model", app,
    )
    try:
        del app[server.CTX_KEY]
        with pytest.raises(HmpError) as exc:
            scope.check()
        assert exc.value.code is ErrorCode.MODEL_UNAVAILABLE
    finally:
        env.store.close()
