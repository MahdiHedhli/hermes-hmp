import os
import time

import pytest

from hmp_plugin.presentation_control_pipe import OwnedControlPipe
from hmp_plugin.presentation_input_v2 import encode_input_v2
from hmp_plugin.presentation_jobs import FrameError


def packet():
    return encode_input_v2(
        {
            "schema": 2,
            "challenge": "a" * 64,
            "epoch": 1,
            "profile": "default",
            "root": "/srv/hermes",
            "home": "/srv/hermes",
            "operation": "METADATA",
            "expected_avatar_sha": None,
            "uid": 501,
            "gid": 20,
            "dir_modes": [448, 488, 493],
            "leaf_modes": [384, 416, 420],
            "source_manifest_sha": "b" * 64,
            "deadline_ns": int((time.monotonic() + 1) * 1e9),
            "directory_policy": [[0, 0, 493], [0, 0, 493], [501, 20, 448]],
            "iid": "a" * 52,
            "canonical_fallback": "Hermes",
            "observed_at": 100,
        }
    )


@pytest.fixture
def pipe():
    read, write = os.pipe()
    stream = os.fdopen(write, "wb", buffering=0)
    handle, child = object(), object()
    owner = OwnedControlPipe(stream, handle=handle, child=child, current=lambda: True)
    yield owner, read, stream, handle, child
    if not stream.closed:
        stream.close()
    os.close(read)


def test_input_then_exact_go_and_actual_eof(pipe):
    owner, read, stream, handle, child = pipe
    data = packet()
    owner.write_input(data)
    owner.send_go(handle, child, "a" * 64)
    assert os.read(read, 8192) == data + b"a" * 64 + b"\n"
    assert os.read(read, 1) == b"" and stream.closed and owner.closed


def test_wrong_go_and_duplicate_input_cannot_replay(pipe):
    owner, read, _, handle, child = pipe
    data = packet()
    owner.write_input(data)
    with pytest.raises(FrameError):
        owner.write_input(data)
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)
    owner.close_for_drain()
    assert os.read(read, 8192) == data
    assert os.read(read, 1) == b""


def test_caught_current_callback_reentry_prevents_any_input_effect(pipe):
    owner, read, _, _, _ = pipe

    def reenter():
        with pytest.raises(FrameError):
            owner.write_input(packet())
        return True

    owner._current = reenter
    with pytest.raises(FrameError):
        owner.write_input(packet())
    owner.close_for_drain()
    assert os.read(read, 1) == b""


def test_changed_blocking_flag_refuses_before_input_write(pipe):
    owner, read, stream, _, _ = pipe
    os.set_blocking(stream.fileno(), True)
    with pytest.raises(FrameError):
        owner.write_input(packet())
    assert owner.uncertain
    os.set_blocking(stream.fileno(), False)
    owner.close_for_drain()
    assert os.read(read, 1) == b""
