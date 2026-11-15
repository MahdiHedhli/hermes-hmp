"""Disposable-child control input, not authentication or process custody.

A child must stay inert until its bounded input and exact GO match. Actual stream
reads can block; only the owning parent supervisor can enforce a hard deadline.
No filesystem operation, process launch or native grant occurs in this module.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import BinaryIO

from .presentation_input_v2 import decode_input_v2
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import INPUT_LIMIT, FrameError, decode_input


def _tick(clock: Callable[[], float], deadline: float) -> None:
    try:
        now = clock()
    except BaseException:
        raise FrameError("BI1_CONTROL_REFUSED") from None
    if (
        type(now) is not float
        or type(deadline) is not float
        or not 0 < deadline < float("inf")
        or not 0 <= now < deadline
    ):
        raise FrameError("BI1_CONTROL_REFUSED")


def _exact(stream: BinaryIO, count: int, clock: Callable[[], float], deadline: float) -> bytes:
    data = bytearray()
    while len(data) < count:
        _tick(clock, deadline)
        chunk = stream.read(count - len(data))
        if type(chunk) is not bytes or not chunk or len(chunk) > count - len(data):
            raise FrameError("BI1_CONTROL_REFUSED")
        data.extend(chunk)
        _tick(clock, deadline)
    return bytes(data)


def read_worker_go(
    stream: BinaryIO, *, clock: Callable[[], float], deadline: float
) -> dict[str, object]:
    """Read closed input +64-byte hex GO/newline +EOF, before any profile I/O.

    Matching challenges are solely a local job/IPC binding. The parent still
    has to prove its original native authority and own this actual child.
    """
    return _read_go(stream, clock=clock, deadline=deadline, decoder=decode_input)


def read_worker_go_v2(
    stream: BinaryIO, *, clock: Callable[[], float], deadline: float
) -> dict[str, object]:
    """Strict schema2 child input; never retry as the legacy schema1 codec."""
    return _read_go(stream, clock=clock, deadline=deadline, decoder=decode_input_v2)


def read_worker_go_v3(
    stream: BinaryIO, *, clock: Callable[[], float], deadline: float
) -> dict[str, object]:
    """Strict input3 only; no legacy path or fresh parent credits."""
    return _read_go(stream, clock=clock, deadline=deadline, decoder=decode_input_v3)


def _read_go(
    stream: BinaryIO,
    *,
    clock: Callable[[], float],
    deadline: float,
    decoder: Callable[[bytes], dict[str, object]],
) -> dict[str, object]:
    prefix = _exact(stream, 4, clock, deadline)
    size = struct.unpack(">I", prefix)[0]
    if size > INPUT_LIMIT:
        raise FrameError("BI1_CONTROL_REFUSED")
    row = decoder(prefix + _exact(stream, size, clock, deadline))
    original_deadline = row["deadline_ns"] / 1_000_000_000
    if original_deadline > deadline:
        raise FrameError("BI1_CONTROL_REFUSED")
    _tick(clock, original_deadline)
    go = _exact(stream, 65, clock, original_deadline)
    if go != row["challenge"].encode("ascii") + b"\n":
        raise FrameError("BI1_CONTROL_REFUSED")
    _tick(clock, original_deadline)
    if stream.read(1) != b"":
        raise FrameError("BI1_CONTROL_REFUSED")
    _tick(clock, original_deadline)
    return row
