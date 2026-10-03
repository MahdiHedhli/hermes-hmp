"""PN-REG authenticated device registration. No grants, provider addresses or network calls.

Every await precedes a fresh authority/configuration check. Writers recheck device
and family under BEGIN IMMEDIATE before replay/CAS; nothing awaits inside it.
The volatile DELETE fence is shared with future dispatch/resolve, not an ACK.
"""

from __future__ import annotations

import json
import sqlite3

from aiohttp import web

from . import crypto, push_config, wire
from .auth import AuthContext
from .contract import ErrorCode, HmpError
from .push_issuer import RouteInputs, rederive_route, route_text
from .request_ctx import ServerContext, bearer, context, json_response

_PUT_FIELDS = {
    "v",
    "request_id",
    "expected_generation",
    "platform",
    "addr_kind",
    "relay_kid",
    "sealed",
    "seal_expires_at",
}


def _owner(request: web.Request) -> tuple[ServerContext, AuthContext]:
    ctx = context(request)
    auth = bearer(request)
    if not ctx.is_approval_owner_device(auth.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)
    return ctx, auth


def _current(request: web.Request, ctx: ServerContext) -> None:
    # Same PR7-6 no-response rule as middleware, rechecked after every await.
    try:
        current = ctx.identity.still_current()
    except Exception:
        current = False
    if not current:
        if request.transport is not None:
            request.transport.abort()
        if ctx.on_identity_changed is not None:
            ctx.on_identity_changed()
        raise HmpError(ErrorCode.OTHER, 503)


def _fresh(request: web.Request, ctx: ServerContext, auth: AuthContext, conn) -> None:
    _current(request, ctx)
    ctx.store.require_push_liveness_in(conn, auth.device_id, auth.family_id)
    if bearer(request) != auth:
        raise HmpError(ErrorCode.REVOKED)
    if not ctx.is_approval_owner_device(auth.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)


async def _body(request: web.Request) -> dict:
    if request.content_length is not None and request.content_length > 4096:
        raise HmpError(ErrorCode.TOO_LARGE)
    try:
        raw = bytearray()
        # Bound streamed/chunked bodies too, without first materializing MAX_BODY_BYTES.
        async for chunk in request.content.iter_chunked(4097):
            raw.extend(chunk)
            if len(raw) > 4096:
                raise HmpError(ErrorCode.TOO_LARGE)
        return wire.parse_body(bytes(raw), max_bytes=4096)
    except (web.HTTPRequestEntityTooLarge, wire.TooLargeError):
        raise HmpError(ErrorCode.TOO_LARGE) from None
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None


def _generation(body: dict) -> int:
    if wire.require_int(body.get("v")) != 1:
        raise wire.WireError("invalid push version")
    return wire.require_int(body.get("expected_generation"), minimum=0)


def _put_shape(body: dict, now: int) -> tuple[bytes, bytes]:
    expected = _PUT_FIELDS | ({"env"} if body.get("platform") == "apns" else set())
    if set(body) != expected:
        raise wire.WireError("invalid push members")
    _generation(body)
    if not push_config.valid_kid(body["relay_kid"]):
        raise wire.WireError("invalid push kid")
    if body["platform"] == "apns":
        if body["addr_kind"] != "apns_token" or body["env"] not in ("sandbox", "production"):
            raise wire.WireError("invalid push platform binding")
    elif body["platform"] == "fcm":
        if body["addr_kind"] not in ("fcm_token", "fcm_fid"):
            raise wire.WireError("invalid push platform binding")
    else:
        raise wire.WireError("invalid push platform")
    expiry = wire.require_int(body["seal_expires_at"], minimum=0)
    if not now + 3600 < expiry <= now + 1209600:
        raise wire.WireError("invalid push expiry")
    intent = wire.b64u_decode_bounded(body["request_id"], max_length=32)
    sealed = wire.b64u_decode_bounded(body["sealed"], max_length=1105)
    if not 16 <= len(intent) <= 32 or not 82 <= len(sealed) <= 1105:
        raise wire.WireError("invalid push encoding length")
    # Closed validated ASCII member/value domain, integers only: stable canonical body hash.
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return crypto.sha256(intent), crypto.sha256(canonical)


def _available(ctx: ServerContext, kid: str) -> None:
    availability = ctx.push_availability()
    if not availability.available:
        raise HmpError(ErrorCode.WRITE_GATE_CLOSED, why=availability.why)
    if kid not in availability.live_kids:
        raise HmpError(ErrorCode.BAD_REQUEST)


async def _key(ctx: ServerContext) -> bytes | None:
    try:
        key = await ctx.identity.read_k_grace_for_push()
        return key if type(key) is bytes and len(key) == 32 else None
    except (OSError, ValueError):
        return None


def _inputs(row) -> RouteInputs:
    return RouteInputs(
        row["iid"],
        row["host_generation"],
        row["device_id"],
        row["family_id"],
        row["generation"],
        bytes(row["salt"]),
    )


async def handle_push_get(request: web.Request) -> web.Response:
    ctx, auth = _owner(request)
    ctx.limiter.check("push_status", auth.device_id, 30, ctx.now())
    key = await _key(ctx)
    _current(request, ctx)
    # A revoke/family rotation/owner denial during the read must never leak old status.
    ctx, auth = _owner(request)
    availability = ctx.push_availability()
    generation, epoch, row = ctx.store.push_status_snapshot(
        auth.device_id, family_id=auth.family_id
    )
    registration = None
    if row is not None and not ctx.push_route_fenced(bytes(row["route_hash"])):
        state = row["state"]
        if state == "active":
            usable = (
                row["iid"] == ctx.iid
                and row["host_generation"] == epoch
                and row["generation"] == generation
                and row["family_id"] == auth.family_id
                and row["expires_at"] > ctx.now()
                and (not availability.available or row["relay_kid"] in availability.live_kids)
                and rederive_route(key, _inputs(row), bytes(row["route_hash"])) is not None
            )
            state = "active" if usable else "expired"
        elif state not in ("provider_gone", "expired") or row["generation"] + 1 != generation:
            state = None
        if state is not None:
            registration = {
                "state": state,
                "platform": row["platform"],
                "expires_at": row["expires_at"],
            }
    body = {
        "available": availability.available,
        "generation": generation,
        "registration": registration,
    }
    if availability.available:
        body["relay_kids"] = list(availability.relay.kids)
    else:
        body["why"] = availability.why
    return json_response(body)


async def handle_push_put(request: web.Request) -> web.Response:
    ctx, auth = _owner(request)
    ctx.limiter.check("push_write", auth.device_id, 6, ctx.now())
    body = await _body(request)
    try:
        request_hash, body_hash = _put_shape(body, ctx.now())
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    _current(request, ctx)
    if not ctx.is_approval_owner_device(auth.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)
    _available(ctx, body["relay_kid"])
    key = await _key(ctx)
    # Key I/O may yield: reopen neither authority nor delivery on an obsolete snapshot.
    try:
        with ctx.store.transaction() as conn:
            _fresh(request, ctx, auth, conn)
            _available(ctx, body["relay_kid"])
            try:
                _put_shape(body, ctx.now())
            except wire.WireError:
                raise HmpError(ErrorCode.BAD_REQUEST) from None
            generation_now = ctx.store.push_generation_in(conn, auth.device_id)
            previous = ctx.store.active_push_in(conn, auth.device_id)
            if previous is not None and bytes(previous["request_hash"]) == request_hash:
                if bytes(previous["body_hash"]) != body_hash:
                    raise HmpError(ErrorCode.IDEMPOTENCY_CONFLICT)
                if previous["family_id"] != auth.family_id or previous["expires_at"] <= ctx.now():
                    raise HmpError(ErrorCode.STALE)
                route = rederive_route(key, _inputs(previous), bytes(previous["route_hash"]))
                epoch = conn.execute(
                    "SELECT store_revocation_epoch FROM meta WHERE id = 1"
                ).fetchone()[0]
                if (
                    previous["iid"] != ctx.iid
                    or previous["host_generation"] != epoch
                    or previous["generation"] != generation_now
                    or ctx.push_route_fenced(bytes(previous["route_hash"]))
                ):
                    raise HmpError(ErrorCode.STALE)
                if route is None:
                    raise HmpError(ErrorCode.RETRY_STATE_LOST)
                result = {
                    "route": route_text(route),
                    "generation": previous["generation"],
                    "expires_at": previous["expires_at"],
                    "state": "active",
                }
            else:
                if body["expected_generation"] != generation_now:
                    raise HmpError(ErrorCode.STALE)
                if key is None:
                    raise HmpError(ErrorCode.OTHER, 503)
                result = ctx.store.replace_push_in(
                    conn,
                    device_id=auth.device_id,
                    family_id=auth.family_id,
                    iid=ctx.iid,
                    key=key,
                    body=body,
                    sealed=wire.b64u_decode_bounded(body["sealed"], max_length=1105),
                    request_hash=request_hash,
                    body_hash=body_hash,
                    now=ctx.now(),
                )
        if previous is not None and result["generation"] != previous["generation"]:
            ctx.push_delete_fence.discard(bytes(previous["route_hash"]))
    except sqlite3.Error:
        raise HmpError(ErrorCode.OTHER, 503) from None
    return json_response(result)


async def handle_push_delete(request: web.Request) -> web.Response:
    ctx, auth = _owner(request)
    ctx.limiter.check("push_write", auth.device_id, 6, ctx.now())
    body = await _body(request)
    try:
        if set(body) != {"v", "expected_generation"}:
            raise wire.WireError("invalid push delete members")
        expected = _generation(body)
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    previous = None
    try:
        with ctx.store.transaction() as conn:
            _fresh(request, ctx, auth, conn)
            previous = ctx.store.active_push_in(conn, auth.device_id)
            if expected != ctx.store.push_generation_in(conn, auth.device_id):
                raise HmpError(ErrorCode.STALE)
            generation = ctx.store.delete_push_in(conn, auth.device_id, now=ctx.now())
        if previous is not None:
            ctx.push_delete_fence.discard(bytes(previous["route_hash"]))
    except sqlite3.Error:
        # BEGIN/COMMIT can fail too. Re-read the current digest after rollback;
        # if storage cannot even identify it, fail closed for this listener.
        try:
            _, _, current = ctx.store.push_status_snapshot(auth.device_id)
            ctx.fence_push_delete(
                bytes(current["route_hash"])
                if current is not None and current["state"] == "active"
                else None
            )
        except Exception:
            ctx.fence_push_delete(None, unreadable=True)
        raise HmpError(ErrorCode.OTHER, 503) from None
    return json_response({"generation": generation})
