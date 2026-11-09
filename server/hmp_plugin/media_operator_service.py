"""Unwired same-UID operator mutation service; not a human-consent verifier.

The adapter never starts this service. Future CLI integration must verify the live
listener and perform exact typed consent before connecting. Native/config writer
coordination and whole-listener Store retirement remain separate prerequisites.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import os
import secrets
import time
from pathlib import Path

from . import wire
from .media_operator_execution import (
    MediaMutationRefusedError,
    MediaOperatorExecutor,
)
from .media_operator_protocol import decode_mutation, encode_reply
from .operator_read import OperatorReadService, OperatorUnavailableError, _peer_uid

_DEADLINE_S = 2.0
_MAX_FRAME = 4096


class MediaOperatorMutationService(OperatorReadService):
    def __init__(self, ctx, anchor_dir: Path, nonce: str, actor) -> None:
        super().__init__(ctx, anchor_dir, nonce, _socket_kind="media_write")
        self._executor = MediaOperatorExecutor(ctx, actor, nonce)
        self._original_ctx = ctx
        self._budget = ctx.read_worker_budget
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._operations: dict[object, concurrent.futures.Future | None] = {}
        self._loop = asyncio.get_running_loop()
        self._started_once = False

    async def start(self) -> None:
        if self._started_once or self._stopping:
            raise OperatorUnavailableError("operator service unavailable")
        self._started_once = True
        await super().start()

    def _current(self) -> bool:
        return (
            not self._stopping
            and self.ctx is self._original_ctx
            and self.ctx.read_worker_budget is self._budget
            and self._executor._same()
            and self._server is not None
            and self._fd is not None
        )

    def _operator_debt(self) -> int:
        return len(self._operations)

    def _retire(self, intent, original) -> None:
        if self._operations.get(intent) is not original:
            return  # unknown/foreign completion cannot retire another operation
        del self._operations[intent]
        self._budget.release(operator=True)
        if self._stopping and not self._operations:
            self._drained.set()

    async def _decide(self, request, deadline):
        intent = object()  # no reservation exists if allocation fails
        if not self._current():
            return encode_reply(request, "refused")
        try:
            self._operations[intent] = None
        except BaseException:
            # Neither budget acquisition nor worker submission has been called.
            self._operations.pop(intent, None)
            return encode_reply(request, "refused")
        try:
            reserved = self._budget.reserve(operator=True)
        except BaseException:
            # Acquisition may have incremented capacity before losing its return.
            # Preserve the original intent and poison shared admission; no refund,
            # Store retirement proof or automatic recovery is fabricated.
            self._budget.poisoned = True
            self._stopping = True
            return encode_reply(request, "unknown")
        if reserved is False:
            self._operations.pop(intent)
            return encode_reply(request, "refused")
        if reserved is not True:
            self._budget.poisoned = True
            self._stopping = True
            return encode_reply(request, "unknown")
        # Debt is derived from this ledger, never a separately allocated int count.
        try:
            original = self._pool.submit(self._executor.decide, request, deadline=deadline)
            self._operations[intent] = original

            def done(future):
                # Actual concurrent Future completion, never an async wrapper's cancellation.
                with contextlib.suppress(RuntimeError):
                    self._loop.call_soon_threadsafe(self._retire, intent, future)

            original.add_done_callback(done)
        except BaseException:
            # Enqueue may have occurred. Unknown debt is never refunded or replayed.
            self._stopping = True
            return encode_reply(request, "unknown")
        try:
            wrapped = asyncio.wrap_future(original)

            def consume_late_error(future):
                # A caller timeout/cancellation leaves this wrapper alive. Consume
                # its eventual exception without logging worker diagnostics. This
                # callback has NO authority to retire debt or release the Store.
                with contextlib.suppress(BaseException):
                    future.exception()

            wrapped.add_done_callback(consume_late_error)
            result = await asyncio.wait_for(
                asyncio.shield(wrapped), max(0, deadline - time.monotonic())
            )
            if not self._current() or time.monotonic() >= deadline:
                return encode_reply(request, "unknown")
            return encode_reply(request, result.status, result.decision)
        except MediaMutationRefusedError:
            return encode_reply(request, "refused")
        except (Exception, asyncio.CancelledError):
            return encode_reply(request, "unknown")

    async def _handle(self, reader, writer) -> None:
        if self._stopping or len(self._clients) >= 2:
            writer.transport.abort()  # no unbounded waiting-close task for excess peers
            return
        task = asyncio.current_task()
        assert task is not None
        self._clients.add(task)
        try:
            sock = writer.get_extra_info("socket")
            if sock is None or _peer_uid(sock) != os.getuid() or not self._current():
                return
            challenge = secrets.token_hex(16)
            deadline = time.monotonic() + _DEADLINE_S
            hello = {
                "protocol": 1,
                "operation": "host_media_read_challenge",
                "iid": self._executor._iid,
                "nonce": self.nonce,
                "generation": self._executor._generation,
                "challenge": challenge,
                "expires_ms": int(deadline * 1000),
            }
            writer.write(wire.dump_json(hello) + b"\n")
            await asyncio.wait_for(writer.drain(), max(0, deadline - time.monotonic()))
            raw = await asyncio.wait_for(reader.readline(), max(0, deadline - time.monotonic()))
            if not raw.endswith(b"\n") or len(raw) > _MAX_FRAME:
                return
            envelope = wire.parse_body(raw[:-1], max_bytes=_MAX_FRAME - 1, max_depth=4)
            if (
                set(envelope) != {"challenge", "mutation"}
                or type(envelope["challenge"]) is not str
                or envelope["challenge"] != challenge
                or type(envelope["mutation"]) is not dict
            ):
                return
            request = decode_mutation(wire.dump_json(envelope["mutation"]))
            challenge = None  # consumed once BEFORE dispatch; handler never reads another frame
            if not self._current() or time.monotonic() >= deadline:
                return
            response = await self._decide(request, deadline)
            if not self._stopping:
                writer.write(response + b"\n")
                await asyncio.wait_for(writer.drain(), max(0, deadline - time.monotonic()))
        except (Exception, asyncio.CancelledError):
            return  # empty response is not a definitive no-write result
        finally:
            self._clients.discard(task)
            writer.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(writer.wait_closed(), _DEADLINE_S)

    async def stop(self) -> int:
        debt = await super().stop()
        self._pool.shutdown(wait=False, cancel_futures=False)
        return debt
