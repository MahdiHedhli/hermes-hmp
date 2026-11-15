"""Local native-read claims; no native authentication or filesystem work here.

Only the actual service issuer may register/retire operations and attach its
original native-policy observation. A claim's shape or an observation alone is
not authority: the reader also joins object identity to this live registry.
The service must separately enforce worker/queue/drain and original credentials.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
MAX_RECORDS = 22


class NativeSourceError(ValueError):
    def __init__(self, reason: str = "native_source_unavailable") -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(eq=False, repr=False)
class _Operation:
    original: object
    profile: str
    deadline: float
    active: bool = True
    claim: NativeReadClaim | None = None
    binding: tuple | None = None


class NativeReadClaim:
    __slots__ = (
        "_authority",
        "_generation",
        "_gid",
        "_home",
        "_in_progress",
        "_owner",
        "_rechecked",
        "_record",
        "_uid",
        "_unknown",
        "_used",
    )

    def __init__(self, owner, record, home, uid, gid, authority):
        self._owner, self._record = owner, record
        self._generation = owner._generation
        self._home, self._uid, self._gid, self._authority = home, uid, gid, authority
        self._used = self._in_progress = self._unknown = False
        self._rechecked = False

    def __repr__(self):
        return "<NativePresentationReadClaim private>"

    def __copy__(self):
        raise TypeError("native read claim cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("native read claim cannot be copied")

    def __reduce__(self):
        raise TypeError("native read claim cannot be serialized")


class NativeReadRegistry:
    """One listener generation's file-read identity registry, not its auth API.

    `issuer` is the private actual service, not a request value or boolean.
    `_issue` may be called only after that service's real native policy/home read.
    Forgetting a file claim never settles a thread, writer or capacity slot.
    """

    def __init__(self, issuer: object, generation: object, clock: Callable[[], float]):
        if issuer is None or generation is None or type(issuer) is bool or type(generation) is bool:
            raise NativeSourceError()
        self._issuer, self._generation, self._clock = issuer, generation, clock
        self._lock = Lock()
        self._records: dict[int, _Operation] = {}
        self._retired = False

    def __repr__(self):
        return "<NativePresentationReadRegistry private>"

    def _issuer_check(self, issuer):
        if issuer is not self._issuer:
            raise NativeSourceError()

    def _now(self):
        try:
            now = self._clock()
        except BaseException:
            raise NativeSourceError() from None
        if type(now) is not float or not math.isfinite(now) or now < 0:
            raise NativeSourceError()
        return now

    def _begin(self, issuer, operation, profile, deadline):
        self._issuer_check(issuer)
        now = self._now()
        if (
            type(profile) is not str
            or not 0 < len(profile) <= 64
            or _PROFILE.fullmatch(profile) is None
            or type(deadline) is not float
            or not now < deadline <= now + 2.0
        ):
            raise NativeSourceError()
        with self._lock:
            if self._retired or id(operation) in self._records or len(self._records) >= MAX_RECORDS:
                raise NativeSourceError()
            self._records[id(operation)] = _Operation(operation, profile, deadline)

    def _issue(self, issuer, operation, *, home, uid, gid, authority):
        self._issuer_check(issuer)
        try:
            home_bytes = home.encode("utf-8") if type(home) is str else b""
        except UnicodeError:
            raise NativeSourceError() from None
        if (
            type(home) is not str
            or not home.startswith("/")
            or home == "/"
            or "\0" in home
            or len(home_bytes) > 4096
            or home.endswith("/")
            or len(home.split("/")) > 32
            or any(part in ("", ".", "..") for part in home.split("/")[1:])
            or type(uid) is not int
            or uid < 0
            or type(gid) is not int
            or gid < 0
            or authority is None
            or type(authority) in (bool, str, int, float, bytes, bytearray, dict, list, tuple)
        ):
            raise NativeSourceError()
        now = self._now()
        with self._lock:
            record = self._records.get(id(operation))
            if (
                self._retired
                or record is None
                or record.original is not operation
                or not record.active
                or now >= record.deadline
                or record.claim is not None
            ):
                raise NativeSourceError()
            claim = NativeReadClaim(self, record, home, uid, gid, authority)
            record.binding = (home, uid, gid, authority)
            record.claim = claim
            return claim

    def _check(self, claim):
        if (
            type(claim) is not NativeReadClaim
            or claim._owner is not self
            or type(claim._record) is not _Operation
        ):
            raise NativeSourceError()
        now = self._now()
        with self._lock:
            record = self._records.get(id(claim._record.original))
            if (
                self._retired
                or record is not claim._record
                or record.claim is not claim
                or not record.active
                or now >= record.deadline
                or claim._unknown
                or claim._generation is not self._generation
                or type(record.binding) is not tuple
                or len(record.binding) != 4
                or claim._home is not record.binding[0]
                or type(claim._uid) is not int
                or claim._uid != record.binding[1]
                or type(claim._gid) is not int
                or claim._gid != record.binding[2]
                or claim._authority is not record.binding[3]
            ):
                raise NativeSourceError()
            return record.profile, record.deadline, *record.binding[:3]

    def _start_read(self, claim):
        self._check(claim)
        with self._lock:
            if claim._used or not claim._record.active or self._retired:
                raise NativeSourceError()
            claim._used = claim._in_progress = True

    def _end_read(self, claim, *, unknown):
        # Cleanup is permitted after deadline/retirement; it cannot mint reads.
        if type(unknown) is not bool:
            raise NativeSourceError()
        if (
            type(claim) is not NativeReadClaim
            or claim._owner is not self
            or type(claim._record) is not _Operation
        ):
            raise NativeSourceError()
        with self._lock:
            if (
                self._records.get(id(claim._record.original)) is not claim._record
                or claim._record.claim is not claim
                or not claim._in_progress
            ):
                raise NativeSourceError()
            claim._unknown |= unknown
            claim._in_progress = False

    def _start_recheck(self, claim):
        self._check(claim)
        with self._lock:
            if (
                not claim._used
                or claim._in_progress
                or claim._rechecked
                or not claim._record.active
                or self._retired
            ):
                raise NativeSourceError()
            claim._rechecked = claim._in_progress = True

    def _retire(self, issuer, operation=None):
        self._issuer_check(issuer)
        with self._lock:
            if operation is None:
                self._retired = True
                for record in self._records.values():
                    record.active = False
            else:
                record = self._records.get(id(operation))
                if record is not None and record.original is operation:
                    record.active = False

    def _forget_closed(self, issuer, operation):
        self._issuer_check(issuer)
        with self._lock:
            record = self._records.get(id(operation))
            if record is None or record.original is not operation or record.active:
                raise NativeSourceError()
            claim = record.claim
            if claim is not None and (claim._in_progress or claim._unknown):
                raise NativeSourceError()
            del self._records[id(operation)]
