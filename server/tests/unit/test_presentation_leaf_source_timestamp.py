"""Source timestamp semantics only; no native admission or receipt claims."""
import pytest

from hmp_plugin.presentation_native_metadata import _declared_leaf_source_before_data
from hmp_plugin.presentation_startup_artifacts import (
    ArtifactObservationError,
    _NativeMetadataSnapshot,
)

from .test_presentation_declared_leaf_policy import snapshot


@pytest.mark.parametrize(('mtime', 'expected'), [
    (0, 0), (0.0, 0), (1.9, 1), (-0.9, 0), (-1.9, -1),
    (2 ** 64 - 1, 2 ** 64 - 1), (-2 ** 64 + 1, -2 ** 64 + 1),
])
def test_source_timestamp_uses_actual_mtime_not_nanoseconds(mtime, expected):
    value = snapshot(mtime_ns=999999999999)
    value = _NativeMetadataSnapshot(value.identity, mtime)
    identity, timestamp = _declared_leaf_source_before_data(value, 501, 7)
    assert identity is value.identity
    assert type(timestamp) is int and timestamp == expected


@pytest.mark.parametrize('mtime', [
    True, '1.9', None, 2 ** 64, -2 ** 64,
    float('inf'), -float('inf'), float('nan'),
])
def test_source_timestamp_refuses_nonprimitive_or_out_of_range_values(mtime):
    value = _NativeMetadataSnapshot(snapshot().identity, mtime)
    with pytest.raises(ArtifactObservationError):
        _declared_leaf_source_before_data(value, 501, 7)


def test_source_timestamp_never_coerces_foreign_value():
    class Foreign:
        def __int__(self):
            raise AssertionError('foreign timestamp conversion must not execute')

        def __lt__(self, other):
            raise AssertionError('foreign timestamp comparison must not execute')

        def __gt__(self, other):
            raise AssertionError('foreign timestamp comparison must not execute')

    value = _NativeMetadataSnapshot(snapshot().identity, Foreign())
    with pytest.raises(ArtifactObservationError):
        _declared_leaf_source_before_data(value, 501, 7)


def test_source_timestamp_retains_original_leaf_policy():
    with pytest.raises(ArtifactObservationError):
        _declared_leaf_source_before_data(snapshot(mode=0o100666), 501, 7)
