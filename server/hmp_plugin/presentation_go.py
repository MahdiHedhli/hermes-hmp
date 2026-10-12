"""One synchronous GO write on an explicitly owned child control pipe.

No pipe/process is created here. A child marker/FD/challenge is not authorization;
only ParentAuthorityAdapter.go_inline may invoke this after native reauthorization.
Partial/uncertain write poisons the handoff and is never retried.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Callable

from .presentation_jobs import FrameError


def _pipe_info(fd: int) -> tuple[int, int, int, bool]:
    row = os.fstat(fd)
    return row.st_dev, row.st_ino, row.st_mode, os.get_blocking(fd)


class GoHandoff:
    def __init__(
        self,
        *,
        handle: object,
        child: object,
        fd: int,
        current: Callable[[], bool],
        write: Callable[[int, bytes], int] = os.write,
        pipe_info: Callable[[int], tuple[int, int, int, bool]] = _pipe_info,
    ):
        if handle is None or child is None or type(fd) is not int or fd < 0:
            raise FrameError("BI1_GO_REFUSED")
        try:
            info = pipe_info(fd)
        except BaseException:
            raise FrameError("BI1_GO_REFUSED") from None
        if (
            type(info) is not tuple
            or len(info) != 4
            or any(type(value) is not int or value < 0 for value in info[:3])
            or not stat.S_ISFIFO(info[2])
            or info[3] is not False
        ):
            raise FrameError("BI1_GO_REFUSED")
        self._pipe_info = pipe_info
        self._pipe_identity = info
        self._handle = handle
        self._child = child
        self._fd = fd
        self._current = current
        self._write = write
        self._attempted = False

    def send(self, handle: object, child: object, challenge: str) -> None:
        if (
            handle is not self._handle
            or child is not self._child
            or self._attempted
            or type(challenge) is not str
            or len(challenge) != 64
            or any(c not in "0123456789abcdef" for c in challenge)
        ):
            raise FrameError("BI1_GO_REFUSED")
        try:
            current = self._current()
            same_pipe = self._pipe_info(self._fd) == self._pipe_identity
        except BaseException:
            raise FrameError("BI1_GO_REFUSED") from None
        if current is not True or not same_pipe:
            raise FrameError("BI1_GO_REFUSED")
        self._attempted = True  # before syscall: an exception can follow an actual write
        try:
            count = self._write(self._fd, challenge.encode("ascii") + b"\n")
        except BaseException:
            raise FrameError("BI1_GO_UNCERTAIN") from None
        if type(count) is not int or count != 65:
            raise FrameError("BI1_GO_UNCERTAIN")
