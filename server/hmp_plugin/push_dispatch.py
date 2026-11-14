"""PN-DSP bounded listener-loop delivery orchestration; no approval authority.

The relay port is injected. T025 supplies the HTTPS/signature transport; this
module never reads provider credentials, sends native answers or logs handles.
Only the immutable insertion/view interfaces are used on the prompt store.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from . import crypto, wire
from .contract import REFRESH_ABSOLUTE_TTL_S, WriteGateState
from .gate import direct_send_gate
from .logging_policy import log_event
from .prompts import ApprovalInserted, RowView
from .push_config import RelayConfig
from .push_hints import HintBinding
from .push_issuer import derive_collapse, rederive_route
from .push_registration import _inputs, _key
from .push_resolve import Gate
from .reads import require_bot_authorized
from .request_ctx import ServerContext

QUEUE_CAP = 64
CONCURRENCY = 2
RECIPIENT_CAP = 4
SLOT_CAP = 256
COUNTER_CAP = 256
INTERVAL_S = 10
HOURLY_CAP = 30
CLOSE_S = 1


def ttl_s(estimate: int | None, now: int) -> int:
    return 330 if estimate is None else max(60, min(900, estimate - now + 30))


@dataclass(frozen=True, repr=False)
class RelayAttempt:
    relay: RelayConfig
    iid: str
    route: bytes
    hint: bytes
    collapse: bytes
    platform: str
    addr_kind: str
    env: str | None
    kid: str
    sealed: bytes
    ttl_s: int
    ts: int
    nonce: bytes


class RelayPort(Protocol):
    async def send(self, attempt: RelayAttempt) -> str: ...
    async def close(self) -> None: ...


# The transport must return only one of these fixed classifications. Unknown
# strings and exceptions are ambiguous, never retryable or retirement evidence.
RESULTS = frozenset(
    {
        "accepted",
        "prewrite_failure",
        "unavailable",
        "postwrite_timeout",
        "provider_unavailable",
        "provider_gone",
        "sealed_invalid",
        "replayed",
        "rate_limited",
        "bad_request",
        "unauthorized",
        "ambiguous",
    }
)


@dataclass(frozen=True, repr=False)
class Event:
    inserted: ApprovalInserted
    deadline: float


@dataclass(frozen=True, repr=False)
class Pending:
    event: Event
    device_id: str
    route_hash: bytes
    generation: int
    hint: str
    collapse: bytes


@dataclass(repr=False)
class Slot:
    last_send: float | None = None
    pending: Pending | None = None
    task: asyncio.Task | None = None
    busy: bool = False


@dataclass(repr=False)
class Counter:
    start: float
    count: int = 0


def _log(outcome: str) -> None:
    # Producer/worker failure isolation includes a broken logging sink.
    with contextlib.suppress(Exception):
        log_event("push_dispatch", outcome=outcome)


def _consume_result(task: asyncio.Task) -> None:
    # A client close that outlives the bounded shutdown may eventually fail.
    # Consume that failure without allowing raw relay text into loop diagnostics.
    if not task.cancelled():
        task.exception()


class PushDispatcher:
    def __init__(
        self,
        ctx: ServerContext,
        relay: RelayPort,
        *,
        require_gate: Gate,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[], float] = lambda: int.from_bytes(crypto.random_bytes(2), "big") / 65535,
    ) -> None:
        self.ctx, self.relay, self.require_gate = ctx, relay, require_gate
        self.monotonic, self.sleep, self.jitter = monotonic, sleep, jitter
        self.loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue[Event] = asyncio.Queue(QUEUE_CAP)
        # Reservations bound even the cross-thread scheduled callbacks, before
        # they reach the loop queue. This lock is never a store/prompt lock.
        self._capacity = threading.BoundedSemaphore(QUEUE_CAP)
        self._semaphore = asyncio.Semaphore(CONCURRENCY)
        self.workers: list[asyncio.Task] = []
        self.slots: OrderedDict[tuple[bytes, int, str], Slot] = OrderedDict()
        self.counters: dict[str, Counter] = {}
        self.closed = False
        self.failures = 0
        self.open_until = 0.0
        self.half_open = False
        self.store = ctx.prompt_store

    def start(self) -> None:
        if self.closed or self.workers or self.store is None or self.store.closed:
            raise ValueError("dispatcher cannot start")
        try:
            for _ in range(CONCURRENCY):
                coro = self._worker()
                try:
                    self.workers.append(self.loop.create_task(coro))
                except BaseException:
                    coro.close()
                    raise
            self.store.set_insertion_observer(self.observe)
        except BaseException:
            self.closed = True
            for task in self.workers:
                task.cancel()
            raise

    def observe(self, inserted: ApprovalInserted) -> None:
        """I-1 producer: synchronous, bounded, no file/SQL/native I/O or await."""
        reserved = False
        try:
            if self.closed or not isinstance(inserted, ApprovalInserted):
                return
            if inserted.surface not in ("bot_chat", "phone_chat"):
                return
            if not self._capacity.acquire(blocking=False):
                _log("queue_full")
                return
            reserved = True
            try:
                same_loop = asyncio.get_running_loop() is self.loop
            except RuntimeError:
                same_loop = False
            if same_loop:
                self._enqueue(inserted)
            else:
                self.loop.call_soon_threadsafe(self._enqueue, inserted)
            reserved = False  # ownership transferred to _enqueue/the consumer
        except Exception:
            _log("producer_failed")
        finally:
            if reserved:
                self._capacity.release()

    def _enqueue(self, inserted: ApprovalInserted) -> None:
        try:
            if self.closed:
                self._capacity.release()
                return
            event = Event(inserted, self.monotonic() + ttl_s(inserted.expires_at, self.ctx.now()))
            self.queue.put_nowait(event)
        except Exception:
            self._capacity.release()
            _log("queue_full")

    def _view(self, inserted: ApprovalInserted) -> RowView | None:
        store = self.ctx.prompt_store
        if (
            self.closed
            or store is not self.store
            or store is None
            or store.closed
            or store.generation != inserted.generation
            or inserted.key[0] != self.ctx.iid
            or not self.ctx.identity.still_current()
        ):
            return None
        availability = self.ctx.push_availability()
        if not availability.available or not self.ctx.approval_surface_available(inserted.surface):
            return None
        view = store.view_row(
            inserted.key, now=self.ctx.now(), members=self.ctx.approval_members_now()
        )
        return (
            view
            if (
                view is not None
                and view.kind == "approval"
                and view.surface == inserted.surface
                and view.generation == inserted.generation
                and view.visible_now
            )
            else None
        )

    def _hint_view(self, binding: HintBinding) -> RowView | None:
        store = self.ctx.prompt_store
        if (
            store is not self.store
            or store is None
            or store.closed
            or store.generation != binding.prompt_generation
        ):
            return None
        return store.view_row(
            binding.key, now=self.ctx.now(), members=self.ctx.approval_members_now()
        )

    def _current(self, pending: Pending, key: bytes | None):
        if self._view(pending.event.inserted) is None or self.monotonic() >= pending.event.deadline:
            return None
        row = self.ctx.store.push_dispatch_device_snapshot(pending.device_id)
        if row is None or not self.ctx.is_approval_owner_device(pending.device_id):
            return None
        now = self.ctx.now()
        availability = self.ctx.push_availability()
        if (
            not availability.available
            or row["user_id"] != pending.event.inserted.key[1]
            or row["device_state"] != "ACTIVE"
            or row["revoked_at"] is not None
            or row["family_device"] != row["device_id"]
            or now >= row["family_created_at"] + REFRESH_ABSOLUTE_TTL_S
            or row["iid"] != self.ctx.iid
            or row["host_generation"] != row["current_h"]
            or row["generation"] != row["current_g"]
            or row["generation"] != pending.generation
            or bytes(row["route_hash"]) != pending.route_hash
            or row["expires_at"] <= now
            or row["relay_kid"] not in availability.live_kids
            or self.ctx.push_route_fenced(pending.route_hash)
        ):
            return None
        route = rederive_route(key, _inputs(row), pending.route_hash)
        return (row, route, availability.relay) if route is not None else None

    async def _ready(self, pending: Pending):
        key = await _key(self.ctx)  # non-repairing key I/O is off the listener loop
        if self._current(pending, key) is None or self.ctx.bridge is None:
            return None
        bridge = self.ctx.bridge
        authz = bridge.authz_state
        await asyncio.to_thread(
            require_bot_authorized,
            bridge,
            pending.event.inserted.key[1],
            pending.event.inserted.key[2],
        )
        if (
            self.ctx.bridge is not bridge
            or bridge.authz_state != authz
            or self._current(pending, key) is None
        ):
            return None
        endpoint = await self.require_gate(
            self.ctx, pending.event.inserted.key[2], member=pending.event.inserted.surface
        )
        if (
            self.ctx.bridge is not bridge
            or bridge.authz_state != authz
            or self._current(pending, key) is None
        ):
            return None
        await asyncio.to_thread(
            require_bot_authorized,
            bridge,
            pending.event.inserted.key[1],
            pending.event.inserted.key[2],
        )
        current = self._current(pending, key)
        gate = direct_send_gate(
            base_write_gate=self.ctx.write_gate(),
            flag_enabled=self.ctx.direct_send_effective(),
            endpoint=endpoint,
        )
        if (
            self.ctx.bridge is not bridge
            or bridge.authz_state != authz
            or gate.state not in (WriteGateState.OPEN, WriteGateState.OPEN_GUARDED)
        ):
            return None
        return current

    async def _worker(self) -> None:
        while True:
            event = await self.queue.get()
            self._capacity.release()
            try:
                await self.dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                _log("dispatch_failed")
            finally:
                self.queue.task_done()

    async def dispatch(self, event: Event) -> None:
        if self.monotonic() >= event.deadline or self._view(event.inserted) is None:
            _log("ineligible")
            return
        if self.monotonic() < self.open_until:
            _log("breaker_open")
            return
        key = await _key(self.ctx)
        if key is None or self._view(event.inserted) is None or self.monotonic() >= event.deadline:
            return
        recipients = 0
        for row in self.ctx.store.push_dispatch_candidates(event.inserted.key[1]):
            pending = Pending(
                event, row["device_id"], bytes(row["route_hash"]), row["generation"], "", b""
            )
            if self._current(pending, key) is None:
                continue
            if recipients == RECIPIENT_CAP:
                _log("recipients_capped")
                break
            recipients += 1
            binding = HintBinding(
                pending.route_hash,
                pending.generation,
                event.inserted.generation,
                event.inserted.key,
                self.ctx.now(),
            )
            hint = self.ctx.push_hints.mint(binding, now=self.ctx.now(), view=self._hint_view)
            route = self._current(pending, key)[1]
            pending = Pending(
                event,
                pending.device_id,
                pending.route_hash,
                pending.generation,
                hint,
                derive_collapse(key, route, event.inserted.key[2]),
            )
            self._schedule(pending)

    def _schedule(self, pending: Pending) -> None:
        slot_key = (pending.route_hash, pending.generation, pending.event.inserted.key[2])
        slot = self.slots.get(slot_key)
        if slot is None:
            if len(self.slots) >= SLOT_CAP:
                idle = next(
                    (
                        key
                        for key, value in self.slots.items()
                        if value.pending is None and not value.busy and value.task is None
                    ),
                    None,
                )
                if idle is None:
                    _log("coalesce_full")
                    return
                del self.slots[idle]
            slot = self.slots[slot_key] = Slot()
        self.slots.move_to_end(slot_key)
        slot.pending = pending  # one pending item; newest K replaces the old one
        if slot.task is None:
            coro = self._trailing(slot)
            try:
                slot.task = self.loop.create_task(coro)
            except BaseException:
                coro.close()
                slot.pending = None
                raise

    async def _trailing(self, slot: Slot) -> None:
        try:
            while slot.pending is not None and not self.closed:
                if slot.last_send is not None:
                    delay = slot.last_send + INTERVAL_S - self.monotonic()
                    if delay > 0:
                        await self.sleep(delay)
                pending, slot.pending = slot.pending, None
                slot.busy = True
                try:
                    await self._send(pending, slot)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _log("dispatch_failed")
                finally:
                    slot.busy = False
        finally:
            slot.task = None

    def _charge(self, device_id: str) -> bool:
        now = self.monotonic()
        for device, counter in tuple(self.counters.items()):
            state, active = self.ctx.store.push_counter_state(device)
            if state != "ACTIVE" or (now >= counter.start + 3600 and not active):
                del self.counters[device]
        counter = self.counters.get(device_id)
        if counter is None:
            if len(self.counters) >= COUNTER_CAP:
                _log("rate_table_full")
                return False
            counter = self.counters[device_id] = Counter(now)
        if now >= counter.start + 3600:
            counter.start, counter.count = now, 0
        if counter.count >= HOURLY_CAP:
            _log("rate_capped")
            return False
        counter.count += 1
        return True

    def _breaker_enter(self) -> tuple[bool, bool]:
        if self.monotonic() < self.open_until or self.half_open:
            _log("breaker_open")
            return False, False
        probe = self.failures >= 3
        if probe:
            self.half_open = True
        return True, probe

    def _breaker_result(self, result: str, *, probe: bool) -> None:
        if probe:
            self.half_open = False
        if result in ("prewrite_failure", "unavailable", "postwrite_timeout"):
            self.failures += 1
            if self.failures >= 3:
                self.open_until = self.monotonic() + 60
        elif probe or self.failures < 3:
            self.failures = 0
            self.open_until = 0.0

    async def _send(self, pending: Pending, slot: Slot) -> None:
        for attempt_number in range(3):
            async with self._semaphore:
                ready = await self._ready(pending)
                if ready is None:
                    return
                admitted, probe = self._breaker_enter()
                if not admitted:
                    return
                # From this point to send() there is no yield or store lock.
                if not self._charge(pending.device_id):
                    self.half_open = False
                    return
                row, route, relay = ready
                remaining = pending.event.deadline - self.monotonic()
                if remaining <= 0:
                    self.half_open = False
                    return
                attempt = RelayAttempt(
                    relay,
                    self.ctx.iid,
                    route,
                    wire.b64u_decode(pending.hint, length=32),
                    pending.collapse,
                    row["platform"],
                    row["addr_kind"],
                    row["env"],
                    row["relay_kid"],
                    bytes(row["sealed"]),
                    ttl_s(pending.event.inserted.expires_at, self.ctx.now()),
                    self.ctx.now(),
                    crypto.random_bytes(16),
                )
                slot.last_send = self.monotonic()
                try:
                    result = await self.relay.send(attempt)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    result = "ambiguous"
                if result not in RESULTS:
                    result = "ambiguous"
                self._breaker_result(result, probe=probe)
                if self.closed:
                    return
                _log(result)
                if result in ("provider_gone", "sealed_invalid"):
                    self.ctx.store.push_feedback(
                        pending.device_id,
                        pending.route_hash,
                        pending.generation,
                        state="provider_gone" if result == "provider_gone" else "expired",
                        now=self.ctx.now(),
                    )
                    return
                if result not in ("prewrite_failure", "unavailable"):
                    return
            if attempt_number == 2 or self.monotonic() < self.open_until:
                return
            delay = (1, 4)[attempt_number] * (0.8 + 0.4 * self.jitter())
            if self.monotonic() + delay >= pending.event.deadline:
                return
            await self.sleep(delay)

    async def close(self) -> None:
        self.closed = True
        if self.ctx.prompt_store is self.store and self.store is not None:
            with contextlib.suppress(Exception):
                self.store.set_insertion_observer(None)
        self.ctx.push_hints.clear()
        tasks = [*self.workers, *(s.task for s in self.slots.values() if s.task is not None)]
        for task in tasks:
            task.cancel()
        closer = self.loop.create_task(self.relay.close())
        tasks.append(closer)
        done, pending = await asyncio.wait(tasks, timeout=CLOSE_S)
        for task in done:
            _consume_result(task)
        for task in pending:
            task.add_done_callback(_consume_result)
            task.cancel()
        self.slots.clear()
        self.counters.clear()
        while not self.queue.empty():
            self.queue.get_nowait()
            self._capacity.release()
            self.queue.task_done()
