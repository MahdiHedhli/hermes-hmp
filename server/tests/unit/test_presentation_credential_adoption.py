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
            if mutation and mutation.startswith("signed_control_native_"):
                from hmp_plugin.presentation_broker_cancel import (
                    _CANCEL_RECEIPT_MINT,
                    BrokerCancellationOwner,
                    _CancelReceipt,
                )
                from hmp_plugin.presentation_cancel_budget import CancellationBudget

                budget = native.cleanup_budget_snapshot
                before = CancellationBudget.inspect(budget)
                grammar_before = dict(record.grammar.__dict__)
                control = BrokerCancellationOwner.retain_credential_cancel(work)
                held["native_control"] = control
                inherit = CancellationBudget.inherit

                def inherited(budget, window, now):
                    held["native_local_end"] = CancellationBudget.inspect(budget)[2]
                    inherit(budget, window, now)
                    if mutation == "signed_control_native_retire":
                        keys["broker"].retire()

                monkeypatch.setattr(CancellationBudget, "inherit", inherited)
                if mutation in ("signed_control_native_phase_drift",
                                "signed_control_native_end_drift"):
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    complete = CredentialControlCursor.completed_current
                    current = BrokerServiceSpine._current
                    callbacks, ready, causes = [], [], []
                    cause = BrokerCancellationOwner._local_cause

                    class ForeignCursorValue:
                        def __eq__(self, other):
                            callbacks.append("eq")
                            raise AssertionError("foreign cursor comparison")

                        def __gt__(self, other):
                            callbacks.append("gt")
                            raise AssertionError("foreign cursor ordering")

                        def __lt__(self, other):
                            callbacks.append("lt")
                            raise AssertionError("foreign cursor ordering")

                    def completed(cursor):
                        result = complete(cursor)
                        ready.append(True)
                        return result

                    def changed(service):
                        current(service)
                        if ready and asyncio.current_task() is control._allocation_snapshot.task:
                            cursor = control._signed_cursor_snapshot
                            if mutation == "signed_control_native_phase_drift":
                                cursor._phase = ForeignCursorValue()
                            else:
                                cursor._end = cursor._end_snapshot = ForeignCursorValue()

                    def observed_cause(owner):
                        causes.append(True)
                        cause(owner)

                    monkeypatch.setattr(CredentialControlCursor, "completed_current", completed)
                    monkeypatch.setattr(BrokerServiceSpine, "_current", changed)
                    monkeypatch.setattr(BrokerCancellationOwner, "_local_cause", observed_cause)
                    held["native_foreign_callbacks"] = callbacks
                    held["native_local_causes"] = causes
                if mutation == "signed_control_native_notice_retire":
                    current = BrokerServiceSpine._current

                    def retired_notice(service):
                        current(service)
                        if control._notice_completed is True:
                            keys["broker"].retire()

                    monkeypatch.setattr(BrokerServiceSpine, "_current", retired_notice)
                waiter = control._cancel_future_snapshot
                done, _ = await asyncio.wait(
                    (waiter, control._allocation_snapshot.task), timeout=0.5,
                    return_when=asyncio.FIRST_COMPLETED)
                assert done
                success = mutation in ("signed_control_native_cancel",
                                       "signed_control_native_retire_parked")
                if success:
                    notice = waiter.result()
                    assert type(notice) is _CancelReceipt and notice.mint is _CANCEL_RECEIPT_MINT
                    assert notice is control._cancel_receipt_snapshot
                    assert notice.allocation is control._allocation_snapshot
                    assert control._go_receipt is None and native.start_attempted is False
                    assert record.grammar._cancel is True and record.grammar._go is False
                    assert record.grammar._client_next == 2
                    assert notice.end == min(notice.window.end_ns, held["native_local_end"])
                    assert CancellationBudget.inspect(budget)[2] == notice.end
                    if mutation == "signed_control_native_retire_parked":
                        keys["broker"].retire()
                    BrokerCancellationOwner.abort(control)
                    outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                   return_exceptions=True)
                    assert outcome == [notice.frame]
                    assert control._stop_known is True and control._failed is False
                    held["native_notice"] = notice
                else:
                    outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                   return_exceptions=True)
                    assert isinstance(outcome[0], FrameError)
                    if mutation == "signed_control_native_notice_retire":
                        assert waiter.done() and control._notice_completed is True
                        assert control._failed is True and control._io_unknown is True
                    else:
                        assert not waiter.done() and control._cancel_receipt is None
                    if mutation not in ("signed_control_native_retire",
                                         "signed_control_native_notice_retire"):
                        assert CancellationBudget.inspect(budget) == before
                        assert record.grammar.__dict__ == grammar_before
                    if mutation in ("signed_control_native_phase_drift",
                                    "signed_control_native_end_drift"):
                        assert held["native_foreign_callbacks"] == []
                        assert held["native_local_causes"] == []
                return ticket
            if mutation and mutation.startswith("signed_control_"):
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget

                budget_before = CancellationBudget.inspect(native.cleanup_budget_snapshot)
                grammar_before = dict(record.grammar.__dict__)
                if mutation in ("signed_control_init_refs", "signed_control_final_refs"):
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    completed = CredentialBeginReceiver._completed_current
                    retain = CredentialControlCursor.retain
                    callbacks = []
                    calls = []
                    active = []

                    class ForeignRefs:
                        def __getitem__(self, index):
                            callbacks.append(index)
                            raise AssertionError("foreign refs indexing")

                        def __iter__(self):
                            callbacks.append("iterate")
                            raise AssertionError("foreign refs iteration")

                    def changed_completed(receiver):
                        result = completed(receiver)
                        if active:
                            calls.append(True)
                            wanted = 1 if mutation == "signed_control_init_refs" else 2
                            if len(calls) == wanted:
                                record.cancel_owner._credential_binding_snapshot._refs_snapshot = (
                                    ForeignRefs())
                        return result

                    def retained(cls, control):
                        active.append(True)
                        return retain(control)

                    monkeypatch.setattr(CredentialBeginReceiver, "_completed_current",
                                        changed_completed)
                    monkeypatch.setattr(CredentialControlCursor, "retain", classmethod(retained))
                    with pytest.raises(FrameError, match="CONTROL_ACQUISITION_REFUSED"):
                        BrokerCancellationOwner.stage_credential_control(work)
                    control = record.cancel_owner
                    assert control._failed is True and callbacks == []
                    await asyncio.gather(control._allocation_snapshot.task, return_exceptions=True)
                    assert control._go_receipt is None and control._cancel_receipt is None
                    assert (CancellationBudget.inspect(native.cleanup_budget_snapshot)
                            == budget_before)
                    assert record.grammar.__dict__ == grammar_before
                    held["signed_cursor"] = control._signed_cursor_snapshot
                    return ticket
                control = BrokerCancellationOwner.stage_credential_control(work)
                held["staged_control"] = control
                cursor = control._signed_cursor_snapshot
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.stage_credential_control(work)
                if mutation == "signed_control_key":
                    keys["broker"].retire()
                elif mutation == "signed_control_deadline":
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: end)
                elif mutation in ("signed_control_retire_after_read", "signed_control_counter"):
                    from hmp_plugin import presentation_broker_cancel as cancel_module
                    recv = cancel_module._SOCKET_RECV

                    def retired_recv(sock, wanted):
                        part = recv(sock, wanted)
                        if mutation == "signed_control_counter":
                            cursor._consumed = cursor._consumed_snapshot = 1
                        else:
                            keys["broker"].retire()
                        return part

                    monkeypatch.setattr(cancel_module, "_SOCKET_RECV", retired_recv)
                elif mutation == "signed_control_buffer":
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    sample = NativeClockOwner.sample
                    held["signed_original_buffer"] = cursor._buffer_origin
                    replacement = bytearray(b"preserve")

                    def buffer_changed(clock):
                        now = sample(clock)
                        if cursor._last_read is not None and cursor._read_intent:
                            cursor._buffer = cursor._buffer_origin = replacement
                            cursor._buffer_values = bytes(replacement)
                            cursor._consumed = cursor._consumed_snapshot = len(replacement) + 8
                            cursor._target = cursor._target_snapshot = len(replacement) + 8
                        return now

                    monkeypatch.setattr(NativeClockOwner, "sample", buffer_changed)
                elif mutation in ("signed_control_blocking", "signed_control_timeout"):
                    from hmp_plugin import presentation_broker_cancel as cancel_module
                    check = SocketChannel._check
                    checked, received = [], []

                    def changed_socket(checked_channel):
                        check(checked_channel)
                        if asyncio.current_task() is control._allocation_snapshot.task:
                            checked.append(True)
                            if len(checked) == 2:
                                if mutation == "signed_control_blocking":
                                    os.set_blocking(checked_channel._fd, True)
                                else:
                                    checked_channel._socket_snapshot.settimeout(0.01)

                    def forbidden_recv(sock, wanted):
                        received.append(True)
                        raise AssertionError("blocking recv must be refused before syscall")

                    monkeypatch.setattr(SocketChannel, "_check", changed_socket)
                    monkeypatch.setattr(cancel_module, "_SOCKET_RECV", forbidden_recv)
                    held["signed_forbidden_recv"] = received
                elif mutation == "signed_control_wrong_task":
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    with pytest.raises(FrameError):
                        CredentialControlCursor._guard(cursor)
                outcome = await asyncio.gather(control._allocation_snapshot.task,
                                               return_exceptions=True)
                assert len(outcome) == 1 and isinstance(outcome[0], FrameError)
                if mutation in ("signed_control_blocking", "signed_control_timeout"):
                    assert held["signed_forbidden_recv"] == [] and cursor._consumed == 0
                    channel._socket_snapshot.setblocking(False)
                assert control._go_receipt is None and control._cancel_receipt is None
                assert CancellationBudget.inspect(native.cleanup_budget_snapshot) == budget_before
                assert record.grammar.__dict__ == grammar_before
                success = mutation in ("signed_control_go", "signed_control_cancel",
                                       "signed_control_fragmented", "signed_control_wrong_task")
                assert cursor._complete is success and cursor._failed is not success
                if success:
                    assert str(outcome[0]) == "BI1_SIGNED_CONTROL_RECEIPT_INTEGRATION_REQUIRED"
                    assert cursor._consumed == len(cursor._raw) + len(cursor._frame)
                    assert channel._reading is False
                else:
                    assert cursor._raw is None
                    if mutation == "signed_control_buffer":
                        assert cursor._buffer_origin == b"preserve"
                        assert held["signed_original_buffer"] == b""
                    else:
                        assert cursor._buffer_origin == b""
                    if mutation == "signed_control_counter":
                        assert cursor._last_read == (0, 8)
                    if mutation in ("signed_control_signature", "signed_control_scope",
                                    "signed_control_sequence", "signed_control_boot"):
                        assert cursor._consumed == held["signed_auth_length"]
                    if mutation in ("signed_control_key", "signed_control_deadline"):
                        assert cursor._consumed == 0
                    if mutation == "signed_control_retire_after_read":
                        assert cursor._consumed == 8
                held["signed_cursor"] = cursor
            if mutation in (
                "control_binding",
                "control_binding_creator_drift",
                "control_binding_reader_drift",
                "control_binding_material_key",
                "control_binding_material_control",
                "control_binding_material_budget",
            ):
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_control_binding import PreparedControlBinding

                original_budget = native.cleanup_budget_snapshot
                budget_before = CancellationBudget.inspect(original_budget)
                grammar_before = dict(record.grammar.__dict__)
                material = PreparedControlBinding.reader_material_current
                held["material_passed"] = False

                def observed_material(binding):
                    assert asyncio.current_task() is binding._allocation.task
                    assert asyncio.current_task() is not binding._creator
                    with pytest.raises(FrameError):
                        PreparedControlBinding.creator_current(binding)
                    material(binding)
                    held["material_passed"] = True

                monkeypatch.setattr(
                    PreparedControlBinding, "reader_material_current", observed_material
                )
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
                if mutation in ("control_binding_creator_drift", "control_binding_reader_drift"):
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
                if mutation == "control_binding_material_key":
                    keys["broker"].retire()
                elif mutation in (
                    "control_binding_material_control",
                    "control_binding_material_budget",
                ):
                    current = BrokerServiceSpine._current
                    callbacks = []
                    held["binding_callbacks"] = callbacks

                    class ForeignMaterial:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign reader material getter")

                    def material_changed(service):
                        current(service)
                        if asyncio.current_task() is original_task:
                            if mutation == "control_binding_material_control":
                                prepared._control_snapshot = ForeignMaterial()
                            else:
                                native.cleanup_budget = ForeignMaterial()

                    monkeypatch.setattr(BrokerServiceSpine, "_current", material_changed)
                outcome = await asyncio.gather(original_task, return_exceptions=True)
                assert len(outcome) == 1 and isinstance(outcome[0], FrameError)
                assert control._failed is True and control._wire_received == 0
                assert control._go_receipt is None and control._cancel_receipt is None
                assert channel._reading is False and control._buffer_origin == b""
                assert CancellationBudget.inspect(original_budget) == budget_before
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
        if mutation and mutation.startswith("signed_control_"):
            from hmp_plugin.presentation_cancel_budget import CancellationWindow

            phase = "CANCEL" if mutation in ("signed_control_cancel", "signed_control_hash",
                                             "signed_control_window") else "GO"
            if mutation.startswith("signed_control_native_"):
                phase = "GO" if mutation == "signed_control_native_go" else "CANCEL"
            body = CancellationWindow(end - 250_000_000, end).encode() if phase == "CANCEL" else b""
            if mutation.startswith("signed_control_native_") and phase == "CANCEL":
                start = time.monotonic_ns()
                if mutation == "signed_control_native_future_window":
                    start += 1_000_000_000
                body = CancellationWindow(start, start + 250_000_000).encode()
            if mutation == "signed_control_window":
                body = b"\0" * 16
            control_frame = encode_frame(binding, phase, 1, body, version=2)
            control_value = dict(value, phase=phase, sequence=1,
                                 frame_sha256=hashlib.sha256(control_frame).hexdigest(),
                                 frame_length=len(control_frame))
            if mutation == "signed_control_scope":
                control_value["scope_sha256"] = "f" * 64
            if mutation == "signed_control_sequence":
                control_value["sequence"] = 2
            if mutation == "signed_control_boot":
                control_value["broker_boot"] = "f" * len(control_value["broker_boot"])
            control_raw = encode_record(control_value, keys["gateway"]._private_key.sign(
                signing_bytes(control_value)))
            if mutation in ("signed_control_signature", "signed_control_native_signature"):
                control_raw = control_raw[:-1] + bytes([control_raw[-1] ^ 1])
            if mutation == "signed_control_hash":
                control_frame = control_frame[:-1] + bytes([control_frame[-1] ^ 1])
            held["signed_auth_length"] = len(control_raw)
            wire = control_raw + control_frame
            if mutation == "signed_control_fragmented":
                for part in (wire[:4], wire[4:8], wire[8:-1], wire[-1:]):
                    await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, part)
                    await asyncio.sleep(0)
            else:
                await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, wire)
        if (mutation and mutation.startswith("signed_control_")) or mutation in (
            None,
            "earlier_accept",
            "queued_after_admission",
            "legacy_control",
            "control_binding",
            "control_binding_creator_drift",
            "control_binding_reader_drift",
            "control_binding_material_key",
            "control_binding_material_control",
            "control_binding_material_budget",
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
    assert held["material_passed"] is True


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


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation",
    [
        "control_binding_material_key",
        "control_binding_material_control",
        "control_binding_material_budget",
    ],
)
async def test_controller_reader_material_rejects_revocation_and_callback_drift(
    local, tmp_path, monkeypatch, mutation
):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert held["material_passed"] is False and held.get("binding_callbacks", []) == []
    control = held["prepared_control"]
    assert control._failed is True and control._wire_received == 0
    assert control._go_receipt is None and control._cancel_receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_go", "signed_control_cancel", "signed_control_scope",
    "signed_control_sequence", "signed_control_signature", "signed_control_hash",
    "signed_control_key", "signed_control_deadline", "signed_control_retire_after_read",
    "signed_control_fragmented", "signed_control_wrong_task", "signed_control_boot",
    "signed_control_window", "signed_control_counter", "signed_control_buffer",
    "signed_control_init_refs", "signed_control_final_refs",
    "signed_control_blocking", "signed_control_timeout",
])
async def test_original_signed_control_cursor_without_native_receipts(local, tmp_path, monkeypatch,
                                                                     mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "signed_cursor" in held


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_native_cancel", "signed_control_native_go",
    "signed_control_native_future_window", "signed_control_native_signature",
    "signed_control_native_retire", "signed_control_native_retire_parked",
    "signed_control_native_phase_drift", "signed_control_native_end_drift",
    "signed_control_native_notice_retire",
])
async def test_signed_cancel_native_receipt_and_owned_local_stop(local, tmp_path, monkeypatch,
                                                               mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "native_control" in held
