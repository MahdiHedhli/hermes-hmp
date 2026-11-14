"""Resolver selection in the F3 approval probe: real-build words, fail closed otherwise."""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

COMPAT_DIR = Path(__file__).resolve().parents[3] / "tools" / "compat"
sys.path.insert(0, str(COMPAT_DIR))
import approval_probes as probes  # noqa: E402


class LegacyBusy:
    _PLAINTEXT_APPROVAL_WORDS: ClassVar[dict[str, tuple[str, str]]] = {
        "yes": ("approve", ""),
        "no": ("deny", ""),
    }


INPUT_KEYS = (
    ("approve", ("approve", "")),
    ("deny", ("deny", "")),
    ("always", ("approve", "always")),
    ("session", ("approve", "session")),
)


ENGLISH = {"approve": "yes", "deny": "no", "always": "always", "session": "session"}
ACTIVE_LANGUAGE = dict(ENGLISH)  # stands in for the target's active-language lookup


class MethodBusy:
    _PLAINTEXT_APPROVAL_EXTRA_WORDS: ClassVar[dict[str, tuple[str, str]]] = {"👍": ("approve", "")}
    _PLAINTEXT_APPROVAL_INPUT_KEYS = INPUT_KEYS

    def _plaintext_approval_words(self):
        words = dict(self._PLAINTEXT_APPROVAL_EXTRA_WORDS)
        for key, verb_args in self._PLAINTEXT_APPROVAL_INPUT_KEYS:
            for word in (ENGLISH[key], ACTIVE_LANGUAGE[key]):
                words.setdefault(word, verb_args)
        return words


def test_legacy_constant_path_is_retained() -> None:
    words, attrs = probes.plaintext_approval_resolver(LegacyBusy)
    assert words == LegacyBusy._PLAINTEXT_APPROVAL_WORDS
    runner = probes.make_runner(attrs)
    assert runner._PLAINTEXT_APPROVAL_WORDS is LegacyBusy._PLAINTEXT_APPROVAL_WORDS


def test_method_resolver_words_come_from_target_build() -> None:
    words, attrs = probes.plaintext_approval_resolver(MethodBusy)
    assert words == {
        "👍": ("approve", ""),
        "yes": ("approve", ""),
        "session": ("approve", "session"),
        "always": ("approve", "always"),
        "no": ("deny", ""),
    }
    runner = probes.make_runner(attrs, extra=1)
    assert runner.extra == 1
    assert isinstance(runner._plaintext_approval_words, partial)
    assert runner._plaintext_approval_words() == words  # what _route_plaintext_approval calls


def test_method_resolver_returns_active_language_words_not_stale_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(ACTIVE_LANGUAGE, "approve", "oui")
    monkeypatch.setitem(ACTIVE_LANGUAGE, "always", "toujours")
    monkeypatch.setitem(ACTIVE_LANGUAGE, "deny", "non")

    class French(MethodBusy):
        _PLAINTEXT_APPROVAL_WORDS: ClassVar[dict[str, tuple[str, str]]] = {"stale": ("approve", "")}

    words, attrs = probes.plaintext_approval_resolver(French)
    assert {"oui", "non", "toujours"} <= set(words)
    assert {"yes", "no"} <= set(words)  # English remains available in every language.
    assert "stale" not in words
    runner = probes.make_runner(attrs)
    assert runner._plaintext_approval_words() == words


def test_method_takes_precedence_over_stale_constant() -> None:
    class Both(MethodBusy):
        _PLAINTEXT_APPROVAL_WORDS: ClassVar[dict[str, tuple[str, str]]] = {"stale": ("approve", "")}

    words, _ = probes.plaintext_approval_resolver(Both)
    assert "stale" not in words and "yes" in words


def test_neither_resolver_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="no known"):
        probes.plaintext_approval_resolver(SimpleNamespace)


def test_method_without_backing_attributes_fails_closed() -> None:
    class Broken:
        def _plaintext_approval_words(self):
            return {"yes": ("approve", "")}

    with pytest.raises(RuntimeError, match="unusable"):
        probes.plaintext_approval_resolver(Broken)


@pytest.mark.parametrize(
    "bad",
    [
        {},
        [],
        None,
        {"": ("approve", "")},
        {"yes": "approve"},
        {"yes": ("approve",)},
        {"yes": ("approve", 1)},
        {"yes": ("run", "")},
        {1: ("approve", "")},
    ],
)
def test_malformed_or_empty_word_set_fails_closed(bad) -> None:
    class Legacy:
        _PLAINTEXT_APPROVAL_WORDS = bad

    with pytest.raises(RuntimeError, match=r"empty|malformed"):
        probes.plaintext_approval_resolver(Legacy)

    class Method(MethodBusy):
        def _plaintext_approval_words(self):
            return bad

    with pytest.raises(RuntimeError, match=r"empty|malformed"):
        probes.plaintext_approval_resolver(Method)
