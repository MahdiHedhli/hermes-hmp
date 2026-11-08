"""Owned bounded startup artifact observations, not runtime admission.

Only the future fixed startup/configuration loader supplies external expectations.
No route imports this module. Matching selected files is not complete reachable
inventory/loader qualification or permission to load keys or publish images.
"""
from __future__ import annotations

import builtins
import hashlib
import os
import stat
import sys
import threading
from dataclasses import dataclass
from types import BuiltinFunctionType, CodeType, FunctionType, MethodDescriptorType, ModuleType
from typing import NamedTuple

from .presentation_gateway_activation import GatewayActivationOwner

_MAX_FILES = 1024
_MAX_FILE = 128 * 1024 * 1024
_MAX_TOTAL = 2 * 1024 * 1024 * 1024


class ArtifactObservationError(Exception):
    def __init__(self, owner=None):
        super().__init__("BI1_STARTUP_ARTIFACTS_REFUSED")
        self.failed_owner = owner


class _NativeActorMismatchError(ArtifactObservationError):
    """Actual original actor differs; no reservation or file call is consumed."""


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


class _NativeReadFileStep(NamedTuple):
    """Original declared-file read cursor; not a new or renewable allowance."""
    owner: object
    scope: object
    registration: object
    walk: object
    expected: ExpectedArtifact
    descriptor: object
    parents: tuple
    digest: object
    hash_kind: type
    hash_update: object
    buffer: object
    buffer_aliases: tuple
    source: object
    observations: object
    code: object
    material: object
    material_code: object
    material_module: object
    owner_type: type
    progress: list
    eof: list

    def __repr__(self):
        return "<NativeReadFileStep unbound original-cursor DATA redacted>"


class _NativeReadConsumer(NamedTuple):
    """Original fixed-file read step DATA; construction is not consumption.

    The experimental runtime-source consumer joins original owner/step/progress
    allocations. Construction or a code object alone never acknowledges bytes.
    """
    owner: object
    scope: object
    registration: object
    walk: object
    file_step: _NativeReadFileStep
    expected: ExpectedArtifact
    descriptor: object
    ordinal: int
    requested: int
    before_count: tuple
    remaining: int
    digest: object
    buffer: object
    source: object
    observations: object
    effect: object
    code: object
    material: object
    material_code: object
    material_module: object
    owner_type: type
    result: list
    progress: list
    operation: list
    committed: list
    consumption: list

    def __repr__(self):
        return "<NativeReadConsumer unbound original-step DATA redacted>"


class _NativeFileResultClaim(NamedTuple):
    """Preallocated original result/consumer DATA; not an ACK or work grant.

    The pending-operation integration must retain the raw allocation until this
    exact fixed consumer acknowledges it, then retire payload references without
    retiring original unknown/debit history. Only runtime-source reads are wired
    experimentally; remaining operation consumers are unfinished.
    """
    attempt: list
    consumer: object
    unset: object
    raw: list
    category: list
    length: list
    acknowledged: list
    envelope: list

    def __repr__(self):
        return "<NativeFileResultClaim unbound DATA redacted>"


class _NativeFileOperation(NamedTuple):
    """Original fixed read/stat/fstat/readlink intent; no generic dispatcher."""
    owner: object
    scope: object
    registration: object
    ledger: object
    native: object
    context: tuple
    operation: int
    callee: object
    arguments: tuple
    descriptor: object
    consumer: object
    index: int
    budget: tuple
    ended: list
    state: list
    result: _NativeFileResultClaim

    def __repr__(self):
        return "<NativeFileOperation unbound DATA redacted>"


class _NativeReadResult(NamedTuple):
    """Private original pending read result; never a bytes-compatible proxy."""
    operation: _NativeFileOperation
    result: _NativeFileResultClaim
    consumer: _NativeReadConsumer
    raw: bytes
    after_count: tuple
    step: _NativeReadFileStep
    effect: object
    effect_index: int
    source_read: object
    source_read_kind: type
    source_return: object
    commit_cell: list
    consumption_cell: list
    effect_cell: list
    raw_cell: list
    length_cell: list
    category_cell: list
    ack_cell: list
    consumer_result_cell: list
    consumer_operation_cell: list
    consumer_progress_cell: list
    step_progress_cell: list
    attempt_cell: list
    envelope_cell: list
    cache_return: object = None

    def __repr__(self):
        return "<NativeReadResult pending unbound DATA redacted>"


class _NativeRuntimeReadCommit(NamedTuple):
    """Fixed consumer's raw-free progress evidence; not caller success DATA."""
    operation: _NativeFileOperation
    result: _NativeFileResultClaim
    consumer: _NativeReadConsumer
    step: _NativeReadFileStep
    count: tuple
    ordinal: int
    remaining: int
    eof: bool
    consumption_token: object
    source_observation: tuple
    source_consumed: int

    def __repr__(self):
        return "<NativeRuntimeReadCommit unqualified progress redacted>"


class _NativeCacheReadReturn(NamedTuple):
    """Ephemeral actual cache-journal return; never retain prefix heads after ACK."""
    heads: tuple
    result_heads: tuple
    attempt: tuple
    result: tuple
    index: int

    def __repr__(self):
        return "<NativeCacheReadReturn transient unbound DATA redacted>"


class _NativeFilePreparation(NamedTuple):
    """Original preparation latch retained on failure, not a file-effect grant."""
    owner: object
    registration: object
    ledger: object
    counts: list
    before: tuple
    index: int
    allocation: list

    def __repr__(self):
        return "<NativeFilePreparation original transition DATA redacted>"


class _NativeCloseAllocation(NamedTuple):
    """Internal preallocated cleanup DATA; construction alone grants nothing.

    The coupled dispatcher must register this exact allocation before open and
    retain its original reference independently of mutable descriptor mirrors.
    The isolated candidate dispatcher consumes these cells; qualification remains open.
    """
    owner: object
    scope: object
    registration: object
    ledger: object
    phase: object
    context: tuple
    close_call: object
    actor_calls: tuple
    actor_modules: tuple
    open_slot: list
    reservation: object
    state: list
    unset: object
    raw: list
    result: list

    def __repr__(self):
        return "<NativeCloseAllocation unbound DATA redacted>"


class _NativeOpenAllocation(NamedTuple):
    """Original open intent/raw-return storage, not admission or a receipt."""
    owner: object
    scope: object
    registration: object
    ledger: object
    parent: object
    arguments: tuple
    native: object
    context: tuple
    index: int
    pending: object
    raw: list
    result: list
    refused: list
    close: _NativeCloseAllocation

    def __repr__(self):
        return "<NativeOpenAllocation unbound DATA redacted>"


class _NativeOpenedDescriptor(NamedTuple):
    """Immutable actual-result wrapper; requires independent original-claim joins.

    This type intentionally supplies no writable status properties. Consumers
    must use the coupled proof validator, not infer closed credit from shape.
    The coupled validator and consumers remain subject to qualification.
    """
    allocation: _NativeOpenAllocation
    fd: int
    close: _NativeCloseAllocation

    @property
    def attempted(self):
        return True

    @property
    def close_attempted(self):
        return self.close.state[0]

    @property
    def closed(self):
        # Diagnostic mirror only; original-ledger authority still requires the
        # coupled validator. Raw syscall return alone is not a completed ACK.
        allocation, close = self.allocation, self.close
        if (type(allocation) is not _NativeOpenAllocation
                or type(close) is not _NativeCloseAllocation or type(self.fd) is not int):
            return False
        state, raw, result, refused = close.state, close.raw, close.result, allocation.refused
        if not (close is allocation.close
                and type(state) is list and len(state) == 2
                and state[0] is True and state[1] is False
                and type(raw) is list and len(raw) == 1 and raw[0] is None
                and type(result) is list and len(result) == 1
                and type(refused) is list and len(refused) == 1 and refused[0] is False):
            return False
        receipt = result[0]
        return (type(receipt) is tuple and len(receipt) == 3
                and receipt[0] is close and receipt[1] is self.fd and receipt[2] is None)

    @property
    def unknown(self):
        return self.allocation.refused[0] or self.close.state[1]

    def __repr__(self):
        return "<NativeOpenedDescriptor actual-result DATA redacted>"


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
    material_origin: object = None

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


class _NativeMetadataSnapshot(NamedTuple):
    """Primitive stat DATA only; never a consumer ACK or operation allowance."""
    identity: tuple
    mtime: int | float

    def __repr__(self):
        return '<NativeMetadataSnapshot unqualified DATA redacted>'


def _native_metadata_snapshot(owner, registration, native, value):
    """Snapshot an actual retained stat result under original native machinery.

    Unwired preparation: the producer must retain its actual native return first;
    the later fixed consumer must bind this DATA to its original pending claim.
    """
    _require(native is not None and type(registration) is _NativeScopeRegistration)
    _native_work_origin_tail(owner, registration, native)
    _require(type(value) is native.result_type)
    identity = (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
                value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    mtime = value.st_mtime
    _require(all(type(part) is int for part in identity)
             and type(mtime) in (int, float))
    snapshot = _NativeMetadataSnapshot(identity, mtime)
    _native_work_origin_tail(owner, registration, native)
    _require(type(value) is native.result_type)
    return snapshot


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
    read_step: list
    metadata_slot: object = None

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
    native_ledger: object
    native_origin: object
    type_pins: tuple
    entry_module: ModuleType
    native_phase: object
    phase_type: type

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
    phase = lineage.ledger.phase
    _require(phase is record.native_phase and type(record.phase_type) is type
             and type(phase) is record.phase_type
             and type(phase.current) is list and len(phase.current) == 1
             and phase.current[0] is phase.idle
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is None
             and type(lineage.ledger.inflight) is list and len(lineage.ledger.inflight) == 1
             and lineage.ledger.inflight[0] is None
             and type(lineage.ledger.failed) is list and len(lineage.ledger.failed) == 1
             and lineage.ledger.failed[0] is False)
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
                                     ordinal, ("/", *expected.path[1:].split("/")),
                                     [0], [None], [None])
                  for ordinal, expected in enumerate(declaration))
    progress = [0]
    ledger, native_origin = lineage.ledger, lineage.native
    native_phase = ledger.phase
    phase_type = type(native_phase)
    type_pins = (type(lineage), type(ledger), type(native_origin))
    _require(type(sys) is ModuleType)
    modules = vars(sys).get('modules')
    _require(type(modules) is dict)
    entry_module = modules.get('hmp_startup.gateway_entry')
    _require(type(entry_module) is ModuleType)
    entry_names = vars(entry_module)
    _require(entry_names.get('GatewayEntryOwner') is GatewayEntryOwner
             and entry_names.get('_NativeFileLineage') is type_pins[0]
             and entry_names.get('_NativeFileLedger') is type_pins[1]
             and entry_names.get('_NativeIOOrigin') is type_pins[2])
    record = _NativeScopeRegistration(lineage, owner, s, cell, root, s.context, index,
                                      walks, progress, ledger, native_origin,
                                      type_pins, entry_module, native_phase, phase_type)
    _require(type(record) is _NativeScopeRegistration and record.lineage is lineage
             and record.owner is owner and record.scope is s
             and record.cell is cell and record.root is root
             and record.context is s.context and record.index is index
             and record.native_ledger is ledger and record.native_origin is native_origin
             and record.type_pins is type_pins and record.entry_module is entry_module
             and record.native_phase is native_phase and record.phase_type is phase_type
             and ledger.phase is native_phase and type(native_phase) is phase_type
             and lineage.ledger is ledger and lineage.native is native_origin
             and modules.get('hmp_startup.gateway_entry') is entry_module
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
    _native_work_registration_tail(owner, record)
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


class _NativeDeclaredMetadataPlan(NamedTuple):
    """Original per-file site allocation; resource binding and ACK still required."""
    owner: object
    scope: _Scope
    walk: _NativeDeclaredWalk
    expected: ExpectedArtifact
    definitions: tuple
    progress: list

    def __repr__(self):
        return '<NativeDeclaredMetadataPlan unqualified site DATA redacted>'


def _prepare_declared_metadata_plan(owner, registration, walk):
    """Allocate fixed file-site order once, before this walk's native effects."""
    _require(type(registration) is _NativeScopeRegistration
             and type(walk) is _NativeDeclaredWalk and walk.owner is owner
             and type(walk.scope) is _Scope and walk.scope is registration.scope
             and type(walk.declaration) is tuple and type(walk.index) is int
             and 0 <= walk.index < len(walk.declaration)
             and type(walk.expected) is ExpectedArtifact
             and type(walk.expected.path) is str
             and walk.expected is walk.declaration[walk.index]
             and type(walk.components) is tuple and 1 < len(walk.components) <= 4096
             and all(type(part) is str for part in walk.components)
             and type(walk.metadata_slot) is list and len(walk.metadata_slot) == 1
             and walk.metadata_slot[0] is None)
    # Operation indices match the captured native tuple. Roles are fixed DATA,
    # never dispatch selectors. Actual opened-parent/leaf joins are not minted here.
    definitions = tuple((4, 'directory', index)
                        for index in range(len(walk.components) - 1))
    leaf = len(walk.components) - 1
    definitions += ((3, 'leaf_before', leaf), (4, 'leaf_opened', leaf),
                    (4, 'leaf_after_read', leaf), (3, 'leaf_after_read', leaf))
    # The actual walker rechecks every held ancestor after hashing, regardless
    # of whether source hashing is active. It does not recheck the leaf again.
    definitions += tuple(site for index in range(len(walk.components) - 1)
                         for site in ((4, 'directory_after_hash', index),
                                      (3, 'directory_after_hash', index)))
    return _NativeDeclaredMetadataPlan(owner, walk.scope, walk, walk.expected,
                                       definitions, [0, None])


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
    metadata = _prepare_declared_metadata_plan(owner, registration, plan)
    _require(plan.metadata_slot[0] is None and plan.state is state and state[0] == 0)
    plan.metadata_slot[0] = metadata
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


def _native_work_registration_tail(owner, registration):
    """Original allocation joins before any nested lineage or native access."""
    _require(type(registration) is _NativeScopeRegistration and registration.owner is owner
             and type(registration.scope) is _Scope)
    s, cell, root = registration.scope, registration.cell, registration.root
    _require(_capture_native_scope(s, cell, root) is registration
             and type(s.activation) is GatewayActivationOwner
             and GatewayActivationOwner._retained_scope(s.activation) is s.activation_scope)
    activation_names = vars(s.activation)
    _require(any(activation_names.get(name) is root for name in
                 ('_artifact_cell', '_package_cell', '_runtime_read_cell',
                  '_runtime_cache_probe_cell', '_cache_read_cell')))
    owner_names = vars(owner)
    _require(type(owner_names) is dict and owner_names.get('_origin') is s
             and owner_names.get('_scope') is s and owner_names.get('_cell') is cell
             and owner_names.get('_root_cell') is root
             and owner_names.get('_native_scope_registration') is registration)
    pins = registration.type_pins
    _require(type(pins) is tuple and len(pins) == 3 and all(type(pin) is type for pin in pins)
             and type(registration.lineage) is pins[0]
             and type(registration.native_ledger) is pins[1]
             and type(registration.native_origin) is pins[2])
    _require(registration.lineage.ledger is registration.native_ledger
             and registration.lineage.native is registration.native_origin
             and registration.native_ledger.phase is registration.native_phase
             and type(registration.phase_type) is type
             and type(registration.native_phase) is registration.phase_type)
    registry = registration.native_ledger.scopes
    _require(type(registry) is list and type(registration.index) is int
             and 0 <= registration.index < len(registry)
             and registry[registration.index] is registration)
    _require(type(sys) is ModuleType)
    modules = vars(sys).get('modules')
    _require(type(modules) is dict and type(registration.entry_module) is ModuleType
             and modules.get('hmp_startup.gateway_entry') is registration.entry_module)


def _capture_native_work_origin(owner, registration):
    """Original DATA for fixed callers; never select or perform an operation."""
    if registration is None:
        return None
    _native_work_registration_tail(owner, registration)
    native = registration.native_origin
    _native_work_origin_tail(owner, registration, native)
    return native


def _native_work_origin_tail(owner, registration, native):
    """Pure original namespace/value join; no runtime or effect grant."""
    if native is None:
        _require(registration is None)
        return
    _native_work_registration_tail(owner, registration)
    _require(native is registration.native_origin)
    modules = vars(sys).get('modules')
    _require(type(native.namespace) is ModuleType and native.namespace is os
             and type(native.native) is ModuleType
             and modules.get('os') is native.namespace and modules.get('posix') is native.native
             and type(builtins) is ModuleType and modules.get('builtins') is builtins
             and type(native.operations) is tuple and len(native.operations) == 6
             and type(native.flags) is tuple and len(native.flags) == 5
             and type(native.errors) is tuple and len(native.errors) == 3
             and type(native.result_type) is type)
    namespace, original = vars(native.namespace), vars(native.native)
    for index, name in enumerate(('open', 'read', 'close', 'stat', 'fstat', 'readlink')):
        function = native.operations[index]
        _require(type(function) is BuiltinFunctionType and function.__self__ is native.native
                 and type(function.__name__) is str and function.__name__ == name
                 and namespace.get(name) is function and original.get(name) is function)
    for index, name in enumerate(('O_RDONLY', 'O_NOFOLLOW', 'O_CLOEXEC',
                                  'O_NONBLOCK', 'O_DIRECTORY')):
        flag = native.flags[index]
        _require(type(flag) is int and namespace.get(name) is flag and original.get(name) is flag)
    _require(namespace.get('stat_result') is native.result_type
             and original.get('stat_result') is native.result_type)
    _require(namespace.get('error') is native.errors[0]
             and original.get('error') is native.errors[0])
    _require(type(native.thread_namespace) is ModuleType and native.thread_namespace is threading
             and type(native.thread_native) is ModuleType
             and modules.get('threading') is native.thread_namespace
             and modules.get('_thread') is native.thread_native
             and type(native.actor_calls) is tuple and len(native.actor_calls) == 3)
    for index, source, alias, name in (
            (0, native.native, native.namespace, 'getpid'),
            (1, native.native, native.namespace, 'geteuid'),
            (2, native.thread_native, native.thread_namespace, 'get_ident')):
        function = native.actor_calls[index]
        _require(type(function) is BuiltinFunctionType and function.__self__ is source
                 and type(function.__name__) is str and function.__name__ == name
                 and vars(source).get(name) is function and vars(alias).get(name) is function)
    error_names = vars(builtins)
    for index, name in enumerate(('OSError', 'FileNotFoundError', 'PermissionError')):
        _require(type(native.errors[index]) is type
                 and error_names.get(name) is native.errors[index])


def _allocate_native_file_open(owner, registration, parent, arguments, pending):
    """Preallocate original intent and one close reservation; no file operation.

    Candidate dispatch only. Admission consumes an attempt even if later
    preparation refuses; there is no release/retry path that launders that debt.
    Parent validity is rechecked at allocation; coupled dispatch must rejoin the
    same original parent again after its last callback and before the file call.
    """
    native = _capture_native_work_origin(owner, registration)
    _require(native is not None and type(arguments) is tuple and len(arguments) == 3
             and type(arguments[0]) is str and type(arguments[1]) is int
             and arguments[2] is parent
             and type(pending) is _Descriptor and pending.fd is None
             and pending.attempted is True and pending.close_attempted is False
             and pending.closed is False and pending.unknown is False)
    parent_claim = _native_parent_descriptor(registration, arguments[0], parent)
    ledger = registration.native_ledger
    _require(type(ledger.attempts) is list and type(ledger.counts) is list
             and len(ledger.counts) == 2
             and all(type(value) is int for value in ledger.counts)
             and 0 <= ledger.counts[0] <= 1048574
             and 0 <= ledger.counts[1] <= 1048574 - ledger.counts[0]
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and ledger.inflight[0] is None
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False and len(ledger.attempts) < 1048576)
    attempts, counts = ledger.attempts, ledger.counts
    used, reserved, index = counts[0], counts[1], len(attempts)
    inflight, failed, failure = ledger.inflight, ledger.failed, ledger.failure
    _require(type(failure) is list and len(failure) == 1 and failure[0] is None)
    token = ledger.preparation
    _require(type(token) is list and len(token) == 3)
    preparation = None
    actor_mismatch = False
    try:
        _require(ledger.inflight is inflight and inflight[0] is None
                 and ledger.failed is failed and failed[0] is False
                 and ledger.failure is failure and failure[0] is None
                 and ledger.preparation is token and ledger.attempts is attempts
                 and len(attempts) == index and ledger.counts is counts and len(counts) == 2
                 and counts[0] is used and counts[1] is reserved)
        inflight[0] = token
        token[0], token[1], token[2] = owner, registration, pending
        try:
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                  registration.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        preparation = _NativeFilePreparation(owner, registration, ledger, counts,
                                             (used, reserved), index, [None])
        token[2] = preparation
        open_slot, raw, result = [None], [None], [None]
        unset, reservation = object(), object()
        close = _NativeCloseAllocation(owner, registration.scope, registration, ledger,
                                       registration.native_phase, registration.context,
                                       native.operations[2],
                                       native.actor_calls, (native.native, native.thread_native),
                                       open_slot, reservation, [False, False], unset,
                                       [unset], [None])
        allocation = _NativeOpenAllocation(owner, registration.scope, registration, ledger,
                                           parent_claim, arguments, native, registration.context,
                                           index, pending, raw, result, [False], close)
        preparation.allocation[0] = allocation
        open_slot[0] = allocation
        _native_work_origin_tail(owner, registration, native)
        _require(ledger.inflight is inflight and inflight[0] is token
                 and ledger.failed is failed and failed[0] is False
                 and ledger.failure is failure and failure[0] is None
                 and ledger.attempts is attempts and len(attempts) == index
                 and ledger.counts is counts and len(counts) == 2
                 and counts[0] is used and counts[1] is reserved
                 and type(used) is int and type(reserved) is int
                 and 0 <= used <= 1048574 and 0 <= reserved <= 1048574 - used)
        attempts.append(allocation)
        counts[0] = used + 1
        counts[1] = reserved + 1
        _require(ledger.inflight is inflight and inflight[0] is token
                 and ledger.attempts is attempts and attempts[index] is allocation
                 and ledger.counts is counts and len(counts) == 2
                 and type(counts[0]) is int and counts[0] == used + 1
                 and type(counts[1]) is int and counts[1] == reserved + 1)
        return allocation
    except BaseException:
        if not actor_mismatch:
            if failure[0] is None:
                failure[0] = preparation if preparation is not None else token
            failed[0] = True
        raise
    finally:
        if ledger.inflight is inflight and inflight[0] is token:
            inflight[0] = None


def _native_file_allocation_original(allocation, original_ledger):
    """Original claim joins only: deliberately independent of current work roots."""
    _require(type(allocation) is _NativeOpenAllocation
             and allocation.ledger is original_ledger)
    registration, ledger, close = allocation.registration, allocation.ledger, allocation.close
    _require(type(registration) is _NativeScopeRegistration
             and type(registration.type_pins) is tuple and len(registration.type_pins) == 3
             and all(type(pin) is type for pin in registration.type_pins)
             and type(ledger) is registration.type_pins[1]
             and type(allocation.native) is registration.type_pins[2])
    _require(registration.owner is allocation.owner and registration.scope is allocation.scope
             and registration.native_ledger is ledger
             and registration.native_origin is allocation.native
             and allocation.context is registration.context
             and type(ledger) is registration.type_pins[1]
             and type(ledger.attempts) is list and type(allocation.index) is int
             and 0 <= allocation.index < len(ledger.attempts)
             and ledger.attempts[allocation.index] is allocation
             and type(close) is _NativeCloseAllocation
             and close.owner is allocation.owner and close.scope is allocation.scope
             and close.registration is registration and close.ledger is ledger
             and close.phase is registration.native_phase and ledger.phase is close.phase
             and close.context is allocation.context
             and close.close_call is allocation.native.operations[2]
             and close.actor_calls is allocation.native.actor_calls
             and type(close.actor_modules) is tuple and len(close.actor_modules) == 2
             and close.actor_modules[0] is allocation.native.native
             and close.actor_modules[1] is allocation.native.thread_native
             and type(close.open_slot) is list and len(close.open_slot) == 1
             and close.open_slot[0] is allocation
             and type(allocation.raw) is list and len(allocation.raw) == 1
             and type(allocation.result) is list and len(allocation.result) == 1
             and type(allocation.refused) is list and len(allocation.refused) == 1
             and type(allocation.refused[0]) is bool
             and type(close.state) is list and len(close.state) == 2
             and all(type(value) is bool for value in close.state)
             and type(close.raw) is list and len(close.raw) == 1
             and type(close.result) is list and len(close.result) == 1)
    return close


def _native_descriptor_opened(descriptor, original_ledger):
    """Internal actual-open result joins; shape alone is not external authority."""
    _require(type(descriptor) is _NativeOpenedDescriptor and type(descriptor.fd) is int
             and descriptor.fd >= 0)
    allocation = descriptor.allocation
    close = _native_file_allocation_original(allocation, original_ledger)
    _require(descriptor.close is close
             and allocation.raw[0] is descriptor.fd
             and type(allocation.result[0]) is tuple and len(allocation.result[0]) == 2
             and allocation.result[0][0] is allocation and allocation.result[0][1] is descriptor)
    return close


def _native_parent_descriptor(registration, name, parent):
    """Select only an original live parent from this fixed caller's own scope."""
    _require(type(registration) is _NativeScopeRegistration and type(name) is str
             and type(parent) in (int, type(None)))
    if parent is None:
        _require(name == "/")
        return None
    _require(parent >= 0 and type(registration.scope) is _Scope)
    records = registration.scope.records
    _require(type(records) is list and len(records) <= 1048576)
    found = None
    for descriptor in records:
        if type(descriptor) is _NativeOpenedDescriptor and descriptor.fd is parent:
            close = _native_descriptor_opened(descriptor, registration.native_ledger)
            if close.state[0] is True:
                continue  # an earlier closed descriptor may have reused this fd number
            _require(found is None and descriptor.allocation.scope is registration.scope
                     and descriptor.allocation.ledger is registration.native_ledger
                     and close.state[1] is False and close.raw[0] is close.unset
                     and close.result[0] is None)
            found = descriptor
    _require(found is not None)
    return found


def _native_descriptor_closed(descriptor, original_ledger):
    """Actual original open/result/close proof, never mutable pending-row credit."""
    close = _native_descriptor_opened(descriptor, original_ledger)
    _require(descriptor.allocation.refused[0] is False
             and close.raw[0] is None and close.state[0] is True and close.state[1] is False
             and type(close.result[0]) is tuple and len(close.result[0]) == 3
             and close.result[0][0] is close and close.result[0][1] is descriptor.fd
             and close.result[0][2] is None)
    return True


def _descriptor_closed_in_scope(row, scope):
    """Fixed consumer's held scope selects native proof versus legacy status."""
    try:
        _require(type(scope) is _Scope)
        if scope.native_files is None:
            return (type(row) is _Descriptor and row.closed is True
                    and row.close_attempted is True and row.unknown is False)
        slot = scope.native_registration_slot
        _require(type(slot) is list and len(slot) == 1
                 and type(slot[0]) is _NativeScopeRegistration)
        registration = slot[0]
        _require(registration.scope is scope and registration.lineage is scope.native_files
                 and type(registration.type_pins) is tuple and len(registration.type_pins) == 3
                 and all(type(pin) is type for pin in registration.type_pins)
                 and type(registration.lineage) is registration.type_pins[0]
                 and type(registration.native_ledger) is registration.type_pins[1]
                 and registration.lineage.ledger is registration.native_ledger
                 and type(row) is _NativeOpenedDescriptor
                 and type(row.allocation) is _NativeOpenAllocation
                 and row.allocation.scope is scope)
        return _native_descriptor_closed(row, registration.native_ledger)
    except ArtifactObservationError:
        return False


def _descriptor_refused(row):
    """Withdraw work credit only; never manufacture close success."""
    if type(row) is _NativeOpenedDescriptor:
        _require(type(row.allocation) is _NativeOpenAllocation)
        row.allocation.refused[0] = True
    else:
        _require(type(row) is _Descriptor)
        row.unknown = True


def _close_native_file_known(owner, allocation, fd, original_ledger):
    """Consume the original reserved cleanup, with no current-work-root lookup."""
    close = _native_file_allocation_original(allocation, original_ledger)
    _require(allocation.owner is owner and type(fd) is int and fd >= 0
             and allocation.raw[0] is fd and close.state[0] is False
             and close.state[1] is False and close.raw[0] is close.unset
             and close.result[0] is None)
    ledger = original_ledger
    phase = close.phase
    _require(type(phase.current) is list and len(phase.current) == 1
             and (phase.current[0] is phase.idle or phase.current[0] is phase.failed)
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is None)
    counts, inflight = ledger.counts, ledger.inflight
    failed, failure = ledger.failed, ledger.failure
    _require(type(failed) is list and len(failed) == 1 and type(failed[0]) is bool
             and type(failure) is list and len(failure) == 1)
    _require(type(counts) is list and len(counts) == 2
             and all(type(value) is int for value in counts)
             and 0 <= counts[0] < 1048576 and 0 < counts[1] <= 1048576 - counts[0]
             and type(inflight) is list and len(inflight) == 1
             and inflight[0] is None)
    used, reserved = counts
    close_call, token = close.close_call, close.reservation
    actor_mismatch = False
    try:
        inflight[0] = close
        try:
            _native_actor_context(close.actor_calls, close.actor_modules, close.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        _require(_native_file_allocation_original(allocation, original_ledger) is close
                 and allocation.raw[0] is fd and close.state[0] is False
                 and close.state[1] is False and close.raw[0] is close.unset
                 and close.reservation is token and close.close_call is close_call
                 and ledger.counts is counts and counts[0] is used and counts[1] is reserved
                 and ledger.inflight is inflight and inflight[0] is close
                 and ledger.phase is phase and phase.result[0] is None
                 and (phase.current[0] is phase.idle or phase.current[0] is phase.failed))
        used_after, reserved_after = used + 1, reserved - 1
        close.state[0] = True
        counts[0], counts[1] = used_after, reserved_after
        value = close_call(fd)
        close.raw[0] = value  # retain actual return before allocating receipt DATA
        _require(value is None)
        close.result[0] = (close, fd, value)
        _require(_native_file_allocation_original(allocation, original_ledger) is close
                 and ledger.inflight is inflight and inflight[0] is close
                 and ledger.counts is counts and len(counts) == 2
                 and counts[0] is used_after and counts[1] is reserved_after)
    except BaseException:
        if not actor_mismatch:
            if failure[0] is None:
                failure[0] = close
            close.state[1] = True
            failed[0] = True
        raise
    finally:
        if ledger.inflight is inflight and inflight[0] is close:
            inflight[0] = None


def _native_read_walk_tail(owner, registration, walk, expected, step):
    """Original declared-walk membership; no step construction or file effect."""
    _require(type(registration) is _NativeScopeRegistration and registration.owner is owner
             and type(registration.scope) is _Scope and type(walk) is _NativeDeclaredWalk
             and walk.owner is owner and walk.scope is registration.scope
             and walk.cell is registration.cell and walk.root is registration.root
             and type(expected) is ExpectedArtifact and walk.expected is expected
             and type(walk.index) is int and type(registration.file_walks) is tuple
             and 0 <= walk.index < len(registration.file_walks)
             and registration.file_walks[walk.index] is walk
             and type(walk.declaration) is tuple and walk.declaration is registration.scope.expected
             and walk.index < len(walk.declaration) and walk.declaration[walk.index] is expected
             and type(registration.file_progress) is list and len(registration.file_progress) == 1
             and type(registration.file_progress[0]) is int
             and registration.file_progress[0] == walk.index
             and type(walk.state) is list and len(walk.state) == 1
             and type(walk.state[0]) is int and walk.state[0] == 1
             and type(walk.read_step) is list and len(walk.read_step) == 1
             and walk.read_step[0] is step)
    _native_work_registration_tail(owner, registration)
    return walk


def _native_declared_leaf_tail(owner, registration, walk, expected, descriptor):
    """Exact original leaf and bounded parent chain for this declared file."""
    _require(type(walk) is _NativeDeclaredWalk and walk.expected is expected
             and type(walk.components) is tuple and 1 <= len(walk.components) <= 64)
    current = descriptor
    leaf = True
    for component in reversed(walk.components):
        _require(type(component) is str and type(current) is _NativeOpenedDescriptor)
        close = _native_descriptor_opened(current, registration.native_ledger)
        allocation = current.allocation
        _require(allocation.owner is owner and allocation.scope is registration.scope
                 and type(allocation.arguments) is tuple and len(allocation.arguments) == 3
                 and type(allocation.arguments[0]) is str and allocation.arguments[0] == component
                 and type(allocation.arguments[1]) is int
                 and close.state[0] is False and close.state[1] is False
                 and close.raw[0] is close.unset)
        directory_flag = allocation.native.flags[4]
        _require(type(directory_flag) is int
                 and bool(allocation.arguments[1] & directory_flag) is (not leaf))
        parent = allocation.parent
        if parent is None:
            _require(component == '/' and allocation.arguments[2] is None)
        else:
            _require(type(parent) is _NativeOpenedDescriptor
                     and allocation.arguments[2] is parent.fd)
        current, leaf = parent, False
    _require(current is None)
    return descriptor


def _native_read_lifecycle_tail(owner, registration, parents):
    """Import-free current owner/activation/continuation lifetime closure."""
    _require(type(registration) is _NativeScopeRegistration and registration.owner is owner
             and type(registration.scope) is _Scope
             and type(parents) is tuple and len(parents) == 7)
    scope = registration.scope
    activation, activation_scope, root, continuation, kind, source, source_kind = parents
    _require(type(activation) is GatewayActivationOwner and activation is scope.activation
             and activation_scope is scope.activation_scope
             and type(scope.parent) is tuple and len(scope.parent) == 6
             and scope.parent[0] is root and type(root) is tuple and len(root) == 3
             and root[0] is continuation and root[1] is activation and root[2] is source
             and type(kind) is type and type(continuation) is kind
             and type(source_kind) is type and type(source) is source_kind)
    own, active, parent = vars(owner), vars(activation), vars(continuation)
    _require(type(own) is dict and type(active) is dict and type(parent) is dict
             and own.get('_failed') is False and own.get('_unknown') is False
             and own.get('_ready') is False and own.get('_released') is False
             and own.get('_retaining') is False and own.get('_started') is True
             and type(own.get('_reading')) is bool
             and active.get('_scope') is activation_scope and active.get('_ready') is True
             and active.get('_retired') is False and active.get('_uncertain') is False
             and active.get('_continuation_owner') is continuation
             and active.get('_continuation_cell') is root
             and parent.get('_root') is root and parent.get('_source') is source
             and parent.get('_ready') is True and parent.get('_failed') is False
             and parent.get('_retired') is False)
    _native_work_registration_tail(owner, registration)
    return scope


def _native_read_accumulator_tail(owner, step, before):
    """Original fixed reader accumulators before admission; no callback or IO."""
    _require(type(step) is _NativeReadFileStep and step.owner is owner
             and type(step.scope) is _Scope and type(step.scope.parent) is tuple
             and len(step.scope.parent) == 6 and type(before) is tuple and len(before) == 3
             and before[0] is owner and before[1] is step.scope
             and type(before[2]) is int and before[2] >= 0
             and type(step.buffer) is bytearray and len(step.buffer) == before[2]
             and step.scope.parent[2] is step.buffer
             and type(step.scope.parent[5]) is tuple and len(step.scope.parent[5]) == 4
             and step.scope.parent[5][2] is step.hash_kind
             and type(step.hash_kind) is type and type(step.digest) is step.hash_kind
             and type(step.hash_update) is MethodDescriptorType
             and step.hash_update.__objclass__ is step.hash_kind
             and step.hash_update.__name__ == 'update'
             and vars(step.hash_kind).get('update') is step.hash_update)
    own = vars(owner)
    _require(type(own) is dict and type(step.buffer_aliases) is tuple
             and all(type(name) is str for name in step.buffer_aliases)
             and step.buffer_aliases in (('_buffer',), ('_buffer', '_original_buffer'))
             and all(own.get(name) is step.buffer for name in step.buffer_aliases))
    return step


def _native_cache_read_input_tail(owner, consumer, heads, attempt):
    """Original cache journal DATA joins only; unused, never read/ACK authority.

    The fixed producer must hold the actual heads/attempt before actor callbacks.
    Do not recapture them from owner mirrors after a callback. Prefix references
    are transient and must not survive the original call's eventual ACK.
    """
    _require(type(consumer) is _NativeReadConsumer and consumer.owner is owner
             and type(consumer.file_step) is _NativeReadFileStep
             and type(consumer.registration) is _NativeScopeRegistration)
    step, registration = consumer.file_step, consumer.registration
    _require(step.owner is owner and type(step.scope) is _Scope
             and type(step.scope.activation) is GatewayActivationOwner
             and step.scope is consumer.scope
             and step.registration is registration and registration.owner is owner
             and registration.scope is step.scope
             and type(step.material_module) is ModuleType
             and type(step.owner_type) is type and type(owner) is step.owner_type
             and type(heads) is tuple and len(heads) == 3
             and all(type(head) is tuple for head in heads)
             and type(attempt) is tuple and len(attempt) == 5)
    namespace = vars(step.material_module)
    _require(type(namespace) is dict and len(namespace) <= 4096
             and all(type(key) is str for key in namespace)
             and type(namespace.get('__name__')) is str
             and namespace.get('__name__') == 'hmp_startup.cache_reader'
             and namespace.get('DeclaredCacheReadOwner') is step.owner_type
             and type(step.scope.material_origin) is tuple
             and len(step.scope.material_origin) == 6
             and step.scope.material_origin[2] is namespace)
    prior_attempts, prior_results, attempts = heads
    index = len(prior_attempts)
    _require(0 <= index < 4096 and len(prior_results) == index
             and len(attempts) == index + 1 and attempts[index] is attempt
             and type(consumer.effect) is list and len(consumer.effect) == 1
             and type(consumer.effect[0]) is _ReadEffect
             and consumer.effect[0].before is consumer.before_count
             and consumer.effect[0].after is None
             and consumer.effect[0].returned is False and consumer.effect[0].unknown is False
             and type(consumer.descriptor) is _NativeOpenedDescriptor
             and attempt[0] is consumer.effect[0]
             and type(attempt[1]) is int and attempt[1] is consumer.descriptor.fd
             and type(attempt[2]) is int and attempt[2] is consumer.requested
             and attempt[3] is consumer.before_count
             and type(attempt[4]) is list and len(attempt[4]) == 1
             and attempt[4][0] is None)
    own, active = vars(owner), vars(step.scope.activation)
    _require(type(own) is dict and len(own) <= 512
             and all(type(key) is str for key in own)
             and type(active) is dict and len(active) <= 512
             and all(type(key) is str for key in active)
             and namespace.get('_OWNER') is owner
             and namespace.get('_ROOT') is registration.root
             and namespace.get('_CELL') is registration.cell
             and namespace.get('_READY') is None
             and namespace.get('_ATTEMPTS') is attempts
             and namespace.get('_RESULTS') is prior_results
             and own.get('_cache_native_heads') is heads
             and own.get('_attempts') is attempts and own.get('_results') is prior_results
             and own.get('_read_claim') is attempt and own.get('_reading') is True
             and own.get('_admitting') is False and own.get('_retaining') is False
             and own.get('_started') is True and own.get('_ready') is False
             and own.get('_released') is False and own.get('_failed') is False
             and own.get('_unknown') is False
             and own.get('_count_cell') is consumer.before_count
             and active.get('_cache_read_owner') is owner
             and active.get('_cache_read_cell') is registration.root
             and active.get('_cache_read_attempts') is attempts
             and active.get('_cache_read_results') is prior_results
             and active.get('_cache_read_fact') is None)
    _native_work_registration_tail(owner, registration)
    _native_read_walk_tail(owner, registration, consumer.walk, consumer.expected, step)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _native_read_accumulator_tail(owner, step, consumer.before_count)
    return heads


def _native_cache_read_return_tail(owner, consumer, actual, after):
    """Pure post-return journal DATA; fixed producer must hold the actual return."""
    _require(type(consumer) is _NativeReadConsumer and consumer.owner is owner
             and type(consumer.file_step) is _NativeReadFileStep
             and type(consumer.registration) is _NativeScopeRegistration
             and type(actual) is _NativeCacheReadReturn
             and type(actual.heads) is tuple and len(actual.heads) == 3
             and all(type(head) is tuple for head in actual.heads)
             and type(actual.result_heads) is tuple
             and type(actual.index) is int and 0 <= actual.index < 4096
             and type(actual.attempt) is tuple and len(actual.attempt) == 5
             and type(actual.result) is tuple and len(actual.result) == 3)
    step, registration = consumer.file_step, consumer.registration
    _require(type(step.scope) is _Scope and step.owner is owner
             and type(step.scope.activation) is GatewayActivationOwner
             and step.registration is registration and registration.owner is owner
             and registration.scope is step.scope and consumer.scope is step.scope
             and type(step.material_module) is ModuleType
             and type(step.owner_type) is type and type(owner) is step.owner_type)
    namespace, own, active = vars(step.material_module), vars(owner), vars(step.scope.activation)
    _require(type(namespace) is dict and len(namespace) <= 4096
             and all(type(key) is str for key in namespace)
             and type(own) is dict and len(own) <= 512
             and all(type(key) is str for key in own)
             and type(active) is dict and len(active) <= 512
             and all(type(key) is str for key in active))
    prior_attempts, prior_results, attempts = actual.heads
    _require(type(step.scope.material_origin) is tuple
             and len(step.scope.material_origin) == 6
             and step.scope.material_origin[2] is namespace)
    _require(type(consumer.requested) is int and 0 < consumer.requested <= 65536
             and len(prior_attempts) == len(prior_results) == actual.index
             and len(attempts) == len(actual.result_heads) == actual.index + 1
             and attempts[actual.index] is actual.attempt
             and actual.result_heads[actual.index] is actual.result
             and type(consumer.effect) is list and len(consumer.effect) == 1
             and type(consumer.effect[0]) is _ReadEffect
             and actual.attempt[0] is consumer.effect[0]
             and type(consumer.descriptor) is _NativeOpenedDescriptor
             and type(consumer.descriptor.fd) is int
             and actual.attempt[1] is consumer.descriptor.fd
             and actual.attempt[2] is consumer.requested
             and actual.attempt[3] is consumer.before_count
             and type(actual.attempt[4]) is list and len(actual.attempt[4]) == 1
             and actual.attempt[4][0] is actual.result
             and actual.result[0] is actual.attempt and actual.result[1] is after
             and type(actual.result[2]) is int and 0 <= actual.result[2] <= consumer.requested
             and type(after) is tuple and len(after) == 3
             and after[0] is owner and after[1] is step.scope
             and type(after[2]) is int and type(consumer.before_count) is tuple
             and len(consumer.before_count) == 3
             and consumer.before_count[0] is owner and consumer.before_count[1] is step.scope
             and type(consumer.before_count[2]) is int
             and after[2] == consumer.before_count[2] + actual.result[2]
             and consumer.effect[0].before is consumer.before_count
             and consumer.effect[0].after is after and consumer.effect[0].returned is True
             and consumer.effect[0].unknown is False)
    _require(type(namespace.get('__name__')) is str
             and namespace.get('__name__') == 'hmp_startup.cache_reader'
             and namespace.get('DeclaredCacheReadOwner') is step.owner_type
             and namespace.get('_OWNER') is owner and namespace.get('_READY') is None
             and namespace.get('_ROOT') is registration.root
             and namespace.get('_CELL') is registration.cell
             and namespace.get('_ATTEMPTS') is attempts
             and namespace.get('_RESULTS') is actual.result_heads
             and own.get('_attempts') is attempts and own.get('_results') is actual.result_heads
             and own.get('_count_cell') is after and own.get('_bytes_read') is after[2]
             and own.get('_reading') is False and own.get('_read_claim') is None
             and active.get('_cache_read_owner') is owner
             and active.get('_cache_read_cell') is registration.root
             and active.get('_cache_read_attempts') is attempts
             and active.get('_cache_read_results') is actual.result_heads
             and active.get('_cache_read_fact') is None)
    _native_work_registration_tail(owner, registration)
    _native_read_walk_tail(owner, registration, consumer.walk, consumer.expected, step)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    return actual


def _new_native_read_file_step(
    owner, registration, walk, expected, descriptor, digest, source, observations
):
    """Fixed runtime/cache reader construction only; never a nominated callable."""
    from hmp_startup.cache_reader import DeclaredCacheReadOwner
    from hmp_startup.runtime_reader import RuntimeSourceReadOwner

    _require(type(registration) is _NativeScopeRegistration and registration.owner is owner
             and type(walk) is _NativeDeclaredWalk and walk.owner is owner
             and walk.scope is registration.scope and walk.expected is expected
             and type(walk.read_step) is list and len(walk.read_step) == 1
             and walk.read_step[0] is None and type(expected) is ExpectedArtifact
             and type(observations) is list)
    _native_read_walk_tail(owner, registration, walk, expected, None)
    scope = _native_scope_current(owner, registration).scope
    _native_read_walk_tail(owner, registration, walk, expected, None)
    if type(owner) is RuntimeSourceReadOwner:
        owner_type, module_name = RuntimeSourceReadOwner, 'hmp_startup.runtime_reader'
        buffer = owner._original_buffer
        buffer_aliases = ('_buffer', '_original_buffer')
    else:
        _require(type(owner) is DeclaredCacheReadOwner)
        owner_type, module_name = DeclaredCacheReadOwner, 'hmp_startup.cache_reader'
        buffer = owner._buffer
        buffer_aliases = ('_buffer',)
    origin = scope.material_origin
    _require(type(origin) is tuple and len(origin) == 6 and origin[3] is owner_type)
    material, file_function = origin[0], origin[4]
    modules = vars(sys).get('modules')
    _require(type(modules) is dict)
    module = modules.get(module_name)
    _require(type(module) is ModuleType and type(owner_type) is type
             and type(material) is FunctionType and material.__code__ is origin[1]
             and material.__globals__ is origin[2] and vars(module) is origin[2]
             and type(file_function) is FunctionType and file_function.__code__ is origin[5]
             and vars(StartupArtifactOwner).get('_file') is file_function
             and type(buffer) is bytearray and len(buffer) == 0)
    hash_origin = scope.parent[5]
    _require(type(hash_origin) is tuple and len(hash_origin) == 4
             and type(hash_origin[2]) is type and type(digest) is hash_origin[2])
    hash_kind = hash_origin[2]
    hash_update = vars(hash_kind).get('update')
    _require(type(hash_update) is MethodDescriptorType and hash_update.__objclass__ is hash_kind
             and hash_update.__name__ == 'update')
    before = owner._count_cell
    _require(type(before) is tuple and len(before) == 3 and before[0] is owner
             and before[1] is scope and type(before[2]) is int and before[2] == 0)
    _native_declared_leaf_tail(owner, registration, walk, expected, descriptor)
    parent_root = scope.parent[0]
    parents = (scope.activation, scope.activation_scope, parent_root, parent_root[0],
               type(parent_root[0]), parent_root[2], type(parent_root[2]))
    _native_read_lifecycle_tail(owner, registration, parents)
    step = _NativeReadFileStep(owner, scope, registration, walk, expected, descriptor, parents,
                               digest, hash_kind, hash_update, buffer, buffer_aliases, source,
                               observations, file_function.__code__, material, material.__code__,
                               module, owner_type, [0, expected.size, before, None], [False])
    _require(_native_scope_current(owner, registration).scope is scope
             and walk.read_step[0] is None and owner._count_cell is before
             and vars(owner_type).get('_material_guard') is material
             and material.__code__ is step.material_code and material.__globals__ is vars(module)
             and vars(StartupArtifactOwner).get('_file') is file_function
             and file_function.__code__ is step.code and len(buffer) == 0)
    _native_read_walk_tail(owner, registration, walk, expected, None)
    _native_declared_leaf_tail(owner, registration, walk, expected, descriptor)
    _native_read_lifecycle_tail(owner, registration, parents)
    _native_read_accumulator_tail(owner, step, before)
    walk.read_step[0] = step
    _native_work_origin_tail(owner, registration, registration.native_origin)
    _native_read_walk_tail(owner, registration, walk, expected, step)
    _native_read_accumulator_tail(owner, step, before)
    return step


def _new_native_read_consumer(owner, step, descriptor, requested):
    """Bind the next exact original file cursor; no read or ACK is performed."""
    _require(type(step) is _NativeReadFileStep and step.owner is owner
             and type(step.walk) is _NativeDeclaredWalk
             and type(step.registration) is _NativeScopeRegistration
             and type(step.progress) is list and len(step.progress) == 4
             and type(step.eof) is list and len(step.eof) == 1 and step.eof[0] is False
             and type(step.progress[0]) is int and step.progress[0] >= 0
             and type(step.progress[1]) is int and step.progress[1] >= 0
             and step.progress[2] is owner._count_cell and step.progress[3] is None
             and type(requested) is int
             and requested == (min(step.progress[1], 65536) if step.progress[1] else 1)
             and type(descriptor) is _NativeOpenedDescriptor and descriptor is step.descriptor)
    registration = step.registration
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    _require(_native_scope_current(owner, registration).scope is step.scope)
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    close = _native_descriptor_opened(descriptor, registration.native_ledger)
    _require(descriptor.allocation.scope is step.scope and step.walk.read_step[0] is step
             and close.state[0] is False and close.state[1] is False
             and close.raw[0] is close.unset)
    ordinal, remaining, before, _ = step.progress
    consumer = _NativeReadConsumer(owner, step.scope, registration, step.walk, step, step.expected,
                                   descriptor, ordinal, requested, before, remaining, step.digest,
                                   step.buffer, step.source, step.observations, [None], step.code,
                                   step.material, step.material_code, step.material_module,
                                   step.owner_type, [None], [None], [None], [None], [None])
    _require(_native_scope_current(owner, registration).scope is step.scope
             and step.progress[0] is ordinal and step.progress[1] is remaining
             and step.progress[2] is before and step.progress[3] is None
             and step.walk.read_step[0] is step and step.eof[0] is False)
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    _native_declared_leaf_tail(owner, registration, step.walk, step.expected, descriptor)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _require(_native_descriptor_opened(descriptor, registration.native_ledger) is close
             and close.state[0] is False and close.state[1] is False
             and close.raw[0] is close.unset)
    step.progress[3] = consumer
    _native_work_origin_tail(owner, registration, registration.native_origin)
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    _require(step.progress[3] is consumer)
    _native_read_accumulator_tail(owner, step, before)
    return consumer


def _native_read_input_tail(owner, consumer, operation=None):
    """Original prepared consumer/effect before actual read admission."""
    _require(type(consumer) is _NativeReadConsumer and consumer.owner is owner
             and type(consumer.registration) is _NativeScopeRegistration
             and type(consumer.file_step) is _NativeReadFileStep)
    registration, step = consumer.registration, consumer.file_step
    _native_read_walk_tail(owner, registration, consumer.walk, consumer.expected, step)
    _native_work_origin_tail(owner, registration, registration.native_origin)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _native_read_accumulator_tail(owner, step, consumer.before_count)
    _native_declared_leaf_tail(owner, registration, consumer.walk, consumer.expected,
                               consumer.descriptor)
    _require(step.descriptor is consumer.descriptor and step.owner is owner
             and step.scope is registration.scope
             and step.registration is registration and consumer.scope is step.scope
             and type(step.progress) is list and len(step.progress) == 4
             and type(step.eof) is list and len(step.eof) == 1 and step.eof[0] is False
             and step.progress[0] is consumer.ordinal and step.progress[1] is consumer.remaining
             and step.progress[2] is consumer.before_count and step.progress[3] is consumer
             and type(consumer.ordinal) is int and consumer.ordinal >= 0
             and type(consumer.remaining) is int and consumer.remaining >= 0
             and type(consumer.requested) is int
             and consumer.requested == (min(consumer.remaining, 65536) if consumer.remaining else 1)
             and type(consumer.before_count) is tuple and len(consumer.before_count) == 3
             and consumer.before_count[0] is owner and consumer.before_count[1] is step.scope
             and type(consumer.before_count[2]) is int
             and owner._count_cell is consumer.before_count
             and owner._bytes_read is consumer.before_count[2] and owner._reading is True
             and type(consumer.result) is list and len(consumer.result) == 1
             and type(consumer.operation) is list and len(consumer.operation) == 1
             and type(consumer.progress) is list and len(consumer.progress) == 1
             and consumer.progress[0] is None
             and type(consumer.committed) is list and len(consumer.committed) == 1
             and consumer.committed[0] is None
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and consumer.consumption[0] is None
             and type(consumer.effect) is list and len(consumer.effect) == 1
             and type(consumer.effect[0]) is _ReadEffect
             and consumer.effect[0].before is consumer.before_count
             and consumer.effect[0].after is None and consumer.effect[0].returned is False
             and consumer.effect[0].unknown is False
             and type(step.scope.reads) is list and len(step.scope.reads) > 0
             and step.scope.reads[-1] is consumer.effect[0]
             and type(consumer.descriptor) is _NativeOpenedDescriptor)
    close = _native_descriptor_opened(consumer.descriptor, registration.native_ledger)
    _require(consumer.descriptor.allocation.scope is step.scope
             and close.state[0] is False and close.state[1] is False
             and close.raw[0] is close.unset)
    if operation is None:
        _require(consumer.operation[0] is None and consumer.result[0] is None)
    else:
        _require(type(operation) is _NativeFileOperation and operation.consumer is consumer
                 and operation.owner is owner and operation.scope is step.scope
                 and operation.registration is registration
                 and operation.ledger is registration.native_ledger
                 and operation.native is registration.native_origin
                 and operation.descriptor is consumer.descriptor
                 and type(operation.result) is _NativeFileResultClaim
                 and consumer.operation[0] is operation and consumer.result[0] is operation.result
                 and type(operation.result.attempt) is list and len(operation.result.attempt) == 1
                 and operation.result.attempt[0] is operation
                 and type(operation.state) is list and len(operation.state) == 3
                 and operation.state[1] is False and operation.state[2] is False
                 and operation.result.raw[0] is operation.result.unset
                 and operation.result.acknowledged[0] is None)
    _require(type(step.material_module) is ModuleType)
    namespace = vars(step.material_module)
    _require(type(namespace) is dict and len(namespace) <= 4096
             and all(type(key) is str for key in namespace)
             and type(namespace.get('__name__')) is str)
    if namespace.get('__name__') == 'hmp_startup.cache_reader':
        own = vars(owner)
        _native_cache_read_input_tail(owner, consumer, own.get('_cache_native_heads'),
                                      own.get('_read_claim'))
    return registration


def _prepare_native_read_operation(owner, consumer):
    """Allocate original operation DATA before the caller admits or debits it."""
    registration = _native_read_input_tail(owner, consumer)
    ledger, native = registration.native_ledger, registration.native_origin
    counts, attempts = ledger.counts, ledger.attempts
    _require(type(counts) is list and len(counts) == 2
             and all(type(value) is int for value in counts)
             and 0 <= counts[0] < 1048576 and 0 <= counts[1] < 1048576 - counts[0]
             and type(attempts) is list and len(attempts) < 1048576)
    used, reserved, index = counts[0], counts[1], len(attempts)
    unset = object()
    result = _NativeFileResultClaim([None], consumer, unset, [unset], [None], [None],
                                    [None], [None])
    operation = _NativeFileOperation(owner, registration.scope, registration, ledger, native,
                                     registration.context, 1, native.operations[1],
                                     (consumer.descriptor.fd, consumer.requested),
                                     consumer.descriptor, consumer, index,
                                     (counts, used, reserved, used + 1), [False],
                                     [False, False, False], result)
    result.attempt[0] = operation
    _native_read_input_tail(owner, consumer)
    _require(ledger.counts is counts and counts[0] is used and counts[1] is reserved
             and ledger.attempts is attempts and len(attempts) == index)
    consumer.result[0] = result
    consumer.operation[0] = operation
    return operation


def _admit_native_read(owner, consumer, operation):
    """Prepare/debit one fixed read; performs no file call or acknowledgment."""
    registration = _native_read_input_tail(owner, consumer, operation)
    ledger, native = registration.native_ledger, registration.native_origin
    phase = registration.native_phase
    counts, inflight, attempts = ledger.counts, ledger.inflight, ledger.attempts
    failed, failure, token = ledger.failed, ledger.failure, ledger.preparation
    _require(type(counts) is list and len(counts) == 2
             and all(type(value) is int for value in counts)
             and 0 <= counts[0] < 1048576 and 0 <= counts[1] < 1048576 - counts[0]
             and type(inflight) is list and len(inflight) == 1 and inflight[0] is None
             and type(attempts) is list and len(attempts) < 1048576
             and type(failed) is list and len(failed) == 1 and failed[0] is False
             and type(failure) is list and len(failure) == 1 and failure[0] is None
             and type(token) is list and len(token) == 3
             and phase.current[0] is phase.idle and phase.result[0] is None)
    _require(type(operation.budget) is tuple and len(operation.budget) == 4
             and operation.budget[0] is counts and counts[0] is operation.budget[1]
             and counts[1] is operation.budget[2] and type(operation.budget[3]) is int
             and operation.budget[3] == operation.budget[1] + 1
             and type(operation.index) is int and len(attempts) == operation.index
             and operation.state[0] is False)
    used, reserved, index = counts[0], counts[1], operation.index
    actor_mismatch = False
    actor_state = actor_arguments = None
    try:
        inflight[0] = token
        token[0], token[1], token[2] = owner, registration, consumer
        phase.result[0] = token
        phase.current[0] = phase.active
        actor_arguments = (consumer, operation, operation.callee, *operation.arguments)
        actor_state = _native_pre_actor_state(owner, actor_arguments)
        try:
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                  registration.context)
        except _NativeActorMismatchError:
            actor_mismatch = True
            raise
        _native_post_actor_state(owner, actor_state, actor_arguments)
        _native_read_input_tail(owner, consumer, operation)
        token[2] = operation
        _require(ledger.counts is counts and counts[0] is used and counts[1] is reserved
                 and ledger.attempts is attempts and len(attempts) == index
                 and ledger.inflight is inflight and inflight[0] is token
                 and ledger.phase is phase and phase.result[0] is token
                 and phase.current[0] is phase.active and failed[0] is False)
        attempts.append(operation)
        counts[0] = operation.budget[3]
        operation.state[0] = True
        phase.result[0] = operation
        inflight[0] = operation
        _require(_native_read_ready_tail(owner, consumer, operation) is operation)
        return operation
    except BaseException:
        unchanged_inputs = False
        if actor_mismatch:
            try:
                _native_post_actor_state(owner, actor_state, actor_arguments)
                _native_read_input_tail(owner, consumer, operation)
                unchanged_inputs = True
            except BaseException:
                unchanged_inputs = False
        clean_mismatch = (actor_mismatch and unchanged_inputs and operation.state[0] is False
                          and ledger.counts is counts
                          and len(counts) == 2 and counts[0] is used and counts[1] is reserved
                          and ledger.attempts is attempts and len(attempts) == index
                          and failed[0] is False and failure[0] is None
                          and inflight[0] is token and phase.result[0] is token
                          and phase.current[0] is phase.active)
        if not clean_mismatch:
            if failure[0] is None:
                failure[0] = operation if operation is not None else token
            failed[0] = True
            if operation is not None:
                operation.state[2] = True
            if (phase.current[0] is phase.active or phase.current[0] is phase.idle):
                phase.current[0] = phase.failed
        else:
            phase.current[0] = phase.idle
        if phase.result[0] is token or (operation is not None and phase.result[0] is operation):
            phase.result[0] = None  # preparation ended; no native file call occurred here
        if inflight[0] is token or (operation is not None and inflight[0] is operation):
            inflight[0] = None
        raise


def _native_read_ready_tail(owner, consumer, operation):
    """Same held admitted operation immediately before its fixed native call."""
    registration = _native_read_input_tail(owner, consumer, operation)
    ledger, phase = registration.native_ledger, registration.native_phase
    _require(operation.state[0] is True and type(operation.index) is int
             and type(ledger.attempts) is list and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and operation.context is registration.context
             and type(operation.operation) is int and operation.operation == 1
             and operation.callee is registration.native_origin.operations[1]
             and type(operation.arguments) is tuple and len(operation.arguments) == 2
             and operation.arguments[0] is consumer.descriptor.fd
             and operation.arguments[1] is consumer.requested
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and ledger.inflight[0] is operation
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False
             and phase.current[0] is phase.active and phase.result[0] is operation)
    return operation


def _abandon_native_read(owner, operation, raw, envelope):
    """Fixed producer failure handoff after its native call has ended; never ACK."""
    try:
        _require(type(operation) is _NativeFileOperation and operation.owner is owner
                 and type(operation.result) is _NativeFileResultClaim
                 and type(operation.registration) is _NativeScopeRegistration
                 and operation.ledger is operation.registration.native_ledger
                 and type(operation.ended) is list and len(operation.ended) == 1
                 and operation.ended[0] is True)
        ledger, result = operation.ledger, operation.result
        phase = operation.registration.native_phase
        operation.state[2] = True
        if ledger.failure[0] is None:
            ledger.failure[0] = operation
        ledger.failed[0] = True
        if result.acknowledged[0] is not None:
            # Keep actual ACK history. A partial/lost consumer acknowledgment
            # closes the lineage without rewriting it as an unconsumed read.
            if (phase.result[0] is operation
                    or (phase.result[0] is None and phase.current[0] is phase.pending
                        and ledger.inflight[0] is None)):
                result.category[0] = 'returned_bytes_ack_unconfirmed'
                if type(raw) is bytes and result.raw[0] is raw:
                    result.raw[0] = result.unset
                if envelope is not None and result.envelope[0] is envelope:
                    result.envelope[0] = None
                phase.result[0] = None
                phase.current[0] = phase.failed
            if ledger.inflight[0] is operation:
                ledger.inflight[0] = None
            return
        if type(raw) is bytes and result.raw[0] is raw:
            result.length[0] = len(raw)
            result.category[0] = 'returned_bytes_abandoned'
            result.raw[0] = result.unset
        elif result.raw[0] is result.unset:
            result.category[0] = ('returned_bytes_abandoned'
                                  if operation.state[1] is True and type(result.length[0]) is int
                                  else 'read_unconfirmed')
        if envelope is not None and result.envelope[0] is envelope:
            result.envelope[0] = None
        if phase.result[0] is operation:
            phase.result[0] = None
            phase.current[0] = phase.failed
        if ledger.inflight[0] is operation:
            ledger.inflight[0] = None
    finally:
        raw = envelope = None


def _native_read_result_tail(owner, envelope):
    """Import-free original pending-read joins; no ACK or fresh work authority."""
    _require(type(envelope) is _NativeReadResult)
    operation, result, consumer = envelope.operation, envelope.result, envelope.consumer
    _require(type(operation) is _NativeFileOperation
             and type(result) is _NativeFileResultClaim and type(consumer) is _NativeReadConsumer
             and operation.owner is owner and consumer.owner is owner
             and operation.result is result and operation.consumer is consumer
             and result.consumer is consumer and type(result.attempt) is list
             and len(result.attempt) == 1 and result.attempt[0] is operation
             and type(consumer.result) is list and len(consumer.result) == 1
             and consumer.result[0] is result
             and result.attempt is envelope.attempt_cell
             and result.raw is envelope.raw_cell and result.length is envelope.length_cell
             and result.category is envelope.category_cell
             and result.acknowledged is envelope.ack_cell
             and result.envelope is envelope.envelope_cell
             and type(envelope.envelope_cell) is list and len(envelope.envelope_cell) == 1
             and envelope.envelope_cell[0] is envelope
             and consumer.result is envelope.consumer_result_cell
             and consumer.operation is envelope.consumer_operation_cell
             and type(consumer.operation) is list and len(consumer.operation) == 1
             and consumer.operation[0] is operation
             and consumer.progress is envelope.consumer_progress_cell
             and consumer.committed is envelope.commit_cell
             and type(envelope.commit_cell) is list and len(envelope.commit_cell) == 1
             and consumer.consumption is envelope.consumption_cell
             and type(envelope.consumption_cell) is list and len(envelope.consumption_cell) == 1
             and consumer.effect is envelope.effect_cell
             and type(envelope.effect_cell) is list and len(envelope.effect_cell) == 1
             and envelope.effect_cell[0] is envelope.effect
             and type(envelope.effect) is _ReadEffect
             and type(operation.registration) is _NativeScopeRegistration)
    registration = operation.registration
    _native_work_registration_tail(owner, registration)
    ledger, native = registration.native_ledger, registration.native_origin
    scope = registration.scope
    phase = registration.native_phase
    _require(operation.registration is consumer.registration
             and operation.ledger is ledger and operation.native is native
             and operation.context is registration.context
             and operation.scope is scope and consumer.scope is scope
             and type(phase.current) is list and len(phase.current) == 1
             and phase.current[0] is phase.pending
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is operation
             and type(ledger.inflight) is list and len(ledger.inflight) == 1
             and ledger.inflight[0] is None
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False and type(ledger.attempts) is list
             and type(operation.index) is int and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and type(operation.operation) is int and operation.operation == 1
             and operation.callee is native.operations[1]
             and type(operation.arguments) is tuple and len(operation.arguments) == 2
             and type(operation.arguments[0]) is int and operation.arguments[0] >= 0
             and type(operation.arguments[1]) is int and 0 < operation.arguments[1] <= 65536
             and type(operation.state) is list and len(operation.state) == 3
             and operation.state[0] is True and operation.state[1] is True
             and operation.state[2] is False
             and type(operation.ended) is list and len(operation.ended) == 1
             and operation.ended[0] is True
             and type(result.raw) is list and len(result.raw) == 1
             and type(envelope.raw) is bytes and result.raw[0] is envelope.raw
             and len(envelope.raw) <= operation.arguments[1]
             and type(result.length) is list and len(result.length) == 1
             and type(result.length[0]) is int and result.length[0] == len(result.raw[0])
             and type(result.category) is list and len(result.category) == 1
             and type(result.category[0]) is str and result.category[0] == 'returned_bytes'
             and type(result.acknowledged) is list and len(result.acknowledged) == 1
             and result.acknowledged[0] is None
             and type(consumer.before_count) is tuple and len(consumer.before_count) == 3
             and consumer.before_count[0] is owner and consumer.before_count[1] is scope
             and type(consumer.before_count[2]) is int
             and type(consumer.progress) is list and len(consumer.progress) == 1)
    after = envelope.after_count
    _require(consumer.progress[0] is after and type(after) is tuple and len(after) == 3
             and after[0] is owner and after[1] is scope
             and type(after[2]) is int and after[2] == consumer.before_count[2] + result.length[0]
             and owner._count_cell is after and owner._bytes_read is after[2]
             and envelope.effect.before is consumer.before_count and envelope.effect.after is after
             and envelope.effect.returned is True and envelope.effect.unknown is False
             and type(envelope.effect_index) is int and envelope.effect_index >= 0
             and type(scope.reads) is list and len(scope.reads) == envelope.effect_index + 1
             and scope.reads[envelope.effect_index] is envelope.effect
             and type(consumer.requested) is int and consumer.requested is operation.arguments[1]
             and type(consumer.ordinal) is int and consumer.ordinal >= 0
             and type(consumer.remaining) is int and consumer.remaining >= 0
             and type(consumer.expected) is ExpectedArtifact
             and type(consumer.walk) is _NativeDeclaredWalk
             and consumer.walk.owner is owner and consumer.walk.scope is scope
             and consumer.walk.expected is consumer.expected
             and type(consumer.walk.state) is list and len(consumer.walk.state) == 1
             and type(consumer.walk.state[0]) is int and consumer.walk.state[0] == 1
             and type(registration.file_walks) is tuple
             and type(consumer.walk.index) is int
             and 0 <= consumer.walk.index < len(registration.file_walks)
             and registration.file_walks[consumer.walk.index] is consumer.walk
             and type(consumer.descriptor) is _NativeOpenedDescriptor
             and operation.descriptor is consumer.descriptor
             and consumer.descriptor.fd is operation.arguments[0])
    step = envelope.step
    _require(consumer.file_step is step and type(step) is _NativeReadFileStep
             and step.owner is owner and step.scope is scope
             and step.registration is registration and step.walk is consumer.walk
             and step.expected is consumer.expected and step.descriptor is consumer.descriptor
             and step.digest is consumer.digest
             and step.buffer is consumer.buffer and step.source is consumer.source
             and step.observations is consumer.observations and step.code is consumer.code
             and step.material is consumer.material and step.material_code is consumer.material_code
             and step.material_module is consumer.material_module
             and step.owner_type is consumer.owner_type
             and type(step.eof) is list and len(step.eof) == 1 and step.eof[0] is False
             and type(step.walk.read_step) is list and len(step.walk.read_step) == 1
             and step.walk.read_step[0] is step
             and step.progress is envelope.step_progress_cell
             and type(step.progress) is list and len(step.progress) == 4
             and step.progress[0] is consumer.ordinal and step.progress[1] is consumer.remaining
             and step.progress[2] is consumer.before_count and step.progress[3] is consumer)
    if envelope.source_read is None:
        _require(envelope.source_read_kind is type(None) and envelope.source_return is None
                 and step.source is None)
    else:
        source_read, source_return = envelope.source_read, envelope.source_return
        _require(type(envelope.source_read_kind) is type
                 and type(source_read) is envelope.source_read_kind
                 and source_read.root is step.source
                 and source_read.record is envelope.effect
                 and source_read.before is consumer.before_count
                 and type(source_read.index) is int
                 and source_read.index == envelope.effect_index
                 and type(source_read.result) is list and len(source_read.result) == 1
                 and source_read.result[0] is source_return
                 and type(source_return) is tuple and len(source_return) == 2
                 and source_return[0] is after and type(source_return[1]) is int
                 and source_return[1] == result.length[0]
                 and type(step.source.reads) is list and len(step.source.reads) > 0
                 and step.source.reads[-1] is source_read)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _native_declared_leaf_tail(owner, registration, consumer.walk, consumer.expected,
                               consumer.descriptor)
    origin = scope.material_origin
    _require(type(origin) is tuple and len(origin) == 6
             and origin[0] is consumer.material and origin[1] is consumer.material_code
             and origin[3] is consumer.owner_type and origin[5] is consumer.code
             and type(origin[4]) is FunctionType and origin[4].__code__ is consumer.code
             and vars(StartupArtifactOwner).get('_file') is origin[4])
    close = _native_descriptor_opened(consumer.descriptor, ledger)
    _require(close.state[0] is False and close.state[1] is False
             and close.raw[0] is close.unset and close.result[0] is None
             and type(consumer.code) is CodeType
             and type(consumer.material) is FunctionType
             and type(consumer.material_code) is CodeType
             and consumer.material.__code__ is consumer.material_code
             and type(consumer.material_module) is ModuleType
             and type(consumer.owner_type) is type and type(owner) is consumer.owner_type
             and vars(consumer.owner_type).get('_material_guard') is consumer.material)
    modules = vars(sys).get('modules')
    namespace = vars(consumer.material_module)
    module_name = namespace.get('__name__')
    owner_name = consumer.owner_type.__name__
    _require(type(modules) is dict and type(module_name) is str
             and modules.get(module_name) is consumer.material_module
             and consumer.material.__globals__ is namespace and namespace is origin[2]
             and type(owner_name) is str and namespace.get(owner_name) is consumer.owner_type)
    if envelope.cache_return is not None:
        _native_cache_read_return_tail(owner, consumer, envelope.cache_return, after)
        _require(vars(owner).get('_cache_native_heads') is None)
    else:
        _require(module_name == 'hmp_startup.runtime_reader')
    _native_work_origin_tail(owner, registration, native)
    return scope


def _native_read_result_current(owner, envelope):
    """Fixed producer must carry this original envelope, never recapture its slot."""
    scope = _native_read_result_tail(owner, envelope)
    operation, consumer = envelope.operation, envelope.consumer
    native = operation.native
    material = consumer.material
    _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                          operation.context)
    _require(_native_read_result_tail(owner, envelope) is scope)
    _require(material(owner) is scope)
    _require(_native_read_result_tail(owner, envelope) is scope)
    return scope


def _consume_native_runtime_read(owner, envelope):
    """Experimental fixed runtime-source consumer; not runtime qualification."""
    data = source_buffer = step = operation = runtime_kind = source_digest = None
    consumption_cell = token = arguments = actor_state = None
    failed = cleanup_unknown = owns_consumption = False
    try:
        # Original pending-result and accumulator joins are import-free. Capture
        # owned allocations before any import hook/material/actor callback.
        _require(type(envelope) is _NativeReadResult)
        operation, consumer, step = envelope.operation, envelope.consumer, envelope.step
        _require(_native_read_result_tail(owner, envelope) is step.scope
                 and vars(step.material_module).get('__name__') == 'hmp_startup.runtime_reader'
                 and envelope.commit_cell[0] is None and step.source is not None)
        _native_read_accumulator_tail(owner, step, consumer.before_count)
        data, source_buffer = envelope.raw, step.source.buffer
        _require(type(source_buffer) is bytearray)
        runtime_kind = step.owner_type
        consumption_cell = envelope.consumption_cell
        _require(consumption_cell[0] is None)
        token = object()
        arguments = (operation, consumer, step, data, source_buffer)
        actor_state = _native_pre_actor_state(owner, arguments)
        _native_actor_context(operation.native.actor_calls,
                              (operation.native.native, operation.native.thread_native),
                              operation.context)
        _native_post_actor_state(owner, actor_state, arguments)
        _require(_native_read_result_tail(owner, envelope) is step.scope)
        _native_read_accumulator_tail(owner, step, consumer.before_count)
        _require(consumption_cell[0] is None)
        # Reentry/duplicates cannot acquire this original one-use consumer slot.
        consumption_cell[0] = token
        owns_consumption = True
        from hmp_startup.runtime_reader import RuntimeSourceReadOwner

        from . import presentation_source_digest as source_digest

        _require(type(owner) is RuntimeSourceReadOwner and runtime_kind is RuntimeSourceReadOwner)
        _require(_native_read_result_current(owner, envelope) is step.scope
                 and consumption_cell[0] is token)
        length = len(data)
        eof = consumer.remaining == 0
        _require((length == 0 if eof else 0 < length <= consumer.remaining)
                 and type(step.observations) is list
                 and type(step.source.effect.consumed) is int
                 and len(step.observations) == step.source.effect.consumed)
        observation = (envelope.source_read, envelope.source_return)
        step.observations.append(observation)
        if eof:
            _require(source_digest.consume_eof(
                step.source, source_buffer, envelope.after_count, step.observations)
                     is envelope.after_count)
        else:
            step.buffer.extend(data)
            _require(_native_read_result_current(owner, envelope) is step.scope)
            step.hash_update(step.digest, data)
            _require(_native_read_result_current(owner, envelope) is step.scope)
            source_digest.append(step.source, source_buffer, data, step.observations)
        commit = _NativeRuntimeReadCommit(
            operation, envelope.result, consumer, step, envelope.after_count,
            consumer.ordinal + 1, consumer.remaining - length, eof, token, observation,
            step.source.effect.consumed)
        # Publish the actual consumer return/progress before post-effect callbacks.
        envelope.commit_cell[0] = commit
        _require(_native_read_result_current(owner, envelope) is step.scope)
        _native_runtime_read_commit_tail(owner, envelope, commit, source_buffer, token)
        # No callbacks after this final original-result/progress closure. A lost
        # acknowledgment fails permanently through the handler, never a replay.
        envelope.ack_cell[0] = commit
        envelope.raw_cell[0] = envelope.result.unset
        envelope.envelope_cell[0] = None
        step.progress[0] = commit.ordinal
        step.progress[1] = commit.remaining
        step.progress[2] = commit.count
        step.progress[3] = None
        step.eof[0] = commit.eof
        phase = operation.registration.native_phase
        phase.result[0] = None
        phase.current[0] = phase.idle
        return commit
    except BaseException:
        failed = True
        owns_consumption = (owns_consumption or
                            (token is not None and type(consumption_cell) is list
                             and len(consumption_cell) == 1 and consumption_cell[0] is token))
        if owns_consumption:
            if runtime_kind is not None and type(owner) is runtime_kind:
                owner._failed = owner._unknown = True
            try:
                _abandon_native_read(owner, operation, data, envelope)
            except BaseException:
                cleanup_unknown = True  # bounded evidence, never exception details
            try:
                # Erase captured original buffers even if a module import failed.
                zeros = bytes(65536)
                for buffer in (step.buffer, source_buffer):
                    _require(type(buffer) is bytearray)
                    for start in range(0, len(buffer), len(zeros)):
                        width = min(len(zeros), len(buffer) - start)
                        buffer[start:start + width] = zeros[:width]
                    buffer.clear()
                step.source.effect.cleared = True
                step.source.effect.unknown = True
            except BaseException:
                cleanup_unknown = True  # fresh outward refusal has no raw context
    finally:
        data = envelope = arguments = actor_state = None
    if failed:
        refusal = ArtifactObservationError(owner)
        refusal.cleanup_unknown = cleanup_unknown
        raise refusal from None


class _NativeCacheReadCommit(NamedTuple):
    """Bounded raw-free cache ACK; deliberately excludes journal prefix tuples."""
    operation: _NativeFileOperation
    result: _NativeFileResultClaim
    consumer: _NativeReadConsumer
    step: _NativeReadFileStep
    count: tuple
    ordinal: int
    remaining: int
    eof: bool
    consumption_token: object
    cache_attempt: tuple
    cache_result: tuple
    cache_index: int
    header: bytes

    def __repr__(self):
        return '<NativeCacheReadCommit unqualified progress redacted>'


def _consume_native_cache_read(owner, envelope):
    """Fixed cache buffer/hash consumer; integrated source requires runtime qualification."""
    data = step = operation = cache_kind = None
    token = consumption_cell = arguments = actor_state = None
    owns_consumption = failed = cleanup_unknown = False
    try:
        _require(type(envelope) is _NativeReadResult)
        operation, consumer, step = envelope.operation, envelope.consumer, envelope.step
        _require(_native_read_result_tail(owner, envelope) is step.scope
                 and vars(step.material_module).get('__name__') == 'hmp_startup.cache_reader'
                 and type(envelope.cache_return) is _NativeCacheReadReturn
                 and step.source is None and envelope.commit_cell[0] is None)
        _native_read_accumulator_tail(owner, step, consumer.before_count)
        data, cache_kind = envelope.raw, step.owner_type
        consumption_cell = envelope.consumption_cell
        _require(consumption_cell[0] is None)
        token = object()
        arguments = (operation, consumer, step, data)
        actor_state = _native_pre_actor_state(owner, arguments)
        _native_actor_context(operation.native.actor_calls,
                              (operation.native.native, operation.native.thread_native),
                              operation.context)
        _native_post_actor_state(owner, actor_state, arguments)
        _require(_native_read_result_tail(owner, envelope) is step.scope)
        _native_read_accumulator_tail(owner, step, consumer.before_count)
        _require(consumption_cell[0] is None)
        consumption_cell[0] = token
        owns_consumption = True
        from hmp_startup.cache_reader import DeclaredCacheReadOwner

        _require(type(owner) is DeclaredCacheReadOwner and cache_kind is DeclaredCacheReadOwner
                 and _native_read_result_current(owner, envelope) is step.scope
                 and consumption_cell[0] is token)
        length, eof = len(data), consumer.remaining == 0
        _require(length == 0 if eof else 0 < length <= consumer.remaining)
        if not eof:
            step.buffer.extend(data)
            _require(_native_read_result_current(owner, envelope) is step.scope)
            step.hash_update(step.digest, data)
            _require(_native_read_result_current(owner, envelope) is step.scope)
        actual = envelope.cache_return
        commit = _NativeCacheReadCommit(
            operation, envelope.result, consumer, step, envelope.after_count,
            consumer.ordinal + 1, consumer.remaining - length, eof, token,
            actual.attempt, actual.result, actual.index, bytes(step.buffer[:16]))
        envelope.commit_cell[0] = commit
        _require(_native_read_result_current(owner, envelope) is step.scope)
        _native_cache_read_commit_tail(owner, envelope, commit, token)
        envelope.ack_cell[0] = commit
        envelope.raw_cell[0] = envelope.result.unset
        envelope.envelope_cell[0] = None
        step.progress[0] = commit.ordinal
        step.progress[1] = commit.remaining
        step.progress[2] = commit.count
        step.progress[3] = None
        step.eof[0] = commit.eof
        phase = operation.registration.native_phase
        phase.result[0] = None
        phase.current[0] = phase.idle
        return commit
    except BaseException:
        failed = True
        owns_consumption = (owns_consumption or
                            (token is not None and type(consumption_cell) is list
                             and len(consumption_cell) == 1 and consumption_cell[0] is token))
        if owns_consumption:
            if cache_kind is not None and type(owner) is cache_kind:
                owner._failed = owner._unknown = True
            try:
                _abandon_native_read(owner, operation, data, envelope)
            except BaseException:
                cleanup_unknown = True
            try:
                buffer = step.buffer
                _require(type(buffer) is bytearray)
                zeros = bytes(65536)
                for start in range(0, len(buffer), len(zeros)):
                    width = min(len(zeros), len(buffer) - start)
                    buffer[start:start + width] = zeros[:width]
                buffer.clear()
            except BaseException:
                cleanup_unknown = True
    finally:
        data = envelope = arguments = actor_state = None
    if failed:
        refusal = ArtifactObservationError(owner)
        refusal.cleanup_unknown = cleanup_unknown
        raise refusal from None


def _native_cache_read_commit_tail(owner, envelope, commit, token):
    """Actual pending cache return and bounded header closure before ACK."""
    scope = _native_read_result_tail(owner, envelope)
    _require(type(commit) is _NativeCacheReadCommit
             and envelope.commit_cell[0] is commit
             and envelope.consumption_cell[0] is token
             and commit.consumption_token is token
             and commit.operation is envelope.operation and commit.result is envelope.result
             and commit.consumer is envelope.consumer and commit.step is envelope.step
             and commit.count is envelope.after_count)
    actual, step, consumer = envelope.cache_return, commit.step, commit.consumer
    _require(type(actual) is _NativeCacheReadReturn
             and commit.cache_attempt is actual.attempt and commit.cache_result is actual.result
             and commit.cache_index is actual.index
             and type(commit.ordinal) is int and commit.ordinal == consumer.ordinal + 1
             and type(commit.remaining) is int
             and commit.remaining == consumer.remaining - len(envelope.raw)
             and type(commit.eof) is bool and commit.eof is (consumer.remaining == 0)
             and (len(envelope.raw) == 0 if commit.eof else len(envelope.raw) > 0)
             and type(commit.header) is bytes
             and len(commit.header) == min(16, commit.count[2])
             and commit.header == step.buffer[:16])
    _native_read_accumulator_tail(owner, step, commit.count)
    return scope


def _native_runtime_read_commit_tail(owner, envelope, commit, source_buffer, token):
    """Import-free final consumer progress closure while original read is pending."""
    scope = _native_read_result_tail(owner, envelope)
    _require(envelope.consumption_cell[0] is token
             and type(commit) is _NativeRuntimeReadCommit and commit.consumption_token is token
             and envelope.commit_cell[0] is commit
             and commit.operation is envelope.operation and commit.result is envelope.result
             and commit.consumer is envelope.consumer and commit.step is envelope.step
             and commit.count is envelope.after_count)
    step, consumer = commit.step, commit.consumer
    _require(type(commit.ordinal) is int and commit.ordinal == consumer.ordinal + 1
             and type(commit.remaining) is int
             and commit.remaining == consumer.remaining - len(envelope.raw)
             and type(commit.eof) is bool and commit.eof is (consumer.remaining == 0)
             and (len(envelope.raw) == 0 if commit.eof else len(envelope.raw) > 0)
             and type(step.buffer) is bytearray and len(step.buffer) == commit.count[2]
             and scope.parent[2] is step.buffer and vars(owner).get('_buffer') is step.buffer
             and vars(owner).get('_original_buffer') is step.buffer
             and type(step.digest) is step.hash_kind
             and vars(step.hash_kind).get('update') is step.hash_update
             and step.source.buffer is source_buffer and type(source_buffer) is bytearray
             and len(source_buffer) == commit.count[2]
             and step.source.effect.buffer is source_buffer
             and step.source.effect.size == commit.count[2]
             and type(commit.source_consumed) is int and commit.source_consumed > 0
             and step.source.effect.consumed is commit.source_consumed
             and type(step.observations) is list
             and len(step.observations) == commit.source_consumed
             and step.observations[-1] is commit.source_observation
             and type(commit.source_observation) is tuple and len(commit.source_observation) == 2
             and commit.source_observation[0] is envelope.source_read
             and commit.source_observation[1] is envelope.source_return
             and (step.source.effect.eof is commit.count if commit.eof
                  else step.source.effect.eof is None))
    return scope


def _native_runtime_read_closed_tail(owner, commit, step):
    """Caller holds the actual fixed-consumer return, never recaptures its ACK."""
    _require(type(commit) is _NativeRuntimeReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    operation, result, consumer = commit.operation, commit.result, commit.consumer
    registration = step.registration
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _require(operation.owner is owner and operation.registration is registration
             and operation.result is result and operation.consumer is consumer
             and result.consumer is consumer and consumer.file_step is step
             and type(result.acknowledged) is list and len(result.acknowledged) == 1
             and result.acknowledged[0] is commit
             and type(result.raw) is list and len(result.raw) == 1
             and result.raw[0] is result.unset
             and type(result.envelope) is list and len(result.envelope) == 1
             and result.envelope[0] is None
             and consumer.committed[0] is commit
             and consumer.consumption[0] is commit.consumption_token
             and type(operation.state) is list and len(operation.state) == 3
             and operation.state[0] is True and operation.state[1] is True
             and operation.state[2] is False
             and type(commit.count) is tuple and len(commit.count) == 3
             and owner._count_cell is commit.count and owner._bytes_read is commit.count[2]
             and step.progress[0] is commit.ordinal and step.progress[1] is commit.remaining
             and step.progress[2] is commit.count and step.progress[3] is None
             and step.eof[0] is commit.eof)
    ledger, phase = operation.ledger, registration.native_phase
    _require(ledger is registration.native_ledger and ledger.failed[0] is False
             and ledger.attempts[operation.index] is operation
             and ledger.counts is operation.budget[0]
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and ledger.inflight[0] is None
             and phase.current[0] is phase.idle and phase.result[0] is None)
    _native_read_accumulator_tail(owner, step, commit.count)
    return commit


def _native_cache_read_closed_tail(owner, commit, step):
    """Caller closure for the actual cache ACK; no journal prefixes are retained."""
    _require(type(commit) is _NativeCacheReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    operation, result, consumer = commit.operation, commit.result, commit.consumer
    registration = step.registration
    _native_read_walk_tail(owner, registration, step.walk, step.expected, step)
    _native_read_lifecycle_tail(owner, registration, step.parents)
    _require(operation.owner is owner and operation.registration is registration
             and operation.result is result and operation.consumer is consumer
             and result.consumer is consumer and consumer.file_step is step
             and type(result.acknowledged) is list and len(result.acknowledged) == 1
             and result.acknowledged[0] is commit
             and type(result.raw) is list and len(result.raw) == 1
             and result.raw[0] is result.unset
             and type(result.envelope) is list and len(result.envelope) == 1
             and result.envelope[0] is None
             and consumer.committed[0] is commit
             and consumer.consumption[0] is commit.consumption_token
             and type(operation.state) is list and len(operation.state) == 3
             and operation.state[0] is True and operation.state[1] is True
             and operation.state[2] is False
             and type(commit.count) is tuple and len(commit.count) == 3
             and owner._count_cell is commit.count and owner._bytes_read is commit.count[2]
             and step.progress[0] is commit.ordinal and step.progress[1] is commit.remaining
             and step.progress[2] is commit.count and step.progress[3] is None
             and step.eof[0] is commit.eof)
    ledger, phase = operation.ledger, registration.native_phase
    _require(ledger is registration.native_ledger and ledger.failed[0] is False
             and ledger.attempts[operation.index] is operation
             and ledger.counts is operation.budget[0]
             and ledger.counts[0] is operation.budget[3]
             and ledger.counts[1] is operation.budget[2]
             and ledger.inflight[0] is None
             and phase.current[0] is phase.idle and phase.result[0] is None)
    _native_read_accumulator_tail(owner, step, commit.count)
    namespace, own = vars(step.material_module), vars(owner)
    _require(type(namespace) is dict and len(namespace) <= 4096
             and all(type(key) is str for key in namespace)
             and namespace.get('__name__') == 'hmp_startup.cache_reader'
             and namespace.get('_OWNER') is owner
             and type(own) is dict and len(own) <= 4096
             and all(type(key) is str for key in own)
             and own.get('_cache_native_heads') is None
             and own.get('_reading') is False and own.get('_read_claim') is None)
    attempts, results = namespace.get('_ATTEMPTS'), namespace.get('_RESULTS')
    _require(type(attempts) is tuple and type(results) is tuple
             and type(commit.cache_index) is int and 0 <= commit.cache_index < 4096
             and len(attempts) == len(results) == commit.cache_index + 1
             and attempts[commit.cache_index] is commit.cache_attempt
             and results[commit.cache_index] is commit.cache_result
             and own.get('_attempts') is attempts and own.get('_results') is results
             and step.scope.activation._cache_read_attempts is attempts
             and step.scope.activation._cache_read_results is results
             and type(commit.cache_attempt) is tuple and len(commit.cache_attempt) == 5
             and type(commit.cache_result) is tuple and len(commit.cache_result) == 3
             and commit.cache_result[0] is commit.cache_attempt
             and commit.cache_result[1] is commit.count
             and type(commit.cache_attempt[4]) is list and len(commit.cache_attempt[4]) == 1
             and commit.cache_attempt[4][0] is commit.cache_result
             and type(commit.header) is bytes
             and len(commit.header) == min(16, commit.count[2])
             and commit.header == step.buffer[:16])
    return commit


def _native_pre_actor_state(owner, arguments):
    """Bounded original owner/argument mirrors, not an operation permission."""
    names = vars(owner)
    _require(type(names) is dict and len(names) <= 512
             and all(type(key) is str for key in names) and type(arguments) is tuple)
    return names, tuple(names.items()), arguments


def _native_post_actor_state(owner, held, arguments):
    names, entries, original_arguments = held
    _require(vars(owner) is names and len(names) == len(entries)
             and all(key in names and names[key] is value for key, value in entries)
             and type(arguments) is tuple and len(arguments) == len(original_arguments)
             and all(a is b for a, b in zip(arguments, original_arguments, strict=True)))


def _native_actor_context(functions, modules, expected):
    """Internal context DATA only; caller must hold validated original functions.

    Shape/context equality grants neither work nor close authority. Fixed work
    callers obtain these references from the joined registration; future close
    callers must obtain them from an independently anchored original close claim.
    """
    _require(type(expected) is tuple and len(expected) == 3
             and all(type(value) is int for value in expected)
             and type(functions) is tuple and len(functions) == 3
             and type(modules) is tuple and len(modules) == 2
             and all(type(module) is ModuleType for module in modules)
             and all(type(function) is BuiltinFunctionType for function in functions))
    _require(functions[0].__self__ is modules[0] and functions[0].__name__ == 'getpid'
             and functions[1].__self__ is modules[0] and functions[1].__name__ == 'geteuid'
             and functions[2].__self__ is modules[1] and functions[2].__name__ == 'get_ident')
    actual = (functions[0](), functions[1](), functions[2]())
    _require(all(type(value) is int for value in actual))
    if actual != expected:
        raise _NativeActorMismatchError
    return actual


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
                     and all(_descriptor_closed_in_scope(row, s)
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
                     and all(_descriptor_closed_in_scope(row, s)
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
        native = _capture_native_work_origin(self, native_registration)
        open_call = None if native is None else native.operations[0]
        native_flags = None if native is None else native.flags
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
        allocation = None
        row.attempted = True
        if native is None:
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if directory:
                flags |= os.O_DIRECTORY
        else:
            _native_work_origin_tail(self, native_registration, native)
            _require(native_flags is native.flags)
            flags = native_flags[0] | native_flags[1] | native_flags[2] | native_flags[3]
            if directory:
                flags |= native_flags[4]
        try:
            _native_registration_tail(self, s, owner_cell, root_cell,
                                      native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            _require(native is None or open_call is native.operations[0])
            if native is None:
                open_call = os.open
            if native is not None:
                allocation = _allocate_native_file_open(
                    self, native_registration, parent, (name, flags, parent), row)
                records = s.records
                record_prefix = tuple(records)
                record_index = len(record_prefix) - 1
                arguments = (name, parent, directory, flags, open_call)
                held_state = _native_pre_actor_state(self, arguments)
                _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
                _native_post_actor_state(self, held_state,
                                         (name, parent, directory, flags, open_call))
                _native_registration_tail(self, s, owner_cell, root_cell,
                                          native_registration, registry)
                _native_work_origin_tail(self, native_registration, native)
                _require(open_call is native.operations[0] and native_flags is native.flags
                         and row.fd is None and row.attempted is True
                         and row.close_attempted is False and row.closed is False
                         and row.unknown is False and s.records is records
                         and len(records) == len(record_prefix)
                         and all(actual is original for actual, original in
                                 zip(records, record_prefix, strict=True))
                         and records[-1] is row
                         and _native_file_allocation_original(
                             allocation, native_registration.native_ledger) is allocation.close
                         and _native_parent_descriptor(native_registration, name, parent)
                             is allocation.parent
                         and allocation.ledger.inflight[0] is None)
                allocation.ledger.inflight[0] = allocation
            fd = open_call(name, flags, dir_fd=parent)
            if allocation is not None:
                allocation.raw[0] = fd  # actual return, before wrapper/receipt allocation
            _require(type(fd) is int and fd >= 0)
            if allocation is None:
                row.fd = fd
            else:
                descriptor = _NativeOpenedDescriptor(allocation, fd, allocation.close)
                opened_result = (allocation, descriptor)
                _require(records is s.records and len(records) == len(record_prefix)
                         and all(actual is original for actual, original in
                                 zip(records, record_prefix, strict=True))
                         and records[record_index] is allocation.pending
                         and allocation.close.state[0] is False
                         and allocation.close.state[1] is False
                         and allocation.close.raw[0] is allocation.close.unset
                         and allocation.close.result[0] is None)
                allocation.result[0] = opened_result
                records[record_index] = descriptor
                row = descriptor
                _require(allocation.ledger.inflight[0] is allocation)
                allocation.ledger.inflight[0] = None
            _require(_native_walk_scope(self, native_registration) is s)
            _native_registration_tail(self, s, owner_cell, root_cell,
                                      native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            if allocation is not None:
                _require(_native_file_allocation_original(
                             allocation, native_registration.native_ledger) is allocation.close
                         and allocation.raw[0] is fd and allocation.result[0] is opened_result
                         and records is s.records and records[record_index] is row
                         and row is descriptor and row.close.state[0] is False
                         and row.close.state[1] is False
                         and row.close.raw[0] is row.close.unset and row.close.result[0] is None)
            return row, fd
        except BaseException:
            _descriptor_refused(row)
            self._unknown = True
            if allocation is not None:
                allocation.refused[0] = True
                if allocation.ledger.inflight[0] is allocation:
                    allocation.ledger.inflight[0] = None
                if type(fd) is int and allocation.raw[0] is fd:
                    try:
                        _close_native_file_known(self, allocation, fd,
                                                 native_registration.native_ledger)
                    except BaseException:
                        allocation.close.state[1] = True
                if allocation.ledger.failure[0] is None:
                    allocation.ledger.failure[0] = allocation
                allocation.ledger.failed[0] = True
            elif type(fd) is int and row.fd is fd and row.close_attempted is False:
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    _descriptor_refused(row)
                    self._unknown = True
            raise

    def _close(self, row, fd, s, root_cell):
        if type(row) is _NativeOpenedDescriptor:
            _require(type(s) is _Scope and type(row.allocation) is _NativeOpenAllocation
                     and row.allocation.scope is s and row.allocation.owner is self
                     and type(row.allocation.registration) is _NativeScopeRegistration)
            registration = row.allocation.registration
            _require(registration.scope is s and registration.owner is self
                     and registration.lineage is s.native_files
                     and type(registration.type_pins) is tuple and len(registration.type_pins) == 3
                     and all(type(pin) is type for pin in registration.type_pins)
                     and type(s.native_files) is registration.type_pins[0]
                     and type(registration.native_ledger) is registration.type_pins[1]
                     and s.native_files.ledger is registration.native_ledger
                     and row.fd is fd
                     and _native_descriptor_opened(row, registration.native_ledger) is row.close)
            _close_native_file_known(self, row.allocation, fd, registration.native_ledger)
            return
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
            _descriptor_refused(row)
            self._unknown = True
            raise

    def _read(self, fd, count, s, native_registration=None, consumer=None):
        native = _capture_native_work_origin(self, native_registration)
        read_call = None if native is None else native.operations[1]
        _require(type(s) is _Scope)
        _native_descriptor_argument(s, fd)
        if type(self) is StartupArtifactOwner:
            _require(self._ready is False and self._attempt_cell is not None)
        _require(_native_walk_scope(self, native_registration) is s and type(count) is int
                 and 0 < count <= 65536 and type(self._bytes_read) is int)
        before, cell = self._bytes_read, self._count_cell
        _require(type(cell) is tuple and len(cell) == 3 and cell[0] is self
                 and cell[1] is s and type(cell[2]) is int and cell[2] == before)
        root, owner_cell = self._root_cell, self._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(self, s, owner_cell, root, native_registration, registry)
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
        if consumer is not None:
            _require(type(consumer) is _NativeReadConsumer and native is not None
                     and consumer.owner is self and consumer.scope is s
                     and consumer.before_count is cell and consumer.requested is count
                     and type(consumer.descriptor) is _NativeOpenedDescriptor
                     and consumer.descriptor.fd is fd
                     and type(consumer.effect) is list and len(consumer.effect) == 1
                     and consumer.effect[0] is None and type(effect) is _ReadEffect)
            consumer.effect[0] = effect
        self._reading = True
        data = None
        operation = envelope = None
        failed_native = False
        try:
            _native_registration_tail(self, s, owner_cell, root, native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            _require(native is None or read_call is native.operations[1])
            if native is None:
                read_call = os.read
            if native is not None and consumer is None:
                held_state = _native_pre_actor_state(self, (fd, count, read_call))
                _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
                _native_post_actor_state(self, held_state, (fd, count, read_call))
                _native_registration_tail(self, s, owner_cell, root,
                                          native_registration, registry)
                _native_work_origin_tail(self, native_registration, native)
                _require(read_call is native.operations[1] and self._count_cell is cell
                         and self._bytes_read is before and self._reading is True
                         and (effect is None or (effect.before is cell and effect.after is None
                              and effect.returned is False and effect.unknown is False
                              and s.reads[read_index] is effect)))
            if consumer is not None:
                operation = _prepare_native_read_operation(self, consumer)
                _require(_admit_native_read(self, consumer, operation) is operation)
                _require(read_call is operation.callee
                         and _native_read_ready_tail(self, consumer, operation) is operation)
            data = read_call(fd, count)
            if operation is not None:
                operation.result.raw[0] = data  # actual C return before any result allocation
                operation.ended[0] = True
                operation.state[1] = True
            _require(type(data) is bytes)
            if operation is not None:
                operation.result.length[0] = len(data)
                operation.result.category[0] = 'returned_bytes'
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
            if operation is not None:
                result_claim = operation.result
                consumer.progress[0] = after_cell
                step = consumer.file_step
                envelope = _NativeReadResult(
                    operation, result_claim, consumer, data, after_cell, step,
                    effect, read_index, source_read, type(source_read), source_return,
                    consumer.committed, consumer.consumption, consumer.effect, result_claim.raw,
                    result_claim.length, result_claim.category,
                    result_claim.acknowledged, consumer.result, consumer.operation,
                    consumer.progress, step.progress, result_claim.attempt, result_claim.envelope)
                result_claim.envelope[0] = envelope
                ledger, phase = operation.ledger, operation.registration.native_phase
                _require(same and ledger.inflight[0] is operation
                         and phase.current[0] is phase.active and phase.result[0] is operation)
                ledger.inflight[0] = None
                phase.current[0] = phase.pending
                _require(_native_read_result_current(self, envelope) is s)
                return envelope
            _require(same and (effect is None or (len(s.reads) == read_index + 1
                      and s.reads[read_index] is effect))
                     and len(data) <= count
                     and _native_walk_scope(self, native_registration) is s
                     and self._bytes_read is after and self._count_cell is after_cell
                     and (source_read is None or
                          (source_read.result[0] is source_return
                           and source_read.root.reads[-1] is source_read)))
            _native_registration_tail(self, s, owner_cell, root, native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            return data
        except BaseException as error:
            if consumer is None:
                self._unknown = True
                if effect is not None:
                    effect.unknown = True
                raise
            failed_native = True
            clean_unadmitted = False
            if operation is not None:
                ledger, phase = operation.ledger, operation.registration.native_phase
                clean_unadmitted = (type(error) is _NativeActorMismatchError
                                    and operation.state[0] is False and ledger.failed[0] is False
                                    and phase.current[0] is phase.idle
                                    and phase.result[0] is None and ledger.inflight[0] is None
                                    and ledger.counts is operation.budget[0]
                                    and ledger.counts[0] is operation.budget[1]
                                    and ledger.counts[1] is operation.budget[2])
                if clean_unadmitted:
                    # No native read was admitted. Keep the prepared records as
                    # evidence and retire this reader; do not invent an unknown
                    # read or reuse its unfinished digest/cursor preparation.
                    self._failed = True
                    self._reading = False
                else:
                    operation.ended[0] = True
                    try:
                        _abandon_native_read(self, operation, data, envelope)
                    except BaseException:
                        operation.state[2] = True
                        ledger.failed[0] = True
            if not clean_unadmitted:
                self._unknown = True
                if effect is not None:
                    effect.unknown = True
        finally:
            data = envelope = None
        if failed_native:
            raise ArtifactObservationError(self) from None

    def _stat(self, name, parent, s, native_registration=None):
        native = _capture_native_work_origin(self, native_registration)
        stat_call = None if native is None else native.operations[3]
        result_type = None if native is None else native.result_type
        _require(_native_walk_scope(self, native_registration) is s)
        root, cell = self._root_cell, self._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_relative_arguments(s, name, parent)
        _native_work_origin_tail(self, native_registration, native)
        _require(native is None or stat_call is native.operations[3])
        _require(native is None or result_type is native.result_type)
        if native is None:
            stat_call = os.stat
        if native is not None:
            held_state = _native_pre_actor_state(self, (name, parent, stat_call, result_type))
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
            _native_post_actor_state(self, held_state, (name, parent, stat_call, result_type))
            _native_registration_tail(self, s, cell, root, native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            _require(stat_call is native.operations[3] and result_type is native.result_type)
        value = stat_call(name, dir_fd=parent, follow_symlinks=False)
        _require(type(value) is (os.stat_result if native is None else result_type)
                 and _native_walk_scope(self, native_registration) is s)
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_work_origin_tail(self, native_registration, native)
        return value

    def _fstat(self, fd, s, native_registration=None):
        native = _capture_native_work_origin(self, native_registration)
        fstat_call = None if native is None else native.operations[4]
        result_type = None if native is None else native.result_type
        _require(_native_walk_scope(self, native_registration) is s)
        root, cell = self._root_cell, self._cell
        registry = (None if native_registration is None
                    else native_registration.lineage.ledger.scopes)
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_descriptor_argument(s, fd)
        _native_work_origin_tail(self, native_registration, native)
        _require(native is None or fstat_call is native.operations[4])
        _require(native is None or result_type is native.result_type)
        if native is None:
            fstat_call = os.fstat
        if native is not None:
            held_state = _native_pre_actor_state(self, (fd, fstat_call, result_type))
            _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
            _native_post_actor_state(self, held_state, (fd, fstat_call, result_type))
            _native_registration_tail(self, s, cell, root, native_registration, registry)
            _native_work_origin_tail(self, native_registration, native)
            _require(fstat_call is native.operations[4] and result_type is native.result_type)
        value = fstat_call(fd)
        _require(type(value) is (os.stat_result if native is None else result_type)
                 and _native_walk_scope(self, native_registration) is s)
        _native_registration_tail(self, s, cell, root, native_registration, registry)
        _native_work_origin_tail(self, native_registration, native)
        return value

    def _readlink(self, name, parent, hop, phase, index, before_state, start,
                  native_registration=None):
        native = _capture_native_work_origin(self, native_registration)
        readlink_call = None if native is None else native.operations[5]
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
            _native_registration_tail(self, s, owner_cell, root,
                                      native_registration, native_registry)
            _native_work_origin_tail(self, native_registration, native)
            _require(native is None or readlink_call is native.operations[5])
            if native is None:
                readlink_call = os.readlink
            if native is not None:
                held_state = _native_pre_actor_state(self, (name, parent, hop, readlink_call))
                _native_actor_context(native.actor_calls, (native.native, native.thread_native),
                                      native_registration.context)
                _native_post_actor_state(self, held_state, (name, parent, hop, readlink_call))
                _native_registration_tail(self, s, owner_cell, root,
                                          native_registration, native_registry)
                _native_work_origin_tail(self, native_registration, native)
                _require(readlink_call is native.operations[5] and self._count_cell is start
                         and runtime.count[0] is start and self._reading is True
                         and runtime.reads[position] is record and record.attempted is True
                         and record.returned is False and record.unknown is False)
            data = readlink_call(name, dir_fd=parent)  # bytes input => bytes output
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
            _native_work_origin_tail(self, native_registration, native)
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
                info = StartupArtifactOwner._fstat(self, fd, s, native_registration)
                mode = stat.S_IMODE(info.st_mode)
                _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, s.context[1])
                         and not mode & (stat.S_ISUID | stat.S_ISGID)
                         and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                parents.append((name, parent, fd, _identity(info, True)))
                parent = fd
            name = path.rsplit("/", 1)[1]
            leaf = StartupArtifactOwner._stat(self, name, parent, s, native_registration)
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
            _require(_identity(StartupArtifactOwner._stat(
                self, name, parent, s, native_registration)) == identity)
            for item, ancestor, fd, signature in parents:
                _require(_identity(StartupArtifactOwner._fstat(
                    self, fd, s, native_registration), True) == signature
                         and _identity(StartupArtifactOwner._stat(
                             self, item, ancestor, s, native_registration), True)
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
                    _descriptor_refused(row)
                    self._unknown = True
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
        runtime_source = False
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
                        runtime_source = True
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
        data = digest = native_envelope = native_step = native_commit = None
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
                info = StartupArtifactOwner._fstat(self, fd, s, native_registration)
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
            before = StartupArtifactOwner._stat(self, name, parent, s, native_registration)
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
            _require(_identity(StartupArtifactOwner._fstat(
                self, fd, s, native_registration)) == original)
            digest = hashlib.sha256()
            header = b""
            capture_header = (not anchor and not _configuration(self)
                              and expected.path.endswith(".pyc"))
            remaining = before.st_size if anchor else expected.size
            if (runtime_source or declared_reader is not None) and native_registration is not None:
                _require(type(native_walk) is tuple and len(native_walk) == 5)
                native_step = _new_native_read_file_step(
                    self, native_registration, native_walk[0], expected, row, digest,
                    source_root, source_observations)
            while remaining:
                _require(_native_walk_scope(self, native_registration) is s)
                _require(progress is None or self._count_cell is progress)
                if native_step is not None:
                    native_consumer = _new_native_read_consumer(
                        self, native_step, row, min(remaining, 65536))
                    if declared_reader is None:
                        native_envelope = StartupArtifactOwner._read(
                            self, fd, min(remaining, 65536), s, native_registration,
                            native_consumer)
                        native_commit = _consume_native_runtime_read(self, native_envelope)
                        _native_runtime_read_closed_tail(self, native_commit, native_step)
                    else:
                        native_envelope = declared_reader._read(
                            self, fd, min(remaining, 65536), s, native_registration,
                            native_consumer)
                        native_commit = _consume_native_cache_read(self, native_envelope)
                        _native_cache_read_closed_tail(self, native_commit, native_step)
                        if capture_header:
                            header = native_commit.header
                    _require(native_commit.eof is False)
                    remaining, progress = native_commit.remaining, native_commit.count
                    native_envelope = None
                    continue
                data = (StartupArtifactOwner._read(
                    self, fd, min(remaining, 65536), s, native_registration)
                        if declared_reader is None else
                        declared_reader._read(
                            self, fd, min(remaining, 65536), s, native_registration))
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
            if native_step is not None:
                native_consumer = _new_native_read_consumer(self, native_step, row, 1)
                if declared_reader is None:
                    native_envelope = StartupArtifactOwner._read(
                        self, fd, 1, s, native_registration, native_consumer)
                    native_commit = _consume_native_runtime_read(self, native_envelope)
                    _native_runtime_read_closed_tail(self, native_commit, native_step)
                else:
                    native_envelope = declared_reader._read(
                        self, fd, 1, s, native_registration, native_consumer)
                    native_commit = _consume_native_cache_read(self, native_envelope)
                    _native_cache_read_closed_tail(self, native_commit, native_step)
                    if capture_header:
                        header = native_commit.header
                _require(native_commit.eof is True and native_commit.remaining == 0)
                native_envelope = None
                data = b''  # actual empty return already consumed/ACKed above
            else:
                data = (StartupArtifactOwner._read(self, fd, 1, s, native_registration)
                        if declared_reader is None else
                        declared_reader._read(self, fd, 1, s, native_registration))
                if source_root is not None:
                    source_observations.append(source_digest.capture(source_root))
            if anchor:
                read_effects.append(s.reads[-1])
            count_cell, counted = self._count_cell, self._bytes_read
            _require(data == b"" and _identity(StartupArtifactOwner._fstat(
                self, fd, s, native_registration)) == original
                     and _identity(StartupArtifactOwner._stat(
                         self, name, parent, s, native_registration)) == original)
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
                    _identity(StartupArtifactOwner._fstat(
                        self, directory, s, native_registration), True) == signature
                    and _identity(StartupArtifactOwner._stat(
                        self, name, parent, s, native_registration), True)
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
            if (runtime_source or declared_reader is not None) and native_registration is not None:
                self._failed = self._unknown = True
            if type(native_envelope) is _NativeReadResult:
                try:
                    # Retire only this caller's original still-pending unACKed
                    # result. Completed ACK history must survive later refusal.
                    pending = native_envelope.operation.registration.native_phase
                    if (pending.current[0] is pending.pending
                            and pending.result[0] is native_envelope.operation
                            and native_envelope.ack_cell[0] is None
                            and native_envelope.envelope_cell[0] is native_envelope):
                        _abandon_native_read(self, native_envelope.operation,
                                             native_envelope.raw, native_envelope)
                except BaseException:
                    self._unknown = True
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
            data = digest = header = native_envelope = None
            for row, fd in reversed(held):
                try:
                    StartupArtifactOwner._close(self, row, fd, s, root_cell)
                except BaseException:
                    _descriptor_refused(row)
                    self._unknown = True
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
