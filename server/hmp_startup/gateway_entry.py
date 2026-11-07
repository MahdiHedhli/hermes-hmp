"""Original invocation through native bootstrap; not runtime/key admission.

Only the fixed installed entry may call this before native bootstrap. It must
keep its own invocation intact through PM's possible interpreter re-exec. The
later factory still supplies independent installation/operator/runtime checks.
"""
from __future__ import annotations

import os
import sys
import threading
from importlib.machinery import ModuleSpec
from types import CodeType, FunctionType, ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner

_OWNER = None
_CELL = None
_STARTED = None


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


class _Invocation(NamedTuple):
    context: tuple
    main: ModuleType
    file: str
    spec: object
    argv: list
    arguments: tuple
    original: list
    original_arguments: tuple

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
                            sys.orig_argv, _arguments(sys.orig_argv))
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
                                    activation_scope.environment)
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
                 and data.environment is activation_scope.environment)
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

    def _invocation_state(self, s, cell):
        """Pure final invocation join after the last native-context callback."""
        _require(type(self) is GatewayEntryOwner and _OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(s) is _Invocation and cell[1] is s and self._scope is s
                 and _CELL is cell and self._failed is False
                 and type(sys.modules) is dict and sys.modules.get("__main__") is s.main
                 and vars(s.main).get("__file__") is s.file
                 and vars(s.main).get("__spec__") is s.spec
                 and sys.argv is s.argv and _arguments(sys.argv) == s.arguments
                 and sys.orig_argv is s.original
                 and _arguments(sys.orig_argv) == s.original_arguments
                 and not any(name in sys.modules for name in (
                     "gateway.run", "hmp_plugin.server", "hmp_plugin.adapter")))
        return s

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
