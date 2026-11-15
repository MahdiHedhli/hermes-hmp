"""NI-6 HMP seam regressions. All ownership results are synthetic fake-port values."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import prompts, server
from hmp_plugin.reads import Reads
from hmp_plugin.request_ctx import ServerContext

from .hmp_kit import Env, get, pair, post, run
from .test_approvals import REQ, RUN, USER, FakeResolver, _arm

BOT = "b"
CHAIN = ("synthetic-root", "synthetic-tip")


class ScriptedOwnershipPort:
    """A closed fake. It never reads native state or treats a registry-shaped value as evidence."""

    def __init__(self, state: prompts.DesktopOwnership, *, can_observe: object = True) -> None:
        self.state = state
        self.can_observe = can_observe
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def observe(
        self, *, profile: str, canonical_lineage: tuple[str, ...]
    ) -> prompts.DesktopOwnership:
        self.calls.append((profile, canonical_lineage))
        return self.state


class RaisingOwnershipPort:
    can_observe = True

    async def observe(
        self, *, profile: str, canonical_lineage: tuple[str, ...]
    ) -> prompts.DesktopOwnership:
        raise RuntimeError("synthetic observer failure")


class RaisingCanObservePort:
    @property
    def can_observe(self) -> bool:
        raise RuntimeError("synthetic eligibility failure")

    async def observe(
        self, *, profile: str, canonical_lineage: tuple[str, ...]
    ) -> prompts.DesktopOwnership:
        raise AssertionError("observe must not follow failed eligibility")


class RaisingLineageTarget:
    @property
    def compression_chain(self) -> tuple[str, ...]:
        raise RuntimeError("synthetic target projection failure")


def _counted_target(calls: list[str]):
    def resolve(profile: str) -> Any:
        calls.append(profile)
        return SimpleNamespace(compression_chain=CHAIN)

    return resolve


def _row(env: Env, user_id: str, *, surface: str, request_id: str, kind: str = "approval"):
    return prompts.PromptRow(
        iid=env.iid,
        user_id=user_id,
        profile=BOT,
        request_id=request_id,
        kind=kind,
        surface=surface,
        choices=("once", "deny") if kind == "approval" else ("Ship", "Wait"),
        question="Continue?" if kind == "clarify" else None,
        run_id=RUN if surface == "bot_chat" else None,
        session_key="synthetic-phone-session" if surface == "phone_chat" else None,
        observed_at=env.clock.now,
        expires_at=env.clock.now + 300,
    )


def _user_id(env: Env, dev: Any) -> str:
    row = (
        env.store._require_conn()
        .execute("SELECT user_id FROM devices WHERE device_id = ?", (dev.device_id,))
        .fetchone()
    )
    return str(row["user_id"])


def _target(
    env: Env,
    store: prompts.PromptStore,
    user_id: str,
    request_id: str,
    *,
    require_lock: bool = False,
) -> None:
    def resolve(_profile: str) -> Any:
        if require_lock:
            key = (env.iid, user_id, BOT, request_id)
            lock = store._locks.get(key)
            assert lock is not None and lock.locked()
        return SimpleNamespace(compression_chain=CHAIN)

    env.bridge.resolve_bot_chat = resolve  # type: ignore[method-assign]


@pytest.mark.parametrize(
    ("state", "shown_bot", "held"),
    [
        (prompts.DesktopOwnership.OWNED, False, True),
        (prompts.DesktopOwnership.UNOWNED, True, False),
        (prompts.DesktopOwnership.UNKNOWN, False, False),
    ],
)
def test_ap3_reports_state_and_preserves_phone_rows(
    tmp_path: Path,
    state: prompts.DesktopOwnership,
    shown_bot: bool,
    held: bool,
) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    port = ScriptedOwnershipPort(state)
    env.ctx.desktop_ownership = port  # type: ignore[assignment]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        store.put(_row(env, user_id, surface="bot_chat", request_id=REQ))
        # Phone clarify avoids the independent Phone approval listing/reconciliation path.
        store.put(
            _row(env, user_id, surface="phone_chat", request_id="phone-clarify", kind="clarify")
        )
        _target(env, store, user_id, REQ)
        status, body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert body["desktop_ownership"] == state.value
        assert body["desktop_held"] is held
        surfaces = {item["surface"] for item in body["prompts"]}
        assert ("bot_chat" in surfaces) is shown_bot
        assert "phone_chat" in surfaces

    run(env, scenario)
    assert port.calls == [(BOT, CHAIN)]


@pytest.mark.parametrize(
    "failure",
    ["string", "none", "object", "observer_exception", "eligibility_exception", "target_getter"],
)
def test_ap3_invalid_or_failed_observation_is_unknown_and_keeps_phone(
    tmp_path: Path, failure: str
) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    if failure == "observer_exception":
        port: Any = RaisingOwnershipPort()
    elif failure == "eligibility_exception":
        port = RaisingCanObservePort()
    else:
        result: Any = {
            "string": "unowned",
            "none": None,
            "object": object(),
            "target_getter": prompts.DesktopOwnership.UNOWNED,
        }[failure]
        port = ScriptedOwnershipPort(result)
    env.ctx.desktop_ownership = port

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        store.put(_row(env, user_id, surface="bot_chat", request_id=REQ))
        store.put(
            _row(env, user_id, surface="phone_chat", request_id="phone-clarify", kind="clarify")
        )
        target_calls: list[str] = []
        if failure == "target_getter":
            env.bridge.resolve_bot_chat = lambda profile: (
                target_calls.append(profile) or RaisingLineageTarget()
            )  # type: ignore[method-assign]
        else:
            env.bridge.resolve_bot_chat = _counted_target(
                target_calls
            )  # type: ignore[method-assign]

        status, body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert body["desktop_ownership"] == "unknown"
        assert body["desktop_held"] is False
        assert [item["request_id"] for item in body["prompts"]] == ["phone-clarify"]
        assert target_calls == ([] if failure == "eligibility_exception" else [BOT])

    run(env, scenario)
    if isinstance(port, ScriptedOwnershipPort):
        assert port.calls == ([] if failure == "target_getter" else [(BOT, CHAIN)])


def test_ap3_unavailable_and_nonliteral_true_skip_observation_only_lookup(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    port = ScriptedOwnershipPort(prompts.DesktopOwnership.UNOWNED, can_observe=1)
    env.ctx.desktop_ownership = port  # type: ignore[assignment]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        store.put(_row(env, user_id, surface="bot_chat", request_id=REQ))
        store.put(
            _row(env, user_id, surface="phone_chat", request_id="phone-clarify", kind="clarify")
        )

        target_calls: list[str] = []
        env.bridge.resolve_bot_chat = _counted_target(target_calls)  # type: ignore[method-assign]
        status, body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert body["desktop_ownership"] == "unknown"
        assert body["desktop_held"] is False
        assert [item["request_id"] for item in body["prompts"]] == ["phone-clarify"]
        assert target_calls == []

    run(env, scenario)
    assert port.calls == []


def test_ap3_phone_only_snapshot_does_not_probe_desktop_ownership(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    port = ScriptedOwnershipPort(prompts.DesktopOwnership.UNOWNED)
    env.ctx.desktop_ownership = port  # type: ignore[assignment]

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        store.put(
            _row(env, user_id, surface="phone_chat", request_id="phone-clarify", kind="clarify")
        )

        target_calls: list[str] = []
        env.bridge.resolve_bot_chat = _counted_target(target_calls)  # type: ignore[method-assign]
        status, body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert body["desktop_ownership"] == "unknown"
        assert body["desktop_held"] is False
        assert [item["request_id"] for item in body["prompts"]] == ["phone-clarify"]
        assert target_calls == []

    run(env, scenario)
    assert port.calls == []


@pytest.mark.asyncio
async def test_default_unavailable_port_short_circuits_before_target_resolution() -> None:
    target_calls: list[str] = []

    ctx = ServerContext(
        identity=object(),
        store=object(),
        compat=object(),
        bridge=SimpleNamespace(
            resolve_bot_chat=_counted_target(target_calls)
        ),  # type: ignore[arg-type]
    )
    assert ctx.desktop_ownership.can_observe is False
    assert (
        await server._observe_desktop_ownership(ctx, BOT)
        is prompts.DesktopOwnership.UNKNOWN
    )
    assert target_calls == []


def test_ap3_missing_store_is_empty_unknown_without_target_lookup(tmp_path: Path) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    env.ctx.prompt_store = None

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})

        target_calls: list[str] = []
        env.bridge.resolve_bot_chat = _counted_target(target_calls)  # type: ignore[method-assign]
        status, body = await get(client, f"/bots/{BOT}/prompts", headers=env.headers(dev))
        assert status == 200
        assert body == {
            "prompts": [],
            "desktop_held": False,
            "desktop_ownership": "unknown",
        }
        assert target_calls == []

    run(env, scenario)


@pytest.mark.parametrize(
    ("state", "can_observe", "expected_status", "should_resolve"),
    [
        (prompts.DesktopOwnership.OWNED, True, 503, False),
        (prompts.DesktopOwnership.UNKNOWN, True, 503, False),
        (prompts.DesktopOwnership.UNOWNED, True, 200, True),
        (prompts.DesktopOwnership.UNOWNED, False, 503, False),
    ],
)
def test_ap4_checks_open_bot_row_under_lock_before_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: prompts.DesktopOwnership,
    can_observe: bool,
    expected_status: int,
    should_resolve: bool,
) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    port = ScriptedOwnershipPort(state, can_observe=can_observe)
    env.ctx.desktop_ownership = port  # type: ignore[assignment]
    resolver_calls: list[tuple[str, str, str]] = []

    async def native_answer(_endpoint: Any, run_id: str, request_id: str, choice: str) -> str:
        resolver_calls.append((run_id, request_id, choice))
        return "accepted"

    from hmp_plugin import direct_send

    monkeypatch.setattr(direct_send, "aiohttp_approval_call", native_answer)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        row = _row(env, user_id, surface="bot_chat", request_id=REQ)
        store.put(row)
        target_calls: list[str] = []
        if can_observe:
            _target(env, store, user_id, REQ, require_lock=True)
        else:
            env.bridge.resolve_bot_chat = _counted_target(
                target_calls
            )  # type: ignore[method-assign]
        before = (
            row.status,
            row.settled_at,
            row.settle_cause,
            row.answer_hash,
            row.expires_at,
            row.stored_status,
            None if row.stored_body is None else dict(row.stored_body),
            row.awaiting_text,
        )
        status, body = await post(
            client,
            f"/bots/{BOT}/prompts/{REQ}",
            {"choice": "once"},
            headers=env.headers(dev),
        )
        assert status == expected_status
        if not can_observe:
            assert target_calls == []
        assert port.calls == ([(BOT, CHAIN)] if can_observe else [])
        assert resolver_calls == ([(RUN, REQ, "once")] if should_resolve else [])
        if not should_resolve:
            after = (
                row.status,
                row.settled_at,
                row.settle_cause,
                row.answer_hash,
                row.expires_at,
                row.stored_status,
                None if row.stored_body is None else dict(row.stored_body),
                row.awaiting_text,
            )
            assert after == before
            assert body["error"]["code"] == "api_server_unavailable"
            assert "applied" not in body
        else:
            assert body["status"] == "resolved"
            assert row.status == "resolved"

    run(env, scenario)


@pytest.mark.parametrize(
    "failure",
    ["string", "none", "object", "observer_exception", "eligibility_exception", "target_getter"],
)
def test_ap4_invalid_or_failed_observation_does_not_resolve_or_mutate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    env = Env(tmp_path)
    _arm(env, flag=True)
    if failure == "observer_exception":
        port: Any = RaisingOwnershipPort()
    elif failure == "eligibility_exception":
        port = RaisingCanObservePort()
    else:
        result: Any = {
            "string": "unowned",
            "none": None,
            "object": object(),
            "target_getter": prompts.DesktopOwnership.UNOWNED,
        }[failure]
        port = ScriptedOwnershipPort(result)
    env.ctx.desktop_ownership = port
    resolver_calls: list[tuple[str, str, str]] = []
    target_calls: list[str] = []

    async def native_answer(_endpoint: Any, run_id: str, request_id: str, choice: str) -> str:
        resolver_calls.append((run_id, request_id, choice))
        return "accepted"

    from hmp_plugin import direct_send

    monkeypatch.setattr(direct_send, "aiohttp_approval_call", native_answer)

    async def scenario(client: TestClient) -> None:
        dev = await pair(env, client)
        user_id = _user_id(env, dev)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        store = env.ctx.prompt_store
        assert store is not None
        row = _row(env, user_id, surface="bot_chat", request_id=REQ)
        store.put(row)
        if failure == "target_getter":
            env.bridge.resolve_bot_chat = lambda profile: (
                target_calls.append(profile) or RaisingLineageTarget()
            )  # type: ignore[method-assign]
        else:
            env.bridge.resolve_bot_chat = _counted_target(
                target_calls
            )  # type: ignore[method-assign]
        before = (
            row.status,
            row.settled_at,
            row.settle_cause,
            row.answer_hash,
            row.expires_at,
            row.stored_status,
            None if row.stored_body is None else dict(row.stored_body),
            row.awaiting_text,
        )
        status, body = await post(
            client,
            f"/bots/{BOT}/prompts/{REQ}",
            {"choice": "once"},
            headers=env.headers(dev),
        )
        after = (
            row.status,
            row.settled_at,
            row.settle_cause,
            row.answer_hash,
            row.expires_at,
            row.stored_status,
            None if row.stored_body is None else dict(row.stored_body),
            row.awaiting_text,
        )
        assert status == 503
        assert body["error"]["code"] == "api_server_unavailable"
        assert "applied" not in body
        assert after == before
        assert resolver_calls == []
        assert target_calls == ([] if failure == "eligibility_exception" else [BOT])
        if isinstance(port, ScriptedOwnershipPort):
            assert port.calls == ([] if failure == "target_getter" else [(BOT, CHAIN)])

    run(env, scenario)


@pytest.mark.asyncio
async def test_settled_replay_skips_desktop_observer() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    row = prompts.PromptRow(
        iid="iid_test",
        user_id=USER,
        profile=BOT,
        request_id=REQ,
        kind="approval",
        surface="bot_chat",
        choices=("once", "deny"),
        run_id=RUN,
        observed_at=1,
    )
    store.put(row)
    calls: list[bool] = []

    async def unowned(_row: prompts.PromptRow) -> prompts.DesktopOwnership:
        calls.append(True)
        return prompts.DesktopOwnership.UNOWNED

    resolver = FakeResolver()
    first = await prompts.answer_prompt(
        store,
        iid=row.iid,
        user_id=USER,
        profile=BOT,
        request_id=REQ,
        body={"choice": "once"},
        resolver=resolver,
        now=2,
        ownership_check=unowned,
    )
    replay = await prompts.answer_prompt(
        store,
        iid=row.iid,
        user_id=USER,
        profile=BOT,
        request_id=REQ,
        body={"choice": "once"},
        resolver=resolver,
        now=3,
        ownership_check=unowned,
    )
    assert first.status == replay.status == 200
    assert first.body == replay.body
    assert calls == [True]
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
async def test_phone_answer_skips_desktop_observer() -> None:
    store = prompts.PromptStore(clock=lambda: 1)
    row = prompts.PromptRow(
        iid="iid_test",
        user_id=USER,
        profile=BOT,
        request_id="phone-clarify",
        kind="clarify",
        surface="phone_chat",
        choices=("Ship", "Wait"),
        question="Continue?",
        observed_at=1,
    )
    store.put(row)
    calls: list[bool] = []

    async def forbidden(_row: prompts.PromptRow) -> prompts.DesktopOwnership:
        calls.append(True)
        return prompts.DesktopOwnership.UNKNOWN

    resolver = FakeResolver()
    result = await prompts.answer_prompt(
        store,
        iid=row.iid,
        user_id=USER,
        profile=BOT,
        request_id=row.request_id,
        body={"choice": "Ship"},
        resolver=resolver,
        now=2,
        ownership_check=forbidden,
    )
    assert result.status == 200
    assert calls == []
    assert resolver.calls == [("clarify", row.request_id, "Ship")]


def test_ro3_phone_projection_remains_independent() -> None:
    store = prompts.PromptStore(clock=lambda: 10)
    store.put(
        prompts.PromptRow(
            iid="iid_test",
            user_id=USER,
            profile=BOT,
            request_id="phone-clarify",
            kind="clarify",
            surface="phone_chat",
            choices=("yes", "no"),
            question="Continue?",
            observed_at=1,
        )
    )
    store.put(
        prompts.PromptRow(
            iid="iid_test",
            user_id=USER,
            profile=BOT,
            request_id="bot-approval",
            kind="approval",
            surface="bot_chat",
            choices=("once", "deny"),
            observed_at=1,
        )
    )
    reads = SimpleNamespace(
        _prompt_store=store,
        _clock=lambda: 10,
        _iid="iid_test",
    )
    rows = Reads._phone_open_requests(reads, USER, BOT)  # type: ignore[arg-type]
    assert [row["clarify_id"] for row in rows] == ["phone-clarify"]
