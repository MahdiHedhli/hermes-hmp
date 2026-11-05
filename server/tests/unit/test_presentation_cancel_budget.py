"""Cancellation arithmetic is not native clock qualification or terminal proof."""

import dataclasses
import struct

import pytest

from hmp_plugin.presentation_cancel_budget import (
    CLEANUP_NS,
    MAX_NS,
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
