"""HMP v1 contract data for the server plugin (`docs/architecture/contracts/HMP_V1.md`, rev 1.0).

Pure data: constants (§13), the v1 wire identifiers (V-1), the error table (ERR-2 plus ERR-2a and
ERR-3), reset reasons, `AuthzState`, guarantee flags, and dataclasses for the F1 wire bodies.

This module imports nothing from Hermes and nothing from its siblings, so every other module (and
`compat.py` before the build gate) can import it safely. Values change only by contract revision
(V-3). `tests/unit/test_contract_tables.py` checks them against the contract text.

The `ReadBridge` Protocol and its value types also live here, not in `bridge.py`. Consumers such
as `reads.py` and `authorize.py` can then type against the bridge without importing `bridge.py`,
which must never be imported on an unsupported build (server-modules.md "Startup order").
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

# --------------------------------------------------------------------------------------------------
# V-1 / V-3: wire identifiers and versions
# --------------------------------------------------------------------------------------------------

CONTRACT_REVISION = "1.0"  # V-3; `/ready` `contract`
PROTOCOL_VERSION = 1  # V-1: QR `v`, request `v`
SUPPORTED_VERSIONS: tuple[int, ...] = (1,)  # `/ready` `versions`

PATH_PREFIX = "/hmp/v1"  # V-1 HTTP path prefix
QR_PREFIX = "hmp1:"  # V-1 QR payload prefix

# V-1 signature transcript tags (TR-13). Raw ASCII bytes, prepended to the transcript.
TAG_PAIR_REQ = b"HMP1-PAIR-REQ"
TAG_PAIR_RESP = b"HMP1-PAIR-RESP"
TAG_PAIR_DONE = b"HMP1-PAIR-DONE"
TAG_TOKEN = b"HMP1-TOKEN"
TAG_SELF_REVOKE = b"HMP1-SELF-REVOKE"
TRANSCRIPT_TAGS: tuple[bytes, ...] = (
    TAG_PAIR_REQ,
    TAG_PAIR_RESP,
    TAG_PAIR_DONE,
    TAG_TOKEN,
    TAG_SELF_REVOKE,
)

# V-1 hash domain tags (TR-12 `secret_hash(tag, x)`).
TAG_OFFER = b"HMP1-OFFER"
TAG_HOST = b"HMP1-HOST"
HASH_DOMAIN_TAGS: tuple[bytes, ...] = (TAG_OFFER, TAG_HOST)

# Server-internal derivation tag for the durable P5 retry grace (research R16, CS-13):
# successor = HMAC-SHA256(k_grace, transcript(TAG_GRACE, refresh_raw, family_id, purpose)).
# Not a V-1 wire identifier: it never appears on the wire or in a device-signed transcript, so it
# is deliberately kept out of TRANSCRIPT_TAGS and HASH_DOMAIN_TAGS.
TAG_GRACE = b"HMP1-GRACE"

# PN-KEY: push-only domains, never added to the V-1 wire/tag tables above.
# ROUTE/COLLAPSE are HMAC-only; RELAY is signature-only (future relay client).
TAG_PUSH_ROUTE = b"HMP1-PUSH-ROUTE"
TAG_PUSH_COLLAPSE = b"HMP1-PUSH-COLLAPSE"
TAG_PUSH_RELAY = b"HMP1-PUSH-RELAY"


# §2: the single conversation id in v1.
CONVERSATION_ID = "default"

# Hermes platform and CLI names. The platform name is the one in PR6-1's operator instruction
# (`hermes -p <p> pairing approve hmp <request_id>`); the CLI is `hermes hmp …` (server-modules.md).
PLATFORM_NAME = "hmp"
CLI_COMMAND = "hmp"

# --------------------------------------------------------------------------------------------------
# §13 constants (tunable only by contract revision)
# --------------------------------------------------------------------------------------------------

OFFER_TTL_S = 300  # server-fixed; <= 600
PAIRING_CONFIRM_WINDOW_S = 600  # also the P4 re-issue window
ACCESS_TTL_S = 600  # the bearer exposure window (E-GAP-27)
REFRESH_IDLE_TTL_S = 2_592_000  # 30 d
REFRESH_ABSOLUTE_TTL_S = 7_776_000  # 90 d
REFRESH_RETRY_GRACE_S = 30
CLOCK_SKEW_S = 120
WATCHDOG_INTERVAL_S = 2  # streams close within 2x this (PR7-5)
HEARTBEAT_S = 15
TAIL_RING = 512  # events per conversation
ADMISSION_WAIT_S = 5
ADMISSION_DEADLINE_S = 30
LOOKUP_SETTLE_MARGIN_S = 30
IDEMPOTENCY_RETENTION_S = 86_400  # 24 h after the last change; purge runs hourly
CLIENT_RETRY_WINDOW_S = 300
CLIENT_MAX_AUTO_ATTEMPTS = 0  # in revision 1.0 (CL-4)
MAX_BODY_BYTES = 8_192
MAX_HEADER_BYTES = 8_192
MAX_JSON_DEPTH = 8
MAX_STREAMS_PER_DEVICE = 4
RATE_PAIR_REQUEST_PER_MIN_PER_IP = 10
RATE_PAIR_REQUEST_PER_MIN_PER_OFFER = 10
RATE_PAIR_COMPLETE_PER_MIN_PER_IP = 60
RATE_PAIR_COMPLETE_PER_MIN_PER_PAIRING_ID = 60
RATE_TOKEN_PER_MIN_PER_IP = 20
RATE_TOKEN_PER_MIN_PER_DEVICE_ID = 20
# F3: polling cannot consume the answer/send budget (003-approvals/DESIGN.md).
RATE_PROMPT_READ_PER_MIN_PER_DEVICE = 60
RATE_PROMPT_ACTION_PER_MIN_PER_DEVICE = 60
LIMITER_TABLE_MAX = 4_096  # LRU bound
OFFER_MAX_FAILURES = 5
SAS_MAX_MISMATCHES = 3
DEVICE_NAME_MAX_BYTES = 64
SNAPSHOT_LIMIT_DEFAULT = 50
SNAPSHOT_LIMIT_MAX = 500
HISTORY_LIMIT_DEFAULT = 100
HISTORY_LIMIT_MAX = 1_000

# Amendment A1 (session browsing, SES-1f). Not an HMP_V1.md §13 constant: A1 is additive (v1.1)
# and these are route-local caps, not contract-wide ones. SES-2 reuses HISTORY_LIMIT_DEFAULT/MAX
# above (its route is a reparameterization of RO-6).
SESSION_LIST_LIMIT_DEFAULT = 30
SESSION_LIST_LIMIT_MAX = 100

# A1 SES-3: a dedicated per-device limiter for the heavier session-list read (no natural
# "only what changed" bound the way `after=<id>` gives history, §3 "Rate limits" recommendation).
RATE_SESSIONS_LIST_PER_MIN_PER_DEVICE_ID = 20

# A1 SES-1e: the opaque offset-cursor's encoded form is bounded well above any real value.
SESSIONS_CURSOR_MAX_BYTES = 128

# A1 SES-1b: title/source neutralization byte budgets (host/Hermes-controlled text; §2 SES-1b).
SESSION_TITLE_MAX_BYTES = 200
SESSION_SOURCE_MAX_BYTES = 64

# SR-5: at least Hermes's own per-user pairing rate-limit window (`gateway/pairing.py`
# `RATE_LIMIT_SECONDS`), so a second `authorize()` call inside it never re-triggers a P6 request
# Hermes would already be rate-limiting on its own side.
AUTHORIZE_TRIGGER_COOLDOWN_S = 600

# SR-4: per-device TR-6-style limits on the bearer read/authorize routes (server.py). The
# authorize route also has its own, HMP-specific per-(user, profile) cooldown (SR-5) above this.
RATE_READ_PER_MIN_PER_DEVICE_ID = 120
RATE_AUTHORIZE_PER_MIN_PER_DEVICE_ID = 10

# --------------------------------------------------------------------------------------------------
# §4 errors: ERR-1, ERR-2, ERR-2a, ERR-3
# --------------------------------------------------------------------------------------------------


class ErrorCode(StrEnum):
    """ERR-2 error codes."""

    BAD_REQUEST = "bad_request"
    UNAUTHENTICATED = "unauthenticated"
    REVOKED = "revoked"
    WRONG_INSTANCE = "wrong_instance"
    PAIR_FAILED = "pair_failed"
    PAIR_DENIED = "pair_denied"
    FORBIDDEN = "forbidden"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    OFFER_USED = "offer_used"
    REFUSED_ALLOW_ALL = "refused_allow_all"
    NOT_ROUTED = "not_routed"
    BUSY = "busy"
    CONVERSATION_CHANGED = "conversation_changed"
    EXPIRED = "expired"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    STALE = "stale"
    INVALID_CHOICE = "invalid_choice"
    OFFER_EXPIRED = "offer_expired"
    TOO_LARGE = "too_large"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"
    DRAINING = "draining"
    LEASE_TIMEOUT = "lease_timeout"
    GUARANTEES_UNAVAILABLE = "guarantees_unavailable"
    RETRY_STATE_LOST = "retry_state_lost"
    OTHER = "other"
    # v1.2, amendment F2 (HMP_V1.md §7a, DS-7): direct send to the canonical Bot Chat.
    NO_BOT_CHAT = "no_bot_chat"
    SESSION_BUSY = "session_busy"
    STALE_HEAD = "stale_head"
    WRITE_GATE_CLOSED = "write_gate_closed"
    API_SERVER_UNAVAILABLE = "api_server_unavailable"
    CRON_UNAVAILABLE = "cron_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"


class SubmitDefinitive(StrEnum):
    """ERR-2 column "Definitive for submit?"."""

    YES = "yes"
    NO = "no"
    NOT_APPLICABLE = "n/a"  # "—" in the table
    ONLY_IF_FLAGGED = "only_if_definitive_true"  # `other`: only when `definitive:true`


@dataclass(frozen=True)
class ErrorSpec:
    """One ERR-2 row: the code, its HTTP status(es), and whether it is definitive for a submit."""

    code: ErrorCode
    http: frozenset[int]
    definitive: SubmitDefinitive


def _spec(code: ErrorCode, http: tuple[int, ...], definitive: SubmitDefinitive) -> ErrorSpec:
    return ErrorSpec(code=code, http=frozenset(http), definitive=definitive)


_Y, _N, _NA, _FLAG = (
    SubmitDefinitive.YES,
    SubmitDefinitive.NO,
    SubmitDefinitive.NOT_APPLICABLE,
    SubmitDefinitive.ONLY_IF_FLAGGED,
)

# ERR-2, in table order.
ERROR_TABLE: Mapping[ErrorCode, ErrorSpec] = {
    s.code: s
    for s in (
        _spec(ErrorCode.BAD_REQUEST, (400,), _Y),
        _spec(ErrorCode.UNAUTHENTICATED, (401,), _Y),
        _spec(ErrorCode.REVOKED, (401,), _Y),
        _spec(ErrorCode.WRONG_INSTANCE, (401,), _Y),
        _spec(ErrorCode.PAIR_FAILED, (401,), _NA),
        _spec(ErrorCode.PAIR_DENIED, (403,), _NA),
        _spec(ErrorCode.FORBIDDEN, (403,), _Y),
        _spec(ErrorCode.UNAUTHORIZED, (403,), _Y),
        _spec(ErrorCode.NOT_FOUND, (404,), _NA),
        _spec(ErrorCode.OFFER_USED, (409,), _NA),
        _spec(ErrorCode.REFUSED_ALLOW_ALL, (409,), _NA),
        _spec(ErrorCode.NOT_ROUTED, (409,), _Y),
        _spec(ErrorCode.BUSY, (409,), _Y),
        _spec(ErrorCode.CONVERSATION_CHANGED, (409,), _Y),
        _spec(ErrorCode.EXPIRED, (409,), _Y),
        _spec(ErrorCode.IDEMPOTENCY_CONFLICT, (409,), _N),
        _spec(ErrorCode.STALE, (409,), _NA),
        _spec(ErrorCode.INVALID_CHOICE, (409,), _NA),
        _spec(ErrorCode.OFFER_EXPIRED, (410,), _NA),
        _spec(ErrorCode.TOO_LARGE, (413,), _Y),
        _spec(ErrorCode.RATE_LIMITED, (429,), _Y),
        _spec(ErrorCode.UNSUPPORTED, (501,), _NA),
        _spec(ErrorCode.DRAINING, (503,), _Y),
        _spec(ErrorCode.LEASE_TIMEOUT, (503,), _Y),
        _spec(ErrorCode.GUARANTEES_UNAVAILABLE, (503,), _Y),
        _spec(ErrorCode.RETRY_STATE_LOST, (503,), _NA),
        _spec(ErrorCode.OTHER, (503, 500), _FLAG),
        # v1.2, amendment F2 (HMP_V1.md §7a DS-7). Direct-send-only codes.
        _spec(ErrorCode.NO_BOT_CHAT, (409,), _Y),
        _spec(ErrorCode.SESSION_BUSY, (409,), _N),
        _spec(ErrorCode.STALE_HEAD, (409,), _Y),
        _spec(ErrorCode.WRITE_GATE_CLOSED, (503,), _Y),
        _spec(ErrorCode.API_SERVER_UNAVAILABLE, (503,), _N),
        _spec(ErrorCode.CRON_UNAVAILABLE, (503,), _NA),
        _spec(ErrorCode.MODEL_UNAVAILABLE, (503,), _NA),
    )
}

# ERR-1: the only extras allowed inside `error`; `guarantees` is the one allowed top-level
# sibling, and only on `503 guarantees_unavailable` (GU-5).
ERROR_EXTRAS_ALLOWED: frozenset[str] = frozenset({"why", "authz", "head_message_id", "definitive"})
ERROR_TOP_LEVEL_SIBLING = "guarantees"

# ERR-1: `message` is a fixed text per code and never echoes caller input.
ERROR_MESSAGES: Mapping[ErrorCode, str] = {
    ErrorCode.BAD_REQUEST: "malformed request",
    ErrorCode.UNAUTHENTICATED: "authentication failed",
    ErrorCode.REVOKED: "device credentials are revoked",
    ErrorCode.WRONG_INSTANCE: "request is for another instance",
    ErrorCode.PAIR_FAILED: "pairing failed",
    ErrorCode.PAIR_DENIED: "pairing refused",
    ErrorCode.FORBIDDEN: "forbidden",
    ErrorCode.UNAUTHORIZED: "not authorized for this bot",
    ErrorCode.NOT_FOUND: "not found",
    ErrorCode.OFFER_USED: "pairing offer already used",
    ErrorCode.REFUSED_ALLOW_ALL: "bot is configured for all users",
    ErrorCode.NOT_ROUTED: "bot is not served by this instance",
    ErrorCode.BUSY: "bot is busy",
    ErrorCode.CONVERSATION_CHANGED: "conversation changed",
    ErrorCode.EXPIRED: "admission deadline passed",
    ErrorCode.IDEMPOTENCY_CONFLICT: "message id reused with a different payload",
    ErrorCode.STALE: "request is no longer answerable",
    ErrorCode.INVALID_CHOICE: "choice not offered",
    ErrorCode.OFFER_EXPIRED: "pairing offer expired",
    ErrorCode.TOO_LARGE: "request too large",
    ErrorCode.RATE_LIMITED: "rate limited",
    ErrorCode.UNSUPPORTED: "not supported by this instance",
    ErrorCode.DRAINING: "instance is restarting",
    ErrorCode.LEASE_TIMEOUT: "turn lease not acquired",
    ErrorCode.GUARANTEES_UNAVAILABLE: "delivery guarantees unavailable",
    ErrorCode.RETRY_STATE_LOST: "refresh retry state lost",
    ErrorCode.OTHER: "request refused",
    # v1.2, amendment F2 (HMP_V1.md §7a DS-7).
    ErrorCode.NO_BOT_CHAT: "bot chat does not exist yet",
    ErrorCode.SESSION_BUSY: "bot chat is in use elsewhere",
    ErrorCode.STALE_HEAD: "conversation view is out of date",
    ErrorCode.WRITE_GATE_CLOSED: "direct send is not available on this instance",
    ErrorCode.API_SERVER_UNAVAILABLE: "direct send delivery is unavailable",
    ErrorCode.CRON_UNAVAILABLE: "scheduled jobs are unavailable",
    ErrorCode.MODEL_UNAVAILABLE: "model management is unavailable",
}


class HmpError(Exception):
    """An HMP error response (ERR-1, ERR-2). Raised by route code; `server.py` shapes it.

    `extras` may only use the ERR-1 names (`why`, `authz`, `head_message_id`, `definitive`);
    `guarantees` is the one top-level sibling, and only on `503 guarantees_unavailable` (GU-5).
    The HTTP status must be one the ERR-2 row allows; it defaults to the row's only status.
    The exception text is the code alone, so logging it can never carry a value (SEC-4).
    """

    def __init__(
        self,
        code: ErrorCode,
        http: int | None = None,
        *,
        guarantees: Mapping[str, bool] | None = None,
        **extras: object,
    ) -> None:
        spec = ERROR_TABLE[code]
        if http is None:
            if len(spec.http) != 1:
                raise ValueError("this error code needs an explicit HTTP status")
            (http,) = spec.http
        if http not in spec.http:
            raise ValueError("HTTP status not allowed for this error code")
        unknown = set(extras) - ERROR_EXTRAS_ALLOWED
        if unknown:
            raise ValueError("error extras outside ERR-1")
        if guarantees is not None and code is not ErrorCode.GUARANTEES_UNAVAILABLE:
            raise ValueError("guarantees ride only on 503 guarantees_unavailable (GU-5)")
        super().__init__(code.value)
        self.code = code
        self.http = http
        self.extras: dict[str, object] = dict(extras)
        self.guarantees = dict(guarantees) if guarantees is not None else None

    def body(self) -> dict[str, object]:
        """The ERR-1 body: `{"error": {"code", "message", ...extras}}` (+ `guarantees`)."""
        error: dict[str, object] = {"code": self.code.value, "message": ERROR_MESSAGES[self.code]}
        error.update(self.extras)
        out: dict[str, object] = {"error": error}
        if self.guarantees is not None:
            out[ERROR_TOP_LEVEL_SIBLING] = self.guarantees
        return out


class OtherWhy(StrEnum):
    """`why` values named by the contract (TR-4, TR-6, ERR-2, ERR-2a, ERR-3, RO-8)."""

    PEER_NOT_ALLOWED = "peer_not_allowed"  # TR-4, with 403 forbidden
    MAX_STREAMS_PER_DEVICE = "max_streams_per_device"  # TR-6, with 429 rate_limited
    UNVERIFIABLE = "unverifiable"  # ERR-3 / PR6-1, with 503 other
    INTERNAL_ERROR = "internal_error"  # ERR-2, with 500 other
    HISTORY_REWRITTEN = "history_rewritten"  # RO-8, optional on 409 conversation_changed
    HERMES_BUILD_UNSUPPORTED = "hermes_build_unsupported"  # ERR-2a
    HERMES_READ_DEPENDENCY_MISSING = "hermes_read_dependency_missing"  # ERR-2a


@dataclass(frozen=True)
class ReadCompatRefusal:
    """ERR-2a: a read-compatibility refusal, sent on every route except `/ready`."""

    http: int
    code: ErrorCode
    why: OtherWhy
    definitive: SubmitDefinitive


# ERR-2a (GU-2c). Definitive for submit: yes (nothing handed off).
READ_COMPAT_REFUSALS: Mapping[OtherWhy, ReadCompatRefusal] = {
    OtherWhy.HERMES_BUILD_UNSUPPORTED: ReadCompatRefusal(
        503, ErrorCode.OTHER, OtherWhy.HERMES_BUILD_UNSUPPORTED, SubmitDefinitive.YES
    ),
    OtherWhy.HERMES_READ_DEPENDENCY_MISSING: ReadCompatRefusal(
        503, ErrorCode.OTHER, OtherWhy.HERMES_READ_DEPENDENCY_MISSING, SubmitDefinitive.YES
    ),
}
# ERR-2a: the only route an unsupported build still serves normally.
READ_COMPAT_EXEMPT_PATH = PATH_PREFIX + "/ready"

# ERR-4: the submit exit tags that make a `503 other` definitive. Kept for completeness; F1
# registers no submit route (FR-053).
DEFINITIVE_OTHER_TAGS: frozenset[str] = frozenset(
    {
        "bot_loop",
        "no_runner",
        "estop",
        "capacity",
        "no_durable_lease",
        "no_handler",
        "unresolved",
        "key_mismatch",
        "route_drop",
        "pre_dispatch_drop",
    }
)


class AuthzState(StrEnum):
    """Per-bot authorization state (RO-1, ERR-3, PR6-1)."""

    AUTHORIZED = "authorized"
    PENDING_OPERATOR = "pending_operator"
    REFUSED_ALLOW_ALL = "refused_allow_all"
    NOT_ROUTED = "not_routed"
    NOT_SERVED = "not_served"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class GateRefusal:
    http: int
    code: ErrorCode
    why: OtherWhy | None = None


# ERR-3: the per-bot gate response for each non-authorized state (always with `authz`).
PER_BOT_GATE_REFUSALS: Mapping[AuthzState, GateRefusal] = {
    AuthzState.PENDING_OPERATOR: GateRefusal(403, ErrorCode.FORBIDDEN),
    AuthzState.REFUSED_ALLOW_ALL: GateRefusal(403, ErrorCode.FORBIDDEN),
    AuthzState.NOT_ROUTED: GateRefusal(409, ErrorCode.NOT_ROUTED),
    AuthzState.NOT_SERVED: GateRefusal(409, ErrorCode.NOT_ROUTED),
    AuthzState.UNVERIFIABLE: GateRefusal(503, ErrorCode.OTHER, OtherWhy.UNVERIFIABLE),
}

# --------------------------------------------------------------------------------------------------
# Reset reasons (RO-6, EV-2)
# --------------------------------------------------------------------------------------------------


class ResetReason(StrEnum):
    CURSOR_NOT_RESOLVABLE = "cursor_not_resolvable"
    LINEAGE_CHANGED = "lineage_changed"
    SESSION_REPLACED = "session_replaced"
    HISTORY_REWRITTEN = "history_rewritten"
    EPOCH_CHANGED = "epoch_changed"
    GAP = "gap"
    RING_OVERFLOW = "ring_overflow"


# RO-6: the reasons a history read may return.
HISTORY_RESET_REASONS: frozenset[ResetReason] = frozenset(
    {
        ResetReason.CURSOR_NOT_RESOLVABLE,
        ResetReason.LINEAGE_CHANGED,
        ResetReason.SESSION_REPLACED,
        ResetReason.HISTORY_REWRITTEN,
    }
)
# EV-2: the reasons the SSE tail may send (not served in F1).
TAIL_RESET_REASONS: frozenset[ResetReason] = frozenset(
    {
        ResetReason.EPOCH_CHANGED,
        ResetReason.GAP,
        ResetReason.RING_OVERFLOW,
        ResetReason.LINEAGE_CHANGED,
        ResetReason.HISTORY_REWRITTEN,
        ResetReason.SESSION_REPLACED,
    }
)

# --------------------------------------------------------------------------------------------------
# §8 guarantees and write gate (GU-1, GU-2, GU-4)
# --------------------------------------------------------------------------------------------------

GUARANTEE_FLAGS: tuple[str, ...] = (
    "no_defer",
    "atomic_anchor",
    "approval_request_id",
    "confirmed_settle",
)

# GU-2: flag -> (key in Hermes's PLATFORM_ADAPTER_CAPABILITIES, floor version).
CAPABILITY_FLOORS: Mapping[str, tuple[str, int]] = {
    "approval_request_id": ("exec_approval_request_id", 1),
    "no_defer": ("defer_policy_reject", 1),
    "atomic_anchor": ("admission_precondition", 2),
    "confirmed_settle": ("turn_settled", 1),
}

# GU-4: the gate is open iff both of these flags are true.
WRITE_GATE_REQUIRED_FLAGS: tuple[str, ...] = ("no_defer", "atomic_anchor")


class WriteGateState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    # v1.2, amendment F2 (HMP_V1.md §7a GU-4a): scoped exclusively to `POST .../chat/messages`.
    # Never returned together with OPEN for the same request (mutually exclusive by construction).
    OPEN_GUARDED = "open_guarded"


WRITE_GATE_CLOSED_REASON = "guarantees_unavailable"

# v1.2, amendment F2 (DS-2(b)): the closed reason reported specifically for the direct-send route
# (`chat/messages`) when the guarded gate cannot open -- distinct from the original submit route's
# WRITE_GATE_CLOSED_REASON, per HMP_V1.md's ERR-2 addition (`write_gate_closed`, a new code, never
# reusing `guarantees_unavailable` for this route's own closed state).
DIRECT_SEND_GATE_CLOSED_REASON = "write_gate_closed"

# --------------------------------------------------------------------------------------------------
# Wire bodies for the F1 routes (server-modules.md "F1 route table"). Field names are the wire
# names. Base64url fields are carried as their wire text; validation lives in `wire.py`.
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Guarantees:
    no_defer: bool = False
    atomic_anchor: bool = False
    approval_request_id: bool = False
    confirmed_settle: bool = False


@dataclass(frozen=True)
class WriteGate:
    state: WriteGateState
    reason: str | None  # None, guarantee floor, or Bot Chat route closed


@dataclass(frozen=True)
class ReadyResponse:
    """PR0-1: `GET /hmp/v1/ready`, 200."""

    versions: tuple[int, ...]
    contract: str
    iid: str
    guarantees: Guarantees
    write_gate: WriteGate


@dataclass(frozen=True)
class QrOffer:
    """PR1-3: the JSON inside the `hmp1:` payload."""

    v: int
    iid: str
    ep: tuple[str, ...]
    oid: str
    s: str
    exp: int


@dataclass(frozen=True)
class PairRequest:
    """PR2-1: `POST /hmp/v1/pair/request` body."""

    v: int
    oid: str
    s: str
    device_name: str
    device_pub: str
    nd: str
    sig: str


@dataclass(frozen=True)
class PairRequestAccepted:
    """PR2-4: 202 response."""

    pairing_id: str
    state: str  # "awaiting_operator"
    ni: str
    device_sas: str
    confirm_by: int
    isig: str


@dataclass(frozen=True)
class PairComplete:
    """PR4-1: `POST /hmp/v1/pair/complete` body."""

    pairing_id: str
    ts: int
    sig: str


@dataclass(frozen=True)
class PairCompleteIssued:
    """PR4-2: 200 response on first issue or lost-response re-issue."""

    device_id: str
    user_ref: str
    refresh_token: str
    access_token: str
    access_expires_at: int


@dataclass(frozen=True)
class TokenRequest:
    """PR5-1: `POST /hmp/v1/auth/token` body."""

    device_id: str
    refresh_token: str
    ts: int
    nonce: str
    sig: str


@dataclass(frozen=True)
class TokenResponse:
    """PR5-2: 200 response."""

    access_token: str
    access_expires_at: int
    refresh_token: str


@dataclass(frozen=True)
class SelfRevokeRequest:
    """PR7-3: `POST /hmp/v1/devices/self/revoke` body."""

    ts: int
    sig: str


@dataclass(frozen=True)
class AuthorizePending:
    """PR6-1: 202 response when the bot awaits the operator."""

    authz: AuthzState  # PENDING_OPERATOR
    user_id: str
    instruction: str
    note: str | None = None  # PR6-3


@dataclass(frozen=True)
class RosterBot:
    profile: str
    display_name: str
    authz: AuthzState
    # Additive RO-1 field. Absent for a bot this device cannot open, and on older HMP builds.
    send_gate: WriteGate | None = field(default=None, metadata={"omit_if_none": True})


@dataclass(frozen=True)
class RosterResponse:
    """RO-1: `GET /hmp/v1/bots`, 200."""

    instance: str
    served_at: int
    guarantees: Guarantees
    write_gate: WriteGate
    bots: tuple[RosterBot, ...]


# Additive tool-output caps (V-3). Unicode code points, not bytes. The bridge applies them
# while reading Hermes rows, so a `Row`'s `text` / `arguments` never carry the uncapped value.
TOOL_ARGUMENTS_CAP = 500
TOOL_OUTPUT_CAP = 4000


@dataclass(frozen=True)
class WireToolCall:
    """One assistant tool call on the wire (additive, V-3).

    `arguments` is the call's arguments rendered as compact JSON, at most
    `TOOL_ARGUMENTS_CAP` characters. `arguments_truncated` is true when that cut happened.
    """

    id: str
    name: str
    arguments: str
    arguments_truncated: bool


@dataclass(frozen=True)
class WireMessage:
    """RO-3 `messages[]` item.

    Tool fields are optional (V-3) and omitted from the JSON when absent, so a message with no
    tool data keeps the previous shape. `truncated` is present only when a tool row's `text` was
    cut to `TOOL_OUTPUT_CAP`.
    """

    id: int
    role: str
    text: str
    client_message_id: str | None
    created_at: float  # Hermes-sourced, informational (ID-1)
    tool_calls: tuple[WireToolCall, ...] | None = field(
        default=None, metadata={"omit_if_none": True}
    )
    tool_name: str | None = field(default=None, metadata={"omit_if_none": True})
    tool_call_id: str | None = field(default=None, metadata={"omit_if_none": True})
    truncated: bool | None = field(default=None, metadata={"omit_if_none": True})


class TurnObservedState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOP_REQUESTED = "stop_requested"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TurnObservation:
    observed_state: TurnObservedState
    since: int | None


@dataclass(frozen=True)
class PartialObservation:
    live_id: str
    text: str


@dataclass(frozen=True)
class TailPosition:
    epoch: str
    seq: int


@dataclass(frozen=True)
class SnapshotResponse:
    """RO-3: `GET …/conversations/default`, 200."""

    conversation_id: str
    session_id: str | None
    head_message_id: int | None
    messages: tuple[WireMessage, ...]
    turn: TurnObservation
    partial: PartialObservation | None
    partial_lost: bool
    open_requests: tuple[Mapping[str, object], ...]
    tail: TailPosition


@dataclass(frozen=True)
class HistoryPage:
    """RO-6: `GET …/messages?after=`, 200 with rows."""

    messages: tuple[WireMessage, ...]
    head_message_id: int | None


@dataclass(frozen=True)
class HistoryReset:
    """RO-6: `GET …/messages?after=`, 200 with a reset."""

    reason: ResetReason
    snapshot_required: bool = True


# --------------------------------------------------------------------------------------------------
# Amendment A1 (session browsing, OD-F9/OD-F10): SES-1 (session list) and SES-2 (session messages).
# Additive under v1.1 (V-3); a client on an earlier 1.x build ignores these routes entirely (V-4).
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionListItem:
    """SES-1 `sessions[]` item. `session_ref` is opaque (SES-1a); the raw Hermes `session_id`,
    `session_key`, `cwd`/`git_repo_root`/`git_branch`, billing/model/system-prompt fields and
    `handoff_*`/`profile_name`/`transport_profile` are never carried (SES-1c)."""

    session_ref: str
    title: str | None
    source: str
    started_at: int
    last_active_at: int | None
    message_count: int
    is_mobile: bool


@dataclass(frozen=True)
class SessionListResponse:
    """SES-1: `GET …/bots/{p}/sessions?cursor=&limit=`, 200."""

    sessions: tuple[SessionListItem, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class SessionSnapshot:
    """SES-2 snapshot-equivalent branch (no `after`, or `after=0`), 200."""

    session_ref: str
    messages: tuple[WireMessage, ...]
    head_message_id: int | None
    truncated: bool


# --------------------------------------------------------------------------------------------------
# Read bridge interface (server-modules.md "Key protocols"). Implemented only in `bridge.py`.
# The value types below carry only what the Protocol signatures need. Their fields are provisional
# (T028 implements them; T016 reviews them).
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationRef:
    """A resolved (user, profile) conversation. The bridge never mints one (FR-036, R11)."""

    user_id: str
    profile: str
    session_id: str


@dataclass(frozen=True)
class Row:
    """One Hermes message row as the bridge returns it.

    `tool_calls` is set on assistant rows. `tool_name`, `tool_call_id` and `truncated` are set
    on tool rows. `text` on a tool row is already capped at `TOOL_OUTPUT_CAP`.
    """

    id: int
    role: str
    text: str
    client_message_id: str | None
    created_at: float
    tool_calls: tuple[WireToolCall, ...] = ()
    tool_name: str | None = None
    tool_call_id: str | None = None
    truncated: bool = False


@dataclass(frozen=True)
class LineageInfo:
    """Inputs for session baselines and reset detection (RO-6, RO-8; `session_baselines`)."""

    session_id: str
    lineage_tip: str
    head_row_id: int | None
    active_row_count: int
    # The compression chain walked forward from `session_id` (root first, tip last). `reads.py`
    # uses a baseline session's chain to tell `lineage_changed` from `session_replaced` (RO-6).
    chain: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionSummary:
    """Amendment A1: one row as `SessionDB.list_sessions_rich` returns it, already narrowed to
    what SES-1 needs (§1.1/§1.2 of the amendment). `session_id` is the Hermes-internal id (or a
    compression lineage's tip, already projected by Hermes itself, per `list_sessions_rich`'s own
    `project_compression_tips` default) -- it is bridge-internal, never put on the wire raw
    (SES-1a): the caller mints an opaque `session_ref` for it (`store.py`)."""

    session_id: str
    title: str | None
    source: str
    started_at: float
    last_active_at: float | None
    message_count: int
    # OD-F11: Hermes's own `sessions.hidden` flag. The canonical "Bot Chat" a bot's Desktop view
    # opens is always created hidden (`hermes-agent`'s `canonical-chat.ts` `createCanonicalChat`,
    # `hidden: true`), so `list_sessions_rich` must be called with `include_hidden=True` to see it
    # at all; `reads.py`'s OD-F11 selector then narrows back down to just that row (plus the
    # phone's own), never disclosing an arbitrary hidden session.
    hidden: bool = False


@dataclass(frozen=True)
class AuthorizeResult:
    """Outcome of the inert P6 authorization trigger (PR6-1, GU-4 exception)."""

    authz: AuthzState
    request_id: str | None = None
    extras: Mapping[str, object] = field(default_factory=dict)


class ReadBridge(Protocol):
    """HMP's only door into Hermes internals (§12, PR-2). Implemented only in `bridge.py`."""

    def served_profiles(self) -> list[str]: ...

    def authz_state(self, user_id: str, profile: str) -> AuthzState:
        """Fails closed to `AuthzState.UNVERIFIABLE`."""
        ...

    def instance_wide_grant(self, profile: str) -> bool:
        """PR6-3 note."""
        ...

    def request_authorization(
        self, user_id: str, profile: str, *, loop: Any = None
    ) -> AuthorizeResult:
        """The inert P6 trigger (GU-4 exception). Hands no user text to Hermes. `loop` (SR-4):
        the real event loop, when this call itself may run off it (`asyncio.to_thread`)."""
        ...

    def conversation_ref(self, user_id: str, profile: str) -> ConversationRef | None:
        """Never mints a conversation or a session."""
        ...

    def head(self, ref: ConversationRef) -> int | None: ...

    def latest(self, ref: ConversationRef, limit: int) -> list[Row]: ...

    def after(self, ref: ConversationRef, after_id: int, limit: int) -> list[Row] | ResetReason: ...

    def lineage(self, ref: ConversationRef) -> LineageInfo: ...

    def capability_versions(self) -> Mapping[str, int]:
        """GU-2 input for `gate.py`."""
        ...

    # ------------------------------------------------------------------------------------------
    # Amendment A1 (OD-F9/OD-F10): read-only session browsing across every source of a bot.
    # ------------------------------------------------------------------------------------------

    def list_sessions(
        self,
        user_id: str,
        profile: str,
        *,
        sources_excluded: Sequence[str],
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        """§1.1 `list_sessions_rich`, narrowed to SES-1's needs. Ordered most-recently-active
        first. Raises on a read failure (never degrades to an empty list -- reads.py's own rule,
        RO-8/RO-6 precedent)."""
        ...

    def resolve_session(
        self, user_id: str, profile: str, session_id: str
    ) -> ConversationRef | None:
        """SES-2: existence + scoping check only for an arbitrary session of this profile (never
        restricted to the id `conversation_ref()` resolves) -- no new lineage/history bridge
        method is needed; `head`/`latest`/`after`/`lineage` already take any `ConversationRef`.
        `None` when `session_id` does not exist in this profile's session database."""
        ...

    # ------------------------------------------------------------------------------------------
    # Amendment F2 (HMP_V1.md §7a, DS-2..DS-6): direct send to the canonical Bot Chat.
    # ------------------------------------------------------------------------------------------

    def resolve_bot_chat(self, profile: str) -> BotChatTarget | None:
        """DS-4(2): the same primitive SES-1's OD-F11 selector and
        `tools.bot_live_delivery.find_canonical_owner` both already use (`get_session_by_title`,
        then the live compression tip). `None` when no Bot Chat exists yet for this profile --
        never created here (DS-9)."""
        ...

    def lease_snapshot(self, profile: str) -> list[Mapping[str, object]] | None:
        """DS-4(3): `active_session_registry_snapshot`, called with the *target profile's own*
        `registry_home`. `None` signals the read itself failed -- the caller MUST fail closed
        (`session_busy`), never treat `None` as "not busy"."""
        ...

    def direct_send_endpoint(self, profile: str) -> DirectSendEndpoint | None:
        """DS-2(b)/DS-6: the resolved `api_server` bind and per-profile `API_SERVER_KEY` for this
        profile, or `None` when either cannot be positively determined (fail closed) or the
        resolved bind is not loopback. Never logs or persists the key (SEC-4)."""
        ...

    def profile_default_model(self, profile: str) -> Mapping[str, object]:
        """Read the routed profile's persisted provider/default model only."""
        ...

    def set_profile_default_model(
        self, profile: str, provider: str, model: str
    ) -> Mapping[str, object] | None:
        """Validated Hermes write; None means the provider/model pair was refused."""
        ...


@dataclass(frozen=True)
class BotChatTarget:
    """DS-4(2)/(4): the canonical Bot Chat's live compression tip -- the id every DS-4/DS-6
    operation addresses, never the registry's possibly-ended root id (routes around
    `_get_existing_session_or_404`'s "accepts an ended parent" gap, HMP_V1.md §7a DS-4(4))."""

    root_session_id: str
    live_tip_session_id: str
    head_message_id: int | None
    # DS-4(3): every id in the compression chain, root to tip -- a lease on *any* of these, not
    # only the live tip, counts as busy (the review's "CLI after /compress" finding).
    compression_chain: tuple[str, ...]


@dataclass(frozen=True)
class DirectSendEndpoint:
    """DS-6: the resolved, positively-loopback `api_server` bind and this profile's own
    `API_SERVER_KEY`. `host` is always `127.0.0.1` or `::1` by construction -- `bridge.py` never
    returns a `DirectSendEndpoint` for any other resolved value (fail closed instead, DS-2(b))."""

    host: str
    port: int
    api_key: str
    # "" for the default profile, "/p/<profile>" for a named (secondary) profile -- the generic
    # mirror `gateway/run_adapters.py` applies to every route, prepended to the loopback path
    # (HMP_V1.md §7a DS-6). Never `/v1/...` (that prefix is the OpenAI-compatible surface, a
    # different mirror rule entirely -- the review's own finding #1).
    path_prefix: str


# --------------------------------------------------------------------------------------------------
# §7a direct send (v1.2, amendment F2): idempotency records, the guard result, and the outcome
# the wire response (DS-7) is built from. Field names mirror the wire shapes in HMP_V1.md.
# --------------------------------------------------------------------------------------------------


class CmidStatus(StrEnum):
    """DS-3: the direct-send idempotency record's own lifecycle -- reserved before the loopback
    call, resolved after a definitive outcome, and never deleted on ambiguity."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    # Review round 3: a task that ended (cancel, crash, or any exception) before a definitive
    # Hermes outcome. Both the retry POST and DS-8 report this as wire state `unknown`.
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DirectSendRequest:
    """DS-1's body, already validated (`wire.py`)."""

    client_message_id: str
    expected_head: int | None
    text: str
    sent_at: int | None = None


@dataclass(frozen=True)
class GuardFailure:
    """DS-4: which guard step failed, and the error code DS-7 maps it to. `retryable` distinguishes
    `session_busy`/`api_server_unavailable` (non-definitive) from `no_bot_chat`/`stale_head`
    (definitive) -- mirrors ERR-2's "Definitive for submit?" column for this route's own codes."""

    code: ErrorCode
    retryable: bool


@dataclass(frozen=True)
class DirectSendOutcome:
    """DS-7: the result `direct_send.py` hands back to the route handler, already in wire shape."""

    state: str  # "accepted" | "queued" | "submitted" | "unknown"
    message_id: int | None = None
    head_message_id: int | None = None
    reply: Mapping[str, object] | None = None
    interleave_detected: bool = False


# Spec 028 D4: pure syntactic values only. No custody/native/lifecycle authority or I/O.
_PA_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_PA_SHA = re.compile(r"[0-9a-f]{64}")
_PA_REF = re.compile(r"[A-Za-z0-9_-]{43}")
_PA_IID = re.compile(r"[a-z2-7]{51}[aq]")


def _pa_check(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid phone attachment")


def _pa_int(value: object, low: int = 0, high: int = (1 << 53) - 1) -> None:
    _pa_check(type(value) is int and low <= value <= high)


def _pa_text(value: object, maximum: int) -> None:
    _pa_check(type(value) is str and len(value) <= maximum)
    _pa_check(not any(0xD800 <= ord(c) <= 0xDFFF for c in value))
    _pa_check(len(value.encode("utf-8")) <= maximum)


def _pa_opaque(value: object) -> None:
    # Existing routed identity strings; syntactic data, never an auth decision.
    _pa_check(type(value) is str and bool(value))
    _pa_check(not any(0xD800 <= ord(c) <= 0xDFFF for c in value))


def _pa_profile(value: object) -> None:
    _pa_text(value, 1024)
    # Match the existing Phone client's UTF-16-unit bound, not a native global maximum.
    _pa_check(bool(value) and len(value.encode("utf-16-le")) // 2 <= 256)
    _pa_check(not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _pa_uuid(value: object) -> None:
    _pa_check(type(value) is str and len(value) == 36 and _PA_UUID.fullmatch(value) is not None)


def _pa_sha(value: object) -> None:
    _pa_check(type(value) is str and len(value) == 64 and _PA_SHA.fullmatch(value) is not None)


def _pa_ref(value: object) -> None:
    _pa_check(type(value) is str and len(value) == 43 and _PA_REF.fullmatch(value) is not None)
    raw = base64.urlsafe_b64decode(value + "=")
    _pa_check(len(raw) == 32 and base64.urlsafe_b64encode(raw).decode().rstrip("=") == value)


def _pa_label(value: object) -> None:
    _pa_text(value, 128)
    _pa_check(bool(value) and value.strip("."))
    _pa_check(not any(ord(c) < 32 or 127 <= ord(c) <= 159 or c in "/\\" for c in value))


def _pa_tuple(value: object, cls: type, *, minimum: int = 1) -> None:
    _pa_check(type(value) is tuple and minimum <= len(value) <= 4)
    _pa_check(all(type(v) is cls for v in value))


class _PhoneAttachmentRedacted:
    __slots__ = ()

    def __repr__(self) -> str:
        return type(self).__name__

    def __str__(self) -> str:
        return type(self).__name__


class PhoneAttachmentMime(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"
    PLAIN_TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    CSV = "text/csv"


class PhoneAttachmentTargetState(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"


class PhoneAttachmentUnavailableReason(StrEnum):
    ADMISSION_UNAVAILABLE = "admission_unavailable"
    TARGET_UNAVAILABLE = "target_unavailable"
    VALIDATOR_UNAVAILABLE = "validator_unavailable"
    FEATURE_UNAVAILABLE = "feature_unavailable"


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentLogicalItem(_PhoneAttachmentRedacted):
    client_attachment_id: str
    sha256: str
    mime: PhoneAttachmentMime
    length: int
    label: str

    def __post_init__(self) -> None:
        _pa_uuid(self.client_attachment_id)
        _pa_sha(self.sha256)
        _pa_check(type(self.mime) is PhoneAttachmentMime)
        _pa_int(self.length, 1, 8 * 1024 * 1024)
        _pa_label(self.label)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentPayload(_PhoneAttachmentRedacted):
    target_binding: str
    text: str
    items: tuple[PhoneAttachmentLogicalItem, ...]

    def __post_init__(self) -> None:
        _pa_ref(self.target_binding)
        _pa_text(self.text, 4096)
        _pa_tuple(self.items, PhoneAttachmentLogicalItem)
        _pa_check(len({v.client_attachment_id for v in self.items}) == len(self.items))
        _pa_check(sum(v.length for v in self.items) <= 16 * 1024 * 1024)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentUploadReference(_PhoneAttachmentRedacted):
    item: PhoneAttachmentLogicalItem
    target_binding: str
    custody_reference: str
    expires_at_ms: int

    def __post_init__(self) -> None:
        _pa_check(type(self.item) is PhoneAttachmentLogicalItem)
        _pa_ref(self.target_binding)
        _pa_ref(self.custody_reference)
        _pa_int(self.expires_at_ms, 1)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentWireReference(_PhoneAttachmentRedacted):
    item: PhoneAttachmentLogicalItem
    custody_reference: str

    def __post_init__(self) -> None:
        _pa_check(type(self.item) is PhoneAttachmentLogicalItem)
        _pa_ref(self.custody_reference)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentMessageRequest(_PhoneAttachmentRedacted):
    client_message_id: str
    payload: PhoneAttachmentPayload
    references: tuple[PhoneAttachmentWireReference, ...]

    def __post_init__(self) -> None:
        _pa_uuid(self.client_message_id)
        _pa_check(type(self.payload) is PhoneAttachmentPayload)
        _pa_tuple(self.references, PhoneAttachmentWireReference)
        _pa_check(tuple(r.item for r in self.references) == self.payload.items)
        _pa_check(len(json.dumps(
            _pa_message_wire(self), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")) <= 8192)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentTargetBinding(_PhoneAttachmentRedacted):
    binding: str
    state: PhoneAttachmentTargetState
    expires_at_ms: int

    def __post_init__(self) -> None:
        _pa_ref(self.binding)
        _pa_check(type(self.state) is PhoneAttachmentTargetState)
        _pa_int(self.expires_at_ms, 1)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentLimits(_PhoneAttachmentRedacted):
    item_count: int
    item_bytes: int
    message_bytes: int
    output_edge: int
    source_pixels: int
    source_edge: int
    source_image_bytes: int
    selection_source_bytes: int
    normalized_mimes: tuple[PhoneAttachmentMime, ...]

    def __post_init__(self) -> None:
        for value, cap in (
            (self.item_count, 4), (self.item_bytes, 8 * 1024 * 1024),
            (self.message_bytes, 16 * 1024 * 1024), (self.output_edge, 2048),
            (self.source_pixels, 120_000_000), (self.source_edge, 32768),
            (self.source_image_bytes, 16 * 1024 * 1024),
            (self.selection_source_bytes, 32 * 1024 * 1024),
        ):
            _pa_int(value, 1, cap)
        _pa_check(type(self.normalized_mimes) is tuple and 1 <= len(self.normalized_mimes) <= 6)
        _pa_check(all(type(v) is PhoneAttachmentMime for v in self.normalized_mimes))
        _pa_check(len(set(self.normalized_mimes)) == len(self.normalized_mimes))


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentsUnavailable(_PhoneAttachmentRedacted):
    reason: PhoneAttachmentUnavailableReason

    def __post_init__(self) -> None:
        _pa_check(type(self.reason) is PhoneAttachmentUnavailableReason)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentsAvailable(_PhoneAttachmentRedacted):
    target: PhoneAttachmentTargetBinding
    limits: PhoneAttachmentLimits

    def __post_init__(self) -> None:
        _pa_check(type(self.target) is PhoneAttachmentTargetBinding)
        _pa_check(type(self.limits) is PhoneAttachmentLimits)


PhoneAttachmentCapability = PhoneAttachmentsUnavailable | PhoneAttachmentsAvailable


class PhoneAttachmentSendState(StrEnum):
    RESERVED = "reserved"
    SUBMITTED = "submitted"
    UNKNOWN = "unknown"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReservation(_PhoneAttachmentRedacted):
    iid: str
    user_id: str
    issuing_device_id: str
    profile: str
    client_message_id: str
    target_binding: str
    payload_sha256: str
    ordered_asset_ids: tuple[str, ...]
    caption_sha256: str
    caption_utf8_length: int
    state: PhoneAttachmentSendState
    created_at_ms: int

    def __post_init__(self) -> None:
        _pa_check(type(self.iid) is str and len(self.iid) == 52 and _PA_IID.fullmatch(self.iid))
        _pa_opaque(self.user_id)
        _pa_opaque(self.issuing_device_id)
        _pa_profile(self.profile)
        _pa_uuid(self.client_message_id)
        _pa_ref(self.target_binding)
        _pa_sha(self.payload_sha256)
        _pa_check(type(self.ordered_asset_ids) is tuple and 1 <= len(self.ordered_asset_ids) <= 4)
        for asset_id in self.ordered_asset_ids:
            _pa_uuid(asset_id)
        _pa_check(len(set(self.ordered_asset_ids)) == len(self.ordered_asset_ids))
        _pa_sha(self.caption_sha256)
        _pa_int(self.caption_utf8_length, 0, 4096)
        _pa_check(type(self.state) is PhoneAttachmentSendState)
        _pa_int(self.created_at_ms)


class PhoneAttachmentBytesState(StrEnum):
    AVAILABLE = "available"
    EXPIRED = "expired"


class PhoneAttachmentCaptionState(StrEnum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentProjectedItem(_PhoneAttachmentRedacted):
    item: PhoneAttachmentLogicalItem
    bytes_state: PhoneAttachmentBytesState
    custody_reference: str | None

    def __post_init__(self) -> None:
        _pa_check(type(self.item) is PhoneAttachmentLogicalItem)
        _pa_check(type(self.bytes_state) is PhoneAttachmentBytesState)
        if self.bytes_state is PhoneAttachmentBytesState.AVAILABLE:
            _pa_ref(self.custody_reference)
        else:
            _pa_check(self.custody_reference is None)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReceipt(_PhoneAttachmentRedacted):
    transport_payload_sha256: str
    caption_state: PhoneAttachmentCaptionState
    items: tuple[PhoneAttachmentProjectedItem, ...]

    def __post_init__(self) -> None:
        _pa_sha(self.transport_payload_sha256)
        _pa_check(type(self.caption_state) is PhoneAttachmentCaptionState)
        _pa_tuple(self.items, PhoneAttachmentProjectedItem)
        _pa_check(len({v.item.client_attachment_id for v in self.items}) == len(self.items))
        _pa_check(sum(v.item.length for v in self.items) <= 16 * 1024 * 1024)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentRowPresent(_PhoneAttachmentRedacted):
    row_id: int
    client_message_id: str
    receipt: PhoneAttachmentReceipt

    def __post_init__(self) -> None:
        _pa_int(self.row_id, 1)
        _pa_uuid(self.client_message_id)
        _pa_check(type(self.receipt) is PhoneAttachmentReceipt)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReconciliationUnknown(_PhoneAttachmentRedacted):
    pass


PhoneAttachmentReconciliation = PhoneAttachmentRowPresent | PhoneAttachmentReconciliationUnknown


class PhoneAttachmentValidationFailure(StrEnum):
    MALFORMED = "malformed"
    TOO_LARGE = "too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    METADATA_PRESENT = "metadata_present"
    MULTIPLE_FRAMES = "multiple_frames"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True, repr=False)
class OwnedPhoneAttachmentInput(_PhoneAttachmentRedacted):
    fd: int
    expected: PhoneAttachmentLogicalItem

    def __post_init__(self) -> None:
        _pa_int(self.fd, 0, (1 << 31) - 1)
        _pa_check(type(self.expected) is PhoneAttachmentLogicalItem)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentValidated(_PhoneAttachmentRedacted):
    item: PhoneAttachmentLogicalItem

    def __post_init__(self) -> None:
        _pa_check(type(self.item) is PhoneAttachmentLogicalItem)


@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentValidationRejected(_PhoneAttachmentRedacted):
    reason: PhoneAttachmentValidationFailure

    def __post_init__(self) -> None:
        _pa_check(type(self.reason) is PhoneAttachmentValidationFailure)


PhoneAttachmentValidationResult = PhoneAttachmentValidated | PhoneAttachmentValidationRejected


class PhoneAttachmentValidator(Protocol):
    async def validate(
        self, source: OwnedPhoneAttachmentInput, /
    ) -> PhoneAttachmentValidationResult: ...


def _pa_message_wire(request: PhoneAttachmentMessageRequest) -> dict[str, object]:
    """One pure wire projection, reused by the request bound and the public codec."""
    return {
        "revision": 1,
        "client_message_id": request.client_message_id,
        "text": request.payload.text,
        "target_binding": request.payload.target_binding,
        "attachments": [
            {
                "client_attachment_id": ref.item.client_attachment_id,
                "sha256": ref.item.sha256,
                "mime": ref.item.mime.value,
                "length": ref.item.length,
                "label": ref.item.label,
                "custody_reference": ref.custody_reference,
            }
            for ref in request.references
        ],
    }
