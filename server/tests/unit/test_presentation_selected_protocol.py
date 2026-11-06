"""Selected v2 channel/clock ownership; no v2 broker work or cancellation gate.

The shared local model explicitly mocks peer identity and Darwin clock facts.
Actual native selected-channel evidence is in the separate exact-helper test.
"""

import asyncio
import os
import time
from dataclasses import replace

import pytest
import pytest_asyncio

from hmp_plugin import presentation_broker_service as service
from hmp_plugin import presentation_clock as clock
from hmp_plugin.presentation_broker_codec import (
    BrokerFrame,
    BrokerHeader,
    decode_frame,
    decode_header,
    encode_frame,
    header_size,
)
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import binding as fresh_binding
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_terminal_status import gateway as gateway

_BINDING = fresh_binding()


def binding():
    return _BINDING


async def read_v2(sock):
    async def exact(count):
        data = bytearray()
        while len(data) < count:
            part = await asyncio.get_running_loop().sock_recv(sock, count - len(data))
            assert part
            data.extend(part)
        return bytes(data)
    async def receive():
        prefix = await exact(8)
        raw = prefix + await exact(header_size(prefix))
        header = decode_header(raw, expected=binding(), expected_version=2)
        return decode_frame(raw + await exact(header.body_length), expected=binding(),
                            expected_version=2)
    return await asyncio.wait_for(receive(), 1)


@pytest_asyncio.fixture
async def v2gateway(local, monkeypatch):
    spine, e, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    remote, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    remote.setblocking(False)
    enrollment = replace(e, gateway_pid=os.getpid(), service_pid=os.getpid() + 1,
                         protocol_version=2)
    channel = service.SocketChannel(sock, enrollment, role="gateway", endpoint=spine._endpoint,
                                    observation=spine._observation)
    try:
        yield channel, remote, spine
    finally:
        assert channel.close()
        assert channel.close_clock()
        sock.close()
        remote.close()
        assert await spine.stop_local_sockets()


@pytest.mark.parametrize("version", [True, 0, 3, 2.0, "2", None])
def test_startup_protocol_selection_is_exact_and_closed(version):
    e = service.StartupEnrollment(binding(), 501, 100, 501, 101, "e" * 64, version)
    with pytest.raises(FrameError):
        e.values()


def test_default_and_selected_protocol_are_part_of_immutable_enrollment_values():
    e = service.StartupEnrollment(binding(), 501, 100, 501, 101, "e" * 64)
    assert len(e.values()) == 9 and e.values()[-1] == 1
    assert replace(e, protocol_version=2).values()[-1] == 2
    assert service._values_shape(e.values()) and not service._values_shape(e.values()[:-1])


@pytest.mark.asyncio
async def test_selected_v2_retains_real_clock_owner_and_correlates_frames(v2gateway):
    channel, remote, _ = v2gateway
    owner = channel._clock_owner
    try:
        assert type(owner) is clock.NativeClockOwner
        assert owner is channel._clock_owner_snapshot and owner._channel is channel
        assert type(owner._qualification) is object
        end = time.monotonic_ns() + 1_000_000_000
        frame = BrokerFrame(BrokerHeader(binding(), "BEGIN", 0, 4, 2), b"data")
        await channel.send(frame, end)
        assert await read_v2(remote) == frame
        await asyncio.get_running_loop().sock_sendall(
            remote, encode_frame(binding(), "READY", 0, version=2))
        ready = await channel.receive(end, expected=binding())
        assert ready.header.version == 2 and ready.header.kind == "READY"
        assert channel.close()
        assert owner._closed_known is False  # socket and clock-FD facts are separate
        assert channel.close_clock() and owner._closed_known is True
        assert channel.close_clock()
    finally:
        channel.close()
        assert channel.close_clock()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["CANCEL", "GO", "RESULT", "STATUS", "ACK", "CLOSED"])
async def test_v2_selection_cannot_open_unjoined_lifecycle(v2gateway, kind):
    channel, _, _ = v2gateway
    body = b"x" * 16 if kind == "CANCEL" else b"data" if kind == "RESULT" else b""
    try:
        with pytest.raises(FrameError):
            await channel.send(BrokerFrame(BrokerHeader(binding(), kind, 1, len(body), 2), body),
                               time.monotonic_ns() + 1_000_000_000)
    finally:
        assert channel.close()
        assert channel.close_clock()


@pytest.mark.asyncio
async def test_selected_v2_never_downgrades_incoming_v1(v2gateway):
    channel, remote, _ = v2gateway
    try:
        await asyncio.get_running_loop().sock_sendall(remote, encode_frame(binding(), "READY", 0))
        with pytest.raises(FrameError):
            await channel.receive(time.monotonic_ns() + 1_000_000_000, expected=binding())
    finally:
        assert channel.close()
        assert channel.close_clock()


@pytest.mark.asyncio
async def test_legacy_channel_rejects_v2_without_acquiring_clock(gateway):
    channel, remote, _ = gateway
    assert channel._clock_owner is None
    await asyncio.get_running_loop().sock_sendall(
        remote, encode_frame(binding(), "READY", 0, version=2))
    with pytest.raises(FrameError):
        await channel.receive(time.monotonic_ns() + 1_000_000_000, expected=binding())
    assert channel._clock_owner is None


@pytest.mark.asyncio
async def test_partial_clock_is_retained_before_initialization_and_admits_no_frames(
    local, monkeypatch
):
    spine, e, client, _, _, _ = local
    sock = client()
    remote, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    remote.setblocking(False)
    retained = []
    def fail(self, channel):
        assert channel._clock_owner is self and channel._clock_owner_snapshot is self
        retained.append(self)
        raise FrameError("synthetic clock initialization failure")
    monkeypatch.setattr(clock.NativeClockOwner, "__init__", fail)
    with pytest.raises(service.ChannelAcquisitionError) as error:
        service.SocketChannel(sock, replace(e, gateway_pid=os.getpid(),
            service_pid=os.getpid() + 1, protocol_version=2),
            role="gateway", endpoint=spine._endpoint, observation=spine._observation)
    partial = error.value.failed_owner
    assert retained == [partial._clock_owner]
    with pytest.raises(FrameError):
        await partial.send(BrokerFrame(BrokerHeader(binding(), "BEGIN", 0, 4, 2), b"data"),
                           time.monotonic_ns() + 1_000_000_000)
    assert partial.close()
    assert partial.close_clock() is False  # not a fabricated empty clock owner
    remote.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_selected_service_refuses_v2_status_before_registry_effect(local, monkeypatch):
    spine, _, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    await asyncio.get_running_loop().sock_sendall(
        sock, encode_frame(binding(), "STATUS", 0, version=2))
    with pytest.raises(FrameError):
        await spine.serve_once(time.monotonic_ns() + 1_000_000_000)
    assert spine._registry.counts.active == 0 and not spine._records
    assert await spine.stop_local_sockets()


@pytest.mark.asyncio
async def test_selected_clock_instance_methods_cannot_replace_native_boundaries(
    v2gateway, monkeypatch
):
    channel, _, _ = v2gateway
    owner = channel._clock_owner
    def bypass():
        pytest.fail("mutable instance method must not supply qualification or closure")
    monkeypatch.setattr(owner, "sample", bypass)
    monkeypatch.setattr(owner, "close_local", bypass)
    before = owner._last_ns
    assert channel._remaining(time.monotonic_ns() + 1_000_000_000) > 0
    assert owner._last_ns >= before
    assert channel.close()
    assert channel.close_clock()
    assert owner._closed_known


@pytest.mark.asyncio
async def test_framing_cannot_use_constant_instance_sample_after_domain_poison(
    v2gateway, monkeypatch
):
    channel, _, _ = v2gateway
    owner = channel._clock_owner
    monkeypatch.setattr(owner, "sample", lambda: time.monotonic_ns())
    owner._local_lost = True
    with pytest.raises(FrameError):
        await channel.send(BrokerFrame(BrokerHeader(binding(), "BEGIN", 0, 4, 2), b"data"),
                           time.monotonic_ns() + 1_000_000_000)
    assert owner._local_lost
