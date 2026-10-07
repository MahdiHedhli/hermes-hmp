"""T029 native-origin push/revoke/restart fixture. Run only in reviewed confinement.

Real native gateway, pairing/owner choice, AP3/AP4, production dispatcher and
signature transport. Synthetic loopback model/relay only. The observation copy
does not modify production source. Desktop-held takeover is NOT covered here.
Collection/skips and helper unit tests are not native execution receipts.
These positive cases require a native approval notifier. Its absence fails the
prerequisite; it cannot count as positive approval/revocation/restart coverage.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import importlib.util
import json
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "push_native_approval_tests", Path(__file__).with_name("test_approvals_fixture.py")
)
assert _spec and _spec.loader
approvals = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(approvals)

import _fixture_common as fc  # noqa: E402 -- sibling loads the fixture tools path
import push_native_fixture as wiring  # noqa: E402
import push_native_observer as observer  # noqa: E402
from push_relay_fixture import FakeHttpsRelay  # noqa: E402

pytestmark = approvals.pytestmark
PROFILE = approvals.DEFAULT_PROFILE


@dataclass
class NativePush:
    gateway: object
    relay: FakeHttpsRelay
    journal: Path


@pytest.fixture(params=approvals._f2.BUILDS)
def native_push(request, tmp_path, monkeypatch):
    with FakeHttpsRelay((tmp_path / "relay").resolve()) as relay:
        # Trust this fresh CA in the clean disposable child only. Production's
        # SSL factory still requires chain/name verification plus the leaf pin.
        monkeypatch.setenv("SSL_CERT_FILE", str(relay.ca_path))
        generator = approvals._f2.gateway.__wrapped__(
            request, tmp_path, approval_owner_enrollment=True
        )
        gateway = next(generator)
        try:
            # Patch the copied bootstrap only while its native process is stopped.
            approvals._f2.dsf.stop_gateway(gateway.gateway_proc)
            journal = wiring.install_fixture(gateway.paths, relay)
            gateway.restart_gateway()
            yield NativePush(gateway, relay, journal)
        finally:
            generator.close()  # actual most-recent gateway, model and lease teardown


def _wait(predicate, *, timeout=20):
    value = approvals._f2.wait_for(predicate, timeout=timeout, interval=0.05)
    assert value, "native fixture observation deadline"
    return value


def _http(client, method, path, body):
    # Existing HMP fixture seeding transport; its pin is not the test target.
    # This does not alter RelayClient's verified TLS context.
    connection = http.client.HTTPSConnection(
        "127.0.0.1", client.port, context=client._ctx(), timeout=30
    )
    try:
        connection.request(method, path, json.dumps(body).encode(), client._headers())
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def _register(value):
    client = value.gateway.client
    status, body = client.get("/hmp/v1/push/registration")
    assert status == 200
    if body["available"] is False:
        assert not approvals._notifier(value.gateway)
        assert body["why"] == "approvals_unavailable"
        return None
    assert body["available"] is True
    intent = {
        "v": 1, "request_id": base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode(),
        "expected_generation": body["generation"], "platform": "apns",
        "addr_kind": "apns_token", "env": "sandbox", "relay_kid": "fixture-kid",
        # Accepted opaque syntax only; no HPKE opening/provider delivery claim.
        "sealed": base64.urlsafe_b64encode(b"s" * 82).rstrip(b"=").decode(),
        "seal_expires_at": int(time.time()) + 7200,
    }
    status, registered = _http(client, "PUT", "/hmp/v1/push/registration", intent)
    assert status == 200 and registered["state"] == "active"
    return registered


def _approval(value, name):
    gateway, client = value.gateway, value.gateway.client
    target = gateway.paths.out_dir / name
    target.mkdir()
    (target / "sentinel").write_text("requires explicit consent")
    gateway.fake_model.push(
        gateway.fake_model_module.ToolCall(
            name="terminal", args={"command": f"rm -rf {shlex.quote(str(target))}"}
        ),
        gateway.fake_model_module.Text("synthetic push fixture reply"),
    )
    ref = approvals._f2.bot_chat_ref(client, PROFILE)
    head = approvals._f2.bot_chat_head(client, PROFILE, ref)
    status, body = approvals.send(
        client, PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="synthetic approval check"
    )
    if not approvals._notifier(gateway):
        assert status in (200, 202)
        approvals._assert_no_card_and_command_not_run(gateway, target, seconds=10)
        assert value.relay.records() == ()
        return None
    assert status == 202, body

    def prompt():
        code, payload = approvals._prompts(client)
        assert code == 200
        cards = [p for p in payload["prompts"] if p.get("kind") == "approval"]
        return cards[0] if cards else None

    card = _wait(prompt)
    assert (target / "sentinel").exists()
    return card


def _deny(value, card):
    status, body = approvals._answer(value.gateway.client, card["request_id"], {"choice": "deny"})
    assert status == 200 and body["applied"] is True
    _wait(lambda: not approvals._prompts(value.gateway.client)[1]["prompts"])


def _warm_up(value):
    assert approvals._notifier(value.gateway), (
        "positive push fixture requires native approval notifier"
    )
    registration = _register(value)
    card = _approval(value, "push-first-probe")
    assert card is not None, "positive push fixture did not observe a native approval"
    assert registration is not None
    _wait(lambda: len(value.relay.records()) == 1)
    body = value.relay.records()[0]  # capture is independently signature-verified
    spki = base64.urlsafe_b64decode(body["iid_spki"] + "=" * (-len(body["iid_spki"]) % 4))
    iid = base64.b32encode(hashlib.sha256(spki).digest()).rstrip(b"=").decode().lower()
    assert iid == value.gateway.client.iid
    assert body["route"] == registration["route"] and body["aud"] == "synthetic-relay"
    _wait(lambda: (observer.snapshot(value.journal) or {}).get("send_completed") == 1)
    _deny(value, card)
    assert (value.gateway.paths.out_dir / "push-first-probe" / "sentinel").exists()
    return True


def _pending(value):
    wiring.arm(value.journal)
    card = _approval(value, "push-pending-probe")
    assert card is not None
    _wait(lambda: (observer.snapshot(value.journal) or {}).get("waiting") == 1)
    observed = observer.snapshot(value.journal)
    assert observed["scheduled"] == 2 and observed["pending_slots"] == 1
    assert observed["send_completed"] == 1 and len(value.relay.records()) == 1
    return card


def test_native_approval_reaches_signed_verified_relay(native_push):
    assert _warm_up(native_push) is True


def test_native_revocation_after_positive_pending_suppresses_relay(native_push):
    value = native_push
    assert _warm_up(value) is True
    _pending(value)
    gateway = value.gateway
    result = subprocess.run(
        [str(gateway.build.venv_python), str(approvals._f2.dsf.FIXTURE_PAIRING_CLI),
         "devices-revoke", "--home", str(gateway.paths.home), "--xdg-state",
         str(gateway.paths.xdg_state), gateway.reference_device_id],
        env=fc.clean_hermes_env(), capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, "native host revoke failed; diagnostics remain private"
    status, _ = gateway.client.get("/hmp/v1/push/registration")
    assert status == 401  # actual bearer revocation, not just a successful CLI exit
    wiring.release(value.journal)
    _wait(lambda: (observer.snapshot(value.journal) or {}).get("send_completed") == 2)
    assert observer.snapshot(value.journal)["pending_slots"] == 0
    assert len(value.relay.records()) == 1
    assert (gateway.paths.out_dir / "push-pending-probe" / "sentinel").exists()


def test_native_restart_drops_positively_pending_work_and_old_hints(native_push):
    value = native_push
    assert _warm_up(value) is True
    _pending(value)
    old_hint = value.relay.records()[0]["hint"]
    value.gateway.restart_gateway()  # graceful close cancels the actual pending task
    closed = observer.snapshot(value.journal, "closed.json")
    assert closed["closed"] and closed["wait_cancelled"] == 1
    assert closed["slots"] == closed["pending_slots"] == closed["queue"] == closed["hints"] == 0
    status, _ = value.gateway.client.post("/hmp/v1/push/hints/resolve", {"v": 1, "hint": old_hint})
    assert status == 404
    assert len(value.relay.records()) == 1
    assert (value.gateway.paths.out_dir / "push-pending-probe" / "sentinel").exists()
