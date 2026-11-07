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
