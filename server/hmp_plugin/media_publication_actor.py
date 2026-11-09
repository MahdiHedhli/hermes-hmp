"""Unwired listener actor for in-process Store observers; no native/IPC coverage.

Only fixed publication operations run on the listener thread. Worker callers wait
for bounded acknowledgements before SQL. Timeout/unknown enqueue closes admission;
permits remain held until queued callbacks actually retire. No future is cancelled.
Adapters must use THIS actor's candidate/claim interface, never its private state.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time

from .media_publication import MediaPublication, MutationTicket, PublicationUnavailable

_ACK_WAIT_S = 0.25
_MAX_PENDING = 32


class MediaPublicationActor:
    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._thread = threading.current_thread()
        self._publisher = MediaPublication()
        self._failed = threading.Event()
        self._slots = threading.BoundedSemaphore(_MAX_PENDING)

    def _owner(self) -> None:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailable()
        if self._failed.is_set():
            self._publisher.close()
            raise PublicationUnavailable()

    def candidate(self, scope: tuple, cohort: tuple):
        self._owner()
        return self._publisher.candidate(scope, cohort)

    def claim_once(self, ticket, scope: tuple, cohort: tuple) -> bool:
        self._owner()
        return self._publisher.claim_once(ticket, scope, cohort)

    def close(self) -> None:
        if threading.current_thread() is not self._thread:
            raise PublicationUnavailable()
        self._failed.set()
        self._publisher.close()

    def _poison(self) -> None:
        # Called on the owner loop, never by the waiting worker.
        self._publisher.close()

    def _fail(self) -> None:
        self._failed.set()
        try:
            self._loop.call_soon_threadsafe(self._poison)
        except BaseException:
            pass  # closed loop cannot authorize; never invent an acknowledgement

    def _deliver(self, reply, deadline, operation, receipt, certain) -> None:
        try:
            if self._failed.is_set() or time.monotonic() >= deadline:
                self._failed.set()
                self._publisher.close()
                raise PublicationUnavailable()
            if operation == 'begin':
                result = self._publisher.begin_mutation()
            else:
                self._publisher.settle_mutation(receipt, certain=certain)
                result = None
            reply.set_result(result)
        except BaseException:
            # A partial operation has unknown completion. Keep all admission shut.
            self._failed.set()
            self._publisher.close()
            if not reply.done():
                reply.set_exception(PublicationUnavailable())
        finally:
            self._slots.release()  # original callback has really finished

    def _request(self, operation: str, receipt=None, certain=False):
        if threading.current_thread() is self._thread:
            raise PublicationUnavailable()  # no loop-thread rendezvous/deadlock
        if self._failed.is_set() or not self._loop.is_running():
            raise PublicationUnavailable()
        if not self._slots.acquire(blocking=False):
            raise PublicationUnavailable()
        reply = concurrent.futures.Future()
        deadline = time.monotonic() + _ACK_WAIT_S
        try:
            self._loop.call_soon_threadsafe(
                self._deliver, reply, deadline, operation, receipt, certain,
            )
            result = reply.result(timeout=max(0, deadline - time.monotonic()))
            if time.monotonic() >= deadline:
                raise PublicationUnavailable()
            return result
        except BaseException:
            # Do not release the slot early: enqueue may have happened and the
            # callback must retire it. Unknown enqueue can retain debt until close.
            self._fail()
            raise PublicationUnavailable() from None

    def begin(self) -> MutationTicket:
        result = self._request('begin')
        if type(result) is not MutationTicket:
            self._fail()
            raise PublicationUnavailable()
        return result

    def settle(self, receipt: object, *, certain: bool) -> None:
        if type(receipt) is not MutationTicket or type(certain) is not bool:
            raise PublicationUnavailable()
        self._request('settle', receipt, certain)
