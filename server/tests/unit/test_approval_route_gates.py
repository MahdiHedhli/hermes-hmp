"""Spec 034 route gates, at the real HTTP route (R6, R7, N1-N7, N31, N32).

Every case drives the actual aiohttp app through the bearer middleware. A spy bridge records each
call, so "returns before endpoint resolution, listing, resolver or delivery" is asserted by calls
that did not happen. Nothing here imports Hermes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import prompts
from hmp_plugin.contract import AuthzState, DirectSendEndpoint
from hmp_plugin.prompts import PromptRow

from .hmp_kit import Device, Env, code, get, pair, post, run
from .test_approvals import REQ, RUN, SECRET_COMMAND, _arm

BOT = "b"


def _user_of(env: Env, dev: Device) -> str:
    row = (
        env.store._require_conn()
        .execute("SELECT user_id FROM devices WHERE device_id = ?", (dev.device_id,))
        .fetchone()
    )
    return str(row["user_id"])


def _row(env: Env, dev: Device, *, surface: str, kind: str = "approval", **extra: Any) -> PromptRow:
    row = PromptRow(
        iid=env.iid,
        user_id=_user_of(env, dev),
        profile=BOT,
        request_id=extra.pop("request_id", REQ),
        kind=kind,
        surface=surface,
        choices=("once", "deny") if kind == "approval" else ("Ship", "Wait"),
        command=SECRET_COMMAND if kind == "approval" else None,
        question="Ship?" if kind == "clarify" else None,
        run_id=RUN if surface == "bot_chat" else None,
        session_key="sess-phone" if surface == "phone_chat" else None,
        observed_at=env.clock.now,
        expires_at=env.clock.now + 300,
        **extra,
    )
    env.ctx.prompt_store.put(row)
    return row


def _setup(
    env: Env, *, approvals: bool = True, phone: bool = True, flag: bool = True
) -> dict[str, list[tuple[Any, ...]]]:
    """Both members as given; the bridge records every Hermes-facing call."""
    _arm(env, flag=flag)
    env.ctx.approvals_available = lambda: approvals
    env.ctx.phone_chat_available = lambda: phone
    calls: dict[str, list[tuple[Any, ...]]] = {
        "endpoint": [], "list": [], "resolve": [], "clarify": [], "native": []
    }

    def endpoint(*args: Any, **_k: Any) -> DirectSendEndpoint:
        calls["endpoint"].append(args)
        return DirectSendEndpoint(host="127.0.0.1", port=9, api_key="k" * 20, path_prefix="")

    def lister(*args: Any, **_k: Any) -> list[dict[str, Any]]:
        calls["list"].append(args)
        # Hermes still has these requests pending, so the list reconcile keeps their rows.
        return [
            {"request_id": REQ, "command": SECRET_COMMAND},
            {"request_id": "phone_" + "1" * 20, "command": SECRET_COMMAND},
        ]

    def resolve(*args: Any, **_k: Any) -> int:
        calls["resolve"].append(args)
        return 1

    def clarify(*args: Any, **_k: Any) -> bool:
        calls["clarify"].append(args)
        return True

    env.bridge.direct_send_endpoint = endpoint  # type: ignore[method-assign]
    env.bridge.list_gateway_approvals = lister  # type: ignore[method-assign]
    env.bridge.resolve_gateway_approval = resolve  # type: ignore[method-assign]
    env.bridge.resolve_gateway_clarify = clarify  # type: ignore[method-assign]
    return calls


def _native(monkeypatch: pytest.MonkeyPatch, calls: dict[str, list[tuple[Any, ...]]], verdict: str):
    async def fake(endpoint: Any, run_id: str, request_id: str, choice: str) -> str:
        calls["native"].append((run_id, request_id, choice))
        return verdict

    from hmp_plugin import direct_send

    monkeypatch.setattr(direct_send, "aiohttp_approval_call", fake)


def _no_hermes_call(calls: dict[str, list[tuple[Any, ...]]]) -> None:
    assert calls["list"] == [] and calls["resolve"] == [] and calls["clarify"] == []
    assert calls["native"] == []


# --------------------------------------------------------------------------------------------
# Owner, controls, denial (N1, N2, N3, N31)
# --------------------------------------------------------------------------------------------


def test_n1_n2_a_paired_authorized_non_owner_gets_404_everywhere(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls = _setup(env)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)  # bot-authorized, same user, in no allowlist
        env.ctx.owner_device_ids = lambda: frozenset()
        _row(env, dev, surface="bot_chat")
        for method, path, body in (
            ("GET", f"/bots/{BOT}/prompts", None),
            ("POST", f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}),
            ("POST", f"/bots/{BOT}/phone/messages", {"client_message_id": "c", "text": "hi"}),
        ):
            status, resp = (
                await get(client, path, headers=env.headers(dev))
                if method == "GET"
                else await post(client, path, body, headers=env.headers(dev))
            )
            assert (status, code(resp)) == (404, "not_found"), path
        # N2: a controls grant without an allowlist entry is still a non-owner.
        assert env.store.set_owner_controls(dev.device_id, allowed=True, now=env.clock.now)
        status, resp = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert (status, code(resp)) == (404, "not_found")
        _no_hermes_call(calls)
        assert calls["endpoint"] == []

    run(env, scenario)


def test_n3_a_host_denial_recorded_while_a_card_is_open_closes_the_next_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    calls = _setup(env)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        _row(env, dev, surface="bot_chat")
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200 and len(listed["prompts"]) == 1
        assert env.store.set_owner_controls(dev.device_id, allowed=False, now=env.clock.now)
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (404, "not_found")
        assert calls["native"] == []

    run(env, scenario)


def test_n31_removal_from_the_allowlist_while_a_card_is_open_closes_the_next_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    calls = _setup(env)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        owners = {dev.device_id}
        env.ctx.owner_device_ids = lambda: frozenset(owners)
        _row(env, dev, surface="bot_chat")
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert status == 200 and resp["applied"] is True
        owners.clear()  # the host edits the live config
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (404, "not_found")
        assert len(calls["native"]) == 1  # not even the idempotent replay reaches Hermes

    run(env, scenario)


def test_n32_a_revoked_device_is_401_before_any_gate_work(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls = _setup(env)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        env.store._require_conn().execute(
            "UPDATE devices SET state = 'REVOKED' WHERE device_id = ?", (dev.device_id,)
        )
        status, _resp = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 401
        assert calls["endpoint"] == []

    run(env, scenario)


# --------------------------------------------------------------------------------------------
# Flag, send, members and bot authorization (R6, N4, N5)
# --------------------------------------------------------------------------------------------


def test_n4_flag_off_or_send_unavailable_closes_all_three_before_any_call(
    tmp_path: Path,
) -> None:
    for mode in ("flag_off", "send_unavailable"):
        env = Env(tmp_path / mode)
        calls = _setup(env, flag=(mode != "flag_off"))
        if mode == "send_unavailable":
            env.ctx.send_available = lambda: False

        async def scenario(client: TestClient, env: Env = env, mode: str = mode) -> None:
            dev = await pair(env, client)
            env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
            for method, path, body in (
                ("GET", f"/bots/{BOT}/prompts", None),
                ("POST", f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}),
                ("POST", f"/bots/{BOT}/phone/messages", {"client_message_id": "c", "text": "hi"}),
            ):
                status, resp = (
                    await get(client, path, headers=env.headers(dev))
                    if method == "GET"
                    else await post(client, path, body, headers=env.headers(dev))
                )
                assert (status, code(resp)) == (503, "write_gate_closed"), (mode, path)

        run(env, scenario)
        assert calls["endpoint"] == [], mode
        _no_hermes_call(calls)


def test_n5_a_bot_the_device_is_not_authorized_for_is_refused_before_the_gate(
    tmp_path: Path,
) -> None:
    env = Env(tmp_path)
    calls = _setup(env)
    env.bridge.authz_state = lambda *_a, **_k: AuthzState.NOT_ROUTED  # type: ignore[method-assign]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        for method, path, body in (
            ("GET", f"/bots/{BOT}/prompts", None),
            ("POST", f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}),
            ("POST", f"/bots/{BOT}/phone/messages", {"client_message_id": "c", "text": "hi"}),
        ):
            status, resp = (
                await get(client, path, headers=env.headers(dev))
                if method == "GET"
                else await post(client, path, body, headers=env.headers(dev))
            )
            assert code(resp) != "write_gate_closed" and status != 200, path
            assert resp["error"]["authz"] == "not_routed", path

    run(env, scenario)
    assert calls["endpoint"] == []
    _no_hermes_call(calls)


def test_both_members_closed_closes_the_list_and_every_answer(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls = _setup(env, approvals=False, phone=False)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        _row(env, dev, surface="bot_chat")
        status, resp = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert (status, code(resp)) == (503, "write_gate_closed")
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (503, "write_gate_closed")

    run(env, scenario)
    assert calls["endpoint"] == []
    _no_hermes_call(calls)


def test_phone_chat_closed_leaves_bot_chat_cards_answerable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    calls = _setup(env, approvals=True, phone=False)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        _row(env, dev, surface="bot_chat")
        _row(env, dev, surface="phone_chat", kind="clarify", request_id="clar_1" + "0" * 20)
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert [p["surface"] for p in listed["prompts"]] == ["bot_chat"]  # no Phone row shown
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert status == 200 and resp["applied"] is True
        # The Phone clarify answer and a Phone send are closed with the member.
        status, resp = await post(
            client,
            f"/bots/{BOT}/prompts/clar_1{'0' * 20}",
            {"choice": "Ship"},
            headers=env.headers(dev),
        )
        assert (status, code(resp)) == (503, "write_gate_closed")
        status, resp = await post(
            client,
            f"/bots/{BOT}/phone/messages",
            {"client_message_id": "c", "text": "hi"},
            headers=env.headers(dev),
        )
        assert (status, code(resp)) == (503, "write_gate_closed")
        assert calls["clarify"] == []

    run(env, scenario)


def test_approvals_closed_leaves_phone_chat_answerable_and_bot_rows_closed(
    tmp_path: Path,
) -> None:
    env = Env(tmp_path)
    calls = _setup(env, approvals=False, phone=True)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        _row(env, dev, surface="bot_chat")
        _row(env, dev, surface="phone_chat", request_id="phone_" + "1" * 20)
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200 and [p["surface"] for p in listed["prompts"]] == ["phone_chat"]
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (503, "write_gate_closed")
        assert calls["native"] == []
        status, resp = await post(
            client,
            f"/bots/{BOT}/prompts/phone_{'1' * 20}",
            {"choice": "once"},
            headers=env.headers(dev),
        )
        assert status == 200 and resp["applied"] is True
        assert calls["resolve"] == [("sess-phone", "once", "phone_" + "1" * 20)]

    run(env, scenario)


# --------------------------------------------------------------------------------------------
# Ownership of the row (N6, N7)
# --------------------------------------------------------------------------------------------


def test_n6_the_same_device_cannot_answer_another_profiles_exact_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    calls = _setup(env)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        _row(env, dev, surface="bot_chat")  # the row belongs to profile "b"
        status, resp = await post(
            client, f"/bots/other/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (404, "not_found")
        status, listed = await get(client, "/bots/other/prompts", headers=env.headers(dev))
        assert status == 200 and listed["prompts"] == []

    run(env, scenario)
    assert calls["native"] == []


def test_n6_another_users_row_is_a_404_for_a_guessing_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    calls = _setup(env)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        env.ctx.prompt_store.put(
            PromptRow(
                iid=env.iid, user_id="hmpu_" + "ef" * 16, profile=BOT, request_id=REQ,
                kind="approval", surface="bot_chat", choices=("once",), run_id=RUN,
            )
        )
        status, resp = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(dev)
        )
        assert (status, code(resp)) == (404, "not_found")

    run(env, scenario)
    assert calls["native"] == []


def test_n7_an_unknown_or_guessed_id_allocates_no_row_and_no_lock(tmp_path: Path) -> None:
    env = Env(tmp_path)
    calls = _setup(env)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        for guess in ("guess-1", "x" * 256, "req_" + "0" * 32):
            status, resp = await post(
                client, f"/bots/{BOT}/prompts/{guess}", {"choice": "once"},
                headers=env.headers(dev),
            )
            assert (status, code(resp)) == (404, "not_found"), guess[:12]
        store = env.ctx.prompt_store
        assert not store._rows and not store._locks and not store._lock_users

    run(env, scenario)
    _no_hermes_call(calls)


# --------------------------------------------------------------------------------------------
# Snapshot `open_requests` follows the Phone member (R6)
# --------------------------------------------------------------------------------------------


def test_snapshot_open_requests_need_an_owner_the_flag_and_phone_chat() -> None:
    from types import SimpleNamespace

    from hmp_plugin import request_ctx

    ctx = request_ctx.ServerContext(identity=object(), store=object(), compat=object())  # type: ignore[arg-type]
    ctx.direct_send_flag = lambda: True
    ctx.phone_chat_available = lambda: True
    assert ctx.is_phone_chat_available() is True
    store = SimpleNamespace(closed=False, phone_closed=True)
    ctx.prompt_store = store
    assert ctx.is_phone_chat_available() is False  # the binding fence closed it
    store.phone_closed, store.closed = False, True
    assert ctx.is_phone_chat_available() is False  # the listener generation ended
    assert prompts.PromptStore().closed is False
