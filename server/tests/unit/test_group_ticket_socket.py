"""Real private synthetic Unix peers plus explicit faults; no native host/ticket."""

from __future__ import annotations

import asyncio
import json
import os
import struct
import sys
import tempfile
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import group_ticket_socket as module
from hmp_plugin.group_ticket_socket import GroupTicketSocketError, GroupTicketSocketRegistry

PROFILE, INSTANCE = "/synthetic/profile", "synthetic-instance"
TICKET = "SYNTHETIC_SOCKET_ONLY_" + "x" * 24


def reply(**changes):
    result = {
        "ticket": TICKET,
        "expires_in_seconds": 30,
        "instance_id": INSTANCE,
        "profile_id": PROFILE,
        "runtime_protocol": 1,
    }
    result.update(changes)
    return json.dumps({"protocol": 1, "id": 1, "ok": True, "result": result}).encode() + b"\n"


@asynccontextmanager
async def peer(*, response=None, gated=False):
    requests, tasks = [], []
    requested, release = asyncio.Event(), asyncio.Event()
    with tempfile.TemporaryDirectory(prefix="hgs-", dir="/tmp") as directory:
        os.chmod(directory, 0o700)
        path = str(Path(directory) / "control.sock")

        async def handle(reader, writer):
            tasks.append(asyncio.current_task())
            try:
                raw = await reader.readline()
                requests.append(raw)
                requested.set()
                if gated:
                    await release.wait()
                if response is not None:
                    writer.write(response)
                    await writer.drain()
            except (ConnectionError, asyncio.IncompleteReadError):
                pass
            finally:
                writer.close()
                with suppress(ConnectionError):
                    await writer.wait_closed()

        server = await asyncio.start_unix_server(handle, path=path)
        os.chmod(path, 0o600)
        try:
            yield SimpleNamespace(
                path=path, requests=requests, tasks=tasks, requested=requested, release=release
            )
        finally:
            release.set()
            server.close()
            await server.wait_closed()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            if tasks:
                await asyncio.gather(*tasks)
            assert all(task.done() for task in tasks)


def prepare(registry, path, **changes):
    values = {
        "socket_path": path,
        "expected_peer_pid": os.getpid(),
        "profile_id": PROFILE,
        "instance_id": INSTANCE,
        "max_seconds": 5,
        "deadline": asyncio.get_running_loop().time() + 2,
    }
    values.update(changes)
    return registry.prepare(**values)


def test_actual_kernel_peer_uid_fixed_request_and_known_close():
    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=2)
            original_deadline = asyncio.get_running_loop().time() + 2
            owner = prepare(registry, target.path, deadline=original_deadline)
            grant = await owner.exchange(deadline=original_deadline)
            assert grant.ticket == TICKET
            assert TICKET not in repr(grant)
            snapshot = owner.snapshot()
            assert snapshot.same_uid_observed and snapshot.expected_pid_observed
            assert snapshot.socket_close_known
            assert snapshot.exchange_cleanup_finished and not snapshot.registry_slot_retained
            assert registry.snapshot().registered == 0
            assert len(target.requests) == 1
            assert json.loads(target.requests[0])["params"] == {
                "profile_id": PROFILE,
                "instance_id": INSTANCE,
                "purpose": "interactive",
                "scope": "profile",
                "restart_wait": "refuse",
            }
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "already_attempted"
            assert await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize("uid", [None, True, -1])
def test_peer_identity_refusal_before_send(monkeypatch, uid):
    monkeypatch.setattr(module, "_peer_identity", lambda _peer: (uid, os.getpid()))

    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == (
                "unsupported_peer" if type(uid) is not int else "peer_refused"
            )
            assert not error.value.mint_may_have_occurred
            assert owner.snapshot().socket_close_known
            assert not owner.snapshot().send_may_have_occurred
            assert await registry.drain()
        assert all(not request for request in target.requests)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "response",
    [
        b"",
        b"{}",
        b"\xff\n",
        reply(instance_id="foreign"),
        b'{"ok":false,"error":"PRIVATE_NATIVE_DIAGNOSTIC"}\n',
        b" " * 65_536 + reply(),
    ],
)
def test_response_refusals_close_once_without_raw_diagnostics(response):
    async def scenario():
        async with peer(response=response) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "invalid_reply"
            assert error.value.mint_may_have_occurred
            assert "PRIVATE_NATIVE_DIAGNOSTIC" not in str(error.value)
            assert target.path not in str(error.value)
            assert error.value.__context__ is None and error.value.__cause__ is None
            assert owner.snapshot().socket_close_known
            assert await registry.drain()

    asyncio.run(scenario())


def test_one_absolute_deadline_and_timeout_keeps_one_shot():
    async def scenario():
        async with peer(response=reply(), gated=True) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(
                registry, target.path, deadline=asyncio.get_running_loop().time() + 0.08
            )
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "expired"
            assert owner.snapshot().socket_close_known
            with pytest.raises(GroupTicketSocketError) as second:
                await owner.exchange()
            assert second.value.reason == "already_attempted"
            assert await registry.drain()

    asyncio.run(scenario())


def test_retire_before_start_never_constructs_socket(monkeypatch):
    calls = []

    def forbidden():
        calls.append(True)
        raise AssertionError("unexpected socket")

    monkeypatch.setattr(module, "_create_socket", forbidden)

    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=1)
        owner = prepare(registry, "/synthetic/control.sock")
        registry.retire()
        with pytest.raises(GroupTicketSocketError):
            await owner.exchange()
        assert not owner.snapshot().attempted
        assert owner.snapshot().socket_close_known and await registry.drain()

    asyncio.run(scenario())
    assert not calls


def test_retirement_fences_late_reply_and_observer_cancel_does_not_cancel_exchange():
    async def scenario():
        async with peer(response=reply(), gated=True) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            task = asyncio.create_task(owner.exchange())
            try:
                await asyncio.wait_for(target.requested.wait(), timeout=1)
                observer = asyncio.create_task(registry.drain())
                await asyncio.sleep(0)
                observer.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await observer
                assert not owner._done.cancelled() and not task.done()
                target.release.set()
                with pytest.raises(GroupTicketSocketError) as error:
                    await task
                assert error.value.reason == "retired"
                assert await registry.drain()
            finally:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    asyncio.run(scenario())


def test_actual_exchange_cancellation_preserved_and_socket_closed():
    async def scenario():
        async with peer(response=reply(), gated=True) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            task = asyncio.create_task(owner.exchange())
            await asyncio.wait_for(target.requested.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert task.cancelled() and owner.snapshot().socket_close_known
            assert await registry.drain()

    asyncio.run(scenario())


def test_unknown_construction_preserves_binding_and_shared_capacity(monkeypatch):
    calls = []

    def unknown():
        calls.append(True)
        raise OSError("SIMULATED_CONSTRUCTOR_FAILURE")

    monkeypatch.setattr(module, "_create_socket", unknown)

    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=1)
        owner = prepare(registry, "/synthetic/control.sock")
        with pytest.raises(GroupTicketSocketError) as error:
            await owner.exchange()
        assert error.value.reason == "creation_unknown"
        assert not owner.snapshot().socket_close_known and owner.snapshot().registry_slot_retained
        for changes in [{}, {"instance_id": "replacement"}, {"profile_id": "/synthetic/other"}]:
            with pytest.raises(GroupTicketSocketError) as busy:
                prepare(registry, "/synthetic/control.sock", **changes)
            assert busy.value.reason == "busy"
        assert not await registry.drain()
        assert not await registry.drain()

    asyncio.run(scenario())
    assert len(calls) == 1


class CloseFault:
    def __init__(self, peer, *, fail=False, delay=0, retire=None):
        self.peer, self.fail, self.delay, self.retire = peer, fail, delay, retire
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.peer, name)

    def close(self):
        self.calls += 1
        self.peer.close()
        if self.retire is not None:
            self.retire()
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise OSError("SIMULATED_AFTER_REAL_CLOSE")


def test_unknown_close_is_never_retried_and_keeps_original_slot(monkeypatch):
    original = module._create_socket
    wrappers = []

    def wrapped():
        value = CloseFault(original(), fail=True)
        wrappers.append(value)
        return value

    monkeypatch.setattr(module, "_create_socket", wrapped)

    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=2)
            owner = prepare(registry, target.path)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "close_unknown"
            assert owner.snapshot().registry_slot_retained and registry.snapshot().registered == 1
            with pytest.raises(GroupTicketSocketError):
                prepare(registry, target.path)
            replacement = prepare(registry, target.path, instance_id="replacement")
            assert registry.snapshot().registered == 2
            replacement.retire()
            assert registry.snapshot().registered == 1
            assert not await registry.drain()
            assert not await registry.drain()

    asyncio.run(scenario())
    assert len(wrappers) == 1 and wrappers[0].calls == 1


@pytest.mark.parametrize("mode", ["deadline", "retire"])
def test_no_grant_until_close_and_final_fence(monkeypatch, mode):
    original = module._create_socket
    original_parse = module.parse_group_ticket_reply
    parsed = []

    def observed_parse(*args, **kwargs):
        value = original_parse(*args, **kwargs)
        parsed.append(True)
        return value

    monkeypatch.setattr(module, "parse_group_ticket_reply", observed_parse)

    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=1)

            def wrapped():
                return CloseFault(
                    original(),
                    delay=1.1 if mode == "deadline" else 0,
                    retire=registry.retire if mode == "retire" else None,
                )

            monkeypatch.setattr(module, "_create_socket", wrapped)
            owner = prepare(
                registry,
                target.path,
                deadline=asyncio.get_running_loop().time() + (1 if mode == "deadline" else 2),
            )
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == ("expired" if mode == "deadline" else "retired")
            assert parsed == [True]
            assert owner.snapshot().socket_close_known and await registry.drain()

    asyncio.run(scenario())


def test_self_drain_refused_without_deadlock(monkeypatch):
    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)

            async def bad_reader(_deadline):
                await registry.drain()
                raise AssertionError("self drain returned")

            monkeypatch.setattr(owner, "_read_line", bad_reader)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "self_drain"
            assert owner.snapshot().socket_close_known and await registry.drain()

    asyncio.run(scenario())


def test_cancelled_completion_future_is_not_settlement():
    async def scenario():
        async with peer(response=reply(), gated=True) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            task = asyncio.create_task(owner.exchange())
            await asyncio.wait_for(target.requested.wait(), timeout=1)
            owner._done.cancel()  # Explicit fault injection, not a public observer API.
            assert not await registry.drain()
            target.release.set()
            with pytest.raises(GroupTicketSocketError):
                await task
            assert owner.snapshot().socket_close_known and owner.snapshot().registry_slot_retained
            assert not await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize("capacity", [True, 0, -1, 17, 1.0, "1", None])
def test_capacity_types_are_exact_and_bounded(capacity):
    async def scenario():
        with pytest.raises(GroupTicketSocketError):
            GroupTicketSocketRegistry(capacity=capacity)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "field,bad",
    [
        ("socket_path", "relative"),
        ("socket_path", "/a/../b"),
        ("socket_path", "/" + "x" * 101),
        ("socket_path", "/\ud800"),
        ("socket_path", "/x\x00"),
        ("profile_id", None),
        ("instance_id", True),
        ("max_seconds", float("inf")),
        ("max_seconds", True),
        ("max_seconds", 31),
    ],
)
def test_binding_validation_does_not_create_socket(field, bad):
    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=1)
        with pytest.raises(GroupTicketSocketError):
            prepare(registry, "/synthetic/control.sock", **{field: bad})
        assert registry.snapshot().registered == 0
        assert await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "deadline", [True, float("nan"), float("inf"), -1, 10**400, (1 << 53) + 1, 0]
)
def test_invalid_or_expired_deadline_does_not_construct(deadline, monkeypatch):
    calls = []

    def forbidden():
        calls.append(True)
        raise AssertionError("unexpected creation")

    monkeypatch.setattr(module, "_create_socket", forbidden)

    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=1)
        owner = prepare(registry, "/synthetic/control.sock")
        with pytest.raises(GroupTicketSocketError):
            await owner.exchange(deadline=deadline)
        assert owner.snapshot().socket_close_known and await registry.drain()

    asyncio.run(scenario())
    assert not calls


def test_wrong_loop_and_constructor_without_loop_refuse():
    with pytest.raises(GroupTicketSocketError):
        GroupTicketSocketRegistry(capacity=1)

    async def scenario():
        value = GroupTicketSocketRegistry(capacity=1)
        value.retire()
        return value

    registry = asyncio.run(scenario())
    with pytest.raises(GroupTicketSocketError) as error:
        registry.snapshot()
    assert error.value.reason == "wrong_loop"


class DeleteFault(dict):
    def __delitem__(self, key):
        raise RuntimeError("SIMULATED_REGISTRY_REMOVAL_FAILURE")


def test_registry_removal_prefix_retains_actual_owner_and_blocks_replacement(monkeypatch):
    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=2)
            owner = prepare(registry, target.path)
            registry._bindings = DeleteFault(registry._bindings)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "completion_unknown"
            assert registry._settlement_unknown is owner
            assert owner.snapshot().socket_close_known and owner.snapshot().registry_slot_retained
            with pytest.raises(GroupTicketSocketError) as busy:
                prepare(registry, target.path, instance_id="replacement")
            assert busy.value.reason == "busy"
            assert not await registry.drain()

    asyncio.run(scenario())


def test_exceptional_completion_future_is_not_settlement():
    async def scenario():
        async with peer(response=reply(), gated=True) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            task = asyncio.create_task(owner.exchange())
            await asyncio.wait_for(target.requested.wait(), timeout=1)
            owner._done.set_exception(RuntimeError("SIMULATED_COMPLETION_FAILURE"))
            assert not await registry.drain()
            target.release.set()
            with pytest.raises(GroupTicketSocketError) as error:
                await task
            assert error.value.reason == "completion_unknown"
            assert owner.snapshot().socket_close_known and owner.snapshot().registry_slot_retained
            assert not await registry.drain()

    asyncio.run(scenario())


def test_held_queue_cannot_renew_bound_deadline_before_any_socket(monkeypatch):
    calls = []

    def forbidden():
        calls.append(True)
        raise AssertionError("queued expiry must precede construction")

    monkeypatch.setattr(module, "_create_socket", forbidden)

    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=2)
        end = asyncio.get_running_loop().time() + 0.03
        expired = prepare(registry, "/synthetic/control.sock", deadline=end)
        renewed = prepare(
            registry, "/synthetic/control.sock", profile_id="/synthetic/other", deadline=end
        )
        await asyncio.sleep(0.06)
        with pytest.raises(GroupTicketSocketError) as first:
            await expired.exchange()
        assert first.value.reason == "expired"
        with pytest.raises(GroupTicketSocketError) as second:
            await renewed.exchange(deadline=asyncio.get_running_loop().time() + 1)
        assert second.value.reason == "invalid_deadline"
        assert expired.snapshot().socket_close_known and renewed.snapshot().socket_close_known
        assert not calls and await registry.drain()

    asyncio.run(scenario())


def test_multiple_lines_in_acquired_reply_are_refused_without_stream_boundary_assumption(
    monkeypatch,
):
    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            original = owner._read_line

            async def extra_line(end):
                raw = await original(end)
                return raw + reply()  # Explicit acquired-buffer fault, not a stream packet claim.

            monkeypatch.setattr(owner, "_read_line", extra_line)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "invalid_reply"
            assert owner.snapshot().socket_close_known and await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize("uid", [0, 1000, (1 << 31) + 7, (1 << 32) - 1])
def test_linux_ucred_unsigned_abi_simulation(uid):
    # Pure ABI data only. No OS/constant spoofing and no Linux runtime claim on Darwin.
    assert module._linux_peer_uid(struct.pack("3I", 123, uid, 456)) == uid


@pytest.mark.parametrize("pid", [None, True, 0, -1, 2_147_483_648, 1.0, "123"])
def test_expected_pid_refused_before_registration(pid):
    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=1)
        with pytest.raises(GroupTicketSocketError) as error:
            prepare(registry, "/synthetic/control.sock", expected_peer_pid=pid)
        assert error.value.reason == "invalid_binding"
        assert registry.snapshot().registered == 0
        assert await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "identity", [None, (), (1,), (1, 2, 3), (os.getuid(), True), (os.getuid(), 0)]
)
def test_unknown_peer_process_refuses_before_send(monkeypatch, identity):
    monkeypatch.setattr(module, "_peer_identity", lambda _peer: identity)

    async def scenario():
        async with peer(response=reply()) as target:
            registry = GroupTicketSocketRegistry(capacity=1)
            owner = prepare(registry, target.path)
            with pytest.raises(GroupTicketSocketError) as error:
                await owner.exchange()
            assert error.value.reason == "unsupported_peer"
            assert not error.value.mint_may_have_occurred
            assert not owner.snapshot().expected_pid_observed
            assert await registry.drain()
        assert all(not request for request in target.requests)

    asyncio.run(scenario())


def test_different_pid_does_not_open_second_binding_slot():
    async def scenario():
        registry = GroupTicketSocketRegistry(capacity=2)
        prepare(registry, "/synthetic/control.sock")
        with pytest.raises(GroupTicketSocketError) as error:
            prepare(registry, "/synthetic/control.sock", expected_peer_pid=os.getpid() + 1)
        assert error.value.reason == "busy"
        assert registry.snapshot().registered == 1
        assert await registry.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize("correct_pid", [False, True])
def test_actual_same_uid_child_process_is_checked_before_send(correct_pid):
    # A distinct real process defeats an implementation that checks only UID or
    # compares the expected number with our own PID instead of the kernel peer.
    script = """
import os, socket, sys
listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
listener.settimeout(3)
listener.bind(sys.argv[1])
os.chmod(sys.argv[1], 0o600)
listener.listen(1)
print('READY', flush=True)
try:
    connection, _ = listener.accept()
    connection.settimeout(3)
    with connection:
        request = b''
        while len(request) < 4096 and not request.endswith(b'\\n'):
            chunk = connection.recv(4096 - len(request))
            if not chunk:
                break
            request += chunk
        if request:
            connection.sendall(sys.argv[2].encode('utf-8'))
        print(len(request), flush=True)
finally:
    listener.close()
"""

    async def scenario():
        with tempfile.TemporaryDirectory(prefix="hgp-", dir="/tmp") as directory:
            os.chmod(directory, 0o700)
            path = str(Path(directory) / "control.sock")
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                "-c",
                script,
                path,
                reply().decode("utf-8"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                assert process.pid != os.getpid()
                assert await asyncio.wait_for(process.stdout.readline(), 2) == b"READY\n"
                registry = GroupTicketSocketRegistry(capacity=1)
                owner = prepare(
                    registry, path, expected_peer_pid=process.pid if correct_pid else os.getpid()
                )
                if correct_pid:
                    grant = await owner.exchange()
                    assert grant.ticket == TICKET
                    assert owner.snapshot().expected_pid_observed
                else:
                    with pytest.raises(GroupTicketSocketError) as error:
                        await owner.exchange()
                    assert error.value.reason == "peer_refused"
                    assert not error.value.mint_may_have_occurred
                    assert owner.snapshot().same_uid_observed
                    assert not owner.snapshot().expected_pid_observed
                assert await registry.drain()
                output, errors = await asyncio.wait_for(process.communicate(), 5)
                assert process.returncode == 0 and errors == b""
                assert int(output.strip()) > 0 if correct_pid else output.strip() == b"0"
            finally:
                # Child socket deadlines are finite; observe its natural exit,
                # never kill a helper or infer exit from observation timeout.
                await asyncio.wait_for(process.wait(), 5)
                assert process.returncode is not None

    asyncio.run(scenario())
