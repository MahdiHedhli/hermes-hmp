"""Disposable T029 observer, copied only into a private fixture plugin.

Never imported by the production package. No prompt, route, device, handle or
body is serialized. The subclass retains real scheduling, sleep and send checks.
This is synchronization instrumentation, not native execution evidence itself.
"""

from __future__ import annotations

import asyncio
import json
import os
import stat
import time
from pathlib import Path

COUNT_CAP = 4096
FILE_CAP = 4096
WAIT_S = 30
FIELDS = frozenset({
    "scheduled", "waiting", "wait_cancelled", "send_completed", "closed",
    "pending_slots", "slots", "queue", "hints",
})
FILES = frozenset({"current.json", "closed.json", "armed", "release"})


def private_root(root: Path) -> Path:
    if root.is_symlink() or root != root.resolve():
        raise ValueError("fixture journal must be a resolved private directory")
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("fixture journal must be private")
    if info.st_uid != os.getuid():
        raise ValueError("fixture journal owner mismatch")
    return root


def _checked_file(info: os.stat_result) -> None:
    if (
        not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_size > FILE_CAP
    ):
        raise ValueError("unsafe fixture journal file")


def read_file(root: Path, name: str) -> bytes | None:
    private_root(root)
    if name not in FILES:
        raise ValueError("unknown fixture journal file")
    try:
        # Nonblocking open lets fstat reject a FIFO without waiting for a writer.
        fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as handle:
        _checked_file(os.fstat(handle.fileno()))
        data = handle.read(FILE_CAP + 1)
    if len(data) > FILE_CAP:
        raise ValueError("fixture journal file grew beyond bound")
    return data


def write_file(root: Path, name: str, data: bytes) -> None:
    private_root(root)
    if name not in FILES or type(data) is not bytes or len(data) > FILE_CAP:
        raise ValueError("invalid fixture journal write")
    # Never follow or replace an existing symlink/hardlink/nonprivate file.
    read_file(root, name)
    temporary = root / ("." + name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, root / name)
    finally:
        if temporary.exists():
            temporary.unlink()


def snapshot(root: Path, name: str = "current.json") -> dict[str, int | bool] | None:
    data = read_file(root, name)
    if data is None:
        return None
    value = json.loads(data)
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("invalid fixture observation")
    if type(value["closed"]) is not bool or any(
        type(v) is not int or not 0 <= v <= COUNT_CAP
        for k, v in value.items() if k != "closed"
    ):
        raise ValueError("unbounded fixture observation")
    return value


class Journal:
    def __init__(self, root: Path) -> None:
        self.root = private_root(root)
        self.counts = {name: 0 for name in FIELDS if name != "closed"}
        self.closed = False

    def increment(self, name: str) -> None:
        if name not in self.counts:
            raise ValueError("unknown fixture counter")
        self.counts[name] = min(COUNT_CAP, self.counts[name] + 1)

    def record(self, dispatcher, *, closed: bool = False) -> None:
        self.closed = closed
        for name, count in (
            ("pending_slots", sum(slot.pending is not None for slot in dispatcher.slots.values())),
            ("slots", len(dispatcher.slots)), ("queue", dispatcher.queue.qsize()),
            ("hints", len(dispatcher.ctx.push_hints)),
        ):
            self.counts[name] = min(COUNT_CAP, count)
        raw = json.dumps(self.counts | {"closed": self.closed}, sort_keys=True).encode("ascii")
        write_file(self.root, "closed.json" if closed else "current.json", raw)

    async def sleep(self, delay: float, dispatcher) -> None:
        # Always await the actual production delay before any test barrier.
        await asyncio.sleep(delay)
        if read_file(self.root, "armed") != b"arm\n":
            return
        self.increment("waiting")
        self.record(dispatcher)
        deadline = time.monotonic() + WAIT_S
        try:
            while read_file(self.root, "release") != b"release\n":
                if time.monotonic() >= deadline:
                    raise TimeoutError("fixture release barrier expired")
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            self.increment("wait_cancelled")
            self.record(dispatcher)
            raise


def observed_dispatcher(base, root: Path):
    """Wrap actual production methods; do not inject a fake clock or gate."""
    class ObservedDispatcher(base):
        def __init__(self, *args, **kwargs):
            self.journal = Journal(root)
            if "sleep" in kwargs:
                raise ValueError("fixture cannot replace an already injected sleep")
            kwargs["sleep"] = self._observed_sleep
            super().__init__(*args, **kwargs)

        async def _observed_sleep(self, delay):
            await self.journal.sleep(delay, self)

        def _schedule(self, pending):
            super()._schedule(pending)
            if any(slot.pending is pending for slot in self.slots.values()):
                self.journal.increment("scheduled")
                self.journal.record(self)

        async def _send(self, pending, slot):
            await super()._send(pending, slot)
            # Only an actual return counts. Cancellation/errors never count as rechecks.
            self.journal.increment("send_completed")
            self.journal.record(self)

        async def close(self):
            await super().close()
            self.journal.record(self, closed=True)

    return ObservedDispatcher


def install() -> None:
    """Called by the fresh copied bootstrap, never by tracked hmp_plugin."""
    here = Path(__file__).resolve().parent
    if here.name != "_hmp_plugin" or Path(__file__).is_symlink():
        raise ValueError("observer requires the copied fixture plugin")
    root = private_root(here.parent / "push-observation")
    from . import server  # Only meaningful inside the copied package.

    server.PushDispatcher = observed_dispatcher(server.PushDispatcher, root)
