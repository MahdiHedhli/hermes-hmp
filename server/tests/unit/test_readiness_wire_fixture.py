"""The shared protocol-1 readiness wire examples exercise the real producer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import readiness, wire
from hmp_plugin.compat import (
    CompatResult,
    CompatStatus,
    Eligibility,
    Feature,
    FeatureStatus,
    Unavailable,
)
from hmp_plugin.hermes_version import UNKNOWN_VERSION
from hmp_plugin.contract import AuthzState

from .hmp_kit import Env, pair, run, url


FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "docs/architecture/contracts/vectors/readiness_v1_vectors.json"
)


def _status(name: str) -> FeatureStatus:
    return {
        "available": FeatureStatus(available=True),
        "unknown": FeatureStatus(available=False, reason=None),
        "below_floor": FeatureStatus(
            available=False, reason=Unavailable.VERSION_BELOW_FLOOR
        ),
    }[name]


def test_shared_readiness_wire_examples_are_produced_by_current_mapping() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["_meta"]["contract"] == "hmp-readiness-wire"
    assert fixture["_meta"]["revision"] == 1
    assert [row["name"] for row in fixture["positive"]] == [
        "missing_controls", "disabled_model", "unknown_axes",
        "below_floor_jobs", "missing_profile_api",
    ]

    for row in fixture["positive"]:
        inputs = row["producer_input"]
        statuses = {
            Feature.JOBS: _status(inputs["jobs_status"]),
            Feature.MODEL: _status(inputs["model_status"]),
        }
        result = CompatResult(
            CompatStatus.SUPPORTED,
            eligibility=Eligibility(
                version=UNKNOWN_VERSION, git_sha=None, features=statuses
            ),
        )
        assert {
            "protocol": 1,
            "features": readiness.capability_snapshot(result),
        } == row["capabilities"]

        features = {}
        for name, feature, host_key in (
            ("jobs", Feature.JOBS, "jobs_host_setting"),
            ("model", Feature.MODEL, "model_host_setting"),
        ):
            capability, reason = readiness.capability_axis(statuses[feature])
            readiness.validate_feature_axes(
                capability, inputs["entitlement"], inputs[host_key],
                inputs["profile_api"],
            )
            features[name] = readiness.feature_status_fields(
                capability=capability,
                capability_reason=reason,
                entitlement=inputs["entitlement"],
                host_setting=inputs[host_key],
                profile_api=inputs["profile_api"],
            )
        bot = row["bot"]
        assert {
            "protocol": 1,
            "checked_at": bot["checked_at"],
            "generation": bot["generation"],
            "features": features,
        } == bot
        assert type(bot["checked_at"]) is int
        assert 0 <= bot["checked_at"] <= readiness.MAX_SAFE_INTEGER
        assert readiness.GENERATION_RE.fullmatch(bot["generation"]) is not None
        assert len(json.dumps(bot, separators=(",", ":")).encode("utf-8")) <= 2048


@pytest.mark.parametrize(
    "name",
    ["missing_controls", "disabled_model", "below_floor_jobs", "missing_profile_api"],
)
def test_authenticated_routes_emit_the_shared_wire_bytes_as_fields(
    tmp_path: Path, name: str,
) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    row = next(case for case in fixture["positive"] if case["name"] == name)
    inputs = row["producer_input"]
    env = Env(tmp_path)

    async def scenario(client: TestClient) -> None:
        env.clock.now = row["bot"]["checked_at"]
        device = await pair(env, client)
        env.ctx.readiness_generation = row["bot"]["generation"]
        env.ctx.compat = CompatResult(
            CompatStatus.SUPPORTED,
            eligibility=Eligibility(
                version=UNKNOWN_VERSION,
                git_sha=None,
                features={
                    Feature.JOBS: _status(inputs["jobs_status"]),
                    Feature.MODEL: _status(inputs["model_status"]),
                },
            ),
        )
        env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
        env.bridge.readiness_profile_api_state = (
            lambda _profile, *, checkpoint: inputs["profile_api"]
        )
        env.ctx.readiness_owner_device_ids = lambda: frozenset()
        env.ctx.readiness_settings = lambda: {
            "cron": {"enabled": inputs["jobs_host_setting"] == "enabled"},
            "model_management": {
                "enabled": inputs["model_host_setting"] == "enabled"
            },
        }
        if inputs["entitlement"] == "granted":
            env.store.set_owner_controls(
                device.device_id, allowed=True, now=env.clock.now
            )
        headers = env.headers(device)
        response = await client.get(url("/readiness/capabilities"), headers=headers)
        assert response.status == 200
        assert await response.read() == wire.dump_json(row["capabilities"])
        response = await client.get(url("/bots/default/readiness"), headers=headers)
        assert response.status == 200
        assert await response.read() == wire.dump_json(row["bot"])

    run(env, scenario)
