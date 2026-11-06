"""Retained source-only reader lifecycle; live runtime qualification is separate.

No route advertises this module. The caller must qualify the fixed own-code,
no-spawn/no-FD-transfer worker, interpreter/dependencies and exclusive reaper.
Task cancellation is not a join, process exit or native closure observation.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from .presentation_authority import AuthorityRefusalError, OpaqueOperation, ParentAuthorityAdapter
from .presentation_child_launch import parser_package_path
from .presentation_control_pipe import OwnedControlPipe
from .presentation_jobs import State
from .presentation_pipes import OwnedPresentationPipes, PipeAcquisitionError
from .presentation_policy_binding import NativePolicyWork
from .presentation_process import PresentationProcessOwner


class ReaderSupervisor:
    """One reserved operation, one run task, one nonrenewable cleanup phase."""

    def __init__(
        self,
        authority: ParentAuthorityAdapter,
        operation: OpaqueOperation,
        *,
        parser_package: str | None = None,
    ):
        if type(authority) is not ParentAuthorityAdapter or authority._clock is not time.monotonic:
            raise AuthorityRefusalError
        record = authority._record(operation)
        if (
            record.reader_supervisor is not None
            or record.remote_operation is not None
            or record.owner.inspect(record.handle)[0] is not State.QUEUED
        ):
            raise AuthorityRefusalError
        self._parser_package = (
            None if parser_package is None else parser_package_path(parser_package)
        )
        self._parser_snapshot = (self._parser_package,)
        self.authority, self.operation, self.record = authority, operation, record
        self.phase = "READY"
        self.task: asyncio.Task | None = None
        self.cleanup_task: asyncio.Task | None = None
        self.cleanup_deadline: float | None = None
        self.process: PresentationProcessOwner | None = None
        self.pipes: OwnedPresentationPipes | None = None
        self.control: OwnedControlPipe | None = None
        self.control_constructed = False
        self.emitted = False
        self.retired = False
        record.reader_supervisor = self  # retain all partial owners before any await

    def _current(self) -> bool:
        parser = self._parser_package
        return (
            (parser is None or type(parser) is str)
            and parser == self._parser_snapshot[0]
            and self.phase == "RUNNING"
            and self.authority._current(self.record)
        )

    def _require_current(self) -> None:
        if not self._current():
            raise AuthorityRefusalError

    async def _body(self, source_sha, fallback, observed_at, avatar_sha, sink) -> None:
        self._require_current()
        accepted = await self.authority.initialize(self.operation)
        self._require_current()
        if not accepted:
            return
        self.authority.start(self.operation)
        self._require_current()
        work = NativePolicyWork(self.authority, self.operation)
        work.start()
        while not work.poll_join():
            await asyncio.sleep(0.005)
            self._require_current()
        accepted = await work.postcheck()
        self._require_current()
        if not accepted:
            return
        self.process = PresentationProcessOwner(parser_package=self._parser_snapshot[0])
        self.authority.retain_process(self.operation, self.process)
        packet = work.worker_input(
            source_manifest_sha=source_sha,
            canonical_fallback=fallback,
            observed_at=observed_at,
            expected_avatar_sha=avatar_sha,
        )
        self._require_current()
        self.process.start()
        child = self.process.child
        self.authority.bind_child(self.operation, child)
        try:
            self.pipes = OwnedPresentationPipes(child.stdout, child.stderr)
        except PipeAcquisitionError as error:
            self.pipes = error.failed_owner
            raise
        # Keep a failed partial constructor, without assuming it is closable.
        self.control = OwnedControlPipe.__new__(OwnedControlPipe)
        self.control.__init__(
            child.stdin, handle=self.record.handle, child=child, current=self._current
        )
        self.control_constructed = True
        self._require_current()
        self.control.write_input(packet)
        accepted = await self.authority.go_inline(self.operation, child, self.control.send_go)
        self._require_current()
        if not accepted:
            return
        while True:
            self._require_current()
            if not self.pipes.drained:
                self.pipes.poll(deadline=self.record.deadline)
            if not self.process.reaped:
                self.process.poll_wait()
            if self.process.reaped and self.pipes.drained:
                break
            await asyncio.sleep(0.005)
        if not self.process.probe_group_absence():
            raise AuthorityRefusalError
        if not self.authority.collect_reader_closure(self.operation, self.pipes, self.control):
            return
        accepted = await self.authority.reauthorize(self.operation)
        self._require_current()
        if accepted:
            self.emitted = self.authority.emit_inline(self.operation, sink)

    def _stop(self) -> None:
        if self.phase != "RUNNING":
            return
        self.phase = "CLEANUP"  # synchronous ownership handoff before cancelling awaits
        self.cleanup_deadline = time.monotonic() + 0.25
        self.authority.cancel(self.operation)
        if self.task is not None and not self.task.done():
            self.task.cancel()

    def _cleanup_current(self) -> bool:
        return self.cleanup_deadline is not None and time.monotonic() < self.cleanup_deadline

    async def _cleanup(self) -> None:
        if not self._cleanup_current():
            return
        process, control, pipes = self.process, self.control, self.pipes
        if process is not None and process._launch_attempted:
            # An uncertain launch/constructor is debt, not permission to guess.
            if process.uncertain or process._child is None:
                return
            if not process.reaped:
                if not self._cleanup_current():
                    return
                process.terminate_once()
            if control is not None and self.control_constructed and not control.closed:
                if control._close_attempted:
                    return
                if not self._cleanup_current():
                    return
                control.close_for_drain()
            while not process.reaped:
                if not self._cleanup_current():
                    return
                process.poll_wait()
                if not process.reaped:
                    await asyncio.sleep(0.005)
            if not process.group_absent:
                if not self._cleanup_current() or process._group_probe_attempted:
                    return
                if not process.probe_group_absence():
                    return
            if control is None or pipes is None or not self.control_constructed:
                return
            if self.record.owner.inspect(self.record.handle)[0] in (State.DRAINING, State.UNKNOWN):
                while self._cleanup_current():
                    if self.authority.drain_cancelled_reader(
                        self.operation, pipes, control, cleanup_deadline=self.cleanup_deadline
                    ):
                        break
                    if not self._cleanup_current():
                        return
                    await asyncio.sleep(0.005)
                if not self._cleanup_current():
                    return
                if (
                    not self.record.reader_collected
                    and self.record.owner.inspect(self.record.handle)[0] is State.DRAINING
                ):
                    if not self._cleanup_current():
                        return
                    self.authority.collect_reader_closure(self.operation, pipes, control)
        # A late native await cannot race another native DRAIN or retirement.
        while self.task is not None and not self.task.done():
            if not self._cleanup_current():
                return
            await asyncio.sleep(0.005)
        work = self.record.policy_work
        if work is not None and not work.resources_closed:
            thread = work._thread
            if thread is not None and thread._started and not thread.joined:
                while self._cleanup_current():
                    if work.poll_join():
                        break
                    if not self._cleanup_current():
                        return
                    await asyncio.sleep(0.005)
                if not self._cleanup_current():
                    return
        if self.record.child is None and work is not None:
            if not self._cleanup_current():
                return
            if not self.authority.refuse_policy_prelaunch(self.operation):
                return
        elif process is not None and not process._launch_attempted:
            if not self._cleanup_current():
                return
            process.seal_unlaunched()
        if self._cleanup_current():
            self.retired = await self.authority.retire_known(self.operation)

    async def run(
        self,
        *,
        source_sha: str,
        fallback: str,
        observed_at: int,
        sink: Callable[[dict[str, object], bytes], None],
        avatar_sha: str | None = None,
    ) -> bool:
        if self.phase != "READY":
            raise AuthorityRefusalError
        self.phase = "RUNNING"
        self.task = asyncio.create_task(
            self._body(source_sha, fallback, observed_at, avatar_sha, sink)
        )
        self.task.add_done_callback(self._consume_failure)
        cancelled = False
        try:
            await asyncio.wait({self.task}, timeout=max(0, self.record.deadline - time.monotonic()))
        except asyncio.CancelledError:
            cancelled = True
        finally:
            self._stop()
            self.cleanup_task = asyncio.create_task(self._cleanup())
            self.cleanup_task.add_done_callback(self._consume_failure)
            try:
                await asyncio.wait(
                    {self.cleanup_task}, timeout=max(0, self.cleanup_deadline - time.monotonic())
                )
            except asyncio.CancelledError:
                cancelled = True
            if not self.cleanup_task.done():
                self.cleanup_task.cancel()
            for task in (self.task, self.cleanup_task):
                if task.done() and not task.cancelled():
                    task.exception()  # consume failure without exposing payload/path details
            if not self.retired:
                self.authority._unknown(self.record)
            self.phase = "CLOSED" if self.retired else "DEBT"
        if cancelled:
            raise asyncio.CancelledError
        return self.emitted

    @staticmethod
    def _consume_failure(task: asyncio.Task) -> None:
        if not task.cancelled():
            task.exception()
