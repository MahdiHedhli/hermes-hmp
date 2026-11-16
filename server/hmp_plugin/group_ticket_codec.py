"""Unactivated local control-ticket codec; not peer/native/phone authorization.

Callers must establish the original adapter-owned native binding and authenticate
its same-user socket before using a reply. This module performs no I/O, mint,
retry, endpoint discovery, gateway start, permission or credential forwarding.
The separate actual transport must bound bytes BEFORE acquiring this input.
"""

from __future__ import annotations

import json
import math
from contextlib import suppress
from dataclasses import dataclass

_MAX_BODY_BYTES = 65_536
_MAX_FIELDS = 8
_TICKET_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


class GroupTicketCodecRefusalError(ValueError):
    """Content-free refusal: never includes a raw response or native diagnostic."""

    def __init__(self) -> None:
        super().__init__("Native group ticket reply unavailable.")


@dataclass(frozen=True, slots=True, repr=False)
class NativeGroupTicketGrant:
    """Sensitive internal DATA only; repr suppression is logging hygiene, not secrecy.

    Neither this constructible value nor its TTL observation proves an authenticated
    peer, native admission, phone rights or lifetime of a connected WebSocket.
    """

    ticket: str
    expires_in_seconds: int


def _text(value: object, maximum: int) -> bool:
    if type(value) is not str or not 1 <= len(value) <= maximum or "\x00" in value:
        return False
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        return False
    return size <= maximum


def _bindings(profile_id: object, instance_id: object) -> None:
    if not _text(profile_id, 4096) or not _text(instance_id, 256):
        raise GroupTicketCodecRefusalError()


def build_group_ticket_request(*, profile_id: str, instance_id: str) -> bytes:
    """Fixed endpoint-only native envelope; no subject/host scope/policy fallback."""
    _bindings(profile_id, instance_id)
    message = {
        "protocol": 1,
        "id": 1,
        "verb": "session-ticket",
        "params": {
            "profile_id": profile_id,
            "instance_id": instance_id,
            "purpose": "interactive",
            "scope": "profile",
            "restart_wait": "refuse",
        },
    }
    raw = json.dumps(message, ensure_ascii=True).encode("ascii")
    if len(raw) > _MAX_BODY_BYTES:
        raise GroupTicketCodecRefusalError()
    return raw + b"\n"


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    if len(pairs) > _MAX_FIELDS:
        raise ValueError("invalid control object")
    result = {}
    for key, value in pairs:
        if not _text(key, 64) or key in result:
            raise ValueError("invalid control object")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise ValueError("invalid control number")


def _scalar(value: object) -> bool:
    if value is None or type(value) is bool:
        return True
    if type(value) is int:
        return -(1 << 63) <= value < (1 << 63)
    if type(value) is float:
        return math.isfinite(value)
    return (type(value) is str and value == "") or _text(value, 256)


def _extras(mapping: dict, required: frozenset[str]) -> bool:
    return required <= mapping.keys() and all(
        _scalar(value) for key, value in mapping.items() if key not in required
    )


def parse_group_ticket_reply(
    raw: bytes, *, profile_id: str, instance_id: str
) -> NativeGroupTicketGrant:
    """Bounded closed projection of a single LF-terminated successful reply.

    Supports bounded scalar additions, never arbitrary nested metadata. Parsing
    working memory is bounded by input/shape, not claimed an exact heap/RSS cap.
    No exception message, cause or returned DATA includes raw remote diagnostics.
    Ordinary Python call stacks/strings are not claimed to be securely zeroized.
    """
    _bindings(profile_id, instance_id)
    if (
        type(raw) is not bytes
        or not 1 < len(raw) <= _MAX_BODY_BYTES + 1
        or not raw.endswith(b"\n")
        or raw.count(b"\n") != 1
        or raw.endswith(b"\r\n")
    ):
        raise GroupTicketCodecRefusalError()
    parsed = None
    with suppress(ValueError, UnicodeError, RecursionError, OverflowError):
        parsed = json.loads(
            raw[:-1].decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    # Outside the decoder's exception handler: do not chain its raw JSON error.
    if type(parsed) is not dict or not _extras(
        parsed, frozenset({"protocol", "id", "ok", "result"})
    ):
        raise GroupTicketCodecRefusalError()
    if (
        type(parsed["protocol"]) is not int
        or parsed["protocol"] != 1
        or type(parsed["id"]) is not int
        or parsed["id"] != 1
        or parsed["ok"] is not True
    ):
        raise GroupTicketCodecRefusalError()
    result = parsed["result"]
    if type(result) is not dict or not _extras(
        result,
        frozenset(
            {"ticket", "expires_in_seconds", "instance_id", "profile_id", "runtime_protocol"}
        ),
    ):
        raise GroupTicketCodecRefusalError()
    if (
        type(result["runtime_protocol"]) is not int
        or result["runtime_protocol"] != 1
        or type(result["profile_id"]) is not str
        or result["profile_id"] != profile_id
        or type(result["instance_id"]) is not str
        or result["instance_id"] != instance_id
        or type(result["expires_in_seconds"]) is not int
        or not 1 <= result["expires_in_seconds"] <= (1 << 31) - 1
        or type(result["ticket"]) is not str
        or not 1 <= len(result["ticket"]) <= 256
        or any(char not in _TICKET_CHARS for char in result["ticket"])
    ):
        raise GroupTicketCodecRefusalError()
    return NativeGroupTicketGrant(result["ticket"], result["expires_in_seconds"])
