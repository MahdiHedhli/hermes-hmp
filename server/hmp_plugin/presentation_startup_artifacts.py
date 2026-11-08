"""Owned bounded startup artifact observations, not runtime admission.

Only the future fixed startup/configuration loader supplies external expectations.
No route imports this module. Matching selected files is not complete reachable
inventory/loader qualification or permission to load keys or publish images.
"""
from __future__ import annotations

import hashlib
import os
import stat
import threading
from dataclasses import dataclass
from types import FunctionType
from typing import NamedTuple

from .presentation_gateway_activation import GatewayActivationOwner

_MAX_FILES = 1024
_MAX_FILE = 128 * 1024 * 1024
_MAX_TOTAL = 2 * 1024 * 1024 * 1024


class ArtifactObservationError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_STARTUP_ARTIFACTS_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise ArtifactObservationError


class ExpectedArtifact(NamedTuple):
    path: str
    size: int
    sha256: str

    def __repr__(self):
        return "<ExternalArtifactExpectation DATA not-approval redacted>"


class OperatorApprovalPath(NamedTuple):
    """Fixed operator-private trust anchor, explicitly not a pinned artifact."""
    path: str

    def __repr__(self):
        return "<OperatorApprovalPath fixed-private-anchor redacted>"


class _OperatorFileReceipt(NamedTuple):
    owner: object
    scope: object
    path: OperatorApprovalPath
    identity: tuple
    sha256: str
    count: tuple
    descriptors: tuple
    reads: tuple

    def __repr__(self):
        return "<OriginalOperatorFileObservation not-runtime-admission redacted>"


@dataclass(repr=False)
class _ReadEffect:
    before: tuple
    after: tuple | None = None
    returned: bool = False
    unknown: bool = False


class _HashedArtifact(NamedTuple):
    owner: object
    scope: object
    expected: ExpectedArtifact
    identity: tuple
    sha256: str
    bytecode_header: bytes
    source_hash: bytes = b""
    source_digest: object = None
    source_mtime: int | None = None

    def __repr__(self):
        return "<HashedArtifact original-descriptor DATA redacted>"


@dataclass(repr=False)
class _Descriptor:
    fd: int | None = None
    attempted: bool = False
    close_attempted: bool = False
    closed: bool = False
    unknown: bool = False


class _Scope(NamedTuple):
    activation: GatewayActivationOwner
    activation_scope: object
    expected: tuple
    context: tuple
    records: list
    parent: object = None
    runtime: object = None
    reads: object = None
    cache: object = None
    source_digest: object = None
    native_files: object = None
    native_registration_slot: object = None

    def __repr__(self):
        return "<StartupArtifactScope redacted>"


class _PackageSource(NamedTuple):
    owner: object
    binding: tuple
    count_cell: tuple
    expected: tuple

    def __repr__(self):
        return "<OriginalPackageCountSource DATA redacted>"


class _RuntimeSource(NamedTuple):
    entry: object
    entry_type: type
    inputs: object
    cell: tuple
    guard: object
    code: object
    plan: object
    link: object
    reads: list
    before: list
    after: list
    count: list
    bound: int

    def __repr__(self):
        return "<OriginalRuntimeLinkSource DATA redacted>"


@dataclass(repr=False)
class _LinkRead:
    hop: object
    phase: int
    index: int
    before: tuple
    attempted: bool = False
    returned: bool = False
    after: tuple | None = None
    data: bytes | None = None
    unknown: bool = False


class _ReadlinkObservation(NamedTuple):
    record: _LinkRead
    before: tuple
    after: tuple
    data: bytes

    def __repr__(self):
        return "<OriginalReadlinkObservation DATA redacted>"


class _LinkSnapshot(NamedTuple):
    source: _RuntimeSource
    phase: int
    links: tuple
    target: tuple
    reads: tuple
    count: tuple

    def __repr__(self):
        return "<OriginalExecutableLinkSnapshot DATA redacted>"


class _LinkTargetObservation(NamedTuple):
    owner: object
    scope: object
    source: _RuntimeSource
    before: _LinkSnapshot
    after: _LinkSnapshot
    receipt: _HashedArtifact
    count: tuple

    def __repr__(self):
        return "<OriginalLinkTargetObservation DATA not-admission redacted>"


def _link_bound(runtime):
    # Standard selected CPython's fixed MAXPATHLEN readlink buffer. This premise
    # is not installed-runtime admission; custom builds need independent qualification.
    _require(type(runtime.implementation) is tuple and len(runtime.implementation) == 3
             and type(runtime.implementation[0]) is str
             and runtime.implementation[0] == "cpython"
             and type(runtime.version) is tuple and len(runtime.version) == 5
             and type(runtime.version[0]) is int and runtime.version[0] == 3
             and type(runtime.version[1]) is int and 11 <= runtime.version[1] < 15
             and type(runtime.platform) is str and runtime.platform in ("darwin", "linux"))
    return 1024 if runtime.platform == "darwin" else 4096


def _runtime_source(entry):
    from hmp_startup.entry_files import EntryFileSnapshotOwner
    from hmp_startup.runtime_files import ExecutableLinkPlan, RuntimeFilePlan

    _require(type(entry) is EntryFileSnapshotOwner)
    inputs = EntryFileSnapshotOwner._current(entry)
    plan = inputs.runtime_plan
    _require(type(plan) is RuntimeFilePlan and type(plan.executable_link) is ExecutableLinkPlan
             and entry._completing is True and entry._attempt_cell is inputs.completion_attempt
             and type(inputs.io_slot) is list and len(inputs.io_slot) == 1
             and inputs.io_slot[0] is None)
    guard = EntryFileSnapshotOwner._pure_current
    _require(type(guard) is FunctionType)
    bound = _link_bound(plan.runtime)
    _require(all(0 < len(hop.target) < bound for hop in plan.executable_link.hops))
    return _RuntimeSource(entry, EntryFileSnapshotOwner, inputs, entry._root_cell,
                          guard, guard.__code__, plan, plan.executable_link,
                          [], [None], [None], [None], bound)


def _runtime_seal(source, owner):
    _require(type(source) is _RuntimeSource
             and type(source.entry) is source.entry_type
             and source.entry._inputs is source.inputs and source.entry._root_cell is source.cell
             and source.inputs.runtime_plan is source.plan
             and source.plan.executable_link is source.link
             and type(source.guard) is FunctionType and source.guard.__code__ is source.code
             and source.entry_type._pure_current is source.guard
             and type(source.count) is list and len(source.count) == 1
             and type(source.before) is list and len(source.before) == 1
             and type(source.after) is list and len(source.after) == 1
             and type(source.reads) is list
             and type(source.inputs.io_slot) is list and len(source.inputs.io_slot) == 1
             and source.inputs.io_slot[0] is owner)
    count = source.count[0]
    _require(type(count) is tuple and len(count) == 3 and count[0] is owner
             and count[1] is owner._origin and type(count[2]) is int)
    _require(owner._count_cell is count and owner._bytes_read is count[2])
    return count


def _runtime_current(source, owner):
    count = _runtime_seal(source, owner)
    source.guard(source.entry, source.inputs, source.cell)
    _require(_runtime_seal(source, owner) is count)


def _link_reads_current(source, snapshot):
    _require(type(snapshot) is _LinkSnapshot and snapshot.source is source
             and type(snapshot.phase) is int and snapshot.phase in (0, 1)
             and type(snapshot.reads) is tuple
             and len(snapshot.reads) == len(source.link.hops))
    for i, (observation, hop) in enumerate(zip(snapshot.reads, source.link.hops, strict=True)):
        _require(type(observation) is _ReadlinkObservation)
        row = observation.record
        index = snapshot.phase * len(source.link.hops) + i
        _require(type(row) is _LinkRead and len(source.reads) > index
                 and source.reads[index] is row and row.hop is hop
                 and type(row.phase) is int and row.phase == snapshot.phase
                 and type(row.index) is int and row.index == index
                 and row.attempted is True and row.returned is True and row.unknown is False
                 and row.before is observation.before and row.after is observation.after
                 and row.data is observation.data and observation.data == hop.target)


def _package_source(package):
    from .presentation_gateway_package import GatewayPackageOwner
    _require(type(package) is GatewayPackageOwner)
    binding = GatewayPackageOwner._retained_binding(package)
    _require(GatewayPackageOwner._guard(package) is binding[0])
    after = GatewayPackageOwner._retained_binding(package)
    _require(all(a is b for a, b in zip(binding[:4], after[:4], strict=True))
             and all(a is b for a, b in zip(binding[4], after[4], strict=True)))
    meta = binding[0].expected
    _require(meta.recipe is not None and type(meta.recipe_binding) is tuple)
    from .presentation_startup_selection import _configuration_rows
    previous = (_configuration_rows(meta.selection)
                + tuple(row[0] for row in meta.recipe_binding[4][3]) + meta.files)
    return _PackageSource(package, binding, binding[3][2][7], previous)


def _source_current(source):
    _require(type(source) is _PackageSource)
    actual = _package_source(source.owner)
    _require(source.count_cell is actual.count_cell
             and all(a is b for a, b in zip(source.binding[:4], actual.binding[:4], strict=True))
             and all(a is b for a, b in zip(source.binding[4], actual.binding[4], strict=True))
             and type(source.expected) is tuple and len(source.expected) == len(actual.expected)
             and all(a is b for a, b in zip(source.expected, actual.expected, strict=True)))


def _identity(row, directory=False):
    _require(type(row) is os.stat_result)
    result = (row.st_dev, row.st_ino, row.st_mode, row.st_uid, row.st_gid)
    if not directory:
        result += (row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
    _require(all(type(v) is int for v in result))
    return result


def _expected(rows):
    _require(type(rows) is tuple and 1 <= len(rows) <= _MAX_FILES)
    seen, total = set(), 0
    for row in rows:
        _require(type(row) is ExpectedArtifact and type(row.path) is str
                 and 1 < len(row.path.encode("utf-8")) <= 4096
                 and row.path.startswith("/")
                 and all(32 <= ord(c) != 127 for c in row.path))
        parts = row.path[1:].split("/")
        _require(1 <= len(parts) <= 64 and all(p not in ("", ".", "..") for p in parts)
                 and row.path not in seen and type(row.size) is int
                 and 0 <= row.size <= _MAX_FILE and type(row.sha256) is str
                 and len(row.sha256) == 64 and all(c in "0123456789abcdef" for c in row.sha256))
        seen.add(row.path)
        total += row.size
        _require(total <= _MAX_TOTAL)


def _configuration(owner):
    if type(owner) is StartupArtifactOwner:
        return False
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return True
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return False
    from .presentation_gateway_recipe import GatewayRecipeOwner
    if type(owner) is GatewayRecipeOwner:
        return True
    from hmp_startup.gateway_approval import GatewayApprovalOwner
    if type(owner) is GatewayApprovalOwner:
        return True
    from hmp_startup.runtime_reader import RuntimeSourceReadOwner
    if type(owner) is RuntimeSourceReadOwner:
        return False
    from hmp_startup.cache_probe import RuntimeCacheProbeOwner
    if type(owner) is RuntimeCacheProbeOwner:
        return False
    from hmp_startup.cache_reader import DeclaredCacheReadOwner
    _require(type(owner) is DeclaredCacheReadOwner)
    return False


def _owner_guard(owner):
    if type(owner) is StartupArtifactOwner:
        return StartupArtifactOwner._guard(owner)
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return StartupSelectionOwner._guard(owner)
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return GatewayPackageOwner._guard(owner)
    from .presentation_gateway_recipe import GatewayRecipeOwner
    if type(owner) is GatewayRecipeOwner:
        return GatewayRecipeOwner._guard(owner)
    from hmp_startup.gateway_approval import GatewayApprovalOwner
    if type(owner) is GatewayApprovalOwner:
        return GatewayApprovalOwner._guard(owner)
    from hmp_startup.runtime_reader import RuntimeSourceReadOwner
    if type(owner) is RuntimeSourceReadOwner:
        return RuntimeSourceReadOwner._guard(owner)
    from hmp_startup.cache_probe import RuntimeCacheProbeOwner
    if type(owner) is RuntimeCacheProbeOwner:
        return RuntimeCacheProbeOwner._guard(owner)
    from hmp_startup.cache_reader import DeclaredCacheReadOwner
    _require(type(owner) is DeclaredCacheReadOwner)
    return DeclaredCacheReadOwner._guard(owner)


def _root(owner, activation):
    if type(owner) is StartupArtifactOwner:
        return activation._artifact_cell
    from .presentation_startup_selection import StartupSelectionOwner
    if type(owner) is StartupSelectionOwner:
        return activation._selection_cell
    from .presentation_gateway_package import GatewayPackageOwner
    if type(owner) is GatewayPackageOwner:
        return activation._package_cell
    from .presentation_gateway_recipe import GatewayRecipeOwner
    if type(owner) is GatewayRecipeOwner:
        return activation._recipe_cell
    from hmp_startup.gateway_approval import GatewayApprovalOwner
    if type(owner) is GatewayApprovalOwner:
        return activation._approval_cell
    from hmp_startup.runtime_reader import RuntimeSourceReadOwner
    if type(owner) is RuntimeSourceReadOwner:
        return activation._runtime_read_cell
    from hmp_startup.cache_probe import RuntimeCacheProbeOwner
    if type(owner) is RuntimeCacheProbeOwner:
        return activation._runtime_cache_probe_cell
    from hmp_startup.cache_reader import DeclaredCacheReadOwner
    _require(type(owner) is DeclaredCacheReadOwner)
    return activation._cache_read_cell


def _append_configuration(owner, data):
    if _configuration(owner):
        from .presentation_startup_selection import StartupSelectionOwner
        if type(owner) is StartupSelectionOwner:
            StartupSelectionOwner._append(owner, data)
        else:
            from .presentation_gateway_recipe import GatewayRecipeOwner
            if type(owner) is GatewayRecipeOwner:
                GatewayRecipeOwner._append(owner, data)
            else:
                from hmp_startup.gateway_approval import GatewayApprovalOwner
                _require(type(owner) is GatewayApprovalOwner)
                GatewayApprovalOwner._append(owner, data)
    elif type(owner) is not StartupArtifactOwner:
        from .presentation_gateway_package import GatewayPackageOwner
        if type(owner) is not GatewayPackageOwner:
            from hmp_startup.runtime_reader import RuntimeSourceReadOwner
            if type(owner) is RuntimeSourceReadOwner:
                RuntimeSourceReadOwner._append(owner, data)
            else:
                from hmp_startup.cache_reader import DeclaredCacheReadOwner
                _require(type(owner) is DeclaredCacheReadOwner)
                DeclaredCacheReadOwner._append(owner, data)


class _NativeDeclaredWalk(NamedTuple):
    """One predeclared file-walk allocation; not a native operation claim."""
    owner: object
    scope: _Scope
    cell: tuple
    root: tuple
    declaration: tuple
    expected: ExpectedArtifact
    index: int
    components: tuple
    state: list

    def __repr__(self):
        return "<OriginalDeclaredFileWalk not-operation-authority redacted>"


class _NativeScopeRegistration(NamedTuple):
    """Original scope provenance DATA; not an operation/consumer claim."""
    lineage: object
    owner: object
    scope: _Scope
    cell: tuple
    root: tuple
    context: tuple
    index: int
    file_walks: tuple
    file_progress: list

    def __repr__(self):
        return "<OriginalNativeScopeRegistration DATA redacted>"


def _capture_native_scope(s, cell, root):
    """Capture original scope-slot DATA without an actor/current callback."""
    _require(type(s) is _Scope and type(cell) is tuple and len(cell) == 2
             and cell[1] is s and type(root) is tuple and len(root) == 3
             and root[0] is s.activation and root[1] is cell[0] and root[2] is s)
    slot = s.native_registration_slot
    if s.native_files is None:
        _require(slot is None)
        return None
    _require(type(slot) is list and len(slot) == 1)
    record = slot[0]
    _require(type(record) is _NativeScopeRegistration
             and record.scope is s and record.owner is cell[0]
             and record.cell is cell and record.root is root
             and record.lineage is s.native_files and record.context is s.context)
    return record


def _native_scope_current(owner, record):
    from hmp_startup.gateway_entry import (
        GatewayEntryOwner,
        _NativeFileLedger,
        _NativeFileLineage,
    )

    _require(type(record) is _NativeScopeRegistration and record.owner is owner
             and type(record.scope) is _Scope
             and type(record.lineage) is _NativeFileLineage
             and type(record.lineage.ledger) is _NativeFileLedger)
    s, lineage, cell, root = record.scope, record.lineage, record.cell, record.root
    registry, index = lineage.ledger.scopes, record.index
    slot = s.native_registration_slot
    _require(type(slot) is list and len(slot) == 1 and slot[0] is record)
    _require(type(registry) is list and type(index) is int and 0 <= index < len(registry)
             and registry[index] is record and s.native_files is lineage)
    _require(_owner_guard(owner) is s
             and GatewayEntryOwner._native_file_lineage(lineage.entry) is lineage)
    _require(owner._scope is s and owner._origin is s
             and owner._cell is cell and owner._root_cell is root
             and vars(owner).get('_native_scope_registration') is record
             and record.context is s.context and lineage.ledger.scopes is registry
             and index < len(registry) and registry[index] is record
             and s.native_registration_slot is slot and len(slot) == 1
             and slot[0] is record)
    return record


def _register_native_scope(owner, s, cell, root):
    _require(type(s) is _Scope)
    slot = s.native_registration_slot
    _require((s.native_files is None and slot is None)
             or (s.native_files is not None and type(slot) is list
                 and len(slot) == 1 and slot[0] is None))
    _require(_owner_guard(owner) is s
             and owner._scope is s and owner._origin is s
             and owner._cell is cell and owner._root_cell is root)
    if s.native_files is None:
        return None
    from hmp_startup.gateway_entry import GatewayEntryOwner, _NativeFileLineage

    lineage = s.native_files
    _require(type(lineage) is _NativeFileLineage
             and GatewayEntryOwner._native_file_lineage(lineage.entry) is lineage)
    registry = lineage.ledger.scopes
    index = len(registry)
    _require(index < 1048576 and vars(owner).get('_native_scope_registration') is None
             and s.native_registration_slot is slot and len(slot) == 1 and slot[0] is None
             and type(s.context) is tuple and len(s.context) == 3
             and all(type(value) is int for value in s.context))
    actor = (os.getpid(), os.geteuid(), threading.get_ident())
    _require(all(type(value) is int for value in actor) and actor == s.context
             and _owner_guard(owner) is s)
    _require(owner._scope is s and owner._origin is s
             and owner._cell is cell and owner._root_cell is root
             and s.native_files is lineage and lineage.ledger.scopes is registry
             and len(registry) == index
             and vars(owner).get('_native_scope_registration') is None
             and s.native_registration_slot is slot and len(slot) == 1 and slot[0] is None)
    from .presentation_gateway_package import GatewayPackageOwner, _Manifest

    declaration = s.expected
    if type(owner) is GatewayPackageOwner:
        _require(type(declaration) is _Manifest)
        declaration = declaration.files
    _expected(declaration)
    walks = tuple(_NativeDeclaredWalk(owner, s, cell, root, declaration, expected,
                                     ordinal, ("/", *expected.path[1:].split("/")), [0])
                  for ordinal, expected in enumerate(declaration))
    progress = [0]
    record = _NativeScopeRegistration(lineage, owner, s, cell, root, s.context, index,
                                      walks, progress)
    _require(type(record) is _NativeScopeRegistration and record.lineage is lineage
             and record.owner is owner and record.scope is s
             and record.cell is cell and record.root is root
             and record.context is s.context and record.index is index
             and owner._scope is s and owner._origin is s
             and owner._cell is cell and owner._root_cell is root
             and lineage.ledger.scopes is registry and len(registry) == index
             and vars(owner).get('_native_scope_registration') is None
             and s.native_registration_slot is slot and len(slot) == 1 and slot[0] is None)
    registry.append(record)
    _require(vars(owner).get('_native_scope_registration') is None
             and s.native_registration_slot is slot and len(slot) == 1 and slot[0] is None)
    slot[0] = record
    _require(vars(owner).get('_native_scope_registration') is None
             and len(slot) == 1 and slot[0] is record)
    owner._native_scope_registration = record
    _require(_native_scope_current(owner, record) is record)
    return record


def _native_registration_tail(owner, s, cell, root, registration, registry):
    """Pure held DATA rejoin after the fixed caller's last work callback."""
    _require(type(s) is _Scope and type(cell) is tuple and len(cell) == 2
             and cell[0] is owner and cell[1] is s
             and type(root) is tuple and len(root) in (3, 4)
             and root[0] is s.activation and root[1] is owner and root[2] is s
             and owner._scope is s and owner._origin is s
             and owner._cell is cell and owner._root_cell is root)
    if registration is None:
        # Preserve the already-validated legacy configuration/approval root.
        _require(registry is None and s.native_files is None
                 and s.native_registration_slot is None)
        return
    _require(_capture_native_scope(s, cell, root) is registration)
    _require(type(registry) is list and type(registration.index) is int
             and 0 <= registration.index < len(registry)
             and registry[registration.index] is registration
             and vars(owner).get('_native_scope_registration') is registration)


def _native_walk_scope(owner, registration):
    if registration is None:
        s = _owner_guard(owner)
        _require(s.native_files is None and s.native_registration_slot is None)
        return s
    return _native_scope_current(owner, registration).scope


def _begin_native_declared_walk(owner, registration, expected):
    _require(type(registration) is _NativeScopeRegistration)
    walks, progress = registration.file_walks, registration.file_progress
    _require(type(walks) is tuple and len(walks) <= _MAX_FILES
             and type(progress) is list and len(progress) == 1
             and type(progress[0]) is int and 0 <= progress[0] < len(walks))
    index = progress[0]
    plan = walks[index]
    _require(type(plan) is _NativeDeclaredWalk and plan.expected is expected
             and plan.owner is owner and plan.scope is registration.scope
             and plan.cell is registration.cell and plan.root is registration.root
             and type(plan.index) is int and plan.index == index
             and type(plan.declaration) is tuple
             and len(plan.declaration) == len(walks)
             and plan.declaration[index] is expected
             and type(plan.state) is list and len(plan.state) == 1
             and type(plan.state[0]) is int and plan.state[0] == 0)
    state = plan.state
    _require(_native_scope_current(owner, registration) is registration
             and registration.file_walks is walks and registration.file_progress is progress
             and len(progress) == 1 and progress[0] is index
             and walks[index] is plan and plan.state is state and len(state) == 1
             and type(state[0]) is int and state[0] == 0)
    state[0] = 1  # file-walk intent only, before any descriptor acquisition
    return plan, walks, progress, index, state


def _finish_native_declared_walk(owner, registration, held):
    _require(type(registration) is _NativeScopeRegistration
             and type(held) is tuple and len(held) == 5)
    plan, walks, progress, index, state = held
    _require(type(plan) is _NativeDeclaredWalk and type(walks) is tuple
             and type(index) is int and 0 <= index < len(walks))
    _native_registration_tail(owner, registration.scope, registration.cell,
                              registration.root, registration,
                              registration.lineage.ledger.scopes)
    _require(registration.file_walks is walks and registration.file_progress is progress
             and type(progress) is list and len(progress) == 1 and progress[0] is index
             and walks[index] is plan and plan.state is state and len(state) == 1
             and type(state[0]) is int and state[0] == 1)
    state[0] = 2
    progress[0] = index + 1


def _native_relative_arguments(s, name, parent):
    """Primitive shape only; does not grant path/descriptor or step authority."""
    if s.native_files is None:
        return
    _require(type(name) is str and type(parent) in (int, type(None)))
    if parent is None:
        _require(name == "/")
    else:
        _require(parent >= 0 and len(name) > 0 and name not in (".", "..")
                 and "/" not in name and "\x00" not in name)


def _native_descriptor_argument(s, fd):
    if s.native_files is not None:
        _require(type(fd) is int and fd >= 0)


class StartupArtifactOwner:
    @classmethod
    def observe(cls, activation, expected):
        _require(cls is StartupArtifactOwner)
        return StartupArtifactOwner.complete(StartupArtifactOwner.retain(activation, expected))

    @classmethod
    def retain(cls, activation, expected):
        _require(cls is StartupArtifactOwner)
        return StartupArtifactOwner._retain(activation, expected, None)

    @classmethod
    def retain_from_package(cls, package, expected):
        _require(cls is StartupArtifactOwner)
        source = _package_source(package)
        return StartupArtifactOwner._retain(source.binding[0].activation, expected, source)

    @classmethod
    def retain_from_runtime_entry(cls, entry):
        _require(cls is StartupArtifactOwner)
        runtime = _runtime_source(entry)
        source = _package_source(runtime.inputs.plugin)
        return StartupArtifactOwner._retain(source.binding[0].activation,
                                           runtime.plan.pending, source, runtime)

    @classmethod
    def retain_from_cache_entry(cls, entry):
        from .presentation_startup_cache import source_from_entry
        _require(cls is StartupArtifactOwner)
        cache = source_from_entry(entry)
        runtime = (_runtime_source(entry) if cache.plan.executable_link is not None else None)
        source = _package_source(cache.inputs.plugin)
        return StartupArtifactOwner._retain(source.binding[0].activation,
                                           cache.plan.pending, source, runtime, cache)

    @classmethod
    def _retain(cls, activation, expected, source, runtime=None, cache=None):
        _require(cls is StartupArtifactOwner and type(activation) is GatewayActivationOwner
                 and activation._artifact_owner is None and activation._artifact_cell is None
                 and activation._artifact_attempt_cell is None
                 and activation._artifact_fact_cell is None)
        GatewayActivationOwner.current(activation)
        _require(activation._artifact_owner is None and activation._artifact_cell is None)
        owner = cls.__new__(cls)
        activation._artifact_owner = owner
        activation._artifact_cell = (activation, owner)
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._facts = owner._hashes = owner._attempt_cell = owner._fact_cell = None
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._count_cell = owner._initial_count_cell = None
        owner._cache_fact = None
        owner._bytes_read = 0
        try:
            if source is not None:
                _require(type(source) is _PackageSource)
                owner._bytes_read = source.count_cell[2]
            digest_context = None if source is None else source.owner._origin.source_digest
            s = _Scope(activation, activation._scope, expected,
                       (os.getpid(), os.geteuid(), threading.get_ident()), [], source, runtime,
                       None if digest_context is None else [], cache, digest_context,
                       None if digest_context is None else digest_context.native_files,
                       None if digest_context is None else [None])
            owner._scope = owner._origin = s
            owner._cell = (owner, s)
            owner._root_cell = (activation, owner, s)
            activation._artifact_cell = owner._root_cell
            scope_cell, scope_root = owner._cell, owner._root_cell
            owner._count_cell = owner._initial_count_cell = (owner, s, owner._bytes_read)
            if runtime is not None:
                _require(type(runtime) is _RuntimeSource and len(runtime.inputs.io_slot) == 1
                         and runtime.inputs.io_slot[0] is None
                         and runtime.plan.pending is expected)
                runtime.guard(runtime.entry, runtime.inputs, runtime.cell)
                _require(runtime.inputs.io_slot[0] is None)
                runtime.inputs.io_slot[0] = owner
                runtime.count[0] = owner._initial_count_cell
                _require(len(source.expected) + len(expected) + len(runtime.link.hops) <= _MAX_FILES
                         and owner._bytes_read + sum(row.size for row in expected)
                         + 2 * runtime.link.text_bytes <= _MAX_TOTAL)
            if cache is not None:
                from .presentation_startup_cache import source_current
                source_current(cache)
                _require(cache.plan.pending is expected
                         and (cache.inputs.io_slot[0] is None or cache.inputs.io_slot[0] is owner)
                         and len(source.expected) + len(expected) + len(cache.paths)
                         + (0 if runtime is None else len(runtime.link.hops)) <= _MAX_FILES)
                cache.inputs.io_slot[0] = owner
            _expected(expected)
            if source is not None:
                _source_current(source)
                _expected(source.expected + expected)
            StartupArtifactOwner._guard(owner)
            _register_native_scope(owner, s, scope_cell, scope_root)
            _require(owner._origin is s and owner._scope is s
                     and owner._cell is scope_cell and owner._root_cell is scope_root
                     and activation._artifact_cell is scope_root)
            return owner
        except BaseException:
            owner._failed = True
            raise ArtifactObservationError(owner) from None

    @classmethod
    def complete(cls, owner):
        _require(cls is StartupArtifactOwner and type(owner) is StartupArtifactOwner
                 and type(owner._origin) is _Scope)
        s, root = owner._origin, owner._root_cell
        native_registration = _capture_native_scope(s, owner._cell, root)
        activation = s.activation
        _require(owner._ready is False and owner._failed is False and owner._unknown is False
                 and owner._attempt_cell is None and activation._artifact_attempt_cell is None)
        _require(owner._scope is s and owner._origin is s and owner._root_cell is root
                 and activation._artifact_owner is owner and activation._artifact_cell is root)
        attempt = (owner, s, root)
        owner._attempt_cell = activation._artifact_attempt_cell = attempt
        fact = None
        try:
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            _require(all(type(v) is int for v in context) and context == s.context)
            _require(_native_walk_scope(owner, native_registration) is s
                     and owner._count_cell is owner._initial_count_cell
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.unknown is False and row.close_attempted is True
                             for row in s.records))
            runtime = s.runtime
            cache_before = cache_after = None
            if s.cache is not None:
                from .presentation_startup_cache import observe_pass
                cache_before = observe_pass(s.cache, owner, 0, None, native_registration)
            before = after = link_fact = None
            if runtime is not None:
                _require(runtime.before[0] is None and runtime.after[0] is None
                         and runtime.reads == [])
                before = StartupArtifactOwner._link_snapshot(owner, 0, None, native_registration)
                _require(runtime.before[0] is None)
                runtime.before[0] = before
            collected = []
            progress = owner._count_cell
            for row in s.expected:
                _require(owner._count_cell is progress)
                collected.append(StartupArtifactOwner._file(owner, row, native_registration))
                progress = owner._count_cell
            hashes = tuple(collected)
            if runtime is not None:
                _require(runtime.before[0] is before)
                _link_reads_current(runtime, before)
                after = StartupArtifactOwner._link_snapshot(owner, 1, before, native_registration)
                _require(runtime.before[0] is before and runtime.after[0] is None
                         and before.links == after.links and before.target == after.target)
                runtime.after[0] = after
                _link_reads_current(runtime, before)
                _link_reads_current(runtime, after)
                receipts = (*runtime.plan.prior, *hashes)
                targets = tuple(row for row in receipts if row.expected is runtime.link.target)
                _require(len(targets) == 1 and targets[0].identity == after.target[0]
                         and targets[0].identity[3] == runtime.link.uid
                         and stat.S_IMODE(targets[0].identity[2]) == runtime.link.mode)
                link_fact = _LinkTargetObservation(owner, s, runtime, before, after,
                                                   targets[0], owner._count_cell)
            if s.cache is not None:
                from .presentation_startup_cache import seal
                cache_after = observe_pass(s.cache, owner, 1, cache_before, native_registration)
                _require(seal(s.cache, owner, cache_before, cache_after) is s.cache)
            count = owner._count_cell
            _require(_native_walk_scope(owner, native_registration) is s
                     and owner._root_cell is root and owner._attempt_cell is attempt
                     and activation._artifact_attempt_cell is attempt
                     and type(count) is tuple and len(count) == 3
                     and count[0] is owner and count[1] is s and type(count[2]) is int
                     and owner._count_cell is count and owner._bytes_read is count[2]
                     and count[2] == owner._initial_count_cell[2]
                     + sum(row.size for row in s.expected)
                     + (0 if runtime is None else 2 * runtime.link.text_bytes)
                     and count[2] <= _MAX_TOTAL
                     and all(type(row) is _HashedArtifact and row.owner is owner
                             and row.scope is s and row.expected is expected
                             for row, expected in zip(hashes, s.expected, strict=True))
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.unknown is False and row.close_attempted is True
                             for row in s.records)
                     and owner._facts is None and owner._hashes is None
                     and owner._fact_cell is None and activation._artifact_fact_cell is None)
            if runtime is not None:
                _require(runtime.before[0] is before and runtime.after[0] is after
                         and link_fact.count is count)
            fact = ((owner, s, hashes, count) if runtime is None
                    else (owner, s, hashes, count, link_fact))
            if s.cache is not None:
                _require(seal(s.cache, owner, cache_before, cache_after) is s.cache
                         and owner._cache_fact is None)
                owner._cache_fact = (owner, s, s.cache, cache_before, cache_after, count)
            owner._facts = tuple(row.expected for row in hashes)
            owner._hashes = hashes
            owner._fact_cell = activation._artifact_fact_cell = fact
            owner._ready = True
            return owner
        except BaseException:
            owner._failed = True
            if fact is not None and activation._artifact_fact_cell is fact:
                activation._artifact_fact_cell = None
            raise ArtifactObservationError(owner) from None

    def __repr__(self):
        return "<StartupArtifactOwner historical-files-not-admission redacted>"

    def _guard(self):
        _require(type(self) is StartupArtifactOwner and type(self._origin) is _Scope
                 and self._scope is self._origin and type(self._cell) is tuple
                 and len(self._cell) == 2 and self._cell[0] is self
                 and self._cell[1] is self._origin)
        s, cell, root_cell = self._origin, self._cell, self._root_cell
        _require(type(s.activation) is GatewayActivationOwner
                 and s.activation._artifact_owner is self
                 and type(root_cell) is tuple and len(root_cell) == 3
                 and s.activation._artifact_cell is root_cell
                 and root_cell[0] is s.activation and root_cell[1] is self
                 and root_cell[2] is s
                 and s.activation._scope is s.activation_scope
                 and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context)
                 and self._failed is False and self._unknown is False
                 and type(s.records) is list and self._reading is False)
        attempt, fact = self._attempt_cell, self._fact_cell
        held_count = self._count_cell
        _require(s.activation._artifact_attempt_cell is attempt
                 and s.activation._artifact_fact_cell is fact)
        actual = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(all(type(v) is int for v in actual) and actual == s.context)
        GatewayActivationOwner.current(s.activation)
        if s.parent is not None:
            _source_current(s.parent)
        if s.runtime is not None:
            _runtime_current(s.runtime, self)
        if s.cache is not None:
            from .presentation_startup_cache import owned_current
            owned_current(s.cache, self)
            if fact is not None:
                _require(StartupArtifactOwner.seal_cache_observation(self) is self._cache_fact)
        if s.runtime is not None and fact is not None:
            _require(type(fact) is tuple and len(fact) == 5
                     and type(fact[4]) is _LinkTargetObservation)
            link_fact = fact[4]
            _require(link_fact.owner is self and link_fact.scope is s
                     and link_fact.source is s.runtime
                     and s.runtime.before[0] is link_fact.before
                     and s.runtime.after[0] is link_fact.after
                     and link_fact.count is fact[3] is self._count_cell)
            _require(len(s.runtime.reads) == 2 * len(s.runtime.link.hops))
            _link_reads_current(s.runtime, link_fact.before)
            _link_reads_current(s.runtime, link_fact.after)
        _require(self._scope is s and self._origin is s and self._cell is cell
                 and s.activation._scope is s.activation_scope
                 and s.activation._artifact_owner is self
                 and self._root_cell is root_cell and s.activation._artifact_cell is root_cell
                 and self._failed is False
                 and self._unknown is False and self._attempt_cell is attempt
                 and self._fact_cell is fact and self._count_cell is held_count
                 and s.activation._artifact_attempt_cell is attempt
                 and s.activation._artifact_fact_cell is fact)
        return s

    def _open(self, name, parent, directory, native_registration=None):
        s = _native_walk_scope(self, native_registration)
        root_cell, owner_cell = self._root_cell, self._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(self, s, owner_cell, root_cell,
                                  native_registration, registry)
        _native_relative_arguments(s, name, parent)
        if s.native_files is not None:
            _require(type(directory) is bool)
        row = _Descriptor()
        s.records.append(row)  # original descriptor allocation before open
        fd = None
        row.attempted = True
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        try:
            _native_registration_tail(self, s, owner_cell, root_cell,
                                      native_registration, registry)
            fd = os.open(name, flags, dir_fd=parent)
            _require(type(fd) is int and fd >= 0)
            row.fd = fd
            _require(_native_walk_scope(self, native_registration) is s)
            _native_registration_tail(self, s, owner_cell, root_cell,
                                      native_registration, registry)
            return row, fd
        except BaseException:
            row.unknown = self._unknown = True
            if type(fd) is int and row.fd is fd and row.close_attempted is False:
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = self._unknown = True
            raise

    def _close(self, row, fd, s, root_cell):
        # Cleanup may run after a failed guard, but only on the original context.
        _require(type(s) is _Scope and type(s.context) is tuple and len(s.context) == 3
                 and all(type(v) is int for v in s.context))
        actual = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(
            all(type(v) is int for v in actual)
            and actual == s.context
            and type(row) is _Descriptor
            and row.fd is fd
            and type(fd) is int
            and row.close_attempted is False
            and type(s.records) is list
            and any(original is row for original in s.records)
            and type(root_cell) is tuple
            and len(root_cell) == (4 if _configuration(self) else 3)
            and root_cell[0] is s.activation
            and root_cell[1] is self
            and root_cell[2] is s
            and self._root_cell is root_cell
            and _root(self, s.activation) is root_cell
            and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope
        )
        row.close_attempted = True
        try:
            os.close(fd)
            row.closed = True
            _require(self._root_cell is root_cell and _root(self, s.activation) is root_cell
                     and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope)
        except BaseException:
            row.unknown = self._unknown = True
            raise

    def _read(self, fd, count, s):
        _require(type(s) is _Scope)
        _native_descriptor_argument(s, fd)
        if type(self) is StartupArtifactOwner:
            _require(self._ready is False and self._attempt_cell is not None)
        _require(_owner_guard(self) is s and type(count) is int
                 and 0 < count <= 65536 and type(self._bytes_read) is int)
        before, cell = self._bytes_read, self._count_cell
        _require(type(cell) is tuple and len(cell) == 3 and cell[0] is self
                 and cell[1] is s and type(cell[2]) is int and cell[2] == before)
        root, owner_cell = self._root_cell, self._cell
        effect = None
        read_index = None
        if s.reads is not None:
            _require(type(s.reads) is list)
            read_index = len(s.reads)
            effect = _ReadEffect(cell)
            s.reads.append(effect)  # original allocation before read effects
        source_read = source_return = None
        if s.source_digest is not None:
            from . import presentation_source_digest as source_digest
            _require(type(s.reads) is list and len(s.reads) <= 65536)
            source_read = source_digest.retain_read(s.source_digest, self, s, effect, read_index)
        self._reading = True
        data = None
        try:
            data = os.read(fd, count)
            _require(type(data) is bytes)
            runtime = s.runtime
            same = (self._scope is s and self._origin is s and self._bytes_read is before
                    and self._count_cell is cell and self._reading is True
                    and self._root_cell is root and self._cell is owner_cell
                    and (runtime is None or runtime.count[0] is cell))
            after = before + len(data)  # actual count before any post-read check
            after_cell = (self, s, after)
            if effect is not None:
                effect.after, effect.returned = after_cell, True
            if same:
                self._bytes_read = after
                self._count_cell = after_cell
            if runtime is not None and same:
                runtime.count[0] = after_cell
            if source_read is not None:
                source_return = source_digest.observed_read(source_read, after_cell, len(data))
            self._reading = False
            _require(same and (effect is None or (len(s.reads) == read_index + 1
                      and s.reads[read_index] is effect))
                     and len(data) <= count and _owner_guard(self) is s
                     and self._bytes_read is after and self._count_cell is after_cell
                     and (source_read is None or
                          (source_read.result[0] is source_return
                           and source_read.root.reads[-1] is source_read)))
            return data
        except BaseException:
            self._unknown = True
            if effect is not None:
                effect.unknown = True
            raise
        finally:
            data = None

    def _stat(self, name, parent, s):
        _require(_owner_guard(self) is s)
        _native_relative_arguments(s, name, parent)
        value = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _require(type(value) is os.stat_result and _owner_guard(self) is s)
        return value

    def _fstat(self, fd, s):
        _require(_owner_guard(self) is s)
        _native_descriptor_argument(s, fd)
        value = os.fstat(fd)
        _require(type(value) is os.stat_result and _owner_guard(self) is s)
        return value

    def _readlink(self, name, parent, hop, phase, index, before_state, start,
                  native_registration=None):
        s = _native_walk_scope(self, native_registration)
        runtime = s.runtime
        _require(type(runtime) is _RuntimeSource and self._ready is False
                 and self._attempt_cell is not None and type(name) is bytes
                 and type(parent) is int and parent >= 0
                 and type(phase) is int and phase in (0, 1)
                 and type(index) is int and 0 <= index < len(runtime.link.hops)
                 and runtime.link.hops[index] is hop
                 and name == os.fsencode(hop.path.rsplit("/", 1)[1])
                 and self._count_cell is start and runtime.count[0] is start
                 and ((phase == 0 and runtime.before[0] is None)
                      or (phase == 1 and runtime.before[0] is before_state))
                 and runtime.after[0] is None)
        position = phase * len(runtime.link.hops) + index
        _require(len(runtime.reads) == position and type(start) is tuple
                 and len(start) == 3 and start[0] is self and start[1] is s
                 and type(start[2]) is int and self._bytes_read is start[2])
        root, owner_cell = self._root_cell, self._cell
        native_registry = (None if native_registration is None
                           else native_registration.lineage.ledger.scopes)
        record = _LinkRead(hop, phase, position, start)
        runtime.reads.append(record)  # owned attempt before the syscall
        record.attempted = self._reading = True
        try:
            data = os.readlink(name, dir_fd=parent)  # bytes input => bytes output
            _require(type(data) is bytes)
            after = start[2] + len(data)  # actual result before postchecks, including refusals
            counted = (self, s, after)
            record.returned = True
            record.data, record.after = data, counted
            same = (self._reading is True and self._scope is s and self._origin is s
                    and self._root_cell is root and s.activation._artifact_cell is root
                    and self._cell is owner_cell and self._count_cell is start
                    and self._bytes_read is start[2] and runtime.count[0] is start)
            if same:
                self._bytes_read, self._count_cell = after, counted
                runtime.count[0] = counted
            self._reading = False
            _require(same and len(data) < runtime.bound and data == hop.target
                     and after <= _MAX_TOTAL and _native_walk_scope(self, native_registration) is s
                     and len(runtime.reads) == position + 1
                     and runtime.reads[position] is record
                     and runtime.count[0] is counted and self._count_cell is counted
                     and self._bytes_read is after
                     and ((phase == 0 and runtime.before[0] is None)
                          or (phase == 1 and runtime.before[0] is before_state)))
            observed = _ReadlinkObservation(record, start, counted, data)
            _native_registration_tail(self, s, owner_cell, root,
                                      native_registration, native_registry)
            return observed
        except BaseException:
            record.unknown = self._unknown = True
            raise
        finally:
            self._reading = False

    def _link_path(self, path, hop, phase, index, before_state, start, observe=True,
                   native_registration=None):
        s = _native_walk_scope(self, native_registration)
        runtime = s.runtime
        _require(type(runtime) is _RuntimeSource and self._count_cell is start
                 and ((hop is None and path is runtime.link.target.path)
                      or (hop is not None and runtime.link.hops[index] is hop
                          and path is hop.path)))
        root, owner_cell = self._root_cell, self._cell
        native_registry = (None if native_registration is None
                           else native_registration.lineage.ledger.scopes)
        held, parents = [], []
        result = observation = None
        progress = start
        failed = False
        try:
            parent = None
            for name in ("/", *path[1:].split("/")[:-1]):
                row, fd = StartupArtifactOwner._open(self, name, parent, True, native_registration)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(self, fd, s)
                mode = stat.S_IMODE(info.st_mode)
                _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                parents.append((name, parent, fd, _identity(info, True)))
                parent = fd
            name = path.rsplit("/", 1)[1]
            leaf = StartupArtifactOwner._stat(self, name, parent, s)
            identity = _identity(leaf)
            _require(self._count_cell is progress and runtime.count[0] is progress)
            if hop is None:
                _require(stat.S_ISREG(leaf.st_mode) and leaf.st_nlink == 1
                         and leaf.st_size == runtime.link.target.size
                         and leaf.st_uid == runtime.link.uid
                         and stat.S_IMODE(leaf.st_mode) == runtime.link.mode)
            else:
                _require(stat.S_ISLNK(leaf.st_mode) and leaf.st_nlink == 1
                         and leaf.st_uid in (0, s.context[1])
                         and not leaf.st_mode & (stat.S_ISUID | stat.S_ISGID)
                         and leaf.st_size == len(hop.target))
                if observe:
                    observation = StartupArtifactOwner._readlink(
                        self, os.fsencode(name), parent, hop, phase, index, before_state, progress,
                        native_registration,
                    )
                    progress = observation.after
            _require(_identity(StartupArtifactOwner._stat(self, name, parent, s)) == identity)
            for item, ancestor, fd, signature in parents:
                _require(_identity(StartupArtifactOwner._fstat(self, fd, s), True) == signature
                         and _identity(StartupArtifactOwner._stat(self, item, ancestor, s), True)
                         == signature)
            _require(_native_walk_scope(self, native_registration) is s
                     and self._count_cell is progress)
            result = identity, tuple((name, signature) for name, _, _, signature in parents)
        except BaseException:
            failed = True
        finally:
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root)
                except BaseException:
                    row.unknown = self._unknown = True
                    failed = True
        if failed:
            raise ArtifactObservationError(self) from None
        _require(_native_walk_scope(self, native_registration) is s and self._count_cell is progress
                 and runtime.count[0] is progress)
        _native_registration_tail(self, s, owner_cell, root,
                                  native_registration, native_registry)
        return result, observation, progress

    def _link_snapshot(self, phase, before_state, native_registration=None):
        s = _native_walk_scope(self, native_registration)
        root, owner_cell = self._root_cell, self._cell
        native_registry = (None if native_registration is None
                           else native_registration.lineage.ledger.scopes)
        runtime = s.runtime
        progress = self._count_cell
        links, reads = [], []
        for index, hop in enumerate(runtime.link.hops):
            metadata, observation, progress = StartupArtifactOwner._link_path(
                self, hop.path, hop, phase, index, before_state, progress,
                native_registration=native_registration,
            )
            links.append((hop, metadata))
            reads.append(observation)
            if before_state is not None:
                _require(runtime.before[0] is before_state)
        target, _, progress = StartupArtifactOwner._link_path(
            self, runtime.link.target.path, None, phase, 0, before_state, progress,
            native_registration=native_registration,
        )
        snapshot = _LinkSnapshot(runtime, phase, tuple(links), target, tuple(reads), progress)
        _link_reads_current(runtime, snapshot)
        _native_registration_tail(self, s, owner_cell, root,
                                  native_registration, native_registry)
        return snapshot

    def seal_link_observation(self, expected):
        """Callback-free original link/read/count joins before entry publication."""
        _require(type(self) is StartupArtifactOwner and self._fact_cell is expected
                 and type(expected) is tuple and len(expected) == 5
                 and self._origin is expected[1] and self._scope is expected[1])
        runtime = self._origin.runtime
        _runtime_seal(runtime, self)
        fact = expected[4]
        _require(len(runtime.reads) == 2 * len(runtime.link.hops))
        _require(type(fact) is _LinkTargetObservation and fact.owner is self
                 and fact.scope is self._origin and fact.source is runtime
                 and runtime.before[0] is fact.before and runtime.after[0] is fact.after
                 and fact.count is expected[3] is self._count_cell)
        _link_reads_current(runtime, fact.before)
        _link_reads_current(runtime, fact.after)
        return fact

    def recheck_link_metadata(self):
        _require(type(self) is StartupArtifactOwner and type(self._origin) is _Scope)
        root, owner_cell, held_fact = self._root_cell, self._cell, self._fact_cell
        native_registration = _capture_native_scope(self._origin, owner_cell, root)
        native_registry = (None if native_registration is None
                           else native_registration.lineage.ledger.scopes)
        s = _native_walk_scope(self, native_registration)
        _require(self._ready is True and self._fact_cell is held_fact
                 and type(self._fact_cell) is tuple
                 and len(self._fact_cell) == 5)
        fact = self._fact_cell[4]
        runtime = s.runtime
        progress = self._count_cell
        for index, (hop, previous) in enumerate(fact.after.links):
            metadata, _, progress = StartupArtifactOwner._link_path(
                self, hop.path, hop, 1, index, fact.before, progress, False, native_registration,
            )
            _require(metadata == previous)
        metadata, _, progress = StartupArtifactOwner._link_path(
            self, runtime.link.target.path, None, 1, 0, fact.before, progress, False,
            native_registration,
        )
        _require(metadata == fact.after.target
                 and _native_walk_scope(self, native_registration) is s
                 and self._fact_cell[4] is fact and self._count_cell is fact.count)
        _require(StartupArtifactOwner.seal_link_observation(self, held_fact) is fact)
        _native_registration_tail(self, s, owner_cell, root,
                                  native_registration, native_registry)
        return fact

    def seal_cache_observation(self):
        from .presentation_startup_cache import seal
        _require(type(self) is StartupArtifactOwner)
        fact = self._cache_fact
        _require(type(fact) is tuple and len(fact) == 6
                 and fact[0] is self and fact[1] is self._origin is self._scope
                 and fact[2] is self._origin.cache and fact[5] is self._count_cell)
        _require(seal(fact[2], self, fact[3], fact[4]) is fact[2])
        return fact

    def _file(self, expected, native_registration=None):
        s = _native_walk_scope(self, native_registration)
        native_walk = None
        if native_registration is not None:
            from .presentation_gateway_package import GatewayPackageOwner, _Manifest

            _require(type(expected) is ExpectedArtifact)
            declared = s.expected
            if type(self) is GatewayPackageOwner:
                _require(type(declared) is _Manifest)
                declared = declared.files
            _require(type(declared) is tuple and 0 < len(declared) <= _MAX_FILES
                     and any(original is expected for original in declared))
            _expected((expected,))  # exact primitive path/size/hash checks before effects
            _require(_native_walk_scope(self, native_registration) is s)
            native_walk = _begin_native_declared_walk(self, native_registration, expected)
        anchor = type(expected) is OperatorApprovalPath
        declared_reader = None
        if anchor:
            from hmp_startup.gateway_approval import GatewayApprovalOwner
            _require(type(self) is GatewayApprovalOwner and type(s.expected) is tuple
                     and len(s.expected) == 1 and s.expected[0] is expected)
        else:
            _require(type(expected) is ExpectedArtifact)
            if not _configuration(self) and type(self) is not StartupArtifactOwner:
                from .presentation_gateway_package import GatewayPackageOwner
                if type(self) is not GatewayPackageOwner:
                    from hmp_startup.runtime_reader import RuntimeSourceReadOwner
                    if type(self) is RuntimeSourceReadOwner:
                        _require(expected is s.expected[0] and self._started is True
                                 and self._ready is False)
                    else:
                        from hmp_startup.cache_reader import DeclaredCacheReadOwner
                        if type(self) is DeclaredCacheReadOwner:
                            _require(expected is s.expected[0] and self._started is True
                                     and self._ready is False)
                            declared_reader = DeclaredCacheReadOwner
        root_cell, owner_cell = self._root_cell, self._cell
        native_registry = (None if native_registration is None
                           else native_registration.lineage.ledger.scopes)
        held, directories, read_effects = [], [], []
        source_root = source_effect = source_buffer = None
        source_hash = b""
        source_mtime = None
        source_observations = []
        progress = self._count_cell if s.runtime is not None else None
        data = digest = None
        result = None
        failed = False
        try:
            if s.source_digest is not None:
                from . import presentation_source_digest as source_digest
                source_root = source_digest.begin(self, s, expected)
                source_effect = None if source_root is None else source_root.effect
                source_buffer = None if source_root is None else source_root.buffer
            parent = None
            for name in ("/", *expected.path[1:].split("/")[:-1]):
                row, fd = StartupArtifactOwner._open(self, name, parent, True, native_registration)
                held.append((row, fd))
                info = StartupArtifactOwner._fstat(self, fd, s)
                signature = _identity(info, True)
                mode = stat.S_IMODE(info.st_mode)
                _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                directories.append((name, parent, fd, signature))
                parent = fd
            if _configuration(self):
                _require(info.st_uid == s.context[1] and stat.S_IMODE(info.st_mode) == 0o700)
            name = expected.path.rsplit("/", 1)[1]
            before = StartupArtifactOwner._stat(self, name, parent, s)
            original = _identity(before)
            _require(stat.S_ISREG(before.st_mode) and before.st_uid in (0, s.context[1])
                     and before.st_nlink == 1
                     and (0 < before.st_size <= 4096 if anchor else before.st_size == expected.size)
                     and not before.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
            if _configuration(self):
                _require(before.st_uid == s.context[1] and stat.S_IMODE(before.st_mode) == 0o600)
            if source_effect is not None:
                timestamp = before.st_mtime
                _require(type(timestamp) in (int, float) and -2 ** 64 < timestamp < 2 ** 64)
                source_mtime = int(timestamp)  # exact CPython path_stats conversion, not ns floor
            row, fd = StartupArtifactOwner._open(self, name, parent, False, native_registration)
            held.append((row, fd))
            _require(_identity(StartupArtifactOwner._fstat(self, fd, s)) == original)
            digest = hashlib.sha256()
            header = b""
            capture_header = (not anchor and not _configuration(self)
                              and expected.path.endswith(".pyc"))
            remaining = before.st_size if anchor else expected.size
            while remaining:
                _require(_native_walk_scope(self, native_registration) is s)
                _require(progress is None or self._count_cell is progress)
                data = (StartupArtifactOwner._read(self, fd, min(remaining, 65536), s)
                        if declared_reader is None else
                        declared_reader._read(self, fd, min(remaining, 65536), s))
                if source_root is not None:
                    source_observations.append(source_digest.capture(source_root))
                if anchor:
                    read_effects.append(s.reads[-1])
                if progress is not None:
                    progress = self._count_cell
                _require(0 < len(data) <= remaining)
                remaining -= len(data)
                _require(_native_walk_scope(self, native_registration) is s)
                _append_configuration(self, data)
                digest.update(data)
                if source_effect is not None:
                    source_digest.append(source_root, source_buffer, data, source_observations)
                if capture_header and len(header) < 16:
                    header += data[:16 - len(header)]
                data = None
                _require(_native_walk_scope(self, native_registration) is s)
            _require(progress is None or self._count_cell is progress)
            data = (StartupArtifactOwner._read(self, fd, 1, s) if declared_reader is None
                    else declared_reader._read(self, fd, 1, s))
            if source_root is not None:
                source_observations.append(source_digest.capture(source_root))
            if anchor:
                read_effects.append(s.reads[-1])
            count_cell, counted = self._count_cell, self._bytes_read
            _require(data == b"" and _identity(StartupArtifactOwner._fstat(self, fd, s)) == original
                     and _identity(StartupArtifactOwner._stat(self, name, parent, s)) == original)
            _require(_native_walk_scope(self, native_registration) is s)
            actual_hash = digest.hexdigest()
            _require(_native_walk_scope(self, native_registration) is s
                     and type(actual_hash) is str
                     and (anchor or actual_hash == expected.sha256))
            if source_effect is not None:
                source_hash = source_digest.finish(source_root, source_buffer, count_cell,
                                                   source_observations)
            for name, parent, directory, signature in directories:
                _require(
                    _identity(StartupArtifactOwner._fstat(self, directory, s), True) == signature
                    and _identity(StartupArtifactOwner._stat(self, name, parent, s), True)
                    == signature
                )
            _require(_native_walk_scope(self, native_registration) is s)
            result = expected
            if anchor:
                result = _OperatorFileReceipt(self, s, expected, original, actual_hash, count_cell,
                                              tuple(row for row, _ in held), tuple(read_effects))
            elif not _configuration(self):
                result = _HashedArtifact(self, s, expected, original, actual_hash, header,
                                         source_hash, source_root, source_mtime)
        except BaseException:
            if source_effect is not None and source_effect.attempted is True:
                source_effect.unknown = True
            failed = True
        finally:
            if source_effect is not None:
                try:
                    source_digest.clear(source_root, source_buffer)
                except BaseException:
                    source_effect.unknown = self._unknown = True
                    failed = True
            data = digest = header = None
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    row.unknown = self._unknown = True
                    failed = True
        if failed:
            raise ArtifactObservationError(self) from None
        _require(_native_walk_scope(self, native_registration) is s
                 and self._count_cell is count_cell and self._bytes_read is counted)
        if source_effect is not None:
            source_fact = source_digest.fact(source_root, self, s, expected,
                                             source_hash, count_cell, source_observations,
                                             source_mtime)
            result = result._replace(source_digest=source_fact)
            _require(source_effect.cleared is True and source_effect.unknown is False
                     and source_effect.result is source_hash
                     and source_effect.buffer is source_buffer and len(source_buffer) == 0)
        _require(_native_walk_scope(self, native_registration) is s
                 and self._count_cell is count_cell and self._bytes_read is counted)
        if source_effect is not None:
            _require(source_digest.seal_fact(source_fact) is source_fact
                     and source_fact.root is source_root and source_fact.source_hash is source_hash
                     and source_fact.count is count_cell and type(result) is _HashedArtifact
                     and result.source_digest is source_fact
                     and source_effect.buffer is source_buffer
                     and source_effect.cleared is True and source_effect.unknown is False
                     and source_effect.result is source_hash and source_effect.after is count_cell)
        _native_registration_tail(self, s, owner_cell, root_cell,
                                  native_registration, native_registry)
        _require(self._count_cell is count_cell and self._bytes_read is counted)
        if native_walk is not None:
            _finish_native_declared_walk(self, native_registration, native_walk)
        return result
