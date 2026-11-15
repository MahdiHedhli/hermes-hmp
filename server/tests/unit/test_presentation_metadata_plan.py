"""Site-plan DATA cannot admit work; foreign fields must not invoke hooks."""
from __future__ import annotations

import pytest

from hmp_plugin import presentation_startup_artifacts as a


def fixture(source):
    owner = object()
    fields = dict.fromkeys(a._Scope._fields)
    fields['source_digest'] = object() if source else None
    scope = a._Scope(**fields)
    fields = dict.fromkeys(a._NativeScopeRegistration._fields)
    fields['scope'] = scope
    registration = a._NativeScopeRegistration(**fields)
    expected = a.ExpectedArtifact('/root/leaf.py', 10, 'a' * 64)
    walk = a._NativeDeclaredWalk(owner, scope, None, None, (expected,), expected, 0,
                                 ('/', 'root', 'leaf.py'), [0], [None], [None])
    return owner, registration, walk


@pytest.mark.parametrize('source', (False, True))
def test_declared_site_order_is_bounded_data_without_native_authority(source):
    owner, registration, walk = fixture(source)
    plan = a._prepare_declared_metadata_plan(owner, registration, walk)
    assert plan.walk is walk and plan.owner is owner and plan.expected is walk.expected
    assert plan.definitions[:2] == ((4, 'directory', 0), (4, 'directory', 1))
    assert plan.definitions[2:6] == (
        (3, 'leaf_before', 2), (4, 'leaf_opened', 2),
        (4, 'leaf_after_read', 2), (3, 'leaf_after_read', 2))
    assert plan.definitions[6:] == (
        (4, 'directory_after_hash', 0), (3, 'directory_after_hash', 0),
        (4, 'directory_after_hash', 1), (3, 'directory_after_hash', 1))
    assert plan.progress == [0, None] and walk.metadata_slot == [None]
    assert len(plan.variants) == len(plan.definitions)
    assert len({id(variant) for variant in plan.variants}) == len(plan.variants)
    for ordinal, variant in enumerate(plan.variants):
        assert variant.owner is owner and variant.walk is walk
        assert variant.expected is walk.expected and variant.ordinal == ordinal
        assert variant.site is plan.definitions[ordinal]
        assert a._native_declared_metadata_site_tail(owner, plan, ordinal) is variant
    # Merely constructing coherent plan DATA does not establish original lineage.
    with pytest.raises(a.ArtifactObservationError):
        a._native_scope_current(owner, registration)
    walk.metadata_slot[0] = plan
    with pytest.raises(a.ArtifactObservationError):
        a._prepare_declared_metadata_plan(owner, registration, walk)


@pytest.mark.parametrize('field', ('registration', 'declaration', 'index', 'expected',
                                  'path', 'components', 'slot'))
def test_malformed_plan_fields_have_no_foreign_hooks(field):
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __getitem__(self, index):
            calls.append('getitem')
            raise AssertionError('foreign index')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

    owner, registration, walk = fixture(True)
    if field == 'registration':
        registration = Foreign()
    elif field == 'path':
        expected = walk.expected._replace(path=Foreign())
        walk = walk._replace(expected=expected, declaration=(expected,))
    else:
        key = 'metadata_slot' if field == 'slot' else field
        walk = walk._replace(**{key: Foreign()})
    with pytest.raises(a.ArtifactObservationError):
        a._prepare_declared_metadata_plan(owner, registration, walk)
    assert calls == []


@pytest.mark.parametrize('fault', [
    'foreign_variants', 'foreign_variant', 'foreign_walk', 'owner',
    'ordinal_bool', 'copied_site', 'unknown_role', 'wrong_operation',
    'swapped_row', 'component_bool',
])
def test_fixed_variant_binding_refuses_drift_without_foreign_hooks(fault):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

    owner, registration, walk = fixture(False)
    plan = a._prepare_declared_metadata_plan(owner, registration, walk)
    variant = plan.variants[0]
    if fault == 'foreign_variants':
        plan = plan._replace(variants=Foreign())
    elif fault == 'foreign_walk':
        plan = plan._replace(walk=Foreign())
    else:
        if fault == 'foreign_variant':
            variant = Foreign()
        elif fault == 'owner':
            variant = variant._replace(owner=object())
        elif fault == 'ordinal_bool':
            variant = variant._replace(ordinal=False)
        elif fault == 'copied_site':
            copied = list(variant.site)
            variant = variant._replace(site=tuple(copied))
        elif fault == 'swapped_row':
            variant = plan.variants[1]
        else:
            site = (4, 'unknown', 0) if fault == 'unknown_role' else (
                (3, 'directory', 0) if fault == 'wrong_operation' else (4, 'directory', False))
            plan = plan._replace(definitions=(site, *plan.definitions[1:]))
            variant = variant._replace(site=site)
        plan = plan._replace(variants=(variant, *plan.variants[1:]))
    with pytest.raises(a.ArtifactObservationError):
        a._native_declared_metadata_site_tail(owner, plan, 0)
    assert calls == []
