"""Actual listener/worker rendezvous; no operator-process or native writer proof."""
import asyncio
import threading
import time
import pytest
from hmp_plugin import media_publication_actor as a
from hmp_plugin.media_publication import PublicationUnavailable
from hmp_plugin.store import Store

SCOPE = ('a' * 52, 'device', 'default', 1)


def test_real_store_worker_invalidates_before_sql_without_blocking_listener(tmp_path):
    async def scenario():
        actor = a.MediaPublicationActor()
        store = Store(tmp_path / 'store.sqlite3', mutation_observer=actor); store.migrate()
        cohort = (object(), object(), object()); old = actor.candidate(SCOPE, cohort)
        entered = threading.Event(); release = threading.Event()
        def write():
            with store.transaction():
                entered.set()
                assert release.wait(2)
                store.insert_user('synthetic', 'owner', 1)
        work = asyncio.create_task(asyncio.to_thread(write))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert not actor.claim_once(old, SCOPE, cohort)
            with pytest.raises(PublicationUnavailable): actor.candidate(SCOPE, cohort)
            await asyncio.wait_for(asyncio.sleep(.01), .2)  # loop remains responsive
        finally:
            release.set()
        await work
        assert store._conn.execute('SELECT count(*) FROM users').fetchone()[0] == 1
        assert actor.claim_once(actor.candidate(SCOPE, cohort), SCOPE, cohort)
        actor.close(); store.close()
    asyncio.run(scenario())


def test_loop_thread_observer_refuses_before_begin_and_changes_nothing():
    async def scenario():
        actor = a.MediaPublicationActor(); cohort = (object(), object(), object())
        ticket = actor.candidate(SCOPE, cohort)
        with pytest.raises(PublicationUnavailable): actor.begin()
        assert actor.claim_once(ticket, SCOPE, cohort)
        actor.close()
    asyncio.run(scenario())


def test_late_begin_ack_starts_no_write_and_poisoned_callback_retires(monkeypatch):
    monkeypatch.setattr(a, '_ACK_WAIT_S', .03)
    async def scenario():
        actor = a.MediaPublicationActor(); started = threading.Event(); writes = []
        def write():
            started.set()
            actor.begin()
            writes.append('must not run without receipt')
        failures = []
        def run_worker():
            try: write()
            except PublicationUnavailable: failures.append(True)
        worker = threading.Thread(target=run_worker)
        worker.start()
        # Keep the loop from processing begin until after its acknowledgement
        # deadline. Awaiting the started event could let begin run first.
        assert started.wait(2)
        time.sleep(.08)
        await asyncio.to_thread(worker.join, 2)
        assert not worker.is_alive() and failures == [True]
        await asyncio.sleep(0)
        assert writes == []
        with pytest.raises(PublicationUnavailable): actor.candidate(SCOPE, (1, 2, 3))
        assert actor._slots.acquire(blocking=False)  # queued callback really retired
        actor._slots.release()
        actor.close()
    asyncio.run(scenario())


def test_uncertain_settlement_and_shutdown_cannot_publish():
    async def scenario():
        actor = a.MediaPublicationActor()
        receipt = await asyncio.to_thread(actor.begin)
        await asyncio.to_thread(actor.settle, receipt, certain=False)
        with pytest.raises(PublicationUnavailable): actor.candidate(SCOPE, (1, 2, 3))
        actor.close()
        with pytest.raises(PublicationUnavailable): await asyncio.to_thread(actor.begin)
    asyncio.run(scenario())
