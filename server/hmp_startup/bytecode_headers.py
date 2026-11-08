"""Original selected bytecode header DATA; no unmarshalling or runtime admission."""
from __future__ import annotations

from typing import NamedTuple

from hmp_plugin.presentation_startup_artifacts import _HashedArtifact

from .gateway_continuation import GatewayContinuationOwner
from .gateway_entry import _interpreter_current


class BytecodeHeaderError(Exception):
    def __init__(self):
        super().__init__("BI1_BYTECODE_HEADER_REFUSED")


def _require(value):
    if value is not True:
        raise BytecodeHeaderError


class BytecodeHeaderData(NamedTuple):
    receipt: _HashedArtifact
    flags: int
    payload: bytes

    def __repr__(self):
        return "<OriginalSelectedBytecodeHeader DATA not-admission redacted>"


def selected_bytecode_headers(continuation):
    """Classify only original selected headers; never infer source equivalence."""
    _require(type(continuation) is GatewayContinuationOwner)
    root = GatewayContinuationOwner.current_binding(continuation)
    source = root[2]
    interpreter = source.entry_binding[0].interpreter
    _require(_interpreter_current(interpreter) is interpreter)
    plan = source.inputs.runtime_plan
    receipts = (*plan.prior, *source.snapshot_fact[3][2])
    result = []
    for expected in plan.all_files:
        if not expected.path.endswith(".pyc"):
            continue
        matching = tuple(row for row in receipts
                         if type(row) is _HashedArtifact and row.expected is expected)
        _require(len(matching) == 1)
        receipt = matching[0]
        header = receipt.bytecode_header
        _require(type(header) is bytes and len(header) == min(16, expected.size)
                 and len(header) == 16 and header[:4] == interpreter.bytecode_magic)
        flags = int.from_bytes(header[4:8], "little")
        _require(flags in (0, 1, 3))
        result.append(BytecodeHeaderData(receipt, flags, header[8:16]))
    _require(GatewayContinuationOwner.current_binding(continuation) is root
             and _interpreter_current(interpreter) is interpreter)
    return tuple(result)


class SourceHashData(NamedTuple):
    receipt: _HashedArtifact
    fact: object

    def __repr__(self):
        return '<OriginalSourceHashData not-admission redacted>'


def selected_source_hashes(continuation):
    """Join all original source receipts; never infer cache equivalence."""
    from hmp_plugin.presentation_source_digest import (
        SourceDigestContext,
        SourceDigestFact,
        seal_fact,
    )

    _require(type(continuation) is GatewayContinuationOwner)
    root = GatewayContinuationOwner.current_binding(continuation)
    source = root[2]
    interpreter = source.entry_binding[0].interpreter
    context = source.io_scope.source_digest
    _require(type(context) is SourceDigestContext
             and source.inputs.plugin_binding[0].source_digest is context
             and context.entry is source.entry and context.interpreter is interpreter
             and type(context.binding) is tuple and len(context.binding) == 3
             and all(a is b for a, b in zip(context.binding, source.entry_binding, strict=True)))
    plan = source.inputs.runtime_plan
    receipts = (*plan.prior, *source.snapshot_fact[3][2])
    result = []
    expected_sources = tuple(row for row in plan.all_files if row.path.endswith('.py'))
    for expected in expected_sources:
        matching = tuple(row for row in receipts
                         if type(row) is _HashedArtifact and row.expected is expected)
        _require(len(matching) == 1)
        receipt = matching[0]
        fact = receipt.source_digest
        _require(type(fact) is SourceDigestFact and seal_fact(fact) is fact
                 and fact.root.context is context
                 and fact.root.owner is receipt.owner and fact.root.scope is receipt.scope
                 and fact.root.expected is expected and fact.source_hash is receipt.source_hash
                 and fact.source_mtime is receipt.source_mtime)
        result.append(SourceHashData(receipt, fact))
    held = tuple(result)
    _require(GatewayContinuationOwner.current_binding(continuation) is root
             and source.io_scope.source_digest is context
             and source.inputs.plugin_binding[0].source_digest is context
             and _interpreter_current(interpreter) is interpreter)
    for expected, row in zip(expected_sources, held, strict=True):
        _require(row.receipt.expected is expected and row.receipt.source_digest is row.fact
                 and row.fact.root.context is context and row.fact.root.owner is row.receipt.owner
                 and row.fact.root.scope is row.receipt.scope and row.fact.root.expected is expected
                 and row.fact.source_hash is row.receipt.source_hash
                 and row.fact.source_mtime is row.receipt.source_mtime
                 and seal_fact(row.fact) is row.fact)
    return held
