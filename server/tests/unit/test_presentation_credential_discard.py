"""Signed discard framing/digest DATA only; no runtime cursor or IO qualification."""

import hashlib

import pytest

from hmp_plugin.presentation_broker_codec import header_size
from hmp_plugin.presentation_credential_phase import check_commitment
from hmp_plugin.presentation_credential_stream import (
    CHUNK_LIMIT,
    CommittedFrameDigest,
    SignedResultDiscard,
)
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_credential_phase import fixture as phase_fixture


def source(body=b"abcdefgh", updates=None):
    binding, frame, expected, sender, receiver, sign = phase_fixture("RESULT", body)
    raw = sign(updates)
    end = 8 + header_size(frame[:8])
    return raw, frame[:end], body, {"sender_public": sender, "receiver_public": receiver,
                                   "expected": expected, "binding": binding}


def consume(cursor, wire, offset=0):
    while offset < len(wire):
        size = cursor.needed
        assert 0 < size <= CHUNK_LIMIT
        part = wire[offset:offset + size]
        cursor.feed(part)
        offset += len(part)
    return cursor.finish()


@pytest.mark.parametrize("offset", [0, 1, 4, 7, 8, 12, -9, -8, -4, -1, None])
def test_original_partial_header_continues_exact_framing_without_body_retention(offset):
    raw, header, body, args = source()
    prefix = raw + header
    if offset is None:
        offset = len(prefix)
    elif offset < 0:
        offset += len(prefix)
    cursor = SignedResultDiscard(prefix[:offset], **args)
    fact = consume(cursor, prefix[offset:] + body)
    assert fact.frame_sha256 == hashlib.sha256(header + body).hexdigest()
    assert fact.frame_length == len(header) + len(body)
    assert cursor._buffer_origin == bytearray()
    assert not hasattr(cursor, "authorized") and not hasattr(cursor, "socket")
    assert all(value is not body for value in vars(cursor).values())
    with pytest.raises(FrameError):
        cursor.finish()


@pytest.mark.parametrize("offset", [0, 1, 4, 7, 8])
def test_partial_body_uses_same_original_digest_without_replaying_bytes(offset):
    raw, header, body, args = source()
    checked = check_commitment(raw, sender_public=args["sender_public"],
                               receiver_public=args["receiver_public"], expected=args["expected"])
    original = CommittedFrameDigest(checked, header, binding=args["binding"])
    if offset:
        original.feed(body[:offset])
    hasher = original._hasher_origin
    cursor = SignedResultDiscard(raw + header, stream=original, **args)
    assert cursor._stream_origin is original and original._hasher_origin is hasher
    assert cursor.needed == len(body) - offset
    fact = consume(cursor, body[offset:])
    assert fact.frame_sha256 == hashlib.sha256(header + body).hexdigest()
    assert original._finished and original._received == len(body)


def test_no_frame_scanning_or_terminal_escape_after_body_corruption():
    raw, header, body, args = source()
    cursor = SignedResultDiscard(raw + header, **args)
    cursor.feed(b"HBA1xxxx")  # terminal-looking bytes are still exact RESULT body bytes
    with pytest.raises(FrameError):
        cursor.finish()
    with pytest.raises(FrameError):
        cursor.feed(body)


@pytest.mark.parametrize("mutation", ["signature", "scope", "length", "digest", "prefix_body"])
def test_bad_signed_metadata_or_body_never_finishes_or_restarts(mutation):
    updates = {"frame_length": 999} if mutation == "length" else None
    if mutation == "digest":
        updates = {"frame_sha256": "f" * 64}
    raw, header, body, args = source(updates=updates)
    if mutation == "signature":
        raw = raw[:-1] + bytes([raw[-1] ^ 1])
    if mutation == "scope":
        args["expected"]["input_sha256"] = "f" * 64
    with pytest.raises(FrameError):
        cursor = SignedResultDiscard(raw + header + (body if mutation == "prefix_body" else b""),
                                     **args)
        consume(cursor, body)


def test_resume_must_match_complete_original_signed_header_and_digest():
    raw, header, _, args = source()
    other_raw, other_header, _, other_args = source(b"different")
    checked = check_commitment(other_raw, sender_public=other_args["sender_public"],
                               receiver_public=other_args["receiver_public"],
                               expected=other_args["expected"])
    other = CommittedFrameDigest(checked, other_header, binding=other_args["binding"])
    with pytest.raises(FrameError):
        SignedResultDiscard(raw + header, stream=other, **args)
    with pytest.raises(FrameError):
        SignedResultDiscard(raw[:4], stream=other, **args)
    assert other._received == 0 and not other._finished


def test_body_chunk_cap_and_exact_remainder_with_large_result():
    body = b"x" * (CHUNK_LIMIT + 13)
    raw, header, _, args = source(body)
    cursor = SignedResultDiscard(raw + header, **args)
    assert cursor.needed == CHUNK_LIMIT
    cursor.feed(body[:CHUNK_LIMIT])
    assert cursor.needed == 13
    assert len(cursor._buffer_origin) == len(raw) + len(header)
    fact = consume(cursor, body[CHUNK_LIMIT:])
    assert fact.frame_sha256 == hashlib.sha256(header + body).hexdigest()


def test_overshoot_and_truncation_are_sticky_no_retry():
    raw, header, body, args = source()
    cursor = SignedResultDiscard(raw[:4], **args)
    with pytest.raises(FrameError):
        cursor.feed(raw[4:])
    assert cursor._failed and not cursor._buffer_origin
    with pytest.raises(FrameError):
        cursor.feed(b"HBA1")
    other = SignedResultDiscard(raw + header, **args)
    other.feed(body[:4])
    with pytest.raises(FrameError):
        other.finish()
    with pytest.raises(FrameError):
        other.feed(body[4:])


def test_refusal_tracebacks_do_not_retain_supplied_image_chunks():
    raw, header, _, args = source()
    marker = b"PRIVATE_SYNTHETIC_IMAGE_CONTENT_DO_NOT_RETAIN"
    cursor = SignedResultDiscard(raw + header, **args)
    with pytest.raises(FrameError) as caught:
        cursor.feed(marker)  # overshoots the exact eight-byte remainder
    assert caught.value.__context__ is None
    tb = caught.value.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename.endswith("presentation_credential_stream.py"):
            assert all(not (type(v) in (bytes, bytearray) and marker in v)
                       for v in tb.tb_frame.f_locals.values())
        tb = tb.tb_next
    with pytest.raises(FrameError) as constructor_failure:
        SignedResultDiscard(raw + header + marker, **args)
    assert constructor_failure.value.__context__ is None
    tb = constructor_failure.value.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename.endswith("presentation_credential_stream.py"):
            assert all(not (type(v) in (bytes, bytearray) and marker in v)
                       for v in tb.tb_frame.f_locals.values())
        tb = tb.tb_next


def test_foreign_expected_key_is_rejected_without_equality():
    raw, _, _, args = source()
    calls = []

    class ForeignKey:
        def __hash__(self):
            return hash("phase")

        def __eq__(self, other):
            calls.append("equality")
            return True

    expected = dict(args["expected"])
    value = expected.pop("phase")
    expected[ForeignKey()] = value
    args["expected"] = expected
    calls.clear()  # fixture construction is outside the parser
    with pytest.raises(FrameError):
        SignedResultDiscard(raw[:4], **args)
    assert calls == []


@pytest.mark.parametrize("stage", ["auth", "header_prefix", "header", "body"])
def test_foreign_paired_auth_end_is_rejected_before_index_or_arithmetic(stage):
    raw, header, _, args = source()
    prefixes = {"auth": raw[:8], "header_prefix": raw,
                "header": raw + header[:8], "body": raw + header}
    cursor = SignedResultDiscard(prefixes[stage], **args)
    calls = []

    class ForeignOffset:
        def __index__(self):
            calls.append("index")
            return len(raw)

        def __add__(self, other):
            calls.append("add")
            return len(raw) + other

        def __eq__(self, other):
            calls.append("equality")
            return True

    cursor._auth_end = cursor._auth_end_origin = ForeignOffset()
    with pytest.raises(FrameError):
        cursor.feed(b"x")
    assert cursor._failed and calls == []
