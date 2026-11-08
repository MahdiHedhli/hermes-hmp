"""Unwired policy DATA checks; no native receipt/admission qualification."""
import pytest

from hmp_plugin.presentation_native_metadata import _declared_leaf_identity
from hmp_plugin.presentation_startup_artifacts import (
    _MAX_FILE,
    ArtifactObservationError,
    _NativeMetadataSnapshot,
)


def snapshot(**changes):
    values = {'dev': 1, 'inode': 2, 'mode': 0o100644, 'uid': 501, 'gid': 20,
              'links': 1, 'size': 7, 'mtime_ns': 8, 'ctime_ns': 9}
    values.update(changes)
    return _NativeMetadataSnapshot(tuple(values.values()), 0.0)


@pytest.mark.parametrize(('uid', 'size'), [(0, 0), (501, 7), (0, _MAX_FILE)])
def test_declared_leaf_identity_preserves_original_full_identity(uid, size):
    value = snapshot(uid=uid, size=size)
    assert _declared_leaf_identity(value, 501, size) is value.identity


@pytest.mark.parametrize('changes', [
    {'mode': 0o040755}, {'mode': 0o120777}, {'mode': 0o10644},
    {'mode': 0o104644}, {'mode': 0o102644},
    {'mode': 0o100664}, {'mode': 0o100646}, {'uid': 502},
    {'links': 0}, {'links': 2}, {'links': True}, {'size': 8},
    {'dev': True}, {'mtime_ns': 0.0},
])
def test_declared_leaf_refuses_policy_and_primitive_drift(changes):
    with pytest.raises(ArtifactObservationError):
        _declared_leaf_identity(snapshot(**changes), 501, 7)


@pytest.mark.parametrize(('uid', 'size'), [
    (True, 7), (-1, 7), (501, True), (501, -1), (501, _MAX_FILE + 1),
])
def test_declared_leaf_refuses_unbounded_or_coercible_policy_input(uid, size):
    with pytest.raises(ArtifactObservationError):
        _declared_leaf_identity(snapshot(), uid, size)


def test_declared_leaf_refuses_foreign_snapshot_without_getters():
    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError('foreign getter must not execute')

    with pytest.raises(ArtifactObservationError):
        _declared_leaf_identity(Foreign(), 501, 7)
