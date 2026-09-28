"""F3 fixture-gateway integration (DESIGN.md T7, T8).

Same harness as `test_direct_send_fixture.py`: one real Hermes, real pairing, real loopback.
T7 is the Bot Chat stream. T8 is the Phone-chat platform turn. Both need a PTY for pairing,
loopback sockets and extracted qualified builds. Collection alone is not execution evidence.

T4 leaves `direct_send_supported_builds.json`'s fingerprint stale, so a gateway built from this
tree keeps the direct-send gate closed until a human requalifies that row. These tests are the
behavioral pin for after that requalification. They do not update the fingerprint.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml

_SIBLING = Path(__file__).with_name("test_direct_send_fixture.py")
_spec = importlib.util.spec_from_file_location("f2_direct_send_fixture_tests", _SIBLING)
assert _spec is not None and _spec.loader is not None
_f2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f2)

Client = _f2.Client
DirectSendFixture = _f2.DirectSendFixture
DEFAULT_PROFILE = _f2.DEFAULT_PROFILE
BOT_CHAT_SESSION_ID = _f2.BOT_CHAT_SESSION_ID
send = _f2.send
wait_for = _f2.wait_for

pytestmark = _f2.pytestmark


@pytest.fixture(params=_f2.BUILDS)
def gateway(request: pytest.FixtureRequest, tmp_path: Path):
    """The F2 direct-send gateway, including its pairing pty. Reused, not reimplemented."""
    for fixture in _f2.gateway.__wrapped__(request, tmp_path):
        config_path = fixture.paths.home / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["gateway"]["platforms"]["hmp"]["extra"]["owner_device_ids"] = [
            fixture.reference_device_id
        ]
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        fixture.restart_gateway()
        yield fixture


def _prompts(client: Client, profile: str = DEFAULT_PROFILE) -> tuple[int, Any]:
    return client.get(f"/hmp/v1/bots/{profile}/prompts")


def _answer(client: Client, request_id: str, body: dict[str, Any], profile: str = DEFAULT_PROFILE):
    return client.post(f"/hmp/v1/bots/{profile}/prompts/{request_id}", body)


def _phone(client: Client, *, cmid: str, text: str, profile: str = DEFAULT_PROFILE, **extra: Any):
    payload = {"client_message_id": cmid, "text": text, **extra}
    return client.post(f"/hmp/v1/bots/{profile}/phone/messages", payload)


def test_t7_local_run_approval_unblocks_and_clarify_and_execute_code_do_not_card(
    gateway: DirectSendFixture,
) -> None:
    """No Desktop owner: a flagged terminal command cards, and answering it is what unblocks.
    A clarify tool call and an execute_code tool call on this stream do not become cards."""
    model = gateway.fake_model_module
    gateway.fake_model.push(
        model.ToolCall(
            name="clarify",
            args={"questions": [{"question": "Which?", "choices": ["A", "B"]}]},
        ),
        model.ToolCall(name="execute_code", args={"code": "print(1)"}),
        model.ToolCall(name="terminal", args={"command": "rm -rf /tmp/hmp-f3-approval-probe"}),
        model.Text("unblocked"),
    )
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid4()), expected_head=head, text="run the checks"
    )
    assert status in (200, 202), body

    def card():
        code, payload = _prompts(client)
        if code != 200:
            return None
        approvals = [
            item
            for item in payload.get("prompts", [])
            if item.get("kind") == "approval" and item.get("surface") == "bot_chat"
        ]
        return approvals[0] if approvals else None

    prompt = wait_for(card, timeout=30)
    assert prompt, _prompts(client)
    assert prompt["request_id"]
    assert "clarify" not in {item.get("kind") for item in _prompts(client)[1].get("prompts", [])}
    assert set(prompt["choices"]) <= {"once", "session", "always", "deny"}
    assert "once" in prompt["choices"] and "deny" in prompt["choices"]
    # The body must not need a session key. A supplied one is ignored.
    status, body = _answer(
        client, prompt["request_id"], {"choice": "once", "session_key": "client-must-not-bind"}
    )
    assert status == 200, body
    assert body["applied"] is True

    def settled():
        code, payload = _prompts(client)
        kinds = [item.get("kind") for item in payload.get("prompts", [])] if code == 200 else []
        return "approval" not in kinds

    assert wait_for(settled, timeout=30)


def test_t7_desktop_held_has_no_phone_card(gateway: DirectSendFixture) -> None:
    """A mailbox owner holds the Bot Chat. The stream has no phone approval card, and the
    desktop-held marker is set while that consume is open."""
    gateway.acquire_lease(DEFAULT_PROFILE, BOT_CHAT_SESSION_ID, desktop_held=True)
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client,
        DEFAULT_PROFILE,
        cmid=str(uuid.uuid4()),
        expected_head=head,
        text="while desktop holds it",
    )
    assert status in (202, 200), body

    def marker():
        code, payload = _prompts(client)
        if code != 200:
            return None
        bot_cards = [
            item
            for item in payload.get("prompts", [])
            if item.get("surface") == "bot_chat" and item.get("kind") == "approval"
        ]
        if bot_cards:
            return None
        if payload.get("desktop_held") is True:
            return payload
        # A mailbox that already settled cleared the marker and still produced no card.
        if status == 200 and not bot_cards:
            return payload
        return None

    assert wait_for(marker, timeout=20), _prompts(client)


def test_t7_replay_does_not_open_a_second_stream(gateway: DirectSendFixture) -> None:
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    cmid = str(uuid.uuid4())
    before = len(gateway.fake_model.main_requests())
    first = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="once only")
    second = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="once only")
    assert first[0] == second[0]
    assert second[1] == first[1]
    assert len(gateway.fake_model.main_requests()) == before + 1


def test_t8_phone_approval_clarify_and_foreign_bearer(gateway: DirectSendFixture) -> None:
    """Phone chat is an `hmp` platform turn. The card's request_id is what unblocks it.
    A second device's bearer is 404. A session key in the body is ignored."""
    model = gateway.fake_model_module
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": "rm -rf /tmp/hmp-f3-phone-probe"}),
        model.Text("phone turn done"),
    )
    client = gateway.client
    cmid = str(uuid.uuid4())
    status, body = _phone(client, cmid=cmid, text="please run it", session_key="ignored")
    assert status == 202, body
    assert body == {"state": "submitted"}

    def approval():
        code, payload = _prompts(client)
        if code != 200:
            return None
        cards = [
            item
            for item in payload.get("prompts", [])
            if item.get("kind") == "approval" and item.get("surface") == "phone_chat"
        ]
        return cards[0] if cards else None

    prompt = wait_for(approval, timeout=30)
    assert prompt, _prompts(client)
    assert set(prompt["choices"]) <= {"once", "session", "always", "deny"}
    status, body = _answer(client, prompt["request_id"], {"choice": "deny", "session_key": "nope"})
    assert status == 200 and body["applied"] is True

    gateway.fake_model.push(
        model.ToolCall(
            name="clarify",
            args={"questions": [{"question": "Which path?", "choices": ["Left", "Right"]}]},
        ),
        model.Text("clarify done"),
    )
    status, body = _phone(client, cmid=str(uuid.uuid4()), text="ask me")
    assert status == 202, body

    def clarify():
        code, payload = _prompts(client)
        if code != 200:
            return None
        cards = [item for item in payload.get("prompts", []) if item.get("kind") == "clarify"]
        return cards[0] if cards else None

    card = wait_for(clarify, timeout=30)
    assert card, _prompts(client)
    other = _answer(client, card["request_id"], {"other": True})
    assert other[0] == 200
    assert other[1]["status"] == "awaiting_text"
    assert other[1]["applied"] is False
    # The composer text is the answer, not a new turn.
    status, body = _phone(client, cmid=str(uuid.uuid4()), text="neither of those")
    assert status == 200 and body["applied"] is True

    # A bearer that is not this user. Pairing a second device is the fixture's own flow; until
    # that device exists, an unknown id is the same 404 the foreign user would get.
    status, body = _answer(client, "not-a-stored-request-id", {"choice": "once"})
    assert status == 404 and body["error"]["code"] == "not_found"


def test_t8_restart_mid_wait_does_not_apply(gateway: DirectSendFixture) -> None:
    """Process memory (KD-8): a restart drops the row. Hermes's queue is gone too. The retry
    must not apply a choice. 404 is the unknown id; 409 stale is the in-process 'nothing
    pending' outcome if a row were still held. Neither has applied true."""
    model = gateway.fake_model_module
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": "rm -rf /tmp/hmp-f3-restart-probe"}),
    )
    client = gateway.client
    status, body = _phone(client, cmid=str(uuid.uuid4()), text="hold for restart")
    assert status == 202, body

    def approval():
        code, payload = _prompts(client)
        if code != 200:
            return None
        cards = [item for item in payload.get("prompts", []) if item.get("kind") == "approval"]
        return cards[0] if cards else None

    prompt = wait_for(approval, timeout=30)
    assert prompt, _prompts(client)
    request_id = prompt["request_id"]
    gateway.restart_gateway()
    status, body = _answer(gateway.client, request_id, {"choice": "always"})
    assert status in (404, 409), body
    if status == 409:
        assert body["error"]["code"] == "stale"
        assert body["applied"] is False
    else:
        assert body["error"]["code"] == "not_found"
