"""Independent permission state in disposable stores; never a live grant."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from hmp_plugin.store import Store

IID = "a" * 52


@pytest.fixture()
def store(tmp_path):
    value = Store(tmp_path / "media.sqlite3")
    value.migrate()
    value.insert_user("user_a", "owner", 1)
    value.insert_device("dev_a", "user_a", "f" * 52, b"public", "phone", 1, state="ACTIVE")
    yield value
    value.close()


def test_migration_preserves_legacy_controls_without_new_media_allows(store):
    store.set_owner_controls("dev_a", allowed=True, now=2)
    conn = store._require_conn()
    conn.execute("DROP TABLE device_media_read")
    conn.execute("DROP TABLE device_media_read_revision")
    conn.execute("UPDATE meta SET schema_version=3")
    store.migrate()
    store.migrate()
    decision = store.media_read_decision(IID, "dev_a")
    assert decision.allowed is None and decision.revision == 0
    assert decision.fallback_controls is True and decision.fallback_revision == 1
    assert store.owner_controls_decision("dev_a") is True
    assert store.request_schema_ready()
    assert conn.execute("SELECT count(*) FROM device_media_read").fetchone()[0] == 0


def test_allow_and_deny_do_not_change_other_privileges(store):
    conn = store._require_conn()
    queries = (
        "SELECT * FROM devices",
        "SELECT * FROM users",
        "SELECT * FROM device_owner_controls",
        "SELECT * FROM token_families",
    )
    before = [[tuple(row) for row in conn.execute(query)] for query in queries]
    original = store.media_read_decision(IID, "dev_a")
    allowed = store.set_media_read(original, allowed=True, now=10)
    assert allowed.allowed is True and allowed.revision == 1
    assert allowed.fallback_controls is allowed.fallback_revision is None
    denied = store.set_media_read(allowed, allowed=False, now=11)
    assert denied.allowed is False and denied.revision == 2
    assert [[tuple(row) for row in conn.execute(query)] for query in queries] == before


def test_stale_write_cannot_overwrite_a_newer_decision(store):
    old = store.media_read_decision(IID, "dev_a")
    current = store.set_media_read(old, allowed=False, now=10)
    assert store.set_media_read(old, allowed=True, now=11) is None
    assert store.media_read_decision(IID, "dev_a") == current


def test_deleted_decision_does_not_reset_its_generation(store):
    first = store.set_media_read(store.media_read_decision(IID, "dev_a"), allowed=True, now=10)
    with store.transaction() as conn:
        conn.execute("DELETE FROM device_media_read WHERE iid=? AND device_id=?", (IID, "dev_a"))
    deleted = store.media_read_decision(IID, "dev_a")
    assert deleted.allowed is None and deleted.revision == 2
    assert store.set_media_read(first, allowed=True, now=11) is None
    restored = store.set_media_read(deleted, allowed=True, now=12)
    assert restored.revision == 3 and restored.generation != first.generation


@pytest.mark.parametrize(
    "statement",
    (
        "UPDATE meta SET instance_epoch=instance_epoch+1",
        "UPDATE meta SET store_revocation_epoch=store_revocation_epoch+1",
    ),
)
def test_instance_transition_invalidates_a_prepared_write(store, statement):
    old = store.media_read_decision(IID, "dev_a")
    with store.transaction() as conn:
        conn.execute(statement)
    assert store.set_media_read(old, allowed=True, now=10) is None


def test_wrong_instance_does_not_inherit_an_allow(store):
    store.set_media_read(store.media_read_decision(IID, "dev_a"), allowed=True, now=10)
    other = store.media_read_decision("b" * 51 + "a", "dev_a")
    assert other.allowed is None and other.revision == 0


def test_revoked_or_missing_device_cannot_receive_a_grant(store):
    old = store.media_read_decision(IID, "dev_a")
    store.set_device_state("dev_a", "REVOKED")
    assert store.media_read_decision(IID, "dev_a") is None
    assert store.media_read_decision(IID, "missing") is None
    assert store.set_media_read(old, allowed=True, now=10) is None


def test_outer_rollback_preserves_decision_and_revision(store):
    old = store.media_read_decision(IID, "dev_a")
    with pytest.raises(RuntimeError, match="synthetic rollback"), store.transaction():
        assert store.set_media_read(old, allowed=True, now=10).revision == 1
        raise RuntimeError("synthetic rollback")
    assert store.media_read_decision(IID, "dev_a") == old


def test_two_connections_compare_and_swap_one_original_revision(store):
    other = Store(store._path)
    other.migrate()
    original = store.media_read_decision(IID, "dev_a")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(store.set_media_read, original, allowed=True, now=10)
            b = pool.submit(other.set_media_read, original, allowed=False, now=10)
            results = [a.result(timeout=10), b.result(timeout=10)]
        assert sum(value is not None for value in results) == 1
        assert store.media_read_decision(IID, "dev_a").revision == 1
    finally:
        other.close()


def test_fallback_controls_changes_generation_but_explicit_media_is_independent(store):
    before = store.media_read_decision(IID, "dev_a")
    store.set_owner_controls("dev_a", allowed=False, now=2)
    fallback = store.media_read_decision(IID, "dev_a")
    assert fallback != before and fallback.fallback_controls is False
    explicit = store.set_media_read(fallback, allowed=True, now=3)
    store.set_owner_controls("dev_a", allowed=True, now=4)
    assert store.media_read_decision(IID, "dev_a") == explicit


def test_missing_revision_trigger_closes_media_authority(store):
    before = store.media_read_decision(IID, "dev_a")
    store._require_conn().execute("DROP TRIGGER media_read_update")
    with pytest.raises(RuntimeError, match="schema unavailable"):
        store.media_read_decision(IID, "dev_a")
    with pytest.raises(RuntimeError, match="schema unavailable"):
        store.set_media_read(before, allowed=True, now=10)


def test_revision_overflow_rolls_back_the_decision(store):
    store.set_media_read(store.media_read_decision(IID, "dev_a"), allowed=True, now=10)
    with store.transaction() as conn:
        conn.execute("UPDATE device_media_read_revision SET revision=?", (2**63 - 1,))
    before = store.media_read_decision(IID, "dev_a")
    with pytest.raises(sqlite3.IntegrityError, match="revision overflow"):
        store.set_media_read(before, allowed=False, now=11)
    assert store.media_read_decision(IID, "dev_a") == before


@pytest.mark.parametrize("allowed", (1, "true", None))
def test_write_does_not_coerce_permission_input(store, allowed):
    with pytest.raises(ValueError):
        store.set_media_read(store.media_read_decision(IID, "dev_a"), allowed=allowed, now=10)


@pytest.mark.parametrize(
    "field",
    (
        "user_id",
        "allowed",
        "revision",
        "instance_epoch",
        "revocation_epoch",
        "fallback_controls",
        "fallback_revision",
    ),
)
def test_cas_rejects_foreign_fields_before_equality(store, field):
    class Foreign:
        def __eq__(self, other):
            raise AssertionError("foreign equality must not execute")

    before = store.media_read_decision(IID, "dev_a")
    malformed = before._replace(**{field: Foreign()})
    with pytest.raises(ValueError):
        store.set_media_read(malformed, allowed=True, now=10)
    assert store.media_read_decision(IID, "dev_a") == before


def test_noncanonical_instance_id_refused_before_permission_lookup(store):
    with pytest.raises(ValueError):
        store.media_read_decision("a" * 51 + "b", "dev_a")
