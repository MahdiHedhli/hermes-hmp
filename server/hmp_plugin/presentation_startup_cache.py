"""Original startup cache absence observations, never import/native authority."""
from __future__ import annotations

import errno
import stat
from dataclasses import dataclass
from typing import NamedTuple


class CacheObservationError(Exception):
    def __init__(self):
        super().__init__("BI1_CACHE_OBSERVATION_REFUSED")


def _require(value):
    if value is not True:
        raise CacheObservationError


class _CacheSource(NamedTuple):
    entry: object
    inputs: object
    cell: tuple
    plan: object
    context_fact: tuple
    paths: tuple
    before: list
    after: list
    effects: list

    def __repr__(self):
        return "<OriginalCacheProbeSource DATA redacted>"


class _Missing(NamedTuple):
    path: str
    index: int
    ancestors: tuple

    def __repr__(self):
        return "<OriginalMissingCacheComponent DATA redacted>"


@dataclass(repr=False)
class _ProbeEffect:
    source: _CacheSource
    phase: int
    index: int
    count: tuple
    attempted: bool = False
    returned: bool = False
    unknown: bool = False
    result: _Missing | None = None
    descriptors: tuple | None = None


class _CachePass(NamedTuple):
    owner: object
    scope: object
    source: _CacheSource
    phase: int
    missing: tuple
    effects: tuple
    count: tuple

    def __repr__(self):
        return "<OriginalCacheAbsencePass sampled-DATA redacted>"


def source_from_entry(entry):
    from hmp_startup.cache_context import CacheContextOwner
    from hmp_startup.entry_files import EntryFileSnapshotOwner, _Inputs
    from hmp_startup.runtime_files import RuntimeFilePlan, _inside, _path

    _require(type(entry) is EntryFileSnapshotOwner and type(entry._inputs) is _Inputs)
    inputs, cell = entry._inputs, entry._root_cell
    _require(type(inputs.runtime_plan) is RuntimeFilePlan and entry._ready is False
             and entry._completing is True and type(inputs.io_slot) is list
             and len(inputs.io_slot) == 1 and inputs.io_slot[0] is None
             and type(inputs.cache_context_slot) is list and len(inputs.cache_context_slot) == 1)
    fact = inputs.cache_context_slot[0]
    _require(type(fact) is tuple and len(fact) == 4 and type(fact[0]) is CacheContextOwner
             and CacheContextOwner.retained_binding(fact[0]) is fact)
    forbidden = (inputs.recipe_binding[0].expected.selection.directory,
                 inputs.recipe_binding[0].activation_scope.root)
    paths = {}
    for row in fact[3]:
        path = row.location.path
        _path(path)
        _require(all(not _inside(path, root) for root in forbidden))
        if row.state == "needs_owned_absence":
            _require(row.cache is None and row.tree is None)
            paths.setdefault(path, path)
    source = _CacheSource(entry, inputs, cell, inputs.runtime_plan, fact,
                          tuple(paths.values()), [None], [None], [])
    source_current(source)
    return source


def source_current(source):
    from hmp_startup.cache_context import CacheContextOwner
    from hmp_startup.entry_files import EntryFileSnapshotOwner, _Inputs
    from hmp_startup.runtime_files import RuntimeFilePlan

    _require(type(source) is _CacheSource and type(source.entry) is EntryFileSnapshotOwner
             and type(source.inputs) is _Inputs and type(source.plan) is RuntimeFilePlan
             and type(source.context_fact) is tuple and len(source.context_fact) == 4
             and type(source.context_fact[0]) is CacheContextOwner
             and source.entry._inputs is source.inputs
             and source.entry._root_cell is source.cell
             and source.inputs.runtime_plan is source.plan
             and source.inputs.cache_context_slot[0] is source.context_fact
             and CacheContextOwner.retained_binding(source.context_fact[0]) is source.context_fact
             and type(source.paths) is tuple and len(source.paths) <= 1024
             and all(type(path) is str for path in source.paths)
             and type(source.before) is list and len(source.before) == 1
             and type(source.after) is list and len(source.after) == 1
             and type(source.effects) is list and len(source.effects) <= 2 * len(source.paths))
    EntryFileSnapshotOwner._pure_lineage(source.entry, source.inputs, source.cell)
    for effect in source.effects:
        _require(type(effect) is _ProbeEffect and effect.source is source
                 and type(effect.phase) is int and effect.phase in (0, 1)
                 and type(effect.index) is int and 0 <= effect.index < len(source.paths)
                 and type(effect.attempted) is bool and type(effect.returned) is bool
                 and effect.unknown is False and type(effect.count) is tuple
                 and len(effect.count) == 3 and type(effect.count[2]) is int)
        if effect.result is not None:
            _missing_shape(effect.result)


def owned_current(source, owner):
    from .presentation_startup_artifacts import StartupArtifactOwner

    _require(type(owner) is StartupArtifactOwner)
    source_current(source)
    _require(owner._origin.cache is source and owner._scope is owner._origin
             and source.inputs.io_slot[0] is owner
             and owner._origin.expected is source.plan.pending)


def _missing_shape(value):
    _require(type(value) is _Missing and type(value.path) is str
             and type(value.index) is int and 0 <= value.index < 64
             and type(value.ancestors) is tuple and 1 <= len(value.ancestors) <= 64)
    for row in value.ancestors:
        _require(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                 and type(row[1]) is tuple and len(row[1]) == 5
                 and all(type(item) is int for item in row[1]))


def _directory(info, context):
    from .presentation_startup_artifacts import _identity

    _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, context[1])
             and not info.st_mode & (stat.S_ISUID | stat.S_ISGID)
             and (not info.st_mode & 0o022
                  or (info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX))))
    return _identity(info, True)


def _is_missing(owner, name, parent, scope, native_registration=None):
    from .presentation_startup_artifacts import StartupArtifactOwner, _native_walk_scope

    _require(_native_walk_scope(owner, native_registration) is scope)
    try:
        value = StartupArtifactOwner._stat(owner, name, parent, scope, native_registration)
    except FileNotFoundError as error:
        _require(type(error) is FileNotFoundError and type(error.errno) is int
                 and error.errno == errno.ENOENT and type(error.filename) is str
                 and error.filename == name)
        code, filename = error.errno, error.filename
        _require(_native_walk_scope(owner, native_registration) is scope and error.errno is code
                 and error.filename is filename)
        return None
    _require(_native_walk_scope(owner, native_registration) is scope)
    return value


def _ancestors_current(owner, scope, ancestors, native_registration=None):
    from .presentation_startup_artifacts import StartupArtifactOwner, _identity, _native_walk_scope

    _require(_native_walk_scope(owner, native_registration) is scope)
    for component, ancestor, fd, original in ancestors:
        _require(_identity(StartupArtifactOwner._fstat(
            owner, fd, scope, native_registration), True) == original
                 and _identity(StartupArtifactOwner._stat(
                     owner, component, ancestor, scope, native_registration), True) == original)
    _require(_native_walk_scope(owner, native_registration) is scope)


def _probe(source, owner, phase, index, native_registration=None):
    from .presentation_startup_artifacts import (
        StartupArtifactOwner,
        _native_registration_tail,
        _native_walk_scope,
    )

    scope = _native_walk_scope(owner, native_registration)
    count, root, owner_cell = owner._count_cell, owner._root_cell, owner._cell
    native_registry = (None if native_registration is None
                       else native_registration.lineage.ledger.scopes)
    effect = _ProbeEffect(source, phase, index, count)
    source.effects.append(effect)  # intent before any acquisition or metadata syscall
    effect.attempted = True
    held, ancestors = [], []
    result = None
    failed = False
    try:
        record, parent = StartupArtifactOwner._open(owner, "/", None, True, native_registration)
        held.append((record, parent))
        signature = _directory(StartupArtifactOwner._fstat(
            owner, parent, scope, native_registration), scope.context)
        ancestors.append(("/", None, parent, signature))
        path = source.paths[index]
        parts = path[1:].split("/")
        _require(1 <= len(parts) <= 64)
        for position, name in enumerate(parts):
            _require(owner._count_cell is count)
            info = _is_missing(owner, name, parent, scope, native_registration)
            if info is None:
                _ancestors_current(owner, scope, ancestors, native_registration)
                _require(_is_missing(owner, name, parent, scope, native_registration) is None)
                _ancestors_current(owner, scope, ancestors, native_registration)
                result = _Missing(path, position,
                                  tuple((component, identity) for component, _, _, identity
                                        in ancestors))
                break
            _require(position < len(parts) - 1)  # present unapproved cache is not absence
            expected = _directory(info, scope.context)
            record, fd = StartupArtifactOwner._open(owner, name, parent, True, native_registration)
            held.append((record, fd))
            _require(_directory(StartupArtifactOwner._fstat(
                owner, fd, scope, native_registration), scope.context)
                     == expected)
            ancestors.append((name, parent, fd, expected))
            parent = fd
        _require(result is not None and owner._count_cell is count)
    except BaseException:
        failed = True
    finally:
        for record, fd in reversed(held):
            try:
                StartupArtifactOwner._close(owner, record, fd, scope, root)
            except BaseException:
                record.unknown = owner._unknown = failed = True
    if failed:
        effect.unknown = owner._unknown = True
        raise CacheObservationError from None
    _require(_native_walk_scope(owner, native_registration) is scope and owner._root_cell is root
             and owner._count_cell is count)
    effect.result = result
    effect.descriptors = tuple(record for record, _ in held)
    effect.returned = True
    _native_registration_tail(owner, scope, owner_cell, root,
                              native_registration, native_registry)
    return result, effect


def observe_pass(source, owner, phase, previous, native_registration=None):
    from .presentation_startup_artifacts import _native_registration_tail, _native_walk_scope

    _require(type(phase) is int and phase in (0, 1))
    scope = _native_walk_scope(owner, native_registration)
    root, owner_cell = owner._root_cell, owner._cell
    native_registry = (None if native_registration is None
                       else native_registration.lineage.ledger.scopes)
    _require(scope.cache is source)
    owned_current(source, owner)
    count = owner._count_cell
    before_slot, after_slot = source.before, source.after
    _require((phase == 0 and previous is None and source.before[0] is None
              and source.after[0] is None and len(source.effects) == 0)
             or (phase == 1 and type(previous) is _CachePass and source.before[0] is previous
                 and source.after[0] is None and len(source.effects) == len(source.paths)))
    missing, effects = [], []
    for index in range(len(source.paths)):
        value, effect = _probe(source, owner, phase, index, native_registration)
        missing.append(value)
        effects.append(effect)
        _require(owner._count_cell is count and (phase == 0 or source.before[0] is previous))
    result = _CachePass(owner, owner._origin, source, phase, tuple(missing), tuple(effects), count)
    if phase == 1:
        _require(len(previous.missing) == len(result.missing))
        for before, after in zip(previous.missing, result.missing, strict=True):
            _missing_shape(before)
            _missing_shape(after)
            _require(before == after)
    _require(_native_walk_scope(owner, native_registration) is scope
             and scope.cache is source and owner._count_cell is count
             and (phase == 0 or source.before[0] is previous))
    _require(source.before is before_slot and source.after is after_slot
             and len(before_slot) == len(after_slot) == 1
             and ((phase == 0 and before_slot[0] is None and after_slot[0] is None)
                  or (phase == 1 and before_slot[0] is previous and after_slot[0] is None)))
    _native_registration_tail(owner, scope, owner_cell, root,
                              native_registration, native_registry)
    (before_slot if phase == 0 else after_slot)[0] = result
    return result


def seal(source, owner, before, after):
    from .presentation_startup_artifacts import _descriptor_closed_in_scope

    owned_current(source, owner)
    _require(type(before) is _CachePass and type(after) is _CachePass
             and source.before[0] is before and source.after[0] is after
             and before.owner is owner and after.owner is owner
             and before.scope is owner._origin is after.scope
             and before.source is source is after.source
             and type(before.phase) is int and type(after.phase) is int
             and before.phase == 0 and after.phase == 1
             and before.count is owner._initial_count_cell
             and after.count is owner._count_cell
             and type(before.missing) is tuple and type(after.missing) is tuple
             and len(before.missing) == len(after.missing) == len(source.paths)
             and len(source.effects) == 2 * len(source.paths))
    for result in (before, after):
        _require(type(result.missing) is tuple and type(result.effects) is tuple
                 and len(result.effects) == len(result.missing) == len(source.paths))
        for index, effect in enumerate(result.effects):
            _require(effect is source.effects[result.phase * len(source.paths) + index]
                     and effect.phase == result.phase and effect.index == index
                     and effect.count is result.count
                     and effect.returned is True and effect.unknown is False
                     and type(effect.result) is _Missing and effect.result is result.missing[index]
                     and effect.result.path is source.paths[index]
                     and type(effect.descriptors) is tuple
                     and all(_descriptor_closed_in_scope(row, owner._origin)
                             and any(original is row for original in owner._origin.records)
                             for row in effect.descriptors))
    return source
