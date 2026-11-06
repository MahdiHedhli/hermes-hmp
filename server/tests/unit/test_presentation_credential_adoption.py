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
    from hmp_plugin.presentation_credential_queued import CredentialQueuedOwner

    original_init = CredentialQueuedOwner.__init__

    def queued_init(work, service, record):
        if mutation == "queued_factory_channel":
            callbacks = []
            held["callbacks"] = callbacks
            held["original_channel"] = record.channel_snapshot

            class ForeignChannel:
                def __getattribute__(self, name):
                    callbacks.append(name)
                    raise AssertionError("foreign constructor channel getter")

            record.channel_snapshot = ForeignChannel()
        original_init(work, service, record)

    monkeypatch.setattr(CredentialQueuedOwner, "__init__", queued_init)
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
            end - 100_000_000 if mutation in ("earlier_accept", "queued_after_admission") else end,
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
            if mutation == "legacy_control":
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_result_transport import BrokerResultWriter, _native_io

                native = spine._registry_snapshot._record(ticket)
                original_budget = CancellationBudget.inspect(native.cleanup_budget)
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    BrokerCancellationOwner.retain(
                        channel, spine._registry_snapshot, ticket, record.grammar
                    )
                assert (
                    channel._cancel_receiver is None and channel._cancel_receiver_snapshot is None
                )
                assert CancellationBudget.inspect(native.cleanup_budget) == original_budget
                # Direct initialization is also rejected before capturing another
                # operation's failure custody or scheduling native Tasks/Futures.
                direct = BrokerCancellationOwner.__new__(BrokerCancellationOwner)
                grammar_before = dict(record.grammar.__dict__)
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.__init__(
                        direct, channel, spine._registry_snapshot, ticket, record.grammar
                    )
                assert record.grammar.__dict__ == grammar_before
                assert CancellationBudget.inspect(native.cleanup_budget) == original_budget
                assert direct._failure_origin_snapshot == (None, None)
                assert direct._allocation_snapshot is None and direct._slot_snapshot.task is None
                assert direct._go_future_snapshot is None and direct._cancel_future_snapshot is None
                assert (
                    channel._cancel_receiver is None and channel._cancel_receiver_snapshot is None
                )
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    BrokerResultWriter.retain(spine, record, receiver._result_snapshot.packet)
                assert record.result_writer is None and record.result_writer_snapshot is None
                assert channel._result_writer is None and channel._result_writer_snapshot is None
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    _native_io(channel)
                held["legacy_refused"] = True
            work = record.credential_work_snapshot
            assert work is record.credential_work
            held["work"] = work
            native = spine._registry_snapshot._record(ticket)
            if mutation and mutation.startswith("queued_"):
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_clock import NativeClockOwner

                if mutation == "queued_after_admission":
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: receiver._end + 1)
                elif mutation == "queued_key":
                    keys["broker"].retire()
                elif mutation == "queued_budget":
                    CancellationBudget.refuse(native.cleanup_budget)
                elif mutation == "queued_receipt":
                    native.input_receipt = object()
                elif mutation == "queued_grammar":
                    record.grammar._ready = True
                elif mutation == "queued_flags":
                    record.credential_adoption_failed = True
                elif mutation == "queued_deadline":
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: native.deadline_ns)
                elif mutation in (
                    "queued_final_key",
                    "queued_foreign_refs",
                    "queued_foreign_budget",
                    "queued_forged_receipt",
                    "queued_socket_receipt",
                ):
                    sample = NativeClockOwner.sample
                    socket_check = SocketChannel._check
                    callbacks = []
                    held["callbacks"] = callbacks

                    class Foreign:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign getter")

                        def __eq__(self, other):
                            callbacks.append("comparison")
                            raise AssertionError("foreign comparison")

                        def __iter__(self):
                            callbacks.append("iterate")
                            raise AssertionError("foreign reference iteration")

                        def __getitem__(self, index):
                            callbacks.append(index)
                            raise AssertionError("foreign reference indexing")

                    def changed(clock):
                        now = sample(clock)
                        if mutation == "queued_final_key":
                            keys["broker"].retire()
                        elif mutation == "queued_foreign_budget":
                            native.cleanup_budget = Foreign()
                        elif mutation in ("queued_forged_receipt", "queued_socket_receipt"):
                            forged = native.input_receipt_snapshot._replace(input_sha=Foreign())
                            native.input_receipt = native.input_receipt_snapshot = forged
                        else:
                            work._refs = Foreign()
                        return now

                    if mutation == "queued_socket_receipt":

                        def socket_changed(channel):
                            result = socket_check(channel)
                            forged = native.input_receipt_snapshot._replace(input_sha=Foreign())
                            native.input_receipt = native.input_receipt_snapshot = forged
                            return result

                        monkeypatch.setattr(SocketChannel, "_check", socket_changed)
                    else:
                        monkeypatch.setattr(NativeClockOwner, "sample", changed)
                elif mutation == "queued_wrong_task":

                    async def foreign_task():
                        return work.current_queued()

                    await asyncio.create_task(foreign_task())
            assert work.current_queued() is native
            if mutation in (
                "control_binding",
                "control_binding_creator_drift",
                "control_binding_reader_drift",
            ):
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget

                budget_before = CancellationBudget.inspect(native.cleanup_budget)
                grammar_before = dict(record.grammar.__dict__)
                control = BrokerCancellationOwner.prepare_credential(work)
                held["prepared_control"] = control
                prepared = control._credential_binding_snapshot
                assert (
                    prepared._bound is True and prepared._allocation is control._allocation_snapshot
                )
                assert prepared._creator is asyncio.current_task()
                assert prepared._allocation.task is not asyncio.current_task()
                assert prepared._allocation.task.get_coro() is control._slot_snapshot.coroutine
                with pytest.raises(FrameError, match="SIGNED_CONTROL_READER_NOT_IMPLEMENTED"):
                    BrokerCancellationOwner._guard(control)
                with pytest.raises(FrameError, match="SIGNED_CONTROL_READER_NOT_IMPLEMENTED"):
                    BrokerServiceSpine._v2_work_current(spine, control)
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.prepare_credential(work)
                original_task = control._allocation_snapshot.task
                if mutation != "control_binding":
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    from hmp_plugin.presentation_control_binding import PreparedControlBinding

                    callbacks = []
                    held["binding_callbacks"] = callbacks

                    class Foreign:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign control getter")

                    if mutation == "control_binding_creator_drift":
                        sample = NativeClockOwner.sample

                        def changed(clock):
                            now = sample(clock)
                            prepared._control_snapshot = Foreign()
                            return now

                        monkeypatch.setattr(NativeClockOwner, "sample", changed)
                        with pytest.raises(FrameError):
                            PreparedControlBinding.creator_current(prepared)
                    else:
                        prepared._allocation = Foreign()
                outcome = await asyncio.gather(original_task, return_exceptions=True)
                assert len(outcome) == 1 and isinstance(outcome[0], FrameError)
                assert control._failed is True and control._wire_received == 0
                assert control._go_receipt is None and control._cancel_receipt is None
                assert channel._reading is False and control._buffer_origin == b""
                assert CancellationBudget.inspect(native.cleanup_budget) == budget_before
                assert record.grammar.__dict__ == grammar_before
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
        if mutation in (
            None,
            "earlier_accept",
            "queued_after_admission",
            "legacy_control",
            "control_binding",
            "control_binding_creator_drift",
            "control_binding_reader_drift",
        ):
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
            channel = held.get("original_channel", held["record"].channel_snapshot)
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


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_queued_work_uses_original_work_end_after_local_admission_cap(
    local, tmp_path, monkeypatch
):
    held, _ = await exchange(local, tmp_path, monkeypatch, "queued_after_admission")
    work = held["work"]
    assert work._initialized is True and work._refused is False
    assert work._end == held["receiver"]._expected["work_end_ns"]
    assert held["record"].credential_adoption_complete is True


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation",
    [
        "queued_key",
        "queued_budget",
        "queued_receipt",
        "queued_flags",
        "queued_final_key",
        "queued_foreign_refs",
        "queued_deadline",
        "queued_wrong_task",
        "queued_foreign_budget",
        "queued_forged_receipt",
        "queued_socket_receipt",
        "queued_grammar",
    ],
)
async def test_queued_current_refuses_late_drift_without_resource_or_go(
    local, tmp_path, monkeypatch, mutation
):
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    record, work = held["record"], held["work"]
    assert record.credential_adoption_complete is True
    assert calls == [record.ticket] and work._refused is True
    native = local[0]._registry_snapshot._record(record.ticket)
    assert native.resources is None and native.start_attempted is False
    assert held.get("callbacks", []) == []
    with pytest.raises(FrameError):
        work.current_queued()


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_queued_constructor_rejects_foreign_channel_before_getters(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "queued_factory_channel")
    record = held["record"]
    assert held["callbacks"] == [] and calls == [record.ticket]
    assert (
        record.credential_adoption_complete is False and record.credential_adoption_failed is True
    )
    assert record.credential_work_snapshot._initialized is False
    native = local[0]._registry_snapshot._record(record.ticket)
    assert native.resources is None and native.start_attempted is False


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_credential_channel_refuses_legacy_control_and_result_before_claims(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "legacy_control")
    assert held["legacy_refused"] is True and calls == [held["ticket"]]
    assert held["record"].credential_adoption_complete is True
    assert held["work"]._refused is False


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_prepared_credential_control_binds_original_task_and_performs_no_io(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "control_binding")
    control = held["prepared_control"]
    assert calls == [held["ticket"]] and control._failed is True
    assert held["record"].cancel_owner is control
    assert control._credential_binding_snapshot._refs is held["work"]._refs_snapshot
    assert local[0]._registry_snapshot._record(held["ticket"]).resources is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation", ["control_binding_creator_drift", "control_binding_reader_drift"]
)
async def test_prepared_control_rejects_foreign_context_without_getters_or_io(
    local, tmp_path, monkeypatch, mutation
):
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    assert held["binding_callbacks"] == [] and calls == [held["ticket"]]
    control = held["prepared_control"]
    assert control._failed is True and control._wire_received == 0
    assert control._go_receipt is None and control._cancel_receipt is None
