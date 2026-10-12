"""Real bearer routes, isolated custody/store. No live host, relay, provider or phone."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
from contextlib import contextmanager

import pytest

from hmp_plugin import wire

from .hmp_kit import Env, code, pair, post, run, url
from .test_push_store import seed_device, seed_row

PATH = "/push/registration"


@pytest.fixture
def env(tmp_path):
    value = Env(tmp_path)
    value.ctx.push_settings = lambda: {
        "enabled": True,
        "relay_url": "https://relay.invalid/base",
        "relay_audience": "test-audience",
        "relay_kids": ["kid-a"],
    }
    value.ctx.direct_send_flag = lambda: True
    value.ctx.approvals_available = lambda: True
    yield value
    value.store.close()


async def owner(env, client):
    dev = await pair(env, client)
    env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
    return dev


def intent(env, generation=0, *, number=1, size=82, platform="apns", **overrides):
    body = {
        "v": 1,
        "request_id": wire.b64u_encode(number.to_bytes(16, "big")),
        "expected_generation": generation,
        "platform": platform,
        "addr_kind": "apns_token" if platform == "apns" else "fcm_token",
        "relay_kid": "kid-a",
        "sealed": wire.b64u_encode(b"s" * size),
        "seal_expires_at": env.clock.now + 7200,
    }
    if platform == "apns":
        body["env"] = "sandbox"
    return body | overrides


async def request(env, client, dev, method, body=None, *, headers=None):
    args = {"headers": env.headers(dev) if headers is None else headers}
    if body is not None:
        args["data"] = body if isinstance(body, bytes) else wire.dump_json(body)
        args["headers"] = args["headers"] | {"Content-Type": "application/json"}
    response = await getattr(client, method)(url(PATH), **args)
    return response.status, await response.json()


def unchanged(env):
    conn = env.store._require_conn()
    return tuple(tuple(row) for row in conn.execute("SELECT * FROM push_registrations")), tuple(
        tuple(row) for row in conn.execute("SELECT * FROM push_device_generations")
    )


def test_issue_replay_replace_and_delete_have_exact_wire_and_custody(env):
    async def scenario(client):
        dev = await owner(env, client)
        before = env.store._require_conn().total_changes
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data == {
            "available": True,
            "relay_kids": ["kid-a"],
            "generation": 0,
            "registration": None,
        }
        assert env.store._require_conn().total_changes == before
        body = intent(env)
        status, first = await request(env, client, dev, "put", body)
        assert status == 200 and set(first) == {"route", "generation", "state", "expires_at"}
        assert first["generation"] == 1 and first["state"] == "active"
        row = env.store._require_conn().execute("SELECT * FROM push_registrations").fetchone()
        raw = wire.b64u_decode(first["route"], length=32)
        fields = (
            env.iid.encode(),
            row["host_generation"].to_bytes(8, "big"),
            dev.device_id.encode(),
            row["family_id"].encode(),
            (1).to_bytes(8, "big"),
            bytes(row["salt"]),
        )
        transcript = b"HMP1-PUSH-ROUTE" + b"".join(len(x).to_bytes(4, "big") + x for x in fields)
        assert hmac.digest(env.identity.k_grace(), transcript, "sha256") == raw
        assert bytes(row["route_hash"]) == hashlib.sha256(raw).digest()
        assert bytes(row["sealed"]) == b"s" * 82 and raw not in tuple(row)
        snapshot = unchanged(env)
        status, replay = await request(env, client, dev, "put", dict(reversed(list(body.items()))))
        assert (status, replay) == (200, first) and unchanged(env) == snapshot
        status, conflict = await request(env, client, dev, "put", body | {"env": "production"})
        assert status == 409 and code(conflict) == "idempotency_conflict"
        assert unchanged(env) == snapshot
        status, second = await request(env, client, dev, "put", intent(env, 1, number=2))
        assert status == 200 and second["generation"] == 2 and second["route"] != first["route"]
        retired = (
            env.store._require_conn()
            .execute("SELECT * FROM push_registrations WHERE state = 'retired'")
            .fetchone()
        )
        assert retired["sealed"] is retired["request_hash"] is retired["body_hash"] is None
        status, deleted = await request(
            env, client, dev, "delete", {"v": 1, "expected_generation": 2}
        )
        assert (status, deleted) == (200, {"generation": 3})
        status, stale = await request(env, client, dev, "put", body)
        assert status == 409 and set(stale["error"]) == {"code", "message"}
        assert code(stale) == "stale"
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["generation"] == 3 and data["registration"] is None
        assert env.bridge.calls == []

    run(env, scenario)


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_wrong_instance_and_owner_precede_body_or_push_reads(env, method, monkeypatch):
    async def scenario(client):
        dev = await pair(env, client)

        def forbidden(*args, **kwargs):
            raise AssertionError("registration/config read before authority")

        monkeypatch.setattr(env.store, "push_status_snapshot", forbidden)
        env.ctx.push_settings = forbidden
        status, data = await request(
            env, client, dev, method, b"bad", headers=env.headers(dev, iid="foreign")
        )
        assert status == 401 and code(data) == "wrong_instance"
        status, data = await request(env, client, dev, method, b"bad")
        assert status == 404 and code(data) == "not_found"
        # A separate controls grant alone still cannot confer approval ownership.
        monkeypatch.setattr(env.store, "owner_controls_decision", lambda _: True)
        status, data = await request(env, client, dev, method, b"bad")
        assert status == 404 and code(data) == "not_found"
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id})
        monkeypatch.setattr(env.store, "owner_controls_decision", lambda _: False)
        status, data = await request(env, client, dev, method, b"bad")
        assert status == 404 and code(data) == "not_found"

    run(env, scenario)


@pytest.mark.parametrize(
    "patch",
    [
        {"v": True},
        {"v": 1.0},
        {"v": 2},
        {"expected_generation": True},
        {"expected_generation": -1},
        {"expected_generation": 2**53},
        {"request_id": "AA"},
        {"request_id": wire.b64u_encode(b"r" * 33)},
        {"relay_kid": "-bad"},
        {"relay_kid": "é"},
        {"relay_kid": []},
        {"platform": "unknown"},
        {"addr_kind": "fcm_token"},
        {"env": None},
        {"env": "other"},
        {"extra": "bad"},
        {"seal_expires_at": True},
        {"sealed": wire.b64u_encode(b"s" * 81)},
        {"sealed": wire.b64u_encode(b"s" * 1106)},
        {"sealed": "AA=="},
        {"sealed": wire.b64u_encode(b"s" * 82)[:-1] + "_"},
    ],
)
def test_malformed_put_is_400_even_when_unavailable(env, patch):
    async def scenario(client):
        dev = await owner(env, client)
        env.ctx.push_settings = lambda: None
        status, data = await request(env, client, dev, "put", intent(env) | patch)
        assert status == 400 and code(data) == "bad_request"
        assert unchanged(env) == ((), ())

    run(env, scenario)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (b'{"v":1,"v":1}', 400),
        (b"[]", 400),
        (b'{"v":"\\ud800"}', 400),
        (b" " * 4097, 413),
        (b"[" * 30, 413),
        (b"\xff", 400),
    ],
)
def test_raw_body_bounds_and_ijson(env, raw, expected):
    async def scenario(client):
        dev = await owner(env, client)
        for method in ("put", "delete"):
            status, data = await request(env, client, dev, method, raw)
            assert status == expected and code(data) in ("bad_request", "too_large")
        assert unchanged(env) == ((), ())

    run(env, scenario)


@pytest.mark.parametrize("size", [82, 1105])
@pytest.mark.parametrize("platform", ["apns", "fcm"])
def test_seal_boundary_and_opaque_point_accepted(env, size, platform):
    async def scenario(client):
        dev = await owner(env, client)
        status, data = await request(
            env, client, dev, "put", intent(env, size=size, platform=platform)
        )
        assert status == 200 and data["generation"] == 1

    run(env, scenario)


@pytest.mark.parametrize(
    "offset,expected", [(3600, 400), (3601, 200), (1209600, 200), (1209601, 400)]
)
def test_expiry_boundaries(env, offset, expected):
    async def scenario(client):
        dev = await owner(env, client)
        status, _ = await request(
            env, client, dev, "put", intent(env, seal_expires_at=env.clock.now + offset)
        )
        assert status == expected

    run(env, scenario)


@pytest.mark.parametrize("kind", ["fcm_token", "fcm_fid"])
def test_fcm_forbids_env_even_null_and_accepts_kinds(env, kind):
    async def scenario(client):
        dev = await owner(env, client)
        body = intent(env, platform="fcm", addr_kind=kind)
        status, data = await request(env, client, dev, "put", body | {"env": None})
        assert status == 400 and code(data) == "bad_request"
        status, _ = await request(env, client, dev, "put", body)
        assert status == 200

    run(env, scenario)


@pytest.mark.parametrize(
    "off,why",
    [
        ("disabled", "push_disabled"),
        ("relay", "relay_unconfigured"),
        ("approvals", "approvals_unavailable"),
        ("direct", "approvals_unavailable"),
    ],
)
def test_get_and_delete_readable_while_off_put_order(env, off, why, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        body = intent(env)
        assert (await request(env, client, dev, "put", body))[0] == 200
        if off == "disabled":
            env.ctx.push_settings = lambda: {"enabled": False}
        elif off == "relay":
            env.ctx.push_settings = lambda: {"enabled": True}
        elif off == "approvals":
            env.ctx.approvals_available = lambda: False
        else:
            env.ctx.direct_send_flag = lambda: False
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["why"] == why and "relay_kids" not in data
        assert data["registration"]["state"] == "active"
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "put", body | {"relay_kid": "removed"})
        assert status == 503 and data["error"]["why"] == why and unchanged(env) == snapshot

        def forbidden():
            raise AssertionError("DELETE must not read delivery config")

        async def forbidden_key(self):
            raise AssertionError("DELETE must not read key")

        env.ctx.push_settings = forbidden
        monkeypatch.setattr(type(env.identity), "read_k_grace_for_push", forbidden_key)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert (status, data) == (200, {"generation": 2})

    run(env, scenario)


@pytest.mark.parametrize("loss", ["key", "kid", "family", "hash", "iid", "H", "G", "expiry"])
def test_get_unusable_is_expired_no_write_and_replay_fails_closed(env, loss, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        body = intent(env)
        assert (await request(env, client, dev, "put", body))[0] == 200
        conn = env.store._require_conn()
        if loss == "key":

            async def no_key(self):
                return None

            monkeypatch.setattr(type(env.identity), "read_k_grace_for_push", no_key)
        elif loss == "kid":
            old = env.ctx.push_settings()
            env.ctx.push_settings = lambda: old | {"relay_kids": ["kid-b"]}
        elif loss == "family":
            env.store.insert_token_family("new-family", dev.device_id, env.clock.now)
            conn.execute("UPDATE push_registrations SET family_id='new-family'")
        elif loss == "hash":
            conn.execute("UPDATE push_registrations SET route_hash=?", (b"h" * 32,))
        elif loss == "iid":
            conn.execute("UPDATE push_registrations SET iid='other-instance'")
        elif loss == "H":
            conn.execute("UPDATE push_registrations SET host_generation=99")
        elif loss == "G":
            conn.execute("UPDATE push_device_generations SET generation=2")
        else:
            conn.execute("UPDATE push_registrations SET expires_at=?", (env.clock.now,))
        snapshot, before = unchanged(env), conn.total_changes
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["registration"]["state"] == "expired"
        assert "route" not in data["registration"] and conn.total_changes == before
        status, data = await request(env, client, dev, "put", body)
        expected = (
            "bad_request"
            if loss == "kid"
            else ("retry_state_lost" if loss in ("key", "hash") else "stale")
        )
        assert status in (400, 409, 503) and code(data) == expected
        assert unchanged(env) == snapshot

    run(env, scenario)


@pytest.mark.parametrize("during", ["revoked", "pending", "family", "owner", "off"])
def test_put_rechecks_after_off_loop_key_read_before_replay_or_cas(env, during, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        body = intent(env)
        assert (await request(env, client, dev, "put", body))[0] == 200
        key = env.identity.k_grace()

        async def race(self):
            if during in ("revoked", "pending"):
                env.store.set_device_state(dev.device_id, during.upper())
            elif during == "family":
                row = (
                    env.store._require_conn()
                    .execute("SELECT family_id FROM push_registrations")
                    .fetchone()
                )
                env.store.revoke_family(row[0], env.clock.now)
            elif during == "owner":
                env.ctx.owner_device_ids = lambda: frozenset()
            else:
                env.ctx.push_settings = lambda: None
            return key

        monkeypatch.setattr(type(env.identity), "read_k_grace_for_push", race)
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "put", body)
        assert status == (404 if during == "owner" else 503 if during == "off" else 401)
        assert code(data) == (
            "not_found"
            if during == "owner"
            else "write_gate_closed"
            if during == "off"
            else "revoked"
        )
        assert unchanged(env) == snapshot

    run(env, scenario)


def test_delete_sqlite_failure_fences_current_row_and_recovery_clears(env, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        digest = bytes(
            env.store._require_conn()
            .execute("SELECT route_hash FROM push_registrations")
            .fetchone()[0]
        )
        original = env.store.delete_push_in

        def failure(conn, device_id, *, now):
            original(conn, device_id, now=now)
            raise sqlite3.OperationalError("synthetic disk failure")

        monkeypatch.setattr(env.store, "delete_push_in", failure)
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert status == 503 and code(data) == "other" and unchanged(env) == snapshot
        assert env.ctx.push_route_fenced(digest)
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["registration"] is None
        status, data = await request(env, client, dev, "put", intent(env))
        assert status == 409 and code(data) == "stale"
        monkeypatch.setattr(env.store, "delete_push_in", original)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert (status, data) == (200, {"generation": 2}) and not env.ctx.push_route_fenced(digest)

    run(env, scenario)


def test_buckets_share_put_delete_and_get_has_separate_limit(env):
    async def scenario(client):
        dev = await owner(env, client)
        for n in range(6):
            method = "put" if n % 2 else "delete"
            status, _ = await request(env, client, dev, method, b"bad")
            assert status == 400
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 0})
        assert status == 429 and code(data) == "rate_limited" and unchanged(env) == snapshot
        for _ in range(30):
            assert (await request(env, client, dev, "get"))[0] == 200
        status, data = await request(env, client, dev, "get")
        assert status == 429 and code(data) == "rate_limited"
        env.clock.now += 60
        assert (await request(env, client, dev, "delete", {"v": 1, "expected_generation": 0}))[
            0
        ] == 200
        status, data = await request(env, client, dev, "put", intent(env))
        assert status == 409 and code(data) == "stale"

    run(env, scenario)


@pytest.mark.parametrize("capacity", ["active", "generation"])
def test_capacity_refusal_no_mutation_existing_replacement_and_delete_still_work(env, capacity):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        env.store.insert_user("user", "synthetic", 1)
        for n in range(63 if capacity == "active" else 255):
            name = seed_device(env.store, f"capacity-{n}")
            if capacity == "active":
                seed_row(env.store, name, number=n + 2, iid=env.iid)
            else:
                env.store._require_conn().execute(
                    "INSERT INTO push_device_generations VALUES (?, 1)", (name,)
                )
        another = await pair(env, client)
        env.ctx.owner_device_ids = lambda: frozenset({dev.device_id, another.device_id})
        snapshot = unchanged(env)
        status, data = await request(env, client, another, "put", intent(env))
        assert status == 503 and data["error"]["why"] == "push_capacity"
        assert unchanged(env) == snapshot
        if capacity == "generation":
            status, data = await request(
                env, client, another, "delete", {"v": 1, "expected_generation": 0}
            )
            assert status == 503 and data["error"]["why"] == "push_capacity"
            assert unchanged(env) == snapshot
        assert (await request(env, client, dev, "put", intent(env, 1, number=2)))[0] == 200
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 2})
        assert (status, data) == (200, {"generation": 3})

    run(env, scenario)


def test_collision_rolls_back_retirement_generation_and_secret_wipe(env, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        status, issued = await request(env, client, dev, "put", intent(env))
        assert status == 200
        from hmp_plugin import store as store_module

        monkeypatch.setattr(
            store_module, "derive_route", lambda *_: wire.b64u_decode(issued["route"], length=32)
        )
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "put", intent(env, 1, number=2))
        assert status == 503 and code(data) == "other" and unchanged(env) == snapshot
        assert not env.store._require_conn().in_transaction

    run(env, scenario)


@pytest.mark.parametrize("method", ["put", "delete"])
def test_generation_ceiling_refuses_without_wrap_or_change(env, method):
    async def scenario(client):
        dev = await owner(env, client)
        env.store._require_conn().execute(
            "INSERT INTO push_device_generations VALUES (?, ?)", (dev.device_id, 2**53 - 1)
        )
        snapshot = unchanged(env)
        body = (
            intent(env, 2**53 - 1)
            if method == "put"
            else {"v": 1, "expected_generation": 2**53 - 1}
        )
        status, data = await request(env, client, dev, method, body)
        assert status == 503 and code(data) == "other" and unchanged(env) == snapshot

    run(env, scenario)


@pytest.mark.parametrize("state", ["provider_gone", "expired", "retired"])
def test_latest_row_rules_and_later_generation_fence(env, state):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        with env.store.transaction() as conn:
            row = env.store.active_push_in(conn, dev.device_id)
            env.store._leave_active_push_in(conn, row, state=state, now=env.clock.now)
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["generation"] == 2
        if state == "retired":
            assert data["registration"] is None
        else:
            assert data["registration"]["state"] == state
        assert (await request(env, client, dev, "delete", {"v": 1, "expected_generation": 2}))[
            0
        ] == 200
        status, data = await request(env, client, dev, "get")
        assert status == 200 and data["generation"] == 3 and data["registration"] is None

    run(env, scenario)


def test_retained_rows_bounded_and_evicted_request_is_stale(env):
    async def scenario(client):
        dev = await owner(env, client)
        first = intent(env)
        for n in range(11):
            if n and n % 3 == 0:
                status, token = await post(client, "/auth/token", env.p5_body(dev))
                assert status == 200
                dev.refresh, dev.access = token["refresh_token"], token["access_token"]
            body = first if n == 0 else intent(env, n, number=n + 1)
            assert (await request(env, client, dev, "put", body))[0] == 200
            env.clock.now += 60
        rows = env.store._require_conn().execute("SELECT * FROM push_registrations").fetchall()
        assert len(rows) == 9 and sum(row["state"] == "active" for row in rows) == 1
        assert all(row["sealed"] is None for row in rows if row["state"] != "active")
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "put", first)
        assert status == 409 and code(data) == "stale" and unchanged(env) == snapshot

    run(env, scenario)


class CommitFailure(sqlite3.Connection):
    fail_commit = False

    def execute(self, sql, parameters=()):
        if sql == "COMMIT" and self.fail_commit:
            self.fail_commit = False
            raise sqlite3.OperationalError("synthetic commit failure")
        return super().execute(sql, parameters)


def test_commit_failure_rolls_back_connection_and_fences_delete(env):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        path = env.store_path
        env.store.close()
        conn = sqlite3.connect(path, isolation_level=None, factory=CommitFailure)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        env.store._conn = conn
        snapshot = unchanged(env)
        conn.fail_commit = True
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert status == 503 and code(data) == "other"
        assert not conn.in_transaction and unchanged(env) == snapshot
        assert env.ctx.push_delete_fence and not env.ctx.push_delete_fence_closed
        assert (await request(env, client, dev, "get"))[1]["registration"] is None
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert (status, data) == (200, {"generation": 2}) and not env.ctx.push_delete_fence

    run(env, scenario)


def test_real_disk_full_fences_delete_and_purge_clears_only_after_commit(env):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        from .test_push_cleanup_causes import install_full_injector

        conn = install_full_injector(env.store, "generation")
        conn.armed = True
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 1})
        assert status == 503 and code(data) == "other" and conn.error_code == sqlite3.SQLITE_FULL
        assert unchanged(env) == snapshot and env.ctx.push_delete_fence
        assert (await request(env, client, dev, "get"))[1]["registration"] is None
        conn.execute("PRAGMA max_page_count=1073741823")
        env.store.purge_push(
            now=env.clock.now + 7200,
            key=env.identity.k_grace(),
            push_available=True,
            live_kids=frozenset({"kid-a"}),
        )
        env.ctx.prune_push_delete_fence()
        assert not env.ctx.push_delete_fence
        assert env.store.push_status_snapshot(dev.device_id)[0] == 2

    run(env, scenario)


@pytest.mark.parametrize("race", ["revoke", "family"])
def test_delete_transactional_liveness_precedes_cas(env, race, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)
        assert (await request(env, client, dev, "put", intent(env)))[0] == 200
        original = env.store.transaction

        @contextmanager
        def revoke_before_begin():
            if race == "revoke":
                env.store.set_device_state(dev.device_id, "REVOKED")
            else:
                row = (
                    env.store._require_conn()
                    .execute("SELECT family_id FROM push_registrations")
                    .fetchone()
                )
                env.store.revoke_family(row[0], env.clock.now)
            with original() as conn:
                yield conn

        monkeypatch.setattr(env.store, "transaction", revoke_before_begin)
        snapshot = unchanged(env)
        status, data = await request(env, client, dev, "delete", {"v": 1, "expected_generation": 0})
        assert status == 401 and code(data) == "revoked" and unchanged(env) == snapshot

    run(env, scenario)


def test_streamed_overlimit_body_and_new_issue_key_loss(env, monkeypatch):
    async def scenario(client):
        dev = await owner(env, client)

        async def chunks():
            yield b" " * 3000
            yield b" " * 1097

        response = await client.put(url(PATH), data=chunks(), headers=env.headers(dev))
        assert response.status == 413 and code(await response.json()) == "too_large"

        async def no_key(self):
            return None

        monkeypatch.setattr(type(env.identity), "read_k_grace_for_push", no_key)
        status, data = await request(env, client, dev, "put", intent(env))
        assert status == 503 and code(data) == "other" and unchanged(env) == ((), ())

    run(env, scenario)
