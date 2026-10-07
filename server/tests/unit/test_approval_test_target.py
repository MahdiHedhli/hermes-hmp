"""Exercise the actual proposed AT1 bridge accessor through synthetic native-shaped ports.

No fake core modules, native import, database, provider or live home is used.
Poison rows prove only HMP field access, not the native SQL/helper projection.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from hmp_plugin.bridge import BridgeError, HermesReadBridge
from hmp_plugin.contract import ApprovalTestTarget


class MetadataRow(Mapping):
    def __init__(self, **metadata):
        self.metadata = metadata
        self.reads = []

    def __getitem__(self, key):
        assert key in ('id', 'parent_session_id'), 'HMP touched forbidden payload'
        self.reads.append(key)
        return self.metadata[key]

    def __iter__(self):
        raise AssertionError('row copied/iterated')

    def __len__(self):
        raise AssertionError('row inspected beyond metadata')


class Database:
    def __init__(self):
        self.title = MetadataRow(id='titled')
        self.tip = 'tip'
        self.lineage = ['root', 'titled', 'tip']
        self.rows = {
            'root': MetadataRow(id='root', parent_session_id=None),
            'titled': MetadataRow(id='titled', parent_session_id='root'),
            'tip': MetadataRow(id='tip', parent_session_id='titled'),
        }
        self.title_calls = self.resume_calls = self.messages = 0
        self.on_session = None

    def get_session_by_title(self, title):
        assert title == 'Bot Chat'
        self.title_calls += 1
        return self.title

    def resolve_resume_session_id(self, session_id):
        assert session_id == 'titled'
        self.resume_calls += 1
        return self.tip

    def get_compression_lineage(self, session_id):
        assert session_id == 'titled'
        return self.lineage

    def get_session(self, session_id):
        if self.on_session:
            self.on_session()
        return self.rows.get(session_id)

    def get_messages(self, *_args, **_kwargs):
        self.messages += 1
        raise AssertionError('AT1 cannot read messages/head')


def bridge_rig():
    db = Database()
    homes = [Path('/synthetic/profile')]
    released = []
    bridge = object.__new__(HermesReadBridge)
    bridge._profile_home = lambda _profile: homes[0]
    bridge._read = lambda action: action()

    @contextlib.contextmanager
    def database(_profile):
        try:
            yield db
        finally:
            released.append(True)

    bridge._db = database
    bridge.resolve_bot_chat = lambda *_args: pytest.fail('normal resolver called')
    bridge.head = lambda *_args: pytest.fail('head called')
    bridge.latest = lambda *_args: pytest.fail('latest called')
    return bridge, db, homes, released


def test_actual_accessor_returns_only_three_frozen_metadata_fields():
    bridge, db, _, released = bridge_rig()
    value = bridge.approval_test_target('bot')
    assert type(value) is ApprovalTestTarget
    assert value == ApprovalTestTarget(Path('/synthetic/profile'), 'root', 'tip')
    assert value.__slots__ == ('profile_home', 'root_session_id', 'live_tip_session_id')
    with pytest.raises(FrozenInstanceError):
        value.root_session_id = 'changed'
    assert db.title_calls == db.resume_calls == 1 and db.messages == 0 and released == [True]
    assert set(db.title.reads) == {'id'}
    assert all(set(row.reads) <= {'id', 'parent_session_id'} for row in db.rows.values())


def test_absent_title_returns_none_without_resume_or_body_read():
    bridge, db, _, released = bridge_rig()
    db.title = None
    assert bridge.approval_test_target('bot') is None
    assert db.resume_calls == db.messages == 0 and released == [True]


@pytest.mark.parametrize('bad', [None, '', False, 7, 'x'*257, 'bad\n'])
def test_malformed_resume_refuses_without_title_fallback_or_body_read(bad):
    bridge, db, _, released = bridge_rig()
    db.tip = bad
    with pytest.raises(BridgeError):
        bridge.approval_test_target('bot')
    assert db.messages == 0 and db.resume_calls == 1 and released == [True]


@pytest.mark.parametrize('bad', [None, [], ['tip']*2, ['root', False], ['x']*101])
def test_malformed_or_overbound_lineage_refuses(bad):
    bridge, db, _, released = bridge_rig()
    db.lineage = bad
    with pytest.raises(BridgeError):
        bridge.approval_test_target('bot')
    assert db.messages == 0 and released == [True]


def test_parent_cycle_and_missing_identity_fail_closed():
    for row in [
        MetadataRow(id='tip', parent_session_id='tip'), MetadataRow(parent_session_id=None),
    ]:
        bridge, db, _, released = bridge_rig()
        db.rows['tip'] = row
        with pytest.raises(BridgeError):
            bridge.approval_test_target('bot')
        assert db.messages == 0 and released == [True]


def test_distinct_parent_roots_refuse():
    bridge, db, _, released = bridge_rig()
    db.rows['tip'] = MetadataRow(id='tip', parent_session_id='other')
    db.rows['other'] = MetadataRow(id='other', parent_session_id=None)
    with pytest.raises(BridgeError):
        bridge.approval_test_target('bot')
    assert db.messages == 0 and released == [True]


def test_routed_home_change_during_lookup_refuses():
    bridge, db, homes, released = bridge_rig()
    db.on_session = lambda: homes.__setitem__(0, Path('/changed'))
    with pytest.raises(BridgeError):
        bridge.approval_test_target('bot')
    assert db.messages == 0 and released == [True]


def test_native_release_failure_never_returns_target():
    bridge, db, _, _ = bridge_rig()

    @contextlib.contextmanager
    def database(_profile):
        yield db
        raise BridgeError('release failed')

    bridge._db = database
    with pytest.raises(BridgeError):
        bridge.approval_test_target('bot')
    assert db.messages == 0


def test_malformed_native_resume_stops_actual_service_before_producer():
    import asyncio
    import os
    from types import SimpleNamespace

    from hmp_plugin.approval_test_host_codec import HostBeginRequest, HostGeneration
    from hmp_plugin.approval_test_service import ApprovalTestService
    from hmp_plugin.contract import AuthzState

    async def run():
        bridge, db, _, released = bridge_rig()
        db.tip = None
        bridge.served_profiles = lambda: ['bot']
        bridge.authz_state = lambda *_args: AuthzState.AUTHORIZED
        row = {'device_id': 'phone', 'user_id': 'owner', 'device_fp': 'fp', 'state': 'ACTIVE'}
        ctx = SimpleNamespace(
            iid='a'*52, bridge=bridge, store=SimpleNamespace(get_device=lambda _id: row),
            identity=SimpleNamespace(still_current=lambda: True),
            is_approvals_available=lambda: True, direct_send_effective=lambda: True,
            is_approval_owner_device=lambda _device: True,
        )
        gen = HostGeneration(ctx.iid, os.getpid(), 'b'*32)
        calls = []

        async def gate(*_args, **_kwargs):
            calls.append('gate')

        def factory(**_kwargs):
            calls.append('producer')
            raise AssertionError('malformed target admitted a producer')

        service = ApprovalTestService(ctx, gen, generation_current=lambda: True,
                                      approvals_gate=gate, producer_factory=factory,
                                      native_current=lambda: True)
        lease = service.responses(HostBeginRequest(gen, 'phone', 'bot', 'tip'))
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        await service.shutdown()
        assert calls == [] and db.messages == 0 and released == [True]
    asyncio.run(run())
