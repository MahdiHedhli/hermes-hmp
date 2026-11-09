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
    run(env, scenario)
