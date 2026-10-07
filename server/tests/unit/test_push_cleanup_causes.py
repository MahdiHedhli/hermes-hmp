"""PN-REV: actual SQLite FULL after each committed native HMP cause, not a mocked error.

The injection enters through each of the three push cleanup write stages. A second connection
observes the committed cause before the real allocation fails and SQLite aborts cleanup.
"""

from __future__ import annotations

import logging
import sqlite3
import threading

import pytest

from hmp_plugin import crypto, wire
from hmp_plugin.contract import REFRESH_RETRY_GRACE_S
from hmp_plugin.revoke import revoke_device

from .hmp_kit import Env, code, get, pair, post, run
from .test_push_store import generation, row, seed_row

TABLES = (
    "meta",
    "devices",
    "token_families",
    "pairings",
    "refresh_tokens",
    "access_tokens",
    "audit",
)


def snapshot(conn):
    return {
        name: sorted(tuple(r) for r in conn.execute(f"SELECT * FROM {name}"))  # noqa: S608 -- fixed names
        for name in TABLES
    }


class FullDuringCleanup(sqlite3.Connection):
    armed = False
    observed = None
    error_code = None
    attempts = 0
    target = "UPDATE push_device_generations SET generation"
    recovery_commits = None

    def execute(self, sql, parameters=()):
        if self.armed and sql.startswith(self.target):
            self.armed = False
            self.attempts += 1
            # No push work may precede the commit: independent read proves it.
            other = sqlite3.connect(self.path)
            try:
                self.observed = snapshot(other)
            finally:
                other.close()
            pages = super().execute("PRAGMA page_count").fetchone()[0]
            super().execute(f"PRAGMA max_page_count={pages}")
            try:
                super().execute("INSERT INTO disk_pressure VALUES (zeroblob(8388608))")
            except sqlite3.OperationalError as exc:
                self.error_code = exc.sqlite_errorcode
                assert self.error_code == sqlite3.SQLITE_FULL
                assert not self.in_transaction  # SQLite aborted this separate cleanup transaction
                raise
            raise AssertionError("real disk-full injection did not fail")
        result = super().execute(sql, parameters)
        if sql == "COMMIT" and self.recovery_commits is not None:
            # Independent read after commit proves retirement is durable before
            # the subsequent purge deletion; observing execute inputs cannot.
            other = sqlite3.connect(self.path)
            other.row_factory = sqlite3.Row
            try:
                self.recovery_commits.append(
                    {
                        table: [dict(r) for r in other.execute(query)]
                        for table, query in (
                            ("push_registrations", "SELECT * FROM push_registrations"),
                            ("push_device_generations", "SELECT * FROM push_device_generations"),
                            ("audit", "SELECT * FROM audit"),
                        )
                    }
                )
            finally:
                other.close()
        return result


def install_full_injector(store, stage):
    path = store._path
    store._require_conn().execute("CREATE TABLE disk_pressure (payload BLOB)")
    store.close()
    conn = sqlite3.connect(
        str(path), isolation_level=None, check_same_thread=False, factory=FullDuringCleanup
    )
    conn.path = path
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    store._conn = conn
    conn.target = {
        "generation": "UPDATE push_device_generations SET generation",
        "registration": "UPDATE push_registrations SET state =",
        "audit": "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, 'push_retire'",
    }[stage]
    conn.armed = True
    return conn


@pytest.mark.parametrize("cause", ["operator", "self", "refresh_reuse", "p4_reissue", "identity"])
@pytest.mark.parametrize("stage", ["generation", "registration", "audit"])
def test_full_cleanup_cannot_change_committed_cause_or_response(tmp_path, cause, stage, caplog):
    caplog.set_level(logging.INFO)
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)
        family = env.store.get_access_token(crypto.sha256(wire.b64u_decode(dev.access, length=32)))[
            "family_id"
        ]
        digest = seed_row(
            env.store,
            dev.device_id,
            family=family,
            iid=env.iid,
            host_generation=env.store.revocation_epoch(),
            expires=env.clock.now + 3600,
        )
        before = snapshot(env.store._require_conn())
        first_refresh = dev.refresh
        if cause == "refresh_reuse":
            status, grant = await post(client, "/auth/token", env.p5_body(dev))
            assert status == 200
            dev.refresh, dev.access = grant["refresh_token"], grant["access_token"]
            env.clock.now += REFRESH_RETRY_GRACE_S + 1
        conn = install_full_injector(env.store, stage)
        if cause == "operator":
            result = revoke_device(env.store, dev.device_id, now=env.clock.now)
            assert result.found and result.was_active and result.last_device
        elif cause == "self":
            status, body = await post(
                client, "/devices/self/revoke", env.self_revoke_body(dev), headers=env.headers(dev)
            )
            assert (status, body) == (200, {})
        elif cause == "refresh_reuse":
            status, body = await post(
                client, "/auth/token", env.p5_body(dev, refresh=first_refresh)
            )
            assert (status, code(body)) == (401, "revoked")
        elif cause == "p4_reissue":
            env.clock.now += 2
            status, body = await post(client, "/pair/complete", env.p4_body(dev))
            assert status == 200 and body["device_id"] == dev.device_id
            assert body["access_token"] != dev.access
        else:
            assert (
                env.store.revoke_all_for_identity_change(env.clock.now) == before["meta"][0][2] + 1
            )
        assert conn.attempts == 1 and conn.error_code == sqlite3.SQLITE_FULL
        assert snapshot(conn) == conn.observed  # cleanup failed, exact cause still committed
        assert snapshot(conn) != before
        assert (
            row(env.store, digest)["state"] == "active"
        )  # stale, never eligible merely by existence
        assert generation(env.store, dev.device_id) == 1
        assert env.store.get_token_family(family)["revoked_at"] == env.clock.now
        if cause == "p4_reissue":
            live = conn.execute(
                "SELECT family_id FROM token_families WHERE revoked_at IS NULL"
            ).fetchall()
            assert len(live) == 1 and live[0][0] != family
            dev.access = body["access_token"]
            assert (await get(client, "/bots", headers=env.headers(dev)))[0] == 200
        else:
            assert (await get(client, "/bots", headers=env.headers(dev)))[0] == 401
        conn.execute("PRAGMA max_page_count=1073741823")
        conn.recovery_commits = []
        env.store.purge_push(
            now=env.clock.now, key=None, push_available=False, live_kids=frozenset()
        )
        recovered = conn.recovery_commits[0]
        assert len(recovered["push_registrations"]) == 1
        retired = recovered["push_registrations"][0]
        assert retired["state"] == "retired"
        assert all(retired[k] is None for k in ("sealed", "request_hash", "body_hash"))
        assert recovered["push_device_generations"][0]["generation"] == 2
        audit = [r for r in env.store.audit_events() if r["event"] == "push_retire"]
        assert len(audit) == 1
        assert tuple(audit[0]) == (env.clock.now, "push_retire", dev.device_id[:8], "retired")
        assert len([r for r in recovered["audit"] if r["event"] == "push_retire"]) == 1
        env.store.purge_push(
            now=env.clock.now, key=None, push_available=False, live_kids=frozenset()
        )
        assert len([r for r in env.store.audit_events() if r["event"] == "push_retire"]) == 1
        if cause in {"operator", "self", "identity"}:
            assert row(env.store, digest) is None
            assert generation(env.store, dev.device_id) == 0
        else:
            assert row(env.store, digest)["state"] == "retired"
            assert row(env.store, digest)["sealed"] is None
            assert generation(env.store, dev.device_id) == 2
        if cause == "p4_reissue":
            assert (
                conn.execute(
                    "SELECT count(*) FROM token_families WHERE revoked_at IS NULL"
                ).fetchone()[0]
                == 1
            )

    run(env, scenario)
    assert any("event=push_purge outcome=cleanup_failed" in r.getMessage() for r in caplog.records)
    assert all("disk is full" not in r.getMessage() for r in caplog.records)


def test_operator_revoke_cleanup_is_not_nested_and_retires_after_commit(tmp_path):
    env = Env(tmp_path)
    env.store.insert_user("user", "synthetic", 1)
    env.store.insert_device("dev-test", "user", "fp", b"pub", "phone", 1, state="ACTIVE")
    env.store.insert_token_family("family-dev-test", "dev-test", 1)
    digest = seed_row(env.store, "dev-test", iid=env.iid, expires=env.clock.now + 3600)
    done = threading.Event()
    errors = []

    def perform():
        try:
            assert revoke_device(env.store, "dev-test", now=env.clock.now).found
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    worker = threading.Thread(target=perform, daemon=True)
    worker.start()
    assert done.wait(2), "nested cleanup deadlocked on Store's non-reentrant write lock"
    worker.join()
    assert errors == []
    retired = row(env.store, digest)
    assert retired["state"] == "retired"
    assert all(retired[k] is None for k in ("sealed", "request_hash", "body_hash"))
    assert generation(env.store, "dev-test") == 2
    audit = [r for r in env.store.audit_events() if r["event"] == "push_retire"]
    assert len(audit) == 1
    assert tuple(audit[0]) == (env.clock.now, "push_retire", "dev-test", "retired")
    assert env.store.cleanup_push_after_commit(now=env.clock.now)
    assert generation(env.store, "dev-test") == 2
    assert len([r for r in env.store.audit_events() if r["event"] == "push_retire"]) == 1
    env.store.purge_push(now=env.clock.now, key=None, push_available=False, live_kids=frozenset())
    assert row(env.store, digest) is None
    assert generation(env.store, "dev-test") == 0
    env.store.close()


def test_grace_retry_and_initial_pairing_do_not_run_cleanup(tmp_path, monkeypatch):
    env = Env(tmp_path)
    calls = []
    monkeypatch.setattr(env.store, "cleanup_push_after_commit", lambda **kw: calls.append(kw))

    async def scenario(client):
        dev = await pair(env, client)
        original = dev.refresh
        status, grant = await post(client, "/auth/token", env.p5_body(dev))
        assert status == 200
        status, retry = await post(client, "/auth/token", env.p5_body(dev, refresh=original))
        assert status == 200 and retry == grant
        assert calls == []

    run(env, scenario)


def test_reissue_cleanup_preserves_registration_of_concurrently_issued_live_family(
    tmp_path, monkeypatch
):
    env = Env(tmp_path)

    async def scenario(client):
        dev = await pair(env, client)
        old_family = env.store.get_access_token(
            crypto.sha256(wire.b64u_decode(dev.access, length=32))
        )["family_id"]
        old = seed_row(
            env.store,
            dev.device_id,
            family=old_family,
            iid=env.iid,
            host_generation=env.store.revocation_epoch(),
            expires=env.clock.now + 3600,
        )
        real_cleanup = env.store.cleanup_push_after_commit
        fresh = []

        def intervening_registration(*, now):
            # Simulate a valid new-family PUT landing between cause commit and cleanup.
            new_family = (
                env.store._require_conn()
                .execute("SELECT family_id FROM token_families WHERE revoked_at IS NULL")
                .fetchone()[0]
            )
            assert new_family != old_family
            with env.store.transaction() as conn:
                conn.execute(
                    "UPDATE push_registrations SET state='retired',sealed=NULL,"
                    "request_hash=NULL,body_hash=NULL WHERE route_hash=?",
                    (old,),
                )
                assert env.store.advance_push_generation_in(conn, dev.device_id) == 2
            fresh.append(
                seed_row(
                    env.store,
                    dev.device_id,
                    family=new_family,
                    iid=env.iid,
                    host_generation=env.store.revocation_epoch(),
                    generation=2,
                    number=2,
                    expires=now + 3600,
                )
            )
            return real_cleanup(now=now)

        monkeypatch.setattr(env.store, "cleanup_push_after_commit", intervening_registration)
        env.clock.now += 2
        status, body = await post(client, "/pair/complete", env.p4_body(dev))
        assert status == 200
        assert row(env.store, old)["state"] == "retired"
        assert row(env.store, fresh[0])["state"] == "active"
        assert generation(env.store, dev.device_id) == 2
        dev.access = body["access_token"]
        assert (await get(client, "/bots", headers=env.headers(dev)))[0] == 200

    run(env, scenario)
