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
