"""Approvals and Phone chat (`HMP_V1.md` §7b, amendment F3; spec 034).

Prompt rows are process memory (AP-2). This module does not import Hermes. Loopback approval
POSTs and `resolve_gateway_*` are injected. `adapter.py` reaches the hooks through the object
`connect` builds; it does not import `tools.approval`.

Each listener open builds a new `PromptStore`: that is the prompt generation. A store that has been
`close`d (listener stop) or whose Phone-chat side was closed by the binding fence (AP-10) refuses
new rows, so a stream or hook bound to an older generation can never surface a row in a newer one.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import itertools
import json
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from .contract import IDEMPOTENCY_RETENTION_S
from .logging_policy import log_event

APPROVAL_CHOICES = ("once", "session", "always", "deny")
_RECOMMENDED_SUFFIX = "(Recommended)"
_REQUEST_ID_MAX = 256
EXPIRY_GRACE_S = 30
OBSERVATION_TTL_S = 60
OBSERVATION_CAP = 256
OBSERVATION_MAX_BYTES = 8192


class HelperUnavailableError(RuntimeError):
    """A Hermes helper HMP calls failed to import, resolve or accept its call at use time
    (`ImportError`, `AttributeError` or `TypeError`), or is not bound. Fixed text; never carries
    Hermes-provided data (AP-7a)."""


class HelperChangedError(HelperUnavailableError):
    """A bound Hermes helper is no longer the object HMP captured (AP-10)."""


def _log(event: str, outcome: str, **ids: str) -> None:
    safe = {
        name: value
        for name, value in ids.items()
        if isinstance(value, str) and len(value) >= 8
    }
    log_event(event, outcome=outcome, **safe)


def strip_recommended(label: str) -> str:
    """The suffix Hermes adds to the first clarify choice (`tools/clarify_tool.py`)."""
    text = label.strip()
    if text.casefold().endswith(_RECOMMENDED_SUFFIX.casefold()):
        return text[: -len(_RECOMMENDED_SUFFIX)].strip()
    return text


def _canonical_answer(body: Mapping[str, object]) -> bytes:
    kept = {
        key: body[key]
        for key in ("choice", "choices", "other", "text")
        if key in body
    }
    raw = json.dumps(kept, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).digest()


@dataclass
class PromptRow:
    """One answerable prompt. `session_key` and `run_id` never go on the wire."""

    iid: str
    user_id: str
    profile: str
    request_id: str
    kind: str  # "approval" | "clarify"
    surface: str  # "bot_chat" | "phone_chat"
    choices: tuple[str, ...]
    command: str | None = None
    description: str | None = None
    question: str | None = None
    multi_select: bool = False
    awaiting_text: bool = False
    expires_at: int | None = None
    observed_at: int = 0
    run_id: str | None = None
    session_key: str | None = None
    status: str = "open"  # open | resolved | expired
    answer_hash: bytes | None = None
    stored_status: int | None = None
    stored_body: dict[str, object] | None = None
    settled_at: int | None = None
    settle_cause: str | None = None  # process memory only; never on the wire or in a log


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: dict[str, object]


PromptKey = tuple[str, str, str, str]

# Why an approval row stopped being open (spec 015 NI-2.2). Only Hermes's own answer counts as
# authoritative: an applied answer, a native not-pending code, or a Hermes listing without the row.
SETTLE_AUTHORITATIVE = frozenset({"answer_applied", "native_not_pending", "phone_listing_omitted"})
SETTLE_NON_AUTHORITATIVE = frozenset({
    "local_expiry",
    "generation_closed",
    "binding_fence",
    "run_ended",
    "phone_not_resolved",
    "clarify_retired",
})


def is_authoritative(cause: object) -> bool:
    """True only for a recorded authoritative cause. `None` and unknown values are False."""
    return isinstance(cause, str) and cause in SETTLE_AUTHORITATIVE


@dataclass(frozen=True)
class ApprovalInserted:
    """One inserted approval row. No command, description, choices, run ID or session key."""

    key: PromptKey
    surface: str  # "bot_chat" | "phone_chat"
    generation: int
    expires_at: int | None


@dataclass(frozen=True)
class MemberState:
    bot_chat: bool
    phone_chat: bool


ALL_OPEN = MemberState(bot_chat=True, phone_chat=True)


def _freeze_wire(wire: Mapping[str, object] | None) -> Mapping[str, object] | None:
    """An owned, read-only copy of a `wire_prompt` body: a fresh dict whose `choices` (the only
    container `wire_prompt` emits) is a tuple, behind a `MappingProxyType`."""
    if wire is None:
        return None
    owned = dict(wire)
    choices = owned.get("choices")
    if isinstance(choices, (list, tuple)):
        owned["choices"] = tuple(item for item in choices)
    return MappingProxyType(owned)


@dataclass(frozen=True)
class RowView:
    """A frozen snapshot of one row. `wire` is excluded from equality and hash; every other
    field is immutable, so a view is hashable."""

    key: PromptKey
    kind: str
    surface: str
    generation: int
    status: str
    settle_cause: str | None
    expires_at: int | None
    held: bool
    open_now: bool
    hidden_now: bool
    visible_now: bool
    settled_at: int | None = None
    session_key: str | None = None
    wire: Mapping[str, object] | None = field(default=None, compare=False, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "wire", _freeze_wire(self.wire))


@dataclass(frozen=True)
class VisibleSet:
    held: bool
    rows: tuple[RowView, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))


# Generation tokens come from one process-wide counter advanced under its own lock, so stores
# built on different threads never share a token and nothing relies on the GIL.
_GENERATION_COUNTER = itertools.count(1)
_GENERATION_LOCK = threading.Lock()


def row_open_now(row: PromptRow, now: int) -> bool:
    """Spec 015 NI-6.1: still open at `now`. Exactly `purge`'s local-expiry rule, without the
    mutation: a stored `open` row past `expires_at + EXPIRY_GRACE_S` is not open now."""
    if row.status != "open":
        return False
    return not (row.expires_at is not None and now > row.expires_at + EXPIRY_GRACE_S)


def row_hidden_now(row: PromptRow, held: bool, members: MemberState) -> bool:
    """Spec 015 NI-6.1: Desktop-held Bot Chat, or the row's surface member is closed. Values only,
    whatever the row's status."""
    if row.surface == "bot_chat":
        return held or not members.bot_chat
    return not members.phone_chat


class PromptResolver(Protocol):
    async def resolve_approval(self, row: PromptRow, choice: str) -> str:
        """`accepted`, `stale`, or `unavailable`."""
        ...

    async def resolve_clarify(self, row: PromptRow, response: str) -> str:
        """`accepted`, `stale`, or `unavailable` (the Hermes helper failed at use time)."""
        ...

    async def mark_awaiting(self, row: PromptRow) -> str:
        """`ok`, `stale`, or `unavailable`."""
        ...


class DesktopOwnership(enum.Enum):
    """Closed HMP view of cross-surface Desktop ownership; no native record data crosses it."""

    OWNED = "owned"
    UNOWNED = "unowned"
    UNKNOWN = "unknown"


class DesktopOwnershipPort(Protocol):
    """Narrow seam for an already-authorized AP-3/AP-4 ownership decision."""

    @property
    def can_observe(self) -> bool:
        """Only the literal `True` permits observation-only profile/target resolution."""
        ...

    async def observe(
        self, *, profile: str, canonical_lineage: tuple[str, ...]
    ) -> DesktopOwnership:
        """Return one closed state. Implementations must not expose source metadata."""
        ...


class UnavailableDesktopOwnershipPort:
    """Safe production default until a separately accepted native provider exists."""

    can_observe = False

    async def observe(
        self, *, profile: str, canonical_lineage: tuple[str, ...]
    ) -> DesktopOwnership:
        return DesktopOwnership.UNKNOWN


class DesktopOwnershipCheck(Protocol):
    async def __call__(self, row: PromptRow) -> DesktopOwnership: ...


def _error(code: str, message: str, *, applied: bool | None = None) -> HttpResult:
    http = {"bad_request": 400, "not_found": 404, "stale": 409, "invalid_choice": 409,
            "idempotency_conflict": 409, "write_gate_closed": 503,
            "api_server_unavailable": 503}[code]
    body: dict[str, object] = {"error": {"code": code, "message": message}}
    if applied is not None:
        body["applied"] = applied
    return HttpResult(http, body)


def _unavailable() -> HttpResult:
    """An answer whose Hermes side could not settle it: `503`, no `applied`, the row stays open."""
    _log("prompt_answer", "unavailable")
    return _error("api_server_unavailable", "direct send delivery is unavailable")


def _not_found() -> HttpResult:
    return _error("not_found", "not found")


def _bad() -> HttpResult:
    return _error("bad_request", "malformed request")


class PromptStore:
    """Process-memory prompts, the desktop-held marker, and Phone-chat transcript observations."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        with _GENERATION_LOCK:
            self.generation: int = next(_GENERATION_COUNTER)
        self._guard = threading.Lock()
        self._rows: dict[tuple[str, str, str, str], PromptRow] = {}
        self._desktop: set[tuple[str, str, str]] = set()
        self._sessions: dict[str, tuple[str, str, str, str]] = {}
        self._suppressed: set[str] = set()
        self._observations: dict[tuple[str, str, str], list[tuple[str, str, float]]] = {}
        self._locks: dict[tuple[str, str, str, str], asyncio.Lock] = {}
        self._lock_users: dict[tuple[str, str, str, str], int] = {}
        self._phone_tasks: dict[tuple[str, str, str, str], asyncio.Task[HttpResult]] = {}
        # Generation fences. `closed`: this listener generation ended. `phone_closed`: the binding
        # fence (AP-10) closed the Phone-chat side of this generation. Both only ever go True.
        self.closed = False
        self.phone_closed = False
        # One synchronous insertion observer per generation (spec 015 NI-1.1). Read and written
        # only under `_guard`; called only after `_guard` is released.
        self._observer: Callable[[ApprovalInserted], None] | None = None

    def set_insertion_observer(self, observer: Callable[[ApprovalInserted], None] | None) -> None:
        """Register (or clear with `None`) the one insertion observer. Safe from any thread; a
        no-op once this generation is closed."""
        with self._guard:
            if self.closed:
                return
            self._observer = observer

    def close(self, now: int) -> None:
        """The listener that owned this generation stopped: expire everything, refuse new rows."""
        with self._guard:
            self.closed = True
            self._observer = None
            for row in self._rows.values():
                self.expire(row, now, cause="generation_closed")
            self._desktop.clear()
        _log("prompt_store", "closed")

    def close_phone_chat(self, now: int) -> None:
        """AP-10: a helper HMP bound is no longer the bound object. Invalidate HMP's own Phone-chat
        state for this generation. This says nothing about Hermes's pending request: nothing here
        reports native expiry. Bot Chat rows are untouched."""
        with self._guard:
            if self.phone_closed:
                return
            self.phone_closed = True
            for row in self._rows.values():
                if row.surface == "phone_chat":
                    self.expire(row, now, cause="binding_fence")
            self._sessions.clear()
            self._observations.clear()
        log_event("approval_binding", outcome="changed")

    @asynccontextmanager
    async def answer_row(self, key: tuple[str, str, str, str]) -> AsyncIterator[PromptRow | None]:
        # Pin the row AND lock before awaiting. Purge cannot split waiting answerers across locks.
        with self._guard:
            row = self._rows.get(key)
            lock = None
            if row is not None:
                lock = self._locks.setdefault(key, asyncio.Lock())
                self._lock_users[key] = self._lock_users.get(key, 0) + 1
        if lock is None:
            yield None
            return
        try:
            async with lock:
                yield row
        finally:
            with self._guard:
                self._lock_users[key] -= 1
                if not self._lock_users[key]:
                    del self._lock_users[key]

    @staticmethod
    def expire(row: PromptRow, now: int, *, cause: str) -> None:
        if row.status == "open":
            row.status = "expired"
            row.settled_at = now
            row.settle_cause = cause

    def settle_answer(self, row: PromptRow, *, status: str, cause: str, now: int) -> None:
        """The answer path's only writer of `status`, `settled_at` and `settle_cause`. It overwrites
        unconditionally, even a settlement another path made while the Hermes call was awaited
        (spec 015 RD-7), and reads no clock: `now` is the caller's pre-await sample."""
        with self._guard:
            row.status = status
            row.settled_at = now
            row.settle_cause = cause

    def expire_run(self, run_id: str, now: int) -> None:
        with self._guard:
            for row in self._rows.values():
                if row.run_id == run_id:
                    self.expire(row, now, cause="run_ended")

    def reconcile_approvals(self, session_key: str, pending: set[str], now: int) -> None:
        with self._guard:
            for row in self._rows.values():
                if (row.session_key == session_key and row.kind == "approval"
                        and row.request_id not in pending):
                    self.expire(row, now, cause="phone_listing_omitted")

    def get(self, key: tuple[str, str, str, str]) -> PromptRow | None:
        with self._guard:
            return self._rows.get(key)

    def purge(self, now: int) -> None:
        with self._guard:
            for row in self._rows.values():
                if row.expires_at is not None and now > row.expires_at + EXPIRY_GRACE_S:
                    self.expire(row, now, cause="local_expiry")
            stale = [
                key for key, row in self._rows.items()
                if self._retention_deleted_now(key, row, now)
            ]
            for key in stale:
                del self._rows[key]
                self._locks.pop(key, None)
            self._purge_observations(now)

    def _purge_observations(self, now: float) -> None:
        for key in list(self._observations):
            kept = [item for item in self._observations[key] if now - item[2] < OBSERVATION_TTL_S]
            if kept:
                self._observations[key] = kept
            else:
                del self._observations[key]

    def put(self, row: PromptRow) -> None:
        key = (row.iid, row.user_id, row.profile, row.request_id)
        with self._guard:
            if self.closed or (self.phone_closed and row.surface == "phone_chat"):
                return
            current = self._rows.get(key)
            if current is not None:
                return
            self._rows[key] = row
            observer = self._observer if row.kind == "approval" else None
        _log(
            "prompt_store",
            "stored",
            user_id=row.user_id,
            request_id=row.request_id,
            run_id=row.run_id or "",
        )
        if observer is not None:
            # Synchronous, on this thread, outside `_guard` (NI-1.3, NI-1.4). Only a callback
            # failure is contained: the call has no `await`, so a `CancelledError` raised here is
            # not the delivery of this task's own cancellation (RD-3). Every other
            # `BaseException` propagates with the row already stored.
            try:
                observer(ApprovalInserted(key, row.surface, self.generation, row.expires_at))
            except (Exception, asyncio.CancelledError):
                _log("prompt_observer", "error")

    def record_stream_approval(
        self,
        *,
        iid: str,
        user_id: str,
        profile: str,
        request_id: str,
        run_id: str,
        command: str,
        description: str,
        choices: tuple[str, ...],
        now: int,
        timeout_s: int,
    ) -> None:
        if not request_id or not run_id or not choices:
            _log("prompt_store", "unbound", user_id=user_id, request_id=request_id, run_id=run_id)
            return
        self.put(
            PromptRow(
                iid=iid,
                user_id=user_id,
                profile=profile,
                request_id=request_id,
                kind="approval",
                surface="bot_chat",
                choices=choices,
                command=command,
                description=description,
                expires_at=now + max(0, timeout_s),
                observed_at=now,
                run_id=run_id,
            )
        )

    def set_desktop_held(self, iid: str, user_id: str, profile: str) -> None:
        key = (iid, user_id, profile)
        with self._guard:
            if key in self._desktop:
                return
            self._desktop.add(key)
        _log("prompt_store", "desktop_held", user_id=user_id)

    def clear_desktop_held(self, iid: str, user_id: str, profile: str) -> None:
        with self._guard:
            self._desktop.discard((iid, user_id, profile))

    def desktop_held(self, iid: str, user_id: str, profile: str) -> bool:
        with self._guard:
            return (iid, user_id, profile) in self._desktop

    def remember_session(
        self, session_key: str, iid: str, user_id: str, profile: str, chat_id: str
    ) -> None:
        if not session_key:
            return
        with self._guard:
            if self.closed or self.phone_closed:
                return
            self._sessions[session_key] = (iid, user_id, profile, chat_id)

    def owner_of_session(self, session_key: str) -> tuple[str, str, str, str] | None:
        with self._guard:
            return self._sessions.get(session_key)

    def open_request_ids(self, session_key: str) -> set[str]:
        owner = self.owner_of_session(session_key)
        if owner is None:
            return set()
        iid, user_id, profile, _chat = owner
        with self._guard:
            return {
                row.request_id
                for row in self._rows.values()
                if row.status == "open"
                and (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
            }

    def open_clarifies(self, iid: str, user_id: str, profile: str) -> tuple[PromptRow, ...]:
        with self._guard:
            return tuple(
                row
                for row in self._rows.values()
                if row.status == "open"
                and row.kind == "clarify"
                and row.surface == "phone_chat"
                and (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
            )

    def owner_of_chat(self, iid: str, chat_id: str) -> tuple[str, str, str] | None:
        with self._guard:
            for stored_iid, user_id, profile, stored_chat in self._sessions.values():
                if stored_chat == chat_id and stored_iid == iid:
                    return stored_iid, user_id, profile
        return None

    def suppress_transcript(self, chat_id: str) -> None:
        with self._guard:
            self._suppressed.add(chat_id)

    def release_transcript(self, chat_id: str) -> None:
        with self._guard:
            self._suppressed.discard(chat_id)

    def transcript_suppressed(self, chat_id: str) -> bool:
        with self._guard:
            return chat_id in self._suppressed

    def add_observation(
        self, iid: str, user_id: str, profile: str, *, role: str, text: str, now: float
    ) -> None:
        if len(text.encode("utf-8")) > OBSERVATION_MAX_BYTES:
            return
        key = (iid, user_id, profile)
        with self._guard:
            if self.closed or self.phone_closed:
                return
            self._purge_observations(now)
            self._observations.setdefault(key, []).append((role, text, now))
            while sum(map(len, self._observations.values())) > OBSERVATION_CAP:
                oldest = min(self._observations, key=lambda k: self._observations[k][0][2])
                self._observations[oldest].pop(0)
                if not self._observations[oldest]:
                    del self._observations[oldest]

    def discard_durable_observations(
        self, iid: str, user_id: str, profile: str, durable: set[tuple[str, str]]
    ) -> None:
        key = (iid, user_id, profile)
        with self._guard:
            remaining = [item for item in self._observations.get(key, [])
                         if (item[0], item[1]) not in durable]
            if remaining:
                self._observations[key] = remaining
            else:
                self._observations.pop(key, None)

    def observations(
        self, iid: str, user_id: str, profile: str
    ) -> tuple[tuple[str, str, float], ...]:
        with self._guard:
            return tuple(self._observations.get((iid, user_id, profile), ()))

    def phone_task(self, key: tuple[str, str, str, str]) -> asyncio.Task[HttpResult] | None:
        with self._guard:
            return self._phone_tasks.get(key)

    def put_phone_task(
        self, key: tuple[str, str, str, str], task: asyncio.Task[HttpResult]
    ) -> None:
        with self._guard:
            self._phone_tasks[key] = task

    def drop_phone_task(
        self, key: tuple[str, str, str, str], task: asyncio.Task[HttpResult]
    ) -> None:
        with self._guard:
            if self._phone_tasks.get(key) is task:
                del self._phone_tasks[key]

    def _retention_deleted_now(
        self, key: PromptKey, row: PromptRow, now: int
    ) -> bool:
        """Spec 015 NI-6.1 / RD-11: the retention-delete conditions of `purge`, on stored values.
        The caller holds `_guard`. Nothing is deleted here."""
        return (
            row.settled_at is not None
            and now - row.settled_at >= IDEMPOTENCY_RETENTION_S
            and not self._lock_users.get(key)
        )

    def _visible_live_rows(
        self, iid: str, user_id: str, profile: str, now: int, members: MemberState
    ) -> tuple[bool, tuple[PromptRow, ...]]:
        """The held marker and the live rows visible now, read in one `_guard` section with no
        callable run under it (RD-9). Shared by `list_visible` and `list_prompts`."""
        with self._guard:
            held = (iid, user_id, profile) in self._desktop
            rows = tuple(
                row
                for row in self._rows.values()
                if (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
                and row_open_now(row, now)
                and not row_hidden_now(row, held, members)
            )
        return held, rows

    def list_visible(
        self, iid: str, user_id: str, profile: str, *, now: int | None = None
    ) -> tuple[PromptRow, ...]:
        """Live open rows for the RO-3 snapshot (a recorded residual: they are not snapshots).
        Purges, then delegates to the shared predicate with every member open (RD-8)."""
        at = int(self._clock()) if now is None else now
        self.purge(at)
        return self._visible_live_rows(iid, user_id, profile, at, ALL_OPEN)[1]

    def _view(
        self,
        row: PromptRow,
        held: bool,
        members: MemberState,
        now: int,
        include_wire: bool,
    ) -> RowView:
        """One frozen snapshot. The caller holds `_guard`; this reads row values only."""
        open_now = row_open_now(row, now)
        hidden_now = row_hidden_now(row, held, members)
        return RowView(
            key=(row.iid, row.user_id, row.profile, row.request_id),
            kind=row.kind,
            surface=row.surface,
            generation=self.generation,
            status=row.status,
            settle_cause=row.settle_cause,
            expires_at=row.expires_at,
            settled_at=row.settled_at,
            held=held,
            open_now=open_now,
            hidden_now=hidden_now,
            visible_now=open_now and not hidden_now,
            session_key=row.session_key if include_wire else None,
            wire=wire_prompt(row) if include_wire else None,
        )

    def view_row(self, key: PromptKey, *, now: int, members: MemberState) -> RowView | None:
        """A frozen view of one row, or `None` when it is missing or the next `purge(now)` would
        delete it (the pure retention mask, RD-11). Mutates nothing, calls nothing under `_guard`,
        and never exposes a session key or wire body (RD-12)."""
        with self._guard:
            row = self._rows.get(key)
            if row is None or self._retention_deleted_now(key, row, now):
                return None
            held = (key[0], key[1], key[2]) in self._desktop
            return self._view(row, held, members, now, False)

    def view_visible(
        self,
        iid: str,
        user_id: str,
        profile: str,
        *,
        now: int,
        members: MemberState,
        include_wire: bool = False,
    ) -> VisibleSet:
        """Every row of the triple in insertion order, open or not, minus retention-masked rows,
        with the held marker, all read in one `_guard` section. Mutates nothing. `wire` and
        `session_key` are populated only when `include_wire` is true (AP-3)."""
        with self._guard:
            held = (iid, user_id, profile) in self._desktop
            views = tuple(
                self._view(row, held, members, now, include_wire)
                for key, row in self._rows.items()
                if (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
                and not self._retention_deleted_now(key, row, now)
            )
        return VisibleSet(held=held, rows=views)


def wire_prompt(row: PromptRow) -> dict[str, object]:
    body: dict[str, object] = {
        "kind": row.kind,
        "surface": row.surface,
        "request_id": row.request_id,
        "expires_at": row.expires_at,
    }
    if row.kind == "approval":
        body["choices"] = list(row.choices)
        body["command"] = row.command or ""
        body["description"] = row.description or ""
    else:
        body["question"] = row.question or ""
        body["multi_select"] = row.multi_select
        body["awaiting_text"] = row.awaiting_text
        if row.choices:
            body["choices"] = list(row.choices)
    return body


def phone_open_request(row: PromptRow) -> dict[str, object]:
    """RO-3 shape plus the v1.3 extras. Clarify uses `clarify_id` (AP-3 / RO-3)."""
    if row.kind == "clarify":
        body: dict[str, object] = {
            "kind": "clarify",
            "clarify_id": row.request_id,
            "question": row.question or "",
            "multi_select": row.multi_select,
            "awaiting_text": row.awaiting_text,
            "expires_at": row.expires_at,
            "surface": row.surface,
        }
        if row.choices:
            body["choices"] = list(row.choices)
        return body
    return {
        "kind": "approval",
        "request_id": row.request_id,
        "command": row.command or "",
        "description": row.description or "",
        "choices": list(row.choices),
        "expires_at": row.expires_at,
        "surface": row.surface,
    }


def list_prompts(
    store: PromptStore,
    *,
    iid: str,
    user_id: str,
    profile: str,
    now: int,
    members: MemberState = ALL_OPEN,
) -> HttpResult:
    store.purge(now)
    held, rows = store._visible_live_rows(iid, user_id, profile, now, members)
    return HttpResult(
        200,
        {
            "prompts": [wire_prompt(row) for row in rows],
            "desktop_held": held,
        },
    )


def _match_choice(offered: tuple[str, ...], submitted: str) -> str | None:
    """The single offered label the submission names; None when none or more than one match."""
    wanted = strip_recommended(submitted).casefold()
    matches = [label for label in offered if strip_recommended(label).casefold() == wanted]
    return matches[0] if len(matches) == 1 else None


def _parse_answer(body: Mapping[str, object]) -> tuple[str, object] | HttpResult:
    if "all" in body or "resolve_all" in body:
        return _bad()
    present = [name for name in ("choice", "choices", "other", "text") if name in body]
    groups = set()
    if "choice" in body or "choices" in body:
        groups.add("choice")
    if "other" in body:
        groups.add("other")
    if "text" in body:
        groups.add("text")
    if len(groups) != 1 or ("choice" in body and "choices" in body):
        return _bad()
    if "choice" in body:
        choice = body["choice"]
        if not isinstance(choice, str) or not choice:
            return _bad()
        return ("choice", choice)
    if "choices" in body:
        choices = body["choices"]
        if (
            not isinstance(choices, list)
            or not choices
            or len(choices) > 4
            or not all(isinstance(item, str) and item for item in choices)
        ):
            return _bad()
        return ("choices", tuple(choices))
    if "other" in body:
        if body["other"] is not True:
            return _bad()
        return ("other", True)
    text = body["text"]
    if not isinstance(text, str) or not text:
        return _bad()
    del present
    return ("text", text)


def _replay(row: PromptRow) -> HttpResult | None:
    if row.stored_status is None or row.stored_body is None:
        return None
    return HttpResult(row.stored_status, dict(row.stored_body))


def _remember(row: PromptRow, result: HttpResult, digest: bytes | None) -> None:
    """Replay fields only. `PromptStore.settle_answer` writes status, `settled_at` and cause."""
    row.stored_status = result.status
    row.stored_body = dict(result.body)
    if digest is not None:
        row.answer_hash = digest


def _stale_cause(row: PromptRow) -> str:
    """NI-2.3: a stale Bot Chat approval came from the native classifier (RD-5); every other stale
    verdict is a Phone result that proves nothing about Hermes (RD-4, RD-6)."""
    if row.kind == "approval" and row.surface == "bot_chat":
        return "native_not_pending"
    return "phone_not_resolved"


async def answer_prompt(
    store: PromptStore,
    *,
    iid: str,
    user_id: str,
    profile: str,
    request_id: str,
    body: Mapping[str, object],
    resolver: PromptResolver,
    now: int,
    ownership_check: DesktopOwnershipCheck | None = None,
) -> HttpResult:
    """AP-4 / AP-5. The stored row decides the kind. A client session key in `body` is ignored."""
    if len(request_id) > _REQUEST_ID_MAX or not request_id:
        return _bad()
    parsed = _parse_answer(body)
    if isinstance(parsed, HttpResult):
        return parsed
    form, value = parsed
    digest = _canonical_answer(body)
    store.purge(now)
    key = (iid, user_id, profile, request_id)
    async with store.answer_row(key) as row:
        if row is None:
            _log("prompt_answer", "not_found", user_id=user_id, request_id=request_id)
            return _not_found()
        now = max(now, int(store._clock()))
        store.purge(now)  # the wait for this row's lock may have crossed the expiry grace
        if row.status == "resolved" and row.answer_hash is not None:
            if row.answer_hash == digest:
                replay = _replay(row)
                if replay is not None:
                    return replay
            _log("prompt_answer", "conflict", user_id=user_id, request_id=request_id)
            return _error(
                "idempotency_conflict",
                "message id reused with a different payload",
                applied=False,
            )
        if row.status == "expired":
            return _error("stale", "request is no longer answerable", applied=False)
        if row.surface == "bot_chat":
            ownership = DesktopOwnership.UNKNOWN
            if ownership_check is not None:
                try:
                    candidate = await ownership_check(row)
                except Exception:
                    candidate = DesktopOwnership.UNKNOWN
                if type(candidate) is DesktopOwnership:
                    ownership = candidate
            if ownership is not DesktopOwnership.UNOWNED:
                return _unavailable()
        result = await _apply(row, form, value, resolver, user_id)
        if result.status == 200 and result.body.get("status") == "resolved":
            store.settle_answer(row, status="resolved", cause="answer_applied", now=now)
            _remember(row, result, digest)
        elif result.status == 409 and isinstance(result.body.get("error"), dict):
            error = result.body["error"]
            code = error.get("code") if isinstance(error, dict) else None
            if code == "stale":
                store.settle_answer(
                    row, status="expired", cause=_stale_cause(row), now=now
                )
                _remember(row, result, None)
            _log(
                "prompt_answer",
                "conflict" if code == "idempotency_conflict" else str(code or "stale"),
                user_id=user_id,
                request_id=request_id,
            )
        elif result.status == 200 and result.body.get("status") == "awaiting_text":
            row.awaiting_text = True
            _log("prompt_answer", "awaiting_text", user_id=user_id, request_id=request_id)
        return result


async def _apply(
    row: PromptRow, form: str, value: object, resolver: PromptResolver, user_id: str
) -> HttpResult:
    if row.kind == "approval":
        if form != "choice" or not isinstance(value, str):
            return _error("invalid_choice", "choice not offered", applied=False)
        if value not in row.choices or value not in APPROVAL_CHOICES:
            return _error("invalid_choice", "choice not offered", applied=False)
        verdict = await resolver.resolve_approval(row, value)
        if verdict == "unavailable":
            return _unavailable()
        if verdict != "accepted":
            return _error("stale", "request is no longer answerable", applied=False)
        _log(
            "prompt_answer",
            "resolved",
            user_id=user_id,
            request_id=row.request_id,
            run_id=row.run_id or "",
        )
        return HttpResult(200, {"status": "resolved", "applied": True})

    if form == "other":
        verdict = await resolver.mark_awaiting(row)
        if verdict == "unavailable":
            return _unavailable()
        if verdict != "ok":
            return _error("stale", "request is no longer answerable", applied=False)
        return HttpResult(200, {"status": "awaiting_text", "applied": False})

    if form == "text":
        if row.choices and not row.awaiting_text:
            return _error("invalid_choice", "choice not offered", applied=False)
        text = value if isinstance(value, str) else ""
        verdict = await resolver.resolve_clarify(row, text)
        if verdict == "unavailable":
            return _unavailable()
        if verdict != "accepted":
            return _error("stale", "request is no longer answerable", applied=False)
        _log("prompt_answer", "resolved", user_id=user_id, request_id=row.request_id)
        return HttpResult(200, {"status": "resolved", "applied": True})

    if form == "choices":
        if not row.multi_select or not isinstance(value, tuple):
            return _error("invalid_choice", "choice not offered", applied=False)
        labels: list[str] = []
        for submitted in value:
            matched = _match_choice(row.choices, submitted)
            if matched is None:
                return _error("invalid_choice", "choice not offered", applied=False)
            stripped = strip_recommended(matched)
            if stripped not in labels:
                labels.append(stripped)
        response = json.dumps(labels, ensure_ascii=False)
    else:
        if row.multi_select or not isinstance(value, str):
            return _error("invalid_choice", "choice not offered", applied=False)
        matched = _match_choice(row.choices, value)
        if matched is None:
            return _error("invalid_choice", "choice not offered", applied=False)
        response = strip_recommended(matched)

    verdict = await resolver.resolve_clarify(row, response)
    if verdict == "unavailable":
        return _unavailable()
    if verdict != "accepted":
        return _error("stale", "request is no longer answerable", applied=False)
    _log("prompt_answer", "resolved", user_id=user_id, request_id=row.request_id)
    return HttpResult(200, {"status": "resolved", "applied": True})


@dataclass
class AdapterHooks:
    """Phone-chat adapter hooks. Hermes calls these on the event loop; Hermes work is threaded."""

    store: PromptStore
    bridge: object
    now: Callable[[], int]
    iid: str
    # `phone_chat` availability (spec 034), default closed. While closed, the producer hooks below
    # neither call the bridge's approval helpers nor store an actionable row.
    phone_available: Callable[[], bool] = field(default=lambda: False)

    def _phone_open(self) -> bool:
        try:
            return self.phone_available() is True
        except Exception:
            return False

    def note_inert(self, chat_id: str) -> None:
        self.store.suppress_transcript(chat_id)

    def on_send(
        self,
        chat_id: str,
        content: str,
        reply_to: str | None,
        metadata: Mapping[str, object] | None,
    ) -> bool:
        """True when the outbound was stored. False when it was dropped (inert reply)."""
        if self.store.transcript_suppressed(chat_id):
            return False
        if isinstance(reply_to, str) and reply_to.startswith("hmp:auth:"):
            return False
        owner = self._owner_for_chat(chat_id)
        if owner is None:
            return False
        _iid, user_id, profile = owner
        if isinstance(metadata, Mapping) and metadata.get("is_approval_prompt") is True:
            content = "Approval unavailable. Wait for Hermes to expire it; chat cannot answer it."
        self.store.add_observation(
            self.iid, user_id, profile, role="assistant", text=content, now=float(self.now())
        )
        return True

    async def reconcile_chat(self, chat_id: str) -> None:
        if not self._phone_open():
            return
        with self.store._guard:
            keys = [key for key, owner in self.store._sessions.items()
                    if owner[0] == self.iid and owner[3] == chat_id]
        lister = getattr(self.bridge, "list_gateway_approvals", None)
        if not callable(lister):
            return
        for key in keys:
            try:
                pending = await asyncio.to_thread(lister, key)
            except Exception:
                _log("prompt_store", "unavailable")
                continue  # unavailable is not proof the waiter is gone
            if isinstance(pending, list):
                ids = {row["request_id"] for row in pending if isinstance(row, Mapping)
                       and isinstance(row.get("request_id"), str)}
                self.store.reconcile_approvals(key, ids, self.now())

    def _owner_for_chat(self, chat_id: str) -> tuple[str, str, str] | None:
        return self.store.owner_of_chat(self.iid, chat_id)

    async def on_exec_approval(self, prompt: object) -> bool:
        if not self._phone_open():
            return False
        session_key = str(getattr(prompt, "session_key", "") or "")
        command = getattr(prompt, "command", None)
        if not isinstance(command, str):
            return False
        owner = self.store.owner_of_session(session_key)
        if owner is None:
            return False
        iid, user_id, profile, _chat = owner
        lister = getattr(self.bridge, "list_gateway_approvals", None)
        if not callable(lister):
            return False
        try:
            pending = await asyncio.to_thread(lister, session_key)
        except Exception:
            return False
        if not isinstance(pending, list):
            return False
        open_ids = self.store.open_request_ids(session_key)
        matches = [
            entry
            for entry in pending
            if isinstance(entry, Mapping)
            and entry.get("command") == command
            and isinstance(entry.get("request_id"), str)
            and entry.get("request_id") not in open_ids
        ]
        recovery = len(matches) != 1
        if not matches:
            # The runner may redact the command. Keep only request-bound deny recovery;
            # never infer an allow choice from an ambiguous command string.
            matches = [entry for entry in pending if isinstance(entry, Mapping)
                       and isinstance(entry.get("request_id"), str)
                       and entry["request_id"] not in open_ids]
        matches = [entry for entry in matches if 0 < len(entry["request_id"]) <= _REQUEST_ID_MAX]
        if not matches:
            return False
        raw_choices = getattr(prompt, "choices", ())
        choices = tuple(
            choice
            for choice in raw_choices
            if isinstance(choice, str) and choice in APPROVAL_CHOICES
        )
        if not choices:
            return False
        timeout_s = await self._timeout("phone_approval_timeout_s", 300, profile)
        description = getattr(prompt, "description", "") or ""
        if recovery:
            if "deny" not in choices:
                return False
            choices = ("deny",)
            command = ""
            description = "Unbound approval. Deny to release this wait, or let Hermes time it out."
        for match in matches:
            request_id = str(match["request_id"])
            self.store.put(
                PromptRow(
                    iid=iid,
                    user_id=user_id,
                    profile=profile,
                    request_id=request_id,
                    kind="approval",
                    surface="phone_chat",
                    choices=choices,
                    command=command,
                    description=description if isinstance(description, str) else "",
                    expires_at=self.now() + max(0, timeout_s),
                    observed_at=self.now(),
                    session_key=session_key,
                )
            )
        return True

    async def on_clarify(
        self,
        *,
        chat_id: str,
        question: str,
        choices: list[str] | None,
        clarify_id: str,
        session_key: str,
    ) -> bool:
        del chat_id
        if not self._phone_open():
            return False
        owner = self.store.owner_of_session(session_key)
        if owner is None or not clarify_id:
            return False
        iid, user_id, profile, _chat = owner
        offered = tuple(choice for choice in (choices or []) if isinstance(choice, str))
        timeout_s = await self._timeout("phone_clarify_timeout_s", 3600, profile)
        # `send_clarify` does not carry `multi_select`, and HMP does not read the private
        # clarify index (AP-9). The answer path still honors the flag when a row has it.
        self.store.put(
            PromptRow(
                iid=iid,
                user_id=user_id,
                profile=profile,
                request_id=clarify_id,
                kind="clarify",
                surface="phone_chat",
                choices=offered,
                question=question,
                multi_select=False,
                awaiting_text=not offered,
                expires_at=self.now() + timeout_s if timeout_s > 0 else None,
                observed_at=self.now(),
                session_key=session_key,
            )
        )
        return True

    def retire(self, clarify_id: str) -> None:
        with self.store._guard:
            for row in self.store._rows.values():
                if row.request_id == clarify_id and row.kind == "clarify" and row.status == "open":
                    self.store.expire(row, self.now(), cause="clarify_retired")
                    _log(
                        "prompt_store",
                        "stale",
                        user_id=row.user_id,
                        request_id=row.request_id,
                    )

    async def _timeout(self, name: str, default: int, profile: str) -> int:
        fn = getattr(self.bridge, name, None)
        if not callable(fn):
            return default
        try:
            value = await asyncio.to_thread(fn, profile)
        except Exception:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value


PhoneDeliver = Callable[..., Awaitable[bool | None]]
PendingApprovals = Callable[[str], list[Mapping[str, object]]]


def phone_text_hash(text: str) -> bytes:
    return hashlib.sha256(json.dumps([text], separators=(",", ":")).encode("utf-8")).digest()


def _stored_phone(result_json: str | None) -> HttpResult | None:
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    status = data.get("http")
    body = data.get("body")
    if isinstance(status, bool) or not isinstance(status, int) or not isinstance(body, dict):
        return None
    return HttpResult(status, body)


def _dump_phone(result: HttpResult) -> str:
    return json.dumps({"http": result.status, "body": result.body}, separators=(",", ":"))


async def handle_phone_send(
    *,
    prompts: PromptStore,
    sqlite_store: object,
    iid: str,
    user_id: str,
    profile: str,
    chat_id: str,
    cmid: str,
    text: str,
    now: int,
    resolver: PromptResolver,
    session_key: Callable[[], str | None],
    pending_approvals: Callable[[str], object],
    deliver: Callable[[], Awaitable[bool | None]],
) -> HttpResult:
    """AP-6. Reserves the cmid before any hand-off. A replay does not call `deliver` again."""
    digest = phone_text_hash(text)
    record, inserted = await asyncio.to_thread(
        sqlite_store.reserve_phone_cmid,  # type: ignore[attr-defined]
        iid,
        user_id,
        profile,
        cmid,
        digest,
        now,
    )
    if bytes(record["payload_hash"]) != digest:
        _log("phone_send", "conflict", user_id=user_id)
        return _error("idempotency_conflict", "message id reused with a different payload")
    task_key = (iid, user_id, profile, cmid)
    if not inserted:
        stored = _stored_phone(record["result_json"])
        if record["status"] != "pending" and stored is not None:
            _log("phone_send", "replay", user_id=user_id)
            return stored
        existing = prompts.phone_task(task_key)
        if existing is not None:
            return await asyncio.shield(existing)
        return HttpResult(200, {"state": "unknown"})

    async def run() -> HttpResult:
        try:
            result, status_name = await _phone_turn(
                prompts=prompts,
                iid=iid,
                user_id=user_id,
                profile=profile,
                chat_id=chat_id,
                text=text,
                now=now,
                resolver=resolver,
                session_key=session_key,
                pending_approvals=pending_approvals,
                deliver=deliver,
            )
        except Exception as exc:
            if isinstance(exc, HelperUnavailableError):
                log_event("approval_helper", outcome="unavailable")
            result = _error("api_server_unavailable", "direct send delivery is unavailable")
            status_name = "unknown"
        await asyncio.to_thread(
            sqlite_store.finalize_phone_cmid,  # type: ignore[attr-defined]
            iid,
            user_id,
            profile,
            cmid,
            status=status_name,
            result_json=_dump_phone(result),
            updated_at=now,
        )
        return result

    task = asyncio.ensure_future(run())
    prompts.put_phone_task(task_key, task)

    def _done(finished: asyncio.Task[HttpResult]) -> None:
        prompts.drop_phone_task(task_key, finished)
        if not finished.cancelled():
            finished.exception()

    task.add_done_callback(_done)
    return await asyncio.shield(task)


async def _phone_turn(
    *,
    prompts: PromptStore,
    iid: str,
    user_id: str,
    profile: str,
    chat_id: str,
    text: str,
    now: int,
    resolver: PromptResolver,
    session_key: Callable[[], str | None],
    pending_approvals: Callable[[str], object],
    deliver: Callable[[], Awaitable[bool | None]],
) -> tuple[HttpResult, str]:
    prompts.purge(now)
    if prompts.open_clarifies(iid, user_id, profile):
        return _error("stale", "answer through the prompt route", applied=False), "rejected"

    key = await asyncio.to_thread(session_key)
    if not isinstance(key, str) or not key:
        _log("phone_send", "refused", user_id=user_id)
        return _error("api_server_unavailable", "direct send delivery is unavailable"), "unknown"
    pending = await asyncio.to_thread(pending_approvals, key)
    if isinstance(pending, list) and pending:
        _log("phone_send", "refused", user_id=user_id)
        return _error("stale", "request is no longer answerable", applied=False), "rejected"
    if not isinstance(pending, list):
        _log("phone_send", "refused", user_id=user_id)
        return _error("api_server_unavailable", "direct send delivery is unavailable"), "unknown"

    prompts.remember_session(key, iid, user_id, profile, chat_id)
    prompts.release_transcript(chat_id)
    accepted = await deliver()
    if accepted is False:
        # Only an exact False is definitive "not admitted" (bridge: gateway refusal or an
        # explicit known ticket refusal). It is HMP's own wire answer, not an upstream gap.
        _log("phone_send", "refused", user_id=user_id)
        return (
            _error("api_server_unavailable", "direct send delivery is unavailable", applied=False),
            "rejected",
        )
    if accepted is not True:
        # None and any malformed non-bool result prove neither admitted nor not-sent.
        _log("phone_send", "unknown", user_id=user_id)
        return HttpResult(200, {"state": "unknown"}), "unknown"
    prompts.add_observation(iid, user_id, profile, role="user", text=text, now=float(now))
    _log("phone_send", "submitted", user_id=user_id)
    return HttpResult(202, {"state": "submitted"}), "submitted"
