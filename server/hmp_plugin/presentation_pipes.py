"""Exclusive bounded result/diagnostic pipe reader; not process termination.

EOF/known close is recorded only from actual syscalls. Timeout or read/close
uncertainty retains ownership debt; this module never claims wait/group drain.
"""

from __future__ import annotations

import os
import select
import selectors
import stat
import time
from io import FileIO
from typing import BinaryIO

from .presentation_jobs import DIAGNOSTIC_LIMIT, OUTPUT_LIMIT, FrameError


def _close_local_file(stream: FileIO, identity: tuple[int, int, int]) -> None:
    if type(stream) is not FileIO or FileIO.closefd.__get__(stream, FileIO) is not True:
        raise FrameError("BI1_PIPE_LOCAL_CLOSE_REFUSED")
    if (
        type(identity) is not tuple
        or len(identity) != 3
        or any(type(v) is not int or v < 0 for v in identity)
    ):
        raise FrameError("BI1_PIPE_LOCAL_CLOSE_REFUSED")
    fd = FileIO.fileno(stream)
    row = os.fstat(fd)
    if (fd, row.st_dev, row.st_ino) != identity:
        raise FrameError("BI1_PIPE_LOCAL_CLOSE_REFUSED")
    FileIO.close(stream)
    if FileIO.closed.__get__(stream, FileIO) is not True:
        raise FrameError("BI1_PIPE_LOCAL_CLOSE_UNCERTAIN")


def _selector_recipe(selector: object) -> tuple | None:
    for class_name, native_name in (("KqueueSelector", "kqueue"), ("EpollSelector", "epoll")):
        cls, native_type = getattr(selectors, class_name, None), getattr(select, native_name, None)
        if cls is not None and native_type is not None and type(selector) is cls:
            native = selector._selector
            mapping = selector._fd_to_key
            if type(native) is not native_type or type(mapping) is not dict:
                return None
            fd = native_type.fileno(native)
            if type(fd) is not int or fd < 0:
                return None
            row = os.fstat(fd)
            return (
                selector,
                cls,
                native,
                native_type,
                cls.close,
                mapping,
                (fd, row.st_dev, row.st_ino),
                cls.unregister,
            )
    return None


def _close_local_selector(selector: object, close_call: object) -> None:
    # Fixed concrete stdlib function captured at acquisition, no instance override.
    close_call(selector)


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
        self._selector_recipe = self._selector_recipe_snapshot = None
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
        self._cleanup_deadline: float | None = None
        self._cleanup_mode: str | None = None
        self._local_cleanup_scope: tuple | None = None
        self._local_cleanup_snapshot: tuple | None = None
        self._local_cleanup_end_ns: int | None = None
        self._discarded_bytes = 0
        try:
            self._selector = selectors.DefaultSelector()
            self._selector_recipe = self._selector_recipe_snapshot = _selector_recipe(
                self._selector
            )
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
            if self._cleanup_mode == "local":
                recipe = self._selector_recipe
                if (
                    recipe is not self._selector_recipe_snapshot
                    or type(recipe) is not tuple
                    or len(recipe) != 8
                ):
                    raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_REFUSED")
                held, cls, native, native_type, close_call, mapping, identity, _unregister = recipe
                if (
                    self._selector is not held
                    or type(held) is not cls
                    or held._selector is not native
                    or type(native) is not native_type
                    or held._fd_to_key is not mapping
                    or type(mapping) is not dict
                    or mapping
                ):
                    raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_REFUSED")
                fd = native_type.fileno(native)
                row = os.fstat(fd)
                if (fd, row.st_dev, row.st_ino) != identity:
                    raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_REFUSED")
                _close_local_selector(held, close_call)
                if (
                    self._selector is not held
                    or held._selector is not native
                    or native_type.closed.__get__(native, native_type) is not True
                    or held._fd_to_key is not mapping
                    or mapping
                    or held._map is not None
                ):
                    raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_UNCERTAIN")
            else:
                self._selector.close()
        except BaseException:
            self.uncertain = True
            raise
        self._selector_closed = True

    @property
    def output(self) -> bytes:
        return bytes(self._output)

    @property
    def output_discarded(self) -> bool:
        return self._cleanup_deadline is not None and self.refused and not self._output

    @property
    def drained(self) -> bool:
        return (
            not self.uncertain
            and self._closed == self._eof == {"result", "diagnostic"}
            and self._selector_closed
        )

    def _identity(self, name: str) -> int:
        if (
            type(name) is not str
            or name not in ("result", "diagnostic")
            or type(self._identities) is not dict
            or type(self._streams) is not dict
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_IDENTITY_REFUSED")
        if any(type(key) is not str for key in self._identities) or set(self._identities) != {
            "result",
            "diagnostic",
        }:
            self.uncertain = True
            raise FrameError("BI1_PIPE_IDENTITY_REFUSED")
        identity = self._identities[name]
        if (
            type(identity) is not tuple
            or len(identity) != 3
            or any(type(value) is not int or value < 0 for value in identity)
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_IDENTITY_REFUSED")
        fd, device, inode = identity
        stream = self._streams[name]
        if self._cleanup_mode == "local":
            if type(stream) is not FileIO or FileIO.closefd.__get__(stream, FileIO) is not True:
                self.uncertain = True
                raise FrameError("BI1_PIPE_IDENTITY_REFUSED")
            observed_fd = FileIO.fileno(stream)
        else:
            observed_fd = stream.fileno()
        row = os.fstat(fd)
        if (
            type(observed_fd) is not int
            or observed_fd != fd
            or (row.st_dev, row.st_ino) != (device, inode)
        ):
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

    def poll_discard(self, *, deadline: float | None = None) -> None:
        """Bounded cleanup only; caller must establish child/group exit first.

        This never restores result-read authority. The first call permanently
        refuses output and starts one nonrenewable 250 ms cleanup allowance.
        Timeout/overflow/descriptor uncertainty retains the exact cleanup debt.
        """
        if self._cleanup_mode is None:
            self._cleanup_mode = "direct"
        elif type(self._cleanup_mode) is not str or self._cleanup_mode != "direct":
            raise FrameError("BI1_PIPE_CLEANUP_MODE_REFUSED")
        self._poll_discard_io(deadline=deadline)

    def _validate_local_closed_facts(self) -> None:
        # Legacy poll flags are NOT native local-close proof. Validate adoption.
        if (
            type(self._closed) is not set
            or any(
                type(name) is not str or name not in ("result", "diagnostic")
                for name in self._closed
            )
            or type(self._selector_closed) is not bool
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_LOCAL_CLOSE_UNCERTAIN")
        for name in self._closed:
            stream = self._streams[name]
            if (
                type(stream) is not FileIO
                or FileIO.closefd.__get__(stream, FileIO) is not True
                or FileIO.closed.__get__(stream, FileIO) is not True
            ):
                self.uncertain = True
                raise FrameError("BI1_PIPE_LOCAL_CLOSE_UNCERTAIN")
        if self._selector_closed:
            recipe = self._selector_recipe
            if (
                recipe is not self._selector_recipe_snapshot
                or type(recipe) is not tuple
                or len(recipe) != 8
            ):
                self.uncertain = True
                raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_UNCERTAIN")
            held, cls, native, native_type, _close_call, mapping, _identity, _unregister = recipe
            if (
                self._selector is not held
                or type(held) is not cls
                or held._selector is not native
                or type(native) is not native_type
                or native_type.closed.__get__(native, native_type) is not True
                or held._fd_to_key is not mapping
                or type(mapping) is not dict
                or mapping
                or held._map is not None
            ):
                self.uncertain = True
                raise FrameError("BI1_LOCAL_SELECTOR_CLOSE_UNCERTAIN")

    def poll_local_discard(
        self,
        *,
        process: object,
        binding: object,
        control: object,
        control_fact: object,
        cleanup_end_ns: int,
    ) -> None:
        """Local-FD EOF/close only; never group/native/descendant/slot closure.

        Requires exact child wait and its own native control-close observation.
        A surviving writer can time out/overflow; no terminal release follows.
        Caller freezes the same end before all cleanup planes, never per poll.
        """
        from .presentation_broker_child import BrokerChildOwner
        from .presentation_control_pipe import ControlCloseObservation, OwnedControlPipe

        if type(self) is not OwnedPresentationPipes:
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        self.refused = True
        self._output[:] = b"\x00" * len(self._output)
        self._output.clear()
        if (
            type(process) is not BrokerChildOwner
            or type(control) is not OwnedControlPipe
            or type(control_fact) is not ControlCloseObservation
            or type(cleanup_end_ns) is not int
            or not 0 < cleanup_end_ns < (1 << 63)
            or self.uncertain
        ):
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        if self._cleanup_mode is None:
            self._cleanup_mode = "local"
            self._local_cleanup_scope = self._local_cleanup_snapshot = (
                process,
                binding,
                control,
                control_fact,
            )
            self._local_cleanup_end_ns = cleanup_end_ns
        elif (
            type(self._cleanup_mode) is not str
            or self._cleanup_mode != "local"
            or self._local_cleanup_scope is not self._local_cleanup_snapshot
            or type(self._local_cleanup_scope) is not tuple
            or len(self._local_cleanup_scope) != 4
            or any(
                a is not b
                for a, b in zip(
                    self._local_cleanup_scope,
                    (process, binding, control, control_fact),
                    strict=True,
                )
            )
            or type(self._local_cleanup_end_ns) is not int
            or cleanup_end_ns != self._local_cleanup_end_ns
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_SCOPE_REFUSED")
        now = time.monotonic_ns()
        if not now < cleanup_end_ns <= now + 250_000_000:
            self.uncertain = True
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_DEADLINE")
        if not process.owns(binding):
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        waited = process.terminal_wait(binding)
        if not process.validates_wait(binding, waited) or process.signals_retired is not True:
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        streams = process.streams
        if (
            type(self._streams) is not dict
            or any(type(key) is not str for key in self._streams)
            or set(self._streams) != {"result", "diagnostic"}
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        if (
            self._streams["result"] is not streams.result
            or self._streams["diagnostic"] is not streams.diagnostic
            or control._stream_snapshot is not streams.control
            or not control.validates_close(binding, process, control_fact)
        ):
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        self._validate_local_closed_facts()
        if time.monotonic_ns() >= cleanup_end_ns:
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_DEADLINE")
        self._poll_discard_io(deadline=cleanup_end_ns / 1_000_000_000)
        self._validate_local_closed_facts()
        if (
            not process.owns(binding)
            or not process.validates_wait(binding, waited)
            or not control.validates_close(binding, process, control_fact)
        ):
            self.uncertain = True
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
        if time.monotonic_ns() >= cleanup_end_ns:
            raise FrameError("BI1_PIPE_LOCAL_CLEANUP_DEADLINE")

    def _poll_discard_io(self, *, deadline: float | None = None) -> None:
        """Common bounded FD I/O; callers retain their DISTINCT proof contracts."""
        if self.uncertain:
            raise FrameError("BI1_PIPE_CLEANUP_REFUSED")
        now = time.monotonic()
        if deadline is not None and (
            type(deadline) is not float or not now < deadline < float("inf")
        ):
            raise FrameError("BI1_PIPE_CLEANUP_DEADLINE")
        if self._cleanup_deadline is None:
            self._cleanup_deadline = (
                min(now + 0.25, deadline) if deadline is not None else now + 0.25
            )
            self.refused = True
            self._output[:] = b"\x00" * len(self._output)
            self._output.clear()
        elif deadline is not None:
            self._cleanup_deadline = min(self._cleanup_deadline, deadline)
        if self.drained:
            return
        if now >= self._cleanup_deadline:
            raise FrameError("BI1_PIPE_CLEANUP_DEADLINE")
        try:
            for name in self._streams.keys() - self._closed:
                self._identity(name)
            for key, _ in self._selector.select(0):
                if time.monotonic() >= self._cleanup_deadline:
                    raise FrameError("BI1_PIPE_CLEANUP_DEADLINE")
                name = key.data
                fd = self._identity(name)
                remaining = OUTPUT_LIMIT + DIAGNOSTIC_LIMIT + 2 - self._discarded_bytes
                try:
                    chunk = os.read(fd, min(65536, remaining + 1))
                except BlockingIOError:
                    continue
                self._discarded_bytes += len(chunk)
                if len(chunk) > remaining:
                    self.uncertain = True
                    raise FrameError("BI1_PIPE_CLEANUP_LIMIT")
                if chunk:
                    continue
                self._eof.add(name)
                if self._cleanup_mode == "local":
                    held_streams, held_identities = self._streams, self._identities
                    stream = held_streams[name]
                    identity = held_identities[name]
                    recipe = self._selector_recipe
                    if (
                        recipe is not self._selector_recipe_snapshot
                        or type(recipe) is not tuple
                        or len(recipe) != 8
                        or self._selector is not recipe[0]
                    ):
                        raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
                    recipe[7](recipe[0], fd)  # captured concrete unregister, not instance callback
                    if (
                        self._streams is not held_streams
                        or self._identities is not held_identities
                        or any(type(key) is not str for key in held_streams)
                        or any(type(key) is not str for key in held_identities)
                        or held_streams[name] is not stream
                        or held_identities[name] is not identity
                    ):
                        raise FrameError("BI1_PIPE_LOCAL_CLEANUP_REFUSED")
                    _close_local_file(stream, identity)
                    if (
                        self._streams is not held_streams
                        or any(type(key) is not str for key in held_streams)
                        or held_streams[name] is not stream
                        or FileIO.closed.__get__(stream, FileIO) is not True
                    ):
                        raise FrameError("BI1_PIPE_LOCAL_CLOSE_UNCERTAIN")
                else:
                    self._selector.unregister(fd)
                    self._streams[name].close()
                self._closed.add(name)
            if self._closed == {"result", "diagnostic"}:
                self._close_selector()
        except FrameError:
            if self._cleanup_mode == "local":
                self.uncertain = True
            raise
        except BaseException:
            self.uncertain = True
            raise FrameError("BI1_PIPE_CLEANUP_UNCERTAIN") from None
