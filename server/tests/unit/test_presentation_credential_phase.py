"""Synthetic signed commitments cannot excuse changed frames or context."""

import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from hmp_plugin.presentation_broker_codec import BrokerBinding, encode_frame
from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_phase import (
    check_broker_cleanup_commitment,
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


@pytest.mark.parametrize("phase,sequence", [
    ("RESULT", 1), ("TERMINAL", 0), ("TERMINAL", 1), ("TERMINAL", 2),
])
def test_cleanup_boundary_authenticates_fixed_phase_sequence_data(phase, sequence):
    data = fixture(phase, b"data", sequence)
    binding, frame, expected, sp, rp, sign = data
    context = {k: v for k, v in expected.items() if k != "phase"}
    fact = check_broker_cleanup_commitment(
        sign(), sender_public=sp, receiver_public=rp, expected_context=context)
    assert check_complete_frame(fact, frame, binding=binding).kind == phase
    assert not hasattr(fact, "authorized")
    for updates in ({"sequence": 3}, {"generation": "f" * 64}):
        with pytest.raises(FrameError):
            check_broker_cleanup_commitment(
                sign(updates), sender_public=sp, receiver_public=rp, expected_context=context)
    damaged = sign()[:-1] + bytes([sign()[-1] ^ 1])
    with pytest.raises(FrameError):
        check_broker_cleanup_commitment(
            damaged, sender_public=sp, receiver_public=rp, expected_context=context)


@pytest.mark.parametrize("phase,body", [
    ("READY", b""), ("GO", b""), ("ACK", b"x" * 32), ("CANCEL", b"x" * 16),
])
def test_cleanup_boundary_refuses_other_signed_phases(phase, body):
    _, _, expected, sp, rp, sign = fixture(phase, body)
    context = {k: v for k, v in expected.items() if k != "phase"}
    context.update(role="broker", direction="b2g")
    with pytest.raises(FrameError):
        check_broker_cleanup_commitment(
            sign(), sender_public=sp, receiver_public=rp, expected_context=context)


@pytest.mark.parametrize("change", ["extra", "missing", "bool_end", "wrong_role", "wrong_peer"])
def test_cleanup_boundary_requires_exact_retained_context_and_peer(change):
    _, _, expected, sp, rp, sign = fixture()
    context = {k: v for k, v in expected.items() if k != "phase"}
    if change == "extra":
        context["phase"] = "RESULT"
    elif change == "missing":
        del context["channel"]
    elif change == "bool_end":
        context["work_end_ns"] = True
    elif change == "wrong_role":
        context["role"] = "gateway"
    else:
        rp = sp
    with pytest.raises(FrameError):
        check_broker_cleanup_commitment(
            sign(), sender_public=sp, receiver_public=rp, expected_context=context)


@pytest.mark.parametrize("sequence", [0, 1, 2])
def test_early_terminal_cannot_choose_another_retained_sequence(sequence):
    _, _, expected, sp, rp, sign = fixture("TERMINAL", b"data", sequence)
    context = {k: v for k, v in expected.items() if k != "phase"}
    context["sequence"] = (sequence + 1) % 3
    with pytest.raises(FrameError):
        check_broker_cleanup_commitment(
            sign(), sender_public=sp, receiver_public=rp, expected_context=context)


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


def begin_fixture(updates=None):
    from hmp_plugin.presentation_credential_scope import derive_input_scope
    from hmp_plugin.presentation_input_v3 import encode_input_v3

    from .test_presentation_credential_scope import input_value

    value = dict(input_value(), **(updates or {}))
    if value["profile"] != "default":
        value["home"] = value["root"] + "/profiles/" + value["profile"]
        value["directory_policy"] = value["directory_policy"] + [[501, 20, 448]] * 2
        parts = value["home"][1:].split("/")
        value["parent_work_counts"] = dict(
            value["parent_work_counts"],
            opens=len(parts) + 1,
            metadata=4 * (len(parts) + 1),
            path_bytes=3 * (1 + sum(len(part.encode("utf-8")) for part in parts)),
        )
    packet = encode_input_v3(value)
    data = fixture("BEGIN", packet, sequence=0)
    binding, frame, expected, sp, rp, sign = data
    scope = derive_input_scope(packet, binding)
    updates = {
        "input_sha256": scope.input_sha256,
        "scope_sha256": scope.scope_sha256,
        "work_end_ns": value["deadline_ns"],
    }
    context = {
        key: item
        for key, item in dict(expected, **updates).items()
        if key not in ("input_sha256", "scope_sha256")
    }
    return (
        binding,
        frame,
        context,
        sp,
        rp,
        lambda changed=None: sign(dict(updates, **(changed or {}))),
    )


def test_begin_stages_hash_claims_then_independently_checks_original_input():
    from hmp_plugin.presentation_credential_phase import check_begin_frame, stage_begin_commitment

    binding, frame, context, sp, rp, sign = begin_fixture()
    raw = sign()
    staged = stage_begin_commitment(
        raw, sender_public=sp, receiver_public=rp, expected_context=context
    )
    end = 8 + int.from_bytes(frame[4:8], "big")
    header = check_committed_header(staged, frame[:end], binding=binding)
    assert header.kind == "BEGIN" and header.sequence == 0
    result = check_begin_frame(
        raw, frame, sender_public=sp, receiver_public=rp, expected_context=context, binding=binding
    )
    assert result.commitment == staged and result.packet == frame[end:]
    assert not hasattr(result, "authorized") and not hasattr(result, "adopted")


@pytest.mark.parametrize("field", ["input_sha256", "scope_sha256"])
def test_valid_signed_begin_hash_is_only_unadopted_claim(field):
    from hmp_plugin.presentation_credential_phase import check_begin_frame, stage_begin_commitment

    binding, frame, context, sp, rp, sign = begin_fixture()
    raw = sign({field: "f" * 64})
    # A valid role signature alone cannot establish the actual input relationship.
    stage_begin_commitment(raw, sender_public=sp, receiver_public=rp, expected_context=context)
    with pytest.raises(FrameError):
        check_begin_frame(
            raw,
            frame,
            sender_public=sp,
            receiver_public=rp,
            expected_context=context,
            binding=binding,
        )


def test_signed_begin_deadline_must_equal_exact_decoded_input_deadline():
    from hmp_plugin.presentation_credential_phase import check_begin_frame

    binding, frame, context, sp, rp, sign = begin_fixture()
    context["work_end_ns"] += 1
    with pytest.raises(FrameError):
        check_begin_frame(
            sign({"work_end_ns": context["work_end_ns"]}),
            frame,
            sender_public=sp,
            receiver_public=rp,
            expected_context=context,
            binding=binding,
        )


@pytest.mark.parametrize("change", ["phase", "sequence", "role", "extra", "missing", "bool"])
def test_begin_staging_rejects_non_original_or_open_context(change):
    from hmp_plugin.presentation_credential_phase import stage_begin_commitment

    _, _, context, sp, rp, sign = begin_fixture()
    raw = sign()
    if change == "phase":
        context["phase"] = "GO"
    elif change == "sequence":
        context["sequence"] = 1
    elif change == "role":
        context["role"] = "broker"
    elif change == "extra":
        context["input_sha256"] = "f" * 64
    elif change == "missing":
        del context["operation_id"]
    else:
        context["work_end_ns"] = True
    with pytest.raises(FrameError):
        stage_begin_commitment(raw, sender_public=sp, receiver_public=rp, expected_context=context)


@pytest.mark.parametrize(
    "updates",
    [
        {"profile": "second"},
        {"challenge": "c" * 64},
        {"epoch": 2},
        {"operation": "AVATAR", "expected_avatar_sha": "d" * 64},
        {"canonical_fallback": "Renamed"},
    ],
)
def test_valid_signed_changed_input_cannot_reuse_original_scope(updates):
    from hmp_plugin.presentation_credential_codec import decode_record
    from hmp_plugin.presentation_credential_phase import check_begin_frame, stage_begin_commitment

    original = begin_fixture()
    original_scope = json.loads(decode_record(original[5]()).canonical_json)["scope_sha256"]
    binding, frame, context, sp, rp, sign = begin_fixture(updates)
    raw = sign({"scope_sha256": original_scope})
    stage_begin_commitment(raw, sender_public=sp, receiver_public=rp, expected_context=context)
    with pytest.raises(FrameError):
        check_begin_frame(
            raw,
            frame,
            sender_public=sp,
            receiver_public=rp,
            expected_context=context,
            binding=binding,
        )


def test_correctly_signed_whole_frame_does_not_excuse_invalid_input3():
    from hmp_plugin.presentation_credential_phase import check_begin_frame, stage_begin_commitment

    binding, frame, expected, sp, rp, sign = fixture("BEGIN", b"data", sequence=0)
    context = {
        key: value for key, value in expected.items() if key not in ("input_sha256", "scope_sha256")
    }
    raw = sign()
    stage_begin_commitment(raw, sender_public=sp, receiver_public=rp, expected_context=context)
    with pytest.raises(FrameError):
        check_begin_frame(
            raw,
            frame,
            sender_public=sp,
            receiver_public=rp,
            expected_context=context,
            binding=binding,
        )
