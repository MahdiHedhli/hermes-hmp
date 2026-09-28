"""Allow-listed log fields (SEC-4, SR-007). HMP never logs `S` or the `hmp1:` payload, pairing
nonces (`nd`/`ni`), tokens, signatures, private keys, `Authorization` headers, SAS values, Hermes
pairing codes, device names, operator labels, peer addresses or message text. Only 8-character id
prefixes and outcome codes are logged. Implementation: T033.

This is the plugin's only logging entry point (`log_event`): every other module that wants to log
something calls it, never `logging.getLogger(...)` directly, so nothing bypasses the allow-list.
`event` and `outcome` are restricted to short, fixed-shape codes (never a caller-supplied value
that could carry secret or free-text content), and every `**ids` value is truncated to its first
`ID_PREFIX_LEN` characters before it reaches the logger — so even a caller mistake (passing a raw
secret where an id belongs) can leak at most 8 characters of it, matching this file's own limit.

Also provides `AllowListedAccessLogger`, the aiohttp access logger `server.py` (T024) wires in:
reduced to method, route template, status and duration, never the query string or any header (so
never the bearer token), and never the concrete path (which could carry an id).
"""

from __future__ import annotations

import logging
import re
import traceback

ID_PREFIX_LEN = 8

LOGGER_NAME = "hmp_plugin"

# `event` and `outcome` are code-like identifiers, never free text: this is what stops an
# accidental secret or message fragment from riding in as one of these two required fields.
_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")

_logger = logging.getLogger(LOGGER_NAME)


def id_prefix(value: str) -> str:
    """The first `ID_PREFIX_LEN` characters of an id-shaped string (SEC-4). Raises if `value`
    is not a string of at least that length — a short value is not an id this policy accepts,
    and silently zero-padding it would misrepresent what was actually logged."""
    if not isinstance(value, str):
        raise TypeError(f"id_prefix() requires a string, got {type(value).__name__}")
    if len(value) < ID_PREFIX_LEN:
        raise ValueError(f"id_prefix() requires at least {ID_PREFIX_LEN} characters")
    return value[:ID_PREFIX_LEN]


def _require_code(name: str, value: str) -> str:
    if not isinstance(value, str) or _CODE_RE.fullmatch(value) is None:
        raise ValueError(
            f"{name} must be a lowercase code matching {_CODE_RE.pattern!r}, got {value!r}"
        )
    return value


def log_event(event: str, *, outcome: str, **ids: str) -> None:
    """The one way any HMP module logs anything (SEC-4). `event` and `outcome` must be short
    lowercase codes; every keyword in `ids` is logged only as its `id_prefix()` (never the raw
    value), labelled by its keyword name (e.g. `log_event("token_refresh", outcome="revoked",
    device_id=device_id)`)."""
    _require_code("event", event)
    _require_code("outcome", outcome)
    fields = " ".join(f"{name}={id_prefix(value)}" for name, value in sorted(ids.items()))
    if fields:
        _logger.info("event=%s outcome=%s %s", event, outcome, fields)
    else:
        _logger.info("event=%s outcome=%s", event, outcome)


def log_bridge_exception(exc: BaseException) -> None:
    """Bridge exceptions are logged by type only (server-modules.md `logging_policy.py`): never
    the exception message, which could quote Hermes-side data."""
    _logger.warning("event=bridge_exception outcome=error exception_type=%s", type(exc).__name__)


_CODE_TOKEN = re.compile(r"[^A-Za-z0-9_.<>-]")


def _frame_label(filename: str, function: str, lineno: int | None) -> str:
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    safe_base, safe_fn = _CODE_TOKEN.sub("_", base), _CODE_TOKEN.sub("_", function)
    return f"{safe_base}:{safe_fn}:{lineno or 0}"


def _in_plugin(filename: str) -> bool:
    path = filename.replace("\\", "/")
    return "/hmp_plugin/" in path or "/plugins/hmp/" in path


def log_handler_exception(exc: BaseException) -> None:
    """An unexpected route-handler exception, logged as code metadata only (SEC-4): the exception
    type, the innermost frame inside this package, and the innermost frame overall -- each as
    `file-basename:function:line`. Never the exception message, never a full path, never locals."""
    frames = traceback.extract_tb(exc.__traceback__)
    inside = [f for f in frames if _in_plugin(f.filename)]
    at = _frame_label(inside[-1].filename, inside[-1].name, inside[-1].lineno) if inside else "-"
    last = _frame_label(frames[-1].filename, frames[-1].name, frames[-1].lineno) if frames else "-"
    _logger.warning(
        "event=handler_error outcome=internal_error exception_type=%s at=%s last=%s",
        _CODE_TOKEN.sub("_", type(exc).__name__),
        at,
        last,
    )


# ------------------------------------------------------------------------------------------------
# aiohttp access log (SR-007 "Server"): disabled or reduced to method, route template, status and
# duration. `server.py` (T024) passes this class as `AppRunner`/`web.run_app`'s `access_log_class`.
# ------------------------------------------------------------------------------------------------

try:
    from aiohttp.abc import AbstractAccessLogger as _AbstractAccessLogger
except ImportError:  # pragma: no cover - aiohttp is a declared runtime dependency (pyproject.toml)
    _AbstractAccessLogger = object  # type: ignore[assignment,misc]


_ALLOWED_ACCESS_LOG_METHODS = frozenset({"GET", "POST", "HEAD"})


class AllowListedAccessLogger(_AbstractAccessLogger):  # type: ignore[misc]
    """Logs only `<method> <route template> <status> <duration>s`. Never the query string (which
    the peer controls and which could carry an accidental secret), never any request or response
    header (so never `Authorization: Bearer ...`), and never the concrete path — only its route
    *template*, e.g. `/hmp/v1/bots/{p}/authorize`, not the profile it was called with.

    `method` is allow-listed too, not passed through raw: HTTP method is an open-ended token, not
    an enum, so an arbitrary request line (`FOOBAR /hmp/v1/ready HTTP/1.1`) would otherwise let
    the peer write free text of its choosing into this log (SEC-4) — the same reason `log_event`
    restricts `event`/`outcome` to fixed, code-shaped values. F1 only ever expects `GET`/`POST`
    (`HEAD` is included as the one other method HTTP defines a standard meaning for); anything
    else is logged as the fixed token `OTHER`.

    `log_format` is accepted (aiohttp's `AbstractAccessLogger.__init__` requires it, and
    `web.run_app`/`AccessLogger` machinery always passes one) but is never used: this logger's
    output shape is fixed by the allow-list, not configurable by a format string that could be
    set to include a disallowed field.
    """

    def __init__(self, logger: logging.Logger, log_format: str = "") -> None:
        super().__init__(logger, log_format)

    def log(self, request: object, response: object, time: float) -> None:
        method = getattr(request, "method", "-")
        if method not in _ALLOWED_ACCESS_LOG_METHODS:
            method = "OTHER"
        route_template = _route_template(request)
        status = getattr(response, "status", "-")
        self.logger.info("%s %s %s %.3f", method, route_template, status, time)


def _route_template(request: object) -> str:
    match_info = getattr(request, "match_info", None)
    route = getattr(match_info, "route", None)
    resource = getattr(route, "resource", None)
    canonical = getattr(resource, "canonical", None)
    return canonical if isinstance(canonical, str) else "-"
