"""Closed completion correlation DATA; never cleanup or release permission."""
import base64

import pytest

from hmp_plugin.presentation_credential_cleanup_claim import _Expected, _match
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_terminal_claim import (
    CleanupStamp,
    StartedClaim,
    claim_binding,
    decode_handoff,
    encode_handoff,
)

from .test_presentation_broker_service import binding


@pytest.fixture
def correlated():
    c = StartedClaim(claim_binding(binding()), "alpha", "METADATA", 2_000_000_000,
        "f" * 64, 1, "a" * 64, "b" * 64, "c" * 64, "d" * 64, "OK", 0, "e" * 64)
    expected = _Expected(c.binding, c.profile, c.operation_kind, c.deadline_ns,
        c.challenge, c.epoch, c.input_sha256, c.worker_source_sha256,
        c.installation_generation, c.clock_domain_sha256, c.result_sha256)
    return c, expected


def test_matching_closed_claim_is_only_data(correlated):
    c, expected = correlated
    handoff = decode_handoff(encode_handoff(c))
    assert _match(expected, handoff) is None
    assert not hasattr(handoff, "release")
    assert not hasattr(handoff, "inherit")


@pytest.mark.parametrize("field,value", [
    ("profile", "beta"), ("operation_kind", "AVATAR"), ("deadline_ns", 2_000_000_001),
    ("challenge", "0" * 64), ("epoch", 2), ("input_sha256", "0" * 64),
    ("worker_source_sha256", "0" * 64), ("installation_generation", "0" * 64),
    ("clock_domain_sha256", "0" * 64), ("result_sha256", "0" * 64),
])
def test_each_original_context_mismatch_refuses(correlated, field, value):
    c, expected = correlated
    handoff = decode_handoff(encode_handoff(c._replace(**{field: value})))
    with pytest.raises(FrameError):
        _match(expected, handoff)


@pytest.mark.parametrize("field", ["iid", "listener", "broker", "channel", "operation"])
def test_each_binding_mismatch_refuses(correlated, field):
    c, expected = correlated
    value = (base64.b32encode(b"\x01" * 32).decode().rstrip("=").lower()
             if field == "iid" else "0" * (32 if field == "listener" else 64))
    changed = c.binding._replace(**{field: value})
    handoff = decode_handoff(encode_handoff(c._replace(binding=changed)))
    with pytest.raises(FrameError):
        _match(expected, handoff)


def test_aborted_after_completed_result_is_not_accepted(correlated):
    c, expected = correlated
    aborted = c._replace(outcome="ABORTED", result_sha256=None)
    handoff = decode_handoff(encode_handoff(aborted, CleanupStamp(0, 250_000_000)))
    with pytest.raises(FrameError):
        _match(expected, handoff)


def test_matching_cleanup_stamp_is_not_adopted(correlated):
    c, expected = correlated
    handoff = decode_handoff(encode_handoff(c, CleanupStamp(0, 250_000_000)))
    assert _match(expected, handoff) is None
    assert handoff.cleanup.end_ns == 250_000_000
    assert not hasattr(handoff, "inherit")
