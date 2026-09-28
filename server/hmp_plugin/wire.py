"""Wire encoding: I-JSON (TR-9), integer typing (TR-10), canonical base64url (TR-11), size and
depth limits (TR-6, §13), and the `hmp1:` QR payload (PR1-3, PR1-5; CS-10 endpoint grammar).

Everything here is pure and side-effect free. A malformed value raises `WireError` (maps to
`400 bad_request`, or the route's uniform failure). An exceeded body or depth limit raises
`TooLargeError` (maps to `413 too_large`). Error messages name the field and the rule only; they
never echo the offending value, so they are safe to log under SEC-4.
"""

from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import re
import unicodedata
from typing import Any

from .contract import (
    CLOCK_SKEW_S,
    MAX_BODY_BYTES,
    MAX_JSON_DEPTH,
    PROTOCOL_VERSION,
    QR_PREFIX,
    QrOffer,
)

# TR-11 exact decoded lengths, by field.
B64U_DECODED_LENGTHS: dict[str, int] = {
    "oid": 16,
    "s": 32,
    "nd": 32,
    "ni": 32,
    "nonce": 16,
    "token": 32,
    "pairing_id": 16,
    "device_pub": 91,
}

# I-JSON (RFC 7493 §2.2): integers outside +-(2**53 - 1) are not interoperable.
IJSON_INT_MAX = 2**53 - 1

# A DER ECDSA P-256 signature is at most 72 bytes (TR-13).
MAX_SIGNATURE_BYTES = 72

# An `hmp1:` QR payload is bounded well above any valid offer.
MAX_QR_PAYLOAD_CHARS = 2_048

_B64U_ALPHABET = re.compile(r"[A-Za-z0-9_-]*")
_IID_ALPHABET = re.compile(r"[a-z2-7]{52}")


class WireError(ValueError):
    """A malformed request value. Maps to `400 bad_request` (or the route's uniform failure)."""


class TooLargeError(WireError):
    """A body, header or depth limit was exceeded. Maps to `413 too_large`."""


# --------------------------------------------------------------------------------------------------
# I-JSON (TR-9)
# --------------------------------------------------------------------------------------------------


def _check_depth(text: str, max_depth: int) -> None:
    """Reject nesting deeper than `max_depth` before the JSON parser recurses into it.

    The top-level object is depth 1. Brackets inside strings are skipped.
    """
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > max_depth:
                raise TooLargeError("json depth exceeds the limit")
        elif ch in "]}":
            depth -= 1


def _reject_constant(name: str) -> Any:
    raise WireError("non-finite number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise WireError("duplicate object member name")
        obj[key] = value
    return obj


def _has_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def _check_strings(value: Any) -> None:
    """No lone surrogates anywhere, in names or values (I-JSON §2.1)."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            if _has_surrogate(item):
                raise WireError("string contains a surrogate code point")
        elif isinstance(item, dict):
            for key, member in item.items():
                if _has_surrogate(key):
                    raise WireError("member name contains a surrogate code point")
                stack.append(member)
        elif isinstance(item, list):
            stack.extend(item)


def parse_ijson(
    raw: bytes, *, max_bytes: int = MAX_BODY_BYTES, max_depth: int = MAX_JSON_DEPTH
) -> Any:
    """Parse I-JSON (RFC 7493) bytes of any top-level type (TR-9, TR-6)."""
    if not isinstance(raw, bytes | bytearray):
        raise WireError("body is not bytes")
    if len(raw) > max_bytes:
        raise TooLargeError("body exceeds the limit")
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WireError("body is not well-formed UTF-8") from exc
    _check_depth(text, max_depth)
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except WireError:
        raise
    except (ValueError, RecursionError) as exc:
        raise WireError("body is not valid JSON") from exc
    _check_strings(value)
    return value


def parse_body(
    raw: bytes, *, max_bytes: int = MAX_BODY_BYTES, max_depth: int = MAX_JSON_DEPTH
) -> dict[str, Any]:
    """Parse an I-JSON request body whose top level is an object (TR-9)."""
    value = parse_ijson(raw, max_bytes=max_bytes, max_depth=max_depth)
    if not isinstance(value, dict):
        raise WireError("top level is not an object")
    return value


def dump_json(value: Any) -> bytes:
    """Serialize a response body: compact UTF-8, finite numbers only."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode(
        "utf-8"
    )


# --------------------------------------------------------------------------------------------------
# Typed fields (TR-10)
# --------------------------------------------------------------------------------------------------


def require_int(value: Any, *, minimum: int | None = None, maximum: int | None = None) -> int:
    """A genuine JSON integer; booleans and floats are rejected (TR-10).

    The value must also sit inside the I-JSON interoperable range (RFC 7493 §2.2).
    """
    if type(value) is not int:  # bool is a subclass of int: excluded on purpose
        raise WireError("expected an integer")
    if not -IJSON_INT_MAX <= value <= IJSON_INT_MAX:
        raise WireError("integer outside the interoperable range")
    if minimum is not None and value < minimum:
        raise WireError("integer below the minimum")
    if maximum is not None and value > maximum:
        raise WireError("integer above the maximum")
    return value


def require_str(value: Any) -> str:
    if not isinstance(value, str):
        raise WireError("expected a string")
    return value


def require_member(body: dict[str, Any], name: str) -> Any:
    if name not in body:
        raise WireError(f"missing member {name!r}")
    return body[name]


# --------------------------------------------------------------------------------------------------
# Canonical base64url (TR-11)
# --------------------------------------------------------------------------------------------------


def b64u_encode(data: bytes) -> str:
    """Unpadded RFC 4648 §5 base64url."""
    return base64.urlsafe_b64encode(bytes(data)).rstrip(b"=").decode("ascii")


def _b64u_decode_canonical(text: Any) -> bytes:
    if not isinstance(text, str):
        raise WireError("base64url value is not a string")
    if _B64U_ALPHABET.fullmatch(text) is None:  # also rejects '=' padding and whitespace
        raise WireError("base64url value has a character outside the unpadded alphabet")
    if len(text) % 4 == 1:
        raise WireError("base64url value has an impossible length")
    try:
        data = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise WireError("base64url value does not decode") from exc
    # Round-trip exactness: rejects non-zero unused trailing bits (TR-11).
    if b64u_encode(data) != text:
        raise WireError("base64url value is not canonical")
    return data


def b64u_decode(text: str, *, length: int) -> bytes:
    """Canonical, unpadded base64url with an exact decoded length (TR-11)."""
    data = _b64u_decode_canonical(text)
    if len(data) != length:
        raise WireError("base64url value has the wrong decoded length")
    return data


def b64u_decode_bounded(text: str, *, max_length: int) -> bytes:
    """Canonical, unpadded base64url of variable length (signatures): 1..`max_length` bytes."""
    if isinstance(text, str) and len(text) > (max_length * 4 + 2) // 3:
        raise WireError("base64url value is too long")
    data = _b64u_decode_canonical(text)
    if not 1 <= len(data) <= max_length:
        raise WireError("base64url value has the wrong decoded length")
    return data


def b64u_field(field: str, text: Any) -> bytes:
    """Decode a named TR-11 field at its exact length (`B64U_DECODED_LENGTHS`)."""
    return b64u_decode(text, length=B64U_DECODED_LENGTHS[field])


def b64u_signature(text: Any) -> bytes:
    """Decode a `sig` / `isig` field: canonical b64u of a DER signature (TR-13)."""
    return b64u_decode_bounded(text, max_length=MAX_SIGNATURE_BYTES)


# --------------------------------------------------------------------------------------------------
# Host/Hermes-controlled display text (PR2-3-style neutralization; A1 amendment §2 SES-1b)
# --------------------------------------------------------------------------------------------------

# The same Unicode general categories `pairing.sanitize_device_name` drops (PR2-3): control,
# format, line/paragraph separators, private-use and unassigned code points.
_DROPPED_TEXT_CATEGORIES: frozenset[str] = frozenset({"Cc", "Cf", "Zl", "Zp", "Co", "Cn"})


def neutralize_text(value: str, *, max_bytes: int) -> str:
    """Host- or Hermes-controlled text made safe to display: never trusted markup (`title`/
    `source` can be model-generated or operator-set text, A1 §2 SES-1b). Drops the categories
    above, applies NFC, then truncates to `max_bytes` UTF-8 bytes without splitting a code point.
    An empty or all-dropped input becomes `""`; the caller decides the placeholder, if any -- this
    function never invents one (unlike `sanitize_device_name`, nothing here is stored as an
    identity artifact, so there is no "must not be empty" rule to enforce)."""
    kept = "".join(ch for ch in value if unicodedata.category(ch) not in _DROPPED_TEXT_CATEGORIES)
    text = unicodedata.normalize("NFC", kept)
    out: list[str] = []
    size = 0
    for ch in text:
        n = len(ch.encode("utf-8"))
        if size + n > max_bytes:
            break
        out.append(ch)
        size += n
    return "".join(out)


# --------------------------------------------------------------------------------------------------
# Identifiers (§2)
# --------------------------------------------------------------------------------------------------


def require_iid(text: Any) -> str:
    """`iid` / `device_fp`: 52 chars of lowercase, unpadded, canonical base32 of 32 bytes (§2)."""
    if not isinstance(text, str) or _IID_ALPHABET.fullmatch(text) is None:
        raise WireError("malformed instance or device fingerprint")
    raw = base64.b32decode(text.upper() + "====")
    if len(raw) != 32 or base64.b32encode(raw).decode("ascii").rstrip("=").lower() != text:
        raise WireError("malformed instance or device fingerprint")
    return text


# --------------------------------------------------------------------------------------------------
# Endpoints (PR1-3, PR1-5; CS-10 / FR-002)
# --------------------------------------------------------------------------------------------------

_TAILNET_V4 = ipaddress.IPv4Network("100.64.0.0/10")
_TAILNET_V6 = ipaddress.IPv6Network("fd7a:115c:a1e0::/48")
_EP_SHAPE = re.compile(r"https://(?P<host>\[[0-9A-Fa-f:.]+\]|[^\[\]/:?#@]+):(?P<port>[0-9]+)")
_DNS_LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_DECIMAL_OCTET = re.compile(r"0|[1-9][0-9]{0,2}")
_TS_NET = ".ts.net"


def _valid_ts_net_name(host: str) -> bool:
    if not host.endswith(_TS_NET) or len(host) > 253:
        return False
    labels = host.split(".")
    if len(labels) < 3:  # at least one label before `ts.net`
        return False
    return all(_DNS_LABEL.fullmatch(label) for label in labels)


def _valid_tailnet_v4(host: str) -> bool:
    parts = host.split(".")
    if len(parts) != 4 or not all(_DECIMAL_OCTET.fullmatch(p) for p in parts):
        return False
    try:
        return ipaddress.IPv4Address(host) in _TAILNET_V4
    except ValueError:
        return False


def _valid_tailnet_v6(bracketed: str) -> bool:
    inner = bracketed[1:-1]
    try:
        return ipaddress.IPv6Address(inner) in _TAILNET_V6
    except ValueError:
        return False


def require_endpoint(ep: Any) -> str:
    """One `ep`: exactly `https://<host>:<port>`, no userinfo, path, query or fragment, where the
    host is a lowercase `*.ts.net` name without a trailing dot, or a literal address in
    `100.64.0.0/10` or `[fd7a:115c:a1e0::/48]` (CS-10, FR-002)."""
    if not isinstance(ep, str):
        raise WireError("endpoint is not a string")
    match = _EP_SHAPE.fullmatch(ep)
    if match is None:
        raise WireError("endpoint is not exactly https://<host>:<port>")
    port_text = match["port"]
    if port_text != str(int(port_text)) or not 1 <= int(port_text) <= 65_535:
        raise WireError("endpoint port is not a canonical port number")
    host = match["host"]
    if host.startswith("["):
        ok = _valid_tailnet_v6(host)
    elif host[-1:].isdigit():
        ok = _valid_tailnet_v4(host)
    else:
        ok = _valid_ts_net_name(host)
    if not ok:
        raise WireError("endpoint host is not a tailnet name or tailnet address")
    return ep


# --------------------------------------------------------------------------------------------------
# QR payload (PR1-3, PR1-5)
# --------------------------------------------------------------------------------------------------

_QR_MEMBERS = ("v", "iid", "ep", "oid", "s", "exp")


def _validate_offer(offer: QrOffer, *, now: int | None) -> QrOffer:
    if require_int(offer.v) != PROTOCOL_VERSION:
        raise WireError("unknown protocol version")
    require_iid(offer.iid)
    if not isinstance(offer.ep, tuple) or not offer.ep:
        raise WireError("endpoint list is empty")
    for ep in offer.ep:
        require_endpoint(ep)
    b64u_field("oid", offer.oid)
    b64u_field("s", offer.s)
    exp = require_int(offer.exp, minimum=0)
    if now is not None and exp + CLOCK_SKEW_S <= now:
        raise WireError("offer has expired")
    return offer


def encode_qr_payload(offer: QrOffer, *, now: int | None = None) -> str:
    """`hmp1:` + b64u(UTF-8 JSON) (PR1-3). Refuses to encode an offer a client must reject."""
    _validate_offer(offer, now=now)
    body = {
        "v": offer.v,
        "iid": offer.iid,
        "ep": list(offer.ep),
        "oid": offer.oid,
        "s": offer.s,
        "exp": offer.exp,
    }
    return QR_PREFIX + b64u_encode(dump_json(body))


def decode_qr_payload(text: Any, *, now: int | None) -> QrOffer:
    """Parse and validate an `hmp1:` payload per PR1-5 and CS-10.

    `now` is the verifier's clock; an offer is expired once `exp + CLOCK_SKEW_S <= now`. Pass
    `None` only to inspect a payload without an expiry decision. Unknown members are ignored
    (V-4); duplicate members are rejected (I-JSON).
    """
    if not isinstance(text, str) or not text.startswith(QR_PREFIX):
        raise WireError("not an hmp1: payload")
    if len(text) > MAX_QR_PAYLOAD_CHARS:
        raise TooLargeError("QR payload exceeds the limit")
    raw = b64u_decode_bounded(text[len(QR_PREFIX) :], max_length=MAX_QR_PAYLOAD_CHARS)
    body = parse_ijson(raw, max_bytes=MAX_QR_PAYLOAD_CHARS)
    if not isinstance(body, dict):
        raise WireError("QR payload is not an object")
    for name in _QR_MEMBERS:
        require_member(body, name)
    ep = body["ep"]
    if not isinstance(ep, list):
        raise WireError("endpoint list is not an array")
    offer = QrOffer(
        v=require_int(body["v"]),
        iid=require_str(body["iid"]),
        ep=tuple(ep),
        oid=require_str(body["oid"]),
        s=require_str(body["s"]),
        exp=require_int(body["exp"]),
    )
    return _validate_offer(offer, now=now)
