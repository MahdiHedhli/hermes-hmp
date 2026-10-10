"""Synthetic-only source tests for the host read boundary and TTY CAS handoff."""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import socket
import stat
import struct
import tempfile
import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import cli, operator_read
from hmp_plugin.contract import AuthzState
from hmp_plugin.controls_requests import (
    RequestOrigin,
    RequestRecordResult,
    RequestRecordView,
    RequestStoreResult,
)
from hmp_plugin.request_ctx import ReadWorkerBudget

RID = "a" * 32
IID = "a" * 52
NONCE = "b" * 32
GEN = "c" * 32


def _checked_operator_test_parent(value: str) -> tuple[Path, int, tuple[int, ...]]:
    """Physical current-UID0700 parent; never normalize a supplied socket literal."""
    parent = Path(value)
    if (not value or not parent.is_absolute() or value != os.path.normpath(value)
            or ".." in parent.parts or len(parent.parts) > 32
            or len(os.fsencode(parent / operator_read.SOCKET_NAME)) >= 104):
        raise ValueError("invalid operator test parent")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parent.parts[1:]:
            named = os.stat(part, dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode):
                raise ValueError("operator test parent has a non-directory ancestor")
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                held = os.fstat(child)
                if (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino):
                    raise ValueError("operator test parent changed during open")
            except BaseException:
                os.close(child)
                raise
            os.close(fd)
            fd = child
        row = os.fstat(fd)
        if row.st_uid != os.getuid() or stat.S_IMODE(row.st_mode) != 0o700:
            raise ValueError("operator test parent must be current-UID0700")
        binding = (row.st_dev, row.st_ino, row.st_uid, row.st_gid, row.st_mode)
        return parent, fd, binding
    except BaseException:
        os.close(fd)
        raise


def _operator_test_socket_absent(fd: int) -> None:
    try:
        os.stat(operator_read.SOCKET_NAME, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise AssertionError("operator test socket survived fixture cleanup")


@pytest.fixture(scope="module", autouse=True)
def _operator_test_parent_fixture():
    """Keep executor ownership; absent-env CI owns only one short temporary parent."""
    supplied = os.environ.get("HOST_OPERATOR_TEST_PARENT")
    owned = supplied is None
    # Canonicalize only the standard temporary base, never a supplied literal.
    value = (tempfile.mkdtemp(prefix="hmp-op-", dir=os.path.realpath(tempfile.gettempdir()))
             if owned else supplied)
    assert value is not None
    parent, fd, binding = _checked_operator_test_parent(value)
    try:
        _operator_test_socket_absent(fd)
        with pytest.MonkeyPatch.context() as patch:
            if owned:
                patch.setenv("HOST_OPERATOR_TEST_PARENT", value)
            # Provided environment is unchanged; a malformed value fails, never falls back.
            try:
                yield
            finally:
                current, reopened, named_binding = _checked_operator_test_parent(value)
                try:
                    held = os.fstat(fd)
                    assert current == parent and named_binding == binding
                    assert (held.st_dev, held.st_ino, held.st_uid,
                            held.st_gid, held.st_mode) == binding
                    _operator_test_socket_absent(fd)
                    if owned:
                        # Empty-only removal, through its physical retained temporary parent.
                        # Never recursively delete, unlink leftovers, or clean a supplied directory.
                        with os.scandir(fd) as entries:
                            assert next(entries, None) is None, (
                                "operator fixture has unexpected leftover"
                            )
                        base_fd = os.open(
                            parent.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        )
                        try:
                            leaf = os.stat(parent.name, dir_fd=base_fd, follow_symlinks=False)
                            assert (leaf.st_dev, leaf.st_ino, leaf.st_uid,
                                    leaf.st_gid, leaf.st_mode) == binding
                            os.rmdir(parent.name, dir_fd=base_fd)
                        finally:
                            os.close(base_fd)
                finally:
                    os.close(reopened)
    finally:
        os.close(fd)


def record() -> RequestRecordView:
    return RequestRecordView(
        RID, "11111111-1111-4111-8111-111111111111",
        RequestOrigin("d" * 32, "hmpu_" + "e" * 32, "f" * 32, IID, 1, 1),
        "primary", "jobs", "PENDING", 100, 700, 0, False, None,
        None, 0, None, True, True,
    )


def sources() -> dict[str, object]:
    return {
        "served_profiles": ["primary"], "authorized_profiles": ["primary"],
        "profile_api": {"primary": "configured"},
        "host_settings": {"jobs": "enabled", "model": "enabled"},
        "eligibility": {"jobs": ["available", None], "model": ["available", None]},
        "approval_owner_allowlisted": True,
    }


def test_closed_wire_rejects_duplicates_unknown_and_unsafe_integer() -> None:
    body = {
        "protocol": 1, "operation": "host_controls_decision_context", "request_id": RID,
        "iid": IID, "nonce": NONCE, "challenge": "0" * 32,
    }
    assert operator_read._request(
        json.dumps(body).encode(), iid=IID, nonce=NONCE,
    ) == (RID, "0" * 32)
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._request(b'{"protocol":1,"protocol":1}', iid=IID, nonce=NONCE)
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._request(json.dumps(body | {"grant": True}).encode(), iid=IID, nonce=NONCE)
    assert not operator_read._safe_ijson({"revision": 9_007_199_254_740_992})


def test_linux_peer_credentials_use_uid_never_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operator_read.sys, "platform", "linux")
    monkeypatch.setattr(operator_read.socket, "SO_PEERCRED", 17, raising=False)
    class Peer:
        def fileno(self) -> int:
            return 12
        def getsockopt(self, _level: int, _option: int, _size: int) -> bytes:
            return struct.pack("=iII", -1, 501, 20)
    assert operator_read._peer_uid(Peer()) == 501  # PID never confers authority
    class HighUid(Peer):
        def getsockopt(self, _level: int, _option: int, _size: int) -> bytes:
            return struct.pack("=iII", -1, 0xF0000001, 20)
    assert operator_read._peer_uid(HighUid()) == 0xF0000001
    class Short(Peer):
        def getsockopt(self, _level: int, _option: int, _size: int) -> bytes:
            return b"short"
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._peer_uid(Short())  # type: ignore[arg-type]


def test_current_platform_peer_credentials_on_owned_socketpair() -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        assert operator_read._peer_uid(left) == os.getuid()
        assert operator_read._peer_uid(right) == os.getuid()
    finally:
        left.close()
        right.close()


def test_parent_walk_refuses_intermediate_symlink(tmp_path: Path) -> None:
    private = Path(os.path.realpath(tmp_path)) / "private"
    private.mkdir(mode=0o700)
    fd, _st = operator_read._parent_fd(private / operator_read.SOCKET_NAME)
    os.close(fd)
    alias = Path(os.path.realpath(tmp_path)) / "alias"
    alias.symlink_to(private, target_is_directory=True)
    with pytest.raises((operator_read.OperatorUnavailableError, OSError)):
        operator_read._parent_fd(alias / operator_read.SOCKET_NAME)


def test_bind_parent_substitution_refuses_and_removes_only_own_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The disposable executor pins this one owned directory and its literal socket
    # path in the child sandbox profile. No arbitrary host AF_UNIX path is opened.
    private = Path(os.environ["HOST_OPERATOR_TEST_PARENT"])
    assert private.is_dir() and private.stat().st_mode & 0o777 == 0o700
    service = operator_read.OperatorReadService(SimpleNamespace(), private / "anchor", NONCE)
    original = operator_read.os.lstat
    seen = 0
    def swapped(path: object, *args: object, **kwargs: object) -> object:
        nonlocal seen
        row = original(path, *args, **kwargs)
        if path == private:
            seen += 1
            if seen >= 2:
                return SimpleNamespace(st_dev=row.st_dev, st_ino=row.st_ino + 1)
        return row
    monkeypatch.setattr(operator_read.os, "lstat", swapped)
    with pytest.raises(operator_read.OperatorUnavailableError):
        asyncio.run(service.start())
    assert not (private / operator_read.SOCKET_NAME).exists()


def test_worker_timeout_keeps_both_slots_charged_until_actual_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release = threading.Event(), threading.Event()
    def blocked(*_args: object) -> dict[str, object]:
        entered.set()
        release.wait(1.0)
        return {"late": True}
    monkeypatch.setattr(operator_read, "_collect", blocked)
    monkeypatch.setattr(operator_read, "DEADLINE_S", 0.01)
    budget = ReadWorkerBudget()
    ctx = SimpleNamespace(read_worker_budget=budget, readiness_generation=GEN)
    service = operator_read.OperatorReadService(ctx, "/private/tmp/synthetic", NONCE)
    async def scenario() -> None:
        with pytest.raises(operator_read.OperatorUnavailableError):
            await service._context(RID, "0" * 32)
        assert entered.is_set()
        assert (budget.active, budget.operator) == (1, 1)
        assert await service.stop() == 1  # listener generation ended with a live read
        fresh_ctx = SimpleNamespace(read_worker_budget=budget, readiness_generation="d" * 32)
        fresh = operator_read.OperatorReadService(fresh_ctx, "/private/tmp/synthetic", NONCE)
        for _ in range(3):
            assert budget.reserve(operator=False)
        with pytest.raises(operator_read.OperatorUnavailableError):
            await fresh._context(RID, "0" * 32)  # reconnect cannot reset the old debt
        for _ in range(3):
            budget.release(operator=False)
        release.set()
        await asyncio.wait_for(service.wait_drained(), 1.0)
        assert (budget.active, budget.operator) == (0, 0)
        assert await fresh._context(RID, "1" * 32) == {"late": True}
    asyncio.run(scenario())


def test_collect_uses_only_host_record_and_rejects_changed_bot_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hmp_plugin import server
    first = record()
    calls: list[str] = []
    class Requests:
        def __init__(self, _store: object) -> None:
            pass
        def host_record(self, *_args: object, **_kwargs: object) -> RequestRecordResult:
            calls.append("host_record")
            return RequestRecordResult("ok", first)
        def decide(self, *_args: object, **_kwargs: object) -> None:
            pytest.fail("read endpoint must never grant Controls")
    class Bridge:
        changed = False
        def served_profiles(self) -> list[str]:
            return ["primary", "second"] if self.changed else ["primary"]
        def authz_state(self, _user: str, _profile: str) -> AuthzState:
            return AuthzState.AUTHORIZED
        def readiness_profile_api_state(self, _profile: str, *, checkpoint: object) -> str:
            checkpoint()  # type: ignore[operator]
            return "configured"
    bridge = Bridge()
    ctx = SimpleNamespace(
        identity=SimpleNamespace(still_current=lambda: True),
        readiness_generation=GEN, bridge=bridge, store=object(),
        now=lambda: 100, iid=IID,
        readiness_owner_device_ids=lambda: frozenset({first.origin.device_id}),
    )
    monkeypatch.setattr(operator_read, "ControlsRequestStore", Requests)
    monkeypatch.setattr(server, "_readiness_feature_statuses", lambda _ctx: {
        "jobs": ("available", None), "model": ("available", None),
    })
    monkeypatch.setattr(server, "_readiness_host_settings", lambda _ctx: {
        "jobs": "enabled", "model": "enabled",
    })
    good = operator_read._collect(ctx, RID, "0" * 32, NONCE, GEN, time.monotonic() + 2)
    assert good["sources"] == sources()
    assert calls == ["host_record", "host_record"]
    original = bridge.served_profiles
    count = 0
    def drifting() -> list[str]:
        nonlocal count
        count += 1
        bridge.changed = count >= 2
        return original()
    bridge.served_profiles = drifting  # type: ignore[method-assign]
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._collect(ctx, RID, "1" * 32, NONCE, GEN, time.monotonic() + 2)


def test_allow_uses_two_distinct_contexts_one_cas_and_committed_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = record()
    granted = replace(
        first, state="GRANTED", decision_revision=1,
        current_controls_revision=1, current_controls_allowed=1,
    )
    class Requests:
        def __init__(self) -> None:
            self.calls: list[tuple[bool, bool]] = []
        def host_record(self, *_args: object, **_kwargs: object) -> RequestRecordResult:
            return RequestRecordResult("ok", first)
        def decide(self, *_args: object, allow: bool, precommit_external_verified: bool,
                   **_kwargs: object) -> RequestStoreResult:
            self.calls.append((allow, precommit_external_verified))
            return RequestStoreResult("committed_needs_effective_readback", RID, "GRANTED", 700, 1)
        def host_decision_readback(self, *_args: object, **_kwargs: object) -> RequestRecordResult:
            return RequestRecordResult("committed", granted)
    requests = Requests()
    responses = [
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(granted), "sources": sources(), "generation": GEN},
    ]
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (requests, first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: responses.pop(0))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    ctx = SimpleNamespace(out=io.StringIO(), now=lambda: 100, env=SimpleNamespace())
    assert cli._cmd_controls_requests(
        ctx, argparse.Namespace(controls_requests_command="allow", request_id=RID),
    ) == cli.EXIT_OK
    assert requests.calls == [(True, True)]
    assert responses == []


def test_allow_changed_bot_set_refuses_before_store_write(monkeypatch: pytest.MonkeyPatch) -> None:
    first = record()
    class Requests:
        def host_record(self, *_args: object, **_kwargs: object) -> RequestRecordResult:
            return RequestRecordResult("ok", first)
        def decide(self, *_args: object, **_kwargs: object) -> None:
            pytest.fail("grant after a changed live bot set")
    responses = [
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(first), "sources": sources() | {"served_profiles": ["other", "primary"]},
         "generation": GEN},
    ]
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: responses.pop(0))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    ctx = SimpleNamespace(out=io.StringIO(), now=lambda: 100, env=SimpleNamespace())
    with pytest.raises(cli.RefusedError):
        cli._cmd_controls_requests(
            ctx, argparse.Namespace(controls_requests_command="allow", request_id=RID),
        )


def test_darwin_peer_uid_is_required_and_failure_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operator_read.sys, "platform", "darwin")
    class Call:
        argtypes: object = None
        restype: object = None
        result = 0
        peer_uid = 501
        def __call__(self, _fd: int, uid: object, gid: object) -> int:
            uid._obj.value = self.peer_uid  # type: ignore[attr-defined]
            gid._obj.value = 20  # type: ignore[attr-defined]
            return self.result
    call = Call()
    monkeypatch.setattr(
        operator_read.ctypes, "CDLL", lambda *_a, **_k: SimpleNamespace(getpeereid=call),
    )
    peer = SimpleNamespace(fileno=lambda: 9)
    assert operator_read._peer_uid(peer) == 501  # type: ignore[arg-type]
    call.peer_uid = 0xF0000001
    assert operator_read._peer_uid(peer) == 0xF0000001  # type: ignore[arg-type]
    call.result = -1
    with pytest.raises(operator_read.OperatorUnavailableError):
        operator_read._peer_uid(peer)  # type: ignore[arg-type]


def test_budget_operator_subcap_and_old_store_close_waits_for_actual_drain() -> None:
    from hmp_plugin import adapter
    budget = ReadWorkerBudget()
    assert budget.reserve(operator=True)
    assert budget.reserve(operator=True)
    assert not budget.reserve(operator=True)
    assert budget.reserve(operator=False)
    assert budget.reserve(operator=False)
    assert not budget.reserve(operator=False)
    for operator in (False, False, True, True):
        budget.release(operator=operator)
    closed: list[str] = []
    event = asyncio.Event()
    store = SimpleNamespace(close=lambda: closed.append("store"))
    srv = SimpleNamespace(ctx=SimpleNamespace(store=store), wait_operator_drain=event.wait)
    self = SimpleNamespace(_close_generation=lambda _ctx: closed.append("generation"))
    async def scenario() -> None:
        task = asyncio.create_task(adapter.HmpAdapter._close_after_operator_drain(self, srv))
        await asyncio.sleep(0)
        assert closed == []
        event.set()
        await task
        assert closed == ["generation", "store"]
    asyncio.run(scenario())


def test_bounded_closed_response_refuses_extra_keys_duplicate_and_oversize() -> None:
    keys = frozenset({"protocol", "record"})
    assert operator_read._closed_json(b'{"protocol":1,"record":null}', keys) == {
        "protocol": 1, "record": None,
    }
    for raw in (b'{"protocol":1,"protocol":1,"record":null}',
                b'{"protocol":1,"record":null,"grant":true}',
                b'{"protocol":NaN,"record":null}'):
        with pytest.raises(operator_read.OperatorUnavailableError):
            operator_read._closed_json(raw, keys)
    assert not operator_read._safe_ijson({"rows": [None] * 65})
    assert not operator_read._safe_ijson({"revision": 9_007_199_254_740_992})


def _tty_ctx() -> SimpleNamespace:
    return SimpleNamespace(out=io.StringIO(), now=lambda: 100, env=SimpleNamespace())


def _request_args(action: str) -> argparse.Namespace:
    return argparse.Namespace(controls_requests_command=action, request_id=RID)


def test_deny_only_changes_request_and_keeps_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    first = record()
    denied = replace(first, state="DENIED")
    calls: list[tuple[bool, bool]] = []
    class Requests:
        reads = 0
        def host_record(self, *_a: object, **_k: object) -> RequestRecordResult:
            self.reads += 1
            return RequestRecordResult("ok", denied if self.reads == 2 else first)
        def decide(self, *_a: object, allow: bool, precommit_external_verified: bool,
                   **_k: object) -> RequestStoreResult:
            calls.append((allow, precommit_external_verified))
            return RequestStoreResult("denied", RID, "DENIED", 700, None)
    requests = Requests()
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (requests, first, IID))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    assert cli._cmd_controls_requests(_tty_ctx(), _request_args("deny")) == cli.EXIT_OK
    assert calls == [(False, False)] and requests.reads == 2
    assert denied.current_controls_revision == first.current_controls_revision
    assert denied.current_controls_allowed == first.current_controls_allowed


@pytest.mark.parametrize("state", ["EXPIRED", "REVOKED", "CONFLICT", "GRANTED", "DENIED"])
def test_terminal_request_cannot_be_decided(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    first = replace(record(), state=state)
    class Requests:
        def decide(self, *_a: object, **_k: object) -> None:
            pytest.fail("terminal request must never cause another decision")
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(
        cli, "_host_request_confirmation", lambda *_a: pytest.fail("prompted terminal request"),
    )
    for action in ("allow", "deny"):
        with pytest.raises(cli.RefusedError):
            cli._cmd_controls_requests(_tty_ctx(), _request_args(action))


@pytest.mark.parametrize("action", ["allow", "deny"])
def test_cancelled_confirmation_never_decides(monkeypatch: pytest.MonkeyPatch, action: str) -> None:
    first = record()
    class Requests:
        def decide(self, *_a: object, **_k: object) -> None:
            pytest.fail("cancelled decision must not commit")
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: {
        "record": asdict(first), "sources": sources(), "generation": GEN,
    })
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: False)
    with pytest.raises(cli.RefusedError):
        cli._cmd_controls_requests(_tty_ctx(), _request_args(action))


@pytest.mark.parametrize("drift", ["epoch", "device", "controls", "expiry", "revoke"])
def test_allow_current_store_drift_refuses_before_cas(
    monkeypatch: pytest.MonkeyPatch, drift: str,
) -> None:
    first = record()
    changes = {
        "epoch": replace(first, origin=replace(first.origin, instance_epoch=2)),
        "device": replace(first, origin=replace(first.origin, device_id="f" * 32)),
        "controls": replace(first, current_controls_revision=1),
        "expiry": replace(first, state="EXPIRED"),
        "revoke": replace(first, state="REVOKED"),
    }
    class Requests:
        def host_record(self, *_a: object, **_k: object) -> RequestRecordResult:
            return RequestRecordResult("ok", changes[drift])
        def decide(self, *_a: object, **_k: object) -> None:
            pytest.fail("stale request must never commit")
    responses = [
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(first), "sources": sources(), "generation": GEN},
    ]
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: responses.pop(0))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    with pytest.raises(cli.RefusedError):
        cli._cmd_controls_requests(_tty_ctx(), _request_args("allow"))
    assert len(responses) == 1  # no second live read after Store currency already failed


@pytest.mark.parametrize("change", ["generation", "profile", "api", "flags"])
def test_allow_live_source_drift_refuses_before_cas(
    monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    first = record()
    class Requests:
        def host_record(self, *_a: object, **_k: object) -> RequestRecordResult:
            return RequestRecordResult("ok", first)
        def decide(self, *_a: object, **_k: object) -> None:
            pytest.fail("changed live source must never commit")
    changed_sources = sources()
    if change == "profile":
        changed_sources["authorized_profiles"] = ["other"]
    if change == "api":
        changed_sources["profile_api"] = {"primary": "missing"}
    if change == "flags":
        changed_sources["host_settings"] = {"jobs": "disabled", "model": "enabled"}
    responses = [
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(first), "sources": changed_sources,
         "generation": "d" * 32 if change == "generation" else GEN},
    ]
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: responses.pop(0))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    with pytest.raises(cli.RefusedError):
        cli._cmd_controls_requests(_tty_ctx(), _request_args("allow"))
    assert responses == []


def test_unknown_postcommit_outcome_never_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    first = record()
    calls: list[str] = []
    class Requests:
        def host_record(self, *_a: object, **_k: object) -> RequestRecordResult:
            return RequestRecordResult("ok", first)
        def decide(self, *_a: object, **_k: object) -> RequestStoreResult:
            calls.append("decide")
            return RequestStoreResult("unknown_commit", RID, "PENDING", 700, None)
        def host_decision_readback(self, *_a: object, **_k: object) -> None:
            pytest.fail("unknown commit is not a positive readback")
    responses = [
        {"record": asdict(first), "sources": sources(), "generation": GEN},
        {"record": asdict(first), "sources": sources(), "generation": GEN},
    ]
    monkeypatch.setattr(cli, "_host_request_current", lambda *_a: (Requests(), first, IID))
    monkeypatch.setattr(cli, "_host_operator_context", lambda *_a: responses.pop(0))
    monkeypatch.setattr(cli, "_host_request_confirmation", lambda *_a: True)
    with pytest.raises(cli.RefusedError, match="outcome unknown"):
        cli._cmd_controls_requests(_tty_ctx(), _request_args("allow"))
    assert calls == ["decide"] and responses == []


def _owned_operator_parent() -> Path:
    parent = Path(os.environ["HOST_OPERATOR_TEST_PARENT"])
    assert parent.is_dir() and parent.stat().st_mode & 0o777 == 0o700
    return parent


def _fixed_reply(request_id: str, challenge: str, nonce: str) -> dict[str, object]:
    now = int(time.monotonic() * 1_000)
    return {
        "protocol": 1, "operation": "host_controls_decision_context",
        "request_id": request_id, "challenge": challenge, "iid": IID,
        "nonce": nonce, "generation": GEN, "record": asdict(record()),
        "sources": sources(), "sample_ms": now, "expires_ms": now + 1_500,
    }


def test_owned_unix_service_client_roundtrip_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _owned_operator_parent()
    calls: list[str] = []
    def collect(_ctx: object, request_id: str, challenge: str, nonce: str,
                _generation: str, _deadline: float) -> dict[str, object]:
        calls.append(request_id)
        return _fixed_reply(request_id, challenge, nonce)
    monkeypatch.setattr(operator_read, "_collect", collect)
    ctx = SimpleNamespace(read_worker_budget=ReadWorkerBudget(), readiness_generation=GEN, iid=IID)
    service = operator_read.OperatorReadService(ctx, parent / "anchor", NONCE)
    async def scenario() -> None:
        await service.start()
        try:
            answer = await asyncio.to_thread(
                operator_read.read_context, service.path,
                iid=IID, nonce=NONCE, request_id=RID,
            )
            assert answer["record"] == asdict(record())
            assert answer["sources"] == sources()
            assert calls == [RID]
        finally:
            assert await service.stop() == 0
        assert not service.path.exists()
        assert (ctx.read_worker_budget.active, ctx.read_worker_budget.operator) == (0, 0)
    asyncio.run(scenario())


def test_owned_unix_wrong_peer_and_oversize_request_never_call_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _owned_operator_parent()
    calls: list[str] = []
    monkeypatch.setattr(operator_read, "_collect", lambda *_a: calls.append("collect"))
    ctx = SimpleNamespace(read_worker_budget=ReadWorkerBudget(), readiness_generation=GEN, iid=IID)
    service = operator_read.OperatorReadService(ctx, parent / "anchor", NONCE)
    def probe(raw: bytes) -> bytes:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.5)
            client.connect(str(service.path))
            client.sendall(raw)
            return client.recv(1024)
    async def scenario() -> None:
        await service.start()
        real_peer = operator_read._peer_uid
        try:
            monkeypatch.setattr(operator_read, "_peer_uid", lambda _sock: os.getuid() + 1)
            request = json.dumps({
                "protocol": 1, "operation": "host_controls_decision_context",
                "request_id": RID, "iid": IID, "nonce": NONCE, "challenge": "0" * 32,
            }).encode() + b"\n"
            assert await asyncio.to_thread(probe, request) == b""
            monkeypatch.setattr(operator_read, "_peer_uid", real_peer)
            assert await asyncio.to_thread(probe, b"x" * 600 + b"\n") == b""
            assert calls == []
        finally:
            monkeypatch.setattr(operator_read, "_peer_uid", real_peer)
            assert await service.stop() == 0
        assert not service.path.exists()
    asyncio.run(scenario())


def test_owned_unix_timeout_retains_debt_until_callback_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _owned_operator_parent()
    entered, release, returned = threading.Event(), threading.Event(), threading.Event()
    def blocked(_ctx: object, request_id: str, challenge: str, nonce: str,
                _generation: str, _deadline: float) -> dict[str, object]:
        entered.set()
        try:
            assert release.wait(10.0), "fixture callback release was not observed"
        finally:
            returned.set()
        return _fixed_reply(request_id, challenge, nonce)
    monkeypatch.setattr(operator_read, "_collect", blocked)
    monkeypatch.setattr(operator_read, "DEADLINE_S", 0.2)
    budget = ReadWorkerBudget()
    ctx = SimpleNamespace(read_worker_budget=budget, readiness_generation=GEN, iid=IID)
    service = operator_read.OperatorReadService(ctx, parent / "anchor", NONCE)
    async def scenario() -> None:
        started = False
        client: asyncio.Task[dict[str, object]] | None = None
        try:
            await service.start()
            started = True
            client = asyncio.create_task(asyncio.to_thread(
                operator_read.read_context, service.path,
                iid=IID, nonce=NONCE, request_id=RID,
            ))
            # Wait for the actual synchronous callback to enter before examining
            # timeout debt. A scheduler delay alone is not evidence of a live read.
            assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 0.6), 0.8)
            with pytest.raises(operator_read.OperatorUnavailableError):
                await asyncio.wait_for(asyncio.shield(client), 0.8)
            assert not returned.is_set()
            assert (budget.active, budget.operator) == (1, 1)
            assert await asyncio.wait_for(service.stop(), 1.0) == 1
            assert not returned.is_set()
            assert (budget.active, budget.operator) == (1, 1)
        finally:
            release.set()
            cleanup_errors: list[Exception] = []
            if started:
                # Idempotent stop is required even when an earlier assertion or
                # wait failed; no listener or socket survives a failed fixture.
                try:
                    await asyncio.wait_for(service.stop(), 3.0)
                except Exception as exc:
                    cleanup_errors.append(exc)
            if client is not None:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(asyncio.gather(client, return_exceptions=True)), 3.0,
                    )
                except Exception as exc:
                    cleanup_errors.append(exc)
            if started:
                try:
                    await asyncio.wait_for(service.wait_drained(), 1.0)
                except Exception as exc:
                    cleanup_errors.append(exc)
            assert (budget.active, budget.operator) == (0, 0)
            assert returned.is_set()
            assert not service.path.exists()
            assert cleanup_errors == []
    asyncio.run(scenario())
