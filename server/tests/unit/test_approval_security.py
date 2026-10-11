"""Regressions for both independent F3 security reviews."""

from __future__ import annotations

from types import SimpleNamespace

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer, make_mocked_request

from hmp_plugin import direct_send as ds
from hmp_plugin import prompts, server
from hmp_plugin.contract import DirectSendEndpoint, HmpError, WireMessage, WriteGate, WriteGateState
from hmp_plugin.reads import Reads

from .hmp_kit import Env
from .test_approvals import (
    IID,
    PROFILE,
    REQ,
    RUN,
    USER,
    FakeResolver,
    _answer,
    _arm,
    _chunks,
    _frame,
    _store_approval,
)


def _request_env(tmp_path, monkeypatch, *, flag=True):
    env = Env(tmp_path)
    _arm(env, flag=flag)
    who = SimpleNamespace(device_id="dev-owner", user_id=USER)
    monkeypatch.setattr(server, "bearer", lambda request: who)
    monkeypatch.setattr(server, "context", lambda request: env.ctx)
    request = make_mocked_request("GET", "/", match_info={"p": "b", "request_id": REQ})
    return env, who, request


@pytest.mark.asyncio
async def test_non_owner_device_cannot_use_any_prompt_route(tmp_path, monkeypatch) -> None:
    env, who, request = _request_env(tmp_path, monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({"dev-owner"})
    # Same authenticated user, different paired device. User-level ownership is insufficient.
    who.device_id = "dev-non-owner"
    for handler in (
        server.handle_prompts_list,
        server.handle_prompt_answer,
        server.handle_phone_send,
    ):
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "not_found"
    assert not env.ctx.prompt_store._locks
    env.store.close()


@pytest.mark.asyncio
async def test_controls_grant_alone_never_opens_an_approval_route(tmp_path, monkeypatch) -> None:
    """The per-device jobs/model controls grant is a different privilege from approvals."""
    env, who, request = _request_env(tmp_path, monkeypatch)
    env.store.insert_user(USER, "label", 1000)
    env.store.insert_device(who.device_id, USER, "f" * 64, b"x", "phone", 1000, state="ACTIVE")
    env.ctx.owner_device_ids = lambda: frozenset()
    assert env.store.set_owner_controls(who.device_id, allowed=True, now=1001)
    assert env.ctx.is_owner_device(who.device_id) is True
    assert env.ctx.is_approval_owner_device(who.device_id) is False
    for handler in (
        server.handle_prompts_list,
        server.handle_prompt_answer,
        server.handle_phone_send,
    ):
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "not_found"
    env.store.close()


@pytest.mark.asyncio
async def test_controls_denial_closes_an_allowlisted_approval_device(tmp_path, monkeypatch) -> None:
    env, who, request = _request_env(tmp_path, monkeypatch)
    env.store.insert_user(USER, "label", 1000)
    env.store.insert_device(who.device_id, USER, "f" * 64, b"x", "phone", 1000, state="ACTIVE")
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})
    assert env.ctx.is_approval_owner_device(who.device_id) is True
    assert env.store.set_owner_controls(who.device_id, allowed=False, now=1001)
    assert env.ctx.is_approval_owner_device(who.device_id) is False
    for handler in (server.handle_prompts_list, server.handle_prompt_answer):
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "not_found"
    env.store.close()


@pytest.mark.asyncio
async def test_flag_off_even_with_full_guarantees(tmp_path, monkeypatch) -> None:
    env, who, request = _request_env(tmp_path, monkeypatch, flag=False)
    env.ctx.write_gate = lambda: WriteGate(WriteGateState.OPEN, None)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})

    async def body(request):
        return {"client_message_id": "c", "text": "hi"}

    monkeypatch.setattr(server, "read_json_body", body)
    for handler in (
        server.handle_prompts_list,
        server.handle_prompt_answer,
        server.handle_phone_send,
    ):
        with pytest.raises(HmpError) as caught:
            await handler(request)
        assert caught.value.code.value == "write_gate_closed"
    env.store.close()


def _rate_env(tmp_path, monkeypatch):
    env, who, request = _request_env(tmp_path, monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({"dev-owner", "dev-second"})

    async def body(request):
        return {"client_message_id": "c", "text": "hello"}

    async def phone(**kwargs):
        return prompts.HttpResult(202, {"state": "submitted"})

    monkeypatch.setattr(server, "read_json_body", body)
    monkeypatch.setattr(prompts, "handle_phone_send", phone)
    return env, who, request


@pytest.mark.asyncio
@pytest.mark.parametrize("cadence", [3, 15])
async def test_phone_polling_and_answers_across_windows(tmp_path, monkeypatch, cadence):
    env, _, request = _rate_env(tmp_path, monkeypatch)
    try:
        # Ten minutes, starting just before a window boundary. One answer, send and
        # immediate refresh per poll deliberately exceed ordinary human activity.
        start = (env.clock.now // 60) * 60 + 59
        for elapsed in range(0, 600, cadence):
            env.clock.now = start + elapsed
            assert (await server.handle_prompts_list(request)).status == 200
            assert (await server.handle_prompt_answer(request)).status == 404  # unknown ID
            assert (await server.handle_phone_send(request)).status == 202
            assert (await server.handle_prompts_list(request)).status == 200
    finally:
        env.store.close()


@pytest.mark.asyncio
async def test_prompt_buckets_are_bounded_separate_and_per_device(tmp_path, monkeypatch):
    env, who, request = _rate_env(tmp_path, monkeypatch)
    try:
        for _ in range(60):
            assert (await server.handle_prompts_list(request)).status == 200
        with pytest.raises(HmpError) as caught:
            await server.handle_prompts_list(request)
        assert caught.value.code.value == "rate_limited"
        # Poll exhaustion must leave the complete answer/send budget available.
        for _ in range(30):
            assert (await server.handle_prompt_answer(request)).status == 404
            assert (await server.handle_phone_send(request)).status == 202
        # A new profile/request ID is not a new budget. Rejection happens before
        # authorization, body parsing or delivery, for every route.
        request = make_mocked_request("POST", "/", match_info={"p": "other", "request_id": "new"})
        for handler in (server.handle_prompts_list, server.handle_prompt_answer,
                        server.handle_phone_send):
            with pytest.raises(HmpError) as caught:
                await handler(request)
            assert caught.value.code.value == "rate_limited"
        # A second owner device of the SAME user has independent bounded budgets.
        who.device_id = "dev-second"
        request = make_mocked_request("GET", "/", match_info={"p": "b", "request_id": REQ})
        assert (await server.handle_prompts_list(request)).status == 200
        assert (await server.handle_prompt_answer(request)).status == 404
        assert (await server.handle_phone_send(request)).status == 202
        who.device_id = "dev-owner"
        env.clock.now += 60
        assert (await server.handle_prompts_list(request)).status == 200
        assert (await server.handle_prompt_answer(request)).status == 404
    finally:
        env.store.close()


@pytest.mark.asyncio
async def test_unknown_ids_allocate_nothing() -> None:
    store = prompts.PromptStore(clock=lambda: 100)
    for i in range(200):
        result = await _answer(store, FakeResolver(), {"choice": "once"}, request_id=f"unknown-{i}")
        assert result.status == 404
    assert not store._locks and not store._rows


@pytest.mark.asyncio
async def test_expiry_hides_refuses_and_purges_lock() -> None:
    store = prompts.PromptStore(clock=lambda: 100)
    _store_approval(store, expires_at=100)
    listed = prompts.list_prompts(store, iid=IID, user_id=USER, profile=PROFILE, now=131)
    assert listed.body["prompts"] == []
    resolver = FakeResolver()
    result = await _answer(store, resolver, {"choice": "once"}, now=131)
    assert result.status == 409 and result.body["applied"] is False
    assert not resolver.calls
    store.purge(131 + prompts.IDEMPOTENCY_RETENTION_S)
    assert not store._rows and not store._locks


@pytest.mark.asyncio
async def test_retired_clarify_is_never_forwarded() -> None:
    from .test_approvals import _store_clarify

    store = prompts.PromptStore(clock=lambda: 100)
    _store_clarify(store)
    hooks = prompts.AdapterHooks(store, object(), lambda: 10, IID)
    hooks.retire(REQ)
    resolver = FakeResolver()
    result = await _answer(store, resolver, {"choice": "Ship it"}, now=11)
    assert result.status == 409 and not resolver.calls


def test_observations_have_global_cap_ttl_and_no_snapshot_injection() -> None:
    store = prompts.PromptStore(clock=lambda: 100)
    for i in range(300):
        store.add_observation(IID, str(i), PROFILE, role="assistant", text="old", now=10)
    assert sum(map(len, store._observations.values())) <= 256
    store.purge(71)
    assert not store._observations
    reads = object.__new__(Reads)
    reads._prompt_store, reads._iid, reads._clock = store, IID, lambda: 100
    store.add_observation(IID, USER, PROFILE, role="assistant", text="old", now=100)
    durable = (
        WireMessage(id=1, role="assistant", text="old", created_at=100, client_message_id=None),
    )
    assert reads._with_observations(USER, PROFILE, durable) == durable
    assert not store.observations(IID, USER, PROFILE)
    assert reads._with_observations(USER, PROFILE, ()) == ()
    store.add_observation(IID, USER, PROFILE, role="assistant", text="unmatched", now=100)
    assert reads._with_observations(USER, PROFILE, ()) == ()


@pytest.mark.asyncio
async def test_sse_crlf_split_and_mismatched_run() -> None:
    data = b"".join(
        (
            _frame("run.started", {"run_id": RUN}),
            _frame("assistant.completed", {"run_id": RUN, "content": "ok"}),
            _frame("done"),
        )
    ).replace(b"\n", b"\r\n")
    result = await ds.consume_sse(_chunks(*(bytes([b]) for b in data)), bind=None)
    assert result.status == 200
    with pytest.raises(aiohttp.ClientPayloadError):
        await ds.consume_sse(
            _chunks(
                _frame("run.started", {"run_id": RUN}),
                _frame("approval.request", {"run_id": "foreign"}),
            ),
            bind=None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [65537, 131073])
async def test_sse_oversized_frame_rejected(size) -> None:
    with pytest.raises(aiohttp.ClientPayloadError, match="limit"):
        await ds.consume_sse(_chunks(b"data: " + b"x" * size), bind=None)


@pytest.mark.asyncio
async def test_http_redirects_and_content_type() -> None:
    calls = []

    async def redirect(request):
        raise web.HTTPTemporaryRedirect(location="/target")

    async def target(request):
        calls.append(True)
        return web.json_response({"resolved": 1})

    app = web.Application()
    app.router.add_post("/v1/runs/{run}/approval", redirect)
    app.router.add_post("/api/sessions/{sid}/chat/stream", redirect)
    app.router.add_post("/target", target)
    async with TestServer(app) as server:
        endpoint = DirectSendEndpoint(
            host="127.0.0.1", port=server.port, api_key="test-fixture-key", path_prefix=""
        )
        assert await ds.aiohttp_approval_call(endpoint, RUN, REQ, "once") == "unavailable"
        assert (await ds.aiohttp_stream_call(endpoint, "s", "hi")).status == 307
        assert not calls


@pytest.mark.asyncio
async def test_clients_set_finite_timeouts_and_disable_redirects(monkeypatch) -> None:
    real = aiohttp.ClientSession
    captured = []

    def session(*args, **kwargs):
        captured.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(aiohttp, "ClientSession", session)
    endpoint = DirectSendEndpoint(
        host="127.0.0.1", port=1, api_key="test-fixture-key", path_prefix=""
    )
    await ds.aiohttp_approval_call(endpoint, RUN, REQ, "deny")
    with pytest.raises(aiohttp.ClientError):
        await ds.aiohttp_stream_call(endpoint, "s", "hi")
    assert len(captured) == 2
    for kwargs in captured:
        assert kwargs["trust_env"] is False
        assert kwargs["auto_decompress"] is False
        assert kwargs["timeout"].total > 0
        assert kwargs["timeout"].sock_read > 0


@pytest.mark.asyncio
async def test_ambiguous_binding_has_deny_only_recovery() -> None:
    store = prompts.PromptStore(clock=lambda: 100)
    store.remember_session("session", IID, USER, PROFILE, "chat")

    class Bridge:
        def list_gateway_approvals(self, key):
            return [{"command": "cmd", "request_id": "a"}, {"command": "cmd", "request_id": "b"}]

    class Prompt:
        session_key, command, choices = "session", "cmd", ("once", "deny")

    hooks = prompts.AdapterHooks(store, Bridge(), lambda: 100, IID, lambda: True)
    assert await hooks.on_exec_approval(Prompt()) is True
    assert {r.request_id for r in store._rows.values()} == {"a", "b"}
    assert all(r.choices == ("deny",) for r in store._rows.values())

    pending = {"a", "b"}

    class Resolver(FakeResolver):
        async def resolve_approval(self, row, choice):
            assert row.session_key == "session" and choice == "deny"
            pending.remove(row.request_id)
            return "accepted"

    resolver = Resolver()
    for request_id in ("a", "b"):
        denied = await _answer(store, resolver, {"choice": "deny"}, request_id=request_id, now=101)
        assert denied.body["applied"] is True
    assert not pending

    async def deliver():
        return True

    result, _ = await prompts._phone_turn(
        prompts=store,
        iid=IID,
        user_id=USER,
        profile=PROFILE,
        chat_id="chat",
        text="next",
        now=102,
        resolver=resolver,
        session_key=lambda: "session",
        pending_approvals=lambda key: list(pending),
        deliver=deliver,
    )
    assert result.status == 202


@pytest.mark.asyncio
async def test_owner_devices_share_one_answer_and_revocation_is_live(tmp_path, monkeypatch):
    import asyncio

    env, who, request = _request_env(tmp_path, monkeypatch)
    allowed = {"dev-owner", "dev-owner-2"}
    env.ctx.owner_device_ids = lambda: frozenset(allowed)
    row = prompts.PromptRow(
        iid=env.iid,
        user_id=USER,
        profile="b",
        request_id=REQ,
        kind="approval",
        surface="bot_chat",
        choices=("once", "deny"),
        run_id=RUN,
    )
    env.ctx.prompt_store.put(row)
    resolver = FakeResolver()
    monkeypatch.setattr(server, "_LivePromptResolver", lambda *_: resolver)

    async def body(request):
        return {"choice": "once"}

    monkeypatch.setattr(server, "read_json_body", body)
    first = asyncio.create_task(server.handle_prompt_answer(request))
    await asyncio.sleep(0)
    who.device_id = "dev-owner-2"
    second = asyncio.create_task(server.handle_prompt_answer(request))
    assert [r.status for r in await asyncio.gather(first, second)] == [200, 200]
    assert len(resolver.calls) == 1
    allowed.remove("dev-owner-2")
    with pytest.raises(HmpError) as caught:
        await server.handle_prompt_answer(request)
    assert caught.value.code.value == "not_found"
    env.store.close()


@pytest.mark.asyncio
async def test_profile_timeout_is_used_by_both_adapter_hooks():
    store = prompts.PromptStore(clock=lambda: 100)
    store.remember_session("session", IID, USER, PROFILE, "chat")
    calls = []

    class Bridge:
        def list_gateway_approvals(self, key):
            return [{"command": "cmd", "request_id": REQ}]

        def phone_approval_timeout_s(self, profile):
            calls.append(("approval", profile))
            return 0

        def phone_clarify_timeout_s(self, profile):
            calls.append(("clarify", profile))
            return 0

    class Prompt:
        session_key, command, choices = "session", "cmd", ("once", "deny")

    hooks = prompts.AdapterHooks(store, Bridge(), lambda: 100, IID, lambda: True)
    assert await hooks.on_exec_approval(Prompt())
    assert store.get((IID, USER, PROFILE, REQ)).expires_at == 100
    await hooks.on_clarify(
        chat_id="chat", question="q", choices=[], clarify_id="clarify", session_key="session"
    )
    assert store.get((IID, USER, PROFILE, "clarify")).expires_at is None
    assert calls == [("approval", PROFILE), ("clarify", PROFILE)]


@pytest.mark.asyncio
async def test_expiry_hint_has_grace_but_authoritative_gone_expires_immediately():
    store = prompts.PromptStore(clock=lambda: 100)
    _store_approval(store, expires_at=100, session_key="session", surface="phone_chat")
    assert prompts.list_prompts(store, iid=IID, user_id=USER, profile=PROFILE, now=125).body[
        "prompts"
    ]
    store.remember_session("session", IID, USER, PROFILE, "chat")

    class Bridge:
        def list_gateway_approvals(self, key):
            return []

    hooks = prompts.AdapterHooks(store, Bridge(), lambda: 125, IID, lambda: True)
    await hooks.reconcile_chat("chat")
    resolver = FakeResolver()
    result = await _answer(store, resolver, {"choice": "once"}, now=125)
    assert result.status == 409 and not resolver.calls


@pytest.mark.asyncio
async def test_purge_cannot_replace_a_lock_with_waiting_answerers():
    import asyncio

    store = prompts.PromptStore(clock=lambda: 100)
    _store_approval(store)
    key = (IID, USER, PROFILE, REQ)
    entered = asyncio.Event()
    release = asyncio.Event()

    class Slow(FakeResolver):
        async def resolve_approval(self, row, choice):
            entered.set()
            await release.wait()
            return await super().resolve_approval(row, choice)

    resolver = Slow()
    first = asyncio.create_task(_answer(store, resolver, {"choice": "once"}))
    await entered.wait()
    second = asyncio.create_task(_answer(store, resolver, {"choice": "once"}))
    await asyncio.sleep(0)
    row = store.get(key)
    row.settled_at = 0
    lock = store._locks[key]
    store.purge(prompts.IDEMPOTENCY_RETENTION_S + 1)
    assert store.get(key) is row and store._locks[key] is lock
    release.set()
    await asyncio.gather(first, second)
    assert len(resolver.calls) == 1
    store.purge(prompts.IDEMPOTENCY_RETENTION_S + 2001)
    assert not store._rows and not store._locks and not store._lock_users


@pytest.mark.asyncio
@pytest.mark.parametrize("status,content_type", [(307, "text/event-stream"), (200, "text/plain")])
async def test_http_response_policy_without_network(monkeypatch, status, content_type):
    import json

    class Response:
        def __init__(self):
            self.headers = {"Content-Type": content_type}
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Session:
        def __init__(self, **kwargs):
            self.connector = kwargs["connector"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.connector.close()

        def post(self, url, **kwargs):
            assert kwargs.get("allow_redirects") is False
            assert json.dumps(kwargs["json"])
            return Response()

    monkeypatch.setattr(aiohttp, "ClientSession", Session)
    endpoint = DirectSendEndpoint(host="127.0.0.1", port=9, api_key="fixture-key", path_prefix="")
    if status == 307:
        assert await ds.aiohttp_approval_call(endpoint, RUN, REQ, "once") == "unavailable"
    result = await ds.aiohttp_stream_call(endpoint, "s", "hi")
    assert result.status == (307 if status == 307 else 502)


@pytest.mark.asyncio
async def test_waiting_answer_rechecks_expiry_after_lock():
    import asyncio

    clock = [100]
    store = prompts.PromptStore(clock=lambda: clock[0])
    _store_approval(store, expires_at=125)
    started, release = asyncio.Event(), asyncio.Event()

    class Slow(FakeResolver):
        async def resolve_approval(self, row, choice):
            started.set()
            await release.wait()
            return await super().resolve_approval(row, choice)

    resolver = Slow("unavailable")
    first = asyncio.create_task(_answer(store, resolver, {"choice": "once"}, now=100))
    await started.wait()
    second = asyncio.create_task(_answer(store, resolver, {"choice": "once"}, now=100))
    await asyncio.sleep(0)
    clock[0] = 200
    release.set()
    assert (await first).status == 503
    stale = await second
    assert stale.status == 409 and stale.body["applied"] is False
    assert len(resolver.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(("owner", "flag"), [(False, True), (True, False), (True, True)])
async def test_snapshot_cannot_bypass_prompt_ownership(tmp_path, monkeypatch, owner, flag):
    import json
    from dataclasses import dataclass

    @dataclass
    class Snapshot:
        open_requests: tuple

    env, who, request = _request_env(tmp_path, monkeypatch, flag=flag)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id}) if owner else frozenset()
    snapshot = Snapshot(open_requests=({"request_id": REQ},))
    env.ctx.reads = SimpleNamespace(snapshot=lambda *args: snapshot)
    monkeypatch.setattr(
        server,
        "_result_response",
        lambda value: server.json_response({"open_requests": value.open_requests}),
    )
    response = await server.handle_snapshot(request)
    assert bool(json.loads(response.body)["open_requests"]) is (owner and flag)
    env.store.close()


@pytest.mark.asyncio
async def test_snapshot_hides_a_phone_row_while_phone_chat_is_closed(tmp_path, monkeypatch):
    import json
    from dataclasses import dataclass

    @dataclass
    class Snapshot:
        open_requests: tuple

    env, who, request = _request_env(tmp_path, monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})
    env.ctx.approvals_available = lambda: True  # Bot Chat approvals open
    env.ctx.phone_chat_available = lambda: False  # Phone chat closed
    store = env.ctx.prompt_store
    store.put(
        prompts.PromptRow(
            iid=IID, user_id=USER, profile="b", request_id=REQ, kind="approval",
            surface="phone_chat", choices=("once", "deny"), command="cmd", session_key="sess",
            observed_at=1, expires_at=301,
        )
    )
    rows = tuple(
        prompts.phone_open_request(row)
        for row in store.list_visible(IID, USER, "b", now=1)
        if row.surface == "phone_chat"
    )
    assert rows  # the phone row is stored and would be visible
    env.ctx.reads = SimpleNamespace(snapshot=lambda *args: Snapshot(open_requests=rows))
    monkeypatch.setattr(
        server,
        "_result_response",
        lambda value: server.json_response({"open_requests": value.open_requests}),
    )
    response = await server.handle_snapshot(request)
    assert json.loads(response.body)["open_requests"] == []
    env.store.close()


@pytest.mark.asyncio
async def test_prompt_authorization_runs_off_event_loop(tmp_path, monkeypatch):
    import threading

    env, who, request = _request_env(tmp_path, monkeypatch)
    env.ctx.owner_device_ids = lambda: frozenset({who.device_id})
    loop_thread = threading.get_ident()
    called = []

    def authorize(*args):
        called.append(threading.get_ident())
        assert threading.get_ident() != loop_thread

    monkeypatch.setattr(server, "require_bot_authorized", authorize)
    assert (await server.handle_prompts_list(request)).status == 200
    assert called
    env.store.close()


@pytest.mark.asyncio
async def test_approval_response_body_is_bounded(monkeypatch):
    from contextlib import asynccontextmanager

    class Content:
        async def read(self, size):
            return b"x" * min(size, 65537)

    async def unbounded_json(**kwargs):
        # Old resp.json() would buffer everything before returning the parsed value.
        return {"resolved": 1}

    @asynccontextmanager
    async def response():
        yield SimpleNamespace(status=200, content=Content(), json=unbounded_json)

    @asynccontextmanager
    async def session(**kwargs):
        try:
            yield SimpleNamespace(post=lambda *a, **kw: response())
        finally:
            await kwargs["connector"].close()

    monkeypatch.setattr(aiohttp, "ClientSession", session)
    endpoint = DirectSendEndpoint(host="127.0.0.1", port=9, api_key="fixture-key", path_prefix="")
    assert await ds.aiohttp_approval_call(endpoint, RUN, REQ, "once") == "unavailable"
