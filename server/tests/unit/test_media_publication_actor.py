"""Actual listener/worker rendezvous; no operator-process or native writer proof."""

import asyncio
import threading
import time

import pytest

from hmp_plugin import media_publication_actor as a
from hmp_plugin.media_publication import PublicationUnavailableError
from hmp_plugin.store import Store

SCOPE = ("a" * 52, "device", "default", 1)


def test_real_store_worker_invalidates_before_sql_without_blocking_listener(tmp_path):
    async def scenario():
        actor = a.MediaPublicationActor()
        store = Store(tmp_path / "store.sqlite3", mutation_observer=actor)
        store.migrate()
        cohort = (object(), object(), object())
        old = actor.candidate(SCOPE, cohort)
        entered = threading.Event()
        release = threading.Event()

        def write():
            with store.transaction():
                entered.set()
                assert release.wait(2)
                store.insert_user("synthetic", "owner", 1)

        work = asyncio.create_task(asyncio.to_thread(write))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert not actor.claim_once(old, SCOPE, cohort)
            with pytest.raises(PublicationUnavailableError):
                actor.candidate(SCOPE, cohort)
            await asyncio.wait_for(asyncio.sleep(0.01), 0.2)  # loop remains responsive
        finally:
            release.set()
        await work
        assert store._conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert actor.claim_once(actor.candidate(SCOPE, cohort), SCOPE, cohort)
        actor.close()
        store.close()

    asyncio.run(scenario())


def test_loop_thread_observer_refuses_before_begin_and_changes_nothing():
    async def scenario():
        actor = a.MediaPublicationActor()
        cohort = (object(), object(), object())
        ticket = actor.candidate(SCOPE, cohort)
        with pytest.raises(PublicationUnavailableError):
            actor.begin()
        assert actor.claim_once(ticket, SCOPE, cohort)
        actor.close()

    asyncio.run(scenario())


def test_late_begin_ack_starts_no_write_and_poisoned_callback_retires(monkeypatch):
    monkeypatch.setattr(a, "_ACK_WAIT_S", 0.03)

    async def scenario():
        actor = a.MediaPublicationActor()
        started = threading.Event()
        writes = []

        def write():
            started.set()
            actor.begin()
            writes.append("must not run without receipt")

        failures = []

        def run_worker():
            try:
                write()
            except PublicationUnavailableError:
                failures.append(True)

        worker = threading.Thread(target=run_worker)
        worker.start()
        # Keep the loop from processing begin until after its acknowledgement
        # deadline. Awaiting the started event could let begin run first.
        assert started.wait(2)
        time.sleep(0.08)  # noqa: ASYNC251 - deliberately prevent fixture loop delivery
        await asyncio.to_thread(worker.join, 2)
        assert not worker.is_alive() and failures == [True]
        await asyncio.sleep(0)
        assert writes == []
        with pytest.raises(PublicationUnavailableError):
            actor.candidate(SCOPE, (1, 2, 3))
        assert actor._slots.acquire(blocking=False)  # queued callback really retired
        actor._slots.release()
        actor.close()

    asyncio.run(scenario())


def test_uncertain_settlement_and_shutdown_cannot_publish():
    async def scenario():
        actor = a.MediaPublicationActor()
        receipt = await asyncio.to_thread(actor.begin)
        await asyncio.to_thread(actor.settle, receipt, certain=False)
        with pytest.raises(PublicationUnavailableError):
            actor.candidate(SCOPE, (1, 2, 3))
        actor.close()
        with pytest.raises(PublicationUnavailableError):
            await asyncio.to_thread(actor.begin)

    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ("candidate", "claim"))
def test_worker_failure_during_currency_clock_never_returns_currency(monkeypatch, operation):
    from hmp_plugin import media_publication as p

    async def scenario():
        actor = a.MediaPublicationActor()
        cohort = (object(), object(), object())
        ticket = actor.candidate(SCOPE, cohort)
        original = p.time.monotonic_ns

        def clock():
            worker = threading.Thread(target=actor._failed.set)
            worker.start()
            worker.join()
            return original()

        monkeypatch.setattr(p.time, "monotonic_ns", clock)
        with pytest.raises(PublicationUnavailableError):
            if operation == "candidate":
                actor.candidate(SCOPE, cohort)
            else:
                actor.claim_once(ticket, SCOPE, cohort)
        actor.close()

    asyncio.run(scenario())


def test_pre_enqueue_future_allocation_failure_releases_only_unused_slot(monkeypatch):
    async def scenario():
        actor = a.MediaPublicationActor()
        original = a.concurrent.futures.Future

        def broken():
            raise MemoryError("synthetic allocation failure")

        # Construct the thread before patching concurrent.futures, because
        # asyncio.to_thread itself uses that module's Future factory.
        errors = []

        def worker():
            try:
                actor.begin()
            except PublicationUnavailableError:
                errors.append(True)

        thread = threading.Thread(target=worker)
        monkeypatch.setattr(a.concurrent.futures, "Future", broken)
        thread.start()
        thread.join(2)
        monkeypatch.setattr(a.concurrent.futures, "Future", original)
        assert not thread.is_alive() and errors == [True]
        await asyncio.sleep(0)
        acquired = [actor._slots.acquire(blocking=False) for _ in range(33)]
        assert acquired == [True] * 32 + [False]
        for _ in range(32):
            actor._slots.release()
        with pytest.raises(PublicationUnavailableError):
            actor.candidate(SCOPE, (1, 2, 3))
        actor.close()

    asyncio.run(scenario())


def test_close_retains_store_until_actual_worker_settlement(tmp_path):
    async def scenario():
        actor = a.MediaPublicationActor()
        store = Store(tmp_path / "store.sqlite3", mutation_observer=actor)
        store.migrate()
        entered = threading.Event()
        release = threading.Event()

        def write():
            with store.transaction():
                entered.set()
                assert release.wait(2)
                store.insert_user("synthetic", "owner", 1)

        work = asyncio.create_task(asyncio.to_thread(write))
        assert await asyncio.to_thread(entered.wait, 2)
        assert actor.outstanding_mutations() == 1
        actor.close()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(actor.wait_drained(), 0.02)
        assert actor.outstanding_mutations() == 1
        release.set()
        with pytest.raises(RuntimeError, match="settlement outcome unavailable"):
            await work
        await asyncio.wait_for(actor.wait_drained(), 0.2)
        assert actor.outstanding_mutations() == 0
        assert store._conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        with pytest.raises(PublicationUnavailableError):
            actor.candidate(SCOPE, (1, 2, 3))
        store.close()  # actual worker ended, not merely a shutdown observation timeout

    asyncio.run(scenario())


def test_unsettled_original_receipt_is_not_erased_by_close_or_drain_timeout():
    async def scenario():
        actor = a.MediaPublicationActor()
        receipt = await asyncio.to_thread(actor.begin)
        actor.close()
        assert actor.outstanding_mutations() == 1
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(actor.wait_drained(), 0.01)
        assert actor.outstanding_mutations() == 1
        # Only the actual receipt-holder can retire this debt. No replay of a write.
        with pytest.raises(PublicationUnavailableError):
            await asyncio.to_thread(actor.settle, receipt, certain=True)
        await asyncio.wait_for(actor.wait_drained(), 0.2)
        assert actor.outstanding_mutations() == 0

    asyncio.run(scenario())


def test_begin_return_loss_retains_preallocated_unknown_debt(monkeypatch):
    async def scenario():
        actor = a.MediaPublicationActor()
        original = actor._publisher.begin_mutation

        def lose_return():
            original()
            raise KeyboardInterrupt("synthetic publisher begin return loss")

        monkeypatch.setattr(actor._publisher, "begin_mutation", lose_return)
        with pytest.raises(PublicationUnavailableError):
            await asyncio.to_thread(actor.begin)
        actor.close()
        assert actor.outstanding_mutations() == 1
        assert list(actor._mutations.values()) == [None]
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(actor.wait_drained(), 0.01)
        assert actor.outstanding_mutations() == 1  # never infer a current receipt or force drain

    asyncio.run(scenario())


def test_cleanup_capacity_is_independent_of_saturated_new_begin_admission():
    async def scenario():
        actor = a.MediaPublicationActor()
        receipt = await asyncio.to_thread(actor.begin)
        held = [actor._slots.acquire(blocking=False) for _ in range(32)]
        assert all(held)
        actor.close()
        try:
            with pytest.raises(PublicationUnavailableError):
                await asyncio.to_thread(actor.settle, receipt, certain=True)
            await asyncio.wait_for(actor.wait_drained(), 0.2)
            assert actor.outstanding_mutations() == 0
            assert not actor._slots.acquire(blocking=False)
        finally:
            for _ in held:
                actor._slots.release()

    asyncio.run(scenario())
