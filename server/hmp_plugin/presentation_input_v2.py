"""Closed private worker schema2: parent-qualified policy and projection context.

No schema1 fallback, filesystem lookup or authority is provided by this codec.
"""

from __future__ import annotations

from . import wire
from .presentation import _name
from .presentation_jobs import (
    _INPUT_KEYS,
    INPUT_LIMIT,
    FrameError,
    _envelope,
    _number,
    _one_frame,
    _utf8,
    validate_input,
)

_KEYS = _INPUT_KEYS | {"directory_policy", "iid", "canonical_fallback", "observed_at"}


def prefixes(home: str) -> tuple[str, ...]:
    parts = home[1:].split("/")
    return ("/", *("/" + "/".join(parts[:i]) for i in range(1, len(parts) + 1)))


def validate_input_v2(value: object) -> dict[str, object]:
    if (
        type(value) is not dict
        or value.keys() != _KEYS
        or type(value.get("schema")) is not int
        or value["schema"] != 2
    ):
        raise FrameError("BI1_INPUT_V2_REFUSED")
    row = value
    base = {key: row[key] for key in _INPUT_KEYS}
    base["schema"] = 1
    validate_input(base)
    _number(row["uid"], 1, (1 << 31) - 1)
    expected = (
        row["root"] if row["profile"] == "default" else row["root"] + "/profiles/" + row["profile"]
    )
    if row["home"] != expected:
        raise FrameError("BI1_INPUT_V2_REFUSED")
    chain = prefixes(row["home"])
    policy = row["directory_policy"]
    if len(chain) > 32 or type(policy) is not list or len(policy) != len(chain):
        raise FrameError("BI1_INPUT_V2_REFUSED")
    for path, rule in zip(chain, policy, strict=True):
        if type(rule) is not list or len(rule) != 3:
            raise FrameError("BI1_INPUT_V2_REFUSED")
        uid = _number(rule[0], 0, (1 << 31) - 1)
        gid = _number(rule[1], 0, (1 << 31) - 1)
        mode = _number(rule[2], 0, 0o777)
        if uid not in (0, row["uid"]) or mode not in (0o700, 0o750, 0o755):
            raise FrameError("BI1_INPUT_V2_REFUSED")
        if path == "/" and (uid != 0 or gid != 0):
            raise FrameError("BI1_INPUT_V2_REFUSED")
        if path in (row["root"], row["home"]) and (uid != row["uid"] or gid != row["gid"]):
            raise FrameError("BI1_INPUT_V2_REFUSED")
    try:
        wire.require_iid(row["iid"])
    except wire.WireError:
        raise FrameError("BI1_INPUT_V2_REFUSED") from None
    _utf8(row["canonical_fallback"], 256)
    if _name(row["canonical_fallback"]) != row["canonical_fallback"]:
        raise FrameError("BI1_INPUT_V2_REFUSED")
    _number(row["observed_at"], 0, (1 << 53) - 1)
    return row


def encode_input_v2(row: dict[str, object]) -> bytes:
    return _envelope(validate_input_v2(row), INPUT_LIMIT)


def decode_input_v2(data: bytes) -> dict[str, object]:
    return validate_input_v2(_one_frame(data, INPUT_LIMIT))
