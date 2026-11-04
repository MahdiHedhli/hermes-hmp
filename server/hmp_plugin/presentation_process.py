"""Retained fixed child launch and exact terminal wait observations.

No route calls this. Runtime/code provenance, exclusive reaper qualification and
hard-deadline supervisor remain unbound. Termination requires retained child custody.
"""

from __future__ import annotations

import errno
import os
import signal
import subprocess
import threading

from .presentation_child_launch import child_launch
from .presentation_jobs import FrameError


class ProcessLaunchError(FrameError):
    def __init__(self, owner: PresentationProcessOwner, original: BaseException):
        super().__init__("BI1_PROCESS_LAUNCH_UNCERTAIN")
        self.failed_owner = owner
        self._original = original


class PresentationProcessOwner:
    def __init__(self):
        self._lock = threading.Lock()
        self._child: subprocess.Popen[bytes] | None = None
        self._pid: int | None = None
        self._launch_attempted = False
        self._binding: object | None = None
        self._sealed_unlaunched = False
        self._termination_attempted = False
        self._wait_status: int | None = None
        self._raw_wait: object = None
        self._group_probe_attempted = False
        self.group_absent = False
        self.signals_retired = False
        self.uncertain = False

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self.uncertain = True
            self.signals_retired = True
            raise FrameError("BI1_PROCESS_REENTRY")
        if self.uncertain:
            self._lock.release()
            raise FrameError("BI1_PROCESS_UNCERTAIN")

    def claim(self, binding: object) -> None:
        """Permanently bind this process owner to one operation before launch."""
        self._enter()
        try:
            if self._binding is not None or self._launch_attempted or self._sealed_unlaunched:
                raise FrameError("BI1_PROCESS_CLAIM_REFUSED")
            if binding is None:
                raise FrameError("BI1_PROCESS_CLAIM_REFUSED")
            self._binding = binding
        finally:
            self._lock.release()

    def owns(self, binding: object) -> bool:
        return binding is not None and self._binding is binding

    def seal_unlaunched(self) -> bool:
        """Close an explicitly never-launched owner; absence alone is no receipt."""
        self._enter()
        try:
            if self._launch_attempted or self._child is not None or self._pid is not None:
                raise FrameError("BI1_PROCESS_SEAL_REFUSED")
            self._sealed_unlaunched = True
            self.signals_retired = True
            return True
        finally:
            self._lock.release()

    @property
    def never_launched_closed(self) -> bool:
        return (
            self._sealed_unlaunched
            and not self._launch_attempted
            and self._child is None
            and self._pid is None
            and self.signals_retired
            and not self.uncertain
        )

    def start(self) -> None:
        self._enter()
        try:
            if self._launch_attempted or self._sealed_unlaunched:
                raise FrameError("BI1_PROCESS_LAUNCH_REFUSED")
            launch = child_launch()
            if self.uncertain:
                raise FrameError("BI1_PROCESS_UNCERTAIN")
            self._launch_attempted = True
            try:
                child = subprocess.Popen(  # noqa: S603 — fixed own-code recipe; no request argv
                    launch.argv,
                    env=dict(launch.environment),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                    close_fds=True,
                    pass_fds=(),
                    start_new_session=True,
                )
            except BaseException as error:
                self.uncertain = True
                self.signals_retired = True
                raise ProcessLaunchError(self, error) from None
            # Retain the exact returned handle BEFORE checks or later callbacks.
            self._child = child
            if self.uncertain or type(child.pid) is not int or child.pid <= 0:
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_UNCERTAIN")
            self._pid = child.pid
        finally:
            self._lock.release()

    @property
    def child(self) -> subprocess.Popen[bytes]:
        """Exclusive ownership: caller may use streams, never poll/wait/signal."""
        if self._child is None:
            raise FrameError("BI1_PROCESS_NOT_STARTED")
        return self._child

    @property
    def reaped(self) -> bool:
        return self._wait_status is not None

    @property
    def exit_code(self) -> int | None:
        return None if self._wait_status is None else os.waitstatus_to_exitcode(self._wait_status)

    def poll_wait(self) -> bool:
        self._enter()
        try:
            child = self.child
            if self.reaped or child.returncode is not None or child.pid != self._pid:
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_WAIT_REFUSED")
            try:
                result = os.waitpid(self._pid, os.WNOHANG)
            except BaseException:
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_WAIT_UNCERTAIN") from None
            self._raw_wait = result
            if (
                type(result) is not tuple
                or len(result) != 2
                or any(type(v) is not int for v in result)
            ):
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_WAIT_UNCERTAIN")
            pid, status = result
            if pid == 0:
                if self.uncertain:
                    raise FrameError("BI1_PROCESS_UNCERTAIN")
                return False
            if pid != self._pid or not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_WAIT_UNCERTAIN")
            # The exact terminal reap and signal retirement survive any later
            # conversion/callback/cancellation failure. Never mint a guessed code.
            self._wait_status = status
            self.signals_retired = True
            child.returncode = os.waitstatus_to_exitcode(status)
            if self.uncertain:
                raise FrameError("BI1_PROCESS_UNCERTAIN")
            return True
        finally:
            self._lock.release()

    def terminate_once(self) -> bool:
        """Request termination once; this never proves reap or resource closure."""
        self._enter()
        try:
            if self._termination_attempted or self.signals_retired or self.reaped:
                raise FrameError("BI1_PROCESS_TERMINATION_REFUSED")
            child = self.child
            if child.pid != self._pid or child.returncode is not None:
                self.uncertain = True
                self.signals_retired = True
                self._termination_attempted = True
                raise FrameError("BI1_PROCESS_CUSTODY_LOST")
            self._termination_attempted = True
            try:
                group = os.getpgid(self._pid)
                if (
                    group != self._pid
                    or self.uncertain
                    or self.signals_retired
                    or child.pid != self._pid
                    or child.returncode is not None
                ):
                    raise FrameError("BI1_PROCESS_CUSTODY_LOST")
                os.killpg(self._pid, signal.SIGKILL)
            except BaseException:
                self.uncertain = True
                self.signals_retired = True
                raise FrameError("BI1_PROCESS_TERMINATION_UNCERTAIN") from None
            return True
        finally:
            self._lock.release()

    def probe_group_absence(self) -> bool:
        self._enter()
        try:
            if not self.reaped or self._group_probe_attempted:
                raise FrameError("BI1_PROCESS_GROUP_REFUSED")
            self._group_probe_attempted = True
            try:
                os.killpg(self._pid, 0)
            except OSError as error:
                if error.errno == errno.ESRCH and not self.uncertain:
                    self.group_absent = True
                    return True
                self.uncertain = True
                raise FrameError("BI1_PROCESS_GROUP_UNCERTAIN") from None
            except BaseException:
                self.uncertain = True
                raise FrameError("BI1_PROCESS_GROUP_UNCERTAIN") from None
            # Existing or reused groups are retained debt and never signalled.
            return False
        finally:
            self._lock.release()
