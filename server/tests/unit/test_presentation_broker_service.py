"""Real private socket/registry model; kernel peer is explicitly mocked here.

Separate-process peer/service qualification is not supplied by this test module.
All file roots and readers are new synthetic fixtures, no Hermes home or GO.
"""
import asyncio
import os
import shutil
import socket
import stat
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from hmp_plugin import presentation_broker_service as service
from hmp_plugin.presentation_broker_codec import (
    BrokerBinding,
    BrokerFrame,
    BrokerHeader,
    decode_frame,
    decode_scope_header,
    encode_frame,
    header_size,
)
from hmp_plugin.presentation_broker_endpoint import BrokerEndpointOwner
from hmp_plugin.presentation_broker_lifecycle import operation_id
from hmp_plugin.presentation_broker_registry import RegistryStatus
from hmp_plugin.presentation_budget import PresentationWorkLedger
from hmp_plugin.presentation_input_v3 import encode_input_v3
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner
from hmp_plugin.presentation_posix import PosixFileOps


def binding(serial=1, *, boot="c" * 64):
    return BrokerBinding("a" * 52, "b" * 32, boot, "d" * 64, operation_id(serial))


@pytest.fixture
def local(monkeypatch, request):
    parent = Path.cwd().resolve()
    if any(stat.S_IMODE(p.stat().st_mode) not in (0o700, 0o750, 0o755)
           for p in (parent, *parent.parents)):
        pytest.skip("synthetic reader roots require safe ancestors")
    temporary = Path("/private/tmp") if sys.platform == "darwin" else Path(tempfile.gettempdir())
    root = Path(tempfile.mkdtemp(prefix="hs-", dir=temporary)).resolve()
    home = Path(tempfile.mkdtemp(prefix="hmp-service-synthetic-", dir=parent)).resolve()
    (home / "profile.yaml").write_text("display_name: SYNTHETIC_SERVICE_ONLY\n")
    (home / "profile.yaml").chmod(0o600)
    path = str(root / "presentation.sock")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(path)
    os.chmod(path, 0o600)
    listener.listen(8)
    endpoint = BrokerEndpointOwner(str(root), expected_uid=os.geteuid())
    observation = endpoint.observe()
    e = service.StartupEnrollment(binding(), os.geteuid(), os.getpid() + 1,
                                  os.geteuid(), os.getpid(), "e" * 64,
                                  getattr(request, "param", 1))
    checks = []
    def peer(sock, *, expected_uid, expected_pid):
        checks.append((expected_uid, expected_pid))
        return service.PeerObservation(expected_uid, expected_pid)
    monkeypatch.setattr(service, "observe_peer", peer)
    spine = service.BrokerServiceSpine(listener, e, endpoint=endpoint, observation=observation,
        parser_package=str(Path(yaml.__file__).resolve().parent))
    clients = []
    def client():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(path)
        sock.setblocking(False)
        clients.append(sock)
        return sock
    def packet(b, end):
        ledger = PresentationWorkLedger(clock=time.monotonic, deadline=end / 1e9)
        owner = ParentPolicyReadOwner(root=str(home), home=str(home), profile="default",
            uid=os.geteuid(), gid=os.getegid(), ledger=ledger, fs=PosixFileOps(),
            current=lambda: True)
        snapshot = owner.run()
        return encode_input_v3({"schema": 3, "challenge": "f" * 64, "epoch": 1,
            "profile": "default", "root": str(home), "home": str(home), "operation": "METADATA",
            "expected_avatar_sha": None, "uid": os.geteuid(), "gid": os.getegid(),
            "deadline_ns": end, "directory_policy": [[r.uid, r.gid, r.modes[0]]
                                                       for r in snapshot.rules],
            "dir_modes": [0o700, 0o750, 0o755], "leaf_modes": [0o600, 0o640, 0o644],
            "source_manifest_sha": "e" * 64,
            "iid": b.iid, "canonical_fallback": "Synthetic", "observed_at": 0,
            "parent_work_counts": dict(snapshot.counts)})
    yield spine, e, client, packet, checks, root
    for sock in clients:
        sock.close()
    listener.close()
    assert endpoint.close()
    shutil.rmtree(root)
    shutil.rmtree(home)


async def read_frame(sock, b):
    loop = asyncio.get_running_loop()
    async def exact(n):
        out = bytearray()
        while len(out) < n:
            part = await asyncio.wait_for(loop.sock_recv(sock, n - len(out)), 1)
            assert part
            out.extend(part)
        return bytes(out)
    pre = await exact(8)
    raw = pre + await exact(header_size(pre))
    header = decode_scope_header(raw, expected_scope=b)
    return decode_frame(raw + await exact(header.body_length), expected=b)


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh_status_channel", [False, True])
async def test_actual_ready_cancel_cleanup_stays_pending_and_status_has_no_body(
    local, fresh_status_channel
):
    spine, _, client, packet, checks, _ = local
    b = binding()
    end = time.monotonic_ns() + 1_800_000_000
    body = packet(b, end)
    sock = client()
    task = asyncio.create_task(spine.serve_once(end))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "BEGIN", 0, body))
    try:
        ready = await read_frame(sock, b)
    except BaseException:
        await task
        raise
    assert ready.header.kind == "READY"
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "CANCEL", 1))
    await asyncio.wait_for(task, 1)
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert not spine._records and checks
    status_sock = client()
    status_task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    status_binding = replace(b, channel="e" * 64) if fresh_status_channel else b
    await asyncio.get_running_loop().sock_sendall(
        status_sock, encode_frame(status_binding, "STATUS", 0))
    result = await read_frame(status_sock, status_binding)
    assert result.header.kind == "PENDING" and result.body == b""
    status_sock.shutdown(socket.SHUT_WR)
    assert await asyncio.get_running_loop().sock_recv(status_sock, 1) == b""
    await status_task
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_wrong_peer_refuses_before_header_or_body_and_closes_partial(local, monkeypatch):
    spine, _, client, _, _, _ = local
    def wrong(*args, **kwargs): raise FrameError("wrong_peer")
    monkeypatch.setattr(service, "observe_peer", wrong)
    sock = client()
    with pytest.raises(service.ChannelAcquisitionError):
        await spine.serve_once(time.monotonic_ns() + 500_000_000)
    assert not spine._records, [(r.channel._integrity_lost, r.channel._close_attempted,
        r.channel._socket.fileno(), r.channel._identity, r.channel._context,
        r.channel._descriptor())
        for r in spine._records]
    assert spine._registry.counts.active == 0
    assert await asyncio.get_running_loop().sock_recv(sock, 1) == b""
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["oversized", "wrong_boot", "truncated"])
async def test_bad_header_refuses_without_reader(local, kind):
    spine, _, client, _, _, _ = local
    sock = client()
    wire = (b"HBR1" + (1025).to_bytes(4, "big") if kind == "oversized" else
            encode_frame(binding(boot="f" * 64), "STATUS", 0) if kind == "wrong_boot" else b"HBR")
    await asyncio.get_running_loop().sock_sendall(sock, wire)
    if kind == "truncated":
        sock.shutdown(socket.SHUT_WR)
    with pytest.raises(FrameError):
        await spine.serve_once(time.monotonic_ns() + 500_000_000)
    assert not spine._records, [(r.channel._integrity_lost, r.channel._close_attempted,
        r.channel._socket.fileno(), r.channel._identity, r.channel._context,
        r.channel._descriptor())
        for r in spine._records]
    assert spine._registry.counts.active == 0
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_shutdown_cancels_pending_accept_without_restarting(local):
    spine, *_ = local
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_500_000_000))
    await asyncio.sleep(0)
    assert await spine.stop_local_sockets()
    assert task.cancelled()
    assert not await spine.stop_local_sockets()


def test_same_process_enrollment_is_not_separate_broker():
    e = service.StartupEnrollment(binding(), 501, 100, 501, 100, "e" * 64)
    with pytest.raises(FrameError):
        e.validate()


def test_scoped_header_does_not_enroll_new_boot():
    b = binding()
    wire = encode_frame(replace(b, channel="e" * 64, operation=operation_id(2)), "STATUS", 0)
    assert decode_scope_header(wire, expected_scope=b).binding.channel == "e" * 64
    with pytest.raises(FrameError):
        decode_scope_header(wire, expected_scope=replace(b, broker="f" * 64))


@pytest.mark.asyncio
async def test_unqualified_go_is_never_relayed_and_started_debt_remains(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    def forbidden(*args):
        pytest.fail("service must not relay GO without native authority")
    monkeypatch.setattr(spine._registry, "relay_resource_go", forbidden)
    b = binding()
    end = time.monotonic_ns() + 1_800_000_000
    sock = client()
    task = asyncio.create_task(spine.serve_once(end))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "BEGIN", 0, packet(b, end)))
    assert (await read_frame(sock, b)).header.kind == "READY"
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "GO", 1))
    with pytest.raises(FrameError):
        await task
    held = next(iter(spine._registry._records.values()))
    assert held.resources._go_attempted is False
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_replay_after_started_cancel_does_not_start_second_reader(local):
    spine, _, client, packet, _, _ = local
    b = binding()
    end = time.monotonic_ns() + 1_800_000_000
    sock = client()
    task = asyncio.create_task(spine.serve_once(end))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "BEGIN", 0, packet(b, end)))
    assert (await read_frame(sock, b)).header.kind == "READY"
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "CANCEL", 1))
    await task
    original = next(iter(spine._registry._records.values())).owner
    end = time.monotonic_ns() + 1_000_000_000
    sock2 = client()
    await asyncio.get_running_loop().sock_sendall(
        sock2, encode_frame(b, "BEGIN", 0, packet(b, end)))
    with pytest.raises(FrameError):
        await spine.serve_once(end)
    assert len(spine._registry._records) == 1
    assert next(iter(spine._registry._records.values())).owner is original
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_progress_cannot_renew_absolute_receive_budget(local, monkeypatch):
    spine, _, client, _, _, _ = local
    sock = client()
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(binding(), "STATUS", 0))
    loop = asyncio.get_running_loop()
    original_recv = loop.sock_recv
    clock = [time.monotonic_ns()]
    async def paced_recv(*args):
        result = await original_recv(*args)
        clock[0] += 35_000_000
        return result
    monkeypatch.setattr(loop, "sock_recv", paced_recv)
    monkeypatch.setattr(service.time, "monotonic_ns", lambda: clock[0])
    with pytest.raises(FrameError):
        await spine.serve_once(clock[0] + 50_000_000)
    assert spine._registry.counts.active == 0 and not spine._records
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_endpoint_replacement_during_read_refuses_before_registry_lookup(local, monkeypatch):
    spine, _, client, _, _, root = local
    accepted = asyncio.Event()
    def peer(*args, **kwargs):
        accepted.set()
    monkeypatch.setattr(service, "observe_peer", peer)
    sock = client()
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    await accepted.wait()
    replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        (root / "presentation.sock").unlink()  # only this test's private endpoint
        replacement.bind(str(root / "presentation.sock"))
        os.chmod(root / "presentation.sock", 0o600)
        replacement.listen(1)
        await asyncio.get_running_loop().sock_sendall(sock, encode_frame(binding(), "STATUS", 0))
        with pytest.raises(FrameError):
            await task
        assert spine._registry.counts.active == 0 and not spine._records
        assert await spine.stop_local_sockets()
    finally:
        replacement.close()


@pytest.mark.asyncio
async def test_cancel_during_ready_write_invalidates_before_cleanup(local, monkeypatch):
    spine, _, client, packet, _, _ = local
    outgoing = asyncio.Event()
    original = service.SocketChannel.send
    async def paused(self, frame, end_ns):
        await original(self, frame, end_ns)
        outgoing.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(service.SocketChannel, "send", paused)
    b = binding()
    end = time.monotonic_ns() + 1_800_000_000
    sock = client()
    task = asyncio.create_task(spine.serve_once(end))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "BEGIN", 0, packet(b, end)))
    await outgoing.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert spine._registry.status(b) is RegistryStatus.PENDING and not spine._records
    held = next(iter(spine._registry._records.values()))
    assert held.resources._go_attempted is False
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_status_ack_retires_only_unlaunched_tombstone_not_replay_history(local):
    spine, _, client, packet, _, _ = local
    b = binding()
    ticket = spine._registry.reserve(b, "default", "METADATA", time.monotonic_ns() + 1_000_000_000)
    spine._registry.seal_unlaunched(ticket)
    sock = client()
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "STATUS", 0))
    assert (await read_frame(sock, b)).header.kind == "CLOSED"
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "ACK", 1))
    await task
    assert spine._registry.status(b) is RegistryStatus.UNKNOWN
    end = time.monotonic_ns() + 1_000_000_000
    sock2 = client()
    await asyncio.get_running_loop().sock_sendall(
        sock2, encode_frame(b, "BEGIN", 0, packet(b, end)))
    with pytest.raises(FrameError):
        await spine.serve_once(end)
    assert spine._registry.counts.active == 0 and not spine._records
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_cancel_after_readiness_never_drops_an_accepted_socket(local, monkeypatch):
    spine, _, client, _, _, _ = local
    loop = asyncio.get_running_loop()
    original_add = loop.add_reader
    task = None
    def cancelling_add(fd, callback, *args):
        def ready():
            callback(*args)
            task.cancel()  # readiness completed, awaiting task has not resumed
        return original_add(fd, ready)
    monkeypatch.setattr(loop, "add_reader", cancelling_add)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    await asyncio.sleep(0)
    assert spine._accept_wait is not None
    client()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not spine._records and spine._accept_wait is None
    assert not spine._accept_registration_unknown
    # No asynchronous result ever held a socket; pending kernel connection is
    # retired by closing this exact owned listener, not by a socket destructor.
    assert await spine.stop_local_sockets()


class ForeignComparison:
    def __eq__(self, other):
        pytest.fail("foreign comparison must not run")


def accepted_channel(local):
    spine, e, client, *_ = local
    client()
    sock, _ = service._SOCKET_ACCEPT(spine._listener)
    channel = service.SocketChannel(sock, e, role="broker", endpoint=spine._endpoint,
                                    observation=spine._observation)
    return channel, sock


@pytest.mark.parametrize("field", ["_context", "_values", "_identity"])
def test_channel_foreign_snapshot_refuses_without_comparison(local, field):
    channel, sock = accepted_channel(local)
    try:
        setattr(channel, field, ForeignComparison())
        with pytest.raises(FrameError):
            channel._check()
        assert channel.close() is False
    finally:
        sock.close()  # test's exact native socket only; no owner fact is forged


@pytest.mark.parametrize("field", ["_context", "_values", "_listener_identity"])
@pytest.mark.asyncio
async def test_listener_foreign_snapshot_refuses_without_comparison(local, field):
    spine, *_ = local
    setattr(spine, field, ForeignComparison())
    with pytest.raises(FrameError):
        spine._current()
    assert await spine.stop_local_sockets() is False


def test_close_flag_laundering_has_no_native_close_or_fact(local, monkeypatch):
    channel, sock = accepted_channel(local)
    try:
        channel._close_attempted = channel._closed_known = True
        monkeypatch.setattr(service, "_SOCKET_CLOSE", lambda s: pytest.fail("no native close"))
        assert channel.close() is False
        assert channel._close_fact is None
    finally:
        sock.close()


def test_postclose_reentry_cannot_mint_local_close_fact(local, monkeypatch):
    channel, sock = accepted_channel(local)
    original = service.os.fstat
    def reentrant(fd):
        try:
            return original(fd)
        except OSError:
            assert channel.close() is False
            raise
    monkeypatch.setattr(service.os, "fstat", reentrant)
    try:
        assert channel.close() is False
        assert channel._integrity_lost and channel._close_fact is None
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_cancel_queued_same_profile_never_launches_second_reader(local):
    spine, _, client, packet, _, _ = local
    b = binding()
    end = time.monotonic_ns() + 1_800_000_000
    sock = client()
    task = asyncio.create_task(spine.serve_once(end))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "BEGIN", 0, packet(b, end)))
    assert (await read_frame(sock, b)).header.kind == "READY"
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(b, "CANCEL", 1))
    await task
    b2 = binding(2)
    end = time.monotonic_ns() + 1_000_000_000
    queued = client()
    await asyncio.get_running_loop().sock_sendall(queued,
        encode_frame(b2, "BEGIN", 0, packet(b2, end)) + encode_frame(b2, "CANCEL", 1))
    await spine.serve_once(end)
    ticket = spine._registry._operations[b2.operation]
    held = spine._registry._record(ticket)
    assert held.owner._launch_attempted is False
    assert spine._registry.status(b2) is RegistryStatus.CLOSED
    assert spine._registry.status(b) is RegistryStatus.PENDING
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_holder_constructor_failure_precedes_native_accept(local, monkeypatch):
    spine, _, client, *_ = local
    client()
    def fail(*args):
        raise MemoryError("synthetic holder allocation failure")
    monkeypatch.setattr(service, "_Connection", fail)
    monkeypatch.setattr(service, "_SOCKET_ACCEPT", lambda *args: pytest.fail("must not accept"))
    with pytest.raises(MemoryError):
        await spine.serve_once(time.monotonic_ns() + 500_000_000)
    assert not spine._records
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_invalid_retention_list_refuses_before_native_accept(local, monkeypatch):
    spine, *_ = local
    class BadRetention(list):
        def append(self, value):
            pytest.fail("foreign append must not run")
    spine._records = BadRetention()
    monkeypatch.setattr(service, "_SOCKET_ACCEPT", lambda *args: pytest.fail("must not accept"))
    with pytest.raises(FrameError):
        await spine.serve_once(time.monotonic_ns() + 500_000_000)
    assert await spine.stop_local_sockets() is False


@pytest.mark.asyncio
async def test_postaccept_channel_allocation_failure_retains_native_socket(local, monkeypatch):
    spine, _, client, *_ = local
    client()
    def fail(*args, **kwargs):
        raise MemoryError("synthetic channel allocation failure")
    monkeypatch.setattr(service, "SocketChannel", fail)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 500_000_000))
    with pytest.raises(MemoryError):
        await task
    assert len(spine._records) == 1
    record = spine._records[0]
    assert type(record.socket) is socket.socket and record.socket.fileno() >= 0
    assert record.channel is None and record.local_closed is False
    assert spine._registry.counts.active == 0
    record.socket.close()  # exact test-owned handle; deliberately no service closure fact
    assert await spine.stop_local_sockets() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["read", "write"])
async def test_expired_budget_precedes_io_coroutine_creation(local, monkeypatch, direction):
    channel, sock = accepted_channel(local)
    loop = asyncio.get_running_loop()
    def forbidden(*args):
        pytest.fail("expired budget must not create an unawaited IO coroutine")
    monkeypatch.setattr(loop, "sock_recv" if direction == "read" else "sock_sendall", forbidden)
    try:
        with pytest.raises(FrameError):
            if direction == "read":
                await channel._exact(8, time.monotonic_ns() - 1)
            else:
                frame = BrokerFrame(BrokerHeader(binding(), "READY", 0, 0), b"")
                await channel.send(frame, time.monotonic_ns() - 1)
        assert channel.close()
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_wrong_outbound_scope_refuses_before_any_bytes(local, monkeypatch):
    channel, sock = accepted_channel(local)
    def forbidden(*args):
        pytest.fail("wrong startup scope must never reach wire")
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_sendall", forbidden)
    try:
        wrong = BrokerFrame(BrokerHeader(binding(boot="f" * 64), "READY", 0, 0), b"")
        with pytest.raises(FrameError):
            await channel.send(wrong, time.monotonic_ns() + 500_000_000)
        assert channel._refused and channel.close()
    finally:
        sock.close()
