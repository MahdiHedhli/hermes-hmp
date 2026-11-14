"""PN-OPS readonly diagnostics. Only isolated synthetic config/store fixtures."""

from __future__ import annotations

import argparse
import hashlib
import io

import pytest

from hmp_plugin import cli, identity, server
from hmp_plugin.store import Store

from .test_push_store import seed_device, seed_row

CONFIG = {
    "enabled": True,
    "relay_url": "https://relay.invalid/private-canary",
    "relay_audience": "private-audience-canary",
    "relay_kids": ["private-kid-canary"],
}


def run(root, store, reader=lambda _root: CONFIG, **overrides):
    out, err = io.StringIO(), io.StringIO()
    env = cli.CliEnv(
        environ={"HERMES_HOME": str(root), "HERMES_SESSION_TEST": "synthetic"},
        stdout=out,
        stderr=err,
        push_settings_reader=reader,
        identity_kwargs=overrides.pop(
            "identity_kwargs", {"hermes_root": root, "binding_root": root.parent / "binding"}
        ),
        **overrides,
    )
    parser = argparse.ArgumentParser()
    cli.setup_parser(parser)
    code = cli.dispatch(parser.parse_args(["push", "status"]), env)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "hermes"
    custody = identity.resolve_custody(
        env={"HERMES_HOME": str(root)}, hermes_root=root, binding_root=tmp_path / "binding"
    )
    custody.anchor_dir.mkdir(parents=True)
    store = Store(server.store_path(custody.anchor_dir))
    store.migrate()
    store.insert_user("user", "private-label-canary", 1)
    yield root, store
    store.close()


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_reads_live_wal_counts_without_migration_keys_authority_or_network(fixture, monkeypatch):
    root, store = fixture
    for name, state in (("active", "ACTIVE"), ("pending", "PENDING"), ("revoked", "REVOKED")):
        seed_device(store, name, state=state)
        seed_row(store, name, number=len(name), state="active" if name == "active" else "retired")
    # Deliberately expire the stored active row: this is stored state, not eligibility.
    with store.transaction() as conn:
        conn.execute("UPDATE push_registrations SET expires_at = 1")
    before = tuple(
        tuple(row) for row in store._require_conn().execute("SELECT * FROM push_registrations")
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unexpected authority/migration/network operation")

    monkeypatch.setattr(Store, "migrate", forbidden)
    monkeypatch.setattr(identity, "load_existing", forbidden)
    monkeypatch.setattr(cli, "_open", forbidden)
    code, out, err = run(root, store)
    assert code == 0 and not err
    assert out == (
        "push_enabled: yes\nrelay_configured: yes\nconfigured_kid_count: 1\n"
        "active_registration_count: 1\nnon_revoked_generation_count: 2\n"
    )
    assert before == tuple(
        tuple(row) for row in store._require_conn().execute("SELECT * FROM push_registrations")
    )
    assert not (root.parent / "binding").exists()
    assert not any(value in out for value in ("private", "active\n", "pending", "revoked\n"))


def test_checkpointed_read_changes_no_files(fixture):
    root, store = fixture
    store.close()
    before = hashes(root)
    assert run(root, store)[0] == 0
    assert hashes(root) == before


@pytest.mark.parametrize(
    "block,expected",
    [
        (CONFIG | {"enabled": False}, ("no", "yes", 1)),
        (CONFIG | {"enabled": "true"}, ("no", "yes", 1)),
        (
            CONFIG | {"relay_url": "https://user:private-secret-canary@relay.invalid"},
            ("yes", "no", 0),
        ),
        (CONFIG | {"relay_kids": ["invalid kid canary"]}, ("yes", "no", 0)),
        (None, ("no", "no", 0)),
    ],
)
def test_reports_literal_opt_in_and_valid_config_even_disabled(fixture, block, expected):
    root, store = fixture
    code, out, err = run(root, store, lambda _root: block)
    assert code == 0 and not err
    enabled, configured, kids = expected
    assert out.startswith(
        f"push_enabled: {enabled}\nrelay_configured: {configured}\nconfigured_kid_count: {kids}\n"
    )
    assert "canary" not in out + err


def test_reader_failure_is_unknown_not_disabled_and_never_echoed(fixture):
    root, store = fixture

    def fail(_root):
        raise ValueError("private-secret-path-canary")

    code, out, err = run(root, store, fail)
    assert code == 2 and not err
    assert "configuration_status: config_unavailable" in out
    assert "push_enabled: unavailable" in out
    assert "active_registration_count: 0" in out
    assert "canary" not in out


def test_missing_store_is_not_created(tmp_path):
    root = tmp_path / "missing"
    code, out, err = run(root, None)
    assert code == 2 and not err
    assert "store_status: store_unavailable" in out
    assert not root.exists()


@pytest.mark.parametrize("schema", [1, 2, 4])
def test_unqualified_store_is_not_migrated(fixture, schema):
    root, store = fixture
    with store.transaction() as conn:
        conn.execute("UPDATE meta SET schema_version = ?", (schema,))
    store.close()
    before = hashes(root)
    code, out, err = run(root, store)
    assert code == 2 and not err
    assert "active_registration_count: unavailable" in out
    assert hashes(root) == before


def test_unreadable_sqlite_is_not_migrated(fixture):
    root, store = fixture
    store.close()
    path = next(root.rglob("*.sqlite3"))
    path.write_bytes(b"private-corrupt-database-canary")
    before = hashes(root)
    code, out, err = run(root, store)
    assert code == 2 and not err and "store_unavailable" in out
    assert "canary" not in out and hashes(root) == before


def test_minimum_gate_failure_does_not_load_configuration_or_hide_store_counts(fixture):
    from hmp_plugin.compat import CompatResult, CompatStatus

    root, store = fixture
    code, out, err = run(root, store, None, compat=lambda: CompatResult(CompatStatus.UNSUPPORTED))
    assert code == 2 and not err
    assert "config_unavailable" in out and "active_registration_count: 0" in out


def test_named_profile_refuses_without_opening_files(fixture):
    root, store = fixture
    before = hashes(root)
    code, out, err = run(
        root,
        store,
        identity_kwargs={
            "hermes_root": root.parent / "other",
            "binding_root": root.parent / "binding",
        },
    )
    assert code == 2 and not out and "default profile" in err
    assert hashes(root) == before


def test_wal_without_shm_is_unavailable_without_creating_sidecar(fixture, tmp_path):
    root, _store = fixture
    source = server.store_path(
        identity.resolve_custody(
            env={"HERMES_HOME": str(root)}, hermes_root=root, binding_root=root.parent / "binding"
        ).anchor_dir
    )
    target = tmp_path / "readonly-copy.sqlite3"
    target.write_bytes(source.read_bytes())
    target.with_name(target.name + "-wal").write_bytes(
        source.with_name(source.name + "-wal").read_bytes()
    )
    before = hashes(tmp_path)
    assert cli._push_store_counts(target) is None
    assert hashes(tmp_path) == before


def test_default_reader_uses_only_gated_optional_diagnostics(fixture, monkeypatch):
    import sys

    from hmp_plugin import bridge
    from hmp_plugin.compat import CompatResult, CompatStatus

    root, store = fixture
    calls = []

    def read(path):
        calls.append(path)
        return CONFIG

    monkeypatch.setattr(bridge, "read_push_settings_for_diagnostics", read)
    # Other suite fixtures reload the native bridge in sys.modules. Bind the
    # injected reader at the actual lazy import target, not a stale package attr.
    monkeypatch.setitem(sys.modules, "hmp_plugin.bridge", bridge)
    code, out, err = run(root, store, None, compat=lambda: CompatResult(CompatStatus.SUPPORTED))
    assert code == 0 and not err and "relay_configured: yes" in out
    assert calls == [root]
