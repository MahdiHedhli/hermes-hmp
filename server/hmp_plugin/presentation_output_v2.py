"""Closed result2 accounting codec; claims are never authority or custody proof."""

from __future__ import annotations

import hashlib
import struct

from .presentation_budget import PresentationBudgetError, PresentationWorkLedger
from .presentation_jobs import (
    _HEADER_KEYS,
    _LEDGER_KEYS,
    HEADER_LIMIT,
    OUTPUT_LIMIT,
    FrameError,
    _digest,
    _envelope,
    _json,
    _number,
    validate_header,
)

_KEYS = _LEDGER_KEYS | {"hash_bytes", "yaml_tokens"}


def validate_header_v2(value: object) -> dict[str, object]:
    if (
        type(value) is not dict
        or value.keys() != _HEADER_KEYS
        or type(value.get("schema")) is not int
        or value["schema"] != 2
    ):
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    ledger = value["ledger"]
    if type(ledger) is not dict or ledger.keys() != _KEYS:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    base = dict(value)
    base["schema"] = 1
    base["ledger"] = {key: ledger[key] for key in _LEDGER_KEYS}
    validate_header(base)
    for key in ("hash_bytes", "yaml_tokens"):
        if (
            type(ledger[key]) is not int
            or not 0 <= ledger[key] <= PresentationWorkLedger._LIMITS[key]
        ):
            raise FrameError("BI1_OUTPUT_V2_REFUSED")
    return value


def compare_parent_totals(
    header: object, *, parent_home: str, parent_counts: dict[str, int]
) -> dict[str, int]:
    row = validate_header_v2(header)
    try:
        parent = PresentationWorkLedger.validate_parent_counts(parent_home, parent_counts)
    except PresentationBudgetError:
        raise FrameError("BI1_OUTPUT_PARENT_REFUSED") from None
    totals = {
        ("read_bytes" if key == "body_bytes" else key): value
        for key, value in row["ledger"].items()
    }
    if any(totals[key] < parent[key] for key in parent):
        raise FrameError("BI1_OUTPUT_PARENT_REFUSED")
    return totals


def encode_output_v2(header: dict[str, object], avatar: bytes) -> bytes:
    row = validate_header_v2(header)
    if type(avatar) is not bytes or len(avatar) != row["avatar_length"]:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    if avatar and hashlib.sha256(avatar).hexdigest() != row["avatar_sha"]:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    wire = _envelope(row, HEADER_LIMIT) + avatar
    if len(wire) > OUTPUT_LIMIT:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    return wire


def decode_output_v2(wire: bytes, challenge: str, epoch: int) -> tuple[dict[str, object], bytes]:
    _digest(challenge)
    _number(epoch, 1, (1 << 63) - 1)
    if type(wire) is not bytes or not 4 <= len(wire) <= OUTPUT_LIMIT:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    length = struct.unpack(">I", wire[:4])[0]
    if length > HEADER_LIMIT or len(wire) < 4 + length:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    row = validate_header_v2(_json(wire[4 : 4 + length], HEADER_LIMIT))
    avatar = wire[4 + length :]
    if row["challenge"] != challenge or row["epoch"] != epoch:
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    if len(avatar) != row["avatar_length"] or (
        avatar and hashlib.sha256(avatar).hexdigest() != row["avatar_sha"]
    ):
        raise FrameError("BI1_OUTPUT_V2_REFUSED")
    return row, avatar


class BoundedResultBufferV2:
    """One version2 result only; bound declared length before body accumulation."""

    def __init__(self):
        self._buffer = bytearray()
        self._header_size: int | None = None
        self._body_size: int | None = None
        self._done = False

    def feed(self, chunk: bytes) -> None:
        if self._done or type(chunk) is not bytes or not 0 < len(chunk) <= 65536:
            self._done = True
            raise FrameError("BI1_OUTPUT_V2_REFUSED")
        if len(self._buffer) + len(chunk) > OUTPUT_LIMIT:
            self._done = True
            raise FrameError("BI1_OUTPUT_V2_REFUSED")
        try:
            self._buffer.extend(chunk)
            if len(self._buffer) >= 4 and self._header_size is None:
                self._header_size = struct.unpack(">I", self._buffer[:4])[0]
                if self._header_size > HEADER_LIMIT:
                    raise FrameError("BI1_OUTPUT_V2_REFUSED")
            if self._header_size is not None and len(self._buffer) >= 4 + self._header_size:
                if self._body_size is None:
                    row = validate_header_v2(
                        _json(bytes(self._buffer[4 : 4 + self._header_size]), HEADER_LIMIT)
                    )
                    self._body_size = row["avatar_length"]
                if len(self._buffer) > 4 + self._header_size + self._body_size:
                    raise FrameError("BI1_OUTPUT_V2_REFUSED")
        except BaseException:
            self._done = True
            raise

    def finish(self, challenge: str, epoch: int) -> tuple[dict[str, object], bytes]:
        if self._done:
            raise FrameError("BI1_OUTPUT_V2_REFUSED")
        self._done = True
        return decode_output_v2(bytes(self._buffer), challenge, epoch)

    def wipe(self) -> None:
        self._buffer[:] = b"\x00" * len(self._buffer)
        self._buffer.clear()
        self._done = True


def compare_parent_snapshot(
    header: object, *, snapshot: object, parent_home: str
) -> dict[str, int]:
    from .presentation_parent_policy import ParentPolicySnapshot

    if type(snapshot) is not ParentPolicySnapshot:
        raise FrameError("BI1_OUTPUT_PARENT_REFUSED")
    totals = compare_parent_totals(
        header, parent_home=parent_home, parent_counts=dict(snapshot.counts)
    )
    row = validate_header_v2(header)
    expected = snapshot.chain
    if type(expected) is not tuple or not expected or len(expected) != snapshot.counts["opens"]:
        raise FrameError("BI1_OUTPUT_PARENT_REFUSED")
    for item in expected:
        if (
            type(item) is not tuple
            or len(item) != 9
            or any(type(v) is not int or not 0 <= v < 1 << 63 for v in item)
        ):
            raise FrameError("BI1_OUTPUT_PARENT_REFUSED")
    if tuple(tuple(item) for item in row["chain"]) != expected:
        raise FrameError("BI1_OUTPUT_PARENT_REFUSED")
    return totals
