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
    "cancel_wait", "pin_drift", "native_ready", "native_wrong_actor", "native_observe_false",
    "native_observe_key", "native_transition_error", "native_transition_key", "native_data_drift",
    "composed_ready", "composed_signature", "composed_wrong_actor",
    "dispatch_ready", "dispatch_signature", "dispatch_cancel",
    "dispatch_go_sign", "dispatch_go_key", "dispatch_go_wrong_actor",
    "dispatch_go_revoked", "dispatch_go_admission", "dispatch_go_deadline",
    "dispatch_go_expected_row", "dispatch_go_foreign_end",
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
            if mutation == "cancel_wait":
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
            assert remote._send_completed and remote._receive_claimed
            with pytest.raises(FrameError):
                NativeReadyReceiver.retain(writer)
            if mutation == "wrong_actor":
                async def wrong_reader():
                    with pytest.raises(FrameError):
                        await receiver.run()
                await asyncio.create_task(wrong_reader())
                assert not receiver._started and not receiver._failed and not channel._reading
            if mutation == "cancel_wait":
                from hmp_plugin import presentation_readiness as readiness
                wait = readiness.SelectorReadiness.wait
                async def observe_wait(waiter, end_ns, **options):
                    if waiter._origin_scope.task is writer._scope_snapshot.allocation.task:
                        read_wait.set()
                    return await wait(waiter, end_ns, **options)
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
            if mutation == "dispatch_ready" or mutation.startswith("dispatch_go_"):
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
                if mutation.startswith("dispatch_go_"):
                    from hmp_plugin import presentation_credential_go as go_module
                    from hmp_plugin.presentation_broker_service import SocketChannel
                    from hmp_plugin.presentation_credential_go import NativeGoCommitment

                    async def signed_go_only(owned_channel, owned_remote):
                        assert owned_channel is channel and owned_remote is remote
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
                        finally:
                            go_record = authority._record(operation)
                            held["go_native_phase"] = go_record.owner.inspect_remote(
                                go_record.handle)
                            assert remote._go_admission_used is True
                            assert channel._go_write_intent is None
                            assert channel._go_write_fact is None
                            with pytest.raises(FrameError):
                                commitment.prepare()
                        raise FrameError("SYNTHETIC_GO_SIGNING_ONLY_NO_WIRE")

                    monkeypatch.setattr(SocketChannel, "send_go", signed_go_only)
                    with pytest.raises((FrameError, AuthorityRefusalError)):
                        await remote.go()
                    commitment = held["go_commitment"]
                    go_success = mutation in ("dispatch_go_sign", "dispatch_go_wrong_actor")
                    pre_attempt_refusal = mutation == "dispatch_go_admission"
                    assert commitment._attempted is not pre_attempt_refusal
                    assert commitment._complete is go_success
                    assert commitment._failed is (not go_success and not pre_attempt_refusal)
                    assert held["go_native_phase"] is (
                        RemotePhase.UNKNOWN if mutation == "dispatch_go_deadline"
                        else RemotePhase.GO_INTENT)
                    assert held.get("go_foreign_callbacks", []) == []
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
                RemoteCleanupOwner.request(cleanup)
                # Actual owned cleanup may retain UNKNOWN: signed cleanup relay
                # is not integrated by this READY-only dispatch slice.
                async with asyncio.timeout(2):
                    result = await asyncio.shield(cleanup._allocations_snapshot[0].task)
                assert type(result) is bool
                assert cleanup._allocations_snapshot[1].task.done()
                assert result is True or cleanup._unknown is True
            else:
                with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
                    await remote.begin_ready()
                if mutation == "dispatch_cancel":
                    assert held["cancel_before_ready"] is True
                assert remote._cleanup_owner_snapshot._ready_fact is None
                assert remote._cleanup_owner_snapshot._credential_work_snapshot._exchange_failed
            async with asyncio.timeout(2):
                await peer_task
            if mutation.startswith("dispatch_go_"):
                assert remote._go_admission_used is True
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
        io_unknown = not read_complete and mutation != "admission_refusal"
        assert receiver._complete is read_complete
        assert receiver._failed is (not read_complete or mutation in (
            "current_key", "native_observe_key"))
        assert receiver._io_unknown is io_unknown
        assert channel._reading is io_unknown
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
        else:
            assert receiver._completion is None
            assert not receiver._scope_origin.buffer and receiver._pending is None
            error = held["read_error"]
            error_type = asyncio.CancelledError if mutation == "cancel_wait" else FrameError
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
