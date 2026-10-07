"""Isolated AF_UNIX/fake-handler controls, never a native/card/phone integration."""

from __future__ import annotations

import asyncio
import contextlib
import os
import socket
import stat
import struct
import sys
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import approval_test_host_transport as transport
from hmp_plugin.approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
    HostResponse,
    decode_host_response_frame,
    encode_host_request,
    encode_host_response,
    unavailable_response_frame,
)

_OP = "1" * 32


@pytest.fixture
def record() -> Iterator[Path]:
    # Fixed short isolated temp parent: no real listener record or host files.
    with tempfile.TemporaryDirectory(prefix="ht-", dir="/tmp") as directory:
        parent = Path(directory)
        parent.chmod(0o700)
        yield parent / "listener.json"


def _generation() -> HostGeneration:
    return HostGeneration("a" * 52, os.getpid(), "0" * 32)


def _begin(generation: HostGeneration | None = None) -> HostBeginRequest:
    return HostBeginRequest(generation or _generation(), "synthetic-device",
                            "synthetic-profile", "synthetic-session", 30000)


class _Handler:
    """Only memory events; no producer/native/DB/server bearer or phone use."""

    def __init__(self) -> None:
        self.requests: list[object] = []
        self.finish = asyncio.Event()
        self.shutdown_seen = asyncio.Event()
        self.shutdown_finish = asyncio.Event()
        self.shutdown_finish.set()
        self.failed_writes = 0

    async def responses(self, request: transport.HostRequest) -> AsyncIterator[HostResponse]:
        self.requests.append(request)
        if type(request) is HostBeginRequest:
            yield HostResponse("accepted", _OP, timeout_ms=request.timeout_ms)
            await self.finish.wait()
            yield HostResponse("completed", _OP, state="cancelled")
        elif request.op == "status":
            yield HostResponse("status", request.operation_id, state="pending", remaining_ms=1)
        else:
            self.finish.set()
            yield HostResponse("cancel_requested", request.operation_id, state="cleanup_pending")

    async def write_failed(self, request: HostBeginRequest) -> None:
        self.failed_writes += 1
        self.finish.set()

    async def shutdown(self) -> None:
        self.shutdown_seen.set()
        await self.shutdown_finish.wait()
        self.finish.set()


async def _connect(record: Path) -> socket.socket:
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    peer.setblocking(False)
    await asyncio.get_running_loop().sock_connect(peer, str(record.parent / "approval-test.sock"))
    return peer


async def _until(condition: Callable[[], bool]) -> None:
    # Passive test observation of OS scheduling: at most one cancellable timer,
    # never a production polling loop or growing task queue.
    loop = asyncio.get_running_loop()
    observed = asyncio.Event()
    timer: asyncio.TimerHandle | None = None

    def check() -> None:
        nonlocal timer
        if condition():
            observed.set()
        else:
            timer = loop.call_later(0.001, check)

    try:
        async with asyncio.timeout(1):
            check()
            await observed.wait()
    finally:
        if timer is not None:
            timer.cancel()


async def _reply(peer: socket.socket) -> HostResponse:
    return await transport._response(peer, held_completion=False)


def _fixed_error(call: Callable[[], object]) -> None:
    with pytest.raises(transport.HostTransportError) as caught:
        call()
    assert caught.value.args == ("approval test unavailable",)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_actual_current_platform_kernel_uid_from_socketpair() -> None:
    assert sys.platform == "darwin" or sys.platform.startswith("linux")
    first, second = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        assert transport.peer_uid(first) == os.getuid()
        assert transport.peer_uid(second) == os.getuid()
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("raw", [b"", b"x", struct.pack("iII", 0, 1, 1)])
def test_linux_credential_mock_refuses_bad_kernel_record(raw: bytes, monkeypatch) -> None:
    monkeypatch.setattr(transport, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(socket, "SO_PEERCRED", 17, raising=False)

    class Peer:
        family = socket.AF_UNIX

        def getsockopt(self, level: int, option: int, size: int) -> bytes:
            assert (level, option, size) == (socket.SOL_SOCKET, 17, 12)
            return raw

    _fixed_error(lambda: transport.peer_uid(Peer()))


def test_linux_unsigned_uid_mock_preserves_kernel_value(monkeypatch) -> None:
    monkeypatch.setattr(transport, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(socket, "SO_PEERCRED", 17, raising=False)

    class Peer:
        family = socket.AF_UNIX

        def getsockopt(self, level: int, option: int, size: int) -> bytes:
            return struct.pack("iII", 123, 2**32 - 1, 22)

    assert transport.peer_uid(Peer()) == 2**32 - 1


def test_unsupported_platform_has_no_file_or_tcp_fallback(record: Path, monkeypatch) -> None:
    monkeypatch.setattr(transport, "sys", SimpleNamespace(platform="unsupported"))
    _fixed_error(lambda: transport.HostIpcEndpoint(record, _generation(), _Handler()))
    assert list(record.parent.iterdir()) == []


@pytest.mark.parametrize("mode", [0o770, 0o750, 0o711, 0o777])
def test_non_private_parent_never_binds(record: Path, mode: int) -> None:
    record.parent.chmod(mode)
    _fixed_error(lambda: transport.HostIpcEndpoint(record, _generation(), _Handler()))
    assert list(record.parent.iterdir()) == []


def test_symlink_parent_is_not_followed(record: Path) -> None:
    link = record.parent / "link"
    link.symlink_to(record.parent, target_is_directory=True)
    _fixed_error(
        lambda: transport.HostIpcEndpoint(link / "listener.json", _generation(), _Handler())
    )
    assert not (record.parent / "approval-test.sock").exists()


def test_wrong_parent_owner_refuses(record: Path, monkeypatch) -> None:
    native = os.lstat

    def changed(path):
        value = native(path)
        if path == record.parent:
            values = list(value)
            values[4] = os.getuid() + 1
            return os.stat_result(values)
        return value

    monkeypatch.setattr(os, "lstat", changed)
    _fixed_error(lambda: transport.HostIpcEndpoint(record, _generation(), _Handler()))


@pytest.mark.parametrize("record", [Path("relative/listener.json"), Path("/synthetic/other.json"),
                                    Path("/synthetic/../synthetic/listener.json"),
                                    Path("/synthetic") / ("x" * 200) / "listener.json"])
def test_fixed_path_and_length_fail_before_bind(record: Path) -> None:
    _fixed_error(lambda: transport.HostIpcEndpoint(record, _generation(), _Handler()))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["file", "symlink", "socket"])
async def test_preexisting_sidecar_is_preserved(record: Path, kind: str) -> None:
    path = record.parent / "approval-test.sock"
    existing = None
    if kind == "file":
        path.write_text("preserve")
    elif kind == "symlink":
        path.symlink_to(record.parent / "missing")
    else:
        existing = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        existing.bind(str(path))
    before = os.lstat(path)
    endpoint = transport.HostIpcEndpoint(record, _generation(), _Handler())
    try:
        _fixed_error(endpoint.start)
        assert transport._identity(os.lstat(path)) == transport._identity(before)
        assert await endpoint.close()
        assert transport._identity(os.lstat(path)) == transport._identity(before)
    finally:
        if existing is not None:
            existing.close()


@pytest.mark.asyncio
async def test_real_local_held_begin_status_cancel_and_owned_cleanup(record: Path) -> None:
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    path = record.parent / "approval-test.sock"
    assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600
    begin = transport.host_exchange(record, _begin())
    try:
        assert (await anext(begin)).result == "accepted"
        assert len(endpoint._connections) == 1
        # Expected request half-close does not cancel or finish the held lease.
        assert not handler.finish.is_set() and handler.failed_writes == 0
        for operation in ("status", "cancel"):
            request = HostOperationRequest(_generation(), operation, _OP)
            replies = [reply async for reply in transport.host_exchange(record, request)]
            assert len(replies) == 1
            assert replies[0].result == ("status" if operation == "status" else "cancel_requested")
        final = await anext(begin)
        assert final.result == "completed" and final.operation_id == _OP
        with pytest.raises(StopAsyncIteration):
            await anext(begin)
        assert len(handler.requests) == 3 and handler.failed_writes == 0
    finally:
        await begin.aclose()
        assert await endpoint.close()
    assert not path.exists()


@pytest.mark.asyncio
async def test_peer_refused_before_handler_or_input_parse(record: Path, monkeypatch) -> None:
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    monkeypatch.setattr(transport, "peer_uid", lambda _peer: os.getuid() + 1)
    peer = await _connect(record)
    try:
        assert await _reply(peer) == HostResponse("unavailable")
        assert handler.requests == []
    finally:
        peer.close()
        assert await endpoint.close()


@pytest.mark.asyncio
async def test_second_begin_refuses_but_status_connection_remains_available(record: Path) -> None:
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    first = transport.host_exchange(record, _begin())
    try:
        assert (await anext(first)).result == "accepted"
        second = [r async for r in transport.host_exchange(record, _begin())]
        assert second == [HostResponse("unavailable")]
        assert len(handler.requests) == 1 and endpoint._begin_active
        request = HostOperationRequest(_generation(), "status", _OP)
        assert [r.result async for r in transport.host_exchange(record, request)] == ["status"]
        assert endpoint._begin_active and not handler.finish.is_set()
    finally:
        await first.aclose()
        await endpoint.close()


@pytest.mark.asyncio
async def test_final_result_waits_for_actual_handler_return(record: Path) -> None:
    handler = _Handler()
    cleanup_entered, cleanup_release = asyncio.Event(), asyncio.Event()
    original = handler.responses

    async def retained(request):
        async for reply in original(request):
            yield reply
        cleanup_entered.set()
        await cleanup_release.wait()

    handler.responses = retained
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    first = transport.host_exchange(record, _begin())
    completion = None
    try:
        assert (await anext(first)).result == "accepted"
        handler.finish.set()
        completion = asyncio.create_task(anext(first))
        await cleanup_entered.wait()
        assert not completion.done() and endpoint._begin_active
        assert len(endpoint._connections) == 1
        cleanup_release.set()
        assert (await completion).result == "completed"
        with pytest.raises(StopAsyncIteration):
            await anext(first)
    finally:
        cleanup_release.set()
        if completion is not None and not completion.done():
            await completion
        await first.aclose()
        await endpoint.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["iid", "pid", "nonce"])
async def test_stale_generation_refuses_before_handler(record: Path, field: str) -> None:
    current = _generation()
    changed = HostGeneration("b" * 51 + "a" if field == "iid" else current.iid,
                             current.pid + 1 if field == "pid" else current.pid,
                             "1" * 32 if field == "nonce" else current.nonce)
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, current, handler)
    endpoint.start()
    try:
        replies = [r async for r in transport.host_exchange(record, _begin(changed))]
        assert replies == [HostResponse("unavailable")] and handler.requests == []
    finally:
        assert await endpoint.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b"", b"\x00\x00", b"\0\0\0\0", b"\0\0\x08\x01",
                                 b"\0\0\0\x01{", b"\0\0\0\x02{}x"])
async def test_invalid_frames_are_fixed_refusal(record: Path, raw: bytes) -> None:
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)
    try:
        await asyncio.get_running_loop().sock_sendall(peer, raw)
        peer.shutdown(socket.SHUT_WR)
        assert await _reply(peer) == HostResponse("unavailable")
        assert handler.requests == []
    finally:
        peer.close()
        assert await endpoint.close()


@pytest.mark.asyncio
async def test_missing_eof_times_out_without_admission(record: Path, monkeypatch) -> None:
    monkeypatch.setattr(transport, "FRAME_SECONDS", 0.05)
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)
    try:
        await asyncio.get_running_loop().sock_sendall(peer, encode_host_request(_begin()))
        await _until(lambda: not endpoint._connections)
        # Wait for acceptance then expiry deterministically rather than treating zero
        # connections before accept as proof of a deadline.
        await asyncio.sleep(0.08)
        assert await _reply(peer) == HostResponse("unavailable")
        assert handler.requests == []
    finally:
        peer.close()
        assert await endpoint.close()


@pytest.mark.asyncio
async def test_slow_header_cannot_restart_whole_request_deadline(record: Path, monkeypatch) -> None:
    monkeypatch.setattr(transport, "FRAME_SECONDS", 0.06)
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)
    try:
        loop = asyncio.get_running_loop()
        await _until(lambda: len(endpoint._connections) == 1)
        await loop.sock_sendall(peer, b"\0")
        await asyncio.sleep(0.04)
        await loop.sock_sendall(peer, b"\0")
        # The second byte does not grant another budget. No request or EOF exists.
        assert await _reply(peer) == HostResponse("unavailable")
        assert handler.requests == []
    finally:
        peer.close()
        await endpoint.close()


@pytest.mark.asyncio
async def test_four_connections_limit_and_join_before_unlink(record: Path) -> None:
    handler = _Handler()
    handler.shutdown_finish.clear()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    clients = [await _connect(record) for _ in range(4)]
    extra = None
    try:
        await _until(lambda: len(endpoint._connections) == 4)
        extra = await _connect(record)
        async with asyncio.timeout(1):
            assert await asyncio.get_running_loop().sock_recv(extra, 1) == b""
        assert len(endpoint._connections) == 4 and handler.requests == []
        closing = asyncio.create_task(endpoint.close())
        await handler.shutdown_seen.wait()
        assert not closing.done() and (record.parent / "approval-test.sock").exists()
        # Close only the observer: owned teardown and four admitted tasks survive.
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert endpoint._close_task is not None and not endpoint._close_task.done()
        for peer in clients:
            peer.close()
        handler.shutdown_finish.set()
        assert await endpoint.close()
    finally:
        for peer in clients:
            peer.close()
        if extra is not None:
            extra.close()
        handler.shutdown_finish.set()
        await endpoint.close()


@pytest.mark.asyncio
async def test_client_disappearance_waits_for_observed_write_failure(record: Path) -> None:
    handler = _Handler()
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    begin = transport.host_exchange(record, _begin())
    try:
        assert (await anext(begin)).result == "accepted"
        await begin.aclose()
        await asyncio.sleep(0)
        assert handler.failed_writes == 0 and not handler.finish.is_set()
        assert len(endpoint._connections) == 1
        # The fake owner, not peer EOF, settles. Only the ensuing write may observe loss.
        handler.finish.set()
        await _until(lambda: not endpoint._connections)
        assert handler.failed_writes == 1
    finally:
        await begin.aclose()
        await endpoint.close()


@pytest.mark.asyncio
async def test_write_failure_requests_owner_cancel_and_retains_handler_lease(record: Path,
                                                                            monkeypatch) -> None:
    handler = _Handler()
    owner_cleanup = asyncio.Event()
    original = handler.responses

    async def retained(request):
        async for reply in original(request):
            yield reply
        await owner_cleanup.wait()

    handler.responses = retained
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)

    async def fail_write(_peer, _frame):
        raise OSError("SYNTHETIC_PRIVATE_EXCEPTION")

    monkeypatch.setattr(transport, "_write", fail_write)
    try:
        await asyncio.get_running_loop().sock_sendall(peer, encode_host_request(_begin()))
        peer.shutdown(socket.SHUT_WR)
        await _until(lambda: handler.failed_writes == 1)
        assert len(endpoint._connections) == 1
        owner_cleanup.set()
        await _until(lambda: not endpoint._connections)
        assert handler.failed_writes == 1
    finally:
        owner_cleanup.set()
        peer.close()
        await endpoint.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["notification", "ordering"])
@pytest.mark.parametrize("cancel_observer", [False, True])
async def test_exceptional_response_joins_finalizer_before_capacity_release(
        record: Path, monkeypatch, failure: str, cancel_observer: bool) -> None:
    handler = _Handler()
    cleanup_entered, cleanup_release = asyncio.Event(), asyncio.Event()
    logs: list[object] = []
    loop = asyncio.get_running_loop()
    previous_logger = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: logs.append(context))

    async def retained(request):
        handler.requests.append(request)
        try:
            yield HostResponse("accepted", _OP, timeout_ms=request.timeout_ms)
            yield HostResponse("completed", "2" * 32, state="cancelled")
        finally:
            cleanup_entered.set()
            await cleanup_release.wait()

    async def notify_failure(_request):
        handler.failed_writes += 1
        raise RuntimeError("SYNTHETIC_PRIVATE_EXCEPTION")

    native_write = transport._write

    async def selected_failure(peer, frame):
        if frame == encode_host_response(HostResponse("accepted", _OP, timeout_ms=30000)):
            raise OSError("SYNTHETIC_PRIVATE_EXCEPTION")
        await native_write(peer, frame)

    handler.responses = retained
    if failure == "notification":
        handler.write_failed = notify_failure
        monkeypatch.setattr(transport, "_write", selected_failure)
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)
    closing = None
    try:
        await loop.sock_sendall(peer, encode_host_request(_begin()))
        peer.shutdown(socket.SHUT_WR)
        await cleanup_entered.wait()
        connection = next(iter(endpoint._connections))
        if failure == "ordering":
            assert (await _reply(peer)).result == "accepted"
        else:
            assert handler.failed_writes == 1
        assert endpoint._begin_active and len(endpoint._connections) == 1
        if cancel_observer:
            connection.cancel()
            with pytest.raises(asyncio.CancelledError):
                await connection
            assert endpoint._begin_active and connection in endpoint._connections
        # A second begin must not enter the handler while its first finally waits.
        assert [reply async for reply in transport.host_exchange(record, _begin())] == [
            HostResponse("unavailable")
        ]
        assert len(handler.requests) == 1
        closing = asyncio.create_task(endpoint.close())
        await handler.shutdown_seen.wait()
        assert not closing.done() and (record.parent / "approval-test.sock").exists()
        assert endpoint._begin_active and connection in endpoint._connections
        cleanup_release.set()
        if cancel_observer:
            # A cancelled consumer is unknown to close; it cannot certify teardown.
            with pytest.raises(transport.HostTransportError):
                await closing
            assert (record.parent / "approval-test.sock").exists()
        else:
            assert await closing
            assert not (record.parent / "approval-test.sock").exists()
        await _until(lambda: connection not in endpoint._connections)
        assert not endpoint._begin_active and logs == []
    finally:
        cleanup_release.set()
        peer.close()
        if closing is not None:
            with contextlib.suppress(transport.HostTransportError):
                await closing
        loop.set_exception_handler(previous_logger)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["close", "iteration"])
async def test_unknown_finalizer_retires_generation_and_retains_sidecar(
        record: Path, failure: str) -> None:
    handler = _Handler()
    entered, release = asyncio.Event(), asyncio.Event()
    logs: list[object] = []
    loop = asyncio.get_running_loop()
    previous_logger = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: logs.append(context))

    async def retained(request):
        handler.requests.append(request)
        try:
            yield HostResponse("accepted", _OP, timeout_ms=request.timeout_ms)
            if failure == "iteration":
                await release.wait()
            else:
                yield HostResponse("completed", "2" * 32, state="cancelled")
        finally:
            entered.set()
            await release.wait()
            raise RuntimeError("SYNTHETIC_PRIVATE_EXCEPTION")

    handler.responses = retained
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    peer = await _connect(record)
    try:
        await loop.sock_sendall(peer, encode_host_request(_begin()))
        peer.shutdown(socket.SHUT_WR)
        assert (await _reply(peer)).result == "accepted"
        if failure == "close":
            await entered.wait()
            assert endpoint._begin_active
        release.set()
        await _until(lambda: endpoint._retired)
        assert endpoint._begin_active and len(endpoint._connections) == 1
        assert [reply async for reply in transport.host_exchange(record, _begin())] == [
            HostResponse("unavailable")
        ]
        assert len(handler.requests) == 1
        with pytest.raises(transport.HostTransportError) as caught:
            await endpoint.close()
        assert caught.value.args == ("approval test unavailable",)
        assert caught.value.__cause__ is None and caught.value.__context__ is None
        assert (record.parent / "approval-test.sock").exists() and logs == []
    finally:
        release.set()
        peer.close()
        loop.set_exception_handler(previous_logger)


@pytest.mark.asyncio
async def test_replaced_socket_inode_is_not_unlinked(record: Path) -> None:
    endpoint = transport.HostIpcEndpoint(record, _generation(), _Handler())
    endpoint.start()
    path = record.parent / "approval-test.sock"
    path.unlink()
    path.write_text("new-owner-context")
    assert await endpoint.close() is False
    assert path.read_text() == "new-owner-context"


@pytest.mark.asyncio
async def test_failed_owner_shutdown_retains_sidecar_and_has_fixed_error(record: Path) -> None:
    handler = _Handler()

    async def failure():
        raise RuntimeError("SYNTHETIC_PRIVATE_EXCEPTION")

    handler.shutdown = failure
    endpoint = transport.HostIpcEndpoint(record, _generation(), handler)
    endpoint.start()
    with pytest.raises(transport.HostTransportError) as caught:
        await endpoint.close()
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert (record.parent / "approval-test.sock").exists()


@pytest.mark.parametrize("replies", [
    [HostResponse("completed", _OP, state="cancelled")],
    [HostResponse("accepted", _OP, timeout_ms=1)],
    [HostResponse("accepted", _OP, timeout_ms=30000),
     HostResponse("completed", "2" * 32, state="cancelled")],
    [HostResponse("unavailable"), HostResponse("unavailable")],
])
def test_closed_response_order_refuses_invalid_contract(replies: list[HostResponse]) -> None:
    seen: list[HostResponse] = []
    with pytest.raises(transport.HostTransportError):
        for reply in replies:
            transport._reply_order(_begin(), seen, reply)
            seen.append(reply)


@pytest.mark.asyncio
async def test_client_checks_kernel_uid_before_sending(record: Path, monkeypatch) -> None:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    path = record.parent / "approval-test.sock"
    server.bind(str(path))
    path.chmod(0o600)
    server.listen(1)
    server.setblocking(False)
    monkeypatch.setattr(transport, "peer_uid", lambda _peer: os.getuid() + 1)
    client = asyncio.create_task(anext(transport.host_exchange(record, _begin())))
    peer = None
    try:
        peer, _ = await asyncio.get_running_loop().sock_accept(server)
        with pytest.raises(transport.HostTransportError) as caught:
            await client
        assert caught.value.__context__ is None and caught.value.__cause__ is None
        assert await asyncio.get_running_loop().sock_recv(peer, 1) == b""
    finally:
        if peer is not None:
            peer.close()
        server.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("frame", [
    b"\0\0\x10\x01", b"\0\0\0\0", b"\0\0\0\x02{}",
    encode_host_response(HostResponse("status", "2" * 32, state="pending", remaining_ms=1)),
])
async def test_client_refuses_bad_frame_or_id(record: Path, frame: bytes) -> None:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    path = record.parent / "approval-test.sock"
    server.bind(str(path))
    path.chmod(0o600)
    server.listen(1)
    server.setblocking(False)

    async def fake_peer():
        peer, _ = await asyncio.get_running_loop().sock_accept(server)
        try:
            await transport._request(peer, _generation())
            await asyncio.get_running_loop().sock_sendall(peer, frame)
        finally:
            peer.close()

    fake = asyncio.create_task(fake_peer())
    try:
        with pytest.raises(transport.HostTransportError) as caught:
            request = HostOperationRequest(_generation(), "status", _OP)
            _ = [r async for r in transport.host_exchange(record, request)]
        assert str(caught.value) == "approval test unavailable"
        assert caught.value.__context__ is None and caught.value.__cause__ is None
        await fake
    finally:
        server.close()


@pytest.mark.asyncio
async def test_client_does_not_publish_final_reply_before_eof(record: Path) -> None:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    path = record.parent / "approval-test.sock"
    server.bind(str(path))
    path.chmod(0o600)
    server.listen(1)
    server.setblocking(False)

    async def fake_peer():
        peer, _ = await asyncio.get_running_loop().sock_accept(server)
        try:
            await transport._request(peer, _generation())
            await asyncio.get_running_loop().sock_sendall(peer, unavailable_response_frame() + b"X")
        finally:
            peer.close()

    fake = asyncio.create_task(fake_peer())
    visible: list[HostResponse] = []
    try:
        with pytest.raises(transport.HostTransportError):
            async for reply in transport.host_exchange(record, _begin()):
                visible.append(reply)
        assert visible == []
        await fake
    finally:
        server.close()


def test_unavailable_frame_stays_exact_fixed_data() -> None:
    assert decode_host_response_frame(unavailable_response_frame()) == HostResponse("unavailable")
