"""Request-scoped active-history batch scan for host-local generated images (C6a).

INERT: no production module imports this one, and nothing at start-up loads it.
It imports the accepted scanner and the accepted candidate module (for `derive_flat_name`) at
module scope, plus the standard library. It does no I/O of its own: it reads only through the
native `get_active_message_ids` and `get_messages` calls the accepted scanner uses, and it never
touches a file, a stat, a socket, a log or a cache.

It answers one question for up to 128 selected rows at once: which of these `(tool row id, canonical
tool digest)` pairs still sit in the *current active set* of one eligible tip, linked strictly as
the accepted scanner links them, with the digest equal and the `image` lexically under the captured
home? One bracketed pass serves every selector, so the native call count does not grow with the
selector count. The accepted single scanner is unchanged and stays the fetch-time check.

Authority: none. The caller binds the same eligible database, home and scope the selectors came
from and supplies `current_tip`; this module adds no input profile or session authority.

Accounting: one shared base budget (the scanner's 4 MiB) is charged exactly as the scanner charges
role, name, call id and declarations, with no selected row, so no candidate content enters it. A
selected row's content is bounded to 64 KiB and checked for lone surrogates before it is retained
or parsed. Each candidate is then judged against the base plus *only its own* content charge. This
equals the single scanner's budget outcome for that row; contents are never summed together.
Retained content is at most 128 bounded strings until the verdicts are made. Not claimed: a
single-instant snapshot, ABA detection, native allocation bounds, or a time bound.

A bracket failure (tip, active ids, paging, any global malformation) refuses every selector with
that closed reason. Otherwise candidates are independent: one refusal never changes another's
verdict. There is no backfill and no selector is ever added or replaced. Nothing here uses an
exception as a success signal, and no value from the caller or the database leaves it: the result
holds only each selector's row id, a closed reason, the accepted row ids and bounded counts.
"""

from __future__ import annotations

import hmac
from typing import Any, Final

from . import local_media_active_scan as _scan
from . import local_media_candidate as _candidate

MAX_SELECTORS: Final = 128
DIGEST_BYTES: Final = 32

OK: Final = _scan.OK
INVALID_ARGUMENT: Final = _scan.INVALID_ARGUMENT
DIGEST_MISMATCH: Final = "digest_mismatch"
LEXICAL_MISMATCH: Final = "lexical_mismatch"
REASONS: Final = frozenset(_scan.REASONS | {DIGEST_MISMATCH, LEXICAL_MISMATCH})

Seam = _scan.Seam


class _Closed:
    """Immutable plain slots object with a fixed text and no serialization or copy."""

    __slots__ = ()

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


def _initialized(obj: _Closed) -> bool:
    """True when any slot is already set, so a constructor never rewrites an existing result."""
    for cls in type(obj).__mro__:
        for slot in getattr(cls, "__slots__", ()):
            try:
                object.__getattribute__(obj, slot)
            except AttributeError:
                continue
            return True
    return False


class BatchVerdict(_Closed):
    """One selector's row id and the closed reason: `ok` or a refusal. Nothing else."""

    __slots__ = ("_reason", "_row_id")

    def __init__(self, row_id: int, reason: str) -> None:
        if _initialized(self):
            raise TypeError("already initialized")
        if type(row_id) is not int or row_id < 1 or reason not in REASONS:
            raise ValueError("invalid verdict")
        object.__setattr__(self, "_row_id", row_id)
        object.__setattr__(self, "_reason", reason)

    @property
    def row_id(self) -> int:
        return self._row_id

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def accepted(self) -> bool:
        return self._reason == OK

    def __repr__(self) -> str:
        return f"BatchVerdict(reason={self._reason})"

    __str__ = __repr__


_STAT_NAMES: Final = ("pages", "rows", "budget_used", "declared")


class ActiveBatchResult(_Closed):
    """The closed outcome of one batch: a top-level reason, per-selector verdicts in selector
    order, the accepted row ids in selector order, and bounded counts.

    `reason` is `ok` when the bracketed pass completed (individual selectors may still be
    refused), `invalid_argument` for a bad input shape (no verdicts), else the bracket failure
    that refused every selector."""

    __slots__ = ("_accepted", "_reason", "_stats", "_verdicts")

    def __init__(
        self,
        reason: str,
        verdicts: tuple[BatchVerdict, ...],
        stats: tuple[int, int, int, int],
    ) -> None:
        if _initialized(self):
            raise TypeError("already initialized")
        if reason not in REASONS or type(verdicts) is not tuple:
            raise ValueError("invalid result")
        if any(type(v) is not BatchVerdict for v in verdicts):
            raise ValueError("invalid result")
        if type(stats) is not tuple or len(stats) != len(_STAT_NAMES):
            raise ValueError("invalid result")
        if any(type(n) is not int or n < 0 for n in stats):
            raise ValueError("invalid result")
        object.__setattr__(self, "_reason", reason)
        object.__setattr__(self, "_verdicts", verdicts)
        object.__setattr__(self, "_accepted", tuple(v.row_id for v in verdicts if v.accepted))
        object.__setattr__(self, "_stats", stats)

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def ok(self) -> bool:
        return self._reason == OK

    @property
    def verdicts(self) -> tuple[BatchVerdict, ...]:
        return self._verdicts

    @property
    def accepted(self) -> tuple[int, ...]:
        return self._accepted

    @property
    def stats(self) -> tuple[tuple[str, int], ...]:
        return tuple(zip(_STAT_NAMES, self._stats, strict=True))

    def __repr__(self) -> str:
        return (
            f"ActiveBatchResult(reason={self._reason}, candidates={len(self._verdicts)},"
            f" accepted={len(self._accepted)})"
        )

    __str__ = __repr__

    def report(self) -> dict[str, Any]:
        """Closed metadata only: reason and counts. No row id, digest, path or content."""
        return {
            "reason": self._reason,
            "candidates": len(self._verdicts),
            "accepted": len(self._accepted),
            **dict(self.stats),
        }


# --------------------------------------------------------------------------- inputs


def _selector_pairs(selectors: Any) -> tuple[tuple[int, bytes], ...]:
    """The validated selectors, else a closed invalid-argument refusal."""
    if type(selectors) is not tuple or not 1 <= len(selectors) <= MAX_SELECTORS:
        raise _scan._Refuse(INVALID_ARGUMENT)
    seen: set[int] = set()
    for item in selectors:
        if type(item) is not tuple or len(item) != 2:
            raise _scan._Refuse(INVALID_ARGUMENT)
        row_id, digest = item
        if (
            type(row_id) is not int
            or row_id < 1
            or row_id in seen
            or type(digest) is not bytes
            or len(digest) != DIGEST_BYTES
        ):
            raise _scan._Refuse(INVALID_ARGUMENT)
        seen.add(row_id)
    return selectors


def _check_args(tip: Any, home: Any, current_tip: Any) -> None:
    _scan._valid_args(tip, 1, current_tip)
    if not _candidate._valid_home(home):
        raise _scan._Refuse(INVALID_ARGUMENT)


# --------------------------------------------------------------------------- the batch


class _Captured:
    """One selected row's bounded values, or the refusal for its own content."""

    __slots__ = ("reason", "selected", "weight")

    def __init__(self) -> None:
        self.reason: str | None = None
        self.selected: dict[str, Any] | None = None
        self.weight = 0


def _capture(row: Any, row_id: int) -> _Captured:
    """Bound and surrogate-check one selected row's content BEFORE it is retained or parsed.

    The row already passed the shared `_inspect_row`, so role/name/call id are charged and
    bounded in the base. Only a tool row yields a selection (as in the scanner)."""
    captured = _Captured()
    if type(row) is not dict:  # native rows are decoded dicts; no second read of another Mapping
        captured.reason = _scan.PAGE_INVALID
        return captured
    role = row.get("role")
    if type(role) is not str or role != "tool":
        return captured  # not a tool row: `_link` refuses it as not a tool
    name, call_id, content = row.get("tool_name"), row.get("tool_call_id"), row.get("content")
    if type(content) is str:
        try:
            weight = _scan.utf8_weight(content, _scan.MAX_RESULT_BYTES)
        except _scan._Refuse as refusal:
            captured.reason = refusal.reason
            return captured
        if weight > _scan.MAX_RESULT_BYTES:
            captured.reason = _scan.RESULT_TOO_LARGE
            return captured
        captured.weight = weight
    else:
        content = None  # not retained; `_parse_image` refuses a non-str as not a candidate
    captured.selected = {
        "id": row_id,
        "tool_name": name if type(name) is str else None,
        "tool_call_id": call_id if type(call_id) is str else None,
        "content": content,
    }
    return captured


def _bracket(
    db: Any,
    tip: str,
    wanted: frozenset[int],
    current_tip: Any,
    seam: Seam | None,
    base: _scan._State,
    stats: dict[str, int],
) -> tuple[list[int], dict[int, _Captured]]:
    """The accepted scanner's bracket and page loop, capturing only the wanted rows."""
    _scan._check_tip(current_tip, tip)
    if seam:
        seam("ids0", 0)
    ids0 = _scan._read_active_ids(db, tip)
    active = frozenset(ids0)
    captures: dict[int, _Captured] = {}
    if wanted & active:  # with none active, paging is skipped; the bracket reads stay
        cursor = 0
        while True:
            if seam:
                seam("page", stats["pages"])
            page = _scan._read(db.get_messages, tip, after_id=cursor, limit=_scan.PAGE_LIMIT)
            if type(page) is not list or len(page) > _scan.PAGE_LIMIT:
                raise _scan._Refuse(_scan.PAGE_INVALID)
            stats["pages"] += 1
            for row in page:
                row_id = _scan._inspect_row(row, base)
                if stats["rows"] >= len(ids0) or row_id != ids0[stats["rows"]] or row_id <= cursor:
                    raise _scan._Refuse(_scan.ROWS_CHANGED)
                stats["rows"] += 1
                cursor = row_id
                if row_id in wanted:
                    captures[row_id] = _capture(row, row_id)
            short = len(page) < _scan.PAGE_LIMIT
            del page  # the native page is dropped before the next read
            if short:
                break
        if stats["rows"] != len(ids0):
            raise _scan._Refuse(_scan.ROWS_CHANGED)
    if seam:
        seam("ids1", 0)
    if _scan._read_active_ids(db, tip, _scan.ROWS_CHANGED) != ids0:
        raise _scan._Refuse(_scan.ROWS_CHANGED)
    _scan._check_tip(current_tip, tip)
    return ids0, captures


def _judge(
    tip: str,
    home: str,
    row_id: int,
    digest: bytes,
    active: frozenset[int],
    base: _scan._State,
    captured: _Captured | None,
) -> str:
    """One selector's closed reason. Reads only the shared base and this selector's own capture."""
    if row_id not in active:
        return _scan.SELECTED_NOT_ACTIVE
    if captured is None:  # unreachable after a completed pass: every active wanted row is captured
        return _scan.ROWS_CHANGED
    if captured.reason is not None:
        return captured.reason
    budget = _scan._Budget(base.budget.limit)
    budget.used = base.budget.used
    own = _scan._State(
        0,
        budget,
        base.declared,
        base.tool_counts,
        base.assistant_digests,
        base.declared_total,
        captured.selected,
    )
    try:
        if captured.selected is not None and type(captured.selected["content"]) is str:
            budget.charge(captured.weight + _scan.NODE_COST)  # only this candidate's content
        claim = _scan._link(own, tip, [])  # the claim's own id tuple is never used here
    except _scan._Refuse as refusal:
        return refusal.reason
    if not hmac.compare_digest(claim.tool_digest, digest):
        return DIGEST_MISMATCH
    if _candidate.derive_flat_name(claim.image, home) is None:
        return LEXICAL_MISMATCH
    return OK


def scan_active_batch(
    db: Any,
    tip: str,
    selectors: tuple[tuple[int, bytes], ...],
    *,
    home: str,
    current_tip: Any,
    seam: Seam | None = None,
) -> ActiveBatchResult:
    """Judge every `(tool row id, tool digest)` selector against the active set of `tip`.

    `seam(phase, index)` is the scanner's test-only seam (`"ids0"`, `"page"` with the page index,
    `"ids1"`), called immediately before each native read; production passes `None` and a seam
    exception is deliberately not wrapped. See the module docstring."""
    stats = {"pages": 0, "rows": 0}
    base: _scan._State | None = None
    pairs: tuple[tuple[int, bytes], ...] = ()
    try:
        _check_args(tip, home, current_tip)
        pairs = _selector_pairs(selectors)
        base = _scan._State(0, _scan._Budget())
        ids0, captures = _bracket(
            db, tip, frozenset(r for r, _ in pairs), current_tip, seam, base, stats
        )
    except _scan._Refuse as refusal:
        reason = refusal.reason
        verdicts = (
            ()
            if reason == INVALID_ARGUMENT
            else tuple(BatchVerdict(row_id, reason) for row_id, _ in pairs)
        )
        return ActiveBatchResult(reason, verdicts, _counts(stats, base))
    active = frozenset(ids0)
    verdicts = tuple(
        BatchVerdict(row_id, _judge(tip, home, row_id, digest, active, base, captures.get(row_id)))
        for row_id, digest in pairs
    )
    return ActiveBatchResult(OK, verdicts, _counts(stats, base))


def _counts(stats: dict[str, int], base: _scan._State | None) -> tuple[int, int, int, int]:
    used = base.budget.used if base is not None else 0
    declared = base.declared_total if base is not None else 0
    return (stats["pages"], stats["rows"], used, declared)
