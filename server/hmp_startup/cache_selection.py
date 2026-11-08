"""CPython source-loader input-attempt semantics; never code/runtime admission."""
from __future__ import annotations

from typing import NamedTuple


class CacheSelectionError(Exception):
    def __init__(self):
        super().__init__('BI1_CACHE_SELECTION_REFUSED')


def _require(value):
    if value is not True:
        raise CacheSelectionError


class CacheInputAttempt(NamedTuple):
    input: str
    validation: str
    flags: int | None

    def __repr__(self):
        return '<SourceLoaderInputAttempt DATA not-admission>'


def source_loader_input(header, magic, mtime, size, source_hash, mode, cache_state):
    """Model a known input observation, not a later read or successful import."""
    _require(type(magic) is bytes and len(magic) == 4
             and type(source_hash) is bytes and len(source_hash) == 8
             and type(mode) is str and mode in ('default', 'always', 'never')
             and type(cache_state) is str
             and cache_state in ('absent', 'nonfile', 'unreadable', 'declared')
             and (header is None or (type(header) is bytes and len(header) <= 16)))
    _require((mtime is None and size is None)
             or (type(mtime) is int and -2 ** 64 < mtime < 2 ** 64
                 and type(size) is int and 0 <= size < 2 ** 64))
    if mtime is None:
        return CacheInputAttempt('source', 'source_stat_unavailable', None)
    if cache_state != 'declared':
        _require(header is None)
        return CacheInputAttempt('source', 'cache_' + cache_state, None)
    _require(type(header) is bytes)
    if len(header) < 16 or header[:4] != magic:
        return CacheInputAttempt('source', 'cache_header_invalid', None)
    flags = int.from_bytes(header[4:8], 'little')
    if flags & ~3:
        return CacheInputAttempt('source', 'cache_header_invalid', flags)
    if not flags & 1:  # includes flags2, as the actual SourceLoader does
        timestamp = int.from_bytes(header[8:12], 'little')
        stored_size = int.from_bytes(header[12:16], 'little')
        if timestamp != mtime & 0xffffffff or stored_size != size & 0xffffffff:
            return CacheInputAttempt('source', 'timestamp_mismatch', flags)
        return CacheInputAttempt('cache', 'timestamp', flags)
    checked = mode != 'never' and (bool(flags & 2) or mode == 'always')
    if checked and header[8:16] != source_hash:
        return CacheInputAttempt('source', 'hash_mismatch', flags)
    return CacheInputAttempt('cache', 'hash_checked' if checked else 'hash_unchecked', flags)


class BoundCacheInputAttempt(NamedTuple):
    source: object
    plan_row: object
    cache: object
    proof: tuple
    header: bytes | None
    attempt: CacheInputAttempt

    def __repr__(self):
        return '<OriginalSnapshotCacheInputAttempt DATA not-admission>'


def _cache_proof(row, snapshot, cache_fact):
    from hmp_plugin.presentation_gateway_package import _Tree
    from hmp_plugin.presentation_startup_cache import (
        CacheObservationError,
        _CachePass,
        _Missing,
        _missing_shape,
    )

    from .cache_candidates import PlannedCachePath
    from .cache_context import CacheInputData
    from .runtime_files import RuntimePackage

    _require(type(row) is CacheInputData and type(row.state) is str
             and type(row.location) is PlannedCachePath and type(row.location.path) is str)
    if row.state == 'declared':
        _require(row.cache is not None)
        return ()
    _require(row.cache is None and type(row.location.path) is str)
    path = row.location.path
    if row.state in ('tree_expected_absent', 'tree_nonfile'):
        package = row.tree
        _require(type(package) is RuntimePackage and type(package.path) is str
                 and path.startswith(package.path + '/') and type(snapshot) is tuple)
        _require(all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
                     and type(pair[1]) is _Tree for pair in snapshot))
        matches = tuple(tree for root, tree in snapshot if root == package.path)
        _require(len(matches) == 1 and type(matches[0]) is _Tree)
        tree = matches[0]
        _require(type(tree.entries) is tuple and type(package.entries) is tuple
                 and all(type(item) is tuple and len(item) == 2
                         and type(item[0]) is str and type(item[1]) is str
                         for item in tree.entries + package.entries)
                 and tree.entries == package.entries)
        relative = path[len(package.path) + 1:]
        entries = tuple(item for item in tree.entries if item[0] == relative)
        if row.state == 'tree_nonfile':
            _require(len(entries) == 1 and entries[0][1] == 'directory')
            return tree, entries[0]
        _require(not entries)
        return tree, None
    _require(row.state == 'needs_owned_absence' and row.tree is None)
    _require(type(cache_fact) is tuple and len(cache_fact) == 6
             and type(cache_fact[3]) is _CachePass and type(cache_fact[4]) is _CachePass)
    before, after = cache_fact[3], cache_fact[4]
    _require(type(before.missing) is tuple and type(after.missing) is tuple
             and len(before.missing) == len(after.missing))
    try:
        for missing in before.missing + after.missing:
            _missing_shape(missing)
    except CacheObservationError:
        raise CacheSelectionError from None
    pairs = tuple((left, right) for left, right in zip(before.missing, after.missing, strict=True)
                  if type(left) is _Missing and type(right) is _Missing
                  and type(left.path) is str and type(right.path) is str
                  and left.path == path and right.path == path)
    _require(len(pairs) == 1 and type(pairs[0][0].index) is int and type(pairs[0][1].index) is int
             and pairs[0][0].index == pairs[0][1].index
             and pairs[0][0].ancestors == pairs[0][1].ancestors)
    return pairs[0]


def selected_cache_input_attempts(continuation):
    """Bind sampled original observations; do not claim a future loader read."""
    import sys
    from types import ModuleType

    from hmp_plugin.presentation_source_digest import seal_fact
    from hmp_plugin.presentation_startup_artifacts import (
        ExpectedArtifact,
        StartupArtifactOwner,
        _HashedArtifact,
    )

    from . import gateway_continuation as continuation_module
    from .bytecode_headers import selected_source_hashes
    from .cache_context import CacheContextOwner, CacheInputData
    from .gateway_continuation import GatewayContinuationOwner
    from .gateway_entry import _interpreter_current

    _require(type(continuation) is GatewayContinuationOwner
             and type(continuation_module) is ModuleType
             and sys.modules.get('hmp_startup.gateway_continuation') is continuation_module)
    namespace = vars(continuation_module)
    _require(namespace.get('GatewayContinuationOwner') is GatewayContinuationOwner)
    root = GatewayContinuationOwner.current_binding(continuation)
    original = root[2]
    context = original.cache_context_fact
    snapshot = original.snapshot_fact
    _require(type(context) is tuple and len(context) == 4
             and type(context[0]) is CacheContextOwner and type(context[3]) is tuple
             and CacheContextOwner.current_binding(context[0]) is context)
    io, cache_fact = snapshot[2], snapshot[7]
    _require(type(io) is StartupArtifactOwner
             and StartupArtifactOwner.seal_cache_observation(io) is cache_fact
             and cache_fact[2].context_fact is context)
    interpreter = original.entry_binding[0].interpreter
    magic, policy = interpreter.bytecode_magic, interpreter.cache_policy
    mode = policy.mode
    sources = selected_source_hashes(continuation)
    receipts = (*original.inputs.runtime_plan.prior, *snapshot[3][2])
    _require(all(type(item) is _HashedArtifact and type(item.expected) is ExpectedArtifact
                 for item in receipts))
    by_expected = {id(item.expected): item for item in receipts}
    _require(len(by_expected) == len(receipts) and len(sources) == len(context[3]))
    bound = []
    for row, source in zip(context[3], sources, strict=True):
        _require(type(row) is CacheInputData and row.source is source.receipt.expected)
        cache = None
        header = None
        if row.state == 'declared':
            cache = by_expected.get(id(row.cache))
            _require(type(cache) is _HashedArtifact and cache.expected is row.cache
                     and type(cache.bytecode_header) is bytes
                     and len(cache.bytecode_header) == min(16, row.cache.size))
            header = cache.bytecode_header
        proof = _cache_proof(row, snapshot[4], cache_fact)
        state = ('declared' if cache is not None else
                 'nonfile' if row.state == 'tree_nonfile' else 'absent')
        attempt = source_loader_input(header, magic, source.receipt.source_mtime,
                                      row.source.size, source.receipt.source_hash, mode, state)
        bound.append(BoundCacheInputAttempt(source, row, cache, proof, header, attempt))
    held = tuple(bound)
    _require(GatewayContinuationOwner.current_binding(continuation) is root
             and CacheContextOwner.current_binding(context[0]) is context
             and StartupArtifactOwner.seal_cache_observation(io) is cache_fact
             and original.cache_context_fact is context and original.snapshot_fact is snapshot
             and _interpreter_current(interpreter) is interpreter
             and interpreter.bytecode_magic is magic and interpreter.cache_policy is policy
             and policy.mode is mode)
    # No callbacks after this original cohort join: the parent's seal inspects
    # held metadata only, and must never receive a substituted foreign source.
    _require(namespace.get('_OWNER') is continuation and namespace.get('_ROOT') is root
             and sys.modules.get('hmp_startup.gateway_continuation') is continuation_module
             and namespace.get('GatewayContinuationOwner') is GatewayContinuationOwner
             and continuation._source is original and continuation._root is root
             and continuation._ready is True and continuation._failed is False
             and continuation._retired is False
             and original.entry_binding[2][3]._continuation_cell is root
             and GatewayContinuationOwner._seal(continuation) is original)
    for row, source, item in zip(context[3], sources, held, strict=True):
        _require(item.source is source and item.plan_row is row
                 and row.source is source.receipt.expected
                 and source.receipt.source_digest is source.fact
                 and source.fact.source_hash is source.receipt.source_hash
                 and source.fact.source_mtime is source.receipt.source_mtime
                 and seal_fact(source.fact) is source.fact)
        if item.cache is not None:
            _require(row.cache is item.cache.expected
                     and by_expected[id(row.cache)] is item.cache
                     and item.cache.bytecode_header is item.header)
        proof = _cache_proof(row, snapshot[4], cache_fact)
        _require(len(proof) == len(item.proof)
                 and all(a is b for a, b in zip(proof, item.proof, strict=True)))
    return held
