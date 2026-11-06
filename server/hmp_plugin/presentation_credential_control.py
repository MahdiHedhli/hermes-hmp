"""Signed control read facts on the original native controller allocation.

Source-only staging, not a working GO/CANCEL lifecycle. First-frame reading
alone grants no native effects. The explicit pre-GO CANCEL adoption joins that
original read to native grammar/budget/receipt and owned local park/stop only.
A dedicated original-service CANCEL validator is separate from reader IO;
Signed GO read receipts are separate from worker relay; resource admission and
production dispatch stay closed.
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
_CONTROL_READ_COMPLETE = object()


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
        owner._frame_index = 0
        owner._wire_before = 0
        owner._prior_completion = None
        owner._advanced = False
        owner._raw = owner._frame = owner._header = None
        owner._phase = None
        owner._release = None
        owner._completion = owner._completion_snapshot = None
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

    def _local(self, *, creator=False):
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
        _require(type(creator) is bool)
        if creator:
            PreparedControlBinding._creator_local(self._binding_snapshot)
        else:
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
        _require(
            type(self._frame_index) is int
            and self._frame_index in (0, 1)
            and type(self._wire_before) is int
            and self._wire_before + self._consumed <= 2 * _LIMIT
            and type(self._advanced) is bool
        )
        if self._frame_index == 0:
            _require(
                self._wire_before == 0
                and self._prior_completion is None
                and self._advanced is False
            )
        else:
            prior = self._prior_completion
            _require(
                type(prior) is tuple
                and len(prior) == 8
                and type(prior[0]) is bytes
                and type(prior[1]) is bytes
                and type(prior[6]) is str
                and prior[6] == "GO"
                and self._advanced is True
                and self._wire_before == len(prior[0]) + len(prior[1])
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
        _require(self._complete is False)
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
            sequence = self._frame_index + 1
            if sequence == 2:
                _require(parsed["phase"] == "CANCEL")
            expected = dict(self._expected_snapshot, phase=parsed["phase"], sequence=sequence)
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
            self._completion = self._completion_snapshot = (
                raw,
                self._frame,
                header,
                original,
                self._consumed_snapshot,
                self._target_snapshot,
                self._phase,
                self._end_snapshot,
            )
            self._release = _CONTROL_READ_COMPLETE
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

    async def read_after_go(self):
        """Same actual controller cursor, second CANCEL only; no cleanup-time reads yet."""
        from .presentation_broker_cancel import BrokerCancellationOwner

        CredentialControlCursor._local(self)
        _require(self._frame_index == 0 and self._advanced is False)
        control = self._control_snapshot
        _require(type(control) is BrokerCancellationOwner)
        phase = control._signed_go_snapshot
        _require(type(phase) is CredentialGoPhase and control._signed_go is phase)
        CredentialGoPhase._local(phase)
        completed = self._completion_snapshot
        CredentialControlCursor._completed_local(self, completed)
        _require(phase._completion is completed and phase._notified is True)
        self._advanced = True  # irreversible before allocating the second frame buffer
        self._prior_completion = completed
        self._wire_before = self._consumed_snapshot
        self._frame_index = 1
        self._buffer = self._buffer_origin = bytearray()
        self._buffer_values = b""
        self._target = self._target_snapshot = 0
        self._consumed = self._consumed_snapshot = 0
        self._pending = self._pending_snapshot = None
        self._raw = self._frame = self._header = self._phase = None
        self._release = None
        self._completion = self._completion_snapshot = None
        self._started = self._complete = False
        await CredentialControlCursor.run(self)

    def _completed_local(self, completion, *, creator=False):
        """Callback-free seal against held original completed cursor facts."""
        from .presentation_broker_codec import BrokerHeader

        CredentialControlCursor._local(self, creator=creator)
        _require(
            self._started is True
            and self._complete is True
            and self._release is _CONTROL_READ_COMPLETE
            and self._read_intent is False
            and self._pending is None
        )
        _require(
            type(completion) is tuple
            and len(completion) == 8
            and self._completion_snapshot is completion
            and self._completion is completion
            and type(completion[0]) is bytes
            and type(completion[1]) is bytes
            and type(completion[2]) is BrokerHeader
            and type(completion[3]) is bytearray
            and type(completion[4]) is int
            and type(completion[5]) is int
            and type(completion[6]) is str
            and type(completion[7]) is int
        )
        raw, frame, header, buffer, consumed, target, phase, end = completion
        _require(
            self._raw is raw
            and self._frame is frame
            and self._header is header
            and self._buffer_origin is buffer
            and self._buffer is buffer
            and self._consumed is consumed
            and self._consumed_snapshot is consumed
            and self._target is target
            and self._target_snapshot is target
            and consumed == target == len(raw) + len(frame)
            and bytes(buffer) == raw + frame
            and self._phase is phase
            and phase in ("GO", "CANCEL")
            and self._end is end
            and self._end_snapshot is end
        )

    def _completion_current(self, *, creator):
        """Original actor's checked local transfer, never a caller-supplied permit."""
        from .presentation_control_binding import PreparedControlBinding

        _require(type(self) is CredentialControlCursor and type(creator) is bool)
        completion = self._completion_snapshot
        CredentialControlCursor._completed_local(self, completion, creator=creator)
        raw, frame, _, _, _, _, phase, _ = completion
        if creator:
            PreparedControlBinding.creator_material_current(self._binding_snapshot)
        else:
            PreparedControlBinding.reader_material_current(self._binding_snapshot)
        CredentialControlCursor._completed_local(self, completion, creator=creator)
        commitment = check_commitment(
            raw,
            sender_public=self._pins[0],
            receiver_public=self._pins[1],
            expected=dict(self._expected_snapshot, phase=phase, sequence=self._frame_index + 1),
        )
        checked = check_complete_frame(commitment, frame, binding=self._broker_binding)
        _require(checked.kind == phase and checked.body_length == (0 if phase == "GO" else 16))
        if creator:
            PreparedControlBinding.creator_material_current(self._binding_snapshot)
        else:
            PreparedControlBinding.reader_material_current(self._binding_snapshot)
        CredentialControlCursor._completed_local(self, completion, creator=creator)
        return completion

    def completed_current(self):
        return CredentialControlCursor._completion_current(self, creator=False)

    def creator_completed_current(self):
        return CredentialControlCursor._completion_current(self, creator=True)


class CredentialCancelAdoption:
    """Original pre-GO signed CANCEL to native receipt/park, no resource authority."""

    @classmethod
    def retain(cls, control):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding

        _require(cls is CredentialCancelAdoption and type(control) is BrokerCancellationOwner)
        binding = control._credential_binding_snapshot
        _require(type(binding) is PreparedControlBinding)
        PreparedControlBinding.creator_current(binding)
        cursor = control._signed_cursor_snapshot
        _require(
            type(cursor) is CredentialControlCursor
            and control._signed_cursor is cursor
            and cursor._binding_snapshot is binding
            and cursor._control_snapshot is control
            and cursor._initialized is True
            and cursor._started is False
            and control._signed_cancel is None
            and control._signed_cancel_snapshot is None
        )
        owner = cls.__new__(cls)
        control._signed_cancel = control._signed_cancel_snapshot = owner
        owner._control = owner._control_snapshot = control
        owner._binding = owner._binding_snapshot = binding
        owner._cursor = owner._cursor_snapshot = cursor
        owner._refs = owner._refs_snapshot = binding._refs_snapshot
        owner._attempted = owner._complete = False
        owner._consume_attempted = owner._consume_complete = owner._consume_failed = False
        from .presentation_broker_cancel import _native_future_methods
        from .presentation_remote_cleanup import _FUTURE, _TaskAllocation

        allocation = control._allocation_snapshot
        cancel, park = control._cancel_allocation_snapshot, control._park_allocation_snapshot
        _require(
            type(allocation) is _TaskAllocation
            and allocation is binding._allocation
            and type(cancel) is tuple
            and len(cancel) == 1
            and type(park) is tuple
            and len(park) == 1
            and type(cancel[0]) is _FUTURE
            and type(park[0]) is _FUTURE
        )
        owner._notice_refs = owner._notice_refs_snapshot = (
            allocation,
            cancel[0],
            park[0],
            cancel,
            park,
            control._cancel_initialized_snapshot,
            control._park_initialized_snapshot,
            control._task_initialized_snapshot,
            control._scope_snapshot,
        )
        owner._native_receipt_origin = None
        CredentialCancelAdoption._notice_local(owner)
        _native_future_methods(cancel[0])
        _native_future_methods(park[0])
        return owner

    def __repr__(self):
        return "<CredentialCancelAdoption no-GO-authority context-redacted>"

    def _notice_local(self):
        """Original native Future/receipt metadata, with no callback-bearing IO."""
        from .presentation_broker_cancel import (
            _CANCEL_RECEIPT_MINT,
            _CancelReceipt,
            _native_future_methods,
        )
        from .presentation_broker_codec import BrokerFrame, BrokerHeader, _row
        from .presentation_cancel_budget import CancellationWindow
        from .presentation_remote_cleanup import _FUTURE, _TaskAllocation

        _require(type(self) is CredentialCancelAdoption)
        control = self._control_snapshot
        from .presentation_broker_cancel import BrokerCancellationOwner

        _require(type(control) is BrokerCancellationOwner and self._control is control)
        held = self._notice_refs_snapshot
        _require(
            type(held) is tuple
            and len(held) == 9
            and self._notice_refs is held
            and type(held[0]) is _TaskAllocation
            and type(held[1]) is _FUTURE
            and type(held[2]) is _FUTURE
            and type(held[3]) is tuple
            and len(held[3]) == 1
            and held[3][0] is held[1]
            and type(held[4]) is tuple
            and len(held[4]) == 1
            and held[4][0] is held[2]
            and all(type(v) is object for v in held[5:8])
            and type(held[8]) is tuple
            and len(held[8]) == 10
        )
        _require(
            control._allocation is held[0]
            and control._allocation_snapshot is held[0]
            and control._cancel_future is held[1]
            and control._cancel_future_snapshot is held[1]
            and control._park_future is held[2]
            and control._park_future_snapshot is held[2]
            and control._cancel_allocation is held[3]
            and control._cancel_allocation_snapshot is held[3]
            and control._park_allocation is held[4]
            and control._park_allocation_snapshot is held[4]
            and control._cancel_initialized is held[5]
            and control._cancel_initialized_snapshot is held[5]
            and control._park_initialized is held[6]
            and control._park_initialized_snapshot is held[6]
            and control._task_initialized is held[7]
            and control._task_initialized_snapshot is held[7]
            and control._scope is held[8]
            and control._scope_snapshot is held[8]
        )
        _native_future_methods(held[0].task)
        _native_future_methods(held[1])
        _native_future_methods(held[2])
        notice = self._native_receipt_origin
        if notice is None:
            _require(control._cancel_receipt is None and control._cancel_receipt_snapshot is None)
            return
        _require(
            type(notice) is _CancelReceipt
            and notice.mint is _CANCEL_RECEIPT_MINT
            and control._cancel_receipt is notice
            and control._cancel_receipt_snapshot is notice
            and notice.scope is held[8]
            and notice.allocation is held[0]
            and notice.future is held[1]
            and notice.park is held[2]
            and type(notice.frame) is BrokerFrame
            and type(notice.frame.header) is BrokerHeader
            and type(notice.frame.body) is bytes
            and notice.frame is control._frame
            and notice.frame is control._frame_snapshot
            and type(notice.window) is CancellationWindow
            and type(notice.timeout) is asyncio.Timeout
            and notice.timeout is control._timeout_snapshot
            and control._timeout is notice.timeout
            and type(notice.end) is int
            and type(control._park_end_snapshot) is int
            and control._park_end is control._park_end_snapshot
            and notice.end == control._park_end_snapshot
        )
        _row(notice.frame.header)
        _require(
            notice.frame.header.kind == "CANCEL"
            and notice.frame.header.sequence
            == (2 if control._go_receipt_snapshot is not None else 1)
            and notice.frame.header.version == 2
            and notice.frame.header.body_length == 16
            and len(notice.frame.body) == 16
            and CancellationWindow.encode(notice.window) == notice.frame.body
        )

    def _local(self, *, creator=False):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding

        _require(
            type(self) is CredentialCancelAdoption
            and type(self._control) is BrokerCancellationOwner
            and self._control is self._control_snapshot
            and type(self._binding) is PreparedControlBinding
            and self._binding is self._binding_snapshot
            and type(self._cursor) is CredentialControlCursor
            and self._cursor is self._cursor_snapshot
            and type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
            and self._binding._refs_snapshot is self._refs
            and self._control._signed_cancel is self
            and self._control._signed_cancel_snapshot is self
            and self._control._signed_cursor is self._cursor
            and self._control._signed_cursor_snapshot is self._cursor
            and self._cursor._binding_snapshot is self._binding
            and self._cursor._control_snapshot is self._control
            and type(self._attempted) is bool
            and type(self._complete) is bool
        )
        _require(type(creator) is bool)
        if creator:
            PreparedControlBinding._creator_local(self._binding_snapshot)
        else:
            PreparedControlBinding._reader_local(self._binding_snapshot)
        _require(
            all(
                type(v) is bool
                for v in (self._consume_attempted, self._consume_complete, self._consume_failed)
            )
        )
        phase = self._control_snapshot._signed_go_snapshot
        if phase is not None:
            _require(
                type(phase) is CredentialGoPhase and self._control_snapshot._signed_go is phase
            )
            CredentialGoPhase._local(phase)
        else:
            _require(
                self._control_snapshot._signed_go is None
                and self._control_snapshot._go_receipt_snapshot is None
            )
        CredentialCancelAdoption._notice_local(self)
        CredentialControlCursor._local(self._cursor_snapshot, creator=creator)
        if self._cursor_snapshot._complete is True:
            CredentialControlCursor._completed_local(
                self._cursor_snapshot, self._cursor_snapshot._completion_snapshot, creator=creator
            )

    def _current(self):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding

        CredentialCancelAdoption._local(self)
        binding, control, refs = self._binding_snapshot, self._control_snapshot, self._refs_snapshot
        PreparedControlBinding.reader_material_current(binding)
        CredentialCancelAdoption._local(self)
        BrokerCancellationOwner._guard(control, cleanup=True)
        CredentialCancelAdoption._local(self)
        _require(
            self._binding_snapshot is binding
            and self._control_snapshot is control
            and self._refs_snapshot is refs
            and control._failed is False
        )
        return refs

    def _completed_current(self, cursor, completed, refs):
        _require(CredentialCancelAdoption._current(self) is refs)
        _require(self._cursor is cursor and self._cursor_snapshot is cursor)
        CredentialControlCursor._completed_local(cursor, completed)

    async def run(self):
        from .presentation_broker_cancel import (
            _CANCEL_RECEIPT_MINT,
            BrokerCancellationOwner,
            _CancelReceipt,
        )
        from .presentation_broker_codec import BrokerFrame
        from .presentation_broker_lifecycle import OperationGrammar
        from .presentation_cancel_budget import CancellationBudget, CancellationWindow
        from .presentation_clock import NativeClockOwner
        from .presentation_remote_cleanup import _FUTURE

        _require(type(self) is CredentialCancelAdoption)
        control = self._control_snapshot
        _require(type(control) is BrokerCancellationOwner and self._control is control)
        failed = False
        try:
            refs = CredentialCancelAdoption._current(self)
            _require(self._attempted is False and self._complete is False)
            cursor = self._cursor_snapshot
            completed = CredentialControlCursor.completed_current(cursor)
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            _require(
                cursor._completion_snapshot is completed
                and cursor._phase == "CANCEL"
                and refs[18]._client_next == cursor._frame_index + 1
                and refs[18]._go is (cursor._frame_index == 1)
                and refs[18]._cancel is False
                and control._retired is False
            )
            raw, frame_bytes, header, _, _, _, _phase, work_end = completed
            # Derive the native frame from the authenticated bytes, not from a
            # caller-created BrokerFrame or mutable decoder object.
            from .presentation_broker_codec import decode_header

            end = 8 + header_size(frame_bytes[:8])
            native_header = decode_header(
                frame_bytes[:end], expected=cursor._broker_binding, expected_version=2
            )
            _require(
                native_header.kind == "CANCEL"
                and native_header.sequence == cursor._frame_index + 1
                and native_header.body_length == 16
            )
            body = frame_bytes[end:]
            window = CancellationWindow.decode(body)
            now = NativeClockOwner.sample(refs[13])
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            _require(
                type(now) is int
                and 0 <= now < work_end
                and cursor._completion_snapshot is completed
                and cursor._raw is raw
                and cursor._frame is frame_bytes
                and cursor._header is header
                and window.start_ns <= now
            )
            # Consume intent before the first native lifecycle/budget mutation.
            self._attempted = True
            BrokerCancellationOwner._local_cause(control)
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            frame = BrokerFrame(native_header, body)
            OperationGrammar.observe(refs[18], frame, sender="client")
            control._frame = control._frame_snapshot = frame
            control._frame_seal = control._frame_seal_snapshot = (frame, native_header, body)
            now = NativeClockOwner.cleanup_sample(refs[13])
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            CancellationBudget.inherit(refs[17], window, now)
            control._adopted = True
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            now = NativeClockOwner.cleanup_sample(refs[13])
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            _require(CancellationBudget.remaining_ns(refs[17], now) > 0)
            end = CancellationBudget.inspect(refs[17])[2]
            _require(type(end) is int and control._notice_attempted is False)
            control._timeout = control._timeout_snapshot = asyncio.timeout_at(end / 1e9)
            notice = _CancelReceipt(
                _CANCEL_RECEIPT_MINT,
                frame,
                window,
                control._scope_snapshot,
                control._allocation_snapshot,
                control._cancel_future_snapshot,
                control._park_future_snapshot,
                control._timeout_snapshot,
                end,
            )
            self._native_receipt_origin = notice
            control._cancel_receipt = control._cancel_receipt_snapshot = notice
            control._parked = True
            control._park_end = control._park_end_snapshot = end
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            control._notice_attempted = True
            _FUTURE.set_result(notice.future, notice)
            control._notice_completed = True
            self._complete = True
            CredentialCancelAdoption._completed_current(self, cursor, completed, refs)
            async with control._timeout_snapshot:
                await control._park_future_snapshot
            _require(False)  # no wake grants ACK or ordinary-work authority
        except asyncio.CancelledError:
            # Cancellation here is local ownership cleanup, not another remote
            # authentication phase. Key retirement cannot prevent it.
            if control._parked is True:
                try:
                    BrokerCancellationOwner._guard(control, cleanup=True)
                    _require(
                        control._failed is False
                        and control._io_unknown is False
                        and control._stop_intent_snapshot is not None
                        and control._notice_completed is True
                        and asyncio.current_task() is control._allocation_snapshot.task
                        and BrokerCancellationOwner.cleanup_remaining(control) > 0
                    )
                    control._stop_known = True
                    return control._frame_snapshot
                except BaseException:
                    control._io_unknown = True
            failed = True
            raise
        except BaseException:
            failed = True
            raise FrameError("BI1_CREDENTIAL_CANCEL_ADOPTION_REFUSED") from None
        finally:
            if failed:
                control._failed = True
                if self._attempted is True:
                    BrokerCancellationOwner._local_cause(control)
                if control._parked is True:
                    control._io_unknown = True

    def _creator_current(self, spine):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_broker_service import BrokerServiceSpine
        from .presentation_control_binding import PreparedControlBinding

        CredentialCancelAdoption._local(self, creator=True)
        refs, control, binding = self._refs_snapshot, self._control_snapshot, self._binding_snapshot
        _require(type(spine) is BrokerServiceSpine and spine is refs[0])
        PreparedControlBinding.creator_material_current(binding)
        CredentialCancelAdoption._local(self, creator=True)
        BrokerCancellationOwner._guard(control, cleanup=True)
        CredentialCancelAdoption._local(self, creator=True)
        _require(
            self._refs_snapshot is refs
            and self._control_snapshot is control
            and self._binding_snapshot is binding
            and control._failed is False
            and control._io_unknown is False
        )
        return refs

    def _consume_scope(self, spine):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_broker_service import BrokerServiceSpine, _Connection
        from .presentation_control_binding import PreparedControlBinding
        from .presentation_remote_cleanup import _TASK

        _require(
            type(self) is CredentialCancelAdoption
            and type(self._refs) is tuple
            and len(self._refs) == 19
            and self._refs is self._refs_snapshot
        )
        refs = self._refs_snapshot
        _require(
            type(spine) is BrokerServiceSpine
            and refs[0] is spine
            and type(refs[1]) is _Connection
            and type(refs[15]) is _TASK
            and refs[1].task is refs[15]
            and asyncio.current_task() is refs[15]
            and type(refs[16]) is asyncio.SelectorEventLoop
            and asyncio.get_running_loop() is refs[16]
            and type(self._binding) is PreparedControlBinding
            and self._binding is self._binding_snapshot
            and self._binding._creator is refs[15]
            and self._binding._refs_snapshot is refs
            and type(self._control) is BrokerCancellationOwner
            and self._control is self._control_snapshot
            and self._control._signed_cancel is self
            and self._control._signed_cancel_snapshot is self
        )
        return refs

    async def wait_notice(self, spine):
        """One original-service receipt consumption; no generic work/GO permission."""
        from .presentation_broker_cancel import (
            _CANCEL_RECEIPT_MINT,
            BrokerCancellationOwner,
            _CancelReceipt,
        )
        from .presentation_broker_codec import encode_frame
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_clock import NativeClockOwner
        from .presentation_remote_cleanup import _FUTURE, _TASK

        # Known wrong actor/scope cannot consume the original service attempt.
        refs = CredentialCancelAdoption._consume_scope(self, spine)
        _require(self._consume_attempted is False)
        control, cursor = self._control_snapshot, self._cursor_snapshot
        self._consume_attempted = True
        try:
            _require(CredentialCancelAdoption._creator_current(self, spine) is refs)
            _require(self._control_snapshot is control and self._cursor_snapshot is cursor)
            held = self._notice_refs_snapshot
            task, future = held[0].task, held[1]
            await asyncio.wait((task, future), return_when=asyncio.FIRST_COMPLETED)
            _require(CredentialCancelAdoption._creator_current(self, spine) is refs)
            _require(
                self._control_snapshot is control
                and self._cursor_snapshot is cursor
                and control._allocation_snapshot.task is task
                and control._cancel_future_snapshot is future
            )
            if not _FUTURE.done(future):
                _TASK.result(task)
                _require(False)
            completion = CredentialControlCursor.creator_completed_current(cursor)
            _require(CredentialCancelAdoption._creator_current(self, spine) is refs)
            _require(self._control_snapshot is control and self._cursor_snapshot is cursor)
            CredentialControlCursor._completed_local(cursor, completion, creator=True)
            notice = control._cancel_receipt_snapshot
            _require(
                type(notice) is _CancelReceipt
                and notice.mint is _CANCEL_RECEIPT_MINT
                and _FUTURE.result(future) is notice
                and control._notice_completed is True
                and self._complete is True
                and self._attempted is True
                and self._consume_failed is False
                and control._retired is True
                and control._stop_intent_snapshot is None
                and not _TASK.done(task)
                and _TASK.cancelling(task) == 0
                and _TASK._fut_waiter.__get__(task, _TASK) is control._park_future_snapshot
                and completion[6] == "CANCEL"
                and encode_frame(
                    control._scope_snapshot[1],
                    "CANCEL",
                    cursor._frame_index + 1,
                    notice.frame.body,
                    version=2,
                )
                == completion[1]
            )
            now = NativeClockOwner.cleanup_sample(refs[13])
            _require(CredentialCancelAdoption._creator_current(self, spine) is refs)
            _require(
                self._control_snapshot is control
                and self._cursor_snapshot is cursor
                and control._cancel_receipt_snapshot is notice
                and control._allocation_snapshot.task is task
                and control._cancel_future_snapshot is future
                and _FUTURE.result(future) is notice
                and not _TASK.done(task)
                and _TASK.cancelling(task) == 0
                and _TASK._fut_waiter.__get__(task, _TASK) is control._park_future_snapshot
            )
            CredentialControlCursor._completed_local(cursor, completion, creator=True)
            _require(CancellationBudget.remaining_ns(refs[17], now) > 0)
            self._consume_complete = True
            return notice.frame
        except BaseException:
            self._consume_failed = True
            BrokerCancellationOwner.refuse_notice(control)
            raise


class CredentialGoPhase:
    """Authenticated GO receipt plus same-task next CANCEL, never worker GO relay."""

    @classmethod
    def retain(cls, control):
        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_control_binding import PreparedControlBinding
        from .presentation_remote_cleanup import _FUTURE

        _require(cls is CredentialGoPhase and type(control) is BrokerCancellationOwner)
        binding = control._credential_binding_snapshot
        _require(type(binding) is PreparedControlBinding)
        PreparedControlBinding.creator_current(binding)
        adoption, cursor = control._signed_cancel_snapshot, control._signed_cursor_snapshot
        _require(
            type(adoption) is CredentialCancelAdoption
            and type(cursor) is CredentialControlCursor
            and control._signed_go is None
            and control._signed_go_snapshot is None
            and type(control._go_allocation_snapshot) is tuple
            and len(control._go_allocation_snapshot) == 1
            and type(control._go_allocation_snapshot[0]) is _FUTURE
        )
        owner = cls.__new__(cls)
        control._signed_go = control._signed_go_snapshot = owner
        owner._refs = owner._refs_snapshot = (
            control,
            adoption,
            cursor,
            binding,
            control._go_allocation_snapshot,
            control._go_future_snapshot,
            control._go_initialized_snapshot,
        )
        owner._attempted = owner._notified = False
        owner._receipt = owner._completion = None
        CredentialGoPhase._local(owner)
        return owner

    def __repr__(self):
        return "<CredentialGoPhase no-worker-relay context-redacted>"

    def _local(self):
        from .presentation_broker_cancel import (
            _GO_RECEIPT_MINT,
            BrokerCancellationOwner,
            _GoReceipt,
            _native_future_methods,
        )
        from .presentation_broker_codec import BrokerFrame, BrokerHeader, _row, encode_frame
        from .presentation_control_binding import PreparedControlBinding
        from .presentation_remote_cleanup import _FUTURE

        _require(
            type(self) is CredentialGoPhase
            and type(self._refs) is tuple
            and len(self._refs) == 7
            and self._refs is self._refs_snapshot
        )
        control, adoption, cursor, binding, allocation, future, initialized = self._refs
        _require(
            type(control) is BrokerCancellationOwner
            and type(adoption) is CredentialCancelAdoption
            and type(cursor) is CredentialControlCursor
            and type(binding) is PreparedControlBinding
            and type(allocation) is tuple
            and len(allocation) == 1
            and type(future) is _FUTURE
            and allocation[0] is future
            and type(initialized) is object
        )
        _require(
            control._signed_go is self
            and control._signed_go_snapshot is self
            and control._signed_cancel_snapshot is adoption
            and control._signed_cursor_snapshot is cursor
            and control._credential_binding_snapshot is binding
            and control._go_allocation is allocation
            and control._go_allocation_snapshot is allocation
            and control._go_future is future
            and control._go_future_snapshot is future
            and control._go_initialized is initialized
            and control._go_initialized_snapshot is initialized
            and type(self._attempted) is bool
            and type(self._notified) is bool
        )
        _require(
            type(cursor._frame_index) is int
            and cursor._frame_index in (0, 1)
            and type(cursor._wire_before) is int
            and 0 <= cursor._wire_before <= _LIMIT
            and type(cursor._advanced) is bool
        )
        _native_future_methods(future)
        receipt = self._receipt
        if receipt is None:
            _require(
                control._go_receipt is None
                and control._go_receipt_snapshot is None
                and self._notified is False
                and not _FUTURE.done(future)
            )
            return
        _require(
            type(receipt) is _GoReceipt
            and receipt.mint is _GO_RECEIPT_MINT
            and control._go_receipt is receipt
            and control._go_receipt_snapshot is receipt
            and type(receipt.scope) is tuple
            and len(receipt.scope) == 10
            and receipt.scope is binding._scope_snapshot
            and receipt.allocation is binding._allocation
            and receipt.future is future
            and type(receipt.frame) is BrokerFrame
            and type(receipt.frame.header) is BrokerHeader
            and type(receipt.frame.body) is bytes
            and receipt.frame.body == b""
        )
        _row(receipt.frame.header)
        _require(
            receipt.frame.header.kind == "GO"
            and receipt.frame.header.sequence == 1
            and receipt.frame.header.version == 2
            and receipt.frame.header.body_length == 0
        )
        completed = self._completion
        _require(
            type(completed) is tuple
            and len(completed) == 8
            and type(completed[0]) is bytes
            and type(completed[1]) is bytes
            and type(completed[3]) is bytearray
            and type(completed[4]) is int
            and type(completed[5]) is int
            and type(completed[6]) is str
            and type(completed[7]) is int
            and completed[4] == completed[5] == len(completed[0]) + len(completed[1])
            and bytes(completed[3]) == completed[0] + completed[1]
            and (
                cursor._completion_snapshot is completed
                if cursor._frame_index == 0
                else cursor._prior_completion is completed
            )
            and type(completed[6]) is str
            and completed[6] == "GO"
            and encode_frame(receipt.scope[1], "GO", 1, b"", version=2) == completed[1]
            and self._attempted is True
        )
        if self._notified:
            _require(_FUTURE.done(future) and _FUTURE.result(future) is receipt)
        else:
            _require(not _FUTURE.done(future))

    async def run(self):
        from .presentation_broker_cancel import (
            _GO_RECEIPT_MINT,
            BrokerCancellationOwner,
            _GoReceipt,
        )
        from .presentation_broker_codec import BrokerFrame, decode_header
        from .presentation_broker_lifecycle import OperationGrammar
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_clock import NativeClockOwner
        from .presentation_remote_cleanup import _FUTURE

        CredentialGoPhase._local(self)
        control, adoption, cursor, _binding, _, future, _ = self._refs_snapshot
        attempted = False
        try:
            refs = CredentialCancelAdoption._current(adoption)
            completion = CredentialControlCursor.completed_current(cursor)
            CredentialCancelAdoption._completed_current(adoption, cursor, completion, refs)
            _require(
                cursor._frame_index == 0
                and completion[6] == "GO"
                and self._attempted is False
                and self._receipt is None
                and refs[18]._ready is True
                and refs[18]._go is False
                and refs[18]._cancel is False
                and refs[18]._invalidated is False
                and refs[18]._client_next == 1
            )
            frame_bytes = completion[1]
            end = 8 + header_size(frame_bytes[:8])
            header = decode_header(
                frame_bytes[:end], expected=cursor._broker_binding, expected_version=2
            )
            _require(header.kind == "GO" and header.sequence == 1 and header.body_length == 0)
            now = NativeClockOwner.sample(refs[13])
            CredentialCancelAdoption._completed_current(adoption, cursor, completion, refs)
            _require(
                type(now) is int
                and 0 <= now < completion[7]
                and CancellationBudget.inspect(refs[17])[2:] == (None, False)
                and control._retired is False
            )
            self._attempted = attempted = True
            frame = BrokerFrame(header, b"")
            OperationGrammar.observe(refs[18], frame, sender="client")
            receipt = _GoReceipt(
                _GO_RECEIPT_MINT,
                frame,
                control._scope_snapshot,
                control._allocation_snapshot,
                future,
            )
            self._receipt, self._completion = receipt, completion
            control._go_receipt = control._go_receipt_snapshot = receipt
            CredentialCancelAdoption._completed_current(adoption, cursor, completion, refs)
            _FUTURE.set_result(future, receipt)
            self._notified = True
            CredentialCancelAdoption._completed_current(adoption, cursor, completion, refs)
            # Native grammar/receipt are read facts only. Generic go_receipt and
            # resource relay stay closed; no GO execution is authorized here.
            await CredentialControlCursor.read_after_go(cursor)
            return await CredentialCancelAdoption.run(adoption)
        finally:
            if attempted and control._stop_known is not True:
                BrokerCancellationOwner._local_cause(control)
