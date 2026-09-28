"""P6 bot authorization (`POST /bots/{p}/authorize`): the PR6-1 outcome table, no code relay
(PR6-2), the instance-wide note (PR6-3). Hermes is reached only through the bridge. T029.

PR6-1, decided only by Hermes's own per-profile stores, failing closed:

- `authorized` → `200 {"authz":"authorized"}`;
- `refused_allow_all` (allow-all in either scope, or the canary is admitted) →
  `409 refused_allow_all {authz}`;
- `not_routed` / `not_served` → `409 not_routed {authz}`;
- `unverifiable` (the query failed, or could not be scoped) →
  `503 other {authz:"unverifiable", why:"unverifiable"}`;
- `pending_operator` → the inert trigger is sent, then
  `202 {"authz":"pending_operator", "user_id", "instruction", "approve_command", "note"?}`.

- **`approve_command` (owner requirement, 2026-09-27).** A new optional 202 field: one
  copy-pasteable POSIX shell command that lists this profile's pending `hmp` requests, filters
  them to this call's own `user_id`, and approves each match. HMP v1 V-3 makes this additive:
  "Revisions `1.x` are additive only: new optional response fields...". A pre-1.x client that has
  never heard of the field ignores it under V-4 ("ignore unknown response fields"). The field
  carries the exact same no-assertion and no-code-relay properties as `instruction` (SR-5, PR6-2):
  if no request is pending the `awk` filter matches nothing and the loop is a no-op, and the
  command never contains a Hermes pairing code -- only the profile name and this call's own
  `user_id`, both already known to the caller.

- **Chats row.** For `pending_operator` only, the user's `chats` row for this bot is minted before
  the trigger, so the trigger and any later conversation share one Hermes session key. This is the
  one place a `chats` row is minted. Reads never mint one (R11).
- **PR6-2, no code relay.** Hermes's reply to the trigger (a pairing code) goes to the adapter's
  `send`, which drops it unlogged. Nothing the bridge returns besides the `authz` state reaches the
  response. The response is built only from fixed text, the served profile name and the caller's
  own `user_id`.
- **PR6-3 / OD-F6(c).** `note` is present when a transport-scope env allowlist, or a non-empty
  `platforms.hmp.extra.allow_from`, is active: either is instance-wide (E-GAP-31, SR-1). HMP only
  discloses existing grants. It never creates, widens or edits one: this module writes nothing to
  Hermes, and the bridge's only hand-off is the inert trigger. The operator approves through
  Hermes's own CLI.
- **SR-5 cooldown.** A per-`(user, profile)` cooldown (`AUTHORIZE_TRIGGER_COOLDOWN_S`, at least
  Hermes's own per-user pairing rate-limit window) is kept in the store. A call inside the window
  sends no trigger; `state` stays whatever the last read showed. Because HMP can never confirm
  Hermes actually created a pending request from a trigger it sent -- it may be rate-limited
  internally, its pending-code slots may be full, or its unauthorized-DM policy may be
  `ignore`/`decline` -- the instruction text is always worded conditionally, whether or not this
  call sent a trigger.
"""

from __future__ import annotations

import contextlib
import shlex
import time
from collections.abc import Callable
from typing import Any

from . import crypto
from .contract import (
    AUTHORIZE_TRIGGER_COOLDOWN_S,
    CONVERSATION_ID,
    PLATFORM_NAME,
    AuthzState,
    ErrorCode,
    HmpError,
    OtherWhy,
    ReadBridge,
)
from .logging_policy import log_bridge_exception

CHAT_ID_PREFIX = "c_"  # §2: `c_` + 128-bit random

INSTANCE_WIDE_NOTE = (
    "This Hermes instance has an instance-wide allowlist for mobile users. A grant made that way "
    "applies to every bot and every paired device on this instance, not only to this request."
)


def operator_instruction(profile: str, user_id: str) -> str:
    """The fixed PR6-1 operator instruction, worded conditionally (SR-5): HMP hands Hermes an
    inert trigger, but it cannot confirm Hermes actually created a pending request from it --
    Hermes may already be rate-limiting this user, its pending-code slots may be full, its
    `unauthorized_dm_behavior` may be `ignore`/`decline`, or this call may have been inside HMP's
    own cooldown and sent no trigger at all. The wording must never assert a request exists. It
    never contains a Hermes pairing code (PR6-2)."""
    p = shlex.quote(profile)
    return (
        f"If a {PLATFORM_NAME} pairing request for user {user_id} appears in "
        f"'hermes -p {p} pairing list', approve it with "
        f"'hermes -p {p} pairing approve {PLATFORM_NAME} <request_id>'."
    )


def approve_command(profile: str, user_id: str) -> str:
    """The `approve_command` 202 field (owner requirement, 2026-09-27; additive under HMP v1 V-3):
    one copy-pasteable POSIX shell command that finds this user's own pending `hmp` request(s) on
    `profile` and approves each. Built entirely from `hermes pairing list`/`pairing approve`, the
    served profile name and the caller's own `user_id` (never a Hermes pairing code, PR6-2) --
    the same two values already in `instruction`. `profile` and `user_id` are each `shlex.quote`d
    as standalone shell words, so a profile name with spaces, quotes or shell metacharacters is
    still safe; `user_id` is passed to `awk` as a `-v` argument (not interpolated into the awk
    program text), so it needs no separate awk-syntax escaping. `$1`/`$2`/`$3` (Platform/Request
    ID/User ID) are the first three whitespace-separated columns of `pairing list`'s table and stay
    aligned even when a later column (Name) contains spaces. If nothing is pending the `awk` filter
    matches no row and the loop runs zero times: this never asserts a request exists (SR-5), same
    as `instruction`."""
    p = shlex.quote(profile)
    u = shlex.quote(user_id)
    return (
        f"hermes -p {p} pairing list | "
        f"awk -v u={u} '$1==\"{PLATFORM_NAME}\" && $3==u {{print $2}}' | "
        f"while read -r id; do hermes -p {p} pairing approve {PLATFORM_NAME} \"$id\"; done"
    )


def new_chat_id() -> str:
    return CHAT_ID_PREFIX + crypto.random_bytes(16).hex()


def ensure_chat(store: Any, user_id: str, profile: str) -> str:
    """The user's `chats` row for this bot, minted once. Never overwritten: an existing row
    keeps its `chat_id`, so the conversation's session key never moves."""
    with store.transaction() as conn:
        row = conn.execute(
            "SELECT chat_id FROM chats WHERE user_id = ? AND profile = ? AND conversation_id = ?",
            (user_id, profile, CONVERSATION_ID),
        ).fetchone()
        if row is not None:
            return str(row["chat_id"])
        chat_id = new_chat_id()
        conn.execute(
            "INSERT INTO chats (user_id, profile, conversation_id, chat_id) VALUES (?, ?, ?, ?)",
            (user_id, profile, CONVERSATION_ID, chat_id),
        )
        return chat_id


class Authorize:
    def __init__(
        self,
        bridge: ReadBridge,
        store: Any,
        *,
        clock: Callable[[], int] = lambda: int(time.time()),
        on_served_profiles: Callable[[list[str]], None] | None = None,
    ) -> None:
        self._bridge = bridge
        self._store = store
        self._clock = clock
        # Live-bug fix (multiplexed gateway): same hook `reads.Reads` takes, called after a
        # successful `authorize()` -- opportunistically, with its own `served_profiles()` call,
        # since `authorize()` has no reason to fetch the served set for itself. Kept optional and
        # never allowed to affect the response (see `authorize()` below).
        self._on_served_profiles = on_served_profiles

    def _state(self, user_id: str, profile: str) -> AuthzState:
        try:
            return self._bridge.authz_state(user_id, profile)
        except Exception as exc:  # the bridge fails closed itself; this is belt and braces
            log_bridge_exception(exc)
            return AuthzState.UNVERIFIABLE

    def _cooldown_active(self, user_id: str, profile: str, now: int) -> bool:
        row = self._store.get_authorize_cooldown(user_id, profile)
        if row is None:
            return False
        return now - int(row["last_trigger_at"]) < AUTHORIZE_TRIGGER_COOLDOWN_S

    def authorize(
        self, user_id: str, profile: str, *, loop: Any = None
    ) -> tuple[int, dict[str, object]]:
        """`loop` (SR-4): the real event loop, passed through to the bridge's P6 hand-off, for
        when this whole call itself runs off the loop (`server.py`'s `asyncio.to_thread`)."""
        state = self._state(user_id, profile)
        if state is AuthzState.PENDING_OPERATOR:
            ensure_chat(self._store, user_id, profile)
            now = int(self._clock())
            if not self._cooldown_active(user_id, profile, now):
                self._store.set_authorize_cooldown(user_id, profile, now)
                try:
                    state = self._bridge.request_authorization(user_id, profile, loop=loop).authz
                except Exception as exc:
                    log_bridge_exception(exc)
                    state = AuthzState.UNVERIFIABLE
            # else (SR-5): inside the cooldown window -- send no trigger. `state` stays
            # PENDING_OPERATOR; the caller still gets a 202 with the (conditional) instruction.
        if self._on_served_profiles is not None:
            try:
                served = self._bridge.served_profiles()
            except Exception as exc:  # the bridge fails closed itself; belt and braces
                log_bridge_exception(exc)
            else:
                with contextlib.suppress(Exception):  # never break an authorize read
                    self._on_served_profiles(served)
        return self._outcome(state, user_id, profile)

    def _outcome(
        self, state: AuthzState, user_id: str, profile: str
    ) -> tuple[int, dict[str, object]]:
        if state is AuthzState.AUTHORIZED:
            return 200, {"authz": state.value}
        if state is AuthzState.REFUSED_ALLOW_ALL:
            raise HmpError(ErrorCode.REFUSED_ALLOW_ALL, authz=state.value)
        if state in (AuthzState.NOT_ROUTED, AuthzState.NOT_SERVED):
            raise HmpError(ErrorCode.NOT_ROUTED, authz=state.value)
        if state is AuthzState.PENDING_OPERATOR:
            body: dict[str, object] = {
                "authz": state.value,
                "user_id": user_id,
                "instruction": operator_instruction(profile, user_id),
                "approve_command": approve_command(profile, user_id),
            }
            if self._instance_wide(profile):
                body["note"] = INSTANCE_WIDE_NOTE
            return 202, body
        # UNVERIFIABLE, or anything unexpected: fail closed.
        raise HmpError(
            ErrorCode.OTHER,
            503,
            authz=AuthzState.UNVERIFIABLE.value,
            why=OtherWhy.UNVERIFIABLE.value,
        )

    def _instance_wide(self, profile: str) -> bool:
        try:
            return bool(self._bridge.instance_wide_grant(profile))
        except Exception as exc:  # unknown: disclose rather than hide
            log_bridge_exception(exc)
            return True
