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
    path = location.path
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
    # Six fixed possible sites per component. None is selected by a caller-
    # supplied operation/path/policy. Branch/ordinal consumption is still unwired.
    definitions = tuple(site for component in range(len(components)) for site in (
        (3, 'probe_initial', component), (4, 'probe_opened', component),
        (3, 'probe_missing_confirmation', component),
        (3, 'probe_leaf_confirmation', component),
        (4, 'probe_final_descriptor', component), (3, 'probe_final_name', component)))
    variants = tuple(_ProbeSite(owner, root, selected, site, ordinal)
                     for ordinal, site in enumerate(definitions))
    return _FreshProbePlan(owner, root, selected, row, location, path, components,
                           selected.proof, context, RuntimeCacheProbeOwner, module,
                           pure, pure.__code__, observe, observe.__code__,
                           definitions, variants, [0, None], [], [])


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
