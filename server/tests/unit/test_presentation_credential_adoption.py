"""Original private-service/registry composition with synthetic peer/clock facts.

No production enrollment, phone authority, worker launch, provider or host data.
"""

import asyncio
import hashlib
import os
import time
from dataclasses import replace

import pytest

from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_registry import BrokerRegistry
from hmp_plugin.presentation_broker_service import BrokerServiceSpine, SocketChannel
from hmp_plugin.presentation_credential_begin import CredentialBeginReceiver
from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_credential_native_binding import key_pair


async def exchange(local, tmp_path, monkeypatch, mutation=None):
    spine, enrollment, connect, make_packet, _, _ = local
    darwin_model(monkeypatch)
    keys = key_pair(tmp_path, enrollment.installation_generation)
    end = time.monotonic_ns() + 1_800_000_000
    gateway = SocketChannel(
        connect(),
        replace(enrollment, gateway_pid=os.getpid(), service_pid=os.getpid() + 1),
        role="gateway",
        endpoint=spine._endpoint,
        observation=spine._observation,
    )
    held = {}
    original_reserve = BrokerRegistry.reserve
    reserve_calls = []

    def reserve(registry, *args):
        ticket = original_reserve(registry, *args)
        reserve_calls.append(ticket)
        if mutation == "after_reserve":
            keys["broker"].retire()
        return ticket

    monkeypatch.setattr(BrokerRegistry, "reserve", reserve)
    original_bind = BrokerRegistry.bind_input_receipt_once

    def bound(registry, ticket, packet):
        original_bind(registry, ticket, packet)
        if mutation == "after_bind":
            keys["broker"].retire()

    monkeypatch.setattr(BrokerRegistry, "bind_input_receipt_once", bound)

    async def broker():
        record = await BrokerServiceSpine._accept_owned(spine, end)
        held["record"] = record
        channel = SocketChannel(
            record.socket,
            enrollment,
            role="broker",
            endpoint=spine._endpoint,
            observation=spine._observation,
        )
        record.channel = record.channel_snapshot = channel
        owner = CredentialHandshakeOwner.retain(
            channel,
            keys["broker"],
            enrollment.scope,
            end - 100_000_000 if mutation == "earlier_accept" else end,
        )
        await owner.run()
        receiver = CredentialBeginReceiver.retain(owner)
        held["receiver"] = receiver
        await receiver.run()
        if mutation == "before_adopt":
            keys["broker"].retire()
        elif mutation == "registry":
            spine._registry = object()
        try:
            ticket = BrokerServiceSpine._adopt_credential_begin(spine, record)
            with pytest.raises(FrameError):
                BrokerServiceSpine._adopt_credential_begin(spine, record)
            assert record.ticket is ticket and record.credential_adoption_failed is False
            return ticket
        except FrameError:
            with pytest.raises(FrameError):
                BrokerServiceSpine._adopt_credential_begin(spine, record)
            raise

    task = asyncio.create_task(broker())
    owner = CredentialHandshakeOwner.retain(gateway, keys["gateway"], enrollment.scope, end)
    try:
        await owner.run()
        binding = owner._operation_binding()
        packet = make_packet(binding, end)
        scope = derive_input_scope(packet, binding)
        frame = encode_frame(binding, "BEGIN", 0, packet, version=2)
        transcript = owner._transcript_snapshot
        value = dict(owner._common)
        value.pop("clock_domain")
        value.update(
            v=1,
            family="phase",
            alg="Ed25519",
            phase="BEGIN",
            role="gateway",
            direction="g2b",
            key_id=hashlib.sha256(keys["gateway"]._selection.own_public).hexdigest(),
            peer_key_id=hashlib.sha256(keys["gateway"]._selection.peer_public).hexdigest(),
            gateway_boot=transcript.gateway_boot,
            broker_boot=transcript.broker_boot,
            channel=transcript.channel,
            transcript_sha256=transcript.transcript_sha256,
            sequence=0,
            input_sha256=scope.input_sha256,
            scope_sha256=scope.scope_sha256,
            frame_sha256=hashlib.sha256(frame).hexdigest(),
            frame_length=len(frame),
        )
        raw = encode_record(value, keys["gateway"]._private_key.sign(signing_bytes(value)))
        await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, raw + frame)
        if mutation in (None, "earlier_accept"):
            held["ticket"] = await task
        else:
            with pytest.raises(FrameError):
                await task
        return held, reserve_calls
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        if "record" in held:
            # Fixture closes its own local descriptors only, not registry debt.
            channel = held["record"].channel_snapshot
            channel.close()
            channel.close_clock()
        gateway.close()
        gateway.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_original_service_adopts_exact_input_once_without_worker(
    local, tmp_path, monkeypatch
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch)
    record, receiver, ticket = held["record"], held["receiver"], held["ticket"]
    assert calls == [ticket] and record.ticket is ticket
    assert record.credential_adoption_attempted is True
    assert record.credential_adoption_complete is True
    native = spine._registry_snapshot._record(ticket)
    assert (
        native.input_bind_attempted is True
        and native.input_receipt is native.input_receipt_snapshot
    )
    assert native.input_receipt.input_sha == hashlib.sha256(receiver._result.packet).hexdigest()
    assert native.start_attempted is False and native.resources is None and native.managed is False
    assert spine._registry_snapshot.counts.waiting == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", ["before_adopt", "after_reserve", "after_bind", "registry"])
async def test_adoption_failure_consumes_attempt_and_retains_any_original_ticket(
    local, tmp_path, monkeypatch, mutation
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    record = held["record"]
    assert record.credential_adoption_attempted is True
    assert (
        record.credential_adoption_complete is False and record.credential_adoption_failed is True
    )
    if mutation in ("after_reserve", "after_bind"):
        assert calls == [record.ticket] and record.ticket is not None
        native = spine._registry_snapshot._record(record.ticket)
        if mutation == "after_bind":
            assert native.input_bind_attempted is True and native.input_receipt is not None
        else:
            assert native.input_bind_attempted is False and native.input_receipt is None
        assert native.resources is None and native.start_attempted is False
        assert spine._registry_snapshot.counts.waiting == 1
        # A retained ticket/receipt is not credential resource or GO permission.
        with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
            SocketChannel._credential_work_ready(record.channel_snapshot)
    else:
        assert calls == [] and record.ticket is None
        assert spine._registry_snapshot.counts.waiting == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_adoption_finishes_under_earlier_local_cap_without_renewing_work_end(
    local, tmp_path, monkeypatch
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch, "earlier_accept")
    receiver, ticket = held["receiver"], held["ticket"]
    native = spine._registry_snapshot._record(ticket)
    assert calls == [ticket]
    assert receiver._end == receiver._end_snapshot < receiver._expected["work_end_ns"]
    assert native.deadline_ns == receiver._expected["work_end_ns"]
    assert native.start_attempted is False and native.resources is None
