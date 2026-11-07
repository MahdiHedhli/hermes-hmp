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
                            "cancel_capture_wait", "cancel_capture_partial"):
                assert reader._cancel_release_origin is not None
                assert not reader._active and not reader._io_unknown
                assert reader._consumed == (4 if mutation.endswith("partial") else 0)
            if mutation in ("cancel_generic", "cancel_foreign_end", "cancel_foreign_future"):
                assert reader._cancel_release_origin is None and reader._io_unknown
            if mutation == "cancel_foreign_future":
                assert held["post_wait_future_substitution"]
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
