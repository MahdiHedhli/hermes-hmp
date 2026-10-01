"""C6a batch tests on a fake store: differential against the real single scanner.

The fake store only exercises parsing, bounds and bracket logic; it is never a substitute for
native behavior. Every history is checked two ways: hand-written expectations (independent of the
module) and the accepted single scanner, which must accept exactly the same selectors once digest
and lexical equality are added.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import hmac
import json
import os
import pickle
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import local_media_active_batch as batch
from hmp_plugin import local_media_active_scan as scan
from hmp_plugin import local_media_candidate as cand

PACKAGE = Path(batch.__file__).parent
HOME = "/srv/hermes/profiles/p1"
IMG = HOME + "/cache/images/"
OK = "ok"


def independent_digest(row_id: int, name: str, call_id: str, content: str) -> bytes:
    text = json.dumps(
        [row_id, "tool", name, call_id, content],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(text.encode("ascii")).digest()


def result(name: str = "a.png", **extra: Any) -> str:
    return json.dumps({"success": True, "image": IMG + name, **extra})


def call(call_id: str, name: str = "image_generate", args: str = "{}") -> dict[str, Any]:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": args}}


def history(pairs: int = 3) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(pairs):
        rows.append({"id": 2 * i + 1, "role": "assistant", "tool_calls": [call(f"c{i}")]})
        rows.append(
            {
                "id": 2 * i + 2,
                "role": "tool",
                "tool_call_id": f"c{i}",
                "tool_name": "image_generate",
                "content": result(f"img{i}.png"),
            }
        )
    return rows


class DB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, Any]] = []

    def get_active_message_ids(self, session_id: str) -> list[int]:
        self.calls.append(("ids", session_id))
        return [r["id"] for r in self.rows]

    def get_messages(self, session_id: str, *, after_id: int, limit: int) -> list[dict[str, Any]]:
        self.calls.append(("page", (after_id, limit)))
        return [r for r in self.rows if r["id"] > after_id][:limit]


def selectors(rows: list[dict[str, Any]], ids: Any) -> tuple[tuple[int, bytes], ...]:
    by_id = {r["id"]: r for r in rows}
    out = []
    for row_id in ids:
        row = by_id.get(row_id)
        if (
            row is not None
            and row.get("role") == "tool"
            and type(row.get("content")) is str
            and type(row.get("tool_name")) is str
            and type(row.get("tool_call_id")) is str
        ):
            try:
                digest = independent_digest(
                    row_id, row["tool_name"], row["tool_call_id"], row["content"]
                )
            except UnicodeEncodeError:
                digest = b"\0" * 32
        else:
            digest = b"\0" * 32
        out.append((row_id, digest))
    return tuple(out)


def run(
    db: DB,
    sels: tuple[tuple[int, bytes], ...],
    *,
    home: str = HOME,
    tip: Any = lambda: "t",
    **kw: Any,
) -> batch.ActiveBatchResult:
    return batch.scan_active_batch(db, "t", sels, home=home, current_tip=tip, **kw)


def oracle(rows: list[dict[str, Any]], sels: Any, home: str = HOME) -> list[int]:
    """Accepted ids by the real single scanner plus digest equality plus derivation."""
    accepted = []
    for row_id, digest in sels:
        out = scan.scan_active_set(DB(rows), "t", row_id, current_tip=lambda: "t")
        if (
            out.ok
            and out.claim is not None
            and hmac.compare_digest(out.claim.tool_digest, digest)
            and cand.derive_flat_name(out.claim.image, home) is not None
        ):
            accepted.append(row_id)
    return accepted


def check(
    rows: list[dict[str, Any]], sels: Any, home: str = HOME, expect: dict[int, str] | None = None
) -> batch.ActiveBatchResult:
    out = run(DB(rows), sels, home=home)
    assert [v.row_id for v in out.verdicts] == [s[0] for s in sels]  # order, nothing added
    assert list(out.accepted) == oracle(rows, sels, home)
    if expect is not None:
        assert {v.row_id: v.reason for v in out.verdicts} == expect
    return out


# --------------------------------------------------------------------------- differential


def _pair_swap(rows: list[dict[str, Any]]) -> None:
    rows[2], rows[3] = (
        {**rows[3], "id": 3},
        {**rows[2], "id": 4},
    )  # tool at id 3, its assistant declaration at id 4


def _bridge(rows: list[dict[str, Any]], pair: int, args: Any) -> None:
    rows[2 * pair]["tool_calls"] = [call(f"c{pair}", "tool_call", json.dumps(args))]


def _set_result(rows: list[dict[str, Any]], content: Any) -> None:
    rows[3]["content"] = content


def _set_image(rows: list[dict[str, Any]], image: str) -> None:
    rows[3]["content"] = json.dumps({"success": True, "image": image})


CASES: list[tuple[str, Any, tuple[int, ...], dict[int, str]]] = [
    ("baseline", lambda r: None, (2, 4, 6), {2: OK, 4: OK, 6: OK}),
    (
        "name",
        lambda r: r[3].__setitem__("tool_name", "terminal"),
        (2, 4, 6),
        {2: OK, 4: "tool_name_mismatch", 6: OK},
    ),
    (
        "dup_tool_row",
        lambda r: r.append({**r[1], "id": 7}),
        (2, 4, 6),
        {2: "duplicate_tool_row", 4: OK, 6: OK},
    ),
    (
        "decl_missing",
        lambda r: r[2].__setitem__("tool_calls", [call("zzz")]),
        (2, 4, 6),
        {2: OK, 4: "declaration_missing", 6: OK},
    ),
    (
        "decl_ambiguous",
        lambda r: r.append({"id": 7, "role": "assistant", "tool_calls": [call("c2")]}),
        (2, 4, 6),
        {2: OK, 4: OK, 6: "declaration_ambiguous"},
    ),
    (
        "inner_id_collision",
        lambda r: _bridge(r, 1, {"calls": [{"name": "image_generate", "id": "c2"}]}),
        (2, 4, 6),
        {2: OK, 4: OK, 6: "declaration_ambiguous"},
    ),
    (
        "inner_call_id_alias",
        lambda r: _bridge(r, 1, {"calls": [{"name": "image_generate", "call_id": "c0"}]}),
        (2, 4, 6),
        {2: "declaration_ambiguous", 4: OK, 6: OK},
    ),
    (
        "bridge_one",
        lambda r: _bridge(r, 1, {"calls": [{"name": "image_generate"}]}),
        (2, 4, 6),
        {2: OK, 4: OK, 6: OK},
    ),
    (
        "bridge_legacy",
        lambda r: _bridge(r, 1, {"name": "image_generate", "arguments": {}}),
        (2, 4, 6),
        {2: OK, 4: OK, 6: OK},
    ),
    (
        "bridge_two",
        lambda r: _bridge(r, 1, {"calls": [{"name": "image_generate"}, {"name": "x"}]}),
        (2, 4, 6),
        {2: OK, 4: "bridge_ambiguous", 6: OK},
    ),
    (
        "bridge_other",
        lambda r: _bridge(r, 1, {"calls": [{"name": "terminal"}]}),
        (2, 4, 6),
        {2: OK, 4: "shape_unsupported", 6: OK},
    ),
    (
        "other_function",
        lambda r: r[2].__setitem__("tool_calls", [call("c1", "terminal")]),
        (2, 4, 6),
        {2: OK, 4: "shape_unsupported", 6: OK},
    ),
    (
        "assistant_after_tool",
        _pair_swap,
        (2, 3, 6),
        {2: OK, 3: "assistant_not_before_tool", 6: OK},
    ),
    (
        "assistant_and_user_rows_selected",
        lambda r: r.append({"id": 7, "role": "user", "content": "x"}),
        (1, 7, 99, 6),
        {1: "selected_not_tool", 7: "selected_not_tool", 99: "selected_not_active", 6: OK},
    ),
    (
        "call_id_invalid",
        lambda r: r[3].__setitem__("tool_call_id", "c" * 300),
        (2, 4, 6),
        {2: OK, 4: "call_id_invalid", 6: OK},
    ),
    (
        "call_id_non_str_other_tool_row_is_inert",
        lambda r: r.append({"id": 7, "role": "tool", "tool_call_id": 5, "tool_name": None}),
        (2, 4, 6),
        {2: OK, 4: OK, 6: OK},
    ),
    (
        "success_false",
        lambda r: _set_result(r, json.dumps({"success": False, "image": IMG + "a.png"})),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "error_key",
        lambda r: _set_result(r, result(error="x")),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "content_none",
        lambda r: _set_result(r, None),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "content_list",
        lambda r: _set_result(r, [{"type": "text", "text": result()}]),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "content_not_json",
        lambda r: _set_result(r, "not json"),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "image_missing",
        lambda r: _set_result(r, json.dumps({"success": True})),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "image_too_long",
        lambda r: _set_image(r, IMG + "a" * 5000),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "image_nul",
        lambda r: _set_image(r, IMG + "a\0b"),
        (2, 4, 6),
        {2: OK, 4: "result_not_candidate", 6: OK},
    ),
    (
        "oversize_content_only_that_row",
        lambda r: _set_result(r, result(pad=" " * 70_000)),
        (2, 4, 6),
        {2: OK, 4: "result_too_large", 6: OK},
    ),
    (
        "surrogate_content_only_that_row",
        lambda r: _set_result(r, '{"success": true, "image": "' + IMG + 'a", "p": "\ud800"}'),
        (2, 4, 6),
        {2: OK, 4: "malformed", 6: OK},
    ),
    (
        "surrogate_in_unselected_tool_row_is_inert",
        lambda r: r.append(
            {
                "id": 7,
                "role": "tool",
                "tool_call_id": "zz",
                "tool_name": "x",
                "content": "\ud800" + "x" * 90_000,
            }
        ),
        (2, 4, 6),
        {2: OK, 4: OK, 6: OK},
    ),
    (
        "huge_unselected_content_is_uncharged",
        lambda r: r.append(
            {
                "id": 7,
                "role": "tool",
                "tool_call_id": "zz",
                "tool_name": "terminal",
                "content": "x" * 9_000_000,
            }
        ),
        (2, 4, 6),
        {2: OK, 4: OK, 6: OK},
    ),
]


@pytest.mark.parametrize(("name", "mutate", "ids", "expect"), CASES, ids=[c[0] for c in CASES])
def test_per_candidate_differential(name: str, mutate: Any, ids: Any, expect: Any) -> None:
    rows = history(3)
    mutate(rows)
    check(rows, selectors(rows, ids), expect=expect)


GLOBAL_CASES: list[tuple[str, Any, str]] = [
    ("role_int", lambda r: r.append({"id": 7, "role": 5}), "malformed"),
    (
        "calls_empty",
        lambda r: r.append({"id": 7, "role": "assistant", "tool_calls": []}),
        "tool_calls_uncertain",
    ),
    (
        "call_bad_id",
        lambda r: r.append({"id": 7, "role": "assistant", "tool_calls": [call("")]}),
        "tool_calls_uncertain",
    ),
    (
        "call_limit",
        lambda r: r.append(
            {"id": 7, "role": "assistant", "tool_calls": [call(f"x{i}") for i in range(65)]}
        ),
        "declaration_limit",
    ),
    (
        "bridge_bad_json",
        lambda r: r.append(
            {"id": 7, "role": "assistant", "tool_calls": [call("q", "tool_call", "{bad")]}
        ),
        "tool_calls_uncertain",
    ),
    (
        "bridge_args_oversize",
        lambda r: r.append(
            {
                "id": 7,
                "role": "assistant",
                "tool_calls": [call("q", "tool_call", '{"name":"a","x":"' + "y" * 70_000 + '"}')],
            }
        ),
        "tool_calls_uncertain",
    ),
    (
        "calls_non_str_key",
        lambda r: r.append({"id": 7, "role": "assistant", "tool_calls": [{**call("q"), 1: "x"}]}),
        "malformed",
    ),
    (
        "base_budget",
        lambda r: r.append(
            {"id": 7, "role": "assistant", "tool_calls": [call("q", "x", "a" * 4_300_000)]}
        ),
        "budget_exceeded",
    ),
]


@pytest.mark.parametrize(
    ("name", "mutate", "reason"), GLOBAL_CASES, ids=[c[0] for c in GLOBAL_CASES]
)
def test_global_malformation_refuses_every_selector(name: str, mutate: Any, reason: str) -> None:
    rows = history(3)
    mutate(rows)
    sels = selectors(rows, (2, 4, 6))
    out = check(rows, sels)
    assert out.accepted == () and out.reason == reason
    assert {v.reason for v in out.verdicts} == {reason}
    for row_id, _ in sels:  # the real single scanner refuses the same history
        assert not scan.scan_active_set(DB(rows), "t", row_id, current_tip=lambda: "t").ok


def test_digest_mismatch_only_for_that_selector() -> None:
    rows = history(3)
    sels = list(selectors(rows, (2, 4, 6)))
    sels[1] = (4, bytes([sels[1][1][0] ^ 1]) + sels[1][1][1:])
    out = check(rows, tuple(sels), expect={2: OK, 4: "digest_mismatch", 6: OK})
    assert out.accepted == (2, 6)
    mixed = tuple(reversed(sels))  # selector order is preserved, verdicts follow it
    assert [v.row_id for v in check(rows, mixed).verdicts] == [6, 4, 2]


def test_accepted_order_follows_selectors_and_no_backfill() -> None:
    rows = history(5)
    sels = selectors(rows, (10, 2, 6))
    out = check(rows, sels)
    assert out.accepted == (10, 2, 6) and len(out.verdicts) == 3
    assert not any(v.row_id in (4, 8) for v in out.verdicts)


# --------------------------------------------------------------------------- lexical variants


@pytest.mark.parametrize(
    ("image", "home", "ok"),
    [
        (IMG + "a.png", HOME, True),
        (IMG + "a.png", HOME + "/", False),
        (IMG + "a.png", HOME + "//", False),
        (HOME + "x/cache/images/a.png", HOME, False),  # home as a mere string prefix
        ("/srv/hermes/profiles/p2/cache/images/a.png", HOME, False),  # foreign home
        (HOME + "/cache/images/../a.png", HOME, False),
        (HOME + "/cache/images/sub/a.png", HOME, False),
        (HOME + "/cache/images/", HOME, False),
        (HOME + "/cache/images/a\x07.png", HOME, False),
        (HOME + "/cache/image/a.png", HOME, False),
        (HOME + "/cache/images//a.png", HOME, False),
        ("/SRV/hermes/profiles/p1/cache/images/a.png", HOME, False),
        (IMG + "a.png", "/srv/hermes/profiles/p1/../p1", False),
        (IMG + "a.png", "/srv/hermes/profiles/p1/cache/images", False),
    ],
)
def test_lexical_variants(image: str, home: str, ok: bool) -> None:
    rows = history(1)
    rows[1]["content"] = json.dumps({"success": True, "image": image})
    out = check(rows, selectors(rows, (2,)), home=home)
    assert out.verdicts[0].reason == (OK if ok else "lexical_mismatch")
    assert out.ok


# --------------------------------------------------------------------------- inputs


def test_input_boundaries_and_invalid_shapes_do_no_native_reads() -> None:
    rows = history(130)
    ids = [2 * i + 2 for i in range(130)]
    sels = selectors(rows, ids)
    assert check(rows, sels[:1]).ok and check(rows, sels[:128]).accepted == tuple(ids[:128])
    d = bytes(32)
    bad_selectors: list[Any] = [
        sels[:129],
        (),
        list(sels[:2]),
        [(2, d)],
        None,
        ((2, d), [4, d]),
        ((2, d, 1),),
        ((2,),),
        ((True, d),),
        ((0, d),),
        ((-1, d),),
        ((2.0, d),),
        (("2", d),),
        ((2, d.hex()),),
        ((2, bytearray(d)),),
        ((2, d[:31]),),
        ((2, d + b"x"),),
        ((2, d), (2, d)),
        ((2, None),),
    ]

    class IntSub(int):
        pass

    class BytesSub(bytes):
        pass

    class TupleSub(tuple):  # type: ignore[type-arg]
        pass

    bad_selectors += [((IntSub(2), d),), ((2, BytesSub(d)),), TupleSub(((2, d),))]
    for bad in bad_selectors:
        tips: list[int] = []
        db = DB(rows)
        out = run(db, bad, tip=lambda tips=tips: tips.append(1) or "t")
        assert out.reason == "invalid_argument" and out.verdicts == () and out.accepted == ()
        assert db.calls == [] and tips == []
    for tip, home, current in [
        ("", HOME, lambda: "t"),
        (b"t", HOME, lambda: "t"),
        (None, HOME, lambda: "t"),
        ("t", "", lambda: "t"),
        ("t", b"x", lambda: "t"),
        ("t", HOME + "\0", lambda: "t"),
        ("t", None, lambda: "t"),
        ("t", HOME, None),
        ("t", HOME, "t"),
    ]:
        db = DB(rows)
        out = batch.scan_active_batch(db, tip, sels[:1], home=home, current_tip=current)  # type: ignore[arg-type]
        assert out.reason == "invalid_argument" and out.verdicts == () and db.calls == []


def test_call_pattern_is_independent_of_selector_count() -> None:
    rows = history(128)
    ids = [2 * i + 2 for i in range(128)]
    seen = []
    for count in (1, 16, 128):
        db, tips = DB(rows), []
        out = run(db, selectors(rows, ids[:count]), tip=lambda tips=tips: tips.append(1) or "t")
        assert out.accepted == tuple(ids[:count]) and len(tips) == 2
        seen.append((db.calls, out.stats))
    assert seen[0][0] == seen[1][0] == seen[2][0]
    assert seen[0][1] == seen[1][1] == seen[2][1]  # same shared base accounting
    assert [c[0] for c in seen[0][0]].count("ids") == 2
    assert [c[1] for c in seen[0][0] if c[0] == "page"] == [(0, 128), (128, 128), (256, 128)]


def test_page_boundaries_and_row_cap() -> None:
    for n in (127, 128, 129, 4095, 4096):
        rows = history(1) + [{"id": 3 + i, "role": "user", "content": "x"} for i in range(n - 2)]
        out = run(DB(rows), selectors(rows, (2,)))
        assert out.accepted == (2,), n
    over = DB(history(1) + [{"id": 3 + i, "role": "user", "content": "x"} for i in range(4095)])
    out = run(over, selectors(over.rows, (2,)))
    assert out.reason == "too_many_rows" and out.verdicts[0].reason == "too_many_rows"
    assert [c[0] for c in over.calls] == ["ids"]


# --------------------------------------------------------------------------- budget


def _budget_rows(content_sizes: list[int], pad: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, size in enumerate(content_sizes):
        base = result(f"img{i}.png", pad="")
        rows.append({"id": 2 * i + 1, "role": "assistant", "tool_calls": [call(f"c{i}")]})
        rows.append(
            {
                "id": 2 * i + 2,
                "role": "tool",
                "tool_call_id": f"c{i}",
                "tool_name": "image_generate",
                "content": base.replace('"pad": ""', '"pad": "' + "p" * size + '"'),
            }
        )
    rows.append(
        {
            "id": 2 * len(content_sizes) + 1,
            "role": "assistant",
            "tool_calls": [call("pad", "x", "a" * pad)],
        }
    )
    return rows


def _own_charge(row: dict[str, Any]) -> int:
    return len(row["content"].encode()) + scan.NODE_COST


def test_each_candidate_pays_only_its_own_charge_at_the_exact_edge() -> None:
    sizes = [40_000, 40_000, 40_000]
    rows = _budget_rows(sizes, 0)
    sels = selectors(rows, (2, 4, 6))
    base_used = run(DB(rows), sels).stats[2][1]  # budget_used with an empty pad
    own = _own_charge(rows[1])
    # base + own == limit: every candidate fits by itself, never summed
    fit = _budget_rows(sizes, scan.BUDGET_BYTES - own - base_used)
    out = check(fit, selectors(fit, (2, 4, 6)))
    assert out.accepted == (2, 4, 6) and out.stats[2][1] == scan.BUDGET_BYTES - own
    assert out.stats[2][1] + 2 * own > scan.BUDGET_BYTES  # a summed charge could not fit
    # one byte more refuses all by their own charge, as the single scanner does
    over = _budget_rows(sizes, scan.BUDGET_BYTES - own - base_used + 1)
    out = check(over, selectors(over, (2, 4, 6)))
    assert {v.reason for v in out.verdicts} == {"budget_exceeded"} and out.reason == OK


def test_budget_refuses_only_the_candidate_whose_own_charge_overflows() -> None:
    rows = _budget_rows([100, 30_000, 100], 0)
    empty_base = run(DB(rows), selectors(rows, (2,))).stats[2][1]
    small, large = _own_charge(rows[1]), _own_charge(rows[3])
    pad = scan.BUDGET_BYTES - empty_base - small  # base + small == limit < base + large
    rows = _budget_rows([100, 30_000, 100], pad)
    out = check(rows, selectors(rows, (2, 4, 6)))
    assert {v.row_id: v.reason for v in out.verdicts} == {
        2: OK,
        4: "budget_exceeded",
        6: OK,
    }
    assert large > small


def test_base_over_budget_refuses_everything() -> None:
    rows = _budget_rows([10], scan.BUDGET_BYTES)
    out = check(rows, selectors(rows, (2,)))
    assert out.accepted == () and out.verdicts[0].reason == "budget_exceeded"


def test_selected_content_is_not_charged_into_the_shared_base() -> None:
    small = history(3)
    big = history(3)
    for row in big[1::2]:
        row["content"] = result(pad="z" * 60_000)
    a = run(DB(small), selectors(small, (2, 4, 6)))
    b = run(DB(big), selectors(big, (2, 4, 6)))
    assert a.stats == b.stats and b.accepted == (2, 4, 6)


def test_content_bounds_exact_and_multibyte() -> None:
    rows = history(1)
    shell = len(result(pad="").encode())
    rows[1]["content"] = result(pad="p" * (scan.MAX_RESULT_BYTES - shell))
    assert len(rows[1]["content"].encode()) == scan.MAX_RESULT_BYTES
    assert check(rows, selectors(rows, (2,))).accepted == (2,)
    rows[1]["content"] += " "
    assert check(rows, selectors(rows, (2,)), expect={2: "result_too_large"})
    # multibyte: bytes, not characters, are bounded
    head = '{"success": true, "image": "' + IMG + 'a.png", "p": "'
    fill = (scan.MAX_RESULT_BYTES - len((head + '"}').encode())) // 2
    rows[1]["content"] = head + "é" * fill + '"}'
    assert len(rows[1]["content"].encode()) <= scan.MAX_RESULT_BYTES
    assert check(rows, selectors(rows, (2,))).accepted == (2,)
    rows[1]["content"] = head + "é" * (fill + 1) + '"}'
    assert check(rows, selectors(rows, (2,)), expect={2: "result_too_large"})


def test_bound_check_runs_before_retention_and_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = history(3)
    rows[3]["content"] = result(pad=" " * 70_000)
    parsed: list[Any] = []
    original = scan._parse_image

    def spy(content: Any) -> str:
        parsed.append(len(content) if isinstance(content, str) else content)
        return original(content)

    monkeypatch.setattr(scan, "_parse_image", spy)
    out = run(DB(rows), selectors(rows, (2, 4, 6)))
    assert out.accepted == (2, 6) and len(parsed) == 2 and max(parsed) < 1000


# --------------------------------------------------------------------------- helper identity


def test_accepted_helpers_are_used_by_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    assert batch._scan is scan and batch._candidate is cand
    names = {"_inspect_row": 0, "_link": 0, "_read_active_ids": 0, "_check_tip": 0}
    for name in names:
        original = getattr(scan, name)

        def wrapper(*a: Any, _o: Any = original, _n: str = name, **k: Any) -> Any:
            names[_n] += 1
            return _o(*a, **k)

        monkeypatch.setattr(scan, name, wrapper)
    rows = history(3)
    out = run(DB(rows), selectors(rows, (2, 4, 6)))
    assert out.accepted == (2, 4, 6)
    assert names == {"_inspect_row": 6, "_link": 3, "_read_active_ids": 2, "_check_tip": 2}


def test_digest_comparison_is_the_constant_time_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = history(3)
    sels = selectors(rows, (2, 4, 6))
    calls: list[tuple[Any, ...]] = []
    original = hmac.compare_digest

    def deny(a: Any, b: Any) -> bool:
        calls.append((type(a), type(b), len(a), len(b)))
        return False

    monkeypatch.setattr(hmac, "compare_digest", deny)
    out = run(DB(rows), sels)
    assert out.accepted == () and {v.reason for v in out.verdicts} == {"digest_mismatch"}
    assert calls == [(bytes, bytes, 32, 32)] * 3
    # a wrong digest is accepted only because the helper said so: acceptance depends on it
    wrong = tuple((i, bytes(32)) for i, _ in sels)
    monkeypatch.setattr(hmac, "compare_digest", lambda a, b: True)
    assert run(DB(rows), wrong).accepted == (2, 4, 6)
    monkeypatch.setattr(hmac, "compare_digest", original)
    assert run(DB(rows), wrong).accepted == ()
    # not reached for a candidate refused earlier
    rows[3]["tool_name"] = "terminal"
    calls.clear()
    monkeypatch.setattr(hmac, "compare_digest", deny)
    run(DB(rows), selectors(rows, (2, 4, 6)))
    assert len(calls) == 2


def test_lexical_derivation_is_called_with_the_exact_captured_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []
    original = cand.derive_flat_name

    def spy(image: str, home: str) -> str | None:
        seen.append(home)
        return original(image, home)

    monkeypatch.setattr(cand, "derive_flat_name", spy)
    rows = history(2)
    assert run(DB(rows), selectors(rows, (2, 4))).accepted == (2, 4)
    assert seen == [HOME, HOME]


# --------------------------------------------------------------------------- bracket faults


def test_successful_bracket_order_and_none_active_skips_paging() -> None:
    rows = history(3)
    events: list[str] = []
    db = DB(rows)
    out = run(
        db,
        selectors(rows, (2,)),
        tip=lambda: events.append("tip") or "t",
        seam=lambda phase, idx: events.append(f"{phase}{idx}"),
    )
    assert out.accepted == (2,)
    assert events == ["tip", "ids00", "page0", "ids10", "tip"]
    events.clear()
    db = DB(rows)
    out = run(
        db,
        selectors(rows, (98, 99)),
        tip=lambda: events.append("tip") or "t",
        seam=lambda phase, idx: events.append(f"{phase}{idx}"),
    )
    assert out.reason == OK and {v.reason for v in out.verdicts} == {"selected_not_active"}
    assert events == ["tip", "ids00", "ids10", "tip"] and [c[0] for c in db.calls] == ["ids", "ids"]
    assert out.stats == (("pages", 0), ("rows", 0), ("budget_used", 0), ("declared", 0))


@pytest.mark.parametrize("active", [(2,), (98, 99)])
def test_none_active_still_refuses_on_bracket_change(active: tuple[int, ...]) -> None:
    rows = history(3)
    db = DB(rows)

    def writer(phase: str, idx: int) -> None:
        if phase == "ids1":
            rows.append({"id": 50, "role": "user", "content": "x"})

    out = run(db, selectors(rows, active), seam=writer)
    assert out.reason == "rows_changed" and {v.reason for v in out.verdicts} == {"rows_changed"}
    assert out.accepted == ()


@pytest.mark.parametrize("fail_at", [0, 1])
def test_tip_change_before_or_after_refuses_all(fail_at: int) -> None:
    rows = history(3)
    n = {"i": 0}

    def tip() -> str:
        n["i"] += 1
        return "other" if n["i"] == fail_at + 1 else "t"

    db = DB(rows)
    out = run(db, selectors(rows, (2, 4, 6)), tip=tip)
    assert out.reason == "tip_changed" and {v.reason for v in out.verdicts} == {"tip_changed"}
    assert out.accepted == ()
    assert (db.calls == []) == (fail_at == 0)  # the before-check precedes every native read


class Hostile:
    def __eq__(self, other: object) -> bool:
        raise ValueError("SECRET-SENTINEL")

    __ne__ = __eq__  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


def _raiser() -> str:
    raise RuntimeError("SECRET-SENTINEL")


@pytest.mark.parametrize("bad", [_raiser, lambda: Hostile(), lambda: 5, lambda: None])
def test_tip_callback_failures_close(bad: Any) -> None:
    rows = history(3)
    for brackets in ((bad, lambda: "t"), (lambda: "t", bad)):
        order = iter(brackets)
        out = run(DB(rows), selectors(rows, (2, 4)), tip=lambda order=order: next(order)())
        assert out.reason == "tip_changed" and out.accepted == ()
        assert "SECRET" not in repr(out) + json.dumps(out.report())


def _fault_db(rows: list[dict[str, Any]]) -> DB:
    return DB(rows)


def test_active_id_faults() -> None:
    rows = history(3)
    sels = selectors(rows, (2, 4, 6))
    for ids, reason in [
        ([1, True], "active_ids_invalid"),
        ([2, 1], "active_ids_invalid"),
        ([1, 1], "active_ids_invalid"),
        ([0, 2], "active_ids_invalid"),
        ("12", "active_ids_invalid"),
        (tuple(range(1, 7)), "active_ids_invalid"),
        (list(range(1, 4098)), "too_many_rows"),
    ]:
        db = DB(rows)
        db.get_active_message_ids = lambda _s, ids=ids: ids  # type: ignore[method-assign]
        out = run(db, sels)
        assert out.reason == reason and {v.reason for v in out.verdicts} == {reason}
    # second read: a changed or oversized list is rows_changed; an invalid list stays invalid
    for second, reason in [
        ([1, 2, 3, 4, 5], "rows_changed"),
        ([1, 2, 3, 4, 5, 6, 7], "rows_changed"),
        (list(range(1, 4098)), "rows_changed"),
        ([2, 1], "active_ids_invalid"),
        ([1, True], "active_ids_invalid"),
    ]:
        db = DB(rows)
        reads = iter([[1, 2, 3, 4, 5, 6], second])
        db.get_active_message_ids = lambda _s, reads=reads: next(reads)  # type: ignore[method-assign]
        out = run(db, sels)
        assert out.reason == reason and out.accepted == (), second
    db = DB(rows)
    reads = iter([[1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]])
    db.get_active_message_ids = lambda _s: next(reads)  # type: ignore[method-assign]
    assert run(db, sels).accepted == (2, 4, 6)


def test_native_errors_are_closed_without_text() -> None:
    rows = history(3)

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("SECRET-SENTINEL")

    for target in ("get_active_message_ids", "get_messages"):
        db = DB(rows)
        setattr(db, target, boom)
        out = run(db, selectors(rows, (2, 4)))
        assert out.reason == "db_error" and {v.reason for v in out.verdicts} == {"db_error"}
        assert "SECRET" not in repr(out) + json.dumps(out.report()) + repr(out.verdicts)


def test_page_faults_refuse_all() -> None:
    rows = history(6)
    sels = selectors(rows, (2, 4, 6))
    twelve = [dict(r) for r in rows]
    cases: list[tuple[Any, str]] = [
        (lambda *_a, **_k: "rows", "page_invalid"),
        (lambda *_a, **_k: tuple(twelve), "page_invalid"),
        (lambda *_a, **_k: [{"id": True, "role": "user"}], "page_invalid"),
        (lambda *_a, **_k: [{"role": "user"}], "page_invalid"),
        (lambda *_a, **_k: ["x"], "page_invalid"),
        (lambda *_a, **_k: [{"id": i, "role": "user"} for i in range(1, 200)], "page_invalid"),
        (lambda *_a, **_k: twelve[1:] + twelve[:1], "rows_changed"),  # out of order
        (lambda *_a, **_k: [*twelve, twelve[0]], "rows_changed"),  # extra row
        (lambda *_a, **_k: twelve[:-1], "rows_changed"),  # missing row
        (lambda *_a, **_k: [{**r, "id": r["id"] + 100} for r in twelve], "rows_changed"),
        (lambda *_a, **_k: [], "rows_changed"),
    ]
    for page, reason in cases:
        db = DB(rows)
        db.get_messages = page  # type: ignore[method-assign]
        out = run(db, sels)
        assert out.reason == reason and {v.reason for v in out.verdicts} == {reason}, reason


def test_page_change_midway_across_pages() -> None:
    mutations = [
        lambda r: r.insert(200, {"id": 9999, "role": "user", "content": "x"}),
        lambda r: r.pop(),
        lambda r: r.append({"id": 9999, "role": "user", "content": "x"}),
        lambda r: r.pop(150),
    ]
    for mutate in mutations:
        rows = history(130)
        sels = selectors(rows, (2, 260))

        def writer(
            phase: str, idx: int, rows: list[dict[str, Any]] = rows, m: Any = mutate
        ) -> None:
            if (phase, idx) == ("page", 1):
                m(rows)

        out = run(DB(rows), sels, seam=writer)
        assert out.reason == "rows_changed" and out.accepted == (), mutate


@pytest.mark.parametrize("phase", ["ids0", "page", "ids1"])
def test_writer_at_each_seam(phase: str) -> None:
    rows = history(3)

    def writer(p: str, idx: int) -> None:
        if p == phase:
            rows.append({"id": 77, "role": "user", "content": "x"})

    out = run(DB(rows), selectors(rows, (2, 4, 6)), seam=writer)
    if phase == "ids0":
        assert out.accepted == (2, 4, 6)  # the write precedes the first read: consistent
    elif phase == "page":
        assert out.reason == "rows_changed" or out.accepted == (2, 4, 6)
    else:
        assert out.reason == "rows_changed" and out.accepted == ()


def test_writer_changing_active_set_during_paging_refuses_all() -> None:
    rows = history(3)

    def writer(p: str, idx: int) -> None:
        if p == "page":
            rows.append({"id": 77, "role": "user", "content": "x"})

    out = run(DB(rows), selectors(rows, (2, 4, 6)), seam=writer)
    assert out.reason == "rows_changed" and {v.reason for v in out.verdicts} == {"rows_changed"}


def test_seam_exceptions_are_not_wrapped_or_turned_into_success() -> None:
    rows = history(3)

    def boom(p: str, idx: int) -> None:
        raise KeyError("seam")

    with pytest.raises(KeyError):
        run(DB(rows), selectors(rows, (2,)), seam=boom)


# --------------------------------------------------------------------------- closed result


def test_result_and_reports_leak_nothing_and_retain_no_input() -> None:
    secret_home = "/srv/SECRET-SENTINEL-home"
    s = "SECRET-SENTINEL"
    rows = [
        {"id": 1, "role": "assistant", "tool_calls": [call(s + "-call")]},
        {
            "id": 2,
            "role": "tool",
            "tool_call_id": s + "-call",
            "tool_name": "image_generate",
            "content": json.dumps({"success": True, "image": secret_home + "/cache/images/" + s}),
        },
    ]
    sels = selectors(rows, (2,))
    out = run(DB(rows), sels, home=secret_home)
    assert out.accepted == (2,)
    shown = repr(out) + str(out) + repr(out.verdicts) + json.dumps(out.report())
    shown += "".join(repr(v) + str(v) for v in out.verdicts) + repr(out.stats)
    assert s not in shown and sels[0][1].hex() not in shown and "ScanClaim" not in shown
    assert set(out.report()) == {
        "reason", "candidates", "accepted", "pages", "rows", "budget_used", "declared",
    }  # fmt: skip
    # only ints, closed reasons and tuples are reachable from the result
    seen: list[Any] = []

    def walk(obj: Any) -> None:
        for slot in type(obj).__slots__:
            value = object.__getattribute__(obj, slot)
            stack = [value]
            while stack:
                item = stack.pop()
                if isinstance(item, tuple):
                    stack.extend(item)
                elif isinstance(item, batch.BatchVerdict):
                    walk(item)
                else:
                    seen.append(item)

    walk(out)
    assert all(type(x) is int or x in batch.REASONS for x in seen)
    assert not any(isinstance(x, bytes | bytearray) for x in seen)
    for obj in (out, out.verdicts[0]):
        assert not hasattr(obj, "__dict__")
        with pytest.raises(AttributeError):
            obj.x = 1  # type: ignore[attr-defined]
        with pytest.raises(AttributeError):
            obj._reason = "ok"
        with pytest.raises(AttributeError):
            del obj._reason
        with pytest.raises(TypeError):
            pickle.dumps(obj)
        with pytest.raises(TypeError):
            copy.copy(obj)
        with pytest.raises(TypeError):
            copy.deepcopy(obj)
        with pytest.raises(TypeError):
            json.dumps(obj)


def test_closed_reasons_are_the_scanner_set_plus_two_literals() -> None:
    assert scan.REASONS | {"digest_mismatch", "lexical_mismatch"} == batch.REASONS
    assert "tool_call" not in batch.REASONS and "image_generate" not in batch.REASONS
    for rows_case in CASES:
        rows = history(3)
        rows_case[1](rows)
        out = run(DB(rows), selectors(rows, rows_case[2]))
        assert {v.reason for v in out.verdicts} <= batch.REASONS
    with pytest.raises(ValueError):
        batch.BatchVerdict(2, "free text")
    with pytest.raises(ValueError):
        batch.BatchVerdict(True, "ok")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- inertness


FROZEN = {
    "local_media_active_scan.py": (
        "81eb6880f396ad3c2a244c875753887332336da4c4a2a68569f3e7c455b8b4c2"
    ),
    "local_media_candidate.py": (
        "4656d83b6adfa1a05a068f63c68111ad2147c5ce0b76b5414ad8082d4d9789d1"
    ),
    "local_media_file_safety.py": (
        "440c3cfa5c636d5d280f4cf8876f900ab9177b0421d55a8d5503fc398973ef74"
    ),
    "local_media_raster_structure.py": (
        "f293d0c1e379d20ec5d466e9a92e9c0e6b961a2a2b7009b5aac3705410b47610"
    ),
    "local_media_result.py": ("04d011cf8b805c2b285297e18f99a4ec1691f0133320948d2680d564c29b4336"),
    "local_media_sidecar.py": ("e3872f8f013fc51f9e4f682d3ad96024817aa1585075433ede980649857410bf"),
    "local_media_registry.py": ("b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2"),
}


@pytest.mark.parametrize("name", sorted(FROZEN))
def test_frozen_modules_are_byte_identical(name: str) -> None:
    assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == FROZEN[name]


def test_batch_imports_only_the_two_accepted_modules_and_stdlib() -> None:
    tree = ast.parse((PACKAGE / "local_media_active_batch.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(
                ("." * node.level)
                + (node.module or "")
                + "|"
                + ",".join(a.name for a in node.names)
            )
    assert modules == {
        "__future__|annotations",
        "hmac",
        "typing|Any,Final",
        ".|local_media_active_scan",
        ".|local_media_candidate",
    }
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"print", "open", "__import__", "eval", "exec", "compile", "logging", "os"}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"stat", "open", "resolve", "read_bytes", "info", "warning", "error"}


def test_fresh_interpreter_loads_only_the_accepted_chain_and_no_production_module_loads_it() -> (
    None
):
    code = (
        "import sys, hmp_plugin.local_media_active_batch\n"
        "found = sorted(m.rsplit('.', 1)[-1] for m in sys.modules if 'local_media_' in m)\n"
        "print(','.join(found))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent), "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr[-500:]
    assert set(done.stdout.strip().split(",")) == {
        "local_media_active_batch",
        "local_media_active_scan",
        "local_media_candidate",
        "local_media_file_safety",
        "local_media_result",
        "local_media_sidecar",
    }
    for path in PACKAGE.glob("*.py"):
        if path.stem != "local_media_active_batch":
            assert "local_media_active_batch" not in path.read_text(encoding="utf-8"), path.name


def test_only_selected_rows_are_captured_or_measured(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = history(4)
    rows.append(
        {"id": 9, "role": "tool", "tool_call_id": "u", "tool_name": "x", "content": "y" * 777}
    )
    captured: list[int] = []
    original = batch._capture

    def spy(row: Any, row_id: int) -> Any:
        captured.append(row_id)
        return original(row, row_id)

    monkeypatch.setattr(batch, "_capture", spy)
    weighed: list[int] = []
    original_weight = scan.utf8_weight

    def weight(text: str, stop_after: int | None = None) -> int:
        weighed.append(len(text))
        return original_weight(text, stop_after)

    monkeypatch.setattr(scan, "utf8_weight", weight)
    out = run(DB(rows), selectors(rows, (4, 2, 98)))
    assert out.accepted == (4, 2) and captured == [2, 4]
    assert 777 not in weighed  # row 9 content was never measured


# --------------------------------------------------------------------------- hardening delta


class _FlipRow(Mapping):  # type: ignore[type-arg]
    """A non-dict Mapping whose role/name/call id reads change after the first inspection."""

    def __init__(self, row: dict[str, Any], other: dict[str, Any]) -> None:
        self.row, self.other = row, other
        self.reads: dict[str, int] = {}

    def get(self, key: str, default: Any = None) -> Any:
        self.reads[key] = self.reads.get(key, 0) + 1
        source = self.row if self.reads[key] == 1 else self.other
        return source.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.row[key]

    def __iter__(self) -> Any:
        return iter(self.row)

    def __len__(self) -> int:
        return len(self.row)


class _Sub(dict):  # type: ignore[type-arg]
    pass


def _swapped_db(wrap: Any) -> tuple[DB, tuple[tuple[int, bytes], ...]]:
    rows = history(2)
    sels = selectors(rows, (2,))
    # a second read of the tool row would link to the other declaration's call id and name
    other = dict(rows[3], tool_call_id="c1")
    rows[1] = wrap(rows[1], other)
    return DB(rows), sels


def test_non_dict_mapping_row_is_refused_alone_not_read_twice() -> None:
    db, sels = _swapped_db(_FlipRow)
    sels = sels + selectors(db.rows, (4,))
    out = run(db, sels)
    assert out.ok and {v.row_id: v.reason for v in out.verdicts} == {2: "page_invalid", 4: OK}
    assert db.rows[1].reads == {"id": 1, "role": 1, "tool_call_id": 1, "tool_name": 1}


def test_exact_dict_control_and_dict_subclass() -> None:
    db, sels = _swapped_db(lambda row, other: dict(row))
    assert run(db, sels).accepted == (2,)  # the exact dict control is unchanged
    db, sels = _swapped_db(lambda row, other: _Sub(row))
    out = run(db, sels)
    assert out.ok and out.verdicts[0].reason == "page_invalid"


def test_non_str_selected_content_is_dropped_before_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Payload:
        pass

    marker = "SECRET-NONSTR-MARKER"
    for content in ([marker] * 50_000, {marker: [marker] * 10}, Payload(), b"x" * 100_000):
        rows = history(2)
        rows[1]["content"] = content
        seen: list[Any] = []
        original = scan._link

        def spy(state: Any, tip: str, ids: Any, _o: Any = original, _s: list[Any] = seen) -> Any:
            _s.append(state.selected)
            return _o(state, tip, ids)

        monkeypatch.setattr(scan, "_link", spy)
        out = run(DB(rows), selectors(rows, (2,)))
        assert out.ok and out.verdicts[0].reason == "result_not_candidate"
        assert len(seen) == 1 and seen[0]["content"] is None
        assert marker not in repr(seen) and repr(out).count(marker) == 0
        monkeypatch.undo()


def test_constructors_refuse_reinitialization_and_keep_the_original() -> None:
    out = run(DB(history(2)), selectors(history(2), (2,)))
    verdict = out.verdicts[0]
    before = (verdict.row_id, verdict.reason, out.reason, out.verdicts, out.accepted, out.stats)
    with pytest.raises((ValueError, TypeError)):
        verdict.__init__(99, "malformed")  # type: ignore[misc]
    with pytest.raises((ValueError, TypeError)):
        out.__init__("malformed", (), (0, 0, 0, 0))  # type: ignore[misc]
    with pytest.raises((ValueError, TypeError)):
        verdict.__init__(0, "bogus")  # type: ignore[misc]
    assert before == (
        verdict.row_id,
        verdict.reason,
        out.reason,
        out.verdicts,
        out.accepted,
        out.stats,
    )
    fresh = batch.BatchVerdict(5, OK)  # a first construction still works
    assert fresh.accepted
