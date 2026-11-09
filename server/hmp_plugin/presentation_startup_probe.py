"""Experimental native startup absence driver; source integration unqualified.

Scope retention binds original source/path/code/type inputs. The actual cache
observer carries the driver's literal finish through Missing/effect/pass
publication using the shared metadata pipeline. This source is not installed;
normal native and interruption behavior still require exact-candidate tests.
"""
from __future__ import annotations

import errno
import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from . import presentation_startup_probe_policy as policy
from . import presentation_gateway_activation as activation_module

from . import presentation_native_metadata as metadata
from .presentation_metadata_custody import (
    _directory_payload_cells, _retire_directory_payload_data,
)
from .presentation_startup_artifacts import (
    StartupArtifactOwner, _NativeOpenedDescriptor, _NativeStartupProbeMetadataResource,
    _NativeScopeRegistration, _capture_native_scope, _descriptor_closed_in_scope,
    _descriptor_refused, _native_actor_context, _native_metadata_snapshot,
    _native_post_actor_state, _native_pre_actor_state, _native_work_origin_tail,
    _native_descriptor_opened, _native_work_registration_tail, _Scope, _require,
)


class _ProbeExecution(NamedTuple):
    owner: object
    plan: object
    registration: object
    origin: tuple
    count: tuple
    next_site: list
    pending: list
    history: list
    opened: list
    outcome: list
    failed: list
    finished: list
    budget: tuple
    cursor: list

    def __repr__(self):
        return '<StartupProbeExecution experimental no-image-authority>'


_ProbeConsumer = metadata._ProbeConsumer


_ProbeReturn = metadata._DirectoryMetadataReturn


class _ProbeCommit(NamedTuple):
    consumer: _ProbeConsumer
    sequence: int
    site: int
    next_site: int
    category: str
    identity: object
    outcome: object
    cursor: object

    def __repr__(self):
        return '<StartupProbeCommit raw-free metadata redacted>'


class _ProbeFinish(NamedTuple):
    execution: _ProbeExecution
    predecessor: _ProbeCommit
    resources: tuple
    outcome: tuple
    closure: tuple

    def __repr__(self):
        return '<StartupProbeFinish original metadata-only return>'


def _new_probe_engine_origin():
    module = sys.modules.get(__name__)
    _require(type(module) is ModuleType and vars(module) is globals())
    from .presentation_startup_cache import _Missing

    kinds = (_ProbeExecution, _ProbeConsumer, _ProbeReturn, _ProbeCommit,
             metadata._ReportedMissingMetadataReturn, _ProbeFinish, _Missing)
    types = tuple((kind, kind._fields,
                   tuple(vars(kind).get(name) for name in kind._fields),
                   kind.__new__, kind.__new__.__code__) for kind in kinds)
    functions = tuple((name, globals()[name], globals()[name].__code__) for name in (
        '_engine_origin_tail', '_execution_tail', '_history_tail',
        '_resource_tail', '_resource', '_consumer_tail',
        '_policy_values', '_run_observation', '_open_ancestor',
        '_finish', '_run_startup_probe', '_lifecycle_tail',
        '_prepare_shared_consumer', '_latch_shared_consumer', '_produce_shared',
        '_consume_shared', '_ack_shared', '_retired_shared', '_history_mirrors_tail', '_attached_shared',
        '_make_shared_commit', '_commit_shared_tail', '_acked_shared_history', '_publish_shared_ack',
        '_finished_state_tail', '_opened_chain_tail', '_new_startup_probe_origin', '_blueprint_tail', '_new_startup_plan', '_startup_plan_tail', '_cursor_ordinal', '_historical_finish_tail', '_path_rows', '_policy_pins_tail', '_historical_finish_mirrors', '_historical_cohort', '_startup_parent_witness'))
    return (module, types, functions, OSError.__dict__['errno'],
            OSError.__dict__['filename'], errno.ENOENT,
            (metadata, tuple((name, vars(metadata).get(name), vars(metadata).get(name).__code__)
                             for name in ('_produce_directory_metadata',
                                          '_consume_directory_policy', '_ack_directory_policy',
                                          '_probe_shared_call', '_probe_function_namespace'))))


def _engine_origin_tail(origin):
    _require(type(origin) is tuple and len(origin) == 7
             and type(origin[0]) is ModuleType
             and sys.modules.get(__name__) is origin[0]
             and vars(origin[0]) is globals()
             and type(origin[1]) is tuple and len(origin[1]) == 7
             and type(origin[2]) is tuple and len(origin[2]) == 37
             and origin[3] is OSError.__dict__['errno']
             and origin[4] is OSError.__dict__['filename']
             and type(origin[5]) is int and origin[5] == errno.ENOENT)
    _require(type(origin[6]) is tuple and len(origin[6]) == 2
             and origin[6][0] is metadata and type(origin[6][1]) is tuple
             and len(origin[6][1]) == 5
             and sys.modules.get('hmp_plugin.presentation_native_metadata') is metadata)
    for name, function, code in origin[6][1]:
        _require(type(name) is str and type(function) is FunctionType
                 and vars(metadata).get(name) is function and function.__code__ is code
                 and function.__globals__ is vars(metadata))
    names = ('_ProbeExecution', '_ProbeConsumer', '_ProbeReturn', '_ProbeCommit',
             None, '_ProbeFinish', None)
    for index, (kind, fields, members, constructor, constructor_code) in enumerate(origin[1]):
        if names[index] is not None:
            _require(globals().get(names[index]) is kind)
        _require(type(kind) is type and vars(kind).get('_fields') is fields
                 and type(constructor) is FunctionType
                 and kind.__new__ is constructor and constructor.__code__ is constructor_code
                 and constructor.__globals__.get('_tuple_new') is tuple.__new__
                 and all(vars(kind).get(name) is member
                         for name, member in zip(fields, members, strict=True)))
    for name, function, code in origin[2]:
        _require(type(name) is str and type(function) is FunctionType
                 and globals().get(name) is function and function.__code__ is code
                 and metadata._probe_function_namespace(origin[0], name, function))
    return origin


def _execution_tail(execution):
    _require(type(execution) is _ProbeExecution)
    owner, plan, reg = execution.owner, execution.plan, execution.registration
    _engine_origin_tail(execution.origin)
    _startup_plan_tail(plan, reg)
    _require(execution.origin is plan.engine_origin
             and vars(owner).get('_startup_probe_execution') is execution
             and vars(owner).get('_count_cell') is execution.count is plan.count
             and type(execution.next_site) is list and len(execution.next_site) == 1
             and type(execution.next_site[0]) is int
             and 0 <= execution.next_site[0] <= len(plan.definitions)
             and type(execution.pending) is list and len(execution.pending) == 1
             and type(execution.history) is list and len(execution.history) <= len(plan.definitions)
             and type(execution.opened) is list and len(execution.opened) < len(plan.components)
             and type(execution.outcome) is list and len(execution.outcome) == 1
             and type(execution.failed) is list and len(execution.failed) == 1
             and execution.failed[0] is False
             and type(execution.finished) is list and len(execution.finished) == 1
             and type(execution.finished[0]) is bool
             and type(execution.cursor) is list and len(execution.cursor) == 1)
    policy._cursor_tail(execution.cursor[0])
    _require(execution.cursor[0].policy is plan.policy
             and execution.next_site[0] == _cursor_ordinal(plan, execution.cursor[0])
             and (not execution.finished[0] or execution.cursor[0].action == 'finished'))
    _native_work_origin_tail(owner, reg, reg.native_origin)
    return execution


def _history_mirrors_tail(execution, predecessor, attached=None):
    _execution_tail(execution)
    history, reg = execution.history, execution.registration
    actual = predecessor
    for sequence in range(len(history) - 1, -1, -1):
        _require(type(actual) is _ProbeCommit and type(actual.sequence) is int
                 and actual.sequence == sequence
                 and history[sequence] is actual
                 and type(actual.consumer) is _ProbeConsumer
                 and actual.consumer.execution is execution
                 and actual.consumer.commit[0] is actual)
        operation = actual.consumer.operation
        _require(type(operation) is metadata._MetadataOperation)
        result = operation.result
        _require(type(result) is metadata._MetadataResult
                 and type(operation) is metadata._MetadataOperation
                 and operation.registration is reg and operation.owner is execution.owner
                 and type(operation.index) is int
                 and reg.native_ledger.attempts[operation.index] is operation
                 and type(actual.category) is str and actual.category in ('returned', 'reported_missing')
                 and type(operation.state) is list and len(operation.state) == 3
                 and all(type(value) is bool for value in operation.state)
                 and operation.state == ([True, True, False] if actual.category == 'returned'
                                         else [True, False, False])
                 and type(operation.ended) is list and len(operation.ended) == 1
                 and operation.ended[0] is True
                 and result.acknowledged[0] is actual
                 and result.consumer[0] is actual.consumer)
        if actual is attached:
            _require(sequence == len(history) - 1
                     and actual.consumer.custody[1].state == [False, False, False])
        else:
            _require(result.custody_link == [None]
                     and actual.consumer.custody[1].state == [True, True, False])
        actual = actual.consumer.predecessor
    _require(actual is None)
    _require((not history and execution.next_site[0] == 0) or
             (history and execution.next_site[0] == predecessor.next_site))
    return execution


def _history_tail(execution, predecessor):
    _history_mirrors_tail(execution, predecessor)
    for commit in execution.history:
        _require(type(commit) is _ProbeCommit and type(commit.consumer) is _ProbeConsumer)
        origin, marker = commit.consumer.custody[:2]
        metadata._origin_tail(origin)
        _require(type(marker) is origin.marker_type
                 and type(marker.reference) is origin.reference_type
                 and origin.reference_call(marker.reference) is None)
    return _history_mirrors_tail(execution, predecessor)


def _opened_chain_tail(execution, closed=False):
    _require(type(execution) is _ProbeExecution and type(closed) is bool)
    reg, plan = execution.registration, execution.plan
    records = reg.scope.records
    _require(type(records) is list and type(execution.opened) is list
             and len(records) == len(plan.base_records) + len(execution.opened)
             and all(records[i] is row for i, row in enumerate(plan.base_records)))
    parent = None
    for position, entry in enumerate(execution.opened):
        _require(type(entry) is tuple and len(entry) == 7
                 and type(entry[0]) is int and entry[0] == position
                 and entry[1] is plan.components[position]
                 and type(entry[3]) is _NativeOpenedDescriptor and type(entry[4]) is int
                 and records[len(plan.base_records) + position] is entry[3])
        descriptor = entry[3]
        close = _native_descriptor_opened(descriptor, reg.native_ledger)
        allocation = descriptor.allocation
        flags = reg.native_origin.flags
        _require(descriptor.fd is entry[4] and allocation.parent is parent
                 and entry[2] is (None if parent is None else parent.fd)
                 and allocation.owner is execution.owner and allocation.scope is reg.scope
                 and allocation.registration is reg
                 and allocation.arguments[0] is entry[1]
                 and allocation.arguments[1] == flags[0] | flags[1] | flags[2] | flags[3] | flags[4]
                 and allocation.arguments[2] is entry[2])
        if entry[5] is None:
            _require(position == 0 and entry[6] is None and execution.history == []
                     and execution.cursor[0].action == 'root_fstat')
        else:
            policy._directory(entry[5], plan.policy)
            _require(type(entry[6]) is _ProbeCommit and entry[6].identity is entry[5]
                     and entry[6].consumer.execution is execution
                     and execution.history[entry[6].sequence] is entry[6])
        if closed:
            _require(_descriptor_closed_in_scope(descriptor, reg.scope))
        else:
            _require(close.state == [False, False] and close.raw[0] is close.unset
                     and close.result[0] is None and allocation.refused == [False])
        parent = descriptor
    return execution


def _resource_tail(owner, resource):
    _require(type(resource) is _NativeStartupProbeMetadataResource and resource.owner is owner
             and type(resource.metadata) is _ProbeExecution)
    execution = _execution_tail(resource.metadata)
    plan, reg = execution.plan, execution.registration
    _require(resource.registration is reg and type(resource.ordinal) is int
             and resource.ordinal == execution.next_site[0]
             and 0 <= resource.ordinal < len(plan.definitions)
             and resource.site is plan.definitions[resource.ordinal]
             and resource.variant is plan.variants[resource.ordinal])
    _opened_chain_tail(execution)
    action = policy._action(execution.cursor[0])
    _require(type(action) is tuple and action[0] in ('stat', 'fstat'))
    if action[0] == 'fstat':
        descriptor = execution.opened[action[1]][3]
        _require(resource.descriptor is descriptor and type(resource.arguments) is tuple
                 and len(resource.arguments) == 1 and resource.arguments[0] is descriptor.fd)
    else:
        descriptor = None if action[2] is None else execution.opened[action[2]][3]
        _require(resource.descriptor is descriptor and type(resource.arguments) is tuple
                 and len(resource.arguments) == 2 and resource.arguments[0] is action[1]
                 and resource.arguments[1] is (None if descriptor is None else descriptor.fd))
    return resource


def _resource(execution, predecessor):
    _history_tail(execution, predecessor)
    _require(execution.pending[0] is None)
    plan, index = execution.plan, execution.next_site[0]
    action = policy._action(execution.cursor[0])
    _require(action is not None and action[0] in ('stat', 'fstat')
             and index < len(plan.definitions))
    descriptor = (execution.opened[action[1]][3] if action[0] == 'fstat' else
                  None if action[2] is None else execution.opened[action[2]][3])
    arguments = ((descriptor.fd,) if action[0] == 'fstat' else
                 (action[1], None if descriptor is None else descriptor.fd))
    values = (execution.owner, execution.registration, execution, plan.variants[index],
              plan.definitions[index], index, descriptor, arguments)
    kind, _, _, constructor, _, _, _ = plan.blueprint[8][6]
    resource = constructor(kind, *values)
    _blueprint_tail(plan.blueprint)
    _require(type(resource) is _NativeStartupProbeMetadataResource
             and all(tuple.__getitem__(resource, i) is value for i, value in enumerate(values)))
    return _resource_tail(execution.owner, resource)


def _consumer_tail(consumer, predecessor):
    _require(type(consumer) is _ProbeConsumer
             and type(consumer.operation) is metadata._MetadataOperation)
    execution, operation = consumer.execution, consumer.operation
    _history_tail(execution, predecessor)
    _resource_tail(execution.owner, operation.resource)
    _require(type(operation) is metadata._MetadataOperation
             and operation.owner is execution.owner
             and operation.registration is execution.registration
             and consumer.predecessor is predecessor
             and operation.result.consumer[0] is consumer
             and execution.pending[0] is consumer
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and (consumer.commit[0] is None or
                  (type(consumer.commit[0]) is _ProbeCommit
                   and consumer.commit[0].consumer is consumer)))
    return operation



def _policy_values(execution, actual, predecessor):
    _require(type(actual) in (_ProbeReturn, metadata._ReportedMissingMetadataReturn)
             and type(actual.consumer) is _ProbeConsumer)
    operation = _consumer_tail(actual.consumer, predecessor)
    result, phase = operation.result, operation.phase
    _require(actual.consumer.execution is execution and phase.current[0] is phase.pending
             and phase.result[0] is operation and operation.ledger.inflight[0] is None
             and result.envelope[0] is actual and result.category[0] == actual.category
             and result.snapshot[0] is actual.snapshot and result.raw[0] is actual.raw
             and operation.ended == [True]
             and actual.category in ('returned', 'reported_missing')
             and operation.state == ([True, False, False] if actual.category == 'reported_missing'
                                       else [True, True, False]))
    identity = (None if actual.category == 'reported_missing' else
                metadata._directory_identity(actual.snapshot, execution.plan.blueprint[2][1]))
    return operation.resource.ordinal, actual.category, identity, execution.cursor[0]


def _run_observation(execution, predecessor):
    resource = _resource(execution, predecessor)
    failed = False
    try:
        return metadata._run_directory_observation(execution.owner, resource, predecessor)
    except BaseException:
        failed = True
    if failed:
        if type(execution.failed) is list and execution.failed == [False]:
            execution.failed[0] = True
        raise metadata.ArtifactObservationError(execution.owner) from None


def _open_ancestor(execution, commit, held):
    _require(type(execution) is _ProbeExecution and type(held) is list)
    _history_tail(execution, commit)
    cursor = execution.cursor[0]
    action = policy._action(cursor)
    _require(action[0] == 'open' and cursor.action in ('root_open', 'component_open'))
    position = cursor.component
    _require(len(execution.opened) == position)
    parent = None if action[2] is None else execution.opened[action[2]][4]
    name = execution.plan.components[position]
    _require(action[1] == name)
    row, fd = StartupArtifactOwner._open(execution.owner, name, parent, True,
                                        execution.registration)
    held.append((row, fd))  # literal actual open retained before callbacks/validation
    entry = (position, name, parent, row, fd, cursor.expected, commit)
    execution.opened.append(entry)
    _engine_origin_tail(execution.origin)
    _require(type(row) is _NativeOpenedDescriptor and row.fd is fd
             and execution.registration.scope.records[len(execution.plan.base_records)+position] is row
             and execution.cursor[0] is cursor)
    following = policy._advance(cursor, 'opened')
    _engine_origin_tail(execution.origin)
    _policy_pins_tail(execution.plan.blueprint)
    policy._validate_advance(cursor, 'opened', None, following)
    _require(execution.cursor[0] is cursor and execution.opened[position] is entry)
    execution.cursor[0] = following
    execution.next_site[0] = _cursor_ordinal(execution.plan, following)
    return commit


def _finish(execution, predecessor, held):
    _require(type(execution) is _ProbeExecution
             and type(execution.finished) is list and len(execution.finished) == 1
             and execution.finished[0] is False
             and type(held) is list)
    resources = tuple(held)
    outcome = _finished_state_tail(execution, predecessor, resources)
    ledger = execution.registration.native_ledger
    closure = (ledger.counts, ledger.counts[0], ledger.counts[1], ledger.attempts,
               len(ledger.attempts), execution.count)
    values = (execution, predecessor, resources, outcome, closure)
    kind, fields, members, constructor, code = execution.origin[1][5]
    result = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(result) is _ProbeFinish and tuple.__len__(result) == 5
             and all(tuple.__getitem__(result, i) is value for i, value in enumerate(values))
             and type(execution.finished) is list and len(execution.finished) == 1
             and execution.finished[0] is False
             and _finished_state_tail(execution, predecessor, resources) is outcome
             and ledger.counts[0] == closure[1] and ledger.counts[1] == closure[2]
             and len(ledger.attempts) == closure[4])
    execution.finished[0] = True
    return result


def _finished_state_tail(execution, predecessor, held):
    _history_tail(execution, predecessor)
    _opened_chain_tail(execution, closed=True)
    reg, budget = execution.registration, execution.budget
    _require(type(held) is tuple and len(held) == len(execution.opened)
             and all(row is execution.opened[i][3] and fd is execution.opened[i][4]
                     for i, (row, fd) in enumerate(held))
             and execution.cursor[0].action == 'finished'
             and execution.next_site[0] == len(execution.plan.definitions)
             and execution.pending[0] is None and type(execution.outcome[0]) is tuple
             and len(execution.outcome[0]) == 3
             and reg.native_ledger.inflight == [None]
             and reg.native_ledger.failed == [False]
             and reg.native_phase.current[0] is reg.native_phase.idle
             and reg.native_phase.result == [None]
             and reg.native_ledger.counts is budget[0]
             and reg.native_ledger.counts[0] == budget[1]+len(execution.history)+2*len(held)
             and reg.native_ledger.counts[1] == budget[2]
             and reg.native_ledger.attempts is budget[3]
             and len(reg.native_ledger.attempts) == budget[4]+len(execution.history)+len(held))
    outcomes = tuple(commit.outcome for commit in execution.history if commit.outcome is not None)
    _require(len(outcomes) == 1 and execution.outcome[0] is outcomes[0]
             and policy._outcome(execution.cursor[0]) == outcomes[0])
    return outcomes[0]


def _run_startup_probe(owner, scope, registration, plan):
    _require(type(owner) is StartupArtifactOwner and type(plan) is _StartupPlan
             and type(registration) is _NativeScopeRegistration
             and registration.scope is scope and registration.owner is owner
             and plan.owner is owner and vars(owner).get('_startup_probe_execution') is None)
    _startup_plan_tail(plan, registration)
    origin = _engine_origin_tail(plan.engine_origin)
    _native_work_origin_tail(owner, registration, registration.native_origin)
    actor_arguments = (scope, registration, plan, origin)
    actor_state = _native_pre_actor_state(owner, actor_arguments)
    native = registration.native_origin
    _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                          registration.context)
    _native_post_actor_state(owner, actor_state, actor_arguments)
    _startup_plan_tail(plan, registration)
    _require(registration.scope is scope and vars(owner).get('_startup_probe_execution') is None)
    ledger = registration.native_ledger
    budget = (ledger.counts, ledger.counts[0], ledger.counts[1], ledger.attempts, len(ledger.attempts))
    cursor = policy._start(plan.policy)
    _policy_pins_tail(plan.blueprint)
    values = (owner, plan, registration, origin, plan.count, [0], [None], [], [],
              [None], [False], [False], budget, [cursor])
    kind, fields, members, constructor, code = origin[1][0]
    execution = constructor(kind, *values)
    _engine_origin_tail(origin)
    _startup_plan_tail(plan, registration)
    _require(vars(owner).get('_startup_probe_execution') is None
             and type(execution) is _ProbeExecution
             and all(tuple.__getitem__(execution, i) is value for i, value in enumerate(values)))
    owner._startup_probe_execution = execution
    held, predecessor, complete = [], None, False
    try:
        _open_ancestor(execution, None, held)  # root open precedes root fstat
        while execution.cursor[0].action != 'finished':
            _require(len(execution.history) < len(plan.definitions))
            if execution.cursor[0].action == 'component_open':
                _open_ancestor(execution, predecessor, held)
            else:
                predecessor = _run_observation(execution, predecessor)
        complete = True
    except BaseException:
        pass
    finally:
        for row, fd in reversed(held):
            try:
                StartupArtifactOwner._close(owner, row, fd, scope, registration.root)
            except BaseException:
                try:
                    _descriptor_refused(row)
                except BaseException:
                    pass  # no false close credit; continue independent reservations
                owner._unknown = True
                complete = False
    if not complete:
        execution.failed[0] = True
        raise metadata.ArtifactObservationError(owner) from None
    return _finish(execution, predecessor, held)


def _lifecycle_tail(owner, scope, registration, plan):
    _require(type(owner) is StartupArtifactOwner and plan.owner is owner
             and registration.scope is scope and registration.owner is owner
             and vars(owner).get('_origin') is scope and vars(owner).get('_scope') is scope
             and vars(owner).get('_root_cell') is registration.root
             and vars(owner).get('_cell') is registration.cell
             and vars(owner).get('_ready') is False and vars(owner).get('_failed') is False
             and vars(owner).get('_unknown') is False and vars(owner).get('_reading') is False
             and vars(owner).get('_count_cell') is plan.count
             and type(plan.count) is tuple and len(plan.count) == 3
             and plan.count[0] is owner and plan.count[1] is scope
             and type(plan.count[2]) is int and vars(owner).get('_bytes_read') == plan.count[2]
             and type(owner._attempt_cell) is tuple
             and scope.activation._artifact_attempt_cell is owner._attempt_cell
             and scope.activation._artifact_owner is owner
             and scope.activation._artifact_cell is registration.root)
    dictionaries, exports = plan.parents
    for object_, dictionary, entries in dictionaries:
        _require(vars(object_) is dictionary and len(dictionary) == len(entries)
                 and all(type(key) is str for key in dictionary)
                 and all(key in dictionary and dictionary[key] is value for key, value in entries))
    for module, name, value in exports:
        _require(type(module) is ModuleType and vars(module).get(name) is value)
    inputs = plan.source.inputs
    _require(vars(plan.source.entry).get('_inputs') is inputs
             and vars(plan.source.entry).get('_root_cell') is plan.source.cell
             and vars(plan.source.entry).get('_failed') is False
             and vars(plan.source.entry).get('_unknown') is False
             and vars(plan.source.entry).get('_completing') is True
             and type(inputs.io_slot) is list and len(inputs.io_slot) == 1 and inputs.io_slot[0] is owner
             and type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1
             and inputs.cache_context_slot[0] is plan.source.context_fact
             and inputs.runtime_plan is plan.source.plan
             and plan.source.plan.pending is scope.expected)
    _require(scope.cache is plan.source and type(plan.source.effects) is list
             and len(plan.source.effects) == len(plan.effect_prefix)
             and all(current is original for current, original
                     in zip(plan.source.effects, plan.effect_prefix, strict=True))
             and plan.source.effects[-1] is plan.effect
             and vars(plan.effect) is plan.effect_dict
             and plan.effect.source is plan.source and plan.effect.phase == plan.phase
             and plan.effect.index == plan.index and plan.effect.count is plan.count
             and plan.effect.attempted is True and plan.effect.returned is False
             and plan.effect.unknown is False and plan.effect.result is None
             and plan.effect.descriptors is None)
    return scope


def _prepare_shared_consumer(owner, operation, predecessor, baseline, eof, custody):
    _require(type(operation) is metadata._MetadataOperation
             and type(operation.resource) is _NativeStartupProbeMetadataResource
             and baseline is None and eof is None)
    execution = operation.resource.metadata
    _history_tail(execution, predecessor)
    _require(execution.pending[0] is None and operation.result.consumer == [None])
    values = (execution, operation, predecessor, [None], custody)
    kind, fields, members, constructor, code = execution.origin[1][1]
    consumer = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(consumer) is _ProbeConsumer
             and all(tuple.__getitem__(consumer, i) is value for i, value in enumerate(values))
             and execution.pending[0] is None and operation.result.consumer == [None])
    operation.result.consumer[0] = consumer
    return consumer


def _latch_shared_consumer(owner, consumer, rejoin=False):
    _require(type(consumer) is _ProbeConsumer and type(consumer.operation) is metadata._MetadataOperation)
    execution = consumer.execution
    _require(execution.owner is owner)
    if not rejoin:
        _history_tail(execution, consumer.predecessor)
        _require(execution.pending[0] is None and consumer.operation.result.consumer[0] is consumer)
        execution.pending[0] = consumer
    _consumer_tail(consumer, consumer.predecessor)
    return consumer


# The native metadata producer/consumer/ACK dispatch is shared with the fixed
# startup cohort; policy-specific history and branch validation remain here.
_produce_shared = metadata._produce_probe_shared
_consume_shared = metadata._consume_probe_shared
_ack_shared = metadata._ack_probe_shared


def _retired_shared(owner, consumer, commit, origin, marker, record):
    _require(type(consumer) is _ProbeConsumer and consumer.execution.owner is owner
             and type(commit) is _ProbeCommit and commit.consumer is consumer
             and record.marker is marker and record.detached is True
             and record.unmatched_link is False and record.unmatched_marker is False)
    _history_tail(consumer.execution, commit)
    _require(consumer.operation.result.acknowledged[0] is commit
             and consumer.execution.pending[0] is None
             and consumer.operation.phase.current[0] is consumer.operation.phase.idle
             and consumer.operation.phase.result == [None])
    return commit


def _attached_shared(owner, consumer, commit):
    """Literal original ACK while capsule is attached; never a file/EOF claim."""
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer)
    execution, operation = consumer.execution, consumer.operation
    _history_mirrors_tail(execution, commit, attached=commit)
    origin, marker, link, slot, state, reference = consumer.custody
    _require(operation.result.custody_origin is origin
             and operation.result.custody_link is link and operation.result.custody_slot is slot
             and slot[0] is marker and marker.state is state and marker.reference is reference)
    cells = _directory_payload_cells(owner, origin, marker, link[0])
    _require(cells.raw[0] is operation.result.unset
             and cells.snapshot[0] is cells.envelope[0] is cells.category[0] is None
             and cells.consumption[0] is commit
             and operation.result.acknowledged[0] is commit
             and execution.pending[0] is None
             and operation.phase.current[0] is operation.phase.idle
             and operation.phase.result == [None] and operation.ledger.inflight == [None]
             and operation.ledger.failed == [False]
             and operation.ledger.counts[0] is operation.budget[3]
             and operation.ledger.counts[1] is operation.budget[2])
    _history_mirrors_tail(execution, commit, attached=commit)
    return commit


def _make_shared_commit(owner, consumer, actual):
    _require(type(consumer) is _ProbeConsumer and consumer.execution.owner is owner)
    execution = consumer.execution
    site, category, identity, before = _policy_values(execution, actual, consumer.predecessor)
    following = policy._advance(before, category, identity)
    _policy_pins_tail(execution.plan.blueprint)
    policy._validate_advance(before, category, identity, following)
    next_site = _cursor_ordinal(execution.plan, following)
    outcome = policy._outcome(following) if following.action == 'finished' else None
    values = (consumer, len(execution.history), site, next_site, category, identity, outcome, following)
    kind, fields, members, constructor, code = execution.origin[1][3]
    commit = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(commit) is _ProbeCommit and tuple.__len__(commit) == len(values)
             and all(tuple.__getitem__(commit, i) is value for i, value in enumerate(values)))
    return commit


def _commit_shared_tail(owner, consumer, actual, commit):
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    execution = consumer.execution
    site, category, identity, before = _policy_values(execution, actual, consumer.predecessor)
    _policy_pins_tail(execution.plan.blueprint)
    policy._validate_advance(before, category, identity, commit.cursor)
    _require(type(commit.sequence) is int and type(commit.site) is int
             and type(commit.next_site) is int and type(commit.category) is str
             and commit.category in ('returned', 'reported_missing')
             and (commit.identity is None or type(commit.identity) is tuple
                  and len(commit.identity) == 5 and all(type(value) is int for value in commit.identity)))
    _require(type(commit.sequence) is int and commit.sequence == len(execution.history)
             and type(commit.site) is int and commit.site == site
             and type(commit.next_site) is int
             and commit.next_site == _cursor_ordinal(execution.plan, commit.cursor)
             and commit.category == category and commit.identity == identity
             and consumer.consumption[0] is actual and consumer.commit[0] is commit)
    _require((commit.outcome is None if commit.cursor.action != 'finished' else
              type(commit.outcome) is tuple and policy._outcome(commit.cursor) == commit.outcome))
    return commit


def _publish_shared_ack(owner, consumer, commit):
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer)
    execution = consumer.execution
    _lifecycle_tail(owner, execution.registration.scope, execution.registration, execution.plan)
    _require(commit.sequence == len(execution.history) and execution.pending[0] is consumer
             and consumer.commit[0] is consumer.operation.result.acknowledged[0] is commit
             and commit.cursor.predecessor is execution.cursor[0])
    if execution.cursor[0].action == 'root_fstat':
        entry = execution.opened[0]
        _require(entry[5] is None and entry[6] is None)
        execution.opened[0] = (*entry[:5], commit.identity, commit)
    execution.history.append(commit)
    execution.cursor[0] = commit.cursor
    execution.next_site[0] = commit.next_site
    if commit.outcome is not None:
        _require(execution.outcome[0] is None)
        execution.outcome[0] = commit.outcome
    execution.pending[0] = None


def _acked_shared_history(owner, consumer, commit):
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer
             and type(consumer.operation) is metadata._MetadataOperation)
    execution, operation = consumer.execution, consumer.operation
    origin, marker, link, slot, state, reference = consumer.custody
    metadata._origin_tail(origin)
    _require(type(marker) is origin.marker_type and marker.operation is operation
             and marker.owner is owner and marker.origin is origin
             and marker.owner_link is link and marker.marker_slot is slot
             and marker.state is state and marker.reference is reference
             and type(state) is list and len(state) == 3
             and all(type(value) is bool for value in state))
    # This is a mirror validator, not a retirement receipt or native allowance.
    # The attached/retired caller tails separately require their literal phase.
    attached = commit if state == [False, False, False] else None
    _history_mirrors_tail(execution, commit, attached=attached)
    ledger, phase = operation.ledger, operation.phase
    _require(execution.pending[0] is None
             and type(operation.index) is int
             and operation.index == len(ledger.attempts) - 1
             and ledger.attempts[operation.index] is operation
             and ledger.counts is operation.budget[0]
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and ledger.failed == [False] and ledger.failure == [None]
             and ledger.inflight == [None] and phase.current[0] is phase.idle
             and phase.result == [None])
    return commit
class _StartupSite(NamedTuple):
    owner: object
    source: object
    phase: int
    index: int
    site: tuple
    ordinal: int


class _StartupPlan(NamedTuple):
    owner: object
    source: object
    phase: int
    index: int
    policy: object
    components: tuple
    definitions: tuple
    variants: tuple
    keys: tuple
    engine_origin: tuple
    blueprint: tuple
    count: tuple
    root: tuple
    cell: tuple
    base_records: tuple
    effect: object
    effect_dict: dict
    effect_prefix: tuple
    previous: object
    parents: tuple


def _path_rows(selected, context):
    # Original components were retained before Scope. Allocate only this active
    # path's bounded possible sites, not O(paths * components squared) at retain.
    policy._policy_tail(selected)
    _require(selected.actor_uid == context[1])
    keys = [('root_fstat', 0, 0)]
    for component in range(1, len(selected.components)):
        keys.append(('component_stat', component, 0))
        if component < len(selected.components)-1:
            keys.append(('component_fstat', component, 0))
        for ancestor in range(component):
            keys.extend((('pre_fstat', component, ancestor), ('pre_stat', component, ancestor)))
        keys.append(('confirmation', component, 0))
        for ancestor in range(component):
            keys.extend((('post_fstat', component, ancestor), ('post_stat', component, ancestor)))
    keys = tuple(keys)
    definitions = tuple((4 if kind.endswith('fstat') else 3, kind,
                         ancestor if kind.startswith(('pre_', 'post_')) else component)
                        for kind, component, ancestor in keys)
    return selected, keys, definitions


def _policy_pins_tail(blueprint):
    _require(type(blueprint) is tuple and len(blueprint) == 10)
    _require(type(blueprint[6]) is tuple and len(blueprint[6]) == 4
             and type(blueprint[8]) is tuple and type(blueprint[9]) is tuple)
    module, functions, kinds, actions = blueprint[6]
    _require(type(functions) is tuple and type(kinds) is tuple
             and all(type(row) is tuple and len(row) == 3 for row in functions)
             and all(type(row) is tuple and len(row) == 7 for row in (*kinds, *blueprint[8]))
             and all(type(row) is tuple and len(row) == 4 for row in blueprint[9]))
    _require(type(module) is ModuleType and module is policy
             and sys.modules.get('hmp_plugin.presentation_startup_probe_policy') is module
             and vars(module).get('_ACTIONS') is actions)
    for name, function, code in functions:
        _require(type(name) is str and type(function) is FunctionType
                 and vars(module).get(name) is function and function.__code__ is code
                 and function.__globals__ is vars(module))
    _require(vars(policy).get('_StartupPathPolicy') is kinds[0][0]
             and vars(policy).get('_StartupCursor') is kinds[1][0]
             and globals().get('_StartupPlan') is blueprint[8][0][0]
             and globals().get('_StartupSite') is blueprint[8][1][0]
             and globals().get('_NativeStartupProbeMetadataResource') is blueprint[8][6][0]
             and globals().get('_Scope') is blueprint[8][7][0])
    cache_module = blueprint[9][0][0]
    _require(type(cache_module) is ModuleType
             and sys.modules.get('hmp_plugin.presentation_startup_cache') is cache_module
             and all(vars(cache_module).get(name) is blueprint[8][index][0]
                     for index, name in ((2, '_ProbeEffect'), (3, '_CachePass'),
                                         (4, '_Missing'), (5, '_CacheSource'))))
    for kind, fields, members, constructor, code, bases, dispatch in (*kinds, *blueprint[8]):
        _require(type(kind) is type and kind.__bases__ is bases
                 and type(constructor) is FunctionType and constructor.__code__ is code
                 and all(vars(kind).get(name) is value for name, value in dispatch))
        if fields is not None:
            _require(vars(kind).get('_fields') is fields and kind.__new__ is constructor
                     and constructor.__globals__.get('_tuple_new') is tuple.__new__
                     and all(vars(kind).get(name) is member
                             for name, member in zip(fields, members, strict=True)))
        else:
            _require(vars(kind).get('__init__') is constructor)
    for module, name, function, code in blueprint[9]:
        _require(type(module) is ModuleType and type(name) is str
                 and type(function) is FunctionType
                 and vars(module).get(name) is function and function.__code__ is code
                 and function.__globals__ is vars(module))
    return blueprint


def _blueprint_tail(blueprint, verify_paths=False):
    _policy_pins_tail(blueprint)
    from .presentation_startup_cache import _CacheSource
    owner, source, context, expected, paths, rows = blueprint[:6]
    _require(type(owner) is StartupArtifactOwner and type(source) is _CacheSource
             and type(context) is tuple and len(context) == 3
             and all(type(value) is int for value in context)
             and source.plan.pending is expected and source.paths is paths
             and type(paths) is tuple and type(rows) is tuple and len(rows) == len(paths)
             and type(blueprint[7]) is tuple)
    if verify_paths:
        for path, selected in zip(paths, rows, strict=True):
            _require(type(path) is str and type(selected) is policy._StartupPathPolicy
                     and selected.path is path and selected.actor_uid == context[1])
            policy._policy_tail(selected)
    _engine_origin_tail(blueprint[7])
    return blueprint


def _new_startup_probe_origin(owner, source, context, expected):
    """Capture original path/code/type inputs before the outer Scope callback."""
    from . import presentation_startup_cache as cache
    _require(type(owner) is StartupArtifactOwner and type(source) is cache._CacheSource
             and vars(owner).get('_scope') is None and vars(owner).get('_origin') is None
             and vars(owner).get('_startup_probe_execution') is None
             and type(context) is tuple and len(context) == 3
             and all(type(value) is int for value in context)
             and source.plan.pending is expected and type(source.paths) is tuple)
    names = vars(owner)
    entries = tuple(names.items())
    paths = source.paths
    module = sys.modules.get(__name__)
    _require(type(module) is ModuleType and vars(module) is globals())
    def pin(kind):
        fields = vars(kind).get('_fields')
        constructor = kind.__new__ if fields is not None else vars(kind)['__init__']
        return (kind, fields,
                () if fields is None else tuple(vars(kind).get(name) for name in fields),
                constructor, constructor.__code__, kind.__bases__,
                tuple((name, vars(kind).get(name)) for name in
                      ('__getattribute__', '__getattr__', '__getitem__', '__len__',
                       '__iter__', '__setattr__', '__delattr__')))
    policy_pins = (policy, tuple((name, vars(policy)[name], vars(policy)[name].__code__)
                                  for name in ('_need', '_new_policy', '_policy_tail', '_directory',
                                               '_cursor_tail', '_start', '_action', '_transition',
                                               '_validate_advance', '_advance', '_outcome')),
                   tuple(pin(kind) for kind in (policy._StartupPathPolicy, policy._StartupCursor)),
                   vars(policy)['_ACTIONS'])
    kinds = tuple(pin(kind) for kind in (_StartupPlan, _StartupSite, cache._ProbeEffect,
                                         cache._CachePass, cache._Missing, cache._CacheSource,
                                         _NativeStartupProbeMetadataResource, _Scope))
    cache_pins = tuple((cache, name, vars(cache)[name], vars(cache)[name].__code__)
                       for name in ('source_current', 'owned_current', '_missing_shape',
                                    '_probe', '_legacy_probe', 'observe_pass', '_cache_seal_mirrors', 'seal'))
    engine_origin = _new_probe_engine_origin()
    rows = tuple(policy._new_policy(path, context[1]) for path in paths)
    blueprint = (owner, source, context, expected, paths, rows, policy_pins,
                 engine_origin, kinds, cache_pins)
    _blueprint_tail(blueprint, verify_paths=True)
    _require(vars(owner) is names and len(names) == len(entries)
             and all(type(key) is str for key in names)
             and all(key in names and names[key] is value for key, value in entries))
    cache.source_current(source)
    _blueprint_tail(blueprint, verify_paths=True)
    _require(vars(owner) is names and len(names) == len(entries)
             and all(key in names and names[key] is value for key, value in entries))
    return (_NativeStartupProbeMetadataResource, StartupArtifactOwner, module,
            _resource_tail, _resource_tail.__code__, engine_origin, blueprint)


def _cursor_ordinal(plan, cursor):
    policy._cursor_tail(cursor)
    _require(cursor.policy is plan.policy)
    kind = cursor.action
    if kind == 'finished':
        return len(plan.definitions)
    if kind in ('root_open', 'component_open'):
        kind = 'root_fstat' if kind == 'root_open' else 'component_fstat'
    key = (kind, cursor.component, cursor.ancestor)
    found = tuple(index for index, original in enumerate(plan.keys) if original == key)
    _require(len(found) == 1)
    return found[0]


def _new_startup_plan(source, owner, phase, index, effect, previous, registration):
    _native_work_registration_tail(owner, registration)
    scope = registration.scope
    origin = scope.native_startup_probe_origin
    _require(type(origin) is tuple and len(origin) == 7
             and origin[0] is _NativeStartupProbeMetadataResource
             and origin[1] is StartupArtifactOwner and origin[2] is sys.modules.get(__name__)
             and origin[3] is _resource_tail and origin[4] is _resource_tail.__code__)
    _engine_origin_tail(origin[5])
    blueprint = _blueprint_tail(origin[6])
    _require(blueprint[0] is owner and blueprint[1] is source
             and type(phase) is int and phase in (0, 1) and type(index) is int
             and 0 <= index < len(blueprint[4])
             and vars(owner).get('_startup_probe_execution') is None)
    from .presentation_startup_cache import owned_current
    owned_current(source, owner)  # full parent validation once at this path boundary
    parents = _startup_parent_witness(source, scope)
    original_policy = blueprint[5][index]
    selected, keys, definitions = _path_rows(original_policy, blueprint[2])
    _blueprint_tail(blueprint)
    _require(selected is original_policy and type(keys) is tuple and type(definitions) is tuple
             and len(keys) == len(definitions) <= 8321)
    site_kind, _, _, site_constructor, _, _, _ = blueprint[8][1]
    variants = tuple(site_constructor(site_kind, owner, source, phase, index, site, ordinal)
                     for ordinal, site in enumerate(definitions))
    values = (owner, source, phase, index, selected, selected.components, definitions,
              variants, keys, origin[5], blueprint, owner._count_cell, owner._root_cell,
              owner._cell, tuple(scope.records), effect, vars(effect), tuple(source.effects), previous, parents)
    plan_kind, _, _, plan_constructor, _, _, _ = blueprint[8][0]
    plan = plan_constructor(plan_kind, *values)
    _blueprint_tail(blueprint)
    _require(type(plan) is _StartupPlan and tuple.__len__(plan) == len(values)
             and all(tuple.__getitem__(plan, i) is value for i, value in enumerate(values)))
    for ordinal, variant in enumerate(variants):
        _require(type(variant) is _StartupSite and variant.owner is owner
                 and variant.source is source and type(variant.phase) is int and variant.phase == phase
                 and type(variant.index) is int and variant.index == index
                 and variant.site is definitions[ordinal] and type(variant.ordinal) is int
                 and variant.ordinal == ordinal)
    _startup_plan_tail(plan, registration)
    return plan


def _startup_plan_tail(plan, registration):
    _require(type(plan) is _StartupPlan and type(registration) is _NativeScopeRegistration
             and registration.owner is plan.owner)
    _engine_origin_tail(plan.engine_origin)
    _blueprint_tail(plan.blueprint)
    scope = registration.scope
    _native_work_registration_tail(plan.owner, registration)
    _require(type(scope.native_startup_probe_origin) is tuple
             and scope.native_startup_probe_origin[6] is plan.blueprint
             and scope.native_startup_probe_origin[5] is plan.engine_origin
             and scope.cache is plan.source and scope.context is plan.blueprint[2]
             and scope.expected is plan.blueprint[3]
             and registration.root is plan.root and registration.cell is plan.cell
             and plan.policy is plan.blueprint[5][plan.index]
             and type(plan.keys) is tuple and type(plan.definitions) is tuple
             and len(plan.keys) == len(plan.definitions) == len(plan.variants) <= 8321
             and plan.components is plan.policy.components
             and len(plan.source.effects) == plan.phase*len(plan.source.paths)+plan.index+1)
    if plan.phase == 0:
        _require(plan.previous is None and plan.source.before == [None]
                 and plan.source.after == [None])
    else:
        from .presentation_startup_cache import _CachePass
        _require(type(plan.previous) is _CachePass and plan.source.before[0] is plan.previous
                 and plan.source.after == [None])
    return _lifecycle_tail(plan.owner, scope, registration, plan)


def _historical_finish_tail(actual):
    """Validate a caller-held old finish; never authorize another operation."""
    _require(type(actual) is _ProbeFinish and type(actual.execution) is _ProbeExecution)
    execution = actual.execution
    _engine_origin_tail(execution.origin)
    mirrors, mirrors_code = _historical_finish_mirrors, _historical_finish_mirrors.__code__
    plan, reg = execution.plan, execution.registration
    _require(type(plan) is _StartupPlan and type(reg) is _NativeScopeRegistration)
    scope = reg.scope
    _blueprint_tail(plan.blueprint)
    _require(execution.owner is plan.owner is plan.blueprint[0] and reg.owner is plan.owner)
    _native_work_registration_tail(execution.owner, reg)
    cohort = _historical_cohort(actual, scope)
    mirrors(actual, scope, cohort)
    _require(reg.scope.native_startup_probe_origin[6] is plan.blueprint
             and type(execution.finished) is list and len(execution.finished) == 1
             and execution.finished[0] is True
             and type(execution.failed) is list and len(execution.failed) == 1
             and execution.failed[0] is False
             and execution.pending == [None]
             and type(actual.predecessor) is _ProbeCommit
             and type(actual.predecessor.sequence) is int
             and type(execution.history) is list
             and len(execution.history) == actual.predecessor.sequence+1
             and execution.cursor[0] is actual.predecessor.cursor
             and execution.cursor[0].action == 'finished'
             and execution.outcome[0] is actual.outcome is actual.predecessor.outcome
             and policy._outcome(execution.cursor[0]) == actual.outcome
             and type(actual.resources) is tuple and len(actual.resources) == len(execution.opened)
             and type(actual.closure) is tuple and len(actual.closure) == 6)
    closure, budget, ledger = actual.closure, execution.budget, reg.native_ledger
    _require(closure[0] is ledger.counts and closure[3] is ledger.attempts
             and all(type(value) is int for value in closure[1:3])
             and type(closure[4]) is int and closure[5] is execution.count
             and closure[1] == budget[1]+len(execution.history)+2*len(actual.resources)
             and closure[2] == budget[2]
             and closure[4] == budget[4]+len(execution.history)+len(actual.resources)
             and ledger.counts[0] >= closure[1] and len(ledger.attempts) >= closure[4])
    predecessor = actual.predecessor
    for sequence in range(len(execution.history)-1, -1, -1):
        _require(type(predecessor) is _ProbeCommit and type(predecessor.sequence) is int
                 and predecessor.sequence == sequence
                 and execution.history[sequence] is predecessor
                 and type(predecessor.consumer) is _ProbeConsumer
                 and predecessor.consumer.execution is execution)
        operation = predecessor.consumer.operation
        _require(type(operation) is metadata._MetadataOperation
                 and type(operation.index) is int and 0 <= operation.index < closure[4]
                 and type(operation.result) is metadata._MetadataResult
                 and operation.registration is reg and ledger.attempts[operation.index] is operation
                 and operation.ended == [True]
                 and operation.result.acknowledged[0] is predecessor
                 and operation.result.consumer[0] is predecessor.consumer
                 and operation.result.custody_link == [None])
        origin, marker = predecessor.consumer.custody[:2]
        metadata._origin_tail(origin)
        _require(type(marker) is origin.marker_type and marker.state == [True, True, False]
                 and origin.reference_call(marker.reference) is None)
        predecessor = predecessor.consumer.predecessor
    _require(predecessor is None)
    for index, (row, fd) in enumerate(actual.resources):
        entry = execution.opened[index]
        _require(type(entry) is tuple and len(entry) == 7 and row is entry[3] and fd is entry[4]
                 and reg.scope.records[len(plan.base_records)+index] is row
                 and _descriptor_closed_in_scope(row, reg.scope))
    if (globals().get('_historical_finish_mirrors') is not mirrors
            or mirrors.__code__ is not mirrors_code):
        raise metadata.ArtifactObservationError from None
    return mirrors(actual, scope, cohort)

def _historical_finish_mirrors(actual, scope, cohort):
    """Full pure reseal after all weak-reference observations; no new admission."""
    _require(type(actual) is _ProbeFinish and type(actual.execution) is _ProbeExecution)
    execution = actual.execution
    _engine_origin_tail(execution.origin)
    plan, reg = execution.plan, execution.registration
    _require(type(plan) is _StartupPlan and type(reg) is _NativeScopeRegistration
             and type(scope) is _Scope
             and type(reg.type_pins) is tuple and len(reg.type_pins) == 3
             and all(type(kind) is type for kind in reg.type_pins)
             and reg.scope is scope and reg.owner is execution.owner is plan.owner
             and type(plan.owner) is StartupArtifactOwner)
    _policy_pins_tail(plan.blueprint)
    _require(type(cohort) is tuple and len(cohort) == 5)
    dictionaries, cells, attempts, attempt_count, activation_cell = cohort
    _require(type(dictionaries) is tuple and type(cells) is tuple)
    for object_, dictionary, entries in dictionaries:
        _require(vars(object_) is dictionary and type(dictionary) is dict
                 and len(dictionary) == len(entries)
                 and all(type(key) is str for key in dictionary)
                 and all(key in dictionary and dictionary[key] is value for key, value in entries))
    for cell, entries in cells:
        _require(type(cell) is list and len(cell) == len(entries)
                 and all(value is original for value, original in zip(cell, entries, strict=True)))
    active = scope.activation
    _require(type(active) is activation_module.GatewayActivationOwner
             and sys.modules.get('hmp_plugin.presentation_gateway_activation') is activation_module
             and vars(activation_module).get('_ENTRY_OWNER') is active
             and vars(activation_module).get('_ENTRY_CELL') is activation_cell
             and type(activation_cell) is tuple and len(activation_cell) == 2
             and activation_cell[0] is active and activation_cell[1] is scope.activation_scope)
    active_names = vars(active)
    _require(active_names.get('_scope') is scope.activation_scope
             and active_names.get('_ready') is True and active_names.get('_retired') is False
             and active_names.get('_uncertain') is False and active_names.get('_capturing') is False
             and active_names.get('_artifact_owner') is plan.owner
             and active_names.get('_artifact_cell') is reg.root
             and active_names.get('_artifact_attempt_cell') is vars(plan.owner).get('_attempt_cell')
             and type(reg.lineage) is reg.type_pins[0]
             and type(reg.native_origin) is reg.type_pins[2]
             and reg.lineage.ledger is reg.native_ledger and reg.lineage.native is reg.native_origin
             and reg.native_ledger.phase is reg.native_phase
             and type(reg.phase_type) is type and type(reg.native_phase) is reg.phase_type
             and type(reg.entry_module) is ModuleType
             and sys.modules.get('hmp_startup.gateway_entry') is reg.entry_module
             and reg.native_ledger.attempts is attempts and len(attempts) == attempt_count)
    names = vars(plan.owner)
    _require(names.get('_origin') is scope and names.get('_scope') is scope
             and names.get('_cell') is reg.cell and names.get('_root_cell') is reg.root
             and names.get('_native_scope_registration') is reg
             and names.get('_failed') is False and names.get('_unknown') is False
             and scope.native_startup_probe_origin[5] is execution.origin
             and scope.native_startup_probe_origin[6] is plan.blueprint
             and scope.cache is plan.source and plan.source.paths is plan.blueprint[4]
             and scope.context is plan.blueprint[2] and scope.expected is plan.blueprint[3]
             and type(execution.finished) is list and len(execution.finished) == 1
             and execution.finished[0] is True
             and type(execution.failed) is list and len(execution.failed) == 1
             and execution.failed[0] is False
             and type(execution.pending) is list and len(execution.pending) == 1
             and execution.pending[0] is None
             and type(execution.history) is list and len(execution.history) > 0
             and type(actual.predecessor) is _ProbeCommit
             and type(actual.predecessor.sequence) is int
             and actual.predecessor.sequence == len(execution.history)-1
             and type(execution.cursor) is list and len(execution.cursor) == 1
             and execution.cursor[0] is actual.predecessor.cursor)
    cursor = execution.cursor[0]
    policy._cursor_tail(cursor)
    _require(cursor.policy is plan.policy and cursor.action == 'finished'
             and type(execution.outcome) is list and len(execution.outcome) == 1
             and execution.outcome[0] is actual.outcome is actual.predecessor.outcome
             and type(actual.outcome) is tuple and len(actual.outcome) == 3
             and actual.outcome[0] is plan.policy.path
             and type(actual.outcome[1]) is int and actual.outcome[1] == cursor.missing-1
             and type(actual.outcome[2]) is tuple
             and len(actual.outcome[2]) == len(cursor.identities) == len(execution.opened)
             and type(actual.resources) is tuple and len(actual.resources) == len(execution.opened)
             and type(actual.closure) is tuple and len(actual.closure) == 6
             and type(execution.budget) is tuple and len(execution.budget) == 5)
    closure, budget, ledger = actual.closure, execution.budget, reg.native_ledger
    _require(type(ledger) is reg.type_pins[1]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(value) is int for value in ledger.counts)
             and type(ledger.attempts) is list
             and closure[0] is ledger.counts is budget[0]
             and closure[3] is ledger.attempts is budget[3]
             and all(type(value) is int for value in closure[1:3])
             and type(closure[4]) is int and closure[5] is execution.count
             and type(budget[1]) is type(budget[2]) is type(budget[4]) is int
             and closure[1] == budget[1]+len(execution.history)+2*len(actual.resources)
             and closure[2] == budget[2]
             and closure[4] == budget[4]+len(execution.history)+len(actual.resources)
             and ledger.counts[0] >= closure[1] and len(ledger.attempts) >= closure[4]
             and type(ledger.scopes) is list and type(reg.index) is int
             and 0 <= reg.index < len(ledger.scopes) and ledger.scopes[reg.index] is reg)
    predecessor = actual.predecessor
    for sequence in range(len(execution.history)-1, -1, -1):
        _require(type(predecessor) is _ProbeCommit
                 and type(predecessor.sequence) is int and predecessor.sequence == sequence
                 and execution.history[sequence] is predecessor
                 and type(predecessor.category) is str
                 and predecessor.category in ('returned', 'reported_missing')
                 and type(predecessor.consumer) is _ProbeConsumer
                 and predecessor.consumer.execution is execution)
        consumer = predecessor.consumer
        operation = consumer.operation
        _require(type(operation) is metadata._MetadataOperation
                 and operation.owner is plan.owner and operation.registration is reg
                 and type(operation.index) is int and 0 <= operation.index < closure[4]
                 and ledger.attempts[operation.index] is operation
                 and type(operation.result) is metadata._MetadataResult
                 and type(operation.state) is list and len(operation.state) == 3
                 and all(type(value) is bool for value in operation.state)
                 and operation.state == ([True, True, False] if predecessor.category == 'returned'
                                         else [True, False, False])
                 and type(operation.ended) is list and len(operation.ended) == 1
                 and operation.ended[0] is True
                 and type(consumer.commit) is list and len(consumer.commit) == 1
                 and consumer.commit[0] is predecessor)
        result = operation.result
        _require(type(result.acknowledged) is list and len(result.acknowledged) == 1
                 and result.acknowledged[0] is predecessor
                 and type(result.consumer) is list and len(result.consumer) == 1
                 and result.consumer[0] is consumer
                 and type(consumer.custody) is tuple and len(consumer.custody) == 6)
        origin, marker, link, slot, state, reference = consumer.custody
        _require(type(origin) is metadata._PayloadOrigin and type(marker) is origin.marker_type
                 and marker.owner is plan.owner and marker.operation is operation
                 and marker.origin is origin and marker.owner_link is link
                 and marker.marker_slot is slot and marker.state is state
                 and marker.reference is reference
                 and result.custody_origin is origin and result.custody_link is link
                 and result.custody_slot is slot
                 and type(link) is list and len(link) == 1 and link[0] is None
                 and type(slot) is list and len(slot) == 1 and slot[0] is marker
                 and type(state) is list and len(state) == 3
                 and state[0] is True and state[1] is True and state[2] is False)
        predecessor = consumer.predecessor
    _require(predecessor is None and type(scope.records) is list
             and len(scope.records) >= len(plan.base_records)+len(actual.resources)
             and all(scope.records[index] is row for index, row in enumerate(plan.base_records)))
    for index, pair in enumerate(actual.resources):
        _require(type(pair) is tuple and len(pair) == 2)
        row, fd = pair
        entry, outcome = execution.opened[index], actual.outcome[2][index]
        _require(type(entry) is tuple and len(entry) == 7
                 and type(row) is _NativeOpenedDescriptor and type(fd) is int
                 and row is entry[3] and fd is entry[4]
                 and entry[1] is plan.components[index]
                 and type(entry[5]) is tuple and len(entry[5]) == 5
                 and all(type(value) is int for value in entry[5])
                 and type(outcome) is tuple and len(outcome) == 2
                 and outcome[0] is plan.components[index]
                 and outcome[1] is cursor.identities[index] and outcome[1] == entry[5]
                 and scope.records[len(plan.base_records)+index] is row
                 and _descriptor_closed_in_scope(row, scope))
    return actual


def _historical_cohort(actual, scope):
    """Hold current original mirrors across observations, never persist them."""
    execution = actual.execution
    plan, registration = execution.plan, execution.registration
    _require(type(scope) is _Scope and registration.scope is scope
             and type(scope.activation) is activation_module.GatewayActivationOwner)
    objects = (plan.owner, scope.activation, plan.source.entry, plan.source.context_fact[0])
    dictionaries = []
    for object_ in objects:
        dictionary = vars(object_)
        _require(type(dictionary) is dict and len(dictionary) <= 512
                 and all(type(key) is str for key in dictionary))
        dictionaries.append((object_, dictionary, tuple(dictionary.items())))
    ledger, phase = registration.native_ledger, registration.native_phase
    cells = (ledger.counts, ledger.inflight, ledger.failed, ledger.failure, ledger.preparation,
             phase.current, phase.result)
    widths = (2, 1, 1, 1, 3, 1, 1)
    _require(all(type(cell) is list and len(cell) == width
                 for cell, width in zip(cells, widths, strict=True))
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and ledger.failure[0] is None
             and all(value is None for value in ledger.preparation)
             and phase.current[0] is phase.idle and phase.result[0] is None)
    return (tuple(dictionaries), tuple((cell, tuple(cell)) for cell in cells),
            ledger.attempts, len(ledger.attempts), vars(activation_module).get('_ENTRY_CELL'))


def _startup_parent_witness(source, scope):
    """Original lifecycle mirrors following full source validation, not authority.

    Parent owners are complete and quiescent during a probe. Immutable source
    facts stay held by the entry inputs. This witness rejects parent ownership,
    readiness and namespace changes at each stage without walking their old
    closed file descriptors again. Final startup sealing still checks receipts.
    """
    active = scope.activation
    objects = (source.entry, source.context_fact[0], source.inputs.entry,
               source.inputs.recipe, source.inputs.plugin, active,
               vars(active).get('_approval_owner'), vars(active).get('_selection_owner'))
    dictionaries, seen, exports = [], [], []
    for object_ in objects:
        if object_ is None or any(object_ is prior for prior in seen):
            continue
        dictionary = vars(object_)
        _require(type(dictionary) is dict and len(dictionary) <= 512
                 and all(type(key) is str for key in dictionary))
        dictionaries.append((object_, dictionary, tuple(dictionary.items())))
        seen.append(object_)
        name = vars(type(object_)).get('__module__')
        _require(type(name) is str)
        module = sys.modules.get(name)
        _require(type(module) is ModuleType)
        for key in ('_OWNER', '_ROOT', '_CELL', '_FACT', '_STARTED', '_ENTRY_OWNER', '_ENTRY_CELL'):
            if key in vars(module):
                exports.append((module, key, vars(module)[key]))
    return tuple(dictionaries), tuple(exports)
