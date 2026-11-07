"""Actual original-work RESULT envelope reads; synthetic pinned peer, no image body."""
import asyncio
import hashlib
import json

import pytest

from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_codec import encode_frame, header_size
from hmp_plugin.presentation_credential_begin_write import NativeBeginWriter
from hmp_plugin.presentation_credential_codec import decode_record, encode_record, signing_bytes
from hmp_plugin.presentation_credential_result_read import NativeResultEnvelopeReceiver
from hmp_plugin.presentation_jobs import OUTPUT_LIMIT, FrameError, RemotePhase
from hmp_plugin.presentation_remote import RemoteOperationOwner
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

from .test_presentation_broker_service import local as local
from .test_presentation_credential_native_binding import begin_gateway as begin_gateway
from .test_presentation_credential_native_binding import handshake
from .test_presentation_remote import prepare
from .test_presentation_supervisor import context as context


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "valid", "fragmented", "signature", "scope", "sequence", "oversize_auth",
    "oversize_body", "wrong_header", "unknown_recv", "count_drift", "tail_key",
    "wrong_actor", "cancel_wait", "cancel_partial", "initial", "deadline",
    "tail_policy", "expected_row", "cancel_generic", "cancel_foreign_end",
    "cancel_foreign_future", "premature",
    "cancel_capture_wait", "cancel_capture_partial",
    "wake_wait", "wake_partial", "wake_copy", "wake_generic", "wake_count",
    "wake_release", "wake_subclass", "wake_capture", "wake_scope", "wake_tail",
    "wake_reserve", "wake_reserve_no_write", "cancel_capture_reserve",
    "wake_reserve_tail_alloc", "wake_reserve_tail_refs", "wake_reserve_tail_barriers",
    "wake_reserve_notice", "wake_reserve_notice_wrong_actor", "wake_reserve_notice_ambiguous",
    "wake_reserve_notice_futurebad", "wake_reserve_notice_init_before",
    "wake_reserve_notice_init_after", "wake_reserve_notice_swapinit",
    "wake_reserve_notice_swapcurrent", "wake_reserve_notice_roleclock",
    "wake_reserve_notice_generationclock", "wake_reserve_notice_bootclock",
    "wake_reserve_notice_processclock", "wake_reserve_notice_fileclock",
    "wake_reserve_notice_reservationclock",
    "wake_reserve_notice_cleanup", "wake_reserve_notice_cleanup_copybad",
    "wake_reserve_notice_cleanup_futurebad", "wake_reserve_notice_cleanup_rolebad",
    "wake_reserve_wait_dispatchbad", "wake_reserve_wait_futurebad",
])
async def test_original_result_envelope(context, begin_gateway, tmp_path, monkeypatch, mutation):
    from hmp_plugin import presentation_credential_result_read as module
    from hmp_plugin.presentation_readiness import SelectorReadiness

    prepared = await prepare(context, begin_gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    handshake_owner, keys, _ = await handshake(prepared, tmp_path)
    remote = authority.bind_remote(operation, channel, handshake_owner._operation_binding(), packet)
    held = {}
    begin = asyncio.Event()
    go = asyncio.Event()
    waiting = asyncio.Event()
    retain = NativeBeginWriter.retain
    if "reserve" in mutation:
        from hmp_plugin.presentation_cleanup_reader import CleanupReadGate
        request = CleanupReadGate.request

        def observed_request(gate):
            result = request(gate)
            if gate._capture_kind == "signed":
                assert result is False  # no suppression/read/CANCEL permission
                assert not gate._capture_cause.done()
                held["reservation_precompletion"] = True
                held["reservation"] = gate._signed_reservation_origin
            return result

        monkeypatch.setattr(CleanupReadGate, "request", observed_request)
        if "_notice_init_" in mutation or mutation.endswith("_swapinit"):
            from hmp_plugin import presentation_credential_cleanup_notice as notice_module
            initialize = notice_module._initialize_future

            def failed_notice_init(future, loop):
                gate = remote._cleanup_owner_snapshot._read_gate_snapshot
                owner = gate._signed_notice_origin
                assert owner is not None and owner._future_origin is future
                assert gate._signed_notice_allocation_origin == (gate, owner)
                if mutation.endswith("_swapinit"):
                    initialize(future, loop)
                    replacement = asyncio.get_running_loop().create_future()
                    owner._future = owner._future_origin = replacement
                    held["notice_original_future"] = future
                    held["notice_swapped_future"] = replacement
                    return
                if mutation.endswith("_after"):
                    initialize(future, loop)
                held["notice_init_retained_before_effect"] = True
                raise OSError("synthetic notice initialization uncertainty")

            monkeypatch.setattr(notice_module, "_initialize_future", failed_notice_init)
        if "_reserve_tail_" in mutation:
            from hmp_plugin import presentation_credential_cleanup_reservation as reservation_module
            current = reservation_module._current
            held["reservation_current_calls"] = 0

            def foreign_after_budget(reservation, gate):
                held["reservation_current_calls"] += 1
                if held["reservation_current_calls"] != 2:
                    return current(reservation, gate)
                cleanup = reservation.capture.cleanup
                names = {
                    "alloc": ("_allocations", "_allocations_snapshot"),
                    "refs": ("_refs", "_refs_snapshot"),
                    "barriers": ("_barriers", "_barriers_snapshot"),
                }[mutation.rsplit("_", 1)[1]]
                saved = tuple(getattr(cleanup, name) for name in names)
                calls = []

                class ForeignStructure:
                    def __getitem__(self, key):
                        calls.append("index")
                        raise AssertionError("foreign indexing")

                    def __getattr__(self, key):
                        calls.append("getter")
                        raise AssertionError("foreign getter")

                foreign = ForeignStructure()
                for name in names:
                    setattr(cleanup, name, foreign)
                try:
                    with pytest.raises((FrameError, AuthorityRefusalError)):
                        current(reservation, gate)
                    assert calls == []
                    held["reservation_foreign_refused"] = True
                finally:
                    # Fixture structural aliases only, after refusal. Never mint/retry a
                    # reservation or restore intent, publication, grants, role or IO flags.
                    for name, value in zip(names, saved, strict=True):
                        setattr(cleanup, name, value)
                raise FrameError("synthetic refused preflight; no successful reservation")

            monkeypatch.setattr(reservation_module, "_current", foreign_after_budget)

    def observed_begin(cls, producer):
        writer = retain(producer)
        held["begin"] = writer
        begin.set()
        return writer

    monkeypatch.setattr(NativeBeginWriter, "retain", classmethod(observed_begin))

    async def peer_result():
        await begin.wait()
        b = held["begin"]._scope_snapshot
        loop = asyncio.get_running_loop()
        async with asyncio.timeout_at(b.intent.end_ns / 1e9):
            actual = bytearray()
            while len(actual) < len(b.wire):
                part = await loop.sock_recv(peer, len(b.wire) - len(actual))
                assert part
                actual.extend(part)
            assert actual == b.wire
            value = json.loads(decode_record(b.raw).canonical_json)
            ready = encode_frame(b.intent.binding, "READY", 0, b"", version=2)
            value.update(phase="READY", role="broker", direction="b2g", sequence=0,
                key_id=hashlib.sha256(keys["broker"]._selection.own_public).hexdigest(),
                peer_key_id=hashlib.sha256(keys["broker"]._selection.peer_public).hexdigest(),
                frame_sha256=hashlib.sha256(ready).hexdigest(), frame_length=len(ready))
            raw = encode_record(value, keys["broker"]._private_key.sign(signing_bytes(value)))
            await loop.sock_sendall(peer, raw + ready)
            await go.wait()
            writer = held["go"]
            wire = writer._scope_snapshot.wire
            actual.clear()
            while len(actual) < len(wire):
                part = await loop.sock_recv(peer, len(wire) - len(actual))
                assert part
                actual.extend(part)
            assert actual == wire
            if mutation.startswith("wake"):
                if mutation == "wake_partial":
                    await loop.sock_sendall(peer, b"HBA1")
                await waiting.wait()
                return
            if mutation.startswith("cancel"):
                if mutation.endswith("partial"):
                    await loop.sock_sendall(peer, b"HBA1")
                await waiting.wait()
                if mutation.startswith("cancel_capture"):
                    from hmp_plugin.presentation_credential_cleanup_capture import (
                        inspect_signed_cleanup,
                    )
                    cleanup = b.remote._cleanup_owner_snapshot
                    RemoteCleanupOwner.request(cleanup)
                    gate = cleanup._read_gate_snapshot
                    captured = gate._signed_capture_origin
                    assert captured is not None
                    assert inspect_signed_cleanup(captured, gate, cleanup) is captured
                    assert captured.receiver is held["reader"] and captured.body is None
                    assert captured.envelope.active and not captured.envelope.complete
                    assert captured.envelope.completion is None
                    expected = b"HBA1" if mutation.endswith("partial") else b""
                    assert captured.envelope.values == expected
                    assert captured.envelope.consumed == len(expected)
                    assert captured.envelope.waiter.scope.task is b.allocation.task
                    assert not captured.envelope.waiter.future_done
                    if mutation == "cancel_capture_reserve":
                        assert captured.write is cleanup._write_fact_snapshot
                    else:
                        assert captured.write is None
                    assert cleanup._cancel_attempted and not cleanup._work_joined
                    assert not gate._requested and gate._fact_origin is None
                    held["signed_envelope_cleanup_capture_checked"] = True
                else:
                    assert b.allocation.task.cancel()
                return
            frame = encode_frame(b.intent.binding, "RESULT", 1, b"abcd", version=2)
            header_end = 8 + header_size(frame[:8])
            header = frame[:header_end]
            if mutation == "oversize_body":
                row = json.loads(header[8:])
                row["body_length"] = OUTPUT_LIMIT + 1
                body = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii")
                header = header[:4] + len(body).to_bytes(4, "big") + body
            if mutation == "wrong_header":
                header = encode_frame(b.intent.binding, "GO", 1, b"", version=2)
            value.update(phase="RESULT", sequence=1,
                frame_sha256=hashlib.sha256(header + b"abcd").hexdigest(),
                frame_length=len(header) + 4)
            if mutation == "scope":
                value["scope_sha256"] = "f" * 64
            if mutation == "sequence":
                value["sequence"] = 2
            raw = encode_record(value, keys["broker"]._private_key.sign(signing_bytes(value)))
            if mutation == "signature":
                raw = raw[:-1] + bytes([raw[-1] ^ 1])
            envelope = raw + header
            if mutation == "oversize_auth":
                envelope = b"HBA1" + (1977).to_bytes(4, "big")
            held["envelope"] = envelope
            if mutation == "fragmented":
                for part in (envelope[:4], envelope[4:8], envelope[8:len(raw)], header):
                    await loop.sock_sendall(peer, part)
                    await asyncio.sleep(0)
            else:
                await loop.sock_sendall(peer, envelope)
            # Deliberately do not send image body: envelope completion is not result validation.

    if mutation == "premature":
        from hmp_plugin.presentation_credential_work import NativePhaseWorkOwner
        exchange_go = NativePhaseWorkOwner.exchange_go

        async def premature_read(producer):
            writer = await exchange_go(producer)
            assert producer._refs[1]._job_origin_snapshot.remote_phase is RemotePhase.GO_INTENT
            with pytest.raises(FrameError):
                NativeResultEnvelopeReceiver.retain(writer)
            assert writer._result_receiver_snapshot is None
            assert channel._credential_result_receiver_snapshot is None
            assert producer._refs[1]._failed is False
            held["premature_refused"] = True
            return writer

        monkeypatch.setattr(NativePhaseWorkOwner, "exchange_go", premature_read)

    original_go = RemoteOperationOwner._go_exchange

    async def original_work_result(owned):
        result = await original_go(owned)
        producer = owned._cleanup_owner_snapshot._credential_work_snapshot
        writer = producer._go_commitment_snapshot._writer_snapshot
        held["go"] = writer
        if "reserve" in mutation and mutation != "wake_reserve_no_write":
            from hmp_plugin.presentation_broker_service import SocketChannel
            SocketChannel._go_written(channel, owned)
            assert RemoteCleanupOwner._publish_write_quiescence(owned._cleanup_owner_snapshot)
        if mutation == "wrong_actor":
            async def wrong_factory():
                with pytest.raises(FrameError):
                    NativeResultEnvelopeReceiver.retain(writer)
            await asyncio.create_task(wrong_factory())
            assert writer._result_receiver is None
        if mutation == "initial":
            from hmp_plugin.presentation_credential_go_write import NativeGoWriter
            current_sent = NativeGoWriter.current_sent

            def refused_initial(owned):
                result = current_sent(owned)
                if owned is writer:
                    assert owned._result_receiver_snapshot is not None
                    raise FrameError("synthetic initialized-envelope refusal")
                return result

            monkeypatch.setattr(NativeGoWriter, "current_sent", refused_initial)
            with pytest.raises(FrameError):
                NativeResultEnvelopeReceiver.retain(writer)
            partial = writer._result_receiver_snapshot
            held["reader"] = partial
            assert partial._failed and not partial._started and partial._consumed == 0
            with pytest.raises(FrameError):
                NativeResultEnvelopeReceiver.retain(writer)
            assert writer._result_receiver_snapshot is partial
            go.set()
            raise FrameError("synthetic stop after retained admission refusal")
        reader = NativeResultEnvelopeReceiver.retain(writer)
        held["reader"] = reader
        go.set()
        if mutation == "wrong_actor":
            async def wrong():
                with pytest.raises(FrameError):
                    await reader.run()
            await asyncio.create_task(wrong())
            assert not reader._started and not reader._failed
        if mutation in ("unknown_recv", "count_drift"):
            recv = module._RECV
            held["native_received"] = 0

            def changed_recv(sock, count):
                part = recv(sock, count)
                held["native_received"] += len(part)
                if mutation == "unknown_recv":
                    raise OSError("synthetic post-recv uncertainty")
                reader._consumed += 1
                return part

            monkeypatch.setattr(module, "_RECV", changed_recv)
        if mutation in ("tail_key", "tail_policy", "expected_row"):
            timeout = module._TIMEOUT
            held["recv_calls"] = 0
            recv = module._RECV

            def counted_recv(sock, count):
                held["recv_calls"] += 1
                return recv(sock, count)

            def retired_tail(sock):
                value = timeout(sock)
                if reader._started:
                    if mutation == "tail_key":
                        keys["gateway"].retire()
                    elif mutation == "tail_policy":
                        authority._record(operation).policy_work._invalid = True
                    else:
                        held["foreign_calls"] = []

                        class ForeignExpected:
                            def __iter__(self):
                                held["foreign_calls"].append("iter")
                                raise AssertionError("foreign expected iteration")

                        scope = reader._scope_origin
                        changed = scope._replace(expected=(ForeignExpected(), *scope.expected[1:]))
                        reader._scope = reader._scope_origin = changed
                return value

            monkeypatch.setattr(module, "_TIMEOUT", retired_tail)
            monkeypatch.setattr(module, "_RECV", counted_recv)
        if mutation == "deadline":
            sample = module.NativeClockOwner.sample

            def expired_sample(clock):
                now = sample(clock)
                return reader._base_origin.intent.end_ns if reader._started else now

            monkeypatch.setattr(module.NativeClockOwner, "sample", expired_sample)
        if "_reserve_wait_" in mutation:
            remaining = RemoteCleanupOwner._remaining
            held["root_wait_clock_calls"] = 0

            def root_wait_clock(owner):
                value = remaining(owner)
                if (owner is owned._cleanup_owner_snapshot
                        and asyncio.current_task() is owner._allocations_snapshot[0].task
                        and owner._read_gate_snapshot._signed_notice_origin is not None):
                    held["root_wait_clock_calls"] += 1
                    if held["root_wait_clock_calls"] == 2:
                        notice = owner._read_gate_snapshot._signed_notice_origin
                        actual = notice._future_allocation_origin[1]
                        held["root_wait_original_future"] = actual
                        if mutation.endswith("_dispatchbad"):
                            def foreign_callback(*args, **kwargs):
                                held["root_wait_foreign_callback"] = True
                                raise AssertionError("foreign callback invoked")
                            actual.add_done_callback = foreign_callback
                        else:
                            replacement = asyncio.get_running_loop().create_future()
                            notice._future = notice._future_origin = replacement
                            held["root_wait_replacement_future"] = replacement
                        held["root_wait_clock_changed"] = True
                return value

            monkeypatch.setattr(RemoteCleanupOwner, "_remaining", root_wait_clock)
        if mutation.startswith("wake"):
            native_wait = asyncio.wait

            async def request_at_registered_wait(futures, **options):
                waiter = reader._waiter_origin
                if (asyncio.current_task() is reader._base_origin.allocation.task
                        and waiter is not None and waiter._attempted
                        and waiter._handle_snapshot is not None
                        and reader._base_origin.refs[0]._barriers_snapshot.cause in futures
                        and not held.get("actual_cause_requested")
                        and (mutation != "wake_partial" or reader._consumed == 4)):
                    held["actual_cause_requested"] = True
                    RemoteCleanupOwner.request(reader._base_origin.refs[0])
                    waiting.set()
                return await native_wait(futures, **options)

            monkeypatch.setattr(asyncio, "wait", request_at_registered_wait)
            if mutation in ("wake_copy", "wake_generic", "wake_subclass"):
                actual_wait = SelectorReadiness.wait

                async def altered_wake(waiter, end, **options):
                    try:
                        return await actual_wait(waiter, end, **options)
                    except module._ReadinessWakeRetiredError as error:
                        if mutation == "wake_generic":
                            raise module.ReadinessWakeError from None
                        if mutation == "wake_subclass":
                            class ForeignWake(module._ReadinessWakeRetiredError):
                                @property
                                def retirement(self):
                                    held["foreign_wake_getter"] = True
                                    return None

                            raise ForeignWake.__new__(ForeignWake) from None
                        raise module._ReadinessWakeRetiredError(
                            error.retirement._replace()) from None

                monkeypatch.setattr(SelectorReadiness, "wait", altered_wake)
            if mutation in ("wake_count", "wake_capture", "wake_scope"):
                actual_stop = NativeResultEnvelopeReceiver._wake_stopped

                def drifted_stop(owner, receipt, **options):
                    if mutation == "wake_count":
                        owner._consumed = owner._consumed_origin = receipt.hold.consumed + 1
                    elif mutation == "wake_capture":
                        gate = owner._base_origin.refs[0]._read_gate_snapshot
                        copied = receipt.capture._replace()
                        gate._signed_capture = gate._signed_capture_origin = copied
                        receipt = receipt._replace(capture=copied)
                    else:
                        waiter = receipt.hold.waiter
                        copied = receipt.hold.native_scope._replace()
                        waiter._scope = waiter._scope_snapshot = waiter._origin_scope = copied
                    return actual_stop(owner, receipt, **options)

                monkeypatch.setattr(NativeResultEnvelopeReceiver, "_wake_stopped", drifted_stop)
            if mutation == "wake_tail":
                original_woken = SelectorReadiness._woken_local

                def tail_drift(waiter, fact):
                    value = original_woken(waiter, fact)
                    reader._target = reader._target_origin = reader._target_origin + 1
                    return value

                monkeypatch.setattr(SelectorReadiness, "_woken_local", tail_drift)
        if mutation.startswith("cancel"):
            wait = SelectorReadiness.wait

            async def observed_wait(waiter, end, **options):
                task = writer._scope_snapshot.signed_scope.producer._refs[6].task
                if (waiter._origin_scope.task is task
                        and (not mutation.endswith("partial") or reader._consumed == 4)):
                    waiting.set()
                try:
                    return await wait(waiter, end, **options)
                except module._ReadinessCancelledError as error:
                    if mutation == "cancel_generic":
                        raise asyncio.CancelledError from None
                    if mutation == "cancel_foreign_end":
                        raise module._ReadinessCancelledError(
                            error.retirement._replace(end=end + 1)) from None
                    raise

            monkeypatch.setattr(SelectorReadiness, "wait", observed_wait)
            if mutation == "cancel_foreign_future":
                cancelled_current = NativeResultEnvelopeReceiver._cancelled_wait_current

                def substituted_future(owner, receipt, *, released=False):
                    assert not released and receipt.hold.future is receipt.readiness.future
                    replacement = asyncio.get_running_loop().create_future()
                    replacement.cancel()
                    waiter = receipt.readiness.owner
                    waiter._future = waiter._future_origin = waiter._future_snapshot = replacement
                    substituted = receipt._replace(
                        readiness=receipt.readiness._replace(future=replacement))
                    held["post_wait_future_substitution"] = True
                    return cancelled_current(owner, substituted, released=released)

                monkeypatch.setattr(NativeResultEnvelopeReceiver, "_cancelled_wait_current",
                                    substituted_future)
        if ("_reserve_notice" in mutation and "_init_" not in mutation
                and not mutation.endswith("_swapinit")):
            from hmp_plugin.presentation_credential_cleanup_notice import SignedReadNotice
            try:
                await reader.run()
            except FrameError:
                notice = owned._cleanup_owner_snapshot._read_gate_snapshot._signed_notice_origin
                assert notice is not None and notice._initialized and not notice._attempted
                if mutation.endswith("_wrong_actor"):
                    async def wrong_notice_actor():
                        with pytest.raises(FrameError):
                            notice.publish()
                    await asyncio.create_task(wrong_notice_actor())
                    assert not notice._attempted and not notice._future_origin.done()
                if mutation.endswith("_ambiguous"):
                    deliver = SignedReadNotice._deliver

                    def delivered_then_failed(future, fact):
                        deliver(future, fact)
                        held["notice_delivered_then_failed"] = True
                        raise OSError("synthetic lost native delivery acknowledgement")

                    monkeypatch.setattr(SignedReadNotice, "_deliver",
                                        staticmethod(delivered_then_failed))
                if mutation == "wake_reserve_notice_futurebad":
                    def foreign_future_method(*args):
                        held["foreign_notice_future_called"] = True
                    notice._future_origin.add_done_callback = foreign_future_method
                clock_fault = mutation.endswith((
                    "_roleclock", "_generationclock", "_bootclock", "_processclock", "_fileclock",
                    "_reservationclock"))
                if mutation.endswith("_swapcurrent") or clock_fault:
                    remaining = RemoteCleanupOwner._remaining
                    held["notice_remaining_calls"] = 0

                    def last_clock_change(cleanup):
                        value = remaining(cleanup)
                        if (cleanup is owned._cleanup_owner_snapshot and notice._attempted):
                            held["notice_remaining_calls"] += 1
                            if held["notice_remaining_calls"] == 2:
                                if mutation.endswith("_swapcurrent"):
                                    held["notice_original_future"] = notice._future_origin
                                    replacement = asyncio.get_running_loop().create_future()
                                    notice._future = notice._future_origin = replacement
                                    held["notice_swapped_future"] = replacement
                                elif mutation.endswith("_reservationclock"):
                                    class ForeignReservation:
                                        def __getattr__(self, name):
                                            held["foreign_notice_reservation_accessed"] = True
                                            raise AssertionError("foreign reservation getter")
                                    notice._reservation = ForeignReservation()
                                elif mutation.endswith("_roleclock"):
                                    keys["gateway"].retire()
                                elif mutation.endswith("_generationclock"):
                                    selection = keys["gateway"]._selection
                                    object.__setattr__(selection, "generation",
                                                       selection.generation + "-changed")
                                elif mutation.endswith("_bootclock"):
                                    keys["gateway"]._boot += "-changed"
                                elif mutation.endswith("_processclock"):
                                    old_pid, old_uid = keys["gateway"]._process
                                    keys["gateway"]._process = (old_pid + 1, old_uid)
                                else:
                                    assert keys["gateway"]._records
                                    keys["gateway"]._records[0].unknown = True
                                held["notice_clock_changed"] = True
                        return value

                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining", last_clock_change)
                if (mutation.endswith(("_ambiguous", "_swapcurrent")) or clock_fault
                        or mutation == "wake_reserve_notice_futurebad"):
                    with pytest.raises(FrameError):
                        notice.publish()
                    assert notice._failed and notice._unknown and notice._attempted
                else:
                    assert notice.publish() is True
                    assert notice._published and not notice._failed
                    assert notice._future_origin.result() is notice._fact_origin
                    held["notice_published"] = True
                if "_notice_cleanup" in mutation:
                    with pytest.raises(FrameError):
                        notice.current_stop_for_cleanup()  # sender is not the cleanup actor
                    assert not notice._failed and not notice._unknown
                    cleanup_checked = asyncio.Event()
                    remaining = RemoteCleanupOwner._remaining
                    checking = False
                    current_for_cleanup = SignedReadNotice.current_stop_for_cleanup
                    held["cleanup_notice_validated_calls"] = 0

                    def counted_cleanup_query(owner):
                        value = current_for_cleanup(owner)
                        held["cleanup_notice_validated_calls"] += 1
                        return value

                    monkeypatch.setattr(SignedReadNotice, "current_stop_for_cleanup",
                                        counted_cleanup_query)

                    def actual_cleanup_probe(cleanup):
                        nonlocal checking
                        value = remaining(cleanup)
                        if (checking and mutation.endswith("bad")
                                and not held.get("cleanup_notice_tail_changed")):
                            held["cleanup_notice_tail_changed"] = True
                            if mutation.endswith("_copybad"):
                                copied = notice._fact_origin._replace()
                                notice._fact = notice._fact_origin = copied
                            elif mutation.endswith("_futurebad"):
                                held["cleanup_notice_original_future"] = notice._future_origin
                                replacement = asyncio.get_running_loop().create_future()
                                notice._future = notice._future_origin = replacement
                            else:
                                keys["gateway"].retire()
                        if (mutation == "wake_reserve_notice_cleanup"
                                and cleanup is owned._cleanup_owner_snapshot
                                and asyncio.current_task() is cleanup._allocations_snapshot[0].task
                                and cleanup._work_joined and held.get("cleanup_notice_checked")):
                            with pytest.raises(FrameError):
                                notice.current_stop_for_cleanup()
                            assert not notice._failed and not notice._unknown
                            held["cleanup_notice_completed_work_refused"] = True
                        if (cleanup is owned._cleanup_owner_snapshot
                                and asyncio.current_task() is cleanup._allocations_snapshot[0].task
                                and notice._published and not checking
                                and not held.get("cleanup_notice_checked")):
                            checking = True
                            try:
                                if mutation.endswith("bad"):
                                    with pytest.raises(FrameError):
                                        notice.current_stop_for_cleanup()
                                    assert notice._failed and notice._unknown
                                    assert cleanup._unknown
                                else:
                                    assert notice.current_stop_for_cleanup() is notice._fact_origin
                                    assert notice.current_stop_for_cleanup() is notice._fact_origin
                                    assert not notice._failed and not notice._unknown
                                    assert not cleanup._work_joined
                                    assert not cleanup._allocations_snapshot[1].task.done()
                                    with pytest.raises(AuthorityRefusalError):
                                        RemoteCleanupOwner._cancel_actor(cleanup, channel)
                                    assert not cleanup._cancel_write_attempted
                                    assert not cleanup._read_gate_snapshot._requested
                                    assert cleanup._read_gate_snapshot._fact_origin is None
                                held["cleanup_notice_checked"] = True
                                cleanup_checked.set()
                            finally:
                                checking = False
                        return value

                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining", actual_cleanup_probe)
                    async with asyncio.timeout_at(reader._base_origin.intent.end_ns / 1e9):
                        # Same original work Task; no replacement reader.
                        await cleanup_checked.wait()
                with pytest.raises(FrameError):
                    notice.publish()  # no second attempt, even after ambiguous delivery
                held["notice_no_retry"] = True
                raise
        await reader.run()
        fact = reader.current_envelope()
        assert fact.frame == held["envelope"][len(fact.raw):]
        assert fact.header.kind == "RESULT" and fact.header.body_length == 4
        assert fact.count == len(held["envelope"]) and reader._complete
        job = owned._job_origin_snapshot
        assert job.remote_phase is RemotePhase.GO_SENT and job.result is None
        assert not job.output_buffer._buffer and not job.output_buffer._done
        held["checked"] = True
        with pytest.raises(FrameError):
            await reader.run()
        with pytest.raises(FrameError):
            NativeResultEnvelopeReceiver.retain(writer)
        assert reader._complete and not reader._failed
        return result

    monkeypatch.setattr(RemoteOperationOwner, "_go_exchange", original_work_result)
    peer_task = asyncio.create_task(peer_result())
    try:
        assert await remote.begin_ready() is True
        success = mutation in ("valid", "fragmented", "wrong_actor", "premature")
        if success:
            assert await remote.go() is True
            assert held["checked"]
            if mutation == "premature":
                assert held["premature_refused"]
        else:
            with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
                await remote.go()
            reader = held["reader"]
            if "_notice_cleanup" in mutation:
                # The caller may refuse as soon as the actual cause completes,
                # before the original sender/cleanup rendezvous has run.
                async with asyncio.timeout_at(reader._base_origin.intent.end_ns / 1e9):
                    outcome = (await asyncio.gather(reader._base_origin.allocation.task,
                                                    return_exceptions=True))[0]
                    cleanup_task = remote._cleanup_owner_snapshot._allocations_snapshot[0].task
                    await asyncio.shield(cleanup_task)
                    assert cleanup_task.done()
                if not held.get("notice_no_retry") and isinstance(outcome, BaseException):
                    raise outcome  # preserve actual original actor/fixture error
            assert reader._failed and not reader._complete
            assert reader._completion_origin is None
            if mutation in ("tail_key", "tail_policy", "expected_row"):
                assert held["recv_calls"] == 0
            if mutation == "expected_row":
                assert not held["foreign_calls"]
            if mutation == "count_drift":
                assert reader._consumed == held["native_received"]
                assert reader._io_unknown
            if mutation == "unknown_recv":
                assert reader._consumed == 0 and held["native_received"] > 0
                assert reader._io_unknown
            if mutation in ("cancel_wait", "cancel_partial",
                            "cancel_capture_wait", "cancel_capture_partial",
                            "cancel_capture_reserve"):
                assert reader._cancel_release_origin is not None
                assert not reader._active and not reader._io_unknown
                assert reader._consumed == (4 if mutation.endswith("partial") else 0)
            if mutation in ("cancel_generic", "cancel_foreign_end", "cancel_foreign_future"):
                assert reader._cancel_release_origin is None and reader._io_unknown
            if mutation == "cancel_foreign_future":
                assert held["post_wait_future_substitution"]
        if mutation.startswith("wake"):
            assert held["actual_cause_requested"]
            reader = held["reader"]
            task = reader._base_origin.allocation.task
            assert task.done() and not task.cancelled() and task.cancelling() == 0
            assert reader._cancel_release_origin is None
            if mutation in ("wake_wait", "wake_partial", "wake_release", "wake_reserve",
                            "wake_reserve_no_write", "wake_reserve_tail_alloc",
                            "wake_reserve_tail_refs", "wake_reserve_tail_barriers",
                            "wake_reserve_notice", "wake_reserve_notice_wrong_actor",
                            "wake_reserve_notice_ambiguous", "wake_reserve_notice_futurebad",
                            "wake_reserve_notice_init_before", "wake_reserve_notice_init_after",
                            "wake_reserve_notice_swapcurrent", "wake_reserve_notice_roleclock",
                            "wake_reserve_notice_generationclock", "wake_reserve_notice_bootclock",
                            "wake_reserve_notice_processclock", "wake_reserve_notice_fileclock",
                            "wake_reserve_notice_reservationclock",
                            "wake_reserve_notice_cleanup", "wake_reserve_notice_cleanup_copybad",
                            "wake_reserve_notice_cleanup_futurebad",
                            "wake_reserve_notice_cleanup_rolebad",
                            "wake_reserve_wait_dispatchbad"):
                assert reader._wake_release_origin is not None and not reader._io_unknown
                assert not reader._active and reader._failed and not reader._buffer_origin
                if mutation == "wake_release":
                    reader._target = reader._target_origin = reader._target_origin + 1
                    with pytest.raises(FrameError):
                        reader._released(channel)
                    assert reader._io_unknown
                elif mutation.endswith(("_swapcurrent", "_reservationclock",
                                        "_cleanup_copybad", "_cleanup_futurebad")):
                    with pytest.raises(FrameError):
                        reader._released(channel)
                    assert reader._io_unknown
                else:
                    reader._released(channel)
            else:
                assert reader._wake_release_origin is None and reader._io_unknown
            assert "foreign_wake_getter" not in held
        if "reserve" in mutation:
            from hmp_plugin.presentation_credential_cleanup_reservation import (
                inspect_signed_reservation,
            )
            gate = remote._cleanup_owner_snapshot._read_gate_snapshot
            assert held["reservation_precompletion"] and gate._signed_reservation_attempted
            assert not gate._requested and gate._fact_origin is None
            if mutation == "wake_reserve_no_write" or "_reserve_tail_" in mutation:
                assert held["reservation"] is None and gate._signed_reservation_failed
                if "_reserve_tail_" in mutation:
                    assert held["reservation_foreign_refused"]
            else:
                reservation = held["reservation"]
                assert reservation is not None and not gate._signed_reservation_failed
                assert inspect_signed_reservation(reservation, gate) is reservation
                assert reservation.wait.owner is held["reader"]._waiter_origin
                assert reservation.write is remote._cleanup_owner_snapshot._write_fact_snapshot
                assert reservation.cause is remote._cleanup_owner_snapshot._barriers_snapshot.cause
                assert gate._signed_reservation_allocation_origin == (gate, reservation)
                if mutation == "cancel_capture_reserve":
                    assert remote._cleanup_owner_snapshot._cancel_attempted
                    assert held["reader"]._base_origin.allocation.task.cancelled()
        if "_reserve_wait_" in mutation:
            cleanup = remote._cleanup_owner_snapshot
            async with asyncio.timeout_at(reader._base_origin.intent.end_ns / 1e9):
                await asyncio.shield(cleanup._allocations_snapshot[0].task)
            assert held["root_wait_clock_changed"] and cleanup._unknown
            assert "root_wait_foreign_callback" not in held
            notice = cleanup._read_gate_snapshot._signed_notice_origin
            assert notice._future_allocation_origin[1] is held["root_wait_original_future"]
            assert not notice._attempted and not notice._published
            assert not cleanup._cancel_write_attempted and not cleanup._work_joined
            if mutation.endswith("_futurebad"):
                assert notice._future_origin is held["root_wait_replacement_future"]
        if "_reserve_notice" in mutation:
            notice = remote._cleanup_owner_snapshot._read_gate_snapshot._signed_notice_origin
            assert notice is not None
            if mutation.endswith("_swapinit"):
                assert notice._failed and notice._unknown
                assert notice._future_allocation_origin[1] is held["notice_original_future"]
                assert notice._future_origin is held["notice_swapped_future"]
                assert notice._future_origin is not notice._future_allocation_origin[1]
            elif "_init_" in mutation:
                assert held["notice_init_retained_before_effect"]
                assert not notice._initialized and notice._failed and notice._unknown
                assert not notice._attempted and not notice._published
            else:
                assert held["notice_no_retry"] and notice._attempted
                assert "foreign_notice_future_called" not in held
                if "_notice_cleanup" in mutation:
                    assert held["cleanup_notice_checked"]
                    if mutation.endswith("bad"):
                        assert held["cleanup_notice_tail_changed"]
                        assert notice._failed and notice._unknown
                        if mutation.endswith("_futurebad"):
                            assert notice._future_allocation_origin[1] is (
                                held["cleanup_notice_original_future"])
                    else:
                        assert held["notice_published"]
                        # Two explicit probe queries plus the actual cleanup loop call.
                        assert held["cleanup_notice_validated_calls"] >= 3
                        assert held["cleanup_notice_completed_work_refused"]
                elif mutation.endswith("_ambiguous"):
                    assert held["notice_delivered_then_failed"]
                    assert notice._future_origin.done() and notice._failed and notice._unknown
                    assert notice._future_origin.result() is notice._fact_origin
                elif mutation.endswith((
                        "_futurebad", "_swapcurrent", "_roleclock", "_generationclock",
                        "_bootclock", "_processclock", "_fileclock", "_reservationclock")):
                    assert not notice._future_origin.done() and notice._failed
                    assert not notice._published
                    if mutation.endswith(("_swapcurrent", "_roleclock", "_generationclock",
                                          "_bootclock", "_processclock", "_fileclock",
                                          "_reservationclock")):
                        assert held["notice_clock_changed"]
                        assert "foreign_notice_reservation_accessed" not in held
                    if mutation.endswith("_swapcurrent"):
                        assert notice._future_allocation_origin[1] is held["notice_original_future"]
                        assert notice._future_origin is held["notice_swapped_future"]
                else:
                    assert held["notice_published"]
        await peer_task
        if mutation.startswith("cancel_capture"):
            assert held["signed_envelope_cleanup_capture_checked"]
        assert remote._result_owner is None
        assert remote._cleanup_owner_snapshot._result_token is None
    finally:
        cleanup = remote._cleanup_owner_snapshot
        if cleanup is not None:
            RemoteCleanupOwner.request(cleanup)
            async with asyncio.timeout(3):
                await asyncio.gather(*(a.task for a in cleanup._allocations_snapshot),
                                     return_exceptions=True)
        if not peer_task.done():
            peer_task.cancel()
        await asyncio.gather(peer_task, return_exceptions=True)
        for key in keys.values():
            key.retire()
