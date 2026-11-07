"""Synthetic signed frames; streaming digest is data, not receiver authority."""

import hashlib
import threading

import pytest

from hmp_plugin.presentation_broker_codec import header_size
from hmp_plugin.presentation_credential_phase import check_commitment
from hmp_plugin.presentation_credential_stream import CHUNK_LIMIT, CommittedFrameDigest
from hmp_plugin.presentation_jobs import OUTPUT_LIMIT, FrameError

from .test_presentation_credential_phase import fixture as phase_fixture


def stream_fixture(phase="RESULT", body=b"data", updates=None):
    binding, frame, expected, sender, receiver, sign = phase_fixture(phase, body)
    commitment = check_commitment(
        sign(updates), sender_public=sender, receiver_public=receiver, expected=expected
    )
    end = 8 + header_size(frame[:8])
    return CommittedFrameDigest(commitment, frame[:end], binding=binding), frame, end


@pytest.mark.parametrize(
    "phase,body",
    [
        ("BEGIN", b"data"),
        ("READY", b""),
        ("GO", b""),
        ("RESULT", b"x" * OUTPUT_LIMIT),
        ("CANCEL", b"x" * 16),
        ("TERMINAL", b"x"),
        ("ACK", b"x" * 32),
    ],
)
def test_chunked_all_phase_bodies_include_exact_original_header(phase, body):
    stream, frame, end = stream_fixture(phase, body)
    assert stream.remaining == len(body)
    for start in range(0, len(body), CHUNK_LIMIT):
        stream.feed(body[start : start + CHUNK_LIMIT])
    assert stream.remaining == 0
    result = stream.finish()
    assert result.frame_sha256 == hashlib.sha256(frame).hexdigest()
    assert result.frame_length == end + len(body)
    assert not hasattr(result, "authorized") and not hasattr(result, "transfer_complete")
    assert all(value is not body for value in vars(stream).values())
    with pytest.raises(FrameError):
        stream.finish()


def test_different_chunk_boundaries_have_same_exact_frame_digest():
    stream, frame, end = stream_fixture(body=b"abcdefgh")
    body = frame[end:]
    for chunk in (body[:1], body[1:4], body[4:]):
        stream.feed(chunk)
    assert stream.finish().frame_sha256 == hashlib.sha256(frame).hexdigest()


@pytest.mark.parametrize("bad", [b"", bytearray(b"data"), memoryview(b"data"), b"too many"])
def test_bad_chunk_refuses_before_progress_and_cannot_resume(bad):
    stream, _, _ = stream_fixture()
    with pytest.raises(FrameError):
        stream.feed(bad)
    assert stream._received == 0
    with pytest.raises(FrameError):
        stream.feed(b"data")
    with pytest.raises(FrameError):
        stream.finish()


def test_chunk_bound_is_independent_of_total_result_limit():
    stream, _, _ = stream_fixture(body=b"x" * (CHUNK_LIMIT + 1))
    with pytest.raises(FrameError):
        stream.feed(b"x" * (CHUNK_LIMIT + 1))
    assert stream._received == 0


def test_truncation_and_body_tampering_never_finish_or_reset():
    stream, _, _ = stream_fixture()
    stream.feed(b"da")
    with pytest.raises(FrameError):
        stream.finish()
    with pytest.raises(FrameError):
        stream.feed(b"ta")
    other, _, _ = stream_fixture()
    other.feed(b"date")
    with pytest.raises(FrameError):
        other.finish()
    records = (other._hasher, other._received)
    with pytest.raises(FrameError):
        other.__init__(other._commitment, b"", binding=other._binding)
    assert other._hasher is records[0] and other._received == records[1] and other._failed


def test_valid_signature_with_wrong_digest_does_not_make_consistent_body():
    stream, _, _ = stream_fixture(updates={"frame_sha256": "f" * 64})
    stream.feed(b"data")
    with pytest.raises(FrameError):
        stream.finish()


def test_wrong_header_length_refuses_before_stream_body_creation():
    with pytest.raises(FrameError):
        stream_fixture(updates={"frame_length": 1000})


def test_commitment_and_binding_drift_refuse_without_foreign_callbacks():
    stream, _, _ = stream_fixture()
    calls = []

    class Foreign:
        def __eq__(self, other):
            calls.append("equality")
            raise AssertionError("foreign commitment must not be compared")

    object.__setattr__(stream._commitment, "frame_sha256", Foreign())
    with pytest.raises(FrameError):
        stream.feed(b"data")
    assert calls == [] and stream._received == 0
    second, _, _ = stream_fixture()
    object.__setattr__(second._binding, "channel", "f" * 64)
    with pytest.raises(FrameError):
        second.feed(b"data")
    assert second._received == 0


def test_different_thread_cannot_borrow_original_digest():
    stream, _, _ = stream_fixture()
    refused = []

    def borrow():
        try:
            stream.feed(b"data")
        except FrameError:
            refused.append(True)

    thread = threading.Thread(target=borrow)
    thread.start()
    thread.join(timeout=1)
    assert not thread.is_alive() and refused == [True] and stream._received == 0
    with pytest.raises(FrameError):
        stream.finish()


def cleanup_auth_fixture(phase="RESULT", sequence=1):
    from hmp_plugin.presentation_credential_stream import SignedCleanupAuthPrefix

    _, frame, expected, sender, receiver, sign = phase_fixture(phase, b"data", sequence)
    context = {k: v for k, v in expected.items() if k not in ("phase", "sequence")}
    raw = sign()

    def make(prefix=b""):
        return SignedCleanupAuthPrefix(prefix, sender_public=sender, receiver_public=receiver,
                                       expected_context=context)

    return make, raw, frame


@pytest.mark.parametrize("phase,sequence", [("RESULT", 1), ("TERMINAL", 2)])
@pytest.mark.parametrize("cut", [0, 1, 7, 8, 9, 73, -1, -2])
def test_cleanup_auth_preserves_same_partial_record_without_body(phase, sequence, cut):
    make, raw, frame = cleanup_auth_fixture(phase, sequence)
    cut = len(raw) + cut + 1 if cut < 0 else cut
    reader = make(raw[:cut])
    offset = cut
    while offset < len(raw):
        count = min(reader.needed, 11, len(raw) - offset)
        reader.feed(raw[offset:offset + count])
        offset += count
    assert reader.needed == 0
    fact = reader.finish()
    assert fact.frame_sha256 == hashlib.sha256(frame).hexdigest()
    assert reader._buffer_origin == bytearray()
    assert not hasattr(fact, "authorized")
    for action in (lambda: reader.feed(b"x"), reader.finish, lambda: reader.needed):
        with pytest.raises(FrameError):
            action()


def test_cleanup_auth_rejects_overread_and_never_scans_following_record():
    make, raw, _ = cleanup_auth_fixture()
    for prefix in (raw + b"x", raw + raw):
        with pytest.raises(FrameError):
            make(prefix)
    reader = make(raw[:-1])
    with pytest.raises(FrameError):
        reader.feed(raw[-1:] + b"x")
    assert reader._buffer_origin == bytearray()
    with pytest.raises(FrameError):
        reader.feed(raw[-1:])


def test_cleanup_auth_truncation_and_invalid_signature_are_permanent():
    make, raw, _ = cleanup_auth_fixture()
    for prefix in (raw[:-1], raw[:-1] + bytes([raw[-1] ^ 1])):
        reader = make(prefix)
        with pytest.raises(FrameError):
            reader.finish()
        assert reader._failed and not reader._buffer_origin
        with pytest.raises(FrameError):
            reader.finish()


def test_cleanup_auth_foreign_target_refuses_without_index_or_arithmetic():
    make, raw, _ = cleanup_auth_fixture()
    reader = make(raw[:8])
    calls = []

    class Foreign:
        def __index__(self):
            calls.append("index")
            return 100

        def __sub__(self, other):
            calls.append("subtract")
            return 1

    reader._target = reader._target_origin = Foreign()
    with pytest.raises(FrameError):
        reader.feed(b"x")
    assert calls == [] and not reader._buffer_origin
