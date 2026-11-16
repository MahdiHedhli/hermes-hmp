"""Exact historical projection, not permission/runtime qualification."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from .media_registry_permission_witness import EDITS, reverse_registry_permission_generation

NAME = "local_media_registry.py"
SOURCE = (Path(__file__).resolve().parents[2] / "hmp_plugin" / NAME).read_text()
PARENT_SHA = "b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2"


def test_exact_committed_delta_recovers_unchanged_historical_hash():
    restored = reverse_registry_permission_generation(SOURCE, NAME)
    assert hashlib.sha256(restored.encode()).hexdigest() == PARENT_SHA


def test_other_modules_are_not_projected():
    assert reverse_registry_permission_generation(SOURCE, "other.py") == SOURCE


def test_unrelated_registry_mutation_survives_and_fails_historical_hash():
    addition = "\n\ndef unapproved_registry_change():\n    return 123\n"
    restored = reverse_registry_permission_generation(SOURCE + addition, NAME)
    assert restored.endswith(addition)
    assert hashlib.sha256(restored.encode()).hexdigest() != PARENT_SHA


@pytest.mark.parametrize("index", range(len(EDITS)))
@pytest.mark.parametrize("damage", ["changed", "duplicate", "relocated"])
def test_each_hunk_damage_refuses_or_cannot_recover_parent(index, damage):
    accepted, _ = EDITS[index]
    if damage == "changed":
        at = next(i for i, character in enumerate(accepted) if not character.isspace())
        changed = accepted[:at] + ("!" if accepted[at] != "!" else "?") + accepted[at + 1:]
        mutated = SOURCE.replace(accepted, changed, 1)
    elif damage == "duplicate":
        mutated = SOURCE + accepted
    else:
        mutated = SOURCE.replace(accepted, "", 1) + accepted
    assert mutated != SOURCE
    try:
        restored = reverse_registry_permission_generation(mutated, NAME)
    except AssertionError:
        return
    assert damage == "relocated"
    assert hashlib.sha256(restored.encode()).hexdigest() != PARENT_SHA
