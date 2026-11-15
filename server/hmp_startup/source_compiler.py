"""Owned native source compilation only; never execution or runtime admission."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from types import CodeType
from typing import NamedTuple

from .gateway_entry import _interpreter_current, _InterpreterOrigin, _SourceCompileOrigin
from .runtime_reader import RuntimeSourceReadOwner, _sha_current

_OWNER = _ROOT = _FACT = None


class SourceCompileError(Exception):
    def __init__(self, owner=None):
        super().__init__('BI1_SOURCE_COMPILATION_REFUSED')
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise SourceCompileError


@dataclass(repr=False)
class _CompileEffect:
    attempted: bool = False
    returned: bool = False
    unknown: bool = False
    code: object = None
    fact: object = None


class _CompileScope(NamedTuple):
    source: RuntimeSourceReadOwner
    read: tuple
    interpreter: _InterpreterOrigin
    compiler: _SourceCompileOrigin
    effect: _CompileEffect
    context: tuple

    def __repr__(self):
        return '<OriginalSourceCompileScope not-admission redacted>'


def _context():
    context = (os.getpid(), os.geteuid(), threading.get_ident())
    _require(all(type(value) is int for value in context))
    return context


class SourceCompilationOwner:
    @classmethod
    def retain(cls, source):
        global _OWNER, _ROOT
        _require(cls is SourceCompilationOwner and type(source) is RuntimeSourceReadOwner
                 and _OWNER is None and _ROOT is None and _FACT is None)
        read = RuntimeSourceReadOwner.completed_binding(source)
        _require(source._compiler_owner is None and source._compiler_cell is None
                 and _OWNER is None and _ROOT is None and _FACT is None)
        runtime_scope = read[1][2]
        interpreter = runtime_scope.parent[0][2].entry_binding[0].interpreter
        _require(type(interpreter) is _InterpreterOrigin
                 and type(interpreter.source_compile) is _SourceCompileOrigin)
        effect = _CompileEffect()
        scope = _CompileScope(source, read, interpreter, interpreter.source_compile,
                              effect, runtime_scope.context)
        owner = cls.__new__(cls)
        root = (owner, scope)
        owner._scope, owner._root = scope, root
        owner._started = owner._ready = owner._failed = False
        owner._retaining = True
        owner._admitting = False
        owner._fact = None
        _OWNER = source._compiler_owner = owner
        _ROOT = source._compiler_cell = root
        try:
            _require(SourceCompilationOwner._guard(owner) is scope
                     and _ROOT is root and _OWNER is owner
                     and owner._scope is scope and owner._root is root
                     and RuntimeSourceReadOwner.completed_binding(source) is read
                     and SourceCompilationOwner._pure(owner) is scope and _ROOT is root
                     and owner._started is False and owner._ready is False
                     and owner._retaining is True)
            owner._retaining = False
            return owner
        except BaseException:
            owner._failed = True
        raise SourceCompileError(owner) from None

    def __repr__(self):
        return '<SourceCompilationOwner no-execution not-admission redacted>'

    def _pure(self):
        _require(type(self) is SourceCompilationOwner and _OWNER is self
                 and type(_ROOT) is tuple and len(_ROOT) == 2 and _ROOT[0] is self
                 and type(_ROOT[1]) is _CompileScope)
        scope, root = _ROOT[1], _ROOT
        _require(self._root is root and self._scope is scope and self._failed is False
                 and type(self._started) is bool and type(self._retaining) is bool
                 and type(self._admitting) is bool
                 and type(scope.source) is RuntimeSourceReadOwner
                 and type(scope.read) is tuple and len(scope.read) == 8
                 and type(scope.interpreter) is _InterpreterOrigin
                 and type(scope.compiler) is _SourceCompileOrigin
                 and scope.compiler is scope.interpreter.source_compile
                 and type(scope.effect) is _CompileEffect
                 and scope.source._compiler_owner is self
                 and scope.source._compiler_cell is root
                 and RuntimeSourceReadOwner.historical_binding(scope.source) is scope.read)
        if self._ready is True:
            _require(type(_FACT) is tuple and len(_FACT) == 5
                     and self._fact is _FACT and scope.effect.fact is _FACT
                     and _FACT[0] is self and _FACT[1] is scope
                     and _FACT[2] is scope.effect and type(_FACT[3]) is CodeType
                     and scope.effect.code is _FACT[3] and _FACT[4] is scope.read)
        else:
            _require(self._ready is False and _FACT is None and self._fact is None
                     and scope.effect.fact is None)
        return scope

    def _guard(self):
        scope = SourceCompilationOwner._pure(self)
        root, fact = _ROOT, _FACT
        started, retaining = self._started, self._retaining
        code = None if fact is None else fact[3]
        _require(_context() == scope.context
                 and _interpreter_current(scope.interpreter) is scope.interpreter
                 and SourceCompilationOwner._pure(self) is scope and _ROOT is root
                 and _FACT is fact and self._fact is fact
                 and self._started is started and self._retaining is retaining
                 and (fact is None or scope.effect.code is code))
        return scope

    def compile(self):
        global _FACT
        scope = SourceCompilationOwner._pure(self)
        _require(self._started is False and self._ready is False and self._retaining is False
                 and self._admitting is False)
        root = _ROOT
        self._admitting = True  # reentrance exclusion, not attempt consumption
        admitted = False
        try:
            actor = _context()
            _require(SourceCompilationOwner._pure(self) is scope and _ROOT is root
                     and self._started is False and self._ready is False
                     and self._retaining is False and self._admitting is True)
            admitted = actor == scope.context
        except BaseException:
            admitted = False
        finally:
            if self._admitting is True:
                self._admitting = False
        _require(admitted is True)
        self._started = True
        source, read, effect = scope.source, scope.read, scope.effect
        buffer = read[4]
        snapshot = digest = code = None
        failed = False
        owned = True  # original actor admitted before attempt consumption
        try:
            _require(SourceCompilationOwner._guard(self) is scope
                     and RuntimeSourceReadOwner.completed_binding(source) is read
                     and effect.attempted is False and effect.returned is False
                     and effect.unknown is False and effect.code is None)
            owned = True
            expected = read[5].expected
            snapshot = bytes(buffer)
            hash_origin = read[1][2].parent[5]
            _require(_sha_current(hash_origin) is hash_origin)
            digest = hash_origin[1](snapshot)
            _require(type(digest) is hash_origin[2])
            actual_sha = hash_origin[3](digest)
            _require(type(actual_sha) is str and actual_sha == expected.sha256
                     and SourceCompilationOwner._guard(self) is scope
                     and RuntimeSourceReadOwner.completed_binding(source) is read
                     and _sha_current(hash_origin) is hash_origin
                     and SourceCompilationOwner._pure(self) is scope
                     and self._started is True and buffer == snapshot)
            effect.attempted = True
            code = scope.compiler.compiler(snapshot, expected.path, 'exec', flags=0,
                                           dont_inherit=True,
                                           optimize=scope.interpreter.flags.optimize)
            effect.code, effect.returned = code, True  # actual return before callbacks
            _require(type(code) is CodeType and type(code.co_filename) is str
                     and code.co_filename == expected.path
                     and SourceCompilationOwner._guard(self) is scope
                     and RuntimeSourceReadOwner.completed_binding(source) is read
                     and effect.attempted is True and effect.returned is True
                     and effect.unknown is False and effect.code is code
                     and SourceCompilationOwner._pure(self) is scope
                     and self._started is True and buffer == snapshot)
            RuntimeSourceReadOwner.release(source)
            _require(SourceCompilationOwner._guard(self) is scope
                     and RuntimeSourceReadOwner.historical_binding(source) is read
                     and source._released is True and len(buffer) == 0
                     and effect.code is code and effect.returned is True
                     and effect.unknown is False and _FACT is None and self._fact is None
                     and SourceCompilationOwner._pure(self) is scope
                     and self._started is True)
            fact = (self, scope, effect, code, read)
            self._fact = scope.effect.fact = _FACT = fact
            self._ready = True
        except BaseException:
            self._failed = failed = True
            effect.unknown = effect.attempted
            if effect.code is code:
                effect.code = None
        finally:
            snapshot = digest = code = None
        if failed:
            if owned:
                RuntimeSourceReadOwner._clear(source, buffer)
            raise SourceCompileError(self) from None
        return self

    def current_binding(self):
        scope = SourceCompilationOwner._pure(self)
        _require(self._ready is True and self._retaining is False)
        fact, effect, code, root = _FACT, scope.effect, _FACT[3], _ROOT
        admitted = failed = False
        try:
            admitted = _context() == scope.context
            _require(admitted is True and _ROOT is root
                     and _FACT is fact and self._fact is fact and effect.fact is fact
                     and SourceCompilationOwner._guard(self) is scope
                     and _FACT is fact and self._fact is fact and fact[1] is scope
                     and scope.effect is effect and effect.code is code and fact[3] is code)
        except BaseException:
            failed = True
            if admitted:
                self._failed = True
        if failed:
            raise SourceCompileError(self) from None
        return fact
