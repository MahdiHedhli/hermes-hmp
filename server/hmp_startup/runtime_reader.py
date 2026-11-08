"""One fresh bounded source read; not code loading or runtime admission."""
from __future__ import annotations

import hashlib
import os
import sys
import threading
from types import BuiltinFunctionType, MethodDescriptorType, ModuleType

from hmp_plugin.presentation_startup_artifacts import StartupArtifactOwner, _Scope

from .gateway_continuation import GatewayContinuationOwner
from .gateway_entry import GatewayEntryOwner

_OWNER = _ROOT = _CELL = _READY = None


class RuntimeReadError(Exception):
    def __init__(self, owner=None):
        super().__init__('BI1_RUNTIME_SOURCE_READ_REFUSED')
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise RuntimeReadError


def _context():
    value = (os.getpid(), os.geteuid(), threading.get_ident())
    _require(all(type(part) is int for part in value))
    return value


def _sha_origin():
    _require(type(sys.modules) is dict and type(hashlib) is ModuleType
             and sys.modules.get('hashlib') is hashlib)
    native = sys.modules.get('_hashlib')
    _require(type(native) is ModuleType)
    function, kind = vars(native).get('openssl_sha256'), vars(native).get('HASH')
    _require(type(function) is BuiltinFunctionType and function.__self__ is native
             and type(function.__module__) is str and function.__module__ == '_hashlib'
             and type(function.__name__) is str and function.__name__ == 'openssl_sha256'
             and vars(hashlib).get('sha256') is function and type(kind) is type)
    method = vars(kind).get('hexdigest')
    _require(type(method) is MethodDescriptorType and method.__objclass__ is kind)
    return native, function, kind, method


def _sha_current(origin):
    _require(type(origin) is tuple and len(origin) == 4)
    current = _sha_origin()
    _require(all(a is b for a, b in zip(origin, current, strict=True)))
    return origin


class RuntimeSourceReadOwner:
    @classmethod
    def retain(cls, continuation, index):
        global _OWNER, _ROOT, _CELL
        from hmp_plugin.presentation_source_digest import SourceDigestContext

        from .cache_selection import selected_cache_input_attempts

        _require(cls is RuntimeSourceReadOwner and type(continuation) is GatewayContinuationOwner
                 and type(index) is int and index >= 0
                 and _OWNER is None and _ROOT is None and _CELL is None and _READY is None)
        hash_origin = _sha_origin()
        root = GatewayContinuationOwner.current_binding(continuation)
        activation = root[1]
        _require(activation._runtime_read_owner is None and activation._runtime_read_cell is None)
        owner = cls.__new__(cls)
        _OWNER = activation._runtime_read_owner = owner  # before callbacks
        owner._root_cell = partial = (activation, owner, None)
        _ROOT = activation._runtime_read_cell = partial
        owner._origin = owner._scope = owner._cell = None
        owner._continuation, owner._continuation_root = continuation, root
        buffer = bytearray()
        owner._buffer = owner._original_buffer = buffer
        owner._bytes_read = 0
        owner._count_cell = None
        owner._ready = owner._failed = owner._unknown = owner._reading = False
        owner._started = owner._released = False
        owner._retaining = True
        owner._receipt = owner._read_fact = None
        owner._compiler_owner = owner._compiler_cell = None
        try:
            rows = selected_cache_input_attempts(continuation)
            _require(index < len(rows) and activation._runtime_read_owner is owner
                     and activation._runtime_read_cell is partial
                     and owner._root_cell is partial)
            selected = rows[index]
            owner._selected = selected
            expected = selected.source.receipt.expected
            context = _context()
            _require(context == root[2].entry_binding[0].context
                     and _OWNER is owner and _ROOT is partial and _CELL is None
                     and activation._runtime_read_owner is owner
                     and activation._runtime_read_cell is partial
                     and owner._root_cell is partial and owner._selected is selected
                     and owner._original_buffer is buffer and owner._buffer is buffer
                     and owner._continuation is continuation
                     and owner._continuation_root is root
                     and _sha_current(hash_origin) is hash_origin)
            digest_context = SourceDigestContext(root[2].entry, root[2].entry_binding,
                                                 root[2].entry_binding[0].interpreter,
                                                 activation, [],
                                                 root[2].entry_binding[0].native_files)
            scope = _Scope(activation, root[2].io_scope.activation_scope, (expected,),
                           context, [], reads=[], source_digest=digest_context,
                           native_files=digest_context.native_files)
            scope = scope._replace(parent=(root, selected, buffer,
                                          scope.records, scope.reads, hash_origin))
            owner._origin = owner._scope = scope
            runtime_cell = (owner, scope)
            _CELL = owner._cell = runtime_cell
            runtime_root = (activation, owner, scope)
            owner._root_cell = runtime_root
            _ROOT = activation._runtime_read_cell = runtime_root
            owner._count_cell = (owner, scope, 0)
            _require(RuntimeSourceReadOwner._guard(owner) is scope
                     and _ROOT is runtime_root and _CELL is runtime_cell
                     and owner._cell is runtime_cell
                     and _OWNER is owner and owner._root_cell is runtime_root
                     and owner._origin is scope and scope.parent[1] is selected
                     and scope.parent[2] is buffer and owner._buffer is buffer
                     and owner._original_buffer is buffer
                     and owner._started is False and owner._ready is False
                     and owner._released is False and owner._read_fact is None)
            owner._retaining = False
            return owner
        except BaseException:
            owner._failed = True
            raise RuntimeReadError(owner) from None

    def __repr__(self):
        return '<RuntimeSourceReadOwner fresh-phase not-admission redacted>'

    def _original(self):
        from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner
        from hmp_plugin.presentation_source_digest import SourceDigestContext, SourceDigestFact
        from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact, _HashedArtifact

        from .bytecode_headers import SourceHashData
        from .cache_selection import BoundCacheInputAttempt
        from .gateway_continuation import _ContinuationSource

        _require(type(self) is RuntimeSourceReadOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 3
                 and _ROOT[1] is self and type(_ROOT[2]) is _Scope
                 and type(_CELL) is tuple and len(_CELL) == 2)
        runtime_root, cell, s = _ROOT, _CELL, _ROOT[2]
        _require(type(s.parent) is tuple and len(s.parent) == 6
                 and type(s.parent[0]) is tuple and len(s.parent[0]) == 3
                 and type(s.parent[1]) is BoundCacheInputAttempt
                 and type(s.parent[2]) is bytearray
                 and type(s.parent[3]) is list and type(s.parent[4]) is list)
        root, selected, buffer, records, reads, hash_origin = s.parent
        _require(_sha_current(hash_origin) is hash_origin)
        _require(type(root[0]) is GatewayContinuationOwner
                 and type(root[2]) is _ContinuationSource
                 and type(selected.source) is SourceHashData
                 and type(selected.source.receipt) is _HashedArtifact
                 and type(selected.source.receipt.expected) is ExpectedArtifact
                 and type(selected.source.fact) is SourceDigestFact
                 and selected.source.receipt.source_digest is selected.source.fact
                 and type(s.activation) is GatewayActivationOwner
                 and type(selected.source.receipt.expected.size) is int
                 and 0 <= selected.source.receipt.expected.size <= 128 * 1024 * 1024
                 and type(selected.source.receipt.expected.path) is str
                 and type(selected.source.receipt.expected.sha256) is str
                 and type(s.source_digest) is SourceDigestContext
                 and s.source_digest.entry is root[2].entry
                 and s.source_digest.binding is root[2].entry_binding
                 and s.source_digest.activation is s.activation
                 and s.native_files is s.source_digest.native_files
                 and s.native_files is GatewayEntryOwner._native_file_lineage(root[2].entry)
                 and type(selected.source.receipt.sha256) is str
                 and type(selected.source.receipt.identity) is tuple
                 and len(selected.source.receipt.identity) == 9
                 and all(type(value) is int for value in selected.source.receipt.identity)
                 and type(s.expected) is tuple and len(s.expected) == 1
                 and s.expected[0] is selected.source.receipt.expected
                 and s.records is records and s.reads is reads
                 and self._origin is s and self._scope is s
                 and self._cell is cell and cell[0] is self and cell[1] is s
                 and self._root_cell is runtime_root and runtime_root[0] is s.activation
                 and self._continuation_root is root and self._continuation is root[0]
                 and self._selected is selected
                 and self._original_buffer is buffer and self._buffer is buffer
                 and root[1] is s.activation
                 and s.activation._runtime_read_owner is self
                 and s.activation._runtime_read_cell is runtime_root
                 and self._failed is False and self._unknown is False
                 and type(self._released) is bool and type(self._retaining) is bool
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and self._count_cell[2] is self._bytes_read
                 and type(self._bytes_read) is int
                 and 0 <= self._bytes_read <= s.expected[0].size
                 and len(buffer) <= s.expected[0].size)
        if self._ready is True:
            _require(type(_READY) is tuple and len(_READY) == 8
                     and self._read_fact is _READY
                     and _READY[0] is self and _READY[1] is runtime_root
                     and _READY[2] is cell and _READY[3] is selected and _READY[4] is buffer
                     and type(_READY[5]) is _HashedArtifact
                     and self._receipt is _READY[5] and _READY[5].owner is self
                     and _READY[5].scope is s and _READY[5].expected is s.expected[0]
                     and _READY[6] is self._count_cell
                     and type(_READY[7]) is SourceDigestFact
                     and _READY[5].source_digest is _READY[7]
                     and _READY[7].count is _READY[6])
        else:
            _require(self._ready is False and _READY is None
                     and self._read_fact is None and self._receipt is None)
        return s, runtime_root, cell, selected, buffer, root

    def _guard(self):
        held = RuntimeSourceReadOwner._original(self)
        _require(self._released is False)
        s, _, _, _, _, root = held
        _require(root[0]._root is root and root[0]._source is root[2]
                 and GatewayContinuationOwner._seal(root[0]) is root[2]
                 and _context() == s.context)
        current = RuntimeSourceReadOwner._original(self)
        _require(all(a is b for a, b in zip(held, current, strict=True))
                 and self._released is False
                 and root[0]._root is root and root[0]._source is root[2]
                 and GatewayContinuationOwner._seal(root[0]) is root[2])
        return s

    def _append(self, data):
        s = RuntimeSourceReadOwner._guard(self)
        _require(self._started is True and self._ready is False and type(data) is bytes)
        buffer, cell = self._original_buffer, self._count_cell
        _require(type(cell) is tuple and len(cell) == 3 and cell[0] is self and cell[1] is s
                 and cell[2] is self._bytes_read
                 and len(buffer) + len(data) == self._bytes_read)
        buffer.extend(data)
        _require(RuntimeSourceReadOwner._guard(self) is s and self._count_cell is cell)

    def read(self):
        global _READY
        # Pure original-owner/shape checks precede the sticky attempt, then all
        # callback-bearing work is inside the failure/cleanup boundary.
        from hmp_plugin.presentation_source_digest import seal_fact

        s, _, _, selected, buffer, _ = RuntimeSourceReadOwner._original(self)
        _require(self._started is False and self._ready is False and self._released is False
                 and self._retaining is False)
        self._started = True
        failed = False
        snapshot = digest = None
        try:
            _require(RuntimeSourceReadOwner._guard(self) is s)
            receipt = StartupArtifactOwner._file(self, s.expected[0])
            count = self._count_cell
            source_fact = receipt.source_digest
            expected_sha = s.expected[0].sha256
            _require(RuntimeSourceReadOwner._guard(self) is s
                     and self._selected is selected and self._original_buffer is buffer
                     and receipt.expected is s.expected[0]
                     and receipt.identity == selected.source.receipt.identity
                     and receipt.sha256 == selected.source.receipt.sha256
                     and seal_fact(source_fact) is source_fact
                     and source_fact.count is count
                     and receipt.source_hash == selected.source.receipt.source_hash
                     and receipt.source_mtime == selected.source.receipt.source_mtime
                     and self._bytes_read == s.expected[0].size
                     and len(buffer) == self._bytes_read
                     and all(row.closed is True and row.close_attempted is True
                             and row.unknown is False for row in s.records))
            # The immutable snapshot is a bounded temporary (not retained in a
            # receipt). Native SHA origin and the final pure byte comparison
            # cover same-length mutation across callbacks/GIL release.
            snapshot = bytes(buffer)
            hash_origin = s.parent[5]
            _require(_sha_current(hash_origin) is hash_origin)
            digest = hash_origin[1](snapshot)
            _require(type(digest) is hash_origin[2])
            actual_hash = hash_origin[3](digest)
            _require(type(actual_hash) is str and actual_hash == expected_sha
                     and RuntimeSourceReadOwner._guard(self) is s
                     and self._selected is selected and self._original_buffer is buffer
                     and _sha_current(hash_origin) is hash_origin
                     and self._count_cell is count and source_fact.count is count
                     and receipt.source_digest is source_fact
                     and seal_fact(source_fact) is source_fact
                     and buffer == snapshot)
            _require(_READY is None and self._read_fact is None and self._receipt is None)
            ready = (self, self._root_cell, self._cell, selected, buffer,
                     receipt, count, source_fact)
            self._receipt = receipt
            self._read_fact = _READY = ready
            self._ready = True
        except BaseException:
            self._failed = failed = True
        finally:
            snapshot = digest = None
        if failed:
            RuntimeSourceReadOwner._clear(self, buffer)
            raise RuntimeReadError(self) from None
        return self

    def historical_binding(self):
        """Original completed read DATA; no actor or current-byte authority."""
        from hmp_plugin.presentation_source_digest import seal_fact

        s, _, _, _, buffer, root = RuntimeSourceReadOwner._original(self)
        _require(self._ready is True and self._retaining is False)
        ready = _READY
        _require((len(buffer) == 0 if self._released else len(buffer) == s.expected[0].size)
                 and root[0]._root is root and root[0]._source is root[2]
                 and GatewayContinuationOwner._seal(root[0]) is root[2]
                 and seal_fact(ready[7]) is ready[7]
                 and _READY is ready and self._read_fact is ready
                 and self._count_cell is ready[6] and self._receipt is ready[5])
        return ready

    def completed_binding(self):
        """Actual current owner; bytes still need a content seal before use."""
        ready = RuntimeSourceReadOwner.historical_binding(self)
        RuntimeSourceReadOwner._guard(self)
        _require(RuntimeSourceReadOwner.historical_binding(self) is ready)
        return ready

    def _clear(self, buffer):
        # Clear the captured original allocation even if a mutable slot changed.
        _require(type(buffer) is bytearray)
        zeros = bytes(65536)
        for start in range(0, len(buffer), len(zeros)):
            buffer[start:start + len(zeros)] = zeros[:min(len(zeros), len(buffer) - start)]
        buffer.clear()

    def release(self):
        # Destruction consults independently anchored ownership, never the
        # mutable buffer slot. Foreign replacements are deliberately untouched.
        _require(type(self) is RuntimeSourceReadOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 3 and _ROOT[1] is self
                 and type(_ROOT[2]) is _Scope and self._released is False
                 and self._ready is True and self._reading is False)
        root, s = _ROOT, _ROOT[2]
        _require(type(s.parent) is tuple and len(s.parent) == 6
                 and type(s.parent[0]) is tuple and len(s.parent[0]) == 3
                 and type(s.parent[0][0]) is GatewayContinuationOwner
                 and type(s.parent[2]) is bytearray)
        continuation_root, buffer = s.parent[0], s.parent[2]
        _require(_context() == s.context
                 and _ROOT is root and _OWNER is self
                 and s.activation._runtime_read_owner is self
                 and s.activation._runtime_read_cell is root
                 and continuation_root[0]._root is continuation_root
                 and continuation_root[0]._source is continuation_root[2]
                 and GatewayContinuationOwner._seal(continuation_root[0]) is continuation_root[2]
                 and self._released is False and self._reading is False)
        self._released = True
        RuntimeSourceReadOwner._clear(self, buffer)
