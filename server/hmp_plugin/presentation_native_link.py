"""Experimental executable-link lifecycle on the shared native kernel.

The early entry now binds this engine before startup observations. The complete
path remains under qualification: actual native traversal exceeds its unchanged
fixture deadline. Neither this module nor its constructors enable image serving.
Original actor/parent/custody/byte-count and reserved-close boundaries remain;
full traversal/fault/runtime/device acceptance is required before installation.
"""
from __future__ import annotations

import sys
from operator import is_not as _native_identity_is_not
from types import FunctionType, ModuleType, CellType, BuiltinFunctionType
from typing import NamedTuple

from . import presentation_link_path_policy as policy
from . import presentation_native_metadata as metadata
from . import presentation_startup_artifacts as artifacts_module
from . import presentation_metadata_custody as custody_module
from .presentation_startup_artifacts import (
    StartupArtifactOwner, _NativeLinkMetadataResource, _NativeOpenedDescriptor,
    _NativeOpenAllocation, _LinkSnapshot, _LinkTargetObservation, _HashedArtifact, _RuntimeSource,
    _NativeLinkBytesResource, _LinkRead, _NativeReadlinkObservation,
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


class _LinkRecheck(NamedTuple):
    owner: object
    registration: object
    fact: object
    finishes: tuple
    count: tuple

    def __repr__(self):
        return '<LinkRecheck original closed metadata-only handoffs redacted>'

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
_RECORD_ALLOCATOR = object.__new__


_ENGINE_FUNCTIONS = (
    '_capture_engine', '_dependency_mirrors', '_engine_origin_tail', '_execution_mirrors',
    '_opened_chain_tail', '_lifetime_tail', '_resource_tail', '_prepare_shared_consumer',
    '_latch_shared_consumer', '_make_shared_commit', '_commit_shared_tail',
    '_publish_shared_ack', '_acked_shared_history', '_resource_bindings', '_byte_record_tail',
    '_make_shared_bytes_commit', '_commit_shared_bytes_tail', '_publish_shared_bytes_ack',
    '_acked_shared_bytes_history', '_produce_shared', '_consume_shared', '_ack_shared',
    '_attached_shared', '_retired_shared', '_effect_pin', '_new_execution', '_append_action',
    '_finish_mirrors', '_finish_path', '_drive_native_path', '_path_history_mirrors',
    '_history_phase_mirrors', '_finish_history', '_snapshot_history_mirrors', '_snapshot',
    '_make_fact', '_recheck', '_open_shared', '_close_known_shared', '_prepare_open_shared',
)


def _dependency_mirrors(dependencies, *, _type=type, _tuple=tuple, _dict=dict,
                        _str=str, _len=len, _vars=vars, _any=any, _zip=zip,
                        _module=ModuleType, _function=FunctionType, _cell=CellType,
                        _error=ArtifactObservationError):
    """Pure original namespaces/classes/code; no owner, callback or work grant."""
    if (_type(dependencies) is not _tuple or _len(dependencies) != 4
            or _type(dependencies[0]) is not _module
            or _type(dependencies[1]) is not _dict
            or _vars(dependencies[0]) is not dependencies[1]
            or _any(_type(k) is not _str for k in dependencies[1])
            or _type(dependencies[2]) is not _dict
            or dependencies[1].get('modules') is not dependencies[2]
            or _any(_type(k) is not _str for k in dependencies[2])
            or _type(dependencies[3]) is not _tuple or _len(dependencies[3]) != 5):
        raise _error from None
    checked_namespaces = []
    expected_modules = ('hmp_plugin.presentation_native_link',
                        'hmp_plugin.presentation_native_metadata',
                        'hmp_plugin.presentation_startup_artifacts',
                        'hmp_plugin.presentation_metadata_custody',
                        'hmp_plugin.presentation_link_path_policy')
    for row, expected_name in _zip(dependencies[3], expected_modules, strict=True):
        if (_type(row) is not _tuple or _len(row) != 6
                or _type(row[0]) is not _str or row[0] != expected_name
                or _type(row[1]) is not _module or _type(row[2]) is not _dict
                or _any(_type(k) is not _str for k in row[2])
                or dependencies[2].get(expected_name) is not row[1]
                or _vars(row[1]) is not row[2]
                or _type(row[3]) is not _tuple or _len(row[2]) != _len(row[3])
                or _any(_type(pair) is not _tuple or _len(pair) != 2
                        or _type(pair[0]) is not _str or pair[0] not in row[2]
                        or row[2][pair[0]] is not pair[1] for pair in row[3])
                or _type(row[4]) is not _tuple or _type(row[5]) is not _tuple):
            raise _error from None
        checked_namespaces.append(row[2])
        for class_row in row[4]:
            if _type(class_row) is not _tuple or _len(class_row) != 3:
                raise _error from None
            kind, bases, members = class_row
            if _type(kind) is not _type or kind.__bases__ is not bases:
                raise _error from None
            names = _vars(kind)
            if (_any(_type(k) is not _str for k in names)
                    or _type(members) is not _tuple or _len(names) != _len(members)
                    or _any(_type(pair) is not _tuple or _len(pair) != 2
                            or _type(pair[0]) is not _str or pair[0] not in names
                            or names[pair[0]] is not pair[1] for pair in members)):
                raise _error from None
        for function_row in row[5]:
            if _type(function_row) is not _tuple or _len(function_row) != 8:
                raise _error from None
            function, code, namespace, defaults, kw, pairs, closure, cells = function_row
            if (_type(function) is not _function or function.__code__ is not code
                    or function.__globals__ is not namespace or _type(namespace) is not _dict
                    or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kw or _type(pairs) is not _tuple
                    or function.__closure__ is not closure or _type(cells) is not _tuple):
                raise _error from None
            if not _any(namespace is prior for prior in checked_namespaces):
                if _any(_type(k) is not _str for k in namespace):
                    raise _error from None
                checked_namespaces.append(namespace)
            if kw is None:
                if _len(pairs) != 0:
                    raise _error from None
            elif (_type(kw) is not _dict or _any(_type(k) is not _str for k in kw)
                  or _len(kw) != _len(pairs)
                  or _any(_type(pair) is not _tuple or _len(pair) != 2
                          or _type(pair[0]) is not _str or pair[0] not in kw
                          or kw[pair[0]] is not pair[1] for pair in pairs)):
                raise _error from None
            if closure is None:
                if _len(cells) != 0:
                    raise _error from None
            elif (_type(closure) is not _tuple or _len(closure) != _len(cells)
                  or _any(_type(cell) is not _cell or cell.cell_contents is not value
                          for cell, value in _zip(closure, cells, strict=True))):
                raise _error from None
    return dependencies


def _capture_engine(*, _type=type, _tuple=tuple, _dict=dict, _str=str,
                    _len=len, _vars=vars, _any=any, _zip=zip,
                    _module=ModuleType, _function=FunctionType, _cell=CellType, _builtin=BuiltinFunctionType,
                    _error=RuntimeError):
    """Capture all original inputs before any helper; never a late fallback."""
    checker = _engine_origin_tail
    if _type(checker) is not _function or checker.__globals__ is not globals():
        raise _error from None
    checker_code, checker_defaults, checker_kw = checker.__code__, checker.__defaults__, checker.__kwdefaults__
    if checker_kw is not None and (_type(checker_kw) is not _dict
                                  or _any(_type(k) is not _str for k in checker_kw)):
        raise _error from None
    checker_pairs = () if checker_kw is None else tuple(checker_kw.items())
    # Hold this literal row before helper callbacks. A later equivalent row is DATA,
    # not the original audit input retained by the actual capture return.
    checker_row = ('_engine_origin_tail', checker, checker_code, globals(),
                   checker_defaults, checker_kw, checker_pairs)
    if (_type(sys) is not _module or _type(sys.modules) is not _dict
            or _any(_type(k) is not _str for k in sys.modules)):
        raise _error from None
    own = sys.modules.get('hmp_plugin.presentation_native_link')
    if _type(own) is not _module or _vars(own) is not globals():
        raise _error from None
    modules = (own, metadata, artifacts_module, custody_module, policy)
    rows, seen_classes, seen_functions = [], set(), set()
    expected_modules = ('hmp_plugin.presentation_native_link',
                        'hmp_plugin.presentation_native_metadata',
                        'hmp_plugin.presentation_startup_artifacts',
                        'hmp_plugin.presentation_metadata_custody',
                        'hmp_plugin.presentation_link_path_policy')
    for module, expected_name in zip(modules, expected_modules, strict=True):
        if _type(module) is not _module:
            raise _error from None
        namespace = vars(module)
        if (_any(_type(k) is not _str for k in namespace)
                or _type(namespace.get('__name__')) is not _str
                or namespace['__name__'] != expected_name
                or sys.modules.get(expected_name) is not module):
            raise _error from None
        classes, code = [], []
        candidates = []
        for value in namespace.values():
            if type(value) is FunctionType:
                candidates.append(value)
            elif (type(value) is type and value not in seen_classes
                  and type(value.__module__) is str and value.__module__.startswith('hmp_')):
                seen_classes.add(value)
                members = tuple(vars(value).items())
                classes.append((value, value.__bases__, members))
                for _, member in members:
                    if type(member) in (classmethod, staticmethod):
                        member = member.__func__
                    if type(member) is FunctionType:
                        candidates.append(member)
                    elif type(member) is property:
                        candidates.extend(function for function in
                                          (member.fget, member.fset, member.fdel)
                                          if type(function) is FunctionType)
        for function in candidates:
            if function in seen_functions:
                continue
            seen_functions.add(function)
            kw, closure = function.__kwdefaults__, function.__closure__
            if kw is not None and (_type(kw) is not _dict or _any(_type(k) is not _str for k in kw)):
                raise _error from None
            code.append((function, function.__code__, function.__globals__, function.__defaults__,
                         kw, () if kw is None else tuple(kw.items()), closure,
                         () if closure is None else tuple(cell.cell_contents for cell in closure)))
        rows.append((module.__name__, module, namespace, tuple(namespace.items()),
                     tuple(classes), tuple(code)))
    dependencies = (sys, vars(sys), sys.modules, tuple(rows))
    if _type(dependencies) is not _tuple or _len(dependencies) != 4 or _type(dependencies[0]) is not _module or (_type(dependencies[1]) is not _dict) or (_vars(dependencies[0]) is not dependencies[1]) or _any((_type(k) is not _str for k in dependencies[1])) or (_type(dependencies[2]) is not _dict) or (dependencies[1].get('modules') is not dependencies[2]) or _any((_type(k) is not _str for k in dependencies[2])) or (_type(dependencies[3]) is not _tuple) or (_len(dependencies[3]) != 5):
        raise _error from None
    checked_namespaces = []
    expected_modules = ('hmp_plugin.presentation_native_link', 'hmp_plugin.presentation_native_metadata', 'hmp_plugin.presentation_startup_artifacts', 'hmp_plugin.presentation_metadata_custody', 'hmp_plugin.presentation_link_path_policy')
    for row, expected_name in _zip(dependencies[3], expected_modules, strict=True):
        if _type(row) is not _tuple or _len(row) != 6 or _type(row[0]) is not _str or (row[0] != expected_name) or (_type(row[1]) is not _module) or (_type(row[2]) is not _dict) or _any((_type(k) is not _str for k in row[2])) or (dependencies[2].get(expected_name) is not row[1]) or (_vars(row[1]) is not row[2]) or (_type(row[3]) is not _tuple) or (_len(row[2]) != _len(row[3])) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in row[2]) or (row[2][pair[0]] is not pair[1]) for pair in row[3])) or (_type(row[4]) is not _tuple) or (_type(row[5]) is not _tuple):
            raise _error from None
        checked_namespaces.append(row[2])
        for class_row in row[4]:
            if _type(class_row) is not _tuple or _len(class_row) != 3:
                raise _error from None
            kind, bases, members = class_row
            if _type(kind) is not _type or kind.__bases__ is not bases:
                raise _error from None
            names = _vars(kind)
            if _any((_type(k) is not _str for k in names)) or _type(members) is not _tuple or _len(names) != _len(members) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in names) or (names[pair[0]] is not pair[1]) for pair in members)):
                raise _error from None
        for function_row in row[5]:
            if _type(function_row) is not _tuple or _len(function_row) != 8:
                raise _error from None
            function, code, namespace, defaults, kw, pairs, closure, cells = function_row
            if _type(function) is not _function or function.__code__ is not code or function.__globals__ is not namespace or (_type(namespace) is not _dict) or (function.__defaults__ is not defaults) or (function.__kwdefaults__ is not kw) or (_type(pairs) is not _tuple) or (function.__closure__ is not closure) or (_type(cells) is not _tuple):
                raise _error from None
            if not _any((namespace is prior for prior in checked_namespaces)):
                if _any((_type(k) is not _str for k in namespace)):
                    raise _error from None
                checked_namespaces.append(namespace)
            if kw is None:
                if _len(pairs) != 0:
                    raise _error from None
            elif _type(kw) is not _dict or _any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in kw) or (kw[pair[0]] is not pair[1]) for pair in pairs)):
                raise _error from None
            if closure is None:
                if _len(cells) != 0:
                    raise _error from None
            elif _type(closure) is not _tuple or _len(closure) != _len(cells) or _any((_type(cell) is not _cell or cell.cell_contents is not value for cell, value in _zip(closure, cells, strict=True))):
                raise _error from None
    audit_checker, audit_kw, audit_pairs = checker, checker_kw, checker_pairs
    if (_type(audit_checker) is not _function or _type(audit_kw) is not _dict
            or audit_checker.__kwdefaults__ is not audit_kw
            or _any(_type(k) is not _str for k in audit_kw)):
        raise _error from None
    if _type(audit_pairs) is not _tuple or _len(audit_kw) != _len(audit_pairs):
        raise _error from None
    audit_originals = {}
    for audit_pair in audit_pairs:
        if (_type(audit_pair) is not _tuple or _len(audit_pair) != 2
                or _type(audit_pair[0]) is not _str):
            raise _error from None
        audit_name, audit_expected = audit_pair
        if (audit_name in audit_originals or audit_name not in audit_kw
                or audit_kw[audit_name] is not audit_expected):
            raise _error from None
        audit_originals[audit_name] = audit_expected
    audit_id = audit_originals.get('_id')
    audit_map = audit_originals.get('_map')
    audit_not = audit_originals.get('_not_identity')
    if (_type(audit_id) is not _builtin or audit_id.__name__ != 'id'
            or _type(audit_id.__self__) is not _module
            or dependencies[2].get('builtins') is not audit_id.__self__):
        raise _error from None
    audit_builtins = _vars(audit_id.__self__)
    if (_any(_type(k) is not _str for k in audit_builtins)
            or audit_checker.__builtins__ is not audit_builtins):
        raise _error from None
    for audit_name, audit_value in (('type',_type), ('tuple',_tuple), ('dict',_dict),
            ('str',_str), ('len',_len), ('vars',_vars), ('any',_any), ('zip',_zip),
            ('id',audit_id), ('map',audit_map)):
        if (audit_builtins.get(audit_name) is not audit_value
                or audit_originals.get('_'+audit_name) is not audit_value):
            raise _error from None
    if _type(audit_map) is not _type:
        raise _error from None
    audit_map_names = _vars(audit_map)
    if _any(_type(k) is not _str for k in audit_map_names):
        raise _error from None
    audit_new = audit_map_names.get('__new__')
    if (_type(audit_new) is not _builtin or audit_new.__self__ is not audit_map
            or audit_new.__name__ != '__new__' or audit_map.__name__ != 'map'
            or audit_map.__module__ != 'builtins'
            or _type(audit_not) is not _builtin or audit_not.__name__ != 'is_not'
            or _type(audit_not.__self__) is not _module
            or dependencies[2].get('_operator') is not audit_not.__self__):
        raise _error from None
    audit_operator = _vars(audit_not.__self__)
    if (_any(_type(k) is not _str for k in audit_operator)
            or audit_operator.get('is_not') is not audit_not):
        raise _error from None
    functions = []
    for name in _ENGINE_FUNCTIONS:
        function = globals().get(name)
        if type(function) is not FunctionType:
            raise _error from None
        kw = function.__kwdefaults__
        if kw is not None and (_type(kw) is not _dict or _any(_type(k) is not _str for k in kw)):
            raise _error from None
        if name == '_engine_origin_tail':
            if (function is not checker or function.__code__ is not checker_code
                    or function.__globals__ is not checker_row[3]
                    or function.__defaults__ is not checker_defaults or kw is not checker_kw):
                raise _error from None
            functions.append(checker_row)
        else:
            functions.append((name, function, function.__code__, function.__globals__,
                              function.__defaults__, kw, () if kw is None else tuple(kw.items())))
    functions = tuple(functions)
    kernel = []
    for name, function in sorted(vars(metadata).items()):
        if name.startswith('_') and type(function) is FunctionType:
            kw = function.__kwdefaults__
            if kw is not None and (_type(kw) is not _dict or _any(_type(k) is not _str for k in kw)):
                raise _error from None
            kernel.append((name, function, function.__code__, function.__globals__,
                           function.__defaults__, kw, () if kw is None else tuple(kw.items())))
    kernel = tuple(kernel)
    kinds = (_LinkExecution, _LinkMetadataConsumer, _LinkMetadataCommit,
             _NativeLinkMetadataResource, _LinkBytesConsumer, _LinkBytesCommit,
             _NativeLinkBytesResource, metadata._LinkBytesOperation, metadata._LinkBytesResult,
             metadata._LinkBytesReturn, _LinkRead, _LinkAction, _LinkPathFinish,
             _NativeReadlinkObservation, _LinkSnapshot, _LinkTargetObservation, _LinkRecheck)
    types = []
    for kind in kinds:
        if type(kind) is not type:
            raise _error from None
        names = vars(kind)
        fields = None if kind is _LinkRead else names.get('_fields')
        constructor = names.get('__init__' if fields is None else '__new__')
        if type(constructor) is staticmethod:
            constructor = constructor.__func__
        if type(constructor) is not FunctionType:
            raise _error from None
        if fields is not None and (_type(fields) is not _tuple
                                   or _any(_type(n) is not _str for n in fields)):
            raise _error from None
        members = tuple(names.items()) if fields is None else tuple(names.get(n) for n in fields)
        dispatch = tuple((name, names.get(name)) for name in (
            '__getattribute__', '__getattr__', '__getitem__', '__len__', '__iter__',
            '__setattr__', '__delattr__', '__eq__', '__ne__', '__hash__', '__bool__'))
        types.append((kind, fields, members, constructor, constructor.__code__,
                      constructor.__globals__, constructor.__defaults__, kind.__bases__, dispatch))
    types = tuple(types)
    # Immutable expected DATA derived only from the already held original rows.
    # It does not cache a mutable-state audit or authorize a native effect.
    layout_modules = []
    for layout_module in dependencies[3]:
        layout_classes = []
        for layout_class in layout_module[4]:
            layout_members = layout_class[2]
            layout_classes.append((layout_class,
                _tuple(pair[0] for pair in layout_members),
                _tuple(pair[1] for pair in layout_members)))
        layout_modules.append((layout_module, _tuple(layout_classes)))
    layout = (dependencies, _tuple(layout_modules))
    origin = (modules[0], types, functions, kernel, dependencies, layout)
    # Immutable DATA only. Parent/root custody must retain this literal return before
    # any fast dispatch can be eligible; generic validation is still complete below.
    audit_record = (origin, layout, checker_row)
    if (globals().get('_engine_origin_tail') is not checker
            or checker.__code__ is not checker_code or checker.__defaults__ is not checker_defaults
            or checker.__kwdefaults__ is not checker_kw
            or type(checker_kw) is not dict or any(type(k) is not str for k in checker_kw)
            or len(checker_kw) != len(checker_pairs)
            or any(k not in checker_kw or checker_kw[k] is not value for k, value in checker_pairs)):
        raise _error from None
    layout = origin[5]
    if (_type(layout) is not _tuple or _len(layout) != 2
            or layout[0] is not dependencies or _type(layout[1]) is not _tuple
            or _len(layout[1]) != _len(dependencies[3])):
        raise _error from None
    for layout_row, layout_module in _zip(layout[1], dependencies[3], strict=True):
        if (_type(layout_row) is not _tuple or _len(layout_row) != 2
                or layout_row[0] is not layout_module
                or _type(layout_module) is not _tuple or _len(layout_module) != 6
                or _type(layout_module[4]) is not _tuple
                or _type(layout_row[1]) is not _tuple
                or _len(layout_row[1]) != _len(layout_module[4])):
            raise _error from None
        for layout_class_row, layout_class in _zip(layout_row[1], layout_module[4], strict=True):
            if (_type(layout_class_row) is not _tuple or _len(layout_class_row) != 3
                    or layout_class_row[0] is not layout_class
                    or _type(layout_class) is not _tuple or _len(layout_class) != 3
                    or _type(layout_class[2]) is not _tuple
                    or _type(layout_class_row[1]) is not _tuple
                    or _type(layout_class_row[2]) is not _tuple
                    or _len(layout_class_row[1]) != _len(layout_class[2])
                    or _len(layout_class_row[2]) != _len(layout_class[2])):
                raise _error from None
            layout_seen = {}
            for layout_pair, layout_key, layout_value in _zip(
                    layout_class[2], layout_class_row[1], layout_class_row[2], strict=True):
                if (_type(layout_pair) is not _tuple or _len(layout_pair) != 2
                        or _type(layout_key) is not _str
                        or layout_pair[0] is not layout_key
                        or layout_pair[1] is not layout_value
                        or layout_key in layout_seen):
                    raise _error from None
                layout_seen[layout_key] = layout_value
    if checker(origin) is not origin:
        raise _error from None
    if _type(dependencies) is not _tuple or _len(dependencies) != 4 or _type(dependencies[0]) is not _module or (_type(dependencies[1]) is not _dict) or (_vars(dependencies[0]) is not dependencies[1]) or _any((_type(k) is not _str for k in dependencies[1])) or (_type(dependencies[2]) is not _dict) or (dependencies[1].get('modules') is not dependencies[2]) or _any((_type(k) is not _str for k in dependencies[2])) or (_type(dependencies[3]) is not _tuple) or (_len(dependencies[3]) != 5):
        raise _error from None
    checked_namespaces = []
    expected_modules = ('hmp_plugin.presentation_native_link', 'hmp_plugin.presentation_native_metadata', 'hmp_plugin.presentation_startup_artifacts', 'hmp_plugin.presentation_metadata_custody', 'hmp_plugin.presentation_link_path_policy')
    for row, expected_name in _zip(dependencies[3], expected_modules, strict=True):
        if _type(row) is not _tuple or _len(row) != 6 or _type(row[0]) is not _str or (row[0] != expected_name) or (_type(row[1]) is not _module) or (_type(row[2]) is not _dict) or _any((_type(k) is not _str for k in row[2])) or (dependencies[2].get(expected_name) is not row[1]) or (_vars(row[1]) is not row[2]) or (_type(row[3]) is not _tuple) or (_len(row[2]) != _len(row[3])) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in row[2]) or (row[2][pair[0]] is not pair[1]) for pair in row[3])) or (_type(row[4]) is not _tuple) or (_type(row[5]) is not _tuple):
            raise _error from None
        checked_namespaces.append(row[2])
        for class_row in row[4]:
            if _type(class_row) is not _tuple or _len(class_row) != 3:
                raise _error from None
            kind, bases, members = class_row
            if _type(kind) is not _type or kind.__bases__ is not bases:
                raise _error from None
            names = _vars(kind)
            if _any((_type(k) is not _str for k in names)) or _type(members) is not _tuple or _len(names) != _len(members) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in names) or (names[pair[0]] is not pair[1]) for pair in members)):
                raise _error from None
        for function_row in row[5]:
            if _type(function_row) is not _tuple or _len(function_row) != 8:
                raise _error from None
            function, code, namespace, defaults, kw, pairs, closure, cells = function_row
            if _type(function) is not _function or function.__code__ is not code or function.__globals__ is not namespace or (_type(namespace) is not _dict) or (function.__defaults__ is not defaults) or (function.__kwdefaults__ is not kw) or (_type(pairs) is not _tuple) or (function.__closure__ is not closure) or (_type(cells) is not _tuple):
                raise _error from None
            if not _any((namespace is prior for prior in checked_namespaces)):
                if _any((_type(k) is not _str for k in namespace)):
                    raise _error from None
                checked_namespaces.append(namespace)
            if kw is None:
                if _len(pairs) != 0:
                    raise _error from None
            elif _type(kw) is not _dict or _any((_type(k) is not _str for k in kw)) or _len(kw) != _len(pairs) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in kw) or (kw[pair[0]] is not pair[1]) for pair in pairs)):
                raise _error from None
            if closure is None:
                if _len(cells) != 0:
                    raise _error from None
            elif _type(closure) is not _tuple or _len(closure) != _len(cells) or _any((_type(cell) is not _cell or cell.cell_contents is not value for cell, value in _zip(closure, cells, strict=True))):
                raise _error from None
    audit_checker, audit_kw, audit_pairs = checker, checker_kw, checker_pairs
    if (_type(audit_checker) is not _function or _type(audit_kw) is not _dict
            or audit_checker.__kwdefaults__ is not audit_kw
            or _any(_type(k) is not _str for k in audit_kw)):
        raise _error from None
    if _type(audit_pairs) is not _tuple or _len(audit_kw) != _len(audit_pairs):
        raise _error from None
    audit_originals = {}
    for audit_pair in audit_pairs:
        if (_type(audit_pair) is not _tuple or _len(audit_pair) != 2
                or _type(audit_pair[0]) is not _str):
            raise _error from None
        audit_name, audit_expected = audit_pair
        if (audit_name in audit_originals or audit_name not in audit_kw
                or audit_kw[audit_name] is not audit_expected):
            raise _error from None
        audit_originals[audit_name] = audit_expected
    audit_id = audit_originals.get('_id')
    audit_map = audit_originals.get('_map')
    audit_not = audit_originals.get('_not_identity')
    if (_type(audit_id) is not _builtin or audit_id.__name__ != 'id'
            or _type(audit_id.__self__) is not _module
            or dependencies[2].get('builtins') is not audit_id.__self__):
        raise _error from None
    audit_builtins = _vars(audit_id.__self__)
    if (_any(_type(k) is not _str for k in audit_builtins)
            or audit_checker.__builtins__ is not audit_builtins):
        raise _error from None
    for audit_name, audit_value in (('type',_type), ('tuple',_tuple), ('dict',_dict),
            ('str',_str), ('len',_len), ('vars',_vars), ('any',_any), ('zip',_zip),
            ('id',audit_id), ('map',audit_map)):
        if (audit_builtins.get(audit_name) is not audit_value
                or audit_originals.get('_'+audit_name) is not audit_value):
            raise _error from None
    if _type(audit_map) is not _type:
        raise _error from None
    audit_map_names = _vars(audit_map)
    if _any(_type(k) is not _str for k in audit_map_names):
        raise _error from None
    audit_new = audit_map_names.get('__new__')
    if (_type(audit_new) is not _builtin or audit_new.__self__ is not audit_map
            or audit_new.__name__ != '__new__' or audit_map.__name__ != 'map'
            or audit_map.__module__ != 'builtins'
            or _type(audit_not) is not _builtin or audit_not.__name__ != 'is_not'
            or _type(audit_not.__self__) is not _module
            or dependencies[2].get('_operator') is not audit_not.__self__):
        raise _error from None
    audit_operator = _vars(audit_not.__self__)
    if (_any(_type(k) is not _str for k in audit_operator)
            or audit_operator.get('is_not') is not audit_not):
        raise _error from None
    layout = origin[5]
    if (_type(layout) is not _tuple or _len(layout) != 2
            or layout[0] is not dependencies or _type(layout[1]) is not _tuple
            or _len(layout[1]) != _len(dependencies[3])):
        raise _error from None
    for layout_row, layout_module in _zip(layout[1], dependencies[3], strict=True):
        if (_type(layout_row) is not _tuple or _len(layout_row) != 2
                or layout_row[0] is not layout_module
                or _type(layout_module) is not _tuple or _len(layout_module) != 6
                or _type(layout_module[4]) is not _tuple
                or _type(layout_row[1]) is not _tuple
                or _len(layout_row[1]) != _len(layout_module[4])):
            raise _error from None
        for layout_class_row, layout_class in _zip(layout_row[1], layout_module[4], strict=True):
            if (_type(layout_class_row) is not _tuple or _len(layout_class_row) != 3
                    or layout_class_row[0] is not layout_class
                    or _type(layout_class) is not _tuple or _len(layout_class) != 3
                    or _type(layout_class[2]) is not _tuple
                    or _type(layout_class_row[1]) is not _tuple
                    or _type(layout_class_row[2]) is not _tuple
                    or _len(layout_class_row[1]) != _len(layout_class[2])
                    or _len(layout_class_row[2]) != _len(layout_class[2])):
                raise _error from None
            layout_seen = {}
            for layout_pair, layout_key, layout_value in _zip(
                    layout_class[2], layout_class_row[1], layout_class_row[2], strict=True):
                if (_type(layout_pair) is not _tuple or _len(layout_pair) != 2
                        or _type(layout_key) is not _str
                        or layout_pair[0] is not layout_key
                        or layout_pair[1] is not layout_value
                        or layout_key in layout_seen):
                    raise _error from None
                layout_seen[layout_key] = layout_value
    if (_type(audit_record) is not _tuple or _len(audit_record) != 3
            or audit_record[0] is not origin or audit_record[1] is not layout
            or origin[5] is not layout or audit_record[2] is not checker_row
            or _len(_tuple(row for row in origin[2] if row is checker_row)) != 1
            or checker_row[1] is not checker or checker_row[2] is not checker_code):
        raise _error from None
    return audit_record

def _engine_origin_tail(origin, *, _type=type, _tuple=tuple, _dict=dict, _str=str, _len=len, _vars=vars, _any=any, _zip=zip, _module=ModuleType, _function=FunctionType, _cell=CellType, _id=id, _builtin=BuiltinFunctionType, _map=map, _not_identity=_native_identity_is_not, _error=ArtifactObservationError):
    """Validate the actual early packet; never capture a current replacement."""
    if _type(origin) is not _tuple or _len(origin) != 6:
        raise _error from None
    dependencies = origin[4]
    if _type(dependencies) is not _tuple or _len(dependencies) != 4 or _type(dependencies[0]) is not _module or (_type(dependencies[1]) is not _dict) or (_vars(dependencies[0]) is not dependencies[1]) or _any((_type(k) is not _str for k in dependencies[1])) or (_type(dependencies[2]) is not _dict) or (dependencies[1].get('modules') is not dependencies[2]) or _any((_type(k) is not _str for k in dependencies[2])) or (_type(dependencies[3]) is not _tuple) or (_len(dependencies[3]) != 5):
        raise _error from None
    layout = origin[5]
    if (_type(layout) is not _tuple or _len(layout) != 2
            or layout[0] is not dependencies or _type(layout[1]) is not _tuple
            or _len(layout[1]) != _len(dependencies[3])):
        raise _error from None
    for layout_row, layout_module in _zip(layout[1], dependencies[3], strict=True):
        if (_type(layout_row) is not _tuple or _len(layout_row) != 2
                or layout_row[0] is not layout_module
                or _type(layout_module) is not _tuple or _len(layout_module) != 6
                or _type(layout_module[4]) is not _tuple
                or _type(layout_row[1]) is not _tuple
                or _len(layout_row[1]) != _len(layout_module[4])):
            raise _error from None
        for layout_class_row, layout_class in _zip(layout_row[1], layout_module[4], strict=True):
            if (_type(layout_class_row) is not _tuple or _len(layout_class_row) != 3
                    or layout_class_row[0] is not layout_class
                    or _type(layout_class) is not _tuple or _len(layout_class) != 3
                    or _type(layout_class[2]) is not _tuple
                    or _type(layout_class_row[1]) is not _tuple
                    or _type(layout_class_row[2]) is not _tuple
                    or _len(layout_class_row[1]) != _len(layout_class[2])
                    or _len(layout_class_row[2]) != _len(layout_class[2])):
                raise _error from None
            layout_seen = {}
            for layout_pair, layout_key, layout_value in _zip(
                    layout_class[2], layout_class_row[1], layout_class_row[2], strict=True):
                if (_type(layout_pair) is not _tuple or _len(layout_pair) != 2
                        or _type(layout_key) is not _str
                        or layout_pair[0] is not layout_key
                        or layout_pair[1] is not layout_value
                        or layout_key in layout_seen):
                    raise _error from None
                layout_seen[layout_key] = layout_value
    if _type(origin[2]) is not _tuple:
        raise _error from None
    audit_rows = _tuple(row for row in origin[2]
        if _type(row) is _tuple and _len(row)==7 and _type(row[0]) is _str
        and row[0]=='_engine_origin_tail')
    if _len(audit_rows)!=1:
        raise _error from None
    audit_checker, audit_kw, audit_pairs = audit_rows[0][1], audit_rows[0][5], audit_rows[0][6]
    if (_type(audit_checker) is not _function or _type(audit_kw) is not _dict
            or audit_checker.__kwdefaults__ is not audit_kw
            or _any(_type(k) is not _str for k in audit_kw)):
        raise _error from None
    if _type(audit_pairs) is not _tuple or _len(audit_kw) != _len(audit_pairs):
        raise _error from None
    audit_originals = {}
    for audit_pair in audit_pairs:
        if (_type(audit_pair) is not _tuple or _len(audit_pair) != 2
                or _type(audit_pair[0]) is not _str):
            raise _error from None
        audit_name, audit_expected = audit_pair
        if (audit_name in audit_originals or audit_name not in audit_kw
                or audit_kw[audit_name] is not audit_expected):
            raise _error from None
        audit_originals[audit_name] = audit_expected
    audit_id = audit_originals.get('_id')
    audit_map = audit_originals.get('_map')
    audit_not = audit_originals.get('_not_identity')
    if (_type(audit_id) is not _builtin or audit_id.__name__ != 'id'
            or _type(audit_id.__self__) is not _module
            or dependencies[2].get('builtins') is not audit_id.__self__):
        raise _error from None
    audit_builtins = _vars(audit_id.__self__)
    if (_any(_type(k) is not _str for k in audit_builtins)
            or audit_checker.__builtins__ is not audit_builtins):
        raise _error from None
    for audit_name, audit_value in (('type',_type), ('tuple',_tuple), ('dict',_dict),
            ('str',_str), ('len',_len), ('vars',_vars), ('any',_any), ('zip',_zip),
            ('id',audit_id), ('map',audit_map)):
        if (audit_builtins.get(audit_name) is not audit_value
                or audit_originals.get('_'+audit_name) is not audit_value):
            raise _error from None
    if _type(audit_map) is not _type:
        raise _error from None
    audit_map_names = _vars(audit_map)
    if _any(_type(k) is not _str for k in audit_map_names):
        raise _error from None
    audit_new = audit_map_names.get('__new__')
    if (_type(audit_new) is not _builtin or audit_new.__self__ is not audit_map
            or audit_new.__name__ != '__new__' or audit_map.__name__ != 'map'
            or audit_map.__module__ != 'builtins'
            or _type(audit_not) is not _builtin or audit_not.__name__ != 'is_not'
            or _type(audit_not.__self__) is not _module
            or dependencies[2].get('_operator') is not audit_not.__self__):
        raise _error from None
    audit_operator = _vars(audit_not.__self__)
    if (_any(_type(k) is not _str for k in audit_operator)
            or audit_operator.get('is_not') is not audit_not):
        raise _error from None
    if _id is not audit_id or _map is not audit_map or _not_identity is not audit_not:
        raise _error from None
    checked_namespaces = {}
    expected_modules = ('hmp_plugin.presentation_native_link', 'hmp_plugin.presentation_native_metadata', 'hmp_plugin.presentation_startup_artifacts', 'hmp_plugin.presentation_metadata_custody', 'hmp_plugin.presentation_link_path_policy')
    for row, expected_name in _zip(dependencies[3], expected_modules, strict=True):
        if _type(row) is not _tuple or _len(row) != 6 or _type(row[0]) is not _str or (row[0] != expected_name) or (_type(row[1]) is not _module) or (_type(row[2]) is not _dict) or _any(_map(_not_identity, _map(_type, row[2]), (_str,) * _len(row[2]))) or (dependencies[2].get(expected_name) is not row[1]) or (_vars(row[1]) is not row[2]) or (_type(row[3]) is not _tuple) or (_len(row[2]) != _len(row[3])) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in row[2]) or (row[2][pair[0]] is not pair[1]) for pair in row[3])) or (_type(row[4]) is not _tuple) or (_type(row[5]) is not _tuple):
            raise _error from None
        checked_namespaces[_id(row[2])] = row[2]
        for class_row in row[4]:
            if _type(class_row) is not _tuple or _len(class_row) != 3:
                raise _error from None
            kind, bases, members = class_row
            if _type(kind) is not _type or kind.__bases__ is not bases:
                raise _error from None
            names = _vars(kind)
            if _any(_map(_not_identity, _map(_type, names), (_str,) * _len(names))) or _type(members) is not _tuple or _len(names) != _len(members) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in names) or (names[pair[0]] is not pair[1]) for pair in members)):
                raise _error from None
        for function_row in row[5]:
            if _type(function_row) is not _tuple or _len(function_row) != 8:
                raise _error from None
            function, code, namespace, defaults, kw, pairs, closure, cells = function_row
            if _type(function) is not _function or function.__code__ is not code or function.__globals__ is not namespace or (_type(namespace) is not _dict) or (function.__defaults__ is not defaults) or (function.__kwdefaults__ is not kw) or (_type(pairs) is not _tuple) or (function.__closure__ is not closure) or (_type(cells) is not _tuple):
                raise _error from None
            if checked_namespaces.get(_id(namespace)) is not namespace:
                if _any(_map(_not_identity, _map(_type, namespace), (_str,) * _len(namespace))):
                    raise _error from None
                checked_namespaces[_id(namespace)] = namespace
            if kw is None:
                if _len(pairs) != 0:
                    raise _error from None
            elif _type(kw) is not _dict or _any(_map(_not_identity, _map(_type, kw), (_str,) * _len(kw))) or _len(kw) != _len(pairs) or _any((_type(pair) is not _tuple or _len(pair) != 2 or _type(pair[0]) is not _str or (pair[0] not in kw) or (kw[pair[0]] is not pair[1]) for pair in pairs)):
                raise _error from None
            if closure is None:
                if _len(cells) != 0:
                    raise _error from None
            elif _type(closure) is not _tuple or _len(closure) != _len(cells) or _any((_type(cell) is not _cell or cell.cell_contents is not value for cell, value in _zip(closure, cells, strict=True))):
                raise _error from None
    if not (type(origin) is tuple and len(origin) == 6 and (type(origin[0]) is ModuleType) and (sys.modules.get('hmp_plugin.presentation_native_link') is origin[0]) and (vars(origin[0]) is globals()) and (type(origin[1]) is tuple) and (type(origin[2]) is tuple) and (type(origin[3]) is tuple)):
        raise _error from None
    if not (type(metadata) is ModuleType and sys.modules.get('hmp_plugin.presentation_native_metadata') is metadata):
        raise _error from None
    kernel_names = vars(metadata)
    if not (checked_namespaces.get(_id(kernel_names)) is kernel_names and all((type(row) is tuple and len(row) == 7 and (type(row[0]) is str) for row in origin[3]))):
        raise _error from None
    first = tuple((row for row in origin[3] if row[0] == '_link_function_pin'))
    if not len(first) == 1:
        raise _error from None
    first = first[0]
    if not (type(first[1]) is FunctionType and first[3] is kernel_names and (kernel_names.get('_link_function_pin') is first[1]) and (first[1].__globals__ is kernel_names) and (first[4] is first[5] is None) and (type(first[6]) is tuple) and (len(first[6]) == 0)):
        raise _error from None
    pin_function = first[1]
    if pin_function.__code__ is not first[2] or pin_function.__defaults__ is not None or pin_function.__kwdefaults__ is not None:
        raise metadata.ArtifactObservationError from None
    allocator = _RECORD_ALLOCATOR
    if not (type(allocator) is BuiltinFunctionType and type(_LinkRead.__bases__) is tuple and (len(_LinkRead.__bases__) == 1) and (allocator.__self__ is _LinkRead.__bases__[0]) and (allocator.__name__ == '__new__') and (vars(_LinkRead.__bases__[0]).get('__new__') is allocator)):
        raise _error from None
    expected = (_LinkExecution, _LinkMetadataConsumer, _LinkMetadataCommit, _NativeLinkMetadataResource, _LinkBytesConsumer, _LinkBytesCommit, _NativeLinkBytesResource, metadata._LinkBytesOperation, metadata._LinkBytesResult, metadata._LinkBytesReturn, _LinkRead, _LinkAction, _LinkPathFinish, _NativeReadlinkObservation, _LinkSnapshot, _LinkTargetObservation, _LinkRecheck)
    if not len(origin[1]) == len(expected):
        raise _error from None
    for row, selected in zip(origin[1], expected, strict=True):
        if not (type(row) is tuple and len(row) == 9 and (row[0] is selected)):
            raise _error from None
        kind, fields, members, constructor, code, namespace, defaults, bases, dispatch = row
        names = vars(kind)
        actual = names.get('__init__' if fields is None else '__new__')
        if type(actual) is staticmethod:
            actual = actual.__func__
        if not (type(kind) is type and actual is constructor and (type(constructor) is FunctionType) and (constructor.__code__ is code) and (constructor.__globals__ is namespace) and (constructor.__defaults__ is defaults) and (kind.__bases__ is bases) and all((names.get(n) is member for n, member in dispatch))):
            raise _error from None
        if fields is None:
            if not (kind is _LinkRead and len(names) == len(members) and all((type(pair) is tuple and len(pair) == 2 and (type(pair[0]) is str) and (pair[0] in names) and (names[pair[0]] is pair[1]) for pair in members))):
                raise _error from None
        elif not (type(fields) is tuple and names.get('_fields') is fields and (namespace.get('_tuple_new') is tuple.__new__) and all((names.get(n) is member for n, member in zip(fields, members, strict=True)))):
            raise _error from None
    shared = {'_produce_shared': '_produce_directory_metadata', '_consume_shared': '_consume_directory_policy', '_ack_shared': '_ack_directory_policy', '_attached_shared': '_acked_directory_commit_tail', '_retired_shared': '_retired_directory_commit_tail'}
    effects = ('_open_shared', '_close_known_shared', '_prepare_open_shared')
    required_functions = ('_capture_engine', '_dependency_mirrors', '_engine_origin_tail', '_execution_mirrors', '_opened_chain_tail', '_lifetime_tail', '_resource_tail', '_prepare_shared_consumer', '_latch_shared_consumer', '_make_shared_commit', '_commit_shared_tail', '_publish_shared_ack', '_acked_shared_history', '_resource_bindings', '_byte_record_tail', '_make_shared_bytes_commit', '_commit_shared_bytes_tail', '_publish_shared_bytes_ack', '_acked_shared_bytes_history', *shared, '_effect_pin', '_new_execution', '_append_action', '_finish_mirrors', '_finish_path', '_drive_native_path', '_path_history_mirrors', '_history_phase_mirrors', '_finish_history', '_snapshot_history_mirrors', '_snapshot', '_make_fact', '_recheck', *effects)
    if not (all((type(row) is tuple and len(row) == 7 and (type(row[0]) is str) for row in origin[2])) and len(origin[2]) == len(required_functions) and (len({row[0] for row in origin[2]}) == len(required_functions)) and all((name in required_functions for name, *_ in origin[2]))):
        raise _error from None
    for row in origin[2]:
        if not (type(row) is tuple and len(row) == 7 and (type(row[0]) is str)):
            raise _error from None
        name = row[0]
        if pin_function.__code__ is not first[2] or pin_function.__defaults__ is not None or pin_function.__kwdefaults__ is not None or (kernel_names['_link_function_pin'] is not pin_function):
            raise metadata.ArtifactObservationError from None
        if name in shared:
            if not globals().get(name) is row[1]:
                raise _error from None
            held_pin_row = (shared[name], *row[1:])
            held_pin_namespace = kernel_names
            held_pin_name = shared[name]
            if not (type(held_pin_row) is tuple and len(held_pin_row) == 7 and (type(held_pin_name) is str) and (type(held_pin_row[0]) is str) and (held_pin_row[0] == held_pin_name) and (type(held_pin_namespace) is dict) and (checked_namespaces.get(_id(held_pin_namespace)) is held_pin_namespace) and (type(held_pin_row[1]) is FunctionType) and (held_pin_row[1].__globals__ is held_pin_namespace) and (held_pin_row[3] is held_pin_namespace) and (held_pin_row[1].__code__ is held_pin_row[2]) and (held_pin_row[1].__defaults__ is held_pin_row[4]) and (held_pin_row[1].__kwdefaults__ is held_pin_row[5]) and (held_pin_namespace.get(held_pin_name) is held_pin_row[1]) and (type(held_pin_row[6]) is tuple)):
                raise _error from None
            if held_pin_row[5] is None:
                if not held_pin_row[6] == ():
                    raise _error from None
            elif not (type(held_pin_row[5]) is dict and len(held_pin_row[5]) == len(held_pin_row[6]) and (not _any(_map(_not_identity, _map(_type, held_pin_row[5]), (_str,) * _len(held_pin_row[5])))) and all((type(pair) is tuple and len(pair) == 2 and (type(pair[0]) is str) and (pair[0] in held_pin_row[5]) and (held_pin_row[5][pair[0]] is pair[1]) for pair in held_pin_row[6]))):
                raise _error from None
        elif name in effects:
            if not (globals().get(name) is row[1] and type(row[1]) is FunctionType and (row[1].__code__ is row[2]) and (row[1].__globals__ is row[3]) and (row[1].__defaults__ is row[4]) and (row[1].__kwdefaults__ is row[5]) and (type(row[6]) is tuple)):
                raise _error from None
            namespace = row[3]
            if not (type(namespace) is dict and checked_namespaces.get(_id(namespace)) is namespace and (namespace.get('StartupArtifactOwner') is StartupArtifactOwner)):
                raise _error from None
            if name == '_open_shared':
                if not vars(StartupArtifactOwner).get('_open') is row[1]:
                    raise _error from None
            elif name == '_close_known_shared':
                if not namespace.get('_close_native_file_known') is row[1]:
                    raise _error from None
            elif not namespace.get('_prepare_native_link_open') is row[1]:
                raise _error from None
            if row[5] is not None:
                if not (type(row[5]) is dict and len(row[5]) == len(row[6]) and (not _any(_map(_not_identity, _map(_type, row[5]), (_str,) * _len(row[5])))) and all((type(pair) is tuple and len(pair) == 2 and (type(pair[0]) is str) and (pair[0] in row[5]) and (row[5][pair[0]] is pair[1]) for pair in row[6]))):
                    raise _error from None
            elif not len(row[6]) == 0:
                raise _error from None
        else:
            held_pin_row = row
            held_pin_namespace = globals()
            held_pin_name = name
            if not (type(held_pin_row) is tuple and len(held_pin_row) == 7 and (type(held_pin_name) is str) and (type(held_pin_row[0]) is str) and (held_pin_row[0] == held_pin_name) and (type(held_pin_namespace) is dict) and (checked_namespaces.get(_id(held_pin_namespace)) is held_pin_namespace) and (type(held_pin_row[1]) is FunctionType) and (held_pin_row[1].__globals__ is held_pin_namespace) and (held_pin_row[3] is held_pin_namespace) and (held_pin_row[1].__code__ is held_pin_row[2]) and (held_pin_row[1].__defaults__ is held_pin_row[4]) and (held_pin_row[1].__kwdefaults__ is held_pin_row[5]) and (held_pin_namespace.get(held_pin_name) is held_pin_row[1]) and (type(held_pin_row[6]) is tuple)):
                raise _error from None
            if held_pin_row[5] is None:
                if not held_pin_row[6] == ():
                    raise _error from None
            elif not (type(held_pin_row[5]) is dict and len(held_pin_row[5]) == len(held_pin_row[6]) and (not _any(_map(_not_identity, _map(_type, held_pin_row[5]), (_str,) * _len(held_pin_row[5])))) and all((type(pair) is tuple and len(pair) == 2 and (type(pair[0]) is str) and (pair[0] in held_pin_row[5]) and (held_pin_row[5][pair[0]] is pair[1]) for pair in held_pin_row[6]))):
                raise _error from None
    required_kernel = ('_link_function_pin', '_closed_link_engine_origin', '_link_policy_helper', '_link_stage_functions', '_rejoin_link_stages', '_link_current_lifetime_tail', '_resource_tail', '_prepare_metadata_operation_with_custody', '_undebited_directory_cells_tail', '_unspent_directory_cells_tail', '_unused_directory_cells_tail', '_unused_directory_intent_tail', '_latched_directory_resource_tail', '_charged_directory_history_tail', '_charged_directory_operation_tail', '_active_directory_operation_tail', '_directory_admission_preparation_tail', '_admit_directory_operation', '_returned_directory_operation_tail', '_pending_directory_cohort_tail', '_pending_directory_return_tail', '_produce_directory_metadata', '_consuming_directory_return_tail', '_directory_commit_cohort_tail', '_prepared_directory_commit_tail', '_consume_directory_policy', '_directory_ack_preparation_tail', '_acked_directory_history_tail', '_acked_directory_commit_tail', '_retired_directory_commit_tail', '_ack_directory_policy', '_run_directory_observation', '_capture_payload_origin', '_allocate_directory_custody', '_origin_tail', '_directory_payload_cells', '_marker_tail', '_payload_state_is_clear', '_native_actor_context', '_native_pre_actor_state', '_native_post_actor_state', '_native_work_origin_tail', '_native_work_registration_tail', '_native_metadata_snapshot', '_require', '_operation_result_family', '_capture_link_byte_count', '_retain_link_byte_failure')
    if not all((type(row) is tuple and len(row) == 7 and (type(row[0]) is str) for row in origin[3])):
        raise _error from None
    kernel_roles = tuple((row[0] for row in origin[3]))
    if not (len(set(kernel_roles)) == len(kernel_roles) and all((name in kernel_roles for name in required_kernel))):
        raise _error from None
    for row in origin[3]:
        if not kernel_names.get(row[0]) is row[1]:
            raise _error from None
        if pin_function.__code__ is not first[2] or pin_function.__defaults__ is not None or pin_function.__kwdefaults__ is not None or (kernel_names['_link_function_pin'] is not pin_function):
            raise metadata.ArtifactObservationError from None
        held_pin_row = row
        held_pin_namespace = row[3]
        held_pin_name = row[0]
        if not (type(held_pin_row) is tuple and len(held_pin_row) == 7 and (type(held_pin_name) is str) and (type(held_pin_row[0]) is str) and (held_pin_row[0] == held_pin_name) and (type(held_pin_namespace) is dict) and (checked_namespaces.get(_id(held_pin_namespace)) is held_pin_namespace) and (type(held_pin_row[1]) is FunctionType) and (held_pin_row[1].__globals__ is held_pin_namespace) and (held_pin_row[3] is held_pin_namespace) and (held_pin_row[1].__code__ is held_pin_row[2]) and (held_pin_row[1].__defaults__ is held_pin_row[4]) and (held_pin_row[1].__kwdefaults__ is held_pin_row[5]) and (held_pin_namespace.get(held_pin_name) is held_pin_row[1]) and (type(held_pin_row[6]) is tuple)):
            raise _error from None
        if held_pin_row[5] is None:
            if not held_pin_row[6] == ():
                raise _error from None
        elif not (type(held_pin_row[5]) is dict and len(held_pin_row[5]) == len(held_pin_row[6]) and (not _any(_map(_not_identity, _map(_type, held_pin_row[5]), (_str,) * _len(held_pin_row[5])))) and all((type(pair) is tuple and len(pair) == 2 and (type(pair[0]) is str) and (pair[0] in held_pin_row[5]) and (held_pin_row[5][pair[0]] is pair[1]) for pair in held_pin_row[6]))):
            raise _error from None
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
             and type(execution.origin) is tuple and len(execution.origin) == 6)
    parent = tuple.__getitem__(reg.lineage, 4)
    blueprint = tuple.__getitem__(execution, 2)
    _require(type(parent) is tuple and len(parent) == 5
             and type(parent[4]) is tuple and len(parent[4]) >= 11
             and type(blueprint) is parent[4][6][0]
             and type(parent[0]) is tuple and len(parent[0]) == 7
             and parent[0][4] is execution.origin
             and parent[0][5] is execution.origin[5]
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
    # The original guard performs the complete fresh runtime audit itself.
    # Join the same immutable runtime here; do not audit it twice across an
    # extra helper-return boundary or reuse a verdict from an earlier call.
    _require(reg.scope.runtime is execution.blueprint.runtime
             and reg.scope.runtime is not None)
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
    _require(reg.scope.runtime is execution.blueprint.runtime
             and reg.scope.runtime is not None)
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
             and len(ledger.attempts) == len(budget[3]) + len(actions)
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and ledger.failure[0] is None and ledger.phase.current[0] is ledger.phase.idle
             and ledger.phase.result[0] is None)
    return _path_history_mirrors(execution, outcome, actions, history, closed, count, budget)


def _path_history_mirrors(execution, outcome, actions, history, closed, count, budget):
    """Historical original DATA; neither a live path nor an effect allowance.

    A later healthy path can own the current count/execution/phase. Validate the
    retained closed span and its actual ACKs, not a permanently idle ledger.
    The independently held finish must still come from its actual caller.
    """
    _require(type(execution) is _LinkExecution
             and type(execution.registration) is _NativeScopeRegistration
             and execution.registration.owner is execution.owner
             and type(execution.policy) is policy._LinkPathPolicy
             and type(execution.definitions) is tuple
             and type(actions) is type(history) is type(closed) is tuple
             and type(execution.actions) is type(execution.history) is type(execution.opened) is list
             and type(execution.closed) is list
             and type(execution.cursor) is list and len(execution.cursor) == 1
             and type(execution.cursor[0]) is policy._LinkPathCursor
             and type(execution.cursor[0].position) is int
             and type(execution.failed) is list and len(execution.failed) == 1
             and execution.failed[0] is False
             and type(execution.count) is list and len(execution.count) == 1
             and execution.count[0] is count
             and type(execution.pending) is list and len(execution.pending) == 1
             and execution.pending[0] is None
             and type(count) is tuple and len(count) == 3
             and count[0] is execution.owner and count[1] is execution.registration.scope
             and type(count[2]) is int
             and type(budget) is tuple and len(budget) == 4
             and budget is execution.budget and type(budget[0]) is list
             and len(budget[0]) == 2 and all(type(v) is int for v in budget[0])
             and type(budget[1]) is type(budget[2]) is int and type(budget[3]) is tuple
             and type(outcome) is tuple and len(outcome) == 3
             and len(actions) == len(execution.definitions) == execution.cursor[0].position
             and len(execution.actions) == len(actions)
             and all(a is b for a, b in zip(actions, execution.actions, strict=True))
             and len(execution.history) == len(history)
             and all(a is b for a, b in zip(history, execution.history, strict=True))
             and len(closed) == len(execution.closed) == len(execution.opened)
             and all(a is b for a, b in zip(closed, execution.closed, strict=True)))
    ledger = execution.registration.native_ledger
    _history_phase_mirrors(execution.registration)
    _require(ledger.counts is budget[0] and ledger.counts[0] >= budget[1] + len(actions) + len(closed)
             and type(ledger.attempts) is list
             and ledger.failed[0] is False and ledger.failure[0] is None
             and ledger.phase is execution.registration.native_phase
             and (ledger.phase.current[0] is ledger.phase.idle
                  or ledger.phase.current[0] is ledger.phase.active
                  or ledger.phase.current[0] is ledger.phase.pending))
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
                     and operation.ledger is ledger and operation.attempts is ledger.attempts
                     and type(operation.index) is int
                     and operation.index == len(budget[3]) + ordinal
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
             and len(ledger.attempts) >= len(budget[3]) + len(actual_attempts)
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


def _history_phase_mirrors(registration):
    """Canonical healthy shared-phase DATA, with no latest-work allowance."""
    _require(type(registration) is _NativeScopeRegistration
             and type(registration.type_pins) is tuple and len(registration.type_pins) == 3
             and type(registration.type_pins[1]) is type
             and type(registration.native_ledger) is registration.type_pins[1]
             and type(registration.phase_type) is type
             and type(registration.native_phase) is registration.phase_type)
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(ledger.phase is phase and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and type(phase.current) is list and len(phase.current) == 1
             and type(phase.result) is list and len(phase.result) == 1
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False
             and type(ledger.failure) is list and len(ledger.failure) == 1
             and ledger.failure[0] is None)
    current = phase.current[0]
    if current is phase.idle:
        _require(ledger.inflight[0] is None and phase.result[0] is None)
    elif current is phase.active:
        _require(ledger.inflight[0] is not None and phase.result[0] is ledger.inflight[0])
    else:
        _require(current is phase.pending and ledger.inflight[0] is None
                 and phase.result[0] is not None)
    return phase


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
                # The record pin retains dataclass __init__, not NamedTuple
                # __new__. Keep the actual instance allocation before calling
                # it; passing the class as self would mutate class authority.
                allocator = _RECORD_ALLOCATOR
                record = allocator(kind)
                _engine_origin_tail(origin)
                _require(type(record) is kind and type(vars(record)) is dict
                         and len(vars(record)) == 0 and _RECORD_ALLOCATOR is allocator)
                initialized = constructor(record, hop, phase, position, execution.count[0])
                _engine_origin_tail(origin)
                _require(initialized is None and type(record) is kind and record.hop is hop
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


def _finish_history(owner, registration, finish):
    """Verify a held old finish while later healthy work owns current state."""
    _require(type(owner) is StartupArtifactOwner
             and type(registration) is _NativeScopeRegistration
             and type(finish) is _LinkPathFinish
             and type(finish.execution) is _LinkExecution)
    execution = finish.execution
    _engine_origin_tail(execution.origin)
    _require(execution.owner is owner and execution.registration is registration
             and type(execution.finished) is list and len(execution.finished) == 1
             and execution.finished[0] is True
             and registration.scope.runtime is execution.blueprint.runtime
             and tuple.__getitem__(registration.scope, 17) is execution.blueprint
             and execution.blueprint.owner is owner
             and execution.blueprint.lineage is registration.lineage
             and execution.blueprint.origin is tuple.__getitem__(registration.lineage, 4)
             and execution.blueprint.origin[0][4] is execution.origin
             and any(row is execution.policy for row in execution.blueprint.rows))
    arguments = (execution, finish.outcome, finish.actions, finish.history,
                 finish.closed, finish.count, finish.budget)
    _path_history_mirrors(*arguments)
    check = _effect_pin(execution.origin, '_origin_tail')
    for commit in finish.history:
        payload_origin, _, _, _, _, reference = commit.consumer.custody
        check(payload_origin)
        _require(payload_origin.reference_callback.__get__(reference, payload_origin.reference_type) is None
                 and payload_origin.reference_call(reference) is None)
    _native_work_registration_tail(owner, registration)
    _runtime_current(execution.blueprint.runtime, owner)
    _engine_origin_tail(execution.origin)
    _path_history_mirrors(*arguments)
    _require(type(vars(owner).get('_count_cell')) is tuple
             and vars(owner)['_count_cell'][0] is owner
             and vars(owner)['_count_cell'][1] is registration.scope
             and type(vars(owner)['_count_cell'][2]) is int
             and vars(owner)['_count_cell'][2] >= finish.count[2])
    return finish


def _snapshot_history_mirrors(owner, registration, source, snapshot):
    """Raw-free snapshot joins only; safe inside the existing owner guard.

    Never observes weak references, recurses through owner/runtime current, or
    grants work. The publication caller retains actual finishes independently.
    """
    _require(type(owner) is StartupArtifactOwner
             and type(registration) is _NativeScopeRegistration
             and type(registration.scope) is _Scope and type(source) is _RuntimeSource
             and registration.owner is owner and registration.scope.runtime is source
             and type(snapshot) is _LinkSnapshot and snapshot.source is source
             and type(snapshot.phase) is int and snapshot.phase in (0, 1)
             and type(snapshot.finishes) is tuple
             and len(snapshot.finishes) == len(source.link.hops) + 1
             and type(snapshot.links) is type(snapshot.reads) is tuple
             and len(snapshot.links) == len(snapshot.reads) == len(source.link.hops)
             and type(snapshot.count) is tuple and len(snapshot.count) == 3
             and snapshot.count[0] is owner and snapshot.count[1] is registration.scope
             and type(snapshot.count[2]) is int)
    for index, finish in enumerate(snapshot.finishes):
        _require(type(finish) is _LinkPathFinish and type(finish.execution) is _LinkExecution)
        execution = finish.execution
        _require(execution.owner is owner and execution.registration is registration
                 and execution.blueprint is tuple.__getitem__(registration.scope, 17)
                 and execution.blueprint.runtime is source
                 and any(row is execution.policy for row in execution.blueprint.rows)
                 and type(execution.finished) is list and len(execution.finished) == 1
                 and execution.finished[0] is True
                 and execution.policy.phase == ('before' if snapshot.phase == 0 else 'after')
                 and type(execution.policy.index) is int and execution.policy.index == index)
        _path_history_mirrors(execution, finish.outcome, finish.actions, finish.history,
                              finish.closed, finish.count, finish.budget)
        if index:
            previous = snapshot.finishes[index - 1]
            _require(finish.budget[1] == previous.budget[1] + len(previous.actions) + len(previous.closed)
                     and finish.budget[2] == previous.budget[2]
                     and len(finish.budget[3]) == len(previous.budget[3]) + len(previous.actions))
        if index == len(source.link.hops):
            _require(execution.policy.hop is None and type(snapshot.target) is tuple
                     and len(snapshot.target) == 2
                     and snapshot.target[0] is finish.outcome[0]
                     and snapshot.target[1] is finish.outcome[1]
                     and finish.count is snapshot.count is snapshot.finishes[index - 1].count)
            continue
        hop = source.link.hops[index]
        row, observation = snapshot.links[index], snapshot.reads[index]
        _require(type(row) is tuple and len(row) == 2 and row[0] is hop
                 and type(row[1]) is tuple and len(row[1]) == 2
                 and row[1][0] is finish.outcome[0] and row[1][1] is finish.outcome[1]
                 and execution.policy.hop is hop
                 and type(observation) is _NativeReadlinkObservation
                 and observation.finish is finish and type(observation.record) is _LinkRead
                 and type(observation.acknowledgement) is _LinkBytesCommit)
        commit, record = observation.acknowledgement, observation.record
        position = snapshot.phase * len(source.link.hops) + index
        _require(position < len(source.reads) and source.reads[position] is record
                 and record.hop is hop and type(record.phase) is int
                 and record.phase == snapshot.phase and type(record.index) is int
                 and record.index == position and record.attempted is record.returned is True
                 and record.unknown is False and record.data is None
                 and type(record.length) is int and record.length == len(hop.target)
                 and observation.length is record.length is commit.length
                 and record.acknowledgement is commit and commit.record is record
                 and record.native_result is commit.consumer.operation.result
                 and commit.consumer.execution is execution
                 and any(actual is commit for actual in finish.history)
                 and observation.before is record.before is commit.before_count
                 and observation.after is record.after is commit.after_count is finish.count)
        if index:
            _require(observation.before is snapshot.finishes[index - 1].count)
    return snapshot


def _snapshot(owner, registration, phase, before_state):
    """Retain literal full path returns through raw-free snapshot allocation."""
    _require(type(owner) is StartupArtifactOwner and type(registration) is _NativeScopeRegistration
             and type(phase) is int and phase in (0, 1))
    scope = _native_walk_scope(owner, registration)
    source = scope.runtime
    lookup = _NativeLinkMetadataResource(owner, registration, None, None, None, (), None)
    origin = metadata._closed_link_engine_origin(owner, lookup)
    drive = _effect_pin(origin, '_drive_native_path')
    finish_check = _effect_pin(origin, '_finish_history')
    progress = vars(owner)['_count_cell']
    links, reads, finishes = [], [], []
    failed = False
    result = None
    try:
        for index, hop in enumerate((*source.link.hops, None)):
            path = source.link.target.path if hop is None else hop.path
            finish = drive(owner, registration, path, hop, phase, index, before_state, progress)
            _require(type(finish) is _LinkPathFinish and finish.execution.owner is owner
                     and finish.execution.registration is registration
                     and finish.execution.policy.hop is hop
                     and finish.execution.policy.path is path)
            finish_check(owner, registration, finish)
            finishes.append(finish)
            progress = finish.count
            projected = (finish.outcome[0], finish.outcome[1])
            if hop is None:
                target = projected
                continue
            byte_commits = tuple(row for row in finish.history if type(row) is _LinkBytesCommit)
            _require(len(byte_commits) == 1)
            actual = byte_commits[0]
            values = (actual.record, actual.before_count, actual.after_count,
                      actual.length, actual, finish)
            kind, _, _, constructor, _, _, _, _, _ = origin[1][13]
            observation = constructor(kind, *values)
            _engine_origin_tail(origin)
            finish_check(owner, registration, finish)
            _require(type(observation) is kind
                     and all(tuple.__getitem__(observation, i) is value for i, value in enumerate(values)))
            links.append((hop, projected))
            reads.append(observation)
        # Capture all literal path finishes before the snapshot constructor.
        held_finishes, held_links, held_reads = tuple(finishes), tuple(links), tuple(reads)
        values = (source, phase, held_links, target, held_reads, progress, held_finishes)
        kind, _, _, constructor, _, _, _, _, _ = origin[1][14]
        result = constructor(kind, *values)
        _engine_origin_tail(origin)
        _require(type(result) is kind and tuple.__len__(result) == len(values)
                 and all(tuple.__getitem__(result, i) is value for i, value in enumerate(values)))
        for finish in held_finishes:
            finish_check(owner, registration, finish)
        _require(_native_walk_scope(owner, registration) is scope)
        _runtime_current(source, owner)
        _engine_origin_tail(origin)
        _snapshot_history_mirrors(owner, registration, source, result)
        _require(vars(owner)['_count_cell'] is source.count[0] is progress
                 and source.before[0] is before_state
                 and source.after[0] is None)
        return result
    except BaseException:
        failed = True
    if failed:
        result = None
        vars(owner)['_unknown'] = True
    raise ArtifactObservationError(owner) from None


def _make_fact(owner, registration, source, before, after, receipt, count):
    """Seal original before/after returns and actual target hash through ctor."""
    _require(type(owner) is StartupArtifactOwner and type(registration) is _NativeScopeRegistration
             and type(receipt) is _HashedArtifact
             and type(source) is _RuntimeSource
             and type(before) is _LinkSnapshot and type(after) is _LinkSnapshot
             and type(before.finishes) is tuple and len(before.finishes) > 0
             and type(after.finishes) is tuple and len(after.finishes) > 0
             and before.source is after.source is source
             and before.phase == 0 and after.phase == 1
             and source.before[0] is before and source.after[0] is after
             and vars(owner).get('_count_cell') is count is after.count)
    origin = before.finishes[0].execution.origin
    _engine_origin_tail(origin)
    for snapshot in (before, after):
        _snapshot_history_mirrors(owner, registration, source, snapshot)
        for finish in snapshot.finishes:
            _finish_history(owner, registration, finish)
    _require(before.links == after.links and before.target == after.target
             and receipt.expected is source.link.target and receipt.identity == after.target[0])
    values = (owner, registration.scope, source, before, after, receipt, count)
    kind, _, _, constructor, _, _, _, _, _ = origin[1][15]
    fact = constructor(kind, *values)
    _engine_origin_tail(origin)
    for snapshot in (before, after):
        for finish in snapshot.finishes:
            _finish_history(owner, registration, finish)
    _require(_native_walk_scope(owner, registration) is values[1])
    _runtime_current(source, owner)
    _engine_origin_tail(origin)
    for snapshot in (before, after):
        _snapshot_history_mirrors(owner, registration, source, snapshot)
    _require(type(fact) is kind and tuple.__len__(fact) == len(values)
             and all(tuple.__getitem__(fact, i) is value for i, value in enumerate(values))
             and source.before[0] is before and source.after[0] is after
             and vars(owner).get('_count_cell') is source.count[0] is count)
    return fact


def _recheck(owner, registration, fact):
    """Metadata-only full traversal; never re-read or re-charge link bytes."""
    _require(type(owner) is StartupArtifactOwner and type(registration) is _NativeScopeRegistration
             and type(fact) is _LinkTargetObservation and fact.owner is owner
             and type(fact.source) is _RuntimeSource
             and type(fact.before) is type(fact.after) is _LinkSnapshot
             and type(fact.after.finishes) is tuple and len(fact.after.finishes) > 0
             and fact.scope is registration.scope and vars(owner).get('_ready') is True
             and type(vars(owner).get('_fact_cell')) is tuple
             and vars(owner)['_fact_cell'][4] is fact)
    source, count = fact.source, fact.count
    origin = fact.after.finishes[0].execution.origin
    _engine_origin_tail(origin)
    drive = _effect_pin(origin, '_drive_native_path')
    finishes = []
    failed = False
    result = None
    try:
        for index, hop in enumerate((*source.link.hops, None)):
            path = source.link.target.path if hop is None else hop.path
            finish = drive(owner, registration, path, hop, 1, index, fact.before, count, False)
            _require(type(finish) is _LinkPathFinish and finish.count is count
                     and finish.execution.policy.phase == 'recheck'
                     and finish.execution.policy.hop is hop)
            _finish_history(owner, registration, finish)
            finishes.append(finish)
        held = tuple(finishes)
        values = (owner, registration, fact, held, count)
        kind, _, _, constructor, _, _, _, _, _ = origin[1][16]
        result = constructor(kind, *values)
        _engine_origin_tail(origin)
        for finish in held:
            _finish_history(owner, registration, finish)
        _require(_native_walk_scope(owner, registration) is registration.scope)
        _runtime_current(source, owner)
        _engine_origin_tail(origin)
        for snapshot in (fact.before, fact.after):
            _snapshot_history_mirrors(owner, registration, source, snapshot)
        for index, finish in enumerate(held):
            _require(type(finish) is _LinkPathFinish and finish.count is count
                     and finish.execution.owner is owner
                     and finish.execution.registration is registration
                     and finish.execution.policy.phase == 'recheck'
                     and finish.execution.policy.index == index
                     and finish.execution.policy.hop is (source.link.hops[index]
                         if index < len(source.link.hops) else None)
                     and finish.execution.finished[0] is True)
            _path_history_mirrors(finish.execution, finish.outcome, finish.actions,
                                  finish.history, finish.closed, finish.count, finish.budget)
        _require(type(result) is kind and tuple.__len__(result) == len(values)
                 and all(tuple.__getitem__(result, i) is value for i, value in enumerate(values))
                 and vars(owner)['_count_cell'] is source.count[0] is count
                 and vars(owner)['_fact_cell'][4] is fact)
        vars(owner)['_native_link_recheck'] = result
        return result
    except BaseException:
        failed = True
    if failed:
        result = None
        vars(owner)['_unknown'] = True
    raise ArtifactObservationError(owner) from None
