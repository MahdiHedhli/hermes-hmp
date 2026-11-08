"""Unwired original metadata intent/result preparation; no syscall dispatcher."""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from .presentation_startup_artifacts import (
    ArtifactObservationError,
    StartupArtifactOwner,
    _native_actor_context,
    _native_declared_metadata_cohort_tail,
    _native_declared_metadata_plan_tail,
    _native_metadata_component_tail,
    _native_metadata_snapshot,
    _native_post_actor_state,
    _native_pre_actor_state,
    _native_read_lifecycle_tail,
    _native_work_origin_tail,
    _NativeActorMismatchError,
    _NativeMetadataResource,
    _NativeMetadataSnapshot,
    _NativeScopeRegistration,
    _prepare_native_metadata_resource,
    _require,
    _Scope,
)


class _MetadataResult(NamedTuple):
    attempt: list
    consumer: list
    unset: object
    raw: list
    category: list
    snapshot: list
    acknowledged: list
    envelope: list

    def __repr__(self):
        return '<MetadataResult unqualified original DATA redacted>'


class _MetadataOperation(NamedTuple):
    owner: object
    resource: _NativeMetadataResource
    registration: object
    ledger: object
    phase: object
    native: object
    context: tuple
    operation: int
    callee: object
    arguments: tuple
    index: int
    attempts: list
    budget: tuple
    result: _MetadataResult
    state: list
    ended: list

    def __repr__(self):
        return '<MetadataOperation unqualified original intent redacted>'


def _resource_tail(owner, resource):
    """Rejoin the held actual resource; never adopt a current replacement."""
    _require(type(resource) is _NativeMetadataResource and resource.owner is owner
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and resource.site[0] in (3, 4)
             and type(resource.arguments) is tuple
             and len(resource.arguments) == (2 if resource.site[0] == 3 else 1))
    metadata = _native_declared_metadata_plan_tail(owner, resource.registration,
                                                  resource.held_walk)
    _require(metadata is resource.metadata and metadata.progress[0] is resource.ordinal
             and metadata.definitions[resource.ordinal] is resource.site)
    actual = _prepare_native_metadata_resource(
        owner, resource.registration, resource.held_walk, resource.descriptor,
        resource.arguments[0] if resource.site[0] == 3 else None)
    _require(actual.metadata is resource.metadata and actual.site is resource.site
             and actual.ordinal is resource.ordinal and actual.descriptor is resource.descriptor
             and all(before is after for before, after in
                     zip(resource.arguments, actual.arguments, strict=True)))
    return resource


def _prepare_metadata_operation(owner, resource):
    """Preallocate original result cells and fixed call DATA without a debit.

    The future fixed producer must retain this actual allocation across admission,
    bind its independently held one-use policy consumer, and recheck every budget,
    resource and phase join before effects. This preparation is not admission.
    """
    _resource_tail(owner, resource)
    registration = resource.registration
    native, ledger, phase = (registration.native_origin, registration.native_ledger,
                             registration.native_phase)
    _native_work_origin_tail(owner, registration, native)
    _require(ledger.phase is phase and type(phase.current) is list
             and len(phase.current) == 1 and phase.current[0] is phase.idle
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is None and type(ledger.inflight) is list
             and len(ledger.inflight) == 1 and ledger.inflight[0] is None
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False)
    attempts, counts = ledger.attempts, ledger.counts
    _require(type(attempts) is list and len(attempts) < 1048576
             and type(counts) is list and len(counts) == 2
             and all(type(value) is int for value in counts)
             and 0 <= counts[0] < 1048576
             and 0 <= counts[1] < 1048576 - counts[0])
    used, reserved, index = counts[0], counts[1], len(attempts)
    operation = resource.site[0]
    callee = native.operations[operation]
    unset = object()
    result = _MetadataResult([None], [None], unset, [unset], [None], [None], [None], [None])
    intent = _MetadataOperation(owner, resource, registration, ledger, phase, native,
                                registration.context, operation, callee, resource.arguments,
                                index, attempts, (counts, used, reserved, used + 1), result,
                                [False, False, False], [False])
    result.attempt[0] = intent
    _require(_resource_tail(owner, resource) is resource
             and ledger.attempts is attempts and len(attempts) == index
             and ledger.counts is counts and counts[0] is used and counts[1] is reserved
             and phase.current[0] is phase.idle and phase.result[0] is None
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and native.operations[operation] is callee)
    return intent


class _DirectoryConsumer(NamedTuple):
    """Fixed source/cache directory policy preparation; not an ACK."""
    owner: object
    operation: _MetadataOperation
    resource: _NativeMetadataResource
    parents: tuple
    owner_type: type
    class_name: str
    module_name: str
    material: object
    material_code: object
    material_module: ModuleType
    file_function: object
    file_code: object
    file_module: ModuleType
    file_owner_type: type
    consumption: list
    commit: list

    def __repr__(self):
        return '<DirectoryConsumer unqualified fixed policy redacted>'


def _directory_material_tail(owner, consumer):
    """Import-free original material closure, including constructor-return drift."""
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(consumer.owner_type) is type and type(owner) is consumer.owner_type
             and type(consumer.operation) is _MetadataOperation
             and type(consumer.resource) is _NativeMetadataResource
             and consumer.resource is consumer.operation.resource
             and type(consumer.resource.registration) is _NativeScopeRegistration
             and type(consumer.resource.registration.scope) is _Scope)
    scope = consumer.resource.registration.scope
    origin = scope.material_origin
    _require(type(origin) is tuple and len(origin) == 6
             and origin[0] is consumer.material and origin[1] is consumer.material_code
             and origin[3] is consumer.owner_type and origin[4] is consumer.file_function
             and origin[5] is consumer.file_code
             and type(consumer.material) is FunctionType
             and consumer.material.__code__ is consumer.material_code
             and type(consumer.file_function) is FunctionType
             and consumer.file_function.__code__ is consumer.file_code
             and type(consumer.material_module) is ModuleType
             and consumer.material.__globals__ is vars(consumer.material_module)
             and origin[2] is vars(consumer.material_module)
             and type(consumer.file_module) is ModuleType
             and consumer.file_function.__globals__ is vars(consumer.file_module)
             and type(consumer.file_owner_type) is type
             and consumer.file_owner_type is StartupArtifactOwner
             and vars(consumer.file_owner_type).get('_file') is consumer.file_function
             and vars(consumer.file_module).get('StartupArtifactOwner') is consumer.file_owner_type
             and vars(consumer.owner_type).get('_material_guard') is consumer.material
             and type(consumer.class_name) is str and type(consumer.module_name) is str
             and (consumer.class_name, consumer.module_name) in (
                 ('RuntimeSourceReadOwner', 'hmp_startup.runtime_reader'),
                 ('DeclaredCacheReadOwner', 'hmp_startup.cache_reader'))
             and type(consumer.owner_type.__name__) is str
             and consumer.owner_type.__name__ == consumer.class_name
             and type(consumer.owner_type.__module__) is str
             and consumer.owner_type.__module__ == consumer.module_name
             and vars(consumer.material_module).get(consumer.class_name) is consumer.owner_type
             and type(vars(consumer.material_module).get('__name__')) is str
             and vars(consumer.material_module).get('__name__') == consumer.module_name
             and type(vars(consumer.file_module).get('__name__')) is str
             and vars(consumer.file_module).get('__name__') ==
             'hmp_plugin.presentation_startup_artifacts'
             and type(sys.modules) is dict
             and sys.modules.get(consumer.module_name) is consumer.material_module
             and sys.modules.get('hmp_plugin.presentation_startup_artifacts')
             is consumer.file_module)
    return consumer


def _unspent_directory_cells_tail(owner, operation):
    """Untouched original intent cells only; caller proves resource/consumer joins."""
    _require(type(operation) is _MetadataOperation and operation.owner is owner
             and type(operation.result) is _MetadataResult
             and type(operation.operation) is int and operation.operation == 4)
    resource, result = operation.resource, operation.result
    _require(type(resource) is _NativeMetadataResource
             and type(resource.registration) is _NativeScopeRegistration)
    registration = resource.registration
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(operation.registration is registration and operation.ledger is ledger
             and ledger.phase is phase
             and operation.phase is phase and operation.native is registration.native_origin
             and operation.context is registration.context
             and operation.callee is operation.native.operations[4]
             and operation.arguments is resource.arguments
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and type(ledger.counts[0]) is int and type(ledger.counts[1]) is int
             and ledger.counts[0] is operation.budget[1]
             and ledger.counts[1] is operation.budget[2]
             and type(operation.budget[3]) is int
             and operation.budget[3] == ledger.counts[0] + 1
             and 0 <= ledger.counts[0] < 1048576
             and 0 <= ledger.counts[1] < 1048576 - ledger.counts[0]
             and type(operation.attempts) is list and ledger.attempts is operation.attempts
             and type(operation.index) is int and operation.index == len(operation.attempts)
             and type(operation.state) is list and len(operation.state) == 3
             and all(type(value) is bool and value is False for value in operation.state)
             and type(operation.ended) is list and len(operation.ended) == 1
             and operation.ended[0] is False
             and type(result.attempt) is list and len(result.attempt) == 1
             and result.attempt[0] is operation
             and type(result.raw) is list and len(result.raw) == 1
             and result.raw[0] is result.unset
             and all(type(cell) is list and len(cell) == 1 and cell[0] is None
                     for cell in (result.category, result.snapshot,
                                  result.acknowledged, result.envelope))
             and type(phase.current) is list and len(phase.current) == 1
             and type(phase.result) is list and len(phase.result) == 1
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False
             and type(ledger.failure) is list and len(ledger.failure) == 1
             and ledger.failure[0] is None)
    return result


def _unused_directory_cells_tail(owner, operation):
    """Unspent cells plus IDLE; not usable during admission preparation."""
    result = _unspent_directory_cells_tail(owner, operation)
    ledger, phase = operation.ledger, operation.phase
    _require(phase.current[0] is phase.idle and phase.result[0] is None
             and ledger.inflight[0] is None)
    return result


def _unused_directory_intent_tail(owner, operation):
    """Original unclaimed preparation input; no consumer can renew it."""
    _require(type(operation) is _MetadataOperation)
    _resource_tail(owner, operation.resource)
    result = _unused_directory_cells_tail(owner, operation)
    _require(type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is None)
    return result


def _prepare_directory_consumer(owner, operation):
    """Bind one actual unused intent to the fixed runtime/cache directory policy.

    Other owner/configuration/tree policies need their own reviewed consumers.
    Nothing here publishes ACTIVE, debits allowance or invokes native work.
    """
    _require(type(operation) is _MetadataOperation and operation.owner is owner
             and type(operation.operation) is int and operation.operation == 4
             and type(operation.result) is _MetadataResult)
    resource, result = operation.resource, operation.result
    _resource_tail(owner, resource)
    _require(resource.site[1] == 'directory'
             and operation.registration is resource.registration
             and type(operation.state) is list and len(operation.state) == 3
             and all(type(value) is bool and value is False for value in operation.state)
             and type(operation.ended) is list and len(operation.ended) == 1
             and operation.ended[0] is False
             and type(result.attempt) is list and len(result.attempt) == 1
             and result.attempt[0] is operation
             and type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is None and type(result.raw) is list
             and len(result.raw) == 1 and result.raw[0] is result.unset
             and all(type(cell) is list and len(cell) == 1 and cell[0] is None
                     for cell in (result.category, result.snapshot,
                                  result.acknowledged, result.envelope)))
    _require(_unused_directory_intent_tail(owner, operation) is result)
    scope = resource.registration.scope
    origin = scope.material_origin
    _require(type(origin) is tuple and len(origin) == 6 and type(origin[3]) is type
             and type(owner) is origin[3])
    # The scope's original class/namespace are retained authority. Registry
    # lookups below only rejoin them; they never nominate a replacement type.
    kind = origin[3]
    class_name = kind.__name__
    _require(type(class_name) is str)
    if class_name == 'RuntimeSourceReadOwner':
        module_name = 'hmp_startup.runtime_reader'
    else:
        _require(class_name == 'DeclaredCacheReadOwner')
        module_name = 'hmp_startup.cache_reader'
    _require(type(origin) is tuple and len(origin) == 6 and origin[3] is kind
             and type(origin[0]) is FunctionType and origin[0].__code__ is origin[1]
             and type(origin[4]) is FunctionType and origin[4].__code__ is origin[5]
             and type(sys.modules) is dict)
    module = sys.modules.get(module_name)
    file_module = sys.modules.get('hmp_plugin.presentation_startup_artifacts')
    _require(type(file_module) is ModuleType and origin[4].__globals__ is vars(file_module)
             and vars(StartupArtifactOwner).get('_file') is origin[4]
             and type(module) is ModuleType and vars(module).get(class_name) is kind
             and type(vars(module).get('__name__')) is str
             and vars(module).get('__name__') == module_name
             and type(kind.__module__) is str and kind.__module__ == module_name
             and origin[0].__globals__ is vars(module)
             and origin[2] is vars(module) and vars(kind).get('_material_guard') is origin[0]
             and type(scope.parent) is tuple and len(scope.parent) == 6
             and type(scope.parent[0]) is tuple and len(scope.parent[0]) == 3)
    root = scope.parent[0]
    parents = (scope.activation, scope.activation_scope, root, root[0], type(root[0]),
               root[2], type(root[2]))
    _native_read_lifecycle_tail(owner, resource.registration, parents)
    consumer = _DirectoryConsumer(owner, operation, resource, parents, kind,
                                   class_name, module_name, origin[0], origin[1], module,
                                   origin[4], origin[5], file_module, StartupArtifactOwner,
                                   [None], [None])
    _require(_resource_tail(owner, resource) is resource
             and operation.result is result and result.consumer[0] is None
             and result.attempt[0] is operation and result.raw[0] is result.unset)
    _native_read_lifecycle_tail(owner, resource.registration, parents)
    _require(_unused_directory_intent_tail(owner, operation) is result
             and _directory_material_tail(owner, consumer) is consumer)
    result.consumer[0] = consumer
    _require(_directory_material_tail(owner, consumer) is consumer
             and result.consumer[0] is consumer)
    return consumer


def _directory_identity(snapshot, actor_uid):
    """Fixed POSIX directory policy DATA; not a native result or an ACK.

    A future consumer must first prove this snapshot came from its held actual
    native return. Constructing a valid-looking snapshot supplies no work credit.
    """
    _require(type(snapshot) is _NativeMetadataSnapshot and type(actor_uid) is int
             and actor_uid >= 0 and type(snapshot.identity) is tuple
             and len(snapshot.identity) == 9
             and all(type(value) is int for value in snapshot.identity))
    identity = snapshot.identity
    mode, uid = identity[2], identity[3]
    # POSIX mode bits match the existing _file policy. Literal integer operations
    # avoid adding a mutable stat-module callback inside pending consumption.
    _require(mode & 0o170000 == 0o040000 and uid in (0, actor_uid)
             and not mode & 0o6000
             and (not mode & 0o022 or (uid == 0 and mode & 0o1000 != 0)))
    return identity[:5]


def _latched_directory_resource_tail(owner, consumer):
    """Original already-latched cohort DATA; not a phase check or work grant."""
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(consumer.operation) is _MetadataOperation
             and type(consumer.resource) is _NativeMetadataResource
             and consumer.operation.resource is consumer.resource)
    operation, resource = consumer.operation, consumer.resource
    registration = resource.registration
    metadata = _native_declared_metadata_cohort_tail(owner, registration, resource.held_walk)
    _require(metadata is resource.metadata and metadata.progress[0] is resource.ordinal
             and metadata.progress[1] is consumer
             and type(resource.ordinal) is int
             and metadata.definitions[resource.ordinal] is resource.site
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and resource.site[0] == 4
             and type(resource.site[1]) is str and resource.site[1] == 'directory'
             and type(resource.site[2]) is int
             and operation.owner is owner and operation.registration is registration
             and operation.ledger is registration.native_ledger
             and operation.phase is registration.native_phase
             and operation.native is registration.native_origin
             and operation.context is registration.context
             and type(operation.operation) is int and operation.operation == 4
             and operation.callee is operation.native.operations[4]
             and operation.arguments is resource.arguments
             and type(operation.result) is _MetadataResult
             and type(operation.result.attempt) is list and len(operation.result.attempt) == 1
             and operation.result.attempt[0] is operation
             and type(operation.result.consumer) is list and len(operation.result.consumer) == 1
             and operation.result.consumer[0] is consumer
             and type(resource.arguments) is tuple and len(resource.arguments) == 1)
    _native_metadata_component_tail(owner, registration, resource.held_walk[0],
                                    resource.descriptor, resource.site[2])
    _require(resource.arguments[0] is resource.descriptor.fd
             and _directory_material_tail(owner, consumer) is consumer)
    _native_read_lifecycle_tail(owner, registration, consumer.parents)
    _native_work_origin_tail(owner, registration, operation.native)
    _require(_directory_material_tail(owner, consumer) is consumer)
    return resource


def _charged_directory_operation_tail(owner, consumer):
    """Rejoin an already-debited directory intent; never admit work.

    The future producer must hold its original consumer across admission. A
    caller-built matching ledger row is not an independent native-call receipt.
    This function neither invokes the native callee nor changes any state.
    """
    _latched_directory_resource_tail(owner, consumer)
    operation = consumer.operation
    ledger, phase, result = operation.ledger, operation.phase, operation.result
    _require(type(operation.state) is list and len(operation.state) == 3
             and operation.state[0] is True and type(operation.state[1]) is bool
             and operation.state[2] is False
             and type(operation.ended) is list and len(operation.ended) == 1
             and type(operation.ended[0]) is bool
             and type(operation.attempts) is list
             and ledger.attempts is operation.attempts
             and type(operation.index) is int
             and 0 <= operation.index < len(operation.attempts)
             and operation.attempts[operation.index] is operation
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(value) is int for value in operation.budget[1:])
             and all(type(value) is int for value in ledger.counts)
             and operation.budget[3] == operation.budget[1] + 1
             and 0 <= operation.budget[1] < 1048576
             and 0 <= operation.budget[2] < 1048576 - operation.budget[1]
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False
             and type(phase.current) is list and len(phase.current) == 1
             and ledger.phase is phase
             and type(ledger.failure) is list and len(ledger.failure) == 1
             and ledger.failure[0] is None
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is operation
             and type(result.raw) is list and len(result.raw) == 1
             and all(type(cell) is list and len(cell) == 1
                     for cell in (result.category, result.snapshot,
                                  result.acknowledged, result.envelope))
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and consumer.commit[0] is None)
    return operation


def _active_directory_operation_tail(owner, consumer):
    """Original charged intent immediately before its fixed native call."""
    operation = _charged_directory_operation_tail(owner, consumer)
    result = operation.result
    _require(operation.state[1] is False and operation.ended[0] is False
             and operation.ledger.inflight[0] is operation
             and operation.phase.current[0] is operation.phase.active
             and result.raw[0] is result.unset
             and all(cell[0] is None for cell in (result.category, result.snapshot,
                                                result.acknowledged, result.envelope)))
    return operation


def _latch_directory_consumer(owner, consumer):
    """Bind the actual prepared consumer to its empty original metadata site.

    This is a one-use plan latch, not actor admission, debit, native work or ACK.
    If final closure refuses after publication, leave the original slot visible;
    never erase a foreign replacement or silently retry this publication.
    """
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(consumer.operation) is _MetadataOperation
             and consumer.operation.resource is consumer.resource)
    operation = consumer.operation
    resource = _resource_tail(owner, consumer.resource)
    result = _unused_directory_cells_tail(owner, operation)
    _require(operation.result is result
             and type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is consumer
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and consumer.commit[0] is None
             and _directory_material_tail(owner, consumer) is consumer)
    _native_read_lifecycle_tail(owner, resource.registration, consumer.parents)
    ledger = operation.ledger
    _require(type(ledger.failure) is list and len(ledger.failure) == 1
             and ledger.failure[0] is None
             and _resource_tail(owner, resource) is resource
             and _unused_directory_cells_tail(owner, operation) is result
             and result.consumer[0] is consumer
             and _directory_material_tail(owner, consumer) is consumer)
    resource.metadata.progress[1] = consumer
    _require(_latched_directory_resource_tail(owner, consumer) is resource
             and _unused_directory_cells_tail(owner, operation) is result
             and result.consumer[0] is consumer)
    return consumer


def _directory_admission_preparation_tail(owner, consumer, operation, token):
    """Original reserved preparation cohort after actor sampling; no new grant."""
    _require(type(operation) is _MetadataOperation
             and _latched_directory_resource_tail(owner, consumer) is operation.resource
             and consumer.operation is operation)
    result = _unspent_directory_cells_tail(owner, operation)
    ledger, phase = operation.ledger, operation.phase
    _require(type(token) is list and len(token) == 3
             and ledger.preparation is token
             and token[0] is owner and token[1] is operation.registration
             and token[2] is consumer
             and ledger.inflight[0] is token
             and phase.current[0] is phase.active and phase.result[0] is token
             and type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is consumer
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and consumer.commit[0] is None)
    return operation


def _admit_directory_operation(owner, consumer):
    """Admit exactly one fixed directory fstat intent; no native call or ACK.

    Wrong actor with unchanged inputs spends no work unit and ends this intent.
    Any drift or partial publication keeps sticky failure/debt; never refund,
    replay or erase a foreign slot. The caller must retain this actual return.
    """
    _latched_directory_resource_tail(owner, consumer)
    operation = consumer.operation
    _unused_directory_cells_tail(owner, operation)
    ledger, phase, native = operation.ledger, operation.phase, operation.native
    counts, attempts = ledger.counts, ledger.attempts
    inflight, failed, failure = ledger.inflight, ledger.failed, ledger.failure
    state, ended, token = operation.state, operation.ended, ledger.preparation
    _require(type(token) is list and len(token) == 3
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and consumer.commit[0] is None)
    actor_mismatch = False
    actor_state = actor_arguments = None
    try:
        inflight[0] = token
        token[0], token[1], token[2] = owner, operation.registration, consumer
        phase.result[0] = token
        phase.current[0] = phase.active
        actor_arguments = (consumer, operation, operation.callee, *operation.arguments)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        try:
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                  operation.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        _native_post_actor_state(owner, actor_state, actor_arguments)
        _directory_admission_preparation_tail(owner, consumer, operation, token)
        attempts.append(operation)
        counts[0] = operation.budget[3]
        state[0] = True
        phase.result[0] = operation
        inflight[0] = operation
        _require(_active_directory_operation_tail(owner, consumer) is operation)
        return operation
    except BaseException:
        clean_mismatch = False
        if actor_mismatch:
            try:
                _native_post_actor_state(owner, actor_state, actor_arguments)
                _directory_admission_preparation_tail(owner, consumer, operation, token)
                clean_mismatch = True
            except BaseException:
                clean_mismatch = False
        if clean_mismatch:
            ended[0] = True  # this exact intent cannot be admitted again
            phase.current[0] = phase.idle
        else:
            if type(failure) is list and len(failure) == 1 and failure[0] is None:
                failure[0] = operation
            if type(failed) is list and len(failed) == 1:
                failed[0] = True
            if type(state) is list and len(state) == 3:
                state[2] = True
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.active or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
        if (type(phase.result) is list and len(phase.result) == 1
                and (phase.result[0] is token or phase.result[0] is operation)):
            phase.result[0] = None
        if (type(inflight) is list and len(inflight) == 1
                and (inflight[0] is token or inflight[0] is operation)):
            inflight[0] = None
        raise


class _DirectoryMetadataReturn(NamedTuple):
    operation: _MetadataOperation
    result: _MetadataResult
    consumer: _DirectoryConsumer
    raw: object
    snapshot: _NativeMetadataSnapshot

    def __repr__(self):
        return '<DirectoryMetadataReturn pending original DATA redacted>'


def _returned_directory_operation_tail(owner, consumer, operation, raw):
    """Actual raw return retained in original ACTIVE storage, before publication."""
    _require(_charged_directory_operation_tail(owner, consumer) is operation
             and operation.state[1] is True and operation.ended[0] is True
             and operation.phase.current[0] is operation.phase.active
             and operation.ledger.inflight[0] is operation
             and type(raw) is operation.native.result_type
             and operation.result.raw[0] is raw
             and all(cell[0] is None for cell in (operation.result.category,
                     operation.result.snapshot, operation.result.acknowledged,
                     operation.result.envelope)))
    return operation


def _pending_directory_return_tail(owner, consumer, actual):
    """Rejoin the actual producer return; constructing matching DATA is no grant."""
    _require(type(actual) is _DirectoryMetadataReturn)
    operation = _charged_directory_operation_tail(owner, consumer)
    result, phase = operation.result, operation.phase
    _require(actual.operation is operation and actual.result is result
             and actual.consumer is consumer
             and operation.state[1] is True and operation.ended[0] is True
             and phase.current[0] is phase.pending
             and operation.ledger.inflight[0] is None
             and result.envelope[0] is actual
             and type(actual.raw) is operation.native.result_type
             and result.raw[0] is actual.raw
             and type(actual.snapshot) is _NativeMetadataSnapshot
             and result.snapshot[0] is actual.snapshot
             and type(result.category[0]) is str and result.category[0] == 'directory'
             and result.acknowledged[0] is None)
    return actual


def _produce_directory_metadata(owner, consumer):
    """One fixed captured fstat with original return custody; no policy ACK.

    This producer is unwired. Its caller must retain the actual return and use
    the fixed policy consumer; PENDING cannot admit more work or descriptor close.
    """
    operation = _admit_directory_operation(owner, consumer)
    result, ledger, phase = operation.result, operation.ledger, operation.phase
    callee, arguments = operation.callee, operation.arguments
    raw, snapshot, actual = result.unset, None, None
    category = 'directory'
    try:
        _require(_active_directory_operation_tail(owner, consumer) is operation
                 and operation.callee is callee and operation.arguments is arguments)
        raw = callee(arguments[0])
        result.raw[0] = raw  # retain the actual C return before allocating/validating
        operation.state[1] = True
        operation.ended[0] = True
        _returned_directory_operation_tail(owner, consumer, operation, raw)
        snapshot = _native_metadata_snapshot(owner, operation.registration,
                                             operation.native, raw)
        _returned_directory_operation_tail(owner, consumer, operation, raw)
        _require(type(snapshot) is _NativeMetadataSnapshot)
        actual = _DirectoryMetadataReturn(operation, result, consumer, raw, snapshot)
        _returned_directory_operation_tail(owner, consumer, operation, raw)
        result.category[0] = category
        result.snapshot[0] = snapshot
        result.envelope[0] = actual
        ledger.inflight[0] = None  # native call ended; pending result stays separately owned
        phase.current[0] = phase.pending
        _require(_pending_directory_return_tail(owner, consumer, actual) is actual)
        return actual
    except BaseException:
        # No refund/replay. Retire only held original data, preserving replacement slots.
        if type(operation.ended) is list and len(operation.ended) == 1:
            operation.ended[0] = True
        if type(operation.state) is list and len(operation.state) == 3:
            operation.state[2] = True
        if (type(ledger.failure) is list and len(ledger.failure) == 1
                and ledger.failure[0] is None):
            ledger.failure[0] = operation
        if type(ledger.failed) is list and len(ledger.failed) == 1:
            ledger.failed[0] = True
        if type(result.raw) is list and len(result.raw) == 1 and result.raw[0] is raw:
            result.raw[0] = result.unset
        if (type(result.snapshot) is list and len(result.snapshot) == 1
                and result.snapshot[0] is snapshot):
            result.snapshot[0] = None
        if (type(result.envelope) is list and len(result.envelope) == 1
                and result.envelope[0] is actual):
            result.envelope[0] = None
        if (type(result.category) is list and len(result.category) == 1
                and result.category[0] is category):
            result.category[0] = None
        if (type(phase.current) is list and len(phase.current) == 1
                and (phase.current[0] is phase.active or phase.current[0] is phase.pending)):
            phase.current[0] = phase.failed
        if (type(phase.result) is list and len(phase.result) == 1
                and phase.result[0] is operation):
            phase.result[0] = None
        if (type(ledger.inflight) is list and len(ledger.inflight) == 1
                and ledger.inflight[0] is operation):
            ledger.inflight[0] = None
    finally:
        raw = result.unset
        snapshot = None
        actual = None
    raise ArtifactObservationError(owner) from None
