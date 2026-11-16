"""Finite synthetic witness ownership; no admission, native launch or live home."""

import asyncio
from types import SimpleNamespace

import pytest

from .test_presentation_supervisor import _wait_for_native_entry


@pytest.fixture
def witnesses(monkeypatch):
    original = asyncio.create_task
    owned = []

    def observe(coro, **kwargs):
        task = original(coro, **kwargs)
        if kwargs.get("name") == "presentation-native-witness":
            owned.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", observe)
    yield owned
    assert len(owned) == 1 and owned[0].done()


@pytest.mark.asyncio
@pytest.mark.parametrize("entered", (False, True))
async def test_finished_supervisor_never_satisfies_blocked_stage(entered, witnesses):
    native = SimpleNamespace(entered=asyncio.Event())
    if entered:
        native.entered.set()
    running = asyncio.get_running_loop().create_future()
    running.set_result(False)
    with pytest.raises(pytest.fail.Exception, match="required blocked native stage"):
        # The already terminal owner must be noticed; no native deadline is changed.
        await asyncio.wait_for(_wait_for_native_entry(native, running), timeout=0.25)
    assert running.done() and running.result() is False


@pytest.mark.asyncio
async def test_original_supervisor_error_is_observed_without_substitution(witnesses):
    native = SimpleNamespace(entered=asyncio.Event())
    running = asyncio.get_running_loop().create_future()
    error = RuntimeError("synthetic original supervisor failure")
    running.set_exception(error)
    with pytest.raises(RuntimeError) as caught:
        await asyncio.wait_for(_wait_for_native_entry(native, running), timeout=0.25)
    assert caught.value is error and running.exception() is error


@pytest.mark.asyncio
async def test_original_supervisor_cancellation_stays_cancellation(witnesses):
    native = SimpleNamespace(entered=asyncio.Event())
    running = asyncio.get_running_loop().create_future()
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await _wait_for_native_entry(native, running)
    assert running.cancelled()


@pytest.mark.asyncio
async def test_entered_witness_does_not_complete_or_cancel_supervisor(witnesses):
    native = SimpleNamespace(entered=asyncio.Event())
    native.entered.set()
    running = asyncio.get_running_loop().create_future()
    try:
        assert await _wait_for_native_entry(native, running) is None
        assert not running.done() and not running.cancelled()
    finally:
        running.cancel()  # This test, rather than the witness waiter, owns it.


@pytest.mark.asyncio
async def test_cancelled_waiter_settles_only_its_own_witness(witnesses):
    native = SimpleNamespace(entered=asyncio.Event())
    running = asyncio.get_running_loop().create_future()
    waiting = asyncio.create_task(_wait_for_native_entry(native, running))
    try:
        await asyncio.sleep(0)  # Let the helper construct its owned witness.
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        assert not running.done() and not running.cancelled()
        assert not native.entered.is_set()
    finally:
        running.cancel()
