"""Unactivated, single-thread operation accounting model; never native authority.

The adapter must supply trusted monotonic samples and measured logical byte sizes.
No payload, credential, callback, native actor or transport is held here. Releasing
model reservations does not prove native thread/socket/writer settlement. The
future actual owner must establish that evidence before calling release methods.
Limits are explicit/provisional, not a qualified production frame/decoder budget.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass


class GroupLedgerRefusalError(ValueError):
    """Fixed content-free refusal, with no caller object formatting."""

    def __init__(self) -> None:
        super().__init__("Group operation accounting unavailable.")


def _integer(value: object) -> int:
    if type(value) is not int or not 1 <= value <= (1 << 31) - 1:
        raise GroupLedgerRefusalError()
    return value


def _time(value: object) -> float:
    if type(value) not in (int, float):
        raise GroupLedgerRefusalError()
    try:
        result = float(value)
    except OverflowError:
        raise GroupLedgerRefusalError() from None
    if not math.isfinite(result) or result < 0 or (type(value) is int and result != value):
        raise GroupLedgerRefusalError()
    return result


@dataclass(slots=True)
class _Operation:
    generation: int
    deadline: float
    descriptor_bytes: int
    pending: bool = False
    reservations: int = 0


@dataclass(frozen=True, slots=True)
class GroupLedgerSnapshot:
    """Accounting only, not a ready/authorized/cleaned-up verdict."""

    generation: int
    open: bool
    queued: int
    pending: int
    reservations: int
    descriptor_bytes: int
    retained_bytes: int


class GroupOperationLedger:
    """One retained model budget across generations; exact opaque handle identity.

    Confined to its constructing Thread object. No tombstones accumulate: stale
    handle identities remain absent and cannot match a later newly minted object.
    Private records are trusted implementation state, not tamper-proof Python.
    """

    def __init__(
        self,
        *,
        max_queued: int,
        max_pending: int,
        max_reservations: int,
        max_descriptor_bytes: int,
        max_retained_bytes: int,
    ) -> None:
        self._max_queued = _integer(max_queued)
        self._max_pending = _integer(max_pending)
        self._max_reservations = _integer(max_reservations)
        self._max_descriptor_bytes = _integer(max_descriptor_bytes)
        self._max_retained_bytes = _integer(max_retained_bytes)
        self._thread = threading.current_thread()
        self._operations: dict[object, _Operation] = {}
        self._reservations: dict[object, tuple[object, int]] = {}
        self._generation = 1
        self._open = True
        self._last_time = 0.0
        self._queued = self._pending = self._descriptors = self._retained = 0

    def _confined(self) -> None:
        if threading.current_thread() is not self._thread:
            raise GroupLedgerRefusalError()

    def _sample(self, now: object) -> float:
        value = _time(now)
        if value < self._last_time:
            raise GroupLedgerRefusalError()
        self._last_time = value
        return value

    def _operation(self, handle: object) -> _Operation:
        if type(handle) is not object or handle not in self._operations:
            raise GroupLedgerRefusalError()
        return self._operations[handle]

    def _current(self, operation: _Operation, now: float) -> bool:
        return self._open and operation.generation == self._generation and now < operation.deadline

    def enqueue(self, *, now: object, deadline: object, descriptor_bytes: object) -> object:
        """Absolute deadline comes from operation creation BEFORE any queue wait."""
        self._confined()
        end = _time(deadline)
        size = _integer(descriptor_bytes)
        current = self._sample(now)
        if (
            not self._open
            or end <= current
            or self._queued >= self._max_queued
            or self._descriptors + size > self._max_descriptor_bytes
        ):
            raise GroupLedgerRefusalError()
        handle = object()
        self._operations[handle] = _Operation(self._generation, end, size)
        self._queued += 1
        self._descriptors += size
        return handle

    def start(self, handle: object, *, now: object) -> None:
        """Model queue-to-pending transition; never starts an actual actor."""
        self._confined()
        operation = self._operation(handle)
        current = self._sample(now)
        if (
            operation.pending
            or not self._current(operation, current)
            or self._pending >= self._max_pending
        ):
            raise GroupLedgerRefusalError()
        operation.pending = True
        self._queued -= 1
        self._pending += 1

    def publication_allowed(self, handle: object, *, now: object) -> bool:
        """Temporal model fence ONLY; never substitutes for auth/source checks."""
        self._confined()
        operation = self._operation(handle)
        current = self._sample(now)
        return operation.pending and self._current(operation, current)

    def reserve(self, handle: object, *, now: object, size: object) -> object:
        """Charge before retaining each logical representation/conversion copy."""
        self._confined()
        operation = self._operation(handle)
        amount = _integer(size)
        current = self._sample(now)
        if (
            not operation.pending
            or not self._current(operation, current)
            or len(self._reservations) >= self._max_reservations
            or self._retained + amount > self._max_retained_bytes
        ):
            raise GroupLedgerRefusalError()
        reservation = object()
        self._reservations[reservation] = (handle, amount)
        operation.reservations += 1
        self._retained += amount
        return reservation

    def release_reservation(self, reservation: object) -> None:
        """Once-only model release; no assertion that real payload/actor stopped."""
        self._confined()
        if type(reservation) is not object or reservation not in self._reservations:
            raise GroupLedgerRefusalError()
        handle, amount = self._reservations.pop(reservation)
        operation = self._operations[handle]
        operation.reservations -= 1
        self._retained -= amount

    def release_operation(self, handle: object) -> None:
        """Actual owner must establish settlement separately, even with zero bytes."""
        self._confined()
        operation = self._operation(handle)
        if operation.reservations:
            raise GroupLedgerRefusalError()
        del self._operations[handle]
        self._descriptors -= operation.descriptor_bytes
        if operation.pending:
            self._pending -= 1
        else:
            self._queued -= 1

    def retire(self) -> None:
        """Out-of-band output fence; full queues/debt do not block this method."""
        self._confined()
        self._open = False

    def advance_generation(self) -> None:
        """New model generation shares all old retained debt, never a new pool."""
        self._confined()
        if self._open or self._generation >= (1 << 63) - 1:
            raise GroupLedgerRefusalError()
        self._generation += 1
        self._open = True

    def snapshot(self) -> GroupLedgerSnapshot:
        self._confined()
        return GroupLedgerSnapshot(
            self._generation,
            self._open,
            self._queued,
            self._pending,
            len(self._reservations),
            self._descriptors,
            self._retained,
        )
