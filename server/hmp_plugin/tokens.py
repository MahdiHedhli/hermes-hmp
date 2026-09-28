"""P5 token exchange (`POST /auth/token`): PR5-3 order and disclosure, owner check without
mutation, single-transaction rotation (PR5-4), durable retry grace with deterministic successor
derivation (PR5-5, research R16, CS-13), `retry_state_lost`, expiry (PR5-7). Also the token-family
issue used by P4 (PR4-2, PR4-4). T026.

PR5-3 order:

1. per-IP rate limit, then (once the body is read) per-`device_id` rate limit (`429`);
2. shape and lengths;
3. device lookup;
4. signature over `HMP1-TOKEN` (before anything reveals device or token state);
5. `ts` freshness and nonce replay; the nonce is remembered only after the signature verified;
6. a signed request from a revoked device is `401 revoked`;
7. refresh-owner check, without mutating anything on a mismatch (PR5-4);
8. rotation in one transaction (PR5-4), or the PR5-5 retry grace, or reuse → family revoked.

Every failure is a uniform `401 unauthenticated`, except `401 revoked` for a signed request from a
revoked device or a revoked family, and for detected reuse. A body that is not I-JSON is
`400 bad_request` (TR-9); a body over the limits is `413`.

Retry grace (research R16, CS-13): the successor refresh and access tokens are
`HMAC-SHA256(k_grace, transcript("HMP1-GRACE", refresh_raw, family_id, purpose))` with
`purpose` in {"refresh", "access"}. The input is the RAW presented token, never its stored hash,
so nothing in the store lets anyone derive a token. The store keeps only hashes, including
`successor_hash`. A retry re-derives the successor and compares hashes; if that fails (a changed
or regenerated `k_grace`, a missing access row), the answer is `503 retry_state_lost`. The
grace-retry access token keeps its original `access_expires_at`.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from . import crypto, wire
from .contract import (
    ACCESS_TTL_S,
    CLOCK_SKEW_S,
    RATE_TOKEN_PER_MIN_PER_DEVICE_ID,
    RATE_TOKEN_PER_MIN_PER_IP,
    REFRESH_ABSOLUTE_TTL_S,
    REFRESH_IDLE_TTL_S,
    REFRESH_RETRY_GRACE_S,
    TAG_GRACE,
    TAG_TOKEN,
    ErrorCode,
    HmpError,
)
from .logging_policy import log_event
from .request_ctx import context, json_response, peer_key, read_json_body

PURPOSE_REFRESH = "refresh"
PURPOSE_ACCESS = "access"
TOKEN_BYTES = 32

DEVICE_ID_RE = re.compile(r"dev_[A-Za-z0-9_-]{22}")
FAMILY_PREFIX = "fam_"


@dataclass(frozen=True)
class TokenGrant:
    """Raw tokens as issued to the device (wire b64u). Never stored, never logged."""

    refresh_token: str
    access_token: str
    access_expires_at: int

    def __repr__(self) -> str:  # never print token values
        return f"TokenGrant(access_expires_at={self.access_expires_at})"


def token_hash(raw: bytes) -> bytes:
    """PR4-4 / TR-12: SHA-256 over the raw decoded bytes."""
    return crypto.sha256(raw)


def derive_successor(k_grace: bytes, refresh_raw: bytes, family_id: str, purpose: str) -> bytes:
    """Research R16: the deterministic successor of a presented raw refresh token."""
    if len(k_grace) != 32 or len(refresh_raw) != TOKEN_BYTES:
        raise ValueError("bad grace derivation input")
    if purpose not in (PURPOSE_REFRESH, PURPOSE_ACCESS):
        raise ValueError("unknown grace derivation purpose")
    message = crypto.transcript(TAG_GRACE, refresh_raw, family_id, purpose)
    return hmac.new(k_grace, message, hashlib.sha256).digest()


def is_device_id(value: Any) -> bool:
    return isinstance(value, str) and DEVICE_ID_RE.fullmatch(value) is not None


# --------------------------------------------------------------------------------------------------
# Issue (P4) — runs inside the caller's store transaction
# --------------------------------------------------------------------------------------------------


def issue_family(conn: Any, *, device_id: str, iid: str, now: int) -> TokenGrant:
    """A new token family with a random refresh and access token (PR4-2, PR4-4). Only hashes are
    written. `conn` is the connection of an open `Store.transaction()`."""
    family_id = FAMILY_PREFIX + wire.b64u_encode(crypto.random_bytes(16))
    refresh = crypto.random_bytes(TOKEN_BYTES)
    access = crypto.random_bytes(TOKEN_BYTES)
    expires = now + ACCESS_TTL_S
    conn.execute(
        "INSERT INTO token_families (family_id, device_id, created_at, revoked_at) "
        "VALUES (?, ?, ?, NULL)",
        (family_id, device_id, now),
    )
    conn.execute(
        "INSERT INTO refresh_tokens (hash, family_id, issued_at, last_used_at, used_at, "
        "successor_hash) VALUES (?, ?, ?, NULL, NULL, NULL)",
        (token_hash(refresh), family_id, now),
    )
    conn.execute(
        "INSERT INTO access_tokens (hash, family_id, device_id, iid, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (token_hash(access), family_id, device_id, iid, expires),
    )
    return TokenGrant(wire.b64u_encode(refresh), wire.b64u_encode(access), expires)


# --------------------------------------------------------------------------------------------------
# P5
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _TokenRequest:
    device_id: str
    refresh_raw: bytes
    ts: int
    nonce: bytes
    sig: bytes


def _unauthenticated() -> HmpError:
    return HmpError(ErrorCode.UNAUTHENTICATED)


def _parse(body: dict[str, Any]) -> _TokenRequest:
    """PR5-3 step 2: every member-level problem is the uniform `401 unauthenticated`."""
    try:
        device_id = body["device_id"]
        if not is_device_id(device_id):
            raise wire.WireError("device_id")
        return _TokenRequest(
            device_id=device_id,
            refresh_raw=wire.b64u_field("token", body["refresh_token"]),
            ts=wire.require_int(body["ts"], minimum=0),
            nonce=wire.b64u_field("nonce", body["nonce"]),
            sig=wire.b64u_signature(body["sig"]),
        )
    except (KeyError, wire.WireError) as exc:
        raise _unauthenticated() from exc


class TokenService:
    """P5 over one store and one identity. `iid`, `k_grace()` come from the loaded identity."""

    def __init__(self, store: Any, identity: Any) -> None:
        self._store = store
        self._identity = identity

    def exchange(self, body: dict[str, Any], now: int) -> TokenGrant:
        req = _parse(body)
        store = self._store
        iid = self._identity.iid
        device = store.get_device(req.device_id)
        if device is None:
            raise _unauthenticated()
        message = crypto.transcript(
            TAG_TOKEN, iid, req.device_id, token_hash(req.refresh_raw), req.ts, req.nonce
        )
        if not crypto.verify(bytes(device["device_pub"]), req.sig, message):
            raise _unauthenticated()
        if abs(req.ts - now) > CLOCK_SKEW_S:
            raise _unauthenticated()
        if store.nonce_seen(req.device_id, req.nonce):
            raise _unauthenticated()
        store.record_p5_nonce(req.device_id, req.nonce, now)
        if device["state"] == "REVOKED":
            raise HmpError(ErrorCode.REVOKED)
        if device["state"] != "ACTIVE":
            raise _unauthenticated()

        presented = token_hash(req.refresh_raw)
        row = store.get_refresh_token(presented)
        if row is None:
            raise _unauthenticated()
        family = store.get_token_family(row["family_id"])
        if family is None or family["device_id"] != req.device_id:
            raise _unauthenticated()  # PR5-4: owner mismatch, nothing changed
        if family["revoked_at"] is not None:
            raise HmpError(ErrorCode.REVOKED)
        if now >= int(family["created_at"]) + REFRESH_ABSOLUTE_TTL_S:
            raise _unauthenticated()  # PR5-7

        if row["used_at"] is None:
            if now >= int(row["issued_at"]) + REFRESH_IDLE_TTL_S:
                raise _unauthenticated()  # PR5-7
            grant = self._rotate(req, family_id=str(family["family_id"]), now=now)
            if grant is not None:
                log_event("token_rotate", outcome="ok", device_id=req.device_id)
                return grant
            row = store.get_refresh_token(presented)  # lost a race: now used
            if row is None or row["used_at"] is None:
                raise _unauthenticated()
        return self._retry_or_reuse(req, row, str(family["family_id"]), now)

    def _rotate(self, req: _TokenRequest, *, family_id: str, now: int) -> TokenGrant | None:
        """PR5-4: one transaction. None when another exchange used the token first."""
        k_grace = self._identity.k_grace()
        refresh = derive_successor(k_grace, req.refresh_raw, family_id, PURPOSE_REFRESH)
        access = derive_successor(k_grace, req.refresh_raw, family_id, PURPOSE_ACCESS)
        successor = token_hash(refresh)
        expires = now + ACCESS_TTL_S
        with self._store.transaction() as conn:
            live = conn.execute(
                "SELECT 1 FROM token_families f JOIN devices d ON d.device_id = f.device_id "
                "WHERE f.family_id = ? AND f.revoked_at IS NULL AND d.state = 'ACTIVE'",
                (family_id,),
            ).fetchone()
            if live is None:
                raise HmpError(ErrorCode.REVOKED)  # rolls back; revoked meanwhile
            cur = conn.execute(
                "UPDATE refresh_tokens SET used_at = ?, last_used_at = ?, successor_hash = ? "
                "WHERE hash = ? AND used_at IS NULL",
                (now, now, successor, token_hash(req.refresh_raw)),
            )
            if cur.rowcount != 1:
                return None
            conn.execute(
                "INSERT INTO refresh_tokens (hash, family_id, issued_at, last_used_at, used_at, "
                "successor_hash) VALUES (?, ?, ?, NULL, NULL, NULL)",
                (successor, family_id, now),
            )
            conn.execute(
                "INSERT INTO access_tokens (hash, family_id, device_id, iid, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_hash(access), family_id, req.device_id, self._identity.iid, expires),
            )
        return TokenGrant(wire.b64u_encode(refresh), wire.b64u_encode(access), expires)

    def _retry_or_reuse(self, req: _TokenRequest, row: Any, family_id: str, now: int) -> TokenGrant:
        """PR5-5: the same successor within the grace while it is unused; otherwise reuse.

        Both branches re-check that the family and the device are still live inside this read (or
        read/write) transaction, immediately before deciding: `exchange()`'s own earlier liveness
        checks ran moments before this method was even called, so an operator or self-revoke that
        lands in between must never let a grace-retry hand back a working grant, nor let a
        reuse-detection race skip revoking a family that is, in fact, still live.
        """
        store = self._store
        successor_hash = row["successor_hash"]
        in_grace = now - int(row["used_at"]) <= REFRESH_RETRY_GRACE_S
        with store.transaction() as conn:
            live = conn.execute(
                "SELECT 1 FROM token_families f JOIN devices d ON d.device_id = f.device_id "
                "WHERE f.family_id = ? AND f.revoked_at IS NULL AND d.state = 'ACTIVE'",
                (family_id,),
            ).fetchone()
            if live is None:
                raise HmpError(ErrorCode.REVOKED)  # rolls back; revoked meanwhile
            successor = store.get_refresh_token(successor_hash) if successor_hash else None
            if in_grace and (successor is None or successor["used_at"] is None):
                k_grace = self._identity.k_grace()
                refresh = derive_successor(k_grace, req.refresh_raw, family_id, PURPOSE_REFRESH)
                access = derive_successor(k_grace, req.refresh_raw, family_id, PURPOSE_ACCESS)
                access_row = store.get_access_token(token_hash(access))
                if (
                    successor is None
                    or not crypto.constant_time_equal(token_hash(refresh), bytes(successor_hash))
                    or access_row is None
                ):
                    log_event("token_retry", outcome="retry_state_lost", device_id=req.device_id)
                    raise HmpError(ErrorCode.RETRY_STATE_LOST)
                log_event("token_retry", outcome="ok", device_id=req.device_id)
                return TokenGrant(
                    wire.b64u_encode(refresh),
                    wire.b64u_encode(access),
                    int(access_row["expires_at"]),
                )
            conn.execute(
                "UPDATE token_families SET revoked_at = ? WHERE family_id = ? "
                "AND revoked_at IS NULL",
                (now, family_id),
            )
            conn.execute(
                "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
                (now, "refresh_reuse", req.device_id[:8], "family_revoked"),
            )
        log_event("token_reuse", outcome="family_revoked", device_id=req.device_id)
        raise HmpError(ErrorCode.REVOKED)


async def handle_token(request: web.Request) -> web.Response:
    ctx = context(request)
    now = ctx.now()
    ctx.limiter.check("token_ip", peer_key(request), RATE_TOKEN_PER_MIN_PER_IP, now)
    body = await read_json_body(request)
    device_id = body.get("device_id")
    if is_device_id(device_id):
        ctx.limiter.check("token_device", device_id, RATE_TOKEN_PER_MIN_PER_DEVICE_ID, now)
    grant = TokenService(ctx.store, ctx.identity).exchange(body, now)
    return json_response(
        {
            "access_token": grant.access_token,
            "access_expires_at": grant.access_expires_at,
            "refresh_token": grant.refresh_token,
        }
    )
