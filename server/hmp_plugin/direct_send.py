"""Direct send to the canonical Bot Chat (`HMP_V1.md` §7a, amendment F2). DS-2..DS-8 orchestration.

Never imports a Hermes internal itself (PR-2, FR-054): every Hermes read goes through
`contract.ReadBridge` (implemented only in `bridge.py`). The loopback call to `api_server` is not
a Hermes import -- it is an HTTP client speaking `api_server`'s own documented product contract
(`HMP_V1.md` GAP-2), pinned to the resolved loopback literal `bridge.py` already validated,
`aiohttp.ClientSession(trust_env=False)` so no proxy environment variable can ever redirect the
Bearer token off-box (DS-6, review round-1 finding #6).

Order (DS-2..DS-7):
  (a) per-bot gate (ERR-3) -- run by the caller (`server.py`), before this module is reached at
      all, exactly like every other `/bots/{p}/...` route. Not this module's job.
  (b) the write gate (`gate.direct_send_gate`): `OPEN_GUARDED` requires the owner-dogfood flag AND
      a resolved, loopback-bound, keyed `DirectSendEndpoint`.
  (c) DS-3 idempotency: reserve `cmid` atomically, before anything below it.
  (d) launch (or reuse) ONE background task per reserved cmid that runs, uncancelled, to a
      definitive conclusion or a genuinely ambiguous `pending` (see BLOCKER #1 below): DS-4's guard
      in order (in-process lock, Bot Chat resolution, lease-registry liveness, head precondition,
      all taken fresh INSIDE the lock), then DS-6's loopback call, then DS-7a's post-hoc check.
  (e) the calling coroutine (the HTTP handler) waits on that task up to `ADMISSION_WAIT_S`
      WITHOUT ever cancelling it, and answers `202 submitted` on timeout -- the task keeps running
      and still finalizes the store row whenever it actually concludes.

**Review round 2, BLOCKER #1 (idempotency/timeout), fixed here.** Round 1 bounded the loopback
call itself with `asyncio.wait_for`, which *cancels* the underlying request on timeout. Hermes does
not stop running the turn when the HTTP call to it is cancelled: `api_server`'s own
`_handle_session_chat` runs `_run_agent` through `loop.run_in_executor`, and that worker thread is
explicitly left running after the submitting coroutine is cancelled (`api_server_runs.py`'s own
`_submit_api_worker`, `api_server.py`'s `_run_agent`) -- confirmed directly against the pinned
Hermes checkout (`8afaab3703e336d72a72c812dd2dd249f04f166a`). Cancelling our own wait therefore
does not stop Hermes; it only stops US from ever recording what Hermes actually did. The fix: the
guard-plus-call-plus-finalize sequence now runs as an independent `asyncio.Task`
(`_execute`, launched by `handle_direct_send` and tracked in `PendingSendTasks`) that nothing in
this module ever cancels. The HTTP-handling coroutine awaits it through
`asyncio.wait_for(asyncio.shield(task), ADMISSION_WAIT_S)`: `shield` means a timeout on the OUTER
wait never touches the inner task, which keeps running to whatever conclusion it reaches and always
finalizes the same idempotency row exactly once. A retry with the same `cmid` never calls the
network again (`store.reserve_cmid`'s `inserted` flag): if this process still tracks the task, the
retry awaits that same task; if the row is `unknown`, or it is still `pending` but no task is
tracked (restart), the retry reports `unknown` -- the same state DS-8 reports -- and does not
resend. Review round 3: cancel, or any exception before a definitive finalize, stores `unknown`
(never left `pending`). `HmpServer.stop` cancels and awaits these tasks, bounded.

Any HTTP response Hermes actually returns -- 401 included -- closes the row (`accepted` or
`rejected`). A connection failure or socket timeout (`aiohttp.ClientError`/`TimeoutError`) stores
`unknown` and is not resent. A task that is still running stays `pending` until it concludes.

The DS-4(1) in-process lock is now held for the ENTIRE guarded sequence (guard through the loopback
call), not just the pre-call guard checks, and `expected_head` is read fresh INSIDE it (never the
pre-lock snapshot two concurrent in-process attempts could otherwise both have read before either
serialized against the other). The lock's own acquisition is bounded (`LOCK_WAIT_S`, documented
below): a turn stuck holding it cannot block a queued second send forever -- that send gets
`session_busy` (retryable) once the bound elapses, rather than waiting indefinitely.

**Review round 2, BLOCKER #4 (post-hoc interleave), fixed here.** Round 1's check compared row
COUNTS (a >32 heuristic). This module now performs the identity check `HMP_V1.md`'s DS-7a itself
describes: it reads the rows committed after `expected_head` (via `ReadBridge.after`, on the
loopback response's own `effective_session_id` when a turn-start compaction rotated it during this
very call) and passes only when the first row is HMP's own user row -- exact text, a bounded
timestamp window around the call -- and no OTHER user row appears before HMP's own assistant reply
is found in that same read (tool/assistant rows belonging to our own turn are allowed; a later,
unrelated turn's rows, appended only after ours settled, are never examined -- the scan stops at
our own reply). See `_check_interleave`'s own docstring for the exact rule and its residual.
"""

from __future__ import annotations

import hashlib
import json
import logging
import socket
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

import aiohttp

from . import gate as gate_module
from .contract import (
    ADMISSION_WAIT_S,
    BotChatTarget,
    CmidStatus,
    ConversationRef,
    DirectSendEndpoint,
    DirectSendOutcome,
    DirectSendRequest,
    ErrorCode,
    GuardFailure,
    ReadBridge,
    ResetReason,
    WriteGate,
    WriteGateState,
)
from .logging_policy import log_bridge_exception, log_event

log = logging.getLogger("hmp.direct_send")

# Silences the client-side aiohttp loggers HMP's own loopback call could otherwise trip (review
# round 2, BLOCKER #3): aiohttp can log request/response details, including headers, from
# `aiohttp.client` at DEBUG under a sufficiently verbose root logger configuration. The Bearer
# token for `api_server` travels in exactly such a header (DS-6). This is set at import time, once,
# rather than per call, since it is a fixed policy, not something any request can legitimately need
# to change.
logging.getLogger("aiohttp.client").setLevel(logging.WARNING)
logging.getLogger("aiohttp.internal").setLevel(logging.WARNING)

# Review round 3: the connect itself is the loopback verification (no separate probe). Short,
# like the old probe — a local listener accepts immediately. The turn body stays unbounded
# (`total=None`); admission timeout does not cancel this request.
LOOPBACK_CONNECT_TIMEOUT_S = 0.5
# Review round 2, BLOCKER #1: the bound on how long a send will wait to acquire the DS-4(1)
# in-process lock before giving up and answering `session_busy` -- deliberately shorter than
# `ADMISSION_WAIT_S` so a stuck earlier turn's lock contention is reported to a queued second send
# well before that send's own outer wait would time out anyway.
LOCK_WAIT_S = 3.0
# DS-7a: the read window for the post-hoc identity check -- generous enough to cover a normal
# turn's own tool-call rows between the user message and the final assistant reply.
_INTERLEAVE_READ_LIMIT = 64
# Page until our reply is found, bounded. 16 pages x 64 rows.
_INTERLEAVE_MAX_PAGES = 16
_INTERLEAVE_CLEAN = "clean"
_INTERLEAVE_DETECTED = "detected"
_INTERLEAVE_UNVERIFIED = "unverified"
# DS-7a: the timestamp tolerance around the call for matching HMP's own user row. Both sides are
# timestamps taken on this same host (Hermes's own row timestamp vs. this call's own clock), so
# this is generous headroom for DB/queueing latency, not a cross-host clock-skew allowance.
_INTERLEAVE_TIMESTAMP_WINDOW_S = 120


@dataclass(frozen=True)
class LoopbackResult:
    """DS-6's raw call outcome, before DS-7 maps it onto the wire."""

    status: int
    body: Mapping[str, object] | None
    effective_session_id: str | None


LoopbackCall = Callable[[DirectSendEndpoint, str, str], Awaitable[LoopbackResult]]


def _format_host(host: str) -> str:
    """A URL-safe host component: an IPv6 literal must be bracketed (`[::1]`), an IPv4 literal is
    used as-is. Review round 2, BLOCKER #3: `bridge.py` only ever hands this function `127.0.0.1`
    or `::1` (never a name), but an unbracketed `::1` is not a valid HTTP authority at all."""
    return f"[{host}]" if ":" in host else host


class _PinnedLoopbackResolver(aiohttp.abc.AbstractResolver):
    """Resolve every name to one literal loopback address. The URL is already that literal;
    this is what stops a resolver, a cache, or a later redirect from opening any other address.
    No DNS."""

    def __init__(self, address: str) -> None:
        self._address = address
        self._family = socket.AF_INET6 if ":" in address else socket.AF_INET

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[aiohttp.abc.ResolveResult]:
        del host, family  # the pin is the address bridge.py already checked, not the URL token
        return [
            {
                "hostname": self._address,
                "host": self._address,
                "port": port,
                "family": self._family,
                "proto": 0,
                "flags": socket.AI_NUMERICHOST,
            }
        ]

    async def close(self) -> None:
        return None


async def aiohttp_loopback_call(
    endpoint: DirectSendEndpoint, live_tip_session_id: str, text: str
) -> LoopbackResult:
    """DS-6: `POST [/p/<profile>]/api/sessions/{id}/chat`, body `{"message": text}`, bearer
    `endpoint.api_key`, pinned to the resolved loopback literal `bridge.py` already positively
    determined -- never a hostname, never a proxy. `trust_env=False` is the whole point: no
    `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` is ever read, so the Bearer token cannot leave the host
    through a configured proxy (review round-1 finding #6). `await`ed directly on this coroutine --
    no `asyncio.to_thread` -- this is genuine async socket I/O, not blocking work.

    Review round 3: this request is the loopback verification. The connector's resolver returns
    only `endpoint.host` (the literal), with a short connect timeout. A refused or timed-out
    connect raises `aiohttp.ClientError` / `TimeoutError`, which the caller maps to
    `api_server_unavailable`. There is no earlier probe connection.

    Review round 2, should-fix (path quoting): `live_tip_session_id` is a Hermes-internal id, never
    caller-controlled, but is still quoted defensively -- this loopback call is the one place HMP
    ever builds a URL path from a value it did not itself construct end-to-end."""
    from urllib.parse import quote

    host = _format_host(endpoint.host)
    session_segment = quote(live_tip_session_id, safe="")
    url = f"http://{host}:{endpoint.port}{endpoint.path_prefix}/api/sessions/{session_segment}/chat"
    timeout = aiohttp.ClientTimeout(
        total=None, connect=LOOPBACK_CONNECT_TIMEOUT_S, sock_connect=LOOPBACK_CONNECT_TIMEOUT_S
    )
    connector = aiohttp.TCPConnector(
        resolver=_PinnedLoopbackResolver(endpoint.host), use_dns_cache=False
    )
    async with (
        aiohttp.ClientSession(trust_env=False, timeout=timeout, connector=connector) as session,
        session.post(
            url,
            json={"message": text},
            headers={"Authorization": f"Bearer {endpoint.api_key}"},
        ) as resp,
    ):
        status = resp.status
        try:
            body = await resp.json(content_type=None)
        except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
            body = None
    effective_session_id = None
    if isinstance(body, Mapping):
        raw_effective = body.get("session_id")
        effective_session_id = raw_effective if isinstance(raw_effective, str) else None
    return LoopbackResult(
        status=status,
        body=body if isinstance(body, Mapping) else None,
        effective_session_id=effective_session_id,
    )


def _payload_hash(text: str, expected_head: int | None) -> bytes:
    """DS-3: `SHA-256` over the canonical `(text, expected_head)`. No message text is ever stored
    -- only this digest (SEC-4)."""
    canonical = json.dumps([text, expected_head], separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def _refuse(code: ErrorCode, *, retryable: bool) -> DirectSendError:
    log_event("direct_send", outcome=code.value)  # the refusal code only, never content (SEC-4)
    return DirectSendError(GuardFailure(code=code, retryable=retryable))


def _is_live_mailbox_owner(entry: Mapping[str, object], live_tip_session_id: str) -> bool:
    """OD-F14: Desktop's live Bot Chat owner is not a competing writer. Hermes's own
    `_admit_to_live_bot_chat` (api_server.py) hands a session-chat turn to that owner's mailbox
    when the owner's lease is on the canonical Bot Chat's compression tip and advertises
    `bot_live_delivery_consumer` with a `live_session_id` (tools/bot_live_delivery.py
    `find_canonical_live_owner`), so Desktop stays the single writer. Only that exact lease is
    exempt; any other lease on the lineage, or this one on a non-tip id (where the mailbox would
    not admit), still means busy."""
    meta = entry.get("metadata")
    return (
        isinstance(meta, Mapping)
        and meta.get("bot_live_delivery_consumer") is True
        and bool(meta.get("live_session_id"))
        and entry.get("session_id") == live_tip_session_id
    )


class DirectSendError(Exception):
    """Raised for every non-accepted outcome; carries the `GuardFailure` the route handler maps
    onto DS-7's response table (`server.py`)."""

    def __init__(self, failure: GuardFailure) -> None:
        super().__init__(failure.code.value)
        self.failure = failure


class _LockEntry:
    """One profile lock plus how many callers have been handed it and not yet released it."""

    __slots__ = ("lock", "refs")

    def __init__(self, lock: object) -> None:
        self.lock = lock
        self.refs = 0


def _lock_busy(lock: object) -> bool:
    """Held, or has waiters. A handed-out-but-not-yet-acquired lock is covered by the refcount,
    not by `locked()` (which is still false in that window)."""
    import asyncio

    if not isinstance(lock, asyncio.Lock):
        return True
    if lock.locked():
        return True
    waiters = getattr(lock, "_waiters", None)
    return bool(waiters)


class ProfileLocks:
    """DS-4(1): an in-process lock keyed by `(profile, lineage root id)`, serializing HMP's own
    concurrent attempts against each other. The root is stable across compression; the pre-lock
    tip is not (a compaction between two resolves would otherwise install a second lock). Says
    nothing about a writer outside HMP's own process -- DS-4(2)/(3) cover that. Import `asyncio`
    lazily inside the method that needs a lock object, so this class is constructible (and
    testable) without an event loop running yet.

    Bounded to `max_entries` (an `OrderedDict` LRU). An entry is evicted only when it is not
    held, has no waiters, AND its refcount is zero (handed out by `get` and not yet
    `release_ref`'d). Otherwise the table may sit above the bound until those calls finish."""

    def __init__(self, max_entries: int = 4096) -> None:
        self._max = max_entries
        self._locks: OrderedDict[tuple[str, str], _LockEntry] = OrderedDict()

    def get(self, profile: str, lineage_root_id: str) -> object:
        import asyncio

        key = (profile, lineage_root_id)
        entry = self._locks.get(key)
        if entry is None:
            entry = _LockEntry(asyncio.Lock())
            self._locks[key] = entry
        else:
            self._locks.move_to_end(key)
        entry.refs += 1
        self._evict()
        return entry.lock

    def release_ref(self, profile: str, lineage_root_id: str) -> None:
        """The caller is done with the object `get` returned (whether or not it acquired it)."""
        entry = self._locks.get((profile, lineage_root_id))
        if entry is None:
            return
        entry.refs = max(0, entry.refs - 1)

    def _evict(self) -> None:
        while len(self._locks) > self._max:
            for key in list(self._locks.keys()):
                entry = self._locks[key]
                if entry.refs > 0 or _lock_busy(entry.lock):
                    continue
                del self._locks[key]
                break
            else:
                break  # every entry is held, waited on, or still handed out


class PendingSendTasks:
    """Review round 2, BLOCKER #1: the in-process registry of currently-running background send
    tasks, keyed by the reserved cmid's own scope `(iid, user_id, profile, cmid)`. Populated when a
    task is launched, evicted once it finishes (whatever the outcome). Empty after a process
    restart by construction (a fresh object) -- that absence is exactly what lets a same-cmid POST
    retry and the DS-8 lookup route (`server.py`) tell "still running in THIS process" from "this
    process has no memory of it" apart, without any extra bookkeeping or persisted state."""

    def __init__(self) -> None:
        self._tasks: dict[tuple[str, str, str, str], object] = {}

    def put(self, key: tuple[str, str, str, str], task: object) -> None:
        self._tasks[key] = task

    def get(self, key: tuple[str, str, str, str]) -> object | None:
        return self._tasks.get(key)

    def discard(self, key: tuple[str, str, str, str], task: object) -> None:
        if self._tasks.get(key) is task:
            del self._tasks[key]

    async def cancel_and_wait(self, bound_s: float) -> None:
        """Cancel every live send and wait up to `bound_s` seconds for them to finish. A task
        that swallows cancellation does not extend the wait. `HmpServer.stop` is the caller."""
        import asyncio

        pending = [
            task
            for task in self._tasks.values()
            if isinstance(task, asyncio.Task) and not task.done()
        ]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=bound_s)


@dataclass(frozen=True)
class DirectSendDeps:
    """Everything `handle_direct_send` needs, injected so it never imports a Hermes internal or a
    real network client at test time (mirrors `reads.py`'s own `ReadBridge`-injection style)."""

    bridge: ReadBridge
    store: object  # `store.Store`; typed as `object` to avoid an import cycle in this module
    locks: ProfileLocks
    now: Callable[[], int]
    loopback_call: LoopbackCall = aiohttp_loopback_call
    tasks: PendingSendTasks = field(default_factory=PendingSendTasks)


def _cmid_key(iid: str, user_id: str, profile: str, cmid: str) -> tuple[str, str, str, str]:
    return (iid, user_id, profile, cmid)


def _stored_outcome(result_json: str) -> DirectSendOutcome:
    return DirectSendOutcome(**json.loads(result_json))


async def handle_direct_send(
    deps: DirectSendDeps,
    *,
    iid: str,
    user_id: str,
    profile: str,
    request: DirectSendRequest,
    flag_enabled: bool,
    base_write_gate: WriteGate,
) -> DirectSendOutcome:
    """DS-2..DS-8. Raises `DirectSendError` for every non-`200`/`202` outcome; the route handler
    (`server.py`) maps `DirectSendError.failure` onto DS-7's response table."""
    import asyncio

    if request.expected_head is None:
        raise _refuse(ErrorCode.BAD_REQUEST, retryable=False)

    # DS-2(b): the gate. `direct_send_endpoint` is resolved whenever it might matter: the guarded
    # path needs it whenever the owner-dogfood flag is on, including a genuinely OPEN base
    # gate: the DS-6 loopback is the only implemented delivery mechanism. An off flag makes no
    # endpoint or Hermes call. Off the event loop: this read can hydrate a secret source.
    endpoint: DirectSendEndpoint | None = None
    if flag_enabled:
        endpoint = await asyncio.to_thread(deps.bridge.direct_send_endpoint, profile)
    effective_gate = gate_module.direct_send_gate(
        base_write_gate=base_write_gate, flag_enabled=flag_enabled, endpoint=endpoint
    )
    if effective_gate.state not in (WriteGateState.OPEN, WriteGateState.OPEN_GUARDED):
        raise _refuse(ErrorCode.WRITE_GATE_CLOSED, retryable=False)
    if endpoint is None:  # defense in depth if gate semantics change later
        raise _refuse(ErrorCode.WRITE_GATE_CLOSED, retryable=False)

    # DS-3: reserve the cmid atomically, BEFORE anything below (round-1 review's timing BLOCKER).
    payload_hash = _payload_hash(request.text, request.expected_head)
    now = deps.now()
    record, inserted = await asyncio.to_thread(
        deps.store.reserve_cmid, iid, user_id, profile, request.client_message_id, payload_hash, now
    )
    if bytes(record["payload_hash"]) != payload_hash:
        raise _refuse(ErrorCode.IDEMPOTENCY_CONFLICT, retryable=False)

    key = _cmid_key(iid, user_id, profile, request.client_message_id)

    if not inserted:
        # A row already existed for this cmid before this call reserved anything.
        if record["status"] == CmidStatus.UNKNOWN.value:
            # Review round 3: same wire state DS-8 reports. Never a second loopback call.
            return DirectSendOutcome(state="unknown")
        if record["status"] != CmidStatus.PENDING.value:
            # DS-3: "the same payload replays the stored outcome and never hands off again."
            stored = record["result_json"]
            if record["status"] == CmidStatus.ACCEPTED.value and stored:
                return _stored_outcome(stored)
            raise _refuse(ErrorCode(_stored_code(stored)), retryable=False)
        # Still pending, and THIS call did not just create it -- NEVER call the network again.
        # Await the in-flight task, or, with no live task, report `unknown` (DS-8's state for
        # this row), never `submitted`.
        task = deps.tasks.get(key)
        if task is None:
            return DirectSendOutcome(state="unknown")
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=ADMISSION_WAIT_S)  # type: ignore[arg-type]
        except TimeoutError:
            return DirectSendOutcome(state="submitted")

    # `inserted` is True: this call owns the fresh reservation. The guard-plus-call-plus-finalize
    # sequence runs as an independent, server-owned background task (BLOCKER #1) that this
    # coroutine never cancels, even if it stops waiting on it below.
    task = asyncio.ensure_future(
        _execute(
            deps, iid=iid, user_id=user_id, profile=profile, request=request, endpoint=endpoint
        )
    )
    deps.tasks.put(key, task)
    task.add_done_callback(lambda t: _on_task_done(deps, key, t))
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=ADMISSION_WAIT_S)
    except TimeoutError:
        return DirectSendOutcome(state="submitted")


def _on_task_done(deps: DirectSendDeps, key: tuple[str, str, str, str], task: object) -> None:
    """Evicts the finished task from the registry and retrieves its exception (if any) so asyncio
    never logs an unretrieved-exception warning for a task nobody is still awaiting after the
    outer `wait_for` above already timed out. A `DirectSendError` is an expected, already-persisted
    guard outcome (`_execute` finalizes or releases the row before ever raising it) and is never
    logged again here; anything else is unexpected and goes through the normal exception logger."""
    import asyncio

    deps.tasks.discard(key, task)
    assert isinstance(task, asyncio.Task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None and not isinstance(exc, DirectSendError):
        log_bridge_exception(exc)


def _lineage_root(target: BotChatTarget) -> str:
    """Compression-lineage root. `compression_chain` is root-first; the tip is not a stable key."""
    if target.compression_chain:
        return target.compression_chain[0]
    return target.root_session_id


async def _execute(
    deps: DirectSendDeps,
    *,
    iid: str,
    user_id: str,
    profile: str,
    request: DirectSendRequest,
    endpoint: DirectSendEndpoint,
) -> DirectSendOutcome:
    """The DS-4 guard, DS-6's call and DS-7/DS-7a's finalize, run to a conclusion regardless of
    whether anyone is still awaiting this task. Every exit path finalizes the row
    (`accepted`/`rejected`/`unknown`) or releases it (a pre-call guard failure Hermes never saw).
    Cancel, or any exception before that, stores `unknown` -- never left `pending`."""
    import asyncio

    settled = False

    def _finalize(status: str, *, code: ErrorCode | None = None, outcome=None) -> None:
        nonlocal settled
        if settled:
            return
        settled = True
        result_json = None
        if outcome is not None:
            result_json = json.dumps(
                {
                    "state": outcome.state,
                    "message_id": outcome.message_id,
                    "head_message_id": outcome.head_message_id,
                    "reply": outcome.reply,
                    "interleave_detected": outcome.interleave_detected,
                }
            )
        elif code is not None:
            result_json = json.dumps({"code": code.value})
        deps.store.finalize_cmid(
            iid,
            user_id,
            profile,
            request.client_message_id,
            status=status,
            result_json=result_json,
            updated_at=deps.now(),
        )

    def _finalize_unknown() -> None:
        nonlocal settled
        if settled:
            return
        settled = True
        deps.store.finalize_cmid(
            iid,
            user_id,
            profile,
            request.client_message_id,
            status=CmidStatus.UNKNOWN.value,
            result_json=json.dumps({"state": "unknown"}),
            updated_at=deps.now(),
        )

    def _release() -> None:
        """HMP is CERTAIN no loopback call was attempted (a pre-call guard failure) -- release the
        reservation entirely (a real delete) so a plain retry under the SAME cmid reserves fresh."""
        nonlocal settled
        if settled:
            return
        settled = True
        deps.store.delete_cmid_reservation(iid, user_id, profile, request.client_message_id)

    try:
        if endpoint is None:
            # Defensive only: the gate's OPEN_GUARDED branch always resolves one. Fails closed
            # rather than handing `None` to `deps.loopback_call`.
            _release()
            raise _refuse(ErrorCode.API_SERVER_UNAVAILABLE, retryable=True)

        # DS-4(2): resolve the canonical Bot Chat. A read failure, including an uncertain
        # compression lineage, fails closed as session_busy (Hermes never saw this attempt).
        try:
            target = await asyncio.to_thread(deps.bridge.resolve_bot_chat, profile)
        except Exception as exc:
            log_bridge_exception(exc)
            await asyncio.to_thread(_release)
            raise _refuse(ErrorCode.SESSION_BUSY, retryable=True) from exc
        if target is None:
            await asyncio.to_thread(
                _finalize, CmidStatus.REJECTED.value, code=ErrorCode.NO_BOT_CHAT
            )
            raise _refuse(ErrorCode.NO_BOT_CHAT, retryable=False)

        root_id = _lineage_root(target)
        lock = deps.locks.get(profile, root_id)
        acquired = False
        try:
            try:
                await asyncio.wait_for(lock.acquire(), timeout=LOCK_WAIT_S)  # type: ignore[union-attr]
            except TimeoutError:
                # A stuck earlier turn cannot block this queued send forever. Hermes never saw it.
                await asyncio.to_thread(_release)
                raise _refuse(ErrorCode.SESSION_BUSY, retryable=True) from None
            acquired = True
            try:
                # `expected_head` is taken fresh, INSIDE the lock.
                try:
                    fresh = await asyncio.to_thread(deps.bridge.resolve_bot_chat, profile)
                except Exception as exc:
                    log_bridge_exception(exc)
                    await asyncio.to_thread(_release)
                    raise _refuse(ErrorCode.SESSION_BUSY, retryable=True) from exc
                if fresh is None:
                    await asyncio.to_thread(
                        _finalize, CmidStatus.REJECTED.value, code=ErrorCode.NO_BOT_CHAT
                    )
                    raise _refuse(ErrorCode.NO_BOT_CHAT, retryable=False)

                snapshot = await asyncio.to_thread(deps.bridge.lease_snapshot, profile)
                chain = set(fresh.compression_chain)
                busy = snapshot is None
                if not busy:
                    for entry in snapshot:
                        leased_session_id = entry.get("session_id")
                        if isinstance(leased_session_id, str) and leased_session_id in chain:
                            if _is_live_mailbox_owner(entry, fresh.live_tip_session_id):
                                continue
                            busy = True
                            break
                if busy:
                    await asyncio.to_thread(_release)
                    raise _refuse(ErrorCode.SESSION_BUSY, retryable=True)

                if fresh.head_message_id != request.expected_head:
                    await asyncio.to_thread(
                        _finalize, CmidStatus.REJECTED.value, code=ErrorCode.STALE_HEAD
                    )
                    raise _refuse(ErrorCode.STALE_HEAD, retryable=False)

                sent_at = deps.now()
                try:
                    result = await deps.loopback_call(
                        endpoint, fresh.live_tip_session_id, request.text
                    )
                except (TimeoutError, aiohttp.ClientError) as exc:
                    log_bridge_exception(exc)
                    # No HTTP response. Store `unknown` (never left pending, never resent).
                    await asyncio.to_thread(_finalize_unknown)
                    raise _refuse(ErrorCode.API_SERVER_UNAVAILABLE, retryable=True) from exc
            finally:
                if acquired:
                    lock.release()  # type: ignore[union-attr]
        finally:
            deps.locks.release_ref(profile, root_id)

        # Hermes answered with a real HTTP status. Every branch below closes the row.
        if result.status == 401:
            await asyncio.to_thread(
                _finalize, CmidStatus.REJECTED.value, code=ErrorCode.WRITE_GATE_CLOSED
            )
            raise _refuse(ErrorCode.WRITE_GATE_CLOSED, retryable=False)
        if result.status not in (200, 202):
            await asyncio.to_thread(
                _finalize, CmidStatus.REJECTED.value, code=ErrorCode.API_SERVER_UNAVAILABLE
            )
            raise _refuse(ErrorCode.API_SERVER_UNAVAILABLE, retryable=False)
        if result.status == 202:
            outcome = DirectSendOutcome(state="queued")
            await asyncio.to_thread(_finalize, CmidStatus.ACCEPTED.value, outcome=outcome)
            return outcome

        body = result.body or {}
        message = body.get("message") if isinstance(body, Mapping) else None
        reply = message if isinstance(message, Mapping) else None
        message_id = _extract_message_id(reply)
        reply_content = reply.get("content") if isinstance(reply, Mapping) else None
        reply_text = reply_content if isinstance(reply_content, str) else None

        try:
            refreshed = await asyncio.to_thread(deps.bridge.resolve_bot_chat, profile)
        except Exception as exc:
            log_bridge_exception(exc)
            refreshed = None
        session_for_check = result.effective_session_id or (
            refreshed.live_tip_session_id if refreshed is not None else fresh.live_tip_session_id
        )
        interleave_detected = await asyncio.to_thread(
            _check_interleave,
            deps.bridge,
            profile=profile,
            user_id=user_id,
            session_id=session_for_check,
            after_id=fresh.head_message_id or 0,
            request_text=request.text,
            reply_text=reply_text,
            sent_at=sent_at,
        )

        outcome = DirectSendOutcome(
            state="accepted",
            message_id=message_id,
            head_message_id=refreshed.head_message_id if refreshed is not None else None,
            reply=reply,
            interleave_detected=interleave_detected,
        )
        await asyncio.to_thread(_finalize, CmidStatus.ACCEPTED.value, outcome=outcome)
        return outcome
    except asyncio.CancelledError:
        # Sync: a cancelled task cannot reliably await. The row must not stay pending.
        _finalize_unknown()
        raise
    except DirectSendError:
        raise
    except Exception:
        _finalize_unknown()
        raise


def _owns_user_row(row: object, request_text: str, sent_at: int) -> bool:
    return (
        getattr(row, "role", None) == "user"
        and getattr(row, "text", None) == request_text
        and abs(int(getattr(row, "created_at", 0)) - sent_at) <= _INTERLEAVE_TIMESTAMP_WINDOW_S
    )


def _reply_index(rows: list, reply_text: str | None, start: int) -> int | None:
    if reply_text is None:
        return None
    for i in range(start, len(rows)):
        row = rows[i]
        if getattr(row, "role", None) == "assistant" and getattr(row, "text", None) == reply_text:
            return i
    return None


def _read_after_pages(
    bridge: ReadBridge, ref: ConversationRef, after_id: int, reply_text: str | None
):
    """Rows strictly after `after_id`, paging until the reply is found or the page bound is hit.
    A `ResetReason` is returned as soon as one page reports it. Raises on a read failure."""
    rows: list = []
    cursor = after_id
    for _ in range(_INTERLEAVE_MAX_PAGES):
        page = bridge.after(ref, cursor, _INTERLEAVE_READ_LIMIT)
        if isinstance(page, ResetReason):
            return page
        if not isinstance(page, list) or not page:
            break
        rows.extend(page)
        if _reply_index(rows, reply_text, 0) is not None:
            break
        if len(page) < _INTERLEAVE_READ_LIMIT:
            break
        last_id = getattr(page[-1], "id", None)
        if not isinstance(last_id, int) or last_id <= cursor:
            break
        cursor = last_id
    return rows


def _post_compaction_ref(bridge: ReadBridge, ref: ConversationRef) -> ConversationRef | None:
    """The transcript to re-read after a reset: `lineage().lineage_tip` when the bridge has it,
    otherwise the caller's session (already `effective_session_id` or the live tip). `None` when
    a lineage read was attempted and could not be trusted."""
    lineage = getattr(bridge, "lineage", None)
    if not callable(lineage):
        return ref
    try:
        info = lineage(ref)
    except Exception as exc:
        log_bridge_exception(exc)
        return None
    tip = getattr(info, "lineage_tip", None)
    if not isinstance(tip, str) or not tip:
        return None
    if tip == ref.session_id:
        return ref
    return ConversationRef(user_id=ref.user_id, profile=ref.profile, session_id=tip)


def _verdict_on_cursor(rows: list, request_text: str, reply_text: str | None, sent_at: int) -> str:
    """Identity rule on a stable cursor: the first row after `expected_head` must be our user row,
    and no other user row appears before our reply. Pages until the reply is in the read."""
    if not rows:
        return _INTERLEAVE_DETECTED
    first = rows[0]
    if not _owns_user_row(first, request_text, sent_at):
        return _INTERLEAVE_DETECTED
    if reply_text is None:
        return _INTERLEAVE_DETECTED
    reply_idx = _reply_index(rows, reply_text, 0)
    if reply_idx is None:
        return _INTERLEAVE_DETECTED  # bounded pages exhausted, reply still absent
    window = rows[1 : reply_idx + 1]
    if any(getattr(row, "role", None) == "user" for row in window):
        return _INTERLEAVE_DETECTED
    return _INTERLEAVE_CLEAN


def _verdict_on_rewritten(
    rows: list, request_text: str, reply_text: str | None, sent_at: int
) -> str:
    """Same identity rule on a post-compaction transcript: find our user row by text and
    timestamp (it is not necessarily the first row of the rewritten history), then no other user
    row before our reply. If that cannot be established, unverified -- not an interleave."""
    user_idx = next(
        (i for i, row in enumerate(rows) if _owns_user_row(row, request_text, sent_at)),
        None,
    )
    if user_idx is None or reply_text is None:
        return _INTERLEAVE_UNVERIFIED
    reply_idx = _reply_index(rows, reply_text, user_idx)
    if reply_idx is None:
        return _INTERLEAVE_UNVERIFIED
    window = rows[user_idx + 1 : reply_idx + 1]
    if any(getattr(row, "role", None) == "user" for row in window):
        return _INTERLEAVE_DETECTED
    return _INTERLEAVE_CLEAN


def _interleave_verdict(
    bridge: ReadBridge,
    *,
    profile: str,
    user_id: str,
    session_id: str,
    after_id: int,
    request_text: str,
    reply_text: str | None,
    sent_at: int,
) -> str:
    ref = ConversationRef(user_id=user_id, profile=profile, session_id=session_id)
    try:
        rows = _read_after_pages(bridge, ref, after_id, reply_text)
    except Exception as exc:
        log_bridge_exception(exc)
        return _INTERLEAVE_DETECTED
    if isinstance(rows, ResetReason):
        # In-place compaction (or any reset) is not itself an interleave. Re-read the
        # post-compaction transcript and apply the same identity rule.
        reread_ref = _post_compaction_ref(bridge, ref)
        if reread_ref is None:
            return _INTERLEAVE_UNVERIFIED
        try:
            rewritten = _read_after_pages(bridge, reread_ref, 0, reply_text)
        except Exception as exc:
            log_bridge_exception(exc)
            return _INTERLEAVE_UNVERIFIED
        if isinstance(rewritten, ResetReason) or not rewritten:
            return _INTERLEAVE_UNVERIFIED
        return _verdict_on_rewritten(rewritten, request_text, reply_text, sent_at)
    if not isinstance(rows, list):
        return _INTERLEAVE_DETECTED
    return _verdict_on_cursor(rows, request_text, reply_text, sent_at)


def _check_interleave(
    bridge: ReadBridge,
    *,
    profile: str,
    user_id: str,
    session_id: str,
    after_id: int,
    request_text: str,
    reply_text: str | None,
    sent_at: int,
) -> bool:
    """DS-7a identity check. Returns True only for a detected foreign user row.

    A `ResetReason` from `bridge.after` (in-place compaction sets the anchor `active=0`, so
    `after` returns `HISTORY_REWRITTEN`; any other reset is the same) does not by itself set the
    flag. The check re-reads the post-compaction transcript (`lineage().lineage_tip` when the
    bridge exposes it, otherwise `session_id`, which the caller set from `effective_session_id`)
    and applies the same text/timestamp/role rule. If that re-read cannot be done, the result is
    unverified: `interleave_detected` stays false and `direct_send` / `interleave_unverified` is
    logged.

    The read pages (`_INTERLEAVE_READ_LIMIT` rows at a time, at most `_INTERLEAVE_MAX_PAGES`)
    until our reply is found. A reply past the first page is not an interleave.

    On a stable cursor, a read failure, a missing first row, or a reply still absent after the
    page bound fails safe to True. Rows after our matched reply are not examined.

    Residual: `session_chat` stores no per-message client id, so two identical texts inside the
    timestamp window are not distinguishable. DS-3 keeps HMP itself from being that collision."""
    verdict = _interleave_verdict(
        bridge,
        profile=profile,
        user_id=user_id,
        session_id=session_id,
        after_id=after_id,
        request_text=request_text,
        reply_text=reply_text,
        sent_at=sent_at,
    )
    if verdict == _INTERLEAVE_UNVERIFIED:
        log_event("direct_send", outcome="interleave_unverified")
        return False
    return verdict == _INTERLEAVE_DETECTED


def _extract_message_id(reply: Mapping[str, object] | None) -> int | None:
    if reply is None:
        return None
    raw = reply.get("id") or reply.get("message_id")
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else None


def _stored_code(stored: str | None) -> str:
    if not stored:
        return ErrorCode.OTHER.value
    try:
        data = json.loads(stored)
    except (TypeError, ValueError):
        return ErrorCode.OTHER.value
    code = data.get("code") if isinstance(data, Mapping) else None
    return code if isinstance(code, str) else ErrorCode.OTHER.value
