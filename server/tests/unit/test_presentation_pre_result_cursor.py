"""Synthetic v2 BEGIN/READY bytes on owned sockets; no native/release authority."""
import asyncio
import errno
import os
import socket
import time
from contextlib import suppress
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_broker_service as service
from hmp_plugin import presentation_readiness as readiness
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_clock import NativeClockOwner
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


@pytest_asyncio.fixture
async def pair(local, monkeypatch, request):
    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    client_sock = client()
    accepted, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    accepted.setblocking(False)
    role = getattr(request, "param", "broker")
    own, other = ((accepted, client_sock) if role == "broker" else (client_sock, accepted))
    e = replace(enrollment, protocol_version=2,
                gateway_pid=os.getpid() + (1 if role == "broker" else 0),
                service_pid=os.getpid() + (0 if role == "broker" else 1))
    channel = service.SocketChannel(own, e, role=role,
        endpoint=spine._endpoint, observation=spine._observation)
    tasks = []
    b = binding()

    def start():
        end = time.monotonic_ns() + 2_000_000_000
        task = asyncio.create_task(channel.receive(end,
            expected=b if role == "gateway" else None))
        tasks.append(task)
        return task

    yield channel, other, b, start
    for task in tasks:
        if not task.done():
            task.cancel()
        with suppress(BaseException):
            await task
        assert task.done()
    if channel._reading:
        cursor = channel._pre_result_cursor_origin
        assert cursor._io_unknown and not channel.close()
        # Fixture-only disposal after exact original Task join. No production
        # socket/read/clock closure facts are manufactured for unknown IO.
        asyncio.get_running_loop().remove_reader(own.fileno())
        assert NativeClockOwner.close_local(channel._clock_owner_snapshot)
        own.close()
        assert not channel._closed_known and not channel._clock_closed_known
    else:
        assert channel.close() and channel.close_clock()
    other.close()
    own.close()
    assert await spine.stop_local_sockets()


@pytest.mark.parametrize("pair", ["broker", "gateway"], indirect=True)
async def test_one_private_frame_retains_metadata_and_wipes_cursor_copy(pair):
    channel, peer, b, start = pair
    body = b"SYNTHETIC_INPUT" if channel._role == "broker" else b""
    kind = "BEGIN" if channel._role == "broker" else "READY"
    wire = encode_frame(b, kind, 0, body, version=2)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire)
    frame = await task
    cursor = channel._pre_result_cursor_origin
    assert frame.body == body and frame.header.kind == kind
    assert cursor._done and cursor._received == cursor._target == len(wire)
    assert not cursor._scope_origin.buffer and cursor._pending is None
    assert cursor._header is frame.header and not channel._reading
    with pytest.raises(FrameError):
        await channel.receive(time.monotonic_ns() + 1_000_000_000, expected=b)
    assert channel._pre_result_cursor_origin is cursor  # no replacement/replay


@pytest.mark.parametrize("stage", ["prefix", "body"])
async def test_partial_frame_cancel_after_hint_consumes_no_following_bytes(
    pair, monkeypatch, stage
):
    channel, peer, b, start = pair
    original = service.SelectorReadiness.wait
    registered = asyncio.Event()
    body = b"SYNTHETIC_INPUT"
    wire = encode_frame(b, "BEGIN", 0, body, version=2)
    cut = 3 if stage == "prefix" else len(wire) - len(body) + 3

    async def wait(waiter, end):
        cursor = channel._pre_result_cursor_origin
        if cursor._received == cut:
            registered.set()
        await original(waiter, end)
        if cursor._received == cut:
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

    monkeypatch.setattr(service.SelectorReadiness, "wait", wait)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire[:cut])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[cut:])
    with pytest.raises(asyncio.CancelledError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert cursor._received == cut and cursor._target == (8 if stage == "prefix" else len(wire))
    assert not cursor._io_unknown and not channel._reading and not cursor._scope_origin.buffer
    assert channel._socket_snapshot.recv(len(wire)) == wire[cut:]  # exact synthetic test peer


@pytest.mark.parametrize("pair,kind", [("gateway", "BEGIN"), ("broker", "RESULT")],
                         indirect=["pair"])
async def test_wrong_phase_header_refuses_before_body_read(pair, kind):
    channel, peer, b, start = pair
    body = b"SYNTHETIC_BODY"
    wire = encode_frame(b, kind, 0, body, version=2)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire)
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert cursor._received == len(wire) - len(body)
    assert cursor._header is None and not channel._reading
    assert channel._socket_snapshot.recv(len(body)) == body


async def test_uncertain_recv_holds_original_read_claim(pair, monkeypatch):
    channel, peer, b, start = pair
    original = service._SOCKET_RECV
    consumed = []

    def recv(sock, count):
        part = original(sock, count)
        consumed.append(len(part))
        raise RuntimeError("synthetic interruption after syscall")

    monkeypatch.setattr(service, "_SOCKET_RECV", recv)
    task = start()
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2))
    with pytest.raises(RuntimeError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert consumed == [8] and cursor._received == 0
    assert cursor._io_unknown and cursor._intent and channel._reading
    assert cursor._pending is None and not cursor._scope_origin.buffer


async def test_buffer_pair_retarget_wipes_only_original_private_copy(pair, monkeypatch):
    channel, peer, b, start = pair
    original = service._SOCKET_RECV
    foreign = bytearray(b"OTHER_OPERATION_SYNTHETIC")
    held = bytes(foreign)

    def recv(sock, count):
        part = original(sock, count)
        cursor = channel._pre_result_cursor_origin
        cursor._buffer = cursor._buffer_origin = foreign
        return part

    monkeypatch.setattr(service, "_SOCKET_RECV", recv)
    task = start()
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2))
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert bytes(foreign) == held and not cursor._scope_origin.buffer
    assert cursor._received == 8 and cursor._io_unknown and channel._reading


async def test_eagain_with_cancellation_cannot_register_interest(pair, monkeypatch):
    channel, _, _, start = pair
    calls = []

    def recv(sock, count):
        asyncio.current_task().cancel()
        raise BlockingIOError(errno.EAGAIN, "synthetic zero-byte cancellation")

    def initialize(*args):
        calls.append(True)
        raise AssertionError("must not register retired work")

    monkeypatch.setattr(service, "_SOCKET_RECV", recv)
    monkeypatch.setattr(service.SelectorReadiness, "__init__", initialize)
    with pytest.raises(asyncio.CancelledError):
        await start()
    cursor = channel._pre_result_cursor_origin
    assert calls == [] and cursor._received == 0
    assert not cursor._io_unknown and not channel._reading


async def test_known_eof_preserves_consumed_offset_without_unknown_claim(pair):
    channel, peer, _, start = pair
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, b"HMP")
    peer.shutdown(socket.SHUT_WR)
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert cursor._received == 3 and not cursor._scope_origin.buffer
    assert not cursor._io_unknown and not channel._reading


@pytest.mark.parametrize("field", ["_received", "_target"])
async def test_counter_drift_never_invokes_foreign_arithmetic(pair, monkeypatch, field):
    channel, peer, b, start = pair
    original = service._SOCKET_RECV
    callbacks = []

    class Foreign:
        def __add__(self, other):
            callbacks.append("add")
            raise AssertionError("foreign arithmetic")
        __iadd__ = __add__
        def __eq__(self, other):
            callbacks.append("eq")
            raise AssertionError("foreign comparison")

    def recv(sock, count):
        part = original(sock, count)
        setattr(channel._pre_result_cursor_origin, field, Foreign())
        return part

    monkeypatch.setattr(service, "_SOCKET_RECV", recv)
    task = start()
    await asyncio.get_running_loop().sock_sendall(
        peer, encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2))
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert callbacks == [] and cursor._received == 8
    assert cursor._io_unknown and channel._reading and not cursor._scope_origin.buffer


async def test_uncertain_registration_retirement_cannot_clear_read_claim(pair, monkeypatch):
    channel, peer, b, start = pair
    original_wait, original_remove = service.SelectorReadiness.wait, readiness._remove_reader
    registered = asyncio.Event()

    def uncertain_remove(loop, fd):
        original_remove(loop, fd)
        return False  # explicit synthetic lost acknowledgement, never retry/claim known close

    async def wait(waiter, end):
        registered.set()
        return await original_wait(waiter, end)

    monkeypatch.setattr(readiness, "_remove_reader", uncertain_remove)
    monkeypatch.setattr(service.SelectorReadiness, "wait", wait)
    wire = encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert cursor._received == 3 and cursor._io_unknown and channel._reading
    assert not cursor._scope_origin.buffer and not channel._closed_known


async def test_scope_pair_retarget_never_touches_other_channel(pair, monkeypatch):
    channel, peer, b, start = pair
    original_wait = service.SelectorReadiness.wait
    foreign = service.SocketChannel.__new__(service.SocketChannel)
    foreign._reading = True
    registered = asyncio.Event()

    async def wait(waiter, end):
        registered.set()
        await original_wait(waiter, end)
        cursor = channel._pre_result_cursor_origin
        cursor._scope = cursor._scope_snapshot = cursor._scope_origin._replace(channel=foreign)

    monkeypatch.setattr(service.SelectorReadiness, "wait", wait)
    wire = encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert foreign._reading and not channel._reading
    assert cursor._received == 3 and not cursor._scope_origin.buffer


@pytest.mark.parametrize("flag", ["_retired", "_unknown", "_attempted"])
@pytest.mark.parametrize("raise_after", [False, True])
async def test_foreign_readiness_flags_never_dispatch_bool_or_claim_retirement(
    pair, monkeypatch, flag, raise_after
):
    channel, peer, b, start = pair
    original = service.SelectorReadiness.wait
    registered = asyncio.Event()
    callbacks = []

    class Foreign:
        def __bool__(self):
            callbacks.append("bool")
            raise AssertionError("foreign readiness truthiness")

    async def wait(waiter, end):
        registered.set()
        await original(waiter, end)
        setattr(waiter, flag, Foreign())
        if raise_after:
            raise FrameError("synthetic unknown notification outcome")

    monkeypatch.setattr(service.SelectorReadiness, "wait", wait)
    wire = encode_frame(b, "BEGIN", 0, b"SYNTHETIC_INPUT", version=2)
    task = start()
    await asyncio.get_running_loop().sock_sendall(peer, wire[:3])
    await registered.wait()
    await asyncio.get_running_loop().sock_sendall(peer, wire[3:])
    with pytest.raises(FrameError):
        await task
    cursor = channel._pre_result_cursor_origin
    assert callbacks == [] and cursor._received == 3
    assert cursor._io_unknown and channel._reading and not channel._closed_known
