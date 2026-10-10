"""R11 / D2b / AP-1: which loopback route a guarded send uses, and that it never falls back.

Only a send from an effective approval-owner device with `approvals` available opens the session
stream. Every other send keeps the synchronous route exactly as before. The choice is made before
the profile lock and never re-made after a failure (N26, N27, H6).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import aiohttp
import pytest

from hmp_plugin import direct_send as ds
from hmp_plugin import server
from hmp_plugin.contract import DirectSendRequest, ErrorCode, WriteGate, WriteGateState
from hmp_plugin.prompts import PromptStore
from hmp_plugin.store import Store

from .hmp_kit import Env
from .test_approvals import USER, _arm
from .test_direct_send import CLOSED, FakeBridge, clean_bridge, make_deps, make_target

REQUEST = DirectSendRequest(client_message_id="c1", expected_head=5, text="hi")


class Calls:
    """Records which transport ran, and what stream binding was visible inside it."""

    def __init__(self) -> None:
        self.sync: list[str] = []
        self.stream: list[str] = []
        self.bound_in_stream: list[object] = []
        self.bound_in_sync: list[object] = []

    async def sync_call(self, endpoint: Any, session_id: str, text: str) -> ds.LoopbackResult:
        self.sync.append(session_id)
        self.bound_in_sync.append(ds._STREAM_BIND.get())
        return ds.LoopbackResult(
            status=200,
            body={"message": {"id": 42, "role": "assistant", "content": "hi"}},
            effective_session_id=session_id,
        )

    async def stream_call(self, endpoint: Any, session_id: str, text: str) -> ds.LoopbackResult:
        self.stream.append(session_id)
        self.bound_in_stream.append(ds._STREAM_BIND.get())
        return ds.LoopbackResult(
            status=200,
            body={"message": {"id": 42, "role": "assistant", "content": "hi"}},
            effective_session_id=session_id,
        )


def _deps(store: Store, calls: Calls, *, prompts: bool = True) -> ds.DirectSendDeps:
    deps = make_deps(store, clean_bridge(), loopback=calls.sync_call)
    return dataclasses.replace(
        deps,
        stream_call=calls.stream_call,
        prompt_store=PromptStore(clock=lambda: 1000) if prompts else None,
    )


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "hmp.sqlite3")
    s.migrate()
    return s


async def _send(deps: ds.DirectSendDeps, *, stream: bool | None, cmid: str = "c1") -> Any:
    kwargs: dict[str, Any] = {} if stream is None else {"stream": stream}
    return await ds.handle_direct_send(
        deps,
        iid="i1",
        user_id=USER,
        profile="default",
        request=DirectSendRequest(client_message_id=cmid, expected_head=5, text="hi"),
        flag_enabled=True,
        base_write_gate=CLOSED,
        **kwargs,
    )


# --------------------------------------------------------------------------------------------
# The default is the synchronous route, unchanged
# --------------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [None, False])
async def test_n26_a_send_without_the_stream_flag_uses_the_sync_call_only(
    store: Store, stream: bool | None
) -> None:
    calls = Calls()
    outcome = await _send(_deps(store, calls), stream=stream)
    assert outcome.state == "accepted"
    assert calls.sync == ["tip1"] and calls.stream == []
    assert calls.bound_in_sync == [None]  # no approval binding exists on the sync route


def test_the_default_deps_stream_call_is_the_stream_route_and_the_default_call_is_sync() -> None:
    import inspect

    fields = ds.DirectSendDeps.__dataclass_fields__
    assert fields["loopback_call"].default is ds.aiohttp_loopback_call
    assert fields["stream_call"].default is ds.aiohttp_stream_call
    assert "chat/stream" in inspect.getsource(ds.aiohttp_stream_call)
    sync_source = inspect.getsource(ds.aiohttp_loopback_call)
    assert "/chat/stream" not in sync_source and '/chat"' in sync_source


@pytest.mark.asyncio
async def test_a_stream_send_uses_the_stream_call_with_the_binding_and_never_the_sync_call(
    store: Store,
) -> None:
    calls = Calls()
    outcome = await _send(_deps(store, calls), stream=True)
    assert outcome.state == "accepted"
    assert calls.stream == ["tip1"] and calls.sync == []
    bind = calls.bound_in_stream[0]
    assert isinstance(bind, ds.StreamBind) and bind.user_id == USER and bind.profile == "default"
    assert ds._STREAM_BIND.get() is None  # reset after the call


@pytest.mark.asyncio
async def test_a_stream_send_without_a_prompt_store_streams_but_binds_nothing(
    store: Store,
) -> None:
    calls = Calls()
    await _send(_deps(store, calls, prompts=False), stream=True)
    assert calls.stream == ["tip1"] and calls.bound_in_stream == [None]


# --------------------------------------------------------------------------------------------
# No fallback after a stream failure (AP-1)
# --------------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        aiohttp.ClientPayloadError("sse ended before a terminal event"),
        aiohttp.ClientConnectionError("refused"),
        TimeoutError(),
    ],
)
async def test_a_stream_failure_never_falls_back_to_the_sync_route(
    store: Store, failure: Exception
) -> None:
    calls = Calls()

    async def failing(endpoint: Any, session_id: str, text: str) -> ds.LoopbackResult:
        calls.stream.append(session_id)
        raise failure

    deps = dataclasses.replace(_deps(store, calls), stream_call=failing)
    with pytest.raises(ds.DirectSendError) as caught:
        await _send(deps, stream=True)
    assert caught.value.failure.code is ErrorCode.API_SERVER_UNAVAILABLE
    assert calls.stream == ["tip1"] and calls.sync == []  # the sync route was never opened
    # The attempt is stored `unknown` and replayed as such: not re-sent, not sent another way.
    replay = await _send(deps, stream=True)
    assert replay.state == "unknown"
    assert calls.sync == [] and len(calls.stream) == 1


@pytest.mark.asyncio
async def test_a_non_200_stream_result_is_a_refusal_without_a_sync_attempt(store: Store) -> None:
    calls = Calls()

    async def not_found(endpoint: Any, session_id: str, text: str) -> ds.LoopbackResult:
        calls.stream.append(session_id)
        return ds.LoopbackResult(status=404, body=None, effective_session_id=None)

    deps = dataclasses.replace(_deps(store, calls), stream_call=not_found)
    with pytest.raises(ds.DirectSendError):
        await _send(deps, stream=True)
    assert calls.sync == [] and calls.stream == ["tip1"]


@pytest.mark.asyncio
async def test_a_failing_sync_send_is_unchanged_by_the_presence_of_a_stream_call(
    store: Store,
) -> None:
    calls = Calls()

    async def failing_sync(endpoint: Any, session_id: str, text: str) -> ds.LoopbackResult:
        calls.sync.append(session_id)
        raise aiohttp.ClientConnectionError("refused")

    deps = dataclasses.replace(_deps(store, calls), loopback_call=failing_sync)
    with pytest.raises(ds.DirectSendError) as caught:
        await _send(deps, stream=False)
    assert caught.value.failure.code is ErrorCode.API_SERVER_UNAVAILABLE
    assert calls.stream == []  # a sync failure is never retried on the stream route


# --------------------------------------------------------------------------------------------
# The decision at the route, from live state (D2b)
# --------------------------------------------------------------------------------------------


def _route_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = Env(tmp_path)
    _arm(env, flag=True)
    env.ctx.write_gate = lambda: WriteGate(WriteGateState.CLOSED, "guarantees_unavailable")  # type: ignore[method-assign]
    calls = Calls()
    deps = _deps(env.store, calls)
    who = SimpleNamespace(device_id="dev-owner", user_id=USER)
    monkeypatch.setattr(server, "bearer", lambda request: who)
    monkeypatch.setattr(server, "context", lambda request: env.ctx)

    async def body(request: Any) -> dict[str, Any]:
        return {"client_message_id": "c-route", "expected_head": 5, "text": "hi"}

    monkeypatch.setattr(server, "read_json_body", body)
    monkeypatch.setattr(server, "require_bot_authorized", lambda *a: None)
    env.bridge.resolve_bot_chat = lambda profile: make_target()  # type: ignore[method-assign]
    env.bridge.lease_snapshot = lambda profile: []  # type: ignore[method-assign]
    env.bridge.after = clean_bridge().after  # type: ignore[method-assign]
    env.bridge.direct_send_endpoint = FakeBridge(bot_chat=None).direct_send_endpoint  # type: ignore[method-assign]
    env.ctx.direct_send_deps = dataclasses.replace(deps, bridge=env.bridge)  # type: ignore[arg-type]
    return env, who, calls


async def _post_chat(env: Env) -> Any:
    from aiohttp.test_utils import make_mocked_request

    request = make_mocked_request("POST", "/", match_info={"p": "b"})
    return await server.handle_chat_send(request)


@pytest.mark.asyncio
async def test_n26_h6_only_an_approval_owner_with_approvals_available_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, _who, calls = _route_env(tmp_path / "owner", monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({"dev-owner"})
    await _post_chat(env)
    assert calls.stream == ["tip1"] and calls.sync == []
    env.store.close()

    # The same user on a device that is not an approval owner: synchronous, unchanged.
    env, _who, calls = _route_env(tmp_path / "non-owner", monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({"someone-else"})
    await _post_chat(env)
    assert calls.sync == ["tip1"] and calls.stream == []
    env.store.close()


@pytest.mark.asyncio
async def test_a_host_denied_owner_and_a_closed_approvals_member_both_send_synchronously(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, who, calls = _route_env(tmp_path / "denied", monkeypatch)
    env.store.insert_user(USER, "label", 1000)
    env.store.insert_device(who.device_id, USER, "f" * 64, b"x", "phone", 1000, state="ACTIVE")
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})
    assert env.store.set_owner_controls(who.device_id, allowed=False, now=1001)
    await _post_chat(env)
    assert calls.sync == ["tip1"] and calls.stream == []
    env.store.close()

    env, who, calls = _route_env(tmp_path / "closed", monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({"dev-owner"})
    env.ctx.approvals_available = lambda: False
    await _post_chat(env)
    assert calls.sync == ["tip1"] and calls.stream == []
    env.store.close()


@pytest.mark.asyncio
async def test_a_controls_grant_alone_does_not_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, who, calls = _route_env(tmp_path, monkeypatch)
    env.store.insert_user(USER, "label", 1000)
    env.store.insert_device(who.device_id, USER, "f" * 64, b"x", "phone", 1000, state="ACTIVE")
    env.ctx.owner_device_ids = lambda: frozenset()
    assert env.store.set_owner_controls(who.device_id, allowed=True, now=1001)
    await _post_chat(env)
    assert calls.sync == ["tip1"] and calls.stream == []
    env.store.close()


@pytest.mark.asyncio
async def test_removing_the_owner_between_two_sends_changes_the_next_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, _who, calls = _route_env(tmp_path, monkeypatch)
    owners = {"dev-owner"}
    env.ctx.owner_device_ids = lambda: frozenset(owners)

    ids = iter(["c-a", "c-b"])

    async def body(request: Any) -> dict[str, Any]:
        return {"client_message_id": next(ids), "expected_head": 5, "text": "hi"}

    monkeypatch.setattr(server, "read_json_body", body)
    await _post_chat(env)
    owners.clear()
    await _post_chat(env)
    assert calls.stream == ["tip1"] and calls.sync == ["tip1"]  # live state, not cached
    env.store.close()
