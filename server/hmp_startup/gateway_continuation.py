"""Original startup-to-runtime handoff DATA, never runtime/native/key admission.

The early entry/file/approval guards remain early-only. This owner retains their
original completed observations before listener imports and checks continuation
without recapture, PM selection, file IO or a caller-chosen allow-late flag.
"""
from __future__ import annotations

import os
import sys
import threading
from importlib.machinery import ModuleSpec, SourceFileLoader
from pathlib import PosixPath
from types import FunctionType, ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner
from hmp_plugin.presentation_gateway_package import GatewayPackageOwner, _Scan
from hmp_plugin.presentation_gateway_recipe import GatewayRecipeOwner, _same_recipe_binding
from hmp_plugin.presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _HashedArtifact,
    _Scope,
)

from .entry_files import EntryFileSnapshotOwner, _Inputs, _same_package
from .gateway_approval import GatewayApprovalOwner, _api_state
from .gateway_entry import GatewayEntryOwner, _origin_current
from .runtime_files import RuntimeFilePlan

_OWNER = _ROOT = None


class GatewayContinuationError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_CONTINUATION_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise GatewayContinuationError


def _same(before, after):
    return (type(before) is tuple and type(after) is tuple and len(before) == len(after)
            and all(left is right for left, right in zip(before, after, strict=True)))


class _NativeOrigin(NamedTuple):
    name: str
    module: ModuleType
    file: str
    spec: ModuleSpec
    origin: str
    loader: SourceFileLoader

    def __repr__(self):
        return "<OriginalNativeModuleOrigin redacted>"


class _ContinuationSource(NamedTuple):
    entry: GatewayEntryOwner
    entry_binding: tuple
    approval: GatewayApprovalOwner
    approval_binding: tuple
    recipe: GatewayRecipeOwner
    recipe_binding: tuple
    snapshot: EntryFileSnapshotOwner
    snapshot_cell: tuple
    snapshot_fact: tuple
    inputs: _Inputs
    io_scope: _Scope
    io_cell: tuple
    io_root: tuple
    resources: tuple
    native: tuple
    cache_context_fact: tuple

    def __repr__(self):
        return "<OriginalCompletedStartupContinuation DATA not-admission redacted>"


def _native_origins(activation_scope):
    result = []
    for name, module in (("hermes_bootstrap", activation_scope.bootstrap),
                         ("pm.environments", activation_scope.pm)):
        _require(type(module) is ModuleType and sys.modules.get(name) is module)
        values = vars(module)
        file, spec = values.get("__file__"), values.get("__spec__")
        expected = activation_scope.root + ("/hermes_bootstrap.py" if name == "hermes_bootstrap"
                                            else "/pm/environments.py")
        _require(type(file) is str and file == expected and type(spec) is ModuleSpec)
        origin, loader = vars(spec).get("origin"), vars(spec).get("loader")
        _require(type(origin) is str and origin == file and type(loader) is SourceFileLoader
                 and values.get("__loader__") is loader
                 and type(vars(loader).get("name")) is str and vars(loader)["name"] == name
                 and type(vars(loader).get("path")) is str and vars(loader)["path"] == file)
        result.append(_NativeOrigin(name, module, file, spec, origin, loader))
    return tuple(result)


def _native_current(source):
    activation = source.entry_binding[2][3]
    scope = source.recipe_binding[0].activation_scope
    _require(type(activation) is GatewayActivationOwner
             and GatewayActivationOwner._retained_scope(activation) is scope
             and activation._ready is True and activation._retired is False
             and activation._uncertain is False and activation._capturing is False
             and type(sys.modules) is dict and sys.modules is scope.modules
             and sys.path is scope.paths and type(scope.paths) is list
             and type(scope.path_values) is tuple
             and all(type(path) is str for path in scope.paths)
             and tuple(scope.paths) == scope.path_values
             and type(scope.activate) is FunctionType
             and scope.activate.__globals__ is vars(scope.pm)
             and scope.activate.__code__ is scope.code
             and vars(scope.pm).get("activate_dependencies") is scope.activate)
    for row in source.native:
        _require(type(row) is _NativeOrigin and type(row.module) is ModuleType
                 and sys.modules.get(row.name) is row.module)
        values, props = vars(row.module), vars(row.spec)
        _require(values.get("__file__") is row.file and values.get("__spec__") is row.spec
                 and props.get("origin") is row.origin and props.get("loader") is row.loader
                 and values.get("__loader__") is row.loader
                 and type(vars(row.loader).get("name")) is str
                 and vars(row.loader)["name"] == row.name
                 and type(vars(row.loader).get("path")) is str
                 and vars(row.loader)["path"] == row.file)


def _runtime_fact(fact, snapshot, inputs):
    _require(type(fact) is tuple and len(fact) == 7 and fact[0] is snapshot
             and fact[1] is inputs and type(inputs) is _Inputs
             and type(inputs.runtime_plan) is RuntimeFilePlan)
    pending = inputs.runtime_plan.pending
    _require(type(pending) is tuple
             and all(type(row) is ExpectedArtifact and type(row.path) is str
                     and type(row.size) is int and type(row.sha256) is str for row in pending))
    io, file_fact = fact[2], fact[3]
    _require(type(io) is StartupArtifactOwner and type(io._origin) is _Scope
             and type(file_fact) is tuple
             and len(file_fact) == (4 if inputs.runtime_plan.executable_link is None else 5)
             and file_fact[0] is io and file_fact[1] is io._origin
             and type(file_fact[2]) is tuple and type(file_fact[3]) is tuple
             and len(file_fact[3]) == 3 and file_fact[3][0] is io
             and file_fact[3][1] is io._origin and type(file_fact[3][2]) is int
             and 0 <= file_fact[3][2] <= 2 * 1024 * 1024 * 1024
             and len(file_fact[2]) == len(pending)
             and all(type(row) is _HashedArtifact and row.owner is io
                     and row.scope is io._origin and row.expected is expected
                     and type(row.identity) is tuple and len(row.identity) == 9
                     and all(type(value) is int for value in row.identity)
                     and type(row.sha256) is str and row.sha256 == expected.sha256
                     for row, expected in zip(
                         file_fact[2], pending, strict=True)))
    return io


class GatewayContinuationOwner:
    @classmethod
    def retain(cls, entry, approval, recipe, snapshot):
        global _OWNER, _ROOT
        _require(cls is GatewayContinuationOwner and type(entry) is GatewayEntryOwner
                 and type(approval) is GatewayApprovalOwner and type(recipe) is GatewayRecipeOwner
                 and type(snapshot) is EntryFileSnapshotOwner and _OWNER is None and _ROOT is None)
        eb = GatewayEntryOwner._retained_binding(entry)
        activation = eb[2][3]
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(value) is int for value in context) and context == eb[0].context
                 and _same(eb, GatewayEntryOwner._retained_binding(entry))
                 and _OWNER is None and _ROOT is None
                 and activation._continuation_owner is None
                 and activation._continuation_cell is None)
        owner = cls.__new__(cls)
        _OWNER = activation._continuation_owner = owner  # before freshness callbacks
        partial = (owner, activation, eb)
        _ROOT = activation._continuation_cell = partial
        owner._source = owner._root = None
        owner._ready = owner._failed = owner._retired = False
        try:
            # Capture original cells/resources before any freshness callback.
            ab = GatewayApprovalOwner._retained_binding(approval)
            rb = GatewayRecipeOwner._retained_binding(recipe)
            inputs = snapshot._inputs
            _require(type(inputs) is _Inputs and inputs.entry is entry and inputs.recipe is recipe
                     and type(inputs.runtime_plan) is RuntimeFilePlan
                     and type(inputs.cache_context_slot) is list
                     and len(inputs.cache_context_slot) == 1
                     and type(snapshot._fact_cell) is tuple and len(snapshot._fact_cell) == 7
                     and snapshot._ready is True and snapshot._completing is True
                     and rb[0].expected.configuration._origin.parent.owner is approval
                     and ab[0].activation is activation is rb[0].activation
                     and _OWNER is owner and _ROOT is partial
                     and activation._continuation_owner is owner
                     and activation._continuation_cell is partial)
            io = _runtime_fact(snapshot._fact_cell, snapshot, inputs)
            _require(type(io._origin.records) is list and type(inputs.scans) is list)
            rows = [ab[0].records, rb[0].records, inputs.plugin_binding[0].records,
                    io._origin.records, inputs.scans]
            source = _ContinuationSource(
                entry, eb, approval, ab, recipe, rb, snapshot, snapshot._root_cell,
                snapshot._fact_cell, inputs, io._origin, io._cell, io._root_cell,
                tuple((items, tuple(items)) for items in rows),
                _native_origins(rb[0].activation_scope), inputs.cache_context_slot[0])
            owner._source = source
            root = (owner, activation, source)
            owner._root = _ROOT = activation._continuation_cell = root
            GatewayContinuationOwner._seal(owner)
            _require(EntryFileSnapshotOwner._current(snapshot) is inputs
                     and _same(eb, GatewayEntryOwner.current_binding(entry))
                     and _same(ab, GatewayApprovalOwner.current_binding(approval))
                     and _same_recipe_binding(rb, GatewayRecipeOwner._loaded_binding(recipe)))
            _require(owner._root is root is _ROOT is activation._continuation_cell
                     and owner._source is source
                     and GatewayContinuationOwner._seal(owner) is source)
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = True
            raise GatewayContinuationError(owner) from None

    def __repr__(self):
        return "<GatewayContinuationOwner original-DATA not-runtime-admission redacted>"

    def _seal(self):
        _require(type(self) is GatewayContinuationOwner and _OWNER is self
                 and type(self._source) is _ContinuationSource)
        s, root = self._source, self._root
        activation = s.entry_binding[2][3]
        _require(type(root) is tuple and len(root) == 3 and root is _ROOT
                 and root[0] is self and root[1] is activation and root[2] is s
                 and activation._continuation_owner is self
                 and activation._continuation_cell is root
                 and self._failed is False and self._retired is False
                 and _same(s.entry_binding, GatewayEntryOwner._retained_binding(s.entry))
                 and _same(s.approval_binding, GatewayApprovalOwner._retained_binding(s.approval))
                 and _same_recipe_binding(s.recipe_binding,
                                         GatewayRecipeOwner._retained_binding(s.recipe)))
        EntryFileSnapshotOwner._pure_lineage(s.snapshot, s.inputs, s.snapshot_cell)
        fact = s.snapshot_fact
        io = _runtime_fact(fact, s.snapshot, s.inputs)
        _require(s.snapshot._root_cell is s.snapshot_cell and s.snapshot._inputs is s.inputs
                 and s.snapshot._fact_cell is fact and activation._entry_files_fact_cell is fact
                 and fact[0] is s.snapshot and fact[1] is s.inputs
                 and s.snapshot._ready is True and s.snapshot._completing is True
                 and io._scope is s.io_scope is io._origin and io._cell is s.io_cell
                 and io._root_cell is s.io_root is activation._artifact_cell
                 and io._fact_cell is fact[3] is activation._artifact_fact_cell
                 and io._ready is True and io._failed is False and io._unknown is False
                 and io._reading is False and io._count_cell is fact[3][3]
                 and io._bytes_read is fact[3][3][2]
                 and io._hashes is fact[3][2]
                 and all(type(row) is _HashedArtifact and row.owner is io
                         and row.scope is s.io_scope for row in io._hashes)
                 and type(fact[6]) is tuple and len(fact[6]) == len(s.inputs.runtime_plan.loose)
                 and all(type(row) is tuple and len(row) == 2 and row[0] is expected.path
                         and type(row[1]) is tuple and len(row[1]) == 2
                         and type(row[1][0]) is tuple and len(row[1][0]) == 9
                         and type(row[1][1]) is tuple
                         for row, expected in zip(
                             fact[6], s.inputs.runtime_plan.loose, strict=True))
                 and type(s.resources) is tuple)
        _require(_same_package(s.inputs.plugin_binding,
                               GatewayPackageOwner._retained_binding(s.inputs.plugin)))
        for items, originals in s.resources:
            _require(type(items) is list and type(originals) is tuple
                     and len(items) == len(originals)
                     and all(actual is held and type(held) in (_Descriptor, _Scan)
                             and held.closed is True and held.close_attempted is True
                             and held.unknown is False
                             for actual, held in zip(items, originals, strict=True)))
        _require(s.inputs.cache_context_slot[0] is s.cache_context_fact)
        _native_current(s)
        _api_state(s.approval_binding[0].parent)
        _require(_origin_current(s.entry_binding[2][5]) is s.entry_binding[2][5]
                 and GatewayEntryOwner._invocation_values(
                     s.entry, s.entry_binding[0], s.entry_binding[1]) is s.entry_binding[0])
        return s

    def current_binding(self):
        """Fresh continued provenance only; caller must still enforce runtime/listener policy."""
        _require(type(self) is GatewayContinuationOwner and _OWNER is self
                 and self._ready is True and self._failed is False and self._retired is False
                 and type(_ROOT) is tuple and len(_ROOT) == 3
                 and _ROOT[0] is self and type(_ROOT[2]) is _ContinuationSource)
        root = _ROOT
        s = root[2]
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(value) is int for value in context)
                 and context == s.entry_binding[0].context)
        try:
            _require(self._source is s and self._root is root is _ROOT
                     is s.entry_binding[2][3]._continuation_cell
                     and GatewayContinuationOwner._seal(self) is s)
            api = s.approval_binding[0].parent
            value = api.function()
            _require(type(value) is PosixPath and str(value) == api.root)
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(value) is int for value in context)
                     and context == s.entry_binding[0].context
                     and self._source is s and self._root is root is _ROOT
                     is s.entry_binding[2][3]._continuation_cell
                     and GatewayContinuationOwner._seal(self) is s)
            _require(_origin_current(s.entry_binding[2][5]) is s.entry_binding[2][5]
                     and GatewayEntryOwner._invocation_values(
                         s.entry, s.entry_binding[0], s.entry_binding[1]) is s.entry_binding[0])
            return root
        except BaseException:
            self._failed = True
            raise GatewayContinuationError(self) from None
