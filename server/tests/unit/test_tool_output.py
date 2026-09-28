"""Tool output on the read path (additive wire fields, V-3).

Hermes `messages` columns, from `hermes_state_common.py` (Hermes 8afaab37): `tool_calls` TEXT
(JSON) on assistant rows, `tool_name` TEXT and `tool_call_id` TEXT on tool rows. `SessionDB.
get_messages` (`hermes_state_messages.py`) returns `tool_calls` decoded to a list. The bridge is
the only module that reads them. Nothing in this path logs message content (SEC-4).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from hmp_plugin.bridge import HermesReadBridge
from hmp_plugin.contract import TOOL_ARGUMENTS_CAP, TOOL_OUTPUT_CAP, ConversationRef
from hmp_plugin.reads import _wire
from hmp_plugin.request_ctx import _plain

from .fake_hermes import FakeDirectory, World

USER = "hmpu_" + "a" * 32


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


@pytest.fixture
def bridge(world: World) -> HermesReadBridge:
    directory = FakeDirectory()
    directory.chats[(USER, "alpha")] = "c_" + "1" * 32
    world.start_conversation("alpha", "c_" + "1" * 32, "s1")
    return HermesReadBridge(world.adapter, directory, hermes=world.api)  # type: ignore[arg-type]


def _latest(bridge: HermesReadBridge) -> list:
    return bridge.latest(ConversationRef(USER, "alpha", "s1"), 20)


def _body(row: object) -> dict:
    return _plain(_wire(row))  # type: ignore[arg-type]


def test_caps_are_the_contract_numbers() -> None:
    assert TOOL_ARGUMENTS_CAP == 500
    assert TOOL_OUTPUT_CAP == 4000


def test_assistant_tool_calls_are_compact_and_optional(
    world: World, bridge: HermesReadBridge
) -> None:
    calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "terminal",
                "arguments": '{ "command" : "ls" , "path" : "/tmp" }',
            },
        }
    ]
    db = world.dbs["alpha"]
    db.append("s1", "user", "hello")
    db.append("s1", "assistant", "", tool_calls=calls)
    db.append(
        "s1",
        "assistant",
        "same calls as stored JSON text",
        tool_calls=json.dumps(calls),
    )

    user, decoded, stored = _latest(bridge)
    assert user.role == "user" and user.tool_calls == () and user.tool_name is None
    assert "tool_calls" not in _body(user)
    assert set(_body(user)) == {"id", "role", "text", "client_message_id", "created_at"}

    for row in (decoded, stored):
        assert row.role == "assistant"
        assert len(row.tool_calls) == 1
        call = row.tool_calls[0]
        assert call.id == "call_1" and call.name == "terminal"
        assert call.arguments == '{"command":"ls","path":"/tmp"}'
        assert call.arguments_truncated is False
        wire = _body(row)["tool_calls"]
        assert wire == [
            {
                "id": "call_1",
                "name": "terminal",
                "arguments": '{"command":"ls","path":"/tmp"}',
                "arguments_truncated": False,
            }
        ]
        assert "tool_name" not in _body(row) and "truncated" not in _body(row)


def test_arguments_cap_drops_the_rest(world: World, bridge: HermesReadBridge) -> None:
    full = {"command": "x" * 800}
    tail = "x" * 800
    world.dbs["alpha"].append(
        "s1",
        "assistant",
        "",
        tool_calls=[
            {
                "id": "call_long",
                "function": {"name": "terminal", "arguments": full},
            },
            {"name": "bare_name", "arguments": "not json " + tail},
            {"function": {"arguments": "{}"}},  # no name: skipped
            "not-a-call",
        ],
    )
    row = _latest(bridge)[0]
    assert [c.name for c in row.tool_calls] == ["terminal", "bare_name"]
    capped, raw = row.tool_calls
    assert capped.arguments_truncated is True and len(capped.arguments) == TOOL_ARGUMENTS_CAP
    assert tail not in capped.arguments
    assert raw.arguments_truncated is True and len(raw.arguments) == TOOL_ARGUMENTS_CAP
    assert raw.id == ""
    assert tail not in raw.arguments


def test_bad_tool_calls_do_not_fail_the_row(world: World, bridge: HermesReadBridge) -> None:
    world.dbs["alpha"].append("s1", "assistant", "still here", tool_calls="{not json")
    row = _latest(bridge)[0]
    assert row.role == "assistant" and row.text == "still here" and row.tool_calls == ()
    assert "tool_calls" not in _body(row)


def test_tool_row_caps_output_and_keeps_the_role(
    world: World, bridge: HermesReadBridge, caplog: pytest.LogCaptureFixture
) -> None:
    secret = ("TOOL_SECRET_DO_NOT_LOG_" + ("y" * TOOL_OUTPUT_CAP)) + "UNIQUE_TAIL_MARKER"
    tail = "UNIQUE_TAIL_MARKER"
    world.dbs["alpha"].append(
        "s1",
        "tool",
        secret,
        tool_name="terminal",
        tool_call_id="call_1",
    )
    world.dbs["alpha"].append("s1", "tool", "short", tool_name="web", tool_call_id="call_2")
    # A long user/assistant message is not the tool cap.
    long_user = "u" * (TOOL_OUTPUT_CAP + 50)
    world.dbs["alpha"].append("s1", "user", long_user)

    with caplog.at_level(logging.DEBUG):
        tool, short, user = _latest(bridge)

    assert tool.role == "tool"
    assert tool.tool_name == "terminal" and tool.tool_call_id == "call_1"
    assert tool.truncated is True and len(tool.text) == TOOL_OUTPUT_CAP
    assert tool.text == secret[:TOOL_OUTPUT_CAP]
    assert tail not in tool.text
    body = _body(tool)
    assert body["truncated"] is True and body["tool_name"] == "terminal"
    assert body["tool_call_id"] == "call_1" and "tool_calls" not in body
    assert tail not in body["text"] and "TOOL_SECRET_DO_NOT_LOG_" in body["text"]

    assert short.truncated is False and short.text == "short"
    assert "truncated" not in _body(short)
    assert user.role == "user" and user.text == long_user and user.truncated is False
    assert "TOOL_SECRET_DO_NOT_LOG_" not in caplog.text
    assert tail not in caplog.text
