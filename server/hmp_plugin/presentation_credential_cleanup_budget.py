"""One-shot signed cleanup-stamp min publication on the original native budget.

No new time allowance, reader, registration, CANCEL, ACK or native release. An
uncertain publication is never replayed or restored to its previous deadline.
"""
from __future__ import annotations

from typing import NamedTuple

from .presentation_broker_service import SocketChannel
from .presentation_cancel_budget import CancellationBudget, CancellationWindow
from .presentation_cleanup_reader import CleanupReadGate
from .presentation_credential_cleanup_claim import _metadata, current
from .presentation_credential_cleanup_notice import SignedReadNotice
from .presentation_credential_cleanup_reservation import SignedReadReservation
from .presentation_jobs import FrameError
from .presentation_remote_cleanup import RemoteCleanupOwner
from .presentation_terminal_claim import CleanupStamp

_INHERIT = CancellationBudget.inherit


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_TERMINAL_BUDGET_REFUSED")


class _Publication:
    def __repr__(self):
        return "<SignedBudgetPublication one-shot redacted>"


class _BudgetFact(NamedTuple):
    correlation: object
    budget: CancellationBudget
    previous_end: int
    effective_end: int
    stamp: CleanupStamp | None

    def __repr__(self):
        return "<SignedBudgetFact min-only no-ACK-or-native-release>"


class _Held(NamedTuple):
    scope: object
    reservation: SignedReadReservation
    cleanup: RemoteCleanupOwner
    gate: CleanupReadGate
    channel: SocketChannel
    refs: tuple

    def __repr__(self):
        return "<SignedBudgetHeld original-roots redacted>"


def _hold(correlation, budget):
    scope = correlation.scope
    reservation = scope.idle_scope[0].reservation
    _require(type(reservation) is SignedReadReservation)
    gate, cleanup = reservation.gate, reservation.capture.cleanup
    channel = reservation.capture.channel
    _require(type(cleanup) is RemoteCleanupOwner and type(gate) is CleanupReadGate
             and type(channel) is SocketChannel and type(cleanup._refs_snapshot) is tuple
             and len(cleanup._refs_snapshot) == 12 and cleanup._refs_snapshot[8] is budget)
    return _Held(scope, reservation, cleanup, gate, channel, cleanup._refs_snapshot)


def _idle(correlation, budget, held):
    _require(type(held) is _Held and correlation.scope is held.scope
             and type(held.cleanup) is RemoteCleanupOwner
             and type(held.gate) is CleanupReadGate and type(held.channel) is SocketChannel
             and type(held.refs) is tuple and len(held.refs) == 12
             and held.refs[8] is budget and held.refs[3] is held.channel
             and held.cleanup._refs is held.refs and held.cleanup._refs_snapshot is held.refs
             and held.gate._refs is held.refs)
    RemoteCleanupOwner._guard(held.cleanup)
    CleanupReadGate.guard(held.gate)
    _require(held.reservation.budget is budget and type(budget) is CancellationBudget
             and held.reservation.gate is held.gate
             and held.reservation.capture.cleanup is held.cleanup
             and held.reservation.capture.channel is held.channel
             and held.cleanup._refs is held.refs and held.cleanup._refs_snapshot is held.refs
             and held.gate._refs is held.refs
             and held.gate._fact is None and held.gate._fact_origin is None
             and held.gate._changing is False and held.gate._change_active is False
             and held.gate._waiter is None and held.gate._pending is None
             and held.channel._reading is False and held.channel._writing is False)
    return held.cleanup


def inherit(native):
    """Use only the actual correlated handoff; caller cannot supply a window."""
    from .presentation_credential_cleanup_read import NativeCleanupRead
    _require(type(native) is NativeCleanupRead and native._budget_publication is None
             and native._budget_publication_origin is None
             and native._budget_publication_cell is None)
    correlation = _metadata(native)
    SignedReadNotice._actor(correlation.scope.notice)
    step = _Publication.__new__(_Publication)
    step.attempted = step.returned = step.complete = step.failed = False
    step.fact = step.fact_cell = None
    native._budget_publication = native._budget_publication_origin = step
    native._budget_publication_cell = (native, step)
    cell = native._budget_publication_cell
    budget = correlation.scope.idle_scope[3]
    failed = False
    try:
        _require(current(native) is correlation)
        held = _hold(correlation, budget)
        cleanup = _idle(correlation, budget, held)
        work_end, now, old_end, broken = CancellationBudget.inspect(budget)
        _require(type(now) is int and type(old_end) is int and now < old_end
                 and work_end == correlation.expected.deadline and broken is False)
        stamp = correlation.handoff.cleanup
        _require(stamp is None or type(stamp) is CleanupStamp)
        end = old_end
        if stamp is not None:
            window = CancellationWindow(stamp.start_ns, stamp.end_ns)
            _require(window.start_ns <= now and window.start_ns <= work_end)
            end = min(old_end, window.end_ns)
            step.attempted = True  # uncertain arithmetic publication may never be repeated
            _INHERIT(budget, window, now)
            step.returned = True
        work_after, last_after, end_after, broken = CancellationBudget.inspect(budget)
        _require(work_after == work_end and last_after == now and end_after == end
                 and broken is False and _idle(correlation, budget, held) is cleanup)
        _require(current(native) is correlation)
        _, final_now, final_end, broken = CancellationBudget.inspect(budget)
        _require(type(final_now) is int and final_now >= now and final_now < end
                 and final_end == end and broken is False
                 and _metadata(native) is correlation
                 and _idle(correlation, budget, held) is cleanup
                 and native._budget_publication is step
                 and native._budget_publication_origin is step
                 and native._budget_publication_cell is cell
                 and step.failed is False and step.complete is False)
        fact = _BudgetFact(correlation, budget, old_end, end, stamp)
        _require(type(fact) is _BudgetFact and fact.correlation is correlation
                 and fact.budget is budget and type(fact.previous_end) is int
                 and fact.previous_end == old_end and type(fact.effective_end) is int
                 and fact.effective_end == end and fact.stamp is stamp)
        step.fact, step.fact_cell = fact, (step, fact)
        step.complete = True
        return fact
    except BaseException:
        step.failed = failed = True
        # Preserve any real min publication; refuse release rather than restore or retry.
        if type(budget) is CancellationBudget:
            CancellationBudget.refuse(budget)
    if failed:
        raise FrameError("BI1_SIGNED_TERMINAL_BUDGET_UNKNOWN") from None
