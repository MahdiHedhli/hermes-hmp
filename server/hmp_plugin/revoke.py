"""P7-3 self-revoke (`POST /devices/self/revoke`) and operator revoke helpers (PR7-1: atomic
family revoke; the last-device hint prints Hermes commands and never runs them). T027.

Self-revoke (PR7-3), after bearer authentication (TR-5, PR5-6):

| Situation | Response |
|---|---|
| revoked | `200 {}` |
| stale `ts` or bad signature | `401 unauthenticated` |
| device not active | `401 revoked` |
| malformed | `400 bad_request` |

A bearer token of a revoked device is already answered `401 revoked` by `auth.py`; the row is
re-checked inside the revoking transaction, so a revocation that lands in between is also
`401 revoked`. The signature is `HMP1-SELF-REVOKE` over (`iid`, `device_id`, `ts`) with the
device key; `ts` must be within `CLOCK_SKEW_S` of the host clock.

Operator revoke (PR7-1): `revoke_device` revokes the device and every token family of it in one
transaction. When that leaves its user with no active device, the caller (the CLI, T032) prints
`last_device_hint(...)`: the Hermes `pairing revoke` command for each profile where the user is
still approved, plus a flag for instance-wide env allowlist membership. HMP never runs them.
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from . import crypto, wire
from .contract import CLOCK_SKEW_S, PLATFORM_NAME, TAG_SELF_REVOKE, ErrorCode, HmpError
from .logging_policy import log_event
from .request_ctx import bearer, context, json_response, read_json_body


@dataclass(frozen=True)
class RevokeResult:
    found: bool
    was_active: bool = False
    user_id: str | None = None
    last_device: bool = False  # the user has no ACTIVE device left


def _revoke_in(conn: Any, device_id: str, now: int, event: str) -> RevokeResult:
    row = conn.execute(
        "SELECT user_id, state FROM devices WHERE device_id = ?", (device_id,)
    ).fetchone()
    if row is None:
        return RevokeResult(found=False)
    was_active = row["state"] == "ACTIVE"
    conn.execute("UPDATE devices SET state = 'REVOKED' WHERE device_id = ?", (device_id,))
    conn.execute(
        "UPDATE token_families SET revoked_at = ? WHERE device_id = ? AND revoked_at IS NULL",
        (now, device_id),
    )
    (remaining,) = conn.execute(
        "SELECT COUNT(*) FROM devices WHERE user_id = ? AND state = 'ACTIVE'", (row["user_id"],)
    ).fetchone()
    conn.execute(
        "INSERT INTO audit (ts, event, id_prefix8, outcome) VALUES (?, ?, ?, ?)",
        (now, event, device_id[:8], "revoked"),
    )
    return RevokeResult(
        found=True, was_active=was_active, user_id=str(row["user_id"]), last_device=remaining == 0
    )


def revoke_device(store: Any, device_id: str, *, now: int) -> RevokeResult:
    """PR7-1: the device and all its token families, atomically. Idempotent."""
    with store.transaction() as conn:
        result = _revoke_in(conn, device_id, now, "operator_revoke")
    if result.found:
        store.cleanup_push_after_commit(now=now)
        log_event("operator_revoke", outcome="revoked", device_id=device_id)
    return result


def last_device_hint(
    user_id: str, approved_profiles: Iterable[str], *, env_allowlisted: bool
) -> list[str]:
    """PR7-1: the commands the operator may run to remove the user from Hermes. Text only;
    HMP never runs them."""
    lines = [
        f"hermes -p {shlex.quote(profile)} pairing revoke {PLATFORM_NAME} {shlex.quote(user_id)}"
        for profile in sorted(set(approved_profiles))
    ]
    if env_allowlisted:
        lines.append(
            "note: this user is also in an instance-wide env allowlist; remove it from the "
            "Hermes configuration to withdraw that grant"
        )
    return lines


# --------------------------------------------------------------------------------------------------
# PR7-3 self-revoke
# --------------------------------------------------------------------------------------------------


def self_revoke(store: Any, iid: str, device_id: str, body: dict[str, Any], *, now: int) -> None:
    try:
        ts = wire.require_int(body["ts"], minimum=0)
        sig = wire.b64u_signature(body["sig"])
    except (KeyError, wire.WireError) as exc:
        raise HmpError(ErrorCode.BAD_REQUEST) from exc
    device = store.get_device(device_id)
    if device is None:
        raise HmpError(ErrorCode.UNAUTHENTICATED)
    if abs(ts - now) > CLOCK_SKEW_S:
        raise HmpError(ErrorCode.UNAUTHENTICATED)
    message = crypto.transcript(TAG_SELF_REVOKE, iid, device_id, ts)
    if not crypto.verify(bytes(device["device_pub"]), sig, message):
        raise HmpError(ErrorCode.UNAUTHENTICATED)
    with store.transaction() as conn:
        state = conn.execute(
            "SELECT state FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if state is None or state["state"] != "ACTIVE":
            raise HmpError(ErrorCode.REVOKED)
        _revoke_in(conn, device_id, now, "self_revoke")
    store.cleanup_push_after_commit(now=now)
    log_event("self_revoke", outcome="revoked", device_id=device_id)


async def handle_self_revoke(request: web.Request) -> web.Response:
    ctx = context(request)
    who = bearer(request)
    body = await read_json_body(request)
    self_revoke(ctx.store, ctx.iid, who.device_id, body, now=ctx.now())
    return json_response({})
