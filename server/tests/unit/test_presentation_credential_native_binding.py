"""Actual policy thread/job ledger and sockets; synthetic native/peer/clock model.

No live Hermes home, production factory, worker GO, provider or user contents.
"""

import asyncio
import json
import os
from dataclasses import replace

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_service import SocketChannel
from hmp_plugin.presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_jobs import FrameError, RemotePhase, State

from .test_presentation_broker_service import local as local
from .test_presentation_remote import prepare
from .test_presentation_selected_protocol import v2gateway as v2gateway
from .test_presentation_supervisor import context as context


def key_pair(tmp_path, generation):
    private = {role: Ed25519PrivateKey.generate() for role in ("gateway", "broker")}
    public = {
        role: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        for role, key in private.items()
    }
    owners = {}
    for role in private:
        peer = "broker" if role == "gateway" else "gateway"
        directory = tmp_path / role
        directory.mkdir(mode=0o700)
        values = {
            "own.seed": private[role].private_bytes(
                Encoding.Raw, PrivateFormat.Raw, NoEncryption()
            ),
            "own.pub": public[role],
            "peer.pub": public[peer],
        }
        for name, data in values.items():
            fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        owners[role] = StartupRoleKeyFiles(
            RoleKeySelection(str(directory), role, generation, public[role], public[peer])
        )
    return owners


async def handshake(prepared, tmp_path):
    authority, operation, _, channel, peer, _, _, binding = prepared
    keys = key_pair(tmp_path, channel._enrollment.installation_generation)
    broker = SocketChannel(
        peer,
        replace(channel._enrollment, gateway_pid=os.getpid() + 1, service_pid=os.getpid()),
        role="broker",
        endpoint=channel._endpoint,
        observation=channel._observation,
    )
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
async def test_handshake_binds_exact_native_packet_and_original_shared_slot(
    context, v2gateway, tmp_path, monkeypatch
):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        remote = authority.bind_remote(operation, channel, binding, packet)
        from hmp_plugin.presentation_result_transport import RemoteResultOwner

        with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
            RemoteResultOwner.retain(remote)
        assert remote._result_owner is None and remote._result_owner_snapshot is None
        assert remote._job_origin_snapshot._remote_candidate_custody_origin is None
        assert remote._job_origin_snapshot._remote_candidate_custody_snapshot is None
        fact = remote._credential_binding
        assert fact is owner._native_input is owner._native_input_snapshot
        assert fact.remote is remote and fact.packet is packet and fact.binding is binding
        assert fact.scope == derive_input_scope(packet, binding)
        record = authority._record(operation)
        assert record.remote_operation is remote
        assert record.owner.inspect_remote(record.handle) is RemotePhase.BOUND
        assert record.owner.inspect(record.handle)[0] is State.STARTING
        # Caller has no work-task authority, even with the original remote.
        with pytest.raises(FrameError):
            channel._reserve_credential_begin(remote)
        assert channel._begin_write_intent is None and remote._send_claimed is False
        original_reserve = SocketChannel._reserve_credential_begin
        observed_intents = []

        def observed_reserve(owned_channel, owned_remote):
            intent = original_reserve(owned_channel, owned_remote)
            cleanup = owned_remote._cleanup_owner_snapshot
            assert asyncio.current_task() is cleanup._allocations_snapshot[1].task
            assert asyncio.current_task() is not cleanup._caller_snapshot
            assert cleanup._caller_snapshot is owner._task
            assert owned_channel._writing is False and owned_channel._begin_write_fact is None
            with pytest.raises(FrameError):
                original_reserve(owned_channel, owned_remote)
            assert owned_channel._begin_write_intent is intent
            observed_intents.append(intent)
            return intent

        monkeypatch.setattr(SocketChannel, "_reserve_credential_begin", observed_reserve)
        from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner

        original_init = NativePhaseWorkOwner.__init__
        original_prepare = NativePhaseWorkOwner.prepare_begin
        signed_records = []
        caller_refusals = []

        def observed_init(producer, cleanup):
            original_init(producer, cleanup)
            assert asyncio.current_task() is cleanup._caller_snapshot
            with pytest.raises(FrameError):
                NativePhaseWorkOwner._guard(producer)
            assert producer._attempted is False
            caller_refusals.append(True)

        def observed_prepare(producer):
            cleanup = producer._cleanup
            assert asyncio.current_task() is cleanup._allocations_snapshot[1].task
            raw = original_prepare(producer)
            with pytest.raises(FrameError):
                original_prepare(producer)
            assert producer._record_snapshot is raw
            signed_records.append(raw)
            return raw

        monkeypatch.setattr(NativePhaseWorkOwner, "__init__", observed_init)
        monkeypatch.setattr(NativePhaseWorkOwner, "prepare_begin", observed_prepare)
        async def stop_after_preparation(producer):
            raise FrameError("SYNTHETIC_PREPARATION_ONLY_NO_IO")
        monkeypatch.setattr(NativePhaseWorkOwner, "exchange_ready", stop_after_preparation)
        # This join grants no unsigned fallback while phase integration is open.
        with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
            await channel.send_go(remote)
        # The existing cleanup owner may conservatively surface authority
        # refusal after the transport gate poisons work; both must retain debt.
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        assert remote._failed and record.remote_operation is remote
        assert record.owner.inspect(record.handle)[0] is State.UNKNOWN
        intent = channel._begin_write_intent
        assert observed_intents == [intent]
        producer = remote._cleanup_owner_snapshot._credential_work_snapshot
        raw = producer._record_snapshot
        assert type(raw) is bytes and producer._record is raw
        assert signed_records == [raw] and caller_refusals == [True]
        from hmp_plugin.presentation_broker_codec import encode_frame
        from hmp_plugin.presentation_credential_codec import decode_record
        from hmp_plugin.presentation_credential_phase import check_commitment, check_complete_frame

        claim = json.loads(decode_record(raw).canonical_json)
        expected = {
            key: value
            for key, value in claim.items()
            if key
            not in ("v", "family", "alg", "key_id", "peer_key_id", "frame_sha256", "frame_length")
        }
        checked = check_commitment(
            raw,
            sender_public=keys["gateway"]._selection.own_public,
            receiver_public=keys["gateway"]._selection.peer_public,
            expected=expected,
        )
        check_complete_frame(
            checked, encode_frame(binding, "BEGIN", 0, packet, version=2), binding=binding
        )
        assert claim["input_sha256"] == fact.scope.input_sha256
        assert claim["scope_sha256"] == fact.scope.scope_sha256
        assert claim["work_end_ns"] == remote._end_snapshot
        assert intent is channel._begin_write_intent_snapshot
        assert intent.remote is remote and intent.packet is packet and intent.binding is binding
        assert intent.end_ns == remote._end_snapshot and intent.version == 2
        assert channel._writing is False and channel._begin_write_fact is None
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
async def test_completed_handshake_cannot_repair_wrong_native_binding(
    context, v2gateway, tmp_path, mutation
):
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
async def test_handshake_completion_cannot_override_current_retirement(
    context, v2gateway, tmp_path, retirement
):
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
async def test_final_native_current_mutation_cannot_mint_join(
    context, v2gateway, tmp_path, monkeypatch, mutation
):
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


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["fence", "policy", "packet"])
async def test_begin_reservation_rechecks_after_native_admission(
    context, v2gateway, tmp_path, monkeypatch, mutation
):
    from hmp_plugin.presentation_remote import RemoteOperationOwner

    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        binding = owner._operation_binding()
        remote = authority.bind_remote(operation, channel, binding, packet)
        original = RemoteOperationOwner._authorize_channel
        admissions = []

        def changed(owned, owned_channel, direction, scope, end, frame):
            original(owned, owned_channel, direction, scope, end, frame)
            admissions.append(direction)
            if mutation == "fence":
                owned._record_snapshot.fence.retire()
            elif mutation == "policy":
                owned._record_snapshot.policy_work._invalid = True
            else:
                owned._record_snapshot.policy_work._packet = bytes(bytearray(packet))

        monkeypatch.setattr(RemoteOperationOwner, "_authorize_channel", changed)
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        assert admissions == ["send"]
        assert remote._send_claimed is True and remote._send_completed is False
        assert channel._begin_write_intent is None
        assert channel._begin_write_intent_snapshot is None
        assert channel._begin_write_fact is None and channel._writing is False
        record = authority._record(operation)
        assert record.remote_operation is remote and record.child is None
        assert record.owner.inspect(record.handle)[0] is State.UNKNOWN
        try:
            received = peer.recv(1)
        except BlockingIOError:
            received = b""
        assert received == b""
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["key", "fence", "policy"])
async def test_signing_postcheck_withholds_record_after_retirement(
    context, v2gateway, tmp_path, monkeypatch, mutation
):
    from hmp_plugin import presentation_credential_work as signing

    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        remote = authority.bind_remote(operation, channel, owner._operation_binding(), packet)
        original = signing.encode_record
        signatures = []

        def retired(statement, signature):
            raw = original(statement, signature)
            signatures.append(raw)
            if mutation == "key":
                keys["gateway"].retire()
            elif mutation == "fence":
                authority._record(operation).fence.retire()
            else:
                authority._record(operation).policy_work._invalid = True
            return raw

        monkeypatch.setattr(signing, "encode_record", retired)
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        producer = remote._cleanup_owner_snapshot._credential_work_snapshot
        assert len(signatures) == 1 and producer._attempted is True and producer._failed is True
        assert producer._record is None and producer._record_snapshot is None
        assert channel._begin_write_intent is not None
        assert channel._begin_write_fact is None and channel._writing is False
        assert remote._send_claimed is True and remote._send_completed is False
        record = authority._record(operation)
        assert record.remote_operation is remote and record.child is None
        assert record.owner.inspect(record.handle)[0] is State.UNKNOWN
        with pytest.raises(FrameError):
            producer.prepare_begin()
        assert len(signatures) == 1
        try:
            received = peer.recv(1)
        except BlockingIOError:
            received = b""
        assert received == b""
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


def test_work_producer_rejects_foreign_receiver_before_getters():
    from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner

    callbacks = []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign receiver getter")

    with pytest.raises(FrameError):
        NativePhaseWorkOwner.prepare_begin(Foreign())
    assert callbacks == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["key", "transcript"])
async def test_preparation_retirement_refused_before_signature_encoding(
    context, v2gateway, tmp_path, monkeypatch, mutation
):
    from hmp_plugin import presentation_credential_work as signing

    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, _, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    try:
        remote = authority.bind_remote(operation, channel, owner._operation_binding(), packet)
        original = signing.signing_bytes
        prepared_statements = []
        encoded = []

        def changed(statement):
            raw = original(statement)
            prepared_statements.append(raw)
            if mutation == "key":
                keys["gateway"].retire()
            else:
                object.__setattr__(owner._transcript_snapshot, "channel", "f" * 64)
            return raw

        def forbidden_encoding(*args):
            encoded.append(args)
            raise AssertionError("retired preparation must not reach signature encoding")

        monkeypatch.setattr(signing, "signing_bytes", changed)
        monkeypatch.setattr(signing, "encode_record", forbidden_encoding)
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        producer = remote._cleanup_owner_snapshot._credential_work_snapshot
        assert len(prepared_statements) == 1 and encoded == []
        assert producer._failed is True and producer._record is None
        assert channel._begin_write_fact is None and remote._send_completed is False
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["allocation", "refs"])
async def test_constructor_rechecks_allocation_after_handshake_clock_boundary(
    context, v2gateway, tmp_path, monkeypatch, mutation
):
    prepared = await prepare(context, v2gateway)
    authority, operation, _, channel, _, _, packet, _ = prepared
    owner, keys, broker = await handshake(prepared, tmp_path)
    original_guard = CredentialHandshakeOwner._guard
    callbacks = []
    retained = []

    class Foreign:
        def __getitem__(self, index):
            callbacks.append(index)
            raise AssertionError("foreign allocation indexing")

    try:
        remote = authority.bind_remote(operation, channel, owner._operation_binding(), packet)

        def changed(owned):
            original_guard(owned)
            cleanup = remote._cleanup_owner_snapshot
            if cleanup is not None and cleanup._initialized is True and not retained:
                producer = cleanup._credential_work_snapshot
                if mutation == "allocation":
                    retained.append(cleanup._allocations_snapshot)
                    cleanup._allocations = cleanup._allocations_snapshot = Foreign()
                elif hasattr(producer, "_refs_snapshot"):
                    retained.append(cleanup._allocations_snapshot)
                    producer._refs = Foreign()

        monkeypatch.setattr(CredentialHandshakeOwner, "_guard", changed)
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        cleanup = remote._cleanup_owner_snapshot
        assert len(retained) == 1 and callbacks == []
        assert cleanup._credential_work_snapshot._ready is False
        assert cleanup._start_snapshot.result() is False
        assert cleanup._unknown is True and channel._begin_write_intent is None
        # Restore only fixture allocation metadata after closed failure barriers;
        # no work, signature or authority acquisition is retried.
        cleanup._allocations = cleanup._allocations_snapshot = retained[0]
        await asyncio.gather(
            *(allocation.task for allocation in retained[0]), return_exceptions=True
        )
    finally:
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


@pytest_asyncio.fixture
async def begin_gateway(local, monkeypatch):
    from hmp_plugin.presentation_clock import NativeClockOwner

    from .test_presentation_selected_protocol import darwin_model

    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    sock = client()
    peer, _ = await asyncio.get_running_loop().sock_accept(spine._listener)
    peer.setblocking(False)
    channel = SocketChannel(sock, replace(enrollment, gateway_pid=os.getpid(),
        service_pid=os.getpid() + 1, protocol_version=2), role="gateway",
        endpoint=spine._endpoint, observation=spine._observation)
    try:
        yield channel, peer, spine
    finally:
        writer = channel._credential_begin_writer_snapshot
        reader = channel._credential_ready_receiver_snapshot
        transition = None if reader is None else reader._transition_snapshot
        go_writer = channel._credential_go_writer_snapshot
        release_drift = False
        if go_writer is not None:
            go_base = go_writer._scope_snapshot.signed_scope.ready_scope.read_scope.write_scope
            release_drift = (go_base.remote._cleanup_owner_snapshot is not go_base.refs[0]
                             or type(go_base.refs[0]._allocations_snapshot) is not tuple)
        closed = channel.close()
        if not closed:
            assert ((writer is not None and writer._unknown)
                    or (reader is not None and reader._io_unknown)
                    or (transition is not None and transition._failed)
                    or (go_writer is not None and (go_writer._unknown or go_writer._failed))
                    or release_drift)
            assert not channel._closed_known
            # Fixture-owned disposal only, never a channel/native release fact.
            # No test flag or protocol evidence is restored to make close pass.
            sock.close()
            assert NativeClockOwner.close_local(channel._clock_owner_snapshot)
        else:
            assert channel.close_clock()
        sock.close()
        peer.close()
        assert await spine.stop_local_sockets()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", [
    "signed", "partial", "wouldblock", "zero", "unknown", "max_packet", "initial_guard",
    "completion_error", "post_send_key", "offset_drift", "wrong_actor", "registration_unknown",
])
async def test_original_work_signed_begin_transport_preserves_reserved_intent(
    context, begin_gateway, tmp_path, monkeypatch, mutation
):
    import errno

    from hmp_plugin import presentation_credential_begin_write as module
    from hmp_plugin.presentation_credential_begin_write import NativeBeginWriter
    from hmp_plugin.presentation_remote import RemoteOperationOwner

    if mutation == "max_packet":
        from hmp_plugin import presentation_input_v3 as input3
        from hmp_plugin.presentation_jobs import INPUT_LIMIT
        original_encode = input3.encode_input_v3
        def maximum_input(value):
            encoded = original_encode(value)
            body = encoded[4:].ljust(INPUT_LIMIT, b" ")
            packet = len(body).to_bytes(4, "big") + body
            assert input3.decode_input_v3(packet) == value and len(packet) == INPUT_LIMIT + 4
            return packet
        monkeypatch.setattr(input3, "encode_input_v3", maximum_input)
    prepared = await prepare(context, begin_gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    if mutation == "max_packet":
        import socket
        channel._socket_snapshot.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
    if mutation == "wrong_actor":
        from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
        initialize = NativePhaseWorkOwner.__init__
        def initialized(producer, cleanup):
            initialize(producer, cleanup)
            with pytest.raises(FrameError):
                NativeBeginWriter.retain(producer)
            assert producer._writer is None and channel._credential_begin_writer is None
        monkeypatch.setattr(NativePhaseWorkOwner, "__init__", initialized)
    owner, keys, broker = await handshake(prepared, tmp_path)
    held = {"actual": bytearray(), "calls": 0}
    wire_ready = asyncio.Event()
    async def receive_known_wire():
        await wire_ready.wait()
        expected = (0 if mutation in ("zero", "initial_guard", "registration_unknown") else
                    7 if mutation == "unknown" else len(held["writer"]._scope_snapshot.wire))
        actual = bytearray()
        async with asyncio.timeout_at(held["writer"]._scope_snapshot.intent.end_ns / 1e9):
            while len(actual) < expected:
                part = await asyncio.get_running_loop().sock_recv(peer, expected - len(actual))
                assert part
                actual.extend(part)
        return bytes(actual)
    receiver_task = asyncio.create_task(receive_known_wire())
    try:
        remote = authority.bind_remote(operation, channel, owner._operation_binding(), packet)
        native_send = module._SEND
        original_authorize = RemoteOperationOwner._authorize_send_completion
        completion_calls = []
        def authorized(owned, *args):
            completion_calls.append(owned)
            result = original_authorize(owned, *args)
            if mutation == "completion_error":
                raise FrameError("SYNTHETIC_COMPLETION_REFUSAL")
            return result
        monkeypatch.setattr(RemoteOperationOwner, "_authorize_send_completion", authorized)
        if mutation == "registration_unknown":
            from hmp_plugin import presentation_readiness as readiness
            install = readiness._install_writer
            def unknown_install(*args):
                install(*args)
                raise OSError("synthetic unknown BEGIN write registration")
            monkeypatch.setattr(readiness, "_install_writer", unknown_install)
        def send(sock, data):
            held["calls"] += 1
            if mutation in ("wouldblock", "registration_unknown") and held["calls"] == 1:
                raise BlockingIOError(errno.EAGAIN, "synthetic known would-block")
            if mutation == "zero":
                return 0
            limit = 7 if mutation == "unknown" else 37 if mutation == "partial" else len(data)
            n = native_send(sock, data[:limit])
            held["actual"].extend(data[:n])
            if mutation == "unknown":
                raise OSError("synthetic uncertain native BEGIN send")
            if mutation == "post_send_key":
                keys["gateway"].retire()
            if mutation == "offset_drift":
                writer = held["writer"]
                writer._offset = writer._offset_snapshot = writer._offset + 1
            return n
        monkeypatch.setattr(module, "_SEND", send)
        async def qualified_test_exchange(producer):
            assert producer is remote._cleanup_owner_snapshot._credential_work_snapshot
            assert asyncio.current_task() is producer._refs_snapshot[6].task
            assert asyncio.current_task() is not producer._cleanup._caller_snapshot
            writer = NativeBeginWriter.retain(producer)
            if mutation == "wrong_actor":
                async def foreign_write():
                    with pytest.raises(FrameError):
                        await writer.write_begin()
                await asyncio.create_task(foreign_write())
                assert writer._attempted is False and writer._failed is False
                assert channel._writing is False
            held["writer"] = writer
            held["intent"] = channel._begin_write_intent_snapshot
            wire_ready.set()
            if mutation == "initial_guard":
                from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
                guard = NativePhaseWorkOwner._guard
                def fail_initial(owned):
                    result = guard(owned)
                    if owned is producer and writer._attempted:
                        held["guard_calls"] = held.get("guard_calls", 0) + 1
                        raise FrameError("SYNTHETIC_INITIAL_WRITE_GUARD")
                    return result
                monkeypatch.setattr(NativePhaseWorkOwner, "_guard", fail_initial)
            with pytest.raises(FrameError):
                NativeBeginWriter.retain(producer)
            try:
                await writer.write_begin()
            finally:
                if mutation == "initial_guard":
                    monkeypatch.setattr(NativePhaseWorkOwner, "_guard", guard)
                    with pytest.raises(FrameError):
                        await writer.write_begin()
                    assert held["guard_calls"] == 1 and held["calls"] == 0
                held["count"] = writer._offset
                held["fact"] = channel._begin_write_fact_snapshot
            # End isolated BEGIN qualification before the signed READY reader.
            raise FrameError("SYNTHETIC_BEGIN_TRANSPORT_ONLY")
        from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
        monkeypatch.setattr(NativePhaseWorkOwner, "exchange_ready", qualified_test_exchange)
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await remote.begin_ready()
        writer = held["writer"]
        scope = writer._scope_snapshot
        succeeded = mutation in ("signed", "partial", "wouldblock", "max_packet", "wrong_actor")
        assert writer._complete is succeeded and writer._failed is not succeeded
        assert writer._attempted
        assert scope.intent is held["intent"] is channel._begin_write_intent_snapshot
        assert scope.intent is writer._scope_snapshot.intent
        assert scope.raw is scope.producer._record_snapshot
        zero_known_progress = mutation in ("zero", "unknown", "initial_guard",
                                           "registration_unknown")
        assert held["count"] == (0 if zero_known_progress else len(scope.wire))
        assert bytes(held["actual"]) == scope.wire[:len(held["actual"])]
        assert await receiver_task == bytes(held["actual"])
        assert completion_calls == ([remote] if succeeded or mutation == "completion_error" else [])
        if mutation == "max_packet":
            assert len(scope.intent.packet) == module._PACKET_LIMIT == 8196
            assert module._LIMIT == 11276
            assert writer._waiter_origin is not None and writer._waiter_origin._retired
        assert (held["fact"] is not None) is succeeded
        if succeeded:
            assert held["fact"].intent is held["intent"]
            assert writer._completion_snapshot.native is held["fact"]
        assert writer._unknown is (mutation in ("unknown", "offset_drift", "registration_unknown"))
        assert channel._writing is (mutation in ("unknown", "offset_drift", "registration_unknown"))
        assert remote._go_admission is None and authority._record(operation).child is None
        assert remote._send_completed is False  # source test intercepted before READY integration
        calls = held["calls"]
        with pytest.raises((FrameError, AuthorityRefusalError)):
            await writer.write_begin()
        assert held["calls"] == calls and channel._begin_write_intent_snapshot is held["intent"]
        if not writer._unknown:
            NativeBeginWriter._released(writer, channel)
        else:
            with pytest.raises(FrameError):
                NativeBeginWriter._released(writer, channel)
        if succeeded:
            # Removing both mutable markers cannot erase the retained signed
            # channel provenance and revive the generic unsigned fallback.
            handshake_owner = channel._credential_handshake_snapshot
            channel._credential_handshake = channel._credential_handshake_snapshot = None
            try:
                with pytest.raises(FrameError):
                    channel._credential_work_ready()
            finally:
                channel._credential_handshake = channel._credential_handshake_snapshot = (
                    handshake_owner)
        # The native completion fact cannot bypass any old unsigned phase path.
        with pytest.raises(FrameError):
            await channel.send_cancel(remote._cleanup_owner_snapshot)
    finally:
        receiver_task.cancel()
        await asyncio.gather(receiver_task, return_exceptions=True)
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()


def test_native_join_phase_rejects_foreign_comparison_without_callbacks():
    calls = []

    class ForeignPhase:
        def __eq__(self, other):
            calls.append(other)
            raise AssertionError("foreign phase equality invoked")

    with pytest.raises(FrameError):
        CredentialHandshakeOwner._native_join_fence(None, None, phase=ForeignPhase())
    assert calls == []
