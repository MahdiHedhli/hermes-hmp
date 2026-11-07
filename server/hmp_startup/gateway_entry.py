"""Original invocation through native bootstrap; not runtime/key admission.

Only the fixed installed entry may call this before native bootstrap. It must
keep its own invocation intact through PM's possible interpreter re-exec. The
later factory still supplies independent installation/operator/runtime checks.
"""
from __future__ import annotations

import os
import sys
import threading
from types import ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner

_OWNER = None
_CELL = None


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


class GatewayEntryOwner:
    @classmethod
    def start(cls):
        global _OWNER, _CELL
        _require(cls is GatewayEntryOwner and _OWNER is None and _CELL is None)
        owner = cls.__new__(cls)
        _OWNER = owner  # before bootstrap/import/re-exec effects
        owner._scope = owner._activation = owner._bootstrap = None
        owner._ready = owner._failed = False
        failed = False
        try:
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
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = failed = True
        if failed:
            raise GatewayEntryError(owner) from None

    def _invocation(self):
        cell = _CELL
        _require(type(self) is GatewayEntryOwner and _OWNER is self
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self
                 and type(cell[1]) is _Invocation and self._scope is cell[1]
                 and self._failed is False)
        s = cell[1]
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context
                 and sys.modules.get("__main__") is s.main
                 and vars(s.main).get("__file__") is s.file
                 and vars(s.main).get("__spec__") is s.spec
                 and sys.argv is s.argv and _arguments(sys.argv) == s.arguments
                 and sys.orig_argv is s.original
                 and _arguments(sys.orig_argv) == s.original_arguments
                 and _OWNER is self and _CELL is cell and self._scope is s
                 and self._failed is False
                 and not any(name in sys.modules for name in (
                     "gateway.run", "hmp_plugin.server", "hmp_plugin.adapter")))
        return s

    def __repr__(self):
        return "<GatewayEntryOwner bootstrap-observed not-runtime-admitted>"
