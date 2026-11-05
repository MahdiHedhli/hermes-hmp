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
from dataclasses import dataclass
from io import FileIO
from typing import BinaryIO

from .presentation_go import GoHandoff
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import FrameError


def _native_close(stream: FileIO) -> None:
    """Exact fixed native boundary; never dispatch an instance close override."""
    if type(stream) is not FileIO:
        raise FrameError("BI1_CONTROL_CLOSE_UNCERTAIN")
    FileIO.close(stream)


@dataclass(frozen=True)
class ControlCloseObservation:
    """One owned local write-end close, never child/native/descendant closure."""

    descriptor: tuple[int, int, int]


class ControlAcquisitionError(FrameError):
    def __init__(self, owner: OwnedControlPipe, original: BaseException):
        super().__init__("BI1_CONTROL_PIPE_REFUSED")
        self.failed_owner = owner
        self._original = original


class OwnedControlPipe:
    def __init__(
        self, stream: BinaryIO, *, handle: object, child: object, current: Callable[[], bool]
    ):
        self._stream = self._stream_snapshot = stream
        self._handle = self._handle_snapshot = handle
        self._child = self._child_snapshot = child
        self._current = current
        self._lock = threading.Lock()
        self._input_attempted = False
        self._input_ready = False
        self._close_attempted = False
        self.closed = False
        self.uncertain = False
        self._deadline = 0.0
        self._work_refused = False
        self._resource_uncertain = False
        self._acquired = False
        self._identity = self._identity_snapshot = None
        self._close_observation: ControlCloseObservation | None = None
        self._close_observation_identity: ControlCloseObservation | None = None
        self._close_observation_snapshot: tuple[int, int, int] | None = None
        try:
            fd = FileIO.fileno(stream) if type(stream) is FileIO else stream.fileno()
            if type(fd) is not int or fd < 0:
                raise ValueError
            row = os.fstat(fd)
            if not stat.S_ISFIFO(row.st_mode):
                raise ValueError
            self._identity = self._identity_snapshot = (fd, row.st_dev, row.st_ino)
            os.set_blocking(fd, False)
            self._go = GoHandoff(
                handle=handle, child=child, fd=fd, current=self._current_go, write=self._write_go
            )
            self._acquired = True
        except BaseException as original:
            # Preserve this exact partial owner and its held stream/close history.
            self._mark_resource_uncertain()
            raise ControlAcquisitionError(self, original) from None

    def _mark_work_refused(self) -> None:
        self._work_refused = True
        self.uncertain = True  # legacy direct path stays conservative

    def _mark_resource_uncertain(self) -> None:
        self._resource_uncertain = True
        self._mark_work_refused()

    @property
    def work_refused(self) -> bool:
        return self._work_refused is True

    @property
    def resource_uncertain(self) -> bool:
        return self._resource_uncertain is not False

    def _bindings(self) -> None:
        if (
            self._stream is not self._stream_snapshot
            or self._handle is not self._handle_snapshot
            or self._child is not self._child_snapshot
            or self._identity is not self._identity_snapshot
            or type(self._identity) is not tuple
            or len(self._identity) != 3
            or any(type(value) is not int or value < 0 for value in self._identity)
        ):
            self._mark_resource_uncertain()
            raise FrameError("BI1_CONTROL_IDENTITY_REFUSED")

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._mark_work_refused()
            raise FrameError("BI1_CONTROL_REENTRY")
        if self.uncertain or self.closed:
            self._lock.release()
            raise FrameError("BI1_CONTROL_PIPE_REFUSED")

    def _fd(self) -> int:
        try:
            self._bindings()
            stream = self._stream_snapshot
            fd, device, inode = self._identity_snapshot
            observed_fd = FileIO.fileno(stream) if type(stream) is FileIO else stream.fileno()
            self._bindings()
            row = os.fstat(fd)
            if (
                type(observed_fd) is not int
                or observed_fd != fd
                or (row.st_dev, row.st_ino) != (device, inode)
                or os.get_blocking(fd) is not False
            ):
                raise FrameError("BI1_CONTROL_IDENTITY_REFUSED")
            return fd
        except BaseException:
            self._mark_resource_uncertain()
            raise FrameError("BI1_CONTROL_IDENTITY_REFUSED") from None

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
        held_fd = self._fd()
        now = time.monotonic()
        if (
            current is not True
            or self.uncertain
            or self.closed
            or not self._input_ready
            or fd != held_fd
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
            row = decode_input_v3(packet)
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
            self._mark_work_refused()
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
            self._mark_work_refused()
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_CONTROL_PIPE_UNCERTAIN") from None
        finally:
            self._lock.release()

    def _close(self) -> None:
        if self._close_attempted:
            self._mark_work_refused()
            raise FrameError("BI1_CONTROL_CLOSE_REFUSED")
        self._fd()
        stream = self._stream_snapshot
        self._bindings()
        self._close_attempted = True
        try:
            native_close = type(stream) is FileIO
            owned_native_close = native_close and FileIO.closefd.__get__(stream, FileIO) is True
            self._bindings()
            if native_close:
                _native_close(stream)
                closed = FileIO.closed.__get__(stream, FileIO)
            else:
                stream.close()  # legacy trusted wrapper support; no typed close fact
                closed = stream.closed
            self._bindings()
            if closed is not True:
                raise FrameError("BI1_CONTROL_CLOSE_UNCERTAIN")
        except BaseException:
            self._mark_resource_uncertain()
            raise
        self.closed = True
        if self._acquired is True and self._resource_uncertain is False and owned_native_close:
            self._close_observation = self._close_observation_identity = ControlCloseObservation(
                self._identity_snapshot
            )
            self._close_observation_snapshot = self._identity_snapshot

    def close_observation(self, handle: object, child: object) -> ControlCloseObservation:
        """Revalidate a known local close; work refusal never becomes GO authority."""
        if not self._lock.acquire(blocking=False):
            self._mark_resource_uncertain()
            raise FrameError("BI1_CONTROL_REENTRY")
        try:
            self._bindings()
            observation = self._close_observation
            if observation is not self._close_observation_identity:
                self._mark_resource_uncertain()
                raise FrameError("BI1_CONTROL_CLOSE_OBSERVATION_REFUSED")
            if (
                handle is not self._handle_snapshot
                or child is not self._child_snapshot
                or self._acquired is not True
                or self._resource_uncertain is not False
                or self.closed is not True
                or self._close_attempted is not True
                or type(observation) is not ControlCloseObservation
                or observation.descriptor is not self._close_observation_snapshot
                or observation.descriptor is not self._identity_snapshot
            ):
                raise FrameError("BI1_CONTROL_CLOSE_OBSERVATION_REFUSED")
            return observation
        finally:
            self._lock.release()

    def validates_close(
        self, handle: object, child: object, observation: ControlCloseObservation
    ) -> bool:
        return observation is self.close_observation(handle, child)

    def close_for_drain(self) -> None:
        # Drain may close a refused job's still-held stream, but never retry a
        # close with unknown outcome or guess a replaced descriptor.
        if not self._lock.acquire(blocking=False):
            self._mark_resource_uncertain()
            raise FrameError("BI1_CONTROL_REENTRY")
        try:
            self._close()
        except BaseException as error:
            self._mark_work_refused()
            if isinstance(error, FrameError):
                raise
            raise FrameError("BI1_CONTROL_CLOSE_UNCERTAIN") from None
        finally:
            self._lock.release()
