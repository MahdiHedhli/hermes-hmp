"""Directory mode policy DATA retains existing POSIX privilege restrictions."""
from __future__ import annotations

import pytest

from hmp_plugin import presentation_native_metadata as metadata
from hmp_plugin import presentation_startup_artifacts as artifacts


@pytest.mark.parametrize(('mode', 'uid', 'allowed'), (
    (0o040755, 0, True),
    (0o041777, 0, True),
    (0o040700, 12345, True),
    (0o040750, 12345, True),
    (0o040777, 0, False),
    (0o040770, 12345, False),
    (0o041777, 12345, False),
    (0o044755, 0, False),
    (0o042755, 0, False),
    (0o044700, 12345, False),
    (0o040755, 54321, False),
    (0o100644, 12345, False),
    (0o120777, 0, False),
    (0o140755, 0, False),
))
def test_directory_policy_preserves_identity_and_denies_unsafe_modes(mode, uid, allowed):
    identity = (1, 2, mode, uid, 3, 1, 4096, 100, 101)
    snapshot = artifacts._NativeMetadataSnapshot(identity, 0.0)
    if allowed:
        assert metadata._directory_identity(snapshot, 12345) == identity[:5]
    else:
        with pytest.raises(artifacts.ArtifactObservationError):
            metadata._directory_identity(snapshot, 12345)
    assert snapshot.identity is identity


@pytest.mark.parametrize('field', ('snapshot', 'uid', 'identity', 'mode', 'mode_bool',
                                  'identity_subclass'))
def test_directory_policy_refuses_foreign_hooks_before_arithmetic(field):
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __and__(self, other):
            calls.append('and')
            raise AssertionError('foreign mode operation')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

    class ForeignTuple(tuple):
        def __getitem__(self, index):
            calls.append('index')
            raise AssertionError('foreign tuple index')

    uid = 12345
    identity = (1, 2, 0o040700, uid, 3, 1, 4096, 100, 101)
    if field == 'identity':
        identity = Foreign()
    elif field in ('mode', 'mode_bool'):
        identity = (*identity[:2], Foreign() if field == 'mode' else True, *identity[3:])
    elif field == 'identity_subclass':
        identity = ForeignTuple(identity)
    snapshot = artifacts._NativeMetadataSnapshot(identity, 0.0)
    if field == 'snapshot':
        snapshot = Foreign()
    elif field == 'uid':
        uid = Foreign()
    with pytest.raises(artifacts.ArtifactObservationError):
        metadata._directory_identity(snapshot, uid)
    assert calls == []
