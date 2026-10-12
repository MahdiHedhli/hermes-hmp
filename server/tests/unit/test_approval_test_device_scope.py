"""Target-device isolation; resolver is deliberately observable."""
from __future__ import annotations

import pytest

from hmp_plugin import prompts

from .test_approvals import IID, PROFILE, REQ, USER, FakeResolver, _store_approval


@pytest.mark.asyncio
async def test_target_device_scope_precedes_answer_and_replay() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    resolver = FakeResolver()
    _store_approval(store, target_device_id="synthetic-target-device", choices=("once", "deny"))
    for device in (None, "synthetic-other-device"):
        assert not store.list_visible(IID, USER, PROFILE, device_id=device)
        result = await prompts.answer_prompt(
            store, iid=IID, user_id=USER, profile=PROFILE, request_id=REQ,
            body={"choice": "once", "device_id": "synthetic-target-device"},
            resolver=resolver, now=2, device_id=device,
        )
        assert result.status == 404
        assert not resolver.calls
    listed = prompts.list_prompts(
        store, iid=IID, user_id=USER, profile=PROFILE, now=2,
        device_id="synthetic-target-device",
    )
    assert len(listed.body["prompts"]) == 1
    assert "target_device_id" not in listed.body["prompts"][0]
    async def answer(device: str) -> prompts.HttpResult:
        return await prompts.answer_prompt(
            store, iid=IID, user_id=USER, profile=PROFILE, request_id=REQ,
            body={"choice": "once"}, resolver=resolver, now=2, device_id=device,
        )
    accepted = await answer("synthetic-target-device")
    assert accepted.status == 200
    assert len(resolver.calls) == 1
    assert (await answer("synthetic-other-device")).status == 404
    assert (await answer("synthetic-target-device")).body == accepted.body
    assert len(resolver.calls) == 1


def test_ordinary_rows_remain_visible_without_target_scope() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    _store_approval(store)
    for device in (None, "synthetic-target-device", "synthetic-other-device"):
        assert len(store.list_visible(IID, USER, PROFILE, device_id=device)) == 1


def test_authenticated_http_target_scope(tmp_path, monkeypatch) -> None:
    from .hmp_kit import Env, code, get, pair, post, run
    from .test_approval_route_gates import BOT, _native, _row, _setup

    env = Env(tmp_path)
    calls = _setup(env)
    _native(monkeypatch, calls, "accepted")

    async def scenario(client) -> None:
        target = await pair(env, client)
        other = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({target.device_id, other.device_id})
        row = _row(env, target, surface="bot_chat", target_device_id=target.device_id)
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(other))
        assert status == 200 and listed["prompts"] == []
        status, rejected = await post(
            client, f"/bots/{BOT}/prompts/{REQ}",
            {"choice": "once", "device_id": target.device_id}, headers=env.headers(other),
        )
        assert (status, code(rejected)) == (404, "not_found")
        assert row.status == "open" and calls["native"] == []
        status, listed = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(target))
        assert status == 200 and len(listed["prompts"]) == 1
        status, accepted = await post(
            client, f"/bots/{BOT}/prompts/{REQ}", {"choice": "once"}, headers=env.headers(target),
        )
        assert status == 200 and accepted["status"] == "resolved"
        assert len(calls["native"]) == 1

    run(env, scenario)


@pytest.mark.asyncio
async def test_scoped_test_rejects_persistent_choice_and_expired_answer() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    resolver = FakeResolver()
    _store_approval(
        store, target_device_id="synthetic-target-device", choices=("once", "deny"),
        expires_at=10,
    )
    async def answer(choice: str, now: int) -> prompts.HttpResult:
        return await prompts.answer_prompt(
            store, iid=IID, user_id=USER, profile=PROFILE, request_id=REQ,
            body={"choice": choice}, resolver=resolver, now=now,
            device_id="synthetic-target-device",
        )
    assert (await answer("always", 2)).status == 409
    assert (await answer("session", 2)).status == 409
    assert not resolver.calls
    assert (await answer("once", 10)).status == 409
    assert not resolver.calls
    assert not store.list_visible(IID, USER, PROFILE, now=10, device_id="synthetic-target-device")


def test_ordinary_approval_expiry_grace_is_preserved() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    _store_approval(store, expires_at=10)
    assert len(store.list_visible(IID, USER, PROFILE, now=40)) == 1
    assert not store.list_visible(IID, USER, PROFILE, now=41)
