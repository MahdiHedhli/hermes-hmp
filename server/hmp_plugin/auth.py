"""Bearer and `HMP-Instance` authentication (TR-5, PR5-6, PR5-7). T026.

Order, per request:

1. `HMP-Instance` must equal the serving `iid`, before any token lookup: otherwise
   `401 wrong_instance` (TR-5). A missing or repeated header is a mismatch.
2. `Authorization: Bearer <b64u 32 B>`; anything else is `401 unauthenticated`. Credentials are
   read from this header only, never from the URL (TR-5).
3. The access token is looked up by SHA-256 of its raw bytes (PR4-4) in `access_tokens` only, so
   a refresh token is never accepted as an access token (PR5-6).
4. It must be bound to this `iid` (PR5-6) and unexpired (PR5-7): otherwise `401 unauthenticated`.
5. Its device must be `ACTIVE` and its family unrevoked. A revoked device, or a revoked family,
   is `401 revoked` (SR-004: a revoked device's next request fails with `revoked`); any other
   non-`ACTIVE` state is `401 unauthenticated`.

The caller of a bearer route has proven possession of a token HMP issued, so disclosing
`revoked` here is intended; P5's stricter disclosure rule (PR5-3) is in `tokens.py`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import crypto, wire
from .contract import ErrorCode, HmpError

_BEARER = re.compile(r"Bearer ([A-Za-z0-9_-]{43})")


@dataclass(frozen=True)
class AuthContext:
    """The authenticated caller of a bearer route."""

    device_id: str
    user_id: str
    family_id: str


class Authenticator:
    """TR-5 / PR5-6 over the store. `now` returns the host clock in integer seconds."""

    def __init__(self, store: Any, iid: str, now: Callable[[], int]) -> None:
        self._store = store
        self._iid = iid
        self._now = now

    def authenticate(self, authorization: str | None, hmp_instance: str | None) -> AuthContext:
        # `iid` is always ASCII (a lowercase base32 fingerprint), so a non-ASCII header value is
        # always a mismatch. Checked before comparing: aiohttp decodes header bytes leniently
        # (surrogateescape), so a non-ASCII or non-UTF-8 header can hold a lone surrogate that
        # `crypto.constant_time_equal`'s `str.encode("utf-8")` (strict) would raise on instead of
        # just returning False, which would otherwise escape as an unhandled 500 (SEC-4: a
        # request malformed only in this header must still get the ordinary 401, never a 500).
        if (
            not isinstance(hmp_instance, str)
            or not hmp_instance.isascii()
            or not crypto.constant_time_equal(hmp_instance, self._iid)
        ):
            raise HmpError(ErrorCode.WRONG_INSTANCE)
        token = bearer_token(authorization)
        if token is None:
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        row = self._store.access_authority_snapshot(crypto.sha256(token))
        if row is None:
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        if not isinstance(row, dict) or not isinstance(row.get("access_iid"), str):
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        if not crypto.constant_time_equal(row["access_iid"], self._iid):
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        if (
            not isinstance(row.get("access_family_id"), str)
            or not isinstance(row.get("access_device_id"), str)
            or row.get("family_found_id") != row["access_family_id"]
            or row.get("family_device_id") != row["access_device_id"]
            or row.get("device_found_id") != row["access_device_id"]
            or not isinstance(row.get("device_user_id"), str)
        ):
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        if row.get("device_state") == "REVOKED" or row.get("family_revoked_at") is not None:
            raise HmpError(ErrorCode.REVOKED)
        if row.get("device_state") != "ACTIVE":
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        expires_at = row.get("access_expires_at")
        if type(expires_at) is not int or self._now() >= expires_at:
            raise HmpError(ErrorCode.UNAUTHENTICATED)
        return AuthContext(
            device_id=row["access_device_id"],
            user_id=row["device_user_id"],
            family_id=row["access_family_id"],
        )


def bearer_token(authorization: str | None) -> bytes | None:
    """The raw 32-byte token of `Bearer <canonical b64u>`, or None."""
    if not isinstance(authorization, str):
        return None
    match = _BEARER.fullmatch(authorization)
    if match is None:
        return None
    try:
        return wire.b64u_field("token", match.group(1))
    except wire.WireError:
        return None
