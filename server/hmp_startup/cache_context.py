"""Original pre-IO cache context DATA; no cache reads, absence proof or admission."""
from __future__ import annotations

import os
import sys
import threading
from types import BuiltinFunctionType, ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_package import GatewayPackageOwner
from hmp_plugin.presentation_gateway_recipe import GatewayRecipeOwner, _same_recipe_binding
from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact

from .cache_candidates import PlannedCachePath, _location, planned_cache_path
from .entry_files import EntryFileSnapshotOwner, _Inputs, _same_package
from .gateway_entry import GatewayEntryOwner, _origin_current
from .runtime_files import RuntimeFilePlan, RuntimePackage, plan_current

_OWNER = _ROOT = _FACT = None


class CacheContextError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_CACHE_CONTEXT_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise CacheContextError


class CacheInputData(NamedTuple):
    source: ExpectedArtifact
    location: PlannedCachePath
    cache: ExpectedArtifact | None
    tree: RuntimePackage | None
    state: str

    def __repr__(self):
        return "<OriginalCacheInputPlan DATA not-observation redacted>"


class _ContextSource(NamedTuple):
    snapshot: EntryFileSnapshotOwner
    inputs: _Inputs
    cell: tuple
    plan: RuntimeFilePlan
    context: tuple
    requires_cwd: bool
    getter: object
    os_module: object
    posix_module: object

    def __repr__(self):
        return "<OriginalPreIOCacheContext redacted>"


def _context():
    values = os.getpid(), os.geteuid(), threading.get_ident()
    _require(all(type(value) is int for value in values))
    return values


def _getter_current(source):
    # Exact native storage before field access: current class getters are not
    # inspection primitives, and a nominal NamedTuple can have short storage.
    if type(source) is not _ContextSource or tuple.__len__(source) != 9:
        _require(False)
        return
    requires = tuple.__getitem__(source, 5)
    getter = tuple.__getitem__(source, 6)
    os_module = tuple.__getitem__(source, 7)
    posix_module = tuple.__getitem__(source, 8)
    if requires is False:
        _require(getter is os_module is posix_module is None)
        return
    if (requires is not True or type(getter) is not BuiltinFunctionType
            or type(os_module) is not ModuleType or type(posix_module) is not ModuleType):
        _require(False)
        return
    registry, namespace, original = sys.modules, vars(os_module), vars(posix_module)
    _require(type(registry) is dict and all(type(key) is str for key in registry)
             and all(type(key) is str for key in namespace)
             and all(type(key) is str for key in original)
             and os_module is os and registry.get("os") is os_module
             and registry.get("posix") is posix_module
             and namespace.get("getcwd") is getter and original.get("getcwd") is getter
             and getter.__self__ is posix_module
             and type(getter.__name__) is str and getter.__name__ == "getcwd"
             and type(getter.__module__) is str and getter.__module__ == "posix")


def _rows(source, cwd):
    inputs, plan = source.inputs, source.plan
    interpreter = inputs.entry_binding[0].interpreter
    tag = interpreter.data.implementation[1]
    optimize = interpreter.flags.optimize
    prefix = interpreter.cache_policy.prefix
    files = {row.path: row for row in plan.all_files}
    result = []
    for row in plan.all_files:
        _require(type(row) is ExpectedArtifact and type(row.path) is str)
        if not row.path.endswith(".py"):
            continue
        location = planned_cache_path(row.path, tag, optimize, prefix, cwd)
        cache = files.get(location.path)
        tree = next((package for package in plan.packages
                     if location.path.startswith(package.path + "/")), None)
        state = "declared" if cache is not None else "needs_owned_absence"
        if tree is not None and cache is None:
            relative = location.path[len(tree.path) + 1:]
            state = ("tree_nonfile" if any(name == relative for name, _ in tree.entries)
                     else "tree_expected_absent")
        result.append(CacheInputData(row, location, cache, tree, state))
    return tuple(result)


class CacheContextOwner:
    @classmethod
    def retain(cls, snapshot):
        global _OWNER, _ROOT, _FACT
        _require(cls is CacheContextOwner and type(snapshot) is EntryFileSnapshotOwner
                 and type(snapshot._inputs) is _Inputs
                 and _OWNER is None and _ROOT is None and _FACT is None)
        inputs, cell = snapshot._inputs, snapshot._root_cell
        _require(type(inputs.runtime_plan) is RuntimeFilePlan
                 and type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1
                 and inputs.cache_context_slot[0] is None
                 and snapshot._ready is False and snapshot._completing is False
                 and type(inputs.io_slot) is list and len(inputs.io_slot) == 1
                 and inputs.io_slot[0] is None and snapshot._cache_context_cell is None)
        original_entry = GatewayEntryOwner._retained_binding(inputs.entry)
        _require(type(inputs.entry_binding) is tuple and len(inputs.entry_binding) == 3
                 and all(a is b for a, b in zip(original_entry, inputs.entry_binding, strict=True)))
        context = original_entry[0].context
        _require(type(context) is tuple and len(context) == 3
                 and all(type(value) is int for value in context))
        _require(_context() == context)  # ineligible callers cannot allocate/poison the slot
        _require(snapshot._inputs is inputs and snapshot._root_cell is cell
                 and inputs.cache_context_slot[0] is None and _OWNER is None and _ROOT is None)
        owner = cls.__new__(cls)
        _OWNER = inputs.cache_context_slot[0] = owner
        owner._ready = owner._failed = owner._retired = False
        owner._fact = owner._cwd = owner._rows = None
        owner._source = owner._root = None
        try:
            plan = inputs.runtime_plan
            _require(type(plan.all_files) is tuple and all(type(row) is ExpectedArtifact
                     and type(row.path) is str for row in plan.all_files))
            required = any(row.path.endswith(".py") and row.path.rsplit("/", 1)[0] == ""
                           for row in plan.all_files)
            getter = vars(os).get("getcwd") if required else None
            source = _ContextSource(snapshot, inputs, cell, plan, context, required, getter,
                                    os if required else None,
                                    sys.modules.get("posix") if required else None)
            owner._source = source
            root = (owner, source)
            owner._root = _ROOT = snapshot._cache_context_cell = root
            CacheContextOwner._seal(owner)
            cwd = source.getter() if required else None
            if required:
                _location(cwd)
            _require(owner._root is root is _ROOT is snapshot._cache_context_cell
                     and owner._source is source and CacheContextOwner._seal(owner) is source)
            owner._cwd = cwd
            rows = _rows(source, cwd)
            owner._rows = rows
            fact = (owner, root, cwd, rows)
            owner._fact = _FACT = fact
            inputs.cache_context_slot[0] = fact
            owner._ready = True
            _require(CacheContextOwner._seal(owner) is source)
            return owner
        except BaseException:
            owner._failed = True
            raise CacheContextError(owner) from None

    def __repr__(self):
        return "<OriginalPreIOCacheContextOwner DATA redacted>"

    def _seal(self):
        _require(type(self) is CacheContextOwner and _OWNER is self
                 and self._failed is False and self._retired is False
                 and type(self._source) is _ContextSource and type(self._root) is tuple)
        source, root = self._source, self._root
        _require(root is _ROOT and len(root) == 2 and root[0] is self and root[1] is source)
        inputs, snapshot = source.inputs, source.snapshot
        _require(type(inputs) is _Inputs and type(snapshot) is EntryFileSnapshotOwner
                 and snapshot._inputs is inputs and snapshot._root_cell is source.cell
                 and type(source.cell) is tuple and len(source.cell) == 2
                 and source.cell[0] is snapshot and source.cell[1] is inputs
                 and snapshot._cache_context_cell is root
                 and snapshot._failed is False and snapshot._unknown is False
                 and type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1
                 and inputs.runtime_plan is source.plan
                 and inputs.recipe_binding[0].activation._entry_files_owner is snapshot
                 and inputs.recipe_binding[0].activation._entry_files_cell is source.cell)
        eb = GatewayEntryOwner._retained_binding(inputs.entry)
        _require(all(a is b for a, b in zip(eb, inputs.entry_binding, strict=True))
                 and GatewayEntryOwner._invocation_values(inputs.entry, eb[0], eb[1]) is eb[0]
                 and _origin_current(eb[2][5]) is eb[2][5]
                 and _same_recipe_binding(inputs.recipe_binding,
                                         GatewayRecipeOwner._retained_binding(inputs.recipe))
                 and _same_package(inputs.plugin_binding,
                                   GatewayPackageOwner._retained_binding(inputs.plugin)))
        plan_current(source.plan, inputs.entry_binding, inputs.recipe_binding,
                     inputs.plugin_binding)
        _getter_current(source)
        if self._ready is False:
            _require(self._fact is None and _FACT is None and inputs.cache_context_slot[0] is self)
        else:
            _require(self._ready is True and type(self._fact) is tuple and len(self._fact) == 4
                     and inputs.cache_context_slot[0] is self._fact is _FACT
                     and self._fact[0] is self and self._fact[1] is root
                     and self._fact[2] is self._cwd and self._fact[3] is self._rows
                     and type(self._rows) is tuple)
        return source

    def retained_binding(self):
        _require(type(self) is CacheContextOwner and self._ready is True)
        CacheContextOwner._seal(self)
        return self._fact

    def current_binding(self):
        _require(type(self) is CacheContextOwner and self._ready is True
                 and self._failed is False and self._retired is False
                 and type(self._source) is _ContextSource)
        source, root, fact = self._source, self._root, self._fact
        _require(type(source.context) is tuple and len(source.context) == 3
                 and all(type(value) is int for value in source.context)
                 and _context() == source.context)
        try:
            _require(self._source is source and self._root is root is _ROOT
                     and self._fact is fact and CacheContextOwner._seal(self) is source)
            if source.requires_cwd:
                cwd = source.getter()
                _location(cwd)
                _require(type(fact[2]) is str and cwd == fact[2])
            _require(self._source is source and self._root is root is _ROOT
                     and self._fact is fact and CacheContextOwner._seal(self) is source)
            return fact
        except BaseException:
            self._failed = True
            raise CacheContextError(self) from None
