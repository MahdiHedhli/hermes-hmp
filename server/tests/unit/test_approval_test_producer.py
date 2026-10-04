"""Finite fake-native controls for the synthetic approval producer contract.

These tests use only in-memory modules, queues, barriers, and rows. They do not import Hermes.
The module remains unwired to a CLI, route, or Phone adapter.
"""

from __future__ import annotations

import asyncio
import contextvars
import sys
import threading
import time
import types
from dataclasses import dataclass
from typing import Any

import pytest

from hmp_plugin.approval_test_producer import (
    ApprovalTestProducer,
    NativeApprovalBindings,
    TargetBinding,
    TestNotice,
    TestOutcome,
    TestStatus,
    _ProcessSlot,
)

TARGET = TargetBinding("instance-a", "user-a", "alpha", "session-a", "device-é")


@dataclass
class _Entry:
    data: dict[str, object]
    event: threading.Event
    result: dict[str, object] | None = None


class _FakeNative:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.lock = threading.Lock()
        self.queues: dict[str, list[_Entry]] = {}
        self.resolver_calls: list[tuple[str, str, str]] = []
        self.withdraw_calls: list[tuple[str, str, str]] = []
        self.block_after_notify = True
        self.bad_callback = False
        self.bad_result: dict[str, object] | None = None
        self.resolve_count: object = 1
        self.withdraw_override: object | None = None
        self.withdraw_error = False
        self.interrupted = False
        self.callback_gate: threading.Event | None = None
        self.list_gate_at_call: int | None = None
        self.list_gate = threading.Event()
        self.list_entered = threading.Event()
        self.duplicate_callback = False
        self.context_probe: contextvars.ContextVar[str] | None = None
        self.context_seen: str | None = None
        self.resolve_gate: threading.Event | None = None
        self.resolve_entered = threading.Event()
        self.force_timeout = threading.Event()
        self.live_withdraw_false_once = False
        self.malformed_list_call: int | None = None
        self.list_calls = 0
        self.waiter_exited = threading.Event()
        self.cleanup_after_waiter_exit: list[bool] = []

        waiter_module = types.ModuleType("tools.approval_gateway_wait")
        approval_module = types.ModuleType("tools.approval")
        interrupt_module = types.ModuleType("tools.interrupt")
        waiter_module._await_gateway_decision = self.waiter
        approval_module.resolve_gateway_approval = self.resolve
        approval_module.withdraw_gateway_approval = self.withdraw
        approval_module.list_gateway_approvals = self.list_rows
        interrupt_module.is_interrupted = self.is_interrupted
        monkeypatch.setitem(sys.modules, waiter_module.__name__, waiter_module)
        monkeypatch.setitem(sys.modules, approval_module.__name__, approval_module)
        monkeypatch.setitem(sys.modules, interrupt_module.__name__, interrupt_module)
        self.bindings = NativeApprovalBindings(
            waiter_module=waiter_module,
            approval_module=approval_module,
            interrupt_module=interrupt_module,
        )

    def waiter(
        self,
        session_key: str,
        notify_cb: Any,
        approval_data: dict[str, object],
        *,
        surface: str = "gateway",
    ) -> dict[str, object]:
        if self.context_probe is not None:
            self.context_seen = self.context_probe.get(None)
        try:
            return self._waiter_impl(session_key, notify_cb, approval_data, surface=surface)
        finally:
            self.waiter_exited.set()

    def _waiter_impl(
        self,
        session_key: str,
        notify_cb: Any,
        approval_data: dict[str, object],
        *,
        surface: str,
    ) -> dict[str, object]:
        assert surface == "gateway"
        entry = _Entry(dict(approval_data), threading.Event())
        with self.lock:
            self.queues.setdefault(session_key, []).append(entry)
        if self.callback_gate is not None:
            self.callback_gate.wait(3.0)
        callback_data = dict(approval_data)
        if self.bad_callback:
            callback_data["request_id"] = "wrong"
        try:
            notify_cb(callback_data)
            if self.duplicate_callback:
                notify_cb(callback_data)
        except Exception:
            with self.lock:
                queue = self.queues.get(session_key, [])
                if entry in queue:
                    queue.remove(entry)
                if not queue:
                    self.queues.pop(session_key, None)
            return {"resolved": False, "choice": None, "notify_failed": True}
        if not self.block_after_notify:
            with self.lock:
                queue = self.queues.get(session_key, [])
                if entry in queue:
                    queue.remove(entry)
                if not queue:
                    self.queues.pop(session_key, None)
            return {"resolved": False, "choice": None, "reason": None}
        end_at = time.monotonic() + 3.0
        while not entry.event.wait(0.01):
            if self.force_timeout.is_set() or time.monotonic() >= end_at:
                return {"resolved": False, "choice": None, "reason": None}
        if self.bad_result is not None:
            return dict(self.bad_result)
        return entry.result or {"resolved": False, "choice": None, "reason": None}

    def resolve(
        self,
        session_key: str,
        choice: str,
        resolve_all: bool = False,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> int:
        del reason
        self.resolver_calls.append((session_key, choice, request_id or ""))
        if self.resolve_gate is not None:
            self.resolve_entered.set()
            self.resolve_gate.wait(3.0)
        with self.lock:
            queue = self.queues.get(session_key, [])
            entry = next(
                (item for item in queue if item.data.get("request_id") == request_id), None
            )
            if entry is None:
                return 0
            queue.remove(entry)
            if not queue:
                self.queues.pop(session_key, None)
            entry.result = {"resolved": True, "choice": choice, "reason": None}
            entry.event.set()
        return self.resolve_count  # type: ignore[return-value]

    def withdraw(self, session_key: str, request_id: str, cause: str) -> bool:
        self.withdraw_calls.append((session_key, request_id, cause))
        if cause == "test_cleanup":
            self.cleanup_after_waiter_exit.append(self.waiter_exited.is_set())
        if self.withdraw_error and cause == "operator_cancel":
            raise RuntimeError("synthetic withdrawal detail must not escape")
        if self.withdraw_override is not None and cause == "operator_cancel":
            return self.withdraw_override  # type: ignore[return-value]
        if cause == "operator_cancel" and self.live_withdraw_false_once:
            self.live_withdraw_false_once = False
            return False
        with self.lock:
            queue = self.queues.get(session_key, [])
            entry = next(
                (item for item in queue if item.data.get("request_id") == request_id), None
            )
            if entry is None:
                return False
            queue.remove(entry)
            if not queue:
                self.queues.pop(session_key, None)
            entry.result = {
                "resolved": True,
                "choice": None,
                "reason": None,
                "cancelled": cause,
            }
            entry.event.set()
            return True

    def list_rows(self, session_key: str) -> list[dict[str, object]]:
        with self.lock:
            self.list_calls += 1
            call_number = self.list_calls
            if self.list_calls == self.malformed_list_call:
                return None  # type: ignore[return-value]
        if call_number == self.list_gate_at_call:
            self.list_entered.set()
            self.list_gate.wait(3.0)
        with self.lock:
            return [dict(entry.data) for entry in self.queues.get(session_key, [])]

    def is_interrupted(self) -> bool:
        return self.interrupted

    def has_entries(self) -> bool:
        with self.lock:
            return any(self.queues.values())


class _MemoryRows:
    def __init__(self) -> None:
        self.rows: dict[str, TestNotice] = {}
        self.on_publish: Any = None

    def publish(self, notice: TestNotice) -> bool:
        if notice.request_id in self.rows:
            return False
        self.rows[notice.request_id] = notice
        if self.on_publish is not None:
            self.on_publish(notice)
        return True

    def remove(self, notice: TestNotice) -> bool:
        self.rows.pop(notice.request_id, None)
        return True


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _wait_until(predicate: Any) -> None:
    for _ in range(300):
        if predicate():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("bounded fake lifecycle did not reach its barrier")


def _service(native: _FakeNative, rows: _MemoryRows, slot: _ProcessSlot) -> ApprovalTestProducer:
    return ApprovalTestProducer(
        loop=asyncio.get_running_loop(),
        native=native.bindings,
        publish=rows.publish,
        remove=rows.remove,
        slot=slot,
    )


def test_malformed_input_refuses_before_slot_or_native_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        for invalid in (True, 0, -1, 60_001, 1.0):
            result = await service.begin_test(TARGET, invalid)  # type: ignore[arg-type]
            assert result == TestOutcome(TestStatus.UNAVAILABLE)
            assert slot.operation is None
        assert await service.begin_test(object(), 10) == TestOutcome(TestStatus.UNAVAILABLE)  # type: ignore[arg-type]
        invalid_target = TargetBinding("x" * 257, "u", "p", "s", "d")
        assert await service.begin_test(invalid_target, 10) == TestOutcome(TestStatus.UNAVAILABLE)
        control_target = TargetBinding("i", "u", "p", "s\x85", "d")
        assert await service.begin_test(control_target, 10) == TestOutcome(TestStatus.UNAVAILABLE)
        assert slot.operation is None
        assert native.queues == {}
        assert rows.rows == {}

    _run(scenario())


def test_once_acknowledgement_is_exact_and_releases_only_after_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        notice = next(iter(rows.rows.values()))
        assert notice.session_id == TARGET.session_id
        route = next(iter(native.queues))
        assert route != TARGET.session_id
        entry = native.queues[route][0]
        assert entry.data["request_id"] == notice.request_id
        assert entry.data["synthetic_marker"]
        assert set(entry.data) == {
            "request_id",
            "synthetic_marker",
            "command",
            "description",
            "pattern_key",
            "pattern_keys",
        }
        assert await service.answer_test(handle, TARGET.device_id, "once") == TestOutcome(
            TestStatus.PENDING
        )
        outcome = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert outcome == TestOutcome(TestStatus.ONCE_ACKNOWLEDGED)
        assert await service.outcome(handle, TARGET.device_id) == outcome
        assert [call[1] for call in native.resolver_calls] == ["once"]
        assert rows.rows == {}
        assert native.queues == {}
        assert slot.operation is None

    _run(scenario())


def test_cancel_is_a_single_owned_withdrawal_and_keeps_slot_until_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        replacement = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        assert await replacement.begin_test(TARGET, 1_000) == TestOutcome(TestStatus.UNAVAILABLE)
        result = await service.cancel_test(handle, TARGET.device_id)
        assert result.status in (TestStatus.PENDING, TestStatus.CLEANUP_PENDING)
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.CANCELLED)
        assert len(native.withdraw_calls) == 1
        assert native.withdraw_calls[0][2] == "operator_cancel"
        assert rows.rows == {} and native.queues == {} and slot.operation is None

    _run(scenario())


def test_callback_mismatch_never_publishes_or_becomes_an_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.bad_callback = True
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert native.resolver_calls == []
        assert rows.rows == {} and native.queues == {} and slot.operation is None

    _run(scenario())


def test_ambiguous_resolver_count_is_not_retried_or_acknowledged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.resolve_count = 0
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert len(native.resolver_calls) == 1
        assert rows.rows == {} and native.queues == {} and slot.operation is None

    _run(scenario())


def test_interrupted_worker_refuses_before_native_queue_or_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.interrupted = True
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert native.queues == {} and rows.rows == {} and slot.operation is None

    _run(scenario())


def test_starting_cancel_holds_slot_until_delayed_callback_and_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.callback_gate = threading.Event()
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(native.has_entries)
        assert await service.cancel_test(handle, TARGET.device_id) == TestOutcome(
            TestStatus.PENDING
        )
        assert slot.operation is not None
        native.callback_gate.set()
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert rows.rows == {} and native.queues == {} and slot.operation is None
        assert len(native.withdraw_calls) == 1

    _run(scenario())


def test_only_joined_cleanup_may_withdraw_again_and_it_cannot_change_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.live_withdraw_false_once = True
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.cancel_test(handle, TARGET.device_id)
        await _wait_until(lambda: len(native.withdraw_calls) == 1)
        assert slot.operation is not None
        native.force_timeout.set()
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert [call[2] for call in native.withdraw_calls] == ["operator_cancel", "test_cleanup"]
        assert native.cleanup_after_waiter_exit == [True]
        assert rows.rows == {} and native.queues == {} and slot.operation is None

    _run(scenario())


def test_answer_cancel_race_uses_one_local_control_and_requires_joined_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        assert await service.answer_test(handle, "wrong-device", "once") == TestOutcome(
            TestStatus.UNAVAILABLE
        )
        await service.answer_test(handle, TARGET.device_id, "once")
        assert await service.cancel_test(handle, TARGET.device_id) == TestOutcome(
            TestStatus.PENDING
        )
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.ONCE_ACKNOWLEDGED)
        assert len(native.resolver_calls) == 1 and native.withdraw_calls == []
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


def test_unexpected_native_choice_is_unavailable_even_after_one_resolver_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.bad_result = {"resolved": True, "choice": "session", "reason": None}
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert len(native.resolver_calls) == 1
        assert rows.rows == {} and native.queues == {} and slot.operation is None

    _run(scenario())


def test_malformed_post_join_listing_keeps_capacity_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.malformed_list_call = 2  # first is private-key collision check; second is cleanup proof
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=0.1)
        assert final == TestOutcome(TestStatus.CLEANUP_PENDING)
        assert slot.operation is not None
        assert rows.rows == {}
        assert await service.begin_test(TARGET, 100) == TestOutcome(TestStatus.UNAVAILABLE)

    _run(scenario())


@pytest.mark.parametrize("held_name", ["_worker_returned", "_control_returned"])
def test_join_waits_for_both_loop_applied_completion_fences(
    monkeypatch: pytest.MonkeyPatch,
    held_name: str,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        loop = asyncio.get_running_loop()
        original = loop.call_soon_threadsafe
        held = threading.Event()
        queued: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []
        queued_lock = threading.Lock()

        def gated(callback: Any, *args: Any, **kwargs: Any) -> Any:
            if getattr(callback, "__name__", "") == held_name:
                with queued_lock:
                    queued.append((callback, args, kwargs))
                held.set()
                return True
            return original(callback, *args, **kwargs)

        monkeypatch.setattr(loop, "call_soon_threadsafe", gated)
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        assert await service.answer_test(handle, TARGET.device_id, "once") == TestOutcome(
            TestStatus.PENDING
        )
        await _wait_until(held.is_set)
        op = slot.operation
        assert op is not None
        if held_name == "_worker_returned":
            await _wait_until(lambda: op.control_result_applied)
            assert not op.worker_result_applied
        else:
            await _wait_until(lambda: op.worker_result_applied)
            assert not op.control_result_applied
        await asyncio.sleep(0.04)
        assert slot.operation is op
        assert not op.cleanup_started and not op.cleanup_finished
        assert op.outcome is None
        with queued_lock:
            assert len(queued) == 1
            callback, args, kwargs = queued.pop()
        original(callback, *args, **kwargs)
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.ONCE_ACKNOWLEDGED
        )
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


def test_answer_vs_cancel_barrier_keeps_one_control_and_frozen_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.resolve_gate = threading.Event()
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        await _wait_until(native.resolve_entered.is_set)
        op = slot.operation
        assert op is not None and op.control_inflight and not op.control_result_applied
        assert await service.cancel_test(handle, TARGET.device_id) == TestOutcome(
            TestStatus.PENDING
        )
        assert len(native.resolver_calls) == 1 and native.withdraw_calls == []
        native.resolve_gate.set()
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.ONCE_ACKNOWLEDGED
        )
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


def test_native_result_cannot_forge_wrapper_pre_invocation_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.bad_result = {"not_invoked": True}
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        op = slot.operation
        assert op is not None
        await service.answer_test(handle, TARGET.device_id, "once")
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.UNAVAILABLE
        )
        assert op.invoke_started and op.native_touched
        assert len(native.resolver_calls) == 1
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


@pytest.mark.parametrize("intent", ["cancel", "expiry"])
def test_true_pre_call_terminal_intent_uses_private_sentinel_without_waiter_call(
    monkeypatch: pytest.MonkeyPatch,
    intent: str,
) -> None:
    native = _FakeNative(monkeypatch)
    native.list_gate_at_call = 1  # invocation-side private-key inspection, before prepare/invoke
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        clock = [asyncio.get_running_loop().time()]
        service._clock = lambda: clock[0]
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(native.list_entered.is_set)
        op = slot.operation
        assert op is not None and not op.invoke_started and not op.native_touched
        if intent == "cancel":
            assert await service.cancel_test(handle, TARGET.device_id) == TestOutcome(
                TestStatus.PENDING
            )
            expected = TestStatus.CANCELLED
        else:
            clock[0] = op.deadline
            service._deadline_fired(op)
            expected = TestStatus.EXPIRED
        native.list_gate.set()
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            expected
        )
        assert op.worker_result is not None
        assert native.waiter_exited.is_set() is False
        assert native.withdraw_calls == [] and native.resolver_calls == []
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


def test_deadline_during_synchronous_callback_publication_removes_exact_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        clock = [asyncio.get_running_loop().time()]
        service._clock = lambda: clock[0]

        def expire_during_publish(_notice: TestNotice) -> None:
            op = slot.operation
            assert op is not None
            clock[0] = op.deadline
            service._deadline_fired(op)

        rows.on_publish = expire_during_publish
        handle = await service.begin_test(TARGET, 5_000)
        assert isinstance(handle, str)
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert rows.rows == {} and native.queues == {} and slot.operation is None
        assert native.resolver_calls == []

    _run(scenario())


def test_late_callback_after_close_does_not_publish_and_keeps_slot_until_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.callback_gate = threading.Event()
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(native.has_entries)
        op = slot.operation
        assert op is not None and op.invoke_started
        closed = await service.close()
        assert closed.status in (TestStatus.PENDING, TestStatus.CLEANUP_PENDING)
        assert slot.operation is op
        native.callback_gate.set()
        final = await service.wait_outcome(handle, TARGET.device_id, timeout=2.0)
        assert final == TestOutcome(TestStatus.UNAVAILABLE)
        assert rows.rows == {} and native.queues == {} and slot.operation is None
        assert len(native.withdraw_calls) == 1

    _run(scenario())


def test_cleanup_observer_hold_keeps_capacity_until_absence_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.list_gate_at_call = 2  # post-join cleanup list, after the invocation-side collision list
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        await _wait_until(native.list_entered.is_set)
        op = slot.operation
        assert op is not None and op.worker_joined and op.outcome == TestStatus.ONCE_ACKNOWLEDGED
        assert await service.begin_test(TARGET, 1_000) == TestOutcome(TestStatus.UNAVAILABLE)
        assert slot.operation is op
        native.list_gate.set()
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.ONCE_ACKNOWLEDGED
        )
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


@pytest.mark.parametrize("resolver_result", [True, 2])
def test_bool_or_multiple_resolver_count_never_acknowledges(
    monkeypatch: pytest.MonkeyPatch,
    resolver_result: object,
) -> None:
    native = _FakeNative(monkeypatch)
    native.resolve_count = resolver_result
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.UNAVAILABLE
        )
        assert len(native.resolver_calls) == 1
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


@pytest.mark.parametrize("withdraw_mode", ["false", "wrong_type", "raises"])
def test_uncertain_cancel_has_no_live_retry_and_joined_cleanup_only(
    monkeypatch: pytest.MonkeyPatch,
    withdraw_mode: str,
) -> None:
    native = _FakeNative(monkeypatch)
    if withdraw_mode == "false":
        native.withdraw_override = False
    elif withdraw_mode == "wrong_type":
        native.withdraw_override = 1
    else:
        native.withdraw_error = True
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.cancel_test(handle, TARGET.device_id)
        await _wait_until(lambda: len(native.withdraw_calls) == 1)
        native.force_timeout.set()
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.UNAVAILABLE
        )
        assert [call[2] for call in native.withdraw_calls] == ["operator_cancel", "test_cleanup"]
        assert native.cleanup_after_waiter_exit == [True]
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


@pytest.mark.parametrize(
    "bad_result",
    [
        {"resolved": True, "choice": "deny", "reason": None, "cancelled": "operator_cancel"},
        {"resolved": 1, "choice": "once", "reason": None},
        {"resolved": True, "choice": "once", "reason": None, "extra": False},
    ],
)
def test_cancellation_bearing_or_malformed_native_result_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    bad_result: dict[str, object],
) -> None:
    native = _FakeNative(monkeypatch)
    native.bad_result = bad_result
    rows, slot = _MemoryRows(), _ProcessSlot()

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        await service.answer_test(handle, TARGET.device_id, "once")
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.UNAVAILABLE
        )
        assert len(native.resolver_calls) == 1
        assert slot.operation is None and rows.rows == {} and native.queues == {}

    _run(scenario())


def test_duplicate_callback_and_context_substitution_preserve_foreign_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = _FakeNative(monkeypatch)
    native.duplicate_callback = True
    caller_context = contextvars.ContextVar("caller_scope", default=None)
    native.context_probe = caller_context
    rows, slot = _MemoryRows(), _ProcessSlot()
    foreign = _Entry({"request_id": "foreign-sentinel"}, threading.Event())
    native.queues["unrelated-session"] = [foreign]

    async def scenario() -> None:
        token = caller_context.set("caller-only")
        try:
            service = _service(native, rows, slot)
            handle = await service.begin_test(TARGET, 2_000)
            assert isinstance(handle, str)
            assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
                TestStatus.UNAVAILABLE
            )
            assert native.context_seen is None
            assert caller_context.get() == "caller-only"
            assert native.interrupted is False
            assert native.queues == {"unrelated-session": [foreign]}
            assert rows.rows == {} and slot.operation is None
        finally:
            caller_context.reset(token)

    _run(scenario())


@pytest.mark.parametrize("substitution", ["callable", "module"])
def test_native_binding_substitution_refuses_control_without_touching_other_queue(
    monkeypatch: pytest.MonkeyPatch,
    substitution: str,
) -> None:
    native = _FakeNative(monkeypatch)
    rows, slot = _MemoryRows(), _ProcessSlot()
    foreign = _Entry({"request_id": "foreign-sentinel"}, threading.Event())
    native.queues["unrelated-session"] = [foreign]

    async def scenario() -> None:
        service = _service(native, rows, slot)
        handle = await service.begin_test(TARGET, 2_000)
        assert isinstance(handle, str)
        await _wait_until(lambda: bool(rows.rows))
        module = native.bindings.approval_module
        original = module.resolve_gateway_approval
        if substitution == "callable":
            module.resolve_gateway_approval = lambda *args, **kwargs: 1
        else:
            monkeypatch.setitem(sys.modules, module.__name__, types.ModuleType(module.__name__))
        try:
            assert await service.answer_test(handle, TARGET.device_id, "once") == TestOutcome(
                TestStatus.PENDING
            )
            assert native.resolver_calls == []
        finally:
            if substitution == "callable":
                module.resolve_gateway_approval = original
            else:
                monkeypatch.setitem(sys.modules, module.__name__, module)
        native.force_timeout.set()
        assert await service.wait_outcome(handle, TARGET.device_id, timeout=2.0) == TestOutcome(
            TestStatus.EXPIRED
        )
        assert native.queues == {"unrelated-session": [foreign]}
        assert rows.rows == {} and slot.operation is None

    _run(scenario())
