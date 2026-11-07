"""Original-reader RESULT/1 -> TERMINAL/2 authentication continuation.

No terminal-body acceptance, ACK, native release or production admission. Previous
record allocations/counts are retained, never reset to start another record.
"""
from __future__ import annotations

import json
import socket
from typing import NamedTuple

from .presentation_credential_cleanup_notice import SignedReadNotice
from .presentation_credential_codec import RECORD_LIMIT
from .presentation_credential_phase import _EXPECTED, ConsistentCommitment
from .presentation_credential_stream import SignedCleanupAuthPrefix
from .presentation_jobs import FrameError


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_TERMINAL_AUTH_REFUSED")


class _Scope(NamedTuple):
    native: object
    read_scope: object
    predecessor: object
    seed: int
    pins: tuple
    expected: tuple
    parser: SignedCleanupAuthPrefix

    def __repr__(self):
        return "<TerminalAuthScope original-result-successor redacted>"


class _Seal(NamedTuple):
    buffer: bytearray
    value: bytes
    target: int
    header_done: bool
    pins: tuple
    expected: tuple
    context: tuple

    def __repr__(self):
        return "<TerminalAuthSeal bounded-prefix redacted>"


class _Stage:
    def __repr__(self):
        return "<TerminalAuth original-reader one-record>"


class _Step:
    def __repr__(self):
        return "<TerminalAuthStep original-socket bounded>"


class _ReadFact(NamedTuple):
    scope: _Scope
    ordinal: int
    count: int
    total_received: int

    def __repr__(self):
        return "<TerminalAuthRead no-phase-acceptance>"


class _AuthFact(NamedTuple):
    scope: _Scope
    checked: ConsistentCommitment
    count: int
    total_received: int

    def __repr__(self):
        return "<TerminalAuthFact signed-DATA no-terminal-acceptance>"


def _predecessor(native, s, *, cleanup):
    from .presentation_credential_cleanup_body import _BodyDone, _Finish
    from .presentation_credential_cleanup_frame import (
        _current_work,
        _Frame,
        _FrameDone,
        _FrameScope,
        current_frame_for_cleanup,
    )
    from .presentation_credential_cleanup_read import NativeCleanupRead

    frame = native._frame_origin
    if frame is not None:
        if cleanup:
            value = current_frame_for_cleanup(native)
        else:
            actual = _current_work(native, s)
            _require(actual is frame and type(frame) is _Frame and frame.complete is True)
            value = frame.done
        _require(type(value) is _FrameDone and value is frame.done
                 and type(frame.done_cell) is tuple and len(frame.done_cell) == 2
                 and frame.done_cell[0] is frame and frame.done_cell[1] is value
                 and type(value.scope) is _FrameScope and value.scope is frame.scope
                 and type(value.scope.phase) is str and value.scope.phase == "RESULT"
                 and type(value.scope.sequence) is int and value.scope.sequence == 1)
        return value
    value = (NativeCleanupRead._base_progress_for_cleanup(native) if cleanup
             else NativeCleanupRead._progress_work_current(native))
    body = native._body_finish_origin
    _require(type(body) is _Finish and body.complete is True and type(value) is _BodyDone
             and value is body.fact and value.scope is body.scope)
    return value


def _scope(native, s):
    stage = native._terminal_origin
    _require(type(stage) is _Stage and native._terminal is stage
             and type(native._terminal_allocation) is tuple
             and len(native._terminal_allocation) == 2
             and native._terminal_allocation[0] is native
             and native._terminal_allocation[1] is stage
             and type(stage.scope) is _Scope and stage.scope is stage.scope_origin
             and type(stage.scope_cell) is tuple and len(stage.scope_cell) == 2
             and stage.scope_cell[0] is stage and stage.scope_cell[1] is stage.scope)
    scope = stage.scope
    _require(scope.native is native and scope.read_scope is s
             and type(scope.seed) is int and scope.seed > 0
             and type(scope.pins) is tuple and len(scope.pins) == 2
             and all(type(v) is bytes and len(v) == 32 for v in scope.pins)
             and scope.pins is s.idle_scope[0].reservation.capture.scope.pins
             and type(scope.expected) is tuple
             and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                     for row in scope.expected)
             and {row[0] for row in scope.expected} == _EXPECTED - {"phase"}
             and len(scope.expected) == len(_EXPECTED) - 1
             and dict(scope.expected)["sequence"] == 2
             and type(scope.parser) is SignedCleanupAuthPrefix
             and stage.parser is scope.parser and stage.parser_origin is scope.parser
             and type(stage.parser_cell) is tuple and len(stage.parser_cell) == 2
             and stage.parser_cell[0] is stage and stage.parser_cell[1] is scope.parser
             and all(type(v) is bool for v in (
                 stage.initialized, stage.failed, stage.finish_attempted,
                 stage.finish_returned, stage.complete)) and stage.failed is False
             and type(stage.received) is int and type(stage.ordinal) is int
             and 0 <= stage.received <= RECORD_LIMIT
             and 0 <= stage.ordinal <= RECORD_LIMIT)
    return stage


def _snapshot(stage, *, pure=False, held_scope=None):
    if held_scope is None:
        held_scope = stage.scope
    _require(type(held_scope) is _Scope and type(held_scope.parser) is SignedCleanupAuthPrefix
             and stage.scope is held_scope and stage.scope_origin is held_scope
             and type(held_scope.pins) is tuple and len(held_scope.pins) == 2
             and all(type(v) is bytes and len(v) == 32 for v in held_scope.pins)
             and type(held_scope.expected) is tuple
             and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                     for row in held_scope.expected)
             and len(held_scope.expected) == len(_EXPECTED) - 1
             and {row[0] for row in held_scope.expected} == _EXPECTED - {"phase"})
    p = held_scope.parser
    if not pure:
        SignedCleanupAuthPrefix._guard(p)
    _require(stage.scope is held_scope and stage.scope_origin is held_scope
             and type(stage.scope_cell) is tuple and len(stage.scope_cell) == 2
             and stage.scope_cell[0] is stage and stage.scope_cell[1] is held_scope)
    _require(type(p._buffer) is bytearray and p._buffer is p._buffer_origin
             and type(p._buffer_allocation_origin) is tuple
             and len(p._buffer_allocation_origin) == 2
             and p._buffer_allocation_origin[0] is p
             and p._buffer_allocation_origin[1] is p._buffer
             and p._initialized is True and p._failed is False and p._finished is False
             and type(p._target) is int and p._target is p._target_origin
             and type(p._header_done) is bool and p._header_done is p._header_done_origin
             and type(p._pins_origin) is tuple and len(p._pins_origin) == 2
             and all(type(v) is bytes and len(v) == 32 for v in p._pins_origin)
             and p._pins is p._pins_origin
             and type(p._expected_origin) is tuple
             and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                     for row in p._expected_origin)
             and len(p._expected_origin) == len(_EXPECTED) - 1
             and {row[0] for row in p._expected_origin} == _EXPECTED - {"phase"}
             and p._expected is p._expected_origin
             and type(p._context_origin) is tuple and len(p._context_origin) == 2
             and all(type(v) is int for v in p._context_origin)
             and p._context is p._context_origin)
    _require(not any(k in vars(p) for k in ("feed", "finish", "needed", "_guard"))
             and p._pins_origin == held_scope.pins and p._expected_origin == held_scope.expected)
    return _Seal(p._buffer_origin, bytes(p._buffer_origin), p._target_origin,
                 p._header_done_origin, p._pins_origin, p._expected_origin, p._context_origin)


def _same(actual, expected):
    _require(type(actual) is _Seal and type(expected) is _Seal
             and actual.buffer is expected.buffer and type(actual.value) is bytes
             and type(expected.value) is bytes and actual.value == expected.value
             and type(actual.target) is int and type(expected.target) is int
             and actual.target == expected.target and actual.header_done is expected.header_done
             and actual.pins is expected.pins and actual.expected is expected.expected
             and actual.context is expected.context)


def _state(stage, *, pure=True):
    seal = stage.seal_origin
    _require(type(seal) is _Seal and stage.seal is seal
             and type(stage.seal_cell) is tuple and len(stage.seal_cell) == 2
             and stage.seal_cell[0] is stage and stage.seal_cell[1] is seal)
    _require(type(seal.buffer) is bytearray and type(seal.value) is bytes
             and type(seal.target) is int and type(seal.header_done) is bool
             and type(seal.pins) is tuple and len(seal.pins) == 2
             and all(type(v) is bytes and len(v) == 32 for v in seal.pins)
             and type(seal.expected) is tuple and type(seal.context) is tuple
             and len(seal.context) == 2 and all(type(v) is int for v in seal.context)
             and stage.received == len(seal.value))
    step = stage.step_origin
    if step is None:
        _require(stage.step is None and stage.step_cell is None
                 and stage.ordinal == stage.received == 0 and stage.active_read_cell is None)
    else:
        _require(type(step) is _Step and stage.step is step
                 and type(stage.step_cell) is tuple and len(stage.step_cell) == 2
                 and stage.step_cell[0] is stage and stage.step_cell[1] is step
                 and type(stage.active_read_cell) is tuple and len(stage.active_read_cell) == 2
                 and stage.active_read_cell[0] is stage and stage.active_read_cell[1] is step
                 and step.owner is stage and step.scope is stage.scope
                 and type(step.scope_cell) is tuple and len(step.scope_cell) == 3
                 and step.scope_cell[0] is step and step.scope_cell[1] is stage
                 and step.scope_cell[2] is stage.scope
                 and all(type(v) is bool for v in (
                     step.attempted, step.returned, step.known, step.fed,
                     step.complete, step.inflight, step.reading_owned))
                 and type(step.ordinal) is int
                 and step.ordinal == stage.ordinal + (0 if step.complete is True else 1)
                 and type(step.total_before) is int and step.total_before >= 0
                 and type(step.requested) is int and step.requested > 0
                 and type(step.before) is _Seal
                 and type(step.before.target) is int and type(step.before.value) is bytes
                 and step.requested == step.before.target - len(step.before.value))
        if step.known:
            _require(type(step.count) is int and type(step.count_cell) is tuple
                     and len(step.count_cell) == 2 and step.count_cell[0] is step
                     and step.count_cell[1] is step.count and step.returned is True
                     and 0 <= step.count <= step.requested)
            if not step.complete:
                _require(type(step.pending) is bytes and type(step.pending_cell) is tuple
                         and len(step.pending_cell) == 3 and step.pending_cell[0] is step
                         and step.pending_cell[1] is step.pending
                         and type(step.pending_cell[2]) is int
                         and step.pending_cell[2] == len(step.pending) == step.count)
        else:
            _require(step.count_cell is None and type(step.count) is int and step.count == 0
                     and step.returned is False and step.pending is None
                     and step.pending_cell is None)
        if step.complete:
            _require(step.known and step.fed and step.pending is None
                     and step.pending_cell is None and step.after is seal
                     and stage.received == step.total_before + step.count
                     and type(step.fact) is _ReadFact and step.fact.scope is stage.scope
                     and all(type(v) is int for v in step.fact[1:])
                     and step.fact.ordinal == step.ordinal and step.fact.count == step.count
                     and step.fact.total_received == stage.scope.seed + stage.received
                     and type(step.fact_cell) is tuple and len(step.fact_cell) == 2
                     and step.fact_cell[0] is step and step.fact_cell[1] is step.fact)
        else:
            _require(stage.received == step.total_before and seal is step.before)
    if stage.finish_returned:
        fact = stage.fact
        p = stage.scope.parser
        _require(type(fact) is _AuthFact and fact.scope is stage.scope
                 and type(fact.checked) is ConsistentCommitment
                 and type(stage.checked_values) is tuple and len(stage.checked_values) == 3
                 and type(stage.checked_values[0]) is bytes
                 and type(stage.checked_values[1]) is str
                 and type(stage.checked_values[2]) is int
                 and type(fact.checked.frame_sha256) is str
                 and type(fact.checked.frame_length) is int
                 and fact.checked.frame_sha256 is stage.checked_values[1]
                 and fact.checked.frame_length is stage.checked_values[2]
                 and type(stage.checked_cell) is tuple and len(stage.checked_cell) == 2
                 and stage.checked_cell[0] is stage and stage.checked_cell[1] is fact.checked
                 and type(stage.fact_cell) is tuple and len(stage.fact_cell) == 2
                 and stage.fact_cell[0] is stage and stage.fact_cell[1] is fact
                 and type(fact.count) is int and fact.count == stage.received
                 and type(fact.total_received) is int
                 and fact.total_received == stage.scope.seed + stage.received
                 and p._initialized is True and p._finished is True and p._failed is False
                 and type(p._target) is int and p._target is seal.target
                 and p._target_origin is seal.target
                 and p._header_done is True and p._header_done_origin is True
                 and type(p._buffer_allocation_origin) is tuple
                 and len(p._buffer_allocation_origin) == 2
                 and p._buffer_allocation_origin[0] is p
                 and p._buffer_allocation_origin[1] is seal.buffer
                 and p._buffer is seal.buffer and p._buffer_origin is seal.buffer
                 and not seal.buffer and p._pins_origin is seal.pins
                 and p._pins is seal.pins and p._expected_origin is seal.expected
                 and p._expected is seal.expected and p._context_origin is seal.context
                 and p._context is seal.context
                 and type(fact.checked.canonical_json) is bytes
                 and fact.checked.canonical_json is stage.checked_values[0]
                 and fact.checked.canonical_json == seal.value[8:-64])
    else:
        _same(_snapshot(stage, pure=pure), seal)
    return seal


def _current(native, s, *, cleanup=False):
    stage = _scope(native, s)
    held_scope = stage.scope
    value = _predecessor(native, s, cleanup=cleanup)
    _require(_scope(native, s) is stage and stage.scope is held_scope)
    _require(value is held_scope.predecessor
             and type(value.total_received) is int and held_scope.seed == value.total_received)
    if stage.initialized:
        _state(stage, pure=True)
    _require(_scope(native, s) is stage and stage.scope is held_scope)
    return stage


def _fail(native, s, stage):
    stage.failed = native._failed = native._unknown = True
    s.notice._failed = s.notice._unknown = True
    s.idle_scope[0].reservation.capture.cleanup._unknown = True
    cell = stage.parser_cell
    if (type(cell) is tuple and len(cell) == 2 and cell[0] is stage
            and type(cell[1]) is SignedCleanupAuthPrefix):
        fields = vars(cell[1])
        buffer_cell = fields.get("_buffer_allocation_origin")
        if (type(buffer_cell) is tuple and len(buffer_cell) == 2
                and buffer_cell[0] is cell[1] and type(buffer_cell[1]) is bytearray):
            bytearray.clear(buffer_cell[1])
    owned = stage.active_read_cell
    if (type(owned) is tuple and len(owned) == 2 and owned[0] is stage
            and type(owned[1]) is _Step):
        owned[1].pending = owned[1].pending_cell = None


def begin(native):
    from .presentation_credential_cleanup_body import _BodyDone, _Finish
    from .presentation_credential_cleanup_frame import _Frame, _FrameDone, _FrameScope
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._actor(s.notice)
    _require(native._terminal is None and native._terminal_origin is None
             and native._terminal_allocation is None and native._failed is False)
    # Pure original completion allocation joins before callbacks. No caller-
    # supplied receipt, phase, sequence, socket, parser or counter is accepted.
    frame = native._frame_origin
    if frame is not None:
        _require(type(frame) is _Frame and native._frame is frame
                 and type(native._frame_allocation_origin) is tuple
                 and len(native._frame_allocation_origin) == 2
                 and native._frame_allocation_origin[0] is native
                 and native._frame_allocation_origin[1] is frame and frame.complete is True
                 and type(frame.done) is _FrameDone
                 and type(frame.done_cell) is tuple and len(frame.done_cell) == 2
                 and frame.done_cell[0] is frame and frame.done_cell[1] is frame.done
                 and type(frame.done.scope) is _FrameScope and frame.done.scope is frame.scope
                 and type(frame.done.scope.phase) is str and frame.done.scope.phase == "RESULT"
                 and type(frame.done.scope.sequence) is int and frame.done.scope.sequence == 1)
        predecessor = frame.done
    else:
        body = native._body_finish_origin
        _require(type(body) is _Finish and native._body_finish is body
                 and type(native._body_finish_allocation) is tuple
                 and len(native._body_finish_allocation) == 2
                 and native._body_finish_allocation[0] is native
                 and native._body_finish_allocation[1] is body and body.complete is True
                 and type(body.fact) is _BodyDone and type(body.fact_cell) is tuple
                 and len(body.fact_cell) == 2 and body.fact_cell[0] is body
                 and body.fact_cell[1] is body.fact)
        predecessor = body.fact
    _require(type(predecessor.total_received) is int and predecessor.total_received > 0)
    capture = s.idle_scope[0].reservation.capture
    rows = capture.scope.expected
    _require(type(rows) is tuple and len(rows) == len(_EXPECTED)
             and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                     for row in rows)
             and {row[0] for row in rows} == _EXPECTED)
    expected = dict(rows)
    _require(type(expected.get("sequence")) is int and expected["sequence"] == 1)
    expected.pop("phase")
    expected["sequence"] = 2
    parser = SignedCleanupAuthPrefix.__new__(SignedCleanupAuthPrefix)
    stage = _Stage.__new__(_Stage)
    stage.scope = stage.scope_origin = _Scope(native, s, predecessor,
        predecessor.total_received, capture.scope.pins, tuple(sorted(expected.items())), parser)
    stage.scope_cell = (stage, stage.scope)
    stage.parser = stage.parser_origin = parser
    stage.parser_cell = (stage, parser)
    stage.initialized = stage.failed = stage.finish_attempted = False
    stage.finish_returned = stage.complete = False
    stage.received = stage.ordinal = 0
    stage.step = stage.step_origin = stage.step_cell = stage.active_read_cell = None
    stage.seal = stage.seal_origin = stage.seal_cell = None
    stage.fact = stage.fact_cell = stage.checked_cell = stage.checked_values = None
    native._terminal = native._terminal_origin = stage
    native._terminal_allocation = (native, stage)
    held_scope = stage.scope
    try:
        _current(native, s)
        SignedCleanupAuthPrefix.__init__(parser, b"", sender_public=capture.scope.pins[0],
            receiver_public=capture.scope.pins[1], expected_context=expected)
        seal = _snapshot(stage, held_scope=held_scope)
        stage.seal = stage.seal_origin = seal
        stage.seal_cell = (stage, seal)
        stage.initialized = True
        _current(native, s)
        return stage.scope
    except BaseException:
        _fail(native, s, stage)
    raise FrameError("BI1_NATIVE_TERMINAL_AUTH_BEGIN_UNKNOWN") from None


def read_next(native):
    from . import presentation_credential_cleanup_read as nr
    from .presentation_credential_cleanup_read import NativeCleanupRead
    from .presentation_credential_codec import payload_size

    s = NativeCleanupRead._origin(native)
    r = SignedReadNotice._actor(s.notice)
    stage = _scope(native, s)
    _require(stage.initialized and not stage.finish_attempted)
    seal = _state(stage)
    requested = seal.target - len(seal.value)
    _require(requested > 0 and (stage.step_origin is None or stage.step_origin.complete))
    previous = stage.step_origin
    held_scope = stage.scope
    step = _Step.__new__(_Step)
    step.owner, step.scope = stage, stage.scope
    step.scope_cell = (step, stage, stage.scope)
    step.ordinal, step.total_before = stage.ordinal + 1, stage.received
    step.before, step.requested = seal, requested
    step.attempted = step.returned = step.known = step.fed = step.complete = False
    step.inflight = step.reading_owned = False
    step.count = 0
    step.count_cell = step.pending = step.pending_cell = None
    step.after = step.fact = step.fact_cell = None
    stage.step = stage.step_origin = step
    stage.step_cell = (stage, step)
    stage.active_read_cell = (stage, step)
    chunk = None
    try:
        _current(native, s)
        channel = r.capture.channel
        _require(channel._reading is False and channel._writing is False
                 and stage.scope.seed + stage.received + requested <= nr._WIRE_LIMIT)
        NativeCleanupRead._final_socket_fence(native, s)
        SignedReadNotice._role_seal(s.notice)
        _require(_scope(native, s) is stage and _state(stage, pure=True) is seal
                 and SignedReadNotice._actor(s.notice) is r
                 and nr._RECV is socket.socket.recv
                 and type(nr._DONTWAIT) is int and nr._DONTWAIT > 0
                 and r.capture.channel is channel and channel._socket is s.sock
                 and channel._reading is False and channel._writing is False)
        step.attempted = step.inflight = step.reading_owned = True
        channel._reading = True
        chunk = NativeCleanupRead._receive(s.sock, requested)
        step.returned = True
        if type(chunk) is bytes:
            step.count = len(chunk)
            step.count_cell = (step, step.count)
            step.known = True
            step.pending = chunk
            step.pending_cell = (step, chunk, step.count)
        _require(_scope(native, s) is stage
                 and stage.step is step and stage.step_origin is step
                 and type(stage.step_cell) is tuple and len(stage.step_cell) == 2
                 and stage.step_cell[0] is stage and stage.step_cell[1] is step
                 and type(stage.active_read_cell) is tuple and len(stage.active_read_cell) == 2
                 and stage.active_read_cell[0] is stage and stage.active_read_cell[1] is step
                 and channel._socket is s.sock and channel._reading is True)
        channel._reading = False
        step.reading_owned = step.inflight = False
        _require(type(chunk) is bytes and 0 < step.count <= requested)
        _current(native, s)
        _require(step.pending is chunk and type(step.pending_cell) is tuple
                 and len(step.pending_cell) == 3 and step.pending_cell[0] is step
                 and step.pending_cell[1] is chunk
                 and type(step.pending_cell[2]) is int
                 and step.pending_cell[2] == len(chunk) == step.count)
        value = seal.value + chunk
        target, header_done = seal.target, seal.header_done
        if not header_done and len(value) == 8:
            target, header_done = 8 + payload_size(value), True
        expected = seal._replace(value=value, target=target, header_done=header_done)
        SignedCleanupAuthPrefix.feed(held_scope.parser, chunk)
        step.fed = True
        after = _snapshot(stage, held_scope=held_scope)
        _same(after, expected)
        step.after = after
        # Post-feed currentness validates progress against the held expected seal,
        # not the now obsolete stopped parser snapshot.
        stage.seal = stage.seal_origin = after
        stage.seal_cell = (stage, after)
        stage.received = step.total_before + step.count
        stage.ordinal = step.ordinal
        step.fact = _ReadFact(held_scope, step.ordinal, step.count,
                              held_scope.seed + stage.received)
        step.fact_cell = (step, step.fact)
        step.pending = step.pending_cell = None
        step.complete = True
        _current(native, s)
        if previous is not None:
            previous.scope_cell = previous.count_cell = previous.fact_cell = None
            previous.pending = previous.pending_cell = None
        return step.fact
    except BaseException:
        _fail(native, s, stage)
    finally:
        chunk = None
        step.pending = step.pending_cell = None
        if (step.inflight is True and step.reading_owned is True
                and stage.step is step and stage.step_origin is step
                and type(stage.step_cell) is tuple and len(stage.step_cell) == 2
                and stage.step_cell[0] is stage and stage.step_cell[1] is step
                and type(stage.active_read_cell) is tuple and len(stage.active_read_cell) == 2
                and stage.active_read_cell[0] is stage and stage.active_read_cell[1] is step
                and r.capture.channel._socket is s.sock and r.capture.channel._reading is True):
            r.capture.channel._reading = False
            step.inflight = step.reading_owned = False
    raise FrameError("BI1_NATIVE_TERMINAL_AUTH_READ_UNKNOWN") from None


def finish(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._actor(s.notice)
    stage = _scope(native, s)
    _require(stage.initialized and not stage.finish_attempted and stage.ordinal > 0)
    seal = _state(stage)
    _require(seal.header_done is True and len(seal.value) == seal.target)
    scope, count = stage.scope, stage.received
    stage.finish_attempted = True
    try:
        _current(native, s)
        checked = SignedCleanupAuthPrefix.finish(scope.parser)
        stage.checked_cell = (stage, checked)
        _require(type(checked) is ConsistentCommitment
                 and type(checked.canonical_json) is bytes
                 and type(checked.frame_sha256) is str and type(checked.frame_length) is int)
        value = json.loads(checked.canonical_json)
        _require(type(value) is dict and value.get("phase") == "TERMINAL"
                 and type(value.get("sequence")) is int and value["sequence"] == 2
                 and type(value.get("frame_sha256")) is str
                 and value["frame_sha256"] == checked.frame_sha256
                 and type(value.get("frame_length")) is int
                 and value["frame_length"] == checked.frame_length)
        stage.checked_values = (checked.canonical_json, checked.frame_sha256, checked.frame_length)
        stage.fact = _AuthFact(scope, checked, count, scope.seed + count)
        stage.fact_cell = (stage, stage.fact)
        stage.finish_returned = True
        _current(native, s)
        stage.complete = True
        return stage.fact
    except BaseException:
        _fail(native, s, stage)
    raise FrameError("BI1_NATIVE_TERMINAL_AUTH_FINISH_UNKNOWN") from None


def current_for_cleanup(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._cleanup_actor(s.notice)
    stage = _scope(native, s)
    try:
        _current(native, s, cleanup=True)
        _require(stage.initialized and (not stage.finish_attempted or stage.complete))
        if stage.complete:
            return stage.fact
        step = stage.step_origin
        _require(step is None or step.complete is True)
        return stage.scope.predecessor if step is None else step.fact
    except BaseException:
        _fail(native, s, stage)
    raise FrameError("BI1_NATIVE_TERMINAL_AUTH_OBSERVER_UNKNOWN") from None


def retire(native):
    cell = native._terminal_allocation
    if type(cell) is tuple and len(cell) == 2 and cell[0] is native and type(cell[1]) is _Stage:
        _fail(native, native._scope_allocation_origin[1], cell[1])
