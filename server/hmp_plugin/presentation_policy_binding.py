"""Policy work attached to one existing native-authorized reserved job.

No route/child launch/clean-abort is provided here. Initial and
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
        self._transfer_attempted = False
        self._closed_pretransfer = False
        self._scope = (root, home, profile, os.geteuid(), os.getegid())
        self._policy = None
        self._thread = None
        self._construction_finished = False
        try:
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
        finally:
            # Constructors never open files or start threads. A terminal failure
            # before thread creation is therefore known zero-work, not start debt.
            self._construction_finished = True

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

    def worker_input(
        self,
        *,
        source_manifest_sha: str,
        canonical_fallback: str,
        observed_at: int,
        expected_avatar_sha: str | None = None,
    ) -> bytes:
        """One private input3 transfer; digest is context, not code attestation."""
        from .presentation_input_v3 import encode_input_v3

        if self._transfer_attempted:
            self._invalid = True
            raise AuthorityRefusalError
        self._transfer_attempted = True
        snapshot = self.observed_snapshot()
        record = self._record
        job = record.owner._resolve(record.handle)
        root, home, profile, uid, gid = self._scope
        if job.operation == "METADATA" and expected_avatar_sha is not None:
            self._invalid = True
            raise AuthorityRefusalError
        if job.operation == "AVATAR" and expected_avatar_sha is None:
            self._invalid = True
            raise AuthorityRefusalError
        packet = encode_input_v3(
            {
                "schema": 3,
                "challenge": record.owner.challenge(record.handle),
                "epoch": record.lease.epoch,
                "profile": profile,
                "root": root,
                "home": home,
                "operation": job.operation,
                "expected_avatar_sha": expected_avatar_sha,
                "uid": uid,
                "gid": gid,
                "dir_modes": [0o700, 0o750, 0o755],
                "leaf_modes": [0o600, 0o640, 0o644],
                "source_manifest_sha": source_manifest_sha,
                "deadline_ns": int(record.deadline * 1_000_000_000),
                "directory_policy": [
                    [rule.uid, rule.gid, rule.modes[0]] for rule in snapshot.rules
                ],
                "iid": record.lease.iid,
                "canonical_fallback": canonical_fallback,
                "observed_at": observed_at,
                "parent_work_counts": dict(snapshot.counts),
            }
        )
        record.owner.bind_parent_result(record.handle, home, snapshot)
        if not self._current():
            self._invalid = True
            raise AuthorityRefusalError
        return packet

    def close_pretransfer(self) -> bool:
        """Known closure before any packet escapes; cancellation grants no join."""
        record = self._record
        if (
            self._authority._by_operation.get(self._operation) is not record
            or record.policy_work is not self
            or record.child is not None
            or record.native_claim is not None
            or self._transfer_attempted
        ):
            return False
        if not self._construction_finished:
            return False
        self._invalid = True
        if self._thread is not None and not self._thread.seal_closed():
            return False
        if self._policy is not None and (
            self._policy.uncertain or not self._policy.descriptors_closed
        ):
            return False
        self._closed_pretransfer = True
        return True

    @property
    def resources_closed(self) -> bool:
        if not self._construction_finished:
            return False
        if self._closed_pretransfer and self._thread is None:
            return self._policy is None or (
                not self._policy.uncertain and self._policy.descriptors_closed
            )
        return (
            self._thread is not None
            and (self._thread.joined or self._closed_pretransfer)
            and not self._thread.uncertain
            and self._policy is not None
            and not self._policy.uncertain
            and self._policy.descriptors_closed
        )
