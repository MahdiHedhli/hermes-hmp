"""One admitted declared-cache read; no fallback, decode or execution authority."""
from __future__ import annotations

import os

from hmp_plugin.presentation_gateway_activation import GatewayActivationOwner
from hmp_plugin.presentation_startup_artifacts import (
    ExpectedArtifact,
    StartupArtifactOwner,
    _Descriptor,
    _HashedArtifact,
    _ReadEffect,
    _Scope,
)

from .cache_selection import BoundCacheInputAttempt, selected_cache_input_attempts
from .gateway_continuation import GatewayContinuationOwner, _ContinuationSource
from .gateway_entry import GatewayEntryOwner
from .runtime_reader import _context, _sha_current, _sha_origin

_OWNER = _ROOT = _CELL = _READY = None
_ATTEMPTS = _RESULTS = ()


class CacheReadError(Exception):
    def __init__(self, owner=None):
        super().__init__('BI1_DECLARED_CACHE_READ_REFUSED')
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise CacheReadError


def _actor():
    value = _context()
    _require(type(value) is tuple and len(value) == 3
             and all(type(part) is int for part in value))
    return value


class DeclaredCacheReadOwner:
    @classmethod
    def retain(cls, continuation, index):
        global _OWNER, _ROOT, _CELL
        _require(cls is DeclaredCacheReadOwner and type(continuation) is GatewayContinuationOwner
                 and type(index) is int and index >= 0
                 and _OWNER is _ROOT is _CELL is _READY is None)
        parent = GatewayContinuationOwner.current_binding(continuation)
        activation = parent[1]
        _require(activation._cache_read_owner is None and activation._cache_read_cell is None
                 and activation._cache_read_fact is None)
        owner = cls.__new__(cls)
        _OWNER = activation._cache_read_owner = owner
        _ROOT = owner._root_cell = activation._cache_read_cell = (activation, owner, None)
        owner._scope = owner._origin = owner._cell = owner._count_cell = None
        owner._started = owner._ready = owner._failed = owner._unknown = False
        owner._reading = owner._released = owner._admitting = False
        owner._read_claim = None
        owner._retaining = True
        owner._bytes_read = 0
        owner._fact = None
        owner._decoder_owner = owner._decoder_cell = owner._decoder_fact = None
        owner._attempts = activation._cache_read_attempts = _ATTEMPTS
        owner._results = activation._cache_read_results = _RESULTS
        buffer = bytearray()
        owner._buffer = buffer
        try:
            partial = _ROOT
            rows = selected_cache_input_attempts(continuation)
            _require(index < len(rows))
            selected = rows[index]
            _require(type(selected) is BoundCacheInputAttempt
                     and type(selected.cache) is _HashedArtifact
                     and type(selected.cache.expected) is ExpectedArtifact)
            expected = selected.cache.expected
            _require(type(expected.size) is int and 0 <= expected.size <= 128 * 1024 * 1024)
            hash_origin = _sha_origin()
            context = _actor()
            _require(context == parent[2].entry_binding[0].context
                     and _OWNER is owner and _ROOT is partial and _CELL is None
                     and owner._root_cell is partial and owner._buffer is buffer
                     and activation._cache_read_cell is partial)
            scope = _Scope(activation, parent[2].io_scope.activation_scope, (expected,),
                           context, [], reads=[],
                           native_files=parent[2].entry_binding[0].native_files)
            scope = scope._replace(parent=(parent, selected, buffer, scope.records,
                                          scope.reads, hash_origin))
            owner._scope = owner._origin = scope
            cell = (owner, scope)
            _CELL = owner._cell = cell
            root = (activation, owner, scope)
            _ROOT = owner._root_cell = activation._cache_read_cell = root
            owner._count_cell = (owner, scope, 0)
            _require(DeclaredCacheReadOwner._guard(owner) is scope and _ROOT is root
                     and _OWNER is owner and _CELL is cell and owner._cell is cell
                     and owner._started is False
                     and owner._retaining is True and owner._ready is False)
            owner._retaining = False
            return owner
        except BaseException:
            owner._failed = True
        raise CacheReadError(owner) from None

    def __repr__(self):
        return '<DeclaredCacheReadOwner no-fallback-no-execution redacted>'

    def _pure(self):
        _require(type(self) is DeclaredCacheReadOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 3 and _ROOT[1] is self
                 and type(_ROOT[2]) is _Scope and type(_CELL) is tuple and len(_CELL) == 2)
        s, root, cell = _ROOT[2], _ROOT, _CELL
        _require(type(s.parent) is tuple and len(s.parent) == 6)
        parent, selected, buffer, records, reads, origin = s.parent
        _require(type(parent) is tuple and len(parent) == 3
                 and type(parent[0]) is GatewayContinuationOwner
                 and type(parent[2]) is _ContinuationSource
                 and type(selected) is BoundCacheInputAttempt
                 and type(selected.cache) is _HashedArtifact
                 and type(selected.cache.expected) is ExpectedArtifact
                 and type(s.activation) is GatewayActivationOwner
                 and type(s.expected) is tuple and len(s.expected) == 1
                 and s.expected[0] is selected.cache.expected
                 and type(s.expected[0].path) is str
                 and type(s.expected[0].sha256) is str
                 and type(selected.cache.identity) is tuple
                 and len(selected.cache.identity) == 9
                 and all(type(value) is int for value in selected.cache.identity)
                 and type(selected.cache.sha256) is str
                 and type(selected.cache.bytecode_header) is bytes
                 and len(selected.cache.bytecode_header) <= 16
                 and type(s.expected[0].size) is int
                 and 0 <= s.expected[0].size <= 128 * 1024 * 1024
                 and type(buffer) is bytearray and self._buffer is buffer
                 and type(records) is list and s.records is records
                 and type(reads) is list and s.reads is reads
                 and self._scope is s and self._origin is s
                 and self._root_cell is root and root[0] is s.activation
                 and self._cell is cell and cell[0] is self and cell[1] is s
                 and parent[1] is s.activation
                 and s.activation._cache_read_owner is self
                 and s.activation._cache_read_cell is root
                 and self._failed is False and self._unknown is False
                 and type(self._released) is bool and type(self._retaining) is bool
                 and type(self._count_cell) is tuple and len(self._count_cell) == 3
                 and self._count_cell[0] is self and self._count_cell[1] is s
                 and type(self._bytes_read) is int and self._count_cell[2] is self._bytes_read
                 and 0 <= self._bytes_read <= s.expected[0].size
                 and len(buffer) <= s.expected[0].size)
        _require(s.native_files is GatewayEntryOwner._native_file_lineage(parent[2].entry)
                 and _sha_current(origin) is origin)
        DeclaredCacheReadOwner._read_chain(self, s, full=self._ready is True)
        if self._ready is True:
            _require(type(_READY) is tuple and len(_READY) == 11
                     and self._fact is _READY and s.activation._cache_read_fact is _READY
                     and _READY[0] is self and _READY[1] is root and _READY[2] is cell
                     and _READY[3] is selected and _READY[4] is buffer
                     and _READY[9] is _ATTEMPTS and _READY[10] is _RESULTS
                     and type(_READY[5]) is _HashedArtifact
                     and _READY[5].owner is self and _READY[5].scope is s
                     and _READY[5].expected is s.expected[0] and _READY[6] is self._count_cell
                     and type(_READY[7]) is tuple and type(_READY[8]) is tuple
                     and len(records) == len(_READY[7]) and len(reads) == len(_READY[8])
                     and all(a is b for a, b in zip(records, _READY[7], strict=True))
                     and all(a is b for a, b in zip(reads, _READY[8], strict=True))
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.close_attempted is True and row.unknown is False
                             for row in records)
                     and all(type(row) is _ReadEffect and row.returned is True
                             and row.unknown is False for row in reads))
        else:
            _require(self._ready is False and _READY is None and self._fact is None
                     and s.activation._cache_read_fact is None)
        return s

    def _guard(self):
        s = DeclaredCacheReadOwner._pure(self)
        root, cell, count, fact = _ROOT, _CELL, self._count_cell, _READY
        attempts, results = _ATTEMPTS, _RESULTS
        parent = s.parent[0]
        lifecycle = (self._started, self._retaining, self._admitting, self._reading)
        claim = self._read_claim
        _require(all(type(value) is bool for value in lifecycle))
        _require(self._released is False and parent[0]._root is parent
                 and parent[0]._source is parent[2]
                 and GatewayContinuationOwner._seal(parent[0]) is parent[2]
                 and _actor() == s.context and DeclaredCacheReadOwner._pure(self) is s
                 and self._released is False and _ROOT is root and _CELL is cell
                 and _READY is fact and self._count_cell is count
                 and _ATTEMPTS is attempts and _RESULTS is results
                 and self._started is lifecycle[0] and self._retaining is lifecycle[1]
                 and self._admitting is lifecycle[2] and self._reading is lifecycle[3]
                 and self._read_claim is claim
                 and parent[0]._root is parent and parent[0]._source is parent[2]
                 and GatewayContinuationOwner._seal(parent[0]) is parent[2])
        return s

    def _read_chain(self, s, full=False):
        _require(type(_ATTEMPTS) is tuple and type(_RESULTS) is tuple
                 and self._attempts is _ATTEMPTS and self._results is _RESULTS
                 and s.activation._cache_read_attempts is _ATTEMPTS
                 and s.activation._cache_read_results is _RESULTS
                 and len(_ATTEMPTS) == len(s.reads) and len(_ATTEMPTS) <= 4096
                 and len(_RESULTS) <= len(_ATTEMPTS) <= len(_RESULTS) + 1)
        start = 0 if full else max(0, len(_ATTEMPTS) - 2)
        previous = None
        if start:
            bridge = _RESULTS[start - 1]
            _require(type(bridge) is tuple and len(bridge) == 3
                     and type(bridge[1]) is tuple and len(bridge[1]) == 3
                     and bridge[1][0] is self and bridge[1][1] is s
                     and type(bridge[1][2]) is int)
            previous = bridge[1]
        for index in range(start, len(_ATTEMPTS)):
            attempt = _ATTEMPTS[index]
            _require(type(attempt) is tuple and len(attempt) == 5
                     and type(attempt[0]) is _ReadEffect and s.reads[index] is attempt[0]
                     and type(attempt[1]) is int and attempt[1] >= 0
                     and type(attempt[2]) is int and 0 < attempt[2] <= 65536
                     and type(attempt[3]) is tuple and len(attempt[3]) == 3
                     and attempt[3][0] is self and attempt[3][1] is s
                     and type(attempt[3][2]) is int
                     and attempt[0].before is attempt[3] and attempt[0].unknown is False
                     and type(attempt[4]) is list and len(attempt[4]) == 1)
            _require(attempt[3][2] == 0 if previous is None else attempt[3] is previous)
            if index < len(_RESULTS):
                result = _RESULTS[index]
                _require(type(result) is tuple and len(result) == 3 and result[0] is attempt
                         and type(result[1]) is tuple and len(result[1]) == 3
                         and result[1][0] is self and result[1][1] is s
                         and type(result[1][2]) is int and type(result[2]) is int
                         and 0 <= result[2] <= attempt[2]
                         and result[1][2] == attempt[3][2] + result[2]
                         and attempt[0].after is result[1] and attempt[0].returned is True
                         and attempt[4][0] is result)
                previous = result[1]
            else:
                _require(self._reading is True and attempt[0].after is None
                         and attempt[0].returned is False and self._count_cell is attempt[3]
                         and attempt[4][0] is None and self._read_claim is attempt)
        if previous is not None:
            _require(self._count_cell is previous)
        else:
            _require(self._bytes_read == 0)

    def _read(self, fd, requested, s):
        global _ATTEMPTS, _RESULTS
        _require(DeclaredCacheReadOwner._guard(self) is s
                 and self._started is True and self._ready is False
                 and self._reading is False and self._read_claim is None
                 and type(fd) is int and fd >= 0
                 and type(requested) is int and 0 < requested <= 65536
                 and len(_ATTEMPTS) < 4096 and len(_ATTEMPTS) == len(_RESULTS))
        root, cell, before = _ROOT, _CELL, self._count_cell
        prior_attempts, prior_results = _ATTEMPTS, _RESULTS
        expected_results = prior_results
        effect = _ReadEffect(before)
        result_slot = [None]
        attempt = (effect, fd, requested, before, result_slot)
        attempts = (*prior_attempts, attempt)
        s.reads.append(effect)
        _ATTEMPTS = self._attempts = s.activation._cache_read_attempts = attempts
        self._reading = True
        self._read_claim = attempt
        data = None
        try:
            data = os.read(fd, requested)
            _require(type(data) is bytes)
            length = len(data)
            after = (self, s, before[2] + length)
            result = (attempt, after, length)
            result_slot[0] = result  # actual return retained even if the next join refuses
            # Actual native return/count allocations precede every callback.
            effect.after, effect.returned = after, True
            same = (_OWNER is self and _ROOT is root and _CELL is cell
                    and s.activation._cache_read_owner is self
                    and s.activation._cache_read_cell is root and self._scope is s
                    and self._origin is s and self._count_cell is before
                    and self._bytes_read is before[2] and self._reading is True
                    and self._read_claim is attempt
                    and _ATTEMPTS is attempts and self._attempts is attempts
                    and s.activation._cache_read_attempts is attempts
                    and _RESULTS is prior_results and self._results is prior_results
                    and s.activation._cache_read_results is prior_results)
            _require(same)
            results = (*prior_results, result)
            _RESULTS = self._results = s.activation._cache_read_results = results
            expected_results = results
            self._count_cell, self._bytes_read = after, after[2]
            self._reading = False
            _require(length <= requested and DeclaredCacheReadOwner._guard(self) is s
                     and _ROOT is root and _CELL is cell and self._count_cell is after
                     and _ATTEMPTS is attempts and _RESULTS is results
                     and effect.after is after and effect.returned is True)
            return data
        except BaseException:
            effect.unknown = self._unknown = True
            raise
        finally:
            if (_OWNER is self and _ROOT is root and _CELL is cell
                    and self._scope is s and self._origin is s
                    and self._root_cell is root and self._cell is cell
                    and s.activation._cache_read_owner is self
                    and s.activation._cache_read_cell is root
                    and _ATTEMPTS is attempts and self._attempts is attempts
                    and s.activation._cache_read_attempts is attempts
                    and _RESULTS is expected_results and self._results is expected_results
                    and s.activation._cache_read_results is expected_results
                    and self._read_claim is attempt and type(self._reading) is bool):
                self._reading = False
                self._read_claim = None
            else:
                self._unknown = True
            data = None

    def _append(self, data):
        s = DeclaredCacheReadOwner._guard(self)
        buffer, count = s.parent[2], self._count_cell
        _require(type(data) is bytes and self._started is True and self._ready is False
                 and len(buffer) + len(data) == self._bytes_read)
        buffer.extend(data)
        _require(DeclaredCacheReadOwner._guard(self) is s and self._count_cell is count
                 and s.parent[2] is buffer)

    def read(self):
        global _READY
        s = DeclaredCacheReadOwner._pure(self)
        _require(self._started is False and self._retaining is False
                 and self._ready is False and self._released is False
                 and self._admitting is False)
        root, cell, count = _ROOT, _CELL, self._count_cell
        selected, buffer = s.parent[1:3]
        self._admitting = True
        admitted = False
        try:
            actor = _actor()
            _require(DeclaredCacheReadOwner._pure(self) is s and _ROOT is root
                     and _CELL is cell and self._count_cell is count
                     and self._started is False and self._ready is False)
            admitted = actor == s.context
        except BaseException:
            admitted = False
        finally:
            if self._admitting is True:
                self._admitting = False
        _require(admitted is True)
        self._started = True
        failed = False
        snapshot = digest = None
        try:
            _require(DeclaredCacheReadOwner._guard(self) is s)
            receipt = StartupArtifactOwner._file(self, s.expected[0])
            count = self._count_cell
            DeclaredCacheReadOwner._read_chain(self, s, full=True)
            records, reads = tuple(s.records), tuple(s.reads)
            ready = (self, root, cell, selected, buffer, receipt, count, records, reads,
                     _ATTEMPTS, _RESULTS)
            snapshot = bytes(buffer)
            origin = s.parent[5]
            _require(_sha_current(origin) is origin)
            digest = origin[1](snapshot)
            _require(type(digest) is origin[2])
            actual_hash = origin[3](digest)
            _require(type(actual_hash) is str and actual_hash == s.expected[0].sha256
                     and receipt.identity == selected.cache.identity
                     and receipt.sha256 == selected.cache.sha256
                     and receipt.bytecode_header == selected.cache.bytecode_header
                     and self._bytes_read == s.expected[0].size and len(buffer) == self._bytes_read
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.close_attempted is True and row.unknown is False
                             for row in records)
                     and all(type(row) is _ReadEffect and row.returned is True
                             and row.unknown is False for row in reads)
                     and DeclaredCacheReadOwner._guard(self) is s and _ROOT is root
                     and _CELL is cell and self._count_cell is count
                     and s.parent[1] is selected and s.parent[2] is buffer
                     and len(s.records) == len(records) and len(s.reads) == len(reads)
                     and all(a is b for a, b in zip(s.records, records, strict=True))
                     and all(a is b for a, b in zip(s.reads, reads, strict=True))
                     and _sha_current(origin) is origin and buffer == snapshot
                     and _ATTEMPTS is ready[9] and _RESULTS is ready[10]
                     and all(type(row) is _Descriptor and row.closed is True
                             and row.close_attempted is True and row.unknown is False
                             for row in records)
                     and all(type(row) is _ReadEffect and row.returned is True
                             and row.unknown is False for row in reads)
                     and self._started is True and self._retaining is False
                     and self._admitting is False and self._ready is False
                     and self._reading is False and self._read_claim is None
                     and _READY is None and self._fact is None
                     and s.activation._cache_read_fact is None)
            DeclaredCacheReadOwner._read_chain(self, s, full=True)
            self._fact = _READY = s.activation._cache_read_fact = ready
            self._ready = True
        except BaseException:
            self._failed = failed = True
        finally:
            snapshot = digest = None
        if failed:
            DeclaredCacheReadOwner._clear(buffer)
            raise CacheReadError(self) from None
        return self

    @staticmethod
    def _clear(buffer):
        _require(type(buffer) is bytearray)
        zeros = bytes(65536)
        for start in range(0, len(buffer), len(zeros)):
            buffer[start:start + len(zeros)] = zeros[:min(len(zeros), len(buffer) - start)]
        buffer.clear()

    def current_binding(self):
        """Original current read; mutable bytes still require a consumer content seal."""
        s = DeclaredCacheReadOwner._pure(self)
        _require(self._ready is True and self._released is False)
        ready, root = _READY, _ROOT
        admitted = failed = False
        try:
            actor = _actor()
            admitted = actor == s.context
            _require(admitted is True and _READY is ready and _ROOT is root
                     and self._fact is ready and s.activation._cache_read_fact is ready
                     and DeclaredCacheReadOwner._guard(self) is s
                     and _READY is ready and _ROOT is root and self._fact is ready
                     and s.activation._cache_read_fact is ready)
        except BaseException:
            failed = True
            if admitted:
                self._failed = True
                DeclaredCacheReadOwner._clear(s.parent[2])
        if failed:
            raise CacheReadError(self) from None
        return ready

    def release(self):
        # A foreign mutable slot must not redirect cleanup away from the original.
        _require(type(self) is DeclaredCacheReadOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 3 and _ROOT[1] is self
                 and type(_ROOT[2]) is _Scope and self._released is False
                 and self._ready is True and self._reading is False)
        root, s = _ROOT, _ROOT[2]
        _require(type(s.parent) is tuple and len(s.parent) == 6
                 and type(s.parent[2]) is bytearray)
        buffer = s.parent[2]
        _require(_actor() == s.context and _ROOT is root and _OWNER is self
                 and s.activation._cache_read_owner is self
                 and s.activation._cache_read_cell is root
                 and self._released is False and self._reading is False)
        self._released = True
        DeclaredCacheReadOwner._clear(buffer)
