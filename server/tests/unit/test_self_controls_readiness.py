"""Own-device route over real Store/auth; synthetic local HTTP only."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import server
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import ErrorCode

from .hmp_kit import Env, code, get, pair, run, url

PATH = "/devices/self/controls-readiness"


@pytest.mark.parametrize(
    ("override", "owner", "expected"),
    [
        (True, False, "granted"),
        (False, True, "missing"),
        (None, True, "granted"),
        (None, False, "missing"),
    ],
)
def test_closed_own_projection_no_writes_or_profile_reads(
    tmp_path: Path, override, owner, expected
):
    env = Env(tmp_path)

    async def scenario(client: TestClient):
        dev = await pair(env, client)
        if override is not None:
            assert env.store.set_owner_controls(dev.device_id, allowed=override, now=env.clock.now)
        loop_thread = threading.get_ident()

        def owners():
            assert threading.get_ident() != loop_thread
            return frozenset([dev.device_id]) if owner else frozenset()

        env.ctx.readiness_owner_device_ids = owners

        def forbidden(*args, **kwargs):
            raise AssertionError("unrelated authority was accessed")

        env.bridge.authz_state = forbidden
        env.ctx.readiness_settings = forbidden
        before = env.store._require_conn().total_changes
        resp = await client.get(url(PATH), headers=env.headers(dev))
        assert resp.status == 200
        assert resp.headers["Cache-Control"] == "no-store"
        raw = await resp.read()
        assert len(raw) <= 512
        assert await resp.json() == {
            "protocol": 1,
            "generation": env.ctx.readiness_generation,
            "entitlement": expected,
            "scope": ["jobs", "model"],
            "api_reachability": "not_probed",
        }
        assert env.store._require_conn().total_changes == before

    run(env, scenario)


def test_exact_get_compat_exception_preserves_feature_gates(tmp_path: Path):
    env = Env(tmp_path)
    env.ctx.readiness_owner_device_ids = lambda: frozenset()

    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.compat = CompatResult(CompatStatus.UNSUPPORTED)
        status, data = await get(client, PATH, headers=env.headers(dev))
        assert status == 200 and data["entitlement"] == "missing"
        for method, path in [
            ("POST", PATH),
            ("GET", "/bots/default/readiness"),
            ("GET", PATH + "/other"),
        ]:
            resp = await client.request(method, url(path), headers=env.headers(dev))
            assert resp.status != 200

    run(env, scenario)


@pytest.mark.parametrize(
    "case",
    [
        "wrong_instance",
        "missing_auth",
        "duplicate_auth",
        "duplicate_instance",
        "refresh",
        "expired",
        "revoked",
        "family",
    ],
)
def test_definitive_auth_refusals(tmp_path: Path, case):
    env = Env(tmp_path)
    env.ctx.readiness_owner_device_ids = lambda: frozenset()

    async def scenario(client):
        dev = await pair(env, client)
        headers = list(env.headers(dev).items())
        expected = "unauthenticated"
        if case == "wrong_instance":
            headers = [("Authorization", "Bearer " + dev.access), ("HMP-Instance", "wrong")]
            expected = "wrong_instance"
        elif case == "missing_auth":
            headers = [("HMP-Instance", env.iid)]
        elif case == "duplicate_auth":
            headers.append(headers[0])
        elif case == "duplicate_instance":
            headers.append(headers[1])
            expected = "wrong_instance"
        elif case == "refresh":
            headers[0] = ("Authorization", "Bearer " + dev.refresh)
        elif case == "expired":
            env.clock.now += 86400
        elif case == "revoked":
            env.store.set_device_state(dev.device_id, "REVOKED")
            expected = "revoked"
        elif case == "family":
            env.store.revoke_families_for_device(dev.device_id, env.clock.now)
            expected = "revoked"
        status, data = await get(client, PATH, headers=headers)
        assert status == 401 and code(data) == expected
        assert "scope" not in data

    run(env, scenario)


@pytest.mark.parametrize("case", ["query", "body"])
def test_empty_get_grammar(tmp_path: Path, case):
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)
        resp = await client.get(
            url(PATH + ("?device=other" if case == "query" else "")),
            headers=env.headers(dev),
            data=b"x" if case == "body" else None,
        )
        assert resp.status == 400

    run(env, scenario)


@pytest.mark.parametrize("case", ["missing_source", "malformed_source", "throw", "clock"])
def test_unknown_source_is_fixed_unavailable(tmp_path: Path, case):
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)
        if case == "malformed_source":
            env.ctx.readiness_owner_device_ids = lambda: []
        elif case == "throw":

            def unavailable():
                raise RuntimeError("synthetic confidential diagnostic")

            env.ctx.readiness_owner_device_ids = unavailable
        elif case == "clock":
            env.ctx.clock = lambda: True
        status, data = await get(client, PATH, headers=env.headers(dev))
        assert status == 503
        assert data == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"}
        }

    run(env, scenario)


@pytest.mark.parametrize("case", ["controls", "generation", "revoked_first", "revoked_second"])
def test_discard_changed_authority_during_controls(tmp_path: Path, case):
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)
        calls = 0
        original = env.store.readiness_owner_controls_value

        def read(device_id):
            nonlocal calls
            calls += 1
            value = original(device_id)
            if case == "controls" and calls == 1:
                env.store.set_owner_controls(device_id, allowed=True, now=env.clock.now)
            elif case == "generation" and calls == 1:
                env.ctx.readiness_generation = "f" * 32
            elif ((case == "revoked_first" and calls == 1)
                  or (case == "revoked_second" and calls == 2)):
                env.store.set_device_state(device_id, "REVOKED")
            return value

        env.store.readiness_owner_controls_value = read
        env.ctx.readiness_owner_device_ids = lambda: frozenset()
        status, data = await get(client, PATH, headers=env.headers(dev))
        assert status == (401 if case.startswith("revoked") else 503)
        assert code(data) == ("revoked" if case.startswith("revoked") else "readiness_unavailable")

    run(env, scenario)


def test_rate_limit_precedes_controls_and_is_shared(tmp_path: Path):
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)

        def forbidden(_):
            raise AssertionError("rate-limited request read controls")

        env.store.readiness_owner_controls_value = forbidden
        for _ in range(30):
            env.ctx.limiter.check("readiness", dev.device_id, 30, env.clock.now)
        status, data = await get(client, PATH, headers=env.headers(dev))
        assert status == 429 and code(data) == ErrorCode.RATE_LIMITED

    run(env, scenario)


@pytest.mark.parametrize("change", ["generation", "context"])
def test_postawait_origin_fence(tmp_path: Path, monkeypatch, change):
    env = Env(tmp_path)
    entered = threading.Event()
    release = threading.Event()

    async def scenario(client):
        dev = await pair(env, client)
        calls = 0

        def owners():
            nonlocal calls
            calls += 1
            if calls == 2:
                entered.set()
                assert release.wait(3)
            return frozenset()

        env.ctx.readiness_owner_device_ids = owners
        pending = asyncio.create_task(get(client, PATH, headers=env.headers(dev)))
        for _ in range(200):
            if entered.is_set():
                break
            await asyncio.sleep(0.005)
        assert entered.is_set()
        if change == "generation":
            env.ctx.readiness_generation = "e" * 32
        else:
            # Test application state replacement only; original Store remains owned by lane.
            client.server.app[server.CTX_KEY] = object()
        release.set()
        status, data = await pending
        assert status == 503 and code(data) == "readiness_unavailable"
        client.server.app[server.CTX_KEY] = env.ctx

    try:
        run(env, scenario)
    finally:
        release.set()


def test_deadline_keeps_running_auth_owned(tmp_path: Path, monkeypatch):
    env = Env(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    monkeypatch.setattr(server, '_READINESS_DEADLINE_S', .05)

    async def scenario(client):
        dev = await pair(env, client)
        original = env.store.access_authority_snapshot
        def held(raw):
            entered.set()
            assert release.wait(3)
            return original(raw)
        monkeypatch.setattr(env.store, 'access_authority_snapshot', held)
        task = asyncio.create_task(get(client, PATH, headers=env.headers(dev)))
        for _ in range(100):
            if entered.is_set():
                break
            await asyncio.sleep(.005)
        assert entered.is_set()
        status, data = await task
        assert status == 503 and code(data) == 'readiness_unavailable'
        assert env.ctx.read_worker_budget.active == 1
        assert len(env.ctx.readiness_reads._activities) == 1
        release.set()
        for _ in range(100):
            if env.ctx.read_worker_budget.active == 0:
                break
            await asyncio.sleep(.005)
        assert env.ctx.read_worker_budget.active == 0
    try:
        run(env, scenario)
    finally:
        release.set()


def test_transfer_encoding_is_rejected(tmp_path: Path):
    env = Env(tmp_path)
    async def scenario(client):
        dev = await pair(env, client)
        async def chunks():
            yield b'x'
        resp = await client.get(url(PATH), headers=env.headers(dev), data=chunks())
        assert resp.status == 400
        assert code(await resp.json()) == 'bad_request'
    run(env, scenario)


def test_shared_capacity_is_held_by_actual_workers(tmp_path: Path, monkeypatch):
    env = Env(tmp_path)
    release = threading.Event()
    async def scenario(client):
        dev = await pair(env, client)
        def held():
            assert release.wait(3)
        async def holder():
            async with env.ctx.readiness_reads.activity(held, deadline=time.monotonic() + 3):
                pass
        tasks = [asyncio.create_task(holder()) for _ in range(4)]
        try:
            for _ in range(100):
                if env.ctx.read_worker_budget.active == 4:
                    break
                await asyncio.sleep(.005)
            assert env.ctx.read_worker_budget.active == 4
            auth_reads = []
            def forbidden(_):
                auth_reads.append(True)
                raise AssertionError('unfunded auth read')
            monkeypatch.setattr(env.store, 'access_authority_snapshot', forbidden)
            status, data = await get(client, PATH, headers=env.headers(dev))
            assert status == 503 and code(data) == 'readiness_unavailable'
            assert env.ctx.read_worker_budget.active == 4
            assert auth_reads == []
        finally:
            release.set()
            await asyncio.gather(*tasks)
        assert env.ctx.read_worker_budget.active == 0
    try:
        run(env, scenario)
    finally:
        release.set()
