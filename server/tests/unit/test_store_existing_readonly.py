"""Ordinary Store definitions with inert sqlite/lock namespaces; no DB or threads."""

from __future__ import annotations

import traceback
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hmp_plugin import store as store_module

_PATCHES = []


def _restore_patches():
    while _PATCHES:
        _PATCHES.pop().stop()


class Cancel(BaseException):
    pass


class ModelLock:
    def __init__(self):
        self.held = False

    def __enter__(self):
        if self.held:
            raise AssertionError("inert lock would block; no real thread was launched")
        self.held = True
        return self

    def __exit__(self, *args):
        self.held = False


class Cursor:
    def __init__(self, backend, rows, sql):
        self.backend = backend
        self.rows = rows
        self.sql = sql

    def fetchone(self):
        self.backend.event("fetchone", self.sql)
        return self.rows[0] if self.rows else None

    def fetchmany(self, count):
        assert count == 2
        self.backend.event("fetchmany", self.sql)
        return self.rows[:count]

    def fetchall(self):
        self.backend.event("fetchall", self.sql)
        return self.rows[:]


class Connection:
    def __init__(self, backend):
        self.backend = backend
        self.closed = 0

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value):
        self.backend.event("row_factory", value)
        self._row_factory = value

    def execute(self, sql, args=()):
        self.backend.sql.append((sql, args))
        self.backend.event("execute", sql)
        data = self.backend
        if sql in {"BEGIN", "ROLLBACK"}:
            rows = []
        elif "length(CAST(sql AS BLOB))" in sql:
            value = data.catalog.get(tuple(args))
            rows = [] if value is None else [{"sql_bytes": len(value.encode())}]
            if data.catalog_count is not None:
                rows = [{"sql_bytes": data.catalog_count}]
        elif sql.startswith("SELECT sql FROM sqlite_master"):
            kind, name = args if len(args) == 2 else ("trigger", args[0])
            value = data.catalog.get((kind, name))
            rows = [] if value is None else [{"sql": value}]
            if data.catalog_rows is not None:
                rows = rows * data.catalog_rows
        elif "COUNT(*) AS trigger_count" in sql:
            rows = [{"trigger_count": data.trigger_count}]
        elif "SELECT name FROM sqlite_master" in sql:
            rows = [{"name": name} for name in data.ns["_REQUEST_TRIGGERS"]]
        elif sql == "SELECT schema_version FROM meta WHERE id = 1":
            rows = [] if data.meta_missing else [{"schema_version": data.version}]
        elif "SELECT high_water" in sql:
            rows = [{"high_water": data.high_water}]
        elif sql == "PRAGMA foreign_key_check":
            rows = data.foreign_key_rows
        elif sql.startswith("SELECT 1 FROM device_owner_controls"):
            rows = data.revision_rows
        elif sql == "SELECT instance_epoch, store_revocation_epoch FROM meta WHERE id = 1":
            rows = (
                []
                if data.meta_missing
                else [{"instance_epoch": data.epochs[0], "store_revocation_epoch": data.epochs[1]}]
            )
        elif sql == "SELECT store_revocation_epoch FROM meta WHERE id = 1":
            rows = [] if data.meta_missing else [{"store_revocation_epoch": data.epochs[1]}]
        elif sql == "SELECT * FROM devices WHERE device_id = ?":
            rows = [data.device] if data.device is not None else []
        elif "FROM access_tokens AS a" in sql:
            rows = [data.access] if data.access is not None else []
        elif sql.startswith("SELECT * FROM chats WHERE"):
            rows = [data.chat] if data.chat is not None else []
        else:
            raise AssertionError(f"undeclared source SQL: {sql}")
        return Cursor(data, rows, sql)

    def close(self):
        self.closed += 1
        self.backend.event("close", self)


class Backend:
    def __init__(self):
        self.ns = None
        self.catalog = {}
        self.calls = []
        self.sql = []
        self.events = []
        self.hook = None
        self.version = 3
        self.epochs = (4, 8)
        self.meta_missing = False
        self.high_water = 0
        self.foreign_key_rows = []
        self.revision_rows = []
        self.catalog_count = None
        self.catalog_rows = None
        self.trigger_count = 3
        self.device = {"device_id": "d", "state": "ACTIVE", "user_id": "u"}
        self.access = {"access_iid": "i", "device_state": "ACTIVE"}
        self.chat = {"chat_id": "c"}
        self.connection = Connection(self)

    def event(self, kind, value):
        self.events.append((kind, value))
        if self.hook is not None:
            self.hook(kind, value)

    def connect(self, database, **kwargs):
        self.calls.append((database, kwargs))
        self.event("connect", database)
        return self.connection


def source():
    backend = Backend()
    # Replace the Store module attributes only, never shared sqlite3.connect or sys.modules.
    # This precedes every tested factory operation; failure cleanup is also inert.
    for name, value in [
        ("sqlite3", SimpleNamespace(connect=backend.connect, Row=dict)),
        ("threading", SimpleNamespace(Lock=ModelLock, get_ident=lambda: 1)),
    ]:
        replacement = patch.object(store_module, name, value)
        replacement.start()
        _PATCHES.append(replacement)
    ns = vars(store_module).copy()
    backend.ns = ns
    statement = []
    for lexeme in ns["_readonly_sql_tokens"](ns["_SCHEMA"]):
        statement.append(lexeme)
        if lexeme == ";":
            normalized = ns["_readonly_table_tokens"](tuple(statement))
            backend.catalog[("table", normalized[2])] = " ".join(statement)
            statement = []
    for sql in ns["_REQUEST_SCHEMA"]:
        backend.catalog[
            ("index" if sql.startswith("CREATE INDEX") else "table", sql.split()[2])
        ] = sql
    for name, sql in ns["_REQUEST_TRIGGERS"].items():
        backend.catalog[("trigger", name)] = sql
    return ns, backend


def opened():
    ns, backend = source()
    reader = ns["Store"].open_existing_readonly(
        Path("/inert/existing.db"), view=ns["ExistingReadView"].LIVE_WAL
    )
    return ns, backend, reader


class TestExistingStoreReader(unittest.TestCase):
    def setUp(self):
        self.addCleanup(_restore_patches)

    def refusal(self, ns, call):
        with self.assertRaises(ns["ExistingStoreReadOnlyError"]) as caught:
            call()
        self.assertEqual(str(caught.exception), "HMP existing store read view unavailable")
        return caught.exception

    def test_rs01_preservation(self):
        ns, _ = source()
        self.assertEqual(
            len(
                [
                    n
                    for n in ns["Store"].__dict__
                    if callable(getattr(ns["Store"], n)) and not n.startswith("__")
                ]
            ),
            57,
        )
        self.assertIn("PRAGMA journal_mode=WAL", ns["Store"].migrate.__code__.co_consts)

    def test_rs02_restricted_surface(self):
        ns, backend, reader = opened()
        for name in [
            "migrate",
            "transaction",
            "revoke_all_for_identity_change",
            "execute",
            "connection",
        ]:
            self.assertFalse(hasattr(reader, name))
        self.refusal(ns, ns["ExistingStoreReader"])
        forged = object.__new__(ns["ExistingStoreReader"])
        forged._custody = ns["_ReadOnlyCustody"]()
        forged._custody.connection = backend.connection
        self.refusal(ns, forged.close)
        self.assertEqual(backend.connection.closed, 0)

        class Foreign(ns["Store"]):
            pass

        self.refusal(
            ns,
            lambda ns=ns: Foreign.open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )

    def test_rs03_path_view(self):
        for path, view in [
            (Path("relative"), "live"),
            (Path("/x"), True),
            (Path("/x"), "live_wal"),
            (Path("/nul\0"), None),
        ]:
            ns, b = source()
            self.refusal(
                ns,
                lambda ns=ns, path=path, view=view: ns["Store"].open_existing_readonly(
                    path, view=view
                ),
            )
            self.assertEqual(b.calls, [])
        ns, b = source()
        with self.assertRaises(TypeError):
            ns["Store"].open_existing_readonly(Path("/x"))
        ns["Store"].open_existing_readonly(
            Path("/has?#%.db"), view=ns["ExistingReadView"].LIVE_WAL
        ).close()
        self.assertEqual(b.calls[0][0], "file:///has%3F%23%25.db?mode=ro")

    def test_rs04_open_arguments(self):
        for view, suffix in [
            ("LIVE_WAL", "?mode=ro"),
            ("QUIESCENT_IMMUTABLE", "?mode=ro&immutable=1"),
        ]:
            ns, b = source()
            reader = ns["Store"].open_existing_readonly(
                Path("/existing"), view=getattr(ns["ExistingReadView"], view)
            )
            self.assertTrue(b.calls[0][0].endswith(suffix))
            self.assertEqual(
                b.calls[0][1],
                {
                    "uri": True,
                    "isolation_level": None,
                    "check_same_thread": False,
                    "cached_statements": 0,
                },
            )
            self.assertIs(b.connection.row_factory, dict)
            reader.close()

    def test_rs05_no_repair_writes(self):
        ns, b, reader = opened()
        reader.get_device("d")
        reader.close()
        for sql, _ in b.sql:
            self.assertTrue(
                sql.startswith("SELECT ")
                or sql in {"BEGIN", "ROLLBACK", "PRAGMA foreign_key_check"},
                sql,
            )
        for failure in [
            FileNotFoundError("private missing"),
            PermissionError("private denied"),
            ValueError("private corrupt"),
        ]:
            ns, b = source()
            b.hook = lambda k, v, f=failure: (_ for _ in ()).throw(f) if k == "connect" else None
            error = self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
            self.assertEqual(error._custody.phase, "OPEN_UNKNOWN")
            self.assertEqual(len(b.calls), 1)
            self.assertEqual(b.connection.closed, 0)

    def test_rs06_validation_origin(self):
        for value in [2, 4, None, True]:
            ns, b = source()
            b.version = value
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
            self.assertEqual(b.connection.closed, 1)
        for epochs in [(-1, 0), (0, True), ("4", 0)]:
            ns, b = source()
            b.epochs = epochs
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
        for malformed in [None, (1,), (1, 2, 3), (True, 0), (0, -1), (0, "2")]:
            ns, b = source()
            with patch.object(ns["Store"], "epoch_authority_snapshot", return_value=malformed):
                self.refusal(
                    ns,
                    lambda ns=ns: ns["Store"].open_existing_readonly(
                        Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                    ),
                )
            self.assertEqual(b.connection.closed, 1)
        ns, b = source()
        b.meta_missing = True
        self.refusal(
            ns,
            lambda: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )
        ns, b, reader = opened()
        self.assertEqual(b.sql[0][0], "BEGIN")
        self.assertEqual(b.sql[-1][0], "ROLLBACK")
        reader.close()

    def test_rs07_schema_changes(self):
        changes = [
            ("meta", "INTEGER PRIMARY KEY", "TEXT PRIMARY KEY"),
            ("meta", "CHECK ( id = 1 )", "CHECK ( id = 2 )"),
            ("devices", "REFERENCES users", "REFERENCES devices"),
            ("devices", "'ACTIVE'", "'INACTIVE'"),
            ("devices", "NOT NULL", "NULL"),
            ("chats", "user_id TEXT", "user_id INTEGER"),
            ("chats", "PRIMARY KEY", "UNIQUE"),
        ]
        for name, old, new in changes:
            ns, b = source()
            self.assertIn(old, b.catalog[("table", name)])
            b.catalog[("table", name)] = b.catalog[("table", name)].replace(old, new)
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
        for kind in ["view", None]:
            ns, b = source()
            sql = b.catalog.pop(("table", "meta"))
            if kind is not None:
                b.catalog[(kind, "meta")] = sql
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
        ns, b = source()
        b.trigger_count = 4
        self.refusal(
            ns,
            lambda ns=ns: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )

    def test_rs08_caps(self):
        ns, _ = source()
        scan = ns["_readonly_sql_tokens"]
        self.assertEqual(scan(" " * 16_384), ())
        self.assertEqual(len(scan("(" * 4096)), 4096)
        for sql in [" " * 16_385, "(" * 4097]:
            with self.assertRaises(ValueError):
                scan(sql)
        for count in [16_385, -1, True, None, "100"]:
            ns, b = source()
            if count is None:
                b.catalog[("table", "meta")] = "x" * 16_385
            else:
                b.catalog_count = count
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
            self.assertFalse(any(sql.startswith("SELECT sql FROM") for sql, _ in b.sql))
        ns, b = source()
        b.catalog_rows = 2
        self.refusal(
            ns,
            lambda ns=ns: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )
        for count in [-1, True, None, "3", 4]:
            ns, b = source()
            b.trigger_count = count
            self.refusal(
                ns,
                lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
            self.assertFalse(any(kind == "fetchall" for kind, _ in b.events))
        ns, b = source()
        trigger = next(iter(ns["_REQUEST_TRIGGERS"]))
        b.catalog[("trigger", trigger)] = " " * 16_385
        self.refusal(
            ns,
            lambda: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )
        self.assertFalse(any(kind == "fetchall" for kind, _ in b.events))

    def test_rs09_tokenizer(self):
        ns, _ = source()
        scan, norm = ns["_readonly_sql_tokens"], ns["_readonly_table_tokens"]
        self.assertEqual(scan("A/*x*/B --end"), ("A", "B"))
        self.assertEqual(
            scan('\'--/*x*/\' "a""b" `a``b` [abc]'), ("'--/*x*/'", '"a""b"', "`a``b`", "[abc]")
        )
        for sql in [
            "/*",
            "/* /* nested */",
            "'bad",
            '"bad',
            "`bad",
            "[bad",
            "[a]]",
            "x\0",
            "x\x01",
            "é",
            "x@",
        ]:
            with self.assertRaises(ValueError):
                scan(sql)
        base = "CREATE TABLE IF NOT EXISTS t (v TEXT CHECK (v = 'ACTIVE'));"
        self.assertEqual(
            norm(scan(base)),
            norm(scan(base.replace("IF NOT EXISTS ", "").replace(" TEXT ", " /*c*/ TEXT "))),
        )
        for sql in [
            base + ";",
            base + " CREATE TABLE u (x TEXT);",
            base.replace("'ACTIVE'", "'active'"),
            base.replace("CHECK", "/*CHECK*/"),
        ]:
            try:
                value = norm(scan(sql))
            except ValueError:
                continue
            self.assertNotEqual(value, norm(scan(base)))

    def test_rs10_delegates(self):
        _ns, b, reader = opened()
        self.assertTrue(reader.request_schema_ready())
        self.assertEqual(reader.revocation_epoch(), 8)
        self.assertEqual(reader.epoch_authority_snapshot(), (4, 8))
        self.assertEqual(reader.get_device("d"), b.device)
        self.assertEqual(reader.access_authority_snapshot(b"hash"), b.access)
        self.assertEqual(reader.get_chat("u", "p", "c"), b.chat)
        reader.close()

    def test_rs11_current_origin_and_false(self):
        for value in [None, (-1, 8), (True, 8)]:
            ns, b, reader = opened()
            if value is None:
                b.meta_missing = True
            else:
                b.epochs = value
            self.refusal(ns, reader.revocation_epoch)
            reader.close()
        for malformed in [None, (1,), (1, 2, 3), (True, 0), (0, -1), (0, "2")]:
            ns, _b, reader = opened()
            with patch.object(ns["Store"], "epoch_authority_snapshot", return_value=malformed):
                self.refusal(ns, reader.revocation_epoch)
            reader.close()
        ns, b, reader = opened()
        b.version = 2
        self.assertFalse(reader.request_schema_ready())
        effects = len(b.sql)
        self.refusal(ns, lambda reader=reader: reader.get_device("d"))
        self.assertEqual(len(b.sql), effects)
        reader.close()

    def test_rs12_reentry(self):
        epoch_sql = "SELECT instance_epoch, store_revocation_epoch FROM meta WHERE id = 1"
        device_sql = "SELECT * FROM devices WHERE device_id = ?"
        boundaries = [
            ("execute", "BEGIN"),
            ("execute", epoch_sql),
            ("fetchone", epoch_sql),
            ("execute", device_sql),
            ("fetchone", device_sql),
            ("execute", "ROLLBACK"),
            ("close", None),
        ]
        for boundary_kind, boundary_sql in boundaries:
            for nested in ["read", "close"]:
                ns, b, reader = opened()
                fired = []
                baseline_rollbacks = sum(sql == "ROLLBACK" for sql, _ in b.sql)

                def hook(
                    kind,
                    value,
                    ns=ns,
                    reader=reader,
                    nested=nested,
                    fired=fired,
                    boundary_kind=boundary_kind,
                    boundary_sql=boundary_sql,
                ):
                    if (
                        kind == boundary_kind
                        and (boundary_sql is None or value == boundary_sql)
                        and not fired
                    ):
                        fired.append(1)
                        self.assertTrue(reader._lock.held)
                        self.refusal(
                            ns, reader.revocation_epoch if nested == "read" else reader.close
                        )

                b.hook = hook
                self.refusal(
                    ns,
                    reader.close
                    if boundary_kind == "close"
                    else lambda reader=reader: reader.get_device("d"),
                )
                self.assertEqual(fired, [1])
                self.assertIsNotNone(reader._custody.first_failure)
                if boundary_kind == "execute" and boundary_sql == "BEGIN":
                    self.assertFalse(any(sql == device_sql for sql, _ in b.sql))
                if boundary_sql == "ROLLBACK":
                    self.assertEqual(
                        sum(sql == "ROLLBACK" for sql, _ in b.sql), baseline_rollbacks + 1
                    )
                b.hook = None
                reader.close()
                self.assertEqual(b.connection.closed, 1)
                self.assertFalse(reader._lock.held)

    def test_rs13_returned_handle_ownership(self):
        ns, b = source()
        private = ValueError("PRIVATE_ROW_FACTORY")
        b.hook = lambda k, v: (_ for _ in ()).throw(private) if k == "row_factory" else None
        error = self.refusal(
            ns,
            lambda ns=ns: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )
        self.assertIs(error._custody.first_failure, private)
        self.assertEqual(b.connection.closed, 1)
        self.assertEqual(error._custody.phase, "CLOSED")

    def test_rs14_close_once(self):
        ns, b, reader = opened()
        reader.close()
        reader.close()
        self.assertEqual(b.connection.closed, 1)
        self.assertIsNone(reader._custody.connection)
        self.refusal(ns, reader.revocation_epoch)
        for failure in [ValueError("PRIVATE_CLOSE"), Cancel("cancel")]:
            ns, b, reader = opened()
            b.hook = lambda k, v, f=failure: (_ for _ in ()).throw(f) if k == "close" else None
            if isinstance(failure, Exception):
                self.refusal(ns, reader.close)
            else:
                with self.assertRaises(Cancel) as caught:
                    reader.close()
                self.assertIs(caught.exception, failure)
            self.refusal(ns, reader.close)
            self.refusal(ns, reader.revocation_epoch)
            self.assertEqual(b.connection.closed, 1)
            self.assertIs(reader._custody.connection, b.connection)
            self.assertEqual(reader._custody.phase, "CLOSE_UNKNOWN")

    def test_rs15_all_failed_primitives_retained(self):
        ns, b = source()
        failures = {
            "validation": ValueError("PRIVATE_VALIDATION"),
            "rollback": ValueError("PRIVATE_ROLLBACK"),
            "close": ValueError("PRIVATE_CLOSE"),
        }

        def hook(kind, value):
            if kind == "execute" and "length(CAST(sql AS BLOB))" in value:
                raise failures["validation"]
            if kind == "execute" and value == "ROLLBACK":
                raise failures["rollback"]
            if kind == "close":
                raise failures["close"]

        b.hook = hook
        error = self.refusal(
            ns,
            lambda ns=ns: ns["Store"].open_existing_readonly(
                Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
            ),
        )
        state = error._custody
        self.assertIs(state.first_failure, failures["validation"])
        self.assertEqual(
            state.cleanup_failures,
            [("rollback", failures["rollback"]), ("close", failures["close"])],
        )
        self.assertIs(state.connection, b.connection)
        self.assertEqual([sql for sql, _ in b.sql].count("ROLLBACK"), 1)
        self.assertEqual(b.connection.closed, 1)
        self.assertNotIn("PRIVATE_", "".join(traceback.format_exception(error)))

    def test_rs16_read_failure_cancel(self):
        for failure in [ValueError("PRIVATE_READ"), Cancel("cancel")]:
            ns, b, reader = opened()

            def hook(kind, value, f=failure):
                if kind == "fetchone" and value == "SELECT * FROM devices WHERE device_id = ?":
                    raise f

            b.hook = hook
            if isinstance(failure, Exception):
                self.refusal(ns, lambda reader=reader: reader.get_device("d"))
            else:
                with self.assertRaises(Cancel) as caught:
                    reader.get_device("d")
                self.assertIs(caught.exception, failure)
            effects = len(b.sql)
            self.refusal(ns, reader.revocation_epoch)
            self.assertEqual(len(b.sql), effects)
            b.hook = None
            reader.close()
            self.assertIs(reader._custody.first_failure, failure)

        ns, b, reader = opened()
        failure = ValueError("PRIVATE_READ_CHAIN")
        rollback = ValueError("PRIVATE_ROLLBACK_CHAIN")
        close = ValueError("PRIVATE_CLOSE_CHAIN")
        before_rollbacks = sum(sql == "ROLLBACK" for sql, _ in b.sql)

        def chain_hook(kind, value):
            if kind == "fetchone" and value == "SELECT * FROM devices WHERE device_id = ?":
                raise failure
            if kind == "execute" and value == "ROLLBACK":
                raise rollback
            if kind == "close":
                raise close

        b.hook = chain_hook
        error = self.refusal(ns, lambda: reader.get_device("d"))
        self.assertIs(reader._custody.first_failure, failure)
        self.assertEqual(reader._custody.cleanup_failures, [("rollback", rollback)])
        close_error = self.refusal(ns, reader.close)
        self.refusal(ns, reader.close)
        self.assertEqual(
            reader._custody.cleanup_failures, [("rollback", rollback), ("close", close)]
        )
        self.assertIs(reader._custody.connection, b.connection)
        self.assertEqual(sum(sql == "ROLLBACK" for sql, _ in b.sql), before_rollbacks + 1)
        self.assertEqual(b.connection.closed, 1)
        self.assertNotIn("PRIVATE_", "".join(traceback.format_exception(error)))
        self.assertNotIn("PRIVATE_", "".join(traceback.format_exception(close_error)))

    def test_rs17_privacy_same_error_type(self):
        for kind in [
            "connect",
            "row_factory",
            "execute",
            "fetchone",
            "fetchmany",
            "fetchall",
            "close",
        ]:
            ns, b = source()
            reader = None
            if kind == "close":
                reader = ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                )
            private = ns["ExistingStoreReadOnlyError"]()
            private.args = ("PRIVATE_MESSAGE",)
            private.add_note("PRIVATE_NOTE")
            private.__cause__ = ValueError("PRIVATE_CAUSE")
            fired = []

            def hook(k, value, kind=kind, fired=fired, private=private):
                if k == kind and not fired:
                    fired.append(1)
                    raise private

            b.hook = hook
            error = self.refusal(
                ns,
                reader.close
                if reader
                else lambda ns=ns: ns["Store"].open_existing_readonly(
                    Path("/x"), view=ns["ExistingReadView"].LIVE_WAL
                ),
            )
            self.assertIsNot(error, private)
            self.assertIs(error._custody.first_failure, private)
            self.assertIsNone(error.__cause__)
            self.assertNotIn("PRIVATE_", "".join(traceback.format_exception(error)))

    def test_rs18_no_authority_claim(self):
        ns, _, reader = opened()
        for name in ["continuation", "claim", "inode", "currentness", "issuer", "grant", "actor"]:
            self.assertFalse(hasattr(reader, name))
        self.assertEqual(
            set(ns["ExistingReadView"].__members__), {"LIVE_WAL", "QUIESCENT_IMMUTABLE"}
        )
        reader.close()

    def test_rs19_independent_lock_and_owned_close(self):
        ns, b, reader = opened()
        self.assertIsNot(reader._lock, reader._store._write_lock)
        foreign = Connection(b)
        reader._store._conn = foreign
        self.refusal(ns, reader.revocation_epoch)
        reader.close()
        self.assertEqual(b.connection.closed, 1)
        self.assertEqual(foreign.closed, 0)

    def test_rs20_inert_scope(self):
        ns, b, reader = opened()
        self.assertIs(ns["sqlite3"].connect.__self__, b)
        self.assertIsInstance(reader._lock, ModelLock)
        self.assertEqual(len(b.calls), 1)
        reader.close()


if __name__ == "__main__":
    unittest.main()
