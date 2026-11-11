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
from types import BuiltinFunctionType, CodeType, FunctionType, MethodDescriptorType, ModuleType, CellType, GetSetDescriptorType, MethodWrapperType, MemberDescriptorType
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
    native_probe_plan: object = None
    native_probe_origin: object = None
    native_probe_engine_origin: object = None
    native_startup_probe_origin: object = None
    native_link_blueprint: object = None
    native_link_audit: object = None

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
    length: int | None = None
    acknowledgement: object = None
    native_result: object = None


class _ReadlinkObservation(NamedTuple):
    record: _LinkRead
    before: tuple
    after: tuple
    data: bytes

    def __repr__(self):
        return "<OriginalReadlinkObservation DATA redacted>"


class _NativeReadlinkObservation(NamedTuple):
    record: _LinkRead
    before: tuple
    after: tuple
    length: int
    acknowledgement: object
    finish: object

    def __repr__(self):
        return "<NativeReadlinkObservation raw-free original handoff redacted>"


class _LinkSnapshot(NamedTuple):
    source: _RuntimeSource
    phase: int
    links: tuple
    target: tuple
    reads: tuple
    count: tuple
    finishes: tuple = ()

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


def _has_native_link_engine(registration):
    """Schema selection only, never a work or permission verdict."""
    if registration is None:
        return False
    _require(type(registration) is _NativeScopeRegistration
             and type(registration.type_pins) is tuple and len(registration.type_pins) == 3
             and type(registration.lineage) is registration.type_pins[0])
    parent = tuple.__getitem__(registration.lineage, 4)
    _require(type(parent) is tuple and len(parent) == 5
             and type(parent[0]) is tuple and len(parent[0]) in (4, 8))
    return len(parent[0]) == 8


def _native_link_function(owner, registration, name):
    """Select only a retained fixed engine dependency; no late export capture."""
    _require(type(owner) is StartupArtifactOwner and type(name) is str
             and name in ('_snapshot', '_snapshot_history_mirrors', '_make_fact', '_recheck')
             and _has_native_link_engine(registration))
    _native_work_registration_tail(owner, registration)
    parent = tuple.__getitem__(registration.lineage, 4)
    origin = parent[0][4]
    audit_record = parent[0][7]
    _require(type(audit_record) is tuple and len(audit_record) == 3
             and tuple.__getitem__(registration.lineage, 5) is audit_record
             and tuple.__getitem__(registration.scope, 18) is audit_record
             and audit_record[0] is origin and audit_record[1] is parent[0][5])
    _require(type(origin) is tuple and len(origin) == 6 and type(origin[3]) is tuple
             and parent[0][5] is origin[5])
    rows = tuple(row for row in origin[3]
                 if type(row) is tuple and len(row) == 7
                 and type(row[0]) is str and row[0] == '_closed_link_engine_origin')
    _require(len(rows) == 1)
    held = rows[0]
    namespace = held[3]
    module = sys.modules.get('hmp_plugin.presentation_native_metadata')
    _require(type(namespace) is dict and all(type(k) is str for k in namespace)
             and type(module) is ModuleType and vars(module) is namespace
             and type(held[1]) is FunctionType and held[1].__globals__ is namespace
             and namespace.get(held[0]) is held[1] and held[1].__code__ is held[2]
             and held[1].__defaults__ is held[4] is None
             and held[1].__kwdefaults__ is held[5] is None
             and type(held[6]) is tuple and len(held[6]) == 0)
    lookup = _NativeLinkMetadataResource(owner, registration, None, None, None, (), None)
    _require(held[1](owner, lookup) is origin)
    rows = tuple(row for row in origin[2] if row[0] == name)
    _require(len(rows) == 1)
    row = rows[0]
    _require(type(row[1]) is FunctionType and row[1].__code__ is row[2]
             and row[1].__globals__ is row[3] and vars(origin[0]) is row[3]
             and row[3].get(name) is row[1]
             and row[1].__defaults__ is row[4] and row[1].__kwdefaults__ is row[5]
             and parent[0][4] is origin and parent[0][7] is audit_record
             and tuple.__getitem__(registration.lineage, 5) is audit_record
             and tuple.__getitem__(registration.scope, 18) is audit_record)
    return row[1]


def _link_reads_current(source, snapshot):
    _require(type(snapshot) is _LinkSnapshot and snapshot.source is source
             and type(snapshot.phase) is int and snapshot.phase in (0, 1)
             and type(snapshot.reads) is tuple
             and len(snapshot.reads) == len(source.link.hops))
    _require(type(source.count) is list and len(source.count) == 1
             and type(source.count[0]) is tuple and len(source.count[0]) == 3)
    owner = source.count[0][0]
    _require(type(owner) is StartupArtifactOwner)
    registration = vars(owner).get('_native_scope_registration')
    if _has_native_link_engine(registration):
        check = _native_link_function(owner, registration, '_snapshot_history_mirrors')
        _require(check(owner, registration, source, snapshot) is snapshot)
        return
    _require(type(snapshot.finishes) is tuple and len(snapshot.finishes) == 0)
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




def _closed_file_graph_mirrors(descriptor, original_ledger):
    """Open/close field comparison DATA, not a syscall or original-ledger proof.

    Unintegrated reference for the fresh graph. A caller must independently own
    the original allocation/ledger before it may interpret matching receipt DATA.
    No production close/work/admission path uses this predicate.
    """
    if type(descriptor) is not _NativeOpenedDescriptor or tuple.__len__(descriptor) != 3:
        return False
    allocation, fd, close = (
        tuple.__getitem__(descriptor, 0),
        tuple.__getitem__(descriptor, 1),
        tuple.__getitem__(descriptor, 2),
    )
    if (
        type(fd) is not int
        or fd < 0
        or type(allocation) is not _NativeOpenAllocation
        or tuple.__len__(allocation) != 14
        or tuple.__getitem__(allocation, 3) is not original_ledger
    ):
        return False
    registration = tuple.__getitem__(allocation, 2)
    native = tuple.__getitem__(allocation, 6)
    if type(registration) is not _NativeScopeRegistration or tuple.__len__(registration) != 15:
        return False
    pins = tuple.__getitem__(registration, 11)
    if (
        type(pins) is not tuple
        or len(pins) != 3
        or any(type(kind) is not type for kind in pins)
        or type(original_ledger) is not pins[1]
        or type(native) is not pins[2]
    ):
        return False
    # These two families are native NamedTuples. Validate native tuple storage
    # before indexed access; a supplied matching type pin is not that proof.
    for kind, value, width in ((pins[1], original_ledger, 11), (pins[2], native, 9)):
        bases = type.__getattribute__(kind, "__bases__")
        if (
            type(bases) is not tuple
            or len(bases) != 1
            or bases[0] is not tuple
            or tuple.__len__(value) != width
        ):
            return False
    owner, scope = tuple.__getitem__(allocation, 0), tuple.__getitem__(allocation, 1)
    context, index = tuple.__getitem__(allocation, 7), tuple.__getitem__(allocation, 8)
    attempts = tuple.__getitem__(original_ledger, 3)
    operations, actors = tuple.__getitem__(native, 2), tuple.__getitem__(native, 8)
    if (
        tuple.__getitem__(registration, 1) is not owner
        or tuple.__getitem__(registration, 2) is not scope
        or tuple.__getitem__(registration, 9) is not original_ledger
        or tuple.__getitem__(registration, 10) is not native
        or tuple.__getitem__(registration, 5) is not context
        or type(attempts) is not list
        or type(index) is not int
        or not 0 <= index < len(attempts)
        or attempts[index] is not allocation
        or type(close) is not _NativeCloseAllocation
        or tuple.__len__(close) != 15
        or tuple.__getitem__(allocation, 13) is not close
        or type(operations) is not tuple
        or len(operations) != 6
        or type(actors) is not tuple
        or len(actors) != 3
    ):
        return False
    if (
        tuple.__getitem__(close, 0) is not owner
        or tuple.__getitem__(close, 1) is not scope
        or tuple.__getitem__(close, 2) is not registration
        or tuple.__getitem__(close, 3) is not original_ledger
        or tuple.__getitem__(close, 4) is not tuple.__getitem__(registration, 13)
        or tuple.__getitem__(original_ledger, 10) is not tuple.__getitem__(close, 4)
        or tuple.__getitem__(close, 5) is not context
        or tuple.__getitem__(close, 6) is not operations[2]
        or tuple.__getitem__(close, 7) is not actors
    ):
        return False
    actor_modules, opened = tuple.__getitem__(close, 8), tuple.__getitem__(close, 9)
    raw, result, refused = (
        tuple.__getitem__(allocation, 10),
        tuple.__getitem__(allocation, 11),
        tuple.__getitem__(allocation, 12),
    )
    state, closed_raw, closed_result = (
        tuple.__getitem__(close, 11),
        tuple.__getitem__(close, 13),
        tuple.__getitem__(close, 14),
    )
    if (
        type(actor_modules) is not tuple
        or len(actor_modules) != 2
        or actor_modules[0] is not tuple.__getitem__(native, 1)
        or actor_modules[1] is not tuple.__getitem__(native, 7)
        or type(opened) is not list
        or len(opened) != 1
        or opened[0] is not allocation
        or type(raw) is not list
        or len(raw) != 1
        or type(result) is not list
        or len(result) != 1
        or type(refused) is not list
        or len(refused) != 1
        or type(refused[0]) is not bool
        or type(state) is not list
        or len(state) != 2
        or type(state[0]) is not bool
        or type(state[1]) is not bool
        or type(closed_raw) is not list
        or len(closed_raw) != 1
        or type(closed_result) is not list
        or len(closed_result) != 1
    ):
        return False
    observed_open, observed_close = result[0], closed_result[0]
    return (
        raw[0] is fd
        and type(observed_open) is tuple
        and len(observed_open) == 2
        and observed_open[0] is allocation
        and observed_open[1] is descriptor
        and refused[0] is False
        and closed_raw[0] is None
        and state[0] is True
        and state[1] is False
        and type(observed_close) is tuple
        and len(observed_close) == 3
        and observed_close[0] is close
        and observed_close[1] is fd
        and observed_close[2] is None
    )


def _scope_file_graph_mirrors(scope):
    """Unintegrated scope file-closure DATA; not original scope or native authority."""
    if type(scope) is not _Scope or tuple.__len__(scope) != 19:
        return False
    records = tuple.__getitem__(scope, 4)
    if type(records) is not list:
        return False
    native_lineage = tuple.__getitem__(scope, 10)
    if native_lineage is None:
        names = vars(_Descriptor)
        if any(type(key) is not str for key in names):
            return False
        dictionary = names.get("__dict__")
        if (
            type(dictionary) is not GetSetDescriptorType
            or dictionary.__objclass__ is not _Descriptor
            or dictionary.__name__ != "__dict__"
        ):
            return False
        for row in records:
            if type(row) is not _Descriptor:
                return False
            state = dictionary.__get__(row, _Descriptor)
            if (
                type(state) is not dict
                or any(type(key) is not str for key in state)
                or dict.get(state, "closed") is not True
                or (dict.get(state, "close_attempted") is not True)
                or (dict.get(state, "unknown") is not False)
            ):
                return False
    else:
        slot = tuple.__getitem__(scope, 11)
        if (
            type(slot) is not list
            or len(slot) != 1
            or type(slot[0]) is not _NativeScopeRegistration
            or (tuple.__len__(slot[0]) != 15)
        ):
            return False
        registration = slot[0]
        pins = tuple.__getitem__(registration, 11)
        if (
            type(pins) is not tuple
            or len(pins) != 3
            or any(type(kind) is not type for kind in pins)
            or (type(native_lineage) is not pins[0])
        ):
            return False
        bases = type.__getattribute__(pins[0], "__bases__")
        if (
            type(bases) is not tuple
            or len(bases) != 1
            or bases[0] is not tuple
            or (tuple.__len__(native_lineage) != 6)
        ):
            return False
        ledger = tuple.__getitem__(registration, 9)
        if (
            tuple.__getitem__(registration, 2) is not scope
            or tuple.__getitem__(registration, 0) is not native_lineage
            or type(ledger) is not pins[1]
            or (tuple.__getitem__(native_lineage, 3) is not ledger)
        ):
            return False
        for row in records:
            if (
                type(row) is not _NativeOpenedDescriptor
                or tuple.__len__(row) != 3
                or type(tuple.__getitem__(row, 0)) is not _NativeOpenAllocation
                or (tuple.__len__(tuple.__getitem__(row, 0)) != 14)
                or (tuple.__getitem__(tuple.__getitem__(row, 0), 1) is not scope)
            ):
                return False
            if type(row) is not _NativeOpenedDescriptor or tuple.__len__(row) != 3:
                return False
            closed_allocation, closed_fd, closed_close = (
                tuple.__getitem__(row, 0),
                tuple.__getitem__(row, 1),
                tuple.__getitem__(row, 2),
            )
            if (
                type(closed_fd) is not int
                or closed_fd < 0
                or type(closed_allocation) is not _NativeOpenAllocation
                or (tuple.__len__(closed_allocation) != 14)
                or (tuple.__getitem__(closed_allocation, 3) is not ledger)
            ):
                return False
            closed_registration = tuple.__getitem__(closed_allocation, 2)
            closed_native = tuple.__getitem__(closed_allocation, 6)
            if (
                type(closed_registration) is not _NativeScopeRegistration
                or tuple.__len__(closed_registration) != 15
            ):
                return False
            closed_pins = tuple.__getitem__(closed_registration, 11)
            if (
                type(closed_pins) is not tuple
                or len(closed_pins) != 3
                or any(type(closed_kind) is not type for closed_kind in closed_pins)
                or (type(ledger) is not closed_pins[1])
                or (type(closed_native) is not closed_pins[2])
            ):
                return False
            for closed_kind, closed_value, closed_width in (
                (closed_pins[1], ledger, 11),
                (closed_pins[2], closed_native, 9),
            ):
                closed_bases = type.__getattribute__(closed_kind, "__bases__")
                if (
                    type(closed_bases) is not tuple
                    or len(closed_bases) != 1
                    or closed_bases[0] is not tuple
                    or (tuple.__len__(closed_value) != closed_width)
                ):
                    return False
            closed_owner, closed_scope = (
                tuple.__getitem__(closed_allocation, 0),
                tuple.__getitem__(closed_allocation, 1),
            )
            closed_context, closed_index = (
                tuple.__getitem__(closed_allocation, 7),
                tuple.__getitem__(closed_allocation, 8),
            )
            closed_attempts = tuple.__getitem__(ledger, 3)
            closed_operations, closed_actors = (
                tuple.__getitem__(closed_native, 2),
                tuple.__getitem__(closed_native, 8),
            )
            if (
                tuple.__getitem__(closed_registration, 1) is not closed_owner
                or tuple.__getitem__(closed_registration, 2) is not closed_scope
                or tuple.__getitem__(closed_registration, 9) is not ledger
                or (tuple.__getitem__(closed_registration, 10) is not closed_native)
                or (tuple.__getitem__(closed_registration, 5) is not closed_context)
                or (type(closed_attempts) is not list)
                or (type(closed_index) is not int)
                or (not 0 <= closed_index < len(closed_attempts))
                or (closed_attempts[closed_index] is not closed_allocation)
                or (type(closed_close) is not _NativeCloseAllocation)
                or (tuple.__len__(closed_close) != 15)
                or (tuple.__getitem__(closed_allocation, 13) is not closed_close)
                or (type(closed_operations) is not tuple)
                or (len(closed_operations) != 6)
                or (type(closed_actors) is not tuple)
                or (len(closed_actors) != 3)
            ):
                return False
            if (
                tuple.__getitem__(closed_close, 0) is not closed_owner
                or tuple.__getitem__(closed_close, 1) is not closed_scope
                or tuple.__getitem__(closed_close, 2) is not closed_registration
                or (tuple.__getitem__(closed_close, 3) is not ledger)
                or (
                    tuple.__getitem__(closed_close, 4)
                    is not tuple.__getitem__(closed_registration, 13)
                )
                or (tuple.__getitem__(ledger, 10) is not tuple.__getitem__(closed_close, 4))
                or (tuple.__getitem__(closed_close, 5) is not closed_context)
                or (tuple.__getitem__(closed_close, 6) is not closed_operations[2])
                or (tuple.__getitem__(closed_close, 7) is not closed_actors)
            ):
                return False
            closed_actor_modules, closed_opened = (
                tuple.__getitem__(closed_close, 8),
                tuple.__getitem__(closed_close, 9),
            )
            closed_raw, closed_result, closed_refused = (
                tuple.__getitem__(closed_allocation, 10),
                tuple.__getitem__(closed_allocation, 11),
                tuple.__getitem__(closed_allocation, 12),
            )
            closed_state, closed_closed_raw, closed_closed_result = (
                tuple.__getitem__(closed_close, 11),
                tuple.__getitem__(closed_close, 13),
                tuple.__getitem__(closed_close, 14),
            )
            if (
                type(closed_actor_modules) is not tuple
                or len(closed_actor_modules) != 2
                or closed_actor_modules[0] is not tuple.__getitem__(closed_native, 1)
                or (closed_actor_modules[1] is not tuple.__getitem__(closed_native, 7))
                or (type(closed_opened) is not list)
                or (len(closed_opened) != 1)
                or (closed_opened[0] is not closed_allocation)
                or (type(closed_raw) is not list)
                or (len(closed_raw) != 1)
                or (type(closed_result) is not list)
                or (len(closed_result) != 1)
                or (type(closed_refused) is not list)
                or (len(closed_refused) != 1)
                or (type(closed_refused[0]) is not bool)
                or (type(closed_state) is not list)
                or (len(closed_state) != 2)
                or (type(closed_state[0]) is not bool)
                or (type(closed_state[1]) is not bool)
                or (type(closed_closed_raw) is not list)
                or (len(closed_closed_raw) != 1)
                or (type(closed_closed_result) is not list)
                or (len(closed_closed_result) != 1)
            ):
                return False
            closed_observed_open, closed_observed_close = (
                closed_result[0],
                closed_closed_result[0],
            )
            if (
                closed_raw[0] is closed_fd
                and type(closed_observed_open) is tuple
                and (len(closed_observed_open) == 2)
                and (closed_observed_open[0] is closed_allocation)
                and (closed_observed_open[1] is row)
                and (closed_refused[0] is False)
                and (closed_closed_raw[0] is None)
                and (closed_state[0] is True)
                and (closed_state[1] is False)
                and (type(closed_observed_close) is tuple)
                and (len(closed_observed_close) == 3)
                and (closed_observed_close[0] is closed_close)
                and (closed_observed_close[1] is closed_fd)
                and (closed_observed_close[2] is None)
            ) is not True:
                return False
    return True


def _interpreter_graph_mirrors(origin):
    """Interpreter/cache/compiler/decoder DATA; not full native or code authority.

    Unintegrated. Native IO exports, original root/callee provenance and actual
    actor results are separate components. No compiler, loader or decoder runs.
    """
    if type(sys) is not ModuleType:
        return False
    sys_names = vars(sys)
    if any(type(key) is not str for key in sys_names):
        return False
    required = ("modules", "implementation", "version_info", "flags", "hexversion",
                "executable", "prefix", "exec_prefix", "base_prefix", "base_exec_prefix",
                "_stdlib_dir", "platform", "pycache_prefix", "dont_write_bytecode")
    if any(key not in sys_names for key in required):
        return False
    registry = dict.get(sys_names, "modules")
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    module = dict.get(registry, "hmp_startup.gateway_entry")
    if type(module) is not ModuleType:
        return False
    names = vars(module)
    if any(type(key) is not str for key in names):
        return False
    labels = (
        "_InterpreterOrigin",
        "InterpreterStartupData",
        "_CachePolicyOrigin",
        "_SourceHashOrigin",
        "_SourceCompileOrigin",
        "_CacheDecodeOrigin",
    )
    kinds = tuple(dict.get(names, name) for name in labels)
    if any(type(kind) is not type for kind in kinds):
        return False
    for kind in kinds:
        bases = type.__getattribute__(kind, "__bases__")
        if type(bases) is not tuple or len(bases) != 1 or bases[0] is not tuple:
            return False
    if type(origin) is not kinds[0] or tuple.__len__(origin) != 11:
        return False
    (
        implementation,
        version,
        flags,
        data,
        bytecode,
        magic,
        cache,
        source_hash,
        compile_source,
        decode,
    ) = (tuple.__getitem__(origin, i) for i in range(10))
    for value, kind, width in (
        (data, kinds[1], 5),
        (cache, kinds[2], 4),
        (source_hash, kinds[3], 8),
        (compile_source, kinds[4], 7),
        (decode, kinds[5], 8),
    ):
        if type(value) is not kind or tuple.__len__(value) != width:
            return False
    implementation_kind = dict.get(names, "SimpleNamespace")
    version_kind, flags_kind = (
        dict.get(names, "_VERSION_TYPE"),
        dict.get(names, "_FLAGS_TYPE"),
    )
    if (
        any(
            type(kind) is not type
            for kind in (implementation_kind, version_kind, flags_kind)
        )
        or type(implementation) is not implementation_kind
        or type(version) is not version_kind
        or (type(flags) is not flags_kind)
        or (dict.get(sys_names, "implementation") is not implementation)
        or (dict.get(sys_names, "version_info") is not version)
        or (dict.get(sys_names, "flags") is not flags)
    ):
        return False
    for kind in (version_kind, flags_kind):
        bases = type.__getattribute__(kind, "__bases__")
        if type(bases) is not tuple or len(bases) != 1 or bases[0] is not tuple:
            return False
    implementation_names = vars(implementation_kind)
    if any(type(key) is not str for key in implementation_names):
        return False
    dictionary = implementation_names.get("__dict__")
    if (
        type(dictionary) is not MemberDescriptorType
        or dictionary.__objclass__ is not implementation_kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    current = dictionary.__get__(implementation, implementation_kind)
    if type(current) is not dict or any(type(key) is not str for key in current):
        return False
    name, tag, hexversion = (
        dict.get(current, "name"),
        dict.get(current, "cache_tag"),
        dict.get(sys_names, "hexversion"),
    )
    if (
        type(name) is not str
        or not 0 < len(name) <= 128
        or type(tag) is not str
        or (not 0 < len(tag) <= 128)
        or (type(hexversion) is not int)
    ):
        return False
    paths, saved_version, saved_flags, saved_implementation, platform = (
        tuple.__getitem__(data, i) for i in range(5)
    )
    actual_paths = tuple(
        dict.get(sys_names, key)
        for key in (
            "executable",
            "prefix",
            "exec_prefix",
            "base_prefix",
            "base_exec_prefix",
            "_stdlib_dir",
        )
    )
    if type(paths) is not tuple or len(paths) != 6:
        return False
    for old, new in zip(paths, actual_paths, strict=True):
        if (
            type(old) is not str
            or type(new) is not str
            or (not 0 < len(new) <= 4096)
            or (not new.startswith("/"))
            or any(not 32 <= ord(char) != 127 for char in new)
            or (old != new)
        ):
            return False
    if (
        type(saved_version) is not tuple
        or len(saved_version) != 5
        or tuple.__len__(version) != 5
        or any(
            type(saved_version[i]) is not int
            or type(tuple.__getitem__(version, i)) is not int
            for i in (0, 1, 2, 4)
        )
        or (type(saved_version[3]) is not str)
        or (type(tuple.__getitem__(version, 3)) is not str)
        or (len(tuple.__getitem__(version, 3)) > 32)
        or any(saved_version[i] != tuple.__getitem__(version, i) for i in range(5))
        or (type(saved_flags) is not tuple)
        or (not 0 < len(saved_flags) <= 64)
        or (tuple.__len__(flags) != len(saved_flags))
        or any(type(value) not in (int, bool) for value in saved_flags)
        or any(
            type(tuple.__getitem__(flags, i)) not in (int, bool)
            for i in range(len(saved_flags))
        )
        or any(
            saved_flags[i] != tuple.__getitem__(flags, i)
            for i in range(len(saved_flags))
        )
        or (type(saved_implementation) is not tuple)
        or (len(saved_implementation) != 3)
        or (type(saved_implementation[0]) is not str)
        or (type(saved_implementation[1]) is not str)
        or (type(saved_implementation[2]) is not int)
        or (saved_implementation != (name, tag, hexversion))
        or (type(platform) is not str)
        or (type(dict.get(sys_names, "platform")) is not str)
        or (not 0 < len(platform) <= 64)
        or (dict.get(sys_names, "platform") != platform)
    ):
        return False
    loaded = []
    for key in (
        "importlib",
        "importlib.util",
        "_frozen_importlib_external",
        "_imp",
        "builtins",
        "marshal",
    ):
        value = dict.get(registry, key)
        if type(value) is not ModuleType:
            return False
        namespace = vars(value)
        if any(type(key) is not str for key in namespace):
            return False
        loaded.append((value, namespace))
    (
        (importlib_module, importlib_names),
        (util, util_names),
        (frozen, frozen_names),
        (native, native_names),
        (builtin_module, builtin_names),
        (marshal_module, marshal_names),
    ) = loaded
    if (
        dict.get(names, "sys") is not sys
        or dict.get(names, "importlib") is not importlib_module
        or dict.get(names, "_imp") is not native
        or (dict.get(names, "builtins") is not builtin_module)
        or (builtin_module is not builtins)
        or (dict.get(names, "marshal") is not marshal_module)
        or (dict.get(importlib_names, "util") is not util)
        or (dict.get(importlib_names, "_bootstrap_external") is not frozen)
        or (dict.get(registry, "importlib._bootstrap_external") is not frozen)
        or (bytecode is not util)
        or (type(magic) is not bytes)
        or (len(magic) != 4)
        or (dict.get(util_names, "MAGIC_NUMBER") is not magic)
        or (tuple.__getitem__(cache, 0) is not native)
    ):
        return False
    mode, prefix, dont_write = (tuple.__getitem__(cache, i) for i in range(1, 4))
    actual_mode, actual_prefix, actual_write = (
        dict.get(native_names, "check_hash_based_pycs"),
        dict.get(sys_names, "pycache_prefix"),
        dict.get(sys_names, "dont_write_bytecode"),
    )
    if (
        type(mode) is not str
        or type(actual_mode) is not str
        or mode not in ("default", "always", "never")
        or (actual_mode != mode)
        or (type(dont_write) is not bool)
        or (actual_write is not dont_write)
    ):
        return False
    for value in (prefix, actual_prefix):
        if value is not None and (
            type(value) is not str
            or not 0 < len(value) <= 4096
            or (not value.startswith("/"))
            or any(
                not 32 <= ord(char) != 127 or 55296 <= ord(char) <= 57343
                for char in value
            )
            or (len(value.encode("utf-8")) > 4096)
            or (
                value != "/"
                and any(part in ("", ".", "..") for part in value[1:].split("/"))
            )
        ):
            return False
    if prefix != actual_prefix:
        return False
    loader = tuple.__getitem__(source_hash, 1)
    hash_function, hash_code = (
        tuple.__getitem__(source_hash, 2),
        tuple.__getitem__(source_hash, 3),
    )
    compiler_function, compiler_code = (
        tuple.__getitem__(compile_source, 2),
        tuple.__getitem__(compile_source, 3),
    )
    decoder_function, decoder_code = (
        tuple.__getitem__(decode, 1),
        tuple.__getitem__(decode, 2),
    )
    if type(loader) is not type or dict.get(frozen_names, "SourceLoader") is not loader:
        return False
    loader_names = vars(loader)
    if any(type(key) is not str for key in loader_names):
        return False
    for function, code, namespace, key in (
        (hash_function, hash_code, loader_names, "get_code"),
        (compiler_function, compiler_code, loader_names, "source_to_code"),
        (decoder_function, decoder_code, frozen_names, "_compile_bytecode"),
    ):
        if (
            type(function) is not FunctionType
            or type(code) is not CodeType
            or function.__globals__ is not frozen_names
            or (function.__code__ is not code)
            or (namespace.get(key) is not function)
            or (type(function.__module__) is not str)
            or (function.__module__ != "_frozen_importlib_external")
            or (type(code.co_names) is not tuple)
            or any(type(name) is not str for name in code.co_names)
        ):
            return False
    hash_names = hash_code.co_names
    if (
        tuple.__getitem__(source_hash, 0) is not frozen
        or dict.get(frozen_names, "_imp") is not native
        or "source_hash" not in hash_names
    ):
        return False
    if "pyc_magic_number_token" in hash_names:
        if "_RAW_MAGIC_NUMBER" in hash_names:
            return False
        key_owner, key_name = (native, "pyc_magic_number_token")
    else:
        if "_RAW_MAGIC_NUMBER" not in hash_names:
            return False
        key_owner, key_name = (frozen, "_RAW_MAGIC_NUMBER")
    key, actual_key = (
        tuple.__getitem__(source_hash, 7),
        dict.get(native_names if key_owner is native else frozen_names, key_name),
    )
    if (
        tuple.__getitem__(source_hash, 5) is not key_owner
        or type(tuple.__getitem__(source_hash, 6)) is not str
        or tuple.__getitem__(source_hash, 6) != key_name
        or (type(key) is not int)
        or (not 0 <= key < 2**64)
        or (type(actual_key) is not int)
        or (key != actual_key)
        or (tuple.__getitem__(compile_source, 0) is not frozen)
        or (tuple.__getitem__(compile_source, 1) is not loader)
        or (tuple.__getitem__(compile_source, 4) is not builtin_module)
        or (tuple.__getitem__(compile_source, 5) is not builtin_names)
        or (compiler_function.__builtins__ is not builtin_names)
        or ("compile" in frozen_names)
        or ("compile" not in compiler_code.co_names)
        or (tuple.__getitem__(decode, 0) is not frozen)
        or (tuple.__getitem__(decode, 3) is not marshal_module)
        or (tuple.__getitem__(decode, 5) is not CodeType)
        or (tuple.__getitem__(decode, 6) is not native)
        or (dict.get(frozen_names, "marshal") is not marshal_module)
        or (dict.get(frozen_names, "_code_type") is not CodeType)
        or any(
            name not in decoder_code.co_names
            for name in ("marshal", "loads", "_code_type", "_imp", "_fix_co_filename")
        )
    ):
        return False
    for function, owner, namespace, name, module_name in (
        (
            tuple.__getitem__(source_hash, 4),
            native,
            native_names,
            "source_hash",
            "_imp",
        ),
        (
            tuple.__getitem__(compile_source, 6),
            builtin_module,
            builtin_names,
            "compile",
            "builtins",
        ),
        (
            tuple.__getitem__(decode, 4),
            marshal_module,
            marshal_names,
            "loads",
            "marshal",
        ),
        (
            tuple.__getitem__(decode, 7),
            native,
            native_names,
            "_fix_co_filename",
            "_imp",
        ),
    ):
        if (
            type(function) is not BuiltinFunctionType
            or function.__self__ is not owner
            or dict.get(namespace, name) is not function
            or (type(function.__name__) is not str)
            or (function.__name__ != name)
            or (type(function.__module__) is not str)
            or (function.__module__ != module_name)
        ):
            return False
    return True

def _native_io_graph_mirrors(origin):
    """Native API export/metadata DATA; no syscall or original-code authority.

    Unintegrated final-graph component. Fresh actor returns, caller/root/callee
    provenance, work admission and complete post-observation seal remain separate.
    """
    if type(sys) is not ModuleType:
        return False
    sys_names = vars(sys)
    if any(type(key) is not str for key in sys_names):
        return False
    registry = dict.get(sys_names, "modules")
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    entry = dict.get(registry, "hmp_startup.gateway_entry")
    if type(entry) is not ModuleType:
        return False
    entry_names = vars(entry)
    if any(type(key) is not str for key in entry_names):
        return False
    kind = dict.get(entry_names, "_NativeIOOrigin")
    if type(kind) is not type or type(origin) is not kind:
        return False
    bases = type.__getattribute__(kind, "__bases__")
    if (
        type(bases) is not tuple
        or len(bases) != 1
        or bases[0] is not tuple
        or tuple.__len__(origin) != 9
    ):
        return False
    (
        os_module,
        native,
        operations,
        flags,
        result_kind,
        errors,
        thread_module,
        thread_native,
        actors,
    ) = (tuple.__getitem__(origin, i) for i in range(9))
    namespaces = []
    for name, module in (
        ("os", os_module),
        ("posix", native),
        ("builtins", builtins),
        ("threading", thread_module),
        ("_thread", thread_native),
    ):
        if type(module) is not ModuleType or dict.get(registry, name) is not module:
            return False
        namespace = vars(module)
        if any(type(key) is not str for key in namespace):
            return False
        namespaces.append(namespace)
    os_names, native_names, builtin_names, thread_names, thread_native_names = (
        namespaces
    )
    if (
        dict.get(entry_names, "os") is not os_module
        or os_module is not os
        or dict.get(entry_names, "builtins") is not builtins
        or dict.get(entry_names, "threading") is not thread_module
        or thread_module is not threading
        or type(dict.get(os_names, "name")) is not str
        or dict.get(os_names, "name") != "posix"
        or type(operations) is not tuple
        or len(operations) != 6
        or type(flags) is not tuple
        or len(flags) != 5
        or type(errors) is not tuple
        or len(errors) != 3
        or type(actors) is not tuple
        or len(actors) != 3
    ):
        return False
    for name, function in zip(
        ("open", "read", "close", "stat", "fstat", "readlink"), operations, strict=True
    ):
        if (
            type(function) is not BuiltinFunctionType
            or function.__self__ is not native
            or type(function.__name__) is not str
            or function.__name__ != name
            or type(function.__module__) is not str
            or function.__module__ != "posix"
            or dict.get(native_names, name) is not function
            or dict.get(os_names, name) is not function
        ):
            return False
    for index, name in enumerate(
        ("O_RDONLY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK", "O_DIRECTORY")
    ):
        value = flags[index]
        if (
            type(value) is not int
            or (value != 0 if index == 0 else value <= 0)
            or dict.get(native_names, name) is not value
            or dict.get(os_names, name) is not value
        ):
            return False
    if (
        type(result_kind) is not type
        or dict.get(native_names, "stat_result") is not result_kind
        or dict.get(os_names, "stat_result") is not result_kind
        or type(type.__getattribute__(result_kind, "__name__")) is not str
        or type.__getattribute__(result_kind, "__name__") != "stat_result"
    ):
        return False
    base = dict.get(native_names, "error")
    if (
        type(base) is not type
        or dict.get(os_names, "error") is not base
        or dict.get(builtin_names, "OSError") is not base
    ):
        return False
    for name, error_kind in zip(
        ("OSError", "FileNotFoundError", "PermissionError"), errors, strict=True
    ):
        if type(error_kind) is not type:
            return False
        name_value = type.__getattribute__(error_kind, "__name__")
        module_value = type.__getattribute__(error_kind, "__module__")
        mro = type.__getattribute__(error_kind, "__mro__")
        if (
            dict.get(builtin_names, name) is not error_kind
            or type(name_value) is not str
            or name_value != name
            or type(module_value) is not str
            or module_value != "builtins"
            or type(mro) is not tuple
            or not any(value is base for value in mro)
        ):
            return False
    for function, module, namespace, alias, name in (
        (actors[0], native, native_names, os_names, "getpid"),
        (actors[1], native, native_names, os_names, "geteuid"),
        (actors[2], thread_native, thread_native_names, thread_names, "get_ident"),
    ):
        if (
            type(function) is not BuiltinFunctionType
            or function.__self__ is not module
            or type(function.__name__) is not str
            or function.__name__ != name
            or dict.get(namespace, name) is not function
            or dict.get(alias, name) is not function
        ):
            return False
    return True

def _entry_graph_mirrors(binding):
    """Started Entry/invocation/native-storage DATA, not original authority.

    Unintegrated. Interpreter/native API/code provenance, fresh actor results
    and the final whole graph remain separate. No production guard uses this.
    """
    if type(binding) is not tuple or len(binding) != 3:
        return False
    registry = sys.modules
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    module = dict.get(registry, "hmp_startup.gateway_entry")
    if type(module) is not ModuleType:
        return False
    names = vars(module)
    if any(type(key) is not str for key in names):
        return False
    labels = (
        "GatewayEntryOwner",
        "_Invocation",
        "_EntryOrigin",
        "EntryStartupData",
        "_InterpreterOrigin",
        "InterpreterStartupData",
        "_NativeFileLineage",
        "_NativeFileLedger",
        "_NativeFilePhase",
        "_NativeIOOrigin",
    )
    kinds = tuple(dict.get(names, name) for name in labels)
    if any(type(kind) is not type for kind in kinds):
        return False
    (
        owner_kind,
        scope_kind,
        origin_kind,
        data_kind,
        interpreter_kind,
        interpreter_data_kind,
        lineage_kind,
        ledger_kind,
        phase_kind,
        native_kind,
    ) = kinds
    for kind in kinds[1:]:
        bases = type.__getattribute__(kind, "__bases__")
        if type(bases) is not tuple or len(bases) != 1 or bases[0] is not tuple:
            return False
    scope, cell, started = binding
    if (
        type(scope) is not scope_kind
        or tuple.__len__(scope) != 11
        or type(cell) is not tuple
        or len(cell) != 2
        or cell[1] is not scope
        or type(started) is not tuple
        or len(started) != 7
    ):
        return False
    owner = cell[0]
    if type(owner) is not owner_kind:
        return False
    kind_names = vars(owner_kind)
    if any(type(key) is not str for key in kind_names):
        return False
    dictionary = kind_names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not owner_kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    state = dictionary.__get__(owner, owner_kind)
    if (
        type(state) is not dict
        or any(type(key) is not str for key in state)
        or any(
            key not in state
            for key in (
                "_scope",
                "_ready",
                "_failed",
                "_started_cell",
                "_activation",
                "_bootstrap",
            )
        )
    ):
        return False
    activation, bootstrap, origin, data = started[3:]
    if (
        dict.get(names, "_OWNER") is not owner
        or dict.get(names, "_CELL") is not cell
        or dict.get(names, "_STARTED") is not started
        or dict.get(names, "_START_ATTEMPTED") is not True
        or dict.get(state, "_scope") is not scope
        or dict.get(state, "_ready") is not True
        or dict.get(state, "_failed") is not False
        or dict.get(state, "_started_cell") is not started
        or started[0] is not owner
        or started[1] is not scope
        or started[2] is not cell
        or type(activation) is not GatewayActivationOwner
        or dict.get(state, "_activation") is not activation
        or type(bootstrap) is not ModuleType
        or dict.get(state, "_bootstrap") is not bootstrap
        or dict.get(registry, "hermes_bootstrap") is not bootstrap
        or type(origin) is not origin_kind
        or tuple.__len__(origin) != 12
        or dict.get(names, "_ENTRY_ORIGIN") is not origin
        or type(data) is not data_kind
        or tuple.__len__(data) != 8
    ):
        return False
    active_module = dict.get(registry, "hmp_plugin.presentation_gateway_activation")
    if type(active_module) is not ModuleType:
        return False
    active_names = vars(active_module)
    if any(type(key) is not str for key in active_names):
        return False
    active_scope_kind = dict.get(active_names, "_ActivationScope")
    active_cell = dict.get(active_names, "_ENTRY_CELL")
    if (
        type(active_scope_kind) is not type
        or type(active_cell) is not tuple
        or len(active_cell) != 2
        or active_cell[0] is not activation
        or type(active_cell[1]) is not active_scope_kind
    ):
        return False
    bases = type.__getattribute__(active_scope_kind, "__bases__")
    if type(bases) is not tuple or len(bases) != 1 or bases[0] is not tuple:
        return False
    active_scope = active_cell[1]
    if (
        tuple.__len__(active_scope) != 11
        or tuple.__getitem__(active_scope, 4) is not bootstrap
    ):
        return False
    context = tuple.__getitem__(scope, 0)
    interpreter = tuple.__getitem__(scope, 8)
    lineage, ledger = tuple.__getitem__(scope, 9), tuple.__getitem__(scope, 10)
    if (
        type(context) is not tuple
        or len(context) != 3
        or any(type(value) is not int for value in context)
        or type(interpreter) is not interpreter_kind
        or tuple.__len__(interpreter) != 11
        or type(tuple.__getitem__(interpreter, 3)) is not interpreter_data_kind
        or tuple.__len__(tuple.__getitem__(interpreter, 3)) != 5
        or type(lineage) is not lineage_kind
        or tuple.__len__(lineage) != 6
        or type(ledger) is not ledger_kind
        or tuple.__len__(ledger) != 11
    ):
        return False
    native = tuple.__getitem__(interpreter, 10)
    if (
        type(native) is not native_kind
        or tuple.__len__(native) != 9
        or tuple.__getitem__(lineage, 0) is not owner
        or tuple.__getitem__(lineage, 1) is not native
        or tuple.__getitem__(lineage, 2) is not context
        or tuple.__getitem__(lineage, 3) is not ledger
        or tuple.__getitem__(ledger, 0) is not owner
        or tuple.__getitem__(ledger, 1) is not native
        or tuple.__getitem__(ledger, 2) is not context
        or tuple.__getitem__(lineage, 4) is not tuple.__getitem__(origin, 10)
        or tuple.__getitem__(lineage, 5) is not tuple.__getitem__(origin, 11)
    ):
        return False
    policy, record = tuple.__getitem__(origin, 10), tuple.__getitem__(origin, 11)
    if (
        type(policy) is not tuple
        or len(policy) != 5
        or type(policy[0]) is not tuple
        or len(policy[0]) != 8
        or type(record) is not tuple
        or len(record) != 3
        or policy[0][7] is not record
        or record[0] is not policy[0][4]
        or record[1] is not policy[0][5]
    ):
        return False
    expected_data = (
        context,
        tuple.__getitem__(scope, 2),
        tuple.__getitem__(scope, 5),
        tuple.__getitem__(scope, 7),
        tuple.__getitem__(origin, 3),
        tuple.__getitem__(active_scope, 8),
        tuple.__getitem__(active_scope, 9),
        tuple.__getitem__(interpreter, 3),
    )
    if any(
        tuple.__getitem__(data, i) is not value for i, value in enumerate(expected_data)
    ):
        return False
    main = tuple.__getitem__(scope, 1)
    if type(main) is not ModuleType or dict.get(registry, "__main__") is not main:
        return False
    main_names = vars(main)
    if (
        any(type(key) is not str for key in main_names)
        or dict.get(main_names, "__file__") is not tuple.__getitem__(scope, 2)
        or dict.get(main_names, "__spec__") is not tuple.__getitem__(scope, 3)
    ):
        return False
    for current, actual, original in (
        (sys.argv, tuple.__getitem__(scope, 4), tuple.__getitem__(scope, 5)),
        (sys.orig_argv, tuple.__getitem__(scope, 6), tuple.__getitem__(scope, 7)),
    ):
        if (
            current is not actual
            or type(actual) is not list
            or type(original) is not tuple
            or not 1 <= len(actual) <= 256
            or len(actual) != len(original)
            or any(
                type(value) is not str or len(value) > 4096 or "\0" in value
                for value in actual
            )
            or any(type(value) is not str for value in original)
            or any(old != new for old, new in zip(actual, original, strict=True))
        ):
            return False
    # Ledger representation only; phase/receipt authority remains at its consumer.
    attempts, counts, inflight, failed, scopes, failure, preparation, phase = (
        tuple.__getitem__(ledger, i) for i in range(3, 11)
    )
    if (
        type(attempts) is not list
        or len(attempts) > 1048576
        or type(counts) is not list
        or len(counts) != 2
        or any(type(value) is not int for value in counts)
        or not 0 <= counts[0] <= 1048576
        or not 0 <= counts[1] <= 1048576 - counts[0]
        or type(inflight) is not list
        or len(inflight) != 1
        or type(failed) is not list
        or len(failed) != 1
        or type(failed[0]) is not bool
        or type(scopes) is not list
        or len(scopes) > 1048576
        or type(failure) is not list
        or len(failure) != 1
        or type(preparation) is not list
        or len(preparation) != 3
        or type(phase) is not phase_kind
        or tuple.__len__(phase) != 6
    ):
        return False
    markers = tuple(tuple.__getitem__(phase, i) for i in range(4))
    current, result = tuple.__getitem__(phase, 4), tuple.__getitem__(phase, 5)
    return not (
        type(current) is not list
        or len(current) != 1
        or type(result) is not list
        or (len(result) != 1)
        or (not any(current[0] is marker for marker in markers))
        or (
            current[0] is markers[0]
            and (inflight[0] is not None or result[0] is not None)
        )
        or (current[0] is markers[2] and (inflight[0] is not None or result[0] is None))
        or (current[0] is markers[1] and (inflight[0] is None or result[0] is None))
    )

def _activation_graph_mirrors(owner):
    """Settled activation/import DATA, not original provenance or actor proof.

    Unintegrated graph component for the registered startup path. It performs
    no actor or bootstrap call. Original Entry/callee authority and complete
    pre/post-observation live graph qualification remain mandatory.
    """
    registry = sys.modules
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    module = dict.get(registry, "hmp_plugin.presentation_gateway_activation")
    if type(module) is not ModuleType:
        return False
    namespace = vars(module)
    if any(type(key) is not str for key in namespace):
        return False
    kind = dict.get(namespace, "GatewayActivationOwner")
    scope_kind = dict.get(namespace, "_ActivationScope")
    row_kind = dict.get(namespace, "_ModuleOrigin")
    alias_kind = dict.get(namespace, "_AliasOrigin")
    spec_kind = dict.get(namespace, "ModuleSpec")
    if (
        kind is not GatewayActivationOwner
        or any(
            type(value) is not type
            for value in (kind, scope_kind, row_kind, alias_kind, spec_kind)
        )
        or type(owner) is not kind
    ):
        return False
    for tuple_kind in (scope_kind, row_kind, alias_kind):
        bases = type.__getattribute__(tuple_kind, "__bases__")
        if type(bases) is not tuple or len(bases) != 1 or bases[0] is not tuple:
            return False
    names = vars(kind)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    state = dictionary.__get__(owner, kind)
    if (
        type(state) is not dict
        or any(type(key) is not str for key in state)
        or any(
            key not in state
            for key in ("_scope", "_ready", "_uncertain", "_retired", "_capturing")
        )
    ):
        return False
    cell, scope = dict.get(namespace, "_ENTRY_CELL"), dict.get(state, "_scope")
    if (
        dict.get(namespace, "_ENTRY_OWNER") is not owner
        or type(cell) is not tuple
        or len(cell) != 2
        or cell[0] is not owner
        or cell[1] is not scope
        or type(scope) is not scope_kind
        or tuple.__len__(scope) != 11
        or dict.get(state, "_ready") is not True
        or dict.get(state, "_uncertain") is not False
        or dict.get(state, "_retired") is not False
        or dict.get(state, "_capturing") is not False
    ):
        return False
    context, modules, paths, path_values = (
        tuple.__getitem__(scope, i) for i in range(4)
    )
    bootstrap, pm, activate, code = (tuple.__getitem__(scope, i) for i in range(4, 8))
    origins = tuple.__getitem__(scope, 10)
    if (
        type(context) is not tuple
        or len(context) != 3
        or any(type(value) is not int for value in context)
        or modules is not registry
        or paths is not sys.path
        or type(paths) is not list
        or type(path_values) is not tuple
        or len(paths) != len(path_values)
        or any(type(value) is not str for value in paths)
        or any(type(value) is not str for value in path_values)
        or any(old != new for old, new in zip(paths, path_values, strict=True))
        or type(bootstrap) is not ModuleType
        or dict.get(registry, "hermes_bootstrap") is not bootstrap
        or type(pm) is not ModuleType
        or dict.get(registry, "pm.environments") is not pm
        or type(activate) is not FunctionType
        or type(code) is not CodeType
        or activate.__code__ is not code
        or type(origins) is not tuple
    ):
        return False
    pm_names = vars(pm)
    if (
        any(type(key) is not str for key in pm_names)
        or activate.__globals__ is not pm_names
        or dict.get(pm_names, "activate_dependencies") is not activate
    ):
        return False
    typing_module, typing_names = (
        dict.get(namespace, "_TYPING"),
        dict.get(namespace, "_TYPING_NAMESPACE"),
    )
    members, entries = (
        dict.get(namespace, "_TYPING_MEMBERS"),
        dict.get(namespace, "_TYPING_ENTRIES"),
    )
    aliases = dict.get(namespace, "_TYPING_ALIASES")
    if (
        "_MISSING_ALIAS" not in namespace
        or type(typing_module) is not ModuleType
        or dict.get(registry, "typing") is not typing_module
        or type(typing_names) is not dict
        or vars(typing_module) is not typing_names
        or any(type(key) is not str for key in typing_names)
        or type(members) is not tuple
        or type(entries) is not tuple
        or type(aliases) is not tuple
    ):
        return False
    missing = dict.get(namespace, "_MISSING_ALIAS")
    for rows, current in ((members, typing_names), (entries, registry)):
        for row in rows:
            if (
                type(row) is not tuple
                or len(row) != 2
                or type(row[0]) is not str
                or dict.get(current, row[0], missing) is not row[1]
            ):
                return False
    for alias in aliases:
        if (
            type(alias) is not tuple
            or len(alias) != 3
            or type(alias[0]) is not str
            or type(alias[1]) is not str
        ):
            return False
    names = vars(spec_kind)
    if any(type(key) is not str for key in names):
        return False
    spec_dictionary = names.get("__dict__")
    if (
        type(spec_dictionary) is not GetSetDescriptorType
        or spec_dictionary.__objclass__ is not spec_kind
        or spec_dictionary.__name__ != "__dict__"
    ):
        return False
    for row in origins:
        if type(row) is alias_kind:
            if tuple.__len__(row) != 1:
                return False
            binding = tuple.__getitem__(row, 0)
            if not any(binding is alias for alias in aliases):
                return False
            if (
                dict.get(registry, binding[0]) is not binding[2]
                or dict.get(typing_names, binding[1], missing) is not binding[2]
            ):
                return False
            continue
        if type(row) is not row_kind or tuple.__len__(row) != 5:
            return False
        name, observed, file, spec, origin = (
            tuple.__getitem__(row, i) for i in range(5)
        )
        if (
            type(name) is not str
            or type(observed) is not ModuleType
            or (file is not None and type(file) is not str)
            or (origin is not None and type(origin) is not str)
            or dict.get(registry, name) is not observed
        ):
            return False
        observed_names = vars(observed)
        if (
            any(type(key) is not str for key in observed_names)
            or dict.get(observed_names, "__file__") is not file
            or dict.get(observed_names, "__spec__") is not spec
        ):
            return False
        if spec is not None:
            if type(spec) is not spec_kind:
                return False
            spec_names = spec_dictionary.__get__(spec, spec_kind)
            if (
                type(spec_names) is not dict
                or any(type(key) is not str for key in spec_names)
                or dict.get(spec_names, "origin") is not origin
            ):
                return False
    return True

def _approval_graph_mirrors(binding):
    """Operator owner/API/read-chain DATA; not original authority or API result.

    Unintegrated final-graph component. Entry/activation provenance, native
    descriptor closure and actual actor/API observations remain separate.
    No production guard calls this function or treats it as approval admission.
    """
    if type(binding) is not tuple or len(binding) != 4:
        return False
    registry = sys.modules
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    module = dict.get(registry, "hmp_startup.gateway_approval")
    if type(module) is not ModuleType:
        return False
    namespace = vars(module)
    if any(type(key) is not str for key in namespace):
        return False
    kind = dict.get(namespace, "GatewayApprovalOwner")
    source_kind = dict.get(namespace, "_RootSource")
    data_kind = dict.get(namespace, "GatewayOperatorApproval")
    spec_kind = dict.get(namespace, "ModuleSpec")
    if any(
        type(value) is not type for value in (kind, source_kind, data_kind, spec_kind)
    ):
        return False
    scope, cell, root, fact = binding
    if (
        type(scope) is not _Scope
        or tuple.__len__(scope) != 19
        or type(cell) is not tuple
        or len(cell) != 2
        or type(root) is not tuple
        or len(root) != 4
        or type(fact) is not tuple
        or len(fact) != 6
    ):
        return False
    owner = cell[0]
    if type(owner) is not kind or cell[1] is not scope:
        return False
    names = vars(kind)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    state = dictionary.__get__(owner, kind)
    required = (
        "_origin",
        "_scope",
        "_cell",
        "_root_cell",
        "_ready",
        "_failed",
        "_unknown",
        "_reading",
        "_fact_cell",
        "_data",
        "_count_cell",
        "_bytes_read",
        "_buffer",
    )
    if (
        type(state) is not dict
        or any(type(key) is not str for key in state)
        or any(key not in state for key in required)
    ):
        return False
    activation = tuple.__getitem__(scope, 0)
    activation_scope = tuple.__getitem__(scope, 1)
    context = tuple.__getitem__(scope, 3)
    records = tuple.__getitem__(scope, 4)
    source = tuple.__getitem__(scope, 5)
    reads = tuple.__getitem__(scope, 7)
    expected = tuple.__getitem__(scope, 2)
    if (
        type(activation) is not GatewayActivationOwner
        or type(context) is not tuple
        or len(context) != 3
        or any(type(value) is not int for value in context)
        or type(records) is not list
        or type(reads) is not list
        or type(expected) is not tuple
        or len(expected) != 1
        or type(expected[0]) is not OperatorApprovalPath
        or tuple.__len__(expected[0]) != 1
        or type(tuple.__getitem__(expected[0], 0)) is not str
        or type(source) is not source_kind
    ):
        return False
    bases = type.__getattribute__(source_kind, "__bases__")
    if (
        type(bases) is not tuple
        or len(bases) != 1
        or bases[0] is not tuple
        or tuple.__len__(source) != 12
    ):
        return False
    names = vars(GatewayActivationOwner)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not GatewayActivationOwner
        or dictionary.__name__ != "__dict__"
    ):
        return False
    active = dictionary.__get__(activation, GatewayActivationOwner)
    if type(active) is not dict or any(type(key) is not str for key in active):
        return False
    if (
        dict.get(namespace, "_OWNER") is not owner
        or dict.get(namespace, "_CELL") is not cell
        or dict.get(namespace, "_ROOT") is not root
        or dict.get(namespace, "_FACT") is not fact
        or dict.get(state, "_origin") is not scope
        or dict.get(state, "_scope") is not scope
        or dict.get(state, "_cell") is not cell
        or dict.get(state, "_root_cell") is not root
        or dict.get(state, "_ready") is not True
        or dict.get(state, "_failed") is not False
        or dict.get(state, "_unknown") is not False
        or dict.get(state, "_reading") is not False
        or dict.get(state, "_fact_cell") is not fact
        or dict.get(state, "_data") is not fact[2]
        or root[0] is not activation
        or root[1] is not owner
        or root[2] is not scope
        or type(root[3]) is not tuple
        or len(root[3]) != 2
        or root[3][0] is not owner
        or type(root[3][1]) is not bytearray
        or len(root[3][1]) != 0
        or dict.get(state, "_buffer") is not root[3][1]
        or dict.get(active, "_scope") is not activation_scope
        or dict.get(active, "_retired") is not False
        or dict.get(active, "_uncertain") is not False
        or dict.get(active, "_approval_owner") is not owner
        or dict.get(active, "_approval_cell") is not root
        or dict.get(active, "_approval_fact_cell") is not fact
        or fact[0] is not owner
        or fact[1] is not scope
        or type(fact[2]) is not data_kind
    ):
        return False
    count, receipt, pin = fact[3:]
    if (
        type(count) is not tuple
        or len(count) != 3
        or count[0] is not owner
        or count[1] is not scope
        or type(count[2]) is not int
        or not 0 < count[2] <= 4096
        or dict.get(state, "_count_cell") is not count
        or type(dict.get(state, "_bytes_read")) is not int
        or dict.get(state, "_bytes_read") != count[2]
        or type(receipt) is not _OperatorFileReceipt
        or tuple.__len__(receipt) != 8
        or tuple.__getitem__(receipt, 0) is not owner
        or tuple.__getitem__(receipt, 1) is not scope
        or tuple.__getitem__(receipt, 2) is not expected[0]
        or tuple.__getitem__(receipt, 5) is not count
        or type(pin) is not ExpectedArtifact
        or tuple.__len__(pin) != 3
        or tuple.__getitem__(pin, 0) is not tuple.__getitem__(expected[0], 0)
        or type(tuple.__getitem__(pin, 1)) is not int
        or tuple.__getitem__(pin, 1) != count[2]
        or tuple.__getitem__(pin, 2) is not tuple.__getitem__(receipt, 4)
    ):
        return False
    identity = tuple.__getitem__(receipt, 3)
    descriptors, read_rows = (
        tuple.__getitem__(receipt, 6),
        tuple.__getitem__(receipt, 7),
    )
    if (
        type(identity) is not tuple
        or len(identity) != 9
        or any(type(value) is not int for value in identity)
        or identity[6] != count[2]
        or type(descriptors) is not tuple
        or len(descriptors) != len(records)
        or not records
        or any(old is not new for old, new in zip(descriptors, records, strict=True))
        or type(read_rows) is not tuple
        or len(read_rows) != len(reads)
        or len(reads) < 2
        or any(old is not new for old, new in zip(read_rows, reads, strict=True))
    ):
        return False
    names = vars(_ReadEffect)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not _ReadEffect
        or dictionary.__name__ != "__dict__"
    ):
        return False
    previous, previous_cell = 0, None
    for effect in read_rows:
        if type(effect) is not _ReadEffect:
            return False
        current = dictionary.__get__(effect, _ReadEffect)
        if (
            type(current) is not dict
            or any(type(key) is not str for key in current)
            or dict.get(current, "returned") is not True
            or dict.get(current, "unknown") is not False
        ):
            return False
        before, after = dict.get(current, "before"), dict.get(current, "after")
        if (
            type(before) is not tuple
            or len(before) != 3
            or before[0] is not owner
            or before[1] is not scope
            or type(before[2]) is not int
            or before[2] != previous
            or (previous_cell is not None and before is not previous_cell)
            or type(after) is not tuple
            or len(after) != 3
            or after[0] is not owner
            or after[1] is not scope
            or type(after[2]) is not int
            or after[2] < previous
        ):
            return False
        previous, previous_cell = after[2], after
    if previous_cell is not count or previous != count[2]:
        return False
    # API namespace/spec/function contents, not an actual API call or root proof.
    api, api_names, function, code = (
        tuple.__getitem__(source, i) for i in (2, 3, 4, 5)
    )
    file, spec, origin, loader = (tuple.__getitem__(source, i) for i in (6, 7, 8, 9))
    native_file = tuple.__getitem__(source, 11)
    if (
        type(api) is not ModuleType
        or type(api_names) is not dict
        or vars(api) is not api_names
        or any(type(key) is not str for key in api_names)
        or type(function) is not FunctionType
        or type(code) is not CodeType
        or type(file) is not str
        or type(native_file) is not str
        or file != native_file
        or type(origin) is not str
        or origin != native_file
        or type(spec) is not spec_kind
        or function.__globals__ is not api_names
        or function.__code__ is not code
        or type(code.co_filename) is not str
        or code.co_filename != native_file
        or dict.get(registry, "hermes_constants") is not api
        or dict.get(api_names, "get_default_hermes_root") is not function
        or dict.get(api_names, "__file__") is not file
        or dict.get(api_names, "__spec__") is not spec
    ):
        return False
    names = vars(spec_kind)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not spec_kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    spec_names = dictionary.__get__(spec, spec_kind)
    if (
        type(spec_names) is not dict
        or any(type(key) is not str for key in spec_names)
        or dict.get(spec_names, "origin") is not origin
        or dict.get(spec_names, "loader") is not loader
    ):
        return False
    entry_binding = tuple.__getitem__(source, 1)
    return (
        type(entry_binding) is tuple
        and len(entry_binding) == 3
        and type(entry_binding[2]) is tuple
        and len(entry_binding[2]) == 7
        and entry_binding[2][0] is tuple.__getitem__(source, 0)
        and entry_binding[2][1] is entry_binding[0]
        and entry_binding[2][2] is entry_binding[1]
        and entry_binding[2][3] is activation
    )

def _cache_context_graph_mirrors(snapshot):
    """Retained cache-context field DATA, not original context or live cwd proof.

    Unintegrated graph component. Native actor, entry/code/root, shared owners,
    cache row semantics and live cwd observations remain separate requirements.
    No guard or admission path uses this predicate.
    """
    registry = sys.modules
    if type(registry) is not dict or any(type(key) is not str for key in registry):
        return False
    namespaces = []
    for name in (
        "hmp_startup.entry_files",
        "hmp_startup.cache_context",
        "hmp_startup.runtime_files",
    ):
        module = dict.get(registry, name)
        if type(module) is not ModuleType:
            return False
        namespace = vars(module)
        if any(type(key) is not str for key in namespace):
            return False
        namespaces.append(namespace)
    entry_names, cache_names, runtime_names = namespaces
    snapshot_kind = dict.get(entry_names, "EntryFileSnapshotOwner")
    input_kind = dict.get(entry_names, "_Inputs")
    cache_kind = dict.get(cache_names, "CacheContextOwner")
    source_kind = dict.get(cache_names, "_ContextSource")
    plan_kind = dict.get(runtime_names, "RuntimeFilePlan")
    if any(
        type(kind) is not type
        for kind in (snapshot_kind, input_kind, cache_kind, source_kind, plan_kind)
    ):
        return False
    if type(snapshot) is not snapshot_kind:
        return False
    names = vars(snapshot_kind)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not snapshot_kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    state = dictionary.__get__(snapshot, snapshot_kind)
    if type(state) is not dict or any(type(key) is not str for key in state):
        return False
    required = ("_inputs", "_root_cell", "_cache_context_cell", "_failed", "_unknown")
    if (
        any(key not in state for key in required)
        or dict.get(state, "_failed") is not False
        or dict.get(state, "_unknown") is not False
    ):
        return False
    inputs = dict.get(state, "_inputs")
    if type(inputs) is not input_kind:
        return False
    bases = type.__getattribute__(input_kind, "__bases__")
    if (
        type(bases) is not tuple
        or len(bases) != 1
        or bases[0] is not tuple
        or tuple.__len__(inputs) != 16
    ):
        return False
    slot = tuple.__getitem__(inputs, 15)
    if type(slot) is not list or len(slot) != 1 or type(slot[0]) is not tuple or len(slot[0]) != 4:
        return False
    fact = slot[0]
    owner = fact[0]
    if type(owner) is not cache_kind:
        return False
    names = vars(cache_kind)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not cache_kind
        or dictionary.__name__ != "__dict__"
    ):
        return False
    current = dictionary.__get__(owner, cache_kind)
    if type(current) is not dict or any(type(key) is not str for key in current):
        return False
    required = ("_source", "_root", "_failed", "_retired", "_ready", "_fact", "_cwd", "_rows")
    if any(key not in current for key in required):
        return False
    source, root = dict.get(current, "_source"), dict.get(current, "_root")
    if (
        dict.get(cache_names, "_OWNER") is not owner
        or dict.get(cache_names, "_ROOT") is not root
        or dict.get(cache_names, "_FACT") is not fact
        or dict.get(current, "_failed") is not False
        or dict.get(current, "_retired") is not False
        or dict.get(current, "_ready") is not True
        or dict.get(current, "_fact") is not fact
        or type(root) is not tuple
        or len(root) != 2
        or root[0] is not owner
        or root[1] is not source
        or fact[1] is not root
        or fact[2] is not dict.get(current, "_cwd")
        or fact[3] is not dict.get(current, "_rows")
        or type(fact[3]) is not tuple
        or type(source) is not source_kind
    ):
        return False
    bases = type.__getattribute__(source_kind, "__bases__")
    if (
        type(bases) is not tuple
        or len(bases) != 1
        or bases[0] is not tuple
        or tuple.__len__(source) != 9
    ):
        return False
    cell, plan = tuple.__getitem__(source, 2), tuple.__getitem__(source, 3)
    if (
        tuple.__getitem__(source, 0) is not snapshot
        or tuple.__getitem__(source, 1) is not inputs
        or type(cell) is not tuple
        or len(cell) != 2
        or cell[0] is not snapshot
        or cell[1] is not inputs
        or dict.get(state, "_root_cell") is not cell
        or dict.get(state, "_cache_context_cell") is not root
        or tuple.__getitem__(inputs, 12) is not plan
        or type(plan) is not plan_kind
    ):
        return False
    bases = type.__getattribute__(plan_kind, "__bases__")
    if (
        type(bases) is not tuple
        or len(bases) != 1
        or bases[0] is not tuple
        or tuple.__len__(plan) != 15
    ):
        return False
    if (
        tuple.__getitem__(plan, 0) is not tuple.__getitem__(inputs, 1)
        or tuple.__getitem__(plan, 1) is not tuple.__getitem__(inputs, 3)
        or tuple.__getitem__(plan, 2) is not tuple.__getitem__(inputs, 5)
    ):
        return False
    recipe_binding = tuple.__getitem__(inputs, 3)
    if type(recipe_binding) is not tuple or len(recipe_binding) != 6:
        return False
    scope = recipe_binding[0]
    if type(scope) is not _Scope or tuple.__len__(scope) != 19:
        return False
    activation = tuple.__getitem__(scope, 0)
    if type(activation) is not GatewayActivationOwner:
        return False
    names = vars(GatewayActivationOwner)
    if any(type(key) is not str for key in names):
        return False
    dictionary = names.get("__dict__")
    if (
        type(dictionary) is not GetSetDescriptorType
        or dictionary.__objclass__ is not GatewayActivationOwner
        or dictionary.__name__ != "__dict__"
    ):
        return False
    active = dictionary.__get__(activation, GatewayActivationOwner)
    if (
        type(active) is not dict
        or any(type(key) is not str for key in active)
        or dict.get(active, "_entry_files_owner") is not snapshot
        or dict.get(active, "_entry_files_cell") is not cell
    ):
        return False
    # Getter metadata only. Never invoke cwd from a retained comparison.
    requires, getter = tuple.__getitem__(source, 5), tuple.__getitem__(source, 6)
    os_module, posix_module = tuple.__getitem__(source, 7), tuple.__getitem__(source, 8)
    if requires is False:
        return getter is os_module is posix_module is None
    if (
        requires is not True
        or type(getter) is not BuiltinFunctionType
        or type(os_module) is not ModuleType
        or type(posix_module) is not ModuleType
    ):
        return False
    namespace, original = vars(os_module), vars(posix_module)
    if any(type(key) is not str for key in namespace) or any(
        type(key) is not str for key in original
    ):
        return False
    return (
        os_module is dict.get(cache_names, "os")
        and dict.get(registry, "os") is os_module
        and dict.get(registry, "posix") is posix_module
        and dict.get(namespace, "getcwd") is getter
        and dict.get(original, "getcwd") is getter
        and getter.__self__ is posix_module
        and type(getter.__name__) is str
        and getter.__name__ == "getcwd"
        and type(getter.__module__) is str
        and getter.__module__ == "posix"
    )

def _loaded_owner_graph_mirrors(package_binding, recipe_binding):
    """Fresh shared-node field comparison DATA, never a guard or admission.

    Unintegrated RGA component. Original-root/callee authentication, descriptor,
    approval/cache/entry/actor checks and the complete final DAG remain required.
    Consistent supplied bindings do not establish original-object provenance.
    No production caller may replace a complete validator with this predicate.
    """
    if (
        type(package_binding) is not tuple
        or len(package_binding) != 5
        or type(recipe_binding) is not tuple
        or len(recipe_binding) != 6
    ):
        return False
    selected = package_binding[4]
    if (
        type(selected) is not tuple
        or len(selected) != 4
        or type(recipe_binding[5]) is not tuple
        or len(recipe_binding[5]) != 4
        or any(left is not right for left, right in zip(selected, recipe_binding[5], strict=True))
    ):
        return False
    modules = sys.modules
    if type(modules) is not dict or any(type(key) is not str for key in modules):
        return False
    specifications = (
        (
            "hmp_plugin.presentation_gateway_package",
            "GatewayPackageOwner",
            package_binding,
            "_package_owner",
            "_package_cell",
            "_package_fact_cell",
        ),
        (
            "hmp_plugin.presentation_gateway_recipe",
            "GatewayRecipeOwner",
            recipe_binding,
            "_recipe_owner",
            "_recipe_cell",
            "_recipe_fact_cell",
        ),
        (
            "hmp_plugin.presentation_startup_selection",
            "StartupSelectionOwner",
            selected,
            "_selection_owner",
            "_selection_cell",
            "_selection_fact_cell",
        ),
    )
    activation = activation_scope = None
    for module_name, class_name, binding, owner_key, root_key, fact_key in specifications:
        module = dict.get(modules, module_name)
        if type(module) is not ModuleType:
            return False
        namespace = vars(module)
        if any(type(key) is not str for key in namespace):
            return False
        kind = dict.get(namespace, class_name)
        if type(kind) is not type:
            return False
        names = vars(kind)
        if any(type(key) is not str for key in names):
            return False
        dictionary = names.get("__dict__")
        if (
            type(dictionary) is not GetSetDescriptorType
            or dictionary.__objclass__ is not kind
            or dictionary.__name__ != "__dict__"
        ):
            return False
        scope, cell, root = binding[:3]
        if (
            type(scope) is not _Scope
            or tuple.__len__(scope) != 19
            or type(cell) is not tuple
            or len(cell) != 2
            or type(root) is not tuple
            or len(root) not in (3, 4)
        ):
            return False
        owner = cell[0]
        if type(owner) is not kind or cell[1] is not scope:
            return False
        state = dictionary.__get__(owner, kind)
        if type(state) is not dict or any(type(key) is not str for key in state):
            return False
        required = (
            "_origin",
            "_scope",
            "_cell",
            "_root_cell",
            "_ready",
            "_failed",
            "_unknown",
            "_reading",
            "_count_cell",
            "_bytes_read",
        )
        if module_name == "hmp_plugin.presentation_gateway_package":
            required += ("_fact_cell", "_fact")
        elif module_name == "hmp_plugin.presentation_gateway_recipe":
            required += ("_plan_cell", "_fact_cell", "_active", "_buffer")
        else:
            required += ("_selection_cell", "_selection", "_buffer")
        if any(key not in state for key in required):
            return False
        current_activation = tuple.__getitem__(scope, 0)
        current_activation_scope = tuple.__getitem__(scope, 1)
        if activation is None:
            activation, activation_scope = current_activation, current_activation_scope
        if (
            current_activation is not activation
            or current_activation_scope is not activation_scope
            or type(activation) is not GatewayActivationOwner
        ):
            return False
        activation_names = vars(GatewayActivationOwner)
        if any(type(key) is not str for key in activation_names):
            return False
        activation_dictionary = activation_names.get("__dict__")
        if (
            type(activation_dictionary) is not GetSetDescriptorType
            or activation_dictionary.__objclass__ is not GatewayActivationOwner
            or activation_dictionary.__name__ != "__dict__"
        ):
            return False
        active = activation_dictionary.__get__(activation, GatewayActivationOwner)
        if type(active) is not dict or any(type(key) is not str for key in active):
            return False
        if (
            dict.get(state, "_origin") is not scope
            or dict.get(state, "_scope") is not scope
            or dict.get(state, "_cell") is not cell
            or dict.get(state, "_root_cell") is not root
            or dict.get(state, "_ready") is not True
            or dict.get(state, "_failed") is not False
            or dict.get(state, "_unknown") is not False
            or dict.get(state, "_reading") is not False
            or root[0] is not activation
            or root[1] is not owner
            or root[2] is not scope
            or dict.get(active, "_scope") is not activation_scope
            or dict.get(active, "_retired") is not False
            or dict.get(active, "_uncertain") is not False
            or dict.get(active, owner_key) is not owner
            or dict.get(active, root_key) is not root
            or type(tuple.__getitem__(scope, 3)) is not tuple
            or len(tuple.__getitem__(scope, 3)) != 3
            or any(type(value) is not int for value in tuple.__getitem__(scope, 3))
            or type(tuple.__getitem__(scope, 4)) is not list
        ):
            return False
        if module_name == "hmp_plugin.presentation_gateway_package":
            fact = binding[3]
            if (
                len(root) != 3
                or type(fact) is not tuple
                or len(fact) != 3
                or fact[0] is not owner
                or fact[1] is not scope
                or dict.get(state, "_fact_cell") is not fact
                or type(fact[2]) is not tuple
                or len(fact[2]) != 8
                or dict.get(state, "_fact") is not fact[2]
            ):
                return False
            count = fact[2][7]
        elif module_name == "hmp_plugin.presentation_gateway_recipe":
            plan, fact = binding[3:5]
            if (
                type(plan) is not tuple
                or len(plan) != 3
                or plan[0] is not owner
                or plan[1] is not scope
                or dict.get(state, "_plan_cell") is not plan
                or dict.get(active, "_recipe_plan_cell") is not plan
                or type(fact) is not tuple
                or len(fact) != 5
                or fact[0] is not owner
                or fact[1] is not scope
                or fact[2] is not plan
                or dict.get(state, "_fact_cell") is not fact
                or dict.get(state, "_active") is not None
            ):
                return False
            count = fact[4]
        else:
            fact = binding[3]
            if (
                type(fact) is not tuple
                or len(fact) != 4
                or fact[0] is not owner
                or fact[1] is not scope
                or dict.get(state, "_selection_cell") is not fact
                or dict.get(state, "_selection") is not fact[2]
            ):
                return False
            count = fact[3]
        if (
            dict.get(active, fact_key) is not fact
            or type(count) is not tuple
            or len(count) != 3
            or count[0] is not owner
            or count[1] is not scope
            or type(count[2]) is not int
            or dict.get(state, "_count_cell") is not count
            or type(dict.get(state, "_bytes_read")) is not int
            or dict.get(state, "_bytes_read") != count[2]
        ):
            return False
        if module_name != "hmp_plugin.presentation_gateway_package":
            if (
                len(root) != 4
                or type(root[3]) is not tuple
                or len(root[3]) != 2
                or root[3][0] is not owner
                or type(root[3][1]) is not bytearray
                or dict.get(state, "_buffer") is not root[3][1]
                or len(root[3][1]) != 0
            ):
                return False
        if module_name == "hmp_plugin.presentation_startup_selection":
            if dict.get(state, "_bytes_read") is not count[2]:
                return False
        # Fresh scan/file mirrors are inline: no project checker callback.
        if module_name == "hmp_plugin.presentation_gateway_package":
            expected = tuple.__getitem__(scope, 2)
            manifest_kind = dict.get(namespace, "_Manifest")
            scan_kind = dict.get(namespace, "_Scan")
            if (
                type(manifest_kind) is not type
                or type(scan_kind) is not type
                or type(expected) is not manifest_kind
            ):
                return False
            bases = type.__getattribute__(manifest_kind, "__bases__")
            if (
                type(bases) is not tuple
                or len(bases) != 1
                or bases[0] is not tuple
                or (tuple.__len__(expected) != 11)
            ):
                return False
            scans = tuple.__getitem__(expected, 8)
            scan_names = vars(scan_kind)
            if type(scans) is not list or any(type(key) is not str for key in scan_names):
                return False
            scan_dictionary = scan_names.get("__dict__")
            if (
                type(scan_dictionary) is not GetSetDescriptorType
                or scan_dictionary.__objclass__ is not scan_kind
                or scan_dictionary.__name__ != "__dict__"
            ):
                return False
            for scan in scans:
                if type(scan) is not scan_kind:
                    return False
                scan_state = scan_dictionary.__get__(scan, scan_kind)
                if (
                    type(scan_state) is not dict
                    or any(type(key) is not str for key in scan_state)
                    or dict.get(scan_state, "closed") is not True
                    or (dict.get(scan_state, "unknown") is not False)
                    or (dict.get(scan_state, "close_attempted") is not True)
                ):
                    return False
        if type(scope) is not _Scope or tuple.__len__(scope) != 19:
            return False
        files_records = tuple.__getitem__(scope, 4)
        if type(files_records) is not list:
            return False
        files_native_lineage = tuple.__getitem__(scope, 10)
        if files_native_lineage is None:
            files_names = vars(_Descriptor)
            if any(type(files_key) is not str for files_key in files_names):
                return False
            files_dictionary = files_names.get("__dict__")
            if (
                type(files_dictionary) is not GetSetDescriptorType
                or files_dictionary.__objclass__ is not _Descriptor
                or files_dictionary.__name__ != "__dict__"
            ):
                return False
            for files_row in files_records:
                if type(files_row) is not _Descriptor:
                    return False
                files_state = files_dictionary.__get__(files_row, _Descriptor)
                if (
                    type(files_state) is not dict
                    or any(type(files_key) is not str for files_key in files_state)
                    or dict.get(files_state, "closed") is not True
                    or (dict.get(files_state, "close_attempted") is not True)
                    or (dict.get(files_state, "unknown") is not False)
                ):
                    return False
        else:
            files_slot = tuple.__getitem__(scope, 11)
            if (
                type(files_slot) is not list
                or len(files_slot) != 1
                or type(files_slot[0]) is not _NativeScopeRegistration
                or (tuple.__len__(files_slot[0]) != 15)
            ):
                return False
            files_registration = files_slot[0]
            files_pins = tuple.__getitem__(files_registration, 11)
            if (
                type(files_pins) is not tuple
                or len(files_pins) != 3
                or any(type(files_kind) is not type for files_kind in files_pins)
                or (type(files_native_lineage) is not files_pins[0])
            ):
                return False
            files_bases = type.__getattribute__(files_pins[0], "__bases__")
            if (
                type(files_bases) is not tuple
                or len(files_bases) != 1
                or files_bases[0] is not tuple
                or (tuple.__len__(files_native_lineage) != 6)
            ):
                return False
            files_ledger = tuple.__getitem__(files_registration, 9)
            if (
                tuple.__getitem__(files_registration, 2) is not scope
                or tuple.__getitem__(files_registration, 0) is not files_native_lineage
                or type(files_ledger) is not files_pins[1]
                or (tuple.__getitem__(files_native_lineage, 3) is not files_ledger)
            ):
                return False
            for files_row in files_records:
                if (
                    type(files_row) is not _NativeOpenedDescriptor
                    or tuple.__len__(files_row) != 3
                    or type(tuple.__getitem__(files_row, 0)) is not _NativeOpenAllocation
                    or (tuple.__len__(tuple.__getitem__(files_row, 0)) != 14)
                    or (tuple.__getitem__(tuple.__getitem__(files_row, 0), 1) is not scope)
                ):
                    return False
                if type(files_row) is not _NativeOpenedDescriptor or tuple.__len__(files_row) != 3:
                    return False
                files_closed_allocation, files_closed_fd, files_closed_close = (
                    tuple.__getitem__(files_row, 0),
                    tuple.__getitem__(files_row, 1),
                    tuple.__getitem__(files_row, 2),
                )
                if (
                    type(files_closed_fd) is not int
                    or files_closed_fd < 0
                    or type(files_closed_allocation) is not _NativeOpenAllocation
                    or (tuple.__len__(files_closed_allocation) != 14)
                    or (tuple.__getitem__(files_closed_allocation, 3) is not files_ledger)
                ):
                    return False
                files_closed_registration = tuple.__getitem__(files_closed_allocation, 2)
                files_closed_native = tuple.__getitem__(files_closed_allocation, 6)
                if (
                    type(files_closed_registration) is not _NativeScopeRegistration
                    or tuple.__len__(files_closed_registration) != 15
                ):
                    return False
                files_closed_pins = tuple.__getitem__(files_closed_registration, 11)
                if (
                    type(files_closed_pins) is not tuple
                    or len(files_closed_pins) != 3
                    or any(
                        type(files_closed_kind) is not type
                        for files_closed_kind in files_closed_pins
                    )
                    or (type(files_ledger) is not files_closed_pins[1])
                    or (type(files_closed_native) is not files_closed_pins[2])
                ):
                    return False
                for files_closed_kind, files_closed_value, files_closed_width in (
                    (files_closed_pins[1], files_ledger, 11),
                    (files_closed_pins[2], files_closed_native, 9),
                ):
                    files_closed_bases = type.__getattribute__(files_closed_kind, "__bases__")
                    if (
                        type(files_closed_bases) is not tuple
                        or len(files_closed_bases) != 1
                        or files_closed_bases[0] is not tuple
                        or (tuple.__len__(files_closed_value) != files_closed_width)
                    ):
                        return False
                files_closed_owner, files_closed_scope = (
                    tuple.__getitem__(files_closed_allocation, 0),
                    tuple.__getitem__(files_closed_allocation, 1),
                )
                files_closed_context, files_closed_index = (
                    tuple.__getitem__(files_closed_allocation, 7),
                    tuple.__getitem__(files_closed_allocation, 8),
                )
                files_closed_attempts = tuple.__getitem__(files_ledger, 3)
                files_closed_operations, files_closed_actors = (
                    tuple.__getitem__(files_closed_native, 2),
                    tuple.__getitem__(files_closed_native, 8),
                )
                if (
                    tuple.__getitem__(files_closed_registration, 1) is not files_closed_owner
                    or tuple.__getitem__(files_closed_registration, 2) is not files_closed_scope
                    or tuple.__getitem__(files_closed_registration, 9) is not files_ledger
                    or (tuple.__getitem__(files_closed_registration, 10) is not files_closed_native)
                    or (tuple.__getitem__(files_closed_registration, 5) is not files_closed_context)
                    or (type(files_closed_attempts) is not list)
                    or (type(files_closed_index) is not int)
                    or (not 0 <= files_closed_index < len(files_closed_attempts))
                    or (files_closed_attempts[files_closed_index] is not files_closed_allocation)
                    or (type(files_closed_close) is not _NativeCloseAllocation)
                    or (tuple.__len__(files_closed_close) != 15)
                    or (tuple.__getitem__(files_closed_allocation, 13) is not files_closed_close)
                    or (type(files_closed_operations) is not tuple)
                    or (len(files_closed_operations) != 6)
                    or (type(files_closed_actors) is not tuple)
                    or (len(files_closed_actors) != 3)
                ):
                    return False
                if (
                    tuple.__getitem__(files_closed_close, 0) is not files_closed_owner
                    or tuple.__getitem__(files_closed_close, 1) is not files_closed_scope
                    or tuple.__getitem__(files_closed_close, 2) is not files_closed_registration
                    or (tuple.__getitem__(files_closed_close, 3) is not files_ledger)
                    or (
                        tuple.__getitem__(files_closed_close, 4)
                        is not tuple.__getitem__(files_closed_registration, 13)
                    )
                    or (
                        tuple.__getitem__(files_ledger, 10)
                        is not tuple.__getitem__(files_closed_close, 4)
                    )
                    or (tuple.__getitem__(files_closed_close, 5) is not files_closed_context)
                    or (tuple.__getitem__(files_closed_close, 6) is not files_closed_operations[2])
                    or (tuple.__getitem__(files_closed_close, 7) is not files_closed_actors)
                ):
                    return False
                files_closed_actor_modules, files_closed_opened = (
                    tuple.__getitem__(files_closed_close, 8),
                    tuple.__getitem__(files_closed_close, 9),
                )
                files_closed_raw, files_closed_result, files_closed_refused = (
                    tuple.__getitem__(files_closed_allocation, 10),
                    tuple.__getitem__(files_closed_allocation, 11),
                    tuple.__getitem__(files_closed_allocation, 12),
                )
                files_closed_state, files_closed_closed_raw, files_closed_closed_result = (
                    tuple.__getitem__(files_closed_close, 11),
                    tuple.__getitem__(files_closed_close, 13),
                    tuple.__getitem__(files_closed_close, 14),
                )
                if (
                    type(files_closed_actor_modules) is not tuple
                    or len(files_closed_actor_modules) != 2
                    or files_closed_actor_modules[0]
                    is not tuple.__getitem__(files_closed_native, 1)
                    or (
                        files_closed_actor_modules[1]
                        is not tuple.__getitem__(files_closed_native, 7)
                    )
                    or (type(files_closed_opened) is not list)
                    or (len(files_closed_opened) != 1)
                    or (files_closed_opened[0] is not files_closed_allocation)
                    or (type(files_closed_raw) is not list)
                    or (len(files_closed_raw) != 1)
                    or (type(files_closed_result) is not list)
                    or (len(files_closed_result) != 1)
                    or (type(files_closed_refused) is not list)
                    or (len(files_closed_refused) != 1)
                    or (type(files_closed_refused[0]) is not bool)
                    or (type(files_closed_state) is not list)
                    or (len(files_closed_state) != 2)
                    or (type(files_closed_state[0]) is not bool)
                    or (type(files_closed_state[1]) is not bool)
                    or (type(files_closed_closed_raw) is not list)
                    or (len(files_closed_closed_raw) != 1)
                    or (type(files_closed_closed_result) is not list)
                    or (len(files_closed_closed_result) != 1)
                ):
                    return False
                files_closed_observed_open, files_closed_observed_close = (
                    files_closed_result[0],
                    files_closed_closed_result[0],
                )
                if (
                    files_closed_raw[0] is files_closed_fd
                    and type(files_closed_observed_open) is tuple
                    and (len(files_closed_observed_open) == 2)
                    and (files_closed_observed_open[0] is files_closed_allocation)
                    and (files_closed_observed_open[1] is files_row)
                    and (files_closed_refused[0] is False)
                    and (files_closed_closed_raw[0] is None)
                    and (files_closed_state[0] is True)
                    and (files_closed_state[1] is False)
                    and (type(files_closed_observed_close) is tuple)
                    and (len(files_closed_observed_close) == 3)
                    and (files_closed_observed_close[0] is files_closed_close)
                    and (files_closed_observed_close[1] is files_closed_fd)
                    and (files_closed_observed_close[2] is None)
                ) is not True:
                    return False
        pass
    return True


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
    # Constructor identity alone does not bind its fields to the retained native
    # result. Check primitive types before comparisons can invoke foreign code.
    _require(type(snapshot) is _NativeMetadataSnapshot
             and type(snapshot.identity) is tuple
             and len(snapshot.identity) == len(identity)
             and all(type(part) is int for part in snapshot.identity)
             and type(snapshot.mtime) is type(mtime))
    _require(all(actual == expected for actual, expected in
                 zip(snapshot.identity, identity, strict=True))
             and snapshot.mtime == mtime)
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
        # Hold the immutable field once, after the exact row/str fences. Strict
        # UTF-8 maps only these ASCII controls to the same forbidden bytes.
        _require(type(row) is ExpectedArtifact and type(path := row.path) is str
                 and 1 < len(encoded := path.encode("utf-8")) <= 4096
                 and path.startswith("/")
                 and len(encoded.translate(None,
                     b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
                     b"\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f")) == len(encoded))
        parts = path[1:].split("/")
        _require(1 <= len(parts) <= 64 and all(p not in ("", ".", "..") for p in parts)
                 and path not in seen and type(row.size) is int
                 and 0 <= row.size <= _MAX_FILE and type(row.sha256) is str
                 and len(row.sha256) == 64 and not row.sha256.strip("0123456789abcdef"))
        seen.add(path)
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


class _NativeDeclaredMetadataSite(NamedTuple):
    """Closed original row binding DATA; never a selectable effect or policy."""
    owner: object
    walk: _NativeDeclaredWalk
    expected: ExpectedArtifact
    site: tuple
    ordinal: int

    def __repr__(self):
        return '<NativeDeclaredMetadataSite unqualified row DATA redacted>'


class _NativeDeclaredMetadataPlan(NamedTuple):
    """Original per-file site allocation; resource binding and ACK still required."""
    owner: object
    scope: _Scope
    walk: _NativeDeclaredWalk
    expected: ExpectedArtifact
    definitions: tuple
    variants: tuple
    progress: list
    commits: list

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
    variants = tuple(_NativeDeclaredMetadataSite(owner, walk, walk.expected, site, ordinal)
                     for ordinal, site in enumerate(definitions))
    return _NativeDeclaredMetadataPlan(owner, walk.scope, walk, walk.expected,
                                       definitions, variants, [0, None], [])


def _native_declared_metadata_site_tail(owner, metadata, ordinal):
    """Validate one original row binding; this supplies no lineage/admission."""
    _require(type(metadata) is _NativeDeclaredMetadataPlan and metadata.owner is owner
             and type(metadata.walk) is _NativeDeclaredWalk
             and metadata.walk.owner is owner and metadata.expected is metadata.walk.expected
             and type(metadata.definitions) is tuple and type(metadata.variants) is tuple
             and len(metadata.variants) == len(metadata.definitions)
             and type(ordinal) is int and 0 <= ordinal < len(metadata.definitions))
    variant, site = metadata.variants[ordinal], metadata.definitions[ordinal]
    _require(type(variant) is _NativeDeclaredMetadataSite
             and variant.owner is owner and variant.walk is metadata.walk
             and variant.expected is metadata.expected and variant.site is site
             and type(variant.ordinal) is int and variant.ordinal == ordinal
             and type(site) is tuple and len(site) == 3
             and type(site[0]) is int and type(site[1]) is str and type(site[2]) is int
             and type(metadata.walk.components) is tuple
             and 0 <= site[2] < len(metadata.walk.components))
    leaf = len(metadata.walk.components) - 1
    _require((site[1] == 'directory' and site[0] == 4 and site[2] < leaf)
             or (site[1] == 'leaf_before' and site[0] == 3 and site[2] == leaf)
             or (site[1] == 'leaf_opened' and site[0] == 4 and site[2] == leaf)
             or (site[1] == 'leaf_after_read' and site[0] in (3, 4) and site[2] == leaf)
             or (site[1] == 'directory_after_hash' and site[0] in (3, 4)
                 and site[2] < leaf))
    return variant


def _native_declared_metadata_cohort_tail(owner, registration, held):
    """Structural held plan joins; no phase, resource or operation authority."""
    _require(type(registration) is _NativeScopeRegistration
             and type(held) is tuple and len(held) == 6)
    walk, walks, progress, index, state, metadata = held
    _require(type(walk) is _NativeDeclaredWalk and type(walks) is tuple
             and type(index) is int and 0 <= index < len(walks)
             and registration.file_walks is walks and walks[index] is walk
             and registration.file_progress is progress
             and type(progress) is list and len(progress) == 1 and progress[0] is index
             and walk.owner is owner and walk.scope is registration.scope
             and walk.cell is registration.cell and walk.root is registration.root
             and walk.state is state and type(state) is list and len(state) == 1
             and type(state[0]) is int and state[0] == 1
             and type(metadata) is _NativeDeclaredMetadataPlan
             and metadata.owner is owner and metadata.scope is registration.scope
             and metadata.walk is walk and metadata.expected is walk.expected
             and type(walk.metadata_slot) is list and len(walk.metadata_slot) == 1
             and walk.metadata_slot[0] is metadata
             and type(metadata.definitions) is tuple and len(metadata.definitions) <= 16384
             and type(metadata.commits) is list
             and len(metadata.commits) <= len(metadata.definitions)
             and type(metadata.progress) is list and len(metadata.progress) == 2
             and type(metadata.progress[0]) is int
             and 0 <= metadata.progress[0] <= len(metadata.definitions))
    if metadata.progress[0] < len(metadata.definitions):
        _native_declared_metadata_site_tail(owner, metadata, metadata.progress[0])
    else:
        _require(metadata.progress[1] is None
                 and len(metadata.commits) == len(metadata.definitions))
    return metadata



def _native_declared_metadata_plan_tail(owner, registration, held):
    """Original unclaimed admission input; a latched consumer is not renewable."""
    metadata = _native_declared_metadata_cohort_tail(owner, registration, held)
    _require(metadata.progress[1] is None
             and metadata.progress[0] < len(metadata.definitions))
    _native_work_registration_tail(owner, registration)
    return metadata


def _native_metadata_component_tail(owner, registration, walk, descriptor, index):
    """Original live opened component/parent chain, never numeric FD membership."""
    _require(type(registration) is _NativeScopeRegistration
             and type(walk) is _NativeDeclaredWalk
             and type(walk.components) is tuple and len(walk.components) <= 4096
             and type(index) is int and -1 <= index < len(walk.components))
    current = descriptor
    for position in range(index, -1, -1):
        component = walk.components[position]
        _require(type(component) is str and type(current) is _NativeOpenedDescriptor)
        close = _native_descriptor_opened(current, registration.native_ledger)
        allocation = current.allocation
        _require(allocation.owner is owner and allocation.scope is registration.scope
                 and allocation.registration is registration
                 and allocation.native is registration.native_origin
                 and type(allocation.arguments) is tuple and len(allocation.arguments) == 3
                 and type(allocation.arguments[0]) is str
                 and allocation.arguments[0] == component
                 and type(allocation.arguments[1]) is int
                 and allocation.refused[0] is False
                 and close.state[0] is False and close.state[1] is False
                 and close.raw[0] is close.unset and close.result[0] is None)
        flags = allocation.native.flags
        _require(type(flags) is tuple and len(flags) == 5 and type(flags[4]) is int
                 and bool(allocation.arguments[1] & flags[4]) is
                 (position < len(walk.components) - 1))
        parent = allocation.parent
        if position == 0:
            _require(component == '/' and parent is None and allocation.arguments[2] is None)
        else:
            _require(type(parent) is _NativeOpenedDescriptor
                     and allocation.arguments[2] is parent.fd)
        current = parent
    _require(current is None)
    return descriptor


class _NativeProbeMetadataResource(NamedTuple):
    """Probe input DATA of a canonical shared type; no native authority."""
    owner: object
    registration: object
    metadata: object
    variant: object
    site: tuple
    ordinal: int
    descriptor: object
    arguments: tuple

    def __repr__(self):
        return '<FreshProbeResource original DATA no-admission>'


class _NativeStartupProbeMetadataResource(NamedTuple):
    """Closed startup-absence policy DATA; no operation or admission authority."""
    owner: object
    registration: object
    metadata: object
    variant: object
    site: tuple
    ordinal: int
    descriptor: object
    arguments: tuple

    def __repr__(self):
        return '<StartupProbeResource DATA no-admission>'


class _NativeLinkMetadataResource(NamedTuple):
    """Closed executable-link stat site; not a native admission or receipt.

    No existing caller constructs this family. The shared kernel additionally
    requires its independently retained early engine origin before preparation.
    """
    owner: object
    registration: object
    execution: object
    site: tuple
    ordinal: int
    arguments: tuple
    descriptor: object

    def __repr__(self):
        return '<NativeLinkMetadataResource fixed path site redacted>'


class _NativeLinkBytesResource(NamedTuple):
    """Fixed readlink site; no metadata/absence or source-read authority."""
    owner: object
    registration: object
    execution: object
    site: tuple
    ordinal: int
    arguments: tuple
    descriptor: object
    record: object
    encoded: object

    def __repr__(self):
        return '<NativeLinkBytesResource fixed readlink site redacted>'


class _NativeMetadataResource(NamedTuple):
    """Bound original resource DATA; no admission, syscall, debit or ACK."""
    owner: object
    registration: _NativeScopeRegistration
    held_walk: tuple
    metadata: _NativeDeclaredMetadataPlan
    site: tuple
    variant: _NativeDeclaredMetadataSite
    ordinal: int
    descriptor: object
    arguments: tuple

    def __repr__(self):
        return '<NativeMetadataResource unqualified original DATA redacted>'


def _prepare_native_metadata_resource(owner, registration, held, descriptor, name=None):
    """Capture this actual site/resource before the future admission callback."""
    metadata = _native_declared_metadata_plan_tail(owner, registration, held)
    ordinal = metadata.progress[0]
    site = metadata.definitions[ordinal]
    variant = _native_declared_metadata_site_tail(owner, metadata, ordinal)
    _require(type(site) is tuple and len(site) == 3 and type(site[0]) is int
             and site[0] in (3, 4) and type(site[1]) is str and type(site[2]) is int)
    walk, operation, component = held[0], site[0], site[2]
    _require(type(walk.components) is tuple and 0 <= component < len(walk.components))
    _native_work_origin_tail(owner, registration, registration.native_origin)
    if operation == 4:
        _require(name is None)
        _native_metadata_component_tail(owner, registration, walk, descriptor, component)
        arguments = (descriptor.fd,)
    else:
        _require(type(name) is str and type(walk.components[component]) is str
                 and name == walk.components[component])
        _native_metadata_component_tail(owner, registration, walk, descriptor, component - 1)
        arguments = (name, None if descriptor is None else descriptor.fd)
    _require(_native_declared_metadata_plan_tail(owner, registration, held) is metadata
             and metadata.progress[0] is ordinal and metadata.definitions[ordinal] is site
             and _native_declared_metadata_site_tail(owner, metadata, ordinal) is variant)
    return _NativeMetadataResource(owner, registration, held, metadata, site, variant, ordinal,
                                   descriptor, arguments)


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
    return plan, walks, progress, index, state, metadata


def _finish_native_declared_walk(owner, registration, held, finish=None):
    _require(type(registration) is _NativeScopeRegistration
             and type(held) is tuple and len(held) == 6)
    plan, walks, progress, index, state, metadata = held
    _require(type(plan) is _NativeDeclaredWalk and type(walks) is tuple
             and type(index) is int and 0 <= index < len(walks))
    _native_registration_tail(owner, registration.scope, registration.cell,
                              registration.root, registration,
                              registration.lineage.ledger.scopes)
    _require(registration.file_walks is walks and registration.file_progress is progress
             and type(progress) is list and len(progress) == 1 and progress[0] is index
             and walks[index] is plan and plan.state is state and len(state) == 1
             and type(state[0]) is int and state[0] == 1
             and type(metadata) is _NativeDeclaredMetadataPlan
             and metadata.owner is owner and metadata.scope is registration.scope
             and metadata.walk is plan and metadata.expected is plan.expected
             and type(plan.metadata_slot) is list and len(plan.metadata_slot) == 1
             and plan.metadata_slot[0] is metadata
             and type(metadata.progress) is list and len(metadata.progress) == 2
             and type(metadata.progress[0]) is int
             and metadata.progress[1] is None and type(metadata.commits) is list)
    if finish is None:
        # Every still-unwired policy retains its original strict zero-site guard.
        _require(metadata.progress[0] == 0 and len(metadata.commits) == 0)
    else:
        from .presentation_native_metadata import _finished_declared_file_tail
        _require(_finished_declared_file_tail(owner, registration, held, finish) is finish)
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
    audit_record = tuple.__getitem__(s, 18)
    if audit_record is not None:
        entry_names = vars(registration.entry_module)
        _require(type(entry_names) is dict and all(type(k) is str for k in entry_names))
        entry_origin, started = entry_names.get('_ENTRY_ORIGIN'), entry_names.get('_STARTED')
        _require(type(entry_origin) is entry_names.get('_EntryOrigin')
                 and tuple.__len__(entry_origin) == 12)
        _require(type(audit_record) is tuple and len(audit_record) == 3
                 and tuple.__len__(registration.lineage) == 6
                 and tuple.__getitem__(registration.lineage, 5) is audit_record
                 and type(started) is tuple and len(started) == 7
                 and started[5] is entry_origin
                 and tuple.__len__(entry_origin) == 12
                 and tuple.__getitem__(entry_origin, 11) is audit_record
                 and tuple.__getitem__(entry_origin, 10) is tuple.__getitem__(registration.lineage, 4)
                 and started[0] is registration.lineage.entry
                 and started[1] is s.source_digest.binding[0]
                 and started[2] is entry_names.get('_CELL')
                 and started is s.source_digest.binding[2]
                 and entry_names.get('_OWNER') is started[0])


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
             and (type(registration.type_pins[0]) is type
                  and type(registration.type_pins[1]) is type
                  and type(registration.type_pins[2]) is type)
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
             and type(close.state[0]) is bool and type(close.state[1]) is bool
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
                 and (type(registration.type_pins[0]) is type
                  and type(registration.type_pins[1]) is type
                  and type(registration.type_pins[2]) is type)
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


def _prepare_native_link_open(owner, registration, name, parent):
    """Return this original open claim before C to the fixed link driver.

    This performs no file effect. The caller must retain this literal return
    independently for cleanup; a later ledger/cell lookup is not a substitute.
    The normal _open admission still rechecks the actor and original parents.
    """
    _require(type(owner) is StartupArtifactOwner
             and type(registration) is _NativeScopeRegistration
             and type(name) is str and type(parent) in (int, type(None)))
    native = _capture_native_work_origin(owner, registration)
    scope = _native_walk_scope(owner, registration)
    _require(native is not None and scope is registration.scope)
    _native_relative_arguments(scope, name, parent)
    flags = native.flags[0] | native.flags[1] | native.flags[2] | native.flags[3] | native.flags[4]
    row = _Descriptor()
    scope.records.append(row)
    row.attempted = True
    allocation = _allocate_native_file_open(owner, registration, parent, (name, flags, parent), row)
    _require(type(allocation) is _NativeOpenAllocation
             and allocation.owner is owner and allocation.registration is registration
             and allocation.scope is scope and allocation.pending is row
             and allocation.arguments[0] is name and allocation.arguments[1] == flags
             and allocation.arguments[2] is parent and allocation.raw[0] is None
             and allocation.result[0] is None and scope.records[-1] is row
             and _native_file_allocation_original(allocation, registration.native_ledger)
                 is allocation.close)
    return allocation


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
        receipt = (close, fd, value)
        close.result[0] = receipt
        _require(_native_file_allocation_original(allocation, original_ledger) is close
                 and ledger.inflight is inflight and inflight[0] is close
                 and ledger.counts is counts and len(counts) == 2
                 and counts[0] is used_after and counts[1] is reserved_after)
        return receipt
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


def _native_read_walk_mirrors_tail(owner, registration, walk, expected, step):
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
    return walk


def _native_read_walk_tail(owner, registration, walk, expected, step):
    walk = _native_read_walk_mirrors_tail(owner, registration, walk, expected, step)
    _native_work_registration_tail(owner, registration)
    _require(_native_read_walk_mirrors_tail(owner, registration, walk, expected, step) is walk)
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


def _native_read_lifecycle_mirrors_tail(owner, registration, parents):
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
    return scope


def _native_read_lifecycle_tail(owner, registration, parents):
    scope = _native_read_lifecycle_mirrors_tail(owner, registration, parents)
    _native_work_registration_tail(owner, registration)
    _require(_native_read_lifecycle_mirrors_tail(owner, registration, parents) is scope)
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


def _native_runtime_read_receipt_mirrors_tail(owner, commit, step):
    """Held raw-free read receipt, not current-work or EOF admission authority."""
    _require(type(commit) is _NativeRuntimeReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    operation, result, consumer = commit.operation, commit.result, commit.consumer
    registration = step.registration
    _require(type(registration) is _NativeScopeRegistration
             and type(step.scope) is _Scope and step.scope is registration.scope
             and type(step.scope.activation) is GatewayActivationOwner
             and type(consumer.committed) is list and len(consumer.committed) == 1
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and type(step.progress) is list and len(step.progress) == 4
             and type(step.progress[0]) is int and type(step.progress[1]) is int
             and type(step.eof) is list and len(step.eof) == 1
             and type(step.eof[0]) is bool and type(commit.eof) is bool
             and type(commit.ordinal) is int and type(commit.remaining) is int
             and type(commit.count) is tuple and len(commit.count) == 3
             and type(commit.count[2]) is int)
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
    ledger = operation.ledger
    _require(ledger is registration.native_ledger and ledger.failed[0] is False
             and type(operation.index) is int and type(ledger.attempts) is list
             and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(value) is int for value in ledger.counts)
             and type(operation.budget[3]) is int)
    _native_read_accumulator_tail(owner, step, commit.count)
    return commit


def _native_runtime_read_receipt_state_tail(owner, commit, step):
    _require(type(commit) is _NativeRuntimeReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    _native_read_walk_tail(owner, step.registration, step.walk, step.expected, step)
    _native_read_lifecycle_tail(owner, step.registration, step.parents)
    return _native_runtime_read_receipt_mirrors_tail(owner, commit, step)


def _native_cache_read_receipt_mirrors_tail(owner, commit, step):
    """Held raw-free cache receipt; no journal prefixes or new work authority."""
    _require(type(commit) is _NativeCacheReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    operation, result, consumer = commit.operation, commit.result, commit.consumer
    registration = step.registration
    _require(type(registration) is _NativeScopeRegistration
             and type(step.scope) is _Scope and step.scope is registration.scope
             and type(step.scope.activation) is GatewayActivationOwner
             and type(consumer.committed) is list and len(consumer.committed) == 1
             and type(consumer.consumption) is list and len(consumer.consumption) == 1
             and type(step.progress) is list and len(step.progress) == 4
             and type(step.progress[0]) is int and type(step.progress[1]) is int
             and type(step.eof) is list and len(step.eof) == 1
             and type(step.eof[0]) is bool and type(commit.eof) is bool
             and type(commit.ordinal) is int and type(commit.remaining) is int
             and type(commit.count) is tuple and len(commit.count) == 3
             and type(commit.count[2]) is int)
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
    ledger = operation.ledger
    _require(ledger is registration.native_ledger and ledger.failed[0] is False
             and type(operation.index) is int and type(ledger.attempts) is list
             and 0 <= operation.index < len(ledger.attempts)
             and ledger.attempts[operation.index] is operation
             and type(operation.budget) is tuple and len(operation.budget) == 4
             and ledger.counts is operation.budget[0]
             and type(ledger.counts) is list and len(ledger.counts) == 2
             and all(type(value) is int for value in ledger.counts)
             and type(operation.budget[3]) is int)
    _native_read_accumulator_tail(owner, step, commit.count)
    _require(type(step.material_module) is ModuleType)
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




def _native_cache_read_receipt_state_tail(owner, commit, step):
    _require(type(commit) is _NativeCacheReadCommit and type(step) is _NativeReadFileStep
             and commit.step is step and step.owner is owner
             and type(commit.operation) is _NativeFileOperation
             and type(commit.result) is _NativeFileResultClaim
             and type(commit.consumer) is _NativeReadConsumer)
    _native_read_walk_tail(owner, step.registration, step.walk, step.expected, step)
    _native_read_lifecycle_tail(owner, step.registration, step.parents)
    return _native_cache_read_receipt_mirrors_tail(owner, commit, step)


def _native_runtime_read_history_tail(owner, commit, step):
    """Actual held receipt during metadata; original close reserves stay held."""
    _require(_native_runtime_read_receipt_state_tail(owner, commit, step) is commit)
    operation = commit.operation
    _require(operation.ledger.counts[0] >= operation.budget[3]
             and operation.ledger.counts[1] is operation.budget[2])
    return commit


def _native_cache_read_history_tail(owner, commit, step):
    """Actual cache receipt during metadata, with the same held reservations."""
    _require(_native_cache_read_receipt_state_tail(owner, commit, step) is commit)
    operation = commit.operation
    _require(operation.ledger.counts[0] >= operation.budget[3]
             and operation.ledger.counts[1] is operation.budget[2])
    return commit


def _native_runtime_read_closed_tail(owner, commit, step):
    """Actual current return plus the original strict latest-debit/IDLE closure."""
    _require(_native_runtime_read_history_tail(owner, commit, step) is commit)
    operation = commit.operation
    ledger, phase = operation.ledger, step.registration.native_phase
    _require(ledger.failed[0] is False
             and ledger.counts[0] is operation.budget[3]
             and ledger.inflight[0] is None
             and phase.current[0] is phase.idle and phase.result[0] is None)
    return commit


def _native_cache_read_closed_tail(owner, commit, step):
    """Actual current cache return; later metadata cannot renew read authority."""
    _require(_native_cache_read_history_tail(owner, commit, step) is commit)
    operation = commit.operation
    ledger, phase = operation.ledger, step.registration.native_phase
    _require(ledger.failed[0] is False
             and ledger.counts[0] is operation.budget[3]
             and ledger.inflight[0] is None
             and phase.current[0] is phase.idle and phase.result[0] is None)
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
        error_type = ArtifactObservationError
        # One private typed refusal per attempt. Hold native base operations before
        # callbacks, bypassing subclass constructors/getters/setters even if a
        # later integrity check detects that very dispatch has changed.
        refusal_new, refusal_init = BaseException.__new__, BaseException.__init__
        refusal_base = BaseException.__dict__
        refusal_dictionary = refusal_base['__dict__'].__get__
        refusal_traceback = refusal_base['__traceback__'].__set__
        refusal_context = refusal_base['__context__'].__set__
        refusal_cause = refusal_base['__cause__'].__set__
        refusal = refusal_new(error_type)
        refusal_init(refusal, "BI1_STARTUP_ARTIFACTS_REFUSED")
        refusal_values = refusal_dictionary(refusal, error_type)
        refusal_values['failed_owner'] = None
        link_raw_type, link_raw_vars, link_raw_tuple, link_raw_len = type, vars, tuple, len
        link_raw_function, link_raw_module = FunctionType, ModuleType
        link_raw_cell = CellType
        link_raw_staticmethod, link_raw_any, link_raw_zip = staticmethod, any, zip
        link_raw_dict, link_raw_str = dict, str
        link_raw_builtin, link_raw_descriptor = BuiltinFunctionType, MethodDescriptorType
        if link_raw_type(cls) is not link_raw_type or cls is not StartupArtifactOwner:
            raise refusal from None
        failure_owner_descriptor = link_raw_vars(cls).get('__dict__')
        if (link_raw_type(failure_owner_descriptor) is not GetSetDescriptorType
                or failure_owner_descriptor.__objclass__ is not cls
                or failure_owner_descriptor.__name__ != '__dict__'
                or link_raw_type(refusal_values) is not link_raw_dict):
            raise refusal from None
        failure_owner_dictionary = failure_owner_descriptor.__get__
        # Hold this module's complete original callable/default bindings before
        # any new blueprint callback; entry points remain the fixed held ones.
        root_namespace = globals()
        root_namespace_entries = tuple(root_namespace.items())
        root_helper_pins = []
        for root_name, root_value in root_namespace_entries:
            if type(root_name) is not str:
                raise refusal from None
            if type(root_value) is FunctionType and root_value.__globals__ is root_namespace:
                root_kw = root_value.__kwdefaults__
                if root_kw is not None and (type(root_kw) is not dict
                        or any(type(k) is not str for k in root_kw)):
                    raise refusal from None
                root_helper_pins.append((root_value, root_value.__code__, root_value.__defaults__,
                                         root_kw, () if root_kw is None else tuple(root_kw.items())))
        root_helper_pins = tuple(root_helper_pins)
        register_scope = _register_native_scope
        if (cls is StartupArtifactOwner and type(activation) is GatewayActivationOwner
                 and activation._artifact_owner is None and activation._artifact_cell is None
                 and activation._artifact_attempt_cell is None
                 and activation._artifact_fact_cell is None) is not True:
            raise refusal from None
        GatewayActivationOwner.current(activation)
        if (activation._artifact_owner is None and activation._artifact_cell is None) is not True:
            raise refusal from None
        owner = cls.__new__(cls)
        activation._artifact_owner = owner
        activation._artifact_cell = (activation, owner)
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._facts = owner._hashes = owner._attempt_cell = owner._fact_cell = None
        owner._scope = owner._origin = owner._cell = owner._root_cell = None
        owner._count_cell = owner._initial_count_cell = None
        owner._cache_fact = None
        owner._startup_probe_execution = None
        owner._bytes_read = 0
        refusal_values['failed_owner'] = owner
        failure_owner_values = failure_owner_dictionary(owner, cls)
        if link_raw_type(failure_owner_values) is not link_raw_dict:
            raise refusal from None
        try:
            if source is not None:
                if (type(source) is _PackageSource) is not True:
                    raise refusal from None
                owner._bytes_read = source.count_cell[2]
            digest_context = None if source is None else source.owner._origin.source_digest
            # Retain the constructor inputs before crossing its callback boundary.
            # A returned tuple must not nominate replacement state for publication.
            kind = _Scope
            fields = vars(kind)['_fields']
            members = tuple(vars(kind).get(name) for name in fields)
            dispatch_names = ('__getattribute__', '__getattr__', '__getitem__',
                              '__len__', '__iter__')
            dispatch = tuple(vars(kind).get(name) for name in dispatch_names)
            constructor = vars(kind)['__new__']
            if type(constructor) is staticmethod:
                constructor = constructor.__func__
            constructor_code = constructor.__code__
            context = (os.getpid(), os.geteuid(), threading.get_ident())
            records = []
            reads = None if digest_context is None else []
            native_files = None if digest_context is None else digest_context.native_files
            slot = None if digest_context is None else [None]
            owner_dict = failure_owner_values
            owner_entries = tuple(owner_dict.items())
            activation_cell = activation._artifact_cell
            need, need_code = _require, _require.__code__
            item, length = tuple.__getitem__, tuple.__len__
            startup_origin = None
            if cache is not None and native_files is not None:
                from .presentation_startup_probe import _new_startup_probe_origin
                startup_origin = _new_startup_probe_origin(owner, cache, context, expected)
            if _require is not need or need.__code__ is not need_code:
                raise refusal from None
            before_constructor = vars(kind).get('__new__')
            if type(before_constructor) is staticmethod:
                before_constructor = before_constructor.__func__
            if (_Scope is kind and before_constructor is constructor
                 and constructor.__code__ is constructor_code
                 and link_raw_type(owner) is cls
                 and failure_owner_dictionary(owner, cls) is owner_dict and len(owner_dict) == len(owner_entries)
                 and all(key in owner_dict and owner_dict[key] is value
                         for key, value in owner_entries)
                 and activation._artifact_owner is owner
                 and activation._artifact_cell is activation_cell) is not True:
                raise refusal from None
            link_blueprint = None
            link_origin = None
            link_audit_record = None
            link_tail = link_tail_code = None
            link_cohort = None
            if runtime is not None and native_files is not None:
                # The ACTUAL already-validated SourceDigestContext retains the
                # original invocation/started/EntryOrigin objects. No late import
                # or current getter is allowed to nominate a replacement origin.
                _source_current(source)
                if (type(runtime) is _RuntimeSource and type(digest_context.binding) is tuple
                     and len(digest_context.binding) == 3) is not True:
                    raise refusal from None
                digest_binding = digest_context.binding
                invocation, started = digest_binding[0], digest_binding[2]
                if (type(started) is tuple and len(started) == 7
                     and started[0] is digest_context.entry) is not True:
                    raise refusal from None
                entry_origin = tuple.__getitem__(started, 5)
                if (tuple.__len__(entry_origin) == 12
                     and tuple.__len__(native_files) == 6
                     and tuple.__len__(invocation) == 11) is not True:
                    raise refusal from None
                link_origin = tuple.__getitem__(entry_origin, 10)
                if (tuple.__getitem__(invocation, 9) is native_files
                     and tuple.__getitem__(native_files, 0) is digest_context.entry
                     and tuple.__getitem__(native_files, 4) is link_origin
                     and type(link_origin) is tuple and len(link_origin) == 5) is not True:
                    raise refusal from None
                if (type(link_origin[0]) is tuple and len(link_origin[0]) == 8) is not True:
                    raise refusal from None
                link_helper_origin = link_origin[0][6]
                if (link_raw_type(link_helper_origin) is not link_raw_tuple
                        or link_raw_len(link_helper_origin) != 8
                        or link_raw_type(link_helper_origin[3]) is not link_raw_tuple
                        or link_raw_len(link_helper_origin[3]) != 4):
                    raise refusal from None
                link_helper_record = link_helper_origin[7]
                if (link_raw_type(link_helper_record) is not link_raw_tuple
                        or link_raw_len(link_helper_record) != 3
                        or link_helper_record[0] is not link_helper_origin[6]
                        or link_helper_record[2] is not link_helper_origin[3][3]
                        or link_raw_type(link_helper_record[1]) is not link_raw_tuple
                        or link_raw_len(link_helper_record[1]) != 4
                        or link_helper_record[1][0] is not link_helper_origin[6]):
                    raise refusal from None
                link_helper_layout = link_helper_record[1]
                link_engine_origin = link_origin[0][4]
                link_audit_record = tuple.__getitem__(entry_origin, 11)
                if (type(link_audit_record) is tuple and len(link_audit_record) == 3
                     and tuple.__getitem__(native_files, 5) is link_audit_record
                     and link_origin[0][7] is link_audit_record
                     and link_audit_record[0] is link_engine_origin
                     and link_audit_record[1] is link_origin[0][5]) is not True:
                    raise refusal from None
                # Raw pointer joins above derive the actual origin. Its fixed
                # early current row is independently code/default pinned below.
                current_row = link_origin[2][7]
                blueprint_row = link_origin[2][5]
                factory_row = link_origin[3][15]
                tail_row = link_origin[3][14]
                cohort_row = link_origin[3][13]
                owner_kind = cls
                owner_namespace = globals()
                origin_entry_names = tuple.__getitem__(entry_origin, 2)
                if (type(origin_entry_names) is dict
                     and all(type(k) is str for k in origin_entry_names)) is not True:
                    raise refusal from None
                origin_invocation_owner = tuple.__getitem__(digest_context, 0)
                origin_invocation_kind = tuple.__getitem__(entry_origin, 7)
                if (link_raw_type(origin_invocation_owner) is origin_invocation_kind
                     and link_raw_type(origin_invocation_kind) is link_raw_type) is not True:
                    raise refusal from None
                origin_dict_descriptor = link_raw_vars(origin_invocation_kind).get('__dict__')
                if (link_raw_type(origin_dict_descriptor) is GetSetDescriptorType
                     and origin_dict_descriptor.__objclass__ is origin_invocation_kind) is not True:
                    raise refusal from None
                origin_dict_get = origin_dict_descriptor.__get__
                if (link_raw_type(origin_dict_get) is MethodWrapperType
                     and origin_dict_get.__self__ is origin_dict_descriptor
                     and origin_dict_get.__name__ == '__get__') is not True:
                    raise refusal from None
                origin_invocation_names = origin_dict_get(origin_invocation_owner, origin_invocation_kind)
                if (link_raw_type(origin_invocation_names) is link_raw_dict
                     and not link_raw_any(link_raw_type(k) is not link_raw_str
                                          for k in origin_invocation_names)
                     and origin_invocation_names.get('_scope') is invocation) is not True:
                    raise refusal from None
                runtime_guard, runtime_code = runtime.guard, runtime.code
                if (type(runtime_guard) is FunctionType and runtime_guard.__code__ is runtime_code
                     and runtime.entry_type._pure_current is runtime_guard) is not True:
                    raise refusal from None
                runtime_guard(runtime.entry, runtime.inputs, runtime.cell)
                # The runtime source is DATA. Its internally consistent copied
                # plan must not replace the actual plan in retained entry inputs.
                runtime_entry = tuple.__getitem__(runtime, 0)
                runtime_entry_kind = tuple.__getitem__(runtime, 1)
                runtime_inputs = tuple.__getitem__(runtime, 2)
                runtime_cell = tuple.__getitem__(runtime, 3)
                runtime_entry_names = vars(runtime_entry)
                runtime_input_kind = type(runtime_inputs)
                if (tuple.__len__(runtime_inputs) == 16
                     and type(runtime_entry) is runtime_entry_kind
                     and runtime_entry_names.get('_inputs') is runtime_inputs
                     and runtime_entry_names.get('_root_cell') is runtime_cell) is not True:
                    raise refusal from None
                runtime_original_plan = tuple.__getitem__(runtime_inputs, 12)
                if (type(runtime_original_plan) is link_origin[4][3][0]
                     and tuple.__len__(runtime_original_plan) == 15) is not True:
                    raise refusal from None
                runtime_original_link = tuple.__getitem__(runtime_original_plan, 14)
                if (type(runtime_original_link) is link_origin[4][4][0]
                     and tuple.__getitem__(runtime, 6) is runtime_original_plan
                     and tuple.__getitem__(runtime, 7) is runtime_original_link
                     and tuple.__getitem__(runtime_original_plan, 7) is expected
                     and tuple.__getitem__(runtime_inputs, 4) is tuple.__getitem__(source, 0)) is not True:
                    raise refusal from None
                # Bind the package graph to the actual retained entry inputs,
                # not only the matching package owner. Binding tuples themselves
                # are fresh return values; their original root/fact members must
                # match, including the nested selection binding. This is a
                # custody fence, not a cached currentness verdict.
                input_package_binding = tuple.__getitem__(runtime_inputs, 5)
                source_package_binding = tuple.__getitem__(source, 1)
                if (link_raw_type(input_package_binding) is link_raw_tuple
                     and link_raw_len(input_package_binding) == 5
                     and link_raw_type(source_package_binding) is link_raw_tuple
                     and link_raw_len(source_package_binding) == 5
                     and tuple.__getitem__(input_package_binding, 0) is tuple.__getitem__(source_package_binding, 0)
                     and tuple.__getitem__(input_package_binding, 1) is tuple.__getitem__(source_package_binding, 1)
                     and tuple.__getitem__(input_package_binding, 2) is tuple.__getitem__(source_package_binding, 2)
                     and tuple.__getitem__(input_package_binding, 3) is tuple.__getitem__(source_package_binding, 3)
                     and link_raw_type(tuple.__getitem__(input_package_binding, 4)) is link_raw_tuple
                     and link_raw_type(tuple.__getitem__(source_package_binding, 4)) is link_raw_tuple
                     and link_raw_len(tuple.__getitem__(input_package_binding, 4)) == 4
                     and link_raw_len(tuple.__getitem__(source_package_binding, 4)) == 4
                     and tuple.__getitem__(tuple.__getitem__(input_package_binding, 4), 0) is tuple.__getitem__(tuple.__getitem__(source_package_binding, 4), 0)
                     and tuple.__getitem__(tuple.__getitem__(input_package_binding, 4), 1) is tuple.__getitem__(tuple.__getitem__(source_package_binding, 4), 1)
                     and tuple.__getitem__(tuple.__getitem__(input_package_binding, 4), 2) is tuple.__getitem__(tuple.__getitem__(source_package_binding, 4), 2)
                     and tuple.__getitem__(tuple.__getitem__(input_package_binding, 4), 3) is tuple.__getitem__(tuple.__getitem__(source_package_binding, 4), 3)) is not True:
                    raise refusal from None
                original_package_source = source
                link_tail, link_tail_code = tail_row[1], tail_row[2]
                source_check, source_check_code = _source_current, _source_current.__code__

                def function_row_current(row):
                    if (type(row) is not tuple or len(row) != 7 or type(row[0]) is not str
                            or type(row[1]) is not FunctionType or type(row[3]) is not dict
                            or any(type(k) is not str for k in row[3])
                            or row[3].get(row[0]) is not row[1]
                            or row[1].__code__ is not row[2] or row[1].__globals__ is not row[3]
                            or row[1].__defaults__ is not row[4]
                            or row[1].__kwdefaults__ is not row[5]
                            or (row[5] is not None and (type(row[5]) is not dict
                                or any(type(k) is not str for k in row[5])
                                or len(row[5]) != len(row[6])
                                or any(k not in row[5] or row[5][k] is not value
                                       for k, value in row[6])))):
                        raise refusal from None

                def link_rejoin():
                    if (globals() is not root_namespace
                            or any(type(k) is not str for k in root_namespace)
                            or len(root_namespace) != len(root_namespace_entries)
                            or any(k not in root_namespace or root_namespace[k] is not value
                                   for k, value in root_namespace_entries)):
                        raise refusal from None
                    for function, code, defaults, kw, pairs in root_helper_pins:
                        if (function.__code__ is not code or function.__defaults__ is not defaults
                                or function.__kwdefaults__ is not kw
                                or (kw is not None and (any(type(k) is not str for k in kw)
                                    or len(kw) != len(pairs)
                                    or any(k not in kw or kw[k] is not value for k, value in pairs)))):
                            raise refusal from None
                    if (_require is not need or need.__code__ is not need_code
                            or _source_current is not source_check
                            or source_check.__code__ is not source_check_code
                            or owner_namespace.get('StartupArtifactOwner') is not owner_kind
                            or type(owner) is not owner_kind):
                        raise refusal from None
                    if (tuple.__getitem__(digest_context, 1) is digest_binding
                         and digest_binding[0] is invocation and digest_binding[2] is started
                         and tuple.__getitem__(started, 5) is entry_origin
                         and tuple.__getitem__(invocation, 9) is native_files
                         and tuple.__getitem__(native_files, 4) is link_origin
                         and tuple.__getitem__(entry_origin, 10) is link_origin
                         and tuple.__getitem__(entry_origin, 11) is link_audit_record
                         and tuple.__getitem__(native_files, 5) is link_audit_record
                         and link_origin[0][7] is link_audit_record
                         and link_origin[0][6] is link_helper_origin
                         and link_helper_origin[7] is link_helper_record
                         and link_helper_record[0] is link_helper_origin[6]
                         and link_helper_record[1] is link_helper_layout
                         and link_helper_record[2] is link_helper_origin[3][3]
                         and origin_entry_names.get('_ENTRY_ORIGIN') is entry_origin
                         and origin_entry_names.get('GatewayEntryOwner') is tuple.__getitem__(entry_origin, 7)
                         and tuple.__getitem__(runtime, 0) is runtime_entry
                         and tuple.__getitem__(runtime, 1) is runtime_entry_kind
                         and tuple.__getitem__(runtime, 2) is runtime_inputs
                         and tuple.__getitem__(runtime, 3) is runtime_cell
                         and tuple.__getitem__(runtime, 4) is runtime_guard
                         and runtime_guard.__code__ is runtime_code
                         and vars(runtime_entry_kind).get('_pure_current') is runtime_guard
                         and tuple.__getitem__(runtime, 6) is runtime_original_plan
                         and tuple.__getitem__(runtime, 7) is runtime_original_link
                         and runtime_entry_names.get('_inputs') is runtime_inputs
                         and runtime_entry_names.get('_root_cell') is runtime_cell
                         and source is original_package_source
                         and tuple.__getitem__(source, 1) is source_package_binding
                         and tuple.__getitem__(runtime_inputs, 4) is tuple.__getitem__(source, 0)
                         and tuple.__getitem__(runtime_inputs, 5) is input_package_binding
                         and tuple.__getitem__(runtime_inputs, 12) is runtime_original_plan
                         and tuple.__getitem__(runtime_original_plan, 14) is runtime_original_link) is not True:
                        raise refusal from None
                    function_row_current(current_row)
                    if (current_row[1](link_origin) is link_origin) is not True:
                        raise refusal from None
                    for row in (current_row, blueprint_row, factory_row, tail_row, cohort_row):
                        function_row_current(row)
                    # The origin checker above is a callback boundary. Rejoin
                    # original package DATA afterward as well as before it.
                    if (source is not original_package_source
                            or tuple.__getitem__(source, 1) is not source_package_binding
                            or tuple.__getitem__(runtime, 2) is not runtime_inputs
                            or tuple.__getitem__(runtime_inputs, 4) is not tuple.__getitem__(source, 0)
                            or tuple.__getitem__(runtime_inputs, 5) is not input_package_binding):
                        raise refusal from None

                # Check raw publication cohorts after EACH child helper return.
                # Factory reads these snapshots, never owner getters or grants.
                classes = []
                for selected in (owner_kind, runtime.entry_type, type(activation),
                                 tuple.__getitem__(entry_origin, 7), runtime_input_kind):
                    namespace = vars(selected)
                    if (type(selected) is type and all(type(k) is str for k in namespace)) is not True:
                        raise refusal from None
                    functions = []
                    for value in namespace.values():
                        if type(value) in (classmethod, staticmethod):
                            value = value.__func__
                        if type(value) is FunctionType:
                            kw = value.__kwdefaults__
                            if (kw is None or (type(kw) is dict and all(type(k) is str for k in kw))) is not True:
                                raise refusal from None
                            functions.append((value, value.__code__, value.__defaults__, kw,
                                              () if kw is None else tuple(kw.items())))
                    classes.append((selected, tuple(namespace.items()), tuple(functions)))
                io_slot = runtime.inputs.io_slot
                if (type(io_slot) is list and len(io_slot) == 1 and io_slot[0] is None
                     and type(runtime.reads) is list and len(runtime.reads) == 0
                     and all(type(values) is list and len(values) == 1 and values[0] is None
                             for values in (runtime.before, runtime.after, runtime.count))) is not True:
                    raise refusal from None
                link_cohort = (((owner_dict, tuple(owner_dict.items())),
                                (vars(activation), tuple(vars(activation).items())),
                                (vars(source.owner), tuple(vars(source.owner).items())),
                                (vars(runtime.entry), tuple(vars(runtime.entry).items())),
                                (vars(digest_context.entry), tuple(vars(digest_context.entry).items()))),
                               tuple((values, tuple(values)) for values in (
                                   runtime.reads, runtime.before, runtime.after,
                                   runtime.count, io_slot)), tuple(classes))
                link_rejoin()
                held_factory = blueprint_row[1](link_origin)
                link_rejoin()
                if (held_factory is factory_row[1]) is not True:
                    raise refusal from None
                link_blueprint = held_factory(owner, runtime, context, native_files,
                                              link_origin, link_cohort)
                link_rejoin()
                if (cohort_row[1](link_cohort) is link_cohort) is not True:
                    raise refusal from None
                link_rejoin()
                if (link_tail(link_blueprint) is link_blueprint) is not True:
                    raise refusal from None
                link_rejoin()
                if (tuple.__getitem__(link_blueprint, 0) is owner
                     and tuple.__getitem__(link_blueprint, 1) is runtime
                     and tuple.__getitem__(link_blueprint, 2) is context
                     and tuple.__getitem__(link_blueprint, 3) is native_files
                     and tuple.__getitem__(link_blueprint, 4) is link_origin) is not True:
                    raise refusal from None
            values = (activation, activation._scope, expected, context, records,
                      source, runtime, reads, cache, digest_context, native_files,
                      slot, None, None, None, None, startup_origin, link_blueprint, link_audit_record)
            s = constructor(kind, *values)
            if _require is not need or need.__code__ is not need_code:
                raise refusal from None
            current_constructor = vars(kind).get('__new__')
            if type(current_constructor) is staticmethod:
                current_constructor = current_constructor.__func__
            if (_Scope is kind and type(s) is kind
                 and current_constructor is constructor
                 and constructor.__code__ is constructor_code
                 and vars(kind).get('_fields') is fields
                 and all(vars(kind).get(name) is member
                         for name, member in zip(fields, members, strict=True))
                 and all(vars(kind).get(name) is member
                         for name, member in zip(dispatch_names, dispatch, strict=True))
                 and length(s) == len(values)
                 and all(item(s, index) is value for index, value in enumerate(values))
                 and link_raw_type(owner) is cls
                 and failure_owner_dictionary(owner, cls) is owner_dict and len(owner_dict) == len(owner_entries)
                 and all(type(key) is str for key in owner_dict)
                 and all(key in owner_dict and owner_dict[key] is value
                         for key, value in owner_entries)
                 and activation._artifact_owner is owner
                 and activation._artifact_cell is activation_cell
                 and type(records) is list and len(records) == 0
                 and (reads is None or type(reads) is list and len(reads) == 0)
                 and (slot is None or type(slot) is list
                      and len(slot) == 1 and slot[0] is None)) is not True:
                raise refusal from None
            if link_blueprint is not None:
                link_rejoin()
                if (cohort_row[1](link_cohort) is link_cohort) is not True:
                    raise refusal from None
                link_rejoin()
                if (item(s, 17) is link_blueprint
                     and link_tail(link_blueprint) is link_blueprint) is not True:
                    raise refusal from None
                link_rejoin()
                # A helper return is not permission to publish changed vacancy.
                if (cohort_row[1](link_cohort) is link_cohort) is not True:
                    raise refusal from None
                link_rejoin()
                if (globals() is not root_namespace
                        or any(type(k) is not str for k in root_namespace)
                        or len(root_namespace) != len(root_namespace_entries)
                        or any(k not in root_namespace or root_namespace[k] is not value
                               for k, value in root_namespace_entries)):
                    raise refusal from None
                for function, code, defaults, kw, pairs in root_helper_pins:
                    if (function.__code__ is not code or function.__defaults__ is not defaults
                            or function.__kwdefaults__ is not kw
                            or (kw is not None and (any(type(k) is not str for k in kw)
                                or len(kw) != len(pairs)
                                or any(k not in kw or kw[k] is not value for k, value in pairs)))):
                        raise refusal from None
                if (tuple.__getitem__(runtime, 0) is not runtime_entry
                        or tuple.__getitem__(runtime, 1) is not runtime_entry_kind
                        or tuple.__getitem__(runtime, 2) is not runtime_inputs
                        or tuple.__getitem__(runtime, 3) is not runtime_cell
                        or tuple.__getitem__(runtime, 6) is not runtime_original_plan
                        or tuple.__getitem__(runtime, 7) is not runtime_original_link
                        or type(runtime_inputs) is not runtime_input_kind
                        or runtime_entry_names.get('_inputs') is not runtime_inputs
                        or runtime_entry_names.get('_root_cell') is not runtime_cell
                        or tuple.__getitem__(runtime_inputs, 12) is not runtime_original_plan
                        or tuple.__getitem__(runtime_original_plan, 14) is not runtime_original_link
                        or tuple.__getitem__(runtime_original_plan, 7) is not expected
                        or source is not original_package_source
                        or tuple.__getitem__(source, 1) is not source_package_binding
                        or tuple.__getitem__(runtime_inputs, 5) is not input_package_binding
                        or tuple.__getitem__(s, 5) is not original_package_source
                        or tuple.__getitem__(runtime_inputs, 4) is not tuple.__getitem__(source, 0)):
                    raise refusal from None
                # Rejoin actual source/entry pointer identities without calling
                # a current getter after the last callback-bearing origin seal.
                if (tuple.__getitem__(digest_context, 0) is not origin_invocation_owner
                        or link_raw_type(origin_invocation_owner) is not origin_invocation_kind
                        or origin_dict_get(origin_invocation_owner, origin_invocation_kind) is not origin_invocation_names
                        or link_raw_any(link_raw_type(k) is not link_raw_str
                                        for k in origin_invocation_names)
                        or origin_invocation_names.get('_scope') is not invocation
                        or tuple.__getitem__(digest_context, 1) is not digest_binding
                        or tuple.__getitem__(digest_context, 5) is not native_files
                        or tuple.__getitem__(invocation, 9) is not native_files
                        or tuple.__getitem__(started, 5) is not entry_origin
                        or tuple.__getitem__(native_files, 4) is not link_origin
                        or tuple.__getitem__(entry_origin, 10) is not link_origin
                        or tuple.__getitem__(entry_origin, 11) is not link_audit_record
                        or tuple.__getitem__(native_files, 5) is not link_audit_record
                        or tuple.__getitem__(s, 18) is not link_audit_record
                        or link_origin[0][7] is not link_audit_record
                        or origin_entry_names.get('_ENTRY_ORIGIN') is not entry_origin
                        or origin_entry_names.get('_STARTED') is not started
                        or origin_entry_names.get('_OWNER') is not tuple.__getitem__(digest_context, 0)
                        or origin_entry_names.get('_CELL') is not digest_binding[1]):
                    raise refusal from None
                # Complete original policy/module/function/type seal, inline so
                # a helper return cannot invalidate it before publication.
                if link_raw_type(link_origin) is not link_raw_tuple or link_raw_len(link_origin) != 5:
                    raise refusal from None
                link_pin_environment, link_pin_modules, link_pin_own_functions, link_pin_policy_functions, link_pin_types = link_origin
                if (
                    link_raw_type(link_pin_environment) is not link_raw_tuple
                    or link_raw_len(link_pin_environment) != 8
                    or link_raw_type(link_pin_environment[0]) is not link_raw_module
                    or (link_raw_type(link_pin_environment[1]) is not link_raw_dict)
                    or (link_raw_vars(link_pin_environment[0]) is not link_pin_environment[1])
                    or link_raw_any(
                        link_raw_type(link_pin_k) is not link_raw_str
                        for link_pin_k in link_pin_environment[1]
                    )
                    or (link_raw_type(link_pin_environment[2]) is not link_raw_dict)
                    or link_raw_any(
                        link_raw_type(link_pin_k) is not link_raw_str
                        for link_pin_k in link_pin_environment[2]
                    )
                    or (link_pin_environment[1].get("modules") is not link_pin_environment[2])
                    or (link_raw_type(link_pin_modules) is not link_raw_tuple)
                    or (link_raw_len(link_pin_modules) != 6)
                    or (link_raw_type(link_pin_own_functions) is not link_raw_tuple)
                    or (link_raw_type(link_pin_policy_functions) is not link_raw_tuple)
                    or (link_raw_type(link_pin_types) is not link_raw_tuple)
                    or (link_raw_len(link_pin_types) != 15)
                ):
                    raise refusal from None
                link_pin_names = (
                    "hmp_startup.link_factory_origin",
                    "hmp_plugin.presentation_link_path_policy",
                    "hmp_plugin.presentation_startup_artifacts",
                    "hmp_startup.runtime_files",
                    "hmp_startup.entry_files",
                    "hmp_startup.cache_context",
                )
                for link_pin_row, link_pin_name in link_raw_zip(link_pin_modules, link_pin_names, strict=True):
                    if link_raw_type(link_pin_row) is not link_raw_tuple or link_raw_len(link_pin_row) != 3 or link_raw_type(link_pin_row[0]) is not link_raw_str or (link_pin_row[0] != link_pin_name) or (link_raw_type(link_pin_row[1]) is not link_raw_module) or (link_raw_type(link_pin_row[2]) is not link_raw_dict) or link_raw_any((link_raw_type(link_pin_k) is not link_raw_str for link_pin_k in link_pin_row[2])) or (link_pin_environment[2].get(link_pin_name) is not link_pin_row[1]) or (link_raw_vars(link_pin_row[1]) is not link_pin_row[2]) or (link_raw_type(link_pin_row[2].get('__name__')) is not link_raw_str) or (link_pin_row[2]['__name__'] != link_pin_name):
                        raise refusal from None
                if link_pin_modules[0][2].get('_CAPTURE_STARTED') is not True:
                    raise refusal from None
                link_pin_own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename', 'current_started')
                link_pin_policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites', '_directory', '_leaf', '_cursor_tail', '_start', '_action', '_advance', '_outcome', '_scope_blueprint_guard', '_scope_blueprint_cohort', '_scope_blueprint_tail', '_new_scope_blueprint')
                for link_pin_rows, link_pin_expected, link_pin_namespace in ((link_pin_own_functions, link_pin_own_names, link_pin_modules[0][2]), (link_pin_policy_functions, link_pin_policy_names, link_pin_modules[1][2])):
                    if link_raw_len(link_pin_rows) != link_raw_len(link_pin_expected):
                        raise refusal from None
                    for link_pin_row, link_pin_name in link_raw_zip(link_pin_rows, link_pin_expected, strict=True):
                        if link_raw_type(link_pin_row) is not link_raw_tuple or link_raw_len(link_pin_row) != 7 or link_raw_type(link_pin_row[0]) is not link_raw_str or (link_pin_row[0] != link_pin_name) or (link_raw_type(link_pin_row[1]) is not link_raw_function) or (link_pin_row[3] is not link_pin_namespace) or (link_pin_namespace.get(link_pin_name) is not link_pin_row[1]) or (link_pin_row[1].__code__ is not link_pin_row[2]) or (link_pin_row[1].__globals__ is not link_pin_namespace) or (link_pin_row[1].__defaults__ is not link_pin_row[4]) or (link_pin_row[1].__closure__ is not None) or (link_raw_type(link_pin_row[6]) is not link_raw_tuple):
                            raise refusal from None
                        link_pin_kw = link_pin_row[1].__kwdefaults__
                        if link_pin_kw is not link_pin_row[5]:
                            raise refusal from None
                        if link_pin_kw is None:
                            if link_pin_row[6] != ():
                                raise refusal from None
                        elif link_raw_type(link_pin_kw) is not link_raw_dict or link_raw_any((link_raw_type(link_pin_k) is not link_raw_str for link_pin_k in link_pin_kw)) or link_raw_len(link_pin_kw) != link_raw_len(link_pin_row[6]) or link_raw_any((link_raw_type(link_pin_pair) is not link_raw_tuple or link_raw_len(link_pin_pair) != 2 or link_raw_type(link_pin_pair[0]) is not link_raw_str or (link_pin_pair[0] not in link_pin_kw) or (link_pin_kw[link_pin_pair[0]] is not link_pin_pair[1]) for link_pin_pair in link_pin_row[6])):
                            raise refusal from None
                link_pin_exports = (
                    (1, "_LinkPathPolicy"),
                    (1, "_LinkPathCursor"),
                    (2, "ExpectedArtifact"),
                    (3, "RuntimeFilePlan"),
                    (3, "ExecutableLinkPlan"),
                    (3, "LinkHop"),
                    (1, "_LinkScopeBlueprint"),
                    (2, "_RuntimeSource"),
                    (2, "_Scope"),
                    (0, "_FilesystemEncodingOrigin"),
                    (0, "_EncodedBasename"),
                    (3, "RuntimePackage"),
                    (4, "_Inputs"),
                    (5, "CacheInputData"),
                    (5, "_ContextSource"),
                )
                for link_pin_pin, (link_pin_module_index, link_pin_name) in link_raw_zip(
                    link_pin_types, link_pin_exports, strict=True
                ):
                    if (
                        link_raw_type(link_pin_pin) is not link_raw_tuple
                        or link_raw_len(link_pin_pin) != 12
                        or link_raw_type(link_pin_pin[0]) is not link_raw_type
                        or (
                            link_pin_modules[link_pin_module_index][2].get(link_pin_name)
                            is not link_pin_pin[0]
                        )
                        or (link_raw_type(link_pin_pin[1]) is not link_raw_tuple)
                        or link_raw_any(
                            link_raw_type(link_pin_n) is not link_raw_str
                            for link_pin_n in link_pin_pin[1]
                        )
                        or (link_raw_type(link_pin_pin[2]) is not link_raw_tuple)
                        or (link_raw_len(link_pin_pin[2]) != link_raw_len(link_pin_pin[1]))
                        or (link_raw_type(link_pin_pin[3]) is not link_raw_function)
                        or (link_raw_type(link_pin_pin[5]) is not link_raw_dict)
                        or link_raw_any(
                            link_raw_type(link_pin_k) is not link_raw_str
                            for link_pin_k in link_pin_pin[5]
                        )
                        or (link_raw_type(link_pin_pin[8]) is not link_raw_tuple)
                    ):
                        raise refusal from None
                    (
                        link_pin_kind,
                        link_pin_fields,
                        link_pin_members,
                        link_pin_constructor,
                        link_pin_code,
                        link_pin_globals_,
                        link_pin_defaults,
                        link_pin_bases,
                        link_pin_dispatch,
                        link_pin_constructor_kw,
                        link_pin_constructor_kw_pairs,
                        link_pin_constructor_global_pairs,
                    ) = link_pin_pin
                    link_pin_namespace = link_raw_vars(link_pin_kind)
                    if link_raw_any(
                        link_raw_type(constructor_key) is not link_raw_str
                        for constructor_key in link_pin_namespace
                    ):
                        raise refusal from None
                    link_pin_actual = link_pin_namespace.get("__new__")
                    if link_raw_type(link_pin_actual) is link_raw_staticmethod:
                        link_pin_actual = link_pin_actual.__func__
                    if (
                        link_pin_namespace.get("_fields") is not link_pin_fields
                        or link_pin_actual is not link_pin_constructor
                        or link_pin_constructor.__code__ is not link_pin_code
                        or (link_pin_constructor.__globals__ is not link_pin_globals_)
                        or (link_pin_constructor.__defaults__ is not link_pin_defaults)
                        or (link_pin_kind.__bases__ is not link_pin_bases)
                        or (link_pin_globals_.get("_tuple_new") is not link_raw_tuple.__new__)
                        or link_raw_any(
                            (
                                link_pin_namespace.get(link_pin_n) is not link_pin_member
                                for link_pin_n, link_pin_member in link_raw_zip(
                                    link_pin_fields, link_pin_members, strict=True
                                )
                            )
                        )
                        or link_raw_any(
                            link_raw_type(link_pin_row) is not link_raw_tuple
                            or link_raw_len(link_pin_row) != 2
                            or link_raw_type(link_pin_row[0]) is not link_raw_str
                            or (link_pin_namespace.get(link_pin_row[0]) is not link_pin_row[1])
                            for link_pin_row in link_pin_dispatch
                        )
                    ):
                        raise refusal from None
                    if (
                        link_raw_type(link_pin_constructor) is not link_raw_function
                        or link_pin_constructor.__kwdefaults__ is not link_pin_constructor_kw
                        or link_pin_constructor.__closure__ is not None
                        or link_raw_type(link_pin_constructor.__code__.co_filename)
                        is not link_raw_str
                        or (
                            link_pin_defaults is not None
                            and link_raw_type(link_pin_defaults) is not link_raw_tuple
                        )
                    ):
                        raise refusal from None
                    for constructor_namespace, constructor_pairs in (
                        (link_pin_globals_, link_pin_constructor_global_pairs),
                        (link_pin_constructor_kw, link_pin_constructor_kw_pairs),
                    ):
                        if link_raw_type(constructor_pairs) is not link_raw_tuple:
                            raise refusal from None
                        if constructor_namespace is None:
                            if link_raw_len(constructor_pairs) != 0:
                                raise refusal from None
                            continue
                        if link_raw_type(
                            constructor_namespace
                        ) is not link_raw_dict or link_raw_len(
                            constructor_namespace
                        ) != link_raw_len(constructor_pairs):
                            raise refusal from None
                        constructor_expected = {}
                        for constructor_pair in constructor_pairs:
                            if (
                                link_raw_type(constructor_pair) is not link_raw_tuple
                                or link_raw_len(constructor_pair) != 2
                                or link_raw_type(constructor_pair[0]) is not link_raw_str
                                or constructor_pair[0] in constructor_expected
                            ):
                                raise refusal from None
                            constructor_expected[constructor_pair[0]] = constructor_pair[1]
                        for constructor_key, constructor_value in constructor_namespace.items():
                            if (
                                link_raw_type(constructor_key) is not link_raw_str
                                or constructor_key not in constructor_expected
                                or constructor_expected[constructor_key] is not constructor_value
                            ):
                                raise refusal from None
                # Original retained-helper prefix and DATA, with no final callback.
                if (link_pin_environment[6] is not link_helper_origin
                        or link_helper_origin[7] is not link_helper_record
                        or link_helper_record[0] is not link_helper_origin[6]
                        or link_helper_record[1] is not link_helper_layout
                        or link_helper_record[2] is not link_helper_origin[3][3]):
                    raise refusal from None
                link_helper_default_pairs = link_pin_own_functions[2][6]
                link_helper_defaults = {}
                for link_helper_pair in link_helper_default_pairs:
                    if (link_raw_type(link_helper_pair) is not link_raw_tuple
                            or link_raw_len(link_helper_pair) != 2
                            or link_raw_type(link_helper_pair[0]) is not link_raw_str
                            or link_helper_pair[0] in link_helper_defaults):
                        raise refusal from None
                    link_helper_defaults[link_helper_pair[0]] = link_helper_pair[1]
                link_helper_default_names = ('_type', '_vars', '_tuple', '_len', '_dict', '_str',
                    '_any', '_zip', '_all', '_set', '_error', '_value_error',
                    '_bool', '_int', '_list', '_bytes', '_bytearray', '_sum', '_ord', '_super')
                if link_raw_any(name not in link_helper_defaults for name in link_helper_default_names):
                    raise refusal from None
                link_helper_expected_builtins = link_raw_tuple(link_helper_defaults[name]
                    for name in link_helper_default_names)
                link_helper_system, link_helper_registry = link_pin_environment[0], link_pin_environment[2]
                if link_raw_type(link_helper_origin) is not link_raw_tuple or link_raw_len(link_helper_origin) != 8 or link_raw_type(link_helper_origin[0]) is not link_raw_module or (link_raw_type(link_helper_origin[1]) is not link_raw_dict) or (link_raw_type(link_helper_origin[2]) is not link_raw_tuple) or (link_raw_type(link_helper_origin[3]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[3]) != 4) or (link_raw_type(link_helper_origin[4]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[4]) != 3) or (link_raw_type(link_helper_origin[5]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[5]) != 3):
                    raise refusal from None
                link_seal_helper_module, link_seal_helper_namespace, link_seal_helper_pairs = link_helper_origin[:3]
                link_seal_helper_builtin_module, link_seal_helper_builtin_namespace, link_seal_helper_primitive_pairs = link_helper_origin[5]
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_helper_registry)) or link_helper_registry.get('hmp_startup.retained_binding_origin') is not link_seal_helper_module or link_raw_vars(link_seal_helper_module) is not link_seal_helper_namespace or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_namespace)) or (link_raw_len(link_seal_helper_namespace) != link_raw_len(link_seal_helper_pairs)) or (link_seal_helper_namespace.get('sys') is not link_helper_system) or (link_raw_type(link_seal_helper_builtin_module) is not link_raw_module) or (link_raw_type(link_seal_helper_builtin_namespace) is not link_raw_dict) or (link_helper_registry.get('builtins') is not link_seal_helper_builtin_module) or (link_raw_vars(link_seal_helper_builtin_module) is not link_seal_helper_builtin_namespace) or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_builtin_namespace)) or (link_seal_helper_namespace.get('__builtins__') is not link_seal_helper_builtin_namespace) or (link_raw_type(link_seal_helper_primitive_pairs) is not link_raw_tuple) or (link_raw_len(link_seal_helper_primitive_pairs) != 20):
                    raise refusal from None
                link_seal_helper_seen = {}
                for link_seal_helper_pair in link_seal_helper_pairs:
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                        raise refusal from None
                    link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                    if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_namespace or link_seal_helper_namespace[link_seal_helper_key] is not link_seal_helper_value:
                        raise refusal from None
                    link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                for link_seal_helper_pair, link_seal_helper_name, link_seal_helper_expected in link_raw_zip(link_seal_helper_primitive_pairs, ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set', 'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray', 'sum', 'ord', 'super'), link_helper_expected_builtins, strict=True):
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str or (link_seal_helper_pair[0] != link_seal_helper_name) or (link_seal_helper_pair[1] is not link_seal_helper_expected) or (link_seal_helper_builtin_namespace.get(link_seal_helper_name) is not link_seal_helper_expected):
                        raise refusal from None
                for link_seal_helper_row, link_seal_helper_name in link_raw_zip(link_helper_origin[3], ('capture', 'current', 'capture_bound', 'current_live'), strict=True):
                    if link_raw_type(link_seal_helper_row) is not link_raw_tuple or link_raw_len(link_seal_helper_row) != 7 or link_raw_type(link_seal_helper_row[0]) is not link_raw_str or (link_seal_helper_row[0] != link_seal_helper_name) or (link_raw_type(link_seal_helper_row[1]) is not link_raw_function) or (link_seal_helper_row[3] is not link_seal_helper_namespace) or (link_seal_helper_namespace.get(link_seal_helper_name) is not link_seal_helper_row[1]) or (link_seal_helper_row[1].__code__ is not link_seal_helper_row[2]) or (link_seal_helper_row[1].__globals__ is not link_seal_helper_namespace) or (link_seal_helper_row[1].__builtins__ is not link_seal_helper_builtin_namespace) or (link_seal_helper_row[1].__defaults__ is not link_seal_helper_row[4]) or (link_seal_helper_row[1].__kwdefaults__ is not link_seal_helper_row[5]) or (link_seal_helper_row[1].__closure__ is not None) or (link_raw_type(link_seal_helper_row[6]) is not link_raw_tuple):
                        raise refusal from None
                    link_seal_helper_kw, link_seal_helper_kw_pairs = (link_seal_helper_row[5], link_seal_helper_row[6])
                    if link_seal_helper_kw is None:
                        if link_raw_len(link_seal_helper_kw_pairs) != 0:
                            raise refusal from None
                    else:
                        if link_raw_type(link_seal_helper_kw) is not link_raw_dict or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_kw)) or link_raw_len(link_seal_helper_kw) != link_raw_len(link_seal_helper_kw_pairs):
                            raise refusal from None
                        link_seal_helper_seen = {}
                        for link_seal_helper_pair in link_seal_helper_kw_pairs:
                            if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                                raise refusal from None
                            link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                            if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_kw or link_seal_helper_kw[link_seal_helper_key] is not link_seal_helper_value:
                                raise refusal from None
                            link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                link_seal_helper_error_kind, link_seal_helper_error_bases, link_seal_helper_error_pairs = link_helper_origin[4]
                if link_raw_type(link_seal_helper_error_kind) is not link_raw_type or link_seal_helper_namespace.get('RetainedBindingOriginError') is not link_seal_helper_error_kind or link_raw_type(link_seal_helper_error_bases) is not link_raw_tuple or (link_raw_len(link_seal_helper_error_bases) != 1) or (link_seal_helper_error_bases[0] is not link_helper_expected_builtins[10]) or (link_seal_helper_error_kind.__bases__ is not link_seal_helper_error_bases) or (link_raw_type(link_seal_helper_error_pairs) is not link_raw_tuple):
                    raise refusal from None
                link_seal_helper_error_names = link_raw_vars(link_seal_helper_error_kind)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_error_names)) or link_raw_len(link_seal_helper_error_names) != link_raw_len(link_seal_helper_error_pairs) or '__init__' in link_seal_helper_error_names or ('__new__' in link_seal_helper_error_names):
                    raise refusal from None
                link_seal_helper_seen = {}
                for link_seal_helper_pair in link_seal_helper_error_pairs:
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                        raise refusal from None
                    link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                    if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_error_names or link_seal_helper_error_names[link_seal_helper_key] is not link_seal_helper_value:
                        raise refusal from None
                    link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                link_hdata_packet = link_helper_origin[6]
                link_helper_all = link_helper_expected_builtins[8]
                link_helper_set = link_helper_expected_builtins[9]
                link_helper_runtime_error = link_helper_expected_builtins[10]
                link_helper_value_error = link_helper_expected_builtins[11]
                link_helper_modules = link_helper_origin[1]['_MODULES']
                link_helper_classes = link_helper_origin[1]['_CLASSES']
                link_helper_functions = link_helper_origin[1]['_FUNCTIONS']
                link_helper_live_globals = link_helper_origin[1]['_LIVE_GLOBALS']
                if link_raw_type(link_helper_layout) is not link_raw_tuple or link_raw_len(link_helper_layout) != 4 or link_helper_layout[0] is not link_hdata_packet:
                    raise refusal from None
                if (link_raw_type(link_hdata_packet) is link_raw_tuple and link_raw_len(link_hdata_packet) == 6) is not True:
                    raise refusal from None
                link_hdata_system, link_hdata_system_names, link_hdata_registry, link_hdata_modules, link_hdata_classes, link_hdata_functions = link_hdata_packet
                if (link_raw_type(link_hdata_system) is link_raw_module and link_raw_type(link_hdata_system_names) is link_raw_dict and (link_raw_vars(link_hdata_system) is link_hdata_system_names) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_system_names)) and (link_raw_type(link_hdata_registry) is link_raw_dict) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_registry)) and (link_hdata_system_names.get('modules') is link_hdata_registry) and (link_raw_type(link_hdata_modules) is link_raw_tuple) and (link_raw_len(link_hdata_modules) == link_raw_len(link_helper_modules)) and (link_raw_type(link_hdata_classes) is link_raw_tuple) and (link_raw_len(link_hdata_classes) == link_raw_len(link_helper_classes)) and (link_raw_type(link_hdata_functions) is link_raw_tuple) and (link_raw_len(link_hdata_functions) == link_raw_len(link_helper_functions))) is not True:
                    raise refusal from None
                link_hdata_builtin_module = link_hdata_registry.get('builtins')
                if link_raw_type(link_hdata_builtin_module) is not link_raw_module:
                    raise refusal from None
                link_hdata_builtin_namespace = link_raw_vars(link_hdata_builtin_module)
                if (link_raw_type(link_hdata_builtin_namespace) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_builtin_namespace))) is not True:
                    raise refusal from None
                for link_hdata_row, link_hdata_name, link_hdata_live_keys, link_hdata_column in link_raw_zip(link_hdata_modules, link_helper_modules, link_helper_live_globals, link_helper_layout[1], strict=True):
                    link_hdata_module, link_hdata_namespace, link_hdata_pairs = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_module) is link_raw_module and link_raw_type(link_hdata_namespace) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_registry)) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and (link_hdata_registry.get(link_hdata_name) is link_hdata_module) and (link_raw_vars(link_hdata_module) is link_hdata_namespace) and (link_raw_type(link_hdata_namespace.get('__name__')) is link_raw_str) and (link_hdata_namespace['__name__'] == link_hdata_name) and (link_hdata_namespace.get('__builtins__') is link_hdata_builtin_namespace or link_hdata_namespace.get('__builtins__') is link_hdata_builtin_module) and (link_raw_len(link_hdata_namespace) == link_raw_len(link_hdata_keys) + link_raw_len(link_hdata_live_keys))) is not True:
                        raise refusal from None
                    link_hdata_expected_pairs = link_raw_dict(link_raw_zip(link_hdata_keys, link_hdata_values, strict=True))
                    link_hdata_valid, link_hdata_observed, link_hdata_live_seen = (True, 0, 0)
                    try:
                        for link_hdata_key, link_hdata_value in link_hdata_namespace.items():
                            if link_raw_type(link_hdata_key) is not link_raw_str:
                                link_hdata_valid = False
                                break
                            link_hdata_observed += 1
                            if link_hdata_key in link_hdata_live_keys:
                                link_hdata_live_seen += 1
                            elif link_hdata_key not in link_hdata_expected_pairs or link_hdata_expected_pairs[link_hdata_key] is not link_hdata_value:
                                link_hdata_valid = False
                                break
                    except link_helper_runtime_error:
                        link_hdata_valid = False
                    if (link_hdata_valid is True and link_hdata_observed == link_raw_len(link_hdata_keys) + link_raw_len(link_hdata_live_keys) and (link_hdata_live_seen == link_raw_len(link_hdata_live_keys))) is not True:
                        raise refusal from None
                for link_hdata_row, (link_hdata_index, link_hdata_name), link_hdata_column in link_raw_zip(link_hdata_classes, link_helper_classes, link_helper_layout[2], strict=True):
                    link_hdata_kind, link_hdata_bases, link_hdata_pairs = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_kind) is link_raw_type and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[link_hdata_index][1])) and (link_hdata_modules[link_hdata_index][1].get(link_hdata_name) is link_hdata_kind) and (link_hdata_kind.__bases__ is link_hdata_bases)) is not True:
                        raise refusal from None
                    link_hdata_names = link_raw_vars(link_hdata_kind)
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_names)) and link_raw_len(link_hdata_names) == link_raw_len(link_hdata_keys)) is not True:
                        raise refusal from None
                    for link_hdata_key, link_hdata_value in link_raw_zip(link_hdata_keys, link_hdata_values, strict=True):
                        if (link_hdata_key in link_hdata_names and link_hdata_names[link_hdata_key] is link_hdata_value) is not True:
                            raise refusal from None
                for link_hdata_row, (link_hdata_index, link_hdata_owner, link_hdata_name), link_hdata_column in link_raw_zip(link_hdata_functions, link_helper_functions, link_helper_layout[3], strict=True):
                    link_hdata_function, link_hdata_code, link_hdata_namespace, link_hdata_defaults, link_hdata_kw, link_hdata_pairs, link_hdata_closure, link_hdata_cells = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_namespace) is link_raw_dict and link_hdata_namespace is link_hdata_modules[link_hdata_index][1] and (link_raw_type(link_hdata_function) is link_raw_function) and (link_hdata_function.__globals__ is link_hdata_namespace) and (link_hdata_function.__builtins__ is link_hdata_builtin_namespace) and (link_hdata_function.__code__ is link_hdata_code) and (link_hdata_function.__defaults__ is link_hdata_defaults) and (link_hdata_function.__kwdefaults__ is link_hdata_kw) and (link_hdata_function.__closure__ is link_hdata_closure)) is not True:
                        raise refusal from None
                    link_hdata_names = link_hdata_namespace
                    if link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) is not True:
                        raise refusal from None
                    if link_hdata_owner is not None:
                        link_hdata_held_kind = None
                        for link_hdata_class_row, (link_hdata_class_index, link_hdata_class_name) in link_raw_zip(link_hdata_classes, link_helper_classes, strict=True):
                            if link_hdata_class_index == link_hdata_index and link_hdata_class_name == link_hdata_owner:
                                link_hdata_held_kind = link_hdata_class_row[0]
                                break
                        if (link_raw_type(link_hdata_held_kind) is link_raw_type and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and (link_hdata_namespace.get(link_hdata_owner) is link_hdata_held_kind)) is not True:
                            raise refusal from None
                        link_hdata_names = link_raw_vars(link_hdata_held_kind)
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_names)) and link_hdata_names.get(link_hdata_name) is link_hdata_function) is not True:
                        raise refusal from None
                    if link_hdata_kw is not None:
                        if (link_raw_type(link_hdata_kw) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_kw)) and (link_raw_len(link_hdata_kw) == link_raw_len(link_hdata_keys))) is not True:
                            raise refusal from None
                        for link_hdata_key, link_hdata_value in link_raw_zip(link_hdata_keys, link_hdata_values, strict=True):
                            if (link_hdata_key in link_hdata_kw and link_hdata_kw[link_hdata_key] is link_hdata_value) is not True:
                                raise refusal from None
                    if link_hdata_closure is not None:
                        if (link_raw_type(link_hdata_closure) is link_raw_tuple and link_raw_len(link_hdata_closure) == link_raw_len(link_hdata_cells)) is not True:
                            raise refusal from None
                        try:
                            if link_helper_all((link_raw_type(link_hdata_cell) is link_raw_cell and link_hdata_cell.cell_contents is link_hdata_value for link_hdata_cell, link_hdata_value in link_raw_zip(link_hdata_closure, link_hdata_cells, strict=True))) is not True:
                                raise refusal from None
                        except link_helper_value_error:
                            raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_hdata_modules[0][1].get('GatewayRecipeOwner') is link_hdata_classes[2][0] and (link_hdata_modules[0][1].get('_same_recipe_binding') is link_hdata_functions[4][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[1][1])) and (link_hdata_modules[0][1].get('StartupSelectionOwner') is link_hdata_classes[3][0]) and (link_hdata_modules[1][1].get('StartupSelectionOwner') is link_hdata_classes[3][0]) and (link_hdata_modules[0][1].get('GatewayStartupSelection') is link_hdata_classes[6][0]) and (link_hdata_modules[1][1].get('GatewayStartupSelection') is link_hdata_classes[6][0]) and (link_hdata_modules[0][1].get('IoScope') is link_hdata_classes[4][0]) and (link_hdata_modules[1][1].get('_Scope') is link_hdata_classes[4][0]) and (link_hdata_modules[1][1].get('_approved_recipe') is link_hdata_functions[6][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[1][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[2][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[3][1])) and (link_hdata_modules[0][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[1][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[2][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[2][1].get('_LATE_MODULES') is link_hdata_modules[3][1].get('_LATE_MODULES'))) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[4][1])) and link_hdata_modules[4][1].get('_Scope') is link_hdata_classes[4][0] and (link_hdata_modules[4][1].get('GatewayActivationOwner') is link_hdata_classes[10][0])) is not True:
                    raise refusal from None
                for link_hdata_index in (0, 1, 2):
                    link_hdata_namespace = link_hdata_modules[link_hdata_index][1]
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and link_hdata_namespace.get('ExpectedArtifact') is link_hdata_classes[13][0] and (link_hdata_namespace.get('_descriptor_closed_in_scope') is link_hdata_functions[15][0]) and (link_hdata_namespace.get('_expected') is link_hdata_functions[19][0])) is not True:
                        raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[5][1])) and link_hdata_modules[2][1].get('_APPROVAL_OWNER_TYPE') is link_hdata_classes[23][0] and (link_hdata_modules[5][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[5][1].get('_LATE_MODULES') is link_hdata_modules[3][1].get('_LATE_MODULES')) and (link_hdata_modules[5][1].get('ExpectedArtifact') is link_hdata_classes[13][0]) and (link_hdata_modules[5][1].get('_Scope') is link_hdata_classes[4][0]) and (link_hdata_modules[5][1].get('_descriptor_closed_in_scope') is link_hdata_functions[15][0]) and (link_hdata_modules[5][1].get('OperatorApprovalPath') is link_hdata_classes[38][0]) and (link_hdata_modules[5][1].get('_OperatorFileReceipt') is link_hdata_classes[39][0]) and (link_hdata_modules[5][1].get('_ReadEffect') is link_hdata_classes[40][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[6][1])) and link_hdata_modules[5][1].get('GatewayEntryOwner') is link_hdata_classes[27][0] and (link_hdata_modules[6][1].get('GatewayActivationOwner') is link_hdata_classes[10][0])) is not True:
                    raise refusal from None
                for (
                    link_runtime_consumer,
                    link_runtime_alias,
                    link_runtime_definition,
                    link_runtime_name,
                ) in (
                    (7, "_artifacts", 4, None),
                    (7, "_PRIVATE", 0, "_PRIVATE"),
                    (7, "_table_rows", 0, "_table_rows"),
                    (7, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (7, "_expected", 4, "_expected"),
                    (7, "_HashedArtifact", 4, "_HashedArtifact"),
                    (8, "GatewayActivationOwner", 3, "GatewayActivationOwner"),
                    (8, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
                    (8, "_same_origins", 0, "_same_origins"),
                    (8, "_Scan", 0, "_Scan"),
                    (8, "_table_rows", 0, "_table_rows"),
                    (8, "_Tree", 0, "_Tree"),
                    (8, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
                    (8, "_same_recipe_binding", 1, "_same_recipe_binding"),
                    (8, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (8, "StartupArtifactOwner", 4, "StartupArtifactOwner"),
                    (8, "_capture_native_scope", 4, "_capture_native_scope"),
                    (8, "_descriptor_closed_in_scope", 4, "_descriptor_closed_in_scope"),
                    (8, "_descriptor_refused", 4, "_descriptor_refused"),
                    (8, "_expected", 4, "_expected"),
                    (8, "_HashedArtifact", 4, "_HashedArtifact"),
                    (8, "_identity", 4, "_identity"),
                    (8, "_native_registration_tail", 4, "_native_registration_tail"),
                    (8, "_native_walk_scope", 4, "_native_walk_scope"),
                    (8, "_Scope", 4, "_Scope"),
                    (8, "gateway_entry", 6, None),
                    (8, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
                    (9, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
                    (9, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
                    (9, "_same_recipe_binding", 1, "_same_recipe_binding"),
                    (9, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (9, "RuntimeFilePlan", 7, "RuntimeFilePlan"),
                    (9, "RuntimePackage", 7, "RuntimePackage"),
                    (9, "plan_current", 7, "plan_current"),
                    (9, "EntryFileSnapshotOwner", 8, "EntryFileSnapshotOwner"),
                    (9, "_Inputs", 8, "_Inputs"),
                    (9, "_same_package", 8, "_same_package"),
                    (9, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
                    (9, "_origin_current", 6, "_origin_current"),
                ):
                    link_runtime_consumer_names = link_hdata_modules[link_runtime_consumer][1]
                    link_runtime_definition_names = link_hdata_modules[link_runtime_definition][1]
                    if not link_helper_all(
                        link_raw_type(link_runtime_key) is link_raw_str
                        for link_runtime_key in link_runtime_consumer_names
                    ) or not link_helper_all(
                        link_raw_type(link_runtime_key) is link_raw_str
                        for link_runtime_key in link_runtime_definition_names
                    ):
                        raise refusal from None
                    link_runtime_expected = (
                        link_hdata_modules[link_runtime_definition][0]
                        if link_runtime_name is None
                        else link_runtime_definition_names.get(link_runtime_name)
                    )
                    if (
                        (
                            link_runtime_name is not None
                            and link_runtime_name not in link_runtime_definition_names
                        )
                        or link_runtime_alias not in link_runtime_consumer_names
                        or link_runtime_consumer_names[link_runtime_alias]
                        is not link_runtime_expected
                    ):
                        raise refusal from None

                link_pin_encoding_origin = link_pin_environment[3]
                if link_raw_type(link_pin_encoding_origin) is not link_pin_types[9][0] or link_raw_tuple.__len__(link_pin_encoding_origin) != 7:
                    raise refusal from None
                link_pin_encoded_module, link_pin_encoded_namespace, link_pin_get_encoding, link_pin_get_errors, link_pin_encode, link_pin_encoding, link_pin_errors = link_pin_encoding_origin
                if link_pin_encoded_module is not link_pin_environment[0] or link_pin_encoded_namespace is not link_pin_environment[1] or link_raw_type(link_pin_get_encoding) is not link_raw_builtin or (link_raw_type(link_pin_get_errors) is not link_raw_builtin) or (link_pin_get_encoding.__self__ is not link_pin_encoded_module) or (link_pin_get_errors.__self__ is not link_pin_encoded_module) or (link_pin_get_encoding.__name__ != 'getfilesystemencoding') or (link_pin_get_errors.__name__ != 'getfilesystemencodeerrors') or (link_pin_encoded_namespace.get('getfilesystemencoding') is not link_pin_get_encoding) or (link_pin_encoded_namespace.get('getfilesystemencodeerrors') is not link_pin_get_errors) or (link_raw_type(link_pin_encode) is not link_raw_descriptor) or (link_pin_encode.__objclass__ is not link_raw_str) or (link_pin_encode.__name__ != 'encode') or (link_raw_vars(link_raw_str).get('encode') is not link_pin_encode) or (link_raw_type(link_pin_encoding) is not link_raw_str) or (link_raw_type(link_pin_errors) is not link_raw_str) or (not 1 <= link_raw_len(link_pin_encoding) <= 64) or (not 1 <= link_raw_len(link_pin_errors) <= 64) or link_raw_any((not (link_pin_c.isascii() and (link_pin_c.isalnum() or link_pin_c in '._-')) for link_pin_c in link_pin_encoding + link_pin_errors)):
                    raise refusal from None
                if (link_raw_type(link_engine_origin) is not link_raw_tuple
                        or link_raw_len(link_engine_origin) != 6
                        or link_pin_environment[4] is not link_engine_origin
                        or link_pin_environment[5] is not link_engine_origin[5]
                        or link_pin_environment[7] is not link_audit_record
                        or link_audit_record[0] is not link_engine_origin
                        or link_audit_record[1] is not link_engine_origin[5]):
                    raise refusal from None
                link_engine_dependencies = link_engine_origin[4]
                if (link_raw_type(link_engine_dependencies) is not link_raw_tuple
                        or link_raw_len(link_engine_dependencies) != 4
                        or link_engine_dependencies[0] is not link_pin_environment[0]
                        or link_engine_dependencies[1] is not link_pin_environment[1]
                        or link_engine_dependencies[2] is not link_pin_environment[2]):
                    raise refusal from None
                if link_raw_type(link_engine_dependencies) is not link_raw_tuple or link_raw_len(link_engine_dependencies) != 4 or link_raw_type(link_engine_dependencies[0]) is not link_raw_module or (link_raw_type(link_engine_dependencies[1]) is not link_raw_dict) or (link_raw_vars(link_engine_dependencies[0]) is not link_engine_dependencies[1]) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_dependencies[1])) or (link_raw_type(link_engine_dependencies[2]) is not link_raw_dict) or (link_engine_dependencies[1].get('modules') is not link_engine_dependencies[2]) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_dependencies[2])) or (link_raw_type(link_engine_dependencies[3]) is not link_raw_tuple) or (link_raw_len(link_engine_dependencies[3]) != 5):
                    raise refusal from None
                layout = link_engine_origin[5]
                if (link_raw_type(layout) is not link_raw_tuple or link_raw_len(layout) != 2
                        or layout[0] is not link_engine_dependencies or link_raw_type(layout[1]) is not link_raw_tuple
                        or link_raw_len(layout[1]) != link_raw_len(link_engine_dependencies[3])):
                    raise refusal from None
                for layout_row, layout_module in link_raw_zip(layout[1], link_engine_dependencies[3], strict=True):
                    if (link_raw_type(layout_row) is not link_raw_tuple or link_raw_len(layout_row) != 2
                            or layout_row[0] is not layout_module
                            or link_raw_type(layout_module) is not link_raw_tuple or link_raw_len(layout_module) != 6
                            or link_raw_type(layout_module[4]) is not link_raw_tuple
                            or link_raw_type(layout_row[1]) is not link_raw_tuple
                            or link_raw_len(layout_row[1]) != link_raw_len(layout_module[4])):
                        raise refusal from None
                    for layout_class_row, layout_class in link_raw_zip(layout_row[1], layout_module[4], strict=True):
                        if (link_raw_type(layout_class_row) is not link_raw_tuple or link_raw_len(layout_class_row) != 3
                                or layout_class_row[0] is not layout_class
                                or link_raw_type(layout_class) is not link_raw_tuple or link_raw_len(layout_class) != 3
                                or link_raw_type(layout_class[2]) is not link_raw_tuple
                                or link_raw_type(layout_class_row[1]) is not link_raw_tuple
                                or link_raw_type(layout_class_row[2]) is not link_raw_tuple
                                or link_raw_len(layout_class_row[1]) != link_raw_len(layout_class[2])
                                or link_raw_len(layout_class_row[2]) != link_raw_len(layout_class[2])):
                            raise refusal from None
                        layout_seen = {}
                        for layout_pair, layout_key, layout_value in link_raw_zip(
                                layout_class[2], layout_class_row[1], layout_class_row[2], strict=True):
                            if (link_raw_type(layout_pair) is not link_raw_tuple or link_raw_len(layout_pair) != 2
                                    or link_raw_type(layout_key) is not link_raw_str
                                    or layout_pair[0] is not layout_key
                                    or layout_pair[1] is not layout_value
                                    or layout_key in layout_seen):
                                raise refusal from None
                            layout_seen[layout_key] = layout_value
                link_engine_checked_namespaces = []
                link_engine_expected_modules = ('hmp_plugin.presentation_native_link', 'hmp_plugin.presentation_native_metadata', 'hmp_plugin.presentation_startup_artifacts', 'hmp_plugin.presentation_metadata_custody', 'hmp_plugin.presentation_link_path_policy')
                for link_engine_row, link_engine_expected_name in link_raw_zip(link_engine_dependencies[3], link_engine_expected_modules, strict=True):
                    if link_raw_type(link_engine_row) is not link_raw_tuple or link_raw_len(link_engine_row) != 6 or link_raw_type(link_engine_row[0]) is not link_raw_str or (link_engine_row[0] != link_engine_expected_name) or (link_raw_type(link_engine_row[1]) is not link_raw_module) or (link_raw_type(link_engine_row[2]) is not link_raw_dict) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_row[2])) or (link_engine_dependencies[2].get(link_engine_expected_name) is not link_engine_row[1]) or (link_raw_vars(link_engine_row[1]) is not link_engine_row[2]) or (link_raw_type(link_engine_row[3]) is not link_raw_tuple) or (link_raw_len(link_engine_row[2]) != link_raw_len(link_engine_row[3])) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_row[2]) or (link_engine_row[2][link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_row[3])) or (link_raw_type(link_engine_row[4]) is not link_raw_tuple) or (link_raw_type(link_engine_row[5]) is not link_raw_tuple):
                        raise refusal from None
                    link_engine_checked_namespaces.append(link_engine_row[2])
                    for link_engine_class_row in link_engine_row[4]:
                        if link_raw_type(link_engine_class_row) is not link_raw_tuple or link_raw_len(link_engine_class_row) != 3:
                            raise refusal from None
                        link_engine_kind, link_engine_bases, link_engine_members = link_engine_class_row
                        if link_raw_type(link_engine_kind) is not link_raw_type or link_engine_kind.__bases__ is not link_engine_bases:
                            raise refusal from None
                        link_engine_names = link_raw_vars(link_engine_kind)
                        if link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_names)) or link_raw_type(link_engine_members) is not link_raw_tuple or link_raw_len(link_engine_names) != link_raw_len(link_engine_members) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_names) or (link_engine_names[link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_members)):
                            raise refusal from None
                    for link_engine_function_row in link_engine_row[5]:
                        if link_raw_type(link_engine_function_row) is not link_raw_tuple or link_raw_len(link_engine_function_row) != 8:
                            raise refusal from None
                        link_engine_function, link_engine_code, link_engine_namespace, link_engine_defaults, link_engine_kw, link_engine_pairs, link_engine_closure, link_engine_cells = link_engine_function_row
                        if link_raw_type(link_engine_function) is not link_raw_function or link_engine_function.__code__ is not link_engine_code or link_engine_function.__globals__ is not link_engine_namespace or (link_raw_type(link_engine_namespace) is not link_raw_dict) or (link_engine_function.__defaults__ is not link_engine_defaults) or (link_engine_function.__kwdefaults__ is not link_engine_kw) or (link_raw_type(link_engine_pairs) is not link_raw_tuple) or (link_engine_function.__closure__ is not link_engine_closure) or (link_raw_type(link_engine_cells) is not link_raw_tuple):
                            raise refusal from None
                        if not link_raw_any((link_engine_namespace is link_engine_prior for link_engine_prior in link_engine_checked_namespaces)):
                            if link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_namespace)):
                                raise refusal from None
                            link_engine_checked_namespaces.append(link_engine_namespace)
                        if link_engine_kw is None:
                            if link_raw_len(link_engine_pairs) != 0:
                                raise refusal from None
                        elif link_raw_type(link_engine_kw) is not link_raw_dict or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_kw)) or link_raw_len(link_engine_kw) != link_raw_len(link_engine_pairs) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_kw) or (link_engine_kw[link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_pairs)):
                            raise refusal from None
                        if link_engine_closure is None:
                            if link_raw_len(link_engine_cells) != 0:
                                raise refusal from None
                        elif link_raw_type(link_engine_closure) is not link_raw_tuple or link_raw_len(link_engine_closure) != link_raw_len(link_engine_cells) or link_raw_any((link_raw_type(link_engine_cell) is not link_raw_cell or link_engine_cell.cell_contents is not link_engine_value for link_engine_cell, link_engine_value in link_raw_zip(link_engine_closure, link_engine_cells, strict=True))):
                            raise refusal from None
                link_primitive_audit_rows = link_raw_tuple((row for row in link_engine_origin[2] if link_raw_type(row) is link_raw_tuple and link_raw_len(row) == 7 and (link_raw_type(row[0]) is link_raw_str) and (row[0] == '_engine_origin_tail')))
                if (link_raw_len(link_primitive_audit_rows) != 1
                        or link_primitive_audit_rows[0] is not link_audit_record[2]):
                    raise refusal from None
                link_primitive_audit_checker, link_primitive_audit_kw = (link_primitive_audit_rows[0][1], link_primitive_audit_rows[0][5])
                if link_raw_type(link_primitive_audit_checker) is not link_raw_function or link_raw_type(link_primitive_audit_kw) is not link_raw_dict or link_primitive_audit_checker.__kwdefaults__ is not link_primitive_audit_kw or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_kw)):
                    raise refusal from None
                link_primitive_audit_pairs = link_primitive_audit_rows[0][6]
                if (link_raw_type(link_primitive_audit_pairs) is not link_raw_tuple
                        or link_raw_len(link_primitive_audit_kw) != link_raw_len(link_primitive_audit_pairs)):
                    raise refusal from None
                link_primitive_audit_originals = {}
                for link_primitive_audit_pair in link_primitive_audit_pairs:
                    if (link_raw_type(link_primitive_audit_pair) is not link_raw_tuple
                            or link_raw_len(link_primitive_audit_pair) != 2
                            or link_raw_type(link_primitive_audit_pair[0]) is not link_raw_str):
                        raise refusal from None
                    link_primitive_audit_name, link_primitive_audit_expected = link_primitive_audit_pair
                    if (link_primitive_audit_name in link_primitive_audit_originals
                            or link_primitive_audit_name not in link_primitive_audit_kw
                            or link_primitive_audit_kw[link_primitive_audit_name] is not link_primitive_audit_expected):
                        raise refusal from None
                    link_primitive_audit_originals[link_primitive_audit_name] = link_primitive_audit_expected
                link_primitive_audit_id = link_primitive_audit_originals.get('_id')
                link_primitive_audit_map = link_primitive_audit_originals.get('_map')
                link_primitive_audit_not = link_primitive_audit_originals.get('_not_identity')
                if link_raw_type(link_primitive_audit_id) is not link_raw_builtin or link_primitive_audit_id.__name__ != 'id' or link_raw_type(link_primitive_audit_id.__self__) is not link_raw_module or (link_engine_dependencies[2].get('builtins') is not link_primitive_audit_id.__self__):
                    raise refusal from None
                link_primitive_audit_builtins = link_raw_vars(link_primitive_audit_id.__self__)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_builtins)) or link_primitive_audit_checker.__builtins__ is not link_primitive_audit_builtins:
                    raise refusal from None
                for link_primitive_audit_name, link_primitive_audit_value in (('type', link_raw_type), ('tuple', link_raw_tuple), ('dict', link_raw_dict), ('str', link_raw_str), ('len', link_raw_len), ('vars', link_raw_vars), ('any', link_raw_any), ('zip', link_raw_zip), ('id', link_primitive_audit_id), ('map', link_primitive_audit_map)):
                    if link_primitive_audit_builtins.get(link_primitive_audit_name) is not link_primitive_audit_value or link_primitive_audit_originals.get('_' + link_primitive_audit_name) is not link_primitive_audit_value:
                        raise refusal from None
                if link_raw_type(link_primitive_audit_map) is not link_raw_type:
                    raise refusal from None
                link_primitive_audit_map_names = link_raw_vars(link_primitive_audit_map)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_map_names)):
                    raise refusal from None
                link_primitive_audit_new = link_primitive_audit_map_names.get('__new__')
                if link_raw_type(link_primitive_audit_new) is not link_raw_builtin or link_primitive_audit_new.__self__ is not link_primitive_audit_map or link_primitive_audit_new.__name__ != '__new__' or (link_primitive_audit_map.__name__ != 'map') or (link_primitive_audit_map.__module__ != 'builtins') or (link_raw_type(link_primitive_audit_not) is not link_raw_builtin) or (link_primitive_audit_not.__name__ != 'is_not') or (link_raw_type(link_primitive_audit_not.__self__) is not link_raw_module) or (link_engine_dependencies[2].get('_operator') is not link_primitive_audit_not.__self__):
                    raise refusal from None
                link_primitive_audit_operator = link_raw_vars(link_primitive_audit_not.__self__)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_operator)) or link_primitive_audit_operator.get('is_not') is not link_primitive_audit_not:
                    raise refusal from None
                # LAST pure publication seal: no origin/tail/cohort helper
                # is called after this block before assigning actual scope slots.
                if (owner_namespace.get('StartupArtifactOwner') is not owner_kind
                        or link_raw_type(owner) is not owner_kind
                        or _Scope is not kind or type(s) is not kind
                        or vars(kind).get('_fields') is not fields
                        or any(vars(kind).get(name) is not member
                               for name, member in zip(fields, members, strict=True))
                        or any(vars(kind).get(name) is not member
                               for name, member in zip(dispatch_names, dispatch, strict=True))
                        or constructor.__code__ is not constructor_code
                        or tuple.__len__(s) != len(values)
                        or any(tuple.__getitem__(s, i) is not value
                               for i, value in enumerate(values))
                        or failure_owner_dictionary(owner, owner_kind) is not owner_dict
                        or type(records) is not list or len(records) != 0
                        or type(reads) is not list or len(reads) != 0
                        or type(slot) is not list or len(slot) != 1 or slot[0] is not None):
                    raise refusal from None
                for names, entries in link_cohort[0]:
                    if (any(type(k) is not str for k in names) or len(names) != len(entries)
                            or any(k not in names or names[k] is not value for k, value in entries)):
                        raise refusal from None
                for cells, entries in link_cohort[1]:
                    if (len(cells) != len(entries)
                            or any(cells[i] is not value for i, value in enumerate(entries))):
                        raise refusal from None
                for selected, entries, functions in link_cohort[2]:
                    names = vars(selected)
                    if (any(type(k) is not str for k in names) or len(names) != len(entries)
                            or any(k not in names or names[k] is not value for k, value in entries)):
                        raise refusal from None
                    for function, code, defaults, kw, pairs in functions:
                        if (function.__code__ is not code or function.__defaults__ is not defaults
                                or function.__kwdefaults__ is not kw
                                or (kw is not None and (any(type(k) is not str for k in kw)
                                    or len(kw) != len(pairs)
                                    or any(k not in kw or kw[k] is not value for k, value in pairs)))):
                            raise refusal from None
            owner._scope = owner._origin = s
            owner._cell = (owner, s)
            owner._root_cell = (activation, owner, s)
            activation._artifact_cell = owner._root_cell
            scope_cell, scope_root = owner._cell, owner._root_cell
            owner._count_cell = owner._initial_count_cell = (owner, s, owner._bytes_read)
            if runtime is not None:
                if (type(runtime) is _RuntimeSource and len(runtime.inputs.io_slot) == 1
                         and runtime.inputs.io_slot[0] is None
                         and runtime.plan.pending is expected) is not True:
                    raise refusal from None
                runtime.guard(runtime.entry, runtime.inputs, runtime.cell)
                if (runtime.inputs.io_slot[0] is None) is not True:
                    raise refusal from None
                runtime.inputs.io_slot[0] = owner
                runtime.count[0] = owner._initial_count_cell
                if (len(source.expected) + len(expected) + len(runtime.link.hops) <= _MAX_FILES
                         and owner._bytes_read + sum(row.size for row in expected)
                         + 2 * runtime.link.text_bytes <= _MAX_TOTAL) is not True:
                    raise refusal from None
            if cache is not None:
                from .presentation_startup_cache import source_current
                source_current(cache)
                if (cache.plan.pending is expected
                         and (cache.inputs.io_slot[0] is None or cache.inputs.io_slot[0] is owner)
                         and len(source.expected) + len(expected) + len(cache.paths)
                         + (0 if runtime is None else len(runtime.link.hops)) <= _MAX_FILES) is not True:
                    raise refusal from None
                cache.inputs.io_slot[0] = owner
            _expected(expected)
            if source is not None:
                _source_current(source)
                _expected(source.expected + expected)
            StartupArtifactOwner._guard(owner)
            if link_blueprint is not None:
                link_rejoin()
                if (link_tail(link_blueprint) is link_blueprint) is not True:
                    raise refusal from None
                link_rejoin()
                if (item(s, 17) is link_blueprint
                     and owner_dict.get('_scope') is s and owner_dict.get('_origin') is s
                     and owner_dict.get('_cell') is scope_cell
                     and owner_dict.get('_root_cell') is scope_root
                     and vars(activation).get('_artifact_cell') is scope_root) is not True:
                    raise refusal from None
                if (globals() is not root_namespace
                        or any(type(k) is not str for k in root_namespace)
                        or len(root_namespace) != len(root_namespace_entries)
                        or any(k not in root_namespace or root_namespace[k] is not value
                               for k, value in root_namespace_entries)):
                    raise refusal from None
                for function, code, defaults, kw, pairs in root_helper_pins:
                    if (function.__code__ is not code or function.__defaults__ is not defaults
                            or function.__kwdefaults__ is not kw
                            or (kw is not None and (any(type(k) is not str for k in kw)
                                or len(kw) != len(pairs)
                                or any(k not in kw or kw[k] is not value for k, value in pairs)))):
                        raise refusal from None
                if (tuple.__getitem__(runtime, 0) is not runtime_entry
                        or tuple.__getitem__(runtime, 1) is not runtime_entry_kind
                        or tuple.__getitem__(runtime, 2) is not runtime_inputs
                        or tuple.__getitem__(runtime, 3) is not runtime_cell
                        or tuple.__getitem__(runtime, 6) is not runtime_original_plan
                        or tuple.__getitem__(runtime, 7) is not runtime_original_link
                        or type(runtime_inputs) is not runtime_input_kind
                        or runtime_entry_names.get('_inputs') is not runtime_inputs
                        or runtime_entry_names.get('_root_cell') is not runtime_cell
                        or tuple.__getitem__(runtime_inputs, 12) is not runtime_original_plan
                        or tuple.__getitem__(runtime_original_plan, 14) is not runtime_original_link
                        or tuple.__getitem__(runtime_original_plan, 7) is not expected
                        or source is not original_package_source
                        or tuple.__getitem__(source, 1) is not source_package_binding
                        or tuple.__getitem__(runtime_inputs, 5) is not input_package_binding
                        or tuple.__getitem__(s, 5) is not original_package_source
                        or tuple.__getitem__(runtime_inputs, 4) is not tuple.__getitem__(source, 0)):
                    raise refusal from None
                # Rejoin actual source/entry pointer identities without calling
                # a current getter after the last callback-bearing origin seal.
                if (tuple.__getitem__(digest_context, 0) is not origin_invocation_owner
                        or link_raw_type(origin_invocation_owner) is not origin_invocation_kind
                        or origin_dict_get(origin_invocation_owner, origin_invocation_kind) is not origin_invocation_names
                        or link_raw_any(link_raw_type(k) is not link_raw_str
                                        for k in origin_invocation_names)
                        or origin_invocation_names.get('_scope') is not invocation
                        or tuple.__getitem__(digest_context, 1) is not digest_binding
                        or tuple.__getitem__(digest_context, 5) is not native_files
                        or tuple.__getitem__(invocation, 9) is not native_files
                        or tuple.__getitem__(started, 5) is not entry_origin
                        or tuple.__getitem__(native_files, 4) is not link_origin
                        or tuple.__getitem__(entry_origin, 10) is not link_origin
                        or tuple.__getitem__(entry_origin, 11) is not link_audit_record
                        or tuple.__getitem__(native_files, 5) is not link_audit_record
                        or tuple.__getitem__(s, 18) is not link_audit_record
                        or link_origin[0][7] is not link_audit_record
                        or origin_entry_names.get('_ENTRY_ORIGIN') is not entry_origin
                        or origin_entry_names.get('_STARTED') is not started
                        or origin_entry_names.get('_OWNER') is not tuple.__getitem__(digest_context, 0)
                        or origin_entry_names.get('_CELL') is not digest_binding[1]):
                    raise refusal from None
                if link_raw_type(link_origin) is not link_raw_tuple or link_raw_len(link_origin) != 5:
                    raise refusal from None
                link_pin_environment, link_pin_modules, link_pin_own_functions, link_pin_policy_functions, link_pin_types = link_origin
                if (
                    link_raw_type(link_pin_environment) is not link_raw_tuple
                    or link_raw_len(link_pin_environment) != 8
                    or link_raw_type(link_pin_environment[0]) is not link_raw_module
                    or (link_raw_type(link_pin_environment[1]) is not link_raw_dict)
                    or (link_raw_vars(link_pin_environment[0]) is not link_pin_environment[1])
                    or link_raw_any(
                        link_raw_type(link_pin_k) is not link_raw_str
                        for link_pin_k in link_pin_environment[1]
                    )
                    or (link_raw_type(link_pin_environment[2]) is not link_raw_dict)
                    or link_raw_any(
                        link_raw_type(link_pin_k) is not link_raw_str
                        for link_pin_k in link_pin_environment[2]
                    )
                    or (link_pin_environment[1].get("modules") is not link_pin_environment[2])
                    or (link_raw_type(link_pin_modules) is not link_raw_tuple)
                    or (link_raw_len(link_pin_modules) != 6)
                    or (link_raw_type(link_pin_own_functions) is not link_raw_tuple)
                    or (link_raw_type(link_pin_policy_functions) is not link_raw_tuple)
                    or (link_raw_type(link_pin_types) is not link_raw_tuple)
                    or (link_raw_len(link_pin_types) != 15)
                ):
                    raise refusal from None
                link_pin_names = (
                    "hmp_startup.link_factory_origin",
                    "hmp_plugin.presentation_link_path_policy",
                    "hmp_plugin.presentation_startup_artifacts",
                    "hmp_startup.runtime_files",
                    "hmp_startup.entry_files",
                    "hmp_startup.cache_context",
                )
                for link_pin_row, link_pin_name in link_raw_zip(link_pin_modules, link_pin_names, strict=True):
                    if link_raw_type(link_pin_row) is not link_raw_tuple or link_raw_len(link_pin_row) != 3 or link_raw_type(link_pin_row[0]) is not link_raw_str or (link_pin_row[0] != link_pin_name) or (link_raw_type(link_pin_row[1]) is not link_raw_module) or (link_raw_type(link_pin_row[2]) is not link_raw_dict) or link_raw_any((link_raw_type(link_pin_k) is not link_raw_str for link_pin_k in link_pin_row[2])) or (link_pin_environment[2].get(link_pin_name) is not link_pin_row[1]) or (link_raw_vars(link_pin_row[1]) is not link_pin_row[2]) or (link_raw_type(link_pin_row[2].get('__name__')) is not link_raw_str) or (link_pin_row[2]['__name__'] != link_pin_name):
                        raise refusal from None
                if link_pin_modules[0][2].get('_CAPTURE_STARTED') is not True:
                    raise refusal from None
                link_pin_own_names = ('_pin_function', '_pin_type', 'capture', 'current', 'factory', 'blueprint_factory', 'encode_basename', 'current_started')
                link_pin_policy_names = ('_need', '_parts', '_policy_tail', '_new_policy', '_sites', '_directory', '_leaf', '_cursor_tail', '_start', '_action', '_advance', '_outcome', '_scope_blueprint_guard', '_scope_blueprint_cohort', '_scope_blueprint_tail', '_new_scope_blueprint')
                for link_pin_rows, link_pin_expected, link_pin_namespace in ((link_pin_own_functions, link_pin_own_names, link_pin_modules[0][2]), (link_pin_policy_functions, link_pin_policy_names, link_pin_modules[1][2])):
                    if link_raw_len(link_pin_rows) != link_raw_len(link_pin_expected):
                        raise refusal from None
                    for link_pin_row, link_pin_name in link_raw_zip(link_pin_rows, link_pin_expected, strict=True):
                        if link_raw_type(link_pin_row) is not link_raw_tuple or link_raw_len(link_pin_row) != 7 or link_raw_type(link_pin_row[0]) is not link_raw_str or (link_pin_row[0] != link_pin_name) or (link_raw_type(link_pin_row[1]) is not link_raw_function) or (link_pin_row[3] is not link_pin_namespace) or (link_pin_namespace.get(link_pin_name) is not link_pin_row[1]) or (link_pin_row[1].__code__ is not link_pin_row[2]) or (link_pin_row[1].__globals__ is not link_pin_namespace) or (link_pin_row[1].__defaults__ is not link_pin_row[4]) or (link_pin_row[1].__closure__ is not None) or (link_raw_type(link_pin_row[6]) is not link_raw_tuple):
                            raise refusal from None
                        link_pin_kw = link_pin_row[1].__kwdefaults__
                        if link_pin_kw is not link_pin_row[5]:
                            raise refusal from None
                        if link_pin_kw is None:
                            if link_pin_row[6] != ():
                                raise refusal from None
                        elif link_raw_type(link_pin_kw) is not link_raw_dict or link_raw_any((link_raw_type(link_pin_k) is not link_raw_str for link_pin_k in link_pin_kw)) or link_raw_len(link_pin_kw) != link_raw_len(link_pin_row[6]) or link_raw_any((link_raw_type(link_pin_pair) is not link_raw_tuple or link_raw_len(link_pin_pair) != 2 or link_raw_type(link_pin_pair[0]) is not link_raw_str or (link_pin_pair[0] not in link_pin_kw) or (link_pin_kw[link_pin_pair[0]] is not link_pin_pair[1]) for link_pin_pair in link_pin_row[6])):
                            raise refusal from None
                link_pin_exports = (
                    (1, "_LinkPathPolicy"),
                    (1, "_LinkPathCursor"),
                    (2, "ExpectedArtifact"),
                    (3, "RuntimeFilePlan"),
                    (3, "ExecutableLinkPlan"),
                    (3, "LinkHop"),
                    (1, "_LinkScopeBlueprint"),
                    (2, "_RuntimeSource"),
                    (2, "_Scope"),
                    (0, "_FilesystemEncodingOrigin"),
                    (0, "_EncodedBasename"),
                    (3, "RuntimePackage"),
                    (4, "_Inputs"),
                    (5, "CacheInputData"),
                    (5, "_ContextSource"),
                )
                for link_pin_pin, (link_pin_module_index, link_pin_name) in link_raw_zip(
                    link_pin_types, link_pin_exports, strict=True
                ):
                    if (
                        link_raw_type(link_pin_pin) is not link_raw_tuple
                        or link_raw_len(link_pin_pin) != 12
                        or link_raw_type(link_pin_pin[0]) is not link_raw_type
                        or (
                            link_pin_modules[link_pin_module_index][2].get(link_pin_name)
                            is not link_pin_pin[0]
                        )
                        or (link_raw_type(link_pin_pin[1]) is not link_raw_tuple)
                        or link_raw_any(
                            link_raw_type(link_pin_n) is not link_raw_str
                            for link_pin_n in link_pin_pin[1]
                        )
                        or (link_raw_type(link_pin_pin[2]) is not link_raw_tuple)
                        or (link_raw_len(link_pin_pin[2]) != link_raw_len(link_pin_pin[1]))
                        or (link_raw_type(link_pin_pin[3]) is not link_raw_function)
                        or (link_raw_type(link_pin_pin[5]) is not link_raw_dict)
                        or link_raw_any(
                            link_raw_type(link_pin_k) is not link_raw_str
                            for link_pin_k in link_pin_pin[5]
                        )
                        or (link_raw_type(link_pin_pin[8]) is not link_raw_tuple)
                    ):
                        raise refusal from None
                    (
                        link_pin_kind,
                        link_pin_fields,
                        link_pin_members,
                        link_pin_constructor,
                        link_pin_code,
                        link_pin_globals_,
                        link_pin_defaults,
                        link_pin_bases,
                        link_pin_dispatch,
                        link_pin_constructor_kw,
                        link_pin_constructor_kw_pairs,
                        link_pin_constructor_global_pairs,
                    ) = link_pin_pin
                    link_pin_namespace = link_raw_vars(link_pin_kind)
                    if link_raw_any(
                        link_raw_type(constructor_key) is not link_raw_str
                        for constructor_key in link_pin_namespace
                    ):
                        raise refusal from None
                    link_pin_actual = link_pin_namespace.get("__new__")
                    if link_raw_type(link_pin_actual) is link_raw_staticmethod:
                        link_pin_actual = link_pin_actual.__func__
                    if (
                        link_pin_namespace.get("_fields") is not link_pin_fields
                        or link_pin_actual is not link_pin_constructor
                        or link_pin_constructor.__code__ is not link_pin_code
                        or (link_pin_constructor.__globals__ is not link_pin_globals_)
                        or (link_pin_constructor.__defaults__ is not link_pin_defaults)
                        or (link_pin_kind.__bases__ is not link_pin_bases)
                        or (link_pin_globals_.get("_tuple_new") is not link_raw_tuple.__new__)
                        or link_raw_any(
                            (
                                link_pin_namespace.get(link_pin_n) is not link_pin_member
                                for link_pin_n, link_pin_member in link_raw_zip(
                                    link_pin_fields, link_pin_members, strict=True
                                )
                            )
                        )
                        or link_raw_any(
                            link_raw_type(link_pin_row) is not link_raw_tuple
                            or link_raw_len(link_pin_row) != 2
                            or link_raw_type(link_pin_row[0]) is not link_raw_str
                            or (link_pin_namespace.get(link_pin_row[0]) is not link_pin_row[1])
                            for link_pin_row in link_pin_dispatch
                        )
                    ):
                        raise refusal from None
                    if (
                        link_raw_type(link_pin_constructor) is not link_raw_function
                        or link_pin_constructor.__kwdefaults__ is not link_pin_constructor_kw
                        or link_pin_constructor.__closure__ is not None
                        or link_raw_type(link_pin_constructor.__code__.co_filename)
                        is not link_raw_str
                        or (
                            link_pin_defaults is not None
                            and link_raw_type(link_pin_defaults) is not link_raw_tuple
                        )
                    ):
                        raise refusal from None
                    for constructor_namespace, constructor_pairs in (
                        (link_pin_globals_, link_pin_constructor_global_pairs),
                        (link_pin_constructor_kw, link_pin_constructor_kw_pairs),
                    ):
                        if link_raw_type(constructor_pairs) is not link_raw_tuple:
                            raise refusal from None
                        if constructor_namespace is None:
                            if link_raw_len(constructor_pairs) != 0:
                                raise refusal from None
                            continue
                        if link_raw_type(
                            constructor_namespace
                        ) is not link_raw_dict or link_raw_len(
                            constructor_namespace
                        ) != link_raw_len(constructor_pairs):
                            raise refusal from None
                        constructor_expected = {}
                        for constructor_pair in constructor_pairs:
                            if (
                                link_raw_type(constructor_pair) is not link_raw_tuple
                                or link_raw_len(constructor_pair) != 2
                                or link_raw_type(constructor_pair[0]) is not link_raw_str
                                or constructor_pair[0] in constructor_expected
                            ):
                                raise refusal from None
                            constructor_expected[constructor_pair[0]] = constructor_pair[1]
                        for constructor_key, constructor_value in constructor_namespace.items():
                            if (
                                link_raw_type(constructor_key) is not link_raw_str
                                or constructor_key not in constructor_expected
                                or constructor_expected[constructor_key] is not constructor_value
                            ):
                                raise refusal from None
                # Original retained-helper prefix and DATA, with no final callback.
                if (link_pin_environment[6] is not link_helper_origin
                        or link_helper_origin[7] is not link_helper_record
                        or link_helper_record[0] is not link_helper_origin[6]
                        or link_helper_record[1] is not link_helper_layout
                        or link_helper_record[2] is not link_helper_origin[3][3]):
                    raise refusal from None
                link_helper_default_pairs = link_pin_own_functions[2][6]
                link_helper_defaults = {}
                for link_helper_pair in link_helper_default_pairs:
                    if (link_raw_type(link_helper_pair) is not link_raw_tuple
                            or link_raw_len(link_helper_pair) != 2
                            or link_raw_type(link_helper_pair[0]) is not link_raw_str
                            or link_helper_pair[0] in link_helper_defaults):
                        raise refusal from None
                    link_helper_defaults[link_helper_pair[0]] = link_helper_pair[1]
                link_helper_default_names = ('_type', '_vars', '_tuple', '_len', '_dict', '_str',
                    '_any', '_zip', '_all', '_set', '_error', '_value_error',
                    '_bool', '_int', '_list', '_bytes', '_bytearray', '_sum', '_ord', '_super')
                if link_raw_any(name not in link_helper_defaults for name in link_helper_default_names):
                    raise refusal from None
                link_helper_expected_builtins = link_raw_tuple(link_helper_defaults[name]
                    for name in link_helper_default_names)
                link_helper_system, link_helper_registry = link_pin_environment[0], link_pin_environment[2]
                if link_raw_type(link_helper_origin) is not link_raw_tuple or link_raw_len(link_helper_origin) != 8 or link_raw_type(link_helper_origin[0]) is not link_raw_module or (link_raw_type(link_helper_origin[1]) is not link_raw_dict) or (link_raw_type(link_helper_origin[2]) is not link_raw_tuple) or (link_raw_type(link_helper_origin[3]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[3]) != 4) or (link_raw_type(link_helper_origin[4]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[4]) != 3) or (link_raw_type(link_helper_origin[5]) is not link_raw_tuple) or (link_raw_len(link_helper_origin[5]) != 3):
                    raise refusal from None
                link_seal_helper_module, link_seal_helper_namespace, link_seal_helper_pairs = link_helper_origin[:3]
                link_seal_helper_builtin_module, link_seal_helper_builtin_namespace, link_seal_helper_primitive_pairs = link_helper_origin[5]
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_helper_registry)) or link_helper_registry.get('hmp_startup.retained_binding_origin') is not link_seal_helper_module or link_raw_vars(link_seal_helper_module) is not link_seal_helper_namespace or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_namespace)) or (link_raw_len(link_seal_helper_namespace) != link_raw_len(link_seal_helper_pairs)) or (link_seal_helper_namespace.get('sys') is not link_helper_system) or (link_raw_type(link_seal_helper_builtin_module) is not link_raw_module) or (link_raw_type(link_seal_helper_builtin_namespace) is not link_raw_dict) or (link_helper_registry.get('builtins') is not link_seal_helper_builtin_module) or (link_raw_vars(link_seal_helper_builtin_module) is not link_seal_helper_builtin_namespace) or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_builtin_namespace)) or (link_seal_helper_namespace.get('__builtins__') is not link_seal_helper_builtin_namespace) or (link_raw_type(link_seal_helper_primitive_pairs) is not link_raw_tuple) or (link_raw_len(link_seal_helper_primitive_pairs) != 20):
                    raise refusal from None
                link_seal_helper_seen = {}
                for link_seal_helper_pair in link_seal_helper_pairs:
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                        raise refusal from None
                    link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                    if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_namespace or link_seal_helper_namespace[link_seal_helper_key] is not link_seal_helper_value:
                        raise refusal from None
                    link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                for link_seal_helper_pair, link_seal_helper_name, link_seal_helper_expected in link_raw_zip(link_seal_helper_primitive_pairs, ('type', 'vars', 'tuple', 'len', 'dict', 'str', 'any', 'zip', 'all', 'set', 'RuntimeError', 'ValueError', 'bool', 'int', 'list', 'bytes', 'bytearray', 'sum', 'ord', 'super'), link_helper_expected_builtins, strict=True):
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str or (link_seal_helper_pair[0] != link_seal_helper_name) or (link_seal_helper_pair[1] is not link_seal_helper_expected) or (link_seal_helper_builtin_namespace.get(link_seal_helper_name) is not link_seal_helper_expected):
                        raise refusal from None
                for link_seal_helper_row, link_seal_helper_name in link_raw_zip(link_helper_origin[3], ('capture', 'current', 'capture_bound', 'current_live'), strict=True):
                    if link_raw_type(link_seal_helper_row) is not link_raw_tuple or link_raw_len(link_seal_helper_row) != 7 or link_raw_type(link_seal_helper_row[0]) is not link_raw_str or (link_seal_helper_row[0] != link_seal_helper_name) or (link_raw_type(link_seal_helper_row[1]) is not link_raw_function) or (link_seal_helper_row[3] is not link_seal_helper_namespace) or (link_seal_helper_namespace.get(link_seal_helper_name) is not link_seal_helper_row[1]) or (link_seal_helper_row[1].__code__ is not link_seal_helper_row[2]) or (link_seal_helper_row[1].__globals__ is not link_seal_helper_namespace) or (link_seal_helper_row[1].__builtins__ is not link_seal_helper_builtin_namespace) or (link_seal_helper_row[1].__defaults__ is not link_seal_helper_row[4]) or (link_seal_helper_row[1].__kwdefaults__ is not link_seal_helper_row[5]) or (link_seal_helper_row[1].__closure__ is not None) or (link_raw_type(link_seal_helper_row[6]) is not link_raw_tuple):
                        raise refusal from None
                    link_seal_helper_kw, link_seal_helper_kw_pairs = (link_seal_helper_row[5], link_seal_helper_row[6])
                    if link_seal_helper_kw is None:
                        if link_raw_len(link_seal_helper_kw_pairs) != 0:
                            raise refusal from None
                    else:
                        if link_raw_type(link_seal_helper_kw) is not link_raw_dict or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_kw)) or link_raw_len(link_seal_helper_kw) != link_raw_len(link_seal_helper_kw_pairs):
                            raise refusal from None
                        link_seal_helper_seen = {}
                        for link_seal_helper_pair in link_seal_helper_kw_pairs:
                            if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                                raise refusal from None
                            link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                            if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_kw or link_seal_helper_kw[link_seal_helper_key] is not link_seal_helper_value:
                                raise refusal from None
                            link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                link_seal_helper_error_kind, link_seal_helper_error_bases, link_seal_helper_error_pairs = link_helper_origin[4]
                if link_raw_type(link_seal_helper_error_kind) is not link_raw_type or link_seal_helper_namespace.get('RetainedBindingOriginError') is not link_seal_helper_error_kind or link_raw_type(link_seal_helper_error_bases) is not link_raw_tuple or (link_raw_len(link_seal_helper_error_bases) != 1) or (link_seal_helper_error_bases[0] is not link_helper_expected_builtins[10]) or (link_seal_helper_error_kind.__bases__ is not link_seal_helper_error_bases) or (link_raw_type(link_seal_helper_error_pairs) is not link_raw_tuple):
                    raise refusal from None
                link_seal_helper_error_names = link_raw_vars(link_seal_helper_error_kind)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_seal_helper_error_names)) or link_raw_len(link_seal_helper_error_names) != link_raw_len(link_seal_helper_error_pairs) or '__init__' in link_seal_helper_error_names or ('__new__' in link_seal_helper_error_names):
                    raise refusal from None
                link_seal_helper_seen = {}
                for link_seal_helper_pair in link_seal_helper_error_pairs:
                    if link_raw_type(link_seal_helper_pair) is not link_raw_tuple or link_raw_len(link_seal_helper_pair) != 2 or link_raw_type(link_seal_helper_pair[0]) is not link_raw_str:
                        raise refusal from None
                    link_seal_helper_key, link_seal_helper_value = link_seal_helper_pair
                    if link_seal_helper_key in link_seal_helper_seen or link_seal_helper_key not in link_seal_helper_error_names or link_seal_helper_error_names[link_seal_helper_key] is not link_seal_helper_value:
                        raise refusal from None
                    link_seal_helper_seen[link_seal_helper_key] = link_seal_helper_value
                link_hdata_packet = link_helper_origin[6]
                link_helper_all = link_helper_expected_builtins[8]
                link_helper_set = link_helper_expected_builtins[9]
                link_helper_runtime_error = link_helper_expected_builtins[10]
                link_helper_value_error = link_helper_expected_builtins[11]
                link_helper_modules = link_helper_origin[1]['_MODULES']
                link_helper_classes = link_helper_origin[1]['_CLASSES']
                link_helper_functions = link_helper_origin[1]['_FUNCTIONS']
                link_helper_live_globals = link_helper_origin[1]['_LIVE_GLOBALS']
                if link_raw_type(link_helper_layout) is not link_raw_tuple or link_raw_len(link_helper_layout) != 4 or link_helper_layout[0] is not link_hdata_packet:
                    raise refusal from None
                if (link_raw_type(link_hdata_packet) is link_raw_tuple and link_raw_len(link_hdata_packet) == 6) is not True:
                    raise refusal from None
                link_hdata_system, link_hdata_system_names, link_hdata_registry, link_hdata_modules, link_hdata_classes, link_hdata_functions = link_hdata_packet
                if (link_raw_type(link_hdata_system) is link_raw_module and link_raw_type(link_hdata_system_names) is link_raw_dict and (link_raw_vars(link_hdata_system) is link_hdata_system_names) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_system_names)) and (link_raw_type(link_hdata_registry) is link_raw_dict) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_registry)) and (link_hdata_system_names.get('modules') is link_hdata_registry) and (link_raw_type(link_hdata_modules) is link_raw_tuple) and (link_raw_len(link_hdata_modules) == link_raw_len(link_helper_modules)) and (link_raw_type(link_hdata_classes) is link_raw_tuple) and (link_raw_len(link_hdata_classes) == link_raw_len(link_helper_classes)) and (link_raw_type(link_hdata_functions) is link_raw_tuple) and (link_raw_len(link_hdata_functions) == link_raw_len(link_helper_functions))) is not True:
                    raise refusal from None
                link_hdata_builtin_module = link_hdata_registry.get('builtins')
                if link_raw_type(link_hdata_builtin_module) is not link_raw_module:
                    raise refusal from None
                link_hdata_builtin_namespace = link_raw_vars(link_hdata_builtin_module)
                if (link_raw_type(link_hdata_builtin_namespace) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_builtin_namespace))) is not True:
                    raise refusal from None
                for link_hdata_row, link_hdata_name, link_hdata_live_keys, link_hdata_column in link_raw_zip(link_hdata_modules, link_helper_modules, link_helper_live_globals, link_helper_layout[1], strict=True):
                    link_hdata_module, link_hdata_namespace, link_hdata_pairs = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_module) is link_raw_module and link_raw_type(link_hdata_namespace) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_registry)) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and (link_hdata_registry.get(link_hdata_name) is link_hdata_module) and (link_raw_vars(link_hdata_module) is link_hdata_namespace) and (link_raw_type(link_hdata_namespace.get('__name__')) is link_raw_str) and (link_hdata_namespace['__name__'] == link_hdata_name) and (link_hdata_namespace.get('__builtins__') is link_hdata_builtin_namespace or link_hdata_namespace.get('__builtins__') is link_hdata_builtin_module) and (link_raw_len(link_hdata_namespace) == link_raw_len(link_hdata_keys) + link_raw_len(link_hdata_live_keys))) is not True:
                        raise refusal from None
                    link_hdata_expected_pairs = link_raw_dict(link_raw_zip(link_hdata_keys, link_hdata_values, strict=True))
                    link_hdata_valid, link_hdata_observed, link_hdata_live_seen = (True, 0, 0)
                    try:
                        for link_hdata_key, link_hdata_value in link_hdata_namespace.items():
                            if link_raw_type(link_hdata_key) is not link_raw_str:
                                link_hdata_valid = False
                                break
                            link_hdata_observed += 1
                            if link_hdata_key in link_hdata_live_keys:
                                link_hdata_live_seen += 1
                            elif link_hdata_key not in link_hdata_expected_pairs or link_hdata_expected_pairs[link_hdata_key] is not link_hdata_value:
                                link_hdata_valid = False
                                break
                    except link_helper_runtime_error:
                        link_hdata_valid = False
                    if (link_hdata_valid is True and link_hdata_observed == link_raw_len(link_hdata_keys) + link_raw_len(link_hdata_live_keys) and (link_hdata_live_seen == link_raw_len(link_hdata_live_keys))) is not True:
                        raise refusal from None
                for link_hdata_row, (link_hdata_index, link_hdata_name), link_hdata_column in link_raw_zip(link_hdata_classes, link_helper_classes, link_helper_layout[2], strict=True):
                    link_hdata_kind, link_hdata_bases, link_hdata_pairs = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_kind) is link_raw_type and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[link_hdata_index][1])) and (link_hdata_modules[link_hdata_index][1].get(link_hdata_name) is link_hdata_kind) and (link_hdata_kind.__bases__ is link_hdata_bases)) is not True:
                        raise refusal from None
                    link_hdata_names = link_raw_vars(link_hdata_kind)
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_names)) and link_raw_len(link_hdata_names) == link_raw_len(link_hdata_keys)) is not True:
                        raise refusal from None
                    for link_hdata_key, link_hdata_value in link_raw_zip(link_hdata_keys, link_hdata_values, strict=True):
                        if (link_hdata_key in link_hdata_names and link_hdata_names[link_hdata_key] is link_hdata_value) is not True:
                            raise refusal from None
                for link_hdata_row, (link_hdata_index, link_hdata_owner, link_hdata_name), link_hdata_column in link_raw_zip(link_hdata_functions, link_helper_functions, link_helper_layout[3], strict=True):
                    link_hdata_function, link_hdata_code, link_hdata_namespace, link_hdata_defaults, link_hdata_kw, link_hdata_pairs, link_hdata_closure, link_hdata_cells = link_hdata_row
                    link_hdata__, link_hdata_keys, link_hdata_values = link_hdata_column
                    if (link_raw_type(link_hdata_namespace) is link_raw_dict and link_hdata_namespace is link_hdata_modules[link_hdata_index][1] and (link_raw_type(link_hdata_function) is link_raw_function) and (link_hdata_function.__globals__ is link_hdata_namespace) and (link_hdata_function.__builtins__ is link_hdata_builtin_namespace) and (link_hdata_function.__code__ is link_hdata_code) and (link_hdata_function.__defaults__ is link_hdata_defaults) and (link_hdata_function.__kwdefaults__ is link_hdata_kw) and (link_hdata_function.__closure__ is link_hdata_closure)) is not True:
                        raise refusal from None
                    link_hdata_names = link_hdata_namespace
                    if link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) is not True:
                        raise refusal from None
                    if link_hdata_owner is not None:
                        link_hdata_held_kind = None
                        for link_hdata_class_row, (link_hdata_class_index, link_hdata_class_name) in link_raw_zip(link_hdata_classes, link_helper_classes, strict=True):
                            if link_hdata_class_index == link_hdata_index and link_hdata_class_name == link_hdata_owner:
                                link_hdata_held_kind = link_hdata_class_row[0]
                                break
                        if (link_raw_type(link_hdata_held_kind) is link_raw_type and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and (link_hdata_namespace.get(link_hdata_owner) is link_hdata_held_kind)) is not True:
                            raise refusal from None
                        link_hdata_names = link_raw_vars(link_hdata_held_kind)
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_names)) and link_hdata_names.get(link_hdata_name) is link_hdata_function) is not True:
                        raise refusal from None
                    if link_hdata_kw is not None:
                        if (link_raw_type(link_hdata_kw) is link_raw_dict and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_kw)) and (link_raw_len(link_hdata_kw) == link_raw_len(link_hdata_keys))) is not True:
                            raise refusal from None
                        for link_hdata_key, link_hdata_value in link_raw_zip(link_hdata_keys, link_hdata_values, strict=True):
                            if (link_hdata_key in link_hdata_kw and link_hdata_kw[link_hdata_key] is link_hdata_value) is not True:
                                raise refusal from None
                    if link_hdata_closure is not None:
                        if (link_raw_type(link_hdata_closure) is link_raw_tuple and link_raw_len(link_hdata_closure) == link_raw_len(link_hdata_cells)) is not True:
                            raise refusal from None
                        try:
                            if link_helper_all((link_raw_type(link_hdata_cell) is link_raw_cell and link_hdata_cell.cell_contents is link_hdata_value for link_hdata_cell, link_hdata_value in link_raw_zip(link_hdata_closure, link_hdata_cells, strict=True))) is not True:
                                raise refusal from None
                        except link_helper_value_error:
                            raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_hdata_modules[0][1].get('GatewayRecipeOwner') is link_hdata_classes[2][0] and (link_hdata_modules[0][1].get('_same_recipe_binding') is link_hdata_functions[4][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[1][1])) and (link_hdata_modules[0][1].get('StartupSelectionOwner') is link_hdata_classes[3][0]) and (link_hdata_modules[1][1].get('StartupSelectionOwner') is link_hdata_classes[3][0]) and (link_hdata_modules[0][1].get('GatewayStartupSelection') is link_hdata_classes[6][0]) and (link_hdata_modules[1][1].get('GatewayStartupSelection') is link_hdata_classes[6][0]) and (link_hdata_modules[0][1].get('IoScope') is link_hdata_classes[4][0]) and (link_hdata_modules[1][1].get('_Scope') is link_hdata_classes[4][0]) and (link_hdata_modules[1][1].get('_approved_recipe') is link_hdata_functions[6][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[0][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[1][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[2][1])) and link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[3][1])) and (link_hdata_modules[0][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[1][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[2][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[2][1].get('_LATE_MODULES') is link_hdata_modules[3][1].get('_LATE_MODULES'))) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[4][1])) and link_hdata_modules[4][1].get('_Scope') is link_hdata_classes[4][0] and (link_hdata_modules[4][1].get('GatewayActivationOwner') is link_hdata_classes[10][0])) is not True:
                    raise refusal from None
                for link_hdata_index in (0, 1, 2):
                    link_hdata_namespace = link_hdata_modules[link_hdata_index][1]
                    if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_namespace)) and link_hdata_namespace.get('ExpectedArtifact') is link_hdata_classes[13][0] and (link_hdata_namespace.get('_descriptor_closed_in_scope') is link_hdata_functions[15][0]) and (link_hdata_namespace.get('_expected') is link_hdata_functions[19][0])) is not True:
                        raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[5][1])) and link_hdata_modules[2][1].get('_APPROVAL_OWNER_TYPE') is link_hdata_classes[23][0] and (link_hdata_modules[5][1].get('GatewayActivationOwner') is link_hdata_classes[10][0]) and (link_hdata_modules[5][1].get('_LATE_MODULES') is link_hdata_modules[3][1].get('_LATE_MODULES')) and (link_hdata_modules[5][1].get('ExpectedArtifact') is link_hdata_classes[13][0]) and (link_hdata_modules[5][1].get('_Scope') is link_hdata_classes[4][0]) and (link_hdata_modules[5][1].get('_descriptor_closed_in_scope') is link_hdata_functions[15][0]) and (link_hdata_modules[5][1].get('OperatorApprovalPath') is link_hdata_classes[38][0]) and (link_hdata_modules[5][1].get('_OperatorFileReceipt') is link_hdata_classes[39][0]) and (link_hdata_modules[5][1].get('_ReadEffect') is link_hdata_classes[40][0])) is not True:
                    raise refusal from None
                if (link_helper_all((link_raw_type(link_hdata_key) is link_raw_str for link_hdata_key in link_hdata_modules[6][1])) and link_hdata_modules[5][1].get('GatewayEntryOwner') is link_hdata_classes[27][0] and (link_hdata_modules[6][1].get('GatewayActivationOwner') is link_hdata_classes[10][0])) is not True:
                    raise refusal from None
                for (
                    link_runtime_consumer,
                    link_runtime_alias,
                    link_runtime_definition,
                    link_runtime_name,
                ) in (
                    (7, "_artifacts", 4, None),
                    (7, "_PRIVATE", 0, "_PRIVATE"),
                    (7, "_table_rows", 0, "_table_rows"),
                    (7, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (7, "_expected", 4, "_expected"),
                    (7, "_HashedArtifact", 4, "_HashedArtifact"),
                    (8, "GatewayActivationOwner", 3, "GatewayActivationOwner"),
                    (8, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
                    (8, "_same_origins", 0, "_same_origins"),
                    (8, "_Scan", 0, "_Scan"),
                    (8, "_table_rows", 0, "_table_rows"),
                    (8, "_Tree", 0, "_Tree"),
                    (8, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
                    (8, "_same_recipe_binding", 1, "_same_recipe_binding"),
                    (8, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (8, "StartupArtifactOwner", 4, "StartupArtifactOwner"),
                    (8, "_capture_native_scope", 4, "_capture_native_scope"),
                    (8, "_descriptor_closed_in_scope", 4, "_descriptor_closed_in_scope"),
                    (8, "_descriptor_refused", 4, "_descriptor_refused"),
                    (8, "_expected", 4, "_expected"),
                    (8, "_HashedArtifact", 4, "_HashedArtifact"),
                    (8, "_identity", 4, "_identity"),
                    (8, "_native_registration_tail", 4, "_native_registration_tail"),
                    (8, "_native_walk_scope", 4, "_native_walk_scope"),
                    (8, "_Scope", 4, "_Scope"),
                    (8, "gateway_entry", 6, None),
                    (8, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
                    (9, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
                    (9, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
                    (9, "_same_recipe_binding", 1, "_same_recipe_binding"),
                    (9, "ExpectedArtifact", 4, "ExpectedArtifact"),
                    (9, "RuntimeFilePlan", 7, "RuntimeFilePlan"),
                    (9, "RuntimePackage", 7, "RuntimePackage"),
                    (9, "plan_current", 7, "plan_current"),
                    (9, "EntryFileSnapshotOwner", 8, "EntryFileSnapshotOwner"),
                    (9, "_Inputs", 8, "_Inputs"),
                    (9, "_same_package", 8, "_same_package"),
                    (9, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
                    (9, "_origin_current", 6, "_origin_current"),
                ):
                    link_runtime_consumer_names = link_hdata_modules[link_runtime_consumer][1]
                    link_runtime_definition_names = link_hdata_modules[link_runtime_definition][1]
                    if not link_helper_all(
                        link_raw_type(link_runtime_key) is link_raw_str
                        for link_runtime_key in link_runtime_consumer_names
                    ) or not link_helper_all(
                        link_raw_type(link_runtime_key) is link_raw_str
                        for link_runtime_key in link_runtime_definition_names
                    ):
                        raise refusal from None
                    link_runtime_expected = (
                        link_hdata_modules[link_runtime_definition][0]
                        if link_runtime_name is None
                        else link_runtime_definition_names.get(link_runtime_name)
                    )
                    if (
                        (
                            link_runtime_name is not None
                            and link_runtime_name not in link_runtime_definition_names
                        )
                        or link_runtime_alias not in link_runtime_consumer_names
                        or link_runtime_consumer_names[link_runtime_alias]
                        is not link_runtime_expected
                    ):
                        raise refusal from None

                link_pin_encoding_origin = link_pin_environment[3]
                if link_raw_type(link_pin_encoding_origin) is not link_pin_types[9][0] or link_raw_tuple.__len__(link_pin_encoding_origin) != 7:
                    raise refusal from None
                link_pin_encoded_module, link_pin_encoded_namespace, link_pin_get_encoding, link_pin_get_errors, link_pin_encode, link_pin_encoding, link_pin_errors = link_pin_encoding_origin
                if link_pin_encoded_module is not link_pin_environment[0] or link_pin_encoded_namespace is not link_pin_environment[1] or link_raw_type(link_pin_get_encoding) is not link_raw_builtin or (link_raw_type(link_pin_get_errors) is not link_raw_builtin) or (link_pin_get_encoding.__self__ is not link_pin_encoded_module) or (link_pin_get_errors.__self__ is not link_pin_encoded_module) or (link_pin_get_encoding.__name__ != 'getfilesystemencoding') or (link_pin_get_errors.__name__ != 'getfilesystemencodeerrors') or (link_pin_encoded_namespace.get('getfilesystemencoding') is not link_pin_get_encoding) or (link_pin_encoded_namespace.get('getfilesystemencodeerrors') is not link_pin_get_errors) or (link_raw_type(link_pin_encode) is not link_raw_descriptor) or (link_pin_encode.__objclass__ is not link_raw_str) or (link_pin_encode.__name__ != 'encode') or (link_raw_vars(link_raw_str).get('encode') is not link_pin_encode) or (link_raw_type(link_pin_encoding) is not link_raw_str) or (link_raw_type(link_pin_errors) is not link_raw_str) or (not 1 <= link_raw_len(link_pin_encoding) <= 64) or (not 1 <= link_raw_len(link_pin_errors) <= 64) or link_raw_any((not (link_pin_c.isascii() and (link_pin_c.isalnum() or link_pin_c in '._-')) for link_pin_c in link_pin_encoding + link_pin_errors)):
                    raise refusal from None
                if (link_raw_type(link_engine_origin) is not link_raw_tuple
                        or link_raw_len(link_engine_origin) != 6
                        or link_pin_environment[4] is not link_engine_origin
                        or link_pin_environment[5] is not link_engine_origin[5]
                        or link_pin_environment[7] is not link_audit_record
                        or link_audit_record[0] is not link_engine_origin
                        or link_audit_record[1] is not link_engine_origin[5]):
                    raise refusal from None
                link_engine_dependencies = link_engine_origin[4]
                if (link_raw_type(link_engine_dependencies) is not link_raw_tuple
                        or link_raw_len(link_engine_dependencies) != 4
                        or link_engine_dependencies[0] is not link_pin_environment[0]
                        or link_engine_dependencies[1] is not link_pin_environment[1]
                        or link_engine_dependencies[2] is not link_pin_environment[2]):
                    raise refusal from None
                if link_raw_type(link_engine_dependencies) is not link_raw_tuple or link_raw_len(link_engine_dependencies) != 4 or link_raw_type(link_engine_dependencies[0]) is not link_raw_module or (link_raw_type(link_engine_dependencies[1]) is not link_raw_dict) or (link_raw_vars(link_engine_dependencies[0]) is not link_engine_dependencies[1]) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_dependencies[1])) or (link_raw_type(link_engine_dependencies[2]) is not link_raw_dict) or (link_engine_dependencies[1].get('modules') is not link_engine_dependencies[2]) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_dependencies[2])) or (link_raw_type(link_engine_dependencies[3]) is not link_raw_tuple) or (link_raw_len(link_engine_dependencies[3]) != 5):
                    raise refusal from None
                layout = link_engine_origin[5]
                if (link_raw_type(layout) is not link_raw_tuple or link_raw_len(layout) != 2
                        or layout[0] is not link_engine_dependencies or link_raw_type(layout[1]) is not link_raw_tuple
                        or link_raw_len(layout[1]) != link_raw_len(link_engine_dependencies[3])):
                    raise refusal from None
                for layout_row, layout_module in link_raw_zip(layout[1], link_engine_dependencies[3], strict=True):
                    if (link_raw_type(layout_row) is not link_raw_tuple or link_raw_len(layout_row) != 2
                            or layout_row[0] is not layout_module
                            or link_raw_type(layout_module) is not link_raw_tuple or link_raw_len(layout_module) != 6
                            or link_raw_type(layout_module[4]) is not link_raw_tuple
                            or link_raw_type(layout_row[1]) is not link_raw_tuple
                            or link_raw_len(layout_row[1]) != link_raw_len(layout_module[4])):
                        raise refusal from None
                    for layout_class_row, layout_class in link_raw_zip(layout_row[1], layout_module[4], strict=True):
                        if (link_raw_type(layout_class_row) is not link_raw_tuple or link_raw_len(layout_class_row) != 3
                                or layout_class_row[0] is not layout_class
                                or link_raw_type(layout_class) is not link_raw_tuple or link_raw_len(layout_class) != 3
                                or link_raw_type(layout_class[2]) is not link_raw_tuple
                                or link_raw_type(layout_class_row[1]) is not link_raw_tuple
                                or link_raw_type(layout_class_row[2]) is not link_raw_tuple
                                or link_raw_len(layout_class_row[1]) != link_raw_len(layout_class[2])
                                or link_raw_len(layout_class_row[2]) != link_raw_len(layout_class[2])):
                            raise refusal from None
                        layout_seen = {}
                        for layout_pair, layout_key, layout_value in link_raw_zip(
                                layout_class[2], layout_class_row[1], layout_class_row[2], strict=True):
                            if (link_raw_type(layout_pair) is not link_raw_tuple or link_raw_len(layout_pair) != 2
                                    or link_raw_type(layout_key) is not link_raw_str
                                    or layout_pair[0] is not layout_key
                                    or layout_pair[1] is not layout_value
                                    or layout_key in layout_seen):
                                raise refusal from None
                            layout_seen[layout_key] = layout_value
                link_engine_checked_namespaces = []
                link_engine_expected_modules = ('hmp_plugin.presentation_native_link', 'hmp_plugin.presentation_native_metadata', 'hmp_plugin.presentation_startup_artifacts', 'hmp_plugin.presentation_metadata_custody', 'hmp_plugin.presentation_link_path_policy')
                for link_engine_row, link_engine_expected_name in link_raw_zip(link_engine_dependencies[3], link_engine_expected_modules, strict=True):
                    if link_raw_type(link_engine_row) is not link_raw_tuple or link_raw_len(link_engine_row) != 6 or link_raw_type(link_engine_row[0]) is not link_raw_str or (link_engine_row[0] != link_engine_expected_name) or (link_raw_type(link_engine_row[1]) is not link_raw_module) or (link_raw_type(link_engine_row[2]) is not link_raw_dict) or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_row[2])) or (link_engine_dependencies[2].get(link_engine_expected_name) is not link_engine_row[1]) or (link_raw_vars(link_engine_row[1]) is not link_engine_row[2]) or (link_raw_type(link_engine_row[3]) is not link_raw_tuple) or (link_raw_len(link_engine_row[2]) != link_raw_len(link_engine_row[3])) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_row[2]) or (link_engine_row[2][link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_row[3])) or (link_raw_type(link_engine_row[4]) is not link_raw_tuple) or (link_raw_type(link_engine_row[5]) is not link_raw_tuple):
                        raise refusal from None
                    link_engine_checked_namespaces.append(link_engine_row[2])
                    for link_engine_class_row in link_engine_row[4]:
                        if link_raw_type(link_engine_class_row) is not link_raw_tuple or link_raw_len(link_engine_class_row) != 3:
                            raise refusal from None
                        link_engine_kind, link_engine_bases, link_engine_members = link_engine_class_row
                        if link_raw_type(link_engine_kind) is not link_raw_type or link_engine_kind.__bases__ is not link_engine_bases:
                            raise refusal from None
                        link_engine_names = link_raw_vars(link_engine_kind)
                        if link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_names)) or link_raw_type(link_engine_members) is not link_raw_tuple or link_raw_len(link_engine_names) != link_raw_len(link_engine_members) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_names) or (link_engine_names[link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_members)):
                            raise refusal from None
                    for link_engine_function_row in link_engine_row[5]:
                        if link_raw_type(link_engine_function_row) is not link_raw_tuple or link_raw_len(link_engine_function_row) != 8:
                            raise refusal from None
                        link_engine_function, link_engine_code, link_engine_namespace, link_engine_defaults, link_engine_kw, link_engine_pairs, link_engine_closure, link_engine_cells = link_engine_function_row
                        if link_raw_type(link_engine_function) is not link_raw_function or link_engine_function.__code__ is not link_engine_code or link_engine_function.__globals__ is not link_engine_namespace or (link_raw_type(link_engine_namespace) is not link_raw_dict) or (link_engine_function.__defaults__ is not link_engine_defaults) or (link_engine_function.__kwdefaults__ is not link_engine_kw) or (link_raw_type(link_engine_pairs) is not link_raw_tuple) or (link_engine_function.__closure__ is not link_engine_closure) or (link_raw_type(link_engine_cells) is not link_raw_tuple):
                            raise refusal from None
                        if not link_raw_any((link_engine_namespace is link_engine_prior for link_engine_prior in link_engine_checked_namespaces)):
                            if link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_namespace)):
                                raise refusal from None
                            link_engine_checked_namespaces.append(link_engine_namespace)
                        if link_engine_kw is None:
                            if link_raw_len(link_engine_pairs) != 0:
                                raise refusal from None
                        elif link_raw_type(link_engine_kw) is not link_raw_dict or link_raw_any((link_raw_type(link_engine_k) is not link_raw_str for link_engine_k in link_engine_kw)) or link_raw_len(link_engine_kw) != link_raw_len(link_engine_pairs) or link_raw_any((link_raw_type(link_engine_pair) is not link_raw_tuple or link_raw_len(link_engine_pair) != 2 or link_raw_type(link_engine_pair[0]) is not link_raw_str or (link_engine_pair[0] not in link_engine_kw) or (link_engine_kw[link_engine_pair[0]] is not link_engine_pair[1]) for link_engine_pair in link_engine_pairs)):
                            raise refusal from None
                        if link_engine_closure is None:
                            if link_raw_len(link_engine_cells) != 0:
                                raise refusal from None
                        elif link_raw_type(link_engine_closure) is not link_raw_tuple or link_raw_len(link_engine_closure) != link_raw_len(link_engine_cells) or link_raw_any((link_raw_type(link_engine_cell) is not link_raw_cell or link_engine_cell.cell_contents is not link_engine_value for link_engine_cell, link_engine_value in link_raw_zip(link_engine_closure, link_engine_cells, strict=True))):
                            raise refusal from None
                link_primitive_audit_rows = link_raw_tuple((row for row in link_engine_origin[2] if link_raw_type(row) is link_raw_tuple and link_raw_len(row) == 7 and (link_raw_type(row[0]) is link_raw_str) and (row[0] == '_engine_origin_tail')))
                if (link_raw_len(link_primitive_audit_rows) != 1
                        or link_primitive_audit_rows[0] is not link_audit_record[2]):
                    raise refusal from None
                link_primitive_audit_checker, link_primitive_audit_kw = (link_primitive_audit_rows[0][1], link_primitive_audit_rows[0][5])
                if link_raw_type(link_primitive_audit_checker) is not link_raw_function or link_raw_type(link_primitive_audit_kw) is not link_raw_dict or link_primitive_audit_checker.__kwdefaults__ is not link_primitive_audit_kw or link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_kw)):
                    raise refusal from None
                link_primitive_audit_pairs = link_primitive_audit_rows[0][6]
                if (link_raw_type(link_primitive_audit_pairs) is not link_raw_tuple
                        or link_raw_len(link_primitive_audit_kw) != link_raw_len(link_primitive_audit_pairs)):
                    raise refusal from None
                link_primitive_audit_originals = {}
                for link_primitive_audit_pair in link_primitive_audit_pairs:
                    if (link_raw_type(link_primitive_audit_pair) is not link_raw_tuple
                            or link_raw_len(link_primitive_audit_pair) != 2
                            or link_raw_type(link_primitive_audit_pair[0]) is not link_raw_str):
                        raise refusal from None
                    link_primitive_audit_name, link_primitive_audit_expected = link_primitive_audit_pair
                    if (link_primitive_audit_name in link_primitive_audit_originals
                            or link_primitive_audit_name not in link_primitive_audit_kw
                            or link_primitive_audit_kw[link_primitive_audit_name] is not link_primitive_audit_expected):
                        raise refusal from None
                    link_primitive_audit_originals[link_primitive_audit_name] = link_primitive_audit_expected
                link_primitive_audit_id = link_primitive_audit_originals.get('_id')
                link_primitive_audit_map = link_primitive_audit_originals.get('_map')
                link_primitive_audit_not = link_primitive_audit_originals.get('_not_identity')
                if link_raw_type(link_primitive_audit_id) is not link_raw_builtin or link_primitive_audit_id.__name__ != 'id' or link_raw_type(link_primitive_audit_id.__self__) is not link_raw_module or (link_engine_dependencies[2].get('builtins') is not link_primitive_audit_id.__self__):
                    raise refusal from None
                link_primitive_audit_builtins = link_raw_vars(link_primitive_audit_id.__self__)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_builtins)) or link_primitive_audit_checker.__builtins__ is not link_primitive_audit_builtins:
                    raise refusal from None
                for link_primitive_audit_name, link_primitive_audit_value in (('type', link_raw_type), ('tuple', link_raw_tuple), ('dict', link_raw_dict), ('str', link_raw_str), ('len', link_raw_len), ('vars', link_raw_vars), ('any', link_raw_any), ('zip', link_raw_zip), ('id', link_primitive_audit_id), ('map', link_primitive_audit_map)):
                    if link_primitive_audit_builtins.get(link_primitive_audit_name) is not link_primitive_audit_value or link_primitive_audit_originals.get('_' + link_primitive_audit_name) is not link_primitive_audit_value:
                        raise refusal from None
                if link_raw_type(link_primitive_audit_map) is not link_raw_type:
                    raise refusal from None
                link_primitive_audit_map_names = link_raw_vars(link_primitive_audit_map)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_map_names)):
                    raise refusal from None
                link_primitive_audit_new = link_primitive_audit_map_names.get('__new__')
                if link_raw_type(link_primitive_audit_new) is not link_raw_builtin or link_primitive_audit_new.__self__ is not link_primitive_audit_map or link_primitive_audit_new.__name__ != '__new__' or (link_primitive_audit_map.__name__ != 'map') or (link_primitive_audit_map.__module__ != 'builtins') or (link_raw_type(link_primitive_audit_not) is not link_raw_builtin) or (link_primitive_audit_not.__name__ != 'is_not') or (link_raw_type(link_primitive_audit_not.__self__) is not link_raw_module) or (link_engine_dependencies[2].get('_operator') is not link_primitive_audit_not.__self__):
                    raise refusal from None
                link_primitive_audit_operator = link_raw_vars(link_primitive_audit_not.__self__)
                if link_raw_any((link_raw_type(k) is not link_raw_str for k in link_primitive_audit_operator)) or link_primitive_audit_operator.get('is_not') is not link_primitive_audit_not:
                    raise refusal from None
                if (owner_namespace.get('StartupArtifactOwner') is not owner_kind
                        or type(owner) is not owner_kind or _Scope is not kind or type(s) is not kind
                        or tuple.__getitem__(s, 17) is not link_blueprint
                        or owner_dict.get('_scope') is not s or owner_dict.get('_origin') is not s
                        or owner_dict.get('_cell') is not scope_cell
                        or owner_dict.get('_root_cell') is not scope_root
                        or vars(activation).get('_artifact_cell') is not scope_root
                        or vars(activation).get('_artifact_owner') is not owner
                        or constructor.__code__ is not constructor_code
                        or any(vars(kind).get(name) is not member
                               for name, member in zip(fields, members, strict=True))
                        or any(vars(kind).get(name) is not member
                               for name, member in zip(dispatch_names, dispatch, strict=True))):
                    raise refusal from None
                for selected, entries, functions in link_cohort[2]:
                    names = vars(selected)
                    if (any(type(k) is not str for k in names) or len(names) != len(entries)
                            or any(k not in names or names[k] is not value for k, value in entries)):
                        raise refusal from None
                    for function, code, defaults, kw, pairs in functions:
                        if (function.__code__ is not code or function.__defaults__ is not defaults
                                or function.__kwdefaults__ is not kw
                                or (kw is not None and (any(type(k) is not str for k in kw)
                                    or len(kw) != len(pairs)
                                    or any(k not in kw or kw[k] is not value for k, value in pairs)))):
                            raise refusal from None
            register_scope(owner, s, scope_cell, scope_root)
            if (owner._origin is s and owner._scope is s
                     and owner._cell is scope_cell and owner._root_cell is scope_root
                     and activation._artifact_cell is scope_root) is not True:
                raise refusal from None
            return owner
        except BaseException:
            # No late owner setter/getter dispatch. Mark only the independently
            # held dictionary while it is still this actual owner's dictionary;
            # never overwrite a replacement/foreign slot to hide custody drift.
            try:
                if failure_owner_dictionary(owner, cls) is failure_owner_values:
                    failure_owner_values['_failed'] = True
            except BaseException:
                pass
        # Raise outside our handler so the rejected exception is not retained as
        # context. Discard earlier guard tracebacks using held native descriptors,
        # never a possibly changed error property or subclass __setattr__.
        refusal_traceback(refusal, None)
        refusal_context(refusal, None)
        refusal_cause(refusal, None)
        raise refusal from None

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
                if _has_native_link_engine(native_registration):
                    make_fact = _native_link_function(owner, native_registration, '_make_fact')
                    link_fact = make_fact(owner, native_registration, runtime, before, after,
                                          targets[0], owner._count_cell)
                else:
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

    def _open(self, name, parent, directory, native_registration=None, prepared=None):
        _require(prepared is None or
                 (type(self) is StartupArtifactOwner and native_registration is not None
                  and type(prepared) is _NativeOpenAllocation))
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
        if prepared is None:
            row = _Descriptor()
            s.records.append(row)  # original descriptor allocation before open
            row.attempted = True
        else:
            _require(prepared.owner is self and prepared.registration is native_registration
                     and prepared.scope is s and prepared.native is native
                     and type(prepared.pending) is _Descriptor
                     and s.records[-1] is prepared.pending
                     and prepared.raw[0] is None and prepared.result[0] is None
                     and prepared.refused[0] is False)
            row = prepared.pending
        fd = None
        allocation = prepared
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
                if prepared is None:
                    allocation = _allocate_native_file_open(
                        self, native_registration, parent, (name, flags, parent), row)
                else:
                    _require(allocation is prepared and type(directory) is bool and directory
                             and prepared.arguments[0] is name
                             and prepared.arguments[1] == flags
                             and prepared.arguments[2] is parent
                             and prepared.raw[0] is None and prepared.result[0] is None)
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
                         and allocation.ledger.inflight[0] is None
                         and (prepared is None or allocation is prepared))
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
                         and row.close.raw[0] is row.close.unset and row.close.result[0] is None
                         and (prepared is None or allocation is prepared))
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
            return _close_native_file_known(self, row.allocation, fd, registration.native_ledger)
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
        _require(not _has_native_link_engine(native_registration))
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
        _require(not _has_native_link_engine(native_registration))
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
        if _has_native_link_engine(native_registration):
            snapshot_call = _native_link_function(self, native_registration, '_snapshot')
            snapshot = snapshot_call(self, native_registration, phase, before_state)
            _link_reads_current(s.runtime, snapshot)
            _require(_native_walk_scope(self, native_registration) is s
                     and s.runtime.count[0] is self._count_cell is snapshot.count)
            _link_reads_current(s.runtime, snapshot)
            return snapshot
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
        if _has_native_link_engine(native_registration):
            recheck = _native_link_function(self, native_registration, '_recheck')
            actual = recheck(self, native_registration, fact)
            _require(vars(self).get('_native_link_recheck') is actual
                     and actual.owner is self and actual.registration is native_registration
                     and actual.fact is fact and actual.count is fact.count
                     and self._fact_cell is held_fact)
            _require(StartupArtifactOwner.seal_link_observation(self, held_fact) is fact)
            return fact
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
        metadata = None
        metadata_last = metadata_before = metadata_eof = None
        directory_baselines = []
        if native_registration is not None and (runtime_source or declared_reader is not None):
            from . import presentation_native_metadata as metadata
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
                if metadata is None:
                    info = StartupArtifactOwner._fstat(self, fd, s, native_registration)
                    signature = _identity(info, True)
                    mode = stat.S_IMODE(info.st_mode)
                    _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, s.context[1])
                             and not mode & (stat.S_ISUID | stat.S_ISGID)
                             and (not mode & 0o022 or (info.st_uid == 0 and bool(mode & stat.S_ISVTX))))
                else:
                    metadata_resource = _prepare_native_metadata_resource(
                        self, native_registration, native_walk, row)
                    metadata_last = metadata._run_directory_observation(
                        self, metadata_resource, metadata_last)
                    _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                             and metadata_last.resource is metadata_resource)
                    directory_baselines.append(metadata_last)
                    signature = metadata_last.identity
                directories.append((name, parent, fd, signature))
                parent = fd
            if _configuration(self):
                _require(info.st_uid == s.context[1] and stat.S_IMODE(info.st_mode) == 0o700)
            name = expected.path.rsplit("/", 1)[1]
            if metadata is None:
                before = StartupArtifactOwner._stat(self, name, parent, s, native_registration)
                original = _identity(before)
                _require(stat.S_ISREG(before.st_mode) and before.st_uid in (0, s.context[1])
                         and before.st_nlink == 1
                         and (0 < before.st_size <= 4096 if anchor else before.st_size == expected.size)
                         and not before.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
            else:
                metadata_resource = _prepare_native_metadata_resource(
                    self, native_registration, native_walk, held[-1][0], name)
                metadata_before = metadata._run_directory_observation(
                    self, metadata_resource, metadata_last)
                _require(type(metadata_before) is metadata._DirectoryPolicyCommit
                         and metadata_before.resource is metadata_resource)
                metadata_last = metadata_before
                original = metadata_before.identity
            if _configuration(self):
                _require(before.st_uid == s.context[1] and stat.S_IMODE(before.st_mode) == 0o600)
            if source_effect is not None:
                timestamp = before.st_mtime if metadata is None else metadata_before.mtime
                _require(type(timestamp) in (int, float) and -2 ** 64 < timestamp < 2 ** 64)
                source_mtime = int(timestamp)  # exact CPython path_stats conversion, not ns floor
            row, fd = StartupArtifactOwner._open(self, name, parent, False, native_registration)
            held.append((row, fd))
            if metadata is None:
                _require(_identity(StartupArtifactOwner._fstat(
                    self, fd, s, native_registration)) == original)
            else:
                metadata_resource = _prepare_native_metadata_resource(
                    self, native_registration, native_walk, row)
                metadata_last = metadata._run_directory_observation(
                    self, metadata_resource, metadata_last)
                _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                         and metadata_last.resource is metadata_resource
                         and metadata_last.identity == original)
            digest = hashlib.sha256()
            header = b""
            capture_header = (not anchor and not _configuration(self)
                              and expected.path.endswith(".pyc"))
            remaining = before.st_size if anchor else expected.size
            if (runtime_source or declared_reader is not None) and native_registration is not None:
                _require(type(native_walk) is tuple and len(native_walk) == 6)
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
                metadata_eof = native_commit
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
            _require(data == b"")
            if metadata is None:
                _require(_identity(StartupArtifactOwner._fstat(
                    self, fd, s, native_registration)) == original
                         and _identity(StartupArtifactOwner._stat(
                             self, name, parent, s, native_registration)) == original)
            else:
                metadata_resource = _prepare_native_metadata_resource(
                    self, native_registration, native_walk, row)
                metadata_last = metadata._run_directory_observation(
                    self, metadata_resource, metadata_last, metadata_before, metadata_eof)
                _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                         and metadata_last.resource is metadata_resource
                         and metadata_last.identity == original)
                metadata_resource = _prepare_native_metadata_resource(
                    self, native_registration, native_walk, held[-2][0], name)
                metadata_last = metadata._run_directory_observation(
                    self, metadata_resource, metadata_last, metadata_before, metadata_eof)
                _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                         and metadata_last.resource is metadata_resource
                         and metadata_last.identity == original)
            _require(_native_walk_scope(self, native_registration) is s)
            actual_hash = digest.hexdigest()
            _require(_native_walk_scope(self, native_registration) is s
                     and type(actual_hash) is str
                     and (anchor or actual_hash == expected.sha256))
            if source_effect is not None:
                source_hash = source_digest.finish(source_root, source_buffer, count_cell,
                                                   source_observations)
            for component, (name, parent, directory, signature) in enumerate(directories):
                if metadata is None:
                    _require(
                        _identity(StartupArtifactOwner._fstat(
                            self, directory, s, native_registration), True) == signature
                        and _identity(StartupArtifactOwner._stat(
                            self, name, parent, s, native_registration), True) == signature)
                else:
                    baseline = directory_baselines[component]
                    metadata_resource = _prepare_native_metadata_resource(
                        self, native_registration, native_walk, held[component][0])
                    metadata_last = metadata._run_directory_observation(
                        self, metadata_resource, metadata_last, baseline, metadata_eof)
                    _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                             and metadata_last.resource is metadata_resource
                             and metadata_last.identity == signature)
                    metadata_resource = _prepare_native_metadata_resource(
                        self, native_registration, native_walk,
                        None if component == 0 else held[component - 1][0], name)
                    metadata_last = metadata._run_directory_observation(
                        self, metadata_resource, metadata_last, baseline, metadata_eof)
                    _require(type(metadata_last) is metadata._DirectoryPolicyCommit
                             and metadata_last.resource is metadata_resource
                             and metadata_last.identity == signature)
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
            if metadata is None:
                _finish_native_declared_walk(self, native_registration, native_walk)
            else:
                _finish_native_declared_walk(self, native_registration, native_walk, metadata_last)
        return result
