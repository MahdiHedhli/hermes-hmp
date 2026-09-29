"""aiohttp app for the HMP listener: TLS 1.3 only, bind and peer policy (TR-4), size and rate
limits (TR-6), ERR-1 error shaping, the ERR-2a refusal middleware, and the F1 route table only
(server-modules.md). F1's own write path (`SUB-1`) is not registered and answers 404 (FR-053).
T024. Amendment F2 (direct send, HMP_V1.md §7a) is the one exception: `POST .../chat/messages`
and its lookup route ARE always registered, answering `503 write_gate_closed` rather than `404`
when the owner-dogfood flag is off or the guard otherwise fails closed (server-modules.md).

Middleware order (outermost first):

1. `current_key` (PR7-6 step 1): every request first checks `identity.still_current()`. Once it
   is False the connection is aborted without a status (PR7-6 step 5) and the listener stops.
   A watchdog makes the same check every `WATCHDOG_INTERVAL_S`, and the TLS context refuses new
   handshakes, so the old key stops terminating TLS on the next tick or request.
2. `errors` (ERR-1): every error, including aiohttp's routing errors, becomes the fixed ERR-1
   body. An unmatched path or method is `404 not_found` (FR-053: the write paths share their
   prefixes with read routes, so a `405` would leak which methods exist). Anything unexpected is
   `500 other {why:"internal_error"}`, logged by exception type only (SEC-4).
3. `peer` (TR-4): peers outside loopback and the tailnet ranges get `403 forbidden
   {why:"peer_not_allowed"}`.
4. `limits` (TR-6): the request line plus headers over `MAX_HEADER_BYTES`, or a declared body over
   `MAX_BODY_BYTES`, gives `413 too_large`. aiohttp's own parser refuses a single line or field
   beyond `PARSER_LINE_LIMIT` (`MAX_HEADER_BYTES`) before any middleware runs, with its own
   `400`/`LineTooLong` fault; `_HmpRequestHandler.handle_error` (below) reshapes that too, into
   the same ERR-1 body (`413 too_large` for `LineTooLong`, `400 bad_request` otherwise) instead of
   aiohttp's default plain-text response, which otherwise echoes the offending bytes back to the
   caller (SEC-4). `HmpServer.start()` also passes a dedicated `logger=` (`_ParserSafeLogger`)
   into the `AppRunner`, so aiohttp's own internal logging of these faults — which otherwise
   includes the peer address and that same raw text via `exc_info` — never reaches the log either;
   it always emits exactly `event=http_parse_error outcome=bad_request`.
5. `compat` (ERR-2a): on an unsupported build every path except `/hmp/v1/ready` answers
   `503 other {why}` and nothing else runs, so no bridge call is possible.

Rate limits (TR-6) are applied inside the P2, P4 and P5 handlers, because the contract orders
them against the body checks and keys two of them on body fields.

Nothing here logs a request value. The aiohttp access log is `AllowListedAccessLogger`: method,
route template, status and duration only (SR-007, CS-22).
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import json
import logging
import ssl
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.http_exceptions import LineTooLong

from . import direct_send, mobile_cron, mobile_model, wire
from .contract import (
    CONTRACT_REVISION,
    HISTORY_LIMIT_DEFAULT,
    HISTORY_LIMIT_MAX,
    MAX_BODY_BYTES,
    MAX_HEADER_BYTES,
    PATH_PREFIX,
    RATE_AUTHORIZE_PER_MIN_PER_DEVICE_ID,
    RATE_READ_PER_MIN_PER_DEVICE_ID,
    RATE_SESSIONS_LIST_PER_MIN_PER_DEVICE_ID,
    READ_COMPAT_EXEMPT_PATH,
    READ_COMPAT_REFUSALS,
    SESSION_LIST_LIMIT_DEFAULT,
    SESSION_LIST_LIMIT_MAX,
    SESSIONS_CURSOR_MAX_BYTES,
    SNAPSHOT_LIMIT_DEFAULT,
    SNAPSHOT_LIMIT_MAX,
    SUPPORTED_VERSIONS,
    WATCHDOG_INTERVAL_S,
    DirectSendOutcome,
    DirectSendRequest,
    ErrorCode,
    HistoryReset,
    HmpError,
    OtherWhy,
    WriteGateState,
)
from .identity import set_ssl_context_attr
from .logging_policy import (
    LOGGER_NAME,
    AllowListedAccessLogger,
    log_bridge_exception,
    log_event,
    log_handler_exception,
)
from .pairing import handle_pair_complete, handle_pair_request
from .reads import require_bot_authorized

# `request_ctx` is the leaf module `ServerContext`/`CTX_KEY`/`context()`/the body and bearer
# helpers now live in (live-bug fix: a request-time `from .server import ...` in a separate
# module resolves against whatever a later plugin reload has put in `sys.modules`, not
# necessarily the load this app was built from -- see that module's docstring). `context`,
# `bearer`, `json_response`, `error_response`, `parse_peer_ip`, `ServerContext`, `ServingIdentity`
# and `CTX_KEY` are used directly below; `RateLimiter`, `peer_key` and `LOOPBACK_RATE_LIMIT_KEY`
# are used only by tests (`server.RateLimiter()`, `server.peer_key(...)`, ...) -- re-exported here
# (noqa: F401, deliberately) so those keep working unchanged.
from .request_ctx import (
    CTX_KEY,
    LOOPBACK_RATE_LIMIT_KEY,  # noqa: F401
    RateLimiter,  # noqa: F401
    ServerContext,
    ServingIdentity,
    bearer,
    context,
    error_response,
    json_response,
    parse_peer_ip,
    peer_key,  # noqa: F401
    read_json_body,
)
from .revoke import handle_self_revoke
from .tokens import handle_token

# The F1 route table (server-modules.md). Method, path under PATH_PREFIX, clause.
F1_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/ready", "PR0-1"),
    ("POST", "/pair/request", "PR2"),
    ("POST", "/pair/complete", "PR4"),
    ("POST", "/auth/token", "PR5"),
    ("POST", "/devices/self/revoke", "PR7-3"),
    ("GET", "/bots", "RO-1"),
    ("POST", "/bots/{p}/authorize", "PR6-1"),
    ("GET", "/bots/{p}/conversations/default", "RO-3"),
    ("GET", "/bots/{p}/conversations/default/messages", "RO-6"),
)

# Amendment A1 (session browsing, OD-F9/OD-F10): SES-1/SES-2. Registered separately from
# F1_ROUTES -- `build_app` adds these only when the kill switch (`ctx.session_browsing_enabled`)
# is on; when it is off they are never added to the router at all, so they 404 exactly like every
# other unregistered F1 write/SSE/intervention route.
A1_SESSION_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/bots/{p}/sessions", "SES-1"),
    ("GET", "/bots/{p}/sessions/{ref}/messages", "SES-2"),
)

# Amendment F2 (direct send, HMP_V1.md §7a): DS-1/DS-8. Unlike A1_SESSION_ROUTES, these are
# ALWAYS registered (server-modules.md's F1 route table note) -- the `direct_send_enabled` flag
# and the rest of DS-2(b)'s gate are re-checked per request, inside the handler, never by
# withholding route registration the way SES-1/SES-2's kill switch does.
F2_DIRECT_SEND_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("POST", "/bots/{p}/chat/messages", "DS-1"),
    ("GET", "/bots/{p}/chat/messages/by-client-id/{cmid}", "DS-8"),
)

MOBILE_CRON_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/bots/{p}/jobs", "CR-1"),
    ("POST", "/bots/{p}/jobs", "CR-2"),
    ("PATCH", "/bots/{p}/jobs/{job_id}", "CR-3"),
    ("DELETE", "/bots/{p}/jobs/{job_id}", "CR-4"),
    ("POST", "/bots/{p}/jobs/{job_id}/pause", "CR-5"),
    ("POST", "/bots/{p}/jobs/{job_id}/resume", "CR-6"),
)

MOBILE_MODEL_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/bots/{p}/model/default", "MD-1"),
    ("GET", "/bots/{p}/model/options", "MD-2"),
    ("PUT", "/bots/{p}/model/default", "MD-3"),
)

# aiohttp's parser limits for one request line or one header field (SEC-4: bounded at the same
# ceiling `limits_middleware` enforces on the total, not a looser one, so a single oversized field
# cannot make the raw parser buffer more than `MAX_HEADER_BYTES` before either it or
# `_HmpRequestHandler.handle_error` rejects the request).
PARSER_LINE_LIMIT = MAX_HEADER_BYTES
PARSER_MAX_HEADERS = 64

# Graceful shutdown bound. Direct-send background tasks are cancelled and awaited up to this
# same bound (`HmpServer.stop`); the HTTP runner uses it too.
SHUTDOWN_TIMEOUT_S = 2.0

ACCESS_LOGGER_NAME = LOGGER_NAME + ".access"
STORE_FILENAME = "hmp.sqlite3"

# TR-4: the only addresses the listener binds to and accepts peers from.
_TAILNET_V4 = ipaddress.IPv4Network("100.64.0.0/10")
_TAILNET_V6 = ipaddress.IPv6Network("fd7a:115c:a1e0::/48")


def full_path(route_path: str) -> str:
    return PATH_PREFIX + route_path


# --------------------------------------------------------------------------------------------------
# Bind and peer policy (TR-4)
# --------------------------------------------------------------------------------------------------


class ListenerConfigError(ValueError):
    """The listener settings violate TR-4. The listener does not start (fail closed)."""


def address_allowed(text: str | None) -> bool:
    """Loopback, `100.64.0.0/10` or `fd7a:115c:a1e0::/48` (TR-4). IPv4-mapped IPv6 is unwrapped;
    anything that is not an IP literal is refused (`parse_peer_ip`, `request_ctx.py`)."""
    addr = parse_peer_ip(text)
    if addr is None:
        return False
    if addr.is_loopback:
        return True
    if isinstance(addr, ipaddress.IPv4Address):
        return addr in _TAILNET_V4
    return addr in _TAILNET_V6


@dataclass(frozen=True)
class ListenerSettings:
    """Where the listener binds: `platforms.hmp.extra.{bind, port}` in the Hermes config."""

    bind: str
    port: int


DEFAULT_BIND = "127.0.0.1"


def listener_settings(extra: Mapping[str, Any] | None) -> ListenerSettings:
    """Validate the platform `extra` settings. `bind` defaults to loopback and must be an IP
    literal in the TR-4 set (no wildcard, no name); `port` is required, 1..65535."""
    extra = extra if isinstance(extra, Mapping) else {}
    bind = extra.get("bind", DEFAULT_BIND)
    if not isinstance(bind, str) or not address_allowed(bind):
        raise ListenerConfigError("bind must be a loopback or tailnet IP address (TR-4)")
    port = extra.get("port")
    if type(port) is not int or not 1 <= port <= 65_535:
        raise ListenerConfigError("port must be an integer in 1..65535")
    return ListenerSettings(bind=bind, port=port)


def store_path(anchor_dir: Path) -> Path:
    """The HMP store, next to the instance anchor in the default profile's plugin data."""
    return Path(anchor_dir).parent / STORE_FILENAME


# --------------------------------------------------------------------------------------------------
# Middlewares
# --------------------------------------------------------------------------------------------------

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


@web.middleware
async def current_key_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """PR7-6 step 1: never answer under a key that is no longer current (no status at all).

    A raising `still_current()` is treated exactly like `False` (fail closed), the same rule
    `_watchdog()` and `_guard_handshakes()` already apply: this middleware is outermost, wrapping
    `error_middleware`, so an exception here would otherwise escape this app's own ERR-1 shaping
    entirely and reach aiohttp's default 500 handling instead (SEC-4).
    """
    ctx = context(request)
    try:
        current = ctx.identity.still_current()
    except Exception:
        current = False
    if not current:
        if request.transport is not None:
            request.transport.abort()
        if ctx.on_identity_changed is not None:
            ctx.on_identity_changed()
        return web.Response(status=503)  # never written: the transport is gone
    return await handler(request)


@web.middleware
async def error_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """ERR-1 shaping for every error. Unmatched path or method → `404 not_found` (FR-053)."""
    try:
        return await handler(request)
    except HmpError as err:
        return error_response(err)
    except (web.HTTPNotFound, web.HTTPMethodNotAllowed):
        return error_response(HmpError(ErrorCode.NOT_FOUND))
    except web.HTTPRequestEntityTooLarge:
        return error_response(HmpError(ErrorCode.TOO_LARGE))
    except web.HTTPException as exc:
        if exc.status == 400:
            return error_response(HmpError(ErrorCode.BAD_REQUEST))
        log_event("http_exception", outcome="internal_error")
        return error_response(HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log_handler_exception(exc)  # type and code location only, never the text (SEC-4)
        return error_response(HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value))


@web.middleware
async def peer_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """TR-4: drop peers outside loopback and the tailnet ranges."""
    if not address_allowed(request.remote):
        raise HmpError(ErrorCode.FORBIDDEN, why=OtherWhy.PEER_NOT_ALLOWED.value)
    return await handler(request)


def header_bytes(request: web.Request) -> int:
    """Request line plus header block, as sent (TR-6 `MAX_HEADER_BYTES`)."""
    line = len(request.method) + len(request.raw_path) + 12  # " ", " HTTP/1.1\r\n"
    return line + sum(len(k) + len(v) + 4 for k, v in request.raw_headers)


@web.middleware
async def limits_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """TR-6: header and declared body size give `413 too_large`."""
    if header_bytes(request) > MAX_HEADER_BYTES:
        raise HmpError(ErrorCode.TOO_LARGE)
    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        raise HmpError(ErrorCode.TOO_LARGE)
    return await handler(request)


@web.middleware
async def compat_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    """ERR-2a: on an unsupported build, only `/hmp/v1/ready` is served (FR-044a)."""
    ctx = context(request)
    if not ctx.compat.supported and request.path != READ_COMPAT_EXEMPT_PATH:
        why = ctx.compat.why or OtherWhy.HERMES_BUILD_UNSUPPORTED
        refusal = READ_COMPAT_REFUSALS.get(why)
        if refusal is None:  # never expected; fail closed on the build-unsupported refusal
            refusal = READ_COMPAT_REFUSALS[OtherWhy.HERMES_BUILD_UNSUPPORTED]
        raise HmpError(refusal.code, refusal.http, why=refusal.why.value)
    return await handler(request)


async def _server_header(_request: web.Request, response: web.StreamResponse) -> None:
    # No version or host details on the wire (PR0-1).
    response.headers["Server"] = "hmp"


# --------------------------------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------------------------------


async def handle_ready(request: web.Request) -> web.Response:
    """PR0-1. Display and diagnostic only; no host details, no `install_id`."""
    ctx = context(request)
    return json_response(
        {
            "versions": list(SUPPORTED_VERSIONS),
            "contract": CONTRACT_REVISION,
            "iid": ctx.iid,
            "guarantees": ctx.guarantees(),
            "write_gate": ctx.reported_write_gate(),
        }
    )


def _query_int(request: web.Request, name: str, *, default: int | None, lo: int, hi: int) -> int:
    values = request.query.getall(name, [])
    if not values:
        if default is None:
            raise HmpError(ErrorCode.BAD_REQUEST)
        return default
    if len(values) != 1:
        raise HmpError(ErrorCode.BAD_REQUEST)
    text = values[0]
    if not text.isascii() or not text.isdigit() or (len(text) > 1 and text[0] == "0"):
        raise HmpError(ErrorCode.BAD_REQUEST)
    if len(text) > 16:
        raise HmpError(ErrorCode.BAD_REQUEST)
    value = int(text)
    if not lo <= value <= hi:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return value


def _query_str(request: web.Request, name: str, *, max_chars: int) -> str | None:
    """An optional single-valued string query param (A1 `cursor`). Absent -> `None`; repeated, or
    longer than `max_chars`, is `400 bad_request` (mirrors `_query_int`'s shape checks)."""
    values = request.query.getall(name, [])
    if not values:
        return None
    if len(values) != 1 or len(values[0]) > max_chars:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return values[0]


def _require(component: Any) -> Any:
    if component is None:  # a supported build always has it; fail closed otherwise
        raise HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value)
    return component


def _result_response(result: Any) -> web.Response:
    """A component result: `(status, body)`, or a body (dataclass or mapping) for `200`."""
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
        return json_response(result[1], status=result[0])
    if isinstance(result, HistoryReset):
        return json_response({"reset": result})
    return json_response(result)


async def handle_roster(request: web.Request) -> web.Response:
    who = bearer(request)
    ctx = context(request)
    ctx.limiter.check("bots_roster", who.device_id, RATE_READ_PER_MIN_PER_DEVICE_ID, ctx.now())
    reads = _require(ctx.reads)
    # SR-4: the bridge's authorization and SQLite reads are blocking (Hermes internals, and on
    # the first check per profile a secret-source hydration that can shell out). Running them
    # synchronously on the gateway's shared event loop would stall every other platform it
    # serves. `asyncio.to_thread` copies contextvars into the worker thread, so Hermes's own
    # profile secret-scope stays correct there too.
    result = await asyncio.to_thread(reads.roster, who.user_id)
    return _result_response(result)


async def handle_authorize(request: web.Request) -> web.Response:
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    ctx.limiter.check(
        "bots_authorize", who.device_id, RATE_AUTHORIZE_PER_MIN_PER_DEVICE_ID, ctx.now()
    )
    authorize = _require(ctx.authorize)
    # SR-4: captured here, on the real loop thread -- the only place `get_running_loop()` is
    # guaranteed correct -- and handed to the (now off-loop) call so its P6 hand-off can still
    # reach this loop (`bridge.request_authorization`'s `loop` parameter).
    loop = asyncio.get_running_loop()
    result = await asyncio.to_thread(authorize.authorize, who.user_id, profile, loop=loop)
    return _result_response(result)


async def handle_snapshot(request: web.Request) -> web.Response:
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    limit = _query_int(
        request, "limit", default=SNAPSHOT_LIMIT_DEFAULT, lo=1, hi=SNAPSHOT_LIMIT_MAX
    )
    ctx.limiter.check("bots_snapshot", who.device_id, RATE_READ_PER_MIN_PER_DEVICE_ID, ctx.now())
    reads = _require(ctx.reads)
    result = await asyncio.to_thread(reads.snapshot, who.user_id, profile, limit)
    return _result_response(result)


async def handle_history(request: web.Request) -> web.Response:
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    after = _query_int(request, "after", default=None, lo=0, hi=wire.IJSON_INT_MAX)
    limit = _query_int(request, "limit", default=HISTORY_LIMIT_DEFAULT, lo=1, hi=HISTORY_LIMIT_MAX)
    ctx.limiter.check("bots_history", who.device_id, RATE_READ_PER_MIN_PER_DEVICE_ID, ctx.now())
    reads = _require(ctx.reads)
    result = await asyncio.to_thread(reads.history, who.user_id, profile, after, limit)
    return _result_response(result)


async def handle_sessions_list(request: web.Request) -> web.Response:
    """Amendment A1, SES-1. Registered only when the kill switch is on (`build_app`)."""
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    limit = _query_int(
        request, "limit", default=SESSION_LIST_LIMIT_DEFAULT, lo=1, hi=SESSION_LIST_LIMIT_MAX
    )
    cursor = _query_str(request, "cursor", max_chars=SESSIONS_CURSOR_MAX_BYTES * 2)
    ctx.limiter.check(
        "bots_sessions_list", who.device_id, RATE_SESSIONS_LIST_PER_MIN_PER_DEVICE_ID, ctx.now()
    )
    reads = _require(ctx.reads)
    result = await asyncio.to_thread(
        reads.list_sessions, who.user_id, profile, cursor=cursor, limit=limit
    )
    return _result_response(result)


async def handle_session_messages(request: web.Request) -> web.Response:
    """Amendment A1, SES-2: a thin reparameterization of RO-6/RO-3 over an opaque `session_ref`
    instead of the mobile-own conversation. `after=0`, or no `after` at all, is the
    snapshot-equivalent branch; any other `after` is the paged branch (RO-6 shape, reset included).
    Registered only when the kill switch is on (`build_app`)."""
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    ref = request.match_info["ref"]
    after = _query_int(request, "after", default=0, lo=0, hi=wire.IJSON_INT_MAX)
    limit = _query_int(request, "limit", default=HISTORY_LIMIT_DEFAULT, lo=1, hi=HISTORY_LIMIT_MAX)
    ctx.limiter.check(
        "bots_session_messages", who.device_id, RATE_READ_PER_MIN_PER_DEVICE_ID, ctx.now()
    )
    reads = _require(ctx.reads)
    if after == 0:
        result: Any = await asyncio.to_thread(
            reads.session_snapshot, who.user_id, profile, ref, limit
        )
    else:
        result = await asyncio.to_thread(
            reads.session_history, who.user_id, profile, ref, after, limit
        )
    return _result_response(result)


_CMID_MAX_BYTES = 128  # generous bound for a UUIDv7 or any reasonable client-generated id
_TEXT_MAX_BYTES = MAX_BODY_BYTES  # the body-size limit is the real bound; no separate text cap


def _parse_direct_send_body(body: dict[str, Any]) -> DirectSendRequest:
    """DS-1's request shape. `expected_head` absent/`null` is accepted here (DS-1 itself is the
    one place that maps "no expected_head" to `400 bad_request`, via `direct_send.py`'s own
    check) -- this function only validates each field's own TYPE, not the cross-field DS-1 rule."""
    cmid = body.get("client_message_id")
    if not isinstance(cmid, str) or not cmid or len(cmid.encode("utf-8")) > _CMID_MAX_BYTES:
        raise HmpError(ErrorCode.BAD_REQUEST)
    expected_head = body.get("expected_head")
    if expected_head is not None and (
        not isinstance(expected_head, int)
        or isinstance(expected_head, bool)
        or not 0 <= expected_head <= wire.IJSON_INT_MAX
    ):
        raise HmpError(ErrorCode.BAD_REQUEST)
    text = body.get("text")
    if not isinstance(text, str) or not text:
        raise HmpError(ErrorCode.BAD_REQUEST)
    sent_at = body.get("sent_at")
    if sent_at is not None and (not isinstance(sent_at, int) or isinstance(sent_at, bool)):
        raise HmpError(ErrorCode.BAD_REQUEST)
    return DirectSendRequest(
        client_message_id=cmid, expected_head=expected_head, text=text, sent_at=sent_at
    )


def _direct_send_outcome_response(outcome: DirectSendOutcome, *, guarded: bool) -> web.Response:
    """DS-7's response body: `state`, plus whichever optional fields this outcome carries.
    `guarantee_level` appears only under the guarded gate, never alongside a full-guarantee
    accept (DS-2(b))."""
    body: dict[str, Any] = {"state": outcome.state}
    if outcome.message_id is not None:
        body["message_id"] = outcome.message_id
    if outcome.head_message_id is not None:
        body["head_message_id"] = outcome.head_message_id
    if guarded:
        body["guarantee_level"] = "guarded"
    if outcome.reply is not None:
        body["reply"] = outcome.reply
    if outcome.interleave_detected:
        body["interleave_detected"] = True
    if outcome.state == "unknown":
        # Same body DS-8 returns for this row (no live task / stored unknown).
        return json_response({"state": "unknown", "message_id": None})
    status = 200 if outcome.state == "accepted" else 202
    return json_response(body, status=status)


async def handle_chat_send(request: web.Request) -> web.Response:
    """DS-1..DS-7: `POST /bots/{p}/chat/messages`. Always registered (unlike SES-1/SES-2); the
    owner-dogfood flag and the rest of DS-2(b)'s gate are checked per request, inside
    `direct_send.handle_direct_send`, never by withholding registration."""
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    require_bot_authorized(_require(ctx.bridge), who.user_id, profile)
    body = await read_json_body(request)
    req = _parse_direct_send_body(body)
    base_gate = ctx.write_gate()
    deps = _require(ctx.direct_send_deps)
    try:
        outcome = await direct_send.handle_direct_send(
            deps,
            iid=ctx.iid,
            user_id=who.user_id,
            profile=profile,
            request=req,
            flag_enabled=ctx.direct_send_enabled(),
            base_write_gate=base_gate,
        )
    except direct_send.DirectSendError as exc:
        raise HmpError(exc.failure.code) from exc
    guarded = base_gate.state is not WriteGateState.OPEN
    return _direct_send_outcome_response(outcome, guarded=guarded)


async def _cron_endpoint(request: web.Request, *, write: bool) -> Any:
    """No job data or loopback call before device and profile authorization."""
    who = bearer(request)
    ctx = context(request)
    if not ctx.is_owner_device(who.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)
    ctx.limiter.check(
        "cron_write" if write else "cron_read", who.device_id,
        20 if write else 60, ctx.now(),
    )
    profile = request.match_info["p"]
    await asyncio.to_thread(require_bot_authorized, _require(ctx.bridge), who.user_id, profile)
    if not ctx.cron_enabled() or not ctx.cron_build_qualified():
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    endpoint = await asyncio.to_thread(ctx.bridge.direct_send_endpoint, profile)
    if endpoint is None:
        raise HmpError(ErrorCode.CRON_UNAVAILABLE)
    return endpoint


async def handle_cron_list(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=False)
    return json_response(await mobile_cron.call(endpoint, method="GET"))


async def handle_cron_create(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=True)
    body = mobile_cron.create_body(await read_json_body(request))
    return json_response(await mobile_cron.call(endpoint, method="POST", body=body))


async def handle_cron_edit(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=True)
    job_id = mobile_cron.job_id(request.match_info["job_id"])
    body = mobile_cron.edit_body(await read_json_body(request))
    return json_response(await mobile_cron.call(endpoint, method="PATCH", job=job_id, body=body))


async def handle_cron_delete(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=True)
    job_id = mobile_cron.job_id(request.match_info["job_id"])
    return json_response(await mobile_cron.call(endpoint, method="DELETE", job=job_id))


async def handle_cron_pause(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=True)
    job_id = mobile_cron.job_id(request.match_info["job_id"])
    result = await mobile_cron.call(endpoint, method="POST", job=job_id, action="pause")
    return json_response(result)


async def handle_cron_resume(request: web.Request) -> web.Response:
    endpoint = await _cron_endpoint(request, write=True)
    job_id = mobile_cron.job_id(request.match_info["job_id"])
    result = await mobile_cron.call(endpoint, method="POST", job=job_id, action="resume")
    return json_response(result)


async def _model_profile(request: web.Request, *, write: bool) -> str:
    """Reject before reading a body, profile config, or model catalog."""
    who = bearer(request)
    ctx = context(request)
    if not ctx.is_owner_device(who.device_id):
        raise HmpError(ErrorCode.NOT_FOUND)
    ctx.limiter.check(
        "model_write" if write else "model_read", who.device_id,
        10 if write else 30, ctx.now(),
    )
    profile = request.match_info["p"]
    await asyncio.to_thread(require_bot_authorized, _require(ctx.bridge), who.user_id, profile)
    if not ctx.model_enabled() or not ctx.model_build_qualified():
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    return profile


async def handle_model_current(request: web.Request) -> web.Response:
    profile = await _model_profile(request, write=False)
    try:
        bridge = _require(context(request).bridge)
        raw = await asyncio.to_thread(bridge.profile_default_model, profile)
    except Exception as exc:
        log_bridge_exception(exc)
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE) from exc
    return json_response(mobile_model.project_current(raw))


async def handle_model_options(request: web.Request) -> web.Response:
    profile = await _model_profile(request, write=False)
    try:
        bridge = _require(context(request).bridge)
        endpoint = await asyncio.to_thread(bridge.direct_send_endpoint, profile)
    except Exception as exc:
        log_bridge_exception(exc)
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE) from exc
    if endpoint is None:
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE)
    return json_response(await mobile_model.options(endpoint))


async def handle_model_update(request: web.Request) -> web.Response:
    profile = await _model_profile(request, write=True)
    provider, model = mobile_model.selection(await read_json_body(request))
    try:
        raw = await asyncio.to_thread(
            _require(context(request).bridge).set_profile_default_model, profile, provider, model
        )
    except Exception as exc:
        log_bridge_exception(exc)
        raise HmpError(ErrorCode.MODEL_UNAVAILABLE) from exc
    if raw is None:
        raise HmpError(ErrorCode.BAD_REQUEST)
    return json_response(mobile_model.project_current(raw))


# DS-7's own definitive-failure codes that mean "HMP's guard refused before Hermes ever saw this
# attempt" (or, for `write_gate_closed`/401, Hermes refused authentication before processing any
# content) -- DS-8's `not_accepted` vocabulary. Any OTHER rejected row (`api_server_unavailable`
# on a definitive non-200/202 status) means Hermes DID receive and answer the request with an
# error, which DS-8's `rejected` vocabulary is for instead.
_NOT_ACCEPTED_CODES = frozenset(
    {
        ErrorCode.NO_BOT_CHAT.value,
        ErrorCode.STALE_HEAD.value,
        ErrorCode.IDEMPOTENCY_CONFLICT.value,
        ErrorCode.WRITE_GATE_CLOSED.value,
    }
)


async def handle_chat_lookup(request: web.Request) -> web.Response:
    """DS-8: `GET /bots/{p}/chat/messages/by-client-id/{cmid}`. Read-only, never re-sends --
    reads this route's own idempotency store (DS-3), scoped to the caller's own `(iid, user_id,
    profile)`, exactly like SUB-7/SUB-8's lookup does for the original submit route.

    Review round 2, BLOCKER #1: a `pending` row's reported state now depends on whether THIS
    process still has a background task tracked for it (`direct_send.PendingSendTasks`) --
    `submitted` when it does (the send is still genuinely in flight here), `unknown` when it does
    not (the task already finished and was evicted a moment ago -- a race resolved by re-reading
    the row once more below -- or, durably, a gateway restart: a fresh process starts with an empty
    task registry by construction, so any row still `pending` from before a restart is reported
    `unknown`, never resent, per this round's own ruling: the client's next step is to check the
    Bot Chat itself, via SES-2, not keep polling this route).

    Review round 2, BLOCKER #4: `interleave_detected` is now surfaced here too, not only on the
    original `POST` response, for a caller that only ever reconciles through this route."""
    who = bearer(request)
    ctx = context(request)
    profile = request.match_info["p"]
    cmid = request.match_info["cmid"]
    require_bot_authorized(_require(ctx.bridge), who.user_id, profile)
    store = _require(ctx.store)
    record = await asyncio.to_thread(store.get_cmid_record, ctx.iid, who.user_id, profile, cmid)
    if record is None:
        return json_response({"state": "unknown", "message_id": None})
    status = record["status"]
    if status == "unknown":
        return json_response({"state": "unknown", "message_id": None})
    if status == "pending":
        deps = ctx.direct_send_deps
        key = (ctx.iid, who.user_id, profile, cmid)
        task = deps.tasks.get(key) if deps is not None else None
        if task is not None and not task.done():
            return json_response({"state": "submitted", "message_id": None})
        # Either no task was ever tracked here (a fresh process since a restart), or it just
        # finished a moment ago -- re-read once so a task that settled between the two checks
        # above is reported by its real, now-finalized outcome instead of a stale "unknown".
        record = await asyncio.to_thread(store.get_cmid_record, ctx.iid, who.user_id, profile, cmid)
        if record is None or record["status"] == "pending":
            return json_response({"state": "unknown", "message_id": None})
        status = record["status"]
    result_json = record["result_json"]
    if status == "rejected":
        code = _stored_rejection_code(result_json)
        state = "not_accepted" if code in _NOT_ACCEPTED_CODES else "rejected"
        return json_response({"state": state, "message_id": None})
    message_id = None
    interleave_detected = False
    state = "submitted"
    if result_json:
        data = json.loads(result_json)
        message_id = data.get("message_id")
        interleave_detected = bool(data.get("interleave_detected"))
        state = "queued" if data.get("state") == "queued" else "accepted"
    body: dict[str, Any] = {"state": state, "message_id": message_id}
    if interleave_detected:
        body["interleave_detected"] = True
    return json_response(body)


def _stored_rejection_code(result_json: str | None) -> str | None:
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
    except (TypeError, ValueError):
        return None
    code = data.get("code") if isinstance(data, dict) else None
    return code if isinstance(code, str) else None


def build_app(ctx: ServerContext) -> web.Application:
    """The HMP application: the middlewares above and the F1 route table, nothing else.

    `handle_pair_request`/`handle_pair_complete`/`handle_self_revoke`/`handle_token` are imported
    at module level now (top of this file), not here: a lazy import here only re-resolves
    `pairing`/`revoke`/`tokens` at the moment the LISTENER starts, which is exactly the moment a
    concurrent plugin reload (a multiplexed gateway loading another profile) may have already
    evicted and re-imported them under a different module object (see `request_ctx.py`'s
    docstring). Importing them at this module's own top level binds this app's route table to the
    same load as everything else it uses.
    """
    app = web.Application(
        middlewares=[
            current_key_middleware,
            error_middleware,
            peer_middleware,
            limits_middleware,
            compat_middleware,
        ],
        client_max_size=MAX_BODY_BYTES,
        handler_args={
            "max_line_size": PARSER_LINE_LIMIT,
            "max_field_size": PARSER_LINE_LIMIT,
            "max_headers": PARSER_MAX_HEADERS,
        },
    )
    app[CTX_KEY] = ctx
    app.on_response_prepare.append(_server_header)
    handlers: dict[str, Handler] = {
        "/ready": handle_ready,
        "/pair/request": handle_pair_request,
        "/pair/complete": handle_pair_complete,
        "/auth/token": handle_token,
        "/devices/self/revoke": handle_self_revoke,
        "/bots": handle_roster,
        "/bots/{p}/authorize": handle_authorize,
        "/bots/{p}/conversations/default": handle_snapshot,
        "/bots/{p}/conversations/default/messages": handle_history,
        # Amendment F2 (direct send): always registered (server-modules.md), unlike A1's kill
        # switch below -- the gate is re-checked per request, inside the handler.
        "/bots/{p}/chat/messages": handle_chat_send,
        "/bots/{p}/chat/messages/by-client-id/{cmid}": handle_chat_lookup,
        "/bots/{p}/jobs": handle_cron_list,
        "/bots/{p}/jobs/{job_id}": handle_cron_edit,
        "/bots/{p}/jobs/{job_id}/pause": handle_cron_pause,
        "/bots/{p}/jobs/{job_id}/resume": handle_cron_resume,
        "/bots/{p}/model/default": handle_model_current,
        "/bots/{p}/model/options": handle_model_options,
    }
    routes = (
        list(F1_ROUTES) + list(F2_DIRECT_SEND_ROUTES)
        + list(MOBILE_CRON_ROUTES) + list(MOBILE_MODEL_ROUTES)
    )
    if ctx.session_browsing_enabled:
        # Amendment A1 kill switch: when off, SES-1/SES-2 are never added to the router at all,
        # so they 404 exactly like every other unregistered F1 route (server-modules.md).
        handlers["/bots/{p}/sessions"] = handle_sessions_list
        handlers["/bots/{p}/sessions/{ref}/messages"] = handle_session_messages
        routes += list(A1_SESSION_ROUTES)
    for method, path, _clause in routes:
        handler = handlers[path]
        if path == "/bots/{p}/jobs" and method == "POST":
            handler = handle_cron_create
        elif path == "/bots/{p}/jobs/{job_id}" and method == "DELETE":
            handler = handle_cron_delete
        elif path == "/bots/{p}/model/default" and method == "PUT":
            handler = handle_model_update
        if method == "GET":
            app.router.add_get(full_path(path), handler, allow_head=False)
        else:
            app.router.add_route(method, full_path(path), handler)
    return app


# --------------------------------------------------------------------------------------------------
# The listener (TR-1, TR-4, PR7-6)
# --------------------------------------------------------------------------------------------------


def _guard_handshakes(
    ctx: ssl.SSLContext, identity: ServingIdentity, on_stale: Callable[[], None] | None
) -> None:
    """Refuse new TLS handshakes once the key is no longer current (PR7-6 step 1). A refused
    handshake is the "next request": it also triggers the listener shutdown."""

    def on_client_hello(_sock: Any, _name: str | None, _ctx: ssl.SSLContext) -> int | None:
        try:
            current = identity.still_current()
        except Exception:
            current = False
        if current:
            return None
        if on_stale is not None:
            with contextlib.suppress(Exception):
                on_stale()
        return ssl.ALERT_DESCRIPTION_HANDSHAKE_FAILURE

    ctx.sni_callback = on_client_hello


def server_ssl_context(
    identity: ServingIdentity, on_stale: Callable[[], None] | None = None
) -> ssl.SSLContext:
    """TLS 1.3 only, the instance certificate, no session tickets or early data.

    The context is the standard library's own class even under a host's process-wide
    client-trust injection, and its settings are written through the C-level descriptors
    (`set_ssl_context_attr`; see the note above `identity.new_stdlib_ssl_context`)."""
    ctx = identity.server_ssl_context()
    if (
        type(ctx).__module__ != "ssl"
        or ctx.minimum_version != ssl.TLSVersion.TLSv1_3
        or ctx.maximum_version != ssl.TLSVersion.TLSv1_3
    ):
        raise ListenerConfigError("the listener must be a stdlib TLS 1.3-only context (TR-1)")
    set_ssl_context_attr(ctx, "options", ctx.options | ssl.OP_NO_TICKET)
    with contextlib.suppress(AttributeError, ValueError):
        set_ssl_context_attr(ctx, "num_tickets", 0)
    _guard_handshakes(ctx, identity, on_stale)
    return ctx


# --------------------------------------------------------------------------------------------------
# Parser-level faults (SEC-4): a bad request line or header never reaches this app's own
# middlewares (they run only once aiohttp's own parser has accepted a syntactically valid HTTP
# message), so aiohttp's default handling — which logs the peer address plus the raw offending
# bytes via `exc_info`, and answers with a plain-text body built from that same exception message —
# has to be replaced independently of `error_middleware`, `_ParserSafeLogger`, `_HmpRequestHandler`
# and `_HmpServer`/`_HmpAppRunner` below do that; `HmpServer.start()` wires them in.
# --------------------------------------------------------------------------------------------------


class _ParserSafeLogger(logging.Logger):
    """The `logger=` `HmpServer.start()` passes to `AppRunner`, forwarded through `Server` to
    `RequestHandler` (aiohttp's own constructor parameter, not app code). aiohttp calls
    `self.logger.debug(...)` / `self.logger.exception(...)` on it internally — most notably from
    `handle_error()` (peer address as a `%s` arg, the raw exception as `exc_info`, which for a
    `LineTooLong` fault embeds the offending header/request-line bytes verbatim). This logger
    ignores whatever it is called with — message, args, `exc_info`, level — and always emits
    exactly the fixed, allow-listed line `event=http_parse_error outcome=bad_request`, the same
    shape `logging_policy.log_event` produces, so nothing aiohttp calls it with can ever reach the
    log (SEC-4). Overriding `_log` (every public logging method funnels through it) rather than
    only `debug`/`exception` also covers any log call a future aiohttp version might add here.
    """

    def __init__(self) -> None:
        super().__init__(LOGGER_NAME + ".transport", level=logging.DEBUG)

    def _log(self, *_args: Any, **_kwargs: Any) -> None:
        log_event("http_parse_error", outcome="bad_request")


class _HmpRequestHandler(web.RequestHandler):  # type: ignore[misc]
    """aiohttp's default `handle_error()` builds its response body from the exception message,
    which for a parser-level fault like `LineTooLong` echoes the offending request line or header
    straight back to the caller (SEC-4). This override keeps the base method's own bookkeeping —
    the "already sent, cannot send another response" guard, and its logging call, which now goes
    through the HMP-owned `_ParserSafeLogger` instead of aiohttp's own logger — and replaces only
    the body: `413 too_large` for `LineTooLong`, `400 bad_request` for any other non-500 fault
    (matching `error_middleware`'s own shaping for the same codes), and the existing
    `500 other {why: internal_error}` shape for a genuine internal error that reached this deep
    (one that escaped every middleware, e.g. `current_key_middleware` itself, before its own
    fail-closed handling above).

    A request that never reaches a parsed HTTP message also never reaches the app, so
    `_server_header` (`app.on_response_prepare`) never runs for it either: the `Server` header is
    set here too, for the same PR0-1 reason (no version or host details on the wire)."""

    def handle_error(
        self,
        request: web.BaseRequest,
        status: int = 500,
        exc: BaseException | None = None,
        message: str | None = None,
    ) -> web.StreamResponse:
        super().handle_error(request, status, exc, message)  # logging only; body is discarded
        if status == 500:
            err = HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value)
        else:
            code = ErrorCode.TOO_LARGE if isinstance(exc, LineTooLong) else ErrorCode.BAD_REQUEST
            err = HmpError(code)
        shaped = error_response(err)
        shaped.headers["Server"] = "hmp"
        shaped.force_close()
        return shaped


class _HmpServer(web.Server):  # type: ignore[misc]
    """Builds `_HmpRequestHandler` instead of aiohttp's default `RequestHandler` (SEC-4, see its
    docstring)."""

    def __call__(self) -> _HmpRequestHandler:
        return _HmpRequestHandler(self, loop=self._loop, **self._kwargs)


class _HmpAppRunner(web.AppRunner):  # type: ignore[misc]
    """Like `web.AppRunner`, but its `Server` is `_HmpServer`. Only the class of the `Server`
    instance `AppRunner._make_server()` already builds is changed (a same-layout, no-`__slots__`
    class swap): this does not re-implement any of that method's own setup/startup/freeze
    sequencing, so it tracks aiohttp's own behavior instead of duplicating it."""

    async def _make_server(self) -> web.Server:
        server = await super()._make_server()
        server.__class__ = _HmpServer
        return server


class HmpServer:
    """One TLS listener around one loaded identity (PR7-6: it never outlives its key)."""

    def __init__(
        self,
        ctx: ServerContext,
        settings: ListenerSettings,
        *,
        watchdog_interval: float = WATCHDOG_INTERVAL_S,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        self.ctx = ctx
        self.settings = settings
        self._interval = watchdog_interval
        self._on_closed = on_closed
        self._runner: web.AppRunner | None = None
        self._watch: asyncio.Task[None] | None = None
        self._stopping: asyncio.Task[None] | None = None
        self.bound: tuple[str, int] | None = None
        self.closed = asyncio.Event()
        ctx.on_identity_changed = self._identity_changed

    async def start(self) -> None:
        if not address_allowed(self.settings.bind):
            raise ListenerConfigError("bind must be a loopback or tailnet IP address (TR-4)")
        ssl_ctx = server_ssl_context(self.ctx.identity, self._identity_changed)
        app = build_app(self.ctx)
        runner = _HmpAppRunner(
            app,
            access_log_class=AllowListedAccessLogger,
            access_log=logging.getLogger(ACCESS_LOGGER_NAME),
            logger=_ParserSafeLogger(),
            shutdown_timeout=SHUTDOWN_TIMEOUT_S,
            handle_signals=False,
        )
        await runner.setup()
        site = web.TCPSite(
            runner, self.settings.bind, self.settings.port, ssl_context=ssl_ctx, reuse_address=True
        )
        try:
            await site.start()
        except BaseException:
            await runner.cleanup()
            raise
        self._runner = runner
        sockets = getattr(site._server, "sockets", None) or ()
        if sockets:
            host, port = sockets[0].getsockname()[:2]
            self.bound = (str(host), int(port))
        self._watch = asyncio.get_running_loop().create_task(self._watchdog())
        log_event("listener_start", outcome="ok")

    async def _watchdog(self) -> None:
        # PR7-6 polls on-disk custody by design; there is no event to wait on.
        while True:
            await asyncio.sleep(self._interval)
            try:
                current = self.ctx.identity.still_current()
            except Exception:
                current = False
            if not current:
                self._identity_changed()
                return

    def _identity_changed(self) -> None:
        if self._stopping is None:
            log_event("identity_changed", outcome="listener_closed")
            self._stopping = asyncio.get_running_loop().create_task(self.stop())

    async def _cancel_pending_sends(self) -> None:
        """Review round 3: cancel in-flight direct sends and wait, bounded, so a stop does not
        leave their tasks (and the profile lock they hold) running after the listener is gone."""
        deps = self.ctx.direct_send_deps
        tasks = getattr(deps, "tasks", None) if deps is not None else None
        cancel = getattr(tasks, "cancel_and_wait", None) if tasks is not None else None
        if cancel is None:
            return
        await cancel(SHUTDOWN_TIMEOUT_S)

    async def stop(self, *, notify: bool = True) -> None:
        """Close the listener. `notify=False` for an orderly shutdown by the owner."""
        await self._cancel_pending_sends()
        if not notify:
            self._on_closed = None
        watch, self._watch = self._watch, None
        if watch is not None and watch is not asyncio.current_task():
            watch.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watch
        runner, self._runner = self._runner, None
        if runner is not None:
            await runner.cleanup()
        if not self.closed.is_set():
            self.closed.set()
            if self._on_closed is not None:
                self._on_closed()
