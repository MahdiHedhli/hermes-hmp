"""R14: how a native Bot Chat answer result is classified (N8, N18, N19).

Only a bounded, parsed native JSON error code makes a row stale. Everything else that is not a
proven application leaves the row open as `api_server_unavailable`. The response text is parsed,
never echoed or logged. These tests drive the real classifier, the real request function over a
fake HTTP session (no socket), and the real route.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import direct_send as ds
from hmp_plugin.contract import DirectSendEndpoint
from hmp_plugin.logging_policy import LOGGER_NAME

from .hmp_kit import Env, code, get, pair, post, run
from .test_approval_route_gates import BOT, _row, _setup
from .test_approvals import REQ, RUN

ENDPOINT = DirectSendEndpoint(host="127.0.0.1", port=9, api_key="k" * 20, path_prefix="")


def _error(status_code: str) -> bytes:
    return json.dumps(
        {"error": {"message": "text", "type": "invalid_request_error", "param": None,
                   "code": status_code}}
    ).encode()


# --------------------------------------------------------------------------------------------
# The classifier table
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        # accepted: a non-bool integer resolved > 0, on a 200
        (200, b'{"object":"hermes.run.approval_response","resolved":1}', "accepted"),
        (200, b'{"resolved":2}', "accepted"),
        # stale: exactly the three native pairs
        (409, _error("approval_not_pending"), "stale"),
        (409, _error("approval_not_active"), "stale"),
        (404, _error("run_not_found"), "stale"),
        # malformed or non-positive 200 is unavailable, never accepted and never stale
        (200, b'{"resolved":0}', "unavailable"),
        (200, b'{"resolved":-1}', "unavailable"),
        (200, b'{"resolved":true}', "unavailable"),
        (200, b'{"resolved":1.0}', "unavailable"),
        (200, b'{"resolved":"1"}', "unavailable"),
        (200, b'{"resolved":null}', "unavailable"),
        (200, b"{}", "unavailable"),
        (200, b"[]", "unavailable"),
        (200, b"not json", "unavailable"),
        (200, b"", "unavailable"),
        (200, b"\xff\xfe", "unavailable"),
        (200, None, "unavailable"),
        # an unknown 409 code, a code on the wrong status, non-JSON 404: unavailable
        (409, _error("something_else"), "unavailable"),
        (409, _error("run_not_found"), "unavailable"),
        (404, _error("approval_not_pending"), "unavailable"),
        (404, b"<html>not found</html>", "unavailable"),
        (404, b"", "unavailable"),
        (404, b'{"error":"run_not_found"}', "unavailable"),
        (404, b'{"error":{"code":["run_not_found"]}}', "unavailable"),
        (404, b'{"error":{"code":null}}', "unavailable"),
        (409, b"{}", "unavailable"),
        (409, None, "unavailable"),
        # every other status
        (400, _error("approval_not_pending"), "unavailable"),
        (401, _error("approval_not_pending"), "unavailable"),
        (403, _error("run_not_found"), "unavailable"),
        (302, _error("run_not_found"), "unavailable"),
        (500, _error("approval_not_pending"), "unavailable"),
        (503, b'{"resolved":1}', "unavailable"),
    ],
)
def test_the_classification_table(status: int, body: bytes | None, expected: str) -> None:
    assert ds.classify_native_answer(status, body) == expected


def test_a_note_in_the_message_never_turns_an_unknown_code_stale() -> None:
    body = json.dumps(
        {"error": {"message": "approval_not_pending", "code": "other_code"}}
    ).encode()
    assert ds.classify_native_answer(409, body) == "unavailable"


# --------------------------------------------------------------------------------------------
# The request function over a fake session (no socket)
# --------------------------------------------------------------------------------------------


class _Content:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def read(self, n: int = -1) -> bytes:
        chunk, self._body = self._body[:n], self._body[n:]
        return chunk


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.content = _Content(body)

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False


def _fake_session(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes, *, fail: Exception | None = None
) -> dict[str, Any]:
    seen: dict[str, Any] = {"posts": 0}

    class Session:
        def __init__(self, **kwargs: Any) -> None:
            seen["session"] = kwargs

        async def __aenter__(self) -> Session:
            return self

        async def __aexit__(self, *_exc: object) -> bool:
            return False

        def post(self, url: str, **kwargs: Any) -> _Response:
            seen["posts"] += 1
            seen["url"], seen["kwargs"] = url, kwargs
            if fail is not None:
                raise fail
            return _Response(status, body)

    monkeypatch.setattr(ds.aiohttp, "ClientSession", Session)
    return seen


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (200, b'{"resolved":1}', "accepted"),
        (409, _error("approval_not_pending"), "stale"),
        (404, _error("run_not_found"), "stale"),
        (403, _error("run_not_found"), "unavailable"),
        (401, b"{}", "unavailable"),
        (404, b"<html></html>", "unavailable"),
        (500, b"{}", "unavailable"),
        (302, b"", "unavailable"),
        (200, b'{"resolved":0}', "unavailable"),
    ],
)
async def test_the_request_sends_exactly_choice_and_request_id_and_does_not_retry(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes, expected: str
) -> None:
    seen = _fake_session(monkeypatch, status, body)
    assert await ds.aiohttp_approval_call(ENDPOINT, RUN, REQ, "once") == expected
    assert seen["posts"] == 1  # no transport retry
    assert seen["kwargs"]["json"] == {"choice": "once", "request_id": REQ}  # never all/resolve_all
    assert seen["kwargs"]["allow_redirects"] is False
    assert seen["session"]["trust_env"] is False
    assert seen["url"].startswith("http://127.0.0.1:9/v1/runs/")


@pytest.mark.asyncio
async def test_timeouts_and_connection_failures_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for failure in (TimeoutError(), aiohttp.ClientConnectionError("refused")):
        seen = _fake_session(monkeypatch, 200, b"{}", fail=failure)
        assert await ds.aiohttp_approval_call(ENDPOINT, RUN, REQ, "deny") == "unavailable"
        assert seen["posts"] == 1


@pytest.mark.asyncio
async def test_an_oversized_response_is_unavailable_not_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    big = b'{"error":{"code":"run_not_found"},"pad":"' + b"x" * (ds.SSE_MAX_FRAME_BYTES + 5) + b'"}'
    _fake_session(monkeypatch, 404, big)
    assert await ds.aiohttp_approval_call(ENDPOINT, RUN, REQ, "once") == "unavailable"


@pytest.mark.asyncio
async def test_a_valid_json_200_at_exactly_one_byte_over_the_cap_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = b'{"resolved":1,"pad":"'
    body = head + b"x" * (ds.SSE_MAX_FRAME_BYTES + 1 - len(head) - 2) + b'"}'
    assert len(body) == ds.SSE_MAX_FRAME_BYTES + 1
    assert json.loads(body)["resolved"] == 1  # valid JSON that would classify as accepted
    seen = _fake_session(monkeypatch, 200, body)
    assert await ds.aiohttp_approval_call(ENDPOINT, RUN, REQ, "once") == "unavailable"
    assert seen["posts"] == 1


@pytest.mark.asyncio
async def test_an_unknown_choice_or_empty_ids_never_reach_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _fake_session(monkeypatch, 200, b'{"resolved":1}')
    assert await ds.aiohttp_approval_call(ENDPOINT, RUN, REQ, "all") == "unavailable"
    assert await ds.aiohttp_approval_call(ENDPOINT, "", REQ, "once") == "unavailable"
    assert await ds.aiohttp_approval_call(ENDPOINT, RUN, "", "once") == "unavailable"
    assert seen["posts"] == 0


# --------------------------------------------------------------------------------------------
# At the route: stale expires the row, unavailable leaves it open (N8, N18, N19)
# --------------------------------------------------------------------------------------------


def _answer_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdicts: list[str]):
    env = Env(tmp_path)
    calls = _setup(env)
    sent: list[tuple[str, str, str]] = []

    async def fake(endpoint: Any, run_id: str, request_id: str, choice: str) -> str:
        sent.append((run_id, request_id, choice))
        return verdicts.pop(0)

    monkeypatch.setattr(ds, "aiohttp_approval_call", fake)
    return env, calls, sent


def test_n8_a_native_stale_is_409_applied_false_and_expires_the_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, _calls, sent = _answer_env(tmp_path, monkeypatch, ["stale"])

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="bot_chat")
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp), resp["applied"]) == (409, "stale", False)
        assert row.status == "expired"
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert listed["prompts"] == []
        # The stored stale answer replays without a second native call.
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (409, "stale")
        assert len(sent) == 1

    run(env, scenario)


def test_n18_n19_an_unavailable_native_result_is_503_without_applied_and_keeps_the_row_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    env, _calls, sent = _answer_env(tmp_path, monkeypatch, ["unavailable", "accepted"])
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        row = _row(env, dev, surface="bot_chat")
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (503, "api_server_unavailable")
        assert "applied" not in resp  # no claim either way
        assert row.status == "open" and row.stored_status is None
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert [p["request_id"] for p in listed["prompts"]] == [REQ]
        assert len(sent) == 1  # not retried by HMP
        # The owner may try again deliberately; this time Hermes settles it.
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert status == 200 and resp["applied"] is True
        assert row.status == "resolved" and len(sent) == 2

    run(env, scenario)
    text = " ".join(rec.getMessage() for rec in caplog.records)
    assert "outcome=unavailable" in text
    assert SECRET_NOT_LOGGED not in text


SECRET_NOT_LOGGED = "rm -rf /super-secret-path"
