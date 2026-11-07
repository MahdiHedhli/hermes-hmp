"""Pinned complete HMP-package snapshot, not native/runtime/factory admission.

Native Hermes checkout/home are never inventoried here. Independently approved
entry execution, dependencies, loader roots and key/native composition remain
separate. No request or route supplies inventory selection.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import threading
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import NamedTuple

from .presentation_gateway_activation import GatewayActivationOwner
from .presentation_gateway_recipe import GatewayRecipeOwner, _same_recipe_binding
from .presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _expected,
    _HashedArtifact,
    _identity,
)
from .presentation_startup_artifacts import _Scope as IoScope
from .presentation_startup_selection import GatewayStartupSelection, StartupSelectionOwner

_MAX_BYTES = 8 * 1024 * 1024
_MAX_ENTRIES = 20000
_PRIVATE = frozenset((".git", ".env", "profiles", "logs", "credentials", "own.seed", "peer.seed",
                      "config.yaml", "SOUL.md"))


class PackageInventoryError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_GATEWAY_PACKAGE_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise PackageInventoryError


def _vacant(configuration):
    _require(type(configuration) is StartupSelectionOwner
             and type(configuration._origin) is IoScope)
    activation = configuration._origin.activation
    _require(type(activation) is GatewayActivationOwner
             and activation._package_owner is None and activation._package_cell is None
             and activation._package_fact_cell is None)


def _selection(owner, recipe=None, binding=None):
    actual = None
    if recipe is not None:
        _require(type(recipe) is GatewayRecipeOwner)
        actual = GatewayRecipeOwner._loaded_binding(recipe)
        _require(binding is not None and _same_recipe_binding(binding, actual)
                 and owner is actual[0].expected.configuration)
    else:
        _require(binding is None)
    _require(type(owner) is StartupSelectionOwner and type(owner._origin) is IoScope)
    s = owner._origin
    activation = s.activation
    _require(type(activation) is GatewayActivationOwner)
    cell = activation._selection_fact_cell
    _require(type(cell) is tuple and len(cell) == 4 and cell[0] is owner and cell[1] is s
             and type(cell[2]) is GatewayStartupSelection
             and type(cell[2].schema) is int and cell[2].schema == (1 if recipe is None else 2)
             and owner._selection is cell[2]
             and owner._selection_cell is cell and owner._ready is True
             and owner._failed is False and owner._unknown is False)
    _require(StartupSelectionOwner._guard(owner) is s
             and activation._selection_fact_cell is cell and owner._selection_cell is cell
             and owner._selection is cell[2] and owner._ready is True)
    if actual is not None:
        _require(_same_recipe_binding(actual, GatewayRecipeOwner._retained_binding(recipe)))
    return activation, s, cell, cell[2]


class _Manifest(NamedTuple):
    selection: StartupSelectionOwner
    selection_scope: object
    selection_cell: tuple
    selection_data: GatewayStartupSelection
    raw: bytes
    root: str
    entries: tuple
    files: tuple
    scans: list
    recipe: object = None
    recipe_binding: tuple | None = None

    def __repr__(self):
        return "<HmpPackageManifest pinned-DATA redacted>"


@dataclass(repr=False)
class _Scan:
    iterator: object = None
    attempted: bool = False
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _decode(raw, selection):
    document = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(document) is dict
             and document.keys() == {"schema", "kind", "generation", "package", "entries"}
             and type(document["schema"]) is int and document["schema"] == 1
             and type(document["kind"]) is str and document["kind"] == "HMP_GATEWAY_PACKAGE"
             and type(document["generation"]) is str
             and document["generation"] == selection.generation)
    root = document["package"]
    _require(type(root) is str and type(__file__) is str
             and root == os.path.dirname(__file__) and root.startswith("/")
             and all(p not in ("", ".", "..") for p in root[1:].split("/"))
             and not root.startswith(selection.directory + "/")
             and not selection.directory.startswith(root + "/") and root != selection.directory)
    entries, files = _table_rows(root, document["entries"])
    _require(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                        allow_nan=False).encode("ascii") == raw)
    return root, entries, files


def _table_rows(root, rows):
    """Pure bounded table DATA; the actual verifier independently binds root/pin."""
    _require(type(rows) is list and 1 <= len(rows) <= _MAX_ENTRIES)
    entries, files, previous, directories = [], [], "", set()
    for row in rows:
        _require(type(row) is dict and row.keys() == {"path", "kind", "size", "sha256"})
        path, kind = row["path"], row["kind"]
        _require(type(path) is str and 0 < len(path.encode("utf-8")) <= 1024
                 and all(32 <= ord(c) != 127 for c in path)
                 and type(kind) is str and kind in ("file", "directory"))
        parts = path.split("/")
        _require(len(parts) <= 32 and all(p not in ("", ".", "..") and p not in _PRIVATE
                                        and not p.startswith(".env.") for p in parts)
                 and path > previous)
        previous = path
        _require(all("/".join(parts[:i]) in directories for i in range(1, len(parts))))
        if kind == "directory":
            _require(type(row["size"]) is int and row["size"] == 0 and row["sha256"] is None)
            directories.add(path)
        else:
            artifact = ExpectedArtifact(root + "/" + path, row["size"], row["sha256"])
            files.append(artifact)
        entries.append((path, kind))
    _expected(tuple(files))
    return tuple(entries), tuple(files)


def _same_origins(before, after):
    _require(type(before) is tuple and type(after) is tuple and len(before) == len(after))
    for left, right in zip(before, after, strict=True):
        _require(type(left) is tuple and type(right) is tuple and len(left) == len(right) == 8
                 and type(left[0]) is str and type(right[0]) is str and left[0] == right[0])
        _require(all(left[index] is right[index] for index in range(1, 7)))
        # These tuples are independently built only from exact primitive strings.
        if left[7] is None:
            _require(right[7] is None)
        else:
            _require(type(left[7]) is tuple and type(right[7]) is tuple
                     and all(type(value) is str for value in left[7] + right[7])
                     and left[7] == right[7])
    return True


class _Tree(NamedTuple):
    entries: tuple
    files: tuple
    directories: tuple
    ancestors: tuple

    def __repr__(self):
        return "<HmpTreeSnapshot stable-metadata redacted>"


def _snapshot_join(before, after, hashes, meta, owner, scope):
    for tree in (before, after):
        _require(type(tree) is _Tree and type(tree.entries) is tuple
                 and tree.entries == meta.entries)
        for rows, width in ((tree.files, 9), (tree.directories, 5), (tree.ancestors, 5)):
            _require(type(rows) is tuple)
            for row in rows:
                _require(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is tuple and len(row[1]) == width
                         and all(type(value) is int for value in row[1]))
    observed = []
    _require(type(hashes) is tuple and len(hashes) == len(meta.files))
    for receipt, expected in zip(hashes, meta.files, strict=True):
        _require(type(receipt) is _HashedArtifact and receipt.owner is owner
                 and receipt.scope is scope and receipt.expected is expected
                 and type(receipt.identity) is tuple and len(receipt.identity) == 9
                 and all(type(value) is int for value in receipt.identity)
                 and type(receipt.sha256) is str and receipt.sha256 == expected.sha256)
        observed.append((expected.path[len(meta.root) + 1:], receipt.identity))
    observed = tuple(sorted(observed))
    _require(before.files == observed and after.files == observed
             and before.directories == after.directories and before.ancestors == after.ancestors)


class RetainedPackageData(NamedTuple):
    selection: GatewayStartupSelection
    native_root: str
    environment: str
    package_root: str
    manifest: bytes
    entries: tuple
    files: tuple
    file_metadata: tuple
    directory_metadata: tuple
    ancestors: tuple
    origins: tuple

    def __repr__(self):
        return "<RetainedPackageData historical-only no-runtime-authority>"


class GatewayPackageOwner:
    @classmethod
    def verify(cls, configuration, raw):
        _require(cls is GatewayPackageOwner)
        return GatewayPackageOwner._verify(configuration, raw, None, None)

    @classmethod
    def verify_recipe(cls, recipe):
        _require(cls is GatewayPackageOwner and type(recipe) is GatewayRecipeOwner)
        try:
            original = GatewayRecipeOwner._retained_binding(recipe)
            configuration = original[0].expected.configuration
            _vacant(configuration)  # occupied startup refuses before fresh native callbacks
            binding = GatewayRecipeOwner._loaded_binding(recipe)
            _require(_same_recipe_binding(original, binding))
            raw = binding[4][3][1][1]
        except BaseException:
            raise PackageInventoryError from None
        return GatewayPackageOwner._verify(configuration, raw, recipe, binding)

    @classmethod
    def _verify(cls, configuration, raw, recipe, binding):
        _require(cls is GatewayPackageOwner)
        _vacant(configuration)
        activation, configuration_scope, fact, selected = _selection(configuration, recipe, binding)
        _require(activation._package_owner is None and activation._package_cell is None
                 and activation._package_fact_cell is None)
        owner = cls.__new__(cls)
        activation._package_owner = owner  # partial owner before hashing/parsing/native effects
        activation._package_cell = (activation, owner, None)
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._bytes_read = 0 if recipe is None else binding[4][4][2]
        owner._seen = 0
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._fact = owner._fact_cell = None
        fact_cell = None
        failed = False
        try:
            _require(type(raw) is bytes and 0 < len(raw) <= _MAX_BYTES
                     and type(selected.gateway_inventory_sha256) is str)
            if recipe is None:
                expected_hash = selected.gateway_inventory_sha256
            else:
                expected_document = binding[4][3][1]
                _require(raw is expected_document[1])
                expected_hash = expected_document[0].sha256
            digest = hashlib.sha256(raw).hexdigest()
            _require(type(digest) is str and digest == expected_hash)
            current = _selection(configuration, recipe, binding)
            _require(current[1] is configuration_scope and current[2] is fact
                     and current[3] is selected)
            root, entries, files = _decode(raw, selected)
            if recipe is not None:
                _expected(configuration_scope.expected
                          + tuple(row[0] for row in binding[4][3]) + files)
            meta = _Manifest(configuration, configuration_scope, fact, selected, raw,
                             root, entries, files, [], recipe, binding)
            s = IoScope(activation, activation._scope, meta,
                        (os.getpid(), os.geteuid(), threading.get_ident()), [])
            owner._scope = owner._origin = s
            owner._cell = (owner, s)
            owner._root_cell = (activation, owner, s)
            activation._package_cell = owner._root_cell
            owner._count_cell = (owner, s, owner._bytes_read)
            _require(sys.dont_write_bytecode is True)  # no unlisted caches created during entry
            before = GatewayPackageOwner._tree(owner)
            _require(type(before) is _Tree and before.entries == entries)
            hashes = tuple(StartupArtifactOwner._file(owner, artifact) for artifact in files)
            actual_count = owner._count_cell
            after = GatewayPackageOwner._tree(owner)
            _snapshot_join(before, after, hashes, meta, owner, s)
            origins = GatewayPackageOwner._origins(owner)
            _require(GatewayPackageOwner._guard(owner) is s)
            _require(_same_origins(origins, GatewayPackageOwner._origins(owner)))
            _require(all(type(r) is _Descriptor and r.closed is True and r.unknown is False
                         for r in s.records)
                     and all(type(r) is _Scan and r.closed is True and r.unknown is False
                             for r in meta.scans))
            data = RetainedPackageData(
                selected, s.activation_scope.root, s.activation_scope.environment,
                root, raw, entries,
                tuple((item.path, item.size, item.sha256) for item in files),
                after.files, after.directories, after.ancestors,
                tuple((row[0], row[2], row[4], row[7]) for row in origins))
            initial_count = 0 if recipe is None else binding[4][4][2]
            _require(type(actual_count) is tuple and len(actual_count) == 3
                     and actual_count[0] is owner and actual_count[1] is s
                     and type(actual_count[2]) is int and owner._count_cell is actual_count
                     and owner._bytes_read is actual_count[2]
                     and actual_count[2] == initial_count + sum(row.size for row in files)
                     and owner._fact is None and owner._fact_cell is None
                     and activation._package_fact_cell is None)
            fact = (owner, s, entries, origins, hashes, after, data, actual_count)
            fact_cell = (owner, s, fact)
            owner._fact, owner._fact_cell = fact, fact_cell
            activation._package_fact_cell = fact_cell
            owner._ready = True  # package snapshot only; never runtime/key/native admission
            return owner
        except BaseException:
            failed = owner._failed = True
            owner._fact = owner._fact_cell = None
            if fact_cell is not None and activation._package_fact_cell is fact_cell:
                activation._package_fact_cell = None
        if failed:
            raise PackageInventoryError(owner) from None

    def __repr__(self):
        return "<GatewayPackageOwner complete-package-snapshot not-runtime-admission>"

    def _retained_binding(self):
        _require(type(self) is GatewayPackageOwner and type(self._origin) is IoScope
                 and self._scope is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(cell) is tuple and len(cell) == 2 and cell[0] is self and cell[1] is s
                 and type(root) is tuple and len(root) == 3
                 and root[0] is s.activation and root[1] is self and root[2] is s
                 and type(s.expected) is _Manifest and type(s.activation) is GatewayActivationOwner
                 and s.activation._package_owner is self and s.activation._package_cell is root
                 and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
                 and s.activation._retired is False and s.activation._uncertain is False
                 and self._ready is True and self._failed is False
                 and self._unknown is False and self._reading is False
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(value) is int for value in s.context)
                 and type(s.records) is list and type(s.expected.scans) is list
                 and all(type(row) is _Descriptor and row.closed is True
                         and row.unknown is False and row.close_attempted is True
                         for row in s.records)
                 and all(type(row) is _Scan and row.closed is True and row.unknown is False
                         and row.close_attempted is True for row in s.expected.scans))
        parent = StartupSelectionOwner._retained_binding(s.expected.selection)
        _require(parent[0] is s.expected.selection_scope and parent[3] is s.expected.selection_cell)
        if s.expected.recipe is not None:
            _require(type(s.expected.recipe) is GatewayRecipeOwner
                     and _same_recipe_binding(s.expected.recipe_binding,
                         GatewayRecipeOwner._retained_binding(s.expected.recipe)))
        else:
            _require(s.expected.recipe_binding is None)
        fact = s.activation._package_fact_cell
        _require(type(fact) is tuple and len(fact) == 3 and fact[0] is self and fact[1] is s
                 and fact is self._fact_cell and type(fact[2]) is tuple and len(fact[2]) == 8
                 and self._fact is fact[2] and fact[2][0] is self and fact[2][1] is s
                 and fact[2][2] is s.expected.entries
                 and type(fact[2][6]) is RetainedPackageData
                 and fact[2][6].selection is s.expected.selection_data
                 and fact[2][6].manifest is s.expected.raw
                 and type(fact[2][7]) is tuple and len(fact[2][7]) == 3
                 and fact[2][7] is self._count_cell and fact[2][7][0] is self
                 and fact[2][7][1] is s and type(fact[2][7][2]) is int
                 and type(self._bytes_read) is int and self._bytes_read == fact[2][7][2])
        return s, cell, root, fact, parent

    def retained_data(self):
        """Historical immutable inputs; never re-query PM, paths, files or module registry."""
        failed = False
        try:
            s, cell, root, fact, parent = GatewayPackageOwner._retained_binding(self)
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(value) is int for value in context) and context == s.context)
            after = GatewayPackageOwner._retained_binding(self)
            _require(after[0] is s and after[1] is cell and after[2] is root and after[3] is fact
                     and all(old is new for old, new in zip(parent, after[4], strict=True)))
            return fact[2][6]
        except BaseException:
            failed = True
        if failed:
            raise PackageInventoryError(self) from None

    def _guard(self):
        _require(type(self) is GatewayPackageOwner and type(self._origin) is IoScope
                 and self._scope is self._origin and type(self._cell) is tuple
                 and len(self._cell) == 2 and self._cell[0] is self
                 and self._cell[1] is self._origin)
        s, cell, root = self._origin, self._cell, self._root_cell
        _require(type(s.expected) is _Manifest and type(s.activation) is GatewayActivationOwner
                 and s.activation._package_owner is self and type(root) is tuple and len(root) == 3
                 and root[0] is s.activation and root[1] is self and root[2] is s
                 and s.activation._package_cell is root
                 and s.activation._scope is s.activation_scope
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context) and type(s.records) is list
                 and self._failed is False and self._unknown is False and self._reading is False)
        context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in context) and context == s.context)
        meta = s.expected
        current = _selection(meta.selection, meta.recipe, meta.recipe_binding)
        _require(current[0] is s.activation and current[1] is meta.selection_scope
                 and current[2] is meta.selection_cell and current[3] is meta.selection_data
                 and self._scope is s and self._origin is s and self._cell is cell
                 and self._root_cell is root and s.activation._package_cell is root
                 and s.activation._package_owner is self and self._failed is False
                 and self._unknown is False)
        return s

    def _names(self, fd):
        s = GatewayPackageOwner._guard(self)
        root_cell = self._root_cell
        scan = _Scan()
        s.expected.scans.append(scan)  # before iterator constructor/hidden FD effects
        iterator = None
        names = []
        failed = False
        try:
            scan.attempted = True
            iterator = os.scandir(fd)
            scan.iterator = iterator
            _require(GatewayPackageOwner._guard(self) is s)
            while True:
                _require(GatewayPackageOwner._guard(self) is s and type(self._seen) is int)
                before = self._seen
                try:
                    entry = next(iterator)
                except StopIteration:
                    break
                same = self._seen is before and self._scope is s and self._origin is s
                self._seen = before + 1
                _require(same)
                name = entry.name
                _require(type(name) is str and name not in ("", ".", "..")
                         and "/" not in name and len(name.encode("utf-8")) <= 1024)
                _require(self._seen <= 2 * _MAX_ENTRIES
                         and GatewayPackageOwner._guard(self) is s)
                names.append(name)
        except BaseException:
            failed = scan.unknown = self._unknown = True
        finally:
            if iterator is not None:
                scan.close_attempted = True
                try:
                    actual = (os.getpid(), os.geteuid(), threading.get_ident())
                    _require(all(type(v) is int for v in actual) and actual == s.context
                             and GatewayActivationOwner._retained_scope(s.activation)
                             is s.activation_scope and self._root_cell is root_cell
                             and s.activation._package_cell is root_cell)
                    iterator.close()
                    scan.closed = True
                    _require(self._root_cell is root_cell
                             and s.activation._package_cell is root_cell
                             and GatewayActivationOwner._retained_scope(s.activation)
                             is s.activation_scope)
                except BaseException:
                    failed = scan.unknown = self._unknown = True
        if failed:
            raise PackageInventoryError(self) from None
        _require(GatewayPackageOwner._guard(self) is s)
        return sorted(names)

    def _tree(self):
        s = GatewayPackageOwner._guard(self)
        meta, root_cell = s.expected, self._root_cell
        held, result, file_rows, directory_rows, ancestors = [], [], [], [], []
        failed = False
        try:
            parent = None
            for name in ("/", *meta.root[1:].split("/")):
                row, fd = StartupArtifactOwner._open(self, name, parent, True)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(self, fd, s)
                mode = stat.S_IMODE(info.st_mode)
                _require(info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                ancestors.append((name, parent, fd, _identity(info, True)))
                parent = fd
            GatewayPackageOwner._walk(self, parent, "", result, file_rows, directory_rows)
            for name, parent, fd, signature in ancestors:
                _require(_identity(StartupArtifactOwner._fstat(self, fd, s), True) == signature
                         and _identity(StartupArtifactOwner._stat(self, name, parent, s), True)
                         == signature)
        except BaseException:
            failed = True
        finally:
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = self._unknown = failed = True
        if failed:
            raise PackageInventoryError(self) from None
        _require(GatewayPackageOwner._guard(self) is s)
        return _Tree(tuple(sorted(result)), tuple(sorted(file_rows)), tuple(sorted(directory_rows)),
                     tuple((name, signature) for name, _, _, signature in ancestors))

    def _walk(self, fd, prefix, result, file_rows, directory_rows):
        s = GatewayPackageOwner._guard(self)
        root_cell = self._root_cell
        _require(prefix.count("/") <= 32)
        before = _identity(StartupArtifactOwner._fstat(self, fd, s), True)
        directory_rows.append((prefix, before))
        for name in GatewayPackageOwner._names(self, fd):
            _require(name not in _PRIVATE and not name.startswith(".env."))
            path = prefix + name
            info = StartupArtifactOwner._stat(self, name, fd, s)
            _require(len(result) < _MAX_ENTRIES)
            if stat.S_ISREG(info.st_mode):
                result.append((path, "file"))
                file_rows.append((path, _identity(info)))
            else:
                _require(stat.S_ISDIR(info.st_mode))  # no symlinks, devices, pipes or sockets
                result.append((path, "directory"))
                row, child = StartupArtifactOwner._open(self, name, fd, True)
                try:
                    child_info = StartupArtifactOwner._fstat(self, child, s)
                    _require(_identity(child_info, True) == _identity(info, True)
                             and child_info.st_uid in (0, s.context[1])
                             and not child_info.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
                    GatewayPackageOwner._walk(self, child, path + "/", result,
                                             file_rows, directory_rows)
                    _require(_identity(StartupArtifactOwner._stat(self, name, fd, s), True)
                             == _identity(info, True))
                finally:
                    StartupArtifactOwner._close(self, row, child, s, root_cell)
        _require(_identity(StartupArtifactOwner._fstat(self, fd, s), True) == before)

    def _origins(self):
        s = GatewayPackageOwner._guard(self)
        files = {row.path for row in s.expected.files}
        prefix = __package__
        _require(type(prefix) is str and type(sys.modules) is dict)
        result = []
        for name, module in tuple(sys.modules.items()):
            _require(type(name) is str)
            if not (name == prefix or name.startswith(prefix + ".")):
                continue
            _require(type(module) is ModuleType)
            values = vars(module)
            file, spec = values.get("__file__"), values.get("__spec__")
            if name == prefix and file is None and spec is None:
                paths = values.get("__path__")
                _require(type(paths) is list and paths == [])
                result.append((name, module, None, None, None, None, paths, ()))
                continue
            _require(type(file) is str and file in files
                     and (spec is None or type(spec) is ModuleSpec))
            origin = None if spec is None else vars(spec).get("origin")
            _require(origin is None or (type(origin) is str and origin == file))
            loader = None if spec is None else vars(spec).get("loader")
            paths = values.get("__path__")
            if paths is None:
                path_values = None
            else:
                _require(type(paths) in (list, tuple)
                         and all(type(path) is str for path in paths)
                         and tuple(paths) == (os.path.dirname(file),))
                path_values = tuple(paths)
            result.append((name, module, file, spec, origin, loader, paths, path_values))
        return tuple(sorted(result, key=lambda row: row[0]))
