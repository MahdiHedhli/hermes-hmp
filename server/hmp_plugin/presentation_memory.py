"""Length-based buffer accounting for the native presentation service.

This portable component performs no reads and grants no authority. A reservation
covers application-owned logical bytes, not Python allocator capacity or RSS.
The producer must retain it until every owned alias/result/write has settled;
request cancellation or future completion does not release reservations here.
"""

from __future__ import annotations

from threading import Lock

OPERATION_PAYLOAD_LIMIT = 16 * 1024 * 1024
MAX_LIVE_BUFFERS = 64
BUFFER_KINDS = frozenset({"file", "conversion", "yaml", "raster", "result", "stream"})


class PresentationMemoryError(ValueError):
    def __init__(self) -> None:
        super().__init__("presentation buffer reservation refused")


class _BufferLease:
    __slots__ = ("_kind", "_owner", "_size")

    def __init__(self, owner: PresentationMemoryBudget, size: int, kind: str) -> None:
        self._owner, self._size, self._kind = owner, size, kind

    def __repr__(self) -> str:
        return "<PresentationBufferLease private>"

    def __copy__(self):
        raise TypeError("presentation buffer lease cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("presentation buffer lease cannot be copied")

    def __reduce__(self):
        raise TypeError("presentation buffer lease cannot be serialized")


class PresentationMemoryBudget:
    """One operation's explicit, lock-protected logical-byte reservations.

    There is no automatic destructor/context-manager/cancel release: a traceback,
    worker or HTTP writer may still retain the actual buffer. The service's six
    operation slots independently retain unknown worker/FD/writer debt.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._live: dict[int, tuple[_BufferLease, int, str]] = {}
        self._used = 0
        self._peak = 0

    def __repr__(self) -> str:
        return "<PresentationMemoryBudget private>"

    def reserve(self, kind: str, size: int) -> _BufferLease:
        # Validate before hashing/comparison; no caller object hooks under lock.
        if (
            type(kind) is not str
            or kind not in BUFFER_KINDS
            or type(size) is not int
            or not 0 < size <= OPERATION_PAYLOAD_LIMIT
        ):
            raise PresentationMemoryError from None
        with self._lock:
            if len(self._live) >= MAX_LIVE_BUFFERS or size > OPERATION_PAYLOAD_LIMIT - self._used:
                raise PresentationMemoryError from None
            lease = _BufferLease(self, size, kind)
            self._live[id(lease)] = (lease, size, kind)
            self._used += size
            self._peak = max(self._peak, self._used)
            return lease

    def release(self, lease: _BufferLease) -> None:
        if type(lease) is not _BufferLease:
            raise PresentationMemoryError from None
        with self._lock:
            held = self._live.get(id(lease))
            if (
                held is None
                or held[0] is not lease
                or lease._owner is not self
                or type(lease._size) is not int
                or lease._size != held[1]
                or type(lease._kind) is not str
                or lease._kind != held[2]
            ):
                raise PresentationMemoryError from None
            del self._live[id(lease)]
            self._used -= held[1]

    def snapshot(self) -> tuple[int, int, int]:
        """Used bytes/live reservations/peak; no source or credential data."""
        with self._lock:
            return self._used, len(self._live), self._peak
