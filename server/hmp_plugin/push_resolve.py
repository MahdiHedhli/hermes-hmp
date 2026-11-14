"""PN-RES authenticated navigation hints, never approval or execution authority.

No row reconciliation, mutation, automatic answer, route echo or provider I/O.
Source-bound approval gate is injected by build_app, safe across plugin reloads.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from aiohttp import web

from . import crypto, wire
from .auth import AuthContext
from .contract import ErrorCode, HmpError, WriteGateState
from .gate import direct_send_gate
from .prompts import RowView, is_authoritative
from .push_hints import HintBinding, hint_live
from .push_issuer import rederive_route
from .push_registration import _body, _current, _inputs, _key, _owner
from .reads import require_bot_authorized
from .request_ctx import ServerContext, json_response

Gate = Callable[..., Awaitable[Any]]


def _not_found() -> None:
    raise HmpError(ErrorCode.NOT_FOUND)


def _flag(ctx: ServerContext) -> bool:
    try:
        block = ctx.push_settings()
        return isinstance(block, Mapping) and block.get("enabled") is True
    except Exception:
        return False


def _local(
    request: web.Request, ctx: ServerContext, auth: AuthContext, key: bytes | None, hint: str
) -> tuple[HintBinding, RowView]:
    _current(request, ctx)
    current_ctx, current_auth = _owner(request)
    if current_ctx is not ctx or current_auth != auth or not _flag(ctx):
        _not_found()
    generation, epoch, row = ctx.store.push_status_snapshot(
        auth.device_id, family_id=auth.family_id
    )
    if row is None or row["state"] != "active":
        _not_found()
    digest = bytes(row["route_hash"])
    try:
        route = rederive_route(key, _inputs(row), digest)
    except crypto.CryptoError:
        route = None
    if (
        row["device_id"] != auth.device_id
        or row["family_id"] != auth.family_id
        or row["iid"] != ctx.iid
        or row["host_generation"] != epoch
        or row["generation"] != generation
        or row["expires_at"] <= ctx.now()
        or ctx.push_route_fenced(digest)
        or route is None
    ):
        _not_found()
    binding = ctx.push_hints.lookup(hint, now=ctx.now())
    store = ctx.prompt_store
    if (
        binding is None
        or binding.route_hash != digest
        or binding.generation != generation
        or store is None
        or store.closed
        or binding.prompt_generation != store.generation
        or binding.key[:2] != (ctx.iid, auth.user_id)
    ):
        _not_found()
    view = store.view_row(binding.key, now=ctx.now(), members=ctx.approval_members_now())
    if (
        view is None
        or view.key != binding.key
        or view.kind != "approval"
        or view.surface not in ("bot_chat", "phone_chat")
        or (view.surface == "phone_chat" and store.phone_closed)
        or not hint_live(binding, view, ctx.now())
    ):
        _not_found()
    return binding, view


async def _grant(ctx: ServerContext, auth: AuthContext, profile: str) -> None:
    if ctx.bridge is None:
        _not_found()
    bridge = ctx.bridge
    source = bridge.authz_state
    try:
        await asyncio.to_thread(require_bot_authorized, bridge, auth.user_id, profile)
    except HmpError:
        # ERR-3 details never disclose the hinted bot or grant state.
        _not_found()
    if ctx.bridge is not bridge or bridge.authz_state != source:
        _not_found()


async def handle_push_resolve(request: web.Request, *, require_gate: Gate) -> web.Response:
    ctx, auth = _owner(request)
    ctx.limiter.check("push_resolve", auth.device_id, 30, ctx.now())
    body = await _body(request)
    _current(request, ctx)
    _owner(request)
    try:
        if set(body) != {"v", "hint"} or wire.require_int(body.get("v")) != 1:
            raise wire.WireError("invalid hint body")
        hint = body["hint"]
        if type(hint) is not str or not 22 <= len(hint) <= 64:
            raise wire.WireError("invalid hint size")
        wire.b64u_decode_bounded(hint, max_length=48)
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    if not _flag(ctx):
        _not_found()
    key = await _key(ctx)
    binding, view = _local(request, ctx, auth, key, hint)
    try:
        await _grant(ctx, auth, binding.key[2])
    finally:
        binding, view = _local(request, ctx, auth, key, hint)
    # Surface gate precedes visibility. Delivery config/kid liveness are not
    # resolver gates; a closed approval surface must retain its 503 result.
    try:
        endpoint = await require_gate(ctx, binding.key[2], member=view.surface)
    finally:
        binding, view = _local(request, ctx, auth, key, hint)
    try:
        await _grant(ctx, auth, binding.key[2])
    finally:
        binding, view = _local(request, ctx, auth, key, hint)
    gate = direct_send_gate(
        base_write_gate=ctx.write_gate(),
        flag_enabled=ctx.direct_send_effective(),
        endpoint=endpoint,
    )
    if not ctx.approval_surface_available(view.surface) or gate.state not in (
        WriteGateState.OPEN,
        WriteGateState.OPEN_GUARDED,
    ):
        raise HmpError(ErrorCode.WRITE_GATE_CLOSED)
    if view.hidden_now:
        _not_found()
    if view.visible_now:
        return json_response({"state": "located", "profile": binding.key[2]})
    if view.status != "open" and is_authoritative(view.settle_cause):
        return json_response({"state": "not_pending"})
    _not_found()
