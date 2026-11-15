"""Original broker-task bounded signed BEGIN reader; no native input adoption.

No production startup calls this owner yet. Success proves this local actor read
and checked its bounded bytes, not profile authority, child custody or GO.
"""

from __future__ import annotations

import asyncio
import os
import threading

from .presentation_broker_codec import BrokerBinding, header_size
from .presentation_broker_service import SocketChannel
from .presentation_credential_codec import payload_size
from .presentation_credential_handshake import CredentialHandshakeOwner
from .presentation_credential_phase import (
    _BEGIN_CONTEXT,
    ConsistentBeginInput,
    check_begin_frame,
    check_committed_header,
    stage_begin_commitment,
)
from .presentation_credential_transcript import check_transcript
from .presentation_jobs import INPUT_LIMIT, FrameError

_LOCAL_READ_COMPLETE = object()
_LIMIT = 2048 + 8 + 1024 + INPUT_LIMIT + 4


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_BEGIN_REFUSED")


class CredentialBeginReceiver:
    """One original task/cursor. Failure retains its claim; never reread/retry."""

    @classmethod
    def retain(cls, handshake):
        _require(cls is CredentialBeginReceiver and type(handshake) is CredentialHandshakeOwner)
        channel = handshake._original_channel
        _require(type(channel) is SocketChannel)
        _require(
            getattr(channel, "_credential_begin_receiver", None) is None
            and getattr(channel, "_credential_begin_receiver_snapshot", None) is None
        )
        owner = cls.__new__(cls)
        owner._original_channel = channel
        channel._credential_begin_receiver = channel._credential_begin_receiver_snapshot = owner
        try:
            CredentialBeginReceiver.__init__(owner, handshake)
        except BaseException:
            channel._refused = True
            raise FrameError("BI1_CREDENTIAL_BEGIN_ACQUISITION_REFUSED") from None
        return owner

    def __init__(self, handshake):
        _require(type(self) is CredentialBeginReceiver and "_initialized" not in vars(self))
        self._initialized = self._started = self._complete = self._failed = False
        self._read_intent = self._io_unknown = False
        self._release = None
        self._buffer = self._buffer_origin = bytearray()
        self._buffer_values = b""
        self._pending = self._pending_snapshot = None
        self._target = self._target_snapshot = 0
        self._consumed = self._consumed_snapshot = 0
        self._result = self._result_snapshot = None
        self._handshake = self._handshake_snapshot = handshake
        _require(type(handshake) is CredentialHandshakeOwner)
        CredentialHandshakeOwner._guard(handshake)
        _require(handshake._role == "broker")
        self._channel = self._original_channel
        _require(
            handshake._original_channel is self._channel
            and self._channel._credential_begin_receiver is self
            and self._channel._credential_begin_receiver_snapshot is self
        )
        self._task = handshake._task
        self._loop = handshake._loop
        self._context = self._context_snapshot = (os.getpid(), os.geteuid(), threading.get_ident())
        self._socket = handshake._socket
        self._records = self._records_snapshot = tuple(handshake._records)
        self._common = self._common_snapshot = tuple(sorted(handshake._common.items()))
        selection = handshake._selection
        self._pins = self._pins_snapshot = (selection.peer_public, selection.own_public)
        transcript = check_transcript(
            self._records,
            gateway_public=self._pins[0],
            broker_public=self._pins[1],
            expected_context=dict(self._common),
        )
        self._binding = self._binding_snapshot = BrokerBinding(
            handshake._binding_snapshot.iid,
            handshake._binding_snapshot.listener,
            handshake._binding_snapshot.broker,
            transcript.channel,
            handshake._common["operation_id"],
        )
        b = self._binding
        self._binding_values = self._binding_values_snapshot = (
            b.iid,
            b.listener,
            b.broker,
            b.channel,
            b.operation,
        )
        expected = dict(self._common)
        expected.pop("clock_domain")
        expected.update(
            phase="BEGIN",
            role="gateway",
            direction="g2b",
            sequence=0,
            gateway_boot=transcript.gateway_boot,
            broker_boot=transcript.broker_boot,
            channel=transcript.channel,
            transcript_sha256=transcript.transcript_sha256,
        )
        self._expected = self._expected_snapshot = expected
        self._expected_values = self._expected_values_snapshot = tuple(sorted(expected.items()))
        self._end = self._end_snapshot = handshake._end
        CredentialHandshakeOwner._guard(handshake)
        self._initialized = True
        CredentialBeginReceiver._guard(self)

    def __repr__(self):
        return "<CredentialBeginReceiver payload-and-context-redacted>"

    def _metadata(self):
        _require(
            type(self) is CredentialBeginReceiver
            and self._initialized is True
            and self._failed is False
            and self._io_unknown is False
        )
        _require(
            type(self._handshake) is CredentialHandshakeOwner
            and self._handshake is self._handshake_snapshot
            and type(self._channel) is SocketChannel
            and self._channel is self._original_channel
            and self._handshake._original_channel is self._channel
            and self._channel._credential_begin_receiver is self
            and self._channel._credential_begin_receiver_snapshot is self
        )
        _require(
            type(self._context) is tuple
            and len(self._context) == 3
            and self._context is self._context_snapshot
            and all(type(v) is int for v in self._context)
            and self._context == (os.getpid(), os.geteuid(), threading.get_ident())
        )
        _require(
            type(self._task) is asyncio.Task
            and self._task is self._handshake._task
            and asyncio.current_task() is self._task
            and asyncio.Task.cancelling(self._task) == 0
            and type(self._loop) is asyncio.SelectorEventLoop
            and self._loop is self._handshake._loop
            and asyncio.get_running_loop() is self._loop
            and self._socket is self._handshake._socket
        )
        _require(
            type(self._records) is tuple
            and len(self._records) == 4
            and self._records is self._records_snapshot
            and all(type(v) is bytes and len(v) <= 2048 for v in self._records)
            and type(self._handshake._records) is list
            and all(type(v) is bytes for v in self._handshake._records)
            and tuple(self._handshake._records) == self._records
        )
        _require(
            type(self._common) is tuple
            and len(self._common) == 6
            and self._common is self._common_snapshot
            and all(
                type(row) is tuple
                and len(row) == 2
                and type(row[0]) is str
                and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                for row in self._common
            )
            and type(self._handshake._common) is dict
            and all(
                type(k) is str and type(v) is (int if k == "work_end_ns" else str)
                for k, v in self._handshake._common.items()
            )
            and tuple(sorted(self._handshake._common.items())) == self._common
        )
        _require(
            type(self._expected) is dict
            and self._expected is self._expected_snapshot
            and all(type(k) is str for k in self._expected)
            and self._expected.keys() == _BEGIN_CONTEXT
            and all(
                type(k) is str and type(v) is (int if k in ("sequence", "work_end_ns") else str)
                for k, v in self._expected.items()
            )
            and type(self._expected_values) is tuple
            and self._expected_values is self._expected_values_snapshot
            and all(
                type(row) is tuple
                and len(row) == 2
                and type(row[0]) is str
                and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                for row in self._expected_values
            )
            and tuple(sorted(self._expected.items())) == self._expected_values
        )
        _require(
            type(self._pins) is tuple
            and len(self._pins) == 2
            and self._pins is self._pins_snapshot
            and all(type(v) is bytes and len(v) == 32 for v in self._pins)
            and self._binding is self._binding_snapshot
            and type(self._binding) is BrokerBinding
            and self._binding_values is self._binding_values_snapshot
            and type(self._binding_values) is tuple
            and len(self._binding_values) == 5
            and all(type(v) is str for v in self._binding_values)
            and all(
                type(v) is str
                for v in (
                    self._binding.iid,
                    self._binding.listener,
                    self._binding.broker,
                    self._binding.channel,
                    self._binding.operation,
                )
            )
            and (
                self._binding.iid,
                self._binding.listener,
                self._binding.broker,
                self._binding.channel,
                self._binding.operation,
            )
            == self._binding_values
            and type(self._end) is int
            and self._end is self._end_snapshot
            and self._end == self._handshake._end
        )
        _require(
            type(self._buffer) is bytearray
            and self._buffer is self._buffer_origin
            and len(self._buffer) <= _LIMIT
            and type(self._buffer_values) is bytes
            and bytes(self._buffer) == self._buffer_values
            and type(self._target) is int
            and self._target is self._target_snapshot
            and len(self._buffer) <= self._target <= _LIMIT
            and type(self._read_intent) is bool
            and type(self._started) is bool
            and type(self._complete) is bool
            and self._result is self._result_snapshot
            and (self._result is None or type(self._result) is ConsistentBeginInput)
            and type(self._consumed) is int
            and self._consumed is self._consumed_snapshot
            and 0 <= self._consumed <= _LIMIT
            and self._pending is self._pending_snapshot
            and (
                self._pending is None
                or (
                    type(self._pending) is bytes
                    and len(self._pending) <= self._target - len(self._buffer)
                )
            )
        )
        _require(
            self._consumed
            == len(self._buffer) + (0 if self._pending is None else len(self._pending))
        )

    def _local(self):
        CredentialBeginReceiver._metadata(self)
        _require(
            self._complete is False
            and self._release is None
            and self._result is None
            and self._result_snapshot is None
        )

    def _completed_current(self):
        """Original actor's current checked input; never native/worker permission."""
        CredentialBeginReceiver._metadata(self)
        CredentialBeginReceiver._released(self, self._original_channel)
        CredentialHandshakeOwner._guard(self._handshake)
        CredentialBeginReceiver._metadata(self)
        CredentialBeginReceiver._released(self, self._original_channel)
        _require(self._started is True and self._target == self._consumed == len(self._buffer))
        prefix = raw = frame = checked = result = claim = None
        failed = False
        try:
            prefix = bytes(self._buffer[:8])
            auth_end = 8 + payload_size(prefix)
            raw, frame = bytes(self._buffer[:auth_end]), bytes(self._buffer[auth_end:])
            checked = check_begin_frame(
                raw,
                frame,
                sender_public=self._pins[0],
                receiver_public=self._pins[1],
                expected_context=self._expected,
                binding=self._binding,
            )
            result = self._result_snapshot
            _require(type(result.packet) is bytes and result.packet == checked.packet)
            claim = result.commitment
            from .presentation_credential_phase import ConsistentCommitment

            _require(
                type(claim) is ConsistentCommitment
                and type(claim.canonical_json) is bytes
                and type(claim.frame_sha256) is str
                and type(claim.frame_length) is int
            )
            _require(
                (claim.canonical_json, claim.frame_sha256, claim.frame_length)
                == (
                    checked.commitment.canonical_json,
                    checked.commitment.frame_sha256,
                    checked.commitment.frame_length,
                )
            )
            CredentialHandshakeOwner._guard(self._handshake)
            CredentialBeginReceiver._metadata(self)
            CredentialBeginReceiver._released(self, self._original_channel)
            _require(self._result_snapshot is result)
            return result
        except BaseException:
            failed = True
        finally:
            prefix = raw = frame = checked = result = claim = None
        if failed:
            raise FrameError("BI1_CREDENTIAL_BEGIN_CURRENT_REFUSED") from None

    def _guard(self):
        CredentialBeginReceiver._local(self)
        CredentialHandshakeOwner._guard(self._handshake)
        CredentialBeginReceiver._local(self)  # final native callback cannot alter the cursor

    async def _take(self, target):
        part = None
        try:
            CredentialBeginReceiver._guard(self)
            _require(
                type(target) is int
                and self._target <= target <= _LIMIT
                and self._read_intent is False
                and self._pending is None
            )
            self._target = self._target_snapshot = target
            while len(self._buffer) < target:
                CredentialBeginReceiver._guard(self)
                prior_consumed = self._consumed_snapshot
                remaining = target - len(self._buffer)
                self._read_intent = True
                async with asyncio.timeout_at(self._end / 1e9):
                    part = await self._loop.sock_recv(self._socket, remaining)
                self._pending = self._pending_snapshot = part
                _require(
                    type(part) is bytes
                    and len(part) <= remaining
                    and self._consumed is self._consumed_snapshot is prior_consumed
                )
                self._consumed = self._consumed_snapshot = prior_consumed + len(part)
                CredentialBeginReceiver._guard(self)
                _require(len(part) > 0)
                self._buffer.extend(part)
                self._buffer_values = bytes(self._buffer)
                self._pending = self._pending_snapshot = None
                self._read_intent = False
                CredentialBeginReceiver._guard(self)
            return bytes(self._buffer)
        finally:
            part = None  # no immutable payload alias in a retained failed frame

    async def run(self):
        _require(type(self) is CredentialBeginReceiver)
        original_channel = self._original_channel
        _require(type(original_channel) is SocketChannel)
        original_buffer = self._buffer_origin
        _require(type(original_buffer) is bytearray)
        prefix = raw = framed = result = None
        failed = cancelled = False
        try:
            CredentialBeginReceiver._guard(self)
            _require(self._started is False)
            self._started = True
            prefix = await CredentialBeginReceiver._take(self, 8)
            raw = await CredentialBeginReceiver._take(self, 8 + payload_size(prefix))
            commitment = stage_begin_commitment(
                raw,
                sender_public=self._pins[0],
                receiver_public=self._pins[1],
                expected_context=self._expected,
            )
            CredentialBeginReceiver._guard(self)
            auth_end = len(raw)
            framed = await CredentialBeginReceiver._take(self, auth_end + 8)
            header_end = auth_end + 8 + header_size(framed[auth_end:])
            framed = await CredentialBeginReceiver._take(self, header_end)
            header = check_committed_header(commitment, framed[auth_end:], binding=self._binding)
            CredentialBeginReceiver._guard(self)
            framed = await CredentialBeginReceiver._take(self, header_end + header.body_length)
            result = check_begin_frame(
                raw,
                framed[auth_end:],
                sender_public=self._pins[0],
                receiver_public=self._pins[1],
                expected_context=self._expected,
                binding=self._binding,
            )
            CredentialBeginReceiver._guard(self)
            _require(
                type(result) is ConsistentBeginInput
                and self._read_intent is False
                and self._pending is None
            )
            self._result = self._result_snapshot = result
            self._complete = True
            self._release = _LOCAL_READ_COMPLETE
            return result
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            prefix = raw = framed = result = None
            if failed:
                self._failed = self._io_unknown = True
                original_channel._refused = True
                # Wipe only the original scope-captured private buffer, never a
                # current field that a native callback may have replaced.
                bytearray.clear(original_buffer)
                self._buffer_values = b""
                self._pending = self._pending_snapshot = None
                self._result = self._result_snapshot = None
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_CREDENTIAL_BEGIN_REFUSED") from None

    def _released(self, channel):
        """Historical local IO closure only, not input/native/worker admission."""
        _require(
            type(self) is CredentialBeginReceiver
            and type(channel) is SocketChannel
            and channel is self._original_channel is self._channel
            and channel._credential_begin_receiver is self
            and channel._credential_begin_receiver_snapshot is self
            and self._complete is True
            and self._failed is False
            and self._io_unknown is False
            and self._release is _LOCAL_READ_COMPLETE
            and self._read_intent is False
            and self._pending is None
            and self._pending_snapshot is None
            and type(self._result) is ConsistentBeginInput
            and self._result is self._result_snapshot
        )
