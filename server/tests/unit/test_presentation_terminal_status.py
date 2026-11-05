"""Real owned sockets; kernel peer mock is explicit in shared local fixture.

No service manager, host profile, GO or RESULT. The separate Darwin peer test
independently records why terminal credentials cannot be a liveness test.
"""
import asyncio
import errno
import os
import socket
import time
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_broker_service as service
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_registry import RegistryStatus
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding as fresh_binding
from .test_presentation_broker_service import local as local
from .test_presentation_broker_service import read_frame

_BASE_BINDING = fresh_binding()


def binding(*, boot="c" * 64):
    return replace(_BASE_BINDING, broker=boot)


@pytest_asyncio.fixture
async def gateway(local):
    spine, enrollment, client, _, _, _ = local
    sock = client()
    remote, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    remote.setblocking(False)
    e = replace(enrollment, gateway_pid=os.getpid(), service_pid=os.getpid() + 1)
    channel = service.SocketChannel(sock, e, role="gateway", endpoint=spine._endpoint,
                                    observation=spine._observation)
    try:
        yield channel, remote, spine
    finally:
        channel.close()
        sock.close()  # dispose the test-owned original even after deliberately poisoned metadata
        remote.close()
        assert await spine.stop_local_sockets()


def adopt(channel, b=None, end=None):
    owner = service.TerminalStatusExchange.__new__(service.TerminalStatusExchange)
    owner.__init__(channel, binding() if b is None else b,
                   time.monotonic_ns() + 1_000_000_000 if end is None else end)
    return owner


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["PENDING", "UNKNOWN"])
async def test_buffered_bodyless_reply_survives_remote_close_without_reauthentication(
    gateway, monkeypatch, kind
):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    assert (await read_frame(remote, binding())).header.kind == "STATUS"
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), kind, 0))
    remote.close()  # buffered frame is present while credential APIs may now refuse
    def unavailable(*args, **kwargs):
        pytest.fail("terminal receive must not ask a closed peer to remain live")
    monkeypatch.setattr(service, "observe_peer", unavailable)
    frame = await owner.receive_reply()
    assert frame.header.kind == kind and frame.body == b"" and owner._phase == "complete"
    assert owner._completion == "queued_eof" and owner._shutdown_intent is False


@pytest.mark.asyncio
async def test_live_reply_requires_one_halfclose_and_clean_eof(gateway):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "PENDING", 0))
    receiving = asyncio.create_task(owner.receive_reply())
    assert await asyncio.get_running_loop().sock_recv(remote, 1) == b""
    assert not receiving.done()  # no result until the remote transport also ends cleanly
    remote.close()
    assert (await receiving).header.kind == "PENDING"
    assert owner._phase == "complete"
    assert owner._completion == "halfclose_eof" and owner._shutdown_returned is True


@pytest.mark.asyncio
@pytest.mark.parametrize("wire", [
    b"HBR",
    encode_frame(binding(), "PENDING", 0) + b"unexpected",
    encode_frame(binding(), "READY", 0),
    encode_frame(binding(), "PENDING", 1),
    encode_frame(replace(binding(), channel="e" * 64), "PENDING", 0),
    encode_frame(binding(boot="f" * 64), "PENDING", 0),
])
async def test_truncated_trailing_nonstatus_and_wrong_binding_refuse(gateway, wire):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, wire)
    remote.close()
    with pytest.raises(FrameError):
        await owner.receive_reply()
    assert owner._failed is True and channel._refused is True
    with pytest.raises(FrameError):
        await owner.receive_reply()  # no revival/replay after a partial or invalid reply


@pytest.mark.asyncio
async def test_halfclose_uncertainty_is_not_retried_or_published(gateway, monkeypatch):
    channel, remote, _ = gateway
    calls = []
    original = service._SOCKET_SHUTDOWN
    def ambiguous(sock, how):
        calls.append(how)
        original(sock, how)  # effect occurred, but the caller cannot certify its return
        raise OSError(errno.ENOTCONN, "synthetic lost halfclose outcome")
    monkeypatch.setattr(service, "_SOCKET_SHUTDOWN", ambiguous)
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "PENDING", 0))
    with pytest.raises(OSError):
        await owner.receive_reply()
    with pytest.raises(FrameError):
        await owner.receive_reply()
    assert calls == [socket.SHUT_WR] and owner._failed is True
    assert owner._shutdown_intent is True and owner._shutdown_returned is False
    assert owner._completion is None


@pytest.mark.asyncio
@pytest.mark.parametrize("when", ["post_send", "eof_entry"])
async def test_broker_accepts_queued_eof_without_postclose_peer_api(local, monkeypatch, when):
    spine, _, client, _, _, _ = local
    sock = client()
    loop = asyncio.get_running_loop()
    original_send, original_eof = loop.sock_sendall, service.TerminalStatusExchange._eof
    closed = False
    original_peer = service.observe_peer
    def peer(*args, **kwargs):
        if closed:
            pytest.fail("closed peer is not a credential-availability requirement")
        return original_peer(*args, **kwargs)
    async def close_peer():
        nonlocal closed
        # Closing with unread response bytes sends ECONNRESET on Linux. Drain
        # the canonical reply first: this causal targets clean EOF, not reset.
        assert (await read_frame(sock, binding())).header.kind == "UNKNOWN"
        sock.close()
        closed = True
    async def send(target, data):
        await original_send(target, data)
        if target is not sock and when == "post_send":
            await close_peer()
    async def eof(owner):
        if when == "eof_entry":
            await close_peer()
        await original_eof(owner)
    monkeypatch.setattr(service, "observe_peer", peer)
    monkeypatch.setattr(loop, "sock_sendall", send)
    monkeypatch.setattr(service.TerminalStatusExchange, "_eof", eof)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    await loop.sock_sendall(sock, encode_frame(binding(), "STATUS", 0))
    await task
    assert closed and not spine._records
    assert spine._registry.status(binding()) is RegistryStatus.UNKNOWN
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_broker_refuses_trailing_gateway_data_and_keeps_registry(local):
    spine, _, client, _, _, _ = local
    sock = client()
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 1_000_000_000))
    await asyncio.get_running_loop().sock_sendall(sock, encode_frame(binding(), "STATUS", 0))
    assert (await read_frame(sock, binding())).header.kind == "UNKNOWN"
    await asyncio.get_running_loop().sock_sendall(sock, b"unexpected")
    sock.shutdown(socket.SHUT_WR)
    with pytest.raises(FrameError):
        await task
    assert spine._registry.status(binding()) is RegistryStatus.UNKNOWN
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_initial_authentication_failure_retains_partial_owner(gateway, monkeypatch):
    channel, _, _ = gateway
    def refused(*args, **kwargs):
        raise FrameError("initial peer refusal")
    monkeypatch.setattr(service, "observe_peer", refused)
    with pytest.raises(FrameError):
        adopt(channel)
    assert type(channel._terminal_owner) is service.TerminalStatusExchange
    assert channel._terminal_owner._failed is True and channel._refused is True


@pytest.mark.asyncio
async def test_duplicate_adoption_and_ordinary_io_cannot_reopen_channel(gateway):
    channel, _, _ = gateway
    owner = adopt(channel)
    with pytest.raises(FrameError):
        adopt(channel)
    assert channel._terminal_owner is owner
    with pytest.raises(FrameError):
        await channel.receive(time.monotonic_ns() + 1_000_000_000, expected=binding())
    with pytest.raises(FrameError):
        await owner.request()


@pytest.mark.asyncio
@pytest.mark.parametrize("drift", ["binding", "endpoint", "generation", "socket"])
async def test_terminal_scope_drift_is_sticky(gateway, monkeypatch, drift):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "PENDING", 0))
    remote.close()
    if drift == "binding":
        owner._binding = replace(binding(), operation="e" * 64)
    elif drift == "endpoint":
        channel._observation = object()
    elif drift == "generation":
        object.__setattr__(channel._enrollment, "installation_generation", "f" * 64)
    else:
        channel._socket = object()
    with pytest.raises(FrameError):
        await owner.receive_reply()
    assert owner._failed is True
    # Restore references to demonstrate that a poisoned exchange cannot revive.
    # The fixture disposes its retained original socket without claiming closure.
    owner._binding = owner._binding_snapshot
    channel._observation = channel._observation_snapshot
    object.__setattr__(channel._enrollment, "installation_generation", channel._values[7])
    channel._socket = channel._socket_snapshot
    with pytest.raises(FrameError):
        await owner.receive_reply()


@pytest.mark.asyncio
async def test_cancelled_status_read_stays_failed_and_has_no_halfclose(gateway, monkeypatch):
    channel, remote, _ = gateway
    calls = []
    original = service._SOCKET_SHUTDOWN
    def shutdown(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(service, "_SOCKET_SHUTDOWN", shutdown)
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    task = asyncio.create_task(owner.receive_reply())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert owner._failed is True and calls == []
    with pytest.raises(FrameError):
        await owner.receive_reply()


@pytest.mark.asyncio
async def test_partial_progress_cannot_renew_original_status_deadline(gateway):
    channel, remote, _ = gateway
    end = time.monotonic_ns() + 40_000_000
    owner = adopt(channel, end=end)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, b"H")
    with pytest.raises((TimeoutError, FrameError)):
        await owner.receive_reply()
    assert owner._end == end and owner._failed is True
    assert owner._shutdown_intent is False


@pytest.mark.asyncio
@pytest.mark.parametrize("peer_unavailable", [False, True])
async def test_closed_does_not_gain_terminal_peer_relaxation(
    gateway, monkeypatch, peer_unavailable
):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "CLOSED", 0))
    if peer_unavailable:
        calls = []
        def unavailable(*args, **kwargs):
            calls.append(True)
            raise FrameError("synthetic current peer API unavailable")
        monkeypatch.setattr(service, "observe_peer", unavailable)
        with pytest.raises(FrameError):
            await owner.receive_reply()
        assert calls == [True]  # CLOSED must still perform current peer authentication
    else:
        assert (await owner.receive_reply()).header.kind == "CLOSED"
        assert owner._phase == "gateway_closed_ack"
        await owner.acknowledge_closed()
        assert (await read_frame(remote, binding())).header.kind == "ACK"
    assert owner._completion is None and owner._shutdown_intent is False


@pytest.mark.asyncio
async def test_close_cannot_dispose_socket_under_terminal_read(gateway):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    task = asyncio.create_task(owner.receive_reply())
    await asyncio.sleep(0)
    assert channel._reading is True
    assert channel.close() is False
    assert channel._socket_snapshot.fileno() >= 0
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert owner._failed is True and owner._shutdown_intent is False


@pytest.mark.asyncio
async def test_changed_kernel_blocking_flag_refuses_before_any_terminal_read(gateway):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    os.set_blocking(channel._fd, True)
    try:
        with pytest.raises(FrameError):
            await owner.receive_reply()
        assert owner._failed is True and owner._shutdown_intent is False
    finally:
        os.set_blocking(channel._fd, False)


@pytest.mark.asyncio
async def test_positive_python_timeout_refuses_before_io_creation(gateway, monkeypatch):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    channel._socket.settimeout(0.25)
    assert os.get_blocking(channel._fd) is False  # insufficient without native gettimeout
    def forbidden(*args):
        pytest.fail("must refuse before even creating another socket read")
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_recv", forbidden)
    try:
        with pytest.raises(FrameError):
            await owner.receive_reply()
        assert owner._failed is True and owner._shutdown_intent is False
    finally:
        channel._socket.setblocking(False)


@pytest.mark.asyncio
async def test_reset_after_bodyless_reply_is_not_clean_eof(gateway, monkeypatch):
    channel, remote, _ = gateway
    owner = adopt(channel)
    await owner.request()
    await read_frame(remote, binding())
    await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "PENDING", 0))
    original_recv = asyncio.get_running_loop().sock_recv
    async def reset_after_halfclose(sock, amount):
        if owner._shutdown_intent:
            raise ConnectionResetError(errno.ECONNRESET, "synthetic connection reset")
        return await original_recv(sock, amount)
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_recv", reset_after_halfclose)
    with pytest.raises(ConnectionResetError):
        await owner.receive_reply()
    assert owner._failed is True and owner._completion is None
    with pytest.raises(FrameError):
        await owner.receive_reply()  # no retry or reset-to-EOF conversion
