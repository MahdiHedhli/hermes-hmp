"""AT1 authenticated projection/control. No ordinary prompt or native action alias."""

from __future__ import annotations

import re
from typing import Any

from aiohttp import web

from . import wire
from .approval_test_producer import TestControlReceipt
from .approval_test_service import TestCard
from .contract import MAX_HEADER_BYTES
from .request_ctx import bearer, context, single_header

INPUT_CAP = 256
OUTPUT_CAP = 1024
_ID = re.compile(r"[0-9a-f]{32}\Z")
ROUTES = (
    ("GET", "/approval-tests/current", "AT1-current"),
    ("GET", "/bots/{p}/approval-tests/current", "AT1-scoped-current"),
    ("POST", "/approval-tests/{phone_test_id}/answer", "AT1-answer"),
    ("POST", "/approval-tests/{phone_test_id}/cancel", "AT1-cancel"),
)


class _RouteError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def _response(body: dict[str, Any], status: int = 200) -> web.Response:
    raw = wire.dump_json(body)
    if len(raw) > OUTPUT_CAP:
        raw = b'{"v":1,"result":"unavailable"}'
        status = 503
    return web.Response(body=raw, status=status, content_type="application/json",
                        headers={"Cache-Control": "no-store"})


def _card(card: object) -> dict[str, Any] | None:
    if card is None:
        return None
    if (type(card) is not TestCard or type(card.test_id) is not str
            or _ID.fullmatch(card.test_id) is None
            or card.title != "Synthetic approval test"
            or card.message != "No action will run." or card.choices != ("once", "deny")):
        raise _RouteError(503, "unavailable")
    return {"test_id": card.test_id, "title": "Synthetic approval test",
            "message": "No action will run.", "choices": ["once", "deny"]}


def _service(ctx: Any) -> Any:
    try:
        return ctx.approval_test_service if ctx.approval_test_current() is True else None
    except Exception:
        return None


def _final(request: web.Request, who: Any, service: Any) -> bool:
    # Reauthentication can raise the ordinary authentication failure. It never
    # turns a revoked family into a successful empty projection.
    ctx = context(request)
    try:
        identity_current = ctx.identity.still_current() is True
    except Exception:
        identity_current = False
    if not identity_current:
        if request.transport is not None:
            request.transport.abort()
        if ctx.on_identity_changed is not None:
            ctx.on_identity_changed()
        raise _RouteError(503, "unavailable")
    if service is None:
        return False
    if bearer(request) != who:
        return False
    return service is not None and _service(context(request)) is service


async def _body(request: web.Request, *, answer: bool) -> dict[str, Any]:
    if request.query_string or "?" in request.raw_path:
        raise _RouteError(400, "bad_request")
    if (request.headers.getall("Transfer-Encoding", [])
            or request.headers.getall("Content-Encoding", [])
            or single_header(request, "Content-Type") != "application/json"):
        raise _RouteError(400, "bad_request")
    length = single_header(request, "Content-Length")
    if length is None or not length or not length.isascii() or not length.isdecimal():
        raise _RouteError(400, "bad_request")
    # Header syntax has its own bound; leading zeroes do not increase body size.
    if len(length) > MAX_HEADER_BYTES:
        raise _RouteError(400, "bad_request")
    significant = length.lstrip("0") or "0"
    if len(significant) > 3 or int(significant) > INPUT_CAP:
        raise _RouteError(413, "too_large")
    declared = int(significant)
    raw = bytearray()
    async for chunk in request.content.iter_chunked(INPUT_CAP + 1):
        raw.extend(chunk)
        if len(raw) > INPUT_CAP:
            raise _RouteError(413, "too_large")
    if len(raw) != declared:
        raise _RouteError(400, "bad_request")
    try:
        body = wire.parse_body(bytes(raw), max_bytes=INPUT_CAP, max_depth=4)
    except wire.WireError:
        raise _RouteError(400, "bad_request") from None
    keys = {"v", "choice"} if answer else {"v"}
    if (set(body) != keys or type(body.get("v")) is not int or body["v"] != 1
            or (answer and (type(body.get("choice")) is not str
                            or body["choice"] not in {"once", "deny"}))):
        raise _RouteError(400, "bad_request")
    return body


async def _current(request: web.Request, profile: str | None) -> web.Response:
    who = bearer(request)  # Ordinary authentication precedes AT1 parsing/lookup.
    try:
        if (request.query_string or "?" in request.raw_path
                or request.headers.getall("Transfer-Encoding", [])
                or request.headers.getall("Content-Encoding", [])
                or request.can_read_body):
            raise _RouteError(400, "bad_request")
        lengths = request.headers.getall("Content-Length", [])
        if lengths and lengths != ["0"]:
            raise _RouteError(400, "bad_request")
        service = _service(context(request))
        try:
            card = (await service.phone_card(request, profile=profile)
                    if service is not None else None)
        except Exception:
            raise _RouteError(503, "unavailable") from None
        current = _final(request, who, service)
        return _response({"v": 1, "card": _card(card) if current else None})
    except _RouteError as refusal:
        return _response({"v": 1, "result": refusal.code}, refusal.status)


async def _control(request: web.Request, *, answer: bool) -> web.Response:
    who = bearer(request)
    try:
        body = await _body(request, answer=answer)
        phone_id = request.match_info["phone_test_id"]
        if _ID.fullmatch(phone_id) is None:
            raise _RouteError(404, "unavailable")
        service = _service(context(request))
        if service is None:
            raise _RouteError(404, "unavailable")
        try:
            receipt = (await service.phone_answer(request, phone_id, body["choice"])
                       if answer else await service.phone_cancel(request, phone_id))
        except Exception:
            raise _RouteError(503, "unavailable") from None
        if (not _final(request, who, service) or type(receipt) is not TestControlReceipt
                or receipt.admission != "accepted"):
            raise _RouteError(404, "unavailable")
        return _response({"v": 1, "result": "accepted"}, 202)
    except _RouteError as refusal:
        return _response({"v": 1, "result": refusal.code}, refusal.status)


async def handle_answer(request: web.Request) -> web.Response:
    return await _control(request, answer=True)


async def handle_cancel(request: web.Request) -> web.Response:
    return await _control(request, answer=False)


async def handle_current(request: web.Request) -> web.Response:
    """Standalone DATA projection; it does not bind per-profile UI authority."""
    return await _current(request, None)


async def handle_scoped_current(request: web.Request) -> web.Response:
    """Canonical path profile goes through the full service authority gate.

    No ordinary/Desktop observation or other suspension follows phone_card's
    last authority await: final live identity/bearer/service checks and encoding
    execute in that same loop turn. A body/query field cannot select a profile.
    """
    return await _current(request, request.match_info["p"])
