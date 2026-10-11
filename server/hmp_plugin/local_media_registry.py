"""Process-local reference registry for host-local generated images (HMP v1 §7e, LM-9).

INERT: nothing at start-up, in a route or in a handler imports this module yet. It is stdlib only
and imports no other `hmp_plugin` module. There is no module-level instance; a later slice owns
creating and sharing one.

**Possessing a ref authorizes nothing.** A registry hit never authorizes a fetch. Every fetch
still re-authenticates, re-checks native authorization and tip, rescans the tool row and rechecks
the file (LM-9, LM-10..LM-12). The registry only says "this process minted this ref for exactly
this caller and this tool row, recently".

What it holds, per entry: a fresh 32-byte random ref (43 base64url characters, no padding) and an
immutable private `Binding` (device, user, instance, profile, session kind, bound session, tip,
tool row id, raw-content digest), a monotonic mint time and the optional first-served sha256.
Nothing is durable, no path, file name or MIME is stored, and a new instance (restart) starts empty.

Rules:

- TTL is 1800 s from mint and is never extended: an entry is live while `now - minted < TTL` and
  expired at exactly TTL. Idempotent mint and lookup do not move the mint time.
- At most 512 entries per device and 4096 in total. Eviction is least recently used, where mint,
  idempotent re-mint and a successful lookup count as use. Expired entries are deleted when seen
  and swept from the oldest mint at each mint; the reverse index and per-device counts are updated
  in the same critical section as every removal.
- Every public method, including every read, runs under one `threading.Lock`, so a shared
  registry is safe from executor threads and the event loop. No method awaits or does I/O.
- `lookup` returns the same `None` for a malformed ref, an unknown ref, an expired or evicted ref,
  and a ref minted for a different device, user, instance or profile. Nothing distinguishes them.
- `record_first_served` is the compare-and-set for the synchronous final section (LM-12). It acts
  only on the very entry the caller's snapshot came from and returns a closed `FirstServe` value.
- Nothing logs. `repr` and `str` of every public object, and every exception, are fixed text with
  no ref, binding, native id or digest. Seams for a controlled clock, random source and lower
  capacities are underscore-private keyword arguments of the constructor; they can lower the
  production limits but never raise them.

Binding fields follow the current native types: the session, tip and every auth string are exact
`str` of 1..256 characters (the scanner's MAX_ID_CHARS); the tool row id is an exact, non-bool
`int`. These bounds limit native and auth input, they are not wire authority. How the registry is
shared between the mint and fetch paths is S4/S5's decision.
"""

from __future__ import annotations

import base64
import math
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from secrets import token_bytes
from typing import Final

MEDIA_REF_TTL_S: Final = 1800
MAX_REFS_PER_DEVICE: Final = 512
MAX_REFS_TOTAL: Final = 4096

REF_BYTES: Final = 32
DIGEST_BYTES: Final = 32
MAX_FIELD_CHARS: Final = 256
_MINT_ATTEMPTS: Final = 4

_REF_RE = re.compile(r"[A-Za-z0-9_-]{43}")


class RegistryRefusal(Exception):  # noqa: N818 - a closed, content-free refusal, not an "error"
    """Raised only for a programming error (bad binding, bad seam). Fixed text, no parameters."""

    def __init__(self) -> None:
        super().__init__("local media registry refused")

    def __reduce__(self) -> tuple[type[RegistryRefusal], tuple[()]]:
        return (RegistryRefusal, ())


class SessionKind(Enum):
    BOT_CHAT = "bot_chat"
    PHONE = "phone"


class FirstServe(Enum):
    """Closed result of `record_first_served`. Only RECORDED and UNCHANGED permit serving."""

    RECORDED = "recorded"
    UNCHANGED = "unchanged"
    REFUSED = "refused"


def _text(value: object) -> str:
    if type(value) is not str or not 0 < len(value) <= MAX_FIELD_CHARS:
        raise RegistryRefusal from None
    return value


def _row_id(value: object) -> int:
    if type(value) is not int:
        raise RegistryRefusal from None
    return value


def _number(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):  # type: ignore[arg-type]
        raise RegistryRefusal from None
    return value  # type: ignore[return-value]


def _seam(fn: Callable[..., object], *args: object) -> object:
    """Call an injected seam; any failure becomes a content-free refusal with no context."""
    try:
        return fn(*args)
    except Exception:  # noqa: S110 - refuse below, outside the handler: no context keeps its text
        pass
    raise RegistryRefusal from None


def _digest(value: object) -> bytes:
    if type(value) is not bytes or len(value) != DIGEST_BYTES:
        raise RegistryRefusal from None
    return value


@dataclass(frozen=True, slots=True, repr=False)
class Caller:
    """The authenticated request context a lookup or CAS must match exactly."""

    device_id: str
    user_id: str
    instance_id: str
    profile: str

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile"):
            _text(getattr(self, name))

    def __repr__(self) -> str:
        return "Caller()"

    __str__ = __repr__


@dataclass(frozen=True, slots=True, repr=False)
class Binding:
    """Everything a ref is bound to. Immutable, hashable, and never shown by `repr`."""

    device_id: str
    user_id: str
    instance_id: str
    profile: str
    kind: SessionKind
    session_id: str
    tip: str
    tool_row_id: int
    raw_digest: bytes

    def __post_init__(self) -> None:
        for name in ("device_id", "user_id", "instance_id", "profile", "session_id", "tip"):
            _text(getattr(self, name))
        _row_id(self.tool_row_id)
        _digest(self.raw_digest)
        if type(self.kind) is not SessionKind:
            raise RegistryRefusal from None

    def __repr__(self) -> str:
        return "Binding()"

    __str__ = __repr__

    def matches(self, caller: Caller) -> bool:
        return (
            self.device_id == caller.device_id
            and self.user_id == caller.user_id
            and self.instance_id == caller.instance_id
            and self.profile == caller.profile
        )


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class EntrySnapshot:
    """Immutable copy of an entry at lookup time, for native checks outside the lock.

    It is not authority: `record_first_served` re-validates the live entry it came from.
    """

    binding: Binding
    minted_at: float
    first_served: bytes | None
    _token: object = field(repr=False)

    def __repr__(self) -> str:
        return "EntrySnapshot()"

    __str__ = __repr__


class _Stored:
    __slots__ = ("binding", "first_served", "minted_at", "token")

    def __init__(self, binding: Binding, minted_at: float) -> None:
        self.binding = binding
        self.minted_at = minted_at
        self.first_served: bytes | None = None
        self.token = object()


@dataclass(frozen=True, slots=True, repr=False)
class _Limits:
    ttl_s: float = MEDIA_REF_TTL_S
    per_device: int = MAX_REFS_PER_DEVICE
    total: int = MAX_REFS_TOTAL

    def __post_init__(self) -> None:
        if type(self.per_device) is not int or type(self.total) is not int:
            raise RegistryRefusal from None
        if not (0 < _number(self.ttl_s) <= MEDIA_REF_TTL_S):
            raise RegistryRefusal from None
        if not (1 <= self.per_device <= MAX_REFS_PER_DEVICE):
            raise RegistryRefusal from None
        if not (1 <= self.total <= MAX_REFS_TOTAL):
            raise RegistryRefusal from None


def _encode_ref(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class LocalMediaRegistry:
    """Lock-protected, process-local, in-memory registry. See the module docstring."""

    def __init__(
        self,
        *,
        _clock: Callable[[], float] = time.monotonic,
        _random: Callable[[int], bytes] = token_bytes,
        _limits: _Limits | None = None,
    ) -> None:
        if not callable(_clock) or not callable(_random):
            raise RegistryRefusal from None
        if _limits is not None and type(_limits) is not _Limits:
            raise RegistryRefusal from None
        self._clock = _clock
        self._random = _random
        self._limits = _limits if _limits is not None else _Limits()
        self._lock = threading.Lock()
        self._last_now = float("-inf")
        # dict order is mint order (entries are never re-minted); `_lru` and `_device_lru` are
        # recency order. `_by_binding` is the reverse index for idempotent mint.
        self._entries: dict[str, _Stored] = {}
        self._lru: OrderedDict[str, None] = OrderedDict()
        self._device_lru: dict[str, OrderedDict[str, None]] = {}
        self._by_binding: dict[Binding, str] = {}

    def __repr__(self) -> str:
        return "LocalMediaRegistry()"

    __str__ = __repr__

    # -- internals; every caller holds the lock ------------------------------------------------

    def _now(self) -> float:
        now = float(_number(_seam(self._clock)))
        if now > self._last_now:
            self._last_now = now
        return self._last_now

    def _expired(self, stored: _Stored, now: float) -> bool:
        return now - stored.minted_at >= self._limits.ttl_s

    def _remove(self, ref: str) -> None:
        stored = self._entries.pop(ref)
        del self._lru[ref]
        self._by_binding.pop(stored.binding, None)
        per_device = self._device_lru[stored.binding.device_id]
        del per_device[ref]
        if not per_device:
            del self._device_lru[stored.binding.device_id]

    def _sweep_expired(self, now: float) -> None:
        while self._entries:
            ref = next(iter(self._entries))
            if not self._expired(self._entries[ref], now):
                return
            self._remove(ref)

    def _touch(self, ref: str, stored: _Stored) -> None:
        self._lru.move_to_end(ref)
        self._device_lru[stored.binding.device_id].move_to_end(ref)

    def _live(self, ref: str, now: float) -> _Stored | None:
        stored = self._entries.get(ref)
        if stored is None:
            return None
        if self._expired(stored, now):
            self._remove(ref)
            return None
        return stored

    def _new_ref(self) -> str:
        for _ in range(_MINT_ATTEMPTS):
            raw = _seam(self._random, REF_BYTES)
            if type(raw) is not bytes or len(raw) != REF_BYTES:
                raise RegistryRefusal from None
            ref = _encode_ref(raw)
            if ref not in self._entries:
                return ref
        raise RegistryRefusal from None

    # -- public API ----------------------------------------------------------------------------

    def mint(self, binding: Binding) -> str:
        """The ref for exactly this binding. An unexpired identical binding returns its existing
        ref and never extends its TTL; otherwise a fresh ref is made, evicting LRU entries first
        when the device or total cap would be exceeded."""
        if type(binding) is not Binding:
            raise RegistryRefusal from None
        with self._lock:
            now = self._now()
            self._sweep_expired(now)
            existing = self._by_binding.get(binding)
            if existing is not None:
                self._touch(existing, self._entries[existing])
                return existing
            ref = self._new_ref()
            per_device = self._device_lru.get(binding.device_id)
            if per_device is not None and len(per_device) >= self._limits.per_device:
                self._remove(next(iter(per_device)))
            if len(self._entries) >= self._limits.total:
                self._remove(next(iter(self._lru)))
            stored = _Stored(binding, now)
            self._entries[ref] = stored
            self._lru[ref] = None
            self._device_lru.setdefault(binding.device_id, OrderedDict())[ref] = None
            self._by_binding[binding] = ref
            return ref

    def lookup(self, ref: object, caller: Caller) -> EntrySnapshot | None:
        """A snapshot of the live entry, or `None` for every refusal alike (malformed, unknown,
        expired, evicted, or bound to another device, user, instance or profile)."""
        if type(ref) is not str or type(caller) is not Caller or not _REF_RE.fullmatch(ref):
            return None
        with self._lock:
            stored = self._live(ref, self._now())
            if stored is None or not stored.binding.matches(caller):
                return None
            self._touch(ref, stored)
            return EntrySnapshot(
                stored.binding, stored.minted_at, stored.first_served, stored.token
            )

    def record_first_served(
        self, ref: object, snapshot: EntrySnapshot, caller: Caller, digest: bytes
    ) -> FirstServe:
        """Compare-and-set of the first served sha256, for the synchronous final section.

        Acts only if `ref` still names the very entry `snapshot` came from, unexpired, for this
        caller. It then records `digest` if none is set (RECORDED), accepts the same digest
        (UNCHANGED), and on a different digest deletes the entry and refuses. A missing, expired,
        replaced or foreign-caller entry is refused (an expired one is deleted; a replacement or
        another caller's entry is left alone). Bad arguments refuse without touching anything."""
        if (
            type(ref) is not str
            or type(snapshot) is not EntrySnapshot
            or type(caller) is not Caller
            or type(digest) is not bytes
            or len(digest) != DIGEST_BYTES
            or not _REF_RE.fullmatch(ref)
        ):
            return FirstServe.REFUSED
        with self._lock:
            stored = self._live(ref, self._now())
            if (
                stored is None
                or stored.token is not snapshot._token
                or stored.binding is not snapshot.binding
                or not stored.binding.matches(caller)
            ):
                return FirstServe.REFUSED
            if stored.first_served is None:
                stored.first_served = digest
                self._touch(ref, stored)
                return FirstServe.RECORDED
            if stored.first_served == digest:
                self._touch(ref, stored)
                return FirstServe.UNCHANGED
            self._remove(ref)
            return FirstServe.REFUSED

    # -- test support ---------------------------------------------------------------------------

    def _audit(self) -> int:
        """Assert that every index agrees with the entries; return the entry count."""
        with self._lock:
            total = len(self._entries)
            assert set(self._lru) == set(self._entries) and len(self._lru) == total
            assert len(self._by_binding) == total
            counted = 0
            for device, refs in self._device_lru.items():
                assert refs and len(refs) <= self._limits.per_device
                assert all(self._entries[r].binding.device_id == device for r in refs)
                counted += len(refs)
            assert counted == total <= self._limits.total
            for ref, stored in self._entries.items():
                assert self._by_binding[stored.binding] == ref
            return total
