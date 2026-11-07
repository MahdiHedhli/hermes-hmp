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
    "wake_reserve_notice_reader_copybad", "wake_reserve_notice_reader_rolebad",
    "wake_reserve_notice_cursorinitbad", "wake_reserve_notice_cursorstatebad",
    "wake_reserve_notice_cursorpairbad",
    "wake_reserve_notice_cursoradmissionscopebad",
    "wake_reserve_notice_cursoradmissionfactbad",
    "wake_reserve_notice_cursoradmissionownerbad",
    "wake_reserve_notice_cursoradmissioninitbad",
    "wake_reserve_notice_cursoradmissionearlybad",
    "wake_reserve_notice_cursoradmissionreservationbad",
    "wake_reserve_notice_cursoradmissionendbad",
    "wake_reserve_notice_native",
    "wake_reserve_notice_native_keybad", "wake_reserve_notice_native_pendingbad",
    "wake_reserve_notice_native_lostack", "wake_reserve_notice_native_eof",
    "wake_reserve_notice_native_blocked", "wake_reserve_notice_native_receiptbad",
    "wake_reserve_notice_native_timeoutbad", "wake_reserve_notice_native_blockingbad",
    "wake_reserve_notice_native_fdbad",
    "wake_reserve_notice_native_probecounterbad",
    "wake_reserve_notice_native_probereadingbad",
    "wake_reserve_notice_native_probewritingbad",
    "wake_reserve_notice_native_posttimeoutbad", "wake_reserve_notice_native_postfdbad",
    "wake_reserve_notice_native_counterbad", "wake_reserve_notice_native_pendingpairbad",
    "wake_reserve_notice_native_scopebad", "wake_reserve_notice_native_workflagbad",
    "wake_reserve_notice_native_parseradvancebad",
    "wake_reserve_notice_native_consume",
    "wake_reserve_notice_native_consume_next",
    "wake_reserve_notice_native_consume_next_auth",
    "wake_reserve_notice_native_consume_next_auth_frame",
    "wake_reserve_notice_native_consume_next_auth_frame_terminal",
    "wake_reserve_notice_native_consume_next_auth_frame_bodyhash",
    "wake_reserve_notice_native_consume_next_auth_frame_authforeign",
    "wake_reserve_notice_native_consume_next_auth_frame_feedshadow",
    "wake_reserve_notice_native_consume_next_auth_frame_finishshadow",
    "wake_reserve_notice_native_consume_next_auth_frame_postledger",
    "wake_reserve_notice_native_consume_next_auth_frame_headcopy",
    "wake_reserve_notice_native_consume_next_auth_signature",
    "wake_reserve_notice_native_consume_next_auth_lost",
    "wake_reserve_notice_native_consume_next_auth_retired",
    "wake_reserve_notice_native_consume_next_auth_copy",
    "wake_reserve_notice_native_consume_next_auth_initial",
    "wake_reserve_notice_native_consume_next_auth_ledger",
    "wake_reserve_notice_native_consume_next_auth_counter",
    "wake_reserve_notice_native_consume_next_auth_values",
    "wake_reserve_notice_native_consume_next_auth_scope",
    "wake_reserve_notice_native_consume_next_short",
    "wake_reserve_notice_native_consume_next_blocked",
    "wake_reserve_notice_native_consume_next_lostack",
    "wake_reserve_notice_native_consume_next_alloc",
    "wake_reserve_notice_native_consume_next_foreign",
    "wake_reserve_notice_native_consume_initial",
    "wake_reserve_notice_native_consume_retired",
    "wake_reserve_notice_native_consume_partial",
    "wake_reserve_notice_native_consume_parsercopy",
    "wake_reserve_notice_native_consume_countdrift",
    "wake_reserve_notice_native_consume_progresscopy",
    "wake_reserve_notice_native_consume_fdmode",
])
async def test_original_result_envelope(context, begin_gateway, tmp_path, monkeypatch, mutation):
    from hmp_plugin import presentation_credential_result_read as module
    from hmp_plugin.presentation_readiness import SelectorReadiness

    next_case = "_native_consume_next" in mutation
    auth_case = "_consume_next_auth" in mutation
    frame_case = "_consume_next_auth_frame" in mutation
    frame_pure_failure = frame_case and mutation.endswith("_authforeign")
    frame_failure = frame_case and mutation.endswith((
        "_bodyhash", "_feedshadow", "_finishshadow", "_postledger", "_headcopy", "_authforeign"))
    auth_failure = auth_case and mutation.endswith((
        "_signature", "_lost", "_retired", "_copy", "_initial", "_ledger", "_counter",
        "_values", "_scope"))
    next_failure = next_case and mutation.endswith(("_blocked", "_lostack", "_alloc", "_foreign"))
    prepared = await prepare(context, begin_gateway)
    authority, operation, _, channel, peer, _, packet, _ = prepared
    handshake_owner, keys, _ = await handshake(prepared, tmp_path)
    remote = authority.bind_remote(operation, channel, handshake_owner._operation_binding(), packet)
    held = {}

    def exercise_native_frame(native, fact):
        # Called synchronously on the actual original work task, not a new actor.
        from hmp_plugin.presentation_credential_cleanup_read import NativeCleanupRead
        from hmp_plugin.presentation_credential_frame_discard import (
            CommittedFrameDiscard,
        )
        if frame_pure_failure:
            class ForeignFrameAuthScope:
                def __getattr__(self, name):
                    held["frame_auth_getter"] = True
                    raise AssertionError("foreign auth scope")
            native._auth_origin.scope = ForeignFrameAuthScope()
            with pytest.raises(FrameError):
                native.start_frame()
            assert native._frame_origin is None
            assert "frame_auth_getter" not in held
        else:
            scope = native.start_frame()
            stage = native._frame_origin
            assert scope.native is native
            assert scope.receipt is fact
            assert stage.scope.parser is stage.parser_origin
            assert stage.ledger_origin.received == (
                fact.total_received)
            for ordinal in (1, 2, 3):
                if mutation.endswith("_feedshadow"):
                    with pytest.raises(FrameError):
                        native.read_frame_next()
                    step = stage.step_origin
                    assert step.known and step.received == 8
                    assert step.count_cell[1] == 8
                    assert not step.fed and not step.complete
                    assert step.pending is None
                    assert not scope.parser._buffer_origin
                    assert "foreign_frame_feed" not in held
                    del scope.parser.feed
                    with pytest.raises(FrameError):
                        native.read_frame_next()
                    break
                frame_fact = native.read_frame_next()
                assert frame_fact.ordinal == ordinal
                assert frame_fact.scope is scope
                assert stage.step_origin.pending is None
                if scope.phase == "RESULT":
                    assert not scope.parser._terminal_origin
            if not mutation.endswith("_feedshadow"):
                assert stage.ledger_origin.seal.needed == 0
                if mutation.endswith("_finishshadow"):
                    frame_finish_fence = NativeCleanupRead._final_socket_fence

                    def shadow_finish_boundary(owner, s):
                        value = frame_finish_fence(owner, s)
                        if (stage.finish_attempted
                                and not held.get("finish_shadow")):
                            held["finish_shadow"] = True
                            def foreign_finish(*args):
                                held["foreign_frame_finish"] = True
                                raise AssertionError("foreign finish")
                            scope.parser.finish = foreign_finish
                        return value

                    monkeypatch.setattr(NativeCleanupRead,
                        "_final_socket_fence",
                        shadow_finish_boundary)
                if mutation.endswith(("_postledger", "_headcopy")):
                    finish = CommittedFrameDiscard.finish

                    def foreign_ledger_after_finish(parser):
                        result = finish(parser)
                        class ForeignFrameLedger:
                            def __getattr__(self, name):
                                held["frame_ledger_getter"] = True
                                raise AssertionError("foreign ledger")
                        if mutation.endswith("_postledger"):
                            stage.ledger_origin = ForeignFrameLedger()
                        else:
                            from dataclasses import replace
                            copied = replace(parser._header_origin)
                            parser._header = parser._header_origin = copied
                        return result

                    monkeypatch.setattr(CommittedFrameDiscard,
                        "finish", foreign_ledger_after_finish)
                if frame_failure:
                    with pytest.raises(FrameError):
                        native.finish_frame()
                    assert stage.failed and stage.done is None
                    assert native._unknown
                    assert "foreign_frame_finish" not in held
                    assert "frame_ledger_getter" not in held
                    if mutation.endswith("_finishshadow"):
                        assert not scope.parser._finish_attempted
                        del scope.parser.finish
                    assert stage.finish_cell[3] == 4
                    assert stage.finish_cell[4] == (
                        fact.total_received
                        + held["native_frame_length"])
                    with pytest.raises(FrameError):
                        native.finish_frame()
                else:
                    done = native.finish_frame()
                    assert done.scope is scope
                    assert done.data.phase == scope.phase
                    assert done.data.digest.frame_length == (
                        held["native_frame_length"])
                    assert done.total_received == (
                        fact.total_received
                        + held["native_frame_length"])
                    assert done.data.terminal == (
                        b"abcd" if scope.phase == "TERMINAL"
                        else None)
                    for action in (native.start_frame,
                                   native.read_frame_next,
                                   native.finish_frame):
                        with pytest.raises(FrameError):
                            action()
                    assert stage.complete and not native._failed
        held["native_frame_checked"] = True

    begin = asyncio.Event()
    go = asyncio.Event()
    waiting = asyncio.Event()
    native_ready, native_queued, native_observed = (
        asyncio.Event(), asyncio.Event(), asyncio.Event())
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
                if "_notice_native" in mutation:
                    await native_ready.wait()
                    phase = "TERMINAL" if mutation.endswith("_frame_terminal") else "RESULT"
                    frame = encode_frame(b.intent.binding, phase, 1, b"abcd", version=2)
                    value.update(phase=phase, sequence=1,
                                 frame_sha256=hashlib.sha256(frame).hexdigest(),
                                 frame_length=len(frame))
                    raw = encode_record(
                        value, keys["broker"]._private_key.sign(signing_bytes(value)))
                    held["native_expected"] = raw[:8]
                    if mutation.endswith("_eof"):
                        import socket
                        peer.shutdown(socket.SHUT_WR)
                    elif next_case:
                        if auth_case and mutation.endswith("_signature"):
                            raw = raw[:-1] + bytes([raw[-1] ^ 1])
                        held["next_record_length"] = len(raw)
                        held["native_frame_length"] = len(frame)
                        if frame_failure:
                            frame = frame[:-1] + bytes([frame[-1] ^ 1])
                        await loop.sock_sendall(peer, raw[:8] if mutation.endswith("_blocked")
                                               else raw + frame)
                    elif not mutation.endswith("_blocked"):
                        await loop.sock_sendall(peer, raw[:8] + b"not-consumed")
                    native_queued.set()
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
            from hmp_plugin.presentation_credential_cleanup_notice import (
                SignedCleanupReader,
                SignedReadNotice,
                SignedStoppedCursor,
            )
            try:
                await reader.run()
            except FrameError:
                notice = owned._cleanup_owner_snapshot._read_gate_snapshot._signed_notice_origin
                assert notice is not None and notice._initialized and not notice._attempted
                if "_notice_native" in mutation:
                    native_ready.set()
                    async with asyncio.timeout_at(reader._base_origin.intent.end_ns / 1e9):
                        await native_queued.wait()
                with pytest.raises(FrameError):
                    notice.current_stop_for_reader()  # publication is not yet delivered
                assert not notice._failed and not notice._unknown
                async def wrong_reader_actor():
                    with pytest.raises(FrameError):
                        notice.current_stop_for_reader()
                await asyncio.create_task(wrong_reader_actor())
                assert not notice._failed and not notice._unknown
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
                    if "_notice_reader_" in mutation:
                        remaining_for_reader = RemoteCleanupOwner._remaining

                        def reader_clock_drift(cleanup):
                            value = remaining_for_reader(cleanup)
                            if (asyncio.current_task() is reader._base_origin.allocation.task
                                    and not held.get("reader_notice_tail_changed")):
                                held["reader_notice_tail_changed"] = True
                                if mutation.endswith("_copybad"):
                                    copied = notice._fact_origin._replace()
                                    notice._fact = notice._fact_origin = copied
                                else:
                                    keys["gateway"].retire()
                            return value

                        monkeypatch.setattr(RemoteCleanupOwner, "_remaining", reader_clock_drift)
                        with pytest.raises(FrameError):
                            notice.current_stop_for_reader()
                        assert held["reader_notice_tail_changed"]
                        assert notice._failed and notice._unknown
                        assert owned._cleanup_owner_snapshot._unknown
                    else:
                        assert notice.current_stop_for_reader() is notice._fact_origin
                        assert notice.current_stop_for_reader() is notice._fact_origin
                        if mutation.endswith("_cursorinitbad"):
                            from hmp_plugin.presentation_credential_stream import (
                                SignedCleanupAuthPrefix,
                            )
                            initialize_cursor = SignedCleanupAuthPrefix.__init__

                            def initialized_cursor_then_failed(parser, *args, **options):
                                assert notice._cursor_allocation_origin[1] is notice._cursor_origin
                                assert notice._cursor_origin._parser_origin is parser
                                initialize_cursor(parser, *args, **options)
                                held["cursor_partial_retained"] = True
                                raise OSError("synthetic parser init acknowledgement lost")

                            monkeypatch.setattr(SignedCleanupAuthPrefix, "__init__",
                                                initialized_cursor_then_failed)
                            with pytest.raises(FrameError):
                                SignedStoppedCursor.retain(notice)
                            cursor = notice._cursor_origin
                            assert not cursor._initialized and cursor._failed
                            assert held["cursor_partial_retained"]
                        else:
                            cursor = SignedStoppedCursor.retain(notice)
                            assert cursor.current() is cursor
                            if mutation.endswith((
                                    "_cursoradmissioninitbad", "_cursoradmissionearlybad")):
                                admission_remaining = RemoteCleanupOwner._remaining

                                def partial_admission_clock(cleanup):
                                    value = admission_remaining(cleanup)
                                    partial = cursor._reader_origin
                                    early = mutation.endswith("_cursoradmissionearlybad")
                                    boundary = (partial is not None
                                                and (partial._scope_origin is None if early
                                                     else partial._fact_origin is not None))
                                    if (boundary
                                            and not partial._admitted
                                            and asyncio.current_task() is (
                                                reader._base_origin.allocation.task)
                                            and not held.get("partial_admission_revoked")):
                                        held["partial_admission_revoked"] = True
                                        held["partial_admission_fact"] = partial._fact_origin
                                        keys["gateway"].retire()
                                    return value

                                monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                    partial_admission_clock)
                                with pytest.raises(FrameError):
                                    SignedCleanupReader.retain(cursor)
                                idle_reader = cursor._reader_origin
                                assert held["partial_admission_revoked"]
                                assert idle_reader._failed and not idle_reader._admitted
                                if mutation.endswith("_cursoradmissionearlybad"):
                                    assert idle_reader._scope_origin is None
                                    assert idle_reader._fact_allocation_origin is None
                                else:
                                    assert idle_reader._fact_allocation_origin[1] is (
                                        held["partial_admission_fact"])
                            else:
                                idle_reader = SignedCleanupReader.retain(cursor)
                                idle_fact = idle_reader.current_idle()
                                assert idle_reader.current_idle() is idle_fact
                                assert idle_fact.scope[2] == cursor._parser.needed
                                assert idle_fact.scope[4] <= notice._reservation.end
                            with pytest.raises(FrameError):
                                SignedCleanupReader.retain(cursor)
                            if not mutation.endswith((
                                    "_cursoradmissioninitbad", "_cursoradmissionearlybad")):
                                assert not idle_reader._failed
                            if "_notice_native" in mutation:
                                from hmp_plugin.presentation_credential_cleanup_read import (
                                    NativeCleanupRead,
                                )
                                native = NativeCleanupRead.retain(idle_reader)
                                held["native_owner"] = native
                                fence = NativeCleanupRead._final_socket_fence
                                dispatch = NativeCleanupRead._dispatch_metadata

                                def observed_fence(owner, scope):
                                    try:
                                        return fence(owner, scope)
                                    except BaseException as error:
                                        held["native_pre_io_failure"] = error
                                        held["native_pre_io_failure_stage"] = "socket_fence"
                                        raise

                                def observed_dispatch(owner, scope):
                                    try:
                                        return dispatch(owner, scope)
                                    except BaseException as error:
                                        held["native_pre_io_failure"] = error
                                        held["native_pre_io_failure_stage"] = "dispatch_metadata"
                                        raise

                                monkeypatch.setattr(NativeCleanupRead, "_final_socket_fence",
                                                    observed_fence)
                                monkeypatch.setattr(NativeCleanupRead, "_dispatch_metadata",
                                                    observed_dispatch)
                                receive = NativeCleanupRead._receive
                                held["native_calls"] = 0

                                def observed_receive(sock, count):
                                    held["native_calls"] += 1
                                    assert sock is reader._base_origin.sock
                                    if (next_case
                                            and held["native_calls"] > 1):
                                        if frame_case and native._frame_origin is not None:
                                            assert (count
                                                    == native._frame_origin.step_origin.requested)
                                        else:
                                            assert count == native._next_read_origin.requested
                                    else:
                                        assert count == 8
                                    try:
                                        value = receive(sock, min(count, 6) if (
                                            next_case and mutation.endswith("_short")
                                            and held["native_calls"] > 1) else count)
                                    except OSError as error:
                                        held["native_receive_errno"] = error.errno
                                        raise
                                    held["native_returned_count"] = len(value)
                                    if (frame_case and mutation.endswith("_feedshadow")
                                            and held["native_calls"] == 3):
                                        def foreign_feed(*args):
                                            held["foreign_frame_feed"] = True
                                            raise AssertionError("foreign feed dispatched")
                                        native._frame_origin.scope.parser.feed = foreign_feed
                                    if next_case and held["native_calls"] > 1:
                                        held["next_actual_received"] = len(value)
                                        if mutation.endswith("_alloc"):
                                            class ForeignStepAllocation:
                                                def __getitem__(self, key):
                                                    held["foreign_step_getitem"] = True
                                                    raise AssertionError("foreign step access")
                                            native._next_read_allocation_origin = (
                                                ForeignStepAllocation())
                                    if (mutation.endswith("_lostack")
                                            and (not next_case or held["native_calls"] > 1)):
                                        raise OSError("synthetic lost receive acknowledgement")
                                    return value

                                monkeypatch.setattr(NativeCleanupRead, "_receive",
                                                    staticmethod(observed_receive))
                                probe_case = mutation.endswith((
                                    "_probecounterbad", "_probereadingbad", "_probewritingbad"))
                                if probe_case:
                                    from hmp_plugin import (
                                        presentation_credential_cleanup_read as nr,
                                    )
                                    timeout_probe = nr._TIMEOUT

                                    def changed_final_probe(sock):
                                        value = timeout_probe(sock)
                                        if not held.get("native_probe_changed"):
                                            held["native_probe_changed"] = True
                                            if mutation.endswith("_probecounterbad"):
                                                class ForeignCounter:
                                                    def __eq__(self, other):
                                                        held["foreign_native_counter_eq"] = True
                                                        raise AssertionError("foreign counter")
                                                native._received = native._received_origin = (
                                                    ForeignCounter())
                                            elif mutation.endswith("_probereadingbad"):
                                                reader._base_origin.channel._reading = True
                                            else:
                                                reader._base_origin.channel._writing = True
                                        return value

                                    monkeypatch.setattr(nr, "_TIMEOUT", changed_final_probe)
                                if mutation.endswith((
                                        "_timeoutbad", "_blockingbad", "_fdbad",
                                        "_posttimeoutbad", "_postfdbad")):
                                    native_remaining = RemoteCleanupOwner._remaining

                                    def native_fd_clock_fault(cleanup):
                                        value = native_remaining(cleanup)
                                        post = mutation.endswith(("_posttimeoutbad", "_postfdbad"))
                                        if (native._attempted and (native._returned if post
                                                                  else not native._returned)
                                                and not held.get("native_fd_changed")):
                                            held["native_fd_changed"] = True
                                            sock = reader._base_origin.sock
                                            if mutation.endswith((
                                                    "_timeoutbad", "_posttimeoutbad")):
                                                sock.settimeout(0.2)
                                            elif mutation.endswith("_blockingbad"):
                                                sock.setblocking(True)
                                            else:
                                                import os
                                                import socket
                                                left, right = socket.socketpair()
                                                left.setblocking(False)
                                                right.setblocking(False)
                                                held["native_fd_fixture_sockets"] = (
                                                    sock, left, right)
                                                os.dup2(left.fileno(), sock.fileno(),
                                                        inheritable=False)
                                        return value

                                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                        native_fd_clock_fault)
                                if mutation.endswith((
                                        "_keybad", "_pendingbad", "_pendingpairbad",
                                        "_counterbad", "_scopebad")):
                                    native_remaining = RemoteCleanupOwner._remaining

                                    def native_clock_fault(cleanup):
                                        value = native_remaining(cleanup)
                                        if (native._count_known
                                                and not held.get("native_clock_changed")):
                                            held["native_clock_changed"] = True
                                            assert native._received == 8
                                            if mutation.endswith("_keybad"):
                                                keys["gateway"].retire()
                                            elif mutation.endswith("_counterbad"):
                                                class ForeignNativeCount:
                                                    def __eq__(self, other):
                                                        held["foreign_native_count_eq"] = True
                                                        raise AssertionError("foreign native count")
                                                native._received = native._received_origin = (
                                                    ForeignNativeCount())
                                            elif mutation.endswith("_scopebad"):
                                                held["native_original_scope"] = native._scope_origin
                                                copied = native._scope_origin._replace()
                                                native._scope = native._scope_origin = copied
                                            else:
                                                replacement = bytearray(b"untouched replacement")
                                                if mutation.endswith("_pendingpairbad"):
                                                    replacement = bytes(bytearray(
                                                        native._pending_origin))
                                                    assert replacement is not (
                                                        native._pending_allocation_origin[1])
                                                held["native_replacement"] = replacement
                                                native._pending = replacement
                                                native._pending_origin = replacement
                                        return value

                                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                        native_clock_fault)
                                observer = NativeCleanupRead.current_for_cleanup

                                def observed_native(owner):
                                    value = observer(owner)
                                    assert owner is native
                                    if next_case:
                                        assert not next_failure
                                        wanted = (native._frame_origin.done if frame_case else
                                                  native._auth_origin.fact if auth_case else
                                                  native._next_read_origin.fact)
                                        assert value is wanted
                                        assert value.total_received == (
                                            native._frame_origin.ledger_origin.received
                                            if frame_case else native._ledger_origin.received)
                                    else:
                                        assert value.count == 8
                                    with pytest.raises(FrameError):
                                        native.current_pending()
                                    with pytest.raises(FrameError):
                                        notice.current_stop_for_cleanup()
                                    assert not notice._unknown
                                    native_observed.set()
                                    return value

                                monkeypatch.setattr(NativeCleanupRead, "current_for_cleanup",
                                                    observed_native)
                                native_failure = not next_case and mutation.endswith((
                                    "_keybad", "_pendingbad", "_lostack", "_eof", "_blocked",
                                    "_timeoutbad", "_blockingbad", "_fdbad",
                                    "_probecounterbad", "_probereadingbad", "_probewritingbad",
                                    "_posttimeoutbad", "_postfdbad", "_counterbad",
                                    "_pendingpairbad", "_scopebad"))
                                if native_failure:
                                    with pytest.raises(FrameError):
                                        native.run_once()
                                    assert native._failed and native._unknown
                                    assert native._pending_origin is None
                                else:
                                    try:
                                        receipt = native.run_once()
                                    except FrameError:
                                        if "native_pre_io_failure" in held:
                                            raise held["native_pre_io_failure"] from None
                                        raise
                                    held["native_original_receipt"] = receipt
                                    assert receipt.count == 8
                                    assert native.current_pending() is receipt
                                    assert native._pending_origin == held["native_expected"]
                                    assert not cursor._parser._buffer_origin
                                if ("_native_consume_" in mutation
                                        and not next_case):
                                    from hmp_plugin.presentation_credential_stream import (
                                        SignedCleanupAuthPrefix,
                                    )
                                    feed = SignedCleanupAuthPrefix.feed
                                    held["consume_feed_calls"] = 0

                                    if mutation.endswith("_initial"):
                                        original_fence = NativeCleanupRead._final_socket_fence

                                        def first_consume_boundary(owner, scope):
                                            if owner._consume_attempted:
                                                held["consume_initial_boundary"] = True
                                                monkeypatch.setattr(NativeCleanupRead,
                                                    "_final_socket_fence", original_fence)
                                                raise FrameError(
                                                    "SYNTHETIC_INITIAL_CONSUME_FAILURE")
                                            return original_fence(owner, scope)

                                        monkeypatch.setattr(NativeCleanupRead,
                                            "_final_socket_fence", first_consume_boundary)

                                    def observed_consume_feed(parser, chunk):
                                        held["consume_feed_calls"] += 1
                                        assert parser is cursor._parser_origin
                                        assert chunk is native._pending_allocation_origin[1]
                                        if mutation.endswith("_partial"):
                                            feed(parser, chunk[:4])
                                            raise FrameError("SYNTHETIC_PARTIAL_FEED_FAILURE")
                                        feed(parser, chunk)
                                        if mutation.endswith("_retired"):
                                            keys["gateway"].retire()
                                        elif mutation.endswith("_parsercopy"):
                                            replacement = bytearray(parser._buffer_origin)
                                            parser._buffer = parser._buffer_origin = replacement
                                            held["consume_parser_replacement"] = replacement
                                        elif mutation.endswith("_countdrift"):
                                            class ForeignConsumeCount:
                                                def __eq__(self, other):
                                                    held["foreign_consume_count_eq"] = True
                                                    raise AssertionError("foreign consume count")
                                            native._received = native._received_origin = (
                                                ForeignConsumeCount())

                                    monkeypatch.setattr(SignedCleanupAuthPrefix, "feed",
                                                        observed_consume_feed)
                                    if mutation.endswith(("_progresscopy", "_fdmode")):
                                        remaining = RemoteCleanupOwner._remaining

                                        def post_consume_clock(cleanup):
                                            value = remaining(cleanup)
                                            if (native._consume_returned
                                                    and not held.get("consume_post_changed")):
                                                held["consume_post_changed"] = True
                                                if mutation.endswith("_fdmode"):
                                                    reader._base_origin.sock.settimeout(0.2)
                                                else:
                                                    held["consume_original_progress"] = (
                                                        native._progress_origin)
                                                    copied = native._progress_origin._replace()
                                                    native._progress = copied
                                                    native._progress_origin = copied
                                            return value

                                        monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                            post_consume_clock)
                                    with pytest.raises(FrameError):
                                        native.consume_pending()
                                    assert native._consume_attempted
                                    assert not native._consume_complete
                                    assert native._native_count_allocation_origin[1] == 8
                                    assert native._pending_origin is None
                                    with pytest.raises(FrameError):
                                        native.consume_pending()
                                    assert held["consume_feed_calls"] == (
                                        0 if mutation.endswith("_initial") else 1)
                                    assert native._consume_attempt_allocation_origin is not None
                                    if mutation.endswith("_initial"):
                                        assert held["consume_initial_boundary"]
                                        assert native._consume_allocation_origin is None
                                    assert "foreign_consume_count_eq" not in held
                                    held["parser_consumption_failed"] = True
                                if mutation.endswith("_consume") or next_case:
                                    async def wrong_consumer():
                                        with pytest.raises(FrameError):
                                            native.consume_pending()
                                    consumed = native.consume_pending()
                                    assert consumed.count == 8
                                    assert consumed.before.parser is cursor._parser_origin
                                    assert consumed.after.parser is cursor._parser_origin
                                    assert consumed.after.value == held["native_expected"]
                                    assert native._consume_complete and native._consume_returned
                                    assert native._pending_origin is None
                                    assert native._native_count_allocation_origin[1] == 8
                                    with pytest.raises(FrameError):
                                        native.consume_pending()
                                    with pytest.raises(FrameError):
                                        native.current_pending()
                                    assert not native._failed and not native._unknown
                                    held["parser_consumption_checked"] = True
                                    if next_case:
                                        from hmp_plugin.presentation_credential_stream import (
                                            SignedCleanupAuthPrefix,
                                        )
                                        parser = cursor._parser_origin
                                        needed = SignedCleanupAuthPrefix.needed.fget(parser)
                                        if mutation.endswith("_foreign"):
                                            class ForeignProgress:
                                                def __getattr__(self, name):
                                                    held["foreign_progress_getter"] = True
                                                    raise AssertionError("foreign progress access")
                                            replacement = ForeignProgress()
                                            native._progress = native._progress_origin = replacement
                                            with pytest.raises(FrameError):
                                                native.read_and_consume_next()
                                            assert "foreign_progress_getter" not in held
                                            assert native._next_read_origin is None
                                            assert native._ledger_origin is None
                                            assert held["native_calls"] == 1
                                        elif next_failure:
                                            with pytest.raises(FrameError):
                                                native.read_and_consume_next()
                                            step = native._next_read_origin
                                            assert (step.attempted and step.failed
                                                    and not step.complete)
                                            assert (step.pending is None
                                                    and step.pending_cell is None)
                                            if mutation.endswith("_alloc"):
                                                assert step.count_known and step.received == needed
                                                assert "foreign_step_getitem" not in held
                                            else:
                                                assert not step.count_known and not step.returned
                                            with pytest.raises(FrameError):
                                                native.read_and_consume_next()
                                            assert held["native_calls"] == 2
                                        else:
                                            next_fact = native.read_and_consume_next()
                                            assert next_fact.ordinal == 1
                                            assert next_fact.count == (
                                                6 if mutation.endswith("_short") else needed)
                                            assert (next_fact.total_received
                                                    == next_fact.total_committed)
                                            assert next_fact.after.parser is parser
                                            if mutation.endswith("_short"):
                                                import weakref
                                                old_step = weakref.ref(native._next_read_origin)
                                                second = native.read_and_consume_next()
                                                assert second.ordinal == 2 and second.count == 6
                                                assert second.total_received == 20
                                                assert old_step() is None  # no linked history
                                            else:
                                                assert next_fact.total_received == 8 + needed
                                                assert (SignedCleanupAuthPrefix.needed.fget(parser)
                                                        == 0)
                                                ledger = native._ledger_origin
                                                step = native._next_read_origin
                                                with pytest.raises(FrameError):
                                                    native.read_and_consume_next()
                                                assert native._ledger_origin is ledger
                                                assert native._next_read_origin is step
                                            assert native._next_read_origin.pending is None
                                            assert not native._failed and not native._unknown
                                        held["next_read_checked"] = True
                                        if auth_case:
                                            finish = SignedCleanupAuthPrefix.finish
                                            held["auth_finish_calls"] = 0

                                            def observed_auth_finish(parser):
                                                held["auth_finish_calls"] += 1
                                                result = finish(parser)
                                                if mutation.endswith("_lost"):
                                                    raise OSError(
                                                        "synthetic auth acknowledgement lost")
                                                if mutation.endswith("_retired"):
                                                    keys["gateway"].retire()
                                                if mutation.endswith("_ledger"):
                                                    class ForeignAuthLedger:
                                                        def __getattr__(self, name):
                                                            held["auth_ledger_getter"] = True
                                                            raise AssertionError("foreign ledger")
                                                    native._ledger_origin = ForeignAuthLedger()
                                                if mutation.endswith("_counter"):
                                                    class ForeignAuthCount:
                                                        def __eq__(self, other):
                                                            held["auth_count_eq"] = True
                                                            raise AssertionError("foreign counter")
                                                    native._next_read_origin.received = (
                                                        ForeignAuthCount())
                                                if mutation.endswith("_values"):
                                                    from dataclasses import replace
                                                    result = replace(result,
                                                        frame_length=result.frame_length + 1)
                                                if mutation.endswith("_scope"):
                                                    class ForeignAuthScope:
                                                        def __getattr__(self, name):
                                                            held["auth_scope_getter"] = True
                                                            raise AssertionError(
                                                                "foreign auth scope")
                                                    native._auth_origin.scope = ForeignAuthScope()
                                                return result

                                            monkeypatch.setattr(SignedCleanupAuthPrefix, "finish",
                                                                observed_auth_finish)
                                            if mutation.endswith("_initial"):
                                                fence = NativeCleanupRead._final_socket_fence

                                                def first_auth_fence(owner, scope):
                                                    if owner._auth_origin is not None:
                                                        monkeypatch.setattr(NativeCleanupRead,
                                                            "_final_socket_fence", fence)
                                                        raise FrameError("SYNTHETIC_AUTH_BOUNDARY")
                                                    return fence(owner, scope)

                                                monkeypatch.setattr(NativeCleanupRead,
                                                    "_final_socket_fence", first_auth_fence)
                                            if mutation.endswith("_copy"):
                                                remaining = RemoteCleanupOwner._remaining

                                                def auth_copy_after_clock(cleanup):
                                                    value = remaining(cleanup)
                                                    attempt = native._auth_origin
                                                    if (attempt is not None and attempt.returned
                                                            and not held.get("auth_copied")):
                                                        from dataclasses import replace
                                                        held["auth_copied"] = True
                                                        held["auth_actual_checked"] = (
                                                            attempt.checked)
                                                        attempt.checked = replace(attempt.checked)
                                                    return value

                                                monkeypatch.setattr(RemoteCleanupOwner,
                                                    "_remaining", auth_copy_after_clock)
                                            if auth_failure:
                                                with pytest.raises(FrameError):
                                                    native.finish_authentication()
                                                attempt = native._auth_origin
                                                assert attempt.failed and not attempt.complete
                                                assert not parser._buffer_origin
                                                assert native._failed and native._unknown
                                                assert "auth_ledger_getter" not in held
                                                assert "auth_count_eq" not in held
                                                assert "auth_scope_getter" not in held
                                                assert attempt.scope_origin.total_received == (
                                                    held["next_record_length"])
                                                with pytest.raises(FrameError):
                                                    native.finish_authentication()
                                            else:
                                                fact = native.finish_authentication()
                                                assert fact.phase == (
                                                    "TERMINAL" if mutation.endswith(
                                                        "_frame_terminal") else "RESULT")
                                                assert fact.scope.before.parser is parser
                                                assert fact.checked is native._auth_origin.checked
                                                assert (fact.total_received
                                                        == held["next_record_length"])
                                                assert (parser._finished
                                                        and not parser._buffer_origin)
                                                assert native._auth_origin.complete
                                                with pytest.raises(FrameError):
                                                    native.finish_authentication()
                                                with pytest.raises(FrameError):
                                                    native.read_and_consume_next()
                                                assert not native._failed and not native._unknown
                                            assert held["auth_finish_calls"] == (
                                                0 if mutation.endswith("_initial") else 1)
                                            held["auth_completion_checked"] = True
                                            if frame_case:
                                                exercise_native_frame(native, fact)
                                    if not next_failure and not auth_failure and not frame_failure:
                                        await asyncio.create_task(wrong_consumer())
                                        assert native._consume_complete and not native._failed
                                if mutation.endswith("_parseradvancebad"):
                                    from hmp_plugin.presentation_credential_stream import (
                                        SignedCleanupAuthPrefix,
                                    )
                                    # Actual received bytes, same original parser. A raw
                                    # feed is DATA progress, not an ownership transfer:
                                    # the frozen stopped cursor must never certify it.
                                    parser = cursor._parser_origin
                                    pending = native._pending_origin
                                    SignedCleanupAuthPrefix.feed(parser, pending)
                                    assert bytes(parser._buffer_origin) == pending
                                    with pytest.raises(FrameError):
                                        native.current_pending()
                                    assert native._native_count_allocation_origin[1] == 8
                                    assert native._pending_origin is None
                                    assert native._failed and native._unknown
                                    held["actual_parser_advance_refused"] = True
                                    pending = None
                                if mutation.endswith("_receiptbad"):
                                    native_remaining = RemoteCleanupOwner._remaining

                                    def native_receipt_drift(cleanup):
                                        value = native_remaining(cleanup)
                                        if not held.get("native_receipt_changed"):
                                            held["native_receipt_changed"] = True
                                            copied = native._fact_origin._replace()
                                            native._fact = native._fact_origin = copied
                                        return value

                                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                        native_receipt_drift)
                                    with pytest.raises(FrameError):
                                        native.current_pending()
                                    assert native._fact_allocation_origin[1] is receipt
                                with pytest.raises(FrameError):
                                    native.run_once()
                                with pytest.raises(FrameError):
                                    idle_reader.current_idle()
                                if mutation.endswith(("_timeoutbad", "_blockingbad", "_fdbad")):
                                    assert held["native_fd_changed"]
                                    assert held["native_calls"] == 0
                                    assert held["native_pre_io_failure_stage"] == "socket_fence"
                                elif probe_case:
                                    assert held["native_probe_changed"]
                                    assert held["native_calls"] == 0
                                    assert (held["native_pre_io_failure_stage"]
                                            == "dispatch_metadata")
                                    assert "foreign_native_counter_eq" not in held
                                else:
                                    assert held["native_calls"] == (
                                        2 if frame_pure_failure else
                                        3 if frame_case and mutation.endswith("_feedshadow") else
                                        5 if frame_case else
                                        3 if next_case and mutation.endswith("_short") else
                                        1 if mutation.endswith("_foreign") else
                                        2 if next_case else 1)
                                if mutation in ("wake_reserve_notice_native",
                                                "wake_reserve_notice_native_workflagbad",
                                                "wake_reserve_notice_native_consume",
                                                "wake_reserve_notice_native_consume_next",
                                                "wake_reserve_notice_native_consume_next_short"
                                                ) or (
                                        auth_case and not auth_failure and not frame_failure):
                                    assert not native._failed and not notice._unknown
                                    async with asyncio.timeout_at(
                                            reader._base_origin.intent.end_ns / 1e9):
                                        await native_observed.wait()
                                    if mutation.endswith("_workflagbad"):
                                        owned._cleanup_owner_snapshot._initialized = False
                            if next_case:
                                assert held["next_read_checked"]
                                if auth_case:
                                    assert held["auth_completion_checked"]
                                    assert not cursor._parser._buffer_origin
                                elif not next_failure:
                                    assert (bytes(cursor._parser._buffer_origin)
                                            == native._next_read_origin.after.value)
                            elif "_native_consume_" in mutation:
                                assert held["parser_consumption_failed"]
                                count = (0 if mutation.endswith("_initial") else
                                         4 if mutation.endswith("_partial") else 8)
                                assert bytes(cursor._parser._buffer_origin) == (
                                    held["native_expected"][:count])
                            elif mutation.endswith("_consume"):
                                assert held["parser_consumption_checked"]
                                assert (bytes(cursor._parser._buffer_origin)
                                        == held["native_expected"])
                            elif mutation.endswith("_parseradvancebad"):
                                assert held["actual_parser_advance_refused"]
                                assert (bytes(cursor._parser._buffer_origin)
                                        == held["native_expected"])
                            else:
                                assert (cursor._parser._buffer_origin
                                        == notice._reservation.capture.envelope.values)
                            if mutation.endswith((
                                    "_cursorstatebad", "_cursorpairbad",
                                    "_cursoradmissionscopebad", "_cursoradmissionfactbad",
                                    "_cursoradmissionownerbad",
                                    "_cursoradmissionreservationbad", "_cursoradmissionendbad")):
                                original_remaining = RemoteCleanupOwner._remaining

                                def cursor_clock_drift(cleanup):
                                    value = original_remaining(cleanup)
                                    work_task = reader._base_origin.allocation.task
                                    if (asyncio.current_task() is work_task
                                            and not held.get("cursor_state_changed")):
                                        held["cursor_state_changed"] = True
                                        if mutation.endswith((
                                                "_cursoradmissionreservationbad",
                                                "_cursoradmissionendbad")):
                                            class ForeignReservation:
                                                def __getattr__(self, name):
                                                    held["foreign_idle_reservation_getter"] = True
                                                    raise AssertionError("foreign reservation")
                                            class ForeignEnd:
                                                def __ge__(self, other):
                                                    held["foreign_idle_end_order"] = True
                                                    raise AssertionError("foreign end ordering")
                                            old = idle_reader._scope_origin
                                            reservation = ForeignReservation()
                                            if mutation.endswith("_cursoradmissionendbad"):
                                                reservation = old[0].reservation._replace(
                                                    end=ForeignEnd())
                                            bad_stop = old[0]._replace(reservation=reservation)
                                            cursor._fact = cursor._fact_origin = bad_stop
                                            scope = (bad_stop, *old[1:])
                                            idle_reader._scope = idle_reader._scope_origin = scope
                                            idle_reader._scope_allocation_origin = (
                                                idle_reader, scope)
                                            with pytest.raises(FrameError):
                                                SignedCleanupReader._metadata(idle_reader)
                                            held["idle_reservation_type_refused"] = True
                                        elif mutation.endswith("_cursoradmissionscopebad"):
                                            scope = tuple(v for v in idle_reader._scope_origin)
                                            held["admission_original_scope"] = (
                                                idle_reader._scope_origin)
                                            idle_reader._scope = idle_reader._scope_origin = scope
                                            fact = idle_reader._fact_origin._replace(scope=scope)
                                            idle_reader._fact = idle_reader._fact_origin = fact
                                        elif mutation.endswith("_cursoradmissionfactbad"):
                                            held["admission_original_fact"] = (
                                                idle_reader._fact_origin)
                                            fact = idle_reader._fact_origin._replace()
                                            idle_reader._fact = idle_reader._fact_origin = fact
                                        elif mutation.endswith("_cursoradmissionownerbad"):
                                            held["admission_original_cursor"] = cursor
                                            replacement = SignedStoppedCursor.__new__(
                                                SignedStoppedCursor)
                                            replacement.__dict__.update(cursor.__dict__)
                                            replacement._reader_allocation_origin = (
                                                replacement, idle_reader)
                                            idle_reader._cursor = replacement
                                            idle_reader._cursor_origin = replacement
                                        elif mutation.endswith("_cursorpairbad"):
                                            from hmp_plugin.presentation_credential_stream import (
                                                SignedCleanupAuthPrefix,
                                            )
                                            capture = notice._reservation.capture
                                            held["cursor_original_parser"] = cursor._parser_origin
                                            replacement = SignedCleanupAuthPrefix(
                                                capture.envelope.values,
                                                sender_public=capture.scope.pins[0],
                                                receiver_public=capture.scope.pins[1],
                                                expected_context={
                                                    k: v for k, v in capture.scope.expected
                                                    if k != "phase"})
                                            cursor._parser = cursor._parser_origin = replacement
                                            state = (replacement._buffer_origin,
                                                     bytes(replacement._buffer_origin),
                                                     replacement._target_origin,
                                                     replacement._header_done_origin)
                                            cursor._parser_state = state
                                            cursor._parser_state_origin = state
                                        else:
                                            parser = cursor._parser
                                            parser._target = parser._target_origin = 9
                                    return value

                                monkeypatch.setattr(RemoteCleanupOwner, "_remaining",
                                                    cursor_clock_drift)
                                with pytest.raises(FrameError):
                                    idle_reader.current_idle()
                                assert held["cursor_state_changed"] and cursor._failed
                                assert idle_reader._failed
                                assert "foreign_idle_reservation_getter" not in held
                                assert "foreign_idle_end_order" not in held
                                if mutation.endswith((
                                        "_cursoradmissionreservationbad",
                                        "_cursoradmissionendbad")):
                                    assert held["idle_reservation_type_refused"]
                                if mutation.endswith("_cursoradmissionscopebad"):
                                    assert idle_reader._scope_allocation_origin[1] is (
                                        held["admission_original_scope"])
                                elif mutation.endswith("_cursoradmissionfactbad"):
                                    assert idle_reader._fact_allocation_origin[1] is (
                                        held["admission_original_fact"])
                                elif mutation.endswith("_cursoradmissionownerbad"):
                                    assert idle_reader._cursor_allocation_origin[1] is cursor
                                    assert idle_reader._cursor_origin is not cursor
                                if mutation.endswith("_cursorpairbad"):
                                    original_parser = held["cursor_original_parser"]
                                    assert cursor._parser_allocation_origin[1] is original_parser
                                    assert cursor._parser_origin is not original_parser
                        with pytest.raises((FrameError, AuthorityRefusalError)):
                            SignedStoppedCursor.retain(notice)
                        if "_notice_native" in mutation:
                            assert not cursor._failed
                            if mutation.endswith("_consume_next_foreign") or frame_pure_failure:
                                assert not native._failed
                                assert "foreign_progress_getter" not in held
                            elif auth_case and not auth_failure and not frame_failure:
                                assert native._auth_origin.complete and not native._failed
                            elif mutation not in ("wake_reserve_notice_native",
                                                "wake_reserve_notice_native_workflagbad",
                                                "wake_reserve_notice_native_consume",
                                                "wake_reserve_notice_native_consume_next",
                                                "wake_reserve_notice_native_consume_next_short"):
                                assert native._failed and notice._unknown
                        elif "_notice_cursor" in mutation:
                            assert cursor._failed and notice._unknown
                            assert owned._cleanup_owner_snapshot._unknown
                        else:
                            assert not cursor._failed and not notice._unknown
                        held["reader_notice_validated"] = True
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
                                with pytest.raises(FrameError):
                                    idle_reader.current_idle()
                                assert not idle_reader._failed
                                with pytest.raises(FrameError):
                                    notice.current_stop_for_reader()
                                assert not notice._failed and not notice._unknown
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
                with pytest.raises((FrameError, AuthorityRefusalError)):
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
            if ("_notice_cleanup" in mutation or "_notice_reader_" in mutation
                    or "_notice_cursor" in mutation or "_notice_native" in mutation):
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
                            "wake_reserve_notice_reader_copybad",
                            "wake_reserve_notice_reader_rolebad",
                            "wake_reserve_notice_cursorinitbad",
                            "wake_reserve_notice_cursorstatebad",
                            "wake_reserve_notice_cursorpairbad",
                            "wake_reserve_notice_cursoradmissionscopebad",
                            "wake_reserve_notice_cursoradmissionfactbad",
                            "wake_reserve_notice_cursoradmissionownerbad",
                            "wake_reserve_notice_cursoradmissioninitbad",
                            "wake_reserve_notice_cursoradmissionearlybad",
                            "wake_reserve_notice_cursoradmissionreservationbad",
                            "wake_reserve_notice_cursoradmissionendbad",
                            "wake_reserve_notice_native",
                            "wake_reserve_notice_native_keybad",
                            "wake_reserve_notice_native_pendingbad",
                            "wake_reserve_notice_native_lostack",
                            "wake_reserve_notice_native_eof",
                            "wake_reserve_notice_native_blocked",
                            "wake_reserve_notice_native_receiptbad",
                            "wake_reserve_notice_native_timeoutbad",
                            "wake_reserve_notice_native_blockingbad",
                            "wake_reserve_notice_native_fdbad",
                            "wake_reserve_notice_native_probecounterbad",
                            "wake_reserve_notice_native_probereadingbad",
                            "wake_reserve_notice_native_probewritingbad",
                            "wake_reserve_notice_native_posttimeoutbad",
                            "wake_reserve_notice_native_postfdbad",
                            "wake_reserve_notice_native_counterbad",
                            "wake_reserve_notice_native_pendingpairbad",
                            "wake_reserve_notice_native_scopebad",
                            "wake_reserve_notice_native_workflagbad",
                            "wake_reserve_notice_native_parseradvancebad",
                            "wake_reserve_notice_native_consume",
                            "wake_reserve_notice_native_consume_next",
                            "wake_reserve_notice_native_consume_next_auth",
                            "wake_reserve_notice_native_consume_next_auth_frame",
                            "wake_reserve_notice_native_consume_next_auth_frame_terminal",
                            "wake_reserve_notice_native_consume_next_auth_frame_bodyhash",
                            "wake_reserve_notice_native_consume_next_auth_frame_authforeign",
                            "wake_reserve_notice_native_consume_next_auth_frame_feedshadow",
                            "wake_reserve_notice_native_consume_next_auth_frame_finishshadow",
                            "wake_reserve_notice_native_consume_next_auth_frame_postledger",
                            "wake_reserve_notice_native_consume_next_auth_frame_headcopy",
                            "wake_reserve_notice_native_consume_next_auth_signature",
                            "wake_reserve_notice_native_consume_next_auth_lost",
                            "wake_reserve_notice_native_consume_next_auth_retired",
                            "wake_reserve_notice_native_consume_next_auth_copy",
                            "wake_reserve_notice_native_consume_next_auth_initial",
                            "wake_reserve_notice_native_consume_next_auth_ledger",
                            "wake_reserve_notice_native_consume_next_auth_counter",
                            "wake_reserve_notice_native_consume_next_auth_values",
                            "wake_reserve_notice_native_consume_next_auth_scope",
                            "wake_reserve_notice_native_consume_next_short",
                            "wake_reserve_notice_native_consume_next_blocked",
                            "wake_reserve_notice_native_consume_next_lostack",
                            "wake_reserve_notice_native_consume_next_alloc",
                            "wake_reserve_notice_native_consume_next_foreign",
                            "wake_reserve_notice_native_consume_initial",
                            "wake_reserve_notice_native_consume_retired",
                            "wake_reserve_notice_native_consume_partial",
                            "wake_reserve_notice_native_consume_parsercopy",
                            "wake_reserve_notice_native_consume_countdrift",
                            "wake_reserve_notice_native_consume_progresscopy",
                            "wake_reserve_notice_native_consume_fdmode",
                            "wake_reserve_wait_dispatchbad"):
                assert reader._wake_release_origin is not None and not reader._io_unknown
                assert not reader._active and reader._failed and not reader._buffer_origin
                if mutation == "wake_release":
                    reader._target = reader._target_origin = reader._target_origin + 1
                    with pytest.raises(FrameError):
                        reader._released(channel)
                    assert reader._io_unknown
                elif mutation.endswith(("_swapcurrent", "_reservationclock",
                                        "_cleanup_copybad", "_cleanup_futurebad",
                                        "_reader_copybad")):
                    with pytest.raises(FrameError):
                        reader._released(channel)
                    assert reader._io_unknown
                elif mutation in ("wake_reserve_notice_native_fdbad",
                                  "wake_reserve_notice_native_postfdbad",
                                  "wake_reserve_notice_native_probereadingbad",
                                  "wake_reserve_notice_native_probewritingbad",
                                  "wake_reserve_notice_native_workflagbad",
                                  "wake_reserve_notice_native_consume_next_alloc"):
                    # Native fd/claim debt is checked separately; do not turn the
                    # historical local wake record into current descriptor credit.
                    pass
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
                if "_notice_reader_" in mutation:
                    assert held["notice_published"] and held["reader_notice_tail_changed"]
                    assert notice._failed and notice._unknown
                elif "_notice_cleanup" in mutation:
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
            if "_notice_native" in mutation:
                native = held["native_owner"]
                if mutation in ("wake_reserve_notice_native",
                                "wake_reserve_notice_native_workflagbad",
                                "wake_reserve_notice_native_consume",
                                "wake_reserve_notice_native_consume_next",
                                "wake_reserve_notice_native_consume_next_short") or (
                        auth_case and not auth_failure and not frame_failure):
                    assert native_observed.is_set()
                if not next_case and mutation.endswith((
                        "_lostack", "_blocked", "_timeoutbad", "_blockingbad", "_fdbad")):
                    assert not native._count_known and not native._returned
                    assert native._fact_origin is None
                    if mutation.endswith("_lostack"):
                        assert held["native_returned_count"] == 8
                    if mutation.endswith("_blocked"):
                        import errno
                        assert held["native_receive_errno"] in (errno.EAGAIN, errno.EWOULDBLOCK)
                elif mutation.endswith("_eof"):
                    assert native._received == 0 and native._count_known
                    assert native._fact_origin is None
                elif "_native_probe" in mutation:
                    assert not native._returned and not native._count_known
                    assert "foreign_native_counter_eq" not in held
                    if mutation.endswith("_probereadingbad"):
                        assert reader._base_origin.channel._reading is True
                    elif mutation.endswith("_probewritingbad"):
                        assert reader._base_origin.channel._writing is True
                elif mutation.endswith(("_counterbad", "_consume_countdrift")):
                    assert native._native_count_allocation_origin[1] == 8
                    assert "foreign_native_count_eq" not in held
                else:
                    assert native._received == 8 and native._count_known
                    assert native._native_count_allocation_origin[1] == 8
                assert native._failed and native._unknown
                assert native._pending_origin is None
                assert native._pending_allocation_origin is None
                assert remote._cleanup_owner_snapshot._unknown
                if mutation.endswith("_workflagbad"):
                    assert remote._cleanup_owner_snapshot._initialized is False
                if mutation.endswith("_pendingbad"):
                    assert held["native_replacement"] == b"untouched replacement"
                if mutation.endswith("_pendingpairbad"):
                    assert held["native_replacement"] == held["native_expected"]
                if mutation.endswith("_scopebad"):
                    assert native._scope_allocation_origin[1] is held["native_original_scope"]
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
        for fixture_socket in held.get("native_fd_fixture_sockets", ()):
            # Exact test-created/rebound descriptors only, after actual task
            # termination and protocol refusal; no production release fact.
            fixture_socket.close()
        for key in keys.values():
            key.retire()
