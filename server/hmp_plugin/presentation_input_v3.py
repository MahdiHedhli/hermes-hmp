"""Closed worker input3 with conserved parent work; no legacy fallback/authority."""

from __future__ import annotations

from .presentation_budget import PresentationBudgetError, PresentationWorkLedger
from .presentation_input_v2 import _KEYS as _V2_KEYS
from .presentation_input_v2 import validate_input_v2
from .presentation_jobs import INPUT_LIMIT, FrameError, _envelope, _one_frame

_KEYS = _V2_KEYS | {"parent_work_counts"}


def validate_input_v3(value: object) -> dict[str, object]:
    if (
        type(value) is not dict
        or value.keys() != _KEYS
        or type(value.get("schema")) is not int
        or value["schema"] != 3
    ):
        raise FrameError("BI1_INPUT_V3_REFUSED")
    base = {key: value[key] for key in _V2_KEYS}
    base["schema"] = 2
    validate_input_v2(base)
    try:
        PresentationWorkLedger.validate_parent_counts(value["home"], value["parent_work_counts"])
    except PresentationBudgetError:
        raise FrameError("BI1_INPUT_V3_REFUSED") from None
    return value


def encode_input_v3(value: dict[str, object]) -> bytes:
    return _envelope(validate_input_v3(value), INPUT_LIMIT)


def decode_input_v3(data: bytes) -> dict[str, object]:
    return validate_input_v3(_one_frame(data, INPUT_LIMIT))
