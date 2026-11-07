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
    BrokerBinding,
    BrokerHeader,
    decode_header,
    header_size,
)
from .presentation_credential_codec import JSON_LIMIT, decode_record
from .presentation_jobs import FrameError

_EXPECTED = frozenset(
    [
        "phase",
        "role",
        "direction",
        "iid",
        "listener",
        "generation",
        "gateway_boot",
        "broker_boot",
        "channel",
        "transcript_sha256",
        "operation_id",
        "sequence",
        "input_sha256",
        "scope_sha256",
        "work_end_ns",
    ]
)


def _refuse():
    raise FrameError("BI1_CREDENTIAL_PHASE_REFUSED")


@dataclass(frozen=True)
class ConsistentCommitment:
    """Immutable checked data, not an operation permit or transfer receipt."""

    canonical_json: bytes
    frame_sha256: str
    frame_length: int


def check_commitment(
    raw: bytes, *, sender_public: bytes, receiver_public: bytes, expected: dict
) -> ConsistentCommitment:
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
    if (
        value["key_id"] != hashlib.sha256(sender_public).hexdigest()
        or value["peer_key_id"] != hashlib.sha256(receiver_public).hexdigest()
    ):
        _refuse()
    try:
        Ed25519PublicKey.from_public_bytes(sender_public).verify(
            parsed.signature, parsed.signing_data
        )
    except (InvalidSignature, ValueError):
        _refuse()
    return ConsistentCommitment(parsed.canonical_json, value["frame_sha256"], value["frame_length"])


def check_broker_cleanup_commitment(
    raw: bytes, *, sender_public: bytes, receiver_public: bytes, expected_context: dict
) -> ConsistentCommitment:
    """Authenticate RESULT/1 or TERMINAL/0..2 at a retained sequence, DATA only.

    This is not a transition permit: the original cursor owner must separately
    prove which transitions are currently allowed, and a direct terminal must
    still carry a qualified ABORTED claim. Never retry a refused record using a
    different parser. No body, cursor advancement or lifecycle fact is produced.
    """
    context_keys = _EXPECTED - {"phase"}
    if (
        type(expected_context) is not dict
        or any(type(key) is not str for key in expected_context)
        or expected_context.keys() != context_keys
        or any(type(value) is not (int if key in ("sequence", "work_end_ns") else str)
               for key, value in expected_context.items())
        or expected_context["role"] != "broker"
        or expected_context["direction"] != "b2g"
        or expected_context["sequence"] not in (0, 1, 2)
    ):
        _refuse()
    # The closed codec bounds and validates the untrusted discriminator first.
    # Its value selects only a fixed expectation, never authority or fallback.
    parsed = decode_record(raw)
    value = json.loads(parsed.canonical_json)
    if value["family"] != "phase" or value["phase"] not in ("RESULT", "TERMINAL"):
        _refuse()
    phase = value["phase"]
    if phase == "RESULT" and expected_context["sequence"] != 1:
        _refuse()
    return check_commitment(
        raw, sender_public=sender_public, receiver_public=receiver_public,
        expected=dict(expected_context, phase=phase),
    )


def check_committed_header(
    commitment: ConsistentCommitment, header: bytes, *, binding: BrokerBinding
) -> BrokerHeader:
    """Bounded header check before body allocation; not completed body validation.

    Reparse the retained canonical claim so constructing a data object cannot
    skip the closed codec. This still does not create runtime owner authority.
    """
    if type(commitment) is not ConsistentCommitment:
        _refuse()
    # This object is data, not an unforgeable fact. The original receiver must
    # retain the exact result of check_commitment; no caller object is admission.
    if (
        type(commitment.canonical_json) is not bytes
        or not 1 <= len(commitment.canonical_json) <= JSON_LIMIT
    ):
        _refuse()
    parsed = decode_record(
        b"HBA1"
        + len(commitment.canonical_json).to_bytes(4, "big")
        + commitment.canonical_json
        + b"\0" * 64
    )
    value = json.loads(parsed.canonical_json)
    if (
        value["family"] != "phase"
        or type(commitment.frame_length) is not int
        or type(commitment.frame_sha256) is not str
        or value["frame_length"] != commitment.frame_length
        or value["frame_sha256"] != commitment.frame_sha256
    ):
        _refuse()
    decoded = decode_header(header, expected=binding, expected_version=2)
    if (
        decoded.kind != value["phase"]
        or decoded.sequence != value["sequence"]
        or binding.iid != value["iid"]
        or binding.listener != value["listener"]
        or binding.channel != value["channel"]
        or binding.operation != value["operation_id"]
        or len(header) + decoded.body_length != commitment.frame_length
    ):
        _refuse()
    return decoded


def check_complete_frame(
    commitment: ConsistentCommitment, frame: bytes, *, binding: BrokerBinding
) -> BrokerHeader:
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


_BEGIN_CONTEXT = _EXPECTED - {"input_sha256", "scope_sha256"}


@dataclass(frozen=True)
class ConsistentBeginInput:
    """Verified data relationship, not native input adoption or authorization."""

    commitment: ConsistentCommitment
    packet: bytes


def stage_begin_commitment(
    raw: bytes, *, sender_public: bytes, receiver_public: bytes, expected_context: dict
) -> ConsistentCommitment:
    """Check fixed BEGIN context/signature before reading its bounded body.

    The two signed input hashes remain unadopted claims. The original broker
    receiver must retain the actual checked record/cursor and complete the
    independent input check before any registry/resource/worker effects.
    """
    if type(expected_context) is not dict:
        _refuse()
    if any(type(key) is not str for key in expected_context):
        _refuse()
    if expected_context.keys() != _BEGIN_CONTEXT:
        _refuse()
    for name, item in expected_context.items():
        if type(item) is not (int if name in ("sequence", "work_end_ns") else str):
            _refuse()
    if (
        expected_context["phase"] != "BEGIN"
        or expected_context["role"] != "gateway"
        or expected_context["direction"] != "g2b"
        or expected_context["sequence"] != 0
    ):
        _refuse()
    parsed = decode_record(raw)
    value = json.loads(parsed.canonical_json)
    if value["family"] != "phase" or value["phase"] != "BEGIN":
        _refuse()
    expected = dict(
        expected_context, input_sha256=value["input_sha256"], scope_sha256=value["scope_sha256"]
    )
    return check_commitment(
        raw, sender_public=sender_public, receiver_public=receiver_public, expected=expected
    )


def check_begin_frame(
    raw: bytes,
    frame: bytes,
    *,
    sender_public: bytes,
    receiver_public: bytes,
    expected_context: dict,
    binding: BrokerBinding,
) -> ConsistentBeginInput:
    """Bounded complete BEGIN/input3 consistency; no native or registry effects.

    Reverify the original record rather than trusting a caller-constructed staged
    data object. This whole-buffer BEGIN helper does not replace the original
    receiver's staged header admission, read cursor or actual transfer evidence.
    """
    from .presentation_credential_scope import derive_input_scope
    from .presentation_input_v3 import decode_input_v3

    commitment = stage_begin_commitment(
        raw,
        sender_public=sender_public,
        receiver_public=receiver_public,
        expected_context=expected_context,
    )
    check_complete_frame(commitment, frame, binding=binding)
    end = 8 + header_size(frame[:8])
    packet = frame[end:]
    row = decode_input_v3(packet)
    scope = derive_input_scope(packet, binding)
    value = json.loads(commitment.canonical_json)
    if (
        row["deadline_ns"] != expected_context["work_end_ns"]
        or scope.input_sha256 != value["input_sha256"]
        or scope.scope_sha256 != value["scope_sha256"]
    ):
        _refuse()
    return ConsistentBeginInput(commitment, packet)
