"""Adversarial wire tests; synthetic keys, no live role owners or host access."""

import json
import struct

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hmp_plugin.presentation_credential_codec import (
    JSON_LIMIT,
    decode_record,
    encode_record,
    payload_size,
    signing_bytes,
)
from hmp_plugin.presentation_jobs import FrameError


def hello(**updates):
    value = {
        "v": 1,
        "family": "handshake",
        "alg": "Ed25519",
        "phase": "HELLO",
        "role": "gateway",
        "direction": "g2b",
        "iid": "a" * 52,
        "listener": "1" * 32,
        "key_id": "2" * 64,
        "peer_key_id": "3" * 64,
        "generation": "4" * 64,
        "operation_id": "5" * 64,
        "work_end_ns": 123,
        "clock_domain": "6" * 64,
        "gateway_boot": "7" * 64,
        "gateway_nonce": "8" * 64,
    }
    value.update(updates)
    return value


def test_synthetic_signature_binds_every_byte_and_domain():
    key = Ed25519PrivateKey.generate()
    original = hello()
    signature = key.sign(signing_bytes(original))
    record = decode_record(encode_record(original, signature))
    key.public_key().verify(record.signature, record.signing_data)
    changed = decode_record(encode_record(hello(work_end_ns=124), signature))
    with pytest.raises(InvalidSignature):
        key.public_key().verify(changed.signature, changed.signing_data)
    with pytest.raises(InvalidSignature):
        key.public_key().verify(signature, record.signing_data.replace(b"HANDSHAKE", b"PHASE"))
    assert record.signing_data.startswith(b"HMP-BI1-CREDENTIAL-HANDSHAKE-1\0")


@pytest.mark.parametrize(
    "changes",
    [
        {"v": True},
        {"work_end_ns": True},
        {"work_end_ns": 0},
        {"work_end_ns": 2**63},
        {"role": "broker"},
        {"direction": "b2g"},
        {"extra": "ignored"},
        {"key_id": "A" * 64},
        {"family": []},
        {"phase": "STATUS"},
        {"alg": "none"},
        {"iid": "../"},
    ],
)
def test_closed_claims_refuse(changes):
    with pytest.raises(FrameError):
        encode_record(hello(**changes), b"s" * 64)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b + b" ",
        lambda b: b.replace(b'"v":1', b'"v":1,"v":1'),
        lambda b: b.replace(b'"v":1', b'"v":1.0'),
        lambda b: b.replace(b'"v":1', b'"v":NaN'),
        lambda b: b.replace(b'"alg"', b'"\\u0061lg"'),
    ],
)
def test_noncanonical_raw_json_refused(mutation):
    body = json.dumps(hello(), sort_keys=True, separators=(",", ":")).encode()
    body = mutation(body)
    raw = b"HBA1" + struct.pack(">I", len(body)) + body + b"s" * 64
    with pytest.raises(FrameError):
        decode_record(raw)


def test_prefix_limit_before_payload_and_exact_record_length():
    for size in (0, JSON_LIMIT + 1, 2**32 - 1):
        with pytest.raises(FrameError):
            payload_size(b"HBA1" + struct.pack(">I", size))
    raw = encode_record(hello(), b"s" * 64)
    for changed in (raw[:-1], raw + b"x", bytearray(raw), b"BAD!" + raw[4:]):
        with pytest.raises(FrameError):
            decode_record(changed)


def test_parser_does_not_claim_signature_verification():
    parsed = decode_record(encode_record(hello(), b"\0" * 64))
    assert type(parsed).__name__ == "UnverifiedRecord"
    assert not hasattr(parsed, "authorized")


@pytest.mark.parametrize("phase", ["BEGIN", "READY", "GO", "RESULT", "CANCEL", "TERMINAL", "ACK"])
def test_phase_closed_schema_roundtrip_and_sequence_limits(phase):
    value = hello(family="phase", phase=phase)
    del value["clock_domain"]
    del value["gateway_nonce"]
    value.update(
        broker_boot="9" * 64,
        channel="a" * 64,
        transcript_sha256="b" * 64,
        sequence=0,
        input_sha256="c" * 64,
        scope_sha256="d" * 64,
        frame_sha256="e" * 64,
        frame_length=100,
    )
    parsed = decode_record(encode_record(value, b"s" * 64))
    assert parsed.signing_data.startswith(b"HMP-BI1-CREDENTIAL-PHASE-1\0")
    for key, bad in (
        ("sequence", True),
        ("sequence", 4),
        ("frame_length", 0),
        ("frame_length", 2**63),
        ("clock_domain", "f" * 64),
    ):
        with pytest.raises(FrameError):
            encode_record(dict(value, **{key: bad}), b"s" * 64)


def test_encoder_rejects_foreign_values_without_equality_callbacks():
    class Foreign(str):
        def __eq__(self, other):
            raise AssertionError("foreign equality must not run")

        __hash__ = str.__hash__

    for name in ("alg", "direction", "phase", "family", "role", "iid"):
        with pytest.raises(FrameError):
            encode_record(hello(**{name: Foreign("g2b")}), b"s" * 64)
    value = hello()
    value[Foreign("foreign")] = "x"
    with pytest.raises(FrameError):
        encode_record(value, b"s" * 64)
