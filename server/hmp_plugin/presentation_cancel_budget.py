"""Nonrenewing cancellation arithmetic, never clock-domain or closure proof.

Callers must qualify a common native clock and bind the operation before adopting
wire values. The current v1 service does neither and cannot use this as admission.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

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


class CancellationBudget:
    """One owner per operation; every cause shortens the same frozen deadline.

    Explicit clock samples make this arithmetic testable, not authenticated. No
    tolerance accepts future starts. A late local cause is capped at the original
    work deadline. Failure is sticky; retained end remains diagnostic, not proof.
    This owner is confined to its event-loop thread; it is not a shared lock.
    """

    def __init__(self, work_end_ns: int):
        _ns(work_end_ns)
        if work_end_ns == 0 or work_end_ns > MAX_NS - CLEANUP_NS:
            _refuse()
        self._work_end_ns = work_end_ns
        self._last_ns: int | None = None
        self._end_ns: int | None = None
        self._failed = False

    def _sample(self, now_ns: int) -> None:
        try:
            _ns(now_ns)
            if self._failed or (self._last_ns is not None and now_ns < self._last_ns):
                _refuse()
        except FrameError:
            self._failed = True
            raise
        self._last_ns = now_ns

    def local(self, now_ns: int) -> CancellationWindow:
        """EOF, timeout and revocation all use this same first-cause owner."""
        self._sample(now_ns)
        start = min(now_ns, self._work_end_ns)
        window = CancellationWindow(start, start + CLEANUP_NS)
        self._shorten(window.end_ns)
        return CancellationWindow(self._end_ns - CLEANUP_NS, self._end_ns)

    def inherit(self, window: CancellationWindow, now_ns: int) -> None:
        self._sample(now_ns)
        try:
            if type(window) is not CancellationWindow:
                _refuse()
            window.__post_init__()
            if window.start_ns > now_ns or window.start_ns > self._work_end_ns:
                _refuse()
        except FrameError:
            self._failed = True
            raise
        self._shorten(window.end_ns)

    def _shorten(self, end_ns: int) -> None:
        self._end_ns = end_ns if self._end_ns is None else min(self._end_ns, end_ns)

    def remaining_ns(self, now_ns: int) -> int:
        self._sample(now_ns)
        if self._end_ns is None:
            self._failed = True
            _refuse()
        return max(0, self._end_ns - now_ns)
