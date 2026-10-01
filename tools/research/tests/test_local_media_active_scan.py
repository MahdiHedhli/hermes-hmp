"""Scanner unit tests on a fake store, plus the native `SessionDB` fixture run.

The fake store only exercises the scanner's own parsing, bounds and bracket logic; it is never a
substitute for native behavior. Native characterization is the last test, which runs the real
child under the independent build's own interpreter.
"""

from __future__ import annotations

import json
from typing import Any

import local_media_active_scan as scan
import local_media_active_scan_fixture as fixture
import pytest

CALL = "call_1"
RESULT = json.dumps({"success": True, "image": "/x/y.png"})


def call(
    call_id: str, name: str = "image_generate", args: str = "{}"
) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


class FakeDB:
    """Quacks like the two native reads the scanner uses, and records the calls."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, Any]] = []

    def get_active_message_ids(self, session_id: str) -> list[int]:
        self.calls.append(("ids", session_id))
        return [r["id"] for r in self.rows]

    def get_messages(
        self, session_id: str, *, after_id: int, limit: int
    ) -> list[dict[str, Any]]:
        self.calls.append(("page", (after_id, limit)))
        return [r for r in self.rows if r["id"] > after_id][:limit]


def base_rows(extra: int = 0) -> list[dict[str, Any]]:
    rows = [
        {"id": 1, "role": "assistant", "tool_calls": [call(CALL)], "content": None},
        {
            "id": 2,
            "role": "tool",
            "tool_call_id": CALL,
            "tool_name": "image_generate",
            "content": RESULT,
        },
    ]
    rows += [{"id": 3 + i, "role": "user", "content": "x"} for i in range(extra)]
    return rows


def run(
    db: FakeDB, row: Any = 2, tip: Any = lambda: "t", **kw: Any
) -> scan.ScanOutcome:
    return scan.scan_active_set(db, "t", row, current_tip=tip, **kw)


def test_positive_pages_with_keyset_and_closed_reads() -> None:
    db = FakeDB(base_rows(extra=300))
    outcome = run(db)
    assert outcome.ok and outcome.claim.shape == "direct"
    assert db.calls[0] == ("ids", "t") and db.calls[-1] == ("ids", "t")
    assert [c[1] for c in db.calls if c[0] == "page"] == [
        (0, 128),
        (128, 128),
        (256, 128),
        (384, 128),
    ][:3]
    assert outcome.stats["pages"] == 3 and outcome.stats["rows"] == 302


def test_page_count_at_the_row_cap() -> None:
    db = FakeDB(base_rows(extra=4094))
    assert run(db).ok
    assert (
        sum(1 for c in db.calls if c[0] == "page") == 33
    )  # 32 full pages and the empty one
    over = FakeDB(base_rows(extra=4095))
    outcome = run(over)
    assert outcome.reason == scan.TOO_MANY_ROWS and not any(
        c[0] == "page" for c in over.calls
    )


@pytest.mark.parametrize(
    ("ids", "reason"),
    [
        ([1, True], scan.ACTIVE_IDS_INVALID),
        ([2, 1], scan.ACTIVE_IDS_INVALID),
        ([1, 1], scan.ACTIVE_IDS_INVALID),
        ([0, 2], scan.ACTIVE_IDS_INVALID),
        ([1.0, 2], scan.ACTIVE_IDS_INVALID),
        ("12", scan.ACTIVE_IDS_INVALID),
    ],
)
def test_active_ids_must_be_ordered_exact_ints(ids: Any, reason: str) -> None:
    db = FakeDB(base_rows())
    db.get_active_message_ids = lambda _s: ids  # type: ignore[method-assign]
    assert run(db).reason == reason


def test_page_validation_and_inconsistency_close() -> None:
    db = FakeDB(base_rows(extra=5))
    db.get_messages = lambda *_a, **_k: [{"id": True, "role": "user"}]  # type: ignore[method-assign]
    assert run(db).reason == scan.PAGE_INVALID
    db.get_messages = lambda *_a, **_k: base_rows(5)[1:] + base_rows(5)[:1]  # type: ignore[method-assign]
    assert run(db).reason == scan.ROWS_CHANGED
    db.get_messages = lambda *_a, **_k: [
        {"id": i, "role": "user"} for i in range(1, 200)
    ]  # type: ignore[method-assign]
    assert run(db).reason == scan.PAGE_INVALID  # over 128 rows in one page


def test_native_errors_become_closed_outcomes_without_text() -> None:
    db = FakeDB(base_rows())

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("PRIVATE-TEXT")

    db.get_messages = boom  # type: ignore[method-assign]
    outcome = run(db)
    assert outcome.reason == scan.DB_ERROR and "PRIVATE" not in repr(
        outcome
    ) + json.dumps(outcome.report())


@pytest.mark.parametrize("row", [True, 0, "2", 2.0, None])
def test_selected_row_id_must_be_exact_positive_int(row: Any) -> None:
    assert run(FakeDB(base_rows()), row=row).reason == scan.INVALID_ARGUMENT


def test_tip_callback_brackets_every_read() -> None:
    seen: list[str] = []
    db = FakeDB(base_rows())
    outcome = run(db, tip=lambda: seen.append("tip") or "t")
    assert outcome.ok and seen == ["tip", "tip"]
    assert run(FakeDB(base_rows()), tip=lambda: "other").reason == scan.TIP_CHANGED


def test_utf8_weight_is_chunked_counts_bytes_and_rejects_lone_surrogates() -> None:
    assert scan.utf8_weight("abc") == 3
    assert (
        scan.utf8_weight("é" * 5000) == 10000
    )  # two bytes each, across chunk boundaries
    assert scan.utf8_weight("😀" * 3) == 12
    assert scan.utf8_weight("é" * 100_000, stop_after=100) < 200_000
    with pytest.raises(scan._Refuse) as info:
        scan.utf8_weight("a" * 5000 + "\ud800")
    assert info.value.reason == scan.MALFORMED


def test_walker_depth_budget_and_types() -> None:
    def nest(depth: int) -> Any:
        value: Any = "x"
        for _ in range(depth):
            value = [value]
        return value

    scan._walk(nest(32), scan._Budget())
    with pytest.raises(scan._Refuse):
        scan._walk(nest(33), scan._Budget())
    for bad in (b"x", (1,), {1: 2}, {"a": object()}):
        with pytest.raises(scan._Refuse):
            scan._walk([bad], scan._Budget())
    budget = scan._Budget(100)
    with pytest.raises(scan._Refuse) as info:
        scan._walk(["a" * 1000], budget)
    assert (
        info.value.reason == scan.BUDGET_EXCEEDED
        and budget.used <= 100 + 1000 + scan.NODE_COST
    )
    scan._walk(
        ["a" * 50], scan._Budget(50 + 2 * scan.NODE_COST)
    )  # list node + string node, exact edge
    with pytest.raises(scan._Refuse):
        scan._walk(["a" * 51], scan._Budget(50 + 2 * scan.NODE_COST))


def test_public_values_are_redacted() -> None:
    outcome = run(FakeDB(base_rows()))
    shown = repr(outcome) + repr(outcome.claim) + json.dumps(outcome.report())
    assert CALL not in shown and "/x/y.png" not in shown
    assert set(outcome.report()) <= {
        "ok",
        "reason",
        "pages",
        "rows",
        "budget_used",
        "declared",
        "shape",
        "tool_digest",
        "assistant_digest",
    }
    assert scan.OK in scan.REASONS and scan.BRIDGE_TOOL not in scan.REASONS


def test_recheck_digest_ignores_assistant_content_only() -> None:
    db = FakeDB(base_rows(extra=2))
    claim = run(db).claim
    db.rows[0]["content"] = "repaired"
    assert scan.recheck(db, claim, current_tip=lambda: "t").ok
    db.rows[0]["tool_calls"] = [call("other")]
    assert (
        scan.recheck(db, claim, current_tip=lambda: "t").reason == scan.SELECTED_CHANGED
    )
    db.rows[0]["tool_calls"] = [call(CALL)]
    db.rows[1]["tool_name"] = "terminal"
    assert (
        scan.recheck(db, claim, current_tip=lambda: "t").reason == scan.SELECTED_CHANGED
    )


class Hostile:
    def __eq__(self, other: object) -> bool:
        raise ValueError("PRIVATE-TEXT")

    __ne__ = __eq__  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


def _raiser() -> str:
    raise RuntimeError("PRIVATE-TEXT")


@pytest.mark.parametrize("bad", [_raiser, lambda: Hostile(), lambda: 5, lambda: None])
def test_tip_callback_failures_close_as_tip_changed_for_scan_and_recheck(bad: Any) -> None:
    for brackets in ((bad, lambda: "t"), (lambda: "t", bad)):
        order = iter(brackets)
        outcome = run(FakeDB(base_rows()), tip=lambda order=order: next(order)())
        assert outcome.reason == scan.TIP_CHANGED
        assert "PRIVATE" not in repr(outcome) + json.dumps(outcome.report())
    db = FakeDB(base_rows())
    claim = run(db).claim
    assert scan.recheck(db, claim, current_tip=bad).reason == scan.TIP_CHANGED
    order = iter((lambda: "t", bad))
    assert (
        scan.recheck(db, claim, current_tip=lambda: next(order)()).reason
        == scan.TIP_CHANGED
    )


def test_oversized_active_ids_refuse_on_length_before_any_iteration() -> None:
    big = [*range(1, scan.MAX_ACTIVE_ROWS + 2), True]  # a bool last would fail iteration
    db = FakeDB(base_rows())
    db.get_active_message_ids = lambda _s: big  # type: ignore[method-assign]
    assert run(db).reason == scan.TOO_MANY_ROWS
    # second bracket read and recheck report a changed set
    good = FakeDB(base_rows())
    reads = iter([[1, 2], big])
    good.get_active_message_ids = lambda _s: next(reads)  # type: ignore[method-assign]
    assert run(good).reason == scan.ROWS_CHANGED
    db = FakeDB(base_rows())
    claim = run(db).claim
    db.get_active_message_ids = lambda _s: big  # type: ignore[method-assign]
    assert scan.recheck(db, claim, current_tip=lambda: "t").reason == scan.ROWS_CHANGED


def legacy_rows(arguments: Any) -> list[dict[str, Any]]:
    rows = base_rows()
    rows[0]["tool_calls"] = [call(CALL, "tool_call", json.dumps(arguments))]
    return rows


def test_legacy_single_bridge_is_accepted_only_for_image_tool() -> None:
    ok = run(FakeDB(legacy_rows({"name": "image_generate", "arguments": {}})))
    assert ok.ok and ok.claim.shape == "bridge_legacy_one"
    assert run(FakeDB(legacy_rows({"calls": [{"name": "image_generate"}]}))).ok
    for args, reason in [
        ({"name": "terminal", "arguments": {}}, scan.SHAPE_UNSUPPORTED),
        ({"name": " image_generate", "arguments": {}}, scan.SHAPE_UNSUPPORTED),
        ({"calls": None, "name": "image_generate"}, scan.TOOL_CALLS_UNCERTAIN),
        ({"calls": "image_generate", "name": "image_generate"}, scan.TOOL_CALLS_UNCERTAIN),
        ({"calls": {"name": "image_generate"}}, scan.TOOL_CALLS_UNCERTAIN),
        ({"arguments": {}}, scan.TOOL_CALLS_UNCERTAIN),
        ({"name": 3}, scan.TOOL_CALLS_UNCERTAIN),
    ]:
        assert run(FakeDB(legacy_rows(args))).reason == reason, args
    rows = legacy_rows({"name": "image_generate"})
    rows[1]["tool_name"] = "tool_call"  # native's rejected-wrapper row
    assert run(FakeDB(rows)).reason == scan.TOOL_NAME_MISMATCH


def test_recheck_bounds_name_and_id_before_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDB(base_rows())
    claim = run(db).claim
    digests: list[tuple[Any, ...]] = []
    original = scan._tool_digest

    def count_digest(*args: Any) -> bytes:
        digests.append(args)
        return original(*args)

    monkeypatch.setattr(scan, "_tool_digest", count_digest)
    db.rows[1]["tool_name"] = "x" * 50_000_000
    outcome = scan.recheck(db, claim, current_tip=lambda: "t")
    assert outcome.reason == scan.SELECTED_CHANGED and outcome.stats["budget_used"] < 1000
    db.rows[1]["tool_name"] = "image_generate"
    db.rows[1]["tool_call_id"] = "c" * 300
    assert scan.recheck(db, claim, current_tip=lambda: "t").reason == scan.SELECTED_CHANGED
    assert digests == []  # refused before canonical serialization of oversized native values


def test_canonical_digest_value_error_is_closed() -> None:
    with pytest.raises(scan._Refuse) as info:
        scan._canonical_digest([10**5000])
    assert info.value.reason == scan.MALFORMED and info.value.__suppress_context__
    db = FakeDB(base_rows())
    claim = run(db).claim
    db.rows[0]["tool_calls"] = [call(CALL, args="{}") | {"extra": 10**5000}]
    assert scan.recheck(db, claim, current_tip=lambda: "t").reason == scan.MALFORMED


NATIVE = fixture.DEFAULT_NATIVE_SRC


@pytest.mark.skipif(
    not (NATIVE / ".venv" / "bin" / "python").is_file(), reason="native build absent"
)
def test_native_fixture_matches_expectations() -> None:
    report = fixture.run_parent(NATIVE)
    assert report["status"] == "COMPLETED", report
    assert report["mismatches"] == [], report["mismatches"]
    assert report["case_count"] >= 60
    assert report["native"]["head_matches"] and report["native"]["tree_clean_after"]
    assert report["native"]["owning_files_unchanged"] and report["scratch_removed"]
    assert (
        report["hermes_state_from_checkout"]
        and report["no_module_from_real_hermes_home"]
    )
    assert report["network_connects_blocked"] == 0 and report["child_stdout_bytes"] == 0
    assert not report["child_stderr_mentions_scratch"]
