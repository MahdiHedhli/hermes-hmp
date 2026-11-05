"""Cancellation arithmetic is not native clock qualification or terminal proof."""

import dataclasses
import struct
import threading
import time

import pytest

from hmp_plugin.presentation_cancel_budget import (
    CLEANUP_NS,
    MAX_NS,
    BudgetBusyError,
    CancellationBudget,
    CancellationWindow,
)
from hmp_plugin.presentation_jobs import FrameError


def test_exact_wire_window_and_immutable_values():
    window = CancellationWindow(100, 100 + CLEANUP_NS)
    assert window.encode() == struct.pack(">QQ", 100, 100 + CLEANUP_NS)
    assert CancellationWindow.decode(window.encode()) == window
    with pytest.raises(dataclasses.FrozenInstanceError):
        window.end_ns = 1000


@pytest.mark.parametrize("start,end", [
    (True, CLEANUP_NS + 1), (0.0, CLEANUP_NS), (-1, CLEANUP_NS - 1),
    (0, CLEANUP_NS + 1), (MAX_NS, MAX_NS + CLEANUP_NS),
    (0, False), (0, float(CLEANUP_NS)),
])
def test_bad_window_never_encodes(start, end):
    with pytest.raises(FrameError):
        CancellationWindow(start, end)


@pytest.mark.parametrize("body", [b"", b"x" * 15, b"x" * 17, bytearray(16), None,
                                  struct.pack(">QQ", 1 << 63, (1 << 63) + CLEANUP_NS)])
def test_bad_wire_values_refuse(body):
    with pytest.raises(FrameError):
        CancellationWindow.decode(body)


@pytest.mark.parametrize("work_end", [0, -1, True, 1.0, MAX_NS, MAX_NS - CLEANUP_NS + 1])
def test_work_deadline_cannot_overflow(work_end):
    with pytest.raises(FrameError):
        CancellationBudget(work_end)


def test_eof_then_cancel_then_late_local_cause_never_renews():
    owner = CancellationBudget(1_000_000_000)
    first = owner.local(10)
    owner.inherit(CancellationWindow(20, 20 + CLEANUP_NS), 30)
    assert owner.local(40) == first
    assert owner.remaining_ns(50) == first.end_ns - 50


def test_earlier_remote_shortens_existing_local_and_every_later_duplicate():
    owner = CancellationBudget(1_000_000_000)
    owner.local(100)
    earlier = CancellationWindow(50, 50 + CLEANUP_NS)
    owner.inherit(earlier, 110)
    owner.inherit(CancellationWindow(80, 80 + CLEANUP_NS), 120)
    assert owner.local(130) == earlier
    assert owner.remaining_ns(140) == earlier.end_ns - 140


def test_already_expired_inherited_budget_has_no_new_allowance():
    owner = CancellationBudget(1_000_000_000)
    owner.inherit(CancellationWindow(10, 10 + CLEANUP_NS), CLEANUP_NS + 20)
    assert owner.remaining_ns(CLEANUP_NS + 30) == 0
    assert owner.local(CLEANUP_NS + 40) == CancellationWindow(10, 10 + CLEANUP_NS)


def test_local_timeout_after_original_end_is_capped():
    owner = CancellationBudget(100)
    assert owner.local(1000) == CancellationWindow(100, 100 + CLEANUP_NS)
    assert owner.remaining_ns(100 + CLEANUP_NS) == 0


@pytest.mark.parametrize("window,now", [
    (CancellationWindow(101, 101 + CLEANUP_NS), 100),
    (CancellationWindow(1001, 1001 + CLEANUP_NS), 2000),
    (None, 100),
])
def test_future_or_outside_work_window_poison_without_reset(window, now):
    owner = CancellationBudget(1000)
    owner.local(50)
    with pytest.raises(FrameError):
        owner.inherit(window, now)
    with pytest.raises(FrameError):
        owner.local(3000)
    assert owner._end_ns == 50 + CLEANUP_NS


def test_backward_clock_and_missing_cause_are_sticky():
    owner = CancellationBudget(1000)
    owner.local(100)
    with pytest.raises(FrameError):
        owner.remaining_ns(99)
    with pytest.raises(FrameError):
        owner.remaining_ns(101)
    empty = CancellationBudget(1000)
    with pytest.raises(FrameError):
        empty.remaining_ns(100)
    with pytest.raises(FrameError):
        empty.local(101)


def test_policy_thread_reads_consistent_generations_during_owner_mutation():
    owner = CancellationBudget(10_000)
    ready = threading.Event()
    done = threading.Event()
    failures = []
    observed = [0]
    def reader():
        ready.set()
        last = -1
        try:
            while not done.is_set():
                try:
                    end, now, cleanup, failed = CancellationBudget.inspect(owner)
                except BudgetBusyError:
                    continue
                assert end == 10_000 and not failed
                if now is not None:
                    assert now >= last and cleanup == CLEANUP_NS
                    last = now
                observed[0] += 1
        except BaseException as error:
            failures.append(error)
    thread = threading.Thread(target=reader)
    thread.start()
    try:
        assert ready.wait(1)
        for now in range(1000):
            assert owner.local(now).end_ns == CLEANUP_NS
            if now % 50 == 0:
                time.sleep(0)
    finally:
        done.set()
        thread.join(1)
    assert not thread.is_alive() and observed[0] > 0 and failures == []
    assert owner.inspect() == (10_000, 999, CLEANUP_NS, False)


def test_foreign_thread_cannot_mutate_and_poison_is_not_reversible():
    owner = CancellationBudget(1000)
    errors = []
    def foreign_writer():
        try:
            owner.local(10)
        except FrameError as error:
            errors.append(error)
    thread = threading.Thread(target=foreign_writer)
    thread.start()
    thread.join(1)
    assert not thread.is_alive() and len(errors) == 1
    assert owner.inspect() == (1000, None, None, True)
    with pytest.raises(FrameError):
        owner.local(11)


def test_foreign_snapshot_refuses_before_callbacks_and_restoration_cannot_revive():
    owner = CancellationBudget(1000)
    callbacks = []
    class Foreign:
        def __len__(self):
            callbacks.append("len")
            return 3
        def __iter__(self):
            callbacks.append("iter")
            return iter(())
        def __eq__(self, other):
            callbacks.append("eq")
            return True
    original = owner._state
    owner._state = Foreign()
    with pytest.raises(FrameError):
        owner.inspect()
    owner._state = original
    assert owner.inspect()[-1] is True and callbacks == []
    with pytest.raises(FrameError):
        owner.local(10)


@pytest.mark.parametrize("replacement", ["tuple", "clone", "rollback"])
def test_well_shaped_replacement_cannot_erase_or_extend_first_cause(replacement):
    owner = CancellationBudget(1000)
    old = owner._state
    owner.local(10)
    current = owner._state
    if replacement == "tuple":
        owner._state = (None, None)
    elif replacement == "clone":
        owner._state = current._replace(last=None, end=None)
    else:
        owner._state = owner._state_snapshot = old
    with pytest.raises(FrameError):
        owner.inspect()
    owner._state = owner._state_snapshot = current
    assert owner.inspect() == (1000, 10, CLEANUP_NS + 10, True)
    with pytest.raises(FrameError):
        owner.local(20)


@pytest.mark.parametrize("field,value", [("end", CLEANUP_NS + 100), ("last", None)])
def test_minted_payload_cannot_be_mutated_in_place(field, value):
    owner = CancellationBudget(1000)
    owner.local(10)
    state = owner._state
    with pytest.raises(AttributeError):
        object.__setattr__(state, field, value)
    assert owner.inspect() == (1000, 10, CLEANUP_NS + 10, False)
