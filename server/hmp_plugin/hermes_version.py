"""Hermes version evidence and the per-feature minimum floors (owner policy 2026-10-01).

Pure and offline: stdlib only, file reads only. This module never imports, executes, evaluates
or compiles Hermes code and never starts a subprocess; `ast.parse` is the only parser used on
Hermes source, and only to read two literal strings.

A Hermes install declares its version in one of three places, tried in this fixed order (the first
valid one wins, matching Hermes's own `get_version_info`, where the install stamp is authoritative):

1. `<root>/install-stamp.json` `baseVersion` (semver; read as UTF-8 with an optional BOM),
2. `hermes_cli/__init__.py` module-level `__version__ = "<semver>"` (a literal assignment),
3. `hermes_cli/__init__.py` module-level `__release_date__ = "<calendar version>"`.

The stamp wins over the literal by decision, not by taking the larger of the two. A missing,
oversized, malformed or placeholder stamp is skipped.

`0.0.0` is Hermes's own placeholder and counts as absent, as does anything that is not a plain
`MAJOR.MINOR.PATCH`. A version that cannot be determined is `UNKNOWN`. Unknown is never "old":
only a version that declares itself below a floor is refused, and every other version is attempted
subject to the real dependency and security checks.

Semver is compared only to a floor's semver and calendar versions only to its calendar floor. HMP
never converts between the two schemes at runtime; both columns of every floor come from
`KNOWN_RELEASES`, the verified release table.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

_INIT_RELATIVE = Path("hermes_cli") / "__init__.py"
_STAMP_RELATIVE = Path("install-stamp.json")
_MAX_INIT_BYTES = 256 * 1024
_MAX_STAMP_BYTES = 64 * 1024

_SEMVER_RE = re.compile(r"(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})")
_CALVER_RE = re.compile(r"(20\d\d)\.([1-9]|1[0-2])\.([1-9]|[12]\d|3[01])(?:\.([1-9]\d{0,2}))?")

SemverTuple = tuple[int, int, int]
CalverTuple = tuple[int, int, int, int]


class VersionSource(StrEnum):
    LITERAL = "literal"
    STAMP = "stamp"
    RELEASE_DATE = "release_date"
    UNKNOWN = "unknown"


class Scheme(StrEnum):
    SEMVER = "semver"
    CALVER = "calver"
    UNKNOWN = "unknown"


class FloorStatus(StrEnum):
    BELOW_FLOOR = "below_floor"
    AT_OR_ABOVE = "at_or_above"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HermesVersion:
    """The parsed version of an install. `parts` is empty exactly when the scheme is unknown."""

    scheme: Scheme
    parts: tuple[int, ...]
    source: VersionSource

    @property
    def known(self) -> bool:
        return self.scheme is not Scheme.UNKNOWN

    @property
    def text(self) -> str:
        """The normalized value for display (`unknown` when it could not be determined)."""
        if self.scheme is Scheme.SEMVER:
            return ".".join(str(p) for p in self.parts)
        if self.scheme is Scheme.CALVER:
            year, month, day, patch = self.parts
            return f"{year}.{month}.{day}" + (f".{patch}" if patch else "")
        return "unknown"


UNKNOWN_VERSION = HermesVersion(Scheme.UNKNOWN, (), VersionSource.UNKNOWN)


@dataclass(frozen=True)
class Floor:
    """One feature floor: the same release expressed in both version schemes."""

    semver: SemverTuple
    calver: CalverTuple

    @property
    def semver_text(self) -> str:
        return ".".join(str(p) for p in self.semver)

    @property
    def calver_text(self) -> str:
        year, month, day, patch = self.calver
        return f"{year}.{month}.{day}" + (f".{patch}" if patch else "")


# Verified (semver, calendar) release pairs, oldest first (read from each release's own
# `hermes_cli/__init__.py`). Strictly increasing in both schemes; a floor must be one of these rows.
KNOWN_RELEASES: tuple[Floor, ...] = (
    Floor((0, 21, 0), (2026, 8, 31, 0)),
    Floor((0, 21, 1), (2026, 9, 7, 0)),
    Floor((0, 21, 2), (2026, 9, 11, 0)),
    Floor((0, 21, 3), (2026, 9, 14, 0)),
    Floor((0, 21, 4), (2026, 9, 21, 0)),
    Floor((0, 21, 5), (2026, 9, 24, 0)),
)

_READ_FLOOR = KNOWN_RELEASES[4]  # oldest release where the read matrix passed
_WRITE_FLOOR = KNOWN_RELEASES[5]  # oldest release containing the tested send/jobs/model APIs

# Feature name (the `compat.Feature` values) -> floor. Kept as strings so this module stays free of
# any other plugin module.
FEATURE_FLOORS: dict[str, Floor] = {
    "read": _READ_FLOOR,
    "session_browsing": _READ_FLOOR,
    "send": _WRITE_FLOOR,
    "jobs": _WRITE_FLOOR,
    "model": _WRITE_FLOOR,
    "approvals": _WRITE_FLOOR,  # spec 034: the send floor; no notifier floor is claimed
    "phone_chat": _WRITE_FLOOR,
    # Local media (spec 011, D-M3): the inherited write floor, where its three native probe rows
    # already sit in the send table. A host-local read feature: it never depends on send.
    "local_media": _WRITE_FLOOR,
}


def parse_semver(value: object) -> SemverTuple | None:
    """`MAJOR.MINOR.PATCH` only. The `0.0.0` placeholder, pre-releases and local tags give None."""
    if not isinstance(value, str):
        return None
    match = _SEMVER_RE.fullmatch(value)
    if match is None:
        return None
    parts = (int(match[1]), int(match[2]), int(match[3]))
    return None if parts == (0, 0, 0) else parts


def parse_calver(value: object) -> CalverTuple | None:
    if not isinstance(value, str):
        return None
    match = _CALVER_RE.fullmatch(value)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3]), int(match[4] or 0))


def _read_capped(path: Path, cap: int) -> bytes | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError:
        return None
    return None if len(data) > cap else data


def _init_literals(root: Path) -> tuple[str | None, str | None]:
    """`(__version__, __release_date__)` literals from the module level of `hermes_cli/__init__`.

    Only an `Assign` with exactly one `Name` target and a `str` constant value counts. An
    annotation without a value is absent. Any size, decode or syntax error means both are absent.
    """
    data = _read_capped(root / _INIT_RELATIVE, _MAX_INIT_BYTES)
    if data is None:
        return None, None
    try:
        tree = ast.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError, ValueError, RecursionError, MemoryError):
        return None, None
    found: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"__version__", "__release_date__"}
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found[node.targets[0].id] = node.value.value
    return found.get("__version__"), found.get("__release_date__")


def _stamp_base_version(root: Path) -> str | None:
    data = _read_capped(root / _STAMP_RELATIVE, _MAX_STAMP_BYTES)
    if data is None:
        return None
    try:
        raw = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    value = raw.get("baseVersion") if isinstance(raw, dict) else None
    return value if isinstance(value, str) else None


def read_hermes_version(root: Path) -> HermesVersion:
    """The version of the Hermes install at `root`, from file reads only. Never raises."""
    try:
        semver = parse_semver(_stamp_base_version(root))
        if semver is not None:
            return HermesVersion(Scheme.SEMVER, semver, VersionSource.STAMP)
        literal, release_date = _init_literals(root)
        semver = parse_semver(literal)
        if semver is not None:
            return HermesVersion(Scheme.SEMVER, semver, VersionSource.LITERAL)
        calver = parse_calver(release_date)
        if calver is not None:
            return HermesVersion(Scheme.CALVER, calver, VersionSource.RELEASE_DATE)
    except Exception:
        return UNKNOWN_VERSION
    return UNKNOWN_VERSION


def classify(version: HermesVersion, floor: Floor) -> FloorStatus:
    """Only a version that declares itself older than `floor` is BELOW_FLOOR. Newer, unreleased
    and unknown versions are never refused on version grounds."""
    if version.scheme is Scheme.SEMVER:
        return (
            FloorStatus.BELOW_FLOOR if version.parts < floor.semver else FloorStatus.AT_OR_ABOVE
        )
    if version.scheme is Scheme.CALVER:
        return (
            FloorStatus.BELOW_FLOOR if version.parts < floor.calver else FloorStatus.AT_OR_ABOVE
        )
    return FloorStatus.UNKNOWN
