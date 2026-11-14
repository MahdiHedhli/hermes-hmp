"""Retained actual policy thread; task completion is never a join receipt.

Native job admission/authorization and one-use transfer stay in the future binder.
No cancellation, forced thread termination or automatic replay is provided.
"""

from __future__ import annotations

import threading

from .presentation_jobs import FrameError
from .presentation_parent_policy import ParentPolicyReadOwner, ParentPolicySnapshot


class PolicyThreadStartError(FrameError):
    def __init__(self, owner: PolicyThreadOwner, original: BaseException):
        super().__init__("BI1_POLICY_THREAD_START_UNCERTAIN")
        self.failed_owner = owner
        self._original = original


class PolicyThreadOwner:
    def __init__(self, policy: ParentPolicyReadOwner):
        if type(policy) is not ParentPolicyReadOwner:
            raise FrameError("BI1_POLICY_THREAD_REFUSED")
        self.policy = policy
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._attempted = False
        self._started = False
        self._snapshot: ParentPolicySnapshot | None = None
        self._failure: BaseException | None = None
        self.joined = False
        self.uncertain = False

    def _work(self) -> None:
        try:
            self._snapshot = self.policy.run()
        except BaseException as error:
            self._failure = error

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self.uncertain = True
            self.policy.uncertain = True
            raise FrameError("BI1_POLICY_THREAD_REENTRY")
        if self.uncertain:
            self._lock.release()
            raise FrameError("BI1_POLICY_THREAD_UNCERTAIN")

    def start(self) -> None:
        self._enter()
        try:
            if self._attempted:
                raise FrameError("BI1_POLICY_THREAD_REPLAY")
            self._attempted = True
            try:
                worker = threading.Thread(target=self._work, name="hmp-bi1-policy", daemon=False)
                self._worker = worker  # retain before start can return late or throw
                if self.uncertain:
                    raise FrameError("BI1_POLICY_THREAD_UNCERTAIN")
                worker.start()
                self._started = True
            except BaseException as error:
                self.uncertain = True
                self.policy.uncertain = True
                self._failure = error
                raise PolicyThreadStartError(self, error) from None
            if self.uncertain:
                raise FrameError("BI1_POLICY_THREAD_UNCERTAIN")
        finally:
            self._lock.release()

    def poll_join(self) -> bool:
        self._enter()
        try:
            worker = self._worker
            if self.joined or not self._started or worker is None:
                raise FrameError("BI1_POLICY_THREAD_JOIN_REFUSED")
            try:
                alive = worker.is_alive()
                if self.uncertain or type(alive) is not bool:
                    raise FrameError("BI1_POLICY_THREAD_JOIN_UNCERTAIN")
                if alive:
                    return False
                worker.join(timeout=0)
                if self.uncertain:
                    raise FrameError("BI1_POLICY_THREAD_JOIN_UNCERTAIN")
                alive = worker.is_alive()
                if self.uncertain or type(alive) is not bool:
                    raise FrameError("BI1_POLICY_THREAD_JOIN_UNCERTAIN")
                if alive:
                    return False
            except BaseException:
                self.uncertain = True
                raise FrameError("BI1_POLICY_THREAD_JOIN_UNCERTAIN") from None
            if self.uncertain:
                raise FrameError("BI1_POLICY_THREAD_JOIN_UNCERTAIN")
            self.joined = True
            return True
        finally:
            self._lock.release()

    def observed_snapshot(self) -> ParentPolicySnapshot:
        if (
            not self.joined
            or self.uncertain
            or self.policy.uncertain
            or not self.policy.descriptors_closed
            or self._failure is not None
            or type(self._snapshot) is not ParentPolicySnapshot
        ):
            raise FrameError("BI1_POLICY_THREAD_RESULT_REFUSED")
        return self._snapshot

    def seal_closed(self) -> bool:
        """Retire only a never-started or actually joined, known-closed owner."""
        self._enter()
        try:
            if self._attempted and not self.joined:
                return False
            if self.uncertain or self.policy.uncertain or not self.policy.descriptors_closed:
                return False
            # Reserve start permanently even when no thread was ever created.
            self._attempted = True
            return True
        finally:
            self._lock.release()
