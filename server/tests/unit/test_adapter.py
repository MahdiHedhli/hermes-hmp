"""T024: `HmpAdapter` handles lifecycle only (FR-053, SR-007, CS-22).

A stand-in for Hermes's documented platform-plugin API (`gateway.platforms.base` and
`gateway.config`) is installed in `sys.modules` for the duration of each test, so the real adapter
module is exercised without importing Hermes. The listener runs on loopback with a real identity
in an isolated temporary home.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import sys
import types
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import cli, reads, wire

from .hmp_kit import Env
from .test_server import WRITE_PATHS, tls_exchange

SECRET_REPLY = "Your pairing code is ABCD2345; share it with the operator."


@dataclass
class _SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None


class _BaseAdapter:
    def __init__(self, config: Any, platform: Any) -> None:
        self.config = config
        self.platform = platform
        self.states: list[str] = []
        self.handled: list[Any] = []

    def _mark_connected(self, *, listener_base: str | None = None) -> None:
        self.states.append("connected")

    def _mark_disconnected(self) -> None:
        self.states.append("disconnected")

    def _set_fatal_error(self, code: str, message: str, *, retryable: bool) -> None:
        self.states.append(f"fatal:{code}:{retryable}")

    async def handle_message(self, event: Any) -> None:  # the Hermes hand-off
        self.handled.append(event)


@pytest.fixture()
def adapter_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    gateway = types.ModuleType("gateway")
    config = types.ModuleType("gateway.config")
    platforms = types.ModuleType("gateway.platforms")
    base = types.ModuleType("gateway.platforms.base")
    config.Platform = lambda name: ("platform", name)  # type: ignore[attr-defined]
    base.BasePlatformAdapter = _BaseAdapter  # type: ignore[attr-defined]
    base.SendResult = _SendResult  # type: ignore[attr-defined]
    for name, mod in (
        ("gateway", gateway),
        ("gateway.config", config),
        ("gateway.platforms", platforms),
        ("gateway.platforms.base", base),
    ):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, "hmp_plugin.adapter", raising=False)
    module = importlib.import_module("hmp_plugin.adapter")
    yield module
    sys.modules.pop("hmp_plugin.adapter", None)


class _Config:
    def __init__(self, extra: dict[str, Any]) -> None:
        self.extra = extra


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_send_drops_the_reply_unlogged(
    adapter_module: types.ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    adapter = adapter_module.HmpAdapter(_Config({"port": 1}))
    with caplog.at_level(logging.DEBUG):
        result = asyncio.run(adapter.send("c_x", SECRET_REPLY, metadata={"k": "v"}))
    assert result.success is True
    assert "ABCD2345" not in caplog.text and "pairing code" not in caplog.text
    info = asyncio.run(adapter.get_chat_info("c_x"))
    assert info["type"] == "dm" and "name" in info


def test_bad_listener_config_does_not_connect(adapter_module: types.ModuleType) -> None:
    wildcard = {"bind": "0.0.0.0", "port": 18920}  # noqa: S104 - must be refused
    adapter = adapter_module.HmpAdapter(_Config(wildcard))
    assert asyncio.run(adapter.connect()) is False
    assert "connected" not in adapter.states


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        # Absent: the default is OFF (opt-in).
        (None, False),
        ({}, False),
        ({"port": 1}, False),
        # Configured: only the boolean True enables it.
        ({"session_browsing": True}, True),
        ({"session_browsing": False}, False),
        ({"session_browsing": "false"}, False),
        ({"session_browsing": "False"}, False),
        ({"session_browsing": "true"}, False),
        ({"session_browsing": "no"}, False),
        ({"session_browsing": 0}, False),
        ({"session_browsing": 1}, False),
        ({"session_browsing": None}, False),
        ({"session_browsing": []}, False),
        ({"session_browsing": {}}, False),
        # A malformed `extra` itself fails closed.
        ("oops", False),
        (["session_browsing"], False),
    ],
)
def test_session_browsing_config_only_an_explicit_true_enables_it(
    adapter_module: types.ModuleType, extra: object, expected: bool
) -> None:
    assert adapter_module._session_browsing_enabled(extra) is expected


def test_lifecycle_and_zero_handoff_on_write_paths(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        assert adapter.states == ["connected"]
        loop = asyncio.get_running_loop()
        for method, path in WRITE_PATHS:
            body = wire.dump_json({"text": "hi"})
            req = (
                f"{method} /hmp/v1{path} HTTP/1.1\r\nHost: t\r\nContent-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii") + body
            status, _ = await loop.run_in_executor(
                None, lambda r=req: tls_exchange(port, env.iid, r)
            )
            assert status == "404", path
        status, _ = await loop.run_in_executor(
            None,
            lambda: tls_exchange(
                port, env.iid, b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n"
            ),
        )
        assert status == "200"
        await adapter.disconnect()
        assert adapter.states[-1] == "disconnected"

    asyncio.run(main())
    assert adapter.handled == []  # zero handle_message calls (FR-053)
    # `served_profiles` (OD-F8, 2026-09-27): read once on `connect()` for the listener record's
    # `profiles` field; `capability_versions` on `/ready` only; nothing on the write paths.
    assert env.bridge.calls == ["served_profiles", "capability_versions"]


def test_connect_writes_served_profiles_into_listener_record(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OD-F8 (2026-09-27): the adapter writes the bridge's served profiles, with the same
    `_fallback_display_name` rule the roster uses, into the listener record -- so `pair offer`'s
    one-command flow can list bots by name without importing Hermes (S1)."""
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default", "netmin"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    assert asyncio.run(adapter.connect()) is True
    record = cli.read_listener_record(
        cli.listener_record_path(env.custody.anchor_dir), iid=env.iid
    )
    asyncio.run(adapter.disconnect())

    assert record.profiles is not None
    assert dict(record.profiles) == {
        "default": reads._fallback_display_name("default"),
        "netmin": reads._fallback_display_name("netmin"),
    }


def test_connect_with_no_bridge_writes_no_profiles(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unsupported build has no bridge: the record's `profiles` stays `None`, exactly as it did
    before OD-F8, so `pair offer` falls back to the placeholder next-steps text."""
    from hmp_plugin.compat import CompatResult, CompatStatus

    env = Env(tmp_path, compat=CompatResult(CompatStatus.UNSUPPORTED))
    assert env.ctx.bridge is None
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    assert asyncio.run(adapter.connect()) is True
    record = cli.read_listener_record(
        cli.listener_record_path(env.custody.anchor_dir), iid=env.iid
    )
    asyncio.run(adapter.disconnect())

    assert record.profiles is None


# --------------------------------------------------------------------------------------------------
# Live-bug fix (multiplexed gateway, 2026-09-27): the multiplexer brings secondary profiles online
# strictly AFTER `connect()` returns (`gateway/run_profile_reconcile.py`'s own
# `served_profile_names` is live bookkeeping, refreshed only as profiles are hot-added/removed) --
# so the listener record's `profiles`, written once at connect, must be kept current:
# opportunistically on every successful roster/authorize read (`test_reads.py`'s
# `on_served_profiles` hook tests), and by this adapter's own periodic safety-net refresh (below).
# --------------------------------------------------------------------------------------------------


def test_sync_refresh_rewrites_on_growth_and_shrink_keeping_nonce_pid_and_mode(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        path = cli.listener_record_path(env.custody.anchor_dir)
        first = cli.read_listener_record(path, iid=env.iid)
        assert dict(first.profiles or ()) == {"default": reads._fallback_display_name("default")}
        assert (path.stat().st_mode & 0o777) == 0o600

        # Growth: a hot-added profile.
        adapter._sync_refresh(["default", "netmin"])
        grown = cli.read_listener_record(path, iid=env.iid)
        assert dict(grown.profiles or ()) == {
            "default": reads._fallback_display_name("default"),
            "netmin": reads._fallback_display_name("netmin"),
        }
        # SR-7: a refresh is not a new listener incarnation -- the nonce (and pid) stay the same
        # across the rewrite, only `profiles` moves.
        assert grown.nonce == first.nonce
        assert grown.pid == first.pid
        assert (path.stat().st_mode & 0o777) == 0o600

        # Shrink: a profile unserved again.
        adapter._sync_refresh(["default"])
        shrunk = cli.read_listener_record(path, iid=env.iid)
        assert dict(shrunk.profiles or ()) == {"default": reads._fallback_display_name("default")}
        assert shrunk.nonce == first.nonce

        await adapter.disconnect()

    asyncio.run(main())


def test_sync_refresh_skips_the_write_when_the_served_set_is_unchanged(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default", "netmin"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        calls: list[Any] = []
        real_write = cli.write_listener_record

        def spy_write(*a: Any, **k: Any) -> None:
            calls.append((a, k))
            real_write(*a, **k)

        monkeypatch.setattr(cli, "write_listener_record", spy_write)

        adapter._sync_refresh(["netmin", "default"])  # same set, different order: not a change
        assert calls == []  # the cheap comparison short-circuited the write entirely

        adapter._sync_refresh(["default", "netmin", "liteforms-connector"])
        assert len(calls) == 1  # an actual change did write, exactly once

        await adapter.disconnect()

    asyncio.run(main())


def test_sync_refresh_failure_is_logged_and_leaves_the_previous_record_intact(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        path = cli.listener_record_path(env.custody.anchor_dir)
        before = path.read_bytes()

        def boom(*_a: Any, **_k: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(cli, "write_listener_record", boom)
        adapter._sync_refresh(["default", "netmin"])  # must not raise
        assert path.read_bytes() == before  # untouched: the failed rewrite changed nothing on disk

        await adapter.disconnect()

    asyncio.run(main())


def test_observe_served_profiles_hook_never_raises(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_observe_served_profiles` is what `Reads.roster`/`Authorize.authorize` call; a malformed
    served set must never surface as an exception to either of them."""
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        adapter._observe_served_profiles(None)  # type: ignore[arg-type]  # not iterable: must not raise
        await adapter.disconnect()

    asyncio.run(main())


def test_periodic_refresh_picks_up_a_hot_added_profile_and_is_cancelled_on_disconnect(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(adapter_module, "PROFILE_REFRESH_INITIAL_DELAY_S", 0.01)
    monkeypatch.setattr(adapter_module, "PROFILE_REFRESH_INTERVAL_S", 0.02)
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        task = adapter._profile_refresh_task
        assert task is not None and not task.done()

        # The multiplexer hot-adds a profile strictly after `connect()` -- the live bug's own
        # timing (`gateway/run_profile_reconcile.py`).
        env.bridge.served_profiles = lambda: ["default", "netmin"]  # type: ignore[method-assign]
        path = cli.listener_record_path(env.custody.anchor_dir)
        for _ in range(50):
            await asyncio.sleep(0.02)
            record = cli.read_listener_record(path, iid=env.iid)
            if record.profiles and dict(record.profiles).get("netmin"):
                break
        else:
            raise AssertionError("the periodic refresh never picked up the hot-added profile")

        await adapter.disconnect()
        assert adapter._profile_refresh_task is None
        assert task.cancelled() or task.done()

    asyncio.run(main())


def test_periodic_refresh_is_cancelled_on_listener_closed(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR7-6: an identity change closes the listener out from under the adapter (not through
    `disconnect()`); the periodic task must not be left running against a dead listener."""
    from hmp_plugin import identity

    monkeypatch.setattr(adapter_module, "PROFILE_REFRESH_INITIAL_DELAY_S", 0.01)
    monkeypatch.setattr(adapter_module, "PROFILE_REFRESH_INTERVAL_S", 0.02)
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: ["default"]  # type: ignore[method-assign]
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        task = adapter._profile_refresh_task
        assert task is not None
        srv = adapter._server
        identity.rotate_key(env.store, **env.kwargs)
        await asyncio.wait_for(srv.closed.wait(), timeout=10)
        await asyncio.sleep(0)
        assert adapter._profile_refresh_task is None
        assert task.cancelled() or task.done()
        await adapter.disconnect()  # idempotent: no live server, no live task

    asyncio.run(main())


def test_identity_change_reports_fatal_and_stays_closed(
    adapter_module: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hmp_plugin import identity

    env = Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))

    async def main() -> None:
        assert await adapter.connect() is True
        srv = adapter._server
        identity.rotate_key(env.store, **env.kwargs)
        await asyncio.wait_for(srv.closed.wait(), timeout=10)
        await asyncio.sleep(0)
        assert adapter.states[-1] == "fatal:hmp_identity_changed:False"
        loop = asyncio.get_running_loop()
        status, _ = await loop.run_in_executor(
            None,
            lambda: tls_exchange(
                port, env.iid, b"GET /hmp/v1/ready HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n"
            ),
        )
        assert status == "connection_failure"
        await adapter.disconnect()

    asyncio.run(main())
