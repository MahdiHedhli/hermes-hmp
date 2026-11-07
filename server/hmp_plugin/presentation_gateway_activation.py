"""One early native PM activation observation, not installed-runtime admission.

The fixed trusted entry calls retain after native bootstrap and before listener
imports. No selection/activation API is called here. The paired startup factory
must independently verify admitted inventories and compose native/key owners.
"""
from __future__ import annotations

import os
import sys
import threading
from importlib.machinery import ModuleSpec
from types import FunctionType, ModuleType
from typing import NamedTuple

_ENTRY_OWNER = None
_ENTRY_CELL = None
_MAX_MODULES = 20000
_MAX_PATHS = 256
_LATE_MODULES = ("gateway.run", "hmp_plugin.adapter", "hmp_plugin.server")


class ActivationCaptureError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_ACTIVATION_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise ActivationCaptureError


def _path(value):
    _require(type(value) is str and 1 < len(value) <= 4096 and value.startswith("/")
             and all(32 <= ord(c) != 127 for c in value))
    _require(all(part not in ("", ".", "..") for part in value[1:].split("/")))
    return value


class _ModuleOrigin(NamedTuple):
    name: str
    module: ModuleType
    file: str | None
    spec: object
    origin: str | None

    def __repr__(self):
        return "<ActivationModuleOrigin redacted>"


def _origins(modules):
    _require(type(modules) is dict and len(modules) <= _MAX_MODULES)
    rows = []
    for name, module in tuple(modules.items()):
        _require(type(name) is str and 0 < len(name) <= 1024)
        if module is None:
            continue  # an absent import supplies no admitted origin
        _require(type(module) is ModuleType)
        values = vars(module)
        file, spec = values.get("__file__"), values.get("__spec__")
        _require(file is None or (type(file) is str and len(file) <= 4096))
        _require(spec is None or type(spec) is ModuleSpec)
        origin = None if spec is None else vars(spec).get("origin")
        _require(origin is None or (type(origin) is str and len(origin) <= 4096))
        rows.append(_ModuleOrigin(name, module, file, spec, origin))
    return tuple(rows)


class _ActivationScope(NamedTuple):
    context: tuple
    modules: dict
    paths: list
    path_values: tuple
    bootstrap: ModuleType
    pm: ModuleType
    activate: FunctionType
    code: object
    root: str
    environment: str
    origins: tuple

    def __repr__(self):
        return "<GatewayActivationScope observed-imports redacted>"


class GatewayActivationOwner:
    """Retained original bootstrap/import evidence; no keys, IO or authority token."""

    @classmethod
    def retain(cls):
        global _ENTRY_OWNER, _ENTRY_CELL
        _require(cls is GatewayActivationOwner and _ENTRY_OWNER is None and _ENTRY_CELL is None)
        owner = cls.__new__(cls)
        _ENTRY_OWNER = owner  # retain partial acquisition before observation
        owner._ready = owner._uncertain = owner._retired = False
        owner._capturing = True
        owner._scope = None
        owner._artifact_owner = owner._artifact_cell = None
        owner._selection_owner = owner._selection_cell = owner._selection_fact_cell = None
        owner._package_owner = owner._package_cell = None
        failed = False
        try:
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context))
            modules, paths = sys.modules, sys.path
            _require(type(modules) is dict and type(paths) is list
                     and 2 <= len(paths) <= _MAX_PATHS
                     and all(type(p) is str and len(p) <= 4096 for p in paths))
            _require(not any(name in modules for name in _LATE_MODULES))
            bootstrap, pm = modules.get("hermes_bootstrap"), modules.get("pm.environments")
            _require(type(bootstrap) is ModuleType and type(pm) is ModuleType)
            native_file = _path(vars(bootstrap).get("__file__"))
            _require(native_file.endswith("/hermes_bootstrap.py"))
            root = native_file[:-len("/hermes_bootstrap.py")]
            _require(_path(paths[0]) == root)
            environment = _path(paths[1])
            _require(environment.endswith("/site-packages") and environment != root)
            pm_file = _path(vars(pm).get("__file__"))
            _require(pm_file == root + "/pm/environments.py")
            activate = vars(pm).get("activate_dependencies")
            _require(type(activate) is FunctionType
                     and activate.__globals__ is vars(pm)
                     and activate.__code__.co_filename == root + "/pm/environments.py")
            s = _ActivationScope(context, modules, paths, tuple(paths), bootstrap, pm,
                                 activate, activate.__code__, root, environment, _origins(modules))
            owner._scope = s
            _ENTRY_CELL = (owner, s)  # original independent entry allocation
            owner._ready = True
            GatewayActivationOwner.current(owner)
            owner._capturing = False
            return owner
        except BaseException:
            owner._uncertain = failed = True
        if failed:
            raise ActivationCaptureError(owner) from None

    def __repr__(self):
        return "<GatewayActivationOwner observed-not-admitted redacted>"

    def current(self):
        failed = False
        try:
            cell = _ENTRY_CELL
            _require(type(self) is GatewayActivationOwner and _ENTRY_OWNER is self
                     and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                     and type(cell[1]) is _ActivationScope and self._scope is cell[1]
                     and self._ready is True and self._uncertain is False
                     and self._retired is False and type(self._capturing) is bool)
            capturing = self._capturing
            s = cell[1]
            _require(type(s.context) is tuple and len(s.context) == 3
                     and all(type(v) is int for v in s.context))
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context) and context == s.context)
            _require(sys.modules is s.modules and type(s.modules) is dict
                     and sys.path is s.paths and type(s.paths) is list
                     and type(s.path_values) is tuple
                     and len(s.paths) == len(s.path_values)
                     and all(type(p) is str for p in s.paths)
                     and tuple(s.paths) == s.path_values
                     and s.modules.get("hermes_bootstrap") is s.bootstrap
                     and s.modules.get("pm.environments") is s.pm
                     and type(s.pm) is ModuleType
                     and vars(s.pm).get("activate_dependencies") is s.activate
                     and type(s.activate) is FunctionType
                     and s.activate.__globals__ is vars(s.pm)
                     and s.activate.__code__ is s.code
                     and type(s.origins) is tuple)
            # New imports require the factory's separate inventory validation. This
            # fence only proves old observed origins have not silently changed.
            for row in s.origins:
                _require(type(row) is _ModuleOrigin and type(row.module) is ModuleType
                         and s.modules.get(row.name) is row.module)
                values = vars(row.module)
                _require(values.get("__file__") is row.file
                         and values.get("__spec__") is row.spec
                         and (row.spec is None or (type(row.spec) is ModuleSpec
                              and vars(row.spec).get("origin") is row.origin)))
            _require(_ENTRY_OWNER is self and _ENTRY_CELL is cell and self._scope is s
                     and self._ready is True and self._uncertain is False
                     and self._retired is False and self._capturing is capturing
                     and (capturing is False
                          or not any(name in s.modules for name in _LATE_MODULES)))
            return self
        except BaseException:
            failed = self._uncertain = True
        if failed:
            raise ActivationCaptureError(self) from None

    def _retained_scope(self):
        """Pure original allocation join for local cleanup, never current authority."""
        cell = _ENTRY_CELL
        _require(type(self) is GatewayActivationOwner and _ENTRY_OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(cell[1]) is _ActivationScope and self._scope is cell[1])
        return cell[1]

    def retire(self):
        _require(type(self) is GatewayActivationOwner and _ENTRY_OWNER is self)
        self._retired = True  # no cleanup resource is released by retirement
