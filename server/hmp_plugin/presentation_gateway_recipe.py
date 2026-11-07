"""Fixed recipe/child document IO under schema2; DATA, not runtime admission."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import NamedTuple

from .presentation_gateway_activation import GatewayActivationOwner
from .presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _expected,
    _Scope,
)
from .presentation_startup_selection import GatewayStartupSelection, StartupSelectionOwner

_RECIPE_LIMIT = 65536
_CHILD_LIMIT = 8 * 1024 * 1024
_TOTAL_LIMIT = 32 * 1024 * 1024
_CHILDREN = (("plugin", "gateway-package.json"), ("entry", "gateway-entry.json"),
             ("dependencies", "gateway-dependencies.json"),
             ("interpreter", "gateway-interpreter.json"))


class GatewayRecipeError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_RECIPE_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise GatewayRecipeError


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


class _Recipe(NamedTuple):
    configuration: StartupSelectionOwner
    configuration_scope: object
    configuration_cell: tuple
    selection: GatewayStartupSelection
    expected: ExpectedArtifact
    documents: list
    recipe_schema: int

    def __repr__(self):
        return "<GatewayRecipeOriginalInputs redacted>"


def _plan(raw, meta):
    document = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(document) is dict and document.keys() == {
        "schema", "kind", "generation", "plugin", "entry", "dependencies", "interpreter"}
        and type(document["schema"]) is int and document["schema"] == meta.recipe_schema
        and type(document["kind"]) is str and document["kind"] == "HMP_GATEWAY_RECIPE"
        and type(document["generation"]) is str
        and document["generation"] == meta.selection.generation)
    rows = []
    for name, filename in _CHILDREN:
        value = document[name]
        _require(type(value) is dict and value.keys() == {"size", "sha256"}
                 and type(value["size"]) is int and 0 < value["size"] <= _CHILD_LIMIT)
        rows.append(ExpectedArtifact(meta.selection.directory + "/" + filename,
                                     value["size"], value["sha256"]))
    rows = tuple(rows)
    _expected(rows)
    _require(meta.expected.size + sum(row.size for row in rows) <= _TOTAL_LIMIT
             and json.dumps(document, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True, allow_nan=False).encode("ascii") == raw)
    return rows


class GatewayRecipeOwner:
    @classmethod
    def load(cls, configuration, recipe_size):
        """Original recipe1/interpreter1 document path; no version detection."""
        _require(cls is GatewayRecipeOwner)
        return GatewayRecipeOwner._load(configuration, recipe_size, 1)

    @classmethod
    def load_executable_links(cls, configuration, recipe_size):
        """Explicit recipe2/interpreter2 documents; link IO/admission remains separate."""
        _require(cls is GatewayRecipeOwner)
        return GatewayRecipeOwner._load(configuration, recipe_size, 2)

    @classmethod
    def _load(cls, configuration, recipe_size, recipe_schema):
        _require(cls is GatewayRecipeOwner and type(configuration) is StartupSelectionOwner
                 and type(recipe_schema) is int and recipe_schema in (1, 2))
        origin = configuration._origin
        _require(type(origin) is _Scope and type(origin.activation) is GatewayActivationOwner)
        activation = origin.activation
        _require(activation._recipe_owner is None and activation._recipe_cell is None
                 and activation._recipe_plan_cell is None and activation._recipe_fact_cell is None)
        try:
            parent = StartupSelectionOwner._guard(configuration)
            selected = StartupSelectionOwner.retained_data(configuration)
        except BaseException:
            raise GatewayRecipeError from None
        _require(parent is origin and type(selected) is GatewayStartupSelection
                 and type(selected.schema) is int
                 and selected.schema == 2 and type(recipe_size) is int
                 and 0 < recipe_size <= _RECIPE_LIMIT)
        _require(activation._recipe_owner is None and activation._recipe_cell is None
                 and activation._recipe_plan_cell is None and activation._recipe_fact_cell is None)
        owner = cls.__new__(cls)
        activation._recipe_owner = owner  # partial owner before file/hash/parse effects
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._bytes_read = 0
        owner._plan_cell = owner._fact_cell = None
        owner._active = None
        buffer = bytearray()
        owner._buffer = buffer
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._count_cell = None
        fact = None
        failed = False
        try:
            owner._scope = owner._origin = _Scope(
                activation, parent.activation_scope,
                _Recipe(configuration, parent, configuration._selection_cell, selected,
                        ExpectedArtifact(selected.directory + "/gateway-recipe.json",
                                         recipe_size, selected.gateway_inventory_sha256),
                        [], recipe_schema),
                (os.getpid(), os.geteuid(), threading.get_ident()), [])
            s = owner._origin
            owner._cell = (owner, s)
            owner._root_cell = root = (activation, owner, s, (owner, buffer))
            activation._recipe_cell = root
            owner._bytes_read = s.expected.configuration_cell[3][2]
            owner._count_cell = (owner, s, owner._bytes_read)
            raw = GatewayRecipeOwner._document(owner, s.expected.expected)
            actual_count = owner._count_cell
            originals = ((s.expected.expected, raw),)
            rows = _plan(raw, s.expected)
            _require(GatewayRecipeOwner._guard(owner) is s and owner._root_cell is root
                     and owner._plan_cell is None and activation._recipe_plan_cell is None
                     and owner._count_cell is actual_count)
            plan_cell = (owner, s, rows)
            owner._plan_cell = activation._recipe_plan_cell = plan_cell
            for row in rows:
                body = GatewayRecipeOwner._document(owner, row)
                actual_count = owner._count_cell
                originals += ((row, body),)
            _require(GatewayRecipeOwner._guard(owner) is s and owner._root_cell is root
                     and owner._plan_cell is plan_cell and activation._recipe_plan_cell is plan_cell
                     and len(s.expected.documents) == len(originals) == 5 and owner._active is None
                     and all(type(observed) is tuple and len(observed) == 2
                             and observed[0] is held[0] and observed[1] is held[1]
                             for observed, held in zip(
                                 s.expected.documents, originals, strict=True))
                     and type(actual_count) is tuple and len(actual_count) == 3
                     and actual_count[0] is owner and actual_count[1] is s
                     and type(actual_count[2]) is int and owner._count_cell is actual_count
                     and owner._bytes_read is actual_count[2]
                     and owner._bytes_read == s.expected.configuration_cell[3][2]
                     + recipe_size + sum(row.size for row in rows)
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.close_attempted is True and row.unknown is False
                             for row in s.records)
                     and owner._fact_cell is None and activation._recipe_fact_cell is None
                     and owner._ready is False)
            fact = (owner, s, plan_cell, originals, actual_count)
            owner._fact_cell = activation._recipe_fact_cell = fact
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = failed = True
            if fact is not None and activation._recipe_fact_cell is fact:
                activation._recipe_fact_cell = None
            owner._fact_cell = None
        finally:
            buffer[:] = b"\0" * len(buffer)
            buffer.clear()
        if failed:
            raise GatewayRecipeError(owner) from None

    def _retained_binding(self):
        """Original closed document DATA/counter custody, never current admission."""
        _require(type(self) is GatewayRecipeOwner and type(self._origin) is _Scope
                 and self._scope is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self and cell[1] is s
                 and type(root) is tuple and len(root) == 4 and root[0] is s.activation
                 and root[1] is self and root[2] is s and type(root[3]) is tuple
                 and len(root[3]) == 2 and root[3][0] is self and type(root[3][1]) is bytearray
                 and self._buffer is root[3][1] and not root[3][1]
                 and type(s.expected) is _Recipe and type(s.expected.recipe_schema) is int
                 and s.expected.recipe_schema in (1, 2)
                 and type(s.activation) is GatewayActivationOwner
                 and s.activation._recipe_owner is self and s.activation._recipe_cell is root
                 and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
                 and s.activation._retired is False and s.activation._uncertain is False
                 and self._ready is True and self._failed is False and self._unknown is False
                 and self._reading is False and self._active is None
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context) and type(s.records) is list
                 and all(type(row) is _Descriptor and row.closed is True
                         and row.close_attempted is True and row.unknown is False
                         for row in s.records))
        parent = StartupSelectionOwner._retained_binding(s.expected.configuration)
        _require(parent[0] is s.expected.configuration_scope
                 and parent[3] is s.expected.configuration_cell
                 and parent[3][2] is s.expected.selection)
        plan, fact, count = self._plan_cell, self._fact_cell, self._count_cell
        _require(type(plan) is tuple and len(plan) == 3 and plan[0] is self and plan[1] is s
                 and s.activation._recipe_plan_cell is plan
                 and type(plan[2]) is tuple and len(plan[2]) == 4
                 and type(fact) is tuple and len(fact) == 5 and fact[0] is self and fact[1] is s
                 and fact[2] is plan and s.activation._recipe_fact_cell is fact
                 and type(fact[3]) is tuple and len(fact[3]) == 5
                 and type(count) is tuple and len(count) == 3 and fact[4] is count
                 and count[0] is self and count[1] is s and type(count[2]) is int
                 and type(self._bytes_read) is int and self._bytes_read == count[2])
        expected = (s.expected.expected, *plan[2])
        _expected(expected)
        _require(0 < count[2] <= _TOTAL_LIMIT + parent[3][3][2]
                 and count[2] == parent[3][3][2] + sum(row.size for row in expected)
                 and all(type(row) is tuple and len(row) == 2 and row[0] is wanted
                         and type(row[1]) is bytes and len(row[1]) == wanted.size
                         for row, wanted in zip(fact[3], expected, strict=True)))
        return s, cell, root, plan, fact, parent

    def _loaded_binding(self):
        """Fresh early-startup join of original loaded document facts; no IO."""
        try:
            binding = GatewayRecipeOwner._retained_binding(self)
            s = binding[0]
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context) and context == s.context
                     and StartupSelectionOwner._guard(s.expected.configuration)
                     is s.expected.configuration_scope)
            after = GatewayRecipeOwner._retained_binding(self)
            _require(_same_recipe_binding(binding, after))
            return binding
        except BaseException:
            raise GatewayRecipeError(self) from None

    def _guard(self):
        _require(type(self) is GatewayRecipeOwner and type(self._origin) is _Scope
                 and self._scope is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self and cell[1] is s
                 and type(root) is tuple and len(root) == 4 and root[0] is s.activation
                 and root[1] is self and root[2] is s and type(root[3]) is tuple
                 and len(root[3]) == 2 and root[3][0] is self and type(root[3][1]) is bytearray
                 and self._buffer is root[3][1] and type(s.expected) is _Recipe
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context) and type(s.records) is list
                 and type(s.expected.documents) is list
                 and type(s.activation) is GatewayActivationOwner
                 and s.activation._recipe_owner is self and s.activation._recipe_cell is root
                 and s.activation._recipe_plan_cell is self._plan_cell
                 and self._failed is False and self._unknown is False and self._reading is False
                 and self._ready is False and self._fact_cell is None
                 and s.activation._recipe_fact_cell is None
                 and type(self._bytes_read) is int
                 and 0 <= self._bytes_read <= _TOTAL_LIMIT + 65536)
        _require(type(s.expected) is _Recipe and type(s.expected.recipe_schema) is int
                 and s.expected.recipe_schema in (1, 2))
        plan_cell = self._plan_cell
        if plan_cell is not None:
            _require(type(plan_cell) is tuple and len(plan_cell) == 3
                     and plan_cell[0] is self and plan_cell[1] is s
                     and type(plan_cell[2]) is tuple and len(plan_cell[2]) == 4)
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context
                 and StartupSelectionOwner._guard(s.expected.configuration)
                 is s.expected.configuration_scope
                 and s.expected.configuration._selection_cell is s.expected.configuration_cell
                 and s.activation._selection_fact_cell is s.expected.configuration_cell
                 and s.expected.configuration._selection is s.expected.selection
                 and self._scope is s and self._origin is s and self._cell is cell
                 and self._root_cell is root and s.activation._recipe_cell is root
                 and s.activation._recipe_owner is self
                 and self._plan_cell is plan_cell and s.activation._recipe_plan_cell is plan_cell
                 and self._buffer is root[3][1] and self._failed is False
                 and self._unknown is False and self._reading is False
                 and self._ready is False and self._fact_cell is None
                 and s.activation._recipe_fact_cell is None)
        parent = StartupSelectionOwner._retained_binding(s.expected.configuration)
        _require(parent[0] is s.expected.configuration_scope
                 and parent[3] is s.expected.configuration_cell
                 and type(self._bytes_read) is int
                 and parent[3][3][2] <= self._bytes_read
                 <= _TOTAL_LIMIT + parent[3][3][2])
        return s

    def _append(self, data):
        s = GatewayRecipeOwner._guard(self)
        active, buffer, root = self._active, self._buffer, self._root_cell
        _require(type(active) is ExpectedArtifact and type(data) is bytes
                 and len(buffer) + len(data) <= active.size)
        buffer.extend(data)
        _require(GatewayRecipeOwner._guard(self) is s and self._active is active
                 and self._buffer is buffer and self._root_cell is root)

    def _document(self, expected):
        s = GatewayRecipeOwner._guard(self)
        buffer, root = self._buffer, self._root_cell
        _require(not buffer and self._active is None)
        if self._plan_cell is None:
            _require(expected is s.expected.expected and len(s.expected.documents) == 0)
        else:
            index = len(s.expected.documents) - 1
            _require(0 <= index < 4 and expected is self._plan_cell[2][index])
        _expected((expected,))
        self._active = expected
        try:
            StartupArtifactOwner._file(self, expected)
            count_cell, counted = self._count_cell, self._bytes_read
            _require(GatewayRecipeOwner._guard(self) is s and self._active is expected
                     and self._buffer is buffer and self._root_cell is root
                     and len(buffer) == expected.size and self._count_cell is count_cell
                     and self._bytes_read is counted)
            raw = bytes(buffer)
            digest = hashlib.sha256(raw).hexdigest()
            _require(type(digest) is str and digest == expected.sha256
                     and GatewayRecipeOwner._guard(self) is s and self._active is expected
                     and self._buffer is buffer and self._root_cell is root
                     and self._count_cell is count_cell and self._bytes_read is counted)
            if self._plan_cell is not None:
                index = len(s.expected.documents) - 1
                child = json.loads(raw, object_pairs_hook=_pairs)
                kind = ("HMP_GATEWAY_PACKAGE", "HMP_GATEWAY_ENTRY",
                        "HMP_GATEWAY_DEPENDENCIES", "HMP_GATEWAY_INTERPRETER")[index]
                _require(type(child) is dict and type(child.get("schema")) is int
                         and child["schema"] == (s.expected.recipe_schema if index == 3 else 1)
                         and type(child.get("kind")) is str
                         and child["kind"] == kind and type(child.get("generation")) is str
                         and child["generation"] == s.expected.selection.generation
                         and json.dumps(child, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=True, allow_nan=False).encode("ascii") == raw
                         and GatewayRecipeOwner._guard(self) is s
                         and self._buffer is buffer and self._active is expected
                         and self._root_cell is root and self._count_cell is count_cell
                         and self._bytes_read is counted)
            s.expected.documents.append((expected, raw))
            self._active = None
            return raw
        finally:
            buffer[:] = b"\0" * len(buffer)
            buffer.clear()

    def __repr__(self):
        return "<GatewayRecipeOwner document-DATA not-runtime-admitted>"


def _same_recipe_binding(before, after):
    _require(type(before) is tuple and type(after) is tuple and len(before) == len(after) == 6
             and type(before[5]) is tuple and type(after[5]) is tuple
             and len(before[5]) == len(after[5]) == 4)
    return (all(old is new for old, new in zip(before[:5], after[:5], strict=True))
            and all(old is new for old, new in zip(before[5], after[5], strict=True)))
