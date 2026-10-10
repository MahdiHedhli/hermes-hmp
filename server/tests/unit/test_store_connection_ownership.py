"""Shared-connection authority and durability regressions for the AR1 Store boundary.

The public-method inventory is exact; these tests exercise the cross-thread SQL boundary, not
an HTTP caller's authority to decide a request. No external provider or clock is used.
"""
from __future__ import annotations

import base64
import inspect
import sqlite3
import threading
from pathlib import Path

import pytest

from hmp_plugin.store import SCHEMA_VERSION, Store
from hmp_plugin.auth import Authenticator
from hmp_plugin.contract import ErrorCode, HmpError

WRITERS = frozenset({
    "revoke_all_for_identity_change", "insert_offer", "insert_pairing", "record_p4_ts",
    "insert_user", "insert_device", "set_owner_controls", "set_device_state",
    "insert_token_family", "revoke_family", "revoke_families_for_device",
    "insert_refresh_token", "insert_access_token", "rotate_refresh_token",
    "record_p5_nonce", "set_chat", "set_session_baseline", "mint_or_get_session_ref",
    "set_other_session_baseline", "reserve_cmid", "delete_cmid_reservation",
    "finalize_cmid", "reserve_phone_cmid", "finalize_phone_cmid", "set_roster_state",
    "set_authorize_cooldown", "write_audit",
})
READERS = frozenset({
    "request_schema_ready", "instance_epoch", "revocation_epoch", "get_offer",
    "get_pairing", "get_device", "owner_controls_decision",
    "readiness_owner_controls_value", "get_token_family", "get_refresh_token",
    "get_access_token", "nonce_seen", "count_p5_nonces", "get_chat",
    "get_session_baseline", "resolve_session_ref", "get_other_session_baseline",
    "get_cmid_record", "get_roster_state", "get_authorize_cooldown", "audit_events",
})
EXPLICIT_WRITERS = frozenset({
    "revoke_all_for_identity_change", "insert_device", "set_owner_controls",
    "set_device_state", "insert_token_family", "revoke_family",
    "revoke_families_for_device", "rotate_refresh_token", "mint_or_get_session_ref",
    "reserve_cmid", "reserve_phone_cmid",
})
EXPLICIT_READERS = frozenset({
    "request_schema_ready", "owner_controls_decision", "readiness_owner_controls_value",
})


def _store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "owner.sqlite3")
    s.migrate()
    s.insert_user("user", "User", 1)
    s.insert_device("device", "user", "fingerprint", b"key", "Phone", 1, state="ACTIVE")
    return s


def _separate_controls(path: Path) -> int | None:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT allowed FROM device_owner_controls WHERE device_id = 'device'"
        ).fetchone()
    return None if row is None else row[0]


def test_exact_public_inventory_has_owner_boundary() -> None:
    assert len(WRITERS) == 27 and len(READERS) == 21
    assert len(WRITERS - EXPLICIT_WRITERS) == 16
    assert len(READERS - EXPLICIT_READERS) == 18
    for name in WRITERS - EXPLICIT_WRITERS:
        assert getattr(Store, name).__wrapped__  # explicit @_owned_write on this exact API
    for name in READERS - EXPLICIT_READERS:
        assert getattr(Store, name).__wrapped__  # explicit @_owned_read on this exact API
    for name in EXPLICIT_WRITERS:
        source = inspect.getsource(getattr(Store, name))
        assert "with self._serialized_writer() as conn:" in source
    for name in EXPLICIT_READERS:
        source = inspect.getsource(getattr(Store, name))
        assert "with self._authority_reader()" in source


@pytest.mark.parametrize("commit", [False, True])
def test_foreign_controls_reader_waits_for_committed_state(tmp_path: Path, commit: bool) -> None:
    store = _store(tmp_path)
    started = threading.Event()
    done = threading.Event()
    values: list[tuple[bool | None, int | None]] = []
    errors: list[BaseException] = []

    def read() -> None:
        started.set()
        try:
            values.append((store.owner_controls_decision("device"),
                           store.readiness_owner_controls_value("device")))
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    try:
        with pytest.raises(RuntimeError, match="abort") if not commit else _no_exception():
            with store.transaction() as conn:
                conn.execute("INSERT INTO device_owner_controls VALUES ('device', 1, 2)")
                worker = threading.Thread(target=read)
                worker.start()
                assert started.wait(2)
                assert not done.wait(0.05)
                # The independent connection cannot observe this tentative authority either.
                assert _separate_controls(store._path) is None
                if not commit:
                    raise RuntimeError("abort")
        worker.join(timeout=2)
        assert not worker.is_alive() and done.is_set() and not errors
        expected = (True, 1) if commit else (None, None)
        assert values == [expected]
        assert _separate_controls(store._path) == (1 if commit else None)
    finally:
        store.close()


class _no_exception:
    def __enter__(self):
        return None
    def __exit__(self, *args):
        return False


def test_foreign_nonce_writer_survives_request_rollback(tmp_path: Path) -> None:
    store = _store(tmp_path)
    started = threading.Event()
    done = threading.Event()
    errors: list[BaseException] = []
    nonce = b"n" * 16

    def write() -> None:
        started.set()
        try:
            store.record_p5_nonce("device", nonce, 3)
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    try:
        with pytest.raises(RuntimeError, match="abort"):
            with store.transaction() as conn:
                conn.execute("INSERT INTO device_owner_controls VALUES ('device', 1, 2)")
                worker = threading.Thread(target=write)
                worker.start()
                assert started.wait(2)
                assert not done.wait(0.05)
                raise RuntimeError("abort")
        worker.join(timeout=2)
        assert not worker.is_alive() and done.is_set() and not errors
        assert store.nonce_seen("device", nonce)
        assert _separate_controls(store._path) is None
        with sqlite3.connect(store._path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM p5_nonces WHERE nonce = ?", (nonce,)).fetchone()[0] == 1
    finally:
        store.close()


def test_owner_reentry_joins_without_nested_begin_and_repeated_migration_reuses_conn(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        original = store._conn
        store.migrate()
        assert store._conn is original
        with store.transaction():
            store.insert_token_family("fam", "device", 2)
            assert store.get_token_family("fam") is not None
            assert store.epoch_authority_snapshot() == (0, 0)
            with pytest.raises(RuntimeError, match="nested"):
                with store.transaction():
                    pass
        assert store.get_token_family("fam") is not None
    finally:
        store.close()


def test_access_authority_snapshot_is_single_joined_statement(tmp_path: Path) -> None:
    store = _store(tmp_path)
    token = b"a" * 32
    try:
        store.insert_token_family("fam", "device", 2)
        store.insert_access_token(token, "fam", "device", "iid", 100)
        statements: list[str] = []
        assert store._conn is not None
        store._conn.set_trace_callback(statements.append)
        row = store.access_authority_snapshot(token)
        store._conn.set_trace_callback(None)
        assert row is not None
        assert row["access_device_id"] == row["family_device_id"] == row["device_found_id"]
        assert row["device_state"] == "ACTIVE"
        assert len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) == 1
        store.revoke_family("fam", 3)
        assert store.access_authority_snapshot(token)["family_revoked_at"] == 3
    finally:
        store.close()


def _seed_full(store: Store) -> None:
    store.insert_offer("offer", b"s" * 32, 100)
    store.insert_pairing("pair", "offer", b"pub", "Phone", b"n" * 16, b"i" * 16, 100)
    store.insert_token_family("family", "device", 2)
    store.insert_refresh_token(b"r" * 32, "family", 2)
    store.insert_access_token(b"a" * 32, "family", "device", "iid", 100)
    store.record_p5_nonce("device", b"old", 2)
    store.set_chat("user", "default", "conv", "chat")
    store.set_session_baseline("user", "default", "session", "tip", 1, 2)
    store.mint_or_get_session_ref("user", "default", "session", "oldref", 2)
    store.set_other_session_baseline("user", "default", "other", "tip", 1, 2)
    store.reserve_cmid("iid", "user", "default", "existing", b"h", 2)
    store.reserve_phone_cmid("iid", "user", "default", "phone", b"h", 2)
    store.set_roster_state("user", "old", 2)
    store.set_authorize_cooldown("user", "default", 2)
    store.write_audit(2, "seed", "ok")


def _read_public(store: Store, name: str):
    args = {
        "request_schema_ready": (), "instance_epoch": (), "revocation_epoch": (),
        "get_offer": ("offer",), "get_pairing": ("pair",), "get_device": ("device",),
        "owner_controls_decision": ("device",),
        "readiness_owner_controls_value": ("device",),
        "get_token_family": ("family",), "get_refresh_token": (b"r" * 32,),
        "get_access_token": (b"a" * 32,), "nonce_seen": ("device", b"old"),
        "count_p5_nonces": (), "get_chat": ("user", "default", "conv"),
        "get_session_baseline": ("user", "default"),
        "resolve_session_ref": ("user", "default", "oldref"),
        "get_other_session_baseline": ("user", "default", "other"),
        "get_cmid_record": ("iid", "user", "default", "existing"),
        "get_roster_state": ("user",), "get_authorize_cooldown": ("user", "default"),
        "audit_events": (),
    }
    assert set(args) == READERS
    return getattr(store, name)(*args[name])


def _write_public(store: Store, name: str) -> None:
    calls = {
        "revoke_all_for_identity_change": lambda: store.revoke_all_for_identity_change(4),
        "insert_offer": lambda: store.insert_offer("new-offer", b"t" * 32, 101),
        "insert_pairing": lambda: store.insert_pairing("new-pair", "offer", b"pub", "Phone", b"x" * 16, b"y" * 16, 101),
        "record_p4_ts": lambda: store.record_p4_ts("pair", 4),
        "insert_user": lambda: store.insert_user("new-user", "New", 4),
        "insert_device": lambda: store.insert_device("new-device", "user", "fp2", b"pub", "New", 4),
        "set_owner_controls": lambda: store.set_owner_controls("device", allowed=True, now=4),
        "set_device_state": lambda: store.set_device_state("device", "REVOKED"),
        "insert_token_family": lambda: store.insert_token_family("new-family", "device", 4),
        "revoke_family": lambda: store.revoke_family("family", 4),
        "revoke_families_for_device": lambda: store.revoke_families_for_device("device", 4),
        "insert_refresh_token": lambda: store.insert_refresh_token(b"q" * 32, "family", 4),
        "insert_access_token": lambda: store.insert_access_token(b"q" * 32, "family", "device", "iid", 101),
        "rotate_refresh_token": lambda: store.rotate_refresh_token(old_hash=b"r" * 32, family_id="family", new_hash=b"q" * 32, successor_hash=b"z" * 32, issued_at=4),
        "record_p5_nonce": lambda: store.record_p5_nonce("device", b"new", 4),
        "set_chat": lambda: store.set_chat("user", "default", "conv", "new-chat"),
        "set_session_baseline": lambda: store.set_session_baseline("user", "default", "new-session", "new-tip", 2, 4),
        "mint_or_get_session_ref": lambda: store.mint_or_get_session_ref("user", "default", "new-session", "newref", 4),
        "set_other_session_baseline": lambda: store.set_other_session_baseline("user", "default", "other", "new-tip", 2, 4),
        "reserve_cmid": lambda: store.reserve_cmid("iid", "user", "default", "new-cmid", b"q", 4),
        "delete_cmid_reservation": lambda: store.delete_cmid_reservation("iid", "user", "default", "existing"),
        "finalize_cmid": lambda: store.finalize_cmid("iid", "user", "default", "existing", status="accepted", result_json=None, updated_at=4),
        "reserve_phone_cmid": lambda: store.reserve_phone_cmid("iid", "user", "default", "new-phone", b"q", 4),
        "finalize_phone_cmid": lambda: store.finalize_phone_cmid("iid", "user", "default", "phone", status="submitted", result_json=None, updated_at=4),
        "set_roster_state": lambda: store.set_roster_state("user", "new", 4),
        "set_authorize_cooldown": lambda: store.set_authorize_cooldown("user", "default", 4),
        "write_audit": lambda: store.write_audit(4, "after", "ok"),
    }
    assert set(calls) == WRITERS
    calls[name]()


def _durable_dump(path: Path) -> tuple[str, ...]:
    with sqlite3.connect(path) as conn:
        return tuple(conn.iterdump())


@pytest.mark.parametrize("commit", [False, True])
@pytest.mark.parametrize("name", sorted(READERS))
def test_each_public_reader_waits_for_foreign_transaction(tmp_path: Path, name: str, commit: bool) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    started = threading.Event()
    finished = threading.Event()
    errors: list[BaseException] = []
    values: list[object] = []

    def work() -> None:
        started.set()
        try:
            values.append(_read_public(store, name))
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    try:
        with _no_exception() if commit else pytest.raises(RuntimeError, match="rollback-marker"):
            with store.transaction() as conn:
                conn.execute("INSERT INTO device_owner_controls VALUES ('device', 1, 4)")
                worker = threading.Thread(target=work)
                worker.start()
                assert started.wait(2) and not finished.wait(0.03)
                if not commit:
                    raise RuntimeError("rollback-marker")
        worker.join(timeout=2)
        assert not worker.is_alive() and finished.is_set() and not errors
        assert len(values) == 1
        assert _separate_controls(store._path) == (1 if commit else None)
        if name == "owner_controls_decision":
            assert values == [True if commit else None]
        if name == "readiness_owner_controls_value":
            assert values == [1 if commit else None]
    finally:
        store.close()


@pytest.mark.parametrize("name", sorted(WRITERS))
def test_each_public_writer_owns_its_commit_after_foreign_rollback(tmp_path: Path, name: str) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    baseline = _durable_dump(store._path)
    started = threading.Event()
    finished = threading.Event()
    errors: list[BaseException] = []

    def work() -> None:
        started.set()
        try:
            _write_public(store, name)
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    try:
        with pytest.raises(RuntimeError, match="rollback-marker"):
            with store.transaction() as conn:
                conn.execute("INSERT INTO device_owner_controls VALUES ('device', 1, 4)")
                worker = threading.Thread(target=work)
                worker.start()
                assert started.wait(2) and not finished.wait(0.03)
                assert _durable_dump(store._path) == baseline
                raise RuntimeError("rollback-marker")
        worker.join(timeout=2)
        assert not worker.is_alive() and finished.is_set() and not errors
        assert _separate_controls(store._path) is None or name == "set_owner_controls"
        assert _durable_dump(store._path) != baseline  # independent committed effect survived
    finally:
        store.close()


def test_future_schema_poison_refuses_every_authority_surface_without_downgrade(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    # Use a separate exact database with a complete old schema and only a future version
    # marker. Ordinary tables existing must not allow bearer or Store authority to continue.
    from hmp_plugin.store import _SCHEMA
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
        conn.execute(
            "INSERT INTO meta (id,instance_epoch,store_revocation_epoch,schema_version) "
            "VALUES (1,0,0,?)", (SCHEMA_VERSION + 1,),
        )
    original_bytes = path.read_bytes()
    with sqlite3.connect(path) as conn:
        original_journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        original_schema = tuple(conn.execute(
            "SELECT type,name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall())
    future = Store(path)
    with pytest.raises(RuntimeError, match="future store schema"):
        future.migrate()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT schema_version FROM meta WHERE id=1").fetchone()[0] == SCHEMA_VERSION + 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == original_journal
        assert tuple(conn.execute(
            "SELECT type,name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()) == original_schema
    assert path.read_bytes() == original_bytes
    for call in (
        future.request_schema_ready, future.instance_epoch,
        lambda: future.get_device("device"),
        lambda: future.access_authority_snapshot(b"x" * 32),
        lambda: future.insert_user("new", "New", 1),
    ):
        with pytest.raises(RuntimeError, match="state unavailable"):
            call()
    with pytest.raises(RuntimeError, match="state unavailable"):
        future.migrate()
    future.close()


class _FailingBoundary:
    """Inject a single actual connection-boundary failure without rewriting Store code."""
    def __init__(self, real: sqlite3.Connection, command: str) -> None:
        self.real = real
        self.command = command
    def execute(self, sql: str, *args):
        if sql == self.command:
            raise sqlite3.OperationalError("injected boundary failure")
        return self.real.execute(sql, *args)
    def close(self) -> None:
        self.real.close()


@pytest.mark.parametrize("command", ["BEGIN IMMEDIATE", "COMMIT", "ROLLBACK"])
def test_boundary_failure_poisons_connection_without_replay(tmp_path: Path, command: str) -> None:
    store = _store(tmp_path)
    real = store._conn
    assert real is not None
    store._conn = _FailingBoundary(real, command)  # type: ignore[assignment]
    try:
        if command == "ROLLBACK":
            with pytest.raises(sqlite3.OperationalError, match="injected"):
                with store.transaction():
                    raise RuntimeError("force rollback")
        else:
            with pytest.raises(sqlite3.OperationalError, match="injected"):
                with store.transaction() as conn:
                    conn.execute("INSERT INTO device_owner_controls VALUES ('device', 1, 2)")
        for call in (store.instance_epoch, lambda: store.insert_user("later", "Later", 3)):
            with pytest.raises(RuntimeError, match="state unavailable"):
                call()
    finally:
        store.close()


def test_lifecycle_refuses_owner_and_waits_for_foreign_transaction(tmp_path: Path) -> None:
    store = _store(tmp_path)
    started = threading.Event()
    done = threading.Event()
    errors: list[BaseException] = []
    old = store._conn
    def repeat_migrate() -> None:
        started.set()
        try:
            store.migrate()
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()
    try:
        with store.transaction():
            with pytest.raises(RuntimeError, match="owned transaction"):
                store.migrate()
            with pytest.raises(RuntimeError, match="owned transaction"):
                store.close()
            worker = threading.Thread(target=repeat_migrate)
            worker.start()
            assert started.wait(2) and not done.wait(0.03)
        worker.join(timeout=2)
        assert not worker.is_alive() and done.is_set() and not errors
        assert store._conn is old
    finally:
        store.close()


@pytest.mark.parametrize("name", sorted(READERS))
def test_same_owner_reader_reentry_terminates(tmp_path: Path, name: str) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    try:
        with store.transaction():
            _read_public(store, name)
    finally:
        store.close()


@pytest.mark.parametrize("name", sorted(WRITERS))
def test_same_owner_writer_reentry_rolls_back_with_owner(tmp_path: Path, name: str) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    baseline = _durable_dump(store._path)
    try:
        with pytest.raises(RuntimeError, match="abort owner"):
            with store.transaction():
                _write_public(store, name)
                raise RuntimeError("abort owner")
        assert _durable_dump(store._path) == baseline
    finally:
        store.close()


def test_external_commits_expose_only_coherent_authority_and_epoch_pairs(tmp_path: Path) -> None:
    store = _store(tmp_path)
    raw = b"a" * 32
    store.insert_token_family("fam", "device", 1)
    # This is the hash the Authenticator computes from the raw bearer value.
    from hmp_plugin import crypto
    store.insert_access_token(crypto.sha256(raw), "fam", "device", "iid", 100)
    auth = Authenticator(store, "iid", lambda: 2)
    bearer = "Bearer " + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    try:
        assert auth.authenticate(bearer, "iid").family_id == "fam"
        assert store.epoch_authority_snapshot() == (0, 0)
        other = sqlite3.connect(store._path, isolation_level=None)
        try:
            other.execute("BEGIN IMMEDIATE")
            other.execute("UPDATE token_families SET revoked_at=3 WHERE family_id='fam'")
            other.execute("UPDATE devices SET state='REVOKED' WHERE device_id='device'")
            other.execute("UPDATE meta SET instance_epoch=1, store_revocation_epoch=1 WHERE id=1")
            # Both queries run on the Store's separate connection while the foreign
            # connection holds uncommitted authority changes.
            assert auth.authenticate(bearer, "iid").family_id == "fam"
            assert store.epoch_authority_snapshot() == (0, 0)
            other.execute("COMMIT")
            assert store.epoch_authority_snapshot() == (1, 1)
            with pytest.raises(HmpError) as exc:
                auth.authenticate(bearer, "iid")
            assert exc.value.code is ErrorCode.REVOKED
        finally:
            if other.in_transaction:
                other.execute("ROLLBACK")
            other.close()
    finally:
        store.close()


def _reader_value(value):
    if isinstance(value, sqlite3.Row):
        return tuple(value)
    if isinstance(value, (list, tuple)):
        return tuple(_reader_value(item) for item in value)
    return value


def _mutate_reader_target(conn: sqlite3.Connection, name: str) -> None:
    """Change the exact row/predicate consumed by each named public reader."""
    sql = {
        "request_schema_ready": "UPDATE meta SET schema_version=4 WHERE id=1",
        "instance_epoch": "UPDATE meta SET instance_epoch=1 WHERE id=1",
        "revocation_epoch": "UPDATE meta SET store_revocation_epoch=1 WHERE id=1",
        "get_offer": "UPDATE offers SET expires_at=101 WHERE oid='offer'",
        "get_pairing": "UPDATE pairings SET confirm_by=101 WHERE pairing_id='pair'",
        "get_device": "UPDATE devices SET label='changed' WHERE device_id='device'",
        "owner_controls_decision": "INSERT INTO device_owner_controls VALUES ('device',1,4)",
        "readiness_owner_controls_value": "INSERT INTO device_owner_controls VALUES ('device',1,4)",
        "get_token_family": "UPDATE token_families SET revoked_at=4 WHERE family_id='family'",
        "get_refresh_token": "UPDATE refresh_tokens SET issued_at=4 WHERE hash=x'" + (b"r" * 32).hex() + "'",
        "get_access_token": "UPDATE access_tokens SET expires_at=101 WHERE hash=x'" + (b"a" * 32).hex() + "'",
        "nonce_seen": "DELETE FROM p5_nonces WHERE device_id='device' AND nonce=x'6f6c64'",
        "count_p5_nonces": "INSERT INTO p5_nonces VALUES ('device',x'6e6577',4)",
        "get_chat": "UPDATE chats SET chat_id='changed' WHERE user_id='user' AND profile='default' AND conversation_id='conv'",
        "get_session_baseline": "UPDATE session_baselines SET lineage_tip='changed' WHERE user_id='user' AND profile='default'",
        "resolve_session_ref": "UPDATE session_refs SET ref='changedref' WHERE ref='oldref'",
        "get_other_session_baseline": "UPDATE other_session_baselines SET lineage_tip='changed' WHERE user_id='user' AND profile='default' AND session_id='other'",
        "get_cmid_record": "UPDATE direct_send_idempotency SET status='accepted' WHERE iid='iid' AND user_id='user' AND profile='default' AND cmid='existing'",
        "get_roster_state": "UPDATE roster_state SET served_set_hash='changed' WHERE user_id='user'",
        "get_authorize_cooldown": "UPDATE authorize_cooldowns SET last_trigger_at=4 WHERE user_id='user' AND profile='default'",
        "audit_events": "INSERT INTO audit VALUES (4,'changed',NULL,'ok')",
    }
    assert set(sql) == READERS
    conn.execute(sql[name])


@pytest.mark.parametrize("commit", [False, True])
@pytest.mark.parametrize("name", sorted(READERS))
def test_each_reader_exposes_only_its_own_committed_value(
    tmp_path: Path, name: str, commit: bool
) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    before = _reader_value(_read_public(store, name))
    started = threading.Event()
    done = threading.Event()
    values: list[object] = []
    errors: list[BaseException] = []
    def read() -> None:
        started.set()
        try:
            values.append(_reader_value(_read_public(store, name)))
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()
    try:
        with _no_exception() if commit else pytest.raises(RuntimeError, match="abort reader"):
            with store.transaction() as conn:
                _mutate_reader_target(conn, name)
                tentative = _reader_value(_read_public(store, name))
                assert tentative != before  # exact reader target, never an unrelated Controls row
                worker = threading.Thread(target=read)
                worker.start()
                assert started.wait(2) and not done.wait(0.03)
                if not commit:
                    raise RuntimeError("abort reader")
        worker.join(timeout=2)
        assert not worker.is_alive() and done.is_set() and not errors
        assert values == [tentative if commit else before]
        store.close()
        if name == "request_schema_ready" and commit:
            # The committed future-version marker must not be reopened by old code.
            with sqlite3.connect(store._path) as conn:
                assert conn.execute("SELECT schema_version FROM meta WHERE id=1").fetchone()[0] == 4
        else:
            reopened = Store(store._path)
            reopened.migrate()
            try:
                assert _reader_value(_read_public(reopened, name)) == (tentative if commit else before)
            finally:
                reopened.close()
    finally:
        store.close()


def test_two_valid_actors_never_yield_a_mixed_access_or_epoch_pair(tmp_path: Path) -> None:
    from hmp_plugin import crypto
    store = _store(tmp_path)
    store.insert_user("other-user", "Other", 1)
    store.insert_device("other-device", "other-user", "other-fp", b"other-key", "Other", 1, state="ACTIVE")
    store.insert_token_family("family-one", "device", 1)
    store.insert_token_family("family-two", "other-device", 1)
    token_one, token_two = b"1" * 32, b"2" * 32
    hash_one, hash_two = crypto.sha256(token_one), crypto.sha256(token_two)
    store.insert_access_token(hash_one, "family-one", "device", "iid", 100)
    store.insert_access_token(hash_two, "family-two", "other-device", "iid", 100)
    auth = Authenticator(store, "iid", lambda: 2)
    bearer_one = "Bearer " + base64.urlsafe_b64encode(token_one).rstrip(b"=").decode("ascii")
    bearer_two = "Bearer " + base64.urlsafe_b64encode(token_two).rstrip(b"=").decode("ascii")
    def pair() -> tuple[tuple[str, str, str], tuple[str, str, str], tuple[int, int] | None]:
        a, b = auth.authenticate(bearer_one, "iid"), auth.authenticate(bearer_two, "iid")
        return ((a.device_id, a.user_id, a.family_id),
                (b.device_id, b.user_id, b.family_id), store.epoch_authority_snapshot())
    before = pair()
    assert before == (("device", "user", "family-one"),
                      ("other-device", "other-user", "family-two"), (0, 0))
    other = sqlite3.connect(store._path, isolation_level=None)
    try:
        other.execute("BEGIN IMMEDIATE")
        other.execute("UPDATE access_tokens SET family_id='family-two', device_id='other-device' WHERE hash=?", (hash_one,))
        other.execute("UPDATE access_tokens SET family_id='family-one', device_id='device' WHERE hash=?", (hash_two,))
        other.execute("UPDATE meta SET instance_epoch=1, store_revocation_epoch=1 WHERE id=1")
        assert pair() == before  # foreign changes are uncommitted on a separate connection
        other.execute("COMMIT")
        after = pair()
        assert after == (("other-device", "other-user", "family-two"),
                         ("device", "user", "family-one"), (1, 1))
        other.execute("BEGIN IMMEDIATE")
        other.execute("UPDATE access_tokens SET family_id='family-one' WHERE hash=?", (hash_one,))
        other.execute("UPDATE meta SET instance_epoch=2, store_revocation_epoch=2 WHERE id=1")
        assert pair() == after
        other.execute("COMMIT")
        assert store.epoch_authority_snapshot() == (2, 2)
        with pytest.raises(HmpError) as exc:
            auth.authenticate(bearer_one, "iid")
        assert exc.value.code is ErrorCode.UNAUTHENTICATED  # mismatched family/device, no positive binding
    finally:
        if other.in_transaction:
            other.execute("ROLLBACK")
        other.close()
        store.close()


def test_foreign_close_waits_for_owner_and_then_refuses_reads(tmp_path: Path) -> None:
    store = _store(tmp_path)
    started, done = threading.Event(), threading.Event()
    errors: list[BaseException] = []
    def close_foreign() -> None:
        started.set()
        try:
            store.close()
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()
    with store.transaction():
        worker = threading.Thread(target=close_foreign)
        worker.start()
        assert started.wait(2) and not done.wait(0.03)
        assert store.instance_epoch() == 0  # owner retains the same live connection
    worker.join(timeout=2)
    assert not worker.is_alive() and done.is_set() and not errors
    assert store._conn is None
    with pytest.raises(RuntimeError, match="migrate"):
        store.instance_epoch()


def test_close_failure_poison_refuses_later_authority(tmp_path: Path) -> None:
    store = _store(tmp_path)
    real = store._conn
    assert real is not None
    class RefusingClose:
        def close(self) -> None:
            raise sqlite3.OperationalError("injected close failure")
    store._conn = RefusingClose()  # type: ignore[assignment]
    try:
        with pytest.raises(sqlite3.OperationalError, match="injected close"):
            store.close()
        with pytest.raises(RuntimeError, match="state unavailable"):
            store.instance_epoch()
    finally:
        real.close()


def test_phone_cmid_direct_send_status_still_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_full(store)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            store.finalize_phone_cmid(
                "iid", "user", "default", "phone", status="accepted",
                result_json=None, updated_at=4,
            )
        row = store._require_conn().execute(
            "SELECT status, updated_at FROM phone_send_idempotency "
            "WHERE iid='iid' AND user_id='user' AND profile='default' AND cmid='phone'"
        ).fetchone()
        assert row is not None and row["status"] == "pending" and row["updated_at"] == 2
    finally:
        store.close()
