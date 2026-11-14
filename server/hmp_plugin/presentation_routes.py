"""Native presentation GET family, closed until actual startup binds readiness.

Helpers are bound once with this app's request context, including across plugin
reloads. No API/flag here grants rights, starts a provider or edits a profile.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from .contract import (
    PER_BOT_GATE_REFUSALS,
    RATE_READ_PER_MIN_PER_DEVICE_ID,
    AuthzState,
    ErrorCode,
    HmpError,
    RosterResponse,
)
from .presentation import HEX64, PROFILE
from .presentation_native_http import NativePresentationStreamAbortedError
from .presentation_native_service import (
    NativePresentationService,
    NativePresentationUnavailableError,
)
from .request_ctx import bearer, context, single_header

ROUTES = (
    ("GET", "/bots/{p}/presentation", "BI1"),
    ("GET", "/bots/{p}/presentation/avatar/{revision}", "BI1"),
)


def bound_service(ctx):
    try:
        service = ctx.presentation_service
        if (
            type(service) is NativePresentationService
            and service._ctx is ctx
            and ctx.presentation_available() is True
            and service.available is True
        ):
            return service
    except Exception:
        return None
    return None


def roster_capability(ctx, result):
    """Only this currently bound service owns its additive version declaration."""
    if type(result) is RosterResponse:
        capabilities = dict(result.capabilities or {})
        capabilities.pop("bot_presentation", None)
        if bound_service(ctx) is not None:
            capabilities["bot_presentation"] = 1
        return replace(result, capabilities=capabilities or None)
    if type(result) is dict:
        body = dict(result)
        capabilities = dict(body.get("capabilities") or {})
        capabilities.pop("bot_presentation", None)
        if bound_service(ctx) is not None:
            capabilities["bot_presentation"] = 1
        if capabilities:
            body["capabilities"] = capabilities
        else:
            body.pop("capabilities", None)
        return body
    return result


def _refusal(status):
    if status.startswith("bot_"):
        try:
            state = AuthzState(status[4:])
            refusal = PER_BOT_GATE_REFUSALS[state]
        except (ValueError, KeyError):
            return HmpError(ErrorCode.PRESENTATION_UNAVAILABLE)
        extras = {"authz": state.value}
        if refusal.why is not None:
            extras["why"] = refusal.why.value
        return HmpError(refusal.code, refusal.http, **extras)
    codes = {
        "bad_request": ErrorCode.BAD_REQUEST,
        "busy": ErrorCode.BUSY,
        "unauthenticated": ErrorCode.UNAUTHENTICATED,
        "revoked": ErrorCode.REVOKED,
        "wrong_instance": ErrorCode.WRONG_INSTANCE,
        "not_found": ErrorCode.NOT_FOUND,
    }
    return HmpError(codes.get(status, ErrorCode.PRESENTATION_UNAVAILABLE))


async def serve(request):
    who = bearer(request)  # original instance/token validation before diagnostics
    ctx = context(request)
    profile = request.match_info["p"]
    revision = request.match_info.get("revision")
    if (
        PROFILE.fullmatch(profile) is None
        or (revision is not None and HEX64.fullmatch(revision) is None)
        or request.query
        or request.headers.get("Transfer-Encoding") is not None
        or request.content_length not in (None, 0)
    ):
        raise HmpError(ErrorCode.BAD_REQUEST)
    ctx.limiter.check(
        "bots_presentation", who.device_id, RATE_READ_PER_MIN_PER_DEVICE_ID, ctx.now()
    )
    service = bound_service(ctx)
    if service is None:
        raise HmpError(ErrorCode.PRESENTATION_UNAVAILABLE)
    handle = None
    failure = None
    aborted = False
    try:
        handle = service.submit(
            single_header(request, "Authorization"),
            single_header(request, "HMP-Instance"),
            profile,
            kind="avatar" if revision is not None else "metadata",
            revision=revision,
        )
        status = await service.wait(handle)
        if status != "ready":
            failure = _refusal(status)
        else:
            return await service.emit(handle, request)
    except NativePresentationStreamAbortedError:
        aborted = True
    except NativePresentationUnavailableError as error:
        failure = _refusal(error.reason)
    finally:
        if handle is not None:
            service.abandon(handle)
    # Leave payload/native error contexts before public error shaping. A failed
    # prepare/write is NEVER converted by global middleware to a second body.
    if aborted:
        raise asyncio.CancelledError()
    raise failure or HmpError(ErrorCode.PRESENTATION_UNAVAILABLE)
