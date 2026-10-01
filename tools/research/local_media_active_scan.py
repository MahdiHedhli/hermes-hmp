"""Active-set scan/link/recheck research module for host-local generated images (not product).

Test tooling: `server/hmp_plugin` never imports it. It answers one question for a caller-provided
eligible tip and selected tool row: does the *current active set* of that tip contain exactly one
executing tool row and exactly one outer assistant declaration for the tool row's call ID, in the
native `image_generate` (direct) or one-entry `tool_call {calls: [...]}` bridge shape, with a
successful `image_generate` result? It reads only through the native `SessionDB` methods
`get_active_message_ids(session_id)` and `get_messages(session_id, after_id=, limit=)`; there is no
SQL, copied storage code, producer hook, route, registry, transport or wire shape here.

It does NOT authorize anything. The caller must establish device, profile, conversation and
eligibility freshly before and after (a future HMP concern) and supplies `current_tip`, a callable
returning the tip that eligibility resolves to *now*; it is called before the first read and after
the last one and must always equal `tip`.

Claims made: "no inconsistency observed across the bracketed reads". Not claimed: a single-instant
snapshot, atomicity between reads, a monotonic epoch, or detection of a restore/undo that returns
the same active IDs with different content in rows other than the two selected ones (ABA).

Processing budget (HMP-side, not native allocation): native `get_messages` runs `SELECT *` and
fully materializes and decodes every column of a page before this module sees it, and
`get_active_message_ids` returns every active ID uncapped; both stay inside the trusted-database
boundary the existing text reads already cross. The budget below bounds the work done *here*,
with two known constant-factor exceptions inside that boundary: the active-ID list length is
checked before any element is iterated, but `str.isascii()` in `utf8_weight` scans a whole string
before any early stop, so one very large native or trusted string is scanned once, unbounded.

Deliberately not inspected: `function.arguments` of a direct `image_generate` call and the
`arguments` of each bridge entry (beyond the 64 KiB cap and structure parse for the bridge
wrapper). Linkage rests on the outer call ID plus a strictly successful result, not on arguments.
Availability limit: a provider that reuses call IDs across turns makes every image in that chat
refuse (`duplicate_tool_row` / `declaration_ambiguous`).

Public values (`repr`, `report()`) carry closed reasons, counts and hash prefixes only: never IDs,
content, paths or arguments. `ScanClaim` holds private values and is for the caller's own use.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

PAGE_LIMIT = 128
MAX_ACTIVE_ROWS = 4096
BUDGET_BYTES = 4 * 1024 * 1024
NODE_COST = (
    8  # every inspected value costs at least this, so visits are bounded by the budget
)
MAX_DEPTH = 32
MAX_ID_CHARS = 256
MAX_CALLS_PER_ROW = 64
MAX_CALLS_TOTAL = 4096
MAX_RESULT_BYTES = 64 * 1024
MAX_BRIDGE_ARGS_BYTES = 64 * 1024
MAX_IMAGE_CHARS = 4096
BRIDGE_TOOL = "tool_call"
IMAGE_TOOL = "image_generate"
_CHUNK = 4096

OK = "ok"
INVALID_ARGUMENT = "invalid_argument"
TIP_CHANGED = "tip_changed"
DB_ERROR = "db_error"
ACTIVE_IDS_INVALID = "active_ids_invalid"
TOO_MANY_ROWS = "too_many_rows"
SELECTED_NOT_ACTIVE = "selected_not_active"
PAGE_INVALID = "page_invalid"
ROWS_CHANGED = "rows_changed"
BUDGET_EXCEEDED = "budget_exceeded"
MALFORMED = "malformed"
TOOL_CALLS_UNCERTAIN = "tool_calls_uncertain"
DECLARATION_LIMIT = "declaration_limit"
SELECTED_NOT_TOOL = "selected_not_tool"
TOOL_NAME_MISMATCH = "tool_name_mismatch"
CALL_ID_INVALID = "call_id_invalid"
DUPLICATE_TOOL_ROW = "duplicate_tool_row"
DECLARATION_MISSING = "declaration_missing"
DECLARATION_AMBIGUOUS = "declaration_ambiguous"
ASSISTANT_NOT_BEFORE_TOOL = "assistant_not_before_tool"
BRIDGE_AMBIGUOUS = "bridge_ambiguous"
SHAPE_UNSUPPORTED = "shape_unsupported"
RESULT_TOO_LARGE = "result_too_large"
RESULT_NOT_CANDIDATE = "result_not_candidate"
SELECTED_CHANGED = "selected_changed"

REASONS = frozenset(
    v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, str)
) - {
    BRIDGE_TOOL,
    IMAGE_TOOL,
}


class _Refuse(Exception):  # noqa: N818 - internal control flow carrying a closed reason
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- bounded measuring


def utf8_weight(text: str, stop_after: int | None = None) -> int:
    """UTF-8 byte length of `text` without building a full encoded copy.

    ASCII is measured by `len`; otherwise 4096-character slices are encoded one at a time. A lone
    surrogate (Python strings never hold a *paired* one) raises a malformed refusal. With
    `stop_after` the measurement may stop early once the total exceeds it (the result is then only
    a lower bound greater than `stop_after`)."""
    if text.isascii():
        return len(text)
    total = 0
    for start in range(0, len(text), _CHUNK):
        try:
            total += len(text[start : start + _CHUNK].encode("utf-8"))
        except UnicodeEncodeError:
            raise _Refuse(MALFORMED) from None
        if stop_after is not None and total > stop_after:
            break
    return total


class _Budget:
    __slots__ = ("limit", "used")

    def __init__(self, limit: int = BUDGET_BYTES) -> None:
        self.limit = limit
        self.used = 0

    def charge(self, amount: int) -> None:
        self.used += amount
        if self.used > self.limit:
            raise _Refuse(BUDGET_EXCEEDED)

    def string(self, text: str) -> int:
        weight = utf8_weight(text, self.limit - self.used)
        self.charge(weight + NODE_COST)
        return weight


def _walk(value: Any, budget: _Budget) -> None:
    """Charge every value of a decoded JSON-like structure; refuse other types and deep nesting.

    Iterative (no recursion) and budget-capped, so a huge or hostile structure stops at the
    budget. Depth is the container nesting; the top-level container is depth 1."""
    stack = [iter((value,))]
    while stack:
        try:
            item = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if isinstance(item, str):
            budget.string(item)
        elif item is None or isinstance(item, bool | int | float):
            budget.charge(NODE_COST)
        elif isinstance(item, list | dict):
            if len(stack) > MAX_DEPTH:
                raise _Refuse(MALFORMED)
            budget.charge(NODE_COST)
            if isinstance(item, dict):
                for key in item:
                    if not isinstance(key, str):
                        raise _Refuse(MALFORMED)
                    budget.string(key)
                stack.append(iter(item.values()))
            else:
                stack.append(iter(item))
        else:
            raise _Refuse(MALFORMED)


def _is_exact_int(value: Any) -> bool:
    return type(value) is int


def _valid_id(value: Any) -> bool:
    if type(value) is not str or not 1 <= len(value) <= MAX_ID_CHARS or "\0" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _canonical_digest(parts: list[Any]) -> bytes:
    """SHA-256 of a canonical serialization. Call only after `_walk` accepted the parts."""
    try:
        text = json.dumps(
            parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
    except ValueError:  # e.g. an int beyond the digit limit; closed, no exception text
        raise _Refuse(MALFORMED) from None
    return hashlib.sha256(text.encode("ascii")).digest()


# --------------------------------------------------------------------------- public results


@dataclass(frozen=True, repr=False)
class ScanClaim:
    """Private values the caller needs for `recheck`; never print or log them."""

    tip: str
    active_ids: tuple[int, ...]
    tool_row_id: int
    assistant_row_id: int
    tool_digest: bytes
    assistant_digest: bytes
    image: str
    shape: str

    def __repr__(self) -> str:
        return "ScanClaim(<redacted>)"


@dataclass(frozen=True, repr=False)
class ScanOutcome:
    ok: bool
    reason: str
    claim: ScanClaim | None = None
    stats: Mapping[str, int] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ScanOutcome(ok={self.ok}, reason={self.reason})"

    def report(self) -> dict[str, Any]:
        """Closed metadata only: outcome, shape, counts and 12-hex digest prefixes."""
        data: dict[str, Any] = {"ok": self.ok, "reason": self.reason, **self.stats}
        if self.claim is not None:
            data["shape"] = self.claim.shape
            data["tool_digest"] = self.claim.tool_digest.hex()[:12]
            data["assistant_digest"] = self.claim.assistant_digest.hex()[:12]
        return data


Seam = Callable[[str, int], None]


# --------------------------------------------------------------------------- row inspection


@dataclass
class _Declaration:
    row_id: int
    kind: str  # "outer" or "inner"
    function: str
    entries: tuple[str, ...] | None  # bridge entry names; None when not a bridge call
    legacy: bool


@dataclass
class _State:
    tool_row_id: int
    budget: _Budget
    declared: dict[str, list[_Declaration]] = field(default_factory=dict)
    tool_counts: dict[str, int] = field(default_factory=dict)
    assistant_digests: dict[int, bytes] = field(default_factory=dict)
    declared_total: int = 0
    selected: dict[str, Any] | None = None


def _parse_bridge_arguments(arguments: Any) -> tuple[list[Mapping[str, Any]], bool]:
    if type(arguments) is not str or utf8_weight(arguments, MAX_BRIDGE_ARGS_BYTES) > (
        MAX_BRIDGE_ARGS_BYTES
    ):
        raise _Refuse(TOOL_CALLS_UNCERTAIN)
    try:
        parsed = json.loads(arguments)
    except (ValueError, RecursionError):
        raise _Refuse(TOOL_CALLS_UNCERTAIN) from None
    if type(parsed) is not dict:
        raise _Refuse(TOOL_CALLS_UNCERTAIN)
    if "calls" in parsed:
        entries, legacy = parsed["calls"], False
        if type(entries) is not list or len(entries) > MAX_CALLS_PER_ROW:
            raise _Refuse(TOOL_CALLS_UNCERTAIN)
    elif "name" in parsed:
        entries, legacy = [parsed], True
    else:
        raise _Refuse(TOOL_CALLS_UNCERTAIN)
    for entry in entries:
        if type(entry) is not dict or type(entry.get("name")) is not str:
            raise _Refuse(TOOL_CALLS_UNCERTAIN)
    return entries, legacy


def _inspect_calls(row_id: int, calls: Any, state: _State) -> None:
    """Validate one assistant row's `tool_calls` and record every declared ID.

    Absent calls are `None` (handled by the caller). Anything else must be a non-empty list: a
    stored `[]` is how native represents both an empty list that was never stored and a malformed
    blob, so it carries no linkage information and the artifact is refused globally."""
    if type(calls) is not list or not calls:
        raise _Refuse(TOOL_CALLS_UNCERTAIN)
    _walk(calls, state.budget)
    if len(calls) > MAX_CALLS_PER_ROW:
        raise _Refuse(DECLARATION_LIMIT)
    row_declared = 0
    for call in calls:
        if type(call) is not dict or not _valid_id(call.get("id")):
            raise _Refuse(TOOL_CALLS_UNCERTAIN)
        function = call.get("function")
        name = function.get("name") if type(function) is dict else None
        if not _valid_id(name):
            raise _Refuse(TOOL_CALLS_UNCERTAIN)
        records = [(call["id"], "outer", None, False)]
        entries: tuple[str, ...] | None = None
        if name == BRIDGE_TOOL:
            parsed, legacy = _parse_bridge_arguments(function.get("arguments"))
            entries = tuple(entry["name"] for entry in parsed)
            records[0] = (call["id"], "outer", entries, legacy)
            for entry in parsed:
                for key in ("id", "call_id"):
                    if key in entry:
                        if not _valid_id(entry[key]):
                            raise _Refuse(TOOL_CALLS_UNCERTAIN)
                        records.append((entry[key], "inner", None, legacy))
        row_declared += len(records)
        state.declared_total += len(records)
        if row_declared > MAX_CALLS_PER_ROW or state.declared_total > MAX_CALLS_TOTAL:
            raise _Refuse(DECLARATION_LIMIT)
        for declared_id, kind, bridge_entries, legacy in records:
            state.declared.setdefault(declared_id, []).append(
                _Declaration(row_id, kind, name, bridge_entries, legacy)
            )
    state.assistant_digests[row_id] = _canonical_digest([row_id, "assistant", calls])


def _inspect_row(row: Any, state: _State) -> int:
    if not isinstance(row, Mapping) or not _is_exact_int(row.get("id")):
        raise _Refuse(PAGE_INVALID)
    row_id = row["id"]
    state.budget.charge(NODE_COST)
    role = row.get("role")
    if type(role) is not str:
        raise _Refuse(MALFORMED)
    state.budget.string(role)
    if role == "assistant":
        calls = row.get("tool_calls")
        if calls is not None:
            _inspect_calls(row_id, calls, state)
    elif role == "tool":
        call_id, name = row.get("tool_call_id"), row.get("tool_name")
        if type(call_id) is str:
            state.budget.string(call_id)
            if _valid_id(call_id):
                state.tool_counts[call_id] = state.tool_counts.get(call_id, 0) + 1
        if type(name) is str:
            state.budget.string(name)
        if row_id == state.tool_row_id:
            content = row.get("content")
            if type(content) is str:
                if utf8_weight(content, MAX_RESULT_BYTES) > MAX_RESULT_BYTES:
                    raise _Refuse(RESULT_TOO_LARGE)
                state.budget.string(content)
            state.selected = {
                "id": row_id,
                "tool_name": name,
                "tool_call_id": call_id,
                "content": content,
            }
    return row_id


def _parse_image(content: Any) -> str:
    """The `image` path of an actual successful result object, else a closed refusal."""
    if type(content) is not str:
        raise _Refuse(RESULT_NOT_CANDIDATE)
    try:
        parsed = json.loads(content)
    except (ValueError, RecursionError):
        raise _Refuse(RESULT_NOT_CANDIDATE) from None
    if (
        type(parsed) is not dict
        or parsed.get("success") is not True
        or "error" in parsed
    ):
        raise _Refuse(RESULT_NOT_CANDIDATE)
    image = parsed.get("image")
    if (
        type(image) is not str
        or not 1 <= len(image) <= MAX_IMAGE_CHARS
        or "\0" in image
    ):
        raise _Refuse(RESULT_NOT_CANDIDATE)
    try:
        image.encode("utf-8")
    except UnicodeEncodeError:
        raise _Refuse(RESULT_NOT_CANDIDATE) from None
    return image


def _tool_digest(row_id: int, name: str, call_id: str, content: str) -> bytes:
    return _canonical_digest([row_id, "tool", name, call_id, content])


# --------------------------------------------------------------------------- native reads


def _read(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except (
        Exception
    ):  # closed outcome only: a native error message could carry private text
        raise _Refuse(DB_ERROR) from None


def _read_active_ids(db: Any, tip: str, over: str = TOO_MANY_ROWS) -> list[int]:
    """Native returns the list already allocated and uncapped (trusted boundary); the length cap is
    checked before any element is iterated, with `over` as the refusal for an oversized list."""
    ids = _read(db.get_active_message_ids, tip)
    if type(ids) is not list:
        raise _Refuse(ACTIVE_IDS_INVALID)
    if len(ids) > MAX_ACTIVE_ROWS:
        raise _Refuse(over)
    if not all(_is_exact_int(i) for i in ids):
        raise _Refuse(ACTIVE_IDS_INVALID)
    if any(b <= a for a, b in pairwise(ids)) or (ids and ids[0] < 1):
        raise _Refuse(ACTIVE_IDS_INVALID)
    return ids


def _check_tip(current_tip: Callable[[], str], tip: str) -> None:
    try:
        now = current_tip()
    except Exception:  # closed outcome only: the callback's error text could carry private data
        raise _Refuse(TIP_CHANGED) from None
    if type(now) is not str or now != tip:  # exact str first: no foreign __eq__/__ne__ runs
        raise _Refuse(TIP_CHANGED)


def _valid_args(tip: Any, row_id: Any, current_tip: Any) -> None:
    if (
        type(tip) is not str
        or not tip
        or not _is_exact_int(row_id)
        or row_id < 1
        or not callable(current_tip)
    ):
        raise _Refuse(INVALID_ARGUMENT)


# --------------------------------------------------------------------------- scan and recheck


def scan_active_set(
    db: Any,
    tip: str,
    tool_row_id: int,
    *,
    current_tip: Callable[[], str],
    seam: Seam | None = None,
) -> ScanOutcome:
    """Scan the whole active set of `tip` and link `tool_row_id`; see the module docstring.

    `seam(phase, index)` is a test seam called immediately before each native read
    (`"ids0"`, `"page"` with the page index, `"ids1"`); the tip callback is the other seam. The
    seam is test-only (production passes `None`) and its exceptions are deliberately not wrapped."""
    stats = {"pages": 0, "rows": 0, "budget_used": 0, "declared": 0}
    state: _State | None = None
    try:
        _valid_args(tip, tool_row_id, current_tip)
        state = _State(tool_row_id, _Budget())
        claim = _scan(db, tip, tool_row_id, current_tip, seam, state, stats)
    except _Refuse as refusal:
        return ScanOutcome(False, refusal.reason, None, _finish(stats, state))
    return ScanOutcome(True, OK, claim, _finish(stats, state))


def _finish(stats: dict[str, int], state: _State | None) -> dict[str, int]:
    if state is not None:
        stats["budget_used"] = state.budget.used
        stats["declared"] = state.declared_total
    return stats


def _scan(
    db: Any,
    tip: str,
    tool_row_id: int,
    current_tip: Callable[[], str],
    seam: Seam | None,
    state: _State,
    stats: dict[str, int],
) -> ScanClaim:
    _check_tip(current_tip, tip)
    if seam:
        seam("ids0", 0)
    ids0 = _read_active_ids(db, tip)
    if tool_row_id not in ids0:
        raise _Refuse(SELECTED_NOT_ACTIVE)
    cursor = 0
    while True:
        if seam:
            seam("page", stats["pages"])
        page = _read(db.get_messages, tip, after_id=cursor, limit=PAGE_LIMIT)
        if type(page) is not list or len(page) > PAGE_LIMIT:
            raise _Refuse(PAGE_INVALID)
        stats["pages"] += 1
        for row in page:
            row_id = _inspect_row(row, state)
            if (
                stats["rows"] >= len(ids0)
                or row_id != ids0[stats["rows"]]
                or row_id <= cursor
            ):
                raise _Refuse(ROWS_CHANGED)
            stats["rows"] += 1
            cursor = row_id
        short = len(page) < PAGE_LIMIT
        del page  # the native page is dropped before the next read
        if short:
            break
    if stats["rows"] != len(ids0):
        raise _Refuse(ROWS_CHANGED)
    if seam:
        seam("ids1", 0)
    if _read_active_ids(db, tip, ROWS_CHANGED) != ids0:
        raise _Refuse(ROWS_CHANGED)
    _check_tip(current_tip, tip)
    return _link(state, tip, ids0)


def _link(state: _State, tip: str, ids: list[int]) -> ScanClaim:
    selected = state.selected
    if selected is None:
        raise _Refuse(SELECTED_NOT_TOOL)
    if selected["tool_name"] != IMAGE_TOOL:
        raise _Refuse(TOOL_NAME_MISMATCH)
    call_id = selected["tool_call_id"]
    if not _valid_id(call_id):
        raise _Refuse(CALL_ID_INVALID)
    if state.tool_counts.get(call_id, 0) != 1:
        raise _Refuse(DUPLICATE_TOOL_ROW)
    declarations = state.declared.get(call_id, [])
    if not declarations:
        raise _Refuse(DECLARATION_MISSING)
    if len(declarations) > 1 or declarations[0].kind != "outer":
        raise _Refuse(DECLARATION_AMBIGUOUS)
    declaration = declarations[0]
    if declaration.row_id >= selected["id"]:
        raise _Refuse(ASSISTANT_NOT_BEFORE_TOOL)
    if declaration.function == IMAGE_TOOL:
        shape = "direct"
    elif declaration.function == BRIDGE_TOOL and declaration.entries is not None:
        if len(declaration.entries) > 1:
            raise _Refuse(BRIDGE_AMBIGUOUS)
        if declaration.entries != (IMAGE_TOOL,):
            raise _Refuse(SHAPE_UNSUPPORTED)
        # legacy single `{name, arguments}` (native normalizer: `calls` absent) is the G1-observed
        # equivalent of the one-entry list; a present-but-null `calls` was refused at parse time
        shape = "bridge_legacy_one" if declaration.legacy else "bridge_one"
    else:
        raise _Refuse(SHAPE_UNSUPPORTED)
    image = _parse_image(selected["content"])
    return ScanClaim(
        tip=tip,
        active_ids=tuple(ids),
        tool_row_id=selected["id"],
        assistant_row_id=declaration.row_id,
        tool_digest=_tool_digest(
            selected["id"], selected["tool_name"], call_id, selected["content"]
        ),
        assistant_digest=state.assistant_digests[declaration.row_id],
        image=image,
        shape=shape,
    )


def _reread(db: Any, tip: str, row_id: int, seam: Seam | None) -> Mapping[str, Any]:
    if seam:
        seam("row", row_id)
    page = _read(db.get_messages, tip, after_id=row_id - 1, limit=1)
    if type(page) is not list or len(page) != 1 or not isinstance(page[0], Mapping):
        raise _Refuse(SELECTED_CHANGED)
    if page[0].get("id") != row_id:
        raise _Refuse(SELECTED_CHANGED)
    return page[0]


def recheck(
    db: Any,
    claim: ScanClaim,
    *,
    current_tip: Callable[[], str],
    seam: Seam | None = None,
) -> ScanOutcome:
    """Re-evaluate a claim after the caller's (hypothetical) file read.

    Same tip, identical active ID list, and the two selected rows re-read exactly: only their
    digests must match (an assistant *content* repair is accepted; its digest excludes content).
    This is not a second full scan and not an atomic claim."""
    stats = {"pages": 0, "rows": 2, "budget_used": 0, "declared": 0}
    budget = _Budget()
    try:
        _valid_args(claim.tip, claim.tool_row_id, current_tip)
        _check_tip(current_tip, claim.tip)
        if seam:
            seam("ids", 0)
        if tuple(_read_active_ids(db, claim.tip, ROWS_CHANGED)) != claim.active_ids:
            raise _Refuse(ROWS_CHANGED)
        assistant = _reread(db, claim.tip, claim.assistant_row_id, seam)
        tool = _reread(db, claim.tip, claim.tool_row_id, seam)
        calls = assistant.get("tool_calls")
        if assistant.get("role") != "assistant" or type(calls) is not list or not calls:
            raise _Refuse(SELECTED_CHANGED)
        _walk(calls, budget)
        if (
            _canonical_digest([claim.assistant_row_id, "assistant", calls])
            != claim.assistant_digest
        ):
            raise _Refuse(SELECTED_CHANGED)
        content = tool.get("content")
        if (
            tool.get("role") != "tool"
            or type(content) is not str
            or utf8_weight(content, MAX_RESULT_BYTES) > MAX_RESULT_BYTES
            or type(tool.get("tool_name")) is not str
            or tool.get("tool_name") != IMAGE_TOOL
            or not _valid_id(tool.get("tool_call_id"))
        ):
            raise _Refuse(SELECTED_CHANGED)
        budget.string(content)
        digest = _tool_digest(
            claim.tool_row_id, tool["tool_name"], tool["tool_call_id"], content
        )
        if digest != claim.tool_digest:
            raise _Refuse(SELECTED_CHANGED)
        _check_tip(current_tip, claim.tip)
    except _Refuse as refusal:
        stats["budget_used"] = budget.used
        return ScanOutcome(False, refusal.reason, None, stats)
    stats["budget_used"] = budget.used
    return ScanOutcome(True, OK, claim, stats)
