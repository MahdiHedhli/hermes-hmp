"""Owned native-service lifecycle with synthetic bridge/header scopes only."""
import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hmp_plugin.auth import AuthContext
from hmp_plugin.contract import AuthzState
from hmp_plugin.presentation_native import PresentationNativeService


def fixture():
    bridge = SimpleNamespace(authz_state=lambda user, profile: AuthzState.AUTHORIZED,
                             _profile_home=lambda profile: Path('/synthetic/hermes'))
    identity = SimpleNamespace(still_current=lambda: True)
    ctx = SimpleNamespace(bridge=bridge, store=object(), identity=identity,
                          iid='synthetic-instance', now=lambda: 100)
    current = [True]
    native_owner = object()
    service = PresentationNativeService(ctx, current=lambda: current[0], native_current=lambda: True, native_owner=native_owner)
    record = SimpleNamespace(listener=ctx, store=ctx.store, bridge=bridge, identity=identity,
        fence=SimpleNamespace(current=True, epoch=1), fence_epoch=1,
        lease=SimpleNamespace(iid=ctx.iid, device_id='device', user_id='user', family_id='family', profile='default', epoch=1),
        headers=SimpleNamespace(authorization='synthetic', instance=ctx.iid),
        deadline=asyncio.get_running_loop().time()+2, operation=object(), native_owner=native_owner)
    return service, record, current


@pytest.mark.asyncio
async def test_observation_requires_auth_before_and_after_native_read():
    service, record, _ = fixture()
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        auth.return_value.authenticate.side_effect = [AuthContext('device', 'user', 'family'), AuthContext('other', 'user', 'family')]
        assert await service.observe(record, 'INITIAL') is None
        assert auth.return_value.authenticate.call_count == 2
    assert await service.drain(record) is True


@pytest.mark.asyncio
async def test_valid_scope_returns_native_home_and_same_owner_objects():
    service, record, _ = fixture()
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        auth.return_value.authenticate.return_value = AuthContext('device', 'user', 'family')
        result = await service.observe(record, 'INITIAL')
    assert result.native_home == '/synthetic/hermes'
    assert result.listener is record.listener and result.native_owner is record.native_owner
    assert await service.drain(record) is True


@pytest.mark.asyncio
async def test_cancelled_observer_retains_actual_worker_until_join():
    service, record, current = fixture()
    started, release = threading.Event(), threading.Event()
    def home(profile):
        started.set()
        release.wait(2)
        return Path('/synthetic/hermes')
    record.bridge._profile_home = home
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        auth.return_value.authenticate.return_value = AuthContext('device', 'user', 'family')
        observing = asyncio.create_task(service.observe(record, 'INITIAL'))
        try:
            for _ in range(100):
                if started.is_set(): break
                await asyncio.sleep(.005)
            assert started.is_set()
            observing.cancel()
            with pytest.raises(asyncio.CancelledError): await observing
            assert record.operation in service._reads
            draining = asyncio.create_task(service.drain(record))
            await asyncio.sleep(.02)
            assert not draining.done()
            current[0] = False
            service.retire()
            release.set()
            assert await draining is True
            assert service._reads == {}
        finally:
            release.set()
            await service.drain(record)


@pytest.mark.asyncio
async def test_wrong_listener_refuses_before_authentication_or_native_read():
    service, record, _ = fixture()
    record.listener = object()
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        assert await service.observe(record, 'INITIAL') is None
        auth.assert_not_called()


@pytest.mark.asyncio
async def test_wrong_native_owner_refuses_before_authentication():
    service, record, _ = fixture()
    record.native_owner = object()
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        assert await service.observe(record, 'INITIAL') is None
        auth.assert_not_called()
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_native_revocation_during_home_lookup_refuses_observation():
    service, record, _ = fixture()
    allowed = [True]
    checks = []
    def policy(user, profile):
        checks.append(allowed[0])
        return AuthzState.AUTHORIZED if allowed[0] else AuthzState.PENDING_OPERATOR
    record.bridge.authz_state = policy
    def home(profile):
        allowed[0] = False
        return Path('/synthetic/hermes')
    record.bridge._profile_home = home
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        auth.return_value.authenticate.return_value = AuthContext('device', 'user', 'family')
        assert await service.observe(record, 'INITIAL') is None
    assert checks == [True, False]
    assert await service.drain(record) is True


@pytest.mark.asyncio
async def test_cancelled_owned_task_does_not_release_running_thread():
    service, record, _ = fixture()
    started, release = threading.Event(), threading.Event()
    def home(profile):
        started.set()
        release.wait(2)
        return Path('/synthetic/hermes')
    record.bridge._profile_home = home
    with patch('hmp_plugin.presentation_native.Authenticator') as auth:
        auth.return_value.authenticate.return_value = AuthContext('device', 'user', 'family')
        observing = asyncio.create_task(service.observe(record, 'INITIAL'))
        try:
            for _ in range(100):
                if started.is_set(): break
                await asyncio.sleep(.005)
            assert started.is_set()
            owner = service._reads[record.operation]
            owner.task.cancel()
            with pytest.raises(asyncio.CancelledError): await observing
            assert service._reads[record.operation] is owner
            assert owner.worker.is_alive() and not owner.joined
            draining = asyncio.create_task(service.drain(record))
            await asyncio.sleep(.02)
            assert not draining.done()
            release.set()
            assert await draining is True
            assert owner.joined and not owner.worker.is_alive()
        finally:
            release.set()
            await service.drain(record)


@pytest.mark.asyncio
async def test_ambiguous_thread_start_keeps_undrained_capacity():
    service, record, _ = fixture()
    with patch('hmp_plugin.presentation_native.Authenticator') as auth, patch('hmp_plugin.presentation_native.threading.Thread.start', side_effect=RuntimeError('synthetic start uncertainty')):
        auth.return_value.authenticate.return_value = AuthContext('device', 'user', 'family')
        assert await service.observe(record, 'INITIAL') is None
    assert record.operation in service._reads
    assert await service.drain(record) is False
    assert await service.close_and_join() is False
