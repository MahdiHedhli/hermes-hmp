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

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner
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
    _capture_native_scope,
    _descriptor_closed_in_scope,
    _descriptor_refused,
    _expected,
    _HashedArtifact,
    _identity,
    _native_registration_tail,
    _native_walk_scope,
    _Scope,
)


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
    runtime_plan: object
    io_slot: list
    scans: list
    cache_context_slot: list

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
    def verify_runtime_files(cls, entry, recipe, plugin):
        _require(cls is EntryFileSnapshotOwner)
        return EntryFileSnapshotOwner.complete(
            EntryFileSnapshotOwner.retain_runtime_files(entry, recipe, plugin))

    @classmethod
    def retain_runtime_files(cls, entry, recipe, plugin):
        _require(cls is EntryFileSnapshotOwner)
        return EntryFileSnapshotOwner._retain(entry, recipe, plugin, True)

    @classmethod
    def retain_runtime_link_files(cls, entry, recipe, plugin):
        """Explicit selected-link path; completion retains link/target snapshot DATA only."""
        _require(cls is EntryFileSnapshotOwner)
        return EntryFileSnapshotOwner._retain(entry, recipe, plugin, True, True)

    @classmethod
    def retain(cls, entry, recipe, plugin):
        """Entry-only compatibility path; never a complete runtime snapshot."""
        _require(cls is EntryFileSnapshotOwner)
        return EntryFileSnapshotOwner._retain(entry, recipe, plugin, False)

    @classmethod
    def _retain(cls, entry, recipe, plugin, runtime_files, executable_links=False):
        _require(type(runtime_files) is bool and type(executable_links) is bool
                 and (runtime_files or not executable_links))
        _require(cls is EntryFileSnapshotOwner and type(entry) is GatewayEntryOwner
                 and type(recipe) is GatewayRecipeOwner and type(plugin) is GatewayPackageOwner)
        try:
            original_entry = GatewayEntryOwner._retained_binding(entry)
            original_recipe = GatewayRecipeOwner._retained_binding(recipe)
            original_plugin = GatewayPackageOwner._retained_binding(plugin)
            if runtime_files:
                _require(original_recipe[0].expected.recipe_schema
                         == (2 if executable_links else 1))
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
        owner._cache_context_cell = None
        owner._seen = 0
        try:
            raw = rb[4][3][2][1]
            root, entries, files, wrapper = _decode(raw, eb, rb)
            plan = None
            if runtime_files:
                from .runtime_files import build_runtime_link_plan, build_runtime_plan
                builder = build_runtime_link_plan if executable_links else build_runtime_plan
                plan = builder(eb, rb, pb, root, entries, files, wrapper)
            owner._inputs = inputs = _Inputs(entry, eb, recipe, rb, plugin, pb, raw,
                                             root, entries, files, wrapper,
                                             (owner, eb, rb, pb), plan, [None], [], [None])
            owner._root_cell = cell = (owner, inputs)
            activation._entry_files_cell = cell
            if plan is not None:
                from .cache_context import CacheContextOwner
                CacheContextOwner.retain(owner)
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
        try:
            EntryFileSnapshotOwner._pure_current(owner, inputs, cell)
            _require(type(inputs.io_slot) is list and len(inputs.io_slot) == 1
                     and inputs.io_slot[0] is None and owner._fact_cell is None
                     and owner._attempt_cell is None
                     and inputs.recipe_binding[0].activation._entry_files_attempt_cell is None)
        except BaseException:
            owner._failed = True
            raise EntryFilesError(owner) from None
        owner._completing = True  # intent before fresh native/context/file effects
        attempt = inputs.completion_attempt
        owner._attempt_cell = attempt
        inputs.recipe_binding[0].activation._entry_files_attempt_cell = attempt
        fact = None
        activation = inputs.recipe_binding[0].activation
        try:
            EntryFileSnapshotOwner._current(owner)
            files, wrapper = inputs.files, inputs.wrapper
            plugin, plan = inputs.plugin, inputs.runtime_plan
            if plan is None:
                expected = files if any(row is wrapper for row in files) else (*files, wrapper)
                packages = ((inputs.root, inputs.entries),)
                loose, prior, dependency_origins = (wrapper,), (), None
            else:
                from .runtime_files import loaded_origins
                expected = plan.pending
                packages = tuple((row.path, row.entries) for row in plan.packages)
                loose, prior = plan.loose, plan.prior
                dependency_origins = loaded_origins(plan)
            linked = plan is not None and plan.executable_link is not None
            if plan is not None:
                io = StartupArtifactOwner.retain_from_cache_entry(owner)
                _require(inputs.io_slot[0] is io)
            else:
                io = StartupArtifactOwner.retain_from_package(plugin, expected)
                _require(inputs.io_slot[0] is None)
                inputs.io_slot[0] = io
            io_scope, io_cell, io_root = io._origin, io._cell, io._root_cell
            native_registration = _capture_native_scope(io_scope, io_cell, io_root)
            native_registry = (None if native_registration is None
                               else native_registration.lineage.ledger.scopes)
            before = tuple((root, EntryFileSnapshotOwner._tree(
                owner, io, root, native_registration)) for root, _ in packages)
            _require(all(tree.entries == entries for (_, tree), (_, entries)
                         in zip(before, packages, strict=True)))
            loose_before = tuple((row.path, EntryFileSnapshotOwner._metadata(
                owner, io, row.path, native_registration)) for row in loose)
            if prior:
                prior_metadata = {root + '/' + path: identity for root, tree in before
                                  for path, identity in tree.files}
                for path, value in loose_before:
                    _require(path not in prior_metadata or prior_metadata[path] == value[0])
                    prior_metadata[path] = value[0]
                _require(all(prior_metadata[row.expected.path] == row.identity for row in prior))
            EntryFileSnapshotOwner._io_current(owner, io, native_registration)
            StartupArtifactOwner.complete(io)
            file_fact, file_attempt = io._fact_cell, io._attempt_cell
            after = tuple((root, EntryFileSnapshotOwner._tree(owner, io, root, native_registration))
                          for root, _ in packages)
            _require(before == after and type(file_fact) is tuple
                     and len(file_fact) == (5 if linked else 4))
            loose_after = tuple((row.path, EntryFileSnapshotOwner._metadata(
                owner, io, row.path, native_registration)) for row in loose)
            _require(loose_before == loose_after)
            metadata = {root + '/' + path: identity for root, tree in after
                        for path, identity in tree.files}
            for path, value in loose_after:
                _require(path not in metadata or metadata[path] == value[0])
                metadata[path] = value[0]
            for receipt in file_fact[2]:
                _require(type(receipt) is _HashedArtifact and receipt.owner is io
                         and receipt.scope is io._origin)
            for receipt in (*prior, *file_fact[2]):
                _require(type(receipt) is _HashedArtifact
                         and metadata[receipt.expected.path] == receipt.identity)
            if linked:
                link_fact = StartupArtifactOwner.recheck_link_metadata(io)
                _require(link_fact is file_fact[4])
                EntryFileSnapshotOwner._pure_current(owner, inputs, cell)
            origins = EntryFileSnapshotOwner._origins(owner)
            _require(_same_origins(origins, EntryFileSnapshotOwner._origins(owner)))
            EntryFileSnapshotOwner._io_current(owner, io, native_registration)
            if plan is not None:
                _require(_same_origins(dependency_origins, loaded_origins(plan)))
                EntryFileSnapshotOwner._pure_current(owner, inputs, cell)
            if plan is not None:
                cache_fact = inputs.cache_context_slot[0]
                from .cache_context import CacheContextOwner
                _require(type(cache_fact) is tuple and len(cache_fact) == 4
                         and type(cache_fact[0]) is CacheContextOwner
                         and CacheContextOwner.current_binding(cache_fact[0]) is cache_fact)
                EntryFileSnapshotOwner._pure_current(owner, inputs, cell)
            # Last origin sampling follows the last native/context callbacks.
            current_origins = EntryFileSnapshotOwner._origins(owner)
            _require(_same_origins(origins, current_origins))
            if plan is not None:
                _require(_same_origins(dependency_origins, loaded_origins(plan)))
            if linked:
                _require(StartupArtifactOwner.seal_link_observation(io, file_fact) is link_fact)
            _require(owner._inputs is inputs and owner._root_cell is cell
                     and io._scope is io_scope is io._origin
                     and io._cell is io_cell and io._root_cell is io_root
                     and activation._artifact_cell is io_root
                     and io._attempt_cell is file_attempt
                     and activation._artifact_attempt_cell is file_attempt
                     and io._ready is True and io._failed is False
                     and io._unknown is False and io._reading is False
                     and io._bytes_read is file_fact[3][2]
                     and io._fact_cell is file_fact and activation._artifact_fact_cell is file_fact
                     and io._hashes is file_fact[2] and io._count_cell is file_fact[3]
                     and all(_descriptor_closed_in_scope(row, io._origin)
                             for row in io._origin.records)
                     and all(type(row) is _Scan and row.closed is True and row.unknown is False
                             and row.close_attempted is True for row in inputs.scans)
                     and owner._fact_cell is None and activation._entry_files_fact_cell is None
                     and owner._completing is True and owner._attempt_cell is attempt
                     and activation._entry_files_attempt_cell is attempt)
            if plan is not None:
                _require(StartupArtifactOwner.seal_cache_observation(io) is io._cache_fact)
            snapshot = after[0][1] if plan is None else after
            origin_snapshot = origins if plan is None else (origins, dependency_origins)
            fact = (owner, inputs, io, file_fact, snapshot, origin_snapshot)
            if plan is not None:
                fact += (loose_after, io._cache_fact)  # original ancestry and cache observations
            _native_registration_tail(io, io_scope, io_cell, io_root,
                                      native_registration, native_registry)
            _require(owner._inputs is inputs and owner._root_cell is cell
                     and owner._fact_cell is None and activation._entry_files_fact_cell is None
                     and owner._ready is False and owner._failed is False
                     and owner._unknown is False and owner._completing is True
                     and owner._attempt_cell is attempt
                     and activation._entry_files_attempt_cell is attempt
                     and io._scope is io_scope is io._origin
                     and io._cell is io_cell and io._root_cell is io_root
                     and activation._artifact_cell is io_root
                     and io._attempt_cell is file_attempt
                     and activation._artifact_attempt_cell is file_attempt
                     and io._ready is True and io._failed is False
                     and io._unknown is False and io._reading is False
                     and io._fact_cell is file_fact and activation._artifact_fact_cell is file_fact
                     and io._hashes is file_fact[2] and io._count_cell is file_fact[3]
                     and io._bytes_read is file_fact[3][2])
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
        _require(type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1)
        cache_slot = inputs.cache_context_slot
        cache_fact = cache_slot[0]
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
        _require(inputs.cache_context_slot is cache_slot and len(cache_slot) == 1
                 and cache_slot[0] is cache_fact)
        if inputs.runtime_plan is not None:
            from .cache_context import CacheContextOwner
            _require(type(cache_fact) is tuple and len(cache_fact) == 4
                     and type(cache_fact[0]) is CacheContextOwner
                     and CacheContextOwner.current_binding(cache_fact[0]) is cache_fact)
        EntryFileSnapshotOwner._pure_current(self, inputs, cell)
        return inputs

    def _pure_lineage(self, inputs, cell):
        activation = inputs.recipe_binding[0].activation
        eb = GatewayEntryOwner._retained_binding(inputs.entry)
        rb = GatewayRecipeOwner._retained_binding(inputs.recipe)
        pb = GatewayPackageOwner._retained_binding(inputs.plugin)
        _require(all(a is b for a, b in zip(eb, inputs.entry_binding, strict=True))
                 and GatewayEntryOwner._invocation_values(inputs.entry, eb[0], eb[1]) is eb[0]
                 and gateway_entry._origin_current(eb[2][5]) is eb[2][5]
                 and _same_recipe_binding(inputs.recipe_binding, rb)
                 and _same_package(inputs.plugin_binding, pb)
                 and self._inputs is inputs and self._root_cell is cell
                 and activation._entry_files_owner is self and activation._entry_files_cell is cell
                 and self._failed is False and self._unknown is False)

        if inputs.runtime_plan is not None:
            from .runtime_files import plan_current
            plan_current(inputs.runtime_plan, inputs.entry_binding,
                         inputs.recipe_binding, inputs.plugin_binding)
        _require(type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1)
        if inputs.runtime_plan is None:
            _require(inputs.cache_context_slot[0] is None and self._cache_context_cell is None)
        else:
            from .cache_context import CacheContextOwner
            cache_fact = inputs.cache_context_slot[0]
            _require(type(cache_fact) is tuple and len(cache_fact) == 4
                     and type(cache_fact[0]) is CacheContextOwner
                     and CacheContextOwner.retained_binding(cache_fact[0]) is cache_fact
                     and cache_fact[1] is self._cache_context_cell)
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

    def _pure_current(self, inputs, cell):
        EntryFileSnapshotOwner._pure_lineage(self, inputs, cell)
        eb = inputs.entry_binding
        _require(GatewayEntryOwner._invocation_state(inputs.entry, eb[0], eb[1]) is eb[0])

    def _io_current(self, io, native_registration=None):
        _require(type(io) is StartupArtifactOwner)
        io_scope, io_cell, io_root = io._origin, io._cell, io._root_cell
        _require(type(io_scope) is _Scope
                 and type(io_scope.activation) is GatewayActivationOwner)
        inputs = EntryFileSnapshotOwner._current(self)
        _require(io._origin is io_scope and io._scope is io_scope
                 and io._cell is io_cell and io._root_cell is io_root)
        _require(type(inputs.io_slot) is list and len(inputs.io_slot) == 1
                 and inputs.io_slot[0] is io and io_scope.activation._artifact_owner is io)
        cell = self._root_cell
        _require(_native_walk_scope(io, native_registration) is io_scope)
        EntryFileSnapshotOwner._pure_current(self, inputs, cell)
        _require(inputs.io_slot[0] is io)
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(io, io_scope, io_cell, io_root, native_registration, registry)
        return inputs

    def _names(self, io, fd, native_registration=None):
        inputs = EntryFileSnapshotOwner._io_current(self, io, native_registration)
        io_scope, io_cell, io_root = io._origin, io._cell, io._root_cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        scan = _Scan()
        inputs.scans.append(scan)
        iterator = None
        try:
            scan.attempted = True
            iterator = os.scandir(fd)
            scan.iterator = iterator
            names = []
            while True:
                EntryFileSnapshotOwner._io_current(self, io, native_registration)
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
            result = sorted(names)
        except BaseException:
            scan.unknown = self._unknown = True
            raise
        finally:
            if iterator is not None:
                scan.close_attempted = True
                try:
                    context = (os.getpid(), os.geteuid(), threading.get_ident())
                    _require(all(type(value) is int for value in context)
                             and context == io_scope.context and scan.iterator is iterator
                             and any(row is scan for row in inputs.scans))
                    iterator.close()
                    scan.closed = True
                except BaseException:
                    scan.unknown = self._unknown = True
                    raise

        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        _native_registration_tail(io, io_scope, io_cell, io_root, native_registration, registry)
        return result

    def _tree(self, io, root=None, native_registration=None):
        inputs = EntryFileSnapshotOwner._io_current(self, io, native_registration)
        if root is None:
            root = inputs.root
        _require(type(root) is str and (root is inputs.root or
                 (inputs.runtime_plan is not None
                  and any(root is row.path for row in inputs.runtime_plan.packages))))
        s, root_cell, io_cell = io._origin, io._root_cell, io._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        held, ancestors, entries, files, directories = [], [], [], [], []
        try:
            parent = None
            for name in ("/", *root[1:].split("/")):
                row, fd = StartupArtifactOwner._open(io, name, parent, True, native_registration)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(io, fd, s, native_registration)
                mode = stat.S_IMODE(info.st_mode)
                _require(info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                ancestors.append((name, parent, fd, _identity(info, True)))
                parent = fd
            EntryFileSnapshotOwner._walk(self, io, parent, "", entries, files, directories,
                                         native_registration)
            for name, parent_fd, fd, signature in ancestors:
                _require(_identity(StartupArtifactOwner._fstat(
                    io, fd, s, native_registration), True) == signature
                         and _identity(StartupArtifactOwner._stat(
                             io, name, parent_fd, s, native_registration), True)
                         == signature)
            result = _Tree(tuple(sorted(entries)), tuple(sorted(files)),
                           tuple(sorted(directories)),
                         tuple((name, signature) for name, _, _, signature in ancestors))
        finally:
            cleanup_failed = False
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(io, row, fd, s, root_cell)
                except BaseException:
                    _descriptor_refused(row)
                    io._unknown = self._unknown = True
                    cleanup_failed = True
            if cleanup_failed:
                raise EntryFilesError(self)

        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        _native_registration_tail(io, s, io_cell, root_cell, native_registration, registry)
        return result

    def _metadata(self, io, path, native_registration=None):
        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        s, cell, io_cell = io._origin, io._root_cell, io._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        held, ancestors = [], []
        try:
            parent = None
            for name in ("/", *path[1:].split("/")[:-1]):
                row, fd = StartupArtifactOwner._open(io, name, parent, True, native_registration)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(io, fd, s, native_registration)
                mode = stat.S_IMODE(info.st_mode)
                _require(info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                ancestors.append((name, parent, fd, _identity(info, True)))
                parent = fd
            leaf = _identity(StartupArtifactOwner._stat(
                io, path.rsplit("/", 1)[1], parent, s, native_registration))
            for name, parent_fd, fd, signature in ancestors:
                _require(_identity(StartupArtifactOwner._fstat(
                    io, fd, s, native_registration), True) == signature
                         and _identity(StartupArtifactOwner._stat(
                             io, name, parent_fd, s, native_registration), True)
                         == signature)
            EntryFileSnapshotOwner._io_current(self, io, native_registration)
            result = leaf, tuple((name, signature) for name, _, _, signature in ancestors)
        finally:
            failed = False
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(io, row, fd, s, cell)
                except BaseException:
                    _descriptor_refused(row)
                    io._unknown = self._unknown = True
                    failed = True
            if failed:
                raise EntryFilesError(self)

        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        _native_registration_tail(io, s, io_cell, cell, native_registration, registry)
        return result

    def _walk(self, io, fd, prefix, entries, files, directories, native_registration=None):
        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        s, cell, io_cell = io._origin, io._root_cell, io._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        signature = _identity(StartupArtifactOwner._fstat(io, fd, s, native_registration), True)
        directories.append((prefix, signature))
        for name in EntryFileSnapshotOwner._names(self, io, fd, native_registration):
            path = prefix + name
            _require(path.count("/") <= 32 and len(entries) < 20000)
            info = StartupArtifactOwner._stat(io, name, fd, s, native_registration)
            if stat.S_ISREG(info.st_mode):
                entries.append((path, "file"))
                files.append((path, _identity(info)))
            else:
                _require(stat.S_ISDIR(info.st_mode))
                entries.append((path, "directory"))
                row, child = StartupArtifactOwner._open(io, name, fd, True, native_registration)
                try:
                    current = StartupArtifactOwner._fstat(io, child, s, native_registration)
                    _require(_identity(current, True) == _identity(info, True)
                             and current.st_uid in (0, s.context[1])
                             and not current.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
                    EntryFileSnapshotOwner._walk(
                        self, io, child, path + "/", entries, files, directories,
                        native_registration)
                finally:
                    try:
                        StartupArtifactOwner._close(io, row, child, s, cell)
                    except BaseException:
                        _descriptor_refused(row)
                        io._unknown = self._unknown = True
                        raise
        _require(_identity(StartupArtifactOwner._fstat(
            io, fd, s, native_registration), True) == signature)
        EntryFileSnapshotOwner._io_current(self, io, native_registration)
        _native_registration_tail(io, s, io_cell, cell, native_registration, registry)

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


# Define the complete snapshot types/helpers before the cycle enters original
# Entry capture. These aliases are used only by method bodies, not definitions.
from . import gateway_entry  # noqa: E402
from .gateway_entry import GatewayEntryOwner  # noqa: E402
