"""Actual owned pipe composition; no process/profile/native authority claims."""

import os
import time

from hmp_plugin.presentation_go import GoHandoff
from hmp_plugin.presentation_jobs import encode_input
from hmp_plugin.presentation_worker_control import read_worker_go


def test_parent_one_use_go_is_consumed_by_actual_child_control_decoder():
    deadline = time.monotonic() + 2.0
    ns = int(deadline * 1_000_000_000)
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
        "deadline_ns": ns,
    }
    read, write = os.pipe()
    os.set_blocking(write, False)
    handle, child = object(), object()
    stream = None
    try:
        payload = encode_input(row)
        assert os.write(write, payload) == len(payload)
        sender = GoHandoff(handle=handle, child=child, fd=write, current=lambda: True)
        sender.send(handle, child, row["challenge"])
        os.close(write)
        write = -1
        stream = os.fdopen(read, "rb", buffering=0)
        read = -1
        assert read_worker_go(stream, clock=time.monotonic, deadline=deadline + 0.1) == row
    finally:
        if write >= 0:
            os.close(write)
        if read >= 0:
            os.close(read)
        if stream is not None:
            stream.close()
