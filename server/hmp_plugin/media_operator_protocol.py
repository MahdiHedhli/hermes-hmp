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


_REPLY_FIELDS = frozenset({'protocol', 'operation', 'iid', 'nonce', 'generation',
                          'attempt', 'device_id', 'status', 'decision'})


@dataclass(frozen=True, slots=True, repr=False)
class MediaOperatorReply:
    status: str
    decision: MediaReadDecision | None
    def __repr__(self) -> str:
        return '<MediaOperatorReply redacted>'


def _validated_reply(request, status, decision) -> MediaOperatorReply:
    if type(request) is not MediaReadMutation:
        raise MediaOperatorProtocolError()
    request.validate()
    if type(status) is not str or status not in {'committed', 'conflict', 'refused', 'unknown'}:
        raise MediaOperatorProtocolError()
    if status != 'committed':
        if decision is not None:
            raise MediaOperatorProtocolError()
    else:
        if type(decision) is not MediaReadDecision:
            raise MediaOperatorProtocolError()
        decision.validate()
        expected = request.expected
        if (decision.iid != request.iid or decision.device_id != request.device_id
                or decision.user_id != expected.user_id or decision.allowed is not request.allowed
                or decision.revision != expected.revision + 1
                or decision.instance_epoch != expected.instance_epoch
                or decision.revocation_epoch != expected.revocation_epoch):
            raise MediaOperatorProtocolError()
    return MediaOperatorReply(status, decision)


def encode_reply(request: MediaReadMutation, status: str,
                 decision: MediaReadDecision | None = None) -> bytes:
    try:
        reply = _validated_reply(request, status, decision)
        fields = None
        if reply.decision is not None:
            fields = {k: v for k, v in reply.decision._asdict().items() if k in _EXPECTED}
            for key in _COUNTERS:
                value = fields[key]
                fields[key] = None if value is None else str(value)
        raw = wire.dump_json({
            'protocol': 1, 'operation': 'host_media_read_decide_result',
            'iid': request.iid, 'nonce': request.nonce, 'generation': request.generation,
            'attempt': request.attempt, 'device_id': request.device_id,
            'status': reply.status, 'decision': fields,
        })
        if len(raw) > MAX_REQUEST_BYTES:
            raise MediaOperatorProtocolError()
        return raw
    except (ValueError, TypeError):
        raise MediaOperatorProtocolError() from None


def decode_reply(raw: bytes, *, request: MediaReadMutation) -> MediaOperatorReply:
    try:
        if type(request) is not MediaReadMutation or type(raw) is not bytes:
            raise MediaOperatorProtocolError()
        request.validate()
        body = wire.parse_body(raw, max_bytes=MAX_REQUEST_BYTES, max_depth=3)
        if (frozenset(body) != _REPLY_FIELDS or type(body['protocol']) is not int
                or body['protocol'] != 1 or body['operation'] != 'host_media_read_decide_result'):
            raise MediaOperatorProtocolError()
        for key in ('iid', 'nonce', 'generation', 'attempt', 'device_id'):
            if type(body[key]) is not str or body[key] != getattr(request, key):
                raise MediaOperatorProtocolError()
        decision = body['decision']
        if decision is not None:
            if type(decision) is not dict or frozenset(decision) != _EXPECTED:
                raise MediaOperatorProtocolError()
            fields = dict(decision)
            for key in _COUNTERS:
                fields[key] = _counter(fields[key], nullable=key == 'fallback_revision')
            decision = MediaReadDecision(iid=request.iid, device_id=request.device_id, **fields)
        return _validated_reply(request, body['status'], decision)
    except (ValueError, TypeError, KeyError):
        raise MediaOperatorProtocolError() from None
