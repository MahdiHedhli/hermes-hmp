"""Reads (T030): the roster (RO-1, RO-2), the snapshot (RO-3, RO-4, RO-5), history and its resets
(RO-6, RO-8), and the persisted session baselines. Hermes is reached only through a
`contract.ReadBridge`.

Order, per route:
- **Roster.** The served set and each bot's `authz`, and nothing else about a bot's authorization
  state (RO-1, SEC-2). `display_name` is presentation only, derived purely from `profile`
  (`_fallback_display_name`; no Hermes read). Hermes's own stored `profile.yaml` `display_name`
  is deferred: reading it would add `hermes_cli/profiles.py` to the read bridge's fingerprinted
  file set and requalify every build (see HMP_V1.md §2, `docs/research/HERMES_PLUGIN_DURABILITY.md`
  §(c)).
- **Snapshot.** `tail` is read first (RO-4). Then the per-bot gate runs (ERR-3, FR-051: authorize
  before any lookup), then the conversation is resolved. A conversation that was never started
  returns an empty snapshot with `head_message_id: null`. Nothing is minted: no `chats` row, no
  Hermes session (FR-036, R11).
- **History.** The gate first, then the reset checks, then the rows.

Only `default` exists (§2). The route table registers no other conversation id, so any other id is
`404 not_found` before this module runs (FR-051).

**Session baselines (RO-6, RO-8; `session_baselines`).** After every snapshot and history read,
the observed lineage of `(user, profile)` is persisted: the routed session id, the lineage tip, the
head row id and the active row count. Because the baseline is in the store, a replacement that
happens while HMP is not running is still reported as `session_replaced` (FR-052). A history read
compares the current lineage with the baseline:

- a baseline exists, and the conversation no longer resolves (the route was pruned or
  replaced) → `session_replaced`;
- the routed session changed, and the new one is in the old one's compression chain →
  `lineage_changed`;
- the routed session changed otherwise (`/new`, auto-reset, `cli_close`) → `session_replaced`;
- same session, and the lineage tip moved (a compression continuation) → `lineage_changed`;
- same tip, and the active row count dropped below the baseline's (RO-8 (b)) →
  `history_rewritten`;
- the cursor row exists but is no longer active (RO-8 (a); bridge) → `history_rewritten`;
- the cursor row does not exist in the lineage tip (bridge) → `cursor_not_resolvable`;
- no conversation and no baseline, with a cursor > 0 → `cursor_not_resolvable`.

A baseline is per user and profile, not per device. After one device has observed a change,
another device that still holds an old cursor gets `history_rewritten` or `cursor_not_resolvable`,
never rows. Every one of these is a reset: the client refetches the snapshot, so nothing is lost
silently (V-4). RO-8 (c), an upstream compaction epoch, does not exist yet (P13); detection is
heuristic until it does (RES-10).

A bridge failure while reading conversation state is `500 other {why:"internal_error"}`, logged by
exception type only. It is never an empty conversation.
"""

from __future__ import annotations

import contextlib
import re
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import wire
from .contract import (
    CONVERSATION_ID,
    HISTORY_RESET_REASONS,
    PER_BOT_GATE_REFUSALS,
    SESSION_SOURCE_MAX_BYTES,
    SESSION_TITLE_MAX_BYTES,
    SESSIONS_CURSOR_MAX_BYTES,
    AuthzState,
    ConversationRef,
    ErrorCode,
    Guarantees,
    HistoryPage,
    HistoryReset,
    HmpError,
    LineageInfo,
    OtherWhy,
    ReadBridge,
    ResetReason,
    RosterBot,
    RosterResponse,
    Row,
    SessionListItem,
    SessionListResponse,
    SessionSnapshot,
    SessionSummary,
    SnapshotResponse,
    TailPosition,
    TurnObservation,
    TurnObservedState,
    WireMessage,
    WriteGate,
)
from .logging_policy import log_bridge_exception
from .prompts import phone_open_request

# Amendment A1 (session browsing, SES-1a): the opaque session_ref prefix, matching the §13-style
# identifier convention (`device_id`, `pairing_id`, ...): a fixed tag plus b64u of random bytes.
SESSION_REF_PREFIX = "ses1_"
SESSION_REF_RANDOM_BYTES = 16


def _new_epoch() -> str:
    """The per-process `epoch` (§2): a fresh opaque value on every HMP process start."""
    return secrets.token_hex(8)


def _wire(row: Row) -> WireMessage:
    """RO-3 / RO-6 / SES-2 message item. Tool fields are omitted when the row has none (V-3)."""
    return WireMessage(
        id=row.id,
        role=row.role,
        text=row.text,
        client_message_id=row.client_message_id,
        created_at=row.created_at,
        tool_calls=row.tool_calls or None,
        tool_name=row.tool_name,
        tool_call_id=row.tool_call_id,
        truncated=True if row.truncated else None,
    )


def _internal_error(exc: BaseException) -> HmpError:
    log_bridge_exception(exc)
    return HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value)


def require_bot_authorized(bridge: ReadBridge, user_id: str, profile: str) -> None:
    """ERR-3: the per-bot query first, and fail closed. Nothing else runs on refusal. Public
    (not `Reads`-internal) so every `/bots/{p}/...` route uses the identical check, including the
    amendment F2 direct-send route (`server.py`), which is not itself a `Reads` method."""
    try:
        authz = bridge.authz_state(user_id, profile)
    except Exception as exc:
        log_bridge_exception(exc)
        authz = AuthzState.UNVERIFIABLE
    if authz is AuthzState.AUTHORIZED:
        return
    refusal = PER_BOT_GATE_REFUSALS.get(authz)
    if refusal is None:  # never expected: fail closed as unverifiable
        authz = AuthzState.UNVERIFIABLE
        refusal = PER_BOT_GATE_REFUSALS[authz]
    extras: dict[str, object] = {"authz": authz.value}
    if refusal.why is not None:
        extras["why"] = refusal.why.value
    raise HmpError(refusal.code, refusal.http, **extras)


# The desktop app's own word-splitting: runs of `-`/`_` become spaces, and `\b\w` (a word-initial
# character) is uppercased -- interior case is left exactly as the profile id spells it, which is
# always lowercase (`_PROFILE_ID_RE`), so this reads identically to the JS original.
_WORD_INITIAL_RE = re.compile(r"\b\w")


def _fallback_display_name(profile: str) -> str:
    """FR-028: `profile`'s roster `display_name`, presentation only. The SAME rule the Hermes
    desktop app applies to an unnamed profile -- never the raw id -- mirroring `displayName` in
    `apps/desktop/src/plugins/hermes-bots/labels.ts` (lines 54-63 of the reviewed build), reduced
    to what HMP has: no Bot Mode title and no remote-source label, only the profile id.

    This is currently the ONLY source: HMP does not read Hermes's own stored `profile.yaml`
    `display_name` (deferred -- it would add `hermes_cli/profiles.py` to the read bridge's
    fingerprinted file set and force every qualified build to be requalified; see HMP_V1.md §2
    and `docs/research/HERMES_PLUGIN_DURABILITY.md` §(c)). "Fallback" names this function for
    when that read lands; today it is unconditional.

    - the primary profile, id `"default"`, reads as `"Hermes"` (labels.ts:54-59);
    - anything else has its `-`/`_` runs turned into single spaces, then each word is
      capitalized (labels.ts:61-63: `replace(/[-_]+/g, ' ')` then `replace(/\\b\\w/g, ...)`).

    Pure and total: never raises, and an empty/blank id maps to itself (empty), exactly as the
    JS does (`''.replace(...) === ''`)."""
    name = (profile or "").strip()
    if name.lower() == "default":
        return "Hermes"
    raw = re.sub(r"[-_]+", " ", name).strip()
    return _WORD_INITIAL_RE.sub(lambda m: m.group().upper(), raw)


# --------------------------------------------------------------------------------------------------
# Amendment A1 (session browsing, SES-1a/SES-1b/SES-1e): ref minting, neutralization, cursor
# --------------------------------------------------------------------------------------------------


def _new_session_ref() -> str:
    """A fresh candidate `session_ref` (SES-1a). Only ever used as the value the store mints,
    or discards in favor of an existing one for the same `(user_id, profile, session_id)`."""
    return SESSION_REF_PREFIX + wire.b64u_encode(secrets.token_bytes(SESSION_REF_RANDOM_BYTES))


def _neutral_title(title: str | None) -> str | None:
    """SES-1b: `title` is Hermes/host-controlled text (model-generated or operator-set) and is
    never treated as trusted markup. `None` stays `None` (the client shows its own placeholder)."""
    if title is None:
        return None
    return wire.neutralize_text(title, max_bytes=SESSION_TITLE_MAX_BYTES)


def _neutral_source(source: str) -> str:
    """SES-1b: same treatment as `title`. An empty result after neutralization is still a valid
    (if uninformative) source label; the client's badge rule already renders an unrecognized
    value as "Other" (`ux-states.md`)."""
    return wire.neutralize_text(source, max_bytes=SESSION_SOURCE_MAX_BYTES)


def _encode_sessions_cursor(offset: int) -> str:
    """SES-1e: an **offset** cursor, never signed -- tampering can only change which offset is
    read within the caller's own already-authorized, already-profile-scoped query."""
    return wire.b64u_encode(wire.dump_json({"v": 1, "o": offset}))


#: OD-F11 (owner ruling, 2026-09-27, via the controller): "bot chats are only done in one channel
#: at a time... just the ones from the bot view", superseding OD-F10's "all sessions of approved
#: bots" breadth for the SESSION SET listed (bot-level authorization, ERR-3, is unchanged -- OD-F11
#: narrows WHICH sessions of an authorized bot are shown, not who may see them). This is the exact
#: literal Hermes's own Bot Mode identity uses in three independent places, cross-checked for this
#: amendment (all read-only):
#:   - `~/.hermes/hermes-agent/apps/desktop/src/plugins/hermes-bots/canonical-chat.ts`:
#:     `export const CANONICAL_CHAT_TITLE = 'Bot Chat'`, and the Desktop Bots view's own selector,
#:     `isCanonicalBotChatHistory`: `rootTitle === CANONICAL_CHAT_TITLE || (!rootTitle && title ===
#:     CANONICAL_CHAT_TITLE)` -- i.e. exact title match, tolerant of a compression lineage's root
#:     vs. tip title field naming;
#:   - `~/.hermes/hermes-agent/tools/bot_mode_probe.py:31`: `BOT_CHAT_TITLE = "Bot Chat"` ("the
#:     only session title that receives the protocol section... Must match the desktop plugin's
#:     createCanonicalChat title");
#:   - `~/.hermes/hermes-agent/hermes_state.py`, `SessionDB.CANONICAL_BOT_CHAT_TITLE = "Bot Chat"`,
#:     used by `_set_session_title`'s own identity rule: "Hidden is the discriminator: canonical
#:     chats are born hidden; a visible session merely named 'Bot Chat' stays renameable."
_CANONICAL_BOT_CHAT_TITLE = "Bot Chat"


def _is_bot_view_session(summary: SessionSummary) -> bool:
    """OD-F11: is `summary` a session Hermes Desktop's own Bots view would show for this bot --
    i.e. the bot's one canonical "Bot Chat"? See `_CANONICAL_BOT_CHAT_TITLE`'s docstring for the
    three independent Hermes-side sources this mirrors.

    `list_sessions_rich`'s own compression-tip projection (`_project_compression_tips`,
    `hermes_state_sessions.py`) already backfills a compressed tip's `title` from its root when
    the tip's own title is unset, so the single `title` field `list_sessions_rich` returns already
    plays the role Desktop's separate `root_title`/`title` pair plays -- there is nothing else to
    check for the lineage case.

    `hidden` is checked too, matching `_set_session_title`'s own stated identity rule exactly
    (hidden is what makes a "Bot Chat"-titled row canonical rather than an ordinary session a user
    happened to name the same thing, which Hermes itself allows to be renamed away freely). Since
    Hermes additionally enforces `sessions.title` uniqueness (`canonical-chat.ts`: "the core
    UNIQUE(title) index makes (profile, 'Bot Chat') an exact registry"), the `hidden` check is
    defense in depth here, not the only thing standing between an ordinary session and this
    selector -- but it is cheap, already available from `list_sessions_rich`, and it is what
    Hermes's own source treats as authoritative, so this checks it explicitly rather than relying
    only on the uniqueness constraint holding in every observed build.

    Never a source-based check: OD-F11 identifies the bot's own chat by TITLE, and explicitly
    excludes every channel-originated session (cli, telegram, discord, cron, ...) regardless of
    its own title, unless it happens to be the one row that is both hidden and titled "Bot Chat".
    """
    return summary.title == _CANONICAL_BOT_CHAT_TITLE and summary.hidden


def _decode_sessions_cursor(text: str) -> int:
    """The inverse of `_encode_sessions_cursor`. A malformed cursor is `400 bad_request` (SES-4)."""
    try:
        raw = wire.b64u_decode_bounded(text, max_length=SESSIONS_CURSOR_MAX_BYTES)
        obj = wire.parse_ijson(raw, max_bytes=SESSIONS_CURSOR_MAX_BYTES)
    except wire.WireError as exc:
        raise HmpError(ErrorCode.BAD_REQUEST) from exc
    if not isinstance(obj, dict) or obj.get("v") != 1:
        raise HmpError(ErrorCode.BAD_REQUEST)
    offset = obj.get("o")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return offset


class Reads:
    def __init__(
        self,
        bridge: ReadBridge,
        store: Any,
        *,
        iid: str,
        guarantees: Callable[[], Guarantees],
        write_gate: Callable[[], WriteGate],
        clock: Callable[[], int] = lambda: int(time.time()),
        epoch: str | None = None,
        on_served_profiles: Callable[[Sequence[str]], None] | None = None,
        prompt_store: Any = None,
    ) -> None:
        self._bridge = bridge
        self._store = store
        self._iid = iid
        self._guarantees = guarantees
        self._write_gate = write_gate
        self._clock = clock
        # F1 serves no live tail (FR-053). The ring is empty, so the lower bound is `seq` 0 in
        # this process's epoch. It is still read first (RO-4), so the order holds when a tail
        # is added.
        self._epoch = epoch if epoch is not None else _new_epoch()
        # Live-bug fix (multiplexed gateway): the adapter's own hook, so a successful roster read
        # -- which already calls `served_profiles()` for free -- can keep the listener record's
        # `profiles` field current between the adapter's own periodic refresh ticks. `None` off a
        # build with no adapter wired in (tests, an unsupported build). Never allowed to affect
        # the response: any exception it raises is swallowed here, not propagated to the caller.
        self._on_served_profiles = on_served_profiles
        self._prompt_store = prompt_store

    # ------------------------------------------------------------------------------------------
    # RO-1 roster
    # ------------------------------------------------------------------------------------------

    def roster(self, user_id: str) -> RosterResponse:
        try:
            served = self._bridge.served_profiles()
        except Exception as exc:
            raise _internal_error(exc) from exc
        if self._on_served_profiles is not None:
            with contextlib.suppress(Exception):  # the hook must never break a roster read
                self._on_served_profiles(served)
        bots = []
        for profile in served:
            try:
                authz = self._bridge.authz_state(user_id, profile)
            except Exception as exc:  # the bridge fails closed itself; this is belt and braces
                log_bridge_exception(exc)
                authz = AuthzState.UNVERIFIABLE
            bots.append(
                RosterBot(
                    profile=profile, display_name=_fallback_display_name(profile), authz=authz
                )
            )
        return RosterResponse(
            instance=self._iid,
            served_at=int(self._clock()),
            guarantees=self._guarantees(),
            write_gate=self._write_gate(),
            bots=tuple(bots),
        )

    # ------------------------------------------------------------------------------------------
    # ERR-3 per-bot gate
    # ------------------------------------------------------------------------------------------

    def _gate(self, user_id: str, profile: str) -> None:
        """ERR-3: the per-bot query first, and fail closed. Nothing else runs on refusal."""
        require_bot_authorized(self._bridge, user_id, profile)

    # ------------------------------------------------------------------------------------------
    # Baselines (RO-6)
    # ------------------------------------------------------------------------------------------

    def _baseline(self, user_id: str, profile: str) -> Any:
        return self._store.get_session_baseline(user_id, profile)

    def _save_baseline(self, user_id: str, profile: str, lineage: LineageInfo) -> None:
        # SR-12: the persisted baseline does not carry `head_row_id` (removed; it was never read
        # back). `lineage.head_row_id` itself is still used live, for this read's own
        # `head_message_id` (see `_history` below).
        self._store.set_session_baseline(
            user_id,
            profile,
            lineage.session_id,
            lineage.lineage_tip,
            lineage.active_row_count,
            int(self._clock()),
        )

    def _drop_baseline(self, user_id: str, profile: str) -> None:
        with self._store.transaction() as conn:
            conn.execute(
                "DELETE FROM session_baselines WHERE user_id = ? AND profile = ?",
                (user_id, profile),
            )

    def _lineage_reset(
        self, ref: ConversationRef, baseline: Any, lineage: LineageInfo
    ) -> ResetReason | None:
        """The reset the baseline comparison calls for, or None (see the module table)."""
        base_session = str(baseline["session_id"])
        base_tip = str(baseline["lineage_tip"])
        base_count = int(baseline["active_row_count"])
        if base_session != lineage.session_id:
            old = ConversationRef(user_id=ref.user_id, profile=ref.profile, session_id=base_session)
            try:
                old_chain = self._bridge.lineage(old).chain
            except Exception as exc:  # cannot prove the same lineage: report the replacement
                log_bridge_exception(exc)
                return ResetReason.SESSION_REPLACED
            if lineage.session_id in old_chain or lineage.lineage_tip in old_chain:
                return ResetReason.LINEAGE_CHANGED
            return ResetReason.SESSION_REPLACED
        if base_tip != lineage.lineage_tip:
            return ResetReason.LINEAGE_CHANGED
        if lineage.active_row_count < base_count:
            return ResetReason.HISTORY_REWRITTEN
        return None

    # ------------------------------------------------------------------------------------------
    # RO-3 snapshot
    # ------------------------------------------------------------------------------------------

    def _tail(self) -> TailPosition:
        return TailPosition(epoch=self._epoch, seq=0)

    def snapshot(self, user_id: str, profile: str, limit: int) -> SnapshotResponse:
        tail = self._tail()  # RO-4: before any other state
        self._gate(user_id, profile)
        try:
            ref = self._bridge.conversation_ref(user_id, profile)
            if ref is None:
                if self._baseline(user_id, profile) is not None:
                    self._drop_baseline(user_id, profile)
                return self._empty_snapshot(tail, user_id, profile)
            lineage = self._bridge.lineage(ref)
            rows = self._bridge.latest(ref, limit)
        except HmpError:
            raise
        except Exception as exc:
            raise _internal_error(exc) from exc
        self._save_baseline(user_id, profile, lineage)
        durable = tuple(_wire(r) for r in rows)
        return SnapshotResponse(
            conversation_id=CONVERSATION_ID,
            session_id=lineage.lineage_tip,
            # The head is the newest active row id, read in the same query as the window (RO-7),
            # so it never names a row the client does not hold.
            head_message_id=rows[-1].id if rows else None,
            messages=self._with_observations(user_id, profile, durable),
            turn=TurnObservation(observed_state=TurnObservedState.UNKNOWN, since=None),
            partial=None,
            partial_lost=False,
            open_requests=self._phone_open_requests(user_id, profile),
            tail=tail,
        )

    def _empty_snapshot(
        self, tail: TailPosition, user_id: str = "", profile: str = ""
    ) -> SnapshotResponse:
        return SnapshotResponse(
            conversation_id=CONVERSATION_ID,
            session_id=None,
            head_message_id=None,
            messages=self._with_observations(user_id, profile, ()),
            turn=TurnObservation(observed_state=TurnObservedState.UNKNOWN, since=None),
            partial=None,
            partial_lost=False,
            open_requests=self._phone_open_requests(user_id, profile),
            tail=tail,
        )

    def _phone_open_requests(self, user_id: str, profile: str) -> tuple[Mapping[str, object], ...]:
        store = self._prompt_store
        if store is None or not user_id:
            return ()
        store.purge(int(self._clock()))
        return tuple(
            phone_open_request(row)
            for row in store.list_visible(self._iid, user_id, profile)
            if row.surface == "phone_chat"
        )

    def _with_observations(
        self, user_id: str, profile: str, durable: tuple[WireMessage, ...]
    ) -> tuple[WireMessage, ...]:
        """Phone-chat observations Hermes has not yet written. A durable row with the same text
        replaces the observation (AP-6)."""
        store = self._prompt_store
        if store is None or not user_id:
            return durable
        remaining = [row.text for row in durable]
        extra: list[WireMessage] = []
        for role, text, created_at in store.observations(self._iid, user_id, profile):
            if text in remaining:
                remaining.remove(text)
                continue
            extra.append(
                WireMessage(
                    id=store.next_provisional_id(),
                    role=role,
                    text=text,
                    client_message_id=None,
                    created_at=float(created_at),
                )
            )
        if not extra:
            return durable
        return durable + tuple(extra)

    # ------------------------------------------------------------------------------------------
    # RO-6 history
    # ------------------------------------------------------------------------------------------

    def history(
        self, user_id: str, profile: str, after: int, limit: int
    ) -> HistoryPage | HistoryReset:
        self._gate(user_id, profile)
        try:
            return self._history(user_id, profile, after, limit)
        except HmpError:
            raise
        except Exception as exc:
            raise _internal_error(exc) from exc

    def _history(
        self, user_id: str, profile: str, after: int, limit: int
    ) -> HistoryPage | HistoryReset:
        baseline = self._baseline(user_id, profile)
        ref = self._bridge.conversation_ref(user_id, profile)
        if ref is None:
            if baseline is not None:
                self._drop_baseline(user_id, profile)
                return HistoryReset(reason=ResetReason.SESSION_REPLACED)
            if after == 0:
                return HistoryPage(messages=(), head_message_id=None)
            return HistoryReset(reason=ResetReason.CURSOR_NOT_RESOLVABLE)

        lineage = self._bridge.lineage(ref)
        reason = self._lineage_reset(ref, baseline, lineage) if baseline is not None else None
        rows: list[Row] = []
        if reason is None:
            page = self._bridge.after(ref, after, limit)
            if isinstance(page, ResetReason):
                # Only RO-6 reasons go on the wire; anything else is still a reset.
                reason = (
                    page if page in HISTORY_RESET_REASONS else ResetReason.CURSOR_NOT_RESOLVABLE
                )
            else:
                rows = page
        self._save_baseline(user_id, profile, lineage)
        if reason is not None:
            return HistoryReset(reason=reason)
        head = lineage.head_row_id
        if rows:
            head = max(head or 0, rows[-1].id)
        return HistoryPage(messages=tuple(_wire(r) for r in rows), head_message_id=head)

    # ------------------------------------------------------------------------------------------
    # Amendment A1 (session browsing, OD-F9/OD-F10): SES-1 list, SES-2 messages
    # ------------------------------------------------------------------------------------------

    def list_sessions(
        self,
        user_id: str,
        profile: str,
        *,
        cursor: str | None,
        limit: int,
        sources_excluded: Sequence[str] = (),
    ) -> SessionListResponse:
        """SES-1. `sources_excluded` is a host-side narrowing on top of the client-facing default
        of "none" (controller ruling, 2026-09-27: `exclude_sources` default is empty). OD-F11
        (owner ruling, 2026-09-27, superseding OD-F10's breadth): the bridge call itself stays the
        generic "every session of this bot" read (`sources_excluded` is plumbing kept for a future
        host-side config, unused by F1 today), but only the bot's own canonical chat
        (`_is_bot_view_session`) and the caller's own session are kept in what actually goes on
        the wire -- never a CLI, Telegram, Discord or other channel session, whatever
        `sources_excluded` says."""
        self._gate(user_id, profile)
        offset = 0 if cursor is None else _decode_sessions_cursor(cursor)
        try:
            own_ref = self._bridge.conversation_ref(user_id, profile)
            summaries = self._bridge.list_sessions(
                user_id, profile, sources_excluded=sources_excluded, limit=limit, offset=offset
            )
        except HmpError:
            raise
        except Exception as exc:
            raise _internal_error(exc) from exc
        own_session_id = own_ref.session_id if own_ref is not None else None
        fetched = len(summaries)  # SES-1e/1f pagination refers to the RAW Hermes page, not the
        # OD-F11-filtered result below: a page can come back with zero visible rows and still
        # have more pages after it.
        summaries = [
            s
            for s in summaries
            if s.session_id == own_session_id or _is_bot_view_session(s)
        ]
        now = int(self._clock())
        items = []
        for s in summaries:
            ref = self._store.mint_or_get_session_ref(
                user_id, profile, s.session_id, _new_session_ref(), now
            )
            items.append(
                SessionListItem(
                    session_ref=ref,
                    title=_neutral_title(s.title),
                    source=_neutral_source(s.source),
                    started_at=int(s.started_at),
                    last_active_at=int(s.last_active_at) if s.last_active_at is not None else None,
                    message_count=s.message_count,
                    is_mobile=s.session_id == own_session_id,
                )
            )
        # SES-1f: no total count is exposed. `next_cursor` is null once the raw Hermes page comes
        # back short of `limit` -- the only signal a client gets for "no more pages". Under OD-F11
        # most raw pages contain 0-2 visible rows; a client may need several "load more" taps on a
        # very active profile before the next page's raw fetch is short of `limit`.
        next_cursor = _encode_sessions_cursor(offset + limit) if fetched == limit else None
        return SessionListResponse(sessions=tuple(items), next_cursor=next_cursor)

    def _resolve_other(self, user_id: str, profile: str, session_id: str) -> ConversationRef:
        """SES-2: the ref already resolved to `session_id` in the caller's own scope (`store.py`).
        A Hermes-side existence check that fails (the session no longer exists) is reported the
        same as an unknown `session_ref` (SES-4): `404 not_found`."""
        try:
            ref = self._bridge.resolve_session(user_id, profile, session_id)
        except Exception as exc:
            raise _internal_error(exc) from exc
        if ref is None:
            raise HmpError(ErrorCode.NOT_FOUND)
        return ref

    def _other_baseline(self, user_id: str, profile: str, session_id: str) -> Any:
        return self._store.get_other_session_baseline(user_id, profile, session_id)

    def _save_other_baseline(
        self, user_id: str, profile: str, session_id: str, lineage: LineageInfo
    ) -> None:
        self._store.set_other_session_baseline(
            user_id, profile, session_id, lineage.lineage_tip, lineage.active_row_count,
            int(self._clock()),
        )

    def _resolve_ref(self, user_id: str, profile: str, session_ref: str) -> str:
        """The per-bot gate runs before this (both callers below), so ref resolution never runs
        for an unauthorized caller (matches RO-3/RO-6: "authorize before any lookup", FR-051). A
        `ref` unknown, or minted for a different `(user_id, profile)`, is `404 not_found` --
        indistinguishable from a foreign ref (SES-1a: never disclosed as "exists but not yours")."""
        session_id = self._store.resolve_session_ref(user_id, profile, session_ref)
        if session_id is None:
            raise HmpError(ErrorCode.NOT_FOUND)
        return session_id

    def session_snapshot(
        self, user_id: str, profile: str, session_ref: str, limit: int
    ) -> SessionSnapshot:
        """SES-2 snapshot-equivalent branch (no `after`, or `after=0`)."""
        self._gate(user_id, profile)
        session_id = self._resolve_ref(user_id, profile, session_ref)
        try:
            ref = self._resolve_other(user_id, profile, session_id)
            lineage = self._bridge.lineage(ref)
            rows = self._bridge.latest(ref, limit)
        except HmpError:
            raise
        except Exception as exc:
            raise _internal_error(exc) from exc
        self._save_other_baseline(user_id, profile, session_id, lineage)
        return SessionSnapshot(
            session_ref=session_ref,
            messages=tuple(_wire(r) for r in rows),
            head_message_id=rows[-1].id if rows else None,
            truncated=len(rows) >= limit,
        )

    def session_history(
        self, user_id: str, profile: str, session_ref: str, after: int, limit: int
    ) -> HistoryPage | HistoryReset:
        """SES-2 paged branch (`after=<id>`): exactly RO-6's shape and reset algorithm (§2 SES-2),
        generalized from the one `session_baselines` row to `other_session_baselines`, keyed by
        `session_id` as well."""
        self._gate(user_id, profile)
        session_id = self._resolve_ref(user_id, profile, session_ref)
        try:
            return self._session_history(user_id, profile, session_id, after, limit)
        except HmpError:
            raise
        except Exception as exc:
            raise _internal_error(exc) from exc

    def _session_history(
        self, user_id: str, profile: str, session_id: str, after: int, limit: int
    ) -> HistoryPage | HistoryReset:
        baseline = self._other_baseline(user_id, profile, session_id)
        ref = self._resolve_other(user_id, profile, session_id)
        lineage = self._bridge.lineage(ref)
        reason = self._lineage_reset(ref, baseline, lineage) if baseline is not None else None
        rows: list[Row] = []
        if reason is None:
            page = self._bridge.after(ref, after, limit)
            if isinstance(page, ResetReason):
                reason = (
                    page if page in HISTORY_RESET_REASONS else ResetReason.CURSOR_NOT_RESOLVABLE
                )
            else:
                rows = page
        self._save_other_baseline(user_id, profile, session_id, lineage)
        if reason is not None:
            return HistoryReset(reason=reason)
        head = lineage.head_row_id
        if rows:
            head = max(head or 0, rows[-1].id)
        return HistoryPage(messages=tuple(_wire(r) for r in rows), head_message_id=head)
