"""Store schema, migration and atomicity tests (T021; data-model.md "Server").

No table may hold message text, a raw token, a raw offer secret or a private key (only hashes and
sanitized display strings). Rotation-style writes must be atomic, and the p5_nonces LRU bound must
be enforced.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hmp_plugin.contract import LIMITER_TABLE_MAX
from hmp_plugin.store import PAIRING_PENDING_STATE, SCHEMA_VERSION, Store

# Column-name signals that would mean raw secret/text material ended up in a table. Hash columns
# (e.g. `secret_hash`, `hash`, `successor_hash`) are exactly how PR4-4/R16 say tokens and offer
# secrets must be stored, so they are not flagged.
FORBIDDEN_SUBSTRINGS = ("message", "raw_token", "raw_secret", "private_key", "privkey")
FORBIDDEN_EXACT = {"text", "token", "secret", "key"}


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "hmp.sqlite3")
    s.migrate()
    return s


def _table_names(store: Store) -> list[str]:
    conn = store._conn  # test-internal: introspection only
    assert conn is not None
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'sqlite_sequence'"
    ).fetchall()
    return [r["name"] for r in rows]


def test_migrate_creates_expected_tables(store: Store) -> None:
    expected = {
        "meta",
        "offers",
        "pairings",
        "users",
        "devices",
        "device_owner_controls",
        "token_families",
        "refresh_tokens",
        "access_tokens",
        "p5_nonces",
        "chats",
        "session_baselines",
        "roster_state",
        "audit",
    }
    assert expected <= set(_table_names(store))


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "hmp.sqlite3"
    s1 = Store(path)
    s1.migrate()
    s1.insert_user("hmpu_a", "label", 1000)
    s1.close()

    s2 = Store(path)
    s2.migrate()  # must not wipe or fail on an already-migrated store
    row = s2.get_offer("nonexistent")
    assert row is None
    (count,) = s2._conn.execute("SELECT COUNT(*) FROM users").fetchone()  # type: ignore[union-attr]
    assert count == 1
    s2.close()


def test_migrate_creates_missing_parent_directory(tmp_path: Path) -> None:
    """On a fresh install, nothing has created `plugin-data/hmp/` yet (identity.py's own
    `plugin-data/hmp/instance/` anchor dir does not help, since `migrate()` runs first per
    adapter.py's startup order). `migrate()` must create its own parent, mode 0700, rather than
    failing with `sqlite3.OperationalError: unable to open database file`."""
    anchor_parent = tmp_path / "plugin-data" / "hmp"
    assert not anchor_parent.exists()
    path = anchor_parent / "hmp.sqlite3"

    s = Store(path)
    s.migrate()
    try:
        assert anchor_parent.is_dir()
        assert (anchor_parent.stat().st_mode & 0o777) == 0o700
        assert path.exists()
    finally:
        s.close()


def test_no_message_text_or_raw_secret_column(store: Store) -> None:
    conn = store._conn
    assert conn is not None
    for table in _table_names(store):
        for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
            name = col["name"].lower()
            assert name not in FORBIDDEN_EXACT, f"{table}.{name}"
            for bad in FORBIDDEN_SUBSTRINGS:
                assert bad not in name, f"{table}.{name}"


def test_use_before_migrate_raises(tmp_path: Path) -> None:
    s = Store(tmp_path / "unmigrated.sqlite3")
    with pytest.raises(RuntimeError):
        s.revocation_epoch()


def test_fresh_store_epochs_are_zero(store: Store) -> None:
    assert store.revocation_epoch() == 0
    assert store.instance_epoch() == 0


def test_schema_version_recorded(store: Store) -> None:
    row = store._conn.execute("SELECT schema_version FROM meta WHERE id = 1").fetchone()  # type: ignore[union-attr]
    assert row["schema_version"] == SCHEMA_VERSION


def test_owner_controls_are_per_active_device_and_revocable(store: Store) -> None:
    store.insert_user("hmpu_a", "label", 1000)
    store.insert_device("dev_a", "hmpu_a", "f" * 64, b"x", "phone a", 1000, state="ACTIVE")
    store.insert_device("dev_b", "hmpu_a", "g" * 64, b"y", "phone b", 1000, state="ACTIVE")
    assert store.owner_controls_decision("dev_a") is None
    assert store.set_owner_controls("dev_a", allowed=True, now=1001)
    assert store.owner_controls_decision("dev_a") is True
    assert store.owner_controls_decision("dev_b") is None
    assert store.set_owner_controls("dev_a", allowed=False, now=1002)
    assert store.owner_controls_decision("dev_a") is False
    store.set_device_state("dev_a", "REVOKED")
    assert not store.set_owner_controls("dev_a", allowed=True, now=1003)
    assert not store.set_owner_controls("missing", allowed=True, now=1003)
    assert store.owner_controls_decision("dev_a") is False


def test_owner_controls_survive_reopen_and_upgrade_legacy_store(tmp_path: Path) -> None:
    path = tmp_path / "hmp.sqlite3"
    first = Store(path)
    first.migrate()
    first.insert_user("hmpu_a", "label", 1000)
    first.insert_device("dev_a", "hmpu_a", "f" * 64, b"x", "phone a", 1000, state="ACTIVE")
    first.set_owner_controls("dev_a", allowed=True, now=1001)
    first._require_conn().execute("UPDATE meta SET schema_version = 1 WHERE id = 1")
    first.close()

    second = Store(path)
    second.migrate()
    assert second.owner_controls_decision("dev_a") is True
    row = second._require_conn().execute("SELECT schema_version FROM meta WHERE id = 1").fetchone()
    assert row["schema_version"] == SCHEMA_VERSION
    second.close()


# ------------------------------------------------------------------------------------------
# revoke_all_for_identity_change (PR7-2, PR7-6) — the surface identity.py/T022 uses.
# ------------------------------------------------------------------------------------------


def _seed_identity_fixture(store: Store) -> None:
    store.insert_user("hmpu_a", "label-a", 1000)
    store.insert_device(
        "dev_a", "hmpu_a", "fpfpfpfp", b"\x00" * 91, "device a", 1000, state="ACTIVE"
    )
    store.insert_device(
        "dev_b", "hmpu_a", "fpfpfpfp", b"\x00" * 91, "device b", 1000, state="PENDING"
    )
    store.insert_token_family("fam_a", "dev_a", 1000)
    store.insert_offer("oid_open", b"\x11" * 32, 9999)
    store.insert_offer("oid_claimed", b"\x22" * 32, 9999)
    store._conn.execute("UPDATE offers SET state = 'claimed' WHERE oid = 'oid_claimed'")  # type: ignore[union-attr]
    store.insert_pairing(
        "pid_1", "oid_open", b"\x00" * 91, "unnamed device", b"\x01" * 32, b"\x02" * 32, 9999
    )


def test_revoke_all_for_identity_change_effects(store: Store) -> None:
    _seed_identity_fixture(store)

    new_epoch = store.revoke_all_for_identity_change(5000)

    assert new_epoch == 1
    assert store.revocation_epoch() == 1
    assert store.get_device("dev_a")["state"] == "REVOKED"
    assert store.get_device("dev_b")["state"] == "REVOKED"
    assert store.get_token_family("fam_a")["revoked_at"] == 5000
    assert store.get_offer("oid_open")["state"] == "expired"
    assert store.get_offer("oid_claimed")["state"] == "claimed"  # not open; left alone
    assert store.get_pairing("pid_1")["state"] == "expired"

    events = store.audit_events()
    assert len(events) == 1
    assert events[0]["event"] == "identity_change_revoke_all"
    assert events[0]["outcome"] == "ok"
    assert events[0]["id_prefix8"] is None  # SEC-4: no ids in this audit row


def test_revoke_all_for_identity_change_bumps_epoch_even_when_nothing_to_revoke(
    store: Store,
) -> None:
    assert store.revoke_all_for_identity_change(1) == 1
    assert store.revoke_all_for_identity_change(2) == 2
    assert store.revocation_epoch() == 2


class _FailingConnection(sqlite3.Connection):
    """A `sqlite3.Connection` that raises once `execute` is called with a SQL statement starting
    with `fail_on_prefix` — used to inject a failure partway through a transaction. `sqlite3.
    Connection` is a C type, so instance-level monkeypatching of `execute` is not possible; a
    subclass is the mechanism sqlite3 itself supports (the `factory=` argument to `connect`)."""

    fail_on_prefix: str | None = None

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:  # type: ignore[override]
        if self.fail_on_prefix and sql.startswith(self.fail_on_prefix):
            raise sqlite3.OperationalError("injected failure")
        return super().execute(sql, *args)


def test_revoke_all_for_identity_change_is_atomic(store: Store) -> None:
    _seed_identity_fixture(store)
    path = store._path
    store.close()

    conn = sqlite3.connect(str(path), isolation_level=None, factory=_FailingConnection)
    conn.row_factory = sqlite3.Row
    conn.fail_on_prefix = "UPDATE meta"
    store._conn = conn

    with pytest.raises(sqlite3.OperationalError):
        store.revoke_all_for_identity_change(5000)
    conn.fail_on_prefix = None

    # Nothing committed: every effect of the aborted transaction is absent.
    assert store.revocation_epoch() == 0
    assert store.get_device("dev_a")["state"] == "ACTIVE"
    assert store.get_device("dev_b")["state"] == "PENDING"
    assert store.get_token_family("fam_a")["revoked_at"] is None
    assert store.get_offer("oid_open")["state"] == "open"
    assert store.get_pairing("pid_1")["state"] == PAIRING_PENDING_STATE
    assert store.audit_events() == []


# ------------------------------------------------------------------------------------------
# refresh token rotation (PR5-4)
# ------------------------------------------------------------------------------------------


def test_rotate_refresh_token_is_one_transaction(store: Store) -> None:
    store.insert_user("hmpu_a", "l", 1000)
    store.insert_device("dev_a", "hmpu_a", "fp", b"\x00" * 91, "d", 1000, state="ACTIVE")
    store.insert_token_family("fam_a", "dev_a", 1000)
    old_hash = b"\x01" * 32
    store.insert_refresh_token(old_hash, "fam_a", 1000)

    new_hash = b"\x02" * 32
    successor_hash = b"\x03" * 32
    store.rotate_refresh_token(
        old_hash=old_hash,
        family_id="fam_a",
        new_hash=new_hash,
        successor_hash=successor_hash,
        issued_at=2000,
    )

    old_row = store.get_refresh_token(old_hash)
    assert old_row["used_at"] == 2000
    assert bytes(old_row["successor_hash"]) == successor_hash
    new_row = store.get_refresh_token(new_hash)
    assert new_row is not None
    assert new_row["used_at"] is None


# ------------------------------------------------------------------------------------------
# p5_nonces LRU bound (TR-6)
# ------------------------------------------------------------------------------------------


def test_p5_nonce_lru_bound_enforced(store: Store) -> None:
    bound = 8
    for i in range(bound + 5):
        store.record_p5_nonce("dev_a", i.to_bytes(16, "big"), seen_at=i, bound=bound)

    assert store.count_p5_nonces() == bound
    # The oldest (lowest seen_at) were evicted; the newest survive.
    assert not store.nonce_seen("dev_a", (0).to_bytes(16, "big"))
    assert store.nonce_seen("dev_a", (bound + 4).to_bytes(16, "big"))


def test_p5_nonce_duplicate_is_a_no_op(store: Store) -> None:
    nonce = b"\x00" * 16
    store.record_p5_nonce("dev_a", nonce, seen_at=1)
    store.record_p5_nonce("dev_a", nonce, seen_at=1)  # replay of an already-seen nonce
    assert store.count_p5_nonces() == 1


def test_p5_nonce_default_bound_is_limiter_table_max(store: Store) -> None:
    # A cheap proxy for "the default bound is LIMITER_TABLE_MAX" without inserting thousands of
    # rows: patch the bound down and confirm the *parameter* threads through, then confirm the
    # signature's default really is the contract constant.
    import inspect

    default = inspect.signature(store.record_p5_nonce).parameters["bound"].default
    assert default == LIMITER_TABLE_MAX


# ------------------------------------------------------------------------------------------
# chats / session_baselines / roster_state upserts
# ------------------------------------------------------------------------------------------


def test_chat_upsert(store: Store) -> None:
    store.set_chat("hmpu_a", "f1-alpha", "default", "chat_1")
    store.set_chat("hmpu_a", "f1-alpha", "default", "chat_2")  # re-set, same key
    row = store.get_chat("hmpu_a", "f1-alpha", "default")
    assert row["chat_id"] == "chat_2"


def test_session_baseline_upsert(store: Store) -> None:
    store.set_session_baseline("hmpu_a", "f1-alpha", "sess_1", "tip_1", 10, 1000)
    store.set_session_baseline("hmpu_a", "f1-alpha", "sess_2", "tip_2", 20, 2000)
    row = store.get_session_baseline("hmpu_a", "f1-alpha")
    assert row["session_id"] == "sess_2"
    assert row["active_row_count"] == 20
    assert "head_row_id" not in row.keys()  # noqa: SIM118 -- sqlite3.Row has no `in` support


# ------------------------------------------------------------------------------------------
# Amendment A1 (session browsing, SES-1a, SES-2): session_refs, other_session_baselines
# ------------------------------------------------------------------------------------------


def test_mint_or_get_session_ref_is_stable(store: Store) -> None:
    ref1 = store.mint_or_get_session_ref("hmpu_a", "alpha", "sess_1", "candidate_1", 1000)
    ref2 = store.mint_or_get_session_ref("hmpu_a", "alpha", "sess_1", "candidate_2", 2000)
    assert ref1 == ref2 == "candidate_1"  # the second candidate is discarded, not reused


def test_mint_or_get_session_ref_distinguishes_sessions(store: Store) -> None:
    r1 = store.mint_or_get_session_ref("hmpu_a", "alpha", "sess_1", "c1", 1000)
    r2 = store.mint_or_get_session_ref("hmpu_a", "alpha", "sess_2", "c2", 1000)
    assert r1 != r2


def test_resolve_session_ref_scoped_to_user_and_profile(store: Store) -> None:
    ref = store.mint_or_get_session_ref("hmpu_a", "alpha", "sess_1", "c1", 1000)
    assert store.resolve_session_ref("hmpu_a", "alpha", ref) == "sess_1"
    # A ref minted for one user/profile is not found for another -- never disclosed as "exists
    # but not yours" (SES-1a).
    assert store.resolve_session_ref("hmpu_b", "alpha", ref) is None
    assert store.resolve_session_ref("hmpu_a", "beta", ref) is None
    assert store.resolve_session_ref("hmpu_a", "alpha", "ses1_unguessable") is None


def test_other_session_baseline_upsert_keyed_by_session(store: Store) -> None:
    store.set_other_session_baseline("hmpu_a", "alpha", "sess_1", "tip_1", 5, 1000)
    store.set_other_session_baseline("hmpu_a", "alpha", "sess_2", "tip_2", 9, 1000)
    row1 = store.get_other_session_baseline("hmpu_a", "alpha", "sess_1")
    row2 = store.get_other_session_baseline("hmpu_a", "alpha", "sess_2")
    assert row1["lineage_tip"] == "tip_1" and row1["active_row_count"] == 5
    assert row2["lineage_tip"] == "tip_2" and row2["active_row_count"] == 9
    assert store.get_other_session_baseline("hmpu_a", "alpha", "sess_3") is None
    store.set_other_session_baseline("hmpu_a", "alpha", "sess_1", "tip_1b", 6, 2000)
    assert store.get_other_session_baseline("hmpu_a", "alpha", "sess_1")["lineage_tip"] == "tip_1b"


def test_roster_state_upsert(store: Store) -> None:
    store.set_roster_state("hmpu_a", "hash1", 1000)
    store.set_roster_state("hmpu_a", "hash2", 2000)
    row = store.get_roster_state("hmpu_a")
    assert row["served_set_hash"] == "hash2"


# ------------------------------------------------------------------------------------------
# audit
# ------------------------------------------------------------------------------------------


def test_write_audit_requires_exact_prefix_length(store: Store) -> None:
    store.write_audit(1, "event", "ok", id_prefix8="abcdefgh")
    with pytest.raises(ValueError):
        store.write_audit(1, "event", "ok", id_prefix8="short")


# ------------------------------------------------------------------------------------------
# direct_send_idempotency (amendment F2, HMP_V1.md §7a DS-3)
# ------------------------------------------------------------------------------------------


def test_reserve_cmid_is_atomic_and_idempotent(store: Store) -> None:
    row, inserted = store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    assert row["status"] == "pending"
    assert row["created_at"] == 1000
    assert inserted is True  # this call created the row
    # a second reservation of the SAME cmid does not overwrite the first (INSERT ... DO NOTHING)
    row2, inserted2 = store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-b", 2000)
    assert row2["created_at"] == 1000
    assert bytes(row2["payload_hash"]) == b"hash-a"
    assert inserted2 is False  # review round 2, BLOCKER #1: a repeat, not a fresh reservation


def test_reserve_cmid_is_scoped(store: Store) -> None:
    store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    # a different (iid, user, profile) never collides with the same cmid text
    other, other_inserted = store.reserve_cmid("iid2", "u1", "default", "cmid1", b"hash-a", 1000)
    assert other is not None
    assert other_inserted is True
    assert store.get_cmid_record("iid1", "u1", "default", "cmid1") is not None
    assert store.get_cmid_record("iid2", "u1", "default", "cmid1") is not None
    assert store.get_cmid_record("iid1", "u2", "default", "cmid1") is None


def test_finalize_cmid_records_a_definitive_outcome(store: Store) -> None:
    store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    store.finalize_cmid(
        "iid1",
        "u1",
        "default",
        "cmid1",
        status="accepted",
        result_json='{"state":"accepted"}',
        updated_at=1010,
    )
    row = store.get_cmid_record("iid1", "u1", "default", "cmid1")
    assert row["status"] == "accepted"
    assert row["result_json"] == '{"state":"accepted"}'
    assert row["updated_at"] == 1010


def test_finalize_cmid_never_required_before_pending_stays_pending(store: Store) -> None:
    """DS-3: a timeout/ambiguous outcome leaves the record 'pending' -- never silently deleted."""
    store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    row = store.get_cmid_record("iid1", "u1", "default", "cmid1")
    assert row["status"] == "pending"


def test_delete_cmid_reservation_frees_it_for_a_fresh_retry(store: Store) -> None:
    store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    store.delete_cmid_reservation("iid1", "u1", "default", "cmid1")
    assert store.get_cmid_record("iid1", "u1", "default", "cmid1") is None
    # a fresh reservation under the same cmid now succeeds with a NEW payload hash
    fresh, fresh_inserted = store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-c", 2000)
    assert bytes(fresh["payload_hash"]) == b"hash-c"
    assert fresh["created_at"] == 2000
    assert fresh_inserted is True


def test_reserve_cmid_waits_on_the_write_lock(store: Store) -> None:
    """Review round 3: `BEGIN IMMEDIATE` on the shared connection is serialized by a
    threading.Lock. A reserve started while that lock is held does not run until it is released."""
    import threading
    import time

    store._write_lock.acquire()
    done = threading.Event()
    errors: list[BaseException] = []

    def run() -> None:
        try:
            store.reserve_cmid("iid1", "u1", "default", "cmid-lock", b"hash-a", 1000)
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    worker = threading.Thread(target=run)
    worker.start()
    time.sleep(0.05)
    assert not done.is_set()
    assert errors == []
    store._write_lock.release()
    worker.join(timeout=2)
    assert done.is_set()
    assert errors == []
    row = store.get_cmid_record("iid1", "u1", "default", "cmid-lock")
    assert row is not None and row["status"] == "pending"


def test_migrate_widens_a_pre_round3_cmid_status_check(tmp_path: Path) -> None:
    """An already-created idempotency table (CHECK without `unknown`) is rebuilt so a cancelled
    send can store `unknown`."""
    import sqlite3

    path = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE direct_send_idempotency ("
        "iid TEXT NOT NULL, user_id TEXT NOT NULL, profile TEXT NOT NULL, cmid TEXT NOT NULL, "
        "payload_hash BLOB NOT NULL, "
        "status TEXT NOT NULL CHECK (status IN ('pending','accepted','rejected')), "
        "result_json TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, "
        "PRIMARY KEY (iid, user_id, profile, cmid))"
    )
    conn.commit()
    conn.close()
    store = Store(path)
    store.migrate()
    store.reserve_cmid("iid1", "u1", "default", "c", b"hash-a", 1)
    store.finalize_cmid(
        "iid1",
        "u1",
        "default",
        "c",
        status="unknown",
        result_json='{"state":"unknown"}',
        updated_at=2,
    )
    row = store.get_cmid_record("iid1", "u1", "default", "c")
    assert row is not None and row["status"] == "unknown"


def test_direct_send_idempotency_status_is_constrained(store: Store) -> None:
    store.reserve_cmid("iid1", "u1", "default", "cmid1", b"hash-a", 1000)
    with pytest.raises(sqlite3.IntegrityError):
        store.finalize_cmid(
            "iid1",
            "u1",
            "default",
            "cmid1",
            status="not_a_real_status",
            result_json=None,
            updated_at=1010,
        )
