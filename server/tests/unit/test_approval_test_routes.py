"""Actual AT1 routes/service with synthetic stores/ports; no native module admission."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import make_mocked_request
from multidict import CIMultiDict

from hmp_plugin import approval_test_routes as routes
from hmp_plugin import prompts, wire
from hmp_plugin.approval_test_producer import TestControlReceipt, TestOutcome, TestStatus
from hmp_plugin.request_ctx import CTX_KEY

from .hmp_kit import Env, get, pair, post, run
from .test_approval_test_authority_service import admitted, finish, rig


class Content:
    def __init__(self, raw):
        self.raw = raw

    def at_eof(self):
        return not self.raw

    async def iter_chunked(self, size):
        for start in range(0, len(self.raw), size):
            yield self.raw[start:start + size]


def request(r, method="GET", path="/approval-tests/current", body=None, headers=None,
            length="auto", profile="bot"):
    h = CIMultiDict(r.phone.headers)
    if body is not None:
        h.add("Content-Type", "application/json")
        if length is not None:
            h.add("Content-Length", str(len(body)) if length == "auto" else length)
    if headers is not None:
        for key, value in headers:
            h.add(key, value)
    req = make_mocked_request(method, path, headers=h, payload=Content(body or b""),
                              match_info={"phone_test_id": "a" * 32, "p": profile})
    req.app[CTX_KEY] = r.ctx
    r.ctx.on_identity_changed = None
    r.ctx.approval_test_service = r.service
    r.ctx.approval_test_generation = r.gen
    r.ctx.approval_test_current = lambda: r.alive[0] and r.native[0]
    return req


def decoded(response):
    assert len(response.body) <= routes.OUTPUT_CAP
    assert response.headers["Cache-Control"] == "no-store"
    return wire.parse_body(response.body)


@pytest.mark.parametrize("raw,extra,status", [
    (b'{"v":1,"choice":"once"}', [], 202),
    (b'{"v":1,"choice":"deny"}', [], 202),
    (b'{"v":1,"choice":"always"}', [], 400),
    (b'{"v":1,"choice":"session"}', [], 400),
    (b'{"v":1,"choice":"Once"}', [], 400),
    (b'{"v":1,"choice":true}', [], 400),
    (b'{"v":true,"choice":"once"}', [], 400),
    (b'{"v":1.0,"choice":"once"}', [], 400),
    (b'{"v":1,"v":1,"choice":"once"}', [], 400),
    (b'{"v":1,"choice":"once","extra":0}', [], 400),
    (b'{"v":1}', [], 400),
    (b'[]', [], 400),
    (b'{"v":1,"choice":"\xff"}', [], 400),
    (b'{"v":1,"choice":"\\ud800"}', [], 400),
    (b'{"v":1,"choice":"once"}junk', [], 400),
    (b' ' * 257, [], 413),
    (b'{"v":1,"choice":"once"}', [("Content-Type", "application/json")], 400),
    (b'{"v":1,"choice":"once"}', [("Content-Length", "25")], 400),
    (b'{"v":1,"choice":"once"}', [("Transfer-Encoding", "chunked")], 400),
    (b'{"v":1,"choice":"once"}', [("Content-Encoding", "gzip")], 400),
], ids=["once", "deny", "always", "session", "uppercase", "boolean_choice",
        "boolean_version", "float_version", "duplicate_version", "unknown_field",
        "missing_choice", "array", "invalid_utf8", "surrogate", "trailing", "oversized",
        "duplicate_type", "duplicate_length", "transfer_encoding", "content_encoding"])
def test_full_route_validation_before_control(raw, extra, status):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r, "POST", "/approval-tests/answer", raw, extra)
            req.match_info["phone_test_id"] = r.service._operation.identity.phone_test_id
            response = await routes.handle_answer(req)
            assert response.status == status
            assert decoded(response) == {"v": 1, "result": "accepted" if status == 202
                                         else "too_large" if status == 413 else "bad_request"}
            assert r.made[0].answer_calls == ([wire.parse_body(raw)["choice"]]
                                               if status == 202 else [])
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("length,raw,status", [
    (None, b'{"v":1}', 400), ("-1", b'{"v":1}', 400),
    ("seven", b'{"v":1}', 400), ("6", b'{"v":1}', 400),
    ("999999999999999999999999999", b'', 413),
    ("256", b' ' * 257, 413), ("7", b'{"v":1}', 202),
], ids=["missing_length", "negative_length", "word_length", "mismatch_length",
        "huge_length", "observed_oversized", "valid"])
def test_cancel_exact_length_and_observed_cap(length, raw, status):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r, "POST", "/approval-tests/cancel", raw, length=length)
            req.match_info["phone_test_id"] = r.service._operation.identity.phone_test_id
            response = await routes.handle_cancel(req)
            assert response.status == status
            decoded(response)
            assert r.made[0].cancel_calls == int(status == 202)
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("path,headers", [
    ("/approval-tests/current?x=1", []), ("/approval-tests/current?", []),
    ("/approval-tests/current", [("Transfer-Encoding", "chunked")]),
    ("/approval-tests/current", [("Content-Length", "1")]),
    ("/approval-tests/current", [("Content-Length", "0"), ("Content-Length", "0")]),
], ids=["query", "empty_query", "transfer_encoding", "body", "duplicate_length"])
def test_current_rejects_query_body_or_ambiguous_headers(path, headers):
    async def scenario():
        r = rig()
        try:
            response = await routes.handle_current(request(r, path=path, headers=headers))
            assert response.status == 400
            assert decoded(response) == {"v": 1, "result": "bad_request"}
            assert r.made == []
        finally:
            await r.service.shutdown()
    asyncio.run(scenario())


def test_actual_service_card_and_controls_are_separate_from_native_settlement():
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r)
            response = await routes.handle_current(req)
            card = decoded(response)["card"]
            assert card == {"test_id": r.service._operation.identity.phone_test_id,
                            "title": "Synthetic approval test", "message": "No action will run.",
                            "choices": ["once", "deny"]}
            answer = request(r, "POST", "/approval-tests/answer", b'{"v":1,"choice":"once"}')
            answer.match_info["phone_test_id"] = card["test_id"]
            assert (await routes.handle_answer(answer)).status == 202
            replay = request(r, "POST", "/approval-tests/answer", b'{"v":1,"choice":"once"}')
            replay.match_info["phone_test_id"] = card["test_id"]
            assert (await routes.handle_answer(replay)).status == 404
            assert decoded(await routes.handle_current(req)) == {"v": 1, "card": None}
            assert r.made[0].answer_calls == ["once"]
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("mutation", ["device", "family", "owner", "generation", "native"])
def test_revoked_or_stale_authority_after_real_service_await(mutation):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r)
            def mutate():
                if mutation == "device":
                    r.ctx.store.device["state"] = "REVOKED"
                elif mutation == "family":
                    r.ctx.store.family["revoked_at"] = 1
                elif mutation == "owner":
                    r.ctx.owners = frozenset()
                elif mutation == "generation":
                    r.alive[0] = False
                else:
                    r.native[0] = False
            r.gate_hook.append(mutate)
            try:
                response = await routes.handle_current(req)
            except Exception as exc:
                from hmp_plugin.contract import HmpError
                assert isinstance(exc, HmpError) and mutation in {"device", "family"}
            else:
                assert decoded(response) == {"v": 1, "card": None}
            assert r.made[0].answer_calls == []
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("profile", ["bot", "other"])
def test_ap3_exact_profile_and_ordinary_body_preservation(profile):
    """Rebound: only the separate scoped route selects the exact profile card."""
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r, path="/bots/" + profile + "/approval-tests/current", profile=profile)
            ordinary = {"prompts": [{"request_id": "ordinary", "command": "synthetic"}],
                        "desktop_held": True, "desktop_ownership": "owned"}
            before = wire.dump_json(ordinary)
            response = await routes.handle_scoped_current(req)
            body = decoded(response)
            assert set(body) == {"v", "card"} and body["v"] == 1
            assert wire.dump_json(ordinary) == before
            assert (body["card"] is not None) == (profile == "bot")
            assert r.ctx.bridge.calls >= 1
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


def test_ap3_last_await_cannot_publish_stale_card():
    """Rebound to scoped GET: a final currentness failure never publishes the card."""
    async def scenario():
        r = rig()
        req = request(r, path="/bots/bot/approval-tests/current")
        async def late(*_args, **_kwargs):
            from hmp_plugin.approval_test_service import TestCard
            await asyncio.sleep(0)
            r.alive[0] = False
            return TestCard("a" * 32)
        r.service.phone_card = late
        try:
            assert decoded(await routes.handle_scoped_current(req)) == {"v": 1, "card": None}
        finally:
            await r.service.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("margin", [0, 1, 40, 1024])
def test_ap3_combined_near_real_eight_mebibyte_boundary(tmp_path, margin):
    """Rebound: near-limit ordinary AP3 bytes remain exact; scoped DTO is independent."""
    from hmp_plugin.approval_test_service import TestCard

    from .test_approvals import _arm

    env = Env(tmp_path)
    _arm(env, flag=True)
    calls = []
    class Service:
        async def phone_card(self, _request, profile=None):
            calls.append(profile)
            return TestCard("a" * 32)
    env.ctx.approval_test_service = Service()
    env.ctx.approval_test_current = lambda: True
    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        user = env.store.get_device(dev.device_id)["user_id"]
        row = prompts.PromptRow(iid=env.iid, user_id=user, profile="bot",
                                request_id="ordinary-large", kind="approval", surface="phone_chat",
                                choices=("deny",), command="", observed_at=env.clock.now,
                                expires_at=env.clock.now + 3600)
        ordinary = {"prompts": [prompts.wire_prompt(row)], "desktop_held": False,
                    "desktop_ownership": "unknown"}
        cap = 8 * 1024 * 1024
        overhead = len(wire.dump_json(ordinary))
        row.command = "x" * (cap - overhead - margin)
        ordinary["prompts"] = [prompts.wire_prompt(row)]
        before = wire.dump_json(ordinary)
        env.ctx.prompt_store.put(row)
        response = await client.get("/hmp/v1/bots/bot/prompts", headers=env.headers(dev))
        assert response.status == 200
        raw = await response.read()
        assert raw == before and len(raw) == cap - margin
        assert "approval_test" not in wire.parse_body(raw, max_bytes=cap)
        assert calls == []
        status, body = await get(client, "/bots/bot/approval-tests/current",
                                 headers=env.headers(dev))
        assert status == 200 and body["card"]["test_id"] == "a" * 32
        assert len(wire.dump_json(body)) <= routes.OUTPUT_CAP
        assert wire.dump_json(ordinary) == before
        assert calls == ["bot"]
    try:
        run(env, scenario)
    finally:
        env.store.close()


@pytest.mark.parametrize("admission", ["duplicate", "unavailable", "untyped", "failure"])
def test_missing_or_lost_typed_receipt_never_becomes_202(admission):
    async def scenario():
        r = rig()
        req = request(r, "POST", "/approval-tests/answer", b'{"v":1,"choice":"once"}')
        async def answer(*_args):
            if admission == "failure":
                raise RuntimeError("synthetic private detail")
            if admission == "untyped":
                return SimpleNamespace(admission="accepted")
            return TestControlReceipt(admission, TestOutcome(TestStatus.PENDING))
        r.service.phone_answer = answer
        try:
            response = await routes.handle_answer(req)
            assert response.status == (503 if admission == "failure" else 404)
            assert decoded(response) == {"v": 1, "result": "unavailable"}
            assert b"synthetic private detail" not in response.body
        finally:
            await r.service.shutdown()
    asyncio.run(scenario())


def test_registered_http_current_authenticates_before_bad_query(tmp_path):
    env = Env(tmp_path)
    async def scenario(client):
        status, _ = await get(client, "/approval-tests/current?bad=1")
        assert status == 401
        dev = await pair(env, client)
        status, body = await get(client, "/approval-tests/current?bad=1", headers=env.headers(dev))
        assert status == 400 and body == {"v": 1, "result": "bad_request"}
        status, body = await get(client, "/approval-tests/current", headers=env.headers(dev))
        assert status == 200 and body == {"v": 1, "card": None}
        assert env.bridge.calls == []
    try:
        run(env, scenario)
    finally:
        env.store.close()


def test_http_ap3_preserves_ordinary_rows_and_ap4_cannot_resolve_test_alias(tmp_path):
    from hmp_plugin.approval_test_service import TestCard

    from .test_approvals import _arm

    env = Env(tmp_path)
    _arm(env, flag=True)
    calls = []
    class Service:
        async def phone_card(self, _request, profile=None):
            calls.append(profile)
            return TestCard("a" * 32) if profile == "bot" else None

        async def phone_answer(self, *_args):
            pytest.fail("ordinary AP4 must not invoke AT1")

        async def phone_cancel(self, *_args):
            pytest.fail("ordinary AP4 must not invoke AT1")
    env.ctx.approval_test_service = Service()
    env.ctx.approval_test_current = lambda: True
    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        status, body = await get(client, "/bots/bot/prompts", headers=env.headers(dev))
        assert status == 200 and body == {
            "prompts": [], "desktop_held": False, "desktop_ownership": "unknown"}
        assert calls == []
        status, body = await get(client, "/bots/bot/approval-tests/current",
                                 headers=env.headers(dev))
        assert status == 200 and body["card"]["test_id"] == "a" * 32
        assert calls == ["bot"]
        status, body = await get(client, "/bots/other/approval-tests/current",
                                 headers=env.headers(dev))
        assert status == 200 and body == {"v": 1, "card": None}
        status, body = await post(client, "/bots/bot/prompts/" + "a" * 32,
                                  {"choice": "once"}, headers=env.headers(dev))
        assert status == 404 and body["error"]["code"] == "not_found"
        assert calls == ["bot", "other"]
        assert env.ctx.prompt_store.get((env.iid, "unused", "bot", "a" * 32)) is None
    try:
        run(env, scenario)
    finally:
        env.store.close()


@pytest.mark.parametrize("length,status", [
    ("0007", 202), ("0" * 100 + "7", 202), ("000257", 413),
    ("0" * (routes.MAX_HEADER_BYTES + 1) + "7", 400),
], ids=["padded_seven", "bounded_padded_seven", "padded_oversized", "header_syntax_cap"])
def test_padded_decimal_length_has_independent_syntax_and_body_bounds(length, status):
    async def scenario():
        r = rig()
        lease, _ = await admitted(r)
        try:
            req = request(r, "POST", "/approval-tests/cancel", b'{"v":1}', length=length)
            req.match_info["phone_test_id"] = r.service._operation.identity.phone_test_id
            response = await routes.handle_cancel(req)
            assert response.status == status
            assert decoded(response) == {"v": 1, "result": "accepted" if status == 202
                                         else "too_large" if status == 413 else "bad_request"}
            assert r.made[0].cancel_calls == int(status == 202)
        finally:
            await finish(r, lease)
    asyncio.run(scenario())


@pytest.mark.parametrize("transition", ["expired", "settled"])
def test_actual_ap3_ordinary_phone_projection_is_final_after_held_at1_await(
        tmp_path, transition):
    """Rebound: ordinary expiry/settlement progresses while the separate read is held."""
    from hmp_plugin.approval_test_service import TestCard

    from .test_approvals import _arm

    env = Env(tmp_path)
    _arm(env, flag=True)
    async def scenario(client):
        dev = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        user = env.store.get_device(dev.device_id)["user_id"]
        row = prompts.PromptRow(iid=env.iid, user_id=user, profile="bot",
                                request_id="ordinary-phone", kind="clarify", surface="phone_chat",
                                choices=("Yes", "No"), question="synthetic question",
                                observed_at=env.clock.now, expires_at=env.clock.now + 10)
        env.ctx.prompt_store.put(row)
        entered = asyncio.Event()
        release = asyncio.Event()
        class Service:
            async def phone_card(self, _request, profile=None):
                assert profile == "bot"
                entered.set()
                await release.wait()
                return TestCard("a" * 32)
        env.ctx.approval_test_service = Service()
        env.ctx.approval_test_current = lambda: True
        req = make_mocked_request("GET", "/bots/bot/approval-tests/current",
                                  headers=env.headers(dev), match_info={"p": "bot"})
        req.app[CTX_KEY] = env.ctx
        task = asyncio.create_task(routes.handle_scoped_current(req))
        try:
            await entered.wait()
            status, before = await get(client, "/bots/bot/prompts", headers=env.headers(dev))
            assert status == 200
            assert [row["request_id"] for row in before["prompts"]] == ["ordinary-phone"]
            assert not task.done() and "approval_test" not in before
            if transition == "expired":
                env.clock.now += 10 + prompts.EXPIRY_GRACE_S + 1
            else:
                env.ctx.prompt_store.settle_answer(row, status="resolved",
                                                  cause="answer_accepted", now=env.clock.now)
            status, body = await get(client, "/bots/bot/prompts", headers=env.headers(dev))
            assert status == 200 and body == {
                "prompts": [], "desktop_held": False, "desktop_ownership": "unknown"}
            assert not task.done()
            release.set()
            projection = decoded(await task)
            assert projection["card"]["test_id"] == "a" * 32
        finally:
            release.set()
            if not task.done():
                await task
    try:
        run(env, scenario)
    finally:
        env.store.close()
