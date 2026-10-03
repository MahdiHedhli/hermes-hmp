"""SD1 causal local-record controls; fake server/ready, no native import or socket."""

from __future__ import annotations

import asyncio
import http.client
import json
import logging
import os
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import cli, crypto, reads

from .hmp_kit import Env
from .test_adapter import _Config, adapter_module  # noqa: F401 - fake gateway fixture
from .test_cli import TAILNET_HOST, Cli

IID = "a" * 52
PROFILES = ["p" + f"{i:03d}" + "a" * 60 for i in range(128)]


def _full(path: Path, **changes: Any) -> None:
    args: dict[str, Any] = {
        "host": TAILNET_HOST,
        "port": 65535,
        "iid": IID,
        "nonce": "f" * 32,
        "profiles": [(p, reads._fallback_display_name(p)) for p in PROFILES],
        "health_checked_at": 2**63 - 1,
        "health": [(p, "unavailable", "unavailable", "unavailable") for p in PROFILES],
    }
    args.update(changes)
    cli.write_listener_record(path, **args)


def _read(path: Path, iid: str = IID) -> cli.ListenerRecord:
    return cli.read_listener_record(path, iid=iid, pid_alive=lambda _pid: True)


def _install(path: Path, data: dict[str, Any], *, padded: int = 16385) -> None:
    # Deliberately mutated reader inputs, not a second implementation of the writer.
    raw = json.dumps(data).encode()
    path.write_bytes(raw + b" " * max(0, padded - len(raw)))
    path.chmod(0o600)


@pytest.mark.parametrize(
    "host,size", [("fe80::1%" + "\\" * 120, 41283), ("::%" + "\\" * 125, 41288)]
)
def test_extended_actual_samples_preserve_every_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str, size: int
) -> None:
    path = tmp_path / "listener.json"
    monkeypatch.setattr(os, "getpid", lambda: 2**31)
    names = [(p, "\\" * 64) for p in PROFILES]
    health = [(p, "unavailable", "unavailable", "unavailable") for p in reversed(PROFILES)]
    _full(path, host=host, nonce="\\" * 128, profiles=names, health=health)
    assert len(path.read_bytes()) == size <= 41291 < 65536
    record = _read(path)
    assert (record.host, record.port, record.iid, record.pid, record.nonce) == (
        host,
        65535,
        IID,
        2**31,
        "\\" * 128,
    )
    assert record.profiles == tuple(names) and record.health == tuple(health)
    assert record.health_checked_at == 2**63 - 1
    assert path.stat().st_mode & 0o777 == 0o600


def test_file_exact_cap_and_one_over(tmp_path: Path) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (65536 - len(raw)))
    assert len(_read(path).profiles or ()) == 128
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(cli.ListenerRecordError, match=r"^the listener record is malformed$"):
        _read(path)


@pytest.mark.parametrize("kind", ["absent_health", "unicode", "unknown", "duplicates"])
def test_legacy_threshold_does_not_admit_loose_oversized_records(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "listener.json"
    cli.write_listener_record(
        path, host="127.0.0.1", port=1, iid=IID, nonce="λ", profiles=[("UPPER", "λ")]
    )
    data = json.loads(path.read_bytes())
    if kind == "absent_health":
        data.pop("health")
        data.pop("health_checked_at")
    elif kind == "unknown":
        data["historical_extra"] = "kept small"
    raw = json.dumps(data).encode()
    if kind == "duplicates":
        raw = raw[:-1] + b', "port": 1}'
    path.write_bytes(raw + b" " * (16384 - len(raw)))
    legacy = _read(path)
    assert legacy.nonce == "λ" and legacy.profiles == (("UPPER", "λ"),)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(cli.ListenerRecordError):
        _read(path)


@pytest.mark.parametrize(
    "problem",
    [
        "format_bool",
        "port_bool",
        "port_high",
        "pid_zero",
        "time_bool",
        "time_negative",
        "time_high",
        "iid_noncanonical",
        "nonce_long",
        "host_long",
        "name_long",
        "unicode",
        "control",
        "bad_id",
        "id_long",
        "duplicate_profile",
        "129",
        "missing_health",
        "health_null",
        "missing_row",
        "duplicate_row",
        "unknown_code",
        "extra_row",
        "unknown_member",
        "duplicate_member",
    ],
)
def test_extended_malformed_fields_never_receive_legacy_fallback(
    tmp_path: Path, problem: str
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    data = json.loads(path.read_bytes())
    if problem == "format_bool":
        data["format"] = True
    elif problem == "port_bool":
        data["port"] = True
    elif problem == "port_high":
        data["port"] = 65536
    elif problem == "pid_zero":
        data["pid"] = 0
    elif problem == "time_bool":
        data["health_checked_at"] = True
    elif problem == "time_negative":
        data["health_checked_at"] = -1
    elif problem == "time_high":
        data["health_checked_at"] = 2**63
    elif problem == "iid_noncanonical":
        data["iid"] = "a" * 51 + "b"
    elif problem == "nonce_long":
        data["nonce"] = "a" * 129
    elif problem == "host_long":
        data["host"] = "::%" + "a" * 126
    elif problem == "name_long":
        data["profiles"][0][1] = "a" * 65
    elif problem == "unicode":
        data["profiles"][0][1] = "😀" * 16
    elif problem == "control":
        data["profiles"][0][1] = "\x00" * 64
    elif problem == "bad_id":
        data["profiles"][0][0] = "X"
    elif problem == "id_long":
        data["profiles"][0][0] = "a" * 65
        data["health"][0][0] = "a" * 65
    elif problem == "duplicate_profile":
        data["profiles"][1] = data["profiles"][0]
    elif problem == "129":
        data["profiles"].append(["extra", "Extra"])
        data["health"].append(["extra", "ready", "ready", "ready"])
    elif problem == "missing_health":
        data.pop("health")
    elif problem == "health_null":
        data["health"] = None
    elif problem == "missing_row":
        data["health"].pop()
    elif problem == "duplicate_row":
        data["health"][1] = data["health"][0]
    elif problem == "unknown_code":
        data["health"][0][1] = "private_key_sentinel"
    elif problem == "extra_row":
        data["health"].append(data["health"][0])
    elif problem == "unknown_member":
        data["extra"] = "private_key_sentinel"
    _install(path, data)
    if problem == "duplicate_member":
        path.write_bytes(path.read_bytes().rstrip()[:-1] + b', "port":65535}')
    with pytest.raises(cli.ListenerRecordError) as caught:
        _read(path, data["iid"] if problem == "iid_noncanonical" else IID)
    assert "private_key_sentinel" not in str(caught.value)


@pytest.mark.parametrize(
    "raw",
    [b"[" * 20000 + b"]" * 20000, b"\xff", b'{"bad":'],
    ids=["deep", "utf8", "incomplete"],
)
def test_invalid_json_has_fixed_errors(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "listener.json"
    path.write_bytes(raw + b" " * max(0, 16385 - len(raw)))
    path.chmod(0o600)
    with pytest.raises(cli.ListenerRecordError, match=r"^the listener record is unreadable$"):
        _read(path)


@pytest.mark.parametrize(
    "cause", ["loose", "unicode", "too_many", "long_string", "huge_int", "generator", "encoding"]
)
def test_writer_projection_budget_and_errors_preserve_old_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    before, inode = path.read_bytes(), path.stat().st_ino
    changes: dict[str, Any] = {}
    if cause == "loose":
        changes["health"] = None
    elif cause == "unicode":
        changes["profiles"] = [(p, "λ" * 64) for p in PROFILES]
    elif cause == "too_many":

        class TooMany(Sequence):
            def __len__(self) -> int:
                return 4097

            def __getitem__(self, _index: Any) -> Any:
                raise AssertionError("must not traverse")

        changes["profiles"] = TooMany()
    elif cause == "long_string":
        changes["nonce"] = "private_key_sentinel" * 1000
    elif cause == "huge_int":
        changes["health_checked_at"] = 1 << 65536
    elif cause == "generator":
        changes["profiles"] = (None for _ in range(1))
    elif cause == "encoding":

        def broken(_self: Any, _data: Any) -> Any:
            raise ValueError("private_key_sentinel")

        monkeypatch.setattr(json.JSONEncoder, "iterencode", broken)
    with pytest.raises(OSError) as caught:
        _full(path, **changes)
    assert str(caught.value) in {
        "the listener record is malformed",
        "listener record exceeds size limit",
    }
    assert path.read_bytes() == before and path.stat().st_ino == inode
    assert not list(tmp_path.glob("*.tmp"))


def test_writer_exact_budget_then_one_less_keeps_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    size = len(path.read_bytes())
    monkeypatch.setattr(cli, "MAX_LISTENER_FILE_BYTES", size)
    _full(path)
    before, inode = path.read_bytes(), path.stat().st_ino
    monkeypatch.setattr(cli, "MAX_LISTENER_FILE_BYTES", size - 1)
    with pytest.raises(OSError, match=r"^listener record exceeds size limit$"):
        _full(path)
    assert path.read_bytes() == before and path.stat().st_ino == inode


@pytest.mark.parametrize("bad", ["rows", "scalar", "integer", "row_width"])
def test_projection_limits_refuse_before_json_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    before = path.read_bytes()
    changes = {
        "rows": {"profiles": [("a", "A")] * 4097},
        "scalar": {"nonce": "a" * 16385},
        "integer": {"health_checked_at": 1 << 65536},
        "row_width": {"profiles": [("a",)]},
    }[bad]

    def forbidden(_data: Any) -> bytes:
        raise AssertionError("projection must fail before JSON encoding")

    monkeypatch.setattr(cli, "_encode_listener_record", forbidden)
    with pytest.raises(OSError, match=r"^the listener record is malformed$"):
        _full(path, **changes)
    assert path.read_bytes() == before


@pytest.mark.parametrize("stage", ["fsync", "replace"])
def test_atomic_io_failure_keeps_old_large_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    before = path.read_bytes()

    def fault(*_a: Any, **_kw: Any) -> None:
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(os, stage, fault)
    with pytest.raises(OSError):
        _full(path)
    assert path.read_bytes() == before and not list(tmp_path.glob("*.tmp"))


def test_current_large_removal_and_foreign_pid_fence(tmp_path: Path) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    cli.remove_listener_record(path)
    assert not path.exists()
    _full(path)
    data = json.loads(path.read_bytes())
    data["pid"] += 1
    _install(path, data)
    before = path.read_bytes()
    cli.remove_listener_record(path)
    assert path.read_bytes() == before


def test_removal_skips_deep_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "listener.json"
    raw = b"[" * 20000 + b"]" * 20000
    path.write_bytes(raw)
    path.chmod(0o600)
    cli.remove_listener_record(path)
    assert path.read_bytes() == raw


@pytest.mark.parametrize("part", ["top", "row", "scalar"])
def test_projection_refuses_subclass_hooks_before_traversal(tmp_path: Path, part: str) -> None:
    class HookList(list):
        def __len__(self) -> int:
            raise AssertionError("must not call subclass len")

        def __iter__(self) -> Any:
            raise AssertionError("must not call subclass iteration")

    class HookString(str):
        def __len__(self) -> int:
            raise AssertionError("must not call subclass len")

    path = tmp_path / "listener.json"
    _full(path)
    before = path.read_bytes()
    changes = {
        "profiles": HookList()
        if part == "top"
        else [HookList(["a", "A"])]
        if part == "row"
        else [("a", HookString("A"))],
    }
    with pytest.raises(OSError, match=r"^the listener record is malformed$"):
        _full(path, **changes)
    assert path.read_bytes() == before


def test_large_removal_preserves_replacement_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, replacement = tmp_path / "listener.json", tmp_path / "new.json"
    _full(path)
    _full(replacement, nonce="replacement")
    new = replacement.read_bytes()
    lstat = os.lstat

    def swap(name: Any, *args: Any, **kwargs: Any) -> Any:
        if Path(name) == path and replacement.exists():
            os.replace(replacement, path)
        return lstat(name, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", swap)
    cli.remove_listener_record(path)
    assert path.read_bytes() == new


@pytest.mark.parametrize(
    "problem",
    ["mode", "symlink", "unsafe_directory", "uid", "regular", "stale", "iid"],
)
def test_large_record_keeps_descriptor_and_identity_refusals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    if problem == "mode":
        path.chmod(0o644)
    elif problem == "symlink":
        real = tmp_path / "real.json"
        path.rename(real)
        path.symlink_to(real)
    elif problem == "unsafe_directory":
        tmp_path.chmod(0o777)
    elif problem in ("uid", "regular"):
        fstat = os.fstat

        def foreign(fd: int) -> Any:
            st = fstat(fd)
            values = list(st)
            if problem == "uid":
                values[4] += 1
            else:
                values[0] = stat.S_IFDIR | 0o600
            return os.stat_result(values)

        monkeypatch.setattr(os, "fstat", foreign)
    with pytest.raises(cli.ListenerRecordError):
        cli.read_listener_record(
            path, iid="b" * 52 if problem == "iid" else IID, pid_alive=lambda _p: problem != "stale"
        )
    if problem == "unsafe_directory":
        tmp_path.chmod(0o700)


@pytest.mark.parametrize(
    "body,live",
    [
        (b'{"iid":"' + IID.encode() + b'"}', True),
        (b'{"padding":"' + b"x" * 20000 + b'","iid":"' + IID.encode() + b'"}', False),
    ],
)
def test_ready_read_bound_is_independent_of_large_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: bytes, live: bool
) -> None:
    path = tmp_path / "listener.json"
    _full(path)
    record = _read(path)
    caps: list[int] = []

    class Response:
        status = 200

        def read(self, size: int) -> bytes:
            caps.append(size)
            return body[:size]

    class Connection:
        sock = type("Peer", (), {"getpeercert": lambda self, **kw: b"synthetic"})()

        def __init__(self, *_a: Any, **_kw: Any) -> None:
            pass

        def connect(self) -> None:
            pass

        def request(self, *_a: Any) -> None:
            pass

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    monkeypatch.setattr(crypto, "certificate_spki", lambda _cert: b"synthetic")
    monkeypatch.setattr(crypto, "spki_fingerprint", lambda _spki: IID)
    assert cli._default_verify_listener_live(record, IID) is live
    assert caps == [16384]
    monkeypatch.setattr(crypto, "spki_fingerprint", lambda _spki: "b" * 52)
    assert cli._default_verify_listener_live(record, IID) is False
    assert caps == [16384]  # foreign pin is refused before the ready read


def test_fake_first_start_discovery_refresh_health_and_removal(
    adapter_module: Any,  # noqa: F811 - imported fixture
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    env = Env(tmp_path)
    env.bridge.served_profiles = lambda: list(PROFILES)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    monkeypatch.setattr(adapter_module.time, "time", lambda: env.clock.now)

    class FakeServer:
        def __init__(self, ctx: Any, _settings: Any, **_kw: Any) -> None:
            self.ctx = ctx
            self.bound = (TAILNET_HOST, 18920)
            self.started = False

        async def start(self) -> None:
            self.started = True

        async def stop(self, **_kw: Any) -> None:
            self.started = False

    monkeypatch.setattr(adapter_module.server, "HmpServer", FakeServer)
    adapter = adapter_module.HmpAdapter(_Config({"port": 18920}))
    c = Cli(env)
    path = cli.listener_record_path(env.custody.anchor_dir)

    async def check() -> None:
        assert not path.exists()
        assert await adapter.connect() is True
        assert adapter._server.started
        first = _read(path, env.iid)
        expected = tuple((p, reads._fallback_display_name(p)) for p in PROFILES)
        assert first.profiles == expected and len(first.health or ()) == 128
        assert c.run("setup", "check") == cli.EXIT_OK and "Served bot count: 128" in c.out
        assert c.run("health", "check") == cli.EXIT_OK
        assert c.out.count('Bot "') == 128
        context = cli._Context(c.cli_env(), env.custody, env.store)
        assert cli._served_bots(context) == list(expected)
        assert len(c.listener_live_calls) == 2
        assert c.qr.rendered == []  # discovery does not mint/grant anything
        adapter._sync_refresh(PROFILES[:1])
        assert len(_read(path, env.iid).profiles or ()) == 1
        adapter._sync_refresh(PROFILES)
        grown = _read(path, env.iid)
        assert grown.profiles == expected and len(grown.health or ()) == 128
        assert (grown.host, grown.port, grown.iid, grown.pid, grown.nonce) == (
            first.host,
            first.port,
            first.iid,
            first.pid,
            first.nonce,
        )
        env.clock.now += 15
        adapter._sync_refresh(PROFILES, refresh_health=True)
        assert _read(path, env.iid).health_checked_at == env.clock.now
        env.ctx.direct_send_flag = lambda: True
        adapter._sync_refresh(PROFILES, refresh_health=True)
        assert c.run("health", "check") == cli.EXIT_REFUSED
        assert c.out.count('Bot "') == 128
        assert all(
            row[1] in ("unsupported", "unavailable") for row in _read(path, env.iid).health or ()
        )
        before = path.read_bytes()
        adapter._sync_refresh([*PROFILES, "extra"])
        assert path.read_bytes() == before and adapter._known_profiles == expected
        assert "refresh_write_failed" in caplog.text

        def private_fault(*_a: Any, **_kw: Any) -> None:
            raise OSError("private_key_sentinel")

        monkeypatch.setattr(cli, "write_listener_record", private_fault)
        adapter._sync_refresh(PROFILES, refresh_health=True)
        assert path.read_bytes() == before
        assert "private_key_sentinel" not in caplog.text
        await adapter.disconnect()
        assert not path.exists() and adapter._profile_refresh_task is None

    with caplog.at_level(logging.INFO):
        asyncio.run(check())
