"""Real prompt insertion/store/recipient fences with virtual time and a fake relay.

No provider/native authority or HTTP/signing evidence is inferred from this port.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from dataclasses import replace

import pytest

from hmp_plugin import identity, prompts, server, wire
from hmp_plugin.contract import REFRESH_ABSOLUTE_TTL_S, AuthzState
from hmp_plugin.push_dispatch import (
    COUNTER_CAP,
    HOURLY_CAP,
    QUEUE_CAP,
    SLOT_CAP,
    Counter,
    Event,
    PushDispatcher,
    Slot,
    ttl_s,
)

from . import test_push_registration as registrations
from .hmp_kit import run
from .test_approval_route_gates import _row, _setup
from .test_push_registration import intent, owner, request
from .test_push_store import seed_row

env = registrations.env


class Clock:
    def __init__(self, env):
        self.env, self.now = env, 100.0
        self.waiters = []

    async def sleep(self, delay):
        future = asyncio.get_running_loop().create_future()
        self.waiters.append((self.now + delay, future))
        await future

    def advance(self, seconds):
        self.now += seconds
        self.env.clock.now += int(seconds)
        for until, future in self.waiters:
            if until <= self.now and not future.done():
                future.set_result(None)


class Relay:
    def __init__(self, *results):
        self.calls, self.results = [], list(results)
        self.closed, self.hold, self.active, self.maximum = False, None, 0, 0
        self.on_send = lambda _: None

    async def send(self, attempt):
        self.calls.append(attempt)
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            self.on_send(attempt)
            if self.hold is not None:
                await self.hold.wait()
            return self.results.pop(0) if self.results else "accepted"
        finally:
            self.active -= 1

    async def close(self):
        self.closed = True


async def until(predicate):
    async with asyncio.timeout(3):
        while not predicate():  # noqa: ASYNC110 - bounded observation of loop/thread completion
            await asyncio.sleep(0.005)


def event(row, generation):
    return prompts.ApprovalInserted(
        (row.iid, row.user_id, row.profile, row.request_id), row.surface, generation, row.expires_at
    )


async def prepare(env, client, *, surface="bot_chat", relay=None):
    dev = await owner(env, client)
    calls = _setup(env)
    env.bridge.authz_state = lambda *_: AuthzState.AUTHORIZED
    status, registration = await request(env, client, dev, "put", intent(env))
    assert status == 200
    row = _row(env, dev, surface=surface)
    clock, relay = Clock(env), relay or Relay()
    dispatcher = PushDispatcher(
        env.ctx,
        relay,
        require_gate=server._require_approvals_gate,
        monotonic=lambda: clock.now,
        sleep=clock.sleep,
        jitter=lambda: 0.5,
    )
    dispatcher.start()
    return dev, row, clock, relay, dispatcher, registration, calls


async def idle(dispatcher):
    await dispatcher.queue.join()
    await until(lambda: all(s.task is None for s in dispatcher.slots.values()))


@pytest.mark.parametrize("surface", ["bot_chat", "phone_chat"])
def test_real_insertion_mints_resolvable_hint_without_native_answers(env, surface):
    async def scenario(client):
        dev, _, _, relay, dispatcher, _, calls = await prepare(env, client, surface=surface)
        try:
            row = _row(env, dev, surface=surface, request_id="new-approval")
            await until(lambda: len(relay.calls) == 1)
            await idle(dispatcher)
            attempt = relay.calls[0]
            hint = wire.b64u_encode(attempt.hint)
            binding = env.ctx.push_hints.lookup(hint, now=env.clock.now)
            assert binding.key == (row.iid, row.user_id, row.profile, row.request_id)
            assert attempt.ttl_s == 330 and len(attempt.route) == 32 and len(attempt.collapse) == 24
            assert attempt.kid == "kid-a" and attempt.sealed == b"s" * 82
            assert env.store.push_dispatch_device_snapshot(dev.device_id)["state"] == "active"
            assert calls["list"] == calls["resolve"] == calls["clarify"] == calls["native"] == []
        finally:
            await dispatcher.close()
        assert relay.closed and not len(env.ctx.push_hints)

    run(env, scenario)


@pytest.mark.parametrize(
    "defect",
    [
        "clarify",
        "closed",
        "old_generation",
        "phone_closed",
        "held",
        "expired_row",
        "expired_queue",
        "flag",
        "member",
        "direct",
        "relay",
        "identity",
        "owner",
        "denied",
        "revoked",
        "family_revoked",
        "family_old",
        "wrong_user",
        "iid",
        "h",
        "g",
        "registration_expired",
        "kid",
        "hash",
        "fence",
        "global_fence",
        "grant",
        "endpoint",
    ],
)
def test_no_request_for_current_ineligible_row_or_recipient(env, defect):
    async def scenario(client):
        surface = "phone_chat" if defect == "phone_closed" else "bot_chat"
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client, surface=surface)
        conn = env.store._require_conn()
        inserted = event(row, env.ctx.prompt_store.generation)
        try:
            if defect == "clarify":
                row.kind = "clarify"
            elif defect == "closed":
                env.ctx.prompt_store.close(env.clock.now)
            elif defect == "old_generation":
                inserted = replace(inserted, generation=inserted.generation + 1)
            elif defect == "phone_closed":
                env.ctx.prompt_store.close_phone_chat(env.clock.now)
            elif defect == "held":
                env.ctx.prompt_store._desktop.add((row.iid, row.user_id, row.profile))
            elif defect == "expired_row":
                clock.advance(331)
            elif defect == "flag":
                env.ctx.push_settings = lambda: {"enabled": False}
            elif defect == "member":
                env.ctx.approvals_available = lambda: False
            elif defect == "direct":
                env.ctx.direct_send_flag = lambda: False
            elif defect == "relay":
                env.ctx.push_settings = lambda: {"enabled": True, "relay_url": "http://invalid"}
            elif defect == "identity":
                env.identity.still_current = lambda: False
            elif defect == "owner":
                env.ctx.owner_device_ids = lambda: frozenset()
            elif defect == "denied":
                env.store.set_owner_controls(dev.device_id, allowed=False, now=env.clock.now)
            elif defect == "revoked":
                conn.execute("UPDATE devices SET state='REVOKED'")
            elif defect == "family_revoked":
                conn.execute("UPDATE token_families SET revoked_at=1")
                # A different live family must not rescue this registration's
                # revoked issuing family.
                env.store.insert_token_family("other-live-family", dev.device_id, env.clock.now)
            elif defect == "family_old":
                conn.execute(
                    "UPDATE token_families SET created_at=?",
                    (env.clock.now - REFRESH_ABSOLUTE_TTL_S,),
                )
            elif defect == "wrong_user":
                env.store.insert_user("other-user", "test", 1)
                conn.execute("UPDATE devices SET user_id='other-user'")
            elif defect == "iid":
                conn.execute("UPDATE push_registrations SET iid='foreign'")
            elif defect == "h":
                conn.execute("UPDATE meta SET store_revocation_epoch=store_revocation_epoch+1")
            elif defect == "g":
                conn.execute("UPDATE push_device_generations SET generation=generation+1")
            elif defect == "registration_expired":
                conn.execute("UPDATE push_registrations SET expires_at=?", (env.clock.now,))
            elif defect == "kid":
                conn.execute("UPDATE push_registrations SET relay_kid='removed'")
            elif defect == "hash":
                conn.execute("UPDATE push_registrations SET salt=?", (b"x" * 32,))
            elif defect == "fence":
                digest = bytes(
                    conn.execute("SELECT route_hash FROM push_registrations").fetchone()[0]
                )
                env.ctx.fence_push_delete(digest)
            elif defect == "global_fence":
                env.ctx.fence_push_delete(None, unreadable=True)
            elif defect == "grant":
                env.bridge.authz_state = lambda *_: AuthzState.NOT_AUTHORIZED
            elif defect == "endpoint":
                env.bridge.direct_send_endpoint = lambda *_: None
            await dispatcher.dispatch(
                Event(inserted, clock.now - 1 if defect == "expired_queue" else clock.now + 330)
            )
            await idle(dispatcher)
            assert relay.calls == []
            env.ctx.prompt_store._desktop.clear()
            await asyncio.sleep(0.01)
            assert relay.calls == []  # becoming visible is not a redispatch trigger
        finally:
            await dispatcher.close()

    run(env, scenario)


@pytest.mark.parametrize("stage", ["key", "grant", "gate", "last_grant"])
@pytest.mark.parametrize("defect", ["held", "owner", "fence", "settled", "generation", "flag"])
def test_rechecks_after_each_async_boundary(env, monkeypatch, stage, defect):
    async def scenario(client):
        _, row, clock, relay, dispatcher, _, _ = await prepare(env, client)
        digest = bytes(
            env.store._require_conn()
            .execute("SELECT route_hash FROM push_registrations")
            .fetchone()[0]
        )

        def change():
            if defect == "held":
                env.ctx.prompt_store._desktop.add((row.iid, row.user_id, row.profile))
            elif defect == "owner":
                env.ctx.owner_device_ids = lambda: frozenset()
            elif defect == "fence":
                env.ctx.fence_push_delete(digest)
            elif defect == "settled":
                env.ctx.prompt_store.settle_answer(
                    row, status="resolved", cause="answer_applied", now=env.clock.now
                )
            elif defect == "generation":
                env.ctx.prompt_store.close(env.clock.now)
            else:
                env.ctx.push_settings = lambda: {"enabled": False}

        original_key = env.identity.read_k_grace_for_push
        count = 0

        async def key():
            nonlocal count
            value = await original_key()
            count += 1
            if stage == "key" and count == 2:  # dequeue mint read, then pre-send read
                change()
            return value

        monkeypatch.setattr(env.identity, "read_k_grace_for_push", key)
        grants = 0

        def grant(*_):
            nonlocal grants
            grants += 1
            if (stage == "grant" and grants == 1) or (stage == "last_grant" and grants == 2):
                # Changes are applied on the listener loop, not a test SQL write thread.
                dispatcher.loop.call_soon_threadsafe(change)
            return AuthzState.AUTHORIZED

        env.bridge.authz_state = grant
        real_gate = dispatcher.require_gate

        async def gate(*args, **kwargs):
            value = await real_gate(*args, **kwargs)
            if stage == "gate":
                change()
            return value

        dispatcher.require_gate = gate
        try:
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await idle(dispatcher)
            assert relay.calls == []
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_coalescing_uses_only_newest_hint_after_window(env):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client)
        try:
            dispatcher.observe(event(row, dispatcher.store.generation))
            await until(lambda: len(relay.calls) == 1)
            await idle(dispatcher)
            for name in ("second", "third"):
                _row(env, dev, surface="bot_chat", request_id=name)
                await dispatcher.queue.join()
            await until(lambda: bool(clock.waiters))
            assert len(relay.calls) == 1
            clock.advance(9)
            await asyncio.sleep(0.01)
            assert len(relay.calls) == 1
            clock.advance(1)
            await until(lambda: len(relay.calls) == 2)
            await idle(dispatcher)
            binding = env.ctx.push_hints.lookup(
                wire.b64u_encode(relay.calls[-1].hint), now=env.clock.now
            )
            assert binding.key[-1] == "third"
            assert relay.calls[0].collapse == relay.calls[-1].collapse
            assert relay.calls[0].hint != relay.calls[-1].hint
        finally:
            await dispatcher.close()

    run(env, scenario)


@pytest.mark.parametrize(
    "result",
    [
        "accepted",
        "postwrite_timeout",
        "provider_unavailable",
        "provider_gone",
        "sealed_invalid",
        "replayed",
        "rate_limited",
        "bad_request",
        "unauthorized",
        "ambiguous",
        "unknown",
    ],
)
def test_nonretry_results_and_exact_feedback(env, result):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client, relay=Relay(result))
        try:
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await idle(dispatcher)
            assert len(relay.calls) == 1 and not clock.waiters
            snap = env.store.push_status_snapshot(dev.device_id)
            if result in ("provider_gone", "sealed_invalid"):
                assert snap[0] == 2 and snap[2]["state"] == (
                    "provider_gone" if result == "provider_gone" else "expired"
                )
                assert snap[2]["sealed"] is None
            else:
                assert snap[0] == 1 and snap[2]["state"] == "active"
        finally:
            await dispatcher.close()

    run(env, scenario)


@pytest.mark.parametrize("result", ["prewrite_failure", "unavailable"])
def test_two_retries_fresh_nonce_time_same_hint_collapse_then_breaker(env, result):
    async def scenario(client):
        _, row, clock, relay, dispatcher, _, _ = await prepare(
            env, client, relay=Relay(result, result, result)
        )
        try:
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await until(lambda: len(relay.calls) == 1 and len(clock.waiters) == 1)
            clock.advance(1)
            await until(lambda: len(relay.calls) == 2 and len(clock.waiters) == 2)
            clock.advance(4)
            await idle(dispatcher)
            assert len(relay.calls) == 3 and dispatcher.open_until == clock.now + 60
            assert (
                len({a.nonce for a in relay.calls}) == 3 and len({a.ts for a in relay.calls}) == 3
            )
            assert len({a.hint for a in relay.calls}) == len({a.collapse for a in relay.calls}) == 1
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            assert len(relay.calls) == 3
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_late_feedback_cas_does_not_retire_new_registration(env):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, first, _ = await prepare(
            env, client, relay=Relay("provider_gone")
        )

        family_id = env.store.push_dispatch_device_snapshot(dev.device_id)["family_id"]
        key = env.identity.k_grace()

        def replace_registration(_):
            with env.store.transaction() as conn:
                env.store.replace_push_in(
                    conn,
                    device_id=dev.device_id,
                    family_id=family_id,
                    iid=env.iid,
                    key=key,
                    body=intent(env, first["generation"], number=2),
                    sealed=b"t" * 82,
                    request_hash=b"q" * 32,
                    body_hash=b"b" * 32,
                    now=env.clock.now,
                )

        relay.on_send = replace_registration
        try:
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await idle(dispatcher)
            snap = env.store.push_status_snapshot(dev.device_id)
            assert len(relay.calls) == 1 and snap[0] == 2 and snap[2]["state"] == "active"
            assert snap[2]["sealed"] == b"t" * 82
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_thread_handoff_and_queue_scheduled_callback_bound(env, monkeypatch):
    async def scenario(client):
        _, row, _, relay, dispatcher, _, _ = await prepare(env, client)
        callbacks = []
        real = dispatcher.loop.call_soon_threadsafe

        def schedule(fn, *args, **kwargs):
            if fn == dispatcher._enqueue:
                callbacks.append((fn, args))
                return None
            return real(fn, *args, **kwargs)

        monkeypatch.setattr(dispatcher.loop, "call_soon_threadsafe", schedule)
        inserted = event(row, dispatcher.store.generation)
        try:
            thread = threading.Thread(
                target=lambda: [dispatcher.observe(inserted) for _ in range(QUEUE_CAP + 10)]
            )
            thread.start()
            thread.join()
            assert len(callbacks) == QUEUE_CAP and dispatcher.queue.qsize() == 0
            for fn, args in callbacks:
                fn(*args)
            assert dispatcher.queue.qsize() == QUEUE_CAP
            await until(lambda: bool(relay.calls))
        finally:
            await dispatcher.close()

    run(env, scenario)


@pytest.mark.parametrize("failure", ["enqueue", "thread_schedule", "log_sink"])
def test_producer_failure_isolation_restores_bounded_reservations(env, monkeypatch, failure):
    async def scenario(client):
        dev, prior_row, _, relay, dispatcher, _, _ = await prepare(env, client)

        def fail(*args, **kwargs):
            raise RuntimeError("private producer error")

        if failure == "enqueue":
            monkeypatch.setattr(dispatcher.queue, "put_nowait", fail)
        elif failure == "log_sink":
            from hmp_plugin import push_dispatch

            monkeypatch.setattr(dispatcher.queue, "put_nowait", fail)
            monkeypatch.setattr(push_dispatch, "log_event", fail)
        else:
            real = dispatcher.loop.call_soon_threadsafe

            def schedule(fn, *args, **kwargs):
                if fn == dispatcher._enqueue:
                    fail()
                return real(fn, *args, **kwargs)

            monkeypatch.setattr(dispatcher.loop, "call_soon_threadsafe", schedule)
        try:
            if failure == "thread_schedule":
                inserted = []
                thread = threading.Thread(
                    target=lambda: inserted.append(
                        _row(env, dev, surface="phone_chat", request_id="producer-failed")
                    )
                )
                thread.start()
                thread.join()
                assert len(inserted) == 1
            else:
                _row(env, dev, surface="bot_chat", request_id="producer-failed")
            assert (
                env.ctx.prompt_store.get(
                    (env.iid, prior_row.user_id, prior_row.profile, "producer-failed")
                )
                is not None
            )
            assert not relay.calls and dispatcher.queue.empty()
            for _ in range(QUEUE_CAP):
                assert dispatcher._capacity.acquire(blocking=False)
            assert not dispatcher._capacity.acquire(blocking=False)
            for _ in range(QUEUE_CAP):
                dispatcher._capacity.release()
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_close_is_bounded_and_consumes_late_client_close_failure(env):
    async def scenario(client):
        _, _, _, relay, dispatcher, _, _ = await prepare(env, client)
        release = asyncio.Event()
        finished = asyncio.Event()
        errors = []
        loop = asyncio.get_running_loop()
        prior_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _, context: errors.append(context))

        async def resistant_close():
            while not release.is_set():
                with contextlib.suppress(asyncio.CancelledError):
                    await release.wait()
            finished.set()
            raise RuntimeError("private late client close text")

        relay.close = resistant_close
        try:
            before = loop.time()
            await dispatcher.close()
            assert loop.time() - before < 1.1 and dispatcher.closed
            release.set()
            await finished.wait()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not errors
        finally:
            release.set()
            loop.set_exception_handler(prior_handler)

    run(env, scenario)


def test_off_loop_key_read_and_hung_relay_listener_close_bound(env, monkeypatch):
    threads = []
    reader = identity._read_k_grace_for_push
    monkeypatch.setattr(
        identity,
        "_read_k_grace_for_push",
        lambda path: (threads.append(threading.get_ident()), reader(path))[1],
    )

    async def scenario(client):
        _, row, _, relay, dispatcher, _, _ = await prepare(env, client)
        relay.hold = asyncio.Event()
        dispatcher.observe(event(row, dispatcher.store.generation))
        await until(lambda: relay.active == 1)
        start = asyncio.get_running_loop().time()
        await dispatcher.close()
        assert asyncio.get_running_loop().time() - start < 1.1
        assert relay.closed and relay.active == 0 and all(t.done() for t in dispatcher.workers)
        assert threads and all(t != threading.get_ident() for t in threads)

    run(env, scenario)


@pytest.mark.parametrize(
    "estimate,expected", [(None, 330), (-1000, 60), (0, 60), (100, 130), (1000, 900)]
)
def test_ttl_bounds(estimate, expected):
    assert ttl_s(estimate, 0) == expected


@pytest.mark.parametrize("timestamps", ["distinct", "tied", "backward"])
def test_recipient_order_cap_and_two_inflight_requests(env, timestamps):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client)
        hashes = []
        owners = {dev.device_id}
        for n in range(7):
            name = f"recipient-{n}"
            env.store.insert_device(
                name, row.user_id, "fp", b"pub", "phone", env.clock.now, state="ACTIVE"
            )
            env.store.insert_token_family(f"family-{name}", name, env.clock.now)
            digest = seed_row(
                env.store,
                name,
                iid=env.iid,
                key=env.identity.k_grace(),
                host_generation=env.store.revocation_epoch(),
                expires=env.clock.now + 7200,
            )
            env.store._require_conn().execute(
                "UPDATE push_registrations SET created_at=? WHERE route_hash=?",
                (
                    env.clock.now + n + 1
                    if timestamps == "distinct"
                    else env.clock.now
                    if timestamps == "tied"
                    else env.clock.now - n,
                    digest,
                ),
            )
            hashes.append(digest)
            owners.add(name)
        env.ctx.owner_device_ids = lambda: frozenset(owners)
        env.store.set_owner_controls("recipient-6", allowed=False, now=env.clock.now)
        relay.hold = asyncio.Event()
        try:
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await until(lambda: len(relay.calls) == 2)
            assert relay.maximum == 2
            relay.hold.set()
            await idle(dispatcher)
            import hashlib

            assert {hashlib.sha256(a.route).digest() for a in relay.calls} == set(hashes[2:6])
            assert len(relay.calls) == 4 and relay.maximum == 2
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_candidate_recency_survives_replacement_and_highest_rowid_deletion(env):
    async def scenario(client):
        dev, row, _, _, dispatcher, _, _ = await prepare(env, client)
        try:
            conn = env.store._require_conn()
            family = env.store.push_dispatch_device_snapshot(dev.device_id)["family_id"]
            for n in range(2):
                name = f"order-{n}"
                env.store.insert_device(
                    name, row.user_id, "fp", b"pub", "phone", env.clock.now, state="ACTIVE"
                )
                env.store.insert_token_family(f"family-{name}", name, env.clock.now)
                seed_row(env.store, name, iid=env.iid, key=env.identity.k_grace())
            assert [r["device_id"] for r in env.store.push_dispatch_candidates(row.user_id)] == [
                "order-1",
                "order-0",
                dev.device_id,
            ]
            # Delete the highest row. Its implicit rowid can be reused, but it
            # still sorts above all surviving candidates after the replacement.
            conn.execute("DELETE FROM push_registrations WHERE device_id='order-1'")
            with env.store.transaction() as tx:
                env.store.replace_push_in(
                    tx,
                    device_id=dev.device_id,
                    family_id=family,
                    iid=env.iid,
                    key=env.identity.k_grace(),
                    body=intent(env, 1, number=2),
                    sealed=b"t" * 82,
                    request_hash=b"q" * 32,
                    body_hash=b"b" * 32,
                    now=env.clock.now - 100,
                )
            assert [r["device_id"] for r in env.store.push_dispatch_candidates(row.user_id)] == [
                dev.device_id,
                "order-0",
            ]
            # Purging retired rows cannot reorder the two remaining active rows.
            conn.execute("DELETE FROM push_registrations WHERE state='retired'")
            assert [r["device_id"] for r in env.store.push_dispatch_candidates(row.user_id)] == [
                dev.device_id,
                "order-0",
            ]
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_hourly_counter_survives_replacement_and_idle_slot_eviction(env):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client)
        try:
            for _ in range(HOURLY_CAP):
                assert dispatcher._charge(dev.device_id)
            assert not dispatcher._charge(dev.device_id)
            status, _ = await request(env, client, dev, "put", intent(env, 1, number=2))
            assert status == 200
            for n in range(SLOT_CAP):
                dispatcher.slots[(n.to_bytes(32, "big"), 1, "profile")] = Slot(last_send=clock.now)
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            await idle(dispatcher)
            assert len(dispatcher.slots) == SLOT_CAP and relay.calls == []
            assert dispatcher.counters[dev.device_id].count == HOURLY_CAP
            clock.advance(3600)
            assert (
                dispatcher._charge(dev.device_id) and dispatcher.counters[dev.device_id].count == 1
            )
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_full_counter_and_all_pending_slot_tables_refuse_without_eviction(env, monkeypatch):
    async def scenario(client):
        dev, row, clock, relay, dispatcher, _, _ = await prepare(env, client)
        try:
            for n in range(COUNTER_CAP):
                dispatcher.counters[str(n)] = Counter(clock.now, 1)
            monkeypatch.setattr(env.store, "push_counter_state", lambda _: ("ACTIVE", True))
            assert not dispatcher._charge(dev.device_id) and len(dispatcher.counters) == COUNTER_CAP
            for n in range(SLOT_CAP):
                dispatcher.slots[(n.to_bytes(32, "big"), 1, "profile")] = Slot(pending=object())
            before = dict(dispatcher.slots)
            await dispatcher.dispatch(
                Event(event(row, dispatcher.store.generation), clock.now + 330)
            )
            assert dict(dispatcher.slots) == before and relay.calls == []
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_half_open_probe_is_exclusive_even_when_old_request_completes(env):
    async def scenario(client):
        _, _, clock, _, dispatcher, _, _ = await prepare(env, client)
        try:
            for _ in range(3):
                dispatcher._breaker_result("postwrite_timeout", probe=False)
            assert dispatcher._breaker_enter() == (False, False)
            clock.advance(60)
            assert dispatcher._breaker_enter() == (True, True)
            dispatcher._breaker_result("accepted", probe=False)
            assert dispatcher._breaker_enter() == (False, False)
            dispatcher._breaker_result("accepted", probe=True)
            assert dispatcher._breaker_enter() == (True, False)
        finally:
            await dispatcher.close()

    run(env, scenario)


@pytest.mark.parametrize("change", ["ttl", "held", "owner", "fence", "kid"])
def test_retry_drops_when_ttl_expires_or_visibility_lost_during_backoff(env, change):
    async def scenario(client):
        _, row, clock, relay, dispatcher, _, _ = await prepare(
            env, client, relay=Relay("unavailable")
        )
        try:
            deadline = clock.now + (2 if change == "ttl" else 330)
            await dispatcher.dispatch(Event(event(row, dispatcher.store.generation), deadline))
            await until(lambda: len(clock.waiters) == 1)
            if change == "held":
                env.ctx.prompt_store._desktop.add((row.iid, row.user_id, row.profile))
            elif change == "owner":
                env.ctx.owner_device_ids = lambda: frozenset()
            elif change == "fence":
                env.ctx.fence_push_delete(None, unreadable=True)
            elif change == "kid":
                env.store._require_conn().execute(
                    "UPDATE push_registrations SET relay_kid='removed'"
                )
            clock.advance(2)
            await idle(dispatcher)
            assert len(relay.calls) == 1
        finally:
            await dispatcher.close()

    run(env, scenario)


def test_real_listener_owns_insertion_worker_and_cancels_hung_request(env):
    async def scenario(client):
        dev, _, _, _, prior, _, _ = await prepare(env, client)
        await prior.close()
        relay = Relay()
        relay.hold = asyncio.Event()
        srv = server.HmpServer(
            env.ctx, server.ListenerSettings("127.0.0.1", 0), push_relay_factory=lambda: relay
        )
        try:
            await srv.start()
            dispatcher = srv._push_dispatcher
            assert dispatcher is not None and len(dispatcher.workers) == 2
            _row(env, dev, surface="bot_chat", request_id="live-listener-approval")
            await until(lambda: relay.active == 1)
            before = asyncio.get_running_loop().time()
            await srv.stop(notify=False)
            assert asyncio.get_running_loop().time() - before < 1.1
            assert dispatcher.closed and relay.closed and relay.active == 0
            assert not len(env.ctx.push_hints)
            assert all(task.done() for task in dispatcher.workers)
        finally:
            await srv.stop(notify=False)

    run(env, scenario)


@pytest.mark.parametrize("creation", ["factory", "constructor", "workers"])
def test_dispatcher_creation_failure_keeps_real_tls_listener_and_routes(env, monkeypatch, creation):
    async def scenario(client):
        _setup(env)
        relay = Relay()

        def factory():
            if creation == "factory":
                raise RuntimeError("sensitive relay text")
            return relay

        if creation == "constructor":
            monkeypatch.setattr(
                server,
                "PushDispatcher",
                lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sensitive")),
            )
        if creation == "workers":
            monkeypatch.setattr(
                PushDispatcher, "start", lambda _: (_ for _ in ()).throw(RuntimeError("sensitive"))
            )
        srv = server.HmpServer(
            env.ctx, server.ListenerSettings("127.0.0.1", 0), push_relay_factory=factory
        )
        try:
            await srv.start()
            assert srv.bound and not srv.closed.is_set() and srv._push_dispatcher is None
            assert srv._runner is not None and srv._watch is not None
            if creation != "factory":
                assert relay.closed
        finally:
            await srv.stop(notify=False)

    run(env, scenario)


def test_resistant_close_keeps_actual_push_drain_pending(env):
    async def scenario(client):
        _, _, _, relay, dispatcher, _, _ = await prepare(env, client)
        release, entered = asyncio.Event(), asyncio.Event()

        async def resistant():
            entered.set()
            while not release.is_set():
                with contextlib.suppress(asyncio.CancelledError):
                    await release.wait()

        relay.close = resistant
        await dispatcher.close()
        await entered.wait()
        assert dispatcher.retirement_pending
        waiter = asyncio.create_task(dispatcher.wait_drained())
        await asyncio.sleep(0)
        assert not waiter.done()
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert dispatcher.retirement_pending
        release.set()
        await dispatcher.wait_drained()
        assert not dispatcher.retirement_pending
        await dispatcher.close()  # same actual close owner, no replay

    run(env, scenario)


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_push_worker_publication_retains_intent_and_refuses_drain(env, monkeypatch,
                                                                       after_enqueue):
    async def scenario(client):
        _setup(env)
        dispatcher = PushDispatcher(env.ctx, Relay(), require_gate=server._require_approvals_gate)
        loop, actual = asyncio.get_running_loop(), []
        original = loop.create_task
        calls = []

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) == "_run_owned":
                calls.append(1)
                if len(calls) == 1:
                    if after_enqueue:
                        actual.append(original(coro, *args, **kwargs))
                    raise MemoryError("synthetic push worker publication loss")
            return original(coro, *args, **kwargs)

        monkeypatch.setattr(loop, "create_task", create)
        try:
            with pytest.raises(MemoryError):
                dispatcher.start()
            assert dispatcher.closed and len(dispatcher._owned_tasks) == 1
            await dispatcher.close()
            with pytest.raises(RuntimeError, match="publication unresolved"):
                await dispatcher.wait_drained()
            assert dispatcher.retirement_pending
        finally:
            for task in actual:
                task.cancel()
            await asyncio.gather(*actual, return_exceptions=True)
            if not after_enqueue:
                for coro, wrapper, task in dispatcher._owned_tasks.values():
                    if task is None:
                        wrapper.close()
                        coro.close()  # fixture knows enqueue never happened

    run(env, scenario)


def test_listener_keeps_push_debt_until_resistant_relay_actually_settles(env):
    async def scenario(client):
        _, _, _, _, prior, _, _ = await prepare(env, client)
        await prior.close()
        relay = Relay()
        release = asyncio.Event()

        async def resistant():
            while not release.is_set():
                with contextlib.suppress(asyncio.CancelledError):
                    await release.wait()

        relay.close = resistant
        srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0),
                               push_relay_factory=lambda: relay)
        await srv.start()
        dispatcher = srv._push_dispatcher
        try:
            await srv.stop(notify=False)
            assert srv.closed.is_set() and srv.operator_worker_debt == 1
            assert srv._push_dispatcher_drained is dispatcher
            drain = asyncio.create_task(srv.wait_operator_drain())
            await asyncio.sleep(0)
            assert not drain.done() and srv.operator_worker_debt == 1
            release.set()
            await drain
            assert srv.operator_worker_debt == 0 and not dispatcher.retirement_pending
        finally:
            release.set()
            await srv.stop(notify=False)
            await dispatcher.wait_drained()

    run(env, scenario)


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_push_close_owner_never_replays_or_certifies_drain(env, monkeypatch,
                                                                 after_enqueue):
    async def scenario(client):
        _, _, _, _, dispatcher, _, _ = await prepare(env, client)
        loop, actual, calls = asyncio.get_running_loop(), [], []
        original = loop.create_task

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) == "_close_owned":
                calls.append(1)
                if after_enqueue:
                    actual.append(original(coro, *args, **kwargs))
                raise MemoryError("synthetic push close publication loss")
            return original(coro, *args, **kwargs)

        monkeypatch.setattr(loop, "create_task", create)
        try:
            for _ in range(2):
                with pytest.raises(RuntimeError, match="cleanup ownership unresolved"):
                    await dispatcher.close()
            if actual:
                await actual[0]  # fixture observation is not retained production ownership
            with pytest.raises(RuntimeError, match="cleanup ownership unresolved"):
                await dispatcher.wait_drained()
            assert len(calls) == 1 and dispatcher.retirement_pending
        finally:
            if not after_enqueue:
                dispatcher._close_coro.close()
                for task in dispatcher.workers:
                    task.cancel()
                await asyncio.gather(*dispatcher.workers, return_exceptions=True)
                await dispatcher.relay.close()  # fixture cleanup only

    run(env, scenario)


def test_known_push_task_cancelled_before_wrapper_entry_retires_original_coroutine(env):
    async def scenario(client):
        _setup(env)
        dispatcher = PushDispatcher(env.ctx, Relay(), require_gate=server._require_approvals_gate)
        entered = []

        async def work():
            entered.append(True)
            await asyncio.Event().wait()

        coro = work()
        task = dispatcher._spawn_owned(coro)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)
        assert not entered and coro.cr_frame is None and not dispatcher._owned_tasks
        await dispatcher.close()
        await dispatcher.wait_drained()

    run(env, scenario)


def test_push_drain_rejects_coordinated_store_alias_replacement(env):
    async def scenario(client):
        _, _, _, _, dispatcher, _, _ = await prepare(env, client)
        await dispatcher.close()
        original = dispatcher.store
        replacement = object()
        env.ctx.prompt_store = replacement
        dispatcher.store = replacement
        try:
            with pytest.raises(RuntimeError, match="scope changed"):
                await dispatcher.wait_drained()
        finally:
            env.ctx.prompt_store = original
            dispatcher.store = original
        await dispatcher.wait_drained()

    run(env, scenario)


def test_actual_authorization_thread_outlives_cancelled_dispatch_and_blocks_drain(env, monkeypatch):
    from hmp_plugin import push_dispatch

    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def authorize(*_args, **_kwargs):
        entered.set()
        release.wait()
        finished.set()

    monkeypatch.setattr(push_dispatch, "require_bot_authorized", authorize)

    async def scenario(client):
        _, row, _, _, dispatcher, _, _ = await prepare(env, client)
        dispatcher.observe(event(row, dispatcher.store.generation))
        try:
            await until(entered.is_set)
            await dispatcher.close()
            assert not finished.is_set() and dispatcher.retirement_pending
            waiter = asyncio.create_task(dispatcher.wait_drained())
            await asyncio.sleep(0)
            assert not waiter.done()
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
            assert not finished.is_set() and dispatcher.retirement_pending
            release.set()
            await dispatcher.wait_drained()
            assert finished.is_set() and not dispatcher.retirement_pending
        finally:
            release.set()
            await dispatcher.close()
            await dispatcher.wait_drained()

    run(env, scenario)


def test_failed_dispatcher_start_retains_slow_relay_until_actual_close(env, monkeypatch):
    async def scenario(client):
        _setup(env)
        relay, release, calls = Relay(), asyncio.Event(), []

        async def slow_close():
            calls.append("close")
            await release.wait()

        relay.close = slow_close
        monkeypatch.setattr(PushDispatcher, "start", lambda _: (_ for _ in ()).throw(
            RuntimeError("synthetic failed start")))
        srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0),
                               push_relay_factory=lambda: relay)
        try:
            await srv.start()
            assert srv._push_dispatcher is None and srv._push_start_dispatcher is not None
            retained = srv._push_start_dispatcher
            await srv.stop(notify=False)
            assert srv._push_dispatcher_drained is retained and srv.operator_worker_debt == 1
            release.set()
            await srv.wait_operator_drain()
            assert srv.operator_worker_debt == 0 and calls == ["close"]
        finally:
            release.set()
            await srv.stop(notify=False)

    run(env, scenario)


def test_failed_dispatcher_constructor_retains_one_original_relay_close(env, monkeypatch):
    async def scenario(client):
        _setup(env)
        relay, release, calls = Relay(), asyncio.Event(), []

        async def slow_close():
            calls.append("close")
            await release.wait()

        relay.close = slow_close
        monkeypatch.setattr(server, "PushDispatcher", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("synthetic failed constructor")))
        srv = server.HmpServer(env.ctx, server.ListenerSettings("127.0.0.1", 0),
                               push_relay_factory=lambda: relay)
        try:
            await srv.start()
            assert srv._push_start_relay is relay and srv._push_start_dispatcher is None
            await srv.stop(notify=False)
            assert srv.operator_worker_debt == 1 and calls == ["close"]
            release.set()
            await srv.wait_operator_drain()
            assert srv.operator_worker_debt == 0 and calls == ["close"]
        finally:
            release.set()
            await srv.stop(notify=False)

    run(env, scenario)


def test_failed_relay_close_cannot_certify_retirement_or_replay(env):
    async def scenario(client):
        _, _, _, relay, dispatcher, _, _ = await prepare(env, client)
        calls = []

        async def failed_close():
            calls.append("close")
            raise RuntimeError("private synthetic close error")

        relay.close = failed_close
        await dispatcher.close()
        with pytest.raises(RuntimeError, match="relay cleanup success unconfirmed"):
            await dispatcher.wait_drained()
        await dispatcher.close()
        assert dispatcher.retirement_pending and calls == ["close"]

    run(env, scenario)
