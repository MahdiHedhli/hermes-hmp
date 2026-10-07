"""Inert PN-ISS-1/PN-KEY handle derivation; no listener, store, file or network I/O.

Future registration/dispatch callers read k_grace once off-loop, then validate
all current row/device/family/generation/visibility bindings themselves. Hash
agreement is only a cryptographic check; it grants no authority or availability.
Nothing here issues a salt, stores a handle, registers a route or logs values.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from . import crypto
from .contract import TAG_PUSH_COLLAPSE, TAG_PUSH_ROUTE
from .wire import b64u_encode


@dataclass(frozen=True, repr=False)
class RouteInputs:
    """Stored PN-ISS-1 fields. repr omits identifiers/salt, which are log-prohibited."""

    iid: str
    host_generation: int
    device_id: str
    family_id: str
    generation: int
    salt: bytes

    def __post_init__(self) -> None:
        if any(type(v) is not str or not v for v in (self.iid, self.device_id, self.family_id)):
            raise crypto.CryptoError("invalid push route binding")
        try:
            for value in (self.iid, self.device_id, self.family_id):
                value.encode("utf-8", errors="strict")
        except UnicodeError:
            raise crypto.CryptoError("invalid push route binding") from None
        if type(self.host_generation) is not int or not 0 <= self.host_generation < 2**64:
            raise crypto.CryptoError("invalid push host generation")
        if type(self.generation) is not int or not 1 <= self.generation < 2**53:
            raise crypto.CryptoError("invalid push registration generation")
        if type(self.salt) is not bytes or len(self.salt) != 32:
            raise crypto.CryptoError("invalid push route salt")


def _check_key(key: bytes) -> None:
    if type(key) is not bytes or len(key) != 32:
        raise crypto.CryptoError("invalid push key")


def derive_route(key: bytes, inputs: RouteInputs) -> bytes:
    """Raw 32-byte R. Only the response/payload caller encodes it with canonical b64u."""
    _check_key(key)
    message = TAG_PUSH_ROUTE + crypto.length_prefixed(
        inputs.iid,
        inputs.host_generation,
        inputs.device_id,
        inputs.family_id,
        inputs.generation,
        inputs.salt,
    )
    return hmac.digest(key, message, "sha256")


def rederive_route(key: bytes | None, inputs: RouteInputs, expected_hash: bytes) -> bytes | None:
    """Return raw R only on an exact SHA-256 match; no state changes on read loss/mismatch."""
    if key is None:
        return None
    if type(expected_hash) is not bytes or len(expected_hash) != 32:
        return None
    route = derive_route(key, inputs)
    return route if hmac.compare_digest(hashlib.sha256(route).digest(), expected_hash) else None


def derive_collapse(key: bytes, route: bytes, scope: str) -> bytes:
    """Raw 24-byte C, equivalent to the first 32 b64u characters. No scope normalization."""
    _check_key(key)
    if type(route) is not bytes or len(route) != 32 or type(scope) is not str or not scope:
        raise crypto.CryptoError("invalid push collapse binding")
    try:
        scope_bytes = scope.encode("utf-8", errors="strict")
    except UnicodeError:
        raise crypto.CryptoError("invalid push collapse binding") from None
    message = TAG_PUSH_COLLAPSE + crypto.length_prefixed(
        hashlib.sha256(route).digest(), scope_bytes
    )
    return hmac.digest(key, message, "sha256")[:24]


def route_text(route: bytes) -> str:
    """Canonical wire form of raw R; reject accidental text/digest lengths."""
    if type(route) is not bytes or len(route) != 32:
        raise crypto.CryptoError("invalid push route")
    return b64u_encode(route)
