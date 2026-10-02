"""F3 fixture-gateway integration (DESIGN.md T7, T8).

Same harness as `test_direct_send_fixture.py`: one real Hermes, real pairing, real loopback.
T7 is the Bot Chat stream. T8 is the Phone-chat platform turn. Both need a PTY for pairing,
loopback sockets and extracted qualified builds. Collection alone is not execution evidence.

Spec 034 (owner policy 2026-10-01): availability comes from the minimum version and the actual
Hermes APIs, never from an exact-build receipt or manifest. Nothing here installs a receipt or edits
a manifest to open a lane, and a pass is sampled evidence for one build, not an admission list.

Bot Chat cards need Hermes's session-stream approval notifier. A build either has it (positive
cases: a card, an exact-ID answer) or does not (negative cases: the send still succeeds, no card is
invented, the dangerous command does not run, nothing warns). Each test below branches on the
build's own source, so exactly one expectation applies per build and no case is skipped. Run it
only against locally present pinned builds in an isolated home, after review. A real listener
reconnect has no public gateway hook, so the generation fence is covered by
`tests/unit/test_approval_fences.py` through the real `open_components` factory instead.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

_SIBLING = Path(__file__).with_name("test_direct_send_fixture.py")
_spec = importlib.util.spec_from_file_location("f2_direct_send_fixture_tests", _SIBLING)
assert _spec is not None and _spec.loader is not None
_f2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f2)

from hmp_plugin import compat  # noqa: E402 -- the server package is on the test path

Client = _f2.Client
DirectSendFixture = _f2.DirectSendFixture
DEFAULT_PROFILE = _f2.DEFAULT_PROFILE
OTHER_PROFILE = _f2.NO_BOT_CHAT_PROFILE
BOT_CHAT_SESSION_ID = _f2.BOT_CHAT_SESSION_ID
send = _f2.send


# Match the fastest foreground phone cadence; never hide HTTP errors as no prompt.
def wait_for(predicate, *, timeout: float):
    return _f2.wait_for(predicate, timeout=timeout, interval=3.0)


pytestmark = _f2.pytestmark


@pytest.fixture(params=_f2.BUILDS)
def gateway(request: pytest.FixtureRequest, tmp_path: Path):
    """The F2 direct-send gateway, including its pairing pty. Reused, not reimplemented.

    The primary device is enrolled as an approval owner for these cases only (the host controls
    decision is granted, and `_rewrite_config` allowlists it). Generic pairing keeps its denied
    default. No receipt or manifest is involved."""
    yield from _f2.gateway.__wrapped__(request, tmp_path, approval_owner_enrollment=True)


def _notifier(gateway: DirectSendFixture) -> bool:
    """Whether this build's Bot Chat session stream has the approval notifier (a source fact).

    The neutral diagnostic `compat.stream_hook_present` reads one file of the build's own tree. An
    undeterminable result is treated as absent so a positive expectation is never assumed."""
    return compat.stream_hook_present(gateway.build.src_dir) is True


def _assert_no_card_and_command_not_run(
    gateway: DirectSendFixture, target: Path, *, seconds: float = 10.0
) -> None:
    """The notifier-absent expectation: Hermes keeps its own fail-closed behavior. No Bot Chat card
    is invented at any point in the window, and the flagged command never runs."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        code, payload = _prompts(gateway.client)
        assert code == 200, payload
        assert not [
            item for item in payload.get("prompts", []) if item.get("surface") == "bot_chat"
        ], payload
        time.sleep(1.0)
    assert (target / "sentinel").exists(), "a flagged command ran with no way to answer it"


def _prompts(client: Client, profile: str = DEFAULT_PROFILE) -> tuple[int, Any]:
    return client.get(f"/hmp/v1/bots/{profile}/prompts")


def _answer(client: Client, request_id: str, body: dict[str, Any], profile: str = DEFAULT_PROFILE):
    return client.post(f"/hmp/v1/bots/{profile}/prompts/{request_id}", body)


def _phone(client: Client, *, cmid: str, text: str, profile: str = DEFAULT_PROFILE, **extra: Any):
    payload = {"client_message_id": cmid, "text": text, **extra}
    return client.post(f"/hmp/v1/bots/{profile}/phone/messages", payload)


def _user_rows(client: Client, profile: str, cmid: str) -> list[dict[str, Any]]:
    """Durable user rows of the profile's default conversation carrying this client_message_id."""
    status, body = client.get(f"/hmp/v1/bots/{profile}/conversations/default")
    assert status == 200, body
    return [
        row
        for row in body.get("messages", [])
        if row.get("role") == "user" and row.get("client_message_id") == cmid
    ]


def _probe_command(gateway: DirectSendFixture) -> tuple[str, Path]:
    # Even a mistakenly auto-approved command can touch only this test's own sentinel.
    target = gateway.paths.out_dir / "approval-probe"
    target.mkdir()
    (target / "sentinel").write_text("requires explicit consent", encoding="utf-8")
    return f"rm -rf {shlex.quote(str(target))}", target


def test_t7_local_run_approval_unblocks_and_clarify_and_execute_code_do_not_card(
    gateway: DirectSendFixture,
) -> None:
    """No Desktop owner: a flagged terminal command cards, and answering it is what unblocks.
    A clarify tool call and an execute_code tool call on this stream do not become cards."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(
            name="clarify",
            args={"questions": [{"question": "Which?", "choices": ["A", "B"]}]},
        ),
        model.ToolCall(name="execute_code", args={"code": "print(1)"}),
        model.ToolCall(name="terminal", args={"command": command}),
        model.Text("unblocked"),
    )
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="run the checks"
    )
    if not _notifier(gateway):
        # No notifier on this build's session stream: the send still succeeds, no card is invented
        # and Hermes's own fail-closed behavior stops the command. No warning is expected.
        assert status in (200, 202), body
        _assert_no_card_and_command_not_run(gateway, target)
        return
    assert status == 202, (
        "Session-chat stream completed before a human answered. This Hermes route must "
        "register a notifier, emit approval.request and keep the run waiting; "
        f"/v1/runs approval support alone is insufficient: {status}, {body}"
    )

    def card():
        code, payload = _prompts(client)
        assert code == 200, payload
        approvals = [
            item
            for item in payload.get("prompts", [])
            if item.get("kind") == "approval" and item.get("surface") == "bot_chat"
        ]
        return approvals[0] if approvals else None

    prompt = wait_for(card, timeout=30)
    assert prompt, _prompts(client)
    assert target.exists(), "command ran without an answer"
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
        assert code == 200, payload
        kinds = [item.get("kind") for item in payload.get("prompts", [])]
        return "approval" not in kinds

    assert wait_for(lambda: not target.exists(), timeout=30), "approval did not unblock command"
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
        cmid=str(uuid.uuid7()),
        expected_head=head,
        text="while desktop holds it",
    )
    assert status in (202, 200), body

    def marker():
        code, payload = _prompts(client)
        assert code == 200, payload
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
    cmid = str(uuid.uuid7())
    before = len(gateway.fake_model.main_requests())
    first = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="once only")
    second = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="once only")
    assert first[0] == second[0]
    assert second[1] == first[1]
    assert len(gateway.fake_model.main_requests()) == before + 1


def test_t8_phone_approval_clarify_and_unknown_id(gateway: DirectSendFixture) -> None:
    """Phone chat is an `hmp` platform turn. The card's request_id is what unblocks it.
    An unknown ID is 404. A session key in the body is ignored.

    Correlation, by client_message_id only (never text): after the first 202 the real HMP
    snapshot shows exactly one durable user row with the sent cmid; the composer cmid refused
    while clarify is awaiting text never appears in the own default transcript once the answer
    completes; another granted profile's default conversation never holds the first cmid.
    Evidence is booleans only, written after every assertion passes."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}),
        model.ToolCall(
            name="clarify",
            args={"questions": [{"question": "Which path?", "choices": ["Left", "Right"]}]},
        ),
        model.Text("clarify done"),
    )
    client = gateway.client
    cmid = str(uuid.uuid7())
    status, body = _phone(client, cmid=cmid, text="please run it", session_key="ignored")
    assert status == 202, body
    assert body == {"state": "submitted"}

    def own_durable_rows() -> list[dict[str, Any]] | None:
        rows = _user_rows(client, DEFAULT_PROFILE, cmid)
        assert len(rows) <= 1, "a sent cmid became more than one durable user row"
        return rows or None

    assert wait_for(own_durable_rows, timeout=30), "sent cmid never became a durable user row"

    def approval():
        code, payload = _prompts(client)
        assert code == 200, payload
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

    assert target.exists(), "denied command ran"

    def clarify():
        code, payload = _prompts(client)
        assert code == 200, payload
        cards = [item for item in payload.get("prompts", []) if item.get("kind") == "clarify"]
        return cards[0] if cards else None

    card = wait_for(clarify, timeout=30)
    assert card, _prompts(client)
    other = _answer(client, card["request_id"], {"other": True})
    assert other[0] == 200
    assert other[1]["status"] == "awaiting_text"
    assert other[1]["applied"] is False
    # Phone input has no control authority, including free text after Other.
    refused_cmid = str(uuid.uuid7())
    status, body = _phone(client, cmid=refused_cmid, text="neither of those")
    assert status == 409 and body["applied"] is False
    status, body = _answer(client, card["request_id"], {"text": "neither of those"})
    assert status == 200 and body["applied"] is True

    def clarify_settled():
        code, payload = _prompts(client)
        assert code == 200, payload
        return not [item for item in payload.get("prompts", []) if item.get("kind") == "clarify"]

    assert wait_for(clarify_settled, timeout=30)
    assert len(_user_rows(client, DEFAULT_PROFILE, cmid)) == 1
    assert not _user_rows(client, DEFAULT_PROFILE, refused_cmid), "refused composer cmid persisted"
    assert not _user_rows(client, OTHER_PROFILE, cmid), "sent cmid leaked to another profile"

    # Unknown-ID behavior; foreign-user/device isolation is covered by the route unit tests.
    status, body = _answer(client, "not-a-stored-request-id", {"choice": "once"})
    assert status == 404 and body["error"]["code"] == "not_found"

    evidence_dir = os.environ.get("HMP_APPROVAL_EVIDENCE_DIR")
    if evidence_dir:
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        (Path(evidence_dir) / f"phone-correlation-{gateway.build.label}.json").write_text(
            json.dumps(
                {"own_durable_id": True, "other_profile_absent": True, "refused_id_absent": True},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def test_t8_restart_mid_wait_does_not_apply(gateway: DirectSendFixture) -> None:
    """Process memory (KD-8): a restart drops the row. Hermes's queue is gone too. The retry
    must not apply a choice. 404 is the unknown id; 409 stale is the in-process 'nothing
    pending' outcome if a row were still held. Neither has applied true."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}),
    )
    client = gateway.client
    status, body = _phone(client, cmid=str(uuid.uuid7()), text="hold for restart")
    assert status == 202, body

    def approval():
        code, payload = _prompts(client)
        assert code == 200, payload
        cards = [item for item in payload.get("prompts", []) if item.get("kind") == "approval"]
        return cards[0] if cards else None

    prompt = wait_for(approval, timeout=30)
    assert prompt, _prompts(client)
    assert target.exists(), "command ran without an answer"
    request_id = prompt["request_id"]
    gateway.restart_gateway()
    status, body = _answer(gateway.client, request_id, {"choice": "always"})
    assert status in (404, 409), body
    if status == 409:
        assert body["error"]["code"] == "stale"
        assert body["applied"] is False
    else:
        assert body["error"]["code"] == "not_found"


def test_t8_cross_profile_exact_id_answer_is_refused(gateway: DirectSendFixture) -> None:
    """The paired device may use both profiles, but a request ID belongs to the profile that
    raised it. Answering it through the other profile must neither run nor settle the command."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(model.ToolCall(name="terminal", args={"command": command}))
    client = gateway.client
    # Prove the refusal below is not just missing access to the other profile.
    status, body = _prompts(client, OTHER_PROFILE)
    assert status == 200, body
    assert not [i for i in body.get("prompts", []) if i.get("kind") == "approval"], body
    status, body = _phone(client, cmid=str(uuid.uuid7()), text="hold for cross-profile")
    assert status == 202, body

    def approval():
        code, payload = _prompts(client)
        assert code == 200, payload
        cards = [item for item in payload.get("prompts", []) if item.get("kind") == "approval"]
        return cards[0] if cards else None

    prompt = wait_for(approval, timeout=30)
    assert prompt, _prompts(client)
    request_id = prompt["request_id"]
    assert target.exists(), "command ran without an answer"

    # "once" is the choice that would execute, so a leak cannot hide behind a harmless choice.
    status, body = _answer(client, request_id, {"choice": "once"}, profile=OTHER_PROFILE)
    assert status in (403, 404, 409), body
    assert body.get("applied") is not True, body

    code, payload = _prompts(client)
    assert code == 200, payload
    pending = [item.get("request_id") for item in payload.get("prompts", [])]
    assert request_id in pending, "wrong-profile answer settled the approval"
    assert target.exists(), "wrong-profile answer executed the command"

    status, body = _answer(client, request_id, {"choice": "deny"})
    assert status == 200 and body["applied"] is True, body

    def settled():
        code, payload = _prompts(client)
        assert code == 200, payload
        return request_id not in [item.get("request_id") for item in payload.get("prompts", [])]

    assert wait_for(settled, timeout=30)
    assert target.exists() and (target / "sentinel").exists(), "denied command ran"


def _pending_approval(client: Client, request_id: str | None = None):
    code, payload = _prompts(client)
    assert code == 200, payload
    cards = [item for item in payload.get("prompts", []) if item.get("kind") == "approval"]
    if request_id is not None:
        cards = [item for item in cards if item.get("request_id") == request_id]
    return cards[0] if cards else None


def test_t7_bot_chat_exact_id_deny_blocks_command(gateway: DirectSendFixture) -> None:
    """Deny by exact ID leaves the dangerous command unrun; a wrong ID resolves nothing."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}), model.Text("stopped")
    )
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="run the checks"
    )
    if not _notifier(gateway):
        assert status in (200, 202), body
        _assert_no_card_and_command_not_run(gateway, target)
        return
    assert status == 202, body
    prompt = wait_for(
        lambda: (lambda c: c if c and c.get("surface") == "bot_chat" else None)(
            _pending_approval(client)),
        timeout=30,
    )
    assert prompt, _prompts(client)
    request_id = prompt["request_id"]
    status, body = _answer(client, "not-the-request-id", {"choice": "once"})
    assert status == 404 and body.get("applied") is not True, body
    assert _pending_approval(client, request_id), "a wrong ID settled the approval"
    assert (target / "sentinel").exists(), "command ran without an answer"

    status, body = _answer(client, request_id, {"choice": "deny"})
    assert status == 200 and body["applied"] is True, body
    assert wait_for(lambda: not _pending_approval(client, request_id), timeout=30)
    assert (target / "sentinel").exists(), "denied command ran"
    # An already-settled ID cannot be replayed into an approval.
    status, body = _answer(client, request_id, {"choice": "once"})
    assert status in (404, 409) and body.get("applied") is not True, body
    assert (target / "sentinel").exists(), "replayed answer ran the denied command"


def test_t8_phone_text_and_slash_never_resolve_pending_approval(
    gateway: DirectSendFixture,
) -> None:
    """Phone text has no control authority: plaintext approval words and slash commands sent as
    ordinary phone messages neither settle the pending card nor run the command."""
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(model.ToolCall(name="terminal", args={"command": command}))
    client = gateway.client
    status, body = _phone(client, cmid=str(uuid.uuid7()), text="hold for text bypass")
    assert status == 202, body
    prompt = wait_for(lambda: _pending_approval(client), timeout=30)
    assert prompt, _prompts(client)
    request_id = prompt["request_id"]
    for text in ("/approve", "/approve always", "yes", "approve", "/deny", "/stop"):
        status, body = _phone(client, cmid=str(uuid.uuid7()), text=text)
        assert not (isinstance(body, dict) and body.get("applied") is True), (text, status, body)
        assert _pending_approval(client, request_id), f"{text!r} settled the approval"
        assert (target / "sentinel").exists(), f"{text!r} ran the command"
    time.sleep(3)  # a bypass that acts asynchronously would show by now
    assert _pending_approval(client, request_id), "the approval settled without an answer"
    assert (target / "sentinel").exists()

    status, body = _answer(client, request_id, {"choice": "deny"})
    assert status == 200 and body["applied"] is True, body
    assert wait_for(lambda: not _pending_approval(client, request_id), timeout=30)
    assert (target / "sentinel").exists(), "denied command ran"


def test_t7_real_timeout_expires_wait_without_running_command(gateway: DirectSendFixture) -> None:
    """A real Hermes approval wait that outlives approvals.timeout ends fail-closed: the command
    never runs, the card leaves the list, and a late answer by the expired ID applies nothing."""
    gateway._rewrite_config(approval_timeout=8)
    gateway.restart_gateway()  # Hermes reads approvals.timeout when the gateway starts
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}), model.Text("timed out")
    )
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="let it expire"
    )
    if not _notifier(gateway):
        assert status in (200, 202), body
        _assert_no_card_and_command_not_run(gateway, target)
        return
    assert status == 202, body
    prompt = wait_for(lambda: _pending_approval(client), timeout=30)
    assert prompt, _prompts(client)
    request_id = prompt["request_id"]
    assert wait_for(lambda: not _pending_approval(client, request_id), timeout=90), (
        "an unanswered approval never expired"
    )
    assert (target / "sentinel").exists(), "expired approval ran the command"
    status, body = _answer(client, request_id, {"choice": "once"})
    assert status in (404, 409, 410) and body.get("applied") is not True, body
    assert (target / "sentinel").exists(), "a late answer ran the expired command"


@pytest.mark.parametrize("closed_by", ["owner", "flag"])
def test_approvals_fixture_fails_closed(gateway: DirectSendFixture, closed_by: str) -> None:
    """The owner allowlist and the explicit host flag each close every approval route on their own
    (the approval lane has no build list left to close it)."""
    if closed_by == "owner":
        gateway._rewrite_config(owner_device_ids=())
        # Hermes loads platform extras when the adapter connects, just like the flag.
        gateway.restart_gateway()
    else:
        gateway.set_direct_send_flag(False)
    before = len(gateway.fake_model.main_requests())
    for status, body in (
        _prompts(gateway.client),
        _phone(gateway.client, cmid=str(uuid.uuid7()), text="fixture must refuse"),
        _answer(gateway.client, "missing-request", {"choice": "once"}),
    ):
        assert status == (404 if closed_by == "owner" else 503), body
        assert body["error"]["code"] == (
            "not_found" if closed_by == "owner" else "write_gate_closed")
    assert len(gateway.fake_model.main_requests()) == before


def test_manifest_mutation_changes_no_availability(gateway: DirectSendFixture) -> None:
    """Editing or emptying the tested-sample manifests in the scratch plugin copy changes nothing
    after a gateway restart: they are evidence only (spec 034 R5, N30)."""
    manifests = gateway.paths.out_dir / "_hmp_plugin"
    for name in (
        "direct_send_supported_builds.json",
        "read_compat_builds.json",
        "write_supported_builds.json",
    ):
        path = manifests / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "builds" in data:
            data["builds"] = []
        path.write_text(json.dumps(data), encoding="utf-8")
    gateway.restart_gateway()
    status, body = _prompts(gateway.client)
    assert status == 200 and body["prompts"] == [], body


def test_non_owner_bot_chat_send_stays_synchronous_and_never_waits_for_a_card(
    gateway: DirectSendFixture,
) -> None:
    """A device that is not an approval owner keeps the synchronous Bot Chat route exactly as
    before: no stream, so a flagged command does not make the turn wait for `approvals.timeout`,
    no card exists, and every approval route answers 404 (spec 034 D2b, N1, N26)."""
    gateway._rewrite_config(owner_device_ids=())
    gateway.restart_gateway()
    model = gateway.fake_model_module
    command, target = _probe_command(gateway)
    gateway.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}), model.Text("done")
    )
    client = gateway.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    started = time.monotonic()
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="not an owner"
    )
    assert status in (200, 202), body
    assert time.monotonic() - started < gateway.approval_timeout, "the turn waited for a card"
    status, body = _prompts(client)
    assert (status, body["error"]["code"]) == (404, "not_found"), body
    assert (target / "sentinel").exists(), "a non-owner turn ran a flagged command"
