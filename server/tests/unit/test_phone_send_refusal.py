"""AP-6: only an exact False from delivery is a definitive refusal (`applied:false`)."""

from __future__ import annotations

import pytest

from hmp_plugin import prompts
from hmp_plugin.prompts import PromptStore

IID = "iid-1"
USER = "u_user"
PROFILE = "alpha"
KEY = "namespace:hmp:dm:phone-session-key"


class Sqlite:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str, str], dict] = {}

    def reserve_phone_cmid(self, iid, user_id, profile, cmid, payload_hash, now):
        del now
        key = (iid, user_id, profile, cmid)
        if key in self.rows:
            return self.rows[key], False
        row = {"payload_hash": payload_hash, "status": "pending", "result_json": None}
        self.rows[key] = row
        return row, True

    def finalize_phone_cmid(self, iid, user_id, profile, cmid, *, status, result_json, updated_at):
        del updated_at
        row = self.rows[(iid, user_id, profile, cmid)]
        row["status"] = status
        row["result_json"] = result_json


class Harness:
    def __init__(self) -> None:
        self.store = PromptStore(clock=lambda: 1)
        self.sqlite = Sqlite()
        self.delivered = 0
        self.outcome: object = True
        self.key: object = KEY
        self.approvals: object = []

    async def send(self, cmid: str = "cmid-1", text: str = "hello") -> prompts.HttpResult:
        async def deliver():
            self.delivered += 1
            if isinstance(self.outcome, Exception):
                raise self.outcome
            return self.outcome

        return await prompts.handle_phone_send(
            prompts=self.store,
            sqlite_store=self.sqlite,
            iid=IID,
            user_id=USER,
            profile=PROFILE,
            chat_id="c_chat",
            cmid=cmid,
            text=text,
            now=10,
            resolver=None,  # type: ignore[arg-type]
            session_key=lambda: self.key,  # type: ignore[arg-type,return-value]
            pending_approvals=lambda _key: self.approvals,
            deliver=deliver,
        )

    def stored_status(self, cmid: str = "cmid-1") -> str:
        return self.sqlite.rows[(IID, USER, PROFILE, cmid)]["status"]


@pytest.mark.asyncio
async def test_exact_false_is_definitive_refusal_and_replays_without_redelivery() -> None:
    h = Harness()
    h.outcome = False
    first = await h.send()
    assert first.status == 503
    assert first.body["error"]["code"] == "api_server_unavailable"
    assert first.body["applied"] is False
    assert h.stored_status() == "rejected"
    assert len(h.store.observations(IID, USER, PROFILE)) == 0
    h.outcome = True  # a replay must never reach delivery again
    replay = await h.send()
    assert (replay.status, replay.body) == (first.status, first.body)
    assert h.delivered == 1
    assert len(h.store.observations(IID, USER, PROFILE)) == 0


@pytest.mark.asyncio
async def test_exact_true_is_unchanged_submitted() -> None:
    h = Harness()
    result = await h.send()
    assert (result.status, result.body) == (202, {"state": "submitted"})
    assert h.stored_status() == "submitted"
    assert len(h.store.observations(IID, USER, PROFILE)) == 1


def _assert_unknown(result: prompts.HttpResult) -> None:
    assert "applied" not in result.body
    assert result.body.get("applied") is not False


@pytest.mark.asyncio
async def test_none_is_unknown_without_applied_false() -> None:
    h = Harness()
    h.outcome = None
    result = await h.send()
    assert (result.status, result.body) == (200, {"state": "unknown"})
    assert h.stored_status() == "unknown"
    h.outcome = False
    replay = await h.send()
    assert replay.body == {"state": "unknown"} and h.delivered == 1


@pytest.mark.asyncio
async def test_delivery_exception_is_unknown_not_false_not_sent() -> None:
    h = Harness()
    h.outcome = RuntimeError("boom")
    result = await h.send()
    assert result.status == 503
    assert result.body["error"]["code"] == "api_server_unavailable"
    _assert_unknown(result)
    assert h.stored_status() == "unknown"
    h.outcome = True
    replay = await h.send()
    assert replay.body == result.body and h.delivered == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", [0, 1, "", "yes", "False", [], {}, 0.0, object()])
async def test_malformed_delivery_result_is_conservatively_unknown(malformed) -> None:
    h = Harness()
    h.outcome = malformed
    result = await h.send()
    assert (result.status, result.body) == (200, {"state": "unknown"})
    assert h.stored_status() == "unknown"
    assert len(h.store.observations(IID, USER, PROFILE)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [None, "", 7])
async def test_session_key_uncertainty_is_unknown_without_delivery(key) -> None:
    h = Harness()
    h.key = key
    result = await h.send()
    assert result.status == 503
    assert result.body["error"]["code"] == "api_server_unavailable"
    _assert_unknown(result)
    assert h.stored_status() == "unknown"
    assert h.delivered == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("probe", [None, "nope", ("x",), {"a": 1}])
async def test_approval_probe_non_list_is_unknown_without_delivery(probe) -> None:
    h = Harness()
    h.approvals = probe
    result = await h.send()
    assert result.status == 503
    _assert_unknown(result)
    assert h.stored_status() == "unknown"
    assert h.delivered == 0


@pytest.mark.asyncio
async def test_pending_approval_gate_stays_stale_applied_false_without_delivery() -> None:
    h = Harness()
    h.approvals = [{"request_id": "x"}]
    result = await h.send()
    assert result.status == 409 and result.body["applied"] is False
    assert result.body["error"]["code"] == "stale"
    assert h.stored_status() == "rejected"
    assert h.delivered == 0


@pytest.mark.asyncio
async def test_fresh_gate_reply_does_not_settle_earlier_ambiguous_attempt() -> None:
    h = Harness()
    h.outcome = None
    ambiguous = await h.send("cmid-a")
    assert ambiguous.body == {"state": "unknown"}
    h.approvals = [{"request_id": "x"}]
    gated = await h.send("cmid-b")
    assert gated.status == 409 and gated.body["applied"] is False
    # The earlier attempt is still unknown and replays as such, never as applied:false.
    assert h.stored_status("cmid-a") == "unknown"
    h.approvals = []
    h.outcome = False
    replay = await h.send("cmid-a")
    assert replay.body == {"state": "unknown"}
    assert h.delivered == 1
