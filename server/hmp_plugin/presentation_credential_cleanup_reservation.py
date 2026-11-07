"""Signed original-wait reservation preflight; NOT an enabled cooperative route.

The existing request still returns False and performs ordinary Task cancellation.
A later reviewed read-ready/continuation contract must consume this preflight;
this record never grants read/CANCEL/ACK/native release or publication authority.
"""
from __future__ import annotations

from typing import NamedTuple

from .presentation_cancel_budget import CancellationBudget
from .presentation_credential_cleanup_capture import (
    SignedCleanupCapture,
    _WaitProgress,
    inspect_signed_cleanup,
)
from .presentation_credential_result_body import NativeResultBodyOwner
from .presentation_credential_result_read import NativeResultEnvelopeReceiver
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError, RemotePhase, State, _Job
from .presentation_output_v2 import BoundedResultBufferV2
from .presentation_readiness import _HANDLE, SelectorReadiness, _WakeBinding
from .presentation_readiness import _Scope as _WaitScope
from .presentation_remote_cleanup import (
    _FUTURE,
    _QUIESCENCE_MINT,
    _TASK,
    RemoteCleanupOwner,
    _WriteQuiescence,
)

_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_READ_RESERVATION_REFUSED")


class SignedReadReservation(NamedTuple):
    mint: object
    gate: object
    capture: SignedCleanupCapture
    wait: _WaitProgress
    cause: object
    write: object
    budget: object
    end: int

    def __repr__(self):
        return "<SignedReadReservation disabled-preflight no-IO-authority>"


def inspect_signed_reservation(reservation, gate):
    """Retained shape/origin only, never live registration/budget permission."""
    _require(type(reservation) is SignedReadReservation and reservation.mint is _MINT
             and reservation.gate is gate and type(reservation.capture) is SignedCleanupCapture
             and type(reservation.wait) is _WaitProgress
             and type(reservation.cause) is _FUTURE and type(reservation.write) is _WriteQuiescence
             and type(reservation.budget) is CancellationBudget
             and type(reservation.end) is int and reservation.end > 0)
    c = reservation.capture
    inspect_signed_cleanup(c, gate, c.cleanup)
    _require(c.write is reservation.write and c.phase is RemotePhase.GO_SENT
             and reservation.write.mint is _QUIESCENCE_MINT
             and reservation.write.owner is c.cleanup and reservation.write.work is c.work
             and reservation.write.channel is c.channel
             and reservation.write.budget is reservation.budget
             and (c.envelope.waiter if c.body is None else c.body.waiter) is reservation.wait)
    return reservation


def _current(reservation, gate):
    from .presentation_cleanup_reader import CleanupReadGate

    inspect_signed_reservation(reservation, gate)
    RemoteCleanupOwner._guard(reservation.capture.cleanup)
    CleanupReadGate.guard(gate)
    c, p = reservation.capture, reservation.wait
    o, w, b = c.cleanup, p.owner, c.scope.write_scope
    _require(gate._signed_capture is c and gate._signed_capture_origin is c
             and type(p.owner) is SelectorReadiness and type(p.scope) is _WaitScope
             and type(p.future) is _FUTURE and type(p.binding) is _WakeBinding
             and type(p.handle) is _HANDLE and type(p.handle_args) is tuple
             and p.attempted is True and p.retired is False and p.future_done is False
             and c.work is o._allocations_snapshot[1]
             and not _TASK.done(c.work.task) and _TASK.cancelling(c.work.task) == 0
             and o._intent is True and o._unknown is False
             and o._work_joined is False and o._cancel_write_attempted is False
             and o._write_fact is reservation.write and o._write_fact_snapshot is reservation.write
             and o._write_fact_consumed is False
             and o._refs_snapshot[8] is reservation.budget
             and gate._capture_cause is reservation.cause
             and o._barriers_snapshot.cause is reservation.cause
             and _FUTURE.get_loop(reservation.cause) is b.loop
             and not _FUTURE.done(reservation.cause) and not _FUTURE.cancelled(reservation.cause)
             and p.scope.task is c.work.task and p.scope.sock is b.sock
             and p.scope.loop is b.loop and p.scope.interest == "read"
             and p.binding.scope is p.scope and p.binding.future is reservation.cause
             and p.binding.end is b.intent.end_ns
             and w._origin_scope is p.scope and w._scope_snapshot is p.scope
             and w._future is p.future and w._future_origin is p.future
             and w._future_snapshot is p.future and not _FUTURE.done(p.future)
             and w._wake_binding is p.binding and w._wake_binding_origin is p.binding
             and w._handle is p.handle and w._handle_snapshot is p.handle
             and w._handle_args is p.handle_args and w._handle_args_snapshot is p.handle_args
             and w._attempted is True and w._retired is False and w._unknown is False
             and c.channel._reading is True and c.channel._writing is False
             and c.channel._work_write_retired is True
             and b.refs[0] is o and b.channel is c.channel
             and b.remote is o._remote_snapshot and b.remote._failed is True
             and type(b.remote._job_origin_snapshot) is _Job
             and b.remote._job_origin_snapshot.state is State.UNKNOWN
             and b.remote._job_origin_snapshot.remote_phase is RemotePhase.UNKNOWN
             and b.remote._job_origin_snapshot.emit_revoked is True
             and b.remote._job_origin_snapshot.result is None
             and b.remote._job_origin_snapshot.remote_result_token is None)
    _require(NativeResultEnvelopeReceiver._metadata(c.receiver) is c.scope)
    if c.body is None:
        _require(c.envelope.active is True and c.envelope.complete is False
                 and c.receiver._active is True and c.receiver._failed is False
                 and c.receiver._io_unknown is False and c.receiver._pending is None
                 and c.receiver._read_intent is False
                 and c.receiver._waiter is w and c.receiver._waiter_origin is w
                 and c.receiver._buffer_values == c.envelope.values
                 and c.receiver._consumed is c.envelope.consumed
                 and c.receiver._target is c.envelope.target)
    else:
        body, held = c.body.owner, c.body
        _require(type(body) is NativeResultBodyOwner
                 and body._scope is held.scope and body._scope_origin is held.scope
                 and c.receiver._body_owner is body and c.receiver._body_owner_snapshot is body
                 and held.scope.envelope is c.receiver and held.scope.envelope_scope is c.scope
                 and body._retired is True
                 and held.active is True and held.validated is False and held.adopted is False
                 and body._active is True and body._failed is False and body._io_unknown is False
                 and body._pending is None and body._pending_snapshot is None
                 and body._read_intent is False
                 and body._commit_intent is False
                 and body._waiter is w and body._waiter_origin is w
                 and body._received is held.received and body._received_snapshot is held.received
                 and body._committed is held.committed
                 and body._committed_snapshot is held.committed
                 and body._initialization_origin is held.allocation
                 and body._initialization is held.allocation
                 and body._stream is held.allocation[1]
                 and body._stream_origin is held.allocation[1]
                 and body._stream_origin._received is held.committed
                 and body._stream_origin._received_snapshot is held.committed
                 and body._hash is held.allocation[2] and body._hash_origin is held.allocation[2]
                 and body._hash_origin.hexdigest() == held.hash_value
                 and body._candidate_snapshot is None and body._candidate is None
                 and held.scope.job is b.remote._job_origin_snapshot
                 and type(held.scope.custody) is tuple and len(held.scope.custody) == 3
                 and held.scope.custody is body._wipe_custody_origin
                 and held.scope.custody is b.remote._output_custody_snapshot
                 and held.scope.custody[0] is held.scope.job
                 and held.scope.custody[1] is held.scope.buffer
                 and held.scope.custody[2] is held.scope.accumulator
                 and held.scope.job.output_buffer is held.scope.buffer
                 and held.scope.job.remote_output_origin is held.scope.buffer
                 and type(held.scope.buffer) is BoundedResultBufferV2
                 and type(held.scope.accumulator) is bytearray
                 and held.scope.buffer._buffer is held.scope.accumulator
                 and held.scope.buffer._done is True and not held.scope.accumulator)
        # Retained digest DATA only; ordinary live body metadata correctly refuses UNKNOWN.
        from .presentation_credential_stream import CommittedFrameDigest
        CommittedFrameDigest._guard(body._stream_origin)
    original, _, end, failed = CancellationBudget.inspect(reservation.budget)
    _require(type(original) is int and original == b.intent.end_ns
             and type(end) is int and end <= reservation.end and failed is False)
    RemoteCleanupOwner._quiescence_binding(o)
    return reservation


def prepare_signed_reservation(gate):
    """One bounded preflight before cause completion; caller keeps route disabled."""
    from .presentation_cleanup_reader import CleanupReadGate

    _require(type(gate) is CleanupReadGate)
    CleanupReadGate.guard(gate)
    c = gate._signed_capture_origin
    _require(type(c) is SignedCleanupCapture)
    p = c.envelope.waiter if c.body is None else c.body.waiter
    _require(type(p) is _WaitProgress)
    o = c.cleanup
    _, _, end, failed = CancellationBudget.inspect(o._refs_snapshot[8])
    _require(type(end) is int and failed is False)
    r = SignedReadReservation(_MINT, gate, c, p, gate._capture_cause, c.write,
                              o._refs_snapshot[8], end)
    _current(r, gate)
    # Actual selector membership, current role and remaining ORIGINAL cleanup time.
    SelectorReadiness._native(p.owner, actor=False)
    handle, _ = SelectorReadiness._slots(p.owner)
    _require(handle is p.handle)
    SelectorReadiness._owned(p.owner, p.handle)
    _require(NativePhaseWorkOwner._retained_material(c.scope.write_scope.producer)[0]
             is o._remote_snapshot)
    _require(RemoteCleanupOwner._remaining(o) > 0)
    _current(r, gate)
    SelectorReadiness._native(p.owner, actor=False)
    handle, _ = SelectorReadiness._slots(p.owner)
    _require(handle is p.handle)
    SelectorReadiness._owned(p.owner, p.handle)
    _require(NativePhaseWorkOwner._retained_material(c.scope.write_scope.producer)[0]
             is o._remote_snapshot)
    _current(r, gate)
    return r
