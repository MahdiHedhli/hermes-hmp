"""Nonrenewing cancellation arithmetic, never clock-domain or closure proof.

Callers must qualify a common native clock and bind the operation before adopting
wire values. The current v1 service does neither and cannot use this as admission.
"""

from __future__ import annotations

import struct
import threading
from dataclasses import dataclass
from typing import NamedTuple

from .presentation_jobs import FrameError

CLEANUP_NS = 250_000_000
MAX_NS = (1 << 63) - 1


def _refuse() -> None:
    raise FrameError("BI1_CANCELLATION_BUDGET_REFUSED")


def _ns(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_NS:
        _refuse()


@dataclass(frozen=True)
class CancellationWindow:
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        _ns(self.start_ns)
        _ns(self.end_ns)
        if self.end_ns != self.start_ns + CLEANUP_NS:
            _refuse()

    def encode(self) -> bytes:
        self.__post_init__()
        return struct.pack(">QQ", self.start_ns, self.end_ns)

    @classmethod
    def decode(cls, body: bytes) -> CancellationWindow:
        if type(body) is not bytes or len(body) != 16:
            _refuse()
        return cls(*struct.unpack(">QQ", body))


class BudgetBusyError(FrameError):
    """A read raced publication; no state/provenance failure is established."""


class _BudgetState(NamedTuple):
    mint: object
    generation: int
    last: int | None
    end: int | None


class CancellationBudget:
    """One event-loop owner; immutable snapshots permit policy-thread reads.

    Exact samples are arithmetic, not clock attestation. All mutations stay on
    the creating thread. Minted generations prevent torn or replaced snapshots.
    Failure is sticky; diagnostic deadlines are never authority or drain proof.
    """

    __slots__ = (
        "_generation", "_integrity_lost", "_mint", "_owner_thread", "_publishing", "_state",
        "_state_snapshot",
        "_work_end_ns", "_work_end_snapshot",
    )

    def __init__(self, work_end_ns: int):
        _ns(work_end_ns)
        if work_end_ns == 0 or work_end_ns > MAX_NS - CLEANUP_NS:
            _refuse()
        self._work_end_ns = self._work_end_snapshot = work_end_ns
        self._mint = object()
        self._generation = 0
        self._publishing = False
        self._state = self._state_snapshot = _BudgetState(self._mint, 0, None, None)
        self._owner_thread = threading.get_ident()
        self._integrity_lost = False

    def inspect(self) -> tuple[int, int | None, int | None, bool]:
        """Consistent minted generation; racing readers refuse without poisoning."""
        try:
            work_end = self._work_end_ns
            _ns(work_end)
            if (work_end is not self._work_end_snapshot
                    or not 0 < work_end <= MAX_NS - CLEANUP_NS
                    or type(self._owner_thread) is not int or type(self._mint) is not object
                    or type(self._integrity_lost) is not bool):
                _refuse()
            for _ in range(3):
                if type(self._publishing) is not bool:
                    _refuse()
                if self._publishing:
                    raise BudgetBusyError("BI1_CANCELLATION_BUDGET_BUSY")
                state, snapshot, generation = self._state, self._state_snapshot, self._generation
                valid = (type(state) is _BudgetState and type(generation) is int
                         and state is snapshot
                         and 0 <= generation < 1 << 63 and state.mint is self._mint
                         and type(state.generation) is int and state.generation == generation
                         and (state.last is None or type(state.last) is int)
                         and (state.end is None or type(state.end) is int))
                if (self._publishing is not False or self._state is not state
                        or self._state_snapshot is not snapshot
                        or self._generation is not generation):
                    continue
                if not valid:
                    _refuse()
                last, end = state.last, state.end
                if last is not None:
                    _ns(last)
                if end is not None:
                    _ns(end)
                    if not CLEANUP_NS <= end <= work_end + CLEANUP_NS:
                        _refuse()
                return work_end, last, end, self._integrity_lost is not False
            raise BudgetBusyError("BI1_CANCELLATION_BUDGET_BUSY")
        except BudgetBusyError:
            raise
        except BaseException:
            self._integrity_lost = True
            raise FrameError("BI1_CANCELLATION_BUDGET_REFUSED") from None

    def refuse(self) -> None:
        """Only an irreversible failure latch; never a new time allowance."""
        self._integrity_lost = True

    def _publish(self, now_ns: int, end_ns: int) -> None:
        if self._publishing is not False or type(self._generation) is not int:
            self._integrity_lost = True
            _refuse()
        self._publishing = True
        try:
            generation = self._generation + 1
            if generation >= 1 << 63:
                _refuse()
            state = _BudgetState(self._mint, generation, now_ns, end_ns)
            self._generation = generation
            self._state = state
            self._state_snapshot = state
        except BaseException:
            self._integrity_lost = True
            raise FrameError("BI1_CANCELLATION_BUDGET_REFUSED") from None
        finally:
            self._publishing = False

    @property
    def _last_ns(self):
        return CancellationBudget.inspect(self)[1]

    @property
    def _end_ns(self):
        return CancellationBudget.inspect(self)[2]

    @property
    def _failed(self):
        return CancellationBudget.inspect(self)[3]

    def _sample(self, now_ns: int) -> tuple[int, int | None]:
        try:
            work_end, last, end, failed = CancellationBudget.inspect(self)
            owner = self._owner_thread
            if type(owner) is not int or threading.get_ident() != owner or failed:
                _refuse()
            _ns(now_ns)
            if last is not None and now_ns < last:
                _refuse()
            return work_end, end
        except BaseException:
            self._integrity_lost = True
            raise FrameError("BI1_CANCELLATION_BUDGET_REFUSED") from None

    def local(self, now_ns: int) -> CancellationWindow:
        """EOF, timeout and revocation shorten the same original first cause."""
        work_end, old_end = CancellationBudget._sample(self, now_ns)
        end = min(now_ns, work_end) + CLEANUP_NS
        if old_end is not None:
            end = min(old_end, end)
        CancellationBudget._publish(self, now_ns, end)
        return CancellationWindow(end - CLEANUP_NS, end)

    def inherit(self, window: CancellationWindow, now_ns: int) -> None:
        work_end, old_end = CancellationBudget._sample(self, now_ns)
        try:
            if type(window) is not CancellationWindow:
                _refuse()
            CancellationWindow.__post_init__(window)
            if window.start_ns > now_ns or window.start_ns > work_end:
                _refuse()
            end = window.end_ns if old_end is None else min(old_end, window.end_ns)
            CancellationBudget._publish(self, now_ns, end)
        except BaseException:
            self._integrity_lost = True
            raise FrameError("BI1_CANCELLATION_BUDGET_REFUSED") from None

    def remaining_ns(self, now_ns: int) -> int:
        _, end = CancellationBudget._sample(self, now_ns)
        if end is None:
            self._integrity_lost = True
            _refuse()
        CancellationBudget._publish(self, now_ns, end)
        return max(0, end - now_ns)
