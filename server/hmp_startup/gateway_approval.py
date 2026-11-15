"""Operator-private approval anchor at the fixed native default-instance root.

No request paths, identity initialization, installation writes or runtime admission.
The private anchor is the operator's trust input; its observed hash is not its own
approval proof. Only the pinned sibling selection may be derived from its bytes.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from importlib.machinery import ModuleSpec
from pathlib import PosixPath
from types import CodeType, FunctionType, GetSetDescriptorType, ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_activation import _LATE_MODULES, GatewayActivationOwner
from hmp_plugin.presentation_startup_artifacts import (
    ExpectedArtifact,
    OperatorApprovalPath,
    StartupArtifactOwner,
    _descriptor_closed_in_scope,
    _OperatorFileReceipt,
    _ReadEffect,
    _Scope,
)

_OWNER = _CELL = _ROOT = _FACT = None

_SUFFIX = "/plugin-data/hmp/presentation/gateway-startup"
_KEYS = frozenset(("schema", "kind", "selection_schema", "selection_size", "selection_sha256",
                   "recipe_schema", "recipe_size"))


class GatewayApprovalError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_OPERATOR_APPROVAL_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise GatewayApprovalError


def _path(value):
    _require(type(value) is str and value.startswith("/")
             and 1 < len(value.encode("utf-8")) <= 4096
             and all(32 <= ord(c) != 127 for c in value)
             and 1 <= len(value[1:].split("/")) <= 58
             and all(part not in ("", ".", "..") for part in value[1:].split("/")))
    return value


class _RootSource(NamedTuple):
    entry: GatewayEntryOwner
    binding: tuple
    module: ModuleType
    namespace: dict
    function: FunctionType
    code: object
    file: str
    spec: object
    origin: object
    loader: object
    root: str
    native_file: str

    def __repr__(self):
        return "<OriginalDefaultInstanceRoot redacted>"


class GatewayOperatorApproval(NamedTuple):
    selection: ExpectedArtifact
    recipe_size: int
    recipe_schema: int

    def __repr__(self):
        return "<GatewayOperatorApproval selection-only not-runtime-admission redacted>"


def _pairs(rows):
    result = {}
    for key, value in rows:
        _require(key not in result)
        result[key] = value
    return result


def _decode(raw, directory):
    _require(type(raw) is bytes and 0 < len(raw) <= 4096)
    document = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(document) is dict and document.keys() == _KEYS
             and all(type(document[key]) is int for key in (
                 "schema", "selection_schema", "selection_size", "recipe_schema", "recipe_size"))
             and document["schema"] == 1
             and type(document["kind"]) is str
             and document["kind"] == "HMP_GATEWAY_OPERATOR_APPROVAL"
             and document["selection_schema"] == 2 and document["recipe_schema"] in (1, 2)
             and 0 < document["selection_size"] <= 65536
             and 0 < document["recipe_size"] <= 65536
             and type(document["selection_sha256"]) is str
             and len(document["selection_sha256"]) == 64
             and all(c in "0123456789abcdef" for c in document["selection_sha256"])
             and json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                            allow_nan=False).encode("ascii") == raw)
    return GatewayOperatorApproval(
        ExpectedArtifact(directory + "/gateway-startup.json", document["selection_size"],
                         document["selection_sha256"]), document["recipe_size"],
        document["recipe_schema"])


def _same_entry(before, after):
    return (type(before) is tuple and type(after) is tuple and len(before) == len(after) == 3
            and all(old is new for old, new in zip(before, after, strict=True)))


def _api_state(source, *, _spec_dict=ModuleSpec.__dict__["__dict__"]):
    # The native descriptor is an inspection primitive, held in the original
    # helper's defaults; mutable source/spec contents remain freshly checked.
    _require(type(source) is _RootSource
             and type(_spec_dict) is GetSetDescriptorType
             and _spec_dict.__objclass__ is ModuleSpec
             and _spec_dict.__name__ == "__dict__")
    registry = sys.modules
    _require(type(registry) is dict and all(type(key) is str for key in registry)
             and type(source.module) is ModuleType
             and type(source.namespace) is dict and vars(source.module) is source.namespace
             and all(type(key) is str for key in source.namespace)
             and type(source.spec) is ModuleSpec)
    spec_namespace = _spec_dict.__get__(source.spec, ModuleSpec)
    _require(type(spec_namespace) is dict
             and all(type(key) is str for key in spec_namespace))
    _require(registry.get("hermes_constants") is source.module
             and source.namespace.get("get_default_hermes_root") is source.function
             and type(source.function) is FunctionType
             and source.function.__globals__ is source.namespace
             and type(source.code) is CodeType
             and source.function.__code__ is source.code
             and type(source.native_file) is str and type(source.file) is str
             and source.file == source.native_file
             and type(source.code.co_filename) is str
             and source.code.co_filename == source.native_file
             and source.namespace.get("__file__") is source.file
             and source.namespace.get("__spec__") is source.spec
             and type(source.origin) is str and source.origin == source.native_file
             and spec_namespace.get("origin") is source.origin
             and spec_namespace.get("loader") is source.loader)


class GatewayApprovalOwner:
    @classmethod
    def load(cls, entry):
        """Fixed operator entry only; no caller expected bytes/root or qualification callback."""
        global _OWNER, _CELL, _ROOT, _FACT
        _require(cls is GatewayApprovalOwner and type(entry) is GatewayEntryOwner
                 and _OWNER is None and _CELL is None and _ROOT is None and _FACT is None)
        binding = GatewayEntryOwner.current_binding(entry)
        activation = binding[2][3]
        _require(type(activation) is GatewayActivationOwner
                 and activation._approval_owner is None and activation._approval_cell is None
                 and activation._approval_fact_cell is None)
        _require(_OWNER is None and _CELL is None and _ROOT is None and _FACT is None)
        owner = cls.__new__(cls)
        _OWNER = owner
        activation._approval_owner = owner  # before API import/call or any file effect
        partial = (activation, owner)
        activation._approval_cell = _CELL = partial
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._fact_cell = owner._data = None
        owner._count_cell = None
        owner._bytes_read = 0
        owner._buffer = buffer = bytearray()
        raw = fact = None
        failed = False
        try:
            # The same documented default-instance API used by HMP identity. Importing
            # this module does not initialize the HMP identity or read its private keys.
            import hermes_constants

            module = hermes_constants
            _require(type(module) is ModuleType and sys.modules.get("hermes_constants") is module)
            namespace = vars(module)
            function, file, spec = (namespace.get("get_default_hermes_root"),
                                    namespace.get("__file__"), namespace.get("__spec__"))
            native_file = activation._scope.root + "/hermes_constants.py"
            _require(type(function) is FunctionType and function.__globals__ is namespace
                     and type(file) is str and file == native_file
                     and type(spec) is ModuleSpec)
            code = function.__code__
            origin, loader = vars(spec).get("origin"), vars(spec).get("loader")
            _require(type(origin) is str and origin == native_file
                     and code.co_filename == native_file)
            root_value = function()
            _require(type(root_value) is PosixPath)
            root = _path(str(root_value))
            source = _RootSource(entry, binding, module, namespace, function, code, file, spec,
                                 origin, loader, root, native_file)
            _api_state(source)
            _require(_same_entry(binding, GatewayEntryOwner.current_binding(entry))
                     and activation._approval_owner is owner
                     and activation._approval_cell is partial
                     and activation._approval_fact_cell is None
                     and _OWNER is owner and _CELL is partial and _ROOT is None and _FACT is None)
            path = OperatorApprovalPath(_path(root + _SUFFIX + "/gateway-approval.json"))
            s = _Scope(activation, activation._scope, (path,), binding[0].context, [],
                       source, None, [])
            owner._scope = owner._origin = s
            owner._cell = _CELL = (owner, s)
            root_cell = (activation, owner, s, (owner, buffer))
            owner._root_cell = activation._approval_cell = _ROOT = root_cell
            owner._count_cell = (owner, s, 0)
            receipt = StartupArtifactOwner._file(owner, path)
            _require(GatewayApprovalOwner._guard(owner) is s
                     and type(receipt) is _OperatorFileReceipt and receipt.owner is owner
                     and receipt.scope is s and receipt.path is path
                     and receipt.count is owner._count_cell
                     and 0 < len(buffer) == owner._bytes_read == receipt.identity[6] <= 4096)
            raw = bytes(buffer)
            data = _decode(raw, root + _SUFFIX)
            _require(GatewayApprovalOwner._guard(owner) is s
                     and owner._root_cell is root_cell and owner._buffer is buffer
                     and receipt.count is owner._count_cell
                     and owner._data is None and owner._fact_cell is None and _FACT is None
                     and activation._approval_fact_cell is None
                     and GatewayApprovalOwner._seal(owner) is s
                     and GatewayApprovalOwner._closed_custody(owner, receipt) is receipt.count)
            fact = (owner, s, data, receipt.count, receipt,
                    ExpectedArtifact(path.path, receipt.count[2], receipt.sha256))
            owner._data = data
            owner._fact_cell = activation._approval_fact_cell = _FACT = fact
            owner._ready = True
        except BaseException:
            owner._failed = failed = True
            if fact is not None and _FACT is fact:
                _FACT = None
            if fact is not None and activation._approval_fact_cell is fact:
                activation._approval_fact_cell = None
            if fact is not None and owner._fact_cell is fact:
                owner._fact_cell = None
        finally:
            buffer[:] = b"\0" * len(buffer)
            buffer.clear()
            raw = None
        if failed:
            raise GatewayApprovalError(owner) from None
        GatewayApprovalOwner._retained_binding(owner)
        return owner

    def __repr__(self):
        return "<GatewayApprovalOwner operator-selected not-runtime-admitted redacted>"

    def _seal(self):
        _require(type(self) is GatewayApprovalOwner and _OWNER is self
                 and type(self._origin) is _Scope
                 and self._scope is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(s.activation) is GatewayActivationOwner
                 and s.activation._approval_owner is self
                 and cell is _CELL and root is _ROOT
                 and type(cell) is tuple and len(cell) == 2 and cell[0] is self and cell[1] is s
                 and type(root) is tuple and len(root) == 4 and root[0] is s.activation
                 and root[1] is self and root[2] is s and s.activation._approval_cell is root
                 and type(root[3]) is tuple and len(root[3]) == 2 and root[3][0] is self
                 and type(root[3][1]) is bytearray and self._buffer is root[3][1]
                 and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
                 and s.activation._retired is False and s.activation._uncertain is False
                 and self._failed is False and self._unknown is False and self._reading is False
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(value) is int for value in s.context)
                 and type(s.records) is list and type(s.reads) is list
                 and type(s.expected) is tuple and len(s.expected) == 1
                 and type(s.expected[0]) is OperatorApprovalPath
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and type(self._count_cell[2]) is int
                 and self._bytes_read is self._count_cell[2])
        _api_state(s.parent)
        _require(type(s.parent.entry) is GatewayEntryOwner
                 and _same_entry(s.parent.binding,
                                 GatewayEntryOwner._retained_binding(s.parent.entry))
                 and s.parent.binding[2][3] is s.activation
                 and s.parent.binding[0].context is s.context)
        return s

    def _guard(self):
        s = GatewayApprovalOwner._seal(self)
        cell, root, count = self._cell, self._root_cell, self._count_cell
        _require(type(sys.modules) is dict and not any(n in sys.modules for n in _LATE_MODULES))
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context)
        _require(_same_entry(s.parent.binding, GatewayEntryOwner.current_binding(s.parent.entry)))
        value = s.parent.function()
        _require(type(value) is PosixPath and str(value) == s.parent.root)
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context)
        _require(GatewayApprovalOwner._seal(self) is s and self._cell is cell
                 and self._root_cell is root and self._count_cell is count
                 and not any(n in sys.modules for n in _LATE_MODULES))
        return s

    def _retained_binding(self):
        """Original operator record, counter and closed-custody DATA; no liveness recapture."""
        s = GatewayApprovalOwner._seal(self)
        root, cell, fact = self._root_cell, self._cell, self._fact_cell
        _require(self._ready is True and len(self._buffer) == 0
                 and fact is _FACT and type(fact) is tuple and len(fact) == 6
                 and fact[0] is self and fact[1] is s
                 and s.activation._approval_fact_cell is fact
                 and type(fact[2]) is GatewayOperatorApproval and self._data is fact[2]
                 and type(fact[4]) is _OperatorFileReceipt and fact[4].owner is self
                 and fact[4].scope is s and fact[4].path is s.expected[0]
                 and fact[4].count is fact[3] is self._count_cell
                 and 0 < fact[3][2] == fact[4].identity[6] <= 4096
                 and type(fact[5]) is ExpectedArtifact
                 and fact[5].path is s.expected[0].path
                 and fact[5].size == fact[3][2] and fact[5].sha256 is fact[4].sha256
                 and GatewayApprovalOwner._closed_custody(self, fact[4]) is fact[3])
        return s, cell, root, fact

    def _closed_custody(self, receipt):
        s = GatewayApprovalOwner._seal(self)
        _require(type(receipt) is _OperatorFileReceipt and receipt.owner is self
                 and receipt.scope is s and type(receipt.descriptors) is tuple
                 and len(receipt.descriptors) == len(s.records) > 0
                 and all(actual is held and _descriptor_closed_in_scope(held, s)
                         for actual, held in zip(
                             s.records, receipt.descriptors, strict=True))
                 and type(receipt.reads) is tuple and len(receipt.reads) == len(s.reads) >= 2
                 and all(actual is held for actual, held in zip(
                     s.reads, receipt.reads, strict=True)))
        previous, previous_cell = 0, None
        for effect in receipt.reads:
            _require(type(effect) is _ReadEffect and effect.returned is True
                     and effect.unknown is False and type(effect.before) is tuple
                     and len(effect.before) == 3 and effect.before[0] is self
                     and effect.before[1] is s and type(effect.before[2]) is int
                     and effect.before[2] == previous
                     and (previous_cell is None or effect.before is previous_cell)
                     and type(effect.after) is tuple and len(effect.after) == 3
                     and effect.after[0] is self and effect.after[1] is s
                     and type(effect.after[2]) is int and effect.after[2] >= previous)
            previous, previous_cell = effect.after[2], effect.after
        _require(previous_cell is receipt.count is self._count_cell
                 and previous == receipt.identity[6] == self._bytes_read)
        return receipt.count

    def current_binding(self):
        _require(_OWNER is self and type(_CELL) is tuple and len(_CELL) == 2
                 and _CELL[0] is self and type(_CELL[1]) is _Scope)
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(value) is int for value in context) and context == _CELL[1].context)
        try:
            before = GatewayApprovalOwner._retained_binding(self)
            GatewayApprovalOwner._guard(self)
            after = GatewayApprovalOwner._retained_binding(self)
            _require(all(a is b for a, b in zip(before, after, strict=True)))
            return before
        except BaseException:
            self._failed = True  # no restored root/API can resurrect this allocation
            raise GatewayApprovalError(self) from None

    def _append(self, data):
        s = GatewayApprovalOwner._guard(self)
        buffer, root = self._buffer, self._root_cell
        _require(type(data) is bytes and len(buffer) + len(data) <= 4096)
        bytearray.extend(buffer, data)
        _require(GatewayApprovalOwner._guard(self) is s
                 and self._root_cell is root and self._buffer is buffer)


# Complete definitions before the cycle enters gateway_entry._capture_origin.
# The entry binds this same class during approval-first initialization.
from .gateway_entry import GatewayEntryOwner
