"""Unwired trusted-local operator CAS execution; NOT a peer/consent verifier.

Future transport must verify its same-UID peer, fresh original context lifetime and
CLI consent before calling this fixed worker operation. No socket/mobile route is
provided here. Nonce/generation do not prove request age or human approval.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import threading
import time

from .media_operator_protocol import MediaReadMutation
from .media_permissions import MediaReadDecision
from .media_publication_actor import MediaPublicationActor
from .store import Store


class MediaMutationRefused(RuntimeError):
    def __init__(self):
        super().__init__('media operator mutation refused')


class MediaMutationUnknown(RuntimeError):
    def __init__(self):
        super().__init__('media operator outcome unknown; inspect; do not replay')


@dataclass(frozen=True, slots=True, repr=False)
class MediaMutationResult:
    status: str
    attempt: str
    decision: MediaReadDecision | None
    def __repr__(self):
        return '<MediaMutationResult redacted>'


class MediaOperatorExecutor:
    def __init__(self, ctx, actor: MediaPublicationActor, nonce: str):
        if (type(actor) is not MediaPublicationActor
                or asyncio.get_running_loop() is not actor._loop
                or type(ctx.store) is not Store
                or ctx.store._mutation_observer is not actor
                or type(nonce) is not str or len(nonce) != 32
                or any(c not in '0123456789abcdef' for c in nonce)):
            raise MediaMutationRefused()
        self._ctx, self._actor = ctx, actor
        self._identity, self._store, self._bridge = ctx.identity, ctx.store, ctx.bridge
        self._iid, self._generation, self._nonce = ctx.iid, ctx.readiness_generation, nonce
        self._loop, self._thread = actor._loop, actor._thread
        self._publisher, self._failure = actor._publisher, actor._failed
        self._transaction = self._store.transaction
        self._set = self._store.set_media_read
        self._read = self._store.media_read_decision

    def _same(self) -> bool:
        ctx, actor = self._ctx, self._actor
        return (ctx.identity is self._identity and ctx.store is self._store
                and ctx.bridge is self._bridge and ctx.iid == self._iid
                and ctx.readiness_generation == self._generation
                and self._store._mutation_observer is actor
                and actor._loop is self._loop and actor._thread is self._thread
                and actor._publisher is self._publisher and actor._failed is self._failure
                and not self._failure.is_set())

    def _check(self, deadline: float) -> None:
        if not self._same() or time.monotonic() >= deadline:
            raise MediaMutationRefused()
        if self._identity.still_current() is not True:
            raise MediaMutationRefused()
        # The identity reader can perform work/callbacks. Rejoin afterward.
        if not self._same() or time.monotonic() >= deadline:
            raise MediaMutationRefused()

    def decide(self, request: MediaReadMutation, *, deadline: float) -> MediaMutationResult:
        if threading.current_thread() is self._thread:
            raise MediaMutationRefused()  # before any native/SQL work
        if (type(request) is not MediaReadMutation or type(deadline) is not float
                or not math.isfinite(deadline) or not 0 < deadline - time.monotonic() <= 2.0):
            raise MediaMutationRefused()
        try:
            request.validate()
        except ValueError:
            raise MediaMutationRefused() from None
        if (request.iid != self._iid or request.nonce != self._nonce
                or request.generation != self._generation):
            raise MediaMutationRefused()
        self._check(deadline)
        now = self._ctx.now()
        if type(now) is not int or not 0 <= now <= 2 ** 63 - 1:
            raise MediaMutationRefused()
        self._check(deadline)
        # Once acquisition can start, any missing result is conservatively unknown.
        try:
            with self._transaction():
                self._check(deadline)
                written = self._set(request.expected, allowed=request.allowed, now=now)
                self._check(deadline)
            self._check(deadline)
            if written is None:
                return MediaMutationResult('conflict', request.attempt, None)
            if type(written) is not MediaReadDecision:
                raise MediaMutationUnknown()
            written.validate()
            current = self._read(self._iid, request.device_id)
            self._check(deadline)
            if type(current) is not MediaReadDecision:
                raise MediaMutationUnknown()
            current.validate()
            if current != written:
                raise MediaMutationUnknown()
            return MediaMutationResult('committed', request.attempt, written)
        except BaseException:
            # A committed SQL result may exist. No rollback or mutation replay here.
            raise MediaMutationUnknown() from None
