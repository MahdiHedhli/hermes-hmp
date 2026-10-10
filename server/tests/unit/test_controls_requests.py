"""Disposable-store causal tests for request-host Controls transaction primitives.

These tests do not exercise a live bearer, host TTY, bridge, or a real Controls grant.
"""

from __future__ import annotations

import sqlite3
import threading
import contextlib
from pathlib import Path

import pytest

from hmp_plugin.controls_requests import ControlsRequestStore, RequestOrigin
import hmp_plugin.controls_requests as requests_module
from hmp_plugin.store import Store, _SCHEMA

IID = "a" * 52
CLIENT = "00000000-0000-4000-8000-000000000001"


def _seed(store: Store, *, device: str = "dev_a", family: str = "fam_a") -> RequestOrigin:
    store.insert_user("hmpu_a", "owner", 1)
    store.insert_device(device, "hmpu_a", "f" * 52, b"k", "phone", 1, state="ACTIVE")
    store.insert_token_family(family, device, 1)
    return RequestOrigin(device, "hmpu_a", family, IID, 0, 0)


def _request(
    api: ControlsRequestStore, origin: RequestOrigin, *, now: int = 1000,
    client: str = CLIENT, feature: str = "jobs",
):
    return api.create(
        origin, client_id=client, profile="main", feature=feature,
        now=now, current_iid=IID,
    )


def test_atomic_v2_migration_backfill_and_legacy_writers(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO meta (id,instance_epoch,store_revocation_epoch,schema_version) "
        "VALUES (1,0,0,2)"
    )
    conn.execute("INSERT INTO users VALUES ('hmpu_a','owner',1)")
    for dev in ("dev_a", "dev_b"):
        conn.execute(
            "INSERT INTO devices VALUES (?, 'hmpu_a', ?, ?, 'phone', 'ACTIVE', 1)",
            (dev, "f" * 52, b"k"),
        )
    conn.execute("INSERT INTO device_owner_controls VALUES ('dev_a',1,2)")
    conn.close()

    store = Store(path)
    store.migrate()
    assert store.request_schema_ready()
    db = store._require_conn()
    revision = lambda dev: db.execute(
        "SELECT revision FROM device_owner_controls_revision WHERE device_id = ?", (dev,)
    ).fetchone()[0]
    assert revision("dev_a") == 1
    assert revision("dev_b") == 0

    # Same-value old-binary update, insert, update and delete are all visible without
    # changing the legacy writer's call path.
    db.execute("UPDATE device_owner_controls SET allowed = 1 WHERE device_id = 'dev_a'")
    assert revision("dev_a") == 2
    db.execute("INSERT INTO device_owner_controls VALUES ('dev_b',0,3)")
    assert revision("dev_b") == 1
    db.execute("UPDATE device_owner_controls SET allowed = 1 WHERE device_id = 'dev_b'")
    assert revision("dev_b") == 2
    db.execute("DELETE FROM device_owner_controls WHERE device_id = 'dev_b'")
    assert revision("dev_b") == 3
    assert store.request_schema_ready()

    # Signed-64 overflow aborts the underlying Controls write, preserving both values.
    db.execute(
        "UPDATE device_owner_controls_revision SET revision = 9223372036854775807 "
        "WHERE device_id = 'dev_a'"
    )
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("UPDATE device_owner_controls SET allowed = 0 WHERE device_id = 'dev_a'")
    assert store.owner_controls_decision("dev_a") is True
    assert revision("dev_a") == 9223372036854775807
    store.close()


def test_migration_failure_rolls_back_request_schema(tmp_path: Path, monkeypatch) -> None:
    # A single-statement fault after the tables exist cannot leave schema_version=3.
    import hmp_plugin.store as store_module

    path = tmp_path / "rollback.sqlite3"
    db = sqlite3.connect(path, isolation_level=None)
    db.executescript(_SCHEMA)
    db.execute(
        "INSERT INTO meta (id,instance_epoch,store_revocation_epoch,schema_version) "
        "VALUES (1,0,0,2)"
    )
    db.close()
    original = store_module._REQUEST_TRIGGERS
    monkeypatch.setattr(
        store_module, "_REQUEST_TRIGGERS",
        {**original, "fault": "CREATE TRIGGER fault AFTER INSERT ON absent_table BEGIN SELECT 1; END"},
    )
    with pytest.raises(sqlite3.DatabaseError):
        Store(path).migrate()
    db = sqlite3.connect(path)
    assert db.execute("SELECT schema_version FROM meta WHERE id=1").fetchone()[0] == 2
    assert db.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='controls_requests'"
    ).fetchone()[0] == 0
    db.close()


def test_partial_schema_refuses_upgrade_without_laundering(tmp_path: Path) -> None:
    path = tmp_path / "partial.sqlite3"
    db = sqlite3.connect(path, isolation_level=None)
    db.executescript(_SCHEMA)
    db.execute(
        "INSERT INTO meta (id,instance_epoch,store_revocation_epoch,schema_version) "
        "VALUES (1,0,0,2)"
    )
    # A preexisting incompatible table is corruption, not an idempotent partial migration.
    incompatible = "CREATE TABLE controls_requests (bad INTEGER)"
    db.execute(incompatible)
    db.close()

    with pytest.raises(sqlite3.DatabaseError):
        Store(path).migrate()
    db = sqlite3.connect(path)
    assert db.execute("SELECT schema_version FROM meta WHERE id=1").fetchone()[0] == 2
    assert db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='controls_requests'"
    ).fetchone()[0] == incompatible
    assert db.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name IN "
        "('device_owner_controls_revision','controls_request_clock','controls_revision_insert',"
        "'controls_revision_update','controls_revision_delete')"
    ).fetchone()[0] == 0
    db.close()


def test_version_three_trigger_drift_disables_request_authority(tmp_path: Path) -> None:
    store = Store(tmp_path / "drift.sqlite3")
    store.migrate()
    origin = _seed(store)
    assert store.request_schema_ready()
    store._require_conn().execute("DROP TRIGGER controls_revision_update")
    assert not store.request_schema_ready()
    api = ControlsRequestStore(store)
    with pytest.raises(RuntimeError, match="request schema unavailable"):
        _request(api, origin)
    assert store.owner_controls_decision(origin.device_id) is None
    store.close()


@pytest.mark.parametrize(
    "writer", ["insert_device", "insert_family", "device", "family", "device_families"]
)
def test_public_device_family_writer_cannot_interleave_checked_grant(
    tmp_path: Path, monkeypatch, writer: str,
) -> None:
    """All five public authority writers wait until the request commits."""
    store = Store(tmp_path / (writer + ".sqlite3"))
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    request = _request(api, origin)
    checked = threading.Event()
    release_decision = threading.Event()
    writer_entered = threading.Event()
    writer_finished = threading.Event()
    original_origin = requests_module._current_origin
    original_writer = store._serialized_writer

    def held_origin(conn, selected):
        result = original_origin(conn, selected)
        if result and selected == origin:
            checked.set()
            assert release_decision.wait(2), "decision release deadline"
        return result

    @contextlib.contextmanager
    def signaled_writer():
        writer_entered.set()
        with original_writer() as conn:
            yield conn

    monkeypatch.setattr(requests_module, "_current_origin", held_origin)
    monkeypatch.setattr(store, "_serialized_writer", signaled_writer)
    decision_result: list[object] = []
    writer_errors: list[BaseException] = []

    def decide() -> None:
        try:
            decision_result.append(api.decide(
                request.request_id, allow=True, now=1001, current_iid=IID,
                precommit_external_verified=True,
            ))
        except BaseException as exc:
            decision_result.append(exc)

    def revoke() -> None:
        try:
            if writer == "insert_device":
                store.insert_device("dev_new", origin.user_id, "g" * 52, b"n", "new", 1002)
            elif writer == "insert_family":
                store.insert_token_family("fam_new", origin.device_id, 1002)
            elif writer == "device":
                store.set_device_state(origin.device_id, "REVOKED")
            elif writer == "family":
                store.revoke_family(origin.family_id, 1002)
            else:
                store.revoke_families_for_device(origin.device_id, 1002)
        except BaseException as exc:
            writer_errors.append(exc)
        finally:
            writer_finished.set()

    decision_thread = threading.Thread(target=decide)
    writer_thread = threading.Thread(target=revoke)
    decision_thread.start()
    try:
        assert checked.wait(2), "origin read deadline"
        writer_thread.start()
        assert writer_entered.wait(2), "writer entry deadline"
        assert not writer_finished.wait(0.1), "revocation interleaved inside checked grant"
    finally:
        release_decision.set()
        decision_thread.join(2)
        if writer_thread.ident is not None:
            writer_thread.join(2)
    assert not decision_thread.is_alive() and not writer_thread.is_alive()
    assert not writer_errors and len(decision_result) == 1
    assert not isinstance(decision_result[0], BaseException)
    assert decision_result[0].code == "committed_needs_effective_readback"
    assert writer_finished.is_set()
    historical = api.host_show(request.request_id, now=1003, current_iid=IID)
    assert historical.code == "ok" and historical.state == "GRANTED"
    db = store._require_conn()
    if writer == "insert_device":
        assert db.execute("SELECT state FROM devices WHERE device_id='dev_new'").fetchone()[0] == "PENDING"
    elif writer == "insert_family":
        assert db.execute("SELECT device_id FROM token_families WHERE family_id='fam_new'").fetchone()[0] == origin.device_id
    elif writer == "device":
        assert db.execute("SELECT state FROM devices WHERE device_id=?", (origin.device_id,)).fetchone()[0] == "REVOKED"
    else:
        assert db.execute("SELECT revoked_at FROM token_families WHERE family_id=?", (origin.family_id,)).fetchone()[0] == 1002
    separate = sqlite3.connect(store._path)
    try:
        assert separate.execute(
            "SELECT state FROM controls_requests WHERE request_id=?", (request.request_id,)
        ).fetchone()[0] == "GRANTED"
        assert separate.execute(
            "SELECT allowed FROM device_owner_controls WHERE device_id=?", (origin.device_id,)
        ).fetchone()[0] == 1
        assert separate.execute(
            "SELECT revision FROM device_owner_controls_revision WHERE device_id=?",
            (origin.device_id,),
        ).fetchone()[0] == 1
    finally:
        separate.close()
    store.close()


def test_revocation_helper_joins_same_thread_transaction(tmp_path: Path) -> None:
    store = Store(tmp_path / "joined.sqlite3")
    store.migrate()
    origin = _seed(store)
    with store.transaction() as conn:
        store.revoke_family(origin.family_id, 1000)
        assert conn.execute("SELECT revoked_at FROM token_families WHERE family_id=?", (origin.family_id,)).fetchone()[0] == 1000
        with pytest.raises(RuntimeError, match="nested Store.transaction"):
            with store.transaction():
                pass
    assert store.get_token_family(origin.family_id)["revoked_at"] == 1000
    store.close()


@pytest.mark.parametrize("writer", ["device", "family", "device_families"])
def test_revocation_committed_first_refuses_allow(tmp_path: Path, writer: str) -> None:
    store = Store(tmp_path / ("first_" + writer + ".sqlite3"))
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    request = _request(api, origin)
    if writer == "device":
        store.set_device_state(origin.device_id, "REVOKED")
    elif writer == "family":
        store.revoke_family(origin.family_id, 1001)
    else:
        store.revoke_families_for_device(origin.device_id, 1001)
    answer = api.decide(
        request.request_id, allow=True, now=1002, current_iid=IID,
        precommit_external_verified=True,
    )
    assert answer.code == "already_decided" and answer.state == "REVOKED"
    db = store._require_conn()
    assert db.execute("SELECT COUNT(*) FROM device_owner_controls").fetchone()[0] == 0
    assert db.execute("SELECT revision FROM device_owner_controls_revision WHERE device_id=?", (origin.device_id,)).fetchone() is None
    assert requests_module._revision(db, origin.device_id) == (0, None)
    assert db.execute("SELECT state FROM controls_requests WHERE request_id=?", (request.request_id,)).fetchone()[0] == "REVOKED"
    store.close()


def test_failed_grant_rolls_back_before_waiting_revocation_commits(
    tmp_path: Path, monkeypatch,
) -> None:
    path = tmp_path / "rollback_then_revoke.sqlite3"
    store = Store(path)
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    request = _request(api, origin)
    tentative = threading.Event()
    release = threading.Event()
    entered = threading.Event()
    finished = threading.Event()
    original_revision = requests_module._revision
    original_writer = store._serialized_writer

    def fault_after_tentative_write(conn, device_id):
        controls = conn.execute(
            "SELECT allowed FROM device_owner_controls WHERE device_id=?", (device_id,)
        ).fetchone()
        if controls is not None and controls["allowed"] == 1:
            tentative.set()
            assert release.wait(2), "tentative write release deadline"
            raise RuntimeError("injected post-write refusal")
        return original_revision(conn, device_id)

    @contextlib.contextmanager
    def signaled_writer():
        entered.set()
        with original_writer() as conn:
            yield conn

    monkeypatch.setattr(requests_module, "_revision", fault_after_tentative_write)
    monkeypatch.setattr(store, "_serialized_writer", signaled_writer)
    decision_errors: list[BaseException] = []
    writer_errors: list[BaseException] = []

    def decide() -> None:
        try:
            api.decide(
                request.request_id, allow=True, now=1001, current_iid=IID,
                precommit_external_verified=True,
            )
        except BaseException as exc:
            decision_errors.append(exc)

    def revoke() -> None:
        try:
            store.revoke_family(origin.family_id, 1002)
        except BaseException as exc:
            writer_errors.append(exc)
        finally:
            finished.set()

    decision_thread = threading.Thread(target=decide)
    writer_thread = threading.Thread(target=revoke)
    decision_thread.start()
    try:
        assert tentative.wait(2), "tentative Controls write deadline"
        writer_thread.start()
        assert entered.wait(2), "revoke entry deadline"
        assert not finished.wait(0.1), "revoke was laundered through tentative grant"
    finally:
        release.set()
        decision_thread.join(2)
        if writer_thread.ident is not None:
            writer_thread.join(2)
    assert not decision_thread.is_alive() and not writer_thread.is_alive()
    assert len(decision_errors) == 1 and isinstance(decision_errors[0], RuntimeError)
    assert str(decision_errors[0]) == "injected post-write refusal"
    assert not writer_errors and finished.is_set()
    # A separate connection confirms the rollback and then the independent revocation commit.
    separate = sqlite3.connect(path)
    try:
        assert separate.execute("SELECT COUNT(*) FROM device_owner_controls").fetchone()[0] == 0
        assert separate.execute(
            "SELECT revision FROM device_owner_controls_revision WHERE device_id=?",
            (origin.device_id,),
        ).fetchone() is None
        assert original_revision(separate, origin.device_id) == (0, None)
        assert separate.execute(
            "SELECT state FROM controls_requests WHERE request_id=?", (request.request_id,)
        ).fetchone()[0] == "PENDING"
        assert separate.execute(
            "SELECT revoked_at FROM token_families WHERE family_id=?", (origin.family_id,)
        ).fetchone()[0] == 1002
    finally:
        separate.close()
    store.close()


@pytest.mark.parametrize("rollback", [True, False])
def test_positive_controls_readers_wait_for_grant_disposition(
    tmp_path: Path, monkeypatch, rollback: bool,
) -> None:
    """Neither positive authority reader observes an uncommitted Controls grant."""
    path = tmp_path / ("reader_rollback.sqlite3" if rollback else "reader_commit.sqlite3")
    store = Store(path)
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    request = _request(api, origin)
    tentative = threading.Event()
    release = threading.Event()
    original_revision = requests_module._revision

    def held_after_tentative_write(conn, device_id):
        row = conn.execute(
            "SELECT allowed FROM device_owner_controls WHERE device_id=?", (device_id,)
        ).fetchone()
        if row is not None and row["allowed"] == 1:
            tentative.set()
            assert release.wait(2), "tentative grant release deadline"
            if rollback:
                raise RuntimeError("injected tentative grant rollback")
        return original_revision(conn, device_id)

    monkeypatch.setattr(requests_module, "_revision", held_after_tentative_write)
    decision_result: list[object] = []
    reader_started = [threading.Event(), threading.Event()]
    reader_finished = [threading.Event(), threading.Event()]
    reader_results: list[list[object]] = [[], []]

    def decide() -> None:
        try:
            decision_result.append(api.decide(
                request.request_id, allow=True, now=1001, current_iid=IID,
                precommit_external_verified=True,
            ))
        except BaseException as exc:
            decision_result.append(exc)

    def read_authority(index: int) -> None:
        reader_started[index].set()
        try:
            value = (store.owner_controls_decision(origin.device_id) if index == 0
                     else store.readiness_owner_controls_value(origin.device_id))
            reader_results[index].append(value)
        except BaseException as exc:
            reader_results[index].append(exc)
        finally:
            reader_finished[index].set()

    decision_thread = threading.Thread(target=decide)
    readers = [threading.Thread(target=read_authority, args=(i,)) for i in range(2)]
    decision_thread.start()
    try:
        assert tentative.wait(2), "tentative Controls write deadline"
        for thread in readers:
            thread.start()
        assert all(event.wait(2) for event in reader_started), "authority reader entry deadlines"
        assert not any(event.wait(0.1) for event in reader_finished), (
            "reader observed the same connection's tentative grant"
        )
    finally:
        release.set()
        decision_thread.join(2)
        for thread in readers:
            if thread.ident is not None:
                thread.join(2)
    assert not decision_thread.is_alive() and all(not thread.is_alive() for thread in readers)
    assert len(decision_result) == 1 and all(len(values) == 1 for values in reader_results)
    assert all(not isinstance(values[0], BaseException) for values in reader_results)
    separate = sqlite3.connect(path)
    try:
        row = separate.execute(
            "SELECT allowed FROM device_owner_controls WHERE device_id=?", (origin.device_id,)
        ).fetchone()
        if rollback:
            assert isinstance(decision_result[0], RuntimeError)
            assert str(decision_result[0]) == "injected tentative grant rollback"
            assert [values[0] for values in reader_results] == [None, None]
            assert row is None
            assert separate.execute(
                "SELECT state FROM controls_requests WHERE request_id=?", (request.request_id,)
            ).fetchone()[0] == "PENDING"
        else:
            assert not isinstance(decision_result[0], BaseException)
            assert decision_result[0].code == "committed_needs_effective_readback"
            assert [values[0] for values in reader_results] == [True, 1]
            assert row == (1,)
            assert separate.execute(
                "SELECT state FROM controls_requests WHERE request_id=?", (request.request_id,)
            ).fetchone()[0] == "GRANTED"
    finally:
        separate.close()
    store.close()


def test_same_origin_idempotency_foreign_scope_and_legacy_conflict(tmp_path: Path) -> None:
    store = Store(tmp_path / "requests.sqlite3")
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    first = _request(api, origin)
    assert first.code == "created" and first.state == "PENDING"
    assert _request(api, origin).request_id == first.request_id
    assert _request(api, origin, feature="models").code == "conflict"
    foreign = RequestOrigin(
        origin.device_id, origin.user_id, "different_family", IID, 0, 0
    )
    assert api.status(foreign, client_id=CLIENT, now=1001, current_iid=IID).code == "not_found"
    assert api.cancel(foreign, client_id=CLIENT, now=1001, current_iid=IID).code == "not_found"
    assert store.set_owner_controls(origin.device_id, allowed=True, now=1002)
    status = api.status(origin, client_id=CLIENT, now=1003, current_iid=IID)
    assert status.state == "CONFLICT"
    assert api.decide(
        first.request_id, allow=True, now=1004, current_iid=IID,
        precommit_external_verified=True,
    ).code == "already_decided"
    store.close()


def test_clock_expiry_cancel_and_positive_readback_boundary(tmp_path: Path) -> None:
    store = Store(tmp_path / "clock.sqlite3")
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    first = _request(api, origin)
    assert api.status(origin, client_id=CLIENT, now=1001, current_iid=IID).state == "PENDING"
    assert api.status(origin, client_id=CLIENT, now=999, current_iid=IID).code == "clock_unknown"
    assert _request(api, origin, client="00000000-0000-4000-8000-000000000002", now=999).code == "clock_unknown"
    assert api.decide(
        first.request_id, allow=True, now=999, current_iid=IID,
        precommit_external_verified=True,
    ).code == "clock_unknown"
    assert api.cancel(origin, client_id=CLIENT, now=999, current_iid=IID).state == "CANCELLED"
    assert store.owner_controls_decision(origin.device_id) is None

    second_client = "00000000-0000-4000-8000-000000000002"
    second = _request(api, origin, client=second_client, now=1002)
    assert second.code == "created"
    positive = api.decide(
        second.request_id, allow=True, now=1003, current_iid=IID,
        precommit_external_verified=True,
    )
    assert positive.code == "committed_needs_effective_readback"
    assert positive.state == "GRANTED" and store.owner_controls_decision(origin.device_id)
    assert api.cancel(origin, client_id=second_client, now=1004, current_iid=IID).code == "already_decided"
    assert api.decide(
        second.request_id, allow=True, now=1004, current_iid=IID,
        precommit_external_verified=True,
    ).code == "already_decided"

    third = _request(
        api, origin, client="00000000-0000-4000-8000-000000000003", now=1005
    )
    assert api.host_show(third.request_id, now=1605, current_iid=IID).state == "EXPIRED"
    store.close()


def test_identity_revocation_and_capacity_are_fail_closed(tmp_path: Path) -> None:
    store = Store(tmp_path / "revocation.sqlite3")
    store.migrate()
    origin = _seed(store)
    api = ControlsRequestStore(store)
    first = _request(api, origin)
    store.revoke_all_for_identity_change(1001)
    assert api.host_show(first.request_id, now=1002, current_iid=IID).state == "REVOKED"
    assert api.decide(
        first.request_id, allow=True, now=1003, current_iid=IID,
        precommit_external_verified=True,
    ).code == "already_decided"
    assert store.owner_controls_decision(origin.device_id) is None
    store.close()
