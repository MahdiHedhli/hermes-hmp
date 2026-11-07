"""Fixed private gateway-startup.json loader under an external startup expectation.

The trusted entry/operator supplies independent expected size/SHA before listener
creation. Loading a matching file does not approve a caller-built expectation,
qualify the entry/inventory/loader, create keys or grant runtime authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import threading
from typing import NamedTuple

from .presentation_gateway_activation import _LATE_MODULES, GatewayActivationOwner
from .presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _expected,
    _Scope,
)

_LIMIT = 65536
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_IID = re.compile(r"[a-z2-7]{52}\Z", re.ASCII)
_KEYS = frozenset(("schema", "kind", "iid", "protocol", "algorithm", "credential_generation",
                   "gateway_public", "broker_public", "gateway_inventory_sha256",
                   "broker_inventory_sha256", "loader_policy"))


class SelectionLoadError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_STARTUP_SELECTION_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise SelectionLoadError


class GatewayStartupSelection(NamedTuple):
    iid: str
    generation: str
    gateway_public: bytes
    broker_public: bytes
    gateway_inventory_sha256: str
    broker_inventory_sha256: str
    loader_policy: str
    directory: str
    schema: int

    def __repr__(self):
        return "<GatewayStartupSelection loaded-not-admitted redacted>"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _decode(raw, directory, schema):
    _require(type(schema) is int and schema in (1, 2))
    _require(type(raw) is bytes and 0 < len(raw) <= _LIMIT)
    document = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(document) is dict and document.keys() == _KEYS)
    _require(all(type(value) is (int if key in ("schema", "protocol") else str)
                 for key, value in document.items()))
    _require(document["schema"] == schema and document["kind"] == "HMP_GATEWAY_STARTUP_SELECTION"
             and document["protocol"] == 2 and document["algorithm"] == "Ed25519"
             and _IID.fullmatch(document["iid"]) is not None)
    iid_raw = base64.b32decode(document["iid"].upper() + "====")
    _require(len(iid_raw) == 32
             and base64.b32encode(iid_raw).decode("ascii").rstrip("=").lower() == document["iid"])
    for key in ("credential_generation", "gateway_public", "broker_public",
                "gateway_inventory_sha256", "broker_inventory_sha256"):
        _require(_HEX.fullmatch(document[key]) is not None)
    _require(document["gateway_public"] != document["broker_public"])
    policy = {"darwin": "darwin-system-loader-trust", "linux": "linux-system-loader-trust"}
    _require(type(sys.platform) is str and sys.platform in policy
             and document["loader_policy"] == policy[sys.platform])
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                           allow_nan=False).encode("ascii")
    _require(canonical == raw)
    return GatewayStartupSelection(
        document["iid"], document["credential_generation"],
        bytes.fromhex(document["gateway_public"]), bytes.fromhex(document["broker_public"]),
        document["gateway_inventory_sha256"], document["broker_inventory_sha256"],
        document["loader_policy"], directory, schema)


class StartupSelectionOwner:
    @classmethod
    def load(cls, activation, expected):
        """Schema1 package-only selection; never interpret as a full recipe pin."""
        _require(cls is StartupSelectionOwner)
        return StartupSelectionOwner._load(activation, expected, 1)

    @classmethod
    def load_recipe_selection(cls, activation, expected):
        """Schema2 complete-recipe selection DATA; no fallback or runtime admission."""
        _require(cls is StartupSelectionOwner)
        return StartupSelectionOwner._load(activation, expected, 2)

    @classmethod
    def _load(cls, activation, expected, schema):
        _require(type(schema) is int and schema in (1, 2))
        _require(cls is StartupSelectionOwner and type(activation) is GatewayActivationOwner)
        _require(activation._selection_owner is None and activation._selection_cell is None
                 and activation._selection_fact_cell is None)
        GatewayActivationOwner.current(activation)
        owner = cls.__new__(cls)
        activation._selection_owner = owner  # before parsing or descriptor effects
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._bytes_read = 0
        owner._selection = owner._selection_cell = None
        buffer = bytearray()
        buffer_cell = (owner, buffer)
        owner._buffer = buffer
        owner._scope = owner._origin = _Scope(
            activation, activation._scope, (expected,),
            (os.getpid(), os.geteuid(), threading.get_ident()), [])
        s = owner._origin
        owner._cell = (owner, s)
        owner._root_cell = (activation, owner, s, buffer_cell)
        activation._selection_cell = owner._root_cell
        root_cell = owner._root_cell
        owner._count_cell = (owner, s, 0)
        raw = selection = fact_cell = None
        failed = False
        try:
            _expected((expected,))
            _require(type(expected) is ExpectedArtifact and 0 < expected.size <= _LIMIT
                     and expected.path.endswith("/gateway-startup.json"))
            StartupSelectionOwner._guard(owner)
            StartupArtifactOwner._file(owner, expected)
            _require(StartupSelectionOwner._guard(owner) is s
                     and owner._root_cell is root_cell and activation._selection_cell is root_cell
                     and owner._buffer is buffer and root_cell[3] is buffer_cell
                     and len(buffer) == expected.size)
            raw = bytes(buffer)
            count = owner._count_cell
            _require(type(count) is tuple and len(count) == 3 and count[0] is owner
                     and count[1] is s and type(count[2]) is int
                     and owner._bytes_read is count[2] and count[2] == expected.size)
            digest = hashlib.sha256(raw).hexdigest()
            _require(type(digest) is str and digest == expected.sha256
                     and StartupSelectionOwner._guard(owner) is s
                     and owner._root_cell is root_cell and activation._selection_cell is root_cell)
            selection = _decode(raw, expected.path.rsplit("/", 1)[0], schema)
            _require(type(selection) is GatewayStartupSelection
                     and type(selection.schema) is int and selection.schema == schema
                     and StartupSelectionOwner._guard(owner) is s
                     and owner._root_cell is root_cell and activation._selection_cell is root_cell)
            _require(owner._selection is None and owner._selection_cell is None
                     and activation._selection_fact_cell is None)
            _require(owner._count_cell is count and owner._bytes_read is count[2])
            fact_cell = (owner, s, selection, count)
            owner._selection = selection
            owner._selection_cell = fact_cell
            activation._selection_fact_cell = fact_cell
            _require(StartupSelectionOwner._guard(owner) is s
                     and owner._selection is selection and owner._selection_cell is fact_cell
                     and activation._selection_fact_cell is fact_cell
                     and owner._root_cell is root_cell and activation._selection_cell is root_cell
                     and owner._count_cell is count and owner._bytes_read is count[2])
            owner._ready = True
        except BaseException:
            failed = owner._failed = True
            owner._selection = owner._selection_cell = None
            if fact_cell is not None and activation._selection_fact_cell is fact_cell:
                activation._selection_fact_cell = None
        finally:
            buffer[:] = b"\0" * len(buffer)
            buffer.clear()
            raw = selection = None
        if failed:
            raise SelectionLoadError(owner) from None
        return owner

    def __repr__(self):
        return "<StartupSelectionOwner private-file loaded-not-admitted redacted>"

    def _guard(self):
        _require(type(self) is StartupSelectionOwner and type(self._origin) is _Scope
                 and self._scope is self._origin and type(self._cell) is tuple
                 and len(self._cell) == 2 and self._cell[0] is self
                 and self._cell[1] is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(s.activation) is GatewayActivationOwner
                 and s.activation._selection_owner is self
                 and type(root) is tuple and len(root) == 4
                 and s.activation._selection_cell is root
                 and root[0] is s.activation and root[1] is self and root[2] is s
                 and type(root[3]) is tuple and len(root[3]) == 2 and root[3][0] is self
                 and type(root[3][1]) is bytearray and self._buffer is root[3][1]
                 and s.activation._scope is s.activation_scope
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context) and type(s.records) is list
                 and self._failed is False and self._unknown is False and self._reading is False
                 and type(sys.modules) is dict
                 and not any(name in sys.modules for name in _LATE_MODULES))
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context)
        GatewayActivationOwner.current(s.activation)
        _require(self._scope is s and self._origin is s and self._cell is cell
                 and self._root_cell is root and s.activation._selection_cell is root
                 and s.activation._scope is s.activation_scope
                 and s.activation._selection_owner is self and self._buffer is root[3][1]
                 and self._failed is False and self._unknown is False
                 and not any(name in sys.modules for name in _LATE_MODULES))
        if self._ready is True:
            _require(StartupSelectionOwner._retained_binding(self)[0] is s)
        return s

    def _retained_binding(self):
        """Pure original loaded DATA/closed-custody join, never live runtime approval."""
        _require(type(self) is StartupSelectionOwner and type(self._origin) is _Scope
                 and self._scope is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self and cell[1] is s
                 and type(root) is tuple and len(root) == 4
                 and root[0] is s.activation and root[1] is self and root[2] is s
                 and type(s.activation) is GatewayActivationOwner
                 and s.activation._selection_owner is self and s.activation._selection_cell is root
                 and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
                 and s.activation._retired is False and s.activation._uncertain is False
                 and self._ready is True and self._failed is False
                 and self._unknown is False and self._reading is False
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(value) is int for value in s.context)
                 and type(root[3]) is tuple and len(root[3]) == 2 and root[3][0] is self
                 and type(root[3][1]) is bytearray and self._buffer is root[3][1]
                 and len(root[3][1]) == 0 and type(s.records) is list
                 and all(type(row) is _Descriptor and row.closed is True
                         and row.unknown is False and row.close_attempted is True
                         for row in s.records))
        fact = s.activation._selection_fact_cell
        _require(type(fact) is tuple and len(fact) == 4 and fact[0] is self and fact[1] is s
                 and type(fact[2]) is GatewayStartupSelection
                 and self._selection is fact[2] and self._selection_cell is fact
                 and type(fact[3]) is tuple and len(fact[3]) == 3
                 and fact[3][0] is self and fact[3][1] is s
                 and type(fact[3][2]) is int and self._count_cell is fact[3]
                 and self._bytes_read is fact[3][2]
                 and type(s.expected) is tuple and len(s.expected) == 1
                 and type(s.expected[0]) is ExpectedArtifact
                 and fact[3][2] == s.expected[0].size)
        return s, cell, root, fact

    def retained_data(self):
        """Original immutable loaded selection, not current files/imports/admission."""
        failed = False
        try:
            s, cell, root, fact = StartupSelectionOwner._retained_binding(self)
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(value) is int for value in context) and context == s.context)
            after = StartupSelectionOwner._retained_binding(self)
            _require(after[0] is s and after[1] is cell and after[2] is root and after[3] is fact)
            return fact[2]
        except BaseException:
            failed = True
        if failed:
            raise SelectionLoadError(self) from None

    def _append(self, data):
        s = StartupSelectionOwner._guard(self)
        root, buffer = self._root_cell, self._buffer
        _require(type(data) is bytes and len(buffer) + len(data) <= _LIMIT)
        bytearray.extend(buffer, data)
        _require(StartupSelectionOwner._guard(self) is s
                 and self._root_cell is root and self._buffer is buffer)
