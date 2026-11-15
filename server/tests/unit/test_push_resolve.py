"""PN-RES real HTTP/auth/store and present-state races. No live Hermes/providers."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from hmp_plugin import prompts, wire
from hmp_plugin.contract import AuthzState, DirectSendEndpoint
from hmp_plugin.push_hints import HINT_CAP, HintBinding, HintMap

from . import test_push_registration as registrations
from .hmp_kit import code, run, url
from .test_approval_route_gates import _row, _setup
from .test_push_registration import intent, owner, request, unchanged

env = registrations.env

PATH = "/push/hints/resolve"


async def prepare(env, client, *, surface="bot_chat"):
    dev = await owner(env, client)
    calls = _setup(env)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    status, registration = await request(env, client, dev, "put", intent(env))
    assert status == 200
    row = _row(env, dev, surface=surface)
    raw = env.store._require_conn().execute("SELECT * FROM push_registrations").fetchone()
    binding = HintBinding(
        bytes(raw["route_hash"]),
        registration["generation"],
        env.ctx.prompt_store.generation,
        (row.iid, row.user_id, row.profile, row.request_id),
        env.clock.now,
    )
    hint = env.ctx.push_hints.mint(binding, now=env.clock.now, view=lambda b: view(env, b))
    return dev, row, binding, hint, calls


def view(env, binding):
    store = env.ctx.prompt_store
    if store.closed or store.generation != binding.prompt_generation:
        return None
    current = store.view_row(binding.key, now=env.clock.now, members=env.ctx.approval_members_now())
    return None if current and current.surface == "phone_chat" and store.phone_closed else current


async def resolve(env, client, dev, hint, *, body=None, headers=None):
    response = await client.post(
        url(PATH),
        data=(wire.dump_json({"v": 1, "hint": hint}) if body is None else body),
        headers=env.headers(dev) if headers is None else headers,
    )
    return response.status, await response.json()


@pytest.mark.parametrize("surface", ["bot_chat", "phone_chat"])
def test_located_only_navigation_and_read_only(env, surface):
    async def scenario(client):
        dev, row, binding, hint, calls = await prepare(env, client, surface=surface)
        before = unchanged(env), env.store._require_conn().total_changes, vars(row).copy()
        entries = dict(env.ctx.push_hints._entries)
        assert await resolve(env, client, dev, hint) == (200, {"state": "located", "profile": "b"})
        assert await resolve(env, client, dev, hint) == (200, {"state": "located", "profile": "b"})
        assert (unchanged(env), env.store._require_conn().total_changes, vars(row)) == before
        assert env.ctx.push_hints._entries == entries
        assert calls["list"] == calls["resolve"] == calls["clarify"] == calls["native"] == []
        assert len(calls["endpoint"]) == 2
        assert view(env, binding).wire is None and view(env, binding).session_key is None

    run(env, scenario)


@pytest.mark.parametrize(
    "cause",
    [*sorted(prompts.SETTLE_AUTHORITATIVE | prompts.SETTLE_NON_AUTHORITATIVE), None, "unknown"],
)
def test_only_authoritative_settlement_not_pending(env, cause):
    async def scenario(client):
        dev, row, _, hint, _ = await prepare(env, client)
        env.ctx.prompt_store.settle_answer(row, status="resolved", cause=cause, now=env.clock.now)
        status, data = await resolve(env, client, dev, hint)
        if cause in prompts.SETTLE_AUTHORITATIVE:
            assert (status, data) == (200, {"state": "not_pending"})
        else:
            assert (status, code(data)) == (404, "not_found")

    run(env, scenario)


@pytest.mark.parametrize("settled", [False, True])
def test_desktop_held_masks_open_or_authoritative_settlement(env, settled):
    async def scenario(client):
        dev, row, _, hint, _ = await prepare(env, client)
        env.ctx.prompt_store._desktop.add((row.iid, row.user_id, row.profile))
        if settled:
            env.ctx.prompt_store.settle_answer(
                row, status="resolved", cause="answer_applied", now=env.clock.now
            )
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (404, "not_found")
        env.ctx.prompt_store._desktop.clear()
        expected = {"state": "not_pending"} if settled else {"state": "located", "profile": "b"}
        assert await resolve(env, client, dev, hint) == (200, expected)

    run(env, scenario)


@pytest.mark.parametrize("delta,expected", [(59, 200), (60, 404), (61, 404)])
def test_actual_settlement_margin_and_immutable_snapshot(env, delta, expected):
    async def scenario(client):
        dev, row, binding, hint, _ = await prepare(env, client)
        frozen = view(env, binding)
        env.ctx.prompt_store.settle_answer(
            row, status="resolved", cause="answer_applied", now=env.clock.now
        )
        settled = view(env, binding)
        assert frozen.status == "open" and frozen.settled_at is None
        assert settled.settled_at == env.clock.now and settled.settle_cause == "answer_applied"
        with pytest.raises(FrozenInstanceError):
            settled.settled_at = 0
        assert "settled_at" not in prompts.wire_prompt(row)
        env.clock.now += delta
        status, data = await resolve(env, client, dev, hint)
        assert status == expected
        if status == 200:
            assert data == {"state": "not_pending"}

    run(env, scenario)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "foreign_route",
        "old_g",
        "old_prompt",
        "closed",
        "phone_closed",
        "expired_prompt",
        "evicted",
        "fence",
        "global_fence",
        "other_user",
        "other_iid",
        "retired",
        "row_iid",
        "row_h",
        "row_g",
        "row_family",
        "hash",
        "expired_registration",
        "salt",
    ],
)
def test_exact_binding_failures_masked(env, defect):
    async def scenario(client):
        dev, row, binding, hint, calls = await prepare(
            env, client, surface="phone_chat" if defect == "phone_closed" else "bot_chat"
        )
        conn = env.store._require_conn()
        if defect == "missing":
            conn.execute("DELETE FROM push_registrations")
        elif defect == "foreign_route":
            env.ctx.push_hints._entries[hint] = replace(binding, route_hash=b"x" * 32)
        elif defect == "old_g":
            env.ctx.push_hints._entries[hint] = replace(binding, generation=binding.generation + 1)
        elif defect == "old_prompt":
            env.ctx.push_hints._entries[hint] = replace(
                binding, prompt_generation=binding.prompt_generation + 1
            )
        elif defect == "closed":
            env.ctx.prompt_store.close(env.clock.now)
        elif defect == "phone_closed":
            env.ctx.prompt_store.close_phone_chat(env.clock.now)
        elif defect == "expired_prompt":
            row.expires_at = env.clock.now - 31
        elif defect == "evicted":
            env.ctx.push_hints.clear()
        elif defect == "fence":
            env.ctx.fence_push_delete(binding.route_hash)
        elif defect == "global_fence":
            env.ctx.fence_push_delete(None, unreadable=True)
        elif defect == "other_user":
            env.ctx.push_hints._entries[hint] = replace(
                binding, key=(row.iid, "foreign", row.profile, row.request_id)
            )
        elif defect == "other_iid":
            env.ctx.push_hints._entries[hint] = replace(
                binding, key=("foreign", row.user_id, row.profile, row.request_id)
            )
        elif defect == "retired":
            conn.execute("UPDATE push_registrations SET state='retired'")
        elif defect == "row_iid":
            conn.execute("UPDATE push_registrations SET iid='foreign'")
        elif defect == "row_h":
            conn.execute("UPDATE push_registrations SET host_generation=host_generation+1")
        elif defect == "row_g":
            conn.execute("UPDATE push_registrations SET generation=generation+1")
        elif defect == "row_family":
            env.store.insert_token_family("foreign", dev.device_id, env.clock.now)
            conn.execute("UPDATE push_registrations SET family_id='foreign'")
        elif defect == "hash":
            conn.execute("UPDATE push_registrations SET route_hash=?", (b"x" * 32,))
        elif defect == "salt":
            conn.execute("UPDATE push_registrations SET salt=?", (b"bad",))
        elif defect == "expired_registration":
            conn.execute("UPDATE push_registrations SET expires_at=?", (env.clock.now,))
        before = unchanged(env), vars(row).copy()
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (404, "not_found")
        assert (unchanged(env), vars(row)) == before
        assert calls["endpoint"] == []

    run(env, scenario)


@pytest.mark.parametrize("state", list(AuthzState))
def test_bot_grant_masks_err3_detail(env, state):
    async def scenario(client):
        dev, _, _, hint, calls = await prepare(env, client)
        env.bridge.authz_state = lambda *_: state
        status, data = await resolve(env, client, dev, hint)
        assert status == (200 if state is AuthzState.AUTHORIZED else 404)
        if status != 200:
            assert (
                data == {"error": {"code": "not_found", "message": "not found"}}
                and calls["endpoint"] == []
            )

    run(env, scenario)


@pytest.mark.parametrize("gate", ["direct", "bot", "phone", "endpoint", "deps"])
def test_closed_surface_gate_503_not_delivery_404(env, gate):
    async def scenario(client):
        dev, _, _, hint, _ = await prepare(
            env, client, surface="phone_chat" if gate == "phone" else "bot_chat"
        )
        if gate == "direct":
            env.ctx.direct_send_flag = lambda: False
        if gate == "bot":
            env.ctx.approvals_available = lambda: False
        if gate == "phone":
            env.ctx.phone_chat_available = lambda: False
        if gate == "endpoint":
            env.bridge.direct_send_endpoint = lambda *_: None
        if gate == "deps":
            env.ctx.direct_send_deps = None
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (503, "write_gate_closed")

    run(env, scenario)


@pytest.mark.parametrize(
    "settings", [None, {}, {"enabled": False}, {"enabled": 1}, {"enabled": "true"}]
)
def test_literal_push_flag_required(env, settings):
    async def scenario(client):
        dev, _, _, hint, calls = await prepare(env, client)
        env.ctx.push_settings = lambda: settings
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (404, "not_found") and calls["endpoint"] == []

    run(env, scenario)


def test_bad_relay_or_removed_kid_is_not_resolver_gate(env):
    async def scenario(client):
        dev, _, _, hint, _ = await prepare(env, client)
        env.ctx.push_settings = lambda: {"enabled": True}
        assert await resolve(env, client, dev, hint) == (200, {"state": "located", "profile": "b"})

    run(env, scenario)


@pytest.mark.parametrize(
    "body",
    [
        b'{"v":true,"hint":"abcdefghijklmnopqrstuv"}',
        b'{"v":1,"hint":"bad"}',
        b'{"v":1,"hint":"abcdefghijklmnopqrstuv="}',
        b'{"v":1,"hint":"!!!!!!!!!!!!!!!!!!!!!!"}',
        b'{"v":1,"hint":"AA","route":"x"}',
        b'{"v":1,"hint":"AA","extra":null}',
        b'{"v":1,"v":1,"hint":"AA"}',
        b'{"v":1,"hint":null}',
        rb'{"v":1,"hint":"\uD800"}',
    ],
)
def test_closed_body_and_canonical_grammar(env, body):
    async def scenario(client):
        dev = await owner(env, client)
        env.ctx.push_settings = lambda: None
        status, data = await resolve(env, client, dev, "", body=body)
        assert (status, code(data)) == (400, "bad_request")

    run(env, scenario)


def test_resolve_rate_is_30_and_separate_from_registration(env):
    async def scenario(client):
        dev, _, _, hint, _ = await prepare(env, client)
        for _ in range(30):
            assert (await resolve(env, client, dev, hint))[0] == 200
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (429, "rate_limited")
        assert (await request(env, client, dev, "get"))[0] == 200
        env.clock.now += 60
        assert (await resolve(env, client, dev, hint))[0] == 200

    run(env, scenario)


@pytest.mark.parametrize("edge", ["key", "grant", "gate", "final_grant"])
@pytest.mark.parametrize(
    "change", ["owner", "grant", "fence", "closed", "held", "direct", "settle"]
)
def test_rechecks_each_async_edge(env, edge, change):
    async def scenario(client):
        dev, row, binding, hint, _ = await prepare(env, client)
        fired = False

        def alter():
            nonlocal fired
            if fired:
                return
            fired = True
            if change == "owner":
                env.ctx.owner_device_ids = lambda: frozenset()
            if change == "grant":
                env.bridge.authz_state = lambda *_: AuthzState.UNVERIFIABLE
            if change == "fence":
                env.ctx.fence_push_delete(binding.route_hash)
            if change == "closed":
                env.ctx.prompt_store.close(env.clock.now)
            if change == "held":
                env.ctx.prompt_store._desktop.add((row.iid, row.user_id, row.profile))
            if change == "direct":
                env.ctx.direct_send_flag = lambda: False
            if change == "settle":
                env.ctx.prompt_store.settle_answer(
                    row, status="resolved", cause="answer_applied", now=env.clock.now
                )

        if edge == "key":
            original = env.identity.read_k_grace_for_push

            async def key():
                value = await original()
                alter()
                return value

            env.identity.read_k_grace_for_push = key
        elif edge in ("grant", "final_grant"):
            n = 0

            def grant(*_):
                nonlocal n
                n += 1
                if n == (1 if edge == "grant" else 2):
                    alter()
                return AuthzState.AUTHORIZED

            env.bridge.authz_state = grant
        else:

            def endpoint(*_):
                alter()
                return DirectSendEndpoint(
                    host="127.0.0.1", port=9, api_key="k" * 20, path_prefix=""
                )

            env.bridge.direct_send_endpoint = endpoint
        status, data = await resolve(env, client, dev, hint)
        assert fired
        expected = 200 if change == "settle" else 503 if change == "direct" else 404
        assert status == expected, (edge, change, data)
        if change == "settle":
            assert data == {"state": "not_pending"}

    run(env, scenario)


def test_hint_capacity_collision_eviction_and_hard_lifetime(env, monkeypatch):
    store = prompts.PromptStore(clock=env.clock)
    row = prompts.PromptRow(env.iid, "user", "b", "request", "approval", "bot_chat", ("deny",))
    store.put(row)
    key = (row.iid, row.user_id, row.profile, row.request_id)

    def get(b):
        return store.view_row(b.key, now=env.clock.now, members=prompts.ALL_OPEN)

    m = HintMap()
    binding = HintBinding(b"h" * 32, 1, store.generation, key, env.clock.now)
    first = m.mint(binding, now=env.clock.now, view=get)
    for _ in range(HINT_CAP - 1):
        m.mint(binding, now=env.clock.now, view=get)
    assert len(m) == 256
    m.mint(binding, now=env.clock.now, view=get)
    assert len(m) == 256 and m.lookup(first, now=env.clock.now) is None
    saved = next(iter(m._entries))
    from hmp_plugin import crypto

    original = crypto.random_bytes
    values = iter([wire.b64u_decode(saved, length=32), original(32)])
    monkeypatch.setattr(crypto, "random_bytes", lambda _: next(values))
    # Make the live colliding entry newest so overflow cannot evict it first.
    existing = m._entries.pop(saved)
    m._entries[saved] = existing
    minted = m.mint(binding, now=env.clock.now, view=get)
    assert minted != saved and saved in m._entries
    before = dict(m._entries)
    assert m.lookup(minted, now=env.clock.now + 3600) is None
    assert m._entries == before
    m.clear()
    assert len(m) == 0


@pytest.mark.parametrize("reason", ["unlisted", "controls_only", "denied"])
def test_owner_precedes_body_and_key(env, reason):
    async def scenario(client):
        dev = await owner(env, client)
        if reason == "unlisted":
            env.ctx.owner_device_ids = lambda: frozenset()
        elif reason == "controls_only":
            env.ctx.owner_device_ids = lambda: frozenset()
            env.store.set_owner_controls(dev.device_id, allowed=True, now=env.clock.now)
        else:
            env.store.set_owner_controls(dev.device_id, allowed=False, now=env.clock.now)

        async def forbidden():
            raise AssertionError("nonowner touched push key")

        env.identity.read_k_grace_for_push = forbidden
        status, data = await resolve(env, client, dev, "", body=b"not json")
        assert (status, code(data)) == (404, "not_found")

    run(env, scenario)


@pytest.mark.parametrize("key", [None, b"x" * 31, b"x" * 32])
def test_lost_or_changed_key_is_unable_to_check(env, key):
    async def scenario(client):
        dev, row, _, hint, calls = await prepare(env, client)

        async def read():
            return key

        env.identity.read_k_grace_for_push = read
        before = unchanged(env), vars(row).copy()
        status, data = await resolve(env, client, dev, hint)
        assert (status, code(data)) == (404, "not_found")
        assert (unchanged(env), vars(row)) == before and calls["endpoint"] == []

    run(env, scenario)


def test_hint_eviction_prefers_settled_over_older_open(env):
    store = prompts.PromptStore(clock=env.clock)
    row = prompts.PromptRow(env.iid, "user", "b", "open", "approval", "bot_chat", ("deny",))
    settled = replace(row, request_id="settled")
    store.put(row)
    store.put(settled)

    def get(binding):
        return store.view_row(binding.key, now=env.clock.now, members=prompts.ALL_OPEN)

    m = HintMap()
    b = HintBinding(
        b"h" * 32,
        1,
        store.generation,
        (row.iid, row.user_id, row.profile, row.request_id),
        env.clock.now,
    )
    first = m.mint(b, now=env.clock.now, view=get)
    for _ in range(HINT_CAP - 2):
        m.mint(b, now=env.clock.now, view=get)
    newest = m.mint(
        replace(b, key=(row.iid, row.user_id, row.profile, settled.request_id)),
        now=env.clock.now,
        view=get,
    )
    store.settle_answer(settled, status="resolved", cause="answer_applied", now=env.clock.now)
    m.mint(b, now=env.clock.now, view=get)
    assert len(m) == 256 and m.lookup(first, now=env.clock.now) is not None
    assert m.lookup(newest, now=env.clock.now) is None


def test_other_paired_owner_cannot_resolve_first_owners_hint(env):
    async def scenario(client):
        first, _, _, hint, calls = await prepare(env, client)
        second = await owner(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({first.device_id, second.device_id})
        status, _ = await request(env, client, second, "put", intent(env, number=2))
        assert status == 200
        status, data = await resolve(env, client, second, hint)
        assert (status, code(data)) == (404, "not_found")
        assert calls["endpoint"] == []

    run(env, scenario)
