"""Frozen original signed-reader progress DATA; never cleanup IO or release permission.

Capture precedes first-cause poisoning. Original output is still withdrawn before
cleanup clock sampling. No copied image body, new reader, deadline or phase reset.
A later cooperative transition must independently qualify current ownership,
write quiescence, wait retirement and the original minimum cleanup budget.
"""
from __future__ import annotations

from typing import NamedTuple

from .presentation_broker_codec import HEADER_LIMIT
from .presentation_broker_service import SocketChannel
from .presentation_credential_begin_write import _BeginWriterScope
from .presentation_credential_codec import RECORD_LIMIT
from .presentation_credential_result_body import _HASH, NativeResultBodyOwner, _BodyScope
from .presentation_credential_result_read import NativeResultEnvelopeReceiver, _ResultReadScope
from .presentation_credential_stream import CommittedFrameDigest
from .presentation_jobs import OUTPUT_LIMIT, FrameError, RemotePhase, State, _Job
from .presentation_readiness import _HANDLE, SelectorReadiness, _WakeBinding
from .presentation_readiness import _Scope as _WaitScope
from .presentation_remote import RemoteOperationOwner
from .presentation_remote_cleanup import _FUTURE, _TASK, RemoteCleanupOwner, _TaskAllocation

_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_CLEANUP_CAPTURE_REFUSED")


class _WaitProgress(NamedTuple):
    owner: object
    scope: object
    future: object
    binding: object
    handle: object
    handle_args: object
    attempted: bool
    retired: bool
    future_done: bool

    def __repr__(self):
        return "<SignedWaitProgress original-registration-data no-retirement-credit>"


def _wait_progress(waiter, base):
    if waiter is None:
        return None
    _require(type(waiter) is SelectorReadiness)
    SelectorReadiness._guard(waiter, actor=False)  # local metadata, no selector/FD IO
    SelectorReadiness._wake_guard(waiter)
    _require(waiter._unknown is False and waiter._origin_scope.task is base.allocation.task
             and waiter._origin_scope.sock is base.sock
             and waiter._origin_scope.loop is base.loop
             and waiter._origin_scope.interest == "read"
             and not _FUTURE.cancelled(waiter._future_origin))
    binding = waiter._wake_binding_origin
    if binding is not None:
        _require(type(binding) is _WakeBinding and binding.end == base.intent.end_ns)
    done = _FUTURE.done(waiter._future_origin)
    if done:
        _require(_FUTURE.result(waiter._future_origin) is None)
    return _WaitProgress(waiter, waiter._origin_scope, waiter._future_origin, binding,
        waiter._handle_snapshot, waiter._handle_args_snapshot,
        waiter._attempted, waiter._retired, done)


def _inspect_wait(progress):
    if progress is None:
        return
    _require(type(progress) is _WaitProgress and type(progress.owner) is SelectorReadiness
             and type(progress.scope) is _WaitScope and type(progress.future) is _FUTURE
             and (progress.binding is None or type(progress.binding) is _WakeBinding)
             and (progress.handle is None or type(progress.handle) is _HANDLE)
             and (progress.handle_args is None or type(progress.handle_args) is tuple)
             and all(type(v) is bool for v in (
                 progress.attempted, progress.retired, progress.future_done)))


class _EnvelopeProgress(NamedTuple):
    consumed: int
    target: int
    values: bytes
    complete: bool
    active: bool
    completion: object
    waiter: object

    def __repr__(self):
        return "<SignedEnvelopeProgress bounded-framing no-authority>"


class _BodyProgress(NamedTuple):
    owner: object
    scope: object
    allocation: tuple
    received: int
    committed: int
    hash_value: str
    active: bool
    validated: bool
    adopted: bool
    waiter: object

    def __repr__(self):
        return "<SignedBodyProgress original-offsets no-image-copy>"


class SignedCleanupCapture(NamedTuple):
    mint: object
    gate: object
    cleanup: object
    receiver: object
    scope: object
    channel: object
    work: object
    phase: object
    envelope: _EnvelopeProgress
    body: object
    write: object

    def __repr__(self):
        return "<SignedCleanupCapture frozen-data no-transfer-or-release>"


def capture_signed_cleanup(gate, cleanup, receiver):
    """Snapshot actual retained framing before revocation, without granting IO."""
    from .presentation_cleanup_reader import CleanupReadGate

    _require(type(gate) is CleanupReadGate and type(cleanup) is RemoteCleanupOwner
             and gate._owner_origin is cleanup and cleanup._read_gate_snapshot is gate
             and cleanup._intent is True and type(receiver) is NativeResultEnvelopeReceiver)
    RemoteCleanupOwner._guard(cleanup)
    s = NativeResultEnvelopeReceiver._metadata(receiver)
    b = s.write_scope
    _require(type(b.remote) is RemoteOperationOwner
             and type(b.remote._job_origin_snapshot) is _Job)
    job = b.remote._job_origin_snapshot
    phase = job.remote_phase
    _require(b.refs[0] is cleanup and b.remote is cleanup._remote_snapshot
             and b.channel is cleanup._refs_snapshot[3] and type(b.channel) is SocketChannel
             and b.channel._credential_result_receiver is receiver
             and b.channel._credential_result_receiver_snapshot is receiver
             and b.channel._result_receiver_snapshot is None
             and b.allocation is cleanup._allocations_snapshot[1]
             and not _TASK.done(b.allocation.task) and not _TASK.cancelling(b.allocation.task)
             and b.remote._job_origin_snapshot.state is State.RUNNING
             and b.remote._job_origin_snapshot.emit_revoked is False
             and (phase is RemotePhase.GO_SENT or phase is RemotePhase.RESULT_VALIDATED)
             and receiver._initialized is True and receiver._started is True
             and receiver._failed is False and receiver._io_unknown is False
             and receiver._read_intent is False and receiver._pending is None
             and b.channel._writing is False)
    e = _EnvelopeProgress(receiver._consumed_origin, receiver._target_origin,
        receiver._buffer_values, receiver._complete, receiver._active,
        receiver._completion_origin, _wait_progress(receiver._waiter_origin, b))
    body, progress = receiver._body_owner_snapshot, None
    if body is None:
        _require(receiver._body_owner is None
                 and b.remote._job_origin_snapshot.remote_phase is RemotePhase.GO_SENT
                 and b.channel._reading is e.active
                 and e.active is (not e.complete))
    else:
        _require(type(body) is NativeResultBodyOwner and receiver._body_owner is body
                 and e.complete is True and e.active is False)
        body_scope = NativeResultBodyOwner._metadata(body)
        _require(body_scope.envelope is receiver and body_scope.envelope_scope is s
                 and body._initialized is True and body._attempted is True
                 and body._read_intent is False and body._commit_intent is False
                 and body._pending is None and body._received == body._committed
                 and b.channel._reading is body._active)
        if body._active:
            _require(body._validated is False and body._finish_attempted is False
                     and body_scope.buffer._done is False
                     and len(body_scope.accumulator) == body._committed)
            CommittedFrameDigest._guard(body._stream_origin)
        else:
            _require(body._validated is True and body._finish_attempted is True
                     and body_scope.buffer._done is True and not body_scope.accumulator)
            NativeResultBodyOwner._candidate_metadata(body)
            if body._adopted:
                NativeResultBodyOwner._adoption_metadata(body)
        _require(type(body._stream_origin._received) is int
                 and body._stream_origin._received == body._committed_snapshot
                 and body._stream_origin._received_snapshot is body._stream_origin._received)
        progress = _BodyProgress(body, body_scope, body._initialization_origin,
            body._received_snapshot, body._committed_snapshot,
            body._hash_origin.hexdigest(), body._active, body._validated,
            body._adopted, _wait_progress(body._waiter_origin, b))
    result = SignedCleanupCapture(_MINT, gate, cleanup, receiver, s, b.channel,
        b.allocation, phase, e, progress,
        cleanup._write_fact_snapshot)
    inspect_signed_cleanup(result, gate, cleanup)
    return result


def inspect_signed_cleanup(capture, gate, cleanup):
    """Frozen data shape/origin only; no live currentness, transfer, IO or credit."""
    from .presentation_cleanup_reader import CleanupReadGate

    _require(type(gate) is CleanupReadGate
             and type(capture) is SignedCleanupCapture and capture.mint is _MINT
             and capture.gate is gate and capture.cleanup is cleanup
             and type(cleanup) is RemoteCleanupOwner
             and type(capture.receiver) is NativeResultEnvelopeReceiver
             and type(capture.scope) is _ResultReadScope
             and type(capture.channel) is SocketChannel
             and type(capture.work) is _TaskAllocation and type(capture.work.task) is _TASK
             and type(capture.phase) is RemotePhase
             and (capture.phase is RemotePhase.GO_SENT
                  or capture.phase is RemotePhase.RESULT_VALIDATED)
             and type(capture.envelope) is _EnvelopeProgress
             and type(capture.scope.write_scope) is _BeginWriterScope
             and capture.scope.write_scope.channel is capture.channel
             and capture.scope.write_scope.allocation is capture.work)
    e = capture.envelope
    _require(type(e.consumed) is int and type(e.target) is int
             and type(e.values) is bytes and type(e.complete) is bool and type(e.active) is bool
             and len(e.values) == e.consumed
             and 0 <= e.consumed <= e.target <= RECORD_LIMIT + 8 + HEADER_LIMIT)
    _inspect_wait(e.waiter)
    p = capture.body
    if p is not None:
        _require(type(p) is _BodyProgress and type(p.owner) is NativeResultBodyOwner
                 and type(p.scope) is _BodyScope and type(p.allocation) is tuple
                 and len(p.allocation) == 3 and p.allocation[0] is p.scope
                 and type(p.allocation[1]) is CommittedFrameDigest
                 and type(p.allocation[2]) is _HASH
                 and p.scope.envelope is capture.receiver
                 and p.scope.envelope_scope is capture.scope
                 and type(p.received) is int and type(p.committed) is int
                 and 0 <= p.received == p.committed <= OUTPUT_LIMIT
                 and type(p.hash_value) is str and len(p.hash_value) == 64
                 and all(type(v) is bool for v in (p.active, p.validated, p.adopted)))
        _inspect_wait(p.waiter)
    return capture
