"""Private payload carrier for the authenticated local image fetch (spec 011 S5; HMP v1 §7e).

One immutable object holds the exact frozen bytes, the structural MIME and the SHA-256 of an
image that bridge phase one read, validated and fingerprinted. It is NOT a wire object: it has
no serialization, no JSON form, no `__dict__`, and a fixed `repr` that carries no byte, size,
digest or MIME. It is stdlib only and imports no other `hmp_plugin` module, so the bridge, the
route orchestrator and the listener binder can all hold the very same class from one copy of this
module (the binder proves that at listener open).

The buffer must never reach an exception, a log line, a report or a public dataclass. The carrier
therefore refuses pickling and copying (a second 8 MiB copy is never made here) and exposes the
bytes only through a property for the in-process handler that streams them.
"""

from __future__ import annotations

from typing import Final

MAX_PAYLOAD_BYTES: Final = 8 * 1024 * 1024
SHA256_BYTES: Final = 32
ALLOWED_MIMES: Final = frozenset({"image/png", "image/jpeg", "image/webp"})


class MediaPayloadRefusal(Exception):  # noqa: N818 - a closed, content-free refusal
    """Raised only for a programming error (bad type or bound). Fixed text, no parameters."""

    def __init__(self) -> None:
        super().__init__("media payload refused")

    def __reduce__(self) -> tuple[type[MediaPayloadRefusal], tuple[()]]:
        return (MediaPayloadRefusal, ())


class MediaPayload:
    """`data` (1..8 MiB exact `bytes`), `mime` (PNG, JPEG or WebP) and `sha256` (32 exact bytes).

    The digest is supplied by the phase that computed it over these very bytes; the carrier
    checks only types and bounds so it never hashes 8 MiB a second time."""

    __slots__ = ("_data", "_mime", "_sha256")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("MediaPayload is final")

    def __init__(self, data: bytes, mime: str, sha256: bytes) -> None:
        if (
            type(data) is not bytes
            or not 0 < len(data) <= MAX_PAYLOAD_BYTES
            or type(mime) is not str
            or mime not in ALLOWED_MIMES
            or type(sha256) is not bytes
            or len(sha256) != SHA256_BYTES
        ):
            raise MediaPayloadRefusal from None
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_mime", mime)
        object.__setattr__(self, "_sha256", sha256)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("MediaPayload is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("MediaPayload is immutable")

    def __repr__(self) -> str:
        return "MediaPayload()"

    __str__ = __repr__

    def __reduce__(self) -> object:
        raise TypeError("MediaPayload is not serializable")

    def __reduce_ex__(self, protocol: object) -> object:
        raise TypeError("MediaPayload is not serializable")

    def __copy__(self) -> object:
        raise TypeError("MediaPayload is not copyable")

    def __deepcopy__(self, memo: object) -> object:
        raise TypeError("MediaPayload is not copyable")

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def mime(self) -> str:
        return self._mime

    @property
    def sha256(self) -> bytes:
        return self._sha256

    @property
    def size(self) -> int:
        return len(self._data)
