"""Closed request codec, not an operator mutation execution or transport test."""
import json
import pytest
from hmp_plugin.media_permissions import MediaReadDecision
from hmp_plugin.media_operator_protocol import (
    MediaReadMutation, MediaOperatorProtocolError, decode_mutation,
)


def request(*, explicit=False, maximum=False):
    n = 2 ** 63 - 1 if maximum else 0
    decision = MediaReadDecision('a' * 52, 'device', 'user', True if explicit else None,
                                max(n, 1) if explicit else n, n, n,
                                None, None if explicit else n)
    return MediaReadMutation('a' * 52, 'a' * 32, 'b' * 32, 'c' * 32, 'device', decision, True)


@pytest.mark.parametrize('explicit', (False, True))
@pytest.mark.parametrize('maximum', (False, True))
def test_roundtrip_preserves_exact_store_counter_domain(explicit, maximum):
    value = request(explicit=explicit, maximum=maximum)
    assert decode_mutation(value.encode()) == value
    assert repr(value) == '<MediaReadMutation redacted>'
    body = json.loads(value.encode())
    assert type(body['expected']['revision']) is str


@pytest.mark.parametrize('bad', (True, 1, 1.0, '', '00', '+1', '-1', '1e3',
                               str(2 ** 63), '9' * 20, 'private/path'))
def test_noncanonical_counters_refuse_without_echo(bad):
    body = json.loads(request().encode()); body['expected']['revision'] = bad
    with pytest.raises(MediaOperatorProtocolError) as caught:
        decode_mutation(json.dumps(body).encode())
    assert str(caught.value) == 'media operator protocol unavailable'


@pytest.mark.parametrize('field,bad', [
    ('protocol', True), ('protocol', 2), ('operation', 'grant_controls'),
    ('iid', 'b' * 52), ('nonce', 'private/path'), ('generation', 'a' * 31 + '\n'),
    ('attempt', 'A' * 32), ('device_id', '../bad\n'), ('allowed', 1),
    ('allowed', 'true'), ('expected', []),
])
def test_closed_root_and_exact_types(field, bad):
    body = json.loads(request().encode()); body[field] = bad
    with pytest.raises(MediaOperatorProtocolError): decode_mutation(json.dumps(body).encode())


@pytest.mark.parametrize('raw', [b'[]', b'{"protocol":1,"protocol":1}', b'NaN',
                                b'\xff', b' ' * 2049, b'{"x":[[[[[]]]]]}'])
def test_malformed_bounded_payload(raw):
    with pytest.raises(MediaOperatorProtocolError): decode_mutation(raw)


@pytest.mark.parametrize('nested', (False, True))
def test_unknown_fields_rejected(nested):
    body = json.loads(request().encode())
    (body['expected'] if nested else body)['private'] = 'not echoed'
    with pytest.raises(MediaOperatorProtocolError): decode_mutation(json.dumps(body).encode())


def test_foreign_expected_and_mismatched_device_cannot_encode():
    value = request()
    wrong = value.expected._replace(device_id='other')
    with pytest.raises(MediaOperatorProtocolError):
        MediaReadMutation(value.iid, value.nonce, value.generation, value.attempt,
                          value.device_id, wrong, True).encode()
    class Foreign:
        def validate(self): raise AssertionError('foreign callback')
    with pytest.raises(MediaOperatorProtocolError):
        MediaReadMutation(value.iid, value.nonce, value.generation, value.attempt,
                          value.device_id, Foreign(), True).encode()
