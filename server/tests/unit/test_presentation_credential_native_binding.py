"""Actual policy thread/job ledger and sockets; synthetic native/peer/clock model.

No live Hermes home, production factory, worker GO, provider or user contents.
"""
import asyncio
import os
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

from hmp_plugin.presentation_broker_service import SocketChannel
from hmp_plugin.presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_jobs import FrameError, RemotePhase, State
from hmp_plugin.presentation_authority import AuthorityRefusalError

from .test_presentation_supervisor import context as context
from .test_presentation_broker_service import local as local
from .test_presentation_selected_protocol import v2gateway as v2gateway
from .test_presentation_remote import prepare


def key_pair(tmp_path, generation):
    private = {role: Ed25519PrivateKey.generate() for role in ("gateway", "broker")}
    public = {role: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) for role, key in private.items()}
    owners = {}
    for role in private:
        peer = "broker" if role == "gateway" else "gateway"
        directory = tmp_path / role
        directory.mkdir(mode=0o700)
        values = {"own.seed": private[role].private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
                  "own.pub": public[role], "peer.pub": public[peer]}
        for name, data in values.items():
            fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        owners[role] = StartupRoleKeyFiles(RoleKeySelection(str(directory), role, generation,
                                                          public[role], public[peer]))
    return owners


async def handshake(prepared, tmp_path):
    authority, operation, _, channel, peer, _, _, binding = prepared
    keys = key_pair(tmp_path, channel._enrollment.installation_generation)
    broker = SocketChannel(peer, replace(channel._enrollment, gateway_pid=os.getpid() + 1,
        service_pid=os.getpid()), role="broker", endpoint=channel._endpoint,
        observation=channel._observation)
    end = int(authority._record(operation).deadline * 1_000_000_000)
    async def receiver():
        owner = CredentialHandshakeOwner.retain(broker, keys["broker"], binding, end)
        await owner.run()
        return owner
    task = asyncio.create_task(receiver())
    try:
        owner = CredentialHandshakeOwner.retain(channel, keys["gateway"], binding, end)
        await owner.run()
        await task
        return owner, keys, broker
    except BaseException:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise


@pytest.mark.asyncio
async def test_handshake_binds_exact_native_packet_and_original_shared_slot(context, v2gateway, tmp_path):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        remote = authority.bind_remote(operation, channel, binding, packet)
        fact = remote._credential_binding
        assert fact is owner._native_input is owner._native_input_snapshot
        assert fact.remote is remote and fact.packet is packet and fact.binding is binding
        assert fact.scope == derive_input_scope(packet, binding)
        record = authority._record(operation)
        assert record.remote_operation is remote
        assert record.owner.inspect_remote(record.handle) is RemotePhase.BOUND
        assert record.owner.inspect(record.handle)[0] is State.STARTING
        # This join grants no unsigned fallback while phase integration is open.
        with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
            await channel.send_go(remote)
        # The existing cleanup owner may conservatively surface authority
        # refusal after the transport gate poisons work; both must retain debt.
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        assert remote._failed and record.remote_operation is remote
        assert record.owner.inspect(record.handle)[0] is State.UNKNOWN
        assert channel._begin_write_intent is None
        assert remote._go_admission is None and record.child is None
        try:
            received = peer.recv(1)
        except BlockingIOError:
            received = b""
        assert received == b""  # no application bytes; cleanup may half-close
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["packet_copy", "channel"])
async def test_completed_handshake_cannot_repair_wrong_native_binding(context, v2gateway, tmp_path, mutation):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, _, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        if mutation == "packet_copy":
            packet = bytes(bytearray(packet))
        else:
            binding = replace(binding, channel="f" * 64)
        with pytest.raises((AuthorityRefusalError, FrameError)):
            authority.bind_remote(operation, channel, binding, packet)
        record = authority._record(operation)
        assert record.remote_operation is not None and record.remote_operation._failed
        assert owner._native_input is None and record.child is None
        assert record.owner.inspect(record.handle)[0] is State.UNKNOWN
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("retirement", ["key", "listener"])
async def test_handshake_completion_cannot_override_current_retirement(context, v2gateway, tmp_path, retirement):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, _, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        if retirement == "key":
            keys["gateway"].retire()
        else:
            authority._record(operation).fence.retire()
        with pytest.raises((AuthorityRefusalError, FrameError)):
            authority.bind_remote(operation, channel, binding, packet)
        record = authority._record(operation)
        assert record.remote_operation is not None and record.remote_operation._failed
        assert record.child is None and owner._native_input is None
        # The same original native slot remains occupied; no repair/retry.
        retained = record.remote_operation
        with pytest.raises(AuthorityRefusalError):
            authority.bind_remote(operation, channel, binding, packet)
        assert record.remote_operation is retained
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["joined", "invalid", "fence", "epoch"])
async def test_final_native_current_mutation_cannot_mint_join(context, v2gateway, tmp_path, monkeypatch, mutation):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, _, work, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        current = authority._current
        calls = 0
        callbacks = []
        class Foreign:
            def __bool__(self):
                callbacks.append("truthiness")
                raise AssertionError("foreign joined flag must not be truth-tested")
        def changed(record):
            nonlocal calls
            result = current(record)
            if owner._native_input_attempted and owner._native_input is None:
                calls += 1
                if calls == 2:
                    if mutation == "joined":
                        work._thread.joined = Foreign()
                    elif mutation == "invalid":
                        work._invalid = True
                    elif mutation == "fence":
                        record.fence.retire()
                    else:
                        record.owner._epoch += 1
                        object.__setattr__(record.lease, "epoch", record.owner._epoch)
            return result
        monkeypatch.setattr(authority, "_current", changed)
        with pytest.raises((AuthorityRefusalError, FrameError)):
            authority.bind_remote(operation, channel, binding, packet)
        assert calls == 2 and callbacks == [] and owner._native_input is None
        record = authority._record(operation)
        assert record.remote_operation is not None and record.remote_operation._failed
        assert record.child is None and channel._begin_write_intent is None
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()
