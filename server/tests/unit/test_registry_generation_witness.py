"""Preservation witness and independently exercised generation guards."""

import ast
import dataclasses
import hashlib
from pathlib import Path

import pytest

from hmp_plugin import local_media_registry as reg

from .registry_generation_witness import (
    CURRENT_SHA256,
    ORIGINAL_SHA256,
    reverse_registry_permission_generations,
)
from .test_local_media_registry import binding, caller, make


def test_exact_delta_recovers_original_frozen_hash_without_replacing_it():
    current = Path(reg.__file__).read_text()
    assert hashlib.sha256(current.encode()).hexdigest() == CURRENT_SHA256
    restored = reverse_registry_permission_generations(current)
    frozen_tree = ast.parse(
        Path(__file__).with_name("test_local_media_active_batch.py").read_text()
    )
    frozen = next(
        n.value
        for n in frozen_tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "FROZEN" for t in n.targets)
    )
    assert ast.literal_eval(frozen)["local_media_registry.py"] == ORIGINAL_SHA256
    assert hashlib.sha256(restored.encode()).hexdigest() == ORIGINAL_SHA256


@pytest.mark.parametrize(
    "old,new",
    [
        ("and self.permission_generation == caller.permission_generation", "and True"),
        ("len(value) not in (0, 4)", "len(value) not in (0, 4, 5)"),
        ("type(item) is not int", "not isinstance(item, int)"),
        ("_permission_generation(self.permission_generation)", "None"),
    ],
)
def test_unknown_generation_guard_changes_cannot_be_stripped(old, new):
    source = Path(reg.__file__).read_text()
    assert old in source
    with pytest.raises(AssertionError):
        reverse_registry_permission_generations(source.replace(old, new))


@pytest.mark.parametrize("coordinate", range(4))
def test_each_generation_coordinate_isolated_from_same_identity_reference(coordinate):
    registry, _clock = make()
    original = (0, 0, 1, -1)
    changed = list(original)
    changed[coordinate] += 1
    changed = tuple(changed)
    first = registry.mint(binding(permission_generation=original))
    assert registry.lookup(first, caller(permission_generation=original)) is not None
    assert registry.lookup(first, caller(permission_generation=changed)) is None
    assert registry.mint(binding(permission_generation=changed)) != first


@pytest.mark.parametrize("factory", [binding, caller])
@pytest.mark.parametrize(
    "generation",
    [
        None,
        True,
        [],
        [0, 0, 0, 0],
        (0,),
        (0, 0, 0),
        (0, 0, 0, 0, 0),
        (False, 0, 0, 0),
        (-2, 0, 0, 0),
        (2**63, 0, 0, 0),
        (1.0, 0, 0, 0),
        ("1", 0, 0, 0),
    ],
)
def test_both_record_constructors_refuse_malformed_generation(factory, generation):
    with pytest.raises(reg.RegistryRefusal):
        factory(permission_generation=generation)


@pytest.mark.parametrize("factory", [binding, caller])
@pytest.mark.parametrize("generation", [(), (-1, 0, 1, 2**63 - 1)])
def test_accepted_generation_is_retained_without_copy_or_coercion(factory, generation):
    record = factory(permission_generation=generation)
    assert record.permission_generation is generation
    assert "permission_generation" in {field.name for field in dataclasses.fields(record)}
