"""The read bridge: the ONLY module that imports Hermes internals (HMP v1 PR-2, §12). T028.

It implements `contract.ReadBridge`, which covers the read subset and the inert P6 trigger.

Rules:
- It reaches only §12 internals. Each is a `HERMES_API_GAP`, and each is listed in
  `compat.READ_DEPENDENCIES`, which the CS-21 dependency probe checks before this module is ever
  imported.
- Reads never mint anything: no conversation, no session, no `chats` row and no database file
  (FR-036, R11). A conversation this bridge does not find is reported as `None`, never created.
- Authorization fails closed. Any failure, or any answer that is not a genuine `bool`, while
  deciding a bot's state gives `AuthzState.UNVERIFIABLE`.
- A failed read of conversation state raises `BridgeError`. It never degrades to an empty list,
  which a client would take as "the conversation is empty". `reads.py` turns the error into
  `500 other {why:"internal_error"}` and logs its type only (SEC-4).
- The P6 trigger is inert (GU-4 exception, PR6-1). Its text is fixed, it carries no user content,
  it is never a gateway command, and it asks the bot for nothing. It is sent only after the bot
  reads `pending_operator`. Hermes's reply (a pairing code) goes to `HmpAdapter.send`, which drops
  it unlogged (PR6-2).
- Nothing here writes to Hermes. No `SessionDB` or `SessionStore` write, no pairing store, no
  allowlist, no `.env`, no configuration. The P6 trigger is the only hand-off (OD-F6(c): grants are
  never created or broadened by HMP).

Every Hermes source file this module imports, or that defines a symbol it reaches, is contained in
`bridge_files` of `read_compat_builds.json`. `tools/compat/bridge_files.py` computes that list
mechanically (research R8, CS-21).

Hermes module-level symbols are imported lazily, inside `HermesApi`, so this module can be imported
and unit-tested without Hermes. Hermes objects (the runner, the adapter, the session store, a
`SessionDB`) are reached only through the names listed in `REACHED_METHODS`. A unit test checks that
list against this file's AST, and checks every entry against `compat.READ_DEPENDENCIES`.

This module is imported only after `compat.CompatGate.evaluate()` returns SUPPORTED. No other
module imports it at module level.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import os
import re
import secrets
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from .contract import (
    CONVERSATION_ID,
    TOOL_ARGUMENTS_CAP,
    TOOL_OUTPUT_CAP,
    AuthorizeResult,
    AuthzState,
    BotChatTarget,
    ConversationRef,
    DirectSendEndpoint,
    LineageInfo,
    ResetReason,
    Row,
    SessionSummary,
    WireToolCall,
)
from .logging_policy import log_bridge_exception, log_event

# P6 inert trigger (PR6-1, GU-4 exception, RV-7): fixed text, no user content, no request. It does
# not start with "/", and `allow_gateway_control` is off, so it is never a gateway command.
INERT_TRIGGER_TEXT = "[hmp] authorization request - no action requested"
INERT_TRIGGER_ID_PREFIX = "hmp:auth:"

# The never-enrolled canary used for allow-all detection (PR6-1, E-DR-1). It has a fresh random
# suffix on every check, so no grant can ever name it.
CANARY_USER_PREFIX = "hmpu_canary_"
CANARY_CHAT_ID = "hmp-canary"
# The chat id used when asking about a user who has no HMP chat for this bot yet. A DM grant is
# decided by the user id; this value never reaches a session key.
PROBE_CHAT_ID = "hmp-authz-probe"
OPERATOR_LABEL_UNKNOWN = "hmp-device"

# PR6-3 / E-GAP-31: the transport-scope env allowlists whose grants are instance-wide.
# `GATEWAY_ALLOWED_USERS` is Hermes's gateway-wide list. `HMP_ALLOWED_USERS` is the platform-shaped
# name, checked as well so the note errs on the side of disclosure.
INSTANCE_WIDE_ALLOWLIST_ENVS: tuple[str, ...] = ("GATEWAY_ALLOWED_USERS", "HMP_ALLOWED_USERS")

# The file name of a profile's session database inside its Hermes home.
STATE_DB_FILENAME = "state.db"

# Amendment F2 (direct send, HMP_V1.md §7a DS-4(2)): the same literal `reads.py`'s OD-F11 selector
# (`_CANONICAL_BOT_CHAT_TITLE`) independently asserts -- both are cross-checked read-only against
# Hermes's own `canonical-chat.ts`/`bot_mode_probe.py`/`hermes_state.py` (SES-7). Not read live from
# any Hermes symbol; a future rename of the literal fails this selector closed, never open.
_CANONICAL_BOT_CHAT_TITLE = "Bot Chat"

# DS-6/DS-2(b), review BLOCKER #3: the ONLY two literals HMP will ever open a socket to. `localhost`
# is accepted as a CONFIGURED value (Hermes's own `listen_address` accepts it) but is immediately
# rewritten to the IPv4 loopback literal below -- HMP never resolves the name `localhost` itself
# (a hosts-file or resolver override of that name must never be able to steer `API_SERVER_KEY`
# off-box). Every other value, including `0.0.0.0` or any other hostname, fails closed to `None`.
_LOOPBACK_LITERALS = frozenset({"127.0.0.1", "::1"})
_LOCALHOST_ALIAS = "localhost"
DEFAULT_API_SERVER_HOST = "127.0.0.1"
DEFAULT_API_SERVER_PORT = 8642
# The minimum usable secret length api_server.py itself enforces for a NAMED profile's own scoped
# key (`hermes_cli.auth.has_usable_secret`'s `min_length=16`, `api_server.py`'s own
# `_expected_api_key`). This mirrors only the length floor, not that function's placeholder-shape
# heuristics -- a partial mirror, documented, not a full reimplementation of a Hermes internal
# (DS-6 discipline: replicate the small precedence rule the guard needs, never import the private
# helper itself).
_MIN_USABLE_KEY_LENGTH = 16
# Same defensive bound `SessionDB.get_compression_lineage`'s forward walk uses
# (`hermes_state_compression.py`, `for _ in range(100)`).
_LINEAGE_WALK_BOUND = 100


def _has_usable_secret(value: object, *, min_length: int = _MIN_USABLE_KEY_LENGTH) -> bool:
    """Partial mirror of `hermes_cli.auth.has_usable_secret` (length floor only; see the constant's
    docstring above)."""
    return isinstance(value, str) and len(value.strip()) >= min_length


def _parent_chain(db: Any, start_id: str) -> tuple[str, ...] | None:
    """Walk `parent_session_id` upward from `start_id`.

    Supported read: `SessionDB.get_session` (`hermes_state_sessions.py:786`), already in
    `REACHED_METHODS` / `compat.READ_DEPENDENCIES`. The row carries `parent_session_id`, the column
    `get_compression_lineage` itself walks (`hermes_state_compression.py:689-719`) before it can
    return only `[session_id]` when its forward spine omits the start id.

    Root-first, including `start_id`. `None` when the chain cannot be established with certainty
    (missing row, a parent id that does not resolve, a non-string parent, a cycle, or the walk
    bound is hit while a parent is still set)."""
    upward: list[str] = []
    current = start_id
    seen: set[str] = set()
    for _ in range(_LINEAGE_WALK_BOUND):
        if not isinstance(current, str) or not current or current in seen:
            return None
        seen.add(current)
        try:
            row = db.get_session(current)
        except Exception:
            return None
        if not isinstance(row, Mapping):
            return None
        row_id = row.get("id")
        if isinstance(row_id, str) and row_id and row_id != current:
            return None
        upward.append(current)
        parent = row.get("parent_session_id")
        if parent is None or parent == "":
            upward.reverse()
            return tuple(upward)
        if not isinstance(parent, str):
            return None
        current = parent
    return None


def _union_session_ids(*groups: object) -> tuple[str, ...]:
    """Stable union. A group that is not a list/tuple of ids is skipped by the caller; this only
    accepts sequences and drops non-strings."""
    out: list[str] = []
    for group in groups:
        if isinstance(group, str):
            items: tuple[object, ...] | list[object] = (group,)
        elif isinstance(group, (list, tuple)):
            items = group
        else:
            continue
        for sid in items:
            if isinstance(sid, str) and sid and sid not in out:
                out.append(sid)
    return tuple(out)


# Attribute names this module calls on Hermes objects, by receiver (see the module docstring).
# `tests/unit/test_bridge.py` checks this table against the AST, and against
# `compat.READ_DEPENDENCIES`.
REACHED_METHODS: Mapping[str, frozenset[str]] = {
    "runner": frozenset(
        {"served_profile_names", "_routed_profile_home", "_is_user_authorized_for_source"}
    ),
    "adapter": frozenset({"build_source", "handle_message"}),
    "session_store": frozenset({"lookup_by_session_key"}),
    "db": frozenset(
        {
            "get_messages",
            "get_active_message_ids",
            "resolve_resume_session_id",
            "get_compression_chain",
            # Amendment A1 (session browsing, OD-F9/OD-F10; SES-1/SES-2).
            "list_sessions_rich",
            "get_session",
            # Amendment F2 (direct send, HMP_V1.md §7a DS-4(2)).
            "get_session_by_title",
            # Amendment F2, review BLOCKER #2 (lease chain): the full compression LINEAGE (ancestors
            # via parent_session_id/end_reason plus descendants), not `get_compression_chain`'s
            # forward-only walk -- compression moves the "Bot Chat" title onto the child, so
            # `get_session_by_title` can hand back an id that is itself the middle or tip of a
            # longer lineage, and a lease left on a pre-compression ancestor id must still be seen.
            "get_compression_lineage",
        }
    ),
}
# Plain data attributes read from Hermes objects (no code is reached through them).
REACHED_DATA_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "gateway_runner",
        "_session_store",
        "profile",
        "session_id",
        "profile_route_rejected",
        "config",
        "extra",
    }
)

# HMP-originated rows carry `platform_message_id = "hmp:<chat_id>:<cmid>"` (§2, `chat_id` row).
_CMID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


class BridgeError(RuntimeError):
    """A Hermes read could not be completed. The text is fixed and never carries Hermes data."""

    def __init__(self, what: str = "hermes read failed") -> None:
        super().__init__(what)


# --------------------------------------------------------------------------------------------------
# HMP-side directory: the `chats` row and the operator label. Read only.
# --------------------------------------------------------------------------------------------------


class Directory(Protocol):
    def chat_id(self, user_id: str, profile: str) -> str | None:
        """The user's HMP chat id for this bot, or None. Never mints one."""
        ...

    def operator_label(self, user_id: str) -> str | None:
        """The operator label of the user's most recently confirmed active device."""
        ...


class StoreDirectory:
    """`Directory` over the HMP store (`store.Store`). It only reads."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def chat_id(self, user_id: str, profile: str) -> str | None:
        row = self._store.get_chat(user_id, profile, CONVERSATION_ID)
        return str(row["chat_id"]) if row is not None else None

    def operator_label(self, user_id: str) -> str | None:
        with self._store.transaction() as conn:
            row = conn.execute(
                "SELECT label FROM devices WHERE user_id = ? AND state = 'ACTIVE' "
                "ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return str(row["label"]) if row is not None and row["label"] else None


# --------------------------------------------------------------------------------------------------
# Hermes module-level symbols (§12), imported lazily. Tests substitute a fake.
# --------------------------------------------------------------------------------------------------


class HermesApi:
    """Every Hermes module-level symbol the bridge reaches. Each import here is a §12 internal."""

    def profile_runtime_scope(self, profile_home: Path) -> Any:
        from gateway.run import _profile_runtime_scope  # §12, E-GAP-14

        return _profile_runtime_scope(Path(profile_home))

    def model_config(self) -> object:
        """Read the current profile's config inside `profile_runtime_scope`."""
        from hermes_cli.config import load_config

        config = load_config()
        return config.get("model") if isinstance(config, Mapping) else None

    def write_profile_model(self, home: Path, provider: str, model: str) -> bool:
        """Use the same scoped, validated writer as Hermes Desktop/dashboard.

        A validation refusal is data, never a caller-visible upstream exception.
        Other errors fail the feature closed and are logged by type only.
        """
        from fastapi import HTTPException
        from hermes_cli.web_routers.profiles import _write_profile_model

        try:
            _write_profile_model(home, provider, model)
        except HTTPException as exc:
            if exc.status_code == 400:
                return False
            raise
        return True

    def create_mobile_cron(self, fields: Mapping[str, object]) -> Mapping[str, object]:
        """Use Hermes's scheduler registration path inside the selected profile scope."""
        from cron.scheduler import create_job_with_scheduler_registration
        from tools.cronjob_prompt_scan import _scan_cron_prompt

        prompt = str(fields["prompt"])
        if _scan_cron_prompt(prompt):
            raise ValueError("Cron prompt rejected by Hermes")
        continuity = fields.get("continuity") is True
        return create_job_with_scheduler_registration(
            name=fields["name"], schedule=fields["schedule"], prompt=prompt,
            deliver=fields["deliver"], paused=True, repeat=fields.get("repeat"),
            context_from=["self"] if continuity else None,
        )

    def edit_mobile_cron(
        self, job_id: str, fields: Mapping[str, object]
    ) -> Mapping[str, object] | None:
        """Apply only HMP's fields through Hermes's own update writer."""
        from cron.jobs import get_job, update_job
        from cron.lifecycle_guard import check_gateway_lifecycle
        from cron.scheduler import _notify_provider_jobs_changed
        from tools.cronjob_prompt_scan import _scan_cron_prompt

        if "prompt" in fields and _scan_cron_prompt(str(fields["prompt"])):
            raise ValueError("Cron prompt rejected by Hermes")
        if "prompt" in fields:
            check_gateway_lifecycle(str(fields["prompt"]), None)
        existing = get_job(job_id)
        if existing is None:
            return None
        if any(existing.get(key) for key in (
            "script", "no_agent", "workdir", "monitor_script", "monitor_url",
        )):
            raise ValueError("This job needs the Hermes desktop cron editor")
        changes = {k: v for k, v in fields.items() if k != "continuity"}
        if "continuity" in fields:
            refs = [r for r in (existing.get("context_from") or []) if isinstance(r, str)
                    and r.lower() != "self"]
            if fields["continuity"] is True:
                refs.append("self")
            changes["context_from"] = refs or None
        updated = update_job(job_id, changes)
        if updated is not None:
            _notify_provider_jobs_changed()
        return updated

    def build_session_key(self, source: Any, profile: str | None) -> str:
        from gateway.session import build_session_key  # §12, E-GAP-6

        return build_session_key(source, profile=profile)

    def acquire(self, db_path: Path) -> Any:
        from hermes_state_registry import acquire  # §12, E-GAP-6/7

        return acquire(db_path)

    def release(self, db: Any) -> None:
        from hermes_state_registry import release  # §12, E-GAP-6/7

        release(db)

    def platform_gate_env(self, name: str) -> str:
        from gateway.platforms._shared import platform_gate_env  # §12, E-GAP-31

        return platform_gate_env(name, "")

    def capability_map(self) -> object:
        """`PLATFORM_ADAPTER_CAPABILITIES` (GU-2), or None when this build has no map."""
        try:
            from gateway.platforms.base import PLATFORM_ADAPTER_CAPABILITIES  # §8 GU-2
        except ImportError:
            return None
        return PLATFORM_ADAPTER_CAPABILITIES

    # -- Amendment F2 (direct send, HMP_V1.md §7a) ------------------------------------------------

    def active_session_registry_snapshot(self, registry_home: Path) -> list[Any]:
        """DS-4(3): read-only lease snapshot, scoped to the *target profile's own* registry home
        (never left at the ambient default -- the review's `registry_home` finding)."""
        from hermes_cli.active_sessions import active_session_registry_snapshot  # §12, DS-4(3)

        return active_session_registry_snapshot(registry_home=registry_home)

    def api_server_extra(self) -> Mapping[str, Any]:
        """DS-6: this profile's own `platforms.api_server` block, read in the ambient scope --
        the caller MUST already be inside `profile_runtime_scope(home)` for a named profile
        (mirrors `authz_state`'s own `_allow_all_active` pattern, above)."""
        from gateway.config import Platform, load_gateway_config  # §12, E-GAP-14

        config = load_gateway_config()
        platform_config = config.platforms.get(Platform.API_SERVER)
        extra = getattr(platform_config, "extra", None)
        return extra if isinstance(extra, Mapping) else {}

    def scoped_api_server_key(self) -> str:
        """DS-6: `API_SERVER_KEY`, read in the ambient scope via the same documented helper
        `api_server.py` itself uses -- never persisted, never logged (SEC-4)."""
        from gateway.platforms._shared import get_scoped_secret  # §12, E-GAP-31

        value = get_scoped_secret("API_SERVER_KEY", "")
        return value if isinstance(value, str) else ""

    def inert_trigger_event(self, *, source: Any, user_id: str, user_name: str) -> Any:
        """The P6 trigger `MessageEvent`. Optional fields are set only when this build has them:
        `allow_gateway_control=False`, so the text is never a command, and `defer_policy="reject"`
        (P2), so a busy bot refuses the trigger instead of queueing it."""
        from gateway.platforms.event import MessageEvent, MessageType  # §12, P2/P3 API

        names = {f.name for f in dataclasses.fields(MessageEvent)}
        kwargs: dict[str, Any] = {
            "text": INERT_TRIGGER_TEXT,
            "message_type": MessageType.TEXT,
            "message_id": INERT_TRIGGER_ID_PREFIX + secrets.token_hex(8),
            "source": source,
            "user_id": user_id,
            "user_name": user_name,
        }
        if "internal" in names:
            kwargs["internal"] = False
        if "allow_gateway_control" in names:
            kwargs["allow_gateway_control"] = False
        else:  # every reviewed build has it; without it the text could be parsed as a command
            raise BridgeError("MessageEvent lacks allow_gateway_control")
        if "defer_policy" in names:
            kwargs["defer_policy"] = "reject"
        return MessageEvent(**kwargs)


def _as_path(value: object) -> Path | None:
    """A usable profile home, or None. Hermes returns a sentinel object, never a path, for a
    profile home that does not resolve (`UNRESOLVED_PROFILE_HOME`)."""
    if isinstance(value, str | os.PathLike):
        path = Path(value)
        return path if path.is_absolute() else None
    return None


def _without_surrogates(value: str) -> str:
    """Drop lone surrogates so the JSON encoder never sees them. The input is not logged."""
    if all(not 0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        return value
    return "".join(ch for ch in value if not 0xD800 <= ord(ch) <= 0xDFFF)


def _cap_chars(text: str, limit: int) -> tuple[str, bool]:
    """Cut `text` to `limit` Unicode code points. The returned string is the only copy kept."""
    cleaned = _without_surrogates(text)
    if len(cleaned) <= limit:
        return cleaned, False
    return cleaned[:limit], True


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    cleaned = _without_surrogates(value)
    return cleaned or None


def _dump_compact(value: object) -> str | None:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return None


def _compact_arguments(raw: object) -> tuple[str, bool]:
    """Arguments as compact JSON, capped at `TOOL_ARGUMENTS_CAP`.

    A JSON string or object is re-rendered with no insignificant whitespace. A string that is
    not JSON is kept as text. Either way the result is at most the cap, and the uncapped value
    is not returned.
    """
    if isinstance(raw, str):
        candidate = raw
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if parsed is not None:
            rendered = _dump_compact(parsed)
            if rendered is not None:
                candidate = rendered
        return _cap_chars(candidate, TOOL_ARGUMENTS_CAP)
    if isinstance(raw, dict | list):
        rendered = _dump_compact(raw)
        if rendered is not None:
            return _cap_chars(rendered, TOOL_ARGUMENTS_CAP)
    return "", False


def _decode_tool_calls(raw: object) -> list[object] | None:
    """Hermes stores `messages.tool_calls` as JSON text. `SessionDB.get_messages` decodes it to
    a list (`_row_to_message_dict`); a raw JSON string is accepted too. Anything else, including
    a string that does not parse, yields no calls. The parse error is not logged (it quotes the
    document)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
    if isinstance(raw, list):
        return list(raw)
    return None


def _call_name(item: Mapping[object, object]) -> str | None:
    """OpenAI shape `function.name`, otherwise a top-level `name`."""
    function = item.get("function")
    if isinstance(function, Mapping):
        name = _optional_str(function.get("name"))
        if name is not None:
            return name
    return _optional_str(item.get("name"))


def _call_id(item: Mapping[object, object]) -> str:
    for key in ("id", "tool_call_id"):
        found = _optional_str(item.get(key))
        if found is not None:
            return found
    return ""


def _call_arguments(item: Mapping[object, object]) -> object:
    function = item.get("function")
    if isinstance(function, Mapping) and "arguments" in function:
        return function.get("arguments")
    return item.get("arguments")


def _tool_calls_of(raw: object) -> tuple[WireToolCall, ...]:
    """Assistant `messages.tool_calls` as wire calls. A call with no name is skipped. A bad blob
    does not fail the row."""
    calls = _decode_tool_calls(raw)
    if not calls:
        return ()
    out: list[WireToolCall] = []
    for item in calls:
        if not isinstance(item, Mapping):
            continue
        name = _call_name(item)
        if name is None:
            continue
        arguments, truncated = _compact_arguments(_call_arguments(item))
        out.append(
            WireToolCall(
                id=_call_id(item),
                name=name,
                arguments=arguments,
                arguments_truncated=truncated,
            )
        )
    return tuple(out)


def _text_of(content: object) -> str:
    """Hermes message content as display text: a string as is, a multimodal part list by its
    text parts, anything else as empty. Rendering is the client's job (FR-034)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return ""


def _created_at(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    number = float(value)
    return number if number == number and abs(number) != float("inf") else 0.0


def _not_routed(source: Any, profile: str) -> bool:
    """SR-6: a source is NOT routed to `profile` when its stamped `profile` differs, OR when
    Hermes's own ingress rejected the route and `build_source` fell back to the owner profile
    (`source.profile_route_rejected`) -- Hermes's real ingress drops such a source before
    authorization, so the bridge must too, even when the fallback owner profile happens to equal
    the one requested. `is not False`, not `is True`: an unexpected non-bool value fails closed."""
    if getattr(source, "profile", None) != profile:
        return True
    return getattr(source, "profile_route_rejected", False) is not False


def _row_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise BridgeError("row id is not a positive integer")
    return value


def _session_id_of(value: object) -> str:
    """Amendment A1: a `sessions.id` value from a `list_sessions_rich`/`get_session` row. Never
    empty -- Hermes's own `sessions.id` column is `TEXT PRIMARY KEY`, never null or blank."""
    if not isinstance(value, str) or not value:
        raise BridgeError("session id is not a non-empty string")
    return value


def _message_count_of(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BridgeError("session message_count is not a non-negative integer")
    return value


def _cmid(platform_message_id: object, chat_id: str | None) -> str | None:
    """`client_message_id` of an HMP-originated row of THIS chat, or None (RO-3)."""
    if chat_id is None or not isinstance(platform_message_id, str):
        return None
    prefix = f"hmp:{chat_id}:"
    if not platform_message_id.startswith(prefix):
        return None
    cmid = platform_message_id[len(prefix) :]
    return cmid if _CMID_RE.fullmatch(cmid) else None


class HermesReadBridge:
    """`contract.ReadBridge` over a running Hermes gateway (HMP v1 §12)."""

    def __init__(
        self,
        adapter: Any,
        directory: Directory,
        *,
        hermes: HermesApi | None = None,
    ) -> None:
        self._adapter = adapter
        self._directory = directory
        self._hermes = hermes if hermes is not None else HermesApi()
        # Always `concurrent.futures.Future` now (SR-4): `request_authorization` schedules the
        # P6 hand-off with `run_coroutine_threadsafe`, which returns that type regardless of
        # which thread calls it from.
        self._pending_triggers: set[Any] = set()

    # ------------------------------------------------------------------------------------------
    # Runner and sources
    # ------------------------------------------------------------------------------------------

    def _runner(self) -> Any:
        runner = getattr(self._adapter, "gateway_runner", None)
        if runner is None:
            raise BridgeError("no gateway runner")
        return runner

    def _source(self, *, chat_id: str, user_id: str, profile: str, user_name: str | None) -> Any:
        """A source built exactly as inbound traffic is: the route matcher stamps `profile`
        from `guild_id`/`scope_id` (`gateway.profile_routes`, E0 §1.8)."""
        adapter = self._adapter
        return adapter.build_source(
            chat_id=chat_id,
            chat_type="dm",
            user_id=user_id,
            user_name=user_name,
            scope_id=profile,
            guild_id=profile,
        )

    def _profile_home(self, profile: str) -> Path:
        # Keep the served set authoritative even if a future Hermes resolver returns a fallback
        # home for an explicit unknown profile. The v2026.8.31 resolver did exactly that, and a
        # direct substitution here would turn an unserved bot read into a root-profile read.
        if not isinstance(profile, str) or not profile or profile not in self.served_profiles():
            raise BridgeError("profile is not served")
        runner = self._runner()
        home = _as_path(runner._routed_profile_home(profile))
        if home is None:
            raise BridgeError("profile home does not resolve")
        return home

    def served_profiles(self) -> list[str]:
        runner = self._runner()
        names = runner.served_profile_names()
        if not isinstance(names, list | tuple):
            raise BridgeError("served profiles is not a list")
        out: list[str] = []
        for name in names:
            if not isinstance(name, str) or not name:
                raise BridgeError("served profile name is not a string")
            if name not in out:
                out.append(name)
        return out

    def profile_default_model(self, profile: str) -> Mapping[str, object]:
        """Read only the routed profile's persisted provider and default model."""
        home = self._profile_home(profile)
        with self._hermes.profile_runtime_scope(home):
            model = self._hermes.model_config()
        if isinstance(model, Mapping):
            provider, default = model.get("provider"), model.get("default")
            return {
                "provider": provider if isinstance(provider, str) else "",
                "model": default if isinstance(default, str) else "",
            }
        return {"provider": "", "model": model if isinstance(model, str) else ""}

    def set_profile_default_model(
        self, profile: str, provider: str, model: str
    ) -> Mapping[str, object] | None:
        """Validate and save via Hermes, then report the stored (possibly normalized) choice."""
        home = self._profile_home(profile)
        if not self._hermes.write_profile_model(home, provider, model):
            return None
        return self.profile_default_model(profile)

    def create_mobile_cron(
        self, profile: str, fields: Mapping[str, object]
    ) -> Mapping[str, object]:
        home = self._profile_home(profile)
        with self._hermes.profile_runtime_scope(home):
            return self._hermes.create_mobile_cron(fields)

    def edit_mobile_cron(
        self, profile: str, job_id: str, fields: Mapping[str, object]
    ) -> Mapping[str, object] | None:
        home = self._profile_home(profile)
        with self._hermes.profile_runtime_scope(home):
            return self._hermes.edit_mobile_cron(job_id, fields)

    # ------------------------------------------------------------------------------------------
    # Authorization (ERR-3, PR6-1): fails closed to UNVERIFIABLE
    # ------------------------------------------------------------------------------------------

    def _authorized(self, source: Any) -> bool | None:
        """Hermes's own per-bot query. None: the query failed or did not answer a bool."""
        runner = self._runner()
        answer = runner._is_user_authorized_for_source(source)
        return answer if isinstance(answer, bool) else None

    def _allow_all_active(self, profile: str) -> bool | None:
        """True: some allow-all form admits a never-enrolled canary, in the transport scope or in
        the routed profile's own scope (E-DR-1). None: the check could not run (fail closed)."""
        canary_user = CANARY_USER_PREFIX + secrets.token_hex(8)
        try:
            canary = self._source(
                chat_id=CANARY_CHAT_ID, user_id=canary_user, profile=profile, user_name=None
            )
            transport = self._authorized(canary)
            if transport is None:
                return None
            if transport:
                return True
            home = self._profile_home(profile)
            with self._hermes.profile_runtime_scope(home):
                routed = self._authorized(canary)
        except Exception as exc:
            log_bridge_exception(exc)
            return None
        return routed

    def authz_state(self, user_id: str, profile: str) -> AuthzState:
        try:
            if profile not in self.served_profiles():
                return AuthzState.NOT_SERVED
            chat_id = self._directory.chat_id(user_id, profile) or PROBE_CHAT_ID
            source = self._source(chat_id=chat_id, user_id=user_id, profile=profile, user_name=None)
            if _not_routed(source, profile):
                return AuthzState.NOT_ROUTED
        except Exception as exc:
            log_bridge_exception(exc)
            return AuthzState.UNVERIFIABLE
        allow_all = self._allow_all_active(profile)
        if allow_all is None:
            return AuthzState.UNVERIFIABLE
        if allow_all:
            return AuthzState.REFUSED_ALLOW_ALL
        try:
            authorized = self._authorized(source)
        except Exception as exc:
            log_bridge_exception(exc)
            return AuthzState.UNVERIFIABLE
        if authorized is None:
            return AuthzState.UNVERIFIABLE
        return AuthzState.AUTHORIZED if authorized else AuthzState.PENDING_OPERATOR

    def instance_wide_grant(self, profile: str) -> bool:
        """PR6-3: is an instance-wide grant active? Two sources, both read in the transport
        (ambient) scope, where Hermes reads them for routed HMP events (E-GAP-31):

        - a transport-scope env allowlist (`GATEWAY_ALLOWED_USERS` / `HMP_ALLOWED_USERS`);
        - a non-empty `platforms.hmp.extra.allow_from` on HMP's own adapter config (SR-1): Hermes
          authorizes from it via `_adapter_extra_allowlist_authorizes`, and because it is read
          from the transport adapter rather than a per-bot store, it is instance-wide across
          every profile this instance routes to, exactly like the env allowlists above.

        A failed read answers True, so the disclosure is shown rather than hidden."""
        del profile  # the allowlists in question are instance-wide by definition
        try:
            if any(
                self._hermes.platform_gate_env(name).strip()
                for name in INSTANCE_WIDE_ALLOWLIST_ENVS
            ):
                return True
            config = getattr(self._adapter, "config", None)
            extra = getattr(config, "extra", None)
            return bool(isinstance(extra, Mapping) and extra.get("allow_from"))
        except Exception as exc:
            log_bridge_exception(exc)
            return True

    def request_authorization(
        self, user_id: str, profile: str, *, loop: asyncio.AbstractEventLoop | None = None
    ) -> AuthorizeResult:
        """The inert P6 trigger (GU-4 exception). The bot's state is re-read first, and the
        trigger is sent only for `pending_operator`. The caller mints the `chats` row beforehand
        (`authorize.py`), so the trigger and any later conversation share one session key. A
        hand-off that cannot be made answers UNVERIFIABLE: without it no pending request exists,
        and the operator instruction would be false.

        `loop` (SR-4): this method itself may now run off the event loop, inside
        `asyncio.to_thread` (`authorize.py`/`server.py`), where `asyncio.get_running_loop()`
        raises (a plain executor thread has none). The caller on the real loop thread -- the only
        place `get_running_loop()` is guaranteed to answer correctly -- captures it and passes it
        down; `asyncio.run_coroutine_threadsafe` is the thread-safe way to still schedule the P6
        hand-off onto THAT loop from wherever this call actually runs. Omitting `loop` (every
        existing unit test) falls back to `get_running_loop()`, called here, on the assumption
        that this call is itself already running on the loop -- unchanged from before.
        """
        state = self.authz_state(user_id, profile)
        if state is not AuthzState.PENDING_OPERATOR:
            return AuthorizeResult(authz=state)
        try:
            chat_id = self._directory.chat_id(user_id, profile)
            if chat_id is None:
                raise BridgeError("no chat for the trigger")
            label = self._directory.operator_label(user_id) or OPERATOR_LABEL_UNKNOWN
            source = self._source(
                chat_id=chat_id, user_id=user_id, profile=profile, user_name=label
            )
            if _not_routed(source, profile):
                return AuthorizeResult(authz=AuthzState.NOT_ROUTED)
            event = self._hermes.inert_trigger_event(
                source=source, user_id=user_id, user_name=label
            )
            real_loop = loop if loop is not None else asyncio.get_running_loop()
            adapter = self._adapter
            future = asyncio.run_coroutine_threadsafe(adapter.handle_message(event), real_loop)
        except Exception as exc:
            log_bridge_exception(exc)
            return AuthorizeResult(authz=AuthzState.UNVERIFIABLE)
        self._pending_triggers.add(future)
        future.add_done_callback(self._trigger_done)
        log_event("p6_trigger", outcome="sent")
        return AuthorizeResult(authz=AuthzState.PENDING_OPERATOR)

    def _trigger_done(self, future: Any) -> None:
        self._pending_triggers.discard(future)
        if future.cancelled():
            return
        exc = future.exception()
        if exc is not None:
            log_bridge_exception(exc)

    # ------------------------------------------------------------------------------------------
    # Conversation reads (RO-3..RO-8). Never mint; failures raise BridgeError.
    # ------------------------------------------------------------------------------------------

    def conversation_ref(self, user_id: str, profile: str) -> ConversationRef | None:
        chat_id = self._directory.chat_id(user_id, profile)
        if chat_id is None:
            return None  # HMP never opened a chat for this bot: nothing to find
        source = self._source(chat_id=chat_id, user_id=user_id, profile=profile, user_name=None)
        if _not_routed(source, profile):
            raise BridgeError("source is not routed to the profile")
        key = self._hermes.build_session_key(source, profile)
        if not isinstance(key, str) or not key:
            raise BridgeError("no session key")
        session_store = getattr(self._adapter, "_session_store", None)
        if session_store is None:
            raise BridgeError("no session store")
        entry = session_store.lookup_by_session_key(key)
        if entry is None:
            return None  # the conversation was never started
        session_id = getattr(entry, "session_id", None)
        if not isinstance(session_id, str) or not session_id:
            return None
        return ConversationRef(user_id=user_id, profile=profile, session_id=session_id)

    @contextlib.contextmanager
    def _db(self, profile: str) -> Iterator[Any]:
        """The profile's own `SessionDB` (E-PRV-9), acquired from Hermes's shared registry and
        released afterwards. A missing database file is an error, never created here."""
        db_path = self._profile_home(profile) / STATE_DB_FILENAME
        if not db_path.is_file():
            raise BridgeError("session database missing")
        db = self._hermes.acquire(db_path)
        try:
            yield db
        finally:
            self._hermes.release(db)

    @staticmethod
    def _tip(db: Any, session_id: str) -> str:
        tip = db.resolve_resume_session_id(session_id)
        return tip if isinstance(tip, str) and tip else session_id

    def _rows(self, ref: ConversationRef, raw: object) -> list[Row]:
        if not isinstance(raw, list):
            raise BridgeError("message rows are not a list")
        chat_id = self._directory.chat_id(ref.user_id, ref.profile)
        out: list[Row] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise BridgeError("message row is not a mapping")
            role = item.get("role")
            role_str = role if isinstance(role, str) else ""
            text = _text_of(item.get("content"))
            tool_calls: tuple[WireToolCall, ...] = ()
            tool_name: str | None = None
            tool_call_id: str | None = None
            truncated = False
            # Hermes `messages` columns (hermes_state_common.py): `tool_calls` JSON on assistant
            # rows, `tool_name` and `tool_call_id` on tool rows. `get_messages` returns them.
            # Role is passed through. Tool text is capped here; the uncapped output is not kept.
            if role_str == "assistant":
                tool_calls = _tool_calls_of(item.get("tool_calls"))
            elif role_str == "tool":
                text, truncated = _cap_chars(text, TOOL_OUTPUT_CAP)
                tool_name = _optional_str(item.get("tool_name"))
                tool_call_id = _optional_str(item.get("tool_call_id"))
            out.append(
                Row(
                    id=_row_id(item.get("id")),
                    role=role_str,
                    text=text,
                    client_message_id=_cmid(item.get("platform_message_id"), chat_id),
                    created_at=_created_at(item.get("timestamp")),
                    tool_calls=tool_calls,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    truncated=truncated,
                )
            )
        return out

    def _read(self, fn: Any) -> Any:
        try:
            return fn()
        except BridgeError:
            raise
        except Exception as exc:
            raise BridgeError() from exc

    def head(self, ref: ConversationRef) -> int | None:
        def run() -> int | None:
            with self._db(ref.profile) as db:
                tip = self._tip(db, ref.session_id)
                rows = db.get_messages(tip, latest=True, limit=1)
            parsed = self._rows(ref, rows)
            return parsed[-1].id if parsed else None

        return self._read(run)

    def latest(self, ref: ConversationRef, limit: int) -> list[Row]:
        def run() -> list[Row]:
            with self._db(ref.profile) as db:
                tip = self._tip(db, ref.session_id)
                rows = db.get_messages(tip, latest=True, limit=limit)
            return self._rows(ref, rows)

        return self._read(run)

    def after(self, ref: ConversationRef, after_id: int, limit: int) -> list[Row] | ResetReason:
        """Rows strictly after `after_id`, or the reset that the cursor calls for. `after_id` 0
        means "from the start". A cursor row that exists but is no longer active was rewritten
        (RO-8 (a)). One that does not exist in the lineage tip cannot be resolved."""

        def run() -> list[Row] | ResetReason:
            with self._db(ref.profile) as db:
                tip = self._tip(db, ref.session_id)
                if after_id > 0:
                    probe = db.get_messages(
                        tip, include_inactive=True, after_id=after_id - 1, limit=1
                    )
                    if not isinstance(probe, list):
                        raise BridgeError("message rows are not a list")
                    if not probe or not isinstance(probe[0], Mapping):
                        return ResetReason.CURSOR_NOT_RESOLVABLE
                    if probe[0].get("id") != after_id:
                        return ResetReason.CURSOR_NOT_RESOLVABLE
                    active = probe[0].get("active")
                    if active not in (0, 1):
                        raise BridgeError("row activity flag missing")
                    if active == 0:
                        return ResetReason.HISTORY_REWRITTEN
                rows = db.get_messages(tip, after_id=after_id, limit=limit)
            return self._rows(ref, rows)

        return self._read(run)

    def lineage(self, ref: ConversationRef) -> LineageInfo:
        def run() -> LineageInfo:
            with self._db(ref.profile) as db:
                chain_raw = db.get_compression_chain(ref.session_id)
                tip = self._tip(db, ref.session_id)
                ids_raw = db.get_active_message_ids(tip)
            chain = tuple(s for s in (chain_raw or ()) if isinstance(s, str) and s)
            if not isinstance(ids_raw, list):
                raise BridgeError("active ids are not a list")
            ids = [_row_id(i) for i in ids_raw]
            return LineageInfo(
                session_id=ref.session_id,
                lineage_tip=tip,
                head_row_id=max(ids) if ids else None,
                active_row_count=len(ids),
                chain=chain or (ref.session_id,),
            )

        return self._read(run)

    # ------------------------------------------------------------------------------------------
    # Amendment A1 (session browsing, OD-F9/OD-F10): SES-1 list, SES-2 resolve
    # ------------------------------------------------------------------------------------------

    def _session_summaries(self, raw: object) -> list[SessionSummary]:
        if not isinstance(raw, list):
            raise BridgeError("session rows are not a list")
        out: list[SessionSummary] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise BridgeError("session row is not a mapping")
            title = item.get("title")
            source = item.get("source")
            last_active = item.get("last_active")
            out.append(
                SessionSummary(
                    session_id=_session_id_of(item.get("id")),
                    title=title if isinstance(title, str) else None,
                    source=source if isinstance(source, str) else "",
                    started_at=_created_at(item.get("started_at")),
                    last_active_at=_created_at(last_active) if last_active is not None else None,
                    message_count=_message_count_of(item.get("message_count")),
                    hidden=bool(item.get("hidden")),
                )
            )
        return out

    def list_sessions(
        self,
        user_id: str,
        profile: str,
        *,
        sources_excluded: Sequence[str],
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        """§1.1 `list_sessions_rich`. `include_hidden=True` (OD-F11 amendment ruling, 2026-09-27):
        the canonical "Bot Chat" a bot's Desktop view opens is always created hidden
        (`hermes-agent`'s `apps/desktop/src/plugins/hermes-bots/canonical-chat.ts`,
        `createCanonicalChat`'s `session.create` call, `hidden: true`), so it would never appear
        at all under the previous `include_hidden=False`. This bridge call stays a generic,
        unfiltered session list -- exactly what OD-F9/OD-F10 originally asked for; `reads.py`'s
        `_is_bot_view_session` selector (OD-F11) narrows the result down to the bot's own chat
        plus the caller's, never disclosing an arbitrary hidden session to the wire."""
        del user_id  # the read is profile-scoped; no per-user Hermes-side filter exists (OD-F10)

        def run() -> list[SessionSummary]:
            with self._db(profile) as db:
                raw = db.list_sessions_rich(
                    exclude_sources=list(sources_excluded) or None,
                    limit=limit,
                    offset=offset,
                    include_children=False,
                    include_archived=False,
                    include_hidden=True,
                    order_by_last_active=True,
                    project_compression_tips=True,
                )
            return self._session_summaries(raw)

        return self._read(run)

    def resolve_session(
        self, user_id: str, profile: str, session_id: str
    ) -> ConversationRef | None:
        def run() -> ConversationRef | None:
            with self._db(profile) as db:
                row = db.get_session(session_id)
            if row is None:
                return None
            if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
                raise BridgeError("session row is not a mapping")
            return ConversationRef(user_id=user_id, profile=profile, session_id=session_id)

        return self._read(run)

    # ------------------------------------------------------------------------------------------
    # GU-2 input
    # ------------------------------------------------------------------------------------------

    def capability_versions(self) -> Mapping[str, int]:
        """A copy of Hermes's capability map, unfiltered: `gate.py` treats every non-integer
        value as absent (DR-12). An absent map, or one that is not a mapping, is empty."""
        try:
            caps = self._hermes.capability_map()
        except Exception as exc:
            log_bridge_exception(exc)
            return {}
        if not isinstance(caps, Mapping):
            return {}
        return {str(k): v for k, v in caps.items()}

    # ------------------------------------------------------------------------------------------
    # Amendment F2 (direct send, HMP_V1.md §7a DS-4/DS-6)
    # ------------------------------------------------------------------------------------------

    def resolve_bot_chat(self, profile: str) -> BotChatTarget | None:
        """DS-4(2): the canonical Bot Chat's live compression tip, its current head, and its FULL
        compression lineage (for DS-4(3)'s "every id in the chain" busy check). `None` when no row
        titled exactly `"Bot Chat"` exists for this profile yet -- never created here (DS-9).

        Review BLOCKER #2: compression moves the title onto the child and clears it from the
        ancestor, so `get_session_by_title` can hand back an id anywhere in the lineage.
        `get_compression_lineage` (`hermes_state_compression.py:689-719`) walks parents only while
        `_is_compression_child_row`, and returns `[session_id]` alone when its forward spine omits
        the start id (line 719). Review round 3: independently walk `parent_session_id` upward from
        the live tip via `SessionDB.get_session` (`hermes_state_sessions.py:786`, a supported read)
        and union those ids with the lineage result. If that walk cannot be established with
        certainty, raise `BridgeError` — the send path fails closed as `session_busy`."""

        def run() -> BotChatTarget | None:
            with self._db(profile) as db:
                row = db.get_session_by_title(_CANONICAL_BOT_CHAT_TITLE)
                if row is None:
                    return None
                if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
                    raise BridgeError("session row is not a mapping")
                titled_id = row["id"]
                tip = self._tip(db, titled_id)
                lineage_raw = db.get_compression_lineage(titled_id)
                if not isinstance(lineage_raw, (list, tuple)):
                    raise BridgeError("compression lineage uncertain")
                from_tip = _parent_chain(db, tip)
                if from_tip is None:
                    raise BridgeError("compression lineage uncertain")
                from_titled = from_tip if titled_id == tip else _parent_chain(db, titled_id)
                if from_titled is None:
                    raise BridgeError("compression lineage uncertain")
                chain = _union_session_ids(from_tip, from_titled, lineage_raw, titled_id, tip)
                if not chain or tip not in chain or titled_id not in chain:
                    raise BridgeError("compression lineage uncertain")
                head_rows = db.get_messages(tip, latest=True, limit=1)
            if not isinstance(head_rows, list):
                raise BridgeError("message rows are not a list")
            head_message_id = (
                _row_id(head_rows[-1].get("id"))
                if head_rows and isinstance(head_rows[-1], Mapping)
                else None
            )
            return BotChatTarget(
                # Lineage root (chain is root-first), stable across compression. The titled id can
                # be the tip after the title moves; the lock and the lease check both need the root.
                root_session_id=chain[0],
                live_tip_session_id=tip,
                head_message_id=head_message_id,
                compression_chain=chain,
            )

        return self._read(run)

    def lease_snapshot(self, profile: str) -> list[Mapping[str, object]] | None:
        """DS-4(3): the target profile's own lease-registry snapshot. `None` on ANY failure --
        "ownership uncertainty fails CLOSED", the same discipline `try_acquire_active_session`
        documents for its own callers. Never raises: a guard caller MUST treat `None` as busy,
        never as "not busy"."""
        try:
            home = self._profile_home(profile)
            raw = self._hermes.active_session_registry_snapshot(home)
        except Exception as exc:
            log_bridge_exception(exc)
            return None
        if not isinstance(raw, list):
            return None
        out: list[Mapping[str, object]] = []
        for entry in raw:
            if not isinstance(entry, Mapping):
                return None
            out.append(entry)
        return out

    def direct_send_endpoint(self, profile: str) -> DirectSendEndpoint | None:
        """DS-2(b)/DS-6: the resolved `api_server` bind and this profile's own `API_SERVER_KEY`.
        `None` on any ambiguity (fail closed) -- an unresolvable config read, a non-loopback bind,
        or an empty/unusable key. Replicates `listen_address`'s own two-line precedence
        (`extra.get("host", os.getenv("API_SERVER_HOST", "127.0.0.1"))`) rather than importing
        that function itself (avoiding a private-adapter-module import, §1.9.1's own reasoning) --
        this small replica is exactly what DS-6 calls for, not a shortcut around it.

        Review BLOCKER #3 (loopback): `host` is never used as given. `"localhost"` -- a name, not a
        literal -- is rewritten to the IPv4 loopback literal immediately; anything else that is not
        already exactly `127.0.0.1` or `::1` fails closed. Review round 3: this function does not
        open its own probe socket. The aiohttp request (`direct_send.aiohttp_loopback_call`) is the
        verification — its connector is pinned to this literal, and a failed connect is
        `api_server_unavailable`. A separate connect-then-close left a gap before the bearer token
        was sent.

        Review should-fix #5 (key coupling): `extra.get("key")` is read FIRST for the default
        profile, exactly like `api_server.py`'s own `self._api_key = extra.get("key", ...)`
        (api_server.py:1191). Review round 3: that inline key must also clear the `min_length=16`
        floor (`hermes_cli.auth.has_usable_secret`); a short value fails closed here (gate closed),
        and is not sent on to become a 401. A named profile never reads `extra.key` at all -- only
        its own scoped secret, under the same floor (a partial mirror -- length only, see
        `_has_usable_secret`)."""
        try:
            home = self._profile_home(profile)
            served = self.served_profiles()
            is_default = bool(served) and profile == served[0]
            with self._hermes.profile_runtime_scope(home):
                extra = self._hermes.api_server_extra()
                scoped_key = self._hermes.scoped_api_server_key()
        except Exception as exc:
            log_bridge_exception(exc)
            return None
        if not isinstance(extra, Mapping):
            return None
        host = extra.get("host")
        if not isinstance(host, str) or not host:
            host = os.environ.get("API_SERVER_HOST", DEFAULT_API_SERVER_HOST)
        if host == _LOCALHOST_ALIAS:
            host = DEFAULT_API_SERVER_HOST  # never resolve the name ourselves (BLOCKER #3)
        if host not in _LOOPBACK_LITERALS:
            return None  # fail closed: never trust an unresolved hostname or non-loopback bind
        raw_port = extra.get("port")
        if raw_port is None:
            raw_port = os.environ.get("API_SERVER_PORT", str(DEFAULT_API_SERVER_PORT))
        try:
            port = int(raw_port)
        except (TypeError, ValueError):
            return None
        if is_default:
            raw_key = extra.get("key")
            # A present inline key is authoritative (api_server.py:1191). Too short → fail closed,
            # do not fall back to the scoped secret and do not hand the short value to the call.
            if isinstance(raw_key, str) and raw_key.strip():
                key = raw_key if _has_usable_secret(raw_key) else ""
            else:
                key = scoped_key if isinstance(scoped_key, str) else ""
        else:
            key = scoped_key if _has_usable_secret(scoped_key) else ""
        if not key:
            return None  # no usable key: the gate stays closed (never a short key, never a 401)
        prefix = "" if is_default else f"/p/{quote(profile, safe='')}"
        return DirectSendEndpoint(host=host, port=port, api_key=key, path_prefix=prefix)
