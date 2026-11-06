"""Derive credential scope from bounded original input3, never result claims.

This digest is correlation data. Native INITIAL and original job ownership remain
required independently; decoding input does not authorize any filesystem read.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .presentation_broker_codec import BrokerBinding, _binding
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError


@dataclass(frozen=True)
class InputScopeDigest:
    input_sha256: str
    scope_sha256: str


def derive_input_scope(packet: bytes, binding: BrokerBinding) -> InputScopeDigest:
    _binding(binding)
    # The decoder checks packet type, bounded framing, closed schema and native
    # policy data shape. It performs no native authority or filesystem effects.
    value = decode_input_v3(packet)
    if value["iid"] != binding.iid:
        raise FrameError("BI1_CREDENTIAL_INPUT_SCOPE_REFUSED")
    input_sha = hashlib.sha256(packet).hexdigest()
    scope = dict(v=1, iid=binding.iid, listener=binding.listener,
                 operation_id=binding.operation, profile=value["profile"],
                 kind=value["operation"], expected_avatar_sha=value["expected_avatar_sha"],
                 challenge=value["challenge"], epoch=value["epoch"],
                 deadline_ns=value["deadline_ns"], input_sha256=input_sha)
    raw = json.dumps(scope, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    return InputScopeDigest(input_sha, hashlib.sha256(raw).hexdigest())
