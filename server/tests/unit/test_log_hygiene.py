"""T024-T027 log hygiene (SEC-4, SR-007, CS-22): every log record emitted while driving P2, P4,
P5 (rotation, grace retry, reuse), self-revoke, operator revoke, bearer reads and a range of
errors scans clean under `tools/ci/scan_logs.py`, and carries none of the values that flowed
through those requests.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import crypto, wire
from hmp_plugin.contract import REFRESH_RETRY_GRACE_S
from hmp_plugin.revoke import revoke_device

from .hmp_kit import Device, Env, get, pair, post, run

REPO = Path(__file__).resolve().parents[3]


def _scanner() -> ModuleType:
    path = REPO / "tools" / "ci" / "scan_logs.py"
    spec = importlib.util.spec_from_file_location("scan_logs_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_full_flow_logs_scan_clean(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    env = Env(tmp_path)
    secrets: list[str] = []

    async def scenario(client: TestClient) -> None:
        dev = Device(name="f1-fixture-device-phone")
        offer = env.offer()
        secrets.extend([wire.b64u_encode(offer.s), offer.oid, dev.name])
        await pair(env, client, dev)
        secrets.extend([dev.refresh, dev.access, dev.pairing_id, wire.b64u_encode(dev.nd)])
        secrets.append(crypto.device_sas(crypto.spki_fingerprint(dev.pub)))
        first = dev.refresh
        status, body = await post(client, "/auth/token", env.p5_body(dev))
        assert status == 200
        dev.refresh, dev.access = body["refresh_token"], body["access_token"]
        secrets.extend([dev.refresh, dev.access])
        assert (await post(client, "/auth/token", env.p5_body(dev, refresh=first)))[0] == 200
        assert (await get(client, "/bots?x=" + "Q" * 30, headers=env.headers(dev)))[0] == 200
        env.clock.now += REFRESH_RETRY_GRACE_S + 1
        assert (await post(client, "/auth/token", env.p5_body(dev, refresh=first)))[0] == 401
        # Errors of every kind, with values that must never be logged.
        await post(client, "/pair/request", b'{"oid":' + b'"' + b"A" * 40 + b'"}')
        await post(client, "/pair/request", env.p2_body(Device(), env.offer(), s="!!"))
        await post(client, "/pair/complete", {"pairing_id": dev.pairing_id, "ts": 1, "sig": "x"})
        await get(client, "/bots", headers={"Authorization": "Bearer " + "Z" * 43})
        await get(client, "/nothing?token=" + "T" * 40)
        other = await pair(env, client)
        secrets.extend([other.refresh, other.access])
        status, _ = await post(
            client, "/devices/self/revoke", env.self_revoke_body(other), headers=env.headers(other)
        )
        assert status == 200
        third = await pair(env, client)
        revoke_device(env.store, third.device_id, now=env.clock.now)

    with caplog.at_level(logging.DEBUG):
        run(env, scenario)
    text = caplog.text
    assert "event=pair_complete" in text  # the plugin logger did log outcomes
    assert "/hmp/v1/auth/token 200" in text  # and the reduced access log ran
    scanner = _scanner()
    rules = scanner.build_rules(REPO / "fixtures" / "f1" / "instances.yaml")
    findings = scanner.scan_text(text, rules)
    assert findings == [], [(n, rule) for n, rule, _ in findings]
    for value in secrets:
        assert value not in text
