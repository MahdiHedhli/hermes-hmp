"""Unwired executable-link metadata policy on the shared native kernel.

This is an incomplete member of the coupled LP3 implementation. Existing early
origins do not contain this engine and refuse its resources before admission.
Neither this module nor its internal constructors enable a service or images.
The distinct byte family, actual driver/finish and early binding must land before
the native caller is connected or this source can be qualified for installation.
"""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from . import presentation_link_path_policy as policy
from . import presentation_native_metadata as metadata
from .presentation_startup_artifacts import (
    StartupArtifactOwner, _NativeLinkMetadataResource, _NativeOpenedDescriptor,
    _NativeOpenAllocation, _LinkSnapshot, _LinkTargetObservation,
    _NativeLinkBytesResource, _LinkRead,
    _NativeScopeRegistration, _Scope, _native_descriptor_opened,
    _native_work_origin_tail, _native_work_registration_tail, _require,
    _runtime_current,
    _native_walk_scope, _close_native_file_known, _prepare_native_link_open,
    _native_descriptor_closed, ArtifactObservationError,
)


class _LinkExecution(NamedTuple):
    owner: object
    registration: object
    blueprint: object
    origin: tuple
    policy: object
    definitions: tuple
    before_state: object
    baseline: object
    count: list
    cursor: list
    pending: list
    history: list
    opened: list
    failed: list
    finished: list
    budget: tuple
    fact: object
    after_state: object
    actions: list
    open_custody: list
    closed: list

    def __repr__(self):
        return '<LinkExecution incomplete native traversal redacted>'


class _LinkMetadataCommit(NamedTuple):
    consumer: object
    sequence: int
    site: int
    before: object
    cursor: object
    identity: tuple

    def __repr__(self):
        return '<LinkMetadataCommit raw-free fixed policy redacted>'


_LinkMetadataConsumer = metadata._LinkMetadataConsumer
_LinkBytesConsumer = metadata._LinkBytesConsumer


class _LinkBytesCommit(NamedTuple):
    consumer: object
    sequence: int
    site: int
    before: object
    cursor: object
    length: int
    before_count: tuple
    after_count: tuple
    record: object

    def __repr__(self):
        return '<LinkBytesCommit actual raw-free length/count ACK redacted>'


class _LinkAction(NamedTuple):
    site: tuple
    before: object
    after: object
    evidence: object

    def __repr__(self):
        return '<LinkAction literal original traversal handoff redacted>'


class _LinkPathFinish(NamedTuple):
    execution: _LinkExecution
    outcome: tuple
    actions: tuple
    history: tuple
    closed: tuple
    count: tuple
    budget: tuple

    def __repr__(self):
        return '<LinkPathFinish original closed traversal return redacted>'

# Only these five aliases may use the shared module's namespace. The stage
# selector validates both their retained kernel exports and these aliases.
_produce_shared = metadata._produce_directory_metadata
_consume_shared = metadata._consume_directory_policy
_ack_shared = metadata._ack_directory_policy
_attached_shared = metadata._acked_directory_commit_tail
_retired_shared = metadata._retired_directory_commit_tail
_open_shared = StartupArtifactOwner._open
_close_known_shared = _close_native_file_known
_prepare_open_shared = _prepare_native_link_open


def _engine_origin_tail(origin):
    """Validate the actual early packet; never capture a current replacement."""
    _require(type(origin) is tuple and len(origin) == 4
             and type(origin[0]) is ModuleType
             and sys.modules.get('hmp_plugin.presentation_native_link') is origin[0]
             and vars(origin[0]) is globals()
             and type(origin[1]) is tuple and type(origin[2]) is tuple
             and type(origin[3]) is tuple)
    _require(type(metadata) is ModuleType
             and sys.modules.get('hmp_plugin.presentation_native_metadata') is metadata)
    kernel_names = vars(metadata)
    _require(all(type(k) is str for k in kernel_names)
             and all(type(row) is tuple and len(row) == 7 and type(row[0]) is str
                     for row in origin[3]))
    first = tuple(row for row in origin[3] if row[0] == '_link_function_pin')
    _require(len(first) == 1)
    first = first[0]
    # No call through the helper being authenticated. Its original defaults
    # are empty; inspect code/global/export identity before the first call.
    _require(type(first[1]) is FunctionType and first[3] is kernel_names
             and kernel_names.get('_link_function_pin') is first[1]
             and first[1].__globals__ is kernel_names
             and first[4] is first[5] is None
             and type(first[6]) is tuple and len(first[6]) == 0)
    pin_function = first[1]
    if (pin_function.__code__ is not first[2]
            or pin_function.__defaults__ is not None
            or pin_function.__kwdefaults__ is not None):
        raise metadata.ArtifactObservationError from None
    expected = (_LinkExecution, _LinkMetadataConsumer, _LinkMetadataCommit,
                _NativeLinkMetadataResource, _LinkBytesConsumer, _LinkBytesCommit,
                _NativeLinkBytesResource, metadata._LinkBytesOperation,
                metadata._LinkBytesResult, metadata._LinkBytesReturn, _LinkRead,
                _LinkAction, _LinkPathFinish)
    _require(len(origin[1]) == len(expected))
    for row, selected in zip(origin[1], expected, strict=True):
        _require(type(row) is tuple and len(row) == 9 and row[0] is selected)
        kind, fields, members, constructor, code, namespace, defaults, bases, dispatch = row
        names = vars(kind)
        actual = names.get('__init__' if fields is None else '__new__')
        if type(actual) is staticmethod:
            actual = actual.__func__
        _require(type(kind) is type and actual is constructor and type(constructor) is FunctionType
                 and constructor.__code__ is code and constructor.__globals__ is namespace
                 and constructor.__defaults__ is defaults and kind.__bases__ is bases
                 and all(names.get(n) is member for n, member in dispatch))
        if fields is None:
            _require(kind is _LinkRead and len(names) == len(members)
                     and all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                             and pair[0] in names and names[pair[0]] is pair[1]
                             for pair in members))
        else:
            _require(type(fields) is tuple and names.get('_fields') is fields
                     and namespace.get('_tuple_new') is tuple.__new__
                     and all(names.get(n) is member for n, member in zip(fields, members, strict=True)))
    shared = {'_produce_shared': '_produce_directory_metadata',
              '_consume_shared': '_consume_directory_policy',
              '_ack_shared': '_ack_directory_policy',
              '_attached_shared': '_acked_directory_commit_tail',
              '_retired_shared': '_retired_directory_commit_tail'}
    effects = ('_open_shared', '_close_known_shared', '_prepare_open_shared')
    required_functions = (
        '_engine_origin_tail', '_execution_mirrors', '_opened_chain_tail', '_lifetime_tail',
        '_resource_tail', '_prepare_shared_consumer', '_latch_shared_consumer',
        '_make_shared_commit', '_commit_shared_tail', '_publish_shared_ack',
        '_acked_shared_history', '_resource_bindings', '_byte_record_tail', '_make_shared_bytes_commit',
        '_commit_shared_bytes_tail', '_publish_shared_bytes_ack',
        '_acked_shared_bytes_history', *shared,
        '_effect_pin', '_new_execution', '_append_action', '_finish_mirrors',
        '_finish_path', '_drive_native_path', *effects,
    )
    _require(all(type(row) is tuple and len(row) == 7 and type(row[0]) is str
                 for row in origin[2])
             and len(origin[2]) == len(required_functions)
             and len({row[0] for row in origin[2]}) == len(required_functions)
             and all(name in required_functions for name, *_ in origin[2]))
    for row in origin[2]:
        _require(type(row) is tuple and len(row) == 7 and type(row[0]) is str)
        name = row[0]
        if (pin_function.__code__ is not first[2]
                or pin_function.__defaults__ is not None
                or pin_function.__kwdefaults__ is not None
                or kernel_names['_link_function_pin'] is not pin_function):
            raise metadata.ArtifactObservationError from None
        if name in shared:
            _require(globals().get(name) is row[1])
            pin_function((shared[name], *row[1:]), kernel_names, shared[name])
        elif name in effects:
            _require(globals().get(name) is row[1] and type(row[1]) is FunctionType
                     and row[1].__code__ is row[2] and row[1].__globals__ is row[3]
                     and row[1].__defaults__ is row[4] and row[1].__kwdefaults__ is row[5]
                     and type(row[6]) is tuple)
            namespace = row[3]
            _require(type(namespace) is dict and all(type(k) is str for k in namespace)
                     and namespace.get('StartupArtifactOwner') is StartupArtifactOwner)
            if name == '_open_shared':
                _require(vars(StartupArtifactOwner).get('_open') is row[1])
            elif name == '_close_known_shared':
                _require(namespace.get('_close_native_file_known') is row[1])
            else:
                _require(namespace.get('_prepare_native_link_open') is row[1])
            if row[5] is not None:
                _require(type(row[5]) is dict and len(row[5]) == len(row[6])
                         and all(type(k) is str for k in row[5])
                         and all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                                 and pair[0] in row[5] and row[5][pair[0]] is pair[1]
                                 for pair in row[6]))
            else:
                _require(len(row[6]) == 0)
        else:
            pin_function(row, globals(), name)
    required_kernel = (
        '_link_function_pin', '_closed_link_engine_origin', '_link_policy_helper',
        '_link_stage_functions', '_rejoin_link_stages', '_link_current_lifetime_tail',
        '_resource_tail', '_prepare_metadata_operation_with_custody',
        '_undebited_directory_cells_tail', '_unspent_directory_cells_tail',
        '_unused_directory_cells_tail', '_unused_directory_intent_tail',
        '_latched_directory_resource_tail', '_charged_directory_history_tail',
        '_charged_directory_operation_tail', '_active_directory_operation_tail',
        '_directory_admission_preparation_tail', '_admit_directory_operation',
        '_returned_directory_operation_tail', '_pending_directory_cohort_tail',
        '_pending_directory_return_tail', '_produce_directory_metadata',
        '_consuming_directory_return_tail', '_directory_commit_cohort_tail',
        '_prepared_directory_commit_tail', '_consume_directory_policy',
        '_directory_ack_preparation_tail', '_acked_directory_history_tail',
        '_acked_directory_commit_tail', '_retired_directory_commit_tail',
        '_ack_directory_policy', '_run_directory_observation',
        '_capture_payload_origin', '_allocate_directory_custody', '_origin_tail',
        '_directory_payload_cells', '_marker_tail', '_payload_state_is_clear',
        '_native_actor_context', '_native_pre_actor_state', '_native_post_actor_state',
        '_native_work_origin_tail', '_native_work_registration_tail',
        '_native_metadata_snapshot', '_require',
        '_operation_result_family', '_capture_link_byte_count', '_retain_link_byte_failure',
    )
    _require(all(type(row) is tuple and len(row) == 7 and type(row[0]) is str
                 for row in origin[3])
             and len({row[0] for row in origin[3]}) == len(origin[3])
             and all(name in tuple(row[0] for row in origin[3]) for name in required_kernel))
    for row in origin[3]:
        _require(kernel_names.get(row[0]) is row[1])
        if (pin_function.__code__ is not first[2]
                or pin_function.__defaults__ is not None
                or pin_function.__kwdefaults__ is not None
                or kernel_names['_link_function_pin'] is not pin_function):
            raise metadata.ArtifactObservationError from None
        pin_function(row, row[3], row[0])
    return origin


def _execution_mirrors(execution):
    """Current path DATA and original runtime identity, never effect admission."""
    _require(type(execution) is _LinkExecution)
    owner, reg = tuple.__getitem__(execution, 0), tuple.__getitem__(execution, 1)
    _require(type(owner) is StartupArtifactOwner and type(reg) is _NativeScopeRegistration
             and reg.owner is owner and type(reg.scope) is _Scope
             and vars(owner).get('_native_link_execution') is execution
             and vars(owner).get('_origin') is reg.scope
             and vars(owner).get('_scope') is reg.scope
             and vars(owner).get('_cell') is reg.cell
             and vars(owner).get('_root_cell') is reg.root
             and tuple.__getitem__(reg.scope, 17) is execution.blueprint
             and type(execution.origin) is tuple and len(execution.origin) == 4)
    parent = tuple.__getitem__(reg.lineage, 4)
    blueprint = tuple.__getitem__(execution, 2)
    _require(type(parent) is tuple and len(parent) == 5
             and type(parent[4]) is tuple and len(parent[4]) >= 11
             and type(blueprint) is parent[4][6][0]
             and type(parent[0]) is tuple and len(parent[0]) == 5
             and parent[0][4] is execution.origin
             and tuple.__getitem__(execution.blueprint, 4) is parent
             and tuple.__getitem__(execution.blueprint, 0) is owner
             and tuple.__getitem__(execution.blueprint, 3) is reg.lineage
             and type(execution.policy) is policy._LinkPathPolicy
             and any(row is execution.policy for row in execution.blueprint.rows)
             and execution.policy.plan is execution.blueprint.link
             and reg.scope.runtime is execution.blueprint.runtime
             and type(execution.definitions) is tuple
             and all(type(row) is tuple and len(row) == 3
                     and type(row[0]) is int and row[0] in (0, 3, 4, 5)
                     and type(row[1]) in (int, str)
                     and type(row[2]) in (int, type(None))
                     for row in execution.definitions)
             and execution.definitions == tuple(
                 ({'open': 0, 'fstat': 4, 'stat': 3, 'readlink': 5}[kind], name, parent)
                 for kind, name, parent in policy._sites(execution.policy))
             and type(execution.cursor) is list and len(execution.cursor) == 1
             and type(execution.cursor[0]) is policy._LinkPathCursor
             and execution.cursor[0].policy is execution.policy
             and type(execution.pending) is list and len(execution.pending) == 1
             and type(execution.history) is list and type(execution.opened) is list
             and type(execution.count) is list and len(execution.count) == 1
             and vars(owner).get('_count_cell') is execution.count[0]
             and execution.blueprint.runtime.count[0] is execution.count[0]
             and type(execution.failed) is list and len(execution.failed) == 1
             and execution.failed[0] is False
             and type(execution.finished) is list and len(execution.finished) == 1
             and type(execution.finished[0]) is bool)
    _require(type(execution.actions) is list and type(execution.open_custody) is list
             and type(execution.closed) is list and type(execution.budget) is tuple
             and len(execution.budget) == 4
             and execution.registration.native_ledger.counts is execution.budget[0]
             and type(execution.budget[1]) is int and type(execution.budget[2]) is int
             and type(execution.budget[3]) is tuple
             and type(execution.budget[0]) is list and len(execution.budget[0]) == 2
             and all(type(value) is int for value in execution.budget[0])
             and execution.budget[0][0] >= execution.budget[1]
             and execution.budget[0][1] == execution.budget[2] + len(execution.opened) - len(execution.closed)
             and type(execution.cursor[0].position) is int
             and 0 <= execution.cursor[0].position - len(execution.actions) <= 1)
    # The shared caller validates its literal ACK before returning it to the
    # driver. During that one handoff the policy is one step ahead of actions;
    # only the actual acknowledged commit can explain that gap.
    if len(execution.actions) != execution.cursor[0].position:
        _require(execution.pending[0] is None and len(execution.history) > 0
                 and type(execution.history[-1]) in (_LinkMetadataCommit, _LinkBytesCommit)
                 and execution.history[-1].cursor is execution.cursor[0]
                 and execution.history[-1].site == len(execution.actions))
    count = execution.count[0]
    _require(type(count) is tuple and len(count) == 3 and count[0] is owner
             and count[1] is reg.scope and type(count[2]) is int
             and vars(owner).get('_bytes_read') is count[2]
             and vars(owner).get('_failed') is False and vars(owner).get('_unknown') is False
             and vars(owner).get('_reading') is False
             and vars(owner).get('_ready') is (execution.policy.phase == 'recheck'))
    runtime = execution.blueprint.runtime
    if execution.policy.phase == 'before':
        _require(execution.before_state is execution.after_state is execution.fact is None
                 and execution.baseline is None
                 and runtime.before[0] is runtime.after[0] is None)
    else:
        before = execution.before_state
        _require(type(before) is _LinkSnapshot and before.source is runtime
                 and before.phase == 0 and runtime.before[0] is before)
        if execution.policy.phase == 'after':
            _require(execution.after_state is execution.fact is None and runtime.after[0] is None)
            snapshot = before
        else:
            after, fact = execution.after_state, execution.fact
            _require(type(after) is _LinkSnapshot and after.source is runtime and after.phase == 1
                     and runtime.after[0] is after and type(fact) is tuple and len(fact) == 5
                     and vars(owner).get('_fact_cell') is fact
                     and reg.scope.activation._artifact_fact_cell is fact
                     and type(fact[4]) is _LinkTargetObservation
                     and fact[4].before is before and fact[4].after is after
                     and fact[4].owner is owner and fact[4].scope is reg.scope
                     and fact[4].source is runtime)
            snapshot = after
        _require(type(snapshot.links) is tuple
                 and len(snapshot.links) == len(runtime.link.hops))
        if execution.policy.hop is None:
            expected = snapshot.target
        else:
            index = execution.policy.index
            _require(type(index) is int and 0 <= index < len(snapshot.links))
            row = snapshot.links[index]
            _require(type(row) is tuple and len(row) == 2 and row[0] is execution.policy.hop)
            expected = row[1]
        _require(execution.baseline is expected)
        baseline = execution.baseline
        _require(type(baseline) is tuple and len(baseline) == 2
                 and type(baseline[0]) is tuple and len(baseline[0]) == 9
                 and all(type(value) is int for value in baseline[0])
                 and type(baseline[1]) is tuple
                 and len(baseline[1]) == len(execution.policy.components) - 1)
        for index, row in enumerate(baseline[1]):
            _require(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                     and type(row[1]) is tuple and len(row[1]) == 5
                     and all(type(value) is int for value in row[1])
                     and row[0] == execution.policy.components[index])
    return execution


def _opened_chain_tail(execution):
    _require(type(execution) is _LinkExecution)
    reg = tuple.__getitem__(execution, 1)
    _require(type(reg) is _NativeScopeRegistration
             and type(tuple.__getitem__(execution, 4)) is policy._LinkPathPolicy)
    _require(len(execution.opened) <= len(execution.policy.components) - 1)
    previous = None
    for index, descriptor in enumerate(execution.opened):
        _require(type(descriptor) is _NativeOpenedDescriptor)
        allocation = descriptor.allocation
        _require(type(allocation) is _NativeOpenAllocation
                 and allocation.owner is execution.owner and allocation.registration is reg
                 and allocation.scope is reg.scope and allocation.parent is previous
                 and allocation.native is reg.native_origin
                 and type(allocation.arguments) is tuple and len(allocation.arguments) == 3
                 and type(allocation.arguments[0]) is str
                 and allocation.arguments[0] == execution.policy.components[index]
                 and type(allocation.arguments[1]) is int
                 and allocation.arguments[1] == (reg.native_origin.flags[0]
                     | reg.native_origin.flags[1] | reg.native_origin.flags[2]
                     | reg.native_origin.flags[3] | reg.native_origin.flags[4])
                 and allocation.arguments[2] is (None if previous is None else previous.fd)
                 and _native_descriptor_opened(descriptor, reg.native_ledger) is descriptor.close
                 and allocation.refused[0] is False
                 and type(descriptor.close.state) is list and len(descriptor.close.state) == 2
                 and descriptor.close.state[0] is descriptor.close.state[1] is False
                 and descriptor.close.raw[0] is descriptor.close.unset
                 and descriptor.close.result[0] is None)
        previous = descriptor
    return execution


def _lifetime_tail(owner, consumer):
    _require(type(consumer) in (_LinkMetadataConsumer, _LinkBytesConsumer))
    execution = tuple.__getitem__(consumer, 0)
    _require(type(execution) is _LinkExecution and tuple.__getitem__(execution, 0) is owner)
    _engine_origin_tail(tuple.__getitem__(execution, 3))
    binding_rows = tuple(row for row in execution.origin[2] if row[0] == '_resource_bindings')
    _require(len(binding_rows) == 1)
    binding_row = binding_rows[0]
    bindings = binding_row[1]
    record_rows = tuple(row for row in execution.origin[2] if row[0] == '_byte_record_tail')
    _require(len(record_rows) == 1)
    record_row, record_check = record_rows[0], record_rows[0][1]
    _execution_mirrors(execution)
    reg = execution.registration
    _native_work_registration_tail(owner, reg)
    _runtime_current(execution.blueprint.runtime, owner)
    _require(StartupArtifactOwner._guard(owner) is reg.scope)
    _opened_chain_tail(execution)
    _native_work_origin_tail(owner, reg, reg.native_origin)
    _require(_execution_mirrors(execution) is execution
             and execution.pending[0] is consumer
             and consumer.operation.resource.execution is execution)
    if type(consumer) is _LinkBytesConsumer:
        if (record_check.__code__ is not record_row[2]
                or record_check.__defaults__ is not record_row[4]
                or record_check.__kwdefaults__ is not record_row[5]):
            raise metadata.ArtifactObservationError from None
        record_check(execution, consumer.operation.resource)
    if (bindings.__code__ is not binding_row[2]
            or bindings.__defaults__ is not binding_row[4]
            or bindings.__kwdefaults__ is not binding_row[5]):
        raise metadata.ArtifactObservationError from None
    bindings(execution, consumer.operation.resource)
    return reg.scope


def _resource_tail(owner, resource):
    _require(type(resource) in (_NativeLinkMetadataResource, _NativeLinkBytesResource)
             and tuple.__getitem__(resource, 0) is owner)
    execution = tuple.__getitem__(resource, 2)
    _require(type(execution) is _LinkExecution)
    _engine_origin_tail(tuple.__getitem__(execution, 3))
    binding_rows = tuple(row for row in execution.origin[2] if row[0] == '_resource_bindings')
    _require(len(binding_rows) == 1)
    binding_row = binding_rows[0]
    bindings = binding_row[1]
    record_rows = tuple(row for row in execution.origin[2] if row[0] == '_byte_record_tail')
    _require(len(record_rows) == 1)
    record_row, record_check = record_rows[0], record_rows[0][1]
    _execution_mirrors(execution)
    _require(execution.owner is owner and execution.registration is resource.registration
             and execution.finished[0] is False and type(resource.ordinal) is int
             and resource.ordinal == execution.cursor[0].position
             and 0 <= resource.ordinal < len(execution.definitions)
             and execution.definitions[resource.ordinal] is resource.site
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int
             and resource.site[0] in ((5,) if type(resource) is _NativeLinkBytesResource else (3, 4))
             and type(resource.arguments) is tuple)
    _opened_chain_tail(execution)
    operation, name, parent = resource.site
    if operation == 4:
        _require(type(name) is int and 0 <= name < len(execution.opened)
                 and parent is None and resource.descriptor is execution.opened[name]
                 and len(resource.arguments) == 1
                 and resource.arguments[0] is resource.descriptor.fd)
    elif operation == 5:
        _require(type(resource) is _NativeLinkBytesResource and type(name) is str
                 and name is execution.policy.components[-1]
                 and type(parent) is int and parent == len(execution.policy.components) - 2
                 and 0 <= parent < len(execution.opened)
                 and resource.descriptor is execution.opened[parent]
                 and len(resource.arguments) == 2 and type(resource.arguments[0]) is bytes
                 and resource.arguments[1] is resource.descriptor.fd)
        origin = tuple.__getitem__(execution.blueprint, 4)
        encoded = resource.encoded
        _require(type(encoded) is origin[4][10][0]
                 and tuple.__getitem__(encoded, 0) is origin
                 and tuple.__getitem__(encoded, 1) is name
                 and tuple.__getitem__(encoded, 2) is resource.arguments[0]
                 and tuple.__getitem__(encoded, 3) is origin[0][3])
        if (record_check.__code__ is not record_row[2]
                or record_check.__defaults__ is not record_row[4]
                or record_check.__kwdefaults__ is not record_row[5]):
            raise metadata.ArtifactObservationError from None
        record_check(execution, resource)
    else:
        _require(type(name) is str and len(resource.arguments) == 2
                 and resource.arguments[0] is name)
        if parent is None:
            _require(name == '/' and resource.descriptor is None
                     and resource.arguments[1] is None)
        else:
            _require(type(parent) is int and 0 <= parent < len(execution.opened)
                     and resource.descriptor is execution.opened[parent]
                     and resource.arguments[1] is resource.descriptor.fd)
    reg = execution.registration
    _native_work_registration_tail(owner, reg)
    _runtime_current(execution.blueprint.runtime, owner)
    _require(StartupArtifactOwner._guard(owner) is reg.scope)
    _native_work_origin_tail(owner, reg, reg.native_origin)
    _require(_execution_mirrors(execution) is execution
             and execution.definitions[resource.ordinal] is resource.site
             and execution.cursor[0].position == resource.ordinal)
    _opened_chain_tail(execution)
    if type(resource) is _NativeLinkBytesResource:
        if (record_check.__code__ is not record_row[2]
                or record_check.__defaults__ is not record_row[4]
                or record_check.__kwdefaults__ is not record_row[5]):
            raise metadata.ArtifactObservationError from None
        record_check(execution, resource)
    if (bindings.__code__ is not binding_row[2]
            or bindings.__defaults__ is not binding_row[4]
            or bindings.__kwdefaults__ is not binding_row[5]):
        raise metadata.ArtifactObservationError from None
    bindings(execution, resource)
    return resource


def _prepare_shared_consumer(owner, operation, predecessor, baseline, eof, custody):
    _require(metadata._operation_result_family(operation)
             and ((type(operation) is metadata._MetadataOperation
                   and type(operation.resource) is _NativeLinkMetadataResource)
                  or (type(operation) is metadata._LinkBytesOperation
                      and type(operation.resource) is _NativeLinkBytesResource))
             and baseline is None and eof is None)
    resource = _resource_tail(owner, operation.resource)
    execution = resource.execution
    expected = None if not execution.history else execution.history[-1]
    _require(predecessor is expected and execution.pending[0] is None
             and type(operation.result.consumer) is list and len(operation.result.consumer) == 1
             and operation.result.consumer[0] is None)
    values = (execution, operation, predecessor, [None], custody, execution.cursor[0])
    index = 4 if type(operation) is metadata._LinkBytesOperation else 1
    kind, _, _, constructor, _, _, _, _, _ = execution.origin[1][index]
    consumer = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(consumer) is kind
             and all(tuple.__getitem__(consumer, i) is value for i, value in enumerate(values))
             and execution.pending[0] is None and operation.result.consumer[0] is None
             and execution.cursor[0] is values[-1])
    operation.result.consumer[0] = consumer
    return consumer


def _latch_shared_consumer(owner, consumer, rejoin=False):
    _require(type(consumer) in (_LinkMetadataConsumer, _LinkBytesConsumer)
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and consumer.owner is owner
             and metadata._operation_result_family(consumer.operation)
             and ((type(consumer) is _LinkMetadataConsumer
                   and type(consumer.operation) is metadata._MetadataOperation)
                  or (type(consumer) is _LinkBytesConsumer
                      and type(consumer.operation) is metadata._LinkBytesOperation)))
    execution, operation = consumer.execution, consumer.operation
    _require(operation.owner is owner and operation.resource.execution is execution
             and operation.resource.registration is execution.registration)
    _resource_tail(owner, operation.resource)
    if not rejoin:
        _require(execution.pending[0] is None and operation.result.consumer[0] is consumer)
        execution.pending[0] = consumer
    _require(execution.pending[0] is consumer
             and execution.cursor[0] is consumer.cursor
             and consumer.predecessor is (None if not execution.history else execution.history[-1])
             and operation.result.consumer[0] is consumer)
    _lifetime_tail(owner, consumer)
    return consumer


def _make_shared_commit(owner, consumer, actual):
    _require(type(consumer) is _LinkMetadataConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and consumer.owner is owner)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    execution, before = consumer.execution, consumer.cursor
    action = execution.definitions[before.position]
    identity = actual.snapshot.identity
    _require(type(identity) is tuple and len(identity) == 9
             and all(type(value) is int for value in identity))
    leaf = 2 * (len(execution.policy.components) - 1)
    if before.position not in (leaf, leaf + 1 + (execution.policy.hop is not None
                                               and execution.policy.phase != 'recheck')):
        identity = tuple.__getitem__(identity, slice(0, 5))
    if execution.baseline is not None:
        if len(identity) == 9:
            baseline = execution.baseline[0]
        else:
            index = (action[1] if action[0] == 4
                     else 0 if action[2] is None else action[2] + 1)
            _require(type(index) is int and 0 <= index < len(execution.baseline[1]))
            baseline = execution.baseline[1][index][1]
        _require(identity == baseline)
    following = policy._advance(before, 'returned', identity)
    values = (consumer, len(execution.history), before.position, before, following, identity)
    kind, _, _, constructor, _, _, _, _, _ = execution.origin[1][2]
    commit = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(commit) is _LinkMetadataCommit
             and all(tuple.__getitem__(commit, i) is value for i, value in enumerate(values))
             and execution.cursor[0] is before and execution.definitions[before.position] is action)
    return commit


def _commit_shared_tail(owner, consumer, actual, commit):
    _require(type(consumer) is _LinkMetadataConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and type(commit) is _LinkMetadataCommit
             and type(tuple.__getitem__(commit, 3)) is policy._LinkPathCursor
             and type(tuple.__getitem__(commit, 4)) is policy._LinkPathCursor
             and type(tuple.__getitem__(tuple.__getitem__(commit, 3), 1)) is int
             and type(tuple.__getitem__(tuple.__getitem__(commit, 4), 1)) is int)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    _require(type(commit) is _LinkMetadataCommit and commit.consumer is consumer
             and consumer.owner is owner and consumer.commit[0] is commit
             and consumer.consumption[0] is actual
             and commit.before is consumer.cursor is consumer.execution.cursor[0]
             and commit.cursor.predecessor is commit.before
             and commit.cursor.policy is consumer.execution.policy
             and type(commit.site) is int and type(commit.sequence) is int
             and commit.cursor.position == commit.before.position + 1
             and commit.site == commit.before.position
             and commit.sequence == len(consumer.execution.history)
             and type(commit.identity) is tuple and len(commit.identity) in (5, 9)
             and all(type(value) is int for value in commit.identity)
             and commit.identity == actual.snapshot.identity[:len(commit.identity)])
    policy._cursor_tail(commit.cursor)
    execution = consumer.execution
    if execution.baseline is not None:
        if len(commit.identity) == 9:
            expected = execution.baseline[0]
        else:
            action = consumer.operation.resource.site
            index = (action[1] if action[0] == 4
                     else 0 if action[2] is None else action[2] + 1)
            _require(type(index) is int and 0 <= index < len(execution.baseline[1]))
            expected = execution.baseline[1][index][1]
        _require(commit.identity == expected)
    before, after = commit.before, commit.cursor
    count = len(consumer.execution.policy.components) - 1
    first_leaf = 2 * count
    second_leaf = first_leaf + 1 + (consumer.execution.policy.hop is not None
                                   and consumer.execution.policy.phase != 'recheck')
    _require(after.link_length is before.link_length)
    if before.position < first_leaf:
        _require(len(commit.identity) == 5
                 and len(after.directories) == len(before.directories) + 1
                 and all(a is b for a, b in zip(after.directories[:-1], before.directories,
                                                strict=True))
                 and after.directories[-1] is commit.identity and after.leaf is before.leaf)
    else:
        _require(after.directories is before.directories)
        if before.position == first_leaf:
            _require(len(commit.identity) == 9 and before.leaf is None
                     and after.leaf is commit.identity)
        else:
            _require(after.leaf is before.leaf)
            if before.position == second_leaf:
                _require(len(commit.identity) == 9 and commit.identity == before.leaf)
            else:
                action = consumer.operation.resource.site
                index = (action[1] if action[0] == 4
                         else 0 if action[2] is None else action[2] + 1)
                _require(type(index) is int and 0 <= index < len(before.directories)
                         and len(commit.identity) == 5
                         and commit.identity == before.directories[index])
    return commit


def _publish_shared_ack(owner, consumer, commit):
    _lifetime_tail(owner, consumer)
    execution = consumer.execution
    _require(type(commit) is _LinkMetadataCommit and commit.consumer is consumer
             and consumer.commit[0] is consumer.operation.result.acknowledged[0] is commit
             and consumer.consumption[0] is commit
             and execution.pending[0] is consumer and execution.cursor[0] is commit.before
             and commit.cursor.predecessor is commit.before
             and commit.sequence == len(execution.history))
    execution.history.append(commit)
    execution.cursor[0] = commit.cursor
    execution.pending[0] = None


def _acked_shared_history(owner, consumer, commit):
    _require(type(consumer) is _LinkMetadataConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and consumer.owner is owner
             and type(commit) is _LinkMetadataCommit and commit.consumer is consumer)
    execution, operation = consumer.execution, consumer.operation
    _engine_origin_tail(execution.origin)
    _execution_mirrors(execution)
    ledger, phase = operation.ledger, operation.phase
    _require(type(commit.sequence) is int and 0 <= commit.sequence < len(execution.history)
             and execution.history[commit.sequence] is commit
             and execution.pending[0] is None and consumer.commit[0] is commit
             and operation.result.acknowledged[0] is commit
             and operation.result.attempt[0] is operation
             and operation.result.consumer[0] is consumer
             and type(operation.index) is int and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and ledger.counts is operation.budget[0]
             and ledger.counts[0] >= operation.budget[3]
             and ledger.failed[0] is False and ledger.failure[0] is None
             and phase.current[0] in (phase.idle, phase.active, phase.pending))
    # Historical DATA can survive later work. This function cannot admit it.
    _native_work_registration_tail(owner, execution.registration)
    return commit


def _resource_bindings(execution, resource):
    """Repeat exact argument/descriptor joins after callback-bearing guards."""
    _require(type(execution) is _LinkExecution
             and type(resource) in (_NativeLinkMetadataResource, _NativeLinkBytesResource))
    definitions, cursors, opened = (tuple.__getitem__(execution, 5),
                                    tuple.__getitem__(execution, 9),
                                    tuple.__getitem__(execution, 12))
    site, ordinal, arguments, descriptor = (tuple.__getitem__(resource, 3),
        tuple.__getitem__(resource, 4), tuple.__getitem__(resource, 5),
        tuple.__getitem__(resource, 6))
    _require(tuple.__getitem__(resource, 2) is execution
             and tuple.__getitem__(resource, 1) is tuple.__getitem__(execution, 1)
             and type(definitions) is tuple and type(ordinal) is int
             and 0 <= ordinal < len(definitions) and definitions[ordinal] is site
             and type(cursors) is list and len(cursors) == 1
             and type(cursors[0]) is policy._LinkPathCursor
             and type(tuple.__getitem__(cursors[0], 1)) is int
             and tuple.__getitem__(cursors[0], 1) == ordinal
             and type(opened) is list and type(arguments) is tuple
             and type(site) is tuple and len(site) == 3 and type(site[0]) is int)
    operation, name, parent = site
    if operation == 4:
        _require(type(resource) is _NativeLinkMetadataResource
                 and type(name) is int and 0 <= name < len(opened)
                 and parent is None and descriptor is opened[name]
                 and type(descriptor) is _NativeOpenedDescriptor
                 and len(arguments) == 1
                 and arguments[0] is tuple.__getitem__(descriptor, 1))
    elif operation == 3:
        _require(type(resource) is _NativeLinkMetadataResource and type(name) is str
                 and len(arguments) == 2 and arguments[0] is name)
        if parent is None:
            _require(name == '/' and descriptor is arguments[1] is None)
        else:
            _require(type(parent) is int and 0 <= parent < len(opened)
                     and descriptor is opened[parent] and type(descriptor) is _NativeOpenedDescriptor
                     and arguments[1] is tuple.__getitem__(descriptor, 1))
    else:
        _require(operation == 5 and type(resource) is _NativeLinkBytesResource
                 and type(name) is str and type(parent) is int
                 and 0 <= parent < len(opened) and descriptor is opened[parent]
                 and type(descriptor) is _NativeOpenedDescriptor and len(arguments) == 2
                 and type(arguments[0]) is bytes
                 and arguments[1] is tuple.__getitem__(descriptor, 1))
        selected = tuple.__getitem__(execution, 4)
        _require(type(selected) is policy._LinkPathPolicy)
        components = tuple.__getitem__(selected, 7)
        _require(type(components) is tuple and len(components) >= 2
                 and name is components[-1] and parent == len(components) - 2)
        blueprint = tuple.__getitem__(execution, 2)
        _require(type(blueprint) is policy._LinkScopeBlueprint)
        origin = tuple.__getitem__(blueprint, 4)
        encoded = tuple.__getitem__(resource, 8)
        _require(type(origin) is tuple and len(origin) == 5
                 and type(origin[4]) is tuple and len(origin[4]) >= 11
                 and type(origin[0]) is tuple and len(origin[0]) >= 4
                 and type(encoded) is origin[4][10][0]
                 and tuple.__getitem__(encoded, 0) is origin
                 and tuple.__getitem__(encoded, 1) is name
                 and tuple.__getitem__(encoded, 2) is arguments[0]
                 and tuple.__getitem__(encoded, 3) is origin[0][3])
    return resource


def _byte_record_tail(execution, resource):
    """Live owned byte-record/count joins; no missing-result interpretation."""
    _require(type(execution) is _LinkExecution and type(resource) is _NativeLinkBytesResource
             and resource.execution is execution and execution.policy.hop is not None
             and execution.policy.phase in ('before', 'after')
             and type(resource.record) is _LinkRead)
    source = execution.blueprint.runtime
    index = execution.policy.index
    phase = 0 if execution.policy.phase == 'before' else 1
    position = phase * len(source.link.hops) + index
    record = resource.record
    names = vars(record)
    _require(type(names) is dict and all(type(k) is str for k in names)
             and type(source.reads) is list and len(source.reads) == position + 1
             and source.reads[position] is record and names.get('hop') is execution.policy.hop
             and type(names.get('phase')) is int and names['phase'] == phase
             and type(names.get('index')) is int and names['index'] == position
             and names.get('data') is None and names.get('unknown') is False
             and names.get('acknowledgement') is None
             and type(names.get('attempted')) is bool and type(names.get('returned')) is bool)
    result = names.get('native_result')
    if result is None:
        _require(names['attempted'] is False and names['returned'] is False
                 and names.get('length') is names.get('after') is None
                 and names.get('before') is execution.count[0])
        return record
    _require(type(result) is metadata._LinkBytesResult and result.record is record
             and result.record_names is names and names.get('before') is result.before_count
             and type(result.attempt) is list and len(result.attempt) == 1
             and type(result.attempt[0]) is metadata._LinkBytesOperation
             and result.attempt[0].resource is resource)
    if names['returned'] is False:
        _require(result.length[0] is result.counted[0] is None
                 and names.get('length') is names.get('after') is None
                 and execution.count[0] is result.before_count)
    else:
        after = result.counted[0]
        _require(names['attempted'] is True and type(result.length[0]) is int
                 and names.get('length') is result.length[0]
                 and type(after) is tuple and len(after) == 3
                 and names.get('after') is after is execution.count[0]
                 and after[0] is execution.owner and after[1] is execution.registration.scope
                 and type(after[2]) is int and after[2] == result.before_count[2] + result.length[0])
    return record


def _make_shared_bytes_commit(owner, consumer, actual):
    _require(type(consumer) is _LinkBytesConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    execution, before = consumer.execution, consumer.cursor
    _require(execution.owner is owner and type(before) is policy._LinkPathCursor
             and execution.cursor[0] is before and type(actual) is metadata._LinkBytesReturn
             and type(actual.raw) is bytes and 0 < len(actual.raw) < execution.policy.bound
             and actual.raw == execution.policy.hop.target
             and actual.counted is actual.result.counted[0])
    following = policy._advance(before, 'returned', actual.raw)
    values = (consumer, len(execution.history), before.position, before, following,
              actual.result.length[0], actual.result.before_count, actual.counted,
              actual.result.record)
    kind, _, _, constructor, _, _, _, _, _ = execution.origin[1][5]
    commit = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(commit) is _LinkBytesCommit
             and all(tuple.__getitem__(commit, i) is value for i, value in enumerate(values))
             and execution.cursor[0] is before)
    return commit


def _commit_shared_bytes_tail(owner, consumer, actual, commit):
    _require(type(consumer) is _LinkBytesConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and type(commit) is _LinkBytesCommit
             and type(tuple.__getitem__(commit, 3)) is policy._LinkPathCursor
             and type(tuple.__getitem__(commit, 4)) is policy._LinkPathCursor)
    before, following = tuple.__getitem__(commit, 3), tuple.__getitem__(commit, 4)
    _require(type(tuple.__getitem__(before, 1)) is int
             and type(tuple.__getitem__(following, 1)) is int)
    metadata._pending_directory_cohort_tail(owner, consumer, actual)
    execution, result = consumer.execution, actual.result
    _require(execution.owner is owner and commit.consumer is consumer
             and consumer.commit[0] is commit and consumer.consumption[0] is actual
             and commit.before is consumer.cursor is execution.cursor[0]
             and type(commit.sequence) is int and commit.sequence == len(execution.history)
             and type(commit.site) is int and commit.site == before.position
             and execution.definitions[commit.site][0] == 5
             and execution.policy.hop is not None and execution.policy.phase != 'recheck'
             and type(actual.raw) is bytes and 0 < len(actual.raw) < execution.policy.bound
             and actual.raw == execution.policy.hop.target
             and type(commit.length) is int and commit.length == len(actual.raw)
             and commit.length is result.length[0]
             and commit.before_count is result.before_count
             and commit.after_count is actual.counted is result.counted[0]
             and commit.record is result.record
             and following.predecessor is before and following.policy is before.policy
             and following.position == before.position + 1
             and following.directories is before.directories and following.leaf is before.leaf
             and type(following.link_length) is int and following.link_length == commit.length)
    policy._cursor_tail(following)
    return commit


def _publish_shared_bytes_ack(owner, consumer, commit):
    _require(type(consumer) is _LinkBytesConsumer and type(commit) is _LinkBytesCommit)
    _lifetime_tail(owner, consumer)
    execution, result = consumer.execution, consumer.operation.result
    names = result.record_names
    _require(commit.consumer is consumer and execution.pending[0] is consumer
             and execution.cursor[0] is commit.before
             and consumer.commit[0] is result.acknowledged[0] is commit
             and consumer.consumption[0] is commit
             and commit.sequence == len(execution.history)
             and commit.after_count is execution.count[0]
             and names.get('native_result') is result and names.get('acknowledgement') is None)
    names['acknowledgement'] = commit
    execution.history.append(commit)
    execution.cursor[0] = commit.cursor
    execution.pending[0] = None


def _acked_shared_bytes_history(owner, consumer, commit):
    """Immediate raw-free ACK data; later path history needs its finish seal."""
    _require(type(consumer) is _LinkBytesConsumer
             and type(tuple.__getitem__(consumer, 0)) is _LinkExecution
             and type(commit) is _LinkBytesCommit)
    execution, operation = consumer.execution, consumer.operation
    _engine_origin_tail(execution.origin)
    _execution_mirrors(execution)
    _require(execution.owner is owner and commit.consumer is consumer
             and type(operation) is metadata._LinkBytesOperation
             and type(operation.result) is metadata._LinkBytesResult)
    result, ledger, phase = operation.result, operation.ledger, operation.phase
    names = result.record_names
    _require(type(commit.sequence) is int and 0 <= commit.sequence < len(execution.history)
             and execution.history[commit.sequence] is commit and execution.pending[0] is None
             and consumer.commit[0] is result.acknowledged[0] is commit
             and result.attempt[0] is operation and result.consumer[0] is consumer
             and commit.record is result.record and names.get('native_result') is result
             and names.get('acknowledgement') is commit and names.get('data') is None
             and names.get('returned') is True and names.get('unknown') is False
             and names.get('length') is commit.length is result.length[0]
             and names.get('before') is commit.before_count is result.before_count
             and names.get('after') is commit.after_count is result.counted[0]
             and type(operation.index) is int and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and ledger.counts is operation.budget[0] and ledger.counts[0] >= operation.budget[3]
             and ledger.failed[0] is False and ledger.failure[0] is None
             and phase.current[0] in (phase.idle, phase.active, phase.pending))
    _native_work_registration_tail(owner, execution.registration)
    return commit


def _effect_pin(origin, name):
    """Return an already retained dependency, never nominate a current export."""
    _engine_origin_tail(origin)
    _require(type(name) is str)
    rows = tuple(row for row in (*origin[2], *origin[3]) if row[0] == name)
    _require(len(rows) == 1)
    return rows[0][1]


def _new_execution(owner, registration, path, hop, phase, index, before_state,
                   start, observe):
    """Bind one fixed path to its original Scope before any new file effect."""
    _require(type(owner) is StartupArtifactOwner
             and type(registration) is _NativeScopeRegistration
             and type(phase) is int and phase in (0, 1)
             and type(index) is int and type(observe) is bool)
    scope = _native_walk_scope(owner, registration)
    blueprint = tuple.__getitem__(scope, 17)
    parent = tuple.__getitem__(registration.lineage, 4)
    _require(type(parent) is tuple and len(parent) == 5
             and type(blueprint) is parent[4][6][0]
             and blueprint.owner is owner and blueprint.lineage is registration.lineage
             and blueprint.origin is parent and blueprint.runtime is scope.runtime
             and vars(owner).get('_count_cell') is start
             and blueprint.runtime.count[0] is start
             and type(path) is str)
    # Lookup only: this provisional resource is never prepared or admitted.
    # The kernel authenticates the independent early parent before selecting
    # the engine; current module globals cannot create that parent authority.
    lookup = _NativeLinkMetadataResource(owner, registration, None, None, None, (), None)
    origin = metadata._closed_link_engine_origin(owner, lookup)
    _engine_origin_tail(origin)
    label = 'recheck' if not observe else 'before' if phase == 0 else 'after'
    logical_index = len(blueprint.link.hops) if hop is None else index
    rows = tuple(row for row in blueprint.rows
                 if row.phase == label and row.index == logical_index)
    _require(len(rows) == 1)
    selected = rows[0]
    _require(selected.path is path and selected.hop is hop
             and (observe or phase == 1))
    definitions = tuple(({'open': 0, 'fstat': 4, 'stat': 3, 'readlink': 5}[kind], name, parent)
                        for kind, name, parent in policy._sites(selected))
    cursor = policy._start(selected)
    ledger = registration.native_ledger
    _require(type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(v) is int for v in ledger.counts)
             and type(ledger.attempts) is list and ledger.inflight[0] is None
             and ledger.failed[0] is False and ledger.failure[0] is None)
    budget = (ledger.counts, ledger.counts[0], ledger.counts[1], tuple(ledger.attempts))
    fact = after_state = baseline = None
    if label != 'before':
        _require(type(before_state) is _LinkSnapshot
                 and blueprint.runtime.before[0] is before_state)
        snapshot = before_state
        if label == 'recheck':
            after_state = blueprint.runtime.after[0]
            fact = vars(owner).get('_fact_cell')
            _require(type(after_state) is _LinkSnapshot)
            snapshot = after_state
        baseline = snapshot.target if hop is None else snapshot.links[logical_index][1]
    values = (owner, registration, blueprint, origin, selected, definitions,
              before_state, baseline, [start], [cursor], [None], [], [], [False],
              [False], budget, fact, after_state, [], [], [])
    kind, _, _, constructor, _, _, _, _, _ = origin[1][0]
    execution = constructor(kind, *values)
    _engine_origin_tail(origin)
    _require(type(execution) is kind and tuple.__len__(execution) == len(values)
             and all(tuple.__getitem__(execution, i) is value for i, value in enumerate(values)))
    prior = vars(owner).get('_native_link_execution')
    _require(prior is None or (type(prior) is _LinkExecution and prior.finished[0] is True))
    vars(owner)['_native_link_execution'] = execution
    _execution_mirrors(execution)
    _native_work_registration_tail(owner, registration)
    _engine_origin_tail(origin)
    _execution_mirrors(execution)
    return execution


def _append_action(execution, site, before, after, evidence):
    """Retain the literal driver return; stored history cannot repair its loss."""
    _require(type(execution) is _LinkExecution and type(before) is policy._LinkPathCursor
             and type(after) is policy._LinkPathCursor
             and type(before.position) is int and type(after.position) is int
             and type(execution.actions) is list and type(execution.definitions) is tuple
             and type(execution.opened) is list and type(execution.history) is list
             and type(execution.cursor) is list and len(execution.cursor) == 1
             and type(site) is tuple and len(site) == 3 and type(site[0]) is int
             and 0 <= before.position < len(execution.definitions)
             and len(execution.actions) == before.position
             and execution.definitions[before.position] is site
             and after.predecessor is before and after.position == before.position + 1
             and before.policy is after.policy is execution.policy)
    if site[0] == 0:
        _require(type(evidence) is tuple and len(evidence) == 2
                 and type(evidence[0]) is _NativeOpenedDescriptor
                 and evidence[0].fd is evidence[1]
                 and execution.opened[-1] is evidence[0]
                 and execution.cursor[0] is before)
    else:
        _require(type(evidence) is (_LinkBytesCommit if site[0] == 5 else _LinkMetadataCommit)
                 and evidence.before is before and evidence.cursor is after
                 and execution.cursor[0] is after
                 and execution.history[-1] is evidence)
    values = (site, before, after, evidence)
    kind, _, _, constructor, _, _, _, _, _ = execution.origin[1][11]
    action = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    _require(type(action) is kind and tuple.__len__(action) == len(values)
             and all(tuple.__getitem__(action, i) is value for i, value in enumerate(values))
             and len(execution.actions) == before.position
             and execution.cursor[0] is (before if site[0] == 0 else after))
    execution.actions.append(action)
    if site[0] == 0:
        execution.cursor[0] = after
    _execution_mirrors(execution)
    return action


def _finish_mirrors(execution, outcome, actions, history, closed, count, budget):
    """Closed original handoffs and budget, with no new native admission."""
    _require(type(execution) is _LinkExecution)
    _execution_mirrors(execution)
    ledger = execution.registration.native_ledger
    scope = execution.registration.scope
    active = vars(scope.activation)
    runtime = execution.blueprint.runtime
    entry = vars(runtime.entry)
    _require(active.get('_scope') is scope.activation_scope
             and active.get('_ready') is True and active.get('_retired') is False
             and active.get('_uncertain') is False
             and active.get('_artifact_owner') is execution.owner
             and active.get('_artifact_cell') is execution.registration.root
             and entry.get('_failed') is False and entry.get('_unknown') is False
             and entry.get('_inputs') is runtime.inputs
             and entry.get('_root_cell') is runtime.cell)
    _require(type(outcome) is tuple and len(outcome) == 3
             and type(actions) is tuple and type(history) is tuple and type(closed) is tuple
             and len(actions) == len(execution.definitions) == execution.cursor[0].position
             and len(execution.actions) == len(actions)
             and all(a is b for a, b in zip(actions, execution.actions, strict=True))
             and len(execution.history) == len(history)
             and all(a is b for a, b in zip(history, execution.history, strict=True))
             and len(closed) == len(execution.closed) == len(execution.opened)
             and all(a is b for a, b in zip(closed, execution.closed, strict=True))
             and execution.pending[0] is None and execution.count[0] is count
             and execution.budget is budget and ledger.counts is budget[0]
             and ledger.counts[0] == budget[1] + len(actions) + len(closed)
             and ledger.counts[1] == budget[2]
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and ledger.failure[0] is None and ledger.phase.current[0] is ledger.phase.idle
             and ledger.phase.result[0] is None)
    actual_attempts = []
    prior = None
    sequence = 0
    initial_count = count
    byte_delta = 0
    for ordinal, action in enumerate(actions):
        _require(type(action) is _LinkAction and action.site is execution.definitions[ordinal]
                 and type(action.before) is policy._LinkPathCursor
                 and type(action.after) is policy._LinkPathCursor
                 and type(action.before.position) is type(action.after.position) is int
                 and action.before.position == ordinal and action.after.position == ordinal + 1
                 and action.after.predecessor is action.before
                 and (prior is None or action.before is prior)
                 and action.before.policy is action.after.policy is execution.policy)
        prior = action.after
        if action.site[0] == 0:
            returned = action.evidence
            _require(type(returned) is tuple and len(returned) == 2
                     and type(returned[0]) is _NativeOpenedDescriptor
                     and returned[0].fd is returned[1])
            actual_attempts.append(returned[0].allocation)
        else:
            commit = action.evidence
            _require(type(commit) is (_LinkBytesCommit if action.site[0] == 5 else _LinkMetadataCommit)
                     and sequence < len(history) and history[sequence] is commit
                     and commit.sequence == sequence and commit.site == ordinal
                     and commit.before is action.before and commit.cursor is action.after)
            consumer = commit.consumer
            _require(type(consumer) is (_LinkBytesConsumer if action.site[0] == 5
                                       else _LinkMetadataConsumer))
            operation = consumer.operation
            _require(type(operation) is (metadata._LinkBytesOperation if action.site[0] == 5
                                        else metadata._MetadataOperation)
                     and type(operation.result) is (metadata._LinkBytesResult if action.site[0] == 5
                                                     else metadata._MetadataResult)
                     and type(operation.resource) is (_NativeLinkBytesResource if action.site[0] == 5
                                                      else _NativeLinkMetadataResource)
                     and all(type(cell) is list and len(cell) == 1 for cell in
                             (consumer.commit, operation.result.acknowledged,
                              operation.result.attempt, operation.result.consumer)))
            _require(consumer.execution is execution and consumer.commit[0] is commit
                     and operation.result.acknowledged[0] is commit
                     and operation.result.attempt[0] is operation
                     and operation.result.consumer[0] is consumer
                     and operation.resource.site is action.site
                     and operation.resource.execution is execution
                     and consumer.predecessor is (None if sequence == 0 else history[sequence - 1]))
            _require(type(consumer.custody) is tuple and len(consumer.custody) == 6
                     and type(operation.state) is list and len(operation.state) == 3
                     and operation.state[0] is operation.state[1] is True
                     and operation.state[2] is False
                     and type(operation.ended) is list and len(operation.ended) == 1
                     and operation.ended[0] is True)
            payload_origin, marker, link, slot, state, reference = consumer.custody
            result = operation.result
            _require(type(payload_origin) is metadata._PayloadOrigin
                     and type(marker) is payload_origin.marker_type
                     and marker.owner is execution.owner and marker.operation is operation
                     and marker.consumer is None and marker.origin is payload_origin
                     and result.custody_origin is payload_origin
                     and type(link) is list and len(link) == 1 and link[0] is None
                     and result.custody_link is marker.owner_link is link
                     and type(slot) is list and len(slot) == 1 and slot[0] is marker
                     and result.custody_slot is marker.marker_slot is slot
                     and marker.state is state and type(state) is list and len(state) == 3
                     and state[0] is state[1] is True and state[2] is False
                     and marker.reference is reference
                     and type(reference) is payload_origin.reference_type)
            actual_attempts.append(operation)
            if action.site[0] == 5:
                _require(type(commit.length) is int and commit.length > 0
                         and commit.record.acknowledgement is commit
                         and commit.record.data is None and commit.record.unknown is False
                         and commit.record.length is commit.length
                         and commit.after_count is count
                         and commit.before_count[2] + commit.length == count[2])
                initial_count, byte_delta = commit.before_count, commit.length
            sequence += 1
    _require(prior is execution.cursor[0] and sequence == len(history)
             and type(outcome[0]) is tuple and outcome[0] is prior.leaf
             and type(outcome[1]) is tuple and len(outcome[1]) == len(prior.directories)
             and outcome[2] is prior.link_length)
    for index, row in enumerate(outcome[1]):
        _require(type(row) is tuple and len(row) == 2
                 and row[0] is execution.policy.components[index]
                 and row[1] is prior.directories[index])
    if execution.baseline is not None:
        _require(outcome[:2] == execution.baseline)
    expected_delta = (0 if execution.policy.hop is None or execution.policy.phase == 'recheck'
                      else len(execution.policy.hop.target))
    _require(byte_delta == expected_delta and count[2] == initial_count[2] + byte_delta
             and len(ledger.attempts) == len(budget[3]) + len(actual_attempts)
             and all(ledger.attempts[i] is row for i, row in enumerate(budget[3]))
             and all(ledger.attempts[len(budget[3]) + i] is row
                     for i, row in enumerate(actual_attempts)))
    for descriptor, receipt in zip(reversed(execution.opened), closed, strict=True):
        close = descriptor.close
        _require(_native_descriptor_closed(descriptor, ledger)
                 and type(receipt) is tuple and len(receipt) == 3
                 and receipt[0] is close and receipt[1] is descriptor.fd and receipt[2] is None
                 and close.result[0] is receipt and close.state[0] is True
                 and close.state[1] is False and close.raw[0] is None)
    return execution


def _finish_path(execution):
    _require(type(execution) is _LinkExecution and execution.finished[0] is False)
    _engine_origin_tail(execution.origin)
    outcome = policy._outcome(execution.cursor[0])
    actions, history, closed = tuple(execution.actions), tuple(execution.history), tuple(execution.closed)
    count, budget = execution.count[0], execution.budget
    _finish_mirrors(execution, outcome, actions, history, closed, count, budget)
    origin_check = _effect_pin(execution.origin, '_origin_tail')
    for commit in history:
        payload_origin, _, _, _, _, reference = commit.consumer.custody
        origin_check(payload_origin)
        _require(payload_origin.reference_callback.__get__(reference, payload_origin.reference_type) is None
                 and payload_origin.reference_call(reference) is None)
    _native_work_registration_tail(execution.owner, execution.registration)
    _runtime_current(execution.blueprint.runtime, execution.owner)
    _engine_origin_tail(execution.origin)
    _finish_mirrors(execution, outcome, actions, history, closed, count, budget)
    values = (execution, outcome, actions, history, closed, count, budget)
    kind, _, _, constructor, _, _, _, _, _ = execution.origin[1][12]
    finish = constructor(kind, *values)
    _engine_origin_tail(execution.origin)
    for commit in history:
        payload_origin, _, _, _, _, reference = commit.consumer.custody
        origin_check(payload_origin)
        _require(payload_origin.reference_callback.__get__(reference, payload_origin.reference_type) is None
                 and payload_origin.reference_call(reference) is None)
    # Constructor and weak observations can retire/change a parent. Revisit
    # the full current Scope/runtime authority after them, then repeat the
    # pure finish mirrors; the earlier check is not a reusable grant.
    _require(_native_walk_scope(execution.owner, execution.registration)
             is execution.registration.scope)
    _runtime_current(execution.blueprint.runtime, execution.owner)
    _engine_origin_tail(execution.origin)
    _finish_mirrors(execution, outcome, actions, history, closed, count, budget)
    _require(type(finish) is kind and tuple.__len__(finish) == len(values)
             and all(tuple.__getitem__(finish, i) is value for i, value in enumerate(values)))
    execution.finished[0] = True
    return finish


def _drive_native_path(owner, registration, path, hop, phase, index, before_state,
                       start, observe=True):
    """Fixed traversal using the shared producer, with independent close custody.

    This remains unreachable from the legacy caller until the early-origin and
    snapshot publication integration is complete. It never serves file bytes.
    """
    execution = _new_execution(owner, registration, path, hop, phase, index,
                               before_state, start, observe)
    origin = execution.origin
    open_call = _effect_pin(origin, '_open_shared')
    prepare_open = _effect_pin(origin, '_prepare_open_shared')
    close_call = _effect_pin(origin, '_close_known_shared')
    run = _effect_pin(origin, '_run_directory_observation')
    append = _effect_pin(origin, '_append_action')
    finish_call = _effect_pin(origin, '_finish_path')
    # Literal pre-C allocations survive lost open/constructor returns. These
    # are cleanup evidence only; no receipt is reconstructed from a mutable
    # holder, current descriptor registry or ledger.
    custody = []
    predecessor = None
    failed = False
    try:
        for ordinal, site in enumerate(execution.definitions):
            _engine_origin_tail(origin)
            _execution_mirrors(execution)
            _require(len(execution.actions) == ordinal
                     and execution.cursor[0].position == ordinal)
            before = execution.cursor[0]
            opcode, name, parent_index = site
            parent = None if parent_index is None else execution.opened[parent_index]
            fd = None if parent is None else parent.fd
            if opcode == 0:
                allocation = prepare_open(owner, registration, name, fd)
                _require(type(allocation) is _NativeOpenAllocation
                         and allocation.owner is owner and allocation.registration is registration)
                claim = (allocation, allocation.raw)
                custody.append(claim)
                execution.open_custody.append(claim)
                _engine_origin_tail(origin)
                returned = open_call(owner, name, fd, True, registration, allocation)
                _require(type(returned) is tuple and len(returned) == 2
                         and type(returned[0]) is _NativeOpenedDescriptor
                         and type(returned[1]) is int and returned[0].fd is returned[1]
                         and allocation is returned[0].allocation
                         and claim[1] is returned[0].allocation.raw)
                execution.opened.append(returned[0])
                after = policy._advance(before, 'opened')
                append(execution, site, before, after, returned)
                returned = None
                continue
            record = encoded = None
            if opcode == 4:
                parent = execution.opened[name]
                arguments = (parent.fd,)
            elif opcode == 3:
                arguments = (name, fd)
            else:
                _require(opcode == 5 and execution.policy.hop is not None)
                parent_origin = execution.blueprint.origin
                encoding_row = parent_origin[2][6]
                _require(encoding_row[0] == 'encode_basename')
                metadata._link_function_pin(encoding_row, encoding_row[3], 'encode_basename')
                encoded = encoding_row[1](parent_origin, name)
                _engine_origin_tail(origin)
                _require(type(encoded) is parent_origin[4][10][0]
                         and encoded[0] is parent_origin and encoded[1] is name
                         and type(encoded[2]) is bytes)
                arguments = (encoded[2], fd)
                position = phase * len(execution.blueprint.link.hops) + index
                kind, _, _, constructor, _, _, _, _, _ = origin[1][10]
                record = constructor(kind, hop, phase, position, execution.count[0])
                _engine_origin_tail(origin)
                _require(type(record) is kind and record.hop is hop
                         and record.phase is phase and record.index is position
                         and record.before is execution.count[0]
                         and len(execution.blueprint.runtime.reads) == position)
                execution.blueprint.runtime.reads.append(record)
            values = (owner, registration, execution, site, ordinal, arguments, parent)
            resource_index = 3 if opcode != 5 else 6
            if opcode == 5:
                values = (*values, record, encoded)
            kind, _, _, constructor, _, _, _, _, _ = origin[1][resource_index]
            resource = constructor(kind, *values)
            _engine_origin_tail(origin)
            _require(type(resource) is kind and tuple.__len__(resource) == len(values)
                     and all(tuple.__getitem__(resource, i) is value for i, value in enumerate(values)))
            commit = run(owner, resource, predecessor)
            _require(type(commit) is (_LinkBytesCommit if opcode == 5 else _LinkMetadataCommit)
                     and commit.consumer.operation.resource is resource
                     and commit.before is before)
            append(execution, site, before, commit.cursor, commit)
            predecessor = commit
    except BaseException:
        failed = True
    finally:
        # Cleanup consumes only original reserved close authority. Never replay
        # an attempted close, including an ambiguous/lost close return.
        for claim in reversed(custody):
            try:
                _require(type(claim) is tuple and len(claim) == 2
                         and type(claim[0]) is _NativeOpenAllocation
                         and type(claim[1]) is list and len(claim[1]) == 1
                         and claim[0].raw is claim[1])
                allocation, raw = claim
                if allocation.close.state[0] is True:
                    failed = True
                    continue
                if type(raw[0]) is not int:
                    _require(raw[0] is None)
                    continue
                receipt = close_call(owner, allocation, raw[0], registration.native_ledger)
                _require(type(receipt) is tuple and len(receipt) == 3
                         and receipt[0] is allocation.close and receipt[1] is raw[0]
                         and receipt[2] is None and allocation.close.result[0] is receipt)
                execution.closed.append(receipt)
            except BaseException:
                failed = True
        if failed:
            execution.failed[0] = True
            vars(owner)['_unknown'] = True
    if failed:
        raise ArtifactObservationError(owner) from None
    try:
        finish = finish_call(execution)
        _require(type(finish) is _LinkPathFinish and finish.execution is execution)
        return finish
    except BaseException:
        execution.failed[0] = True
        vars(owner)['_unknown'] = True
    # Raising outside the handler avoids retaining a foreign exception (and
    # its traceback/data) as __context__ on this public refusal.
    finish = None
    raise ArtifactObservationError(owner) from None
