"""Approval route qualification is independent of guarded-send qualification (draft lane).

A passing guarded-send build, a valid owner device, the flag and an OPEN write gate must not be
enough to list, answer or deliver prompts: the separate approval qualification must say yes too.
Fakes only; no Hermes import, no network.
"""

from __future__ import annotations

import dataclasses
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp import web

from hmp_plugin import compat, direct_send, prompts, request_ctx, server
from hmp_plugin.contract import (
    DirectSendRequest,
    ErrorCode,
    HmpError,
    WriteGate,
    WriteGateState,
)
from hmp_plugin.direct_send import DirectSendDeps, ProfileLocks
from hmp_plugin.store import Store

from .hmp_kit import Env
from .test_adapter import adapter_module  # noqa: F401  (fixture)
from .test_approval_security import _request_env
from .test_approvals import IID, PROFILE, REQ, USER, PromptStore

HANDLERS = (server.handle_prompts_list, server.handle_prompt_answer, server.handle_phone_send)


def _raises() -> bool:
    raise RuntimeError("qualification exploded")


CLOSED_RESULTS = [
    pytest.param(lambda: False, id="false"),
    pytest.param(_raises, id="exception"),
    pytest.param(lambda: 1, id="truthy-int"),
    pytest.param(lambda: "yes", id="truthy-str"),
    pytest.param(lambda: [True], id="truthy-list"),
    pytest.param(lambda: None, id="none"),
]


def _owner_env(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, qualifier: Any, *, flag: bool = True
) -> tuple[Env, Any, Any, list[str]]:
    """Owner device, flag, guarded-send qualified, OPEN write gate; only approvals vary."""
    env, who, request = _request_env(tmp_path, monkeypatch, flag=flag)
    owner_device_id = who.device_id  # immutable capture: later edits to `who` cannot add owners
    env.ctx.owner_device_ids = lambda: frozenset({owner_device_id})
    env.ctx.write_gate = lambda: WriteGate(WriteGateState.OPEN, None)
    # DirectSendDeps is frozen: install a test-only copy with guarded send qualified.
    env.ctx.direct_send_deps = dataclasses.replace(env.ctx.direct_send_deps, qualified=lambda: True)
    env.ctx.approval_qualified = qualifier
    seen: list[str] = []
    real_endpoint = env.bridge.direct_send_endpoint

    def endpoint(*args: Any, **kwargs: Any) -> Any:
        seen.append("endpoint")
        return real_endpoint(*args, **kwargs)

    env.bridge.direct_send_endpoint = endpoint  # type: ignore[method-assign]

    async def body(_request: Any) -> dict[str, Any]:
        return {"client_message_id": "c", "text": "hi", "choice": "once"}

    monkeypatch.setattr(server, "read_json_body", body)

    def boom(name: str) -> Any:
        def fail(*_a: Any, **_k: Any) -> Any:
            seen.append(name)
            raise AssertionError(f"{name} must not run while approvals are unqualified")

        return fail

    async def aboom(*_a: Any, **_k: Any) -> Any:
        seen.append("prompts")
        raise AssertionError("prompt work must not run while approvals are unqualified")

    monkeypatch.setattr(prompts, "list_prompts", boom("list_prompts"))
    monkeypatch.setattr(prompts, "answer_prompt", aboom)
    monkeypatch.setattr(prompts, "handle_phone_send", aboom)
    return env, who, request, seen


def _no_approval_bridge_calls(env: Env) -> None:
    approval_calls = {
        "list_gateway_approvals",
        "resolve_gateway_approval",
        "deliver_phone_message",
        "phone_session_key",
        "resolve_gateway_clarify",
        "mark_clarify_awaiting_text",
        "approval_timeout_s",
    }
    assert not approval_calls & set(env.bridge.calls)


def test_default_server_context_is_closed() -> None:
    ctx = request_ctx.ServerContext(identity=None, store=None, compat=None)  # type: ignore[arg-type]
    assert ctx.approval_qualified() is False
    assert ctx.approval_qualification_open() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("qualifier", CLOSED_RESULTS)
async def test_closed_independent_approval_gate_blocks_ap3_ap4_ap6(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, qualifier: Any
) -> None:
    env, _who, request, seen = _owner_env(tmp_path, monkeypatch, qualifier)
    for handler in HANDLERS:
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "write_gate_closed"
    assert seen == []  # no endpoint resolution, listing, resolver or delivery
    _no_approval_bridge_calls(env)
    env.store.close()


@pytest.mark.asyncio
async def test_explicitly_qualified_keeps_f3_behavior(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, who, request = _request_env(tmp_path, monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})
    env.ctx.write_gate = lambda: WriteGate(WriteGateState.OPEN, None)
    env.ctx.direct_send_deps = dataclasses.replace(env.ctx.direct_send_deps, qualified=lambda: True)
    assert env.ctx.approval_qualified() is True  # the fixture's explicit test-only premise
    calls: list[str] = []

    bodies: dict[str, dict[str, Any]] = {
        "answer": {"choice": "once"},  # AP-4 takes exactly one answer form
        "phone": {"client_message_id": "c", "text": "hi"},  # AP-6 takes text, not a choice
    }
    which = ["answer"]

    async def body(_request: Any) -> dict[str, Any]:
        return bodies[which[0]]

    async def phone(**_kwargs: Any) -> prompts.HttpResult:
        calls.append("phone")
        return prompts.HttpResult(202, {"state": "submitted"})

    monkeypatch.setattr(server, "read_json_body", body)
    monkeypatch.setattr(prompts, "handle_phone_send", phone)
    assert (await server.handle_prompts_list(request)).status == 200
    assert (await server.handle_prompt_answer(request)).status == 404  # unknown ID, gate passed
    which[0] = "phone"
    assert (await server.handle_phone_send(request)).status == 202
    assert calls == ["phone"]
    env.store.close()


@pytest.mark.asyncio
async def test_approval_qualification_is_evaluated_off_the_event_loop(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop_thread = threading.get_ident()
    where: list[int] = []

    def qualifier() -> bool:
        where.append(threading.get_ident())
        return False

    env, _who, request, _seen = _owner_env(tmp_path, monkeypatch, qualifier)
    with pytest.raises(HmpError):
        await server.handle_prompts_list(request)
    assert where and all(ident != loop_thread for ident in where)
    env.store.close()


@pytest.mark.asyncio
async def test_approval_gate_does_not_reuse_a_cached_send_pass(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hmp_plugin import compat

    monkeypatch.setattr(compat, "_direct_send_qualified_cache", True)
    env, _who, request, seen = _owner_env(tmp_path, monkeypatch, lambda: False)
    with pytest.raises(HmpError):
        await server.handle_prompts_list(request)
    assert seen == []
    env.store.close()


@dataclass
class _Snapshot:
    open_requests: tuple[Any, ...]


async def _snapshot_visible(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    owner: bool,
    flag: bool,
    qualifier: Any,
) -> bool:
    env, who, request = _request_env(tmp_path, monkeypatch, flag=flag)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id}) if owner else frozenset()
    env.ctx.approval_qualified = qualifier
    snapshot = _Snapshot(open_requests=({"request_id": REQ},))
    env.ctx.reads = SimpleNamespace(snapshot=lambda *_args: snapshot)
    monkeypatch.setattr(
        server,
        "_result_response",
        lambda value: server.json_response({"open_requests": value.open_requests}),
    )
    response = await server.handle_snapshot(request)
    env.store.close()
    return bool(json.loads(response.body)["open_requests"])


@pytest.mark.asyncio
@pytest.mark.parametrize("qualifier", CLOSED_RESULTS)
async def test_snapshot_metadata_is_stripped_when_approvals_are_closed(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, qualifier: Any
) -> None:
    # Owner device with the send flag on still sees no open requests; the snapshot itself works.
    assert not await _snapshot_visible(
        tmp_path, monkeypatch, owner=True, flag=True, qualifier=qualifier
    )


@pytest.mark.asyncio
async def test_snapshot_metadata_needs_owner_flag_and_qualification(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert await _snapshot_visible(
        tmp_path / "a", monkeypatch, owner=True, flag=True, qualifier=lambda: True
    )
    assert not await _snapshot_visible(
        tmp_path / "b", monkeypatch, owner=False, flag=True, qualifier=lambda: True
    )
    assert not await _snapshot_visible(
        tmp_path / "c", monkeypatch, owner=True, flag=False, qualifier=lambda: True
    )


@pytest.mark.asyncio
async def test_non_owner_never_reaches_the_approval_qualifier(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter: list[int] = []

    def qualifier() -> bool:
        counter.append(1)
        return True

    env, who, request, _seen = _owner_env(tmp_path, monkeypatch, qualifier)
    who.device_id = "dev-non-owner"
    for handler in HANDLERS:
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "not_found"
    assert counter == []
    env.store.close()


@pytest.mark.asyncio
async def test_ordinary_guarded_send_route_ignores_approval_qualification(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    env, _who, request, _seen = _owner_env(tmp_path, monkeypatch, _raises)
    reached: list[str] = []

    async def fake_send(_deps: Any, **kwargs: Any) -> Any:
        reached.append("ds4")
        return SimpleNamespace()

    async def body(_request: Any) -> dict[str, Any]:
        return {"client_message_id": "c", "expected_head": 0, "text": "hi"}

    monkeypatch.setattr(server, "read_json_body", body)
    monkeypatch.setattr(server.direct_send, "handle_direct_send", fake_send)
    monkeypatch.setattr(
        server, "_direct_send_outcome_response", lambda *_a, **_k: web.Response(status=202)
    )
    assert (await server.handle_chat_send(request)).status == 202
    assert reached == ["ds4"]
    env.store.close()


# --- Producer paths: unqualified approval-only work is inert --------------------------------


class _Prompt:
    session_key = "session"
    command = "cmd"
    description = "why"
    choices = ("once", "deny")


class _Bridge:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_gateway_approvals(self, _key: str) -> list[dict[str, str]]:
        self.calls.append("list")
        return [{"command": "cmd", "request_id": REQ}]

    def approval_timeout_s(self, _profile: str) -> int:
        self.calls.append("timeout")
        return 300

    def clarify_timeout_s(self, _profile: str) -> int:
        self.calls.append("clarify_timeout")
        return 3600


@pytest.mark.asyncio
@pytest.mark.parametrize("qualifier", CLOSED_RESULTS)
async def test_closed_hooks_do_not_call_approval_helpers_or_collect_rows(qualifier: Any) -> None:
    store = PromptStore(clock=lambda: 100)
    store.remember_session("session", IID, USER, PROFILE, "chat")
    bridge = _Bridge()
    hooks = prompts.AdapterHooks(store, bridge, lambda: 100, IID, qualifier)
    assert await hooks.on_exec_approval(_Prompt()) is False
    assert (
        await hooks.on_clarify(
            chat_id="chat", question="q", choices=["a"], clarify_id="c1", session_key="session"
        )
        is False
    )
    await hooks.reconcile_chat("chat")
    assert bridge.calls == []
    assert len(store.list_visible(IID, USER, PROFILE)) == 0


@pytest.mark.asyncio
async def test_default_hooks_are_closed() -> None:
    store = PromptStore(clock=lambda: 100)
    store.remember_session("session", IID, USER, PROFILE, "chat")
    bridge = _Bridge()
    hooks = prompts.AdapterHooks(store, bridge, lambda: 100, IID)
    assert await hooks.on_exec_approval(_Prompt()) is False
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_qualified_hooks_collect_rows() -> None:
    store = PromptStore(clock=lambda: 100)
    store.remember_session("session", IID, USER, PROFILE, "chat")
    bridge = _Bridge()
    hooks = prompts.AdapterHooks(store, bridge, lambda: 100, IID, lambda: True)
    assert await hooks.on_exec_approval(_Prompt()) is True
    assert bridge.calls == ["list", "timeout"]


def test_default_direct_send_deps_do_not_bind_prompts() -> None:
    deps = DirectSendDeps(
        bridge=None,  # type: ignore[arg-type]
        store=None,
        locks=ProfileLocks(),
        now=lambda: 1,
    )
    assert deps.approval_qualified() is False


# --- Bot authorization ordering ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthorized_bot_never_reaches_the_approval_qualifier(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter: list[int] = []

    def qualifier() -> bool:
        counter.append(1)
        return True

    env, _who, request, _seen = _owner_env(tmp_path, monkeypatch, qualifier)

    def refuse(*_a: Any, **_k: Any) -> None:
        raise HmpError(ErrorCode.NOT_FOUND)

    monkeypatch.setattr(server, "require_bot_authorized", refuse)
    for handler in HANDLERS:
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "not_found"
    assert counter == []
    env.store.close()


# --- Production adapter wiring ----------------------------------------------------------------


class _WireBridge:
    def __init__(self, _adapter: Any, _directory: Any) -> None:
        pass


@pytest.mark.parametrize("supported", [True, False])
def test_open_components_binds_supported_and_approval_qualification(
    adapter_module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supported: bool  # noqa: F811
) -> None:
    identity_marker = object()
    seen: list[object] = []

    callbacks: list[int] = []

    def factory(read_identity: Any, **_kwargs: Any) -> Any:
        seen.append(read_identity)

        def callback() -> bool:
            callbacks.append(1)
            return True  # even a "yes" must not open an unsupported build

        return callback

    status = compat.CompatStatus.SUPPORTED if supported else compat.CompatStatus.UNSUPPORTED
    outcome = compat.CompatResult(status, identity=identity_marker)  # type: ignore[arg-type]

    class Gate:
        def evaluate(self) -> Any:
            return outcome

    monkeypatch.setattr(adapter_module.compat, "default_gate", lambda **_k: Gate())
    monkeypatch.setattr(adapter_module.compat, "approval_listener_qualifier", factory)
    monkeypatch.setattr(  # the one-shot CLI diagnostic is never the production admission
        adapter_module.compat,
        "approval_build_qualified",
        lambda *_a, **_k: pytest.fail("production admission must use the listener factory"),
    )
    monkeypatch.setattr(
        adapter_module.identity,
        "resolve_custody",
        lambda *_a, **_k: SimpleNamespace(anchor_dir=tmp_path / "anchor"),
    )
    monkeypatch.setattr(
        adapter_module.identity, "load_or_create", lambda _store, **_k: SimpleNamespace(iid=IID)
    )
    monkeypatch.setattr(adapter_module, "_bridge_classes", lambda: (_WireBridge, lambda s: s))
    adapter = SimpleNamespace(config=SimpleNamespace(extra={}))

    ctx = adapter_module.open_components(adapter)
    try:
        # The factory ran exactly once, synchronously, at open; never for an unsupported build.
        assert seen == ([identity_marker] if supported else [])
        assert ctx.approval_qualified() is supported
        assert ctx.approval_qualified() is supported
        assert seen == ([identity_marker] if supported else [])  # callbacks never re-invoke it
        assert len(callbacks) == (2 if supported else 0)
        if supported:
            assert ctx.direct_send_deps.approval_qualified == ctx.approval_qualification_open
            assert adapter._hmp_hooks.approval_qualified == ctx.approval_qualification_open
            assert ctx.approval_qualification_open() is True
        else:
            assert ctx.direct_send_deps is None  # no deps or hooks exist on an unsupported build
            assert not hasattr(adapter, "_hmp_hooks")
            assert ctx.approval_qualification_open() is False
    finally:
        ctx.store.close()


# --- M1/L1: the DS-4 send with approvals closed -----------------------------------------------


def _sse(event: str, payload: dict[str, Any] | None = None) -> bytes:
    body = {"event": event, **(payload or {})}
    return f"event: {event}\ndata: {json.dumps(body)}\n\n".encode()


async def _iterate(parts: list[bytes]) -> Any:
    for part in parts:
        yield part


RUN_ID = "run_" + "56" * 16
SSE_CASES = {
    "keepalive-then-done": [_sse("run.started", {}), b": keepalive\n\n", _sse("done")],
    "keepalive-with-run-id": [
        _sse("run.started", {"run_id": RUN_ID}),
        b": keepalive\n\n",
        _sse("run.completed", {}),
        _sse("done"),
    ],
    "assistant-completed-mailbox": [
        _sse("run.started", {}),
        _sse("assistant.completed", {"content": "hi", "session_id": "tip"}),
        _sse("run.completed", {"session_id": "tip"}),
        _sse("done"),
    ],
    "local": [
        _sse("run.started", {}),
        _sse("message.started", {}),
        _sse("assistant.completed", {"content": "local", "session_id": "tip"}),
        _sse("run.completed", {"session_id": "tip"}),
        _sse("done"),
    ],
    "queued": [_sse("run.started", {}), _sse("run.queued", {}), _sse("done")],
    "refused": [_sse("run.started", {}), _sse("run.failed", {}), _sse("done")],
    "no-terminal": [_sse("run.started", {}), _sse("message.started", {})],
    "started-then-done-no-mailbox-signal": [_sse("run.started", {}), _sse("done")],
}


async def _consume(parts: list[bytes], bind: Any) -> tuple[str, Any]:
    try:
        return "ok", await direct_send.consume_sse(_iterate(parts), bind=bind)
    except Exception as exc:
        return "err", (type(exc), str(exc))


@pytest.mark.asyncio
@pytest.mark.parametrize("case", sorted(SSE_CASES))
async def test_send_result_classification_is_identical_bound_and_unbound(case: str) -> None:
    store = PromptStore(clock=lambda: 1)
    bind = direct_send.StreamBind(
        store=store, iid=IID, user_id=USER, profile=PROFILE, now=lambda: 5_000, timeout_s=300
    )
    assert await _consume(SSE_CASES[case], None) == await _consume(SSE_CASES[case], bind)


@pytest.mark.asyncio
async def test_unbound_keepalive_mailbox_stream_is_queued_not_unknown() -> None:
    kind, result = await _consume(SSE_CASES["keepalive-then-done"], None)
    assert kind == "ok" and result.status == 202 and result.body == {"queued": True}


def _direct_send_deps(
    sqlite: Store, loopback: Any, *, qualifier: Any, timeout: Any = None
) -> DirectSendDeps:
    from .test_direct_send import clean_bridge

    return DirectSendDeps(
        bridge=clean_bridge(head=5),  # type: ignore[arg-type]
        store=sqlite,
        locks=ProfileLocks(),
        now=lambda: 1000,
        loopback_call=loopback,
        prompt_store=PromptStore(clock=lambda: 1),  # type: ignore[arg-type]
        approval_timeout=timeout,
        approval_qualified=qualifier,
    )


async def _send(deps: DirectSendDeps) -> Any:
    from .test_direct_send import OPEN

    return await direct_send.handle_direct_send(
        deps,
        iid="i1",
        user_id="u1",
        profile="default",
        request=DirectSendRequest(client_message_id="c1", expected_head=5, text="hi"),
        flag_enabled=True,
        base_write_gate=OPEN,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("qualifier", CLOSED_RESULTS)
async def test_closed_approvals_send_is_ordinary_and_unbound(
    tmp_path: Any, qualifier: Any
) -> None:
    sqlite = Store(tmp_path / "h.sqlite3")
    sqlite.migrate()
    events: list[str] = []
    binds: list[Any] = []

    async def loopback(*_a: Any) -> direct_send.LoopbackResult:
        binds.append(direct_send._STREAM_BIND.get())
        events.append("loopback")
        return direct_send.LoopbackResult(
            status=202, body={"queued": True}, effective_session_id=None
        )

    def timeout(_profile: str) -> int:
        events.append("approval_timeout")
        return 300

    outcome = await _send(_direct_send_deps(sqlite, loopback, qualifier=qualifier, timeout=timeout))
    assert outcome.state == "queued"
    assert events == ["loopback"]  # no approval_timeout call
    assert binds == [None]  # no stream bind
    sqlite.close()


@pytest.mark.asyncio
async def test_open_approvals_send_still_binds_the_stream(tmp_path: Any) -> None:
    sqlite = Store(tmp_path / "h.sqlite3")
    sqlite.migrate()
    binds: list[Any] = []

    async def loopback(*_a: Any) -> direct_send.LoopbackResult:
        binds.append(direct_send._STREAM_BIND.get())
        return direct_send.LoopbackResult(
            status=202, body={"queued": True}, effective_session_id=None
        )

    outcome = await _send(_direct_send_deps(sqlite, loopback, qualifier=lambda: True))
    assert outcome.state == "queued"
    assert len(binds) == 1 and binds[0] is not None
    sqlite.close()


@pytest.mark.asyncio
async def test_approval_qualification_runs_before_lock_and_head_checks(tmp_path: Any) -> None:
    sqlite = Store(tmp_path / "h.sqlite3")
    sqlite.migrate()
    order: list[str] = []

    async def loopback(*_a: Any) -> direct_send.LoopbackResult:
        order.append("loopback")
        return direct_send.LoopbackResult(
            status=202, body={"queued": True}, effective_session_id=None
        )

    def qualifier() -> bool:
        order.append("qualify")
        return False

    deps = _direct_send_deps(sqlite, loopback, qualifier=qualifier)
    real_lease = deps.bridge.lease_snapshot

    def lease(profile: str) -> Any:
        order.append("lease")
        return real_lease(profile)

    deps.bridge.lease_snapshot = lease  # type: ignore[method-assign]
    await _send(deps)
    assert order == ["qualify", "lease", "loopback"]
    sqlite.close()
