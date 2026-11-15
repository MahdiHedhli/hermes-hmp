"""AR1 fixed readiness projections and authenticated, read-only routes."""

from __future__ import annotations

import asyncio
import contextlib
import sys
import threading
import time
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import readiness, server
from hmp_plugin.bridge import HermesApi, HermesReadBridge
from hmp_plugin.compat import (
    CompatResult,
    CompatStatus,
    Eligibility,
    Feature,
    FeatureStatus,
    Unavailable,
)
from hmp_plugin.contract import AuthzState, ErrorCode, HmpError
from hmp_plugin.hermes_version import UNKNOWN_VERSION

from .hmp_kit import Env, code, get, pair, run
from .test_adapter import adapter_module as adapter_module


def _eligibility(
    *, jobs: FeatureStatus | None = None, model: FeatureStatus | None = None
) -> Eligibility:
    return Eligibility(
        version=UNKNOWN_VERSION,
        git_sha=None,
        features={
            Feature.JOBS: jobs or FeatureStatus(available=True),
            Feature.MODEL: model or FeatureStatus(available=True),
        },
    )


def test_capability_projection_is_closed_and_unknown_versions_are_not_refused() -> None:
    result = CompatResult(
        CompatStatus.UNSUPPORTED,
        eligibility=_eligibility(
            jobs=FeatureStatus(available=False, reason=Unavailable.VERSION_BELOW_FLOOR),
            model=FeatureStatus(available=False, reason=None),
        ),
    )
    assert readiness.capability_snapshot(result) == {
        "jobs": {"capability": "below_floor"},
        "model": {"capability": "unknown"},
    }
    assert readiness.capability_snapshot(
        CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    ) == {
        "jobs": {"capability": "available"},
        "model": {"capability": "available"},
    }
    for malformed in (
        object(),
        CompatResult(CompatStatus.SUPPORTED),
        CompatResult(
            CompatStatus.SUPPORTED,
            eligibility=_eligibility(jobs=FeatureStatus(available=1)),  # type: ignore[arg-type]
        ),
        CompatResult(
            CompatStatus.SUPPORTED,
            eligibility=_eligibility(
                jobs=FeatureStatus(available=True, reason=Unavailable.PROBE_FAILED),
            ),
        ),
    ):
        with pytest.raises(readiness.ReadinessUnavailableError):
            readiness.capability_snapshot(malformed)


def test_per_feature_actions_and_reason_sets_are_independent() -> None:
    jobs = readiness.feature_status_fields(
        capability="available",
        capability_reason=None,
        entitlement="missing",
        host_setting="enabled",
        profile_api="configured",
    )
    model = readiness.feature_status_fields(
        capability="below_floor",
        capability_reason="version_below_floor",
        entitlement="missing",
        host_setting="disabled",
        profile_api="configured",
    )
    assert jobs["action"] == "request_access"
    assert jobs["reasons"] == ["api_not_probed", "controls_missing"]
    assert model["action"] == "plan_host_remediation"
    assert model["reasons"] == [
        "api_not_probed", "controls_missing", "host_flag_disabled", "version_below_floor",
    ]
    for bad_timestamp in (True, -1, readiness.MAX_SAFE_INTEGER + 1, 1.0):
        with pytest.raises(readiness.ReadinessUnavailableError):
            server._readiness_now(
                SimpleNamespace(now=lambda value=bad_timestamp: value)  # type: ignore[arg-type]
            )


def test_capability_route_authenticates_even_on_unsupported_build(tmp_path: Path) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        env.ctx.compat = CompatResult(
            CompatStatus.UNSUPPORTED,
            eligibility=_eligibility(
                jobs=FeatureStatus(available=False, reason=Unavailable.DEPENDENCY_MISSING),
            ),
        )
        status, data = await get(client, "/readiness/capabilities", headers=env.headers(device))
        assert status == 200
        assert data == {
            "protocol": 1,
            "features": {
                "jobs": {"capability": "dependency_missing"},
                "model": {"capability": "available"},
            },
        }
        status, body = await get(
            client, "/readiness/capabilities", headers={"HMP-Instance": env.iid}
        )
        assert status == 401 and code(body) == ErrorCode.UNAUTHENTICATED
        status, body = await get(
            client, "/readiness/capabilities?extra=1", headers=env.headers(device)
        )
        assert status == 400 and code(body) == ErrorCode.BAD_REQUEST

    run(env, scenario)


@pytest.mark.parametrize("path", ["/readiness/capabilities", "/bots/default/readiness"])
@pytest.mark.parametrize(
    "failure", [RuntimeError("synthetic private auth source"), HmpError(ErrorCode.OTHER, http=500)]
)
def test_readiness_auth_source_uncertainty_is_fixed_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str, failure: Exception,
) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)

        def unavailable(_request: Any) -> Any:
            raise failure

        monkeypatch.setattr(server, "bearer", unavailable)
        status, body = await get(client, path, headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }
        assert "synthetic private auth source" not in str(body)

    run(env, scenario)


@pytest.mark.parametrize("bad_generation", [None, True, 1, object()])
def test_readiness_route_maps_malformed_generation_to_fixed_503(
    tmp_path: Path, bad_generation: object,
) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        env.ctx.readiness_generation = bad_generation  # type: ignore[assignment]
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }

    run(env, scenario)


@pytest.mark.parametrize("bad_now", [True, 1.5])
def test_readiness_route_maps_invalid_clock_to_fixed_503(
    tmp_path: Path, bad_now: object,
) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        env.ctx.now = lambda: bad_now  # type: ignore[assignment]
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }

    run(env, scenario)


def test_readiness_route_maps_raising_clock_to_fixed_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        monkeypatch.setattr(
            server, "bearer", lambda _request: SimpleNamespace(device_id=device.device_id)
        )

        def bad_clock() -> int:
            raise RuntimeError("synthetic clock detail")

        env.ctx.now = bad_clock
        status, body = await get(
            client, "/bots/default/readiness", headers=env.headers(device)
        )
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }
        assert "synthetic clock detail" not in str(body)

    run(env, scenario)


def test_readiness_rate_limit_refusal_remains_429(tmp_path: Path) -> None:
    env = Env(tmp_path)
    hits: list[tuple[object, ...]] = []

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)

        def limited(*args: Any, **_kwargs: Any) -> None:
            hits.append(args)
            raise HmpError(ErrorCode.RATE_LIMITED)

        env.ctx.limiter.check = limited  # type: ignore[method-assign]
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 429 and body["error"]["code"] == ErrorCode.RATE_LIMITED
        assert hits == [("readiness", device.device_id, 30, env.clock.now)]

    run(env, scenario)


def _install_actual_readiness_bridge(
    env: Env,
    monkeypatch: pytest.MonkeyPatch,
    *,
    platforms_by_profile: dict[str, object],
    scoped_keys: dict[str, str],
) -> None:
    current_profile = ["default"]
    gateway = types.ModuleType("gateway")
    gateway.__path__ = []  # type: ignore[attr-defined]
    gateway_config = types.ModuleType("gateway.config")
    gateway_config.Platform = SimpleNamespace(API_SERVER="api_server")  # type: ignore[attr-defined]

    def load_gateway_config() -> Any:
        configured = platforms_by_profile[current_profile[0]]
        if isinstance(configured, Exception):
            raise configured
        return SimpleNamespace(platforms=configured)

    gateway_config.load_gateway_config = load_gateway_config  # type: ignore[attr-defined]
    gateway_run = types.ModuleType("gateway.run")

    @contextlib.contextmanager
    def profile_scope(home: Path) -> Any:
        old = current_profile[0]
        current_profile[0] = home.name
        try:
            yield
        finally:
            current_profile[0] = old

    gateway_run._profile_runtime_scope = profile_scope  # type: ignore[attr-defined]
    gateway_platforms = types.ModuleType("gateway.platforms")
    gateway_platforms.__path__ = []  # type: ignore[attr-defined]
    shared = types.ModuleType("gateway.platforms._shared")
    shared.get_scoped_secret = lambda _name, default="": scoped_keys.get(  # type: ignore[attr-defined]
        current_profile[0], default
    )
    gateway.config = gateway_config  # type: ignore[attr-defined]
    gateway.run = gateway_run  # type: ignore[attr-defined]
    gateway.platforms = gateway_platforms  # type: ignore[attr-defined]
    gateway_platforms._shared = shared  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gateway", gateway)
    monkeypatch.setitem(sys.modules, "gateway.config", gateway_config)
    monkeypatch.setitem(sys.modules, "gateway.run", gateway_run)
    monkeypatch.setitem(sys.modules, "gateway.platforms", gateway_platforms)
    monkeypatch.setitem(sys.modules, "gateway.platforms._shared", shared)

    class Runner:
        def served_profile_names(self) -> list[str]:
            return ["default", "named"]

        def _routed_profile_home(self, profile: str) -> Path:
            return Path("/synthetic") / profile

    class Adapter:
        gateway_runner = Runner()

    bridge = HermesReadBridge(Adapter(), object(), hermes=HermesApi())
    bridge.authz_state = lambda *_: AuthzState.AUTHORIZED  # type: ignore[method-assign]
    env.ctx.bridge = bridge
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}


@pytest.mark.parametrize(
    ("platforms", "expected_status", "expected_profile_api"),
    [
        ({}, 200, "missing"),
        ({"api_server": SimpleNamespace(extra={})}, 200, "missing"),
        ({"api_server": None}, 503, None),
        ({"api_server": object()}, 503, None),
        ({"api_server": SimpleNamespace(extra=None)}, 503, None),
        ({"api_server": SimpleNamespace(extra=[])}, 503, None),
        ({"api_server": SimpleNamespace(extra={"host": 1})}, 503, None),
        (RuntimeError("synthetic config source"), 503, None),
    ],
)
def test_actual_hermes_profile_projection_preserves_absence_vs_malformed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platforms: dict[str, object],
    expected_status: int,
    expected_profile_api: str | None,
) -> None:
    env = Env(tmp_path)
    _install_actual_readiness_bridge(
        env, monkeypatch, platforms_by_profile={"default": platforms}, scoped_keys={"default": ""}
    )

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == expected_status
        if expected_status == 503:
            assert body == {
                "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
            }
        else:
            assert body["features"]["jobs"]["profile_api"] == expected_profile_api

    run(env, scenario)


def test_actual_hermes_profile_projection_keeps_default_and_named_key_scopes_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    inline = "synthetic-inline-api-key-0001"
    scoped = "synthetic-named-api-key-0001"
    platforms = {
        "default": {"api_server": SimpleNamespace(extra={
            "host": "127.0.0.1", "port": 8642, "key": inline,
        })},
        "named": {"api_server": SimpleNamespace(extra={
            "host": "127.0.0.1", "port": 8642, "key": inline,
        })},
    }
    env = Env(tmp_path)
    _install_actual_readiness_bridge(
        env,
        monkeypatch,
        platforms_by_profile=platforms,
        scoped_keys={"default": "", "named": ""},
    )

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 200 and body["features"]["jobs"]["profile_api"] == "configured"
        status, body = await get(client, "/bots/named/readiness", headers=env.headers(device))
        assert status == 200 and body["features"]["jobs"]["profile_api"] == "missing"
        # A named profile's inline key is not authority; only its own scoped key is.
        env.ctx.bridge._hermes.readiness_scoped_api_server_key = lambda: scoped  # type: ignore[attr-defined]
        status, body = await get(client, "/bots/named/readiness", headers=env.headers(device))
        assert status == 200 and body["features"]["jobs"]["profile_api"] == "configured"
        assert inline not in str(body) and scoped not in str(body)

    run(env, scenario)


@pytest.mark.parametrize(
    "adapter_config",
    [
        None,
        object(),
        SimpleNamespace(extra=None),
        SimpleNamespace(extra=[]),
        SimpleNamespace(extra={"owner_device_ids": "malformed"}),
    ],
)
def test_actual_adapter_readiness_control_reader_malformed_config_is_fixed_503(
    tmp_path: Path, adapter_config: object, adapter_module: types.ModuleType,
) -> None:
    read_owner_ids = adapter_module._readiness_owner_device_ids_from_adapter

    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    adapter = SimpleNamespace(config=adapter_config)
    reader_hits: list[bool] = []

    def read_controls() -> frozenset[str]:
        reader_hits.append(True)
        return read_owner_ids(adapter)

    env.ctx.readiness_owner_device_ids = read_controls
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }
        assert reader_hits == [True]

    run(env, scenario)


def test_bot_route_authz_controls_and_fixed_response(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    calls: list[str] = []
    def authz(_user: str, profile: str) -> AuthzState:
        calls.append("authz")
        return AuthzState.AUTHORIZED if profile == "default" else AuthzState.NOT_SERVED

    env.bridge.authz_state = authz
    env.bridge.readiness_profile_api_state = lambda profile, *, checkpoint: (
        checkpoint(), calls.append("profile"), "configured"
    )[-1]
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {
        "cron": {"enabled": True}, "model_management": {"enabled": False},
    }
    control_reads: list[str] = []
    read_controls = env.store.readiness_owner_controls_value
    env.store.readiness_owner_controls_value = lambda device_id: (
        control_reads.append(device_id), read_controls(device_id)
    )[-1]

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        env.store.set_owner_controls(device.device_id, allowed=True, now=env.clock.now)
        status, data = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 200
        assert data["protocol"] == 1
        assert data["checked_at"] == env.clock.now
        assert len(data["generation"]) == 32
        assert data["features"]["jobs"] == {
            "capability": "available",
            "entitlement": "granted",
            "host_setting": "enabled",
            "profile_api": "configured",
            "api_reachability": "not_probed",
            "reasons": ["api_not_probed"],
            "action": "check_host",
        }
        assert data["features"]["model"]["host_setting"] == "disabled"
        assert data["features"]["model"]["action"] == "plan_host_remediation"
        env.bridge.readiness_profile_api_state = lambda _profile, *, checkpoint: "unknown"
        status, unknown = await get(
            client, "/bots/default/readiness", headers=env.headers(device)
        )
        assert status == 200
        assert unknown["features"]["jobs"]["profile_api"] == "unknown"
        assert unknown["features"]["jobs"]["reasons"] == [
            "api_not_probed", "profile_api_unknown",
        ]
        assert unknown["features"]["jobs"]["action"] == "check_host"
        env.store.set_owner_controls(device.device_id, allowed=False, now=env.clock.now + 1)
        status, denied = await get(
            client, "/bots/default/readiness", headers=env.headers(device)
        )
        assert status == 200
        assert denied["features"]["jobs"]["entitlement"] == "missing"
        assert denied["features"]["jobs"]["action"] == "request_access"
        assert denied["features"]["model"]["action"] == "plan_host_remediation"
        before = list(calls)
        controls_before = len(control_reads)
        status, body = await get(client, "/bots/other/readiness", headers=env.headers(device))
        assert status == 404 and code(body) == ErrorCode.NOT_FOUND
        assert "profile" not in calls[len(before):]
        assert len(control_reads) == controls_before  # unauthorized target reads no controls
        status, body = await get(client, "/bots/default/readiness?x=1", headers=env.headers(device))
        assert status == 400 and code(body) == ErrorCode.BAD_REQUEST
        status, body = await get(
            client, "/bots/default/readiness", headers=env.headers(device, iid="wrong-instance")
        )
        assert status == 401 and body["error"]["code"] == "wrong_instance"
        assert len(control_reads) == controls_before
        status, body = await get(
            client, "/bots/default/readiness", headers=env.headers(device), data=b"x"
        )
        assert status == 400 and code(body) == ErrorCode.BAD_REQUEST
        assert env.ctx.reads.calls == []  # no catalog, jobs, or session projection is reachable

    run(env, scenario)


def test_malformed_live_projection_is_unavailable_not_disabled_or_missing(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    profile_reads: list[str] = []
    env.bridge.readiness_profile_api_state = lambda profile, *, checkpoint: (
        profile_reads.append(profile) or "unknown"
    )
    env.ctx.readiness_owner_device_ids = lambda: []  # malformed strict fallback (must be frozenset)
    env.ctx.readiness_settings = lambda: {"cron": {"enabled": "false"}, "model_management": {}}

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }
        assert profile_reads == []  # malformed controls are rejected before profile resolution
        env.ctx.readiness_owner_device_ids = lambda: frozenset()
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503 and body["error"]["code"] == "readiness_unavailable"
        assert profile_reads == []  # malformed enabled type is not projected as disabled
        env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}

        def secret_exception(_profile: str, *, checkpoint: Any) -> str:
            raise ValueError("synthetic private endpoint detail")

        env.bridge.readiness_profile_api_state = secret_exception
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503
        assert body == {
            "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
        }
        assert "synthetic private endpoint detail" not in str(body)

    run(env, scenario)


def test_readiness_timeout_keeps_worker_slot_until_blocking_reader_joins(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}
    started = threading.Event()
    release = threading.Event()

    def blocked_profile(_profile: str, *, checkpoint: Any) -> str:
        checkpoint()
        started.set()
        release.wait(5)
        return "unknown"

    env.bridge.readiness_profile_api_state = blocked_profile

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        response = await client.get(
            "/hmp/v1/bots/default/readiness", headers=env.headers(device)
        )
        try:
            assert response.status == 503
            assert await response.json() == {
                "error": {"code": "readiness_unavailable", "message": "readiness unavailable"},
            }
            assert started.is_set()
            assert env.ctx.readiness_workers == 1
        finally:
            release.set()
        deadline = time.monotonic() + 1
        while env.ctx.readiness_workers and time.monotonic() < deadline:  # noqa: ASYNC110
            await asyncio.sleep(0.01)
        assert env.ctx.readiness_workers == 0

    run(env, scenario)


def test_readiness_admits_at_most_four_profile_workers(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}
    started = threading.Event()
    release = threading.Event()
    calls = 0
    calls_lock = threading.Lock()

    def blocked_profile(_profile: str, *, checkpoint: Any) -> str:
        nonlocal calls
        checkpoint()
        with calls_lock:
            calls += 1
        started.set()
        release.wait(5)
        return "unknown"

    env.bridge.readiness_profile_api_state = blocked_profile

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        headers = env.headers(device)
        tasks = [
            asyncio.create_task(client.get("/hmp/v1/bots/default/readiness", headers=headers))
            for _ in range(5)
        ]
        try:
            assert await asyncio.to_thread(started.wait, 1)
            admission_deadline = time.monotonic() + 1
            while calls < 4 and time.monotonic() < admission_deadline:  # noqa: ASYNC110
                await asyncio.sleep(0.01)
            assert env.ctx.readiness_workers == 4
            assert calls == 4
            responses = await asyncio.gather(*tasks)
            assert all(response.status == 503 for response in responses)
            assert env.ctx.readiness_workers == 4  # timed-out workers are still charged
            release.set()
            deadline = time.monotonic() + 1
            while env.ctx.readiness_workers and time.monotonic() < deadline:  # noqa: ASYNC110
                await asyncio.sleep(0.01)
            assert env.ctx.readiness_workers == 0
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()

    run(env, scenario)


def test_disconnected_readiness_caller_does_not_release_worker_early(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}
    started = threading.Event()
    release = threading.Event()

    def blocked_profile(_profile: str, *, checkpoint: Any) -> str:
        checkpoint()
        started.set()
        release.wait(5)
        return "unknown"

    env.bridge.readiness_profile_api_state = blocked_profile

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        request = asyncio.create_task(
            client.get("/hmp/v1/bots/default/readiness", headers=env.headers(device))
        )
        try:
            assert await asyncio.to_thread(started.wait, 1)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            assert env.ctx.readiness_workers == 1
        finally:
            release.set()
        deadline = time.monotonic() + 1
        while env.ctx.readiness_workers and time.monotonic() < deadline:  # noqa: ASYNC110
            await asyncio.sleep(0.01)
        assert env.ctx.readiness_workers == 0

    run(env, scenario)


@pytest.mark.parametrize("changed_source", ["controls", "settings", "generation"])
def test_readiness_discards_snapshot_when_live_source_changes_during_profile_read(
    tmp_path: Path, changed_source: str,
) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    settings = {"cron": {"enabled": True}, "model_management": {"enabled": True}}
    env.ctx.readiness_settings = lambda: settings

    def mutate_after_projection(_profile: str, *, checkpoint: Any) -> str:
        checkpoint()
        if changed_source == "controls":
            # Switch from fallback denial to an explicit grant while the profile lookup runs.
            env.store.set_owner_controls(target_device[0], allowed=True, now=env.clock.now)
        elif changed_source == "settings":
            settings["cron"]["enabled"] = False
        else:
            env.ctx.readiness_generation = (
                "0" * 32 if env.ctx.readiness_generation != "0" * 32 else "1" * 32
            )
        return "configured"

    env.bridge.readiness_profile_api_state = mutate_after_projection

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        target_device[0] = device.device_id
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 503 and code(body) == ErrorCode.READINESS_UNAVAILABLE

    target_device: list[str] = [""]
    run(env, scenario)


def test_readiness_rechecks_revocation_after_profile_lookup(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.ctx.compat = CompatResult(CompatStatus.SUPPORTED, eligibility=_eligibility())
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    env.ctx.readiness_owner_device_ids = lambda: frozenset()
    env.ctx.readiness_settings = lambda: {"cron": {}, "model_management": {}}
    target_device: list[str] = [""]

    def revoke_during_lookup(_profile: str, *, checkpoint: Any) -> str:
        env.store.set_device_state(target_device[0], "REVOKED")
        checkpoint()
        return "configured"

    env.bridge.readiness_profile_api_state = revoke_during_lookup

    async def scenario(client: TestClient) -> None:
        device = await pair(env, client)
        target_device[0] = device.device_id
        status, body = await get(client, "/bots/default/readiness", headers=env.headers(device))
        assert status == 401 and body["error"]["code"] == "revoked"
        assert "features" not in body

    run(env, scenario)
