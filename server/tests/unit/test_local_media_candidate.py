"""Bounded local image candidate extraction: causal guards, not a mirror of the code.

The module is inert and does no I/O. Each guard below is a function of a module object, so the
same guard runs against the real module and against out-of-tree mutants that must fail it.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import json
import logging
import os
import pathlib
import random
import subprocess
import sys
import types
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import local_media_active_scan as scan
from hmp_plugin import local_media_candidate as cand
from hmp_plugin.local_media_sidecar import MAX_CANDIDATES_PER_RESPONSE, MediaCandidate

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
SOURCE = (PACKAGE / "local_media_candidate.py").read_text(encoding="utf-8")

HOME = "/srv/hermes/profiles/p1"
PREFIX = HOME + "/cache/images/"
IMG = PREFIX + "gen_secret_name.png"


class Str(str):
    """A `str` subclass: never an exact `str`."""


def result(image: object = IMG, **extra: object) -> str:
    return json.dumps({"success": True, "image": image, **extra})


GOOD = result()
BAD = json.dumps({"success": False, "error": "no"})


def trow(row_id: Any, content: Any = GOOD, **over: Any) -> dict[str, Any]:
    row = {
        "id": row_id,
        "role": "tool",
        "tool_name": "image_generate",
        "tool_call_id": f"call_{row_id}",
        "content": content,
    }
    row.update(over)
    return row


def padded(nbytes: int) -> str:
    """A valid result of exactly `nbytes` ASCII bytes."""
    base = result(pad="")
    return result(pad="x" * (nbytes - len(base)))


class Counts:
    loads = 0
    parses = 0


@contextlib.contextmanager
def counting() -> Iterator[Counts]:
    counts = Counts()
    real_loads, real_parse = json.loads, scan._parse_image

    def loads(*a: Any, **k: Any) -> Any:
        counts.loads += 1
        return real_loads(*a, **k)

    def parse(content: Any) -> Any:
        counts.parses += 1
        return real_parse(content)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(json, "loads", loads)
        mp.setattr(scan, "_parse_image", parse)
        yield counts


def ids(out: tuple[MediaCandidate, ...]) -> list[int]:
    return [c.tool_row_id for c in out]


def never_raises(fn: Callable[..., Any], *args: Any) -> Any:
    try:
        return fn(*args)
    except BaseException:
        raise AssertionError("raised") from None


# --- guards: each is a function of a module, so a mutant can be run through it ---------------


def wide(pad_chars: int = 40000) -> str:
    return json.dumps({"success": True, "image": IMG, "pad": "é" * pad_chars}, ensure_ascii=False)


def check_bound(mod: Any) -> None:
    over_chars, over_bytes = padded(65537), wide()
    assert len(over_bytes) < 65536 < len(over_bytes.encode())  # chars fit, UTF-8 weight does not
    for content in (over_chars, over_bytes, "x" * 70000):
        with counting() as c:
            assert mod.raw_tool_candidate(trow(1, content), HOME) is None
            assert (c.loads, c.parses) == (0, 0)
    with counting() as c:
        got = mod.raw_tool_candidate(trow(2, padded(65536)), HOME)  # exactly the bound passes
        assert got is not None and got.tool_row_id == 2
        assert c.loads == 1


def check_derivation(mod: Any) -> None:
    assert mod.raw_tool_candidate(trow(1, result(PREFIX + "a.png")), HOME) is not None
    for image in (
        PREFIX + "sub/a.png",
        PREFIX + "../a.png",
        PREFIX + "/etc/a.png",
        PREFIX + "a\\b.png",
        PREFIX + "a" + chr(0x200B) + "b.png",
        HOME + "/cache/image_cache/a.png",
        "/srv/hermes/profiles/other/cache/images/a.png",
        PREFIX,
        HOME + "/cache/images/",
    ):
        assert mod.raw_tool_candidate(trow(1, result(image)), HOME) is None, image
    assert mod.derive_flat_name(PREFIX + "a.png", HOME + "/") is None
    assert mod.derive_flat_name(PREFIX + "a.png", HOME + "//") is None
    assert mod.derive_flat_name(PREFIX + "a.png", HOME) == "a.png"
    assert mod.derive_flat_name(PREFIX + "é" * 65, HOME) is None
    assert mod.derive_flat_name(PREFIX + "a" * 128, HOME) == "a" * 128


def check_order(mod: Any) -> None:
    rows = [trow(i) for i in range(1, 6)]
    full = frozenset(range(1, 6))
    assert ids(mod.collect_candidates(rows, HOME, full)) == [5, 4, 3, 2, 1]
    mixed = list(rows)
    random.Random(7).shuffle(mixed)
    assert ids(mod.collect_candidates(mixed, HOME, full)) == [5, 4, 3, 2, 1]
    assert ids(mod.collect_candidates(rows[::-1], HOME, full)) == [5, 4, 3, 2, 1]


def check_cap(mod: Any) -> None:
    rows = [trow(i) for i in range(1, 131)]
    with counting() as c:
        out = mod.collect_candidates(rows, HOME, frozenset(range(1, 131)))
    assert ids(out) == list(range(130, 2, -1)) and len(out) == MAX_CANDIDATES_PER_RESPONSE
    assert c.parses == MAX_CANDIDATES_PER_RESPONSE


def check_no_backfill(mod: Any) -> None:
    bad = [trow(i, BAD) for i in range(6, 134)]  # the 128 newest attempts all fail
    rows = [trow(i) for i in range(1, 6)] + bad
    with counting() as c:
        out = mod.collect_candidates(rows, HOME, frozenset(range(1, 134)))
    assert out == () and c.parses == MAX_CANDIDATES_PER_RESPONSE
    some = [trow(i, BAD if i % 2 else GOOD) for i in range(1, 11)]
    assert ids(mod.collect_candidates(some, HOME, frozenset(range(1, 11)))) == [10, 8, 6, 4, 2]


def check_unreturned(mod: Any) -> None:
    rows = [trow(i) for i in range(1, 201)]
    with counting() as c:
        out = mod.collect_candidates(rows, HOME, frozenset({1, 2, 3}))
    assert ids(out) == [3, 2, 1] and c.parses == 3


def check_other_tools(mod: Any) -> None:
    noise = [trow(i, tool_name="other_tool") for i in range(201, 401)]
    noise += [trow(i, role="assistant") for i in range(401, 501)]
    rows = [trow(i) for i in range(1, 4)] + noise
    out = mod.collect_candidates(rows, HOME, frozenset(range(1, 501)))
    assert ids(out) == [3, 2, 1]


def check_dedupe(mod: Any) -> None:
    with counting() as c:
        out = mod.collect_candidates([trow(5), trow(5), trow(4)], HOME, frozenset({4, 5}))
    assert out == () and c.parses == 0
    first_wins = mod.collect_candidates([trow(5, GOOD), trow(5, BAD)], HOME, frozenset({5}))
    assert first_wins == ()


def check_digest(mod: Any) -> None:
    got = mod.raw_tool_candidate(trow(7), HOME)
    assert got is not None
    assert got.raw_digest == scan._tool_digest(7, "image_generate", "call_7", GOOD)
    other = mod.raw_tool_candidate(trow(7, GOOD + " "), HOME)
    assert other is not None and other.raw_digest != got.raw_digest


def check_ids(mod: Any) -> None:
    rows = [trow(1)]
    assert mod.collect_candidates(rows, HOME, frozenset({True})) == ()
    assert mod.collect_candidates(rows, HOME, frozenset({0, 1})) == ()
    assert mod.collect_candidates(rows, HOME, frozenset({-1, 1})) == ()
    assert mod.collect_candidates(rows, HOME, frozenset({1})) != ()


def check_exact_types(mod: Any) -> None:
    assert mod.raw_tool_candidate(trow(1, role=Str("tool")), HOME) is None
    assert mod.raw_tool_candidate(trow(1, tool_name=Str("image_generate")), HOME) is None
    assert mod.raw_tool_candidate(trow(1, GOOD), Str(HOME)) is None
    assert mod.collect_candidates([trow(1, role=Str("tool"))], HOME, frozenset({1})) == ()


def check_total(mod: Any) -> None:
    class Boom(Mapping[Any, Any]):
        def __getitem__(self, key: Any) -> Any:
            raise RuntimeError("secret")

        def get(self, key: Any, default: Any = None) -> Any:
            raise RuntimeError("secret")

        def __iter__(self) -> Iterator[Any]:
            raise RuntimeError("secret")

        def __len__(self) -> int:
            raise RuntimeError("secret")

    assert never_raises(mod.raw_tool_candidate, Boom(), HOME) is None
    out = never_raises(mod.collect_candidates, [Boom(), trow(2)], HOME, frozenset({2}))
    assert ids(out) == [2]

    def raising(_name: object) -> None:
        raise RuntimeError("secret")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mod, "classify_candidate", raising)
        assert never_raises(mod.raw_tool_candidate, trow(1), HOME) is None
        assert never_raises(mod.collect_candidates, [trow(1)], HOME, frozenset({1})) == ()


CHECKS: dict[str, Callable[[Any], None]] = {
    "bound": check_bound,
    "derivation": check_derivation,
    "order": check_order,
    "cap": check_cap,
    "no_backfill": check_no_backfill,
    "unreturned": check_unreturned,
    "other_tools": check_other_tools,
    "dedupe": check_dedupe,
    "digest": check_digest,
    "ids": check_ids,
    "exact_types": check_exact_types,
    "total": check_total,
}


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_guard_passes_on_the_real_module(name: str) -> None:
    CHECKS[name](cand)


# --- out-of-tree mutants must each fail their target guard ----------------------------------------

BLOCK_OLD = """            attempts += 1
            candidate = raw_tool_candidate(row, home)  # type: ignore[arg-type]
            if candidate is not None:
                found.append(candidate)
"""
BLOCK_NEW = """            candidate = raw_tool_candidate(row, home)  # type: ignore[arg-type]
            if candidate is not None:
                attempts += 1
                found.append(candidate)
"""

# label -> (guard, old text, new text, expected occurrences)
MUTANTS: dict[str, tuple[str, str, str, int]] = {
    "parse before the bound": (
        "bound",
        "image = parse_image_result(content)  # the one bounded, accepted parse",
        "image = _scan._parse_image(content)",
        1,
    ),
    "grammar relaxed": (
        "derivation",
        "return name if classify_candidate(name) is None else None",
        "return name or None",
        1,
    ),
    "home normalized": (
        "derivation",
        "prefix = home + IMAGE_CACHE_SUFFIX",
        'prefix = home.rstrip("/") + IMAGE_CACHE_SUFFIX',
        1,
    ),
    "no ordering": (
        "order",
        "ordered = sorted(raw_rows, key=_row_id, reverse=True)",
        "ordered = list(raw_rows)",
        1,
    ),
    "oldest first": (
        "order",
        "key=_row_id, reverse=True",
        "key=_row_id, reverse=False",
        1,
    ),
    "cap off by one": (
        "cap",
        "attempts >= MAX_CANDIDATES_PER_RESPONSE",
        "attempts > MAX_CANDIDATES_PER_RESPONSE",
        1,
    ),
    "backfill after rejection": ("no_backfill", BLOCK_OLD, BLOCK_NEW, 1),
    "returned filter removed": (
        "unreturned",
        " or row_id not in returned_tool_ids",
        "",
        1,
    ),
    "duplicate preflight removed": (
        "dedupe",
        "if len(positive_ids) != len(set(positive_ids)):\n            return ()",
        "if len(positive_ids) != len(set(positive_ids)):\n            pass",
        1,
    ),
    "digest of other bytes": (
        "digest",
        "_scan._tool_digest(row_id, IMAGE_TOOL, call_id, content)",
        "_scan._tool_digest(row_id, IMAGE_TOOL, call_id, call_id)",
        1,
    ),
    "bool ids": (
        "ids",
        "return type(value) is int and value >= 1",
        "return isinstance(value, int) and value >= 1",
        1,
    ),
    "zero ids": (
        "ids",
        "return type(value) is int and value >= 1",
        "return type(value) is int and value >= 0",
        1,
    ),
    "role by equality only": (
        "exact_types",
        "if type(role) is not str or role != TOOL_ROLE:",
        "if role != TOOL_ROLE:",
        2,
    ),
    "narrow except": (
        "total",
        "    except Exception:  # nothing private may escape; no chaining, no logging",
        "    except ValueError:",
        1,
    ),
    "any tool row is an attempt": (
        "other_tools",
        "if type(name) is not str or name != IMAGE_TOOL or not _positive_id(row_id):",
        "if not _positive_id(row_id):",
        1,
    ),
}


@contextlib.contextmanager
def loaded(tmp_path: Path, name: str, source: str) -> Iterator[Any]:
    path = tmp_path / f"{name}.py"  # out of tree: never inside the repository
    path.write_text(source, encoding="utf-8")
    modname = f"hmp_plugin._mutant_{name}"
    spec = importlib.util.spec_from_file_location(modname, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(modname, None)


def test_unmutated_copy_out_of_tree_passes_every_guard(tmp_path: Path) -> None:
    with loaded(tmp_path, "control", SOURCE) as mod:
        for check in CHECKS.values():
            check(mod)


@pytest.mark.parametrize("label", sorted(MUTANTS))
def test_each_mutant_fails_its_target_guard(tmp_path: Path, label: str) -> None:
    guard, old, new, count = MUTANTS[label]
    assert SOURCE.count(old) == count, "the mutation does not apply exactly"
    mutated = SOURCE.replace(old, new)
    assert mutated != SOURCE
    with loaded(tmp_path, "mutant", mutated) as mod, pytest.raises(AssertionError):
        CHECKS[guard](mod)


def test_every_guard_has_a_mutant() -> None:
    assert {guard for guard, *_ in MUTANTS.values()} == set(CHECKS)


# --- derive_flat_name -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("image", "home", "expected"),
    [
        (PREFIX + "a.png", HOME, "a.png"),
        (PREFIX + "é.png", HOME, "é.png"),
        (PREFIX + "a" * 128, HOME, "a" * 128),
        (PREFIX + "a" * 129, HOME, None),
        (PREFIX + "é" * 64, HOME, "é" * 64),  # 128 bytes
        (PREFIX + "é" * 65, HOME, None),  # 130 bytes
        (PREFIX + "..", HOME, None),
        (PREFIX + ".", HOME, None),
        (PREFIX + "a/b.png", HOME, None),
        (PREFIX + "a\\b.png", HOME, None),
        (PREFIX + "/abs.png", HOME, None),
        (PREFIX + "a\x00.png", HOME, None),
        (PREFIX + "a\n.png", HOME, None),
        (PREFIX + "a" + chr(0x200B) + ".png", HOME, None),  # format character
        (PREFIX + "a" + chr(0x2028) + ".png", HOME, None),  # line separator
        (PREFIX, HOME, None),
        (HOME + "/cache/image_cache/a.png", HOME, None),
        (HOME + "/image_cache/a.png", HOME, None),
        ("/srv/hermes/profiles/p2/cache/images/a.png", HOME, None),
        ("/srv/hermes/profiles/p1x/cache/images/a.png", HOME, None),
        ("/srv/hermes/profiles/p1/cache/images/a.png", HOME + "/", None),
        ("/srv/hermes/profiles/p1/cache/images/a.png", HOME + "//", None),
        ("/private/tmp/h/cache/images/a.png", "/tmp/h", None),  # noqa: S108
        ("/tmp/h/cache/images/a.png", "/private/tmp/h", None),  # noqa: S108
        ("//srv/hermes/profiles/p1/cache/images/a.png", HOME, None),
        ("/srv/hermes/profiles/p1/./cache/images/a.png", HOME, None),
        (PREFIX + "a.png", "", None),
        (PREFIX + "a.png", HOME + "\x00", None),
        ("/cache/images/a.png", "", None),
        (b"x", HOME, None),
        (PREFIX + "a.png", b"x", None),
        (None, HOME, None),
        (PREFIX + "a.png", None, None),
        (Str(PREFIX + "a.png"), HOME, None),
        (PREFIX + "a.png", Str(HOME), None),
        (PREFIX + Str("a.png"), HOME, "a.png"),  # concatenation yields an exact str
        (pathlib.PurePosixPath(PREFIX + "a.png"), HOME, None),
    ],
)
def test_derive_flat_name(image: Any, home: Any, expected: str | None) -> None:
    got = cand.derive_flat_name(image, home)
    assert got == expected
    assert got is None or type(got) is str


def test_derivation_touches_no_filesystem_api(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("filesystem or path normalization call")

    for owner, attr in (
        (os, "stat"),
        (os, "lstat"),
        (os, "fspath"),
        (os, "getcwd"),
        (os, "listdir"),
        (os, "scandir"),
        (os, "open"),
        (os.path, "realpath"),
        (os.path, "abspath"),
        (os.path, "normpath"),
        (os.path, "exists"),
        (os.path, "expanduser"),
        (pathlib.Path, "resolve"),
        (pathlib.Path, "stat"),
        (pathlib.Path, "exists"),
        (pathlib.Path, "expanduser"),
    ):
        monkeypatch.setattr(owner, attr, boom)
    monkeypatch.setattr("builtins.open", boom)
    assert cand.derive_flat_name(PREFIX + "a.png", HOME) == "a.png"
    got = cand.raw_tool_candidate(trow(3), HOME)
    assert got is not None and got.tool_row_id == 3
    assert ids(cand.collect_candidates([trow(3), trow(4)], HOME, frozenset({3, 4}))) == [4, 3]


# --- raw_tool_candidate ---------------------------------------------------------------------------


def test_positive_candidate_carries_only_row_id_and_digest() -> None:
    got = cand.raw_tool_candidate(trow(9), HOME)
    assert type(got) is MediaCandidate
    assert got.tool_row_id == 9
    assert got.raw_digest == scan._tool_digest(9, "image_generate", "call_9", GOOD)
    assert type(got).__slots__ == ("_raw_digest", "_tool_row_id")
    values = [got.tool_row_id, got.raw_digest]
    blob = repr(got) + str(got) + repr(values)
    for private in ("gen_secret_name", HOME, "cache/images", "call_9", "image_generate"):
        assert private not in blob
    assert b"gen_secret_name" not in got.raw_digest and len(got.raw_digest) == 32


def test_the_row_mapping_is_not_mutated_or_retained() -> None:
    row = trow(9)
    before = dict(row)
    got = cand.raw_tool_candidate(row, HOME)
    assert got is not None and row == before


def test_mapping_proxy_rows_are_accepted_like_native_mappings() -> None:
    got = cand.raw_tool_candidate(types.MappingProxyType(trow(4)), HOME)  # type: ignore[arg-type]
    assert got is not None and got.tool_row_id == 4


@pytest.mark.parametrize(
    "row",
    [
        trow(1, role="assistant"),
        trow(1, role="user"),
        trow(1, role=None),
        trow(1, role=Str("tool")),
        trow(1, tool_name="other"),
        trow(1, tool_name=None),
        trow(1, tool_name="Image_Generate"),
        trow(1, tool_name=Str("image_generate")),
        trow(0),
        trow(-1),
        trow(True),
        trow(1.0),
        trow("1"),
        trow(None),
        trow(1, tool_call_id=""),
        trow(1, tool_call_id=None),
        trow(1, tool_call_id=7),
        trow(1, tool_call_id="a\x00b"),
        trow(1, tool_call_id="x" * 5000),
        trow(1, tool_call_id=Str("call_1")),
        trow(1, content=None),
        trow(1, content=[{"type": "text", "text": GOOD}]),
        trow(1, content=GOOD.encode()),
        trow(1, content=Str(GOOD)),
        trow(1, content=""),
        trow(1, content="not json"),
        trow(1, content="[1]"),
        trow(1, content=json.dumps({"success": False, "image": IMG})),
        trow(1, content=json.dumps({"success": "true", "image": IMG})),
        trow(1, content=json.dumps({"success": 1, "image": IMG})),
        trow(1, content=json.dumps({"success": True, "image": IMG, "error": "x"})),
        trow(1, content=json.dumps({"success": True, "image": IMG, "error": None})),
        trow(1, content=json.dumps({"success": True})),
        trow(1, content=json.dumps({"success": True, "image": None})),
        trow(1, content=json.dumps({"success": True, "image": 5})),
        trow(1, content=json.dumps({"success": True, "image": ""})),
        trow(1, content=json.dumps({"success": True, "image": PREFIX + "a\x00.png"})),
        trow(1, content=json.dumps({"success": True, "image": PREFIX + "a" * 4096})),
        trow(1, content=json.dumps({"success": True, "image": ["x"]})),
        {k: v for k, v in trow(1).items() if k != "id"},
        {k: v for k, v in trow(1).items() if k != "role"},
        {k: v for k, v in trow(1).items() if k != "tool_name"},
        {k: v for k, v in trow(1).items() if k != "tool_call_id"},
        {k: v for k, v in trow(1).items() if k != "content"},
        [("id", 1)],
        "row",
        None,
        7,
    ],
)
def test_raw_tool_candidate_refuses(row: Any) -> None:
    assert cand.raw_tool_candidate(row, HOME) is None


@pytest.mark.parametrize("home", ["", HOME + "/", HOME + "x", "/other", "\x00", HOME + "\x00"])
def test_raw_tool_candidate_needs_the_exact_home(home: str) -> None:
    assert cand.raw_tool_candidate(trow(1), home) is None


@pytest.mark.parametrize("home", [None, b"/x", 5, Str(HOME), pathlib.PurePosixPath(HOME)])
def test_raw_tool_candidate_with_a_non_str_home_is_none(home: Any) -> None:
    assert cand.raw_tool_candidate(trow(1), home) is None


def test_every_internal_failure_is_closed_and_silent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    row = trow(1)

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("SECRET-" + IMG)

    for owner, attr in (
        (cand, "parse_image_result"),
        (cand, "classify_candidate"),
        (cand, "derive_flat_name"),
        (scan, "_tool_digest"),
        (scan, "_valid_id"),
        (scan, "_parse_image"),
        (cand, "MediaCandidate"),
    ):
        with monkeypatch.context() as mp:
            mp.setattr(owner, attr, boom)
            assert never_raises(cand.raw_tool_candidate, row, HOME) is None
            assert never_raises(cand.collect_candidates, [row], HOME, frozenset({1})) == ()
    assert caplog.records == []


def test_deep_nesting_in_the_result_is_a_refusal_not_a_raise() -> None:
    deep = "[" * 100000 + "]" * 100000
    assert cand.raw_tool_candidate(trow(1, deep), HOME) is None


# --- bound before the parser ----------------------------------------------------------------------


def test_exact_boundary_is_inclusive_and_one_byte_over_never_reaches_the_parser() -> None:
    with counting() as c:
        assert cand.raw_tool_candidate(trow(1, padded(65536)), HOME) is not None
    assert (c.loads, c.parses) == (1, 1)
    with counting() as c:
        assert cand.raw_tool_candidate(trow(1, padded(65537)), HOME) is None
    assert (c.loads, c.parses) == (0, 0)


def test_wide_characters_are_weighed_in_utf8_bytes() -> None:
    content = wide()
    assert len(content) < 65536 < len(content.encode())
    with counting() as c:
        assert cand.raw_tool_candidate(trow(1, content), HOME) is None
    assert (c.loads, c.parses) == (0, 0)
    edge = json.dumps({"success": True, "image": IMG, "pad": "é" * 100}, ensure_ascii=False)
    assert len(edge.encode()) < 65536
    assert cand.raw_tool_candidate(trow(1, edge), HOME) is not None


def test_an_oversized_page_of_rows_never_parses() -> None:
    rows = [trow(i, padded(70000)) for i in range(1, 40)]
    with counting() as c:
        assert cand.collect_candidates(rows, HOME, frozenset(range(1, 40))) == ()
    assert (c.loads, c.parses) == (0, 0)


# --- collect_candidates ---------------------------------------------------------------------------


def test_native_ascending_page_yields_newest_first() -> None:
    rows = [trow(i) for i in (3, 9, 12, 40)]
    out = cand.collect_candidates(rows, HOME, frozenset({3, 9, 12, 40}))
    assert ids(out) == [40, 12, 9, 3]
    assert all(type(c) is MediaCandidate for c in out)


def test_tuple_pages_are_accepted_and_other_sequences_are_not() -> None:
    rows = [trow(1), trow(2)]
    full = frozenset({1, 2})
    assert ids(cand.collect_candidates(tuple(rows), HOME, full)) == [2, 1]

    class ListSub(list[Any]):
        pass

    class TupleSub(tuple[Any, ...]):
        __slots__ = ()

    for page in (ListSub(rows), TupleSub(rows), iter(rows), set(), "ab", None, 5, {1: 2}):
        assert cand.collect_candidates(page, HOME, full) == ()  # type: ignore[arg-type]


def test_row_count_is_bounded_by_the_history_maximum() -> None:
    rows = [trow(i, tool_name="other") for i in range(1, 1001)]
    rows[-1] = trow(1000)
    assert ids(cand.collect_candidates(rows, HOME, frozenset({1000}))) == [1000]
    assert cand.collect_candidates([*rows, trow(1001)], HOME, frozenset({1000})) == ()
    with counting() as c:
        assert cand.collect_candidates([*rows, trow(1001)], HOME, frozenset({1001})) == ()
    assert c.parses == 0


@pytest.mark.parametrize(
    "returned",
    [
        set(),
        {1},
        [1],
        (1,),
        None,
        frozenset(),
        frozenset({1, "2"}),
        frozenset({1, 2.0}),
        frozenset({1, None}),
        frozenset({0}),
        frozenset({-5, 1}),
        frozenset(range(1, 1002)),
    ],
)
def test_returned_ids_must_be_an_exact_bounded_frozenset_of_positive_ints(returned: Any) -> None:
    with counting() as c:
        assert cand.collect_candidates([trow(1)], HOME, returned) == ()
    assert c.parses == 0


def test_returned_ids_at_the_bound_are_accepted_and_subclasses_are_not() -> None:
    assert ids(cand.collect_candidates([trow(1)], HOME, frozenset(range(1, 1001)))) == [1]

    class Frozen(frozenset[int]):
        pass

    assert cand.collect_candidates([trow(1)], HOME, Frozen({1})) == ()


@pytest.mark.parametrize("home", ["", "\x00", HOME + "\x00", None, b"/x", Str(HOME)])
def test_an_invalid_home_yields_nothing_and_parses_nothing(home: Any) -> None:
    with counting() as c:
        assert cand.collect_candidates([trow(1)], home, frozenset({1})) == ()
    assert c.parses == 0


def test_a_foreign_or_respelled_home_yields_nothing() -> None:
    for home in ("/srv/hermes/profiles/p2", HOME + "/", "/srv//hermes/profiles/p1"):
        assert cand.collect_candidates([trow(1)], home, frozenset({1})) == ()


def test_unreturned_rows_never_count_and_never_parse() -> None:
    rows = [trow(i) for i in range(1, 301)]
    with counting() as c:
        out = cand.collect_candidates(rows, HOME, frozenset({2, 7}))
    assert ids(out) == [7, 2] and c.parses == 2


def test_non_image_rows_do_not_consume_attempts() -> None:
    rows = [trow(i, tool_name="web_search") for i in range(10, 400)] + [trow(1), trow(2)]
    rows += [trow(i, role="assistant") for i in range(400, 600)]
    out = cand.collect_candidates(rows, HOME, frozenset(range(1, 600)))
    assert ids(out) == [2, 1]


def test_invalid_content_consumes_an_attempt_and_is_not_replaced() -> None:
    newest_bad = [trow(i, BAD) for i in range(1000, 1000 - MAX_CANDIDATES_PER_RESPONSE, -1)]
    older_good = [trow(i) for i in range(1, 50)]
    returned = frozenset(range(1, 1001))
    with counting() as c:
        out = cand.collect_candidates([*older_good, *newest_bad], HOME, returned)
    assert out == () and c.parses == MAX_CANDIDATES_PER_RESPONSE


def test_one_hundred_twenty_eight_attempts_is_the_ceiling_with_malformed_mixed_in() -> None:
    rows: list[Any] = [trow(i) for i in range(1, 301)]
    rows[250] = trow(251, content=None)  # malformed but still an image_generate attempt
    rows[260] = {"id": 261}  # not an attempt at all
    rows[270] = "junk"
    rows[280] = None
    returned = frozenset(range(1, 301))
    with counting() as c:
        out = cand.collect_candidates(rows, HOME, returned)
    assert len(out) <= MAX_CANDIDATES_PER_RESPONSE
    assert c.parses <= MAX_CANDIDATES_PER_RESPONSE
    # 300..173 would be 128 attempts but 261, 271, 281 are not attempts, so three more fit
    assert ids(out)[0] == 300 and 251 not in ids(out)
    assert ids(out) == sorted(ids(out), reverse=True)


def test_duplicate_ids_refuse_whole_sidecar_before_parsing() -> None:
    other = result(PREFIX + "other.png")
    with counting() as c:
        out = cand.collect_candidates(
            [trow(5), trow(5, other), trow(5), trow(4)], HOME, frozenset({4, 5})
        )
    assert out == () and c.parses == 0
    # The unique-row control still parses both returned rows and binds the
    # digest to the actual tool result, so the refusal is attributable to the
    # duplicate-row preflight rather than an inert extraction path.
    with counting() as unique_count:
        unique = cand.collect_candidates([trow(5), trow(4)], HOME, frozenset({4, 5}))
    assert ids(unique) == [5, 4] and unique_count.parses == 2
    assert unique[0].raw_digest == scan._tool_digest(5, "image_generate", "call_5", GOOD)


def test_unsorted_and_descending_pages_give_the_same_result() -> None:
    rows = [trow(i) for i in range(1, 60)]
    full = frozenset(range(1, 60))
    expect = list(range(59, 0, -1))
    shuffled = list(rows)
    random.Random(3).shuffle(shuffled)
    for page in (rows, rows[::-1], shuffled):
        assert ids(cand.collect_candidates(page, HOME, full)) == expect


def test_a_failing_row_does_not_stop_the_others() -> None:
    class Boom(Mapping[Any, Any]):
        def __getitem__(self, key: Any) -> Any:
            raise RuntimeError("SECRET")

        def get(self, key: Any, default: Any = None) -> Any:
            raise RuntimeError("SECRET")

        def __iter__(self) -> Iterator[Any]:
            raise RuntimeError("SECRET")

        def __len__(self) -> int:
            raise RuntimeError("SECRET")

    rows = [trow(1), Boom(), trow(3), {1: 2}, trow("x"), trow(2, content=object())]
    out = never_raises(cand.collect_candidates, rows, HOME, frozenset({1, 2, 3}))
    assert ids(out) == [3, 1]


def test_a_hostile_id_does_not_break_ordering() -> None:
    class WeirdId(int):
        def __gt__(self, other: object) -> bool:
            raise RuntimeError("cmp")

    rows = [trow(WeirdId(9)), trow(3), trow(2**70), trow(1)]
    out = never_raises(cand.collect_candidates, rows, HOME, frozenset({1, 3, 2**70}))
    assert ids(out) == [2**70, 3, 1]


def test_get_that_fails_midway_is_closed() -> None:
    class Flaky(dict[str, Any]):
        calls = 0

        def get(self, key: str, default: Any = None) -> Any:
            Flaky.calls += 1
            if Flaky.calls > 6:
                raise RuntimeError("SECRET")
            return super().get(key, default)

    row = Flaky(trow(5))
    out = never_raises(cand.collect_candidates, [row, trow(4)], HOME, frozenset({4, 5}))
    assert type(out) is tuple


# --- P6: the digest is the accepted scanner's digest ----------------------------------------------


class FakeDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def get_active_message_ids(self, session_id: str) -> list[int]:
        return [r["id"] for r in self.rows]

    def get_messages(self, session_id: str, *, after_id: int, limit: int) -> list[dict[str, Any]]:
        return [r for r in self.rows if r["id"] > after_id][:limit]


def synthetic_pair(content: str = GOOD) -> list[dict[str, Any]]:
    call = {
        "id": "call_2",
        "type": "function",
        "function": {"name": "image_generate", "arguments": "{}"},
    }
    return [
        {"id": 1, "role": "assistant", "tool_calls": [call], "content": None},
        trow(2, content),
    ]


def test_digest_equals_the_active_set_scanners_claim_digest() -> None:
    rows = synthetic_pair()
    outcome = scan.scan_active_set(FakeDB(rows), "t", 2, current_tip=lambda: "t")
    assert outcome.ok and outcome.claim is not None
    out = cand.collect_candidates(rows, HOME, frozenset({2}))
    assert len(out) == 1
    assert out[0].tool_row_id == outcome.claim.tool_row_id == 2
    assert out[0].raw_digest == outcome.claim.tool_digest
    # the scanner's own image derives to the same pass: nothing from here is reused by it
    assert cand.derive_flat_name(outcome.claim.image, HOME) == "gen_secret_name.png"


def test_a_changed_byte_changes_the_digest_the_scanner_would_reject() -> None:
    first = scan.scan_active_set(FakeDB(synthetic_pair()), "t", 2, current_tip=lambda: "t")
    changed = GOOD.replace("true", "true ")
    second = scan.scan_active_set(FakeDB(synthetic_pair(changed)), "t", 2, current_tip=lambda: "t")
    assert first.claim is not None and second.claim is not None
    a = cand.collect_candidates(synthetic_pair(), HOME, frozenset({2}))[0]
    b = cand.collect_candidates(synthetic_pair(changed), HOME, frozenset({2}))[0]
    assert a.raw_digest == first.claim.tool_digest and b.raw_digest == second.claim.tool_digest
    assert a.raw_digest != b.raw_digest
    assert hashlib.sha256(GOOD.encode()).digest() != a.raw_digest


# --- inertness and imports ------------------------------------------------------------------------


def _imports(source: str) -> set[str]:
    """Every module a source imports, as written (`.x` for a relative import)."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            found.update(base + a.name if base == "." else base for a in node.names)
    return found


def test_imports_are_exactly_the_accepted_modules_and_stdlib() -> None:
    assert _imports(SOURCE) == {
        "__future__",
        "collections.abc",
        "typing",
        ".local_media_active_scan",
        ".local_media_file_safety",
        ".local_media_result",
        ".local_media_sidecar",
    }


def test_source_has_no_io_logging_or_raise() -> None:
    tree = ast.parse(SOURCE)
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"print", "open", "os", "Path", "logging", "json", "sys"}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"resolve", "stat", "exists", "realpath", "normpath", "getLogger"}


def test_importing_adds_only_the_accepted_modules_to_the_package_import() -> None:
    code = (
        "import sys\n"
        "import hmp_plugin\n"
        "before = set(sys.modules)\n"
        "import hmp_plugin.local_media_candidate\n"
        "print(sorted(m for m in set(sys.modules) - before if m.startswith('hmp_plugin')))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=PACKAGE.parent,
        env={**os.environ, "PYTHONPATH": str(PACKAGE.parent), "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=60,
    )
    added = ast.literal_eval(out.stdout.strip())
    assert added == [
        "hmp_plugin.local_media_active_scan",
        "hmp_plugin.local_media_candidate",
        "hmp_plugin.local_media_file_safety",
        "hmp_plugin.local_media_result",
        "hmp_plugin.local_media_sidecar",
    ], out.stdout + out.stderr
