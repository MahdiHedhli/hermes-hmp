"""Spec 014 storage lifecycle, with historical databases and independent synthetic rows.

No live home, relay/provider address or key file. These tests do not certify routes,
listener scheduling, delivery, or complete T020/T022 integration.
"""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
from pathlib import Path

import pytest

from hmp_plugin.contract import ErrorCode, HmpError
from hmp_plugin.store import Store

KEY = b"k" * 32
NOW = 4_000_000


@pytest.fixture
def store(tmp_path: Path):
    value = Store(tmp_path / "store.sqlite3")
    value.migrate()
    value.insert_user("user", "synthetic", 1)
    yield value
    value.close()


def seed_device(store: Store, name: str, *, state: str = "ACTIVE") -> str:
    store.insert_device(name, "user", "fp", b"synthetic", "phone", 1, state=state)
    store.insert_token_family("family-" + name, name, 1)
    return name


def seed_row(
    store: Store,
    device: str,
    *,
    number: int = 1,
    state: str = "active",
    family: str | None = None,
    iid: str = "synthetic-iid",
    generation: int = 1,
    host_generation: int = 0,
    key: bytes = KEY,
    kid: str = "kid-a",
    expires: int = NOW + 3600,
    changed: int = NOW,
) -> bytes:
    """Expected digest recomputed from stdlib TR-13, without importing issuer code."""
    family = family or "family-" + device
    salt = number.to_bytes(32, "big")
    fields = (
        iid.encode(),
        host_generation.to_bytes(8, "big"),
        device.encode(),
        family.encode(),
        generation.to_bytes(8, "big"),
        salt,
    )
    message = b"HMP1-PUSH-ROUTE" + b"".join(len(f).to_bytes(4, "big") + f for f in fields)
    digest = hashlib.sha256(hmac.digest(key, message, "sha256")).digest()
    with store.transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO push_device_generations VALUES (?, ?)", (device, generation)
        )
        conn.execute(
            "INSERT INTO push_registrations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                digest,
                device,
                family,
                iid,
                host_generation,
                generation,
                salt,
                "apns",
                "apns_token",
                "sandbox",
                kid,
                b"c" * 82,
                b"r" * 32,
                b"b" * 32,
                state,
                NOW,
                expires,
                changed,
            ),
        )
    return digest


def row(store: Store, digest: bytes):
    return (
        store._require_conn()
        .execute("SELECT * FROM push_registrations WHERE route_hash = ?", (digest,))
        .fetchone()
    )


def generation(store: Store, device: str) -> int:
    return store.push_generation_in(store._require_conn(), device)


def purge(store: Store, *, key=KEY, available=True, kids=frozenset({"kid-a"}), now=NOW):
    store.purge_push(now=now, key=key, push_available=available, live_kids=kids)


@pytest.mark.parametrize("version", [1, 2])
def test_real_legacy_migration_preserves_data_and_reopens_idempotently(tmp_path, version):
    path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(path)
    fixture = Path(__file__).parents[1] / "fixtures" / f"push-legacy-schema-{version}.sql"
    conn.executescript(fixture.read_text())
    conn.execute("INSERT INTO users VALUES ('user','label',19)")
    conn.execute("INSERT INTO devices VALUES ('dev','user','fp',x'11','phone','ACTIVE',20)")
    conn.execute("INSERT INTO token_families VALUES ('family','dev',21,NULL)")
    conn.execute("INSERT INTO audit VALUES (22,'original',NULL,'ok')")
    if version == 2:
        conn.execute("INSERT INTO device_owner_controls VALUES ('dev',1,23)")
    old_ddl = dict(conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"))
    conn.commit()
    conn.close()
    for _ in range(2):
        store = Store(path)
        store.migrate()
        try:
            assert store.instance_epoch() == 7 and store.revocation_epoch() == 4
            assert store.get_device("dev")["state"] == "ACTIVE"
            assert store.get_token_family("family")["revoked_at"] is None
            assert len(store.audit_events()) == 1
            assert store.owner_controls_decision("dev") is (True if version == 2 else None)
            meta = store._require_conn().execute("SELECT schema_version FROM meta").fetchone()
            assert meta[0] == 3
            ddl = dict(
                store._require_conn().execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='table'"
                )
            )
            assert all(ddl[name] == sql for name, sql in old_ddl.items())
            assert {"push_registrations", "push_device_generations"} <= set(ddl)
            assert store._require_conn().execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            store.close()


@pytest.mark.parametrize("target", ["PENDING", "ACTIVE", "REVOKED"])
def test_revoked_device_cannot_be_revived_and_can_be_purged(store, target):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    store.set_device_state("dev", "REVOKED")
    store.set_device_state("dev", target)
    assert store.get_device("dev")["state"] == "REVOKED"
    purge(store, key=None, available=False, kids=frozenset())
    assert row(store, digest) is None and generation(store, "dev") == 0
    assert store.get_device("dev")["state"] == "REVOKED"
    with store.transaction() as conn, pytest.raises(HmpError) as exc:
        store.advance_push_generation_in(conn, "dev")
    assert exc.value.code is ErrorCode.REVOKED


def test_active_requires_generation_and_route_and_active_device_are_unique(store):
    seed_device(store, "dev")
    first = seed_row(store, "dev")
    with pytest.raises(sqlite3.IntegrityError):
        seed_row(store, "dev", number=2)
    with pytest.raises(sqlite3.IntegrityError):
        seed_row(store, "dev", state="retired")
    assert row(store, first)["state"] == "active"
    with store.transaction() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM push_device_generations WHERE device_id='dev'")


@pytest.mark.parametrize(
    "change",
    [
        "platform='other'",
        "addr_kind='fcm_token'",
        "env=NULL",
        "env='other'",
        "state='other'",
        "sealed=NULL",
        "request_hash=NULL",
        "body_hash=NULL",
    ],
)
def test_registration_schema_rejects_invalid_active_shapes(store, change):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    before = tuple(row(store, digest))
    with pytest.raises(sqlite3.IntegrityError), store.transaction() as conn:
        conn.execute(f"UPDATE push_registrations SET {change}")  # noqa: S608 -- fixed test literals
    assert tuple(row(store, digest)) == before


def test_registration_cannot_be_inserted_without_device_generation(store):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    values = tuple(row(store, digest))
    with store.transaction() as conn:
        conn.execute("DELETE FROM push_registrations")
        conn.execute("DELETE FROM push_device_generations")
    with pytest.raises(sqlite3.IntegrityError), store.transaction() as conn:
        conn.execute(
            "INSERT INTO push_registrations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values
        )
    assert row(store, digest) is None


def test_second_connection_cannot_revive_revoked_or_delete_live_generation(store):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    other = Store(store._path)
    other.migrate()
    try:
        assert other.get_device("dev")["state"] == "ACTIVE"  # stale caller observation
        store.set_device_state("dev", "REVOKED")
        other.set_device_state("dev", "ACTIVE")
        assert store.get_device("dev")["state"] == "REVOKED"
        purge(other, key=None)
        assert row(store, digest) is None and generation(store, "dev") == 0
        seed_device(store, "live")
        fresh = seed_row(store, "live")
        purge(other, key=None)
        assert row(store, fresh)["state"] == "active" and generation(store, "live") == 1
    finally:
        other.close()


@pytest.mark.parametrize("cause", ["expiry", "kid", "key", "family", "pending", "epoch"])
def test_purge_invalidates_by_each_authoritative_cause_and_wipes_secrets(store, cause):
    seed_device(store, "dev")
    digest = seed_row(store, "dev", expires=NOW if cause == "expiry" else NOW + 1)
    conn = store._require_conn()
    if cause == "family":
        conn.execute("UPDATE token_families SET revoked_at=1")
    if cause == "pending":
        store.set_device_state("dev", "PENDING")
    if cause == "epoch":
        conn.execute("UPDATE meta SET store_revocation_epoch=1")
    purge(
        store,
        key=b"z" * 32 if cause == "key" else KEY,
        kids=frozenset({"kid-b"}) if cause == "kid" else frozenset({"kid-a"}),
    )
    value = row(store, digest)
    assert value["state"] == ("retired" if cause in {"family", "pending", "epoch"} else "expired")
    assert all(value[k] is None for k in ("sealed", "request_hash", "body_hash"))
    assert generation(store, "dev") == 2
    audit = [r for r in store.audit_events() if r["event"] == "push_retire"]
    assert [tuple(r) for r in audit] == [(NOW, "push_retire", "dev", value["state"])]
    purge(store, key=None, available=False)
    assert generation(store, "dev") == 2  # no second advance for an already-retained row
    assert len([r for r in store.audit_events() if r["event"] == "push_retire"]) == 1


@pytest.mark.parametrize(
    "off_reason", ["push_disabled", "relay_unconfigured", "approvals_unavailable"]
)
@pytest.mark.parametrize("key", [KEY, None])
def test_push_off_preserves_inert_row_but_other_purge_work_continues(store, off_reason, key):
    # The PN-AV decision is the caller's job; this tests the storage predicate for every off reason.
    for name in ("inert", "expired", "revoked", "family"):
        seed_device(store, name)
    inert = seed_row(store, "inert", kid="removed")
    expired = seed_row(store, "expired", expires=NOW)
    revoked = seed_row(store, "revoked")
    family = seed_row(store, "family")
    store.set_device_state("revoked", "REVOKED")
    store.revoke_family("family-family", NOW)
    before = tuple(row(store, inert))
    purge(store, key=key, available=False, kids=frozenset())
    assert tuple(row(store, inert)) == before, off_reason
    assert generation(store, "inert") == 1
    assert row(store, expired)["state"] == "expired"
    assert row(store, revoked) is None
    assert row(store, family)["state"] == "retired"
    assert (
        store._require_conn()
        .execute("SELECT count(*) FROM push_registrations WHERE state='active'")
        .fetchone()[0]
        == 1
    )  # inert consumes D24, not D25
    purge(store, key=key, available=True, kids=frozenset({"kid-a"}))
    assert row(store, inert)["state"] == "expired"


def test_unreadable_key_skips_only_hash_check(store):
    for name in ("valid", "expired", "removed"):
        seed_device(store, name)
    valid = seed_row(store, "valid")
    expired = seed_row(store, "expired", expires=NOW)
    removed = seed_row(store, "removed", kid="old")
    before = tuple(row(store, valid))
    purge(store, key=None)
    assert tuple(row(store, valid)) == before
    assert row(store, expired)["state"] == row(store, removed)["state"] == "expired"


def test_hash_mismatch_still_expires_while_push_is_off(store):
    seed_device(store, "dev")
    digest = seed_row(store, "dev", kid="removed")
    purge(store, key=b"z" * 32, available=False, kids=frozenset())
    assert row(store, digest)["state"] == "expired"
    assert generation(store, "dev") == 2


def test_reversible_owner_denial_does_not_retire_registration(store):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    assert store.set_owner_controls("dev", allowed=False, now=NOW)
    before = tuple(row(store, digest))
    purge(store, key=KEY)
    assert tuple(row(store, digest)) == before
    assert store.set_owner_controls("dev", allowed=True, now=NOW + 1)
    assert generation(store, "dev") == 1


def test_retained_age_caps_and_generation_survives_eviction(store):
    seed_device(store, "dev")
    old = seed_row(store, "dev", state="retired", changed=NOW - 30 * 86400)
    retained = [
        seed_row(store, "dev", number=i, state="provider_gone", changed=NOW + i)
        for i in range(2, 12)
    ]
    purge(store, key=None)
    assert row(store, old) is None
    assert [digest for digest in retained if row(store, digest)] == retained[-8:]
    assert generation(store, "dev") == 1
    assert all(row(store, digest)["sealed"] is None for digest in retained[-8:])


def test_retained_global_cap_is_oldest_first_after_per_device_cap(store):
    for device_number in range(129):
        name = seed_device(store, f"dev-{device_number:03}")
        for i in range(8):
            seed_row(
                store, name, number=i + 1, state="expired", changed=NOW + device_number * 8 + i
            )
    purge(store, key=None)
    conn = store._require_conn()
    assert conn.execute("SELECT count(*) FROM push_registrations").fetchone()[0] == 1024
    assert (
        conn.execute("SELECT min(state_changed_at) FROM push_registrations").fetchone()[0]
        == NOW + 8
    )
    assert conn.execute("SELECT count(*) FROM push_device_generations").fetchone()[0] == 129


def test_active_and_generation_caps_refuse_without_writes_but_allow_existing(store):
    for n in range(256):
        name = seed_device(store, f"dev-{n}")
        if n < 64:
            seed_row(store, name)
        else:
            with store.transaction() as conn:
                store.advance_push_generation_in(conn, name)
    seed_device(store, "new")
    with pytest.raises(HmpError) as exc, store.transaction() as conn:
        store.check_push_capacity_in(conn, "new")
    assert exc.value.extras == {"why": "push_capacity"}
    assert generation(store, "new") == 0
    with pytest.raises(HmpError) as exc, store.transaction() as conn:
        store.advance_push_generation_in(conn, "new")  # no-generation DELETE
    assert exc.value.extras == {"why": "push_capacity"}
    with store.transaction() as conn:
        store.check_push_capacity_in(conn, "dev-0")  # replacement is never capacity-refused
    store.set_device_state("dev-0", "REVOKED")
    purge(store, key=None, available=False)
    with store.transaction() as conn:
        assert store.advance_push_generation_in(conn, "new") == 1


def test_generation_overflow_rolls_back_without_decreasing_or_creating(store):
    seed_device(store, "dev")
    digest = seed_row(store, "dev")
    store._require_conn().execute("UPDATE push_device_generations SET generation=?", (2**53 - 1,))
    before = tuple(row(store, digest))
    with pytest.raises(HmpError) as exc:
        purge(store, key=None, kids=frozenset())
    assert (exc.value.http, exc.value.code, exc.value.extras) == (503, ErrorCode.OTHER, {})
    assert generation(store, "dev") == 2**53 - 1
    assert tuple(row(store, digest)) == before


def test_post_commit_cleanup_does_not_enforce_retained_cap_or_expire_inert_rows(store):
    seed_device(store, "dev")
    for i in range(10):
        seed_row(store, "dev", number=i + 1, state="retired")
    active = seed_row(store, "dev", number=11, kid="removed", expires=NOW - 1)
    assert store.cleanup_push_after_commit(now=NOW)
    assert row(store, active)["state"] == "active"
    assert (
        store._require_conn().execute("SELECT count(*) FROM push_registrations").fetchone()[0] == 11
    )


def test_cleanup_failure_and_broken_log_handler_do_not_escape(store, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("prohibited-secret-marker")

    monkeypatch.setattr(store, "_retire_ineligible_push_in", fail)
    monkeypatch.setattr("hmp_plugin.store.log_event", fail)
    assert store.cleanup_push_after_commit(now=NOW) is False
    assert not store._require_conn().in_transaction


@pytest.mark.parametrize("cause", ["revoked", "family", "pending", "epoch"])
def test_cleanup_retires_without_deleting_generation_and_audits_only_prefix(store, cause):
    name = seed_device(store, "dev_audit_secret_suffix")
    digest = seed_row(store, name)
    if cause == "family":
        store.revoke_family("family-" + name, NOW)
    elif cause == "epoch":
        store._require_conn().execute("UPDATE meta SET store_revocation_epoch=1")
    else:
        store.set_device_state(name, "REVOKED" if cause == "revoked" else "PENDING")
    assert store.cleanup_push_after_commit(now=NOW)
    value = row(store, digest)
    assert value["state"] == "retired"
    assert all(value[k] is None for k in ("sealed", "request_hash", "body_hash"))
    assert generation(store, name) == 2
    events = [r for r in store.audit_events() if r["event"] == "push_retire"]
    assert [tuple(r) for r in events] == [(NOW, "push_retire", name[:8], "retired")]
    assert "secret_suffix" not in repr([tuple(r) for r in events])
    assert store.cleanup_push_after_commit(now=NOW + 1)
    assert generation(store, name) == 2
    assert len([r for r in store.audit_events() if r["event"] == "push_retire"]) == 1


class RowBudgetConnection(sqlite3.Connection):
    """Observe actual SQLite row counts between each BEGIN and COMMIT."""

    def execute(self, sql, parameters=()):
        if sql == "BEGIN IMMEDIATE":
            self.changed = 0
        cursor = super().execute(sql, parameters)
        if sql.startswith(("DELETE FROM push_", "UPDATE push_")):
            self.changed += cursor.rowcount
        if sql == "COMMIT":
            self.budgets.append(self.changed)
        return cursor


def observe_row_budgets(store):
    path = store._path
    store.close()
    conn = sqlite3.connect(
        str(path), isolation_level=None, check_same_thread=False, factory=RowBudgetConnection
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.budgets = []
    store._conn = conn
    return conn


def test_revoked_backlog_is_purge_only_and_each_transaction_is_bounded(store):
    # Legal historical shape after skipped/failed cleanup: REVOKED G rows are
    # outside D28. A stopped listener can accumulate more than either batch cap.
    for n in range(1100):
        name = seed_device(store, f"revoked-{n}", state="REVOKED")
        seed_row(store, name, state="retired", number=1)
        seed_row(store, name, state="retired", number=2)
    current = seed_device(store, "current-live")
    live = seed_row(store, current)
    conn = observe_row_budgets(store)
    assert store.cleanup_push_after_commit(now=NOW)
    assert conn.budgets == [0]  # no global deletes or non-active wipes in cause cleanup
    assert conn.execute("SELECT count(*) FROM push_device_generations").fetchone()[0] == 1101
    assert conn.execute("SELECT count(*) FROM push_registrations").fetchone()[0] == 2201
    conn.budgets.clear()
    purge(store, key=None, available=False)
    assert [n for n in conn.budgets if n] == [1024, 1024, 152, 256, 256, 256, 256, 76]
    assert conn.execute("SELECT count(*) FROM push_registrations").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM push_device_generations").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM devices WHERE state='REVOKED'").fetchone()[0] == 1100
    assert row(store, live)["state"] == "active" and generation(store, current) == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_retained_wipe_and_age_deletion_use_separate_bounded_transactions(store):
    name = seed_device(store, "retained-backlog")
    # Deliberately over-cap fixture tests the defensive batching, not a valid PUT.
    for n in range(1100):
        seed_row(store, name, number=n + 1, state="retired", changed=NOW - 30 * 86400)
    conn = observe_row_budgets(store)
    purge(store, key=None, available=False)
    assert [n for n in conn.budgets if n] == [1024, 76, 1024, 76]
    assert conn.execute("SELECT count(*) FROM push_registrations").fetchone()[0] == 0
    assert generation(store, name) == 1


def test_per_device_eviction_finishes_before_global_ranking(store):
    first = seed_device(store, "protected")
    protected = [seed_row(store, first, state="retired", number=n + 1) for n in range(8)]
    second = seed_device(store, "overflowing")
    extra = [
        seed_row(store, second, state="retired", number=n + 1, changed=NOW + n + 1)
        for n in range(1025)
    ]
    purge(store, key=None)
    # Global ranking before per-device trimming would wrongly evict protected history.
    assert all(row(store, digest) is not None for digest in protected)
    assert [digest for digest in extra if row(store, digest)] == extra[-8:]


def test_revoked_batch_cannot_bypass_active_retirement(store):
    seed_device(store, "revoked-device")
    digest = seed_row(store, "revoked-device")
    store.set_device_state("revoked-device", "REVOKED")
    with store.transaction() as conn:
        assert store._delete_revoked_push_batch_in(conn) == 0
    assert row(store, digest)["state"] == "active"
    assert generation(store, "revoked-device") == 1
    purge(store, key=None, available=False)
    assert row(store, digest) is None
    assert generation(store, "revoked-device") == 0
    audit = [r for r in store.audit_events() if r["event"] == "push_retire"]
    assert len(audit) == 1
    assert tuple(audit[0]) == (NOW, "push_retire", "revoked-", "retired")
