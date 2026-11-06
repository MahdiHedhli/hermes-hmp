"""Signed phase/body consistency, with no native or lifecycle authority.

The original role owner supplies current pins and its retained expected phase,
sequence and context. BEGIN expectations can be staged unadopted metadata until
input3 is fully decoded and its independent scope is compared. This module never
adopts input, renews a budget, writes, replays, signs or releases custody.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .presentation_broker_codec import (
    BrokerBinding, BrokerHeader, decode_header, header_size,
)
from .presentation_credential_codec import JSON_LIMIT, decode_record
from .presentation_jobs import FrameError

_EXPECTED = frozenset("phase role direction iid listener generation gateway_boot broker_boot channel transcript_sha256 operation_id sequence input_sha256 scope_sha256 work_end_ns".split())


def _refuse():
    raise FrameError("BI1_CREDENTIAL_PHASE_REFUSED")


@dataclass(frozen=True)
class ConsistentCommitment:
    """Immutable checked data, not an operation permit or transfer receipt."""
    canonical_json: bytes
    frame_sha256: str
    frame_length: int


def check_commitment(raw: bytes, *, sender_public: bytes, receiver_public: bytes,
                     expected: dict) -> ConsistentCommitment:
    if type(expected) is not dict or any(type(key) is not str for key in expected):
        _refuse()
    if expected.keys() != _EXPECTED:
        _refuse()
    for name, item in expected.items():
        if type(item) is not (int if name in ("sequence", "work_end_ns") else str):
            _refuse()
    if any(type(key) is not bytes or len(key) != 32 for key in (sender_public, receiver_public)):
        _refuse()
    if sender_public == receiver_public:
        _refuse()
    parsed = decode_record(raw)
    value = json.loads(parsed.canonical_json)
    if value["family"] != "phase" or any(value[key] != item for key, item in expected.items()):
        _refuse()
    if (value["key_id"] != hashlib.sha256(sender_public).hexdigest()
        or value["peer_key_id"] != hashlib.sha256(receiver_public).hexdigest()):
        _refuse()
    try:
        Ed25519PublicKey.from_public_bytes(sender_public).verify(parsed.signature, parsed.signing_data)
    except (InvalidSignature, ValueError):
        _refuse()
    return ConsistentCommitment(parsed.canonical_json, value["frame_sha256"], value["frame_length"])


def check_committed_header(commitment: ConsistentCommitment, header: bytes, *,
                           binding: BrokerBinding) -> BrokerHeader:
    """Bounded header check before body allocation; not completed body validation.

    Reparse the retained canonical claim so constructing a data object cannot
    skip the closed codec. This still does not create runtime owner authority.
    """
    if type(commitment) is not ConsistentCommitment:
        _refuse()
    # This object is data, not an unforgeable fact. The original receiver must
    # retain the exact result of check_commitment; no caller object is admission.
    if (type(commitment.canonical_json) is not bytes
        or not 1 <= len(commitment.canonical_json) <= JSON_LIMIT):
        _refuse()
    parsed = decode_record(b"HBA1" + len(commitment.canonical_json).to_bytes(4, "big")
                           + commitment.canonical_json + b"\0" * 64)
    value = json.loads(parsed.canonical_json)
    if (value["family"] != "phase" or type(commitment.frame_length) is not int
        or type(commitment.frame_sha256) is not str
        or value["frame_length"] != commitment.frame_length
        or value["frame_sha256"] != commitment.frame_sha256):
        _refuse()
    decoded = decode_header(header, expected=binding, expected_version=2)
    if (decoded.kind != value["phase"] or decoded.sequence != value["sequence"]
        or binding.iid != value["iid"] or binding.listener != value["listener"]
        or binding.channel != value["channel"] or binding.operation != value["operation_id"]
        or len(header) + decoded.body_length != commitment.frame_length):
        _refuse()
    return decoded


def check_complete_frame(commitment: ConsistentCommitment, frame: bytes, *,
                         binding: BrokerBinding) -> BrokerHeader:
    """Whole-buffer check for fixtures; streaming owner must hash its own cursor."""
    if type(frame) is not bytes or type(commitment) is not ConsistentCommitment:
        _refuse()
    if type(commitment.frame_length) is not int or len(frame) != commitment.frame_length:
        _refuse()
    end = 8 + header_size(frame[:8])
    header = check_committed_header(commitment, frame[:end], binding=binding)
    if hashlib.sha256(frame).hexdigest() != commitment.frame_sha256:
        _refuse()
    return header
