"""Experimental complete fresh-probe engine; not an installed feature.

One closed producer serves the original probe sites. This module does not accept
paths, operations, policies or grants from a client. The actual admitted owner
must retain its execution and literal returns; DATA preparation is not admission.
The actual observe caller consumes the original typed finish; installation remains gated.
"""
from __future__ import annotations

import errno
import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from hmp_plugin import presentation_native_metadata as metadata
from hmp_plugin.presentation_metadata_custody import (
    _directory_payload_cells, _retire_directory_payload_data,
)
from hmp_plugin.presentation_startup_artifacts import (
    StartupArtifactOwner, _NativeOpenedDescriptor, _NativeProbeMetadataResource,
    _NativeScopeRegistration, _capture_native_scope, _descriptor_closed_in_scope,
    _descriptor_refused, _native_actor_context, _native_metadata_snapshot,
    _native_post_actor_state, _native_pre_actor_state, _native_work_origin_tail,
    _native_descriptor_opened, _require,
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

    def __repr__(self):
        return '<FreshProbeExecution experimental no-image-authority>'


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

    def __repr__(self):
        return '<FreshProbeCommit raw-free metadata redacted>'


class _ProbeFinish(NamedTuple):
    execution: _ProbeExecution
    predecessor: _ProbeCommit
    resources: tuple
    outcome: tuple

    def __repr__(self):
        return '<FreshProbeFinish original metadata-only return>'


def _new_probe_engine_origin():
    module = sys.modules.get(__name__)
    _require(type(module) is ModuleType and vars(module) is globals())
    kinds = (_ProbeExecution, _ProbeConsumer, _ProbeReturn, _ProbeCommit,
             metadata._ReportedMissingMetadataReturn, _ProbeFinish)
    types = tuple((kind, kind._fields,
                   tuple(vars(kind).get(name) for name in kind._fields)) for kind in kinds)
    functions = tuple((name, globals()[name], globals()[name].__code__) for name in (
        '_engine_origin_tail', '_execution_tail', '_history_tail',
        '_resource_tail', '_resource', '_consumer_tail',
        '_policy_values', '_run_observation', '_open_ancestor',
        '_finish', '_run_fresh_probe', '_lifecycle_tail',
        '_prepare_shared_consumer', '_latch_shared_consumer', '_produce_shared',
        '_consume_shared', '_ack_shared', '_retired_shared', '_history_mirrors_tail', '_attached_shared',
        '_make_shared_commit', '_commit_shared_tail', '_acked_shared_history', '_publish_shared_ack',
        '_finished_state_tail', '_opened_chain_tail'))
    return (module, types, functions, OSError.__dict__['errno'],
            OSError.__dict__['filename'], errno.ENOENT,
            (metadata, tuple((name, vars(metadata).get(name), vars(metadata).get(name).__code__)
                             for name in ('_produce_directory_metadata',
                                          '_consume_directory_policy', '_ack_directory_policy'))))


def _engine_origin_tail(origin):
    _require(type(origin) is tuple and len(origin) == 7
             and type(origin[0]) is ModuleType
             and sys.modules.get(__name__) is origin[0]
             and vars(origin[0]) is globals()
             and type(origin[1]) is tuple and len(origin[1]) == 6
             and type(origin[2]) is tuple and len(origin[2]) == 26
             and origin[3] is OSError.__dict__['errno']
             and origin[4] is OSError.__dict__['filename']
             and type(origin[5]) is int and origin[5] == errno.ENOENT)
    _require(type(origin[6]) is tuple and len(origin[6]) == 2
             and origin[6][0] is metadata and type(origin[6][1]) is tuple
             and len(origin[6][1]) == 3
             and sys.modules.get('hmp_plugin.presentation_native_metadata') is metadata)
    for name, function, code in origin[6][1]:
        _require(type(name) is str and type(function) is FunctionType
                 and vars(metadata).get(name) is function and function.__code__ is code
                 and function.__globals__ is vars(metadata))
    for kind, fields, members in origin[1]:
        _require(type(kind) is type and vars(kind).get('_fields') is fields
                 and all(vars(kind).get(name) is member
                         for name, member in zip(fields, members, strict=True)))
    for name, function, code in origin[2]:
        _require(type(name) is str and type(function) is FunctionType
                 and globals().get(name) is function and function.__code__ is code
                 and function.__globals__ is globals())
    return origin


def _execution_tail(execution):
    _require(type(execution) is _ProbeExecution)
    owner, plan, reg = execution.owner, execution.plan, execution.registration
    _engine_origin_tail(execution.origin)
    _require(execution.origin is plan.engine_origin
             and type(reg) is _NativeScopeRegistration and reg.owner is owner
             and reg.scope.native_probe_plan is plan
             and reg.scope.native_probe_engine_origin is execution.origin
             and vars(owner).get('_probe_execution') is execution
             and vars(owner).get('_origin') is reg.scope
             and vars(owner).get('_scope') is reg.scope
             and vars(owner).get('_probe_plan') is plan
             and vars(owner).get('_started') is True
             and vars(owner).get('_ready') is False
             and vars(owner).get('_failed') is False
             and vars(owner).get('_unknown') is False
             and vars(owner).get('_retaining') is False
             and vars(owner).get('_admitting') is False
             and vars(owner).get('_count_cell') is execution.count
             and vars(owner).get('_bytes_read') == 0
             and _capture_native_scope(reg.scope, reg.cell, reg.root) is reg
             and type(execution.next_site) is list and len(execution.next_site) == 1
             and type(execution.next_site[0]) is int
             and 0 <= execution.next_site[0] <= len(plan.definitions)
             and type(execution.pending) is list and len(execution.pending) == 1
             and type(execution.history) is list
             and len(execution.history) <= len(plan.definitions)
             and type(execution.opened) is list
             and len(execution.opened) < len(plan.components)
             and type(execution.outcome) is list and len(execution.outcome) == 1
             and type(execution.failed) is list and execution.failed == [False]
             and type(execution.finished) is list and len(execution.finished) == 1
             and type(execution.finished[0]) is bool
             and (execution.finished[0] is False or
                  (execution.next_site[0] == len(plan.definitions)
                   and execution.pending[0] is None)))
    _native_work_origin_tail(owner, reg, reg.native_origin)
    _lifecycle_tail(owner, reg.scope, reg, plan)
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
    """Join each actual directory open to its original component and parent."""
    _require(type(closed) is bool and type(execution) is _ProbeExecution)
    reg, plan = execution.registration, execution.plan
    _require(type(execution.opened) is list and type(reg.scope.records) is list
             and len(execution.opened) == len(reg.scope.records)
             and len(execution.opened) < len(plan.components))
    parent = None
    for position, entry in enumerate(execution.opened):
        _require(type(entry) is tuple and len(entry) == 7
                 and type(entry[0]) is int and entry[0] == position
                 and entry[1] is plan.components[position]
                 and type(entry[3]) is _NativeOpenedDescriptor
                 and type(entry[4]) is int and entry[4] >= 0
                 and type(entry[5]) is tuple and len(entry[5]) == 5
                 and all(type(value) is int for value in entry[5])
                 and type(entry[6]) is _ProbeCommit
                 and entry[6].identity is entry[5]
                 and entry[6].site == position * 6
                 and reg.scope.records[position] is entry[3])
        descriptor = entry[3]
        close = _native_descriptor_opened(descriptor, reg.native_ledger)
        allocation = descriptor.allocation
        flags = reg.native_origin.flags
        _require(descriptor.fd is entry[4]
                 and entry[2] is (None if parent is None else parent.fd)
                 and allocation.parent is parent and allocation.owner is execution.owner
                 and allocation.scope is reg.scope and allocation.registration is reg
                 and type(allocation.arguments) is tuple and len(allocation.arguments) == 3
                 and allocation.arguments[0] is entry[1]
                 and type(allocation.arguments[1]) is int
                 and allocation.arguments[1] == flags[0] | flags[1] | flags[2] | flags[3] | flags[4]
                 and allocation.arguments[2] is entry[2])
        if closed:
            _require(_descriptor_closed_in_scope(descriptor, reg.scope))
        else:
            _require(close.state == [False, False] and close.raw[0] is close.unset
                     and close.result[0] is None and allocation.refused == [False])
        parent = descriptor
    return execution


def _resource_tail(owner, resource):
    _require(type(resource) is _NativeProbeMetadataResource and resource.owner is owner
             and type(resource.metadata) is _ProbeExecution)
    execution = _execution_tail(resource.metadata)
    plan, reg = execution.plan, execution.registration
    _require(resource.registration is reg and type(resource.ordinal) is int
             and resource.ordinal == execution.next_site[0]
             and 0 <= resource.ordinal < len(plan.definitions)
             and resource.site is plan.definitions[resource.ordinal]
             and resource.variant is plan.variants[resource.ordinal])
    _opened_chain_tail(execution)
    position, offset = divmod(resource.ordinal, 6)
    _require(type(resource.arguments) is tuple)
    descriptor = None
    if offset == 1 or offset == 4:
        _require(position < len(execution.opened))
        row = execution.opened[position]
        descriptor = row[3]
        _require(type(descriptor) is _NativeOpenedDescriptor
                 and reg.scope.records[position] is descriptor)
        _native_descriptor_opened(descriptor, reg.native_ledger)
        _require(resource.descriptor is descriptor and len(resource.arguments) == 1
                 and resource.arguments[0] is descriptor.fd)
    else:
        if position:
            _require(position - 1 < len(execution.opened))
            descriptor = execution.opened[position - 1][3]
            _native_descriptor_opened(descriptor, reg.native_ledger)
        _require(resource.descriptor is descriptor and len(resource.arguments) == 2
                 and resource.arguments[0] is plan.components[position]
                 and resource.arguments[1] is (None if descriptor is None else descriptor.fd))
    return resource


def _resource(execution, predecessor):
    _history_tail(execution, predecessor)
    _require(execution.pending[0] is None)
    plan, index = execution.plan, execution.next_site[0]
    _require(index < len(plan.definitions))
    position, offset = divmod(index, 6)
    descriptor = (execution.opened[position][3] if offset in (1, 4) else
                  None if position == 0 else execution.opened[position - 1][3])
    arguments = ((descriptor.fd,) if offset in (1, 4) else
                 (plan.components[position], None if descriptor is None else descriptor.fd))
    values = (execution.owner, execution.registration, execution,
              plan.variants[index], plan.definitions[index], index, descriptor, arguments)
    resource = _NativeProbeMetadataResource(*values)
    _require(type(resource) is _NativeProbeMetadataResource
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
    consumer = actual.consumer
    operation = _consumer_tail(consumer, predecessor)
    result, phase = operation.result, operation.phase
    _require(consumer.execution is execution and phase.current[0] is phase.pending
             and phase.result[0] is operation and operation.ledger.inflight[0] is None
             and result.envelope[0] is actual and type(result.category[0]) is str and result.category[0] == actual.category
             and result.snapshot[0] is actual.snapshot
             and result.raw[0] is actual.raw and operation.ended == [True])
    plan, site = execution.plan, operation.resource.ordinal
    position, offset = divmod(site, 6)
    missing = actual.category == 'reported_missing'
    _require(actual.category in ('returned', 'reported_missing')
             and operation.state == ([True, False, False] if missing else [True, True, False]))
    identity = None
    if not missing:
        _require(type(actual.snapshot) is metadata._NativeMetadataSnapshot
                 and type(actual.snapshot.identity) is tuple
                 and len(actual.snapshot.identity) == 9
                 and all(type(x) is int for x in actual.snapshot.identity))
        full = actual.snapshot.identity
        identity = full[:5] if full[2] & 0o170000 == 0o040000 else full
    outcome = None
    if offset == 0:
        if missing:
            _require(position > 0)
            next_site = position * 6 + 2
        elif position < len(plan.components) - 1:
            identity = metadata._directory_identity(actual.snapshot, plan.context[1])
            next_site = position * 6 + 1
        else:
            if len(identity) == 5:
                _require(plan.row.state == 'tree_nonfile')
                relative = plan.path[len(plan.row.tree.path) + 1:] + '/'
                originals = tuple(value for prefix, value in plan.proof[0].directories
                                  if prefix == relative)
                _require(len(originals) == 1 and originals[0] == identity)
            else:
                _require(full[2] & 0o170000 == 0o100000 and plan.selected.cache is not None
                         and identity == plan.selected.cache.identity)
            next_site = position * 6 + 3
    elif offset == 1:
        _require(not missing and type(predecessor) is _ProbeCommit
                 and predecessor.site == position * 6 and identity == predecessor.identity)
        next_site = (position + 1) * 6
    elif offset == 2:
        _require(missing and type(predecessor) is _ProbeCommit
                 and predecessor.site == position * 6
                 and predecessor.category == 'reported_missing')
        outcome = ('missing_component', position - 1, None,
                   tuple(row[5] for row in execution.opened))
        next_site = 4
    elif offset == 3:
        _require(not missing and type(predecessor) is _ProbeCommit
                 and predecessor.site == position * 6 and identity == predecessor.identity)
        outcome = ('directory' if len(identity) == 5 else 'declared_regular',
                   position - 1, identity, tuple(row[5] for row in execution.opened))
        next_site = 4
    else:
        _require(offset in (4, 5) and not missing
                 and position < len(execution.opened)
                 and identity == execution.opened[position][5])
        next_site = (position * 6 + 5 if offset == 4 else
                     (position + 1) * 6 + 4 if position + 1 < len(execution.opened) else
                     len(plan.definitions))
    return (len(execution.history), site, next_site, actual.category, identity, outcome)


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
    _history_tail(execution, commit)
    position, offset = divmod(commit.site, 6)
    _require(offset == 0 and commit.category == 'returned'
             and execution.next_site[0] == position * 6 + 1
             and len(execution.opened) == position)
    name = execution.plan.components[position]
    parent = None if position == 0 else execution.opened[position - 1][4]
    row, fd = StartupArtifactOwner._open(execution.owner, name, parent, True,
                                        execution.registration)
    held.append((row, fd))  # actual return retained before any validation/callback
    execution.opened.append((position, name, parent, row, fd, commit.identity, commit))
    _require(type(row) is _NativeOpenedDescriptor and row.fd is fd
             and execution.registration.scope.records[position] is row)
    return commit


def _finish(execution, predecessor, held):
    _require(execution.finished == [False] and type(held) is list)
    resources = tuple(held)
    outcome = _finished_state_tail(execution, predecessor, resources)
    values = (execution, predecessor, resources, outcome)
    result = _ProbeFinish(*values)
    _engine_origin_tail(execution.origin)
    _require(type(result) is _ProbeFinish and tuple.__len__(result) == 4
             and all(tuple.__getitem__(result, i) is value for i, value in enumerate(values))
             and execution.finished == [False])
    _require(_finished_state_tail(execution, predecessor, resources) is outcome)
    execution.finished[0] = True
    return result


def _finished_state_tail(execution, predecessor, held):
    _history_tail(execution, predecessor)
    _opened_chain_tail(execution, closed=True)
    reg = execution.registration
    _require(type(held) is tuple)
    _require(execution.next_site[0] == len(execution.plan.definitions)
             and execution.pending[0] is None and type(execution.outcome[0]) is tuple
             and len(execution.outcome[0]) == 4
             and len(reg.scope.records) == len(execution.opened)
             and all(reg.scope.records[i] is row[3]
                     and _descriptor_closed_in_scope(row[3], reg.scope)
                     for i, row in enumerate(execution.opened))
             and reg.native_ledger.inflight == [None]
             and reg.native_ledger.failed == [False]
             and reg.native_phase.current[0] is reg.native_phase.idle
             and reg.native_phase.result == [None])
    budget = execution.budget
    _require(type(budget) is tuple and len(budget) == 5
             and reg.native_ledger.counts is budget[0]
             and reg.native_ledger.attempts is budget[3]
             and type(budget[1]) is int and type(budget[2]) is int and type(budget[4]) is int
             and all(type(value) is int for value in reg.native_ledger.counts)
             and reg.native_ledger.counts[0] == budget[1] + len(execution.history) + 2 * len(held)
             and reg.native_ledger.counts[1] == budget[2]
             and len(reg.native_ledger.attempts) == budget[4] + len(execution.history) + len(held)
             and len(held) == len(execution.opened)
             and all(row is execution.opened[i][3] and fd is execution.opened[i][4]
                     for i, (row, fd) in enumerate(held)))
    _history_mirrors_tail(execution, predecessor)
    outcomes = tuple(commit.outcome for commit in execution.history if commit.outcome is not None)
    _require(len(outcomes) == 1 and execution.outcome[0] is outcomes[0])
    return outcomes[0]


def _run_fresh_probe(owner, scope, registration, plan):
    _require(vars(owner).get('_probe_execution') is None
             and registration.scope is scope and scope.native_probe_plan is plan
             and vars(owner).get('_started') is True and scope.records == [])
    origin = _engine_origin_tail(plan.engine_origin)
    _lifecycle_tail(owner, scope, registration, plan)
    _native_work_origin_tail(owner, registration, registration.native_origin)
    arguments = (scope, registration, plan, origin)
    actor_state = _native_pre_actor_state(owner, arguments)
    native = registration.native_origin
    _native_actor_context(native.actor_calls, (native.native, native.thread_native), registration.context)
    _native_post_actor_state(owner, actor_state, arguments)
    _lifecycle_tail(owner, scope, registration, plan)
    ledger = registration.native_ledger
    budget = (ledger.counts, ledger.counts[0], ledger.counts[1], ledger.attempts, len(ledger.attempts))
    values = (owner, plan, registration, origin, vars(owner)['_count_cell'],
              [0], [None], [], [], [None], [False], [False], budget)
    execution = _ProbeExecution(*values)
    _engine_origin_tail(origin)
    _lifecycle_tail(owner, scope, registration, plan)
    _require(vars(owner).get('_probe_execution') is None and type(execution) is _ProbeExecution
             and tuple.__len__(execution) == len(values)
             and all(tuple.__getitem__(execution, i) is value for i, value in enumerate(values)))
    owner._probe_execution = execution
    held = []
    predecessor = None
    complete = False
    try:
        while execution.next_site[0] < len(plan.definitions):
            _require(len(execution.history) < len(plan.definitions))
            predecessor = _run_observation(execution, predecessor)
            if predecessor.site % 6 == 0 and predecessor.next_site % 6 == 1:
                _open_ancestor(execution, predecessor, held)
        complete = True
    except BaseException:
        pass
    finally:
        for row, fd in reversed(held):
            try:
                StartupArtifactOwner._close(owner, row, fd, scope, registration.root)
            except BaseException:
                _descriptor_refused(row)
                owner._unknown = True
                complete = False
    if not complete:
        execution.failed[0] = True
        raise metadata.ArtifactObservationError(owner) from None
    return _finish(execution, predecessor, held)


def _lifecycle_tail(owner, scope, registration, plan):
    """Pure original activation/continuation/source selection join; no effects."""
    _require(registration.owner is owner and registration.scope is scope
             and scope.native_probe_plan is plan and plan.owner is owner
             and scope.parent[0] is plan.root and scope.parent[1] is plan.selected
             and type(plan.root) is tuple and len(plan.root) == 3
             and plan.root[1] is scope.activation
             and vars(owner).get('_origin') is scope and vars(owner).get('_scope') is scope
             and vars(owner).get('_probe_plan') is plan
             and vars(owner).get('_started') is True
             and vars(owner).get('_ready') is False and vars(owner).get('_failed') is False
             and vars(owner).get('_unknown') is False
             and vars(owner).get('_root_cell') is registration.root
             and vars(owner).get('_cell') is registration.cell
             and plan.selected.plan_row is plan.row and plan.row.location is plan.location
             and plan.location.path is plan.path and plan.selected.proof is plan.proof
             and plan.material.__code__ is plan.material_code
             and plan.observe.__code__ is plan.observe_code
             and vars(plan.owner_type).get('_pure') is plan.material
             and vars(plan.owner_type).get('_observe_owned') is plan.observe)
    active, parent = vars(scope.activation), vars(plan.root[0])
    _require(active.get('_scope') is scope.activation_scope and active.get('_ready') is True
             and active.get('_retired') is False and active.get('_uncertain') is False
             and active.get('_continuation_owner') is plan.root[0]
             and active.get('_continuation_cell') is plan.root
             and parent.get('_root') is plan.root and parent.get('_source') is plan.root[2]
             and parent.get('_ready') is True and parent.get('_failed') is False
             and parent.get('_retired') is False)
    return scope


def _prepare_shared_consumer(owner, operation, predecessor, baseline, eof, custody):
    _require(type(operation) is metadata._MetadataOperation
             and type(operation.resource) is _NativeProbeMetadataResource
             and baseline is None and eof is None)
    execution = operation.resource.metadata
    _history_tail(execution, predecessor)
    _require(execution.pending[0] is None and operation.result.consumer == [None])
    values = (execution, operation, predecessor, [None], custody)
    consumer = _ProbeConsumer(*values)
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


def _produce_shared(owner, consumer):
    _require(type(consumer) is _ProbeConsumer and consumer.execution.owner is owner)
    origin = _engine_origin_tail(consumer.execution.origin)
    return origin[6][1][0][1](owner, consumer)


def _consume_shared(owner, consumer, actual):
    _require(type(consumer) is _ProbeConsumer and consumer.execution.owner is owner)
    origin = _engine_origin_tail(consumer.execution.origin)
    return origin[6][1][1][1](owner, consumer, actual)


def _ack_shared(owner, consumer, actual, commit):
    _require(type(consumer) is _ProbeConsumer and consumer.execution.owner is owner)
    origin = _engine_origin_tail(consumer.execution.origin)
    return origin[6][1][2][1](owner, consumer, actual, commit)


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
    values = (consumer, *_policy_values(consumer.execution, actual, consumer.predecessor))
    kind = _ProbeCommit
    commit = kind(*values)
    _engine_origin_tail(consumer.execution.origin)
    _require(type(commit) is kind and kind is _ProbeCommit and tuple.__len__(commit) == len(values)
             and all(tuple.__getitem__(commit, i) is value for i, value in enumerate(values)))
    return commit


def _commit_shared_tail(owner, consumer, actual, commit):
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    expected = _policy_values(consumer.execution, actual, consumer.predecessor)
    values = (commit.sequence, commit.site, commit.next_site,
              commit.category, commit.identity, commit.outcome)
    _require(all(type(value) is int for value in values[:3])
             and type(values[3]) is str and values[3] in ('returned', 'reported_missing'))
    identity, outcome = values[4:]
    _require(identity is None or (type(identity) is tuple and len(identity) in (5, 9)
                                  and all(type(value) is int for value in identity)))
    if outcome is not None:
        _require(type(outcome) is tuple and len(outcome) == 4
                 and type(outcome[0]) is str and type(outcome[1]) is int
                 and (outcome[2] is None or (type(outcome[2]) is tuple
                      and len(outcome[2]) in (5, 9) and all(type(x) is int for x in outcome[2])))
                 and type(outcome[3]) is tuple
                 and all(type(row) is tuple and len(row) == 5
                         and all(type(x) is int for x in row) for row in outcome[3]))
    _require(values == expected and consumer.consumption[0] is actual
             and consumer.commit[0] is commit)
    return commit


def _publish_shared_ack(owner, consumer, commit):
    _require(type(consumer) is _ProbeConsumer and type(commit) is _ProbeCommit
             and consumer.execution.owner is owner and commit.consumer is consumer)
    execution = consumer.execution
    _lifecycle_tail(owner, execution.registration.scope, execution.registration, execution.plan)
    _require(type(commit.sequence) is int and commit.sequence == len(execution.history)
             and execution.pending[0] is consumer
             and consumer.commit[0] is consumer.operation.result.acknowledged[0] is commit)
    execution.history.append(commit)
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
