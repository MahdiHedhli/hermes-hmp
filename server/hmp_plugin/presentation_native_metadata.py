"""Unwired original metadata intent/result preparation; no syscall dispatcher."""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType, MemberDescriptorType
from typing import NamedTuple

from .presentation_metadata_custody import (
    _allocate_directory_custody,
    _capture_payload_origin,
    _directory_payload_cells,
    _marker_tail,
    _origin_tail,
    _payload_state_is_clear,
    _PayloadOrigin,
)
from .presentation_startup_artifacts import (
    _MAX_FILE,
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
    _NativeDeclaredMetadataPlan,
    _NativeMetadataResource,
    _NativeProbeMetadataResource,
    _NativeStartupProbeMetadataResource,
    _native_work_registration_tail,
    _NativeMetadataSnapshot,
    _NativeScopeRegistration,
    _NativeDeclaredMetadataSite,
    _NativeRuntimeReadCommit,
    _NativeCacheReadCommit,
    _native_runtime_read_history_tail,
    _native_cache_read_history_tail,
    _native_runtime_read_receipt_state_tail,
    _native_cache_read_receipt_state_tail,
    _native_runtime_read_receipt_mirrors_tail,
    _native_cache_read_receipt_mirrors_tail,
    _native_read_walk_mirrors_tail,
    _native_read_lifecycle_mirrors_tail,
    _NativeOpenedDescriptor,
    _native_descriptor_closed,
    _prepare_native_metadata_resource,
    _require,
    _Scope,
)


class _MetadataResult(NamedTuple):
    """Raw-free retained history; payload access is DATA, never admission."""
    attempt: list
    consumer: list
    unset: object
    acknowledged: list
    custody_origin: _PayloadOrigin
    custody_link: list
    custody_slot: list

    def _cell(self, index):
        # These compatibility accessors preserve the existing fixed-policy joins.
        # A future fixed caller must independently hold the actual factory return
        # across effects; following this current link cannot establish custody.
        origin = self.custody_origin
        _require(type(self.attempt) is list and len(self.attempt) == 1
                 and type(self.attempt[0]) is _MetadataOperation
                 and self.attempt[0].result is self
                 and type(self.custody_link) is list and len(self.custody_link) == 1
                 and type(self.custody_slot) is list and len(self.custody_slot) == 1)
        operation = self.attempt[0]
        payload, marker = self.custody_link[0], self.custody_slot[0]
        _marker_tail(operation.owner, origin, marker, payload)
        _require(marker.operation is operation and marker.consumer is None
                 and marker.owner_link is self.custody_link
                 and marker.marker_slot is self.custody_slot
                 and _payload_state_is_clear(marker.state))
        cells = _directory_payload_cells(operation.owner, origin, marker, payload)
        cell = cells[index]
        _require(type(cell) is list and len(cell) == 1)
        return cell

    @property
    def raw(self):
        return self._cell(0)

    @property
    def category(self):
        return self._cell(1)

    @property
    def snapshot(self):
        return self._cell(2)

    @property
    def envelope(self):
        return self._cell(3)

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


def _startup_probe_origin_tail(owner, resource):
    """Only an original registered startup scope may select its fixed policy."""
    _require(type(resource) is _NativeStartupProbeMetadataResource
             and type(owner) is StartupArtifactOwner and resource.owner is owner
             and type(resource.registration) is _NativeScopeRegistration)
    registration = resource.registration
    _native_work_registration_tail(owner, registration)
    scope = registration.scope
    origin = scope.native_startup_probe_origin
    _require(scope.cache is not None and type(origin) is tuple and len(origin) == 7
             and origin[0] is _NativeStartupProbeMetadataResource
             and origin[1] is StartupArtifactOwner and type(origin[2]) is ModuleType
             and type(origin[3]) is FunctionType and origin[3].__code__ is origin[4]
             and origin[3].__globals__ is vars(origin[2])
             and type(sys.modules) is dict
             and sys.modules.get('hmp_plugin.presentation_startup_probe') is origin[2]
             and vars(origin[2]).get('_resource_tail') is origin[3]
             and type(origin[5]) is tuple and len(origin[5]) == 7
             and origin[5][0] is origin[2])
    return origin


def _closed_probe_engine_origin(owner, resource):
    """Fixed internal cohorts only; no client policy selector or callback."""
    if type(resource) is _NativeStartupProbeMetadataResource:
        return _startup_probe_origin_tail(owner, resource)[5]
    _require(type(resource) is _NativeProbeMetadataResource and resource.owner is owner
             and type(resource.registration) is _NativeScopeRegistration)
    _native_work_registration_tail(owner, resource.registration)
    origin = resource.registration.scope.native_probe_engine_origin
    _require(type(origin) is tuple and len(origin) == 7
             and type(origin[0]) is ModuleType and type(origin[2]) is tuple)
    return origin


def _resource_tail(owner, resource):
    """Rejoin the held actual resource; never adopt a current replacement."""
    if type(resource) is _NativeStartupProbeMetadataResource:
        origin = _startup_probe_origin_tail(owner, resource)
        return origin[3](owner, resource)
    if type(resource) is not _NativeMetadataResource:
        # Type and registration are checked before touching startup namespaces.
        # Current exports can only rejoin originals captured before constructors;
        # they cannot nominate a replacement helper or resource type.
        _require(type(resource) is _NativeProbeMetadataResource
                 and resource.owner is owner
                 and type(resource.registration) is _NativeScopeRegistration)
        registration = resource.registration
        _native_work_registration_tail(owner, registration)
        origin = registration.scope.native_probe_origin
        _require(type(origin) is tuple and len(origin) == 6
                 and origin[0] is _NativeProbeMetadataResource
                 and type(origin[1]) is type and type(owner) is origin[1]
                 and type(origin[2]) is ModuleType and type(origin[3]) is ModuleType
                 and type(origin[4]) is FunctionType
                 and origin[4].__code__ is origin[5]
                 and origin[4].__globals__ is vars(origin[3])
                 and type(sys.modules) is dict
                 and sys.modules.get('hmp_startup.cache_probe') is origin[2]
                 and sys.modules.get('hmp_startup.probe_metadata') is origin[3]
                 and vars(origin[2]).get('RuntimeCacheProbeOwner') is origin[1]
                 and vars(origin[3]).get('_ProbeObservationResource') is origin[0]
                 and vars(origin[3]).get('_fresh_probe_resource_tail') is origin[4])
        return origin[4](owner, resource)
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
             and actual.variant is resource.variant
             and actual.ordinal is resource.ordinal and actual.descriptor is resource.descriptor
             and all(before is after for before, after in
                     zip(resource.arguments, actual.arguments, strict=True)))
    return resource


def _prepare_metadata_operation(owner, resource):
    """Legacy preparation DATA; this wrapper does not retain retirement custody."""
    intent, marker, payload = _prepare_metadata_operation_with_custody(owner, resource)
    # Native calls are not made here. Fixed callers must use the three actual
    # factory returns above rather than rediscovering payload identity later.
    del marker, payload
    return intent


def _prepare_metadata_operation_with_custody(owner, resource):
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
    origin = _capture_payload_origin()
    result = _MetadataResult([None], [None], unset, [None], origin, [None], [None])
    intent = _MetadataOperation(owner, resource, registration, ledger, phase, native,
                                registration.context, operation, callee, resource.arguments,
                                index, attempts, (counts, used, reserved, used + 1), result,
                                [False, False, False], [False])
    result.attempt[0] = intent
    marker, payload = _allocate_directory_custody(
        owner, intent, None, origin, result.custody_link, result.custody_slot, unset)
    _require(_resource_tail(owner, resource) is resource
             and ledger.attempts is attempts and len(attempts) == index
             and ledger.counts is counts and counts[0] is used and counts[1] is reserved
             and phase.current[0] is phase.idle and phase.result[0] is None
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and native.operations[operation] is callee)
    return intent, marker, payload


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
    commit: list
    history: list
    predecessor: object
    baseline: object = None
    eof: object = None
    custody: object = None

    @property
    def consumption(self):
        return self.operation.result._cell(4)

    def __repr__(self):
        return '<DirectoryConsumer unqualified fixed policy redacted>'


class _ProbeConsumer(NamedTuple):
    """Closed probe policy, sharing lifecycle without claiming file/EOF policy."""
    execution: object
    operation: _MetadataOperation
    predecessor: object
    commit: list
    custody: tuple

    @property
    def owner(self):
        return self.execution.owner

    @property
    def resource(self):
        return self.operation.resource

    @property
    def consumption(self):
        return self.operation.result._cell(4)

    @property
    def baseline(self):
        return None

    @property
    def eof(self):
        return None

    @property
    def history(self):
        return self.execution.history

    def __repr__(self):
        return '<ProbeConsumer fixed metadata policy redacted>'


def _probe_stage_functions(owner, resource):
    """Actual registered origin selects fixed internal stages, never a caller."""
    origin = _closed_probe_engine_origin(owner, resource)
    wanted = ('_prepare_shared_consumer', '_latch_shared_consumer',
              '_produce_shared', '_consume_shared', '_ack_shared', '_attached_shared', '_retired_shared')
    stages = []
    for name in wanted:
        rows = tuple(row for row in origin[2] if type(row) is tuple and len(row) == 3
                     and type(row[0]) is str and row[0] == name)
        _require(len(rows) == 1)
        _, function, code = rows[0]
        _require(type(function) is FunctionType and function.__code__ is code
                 and function.__globals__ is vars(origin[0])
                 and vars(origin[0]).get(name) is function)
        stages.append(function)
    return tuple(stages)



def _rejoin_probe_stages(owner, resource, origin, stages):
    """Rejoin retained originals after preceding stage callbacks; no nomination."""
    _require(type(resource) in (_NativeProbeMetadataResource, _NativeStartupProbeMetadataResource)
             and type(stages) is tuple and len(stages) == 7)
    _require(_closed_probe_engine_origin(owner, resource) is origin)
    actual = _probe_stage_functions(owner, resource)
    _require(_closed_probe_engine_origin(owner, resource) is origin
             and all(current is held for current, held in zip(actual, stages, strict=True)))


def _probe_policy_helper(owner, consumer, name):
    """Closed original probe policy projection, never a client callback."""
    _require(type(consumer) is _ProbeConsumer and type(name) is str
             and name in ('_make_shared_commit', '_commit_shared_tail',
                          '_acked_shared_history', '_publish_shared_ack'))
    operation = tuple.__getitem__(consumer, 1)
    _require(type(operation) is _MetadataOperation
             and type(operation.resource) in (_NativeProbeMetadataResource, _NativeStartupProbeMetadataResource))
    _require(type(operation.registration) is _NativeScopeRegistration
             and operation.registration is operation.resource.registration)
    _native_work_registration_tail(owner, operation.registration)
    origin = _closed_probe_engine_origin(owner, operation.resource)
    _require(type(origin) is tuple and len(origin) == 7 and type(origin[0]) is ModuleType
             and type(origin[2]) is tuple)
    rows = tuple(row for row in origin[2] if type(row) is tuple and len(row) == 3
                 and type(row[0]) is str and row[0] == name)
    _require(len(rows) == 1)
    _, function, code = rows[0]
    _require(type(function) is FunctionType and function.__code__ is code
             and function.__globals__ is vars(origin[0])
             and vars(origin[0]).get(name) is function)
    return function


def _probe_latched_resource_tail(owner, consumer):
    _require(type(consumer) is _ProbeConsumer)
    operation = tuple.__getitem__(consumer, 1)
    _require(type(operation) is _MetadataOperation
             and type(operation.resource) in (_NativeProbeMetadataResource, _NativeStartupProbeMetadataResource))
    stages = _probe_stage_functions(owner, operation.resource)
    _require(stages[1](owner, consumer, rejoin=True) is consumer)
    return operation.resource


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


def _fixed_metadata_role(resource):
    """Closed original directory/leaf-before/opened roles, never caller dispatch."""
    _require(type(resource) is _NativeMetadataResource
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and type(resource.site[1]) is str)
    operation, role = resource.site[:2]
    _require((operation == 4 and role == 'directory')
             or (operation == 3 and role == 'leaf_before')
             or (operation == 4 and role == 'leaf_opened')
             or (operation in (3, 4) and role in ('leaf_after_read', 'directory_after_hash')))
    return role


def _fixed_metadata_resource_tail(owner, resource):
    """Rejoin the actual directory FD or original leaf name/opened parent."""
    role = _fixed_metadata_role(resource)
    _require(type(resource.arguments) is tuple
             and len(resource.arguments) == (1 if resource.site[0] == 4 else 2))
    walk = resource.held_walk[0]
    component = resource.site[2]
    _native_metadata_component_tail(owner, resource.registration, walk,
                                    resource.descriptor,
                                    component if resource.site[0] == 4 else component - 1)
    if resource.site[0] == 4:
        _require(resource.arguments[0] is resource.descriptor.fd)
    else:
        _require(type(resource.arguments[0]) is str
                 and type(walk.components[component]) is str
                 and resource.arguments[0] == walk.components[component]
                 and resource.arguments[1] is (None if resource.descriptor is None else resource.descriptor.fd))
    return resource


def _fixed_metadata_identity_size(resource):
    return 5 if _fixed_metadata_role(resource) in ('directory', 'directory_after_hash') else 9


def _undebited_directory_cells_tail(owner, operation):
    """Untouched original intent cells only; caller proves resource/consumer joins."""
    _require(type(operation) is _MetadataOperation and operation.owner is owner
             and type(operation.result) is _MetadataResult
             and type(operation.operation) is int and operation.operation in (3, 4))
    resource, result = operation.resource, operation.result
    _require(type(resource) in (_NativeMetadataResource, _NativeProbeMetadataResource,
                                        _NativeStartupProbeMetadataResource)
             and type(resource.registration) is _NativeScopeRegistration)
    registration = resource.registration
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(operation.registration is registration and operation.ledger is ledger
             and ledger.phase is phase
             and operation.phase is phase and operation.native is registration.native_origin
             and operation.context is registration.context
             and operation.callee is operation.native.operations[operation.operation]
             and operation.operation == resource.site[0]
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
             and type(operation.ended[0]) is bool
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


def _unspent_directory_cells_tail(owner, operation):
    """An undebited intent must still be unended to enter admission."""
    result = _undebited_directory_cells_tail(owner, operation)
    _require(operation.ended[0] is False)
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


def _prepare_directory_consumer(owner, operation, predecessor=None, baseline=None, eof=None,
                                custody=None):
    """Bind one actual unused intent to a fixed runtime/cache metadata policy.

    Other owner/configuration/tree policies need their own reviewed consumers.
    Nothing here publishes ACTIVE, debits allowance or invokes native work.
    """
    _require(type(operation) is _MetadataOperation and operation.owner is owner
             and type(operation.operation) is int and operation.operation in (3, 4)
             and type(operation.result) is _MetadataResult)
    resource, result = operation.resource, operation.result
    _resource_tail(owner, resource)
    _require(_fixed_metadata_role(resource) in ('directory', 'leaf_before', 'leaf_opened', 'leaf_after_read', 'directory_after_hash')
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
    history = resource.metadata.commits
    _require(type(history) is list and len(history) == resource.ordinal)
    # The fixed caller carries the literal previous return across callbacks.
    # Current mirrors can confirm it; they cannot nominate its replacement.
    _require(predecessor is None if resource.ordinal == 0 else
             type(predecessor) is _DirectoryPolicyCommit
             and history[resource.ordinal - 1] is predecessor)
    consumer = _DirectoryConsumer(owner, operation, resource, parents, kind,
                                   class_name, module_name, origin[0], origin[1], module,
                                   origin[4], origin[5], file_module, StartupArtifactOwner,
                                   [None], history, predecessor, baseline, eof, custody)
    _require(_resource_tail(owner, resource) is resource
             and operation.result is result and result.consumer[0] is None
             and result.attempt[0] is operation and result.raw[0] is result.unset)
    _native_read_lifecycle_tail(owner, resource.registration, parents)
    _require(_unused_directory_intent_tail(owner, operation) is result
             and _directory_material_tail(owner, consumer) is consumer)
    _directory_predecessors_tail(owner, consumer)
    _require(consumer.predecessor is predecessor
             and consumer.baseline is baseline and consumer.eof is eof
             and consumer.custody is custody)
    result.consumer[0] = consumer
    _require(_directory_material_tail(owner, consumer) is consumer
             and result.consumer[0] is consumer)
    _directory_predecessors_tail(owner, consumer)
    _require(consumer.predecessor is predecessor
             and consumer.baseline is baseline and consumer.eof is eof
             and consumer.custody is custody)
    return consumer


def _metadata_predecessor_chain_tail(owner, consumer):
    """Held raw-free original ACK prefix, never a cursor or native-work credit."""
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(consumer.resource) is _NativeMetadataResource)
    resource = consumer.resource
    metadata, registration = resource.metadata, resource.registration
    _require(type(metadata) is _NativeDeclaredMetadataPlan
             and type(registration) is _NativeScopeRegistration
             and consumer.history is metadata.commits and type(consumer.history) is list
             and type(resource.ordinal) is int
             and type(metadata.definitions) is tuple
             and 0 <= resource.ordinal < len(metadata.definitions)
             and len(consumer.history) >= resource.ordinal)
    commit = consumer.predecessor
    for ordinal in range(resource.ordinal - 1, -1, -1):
        _require(type(commit) is _DirectoryPolicyCommit and commit.owner is owner
                 and consumer.history[ordinal] is commit
                 and type(commit.ordinal) is int and commit.ordinal == ordinal
                 and type(commit.next_ordinal) is int and commit.next_ordinal == ordinal + 1
                 and commit.site is metadata.definitions[ordinal]
                 and type(commit.resource) is _NativeMetadataResource
                 and commit.resource.metadata is metadata
                 and commit.resource.registration is registration
                 and commit.resource.held_walk is resource.held_walk
                 and type(commit.operation) is _MetadataOperation
                 and commit.operation.owner is owner
                 and commit.operation.resource is commit.resource
                 and commit.operation.registration is registration
                 and commit.operation.attempts is registration.native_ledger.attempts
                 and type(commit.operation.index) is int
                 and 0 <= commit.operation.index < len(commit.operation.attempts)
                 and commit.operation.attempts[commit.operation.index] is commit.operation
                 and type(commit.operation.state) is list
                 and all(type(value) is bool for value in commit.operation.state)
                 and commit.operation.state == [True, True, False]
                 and type(commit.operation.ended) is list
                 and all(type(value) is bool for value in commit.operation.ended)
                 and commit.operation.ended == [True]
                 and type(commit.operation.result) is _MetadataResult
                 and type(commit.operation.result.acknowledged) is list
                 and len(commit.operation.result.acknowledged) == 1
                 and commit.operation.result.acknowledged[0] is commit
                 and type(commit.consumer) is _DirectoryConsumer
                 and commit.consumer.operation is commit.operation
                 and commit.consumer.resource is commit.resource
                 and type(commit.consumer.commit) is list and len(commit.consumer.commit) == 1
                 and commit.consumer.commit[0] is commit
                 and commit.consumer.history is consumer.history)
        commit = commit.consumer.predecessor
    _require(commit is None)
    return consumer


def _directory_predecessors_tail(owner, consumer):
    _metadata_predecessor_chain_tail(owner, consumer)
    resource = consumer.resource
    if _fixed_metadata_role(resource) == 'leaf_opened':
        predecessor = consumer.predecessor
        _require(type(predecessor) is _DirectoryPolicyCommit
                 and predecessor.resource.held_walk is resource.held_walk
                 and type(predecessor.site) is tuple and len(predecessor.site) == 3
                 and predecessor.site[0] == 3 and predecessor.site[1] == 'leaf_before'
                 and predecessor.resource.variant.expected is resource.variant.expected
                 and type(predecessor.identity) is tuple and len(predecessor.identity) == 9
                 and all(type(value) is int for value in predecessor.identity))
    if _fixed_metadata_role(resource) in ('leaf_after_read', 'directory_after_hash'):
        _postread_receipts_tail(owner, consumer)
    else:
        _require(consumer.baseline is None and consumer.eof is None)
    return consumer


def _postread_receipts_tail(owner, consumer):
    """Literal baseline/EOF joins plus exact accounted metadata since that EOF.

    Historical read validation grants no work. This closed post-read sequence
    accounts for every intervening attempt/debit and retains the original EOF
    return rather than adopting an ACK from current mirrors.
    """
    resource, operation = consumer.resource, consumer.operation
    baseline, eof = consumer.baseline, consumer.eof
    directory = _fixed_metadata_role(resource) == 'directory_after_hash'
    _require(type(baseline) is _DirectoryPolicyCommit
             and baseline.owner is owner
             and type(baseline.resource) is _NativeMetadataResource
             and type(baseline.resource.variant) is _NativeDeclaredMetadataSite
             and baseline.resource.held_walk is resource.held_walk
             and baseline.resource.variant.expected is resource.variant.expected
             and type(baseline.site) is tuple and len(baseline.site) == 3
             and type(baseline.site[0]) is int and baseline.site[0] == (4 if directory else 3)
             and type(baseline.site[1]) is str
             and baseline.site[1] == ('directory' if directory else 'leaf_before')
             and type(baseline.identity) is tuple
             and len(baseline.identity) == (5 if directory else 9)
             and all(type(value) is int for value in baseline.identity)
             and type(baseline.ordinal) is int
             and 0 <= baseline.ordinal < resource.ordinal
             and consumer.history[baseline.ordinal] is baseline)
    if consumer.class_name == 'RuntimeSourceReadOwner':
        _require(type(eof) is _NativeRuntimeReadCommit)
        _require(_native_runtime_read_history_tail(owner, eof, eof.step) is eof)
    else:
        _require(consumer.class_name == 'DeclaredCacheReadOwner'
                 and type(eof) is _NativeCacheReadCommit)
        _require(_native_cache_read_history_tail(owner, eof, eof.step) is eof)
    walk = resource.held_walk[0]
    step, read = eof.step, eof.operation
    _require(consumer.baseline is baseline and consumer.eof is eof
             and step.walk is walk and step.expected is resource.variant.expected
             and step.registration is resource.registration
             and eof.eof is True and type(eof.remaining) is int and eof.remaining == 0
             and type(eof.count[2]) is int and eof.count[2] == step.expected.size)
    if directory:
        descriptor = baseline.resource.descriptor
        _require(type(descriptor) is _NativeOpenedDescriptor
                 and type(baseline.site[2]) is int and baseline.site[2] == resource.site[2])
        _native_metadata_component_tail(owner, resource.registration, walk, descriptor,
                                        resource.site[2])
        _require(resource.descriptor is (descriptor if resource.site[0] == 4 else
                                        descriptor.allocation.parent))
    else:
        _require(resource.descriptor is (step.descriptor if resource.site[0] == 4 else
                                        step.descriptor.allocation.parent))
    # Every original metadata row after EOF has exactly one accounted debit.
    # No open/close/read or unrelated attempt can be inserted into this sequence.
    first = len(walk.components) + 1
    offset = resource.ordinal - first
    _require(type(offset) is int and 0 <= offset < len(resource.metadata.definitions) - first
             and (offset >= 2 if directory else offset < 2)
             and (not directory or resource.site[2] == (offset - 2) // 2)
             and resource.site[0] == (4 if offset % 2 == 0 else 3)
             and type(operation.state) is list and len(operation.state) == 3
             and type(operation.state[0]) is bool
             and type(read.index) is int and type(read.budget[3]) is int
             and operation.index == read.index + 1 + offset
             and len(operation.ledger.attempts) == read.index + 1 + offset + int(operation.state[0])
             and operation.ledger.counts[0] == read.budget[3] + offset + int(operation.state[0])
             and operation.budget[1] == read.budget[3] + offset)
    predecessor = consumer.predecessor
    _require(type(predecessor) is _DirectoryPolicyCommit
             and predecessor.resource.held_walk is resource.held_walk
             and predecessor.site is resource.metadata.definitions[resource.ordinal - 1])
    for earlier in range(offset):
        actual = consumer.history[first + earlier]
        _require(type(actual) is _DirectoryPolicyCommit
                 and actual.operation.index == read.index + 1 + earlier
                 and actual.operation.budget[1] == read.budget[3] + earlier
                 and actual.operation.budget[3] == read.budget[3] + earlier + 1
                 and actual.consumer.eof is eof)
    if offset % 2:
        _require(predecessor.consumer.baseline is baseline)
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



def _declared_leaf_identity(snapshot, actor_uid, expected_size):
    """Fixed runtime/cache regular-file policy DATA, not an admission or ACK.

    This excludes anchor/configuration policies. A future fixed consumer must
    bind expected_size to its original declared row and snapshot to the actual
    retained native return; valid-looking DATA cannot substitute for those joins.
    """
    _require(type(snapshot) is _NativeMetadataSnapshot and type(actor_uid) is int
             and actor_uid >= 0 and type(expected_size) is int
             and 0 <= expected_size <= _MAX_FILE
             and type(snapshot.identity) is tuple and len(snapshot.identity) == 9
             and all(type(value) is int for value in snapshot.identity))
    identity = snapshot.identity
    mode, uid, links, size = identity[2], identity[3], identity[5], identity[6]
    # Preserve _file's exact policy without mutable stat-module callbacks.
    _require(mode & 0o170000 == 0o100000 and uid in (0, actor_uid)
             and links == 1 and size == expected_size
             and not mode & (0o022 | 0o6000))
    return identity


def _declared_leaf_source_before_data(snapshot, actor_uid, expected_size):
    """Fixed source-effect leaf-before DATA; never an operation allowance.

    Preserve the original _file/path_stats integer conversion of this same
    native snapshot's st_mtime, including truncation toward zero before epoch.
    Only a source-digest effect requires this timestamp. Cache/non-source
    consumers retain their existing policy without this extra requirement.
    The eventual fixed consumer must still bind the original declaration,
    actual native return and source-digest predecessor before publication.
    """
    identity = _declared_leaf_identity(snapshot, actor_uid, expected_size)
    timestamp = snapshot.mtime
    _require(type(timestamp) in (int, float) and -2 ** 64 < timestamp < 2 ** 64)
    return identity, int(timestamp)


def _latched_directory_resource_tail(owner, consumer):
    """Original already-latched cohort DATA; not a phase check or work grant."""
    if type(consumer) is _ProbeConsumer:
        return _probe_latched_resource_tail(owner, consumer)
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(consumer.operation) is _MetadataOperation
             and type(consumer.resource) is _NativeMetadataResource
             and consumer.operation.resource is consumer.resource)
    operation, resource = consumer.operation, consumer.resource
    registration = resource.registration
    metadata = _native_declared_metadata_cohort_tail(owner, registration, resource.held_walk)
    _directory_predecessors_tail(owner, consumer)
    _require(len(consumer.history) == resource.ordinal)
    _require(metadata is resource.metadata and metadata.progress[0] is resource.ordinal
             and metadata.progress[1] is consumer
             and type(resource.ordinal) is int
             and metadata.definitions[resource.ordinal] is resource.site
             and metadata.variants[resource.ordinal] is resource.variant
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and resource.site[0] in (3, 4)
             and _fixed_metadata_role(resource) in ('directory', 'leaf_before', 'leaf_opened', 'leaf_after_read', 'directory_after_hash')
             and type(resource.site[2]) is int
             and operation.owner is owner and operation.registration is registration
             and operation.ledger is registration.native_ledger
             and operation.phase is registration.native_phase
             and operation.native is registration.native_origin
             and operation.context is registration.context
             and type(operation.operation) is int and operation.operation in (3, 4)
             and operation.callee is operation.native.operations[operation.operation]
             and operation.operation == resource.site[0]
             and operation.arguments is resource.arguments
             and type(operation.result) is _MetadataResult
             and type(operation.result.attempt) is list and len(operation.result.attempt) == 1
             and operation.result.attempt[0] is operation
             and type(operation.result.consumer) is list and len(operation.result.consumer) == 1
             and operation.result.consumer[0] is consumer
             and type(resource.arguments) is tuple)
    _require(_fixed_metadata_resource_tail(owner, resource) is resource
             and _directory_material_tail(owner, consumer) is consumer)
    _native_read_lifecycle_tail(owner, registration, consumer.parents)
    _native_work_origin_tail(owner, registration, operation.native)
    _require(_directory_material_tail(owner, consumer) is consumer)
    _directory_predecessors_tail(owner, consumer)
    _require(len(consumer.history) == resource.ordinal)
    return resource


def _charged_directory_history_tail(owner, consumer):
    """Rejoin an already-debited directory intent; never admit work.

    The future producer must hold its original consumer across admission. A
    caller-built matching ledger row is not an independent native-call receipt.
    This function neither invokes the native callee nor changes any state.
    """
    _latched_directory_resource_tail(owner, consumer)
    operation = consumer.operation
    ledger, phase = operation.ledger, operation.phase
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
             and phase.result[0] is operation)
    return operation


def _charged_directory_operation_tail(owner, consumer):
    """Charged history plus current payload DATA; never independent custody."""
    operation = _charged_directory_history_tail(owner, consumer)
    result = operation.result
    _require(type(result.raw) is list and len(result.raw) == 1
             and all(type(cell) is list and len(cell) == 1
                     for cell in (result.category, result.snapshot,
                                  result.acknowledged, result.envelope))
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and type(consumer.commit) is list and len(consumer.commit) == 1)
    return operation


def _active_directory_operation_tail(owner, consumer):
    """Original charged intent immediately before its fixed native call."""
    operation = _charged_directory_operation_tail(owner, consumer)
    result = operation.result
    _require(operation.state[1] is False and operation.ended[0] is False
             and operation.ledger.inflight[0] is operation
             and consumer.consumption[0] is None and consumer.commit[0] is None
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

    @property
    def category(self):
        return 'returned'

    def __repr__(self):
        return '<DirectoryMetadataReturn pending original DATA redacted>'



class _ReportedMissingMetadataReturn(NamedTuple):
    """Actual known-raised STAT outcome; no exception/errno/filename retained."""
    operation: _MetadataOperation
    result: _MetadataResult
    consumer: _ProbeConsumer

    @property
    def raw(self):
        return self.result.unset

    @property
    def snapshot(self):
        return None

    @property
    def category(self):
        return 'reported_missing'

    def __repr__(self):
        return '<ReportedMissingMetadataReturn known raised DATA redacted>'


def _probe_current_lifetime_tail(owner, consumer):
    _require(type(consumer) is _ProbeConsumer and type(consumer.operation) is _MetadataOperation
             and type(consumer.operation.resource) in (_NativeProbeMetadataResource, _NativeStartupProbeMetadataResource))
    registration = consumer.operation.registration
    _require(type(registration) is _NativeScopeRegistration
             and registration is consumer.operation.resource.registration)
    _native_work_registration_tail(owner, registration)
    origin = _closed_probe_engine_origin(owner, consumer.operation.resource)
    _require(type(origin) is tuple and len(origin) == 7 and type(origin[2]) is tuple)
    rows = tuple(row for row in origin[2] if type(row) is tuple and len(row) == 3
                 and type(row[0]) is str and row[0] == '_lifecycle_tail')
    _require(len(rows) == 1)
    _, function, code = rows[0]
    _require(type(function) is FunctionType and function.__code__ is code
             and function.__globals__ is vars(origin[0])
             and vars(origin[0]).get('_lifecycle_tail') is function)
    return function(owner, registration.scope, registration, registration.scope.native_probe_plan)


def _reported_missing_operation_tail(owner, consumer, actual):
    _require(type(consumer) is _ProbeConsumer and type(actual) is _ReportedMissingMetadataReturn)
    operation = _charged_directory_operation_tail(owner, consumer)
    result = operation.result
    _require(actual.operation is operation and actual.result is result and actual.consumer is consumer
             and operation.operation == 3 and operation.state[1] is False
             and operation.state[2] is False and operation.ended[0] is True
             and operation.phase.current[0] is operation.phase.active
             and operation.ledger.inflight[0] is operation
             and result.raw[0] is result.unset
             and consumer.consumption[0] is None and consumer.commit[0] is None
             and all(cell[0] is None for cell in (result.category, result.snapshot,
                                                result.acknowledged, result.envelope)))
    _probe_current_lifetime_tail(owner, consumer)
    return actual

def _returned_directory_operation_tail(owner, consumer, operation, raw):
    """Actual raw return retained in original ACTIVE storage, before publication."""
    _require(_charged_directory_operation_tail(owner, consumer) is operation
             and operation.state[1] is True and operation.ended[0] is True
             and operation.phase.current[0] is operation.phase.active
             and operation.ledger.inflight[0] is operation
             and consumer.consumption[0] is None and consumer.commit[0] is None
             and type(raw) is operation.native.result_type
             and operation.result.raw[0] is raw
             and all(cell[0] is None for cell in (operation.result.category,
                     operation.result.snapshot, operation.result.acknowledged,
                     operation.result.envelope)))
    return operation


def _pending_directory_cohort_tail(owner, consumer, actual):
    """Rejoin the actual producer return; constructing matching DATA is no grant."""
    if type(consumer) is _ProbeConsumer:
        _require(type(actual) in (_DirectoryMetadataReturn, _ReportedMissingMetadataReturn))
        operation = _charged_directory_operation_tail(owner, consumer)
        result, phase = operation.result, operation.phase
        _require(actual.operation is operation and actual.result is result
                 and actual.consumer is consumer and operation.ended[0] is True
                 and phase.current[0] is phase.pending and operation.ledger.inflight[0] is None
                 and result.envelope[0] is actual and type(result.category[0]) is str
                 and result.category[0] == actual.category)
        if type(actual) is _ReportedMissingMetadataReturn:
            _require(operation.operation == 3 and operation.state[1] is False
                     and result.raw[0] is result.unset and result.snapshot[0] is None)
        else:
            _require(operation.state[1] is True and type(actual.raw) is operation.native.result_type
                     and result.raw[0] is actual.raw and type(actual.snapshot) is _NativeMetadataSnapshot
                     and result.snapshot[0] is actual.snapshot)
        _probe_current_lifetime_tail(owner, consumer)
        return actual
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
             and type(result.category[0]) is str
             and result.category[0] == _fixed_metadata_role(consumer.resource))
    return actual


def _pending_directory_return_tail(owner, consumer, actual):
    """Original pending result before any fixed policy consumption."""
    _pending_directory_cohort_tail(owner, consumer, actual)
    _require(consumer.consumption[0] is None and consumer.commit[0] is None
             and actual.result.acknowledged[0] is None)
    return actual


def _produce_directory_metadata(owner, consumer):
    """One fixed captured fstat/no-follow stat with original custody; no policy ACK.

    This producer is unwired. Its caller must retain the actual return and use
    the fixed policy consumer; PENDING cannot admit more work or descriptor close.
    """
    operation = _admit_directory_operation(owner, consumer)
    result, ledger, phase = operation.result, operation.ledger, operation.phase
    callee, arguments = operation.callee, operation.arguments
    unset, held_state = result.unset, operation.state
    raw, snapshot, actual = unset, None, None
    probe = type(consumer) is _ProbeConsumer
    category = 'returned' if probe else _fixed_metadata_role(consumer.resource)
    native = operation.native
    missing_type = native.errors[1]
    error_number = vars(native.errors[0]).get('errno')
    error_filename = vars(native.errors[0]).get('filename')
    _require(type(error_number) is MemberDescriptorType
             and type(error_filename) is MemberDescriptorType
             and error_number.__objclass__ is native.errors[0]
             and error_filename.__objclass__ is native.errors[0])
    missing = number = filename = None
    enoent = (_closed_probe_engine_origin(owner, operation.resource)[5]
              if probe else None)
    _require(not probe or type(enoent) is int)
    origin = marker = payload = cells = joined_cells = None
    raw_cell = category_cell = snapshot_cell = envelope_cell = None
    try:
        # Capture actual cells before the native call. Compatibility properties
        # perform closure work and must not sit between the C return and storage.
        origin = result.custody_origin
        payload, marker = result.custody_link[0], result.custody_slot[0]
        cells = _directory_payload_cells(owner, origin, marker, payload)
        raw_cell, category_cell, snapshot_cell, envelope_cell = cells[:4]
        _require(_active_directory_operation_tail(owner, consumer) is operation
                 and operation.callee is callee and operation.arguments is arguments)
        # ACTIVE closure can execute descriptor joins. Rejoin the held original
        # capsule/cells afterward; never dispatch using a recaptured replacement.
        joined_cells = _directory_payload_cells(owner, origin, marker, payload)
        # Rejoin registration/material/lifecycle/native bindings and debit after
        # the last callback-bearing custody check, without payload properties.
        _require(_charged_directory_history_tail(owner, consumer) is operation)
        _require(all(descriptor.__get__(payload, origin.payload_type) is cell
                     for descriptor, cell in zip(origin.members, cells, strict=True)))
        _require(result.custody_origin is origin
                 and result.custody_link is marker.owner_link
                 and result.custody_slot is marker.marker_slot
                 and marker.operation is operation
                 and all(before is after for before, after in
                         zip(cells, joined_cells, strict=True))
                 and operation.callee is callee and operation.arguments is arguments
                 and operation.result is result and consumer.operation is operation
                 and phase.current[0] is phase.active and phase.result[0] is operation
                 and ledger.inflight[0] is operation and ledger.failed[0] is False
                 and operation.state[0] is True and operation.state[1] is False
                 and operation.state[2] is False and operation.ended[0] is False
                 and raw_cell[0] is result.unset
                 and category_cell[0] is snapshot_cell[0] is envelope_cell[0] is None
                 and cells.consumption[0] is None
                 and type(result.acknowledged) is list and len(result.acknowledged) == 1
                 and result.acknowledged[0] is None
                 and type(consumer.commit) is list and len(consumer.commit) == 1
                 and consumer.commit[0] is None)
        if operation.operation == 4:
            if probe:
                _probe_current_lifetime_tail(owner, consumer)
            raw = callee(arguments[0])
        else:
            if probe:
                # Final lifetime closure is before the call but OUTSIDE the
                # diagnostic handler: control failure is never native missing.
                _probe_current_lifetime_tail(owner, consumer)
            try:
                raw = callee(arguments[0], dir_fd=arguments[1], follow_symlinks=False)
            except missing_type as error:
                if not probe:
                    raise
                _require(type(error) is missing_type)
                number = error_number.__get__(error, missing_type)
                filename = error_filename.__get__(error, missing_type)
                _require(type(number) is int and number == enoent
                         and type(filename) is str and filename == arguments[0])
                missing = _ReportedMissingMetadataReturn(operation, result, consumer)
                _require(type(missing) is _ReportedMissingMetadataReturn
                         and missing.operation is operation and missing.result is result
                         and missing.consumer is consumer)
        # Capture the literal return before allocation/validation. This store
        # and the returned-state publication are OUTSIDE diagnostic handling.
        if missing is None:
            raw_cell[0] = raw
            operation.state[1] = True
        operation.ended[0] = True
        if missing is None:
            _returned_directory_operation_tail(owner, consumer, operation, raw)
            snapshot = _native_metadata_snapshot(owner, operation.registration,
                                                 operation.native, raw)
            _returned_directory_operation_tail(owner, consumer, operation, raw)
            _require(type(snapshot) is _NativeMetadataSnapshot)
            actual = _DirectoryMetadataReturn(operation, result, consumer, raw, snapshot)
            _returned_directory_operation_tail(owner, consumer, operation, raw)
        else:
            # A known raised outcome is ended, charged and still NOT returned.
            # It does not set the unknown/integrity-failure slot or clear debt.
            actual = _reported_missing_operation_tail(owner, consumer, missing)
            category = 'reported_missing'
            snapshot = None
        category_cell[0] = category
        snapshot_cell[0] = snapshot
        envelope_cell[0] = actual
        ledger.inflight[0] = None  # native call ended; pending result stays separately owned
        phase.current[0] = phase.pending
        _require(_pending_directory_return_tail(owner, consumer, actual) is actual)
        return actual
    except BaseException:
        # This held local is assigned ONLY by the literal native call. Even if
        # a later bookkeeping store failed, retain actual returned history;
        # never reconstruct it from a current result cell or false diagnostic.
        if (raw is not unset and type(held_state) is list and len(held_state) == 3
                and held_state[1] is False):
            held_state[1] = True
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
        if type(raw_cell) is list and len(raw_cell) == 1 and raw_cell[0] is raw:
            raw_cell[0] = result.unset
        if (type(snapshot_cell) is list and len(snapshot_cell) == 1
                and snapshot_cell[0] is snapshot):
            snapshot_cell[0] = None
        if (type(envelope_cell) is list and len(envelope_cell) == 1
                and envelope_cell[0] is actual):
            envelope_cell[0] = None
        if (type(category_cell) is list and len(category_cell) == 1
                and category_cell[0] is category):
            category_cell[0] = None
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
        missing = number = filename = None
        error_number = error_filename = missing_type = enoent = None
        origin = marker = payload = cells = joined_cells = None
        raw_cell = category_cell = snapshot_cell = envelope_cell = None
    raise ArtifactObservationError(owner) from None


class _DirectoryPolicyCommit(NamedTuple):
    owner: object
    operation: _MetadataOperation
    consumer: _DirectoryConsumer
    resource: _NativeMetadataResource
    site: tuple
    ordinal: int
    next_ordinal: int
    identity: tuple
    mtime: int | float | None = None

    def __repr__(self):
        return '<DirectoryPolicyCommit prepared original DATA redacted>'


def _consuming_directory_return_tail(owner, consumer, actual):
    _pending_directory_cohort_tail(owner, consumer, actual)
    _require(consumer.consumption[0] is actual and consumer.commit[0] is None
             and actual.result.acknowledged[0] is None)
    return actual


def _directory_commit_cohort_tail(owner, consumer, actual, commit):
    if type(consumer) is _ProbeConsumer:
        function = _probe_policy_helper(owner, consumer, '_commit_shared_tail')
        return function(owner, consumer, actual, commit)
    _pending_directory_cohort_tail(owner, consumer, actual)
    _require(type(commit) is _DirectoryPolicyCommit and commit.owner is owner
             and commit.operation is actual.operation and commit.consumer is consumer
             and commit.resource is consumer.resource
             and commit.site is consumer.resource.site
             and commit.ordinal is consumer.resource.ordinal
             and type(commit.next_ordinal) is int
             and commit.next_ordinal == commit.ordinal + 1
             and commit.next_ordinal <= len(consumer.resource.metadata.definitions)
             and type(commit.identity) is tuple
             and len(commit.identity) == _fixed_metadata_identity_size(consumer.resource)
             and all(type(value) is int for value in commit.identity)
             and type(actual.snapshot.identity) is tuple
             and len(actual.snapshot.identity) == 9
             and all(type(value) is int for value in actual.snapshot.identity)
             and all(commit.identity[index] == actual.snapshot.identity[index]
                     for index in range(_fixed_metadata_identity_size(consumer.resource)))
             and consumer.consumption[0] is actual and consumer.commit[0] is commit)
    _require((commit.mtime is None if _fixed_metadata_role(consumer.resource) in ('directory', 'directory_after_hash')
              else type(commit.mtime) in (int, float)
              and commit.mtime is actual.snapshot.mtime))
    return commit


def _prepared_directory_commit_tail(owner, consumer, actual, commit):
    _directory_commit_cohort_tail(owner, consumer, actual, commit)
    _require(actual.result.acknowledged[0] is None)
    return commit


def _consume_directory_policy(owner, consumer, actual):
    """Consume one original pending result into a fixed policy commit; not ACK.

    Pending raw storage remains owned until a separate fixed ACK retires it.
    A clean wrong actor leaves the original result available to its owner.
    Drift fails closed, preserving debt and retiring only held original data.
    """
    verified = actor_mismatch = False
    operation = result = ledger = phase = category = None
    actor_state = actor_arguments = identity = commit = None
    try:
        _pending_directory_return_tail(owner, consumer, actual)
        operation = actual.operation
        result, ledger, phase = operation.result, operation.ledger, operation.phase
        category = result.category[0]
        verified = True
        consumer.consumption[0] = actual
        actor_arguments = (consumer, actual, operation)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        try:
            _native_actor_context(operation.native.actor_calls,
                                  (operation.native.native, operation.native.thread_native),
                                  operation.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        _native_post_actor_state(owner, actor_state, actor_arguments)
        _consuming_directory_return_tail(owner, consumer, actual)
        if type(consumer) is _ProbeConsumer:
            make_commit = _probe_policy_helper(owner, consumer, '_make_shared_commit')
            commit = make_commit(owner, consumer, actual)
        else:
            resource = consumer.resource
            if _fixed_metadata_role(resource) in ('directory', 'directory_after_hash'):
                identity = _directory_identity(actual.snapshot, operation.context[1])
                mtime = None
                if _fixed_metadata_role(resource) == 'directory_after_hash':
                    _require(identity == consumer.baseline.identity)
            else:
                identity = _declared_leaf_identity(actual.snapshot, operation.context[1],
                                                    resource.variant.expected.size)
                # Preserve the same actual result's primitive timestamp. Conditional
                # source-effect conversion stays with the complete walker integration.
                mtime = actual.snapshot.mtime
                if _fixed_metadata_role(resource) == 'leaf_opened':
                    # This is the literal preceding caller return, not a new baseline
                    # sampled from current history or the newly opened descriptor.
                    predecessor = consumer.predecessor
                    _require(type(predecessor) is _DirectoryPolicyCommit
                             and type(predecessor.identity) is tuple
                             and len(predecessor.identity) == 9
                             and all(type(value) is int for value in predecessor.identity)
                             and identity == predecessor.identity)
                elif _fixed_metadata_role(resource) == 'leaf_after_read':
                    _require(identity == consumer.baseline.identity)
            _consuming_directory_return_tail(owner, consumer, actual)
            commit = _DirectoryPolicyCommit(owner, operation, consumer, resource, resource.site,
                                             resource.ordinal, resource.ordinal + 1, identity, mtime)
            _consuming_directory_return_tail(owner, consumer, actual)
        _consuming_directory_return_tail(owner, consumer, actual)
        consumer.commit[0] = commit
        _require(_prepared_directory_commit_tail(owner, consumer, actual, commit) is commit)
        return commit
    except BaseException:
        clean_mismatch = False
        if verified and actor_mismatch:
            try:
                _native_post_actor_state(owner, actor_state, actor_arguments)
                _consuming_directory_return_tail(owner, consumer, actual)
                clean_mismatch = True
            except BaseException:
                clean_mismatch = False
        if clean_mismatch:
            consumer.consumption[0] = None  # no policy was consumed, no new IO/debit
        elif verified:
            if type(operation.state) is list and len(operation.state) == 3:
                operation.state[2] = True
            if type(ledger.failed) is list and len(ledger.failed) == 1:
                ledger.failed[0] = True
            if (type(ledger.failure) is list and len(ledger.failure) == 1
                    and ledger.failure[0] is None):
                ledger.failure[0] = operation
            if type(result.raw) is list and len(result.raw) == 1 and result.raw[0] is actual.raw:
                result.raw[0] = result.unset
            if (type(result.snapshot) is list and len(result.snapshot) == 1
                    and result.snapshot[0] is actual.snapshot):
                result.snapshot[0] = None
            if (type(result.envelope) is list and len(result.envelope) == 1
                    and result.envelope[0] is actual):
                result.envelope[0] = None
            if (type(result.category) is list and len(result.category) == 1
                    and result.category[0] is category):
                result.category[0] = None
            if (type(consumer.consumption) is list and len(consumer.consumption) == 1
                    and consumer.consumption[0] is actual):
                consumer.consumption[0] = operation
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.pending or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
            if (type(phase.result) is list and len(phase.result) == 1
                    and phase.result[0] is operation):
                phase.result[0] = None
    finally:
        actual = None
        actor_state = actor_arguments = identity = commit = None
        operation = result = ledger = phase = consumer = None
    raise ArtifactObservationError(owner) from None


def _directory_ack_preparation_tail(owner, consumer, actual, commit):
    _directory_commit_cohort_tail(owner, consumer, actual, commit)
    _require(actual.result.acknowledged[0] is commit)
    return commit


def _acked_directory_history_tail(owner, consumer, commit):
    """Raw-free ACK history closure; not admission or a returned-receipt proof."""
    if type(consumer) is _ProbeConsumer:
        function = _probe_policy_helper(owner, consumer, '_acked_shared_history')
        return function(owner, consumer, commit)
    _require(type(consumer) is _DirectoryConsumer and consumer.owner is owner
             and type(commit) is _DirectoryPolicyCommit and commit.owner is owner
             and commit.consumer is consumer and commit.operation is consumer.operation
             and type(consumer.operation) is _MetadataOperation
             and type(consumer.resource) is _NativeMetadataResource
             and commit.resource is consumer.resource
             and consumer.operation.resource is consumer.resource)
    operation, resource = consumer.operation, consumer.resource
    registration, result = operation.registration, operation.result
    _require(operation.owner is owner and resource.owner is owner
             and resource.registration is registration)
    _native_work_origin_tail(owner, registration, operation.native)
    _require(operation.context is registration.context
             and type(operation.operation) is int and operation.operation in (3, 4)
             and operation.callee is operation.native.operations[operation.operation]
             and operation.operation == resource.site[0]
             and operation.arguments is resource.arguments
             and type(operation.arguments) is tuple
             and len(operation.arguments) == (1 if operation.operation == 4 else 2)
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and resource.site[0] in (3, 4)
             and _fixed_metadata_role(resource) in ('directory', 'leaf_before', 'leaf_opened', 'leaf_after_read', 'directory_after_hash')
             and type(resource.site[2]) is int)
    metadata = _native_declared_metadata_cohort_tail(owner, registration, resource.held_walk)
    _directory_predecessors_tail(owner, consumer)
    _require(type(commit.ordinal) is int
             and 0 <= commit.ordinal < len(metadata.definitions)
             and type(commit.next_ordinal) is int
             and commit.next_ordinal == commit.ordinal + 1
             and len(consumer.history) == commit.next_ordinal
             and consumer.history[commit.ordinal] is commit)
    _require(metadata is resource.metadata and type(commit.ordinal) is int
             and 0 <= commit.ordinal < len(metadata.definitions)
             and commit.ordinal is resource.ordinal and commit.site is resource.site
             and metadata.definitions[commit.ordinal] is commit.site
             and type(commit.next_ordinal) is int
             and commit.next_ordinal == commit.ordinal + 1
             and metadata.progress[0] is commit.next_ordinal
             and metadata.progress[1] is None
             and type(commit.identity) is tuple
             and len(commit.identity) == _fixed_metadata_identity_size(consumer.resource)
             and all(type(value) is int for value in commit.identity)
             and (commit.mtime is None if _fixed_metadata_role(resource) in ('directory', 'directory_after_hash')
                  else type(commit.mtime) in (int, float))
             and type(result) is _MetadataResult
             and type(result.attempt) is list and len(result.attempt) == 1
             and result.attempt[0] is operation
             and type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is consumer
             and type(result.acknowledged) is list and len(result.acknowledged) == 1
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and result.acknowledged[0] is consumer.commit[0] is commit
             and type(operation.state) is list and len(operation.state) == 3
             and operation.state[0] is True and operation.state[1] is True
             and operation.state[2] is False
             and type(operation.ended) is list and len(operation.ended) == 1
             and operation.ended[0] is True)
    ledger, phase = operation.ledger, operation.phase
    _require(ledger is registration.native_ledger and phase is registration.native_phase
             and ledger.phase is phase and type(operation.attempts) is list
             and ledger.attempts is operation.attempts and type(operation.index) is int
             and 0 <= operation.index < len(operation.attempts)
             and operation.attempts[operation.index] is operation
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(value) is int for value in ledger.counts)
             and all(type(value) is int for value in operation.budget[1:])
             and operation.budget[3] == operation.budget[1] + 1
             and 0 <= operation.budget[1] < 1048576
             and 0 <= ledger.counts[1] < 1048576 - operation.budget[1]
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and ledger.inflight[0] is None
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False
             and type(ledger.failure) is list and len(ledger.failure) == 1
             and ledger.failure[0] is None
             and type(phase.current) is list and len(phase.current) == 1
             and phase.current[0] is phase.idle
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is None)
    _require(_fixed_metadata_resource_tail(owner, resource) is resource
             and _directory_material_tail(owner, consumer) is consumer)
    _native_read_lifecycle_tail(owner, registration, consumer.parents)
    _native_work_origin_tail(owner, registration, operation.native)
    _directory_predecessors_tail(owner, consumer)
    _require(type(commit.ordinal) is int
             and 0 <= commit.ordinal < len(metadata.definitions)
             and type(commit.next_ordinal) is int
             and commit.next_ordinal == commit.ordinal + 1
             and len(consumer.history) == commit.next_ordinal
             and consumer.history[commit.ordinal] is commit)
    return commit



def _acked_directory_commit_tail(owner, consumer, commit):
    """Original closed ACK with its still-attached, already cleared payload."""
    _acked_directory_history_tail(owner, consumer, commit)
    result = consumer.operation.result
    _require(all(type(cell) is list and len(cell) == 1 for cell in
                 (result.raw, result.category, result.snapshot,
                  result.envelope, consumer.consumption))
             and result.raw[0] is result.unset
             and result.category[0] is result.snapshot[0] is result.envelope[0] is None
             and consumer.consumption[0] is commit)
    # Payload getters include descriptor/weakref joins; close live history again.
    return _acked_directory_history_tail(owner, consumer, commit)


def _retired_directory_commit_tail(owner, consumer, commit, origin, marker, record):
    """Closed ACK plus actual caller-held retirement DATA, never a native ACK.

    The fixed caller must hold the actual commit and retirement allocation, clear its
    payload/cell/envelope aliases, then use this tail before any further work.
    Neither a current record lookup nor constructing matching DATA is a receipt.
    """
    _acked_directory_history_tail(owner, consumer, commit)
    _origin_tail(origin)
    operation = consumer.operation
    result = operation.result
    _require(type(marker) is origin.marker_type and marker.owner is owner
             and marker.operation is operation and marker.consumer is None
             and marker.origin is origin and result.custody_origin is origin
             and type(marker.owner_link) is list and len(marker.owner_link) == 1
             and result.custody_link is marker.owner_link and marker.owner_link[0] is None
             and type(marker.marker_slot) is list and len(marker.marker_slot) == 1
             and result.custody_slot is marker.marker_slot and marker.marker_slot[0] is marker
             and type(marker.state) is list and len(marker.state) == 3
             and marker.state[0] is True and marker.state[1] is True and marker.state[2] is False
             and type(record) is origin.record_type and record.marker is marker
             and record.detached is True and record.unmatched_link is False
             and record.unmatched_marker is False
             and type(marker.reference) is origin.reference_type
             and origin.reference_callback.__get__(marker.reference, origin.reference_type) is None
             and origin.reference_call(marker.reference) is None)
    # Disposal may have run finalizers; no payload reads or weakref calls after
    # this live material/registration/lifecycle/native/budget/history closure.
    _acked_directory_history_tail(owner, consumer, commit)
    _require(result.custody_origin is origin and result.custody_link is marker.owner_link
             and marker.owner_link[0] is None and result.custody_slot is marker.marker_slot
             and marker.marker_slot[0] is marker and marker.state[0] is True
             and marker.state[1] is True and marker.state[2] is False
             and record.marker is marker and record.detached is True
             and record.unmatched_link is False and record.unmatched_marker is False)
    return commit


def _ack_directory_policy(owner, consumer, actual, commit):
    """Retire one actual prepared directory result and advance its original site.

    The caller holds the actual producer return and commit through final closure.
    Partial ACK/debit history is never rolled back or replayed on failure.
    """
    verified = actor_mismatch = False
    operation = result = ledger = phase = category = None
    actor_state = actor_arguments = None
    try:
        _prepared_directory_commit_tail(owner, consumer, actual, commit)
        operation = actual.operation
        result, ledger, phase = operation.result, operation.ledger, operation.phase
        category = result.category[0]
        verified = True
        result.acknowledged[0] = commit
        actor_arguments = (consumer, actual, commit)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        try:
            _native_actor_context(operation.native.actor_calls,
                                  (operation.native.native, operation.native.thread_native),
                                  operation.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        _native_post_actor_state(owner, actor_state, actor_arguments)
        _directory_ack_preparation_tail(owner, consumer, actual, commit)
        result.raw[0] = result.unset
        result.snapshot[0] = None
        result.envelope[0] = None
        result.category[0] = None
        consumer.consumption[0] = commit  # retire the raw-bearing backlink too
        if type(consumer) is _ProbeConsumer:
            publish = _probe_policy_helper(owner, consumer, '_publish_shared_ack')
            publish(owner, consumer, commit)
        else:
            consumer.history.append(commit)  # actual ACK, retained without the native payload
            consumer.resource.metadata.progress[0] = commit.next_ordinal
            consumer.resource.metadata.progress[1] = None
        phase.result[0] = None
        phase.current[0] = phase.idle
        _require(_acked_directory_commit_tail(owner, consumer, commit) is commit)
        return commit
    except BaseException:
        clean_mismatch = False
        if verified and actor_mismatch:
            try:
                _native_post_actor_state(owner, actor_state, actor_arguments)
                _directory_ack_preparation_tail(owner, consumer, actual, commit)
                clean_mismatch = True
            except BaseException:
                clean_mismatch = False
        if clean_mismatch:
            result.acknowledged[0] = None  # no ACK retired any original data
        elif verified:
            if type(operation.state) is list and len(operation.state) == 3:
                operation.state[2] = True
            if type(ledger.failed) is list and len(ledger.failed) == 1:
                ledger.failed[0] = True
            if (type(ledger.failure) is list and len(ledger.failure) == 1
                    and ledger.failure[0] is None):
                ledger.failure[0] = operation
            if type(result.raw) is list and len(result.raw) == 1 and result.raw[0] is actual.raw:
                result.raw[0] = result.unset
            if (type(result.snapshot) is list and len(result.snapshot) == 1
                    and result.snapshot[0] is actual.snapshot):
                result.snapshot[0] = None
            if (type(result.envelope) is list and len(result.envelope) == 1
                    and result.envelope[0] is actual):
                result.envelope[0] = None
            if (type(result.category) is list and len(result.category) == 1
                    and result.category[0] is category):
                result.category[0] = None
            if (type(consumer.consumption) is list and len(consumer.consumption) == 1
                    and consumer.consumption[0] is actual):
                consumer.consumption[0] = commit
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.pending or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
            if (type(phase.result) is list and len(phase.result) == 1
                    and phase.result[0] is operation):
                phase.result[0] = None
    finally:
        actual = commit = consumer = None
        actor_state = actor_arguments = None
        operation = result = ledger = phase = None
    raise ArtifactObservationError(owner) from None


def _release_ended_directory_preparation(owner, consumer):
    """Release only an original ended, uncharged, raw-empty preparation.

    No descriptor operation, actor resample, refund or intent rearming occurs.
    This permits rightful-owner preparation after a clean actor refusal; it
    cannot retire an admitted, returned, failed or pending native operation.
    """
    resource = _latched_directory_resource_tail(owner, consumer)
    operation = consumer.operation
    result = _undebited_directory_cells_tail(owner, operation)
    ledger, phase = operation.ledger, operation.phase
    _require(operation.ended[0] is True
             and phase.current[0] is phase.idle and phase.result[0] is None
             and ledger.inflight[0] is None
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.commit) is list and len(consumer.commit) == 1
             and consumer.commit[0] is None
             and type(result.consumer) is list and len(result.consumer) == 1
             and result.consumer[0] is consumer)
    metadata = resource.metadata
    _require(metadata.progress[0] is resource.ordinal and metadata.progress[1] is consumer
             and _directory_material_tail(owner, consumer) is consumer)
    try:
        consumer.consumption[0] = operation  # preserve this ended preparation's history
        metadata.progress[1] = None
        _require(_native_declared_metadata_plan_tail(owner, resource.registration,
                                                     resource.held_walk) is metadata
                 and metadata.progress[0] is resource.ordinal and metadata.progress[1] is None
                 and _undebited_directory_cells_tail(owner, operation) is result
                 and consumer.consumption[0] is operation and consumer.commit[0] is None
                 and result.consumer[0] is consumer
                 and phase.current[0] is phase.idle and phase.result[0] is None
                 and ledger.inflight[0] is None
                 and _directory_material_tail(owner, consumer) is consumer)
        _native_read_lifecycle_tail(owner, resource.registration, consumer.parents)
        _require(_undebited_directory_cells_tail(owner, operation) is result
                 and operation.ended[0] is True
                 and metadata.progress[0] is resource.ordinal and metadata.progress[1] is None
                 and consumer.consumption[0] is operation and consumer.commit[0] is None
                 and phase.current[0] is phase.idle and phase.result[0] is None
                 and ledger.inflight[0] is None)
        return consumer
    except BaseException:
        if type(operation.state) is list and len(operation.state) == 3:
            operation.state[2] = True
        if type(ledger.failed) is list and len(ledger.failed) == 1:
            ledger.failed[0] = True
        if (type(ledger.failure) is list and len(ledger.failure) == 1
                and ledger.failure[0] is None):
            ledger.failure[0] = operation
        if (type(phase.current) is list and len(phase.current) == 1
                and phase.current[0] is phase.idle):
            phase.current[0] = phase.failed
    finally:
        consumer = operation = result = resource = metadata = ledger = phase = None
    raise ArtifactObservationError(owner) from None


def _abandon_known_directory_return(owner, consumer, actual, commit=None):
    """Abort only a caller-held original unACKed return under its live cohort.

    Optional commit is the caller's actual prepared policy return, never a row
    adopted from current storage. No native work, close, refund, cursor advance
    or ACK occurs. Lost producer return/revoked lifetime need separate handling.
    """
    verified = False
    operation = result = ledger = phase = category = None
    actor_state = actor_arguments = None
    try:
        if commit is None:
            _pending_directory_return_tail(owner, consumer, actual)
        else:
            _prepared_directory_commit_tail(owner, consumer, actual, commit)
        operation = actual.operation
        result, ledger, phase = operation.result, operation.ledger, operation.phase
        category = result.category[0]
        actor_arguments = (consumer, actual, commit)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        _native_actor_context(operation.native.actor_calls,
                              (operation.native.native, operation.native.thread_native),
                              operation.context)
        _native_post_actor_state(owner, actor_state, actor_arguments)
        if commit is None:
            _pending_directory_return_tail(owner, consumer, actual)
        else:
            _prepared_directory_commit_tail(owner, consumer, actual, commit)
        verified = True
        operation.state[2] = True
        ledger.failed[0] = True
        if ledger.failure[0] is None:
            ledger.failure[0] = operation
        if result.raw[0] is actual.raw:
            result.raw[0] = result.unset
        if result.snapshot[0] is actual.snapshot:
            result.snapshot[0] = None
        if result.envelope[0] is actual:
            result.envelope[0] = None
        if result.category[0] is category:
            result.category[0] = None
        if consumer.consumption[0] is actual:
            consumer.consumption[0] = operation
        if phase.result[0] is operation:
            phase.result[0] = None
        if phase.current[0] is phase.pending or phase.current[0] is phase.idle:
            phase.current[0] = phase.failed
        _require(operation.state[0] is True and operation.state[1] is True
                 and operation.state[2] is True and operation.ended[0] is True
                 and ledger.failed[0] is True and ledger.failure[0] is operation
                 and ledger.inflight[0] is None
                 and phase.current[0] is phase.failed and phase.result[0] is None
                 and result.raw[0] is result.unset
                 and result.snapshot[0] is result.envelope[0] is result.category[0] is None
                 and result.acknowledged[0] is None
                 and consumer.commit[0] is commit
                 and consumer.consumption[0] is (None if commit is None else operation)
                 and consumer.resource.metadata.progress[0] is consumer.resource.ordinal
                 and consumer.resource.metadata.progress[1] is consumer
                 and ledger.counts is operation.budget[0]
                 and ledger.counts[0] is operation.budget[3]
                 and ledger.counts[1] is operation.budget[2]
                 and ledger.attempts is operation.attempts
                 and ledger.attempts[operation.index] is operation)
        return None
    except BaseException:
        if verified:
            if type(operation.state) is list and len(operation.state) == 3:
                operation.state[2] = True
            if type(ledger.failed) is list and len(ledger.failed) == 1:
                ledger.failed[0] = True
            if (type(ledger.failure) is list and len(ledger.failure) == 1
                    and ledger.failure[0] is None):
                ledger.failure[0] = operation
            if type(result.raw) is list and len(result.raw) == 1 and result.raw[0] is actual.raw:
                result.raw[0] = result.unset
            if (type(result.snapshot) is list and len(result.snapshot) == 1
                    and result.snapshot[0] is actual.snapshot):
                result.snapshot[0] = None
            if (type(result.envelope) is list and len(result.envelope) == 1
                    and result.envelope[0] is actual):
                result.envelope[0] = None
            if (type(result.category) is list and len(result.category) == 1
                    and result.category[0] is category):
                result.category[0] = None
            if (type(consumer.consumption) is list and len(consumer.consumption) == 1
                    and consumer.consumption[0] is actual):
                consumer.consumption[0] = operation
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.pending or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
            if (type(phase.result) is list and len(phase.result) == 1
                    and phase.result[0] is operation):
                phase.result[0] = None
    finally:
        actual = commit = consumer = None
        actor_state = actor_arguments = None
        operation = result = ledger = phase = None
    raise ArtifactObservationError(owner) from None




def _finished_capsule_mirrors_tail(owner, commit):
    """Confirm the before-effect custody pinned in this actual returned commit."""
    _require(type(commit) is _DirectoryPolicyCommit
             and type(commit.consumer) is _DirectoryConsumer
             and commit.consumer.owner is owner
             and type(commit.operation) is _MetadataOperation
             and type(commit.operation.result) is _MetadataResult
             and type(commit.consumer.custody) is tuple and len(commit.consumer.custody) == 6)
    origin, marker, link, slot, state, reference = commit.consumer.custody
    _require(type(origin) is _PayloadOrigin)
    result = commit.operation.result
    _require(type(marker) is origin.marker_type and marker.owner is owner
             and marker.operation is commit.operation and marker.origin is origin
             and marker.consumer is None and result.custody_origin is origin
             and type(link) is list and len(link) == 1 and link[0] is None
             and result.custody_link is marker.owner_link is link
             and type(slot) is list and len(slot) == 1 and slot[0] is marker
             and result.custody_slot is marker.marker_slot is slot
             and marker.state is state and type(state) is list and len(state) == 3
             and state[0] is True and state[1] is True and state[2] is False
             and marker.reference is reference and type(reference) is origin.reference_type
             and type(origin) is _PayloadOrigin)
    return commit


def _finished_capsule_tail(owner, commit):
    """Observe original weak death; the caller must seal all mirrors afterward."""
    _require(type(commit) is _DirectoryPolicyCommit
             and type(commit.consumer) is _DirectoryConsumer
             and type(commit.consumer.custody) is tuple and len(commit.consumer.custody) == 6)
    origin, marker, link, slot, state, reference = commit.consumer.custody
    _origin_tail(origin)
    _require(type(reference) is origin.reference_type
             and origin.reference_callback.__get__(reference, origin.reference_type) is None
             and origin.reference_call(reference) is None)
    return commit


def _finished_declared_file_mirrors_tail(owner, registration, held, last):
    """Literal final pre-close return, complete history, and actual owned closes.

    The fixed file caller holds the last observation's actual return across all
    cleanup. Current mirrors only confirm it; none nominates a finish receipt.
    This is not a replacement baseline, a current FD-open check or new work.
    """
    _require(type(last) is _DirectoryPolicyCommit and last.owner is owner
             and type(last.consumer) is _DirectoryConsumer
             and type(last.operation) is _MetadataOperation
             and type(last.resource) is _NativeMetadataResource
             and last.resource.registration is registration
             and last.resource.held_walk is held)
    resource, consumer = last.resource, last.consumer
    metadata = _native_declared_metadata_cohort_tail(owner, registration, held)
    _require(resource.metadata is metadata and consumer.resource is resource
             and consumer.operation is last.operation
             and consumer.history is metadata.commits
             and type(metadata.definitions) is tuple and len(metadata.definitions) > 0
             and metadata.progress[0] == len(metadata.definitions)
             and metadata.progress[1] is None
             and len(metadata.commits) == len(metadata.definitions)
             and type(last.ordinal) is int and type(last.next_ordinal) is int
             and last.ordinal == len(metadata.definitions) - 1
             and last.next_ordinal == len(metadata.definitions)
             and metadata.commits[-1] is last
             and last.site is metadata.definitions[-1]
             and last.site[0] == 3 and last.site[1] == 'directory_after_hash')
    _metadata_predecessor_chain_tail(owner, consumer)
    for ordinal, actual in enumerate(metadata.commits):
        _require(type(actual) is _DirectoryPolicyCommit and actual.owner is owner
                 and type(actual.resource) is _NativeMetadataResource
                 and type(actual.operation) is _MetadataOperation
                 and type(actual.operation.result) is _MetadataResult
                 and type(actual.consumer) is _DirectoryConsumer
                 and type(actual.ordinal) is int and type(actual.next_ordinal) is int
                 and actual.ordinal == ordinal and actual.next_ordinal == ordinal + 1
                 and actual.site is metadata.definitions[ordinal]
                 and actual.resource.metadata is metadata
                 and actual.resource.held_walk is held
                 and actual.operation.owner is owner
                 and actual.operation.resource is actual.resource
                 and actual.consumer.operation is actual.operation
                 and actual.consumer.resource is actual.resource
                 and type(actual.consumer.commit) is list and len(actual.consumer.commit) == 1
                 and actual.consumer.commit[0] is actual
                 and type(actual.operation.result.acknowledged) is list
                 and len(actual.operation.result.acknowledged) == 1
                 and actual.operation.result.acknowledged[0] is actual
                 and type(actual.operation.ended) is list and len(actual.operation.ended) == 1
                 and actual.operation.ended[0] is True
                 and type(actual.operation.state) is list and len(actual.operation.state) == 3
                 and all(type(value) is bool for value in actual.operation.state)
                 and actual.operation.state == [True, True, False])
        _finished_capsule_mirrors_tail(owner, actual)
    eof = consumer.eof
    if consumer.class_name == 'RuntimeSourceReadOwner':
        _require(type(eof) is _NativeRuntimeReadCommit)
        _require(_native_runtime_read_receipt_mirrors_tail(owner, eof, eof.step) is eof)
    else:
        _require(consumer.class_name == 'DeclaredCacheReadOwner'
                 and type(eof) is _NativeCacheReadCommit)
        _require(_native_cache_read_receipt_mirrors_tail(owner, eof, eof.step) is eof)
    _require(eof.eof is True and eof.remaining == 0 and eof.step.walk is held[0]
             and eof.step.expected is metadata.expected)
    descriptor = eof.step.descriptor
    for _ in held[0].components:
        _require(type(descriptor) is _NativeOpenedDescriptor)
        _require(_native_descriptor_closed(descriptor, registration.native_ledger))
        descriptor = descriptor.allocation.parent
    _require(descriptor is None)
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(last.operation.ledger is ledger
             and ledger.attempts[last.operation.index] is last.operation
             and len(ledger.attempts) == last.operation.index + 1
             and ledger.counts[0] == last.operation.budget[3] + len(held[0].components)
             and ledger.counts[1] == last.operation.budget[2] - len(held[0].components)
             and ledger.failed[0] is False and ledger.failure[0] is None
             and ledger.inflight[0] is None and phase.current[0] is phase.idle
             and phase.result[0] is None)
    _native_read_walk_mirrors_tail(owner, registration, eof.step.walk, eof.step.expected, eof.step)
    _native_read_lifecycle_mirrors_tail(owner, registration, consumer.parents)
    # Rejoin literal finish and complete cursor after callback-bearing closure.
    _require(resource.held_walk is held and resource.metadata is metadata
             and metadata.commits[-1] is last and consumer.eof is eof
             and metadata.progress[0] == len(metadata.definitions)
             and metadata.progress[1] is None
             and ledger.counts[0] == last.operation.budget[3] + len(held[0].components)
             and ledger.counts[1] == last.operation.budget[2] - len(held[0].components)
             and ledger.failed[0] is False and ledger.inflight[0] is None)
    return last


def _finished_declared_file_tail(owner, registration, held, last):
    """Literal final pre-close return, complete history, and actual owned closes.

    The fixed file caller holds the last observation's actual return across all
    cleanup. Current mirrors only confirm it; none nominates a finish receipt.
    This is not a replacement baseline, a current FD-open check or new work.
    """
    _require(type(last) is _DirectoryPolicyCommit and last.owner is owner
             and type(last.consumer) is _DirectoryConsumer
             and type(last.operation) is _MetadataOperation
             and type(last.resource) is _NativeMetadataResource
             and last.resource.registration is registration
             and last.resource.held_walk is held)
    resource, consumer = last.resource, last.consumer
    metadata = _native_declared_metadata_cohort_tail(owner, registration, held)
    _require(resource.metadata is metadata and consumer.resource is resource
             and consumer.operation is last.operation
             and consumer.history is metadata.commits
             and type(metadata.definitions) is tuple and len(metadata.definitions) > 0
             and metadata.progress[0] == len(metadata.definitions)
             and metadata.progress[1] is None
             and len(metadata.commits) == len(metadata.definitions)
             and type(last.ordinal) is int and type(last.next_ordinal) is int
             and last.ordinal == len(metadata.definitions) - 1
             and last.next_ordinal == len(metadata.definitions)
             and metadata.commits[-1] is last
             and last.site is metadata.definitions[-1]
             and last.site[0] == 3 and last.site[1] == 'directory_after_hash')
    _metadata_predecessor_chain_tail(owner, consumer)
    for ordinal, actual in enumerate(metadata.commits):
        _require(type(actual) is _DirectoryPolicyCommit and actual.owner is owner
                 and type(actual.resource) is _NativeMetadataResource
                 and type(actual.operation) is _MetadataOperation
                 and type(actual.operation.result) is _MetadataResult
                 and type(actual.consumer) is _DirectoryConsumer
                 and type(actual.ordinal) is int and type(actual.next_ordinal) is int
                 and actual.ordinal == ordinal and actual.next_ordinal == ordinal + 1
                 and actual.site is metadata.definitions[ordinal]
                 and actual.resource.metadata is metadata
                 and actual.resource.held_walk is held
                 and actual.operation.owner is owner
                 and actual.operation.resource is actual.resource
                 and actual.consumer.operation is actual.operation
                 and actual.consumer.resource is actual.resource
                 and type(actual.consumer.commit) is list and len(actual.consumer.commit) == 1
                 and actual.consumer.commit[0] is actual
                 and type(actual.operation.result.acknowledged) is list
                 and len(actual.operation.result.acknowledged) == 1
                 and actual.operation.result.acknowledged[0] is actual
                 and type(actual.operation.ended) is list and len(actual.operation.ended) == 1
                 and actual.operation.ended[0] is True
                 and type(actual.operation.state) is list and len(actual.operation.state) == 3
                 and all(type(value) is bool for value in actual.operation.state)
                 and actual.operation.state == [True, True, False])
        _finished_capsule_tail(owner, actual)
    eof = consumer.eof
    if consumer.class_name == 'RuntimeSourceReadOwner':
        _require(type(eof) is _NativeRuntimeReadCommit)
        _require(_native_runtime_read_receipt_state_tail(owner, eof, eof.step) is eof)
    else:
        _require(consumer.class_name == 'DeclaredCacheReadOwner'
                 and type(eof) is _NativeCacheReadCommit)
        _require(_native_cache_read_receipt_state_tail(owner, eof, eof.step) is eof)
    _require(eof.eof is True and eof.remaining == 0 and eof.step.walk is held[0]
             and eof.step.expected is metadata.expected)
    descriptor = eof.step.descriptor
    for _ in held[0].components:
        _require(type(descriptor) is _NativeOpenedDescriptor)
        _require(_native_descriptor_closed(descriptor, registration.native_ledger))
        descriptor = descriptor.allocation.parent
    _require(descriptor is None)
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(last.operation.ledger is ledger
             and ledger.attempts[last.operation.index] is last.operation
             and len(ledger.attempts) == last.operation.index + 1
             and ledger.counts[0] == last.operation.budget[3] + len(held[0].components)
             and ledger.counts[1] == last.operation.budget[2] - len(held[0].components)
             and ledger.failed[0] is False and ledger.failure[0] is None
             and ledger.inflight[0] is None and phase.current[0] is phase.idle
             and phase.result[0] is None)
    _require(_directory_material_tail(owner, consumer) is consumer)
    _native_read_lifecycle_tail(owner, registration, consumer.parents)
    _native_work_origin_tail(owner, registration, registration.native_origin)
    # Rejoin literal finish and complete cursor after callback-bearing closure.
    _require(resource.held_walk is held and resource.metadata is metadata
             and metadata.commits[-1] is last and consumer.eof is eof
             and metadata.progress[0] == len(metadata.definitions)
             and metadata.progress[1] is None
             and ledger.counts[0] == last.operation.budget[3] + len(held[0].components)
             and ledger.counts[1] == last.operation.budget[2] - len(held[0].components)
             and ledger.failed[0] is False and ledger.inflight[0] is None)
    _require(_finished_declared_file_mirrors_tail(owner, registration, held, last) is last)
    return last


def _run_directory_observation(owner, resource, predecessor=None, baseline=None, eof=None):
    """Shared fixed-policy caller with pre-effect independent memory custody.

    Only the actual factory/producer/policy/ACK returns are used. Cleanup is
    memory-only after the fixed synchronous producer has unwound; it never
    consults a current envelope as a receipt, closes an FD, refunds or retries.
    A successful return is the actual closed commit, with its payload gone.
    """
    operation = marker = payload = origin = result = consumer = None
    held_link = held_slot = held_state = held_reference = None
    actual = commit = acked = record = None
    actor_state = actor_arguments = None
    producer_started = producer_unwound = complete = retired = False
    # Retain these fixed function references across preparation callbacks. This
    # is not a caller-selected dispatcher or a new admission surface.
    probe_origin = probe_stages = None
    prepare, latch, produce, consume, acknowledge, attached_tail, retired_tail = (
        _prepare_directory_consumer, _latch_directory_consumer,
        _produce_directory_metadata, _consume_directory_policy, _ack_directory_policy,
        _acked_directory_commit_tail, _retired_directory_commit_tail)
    if type(resource) in (_NativeProbeMetadataResource, _NativeStartupProbeMetadataResource):
        _require(baseline is None and eof is None)
        probe_stages = _probe_stage_functions(owner, resource)
        probe_origin = _closed_probe_engine_origin(owner, resource)
        prepare, latch, produce, consume, acknowledge, attached_tail, retired_tail = probe_stages
    try:
        # Reject a foreign actor before allocating/latching caller-owned custody.
        # This is eligibility only: the producer still samples the actor at its
        # original ACTIVE admission boundary immediately before native effects.
        _resource_tail(owner, resource)
        registration = resource.registration
        native = registration.native_origin
        actor_arguments = (resource, registration, predecessor, baseline, eof)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                              registration.context)
        _native_post_actor_state(owner, actor_state, actor_arguments)
        _require(_resource_tail(owner, resource) is resource
                 and resource.registration is registration
                 and registration.native_origin is native)
        actor_state = actor_arguments = None
        operation, marker, payload = _prepare_metadata_operation_with_custody(owner, resource)
        result, origin = operation.result, operation.result.custody_origin
        _marker_tail(owner, origin, marker, payload)
        _require(marker.operation is operation and marker.consumer is None
                 and result.custody_link is marker.owner_link
                 and result.custody_slot is marker.marker_slot)
        held_link, held_slot = marker.owner_link, marker.marker_slot
        held_state, held_reference = marker.state, marker.reference
        custody = (origin, marker, held_link, held_slot, held_state, held_reference)
        if probe_stages is not None:
            _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
        consumer = prepare(owner, operation, predecessor, baseline, eof, custody)
        _require(consumer.predecessor is predecessor
             and consumer.baseline is baseline and consumer.eof is eof
             and consumer.custody is custody)
        if probe_stages is not None:
            _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
        _require(latch(owner, consumer) is consumer
                 and consumer.predecessor is predecessor
                 and consumer.baseline is baseline and consumer.eof is eof
             and consumer.custody is custody)
        producer_started = True
        try:
            if probe_stages is not None:
                _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
            actual = produce(owner, consumer)
        finally:
            # Control flow, not a current stored ended flag: the actual fixed
            # synchronous call returned or raised before this caller continues.
            producer_unwound = True
        if probe_stages is not None:
            _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
        commit = consume(owner, consumer, actual)
        if probe_stages is not None:
            _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
        acked = acknowledge(owner, consumer, actual, commit)
        if probe_stages is not None:
            _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
        _require(acked is commit
                 and attached_tail(owner, consumer, commit) is commit)
        complete = True
    except BaseException:  # noqa: S110 - never log private raw-bearing exceptions
        pass

    # Leave the original exception handler before disposal so a fresh outward
    # error cannot carry its private exception/traceback as implicit context.
    actual = None
    try:
        _require(type(operation) is _MetadataOperation and operation.owner is owner
                 and (not producer_started or producer_unwound))
        native = operation.native
        actor_arguments = (operation, marker)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                              operation.context)
        _native_post_actor_state(owner, actor_state, actor_arguments)
        # This fixed frame received the actual factory triple before effects.
        # Mutable marker slots/backlinks cannot revoke its memory-only custody.
        # Normal result/ACK guards remain strict and never use this branch.
        _origin_tail(origin)
        _require(type(marker) is origin.marker_type and marker.owner is owner
                 and marker.operation is operation and marker.origin is origin
                 and marker.owner_link is held_link and marker.marker_slot is held_slot
                 and marker.state is held_state and marker.reference is held_reference
                 and type(payload) is origin.payload_type
                 and type(held_reference) is origin.reference_type
                 and origin.reference_callback.__get__(
                     held_reference, origin.reference_type) is None
                 and origin.reference_call(held_reference) is payload)
        if not complete and producer_started and producer_unwound:
            # Preserve real debit/ACK/cursor history and all foreign replacements.
            # This branch admits no native work and does not require live grants.
            ledger, phase = operation.ledger, operation.phase
            if (type(operation.state) is list and len(operation.state) == 3
                    and operation.state[2] is False):
                operation.state[2] = True
            if (type(ledger.failed) is list and len(ledger.failed) == 1
                    and ledger.failed[0] is False):
                ledger.failed[0] = True
            if (type(ledger.failure) is list and len(ledger.failure) == 1
                    and ledger.failure[0] is None):
                ledger.failure[0] = operation
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.active or phase.current[0] is phase.pending
                         or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
            if (type(phase.result) is list and len(phase.result) == 1
                    and phase.result[0] is operation):
                phase.result[0] = None
            if (type(ledger.inflight) is list and len(ledger.inflight) == 1
                    and ledger.inflight[0] is operation):
                ledger.inflight[0] = None
        # Conditional detach uses the pre-effect link allocation and actual
        # held payload. Never read a current envelope/record to nominate either.
        detached = (type(held_link) is list and len(held_link) == 1
                    and held_link[0] is payload)
        if detached:
            held_link[0] = None
        unmatched_marker = not (
            type(held_slot) is list and len(held_slot) == 1 and held_slot[0] is marker
            and _payload_state_is_clear(held_state))
        try:
            if origin.marker_member.__get__(payload, origin.payload_type) is not marker:
                unmatched_marker = True
        except BaseException:
            unmatched_marker = True
        # These are historical memory-disposition markers, never native ACKs.
        # Preserve foreign entries in the original state list as well.
        if type(held_state) is list and len(held_state) == 3:
            if held_state[0] is False:
                held_state[0] = True
            if (unmatched_marker or not detached) and held_state[2] is False:
                held_state[2] = True
        record = tuple.__new__(origin.record_type,
                               (marker, detached, not detached, unmatched_marker))
        if type(held_state) is list and len(held_state) == 3 and held_state[1] is False:
            held_state[1] = True
        retired = True
        if complete:
            _require(record.detached is True and record.unmatched_link is False
                     and record.unmatched_marker is False)
    except BaseException:
        complete = False
    finally:
        try:
            if not retired and type(operation) is _MetadataOperation:
                # An interruption can precede the first detach store. Recheck
                # the original actor and pre-effect custody before a final
                # memory-only detach; never manufacture a retirement/ACK record.
                _require(operation.owner is owner
                         and (not producer_started or producer_unwound))
                native = operation.native
                actor_arguments = (operation, marker)
                actor_state = _native_pre_actor_state(owner, actor_arguments)
                _native_actor_context(native.actor_calls,
                                      (native.native, native.thread_native),
                                      operation.context)
                _native_post_actor_state(owner, actor_state, actor_arguments)
                _origin_tail(origin)
                _require(type(marker) is origin.marker_type and marker.owner is owner
                         and marker.operation is operation and marker.origin is origin
                         and marker.owner_link is held_link
                         and marker.marker_slot is held_slot
                         and marker.state is held_state and marker.reference is held_reference
                         and type(payload) is origin.payload_type
                         and type(held_reference) is origin.reference_type
                         and origin.reference_callback.__get__(
                             held_reference, origin.reference_type) is None
                         and origin.reference_call(held_reference) is payload)
                if (type(held_link) is list and len(held_link) == 1
                        and held_link[0] is payload):
                    held_link[0] = None
        except BaseException:  # no private exceptions or authority bypass
            complete = False
        finally:
            # Disposal can run finalizers; all normal live closure follows it.
            actual = payload = None
            actor_state = actor_arguments = None

    if complete and retired:
        try:
            actor_arguments = (operation, marker, commit, record)
            actor_state = _native_pre_actor_state(owner, actor_arguments)
            native = operation.native
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                  operation.context)
            _native_post_actor_state(owner, actor_state, actor_arguments)
            if probe_stages is not None:
                _rejoin_probe_stages(owner, resource, probe_origin, probe_stages)
            _require(retired_tail(
                owner, consumer, commit, origin, marker, record) is commit)
            return commit
        except BaseException:  # noqa: S110 - no raw exceptions or retry on disposal drift
            pass
        finally:
            actor_state = actor_arguments = None
    # A refusal after ACK/disposal still ends this caller. Poison only original
    # matching history under the original actor; never rewind a real ACK/cursor.
    if producer_started and producer_unwound:
        try:
            _require(type(operation) is _MetadataOperation and operation.owner is owner)
            actor_arguments = (operation, marker)
            actor_state = _native_pre_actor_state(owner, actor_arguments)
            native = operation.native
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                  operation.context)
            _native_post_actor_state(owner, actor_state, actor_arguments)
            ledger, phase = operation.ledger, operation.phase
            if (type(operation.state) is list and len(operation.state) == 3
                    and operation.state[2] is False):
                operation.state[2] = True
            if (type(ledger.failed) is list and len(ledger.failed) == 1
                    and ledger.failed[0] is False):
                ledger.failed[0] = True
            if (type(ledger.failure) is list and len(ledger.failure) == 1
                    and ledger.failure[0] is None):
                ledger.failure[0] = operation
            if (type(phase.current) is list and len(phase.current) == 1
                    and (phase.current[0] is phase.active or phase.current[0] is phase.pending
                         or phase.current[0] is phase.idle)):
                phase.current[0] = phase.failed
        except BaseException:  # noqa: S110 - wrong actors get no history mutation authority
            pass
        finally:
            actor_state = actor_arguments = None
    # In particular, a lost producer return cannot become a received envelope.
    # Original pending/failure/debit records remain; no current-row adoption.
    actual = payload = record = acked = commit = None
    raise ArtifactObservationError(owner) from None
