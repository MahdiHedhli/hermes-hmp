"""Causal scope checks for the test-only lifecycle inverse; no runtime acceptance."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from . import approved_media_lifecycle_composition_witness as witness

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"


@pytest.mark.parametrize("name, expected", [
    ("adapter.py", "59c36a6aa405da940d6acb9a55d01be3ac79c4d8799465ed3c7aab9bfc923cfb"),
    ("server.py", "08f85d2c3bf69662506f555a80a86aa3163263e9d98d1d98214f6c1ce8ab663f"),
])
def test_recovers_exact_pre_lifecycle_source(name, expected):
    original = (PACKAGE / name).read_text()
    restored = witness.reverse_lifecycle_composition(original, name)
    assert hashlib.sha256(restored.encode()).hexdigest() == expected


@pytest.mark.parametrize("name", ["adapter.py", "server.py"])
def test_preserves_unrelated_dynamic_lookup_and_media_references(name):
    original = (PACKAGE / name).read_text()
    injected = "\n\ndef unapproved_media():\n    __import__('foreign')\n"
    restored = witness.reverse_lifecycle_composition(original + injected, name)
    assert restored.endswith(injected)


STAGES = (
    ("adapter.py", witness.ADAPTER_11A70F01),
    ("adapter.py", witness.ADAPTER_7C528066),
    ("server.py", witness.SERVER_30DEDF99),
    ("server.py", witness.SERVER_11A70F01),
    ("server.py", witness.SERVER_9AB26958),
)


def _stages():
    sources = {name: (PACKAGE / name).read_text() for name, _ in STAGES}
    for name, edits in STAGES:
        source = sources[name]
        for index, (accepted, _) in enumerate(edits):
            yield name, edits, source, index, accepted
        sources[name] = witness._reverse_exact_edits(source, edits)


@pytest.mark.parametrize("name, edits, source, index, accepted", list(_stages()))
@pytest.mark.parametrize("damage", ["changed", "duplicate"])
def test_each_exact_stage_refuses_changed_or_duplicate_blocks(
    name, edits, source, index, accepted, damage
):
    del name, index
    if damage == "changed":
        mutated = source.replace(accepted, accepted.replace("\n", " # changed\n", 1), 1)
    else:
        mutated = source + accepted
    assert mutated != source
    with pytest.raises(AssertionError):
        witness._reverse_exact_edits(mutated, edits)


@pytest.mark.parametrize("name, edits, source, index, accepted", list(_stages()))
def test_relocated_blocks_cannot_recover_pinned_parent(name, edits, source, index, accepted):
    del name, index
    expected = {
        id(witness.ADAPTER_11A70F01):
            "cb3477b7472da51e479746952a329f39d41d2a98ab49735a76c525c6790c2cc1",
        id(witness.ADAPTER_7C528066):
            "59c36a6aa405da940d6acb9a55d01be3ac79c4d8799465ed3c7aab9bfc923cfb",
        id(witness.SERVER_30DEDF99):
            "196ec1233bc265c9040460000dfe7192744c9bc710d65e154347ab784fe66f8c",
        id(witness.SERVER_11A70F01):
            "3736a37ee6651e89c5a9e477057c3560644b242afbfe896869c1c7c5496407c3",
        id(witness.SERVER_9AB26958):
            "08f85d2c3bf69662506f555a80a86aa3163263e9d98d1d98214f6c1ce8ab663f",
    }[id(edits)]
    moved = source.replace(accepted, "", 1) + accepted
    assert moved != source
    try:
        restored = witness._reverse_exact_edits(moved, edits)
    except AssertionError:
        return
    assert hashlib.sha256(restored.encode()).hexdigest() != expected
