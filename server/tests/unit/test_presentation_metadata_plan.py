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
        ((4, 'source_after_hash', 2), (3, 'source_after_hash', 2)) if source else ())
    assert plan.progress == [0, None] and walk.metadata_slot == [None]
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
