"""Original fresh-probe plan DATA; no admission, native call or diagnostic ACK.

The complete probe traversal needs a distinct consumer and reported-missing
lifecycle. This module binds its original inputs before effects. Its zero-cursor
guard remains until that lifecycle is implemented; a plan is never authority.
"""
from __future__ import annotations

import sys
from types import FunctionType, ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_startup_artifacts import _Scope
from hmp_plugin.presentation_startup_artifacts import (
    _NativeScopeRegistration, _NativeProbeMetadataResource,
    _capture_native_scope, _native_work_origin_tail,
)

from .cache_probe import RuntimeCacheProbeOwner
from .cache_candidates import PlannedCachePath
from .cache_context import CacheInputData
from .cache_selection import BoundCacheInputAttempt
from .gateway_continuation import GatewayContinuationOwner, _ContinuationSource


class ProbePlanError(ValueError):
    def __init__(self):
        super().__init__('BI1_FRESH_PROBE_PLAN_REFUSED')


def _need(value):
    if value is not True:
        raise ProbePlanError from None


class _ProbeSite(NamedTuple):
    owner: object
    root: tuple
    selected: object
    site: tuple
    ordinal: int

    def __repr__(self):
        return '<FreshProbeSite DATA no-operation-authority>'


class _FreshProbePlan(NamedTuple):
    owner: object
    root: tuple
    selected: object
    row: object
    location: object
    path: str
    components: tuple
    proof: tuple
    context: tuple
    owner_type: type
    module: ModuleType
    material: object
    material_code: object
    observe: object
    observe_code: object
    definitions: tuple
    variants: tuple
    progress: list
    commits: list
    ancestors: list
    resource_origin: tuple
    engine_origin: tuple

    def __repr__(self):
        return '<FreshProbePlan original DATA no-admission>'


def _new_fresh_probe_plan(owner, root, selected, context):
    """Capture the actual retain caller's inputs, before constructing its scope.

    All rows below are possible fixed sites, including distinct confirmations.
    Their allocation grants no branch, syscall, byte allowance or missing-file
    result. The eventual consumer must derive a branch from actual prior returns.
    """
    _need(type(owner) is RuntimeCacheProbeOwner and type(root) is tuple and len(root) == 3
          and type(root[0]) is GatewayContinuationOwner
          and type(root[2]) is _ContinuationSource
          and type(selected) is BoundCacheInputAttempt
          and type(selected.plan_row) is CacheInputData
          and type(selected.plan_row.location) is PlannedCachePath
          and type(selected.plan_row.location.path) is str
          and type(selected.proof) is tuple
          and type(context) is tuple and len(context) == 3
          and all(type(part) is int for part in context))
    row, location = selected.plan_row, selected.plan_row.location
    path, proof = location.path, selected.proof
    owner_kind = RuntimeCacheProbeOwner
    _need(1 < len(path.encode('utf-8')) <= 4096 and path.startswith('/')
          and all(32 <= ord(char) != 127 for char in path))
    parts = path[1:].split('/')
    _need(1 <= len(parts) <= 64 and all(part not in ('', '.', '..') for part in parts))
    components = ('/', *parts)
    _need(type(sys.modules) is dict)
    module = sys.modules.get('hmp_startup.cache_probe')
    _need(type(module) is ModuleType)
    names = vars(module)
    pure = vars(RuntimeCacheProbeOwner).get('_pure')
    observe = vars(RuntimeCacheProbeOwner).get('_observe_owned')
    _need(names.get('RuntimeCacheProbeOwner') is RuntimeCacheProbeOwner
          and names.get('_OWNER') is owner and names.get('_CELL') is None
          and names.get('_FACT') is None
          and type(names.get('_ROOT')) is tuple and len(names['_ROOT']) == 3
          and names['_ROOT'][0] is root[1] and names['_ROOT'][1] is owner
          and names['_ROOT'][2] is None
          and type(pure) is FunctionType and pure.__globals__ is names
          and type(observe) is FunctionType and observe.__globals__ is names
          and vars(owner).get('_retaining') is True
          and vars(owner).get('_started') is False
          and vars(owner).get('_probe_plan') is None)
    # Hold original code and namespace/owner inputs BEFORE any constructor can
    # invoke a callback. Later matching mirrors cannot nominate new originals.
    pure_code, observe_code = pure.__code__, observe.__code__
    partial = names['_ROOT']
    owner_names = vars(owner)
    owner_entries = tuple(owner_names.items())
    helper = _fresh_probe_resource_tail
    helper_module = sys.modules.get(__name__)
    _need(type(helper) is FunctionType and type(helper_module) is ModuleType
          and helper.__globals__ is vars(helper_module)
          and vars(helper_module).get('_fresh_probe_resource_tail') is helper
          and _ProbeObservationResource is _NativeProbeMetadataResource)
    resource_origin = (_NativeProbeMetadataResource, owner_kind, module,
                       helper_module, helper, helper.__code__)
    from .probe_native import _new_probe_engine_origin

    engine_origin = _new_probe_engine_origin()
    site_kind, plan_kind = _ProbeSite, _FreshProbePlan
    site_fields, plan_fields = site_kind._fields, plan_kind._fields
    site_members = tuple(vars(site_kind).get(field) for field in site_fields)
    plan_members = tuple(vars(plan_kind).get(field) for field in plan_fields)
    tuple_item, tuple_length = tuple.__getitem__, tuple.__len__
    need, need_code, error_type = _need, _need.__code__, ProbePlanError
    # Six fixed possible sites per component. None is selected by a caller-
    # supplied operation/path/policy. Branch/ordinal consumption is still unwired.
    definitions = tuple(site for component in range(len(components)) for site in (
        (3, 'probe_initial', component), (4, 'probe_opened', component),
        (3, 'probe_missing_confirmation', component),
        (3, 'probe_leaf_confirmation', component),
        (4, 'probe_final_descriptor', component), (3, 'probe_final_name', component)))
    variants = tuple(site_kind(owner, root, selected, site, ordinal)
                     for ordinal, site in enumerate(definitions))
    values = (owner, root, selected, row, location, path, components,
              proof, context, owner_kind, module,
              pure, pure_code, observe, observe_code,
              definitions, variants, [0, None], [], [], resource_origin, engine_origin)
    result = plan_kind(*values)
    if need.__code__ is not need_code:
        raise error_type from None
    need(type(result) is plan_kind and tuple_length(result) == len(values)
         and all(tuple_item(result, index) is original
                 for index, original in enumerate(values))
         and _ProbeSite is site_kind and _FreshProbePlan is plan_kind
         and site_kind._fields is site_fields and plan_kind._fields is plan_fields
         and all(vars(site_kind).get(field) is member
                 for field, member in zip(site_fields, site_members, strict=True))
         and all(vars(plan_kind).get(field) is member
                 for field, member in zip(plan_fields, plan_members, strict=True)))
    need(helper.__code__ is resource_origin[5]
         and sys.modules.get(__name__) is helper_module
         and vars(helper_module).get('_fresh_probe_resource_tail') is helper
         and _ProbeObservationResource is resource_origin[0])
    need(pure.__code__ is pure_code and observe.__code__ is observe_code
         and pure.__globals__ is names and observe.__globals__ is names
         and type(sys.modules) is dict
         and sys.modules.get('hmp_startup.cache_probe') is module
         and vars(module) is names
         and RuntimeCacheProbeOwner is owner_kind
         and names.get('RuntimeCacheProbeOwner') is owner_kind
         and vars(owner_kind).get('_pure') is pure
         and vars(owner_kind).get('_observe_owned') is observe
         and selected.plan_row is row and row.location is location
         and location.path is path and selected.proof is proof
         and names.get('_OWNER') is owner and names.get('_CELL') is None
         and names.get('_FACT') is None and names.get('_ROOT') is partial
         and vars(owner) is owner_names and len(owner_names) == len(owner_entries)
         and all(type(key) is str for key in owner_names)
         and all(key in owner_names and owner_names[key] is value
                 for key, value in owner_entries))
    for ordinal, (site, variant) in enumerate(zip(definitions, variants, strict=True)):
        need(type(variant) is site_kind and tuple_length(variant) == 5
             and tuple_item(variant, 0) is owner and tuple_item(variant, 1) is root
             and tuple_item(variant, 2) is selected and tuple_item(variant, 3) is site
             and type(tuple_item(variant, 4)) is int and tuple_item(variant, 4) == ordinal)
    return result


def _fresh_probe_plan_tail(owner, scope, original):
    """Pure original plan/scope binding, retaining the unwired zero-state fence.

    No owner callback, actor sample, native operation or registration lookup runs
    here. The fixed caller must separately retain its actual registration and
    original plan across those effects. A matching current row is not a receipt.
    """
    _need(type(scope) is _Scope and type(original) is _FreshProbePlan
          and original.owner is owner and type(original.owner_type) is type
          and type(owner) is original.owner_type
          and scope.native_probe_plan is original
          and scope.native_probe_origin is original.resource_origin
          and scope.native_probe_engine_origin is original.engine_origin
          and type(scope.parent) is tuple and len(scope.parent) == 2
          and scope.parent[0] is original.root and scope.parent[1] is original.selected
          and type(original.root) is tuple and len(original.root) == 3
          and scope.activation is original.root[1]
          and scope.context is original.context
          and type(original.context) is tuple and len(original.context) == 3
          and all(type(value) is int for value in original.context)
          and type(scope.expected) is tuple and len(scope.expected) == 1)
    own = vars(owner)
    _need(own.get('_origin') is scope and own.get('_scope') is scope
          and own.get('_probe_plan') is original
          and type(own.get('_cell')) is tuple and len(own['_cell']) == 2
          and own['_cell'][0] is owner and own['_cell'][1] is scope
          and type(own.get('_root_cell')) is tuple and len(own['_root_cell']) == 3
          and own['_root_cell'][0] is scope.activation
          and own['_root_cell'][1] is owner and own['_root_cell'][2] is scope
          and type(original.module) is ModuleType
          and type(sys.modules) is dict
          and sys.modules.get('hmp_startup.cache_probe') is original.module)
    names = vars(original.module)
    _need(names.get('RuntimeCacheProbeOwner') is original.owner_type
          and names.get('_OWNER') is owner and names.get('_CELL') is own['_cell']
          and names.get('_ROOT') is own['_root_cell']
          and type(original.material) is FunctionType
          and original.material.__globals__ is names
          and original.material.__code__ is original.material_code
          and vars(original.owner_type).get('_pure') is original.material
          and type(original.observe) is FunctionType
          and original.observe.__globals__ is names
          and original.observe.__code__ is original.observe_code
          and vars(original.owner_type).get('_observe_owned') is original.observe)
    # These are immutable original selections already type-checked by retain.
    # Rejoin their exact rows/values before inspecting any nested DATA.
    _need(type(original.selected) is BoundCacheInputAttempt
          and type(original.row) is CacheInputData
          and original.selected.plan_row is original.row
          and type(original.location) is PlannedCachePath
          and original.row.location is original.location
          and original.location.path is original.path
          and type(original.path) is str and original.path.startswith('/')
          and original.selected.proof is original.proof
          and type(original.proof) is tuple
          and scope.expected[0] is original.row.source
          and type(original.components) is tuple and 2 <= len(original.components) <= 65
          and all(type(part) is str for part in original.components)
          and original.components[0] == '/'
          and '/'.join(original.components[1:]) == original.path[1:]
          and type(original.definitions) is tuple and type(original.variants) is tuple
          and len(original.definitions) == len(original.variants) == 6 * len(original.components))
    for ordinal, (site, variant) in enumerate(zip(original.definitions, original.variants, strict=True)):
        component, offset = divmod(ordinal, 6)
        operation, role = ((3, 'probe_initial'), (4, 'probe_opened'),
                           (3, 'probe_missing_confirmation'), (3, 'probe_leaf_confirmation'),
                           (4, 'probe_final_descriptor'), (3, 'probe_final_name'))[offset]
        _need(type(site) is tuple and len(site) == 3
              and type(site[0]) is int and type(site[1]) is str and type(site[2]) is int
              and site[0] == operation and site[1] == role and site[2] == component
              and type(variant) is _ProbeSite and variant.owner is owner
              and variant.root is original.root and variant.selected is original.selected
              and variant.site is site and type(variant.ordinal) is int
              and variant.ordinal == ordinal)
    _need(type(original.progress) is list and len(original.progress) == 2
          and type(original.progress[0]) is int and original.progress[0] == 0
          and original.progress[1] is None
          and type(original.commits) is list and len(original.commits) == 0
          and type(original.ancestors) is list and len(original.ancestors) == 0)
    return original


_ProbeObservationResource = _NativeProbeMetadataResource


def _fresh_probe_resource_tail(owner, resource):
    """Unclaimed root resource only while the complete probe engine is unwired.

    This deliberately does not relax the original zero-state plan fence. Later
    sites require the distinct probe consumer/history/diagnostic lifecycle, not
    another DirectoryConsumer owner or a caller-selected path/operation.
    """
    _need(type(resource) is _ProbeObservationResource and resource.owner is owner
          and type(resource.registration) is _NativeScopeRegistration
          and type(resource.registration.scope) is _Scope)
    scope = resource.registration.scope
    plan = scope.native_probe_plan
    _need(type(plan) is _FreshProbePlan
          and scope.native_probe_engine_origin is plan.engine_origin)
    origin = plan.engine_origin
    _need(type(origin) is tuple and len(origin) == 6
          and type(origin[0]) is ModuleType
          and sys.modules.get('hmp_startup.probe_native') is origin[0]
          and type(origin[1]) is tuple and len(origin[1]) == 4
          and type(origin[2]) is tuple and len(origin[2]) == 21)
    if type(resource.metadata) is origin[1][0][0]:
        for name, function, code in origin[2]:
            _need(type(name) is str and type(function) is FunctionType
                  and vars(origin[0]).get(name) is function
                  and function.__globals__ is vars(origin[0]) and function.__code__ is code)
        # Exact retained engine helper, never a current module nomination.
        _need(origin[2][3][0] == '_resource_tail')
        return origin[2][3][1](owner, resource)
    _need(vars(owner).get('_probe_execution') is None)
    _need(type(resource) is _ProbeObservationResource and resource.owner is owner
          and type(owner) is RuntimeCacheProbeOwner
          and type(resource.registration) is _NativeScopeRegistration
          and resource.registration.owner is owner
          and type(resource.registration.scope) is _Scope
          and type(resource.metadata) is _FreshProbePlan)
    registration, plan = resource.registration, resource.metadata
    scope = registration.scope
    own = vars(owner)
    _need(own.get('_origin') is scope and own.get('_scope') is scope
          and own.get('_started') is True and own.get('_ready') is False
          and own.get('_failed') is False and own.get('_unknown') is False
          and own.get('_retaining') is False and own.get('_admitting') is False)
    cell, root = own.get('_cell'), own.get('_root_cell')
    _need(_capture_native_scope(scope, cell, root) is registration
          and _fresh_probe_plan_tail(owner, scope, plan) is plan
          and type(scope.records) is list and len(scope.records) == 0
          and type(resource.ordinal) is int and resource.ordinal == 0
          and resource.site is plan.definitions[0]
          and resource.variant is plan.variants[0]
          and resource.site == (3, 'probe_initial', 0)
          and resource.descriptor is None
          and type(resource.arguments) is tuple and len(resource.arguments) == 2
          and resource.arguments[0] is plan.components[0]
          and resource.arguments[1] is None)
    _native_work_origin_tail(owner, registration, registration.native_origin)
    _need(_capture_native_scope(scope, cell, root) is registration
          and _fresh_probe_plan_tail(owner, scope, plan) is plan
          and own.get('_started') is True and own.get('_ready') is False
          and own.get('_failed') is False and own.get('_unknown') is False
          and own.get('_retaining') is False and own.get('_admitting') is False
          and len(scope.records) == 0 and resource.metadata is plan
          and resource.site is plan.definitions[0] and resource.variant is plan.variants[0]
          and resource.descriptor is None
          and type(resource.arguments) is tuple and len(resource.arguments) == 2
          and resource.arguments[0] is plan.components[0] and resource.arguments[1] is None)
    return resource


def _prepare_fresh_probe_resource(owner, registration, original):
    """Allocate original root input for shared intent preparation, without IO.

    The actual probe invocation must already have passed its normal admission.
    This provides neither native admission nor result/diagnostic credit. The
    unsupported consumer path remains closed until the complete engine is wired.
    """
    _need(type(registration) is _NativeScopeRegistration
          and type(registration.scope) is _Scope
          and registration.owner is owner and type(original) is _FreshProbePlan)
    _fresh_probe_plan_tail(owner, registration.scope, original)
    kind = _ProbeObservationResource
    fields = kind._fields
    members = tuple(vars(kind).get(name) for name in fields)
    item, length = tuple.__getitem__, tuple.__len__
    site, variant = original.definitions[0], original.variants[0]
    arguments = (original.components[0], None)
    values = (owner, registration, original, variant, site, 0, None, arguments)
    result = kind(*values)
    _need(_ProbeObservationResource is kind and type(result) is kind
          and vars(kind).get('_fields') is fields
          and all(vars(kind).get(name) is member
                  for name, member in zip(fields, members, strict=True))
          and length(result) == len(values)
          and all(item(result, index) is value for index, value in enumerate(values)))
    return _fresh_probe_resource_tail(owner, result)
