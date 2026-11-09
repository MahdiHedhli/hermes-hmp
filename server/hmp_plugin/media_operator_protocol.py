"""Closed operator mutation request DATA only; no socket, authority or SQL execution.

New protocol counters are canonical decimal strings, preserving the Store's full
signed-64-bit domain without JSON rounding. This does not modify older read DTOs.
"""
from __future__ import annotations

from dataclasses import dataclass
from . import wire
from .media_permissions import MediaReadDecision, validate_media_scope

MAX_REQUEST_BYTES = 2048
_COUNTERS = ('revision', 'instance_epoch', 'revocation_epoch', 'fallback_revision')
_EXPECTED = frozenset(MediaReadDecision._fields) - {'iid', 'device_id'}
_FIELDS = frozenset({'protocol', 'operation', 'iid', 'nonce', 'generation', 'attempt',
                     'device_id', 'expected', 'allowed'})


class MediaOperatorProtocolError(ValueError):
    def __init__(self) -> None:
        super().__init__('media operator protocol unavailable')


def _hex(value: object) -> bool:
    return (type(value) is str and len(value) == 32
            and all(c in '0123456789abcdef' for c in value))


def _counter(value: object, *, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if (type(value) is not str or not 1 <= len(value) <= 19
            or any(c not in '0123456789' for c in value)
            or (len(value) > 1 and value[0] == '0')):
        raise MediaOperatorProtocolError()
    result = int(value)
    if result > 2 ** 63 - 1:
        raise MediaOperatorProtocolError()
    return result


@dataclass(frozen=True, slots=True, repr=False)
class MediaReadMutation:
    iid: str
    nonce: str
    generation: str
    attempt: str
    device_id: str
    expected: MediaReadDecision
    allowed: bool

    def __repr__(self) -> str:
        return '<MediaReadMutation redacted>'

    def validate(self) -> None:
        try:
            validate_media_scope(self.iid, self.device_id)
            if (not all(_hex(v) for v in (self.nonce, self.generation, self.attempt))
                    or type(self.allowed) is not bool
                    or type(self.expected) is not MediaReadDecision):
                raise MediaOperatorProtocolError()
            self.expected.validate()
            if self.expected.iid != self.iid or self.expected.device_id != self.device_id:
                raise MediaOperatorProtocolError()
        except (ValueError, TypeError):
            raise MediaOperatorProtocolError() from None

    def encode(self) -> bytes:
        self.validate()
        expected = {k: v for k, v in self.expected._asdict().items() if k in _EXPECTED}
        for key in _COUNTERS:
            value = expected[key]
            expected[key] = None if value is None else str(value)
        raw = wire.dump_json({
            'protocol': 1, 'operation': 'host_media_read_decide',
            'iid': self.iid, 'nonce': self.nonce, 'generation': self.generation,
            'attempt': self.attempt, 'device_id': self.device_id,
            'expected': expected, 'allowed': self.allowed,
        })
        if len(raw) > MAX_REQUEST_BYTES:
            raise MediaOperatorProtocolError()
        return raw


def decode_mutation(raw: bytes) -> MediaReadMutation:
    try:
        if type(raw) is not bytes:
            raise MediaOperatorProtocolError()
        body = wire.parse_body(raw, max_bytes=MAX_REQUEST_BYTES, max_depth=3)
        if (frozenset(body) != _FIELDS or type(body['protocol']) is not int
                or body['protocol'] != 1 or type(body['operation']) is not str
                or body['operation'] != 'host_media_read_decide'):
            raise MediaOperatorProtocolError()
        expected = body['expected']
        if type(expected) is not dict or frozenset(expected) != _EXPECTED:
            raise MediaOperatorProtocolError()
        fields = dict(expected)
        for key in _COUNTERS:
            fields[key] = _counter(fields[key], nullable=key == 'fallback_revision')
        decision = MediaReadDecision(iid=body['iid'], device_id=body['device_id'], **fields)
        request = MediaReadMutation(
            body['iid'], body['nonce'], body['generation'], body['attempt'],
            body['device_id'], decision, body['allowed'],
        )
        request.validate()
        return request
    except (ValueError, TypeError, KeyError):
        raise MediaOperatorProtocolError() from None
