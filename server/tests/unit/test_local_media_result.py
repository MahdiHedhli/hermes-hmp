"""The bounded result wrapper: the 64 KiB bound is applied before any JSON parse."""

from __future__ import annotations

import json

import pytest

from hmp_plugin import local_media_active_scan as scan
from hmp_plugin import local_media_result as res
from hmp_plugin.local_media_result import ResultRefusal, parse_image_result

LIMIT = 64 * 1024
PATH = "/home/user/.hermes/cache/images/gen_1.png"


def ok(**extra: object) -> str:
    return json.dumps({"success": True, "image": PATH, **extra}, ensure_ascii=False)


@pytest.fixture
def parse_calls(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    calls: list[object] = []
    real = scan._parse_image

    def spy(content: object) -> str:
        calls.append(content)
        return real(content)

    monkeypatch.setattr(scan, "_parse_image", spy)
    return calls


def test_success_returns_image() -> None:
    assert parse_image_result(ok()) == PATH


@pytest.mark.parametrize("content", [None, b"{}", 5, ["x"], {"success": True}])
def test_non_str_is_not_candidate(content: object) -> None:
    assert parse_image_result(content) is ResultRefusal.NOT_CANDIDATE


class StrSub(str):
    pass


def test_str_subclass_is_not_candidate() -> None:
    assert parse_image_result(StrSub(ok())) is ResultRefusal.NOT_CANDIDATE


@pytest.mark.parametrize(
    "content",
    [
        "",
        "not json",
        "[]",
        json.dumps({"success": 1, "image": PATH}),
        json.dumps({"success": "true", "image": PATH}),
        json.dumps({"image": PATH}),
        json.dumps({"success": True, "image": PATH, "error": None}),
        json.dumps({"success": True, "image": 7}),
        json.dumps({"success": True, "image": ""}),
        json.dumps({"success": True, "image": "a\0b"}),
        json.dumps({"success": True, "image": "x" * 4097}),
        '{"success": true, "image": "\\ud800"}',
        "[" * 60000,
    ],
)
def test_strict_predicate_refuses(content: str) -> None:
    assert parse_image_result(content) is ResultRefusal.NOT_CANDIDATE


def test_image_length_bounds() -> None:
    assert parse_image_result(json.dumps({"success": True, "image": "x"})) == "x"
    edge = "y" * 4096
    assert parse_image_result(json.dumps({"success": True, "image": edge})) == edge


def test_oversize_ascii_refused_before_parse(
    monkeypatch: pytest.MonkeyPatch, parse_calls: list[object]
) -> None:
    def boom(*_a: object, **_k: object) -> object:
        raise AssertionError("json.loads reached")

    monkeypatch.setattr(scan.json, "loads", boom)
    body = ok(pad="p" * LIMIT)
    assert len(body) > LIMIT
    assert parse_image_result(body) is ResultRefusal.TOO_LARGE
    assert parse_calls == []


def test_oversize_by_utf8_weight_refused_before_parse(
    monkeypatch: pytest.MonkeyPatch, parse_calls: list[object]
) -> None:
    monkeypatch.setattr(scan.json, "loads", lambda *_a, **_k: pytest.fail("parsed"))
    body = ok(pad="é" * (LIMIT // 2))  # fewer than 64 Ki chars, more than 64 KiB of UTF-8
    assert len(body) <= LIMIT < len(body.encode())
    assert parse_image_result(body) is ResultRefusal.TOO_LARGE
    assert parse_calls == []


def test_exact_limit_is_admitted() -> None:
    base = ok(pad="")
    body = ok(pad="p" * (LIMIT - len(base)))
    assert len(body.encode()) == LIMIT
    assert parse_image_result(body) == PATH
    assert parse_image_result(body + " ") is ResultRefusal.TOO_LARGE


def test_lone_surrogate_in_raw_text_refused_without_parse(parse_calls: list[object]) -> None:
    assert parse_image_result("é\ud800") is ResultRefusal.NOT_CANDIDATE
    assert parse_calls == []


def test_utf8_weight_gets_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, int | None]] = []
    real = scan.utf8_weight

    def spy(text: str, stop_after: int | None = None) -> int:
        seen.append((text, stop_after))
        return real(text, stop_after)

    monkeypatch.setattr(scan, "utf8_weight", spy)
    body = ok()
    parse_image_result(body)
    assert seen == [(body, LIMIT)]


def test_unexpected_exception_is_closed_and_content_free(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "/SECRET/host/path"

    def boom(content: object) -> str:
        raise RuntimeError(secret + str(content))

    monkeypatch.setattr(scan, "_parse_image", boom)
    with caplog.at_level("DEBUG"):
        out = parse_image_result(ok())
    assert out is ResultRefusal.UNAVAILABLE
    assert caplog.records == []
    for text in (repr(out), str(out), repr(out.value)):
        assert secret not in text and PATH not in text


def test_refusals_are_closed_and_repr_has_no_content() -> None:
    assert {r.value for r in ResultRefusal} == {
        "result_not_candidate",
        "result_too_large",
        "result_unavailable",
    }
    for r in ResultRefusal:
        assert "/" not in repr(r)


def test_uses_the_scanner_predicate_not_a_copy() -> None:
    assert res._scan is scan
    assert not hasattr(res, "json")
