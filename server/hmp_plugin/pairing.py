"""Pairing P2 (`POST /pair/request`) and P4 (`POST /pair/complete`): PR2-2 check order, PR2-3
sanitization, PR2-5 durable nonces, the PR4-2 outcome table and PR4-3 fresh `ts`. T025.

P2 (PR2-2), cheapest first:

1. size and shape: `413` over the limits, `400 bad_request` for a body that is not an I-JSON
   object (TR-9);
2. per-IP, then per-offer rate limit (`429`);
3. offer lookup and state: not open → `409 offer_used` (no SAS); expired → `410 offer_expired`;
4. field decoding and lengths; 5. `device_name` validation; 6. constant-time secret-hash compare;
7. the possession-proof signature over `HMP1-PAIR-REQ` (the exact wire `device_name`);
8. the atomic claim, which persists `nd` and `ni` with the pairing (PR2-5).

Every other failure is `401 pair_failed`. Failures at steps 4-7 count against the offer, which
burns (state `burned`, then `409 offer_used`) after `OFFER_MAX_FAILURES`.

P4 (PR4-1..PR4-3): rate limits, then the pairing's durable nonces (unavailable → `410`), the
signature over `HMP1-PAIR-DONE`, then a fresh and strictly increasing `ts` (PR4-3), then the PR4-2
table in order. `confirm_by` bounds a pairing that has not been issued tokens yet; once tokens
were issued, the re-issue window (`PAIRING_CONFIRM_WINDOW_S` after the first issue) governs.
Reading `confirm_by` as also bounding issued pairings would make the "after that window →
`409 offer_used`" row unreachable, since the window always ends after `confirm_by`.

Interface with the operator CLI (T032): the CLI confirms or denies through `confirm_pairing` and
`deny_pairing`. A confirmed pairing's device is `device_id_for_pairing(pairing_id)`, created
`ACTIVE` in the confirming transaction (PR3-4). `device_id` is therefore fixed at P2
(HMP v1 §2: "minted by HMP at P2") and is `dev_` + the pairing id's 16 random bytes.
Offers are stored by the canonical b64u text of `oid`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from . import crypto, wire
from .contract import (
    CLOCK_SKEW_S,
    DEVICE_NAME_MAX_BYTES,
    OFFER_MAX_FAILURES,
    PAIRING_CONFIRM_WINDOW_S,
    PROTOCOL_VERSION,
    RATE_PAIR_COMPLETE_PER_MIN_PER_IP,
    RATE_PAIR_COMPLETE_PER_MIN_PER_PAIRING_ID,
    RATE_PAIR_REQUEST_PER_MIN_PER_IP,
    RATE_PAIR_REQUEST_PER_MIN_PER_OFFER,
    SAS_MAX_MISMATCHES,
    TAG_OFFER,
    TAG_PAIR_DONE,
    TAG_PAIR_REQ,
    TAG_PAIR_RESP,
    ErrorCode,
    HmpError,
)
from .logging_policy import log_event
from .request_ctx import context, json_response, peer_key, read_json_body
from .store import PAIRING_PENDING_STATE
from .tokens import TokenGrant, issue_family

UNNAMED_DEVICE = "unnamed device"

# PR2-3: Unicode general categories dropped from `device_name` before storage and display.
DROPPED_CATEGORIES: frozenset[str] = frozenset({"Cc", "Cf", "Zl", "Zp", "Co", "Cn"})

# Pairing states. `awaiting_operator` is the PR2-4 wire literal the store treats as pending.
STATE_AWAITING = PAIRING_PENDING_STATE
STATE_CONFIRMED = "confirmed"
STATE_DENIED = "denied"
STATE_EXPIRED = "expired"
PAIRING_STATES: frozenset[str] = frozenset(
    {STATE_AWAITING, STATE_CONFIRMED, STATE_DENIED, STATE_EXPIRED}
)

# b64u text of 16 bytes: the longest `oid` / `pairing_id` accepted as a rate-limit key.
_ID16_CHARS = 22


def sanitize_device_name(wire_value: str) -> str:
    """PR2-3: drop Cc/Cf/Zl/Zp/Co/Cn, apply NFC, truncate to DEVICE_NAME_MAX_BYTES; an empty
    result becomes "unnamed device". For storage and display only."""
    kept = "".join(ch for ch in wire_value if unicodedata.category(ch) not in DROPPED_CATEGORIES)
    text = unicodedata.normalize("NFC", kept)
    out: list[str] = []
    size = 0
    for ch in text:
        n = len(ch.encode("utf-8"))
        if size + n > DEVICE_NAME_MAX_BYTES:
            break
        out.append(ch)
        size += n
    return "".join(out) or UNNAMED_DEVICE


def device_id_for_pairing(pairing_id: str) -> str:
    """The device id a pairing activates (`dev_` + b64u of the pairing id's 16 bytes)."""
    wire.b64u_field("pairing_id", pairing_id)
    return "dev_" + pairing_id


def _failed() -> HmpError:
    return HmpError(ErrorCode.PAIR_FAILED)


def _strings(body: dict[str, Any], names: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        value = body.get(name)
        if not isinstance(value, str):
            raise _failed()
        out[name] = value
    return out


# --------------------------------------------------------------------------------------------------
# P2
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PairRequestAccepted:
    pairing_id: str
    ni: str
    device_sas: str
    confirm_by: int
    isig: str


class PairingService:
    def __init__(self, store: Any, identity: Any, limiter: Any) -> None:
        self._store = store
        self._identity = identity
        self._limiter = limiter

    # ---- P2 -------------------------------------------------------------------------------------

    def request(self, body: dict[str, Any], *, peer: str, now: int) -> PairRequestAccepted:
        # 1. shape: the members exist with their JSON types.
        fields = _strings(body, ("oid", "s", "device_name", "device_pub", "nd", "sig"))
        if "v" not in body:
            raise _failed()
        oid = fields["oid"]
        # 2. rate limits: per IP, then per offer.
        self._limiter.check("pair_request_ip", peer, RATE_PAIR_REQUEST_PER_MIN_PER_IP, now)
        if len(oid) > _ID16_CHARS:
            raise _failed()
        self._limiter.check("pair_request_offer", oid, RATE_PAIR_REQUEST_PER_MIN_PER_OFFER, now)
        # 3. offer lookup and state.
        offer = self._store.get_offer(oid)
        if offer is None:
            raise _failed()
        self._offer_state_or_raise(offer, now)
        # 4-7. every failure counts against the open offer.
        try:
            oid_raw = wire.b64u_field("oid", oid)
            if wire.require_int(body["v"]) != PROTOCOL_VERSION:
                raise wire.WireError("v")
            secret = wire.b64u_field("s", fields["s"])
            device_pub = wire.b64u_field("device_pub", fields["device_pub"])
            crypto.check_p256_spki(device_pub)
            nd = wire.b64u_field("nd", fields["nd"])
            sig = wire.b64u_signature(fields["sig"])
            name = fields["device_name"]
            if len(name.encode("utf-8", errors="strict")) > DEVICE_NAME_MAX_BYTES:
                raise wire.WireError("device_name")
            if not crypto.constant_time_equal(
                crypto.secret_hash(TAG_OFFER, secret), bytes(offer["secret_hash"])
            ):
                raise wire.WireError("secret")
            message = crypto.transcript(
                TAG_PAIR_REQ,
                self._identity.iid,
                oid_raw,
                crypto.sha256(secret),
                device_pub,
                name,
                nd,
            )
            if not crypto.verify(device_pub, sig, message):
                raise wire.WireError("sig")
        except (wire.WireError, crypto.CryptoError, UnicodeError) as exc:
            self._count_failure(oid)
            log_event("pair_request", outcome="pair_failed")
            raise _failed() from exc
        # 8. atomic claim.
        return self._claim(oid, oid_raw, device_pub, name, nd, now)

    def _offer_state_or_raise(self, offer: Any, now: int) -> None:
        state = offer["state"]
        if state == "expired":
            raise HmpError(ErrorCode.OFFER_EXPIRED)
        if state != "open":
            raise HmpError(ErrorCode.OFFER_USED)
        if now >= int(offer["expires_at"]):
            with self._store.transaction() as conn:
                conn.execute(
                    "UPDATE offers SET state = 'expired' WHERE oid = ? AND state = 'open'",
                    (offer["oid"],),
                )
            raise HmpError(ErrorCode.OFFER_EXPIRED)

    def _count_failure(self, oid: str) -> None:
        with self._store.transaction() as conn:
            conn.execute(
                "UPDATE offers SET failures = failures + 1, state = CASE "
                "WHEN failures + 1 >= ? THEN 'burned' ELSE state END "
                "WHERE oid = ? AND state = 'open'",
                (OFFER_MAX_FAILURES, oid),
            )

    def _claim(
        self, oid: str, oid_raw: bytes, device_pub: bytes, name: str, nd: bytes, now: int
    ) -> PairRequestAccepted:
        pairing_raw = crypto.random_bytes(16)
        pairing_id = wire.b64u_encode(pairing_raw)
        ni = crypto.random_bytes(32)
        confirm_by = now + PAIRING_CONFIRM_WINDOW_S
        with self._store.transaction() as conn:
            cur = conn.execute(
                "UPDATE offers SET state = 'claimed' WHERE oid = ? AND state = 'open' "
                "AND expires_at > ?",
                (oid, now),
            )
            if cur.rowcount != 1:
                row = conn.execute("SELECT state FROM offers WHERE oid = ?", (oid,)).fetchone()
                if row is not None and row["state"] in ("open", "expired"):
                    raise HmpError(ErrorCode.OFFER_EXPIRED)
                raise HmpError(ErrorCode.OFFER_USED)
            conn.execute(
                "INSERT INTO pairings (pairing_id, oid, device_pub, device_name_sanitized, nd, "
                "ni, confirm_by, state, sas_mismatches, last_p4_ts, first_issue_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)",
                (
                    pairing_id,
                    oid,
                    device_pub,
                    sanitize_device_name(name),
                    nd,
                    ni,
                    confirm_by,
                    STATE_AWAITING,
                ),
            )
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
                (now, "pair_request", pairing_id[:8], "awaiting_operator"),
            )
        sas = crypto.device_sas(crypto.spki_fingerprint(device_pub))
        response = crypto.transcript(
            TAG_PAIR_RESP,
            self._identity.iid,
            oid_raw,
            device_pub,
            nd,
            ni,
            pairing_raw,
            sas,
            confirm_by,
        )
        isig = crypto.sign(self._identity.private_key(), response)
        log_event(
            "pair_request", outcome="awaiting_operator", device_id=device_id_for_pairing(pairing_id)
        )
        return PairRequestAccepted(
            pairing_id=pairing_id,
            ni=wire.b64u_encode(ni),
            device_sas=sas,
            confirm_by=confirm_by,
            isig=wire.b64u_encode(isig),
        )

    # ---- P4 -------------------------------------------------------------------------------------

    def complete(self, body: dict[str, Any], *, now: int) -> CompleteOutcome:
        """P4 after the per-IP limit (applied by the handler before the body is read)."""
        pairing_id = body.get("pairing_id")
        if isinstance(pairing_id, str) and len(pairing_id) <= _ID16_CHARS:
            self._limiter.check(
                "pair_complete_pairing", pairing_id, RATE_PAIR_COMPLETE_PER_MIN_PER_PAIRING_ID, now
            )
        try:
            if not isinstance(pairing_id, str):
                raise wire.WireError("pairing_id")
            pairing_raw = wire.b64u_field("pairing_id", pairing_id)
            ts = wire.require_int(body.get("ts"), minimum=0)
            sig = wire.b64u_signature(body.get("sig"))
        except wire.WireError as exc:
            raise _failed() from exc
        row = self._store.get_pairing(pairing_id)
        if row is None:
            raise _failed()
        nd, ni = row["nd"], row["ni"]
        if not all(isinstance(n, bytes) and len(n) == 32 for n in (nd, ni)):
            raise HmpError(ErrorCode.OFFER_EXPIRED)  # pairing nonces unavailable (PR2-5)
        message = crypto.transcript(TAG_PAIR_DONE, self._identity.iid, pairing_raw, nd, ni, ts)
        if not crypto.verify(bytes(row["device_pub"]), sig, message):
            raise _failed()
        # PR4-3: fresh and strictly increasing, recorded atomically.
        if abs(ts - now) > CLOCK_SKEW_S:
            raise _failed()
        with self._store.transaction() as conn:
            cur = conn.execute(
                "UPDATE pairings SET last_p4_ts = ? WHERE pairing_id = ? "
                "AND (last_p4_ts IS NULL OR last_p4_ts < ?)",
                (ts, pairing_id, ts),
            )
            if cur.rowcount != 1:
                raise _failed()
        return self._outcome(pairing_id, now)

    def _outcome(self, pairing_id: str, now: int) -> CompleteOutcome:
        """PR4-2, in evaluation order."""
        store = self._store
        row = store.get_pairing(pairing_id)
        if row is None:
            raise _failed()
        state = row["state"]
        issued = row["first_issue_at"] is not None
        if state == STATE_DENIED:
            raise HmpError(ErrorCode.PAIR_DENIED)
        if state == STATE_EXPIRED or (not issued and now > int(row["confirm_by"])):
            raise HmpError(ErrorCode.OFFER_EXPIRED)
        if state == STATE_AWAITING:
            return CompleteOutcome(pending=True)
        if state != STATE_CONFIRMED:
            raise _failed()
        device_id = device_id_for_pairing(pairing_id)
        device = store.get_device(device_id)
        if device is None or device["state"] != "ACTIVE":
            raise HmpError(ErrorCode.PAIR_DENIED)
        if issued and now > int(row["first_issue_at"]) + PAIRING_CONFIRM_WINDOW_S:
            raise HmpError(ErrorCode.OFFER_USED)
        iid = self._identity.iid
        with store.transaction() as conn:
            live = conn.execute(
                "SELECT d.user_id FROM devices d JOIN pairings p ON p.pairing_id = ? "
                "WHERE d.device_id = ? AND d.state = 'ACTIVE' AND p.state = ?",
                (pairing_id, device_id, STATE_CONFIRMED),
            ).fetchone()
            if live is None:
                raise HmpError(ErrorCode.PAIR_DENIED)
            if issued:
                # Lost-response re-issue: the earlier family is revoked (PR4-2).
                conn.execute(
                    "UPDATE token_families SET revoked_at = ? WHERE device_id = ? "
                    "AND revoked_at IS NULL",
                    (now, device_id),
                )
                outcome = "reissued"
            else:
                cur = conn.execute(
                    "UPDATE pairings SET first_issue_at = ? WHERE pairing_id = ? "
                    "AND first_issue_at IS NULL",
                    (now, pairing_id),
                )
                if cur.rowcount != 1:
                    raise _failed()
                outcome = "issued"
            grant = issue_family(conn, device_id=device_id, iid=iid, now=now)
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
                (now, "pair_complete", pairing_id[:8], outcome),
            )
        if issued:
            store.cleanup_push_after_commit(now=now)
        log_event("pair_complete", outcome=outcome, device_id=device_id)
        return CompleteOutcome(
            pending=False, device_id=device_id, user_ref=str(live["user_id"]), grant=grant
        )


@dataclass(frozen=True)
class CompleteOutcome:
    pending: bool
    device_id: str | None = None
    user_ref: str | None = None
    grant: TokenGrant | None = None


# --------------------------------------------------------------------------------------------------
# Operator confirmation and denial (P3; used by the CLI, T032)
# --------------------------------------------------------------------------------------------------


def confirm_pairing(store: Any, pairing_id: str, *, user_id: str, label: str, now: int) -> str:
    """PR3-4: activate the device of a still-pending pairing, in one transaction. The user row
    must exist. Returns the device id. Raises `LookupError` when the pairing is not pending, its
    `confirm_by` has passed, or its `sas_mismatches` already reached `SAS_MAX_MISMATCHES` (SR-2:
    defense in depth -- the CLI's own SAS check already refuses this case first, but a pairing at
    the limit must never activate a device through any path)."""
    device_id = device_id_for_pairing(pairing_id)
    with store.transaction() as conn:
        row = conn.execute(
            "SELECT device_pub, confirm_by, sas_mismatches FROM pairings "
            "WHERE pairing_id = ? AND state = ?",
            (pairing_id, STATE_AWAITING),
        ).fetchone()
        if (
            row is None
            or now > int(row["confirm_by"])
            or int(row["sas_mismatches"]) >= SAS_MAX_MISMATCHES
        ):
            raise LookupError("pairing is not pending")
        device_pub = bytes(row["device_pub"])
        conn.execute(
            "INSERT INTO devices (device_id, user_id, device_fp, device_pub, label, state, "
            "created_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)",
            (device_id, user_id, crypto.spki_fingerprint(device_pub), device_pub, label, now),
        )
        conn.execute(
            "UPDATE pairings SET state = ? WHERE pairing_id = ?", (STATE_CONFIRMED, pairing_id)
        )
        conn.execute(
            "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
            (now, "pair_confirm", pairing_id[:8], "confirmed"),
        )
    return device_id


def deny_pairing(store: Any, pairing_id: str, *, now: int) -> bool:
    """Deny a pending pairing (P4 then answers `403 pair_denied`). False if it was not pending."""
    with store.transaction() as conn:
        cur = conn.execute(
            "UPDATE pairings SET state = ? WHERE pairing_id = ? AND state = ?",
            (STATE_DENIED, pairing_id, STATE_AWAITING),
        )
        if cur.rowcount == 1:
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
                (now, "pair_deny", pairing_id[:8], "denied"),
            )
    return cur.rowcount == 1


# --------------------------------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------------------------------


async def handle_pair_request(request: web.Request) -> web.Response:
    ctx = context(request)
    now = ctx.now()
    body = await read_json_body(request)
    accepted = PairingService(ctx.store, ctx.identity, ctx.limiter).request(
        body, peer=peer_key(request), now=now
    )
    return json_response(
        {
            "pairing_id": accepted.pairing_id,
            "state": STATE_AWAITING,
            "ni": accepted.ni,
            "device_sas": accepted.device_sas,
            "confirm_by": accepted.confirm_by,
            "isig": accepted.isig,
        },
        status=202,
    )


async def handle_pair_complete(request: web.Request) -> web.Response:
    ctx = context(request)
    now = ctx.now()
    ctx.limiter.check("pair_complete_ip", peer_key(request), RATE_PAIR_COMPLETE_PER_MIN_PER_IP, now)
    body = await read_json_body(request)
    outcome = PairingService(ctx.store, ctx.identity, ctx.limiter).complete(body, now=now)
    if outcome.pending:
        return json_response({"state": STATE_AWAITING}, status=202)
    if outcome.grant is None:  # never: every non-pending outcome carries a grant
        raise HmpError(ErrorCode.PAIR_FAILED)
    return json_response(
        {
            "device_id": outcome.device_id,
            "user_ref": outcome.user_ref,
            "refresh_token": outcome.grant.refresh_token,
            "access_token": outcome.grant.access_token,
            "access_expires_at": outcome.grant.access_expires_at,
        }
    )
