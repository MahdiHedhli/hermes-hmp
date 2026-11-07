"""Original-reader TERMINAL/2 correlation DATA; no budget adoption, ACK or release.

Only the completed RESULT predecessor position is supported here. Matching a
claim does not qualify the producer's native closure or accept its cleanup stamp.
"""
from __future__ import annotations

import hashlib
import json
from typing import NamedTuple

from .presentation_credential_cleanup_body import _BodyDone
from .presentation_credential_cleanup_frame import _FrameDone
from .presentation_credential_frame_discard import DiscardedFrame
from .presentation_credential_phase import _EXPECTED
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError
from .presentation_remote import RemoteOperationOwner
from .presentation_terminal_claim import (
    StartedClaim,
    TerminalHandoff,
    _values,
    claim_binding,
    decode_handoff,
)

_SHA256 = hashlib.sha256


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_TERMINAL_CORRELATION_REFUSED")


class _Expected(NamedTuple):
    binding: object
    profile: str
    operation: str
    deadline: int
    challenge: str
    epoch: int
    input_sha: str
    source_sha: str
    generation: str
    domain_sha: str
    result_sha: str

    def __repr__(self):
        return "<TerminalExpected original-input-and-result-DATA redacted>"


class _Correlation(NamedTuple):
    native: object
    scope: object
    frame: object
    predecessor: object
    expected: _Expected
    handoff: TerminalHandoff

    def __repr__(self):
        return "<TerminalCorrelation DATA no-budget-adoption-or-release>"


class _Attempt:
    def __repr__(self):
        return "<TerminalCorrelationAttempt one-shot redacted>"


def _expected(native, scope, frame):
    """Derive every comparison from retained native request/context, never claim data."""
    from .presentation_credential_cleanup_terminal_frame import _scope

    _require(_scope(native, scope) is frame and frame.complete is True)
    capture = scope.idle_scope[0].reservation.capture
    write = capture.scope.write_scope
    packet, binding = write.intent.packet, write.intent.binding
    _require(type(packet) is bytes and type(write.remote) is RemoteOperationOwner)
    RemoteOperationOwner._clock_binding(write.remote)
    values = write.remote._clock_domain_values_snapshot
    _require(type(values) is tuple and len(values) == 4
             and type(values[0]) is str and type(values[1]) is str
             and type(values[2]) is bytes and len(values[2]) <= 64
             and (values[3] is None or (type(values[3]) is tuple and len(values[3]) == 2
                  and all(type(v) is int and 0 <= v < 1 << 63 for v in values[3]))))
    domain = json.dumps((values[0], values[1], values[2].hex(), values[3]),
                        separators=(",", ":"), ensure_ascii=True).encode("ascii")
    row = decode_input_v3(packet)
    rows = capture.scope.expected
    _require(type(rows) is tuple and len(rows) == len(_EXPECTED)
             and all(type(r) is tuple and len(r) == 2 and type(r[0]) is str
                     and type(r[1]) is (int if r[0] in ("sequence", "work_end_ns") else str)
                     for r in rows) and {r[0] for r in rows} == _EXPECTED)
    context = dict(rows)
    _require(row["iid"] == binding.iid and row["deadline_ns"] == context["work_end_ns"]
             and type(context["generation"]) is str)
    predecessor = frame.scope.auth.scope.predecessor
    _require(type(predecessor) in (_FrameDone, _BodyDone))
    if type(predecessor) is _FrameDone:
        _require(type(predecessor.data) is DiscardedFrame)
        result_sha = predecessor.data.payload_sha256
    else:
        result_sha = predecessor.payload_sha256
    _require(type(result_sha) is str and len(result_sha) == 64)
    input_sha, domain_sha = _SHA256(packet).hexdigest(), _SHA256(domain).hexdigest()
    _require(type(input_sha) is str and len(input_sha) == 64
             and type(domain_sha) is str and len(domain_sha) == 64)
    return _Expected(claim_binding(binding), row["profile"], row["operation"],
                     row["deadline_ns"], row["challenge"], row["epoch"],
                     input_sha, row["source_manifest_sha"],
                     context["generation"], domain_sha, result_sha)


def _match(expected, handoff):
    _require(type(expected) is _Expected and type(handoff) is TerminalHandoff)
    c = handoff.claim
    _require(type(c) is StartedClaim)
    _values(c)  # Reseal exact primitives even across a decoder return boundary.
    _require((c.binding, c.profile, c.operation_kind, c.deadline_ns, c.challenge, c.epoch,
              c.input_sha256, c.worker_source_sha256, c.installation_generation,
              c.clock_domain_sha256, c.result_sha256) == tuple(expected)
             and c.outcome == "OK" and c.exit_code == 0)


def correlate(native):
    """One original-actor correlation attempt; returns DATA only, never accepts cleanup."""
    from .presentation_credential_cleanup_read import NativeCleanupRead
    from .presentation_credential_cleanup_terminal_frame import _current_work, _scope

    scope = NativeCleanupRead._origin(native)
    from .presentation_credential_cleanup_notice import SignedReadNotice
    SignedReadNotice._actor(scope.notice)
    frame = _scope(native, scope)
    _require(native._claim_attempt is None and native._claim_attempt_origin is None
             and native._claim_attempt_cell is None and frame.complete is True)
    attempt = _Attempt.__new__(_Attempt)
    attempt.failed = attempt.complete = False
    attempt.fact = attempt.fact_cell = None
    native._claim_attempt = native._claim_attempt_origin = attempt
    native._claim_attempt_cell = (native, attempt)
    attempt_cell = native._claim_attempt_cell
    failed = False
    try:
        _current_work(native, scope)
        expected = _expected(native, scope, frame)
        done = frame.done
        _require(type(done) is _FrameDone and done.scope is frame.scope
                 and type(frame.done_cell) is tuple and len(frame.done_cell) == 2
                 and frame.done_cell[0] is frame and frame.done_cell[1] is done
                 and done.data is frame.result_origin)
        done_cell, frame_scope = frame.done_cell, frame.scope
        _require(type(done.data) is DiscardedFrame and type(done.data.terminal) is bytes)
        wire = done.data.terminal
        handoff = decode_handoff(wire)
        _match(expected, handoff)
        predecessor = frame.scope.auth.scope.predecessor
        fact = _Correlation(native, scope, frame, predecessor, expected, handoff)
        attempt.fact, attempt.fact_cell = fact, (attempt, fact)
        fact_cell = attempt.fact_cell
        _current_work(native, scope)
        checked = _expected(native, scope, frame)
        _current_work(native, scope)
        _require(checked == expected
                 and native._claim_attempt is attempt and native._claim_attempt_origin is attempt
                 and native._claim_attempt_cell is attempt_cell
                 and frame.scope is frame_scope and frame.scope_origin is frame_scope
                 and frame.done is done and frame.done_cell is done_cell
                 and done.data is frame.result_origin
                 and done.data.terminal is wire
                 and frame.scope.auth.scope.predecessor is predecessor
                 and attempt.failed is False and attempt.complete is False
                 and attempt.fact is fact and attempt.fact_cell is fact_cell)
        attempt.complete = True
        return fact
    except BaseException:
        attempt.failed = failed = True
    if failed:
        raise FrameError("BI1_NATIVE_TERMINAL_CORRELATION_UNKNOWN") from None


def _metadata(native):
    """Retained correlation joins only; no live clock or filesystem effects."""
    from .presentation_credential_cleanup_read import NativeCleanupRead
    from .presentation_credential_cleanup_terminal_frame import _scope

    scope = NativeCleanupRead._origin(native)
    attempt = native._claim_attempt_origin
    _require(type(attempt) is _Attempt and native._claim_attempt is attempt
             and type(native._claim_attempt_cell) is tuple
             and len(native._claim_attempt_cell) == 2
             and native._claim_attempt_cell[0] is native
             and native._claim_attempt_cell[1] is attempt
             and attempt.failed is False and attempt.complete is True)
    fact = attempt.fact
    _require(type(fact) is _Correlation and type(attempt.fact_cell) is tuple
             and len(attempt.fact_cell) == 2 and attempt.fact_cell[0] is attempt
             and attempt.fact_cell[1] is fact and fact.native is native and fact.scope is scope)
    frame = _scope(native, scope)
    _require(fact.frame is frame and frame.complete is True
             and type(frame.done) is _FrameDone and type(frame.done_cell) is tuple
             and len(frame.done_cell) == 2 and frame.done_cell[0] is frame
             and frame.done_cell[1] is frame.done and frame.done.scope is frame.scope
             and frame.done.data is frame.result_origin
             and type(frame.done.data) is DiscardedFrame
             and type(frame.done.data.terminal) is bytes
             and frame.scope.auth.scope.predecessor is fact.predecessor
             and type(fact.expected) is _Expected and type(fact.handoff) is TerminalHandoff)
    return fact


def current(native):
    """Original actor/current context, still DATA rather than cleanup admission."""
    from .presentation_credential_cleanup_notice import SignedReadNotice
    from .presentation_credential_cleanup_terminal_frame import _current_work
    from .presentation_terminal_claim import encode_handoff

    fact = _metadata(native)
    SignedReadNotice._actor(fact.scope.notice)
    frame = fact.frame
    done, scope, done_cell = frame.done, frame.scope, frame.done_cell
    _current_work(native, fact.scope)
    _require(_metadata(native) is fact)
    expected = _expected(native, fact.scope, frame)
    _match(expected, fact.handoff)
    wire = encode_handoff(fact.handoff.claim, fact.handoff.cleanup)
    _current_work(native, fact.scope)
    _require(_metadata(native) is fact and expected == fact.expected
             and frame.scope is scope and frame.done is done and frame.done_cell is done_cell
             and type(wire) is bytes and wire == done.data.terminal)
    return fact
