"""Actual closed-frame/GO stream checks, no files or processes."""

import io
import struct

import pytest

from hmp_plugin.presentation_jobs import FrameError, encode_input
from hmp_plugin.presentation_worker_control import read_worker_go


def packet():
    row = {
        "schema": 1,
        "challenge": "a" * 64,
        "epoch": 1,
        "profile": "default",
        "root": "/synthetic/hermes",
        "home": "/synthetic/hermes",
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": 501,
        "gid": 20,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": "b" * 64,
        "deadline_ns": 2_000_000_000,
    }
    return row, encode_input(row)


def test_closed_input_and_exact_go_returns_same_scope():
    row, body = packet()
    assert (
        read_worker_go(io.BytesIO(body + b"a" * 64 + b"\n"), clock=lambda: 1.0, deadline=2.0) == row
    )


@pytest.mark.parametrize(
    "suffix", [b"", b"b" * 64 + b"\n", b"a" * 64 + b"!", b"a" * 64 + b"\nEXTRA"]
)
def test_missing_wrong_or_extra_go_refuses(suffix):
    _, body = packet()
    with pytest.raises(FrameError):
        read_worker_go(io.BytesIO(body + suffix), clock=lambda: 1.0, deadline=2.0)


def test_oversize_prefix_is_refused_before_body_read():
    class HeaderOnly(io.BytesIO):
        def read(self, count):
            assert self.tell() == 0 and count == 4
            return super().read(count)

    with pytest.raises(FrameError):
        read_worker_go(HeaderOnly(struct.pack(">I", 8193)), clock=lambda: 1.0, deadline=2.0)


def test_original_deadline_cannot_be_extended_by_worker():
    _, body = packet()
    with pytest.raises(FrameError):
        read_worker_go(io.BytesIO(body + b"a" * 64 + b"\n"), clock=lambda: 1.0, deadline=1.5)
