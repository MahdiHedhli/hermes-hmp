"""Spec 034 R13, R15, N23, N29: use-time capability failures and log hygiene, at the routes.

A Hermes helper that fails when HMP calls it is an actual capability failure for that operation:
a fixed outcome log, `503 api_server_unavailable` without `applied`, never a fabricated success,
and never a claim that Hermes's request ended. Canary values stand in for every private value and
none may reach a log record.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import direct_send as ds
from hmp_plugin import prompts
from hmp_plugin.logging_policy import LOGGER_NAME

from .hmp_kit import Env, code, get, pair, post, run
from .test_approval_route_gates import BOT, _row, _setup
from .test_approvals import REQ, _frame

CANARY_COMMAND = "rm -rf /canary-private-command"
CANARY_DESCRIPTION = "canary description text"
CANARY_QUESTION = "canary question text?"
CANARY_CHOICE = "canary-choice-label"
CANARY_TEXT = "canary free text answer"
CANARY_KEY = "k" * 20
CANARIES = (CANARY_COMMAND, CANARY_DESCRIPTION, CANARY_QUESTION, CANARY_CHOICE, CANARY_TEXT)


def _text(caplog: pytest.LogCaptureFixture) -> str:
    return " ".join(r.getMessage() for r in caplog.records)


def _assert_clean(caplog: pytest.LogCaptureFixture) -> None:
    text = _text(caplog)
    for canary in CANARIES:
        assert canary not in text, canary
    assert CANARY_KEY not in text and "Authorization" not in text and "Bearer" not in text


def test_r15_a_phone_approval_helper_failing_is_unavailable_not_applied_not_stale(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    env = Env(tmp_path)
    calls = _setup(env)

    def failing(*_a: Any, **_k: Any) -> int:
        raise prompts.HelperUnavailableError("phone chat helper failed")

    env.bridge.resolve_gateway_approval = failing  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="phone_chat")
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (503, "api_server_unavailable")
        assert "applied" not in resp
        assert row.status == "open" and row.stored_status is None  # not expired, not settled
        # The row stays listed; HMP does not claim the Hermes wait ended.
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert [p["request_id"] for p in listed["prompts"]] == [REQ]

    run(env, scenario)
    assert "event=approval_helper outcome=unavailable" in _text(caplog)
    _assert_clean(caplog)
    assert calls["native"] == []


def test_r15_clarify_and_other_helper_failures_are_unavailable_too(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    env = Env(tmp_path)
    _setup(env)

    def failing(*_a: Any, **_k: Any) -> bool:
        raise prompts.HelperUnavailableError("phone chat helper failed")

    env.bridge.resolve_gateway_clarify = failing  # type: ignore[method-assign]
    env.bridge.mark_clarify_awaiting_text = failing  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="phone_chat", kind="clarify")
        for body in ({"choice": "Ship"}, {"other": True}):
            status, resp = await post(
                client, f"/bots/{BOT}/prompts/{REQ}", body, headers=env.headers(dev)
            )
            assert (status, code(resp)) == (503, "api_server_unavailable"), body
            assert "applied" not in resp
        assert row.status == "open"

    run(env, scenario)
    _assert_clean(caplog)


def test_r15_a_failing_list_reconcile_keeps_the_row_and_still_answers_the_list(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    env = Env(tmp_path)
    _setup(env)

    def failing(*_a: Any, **_k: Any) -> list[dict[str, Any]]:
        raise prompts.HelperUnavailableError("phone chat helper failed")

    env.bridge.list_gateway_approvals = failing  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="phone_chat")
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200 and [p["request_id"] for p in listed["prompts"]] == [REQ]
        assert row.status == "open"  # unavailable is not proof the waiter is gone

    run(env, scenario)
    assert "outcome=unavailable" in _text(caplog)


def test_r15_a_failing_phone_send_preflight_is_unavailable_and_nothing_is_delivered(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    env = Env(tmp_path)
    _setup(env)
    delivered: list[str] = []

    def failing(*_a: Any, **_k: Any) -> list[dict[str, Any]]:
        raise prompts.HelperUnavailableError("phone chat helper failed")

    env.bridge.list_gateway_approvals = failing  # type: ignore[method-assign]
    env.bridge.phone_session_key = lambda user, profile: "sess-phone"  # type: ignore[method-assign]

    async def deliver(**_k: Any) -> bool:
        delivered.append("x")
        return True

    env.bridge.deliver_phone_message = deliver  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, resp = await post(
            client,
            f"/bots/{BOT}/phone/messages",
            {"client_message_id": "01890000-0000-7000-8000-000000000001", "text": CANARY_TEXT},
            headers=env.headers(dev),
        )
        assert (status, code(resp)) == (503, "api_server_unavailable")
        assert "applied" not in resp

    run(env, scenario)
    assert delivered == []
    assert "event=approval_helper outcome=unavailable" in _text(caplog)
    _assert_clean(caplog)


def test_n29_the_normal_flow_logs_only_fixed_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    env = Env(tmp_path)
    calls = _setup(env)

    async def native(endpoint: Any, run_id: str, request_id: str, choice: str) -> str:
        calls["native"].append(choice)
        return "accepted"

    monkeypatch.setattr(ds, "aiohttp_approval_call", native)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        env.ctx.prompt_store.put(
            prompts.PromptRow(
                iid=env.iid, user_id=_user(env, dev), profile=BOT, request_id=REQ, kind="approval",
                surface="bot_chat", choices=("once", "deny"), command=CANARY_COMMAND,
                description=CANARY_DESCRIPTION, run_id="run_" + "34" * 16, observed_at=1,
            )
        )
        env.ctx.prompt_store.put(
            prompts.PromptRow(
                iid=env.iid, user_id=_user(env, dev), profile=BOT, request_id="clar" + "0" * 20,
                kind="clarify", surface="phone_chat", choices=(CANARY_CHOICE, "Wait"),
                question=CANARY_QUESTION, session_key="sess-phone", observed_at=1,
            )
        )
        await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        await post(
            client, f"/bots/{BOT}/prompts/clar{'0' * 20}", {"choice": CANARY_CHOICE},
            headers=env.headers(dev),
        )
        await post(
            client, f"/bots/{BOT}/prompts/clar{'0' * 20}", {"text": CANARY_TEXT},
            headers=env.headers(dev),
        )

    run(env, scenario)
    _assert_clean(caplog)
    assert "event=prompt_answer outcome=resolved" in _text(caplog)


def _user(env: Env, dev: Any) -> str:
    row = (
        env.store._require_conn()
        .execute("SELECT user_id FROM devices WHERE device_id = ?", (dev.device_id,))
        .fetchone()
    )
    return str(row["user_id"])


@pytest.mark.asyncio
async def test_n29_stream_frames_and_failures_log_no_prompt_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    store = prompts.PromptStore(clock=lambda: 1)
    bind = ds.StreamBind(
        store=store, iid="i" * 40, user_id="hmpu_" + "ab" * 16, profile="b", now=lambda: 1,
        timeout_s=300,
    )

    async def parts():
        yield _frame("run.started", {"run_id": "r1"})
        yield _frame(
            "approval.request",
            {"run_id": "r1", "request_id": REQ, "command": CANARY_COMMAND,
             "description": CANARY_DESCRIPTION, "choices": ["once", "deny"]},
        )
        yield _frame("run.failed", {"run_id": "r1", "error": CANARY_TEXT})
        yield _frame("done", {})

    await ds.consume_sse(parts(), bind=bind)
    _assert_clean(caplog)


@pytest.mark.asyncio
async def test_n23_a_stream_with_no_notifier_sends_cleanly_with_no_card_and_no_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """On a release whose session stream has no approval notifier Hermes emits no
    `approval.request`. The send still succeeds, HMP invents no card, and nothing warns."""
    caplog.set_level(logging.DEBUG)
    store = prompts.PromptStore(clock=lambda: 1)
    bind = ds.StreamBind(
        store=store, iid="i" * 40, user_id="hmpu_" + "ab" * 16, profile="b", now=lambda: 1,
        timeout_s=300,
    )

    async def parts():
        yield _frame("run.started", {"run_id": "r1"})
        yield _frame("message.started", {})
        yield _frame("assistant.completed", {"content": "done", "session_id": "s1"})
        yield _frame("run.completed", {"run_id": "r1", "session_id": "s1"})
        yield _frame("done", {})

    result = await ds.consume_sse(parts(), bind=bind)
    assert result.status == 200 and result.body["message"]["content"] == "done"  # type: ignore[index]
    assert not store._rows  # no fabricated card
    assert store.list_visible(bind.iid, bind.user_id, bind.profile) == ()
    text = _text(caplog).lower()
    for word in ("warning", "unsupported", "unvalidated", "not one of"):
        assert word not in text
    assert all(r.levelno < logging.WARNING for r in caplog.records)
