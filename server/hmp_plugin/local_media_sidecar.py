"""Non-wire read-result carriers for host-local generated images (HMP v1 §7e, LM-8).

INERT: nothing at start-up, in a route or in `reads.py` imports this module; the bridge loads it
only inside its unused media-aware read methods.
It imports only the standard library and `contract` (for the `Row`, `ConversationRef`,
`ResetReason` and public wire types). It imports no parser, scanner, registry or other
`local_media_*` module.

A candidate is **not authority**. It is the smallest fact a later slice may pre-filter on: a
positive tool row id and the 32-byte digest of that row's raw content. It carries no image string,
no path, no flat name and no raw content. A later handler must rescan the active history and
compare the row id and digest itself before it mints anything.

These carriers must never reach a wire body. They are deliberately **not** dataclasses, mappings,
tuples or sequences: `request_ctx._plain` serializes dataclass fields, mappings and tuples
recursively and passes every other object through, so the only safe shape is a plain slots object
that `wire.dump_json` then rejects. An accidental return of a carrier therefore fails closed as the
existing `500 other` with a fixed body. Every class here:

- is a plain class with `__slots__` (no instance dict); ordinary subclassing is refused, which is
  not containment of trusted in-process code (which can still spoof a name or a `__class__`);
- is immutable: values are set once in `__init__`, `__setattr__` and `__delattr__` refuse;
- has a fixed `repr`, `str` and `format` with no value in them;
- refuses pickle, copy and deepcopy with a fixed message;
- keeps object identity for `==` and `hash`;
- validates exact types (`type(x) is ...`, never `isinstance`), bounded counts and bounded string
  lengths, and refuses with a content-free `MediaCarrierRefusal`.

Nothing logs. Every refusal has fixed text with no parameter, so a refusal cannot carry a value.
`MediaReadResult.public` holds exactly the object the old read method returns; this module does
not inspect, copy or sanitize it beyond its exact class.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Final, Generic, Protocol, TypeVar

from .contract import (
    HISTORY_LIMIT_MAX,
    ConversationRef,
    HistoryPage,
    HistoryReset,
    ResetReason,
    Row,
    SessionSnapshot,
    SnapshotResponse,
)

MAX_CANDIDATES_PER_RESPONSE: Final = 128
MAX_FIELD_CHARS: Final = 256
DIGEST_BYTES: Final = 32
MAX_ROWS: Final = HISTORY_LIMIT_MAX

_PUBLIC_TYPES: Final = frozenset({SnapshotResponse, HistoryPage, HistoryReset, SessionSnapshot})
_CLOSED: Final = frozenset(
    {
        "MediaCandidate",
        "MediaRowsQuery",
        "BridgeMediaRows",
        "MediaSidecar",
        "MediaReadResult",
    }
)

P = TypeVar("P")


class MediaCarrierRefusal(Exception):  # noqa: N818 - a closed, content-free refusal, not an "error"
    """Raised only for a programming error (bad type, bound or shape). Fixed text, no parameters."""

    def __init__(self) -> None:
        super().__init__("local media carrier refused")

    def __reduce__(self) -> tuple[type[MediaCarrierRefusal], tuple[()]]:
        return (MediaCarrierRefusal, ())


class MediaOrigin(Enum):
    """How the rows were read. A fact about the read, not session-kind authority."""

    OWN_CONVERSATION = "own_conversation"
    BROWSED_SESSION = "browsed_session"


class SidecarStatus(Enum):
    CANDIDATES = "candidates"
    NO_ROWS = "no_rows"
    UNSUPPORTED_BRIDGE = "unsupported_bridge"


def _text(value: object) -> str:
    if type(value) is not str or not 0 < len(value) <= MAX_FIELD_CHARS:
        raise MediaCarrierRefusal from None
    return value


def _optional_text(value: object) -> str | None:
    return None if value is None else _text(value)


def _candidates(value: object) -> tuple[MediaCandidate, ...]:
    if type(value) is not tuple or len(value) > MAX_CANDIDATES_PER_RESPONSE:
        raise MediaCarrierRefusal from None
    seen: set[int] = set()
    for item in value:
        if type(item) is not MediaCandidate or item.tool_row_id in seen:
            raise MediaCarrierRefusal from None
        seen.add(item.tool_row_id)
    return value


class _Carrier:
    """Shared immutability, fixed text and serialization refusal. Never instantiated directly."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if cls.__module__ != __name__ or cls.__name__ not in _CLOSED:
            raise TypeError("closed carrier")
        super().__init_subclass__(**kwargs)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("immutable")

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    __str__ = __repr__

    def __reduce__(self) -> Any:
        raise TypeError("not serializable")

    def __reduce_ex__(self, protocol: object) -> Any:
        raise TypeError("not serializable")

    def __copy__(self) -> Any:
        raise TypeError("not serializable")

    def __deepcopy__(self, memo: object) -> Any:
        raise TypeError("not serializable")


class MediaCandidate(_Carrier):
    """A positive tool row id and the 32-byte digest of its raw content. Never a path or name."""

    __slots__ = ("_raw_digest", "_tool_row_id")

    def __init__(self, tool_row_id: int, raw_digest: bytes) -> None:
        if type(tool_row_id) is not int or tool_row_id < 1:
            raise MediaCarrierRefusal from None
        if type(raw_digest) is not bytes or len(raw_digest) != DIGEST_BYTES:
            raise MediaCarrierRefusal from None
        object.__setattr__(self, "_tool_row_id", tool_row_id)
        object.__setattr__(self, "_raw_digest", raw_digest)

    @property
    def tool_row_id(self) -> int:
        return self._tool_row_id

    @property
    def raw_digest(self) -> bytes:
        return self._raw_digest


class MediaRowsQuery(_Carrier):
    """Provenance of the one native query that produced the rows."""

    __slots__ = ("_profile", "_query_tip", "_session_id")

    def __init__(self, profile: str, session_id: str, query_tip: str) -> None:
        object.__setattr__(self, "_profile", _text(profile))
        object.__setattr__(self, "_session_id", _text(session_id))
        object.__setattr__(self, "_query_tip", _text(query_tip))

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def query_tip(self) -> str:
        return self._query_tip


class BridgeMediaRows(_Carrier):
    """Bridge to `Reads`: the rows the old method returns, the query, and the candidates."""

    __slots__ = ("_candidates", "_query", "_rows")

    def __init__(
        self,
        rows: tuple[Row, ...],
        query: MediaRowsQuery,
        candidates: tuple[MediaCandidate, ...],
    ) -> None:
        if type(rows) is not tuple or len(rows) > MAX_ROWS:
            raise MediaCarrierRefusal from None
        if any(type(row) is not Row for row in rows):
            raise MediaCarrierRefusal from None
        if type(query) is not MediaRowsQuery:
            raise MediaCarrierRefusal from None
        object.__setattr__(self, "_rows", rows)
        object.__setattr__(self, "_query", query)
        object.__setattr__(self, "_candidates", _candidates(candidates))

    @property
    def rows(self) -> tuple[Row, ...]:
        return self._rows

    @property
    def query(self) -> MediaRowsQuery:
        return self._query

    @property
    def candidates(self) -> tuple[MediaCandidate, ...]:
        return self._candidates


class MediaSidecar(_Carrier):
    """`Reads` to a future handler. Records the read; it establishes no authority.

    Only `CANDIDATES` may carry candidates, and then the session and both tips are required. The
    other statuses carry none and may lack a session or tip (no conversation, a reset page, an
    unsupported bridge).
    """

    __slots__ = (
        "_candidates",
        "_lineage_tip",
        "_origin",
        "_profile",
        "_query_tip",
        "_session_id",
        "_status",
        "_user_id",
    )

    def __init__(
        self,
        *,
        status: SidecarStatus,
        origin: MediaOrigin,
        user_id: str,
        profile: str,
        session_id: str | None,
        query_tip: str | None,
        lineage_tip: str | None,
        candidates: tuple[MediaCandidate, ...],
    ) -> None:
        if type(status) is not SidecarStatus or type(origin) is not MediaOrigin:
            raise MediaCarrierRefusal from None
        session_id = _optional_text(session_id)
        query_tip = _optional_text(query_tip)
        lineage_tip = _optional_text(lineage_tip)
        _candidates(candidates)
        if status is SidecarStatus.CANDIDATES:
            if session_id is None or query_tip is None or lineage_tip is None:
                raise MediaCarrierRefusal from None
        elif candidates:
            raise MediaCarrierRefusal from None
        object.__setattr__(self, "_status", status)
        object.__setattr__(self, "_origin", origin)
        object.__setattr__(self, "_user_id", _text(user_id))
        object.__setattr__(self, "_profile", _text(profile))
        object.__setattr__(self, "_session_id", session_id)
        object.__setattr__(self, "_query_tip", query_tip)
        object.__setattr__(self, "_lineage_tip", lineage_tip)
        object.__setattr__(self, "_candidates", candidates)

    @property
    def status(self) -> SidecarStatus:
        return self._status

    @property
    def origin(self) -> MediaOrigin:
        return self._origin

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def query_tip(self) -> str | None:
        return self._query_tip

    @property
    def lineage_tip(self) -> str | None:
        return self._lineage_tip

    @property
    def candidates(self) -> tuple[MediaCandidate, ...]:
        return self._candidates

    @property
    def provenance_consistent(self) -> bool:
        """The rows' query tip equals the separately read lineage tip. Derived, not stored."""
        return self._query_tip is not None and self._query_tip == self._lineage_tip


class MediaReadResult(_Carrier, Generic[P]):
    """`public` is exactly what the old read method returns; `sidecar` is private."""

    __slots__ = ("_public", "_sidecar")

    def __init__(self, public: P, sidecar: MediaSidecar) -> None:
        if type(public) not in _PUBLIC_TYPES or type(sidecar) is not MediaSidecar:
            raise MediaCarrierRefusal from None
        object.__setattr__(self, "_public", public)
        object.__setattr__(self, "_sidecar", sidecar)

    @property
    def public(self) -> P:
        return self._public

    @property
    def sidecar(self) -> MediaSidecar:
        return self._sidecar


class MediaReadBridge(Protocol):
    """Optional bridge extension, selected by an explicit class-level opt-in (never probed).

    `ReadBridge` itself is unchanged. S4 calls these through `Reads` and `bind_media_batch` through
    the descriptor routes. A bridge that cannot represent the query metadata (or a page over
    `MAX_ROWS`) returns the exact old text-row list instead.
    """

    def latest_with_media(
        self, ref: ConversationRef, limit: int
    ) -> BridgeMediaRows | list[Row]: ...

    def after_with_media(
        self, ref: ConversationRef, after_id: int, limit: int
    ) -> BridgeMediaRows | list[Row] | ResetReason: ...

    def bind_media_batch(self, sidecar: MediaSidecar) -> object | None: ...
