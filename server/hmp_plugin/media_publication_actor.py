"""Unwired listener actor for in-process Store observers; no native/IPC coverage.

Only fixed publication operations run on the listener thread. Worker callers wait
for bounded acknowledgements before SQL. Timeout/unknown enqueue closes admission;
permits remain held until queued callbacks actually retire. No future is cancelled.
Adapters must use THIS actor's candidate/claim interface, never its private state.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import threading
import time

from .media_publication import MediaPublication, MutationTicket, PublicationUnavailableError

_ACK_WAIT_S = 0.25
_MAX_PENDING = 32


class MediaPublicationActor:
    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._thread = threading.current_thread()
        self._publisher = MediaPublication()
        self._failed = threading.Event()
        self._slots = threading.BoundedSemaphore(_MAX_PENDING)
        self._cleanup_slots = threading.BoundedSemaphore(_MAX_PENDING)
        self._mutations: dict[object, MutationTicket | None] = {}
        self._drained = asyncio.Event()

    def _owner(self) -> None:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailableError()
        if self._failed.is_set():
            self._publisher.close()
            raise PublicationUnavailableError()

    def candidate(self, scope: tuple, cohort: tuple):
        self._owner()
        publisher, loop, thread = self._publisher, self._loop, self._thread
        result = publisher.candidate(scope, cohort)
        self._post_operation(publisher, loop, thread)
        return result

    def claim_once(self, ticket, scope: tuple, cohort: tuple) -> bool:
        self._owner()
        publisher, loop, thread = self._publisher, self._loop, self._thread
        result = publisher.claim_once(ticket, scope, cohort)
        self._post_operation(publisher, loop, thread)
        return result

    def _post_operation(self, publisher, loop, thread) -> None:
        if (
            self._failed.is_set()
            or self._publisher is not publisher
            or self._loop is not loop
            or self._thread is not thread
            or not loop.is_running()
        ):
            self._failed.set()
            publisher.close()
            raise PublicationUnavailableError()

    def close(self) -> None:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailableError()
        self._failed.set()
        self._publisher.close()
        self._refresh_drain()

    def _poison(self) -> None:
        # Called on the owner loop, never by the waiting worker.
        self._publisher.close()
        self._refresh_drain()

    def _refresh_drain(self) -> None:
        if self._failed.is_set() and not self._mutations:
            self._drained.set()
        else:
            self._drained.clear()

    def outstanding_mutations(self) -> int:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailableError()
        return len(self._mutations)

    async def wait_drained(self) -> None:
        if asyncio.get_running_loop() is not self._loop or not self._failed.is_set():
            raise PublicationUnavailableError()
        await self._drained.wait()

    def _fail(self) -> None:
        self._failed.set()
        # Best-effort owner cleanup only: sticky failure already refuses all claims.
        with contextlib.suppress(BaseException):
            self._loop.call_soon_threadsafe(self._poison)

    def _deliver(self, reply, deadline, operation, receipt, certain, slots) -> None:
        try:
            closed = self._failed.is_set() or time.monotonic() >= deadline
            if closed:
                self._failed.set()
                self._publisher.close()
            if operation == "begin":
                if closed:
                    raise PublicationUnavailableError()
                intent = object()
                self._mutations[intent] = None  # BEFORE requesting the mutation receipt
                self._refresh_drain()
                result = self._publisher.begin_mutation()
                self._mutations[intent] = result  # original receipt, before acknowledgement
            elif operation == "settle":
                if type(receipt) is not MutationTicket:
                    raise PublicationUnavailableError()
                intent = next(
                    (key for key, value in self._mutations.items() if value is receipt), None
                )
                if intent is None:
                    raise PublicationUnavailableError()
                if not closed:
                    self._publisher.settle_mutation(receipt, certain=certain)
                # Closed settlement is cleanup only, never publication authority.
                # The fixed Store observer calls only after its actual SQL returns.
                del self._mutations[intent]
                self._refresh_drain()
                result = None
            else:
                raise PublicationUnavailableError()
            reply.set_result(result)
        except BaseException:
            # A partial operation has unknown completion. Keep all admission shut.
            self._failed.set()
            self._publisher.close()
            self._refresh_drain()
            if not reply.done():
                reply.set_exception(PublicationUnavailableError())
        finally:
            slots.release()  # original callback and original reservation have retired

    def _request(self, operation: str, receipt=None, certain=False):
        if threading.current_thread() is self._thread:
            raise PublicationUnavailableError()  # no loop-thread rendezvous/deadlock
        if (self._failed.is_set() and operation != "settle") or not self._loop.is_running():
            raise PublicationUnavailableError()
        # Cleanup has independent reserved capacity, including after publication close.
        slots = self._cleanup_slots if operation == "settle" else self._slots
        reserved = None  # unknown acquisition is not proof a slot is unused
        enqueue_attempted = False
        try:
            reserved = slots.acquire(blocking=False)
            if reserved is False:
                raise PublicationUnavailableError()
            reply = concurrent.futures.Future()
            deadline = time.monotonic() + _ACK_WAIT_S
            enqueue_attempted = True
            self._loop.call_soon_threadsafe(
                self._deliver,
                reply,
                deadline,
                operation,
                receipt,
                certain,
                slots,
            )
            result = reply.result(timeout=max(0, deadline - time.monotonic()))
            if self._failed.is_set() or time.monotonic() >= deadline:
                raise PublicationUnavailableError()
            return result
        except BaseException:
            if reserved is False:
                raise PublicationUnavailableError() from None  # capacity refusal, no operation
            self._fail()
            if reserved is True and not enqueue_attempted:
                slots.release()  # proven unused; no callback can own it
            # Otherwise retain debt until actual callback retirement. Unknown
            # enqueue/acquisition may retain debt until this closed actor retires.
            raise PublicationUnavailableError() from None

    def begin(self) -> MutationTicket:
        result = self._request("begin")
        if type(result) is not MutationTicket:
            self._fail()
            raise PublicationUnavailableError()
        return result

    def settle(self, receipt: object, *, certain: bool) -> None:
        if type(receipt) is not MutationTicket or type(certain) is not bool:
            raise PublicationUnavailableError()
        self._request("settle", receipt, certain)
