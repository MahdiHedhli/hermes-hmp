"""Original recipe-derived entry/wrapper file snapshot, never runtime admission."""
from __future__ import annotations

import json
import os
import stat
import sys
import threading
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import NamedTuple

from hmp_plugin.presentation_gateway_package import (
    GatewayPackageOwner,
    _same_origins,
    _Scan,
    _table_rows,
    _Tree,
)
from hmp_plugin.presentation_gateway_recipe import GatewayRecipeOwner, _same_recipe_binding
from hmp_plugin.presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _expected,
    _HashedArtifact,
    _identity,
)

from . import gateway_entry
from .gateway_entry import GatewayEntryOwner


class EntryFilesError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_ENTRY_FILES_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise EntryFilesError


def _same_package(before, after):
    _require(type(before) is tuple and type(after) is tuple and len(before) == len(after) == 5)
    return (all(a is b for a, b in zip(before[:4], after[:4], strict=True))
            and all(a is b for a, b in zip(before[4], after[4], strict=True)))


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        _require(name not in result)
        result[name] = value
    return result


class _Inputs(NamedTuple):
    entry: GatewayEntryOwner
    entry_binding: tuple
    recipe: GatewayRecipeOwner
    recipe_binding: tuple
    plugin: GatewayPackageOwner
    plugin_binding: tuple
    raw: bytes
    root: str
    entries: tuple
    files: tuple
    wrapper: ExpectedArtifact
    completion_attempt: tuple
    io_slot: list
    scans: list

    def __repr__(self):
        return "<OriginalEntryFileInputs DATA redacted>"


def _decode(raw, entry_binding, recipe_binding):
    document = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(document) is dict and document.keys() == {
        "schema", "kind", "generation", "package", "entries", "wrapper"}
        and type(document["schema"]) is int and document["schema"] == 1
        and type(document["kind"]) is str and document["kind"] == "HMP_GATEWAY_ENTRY"
        and type(document["generation"]) is str
        and document["generation"] == recipe_binding[0].expected.selection.generation)
    root = document["package"]
    origin = entry_binding[2][5]
    _require(type(root) is str and root == os.path.dirname(origin.file)
             and root == os.path.dirname(__file__)
             and root != recipe_binding[0].expected.selection.directory
             and not root.startswith(recipe_binding[0].expected.selection.directory + "/")
             and not recipe_binding[0].expected.selection.directory.startswith(root + "/"))
    entries, files = _table_rows(root, document["entries"])
    _require(origin.file in {row.path for row in files} and __file__ in {row.path for row in files})
    wrapper = document["wrapper"]
    _require(type(wrapper) is dict and wrapper.keys() == {"path", "size", "sha256"}
             and type(wrapper["path"]) is str and wrapper["path"] == entry_binding[0].file
             and wrapper["path"].rsplit("/", 1)[-1] not in {".env", "SOUL.md", "config.yaml"}
             and not wrapper["path"].startswith(
                 recipe_binding[0].expected.selection.directory + "/"))
    wrapper = ExpectedArtifact(wrapper["path"], wrapper["size"], wrapper["sha256"])
    _expected((wrapper,))
    _require(wrapper.size > 0)
    matching = tuple(row for row in files if row.path == wrapper.path)
    if matching:
        _require(len(matching) == 1 and matching[0].size == wrapper.size
                 and matching[0].sha256 == wrapper.sha256)
        wrapper = matching[0]
    else:
        _require(not wrapper.path.startswith(root + "/"))
    _require(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                        allow_nan=False).encode("ascii") == raw)
    return root, entries, files, wrapper


class EntryFileSnapshotOwner:
    @classmethod
    def verify(cls, entry, recipe, plugin):
        _require(cls is EntryFileSnapshotOwner)
        return EntryFileSnapshotOwner.complete(EntryFileSnapshotOwner.retain(entry, recipe, plugin))

    @classmethod
    def retain(cls, entry, recipe, plugin):
        """Retain original entry inputs before allocating/completing any file IO."""
        _require(cls is EntryFileSnapshotOwner and type(entry) is GatewayEntryOwner
                 and type(recipe) is GatewayRecipeOwner and type(plugin) is GatewayPackageOwner)
        try:
            original_entry = GatewayEntryOwner._retained_binding(entry)
            original_recipe = GatewayRecipeOwner._retained_binding(recipe)
            original_plugin = GatewayPackageOwner._retained_binding(plugin)
            activation = original_recipe[0].activation
            _require(original_entry[2][3] is activation is original_plugin[0].activation
                     and activation._entry_files_owner is None
                     and activation._entry_files_cell is None
                     and activation._entry_files_fact_cell is None
                     and activation._entry_files_attempt_cell is None)
            eb = GatewayEntryOwner.current_binding(entry)
            rb = GatewayRecipeOwner._loaded_binding(recipe)
            pb = GatewayPackageOwner._retained_binding(plugin)
            _require(all(a is b for a, b in zip(original_entry, eb, strict=True))
                     and _same_recipe_binding(original_recipe, rb)
                     and _same_package(original_plugin, pb)
                     and GatewayPackageOwner._guard(plugin) is pb[0]
                     and eb[2][3] is rb[0].activation is pb[0].activation
                     and pb[0].expected.recipe is recipe
                     and _same_recipe_binding(pb[0].expected.recipe_binding, rb))
            activation = rb[0].activation
            _require(activation._entry_files_owner is None and activation._entry_files_cell is None
                     and activation._entry_files_fact_cell is None
                     and activation._entry_files_attempt_cell is None)
        except BaseException:
            raise EntryFilesError from None
        owner = cls.__new__(cls)
        activation._entry_files_owner = owner
        owner._ready = owner._failed = owner._unknown = owner._completing = False
        owner._inputs = owner._root_cell = owner._fact_cell = owner._attempt_cell = None
        owner._seen = 0
        try:
            raw = rb[4][3][2][1]
            root, entries, files, wrapper = _decode(raw, eb, rb)
            owner._inputs = inputs = _Inputs(entry, eb, recipe, rb, plugin, pb, raw,
                                             root, entries, files, wrapper,
                                             (owner, eb, rb, pb), [None], [])
            owner._root_cell = cell = (owner, inputs)
            activation._entry_files_cell = cell
            EntryFileSnapshotOwner._current(owner)
            return owner
        except BaseException:
            owner._failed = True
            raise EntryFilesError(owner) from None

    @classmethod
    def complete(cls, owner):
        """One completion on the original retained plan; never extend a finished IO owner."""
        _require(cls is EntryFileSnapshotOwner and type(owner) is EntryFileSnapshotOwner
                 and owner._ready is False and owner._failed is False
                 and owner._unknown is False and owner._completing is False
                 and type(owner._inputs) is _Inputs)
        inputs, cell = owner._inputs, owner._root_cell
        EntryFileSnapshotOwner._pure_current(owner, inputs, cell)
        _require(type(inputs.io_slot) is list and len(inputs.io_slot) == 1
                 and inputs.io_slot[0] is None and owner._fact_cell is None
                 and owner._attempt_cell is None
                 and inputs.recipe_binding[0].activation._entry_files_attempt_cell is None)
        owner._completing = True  # intent before fresh native/context/file effects
        attempt = inputs.completion_attempt
        owner._attempt_cell = attempt
        inputs.recipe_binding[0].activation._entry_files_attempt_cell = attempt
        fact = None
        activation = inputs.recipe_binding[0].activation
        try:
            EntryFileSnapshotOwner._current(owner)
            files, wrapper = inputs.files, inputs.wrapper
            root, entries = inputs.root, inputs.entries
            plugin = inputs.plugin
            expected = files if any(row is wrapper for row in files) else (*files, wrapper)
            io = StartupArtifactOwner.retain_from_package(plugin, expected)
            inputs.io_slot[0] = io
            before = EntryFileSnapshotOwner._tree(owner, io)
            _require(before.entries == entries)
            wrapper_before = EntryFileSnapshotOwner._metadata(owner, io, wrapper.path)
            EntryFileSnapshotOwner._io_current(owner, io)
            StartupArtifactOwner.complete(io)
            file_fact = io._fact_cell
            after = EntryFileSnapshotOwner._tree(owner, io)
            _require(before == after and type(file_fact) is tuple and len(file_fact) == 4)
            wrapper_after = EntryFileSnapshotOwner._metadata(owner, io, wrapper.path)
            _require(wrapper_before == wrapper_after)
            metadata = dict(after.files)
            for receipt in file_fact[2]:
                _require(type(receipt) is _HashedArtifact and receipt.owner is io
                         and receipt.scope is io._origin)
                if receipt.expected is wrapper:
                    _require(receipt.identity == wrapper_after[0])
                if receipt.expected.path.startswith(root + "/"):
                    relative = receipt.expected.path[len(root) + 1:]
                    _require(metadata[relative] == receipt.identity)
            origins = EntryFileSnapshotOwner._origins(owner)
            _require(_same_origins(origins, EntryFileSnapshotOwner._origins(owner)))
            EntryFileSnapshotOwner._io_current(owner, io)
            _require(owner._inputs is inputs and owner._root_cell is cell
                     and io._fact_cell is file_fact and activation._artifact_fact_cell is file_fact
                     and io._hashes is file_fact[2] and io._count_cell is file_fact[3]
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.unknown is False and row.close_attempted is True
                             for row in io._origin.records)
                     and all(type(row) is _Scan and row.closed is True and row.unknown is False
                             and row.close_attempted is True for row in inputs.scans)
                     and owner._fact_cell is None and activation._entry_files_fact_cell is None
                     and owner._completing is True and owner._attempt_cell is attempt
                     and activation._entry_files_attempt_cell is attempt)
            fact = (owner, inputs, io, file_fact, after, origins)
            owner._fact_cell = activation._entry_files_fact_cell = fact
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = True
            if fact is not None and activation._entry_files_fact_cell is fact:
                activation._entry_files_fact_cell = None
            raise EntryFilesError(owner) from None

    def _current(self):
        _require(type(self) is EntryFileSnapshotOwner and type(self._inputs) is _Inputs
                 and type(self._root_cell) is tuple and len(self._root_cell) == 2
                 and self._root_cell[0] is self and self._root_cell[1] is self._inputs
                 and self._failed is False and self._unknown is False)
        inputs, cell = self._inputs, self._root_cell
        activation = inputs.recipe_binding[0].activation
        eb = GatewayEntryOwner.current_binding(inputs.entry)
        rb = GatewayRecipeOwner._loaded_binding(inputs.recipe)
        pb = GatewayPackageOwner._retained_binding(inputs.plugin)
        _require(all(a is b for a, b in zip(eb, inputs.entry_binding, strict=True))
                 and _same_recipe_binding(inputs.recipe_binding, rb)
                 and _same_package(inputs.plugin_binding, pb)
                 and GatewayPackageOwner._guard(inputs.plugin) is pb[0]
                 and self._inputs is inputs and self._root_cell is cell
                 and activation._entry_files_owner is self and activation._entry_files_cell is cell
                 and self._failed is False and self._unknown is False)
        EntryFileSnapshotOwner._pure_current(self, inputs, cell)
        return inputs

    def _pure_current(self, inputs, cell):
        activation = inputs.recipe_binding[0].activation
        eb = GatewayEntryOwner._retained_binding(inputs.entry)
        rb = GatewayRecipeOwner._retained_binding(inputs.recipe)
        pb = GatewayPackageOwner._retained_binding(inputs.plugin)
        _require(all(a is b for a, b in zip(eb, inputs.entry_binding, strict=True))
                 and GatewayEntryOwner._invocation_state(inputs.entry, eb[0], eb[1]) is eb[0]
                 and gateway_entry._origin_current(eb[2][5]) is eb[2][5]
                 and _same_recipe_binding(inputs.recipe_binding, rb)
                 and _same_package(inputs.plugin_binding, pb)
                 and self._inputs is inputs and self._root_cell is cell
                 and activation._entry_files_owner is self and activation._entry_files_cell is cell
                 and self._failed is False and self._unknown is False)

        original_attempt = inputs.completion_attempt
        _require(type(original_attempt) is tuple and len(original_attempt) == 4
                 and original_attempt[0] is self and original_attempt[1] is inputs.entry_binding
                 and original_attempt[2] is inputs.recipe_binding
                 and original_attempt[3] is inputs.plugin_binding)
        attempt = self._attempt_cell
        if self._completing is False:
            _require(attempt is None and activation._entry_files_attempt_cell is None)
        else:
            _require(self._completing is True and attempt is original_attempt
                     and activation._entry_files_attempt_cell is original_attempt)

    def _io_current(self, io):
        inputs = EntryFileSnapshotOwner._current(self)
        _require(type(io) is StartupArtifactOwner and type(inputs.io_slot) is list
                 and len(inputs.io_slot) == 1 and inputs.io_slot[0] is io
                 and io._origin.activation._artifact_owner is io)
        cell = self._root_cell
        StartupArtifactOwner._guard(io)
        EntryFileSnapshotOwner._pure_current(self, inputs, cell)
        _require(inputs.io_slot[0] is io)
        return inputs

    def _names(self, io, fd):
        inputs = EntryFileSnapshotOwner._io_current(self, io)
        scan = _Scan()
        inputs.scans.append(scan)
        iterator = None
        try:
            scan.attempted = True
            iterator = os.scandir(fd)
            scan.iterator = iterator
            names = []
            while True:
                EntryFileSnapshotOwner._io_current(self, io)
                _require(type(self._seen) is int)
                before_count = self._seen
                try:
                    item = next(iterator)
                except StopIteration:
                    break
                same = self._seen is before_count and self._inputs is inputs
                self._seen = before_count + 1
                _require(same and type(item) is os.DirEntry)
                name = item.name
                _require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
                _require(len(name.encode("utf-8")) <= 1024 and self._seen <= 40000)
                names.append(name)
            return sorted(names)
        except BaseException:
            scan.unknown = self._unknown = True
            raise
        finally:
            if iterator is not None:
                scan.close_attempted = True
                try:
                    context = (os.getpid(), os.geteuid(), threading.get_ident())
                    _require(all(type(value) is int for value in context)
                             and context == io._origin.context and scan.iterator is iterator
                             and any(row is scan for row in inputs.scans))
                    iterator.close()
                    scan.closed = True
                except BaseException:
                    scan.unknown = self._unknown = True
                    raise

    def _tree(self, io):
        inputs = EntryFileSnapshotOwner._io_current(self, io)
        s, root_cell = io._origin, io._root_cell
        held, ancestors, entries, files, directories = [], [], [], [], []
        try:
            parent = None
            for name in ("/", *inputs.root[1:].split("/")):
                row, fd = StartupArtifactOwner._open(io, name, parent, True)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(io, fd, s)
                mode = stat.S_IMODE(info.st_mode)
                _require(info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                ancestors.append((name, parent, fd, _identity(info, True)))
                parent = fd
            EntryFileSnapshotOwner._walk(self, io, parent, "", entries, files, directories)
            for name, parent_fd, fd, signature in ancestors:
                _require(_identity(StartupArtifactOwner._fstat(io, fd, s), True) == signature
                         and _identity(StartupArtifactOwner._stat(io, name, parent_fd, s), True)
                         == signature)
            return _Tree(tuple(sorted(entries)), tuple(sorted(files)), tuple(sorted(directories)),
                         tuple((name, signature) for name, _, _, signature in ancestors))
        finally:
            cleanup_failed = False
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(io, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = io._unknown = self._unknown = True
                    cleanup_failed = True
            if cleanup_failed:
                raise EntryFilesError(self)

    def _metadata(self, io, path):
        EntryFileSnapshotOwner._io_current(self, io)
        s, cell = io._origin, io._root_cell
        held, ancestors = [], []
        try:
            parent = None
            for name in ("/", *path[1:].split("/")[:-1]):
                row, fd = StartupArtifactOwner._open(io, name, parent, True)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(io, fd, s)
                mode = stat.S_IMODE(info.st_mode)
                _require(info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                ancestors.append((name, parent, fd, _identity(info, True)))
                parent = fd
            leaf = _identity(StartupArtifactOwner._stat(io, path.rsplit("/", 1)[1], parent, s))
            for name, parent_fd, fd, signature in ancestors:
                _require(_identity(StartupArtifactOwner._fstat(io, fd, s), True) == signature
                         and _identity(StartupArtifactOwner._stat(io, name, parent_fd, s), True)
                         == signature)
            EntryFileSnapshotOwner._io_current(self, io)
            return leaf, tuple((name, signature) for name, _, _, signature in ancestors)
        finally:
            failed = False
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(io, row, fd, s, cell)
                except BaseException:
                    row.unknown = io._unknown = self._unknown = True
                    failed = True
            if failed:
                raise EntryFilesError(self)

    def _walk(self, io, fd, prefix, entries, files, directories):
        EntryFileSnapshotOwner._io_current(self, io)
        s, cell = io._origin, io._root_cell
        signature = _identity(StartupArtifactOwner._fstat(io, fd, s), True)
        directories.append((prefix, signature))
        for name in EntryFileSnapshotOwner._names(self, io, fd):
            path = prefix + name
            _require(path.count("/") <= 32 and len(entries) < 20000)
            info = StartupArtifactOwner._stat(io, name, fd, s)
            if stat.S_ISREG(info.st_mode):
                entries.append((path, "file"))
                files.append((path, _identity(info)))
            else:
                _require(stat.S_ISDIR(info.st_mode))
                entries.append((path, "directory"))
                row, child = StartupArtifactOwner._open(io, name, fd, True)
                try:
                    current = StartupArtifactOwner._fstat(io, child, s)
                    _require(_identity(current, True) == _identity(info, True)
                             and current.st_uid in (0, s.context[1])
                             and not current.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
                    EntryFileSnapshotOwner._walk(
                        self, io, child, path + "/", entries, files, directories)
                finally:
                    try:
                        StartupArtifactOwner._close(io, row, child, s, cell)
                    except BaseException:
                        row.unknown = io._unknown = self._unknown = True
                        raise
        _require(_identity(StartupArtifactOwner._fstat(io, fd, s), True) == signature)

    def _origins(self):
        inputs = EntryFileSnapshotOwner._current(self)
        paths = {row.path for row in inputs.files}
        rows = []
        _require(type(sys.modules) is dict)
        for name, module in tuple(sys.modules.items()):
            _require(type(name) is str)
            if not (name == __package__ or name.startswith(__package__ + ".")):
                continue
            _require(type(module) is ModuleType)
            values = vars(module)
            file, spec = values.get("__file__"), values.get("__spec__")
            _require(type(file) is str and file in paths
                     and (spec is None or type(spec) is ModuleSpec))
            origin = None if spec is None else vars(spec).get("origin")
            _require(origin is None or (type(origin) is str and origin == file))
            loader = None if spec is None else vars(spec).get("loader")
            search = values.get("__path__")
            _require(search is None or (type(search) in (tuple, list)
                     and all(type(value) is str for value in search)
                     and tuple(search) == (os.path.dirname(file),)))
            search_values = None if search is None else tuple(search)
            rows.append((name, module, file, spec, origin, loader, search, search_values))
        return tuple(rows)

    def __repr__(self):
        return "<EntryFileSnapshotOwner file-DATA not-executed-wrapper-attestation>"
