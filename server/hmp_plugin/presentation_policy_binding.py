"""Policy work attached to one existing native-authorized reserved job.

No route/child launch/input publication/clean-abort is provided here. Initial and
BEFORE observations are required; fresh native postcheck follows actual join.
"""

from __future__ import annotations

import os

from .presentation_authority import AuthorityRefusalError, OpaqueOperation, ParentAuthorityAdapter
from .presentation_budget import PresentationWorkLedger
from .presentation_jobs import State
from .presentation_parent_policy import ParentPolicyReadOwner, ParentPolicySnapshot
from .presentation_policy_thread import PolicyThreadOwner
from .presentation_posix import PosixFileOps


class NativePolicyWork:
    def __init__(self, authority: ParentAuthorityAdapter, operation: OpaqueOperation):
        if type(authority) is not ParentAuthorityAdapter or type(operation) is not OpaqueOperation:
            raise AuthorityRefusalError
        record = authority._record(operation)
        if (
            record.owner.inspect(record.handle)[0] is not State.STARTING
            or not record.initial_complete
            or record.policy_work is not None
            or record.child is not None
            or type(record.initial_home) is not str
        ):
            raise AuthorityRefusalError
        home = record.initial_home
        profile = record.lease.profile
        if profile == "default":
            root = home
        else:
            suffix = "/profiles/" + profile
            if not home.endswith(suffix):
                raise AuthorityRefusalError
            root = home[: -len(suffix)]
        self._authority, self._operation, self._record = authority, operation, record
        record.policy_work = self  # one operation owns even partial construction
        self._invalid = False
        self._attempted = False
        self._postcheck_attempted = False
        self._postchecked = False
        self._policy = None
        self._thread = None
        if not self._current():
            raise AuthorityRefusalError
        self._policy = ParentPolicyReadOwner(
            root=root,
            home=home,
            profile=profile,
            uid=os.geteuid(),
            gid=os.getegid(),
            ledger=PresentationWorkLedger(clock=authority._clock, deadline=record.deadline),
            fs=PosixFileOps(),
            current=self._current,
        )
        self._thread = PolicyThreadOwner(self._policy)

    def _local_current(self) -> bool:
        record = self._record
        return (
            not self._invalid
            and self._authority._by_operation.get(self._operation) is record
            and record.policy_work is self
            and not self._authority.disabled
            and not record.owner.disabled
            and record.fence.current
            and record.fence.epoch == record.fence_epoch
            and record.owner.epoch == record.lease.epoch
            and record.child is None
            and record.owner.inspect(record.handle)[0] is State.STARTING
        )

    def _current(self) -> bool:
        # No callbacks in the final local fence check.
        return (
            self._local_current()
            and self._authority._current(self._record)
            and self._local_current()
        )

    def start(self) -> None:
        if self._attempted:
            self._invalid = True
            raise AuthorityRefusalError
        self._attempted = True
        if not self._current() or self._thread is None:
            raise AuthorityRefusalError
        self._thread.start()

    def poll_join(self) -> bool:
        if self._thread is None:
            raise AuthorityRefusalError
        return self._thread.poll_join()

    async def postcheck(self) -> bool:
        if self._postcheck_attempted:
            self._invalid = True
            raise AuthorityRefusalError
        self._postcheck_attempted = True  # reserve before any foreign callback
        if not self._current():
            raise AuthorityRefusalError
        if self._thread is None:
            raise AuthorityRefusalError
        self._thread.observed_snapshot()
        if not await self._authority._observe(self._record, "PRE_GO"):
            return False
        self._postchecked = self._current()
        return self._postchecked

    def observed_snapshot(self) -> ParentPolicySnapshot:
        if not self._postchecked or not self._current() or self._thread is None:
            raise AuthorityRefusalError
        return self._thread.observed_snapshot()
