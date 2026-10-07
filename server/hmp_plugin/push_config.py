"""PN-AV live host-only push settings. No file, network, environment or authority I/O.

Each caller takes one immutable snapshot. Invalid kids/pins close the whole
relay configuration; they are never filtered into an empty liveness set.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import wire

_KID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", re.ASCII)
_AUDIENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", re.ASCII)


@dataclass(frozen=True, repr=False)
class RelayConfig:
    url: str
    audience: str
    kids: tuple[str, ...]
    spki_pins: tuple[bytes, ...] | None


@dataclass(frozen=True, repr=False)
class PushAvailability:
    available: bool
    why: str | None
    relay: RelayConfig | None

    @property
    def live_kids(self) -> frozenset[str]:
        # A malformed or unavailable configuration must never drive kid expiry.
        return frozenset(self.relay.kids) if self.available and self.relay else frozenset()


def configuration_summary(block: object) -> tuple[bool, bool, int]:
    """Configured state only, independent of live approval gates or relay reachability.

    No relay URL, key id or pin escapes this projection. A malformed relay is
    unconfigured even when the host has opted in. Disabled settings may still
    contain a valid relay configuration.
    """
    if not isinstance(block, Mapping):
        return False, False, 0
    relay = _relay(block)
    return block.get("enabled") is True, relay is not None, len(relay.kids) if relay else 0


def valid_kid(value: object) -> bool:
    return type(value) is str and _KID.fullmatch(value) is not None


def _valid_base_url(value: object) -> bool:
    if type(value) is not str or not value or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        # This is a base for appending /v1/push. Credentials, query and fragment
        # cannot be appended safely and are not relay authentication material.
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            # urlsplit loses a present-but-empty query or fragment delimiter.
            # Reject the delimiters themselves before appending the endpoint.
            and "?" not in value
            and "#" not in value
            and parsed.port != 0
            and "\\" not in value
        )
    except ValueError:
        return False


def _relay(block: Mapping) -> RelayConfig | None:
    url, audience, kids = (
        block.get(name) for name in ("relay_url", "relay_audience", "relay_kids")
    )
    if (
        not _valid_base_url(url)
        or type(audience) is not str
        or _AUDIENCE.fullmatch(audience) is None
        or type(kids) is not list
        or not kids
        or any(not valid_kid(kid) for kid in kids)
    ):
        return None
    pins = None
    if "relay_spki_pins" in block:
        configured = block["relay_spki_pins"]
        if type(configured) is not list or not 1 <= len(configured) <= 8:
            return None
        decoded = []
        for pin in configured:
            try:
                if type(pin) is not str or len(pin) != 43:
                    return None
                digest = wire.b64u_decode(pin, length=32)
            except wire.WireError:
                return None
            if digest in decoded:
                return None
            decoded.append(digest)
        pins = tuple(decoded)
    return RelayConfig(url, audience, tuple(kids), pins)


def evaluate(
    block: object, *, direct_send: bool, approvals: bool, phone_chat: bool
) -> PushAvailability:
    """One live call, PN-AV-4 precedence. Only literal True opens an opt-in/member."""
    if not isinstance(block, Mapping) or block.get("enabled") is not True:
        return PushAvailability(False, "push_disabled", None)
    relay = _relay(block)
    if relay is None:
        return PushAvailability(False, "relay_unconfigured", None)
    if direct_send is not True or not (approvals is True or phone_chat is True):
        return PushAvailability(False, "approvals_unavailable", relay)
    return PushAvailability(True, None, relay)
