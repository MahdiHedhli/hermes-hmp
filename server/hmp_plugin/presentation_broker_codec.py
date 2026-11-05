"""Bounded broker frame correlation, not peer authentication or custody proof.

The private service spine composes bounded reads and lifecycle sequencing.
Production startup/runtime, original native authority and terminal remote custody
remain unqualified; frame correlation alone cannot activate a capability.
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass

from . import wire
from .presentation_jobs import INPUT_LIMIT, OUTPUT_LIMIT, FrameError

MAGIC = b"HBR1"
HEADER_LIMIT = 1024
FRAME_LIMIT = 8 + HEADER_LIMIT + OUTPUT_LIMIT
_KINDS = frozenset(
    {"BEGIN", "READY", "GO", "CANCEL", "CLOSED", "ACK", "STATUS", "RESULT", "PENDING", "UNKNOWN"}
)
_KEYS = frozenset(
    {"v", "kind", "iid", "listener", "broker", "channel", "operation", "sequence", "body_length"}
)
_HEX32 = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def _fail() -> None:
    raise FrameError("BI1_BROKER_FRAME_REFUSED")


@dataclass(frozen=True)
class BrokerBinding:
    """Correlation only. Values cannot grant or assert native authorization."""

    iid: str
    listener: str
    broker: str
    channel: str
    operation: str

    def __post_init__(self) -> None:
        if type(self.iid) is not str:
            _fail()
        try:
            wire.require_iid(self.iid)
        except wire.WireError:
            _fail()
        if type(self.listener) is not str or _HEX32.fullmatch(self.listener) is None:
            _fail()
        for value in (self.broker, self.channel, self.operation):
            if type(value) is not str or _HEX64.fullmatch(value) is None:
                _fail()


@dataclass(frozen=True)
class BrokerHeader:
    binding: BrokerBinding
    kind: str
    sequence: int
    body_length: int
    version: int = 1


@dataclass(frozen=True)
class BrokerFrame:
    header: BrokerHeader
    body: bytes


def _binding(value: BrokerBinding) -> None:
    if type(value) is not BrokerBinding:
        _fail()
    value.__post_init__()


def _version(value: int) -> None:
    if type(value) is not int or value not in (1, 2):
        _fail()


def _shape(kind: str, sequence: int, body_length: int, version: int) -> None:
    _version(version)
    if (
        type(kind) is not str
        or kind not in _KINDS
        or type(sequence) is not int
        or not 0 <= sequence <= 3
        or type(body_length) is not int
    ):
        _fail()
    if kind == "BEGIN":
        valid = 4 <= body_length <= INPUT_LIMIT + 4
    elif kind == "CANCEL" and version == 2:
        valid = body_length == 16
    elif kind == "RESULT":
        valid = 4 <= body_length <= OUTPUT_LIMIT
    else:
        valid = body_length == 0
    if not valid:
        _fail()


def _row(header: BrokerHeader) -> dict[str, object]:
    if type(header) is not BrokerHeader:
        _fail()
    _binding(header.binding)
    _shape(header.kind, header.sequence, header.body_length, header.version)
    binding = header.binding
    return {
        "v": header.version,
        "kind": header.kind,
        "iid": binding.iid,
        "listener": binding.listener,
        "broker": binding.broker,
        "channel": binding.channel,
        "operation": binding.operation,
        "sequence": header.sequence,
        "body_length": header.body_length,
    }


def _canonical(row: dict[str, object]) -> bytes:
    return json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def encode_frame(
    binding: BrokerBinding, kind: str, sequence: int, body: bytes = b"", *, version: int = 1
) -> bytes:
    if type(body) is not bytes:
        _fail()
    header = BrokerHeader(binding, kind, sequence, len(body), version)
    raw = _canonical(_row(header))
    if not 1 <= len(raw) <= HEADER_LIMIT:
        _fail()
    return MAGIC + struct.pack(">I", len(raw)) + raw + body


def header_size(prefix: bytes) -> int:
    """Validate the eight-byte prefix before a transport reads any header/body."""
    if type(prefix) is not bytes or len(prefix) != 8 or prefix[:4] != MAGIC:
        _fail()
    length = struct.unpack(">I", prefix[4:])[0]
    if not 1 <= length <= HEADER_LIMIT:
        _fail()
    return length


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    row: dict[str, object] = {}
    for key, value in pairs:
        if key in row:
            _fail()
        row[key] = value
    return row


def _constant(value: str) -> None:
    _fail()


def decode_header(
    data: bytes, *, expected: BrokerBinding, expected_version: int = 1
) -> BrokerHeader:
    """Match one closed canonical header to exact operation correlation."""
    return _decode_header(
        data, expected=expected, scope_only=False, expected_version=expected_version
    )


def decode_scope_header(
    data: bytes, *, expected_scope: BrokerBinding, expected_version: int = 1
) -> BrokerHeader:
    """Server header only: match enrolled iid/listener/boot before body receive.

    Channel/operation remain untrusted correlation, subject to grammar and the
    one shared registry's replay/capacity admission. No enrollment from frames.
    """
    return _decode_header(
        data, expected=expected_scope, scope_only=True, expected_version=expected_version
    )


def _decode_header(
    data: bytes, *, expected: BrokerBinding, scope_only: bool, expected_version: int
) -> BrokerHeader:
    """Validate correlation and body bounds BEFORE a transport receives that body.

    Requires exactly prefix+header, not body bytes. It does not authenticate a
    peer, validate input3/output2, or establish correct lifecycle sequencing.
    """
    _binding(expected)
    _version(expected_version)
    if type(data) is not bytes or len(data) < 8:
        _fail()
    length = header_size(data[:8])
    if len(data) != 8 + length:
        _fail()
    raw = data[8:]
    try:
        row = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise FrameError("BI1_BROKER_FRAME_REFUSED") from None
    if (
        type(row) is not dict or row.keys() != _KEYS
        or type(row["v"]) is not int or row["v"] != expected_version
    ):
        _fail()
    binding = BrokerBinding(
        row["iid"], row["listener"], row["broker"], row["channel"], row["operation"]
    )
    if scope_only:
        if (binding.iid, binding.listener, binding.broker) != (
            expected.iid, expected.listener, expected.broker
        ):
            _fail()
    elif binding != expected:
        _fail()
    header = BrokerHeader(binding, row["kind"], row["sequence"], row["body_length"], row["v"])
    if raw != _canonical(_row(header)):
        _fail()
    return header


def decode_frame(
    data: bytes, *, expected: BrokerBinding, expected_version: int = 1
) -> BrokerFrame:
    """Whole-buffer fixture codec; no streaming/allocation-bound claim."""
    if type(data) is not bytes or not 8 <= len(data) <= FRAME_LIMIT:
        _fail()
    length = header_size(data[:8])
    end = 8 + length
    header = decode_header(data[:end], expected=expected, expected_version=expected_version)
    if len(data) != end + header.body_length:
        _fail()
    return BrokerFrame(header, data[end:])
