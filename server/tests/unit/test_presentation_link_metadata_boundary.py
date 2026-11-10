"""New link-family refusal fences; not native traversal qualification."""
import sys
from types import FunctionType

import pytest

from hmp_plugin import presentation_native_metadata as kernel
from hmp_plugin import presentation_native_link as link
from hmp_plugin.presentation_startup_artifacts import (
    ArtifactObservationError, _NativeLinkMetadataResource,
)


class Foreign:
    def __init__(self, calls):
        object.__setattr__(self, 'calls', calls)

    def __getattribute__(self, name):
        object.__getattribute__(self, 'calls').append(name)
        raise AssertionError('foreign link DATA was dispatched')

    def __eq__(self, other):
        object.__getattribute__(self, 'calls').append('equality')
        raise AssertionError('foreign link equality was dispatched')


def rejected_cohort():
    calls = []
    owner = object()
    foreign = Foreign(calls)
    resource = _NativeLinkMetadataResource(owner, None, foreign, (3, 'synthetic', 0),
                                           0, ('synthetic', 7), foreign)
    values = [None] * len(kernel._MetadataOperation._fields)
    values[0], values[1] = owner, resource
    operation = kernel._MetadataOperation(*values)
    consumer = kernel._LinkMetadataConsumer(foreign, operation, None, [None], (), foreign)
    return owner, resource, operation, consumer, calls


def test_link_metadata_uses_the_existing_kernel_without_a_new_native_producer():
    assert link._LinkMetadataConsumer is kernel._LinkMetadataConsumer
    assert link._produce_shared is kernel._produce_directory_metadata
    assert link._consume_shared is kernel._consume_directory_policy
    assert link._ack_shared is kernel._ack_directory_policy
    assert link._attached_shared is kernel._acked_directory_commit_tail
    assert link._retired_shared is kernel._retired_directory_commit_tail


@pytest.mark.parametrize('stage', ('resource', 'origin', 'stages', 'caller', 'latched', 'lifetime'))
def test_unbound_link_family_refuses_before_foreign_dispatch(stage):
    owner, resource, operation, consumer, calls = rejected_cohort()
    functions = {
        'resource': lambda: kernel._resource_tail(owner, resource),
        'origin': lambda: kernel._closed_link_engine_origin(owner, resource),
        'stages': lambda: kernel._link_stage_functions(owner, resource),
        'caller': lambda: kernel._run_directory_observation(owner, resource),
        'latched': lambda: kernel._latched_directory_resource_tail(owner, consumer),
        'lifetime': lambda: kernel._link_current_lifetime_tail(owner, consumer),
    }
    with pytest.raises(ArtifactObservationError):
        functions[stage]()
    assert calls == []


@pytest.mark.parametrize('stage', ('link_pending', 'probe_missing'))
def test_link_consumer_never_accepts_probe_reported_missing(stage):
    owner, resource, operation, consumer, calls = rejected_cohort()
    actual = kernel._ReportedMissingMetadataReturn(operation, None, consumer)
    with pytest.raises(ArtifactObservationError):
        if stage == 'link_pending':
            kernel._pending_directory_cohort_tail(owner, consumer, actual)
        else:
            kernel._reported_missing_operation_tail(owner, consumer, actual)
    assert calls == []
    assert consumer.baseline is None and consumer.eof is None
    assert type(consumer) is not kernel._DirectoryConsumer
    assert type(consumer) is not kernel._ProbeConsumer


def test_link_helper_names_cannot_select_an_arbitrary_callback():
    owner, resource, operation, consumer, calls = rejected_cohort()
    with pytest.raises(ArtifactObservationError):
        kernel._link_policy_helper(owner, resource, 'synthetic_forbidden_callback')
    assert calls == []


def packet():
    """Local packet validation only; never an entry/Scope or native allowance."""
    from hmp_startup.link_factory_origin import _pin_function, _pin_type

    names = ('_engine_origin_tail', '_execution_mirrors', '_opened_chain_tail',
             '_lifetime_tail', '_resource_tail', '_prepare_shared_consumer',
             '_latch_shared_consumer', '_make_shared_commit', '_commit_shared_tail',
             '_publish_shared_ack', '_acked_shared_history', '_produce_shared',
             '_consume_shared', '_ack_shared', '_attached_shared', '_retired_shared',
             '_resource_bindings', '_byte_record_tail', '_make_shared_bytes_commit', '_commit_shared_bytes_tail',
             '_publish_shared_bytes_ack', '_acked_shared_bytes_history')
    functions = tuple(_pin_function(name, vars(link)[name], vars(link)[name].__globals__)
                      for name in names)
    kernel_functions = tuple(_pin_function(name, function, function.__globals__)
                             for name, function in sorted(vars(kernel).items())
                             if name.startswith('_') and type(function) is FunctionType)
    types = tuple(_pin_type(kind) for kind in (
        link._LinkExecution, kernel._LinkMetadataConsumer,
        link._LinkMetadataCommit, _NativeLinkMetadataResource,
        kernel._LinkBytesConsumer, link._LinkBytesCommit, link._NativeLinkBytesResource,
        kernel._LinkBytesOperation, kernel._LinkBytesResult, kernel._LinkBytesReturn))
    kind = link._LinkRead
    namespace = vars(kind)
    constructor = namespace['__init__']
    record_pin = (kind, None, tuple(namespace.items()), constructor, constructor.__code__,
                  constructor.__globals__, constructor.__defaults__, kind.__bases__,
                  tuple((name, namespace.get(name)) for name in (
                      '__getattribute__', '__getattr__', '__setattr__', '__delattr__')))
    types = (*types, record_pin)
    return sys.modules[link.__name__], types, functions, kernel_functions


def test_local_packet_validator_returns_the_actual_packet_without_admitting_work():
    original = packet()
    assert link._engine_origin_tail(original) is original


@pytest.mark.parametrize('fault', ('export', 'code', 'defaults', 'kwdefaults', 'foreign_key'))
def test_first_pin_helper_is_authenticated_before_it_can_execute(monkeypatch, fault):
    original = packet()
    calls = []

    def replacement(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign pin helper executed')

    def changed_code(*args, **kwargs):
        raise AssertionError('changed pin helper executed')

    if fault == 'export':
        monkeypatch.setattr(kernel, '_link_function_pin', replacement)
    elif fault == 'code':
        monkeypatch.setattr(kernel._link_function_pin, '__code__', changed_code.__code__)
    elif fault == 'defaults':
        monkeypatch.setattr(kernel._link_function_pin, '__defaults__', ('SYNTHETIC',))
    elif fault == 'kwdefaults':
        monkeypatch.setattr(kernel._link_function_pin, '__kwdefaults__', {'synthetic': True})
    else:
        class Key:
            def __hash__(self):
                return hash('_link_function_pin')

            def __eq__(self, other):
                calls.append('equality')
                return False

        monkeypatch.setitem(vars(kernel), Key(), object())
        calls.clear()
    with pytest.raises(ArtifactObservationError):
        link._engine_origin_tail(original)
    assert calls == []


@pytest.mark.parametrize('stage', ('resource', 'lifetime', 'latch', 'make', 'history', 'opened'))
def test_direct_link_policy_fences_execution_before_field_access(stage):
    owner, resource, operation, consumer, calls = rejected_cohort()
    functions = {
        'resource': lambda: link._resource_tail(owner, resource),
        'lifetime': lambda: link._lifetime_tail(owner, consumer),
        'latch': lambda: link._latch_shared_consumer(owner, consumer),
        'make': lambda: link._make_shared_commit(owner, consumer, None),
        'history': lambda: link._acked_shared_history(owner, consumer, None),
        'opened': lambda: link._opened_chain_tail(Foreign(calls)),
    }
    with pytest.raises(ArtifactObservationError):
        functions[stage]()
    assert calls == []


def test_commit_cursor_is_fenced_before_its_fields_or_pending_policy_are_read():
    calls = []
    owner = object()
    values = [None] * len(link._LinkExecution._fields)
    values[0] = owner
    execution = link._LinkExecution(*values)
    consumer = kernel._LinkMetadataConsumer(execution, None, None, [None], (), None)
    before = link.policy._LinkPathCursor(None, 0, (), None, None, None)
    commit = link._LinkMetadataCommit(consumer, 0, 0, before, Foreign(calls), ())
    with pytest.raises(ArtifactObservationError):
        link._commit_shared_tail(owner, consumer, None, commit)
    assert calls == []


def test_first_pin_pairs_are_fenced_before_any_equality_protocol():
    original = packet()
    calls = []
    rows = tuple((row[:6] + (Foreign(calls),)) if row[0] == '_link_function_pin' else row
                 for row in original[3])
    malformed = (*original[:3], rows)
    with pytest.raises(ArtifactObservationError):
        link._engine_origin_tail(malformed)
    assert calls == []


@pytest.mark.parametrize('position', ('before', 'after'))
def test_cursor_positions_are_fenced_before_pending_policy_dispatch(monkeypatch, position):
    from .test_presentation_link_path_policy import _at

    calls = []
    owner = object()
    values = [None] * len(link._LinkExecution._fields)
    values[0] = owner
    execution = link._LinkExecution(*values)
    consumer = kernel._LinkMetadataConsumer(execution, None, None, [None], (), None)
    before = _at(1)
    after = link.policy._advance(before, 'returned', (1, 10, 0o040755, 0, 0))
    if position == 'before':
        before = before._replace(position=Foreign(calls))
    else:
        after = after._replace(position=Foreign(calls))
    commit = link._LinkMetadataCommit(consumer, 0, 1, before, after, ())

    def pending_trap(*args):
        calls.append('pending')
        raise AssertionError('unfenced cursor reached policy dispatch')

    # A rejecting trap proves ordering; it never returns a validation or grants
    # native work and cannot make an otherwise invalid cohort proceed.
    monkeypatch.setattr(kernel, '_pending_directory_cohort_tail', pending_trap)
    with pytest.raises(ArtifactObservationError):
        link._commit_shared_tail(owner, consumer, None, commit)
    assert calls == []


@pytest.mark.parametrize('drift', ('none', 'opened', 'arguments', 'position'))
def test_pure_final_binding_rejects_stale_descriptor_or_fd_data(drift):
    """Synthetic tuple mirrors only: no original FD, registration or admission."""
    owner, registration = object(), object()
    descriptor = link._NativeOpenedDescriptor(None, 7, None)
    site = (4, 0, None)
    cursor = link.policy._LinkPathCursor(None, 1, (), None, None, None)
    values = [None] * len(link._LinkExecution._fields)
    values[0], values[1], values[5], values[9], values[12] = (
        owner, registration, ((0, '/', None), site), [cursor], [descriptor])
    execution = link._LinkExecution(*values)
    resource = _NativeLinkMetadataResource(owner, registration, execution, site, 1,
                                           (descriptor.fd,), descriptor)
    calls = []
    if drift == 'none':
        assert link._resource_bindings(execution, resource) is resource
        return
    if drift == 'opened':
        # Same numeric FD is insufficient: the original descriptor is required.
        execution.opened[0] = link._NativeOpenedDescriptor(None, 7, None)
    elif drift == 'arguments':
        resource = resource._replace(arguments=(9,))
    else:
        execution.cursor[0] = cursor._replace(position=Foreign(calls))
    with pytest.raises(ArtifactObservationError):
        link._resource_bindings(execution, resource)
    assert calls == []
