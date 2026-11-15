"""Actual synthetic signatures and frame bytes; consistency DATA, no native IO."""
import hashlib
from dataclasses import replace

import pytest

from hmp_plugin.presentation_broker_codec import TERMINAL_LIMIT, header_size
from hmp_plugin.presentation_credential_frame_discard import CommittedFrameDiscard
from hmp_plugin.presentation_credential_phase import check_commitment
from hmp_plugin.presentation_credential_stream import CHUNK_LIMIT, CommittedFrameDigest
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_credential_phase import fixture


def prepared(phase="RESULT", body=b"image-data", sequence=1, **updates):
    binding, frame, expected, sender, receiver, sign = fixture(phase, body, sequence)
    checked = check_commitment(sign(), sender_public=sender, receiver_public=receiver,
                               expected=expected)
    parser = CommittedFrameDiscard(checked, binding=binding,
        phase=updates.get("phase", phase), sequence=updates.get("sequence", sequence))
    return parser, frame, 8 + header_size(frame[:8])


def header(parser, frame, end):
    parser.feed(frame[:3])
    assert parser.needed == 5
    parser.feed(frame[3:8])
    assert parser.needed == end - 8
    parser.feed(frame[8:end])


@pytest.mark.parametrize("phase,sequence,body", [
    ("RESULT", 1, b"x" * (CHUNK_LIMIT + 7)),
    ("TERMINAL", 0, b"not-a-qualified-ABORTED-claim"),
    ("TERMINAL", 1, b"synthetic terminal metadata"),
    ("TERMINAL", 2, b"x" * TERMINAL_LIMIT),
])
def test_exact_header_then_body_discard_full_hash(phase, sequence, body):
    parser, frame, end = prepared(phase, body, sequence)
    header(parser, frame, end)
    stream = parser._stream_origin
    assert parser._stream_allocation[1] is stream
    for start in range(end, len(frame), CHUNK_LIMIT):
        count = parser.needed
        parser.feed(frame[start:start + count])
        assert parser._stream_origin is stream
        assert bytes(parser._buffer_origin) == frame[:end]
        if phase == "RESULT":
            assert not parser._terminal_origin
    assert parser.needed == 0
    result = parser.finish()
    assert result.digest.frame_length == len(frame)
    assert result.digest.frame_sha256 == hashlib.sha256(frame).hexdigest()
    assert result.phase == phase and result.sequence == sequence
    assert result.terminal == (body if phase == "TERMINAL" else None)
    assert result.payload_sha256 == (
        hashlib.sha256(body).hexdigest() if phase == "RESULT" else None
    )
    if phase == "RESULT":
        assert parser._payload_origin._hasher_origin is not stream._hasher_origin
        assert parser._payload_origin._received == len(body)
    assert not parser._terminal_origin
    assert not hasattr(result, "accepted") and not hasattr(result, "release")
    assert "synthetic" not in repr(result)
    with pytest.raises(FrameError):
        parser.finish()
    assert parser._finished and not parser._failed


@pytest.mark.parametrize("chunk", [b"", bytearray(b"x"), memoryview(b"x"), b"x" * 9])
def test_bad_chunk_before_first_header_never_rescans(chunk):
    parser, frame, _ = prepared()
    with pytest.raises(FrameError):
        parser.feed(chunk)
    assert parser._failed and not parser._buffer_origin and not parser._terminal_origin
    with pytest.raises(FrameError):
        parser.feed(frame[:8])


def test_following_frame_cannot_be_overread_or_used_to_repair_body():
    parser, frame, end = prepared()
    header(parser, frame, end)
    parser.feed(frame[end:])
    assert parser.needed == 0
    with pytest.raises(FrameError):
        parser.feed(b"HBV2NEXT")
    assert parser._failed
    with pytest.raises(FrameError):
        parser.finish()


@pytest.mark.parametrize("phase", ["RESULT", "TERMINAL"])
def test_body_hash_failure_wipes_private_metadata_without_replay(phase):
    parser, frame, end = prepared(phase)
    header(parser, frame, end)
    bad = bytes([frame[end] ^ 1]) + frame[end + 1:]
    parser.feed(bad)
    with pytest.raises(FrameError):
        parser.finish()
    assert parser._failed and not parser._buffer_origin and not parser._terminal_origin
    assert parser._digest is None and parser._fact is None
    with pytest.raises(FrameError):
        parser.feed(frame[end:])


@pytest.mark.parametrize("kind,sequence", [(True, 1), ("RESULT", True), ("RESULT", 0),
                                          ("TERMINAL", 3), ("ACK", 1)])
def test_closed_exact_phase_and_sequence_types(kind, sequence):
    binding, _, expected, sender, receiver, sign = fixture()
    checked = check_commitment(sign(), sender_public=sender, receiver_public=receiver,
                               expected=expected)
    with pytest.raises(FrameError):
        CommittedFrameDiscard(checked, binding=binding, phase=kind, sequence=sequence)


@pytest.mark.parametrize("expected_phase,expected_sequence", [("TERMINAL", 1), ("RESULT", 2)])
def test_no_phase_or_sequence_fallback(expected_phase, expected_sequence):
    if expected_phase == "RESULT":
        with pytest.raises(FrameError):
            prepared(phase=expected_phase, sequence=expected_sequence)
        return
    parser, frame, end = prepared("RESULT")
    # A separately constructed data parser cannot reinterpret a RESULT as TERMINAL.
    other = CommittedFrameDiscard(parser._claim_origin, binding=parser._binding_origin,
                                  phase=expected_phase, sequence=expected_sequence)
    with pytest.raises(FrameError):
        header(other, frame, end)
    assert other._failed


def test_coherent_copied_digest_is_not_the_allocated_original():
    parser, frame, end = prepared()
    header(parser, frame, end)
    original = parser._stream_origin
    other = CommittedFrameDigest(parser._claim_origin, frame[:end], binding=parser._binding_origin)
    parser._stream = parser._stream_origin = other
    with pytest.raises(FrameError):
        parser.feed(frame[end:])
    assert original._received == 0 and other._received == 0
    assert parser._stream_allocation[1] is original


def test_partial_digest_initialization_is_retained_before_effect(monkeypatch):
    parser, frame, end = prepared()
    actual = CommittedFrameDigest.__init__
    seen = []

    def lost_init(stream, *args, **kwargs):
        assert parser._stream_allocation[1] is stream
        seen.append(stream)
        actual(stream, *args, **kwargs)
        raise OSError("synthetic lost digest initialization")

    monkeypatch.setattr(CommittedFrameDigest, "__init__", lost_init)
    with pytest.raises(FrameError):
        header(parser, frame, end)
    assert len(seen) == 1 and parser._stream_allocation[1] is seen[0]
    assert parser._failed and not parser._buffer_origin


def test_lost_hash_finish_return_is_unknown_and_not_retried(monkeypatch):
    parser, frame, end = prepared("TERMINAL")
    header(parser, frame, end)
    parser.feed(frame[end:])
    finish = CommittedFrameDigest.finish
    seen = []

    def lost_return(stream):
        seen.append(stream)
        finish(stream)
        raise OSError("synthetic lost hash acknowledgement")

    monkeypatch.setattr(CommittedFrameDigest, "finish", lost_return)
    with pytest.raises(FrameError):
        parser.finish()
    assert parser._stream_origin._finished and parser._digest is None
    assert parser._failed and not parser._terminal_origin
    with pytest.raises(FrameError):
        parser.finish()
    assert len(seen) == 1


def test_changed_binding_and_returned_digest_are_refused(monkeypatch):
    parser, frame, end = prepared()
    header(parser, frame, end)
    parser.feed(frame[end:])
    finish = CommittedFrameDigest.finish

    def corrupt_return(stream):
        return replace(finish(stream), frame_length=len(frame) + 1)

    monkeypatch.setattr(CommittedFrameDigest, "finish", corrupt_return)
    with pytest.raises(FrameError):
        parser.finish()
    assert parser._finish_returned and parser._digest_allocation[1] is parser._digest
    assert parser._failed and parser._fact is None


def test_foreign_header_return_has_no_getter_dispatch(monkeypatch):
    from hmp_plugin import presentation_credential_frame_discard as module
    parser, frame, end = prepared()
    seen = []

    class ForeignHeader:
        def __getattr__(self, name):
            seen.append(name)
            raise AssertionError("foreign header access")

    monkeypatch.setattr(module, "check_committed_header", lambda *a, **k: ForeignHeader())
    with pytest.raises(FrameError):
        header(parser, frame, end)
    assert not seen and parser._failed


def test_native_hash_callback_cannot_dispatch_foreign_allocation(monkeypatch):
    from hmp_plugin import presentation_credential_frame_discard as module
    parser, frame, end = prepared("TERMINAL")
    header(parser, frame, end)
    parser.feed(frame[end:])
    sha = module._SHA256
    seen = []

    class ForeignAllocation:
        def __getitem__(self, key):
            seen.append(key)
            raise AssertionError("foreign hash allocation")

    def changed_hash_origin(raw):
        value = sha(raw)
        parser._hash_allocation = ForeignAllocation()
        return value

    monkeypatch.setattr(module, "_SHA256", changed_hash_origin)
    with pytest.raises(FrameError):
        parser.finish()
    assert not seen and parser._failed
    assert not parser._terminal_origin and parser._fact is None


def test_terminal_bytes_mutated_after_stream_hash_are_never_transferred(monkeypatch):
    parser, frame, end = prepared("TERMINAL")
    header(parser, frame, end)
    feed = CommittedFrameDigest.feed

    def changed_terminal(stream, chunk):
        feed(stream, chunk)
        parser._terminal_origin[0] ^= 1

    monkeypatch.setattr(CommittedFrameDigest, "feed", changed_terminal)
    parser.feed(frame[end:])
    with pytest.raises(FrameError):
        parser.finish()
    assert parser._finish_returned and parser._fact is None
    assert not parser._terminal_origin
