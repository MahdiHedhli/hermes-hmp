"""Actual socket cursor with synthetic keys and MOCKED channel/clock authority.

No production factory, native input adoption, registry, worker or host access.
"""

import asyncio
import hashlib
import json
import time

import pytest

from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_service import SocketChannel
from hmp_plugin.presentation_credential_begin import CredentialBeginReceiver
from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_input_v3 import encode_input_v3
from hmp_plugin.presentation_jobs import INPUT_LIMIT, FrameError

from .test_presentation_credential_handshake import pair as pair
from .test_presentation_credential_scope import input_value


async def setup(pair, monkeypatch, accept_delta=0):
    channels, keys, binding = pair
    end = time.monotonic_ns() + 1_800_000_000
    receivers = []
    reads = []
    reading = asyncio.Event()
    loop = asyncio.get_running_loop()
    recv = loop.sock_recv

    async def observed(sock, count):
        if sock is channels["broker"]._socket_snapshot and receivers:
            reads.append(count)
            reading.set()
        return await recv(sock, count)

    monkeypatch.setattr(loop, "sock_recv", observed)

    async def broker():
        handshake = CredentialHandshakeOwner.retain(
            channels["broker"], keys["broker"], binding, end + accept_delta
        )
        await handshake.run()
        receiver = CredentialBeginReceiver.retain(handshake)
        receivers.append(receiver)
        return await receiver.run()

    task = asyncio.create_task(broker())
    handshake = CredentialHandshakeOwner.retain(channels["gateway"], keys["gateway"], binding, end)
    try:
        await handshake.run()
        await reading.wait()
    except BaseException:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise
    binding = handshake._operation_binding()
    packet = encode_input_v3(dict(input_value(), deadline_ns=end))
    frame = encode_frame(binding, "BEGIN", 0, packet, version=2)
    scope = derive_input_scope(packet, binding)
    transcript = handshake._transcript_snapshot
    statement = dict(handshake._common)
    statement.pop("clock_domain")
    statement.update(
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

    def sign(changes=None):
        claim = dict(statement, **(changes or {}))
        return encode_record(claim, keys["gateway"]._private_key.sign(signing_bytes(claim)))

    return channels, keys, task, receivers[0], reads, frame, packet, sign


@pytest.mark.asyncio
async def test_original_broker_cursor_reads_exact_signed_begin_without_adoption(pair, monkeypatch):
    channels, _, task, receiver, reads, frame, packet, sign = await setup(pair, monkeypatch)
    raw = sign()
    with pytest.raises(FrameError):
        SocketChannel._credential_external_idle(channels["broker"])
    await asyncio.get_running_loop().sock_sendall(
        channels["gateway"]._socket_snapshot, raw + frame + b"TAIL"
    )
    result = await task
    assert receiver._result is receiver._result_snapshot is result
    assert result.packet == packet and receiver._complete is True
    assert receiver._io_unknown is False and receiver._read_intent is False
    assert receiver._pending is None and bytes(receiver._buffer) == raw + frame
    assert len(receiver._buffer) == sum(reads)
    assert channels["broker"]._socket_snapshot.recv(4) == b"TAIL"
    SocketChannel._credential_external_idle(channels["broker"])
    assert not hasattr(result, "authorized") and not hasattr(receiver, "ticket")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["signature", "scope", "oversized_header", "eof"])
async def test_failed_original_receive_retains_claim_and_never_retries(pair, monkeypatch, failure):
    channels, _, task, receiver, reads, frame, _, sign = await setup(pair, monkeypatch)
    raw = sign()
    if failure == "signature":
        raw = raw[:-1] + bytes([raw[-1] ^ 1])
    elif failure == "scope":
        raw = sign({"scope_sha256": "f" * 64})
    elif failure == "oversized_header":
        end = 8 + int.from_bytes(frame[4:8], "big")
        row = json.loads(frame[8:end])
        row["body_length"] = INPUT_LIMIT + 5
        header = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        frame = b"HBR1" + len(header).to_bytes(4, "big") + header + frame[end:]
        raw = sign({"frame_length": len(frame), "frame_sha256": hashlib.sha256(frame).hexdigest()})
    if failure == "eof":
        raw, frame = raw[:9], b""
    await asyncio.get_running_loop().sock_sendall(channels["gateway"]._socket_snapshot, raw + frame)
    if failure == "eof":
        import socket

        channels["gateway"]._socket_snapshot.shutdown(socket.SHUT_WR)
    with pytest.raises(FrameError):
        await task
    assert receiver._failed is True and receiver._io_unknown is True
    assert receiver._result is None and receiver._complete is False
    assert channels["broker"]._credential_begin_receiver_snapshot is receiver
    assert receiver._buffer == b"" and receiver._buffer_values == b""
    assert receiver._pending is None and receiver._pending_snapshot is None
    if failure == "signature":
        assert receiver._consumed == len(raw)  # no HBR1 prefix/body read
    if failure == "oversized_header":
        assert receiver._consumed == len(raw) + 8 + len(header)  # no body read
    before = list(reads)
    with pytest.raises(FrameError):
        await receiver.run()
    assert reads == before
    with pytest.raises(FrameError):
        SocketChannel._credential_external_idle(channels["broker"])


@pytest.mark.asyncio
async def test_cancelled_original_read_keeps_unknown_cursor_and_channel_claim(pair, monkeypatch):
    channels, _, task, receiver, reads, _, _, _ = await setup(pair, monkeypatch)
    assert receiver._read_intent is True and reads == [8]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert receiver._io_unknown is True and receiver._failed is True
    assert receiver._result is None and receiver._read_intent is True
    assert receiver._buffer == b""
    with pytest.raises(FrameError):
        SocketChannel._credential_external_idle(channels["broker"])


@pytest.mark.asyncio
async def test_broker_conserves_earlier_accept_deadline_without_rewriting_input(pair, monkeypatch):
    channels, _, task, receiver, _, frame, _, sign = await setup(pair, monkeypatch, -100_000_000)
    assert receiver._end < receiver._expected["work_end_ns"]
    original_end = receiver._end
    await asyncio.get_running_loop().sock_sendall(
        channels["gateway"]._socket_snapshot, sign() + frame
    )
    await task
    assert receiver._end == original_end and receiver._complete is True


@pytest.mark.asyncio
async def test_partial_body_failure_drops_payload_and_original_exception_context(pair, monkeypatch):
    import socket

    channels, _, task, receiver, _, frame, _, sign = await setup(pair, monkeypatch)
    sent = sign() + frame[:-5]
    original_buffer = receiver._buffer_origin
    await asyncio.get_running_loop().sock_sendall(channels["gateway"]._socket_snapshot, sent)
    channels["gateway"]._socket_snapshot.shutdown(socket.SHUT_WR)
    with pytest.raises(FrameError) as caught:
        await task
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert receiver._consumed == len(sent) and original_buffer == b""
    assert receiver._buffer_values == b"" and receiver._pending_snapshot is None
    assert receiver._result is None and receiver._io_unknown is True
    tb = caught.value.__traceback__
    while tb:
        if tb.tb_frame.f_code.co_name == "run":
            assert all(
                tb.tb_frame.f_locals[key] is None for key in ("prefix", "raw", "framed", "result")
            )
        tb = tb.tb_next


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["key", "foreign_buffer"])
async def test_final_body_native_postcheck_drops_original_payload_without_foreign_wipe(
    pair, monkeypatch, mutation
):
    from hmp_plugin.presentation_clock import NativeClockOwner

    channels, keys, task, receiver, _, frame, _, sign = await setup(pair, monkeypatch)
    raw = sign()
    original_buffer = receiver._buffer_origin
    sample = NativeClockOwner.sample
    callbacks = []
    injected = []

    class Foreign:
        def __len__(self):
            callbacks.append("length")
            raise AssertionError("foreign buffer length")

        def clear(self):
            callbacks.append("wipe")
            raise AssertionError("foreign buffer wipe")

    foreign = Foreign()

    def changed(clock):
        now = sample(clock)
        if (
            receiver._target == len(raw) + len(frame)
            and receiver._pending is not None
            and not injected
        ):
            injected.append(True)
            if mutation == "key":
                keys["broker"].retire()
            else:
                receiver._buffer = foreign
        return now

    monkeypatch.setattr(NativeClockOwner, "sample", changed)
    await asyncio.get_running_loop().sock_sendall(channels["gateway"]._socket_snapshot, raw + frame)
    with pytest.raises(FrameError) as caught:
        await task
    assert injected == [True] and callbacks == []
    assert original_buffer == b"" and receiver._buffer_values == b""
    assert receiver._pending is None and receiver._result_snapshot is None
    assert receiver._consumed == len(raw) + len(frame) and receiver._io_unknown is True
    assert caught.value.__context__ is None
    if mutation == "foreign_buffer":
        assert receiver._buffer is foreign  # no repaired field or foreign cleanup
