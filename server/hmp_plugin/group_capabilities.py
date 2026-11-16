"""Bounded native group advertisements; never a phone permission or ready verdict.

This internal input boundary is not wired to a route, native client or Store.
The caller must separately establish transport identity, device/bot/room rights,
current authority and operation semantics. Input is already-decoded JSON DATA;
frame limits and decoder safety are outside this parser.
"""

from __future__ import annotations

from dataclasses import dataclass

_MAX_FIELDS = 64
_MAX_KEY_CHARS = 128
_MAX_METHODS = 128
_MAX_FEATURES = 32
_MAX_TOKEN_CHARS = 80
_MAX_INTEGER = (1 << 31) - 1
_LOCAL_LOG_PAGE_LIMIT = 500
_METHODS = frozenset(
    {
        "groups.capabilities",
        "groups.list",
        "groups.state",
        "groups.log",
        "groups.create",
        "groups.rename",
        "groups.context",
        "groups.disband",
        "groups.send",
        "groups.attachment.upload",
        "groups.attachment.download",
        "groups.stop",
        "groups.continue",
        "groups.retry",
        "groups.discard",
        "groups.approve",
        "groups.peer.register",
        "groups.peer.invite",
        "groups.peer.revoke",
    }
)
_FEATURES = frozenset(
    {
        "room_identity",
        "monotonic_log",
        "replayable_disband",
        "peer_renewal_horizon",
    }
)


class InvalidGroupCapabilitiesError(ValueError):
    """A fixed refusal that contains no native diagnostic, identity or content."""

    def __init__(self) -> None:
        super().__init__("Native group capabilities unavailable.")


@dataclass(frozen=True, slots=True, repr=False)
class NativeGroupCapabilities:
    """Observations only: even an advertised method can be unauthorized natively."""

    protocol_version: int
    driver: bool
    persistent_process: bool
    methods: frozenset[str]
    features: frozenset[str]
    log_page_limit: int

    def advertises(self, method: str) -> bool:
        """Known-name membership, without a readiness or authorization inference."""
        if (
            type(method) is not str
            or not 1 <= len(method) <= _MAX_TOKEN_CHARS
            or method not in _METHODS
        ):
            raise InvalidGroupCapabilitiesError()
        return method in self.methods


def _positive_integer(value: object) -> int:
    if type(value) is not int or not 1 <= value <= _MAX_INTEGER:
        raise InvalidGroupCapabilitiesError()
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise InvalidGroupCapabilitiesError()
    return value


def _tokens(value: object, *, known: frozenset[str], limit: int) -> frozenset[str]:
    if type(value) is not list or len(value) > limit:
        raise InvalidGroupCapabilitiesError()
    for token in value:
        if type(token) is not str or not 1 <= len(token) <= _MAX_TOKEN_CHARS or not token.isascii():
            raise InvalidGroupCapabilitiesError()
    # Unknown bounded additions do not become retained metadata or native grants.
    return frozenset(token for token in value if token in known)


def parse_group_capabilities(value: object) -> NativeGroupCapabilities:
    """Normalize only understood fields; never inspect ignored metadata values."""
    if type(value) is not dict or len(value) > _MAX_FIELDS:
        raise InvalidGroupCapabilitiesError()
    # Validate before lookups: even a plain dict can contain a foreign key whose
    # equality implementation runs when a required String key is looked up.
    for key in value:
        if type(key) is not str or not 1 <= len(key) <= _MAX_KEY_CHARS:
            raise InvalidGroupCapabilitiesError()
    return NativeGroupCapabilities(
        protocol_version=_positive_integer(value.get("protocol_version")),
        driver=_boolean(value.get("driver")),
        persistent_process=_boolean(value.get("persistent_process")),
        methods=_tokens(value.get("methods"), known=_METHODS, limit=_MAX_METHODS),
        features=_tokens(value.get("features"), known=_FEATURES, limit=_MAX_FEATURES),
        log_page_limit=min(_positive_integer(value.get("max_log_limit")), _LOCAL_LOG_PAGE_LIMIT),
    )
