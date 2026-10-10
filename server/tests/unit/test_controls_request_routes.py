"""Route-level Controls request tests use only a synthetic isolated Store and paired devices."""
from __future__ import annotations

import uuid
from pathlib import Path

from aiohttp.test_utils import TestClient

from hmp_plugin import controls_request_routes
from hmp_plugin.auth import Authenticator
from hmp_plugin.contract import AuthzState
from .hmp_kit import Env, code, get, pair, post, run, url

PREFIX = "/devices/self/controls-requests"


def _enabled(tmp_path: Path) -> Env:
    env = Env(tmp_path)
    env.ctx.controls_requests_enabled = True
    env.ctx.cron_available = lambda: True
    env.ctx.cron_flag = lambda: True
    env.ctx.model_available = lambda: True
    env.ctx.model_flag = lambda: True
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    return env


def _body(cid: str | None = None, *, profile: str = "default", feature: str = "jobs") -> dict:
    return {"client_request_id": cid or str(uuid.uuid4()),
            "bot_profile": profile, "feature": feature}


def test_disabled_registration_is_absent(tmp_path: Path) -> None:
    env = Env(tmp_path)
    async def scenario(client: TestClient) -> None:
        status, _ = await get(client, PREFIX + "/capabilities")
        assert status == 404
        status, _ = await post(client, PREFIX, _body())
        assert status == 404
    run(env, scenario)


def test_create_retry_recovery_cancel_and_history_only(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = env.headers(dev)
        status, cap = await get(client, PREFIX + "/capabilities", headers=headers)
        assert status == 200
        assert cap == {"protocol": 1, "supported": True,
                       "scope": "device_jobs_models_now_and_future_authorized_bots",
                       "ttl_seconds": 600}
        body = _body()
        status, first = await post(client, PREFIX, body, headers=headers)
        assert status == 202
        assert set(first) == {"protocol", "request_id", "client_request_id", "bot_profile",
                              "feature", "state", "expires_at", "scope",
                              "effective_controls", "controls_revision"}
        assert first["state"] == "PENDING" and first["client_request_id"] == body["client_request_id"]
        assert first["effective_controls"] == "missing"
        status, repeat = await post(client, PREFIX, body, headers=headers)
        assert status == 200 and repeat["request_id"] == first["request_id"]
        status, conflict = await post(client, PREFIX, {**body, "feature": "models"}, headers=headers)
        assert status == 409 and code(conflict) == "idempotency_conflict"
        status, by_client = await get(client, PREFIX + "/by-client-id/" + body["client_request_id"], headers=headers)
        assert status == 200 and by_client["request_id"] == first["request_id"]
        rid = first["request_id"]
        status, by_id = await get(client, PREFIX + "/" + rid, headers=headers)
        assert status == 200 and by_id["request_id"] == rid
        status, cancelled = await post(client, PREFIX + "/" + rid + "/cancel", {}, headers=headers)
        assert status == 200 and cancelled["state"] == "CANCELLED"
        status, again = await post(client, PREFIX + "/" + rid + "/cancel", {}, headers=headers)
        assert status == 200 and again["state"] == "CANCELLED"
        assert env.store.readiness_owner_controls_value(dev.device_id) is None
    run(env, scenario)


def test_foreign_origin_revocation_and_clock_refuse(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        first = await pair(env, client)
        second = await pair(env, client)
        body = _body()
        status, created = await post(client, PREFIX, body, headers=env.headers(first))
        assert status == 202
        rid = created["request_id"]
        for path in (PREFIX + "/" + rid, PREFIX + "/by-client-id/" + body["client_request_id"]):
            status, reply = await get(client, path, headers=env.headers(second))
            assert status == 404 and code(reply) == "not_found"
        status, reply = await post(client, PREFIX + "/" + rid + "/cancel", {}, headers=env.headers(second))
        assert status == 404 and code(reply) == "not_found"
        env.clock.now -= 1
        status, reply = await post(client, PREFIX, _body(), headers=env.headers(first))
        assert status == 503 and code(reply) == "controls_request_unavailable"
        env.clock.now += 1
        first_headers = env.headers(first)
        who = Authenticator(env.store, env.iid, env.ctx.now).authenticate(
            first_headers["Authorization"], first_headers["HMP-Instance"]
        )
        env.store.revoke_family(who.family_id, env.clock.now)
        status, reply = await get(client, PREFIX + "/" + rid, headers=env.headers(first))
        assert status == 401 and code(reply) == "revoked"
    run(env, scenario)


def test_closed_body_ids_and_no_remote_decision(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = env.headers(dev)
        valid = _body()
        cases = (
            {**valid, "device_id": dev.device_id},
            {**valid, "allow": True},
            {**valid, "client_request_id": "x"},
            {**valid, "bot_profile": "../bad"},
            {**valid, "feature": "admin"},
        )
        for bad in cases:
            status, reply = await post(client, PREFIX, bad, headers=headers)
            assert status == 400 and code(reply) == "bad_request"
        status, reply = await post(client, PREFIX, b"{" + b" " * 513 + b"}", headers=headers)
        assert status == 400 and code(reply) == "bad_request"
        duplicate = (b'{"client_request_id":"' + valid["client_request_id"].encode() +
                     b'","bot_profile":"default","feature":"jobs","feature":"models"}')
        status, reply = await post(client, PREFIX, duplicate, headers=headers)
        assert status == 400 and code(reply) == "bad_request"
        status, reply = await get(client, PREFIX + "/" + "A" * 32, headers=headers)
        assert status == 400 and code(reply) == "bad_request"
        status, _ = await post(client, PREFIX + "/allow", {}, headers=headers)
        assert status in (404, 405)
        status, reply = await get(client, PREFIX + "/capabilities?admin=true", headers=headers)
        assert status == 400 and code(reply) == "bad_request"
    run(env, scenario)


def test_bot_authorization_and_effective_value_are_independent(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = env.headers(dev)
        env.bridge.authz_state = lambda *_: AuthzState.NOT_ROUTED
        status, reply = await post(client, PREFIX, _body(), headers=headers)
        assert status == 409 and code(reply) == "not_routed"
        env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
        body = _body()
        status, pending = await post(client, PREFIX, body, headers=headers)
        assert status == 202 and pending["effective_controls"] == "missing"
        assert env.store.set_owner_controls(dev.device_id, allowed=True, now=env.clock.now)
        status, history = await get(client, PREFIX + "/" + pending["request_id"], headers=headers)
        assert status == 200
        assert history["state"] == "CONFLICT" and history["effective_controls"] == "granted"
        assert history["controls_revision"] is not None
        env.ctx.readiness_owner_device_ids = lambda: None  # malformed fallback is never a grant
        # An explicit Store row still takes precedence over the malformed legacy reader.
        status, explicit = await get(client, PREFIX + "/" + pending["request_id"], headers=headers)
        assert status == 200 and explicit["effective_controls"] == "granted"
    run(env, scenario)


def test_rate_quota_and_schema_loss_fail_closed(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = env.headers(dev)
        status, _ = await post(client, PREFIX, _body(), headers=headers)
        assert status == 202
        status, reply = await post(client, PREFIX, _body(), headers=headers)
        assert status == 429 and code(reply) == "rate_limited"
        with env.store.transaction() as conn:
            conn.execute("DROP TABLE controls_requests")  # synthetic isolated Store only
        status, reply = await get(client, PREFIX + "/capabilities", headers=headers)
        assert status == 503 and code(reply) == "controls_request_unavailable"
    run(env, scenario)


def test_revocation_during_body_await_never_inserts(tmp_path: Path, monkeypatch) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        headers = env.headers(dev)
        who = Authenticator(env.store, env.iid, env.ctx.now).authenticate(
            headers["Authorization"], headers["HMP-Instance"]
        )
        original = controls_request_routes._body_bytes
        async def revoke_after_read(request):
            body = await original(request)
            env.store.revoke_family(who.family_id, env.clock.now)
            return body
        monkeypatch.setattr(controls_request_routes, "_body_bytes", revoke_after_read)
        status, reply = await post(client, PREFIX, _body(), headers=headers)
        assert status == 401 and code(reply) == "revoked"
        with env.store.transaction() as conn:
            assert conn.execute("SELECT COUNT(*) FROM controls_requests").fetchone()[0] == 0
    run(env, scenario)


def test_host_denial_between_insert_and_record_read_returns_200(tmp_path: Path, monkeypatch) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        original = controls_request_routes._record_by_request
        seen = False
        def host_decides_before_read(ctx, origin, request_id, now):
            nonlocal seen
            if not seen:
                seen = True
                decision = controls_request_routes.ControlsRequestStore(ctx.store).decide(
                    request_id, allow=False, now=now, current_iid=ctx.iid,
                    precommit_external_verified=False,
                )
                assert decision.code == "denied"  # synthetic Store interleaving, no host TTY
            return original(ctx, origin, request_id, now)
        monkeypatch.setattr(controls_request_routes, "_record_by_request", host_decides_before_read)
        status, history = await post(client, PREFIX, _body(), headers=env.headers(dev))
        assert status == 200 and history["state"] == "DENIED" and seen
    run(env, scenario)


def test_legacy_reader_host_write_downgrades_effective_hint(tmp_path: Path) -> None:
    env = _enabled(tmp_path)
    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        def races_controls_write():
            assert env.store.set_owner_controls(dev.device_id, allowed=True, now=env.clock.now)
            return frozenset({dev.device_id})
        env.ctx.readiness_owner_device_ids = races_controls_write
        status, history = await post(client, PREFIX, _body(), headers=env.headers(dev))
        assert status == 202 and history["state"] == "PENDING"
        assert history["effective_controls"] == "unknown"
        assert history["controls_revision"] is None
    run(env, scenario)
