"""Authenticated self-service Controls requests; no remote decision endpoint.

The listener registers these routes only for an explicit local startup opt-in. All
origin fields come from the bearer and current Store epochs. Records are history,
never an entitlement or a substitute for the ordinary feature gates.
"""
from __future__ import annotations

import re
from typing import Any

from aiohttp import web

from . import wire
from .auth import AuthContext, Authenticator
from .contract import ErrorCode, HmpError
from .controls_requests import (
    ControlsRequestStore, RequestOrigin, RequestRecordView, remote_record_fields,
)
from .reads import require_bot_authorized
from .request_ctx import context, peer_key, single_header
from .store import _request_schema_valid

_MAX_SAFE_NOW = (1 << 53) - 1 - 600
_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
_REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_CLIENT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z",
    re.ASCII,
)


def registration_ready(ctx: Any) -> bool:
    """A local startup gate; malformed or unavailable Store schema stays unregistered."""
    if ctx.controls_requests_enabled is not True or ctx.compat.supported is not True:
        return False
    try:
        if ctx.identity.still_current() is not True:
            return False
        with ctx.store.transaction() as conn:
            return _request_schema_valid(conn) is True
    except Exception:
        return False


def _unavailable() -> HmpError:
    return HmpError(ErrorCode.CONTROLS_REQUEST_UNAVAILABLE)


def _now(ctx: Any) -> int:
    try:
        value = ctx.clock()
    except Exception:
        raise _unavailable() from None
    if type(value) is not int or not 0 <= value <= _MAX_SAFE_NOW:
        raise _unavailable()
    return value


def _epochs(ctx: Any) -> tuple[int, int]:
    try:
        value = ctx.store.epoch_authority_snapshot()
    except Exception:
        raise _unavailable() from None
    if (not isinstance(value, tuple) or len(value) != 2
            or any(type(v) is not int or v < 0 for v in value)):
        raise _unavailable()
    return value


def _initial(request: web.Request) -> tuple[Any, AuthContext, RequestOrigin]:
    ctx = context(request)
    who = Authenticator(ctx.store, ctx.iid, ctx.now).authenticate(
        single_header(request, "Authorization"), single_header(request, "HMP-Instance")
    )
    if not registration_ready(ctx):
        raise _unavailable()
    try:
        current = ctx.identity.still_current()
        iid = ctx.iid
    except Exception:
        raise _unavailable() from None
    if current is not True:
        raise _unavailable()
    instance_epoch, revocation_epoch = _epochs(ctx)
    return ctx, who, RequestOrigin(
        who.device_id, who.user_id, who.family_id, iid,
        instance_epoch, revocation_epoch,
    )


def _current(request: web.Request, ctx: Any, who: AuthContext, origin: RequestOrigin) -> None:
    """Repeat after every body/bridge await and before the synchronous Store operation."""
    try:
        if ctx.identity.still_current() is not True or ctx.iid != origin.iid:
            raise _unavailable()
        refreshed = Authenticator(ctx.store, ctx.iid, ctx.now).authenticate(
            single_header(request, "Authorization"), single_header(request, "HMP-Instance")
        )
    except HmpError:
        raise
    except Exception:
        raise _unavailable() from None
    if refreshed != who or _epochs(ctx) != (
        origin.instance_epoch, origin.store_revocation_epoch
    ):
        raise _unavailable()


def _rate(request: web.Request, ctx: Any, who: AuthContext, bucket: str, limit: int) -> None:
    now = _now(ctx)
    ctx.limiter.check("controls_request_ip", peer_key(request), 60, now)
    ctx.limiter.check(bucket, who.device_id, limit, now)


async def _body_bytes(request: web.Request) -> bytes:
    if request.content_length is not None and request.content_length > 512:
        raise HmpError(ErrorCode.BAD_REQUEST)
    body = bytearray()
    while True:
        part = await request.content.read(513 - len(body))
        if not part:
            break
        body.extend(part)
        if len(body) > 512:
            raise HmpError(ErrorCode.BAD_REQUEST)
    return bytes(body)


async def _empty(request: web.Request) -> None:
    if request.query_string or await _body_bytes(request):
        raise HmpError(ErrorCode.BAD_REQUEST)


def _json(body: dict[str, object], *, status: int = 200) -> web.Response:
    encoded = wire.dump_json(body)
    if len(encoded) > 2048:
        raise _unavailable()
    return web.Response(status=status, body=encoded, content_type="application/json",
                        headers={"Cache-Control": "no-store"})


def _record_response(request: web.Request, ctx: Any, who: AuthContext,
                     origin: RequestOrigin, record: RequestRecordView,
                     *, status: int = 200) -> web.Response:
    # A historical GRANTED row is not a grant. The fresh value is a hint only;
    # ordinary jobs/models use their own checks regardless of this response.
    effective = "unknown"
    current: tuple[int, int | None] | None = None
    if record.current_origin_active and record.current_iid_matches:
        try:
            current = ControlsRequestStore(ctx.store).current_controls_snapshot(
                origin, current_iid=ctx.iid
            )
            row = current[1] if current is not None else None
            if (current == (record.current_controls_revision, record.current_controls_allowed)
                    and type(row) is int and row in (0, 1)):
                effective = "granted" if row == 1 else "missing"
            elif (current == (record.current_controls_revision, None)
                  and row is None):
                reader = ctx.readiness_owner_device_ids
                ids = reader() if reader is not None else None
                if type(ids) is frozenset and all(type(item) is str for item in ids):
                    effective = "granted" if origin.device_id in ids else "missing"
        except Exception:
            effective = "unknown"
        # A legacy allowlist reader is outside Store's transaction and may itself
        # race a direct host Controls write. Never publish its stale conclusion.
        try:
            final = ControlsRequestStore(ctx.store).current_controls_snapshot(
                origin, current_iid=ctx.iid
            )
            if final != current or final != (
                record.current_controls_revision, record.current_controls_allowed
            ):
                effective = "unknown"
        except Exception:
            effective = "unknown"
    try:
        fields = remote_record_fields(record, effective_controls=effective)
    except (RuntimeError, ValueError):
        raise _unavailable() from None
    _current(request, ctx, who, origin)
    return _json(fields, status=status)


def _store_result(code: str) -> None:
    if code == "not_found":
        raise HmpError(ErrorCode.NOT_FOUND)
    if code in ("conflict", "already_decided"):
        raise HmpError(ErrorCode.IDEMPOTENCY_CONFLICT)
    if code == "quota":
        raise HmpError(ErrorCode.RATE_LIMITED)
    if code != "ok":
        raise _unavailable()


def _profile_feature(body: dict[str, object]) -> tuple[str, str, str]:
    if set(body) != {"client_request_id", "bot_profile", "feature"}:
        raise HmpError(ErrorCode.BAD_REQUEST)
    client_id, profile, feature = (
        body["client_request_id"], body["bot_profile"], body["feature"]
    )
    if (type(client_id) is not str or _CLIENT_ID.fullmatch(client_id) is None
            or type(profile) is not str or _PROFILE.fullmatch(profile) is None
            or type(feature) is not str or feature not in ("jobs", "models")):
        raise HmpError(ErrorCode.BAD_REQUEST)
    return client_id, profile, feature


def _feature_available(ctx: Any, feature: str) -> bool:
    if feature == "jobs":
        return ctx.is_cron_available() and ctx.cron_enabled()
    return ctx.is_model_available() and ctx.model_enabled()


def _record_by_request(ctx: Any, origin: RequestOrigin, request_id: str, now: int) -> RequestRecordView:
    try:
        result = ControlsRequestStore(ctx.store).status_by_request_id(
            origin, request_id=request_id, now=now, current_iid=ctx.iid
        )
    except ValueError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    except Exception:
        raise _unavailable() from None
    _store_result(result.code)
    if result.record is None:
        raise _unavailable()
    return result.record


async def capabilities(request: web.Request) -> web.Response:
    ctx, who, origin = _initial(request)
    _rate(request, ctx, who, "controls_request_read", 120)
    await _empty(request)
    _current(request, ctx, who, origin)
    return _json({"protocol": 1, "supported": True,
                  "scope": "device_jobs_models_now_and_future_authorized_bots",
                  "ttl_seconds": 600})


async def create(request: web.Request) -> web.Response:
    ctx, who, origin = _initial(request)
    _rate(request, ctx, who, "controls_request_create", 10)
    if request.query_string:
        raise HmpError(ErrorCode.BAD_REQUEST)
    raw = await _body_bytes(request)
    try:
        body = wire.parse_body(raw, max_bytes=512, max_depth=8)
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    client_id, profile, feature = _profile_feature(body)
    _current(request, ctx, who, origin)
    if ctx.bridge is None or not _feature_available(ctx, feature):
        raise _unavailable()
    # The existing per-bot authorization check is deliberately before creation.
    require_bot_authorized(ctx.bridge, who.user_id, profile)
    _current(request, ctx, who, origin)
    if not _feature_available(ctx, feature):
        raise _unavailable()
    now = _now(ctx)
    try:
        outcome = ControlsRequestStore(ctx.store).create(
            origin, client_id=client_id, profile=profile, feature=feature,
            now=now, current_iid=ctx.iid,
        )
    except ValueError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    except Exception:
        raise _unavailable() from None
    if outcome.code not in ("created", "ok"):
        _store_result(outcome.code)
        raise _unavailable()
    if outcome.request_id is None:
        raise _unavailable()
    _current(request, ctx, who, origin)
    record = _record_by_request(ctx, origin, outcome.request_id, _now(ctx))
    return _record_response(request, ctx, who, origin, record,
                            status=202 if outcome.code == "created" and record.state == "PENDING" else 200)


async def by_client_id(request: web.Request) -> web.Response:
    ctx, who, origin = _initial(request)
    _rate(request, ctx, who, "controls_request_read", 120)
    await _empty(request)
    client_id = request.match_info.get("client_id", "")
    if _CLIENT_ID.fullmatch(client_id) is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    _current(request, ctx, who, origin)
    try:
        result = ControlsRequestStore(ctx.store).status_record_by_client_id(
            origin, client_id=client_id, now=_now(ctx), current_iid=ctx.iid
        )
    except ValueError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    except Exception:
        raise _unavailable() from None
    _store_result(result.code)
    if result.record is None:
        raise _unavailable()
    return _record_response(request, ctx, who, origin, result.record)


async def by_request_id(request: web.Request) -> web.Response:
    ctx, who, origin = _initial(request)
    _rate(request, ctx, who, "controls_request_read", 120)
    await _empty(request)
    request_id = request.match_info.get("request_id", "")
    if _REQUEST_ID.fullmatch(request_id) is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    _current(request, ctx, who, origin)
    return _record_response(request, ctx, who, origin,
                            _record_by_request(ctx, origin, request_id, _now(ctx)))


async def cancel(request: web.Request) -> web.Response:
    ctx, who, origin = _initial(request)
    _rate(request, ctx, who, "controls_request_cancel", 20)
    if request.query_string:
        raise HmpError(ErrorCode.BAD_REQUEST)
    raw = await _body_bytes(request)
    try:
        body = wire.parse_body(raw, max_bytes=512, max_depth=8)
    except wire.WireError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    if body != {}:
        raise HmpError(ErrorCode.BAD_REQUEST)
    request_id = request.match_info.get("request_id", "")
    if _REQUEST_ID.fullmatch(request_id) is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    _current(request, ctx, who, origin)
    try:
        outcome = ControlsRequestStore(ctx.store).cancel_by_request_id(
            origin, request_id=request_id, now=_now(ctx), current_iid=ctx.iid
        )
    except ValueError:
        raise HmpError(ErrorCode.BAD_REQUEST) from None
    except Exception:
        raise _unavailable() from None
    if outcome.code not in ("cancelled", "ok"):
        _store_result(outcome.code)
    _current(request, ctx, who, origin)
    return _record_response(request, ctx, who, origin,
                            _record_by_request(ctx, origin, request_id, _now(ctx)))
