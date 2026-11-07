"""Finish the SAME captured partial-body digest. Consistency DATA only.

No new reader, image accumulator, terminal acceptance, ACK or release authority.
"""
from __future__ import annotations

from typing import NamedTuple

from .presentation_credential_cleanup_notice import SignedReadNotice
from .presentation_credential_stream import (
    _HASH_TYPE,
    CommittedFrameDigest,
    ConsistentFrameDigest,
    SignedResultDiscard,
)
from .presentation_jobs import FrameError

_HASH_HEX = _HASH_TYPE.hexdigest


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_BODY_FINISH_REFUSED")


class _FinishScope(NamedTuple):
    native: object
    read_scope: object
    before: object
    progress: object
    step: object
    ledger: object
    receipt: object
    count: int
    total: int
    claim: object
    claim_values: tuple
    context: tuple
    body_length: int
    header_length: int
    auth_end: int

    def __repr__(self):
        return "<BodyFinishScope original-digest payload-redacted>"


class _Finish:
    def __repr__(self):
        return "<BodyFinish original-digest one-shot>"


class _BodyDone(NamedTuple):
    scope: _FinishScope
    digest: ConsistentFrameDigest
    count: int
    total_received: int

    def __repr__(self):
        return "<BodyDone consistency-only no-terminal-or-release>"


def _scope(native, read_scope, before):
    from .presentation_credential_cleanup_read import _ParserSeal
    from .presentation_credential_phase import ConsistentCommitment

    finish = native._body_finish_origin
    _require(type(finish) is _Finish and native._body_finish is finish
             and type(native._body_finish_allocation) is tuple
             and len(native._body_finish_allocation) == 2
             and native._body_finish_allocation[0] is native
             and native._body_finish_allocation[1] is finish
             and type(finish.scope) is _FinishScope and finish.scope is finish.scope_origin
             and type(finish.scope_cell) is tuple and len(finish.scope_cell) == 2
             and finish.scope_cell[0] is finish and finish.scope_cell[1] is finish.scope)
    s = finish.scope
    _require(s.native is native and s.read_scope is read_scope
             and type(s.before) is _ParserSeal and s.before is before
             and s.progress is native._progress_origin and s.step is native._next_read_origin
             and s.ledger is native._ledger_origin
             and all(type(v) is int for v in (s.count, s.total, s.body_length,
                 s.header_length, s.auth_end)) and 0 < s.count <= s.total
             and type(s.claim) is ConsistentCommitment
             and type(s.claim_values) is tuple and len(s.claim_values) == 3
             and type(s.claim_values[0]) is bytes and type(s.claim_values[1]) is str
             and type(s.claim_values[2]) is int
             and type(s.context) is tuple and len(s.context) == 2
             and all(type(v) is int for v in s.context)
             and all(type(v) is bool for v in (
                 finish.attempted, finish.returned, finish.complete, finish.failed))
             and finish.attempted is True and finish.failed is False)
    parser, stream = before.parser, before.stream
    capture = read_scope.idle_scope[0].reservation.capture
    body = capture.body
    _require(body is not None and type(parser) is SignedResultDiscard
             and type(stream) is CommittedFrameDigest and type(before.hasher) is _HASH_TYPE
             and before.parser is read_scope.idle_scope[1]
             and body.allocation[1] is stream
             and type(body.allocation[2]) is _HASH_TYPE
             and body.allocation[2] is body.owner._hash_origin
             and before.hasher is s.progress.before.hasher
             and body.owner._initialization_origin is body.allocation
             and body.owner._stream is stream and body.owner._stream_origin is stream
)
    _require(type(body.owner._committed) is int and body.owner._committed == body.committed
             and type(before.received) is int and before.received == s.body_length
             and type(before.buffer) is bytearray and type(before.value) is bytes
             and type(before.target) is int and before.target == len(before.value)
)
    _require(before.binding is capture.scope.write_scope.intent.binding
             and parser._binding is before.binding and parser._binding_origin is before.binding
             and parser._stream is stream and parser._stream_origin is stream
             and parser._buffer is before.buffer and parser._buffer_origin is before.buffer
             and type(parser._stage) is str
             and parser._stage is parser._stage_origin and parser._stage == "body"
             and parser._target is before.target and parser._target_origin is before.target
             and type(parser._auth_end) is int and parser._auth_end == s.auth_end
             and parser._auth_end_origin is parser._auth_end
             and parser._pins is before.pins and parser._pins_origin is before.pins
             and parser._expected is before.expected and parser._expected_origin is before.expected
             and parser._context is before.context
             and not any(k in vars(parser) for k in ("feed", "finish", "needed", "_guard"))
             and not any(k in vars(stream) for k in (
                 "feed", "finish", "remaining", "_guard"))
)
    _require(stream._hasher is before.hasher and stream._hasher_origin is before.hasher
             and stream._commitment is s.claim and stream._commitment_origin is s.claim
             and stream._commitment_values is s.claim_values
             and stream._context is s.context
             and type(stream._body_length) is int and stream._body_length == s.body_length
             and type(stream._header_length) is int and stream._header_length == s.header_length
             and stream._binding is before.binding and stream._binding_origin is before.binding
)
    _require(type(s.claim.canonical_json) is bytes
             and type(s.claim.frame_sha256) is str and type(s.claim.frame_length) is int
             and (s.claim.canonical_json, s.claim.frame_sha256, s.claim.frame_length)
                 == s.claim_values)
    if s.step is None:
        _require(s.receipt is s.progress and s.count == s.total == s.receipt.count)
    else:
        _require(s.receipt is s.step.fact and s.count == s.receipt.count
                 and s.total == s.receipt.total_received)
    return finish


def metadata(native, read_scope, before):
    finish = native._body_finish_origin
    if finish is None:
        _require(native._body_finish is None and native._body_finish_allocation is None)
        return None
    finish = _scope(native, read_scope, before)
    if not finish.returned:
        _require(finish.complete is False and finish.result is None and finish.result_cell is None
                 and finish.fact is None and finish.fact_cell is None)
        return None
    s, result = finish.scope, finish.result
    stream, parser = before.stream, before.parser
    _require(type(result) is ConsistentFrameDigest
             and type(finish.result_cell) is tuple and len(finish.result_cell) == 2
             and finish.result_cell[0] is finish and finish.result_cell[1] is result
             and type(result.frame_sha256) is str and type(result.frame_length) is int
             and result.frame_sha256 == s.claim_values[1]
             and result.frame_length == s.claim_values[2]
             and parser._finished is True and parser._failed is False
             and stream._finished is True and stream._failed is False
             and type(stream._received) is int and stream._received == before.received
             and stream._received_snapshot is stream._received
             and not before.buffer and type(before.digest) is str)
    # Fixed C hash access, followed by fresh pure identity/result joins. No
    # unfinished-parser guard after the real finish clears its owned buffer.
    values = (result.frame_sha256, result.frame_length)
    result_cell = finish.result_cell
    received = stream._received
    digest = _HASH_HEX(before.hasher)
    _require(_scope(native, read_scope, before) is finish
             and finish.result is result
             and type(finish.result_cell) is tuple and finish.result_cell is result_cell
             and len(finish.result_cell) == 2
             and finish.result_cell[0] is finish and finish.result_cell[1] is result
             and type(result.frame_sha256) is str and result.frame_sha256 is values[0]
             and type(result.frame_length) is int and result.frame_length is values[1]
             and parser._finished is True and parser._failed is False
             and stream._finished is True and stream._failed is False
             and type(stream._received) is int and stream._received is received
             and stream._received_snapshot is received
             and stream._received == before.received and not before.buffer
             and type(digest) is str and digest == before.digest == values[0])
    fact = finish.fact
    _require(type(fact) is _BodyDone and fact.scope is s and fact.digest is result
             and type(finish.fact_cell) is tuple and len(finish.fact_cell) == 2
             and finish.fact_cell[0] is finish and finish.fact_cell[1] is fact
             and type(fact.count) is int and type(fact.total_received) is int
             and fact.count == s.count and fact.total_received == s.total)
    return fact


def finish_body(native):
    from .presentation_credential_cleanup_read import (
        _MINT,
        NativeCleanupRead,
        _ConsumedReceipt,
        _NextReceipt,
        _ParserSeal,
    )

    read_scope = NativeCleanupRead._origin(native)
    r = SignedReadNotice._actor(read_scope.notice)
    _require(native._body_finish is None and native._body_finish_origin is None
             and native._body_finish_allocation is None and native._consume_complete is True
             and native._auth_allocation_origin is None and native._frame_allocation_origin is None
             and native._failed is False and native._unknown is False)
    progress = native._progress_origin
    cell = native._progress_allocation_origin
    _require(type(progress) is _ConsumedReceipt and native._progress is progress
             and progress.mint is _MINT and progress.owner is native
             and progress.scope is read_scope
             and type(cell) is tuple and len(cell) == 2
             and cell[0] is native and cell[1] is progress
             and type(progress.after) is _ParserSeal)
    before = NativeCleanupRead._continuation_seal(native, read_scope, progress.after)
    _require(type(before) is _ParserSeal)
    parser = before.parser
    _require(type(parser) is SignedResultDiscard and parser is read_scope.idle_scope[1]
             and type(before.stream) is CommittedFrameDigest
             and type(before.received) is int and type(before.stream._body_length) is int
             and before.received == before.stream._body_length)
    step = native._next_read_origin
    receipt = progress if step is None else step.fact
    _require(type(receipt) is (_ConsumedReceipt if step is None else _NextReceipt))
    count, total = receipt.count, receipt.count if step is None else receipt.total_received
    stream = before.stream
    finish = _Finish.__new__(_Finish)
    finish.scope = finish.scope_origin = _FinishScope(native, read_scope, before,
        progress, step, native._ledger_origin, receipt, count, total, stream._commitment_origin,
        stream._commitment_values, stream._context, stream._body_length,
        stream._header_length, parser._auth_end_origin)
    finish.scope_cell = (finish, finish.scope)
    finish.attempted = True
    finish.returned = finish.complete = finish.failed = False
    finish.result = finish.result_cell = finish.fact = finish.fact_cell = None
    native._body_finish = native._body_finish_origin = finish
    native._body_finish_allocation = (native, finish)
    failed = False
    result = None
    try:
        NativeCleanupRead._progress_work_current(native)
        _require(SignedResultDiscard.needed.fget(parser) == 0)
        result = SignedResultDiscard.finish(parser)
        finish.result = result
        finish.result_cell = (finish, result)
        finish.returned = True
        finish.fact = _BodyDone(finish.scope, result, count, total)
        finish.fact_cell = (finish, finish.fact)
        NativeCleanupRead._progress_work_current(native)
        finish.complete = True
        _require(metadata(native, read_scope, before) is finish.fact)
        return finish.fact
    except BaseException:
        failed = finish.failed = native._failed = native._unknown = True
        read_scope.notice._failed = read_scope.notice._unknown = True
        r.capture.cleanup._unknown = True
        before.buffer.clear()
        NativeCleanupRead._drop_pending(native)
    finally:
        result = None
    if failed:
        raise FrameError("BI1_NATIVE_BODY_FINISH_UNKNOWN") from None
