"""Bounded extraction of local image candidates from one returned page of native rows (LM-8).

INERT: nothing at start-up, in a route or in `reads.py` imports this module; the bridge loads it
only inside its unused media-aware read methods.
It imports only the accepted result parser, the accepted flat-name grammar, the accepted scanner's
digest and id helpers, and the carrier module. It does no I/O of any kind.

A candidate is **not authority**. This module answers one question per row: did this strict
`image_generate` tool row pass the 64 KiB bound and the one accepted parser, and does its `image`
lexically sit directly under `<home>/cache/images/`? If so the row is a `MediaCandidate` holding
only the row id and the scanner's canonical tool digest. The image string, the flat name, the home
and the raw content are used for that pass/fail test and dropped; none is carried or logged. A
later handler must rescan the active history and compare the row id and digest before it mints.

Derivation is purely lexical: an exact-`str` prefix test against the home string the caller
captured, then the accepted flat-name grammar. There is no `Path`, `os`, `stat`, `resolve` or
normalization, so a differently spelled home refuses. Refusals are `None`; nothing here raises to
a caller and nothing logs.

Like the modules it uses, this one needs Python 3.11+ and is imported by nothing at start-up.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from . import local_media_active_scan as _scan
from .local_media_file_safety import classify_candidate
from .local_media_result import parse_image_result
from .local_media_sidecar import (
    MAX_CANDIDATES_PER_RESPONSE,
    MAX_ROWS,
    MediaCandidate,
)

IMAGE_CACHE_SUFFIX: Final = "/cache/images/"
TOOL_ROLE: Final = "tool"
IMAGE_TOOL: Final = "image_generate"


def _valid_home(home: object) -> bool:
    return type(home) is str and bool(home) and "\0" not in home


def _positive_id(value: object) -> bool:
    return type(value) is int and value >= 1


def derive_flat_name(image: str, home: str) -> str | None:
    """The one flat cache name directly under `<home>/cache/images/`, else `None`. Lexical only."""
    if type(image) is not str or not _valid_home(home):
        return None
    prefix = home + IMAGE_CACHE_SUFFIX
    if not image.startswith(prefix):
        return None
    name = image[len(prefix) :]
    return name if classify_candidate(name) is None else None


def raw_tool_candidate(item: Mapping[object, object], home: str) -> MediaCandidate | None:
    """The candidate for one native row, or `None`. Total: it never raises and never logs."""
    try:
        if not isinstance(item, Mapping):
            return None
        role, name = item.get("role"), item.get("tool_name")
        if type(role) is not str or role != TOOL_ROLE:
            return None
        if type(name) is not str or name != IMAGE_TOOL:
            return None
        row_id = item.get("id")
        if not _positive_id(row_id):
            return None
        call_id = item.get("tool_call_id")
        if not _scan._valid_id(call_id):
            return None
        content = item.get("content")
        if type(content) is not str:
            return None
        image = parse_image_result(content)  # the one bounded, accepted parse
        if type(image) is not str or derive_flat_name(image, home) is None:
            return None
        digest = _scan._tool_digest(row_id, IMAGE_TOOL, call_id, content)
        return MediaCandidate(row_id, digest)
    except Exception:  # nothing private may escape; no chaining, no logging
        return None


def _attempt_id(row: object) -> int | None:
    """The row id if this row would count as an `image_generate` attempt, else `None`."""
    try:
        if not isinstance(row, Mapping):
            return None
        role, name, row_id = row.get("role"), row.get("tool_name"), row.get("id")
        if type(role) is not str or role != TOOL_ROLE:
            return None
        if type(name) is not str or name != IMAGE_TOOL or not _positive_id(row_id):
            return None
        return row_id  # type: ignore[return-value]
    except Exception:
        return None


def _row_id(row: object) -> int:
    """The row's positive id for ordering, or 0 (sorted last, never a candidate)."""
    try:
        row_id = row.get("id") if isinstance(row, Mapping) else None
        return row_id if _positive_id(row_id) else 0  # type: ignore[return-value]
    except Exception:
        return 0


def collect_candidates(
    raw_rows: Sequence[object], home: str, returned_tool_ids: frozenset[int]
) -> tuple[MediaCandidate, ...]:
    """Candidates among the newest `image_generate` rows of one returned page, newest first.

    Rows are ordered here by positive row id, newest first, because the page order is not trusted.
    A repeated positive native row id makes the page ambiguous and yields no candidates.
    Only ids in `returned_tool_ids` are considered. At most
    `MAX_CANDIDATES_PER_RESPONSE` rows are attempted; a rejected attempt is not replaced by an
    older row. An invalid argument shape or home yields `()`.
    """
    try:
        if type(raw_rows) not in (list, tuple) or len(raw_rows) > MAX_ROWS:
            return ()
        if type(returned_tool_ids) is not frozenset or len(returned_tool_ids) > MAX_ROWS:
            return ()
        if not all(_positive_id(i) for i in returned_tool_ids) or not _valid_home(home):
            return ()
        # A native page with two rows claiming one id has no unique returned-row identity.
        # Refuse the whole optional media sidecar before parsing any result; the ordinary
        # text read retains its existing behavior.  This is bounded by MAX_ROWS above.
        raw_ids = [_row_id(row) for row in raw_rows]
        positive_ids = [row_id for row_id in raw_ids if row_id > 0]
        if len(positive_ids) != len(set(positive_ids)):
            return ()
        ordered = sorted(raw_rows, key=_row_id, reverse=True)
        seen: set[int] = set()
        found: list[MediaCandidate] = []
        attempts = 0
        for row in ordered:
            row_id = _attempt_id(row)
            if row_id is None or row_id not in returned_tool_ids or row_id in seen:
                continue
            seen.add(row_id)
            if attempts >= MAX_CANDIDATES_PER_RESPONSE:
                break
            attempts += 1
            candidate = raw_tool_candidate(row, home)  # type: ignore[arg-type]
            if candidate is not None:
                found.append(candidate)
        return tuple(found)
    except Exception:
        return ()
