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
from types import BuiltinFunctionType, CodeType, FunctionType, ModuleType, SimpleNamespace
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner

_OWNER = None
_CELL = None
_STARTED = None
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
                              _cache_decode_origin(source_hash))


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
             and _same_cache_decode(origin.cache_decode, current.cache_decode))
    return origin


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
        global _OWNER, _CELL, _STARTED
        _require(cls is GatewayEntryOwner and _OWNER is None and _CELL is None and _STARTED is None)
        owner = cls.__new__(cls)
        _OWNER = owner  # before bootstrap/import/re-exec effects
        owner._scope = owner._activation = owner._bootstrap = owner._started_cell = None
        owner._ready = owner._failed = False
        failed = False
        started = None
        try:
            origin = _origin_current(_ENTRY_ORIGIN)
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
            s = _Invocation(context, main, file, vars(main).get("__spec__"),
                            sys.argv, _arguments(sys.argv),
                            sys.orig_argv, _arguments(sys.orig_argv), _interpreter())
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
                 and type(s.interpreter.data) is InterpreterStartupData
                 and data.interpreter is s.interpreter.data)
        return s, cell, started

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
        _require(_interpreter_current(s.interpreter) is s.interpreter)
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
    return _EntryOrigin(__name__, module, values, file, spec, origin, loader,
                        GatewayEntryOwner, function, function.__code__)


_ENTRY_ORIGIN = _capture_origin()
