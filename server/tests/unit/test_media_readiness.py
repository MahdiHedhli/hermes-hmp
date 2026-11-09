"""Content-free diagnostics distinguish missing rights from host/API gates."""
import itertools
import pytest
from hmp_plugin.media_readiness import host_setting, project, MediaReadinessUnavailable


@pytest.mark.parametrize('rights,flag,api', tuple(itertools.product(
    ('granted', 'missing', 'unknown'), ('enabled', 'disabled', 'unknown'),
    ('available', 'unavailable', 'unknown'))))
def test_axes_remain_independent(rights, flag, api):
    result = project(entitlement=rights, host=flag, api=api)
    assert result['entitlement'] == rights
    assert result['host_setting'] == flag
    assert result['runtime_api'] == api
    ready = (rights, flag, api) == ('granted', 'enabled', 'available')
    assert result['operational'] is ready
    assert result['action'] == ('none' if ready else 'contact_host_operator')
    assert result['image_availability'] == 'not_probed'
    assert ('media_read_missing' in result['reasons']) is (rights == 'missing')
    assert ('host_flag_disabled' in result['reasons']) is (flag == 'disabled')
    assert ('media_api_unavailable' in result['reasons']) is (api == 'unavailable')


@pytest.mark.parametrize('config,expected', [
    ({}, 'disabled'), ({'local_media': {}}, 'disabled'),
    ({'local_media': {'enabled': True}}, 'enabled'),
    ({'local_media': {'enabled': False}}, 'disabled'),
    ({'local_media': {'enabled': 1}}, 'unknown'),
    ({'local_media': {'enabled': 'true'}}, 'unknown'),
    ({'local_media': None}, 'unknown'), (None, 'unknown'),
])
def test_host_flag_exact_boolean(config, expected):
    assert host_setting(config) == expected


@pytest.mark.parametrize('field', ('entitlement', 'host', 'api'))
def test_untrusted_values_never_escape(field):
    kwargs = dict(entitlement='granted', host='enabled', api='available')
    kwargs[field] = 'private path /secret must not escape'
    with pytest.raises(MediaReadinessUnavailable) as exc:
        project(**kwargs)
    assert str(exc.value) == 'media readiness unavailable'


def test_route_is_authenticated_read_only_and_does_not_probe_images(tmp_path):
    from .hmp_kit import Env, pair, get, run
    from hmp_plugin.contract import AuthzState
    env = Env(tmp_path)
    env.bridge.authz_state = lambda user, profile: AuthzState.AUTHORIZED
    env.ctx.readiness_settings = lambda: {'local_media': {'enabled': False}}

    async def scenario(client):
        device = await pair(env, client)
        path = '/bots/default/media-readiness'
        before = env.store.media_read_decision(env.iid, device.device_id)
        status, _ = await get(client, path, headers={'HMP-Instance': env.iid})
        assert status == 401
        status, data = await get(client, path, headers=env.headers(device))
        assert status == 200, data
        assert data['media']['host_setting'] == 'disabled'
        assert data['media']['image_availability'] == 'not_probed'
        assert env.store.media_read_decision(env.iid, device.device_id) == before
        status, _ = await get(client, path + '?extra=1', headers=env.headers(device))
        assert status == 400
        env.bridge.authz_state = lambda user, profile: AuthzState.NOT_SERVED
        status, data = await get(client, path, headers=env.headers(device))
        assert status == 404 and 'media' not in data
    run(env, scenario)


@pytest.mark.parametrize('change', ('media_deny', 'generation', 'bot_revoke', 'host_flag'))
def test_route_discards_snapshot_changed_during_config_callback(tmp_path, change):
    from .hmp_kit import Env, pair, get, run
    from hmp_plugin.contract import AuthzState
    env = Env(tmp_path)
    env.bridge.authz_state = lambda user, profile: AuthzState.AUTHORIZED

    async def scenario(client):
        device = await pair(env, client)
        initial = env.store.media_read_decision(env.iid, device.device_id)
        assert env.store.set_media_read(initial, allowed=True, now=env.clock.now) is not None
        calls = []

        def settings():
            calls.append(1)
            if len(calls) == 1:
                if change == 'media_deny':
                    previous = env.store.media_read_decision(env.iid, device.device_id)
                    assert env.store.set_media_read(previous, allowed=False, now=env.clock.now)
                elif change == 'generation':
                    env.ctx.readiness_generation = 'a' * 32
                elif change == 'bot_revoke':
                    env.bridge.authz_state = lambda user, profile: AuthzState.NOT_SERVED
            return {'local_media': {'enabled': not (change == 'host_flag' and len(calls) > 1)}}

        env.ctx.readiness_settings = settings
        status, data = await get(client, '/bots/default/media-readiness',
                                 headers=env.headers(device))
        assert status == (404 if change == 'bot_revoke' else 503), data
        assert 'media' not in data
        assert env.store.owner_controls_decision(device.device_id) is None
    run(env, scenario)


@pytest.mark.parametrize('change', ('deny_regrant', 'generation', 'bot_revoke'))
def test_route_final_delivery_fence_discards_post_worker_changes(tmp_path, monkeypatch, change):
    import threading
    from .hmp_kit import Env, pair, get, run
    from hmp_plugin import server
    from hmp_plugin.contract import AuthzState
    env = Env(tmp_path)
    env.bridge.authz_state = lambda user, profile: AuthzState.AUTHORIZED
    env.ctx.readiness_settings = lambda: {'local_media': {'enabled': False}}
    original = server._collect_media_readiness
    changed = []

    async def scenario(client):
        device = await pair(env, client)
        initial = env.store.media_read_decision(env.iid, device.device_id)
        assert env.store.set_media_read(initial, allowed=True, now=env.clock.now)

        def collect(ctx, **scope):
            result = original(ctx, **scope)
            if threading.current_thread() is not threading.main_thread() and not changed:
                changed.append(True)
                if change == 'deny_regrant':
                    for allowed in (False, True):
                        previous = env.store.media_read_decision(env.iid, device.device_id)
                        assert env.store.set_media_read(previous, allowed=allowed, now=env.clock.now)
                elif change == 'generation':
                    env.ctx.readiness_generation = 'a' * 32
                else:
                    env.bridge.authz_state = lambda user, profile: AuthzState.NOT_SERVED
            return result

        monkeypatch.setattr(server, '_collect_media_readiness', collect)
        status, data = await get(client, '/bots/default/media-readiness',
                                 headers=env.headers(device))
        assert changed and status == (404 if change == 'bot_revoke' else 503), data
        assert 'media' not in data and '_authority' not in str(data)
    run(env, scenario)


def test_media_capability_is_authenticated_protocol_only(tmp_path):
    from .hmp_kit import Env, pair, get, run
    env = Env(tmp_path)

    async def scenario(client):
        device = await pair(env, client)
        path = '/media-readiness/capabilities'
        status, _ = await get(client, path, headers={'HMP-Instance': env.iid})
        assert status == 401
        status, body = await get(client, path, headers=env.headers(device))
        assert status == 200
        assert body == {'protocol': 1, 'media_readiness': True, 'remote_permission_write': False}
        # Query extensions are not silently accepted as a different protocol.
        status, _ = await get(client, path + '?protocol=2', headers=env.headers(device))
        assert status == 400
    run(env, scenario)
