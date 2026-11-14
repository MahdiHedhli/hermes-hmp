"""Accepted scoped GET through actual routes/service and exact ordinary AP3 handler."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from hmp_plugin import approval_test_routes as routes
from hmp_plugin import prompts, server, wire
from hmp_plugin.approval_test_producer import TestStatus
from hmp_plugin.approval_test_service import TestCard
from hmp_plugin.contract import ApprovalTestTarget
from hmp_plugin.request_ctx import CTX_KEY

from .hmp_kit import Env, get, pair, run
from .test_approval_test_authority_service import admitted, finish, rig
from .test_approval_test_routes import decoded, request
from .test_approvals import _arm


@pytest.mark.parametrize("profile", ["bot", "foreign", "../bot", "bot/child"])
def test_scoped_handler_uses_exact_path_profile_and_full_service(profile):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            before = r.ctx.bridge.calls
            req = request(r, path="/bots/" + profile + "/approval-tests/current", profile=profile)
            body = decoded(await routes.handle_scoped_current(req))
            assert set(body) == {"v", "card"} and body["v"] == 1
            assert (body["card"] is not None) == (profile == "bot")
            if profile == "bot":
                assert r.ctx.bridge.calls > before
            else:
                assert r.ctx.bridge.calls == before
            assert r.made[0].answer_calls == [] and r.made[0].cancel_calls == 0
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("transition", ["owner", "target", "native", "expired", "settled"])
def test_scoped_full_authority_after_gate_await_never_emits_stale_card(monkeypatch, transition):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        loop = asyncio.get_running_loop()
        original_time = loop.time
        offset = [0.0]
        monkeypatch.setattr(loop, "time", lambda: original_time() + offset[0])
        def mutate():
            if transition == "owner":
                r.ctx.owners = frozenset()
            elif transition == "target":
                r.ctx.bridge.target = ApprovalTestTarget(
                    Path("/synthetic/profile"), "root", "new-tip")
            elif transition == "native":
                r.native[0] = False
            elif transition == "expired":
                offset[0] += 31.0
            else:
                r.made[0].settle(TestStatus.DENIED)
        r.gate_hook.append(mutate)
        try:
            req = request(r, path="/bots/bot/approval-tests/current")
            assert decoded(await routes.handle_scoped_current(req)) == {"v": 1, "card": None}
            assert r.made[0].answer_calls == [] and r.made[0].cancel_calls == 0
        finally:
            await finish(r, lease)
            monkeypatch.setattr(loop, "time", original_time)
    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["tip", "home", "grant", "missing"])
def test_scoped_get_rechecks_native_target_each_read_not_cached_card(change):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r, path="/bots/bot/approval-tests/current")
            assert decoded(await routes.handle_scoped_current(req))["card"] is not None
            calls = r.ctx.bridge.calls
            if change == "tip":
                r.ctx.bridge.target = ApprovalTestTarget(
                    Path("/synthetic/profile"), "root", "new-tip")
            elif change == "home":
                r.ctx.bridge.target = ApprovalTestTarget(Path("/synthetic/replaced"), "root", "tip")
            elif change == "grant":
                r.ctx.bridge.authorized = False
            else:
                r.ctx.bridge.target = None
            assert decoded(await routes.handle_scoped_current(req)) == {"v": 1, "card": None}
            assert r.ctx.bridge.calls >= calls
            assert r.made[0].answer_calls == [] and r.made[0].cancel_calls == 0
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["lost", "raising"])
def test_scoped_identity_failure_after_authority_await_aborts_without_card(kind):
    async def scenario():
        r = rig()
        req = request(r, path="/bots/bot/approval-tests/current")
        notifications = []
        r.ctx.on_identity_changed = lambda: notifications.append(True)
        async def late(*_args, **_kwargs):
            await asyncio.sleep(0)
            if kind == "lost":
                r.ctx.current = False
            else:
                def raising():
                    raise RuntimeError("synthetic private identity failure")
                r.ctx.identity.still_current = raising
            return TestCard("a" * 32)
        r.service.phone_card = late
        try:
            response = await routes.handle_scoped_current(req)
            assert response.status == 503
            assert decoded(response) == {"v": 1, "result": "unavailable"}
            assert notifications == [True]
            req.transport.abort.assert_called_once()
            assert b"synthetic private identity failure" not in response.body
        finally:
            await r.service.shutdown()
    asyncio.run(scenario())


def test_older_host_scoped_404_keeps_ordinary_handler_independent(tmp_path):
    """An isolated app with the original ordinary route has no scoped extension route.

    This exercises real HTTP404/error shaping and ordinary handler functionality,
    not a historical-host binary or native qualification.
    """
    env = Env(tmp_path)
    _arm(env, flag=True)
    seen = []
    class Service:
        async def phone_card(self, *_args, **_kwargs):
            seen.append(True)
            raise AssertionError("ordinary AP3 must never enter synthetic observation")
    env.ctx.approval_test_service = Service()
    env.ctx.approval_test_current = lambda: True
    older = web.Application(middlewares=[server.current_key_middleware, server.error_middleware,
                                        server.peer_middleware, server.limits_middleware,
                                        server.compat_middleware])
    older[CTX_KEY] = env.ctx
    older.router.add_get(server.full_path("/bots/{p}/prompts"), server.handle_prompts_list,
                         allow_head=False)
    # Pair using the full existing app first; use the ordinary-only app for compatibility reads.
    dev = []
    async def pair_first(client):
        dev.append(await pair(env, client))
    try:
        run(env, pair_first)
    except BaseException:
        env.store.close()
        raise
    env.ctx.owner_device_ids = lambda: frozenset({dev[0].device_id})
    env.app = lambda: older
    async def scenario(client):
        status, body = await get(client, "/bots/bot/approval-tests/current",
                                 headers=env.headers(dev[0]))
        assert status == 404 and body["error"]["code"] == "not_found"
        status, body = await get(client, "/bots/bot/prompts", headers=env.headers(dev[0]))
        assert status == 200 and body == {
            "prompts": [], "desktop_held": False, "desktop_ownership": "unknown"}
        assert seen == []
    try:
        run(env, scenario)
    finally:
        env.store.close()


@pytest.mark.parametrize("ownership", ["owned", "unowned", "unknown"])
def test_ordinary_open_bot_desktop_await_never_invokes_scoped_observer(tmp_path, ownership):
    env = Env(tmp_path)
    _arm(env, flag=True)
    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        user = env.store.get_device(dev.device_id)["user_id"]
        row = prompts.PromptRow(iid=env.iid, user_id=user, profile="bot", request_id="ordinary-bot",
                                kind="approval", surface="bot_chat", choices=("deny",),
                                command="synthetic ordinary command", observed_at=env.clock.now,
                                expires_at=env.clock.now + 3600, run_id="synthetic-ordinary-run")
        env.ctx.prompt_store.put(row)
        entered = asyncio.Event()
        release = asyncio.Event()
        desktop_calls = []
        synthetic_calls = []
        class Desktop:
            can_observe = True
            async def observe(self, *, profile, canonical_lineage):
                desktop_calls.append((profile, canonical_lineage))
                entered.set()
                await release.wait()
                return prompts.DesktopOwnership(ownership)
        class Service:
            async def phone_card(self, _request, profile=None):
                synthetic_calls.append(profile)
                return TestCard("a" * 32)
        env.ctx.desktop_ownership = Desktop()
        env.ctx.approval_test_service = Service()
        env.ctx.approval_test_current = lambda: True
        req = make_mocked_request("GET", "/bots/bot/prompts", headers=env.headers(dev),
                                  match_info={"p": "bot"})
        req.app[CTX_KEY] = env.ctx
        ordinary = asyncio.create_task(server.handle_prompts_list(req))
        try:
            await entered.wait()
            assert synthetic_calls == [] and not ordinary.done()
            scoped = make_mocked_request("GET", "/bots/bot/approval-tests/current",
                                         headers=env.headers(dev), match_info={"p": "bot"})
            scoped.app[CTX_KEY] = env.ctx
            projection = decoded(await routes.handle_scoped_current(scoped))
            assert projection["card"]["test_id"] == "a" * 32
            assert not ordinary.done() and synthetic_calls == ["bot"]
            release.set()
            response = await ordinary
            body = wire.parse_body(response.body)
            assert body == {
                "prompts": [prompts.wire_prompt(row)] if ownership == "unowned" else [],
                "desktop_held": ownership == "owned", "desktop_ownership": ownership}
            assert desktop_calls == [("bot", ("test-root", "test-tip"))]
            assert synthetic_calls == ["bot"]
        finally:
            release.set()
            if not ordinary.done():
                await ordinary
    try:
        run(env, scenario)
    finally:
        env.store.close()


@pytest.mark.parametrize("failure", ["bad_card", "internal"])
def test_scoped_failure_shape_is_fixed_and_ordinary_projection_still_completes(tmp_path, failure):
    env = Env(tmp_path)
    _arm(env, flag=True)
    seen = []
    class Service:
        async def phone_card(self, _request, profile=None):
            seen.append(profile)
            if failure == "bad_card":
                return object()
            raise RuntimeError("synthetic private failure")
    env.ctx.approval_test_service = Service()
    env.ctx.approval_test_current = lambda: True
    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, body = await get(client, "/bots/bot/approval-tests/current",
                                 headers=env.headers(dev))
        assert status == 503 and body == {"v": 1, "result": "unavailable"}
        status, body = await get(client, "/bots/bot/prompts", headers=env.headers(dev))
        assert status == 200 and body == {
            "prompts": [], "desktop_held": False, "desktop_ownership": "unknown"}
        assert seen == ["bot"]
    try:
        run(env, scenario)
    finally:
        env.store.close()


@pytest.mark.parametrize("selector", ["query", "body", "transfer"])
def test_scoped_query_or_body_cannot_replace_foreign_path_profile(selector):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            before = r.ctx.bridge.calls
            path = "/bots/foreign/approval-tests/current"
            body = None
            headers = None
            if selector == "query":
                path += "?profile=bot"
            elif selector == "body":
                body = b'{"profile":"bot"}'
            else:
                headers = [("Transfer-Encoding", "chunked")]
            req = request(r, path=path, profile="foreign", body=body, headers=headers)
            response = await routes.handle_scoped_current(req)
            assert response.status == 400
            assert decoded(response) == {"v": 1, "result": "bad_request"}
            assert r.ctx.bridge.calls == before
            assert r.made[0].answer_calls == [] and r.made[0].cancel_calls == 0
        finally:
            await finish(r, lease)
    asyncio.run(scenario())
