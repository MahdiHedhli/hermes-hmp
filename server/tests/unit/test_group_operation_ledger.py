"""Portable model causality only; no native actor, transport or permission proof."""

from dataclasses import FrozenInstanceError
from threading import Thread

import pytest

from hmp_plugin.group_operation_ledger import GroupLedgerRefusalError, GroupOperationLedger


def ledger(**changes):
    limits = {
        "max_queued": 2,
        "max_pending": 1,
        "max_reservations": 2,
        "max_descriptor_bytes": 8,
        "max_retained_bytes": 8,
    }
    limits.update(changes)
    return GroupOperationLedger(**limits)


def active(owner):
    token = owner.enqueue(now=1, deadline=10, descriptor_bytes=2)
    owner.start(token, now=2)
    return token


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.0, "1", None, 1 << 40])
@pytest.mark.parametrize(
    "field",
    ["max_queued", "max_pending", "max_reservations", "max_descriptor_bytes", "max_retained_bytes"],
)
def test_exact_positive_bounded_limits(field, value):
    with pytest.raises(GroupLedgerRefusalError):
        ledger(**{field: value})


@pytest.mark.parametrize(
    "bad", [True, None, "1", -1, float("nan"), float("inf"), -float("inf"), 10**400]
)
def test_invalid_clock_or_deadline_has_no_accounting_effect(bad):
    owner = ledger()
    before = owner.snapshot()
    for values in [{"now": bad, "deadline": 10}, {"now": 1, "deadline": bad}]:
        with pytest.raises(GroupLedgerRefusalError):
            owner.enqueue(**values, descriptor_bytes=2)
        assert owner.snapshot() == before


def test_queue_wait_does_not_renew_deadline_or_refund_slot():
    owner = ledger()
    token = owner.enqueue(now=1, deadline=3, descriptor_bytes=2)
    with pytest.raises(GroupLedgerRefusalError):
        owner.start(token, now=3)
    assert owner.snapshot().queued == 1
    assert not owner.publication_allowed(token, now=4)
    owner.release_operation(token)
    assert owner.snapshot().queued == 0


def test_started_deadline_fences_without_refunding_debt():
    owner = ledger()
    token = active(owner)
    reservation = owner.reserve(token, now=3, size=8)
    assert owner.publication_allowed(token, now=9)
    before = owner.snapshot()
    assert not owner.publication_allowed(token, now=10)
    assert owner.snapshot() == before
    with pytest.raises(GroupLedgerRefusalError):
        owner.release_operation(token)
    owner.release_reservation(reservation)
    owner.release_operation(token)
    assert owner.snapshot().pending == owner.snapshot().retained_bytes == 0


def test_queue_pending_and_descriptor_capacity_are_independent():
    owner = ledger()
    first = active(owner)
    second = owner.enqueue(now=3, deadline=10, descriptor_bytes=3)
    third = owner.enqueue(now=3, deadline=10, descriptor_bytes=3)
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=3, deadline=10, descriptor_bytes=1)
    with pytest.raises(GroupLedgerRefusalError):
        owner.start(second, now=3)
    assert owner.snapshot() == before
    owner.release_operation(third)
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=3, deadline=10, descriptor_bytes=4)
    owner.release_operation(first)
    owner.start(second, now=4)
    assert owner.publication_allowed(second, now=4)


def test_retire_full_queues_is_immediate_and_generations_share_debt():
    owner = ledger()
    first = active(owner)
    reservation = owner.reserve(first, now=3, size=8)
    owner.enqueue(now=3, deadline=10, descriptor_bytes=3)
    owner.enqueue(now=3, deadline=10, descriptor_bytes=3)
    before = owner.snapshot()
    owner.retire()
    assert not owner.publication_allowed(first, now=4)
    owner.advance_generation()
    after = owner.snapshot()
    assert after.generation == before.generation + 1
    assert (after.queued, after.pending, after.retained_bytes) == (2, 1, 8)
    assert not owner.publication_allowed(first, now=4)
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=4, deadline=11, descriptor_bytes=1)
    owner.release_reservation(reservation)
    owner.release_operation(first)
    assert owner.snapshot().queued == 2


def test_reservations_share_byte_and_count_budgets_and_release_once():
    owner = ledger()
    token = active(owner)
    one = owner.reserve(token, now=3, size=4)
    two = owner.reserve(token, now=3, size=4)
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.reserve(token, now=3, size=1)
    assert owner.snapshot() == before
    owner.release_reservation(one)
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.release_reservation(one)
    assert owner.snapshot() == before
    owner.release_reservation(two)
    owner.release_operation(token)
    assert owner.snapshot().reservations == 0


class Hostile:
    def __hash__(self):
        raise AssertionError("foreign hash invoked")

    def __eq__(self, other):
        raise AssertionError("foreign equality invoked")

    def __float__(self):
        raise AssertionError("foreign conversion invoked")

    def __repr__(self):
        raise AssertionError("foreign formatting invoked")


@pytest.mark.parametrize("handle", [object(), Hostile(), None, 1, "x"])
def test_unregistered_exact_handles_refuse_without_foreign_hooks(handle):
    owner = ledger()
    before = owner.snapshot()
    for function in [
        lambda: owner.start(handle, now=1),
        lambda: owner.publication_allowed(handle, now=1),
        lambda: owner.release_operation(handle),
        lambda: owner.release_reservation(handle),
    ]:
        with pytest.raises(GroupLedgerRefusalError):
            function()
        assert owner.snapshot() == before


def test_cross_owner_and_stale_handles_never_reclaim_new_records():
    first, second = ledger(), ledger()
    token = active(first)
    with pytest.raises(GroupLedgerRefusalError):
        second.start(token, now=3)
    first.release_operation(token)
    new = first.enqueue(now=3, deadline=20, descriptor_bytes=2)
    before = first.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        first.release_operation(token)
    assert first.snapshot() == before and new is not token


def test_backwards_sample_and_duplicate_start_leave_counters_unchanged():
    owner = ledger()
    token = active(owner)
    before = owner.snapshot()
    for now in [1, 2]:
        with pytest.raises(GroupLedgerRefusalError):
            owner.start(token, now=now)
    assert owner.snapshot() == before


def test_advance_requires_retirement_and_no_tombstones_accumulate():
    owner = ledger()
    with pytest.raises(GroupLedgerRefusalError):
        owner.advance_generation()
    for step in range(1000):
        token = owner.enqueue(now=step, deadline=step + 1, descriptor_bytes=1)
        owner.release_operation(token)
        owner.retire()
        owner.advance_generation()
    assert owner.snapshot().queued == owner.snapshot().pending == 0
    assert not owner._operations and not owner._reservations


def test_thread_confinement_even_retirement_and_snapshots():
    owner = ledger()
    token = active(owner)
    failures = []

    def other_thread():
        for function in [
            owner.retire,
            owner.advance_generation,
            owner.snapshot,
            lambda: owner.release_operation(token),
        ]:
            try:
                function()
            except GroupLedgerRefusalError:
                failures.append(True)

    worker = Thread(target=other_thread)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive() and len(failures) == 4
    assert owner.publication_allowed(token, now=3)
    with pytest.raises(FrozenInstanceError):
        owner.snapshot().pending = 0


def test_lossy_integer_clock_and_adjacent_deadline_are_rejected():
    owner = ledger()
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=(1 << 53) + 1, deadline=(1 << 53) + 2, descriptor_bytes=1)
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=1 << 53, deadline=(1 << 53) + 1, descriptor_bytes=1)
    assert owner.snapshot() == before


def test_exact_large_integer_clock_still_rejects_backwards_sample():
    owner = ledger()
    token = owner.enqueue(now=(1 << 53) + 2, deadline=(1 << 53) + 4, descriptor_bytes=1)
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.start(token, now=1 << 53)
    assert owner.snapshot() == before


def test_reservation_count_and_bytes_each_refuse_independently():
    count_owner = ledger(max_retained_bytes=100)
    token = active(count_owner)
    count_owner.reserve(token, now=3, size=1)
    count_owner.reserve(token, now=3, size=1)
    before = count_owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        count_owner.reserve(token, now=3, size=1)
    assert count_owner.snapshot() == before
    bytes_owner = ledger(max_reservations=10)
    token = active(bytes_owner)
    bytes_owner.reserve(token, now=3, size=8)
    before = bytes_owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        bytes_owner.reserve(token, now=3, size=1)
    assert bytes_owner.snapshot() == before


def test_queue_limit_independent_of_descriptor_bytes_and_temporal_scope():
    owner = ledger(max_descriptor_bytes=100)
    owner.enqueue(now=1, deadline=10, descriptor_bytes=1)
    token = owner.enqueue(now=1, deadline=10, descriptor_bytes=1)
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=1, deadline=10, descriptor_bytes=1)
    assert owner.snapshot() == before
    with pytest.raises(GroupLedgerRefusalError):
        owner.reserve(token, now=1, size=1)
    assert not owner.publication_allowed(token, now=1)


def test_hostile_number_conversion_never_runs():
    owner = ledger()
    before = owner.snapshot()
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=Hostile(), deadline=10, descriptor_bytes=1)
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=1, deadline=Hostile(), descriptor_bytes=1)
    with pytest.raises(GroupLedgerRefusalError):
        owner.enqueue(now=1, deadline=10, descriptor_bytes=Hostile())
    assert owner.snapshot() == before
