"""Synthetic signed commitments cannot excuse changed frames or context."""

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from hmp_plugin.presentation_broker_codec import BrokerBinding, encode_frame
from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_phase import (
    check_commitment,
    check_committed_header,
    check_complete_frame,
)
from hmp_plugin.presentation_jobs import FrameError


def fixture(phase="RESULT", body=b"data", sequence=1):
    sender, receiver = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()

    def public(key):
        return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    sp, rp = public(sender), public(receiver)
    binding = BrokerBinding("a" * 52, "1" * 32, "2" * 64, "3" * 64, "4" * 64)
    frame = encode_frame(binding, phase, sequence, body, version=2)
    role = "gateway" if phase in ("BEGIN", "GO", "ACK", "CANCEL") else "broker"
    expected = {
        "phase": phase,
        "role": role,
        "direction": "g2b" if role == "gateway" else "b2g",
        "iid": binding.iid,
        "listener": binding.listener,
        "generation": "5" * 64,
        "gateway_boot": "6" * 64,
        "broker_boot": "7" * 64,
        "channel": binding.channel,
        "transcript_sha256": "8" * 64,
        "operation_id": binding.operation,
        "sequence": sequence,
        "input_sha256": "9" * 64,
        "scope_sha256": "a" * 64,
        "work_end_ns": 100,
    }
    value = dict(
        expected,
        v=1,
        family="phase",
        alg="Ed25519",
        key_id=hashlib.sha256(sp).hexdigest(),
        peer_key_id=hashlib.sha256(rp).hexdigest(),
        frame_sha256=hashlib.sha256(frame).hexdigest(),
        frame_length=len(frame),
    )

    def sign(updates=None):
        claim = dict(value, **(updates or {}))
        return encode_record(claim, sender.sign(signing_bytes(claim)))

    return binding, frame, expected, sp, rp, sign


def checked(data, updates=None, expected_updates=None):
    _binding, _frame, expected, sp, rp, sign = data
    claim = check_commitment(
        sign(updates),
        sender_public=sp,
        receiver_public=rp,
        expected=dict(expected, **(expected_updates or {})),
    )
    return claim


@pytest.mark.parametrize(
    "phase,body",
    [
        ("BEGIN", b"data"),
        ("READY", b""),
        ("GO", b""),
        ("RESULT", b"data"),
        ("CANCEL", b"x" * 16),
        ("TERMINAL", b"x"),
        ("ACK", b"x" * 32),
    ],
)
def test_each_phase_binds_header_and_entire_body(phase, body):
    data = fixture(phase, body)
    commitment = checked(data)
    header = check_complete_frame(commitment, data[1], binding=data[0])
    assert header.kind == phase and header.version == 2
    assert not hasattr(commitment, "authorized")


def test_signed_wrong_digest_or_length_cannot_admit_body():
    data = fixture()
    for updates in ({"frame_sha256": "f" * 64}, {"frame_length": len(data[1]) + 1}):
        commitment = checked(data, updates)
        with pytest.raises(FrameError):
            check_complete_frame(commitment, data[1], binding=data[0])
    commitment = checked(data)
    for frame in (data[1][:-1] + b"!", data[1] + b"!", data[1][:-1]):
        with pytest.raises(FrameError):
            check_complete_frame(commitment, frame, binding=data[0])


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_sha256", "b" * 64),
        ("scope_sha256", "b" * 64),
        ("operation_id", "b" * 64),
        ("gateway_boot", "b" * 64),
        ("sequence", 2),
        ("work_end_ns", 101),
    ],
)
def test_valid_signature_cannot_rebind_original_context(field, value):
    with pytest.raises(FrameError):
        checked(fixture(), {field: value})


def test_signed_header_kind_mismatch_and_v1_downgrade_refused_before_body():
    data = fixture("GO", b"")
    commitment = checked(data)
    for frame in (
        encode_frame(data[0], "READY", 1, version=2),
        encode_frame(data[0], "GO", 1, version=1),
    ):
        with pytest.raises(FrameError):
            check_committed_header(commitment, frame, binding=data[0])


def test_signature_and_receiver_pin_are_checked():
    data = fixture()
    _binding, _frame, expected, sp, rp, sign = data
    raw = sign()
    with pytest.raises(FrameError):
        check_commitment(
            raw[:-1] + bytes([raw[-1] ^ 1]), sender_public=sp, receiver_public=rp, expected=expected
        )
    with pytest.raises(FrameError):
        check_commitment(raw, sender_public=sp, receiver_public=b"z" * 32, expected=expected)
