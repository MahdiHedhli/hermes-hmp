"""Spec 015 T030 (I-1): the one synchronous insertion observer per prompt generation.

The observer is driven through the real producers: `PromptStore.put`, `_apply_sse_frame` and
`consume_sse` for Bot Chat, and `AdapterHooks.on_exec_approval` for Phone chat. Concurrency tests
order their steps with events and joins, never with sleeps. No observer is registered in
production code.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import threading
from pathlib import Path
from typing import Any

import aiohttp
import pytest

from hmp_plugin import direct_send as ds
from hmp_plugin import prompts
from hmp_plugin.logging_policy import LOGGER_NAME
from hmp_plugin.prompts import AdapterHooks, ApprovalInserted, PromptRow, PromptStore

from .test_approvals import IID, PROFILE, REQ, RUN, USER, _chunks, _frame

SESSION = "namespace:hmp:dm:phone"
CHOICES = ("once", "session", "always", "deny")
OBSERVER_LOG = "event=prompt_observer outcome=error"


class _Direct(BaseException):
    """A direct `BaseException` subclass that is not `Exception` or `CancelledError`."""


def _raise_group() -> BaseException:
    return BaseExceptionGroup("g", [KeyboardInterrupt()])


CONTAINED = {
    "runtime_error": lambda: RuntimeError("boom"),
    "exception_group": lambda: ExceptionGroup("g", [ValueError("x")]),
    "cancelled": lambda: asyncio.CancelledError(),
}
PROPAGATED = {
    "keyboard_interrupt": KeyboardInterrupt,
    "system_exit": SystemExit,
    "generator_exit": GeneratorExit,
    "base_group_of_cancelled": lambda: BaseExceptionGroup(
        "g", [asyncio.CancelledError()]
    ),
    "base_group_mixed": _raise_group,
    "direct_base_exception": _Direct,
}


def _approval(surface: str = "bot_chat", request_id: str = REQ, **extra: Any) -> PromptRow:
    bot = surface == "bot_chat"
    fields: dict[str, Any] = {
        "iid": IID, "user_id": USER, "profile": PROFILE, "request_id": request_id,
        "kind": "approval", "surface": surface, "choices": CHOICES, "command": "ls",
        "description": "d", "run_id": RUN if bot else None,
        "session_key": None if bot else SESSION, "expires_at": 1_100, "observed_at": 1_000,
    }
    fields.update(extra)
    return PromptRow(**fields)


def _clarify(**extra: Any) -> PromptRow:
    fields: dict[str, Any] = {
        "iid": IID, "user_id": USER, "profile": PROFILE, "request_id": REQ, "kind": "clarify",
        "surface": "phone_chat", "choices": (), "question": "Ship?", "session_key": SESSION,
        "expires_at": 1_100, "observed_at": 1_000,
    }
    fields.update(extra)
    return PromptRow(**fields)


def _key(row: PromptRow) -> tuple[str, str, str, str]:
    return (row.iid, row.user_id, row.profile, row.request_id)


class _Recorder:
    def __init__(self) -> None:
        self.events: list[ApprovalInserted] = []
        self.threads: list[int] = []

    def __call__(self, event: ApprovalInserted) -> None:
        self.events.append(event)
        self.threads.append(threading.get_ident())


def _observed(row: PromptRow | None = None) -> tuple[PromptStore, _Recorder]:
    store = PromptStore(clock=lambda: 1)
    recorder = _Recorder()
    store.set_insertion_observer(recorder)
    if row is not None:
        store.put(row)
    return store, recorder


class _Prompt:
    session_key = SESSION
    command = "echo hi"
    description = "why"
    choices = ("once", "deny")


class _Bridge:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows

    def list_gateway_approvals(self, _key: str) -> list[dict[str, str]]:
        return self.rows


def _hooks(store: PromptStore, rows: list[dict[str, str]]) -> AdapterHooks:
    store.remember_session(SESSION, IID, USER, PROFILE, "c_chat")
    return AdapterHooks(
        store=store, bridge=_Bridge(rows), now=lambda: 9, iid=IID, phone_available=lambda: True
    )


def _bind(store: PromptStore) -> ds.StreamBind:
    return ds.StreamBind(
        store=store, iid=IID, user_id=USER, profile=PROFILE, now=lambda: 5_000, timeout_s=300
    )


def _bot_frames() -> list[bytes]:
    return [
        _frame("run.started", {"run_id": RUN}),
        _frame("message.started", {}),
        _frame("approval.request", {"run_id": RUN, "request_id": REQ, "command": "x",
                                    "description": "d", "choices": ["once", "deny"]}),
        _frame("assistant.completed", {"content": "ok", "session_id": "s1"}),
        _frame("run.completed", {"run_id": RUN}),
        _frame("done", {}),
    ]


def _observer_logs(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.getMessage() == OBSERVER_LOG]


# --- the event ------------------------------------------------------------------------------


def test_event_is_frozen_and_carries_only_the_four_fields() -> None:
    assert [f.name for f in dataclasses.fields(ApprovalInserted)] == [
        "key", "surface", "generation", "expires_at",
    ]
    event = ApprovalInserted(("a", "b", "c", "d"), "bot_chat", 1, None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.surface = "phone_chat"  # type: ignore[misc]


@pytest.mark.parametrize("surface", ["bot_chat", "phone_chat"])
def test_an_inserted_approval_notifies_once_with_the_exact_event(surface: str) -> None:
    row = _approval(surface, expires_at=1_234)
    store, recorder = _observed(row)
    assert recorder.events == [ApprovalInserted(_key(row), surface, store.generation, 1_234)]


def test_expires_at_none_is_passed_through() -> None:
    row = _approval(expires_at=None)
    store, recorder = _observed(row)
    assert recorder.events == [ApprovalInserted(_key(row), "bot_chat", store.generation, None)]


def test_the_event_carries_no_prompt_text_or_session_key() -> None:
    row = _approval("phone_chat", command="SECRET-CMD", description="SECRET-DESC")
    _store, recorder = _observed(row)
    text = repr(recorder.events[0])
    for secret in ("SECRET-CMD", "SECRET-DESC", SESSION, "once", "deny"):
        assert secret not in text


def test_no_observer_by_default_and_put_is_unchanged() -> None:
    store = PromptStore(clock=lambda: 1)
    row = _approval()
    store.put(row)
    assert store.get(_key(row)) is row
    assert store._observer is None


def test_the_stored_log_is_unchanged_and_precedes_the_observer(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = PromptStore(clock=lambda: 1)
    order: list[str] = []
    store.set_insertion_observer(lambda _event: order.append("observer"))
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        store.put(_approval())
    messages = [r.getMessage() for r in caplog.records]
    stored = [m for m in messages if m.startswith("event=prompt_store outcome=stored")]
    assert len(stored) == 1 and OBSERVER_LOG not in messages
    assert order == ["observer"]
    baseline = PromptStore(clock=lambda: 1)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        baseline.put(_approval())
    assert [r.getMessage() for r in caplog.records] == stored


# --- real producers -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_real_sse_path_notifies_once_for_a_bot_chat_approval() -> None:
    store, recorder = _observed()
    await ds.consume_sse(_chunks(*_bot_frames()), bind=_bind(store))
    assert recorder.events == [
        ApprovalInserted((IID, USER, PROFILE, REQ), "bot_chat", store.generation, 5_300)
    ]
    # The observer runs on the loop thread that consumed the stream.
    assert recorder.threads == [threading.get_ident()]


@pytest.mark.asyncio
async def test_unbound_stream_approvals_and_clarify_style_frames_do_not_notify() -> None:
    store, recorder = _observed()
    state = ds._StreamState()
    ds._apply_sse_frame(state, "run.started", {"run_id": RUN}, comment=False, bind=_bind(store))
    ds._apply_sse_frame(
        state,
        "approval.request",
        {"run_id": RUN, "request_id": "", "command": "x", "choices": ["once"]},
        comment=False,
        bind=_bind(store),
    )
    ds._apply_sse_frame(
        state,
        "approval.request",
        {"run_id": RUN, "request_id": REQ, "command": "x", "choices": []},
        comment=False,
        bind=_bind(store),
    )
    assert recorder.events == [] and not store._rows


@pytest.mark.asyncio
async def test_the_real_phone_hook_notifies_once_per_inserted_row() -> None:
    store, recorder = _observed()
    hooks = _hooks(store, [{"command": "echo hi", "request_id": REQ}])
    assert await hooks.on_exec_approval(_Prompt()) is True
    assert [e.key for e in recorder.events] == [(IID, USER, PROFILE, REQ)]
    assert recorder.events[0].surface == "phone_chat"
    assert recorder.events[0].generation == store.generation
    assert recorder.threads == [threading.get_ident()]


@pytest.mark.asyncio
async def test_a_recovery_hook_with_two_matches_notifies_for_each_inserted_row() -> None:
    store, recorder = _observed()
    hooks = _hooks(store, [
        {"command": "echo hi", "request_id": REQ},
        {"command": "echo hi", "request_id": REQ + "b"},
    ])
    assert await hooks.on_exec_approval(_Prompt()) is True
    assert sorted(e.key[3] for e in recorder.events) == [REQ, REQ + "b"]
    # A repeat finds both already open and inserts nothing.
    assert await hooks.on_exec_approval(_Prompt()) is False
    assert len(recorder.events) == 2


# --- refused inserts ------------------------------------------------------------------------


def test_clarify_does_not_notify_but_is_stored() -> None:
    row = _clarify()
    store, recorder = _observed(row)
    assert store.get(_key(row)) is row
    assert recorder.events == []


def test_a_duplicate_key_does_not_notify_again() -> None:
    row = _approval()
    store, recorder = _observed(row)
    store.put(_approval(command="other"))
    store.put(_approval("phone_chat"))  # same key, other surface
    assert len(recorder.events) == 1
    assert store.get(_key(row)) is row


def test_a_closed_generation_refuses_and_does_not_notify() -> None:
    store, recorder = _observed()
    store.close(10)
    store.put(_approval())
    assert recorder.events == [] and not store._rows


def test_a_phone_closed_generation_refuses_phone_rows_but_still_notifies_bot_chat() -> None:
    store, recorder = _observed()
    store.close_phone_chat(10)
    store.put(_approval("phone_chat"))
    assert recorder.events == [] and not store._rows
    bot = _approval("bot_chat", request_id=REQ + "b")
    store.put(bot)
    assert [e.key for e in recorder.events] == [_key(bot)]  # close_phone_chat keeps the observer
    assert store._observer is not None


# --- lifecycle ------------------------------------------------------------------------------


def test_close_clears_the_observer_and_registration_after_close_is_a_no_op() -> None:
    store, recorder = _observed()
    store.close(10)
    assert store._observer is None
    store.set_insertion_observer(recorder)
    assert store._observer is None
    store.put(_approval())
    assert recorder.events == []


def test_clearing_with_none_detaches_and_a_second_observer_replaces_the_first() -> None:
    store, first = _observed()
    second = _Recorder()
    store.set_insertion_observer(second)
    store.put(_approval())
    assert first.events == [] and len(second.events) == 1
    store.set_insertion_observer(None)
    store.put(_approval(request_id=REQ + "b"))
    assert len(second.events) == 1


def test_a_stream_bound_to_an_older_generation_cannot_notify_a_newer_observer() -> None:
    old = PromptStore(clock=lambda: 1)
    new = PromptStore(clock=lambda: 1)
    recorder = _Recorder()
    new.set_insertion_observer(recorder)
    old.close(10)
    old.put(_approval())
    assert recorder.events == [] and old.generation != new.generation


def test_register_takes_the_store_guard() -> None:
    class SpyLock:
        def __init__(self) -> None:
            self.inner = threading.Lock()
            self.entries = 0

        def __enter__(self) -> bool:
            self.entries += 1
            return self.inner.__enter__()

        def __exit__(self, *exc: object) -> None:
            self.inner.__exit__(*exc)

    store = PromptStore(clock=lambda: 1)
    spy = SpyLock()
    store._guard = spy  # type: ignore[assignment]
    store.set_insertion_observer(_Recorder())
    assert spy.entries == 1
    store.set_insertion_observer(None)
    assert spy.entries == 2


# --- the lock -------------------------------------------------------------------------------


def test_the_observer_runs_outside_the_guard_and_may_reenter_the_store() -> None:
    store = PromptStore(clock=lambda: 1)
    seen: dict[str, Any] = {}

    def observer(event: ApprovalInserted) -> None:
        acquired = store._guard.acquire(blocking=False)
        seen["acquired"] = acquired
        if not acquired:
            return  # Report the lock violation without blocking on the following re-entry.
        store._guard.release()
        seen["row"] = store.get(event.key)
        seen["visible"] = store.list_visible(IID, USER, PROFILE, now=1)
        store.set_insertion_observer(None)

    store.set_insertion_observer(observer)
    row = _approval()
    store.put(row)
    assert seen["acquired"] is True
    assert seen["row"] is row and seen["visible"] == (row,)


def test_an_observer_that_puts_another_row_notifies_for_it_too() -> None:
    store = PromptStore(clock=lambda: 1)
    keys: list[str] = []

    def observer(event: ApprovalInserted) -> None:
        keys.append(event.key[3])
        if event.key[3] == REQ:
            store.put(_approval(request_id=REQ + "b"))

    store.set_insertion_observer(observer)
    store.put(_approval())
    assert keys == [REQ, REQ + "b"]


# --- reference capture (deterministic interleavings) ----------------------------------------


def _after_stored(monkeypatch: pytest.MonkeyPatch, action: Any) -> None:
    """Run `action` at the first `prompt_store stored` log: after `_guard` is released and before
    the observer is called, the only window where a late read of the slot would differ."""
    real = prompts._log
    fired: list[bool] = []

    def hook(event: str, outcome: str, **ids: str) -> None:
        real(event, outcome, **ids)
        if (event, outcome) == ("prompt_store", "stored") and not fired:
            fired.append(True)
            action()

    monkeypatch.setattr(prompts, "_log", hook)


def test_the_captured_reference_is_called_even_if_it_is_replaced_before_the_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, first = _observed()
    second = _Recorder()
    _after_stored(monkeypatch, lambda: store.set_insertion_observer(second))
    store.put(_approval())
    assert len(first.events) == 1 and second.events == []
    store.put(_approval(request_id=REQ + "b"))
    assert len(first.events) == 1 and len(second.events) == 1


def test_the_captured_reference_is_called_even_if_cleared_from_another_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, recorder = _observed()

    def clear_elsewhere() -> None:
        worker = threading.Thread(target=lambda: store.set_insertion_observer(None))
        worker.start()
        worker.join()

    _after_stored(monkeypatch, clear_elsewhere)
    store.put(_approval())
    assert store._observer is None and len(recorder.events) == 1


def test_a_row_inserted_just_before_close_is_still_delivered_then_nothing_more(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, recorder = _observed()
    _after_stored(monkeypatch, lambda: store.close(10))
    store.put(_approval())
    assert len(recorder.events) == 1 and store.closed and store._observer is None
    store.put(_approval(request_id=REQ + "b"))
    assert len(recorder.events) == 1


def test_a_registration_made_before_the_insert_decision_is_seen_by_that_insert() -> None:
    store = PromptStore(clock=lambda: 1)
    late = _Recorder()
    store.set_insertion_observer(late)
    store.put(_approval())
    assert len(late.events) == 1


def test_registration_after_a_refused_insert_does_not_replay_it() -> None:
    store = PromptStore(clock=lambda: 1)
    row = _approval()
    store.put(row)
    late = _Recorder()
    store.set_insertion_observer(late)
    store.put(_approval())  # duplicate: refused
    assert late.events == []


# --- threads --------------------------------------------------------------------------------


def test_put_from_a_worker_thread_calls_the_observer_on_that_thread_without_a_loop() -> None:
    store, recorder = _observed()
    outcome: dict[str, Any] = {}

    def work() -> None:
        outcome["thread"] = threading.get_ident()
        try:
            asyncio.get_running_loop()
            outcome["loop"] = True
        except RuntimeError:
            outcome["loop"] = False
        store.put(_approval())

    worker = threading.Thread(target=work)
    worker.start()
    worker.join()
    assert outcome["loop"] is False
    assert recorder.threads == [outcome["thread"]] != [threading.get_ident()]
    assert threading.active_count() == 1


def test_registration_from_a_worker_thread_is_seen_by_the_next_put() -> None:
    store = PromptStore(clock=lambda: 1)
    recorder = _Recorder()
    worker = threading.Thread(target=lambda: store.set_insertion_observer(recorder))
    worker.start()
    worker.join()
    store.put(_approval())
    assert len(recorder.events) == 1


def test_concurrent_puts_notify_exactly_once_per_row_on_each_caller_thread() -> None:
    store = PromptStore(clock=lambda: 1)
    count = 8
    lock = threading.Lock()
    seen: list[tuple[str, int]] = []

    def observer(event: ApprovalInserted) -> None:
        with lock:
            seen.append((event.key[3], threading.get_ident()))

    store.set_insertion_observer(observer)
    barrier = threading.Barrier(count)
    callers: dict[str, int] = {}

    def work(index: int) -> None:
        request_id = f"{REQ}-{index}"
        callers[request_id] = threading.get_ident()
        barrier.wait()
        store.put(_approval(request_id=request_id))
        store.put(_approval(request_id=request_id))  # a duplicate adds nothing

    threads = [threading.Thread(target=work, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(seen) == sorted(callers.items())


def test_concurrent_duplicate_keys_notify_exactly_once() -> None:
    store, recorder = _observed()
    count = 8
    barrier = threading.Barrier(count)

    def work() -> None:
        barrier.wait()
        store.put(_approval())

    threads = [threading.Thread(target=work) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(recorder.events) == 1


# --- containment ----------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CONTAINED))
def test_a_contained_failure_leaves_the_row_stored_and_logs_one_fixed_line(
    name: str, caplog: pytest.LogCaptureFixture
) -> None:
    store = PromptStore(clock=lambda: 1)
    calls: list[int] = []

    def observer(_event: ApprovalInserted) -> None:
        calls.append(1)
        raise CONTAINED[name]()

    store.set_insertion_observer(observer)
    row = _approval()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        assert store.put(row) is None
    assert store.get(_key(row)) is row and row.status == "open"
    assert calls == [1]
    assert _observer_logs(caplog) == [OBSERVER_LOG]
    assert REQ not in caplog.text and "boom" not in caplog.text


@pytest.mark.parametrize("name", sorted(CONTAINED))
@pytest.mark.asyncio
async def test_a_raising_observer_does_not_stop_the_real_sse_consumer(
    name: str, caplog: pytest.LogCaptureFixture
) -> None:
    store = PromptStore(clock=lambda: 1)

    def observer(_event: ApprovalInserted) -> None:
        raise CONTAINED[name]()

    store.set_insertion_observer(observer)
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        result = await ds.consume_sse(_chunks(*_bot_frames()), bind=_bind(store))
    # The stream ran to its terminal event and produced its normal result.
    assert result.status == 200 and result.body is not None
    assert result.body["message"] == {"role": "assistant", "content": "ok"}
    row = store.get((IID, USER, PROFILE, REQ))
    assert row is not None and row.settle_cause == "run_ended"  # stored, then settled by run end
    assert _observer_logs(caplog) == [OBSERVER_LOG]


@pytest.mark.parametrize("name", sorted(CONTAINED))
@pytest.mark.asyncio
async def test_a_raising_observer_does_not_change_the_apply_frame_state(name: str) -> None:
    store = PromptStore(clock=lambda: 1)

    def observer(_event: ApprovalInserted) -> None:
        raise CONTAINED[name]()

    store.set_insertion_observer(observer)
    state = ds._StreamState()
    bind = _bind(store)
    ds._apply_sse_frame(state, "run.started", {"run_id": RUN}, comment=False, bind=bind)
    ds._apply_sse_frame(
        state,
        "approval.request",
        {"run_id": RUN, "request_id": REQ, "command": "x", "choices": ["once", "deny"]},
        comment=False,
        bind=bind,
    )
    assert state.saw_approval and state.phase == "local"
    ds._apply_sse_frame(state, "done", {}, comment=False, bind=bind)
    assert state.terminal


@pytest.mark.parametrize("name", sorted(CONTAINED))
@pytest.mark.asyncio
async def test_a_raising_observer_leaves_on_exec_approval_returning_true(
    name: str, caplog: pytest.LogCaptureFixture
) -> None:
    store = PromptStore(clock=lambda: 1)

    def observer(_event: ApprovalInserted) -> None:
        raise CONTAINED[name]()

    store.set_insertion_observer(observer)
    hooks = _hooks(store, [{"command": "echo hi", "request_id": REQ}])
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        assert await hooks.on_exec_approval(_Prompt()) is True
    row = store.get((IID, USER, PROFILE, REQ))
    assert row is not None and row.surface == "phone_chat" and row.status == "open"
    assert _observer_logs(caplog) == [OBSERVER_LOG]


@pytest.mark.asyncio
async def test_a_recovery_hook_still_stores_every_row_when_the_observer_raises() -> None:
    store = PromptStore(clock=lambda: 1)

    def observer(_event: ApprovalInserted) -> None:
        raise RuntimeError("boom")

    store.set_insertion_observer(observer)
    hooks = _hooks(store, [
        {"command": "echo hi", "request_id": REQ},
        {"command": "echo hi", "request_id": REQ + "b"},
    ])
    assert await hooks.on_exec_approval(_Prompt()) is True
    assert len(store._rows) == 2


@pytest.mark.parametrize("name", sorted(PROPAGATED))
def test_every_other_base_exception_propagates_from_put_with_the_row_stored(
    name: str, caplog: pytest.LogCaptureFixture
) -> None:
    store = PromptStore(clock=lambda: 1)
    raised: list[BaseException] = []

    def observer(_event: ApprovalInserted) -> None:
        exc = PROPAGATED[name]()
        raised.append(exc)
        raise exc

    store.set_insertion_observer(observer)
    row = _approval()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME), pytest.raises(BaseException) as info:
        store.put(row)
    assert info.value is raised[0]
    assert store.get(_key(row)) is row
    assert _observer_logs(caplog) == []
    assert store._guard.acquire(blocking=False)  # the guard was not left held
    store._guard.release()


@pytest.mark.parametrize("name", sorted(PROPAGATED))
@pytest.mark.asyncio
async def test_every_other_base_exception_propagates_through_the_real_producers(
    name: str, caplog: pytest.LogCaptureFixture
) -> None:
    def observer(_event: ApprovalInserted) -> None:
        raise PROPAGATED[name]()

    bot = PromptStore(clock=lambda: 1)
    bot.set_insertion_observer(observer)
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        with pytest.raises(BaseException) as sse:
            await ds.consume_sse(_chunks(*_bot_frames()), bind=_bind(bot))
        assert not isinstance(sse.value, aiohttp.ClientPayloadError)
        assert bot.get((IID, USER, PROFILE, REQ)) is not None

        phone = PromptStore(clock=lambda: 1)
        phone.set_insertion_observer(observer)
        hooks = _hooks(phone, [{"command": "echo hi", "request_id": REQ}])
        with pytest.raises(BaseException) as hook:
            await hooks.on_exec_approval(_Prompt())
        assert phone.get((IID, USER, PROFILE, REQ)) is not None
    assert type(sse.value) is type(hook.value)
    assert _observer_logs(caplog) == []


# --- scope ----------------------------------------------------------------------------------


def test_no_production_module_registers_an_observer() -> None:
    root = Path(prompts.__file__).parent
    hits = []
    for path in sorted(root.rglob("*.py")):
        for line in path.read_text().splitlines():
            if "set_insertion_observer" in line or "._observer" in line:
                hits.append((path.name, line.strip()))
    assert {name for name, _line in hits} == {"prompts.py"}
    assert [line for _name, line in hits if "set_insertion_observer(" in line
            and not line.startswith("def ")] == []
