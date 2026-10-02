"""The one bounded result parser for local image delivery, shared by mint and fetch.

It wraps the accepted scanner predicate (`local_media_active_scan._parse_image`) and adds the
byte bound that predicate expects its caller to have applied: the exact `str` is measured against
the raw 64 KiB UTF-8 limit *before* `json.loads` sees it. It is not a second parser.

Nothing here logs, and no refusal carries the raw body, an exception, or its text. The success
value is the candidate `image` string, which is private: keep it out of wire bodies, logs and
`repr`s.

Like the scanner it uses, this module needs Python 3.11+ and is imported by nothing at start-up.
"""

from __future__ import annotations

from enum import Enum

from . import local_media_active_scan as _scan

MAX_RESULT_BYTES = _scan.MAX_RESULT_BYTES


class ResultRefusal(Enum):
    """Closed, content-free reasons. `repr` and `str` show only the member name."""

    NOT_CANDIDATE = "result_not_candidate"
    TOO_LARGE = "result_too_large"
    UNAVAILABLE = "result_unavailable"


def parse_image_result(content: object) -> str | ResultRefusal:
    """The candidate `image` of a strictly successful `image_generate` result, else a refusal."""
    try:
        if type(content) is not str:
            return ResultRefusal.NOT_CANDIDATE
        # Every character is at least one UTF-8 byte, so this refuses without scanning the string.
        if len(content) > MAX_RESULT_BYTES:
            return ResultRefusal.TOO_LARGE
        if _scan.utf8_weight(content, MAX_RESULT_BYTES) > MAX_RESULT_BYTES:
            return ResultRefusal.TOO_LARGE
        return _scan._parse_image(content)  # the one accepted predicate
    except _scan._Refuse as refusal:
        if refusal.reason == _scan.RESULT_TOO_LARGE:
            return ResultRefusal.TOO_LARGE
        return ResultRefusal.NOT_CANDIDATE
    except Exception:  # nothing private may escape or be logged
        return ResultRefusal.UNAVAILABLE
