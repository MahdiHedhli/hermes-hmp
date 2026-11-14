"""Synthetic memory accounting; not a native call, receipt or image test."""
import pytest

from hmp_plugin import presentation_native_metadata as kernel
from hmp_plugin.presentation_startup_artifacts import (
    ArtifactObservationError, _LinkRead, _NativeLinkBytesResource,
)


def memory_count(before_value=10):
    owner, scope, root, cell = object(), object(), object(), object()
    before = (owner, scope, before_value)
    own = dict(_scope=scope, _origin=scope, _root_cell=root, _cell=cell,
               _count_cell=before, _bytes_read=before_value)
    runtime, execution = [before], [before]
    record = _LinkRead(object(), 0, 0, before)
    context = (own, scope, root, cell, runtime, execution, vars(record), before)
    result = kernel._LinkBytesResult([None], [None], object(), [None], None, [None], [None],
                                     [None], before, [None], record, vars(record), context)
    resource = _NativeLinkBytesResource(owner, None, None, (5, 'synthetic', 0), 0,
                                        (b'synthetic', 7), None, record, None)
    values = [None] * len(kernel._LinkBytesOperation._fields)
    values[0], values[1], values[7], values[13] = owner, resource, 5, result
    operation = kernel._LinkBytesOperation(*values)
    result.attempt[0] = operation
    record.native_result = result
    record.attempted = True  # synthetic caller-held return, not a real native call
    return operation, result, record, own, runtime, execution, before


@pytest.mark.parametrize('size', (0, 3, 300, 4096))
def test_actual_supplied_length_is_recorded_once_without_raw_storage_or_ack(size):
    operation, result, record, own, runtime, execution, before = memory_count()
    returned = kernel._capture_link_byte_count(operation, b'x' * size)
    assert returned is result.counted[0] is record.after is own['_count_cell']
    assert returned is runtime[0] is execution[0]
    assert returned[0] is before[0] and returned[1] is before[1]
    assert own['_bytes_read'] == returned[2] == before[2] + size
    assert result.length[0] == record.length == size and record.returned
    assert record.data is None and record.acknowledgement is None
    assert result.acknowledged == [None] and result.before_count is before
    with pytest.raises(ArtifactObservationError):
        kernel._capture_link_byte_count(operation, b'x' * size)
    assert own['_count_cell'] is returned and own['_bytes_read'] == before[2] + size


@pytest.mark.parametrize('changed', ('_scope', '_origin', '_root_cell', '_cell', '_count_cell',
                                     '_bytes_read', 'runtime', 'execution', 'counted'))
def test_replacements_are_preserved_and_known_failure_is_audited_without_replay(changed):
    operation, result, record, own, runtime, execution, before = memory_count()
    replacement = object()
    target = {'runtime': runtime, 'execution': execution, 'counted': result.counted}.get(changed)
    if target is None:
        own[changed] = replacement
    else:
        target[0] = replacement
    with pytest.raises(ArtifactObservationError):
        kernel._capture_link_byte_count(operation, b'synthetic')
    kernel._retain_link_byte_failure(operation, b'synthetic')
    assert record.returned and record.unknown and record.length == result.length[0] == 9
    assert record.data is None and record.acknowledgement is None
    assert result.acknowledged == [None]
    assert (own[changed] is replacement if target is None else target[0] is replacement)
    if changed != '_bytes_read':
        assert own['_bytes_read'] == before[2]


def test_quota_refusal_preserves_real_length_and_count_without_ack():
    operation, result, record, own, runtime, execution, before = memory_count(kernel._MAX_TOTAL)
    with pytest.raises(ArtifactObservationError):
        kernel._capture_link_byte_count(operation, b'bad')
    kernel._retain_link_byte_failure(operation, b'bad')
    assert own['_bytes_read'] == kernel._MAX_TOTAL + 3
    assert own['_count_cell'] is result.counted[0] is runtime[0] is execution[0]
    assert record.returned and record.unknown and record.length == 3
    assert record.acknowledgement is None and result.acknowledged == [None]


def test_unknown_return_never_guesses_length_or_count():
    operation, result, record, own, runtime, execution, before = memory_count()
    record.attempted = True
    kernel._retain_link_byte_failure(operation, None)
    kernel._mark_link_byte_failed(operation)
    assert record.unknown and not record.returned and record.length is None
    assert result.length == result.counted == [None]
    assert own['_count_cell'] is runtime[0] is execution[0] is before


def test_unattempted_refusal_does_not_invent_unknown_native_work():
    operation, result, record, own, runtime, execution, before = memory_count()
    record.attempted = False
    kernel._mark_link_byte_failed(operation)
    assert not record.attempted and not record.returned and not record.unknown
    assert result.length == result.counted == [None]


@pytest.mark.parametrize('field', ('native_result', 'attempted', 'returned', 'length', 'after',
                                  'unknown', 'data', 'acknowledgement', 'before'))
def test_record_drift_is_preserved_while_actual_length_stays_in_owned_result(field):
    operation, result, record, own, runtime, execution, before = memory_count()
    replacement = object()
    vars(record)[field] = replacement
    with pytest.raises(ArtifactObservationError):
        kernel._capture_link_byte_count(operation, b'synthetic')
    assert vars(record)[field] is replacement
    assert result.length == [9] and result.counted == [None]
    assert own['_count_cell'] is runtime[0] is execution[0] is before
    kernel._retain_link_byte_failure(operation, b'synthetic')
    assert vars(record)[field] is replacement
    assert result.length == [9] and result.acknowledged == [None]


@pytest.mark.parametrize('mismatch', ('opcode', 'operation_type', 'result_type', 'resource_type'))
def test_byte_family_cannot_masquerade_as_metadata(mismatch):
    operation, result, record, own, runtime, execution, before = memory_count()
    if mismatch == 'opcode':
        operation = operation._replace(operation=4)
    elif mismatch == 'operation_type':
        operation = kernel._MetadataOperation(*operation)
    elif mismatch == 'result_type':
        operation = operation._replace(result=kernel._MetadataResult(*result[:7]))
    else:
        operation = operation._replace(resource=None)
    assert not kernel._operation_result_family(operation)
    with pytest.raises(ArtifactObservationError):
        kernel._capture_link_byte_count(operation, b'synthetic')
    assert not record.returned and own['_count_cell'] is before


def test_byte_consumer_cannot_consume_probe_reported_missing():
    operation, result, record, own, runtime, execution, before = memory_count()
    consumer = kernel._LinkBytesConsumer(None, operation, None, [None], (), None)
    actual = kernel._ReportedMissingMetadataReturn(operation, result, consumer)
    with pytest.raises(ArtifactObservationError):
        kernel._pending_directory_cohort_tail(None, consumer, actual)
    with pytest.raises(ArtifactObservationError):
        kernel._reported_missing_operation_tail(None, consumer, actual)
    assert result.acknowledged == [None] and own['_count_cell'] is before
