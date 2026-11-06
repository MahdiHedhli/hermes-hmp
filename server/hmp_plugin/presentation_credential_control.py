"""First signed control frame on the original native controller allocation.

Source-only staging, not a working GO/CANCEL lifecycle. A complete authenticated
read never mints native receipts, observes grammar, adopts a cancellation window,
starts resources or authorizes GO. Production dispatch remains closed.
"""

from __future__ import annotations

import asyncio
import json

from .presentation_broker_codec import BrokerBinding, header_size
from .presentation_credential_codec import payload_size
from .presentation_credential_phase import (
    _EXPECTED,
    check_commitment,
    check_committed_header,
    check_complete_frame,
)
from .presentation_jobs import FrameError

_LIMIT = 2048 + 8 + 1024 + 16


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_CONTROL_READ_REFUSED")


class CredentialControlCursor:
    """One retained original controller cursor; no caller-selected phase or key."""

    @classmethod
    def retain(cls, control):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding
        from .presentation_credential_begin import CredentialBeginReceiver

        _require(cls is CredentialControlCursor and type(control) is BrokerCancellationOwner)
        binding = control._credential_binding_snapshot
        _require(type(binding) is PreparedControlBinding)
        PreparedControlBinding.creator_current(binding)
        _require(control._signed_cursor is None and control._signed_cursor_snapshot is None)
        refs = binding._refs_snapshot
        receiver = refs[6]
        result = CredentialBeginReceiver._completed_current(receiver)
        PreparedControlBinding.creator_current(binding)
        _require(
            binding._refs_snapshot is refs
            and control._credential_binding_snapshot is binding
            and control._credential_binding is binding
        )
        owner = cls.__new__(cls)
        # Retain the consumed original claim before any further validation.
        control._signed_cursor = control._signed_cursor_snapshot = owner
        owner._initialized = owner._started = owner._complete = owner._failed = False
        owner._control = owner._control_snapshot = control
        owner._binding = owner._binding_snapshot = binding
        buffer = bytearray()
        owner._buffer = owner._buffer_origin = buffer
        owner._buffer_values = b""
        owner._target = owner._target_snapshot = 0
        owner._consumed = owner._consumed_snapshot = 0
        owner._read_intent = owner._io_unknown = False
        owner._pending = owner._pending_snapshot = None
        owner._waiter = None
        owner._last_read = None
        owner._raw = owner._frame = owner._header = None
        owner._phase = None
        sock, loop = refs[14]._socket_snapshot, binding._loop
        pins, broker_binding = receiver._pins_snapshot, receiver._binding_snapshot
        end = refs[4].deadline_ns
        owner._socket, owner._loop = sock, loop
        owner._pins = owner._pins_snapshot = pins
        owner._broker_binding = broker_binding
        owner._end = owner._end_snapshot = end
        # BEGIN was reverified by its original actor above. Copy only closed
        # signed primitive context, never a caller-selected expectation.
        value = json.loads(result.commitment.canonical_json)
        expected = tuple(sorted((k, value[k]) for k in _EXPECTED - {"phase", "sequence"}))
        owner._expected = owner._expected_snapshot = expected
        b = owner._broker_binding
        _require(type(b) is BrokerBinding)
        values = (b.iid, b.listener, b.broker, b.channel, b.operation)
        owner._binding_values = values
        PreparedControlBinding.creator_current(binding)
        _require(CredentialBeginReceiver._completed_current(receiver) is result)
        PreparedControlBinding.creator_current(binding)
        _require(
            binding._refs_snapshot is refs
            and control._credential_binding_snapshot is binding
            and control._credential_binding is binding
            and control._signed_cursor is owner
            and control._signed_cursor_snapshot is owner
            and owner._binding is binding
            and owner._binding_snapshot is binding
            and owner._control is control
            and owner._control_snapshot is control
            and owner._buffer is buffer
            and owner._buffer_origin is buffer
            and len(buffer) == 0
            and owner._socket is sock
            and owner._loop is loop
            and owner._pins is pins
            and owner._pins_snapshot is pins
            and owner._broker_binding is broker_binding
            and owner._binding_values is values
            and owner._expected is expected
            and owner._expected_snapshot is expected
            and owner._end is end
            and owner._end_snapshot is end
            and owner._initialized is False
            and owner._started is False
            and owner._failed is False
            and owner._complete is False
        )
        owner._initialized = True
        return owner

    def __repr__(self):
        return "<CredentialControlCursor no-native-receipt context-redacted>"

    def _local(self):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding

        _require(type(self) is CredentialControlCursor and self._initialized is True)
        _require(
            type(self._binding) is PreparedControlBinding
            and self._binding is self._binding_snapshot
            and type(self._control) is BrokerCancellationOwner
            and self._control is self._control_snapshot
            and self._binding._control_snapshot is self._control
            and self._control._credential_binding_snapshot is self._binding
            and self._control._credential_binding is self._binding
            and self._control._signed_cursor is self
            and self._control._signed_cursor_snapshot is self
        )
        PreparedControlBinding._reader_local(self._binding_snapshot)
        _require(
            type(self._expected) is tuple
            and self._expected is self._expected_snapshot
            and len(self._expected) == len(_EXPECTED) - 2
            and all(
                type(row) is tuple
                and len(row) == 2
                and type(row[0]) is str
                and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                for row in self._expected
            )
            and {row[0] for row in self._expected} == _EXPECTED - {"phase", "sequence"}
            and type(self._pins) is tuple
            and self._pins is self._pins_snapshot
            and len(self._pins) == 2
            and all(type(v) is bytes and len(v) == 32 for v in self._pins)
            and type(self._end) is int
            and self._end is self._end_snapshot
            and self._end == self._binding._refs_snapshot[4].deadline_ns
        )
        _require(
            type(self._broker_binding) is BrokerBinding
            and all(
                type(v) is str
                for v in (
                    self._broker_binding.iid,
                    self._broker_binding.listener,
                    self._broker_binding.broker,
                    self._broker_binding.channel,
                    self._broker_binding.operation,
                )
            )
            and type(self._binding_values) is tuple
            and len(self._binding_values) == 5
            and all(type(v) is str for v in self._binding_values)
            and (
                self._broker_binding.iid,
                self._broker_binding.listener,
                self._broker_binding.broker,
                self._broker_binding.channel,
                self._broker_binding.operation,
            )
            == self._binding_values
            and self._pins
            == (self._binding._key_values_snapshot[4], self._binding._key_values_snapshot[3])
            and self._socket is self._binding._refs_snapshot[14]._socket_snapshot
            and self._loop is self._binding._loop
            and all(
                type(v) is bool
                for v in (
                    self._started,
                    self._complete,
                    self._failed,
                    self._read_intent,
                    self._io_unknown,
                )
            )
            and self._failed is False
            and self._complete is False
            and self._io_unknown is False
            and type(self._buffer) is bytearray
            and self._buffer is self._buffer_origin
            and type(self._buffer_values) is bytes
            and bytes(self._buffer) == self._buffer_values
            and type(self._target) is int
            and self._target is self._target_snapshot
            and type(self._consumed) is int
            and self._consumed is self._consumed_snapshot
            and 0 <= len(self._buffer) <= self._consumed <= self._target <= _LIMIT
        )
        if self._pending is None:
            _require(self._pending_snapshot is None and len(self._buffer) == self._consumed)
        else:
            _require(
                type(self._pending) is bytes
                and self._pending is self._pending_snapshot
                and len(self._buffer) + len(self._pending) == self._consumed
            )

    def _guard(self):
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_clock import NativeClockOwner
        from .presentation_control_binding import PreparedControlBinding

        CredentialControlCursor._local(self)
        binding = self._binding_snapshot
        PreparedControlBinding.reader_material_current(binding)
        CredentialControlCursor._local(self)
        refs = binding._refs_snapshot
        # This stage is first-frame-only, under the original work end. Remote
        # cleanup adoption is NOT implemented and cannot renew this read cap.
        before = CancellationBudget.inspect(refs[17])
        _require(before[0] == self._end and before[2] is None and before[3] is False)
        now = NativeClockOwner.sample(refs[13])
        CredentialControlCursor._local(self)
        PreparedControlBinding.reader_material_current(binding)
        CredentialControlCursor._local(self)
        _require(type(now) is int and 0 <= now < self._end)
        _require(CancellationBudget.inspect(refs[17]) == before)

    async def _take(self, target):
        import errno
        import os

        from .presentation_broker_cancel import _SOCKET_RECV
        from .presentation_broker_service import _SOCKET_FILENO, _SOCKET_TIMEOUT
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_readiness import SelectorReadiness

        part = None
        buffer = self._buffer_origin
        _require(type(buffer) is bytearray)
        try:
            CredentialControlCursor._guard(self)
            _require(
                type(target) is int
                and self._target <= target <= _LIMIT
                and self._pending is None
                and self._read_intent is False
            )
            self._target = self._target_snapshot = target
            while len(self._buffer_origin) < target:
                CredentialControlCursor._guard(self)
                _require(
                    self._buffer is buffer
                    and self._buffer_origin is buffer
                    and self._target is target
                    and self._target_snapshot is target
                )
                consumed = self._consumed_snapshot
                values = bytes(buffer)
                wanted = target - len(buffer)
                sock = self._socket
                refs = self._binding_snapshot._refs_snapshot
                fd, budget = refs[14]._fd, refs[17]
                state = CancellationBudget.inspect(budget)
                # SocketChannel's peer checks can run after its earlier mode
                # check. Recheck concrete nonblocking/timeout state last, then
                # only callback-free metadata/budget fences before recv.
                timeout = _SOCKET_TIMEOUT(sock)
                _require(
                    type(fd) is int
                    and _SOCKET_FILENO(sock) == fd
                    and os.get_blocking(fd) is False
                    and type(timeout) is float
                    and timeout == 0.0
                )
                CredentialControlCursor._local(self)
                _require(
                    self._socket is sock
                    and self._binding_snapshot._refs_snapshot is refs
                    and refs[14]._fd is fd
                    and refs[17] is budget
                    and CancellationBudget.inspect(budget) == state
                    and self._buffer is buffer
                    and self._buffer_origin is buffer
                    and self._target is target
                    and self._target_snapshot is target
                    and self._consumed is consumed
                    and self._consumed_snapshot is consumed
                    and self._pending is None
                    and self._read_intent is False
                )
                self._read_intent = True
                try:
                    part = _SOCKET_RECV(sock, wanted)
                except BlockingIOError as error:
                    _require(
                        type(error) is BlockingIOError
                        and type(error.errno) is int
                        and error.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
                    )
                    self._read_intent = False
                    CredentialControlCursor._guard(self)
                    waiter = SelectorReadiness.__new__(SelectorReadiness)
                    self._waiter = waiter
                    SelectorReadiness.__init__(waiter, self._socket)
                    await SelectorReadiness.wait(waiter, self._end)
                    _require(
                        self._waiter is waiter
                        and waiter._initialized is True
                        and waiter._attempted is True
                        and waiter._retired is True
                        and waiter._unknown is False
                    )
                    CredentialControlCursor._guard(self)
                    continue
                self._pending = self._pending_snapshot = part
                _require(type(part) is bytes and 0 <= len(part) <= wanted)
                self._last_read = (consumed, len(part))  # actual syscall count survives refusal
                _require(self._consumed is consumed and self._consumed_snapshot is consumed)
                committed = consumed + len(part)
                self._consumed = self._consumed_snapshot = committed
                CredentialControlCursor._guard(self)
                _require(
                    self._buffer is buffer
                    and self._buffer_origin is buffer
                    and self._target is target
                    and self._target_snapshot is target
                    and self._consumed is committed
                    and self._consumed_snapshot is committed
                    and self._pending is part
                    and self._pending_snapshot is part
                    and self._read_intent is True
                    and bytes(buffer) == values
                    and len(part) > 0
                )
                bytearray.extend(buffer, part)
                self._buffer_values = bytes(buffer)
                self._pending = self._pending_snapshot = None
                self._read_intent = False
                CredentialControlCursor._guard(self)
            _require(
                self._buffer is buffer
                and self._buffer_origin is buffer
                and self._target is target
                and self._target_snapshot is target
            )
            return bytes(buffer)
        finally:
            part = None

    async def run(self):

        original = self._buffer_origin
        _require(type(original) is bytearray)
        prefix = raw = framed = commitment = header = parsed = expected = None
        cancelled = failed = False
        try:
            CredentialControlCursor._guard(self)
            _require(self._started is False)
            self._started = True
            channel = self._binding_snapshot._refs_snapshot[14]
            _require(channel._reading is False)
            channel._reading = True
            prefix = await CredentialControlCursor._take(self, 8)
            raw = await CredentialControlCursor._take(self, 8 + payload_size(prefix))
            from .presentation_credential_codec import decode_record

            parsed = json.loads(decode_record(raw).canonical_json)
            # Read only the phase discriminator from the closed codec. It is not
            # a revocation hint; no native effect occurs before authentication.
            _require(parsed["family"] == "phase" and parsed["phase"] in ("GO", "CANCEL"))
            expected = dict(self._expected_snapshot, phase=parsed["phase"], sequence=1)
            commitment = check_commitment(
                raw, sender_public=self._pins[0], receiver_public=self._pins[1], expected=expected
            )
            CredentialControlCursor._guard(self)
            auth_end = len(raw)
            framed = await CredentialControlCursor._take(self, auth_end + 8)
            header_end = auth_end + 8 + header_size(framed[auth_end:])
            framed = await CredentialControlCursor._take(self, header_end)
            header = check_committed_header(
                commitment, framed[auth_end:], binding=self._broker_binding
            )
            _require(header.body_length == (0 if header.kind == "GO" else 16))
            CredentialControlCursor._guard(self)
            framed = await CredentialControlCursor._take(self, header_end + header.body_length)
            check_complete_frame(commitment, framed[auth_end:], binding=self._broker_binding)
            if header.kind == "CANCEL":
                from .presentation_cancel_budget import CancellationWindow

                # Validate the exact native wire shape without adopting its window.
                CancellationWindow.decode(framed[header_end:])
            # Reverify the exact retained raw record after all reads/callbacks.
            check_commitment(
                raw, sender_public=self._pins[0], receiver_public=self._pins[1], expected=expected
            )
            CredentialControlCursor._guard(self)
            _require(
                self._buffer_origin is original
                and self._buffer is original
                and bytes(original) == framed
            )
            self._raw, self._frame, self._header = raw, framed[auth_end:], header
            self._phase = header.kind
            self._complete = True
            return None  # no data object is accepted as native authority
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            prefix = raw = framed = commitment = header = parsed = expected = None
            if failed:
                self._failed = True
                # Conservative uncertainty retains original consumed counts and
                # read/readiness intent. No retry or borrowed-buffer cleanup.
                self._io_unknown = True
                bytearray.clear(original)
                self._buffer_values = b""
                self._pending = self._pending_snapshot = None
                self._raw = self._frame = self._header = self._phase = None
            if not failed:
                channel._reading = False
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_CREDENTIAL_CONTROL_READ_REFUSED") from None
