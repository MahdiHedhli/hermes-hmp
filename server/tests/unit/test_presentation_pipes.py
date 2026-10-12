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
