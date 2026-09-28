"""Approvals and Phone chat (`HMP_V1.md` §7b, amendment F3).

Prompt rows are process memory (AP-2). This module does not import Hermes. Loopback approval
POSTs and `resolve_gateway_*` are injected. `adapter.py` reaches the hooks through the object
`connect` builds; it does not import `tools.approval`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from .contract import IDEMPOTENCY_RETENTION_S
from .logging_policy import log_event

APPROVAL_CHOICES = ("once", "session", "always", "deny")
_RECOMMENDED_SUFFIX = "(Recommended)"
_PROVISIONAL_ID_BASE = 1_000_000_000
_REQUEST_ID_MAX = 256


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


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: dict[str, object]


class PromptResolver(Protocol):
    async def resolve_approval(self, row: PromptRow, choice: str) -> str:
        """`accepted`, `stale`, or `unavailable`."""
        ...

    async def resolve_clarify(self, row: PromptRow, response: str) -> str:
        """`accepted` or `stale`."""
        ...

    async def mark_awaiting(self, row: PromptRow) -> str:
        """`ok` or `stale`."""
        ...


def _error(code: str, message: str, *, applied: bool | None = None) -> HttpResult:
    http = {"bad_request": 400, "not_found": 404, "stale": 409, "invalid_choice": 409,
            "idempotency_conflict": 409, "write_gate_closed": 503,
            "api_server_unavailable": 503}[code]
    body: dict[str, object] = {"error": {"code": code, "message": message}}
    if applied is not None:
        body["applied"] = applied
    return HttpResult(http, body)


def _not_found() -> HttpResult:
    return _error("not_found", "not found")


def _bad() -> HttpResult:
    return _error("bad_request", "malformed request")


class PromptStore:
    """Process-memory prompts, the desktop-held marker, and Phone-chat transcript observations."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._rows: dict[tuple[str, str, str, str], PromptRow] = {}
        self._desktop: set[tuple[str, str, str]] = set()
        self._sessions: dict[str, tuple[str, str, str, str]] = {}
        self._suppressed: set[str] = set()
        self._observations: dict[tuple[str, str, str], list[tuple[str, str, float]]] = {}
        self._locks: dict[tuple[str, str, str, str], asyncio.Lock] = {}
        self._phone_tasks: dict[tuple[str, str, str, str], asyncio.Task[HttpResult]] = {}
        self._next_provisional = _PROVISIONAL_ID_BASE

    def answer_lock(self, key: tuple[str, str, str, str]) -> asyncio.Lock:
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    def get(self, key: tuple[str, str, str, str]) -> PromptRow | None:
        with self._guard:
            return self._rows.get(key)

    def purge(self, now: int) -> None:
        with self._guard:
            stale = [
                key
                for key, row in self._rows.items()
                if row.settled_at is not None and now - row.settled_at >= IDEMPOTENCY_RETENTION_S
            ]
            for key in stale:
                del self._rows[key]

    def put(self, row: PromptRow) -> None:
        key = (row.iid, row.user_id, row.profile, row.request_id)
        with self._guard:
            current = self._rows.get(key)
            if current is not None:
                return
            self._rows[key] = row
        _log(
            "prompt_store",
            "stored",
            user_id=row.user_id,
            request_id=row.request_id,
            run_id=row.run_id or "",
        )

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
                expires_at=now + timeout_s if timeout_s > 0 else None,
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
        key = (iid, user_id, profile)
        with self._guard:
            self._observations.setdefault(key, []).append((role, text, now))

    def observations(
        self, iid: str, user_id: str, profile: str
    ) -> tuple[tuple[str, str, float], ...]:
        with self._guard:
            return tuple(self._observations.get((iid, user_id, profile), ()))

    def next_provisional_id(self) -> int:
        with self._guard:
            value = self._next_provisional
            self._next_provisional += 1
            return value

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

    def list_visible(self, iid: str, user_id: str, profile: str) -> tuple[PromptRow, ...]:
        held = self.desktop_held(iid, user_id, profile)
        with self._guard:
            rows = [
                row
                for row in self._rows.values()
                if row.status == "open"
                and (row.iid, row.user_id, row.profile) == (iid, user_id, profile)
            ]
        if held:
            rows = [row for row in rows if row.surface != "bot_chat"]
        return tuple(rows)


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
    store: PromptStore, *, iid: str, user_id: str, profile: str, now: int
) -> HttpResult:
    store.purge(now)
    rows = store.list_visible(iid, user_id, profile)
    return HttpResult(
        200,
        {
            "prompts": [wire_prompt(row) for row in rows],
            "desktop_held": store.desktop_held(iid, user_id, profile),
        },
    )


def _match_choice(offered: tuple[str, ...], submitted: str) -> str | None:
    wanted = strip_recommended(submitted).casefold()
    for label in offered:
        if strip_recommended(label).casefold() == wanted:
            return label
    return None


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


def _remember(
    row: PromptRow, result: HttpResult, digest: bytes | None, now: int, *, settle: bool
) -> None:
    row.stored_status = result.status
    row.stored_body = dict(result.body)
    if settle:
        row.settled_at = now
    if digest is not None:
        row.answer_hash = digest


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
    async with store.answer_lock(key):
        row = store.get(key)
        if row is None:
            _log("prompt_answer", "not_found", user_id=user_id, request_id=request_id)
            return _not_found()
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
            replay = _replay(row)
            if replay is not None:
                return replay
        result = await _apply(row, form, value, resolver, user_id)
        if result.status == 200 and result.body.get("status") == "resolved":
            row.status = "resolved"
            _remember(row, result, digest, now, settle=True)
        elif result.status == 409 and isinstance(result.body.get("error"), dict):
            error = result.body["error"]
            code = error.get("code") if isinstance(error, dict) else None
            if code == "stale":
                row.status = "expired"
                _remember(row, result, None, now, settle=True)
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
            return _error("api_server_unavailable", "direct send delivery is unavailable")
        if verdict != "accepted":
            return _error("stale", "request is no longer answerable", applied=False)
        _log(
            "prompt_answer",
            f"resolved_{value}",
            user_id=user_id,
            request_id=row.request_id,
            run_id=row.run_id or "",
        )
        return HttpResult(200, {"status": "resolved", "applied": True})

    if form == "other":
        verdict = await resolver.mark_awaiting(row)
        if verdict != "ok":
            return _error("stale", "request is no longer answerable", applied=False)
        return HttpResult(200, {"status": "awaiting_text", "applied": False})

    if form == "text":
        if row.choices and not row.awaiting_text:
            return _error("invalid_choice", "choice not offered", applied=False)
        text = value if isinstance(value, str) else ""
        verdict = await resolver.resolve_clarify(row, text)
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
    if verdict != "accepted":
        return _error("stale", "request is no longer answerable", applied=False)
    _log("prompt_answer", "resolved", user_id=user_id, request_id=row.request_id)
    return HttpResult(200, {"status": "resolved", "applied": True})


def message_as_clarify_body(row: PromptRow, text: str) -> Mapping[str, object]:
    """AP-6: a phone message while a clarify is pending is an answer, not a new turn."""
    if row.awaiting_text or not row.choices:
        return {"text": text}
    if row.multi_select:
        return {"text": text}
    if _match_choice(row.choices, text) is not None:
        return {"choice": text}
    return {"text": text}


@dataclass
class AdapterHooks:
    """Phone-chat adapter hooks. Hermes calls these on the event loop; Hermes work is threaded."""

    store: PromptStore
    bridge: object
    now: Callable[[], int]
    iid: str
    _approval_fallback: set[str] = field(default_factory=set)

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
            self._approval_fallback.add(chat_id)
        self.store.add_observation(
            self.iid, user_id, profile, role="assistant", text=content, now=float(self.now())
        )
        return True

    def _owner_for_chat(self, chat_id: str) -> tuple[str, str, str] | None:
        return self.store.owner_of_chat(self.iid, chat_id)

    async def on_exec_approval(self, prompt: object) -> bool:
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
        if len(matches) != 1:
            return False
        request_id = str(matches[0]["request_id"])
        raw_choices = getattr(prompt, "choices", ())
        choices = tuple(
            choice
            for choice in raw_choices
            if isinstance(choice, str) and choice in APPROVAL_CHOICES
        )
        if not choices:
            return False
        timeout_s = await self._timeout("approval_timeout_s", 300)
        description = getattr(prompt, "description", "") or ""
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
                expires_at=self.now() + timeout_s if timeout_s > 0 else None,
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
        owner = self.store.owner_of_session(session_key)
        if owner is None or not clarify_id:
            return False
        iid, user_id, profile, _chat = owner
        offered = tuple(choice for choice in (choices or []) if isinstance(choice, str))
        timeout_s = await self._timeout("clarify_timeout_s", 3600)
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
                    row.status = "expired"
                    row.settled_at = self.now()
                    _log(
                        "prompt_store",
                        "stale",
                        user_id=row.user_id,
                        request_id=row.request_id,
                    )

    async def _timeout(self, name: str, default: int) -> int:
        fn = getattr(self.bridge, name, None)
        if not callable(fn):
            return default
        try:
            value = await asyncio.to_thread(fn)
        except Exception:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value


PhoneDeliver = Callable[..., Awaitable[bool]]
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
    deliver: Callable[[], Awaitable[bool]],
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
        except Exception:
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
    deliver: Callable[[], Awaitable[bool]],
) -> tuple[HttpResult, str]:
    clarifies = prompts.open_clarifies(iid, user_id, profile)
    if len(clarifies) > 1:
        _log("phone_send", "refused", user_id=user_id)
        return _error("invalid_choice", "choice not offered", applied=False), "rejected"
    if len(clarifies) == 1:
        result = await answer_prompt(
            prompts,
            iid=iid,
            user_id=user_id,
            profile=profile,
            request_id=clarifies[0].request_id,
            body=message_as_clarify_body(clarifies[0], text),
            resolver=resolver,
            now=now,
        )
        status_name = "submitted" if result.status < 400 else "rejected"
        return result, status_name

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
    prompts.add_observation(iid, user_id, profile, role="user", text=text, now=float(now))
    accepted = await deliver()
    if not accepted:
        _log("phone_send", "refused", user_id=user_id)
        return _error("api_server_unavailable", "direct send delivery is unavailable"), "rejected"
    _log("phone_send", "submitted", user_id=user_id)
    return HttpResult(202, {"state": "submitted"}), "submitted"
