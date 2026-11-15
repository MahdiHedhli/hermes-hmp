"""Actual original-work socket reads; synthetic native authority/peer/clock model.

No live host, provider, device, production caller or native READY/GO transition.
"""

import asyncio
import hashlib
import json

import pytest

from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_credential_begin_write import NativeBeginWriter
from hmp_plugin.presentation_credential_codec import decode_record, encode_record, signing_bytes
from hmp_plugin.presentation_credential_ready_read import NativeReadyReceiver
from hmp_plugin.presentation_jobs import FrameError, RemotePhase

from .test_presentation_broker_service import local as local
from .test_presentation_credential_native_binding import begin_gateway as begin_gateway
from .test_presentation_credential_native_binding import handshake
from .test_presentation_remote import prepare
from .test_presentation_supervisor import context as context


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", [
    "ready", "fragmented", "signature", "scope", "sequence", "hash", "wrong_phase",
    "oversize_auth", "eof", "unknown_recv", "target_drift", "count_drift", "buffer_drift",
    "current_key", "admission_refusal", "wrong_actor", "missing_write", "deadline",
    "cancel_wait", "cancel_wait_partial", "cancel_wait_key", "cancel_wait_key_expired",
    "cancel_wait_key_cancelled", "cancel_wait_key_read_debt", "cancel_wait_key_clock_expired",
    "cancel_wait_generic",
    "cancel_wait_foreign_end", "cancel_wait_progress", "cancel_wait_subclass",
    "cancel_wait_sign", "cancel_wait_sign_partial", "cancel_wait_sign_key",
    "cancel_wait_sign_wrong_actor", "cancel_wait_sign_expired", "cancel_wait_sign_tail_key",
    "cancel_wait_sign_prepare_error", "cancel_wait_sign_foreign_sequence",
    "cancel_wait_sign_read_tail_key", "cancel_wait_sign_read_tail_unknown",
    "cancel_wait_sign_read_tail_intent", "cancel_wait_sign_write",
    "cancel_wait_sign_write_partial", "cancel_wait_sign_write_eagain",
    "cancel_wait_sign_write_unknown", "cancel_wait_sign_write_zero",
    "cancel_wait_sign_write_registration", "cancel_wait_sign_write_tail_key",
    "cancel_wait_sign_write_expired", "cancel_wait_sign_write_initial",
    "cancel_wait_sign_write_wrong_actor", "cancel_wait_sign_write_tail_unknown",
    "cancel_wait_sign_write_tail_cancel", "cancel_wait_sign_write_release_key", "pin_drift",
    "native_ready", "native_wrong_actor", "native_observe_false",
    "native_observe_key", "native_transition_error", "native_transition_key", "native_data_drift",
    "composed_ready", "composed_signature", "composed_wrong_actor",
    "dispatch_ready", "dispatch_signature", "dispatch_cancel",
    "dispatch_go_sign", "dispatch_go_key", "dispatch_go_wrong_actor",
    "dispatch_go_revoked", "dispatch_go_admission", "dispatch_go_deadline",
    "dispatch_go_expected_row", "dispatch_go_foreign_end",
    "dispatch_go_write", "dispatch_go_write_partial", "dispatch_go_write_eagain",
    "dispatch_go_write_unknown", "dispatch_go_write_key",
    "dispatch_go_write_zero", "dispatch_go_write_registration", "dispatch_go_write_initial",
    "dispatch_go_write_tail_key", "dispatch_go_write_tail_cancel",
    "dispatch_go_write_tail_policy", "dispatch_go_write_tail_listener",
    "dispatch_go_write_tail_admission",
    "dispatch_go_write_wrong_actor", "dispatch_go_write_intent_drift",
    "dispatch_go_write_release_cleanup", "dispatch_go_write_release_allocation",
    "dispatch_go_live", "dispatch_go_live_key", "dispatch_go_live_cancel",
    "dispatch_go_live_error", "dispatch_go_live_future", "dispatch_go_live_final_key",
    "dispatch_go_live_result_tail", "dispatch_go_live_result_tail_key",
    "dispatch_go_live_result_tail_policy", "dispatch_go_live_result_tail_listener",
    "dispatch_go_live_result_tail_scope", "dispatch_go_live_result_tail_budget",
    "dispatch_go_live_result_tail_wrong_actor",
    "dispatch_cleanup_material", "dispatch_cleanup_material_key",
    "dispatch_cleanup_material_wrong_actor", "dispatch_cleanup_material_after_go",
    "dispatch_cleanup_material_allocations", "dispatch_cleanup_material_slots",
    "dispatch_cleanup_sign", "dispatch_cleanup_sign_after_go",
    "dispatch_cleanup_sign_wrong_actor", "dispatch_cleanup_sign_key",
    "dispatch_cleanup_sign_expired", "dispatch_cleanup_sign_expired_prepared",
    "dispatch_cleanup_sign_expected_row", "dispatch_cleanup_sign_foreign_end",
    "dispatch_cleanup_sign_write", "dispatch_cleanup_sign_write_after_go",
    "dispatch_cleanup_sign_write_partial", "dispatch_cleanup_sign_write_eagain",
    "dispatch_cleanup_sign_write_unknown", "dispatch_cleanup_sign_write_key",
    "dispatch_cleanup_sign_write_tail_key",
    "dispatch_cleanup_sign_write_foreign_intent_after_go",
    "dispatch_cleanup_sign_write_zero", "dispatch_cleanup_sign_write_registration",
    "dispatch_cleanup_sign_write_wrong_actor", "dispatch_cleanup_sign_write_tail_cancel",
    "dispatch_cleanup_route", "dispatch_cleanup_route_after_go",
    "dispatch_cleanup_route_key", "dispatch_cleanup_route_wrong_actor",
    "dispatch_cleanup_route_initial_failure", "dispatch_cleanup_route_key_expired",
    "dispatch_cleanup_route_key_cancelled", "dispatch_cleanup_route_key_read_debt",
])
async def test_original_work_ready_read_requires_its_complete_signed_begin(
    context, begin_gateway, tmp_path, monkeypatch, mutation
):
    prepared = await prepare(context, begin_gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    handshake_owner, keys, broker = await handshake(prepared, tmp_path)
    held = {}
    writer_retained = asyncio.Event()
    read_wait = asyncio.Event()
    async def peer_ready():
        await writer_retained.wait()
        b = held["writer"]._scope_snapshot
        async with asyncio.timeout_at(b.intent.end_ns / 1e9):
            received = bytearray()
            while len(received) < len(b.wire):
                part = await asyncio.get_running_loop().sock_recv(peer, len(b.wire) - len(received))
                assert part
                received.extend(part)
            assert bytes(received) == b.wire
            if mutation.startswith("cancel_wait"):
                if mutation in ("cancel_wait_partial", "cancel_wait_sign_partial"):
                    await asyncio.get_running_loop().sock_sendall(peer, b"HBAX")
                await read_wait.wait()
                b.allocation.task.cancel()  # synthetic owned task only
                held["ready_wire"] = b""
                return
            value = json.loads(decode_record(b.raw).canonical_json)
            frame = encode_frame(b.intent.binding, "READY", 0, b"", version=2)
            value.update(phase="READY", role="broker", direction="b2g", sequence=0,
                key_id=hashlib.sha256(keys["broker"]._selection.own_public).hexdigest(),
                peer_key_id=hashlib.sha256(keys["broker"]._selection.peer_public).hexdigest(),
                frame_sha256=hashlib.sha256(frame).hexdigest(), frame_length=len(frame))
            if mutation == "scope":
                value["scope_sha256"] = "f" * 64
            if mutation == "sequence":
                value["sequence"] = 1
            if mutation == "hash":
                value["frame_sha256"] = "f" * 64
            if mutation == "wrong_phase":
                frame = encode_frame(b.intent.binding, "GO", 0, b"", version=2)
                value.update(phase="GO", frame_sha256=hashlib.sha256(frame).hexdigest(),
                             frame_length=len(frame))
            raw = encode_record(value, keys["broker"]._private_key.sign(signing_bytes(value)))
            if mutation in ("signature", "composed_signature", "dispatch_signature"):
                raw = raw[:-1] + bytes([raw[-1] ^ 1])
            wire = raw + frame
            if mutation == "oversize_auth":
                wire = b"HBA1" + (1977).to_bytes(4, "big")
            if mutation == "eof":
                wire = wire[:12]
            held["ready_wire"] = wire
            if mutation == "fragmented":
                for piece in (wire[:4], wire[4:8], wire[8:len(raw)], wire[len(raw):]):
                    await asyncio.get_running_loop().sock_sendall(peer, piece)
                    await asyncio.sleep(0)
            else:
                await asyncio.get_running_loop().sock_sendall(peer, wire)
            if mutation == "eof":
                import socket
                peer.shutdown(socket.SHUT_WR)
    peer_task = asyncio.create_task(peer_ready())
    try:
        remote = authority.bind_remote(operation, channel,
                                       handshake_owner._operation_binding(), packet)
        from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
        original_exchange = NativePhaseWorkOwner.exchange_ready
        if mutation == "admission_refusal":
            from hmp_plugin.presentation_remote import RemoteOperationOwner
            authorize = RemoteOperationOwner._authorize_channel
            def refused(owned, *args):
                result = authorize(owned, *args)
                if owned is remote and args[1] == "receive":
                    held["admission_calls"] = held.get("admission_calls", 0) + 1
                    raise FrameError("SYNTHETIC_LATE_RECEIVE_CLAIM_REFUSAL")
                return result
            monkeypatch.setattr(RemoteOperationOwner, "_authorize_channel", refused)
        async def source_only_exchange(producer):
            assert producer is remote._cleanup_owner_snapshot._credential_work_snapshot
            if mutation.startswith("composed_"):
                retain = NativeBeginWriter.retain

                def observed_retain(cls, owned):
                    writer = retain(owned)
                    held["writer"] = writer
                    writer_retained.set()
                    return writer

                monkeypatch.setattr(NativeBeginWriter, "retain", classmethod(observed_retain))
                if mutation == "composed_wrong_actor":
                    async def wrong_exchange():
                        with pytest.raises(FrameError):
                            await original_exchange(producer)
                    await asyncio.create_task(wrong_exchange())
                    assert producer._exchange_attempted is False
                    assert producer._writer is None
                try:
                    held["exchange_receipt"] = await original_exchange(producer)
                finally:
                    held["exchange_producer"] = producer
                    held["exchange_phase"] = authority._record(operation).owner.inspect_remote(
                        authority._record(operation).handle)
                    state = (producer._exchange_attempted, producer._exchange_complete,
                             producer._exchange_failed)
                    with pytest.raises(FrameError):
                        await original_exchange(producer)
                    assert state == (producer._exchange_attempted, producer._exchange_complete,
                                     producer._exchange_failed)
                raise FrameError("SYNTHETIC_COMPOSED_READY_STOP_BEFORE_GO")
            writer = NativeBeginWriter.retain(producer)
            held["writer"] = writer
            writer_retained.set()
            if mutation == "missing_write":
                remote._send_completed = True  # a mutable flag is not completed BEGIN evidence
                try:
                    with pytest.raises(FrameError):
                        NativeReadyReceiver.retain(writer)
                    assert writer._ready_receiver is None and not remote._receive_claimed
                finally:
                    remote._send_completed = False
            await writer.write_begin()
            if mutation == "wrong_actor":
                async def wrong_factory():
                    with pytest.raises(FrameError):
                        NativeReadyReceiver.retain(writer)
                await asyncio.create_task(wrong_factory())
                assert writer._ready_receiver is None
            try:
                receiver = NativeReadyReceiver.retain(writer)
            except FrameError:
                held["receiver"] = writer._ready_receiver_snapshot
                if mutation == "admission_refusal":
                    monkeypatch.setattr(RemoteOperationOwner, "_authorize_channel", authorize)
                    with pytest.raises(FrameError):
                        NativeReadyReceiver.retain(writer)
                    assert held["admission_calls"] == 1
                raise
            held["receiver"] = receiver
            if mutation.startswith("cancel_wait_sign"):
                from hmp_plugin.presentation_broker_service import SocketChannel
                from hmp_plugin.presentation_credential_pre_ready_cancel import (
                    NativePreReadyCancelCommitment,
                )
                from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

                async def pre_ready_data_only(owned_channel, cleanup):
                    assert owned_channel is channel
                    held["pre_ready_called"] = True
                    if mutation == "cancel_wait_sign_wrong_actor":
                        async def wrong_signer():
                            with pytest.raises(FrameError):
                                NativePreReadyCancelCommitment.retain(cleanup)
                        await asyncio.create_task(wrong_signer())
                        assert cleanup._pre_ready_cancel_commitment_snapshot is None
                    if mutation == "cancel_wait_sign_key":
                        keys["gateway"].retire()
                        with pytest.raises(FrameError):
                            NativePreReadyCancelCommitment.retain(cleanup)
                        signer = cleanup._pre_ready_cancel_commitment_snapshot
                    else:
                        try:
                            signer = NativePreReadyCancelCommitment.retain(cleanup)
                        except BaseException as error:
                            held["pre_ready_error"] = error
                            raise
                        if mutation.startswith("cancel_wait_sign_read_tail_"):
                            released = NativeReadyReceiver._released
                            calls = []

                            def retired_read_tail(owned, transport):
                                result = released(owned, transport)
                                if owned is receiver:
                                    calls.append(True)
                                    if len(calls) == 2:
                                        if mutation.endswith("_key"):
                                            keys["gateway"].retire()
                                        elif mutation.endswith("_unknown"):
                                            cleanup._unknown = True
                                        else:
                                            cleanup._intent = False
                                return result

                            monkeypatch.setattr(NativeReadyReceiver, "_released", retired_read_tail)
                            with pytest.raises(FrameError):
                                NativePreReadyCancelCommitment._guard(signer)
                            assert len(calls) == 2 and signer._attempted is False
                            with pytest.raises(FrameError):
                                signer.prepare()
                        elif mutation in ("cancel_wait_sign_tail_key",
                                        "cancel_wait_sign_prepare_error",
                                        "cancel_wait_sign_foreign_sequence"):
                            prepare_cancel = RemoteCleanupOwner._prepare_cancel
                            held["pre_ready_sequence_getters"] = []

                            class ForeignSequence:
                                def __eq__(self, other):
                                    held["pre_ready_sequence_getters"].append("eq")
                                    raise AssertionError("foreign sequence comparison")

                            def changed_preparation(owned, transport):
                                if mutation == "cancel_wait_sign_prepare_error":
                                    raise FrameError("SYNTHETIC_PREPARATION_REFUSED")
                                frame = prepare_cancel(owned, transport)
                                if mutation == "cancel_wait_sign_tail_key":
                                    keys["gateway"].retire()
                                else:
                                    owned._cancel_sequence = owned._cancel_sequence_snapshot = (
                                        ForeignSequence())
                                return frame

                            monkeypatch.setattr(RemoteCleanupOwner, "_prepare_cancel",
                                                changed_preparation)
                            with pytest.raises(FrameError):
                                signer.prepare()
                            assert held["pre_ready_sequence_getters"] == []
                        elif mutation == "cancel_wait_sign_expired":
                            remaining = RemoteCleanupOwner._remaining
                            monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                lambda owned: 0.0 if owned is cleanup else remaining(owned))
                            with pytest.raises(FrameError):
                                signer.prepare()
                        else:
                            raw = signer.prepare()
                            held["pre_ready_signed"] = raw
                            value = json.loads(decode_record(raw).canonical_json)
                            assert value["phase"] == "CANCEL" and value["sequence"] == 1
                            assert value["work_end_ns"] == writer._scope_snapshot.intent.end_ns
                            assert cleanup._cancel_write_completed is False
                            assert producer._ready_transition_snapshot is None
                            assert channel._go_write_intent_snapshot is None
                            if mutation.startswith("cancel_wait_sign_write"):
                                from hmp_plugin import (
                                    presentation_credential_pre_ready_cancel_write as cancel_module,
                                )
                                cancel_writer = (
                                    cancel_module.NativePreReadyCancelWriter.retain(signer))
                                held["pre_ready_writer"] = cancel_writer
                                if mutation.endswith("_wrong_actor"):
                                    async def wrong_cancel_writer():
                                        with pytest.raises(FrameError):
                                            await cancel_writer.write_cancel()
                                    await asyncio.create_task(wrong_cancel_writer())
                                    assert cancel_writer._attempted is False
                                if mutation.endswith("_initial"):
                                    guard = cancel_module.NativePreReadyCancelWriter._guard

                                    def refused_first_write(owned):
                                        if owned is cancel_writer and owned._attempted:
                                            raise FrameError("SYNTHETIC_FIRST_WRITE_GUARD_REFUSED")
                                        return guard(owned)

                                    monkeypatch.setattr(cancel_module.NativePreReadyCancelWriter,
                                                        "_guard", refused_first_write)
                                send = cancel_module._SEND
                                held["pre_ready_send_calls"] = 0

                                def observed_send(sock, data):
                                    held["pre_ready_send_calls"] += 1
                                    count = held["pre_ready_send_calls"]
                                    if mutation.endswith("_unknown"):
                                        raise OSError("synthetic uncertain CANCEL send")
                                    if mutation.endswith("_zero"):
                                        return 0
                                    if count == 1 and mutation.endswith(
                                            ("_eagain", "_registration")):
                                        import errno
                                        raise BlockingIOError(errno.EAGAIN, "synthetic would block")
                                    short = count == 1 and mutation.endswith("_partial")
                                    return send(sock, data[:23] if short else data)

                                monkeypatch.setattr(cancel_module, "_SEND", observed_send)
                                if mutation.endswith("_expired"):
                                    remaining = RemoteCleanupOwner._remaining
                                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                        lambda owned: 0.0 if owned is cleanup
                                        and cancel_writer._active else remaining(owned))
                                if mutation.endswith("_registration"):
                                    def refused_init(owned, sock):
                                        raise FrameError("SYNTHETIC_WRITE_REGISTRATION_REFUSED")
                                    monkeypatch.setattr(cancel_module.SelectorWriteReadiness,
                                                        "__init__", refused_init)
                                if mutation.endswith(
                                        ("_tail_key", "_tail_unknown", "_tail_cancel")):
                                    inheritable = cancel_module.os.get_inheritable

                                    def retired_send_tail(fd):
                                        result = inheritable(fd)
                                        import sys
                                        if (fd == channel._fd_snapshot and cancel_writer._active
                                                and sys._getframe(1).f_code
                                                is cancel_module.NativePreReadyCancelWriter
                                                ._guard.__code__):
                                            held["pre_ready_final_tail"] = True
                                            if mutation.endswith("_tail_key"):
                                                keys["gateway"].retire()
                                            elif mutation.endswith("_tail_unknown"):
                                                cleanup._unknown = True
                                            else:
                                                cleanup._allocations_snapshot[0].task.cancel()
                                        return result

                                    monkeypatch.setattr(cancel_module.os, "get_inheritable",
                                                        retired_send_tail)
                                succeeds = mutation in ("cancel_wait_sign_write",
                                    "cancel_wait_sign_write_partial",
                                    "cancel_wait_sign_write_eagain",
                                    "cancel_wait_sign_write_wrong_actor",
                                    "cancel_wait_sign_write_release_key")
                                if succeeds:
                                    await cancel_writer.write_cancel()
                                    if mutation.endswith("_release_key"):
                                        keys["gateway"].retire()
                                    cancel_module.NativePreReadyCancelWriter._released(
                                        cancel_writer, channel)
                                else:
                                    with pytest.raises((FrameError, OSError)):
                                        await cancel_writer.write_cancel()
                                assert cleanup._cancel_write_completed is succeeds
                                assert cancel_writer._complete is succeeds
                                with pytest.raises(FrameError):
                                    await cancel_writer.write_cancel()
                                with pytest.raises(FrameError):
                                    cancel_module.NativePreReadyCancelWriter.retain(signer)
                    held["pre_ready_signer"] = signer
                    with pytest.raises(FrameError):
                        NativePreReadyCancelCommitment.retain(cleanup)
                    with pytest.raises(FrameError):
                        signer.prepare()
                    raise FrameError("SYNTHETIC_PRE_READY_DATA_ONLY_NO_TRANSPORT")

                async def observed_pre_ready_data_only(owned_channel, cleanup):
                    try:
                        return await pre_ready_data_only(owned_channel, cleanup)
                    except BaseException as error:
                        held["pre_ready_callback_error"] = error
                        raise

                monkeypatch.setattr(SocketChannel, "send_cancel", observed_pre_ready_data_only)
            assert remote._send_completed and remote._receive_claimed
            with pytest.raises(FrameError):
                NativeReadyReceiver.retain(writer)
            if mutation == "wrong_actor":
                async def wrong_reader():
                    with pytest.raises(FrameError):
                        await receiver.run()
                await asyncio.create_task(wrong_reader())
                assert not receiver._started and not receiver._failed and not channel._reading
            if mutation.startswith("cancel_wait_key_"):
                from hmp_plugin.presentation_credential_pre_ready_cancel import (
                    NativePreReadyCancelCommitment,
                )
                from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

                cleanup = remote._cleanup_owner_snapshot
                if mutation in ("cancel_wait_key_expired", "cancel_wait_key_clock_expired"):
                    remaining = RemoteCleanupOwner._remaining

                    def expired_failed_signer(owned):
                        result = remaining(owned)
                        signer = cleanup._pre_ready_cancel_commitment_snapshot
                        if (owned is cleanup and signer is not None and signer._failed
                                and (mutation == "cancel_wait_key_expired"
                                     or channel._closed_known)):
                            return 0.0
                        return result

                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining", expired_failed_signer)
                else:
                    retain = NativePreReadyCancelCommitment.retain

                    def changed_refusal(cls, owned):
                        try:
                            return retain(owned)
                        except FrameError:
                            signer = cleanup._pre_ready_cancel_commitment_snapshot
                            assert signer is not None and signer._failed
                            if mutation == "cancel_wait_key_cancelled":
                                assert cleanup._allocations_snapshot[0].task.cancel()
                            else:
                                receiver._io_unknown = True
                            raise

                    monkeypatch.setattr(NativePreReadyCancelCommitment, "retain",
                                        classmethod(changed_refusal))
            if mutation.startswith("cancel_wait"):
                from hmp_plugin import presentation_readiness as readiness
                wait = readiness.SelectorReadiness.wait
                held["cancel_getters"] = []

                class ForeignCancelled(readiness._ReadinessCancelledError):
                    def __getattribute__(self, name):
                        if name == "retirement":
                            held["cancel_getters"].append(name)
                            raise AssertionError("foreign cancellation getter")
                        return super().__getattribute__(name)

                async def observe_wait(waiter, end_ns, **options):
                    if (waiter._origin_scope.task is writer._scope_snapshot.allocation.task
                            and (mutation not in ("cancel_wait_partial", "cancel_wait_sign_partial")
                                 or receiver._consumed == 4)):
                        read_wait.set()
                    try:
                        return await wait(waiter, end_ns, **options)
                    except readiness._ReadinessCancelledError as error:
                        if mutation == "cancel_wait_generic":
                            raise asyncio.CancelledError from None
                        if mutation == "cancel_wait_foreign_end":
                            raise readiness._ReadinessCancelledError(
                                error.retirement._replace(end=end_ns + 1)) from None
                        if mutation == "cancel_wait_subclass":
                            raise ForeignCancelled(error.retirement) from None
                        if mutation == "cancel_wait_progress":
                            receiver._consumed += 1
                        if mutation.startswith("cancel_wait_key"):
                            keys["gateway"].retire()
                        raise
                monkeypatch.setattr(readiness.SelectorReadiness, "wait", observe_wait)
            if mutation in ("deadline", "pin_drift"):
                from hmp_plugin.presentation_clock import NativeClockOwner
                sample = NativeClockOwner.sample
                held["pin_callbacks"] = []
                class ForeignPin:
                    def __eq__(self, other):
                        held["pin_callbacks"].append("eq")
                        raise AssertionError("foreign key comparison")
                    def __len__(self):
                        held["pin_callbacks"].append("len")
                        raise AssertionError("foreign key length")
                def changed_sample(clock):
                    now = sample(clock)
                    if (receiver._started and asyncio.current_task()
                            is writer._scope_snapshot.allocation.task):
                        if mutation == "deadline":
                            return writer._scope_snapshot.intent.end_ns
                        if not held.get("pin_changed"):
                            held["pin_changed"] = True
                            object.__setattr__(writer._scope_snapshot.refs[5], "peer_public",
                                               ForeignPin())
                    return now
                monkeypatch.setattr(NativeClockOwner, "sample", changed_sample)
            if mutation == "unknown_recv":
                from hmp_plugin import presentation_credential_ready_read as module
                recv = module._RECV
                def unknown(sock, wanted):
                    part = recv(sock, min(wanted, 4))
                    held["actual_unknown_count"] = len(part)
                    raise OSError("SYNTHETIC_UNKNOWN_READY_RECV")
                monkeypatch.setattr(module, "_RECV", unknown)
            if mutation in ("target_drift", "count_drift", "buffer_drift"):
                guard = NativeReadyReceiver._guard
                def changed(owned):
                    result = guard(owned)
                    if owned is receiver and owned._pending and not held.get("changed"):
                        held["changed"] = True
                        if mutation == "target_drift":
                            owned._target = owned._target_origin = owned._target + 1
                        elif mutation == "count_drift":
                            owned._consumed = owned._consumed_origin = owned._consumed + 1
                            owned._target = owned._target_origin = owned._target + 1
                        else:
                            held["foreign_buffer"] = bytearray(b"PRESERVE_FOREIGN_READY_BUFFER")
                            owned._buffer = owned._buffer_origin = held["foreign_buffer"]
                    return result
                monkeypatch.setattr(NativeReadyReceiver, "_guard", changed)
            try:
                await receiver.run()
            except BaseException as error:
                held["read_error"] = error
                raise
            finally:
                if mutation == "pin_drift":
                    object.__setattr__(writer._scope_snapshot.refs[5], "peer_public",
                                       receiver._scope_origin.pins[0])
            if mutation == "current_key":
                keys["gateway"].retire()
            fact = receiver.current_ready()
            held["ready_fact"] = fact
            assert authority._record(operation).owner.inspect_remote(
                authority._record(operation).handle) is RemotePhase.BEGIN_INTENT
            if mutation.startswith("native_"):
                from hmp_plugin.presentation_authority import ParentAuthorityAdapter
                from hmp_plugin.presentation_credential_ready_transition import (
                    NativeReadyTransition,
                )
                from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
                from hmp_plugin.presentation_jobs import JobOwner
                if mutation == "native_wrong_actor":
                    async def foreign_factory():
                        with pytest.raises(FrameError):
                            NativeReadyTransition.retain(receiver)
                    await asyncio.create_task(foreign_factory())
                    assert receiver._transition is None
                transition = NativeReadyTransition.retain(receiver)
                held["native_transition"] = transition
                with pytest.raises(FrameError):
                    NativeReadyTransition.retain(receiver)
                if mutation == "native_wrong_actor":
                    async def foreign_run():
                        with pytest.raises(FrameError):
                            await transition.run()
                    await asyncio.create_task(foreign_run())
                    assert transition._attempted is False
                observe = ParentAuthorityAdapter._observe
                mutate = JobOwner.remote_transition
                async def changed_observe(adapter, record, phase):
                    result = await observe(adapter, record, phase)
                    if phase == "PRE_GO" and transition._observe_attempted:
                        held["observe_calls"] = held.get("observe_calls", 0) + 1
                        if mutation == "native_observe_false":
                            return False
                        if mutation == "native_observe_key":
                            keys["gateway"].retire()
                        if mutation == "native_data_drift":
                            receiver._buffer_origin[0] ^= 1
                            receiver._buffer_values = bytes(receiver._buffer_origin)
                    return result
                def changed_mutate(job_owner, handle, owned, phase):
                    result = mutate(job_owner, handle, owned, phase)
                    if owned is remote and phase is RemotePhase.READY:
                        held["mutate_calls"] = held.get("mutate_calls", 0) + 1
                        if mutation == "native_transition_key":
                            keys["gateway"].retire()
                        if mutation == "native_transition_error":
                            raise FrameError("SYNTHETIC_POST_NATIVE_READY_ERROR")
                    return result
                monkeypatch.setattr(ParentAuthorityAdapter, "_observe", changed_observe)
                monkeypatch.setattr(JobOwner, "remote_transition", changed_mutate)
                try:
                    await transition.run()
                    held["native_receipt"] = transition.current_phase()
                    # Original BEGIN-only material guard must not borrow READY authority.
                    with pytest.raises(FrameError):
                        NativePhaseWorkOwner._local(producer)
                finally:
                    held["phase_at_transition_boundary"] = (
                        authority._record(operation).owner.inspect_remote(
                            authority._record(operation).handle))
                    monkeypatch.setattr(ParentAuthorityAdapter, "_observe", observe)
                    monkeypatch.setattr(JobOwner, "remote_transition", mutate)
                    before_calls = (held.get("observe_calls", 0), held.get("mutate_calls", 0))
                    with pytest.raises(FrameError):
                        await transition.run()
                    assert before_calls == (held.get("observe_calls", 0),
                                            held.get("mutate_calls", 0))
            # Stop before production dispatch or GO.
            raise FrameError("SYNTHETIC_READY_READ_ONLY")
        if mutation.startswith("dispatch_"):
            from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

            retain = NativeBeginWriter.retain
            if mutation == "dispatch_cancel":
                from hmp_plugin.presentation_authority import ParentAuthorityAdapter

                observe = ParentAuthorityAdapter._observe

                async def cancel_before_ready(adapter, record, phase):
                    result = await observe(adapter, record, phase)
                    reader = channel._credential_ready_receiver_snapshot
                    if phase == "PRE_GO" and reader is not None and reader._complete:
                        held["cancel_before_ready"] = True
                        RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
                    return result

                monkeypatch.setattr(ParentAuthorityAdapter, "_observe", cancel_before_ready)

            def dispatch_writer(cls, producer):
                writer = retain(producer)
                held["writer"] = writer
                writer_retained.set()
                return writer

            monkeypatch.setattr(NativeBeginWriter, "retain", classmethod(dispatch_writer))
            if (mutation == "dispatch_ready" or mutation.startswith("dispatch_go_")
                    or mutation.startswith("dispatch_cleanup_")):
                assert await remote.begin_ready() is True
                cleanup = remote._cleanup_owner_snapshot
                producer = cleanup._credential_work_snapshot
                assert producer._exchange_complete and not producer._exchange_failed
                assert cleanup._ready_fact is cleanup._ready_fact_snapshot
                assert cleanup._ready_snapshot.result() is True
                assert not cleanup._allocations_snapshot[1].task.done()
                assert authority._record(operation).owner.inspect_remote(
                    authority._record(operation).handle) is RemotePhase.READY
                assert remote._go_admission is None and authority._record(operation).child is None
                with pytest.raises(FrameError):
                    channel._credential_work_ready()
                if mutation.startswith("dispatch_go_live"):
                    from hmp_plugin.presentation_jobs import JobOwner
                    from hmp_plugin.presentation_remote import RemoteOperationOwner

                    native_transition = JobOwner.remote_transition
                    held["live_go_sent_calls"] = 0
                    if mutation == "dispatch_go_live_future":
                        publish = RemoteCleanupOwner._publish_write_quiescence
                        held["foreign_cause_calls"] = []

                        def foreign_cause_callback(*args, **kwargs):
                            held["foreign_cause_calls"].append(True)
                            raise AssertionError("foreign cause Future method dispatched")

                        def changed_publish(owned):
                            result = publish(owned)
                            if owned is cleanup and result is True:
                                cleanup._cause_snapshot.add_done_callback = foreign_cause_callback
                            return result

                        monkeypatch.setattr(RemoteCleanupOwner, "_publish_write_quiescence",
                                            changed_publish)
                    if mutation == "dispatch_go_live_final_key":
                        from hmp_plugin.presentation_remote import RemoteOperationOwner

                        check = RemoteOperationOwner._check
                        held["native_sent_checks"] = 0

                        def retire_after_final_check(owned, phase):
                            result = check(owned, phase)
                            if owned is remote and phase is RemotePhase.GO_SENT:
                                held["native_sent_checks"] += 1
                                if held["native_sent_checks"] == 5:
                                    keys["gateway"].retire()
                            return result

                        monkeypatch.setattr(RemoteOperationOwner, "_check",
                                            retire_after_final_check)

                    def observed_go_sent(job_owner, handle, owned_remote, phase):
                        result = native_transition(job_owner, handle, owned_remote, phase)
                        if (owned_remote is remote and phase is RemotePhase.GO_INTENT
                                and mutation.startswith("dispatch_go_live_result_tail")):
                            with pytest.raises(AuthorityRefusalError):
                                RemoteOperationOwner._result_intent_local(
                                    remote, channel, remote._end_snapshot)
                            held["result_tail_before_sent_refused"] = True
                        if owned_remote is remote and phase is RemotePhase.GO_SENT:
                            held["live_go_sent_calls"] += 1
                            held["observed_native_go_sent"] = job_owner.inspect_remote(handle)
                            if mutation.startswith("dispatch_go_live_result_tail"):
                                # Actual original work Task and actual native GO_SENT, no
                                # production result reader or phase mutation in the fixture.
                                try:
                                    RemoteOperationOwner._result_intent_local(
                                        remote, channel, remote._end_snapshot)
                                except BaseException as error:
                                    trace = error.__traceback__
                                    where = []
                                    while trace:
                                        where.append((trace.tb_frame.f_code.co_name,
                                                      trace.tb_lineno))
                                        trace = trace.tb_next
                                    diagnostic = (type(error).__name__, where[-2:])
                                    raise AssertionError(diagnostic) from None
                                held["result_tail_checked"] = True
                                if mutation.endswith("_policy"):
                                    authority._record(operation).policy_work._invalid = True
                                elif mutation.endswith("_listener"):
                                    authority._record(operation).fence.retire()
                                elif mutation.endswith("_scope"):
                                    remote._go_admission = object()
                                elif mutation.endswith("_budget"):
                                    from hmp_plugin.presentation_cancel_budget import (
                                        CancellationBudget,
                                    )
                                    CancellationBudget.refuse(remote._cleanup_budget_snapshot)
                                elif mutation.endswith("_key"):
                                    keys["gateway"].retire()
                                if mutation not in ("dispatch_go_live_result_tail",
                                                    "dispatch_go_live_result_tail_wrong_actor"):
                                    with pytest.raises((FrameError, AuthorityRefusalError)):
                                        RemoteOperationOwner._result_intent_local(
                                            remote, channel, remote._end_snapshot)
                                    held["result_tail_refused"] = True
                            if mutation == "dispatch_go_live_key":
                                keys["gateway"].retire()
                            elif mutation == "dispatch_go_live_cancel":
                                RemoteCleanupOwner.request(cleanup)
                            elif mutation == "dispatch_go_live_error":
                                raise FrameError("SYNTHETIC_POST_GO_SENT_NATIVE_ERROR")
                        return result

                    monkeypatch.setattr(JobOwner, "remote_transition", observed_go_sent)
                    try:
                        if mutation in ("dispatch_go_live", "dispatch_go_live_result_tail",
                                        "dispatch_go_live_result_tail_wrong_actor"):
                            try:
                                assert await remote.go() is True
                            except BaseException:
                                task = cleanup._allocations_snapshot[1].task
                                if task.done() and not task.cancelled():
                                    task.result()
                                raise
                            if mutation == "dispatch_go_live_result_tail_wrong_actor":
                                with pytest.raises(AuthorityRefusalError):
                                    RemoteOperationOwner._result_intent_local(
                                        remote, channel, remote._end_snapshot)
                                assert remote._failed is False
                            assert cleanup._go_notice_fact is channel._go_write_fact_snapshot
                            assert cleanup._go_notice_snapshot.result() is True
                            assert not cleanup._allocations_snapshot[1].task.done()
                            assert authority._record(operation).owner.inspect_remote(
                                authority._record(operation).handle) is RemotePhase.GO_SENT
                        else:
                            with pytest.raises((FrameError, AuthorityRefusalError,
                                                asyncio.CancelledError)):
                                await remote.go()
                            if mutation != "dispatch_go_live_future":
                                assert cleanup._go_notice_fact is None
                    finally:
                        monkeypatch.setattr(JobOwner, "remote_transition", native_transition)
                    writer = producer._go_commitment_snapshot._writer_snapshot
                    held["go_writer"] = writer
                    assert writer._complete and writer._offset == len(writer._scope_snapshot.wire)
                    observed_go = peer.recv(65536)
                    go_wire = writer._scope_snapshot.wire
                    assert observed_go[:len(go_wire)] == go_wire
                    extra = observed_go[len(go_wire):]
                    if extra:
                        cancel_signer = cleanup._credential_cancel_commitment_snapshot
                        assert cancel_signer is not None and cancel_signer._complete
                        cancel_wire = cancel_signer._raw_snapshot + cancel_signer._frame_snapshot
                        async with asyncio.timeout(1):
                            while len(extra) < len(cancel_wire):
                                extra += await asyncio.get_running_loop().sock_recv(
                                    peer, len(cancel_wire) - len(extra))
                        assert extra == cancel_wire and cleanup._cancel_write_completed
                    if mutation.startswith("dispatch_go_live_result_tail"):
                        assert held["result_tail_checked"]
                        assert held["result_tail_before_sent_refused"]
                        if mutation not in ("dispatch_go_live_result_tail",
                                            "dispatch_go_live_result_tail_wrong_actor"):
                            assert held["result_tail_refused"]
                    assert held["live_go_sent_calls"] == 1
                    assert held["observed_native_go_sent"] is RemotePhase.GO_SENT
                    assert remote._go_admission_used is True
                    assert remote._result_owner is None
                    assert cleanup._result_token is None
                    if mutation in ("dispatch_go_live", "dispatch_go_live_result_tail",
                                        "dispatch_go_live_result_tail_wrong_actor"):
                        assert not cleanup._result_notice.done()
                    else:
                        assert cleanup._result_notice.done()
                        assert cleanup._result_notice.result() is False
                    assert not cleanup._cause_snapshot.cancelled()
                    if mutation == "dispatch_go_live_future":
                        assert held["foreign_cause_calls"] == []
                        assert cleanup._cause_snapshot.done()
                    if mutation == "dispatch_go_live_final_key":
                        assert held["native_sent_checks"] == 5
                    assert authority._record(operation).child is None
                elif mutation.startswith("dispatch_go_"):
                    from hmp_plugin import presentation_credential_go as go_module
                    from hmp_plugin.presentation_credential_go import NativeGoCommitment

                    async def signed_go_only(owned_producer):
                        assert owned_producer is producer
                        if mutation == "dispatch_go_wrong_actor":
                            async def wrong_go():
                                with pytest.raises(FrameError):
                                    NativeGoCommitment.retain(producer)
                            await asyncio.create_task(wrong_go())
                            assert producer._go_commitment is None
                        commitment = NativeGoCommitment.retain(producer)
                        held["go_commitment"] = commitment
                        with pytest.raises(FrameError):
                            NativeGoCommitment.retain(producer)
                        if mutation == "dispatch_go_key":
                            encode = go_module.encode_record

                            def revoke_after_sign(*args):
                                raw = encode(*args)
                                keys["gateway"].retire()
                                return raw

                            monkeypatch.setattr(go_module, "encode_record", revoke_after_sign)
                        if mutation == "dispatch_go_revoked":
                            keys["gateway"].retire()
                        if mutation == "dispatch_go_admission":
                            admission = remote._go_admission_snapshot
                            foreign_admission = admission._replace(
                                packet=bytes(bytearray(admission.packet)))
                            remote._go_admission = remote._go_admission_snapshot = foreign_admission
                        if mutation in ("dispatch_go_deadline", "dispatch_go_expected_row",
                                        "dispatch_go_foreign_end"):
                            sample = go_module.NativeClockOwner.sample
                            held["go_foreign_callbacks"] = []

                            class ForeignGoData:
                                def __iter__(self):
                                    held["go_foreign_callbacks"].append("iter")
                                    raise AssertionError("foreign GO data iteration")

                                def __eq__(self, other):
                                    held["go_foreign_callbacks"].append("eq")
                                    raise AssertionError("foreign GO end comparison")

                            def changed_go_clock(clock):
                                now = sample(clock)
                                if (commitment._attempted and asyncio.current_task()
                                        is producer._refs_snapshot[6].task):
                                    if mutation == "dispatch_go_deadline":
                                        return remote._end_snapshot
                                    if not held.get("go_data_changed"):
                                        held["go_data_changed"] = True
                                        scope = commitment._scope_snapshot
                                        if mutation == "dispatch_go_expected_row":
                                            scope = scope._replace(
                                                expected=(ForeignGoData(), *scope.expected[1:]))
                                        else:
                                            foreign = scope.admission._replace(
                                                end_ns=ForeignGoData())
                                            remote._go_admission = foreign
                                            remote._go_admission_snapshot = foreign
                                            scope = scope._replace(admission=foreign)
                                        commitment._scope = commitment._scope_snapshot = scope
                                return now

                            monkeypatch.setattr(go_module.NativeClockOwner, "sample",
                                                changed_go_clock)
                        try:
                            held["go_raw"] = commitment.prepare()
                            if mutation.startswith("dispatch_go_write"):
                                import errno

                                from hmp_plugin import presentation_credential_go_write as go_write
                                from hmp_plugin.presentation_credential_go_write import (
                                    NativeGoWriter,
                                )

                                if mutation == "dispatch_go_write_wrong_actor":
                                    async def wrong_go_writer_factory():
                                        with pytest.raises(FrameError):
                                            NativeGoWriter.retain(commitment)
                                    await asyncio.create_task(wrong_go_writer_factory())
                                    assert commitment._writer is None
                                writer = NativeGoWriter.retain(commitment)
                                held["go_writer"] = writer
                                if mutation == "dispatch_go_write_wrong_actor":
                                    async def wrong_go_write():
                                        with pytest.raises(FrameError):
                                            await writer.write_go()
                                    await asyncio.create_task(wrong_go_write())
                                    assert writer._attempted is False and writer._failed is False
                                send = go_write._SEND
                                held["go_send_calls"] = 0

                                def changed_go_send(sock, data):
                                    held["go_send_calls"] += 1
                                    if mutation == "dispatch_go_write_zero":
                                        return 0
                                    if (mutation in ("dispatch_go_write_eagain",
                                                     "dispatch_go_write_registration")
                                            and held["go_send_calls"] == 1):
                                        raise BlockingIOError(
                                            errno.EAGAIN, "synthetic GO wouldblock")
                                    limit = (37 if mutation == "dispatch_go_write_partial" else
                                             7 if mutation == "dispatch_go_write_unknown"
                                             else len(data))
                                    count = send(sock, data[:limit])
                                    if mutation == "dispatch_go_write_unknown":
                                        raise OSError("synthetic uncertain GO send")
                                    if mutation == "dispatch_go_write_key":
                                        keys["gateway"].retire()
                                    if mutation == "dispatch_go_write_intent_drift":
                                        class ForeignGoIntent:
                                            def __getattribute__(self, name):
                                                held["intent_foreign_callbacks"] = True
                                                raise AssertionError("foreign GO intent getter")
                                        foreign = ForeignGoIntent()
                                        channel._go_write_intent = foreign
                                        channel._go_write_intent_snapshot = foreign
                                    return count

                                monkeypatch.setattr(go_write, "_SEND", changed_go_send)
                                if mutation.startswith("dispatch_go_write_tail_"):
                                    timeout = go_write._TIMEOUT

                                    def changed_go_tail(sock):
                                        value = timeout(sock)
                                        if writer._attempted and not held.get("go_tail_changed"):
                                            held["go_tail_changed"] = True
                                            if mutation == "dispatch_go_write_tail_key":
                                                keys["gateway"].retire()
                                            elif mutation == "dispatch_go_write_tail_cancel":
                                                allocation = writer._scope_snapshot.signed_scope
                                                task = allocation.ready_scope.read_scope.write_scope
                                                assert task.allocation.task.cancel() is True
                                            elif mutation == "dispatch_go_write_tail_policy":
                                                record = authority._record(operation)
                                                record.policy_work._invalid = True
                                            elif mutation == "dispatch_go_write_tail_listener":
                                                authority._record(operation).fence.retire()
                                            else:
                                                admission = remote._go_admission_snapshot
                                                changed = admission._replace(
                                                    packet=bytes(bytearray(admission.packet)))
                                                remote._go_admission = changed
                                                remote._go_admission_snapshot = changed
                                        return value

                                    monkeypatch.setattr(go_write, "_TIMEOUT", changed_go_tail)
                                if mutation == "dispatch_go_write_registration":
                                    from hmp_plugin import presentation_readiness as readiness

                                    install = readiness._install_writer

                                    def unknown_go_install(*args):
                                        install(*args)
                                        raise OSError("synthetic uncertain GO registration")

                                    monkeypatch.setattr(readiness, "_install_writer",
                                                        unknown_go_install)
                                if mutation == "dispatch_go_write_initial":
                                    material = NativeGoCommitment._material_guard

                                    def reject_initial_signer(owned):
                                        result = material(owned)
                                        if owned is commitment and writer._attempted:
                                            held["initial_go_guard_calls"] = (
                                                held.get("initial_go_guard_calls", 0) + 1)
                                            raise FrameError("SYNTHETIC_INITIAL_GO_WRITE_REFUSAL")
                                        return result

                                    monkeypatch.setattr(NativeGoCommitment, "_material_guard",
                                                        reject_initial_signer)
                                try:
                                    await writer.write_go()
                                finally:
                                    with pytest.raises(FrameError):
                                        await writer.write_go()
                                    try:
                                        held["go_actual_wire"] = peer.recv(65536)
                                    except BlockingIOError:
                                        held["go_actual_wire"] = b""
                                    if mutation == "dispatch_go_write_initial":
                                        monkeypatch.setattr(NativeGoCommitment, "_material_guard",
                                                            material)
                                        assert held["initial_go_guard_calls"] == 1
                                        assert held["go_send_calls"] == 0
                        finally:
                            go_record = authority._record(operation)
                            held["go_native_phase"] = go_record.owner.inspect_remote(
                                go_record.handle)
                            assert remote._go_admission_used is True
                            if "go_writer" in held:
                                writer = held["go_writer"]
                                if mutation == "dispatch_go_write_intent_drift":
                                    assert not held.get("intent_foreign_callbacks")
                                else:
                                    assert channel._go_write_intent is writer._scope_snapshot.intent
                                assert (channel._go_write_fact is not None) is writer._complete
                            else:
                                assert channel._go_write_intent is None
                                assert channel._go_write_fact is None
                            with pytest.raises(FrameError):
                                commitment.prepare()
                        raise FrameError("SYNTHETIC_GO_SIGNING_ONLY_NO_WIRE")

                    monkeypatch.setattr(NativePhaseWorkOwner, "exchange_go", signed_go_only)
                    with pytest.raises((FrameError, AuthorityRefusalError, OSError,
                                        asyncio.CancelledError)):
                        await remote.go()
                    commitment = held["go_commitment"]
                    go_success = (mutation in ("dispatch_go_sign", "dispatch_go_wrong_actor")
                                  or mutation.startswith("dispatch_go_write"))
                    pre_attempt_refusal = mutation == "dispatch_go_admission"
                    assert commitment._attempted is not pre_attempt_refusal
                    assert commitment._complete is go_success
                    assert commitment._failed is (not go_success and not pre_attempt_refusal)
                    assert held["go_native_phase"] is (
                        RemotePhase.UNKNOWN if mutation == "dispatch_go_deadline"
                        else RemotePhase.GO_INTENT)
                    assert held.get("go_foreign_callbacks", []) == []
                    if "go_writer" in held:
                        writer = held["go_writer"]
                        write_success = mutation in (
                            "dispatch_go_write", "dispatch_go_write_partial",
                            "dispatch_go_write_eagain", "dispatch_go_write_wrong_actor",
                            "dispatch_go_write_release_cleanup",
                            "dispatch_go_write_release_allocation")
                        assert writer._complete is write_success
                        assert writer._failed is not write_success
                        assert writer._unknown is (mutation in (
                            "dispatch_go_write_unknown", "dispatch_go_write_registration",
                            "dispatch_go_write_intent_drift",
                            "dispatch_go_write_tail_admission"))
                        expected_wire = writer._scope_snapshot.wire
                        assert held["go_actual_wire"] == expected_wire[:len(held["go_actual_wire"])]
                        if write_success:
                            assert writer._offset == len(expected_wire)
                            assert channel._go_write_fact is writer._fact_snapshot
                        elif mutation == "dispatch_go_write_unknown":
                            assert writer._offset == 0 and len(held["go_actual_wire"]) == 7
                        elif mutation in (
                            "dispatch_go_write_zero", "dispatch_go_write_registration",
                            "dispatch_go_write_initial", "dispatch_go_write_tail_key",
                            "dispatch_go_write_tail_cancel", "dispatch_go_write_tail_policy",
                            "dispatch_go_write_tail_listener", "dispatch_go_write_tail_admission"):
                            assert writer._offset == 0 and held["go_actual_wire"] == b""
                            if mutation.startswith("dispatch_go_write_tail_"):
                                assert held["go_send_calls"] == 0
                        else:
                            assert writer._offset == len(expected_wire)
                    if go_success:
                        from hmp_plugin.presentation_credential_phase import (
                            check_commitment,
                            check_complete_frame,
                        )

                        scope = commitment._scope_snapshot
                        checked = check_commitment(held["go_raw"], sender_public=scope.pins[0],
                            receiver_public=scope.pins[1], expected=dict(scope.expected))
                        header = check_complete_frame(checked, scope.frame,
                                                      binding=remote._binding_snapshot)
                        assert header.kind == "GO" and header.sequence == 1
                    else:
                        assert commitment._raw is None and "go_raw" not in held
                if mutation.startswith("dispatch_cleanup_"):
                    from hmp_plugin.presentation_broker_service import SocketChannel
                    from hmp_plugin.presentation_cancel_budget import CancellationBudget

                    if mutation.endswith("_after_go"):
                        assert await remote.go() is True
                        held["cleanup_prior_go_wire"] = peer.recv(65536)
                        assert held["cleanup_prior_go_wire"]

                    async def material_only_cancel(owned_channel, owned_cleanup):
                        assert owned_channel is channel and owned_cleanup is cleanup
                        held["cleanup_material_called"] = True
                        held["original_cleanup_allocations"] = cleanup._allocations_snapshot
                        before = CancellationBudget.inspect(cleanup._refs_snapshot[8])
                        assert before[2] is not None
                        if mutation.startswith("dispatch_cleanup_sign"):
                            from hmp_plugin import (
                                presentation_credential_cancel_commitment as cancel,
                            )
                            from hmp_plugin.presentation_credential_phase import (
                                check_commitment,
                                check_complete_frame,
                            )

                            if mutation == "dispatch_cleanup_sign_wrong_actor":
                                async def wrong_cancel_signer():
                                    with pytest.raises(FrameError):
                                        cancel.NativeCancelCommitment.retain(cleanup)
                                await asyncio.create_task(wrong_cancel_signer())
                                assert cleanup._credential_cancel_commitment is None
                            commitment = cancel.NativeCancelCommitment.retain(cleanup)
                            held["cancel_commitment"] = commitment
                            with pytest.raises(FrameError):
                                cancel.NativeCancelCommitment.retain(cleanup)
                            if mutation == "dispatch_cleanup_sign_key":
                                encode = cancel.encode_record

                                def retire_cancel_key(*args):
                                    raw = encode(*args)
                                    keys["gateway"].retire()
                                    return raw

                                monkeypatch.setattr(cancel, "encode_record", retire_cancel_key)
                            if mutation in ("dispatch_cleanup_sign_expired",
                                            "dispatch_cleanup_sign_expired_prepared"):
                                remaining = RemoteCleanupOwner._remaining
                                prepare_native = RemoteCleanupOwner._prepare_cancel

                                def observed_native_prepare(owned, owned_channel):
                                    frame = prepare_native(owned, owned_channel)
                                    if owned is cleanup:
                                        held["native_cancel_prepared"] = True
                                    return frame

                                monkeypatch.setattr(RemoteCleanupOwner, "_prepare_cancel",
                                                    observed_native_prepare)

                                def no_cancel_time(owned):
                                    value = remaining(owned)
                                    if (owned is cleanup and commitment._attempted
                                            and (mutation == "dispatch_cleanup_sign_expired"
                                                 or held.get("native_cancel_prepared"))):
                                        return 0.0
                                    return value

                                monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                    no_cancel_time)
                            if mutation in ("dispatch_cleanup_sign_expected_row",
                                            "dispatch_cleanup_sign_foreign_end"):
                                sign_data = cancel.signing_bytes
                                held["foreign_cancel_calls"] = []

                                class ForeignCancelData:
                                    def __iter__(self):
                                        held["foreign_cancel_calls"].append("iter")
                                        raise AssertionError("foreign CANCEL rows iterated")

                                    def __eq__(self, other):
                                        held["foreign_cancel_calls"].append("eq")
                                        raise AssertionError("foreign CANCEL end compared")

                                def replaced_cancel_metadata(statement):
                                    data = sign_data(statement)
                                    if mutation == "dispatch_cleanup_sign_expected_row":
                                        rows = (ForeignCancelData(),
                                                *commitment._expected_snapshot[1:])
                                        commitment._expected = commitment._expected_snapshot = rows
                                    else:
                                        foreign = ForeignCancelData()
                                        cleanup._cancel_end = cleanup._cancel_end_snapshot = foreign
                                    return data

                                monkeypatch.setattr(cancel, "signing_bytes",
                                                    replaced_cancel_metadata)
                            success = (mutation in ("dispatch_cleanup_sign",
                                                    "dispatch_cleanup_sign_after_go",
                                                    "dispatch_cleanup_sign_wrong_actor")
                                       or mutation.startswith("dispatch_cleanup_sign_write"))
                            try:
                                if success:
                                    raw = commitment.prepare()
                                    scope = commitment._scope_snapshot
                                    checked = check_commitment(raw, sender_public=scope.pins[0],
                                        receiver_public=scope.pins[1],
                                        expected=dict(commitment._expected_snapshot))
                                    header = check_complete_frame(checked,
                                        commitment._frame_snapshot,
                                        binding=remote._binding_snapshot)
                                    assert header.kind == "CANCEL" and header.body_length == 16
                                    assert header.sequence == (
                                        2 if mutation.endswith("_after_go") else 1)
                                    assert commitment._end_snapshot == before[2]
                                else:
                                    with pytest.raises(FrameError):
                                        commitment.prepare()
                                    assert commitment._raw is None
                            finally:
                                with pytest.raises(FrameError):
                                    commitment.prepare()
                            assert commitment._attempted is True
                            assert commitment._complete is success
                            assert commitment._failed is not success
                            after = CancellationBudget.inspect(cleanup._refs_snapshot[8])
                            assert after[0] == before[0] and after[2] == before[2]
                            assert after[3] is False and after[1] >= before[1]
                            assert held.get("foreign_cancel_calls", []) == []
                            if mutation.startswith("dispatch_cleanup_sign_write"):
                                import errno

                                from hmp_plugin import presentation_credential_cancel_write as write

                                if mutation == "dispatch_cleanup_sign_write_wrong_actor":
                                    async def wrong_cancel_writer():
                                        with pytest.raises(FrameError):
                                            write.NativeCancelWriter.retain(commitment)
                                    await asyncio.create_task(wrong_cancel_writer())
                                    assert commitment._writer is None
                                writer = write.NativeCancelWriter.retain(commitment)
                                held["cancel_writer"] = writer
                                if mutation == "dispatch_cleanup_sign_write_wrong_actor":
                                    async def wrong_cancel_write():
                                        with pytest.raises(FrameError):
                                            await writer.write_cancel()
                                    await asyncio.create_task(wrong_cancel_write())
                                    assert writer._attempted is False and writer._failed is False
                                send = write._SEND
                                held["cancel_send_calls"] = 0

                                def changed_cancel_send(sock, data):
                                    held["cancel_send_calls"] += 1
                                    if mutation == "dispatch_cleanup_sign_write_zero":
                                        return 0
                                    if (mutation in ("dispatch_cleanup_sign_write_eagain",
                                                     "dispatch_cleanup_sign_write_registration")
                                            and held["cancel_send_calls"] == 1):
                                        raise BlockingIOError(errno.EAGAIN, "synthetic CANCEL wait")
                                    if mutation == "dispatch_cleanup_sign_write_partial":
                                        limit = 41
                                    elif mutation == "dispatch_cleanup_sign_write_unknown":
                                        limit = 7
                                    else:
                                        limit = len(data)
                                    count = send(sock, data[:limit])
                                    if mutation == "dispatch_cleanup_sign_write_unknown":
                                        raise OSError("synthetic uncertain CANCEL send")
                                    if mutation == "dispatch_cleanup_sign_write_key":
                                        keys["gateway"].retire()
                                    return count

                                monkeypatch.setattr(write, "_SEND", changed_cancel_send)
                                if mutation == "dispatch_cleanup_sign_write_registration":
                                    from hmp_plugin import presentation_readiness as readiness

                                    install = readiness._install_writer

                                    def unknown_cancel_registration(*args):
                                        install(*args)
                                        raise OSError("synthetic uncertain CANCEL registration")

                                    monkeypatch.setattr(readiness, "_install_writer",
                                                        unknown_cancel_registration)
                                if mutation in ("dispatch_cleanup_sign_write_tail_key",
                                                "dispatch_cleanup_sign_write_tail_cancel",
                                                "dispatch_cleanup_sign_write_foreign_intent_after_go"):
                                    timeout = write._TIMEOUT
                                    held["foreign_cancel_intent_calls"] = []

                                    class ForeignCancelGoIntent:
                                        def __getattribute__(self, name):
                                            held["foreign_cancel_intent_calls"].append(name)
                                            raise AssertionError("foreign CANCEL GO intent getter")

                                    def changed_cancel_timeout(sock):
                                        value = timeout(sock)
                                        if (writer._attempted
                                                and not held.get("cancel_tail_changed")):
                                            held["cancel_tail_changed"] = True
                                            if mutation == "dispatch_cleanup_sign_write_tail_key":
                                                keys["gateway"].retire()
                                            elif mutation.endswith("_tail_cancel"):
                                                signed = writer._scope_snapshot.signed_scope
                                                assert signed.allocation.task.cancel() is True
                                            else:
                                                scope = writer._scope_snapshot
                                                forged = scope.go._replace(
                                                    intent=ForeignCancelGoIntent())
                                                channel._go_write_fact = forged
                                                channel._go_write_fact_snapshot = forged
                                                changed = scope._replace(go=forged)
                                                writer._scope = writer._scope_snapshot = changed
                                                with pytest.raises(FrameError):
                                                    writer._begin_writing(
                                                        scope.signed_scope.ready_scope.read_scope.writer)
                                                assert held["foreign_cancel_intent_calls"] == []
                                        return value

                                    monkeypatch.setattr(write, "_TIMEOUT", changed_cancel_timeout)
                                write_success = mutation not in (
                                    "dispatch_cleanup_sign_write_unknown",
                                    "dispatch_cleanup_sign_write_key",
                                    "dispatch_cleanup_sign_write_tail_key",
                                    "dispatch_cleanup_sign_write_foreign_intent_after_go",
                                    "dispatch_cleanup_sign_write_zero",
                                    "dispatch_cleanup_sign_write_registration",
                                    "dispatch_cleanup_sign_write_tail_cancel")
                                if write_success:
                                    await writer.write_cancel()
                                else:
                                    with pytest.raises((FrameError, AuthorityRefusalError,
                                                        OSError)):
                                        await writer.write_cancel()
                                with pytest.raises(FrameError):
                                    await writer.write_cancel()
                                try:
                                    actual_wire = peer.recv(65536)
                                except BlockingIOError:
                                    actual_wire = b""
                                expected_wire = writer._scope_snapshot.wire
                                assert actual_wire == expected_wire[:len(actual_wire)]
                                assert writer._complete is write_success
                                assert writer._failed is not write_success
                                assert writer._unknown is (mutation in (
                                    "dispatch_cleanup_sign_write_unknown",
                                    "dispatch_cleanup_sign_write_foreign_intent_after_go",
                                    "dispatch_cleanup_sign_write_registration"))
                                assert cleanup._cancel_write_completed is write_success
                                assert writer._scope_snapshot.end == before[2]
                                if write_success:
                                    assert writer._offset == len(expected_wire)
                                elif mutation == "dispatch_cleanup_sign_write_unknown":
                                    assert writer._offset == 0 and len(actual_wire) == 7
                                elif mutation in ("dispatch_cleanup_sign_write_tail_key",
                                                  "dispatch_cleanup_sign_write_tail_cancel",
                                                  "dispatch_cleanup_sign_write_foreign_intent_after_go"):
                                    assert writer._offset == 0 and actual_wire == b""
                                    assert held["cancel_send_calls"] == 0
                                    assert held["foreign_cancel_intent_calls"] == []
                                elif mutation in ("dispatch_cleanup_sign_write_zero",
                                                  "dispatch_cleanup_sign_write_registration"):
                                    assert writer._offset == 0 and actual_wire == b""
                                    assert held["cancel_send_calls"] == 1
                                else:
                                    assert writer._offset == len(expected_wire)
                            else:
                                assert cleanup._cancel_write_completed is False
                            assert cleanup._cancel_write_attempted is (
                                mutation != "dispatch_cleanup_sign_expired")
                            raise FrameError("SYNTHETIC_CANCEL_SIGNING_ONLY_NO_IO")
                        if mutation == "dispatch_cleanup_material_wrong_actor":
                            async def wrong_cleanup_role():
                                with pytest.raises(FrameError):
                                    producer._cleanup_material(cleanup)
                            await asyncio.create_task(wrong_cleanup_role())
                        if mutation in ("dispatch_cleanup_material_allocations",
                                        "dispatch_cleanup_material_slots"):
                            from hmp_plugin import presentation_remote_cleanup as cleanup_module

                            native_timeout = cleanup_module._SOCKET_TIMEOUT
                            held["material_foreign_calls"] = []

                            class ForeignCleanupRows:
                                def __getitem__(self, key):
                                    held["material_foreign_calls"].append(key)
                                    raise AssertionError("foreign cleanup rows indexed")

                            def replaced_tail(sock):
                                result = native_timeout(sock)
                                if mutation == "dispatch_cleanup_material_allocations":
                                    foreign = ForeignCleanupRows()
                                    cleanup._allocations = cleanup._allocations_snapshot = foreign
                                else:
                                    foreign = ForeignCleanupRows()
                                    cleanup._slots = cleanup._slots_snapshot = foreign
                                return result

                            monkeypatch.setattr(cleanup_module, "_SOCKET_TIMEOUT", replaced_tail)
                            with pytest.raises(FrameError):
                                producer._cleanup_material(cleanup)
                            assert held["material_foreign_calls"] == []
                        elif mutation == "dispatch_cleanup_material_key":
                            keys["gateway"].retire()
                            with pytest.raises(FrameError):
                                producer._cleanup_material(cleanup)
                        else:
                            material = producer._cleanup_material(cleanup)
                            assert material[0] is remote and material[2] is channel
                            assert cleanup._allocations_snapshot[1].task.done()
                        assert CancellationBudget.inspect(cleanup._refs_snapshot[8]) == before
                        assert cleanup._cancel_write_attempted is False
                        assert cleanup._cancel_wire is None
                        raise FrameError("SYNTHETIC_CLEANUP_ROLE_ONLY_NO_SIGN_OR_IO")

                    if mutation.startswith("dispatch_cleanup_route"):
                        from hmp_plugin import presentation_credential_cancel_write as write

                        send = write._SEND
                        held["route_wire"] = bytearray()
                        held["route_send_calls"] = 0

                        def observed_route_send(sock, data):
                            held["route_send_calls"] += 1
                            count = send(sock, data)
                            held["route_wire"].extend(data[:count])
                            return count

                        monkeypatch.setattr(write, "_SEND", observed_route_send)
                        if mutation == "dispatch_cleanup_route_wrong_actor":
                            before = CancellationBudget.inspect(cleanup._refs_snapshot[8])
                            with pytest.raises(AuthorityRefusalError):
                                await RemoteCleanupOwner._send_credential_cancel(cleanup, channel)
                            assert cleanup._credential_cancel_commitment is None
                            assert cleanup._cancel_write_attempted is False
                            assert cleanup._unknown is False
                            assert CancellationBudget.inspect(cleanup._refs_snapshot[8]) == before
                        if mutation == "dispatch_cleanup_route_initial_failure":
                            from hmp_plugin.presentation_credential_cancel_commitment import (
                                NativeCancelCommitment,
                            )

                            actor = RemoteCleanupOwner._cancel_actor
                            retain = NativeCancelCommitment.retain
                            held["initial_route_native_calls"] = 0

                            def failed_initial_actor(owned, owned_channel):
                                actor(owned, owned_channel)
                                if owned is cleanup:
                                    held["initial_route_native_calls"] += 1
                                    assert cleanup._credential_cancel_commitment is not None
                                    raise FrameError("SYNTHETIC_INITIAL_ROUTE_NATIVE_FAILURE")

                            def observed_failed_retain(cls, owned):
                                try:
                                    return retain(owned)
                                except FrameError:
                                    original = cleanup._credential_cancel_commitment_snapshot
                                    assert original is not None and original._failed
                                    # White-box restoration tests only the consumed-owner fence.
                                    # No actual preparation/IO or authority is retried.
                                    monkeypatch.setattr(RemoteCleanupOwner, "_cancel_actor", actor)
                                    original._failed = False
                                    try:
                                        with pytest.raises(FrameError):
                                            retain(owned)
                                    finally:
                                        original._failed = True
                                    assert (cleanup._credential_cancel_commitment_snapshot
                                            is original)
                                    assert held["initial_route_native_calls"] == 1
                                    assert cleanup._cancel_write_attempted is False
                                    raise

                            monkeypatch.setattr(RemoteCleanupOwner, "_cancel_actor",
                                                failed_initial_actor)
                            monkeypatch.setattr(NativeCancelCommitment, "retain",
                                                classmethod(observed_failed_retain))
                        if mutation.startswith("dispatch_cleanup_route_key"):
                            keys["gateway"].retire()
                        if mutation == "dispatch_cleanup_route_key_expired":
                            remaining = RemoteCleanupOwner._remaining

                            def expired_local_refusal(owned):
                                value = remaining(owned)
                                signer = cleanup._credential_cancel_commitment_snapshot
                                if owned is cleanup and signer is not None and signer._failed:
                                    return 0.0
                                return value

                            monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                expired_local_refusal)
                        if mutation in ("dispatch_cleanup_route_key_cancelled",
                                        "dispatch_cleanup_route_key_read_debt"):
                            from hmp_plugin.presentation_credential_cancel_commitment import (
                                NativeCancelCommitment,
                            )

                            retain_failed = NativeCancelCommitment.retain

                            def changed_failed_signer(cls, owned):
                                try:
                                    return retain_failed(owned)
                                except FrameError:
                                    signer = cleanup._credential_cancel_commitment_snapshot
                                    assert signer is not None and signer._failed
                                    if mutation == "dispatch_cleanup_route_key_cancelled":
                                        assert signer._scope_snapshot.allocation.task.cancel()
                                    else:
                                        receiver = channel._credential_ready_receiver_snapshot
                                        receiver._io_unknown = True
                                    raise

                            monkeypatch.setattr(NativeCancelCommitment, "retain",
                                                classmethod(changed_failed_signer))
                    else:
                        monkeypatch.setattr(SocketChannel, "send_cancel", material_only_cancel)
                RemoteCleanupOwner.request(cleanup)
                # Actual owned cleanup may retain UNKNOWN: signed cleanup relay
                # is not integrated by this READY-only dispatch slice.
                try:
                    async with asyncio.timeout(2):
                        result = await asyncio.shield(cleanup._allocations_snapshot[0].task)
                except asyncio.CancelledError:
                    assert mutation in ("dispatch_cleanup_sign_write_tail_cancel",
                                        "dispatch_cleanup_route_key_cancelled")
                    assert cleanup._allocations_snapshot[0].task.cancelled()
                    result = False  # actual cancelled cleanup is not settlement evidence
                assert type(result) is bool
                original_allocations = held.get("original_cleanup_allocations",
                                                cleanup._allocations_snapshot)
                assert original_allocations[1].task.done()
                held["joined_work_outcome"] = await asyncio.gather(
                    original_allocations[1].task, return_exceptions=True)
                assert result is True or cleanup._unknown is True
                if mutation.startswith("dispatch_cleanup_route"):
                    from hmp_plugin.presentation_cancel_budget import CancellationWindow
                    from hmp_plugin.presentation_credential_codec import payload_size
                    from hmp_plugin.presentation_credential_phase import (
                        check_commitment,
                        check_complete_frame,
                    )

                    commitment = cleanup._credential_cancel_commitment_snapshot
                    assert commitment is not None
                    if (mutation.startswith("dispatch_cleanup_route_key")
                            or mutation == "dispatch_cleanup_route_initial_failure"):
                        assert result is False and cleanup._unknown is True
                        assert held["route_send_calls"] == 0 and held["route_wire"] == b""
                        assert commitment._failed and not commitment._complete
                        local_closed = mutation in (
                            "dispatch_cleanup_route_key", "dispatch_cleanup_route_initial_failure")
                        assert cleanup._socket_closed is local_closed
                        assert cleanup._clock_closed is local_closed
                        assert channel._closed_known is local_closed
                        assert channel._clock_closed_known is local_closed
                        if not local_closed:
                            assert channel._close_attempted is False
                    else:
                        assert result is True and cleanup._unknown is False
                        assert cleanup._socket_closed and cleanup._clock_closed
                        assert cleanup._cancel_write_completed and commitment._complete
                        wire = bytes(held["route_wire"])
                        observed = bytearray()
                        async with asyncio.timeout(1):
                            while len(observed) < len(wire):
                                chunk = await asyncio.get_running_loop().sock_recv(
                                    peer, len(wire) - len(observed))
                                assert chunk
                                observed.extend(chunk)
                        assert bytes(observed) == wire
                        cut = 8 + payload_size(wire[:8])
                        scope = commitment._scope_snapshot
                        expected = dict(scope.ready_scope.read_scope.expected)
                        expected.update(phase="CANCEL", role="gateway", direction="g2b",
                            sequence=2 if mutation.endswith("_after_go") else 1)
                        checked = check_commitment(wire[:cut], sender_public=scope.pins[0],
                            receiver_public=scope.pins[1], expected=expected)
                        header = check_complete_frame(checked, wire[cut:],
                                                      binding=remote._binding_snapshot)
                        assert header.kind == "CANCEL" and header.body_length == 16
                        window = CancellationWindow.decode(wire[-16:])
                        assert window.end_ns == cleanup._cancel_end_snapshot
                        assert window.end_ns <= remote._end_snapshot + 250_000_000
                        assert not cleanup._result_token and remote._result_owner is None
                elif mutation.startswith("dispatch_cleanup_"):
                    assert held.get("cleanup_material_called") is True
                if mutation in ("dispatch_go_write_release_cleanup",
                                "dispatch_go_write_release_allocation"):
                    held["release_foreign_callbacks"] = []

                    class ForeignGoCleanup:
                        def __getattribute__(self, name):
                            held["release_foreign_callbacks"].append(name)
                            raise AssertionError("foreign GO cleanup getter")

                        def __getitem__(self, key):
                            held["release_foreign_callbacks"].append(key)
                            raise AssertionError("foreign GO allocation indexing")

                    closed_before_drift = channel._closed_known
                    close_fact_before_drift = channel._close_fact_snapshot
                    foreign = ForeignGoCleanup()
                    if mutation == "dispatch_go_write_release_cleanup":
                        remote._cleanup_owner = remote._cleanup_owner_snapshot = foreign
                    else:
                        cleanup._allocations = cleanup._allocations_snapshot = foreign
                    from hmp_plugin.presentation_credential_go_write import NativeGoWriter

                    with pytest.raises(FrameError):
                        NativeGoWriter._released(held["go_writer"], channel)
                    assert held["release_foreign_callbacks"] == []
                    assert channel.close() is False
                    assert channel._closed_known is closed_before_drift
                    assert channel._close_fact_snapshot is close_fact_before_drift
            else:
                with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
                    await remote.begin_ready()
                if mutation == "dispatch_cancel":
                    assert held["cancel_before_ready"] is True
                assert remote._cleanup_owner_snapshot._ready_fact is None
                assert remote._cleanup_owner_snapshot._credential_work_snapshot._exchange_failed
            async with asyncio.timeout(2):
                await peer_task
            if mutation.startswith("dispatch_cleanup_") and mutation.endswith("_after_go"):
                assert remote._go_admission_used is True
            elif mutation.startswith("dispatch_go_"):
                assert remote._go_admission_used is True
                if "go_writer" not in held:
                    assert channel._go_write_intent is None and channel._go_write_fact is None
            else:
                assert remote._go_admission is None
            assert authority._record(operation).child is None
            assert authority._record(operation).owner.inspect_remote(
                authority._record(operation).handle) is RemotePhase.UNKNOWN
            return
        monkeypatch.setattr(NativePhaseWorkOwner, "exchange_ready", source_only_exchange)
        with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
            await remote.begin_ready()
        if (mutation in ("cancel_wait", "cancel_wait_partial")
                or mutation.startswith("cancel_wait_key")):
            async with asyncio.timeout(2):
                cleanup_task = remote._cleanup_owner_snapshot._allocations_snapshot[0].task
                try:
                    held["automatic_pre_ready_closed"] = await asyncio.shield(cleanup_task)
                except asyncio.CancelledError:
                    assert mutation == "cancel_wait_key_cancelled" and cleanup_task.cancelled()
                    held["automatic_pre_ready_closed"] = False  # no settlement inferred
        if mutation.startswith("cancel_wait_sign"):
            async with asyncio.timeout(2):
                cleanup_task = remote._cleanup_owner_snapshot._allocations_snapshot[0].task
                try:
                    assert await asyncio.shield(cleanup_task) is False
                except asyncio.CancelledError:
                    assert mutation == "cancel_wait_sign_write_tail_cancel"
                    assert cleanup_task.cancelled()
        async with asyncio.timeout(2):
            await peer_task  # fixture rendezvous bound, not a protocol deadline
        if mutation.startswith("composed_"):
            producer = held["exchange_producer"]
            succeeds = mutation != "composed_signature"
            assert producer._exchange_attempted is True
            assert producer._exchange_complete is succeeds
            assert producer._exchange_failed is not succeeds
            assert (held.get("exchange_receipt") is not None) is succeeds
            assert held["exchange_phase"] is (
                RemotePhase.READY if succeeds else RemotePhase.BEGIN_INTENT)
            assert remote._go_admission is None and authority._record(operation).child is None
            with pytest.raises(FrameError):
                channel._credential_work_ready()
            return
        receiver = held["receiver"]
        native_case = mutation.startswith("native_")
        succeeds = mutation in ("ready", "fragmented", "wrong_actor", "missing_write")
        read_complete = succeeds or mutation == "current_key" or native_case
        known_cancel = (mutation in ("cancel_wait", "cancel_wait_partial")
                        or mutation.startswith(("cancel_wait_key", "cancel_wait_sign")))
        if mutation == "cancel_wait_key_read_debt":
            known_cancel = False
        io_unknown = not read_complete and mutation != "admission_refusal" and not known_cancel
        assert receiver._complete is read_complete
        assert receiver._failed is (not read_complete or mutation in (
            "current_key", "native_observe_key"))
        assert receiver._io_unknown is io_unknown
        assert channel._reading is (False if mutation == "cancel_wait_key_read_debt"
                                    else io_unknown)
        assert remote._send_completed and remote._receive_claimed
        assert remote._go_admission is None and authority._record(operation).child is None
        assert receiver._admission_attempted and receiver._claim_attempted
        assert receiver._claim_complete is (mutation != "admission_refusal")
        assert receiver._target <= 3080 and receiver._consumed <= receiver._target
        before = receiver._consumed
        if succeeds:
            fact = held["ready_fact"]
            assert fact.raw + fact.frame == held["ready_wire"]
            assert bytes(fact.buffer) == held["ready_wire"]
            assert fact.scope.write_scope is held["writer"]._scope_snapshot
            assert fact.count == fact.target == len(held["ready_wire"])
        if native_case:
            transition = held["native_transition"]
            native_success = mutation in ("native_ready", "native_wrong_actor")
            mutated = native_success or mutation in (
                "native_transition_key", "native_transition_error")
            assert transition._complete is native_success
            assert transition._failed is not native_success
            assert transition._attempted and transition._observe_attempted
            assert held["observe_calls"] == 1
            assert held.get("mutate_calls", 0) == int(mutated)
            assert transition._native_attempted is mutated
            phase = held["phase_at_transition_boundary"]
            assert phase is (RemotePhase.READY if mutated else RemotePhase.BEGIN_INTENT)
            assert authority._record(operation).owner.inspect_remote(
                authority._record(operation).handle) is RemotePhase.UNKNOWN
            assert (held.get("native_receipt") is not None) is native_success
            assert (transition._receipt is not None) is native_success
        if mutation == "native_data_drift":
            with pytest.raises(FrameError):
                NativeReadyReceiver._released(receiver, channel)
        elif not io_unknown:
            NativeReadyReceiver._released(receiver, channel)
            if known_cancel:
                assert receiver._cancel_release_origin is not None
                assert receiver._scope_origin.write_scope.allocation.task.cancelled()
                assert receiver._completion is None and receiver._failed
                stopped = receiver._cancel_release_origin
                assert not hasattr(stopped, "values")
                assert stopped.consumed == (4 if mutation in (
                    "cancel_wait_partial", "cancel_wait_sign_partial") else 0)
                assert not receiver._buffer_origin and receiver._buffer_values == b""
                error = held["read_error"]
                assert type(error) is asyncio.CancelledError and error.__context__ is None
                trace = error.__traceback__
                while trace:
                    if trace.tb_frame.f_code.co_filename.endswith(
                            "presentation_credential_ready_read.py"):
                        for name in ("part", "values", "prefix", "raw", "framed", "header",
                                     "checked"):
                            assert trace.tb_frame.f_locals.get(name) is None
                    trace = trace.tb_next
                with pytest.raises(FrameError):
                    NativeReadyReceiver._released(receiver, broker)
        else:
            assert receiver._completion is None
            assert not receiver._scope_origin.buffer and receiver._pending is None
            error = held["read_error"]
            error_type = (asyncio.CancelledError if mutation in (
                "cancel_wait_generic", "cancel_wait_progress", "cancel_wait_key_read_debt")
                else FrameError)
            assert type(error) is error_type
            assert error.__context__ is None
            trace = error.__traceback__
            while trace:
                filename = trace.tb_frame.f_code.co_filename
                if filename.endswith("presentation_credential_ready_read.py"):
                    local = trace.tb_frame.f_locals
                    for name in ("part", "values", "prefix", "raw", "framed", "header", "checked"):
                        assert local.get(name) is None
                trace = trace.tb_next
            if mutation == "buffer_drift":
                assert held["foreign_buffer"] == b"PRESERVE_FOREIGN_READY_BUFFER"
            if mutation in ("target_drift", "count_drift"):
                assert receiver._last_read == (0, 8, 8)  # actual count survives callback drift
            with pytest.raises(FrameError):
                NativeReadyReceiver._released(receiver, channel)
        if mutation.startswith("cancel_wait"):
            assert held["cancel_getters"] == []
        if (mutation in ("cancel_wait", "cancel_wait_partial")
                or mutation.startswith("cancel_wait_key")):
            cleanup = remote._cleanup_owner_snapshot
            signer = cleanup._pre_ready_cancel_commitment_snapshot
            assert signer is not None
            if mutation.startswith("cancel_wait_key"):
                assert held["automatic_pre_ready_closed"] is False
                socket_closed = mutation in ("cancel_wait_key", "cancel_wait_key_clock_expired")
                clock_closed = mutation == "cancel_wait_key"
                assert cleanup._unknown and cleanup._socket_closed is socket_closed
                assert cleanup._clock_closed is clock_closed
                assert channel._closed_known is socket_closed
                assert channel._clock_closed_known is clock_closed
                if not socket_closed:
                    assert channel._close_attempted is False
                assert signer._failed and signer._raw_snapshot is None
                assert signer._writer_snapshot is None and not cleanup._cancel_write_attempted
            else:
                assert held["automatic_pre_ready_closed"] is True
                assert cleanup._socket_closed and cleanup._clock_closed
                cancel_writer = signer._writer_snapshot
                assert cancel_writer._complete and cleanup._cancel_write_completed
                wire = cancel_writer._scope_snapshot.wire
                observed = bytearray()
                async with asyncio.timeout(2):
                    while len(observed) < len(wire):
                        part = await asyncio.get_running_loop().sock_recv(
                            peer, len(wire) - len(observed))
                        assert part
                        observed.extend(part)
                assert bytes(observed) == wire
            assert cleanup._credential_cancel_commitment_snapshot is None
            assert cleanup._credential_work_snapshot._ready_transition_snapshot is None
        if mutation.startswith("cancel_wait_sign"):
            assert held["pre_ready_called"]
            if "pre_ready_signer" not in held:
                raise held["pre_ready_callback_error"]
            signer = held["pre_ready_signer"]
            assert signer._complete is (mutation in (
                "cancel_wait_sign", "cancel_wait_sign_partial", "cancel_wait_sign_wrong_actor")
                or mutation.startswith("cancel_wait_sign_write"))
            assert signer._raw_snapshot is held.get("pre_ready_signed")
            if mutation.startswith("cancel_wait_sign_write"):
                cancel_writer = held["pre_ready_writer"]
                assert channel._credential_cancel_writer_snapshot is cancel_writer
                if cancel_writer._complete:
                    wire = cancel_writer._scope_snapshot.wire
                    observed = bytearray()
                    async with asyncio.timeout(2):
                        while len(observed) < len(wire):
                            observed.extend(await asyncio.get_running_loop().sock_recv(
                                peer, len(wire) - len(observed)))
                    assert bytes(observed) == wire
                    assert cancel_writer._offset == len(wire)
                else:
                    assert cancel_writer._fact_snapshot is None
                if mutation.endswith(("_tail_key", "_tail_unknown", "_tail_cancel")):
                    assert held["pre_ready_final_tail"]
                    assert held["pre_ready_send_calls"] == 0
                if mutation in ("cancel_wait_sign_write_unknown",
                                "cancel_wait_sign_write_registration"):
                    assert cancel_writer._unknown and channel._writing
            else:
                assert channel._credential_cancel_writer_snapshot is None
        if mutation == "pin_drift":
            assert held["pin_callbacks"] == [] and receiver._consumed == 0
        with pytest.raises(FrameError):
            await receiver.run()
        assert receiver._consumed is before  # retry cannot change original custody/debt
        with pytest.raises(FrameError):
            channel._credential_work_ready()
    finally:
        peer_task.cancel()
        await asyncio.gather(peer_task, return_exceptions=True)
        assert broker.close() and broker.close_clock()
        for key in keys.values():
            key.retire()
