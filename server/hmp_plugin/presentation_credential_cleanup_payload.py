"""Original captured RESULT-body hash seed; separate DATA copy, no output revival."""
from __future__ import annotations

from typing import NamedTuple

from .presentation_credential_payload_digest import PayloadDigest
from .presentation_credential_stream import _HASH_TYPE, CommittedFrameDigest
from .presentation_jobs import FrameError

_HEX = _HASH_TYPE.hexdigest


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_PAYLOAD_DIGEST_REFUSED")


class _Seed(NamedTuple):
    native: object
    scope: object
    body: object
    source: object
    count: int
    sha256: str
    data: PayloadDigest

    def __repr__(self):
        return "<PayloadSeed original-result2-body-hash redacted>"


def _metadata(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead
    s = NativeCleanupRead._origin(native)
    seed = native._payload_seed_origin
    _require(
        type(seed) is _Seed
        and native._payload_seed is seed
        and type(native._payload_seed_cell) is tuple
        and len(native._payload_seed_cell) == 2
        and native._payload_seed_cell[0] is native
        and native._payload_seed_cell[1] is seed
        and seed.native is native
        and seed.scope is s
        and seed.body is s.idle_scope[0].reservation.capture.body
        and type(seed.source) is _HASH_TYPE
        and seed.source is seed.body.allocation[2]
        and seed.body.owner._hash_origin is seed.source
        and seed.body.owner._initialization_origin is seed.body.allocation
        and type(seed.count) is int
        and seed.count == seed.body.committed
        and type(seed.sha256) is str
        and seed.sha256 is seed.body.hash_value
        and type(seed.data) is PayloadDigest
        and type(seed.data._seed) is tuple
        and len(seed.data._seed) == 4
        and seed.data._seed[0] is seed.data
        and seed.data._seed[1] is seed.source
        and type(seed.data._seed[2]) is int
        and seed.data._seed[2] == seed.count
        and seed.data._seed[3] is seed.sha256
    )
    PayloadDigest._metadata(seed.data)
    return seed


def initialize(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead
    s = NativeCleanupRead._origin(native)
    body = s.idle_scope[0].reservation.capture.body
    _require(body is not None and native._payload_seed_origin is None
             and native._payload_seed is None and native._payload_seed_cell is None
             and type(body.allocation[2]) is _HASH_TYPE and type(body.committed) is int
             and type(body.hash_value) is str)
    data = PayloadDigest.__new__(PayloadDigest)
    seed = _Seed(native, s, body, body.allocation[2], body.committed, body.hash_value, data)
    native._payload_seed = native._payload_seed_origin = seed
    native._payload_seed_cell = (native, seed)
    NativeCleanupRead._current_work(native)
    PayloadDigest.__init__(data, source=seed.source, seed_count=seed.count, seed_sha256=seed.sha256)
    NativeCleanupRead._current_work(native)
    _require(current_seed(native) is seed and data._received == seed.count)
    NativeCleanupRead._current_work(native)


def current_seed(native):
    """Fixed source digest fence; native caller must reseal role/budget/FD afterward."""
    seed = _metadata(native)
    value = _HEX(seed.source)
    _require(_metadata(native) is seed and type(value) is str and value == seed.sha256)
    from .presentation_cancel_budget import CancellationBudget
    from .presentation_credential_cleanup_notice import SignedReadNotice
    SignedReadNotice._role_seal(seed.scope.notice)
    _, last, end, failed = CancellationBudget.inspect(seed.scope.idle_scope[3])
    _require(type(last) is int and type(end) is int and last < end
             and end <= seed.scope.idle_scope[4] and failed is False
             and _metadata(native) is seed)
    return seed


def feed(native, chunk, count):
    failed = False
    try:
        seed = current_seed(native)
        stream = seed.body.allocation[1]
        _require(type(stream) is CommittedFrameDigest and type(count) is int
                 and type(chunk) is bytes and type(stream._received) is int
                 and stream._received == count
                 and seed.data._received + len(chunk) == count)
        PayloadDigest.feed(seed.data, chunk)
        _require(_metadata(native) is seed and seed.data._received == count)
    except BaseException:
        failed = True
    finally:
        chunk = None
    if failed:
        raise FrameError("BI1_NATIVE_PAYLOAD_FEED_UNKNOWN") from None


def finish(native, count):
    seed = current_seed(native)
    stream = seed.body.allocation[1]
    _require(type(count) is int and type(stream) is CommittedFrameDigest
             and stream._finished is True and type(stream._body_length) is int
             and count == stream._received == stream._body_length)
    fact = PayloadDigest.finish(seed.data, count)
    _require(_metadata(native) is seed and PayloadDigest.current_fact(seed.data, count) is fact)
    return fact


def current_fact(native, count):
    seed = _metadata(native)
    return PayloadDigest.current_fact(seed.data, count)
