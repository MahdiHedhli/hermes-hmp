"""Original invocation through native bootstrap; not runtime/key admission.

Only the fixed installed entry may call this before native bootstrap. It must
keep its own invocation intact through PM's possible interpreter re-exec. The
later factory still supplies independent installation/operator/runtime checks.
"""
from __future__ import annotations

import _imp
import builtins
import importlib._bootstrap_external
import importlib.util
import marshal
import os
import sys
import threading
from importlib.machinery import ModuleSpec
from types import (
    BuiltinFunctionType,
    CodeType,
    FunctionType,
    GetSetDescriptorType,
    ModuleType,
    SimpleNamespace,
)
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner

_OWNER = None
_CELL = None
_STARTED = None
_START_ATTEMPTED = False
# Required key during early helper capture; only the final literal return publishes it.
_ENTRY_ORIGIN = None
_VERSION_TYPE = type(sys.version_info)
_FLAGS_TYPE = type(sys.flags)


class GatewayEntryError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_ENTRY_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise GatewayEntryError


def _arguments(value):
    _require(type(value) is list and 1 <= len(value) <= 256
             and all(type(v) is str and len(v) <= 4096 and "\0" not in v for v in value))
    return tuple(value)


class InterpreterStartupData(NamedTuple):
    paths: tuple
    version: tuple
    flags: tuple
    implementation: tuple
    platform: str

    def __repr__(self):
        return "<InterpreterStartupData observed-not-admitted redacted>"


class _CachePolicyOrigin(NamedTuple):
    module: ModuleType
    mode: str
    prefix: str | None
    dont_write: bool

    def __repr__(self):
        return "<OriginalInterpreterCachePolicy DATA redacted>"


def _cache_values(origin):
    _require(type(origin) is _CachePolicyOrigin and type(origin.module) is ModuleType
             and type(origin.mode) is str and origin.mode in ("default", "always", "never")
             and type(origin.dont_write) is bool
             and (origin.prefix is None or type(origin.prefix) is str))
    prefix = origin.prefix
    if prefix is not None:
        _require(0 < len(prefix) <= 4096 and prefix.startswith("/")
                 and all(32 <= ord(c) != 127 and not 0xD800 <= ord(c) <= 0xDFFF for c in prefix)
                 and len(prefix.encode("utf-8")) <= 4096
                 and (prefix == "/" or all(part not in ("", ".", "..")
                                          for part in prefix[1:].split("/"))))
    return origin.mode, prefix, origin.dont_write


def _cache_policy():
    module = sys.modules.get("_imp")
    _require(type(module) is ModuleType and module is _imp)
    origin = _CachePolicyOrigin(module, vars(module).get("check_hash_based_pycs"),
                                sys.pycache_prefix, sys.dont_write_bytecode)
    _cache_values(origin)
    return origin


class _SourceHashOrigin(NamedTuple):
    module: ModuleType
    loader_type: type
    function: FunctionType
    code: CodeType
    builtin: BuiltinFunctionType
    key_owner: ModuleType
    key_name: str
    key: int

    def __repr__(self):
        return "<OriginalInterpreterSourceHash redacted>"


def _source_hash_origin(native):
    module = sys.modules.get("_frozen_importlib_external")
    _require(type(module) is ModuleType and module is importlib._bootstrap_external
             and sys.modules.get("importlib._bootstrap_external") is module)
    loader_type = vars(module).get("SourceLoader")
    _require(type(loader_type) is type)
    function = vars(loader_type).get("get_code")
    _require(type(function) is FunctionType and function.__globals__ is vars(module)
             and type(function.__module__) is str
             and function.__module__ == "_frozen_importlib_external")
    code = function.__code__
    names = code.co_names
    _require(type(code) is CodeType and type(names) is tuple
             and all(type(name) is str for name in names)
             and vars(module).get("_imp") is native and "source_hash" in names)
    if "pyc_magic_number_token" in names:
        _require("_RAW_MAGIC_NUMBER" not in names)
        key_owner, key_name = native, "pyc_magic_number_token"
    else:
        _require("_RAW_MAGIC_NUMBER" in names)
        key_owner, key_name = module, "_RAW_MAGIC_NUMBER"
    key = vars(key_owner).get(key_name)
    builtin = vars(native).get("source_hash")
    _require(type(key) is int and 0 <= key < 2 ** 64
             and type(builtin) is BuiltinFunctionType and builtin.__self__ is native
             and type(builtin.__name__) is str and builtin.__name__ == "source_hash"
             and type(builtin.__module__) is str and builtin.__module__ == "_imp")
    return _SourceHashOrigin(module, loader_type, function, code, builtin,
                             key_owner, key_name, key)


def _same_source_hash(origin, current):
    _require(type(origin) is _SourceHashOrigin and type(current) is _SourceHashOrigin
             and type(origin.key) is int and type(origin.key_name) is str)
    return (current.module is origin.module and current.loader_type is origin.loader_type
            and current.function is origin.function
            and current.code is origin.code and current.builtin is origin.builtin
            and current.key_owner is origin.key_owner and current.key_name == origin.key_name
            and current.key == origin.key)


class _SourceCompileOrigin(NamedTuple):
    module: ModuleType
    loader_type: type
    function: FunctionType
    code: CodeType
    builtins_module: ModuleType
    namespace: dict
    compiler: BuiltinFunctionType

    def __repr__(self):
        return "<OriginalInterpreterSourceCompiler redacted>"


def _source_compile_origin(source_hash):
    _require(type(source_hash) is _SourceHashOrigin and type(sys.modules) is dict
             and type(builtins) is ModuleType and sys.modules.get("builtins") is builtins
             and type(source_hash.module) is ModuleType
             and type(source_hash.loader_type) is type)
    module, loader = source_hash.module, source_hash.loader_type
    _require(sys.modules.get("_frozen_importlib_external") is module
             and sys.modules.get("importlib._bootstrap_external") is module
             and vars(module).get("SourceLoader") is loader)
    function = vars(loader).get("source_to_code")
    _require(type(function) is FunctionType and function.__globals__ is vars(module)
             and type(function.__module__) is str
             and function.__module__ == "_frozen_importlib_external"
             and type(function.__code__) is CodeType
             and type(function.__builtins__) is dict
             and function.__builtins__ is vars(builtins)
             and "compile" not in vars(module))
    names = function.__code__.co_names
    _require(type(names) is tuple and all(type(name) is str for name in names))
    namespace = function.__builtins__
    compiler = namespace.get("compile")
    _require(type(compiler) is BuiltinFunctionType and compiler.__self__ is builtins
             and type(compiler.__name__) is str and compiler.__name__ == "compile"
             and type(compiler.__module__) is str and compiler.__module__ == "builtins"
             and "compile" in names)
    return _SourceCompileOrigin(module, loader, function, function.__code__,
                                builtins, namespace, compiler)


def _same_source_compile(origin, current):
    _require(type(origin) is _SourceCompileOrigin and type(current) is _SourceCompileOrigin)
    return all(a is b for a, b in zip(origin, current, strict=True))


class _CacheDecodeOrigin(NamedTuple):
    module: ModuleType
    function: FunctionType
    code: CodeType
    marshal_module: ModuleType
    loads: BuiltinFunctionType
    code_type: type
    native: ModuleType
    fix_filename: BuiltinFunctionType

    def __repr__(self):
        return "<OriginalInterpreterCacheDecoder redacted>"


def _cache_decode_origin(source_hash):
    _require(type(source_hash) is _SourceHashOrigin and type(sys.modules) is dict
             and type(source_hash.module) is ModuleType
             and type(marshal) is ModuleType and sys.modules.get("marshal") is marshal)
    module = source_hash.module
    _require(sys.modules.get("_frozen_importlib_external") is module
             and sys.modules.get("importlib._bootstrap_external") is module)
    function = vars(module).get("_compile_bytecode")
    _require(type(function) is FunctionType and function.__globals__ is vars(module)
             and type(function.__module__) is str
             and function.__module__ == "_frozen_importlib_external"
             and type(function.__code__) is CodeType)
    names = function.__code__.co_names
    _require(type(names) is tuple and all(type(name) is str for name in names)
             and all(name in names for name in
                     ("marshal", "loads", "_code_type", "_imp", "_fix_co_filename")))
    native = vars(module).get("_imp")
    _require(type(native) is ModuleType and native is _imp
             and sys.modules.get("_imp") is native
             and vars(module).get("marshal") is marshal
             and vars(module).get("_code_type") is CodeType)
    loads, fixer = vars(marshal).get("loads"), vars(native).get("_fix_co_filename")
    for function_value, owner, name, module_name in (
            (loads, marshal, "loads", "marshal"),
            (fixer, native, "_fix_co_filename", "_imp")):
        _require(type(function_value) is BuiltinFunctionType
                 and function_value.__self__ is owner
                 and type(function_value.__name__) is str and function_value.__name__ == name
                 and type(function_value.__module__) is str
                 and function_value.__module__ == module_name)
    return _CacheDecodeOrigin(module, function, function.__code__, marshal, loads,
                              CodeType, native, fixer)


def _same_cache_decode(origin, current):
    _require(type(origin) is _CacheDecodeOrigin and type(current) is _CacheDecodeOrigin)
    return all(a is b for a, b in zip(origin, current, strict=True))


class _NativeIOOrigin(NamedTuple):
    namespace: ModuleType
    native: ModuleType
    operations: tuple
    flags: tuple
    result_type: type
    errors: tuple
    thread_namespace: ModuleType
    thread_native: ModuleType
    actor_calls: tuple

    def __repr__(self):
        return "<OriginalNativeFileMachinery metadata-only>"


def _native_io_origin():
    # Capture canonical C bindings without opening a path or minting an outcome.
    _require(type(os) is ModuleType and type(builtins) is ModuleType
             and type(sys.modules) is dict and sys.modules.get("os") is os
             and sys.modules.get("builtins") is builtins
             and type(vars(os).get("name")) is str and vars(os).get("name") == "posix")
    native = sys.modules.get("posix")
    _require(type(native) is ModuleType)
    operations = []
    for name in ("open", "read", "close", "stat", "fstat", "readlink"):
        value = vars(native).get(name)
        _require(type(value) is BuiltinFunctionType and value.__self__ is native
                 and type(value.__name__) is str and value.__name__ == name
                 and type(value.__module__) is str and value.__module__ == "posix"
                 and vars(os).get(name) is value)
        operations.append(value)
    flags = []
    for index, name in enumerate(("O_RDONLY", "O_NOFOLLOW", "O_CLOEXEC",
                                  "O_NONBLOCK", "O_DIRECTORY")):
        value = vars(native).get(name)
        _require(type(value) is int and (value == 0 if index == 0 else value > 0)
                 and vars(os).get(name) is value)
        flags.append(value)
    result_type = vars(native).get("stat_result")
    _require(type(result_type) is type and vars(os).get("stat_result") is result_type
             and type(result_type.__name__) is str and result_type.__name__ == "stat_result")
    base = vars(native).get("error")
    _require(type(base) is type and vars(os).get("error") is base
             and vars(builtins).get("OSError") is base)
    errors = []
    for name in ("OSError", "FileNotFoundError", "PermissionError"):
        kind = vars(builtins).get(name)
        _require(type(kind) is type and type(kind.__name__) is str and kind.__name__ == name
                 and type(kind.__module__) is str and kind.__module__ == "builtins"
                 and type(kind.__mro__) is tuple and base in kind.__mro__)
        errors.append(kind)
    thread_native = sys.modules.get('_thread')
    _require(type(threading) is ModuleType and sys.modules.get('threading') is threading
             and type(thread_native) is ModuleType)
    actor_calls = []
    for namespace, alias, name in ((native, os, 'getpid'), (native, os, 'geteuid'),
                                    (thread_native, threading, 'get_ident')):
        function = vars(namespace).get(name)
        _require(type(function) is BuiltinFunctionType and function.__self__ is namespace
                 and type(function.__name__) is str and function.__name__ == name
                 and vars(alias).get(name) is function)
        actor_calls.append(function)
    return _NativeIOOrigin(os, native, tuple(operations), tuple(flags), result_type, tuple(errors),
                           threading, thread_native, tuple(actor_calls))


def _same_native_io(origin, current):
    _require(type(origin) is _NativeIOOrigin and type(current) is _NativeIOOrigin
             and type(origin.operations) is tuple and type(current.operations) is tuple
             and type(origin.flags) is tuple and type(current.flags) is tuple
             and type(origin.errors) is tuple and type(current.errors) is tuple)
    return (origin.namespace is current.namespace and origin.native is current.native
            and origin.result_type is current.result_type
            and origin.thread_namespace is current.thread_namespace
            and origin.thread_native is current.thread_native
            and type(origin.actor_calls) is tuple and type(current.actor_calls) is tuple
            and len(origin.actor_calls) == len(current.actor_calls) == 3
            and all(a is b for a, b in zip(origin.actor_calls, current.actor_calls, strict=True))
            and len(origin.operations) == len(current.operations) == 6
            and len(origin.flags) == len(current.flags) == 5
            and len(origin.errors) == len(current.errors) == 3
            and all(a is b for a, b in zip(origin.operations, current.operations, strict=True))
            and all(a is b for a, b in zip(origin.flags, current.flags, strict=True))
            and all(a is b for a, b in zip(origin.errors, current.errors, strict=True)))


class _InterpreterOrigin(NamedTuple):
    implementation: SimpleNamespace
    version: object
    flags: object
    data: InterpreterStartupData
    bytecode_module: ModuleType
    bytecode_magic: bytes
    cache_policy: _CachePolicyOrigin
    source_hash: _SourceHashOrigin
    source_compile: _SourceCompileOrigin
    cache_decode: _CacheDecodeOrigin
    native_io: _NativeIOOrigin

    def __repr__(self):
        return "<OriginalInterpreterOrigin redacted>"


def _interpreter():
    implementation, version, flags = sys.implementation, sys.version_info, sys.flags
    _require(type(implementation) is SimpleNamespace and type(version) is _VERSION_TYPE
             and type(flags) is _FLAGS_TYPE)
    values = vars(implementation)
    name, tag, hexversion = values.get("name"), values.get("cache_tag"), sys.hexversion
    _require(type(name) is str and 0 < len(name) <= 128
             and type(tag) is str and 0 < len(tag) <= 128 and type(hexversion) is int)
    paths = (sys.executable, sys.prefix, sys.exec_prefix, sys.base_prefix,
             sys.base_exec_prefix, getattr(sys, "_stdlib_dir", None))
    _require(all(type(value) is str and 0 < len(value) <= 4096
                 and value.startswith("/") and all(32 <= ord(c) != 127 for c in value)
                 for value in paths))
    v = tuple(version)
    _require(len(v) == 5 and all(type(v[i]) is int for i in (0, 1, 2, 4))
             and type(v[3]) is str and len(v[3]) <= 32)
    f = tuple(flags)
    _require(0 < len(f) <= 64 and all(type(value) in (int, bool) for value in f)
             and type(sys.platform) is str and 0 < len(sys.platform) <= 64)
    data = InterpreterStartupData(paths, v, f, (name, tag, hexversion), sys.platform)
    bytecode = sys.modules.get("importlib.util")
    _require(type(bytecode) is ModuleType and bytecode is importlib.util)
    magic = vars(bytecode).get("MAGIC_NUMBER")
    _require(type(magic) is bytes and len(magic) == 4)
    cache = _cache_policy()
    source_hash = _source_hash_origin(cache.module)
    return _InterpreterOrigin(implementation, version, flags, data, bytecode, magic,
                              cache, source_hash, _source_compile_origin(source_hash),
                              _cache_decode_origin(source_hash), _native_io_origin())


def _interpreter_current(origin):
    _require(type(origin) is _InterpreterOrigin and type(origin.data) is InterpreterStartupData)
    current = _interpreter()
    _require(current.implementation is origin.implementation and current.version is origin.version
             and current.flags is origin.flags and current.data == origin.data
             and current.bytecode_module is origin.bytecode_module
             and current.bytecode_magic is origin.bytecode_magic
             and type(origin.cache_policy) is _CachePolicyOrigin
             and current.cache_policy.module is origin.cache_policy.module
             and _cache_values(current.cache_policy) == _cache_values(origin.cache_policy)
             and _same_source_hash(origin.source_hash, current.source_hash)
             and _same_source_compile(origin.source_compile, current.source_compile)
             and _same_cache_decode(origin.cache_decode, current.cache_decode)
             and _same_native_io(origin.native_io, current.native_io))
    return origin


class _NativeFilePhase(NamedTuple):
    """Original opaque phase markers; metadata representation grants no work."""
    idle: object
    active: object
    pending: object
    failed: object
    current: list
    result: list

    def __repr__(self):
        return "<NativeFilePhase original markers redacted>"


class _NativeFileLedger(NamedTuple):
    """Original storage allocation, not a dispatcher or operation receipt."""
    entry: object
    native: _NativeIOOrigin
    context: tuple
    attempts: list
    counts: list
    inflight: list
    failed: list
    scopes: list
    failure: list
    preparation: list
    phase: _NativeFilePhase

    def __repr__(self):
        return "<OriginalNativeFileLedger storage-only redacted>"


def _native_file_ledger_shape(ledger):
    # Shape only, never an effect grant or a completed operation observation.
    _require(type(ledger) is _NativeFileLedger
             and type(ledger.attempts) is list and len(ledger.attempts) <= 1048576
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and type(ledger.counts[0]) is int and type(ledger.counts[1]) is int
             and 0 <= ledger.counts[0] <= 1048576
             and 0 <= ledger.counts[1] <= 1048576 - ledger.counts[0]
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and type(ledger.phase) is _NativeFilePhase
             and type(ledger.phase.current) is list and len(ledger.phase.current) == 1
             and type(ledger.phase.result) is list and len(ledger.phase.result) == 1
             and any(ledger.phase.current[0] is marker for marker in (
                 ledger.phase.idle, ledger.phase.active, ledger.phase.pending, ledger.phase.failed))
             and (ledger.phase.current[0] is not ledger.phase.idle
                  or (ledger.inflight[0] is None and ledger.phase.result[0] is None))
             and (ledger.phase.current[0] is not ledger.phase.pending
                  or (ledger.inflight[0] is None and ledger.phase.result[0] is not None))
             and (ledger.phase.current[0] is not ledger.phase.active
                  or (ledger.inflight[0] is not None and ledger.phase.result[0] is not None))
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and type(ledger.failed[0]) is bool
             and type(ledger.scopes) is list and len(ledger.scopes) <= 1048576
             and type(ledger.failure) is list and len(ledger.failure) == 1
             and type(ledger.preparation) is list and len(ledger.preparation) == 3)


class _NativeFileLineage(NamedTuple):
    """Original entry allocation only; no operation, receipt or fallback grant."""
    entry: object
    native: _NativeIOOrigin
    context: tuple
    ledger: _NativeFileLedger
    link_policy: object = None
    audit_record: object = None

    def __repr__(self):
        return "<OriginalNativeFileLineage unimplemented-effects redacted>"


class _Invocation(NamedTuple):
    context: tuple
    main: ModuleType
    file: str
    spec: object
    argv: list
    arguments: tuple
    original: list
    original_arguments: tuple
    interpreter: _InterpreterOrigin
    native_files: _NativeFileLineage
    native_file_ledger: _NativeFileLedger

    def __repr__(self):
        return "<GatewayEntryInvocation redacted>"


class _EntryOrigin(NamedTuple):
    name: str
    module: ModuleType
    namespace: dict
    file: str
    spec: object
    origin: str | None
    loader: object
    owner_type: type
    function: FunctionType
    code: CodeType
    link_policy: object = None
    audit_record: object = None

    def __repr__(self):
        return "<GatewayEntryOrigin observed-not-admitted redacted>"


class EntryStartupData(NamedTuple):
    context: tuple
    main_file: str
    arguments: tuple
    original_arguments: tuple
    entry_file: str
    native_root: str
    environment: str
    interpreter: InterpreterStartupData

    def __repr__(self):
        return "<EntryStartupData historical-only redacted>"


class GatewayEntryOwner:
    @classmethod
    def start(cls):
        global _OWNER, _CELL, _STARTED, _START_ATTEMPTED
        _require(cls is GatewayEntryOwner and _OWNER is None and _CELL is None
                 and _STARTED is None and _START_ATTEMPTED is False)
        # Original entry/capture and inspection dependencies precede the first
        # owner constructor. Its return cannot nominate a coherent replacement.
        need, need_code = _require, _require.__code__
        guard, guard_code = _origin_current, _origin_current.__code__
        origin = guard(_ENTRY_ORIGIN)
        link_policy = tuple.__getitem__(origin, 10)
        audit_record = tuple.__getitem__(origin, 11)
        owner_kind = GatewayEntryOwner
        type_of, vars_of, len_of, tuple_of, all_of = type, vars, len, tuple, all
        refused = RuntimeError
        constructor = cls.__new__
        class_rows = tuple_of((kind, tuple_of(vars_of(kind).items()), kind.__bases__)
                              for kind in (owner_kind, GatewayEntryError, _EntryOrigin,
                                           _NativeFileLineage))
        functions = []
        for _, items, _ in class_rows:
            for _, item in items:
                if type_of(item) in (classmethod, staticmethod):
                    item = item.__func__
                if type_of(item) is FunctionType:
                    functions.append((item, item.__code__, item.__defaults__, item.__kwdefaults__))
        constructor_globals = tuple_of((f.__globals__, tuple_of(f.__globals__.items()))
                                       for f in (_EntryOrigin.__new__, _NativeFileLineage.__new__))
        # A lost/raising constructor cannot be retried or re-enter start while
        # its result is unknown. This is one fixed installed-entry attempt.
        _START_ATTEMPTED = True
        namespace = guard.__globals__
        namespace_items = tuple_of(namespace.items())
        owner = constructor(cls)
        if (len_of(namespace) != len_of(namespace_items)
                or not all_of(type_of(k) is str for k in namespace)
                or not all_of(k in namespace and namespace[k] is v for k, v in namespace_items)
                or _require is not need or need.__code__ is not need_code
                or _origin_current is not guard or guard.__code__ is not guard_code
                or _ENTRY_ORIGIN is not origin or _START_ATTEMPTED is not True
                or type_of(owner) is not owner_kind):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for kind, items, bases in class_rows:
            if type_of(kind) is not type_of:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            actual = vars_of(kind)
            if (kind.__bases__ is not bases or len_of(actual) != len_of(items)
                    or not all_of(type_of(k) is str for k in actual)
                    or not all_of(k in actual and actual[k] is v for k, v in items)):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if not all_of(f.__code__ is code and f.__defaults__ is defaults
                      and f.__kwdefaults__ is kw for f, code, defaults, kw in functions):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for actual, items in constructor_globals:
            if (len_of(actual) != len_of(items) or not all_of(type_of(k) is str for k in actual)
                    or not all_of(k in actual and actual[k] is v for k, v in items)):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        need(guard(origin) is origin and tuple.__getitem__(origin, 10) is link_policy
             and tuple.__getitem__(origin, 11) is audit_record
             and _OWNER is None and _CELL is None and _STARTED is None)
        _OWNER = owner  # before bootstrap/import/re-exec effects
        owner._scope = owner._activation = owner._bootstrap = owner._started_cell = None
        owner._ready = owner._failed = False
        failed = False
        started = None
        try:
            need(guard(origin) is origin and _ENTRY_ORIGIN is origin
                 and tuple.__getitem__(origin, 10) is link_policy
                 and tuple.__getitem__(origin, 11) is audit_record)
            _require(type(sys.modules) is dict
                     and not any(name in sys.modules for name in (
                         "hermes_bootstrap", "pm.environments", "gateway.run",
                         "hmp_plugin.server", "hmp_plugin.adapter")))
            main = sys.modules.get("__main__")
            _require(type(main) is ModuleType)
            file = vars(main).get("__file__")
            _require(type(file) is str and file.startswith("/")
                     and len(file) <= 4096 and "\0" not in file)
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context))
            interpreter = _interpreter()
            phase = _NativeFilePhase(object(), object(), object(), object(), [None], [None])
            phase.current[0] = phase.idle
            ledger = _NativeFileLedger(owner, interpreter.native_io, context,
                                       [], [0, 0], [None], [False], [], [None],
                                       [None, None, None], phase)
            native_files = _NativeFileLineage(owner, interpreter.native_io, context, ledger,
                                             link_policy, audit_record)
            s = _Invocation(context, main, file, vars(main).get("__spec__"),
                            sys.argv, _arguments(sys.argv),
                            sys.orig_argv, _arguments(sys.orig_argv), interpreter,
                            native_files, ledger)
            owner._scope = s
            cell = (owner, s)
            _CELL = cell
            _require(GatewayEntryOwner._invocation(owner) is s and _CELL is cell)
            import hermes_bootstrap

            bootstrap = hermes_bootstrap
            owner._bootstrap = bootstrap
            _require(GatewayEntryOwner._invocation(owner) is s and _CELL is cell)
            _require(type(bootstrap) is ModuleType
                     and sys.modules.get("hermes_bootstrap") is bootstrap
                     and "gateway.run" not in sys.modules)
            activation = GatewayActivationOwner.retain()
            owner._activation = activation
            _require(GatewayEntryOwner._invocation(owner) is s and _CELL is cell)
            _require(sys.modules.get("hermes_bootstrap") is bootstrap
                     and GatewayActivationOwner.current(activation) is activation)
            _require(GatewayEntryOwner._invocation(owner) is s and _CELL is cell)
            _require(owner._activation is activation and owner._bootstrap is bootstrap
                     and sys.modules.get("hermes_bootstrap") is bootstrap
                     and owner._ready is False and owner._failed is False)
            _require(_origin_current(origin) is origin
                     and GatewayEntryOwner._invocation(owner) is s and _CELL is cell)
            _require(GatewayActivationOwner.current(activation) is activation
                     and GatewayEntryOwner._invocation_state(owner, s, cell) is s
                     and _origin_current(origin) is origin)
            activation_scope = GatewayActivationOwner._retained_scope(activation)
            _require(owner._activation is activation and owner._bootstrap is bootstrap
                     and sys.modules.get("hermes_bootstrap") is bootstrap
                     and owner._ready is False and owner._failed is False
                     and owner._started_cell is None and _STARTED is None)
            data = EntryStartupData(s.context, s.file, s.arguments, s.original_arguments,
                                    origin.file, activation_scope.root,
                                    activation_scope.environment, s.interpreter.data)
            started = (owner, s, cell, activation, bootstrap, origin, data)
            owner._started_cell = _STARTED = started
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = failed = True
            if started is not None and _STARTED is started:
                _STARTED = None
            if owner._started_cell is started:
                owner._started_cell = None
        if failed:
            raise GatewayEntryError(owner) from None

    def _retained_binding(self):
        """Pure original started DATA; never rediscover current registry/paths."""
        cell, started = _CELL, _STARTED
        _require(type(self) is GatewayEntryOwner and _OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(cell[1]) is _Invocation and self._scope is cell[1]
                 and self._ready is True and self._failed is False
                 and type(started) is tuple and len(started) == 7 and started[0] is self
                 and started[1] is cell[1] and started[2] is cell
                 and self._started_cell is started
                 and type(started[3]) is GatewayActivationOwner
                 and self._activation is started[3] and type(started[4]) is ModuleType
                 and self._bootstrap is started[4] and type(started[5]) is _EntryOrigin
                 and started[5] is _ENTRY_ORIGIN and type(started[6]) is EntryStartupData)
        s = cell[1]
        activation_scope = GatewayActivationOwner._retained_scope(started[3])
        data = started[6]
        _require(type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context)
                 and activation_scope.bootstrap is started[4]
                 and data.context is s.context and data.main_file is s.file
                 and data.arguments is s.arguments
                 and data.original_arguments is s.original_arguments
                 and data.entry_file is started[5].file
                 and data.native_root is activation_scope.root
                 and data.environment is activation_scope.environment
                 and type(s.interpreter) is _InterpreterOrigin
                 and type(s.native_files) is _NativeFileLineage
                 and s.native_files.entry is self
                 and s.native_files.native is s.interpreter.native_io
                 and s.native_files.context is s.context
                 and type(s.native_file_ledger) is _NativeFileLedger
                 and s.native_files.ledger is s.native_file_ledger
                 and tuple.__len__(s.native_files) == 6
                 and tuple.__getitem__(s.native_files, 4)
                     is tuple.__getitem__(started[5], 10)
                 and tuple.__getitem__(s.native_files, 5)
                     is tuple.__getitem__(started[5], 11)
                 and tuple.__getitem__(started[5], 11)
                     is tuple.__getitem__(tuple.__getitem__(started[5], 10), 0)[7]
                 and s.native_file_ledger.entry is self
                 and s.native_file_ledger.native is s.interpreter.native_io
                 and s.native_file_ledger.context is s.context
                 and type(s.interpreter.data) is InterpreterStartupData
                 and data.interpreter is s.interpreter.data)
        _native_file_ledger_shape(s.native_file_ledger)
        return s, cell, started

    def _native_file_lineage(self):
        """Return original allocation DATA, never discover or recreate an owner."""
        binding = GatewayEntryOwner._retained_binding(self)
        return binding[0].native_files

    def retained_data(self):
        """Original immutable observations, not current imports or runtime permission."""
        try:
            before = GatewayEntryOwner._retained_binding(self)
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context) and context == before[0].context)
            after = GatewayEntryOwner._retained_binding(self)
            _require(all(old is new for old, new in zip(before, after, strict=True)))
            return before[2][6]
        except BaseException:
            raise GatewayEntryError(self) from None

    def current_binding(self):
        """Fresh early entry observation; still not installed/operator admission."""
        try:
            before = GatewayEntryOwner._retained_binding(self)
            _require(GatewayEntryOwner._invocation(self) is before[0]
                     and _origin_current(before[2][5]) is before[2][5]
                     and GatewayActivationOwner.current(before[2][3]) is before[2][3])
            after = GatewayEntryOwner._retained_binding(self)
            _require(all(old is new for old, new in zip(before, after, strict=True)))
            _require(GatewayEntryOwner._invocation_state(self, before[0], before[1]) is before[0]
                     and _origin_current(before[2][5]) is before[2][5])
            return before
        except BaseException:
            raise GatewayEntryError(self) from None

    def _invocation_values(self, s, cell):
        """Original invocation DATA, without an early-listener eligibility claim."""
        _require(type(self) is GatewayEntryOwner and _OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(s) is _Invocation and cell[1] is s and self._scope is s
                 and _CELL is cell and self._failed is False
                 and type(sys.modules) is dict and sys.modules.get("__main__") is s.main
                 and vars(s.main).get("__file__") is s.file
                 and vars(s.main).get("__spec__") is s.spec
                 and sys.argv is s.argv and _arguments(sys.argv) == s.arguments
                 and sys.orig_argv is s.original
                 and _arguments(sys.orig_argv) == s.original_arguments)
        original = _origin_current(_ENTRY_ORIGIN)
        _require(type(s.native_files) is _NativeFileLineage
                 and tuple.__len__(s.native_files) == 6
                 and tuple.__getitem__(s.native_files, 0) is self
                 and tuple.__getitem__(s.native_files, 4) is tuple.__getitem__(original, 10)
                 and tuple.__getitem__(s.native_files, 5) is tuple.__getitem__(original, 11))
        _require(_interpreter_current(s.interpreter) is s.interpreter)
        _require(_origin_current(original) is original
                 and tuple.__getitem__(s.native_files, 5) is tuple.__getitem__(original, 11))
        return s

    def _invocation_state(self, s, cell):
        """Early startup only; continuation does not relax this fence."""
        value = GatewayEntryOwner._invocation_values(self, s, cell)
        _require(not any(name in sys.modules for name in (
            "gateway.run", "hmp_plugin.server", "hmp_plugin.adapter")))
        return value

    def _invocation(self):
        cell = _CELL
        _require(type(self) is GatewayEntryOwner and _OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(cell[1]) is _Invocation and self._scope is cell[1]
                 and self._failed is False)
        s = cell[1]
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context)
        return GatewayEntryOwner._invocation_state(self, s, cell)

    def __repr__(self):
        return "<GatewayEntryOwner bootstrap-observed not-runtime-admitted>"


def _origin_current(origin):
    _require(type(sys.modules) is dict and type(origin) is _EntryOrigin
             and origin is _ENTRY_ORIGIN
             and origin.owner_type is GatewayEntryOwner and type(origin.module) is ModuleType
             and type(origin.namespace) is dict and vars(origin.module) is origin.namespace
             and sys.modules.get(origin.name) is origin.module)
    # Pointer preservation only: link helper/type validation is repeated when
    # that fixed policy is actually used, not cached as permission for any work.
    _require(tuple.__len__(origin) == 12
             and type(tuple.__getitem__(origin, 10)) is tuple
             and tuple.__len__(tuple.__getitem__(origin, 10)) == 5)
    policy = tuple.__getitem__(origin, 10)
    environment = tuple.__getitem__(policy, 0)
    record = tuple.__getitem__(origin, 11)
    _require(type(environment) is tuple and tuple.__len__(environment) == 8
             and type(record) is tuple and tuple.__len__(record) == 3
             and tuple.__getitem__(environment, 7) is record
             and tuple.__getitem__(record, 0) is tuple.__getitem__(environment, 4)
             and tuple.__getitem__(record, 1) is tuple.__getitem__(environment, 5))
    values = origin.namespace
    method = vars(GatewayEntryOwner).get("start")
    _require(type(method) is classmethod and type(origin.function) is FunctionType
             and method.__func__ is origin.function and type(origin.code) is CodeType
             and origin.function.__code__ is origin.code
             and origin.function.__globals__ is origin.namespace
             and values.get("__file__") is origin.file and values.get("__spec__") is origin.spec
             and (origin.spec is None or (type(origin.spec) is ModuleSpec
                  and vars(origin.spec).get("origin") is origin.origin
                  and vars(origin.spec).get("loader") is origin.loader)))
    return origin


def _link_policy_current(origin):
    """Validate the actual held early DATA seal; not native/link admission."""
    _require(type(origin) is tuple and len(origin) == 5
             and type(origin[2]) is tuple and len(origin[2]) == 8)
    row = origin[2][4]
    _require(type(row) is tuple and len(row) == 7 and type(row[0]) is str
             and row[0] == 'factory' and type(row[1]) is FunctionType
             and type(row[3]) is dict and all(type(k) is str for k in row[3])
             and row[3].get('factory') is row[1]
             and row[1].__code__ is row[2] and row[1].__globals__ is row[3]
             and row[1].__defaults__ is row[4] and row[1].__kwdefaults__ is row[5]
             and type(row[5]) is dict and all(type(k) is str for k in row[5])
             and type(row[6]) is tuple and len(row[5]) == len(row[6])
             and all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                     and pair[0] in row[5] and row[5][pair[0]] is pair[1]
                     for pair in row[6]))
    actual = row[1](origin)  # actual captured guard, never a current export
    _require(actual is origin[3][3][1])
    return origin


def _capture_origin():
    _require(type(sys.modules) is dict)
    module = sys.modules.get(__name__)
    _require(type(module) is ModuleType and vars(module) is globals())
    values = vars(module)
    file, spec = values.get("__file__"), values.get("__spec__")
    _require(type(file) is str and file.startswith("/") and len(file) <= 4096
             and all(32 <= ord(c) != 127 for c in file)
             and (spec is None or type(spec) is ModuleSpec))
    method = vars(GatewayEntryOwner).get("start")
    _require(type(method) is classmethod and type(method.__func__) is FunctionType)
    function = method.__func__
    _require(function.__globals__ is values and type(function.__code__) is CodeType
             and type(function.__code__.co_filename) is str
             and function.__code__.co_filename == file)
    origin = None if spec is None else vars(spec).get("origin")
    loader = None if spec is None else vars(spec).get("loader")
    _require(origin is None or (type(origin) is str and origin == file))
    # This is the initial module-load boundary, before start/__new__/bootstrap.
    # Initialization imports may execute code. Hold and reseal our own original
    # namespace, classes, helpers and generated constructors across them.
    type_of, vars_of, len_of, tuple_of, all_of = type, vars, len, tuple, all
    zip_of, value_error = zip, ValueError
    module_kind, sys_module = ModuleType, sys
    refused = RuntimeError
    module_items = tuple_of(values.items())
    classes = (GatewayEntryOwner, GatewayEntryError, _EntryOrigin, _NativeFileLineage)
    class_rows = tuple_of((kind, tuple_of(vars_of(kind).items()), kind.__bases__)
                          for kind in classes)
    functions = [item for item in values.values() if type_of(item) is FunctionType]
    for _, items, _ in class_rows:
        for _, item in items:
            if type_of(item) in (classmethod, staticmethod):
                item = item.__func__
            if type_of(item) is FunctionType:
                functions.append(item)
    function_rows = tuple_of((f, f.__code__, f.__defaults__, f.__kwdefaults__,
                              () if f.__kwdefaults__ is None else tuple_of(f.__kwdefaults__.items()),
                              f.__closure__, () if f.__closure__ is None else
                              tuple_of(cell.cell_contents for cell in f.__closure__))
                             for f in functions)
    constructor = vars_of(_EntryOrigin)['__new__']
    if type_of(constructor) is staticmethod:
        constructor = constructor.__func__
    constructor_globals = tuple_of((f.__globals__, tuple_of(f.__globals__.items()))
                                   for f in (constructor, _NativeFileLineage.__new__))
    origin_kind, owner_kind, guard = _EntryOrigin, GatewayEntryOwner, _link_policy_current
    registry, sys_namespace = sys.modules, vars_of(sys)
    spec_dictionary = vars_of(ModuleSpec).get('__dict__')
    if (type_of(spec_dictionary) is not GetSetDescriptorType
            or spec_dictionary.__objclass__ is not ModuleSpec
            or type_of(spec_dictionary.__name__) is not str
            or spec_dictionary.__name__ != '__dict__'):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    def seal():
        if (type_of(module) is not module_kind or type_of(sys_module) is not module_kind
                or vars_of(module) is not values or len_of(values) != len_of(module_items)
                or not all_of(type_of(k) is str for k in values)
                or not all_of(k in values and values[k] is v for k, v in module_items)
                or not all_of(type_of(k) is str for k in sys_namespace)
                or sys_namespace.get('modules') is not registry
                or not all_of(type_of(k) is str for k in registry)
                or registry.get(__name__) is not module):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for kind, items, bases in class_rows:
            if type_of(kind) is not type_of:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            namespace = vars_of(kind)
            if (kind.__bases__ is not bases or len_of(namespace) != len_of(items)
                    or not all_of(type_of(k) is str for k in namespace)
                    or not all_of(k in namespace and namespace[k] is v for k, v in items)):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for f, code, defaults, kw, pairs, closure, cells in function_rows:
            if (f.__code__ is not code or f.__defaults__ is not defaults or f.__kwdefaults__ is not kw
                    or (kw is not None and (not all_of(type_of(k) is str for k in kw)
                        or len_of(kw) != len_of(pairs)
                        or not all_of(k in kw and kw[k] is v for k, v in pairs)))):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            try:
                if (f.__closure__ is not closure or (closure is not None
                        and not all_of(cell.cell_contents is value
                                       for cell, value in zip_of(closure, cells, strict=True)))):
                    raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            except value_error:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for namespace, items in constructor_globals:
            if (len_of(namespace) != len_of(items) or not all_of(type_of(k) is str for k in namespace)
                    or not all_of(k in namespace and namespace[k] is v for k, v in items)):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    # Prepare the approval sibling before helper capture. Approval-first imports
    # reach this point with all definitions complete and only the final alias
    # import pending. Never repair an absent alias in an initialized module.
    getframe = sys_namespace.get('_getframe')
    if (type_of(getframe) is not BuiltinFunctionType
            or getframe.__self__ is not sys_module or getframe.__name__ != '_getframe'):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    from . import gateway_approval
    seal()
    approval_name = 'hmp_startup.gateway_approval'
    if (type_of(gateway_approval) is not module_kind
            or registry.get(approval_name) is not gateway_approval):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    approval_values = vars_of(gateway_approval)
    approval_file = file.rsplit('/', 1)[0] + '/gateway_approval.py'
    if not all_of(type_of(k) is str for k in approval_values):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    approval_label = approval_values.get('__name__')
    if (type_of(approval_label) is not str or approval_label != approval_name
            or type_of(approval_values.get('__file__')) is not str
            or approval_values['__file__'] != approval_file):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name in ('GatewayApprovalOwner', 'GatewayApprovalError', '_RootSource',
                 'GatewayOperatorApproval'):
        kind = approval_values.get(name)
        if type_of(kind) is not type_of:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        label = vars_of(kind).get('__module__')
        if type_of(label) is not str or label != approval_name:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name in ('_require', '_path', '_pairs', '_decode', '_same_entry', '_api_state'):
        helper = approval_values.get(name)
        if (type_of(helper) is not FunctionType or helper.__globals__ is not approval_values
                or helper.__code__.co_filename != approval_file):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if 'GatewayEntryOwner' not in approval_values:
        approval_spec = approval_values.get('__spec__')
        if type_of(approval_spec) is not ModuleSpec:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        approval_spec_values = vars_of(approval_spec)
        if (not all_of(type_of(k) is str for k in approval_spec_values)
                or approval_spec_values.get('_initializing') is not True):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        frame = getframe()
        initializing_frame = False
        for _ in range(128):
            if frame is None:
                break
            if (frame.f_globals is approval_values and frame.f_code.co_name == '<module>'
                    and frame.f_code.co_filename == approval_file):
                initializing_frame = True
                break
            frame = frame.f_back
        del frame
        if initializing_frame is not True:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        approval_values['GatewayEntryOwner'] = owner_kind
    if approval_values['GatewayEntryOwner'] is not owner_kind:
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    # Hold already prepared approval code/dispatch before another module import
    # can run callbacks. Reuse the original entry seal, including closure cells.
    approval_classes = tuple_of(approval_values[name] for name in (
        'GatewayApprovalOwner', 'GatewayApprovalError', '_RootSource', 'GatewayOperatorApproval'))
    approval_class_rows = tuple_of((kind, tuple_of(vars_of(kind).items()), kind.__bases__)
                                   for kind in approval_classes)
    class_rows = (*class_rows, *approval_class_rows)
    approval_functions = [item for item in approval_values.values() if type_of(item) is FunctionType]
    for _, items, _ in approval_class_rows:
        for _, item in items:
            if type_of(item) in (classmethod, staticmethod):
                item = item.__func__
            if type_of(item) is FunctionType:
                approval_functions.append(item)
    function_rows = (*function_rows, *tuple_of((f, f.__code__, f.__defaults__, f.__kwdefaults__,
        () if f.__kwdefaults__ is None else tuple_of(f.__kwdefaults__.items()),
        f.__closure__, () if f.__closure__ is None else
        tuple_of(cell.cell_contents for cell in f.__closure__)) for f in approval_functions))
    approval_items = tuple_of(approval_values.items())
    entry_seal = seal

    def seal():
        entry_seal()
        if (registry.get(approval_name) is not gateway_approval
                or vars_of(gateway_approval) is not approval_values
                or len_of(approval_values) != len_of(approval_items)
                or not all_of(type_of(k) is str for k in approval_values)
                or not all_of(k in approval_values and approval_values[k] is v
                              for k, v in approval_items)):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    from hmp_plugin import presentation_startup_selection as selection_module
    seal()
    selection_name = 'hmp_plugin.presentation_startup_selection'
    if (type_of(selection_module) is not module_kind
            or registry.get(selection_name) is not selection_module):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    selection_values = vars_of(selection_module)
    if not all_of(type_of(k) is str for k in selection_values):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    selection_label = selection_values.get('__name__')
    selection_file = file.rsplit('/', 2)[0] + '/hmp_plugin/presentation_startup_selection.py'
    if (type_of(selection_label) is not str or selection_label != selection_name
            or type_of(selection_values.get('__file__')) is not str
            or selection_values['__file__'] != selection_file):
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    for name in ('_approval_binding', '_require'):
        helper = selection_values.get(name)
        if (type_of(helper) is not FunctionType or helper.__globals__ is not selection_values
                or helper.__code__.co_filename != selection_file):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    approval_kind = approval_values['GatewayApprovalOwner']
    if '_APPROVAL_OWNER_TYPE' not in selection_values:
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    if selection_values['_APPROVAL_OWNER_TYPE'] is None:
        frame = getframe()
        initializing_frame = False
        for _ in range(128):
            if frame is None:
                break
            if (frame.f_globals is values and frame.f_code.co_name == '<module>'
                    and frame.f_code.co_filename == file):
                initializing_frame = True
                break
            frame = frame.f_back
        del frame
        if values.get('_ENTRY_ORIGIN') is not None or initializing_frame is not True:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        selection_values['_APPROVAL_OWNER_TYPE'] = approval_kind
    if selection_values['_APPROVAL_OWNER_TYPE'] is not approval_kind:
        raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
    selection_items = tuple_of(selection_values.items())
    prepared_seal = seal

    def seal():
        prepared_seal()
        if (registry.get(selection_name) is not selection_module
                or vars_of(selection_module) is not selection_values
                or len_of(selection_values) != len_of(selection_items)
                or not all_of(type_of(k) is str for k in selection_values)
                or not all_of(k in selection_values and selection_values[k] is v
                              for k, v in selection_items)):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    # Fixed runtime definitions must be held before later imports can nominate
    # replacements. This transient seal is not the persistent runtime-origin
    # record and does not itself authorize a shorter admission path.
    runtime_rows = []
    entry_values = {}
    runtime_parent_seal = seal

    def seal():
        runtime_parent_seal()
        for runtime_module, runtime_name, namespace, items, spec_values, spec_items in runtime_rows:
            if (type_of(runtime_module) is not module_kind
                    or registry.get(runtime_name) is not runtime_module
                    or vars_of(runtime_module) is not namespace
                    or len_of(namespace) != len_of(items)
                    or not all_of(type_of(k) is str for k in namespace)
                    or not all_of(k in namespace and namespace[k] is v for k, v in items)
                    or len_of(spec_values) != len_of(spec_items)
                    or not all_of(type_of(k) is str for k in spec_values)
                    or not all_of(k in spec_values and spec_values[k] is v
                                  for k, v in spec_items)):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None

    for short_name, class_names, helper_names in (
        ('runtime_files', ('RuntimeFilesError', 'RuntimePackage', 'LinkHop',
                           'ExecutableLinkPlan', 'RuntimeFilePlan'),
         ('_require', '_pairs', '_document', '_path', '_inside', '_typed_equal',
          '_library_name', '_link_plan', 'build_runtime_plan', 'build_runtime_link_plan',
          '_build_runtime_plan', 'plan_current', 'loaded_origins')),
        ('cache_candidates', ('CacheCandidateError', 'PlannedCachePath'),
         ('_require', '_location', 'planned_cache_path')),
        ('entry_files', ('EntryFilesError', '_Inputs', 'EntryFileSnapshotOwner'),
         ('_require', '_same_package', '_pairs', '_decode')),
        ('cache_context', ('CacheContextError', 'CacheInputData', '_ContextSource',
                           'CacheContextOwner'),
         ('_require', '_context', '_getter_current', '_rows')),
    ):
        seal()
        runtime_name = 'hmp_startup.' + short_name
        runtime_module = registry.get(runtime_name)
        # Importlib itself reads an existing module's spec. Fence a partial
        # module directly before allowing any import machinery to inspect it.
        if runtime_module is None:
            if short_name == 'runtime_files':
                from . import runtime_files as runtime_module
            elif short_name == 'cache_candidates':
                from . import cache_candidates as runtime_module
            elif short_name == 'entry_files':
                from . import entry_files as runtime_module
            else:
                from . import cache_context as runtime_module
        seal()
        runtime_file = file.rsplit('/', 1)[0] + '/' + short_name + '.py'
        if (type_of(runtime_module) is not module_kind
                or registry.get(runtime_name) is not runtime_module):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        namespace = vars_of(runtime_module)
        if not all_of(type_of(k) is str for k in namespace):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        label, path = namespace.get('__name__'), namespace.get('__file__')
        runtime_spec = namespace.get('__spec__')
        if (type_of(label) is not str or label != runtime_name
                or type_of(path) is not str or path != runtime_file
                or type_of(runtime_spec) is not ModuleSpec):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        spec_values = spec_dictionary.__get__(runtime_spec, ModuleSpec)
        if type_of(spec_values) is not dict:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if not all_of(type_of(k) is str for k in spec_values):
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        spec_origin = spec_values.get('origin')
        if type_of(spec_origin) is not str or spec_origin != runtime_file:
            raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for name in class_names:
            kind = namespace.get(name)
            if type_of(kind) is not type_of:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            class_namespace = vars_of(kind)
            if not all_of(type_of(k) is str for k in class_namespace):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            label = class_namespace.get('__module__')
            if type_of(label) is not str or label != runtime_name:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        for name in helper_names:
            helper = namespace.get(name)
            if (type_of(helper) is not FunctionType or helper.__globals__ is not namespace
                    or type_of(helper.__code__) is not CodeType
                    or type_of(helper.__code__.co_filename) is not str
                    or helper.__code__.co_filename != runtime_file):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        if short_name == 'entry_files':
            aliases = (('gateway_entry', module), ('GatewayEntryOwner', owner_kind))
        elif short_name == 'cache_context':
            aliases = (('EntryFileSnapshotOwner', entry_values['EntryFileSnapshotOwner']),
                       ('_Inputs', entry_values['_Inputs']),
                       ('_same_package', entry_values['_same_package']),
                       ('GatewayEntryOwner', owner_kind),
                       ('_origin_current', values['_origin_current']))
        else:
            aliases = ()
        for name, expected in aliases:
            if name not in namespace:
                frame = getframe()
                initializing_frame = False
                for _ in range(128):
                    if frame is None:
                        break
                    code = frame.f_code
                    if (frame.f_globals is namespace and type_of(code.co_name) is str
                            and code.co_name == '<module>'
                            and type_of(code.co_filename) is str
                            and code.co_filename == runtime_file):
                        initializing_frame = True
                        break
                    frame = frame.f_back
                del frame
                if (spec_values.get('_initializing') is not True
                        or initializing_frame is not True
                        or values.get('_ENTRY_ORIGIN') is not None):
                    raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
                namespace[name] = expected
            if namespace[name] is not expected:
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
        runtime_class_rows = []
        for name in class_names:
            kind = namespace[name]
            class_namespace = vars_of(kind)
            if not all_of(type_of(k) is str for k in class_namespace):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            items = tuple_of(class_namespace.items())
            if not all_of(type_of(k) is str for k, _ in items):
                raise refused('BI1_LINK_FACTORY_ORIGIN_REFUSED') from None
            runtime_class_rows.append((kind, items, kind.__bases__))
        runtime_class_rows = tuple_of(runtime_class_rows)
        class_rows = (*class_rows, *runtime_class_rows)
        runtime_functions = [namespace[name] for name in helper_names]
        for _, items, _ in runtime_class_rows:
            for _, item in items:
                if type_of(item) in (classmethod, staticmethod):
                    item = item.__func__
                if type_of(item) is FunctionType:
                    runtime_functions.append(item)
        function_rows = (*function_rows, *tuple_of(
            (f, f.__code__, f.__defaults__, f.__kwdefaults__,
             () if f.__kwdefaults__ is None else tuple_of(f.__kwdefaults__.items()),
             f.__closure__, () if f.__closure__ is None else
             tuple_of(cell.cell_contents for cell in f.__closure__)) for f in runtime_functions))
        # Generated NamedTuple constructors have private globals separate from
        # the defining module; retain those too, without freezing collections.
        for _, items, _ in runtime_class_rows:
            for name, item in items:
                if name != '__new__':
                    continue
                if type_of(item) is staticmethod:
                    item = item.__func__
                if type_of(item) is FunctionType and item.__globals__ is not namespace:
                    constructor_globals = (*constructor_globals,
                        (item.__globals__, tuple_of(item.__globals__.items())))
        runtime_rows.append((runtime_module, runtime_name, namespace, tuple_of(namespace.items()),
                             spec_values, tuple_of(spec_values.items())))
        if short_name == 'entry_files':
            entry_values = namespace
        seal()

    from . import link_factory_origin

    seal()  # never call a helper nominated by changes to this entry module
    _require(type_of(link_factory_origin) is module_kind)
    link_namespace = vars_of(link_factory_origin)
    _require(all_of(type_of(k) is str for k in link_namespace))
    capture = link_namespace.get('capture')
    _require(type(capture) is FunctionType and capture.__globals__ is link_namespace)
    link_policy = capture()
    seal()
    _require(type_of(link_policy) is tuple_of and len_of(link_policy) == 5)
    link_environment = tuple_of.__getitem__(link_policy, 0)
    _require(type_of(link_environment) is tuple_of and len_of(link_environment) == 8)
    audit_record = tuple_of.__getitem__(link_environment, 7)
    _require(type_of(audit_record) is tuple_of and len_of(audit_record) == 3)
    _require(guard(link_policy) is link_policy)
    seal()
    fields = (__name__, module, values, file, spec, origin, loader,
              owner_kind, function, function.__code__, link_policy, audit_record)
    actual = constructor(origin_kind, *fields)
    seal()
    _require(type(actual) is origin_kind and tuple.__len__(actual) == len(fields)
             and all(tuple.__getitem__(actual, i) is value for i, value in enumerate(fields)))
    _require(guard(link_policy) is link_policy)
    seal()
    return actual


_ENTRY_ORIGIN = _capture_origin()
