"""Historical native cache decode/fix effects; never execution authority."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import CodeType
from typing import NamedTuple

from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact, _HashedArtifact

from .bytecode_headers import SourceHashData
from .cache_reader import DeclaredCacheReadOwner, _actor
from .cache_selection import BoundCacheInputAttempt, CacheInputAttempt, source_loader_input
from .gateway_continuation import GatewayContinuationOwner
from .gateway_entry import _CacheDecodeOrigin, _interpreter_current, _InterpreterOrigin
from .runtime_reader import _sha_current

_OWNER = _ROOT = _INPUT = _OBSERVED = _LOAD = _FIX = _FACT = None


class CacheDecodeError(Exception):
    def __init__(self, owner=None):
        super().__init__('BI1_SELECTED_CACHE_DECODE_REFUSED')
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise CacheDecodeError


@dataclass(repr=False)
class _DecodeEffects:
    load_attempted: bool = False
    load_returned: bool = False
    load_unknown: bool = False
    load_slot: list = field(default_factory=lambda: [None])
    fix_attempted: bool = False
    fix_returned: bool = False
    fix_unknown: bool = False
    fix_slot: list = field(default_factory=lambda: [None])
    release_attempted: bool = False
    release_returned: bool = False
    observed: object = None
    fact: object = None


class _DecodeScope(NamedTuple):
    reader: DeclaredCacheReadOwner
    read: tuple
    interpreter: _InterpreterOrigin
    decoder: _CacheDecodeOrigin
    source: ExpectedArtifact
    context: tuple
    effects: _DecodeEffects
    load_slot: list
    fix_slot: list

    def __repr__(self):
        return '<SelectedCacheDecodeScope historical-effects-only>'


def _decision(scope, header):
    selected = scope.read[3]
    _require(type(selected) is BoundCacheInputAttempt
             and type(selected.attempt) is CacheInputAttempt
             and type(selected.attempt.input) is str
             and type(selected.attempt.validation) is str
             and (selected.attempt.flags is None or type(selected.attempt.flags) is int)
             and type(selected.source) is SourceHashData
             and type(selected.source.receipt) is _HashedArtifact
             and selected.source.receipt.expected is scope.source
             and type(selected.source.receipt.source_mtime) is int
             and type(selected.source.receipt.source_hash) is bytes
             and len(selected.source.receipt.source_hash) == 8
             and type(scope.source.path) is str and type(scope.source.size) is int
             and type(header) is bytes and len(header) == 16)
    actual = source_loader_input(header, scope.interpreter.bytecode_magic,
                                 selected.source.receipt.source_mtime, scope.source.size,
                                 selected.source.receipt.source_hash,
                                 scope.interpreter.cache_policy.mode, 'declared')
    _require(actual == selected.attempt and actual.input == 'cache')
    return actual


class SelectedCacheDecodeOwner:
    @classmethod
    def retain(cls, reader):
        global _OWNER, _ROOT
        _require(cls is SelectedCacheDecodeOwner and type(reader) is DeclaredCacheReadOwner
                 and _OWNER is _ROOT is _INPUT is _OBSERVED is _LOAD is _FIX is _FACT is None)
        read = DeclaredCacheReadOwner.current_binding(reader)
        _require(reader._decoder_owner is None and reader._decoder_cell is None
                 and reader._decoder_fact is None)
        runtime = read[1][2]
        interpreter = runtime.parent[0][2].entry_binding[0].interpreter
        _require(type(interpreter) is _InterpreterOrigin
                 and type(interpreter.cache_decode) is _CacheDecodeOrigin
                 and type(read[3]) is BoundCacheInputAttempt
                 and type(read[3].plan_row.source) is ExpectedArtifact)
        effects = _DecodeEffects()
        scope = _DecodeScope(reader, read, interpreter, interpreter.cache_decode,
                             read[3].plan_row.source, runtime.context, effects,
                             effects.load_slot, effects.fix_slot)
        owner = cls.__new__(cls)
        root = (owner, scope)
        owner._scope, owner._root = scope, root
        owner._ready = owner._failed = owner._started = owner._admitting = False
        owner._decoding = owner._source_released = False
        owner._retaining = True
        owner._fact = owner._payload = None
        _OWNER = reader._decoder_owner = owner
        _ROOT = reader._decoder_cell = root
        try:
            _decision(scope, read[5].bytecode_header)
            _require(SelectedCacheDecodeOwner._guard(owner) is scope
                     and _ROOT is root and _OWNER is owner and owner._scope is scope
                     and owner._retaining is True and owner._started is False
                     and DeclaredCacheReadOwner.current_binding(reader) is read
                     and SelectedCacheDecodeOwner._pure(owner) is scope and _ROOT is root)
            owner._retaining = False
            return owner
        except BaseException:
            owner._failed = True
        raise CacheDecodeError(owner) from None

    def __repr__(self):
        return '<SelectedCacheDecodeOwner historical-only no-execution>'

    def _pure(self):
        _require(type(self) is SelectedCacheDecodeOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 2 and _ROOT[0] is self
                 and type(_ROOT[1]) is _DecodeScope)
        scope, root = _ROOT[1], _ROOT
        _require(self._scope is scope and self._root is root and self._failed is False
                 and all(type(value) is bool for value in
                         (self._ready, self._started, self._admitting, self._retaining,
                          self._decoding, self._source_released))
                 and type(scope.reader) is DeclaredCacheReadOwner
                 and type(scope.read) is tuple and len(scope.read) == 11
                 and type(scope.interpreter) is _InterpreterOrigin
                 and type(scope.decoder) is _CacheDecodeOrigin
                 and scope.decoder is scope.interpreter.cache_decode
                 and type(scope.source) is ExpectedArtifact
                 and type(scope.effects) is _DecodeEffects
                 and scope.reader._decoder_owner is self
                 and scope.reader._decoder_cell is root
                 and scope.reader._fact is scope.read
                 and DeclaredCacheReadOwner._pure(scope.reader) is scope.read[1][2]
                 and scope.reader._released is self._source_released
                 and len(scope.read[4]) ==
                 (0 if self._source_released else scope.read[5].expected.size))
        effect = scope.effects
        _require(type(scope.load_slot) is list and len(scope.load_slot) == 1
                 and type(scope.fix_slot) is list and len(scope.fix_slot) == 1
                 and effect.load_slot is scope.load_slot and effect.fix_slot is scope.fix_slot
                 and effect.load_unknown is False and effect.fix_unknown is False
                 and all(type(value) is bool for value in
                         (effect.load_attempted, effect.load_returned, effect.fix_attempted,
                          effect.fix_returned, effect.release_attempted, effect.release_returned)))
        if _INPUT is None:
            _require(self._payload is None)
        else:
            _require(type(_INPUT) is tuple and len(_INPUT) == 3 and _INPUT[0] is scope
                     and self._payload is _INPUT and type(_INPUT[1]) is bytes
                     and type(_INPUT[2]) is memoryview and _INPUT[2].obj is _INPUT[1]
                     and _INPUT[2].readonly is True and _INPUT[2].nbytes == len(_INPUT[1]) - 16)
        _require(effect.observed is _OBSERVED)
        if _OBSERVED is not None:
            _require(type(_OBSERVED) is tuple and len(_OBSERVED) == 6
                     and _OBSERVED[0] is scope.reader and _OBSERVED[1] is scope.read
                     and _OBSERVED[2] is scope.read[6] and type(_OBSERVED[3]) is str
                     and type(_OBSERVED[4]) is bytes and len(_OBSERVED[4]) == 16
                     and type(_OBSERVED[5]) is int
                     and _OBSERVED[5] == scope.read[5].expected.size - 16)
        if _LOAD is None:
            _require(effect.load_slot[0] is None and effect.load_returned is False)
        else:
            _require(type(_LOAD) is tuple and len(_LOAD) == 3 and _LOAD[0] is effect
                     and _LOAD[2] is _OBSERVED and effect.load_slot[0] is _LOAD
                     and effect.load_attempted is True and effect.load_returned is True)
        if _FIX is None:
            _require(effect.fix_slot[0] is None and effect.fix_returned is False)
        else:
            _require(type(_FIX) is tuple and len(_FIX) == 4 and _FIX[0] is effect
                     and _LOAD is not None and _FIX[1] is _LOAD[1] and _FIX[2] is None
                     and _FIX[3] is _LOAD and effect.fix_slot[0] is _FIX
                     and effect.fix_attempted is True and effect.fix_returned is True)
        if self._ready is True:
            _require(type(_FACT) is tuple and len(_FACT) == 7 and self._fact is _FACT
                     and effect.fact is _FACT and scope.reader._decoder_fact is _FACT
                     and _FACT[0] is self and _FACT[1] is scope and _FACT[2] is effect
                     and type(_FACT[3]) is CodeType and _FACT[3] is _LOAD[1]
                     and _FACT[4] is _OBSERVED and _FACT[5] is _LOAD and _FACT[6] is _FIX
                     and _INPUT is None and self._source_released is True
                     and self._decoding is False and effect.release_returned is True)
        else:
            _require(self._ready is False and _FACT is None and self._fact is None
                     and effect.fact is None and scope.reader._decoder_fact is None)
        return scope

    def _guard(self):
        scope = SelectedCacheDecodeOwner._pure(self)
        held = (_ROOT, _INPUT, _OBSERVED, _LOAD, _FIX, _FACT)
        lifecycle = (self._started, self._retaining, self._admitting, self._decoding,
                     self._source_released)
        parent = scope.read[1][2].parent[0]
        _require(_actor() == scope.context
                 and _interpreter_current(scope.interpreter) is scope.interpreter
                 and parent[0]._root is parent and parent[0]._source is parent[2]
                 and GatewayContinuationOwner._seal(parent[0]) is parent[2]
                 and SelectedCacheDecodeOwner._pure(self) is scope
                 and all(a is b for a, b in zip(
                     held, (_ROOT, _INPUT, _OBSERVED, _LOAD, _FIX, _FACT), strict=True))
                 and all(a is b for a, b in zip(lifecycle,
                     (self._started, self._retaining, self._admitting, self._decoding,
                      self._source_released), strict=True)))
        return scope

    def decode(self):
        global _INPUT, _OBSERVED, _LOAD, _FIX, _FACT
        scope = SelectedCacheDecodeOwner._pure(self)
        _require(self._started is False and self._retaining is False
                 and self._admitting is False and self._decoding is False and self._ready is False)
        root = _ROOT
        self._admitting = True
        admitted = False
        try:
            actor = _actor()
            _require(SelectedCacheDecodeOwner._pure(self) is scope and _ROOT is root
                     and self._started is False and self._admitting is True)
            admitted = actor == scope.context
        except BaseException:
            admitted = False
        finally:
            if self._admitting is True:
                self._admitting = False
        _require(admitted is True)
        self._started = self._decoding = True
        reader, read, effect = scope.reader, scope.read, scope.effects
        buffer = read[4]
        load_slot, fix_slot = scope.load_slot, scope.fix_slot
        snapshot = body = digest = payload = None
        observed = load_result = fix_result = code = fact = None
        failed = False
        load_attempted = fix_attempted = False
        try:
            _require(SelectedCacheDecodeOwner._guard(self) is scope
                     and DeclaredCacheReadOwner.current_binding(reader) is read)
            snapshot = bytes(buffer)
            origin = read[1][2].parent[5]
            _require(_sha_current(origin) is origin)
            digest = origin[1](snapshot)
            _require(type(digest) is origin[2])
            actual_sha = origin[3](digest)
            _require(type(actual_sha) is str and actual_sha == read[5].expected.sha256
                     and snapshot[:16] == read[5].bytecode_header
                     and SelectedCacheDecodeOwner._guard(self) is scope
                     and DeclaredCacheReadOwner.current_binding(reader) is read
                     and _sha_current(origin) is origin and buffer == snapshot)
            _decision(scope, snapshot[:16])
            observed = (reader, read, read[6], actual_sha, snapshot[:16], len(snapshot) - 16)
            _require(_OBSERVED is None and effect.observed is None)
            _OBSERVED = effect.observed = observed
            body = memoryview(snapshot)[16:]
            payload = (scope, snapshot, body)
            _require(_INPUT is None and self._payload is None)
            _INPUT = self._payload = payload
            _require(SelectedCacheDecodeOwner._guard(self) is scope
                     and _INPUT is payload and _OBSERVED is observed and buffer == snapshot
                     and self._decoding is True and self._started is True)
            effect.load_attempted = load_attempted = True
            code = scope.decoder.loads(body)
            load_result = (effect, code, observed)
            load_slot[0] = load_result  # actual return before any refusal/callback
            effect.load_returned = True
            _require(_LOAD is None)
            _LOAD = load_result
            _require(type(code) is CodeType and _ROOT is root and _OBSERVED is observed
                     and _INPUT is payload and self._decoding is True
                     and SelectedCacheDecodeOwner._guard(self) is scope
                     and _LOAD is load_result and effect.load_slot[0] is load_result
                     and buffer == snapshot)
            effect.fix_attempted = fix_attempted = True
            returned = scope.decoder.fix_filename(code, scope.source.path)
            fix_result = (effect, code, returned, load_result)
            fix_slot[0] = fix_result  # actual None return, CodeType was mutated
            effect.fix_returned = True
            _require(_FIX is None and _LOAD is load_result)
            _FIX = fix_result
            _require(returned is None and type(code.co_filename) is str
                     and code.co_filename == scope.source.path
                     and _ROOT is root and _INPUT is payload and _OBSERVED is observed
                     and self._decoding is True and self._started is True
                     and SelectedCacheDecodeOwner._guard(self) is scope
                     and _LOAD is load_result and _FIX is fix_result and buffer == snapshot)
            effect.release_attempted = True
            DeclaredCacheReadOwner.release(reader)
            effect.release_returned = self._source_released = True
            _require(_ROOT is root and _LOAD is load_result and _FIX is fix_result
                     and reader._released is True and len(buffer) == 0)
        except BaseException:
            self._failed = failed = True
        finally:
            if body is not None:
                try:
                    memoryview.release(body)
                except BaseException:
                    self._failed = failed = True
            if _INPUT is payload:
                _INPUT = None
            if self._payload is payload:
                self._payload = None
            snapshot = body = digest = payload = None
            if (_ROOT is root and _OWNER is self and self._scope is scope
                    and reader._decoder_owner is self and reader._decoder_cell is root
                    and self._decoding is True):
                self._decoding = False
            else:
                self._failed = failed = True
        if not failed:
            try:
                fact = (self, scope, effect, code, observed, load_result, fix_result)
                _require(SelectedCacheDecodeOwner._guard(self) is scope
                         and _ROOT is root and _OBSERVED is observed and _LOAD is load_result
                         and _FIX is fix_result and _INPUT is None and self._payload is None
                         and self._started is True and self._decoding is False
                         and self._source_released is True and _FACT is None
                         and self._fact is None and effect.fact is None
                         and reader._decoder_fact is None
                         and type(code.co_filename) is str
                         and code.co_filename == scope.source.path)
                self._fact = effect.fact = _FACT = reader._decoder_fact = fact
                self._ready = True
            except BaseException:
                self._failed = failed = True
        code = fact = None
        if failed:
            # Restore only original owned result cells from actual local returns;
            # foreign replacement lists/global aliases remain untouched.
            load_slot[:] = [load_result]
            fix_slot[:] = [fix_result]
            effect.load_attempted, effect.fix_attempted = load_attempted, fix_attempted
            effect.load_returned = load_result is not None
            effect.fix_returned = fix_result is not None
            effect.load_unknown = load_attempted and load_result is None
            effect.fix_unknown = fix_attempted and fix_result is None
            DeclaredCacheReadOwner._clear(buffer)
            raise CacheDecodeError(self) from None
        return self

    def historical_binding(self):
        """Actual completed effects, NOT current immutable code/filename evidence."""
        scope = SelectedCacheDecodeOwner._pure(self)
        _require(self._ready is True and self._decoding is False)
        fact, root, load, fix = _FACT, _ROOT, _LOAD, _FIX
        admitted = failed = False
        try:
            admitted = _actor() == scope.context
            _require(admitted is True and _ROOT is root and _FACT is fact
                     and _LOAD is load and _FIX is fix
                     and SelectedCacheDecodeOwner._guard(self) is scope and _ROOT is root
                     and _FACT is fact and _LOAD is load and _FIX is fix
                     and self._fact is fact and scope.reader._decoder_fact is fact)
        except BaseException:
            failed = True
            if admitted:
                self._failed = True
        if failed:
            raise CacheDecodeError(self) from None
        return fact
