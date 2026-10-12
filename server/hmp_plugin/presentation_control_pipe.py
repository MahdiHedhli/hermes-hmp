"""One owned nonblocking input/GO pipe, separate from native permission.

Caller owns the actual process and any thread executing bounded input writes.
Only original native PRE_GO may invoke send_go. Close uncertainty is never retried.
"""

from __future__ import annotations

import os
import select
import stat
import threading
import time
from collections.abc import Callable
from typing import BinaryIO

from .presentation_go import GoHandoff
from .presentation_input_v2 import decode_input_v2
from .presentation_jobs import FrameError


class OwnedControlPipe:
    def __init__(
        self, stream: BinaryIO, *, handle: object, child: object, current: Callable[[], bool]
    ):
        self._stream = stream
        self._handle = handle
        self._child = child
        self._current = current
        self._lock = threading.Lock()
        self._input_attempted = False
        self._input_ready = False
        self._close_attempted = False
        self.closed = False
        self.uncertain = False
        self._deadline = 0.0
        try:
            fd = stream.fileno()
            row = os.fstat(fd)
            if not stat.S_ISFIFO(row.st_mode):
                raise ValueError
            self._identity = (fd, row.st_dev, row.st_ino)
            os.set_blocking(fd, False)
            self._go = GoHandoff(
                handle=handle, child=child, fd=fd, current=self._current_go, write=self._write_go
            )
        except BaseException:
            # No additional FD was acquired; caller retains this exact stream.
            self.uncertain = True
            raise FrameError("BI1_CONTROL_PIPE_REFUSED") from None

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self.uncertain = True
            raise FrameError("BI1_CONTROL_REENTRY")
        if self.uncertain or self.closed:
            self._lock.release()
            raise FrameError("BI1_CONTROL_PIPE_REFUSED")

    def _fd(self) -> int:
        fd, device, inode = self._identity
        row = os.fstat(fd)
        if (
            self._stream.fileno() != fd
            or (row.st_dev, row.st_ino) != (device, inode)
            or os.get_blocking(fd) is not False
        ):
            self.uncertain = True
            raise FrameError("BI1_CONTROL_IDENTITY_REFUSED")
        return fd

    def _current_go(self) -> bool:
        current = self._current()
        return (
            current is True
            and not self.uncertain
            and not self.closed
            and self._input_ready
            and time.monotonic() < self._deadline
        )

    def _write_go(self, fd: int, data: bytes) -> int:
        # GoHandoff already checked its pipe identity. This owner-aware fence
        # follows those callbacks and precedes the actual one-use syscall.
        current = self._current()
        now = time.monotonic()
        if (
            current is not True
            or self.uncertain
            or self.closed
            or not self._input_ready
            or fd != self._identity[0]
            or now >= self._deadline
        ):
            raise FrameError("BI1_CONTROL_GO_REFUSED")
        return os.write(fd, data)

    def write_input(self, packet: bytes) -> None:
        self._enter()
        try:
            if self._input_attempted:
                raise FrameError("BI1_CONTROL_INPUT_REFUSED")
            self._input_attempted = True
            if type(packet) is not bytes:
                raise FrameError("BI1_CONTROL_INPUT_REFUSED")
            row = decode_input_v2(packet)
            self._deadline = row["deadline_ns"] / 1_000_000_000
            self._challenge = row["challenge"]
            offset = 0
            while offset < len(packet):
                current = self._current()
                now = time.monotonic()
                if current is not True or self.uncertain or not now < self._deadline:
                    raise FrameError("BI1_CONTROL_INPUT_REFUSED")
                fd = self._fd()
                if self.uncertain or time.monotonic() >= self._deadline:
                    raise FrameError("BI1_CONTROL_INPUT_REFUSED")
                try:
                    count = os.write(fd, packet[offset:])
                except BlockingIOError:
                    select.select([], [fd], [], min(0.05, self._deadline - now))
                    continue
                if type(count) is not int or not 0 < count <= len(packet) - offset:
                    raise FrameError("BI1_CONTROL_INPUT_UNCERTAIN")
                offset += count
            now = time.monotonic()
            if self.uncertain or now >= self._deadline:
                raise FrameError("BI1_CONTROL_INPUT_REFUSED")
            self._input_ready = True
        except BaseException as error:
            self.uncertain = True
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_CONTROL_PIPE_UNCERTAIN") from None
        finally:
            self._lock.release()

    def send_go(self, handle: object, child: object, challenge: str) -> None:
        self._enter()
        try:
            if not self._input_ready or challenge != self._challenge:
                raise FrameError("BI1_CONTROL_GO_REFUSED")
            self._go.send(handle, child, challenge)
            now = time.monotonic()
            if self.uncertain or now >= self._deadline:
                raise FrameError("BI1_CONTROL_GO_UNCERTAIN")
            self._close()
            now = time.monotonic()
            if self.uncertain or now >= self._deadline:
                raise FrameError("BI1_CONTROL_GO_UNCERTAIN")
        except BaseException as error:
            self.uncertain = True
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_CONTROL_PIPE_UNCERTAIN") from None
        finally:
            self._lock.release()

    def _close(self) -> None:
        if self._close_attempted:
            self.uncertain = True
            raise FrameError("BI1_CONTROL_CLOSE_REFUSED")
        self._fd()
        self._close_attempted = True
        try:
            self._stream.close()
        except BaseException:
            self.uncertain = True
            raise
        self.closed = True

    def close_for_drain(self) -> None:
        # Drain may close a refused job's still-held stream, but never retry a
        # close with unknown outcome or guess a replaced descriptor.
        if not self._lock.acquire(blocking=False):
            self.uncertain = True
            raise FrameError("BI1_CONTROL_REENTRY")
        try:
            self._close()
        except BaseException as error:
            self.uncertain = True
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_CONTROL_CLOSE_UNCERTAIN") from None
        finally:
            self._lock.release()
