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
