"""Same-original-read source hash evidence; no import or runtime admission."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


class SourceDigestError(Exception):
    def __init__(self):
        super().__init__('BI1_SOURCE_DIGEST_REFUSED')


def _require(value):
    if value is not True:
        raise SourceDigestError


class SourceDigestContext(NamedTuple):
    entry: object
    binding: tuple
    interpreter: object
    activation: object
    effects: list

    def __repr__(self):
        return '<OriginalSourceDigestContext redacted>'


@dataclass(repr=False)
class _DigestEffect:
    context: SourceDigestContext
    owner: object
    scope: object
    expected: object
    before: tuple
    buffer: bytearray
    size: int = 0
    attempted: bool = False
    returned: bool = False
    unknown: bool = False
    cleared: bool = False
    result: bytes | None = None
    after: tuple | None = None
    consumed: int = 0


class _DigestRoot(NamedTuple):
    effect: _DigestEffect
    context: SourceDigestContext
    owner: object
    scope: object
    expected: object
    before: tuple
    buffer: bytearray
    reads: list

    def __repr__(self):
        return '<OriginalSourceDigestAllocation redacted>'


def _types(owner, scope, expected):
    from .presentation_gateway_package import GatewayPackageOwner
    from .presentation_startup_artifacts import ExpectedArtifact, StartupArtifactOwner, _Scope

    allowed = type(owner) in (GatewayPackageOwner, StartupArtifactOwner)
    if not allowed:
        from hmp_startup.runtime_reader import RuntimeSourceReadOwner
        allowed = type(owner) is RuntimeSourceReadOwner
    _require(allowed and type(scope) is _Scope and type(expected) is ExpectedArtifact)


def retain(entry, activation):
    from hmp_startup.gateway_entry import GatewayEntryOwner

    _require(type(entry) is GatewayEntryOwner)
    binding = GatewayEntryOwner._retained_binding(entry)
    current = GatewayEntryOwner.current_binding(entry)
    _require(type(binding) is tuple and len(binding) == 3
             and all(a is b for a, b in zip(binding, current, strict=True))
             and binding[2][3] is activation)
    return SourceDigestContext(entry, binding, binding[0].interpreter, activation, [])


def current(context, scope):
    from hmp_startup.gateway_entry import GatewayEntryOwner, _interpreter_current

    from .presentation_startup_artifacts import _Scope

    _require(type(context) is SourceDigestContext and type(context.entry) is GatewayEntryOwner
             and type(context.binding) is tuple and len(context.binding) == 3
             and type(scope) is _Scope
             and type(context.effects) is list and scope.source_digest is context
             and scope.activation is context.activation)
    actual = GatewayEntryOwner._retained_binding(context.entry)
    _require(all(a is b for a, b in zip(context.binding, actual, strict=True))
             and context.binding[0].interpreter is context.interpreter
             and context.binding[2][3] is context.activation
             and _interpreter_current(context.interpreter) is context.interpreter)
    return context


def begin(owner, scope, expected):
    from .presentation_startup_artifacts import _MAX_FILE, _MAX_FILES, ExpectedArtifact

    _types(owner, scope, expected)
    _require(type(expected.path) is str)
    context = scope.source_digest
    if context is None or not expected.path.endswith('.py'):
        return None
    current(context, scope)
    _require(type(expected) is ExpectedArtifact and type(expected.size) is int
             and 0 <= expected.size <= _MAX_FILE
             and owner._origin is scope is owner._scope
             and len(context.effects) < _MAX_FILES
             and all(type(row) is _DigestRoot for row in context.effects)
             and not any(row.owner is owner and row.expected is expected
                         for row in context.effects))
    effect = _DigestEffect(context, owner, scope, expected, owner._count_cell, bytearray())
    root = _DigestRoot(effect, context, owner, scope, expected, effect.before, effect.buffer, [])
    context.effects.append(root)  # immutable original allocation before file effects
    return root


class _SourceRead(NamedTuple):
    root: _DigestRoot
    record: object
    index: int
    before: tuple
    result: list

    def __repr__(self):
        return '<OriginalSourceRead redacted>'


def retain_read(context, owner, scope, record, index):
    from .presentation_startup_artifacts import _ReadEffect

    current(context, scope)
    _require(type(context.effects) is list and type(record) is _ReadEffect
             and type(scope.reads) is list and type(index) is int
             and 0 <= index < len(scope.reads) and scope.reads[index] is record)
    if not context.effects:
        return None
    root = context.effects[-1]
    _require(type(root) is _DigestRoot and type(root.effect) is _DigestEffect)
    if root.effect.cleared is True:
        return None
    _require(root.owner is owner and root.scope is scope and type(root.reads) is list
             and len(root.reads) <= 65536 and record.before is owner._count_cell)
    read = _SourceRead(root, record, index, record.before, [None])
    root.reads.append(read)
    return read


def observed_read(read, count, length):
    if read is None:
        return
    _require(type(read) is _SourceRead and type(read.result) is list
             and len(read.result) == 1 and read.result[0] is None
             and type(count) is tuple and len(count) == 3 and type(count[2]) is int
             and type(length) is int and 0 <= length <= 65536)
    result = (count, length)
    read.result[0] = result  # actual result, before post-read callbacks
    return result


def capture(root):
    """Capture immediately after fixed _read returns, before any callbacks."""
    _require(type(root) is _DigestRoot and type(root.reads) is list and len(root.reads) > 0)
    read = root.reads[-1]
    _require(type(read) is _SourceRead and read.root is root and type(read.result) is list
             and len(read.result) == 1 and type(read.result[0]) is tuple)
    return read, read.result[0]


def _read_result(root, index, before, held):
    from .presentation_startup_artifacts import _ReadEffect, _Scope

    _require(type(root) is _DigestRoot and type(root.scope) is _Scope
             and type(root.reads) is list and type(index) is int and 0 <= index < len(root.reads)
             and type(root.scope.reads) is list)
    read = root.reads[index]
    _require(type(held) is tuple and len(held) == 2 and held[0] is read)
    _require(type(read) is _SourceRead and read.root is root
             and type(read.record) is _ReadEffect and type(read.index) is int
             and 0 <= read.index < len(root.scope.reads)
             and root.scope.reads[read.index] is read.record
             and read.before is before and read.record.before is before
             and type(read.result) is list and len(read.result) == 1)
    result = read.result[0]
    _require(result is held[1])
    _require(type(result) is tuple and len(result) == 2
             and type(result[0]) is tuple and len(result[0]) == 3
             and type(result[0][2]) is int and type(result[1]) is int
             and 0 <= result[1] <= 65536 and read.record.after is result[0]
             and read.record.returned is True and read.record.unknown is False
             and result[0][0] is root.owner and result[0][1] is root.scope
             and type(before) is tuple and len(before) == 3 and type(before[2]) is int
             and result[0][2] - before[2] == result[1])
    return result


def _consume(root, length, observations):
    _require(type(root) is _DigestRoot and type(root.effect) is _DigestEffect)
    _types(root.owner, root.scope, root.expected)
    effect = root.effect
    _require(type(effect.consumed) is int and effect.consumed >= 0
             and type(observations) is list and len(observations) == effect.consumed + 1
             and type(root.reads) is list and len(root.reads) == len(observations))
    before = root.before
    if effect.consumed:
        index = effect.consumed - 1
        previous = observations[index]
        _require(type(previous) is tuple and len(previous) == 2
                 and type(previous[0]) is _SourceRead)
        before = _read_result(root, index, previous[0].before, previous)[0]
    # Full original history is checked once before fact publication and at each
    # persistent seal; per-chunk acquisition checks only this held count bridge.
    result = _read_result(root, effect.consumed, before, observations[effect.consumed])
    _require(result[1] == length and root.owner._count_cell is result[0])
    effect.consumed += 1
    return result[0]


def _held(root, buffer):
    from .presentation_startup_artifacts import ExpectedArtifact, _Scope

    _require(type(root) is _DigestRoot and type(root.effect) is _DigestEffect
             and type(root.context) is SourceDigestContext and type(root.scope) is _Scope
             and type(root.expected) is ExpectedArtifact and type(root.expected.size) is int
             and type(root.context.effects) is list and type(buffer) is bytearray
             and root.buffer is buffer)
    _types(root.owner, root.scope, root.expected)
    effect = root.effect
    _require(effect.context is root.context and effect.owner is root.owner
             and effect.scope is root.scope and effect.expected is root.expected
             and effect.before is root.before and effect.buffer is buffer
             and effect.cleared is False and effect.unknown is False
             and type(effect.size) is int and len(buffer) == effect.size
             and 0 <= effect.size <= root.expected.size
             and root.owner._origin is root.scope is root.owner._scope
             and any(row is root for row in root.context.effects))
    current(root.context, root.scope)
    return effect


def append(root, buffer, chunk, observations):
    if root is None:
        return
    try:
        effect = _held(root, buffer)
        _require(type(chunk) is bytes and effect.attempted is False
                 and len(chunk) <= effect.expected.size - effect.size)
        _consume(root, len(chunk), observations)
        buffer.extend(chunk)
        effect.size += len(chunk)
        _held(root, buffer)
    finally:
        chunk = None  # do not retain source chunks in an error traceback


def finish(root, buffer, count, observations):
    if root is None:
        return b''
    effect = _held(root, buffer)
    _require(effect.attempted is False and effect.returned is False and effect.result is None
             and effect.size == effect.expected.size and effect.owner._count_cell is count
             and type(count) is tuple and len(count) == 3 and type(count[2]) is int
             and type(effect.before) is tuple and len(effect.before) == 3
             and type(effect.before[2]) is int
             and count[0] is effect.owner and count[1] is effect.scope
             and effect.before[0] is effect.owner and effect.before[1] is effect.scope
             and count[2] - effect.before[2] == effect.size)
    _require(_consume(root, 0, observations) is count)  # original EOF return allocation
    origin = effect.context.interpreter.source_hash
    effect.after = count
    effect.attempted = True  # lost acknowledgement consumes this actual attempt
    try:
        result = origin.builtin(origin.key, buffer)
        effect = _held(root, buffer)
        _require(effect.context.interpreter.source_hash is origin
                 and effect.owner._count_cell is count and effect.after is count
                 and type(result) is bytes and len(result) == 8
                 and effect.returned is False and effect.result is None)
        effect.result = result
        effect.returned = True
        return result
    except BaseException:
        effect.unknown = True
        raise SourceDigestError from None


def clear(root, buffer):
    if root is None:
        return
    # Always erase the captured original allocation, including on alias drift.
    _require(type(buffer) is bytearray)
    zeros = bytes(65536)
    for start in range(0, len(buffer), len(zeros)):
        width = min(len(zeros), len(buffer) - start)
        buffer[start:start + width] = zeros[:width]
    buffer.clear()
    _require(type(root) is _DigestRoot and root.buffer is buffer
             and type(root.effect) is _DigestEffect)
    effect = root.effect
    same = (effect.buffer is buffer and effect.context is root.context
            and effect.owner is root.owner and effect.scope is root.scope
            and effect.expected is root.expected and effect.before is root.before)
    effect.cleared = True
    if not same:
        effect.unknown = True
        raise SourceDigestError


class SourceDigestFact(NamedTuple):
    root: _DigestRoot
    observations: tuple
    source_hash: bytes
    count: tuple
    source_mtime: int

    def __repr__(self):
        return '<OriginalSourceDigestFact redacted>'


def fact(root, owner, scope, expected, result, count, observations, source_mtime):
    _types(owner, scope, expected)
    _require(type(root) is _DigestRoot)
    _require(type(observations) is list and owner._count_cell is count)
    value = SourceDigestFact(root, tuple(observations), result, count, source_mtime)
    _require(root.owner is owner and root.scope is scope and root.expected is expected)
    seal_fact(value)
    _require(owner._count_cell is count)
    return value


def seal_fact(value):
    _require(type(value) is SourceDigestFact and type(value.source_mtime) is int
             and -2 ** 64 < value.source_mtime < 2 ** 64)
    root, result, count = value.root, value.source_hash, value.count
    _require(type(root) is _DigestRoot and type(root.effect) is _DigestEffect
             and type(root.context) is SourceDigestContext and type(root.context.effects) is list
             and any(row is root for row in root.context.effects)
             and type(root.buffer) is bytearray and len(root.buffer) == 0)
    _types(root.owner, root.scope, root.expected)
    effect = root.effect
    _require(effect.context is root.context and effect.owner is root.owner
             and effect.scope is root.scope and effect.expected is root.expected
             and effect.before is root.before and effect.buffer is root.buffer
             and effect.cleared is True and effect.attempted is True
             and effect.returned is True and effect.unknown is False
             and type(result) is bytes and len(result) == 8 and effect.result is result
             and effect.after is count and type(effect.consumed) is int
             and type(value.observations) is tuple and type(root.reads) is list
             and len(root.reads) == len(value.observations) == effect.consumed
             and effect.consumed >= 1)
    before = root.before
    for index in range(effect.consumed):
        observed = _read_result(root, index, before, value.observations[index])
        _require((observed[1] == 0) is (index == effect.consumed - 1))
        before = observed[0]
    _require(before is count and root.owner._origin is root.scope is root.owner._scope)
    current(root.context, root.scope)
    return value
