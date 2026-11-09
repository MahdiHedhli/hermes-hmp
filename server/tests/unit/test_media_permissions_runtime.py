"""Independent media permissions through real descriptor/fetch fixtures; no live host."""
import argparse
import asyncio
import io
from types import SimpleNamespace

import pytest

from hmp_plugin import cli, operator_read
from hmp_plugin.request_ctx import ServerContext
from hmp_plugin.store import Store

from .test_operator_read import (
    _operator_test_parent_fixture as _operator_test_parent_fixture,
)
from .test_operator_read import (
    _owned_operator_parent,
)
from .test_s5_media_fetch import Fx as FetchRig


def _decision(fx, device, allowed):
    store = fx.rig.env.store
    previous = store.media_read_decision(fx.ctx.iid, device.device_id)
    current = store.set_media_read(previous, allowed=allowed, now=fx.rig.env.clock())
    assert current is not None
    return current


def test_media_only_allow_fetches_without_approval_or_controls(tmp_path, monkeypatch):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        store = fx.rig.env.store
        store.set_owner_controls(device.device_id, allowed=False, now=fx.rig.env.clock())
        assert await fx.mint(client) == {}
        _decision(fx, device, True)
        assert not fx.ctx.is_approval_owner_device(device.device_id)
        assert not fx.ctx.is_owner_device(device.device_id)
        refs = await fx.mint(client)
        assert refs
        status, _headers, body = await fx.get(client, next(iter(refs.values())))
        assert status == 200 and body
        assert store.owner_controls_decision(device.device_id) is False
        assert device.device_id not in fx.rig.owners

    fx.run(scenario)


def test_deny_then_regrant_does_not_revive_old_references(tmp_path, monkeypatch):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        _decision(fx, device, True)
        old = next(iter((await fx.mint(client)).values()))
        _decision(fx, device, False)
        assert (await fx.get(client, old))[0] == 404
        _decision(fx, device, True)
        assert (await fx.get(client, old))[0] == 404
        new = next(iter((await fx.mint(client)).values()))
        assert new != old and (await fx.get(client, new))[0] == 200

    fx.run(scenario)


@pytest.mark.parametrize('phase', ('after_p1', 'after_p2'))
def test_late_worker_result_cannot_survive_deny_regrant(tmp_path, monkeypatch, phase):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client, owner=False)
        _decision(fx, device, True)
        ref = next(iter((await fx.mint(client)).values()))

        def revoke_and_restore():
            _decision(fx, device, False)
            _decision(fx, device, True)

        getattr(fx, phase).append(revoke_and_restore)
        assert (await fx.get(client, ref))[0] == 404
        assert fx.p1_in == 1

    fx.run(scenario)


def test_explicit_media_deny_closes_legacy_owner_without_changing_other_rights(
    tmp_path, monkeypatch,
):
    fx = FetchRig(tmp_path, monkeypatch)

    async def scenario(client):
        device = await fx.rig.pair(client)
        assert await fx.mint(client)
        _decision(fx, device, False)
        assert await fx.mint(client) == {}
        assert fx.ctx.is_approval_owner_device(device.device_id)
        assert fx.ctx.is_owner_device(device.device_id)

    fx.run(scenario)


def test_operator_media_roundtrip_is_read_only_and_scoped(tmp_path):
    store = Store(tmp_path / 'media.sqlite3')
    store.migrate()
    store.insert_user('user_a', 'owner', 1)
    store.insert_device('dev_a', 'user_a', 'f' * 52, b'public', 'phone', 1, state='ACTIVE')
    iid = 'a' * 52
    ctx = ServerContext(SimpleNamespace(iid=iid, still_current=lambda: True), store, None)
    service = operator_read.OperatorReadService(ctx, _owned_operator_parent() / 'anchor', 'a' * 32)
    before = store.media_read_decision(iid, 'dev_a')

    async def scenario():
        await service.start()
        try:
            reply = await asyncio.to_thread(
                operator_read.read_media_context, service.path,
                iid=iid, nonce='a' * 32, device_id='dev_a',
            )
            assert reply['decision'] == before._asdict()
            assert reply['effective'] is False and reply['host_enabled'] is False
        finally:
            assert await service.stop() == 0
            await service.wait_drained()

    try:
        asyncio.run(scenario())
        assert store.media_read_decision(iid, 'dev_a') == before
    finally:
        store.close()


@pytest.mark.parametrize('allowed', (True, False))
def test_operator_command_confirms_and_reads_back_only_media_permission(
    tmp_path, monkeypatch, allowed,
):
    store = Store(tmp_path / 'media.sqlite3')
    store.migrate()
    store.insert_user('user_a', 'owner', 1)
    store.insert_device('dev_a', 'user_a', 'f' * 52, b'public', 'phone', 1, state='ACTIVE')
    iid = 'a' * 52
    ctx = SimpleNamespace(store=store, out=io.StringIO(), now=lambda: 10)
    reads = []

    def live(_ctx, device_id, actual_iid):
        assert actual_iid == iid and device_id == 'dev_a'
        decision = store.media_read_decision(iid, device_id)
        reads.append(decision.revision)
        return {'decision': decision._asdict(), 'nonce': 'a' * 32, 'generation': 'b' * 32,
                'host_enabled': False, 'api_available': True, 'effective': decision.allowed is True,
                'expires_ms': 2 ** 52}

    monkeypatch.setattr(cli, '_load_identity', lambda _ctx: SimpleNamespace(iid=iid))
    monkeypatch.setattr(cli, '_media_operator_context', live)
    monkeypatch.setattr(cli, '_host_request_confirmation', lambda _ctx, token: token.startswith(
        ('ALLOW' if allowed else 'DENY') + ' MEDIA_READ dev_a'))
    try:
        action = 'grant-media-read' if allowed else 'deny-media-read'
        args = argparse.Namespace(devices_command=action, device_id='dev_a')
        assert cli._cmd_devices_media(ctx, args) == 0
        assert reads == [0, 0, 1]
        assert store.media_read_decision(iid, 'dev_a').allowed is allowed
        assert store.owner_controls_decision('dev_a') is None
    finally:
        store.close()
