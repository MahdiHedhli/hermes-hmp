"""Buffer accounting only; no source authority or native read qualification."""

import copy
import pickle
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from threading import Barrier

import pytest

from hmp_plugin.presentation_memory import (
    MAX_LIVE_BUFFERS,
    OPERATION_PAYLOAD_LIMIT,
    PresentationMemoryBudget,
    PresentationMemoryError,
    _BufferLease,
)


def test_simultaneous_conversion_result_and_stream_copies_are_charged():
    budget = PresentationMemoryBudget()
    sizes = (2_000_000, 2_000_000, 2_000_000, 65_536 * 4, 4096, 65_536, 65_536)
    kinds = ("file", "file", "conversion", "yaml", "result", "stream", "stream")
    leases = [budget.reserve(kind, size) for kind, size in zip(kinds, sizes, strict=True)]
    assert budget.snapshot() == (sum(sizes), len(sizes), sum(sizes))
    for lease in reversed(leases):
        budget.release(lease)
    assert budget.snapshot() == (0, 0, sum(sizes))


@pytest.mark.parametrize("size", [True, False, 0, -1, 1.0, None, OPERATION_PAYLOAD_LIMIT + 1])
def test_invalid_size_cannot_change_accounting(size):
    budget = PresentationMemoryBudget()
    with pytest.raises(PresentationMemoryError):
        budget.reserve("file", size)
    assert budget.snapshot() == (0, 0, 0)


def test_full_envelope_refuses_another_copy_without_losing_original_charge():
    budget = PresentationMemoryBudget()
    lease = budget.reserve("file", OPERATION_PAYLOAD_LIMIT)
    with pytest.raises(PresentationMemoryError):
        budget.reserve("conversion", 1)
    assert budget.snapshot() == (OPERATION_PAYLOAD_LIMIT, 1, OPERATION_PAYLOAD_LIMIT)
    budget.release(lease)
    with pytest.raises(PresentationMemoryError):
        budget.release(lease)
    assert budget.snapshot() == (0, 0, OPERATION_PAYLOAD_LIMIT)


def test_wrong_budget_and_forged_equal_ticket_do_not_release_original():
    budget, other = PresentationMemoryBudget(), PresentationMemoryBudget()
    lease = budget.reserve("result", 4096)
    forged = _BufferLease(budget, 4096, "result")
    for target, ticket in ((other, lease), (budget, forged)):
        with pytest.raises(PresentationMemoryError):
            target.release(ticket)
    assert budget.snapshot() == (4096, 1, 4096)
    assert other.snapshot() == (0, 0, 0)
    budget.release(lease)


def test_changed_ticket_cannot_underflow_or_reassign_charge():
    budget = PresentationMemoryBudget()
    lease = budget.reserve("file", 2048)
    lease._size = 1
    with pytest.raises(PresentationMemoryError):
        budget.release(lease)
    assert budget.snapshot() == (2048, 1, 2048)
    lease._size = 2048
    budget.release(lease)


def test_many_tiny_allocations_are_bounded_independently_of_byte_cap():
    budget = PresentationMemoryBudget()
    leases = [budget.reserve("raster", 1) for _ in range(MAX_LIVE_BUFFERS)]
    with pytest.raises(PresentationMemoryError):
        budget.reserve("raster", 1)
    assert budget.snapshot() == (MAX_LIVE_BUFFERS, MAX_LIVE_BUFFERS, MAX_LIVE_BUFFERS)
    for lease in leases:
        budget.release(lease)


@pytest.mark.parametrize("action", [copy.copy, copy.deepcopy, pickle.dumps])
def test_ticket_cannot_be_duplicated_or_serialized(action):
    budget = PresentationMemoryBudget()
    lease = budget.reserve("stream", 65536)
    with pytest.raises(TypeError):
        action(lease)
    assert budget.snapshot() == (65536, 1, 65536)
    budget.release(lease)


def test_foreign_kind_and_ticket_invoke_no_hooks():
    hooks = []

    class Kind(str):
        def __hash__(self):
            hooks.append("hash")
            raise AssertionError("foreign kind hashed")

    class Ticket:
        def __getattribute__(self, name):
            hooks.append("attribute")
            raise AssertionError("foreign ticket inspected")

    budget = PresentationMemoryBudget()
    for kind in (Kind("file"), "private/path", "authorization"):
        with pytest.raises(PresentationMemoryError):
            budget.reserve(kind, 1)
    with pytest.raises(PresentationMemoryError):
        budget.release(Ticket())
    assert hooks == [] and budget.snapshot() == (0, 0, 0)


def test_concurrent_workers_cannot_overbook_then_release():
    budget = PresentationMemoryBudget()
    workers, size = 8, OPERATION_PAYLOAD_LIMIT // 4
    ready, settled = Barrier(workers), Barrier(workers)

    def work():
        lease = None
        ready.wait(timeout=5)
        with suppress(PresentationMemoryError):
            lease = budget.reserve("file", size)
        settled.wait(timeout=5)
        if lease is not None:
            budget.release(lease)
        return lease is not None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: work(), range(workers)))
    assert results.count(True) == 4
    assert budget.snapshot() == (0, 0, OPERATION_PAYLOAD_LIMIT)
