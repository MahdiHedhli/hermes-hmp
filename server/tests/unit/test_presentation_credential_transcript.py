"""Synthetic bilateral transcript fixtures, without runtime admission."""

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_transcript import channel_digest, check_transcript
from hmp_plugin.presentation_jobs import FrameError


def fixture(seed="a", mutation=None):
    keys = {role: Ed25519PrivateKey.generate() for role in ("gateway", "broker")}
    public = {
        role: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        for role, key in keys.items()
    }
    ids = {role: hashlib.sha256(raw).hexdigest() for role, raw in public.items()}
    context = {
        "iid": "a" * 52,
        "listener": "1" * 32,
        "generation": "2" * 64,
        "clock_domain": "3" * 64,
        "operation_id": "4" * 64,
        "work_end_ns": 100,
    }

    def sign(phase, role, **extra):
        peer = "broker" if role == "gateway" else "gateway"
        value = dict(
            context,
            v=1,
            family="handshake",
            alg="Ed25519",
            phase=phase,
            role=role,
            direction="g2b" if role == "gateway" else "b2g",
            key_id=ids[role],
            peer_key_id=ids[peer],
            **extra,
        )
        if mutation is not None:
            mutation(phase, value)
        return encode_record(value, keys[role].sign(signing_bytes(value)))

    hello = sign("HELLO", "gateway", gateway_boot="5" * 64, gateway_nonce=seed * 64)
    challenge = sign(
        "CHALLENGE",
        "broker",
        gateway_boot="5" * 64,
        gateway_nonce=seed * 64,
        broker_boot="6" * 64,
        broker_nonce="7" * 64,
        hello_sha256=hashlib.sha256(hello).hexdigest(),
    )
    channel = channel_digest(hello, challenge)
    finish = sign(
        "FINISH",
        "gateway",
        gateway_boot="5" * 64,
        broker_boot="6" * 64,
        channel=channel,
        hello_sha256=hashlib.sha256(hello).hexdigest(),
        challenge_sha256=hashlib.sha256(challenge).hexdigest(),
    )
    accept = sign(
        "ACCEPT",
        "broker",
        gateway_boot="5" * 64,
        broker_boot="6" * 64,
        channel=channel,
        finish_sha256=hashlib.sha256(finish).hexdigest(),
    )
    return (hello, challenge, finish, accept), public, context


def check(records, public, context):
    return check_transcript(
        records,
        gateway_public=public["gateway"],
        broker_public=public["broker"],
        expected_context=context,
    )


def test_all_handshake_phases_and_exact_transcript_hash():
    records, public, context = fixture()
    result = check(records, public, context)
    assert result.channel == channel_digest(*records[:2])
    assert (
        result.transcript_sha256
        == hashlib.sha256(b"HMP-BI1-TRANSCRIPT-1\0" + b"".join(records)).hexdigest()
    )
    assert not hasattr(result, "authorized")


@pytest.mark.parametrize("index", range(4))
def test_each_signature_tamper_refused(index):
    records, public, context = fixture()
    changed = list(records)
    changed[index] = changed[index][:-1] + bytes([changed[index][-1] ^ 1])
    with pytest.raises(FrameError):
        check(tuple(changed), public, context)


def test_operation_rebinding_splice_wrong_key_and_order_refused():
    records, public, context = fixture()
    other, _, _ = fixture("b")
    for changed, pins, expected in (
        (records, public, dict(context, work_end_ns=101)),
        (records, dict(public, broker=public["gateway"]), context),
        ((records[0], other[1], records[2], records[3]), public, context),
        ((records[1], records[0], records[2], records[3]), public, context),
    ):
        with pytest.raises(FrameError):
            check(changed, pins, expected)


def test_foreign_context_key_refused_before_equality():
    class Foreign(str):
        def __eq__(self, other):
            raise AssertionError("foreign equality must not run")

        __hash__ = str.__hash__

    records, public, context = fixture()
    expected = {Foreign(name): value for name, value in context.items()}
    with pytest.raises(FrameError):
        check(records, public, expected)


@pytest.mark.parametrize(
    "phase,field,bad",
    [
        ("CHALLENGE", "hello_sha256", "f" * 64),
        ("FINISH", "challenge_sha256", "f" * 64),
        ("ACCEPT", "finish_sha256", "f" * 64),
        ("CHALLENGE", "gateway_nonce", "f" * 64),
        ("FINISH", "gateway_boot", "f" * 64),
        ("ACCEPT", "broker_boot", "f" * 64),
        ("CHALLENGE", "broker_nonce", "6" * 64),
    ],
)
def test_valid_signatures_do_not_excuse_broken_transcript_links(phase, field, bad):
    def mutate(current, value):
        if current == phase:
            value[field] = bad

    records, public, context = fixture(mutation=mutate)
    with pytest.raises(FrameError):
        check(records, public, context)
