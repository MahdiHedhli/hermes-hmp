"""Fresh original-row cache metadata probe; no read/fallback/code authority."""
from __future__ import annotations

import errno
import os
import stat
import threading
from typing import NamedTuple
from types import FunctionType

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner
from hmp_plugin.presentation_gateway_package import _Tree
from hmp_plugin.presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _capture_native_scope,
    _capture_native_work_origin,
    _descriptor_closed_in_scope,
    _descriptor_refused,
    _HashedArtifact,
    _identity,
    _native_actor_context,
    _native_post_actor_state,
    _native_pre_actor_state,
    _native_registration_tail,
    _native_relative_arguments,
    _native_walk_scope,
    _native_work_origin_tail,
    _Scope,
)

from .bytecode_headers import SourceHashData
from .cache_candidates import PlannedCachePath
from .cache_context import CacheInputData
from .cache_selection import BoundCacheInputAttempt, selected_cache_input_attempts
from .gateway_continuation import GatewayContinuationOwner, _ContinuationSource
from .gateway_entry import GatewayEntryOwner
from .runtime_files import RuntimePackage

_OWNER = _ROOT = _CELL = _FACT = None


class CacheProbeError(Exception):
    def __init__(self, owner=None):
        super().__init__('BI1_RUNTIME_CACHE_PROBE_REFUSED')
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise CacheProbeError


class CacheProbeData(NamedTuple):
    state: str
    position: int
    identity: tuple | None
    ancestors: tuple

    def __repr__(self):
        return '<FreshCacheProbe DATA no-fallback-authority>'


def _context():
    value = (os.getpid(), os.geteuid(), threading.get_ident())
    _require(all(type(part) is int for part in value))
    return value


class RuntimeCacheProbeOwner:
    @classmethod
    def retain(cls, continuation, index):
        global _OWNER, _ROOT, _CELL
        _require(cls is RuntimeCacheProbeOwner and type(continuation) is GatewayContinuationOwner
                 and type(index) is int and index >= 0
                 and _OWNER is _ROOT is _CELL is _FACT is None)
        root = GatewayContinuationOwner.current_binding(continuation)
        activation = root[1]
        _require(activation._runtime_cache_probe_owner is None
                 and activation._runtime_cache_probe_cell is None
                 and activation._runtime_cache_probe_fact is None)
        owner = cls.__new__(cls)
        _OWNER = activation._runtime_cache_probe_owner = owner
        partial = (activation, owner, None)
        _ROOT = owner._root_cell = activation._runtime_cache_probe_cell = partial
        owner._scope = owner._origin = owner._cell = owner._count_cell = None
        owner._ready = owner._failed = owner._unknown = owner._reading = owner._started = False
        owner._retaining = True
        owner._admitting = False
        owner._bytes_read = 0
        owner._fact = None
        owner._probe_plan = None
        owner._probe_execution = None
        try:
            rows = selected_cache_input_attempts(continuation)
            _require(index < len(rows))
            selected = rows[index]
            context = _context()
            _require(type(selected) is BoundCacheInputAttempt
                     and context == root[2].entry_binding[0].context
                     and _ROOT is partial and _OWNER is owner and _CELL is None
                     and owner._root_cell is partial
                     and activation._runtime_cache_probe_cell is partial)
            from .probe_metadata import _new_fresh_probe_plan

            plan = _new_fresh_probe_plan(owner, root, selected, context)
            scope_kind = _Scope
            scope_fields = vars(scope_kind)['_fields']
            scope_members = tuple(vars(scope_kind).get(field) for field in scope_fields)
            dispatch_names = ('__getattribute__', '__getattr__', '__getitem__', '__len__', '__iter__')
            scope_dispatch = tuple(vars(scope_kind).get(name) for name in dispatch_names)
            owner_names = vars(owner)
            owner_entries = tuple(owner_names.items())
            need, need_code = _require, _require.__code__
            material, observe = plan.material, plan.observe
            material_code, observe_code = plan.material_code, plan.observe_code
            activation_scope = root[2].io_scope.activation_scope
            expected, records, parent = (selected.plan_row.source,), [], (root, selected)
            native_files, slot = root[2].entry_binding[0].native_files, [None]
            values = (activation, activation_scope, expected, context, records, parent,
                      None, None, None, None, native_files, slot, None, plan,
                      plan.resource_origin, plan.engine_origin)
            tuple_item, tuple_length = tuple.__getitem__, tuple.__len__
            scope = scope_kind(activation, activation_scope, expected, context, records,
                               parent=parent, native_files=native_files,
                               native_registration_slot=slot, native_probe_plan=plan,
                               native_probe_origin=plan.resource_origin,
                               native_probe_engine_origin=plan.engine_origin)
            # Scope construction is a separate callback boundary after the plan
            # factory's seal. Do not overwrite a replacement owner/plan slot or
            # publish a changed scope merely because the earlier factory closed.
            if need.__code__ is not need_code:
                raise CacheProbeError(owner) from None
            need(type(scope) is scope_kind and _Scope is scope_kind
                 and vars(scope_kind).get('_fields') is scope_fields
                 and all(vars(scope_kind).get(field) is member
                         for field, member in zip(scope_fields, scope_members, strict=True))
                 and all(vars(scope_kind).get(name) is member
                         for name, member in zip(dispatch_names, scope_dispatch, strict=True))
                 and tuple_length(scope) == len(values)
                 and all(tuple_item(scope, index) is original
                         for index, original in enumerate(values))
                 and vars(owner) is owner_names and len(owner_names) == len(owner_entries)
                 and all(type(key) is str for key in owner_names)
                 and all(key in owner_names and owner_names[key] is value
                         for key, value in owner_entries)
                 and owner_names.get('_probe_plan') is None
                 and type(records) is list and len(records) == 0
                 and type(slot) is list and len(slot) == 1 and slot[0] is None
                 and material.__code__ is material_code and observe.__code__ is observe_code
                 and vars(cls).get('_pure') is material
                 and vars(cls).get('_observe_owned') is observe
                 and RuntimeCacheProbeOwner is cls
                 and _ROOT is partial and _OWNER is owner and _CELL is None and _FACT is None
                 and owner._root_cell is partial
                 and activation._runtime_cache_probe_cell is partial)
            owner._probe_plan = plan
            cell = (owner, scope)
            runtime_root = (activation, owner, scope)
            owner._scope = owner._origin = scope
            _CELL = owner._cell = cell
            _ROOT = owner._root_cell = activation._runtime_cache_probe_cell = runtime_root
            owner._count_cell = (owner, scope, 0)
            _require(RuntimeCacheProbeOwner._guard(owner) is scope
                     and _ROOT is runtime_root and _CELL is cell and _OWNER is owner
                     and owner._started is False and owner._ready is False)
            from hmp_plugin.presentation_startup_artifacts import _register_native_scope

            _register_native_scope(owner, scope, cell, runtime_root)
            _require(owner._origin is scope and owner._scope is scope
                     and owner._cell is cell and owner._root_cell is runtime_root
                     and activation._runtime_cache_probe_cell is runtime_root)
            owner._retaining = False
            return owner
        except BaseException:
            owner._failed = True
        raise CacheProbeError(owner) from None

    def __repr__(self):
        return '<RuntimeCacheProbeOwner metadata-only no-admission>'

    def _pure(self):
        _require(type(self) is RuntimeCacheProbeOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 3 and _ROOT[1] is self
                 and type(_ROOT[2]) is _Scope and type(_CELL) is tuple and len(_CELL) == 2)
        s = _ROOT[2]
        _require(self._origin is s and self._scope is s and self._root_cell is _ROOT
                 and self._cell is _CELL and _CELL[0] is self and _CELL[1] is s
                 and self._failed is False and self._unknown is False
                 and type(s.activation) is GatewayActivationOwner
                 and s.activation._runtime_cache_probe_owner is self
                 and s.activation._runtime_cache_probe_cell is _ROOT
                 and type(s.parent) is tuple and len(s.parent) == 2
                 and type(s.parent[0]) is tuple and len(s.parent[0]) == 3
                 and type(s.parent[0][0]) is GatewayContinuationOwner
                 and type(s.parent[0][2]) is _ContinuationSource
                 and type(s.parent[1]) is BoundCacheInputAttempt
                 and type(s.parent[1].plan_row) is CacheInputData
                 and type(s.records) is list and type(self._bytes_read) is int
                 and self._bytes_read == 0
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and type(self._count_cell[2]) is int and self._count_cell[2] == 0)
        _require(s.native_files is GatewayEntryOwner._native_file_lineage(s.parent[0][2].entry))
        selected = s.parent[1]
        row = selected.plan_row
        _require(type(row.location) is PlannedCachePath and type(row.location.path) is str
                 and type(row.source) is ExpectedArtifact
                 and type(selected.source) is SourceHashData
                 and type(selected.source.receipt) is _HashedArtifact
                 and selected.source.receipt.expected is row.source
                 and type(selected.proof) is tuple and type(row.state) is str)
        if selected.cache is not None:
            _require(type(selected.cache) is _HashedArtifact and type(row.cache) is ExpectedArtifact
                     and selected.cache.expected is row.cache
                     and type(selected.cache.identity) is tuple
                     and len(selected.cache.identity) == 9
                     and all(type(value) is int for value in selected.cache.identity))
        if row.state == 'tree_nonfile':
            _require(type(row.tree) is RuntimePackage and type(row.tree.path) is str
                     and len(selected.proof) == 2 and type(selected.proof[0]) is _Tree
                     and type(selected.proof[0].directories) is tuple
                     and all(type(item) is tuple and len(item) == 2 and type(item[0]) is str
                             and type(item[1]) is tuple and len(item[1]) == 5
                             and all(type(value) is int for value in item[1])
                             for item in selected.proof[0].directories))
        from .probe_metadata import _fresh_probe_plan_tail

        valid_plan = False
        try:
            valid_plan = _fresh_probe_plan_tail(self, s, self._probe_plan) is self._probe_plan
        except BaseException:
            pass
        _require(valid_plan)
        if self._ready is True:
            _require(type(_FACT) is tuple and len(_FACT) == 10 and self._fact is _FACT
                     and _FACT[0] is self and _FACT[1] is s
                     and type(_FACT[2]) is CacheProbeData and _FACT[4] is self._count_cell
                     and s.activation._runtime_cache_probe_fact is _FACT
                     and type(_FACT[3]) is tuple and type(_FACT[5]) is tuple
                     and _FACT[6] is selected and _FACT[7] is row.location.path
                     and _FACT[8] is selected.proof and _FACT[9] is _ROOT
                     and len(s.records) == len(_FACT[5])
                     and all(a is b for a, b in zip(s.records, _FACT[5], strict=True))
                     and all(type(item) is tuple and len(item) == 2
                             and type(item[1]) is int
                             and _descriptor_closed_in_scope(item[0], s)
                             and item[0].fd is item[1]
                             for item in _FACT[3]))
        else:
            _require(self._ready is False and _FACT is None and self._fact is None
                     and s.activation._runtime_cache_probe_fact is None)
        return s

    def _guard(self):
        s = RuntimeCacheProbeOwner._pure(self)
        root, cell, fact, count = _ROOT, _CELL, _FACT, self._count_cell
        started, retaining = self._started, self._retaining
        parent = s.parent[0]
        _require(parent[0]._root is parent and parent[0]._source is parent[2]
                 and GatewayContinuationOwner._seal(parent[0]) is parent[2]
                 and _context() == s.context
                 and RuntimeCacheProbeOwner._pure(self) is s
                 and _ROOT is root and _CELL is cell and _FACT is fact
                 and self._count_cell is count
                 and self._started is started and self._retaining is retaining
                 and parent[0]._root is parent and parent[0]._source is parent[2]
                 and GatewayContinuationOwner._seal(parent[0]) is parent[2])
        return s

    def _stat_known(self, name, parent, s, native_registration=None):
        native = _capture_native_work_origin(self, native_registration)
        stat_call = None if native is None else native.operations[3]
        result_type = None if native is None else native.result_type
        missing_type = FileNotFoundError if native is None else native.errors[1]
        # Only exact ENOENT becomes sampled missing data. No read/permission or
        # structural error is relabeled as a cache miss here.
        result = None
        missing = False
        _require(_native_walk_scope(self, native_registration) is s)
        root, cell = self._root_cell, self._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_relative_arguments(s, name, parent)
        try:
            _native_work_origin_tail(self, native_registration, native)
            _require(native is None or (stat_call is native.operations[3]
                     and result_type is native.result_type and missing_type is native.errors[1]))
            if native is None:
                stat_call = os.stat
            if native is not None:
                held_state = _native_pre_actor_state(self, (name, parent, stat_call, result_type,
                                                           missing_type))
                _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
                _native_post_actor_state(self, held_state,
                                         (name, parent, stat_call, result_type, missing_type))
                _native_registration_tail(self, s, cell, root, native_registration, registry)
                _native_work_origin_tail(self, native_registration, native)
                _require(stat_call is native.operations[3] and result_type is native.result_type
                         and missing_type is native.errors[1] and _ROOT is root and _CELL is cell)
            result = stat_call(name, dir_fd=parent, follow_symlinks=False)
        except missing_type as exc:
            _require(type(exc) is missing_type
                     and type(exc.errno) is int
                     and exc.errno == errno.ENOENT and type(exc.filename) is str
                     and exc.filename == name)
            missing = True
        _require(_native_walk_scope(self, native_registration) is s)
        _require(missing or type(result) is (os.stat_result if native is None else result_type))
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_work_origin_tail(self, native_registration, native)
        return result

    def _start(self):
        s = RuntimeCacheProbeOwner._pure(self)
        _require(self._started is False and self._retaining is False and self._ready is False
                 and self._admitting is False)
        root, cell, count = _ROOT, _CELL, self._count_cell
        native_registration = _capture_native_scope(s, cell, root)
        selected = s.parent[1]
        path, proof = selected.plan_row.location.path, selected.proof
        self._admitting = True
        admitted = False
        try:
            actor = _context()
            _require(type(actor) is tuple and len(actor) == 3
                     and all(type(value) is int for value in actor)
                     and RuntimeCacheProbeOwner._pure(self) is s
                     and _ROOT is root and _CELL is cell and self._count_cell is count
                     and s.parent[1] is selected and selected.plan_row.location.path is path
                     and selected.proof is proof and self._started is False
                     and self._retaining is False and self._ready is False)
            admitted = actor == s.context
        except BaseException:
            admitted = False
        finally:
            if self._admitting is True:
                self._admitting = False
        _require(admitted is True)
        self._started = True
        return s, selected, path, proof, native_registration, root, cell, count

    def observe(self):
        s, selected, path, proof, native_registration, root, cell, count = (
            RuntimeCacheProbeOwner._start(self))
        failed = False
        try:
            return RuntimeCacheProbeOwner._observe_owned(
                self, s, selected, path, proof, native_registration, root, cell, count)
        except BaseException:
            self._failed = failed = True
        if failed:
            raise CacheProbeError(self) from None

    def _observe_owned(self, s, selected, path, proof, native_registration, root, cell, count):
        global _FACT
        _require(_native_walk_scope(self, native_registration) is s
                 and _ROOT is root and _CELL is cell and self._count_cell is count)
        native_registry = native_registration.lineage.ledger.scopes
        # Keep the original complete engine return across data allocation. No
        # current history/cursor lookup can substitute for a lost return.
        plan = s.native_probe_plan
        from . import probe_native as engine

        origin = plan.engine_origin
        validate = origin[2][0][1]
        _require(type(validate) is FunctionType and engine is origin[0]
                 and vars(engine).get('_engine_origin_tail') is validate
                 and validate.__code__ is origin[2][0][2])
        validate(origin)
        run = origin[2][10][1]
        finish_tail = origin[2][24][1]
        finish_kind = origin[1][5][0]
        _require(origin[2][10][0] == '_run_fresh_probe'
                 and origin[2][24][0] == '_finished_state_tail')
        actual = run(self, s, native_registration, plan)
        validate(origin)
        _require(type(actual) is finish_kind and actual.execution is self._probe_execution
                 and actual.execution.finished == [True]
                 and actual.execution.owner is self and actual.execution.plan is plan
                 and type(actual.outcome) is tuple and len(actual.outcome) == 4
                 and type(actual.resources) is tuple)
        outcome, resources = actual.outcome, actual.resources
        _require(finish_tail(actual.execution, actual.predecessor, resources) is outcome)
        kind = CacheProbeData
        fields = kind._fields
        members = tuple(vars(kind).get(name) for name in fields)
        constructor, constructor_code = kind.__new__, kind.__new__.__code__
        result = kind(*outcome)
        _require(CacheProbeData is kind and kind._fields is fields
                 and kind.__new__ is constructor and constructor.__code__ is constructor_code
                 and all(vars(kind).get(name) is member
                         for name, member in zip(fields, members, strict=True))
                 and type(result) is kind and tuple.__len__(result) == 4
                 and all(tuple.__getitem__(result, i) is value
                         for i, value in enumerate(outcome)))
        _require(finish_tail(actual.execution, actual.predecessor, resources) is outcome
                 and actual.execution.finished == [True])
        records = tuple(s.records)
        fact = (self, s, result, resources, count, records, selected, path, proof, root)
        _require(_native_walk_scope(self, native_registration) is s and _ROOT is root
                 and self._count_cell is count and self._bytes_read == 0
                 and self._started is True and self._retaining is False
                 and self._ready is False and self._fact is None and _FACT is None
                 and s.parent[1] is selected and selected.plan_row.location.path is path
                 and selected.proof is proof and len(s.records) == len(records)
                 and all(actual is original for actual, original
                         in zip(s.records, records, strict=True))
                 and all(_descriptor_closed_in_scope(row, s) and row.fd is fd
                         for row, fd in resources))
        _native_registration_tail(self, s, cell, root, native_registration, native_registry)
        validate(origin)
        _require(finish_tail(actual.execution, actual.predecessor, resources) is outcome
                 and actual.execution.finished == [True]
                 and self._ready is False and self._fact is None and _FACT is None
                 and self._count_cell is count and self._bytes_read == 0)
        self._fact = _FACT = s.activation._runtime_cache_probe_fact = fact
        self._ready = True
        return self


    def current_binding(self):
        s = RuntimeCacheProbeOwner._pure(self)
        _require(self._ready is True and self._retaining is False)
        fact, root, cell = _FACT, _ROOT, _CELL
        native_registration = _capture_native_scope(s, cell, root)
        native_registry = native_registration.lineage.ledger.scopes
        admitted = failed = False
        try:
            actor = _context()
            _require(type(actor) is tuple and len(actor) == 3
                     and all(type(value) is int for value in actor))
            admitted = actor == s.context
            _require(admitted is True and _ROOT is root and _FACT is fact
                     and self._fact is fact and s.activation._runtime_cache_probe_fact is fact
                     and _native_walk_scope(self, native_registration) is s
                     and _FACT is fact and self._fact is fact
                     and s.activation._runtime_cache_probe_fact is fact)
            _native_registration_tail(self, s, cell, root, native_registration, native_registry)
        except BaseException:
            failed = True
            if admitted:
                self._failed = True
        if failed:
            raise CacheProbeError(self) from None
        return fact
