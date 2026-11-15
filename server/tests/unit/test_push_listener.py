"""PN-BND real listener/store lifetime, using only isolated homes and loopback TLS.

No provider, relay, phone or native Hermes admission is exercised.
"""

from __future__ import annotations

import asyncio
import logging
import threading

import pytest

from hmp_plugin import identity, server

from .hmp_kit import Env
from .test_push_cleanup_causes import install_full_injector
from .test_push_config import block
from .test_push_store import generation, row, seed_device, seed_row


def seeded(tmp_path):
    env = Env(tmp_path)
    env.store.insert_user("user", "synthetic", 1)
    seed_device(env.store, "device-synthetic")
    return env


def registration(env, **changes):
    return seed_row(
        env.store, "device-synthetic", iid=env.iid,
        host_generation=env.store.revocation_epoch(), key=env.identity.k_grace(),
        expires=env.clock.now + 3600, **changes,
    )


def listener(env):
    return server.HmpServer(
        env.ctx, server.ListenerSettings("127.0.0.1", 0), watchdog_interval=3600
    )


def test_listener_open_purges_once_reads_key_off_loop_without_repair(tmp_path, monkeypatch):
    env = seeded(tmp_path)
    digest = registration(env, kid="removed")
    config = block(relay_kids=["current"])
    env.ctx.push_settings = lambda: config
    env.ctx.direct_send_flag = lambda: True
    env.ctx.approvals_available = lambda: True
    real_read = identity._read_k_grace_for_push
    threads = []
    monkeypatch.setattr(
        identity, "_read_k_grace_for_push",
        lambda path: (threads.append(threading.get_ident()), real_read(path))[1],
    )
    monkeypatch.setattr(
        env.identity, "k_grace", lambda: pytest.fail("listener invoked repairing key accessor")
    )
    key_path = env.custody.k_grace_path
    before = (key_path.read_bytes(), key_path.stat().st_mode)

    async def scenario():
        event_thread = threading.get_ident()
        srv = listener(env)
        await srv.start()
        try:
            assert row(env.store, digest)["state"] == "expired"
            assert generation(env.store, "device-synthetic") == 2
            assert threads and len(threads) == 1 and threads[0] != event_thread
            assert srv.bound and not srv.closed.is_set()
            assert srv._push_watch is not None and not srv._push_watch.done()
        finally:
            task = srv._push_watch
            await srv.stop(notify=False)
            assert srv._push_watch is None and task.done()
    try:
        asyncio.run(scenario())
        assert (key_path.read_bytes(), key_path.stat().st_mode) == before
        assert env.bridge.calls == []
    finally:
        env.store.close()


def test_hourly_lane_rechecks_live_availability_and_stops_cleanly(tmp_path, monkeypatch):
    env = seeded(tmp_path)
    digest = registration(env, kid="old")
    config = block(enabled=False, relay_kids=["new"])
    env.ctx.push_settings = lambda: config
    env.ctx.direct_send_flag = lambda: True
    env.ctx.approvals_available = lambda: True
    monkeypatch.setattr(server, "PUSH_PURGE_INTERVAL_S", 0.01)
    original = env.store.purge_push_steps
    calls = []

    async def scenario():
        second_pass = asyncio.Event()
        def steps(**kw):
            calls.append(kw["push_available"])
            yield from original(**kw)
            if len(calls) >= 2:
                second_pass.set()
        monkeypatch.setattr(env.store, "purge_push_steps", steps)
        srv = listener(env)
        await srv.start()
        assert row(env.store, digest)["state"] == "active"  # off is inert, not kid expiry
        config["enabled"] = True
        try:
            await asyncio.wait_for(second_pass.wait(), 1)
            assert calls[:2] == [False, True]
            assert row(env.store, digest)["state"] == "expired"
        finally:
            await srv.stop(notify=False)
        count = len(calls)
        await asyncio.sleep(0.04)
        assert len(calls) == count
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


@pytest.mark.parametrize("key_state", ["missing", "wrong_length"])
def test_key_loss_skips_hash_only_and_never_creates_file(tmp_path, key_state, monkeypatch):
    env = seeded(tmp_path)
    valid = registration(env, kid="removed")
    seed_device(env.store, "expired")
    expired = seed_row(
        env.store, "expired", iid=env.iid, host_generation=env.store.revocation_epoch(),
        expires=env.clock.now,
    )
    key_path = env.custody.k_grace_path
    if key_state == "missing":
        key_path.unlink()
    else:
        key_path.write_bytes(b"short")
    monkeypatch.setattr(
        env.identity, "k_grace", lambda: pytest.fail("listener repaired unreadable push key")
    )
    async def scenario():
        srv = listener(env)
        await srv.start()
        try:
            assert row(env.store, valid)["state"] == "active"
            assert row(env.store, expired)["state"] == "expired"
        finally:
            await srv.stop(notify=False)
    try:
        asyncio.run(scenario())
        if key_state == "missing":
            assert not key_path.exists()
        else:
            assert key_path.read_bytes() == b"short"
    finally:
        env.store.close()


def test_cancel_between_committed_passes_leaves_no_lock_or_partial_retirement(
    tmp_path, monkeypatch
):
    env = seeded(tmp_path)
    digest = registration(env)
    env.store.set_device_state("device-synthetic", "REVOKED")
    original = env.store.purge_push_steps
    observations = []
    async def scenario():
        srv = listener(env)
        def steps(**kw):
            for _ in original(**kw):
                assert not env.store._require_conn().in_transaction
                observations.append((row(env.store, digest)["state"],
                                     generation(env.store, "device-synthetic")))
                asyncio.get_running_loop().call_soon(asyncio.current_task().cancel)
                yield None
        monkeypatch.setattr(env.store, "purge_push_steps", steps)
        with pytest.raises(asyncio.CancelledError):
            await srv._purge_push_once()
        assert observations == [("retired", 2)]
        assert not env.store._require_conn().in_transaction
        with env.store.transaction() as conn:
            count = conn.execute(
                "SELECT count(*) FROM audit WHERE event='push_retire'"
            ).fetchone()[0]
            assert count == 1
        monkeypatch.setattr(env.store, "purge_push_steps", original)
        await srv._purge_push_once()
        assert row(env.store, digest) is None
        assert generation(env.store, "device-synthetic") == 0
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()


def test_startup_cleanup_disk_full_is_fixed_log_failure_not_listener_failure(tmp_path, caplog):
    env = seeded(tmp_path)
    digest = registration(env)
    env.store.set_device_state("device-synthetic", "REVOKED")
    conn = install_full_injector(env.store, "audit")
    caplog.set_level(logging.INFO)
    async def scenario():
        srv = listener(env)
        await srv.start()
        try:
            assert srv.bound and not srv.closed.is_set()
            assert conn.attempts == 1
            assert row(env.store, digest)["state"] == "active"
            assert generation(env.store, "device-synthetic") == 1
            conn.execute("PRAGMA max_page_count=1073741823")
            await srv._purge_push_once()
            assert row(env.store, digest) is None
            assert generation(env.store, "device-synthetic") == 0
            audit = [r for r in env.store.audit_events() if r["event"] == "push_retire"]
            assert len(audit) == 1
        finally:
            await srv.stop(notify=False)
    try:
        asyncio.run(scenario())
        assert any(
            "event=push_purge outcome=cleanup_failed" in r.getMessage() for r in caplog.records
        )
        assert all("disk is full" not in r.getMessage() for r in caplog.records)
    finally:
        env.store.close()


def test_key_reader_failure_still_runs_non_hash_maintenance(tmp_path, monkeypatch):
    env = seeded(tmp_path)
    digest = registration(env)
    env.clock.now += 3600
    async def failed_read():
        raise OSError("private synthetic key failure")
    monkeypatch.setattr(env.identity, "read_k_grace_for_push", failed_read)
    async def scenario():
        await listener(env)._purge_push_once()
        assert row(env.store, digest)["state"] == "expired"
        assert generation(env.store, "device-synthetic") == 2
    try:
        asyncio.run(scenario())
    finally:
        env.store.close()
