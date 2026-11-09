"""Listener-thread currency primitive, NOT authentication or an enabled route.

A worker must still collect real authority. Every participating writer must obtain
invalidation on the listener thread BEFORE changing authority, then settle there.
No SQL, native/config callbacks, waits, or worker cancellation occur here. This
module is deliberately unwired until store/operator/native writer coverage exists.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

_MAX_EPOCH = (1 << 53) - 1
_MAX_INFLIGHT = 32
_MAX_LIFETIME_NS = 2_000_000_000


class PublicationUnavailableError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("media publication unavailable")


@dataclass(frozen=True, eq=False, repr=False, slots=True)
class PublicationTicket:
    def __repr__(self) -> str:
        return "PublicationTicket()"


@dataclass(frozen=True, eq=False, repr=False, slots=True)
class MutationTicket:
    def __repr__(self) -> str:
        return "MutationTicket()"


def _scope(value: object) -> tuple[str, str, str, int]:
    if type(value) is not tuple or len(value) != 4:
        raise PublicationUnavailableError()
    iid, device, profile, request_epoch = value
    if (
        type(iid) is not str
        or len(iid) != 52
        or any(c not in "abcdefghijklmnopqrstuvwxyz234567" for c in iid)
        or iid[-1] not in "aq"
        or type(device) is not str
        or not 1 <= len(device) <= 256
        or any(not 33 <= ord(c) <= 126 for c in device)
        or type(profile) is not str
        or not 1 <= len(profile) <= 64
        or not profile[0].isascii()
        or not profile[0].isalnum()
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in profile)
        or type(request_epoch) is not int
        or not 0 <= request_epoch <= _MAX_EPOCH
    ):
        raise PublicationUnavailableError()
    return value


def _cohort(value: object) -> tuple[object, object, object]:
    if type(value) is not tuple or len(value) != 3 or any(v is None for v in value):
        raise PublicationUnavailableError()
    return value


class MediaPublication:
    """Single listener-thread ownership. Currency is never a permission grant.

    Cross-process/native writers have no automatic coherence. The adapter MUST NOT
    use this primitive as its final gate until their before-effect invalidation
    contract is implemented. Thread rejection cannot replace an RPC handshake.
    """

    def __init__(self) -> None:
        self._thread = threading.current_thread()
        self._epoch = 0
        self._poisoned = False
        self._pending: dict[MutationTicket, None] = {}
        self._candidates: dict[PublicationTicket, tuple[int, int, tuple, tuple]] = {}

    def _owner(self) -> None:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailableError()

    def _advance(self) -> None:
        if self._epoch >= _MAX_EPOCH:
            self._poisoned = True
            self._candidates.clear()
            raise PublicationUnavailableError()
        self._epoch += 1
        self._candidates.clear()

    def begin_mutation(self) -> MutationTicket:
        self._owner()
        if self._poisoned or len(self._pending) >= _MAX_INFLIGHT:
            raise PublicationUnavailableError()
        self._advance()  # invalidation happens before caller may change authority
        ticket = MutationTicket()
        self._pending[ticket] = None
        return ticket

    def settle_mutation(self, ticket: MutationTicket, *, certain: bool) -> None:
        self._owner()
        if type(ticket) is not MutationTicket or ticket not in self._pending:
            raise PublicationUnavailableError()
        if type(certain) is not bool:
            raise PublicationUnavailableError()
        if not certain:
            # Poison BEFORE any transition can release the pending mutation.
            self._poisoned = True
            self._candidates.clear()
        self._advance()  # pending remains closed across interrupted advancement
        del self._pending[ticket]  # last: only a settled result releases this barrier

    # Create BEFORE worker sampling begins, never after a completed authority read.
    def candidate(self, scope: tuple[str, str, str, int], cohort: tuple) -> PublicationTicket:
        self._owner()
        scope = _scope(scope)
        cohort = _cohort(cohort)
        now = time.monotonic_ns()
        self._candidates = {k: v for k, v in self._candidates.items() if now < v[1]}
        if self._poisoned or self._pending or len(self._candidates) >= _MAX_INFLIGHT:
            raise PublicationUnavailableError()
        ticket = PublicationTicket()
        self._candidates[ticket] = (self._epoch, now + _MAX_LIFETIME_NS, scope, cohort)
        return ticket

    def claim_once(self, ticket: PublicationTicket, scope: tuple, cohort: tuple) -> bool:
        self._owner()
        if type(ticket) is not PublicationTicket:
            return False
        # Consume on any attempt with the original ticket, including scope mismatch.
        retained = self._candidates.pop(ticket, None)
        if retained is None:
            return False
        scope = _scope(scope)
        cohort = _cohort(cohort)
        epoch, deadline, expected_scope, expected_cohort = retained
        return (
            not self._poisoned
            and not self._pending
            and epoch == self._epoch
            and time.monotonic_ns() < deadline
            and scope == expected_scope
            and all(a is b for a, b in zip(cohort, expected_cohort, strict=True))
        )

    def close(self) -> None:
        self._owner()
        self._poisoned = True
        self._candidates.clear()
        self._pending.clear()
