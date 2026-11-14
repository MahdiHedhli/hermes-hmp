"""Source-only shared-group child custody. Never group or remote closure proof.

Caller must strongly retain every owner (including failures) before launch until
qualified retirement. Runtime exclusive reaper, no-spawn worker/code provenance,
service containment and pipe/native closure remain separate activation gates.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, replace
from typing import BinaryIO

from .presentation_child_launch import ChildLaunch, child_launch
from .presentation_jobs import FrameError

# Fixed trusted-runtime primitives, not request-selected constructors. Separate
# allocation lets the owner retain a partial handle before initializer effects.
_POPEN_TYPE = subprocess.Popen
_POPEN_NEW = _POPEN_TYPE.__new__
_POPEN_INIT = _POPEN_TYPE.__init__


def _allocate_popen() -> subprocess.Popen:
    return _POPEN_NEW(_POPEN_TYPE)


def _initialize_popen(child: subprocess.Popen, *args, **kwargs) -> None:
    if type(child) is not _POPEN_TYPE:
        raise FrameError("BI1_BROKER_CHILD_NATIVE_HANDLE_REFUSED")
    _POPEN_INIT(child, *args, **kwargs)


def _empty_active() -> list:
    # Necessary observation only: fresh standalone startup, no foreign
    # constructors/reapers and strong retention remain qualification premises.
    active = getattr(subprocess, "_active", None)
    if type(active) is not list or len(active) != 0:
        raise FrameError("BI1_BROKER_CHILD_RUNTIME_REFUSED")
    return active


@dataclass(frozen=True)
class BrokerReaderStreams:
    control: BinaryIO
    result: BinaryIO
    diagnostic: BinaryIO


@dataclass(frozen=True)
class ChildWaitObservation:
    raw_status: int
    exit_code: int


class BrokerChildLaunchError(FrameError):
    def __init__(self, owner: BrokerChildOwner, original: BaseException):
        super().__init__("BI1_BROKER_CHILD_LAUNCH_UNCERTAIN")
        self.failed_owner = owner
        self._original = original


class BrokerChildOwner:
    """One exact direct child; no route, Popen exposure or group signal API."""

    def __init__(
        self, binding: object, *, parser_package: str | None = None, deadline_ns: int | None = None
    ):
        if binding is None:
            raise FrameError("BI1_BROKER_CHILD_BINDING_REFUSED")
        if deadline_ns is not None and (
            type(deadline_ns) is not int or not 0 < deadline_ns < (1 << 63)
        ):
            raise FrameError("BI1_BROKER_CHILD_DEADLINE_REFUSED")
        self._deadline_ns = self._deadline_snapshot = deadline_ns
        self._binding = binding
        self._binding_snapshot = binding
        self._context = (os.getpid(), os.getpgrp())
        self._context_snapshot = self._context
        # Reuse only the fixed executable/parser recipe, not direct-owner topology.
        self._launch = replace(child_launch(parser_package), start_new_session=False)
        self._launch_snapshot = self._launch
        self._recipe_snapshot = (
            self._launch.argv,
            self._launch.environment,
            self._launch.close_fds,
            self._launch.pass_fds,
            self._launch.start_new_session,
        )
        self._lock = threading.Lock()
        self._popen_type = self._popen_type_snapshot = _POPEN_TYPE
        self._constructor_returned = False
        self._child: subprocess.Popen[bytes] | None = None
        self._child_snapshot: subprocess.Popen[bytes] | None = None
        self._pid: int | None = None
        self._pid_snapshot: int | None = None
        self._streams: BrokerReaderStreams | None = None
        self._stream_snapshot: tuple[BinaryIO, BinaryIO, BinaryIO] | None = None
        self._streams_identity: BrokerReaderStreams | None = None
        self._launch_attempted = False
        self._sealed = False
        self._signal_attempted = False
        self._signals_retired = False
        self._uncertain = False
        self._raw_terminal_status: int | None = None
        self._wait: ChildWaitObservation | None = None
        self._wait_identity: ChildWaitObservation | None = None
        self._wait_snapshot: tuple[int, int] | None = None

    @property
    def uncertain(self) -> bool:
        return self._uncertain

    @property
    def signals_retired(self) -> bool:
        return self._signals_retired

    def _poison(self, code: str) -> None:
        self._uncertain = True
        self._signals_retired = True
        raise FrameError(code)

    def _check(self) -> None:
        try:
            self._check_state()
        except FrameError:
            raise
        except BaseException:
            self._poison("BI1_BROKER_CHILD_STATE_UNCERTAIN")

    def _check_launch_state(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self._uncertain,
                self._signals_retired,
                self._signal_attempted,
                self._launch_attempted,
                self._sealed,
                self._constructor_returned,
            )
        ):
            self._poison("BI1_BROKER_CHILD_STATE_DRIFT")
        if self._uncertain:
            raise FrameError("BI1_BROKER_CHILD_UNCERTAIN")
        if (
            type(self._popen_type) is not type
            or self._popen_type is not self._popen_type_snapshot
            or self._popen_type is not _POPEN_TYPE
            or type(self._context_snapshot) is not tuple
            or len(self._context_snapshot) != 2
            or any(type(value) is not int for value in self._context_snapshot)
            or self._context is not self._context_snapshot
            or (os.getpid(), os.getpgrp()) != self._context_snapshot
            or self._deadline_ns is not self._deadline_snapshot
            or (self._deadline_ns is not None and type(self._deadline_ns) is not int)
            or self._binding is not self._binding_snapshot
            or type(self._launch) is not ChildLaunch
            or self._launch is not self._launch_snapshot
            or type(self._recipe_snapshot) is not tuple
            or len(self._recipe_snapshot) != 5
            or any(
                a is not b
                for a, b in zip(
                    (
                        self._launch.argv,
                        self._launch.environment,
                        self._launch.close_fds,
                        self._launch.pass_fds,
                        self._launch.start_new_session,
                    ),
                    self._recipe_snapshot,
                    strict=True,
                )
            )
        ):
            self._poison("BI1_BROKER_CHILD_CONTEXT_DRIFT")
    def _check_state(self) -> None:
        self._check_launch_state()
        if self._child is not None and not self._constructor_returned:
            self._poison("BI1_BROKER_CHILD_PARTIAL_HANDLE")
        if self._child is None and self._constructor_returned:
            self._poison("BI1_BROKER_CHILD_PARTIAL_HANDLE")
        if self._child is not self._child_snapshot:
            self._poison("BI1_BROKER_CHILD_HANDLE_DRIFT")
        if self._child is None:
            if self._pid is not None or self._pid_snapshot is not None:
                self._poison("BI1_BROKER_CHILD_HANDLE_DRIFT")
        elif (
            type(self._pid) is not int
            or type(self._pid_snapshot) is not int
            or self._pid is not self._pid_snapshot
        ):
            self._poison("BI1_BROKER_CHILD_HANDLE_DRIFT")
        if self._wait is None and self._raw_terminal_status is not None:
            self._poison("BI1_BROKER_CHILD_WAIT_DRIFT")
        if self._wait is not self._wait_identity or (
            self._wait is not None
            and (
                type(self._wait) is not ChildWaitObservation
                or type(self._wait.raw_status) is not int
                or type(self._wait.exit_code) is not int
                or type(self._raw_terminal_status) is not int
                or self._wait.raw_status != self._raw_terminal_status
                or type(self._wait_snapshot) is not tuple
                or len(self._wait_snapshot) != 2
                or any(type(value) is not int for value in self._wait_snapshot)
                or (self._wait.raw_status, self._wait.exit_code) != self._wait_snapshot
            )
        ):
            self._poison("BI1_BROKER_CHILD_WAIT_DRIFT")
        if self._child is not None and (
            type(self._child.pid) is not int
            or self._child.pid != self._pid_snapshot
            or (self._wait is None and self._child.returncode is not None)
            or (
                self._wait is not None
                and (
                    type(self._child.returncode) is not int
                    or self._child.returncode != self._wait.exit_code
                )
            )
        ):
            self._poison("BI1_BROKER_CHILD_HANDLE_DRIFT")
        if self._streams is not self._streams_identity:
            self._poison("BI1_BROKER_CHILD_STREAM_DRIFT")
        if self._stream_snapshot is not None and (
            type(self._stream_snapshot) is not tuple
            or len(self._stream_snapshot) != 3
            or type(self._streams) is not BrokerReaderStreams
            or any(
                a is not b
                for a, b in zip(
                    (self._streams.control, self._streams.result, self._streams.diagnostic),
                    self._stream_snapshot,
                    strict=True,
                )
            )
            or any(
                a is not b
                for a, b in zip(
                    (self._child.stdin, self._child.stdout, self._child.stderr),
                    self._stream_snapshot,
                    strict=True,
                )
            )
        ):
            self._poison("BI1_BROKER_CHILD_STREAM_DRIFT")

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._poison("BI1_BROKER_CHILD_REENTRY")
        try:
            self._check()
        except BaseException:
            self._lock.release()
            raise

    @property
    def startup_recipe(self) -> ChildLaunch:
        """Frozen configuration for startup comparison, never code attestation."""
        self._enter()
        try:
            return self._launch_snapshot
        finally:
            self._lock.release()

    def owns(self, binding: object) -> bool:
        self._enter()
        try:
            return binding is not None and binding is self._binding_snapshot
        finally:
            self._lock.release()

    def seal_unlaunched(self) -> None:
        self._enter()
        try:
            if self._launch_attempted or self._sealed or self._child is not None:
                raise FrameError("BI1_BROKER_CHILD_SEAL_REFUSED")
            self._sealed = True
            self._signals_retired = True
        finally:
            self._lock.release()

    @property
    def never_launched_closed(self) -> bool:
        self._enter()
        try:
            return self._sealed and not self._launch_attempted and self._child is None
        finally:
            self._lock.release()

    def start(self) -> None:
        self._enter()
        try:
            if self._launch_attempted or self._sealed:
                raise FrameError("BI1_BROKER_CHILD_START_REFUSED")
            self._launch_attempted = True
            try:
                if self._deadline_ns is not None and time.monotonic_ns() >= self._deadline_ns:
                    self._poison("BI1_BROKER_CHILD_START_DEADLINE")
                active = _empty_active()
                child = _allocate_popen()
                # Retain before type checks and every constructor side effect.
                self._child = self._child_snapshot = child
                self._check_launch_state()
                if type(child) is not self._popen_type or _empty_active() is not active:
                    self._poison("BI1_BROKER_CHILD_NATIVE_HANDLE_REFUSED")
                if self._deadline_ns is not None and time.monotonic_ns() >= self._deadline_ns:
                    self._poison("BI1_BROKER_CHILD_START_DEADLINE")
                _initialize_popen(
                    child,
                    self._launch.argv,
                    env=dict(self._launch.environment),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                    close_fds=True,
                    pass_fds=(),
                    start_new_session=False,
                )
                if self._child is not child or self._child_snapshot is not child:
                    self._poison("BI1_BROKER_CHILD_HANDLE_DRIFT")
                self._constructor_returned = True
            except BaseException as error:
                self._uncertain = self._signals_retired = True
                raise BrokerChildLaunchError(self, error) from None
            # A successful constructor return is not a wait/close/custody fact.
            try:
                self._pid = self._pid_snapshot = child.pid
                if (
                    type(self._pid) is not int
                    or self._pid <= 1
                    or self._pid == self._context[0]
                    or child.returncode is not None
                    or os.getpgid(self._pid) != self._context[1]
                    or any(stream is None for stream in (child.stdin, child.stdout, child.stderr))
                ):
                    self._poison("BI1_BROKER_CHILD_LAYOUT_REFUSED")
                self._check()
                self._streams = self._streams_identity = BrokerReaderStreams(
                    child.stdin, child.stdout, child.stderr
                )
                self._stream_snapshot = (child.stdin, child.stdout, child.stderr)
            except BaseException:
                self._uncertain = self._signals_retired = True
                raise FrameError("BI1_BROKER_CHILD_LAYOUT_UNCERTAIN") from None
        finally:
            self._lock.release()

    @property
    def streams(self) -> BrokerReaderStreams:
        self._enter()
        try:
            if self._streams is None:
                raise FrameError("BI1_BROKER_CHILD_NOT_STARTED")
            return self._streams
        finally:
            self._lock.release()

    def poll_wait(self) -> bool:
        self._enter()
        try:
            if self._child is None or self._raw_terminal_status is not None:
                raise FrameError("BI1_BROKER_CHILD_WAIT_REFUSED")
            child, pid_expected = self._child, self._pid
            try:
                result = os.waitpid(pid_expected, os.WNOHANG)
            except BaseException:
                self._poison("BI1_BROKER_CHILD_WAIT_UNCERTAIN")
            if (
                type(result) is not tuple
                or len(result) != 2
                or any(type(value) is not int for value in result)
            ):
                self._poison("BI1_BROKER_CHILD_WAIT_UNCERTAIN")
            pid, status = result
            if (pid, status) == (0, 0):
                self._check()
                return False
            if (
                pid != pid_expected
                or not 0 <= status <= 65535
                or not (os.WIFEXITED(status) or os.WIFSIGNALED(status))
            ):
                self._poison("BI1_BROKER_CHILD_WAIT_UNCERTAIN")
            # Preserve exact known terminal fact before later checks/conversions.
            self._signals_retired = True
            self._raw_terminal_status = status
            try:
                code = os.waitstatus_to_exitcode(status)
            except BaseException:
                self._poison("BI1_BROKER_CHILD_STATUS_UNCERTAIN")
            # This exact returned handle, not a possibly retargeted field, owns the reap.
            child.returncode = code
            self._wait = self._wait_identity = ChildWaitObservation(status, code)
            self._wait_snapshot = (status, code)
            self._check()
            return True
        finally:
            self._lock.release()

    def terminate_once(self) -> None:
        self._enter()
        try:
            if (
                self._child is None
                or self._signal_attempted
                or self._signals_retired
                or self._wait is not None
            ):
                raise FrameError("BI1_BROKER_CHILD_SIGNAL_REFUSED")
            self._signal_attempted = True
            self._signals_retired = True
            try:
                # Unreaped exact child + exclusive reaper is required; no group signal.
                os.kill(self._pid, signal.SIGKILL)
            except BaseException:
                self._poison("BI1_BROKER_CHILD_SIGNAL_UNCERTAIN")
            self._check()
        finally:
            self._lock.release()

    def terminal_wait(self, binding: object) -> ChildWaitObservation:
        self._enter()
        try:
            if binding is not self._binding_snapshot or self._wait is None:
                raise FrameError("BI1_BROKER_CHILD_OBSERVATION_REFUSED")
            return self._wait
        finally:
            self._lock.release()

    def validates_wait(self, binding: object, observation: ChildWaitObservation) -> bool:
        self._enter()
        try:
            return (
                binding is self._binding_snapshot
                and self._wait is not None
                and observation is self._wait
            )
        finally:
            self._lock.release()
