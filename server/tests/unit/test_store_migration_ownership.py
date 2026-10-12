"""Connection handoff failures with inert connections, paths and synchronization."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hmp_plugin import store as store_module


class StopMigration(BaseException):
    pass


class InertLock:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class MigrationHarness:
    def __init__(
        self,
        module,
        monkeypatch,
        *,
        existing=False,
        fail=None,
        error_type=RuntimeError,
        cleanup_type=None,
        version=2,
    ):
        self.events = []
        self.fail = fail
        self.setup_failure = error_type("synthetic migration failure")
        self.cleanup_failure = cleanup_type("synthetic close failure") if cleanup_type else None
        self.connects = 0
        self.closes = 0
        self.returned = False
        self.caught = None
        self.module = module
        harness = self

        class InertPath:
            @property
            def parent(self):
                return self

            def mkdir(self, **_kwargs):
                harness.step("mkdir")

            def __str__(self):
                return "inert-database"

        class InertConnection:
            def __setattr__(self, name, value):
                if name == "row_factory":
                    harness.step("row_factory")
                object.__setattr__(self, name, value)

            def execute(self, sql):
                harness.step("execute:" + sql)
                return SimpleNamespace(fetchone=lambda: self.fetch(sql))

            def fetch(self, sql):
                harness.step("fetch:" + sql)
                if "sqlite_master" in sql:
                    return {"exists": True}
                return {"schema_version": version}

            def executescript(self, _sql):
                harness.step("schema")

            def close(self):
                harness.closes += 1
                if harness.cleanup_failure is not None:
                    raise harness.cleanup_failure

        self.connection = InertConnection()

        def connect(*_args, **_kwargs):
            harness.connects += 1
            harness.step("connect")
            return harness.connection

        monkeypatch.setattr(module, "sqlite3", SimpleNamespace(connect=connect, Row=object()))
        monkeypatch.setattr(
            module, "threading", SimpleNamespace(Lock=InertLock, get_ident=lambda: 7)
        )
        monkeypatch.setattr(module, "_widen_cmid_status", lambda _conn: harness.step("widen"))
        monkeypatch.setattr(
            module, "_migrate_request_schema", lambda _conn: harness.step("request_schema")
        )
        self.store = module.Store(InertPath())
        if existing:
            self.store._conn = self.connection

    def step(self, event):
        self.events.append(event)
        if len(self.events) - 1 == self.fail:
            raise self.setup_failure

    def run(self):
        try:
            self.store.migrate()
            self.returned = True
        except BaseException as error:
            self.caught = error
        return self


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("error_type", [RuntimeError, StopMigration])
def test_migration_failure_preserves_connection_ownership(monkeypatch, existing, error_type):
    baseline = MigrationHarness(store_module, monkeypatch, existing=existing).run()
    assert baseline.returned and baseline.caught is None and baseline.closes == 0
    for index, event in enumerate(list(baseline.events)):
        harness = MigrationHarness(
            store_module, monkeypatch, existing=existing, fail=index, error_type=error_type
        ).run()
        assert harness.caught is harness.setup_failure and not harness.returned, event
        owns_new = not existing and event not in ("mkdir", "connect")
        assert harness.closes == int(owns_new), event
        assert harness.store._conn is (harness.connection if existing else None)
        # Directory failure precedes connection setup and retains existing poison behavior.
        assert harness.store._poisoned is (event != "mkdir")
        if event != "mkdir":
            connects = harness.connects
            with pytest.raises(RuntimeError, match="Store connection state unavailable"):
                harness.store.migrate()
            assert harness.connects == connects
        # Store.close must not close an unpublished new connection for a second time.
        harness.store.close()
        assert harness.closes == int(owns_new) + int(existing)


@pytest.mark.parametrize("error_type", [RuntimeError, StopMigration])
@pytest.mark.parametrize("cleanup_type", [RuntimeError, StopMigration])
def test_migration_cleanup_failure_retains_handle_and_both_causes(
    monkeypatch, error_type, cleanup_type
):
    baseline = MigrationHarness(store_module, monkeypatch).run()
    for index, event in enumerate(list(baseline.events)):
        if event in ("mkdir", "connect"):
            continue
        harness = MigrationHarness(
            store_module,
            monkeypatch,
            fail=index,
            error_type=error_type,
            cleanup_type=cleanup_type,
        ).run()
        error = harness.caught
        assert isinstance(error, store_module._MigrationCleanupError), event
        assert error.setup_failure is harness.setup_failure
        assert error.__cause__ is harness.setup_failure
        assert error.cleanup_failure is harness.cleanup_failure
        assert error.connection is harness.connection and error.connection_close_unknown is True
        assert harness.closes == 1 and not harness.returned
        assert harness.store._conn is None and harness.store._poisoned is True
        assert str(error) == "HMP store migration failed with unresolved connection cleanup"
        harness.store.close()
        assert harness.closes == 1
        connects = harness.connects
        with pytest.raises(RuntimeError, match="Store connection state unavailable"):
            harness.store.migrate()
        assert harness.connects == connects and harness.closes == 1


@pytest.mark.parametrize("existing", [False, True])
def test_migration_success_keeps_connection_for_owner(monkeypatch, existing):
    harness = MigrationHarness(store_module, monkeypatch, existing=existing).run()
    assert harness.returned and harness.caught is None
    assert harness.store._conn is harness.connection and harness.closes == 0
    assert harness.connects == int(not existing)
    harness.store.close()
    assert harness.closes == 1 and harness.store._conn is None


@pytest.mark.parametrize("existing", [False, True])
def test_future_schema_still_refused_before_writes(monkeypatch, existing):
    harness = MigrationHarness(
        store_module, monkeypatch, existing=existing, version=store_module.SCHEMA_VERSION + 1
    ).run()
    assert isinstance(harness.caught, RuntimeError)
    assert str(harness.caught) == "future store schema unavailable"
    assert not harness.returned and harness.store._poisoned
    assert not any("PRAGMA" in event or event == "schema" for event in harness.events)
    assert harness.closes == int(not existing)


def test_owned_transaction_gate_unchanged(monkeypatch):
    harness = MigrationHarness(store_module, monkeypatch)
    harness.store._transaction_owner = 7
    harness.run()
    assert str(harness.caught) == "migrate during owned transaction"
    assert harness.connects == harness.closes == 0 and harness.events == []


def test_close_failure_policy_for_published_connection_is_unchanged(monkeypatch):
    harness = MigrationHarness(store_module, monkeypatch, existing=True, cleanup_type=RuntimeError)
    with pytest.raises(RuntimeError) as first:
        harness.store.close()
    assert first.value is harness.cleanup_failure
    assert harness.store._conn is harness.connection and harness.store._poisoned
    with pytest.raises(RuntimeError) as second:
        harness.store.close()
    assert second.value is harness.cleanup_failure and harness.closes == 2
