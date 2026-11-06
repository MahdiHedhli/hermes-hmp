"""Real disposable socket exchange; channel/kernel/clock qualification MOCKED.

Synthetic keys only. No production startup, native authority, GO or host access.
"""

import asyncio
import hashlib
import os
import socket
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_broker_service import SocketChannel, StartupEnrollment
from hmp_plugin.presentation_clock import ClockDomain, NativeClockOwner
from hmp_plugin.presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles
from hmp_plugin.presentation_credential_handshake import (
    CredentialHandshakeOwner,
    HandshakeAcquisitionError,
)
from hmp_plugin.presentation_jobs import FrameError

_REAL_CHANNEL_CHECK = SocketChannel._check


@pytest.fixture
def pair(tmp_path, monkeypatch):
    private = {role: Ed25519PrivateKey.generate() for role in ("gateway", "broker")}
    public = {
        role: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        for role, key in private.items()
    }
    keys = {}
    for role in private:
        directory = tmp_path / role
        directory.mkdir(mode=0o700)
        peer = "broker" if role == "gateway" else "gateway"
        contents = {
            "own.seed": private[role].private_bytes(
                Encoding.Raw, PrivateFormat.Raw, NoEncryption()
            ),
            "own.pub": public[role],
            "peer.pub": public[peer],
        }
        for name, data in contents.items():
            fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        keys[role] = StartupRoleKeyFiles(
            RoleKeySelection(str(directory), role, "5" * 64, public[role], public[peer])
        )
    binding = BrokerBinding("a" * 52, "1" * 32, "2" * 64, "3" * 64, "4" * 64)
    socks = socket.socketpair()
    channels = {}
    clock = NativeClockOwner.__new__(NativeClockOwner)
    clock._domain_snapshot = ClockDomain(
        "darwin", "mach_absolute_time()", b"11111111-1111-1111-1111-111111111111", None
    )
    monkeypatch.setattr(SocketChannel, "_qualified_clock", lambda channel: clock)
    monkeypatch.setattr(SocketChannel, "_check", lambda channel: None)
    monkeypatch.setattr(NativeClockOwner, "sample", lambda owner: time.monotonic_ns())
    for role, sock in zip(("gateway", "broker"), socks, strict=True):
        sock.setblocking(False)
        channel = SocketChannel.__new__(SocketChannel)
        channel._socket_snapshot = sock
        enrollment = StartupEnrollment(
            binding, os.geteuid(), os.getpid(), os.geteuid(), os.getpid() + 1, "5" * 64, 2
        )
        channel._values_snapshot = enrollment.values()
        channel._identity_snapshot = (sock.fileno(), 1, 2, 3)
        channel._role_snapshot = role
        channel._reading = channel._writing = channel._refused = False
        channel._terminal_owner = channel._begin_write_intent = None
        channel._enrollment = channel._enrollment_snapshot = enrollment
        channels[role] = channel
    yield channels, keys, binding
    for sock in socks:
        sock.close()
    for key in keys.values():
        key.retire()


@pytest.mark.asyncio
async def test_bilateral_actual_socket_transcript_and_local_write_facts(pair):
    channels, keys, binding = pair
    owners = {}
    end = time.monotonic_ns() + 1_800_000_000

    async def actor(role):
        # Broker starts with its own accept end and no adopted native operation.
        owner = CredentialHandshakeOwner.retain(
            channels[role], keys[role], binding, end if role == "gateway" else end + 10_000_000
        )
        owners[role] = owner
        return await owner.run()

    gateway, broker = await asyncio.gather(actor("gateway"), actor("broker"))
    assert gateway == broker
    for owner in owners.values():
        assert owner._complete and len(owner._records) == 4
        assert len(owner._write_complete) == len(owner._write_intents) == 2
        assert owner._wire_bytes == sum(map(len, owner._records)) <= 8192
    assert owners["broker"]._end == end
    assert not hasattr(gateway, "authorized")


@pytest.mark.asyncio
async def test_key_retirement_after_write_prevents_completion_fact(pair, monkeypatch):
    channels, keys, binding = pair
    loop = asyncio.get_running_loop()
    send = loop.sock_sendall

    async def retiring(sock, raw):
        await send(sock, raw)
        keys["gateway"].retire()

    monkeypatch.setattr(loop, "sock_sendall", retiring)
    owner = CredentialHandshakeOwner.retain(
        channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
    )
    with pytest.raises(FrameError):
        await owner.run()
    assert owner._io_unknown and owner._refused and channels["gateway"]._refused
    assert len(owner._write_intents) == 1 and owner._write_complete == []
    with pytest.raises(FrameError):
        await owner.run()
    assert len(owner._write_intents) == 1


@pytest.mark.asyncio
async def test_failed_write_is_not_retried_and_reinit_cannot_replace_debt(pair, monkeypatch):
    channels, keys, binding = pair
    calls = []

    async def broken(sock, raw):
        calls.append(len(raw))
        raise ConnectionResetError("synthetic write uncertainty")

    monkeypatch.setattr(asyncio.get_running_loop(), "sock_sendall", broken)
    end = time.monotonic_ns() + 1_800_000_000
    owner = CredentialHandshakeOwner.retain(channels["gateway"], keys["gateway"], binding, end)
    with pytest.raises(ConnectionResetError):
        await owner.run()
    original = owner._write_intents
    with pytest.raises(HandshakeAcquisitionError):
        owner.__init__(channels["gateway"], keys["gateway"], binding, end)
    assert owner._write_intents is original and len(calls) == 1 and owner._io_unknown


@pytest.mark.asyncio
async def test_foreign_task_cannot_borrow_actor(pair):
    channels, keys, binding = pair
    owner = CredentialHandshakeOwner.retain(
        channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
    )
    with pytest.raises(FrameError):
        await asyncio.create_task(owner.run())
    assert owner._refused and owner._write_intents == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["retire", "cursor"])
async def test_final_clock_sample_reseal_prevents_signing_and_send(pair, monkeypatch, mutation):
    from hmp_plugin import presentation_credential_handshake as handshake

    channels, keys, binding = pair
    owner = CredentialHandshakeOwner.retain(
        channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
    )
    counts = {"sign_prepare": 0, "send": 0}

    def changed_clock(clock):
        if mutation == "retire":
            keys["gateway"].retire()
        else:
            owner._cursor = bytearray(b"foreign")
        return time.monotonic_ns()

    def forbidden_prepare(value):
        counts["sign_prepare"] += 1
        raise AssertionError("stale boundary must not prepare signing bytes")

    async def forbidden_send(sock, raw):
        counts["send"] += 1
        raise AssertionError("stale boundary must not send")

    monkeypatch.setattr(NativeClockOwner, "sample", changed_clock)
    monkeypatch.setattr(handshake, "signing_bytes", forbidden_prepare)
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_sendall", forbidden_send)
    with pytest.raises(FrameError):
        await owner.run()
    assert counts == {"sign_prepare": 0, "send": 0}
    assert owner._write_intents == [] and owner._release_fact is None


@pytest.mark.asyncio
async def test_constructor_first_sample_cannot_select_foreign_key_object(pair, monkeypatch):
    channels, keys, binding = pair

    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError("foreign selection attributes must not be followed")

    def changed_clock(clock):
        keys["gateway"]._selection = Foreign()
        return time.monotonic_ns()

    monkeypatch.setattr(NativeClockOwner, "sample", changed_clock)
    with pytest.raises(HandshakeAcquisitionError):
        CredentialHandshakeOwner.retain(
            channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
        )
    assert channels["gateway"]._credential_handshake._records == []


@pytest.mark.asyncio
async def test_partial_prefix_cancellation_keeps_cursor_and_channel_debt(pair, monkeypatch):
    channels, keys, binding = pair
    owners = []
    observed = asyncio.Event()
    loop = asyncio.get_running_loop()
    original_recv = loop.sock_recv

    async def observe_recv(sock, count):
        data = await original_recv(sock, count)
        if sock is channels["broker"]._socket_snapshot and data == b"HBA1\0":
            loop.call_soon(observed.set)  # actor retains bytes before this callback
        return data

    monkeypatch.setattr(loop, "sock_recv", observe_recv)

    async def broker():
        owner = CredentialHandshakeOwner.retain(
            channels["broker"], keys["broker"], binding, time.monotonic_ns() + 1_800_000_000
        )
        owners.append(owner)
        await owner.run()

    task = asyncio.create_task(broker())
    await asyncio.get_running_loop().sock_sendall(channels["gateway"]._socket_snapshot, b"HBA1\0")

    await asyncio.wait_for(observed.wait(), 1)
    assert owners and len(owners[0]._cursor) == 5
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    owner = owners[0]
    assert owner._io_unknown and bytes(owner._cursor) == b"HBA1\0" and owner._release_fact is None
    with pytest.raises(FrameError):
        channels["broker"]._credential_external_idle()


@pytest.mark.asyncio
async def test_real_channel_entry_guards_respect_original_handshake_claim(pair, monkeypatch):
    import shutil
    import tempfile

    from hmp_plugin import presentation_broker_service as service
    from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader
    from hmp_plugin.presentation_broker_endpoint import BrokerEndpointOwner

    _, keys, binding = pair
    root = tempfile.mkdtemp(prefix="hc-", dir="/private/tmp")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    gateway_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    accepted = None
    endpoint = None
    try:
        path = root + "/presentation.sock"
        listener.bind(path)
        os.chmod(path, 0o600)
        listener.listen(1)
        gateway_socket.connect(path)
        accepted, _ = listener.accept()
        endpoint = BrokerEndpointOwner(root, expected_uid=os.geteuid())
        observation = endpoint.observe()
        monkeypatch.setattr(SocketChannel, "_check", _REAL_CHANNEL_CHECK)
        monkeypatch.setattr(
            service,
            "observe_peer",
            lambda sock, expected_uid, expected_pid: service.PeerObservation(
                expected_uid, expected_pid
            ),
        )
        # Only native clock acquisition is mocked. SocketChannel initialization,
        # descriptor/endpoint bindings and external IO/close entry guards are real.
        monkeypatch.setattr(NativeClockOwner, "__init__", lambda owner, channel: None)
        enrollment = service.StartupEnrollment(
            binding, os.geteuid(), os.getpid(), os.geteuid(), os.getpid() + 1, "5" * 64, 2
        )
        channel = SocketChannel(
            gateway_socket, enrollment, role="gateway", endpoint=endpoint, observation=observation
        )
        owner = CredentialHandshakeOwner.retain(
            channel, keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
        )
        with pytest.raises(FrameError):
            await channel.receive(time.monotonic_ns() + 1_000_000_000, expected=binding)
        frame = BrokerFrame(BrokerHeader(binding, "BEGIN", 0, 4, 2), b"data")
        with pytest.raises(FrameError):
            await channel.send(frame, time.monotonic_ns() + 1_000_000_000)
        assert channel._pre_result_cursor is None and channel._begin_write_intent is None
        assert channel.close_clock() is False

        def forbidden_close(sock):
            raise AssertionError("active claim must refuse before native socket close")

        monkeypatch.setattr(service, "_SOCKET_CLOSE", forbidden_close)
        assert channel.close() is False
        assert gateway_socket.fileno() >= 0 and owner._release_fact is None
    finally:
        gateway_socket.close()
        if accepted is not None:
            accepted.close()
        listener.close()
        if endpoint is not None:
            assert endpoint.close()
        shutil.rmtree(root)


@pytest.mark.asyncio
async def test_authenticated_hello_final_sample_cannot_adopt_foreign_end(pair, monkeypatch):
    from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes

    channels, keys, binding = pair
    owner = CredentialHandshakeOwner.retain(
        channels["broker"], keys["broker"], binding, time.monotonic_ns() + 1_800_000_000
    )
    original_end, original_common = owner._end, owner._common_values
    callback_calls = []

    class Foreign:
        def __eq__(self, other):
            callback_calls.append("equality")
            raise AssertionError("foreign end must be rejected before comparison")

        def __lt__(self, other):
            callback_calls.append("ordering")
            raise AssertionError("foreign end must be rejected before min")

    selected = keys["gateway"]._selection
    value = dict(
        owner._common,
        v=1,
        family="handshake",
        alg="Ed25519",
        phase="HELLO",
        role="gateway",
        direction="g2b",
        key_id=hashlib.sha256(selected.own_public).hexdigest(),
        peer_key_id=hashlib.sha256(selected.peer_public).hexdigest(),
        gateway_boot=keys["gateway"]._boot,
        gateway_nonce="e" * 64,
    )
    value["operation_id"] = "6" * 64
    raw = encode_record(value, keys["gateway"]._private_key.sign(signing_bytes(value)))
    boundary_samples = 0

    def boundary(clock):
        nonlocal boundary_samples
        if len(owner._cursor) == len(raw) and not owner._records:
            boundary_samples += 1
            if boundary_samples == 2:
                owner._common["work_end_ns"] = Foreign()
        return time.monotonic_ns()

    monkeypatch.setattr(NativeClockOwner, "sample", boundary)
    await asyncio.get_running_loop().sock_sendall(channels["gateway"]._socket_snapshot, raw)
    with pytest.raises(FrameError):
        await owner.run()
    assert boundary_samples == 2 and callback_calls == []
    assert owner._end == original_end and owner._common_values == original_common
    assert owner._records == [] and owner._write_intents == []
    assert owner._common["operation_id"] == binding.operation


@pytest.mark.asyncio
async def test_foreign_binding_getters_are_not_followed(pair):
    channels, keys, _ = pair

    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError("foreign binding attributes must not be followed")

    with pytest.raises(HandshakeAcquisitionError):
        CredentialHandshakeOwner.retain(
            channels["gateway"], keys["gateway"], Foreign(), time.monotonic_ns() + 1_800_000_000
        )


@pytest.mark.asyncio
async def test_paired_current_channel_retarget_poisons_only_original(pair, monkeypatch):
    channels, keys, binding = pair
    original, borrowed = channels["gateway"], channels["broker"]
    owner = CredentialHandshakeOwner.retain(
        original, keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
    )

    def retarget(clock):
        owner._channel = borrowed
        borrowed._credential_handshake = borrowed._credential_handshake_snapshot = owner
        return time.monotonic_ns()

    monkeypatch.setattr(NativeClockOwner, "sample", retarget)
    with pytest.raises(FrameError):
        await owner.run()
    assert original._refused is True and borrowed._refused is False
    assert borrowed._socket_snapshot.fileno() >= 0 and owner._write_intents == []
    with pytest.raises(FrameError):
        borrowed._credential_external_idle()


@pytest.mark.asyncio
async def test_constructor_clock_boundary_rejects_foreign_boot_before_equality(pair, monkeypatch):
    channels, keys, binding = pair
    callbacks = []

    class Foreign:
        def __eq__(self, other):
            callbacks.append("equality")
            raise AssertionError("foreign boot must not reach equality")

    def altered(clock):
        object.__setattr__(clock._domain_snapshot, "boot", Foreign())
        return time.monotonic_ns()

    monkeypatch.setattr(NativeClockOwner, "sample", altered)
    with pytest.raises(HandshakeAcquisitionError):
        CredentialHandshakeOwner.retain(
            channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
        )
    assert callbacks == []


@pytest.mark.asyncio
async def test_final_clock_boundary_rejects_foreign_scope_without_getters(pair, monkeypatch):
    channels, keys, binding = pair
    owner = CredentialHandshakeOwner.retain(
        channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
    )
    callbacks = []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign scope must not receive getters")

    def altered(clock):
        object.__setattr__(channels["gateway"]._enrollment, "scope", Foreign())
        return time.monotonic_ns()

    monkeypatch.setattr(NativeClockOwner, "sample", altered)
    with pytest.raises(FrameError):
        await owner.run()
    assert callbacks == [] and owner._write_intents == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["snapshot", "clock_value"])
async def test_constructor_rejects_foreign_snapshot_or_time_before_comparison(
    pair, monkeypatch, mutation
):
    channels, keys, binding = pair
    callbacks = []

    class Foreign:
        def __eq__(self, other):
            callbacks.append("equality")
            raise AssertionError("foreign snapshot must not reach equality")

        def __lt__(self, other):
            callbacks.append("ordering")
            raise AssertionError("foreign time must not reach ordering")

    def altered(clock):
        if mutation == "snapshot":
            channels["gateway"]._credential_handshake._domain_values = Foreign()
            return time.monotonic_ns()
        return Foreign()

    monkeypatch.setattr(NativeClockOwner, "sample", altered)
    with pytest.raises(HandshakeAcquisitionError):
        CredentialHandshakeOwner.retain(
            channels["gateway"], keys["gateway"], binding, time.monotonic_ns() + 1_800_000_000
        )
    assert callbacks == []
