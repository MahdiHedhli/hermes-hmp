"""Isolated, no-operation producer for a synthetic approval test.

This module is intentionally not wired to a CLI, HTTP route, or PromptStore. The caller must be
admitted separately and supply only its fixed in-memory publish/remove adapter. Native bindings are
injected after the HMP compatibility gate; importing this module alone is
inert. The CLI/IPC caller and bridge factory are outside this admitted source slice.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import contextvars
import inspect
import re
import secrets
import sys
import threading
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from types import ModuleType
from typing import Any

_HANDLE_RE = re.compile(r"[0-9a-f]{64}\Z")
_REQUEST_RE = re.compile(r"[0-9a-f]{32}\Z")
_MARKER_RE = re.compile(r"[0-9a-f]{64}\Z")
_ROUTE_RE = re.compile(r"hmp_synthetic_approval_test_v1_[0-9a-f]{64}\Z")
_ROUTE_PREFIX = "hmp_synthetic_approval_test_v1_"
_MAX_BINDING_BYTES = 256
_MIN_TIMEOUT_MS = 1
_MAX_TIMEOUT_MS = 60_000
_COMMAND = "Synthetic approval test — no action will run"
_DESCRIPTION = "Choose once to acknowledge this test card, or deny. No command or tool will run."
_NOTIFY_FAILED = "synthetic approval test notification unavailable"
# Identity-only wrapper result. Native code can return arbitrary dictionaries, but cannot create
# this private object; it records only that the wrapper declined invocation before the native call.
_NOT_INVOKED = object()


def _same_text(left: str, right: str) -> bool:
    try:
        if len(left) > _MAX_BINDING_BYTES or len(right) > _MAX_BINDING_BYTES:
            return False
        left_bytes, right_bytes = left.encode("utf-8"), right.encode("utf-8")
        if len(left_bytes) > _MAX_BINDING_BYTES or len(right_bytes) > _MAX_BINDING_BYTES:
            return False
        return secrets.compare_digest(left_bytes, right_bytes)
    except UnicodeError:
        return False


class TestStatus(StrEnum):
    PENDING = "pending"
    ONCE_ACKNOWLEDGED = "once_acknowledged"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"
    CLEANUP_PENDING = "cleanup_pending"


@dataclass(frozen=True, slots=True)
class TestOutcome:
    status: TestStatus


@dataclass(frozen=True, slots=True)
class TargetBinding:
    """Canonical target identity copied from the gateway by a future separately gated caller."""

    instance_id: str
    user_id: str
    profile: str
    session_id: str
    device_id: str


@dataclass(frozen=True, slots=True)
class TestNotice:
    """In-memory notification input; native routing data is deliberately not exposed."""

    instance_id: str
    user_id: str
    profile: str
    session_id: str
    device_id: str
    request_id: str
    command: str = _COMMAND
    description: str = _DESCRIPTION
    choices: tuple[str, str] = ("once", "deny")
    deadline_monotonic: float = 0.0


@dataclass(frozen=True, slots=True)
class _BoundFunction:
    module: ModuleType
    name: str
    function: Callable[..., Any]
    parameter_names: tuple[str, ...]
    surface_keyword_only: bool = False


class NativeApprovalBindings:
    """Exact sampled callable bindings, captured by the Hermes-only bridge module."""

    def __init__(
        self,
        *,
        waiter_module: ModuleType,
        approval_module: ModuleType,
        interrupt_module: ModuleType,
    ) -> None:
        if (
            type(waiter_module) is not ModuleType
            or waiter_module.__name__ != "tools.approval_gateway_wait"
            or type(approval_module) is not ModuleType
            or approval_module.__name__ != "tools.approval"
            or type(interrupt_module) is not ModuleType
            or interrupt_module.__name__ != "tools.interrupt"
        ):
            raise ValueError("approval test helper unavailable")
        self.waiter_module = waiter_module
        self.approval_module = approval_module
        self.interrupt_module = interrupt_module
        self.waiter = self._bind(
            waiter_module,
            "_await_gateway_decision",
            ("session_key", "notify_cb", "approval_data", "surface"),
            surface_keyword_only=True,
        )
        self.resolver = self._bind(
            approval_module,
            "resolve_gateway_approval",
            ("session_key", "choice", "resolve_all", "reason", "request_id"),
        )
        self.withdrawer = self._bind(
            approval_module,
            "withdraw_gateway_approval",
            ("session_key", "request_id", "cause"),
        )
        self.lister = self._bind(approval_module, "list_gateway_approvals", ("session_key",))
        self.interrupted = self._bind(interrupt_module, "is_interrupted", ())

    @staticmethod
    def _bind(
        module: ModuleType,
        name: str,
        parameter_names: tuple[str, ...],
        *,
        surface_keyword_only: bool = False,
    ) -> _BoundFunction:
        try:
            function = getattr(module, name, None)
        except BaseException:
            raise ValueError("approval test helper unavailable") from None
        if not callable(function):
            raise ValueError("approval test helper unavailable")
        bound = _BoundFunction(module, name, function, parameter_names, surface_keyword_only)
        if not NativeApprovalBindings._shape_matches(bound):
            raise ValueError("approval test helper unavailable")
        return bound

    @staticmethod
    def _shape_matches(bound: _BoundFunction) -> bool:
        try:
            signature = inspect.signature(bound.function)
        except (TypeError, ValueError):
            return False
        params = tuple(signature.parameters.values())
        if tuple(p.name for p in params) != bound.parameter_names:
            return False
        if any(
            p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in params
        ):
            return False
        if bound.surface_keyword_only:
            return (
                params[-1].kind is inspect.Parameter.KEYWORD_ONLY
                and params[-1].default == "gateway"
                and all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params[:-1])
            )
        expected_defaults: tuple[tuple[str, object], ...] = ()
        if bound.name == "resolve_gateway_approval":
            expected_defaults = (("resolve_all", False), ("reason", None), ("request_id", None))
        if any(
            signature.parameters[name].default != default for name, default in expected_defaults
        ):
            return False
        return all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)

    def current(self) -> bool:
        """Fail closed on module replacement, callable replacement, or call-shape drift."""
        try:
            bound = (self.waiter, self.resolver, self.withdrawer, self.lister, self.interrupted)
            for item in bound:
                if sys.modules.get(item.module.__name__) is not item.module:
                    return False
                if getattr(item.module, item.name, None) is not item.function:
                    return False
                if not self._shape_matches(item):
                    return False
            return True
        except BaseException:
            return False


@dataclass(slots=True)
class _Operation:
    loop: asyncio.AbstractEventLoop
    generation: int
    handle: str
    route_key: str
    request_id: str
    marker: str
    target: TargetBinding
    deadline: float
    intent: str | None = None
    invoke_started: bool = False
    native_touched: bool = False
    callback_seen: bool = False
    row: TestNotice | None = None
    answer_choice: str | None = None
    answer_count: int | None = None
    withdrawal_return: bool | None = None
    control_inflight: bool = False
    worker: threading.Thread | None = None
    control_worker: threading.Thread | None = None
    worker_result: object = None
    worker_result_valid: bool = False
    worker_result_applied: bool = False
    worker_error: bool = False
    row_removal_ok: bool = True
    row_removal_attempted: bool = False
    worker_joined: bool = False
    control_joined: bool = True
    control_result_applied: bool = True
    cleanup_started: bool = False
    cleanup_finished: bool = False
    cleanup_proved: bool = False
    outcome: TestStatus | None = None
    deadline_handle: asyncio.TimerHandle | None = None
    status_waiters: list[asyncio.Future[TestOutcome]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Completed:
    handle: str
    device_id: str
    outcome: TestOutcome


@dataclass(slots=True)
class _ProcessSlot:
    """Share a process slot; service replacement cannot drop a live worker."""

    operation: _Operation | None = None
    completed: _Completed | None = None
    generation: int = 0
    guard: threading.Lock = field(default_factory=threading.Lock)


_PROCESS_SLOT = _ProcessSlot()


class ApprovalTestProducer:
    """One-slot in-process producer. Caller authentication and projection are separate gates."""

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        native: NativeApprovalBindings,
        publish: Callable[[TestNotice], object],
        remove: Callable[[TestNotice], object],
        slot: _ProcessSlot | None = None,
    ) -> None:
        """The row adapters are synchronous and memory-only.

        `publish` returns literal True only after inserting this exact notice. `remove` is
        idempotent and returns literal True only when this exact notice is absent; it must not
        remove a row by a broad session/profile selector.
        """
        self._loop = loop
        if (
            type(native) is not NativeApprovalBindings
            or not callable(publish)
            or not callable(remove)
        ):
            raise ValueError("approval test helper unavailable")
        self._native = native
        self._publish = publish
        self._remove = remove
        self._slot = _PROCESS_SLOT if slot is None else slot
        self._clock = loop.time

    @staticmethod
    def _valid_binding(target: object) -> bool:
        if type(target) is not TargetBinding:
            return False
        for value in (
            target.instance_id,
            target.user_id,
            target.profile,
            target.session_id,
            target.device_id,
        ):
            if type(value) is not str or not value:
                return False
            try:
                raw = value.encode("utf-8", errors="strict")
            except UnicodeError:
                return False
            if len(raw) > _MAX_BINDING_BYTES or any(
                unicodedata.category(ch) == "Cc" for ch in value
            ):
                return False
        return True

    def _on_loop(self) -> bool:
        try:
            return asyncio.get_running_loop() is self._loop
        except RuntimeError:
            return False

    async def begin_test(self, target: TargetBinding, timeout_ms: int) -> str | TestOutcome:
        if not self._on_loop() or not self._valid_binding(target):
            return TestOutcome(TestStatus.UNAVAILABLE)
        if type(timeout_ms) is not int or not _MIN_TIMEOUT_MS <= timeout_ms <= _MAX_TIMEOUT_MS:
            return TestOutcome(TestStatus.UNAVAILABLE)
        if not self._native.current():
            return TestOutcome(TestStatus.UNAVAILABLE)
        try:
            now = self._clock()
            if type(now) not in (int, float):
                return TestOutcome(TestStatus.UNAVAILABLE)
            deadline = float(now) + timeout_ms / 1000.0
        except (OverflowError, TypeError, ValueError):
            return TestOutcome(TestStatus.UNAVAILABLE)
        if not deadline > float(now):
            return TestOutcome(TestStatus.UNAVAILABLE)
        # The lock protects only process-wide slot reservation/release. It never spans native calls,
        # callbacks, awaits, or thread joins.
        handle = secrets.token_hex(32)
        request_id = secrets.token_hex(16)
        marker = secrets.token_hex(32)
        route_key = _ROUTE_PREFIX + secrets.token_hex(32)
        if (
            not _HANDLE_RE.fullmatch(handle)
            or not _REQUEST_RE.fullmatch(request_id)
            or not _MARKER_RE.fullmatch(marker)
            or not _ROUTE_RE.fullmatch(route_key)
            or route_key == target.session_id
        ):
            return TestOutcome(TestStatus.UNAVAILABLE)
        with self._slot.guard:
            if self._slot.operation is not None:
                return TestOutcome(TestStatus.UNAVAILABLE)
            self._slot.generation += 1
            generation = self._slot.generation
            op = _Operation(
                self._loop, generation, handle, route_key, request_id, marker, target, deadline
            )
            self._slot.operation = op
        try:
            op.deadline_handle = self._loop.call_at(deadline, self._deadline_fired, op)
        except RuntimeError:
            with self._slot.guard:
                if self._slot.operation is op:
                    self._slot.operation = None
            return TestOutcome(TestStatus.UNAVAILABLE)
        worker = threading.Thread(
            target=self._worker_entry,
            args=(op,),
            name="hmp-approval-test-wait",
            daemon=False,
        )
        op.worker = worker
        try:
            worker.start()
        except Exception:
            if worker.is_alive():
                op.intent = "failure"
                self._schedule_join(op)
            else:
                op.worker_error = True
                op.worker_result_applied = True
                with self._slot.guard:
                    if self._slot.operation is op:
                        self._slot.operation = None
                if op.deadline_handle is not None:
                    op.deadline_handle.cancel()
            return TestOutcome(TestStatus.UNAVAILABLE)
        return handle

    async def answer_test(
        self, handle: str, authenticated_device_id: str, choice: str
    ) -> TestOutcome:
        if not self._on_loop():
            return TestOutcome(TestStatus.UNAVAILABLE)
        op = self._matching(handle, authenticated_device_id)
        if op is None or type(choice) is not str or choice not in ("once", "deny"):
            return TestOutcome(TestStatus.UNAVAILABLE)
        if op.intent is not None or op.row is None or self._clock() >= op.deadline:
            if op.intent is None and self._clock() >= op.deadline:
                self._deadline_fired(op)
            return self._public_outcome(op)
        if op.control_inflight or not self._native.current():
            return self._public_outcome(op)
        op.intent = "answer_" + choice
        op.control_inflight = True
        op.control_joined = False
        op.answer_choice = choice
        self._start_control(op, "answer", choice)
        return self._public_outcome(op)

    async def cancel_test(self, handle: str, authenticated_device_id: str) -> TestOutcome:
        if not self._on_loop():
            return TestOutcome(TestStatus.UNAVAILABLE)
        op = self._matching(handle, authenticated_device_id)
        if op is None:
            return TestOutcome(TestStatus.UNAVAILABLE)
        if op.intent is not None:
            return self._public_outcome(op)
        op.intent = "cancel"
        self._remove_row(op)
        if op.invoke_started and not op.control_inflight and self._native.current():
            op.control_inflight = True
            op.control_joined = False
            self._start_control(op, "withdraw", "operator_cancel")
        return self._public_outcome(op)

    async def outcome(self, handle: str, authenticated_device_id: str) -> TestOutcome:
        if not self._on_loop():
            return TestOutcome(TestStatus.UNAVAILABLE)
        op = self._matching(handle, authenticated_device_id)
        if op is not None:
            return self._public_outcome(op)
        return self._completed_outcome(handle, authenticated_device_id)

    # The timeout bounds this observer only; the operation has its fixed admission deadline.
    async def wait_outcome(
        self,
        handle: str,
        authenticated_device_id: str,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> TestOutcome:
        if not self._on_loop():
            return TestOutcome(TestStatus.UNAVAILABLE)
        op = self._matching(handle, authenticated_device_id)
        if op is None:
            return self._completed_outcome(handle, authenticated_device_id)
        if op.cleanup_finished:
            return self._public_outcome(op)
        future: asyncio.Future[TestOutcome] = self._loop.create_future()
        op.status_waiters.append(future)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return self._public_outcome(op)
        finally:
            if future in op.status_waiters:
                op.status_waiters.remove(future)

    async def close(self) -> TestOutcome:
        if not self._on_loop():
            return TestOutcome(TestStatus.UNAVAILABLE)
        op = self._slot.operation
        if op is not None and op.loop is not self._loop:
            return TestOutcome(TestStatus.UNAVAILABLE)
        if op is None:
            return TestOutcome(TestStatus.CANCELLED)
        if op.intent is None:
            op.intent = "shutdown"
            self._remove_row(op)
            if op.invoke_started and not op.control_inflight and self._native.current():
                op.control_inflight = True
                op.control_joined = False
                self._start_control(op, "withdraw", "gateway_shutdown")
        return self._public_outcome(op)

    def _matching(self, handle: object, device_id: object) -> _Operation | None:
        op = self._slot.operation
        if (
            op is None
            or op.loop is not self._loop
            or type(handle) is not str
            or not _HANDLE_RE.fullmatch(handle)
            or not _same_text(handle, op.handle)
            or type(device_id) is not str
            or not _same_text(device_id, op.target.device_id)
        ):
            return None
        return op

    def _completed_outcome(self, handle: object, device_id: object) -> TestOutcome:
        with self._slot.guard:
            completed = self._slot.completed
        if (
            completed is not None
            and type(handle) is str
            and type(device_id) is str
            and _same_text(handle, completed.handle)
            and _same_text(device_id, completed.device_id)
        ):
            return completed.outcome
        return TestOutcome(TestStatus.UNAVAILABLE)

    @staticmethod
    def _public_outcome(op: _Operation | None) -> TestOutcome:
        if op is None:
            return TestOutcome(TestStatus.UNAVAILABLE)
        if op.cleanup_finished:
            return TestOutcome(op.outcome or TestStatus.UNAVAILABLE)
        if op.outcome is not None:
            return TestOutcome(TestStatus.CLEANUP_PENDING)
        if op.intent in ("cancel", "shutdown"):
            return TestOutcome(
                TestStatus.PENDING if not op.worker_joined else TestStatus.CLEANUP_PENDING
            )
        if op.intent == "expiry" or op.intent == "native_timeout":
            return TestOutcome(
                TestStatus.PENDING if not op.worker_joined else TestStatus.CLEANUP_PENDING
            )
        return TestOutcome(TestStatus.PENDING)

    def _deadline_fired(self, op: _Operation) -> None:
        if self._slot.operation is not op or op.outcome is not None:
            return
        if self._clock() < op.deadline:
            return
        if op.intent is None:
            op.intent = "expiry"
            self._remove_row(op)
            if op.invoke_started and not op.control_inflight and self._native.current():
                op.control_inflight = True
                op.control_joined = False
                self._start_control(op, "withdraw", "operator_deadline")
        self._notify_waiters(op)

    def _worker_entry(self, op: _Operation) -> None:
        result: object = None
        error = False
        try:
            result = contextvars.Context().run(self._invoke_waiter, op)
        except BaseException:
            error = True
        # A closed loop keeps the slot charged; it never proves completed cleanup.
        with contextlib.suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._worker_returned, op, result, error)

    def _invoke_waiter(self, op: _Operation) -> object:
        if not self._native.current():
            raise RuntimeError("approval test helper unavailable")
        interrupted = self._native.interrupted.function()
        if type(interrupted) is not bool or interrupted:
            raise RuntimeError("approval test unavailable")
        if not self._native.current():
            raise RuntimeError("approval test helper unavailable")
        rows = self._native.lister.function(op.route_key)
        if type(rows) is not list or rows:
            raise RuntimeError("approval test unavailable")
        allowed = self._loop_call(self._prepare_invocation, op, deadline=op.deadline)
        if allowed is not True:
            return _NOT_INVOKED
        if not self._native.current():
            raise RuntimeError("approval test helper unavailable")
        data = {
            "request_id": op.request_id,
            "synthetic_marker": op.marker,
            "command": _COMMAND,
            "description": _DESCRIPTION,
            "pattern_key": "",
            "pattern_keys": [],
        }
        return self._native.waiter.function(
            op.route_key,
            lambda callback_data: self._notify_callback(op, callback_data),
            data,
            surface="gateway",
        )

    def _loop_call(self, fn: Callable[..., Any], *args: Any, deadline: float) -> Any:
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()

        def run() -> None:
            if not future.cancelled():
                try:
                    future.set_result(fn(*args))
                except BaseException as exc:
                    future.set_exception(exc)

        self._loop.call_soon_threadsafe(run)
        remaining = deadline - self._loop.time()
        if remaining <= 0:
            raise TimeoutError
        return future.result(timeout=remaining)

    def _prepare_invocation(self, op: _Operation) -> bool:
        try:
            if (
                self._slot.operation is not op
                or op.intent is not None
                or self._clock() >= op.deadline
                or not self._native.current()
            ):
                return False
        except BaseException:
            return False
        # From this point onward the worker may enter the native waiter even if cancellation races
        # immediately after this loop turn. Cleanup therefore treats enqueue as possible.
        op.native_touched = True
        op.invoke_started = True
        return True

    def _notify_callback(self, op: _Operation, data: object) -> None:
        future: concurrent.futures.Future[None] = concurrent.futures.Future()

        def on_loop() -> None:
            self._accept_callback(op, data, future)

        try:
            self._loop.call_soon_threadsafe(on_loop)
            remaining = op.deadline - self._loop.time()
            if remaining <= 0:
                raise TimeoutError
            future.result(timeout=remaining)
        except BaseException:
            with contextlib.suppress(RuntimeError):
                self._loop.call_soon_threadsafe(self._callback_wait_failed, op)
            raise RuntimeError(_NOTIFY_FAILED) from None

    def _accept_callback(
        self, op: _Operation, data: object, future: concurrent.futures.Future[None]
    ) -> None:
        if future.done():
            return
        if (
            self._slot.operation is not op
            or op.callback_seen
            or op.intent is not None
            or self._clock() >= op.deadline
            or not self._callback_shape(op, data)
        ):
            future.set_exception(RuntimeError(_NOTIFY_FAILED))
            return
        op.callback_seen = True
        notice = TestNotice(
            instance_id=op.target.instance_id,
            user_id=op.target.user_id,
            profile=op.target.profile,
            session_id=op.target.session_id,
            device_id=op.target.device_id,
            request_id=op.request_id,
            deadline_monotonic=op.deadline,
        )
        # This synchronous commit runs on the service loop. Expiry and publication are serialized;
        # a post-call deadline check removes a row before the loop can serve another request.
        op.row = notice
        try:
            published = self._publish(notice)
        except BaseException:
            self._remove_row(op)
            future.set_exception(RuntimeError(_NOTIFY_FAILED))
            return
        if inspect.isawaitable(published):
            if inspect.iscoroutine(published):
                published.close()
            self._remove_row(op)
            future.set_exception(RuntimeError(_NOTIFY_FAILED))
            return
        if published is not True:
            self._remove_row(op)
            future.set_exception(RuntimeError(_NOTIFY_FAILED))
            return
        if self._slot.operation is not op or op.intent is not None or self._clock() >= op.deadline:
            self._remove_row(op)
            future.set_exception(RuntimeError(_NOTIFY_FAILED))
            return
        future.set_result(None)
        self._notify_waiters(op)

    @staticmethod
    def _callback_shape(op: _Operation, data: object) -> bool:
        if type(data) is not dict or set(data) != {
            "request_id",
            "synthetic_marker",
            "command",
            "description",
            "pattern_key",
            "pattern_keys",
        }:
            return False
        return (
            type(data.get("request_id")) is str
            and data.get("request_id") == op.request_id
            and type(data.get("synthetic_marker")) is str
            and data.get("synthetic_marker") == op.marker
            and type(data.get("command")) is str
            and data.get("command") == _COMMAND
            and type(data.get("description")) is str
            and data.get("description") == _DESCRIPTION
            and type(data.get("pattern_key")) is str
            and data.get("pattern_key") == ""
            and type(data.get("pattern_keys")) is list
            and data.get("pattern_keys") == []
        )

    def _callback_wait_failed(self, op: _Operation) -> None:
        if self._slot.operation is op and op.intent is None:
            op.intent = "failure"
            self._remove_row(op)
            self._notify_waiters(op)

    def _start_control(self, op: _Operation, action: str, value: str) -> None:
        def run() -> None:
            result: object = None
            error = False
            try:
                if not self._native.current():
                    raise RuntimeError("approval test helper unavailable")
                if action == "answer":
                    result = self._native.resolver.function(
                        op.route_key, value, resolve_all=False, request_id=op.request_id
                    )
                elif action == "withdraw":
                    result = self._native.withdrawer.function(op.route_key, op.request_id, value)
                else:
                    error = True
            except BaseException:
                error = True
            with contextlib.suppress(RuntimeError):
                self._loop.call_soon_threadsafe(self._control_returned, op, action, result, error)

        thread = threading.Thread(
            target=lambda: contextvars.Context().run(run),
            name="hmp-approval-test-control",
            daemon=False,
        )
        op.control_worker = thread
        op.control_joined = False
        op.control_result_applied = False
        try:
            thread.start()
        except Exception:
            op.control_joined = True
            op.control_result_applied = True
            op.control_inflight = False
            op.intent = "failure"
            op.outcome = TestStatus.UNAVAILABLE
            self._remove_row(op)
            self._schedule_join(op)

    def _control_returned(self, op: _Operation, action: str, result: object, error: bool) -> None:
        if self._slot.operation is not op:
            return
        op.control_result_applied = True
        op.control_inflight = False
        if action == "answer":
            if not error and type(result) is int and result == 1:
                op.answer_count = 1
                self._remove_row(op)
            else:
                op.answer_count = -1
                op.intent = "failure"
                self._remove_row(op)
        elif action == "withdraw":
            if not error and type(result) is bool:
                op.withdrawal_return = result
            else:
                op.withdrawal_return = None
            self._remove_row(op)
        self._notify_waiters(op)
        self._schedule_join(op)

    def _worker_returned(self, op: _Operation, result: object, error: bool) -> None:
        if self._slot.operation is not op:
            return
        op.worker_result = result
        op.worker_error = error
        op.worker_result_valid = self._valid_worker_result(result)
        op.worker_result_applied = True
        self._schedule_join(op)

    @staticmethod
    def _valid_worker_result(result: object) -> bool:
        if result is _NOT_INVOKED:
            return True
        if type(result) is not dict:
            return False
        keys = set(result)
        if keys == {"resolved", "choice", "reason"}:
            resolved = result.get("resolved")
            choice = result.get("choice")
            reason = result.get("reason")
            if type(resolved) is not bool or (
                reason is not None
                and (type(reason) is not str or len(reason.encode("utf-8", "replace")) > 256)
            ):
                return False
            if resolved:
                return type(choice) is str and choice in ("once", "deny")
            return choice is None
        if keys == {"resolved", "choice", "reason", "cancelled"}:
            return (
                result.get("resolved") is True
                and result.get("choice") is None
                and (
                    result.get("reason") is None
                    or (
                        type(result.get("reason")) is str
                        and len(result.get("reason").encode("utf-8", "replace")) <= 256
                    )
                )
                and type(result.get("cancelled")) is str
                and len(result.get("cancelled").encode("utf-8", "replace")) <= 128
            )
        if keys == {"resolved", "choice", "notify_failed"}:
            return (
                result.get("resolved") is False
                and result.get("choice") is None
                and result.get("notify_failed") is True
            )
        return False

    def _schedule_join(self, op: _Operation) -> None:
        if self._slot.operation is not op:
            return
        self._loop.call_soon(self._join_progress, op)

    def _join_progress(self, op: _Operation) -> None:
        if self._slot.operation is not op:
            return
        worker = op.worker
        control = op.control_worker
        if worker is not None and worker.is_alive():
            self._loop.call_later(0.01, self._join_progress, op)
            return
        if worker is not None and not op.worker_joined:
            worker.join()
            op.worker_joined = True
        if control is not None and control.is_alive():
            self._loop.call_later(0.01, self._join_progress, op)
            return
        if control is not None and not op.control_joined:
            control.join()
            op.control_joined = True
        # A thread can enqueue its loop callback and exit before this poll runs. Joining the OS
        # thread is not proof that the loop has applied its result. Keep the slot charged until
        # both operation-bound result messages have been consumed.
        if (
            op.worker is None
            or not op.worker_joined
            or not op.worker_result_applied
            or not op.control_joined
            or not op.control_result_applied
        ):
            self._loop.call_later(0.01, self._join_progress, op)
            return
        self._finalize_worker(op)

    def _finalize_worker(self, op: _Operation) -> None:
        if op.cleanup_started:
            return
        op.cleanup_started = True
        op.outcome = self._reconcile(op)
        self._remove_row(op)
        if not op.row_removal_ok:
            op.outcome = TestStatus.UNAVAILABLE
        if not op.native_touched:
            op.cleanup_proved = True
            self._finish_cleanup(op, True)
            return

        def cleanup() -> None:
            proved = False
            try:
                if not self._native.current():
                    raise RuntimeError("approval test helper unavailable")
                rows = self._native.lister.function(op.route_key)
                ids = self._row_ids(rows)
                if ids is None:
                    raise RuntimeError("approval test unavailable")
                if op.request_id in ids:
                    if not self._native.current():
                        raise RuntimeError("approval test helper unavailable")
                    removed = self._native.withdrawer.function(
                        op.route_key, op.request_id, "test_cleanup"
                    )
                    if type(removed) is not bool or removed is not True:
                        raise RuntimeError("approval test unavailable")
                    if not self._native.current():
                        raise RuntimeError("approval test helper unavailable")
                    rows = self._native.lister.function(op.route_key)
                    ids = self._row_ids(rows)
                    if ids is None:
                        raise RuntimeError("approval test unavailable")
                proved = op.request_id not in ids
            except BaseException:
                proved = False
            with contextlib.suppress(RuntimeError):
                self._loop.call_soon_threadsafe(self._finish_cleanup, op, proved)

        thread = threading.Thread(
            target=lambda: contextvars.Context().run(cleanup),
            name="hmp-approval-test-cleanup",
            daemon=False,
        )
        op.control_worker = thread
        op.control_joined = False
        try:
            thread.start()
        except Exception:
            op.control_joined = True
            self._finish_cleanup(op, False)

    @staticmethod
    def _row_ids(rows: object) -> set[str] | None:
        if type(rows) is not list or len(rows) > 128:
            return None
        result: set[str] = set()
        for row in rows:
            if type(row) is not dict:
                return None
            request_id = row.get("request_id")
            if type(request_id) is not str or not request_id or len(request_id) > 128:
                return None
            if request_id in result:
                return None
            result.add(request_id)
        return result

    @staticmethod
    def _reconcile(op: _Operation) -> TestStatus:
        if op.worker_error or not op.worker_result_valid:
            return TestStatus.UNAVAILABLE
        result = op.worker_result
        if result is _NOT_INVOKED and not op.invoke_started and not op.native_touched:
            if op.intent == "cancel" or op.intent == "shutdown":
                return TestStatus.CANCELLED
            if op.intent == "expiry" or op.intent == "native_timeout":
                return TestStatus.EXPIRED
            return TestStatus.UNAVAILABLE
        if type(result) is not dict:
            return TestStatus.UNAVAILABLE
        resolved = result.get("resolved")
        choice = result.get("choice")
        if "notify_failed" in result:
            return TestStatus.UNAVAILABLE
        if "cancelled" in result:
            expected_cause = {
                "cancel": "operator_cancel",
                "shutdown": "gateway_shutdown",
                "expiry": "operator_deadline",
            }.get(op.intent)
            if (
                expected_cause is not None
                and op.withdrawal_return is True
                and result.get("cancelled") == expected_cause
            ):
                if op.intent == "expiry":
                    return TestStatus.EXPIRED
                return TestStatus.CANCELLED
            return TestStatus.UNAVAILABLE
        if not resolved:
            if op.intent in (None, "expiry", "native_timeout"):
                return TestStatus.EXPIRED
            return TestStatus.UNAVAILABLE
        if type(choice) is str and choice in ("once", "deny"):
            if op.answer_count != 1 or op.answer_choice != choice:
                return TestStatus.UNAVAILABLE
            return TestStatus.ONCE_ACKNOWLEDGED if choice == "once" else TestStatus.DENIED
        return TestStatus.UNAVAILABLE

    def _finish_cleanup(self, op: _Operation, proved: bool) -> None:
        if self._slot.operation is not op:
            return
        control = op.control_worker
        if control is not None and control.is_alive():
            self._loop.call_later(0.01, self._finish_cleanup, op, proved)
            return
        if control is not None and not op.control_joined:
            control.join()
            op.control_joined = True
        op.cleanup_proved = proved
        if not proved:
            op.outcome = op.outcome or TestStatus.UNAVAILABLE
            self._notify_waiters(op)
            return
        if op.row is not None or not op.row_removal_ok:
            op.outcome = op.outcome or TestStatus.UNAVAILABLE
            self._notify_waiters(op)
            return
        op.cleanup_finished = True
        if op.deadline_handle is not None:
            op.deadline_handle.cancel()
        self._notify_waiters(op)
        with self._slot.guard:
            if self._slot.operation is op:
                self._slot.completed = _Completed(
                    op.handle,
                    op.target.device_id,
                    TestOutcome(op.outcome or TestStatus.UNAVAILABLE),
                )
                self._slot.operation = None

    def _remove_row(self, op: _Operation) -> None:
        if op.row is not None and not op.row_removal_attempted:
            op.row_removal_attempted = True
            removed = self._remove_safely(op.row)
            op.row_removal_ok = removed and op.row_removal_ok
            if removed:
                op.row = None

    def _remove_safely(self, notice: TestNotice) -> bool:
        try:
            result = self._remove(notice)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                return False
            return result is True
        except BaseException:
            return False

    def _notify_waiters(self, op: _Operation) -> None:
        if not op.cleanup_finished:
            return
        result = TestOutcome(op.outcome or TestStatus.UNAVAILABLE)
        for future in tuple(op.status_waiters):
            if not future.done():
                future.set_result(result)
        op.status_waiters.clear()
