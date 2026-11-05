"""Retained reader resources and candidate bytes; no native/remote authority.

The private broker spine composes retained resources, but production admission
and native GO still require their own gates. Local observations never release
started registry/native reservations.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

from .presentation_broker_child import BrokerChildOwner, ChildWaitObservation
from .presentation_broker_codec import BrokerBinding, _binding
from .presentation_cancel_budget import CancellationBudget
from .presentation_control_pipe import ControlAcquisitionError, OwnedControlPipe
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import _PROFILE, INPUT_LIMIT, OUTPUT_LIMIT, FrameError
from .presentation_output_v2 import compare_parent_totals, decode_output_v2
from .presentation_pipes import OwnedPresentationPipes, PipeAcquisitionError


@dataclass(frozen=True)
class BrokerLocalDrainObservation:
    scope: tuple[str | int, ...]
    exit_code: int


class BrokerReaderResources:
    def __init__(
        self,
        operation: object,
        process: BrokerChildOwner,
        *,
        binding: BrokerBinding,
        profile: str,
        kind: str,
        deadline_ns: int,
        cleanup_budget: CancellationBudget,
    ):
        from .presentation_broker_registry import _Record

        _binding(binding)
        if (
            type(operation) is not _Record
            or type(process) is not BrokerChildOwner
            or type(profile) is not str
            or _PROFILE.fullmatch(profile) is None
            or type(kind) is not str
            or kind not in ("METADATA", "AVATAR")
            or type(deadline_ns) is not int
            or not 0 < deadline_ns < 1 << 63
        ):
            raise FrameError("BI1_BROKER_RESOURCES_BINDING_REFUSED")
        if (type(cleanup_budget) is not CancellationBudget
                or cleanup_budget is not operation.cleanup_budget
                or cleanup_budget is not operation.cleanup_budget_snapshot
                or deadline_ns != operation.deadline_ns
                or CancellationBudget.inspect(cleanup_budget) != (deadline_ns, None, None, False)):
            raise FrameError("BI1_BROKER_RESOURCES_BINDING_REFUSED")
        self._cleanup_budget = self._cleanup_budget_snapshot = cleanup_budget
        self._cleanup_sampling = False
        self._operation = self._operation_snapshot = operation
        self._process = self._process_snapshot = process
        self._scope = self._scope_snapshot = (
            binding.iid,
            binding.listener,
            binding.broker,
            binding.channel,
            binding.operation,
            profile,
            kind,
            deadline_ns,
        )
        self._context = self._context_snapshot = (os.getpid(), os.getpgrp())
        self._deadline_ns = self._deadline_snapshot = deadline_ns
        self._lock = threading.Lock()
        self._phase = "NEW"
        self._invalidated = False
        self._poisoned = False
        self._start_attempted = self._input_attempted = self._go_attempted = False
        self._result_taken = False
        self._normal_complete = False
        self._streams = self._streams_snapshot = None
        self._pipes = self._pipes_snapshot = None
        self._pipe_buffer_snapshot = None
        self._control = self._control_snapshot = None
        self._wait: ChildWaitObservation | None = None
        self._wait_identity: ChildWaitObservation | None = None
        self._control_fact = None
        self._input_context = self._input_snapshot = None
        self._candidate = self._candidate_snapshot = bytearray()
        self._cleanup_end_ns: int | None = None
        self._cleanup_end_snapshot: int | None = None
        self._observation = self._observation_identity = None
        self._observation_values = None
        self._check()

    def _begin_cleanup(self) -> None:
        self._invalidated = True
        self._normal_complete = False
        owned = self._candidate_snapshot
        if owned is self._candidate and type(owned) is bytearray:
            owned[:] = b"\x00" * len(owned)
            owned.clear()
        self._input_context = self._input_snapshot = None
        if (
            type(self._pipes) is OwnedPresentationPipes
            and self._pipes._output is self._pipe_buffer_snapshot
            and type(self._pipe_buffer_snapshot) is bytearray
        ):
            self._pipe_buffer_snapshot[:] = b"\x00" * len(self._pipe_buffer_snapshot)
            self._pipe_buffer_snapshot.clear()
            self._pipes.refused = True
        self._freeze_cleanup()
        if self._phase != "LOCAL_DRAINED":
            self._phase = "CLEANUP"

    def _freeze_cleanup(self) -> None:
        if self._cleanup_sampling is not False:
            self._poison()
        self._cleanup_sampling = True
        try:
            budget = self._cleanup_budget_snapshot
            if type(budget) is not CancellationBudget or self._cleanup_budget is not budget:
                self._poison()
            now = time.monotonic_ns()
            if (self._cleanup_budget is not budget or self._cleanup_budget_snapshot is not budget
                    or self._poisoned is not False or self._cleanup_sampling is not True
                    or self._cleanup_end_ns is not self._cleanup_end_snapshot
                    or (self._cleanup_end_ns is not None
                        and type(self._cleanup_end_ns) is not int)):
                self._poison()
            window = CancellationBudget.local(budget, now)
            end = window.end_ns if self._cleanup_end_ns is None else min(
                self._cleanup_end_ns, window.end_ns)
            self._cleanup_end_ns = self._cleanup_end_snapshot = end
        finally:
            self._cleanup_sampling = False

    def _poison(self) -> None:
        self._poisoned = True
        self._invalidated = True
        if (
            self._candidate_snapshot is self._candidate
            and type(self._candidate_snapshot) is bytearray
        ):
            self._candidate_snapshot[:] = b"\x00" * len(self._candidate_snapshot)
            self._candidate_snapshot.clear()
        self._input_context = self._input_snapshot = None
        raise FrameError("BI1_BROKER_RESOURCES_UNCERTAIN")

    def _check(self) -> None:
        from .presentation_broker_registry import _Record

        try:
            if (
                type(self._poisoned) is not bool
                or self._poisoned
                or self._operation is not self._operation_snapshot
                or type(self._operation) is not _Record
                or self._process is not self._process_snapshot
                or type(self._process) is not BrokerChildOwner
                or self._scope is not self._scope_snapshot
                or type(self._scope) is not tuple
                or len(self._scope) != 8
                or any(type(v) is not str for v in self._scope[:7])
                or type(self._scope[7]) is not int
                or self._deadline_ns is not self._deadline_snapshot
                or self._deadline_ns != self._scope[7]
                or type(self._cleanup_budget) is not CancellationBudget
                or self._cleanup_budget is not self._cleanup_budget_snapshot
                or CancellationBudget.inspect(self._cleanup_budget)[0] != self._deadline_ns
                or self._operation.cleanup_budget is not self._cleanup_budget
                or self._operation.cleanup_budget_snapshot is not self._cleanup_budget
                or self._context is not self._context_snapshot
                or type(self._context) is not tuple
                or len(self._context) != 2
                or any(type(v) is not int for v in self._context)
                or self._context != (os.getpid(), os.getpgrp())
                or type(self._phase) is not str
                or self._phase not in ("NEW", "RUNNING", "CLEANUP", "LOCAL_DRAINED")
                or any(
                    type(v) is not bool
                    for v in (
                        self._cleanup_sampling,
                        self._invalidated,
                        self._start_attempted,
                        self._input_attempted,
                        self._go_attempted,
                        self._result_taken,
                        self._normal_complete,
                    )
                )
                or self._candidate is not self._candidate_snapshot
                or type(self._candidate) is not bytearray
                or len(self._candidate) > OUTPUT_LIMIT
                or self._streams is not self._streams_snapshot
                or self._pipes is not self._pipes_snapshot
                or (self._pipes is not None and type(self._pipes) is not OwnedPresentationPipes)
                or self._control is not self._control_snapshot
                or (self._control is not None and type(self._control) is not OwnedControlPipe)
                or self._input_context is not self._input_snapshot
                or self._cleanup_end_ns is not self._cleanup_end_snapshot
                or (self._cleanup_end_ns is not None and type(self._cleanup_end_ns) is not int)
                or self._wait is not self._wait_identity
                or (
                    self._wait is not None
                    and (
                        type(self._wait) is not ChildWaitObservation
                        or not self._process.validates_wait(self._operation, self._wait)
                    )
                )
                or not self._process.owns(self._operation)
                or type(self._process._deadline_snapshot) is not int
                or self._process._deadline_snapshot != self._deadline_ns
                or (not self._start_attempted and self._process._launch_attempted)
            ):
                self._poison()
            if self._streams is not None:
                held = self._process.streams
                if self._streams is not held:
                    self._poison()
                if self._pipes is not None and (
                    type(self._pipes._streams) is not dict
                    or any(type(k) is not str for k in self._pipes._streams)
                    or set(self._pipes._streams) != {"result", "diagnostic"}
                    or self._pipes._output is not self._pipe_buffer_snapshot
                    or type(self._pipe_buffer_snapshot) is not bytearray
                    or self._pipes._streams["result"] is not held.result
                    or self._pipes._streams["diagnostic"] is not held.diagnostic
                ):
                    self._poison()
                if self._control is not None and (
                    self._control._stream_snapshot is not held.control
                    or self._control._handle_snapshot is not self._operation
                    or self._control._child_snapshot is not self._process
                ):
                    self._poison()
            if self._observation is not self._observation_identity:
                self._poison()
            if self._observation is not None and (
                type(self._observation) is not BrokerLocalDrainObservation
                or self._observation.scope is not self._scope_snapshot
                or type(self._observation.exit_code) is not int
                or type(self._observation_values) is not int
                or self._observation.exit_code != self._observation_values
            ):
                self._poison()
        except BaseException:
            self._poison()

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._invalidated = True
            self._freeze_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_REENTRY")
        try:
            self._check()
        except BaseException:
            self._lock.release()
            raise

    def _fresh(self) -> bool:
        self._check()
        _, _, end, failed = CancellationBudget.inspect(self._cleanup_budget)
        if end is not None or failed:
            return False
        now = time.monotonic_ns()
        self._check()
        _, _, end, failed = CancellationBudget.inspect(self._cleanup_budget)
        return not self._invalidated and end is None and not failed and now < self._deadline_ns

    def _work_current(self) -> bool:
        return self._phase == "RUNNING" and self._fresh()

    def _require_work(self) -> None:
        if self._phase != "RUNNING" or not self._fresh():
            raise FrameError("BI1_BROKER_RESOURCES_WORK_REFUSED")

    def start(self) -> None:
        self._enter()
        try:
            if self._phase != "NEW" or self._start_attempted or not self._fresh():
                raise FrameError("BI1_BROKER_RESOURCES_START_REFUSED")
            self._start_attempted = True
            self._process.start()
            self._streams = self._streams_snapshot = self._process.streams
            try:
                self._pipes = self._pipes_snapshot = OwnedPresentationPipes(
                    self._streams.result, self._streams.diagnostic
                )
            except PipeAcquisitionError as error:
                self._pipes = self._pipes_snapshot = error.failed_owner
                self._pipe_buffer_snapshot = self._pipes._output
                raise
            self._pipe_buffer_snapshot = self._pipes._output
            try:
                self._control = self._control_snapshot = OwnedControlPipe(
                    self._streams.control,
                    handle=self._operation,
                    child=self._process,
                    current=self._work_current,
                )
            except ControlAcquisitionError as error:
                self._control = self._control_snapshot = error.failed_owner
                raise
            self._phase = "RUNNING"
            self._require_work()
        except BaseException:
            self._begin_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_START_UNCERTAIN") from None
        finally:
            self._lock.release()

    def stage_input(self, packet: bytes) -> None:
        self._enter()
        try:
            self._require_work()
            if (
                self._input_attempted
                or type(packet) is not bytes
                or not 4 <= len(packet) <= INPUT_LIMIT + 4
            ):
                raise FrameError("BI1_BROKER_RESOURCES_INPUT_REFUSED")
            self._input_attempted = True
            row = decode_input_v3(packet)
            if (
                (row["iid"], row["profile"], row["operation"], row["deadline_ns"])
                != (self._scope[0], self._scope[5], self._scope[6], self._deadline_ns)
                or (self._scope[6] == "METADATA" and row["expected_avatar_sha"] is not None)
                or (self._scope[6] == "AVATAR" and row["expected_avatar_sha"] is None)
            ):
                raise FrameError("BI1_BROKER_RESOURCES_INPUT_REFUSED")
            self._input_context = self._input_snapshot = (
                row["challenge"],
                row["epoch"],
                row["home"],
                tuple(sorted(row["parent_work_counts"].items())),
                row["expected_avatar_sha"],
            )
            self._control.write_input(packet)
            self._require_work()
        except BaseException:
            self._begin_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_INPUT_REFUSED") from None
        finally:
            self._lock.release()

    def relay_go(self) -> None:
        """Private qualified service entry after fresh original native/grammar GO."""
        self._enter()
        try:
            self._require_work()
            if self._go_attempted or self._input_context is None:
                raise FrameError("BI1_BROKER_RESOURCES_GO_REFUSED")
            self._go_attempted = True
            self._control.send_go(self._operation, self._process, self._input_context[0])
            self._require_work()
        except BaseException:
            self._begin_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_GO_REFUSED") from None
        finally:
            self._lock.release()

    def _closed(self) -> bool:
        if self._wait is None or self._pipes is None or self._control is None:
            return False
        if not self._process.validates_wait(self._operation, self._wait):
            self._poison()
        self._control_fact = self._control.close_observation(self._operation, self._process)
        return self._pipes.validate_local_closed(
            process=self._process,
            binding=self._operation,
            control=self._control,
            control_fact=self._control_fact,
        )

    def _mint(self) -> bool:
        self._check()
        if not self._closed():
            return False
        if self._observation is None:
            self._observation = self._observation_identity = BrokerLocalDrainObservation(
                self._scope_snapshot, self._wait.exit_code
            )
            self._observation_values = self._wait.exit_code
        self._phase = "LOCAL_DRAINED"
        self._check()
        return True

    def poll_result(self) -> bool:
        self._enter()
        try:
            if self._phase == "LOCAL_DRAINED":
                if (
                    not self._normal_complete
                    or not self._fresh()
                    or not self._closed()
                    or not self._fresh()
                ):
                    raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED")
                return True
            self._require_work()
            if not self._go_attempted or self._input_context is None:
                raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED")
            if not self._pipes.drained:
                self._pipes.poll(deadline=self._deadline_ns / 1_000_000_000)
            if self._wait is None and self._process.poll_wait():
                self._wait = self._wait_identity = self._process.terminal_wait(self._operation)
            self._require_work()
            if self._wait is None or not self._pipes.drained:
                return False
            if self._wait.exit_code != 0 or not self._mint():
                raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED")
            context = self._input_context
            row, avatar = decode_output_v2(self._pipes.output, context[0], context[1])
            compare_parent_totals(row, parent_home=context[2], parent_counts=dict(context[3]))
            if (
                row["outcome"] != "OK"
                or row["cleanup"] != {"known_fds_closed": True, "unknown_close": False}
                or (context[4] is not None and row["avatar_sha"] != context[4])
            ):
                raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED")
            del row, avatar  # temporary decoded body is not retained alongside encoded result
            self._candidate = self._candidate_snapshot = self._pipes._output
            self._pipes._output = self._pipe_buffer_snapshot = bytearray()
            self._check()
            if not self._fresh():
                raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED")
            self._normal_complete = True
            return True
        except BaseException:
            self._begin_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_RESULT_REFUSED") from None
        finally:
            self._lock.release()

    def take_candidate(self) -> bytes:
        self._enter()
        try:
            if (
                self._phase != "LOCAL_DRAINED"
                or not self._fresh()
                or self._result_taken
                or not self._candidate
                or not self._normal_complete
                or not self._closed()
                or not self._fresh()
            ):
                raise FrameError("BI1_BROKER_RESOURCES_CANDIDATE_REFUSED")
            self._result_taken = True
            held_candidate = self._candidate
            wire = bytes(held_candidate)
            held_candidate[:] = b"\x00" * len(held_candidate)
            held_candidate.clear()
            if not self._fresh():
                raise FrameError("BI1_BROKER_RESOURCES_CANDIDATE_REFUSED")
            return wire
        except BaseException:
            self._begin_cleanup()
            raise FrameError("BI1_BROKER_RESOURCES_CANDIDATE_REFUSED") from None
        finally:
            self._lock.release()

    def abort(self) -> None:
        self._enter()
        try:
            self._begin_cleanup()  # synchronous wipe/invalidation/frozen end, no I/O
        finally:
            self._lock.release()

    def _cleanup_live(self) -> bool:
        if (type(self._cleanup_end_ns) is not int
                or self._cleanup_end_ns is not self._cleanup_end_snapshot):
            return False
        if self._cleanup_sampling is not False:
            self._poison()
        self._cleanup_sampling = True
        try:
            budget = self._cleanup_budget_snapshot
            cached = self._cleanup_end_snapshot
            if type(budget) is not CancellationBudget or self._cleanup_budget is not budget:
                self._poison()
            now = time.monotonic_ns()
            if (self._cleanup_sampling is not True or self._poisoned is not False
                    or self._cleanup_budget is not budget
                    or self._cleanup_budget_snapshot is not budget
                    or self._cleanup_end_ns is not cached
                    or self._cleanup_end_snapshot is not cached):
                self._poison()
            return CancellationBudget.remaining_ns(budget, now) > 0 and now < cached
        except FrameError:
            return False
        finally:
            self._cleanup_sampling = False

    def poll_cleanup(self) -> bool:
        self._enter()
        try:
            if not self._invalidated:
                raise FrameError("BI1_BROKER_RESOURCES_CLEANUP_REFUSED")
            if not self._cleanup_live():
                return False
            if self._observation is not None:
                return self._closed() and self._cleanup_live()
            if self._wait is None:
                if not self._cleanup_live():
                    return False
                waited = self._process.poll_wait()
                if not self._cleanup_live():
                    return False
                if waited:
                    self._wait = self._wait_identity = self._process.terminal_wait(self._operation)
                elif self._process.signals_retired is not True:
                    if not self._cleanup_live():
                        return False
                    self._process.terminate_once()
            if not self._cleanup_live():
                return False
            if self._control is None or self._pipes is None:
                return False
            if self._control.closed is not True:
                if not self._cleanup_live():
                    return False
                self._control.close_for_drain()
            if not self._cleanup_live():
                return False
            if self._wait is None:
                if not self._cleanup_live():
                    return False
                if not self._process.poll_wait():
                    return False
                self._wait = self._wait_identity = self._process.terminal_wait(self._operation)
            if not self._cleanup_live():
                return False
            self._control_fact = self._control.close_observation(self._operation, self._process)
            if not self._cleanup_live():
                return False
            self._pipes.poll_local_discard(
                process=self._process,
                binding=self._operation,
                control=self._control,
                control_fact=self._control_fact,
                cleanup_end_ns=self._cleanup_end_ns,
            )
            if not self._cleanup_live():
                return False
            result = self._mint()
            return result and self._cleanup_live()
        except FrameError:
            return False
        finally:
            self._lock.release()

    def local_observation(self, operation: object) -> BrokerLocalDrainObservation:
        self._enter()
        try:
            if (
                operation is not self._operation_snapshot
                or self._observation is None
                or not self._closed()
            ):
                raise FrameError("BI1_BROKER_RESOURCES_OBSERVATION_REFUSED")
            return self._observation
        finally:
            self._lock.release()

    def validates_local(self, operation: object, observation: BrokerLocalDrainObservation) -> bool:
        return observation is self.local_observation(operation)
