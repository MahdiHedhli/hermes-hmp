"""Read-only inspection against synthetic existing custody and real SQLite state."""
import json
import sqlite3

import pytest

from hmp_plugin import cli, operator_read, server
from hmp_plugin.store import Store

from . import hmp_kit
from .test_cli import Cli


def _fixture(tmp_path, monkeypatch):
    env = hmp_kit.Env(tmp_path)
    env.store.insert_user('user_a', 'owner', 1)
    env.store.insert_device('dev_a', 'user_a', 'f' * 52, b'public', 'phone', 1, state='ACTIVE')
    c = Cli(env)
    c.write_record(profiles=[])
    decision = env.store.media_read_decision(env.iid, 'dev_a')

    def reply(_path, *, iid, nonce, device_id):
        assert iid == env.iid and device_id == 'dev_a'
        return {'decision': decision._asdict(), 'effective': False, 'host_enabled': False,
                    'api_available': True, 'nonce': nonce, 'generation': 'b' * 32,
                'expires_ms': 2 ** 52}

    monkeypatch.setattr(operator_read, 'read_media_context', reply)
    monkeypatch.setattr(cli, '_open', lambda *_a, **_k: pytest.fail('mutable context opened'))
    monkeypatch.setattr(Store, 'migrate', lambda *_a, **_k: pytest.fail('migration attempted'))
    return env, c, decision


@pytest.mark.parametrize('wal', (False, True))
def test_inspect_existing_state_without_mutable_store(tmp_path, monkeypatch, wal):
    env, c, decision = _fixture(tmp_path, monkeypatch)
    path = server.store_path(env.custody.anchor_dir)
    if not wal:
        env.store.close()
    before = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()
              and not p.name.endswith('-shm')}
    try:
        # Inspection is not newly gated by setup compatibility or served-profile count.
        c.compat = hmp_kit.UNSUPPORTED
        assert c.run('devices', 'media-read', 'dev_a') == 0, c.err
        assert json.loads(c.out) == {
            'device_id': 'dev_a', 'explicit_media_read': decision.allowed,
            'effective_entitlement': False, 'revision': decision.revision, 'host_enabled': False,
            'api_available': True, 'per_bot_authorization': 'required separately',
        }
        after = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()
                 and not p.name.endswith('-shm')}
        assert after == before
        if not wal:
            assert not path.with_name(path.name + '-wal').exists()
            assert not path.with_name(path.name + '-shm').exists()
    finally:
        env.store.close()


@pytest.mark.parametrize('failure', ('listener', 'decision', 'inactive', 'schema', 'missing'))
def test_inspection_refuses_unavailable_or_changed_authority(tmp_path, monkeypatch, failure):
    env, c, _decision = _fixture(tmp_path, monkeypatch)
    try:
        if failure == 'listener':
            c.listener_live = False
        elif failure == 'decision':
            previous = env.store.media_read_decision(env.iid, 'dev_a')
            env.store.set_media_read(previous, allowed=True, now=2)
        elif failure in ('inactive', 'schema'):
            with env.store.transaction() as conn:
                if failure == 'inactive':
                    conn.execute("UPDATE devices SET state='REVOKED' WHERE device_id='dev_a'")
                else:
                    conn.execute('UPDATE meta SET schema_version=3 WHERE id=1')
        else:
            env.store.close()
            server.store_path(env.custody.anchor_dir).unlink()
        assert c.run('devices', 'media-read', 'dev_a') != 0
        assert c.out == ''
        assert 'refused' in c.err.lower() or 'not ready' in c.err.lower()
    finally:
        env.store.close()


def test_inspection_adapter_enforces_readonly_connection(tmp_path, monkeypatch):
    env, _c, _decision = _fixture(tmp_path, monkeypatch)
    try:
        with (cli._media_inspection_connection(server.store_path(env.custody.anchor_dir)) as conn,
              pytest.raises(sqlite3.OperationalError, match='readonly')):
            conn.execute('DELETE FROM devices')
    finally:
        env.store.close()


def test_identity_epoch_changed_after_decision_refuses(tmp_path, monkeypatch):
    env, c, _decision = _fixture(tmp_path, monkeypatch)
    original = cli._ReadOnlyMediaStore.media_read_decision

    def changed(store, iid, device_id):
        result = original(store, iid, device_id)
        with env.store.transaction() as conn:
            conn.execute('UPDATE meta SET '
                         'store_revocation_epoch=store_revocation_epoch+1 WHERE id=1')
        return result

    monkeypatch.setattr(cli._ReadOnlyMediaStore, 'media_read_decision', changed)
    try:
        assert c.run('devices', 'media-read', 'dev_a') != 0
        assert c.out == ''
    finally:
        env.store.close()


def test_missing_wal_shared_memory_refuses_without_creating_files(tmp_path, monkeypatch):
    env, c, _decision = _fixture(tmp_path, monkeypatch)
    path = server.store_path(env.custody.anchor_dir)
    env.store.close()
    wal = path.with_name(path.name + '-wal')
    wal.write_bytes(b'synthetic-incomplete-wal')
    assert not path.with_name(path.name + '-shm').exists()
    before = path.read_bytes()
    assert c.run('devices', 'media-read', 'dev_a') != 0
    assert c.out == '' and path.read_bytes() == before
    assert wal.read_bytes() == b'synthetic-incomplete-wal'
    assert not path.with_name(path.name + '-shm').exists()


@pytest.mark.parametrize('changed', ('epoch', 'decision'))
def test_gateway_wal_appears_during_roundtrip_observed_fresh(tmp_path, monkeypatch, changed):
    env, c, decision = _fixture(tmp_path, monkeypatch)
    path = server.store_path(env.custody.anchor_dir)
    env.store.close()
    assert not path.with_name(path.name + '-wal').exists()
    writer = sqlite3.connect(path)
    try:
        def reply(_path, *, iid, nonce, device_id):
            writer.execute('PRAGMA journal_mode=WAL')
            if changed == 'epoch':
                writer.execute('UPDATE meta SET '
                               'store_revocation_epoch=store_revocation_epoch+1 WHERE id=1')
            else:
                writer.execute(
                    'INSERT INTO device_media_read(iid,device_id,allowed,updated_at) '
                    'VALUES(?,?,1,2)',
                    (iid, device_id),
                )
            writer.commit()
            assert path.with_name(path.name + '-wal').exists()
            return {'decision': decision._asdict(), 'effective': False, 'host_enabled': False,
                    'api_available': True, 'nonce': nonce, 'generation': 'b' * 32,
                    'expires_ms': 2 ** 52}

        monkeypatch.setattr(operator_read, 'read_media_context', reply)
        assert c.run('devices', 'media-read', 'dev_a') != 0
        assert c.out == ''
    finally:
        writer.close()
