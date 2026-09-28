"""T027: self-revoke (PR7-3, one test per row) and operator revoke (PR7-1): atomic family revoke,
the last-device hint that prints Hermes commands and never runs them, and the next request of a
revoked device failing with `401 revoked` (SR-004).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import wire
from hmp_plugin.contract import CLOCK_SKEW_S, TAG_SELF_REVOKE, ErrorCode, HmpError
from hmp_plugin.revoke import last_device_hint, revoke_device, self_revoke

from .hmp_kit import Device, Env, code, get, pair, post, run


async def self_revoke_req(env: Env, client: TestClient, dev: Device, body: Any) -> tuple[int, Any]:
    return await post(client, "/devices/self/revoke", body, headers=env.headers(dev))


def _families(env: Env, device_id: str) -> list[Any]:
    with env.store.transaction() as conn:
        rows = conn.execute(
            "SELECT revoked_at FROM token_families WHERE device_id = ?", (device_id,)
        ).fetchall()
    return [r["revoked_at"] for r in rows]


# --------------------------------------------------------------------------------------------------
# PR7-3 table
# --------------------------------------------------------------------------------------------------


def test_pr73_row1_revoked_is_200_and_next_request_is_revoked(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        other = await pair(env, client)
        status, body = await self_revoke_req(env, client, dev, env.self_revoke_body(dev))
        assert (status, body) == (200, {})
        assert env.store.get_device(dev.device_id)["state"] == "REVOKED"
        assert all(r is not None for r in _families(env, dev.device_id))
        status, body = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(body)) == (401, "revoked")
        status, body = await post(client, "/auth/token", env.p5_body(dev))
        assert (status, code(body)) == (401, "revoked")
        # Only the calling device.
        assert env.store.get_device(other.device_id)["state"] == "ACTIVE"
        assert (await get(client, "/bots", headers=env.headers(other)))[0] == 200

    run(env, scenario)


def test_pr73_row2_stale_ts_or_bad_signature_is_401(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        for ts in (env.clock.now - CLOCK_SKEW_S - 1, env.clock.now + CLOCK_SKEW_S + 1):
            status, body = await self_revoke_req(env, client, dev, env.self_revoke_body(dev, ts=ts))
            assert (status, code(body)) == (401, "unauthenticated")
        bad = env.self_revoke_body(dev)
        bad["sig"] = Device().sign(b"x")  # another key
        status, body = await self_revoke_req(env, client, dev, bad)
        assert (status, code(body)) == (401, "unauthenticated")
        # A signature bound to another instance.
        from hmp_plugin import crypto

        other_iid = "a" * 52
        msg = crypto.transcript(TAG_SELF_REVOKE, other_iid, dev.device_id, env.clock.now)
        status, body = await self_revoke_req(
            env, client, dev, {"ts": env.clock.now, "sig": dev.sign(msg)}
        )
        assert (status, code(body)) == (401, "unauthenticated")
        assert env.store.get_device(dev.device_id)["state"] == "ACTIVE"

    run(env, scenario)


def test_pr73_row3_device_not_active_is_revoked(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        body = env.self_revoke_body(dev)
        revoke_device(env.store, dev.device_id, now=env.clock.now)
        status, reply = await self_revoke_req(env, client, dev, body)
        assert (status, code(reply)) == (401, "revoked")
        # Revoked after bearer authentication, before the revoking transaction: still `revoked`.
        with pytest.raises(HmpError) as err:
            self_revoke(env.store, env.iid, dev.device_id, body, now=env.clock.now)
        assert err.value.code is ErrorCode.REVOKED

    run(env, scenario)


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        {},
        {"ts": 1},
        {"sig": "AAAA"},
        {"ts": 1.5, "sig": "AAAA"},
        {"ts": True, "sig": "AAAA"},
        {"ts": "1", "sig": "AAAA"},
        {"ts": 1, "sig": "=="},
        {"ts": 1, "sig": 5},
    ],
)
def test_pr73_row4_malformed_is_400(tmp_path: Path, body: Any) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, reply = await self_revoke_req(env, client, dev, body)
        assert (status, code(reply)) == (400, "bad_request")
        assert env.store.get_device(dev.device_id)["state"] == "ACTIVE"

    run(env, scenario)


def test_self_revoke_requires_bearer_and_instance(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        status, body = await post(client, "/devices/self/revoke", env.self_revoke_body(dev))
        assert (status, code(body)) == (401, "wrong_instance")
        headers = {"HMP-Instance": env.iid}
        status, body = await post(
            client, "/devices/self/revoke", env.self_revoke_body(dev), headers=headers
        )
        assert (status, code(body)) == (401, "unauthenticated")
        assert env.store.get_device(dev.device_id)["state"] == "ACTIVE"

    run(env, scenario)


# --------------------------------------------------------------------------------------------------
# PR7-1 operator revoke
# --------------------------------------------------------------------------------------------------


def test_operator_revoke_is_atomic_and_next_request_is_revoked(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.clock.now += 5
        status, body = await post(client, "/pair/complete", env.p4_body(dev))  # a second family
        assert status == 200
        dev.access = body["access_token"]
        result = revoke_device(env.store, dev.device_id, now=env.clock.now)
        assert result.found and result.was_active and result.last_device
        assert env.store.get_device(dev.device_id)["state"] == "REVOKED"
        assert _families(env, dev.device_id) and all(
            r is not None for r in _families(env, dev.device_id)
        )
        status, body = await get(client, "/bots", headers=env.headers(dev))
        assert (status, code(body)) == (401, "revoked")
        assert revoke_device(env.store, dev.device_id, now=env.clock.now).found  # idempotent
        assert not revoke_device(env.store, "dev_" + "Z" * 22, now=env.clock.now).found

    run(env, scenario)


def test_operator_revoke_rolls_back_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import contextlib
    import sqlite3

    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        real = env.store.transaction

        class Failing:
            def __init__(self, conn: sqlite3.Connection) -> None:
                self.conn = conn

            def execute(self, sql: str, *args: Any) -> Any:
                if sql.startswith("UPDATE token_families"):
                    raise sqlite3.OperationalError("simulated failure")
                return self.conn.execute(sql, *args)

        @contextlib.contextmanager
        def failing() -> Any:
            with real() as conn:
                yield Failing(conn)

        monkeypatch.setattr(env.store, "transaction", failing)
        with pytest.raises(sqlite3.OperationalError):
            revoke_device(env.store, dev.device_id, now=env.clock.now)
        monkeypatch.setattr(env.store, "transaction", real)
        assert env.store.get_device(dev.device_id)["state"] == "ACTIVE"
        assert all(r is None for r in _families(env, dev.device_id))

    run(env, scenario)


def test_last_device_flag(tmp_path: Path) -> None:
    env = Env(tmp_path)
    user = "hmpu_" + "1" * 32

    async def scenario(client: TestClient) -> None:
        a, b = Device(), Device()
        for dev in (a, b):
            offer = env.offer()
            _, body = await post(client, "/pair/request", env.p2_body(dev, offer))
            dev.pairing_id = body["pairing_id"]
            dev.ni = wire.b64u_decode(body["ni"], length=32)
            dev.device_id = env.confirm(dev, user_id=user)
        assert not revoke_device(env.store, a.device_id, now=env.clock.now).last_device
        last = revoke_device(env.store, b.device_id, now=env.clock.now)
        assert last.last_device and last.user_id == user

    run(env, scenario)


def test_last_device_hint_prints_commands_and_never_runs_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("HMP must never run a Hermes command")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    user = "hmpu_" + "2" * 32
    lines = last_device_hint(user, ["work", "home", "work", "odd name"], env_allowlisted=True)
    assert lines[:3] == [
        f"hermes -p home pairing revoke hmp {user}",
        f"hermes -p 'odd name' pairing revoke hmp {user}",
        f"hermes -p work pairing revoke hmp {user}",
    ]
    assert "allowlist" in lines[3]
    assert last_device_hint(user, [], env_allowlisted=False) == []
