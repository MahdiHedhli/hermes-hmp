"""Exclusive bounded result/diagnostic pipe reader; not process termination.

EOF/known close is recorded only from actual syscalls. Timeout or read/close
uncertainty retains ownership debt; this module never claims wait/group drain.
"""

from __future__ import annotations

import os
import selectors
import stat
import time
from typing import BinaryIO

from .presentation_jobs import DIAGNOSTIC_LIMIT, OUTPUT_LIMIT, FrameError


class PipeAcquisitionError(FrameError):
    """Closed failure retaining the exact owner and ambiguous cleanup debt."""

    def __init__(
        self, owner: OwnedPresentationPipes, original: BaseException, cleanup: BaseException | None
    ):
        super().__init__("BI1_PIPE_ACQUISITION_REFUSED")
        self.failed_owner = owner
        self._original = original
        self._cleanup = cleanup


class OwnedPresentationPipes:
    def __init__(self, result: BinaryIO, diagnostic: BinaryIO):
        self._selector = None
        self._streams = {"result": result, "diagnostic": diagnostic}
        self._identities: dict[str, tuple[int, int, int]] = {}
        self._eof: set[str] = set()
        self._closed: set[str] = set()
        self._output = bytearray()
        self.diagnostic_bytes = 0
        self.uncertain = False
        self.refused = False
        self._selector_closed = False
        self._selector_close_attempted = False
        try:
            self._selector = selectors.DefaultSelector()
            fds = [stream.fileno() for stream in self._streams.values()]
            if len(set(fds)) != 2:
                raise ValueError
            for name, stream in self._streams.items():
                fd = stream.fileno()
                row = os.fstat(fd)
                if not stat.S_ISFIFO(row.st_mode):
                    raise ValueError
                self._identities[name] = (fd, row.st_dev, row.st_ino)
                os.set_blocking(fd, False)
                self._selector.register(fd, selectors.EVENT_READ, name)
        except BaseException as original:
            # Caller retains both supplied stream records on failed acquisition.
            self.uncertain = True
            cleanup = None
            if self._selector is not None:
                try:
                    self._close_selector()
                except BaseException as error:
                    cleanup = error
            raise PipeAcquisitionError(self, original, cleanup) from None

    def _close_selector(self) -> None:
        if self._selector_close_attempted or self._selector is None:
            self.uncertain = True
            raise FrameError("BI1_SELECTOR_CLOSE_REFUSED")
        self._selector_close_attempted = True
        try:
            self._selector.close()
        except BaseException:
            self.uncertain = True
            raise
        self._selector_closed = True

    @property
    def output(self) -> bytes:
        return bytes(self._output)

    @property
    def drained(self) -> bool:
        return (
            not self.uncertain
            and self._closed == self._eof == {"result", "diagnostic"}
            and self._selector_closed
        )

    def _identity(self, name: str) -> int:
        fd, device, inode = self._identities[name]
        stream = self._streams[name]
        row = os.fstat(fd)
        if stream.fileno() != fd or (row.st_dev, row.st_ino) != (device, inode):
            self.uncertain = True
            raise FrameError("BI1_PIPE_IDENTITY_REFUSED")
        return fd

    def poll(self, *, deadline: float) -> None:
        if self.uncertain or self.refused or self.drained:
            raise FrameError("BI1_PIPE_POLL_REFUSED")
        now = time.monotonic()
        if type(deadline) is not float or not now < deadline < float("inf"):
            self.refused = True
            raise FrameError("BI1_PIPE_DEADLINE")
        try:
            # Closed/replaced descriptors can silently disappear from selectors.
            # Validate every retained stream, even when no readiness event fires.
            for name in self._streams.keys() - self._closed:
                self._identity(name)
            for key, _ in self._selector.select(min(deadline - now, 0.05)):
                if time.monotonic() >= deadline:
                    self.refused = True
                    raise FrameError("BI1_PIPE_DEADLINE")
                name = key.data
                fd = self._identity(name)
                remaining = (
                    OUTPUT_LIMIT - len(self._output)
                    if name == "result"
                    else DIAGNOSTIC_LIMIT - self.diagnostic_bytes
                )
                try:
                    chunk = os.read(fd, min(65536, remaining + 1))
                except BlockingIOError:
                    continue
                if len(chunk) > remaining:
                    self.refused = True
                    raise FrameError("BI1_PIPE_LIMIT")
                if chunk:
                    if name == "result":
                        self._output.extend(chunk)
                    else:
                        self.diagnostic_bytes += len(chunk)
                    continue
                self._eof.add(name)
                self._selector.unregister(fd)
                # Close exactly once. An exception is unknown, never retried.
                self._streams[name].close()
                self._closed.add(name)
            if self._closed == {"result", "diagnostic"}:
                self._close_selector()
        except FrameError:
            raise
        except BaseException:
            self.uncertain = True
            raise FrameError("BI1_PIPE_UNCERTAIN") from None
