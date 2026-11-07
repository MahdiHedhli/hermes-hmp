"""Causal late-revocation checks on jobs/model read responses, synthetic only."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import mobile_cron, mobile_model, server
from hmp_plugin.auth import Authenticator
from hmp_plugin.contract import AuthzState

from .hmp_kit import Env, get, pair, run


@pytest.mark.parametrize("route", ["jobs", "model/default", "model/options"])
@pytest.mark.parametrize("change,expected", [
    ("none", 200), ("controls", 404), ("family", 401), ("bot", 403),
    ("flag", 503), ("generation", 503), ("bridge", 503), ("store", 503),
    ("identity", 503), ("bot_callback_bridge", 503),
    ("final_auth_flag", 503), ("final_auth_identity", 503),
    ("final_auth_bot", 403), ("final_owner_flag", 503),
])
def test_read_result_requires_original_current_authority(
    tmp_path: Path, monkeypatch, route: str, change: str, expected: int,
) -> None:
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.bridge.direct_send_endpoint = lambda _: object()
    env.ctx.cron_flag = env.ctx.model_flag = lambda: True
    env.ctx.cron_available = env.ctx.model_available = lambda: True
    reads: list[str] = []

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        headers = env.headers(dev)
        who = Authenticator(env.store, env.ctx.iid, env.ctx.now).authenticate(
            headers["Authorization"], headers["HMP-Instance"],
        )

        def complete():
            reads.append(route)
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
            elif change == "store":
                env.ctx.store = object()
            elif change == "identity":
                env.ctx.identity = object()
            elif change == "bot_callback_bridge":
                def drift(*_args):
                    env.ctx.bridge = object()
                    return AuthzState.AUTHORIZED
                env.bridge.authz_state = drift
            elif change.startswith("final_"):
                count = [0]

                def revoke():
                    if change.endswith("flag"):
                        env.ctx.cron_flag = env.ctx.model_flag = lambda: False
                    elif change.endswith("identity"):
                        monkeypatch.setattr(env.identity, "still_current", lambda: False)
                    else:
                        env.bridge.authz_state = lambda *_: AuthzState.PENDING_OPERATOR

                if change.startswith("final_auth"):
                    original_auth = Authenticator.authenticate

                    def auth(self, *args):
                        value = original_auth(self, *args)
                        count[0] += 1
                        if count[0] == 2:
                            revoke()
                        return value

                    monkeypatch.setattr(Authenticator, "authenticate", auth)
                else:
                    original_owner = env.ctx.is_owner_device

                    def owner(device_id):
                        value = original_owner(device_id)
                        count[0] += 1
                        if count[0] == 2:
                            revoke()
                        return value

                    monkeypatch.setattr(env.ctx, "is_owner_device", owner)
            return {"provider": "synthetic", "model": "private-result"}

        async def jobs(*_args, **_kwargs):
            await asyncio.sleep(0)
            complete()
            return {"jobs": []}

        async def options(*_args):
            await asyncio.sleep(0)
            complete()
            return {"providers": []}

        monkeypatch.setattr(mobile_cron, "call", jobs)
        monkeypatch.setattr(mobile_model, "options", options)
        env.bridge.profile_default_model = lambda _: complete()
        # Scope mutation is intentional; restore original dependencies for fixture cleanup.
        original = (env.ctx.store, env.ctx.bridge, env.ctx.identity)
        try:
            status, body = await get(client, "/bots/default/" + route, headers=headers)
            assert status == expected
            assert reads == [route]
            if expected != 200:
                assert "private-result" not in str(body)
                assert "jobs" not in body and "providers" not in body
        finally:
            env.ctx.store, env.ctx.bridge, env.ctx.identity = original

    run(env, scenario)


@pytest.mark.parametrize("route", ["jobs", "model/options"])
def test_endpoint_scope_change_prevents_subsequent_read(tmp_path: Path, monkeypatch, route):
    env = Env(tmp_path)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.cron_flag = env.ctx.model_flag = lambda: True
    env.ctx.cron_available = env.ctx.model_available = lambda: True
    reads = []

    def endpoint(_):
        env.ctx.readiness_generation = "f" * 32
        return object()

    env.bridge.direct_send_endpoint = endpoint

    async def unexpected(*_args, **_kwargs):
        reads.append(True)
        return {}

    monkeypatch.setattr(mobile_cron, "call", unexpected)
    monkeypatch.setattr(mobile_model, "options", unexpected)

    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, _ = await get(client, "/bots/default/" + route, headers=env.headers(dev))
        assert status == 503 and reads == []

    run(env, scenario)


def test_scope_repr_redacts_headers(tmp_path):
    # Even failure/reporting code must not accidentally render retained credentials.
    scope = server._ControlsRequestScope(*(["synthetic-secret"] * 12))
    assert repr(scope) == "<ControlsRequestScope redacted>"


@pytest.mark.parametrize("route", ["jobs", "model/default", "model/options"])
@pytest.mark.parametrize("boundary", ["owner", "limiter"])
def test_initial_callback_cannot_redirect_native_authorization(
    tmp_path, monkeypatch, route, boundary,
):
    env = Env(tmp_path)
    native = []
    env.bridge.authz_state = lambda *_: native.append("auth") or AuthzState.AUTHORIZED
    env.bridge.direct_send_endpoint = lambda _: native.append("endpoint")
    env.ctx.cron_flag = env.ctx.model_flag = lambda: True
    env.ctx.cron_available = env.ctx.model_available = lambda: True

    async def scenario(client):
        dev = await pair(env, client)
        original_bridge = env.ctx.bridge
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        if boundary == "owner":
            def owner(_):
                env.ctx.bridge = object()
                return True
            monkeypatch.setattr(env.ctx, "is_owner_device", owner)
        else:
            original_check = env.ctx.limiter.check

            def check(*args):
                original_check(*args)
                env.ctx.bridge = object()
            monkeypatch.setattr(env.ctx.limiter, "check", check)
        try:
            status, _ = await get(client, "/bots/default/" + route, headers=env.headers(dev))
            assert status == 503 and native == []
        finally:
            env.ctx.bridge = original_bridge

    run(env, scenario)
