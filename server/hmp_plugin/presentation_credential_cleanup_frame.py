"""Original-reader frame stage. No terminal acceptance, ACK, release or emission.

All transport runs on the retained NativeCleanupRead socket/task. Frame state and
steps are bounded DATA allocations, never a replacement reader or selector.
"""
from __future__ import annotations

import hashlib
import socket
from typing import NamedTuple

from .presentation_broker_codec import HEADER_LIMIT, BrokerBinding
from .presentation_credential_cleanup_notice import SignedReadNotice
from .presentation_credential_frame_discard import CommittedFrameDiscard, DiscardedFrame
from .presentation_credential_stream import (
    _HASH_TYPE,
    CHUNK_LIMIT,
    CommittedFrameDigest,
    ConsistentFrameDigest,
)
from .presentation_jobs import FrameError, RemotePhase

_HASH_HEX = _HASH_TYPE.hexdigest
_HASH_COPY = _HASH_TYPE.copy
_HASH_UPDATE = _HASH_TYPE.update
_SHA256 = hashlib.sha256


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_FRAME_REFUSED")


class _FrameScope(NamedTuple):
    native: object
    read_scope: object
    auth: object
    receipt: object
    binding: BrokerBinding
    phase: str
    sequence: int
    outer: bytes
    parser: CommittedFrameDiscard

    def __repr__(self):
        return "<FrameScope original-auth-reader redacted>"


class _FrameSeal(NamedTuple):
    parser: object
    buffer: object
    value: bytes
    target: int
    header: object
    stream: object
    hasher: object
    received: int
    digest: object
    terminal: object
    terminal_value: bytes
    needed: int

    def __repr__(self):
        return "<FrameSeal bounded-discard-progress redacted>"


class _Ledger(NamedTuple):
    ordinal: int
    received: int
    committed: int
    seal: _FrameSeal

    def __repr__(self):
        return "<FrameLedger cumulative-post-cause-counts>"


class _StepScope(NamedTuple):
    frame: object
    before: _Ledger
    ordinal: int

    def __repr__(self):
        return "<FrameStepScope original-reader>"


class _FrameReadFact(NamedTuple):
    scope: _FrameScope
    ordinal: int
    count: int
    total_received: int
    total_committed: int
    after: _FrameSeal

    def __repr__(self):
        return "<FrameReadFact no-frame-acceptance-or-release>"


class _FrameDone(NamedTuple):
    scope: _FrameScope
    data: DiscardedFrame
    count: int
    total_received: int

    def __repr__(self):
        return "<FrameDone consistency-only no-terminal-acceptance-or-release>"


class _Frame:
    def __repr__(self):
        return "<OriginalFrameStage payload-redacted>"


class _Step:
    def __repr__(self):
        return "<OriginalFrameReadStep payload-redacted>"


def _scope(native, read_scope):
    from .presentation_credential_cleanup_read import _AuthAttempt, _AuthReceipt

    frame = native._frame_origin
    cell = native._frame_allocation_origin
    _require(type(frame) is _Frame and native._frame is frame
             and type(cell) is tuple and len(cell) == 2 and cell[0] is native and cell[1] is frame
             and type(frame.scope) is _FrameScope and frame.scope is frame.scope_origin
             and type(frame.scope_cell) is tuple and len(frame.scope_cell) == 2
             and frame.scope_cell[0] is frame and frame.scope_cell[1] is frame.scope)
    s = frame.scope
    _require(s.native is native and s.read_scope is read_scope
             and type(s.auth) is _AuthAttempt and s.auth is native._auth_origin
             and s.auth.complete is True and type(s.receipt) is _AuthReceipt
             and s.receipt is s.auth.fact and type(s.auth.fact_cell) is tuple
             and len(s.auth.fact_cell) == 2 and s.auth.fact_cell[1] is s.receipt
             and type(s.phase) is str and s.phase in ("RESULT", "TERMINAL")
             and type(s.sequence) is int and s.sequence == 1
             and type(s.receipt.values) is tuple and len(s.receipt.values) == 4
             and s.receipt.values[3] is s.phase
             and type(s.binding) is BrokerBinding
             and type(s.outer) is bytes and len(s.outer) <= 8 + HEADER_LIMIT
             and type(s.parser) is CommittedFrameDiscard
             and "feed" not in vars(s.parser) and "finish" not in vars(s.parser)
             and "needed" not in vars(s.parser)
             and frame.parser is s.parser and frame.parser_origin is s.parser
             and type(frame.parser_cell) is tuple and len(frame.parser_cell) == 2
             and frame.parser_cell[0] is frame and frame.parser_cell[1] is s.parser
             and all(type(v) is bool for v in (
                 frame.initialized, frame.failed, frame.finish_attempted, frame.finish_returned,
                 frame.complete, frame.outer_attempted)) and frame.failed is False)
    capture = read_scope.idle_scope[0].reservation.capture
    # Pre-poison history selects discard eligibility, never revived live work.
    _require(capture.phase is RemotePhase.GO_SENT and capture.body is None
             and s.binding is capture.scope.write_scope.intent.binding
             and type(capture.scope.expected) is tuple
             and all(type(r) is tuple and len(r) == 2 and type(r[0]) is str
                     and type(r[1]) is (int if r[0] in ("sequence", "work_end_ns") else str)
                     for r in capture.scope.expected)
             and dict(capture.scope.expected)["sequence"] == s.sequence
             and read_scope.cursor._outer is s.outer and read_scope.cursor._outer_origin is s.outer)
    original, raw = capture.envelope.values, s.receipt.scope.before.value
    _require(type(original) is bytes and type(raw) is bytes
             and s.outer == (original[len(raw):] if len(original) > len(raw) else b"")
             and (len(original) <= len(raw) or original[:len(raw)] == raw))
    return frame


def _snapshot(frame):
    p = frame.scope.parser
    _require(type(p) is CommittedFrameDiscard)
    needed = CommittedFrameDiscard.needed.fget(p)
    _require(p._claim_origin is frame.scope.receipt.checked
             and p._binding_origin is frame.scope.binding
             and p._expected == (frame.scope.phase, frame.scope.sequence))
    stream = p._stream_origin
    hasher = digest = None
    received = 0
    if stream is not None:
        _require(type(stream) is CommittedFrameDigest and type(stream._hasher_origin) is _HASH_TYPE)
        hasher, received = stream._hasher_origin, stream._received
        digest = _HASH_HEX(hasher)
    return _FrameSeal(p, p._buffer_origin, bytes(p._buffer_origin), p._target_origin,
        p._header_origin, stream, hasher, received, digest, p._terminal_origin,
        bytes(p._terminal_origin), needed)


def _same(actual, expected):
    _require(type(actual) is _FrameSeal and type(expected) is _FrameSeal
             and actual.parser is expected.parser and actual.buffer is expected.buffer
             and actual.header is expected.header and actual.stream is expected.stream
             and actual.hasher is expected.hasher and actual.terminal is expected.terminal
             and type(actual.value) is bytes and type(expected.value) is bytes
             and actual.value == expected.value
             and type(actual.terminal_value) is bytes and type(expected.terminal_value) is bytes
             and actual.terminal_value == expected.terminal_value
             and all(type(v) is int for v in (
                 actual.target, expected.target, actual.received, expected.received,
                 actual.needed, expected.needed))
             and actual.target == expected.target and actual.received == expected.received
             and actual.needed == expected.needed
             and type(actual.digest) is type(expected.digest) and actual.digest == expected.digest)


def _ledger(frame):
    from .presentation_credential_cleanup_read import _WIRE_LIMIT

    ledger = frame.ledger_origin
    _require(type(ledger) is _Ledger and frame.ledger is ledger
             and type(frame.ledger_cell) is tuple and len(frame.ledger_cell) == 2
             and frame.ledger_cell[0] is frame and frame.ledger_cell[1] is ledger
             and all(type(v) is int for v in ledger[:3])
             and 0 <= ledger.ordinal < _WIRE_LIMIT
             and 0 <= ledger.received == ledger.committed <= _WIRE_LIMIT
             and type(ledger.seal) is _FrameSeal)
    step = frame.step_origin
    if step is None:
        _require(frame.step is None and frame.step_cell is None and ledger.ordinal == 0)
        return ledger.seal
    _require(type(step) is _Step and frame.step is step
             and type(frame.step_cell) is tuple and len(frame.step_cell) == 2
             and frame.step_cell[0] is frame and frame.step_cell[1] is step
             and type(step.scope) is _StepScope and step.scope is step.scope_origin
             and type(step.scope_cell) is tuple and len(step.scope_cell) == 2
             and step.scope_cell[0] is step and step.scope_cell[1] is step.scope
             and step.scope.frame is frame and type(step.scope.before) is _Ledger
             and all(type(v) is bool for v in (step.attempted, step.returned, step.known,
                 step.fed, step.complete, step.failed, step.inflight, step.reading_owned))
             and step.failed is False and step.inflight is False and step.reading_owned is False
             and type(step.received) is int)
    before = step.scope.before
    _require(all(type(v) is int for v in before[:3])
             and type(before.seal) is _FrameSeal and type(step.scope.ordinal) is int
             and step.scope.ordinal == before.ordinal + 1)
    if step.known:
        _require(type(step.count_cell) is tuple and len(step.count_cell) == 2
                 and step.count_cell[0] is step and step.count_cell[1] is step.received
                 and type(step.requested) is int
                 and 0 < step.received <= step.requested <= CHUNK_LIMIT
                 and step.attempted is True and step.returned is True
                 and before.received + step.received <= _WIRE_LIMIT)
    else:
        _require(step.count_cell is None and step.received == 0 and step.returned is False)
    if step.complete:
        _require(step.fed is True and ledger is step.committed_ledger
                 and ledger.ordinal == step.scope.ordinal
                 and ledger.received == before.received + step.received
                 and ledger.committed == before.committed + step.received
                 and ledger.seal is step.after
                 and step.pending is None and step.pending_cell is None)
    else:
        _require(ledger is before)
        if step.known:
            _require(type(step.pending_cell) is tuple and len(step.pending_cell) == 3
                     and step.pending_cell[0] is step and type(step.pending) is bytes
                     and step.pending_cell[1] is step.pending
                     and type(step.pending_cell[2]) is int
                     and step.pending_cell[2] == len(step.pending) == step.received)
    if not step.fed:
        _require(step.after is None and step.fact is None and step.fact_cell is None)
        return before.seal
    _require(type(step.after) is _FrameSeal and type(step.fact) is _FrameReadFact
             and type(step.fact_cell) is tuple and len(step.fact_cell) == 2
             and step.fact_cell[0] is step and step.fact_cell[1] is step.fact
             and step.fact.scope is frame.scope
             and all(type(v) is int for v in step.fact[1:5])
             and step.fact.ordinal == step.scope.ordinal and step.fact.count == step.received
             and step.fact.total_received == before.received + step.received
             and step.fact.total_committed == before.committed + step.received
             and step.fact.after is step.after)
    return step.after


def _finished(frame, seal):
    p, result = frame.scope.parser, frame.result_origin
    _require(frame.finish_returned is True and type(result) is DiscardedFrame
             and type(frame.finish_cell) is tuple and len(frame.finish_cell) == 5
             and frame.finish_cell[0] is frame and frame.finish_cell[1] is frame.ledger_origin
             and frame.finish_cell[2] is seal
             and type(seal.target) is int and type(seal.received) is int
             and type(seal.needed) is int and seal.needed == 0
             and type(result.phase) is str and type(result.sequence) is int
             and type(result.digest) is ConsistentFrameDigest
             and frame.result is result
             and type(frame.result_cell) is tuple and len(frame.result_cell) == 2
             and frame.result_cell[0] is frame and frame.result_cell[1] is result
             and p is seal.parser and p._finished is True and p._failed is False
             and p._fact is result and type(p._fact_allocation) is tuple
             and len(p._fact_allocation) == 2 and p._fact_allocation[0] is p
             and p._fact_allocation[1] is result
             and p._claim_origin is frame.scope.receipt.checked
             and p._claim is frame.scope.receipt.checked
             and p._binding_origin is frame.scope.binding and p._binding is frame.scope.binding
             and p._expected == (frame.scope.phase, frame.scope.sequence)
             and p._buffer is seal.buffer and p._buffer_origin is seal.buffer
             and type(seal.buffer) is bytearray and bytes(seal.buffer) == seal.value
             and p._header is seal.header and p._header_origin is seal.header
             and type(p._header_allocation) is tuple and len(p._header_allocation) == 3
             and p._header_allocation[0] is p and p._header_allocation[1] is seal.header
             and type(p._header_allocation[2]) is bytes
             and p._header_allocation[2] == seal.value
             and p._stream is seal.stream and p._stream_origin is seal.stream
             and type(p._stream_allocation) is tuple and len(p._stream_allocation) == 3
             and p._stream_allocation[0] is p and p._stream_allocation[1] is seal.stream
             and p._stream_allocation[2] is seal.header
             and type(p._hash_allocation) is tuple and len(p._hash_allocation) == 3
             and p._hash_allocation[0] is p and p._hash_allocation[1] is seal.stream
             and p._hash_allocation[2] is seal.hasher
             and type(seal.stream) is CommittedFrameDigest
             and seal.stream._finished is True and seal.stream._failed is False
             and seal.stream._hasher is seal.hasher and seal.stream._hasher_origin is seal.hasher
             and type(seal.hasher) is _HASH_TYPE
             and type(seal.stream._received) is int
             and seal.stream._received == seal.received == seal.stream._body_length
             and p._terminal_origin is seal.terminal and p._terminal is seal.terminal
             and type(seal.terminal) is bytearray and not seal.terminal
             and result.phase == frame.scope.phase and result.sequence == frame.scope.sequence
             and result.digest is p._digest
             and type(result.digest.frame_sha256) is str
             and type(result.digest.frame_length) is int
             and result.digest.frame_sha256 == frame.scope.receipt.checked.frame_sha256
             and result.digest.frame_length == frame.scope.receipt.checked.frame_length)
    if frame.scope.phase == "RESULT":
        _require(result.terminal is None and seal.terminal_value == b"")
    else:
        _require(type(result.terminal) is bytes and result.terminal == seal.terminal_value)
    digest = result.digest
    _require(type(p._digest_allocation) is tuple and len(p._digest_allocation) == 2
             and p._digest_allocation[0] is p and p._digest_allocation[1] is digest)
    cells = (p._header_allocation, p._stream_allocation, p._hash_allocation,
             p._fact_allocation, p._digest_allocation)
    values = (digest.frame_sha256, digest.frame_length)
    value = _HASH_HEX(seal.hasher)
    _require(type(value) is str and type(seal.digest) is str and value == seal.digest
             and frame.result is result and frame.result_origin is result
             and type(frame.result_cell) is tuple and len(frame.result_cell) == 2
             and frame.result_cell[0] is frame and frame.result_cell[1] is result
             and p._fact is result and p._header is seal.header and p._header_origin is seal.header
             and p._header_allocation is cells[0] and p._stream_allocation is cells[1]
             and p._hash_allocation is cells[2] and p._fact_allocation is cells[3]
             and p._digest_allocation is cells[4]
             and p._stream_origin is seal.stream
             and p._stream is seal.stream and seal.stream._hasher_origin is seal.hasher
             and seal.stream._hasher is seal.hasher
             and seal.stream._finished is True and seal.stream._failed is False
             and type(seal.stream._received) is int
             and seal.stream._received == seal.received
             and seal.stream._received_snapshot is seal.stream._received
             and result.digest is digest and p._digest is digest
             and type(digest.frame_sha256) is str and digest.frame_sha256 is values[0]
             and type(digest.frame_length) is int and digest.frame_length is values[1]
             and p._buffer_origin is seal.buffer and p._buffer is seal.buffer
             and bytes(seal.buffer) == seal.value
             and p._terminal_origin is seal.terminal and p._terminal is seal.terminal
             and not seal.terminal)
    return result


def _current_work(native, scope):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    NativeCleanupRead._progress_work_current(native)
    frame = _scope(native, scope)
    if not frame.initialized:
        _require(frame.ledger is None and frame.step is None)
        return frame
    seal = _ledger(frame)
    if frame.finish_returned:
        _finished(frame, seal)
    else:
        _same(_snapshot(frame), seal)
    SignedReadNotice._role_seal(scope.notice)
    _require(SignedReadNotice._actor(scope.notice) is scope.idle_scope[0].reservation
             and _scope(native, scope) is frame and _ledger(frame) is seal)
    return frame


def _wipe(frame):
    cell = frame.parser_cell
    if (type(cell) is tuple and len(cell) == 2 and cell[0] is frame
            and type(cell[1]) is CommittedFrameDiscard):
        parser = cell[1]
        fields = vars(parser)
        for name in ("_buffer_allocation", "_terminal_allocation"):
            owned = fields.get(name)
            if (type(owned) is tuple and len(owned) == 2 and owned[0] is parser
                    and type(owned[1]) is bytearray):
                owned[1][:] = b"\x00" * len(owned[1])
                owned[1].clear()
        parser._failed = True
    step = frame.step_origin
    if type(step) is _Step:
        step.pending = step.pending_cell = None


def _fail(native, scope, frame):
    frame.failed = native._failed = native._unknown = True
    scope.notice._failed = scope.notice._unknown = True
    scope.idle_scope[0].reservation.capture.cleanup._unknown = True
    _wipe(frame)


def start_frame(native):
    from .presentation_credential_cleanup_read import (
        NativeCleanupRead,
        _AuthAttempt,
        _AuthReceipt,
        _AuthScope,
        _ParserSeal,
    )

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._actor(s.notice)
    auth = native._auth_origin
    _require(native._frame_origin is None and native._frame is None
             and native._frame_allocation_origin is None
             and type(auth) is _AuthAttempt and native._auth is auth
             and type(native._auth_allocation_origin) is tuple
             and len(native._auth_allocation_origin) == 2
             and native._auth_allocation_origin[0] is native
             and native._auth_allocation_origin[1] is auth
             and auth.complete is True and auth.returned is True and auth.failed is False
             and type(auth.scope) is _AuthScope and auth.scope is auth.scope_origin
             and type(auth.scope_allocation) is tuple
             and len(auth.scope_allocation) == 2 and auth.scope_allocation[0] is auth
             and auth.scope_allocation[1] is auth.scope
             and auth.scope.owner is native and auth.scope.scope is s
             and type(auth.scope.before) is _ParserSeal
             and type(auth.scope.before.value) is bytes
             and type(auth.fact) is _AuthReceipt and auth.fact.scope is auth.scope
             and auth.fact.owner is native and auth.fact.checked is auth.checked
             and type(auth.fact_cell) is tuple and len(auth.fact_cell) == 2
             and auth.fact_cell[0] is auth and auth.fact_cell[1] is auth.fact
             and type(auth.fact.values) is tuple and len(auth.fact.values) == 4
             and type(auth.fact.values[3]) is str
             and auth.fact.values[3] in ("RESULT", "TERMINAL"))
    receipt = auth.fact
    capture = s.idle_scope[0].reservation.capture
    _require(capture.phase is RemotePhase.GO_SENT and capture.body is None
             and type(capture.envelope.values) is bytes
             and type(auth.scope.before.value) is bytes)
    original = capture.envelope.values
    raw = auth.scope.before.value
    outer = s.cursor._outer_origin
    _require(type(outer) is bytes and s.cursor._outer is outer
             and len(outer) <= 8 + HEADER_LIMIT
             and outer == (original[len(raw):] if len(original) > len(raw) else b"")
             and (len(original) <= len(raw) or original[:len(raw)] == raw))
    parser = CommittedFrameDiscard.__new__(CommittedFrameDiscard)
    frame = _Frame.__new__(_Frame)
    frame.scope = frame.scope_origin = _FrameScope(native, s, auth, receipt,
        capture.scope.write_scope.intent.binding, receipt.values[3], 1, outer, parser)
    frame.scope_cell = (frame, frame.scope)
    frame.parser = frame.parser_origin = parser
    frame.parser_cell = (frame, parser)
    frame.initialized = frame.failed = frame.finish_attempted = False
    frame.finish_returned = frame.complete = frame.outer_attempted = False
    frame.ledger = frame.ledger_origin = frame.ledger_cell = None
    frame.step = frame.step_origin = frame.step_cell = None
    frame.result = frame.result_origin = frame.result_cell = frame.done = frame.done_cell = None
    frame.finish_cell = None
    native._frame = native._frame_origin = frame
    native._frame_allocation_origin = (native, frame)
    failed = False
    try:
        _current_work(native, s)
        CommittedFrameDiscard.__init__(parser, receipt.checked, binding=frame.scope.binding,
                                      phase=frame.scope.phase, sequence=frame.scope.sequence)
        frame.outer_attempted = True
        offset = 0
        while offset < len(outer):
            count = min(CommittedFrameDiscard.needed.fget(parser), len(outer) - offset)
            _require(count > 0)
            CommittedFrameDiscard.feed(parser, outer[offset:offset + count])
            offset += count
        seal = _snapshot(frame)
        total = receipt.total_received
        _require(type(total) is int and total >= 0)
        ledger = _Ledger(0, total, total, seal)
        frame.ledger = frame.ledger_origin = ledger
        frame.ledger_cell = (frame, ledger)
        frame.initialized = True
        _current_work(native, s)
        return frame.scope
    except BaseException:
        failed = True
        _fail(native, s, frame)
    if failed:
        raise FrameError("BI1_NATIVE_FRAME_START_UNKNOWN") from None


def _dispatch_snapshot(frame, seal, requested):
    """Fixed metadata/hash seals after final FD/mode probes; no clock/peer call."""
    p = frame.scope.parser
    _require(type(p) is CommittedFrameDiscard and p is seal.parser
             and p._initialized is True and p._failed is False and p._finished is False
             and p._inflight is False and p._finish_attempted is False
             and p._buffer is seal.buffer and p._buffer_origin is seal.buffer
             and type(seal.buffer) is bytearray and bytes(seal.buffer) == seal.value
             and type(p._target) is int and p._target is p._target_origin
             and p._target == seal.target
             and p._terminal is seal.terminal and p._terminal_origin is seal.terminal
             and type(seal.terminal) is bytearray
             and bytes(seal.terminal) == seal.terminal_value
             and p._header is seal.header and p._header_origin is seal.header
             and p._stream is seal.stream and p._stream_origin is seal.stream
             and p._claim is frame.scope.receipt.checked
             and p._claim_origin is frame.scope.receipt.checked
             and p._binding is frame.scope.binding and p._binding_origin is frame.scope.binding)
    if seal.stream is None:
        _require(seal.header is None and type(seal.target) is int
                 and requested == seal.target - len(seal.value))
    else:
        stream = seal.stream
        _require(type(stream) is CommittedFrameDigest
                 and stream._initialized is True and stream._failed is False
                 and stream._finished is False and stream._hasher is seal.hasher
                 and stream._hasher_origin is seal.hasher and type(seal.hasher) is _HASH_TYPE
                 and type(stream._received) is int and stream._received is stream._received_snapshot
                 and type(stream._body_length) is int
                 and stream._received == seal.received
                 and requested == min(CHUNK_LIMIT, stream._body_length - stream._received)
                 and _HASH_HEX(seal.hasher) == seal.digest)


def read_frame_next(native):
    from . import presentation_credential_cleanup_read as read_module
    from .presentation_credential_cleanup_read import _WIRE_LIMIT, NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    r = SignedReadNotice._actor(s.notice)
    frame = _scope(native, s)
    _require(frame.initialized is True and frame.finish_attempted is False)
    seal = _ledger(frame)
    _require(type(seal.needed) is int and 0 < seal.needed <= CHUNK_LIMIT)
    previous = frame.step_origin
    _require(previous is None or previous.complete is True)
    before = frame.ledger_origin
    step = _Step.__new__(_Step)
    step.scope = step.scope_origin = _StepScope(frame, before, before.ordinal + 1)
    step.scope_cell = (step, step.scope)
    step.attempted = step.returned = step.known = step.fed = step.complete = False
    step.failed = step.inflight = step.reading_owned = False
    step.received = 0
    step.requested = seal.needed
    step.count_cell = step.pending = step.pending_cell = None
    step.after = step.fact = step.fact_cell = step.committed_ledger = None
    frame.step = frame.step_origin = step
    frame.step_cell = (frame, step)
    failed = False
    chunk = copy = None
    held_parser = frame.scope.parser
    try:
        _current_work(native, s)
        _require(before.received + step.requested <= _WIRE_LIMIT)
        channel = r.capture.channel
        _require(channel._reading is False and channel._writing is False)
        NativeCleanupRead._final_socket_fence(native, s)
        SignedReadNotice._role_seal(s.notice)
        _dispatch_snapshot(frame, seal, step.requested)
        SignedReadNotice._role_seal(s.notice)
        _require(_scope(native, s) is frame and _ledger(frame) is seal
                 and SignedReadNotice._actor(s.notice) is r
                 and read_module._RECV is socket.socket.recv
                 and type(read_module._DONTWAIT) is int and read_module._DONTWAIT > 0)
        step.attempted = step.inflight = step.reading_owned = True
        channel._reading = True
        chunk = NativeCleanupRead._receive(s.sock, step.requested)
        step.returned = True
        if type(chunk) is bytes:
            step.received = len(chunk)
            step.count_cell = (step, step.received)
            step.known = True
            step.pending = chunk
            step.pending_cell = (step, chunk, step.received)
        cell = frame.step_cell
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is frame and cell[1] is step
                 and channel._socket is s.sock and channel._reading is True)
        channel._reading = False
        step.inflight = step.reading_owned = False
        _current_work(native, s)
        expected_hash = None
        if seal.stream is not None:
            copy = _HASH_COPY(seal.hasher)
            _HASH_UPDATE(copy, chunk)
            expected_hash = _HASH_HEX(copy)
            _current_work(native, s)
        CommittedFrameDiscard.feed(held_parser, chunk)
        after = _snapshot(frame)
        if seal.stream is None:
            _require(after.value == seal.value + chunk and after.terminal_value == b"")
            if after.stream is not None:
                _require(after.received == 0 and after.digest == _SHA256(after.value).hexdigest())
        else:
            _require(after.buffer is seal.buffer and after.value == seal.value
                     and after.header is seal.header and after.stream is seal.stream
                     and after.hasher is seal.hasher
                     and after.received == seal.received + step.received
                     and after.digest == expected_hash
                     and after.terminal is seal.terminal
                     and after.terminal_value == (seal.terminal_value + chunk
                         if frame.scope.phase == "TERMINAL" else b""))
        step.after = after
        step.fact = _FrameReadFact(frame.scope, step.scope.ordinal, step.received,
            before.received + step.received, before.committed + step.received, after)
        step.fact_cell = (step, step.fact)
        step.fed = True
        _current_work(native, s)
        ledger = _Ledger(step.scope.ordinal, step.fact.total_received,
                         step.fact.total_committed, after)
        step.committed_ledger = ledger
        frame.ledger = frame.ledger_origin = ledger
        frame.ledger_cell = (frame, ledger)
        step.pending = step.pending_cell = None
        step.complete = True
        _require(_ledger(frame) is after)
        if previous is not None:
            previous.scope_cell = previous.count_cell = previous.fact_cell = None
            previous.failed = True
        return step.fact
    except BaseException:
        failed = step.failed = True
        _fail(native, s, frame)
    finally:
        chunk = copy = None
        step.pending = step.pending_cell = None
        cell = frame.step_cell
        if (step.reading_owned is True and step.inflight is True
                and type(cell) is tuple and len(cell) == 2 and cell[0] is frame and cell[1] is step
                and r.capture.channel._socket is s.sock and r.capture.channel._reading is True):
            r.capture.channel._reading = False
            step.reading_owned = step.inflight = False
    if failed:
        raise FrameError("BI1_NATIVE_FRAME_READ_UNKNOWN") from None


def finish_frame(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._actor(s.notice)
    frame = _scope(native, s)
    seal = _ledger(frame)
    _require(frame.initialized is True and frame.finish_attempted is False and seal.needed == 0)
    ledger, step, held_scope = frame.ledger_origin, frame.step_origin, frame.scope
    count = 0 if step is None else step.received
    total = ledger.received
    _require(type(count) is int and type(total) is int)
    frame.finish_cell = (frame, ledger, seal, count, total)
    frame.finish_attempted = True
    failed = False
    try:
        _current_work(native, s)
        result = CommittedFrameDiscard.finish(held_scope.parser)
        frame.result = frame.result_origin = result
        frame.result_cell = (frame, result)
        frame.finish_returned = True
        _current_work(native, s)
        frame.done = _FrameDone(held_scope, result, count, total)
        frame.done_cell = (frame, frame.done)
        frame.complete = True
        return frame.done
    except BaseException:
        failed = True
        _fail(native, s, frame)
    if failed:
        raise FrameError("BI1_NATIVE_FRAME_FINISH_UNKNOWN") from None


def current_frame_for_cleanup(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._cleanup_actor(s.notice)
    frame = _scope(native, s)
    failed = False
    try:
        NativeCleanupRead._base_progress_for_cleanup(native)
        _require(frame.initialized is True)
        seal = _ledger(frame)
        if frame.finish_returned:
            _finished(frame, seal)
            _require(frame.complete is True and type(frame.done) is _FrameDone
                     and type(frame.done_cell) is tuple and len(frame.done_cell) == 2
                     and frame.done_cell[0] is frame and frame.done_cell[1] is frame.done
                     and frame.done.scope is frame.scope and frame.done.data is frame.result_origin)
            value = frame.done
        else:
            _same(_snapshot(frame), seal)
            step = frame.step_origin
            _require(step is None or step.complete is True)
            value = frame.scope.receipt if step is None else step.fact
        SignedReadNotice._role_seal(s.notice)
        _require(SignedReadNotice._cleanup_actor(s.notice) is s.idle_scope[0].reservation
                 and _scope(native, s) is frame and _ledger(frame) is seal)
        return value
    except BaseException:
        failed = True
        _fail(native, s, frame)
    if failed:
        raise FrameError("BI1_NATIVE_FRAME_OBSERVER_UNKNOWN") from None


def retire_frame_pending(native):
    cell = native._frame_allocation_origin
    if (type(cell) is tuple and len(cell) == 2 and cell[0] is native
            and type(cell[1]) is _Frame):
        cell[1].failed = True
        _wipe(cell[1])
