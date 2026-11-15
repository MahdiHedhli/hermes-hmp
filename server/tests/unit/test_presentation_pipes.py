import os
import time

import pytest

from hmp_plugin.presentation_jobs import DIAGNOSTIC_LIMIT, FrameError
from hmp_plugin.presentation_pipes import OwnedPresentationPipes


@pytest.fixture
def pipes():
    result_read, result_write = os.pipe()
    diagnostic_read, diagnostic_write = os.pipe()
    result = os.fdopen(result_read, "rb", buffering=0)
    diagnostic = os.fdopen(diagnostic_read, "rb", buffering=0)
    owner = OwnedPresentationPipes(result, diagnostic)
    yield owner, result_write, diagnostic_write, result, diagnostic
    for stream in (result, diagnostic):
        if not stream.closed:
            stream.close()
    for fd in (result_write, diagnostic_write):
        try:
            os.close(fd)
        except OSError:
            continue


def test_actual_eof_closes_both_streams_and_counts_but_discards_diagnostics(pipes):
    owner, result_write, diagnostic_write, result, diagnostic = pipes
    os.write(result_write, b"synthetic-result")
    os.write(diagnostic_write, b"synthetic-diagnostic")
    os.close(result_write)
    os.close(diagnostic_write)
    deadline = time.monotonic() + 1.0
    while not owner.drained:
        owner.poll(deadline=deadline)
    assert owner.output == b"synthetic-result"
    assert owner.diagnostic_bytes == len(b"synthetic-diagnostic")
    assert result.closed and diagnostic.closed
    with pytest.raises(FrameError):
        owner.poll(deadline=deadline)


def test_expiry_does_not_invent_eof_or_close(pipes):
    owner, _, _, result, diagnostic = pipes
    with pytest.raises(FrameError, match="BI1_PIPE_DEADLINE"):
        owner.poll(deadline=time.monotonic() - 1.0)
    assert owner.refused and not owner.drained
    assert not result.closed and not diagnostic.closed


def test_diagnostic_overflow_is_refused_before_retaining_content(pipes):
    owner, _, diagnostic_write, _, _ = pipes
    os.write(diagnostic_write, b"x" * (DIAGNOSTIC_LIMIT + 1))
    with pytest.raises(FrameError, match="BI1_PIPE_LIMIT"):
        owner.poll(deadline=time.monotonic() + 1.0)
    assert owner.refused and not owner.drained
    assert owner.diagnostic_bytes == 0 and owner.output == b""


def test_externally_closed_stream_retains_uncertain_ownership(pipes):
    owner, result_write, _, result, _ = pipes
    os.write(result_write, b"x")
    result.close()
    with pytest.raises(FrameError, match="BI1_PIPE_UNCERTAIN"):
        owner.poll(deadline=time.monotonic() + 1.0)
    assert owner.uncertain and not owner.drained


def test_failed_acquisition_retains_selector_owner_when_cleanup_also_fails(monkeypatch):
    import io

    from hmp_plugin import presentation_pipes
    from hmp_plugin.presentation_pipes import PipeAcquisitionError

    class Selector:
        closes = 0

        def close(self):
            self.closes += 1
            raise OSError("synthetic cleanup error")

    selector = Selector()
    monkeypatch.setattr(presentation_pipes.selectors, "DefaultSelector", lambda: selector)
    # BytesIO has no OS descriptor, so acquisition fails after selector creation.
    with pytest.raises(PipeAcquisitionError) as captured:
        OwnedPresentationPipes(io.BytesIO(), io.BytesIO())
    owner = captured.value.failed_owner
    assert owner._selector is selector
    assert owner.uncertain and not owner.drained
    assert captured.value._original is not None
    assert isinstance(captured.value._cleanup, OSError)
    assert str(captured.value) == "BI1_PIPE_ACQUISITION_REFUSED"
    assert selector.closes == 1
    with pytest.raises(FrameError, match="BI1_SELECTOR_CLOSE_REFUSED"):
        owner._close_selector()
    assert selector.closes == 1


def test_selector_creation_failure_still_returns_explicit_uncertain_owner(monkeypatch):
    import io

    from hmp_plugin import presentation_pipes
    from hmp_plugin.presentation_pipes import PipeAcquisitionError

    def fail():
        raise OSError("synthetic acquisition error")

    monkeypatch.setattr(presentation_pipes.selectors, "DefaultSelector", fail)
    with pytest.raises(PipeAcquisitionError) as captured:
        OwnedPresentationPipes(io.BytesIO(), io.BytesIO())
    assert captured.value.failed_owner.uncertain
    assert not captured.value.failed_owner.drained
    assert captured.value._cleanup is None


def test_cleanup_discards_expired_result_without_renewing_output_authority(pipes):
    owner, result_write, diagnostic_write, result, diagnostic = pipes
    os.write(result_write, b"synthetic-leftover")
    os.write(diagnostic_write, b"synthetic-diagnostic")
    with pytest.raises(FrameError, match="BI1_PIPE_DEADLINE"):
        owner.poll(deadline=time.monotonic() - 1.0)
    os.close(result_write)
    os.close(diagnostic_write)
    while not owner.drained:
        owner.poll_discard()
    assert owner.refused and owner.output == b""
    assert owner._discarded_bytes == len(b"synthetic-leftoversynthetic-diagnostic")
    assert result.closed and diagnostic.closed
    with pytest.raises(FrameError):
        owner.poll(deadline=time.monotonic() + 1.0)


def test_cleanup_allowance_is_frozen_and_does_not_invent_eof(pipes, monkeypatch):
    from hmp_plugin import presentation_pipes

    owner, _, _, result, diagnostic = pipes
    now = [10.0]
    monkeypatch.setattr(presentation_pipes.time, "monotonic", lambda: now[0])
    owner.poll_discard()
    assert owner._cleanup_deadline == 10.25
    now[0] = 10.26
    for _ in range(2):
        with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_DEADLINE"):
            owner.poll_discard()
    assert owner._cleanup_deadline == 10.25
    assert not owner.drained and not result.closed and not diagnostic.closed


def test_cleanup_closed_descriptor_is_uncertain_and_not_retried(pipes):
    owner, _, _, result, diagnostic = pipes
    result.close()
    with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_UNCERTAIN"):
        owner.poll_discard()
    assert owner.uncertain and not owner.drained and not diagnostic.closed
    with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_REFUSED"):
        owner.poll_discard()


def test_already_drained_reader_still_wipes_buffer_and_refuses_output(pipes):
    owner, result_write, diagnostic_write, _, _ = pipes
    os.write(result_write, b"synthetic-buffered")
    os.close(result_write)
    os.close(diagnostic_write)
    while not owner.drained:
        owner.poll(deadline=time.monotonic() + 1.0)
    assert owner.output == b"synthetic-buffered"
    owner.poll_discard()
    assert owner.refused and owner.output == b"" and owner.drained


def test_cleanup_overflow_retains_uncertain_debt_without_retry(pipes, monkeypatch):
    from hmp_plugin import presentation_pipes

    owner, result_write, _, result, diagnostic = pipes
    monkeypatch.setattr(presentation_pipes, "OUTPUT_LIMIT", 0)
    monkeypatch.setattr(presentation_pipes, "DIAGNOSTIC_LIMIT", 0)
    os.write(result_write, b"xxx")
    with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_LIMIT"):
        owner.poll_discard()
    assert owner.uncertain and not owner.drained
    assert not result.closed and not diagnostic.closed
    with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_REFUSED"):
        owner.poll_discard()


def test_outer_cleanup_deadline_can_only_shorten_allowance(pipes, monkeypatch):
    from hmp_plugin import presentation_pipes

    owner, _, _, result, diagnostic = pipes
    now = [10.0]
    monkeypatch.setattr(presentation_pipes.time, "monotonic", lambda: now[0])
    owner.poll_discard(deadline=10.1)
    owner.poll_discard(deadline=10.2)
    assert owner._cleanup_deadline == 10.1
    now[0] = 10.11
    with pytest.raises(FrameError, match="BI1_PIPE_CLEANUP_DEADLINE"):
        owner.poll_discard(deadline=20.0)
    assert owner._cleanup_deadline == 10.1
    assert not owner.drained and not result.closed and not diagnostic.closed
