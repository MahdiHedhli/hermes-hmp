"""Instrumentation bounds/cancellation only, never native Hermes evidence."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import push_native_observer as observer
import pytest


def _root(tmp_path):
    root = (tmp_path / "observation").resolve()
    root.mkdir(mode=0o700)
    return root


def _dispatcher():
    return SimpleNamespace(
        slots={1: SimpleNamespace(pending=object())}, queue=asyncio.Queue(),
        ctx=SimpleNamespace(push_hints=[]),
    )


def test_private_bounded_closed_observations_and_symlink_rejection(tmp_path):
    root = _root(tmp_path)
    journal = observer.Journal(root)
    for _ in range(observer.COUNT_CAP + 10):
        journal.increment("scheduled")
    dispatcher = _dispatcher()
    journal.record(dispatcher)
    value = observer.snapshot(root)
    assert set(value) == observer.FIELDS
    assert value["scheduled"] == observer.COUNT_CAP and value["pending_slots"] == 1
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in root.iterdir())
    with pytest.raises(ValueError, match="invalid fixture journal"):
        observer.write_file(root, "release", b"x" * (observer.FILE_CAP + 1))
    external = tmp_path / "external"
    external.write_bytes(b"unchanged")
    (root / "release").symlink_to(external)
    with pytest.raises(OSError):
        observer.write_file(root, "release", b"release\n")
    assert external.read_bytes() == b"unchanged"
    root.chmod(0o755)
    with pytest.raises(ValueError, match="private"):
        observer.snapshot(root)


def test_controlled_barrier_follows_real_delay_and_propagates_cancellation(tmp_path):
    root = _root(tmp_path)
    journal, dispatcher = observer.Journal(root), _dispatcher()
    observer.write_file(root, "armed", b"arm\n")

    async def drive():
        task = asyncio.create_task(journal.sleep(0.15, dispatcher))
        await asyncio.sleep(0.05)
        assert observer.snapshot(root) is None  # no wait observation before actual delay
        async with asyncio.timeout(2):
            while observer.snapshot(root) is None:  # noqa: ASYNC110 -- cross-process file port
                await asyncio.sleep(0.01)
        assert observer.snapshot(root)["waiting"] == 1
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert observer.snapshot(root)["wait_cancelled"] == 1
        next_task = asyncio.create_task(journal.sleep(0, dispatcher))
        await asyncio.sleep(0)
        observer.write_file(root, "release", b"release\n")
        await asyncio.wait_for(next_task, timeout=1)

    asyncio.run(drive())
    assert b"unchanged" not in (root / "current.json").read_bytes()


def test_fifo_is_rejected_without_waiting_for_a_writer(tmp_path):
    root = _root(tmp_path)
    os.mkfifo(root / "armed", mode=0o600)
    # A child timeout bounds a regression to blocking open; no FIFO writer exists.
    code = (
        "from pathlib import Path; import push_native_observer as o; "
        f"o.read_file(Path({str(root)!r}), 'armed')"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(observer.__file__)),
        timeout=3, check=False,
    )
    assert result.returncode != 0
    assert "ValueError: unsafe fixture journal file" in result.stderr


def test_wrapper_calls_actual_base_and_does_not_count_failed_send(tmp_path):
    root = _root(tmp_path)

    class Base:
        def __init__(self, *, sleep):
            self.sleep = sleep
            value = _dispatcher()
            self.slots, self.queue, self.ctx = value.slots, value.queue, value.ctx
            self.calls = []

        def _schedule(self, pending):
            self.calls.append("schedule")
            self.slots[1].pending = pending

        async def _send(self, pending, slot):
            self.calls.append("send")
            if pending is None:
                raise ValueError("failed base send")

        async def close(self):
            self.calls.append("close")
            self.slots.clear()

    wrapped = observer.observed_dispatcher(Base, root)()
    pending = object()
    wrapped._schedule(pending)
    assert observer.snapshot(root)["scheduled"] == 1

    async def drive():
        await wrapped._send(pending, wrapped.slots[1])
        with pytest.raises(ValueError, match="failed base"):
            await wrapped._send(None, wrapped.slots[1])
        assert observer.snapshot(root)["send_completed"] == 1
        await wrapped.close()

    asyncio.run(drive())
    closed = observer.snapshot(root, "closed.json")
    assert closed["closed"] and closed["slots"] == closed["pending_slots"] == 0
    assert wrapped.calls == ["schedule", "send", "send", "close"]
    invalid = closed | {"private_prompt": "not allowed"}
    observer.write_file(root, "closed.json", json.dumps(invalid).encode())
    with pytest.raises(ValueError, match="invalid fixture observation"):
        observer.snapshot(root, "closed.json")
