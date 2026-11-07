"""One-shot signed reader-stop notice component, not enabled cleanup IO authority.

Future ownership precedes initialization. Only the original uncancelled work task
may publish after actual correlated wake retirement. Original cleanup validates
current stop DATA only; no read/signer grant exists. Signed request still returns
False and normally cancels work.
"""
from __future__ import annotations

import asyncio
from typing import NamedTuple

from .presentation_cancel_budget import CancellationBudget
from .presentation_credential_cleanup_reservation import (
    SignedReadReservation,
    inspect_signed_reservation,
)
from .presentation_credential_result_body import (
    NativeResultBodyOwner,
    _BodyWait,
    _BodyWakeRetirement,
)
from .presentation_credential_result_read import (
    NativeResultEnvelopeReceiver,
    _ResultWaitHold,
    _ResultWakeRetirement,
)
from .presentation_credential_stream import CHUNK_LIMIT
from .presentation_credential_work import NativePhaseWorkOwner
from .presentation_jobs import FrameError
from .presentation_readiness import SelectorReadiness, _scheduler_safe, _WakeWaitRetirement
from .presentation_remote_cleanup import _FUTURE, _TASK, RemoteCleanupOwner, _initialize_future

_MINT = object()
_READER_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_READ_NOTICE_REFUSED")


class _SignedReadReady(NamedTuple):
    mint: object
    owner: object
    reservation: SignedReadReservation
    stop: object
    end: int

    def __repr__(self):
        return "<SignedReadReady original-stop-notice no-IO-or-release>"


class SignedReadNotice:
    @classmethod
    def retain(cls, gate):
        from .presentation_cleanup_reader import CleanupReadGate

        _require(cls is SignedReadNotice and type(gate) is CleanupReadGate)
        CleanupReadGate.guard(gate)
        r = gate._signed_reservation_origin
        inspect_signed_reservation(r, gate)
        _require(gate._signed_notice is None and gate._signed_notice_origin is None)
        owner = cls.__new__(cls)
        owner._gate = gate
        owner._reservation = r
        owner._future = owner._future_origin = None
        owner._future_allocation_origin = None
        owner._initialized = owner._init_attempted = False
        owner._attempted = owner._published = owner._failed = owner._unknown = False
        owner._fact = owner._fact_origin = owner._fact_allocation_origin = None
        owner._cursor = owner._cursor_origin = owner._cursor_allocation_origin = None
        # Retain every possibly partial native allocation before its first effect.
        gate._signed_notice = gate._signed_notice_origin = owner
        gate._signed_notice_allocation_origin = (gate, owner)
        failed = False
        try:
            future = _FUTURE.__new__(_FUTURE)
            owner._future = owner._future_origin = future
            owner._future_allocation_origin = (owner, future, r.capture.scope.write_scope.loop)
            owner._init_attempted = True
            _initialize_future(future, r.capture.scope.write_scope.loop)
            owner._initialized = True
            SignedReadNotice.inspect(owner, gate)
        except BaseException:
            failed = owner._failed = owner._unknown = True
            r.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_READ_NOTICE_INITIALIZATION_UNKNOWN") from None
        return owner

    def __repr__(self):
        return "<SignedReadNotice original-owned-future no-cleanup-permission>"

    def inspect(self, gate):
        """Retained shape only, including partial initialization; no ready credit."""
        from .presentation_cleanup_reader import CleanupReadGate

        _require(type(self) is SignedReadNotice and type(gate) is CleanupReadGate
                 and self._gate is gate
                 and gate._signed_notice is self and gate._signed_notice_origin is self
                 and type(gate._signed_notice_allocation_origin) is tuple
                 and len(gate._signed_notice_allocation_origin) == 2
                 and gate._signed_notice_allocation_origin[0] is gate
                 and gate._signed_notice_allocation_origin[1] is self
                 and type(self._reservation) is SignedReadReservation
                 and self._reservation is gate._signed_reservation_origin
                 and self._future is self._future_origin
                 and (self._future_origin is None or type(self._future_origin) is _FUTURE)
                 and all(type(v) is bool for v in (
                     self._initialized, self._init_attempted, self._attempted, self._published,
                     self._failed, self._unknown))
                 and self._fact is self._fact_origin)
        inspect_signed_reservation(self._reservation, gate)
        allocation = self._future_allocation_origin
        if allocation is None:
            _require(self._future_origin is None and self._init_attempted is False)
        else:
            _require(type(allocation) is tuple and len(allocation) == 3
                     and allocation[0] is self and type(allocation[1]) is _FUTURE
                     and self._future is allocation[1] and self._future_origin is allocation[1]
                     and allocation[2] is self._reservation.capture.scope.write_scope.loop)
        if self._initialized:
            _require(self._init_attempted is True and type(self._future_origin) is _FUTURE
                     and _FUTURE.get_loop(self._future_origin)
                     is self._reservation.capture.scope.write_scope.loop)
        else:
            _require(self._attempted is False and self._published is False)
        fact = self._fact_origin
        if fact is None:
            _require(self._fact_allocation_origin is None and self._published is False)
        else:
            _require(type(fact) is _SignedReadReady and fact.mint is _MINT
                     and fact.owner is self and fact.reservation is self._reservation
                     and type(fact.end) is int and 0 < fact.end <= self._reservation.end
                     and type(self._fact_allocation_origin) is tuple
                     and len(self._fact_allocation_origin) == 2
                     and self._fact_allocation_origin[0] is self
                     and self._fact_allocation_origin[1] is fact and self._attempted is True)
        cursor = self._cursor_origin
        if cursor is None:
            _require(self._cursor is None and self._cursor_allocation_origin is None)
        else:
            _require(type(cursor) is SignedStoppedCursor and self._cursor is cursor
                     and type(self._cursor_allocation_origin) is tuple
                     and len(self._cursor_allocation_origin) == 2
                     and self._cursor_allocation_origin[0] is self
                     and self._cursor_allocation_origin[1] is cursor)
        return self

    def _actor(self):
        from .presentation_cleanup_reader import CleanupReadGate

        _require(type(self) is SignedReadNotice)
        SignedReadNotice.inspect(self, self._gate)
        CleanupReadGate.guard(self._gate)
        r = self._reservation
        RemoteCleanupOwner._guard(r.capture.cleanup)
        _require(asyncio.current_task() is r.capture.work.task
                 and not _TASK.done(r.capture.work.task)
                 and _TASK.cancelling(r.capture.work.task) == 0)
        return r

    def _stop_metadata(self):
        """Original stopped-cursor DATA; neither actor is selected by this helper."""
        from .presentation_cleanup_reader import CleanupReadGate

        _require(type(self) is SignedReadNotice)
        SignedReadNotice.inspect(self, self._gate)
        CleanupReadGate.guard(self._gate)
        r = self._reservation
        RemoteCleanupOwner._guard(r.capture.cleanup)
        c, o = r.capture, r.capture.cleanup
        _require(self._initialized is True and self._failed is False and self._unknown is False
                 and o._intent is True and o._unknown is False and o._work_joined is False
                 and o._write_fact_snapshot is r.write and o._write_fact is r.write
                 and o._write_fact_consumed is False and o._cancel_write_attempted is False
                 and c.channel._writing is False and c.channel._reading is False
                 and o._barriers_snapshot.cause is r.cause and _FUTURE.done(r.cause)
                 and not _FUTURE.cancelled(r.cause) and _FUTURE.result(r.cause) is None
                 and o._refs_snapshot[8] is r.budget)
        if c.body is None:
            reader = c.receiver
            stop = reader._wake_release_origin
            _require(type(stop) is _ResultWakeRetirement and stop.capture is c
                     and type(stop.hold) is _ResultWaitHold
                     and type(stop.native) is _WakeWaitRetirement
                     and reader._wake_release is stop and stop.hold.waiter is r.wait.owner
                     and stop.native.scope is r.wait.scope and stop.native.future is r.wait.future
                     and reader._failed is True and reader._active is False)
            NativeResultEnvelopeReceiver._wake_stop_metadata(reader, stop)
        else:
            body = c.body.owner
            stop = body._wake_receipt_origin
            _require(type(stop) is _BodyWakeRetirement and stop.capture is c
                     and type(stop.wait) is _BodyWait
                     and type(stop.native) is _WakeWaitRetirement
                     and body._wake_receipt is stop and stop.wait.waiter is r.wait.owner
                     and stop.native.scope is r.wait.scope and stop.native.future is r.wait.future
                     and body._failed is True and body._active is False)
            NativeResultBodyOwner._wake_retirement_metadata(body, stop)
        RemoteCleanupOwner._quiescence_binding(o)
        _, _, end, failed = CancellationBudget.inspect(r.budget)
        _require(type(end) is int and 0 < end <= r.end and failed is False)
        return stop, end

    def _stop(self):
        SignedReadNotice._actor(self)
        return SignedReadNotice._stop_metadata(self)

    def _cleanup_actor(self):
        """Fixed original cleanup actor; never borrows the work actor's admission."""
        _require(type(self) is SignedReadNotice)
        SignedReadNotice.inspect(self, self._gate)
        r = self._reservation
        o = r.capture.cleanup
        RemoteCleanupOwner._guard(o)
        task = o._allocations_snapshot[0].task
        _require(asyncio.current_task() is task and not _TASK.done(task)
                 and _TASK.cancelling(task) == 0
                 and o._allocations_snapshot[1] is r.capture.work
                 and not _TASK.done(r.capture.work.task)
                 and _TASK.cancelling(r.capture.work.task) == 0)
        return r

    def _ready_metadata(self):
        """Actual delivered notice identity and stopped cursor; no IO permission."""
        stop, end = SignedReadNotice._stop_metadata(self)
        fact, future = self._fact_origin, self._future_origin
        _require(self._attempted is True and self._published is True
                 and self._failed is False and self._unknown is False
                 and type(fact) is _SignedReadReady and fact.stop is stop
                 and fact.reservation is self._reservation and end <= fact.end
                 and type(future) is _FUTURE and _FUTURE.done(future)
                 and not _FUTURE.cancelled(future) and _FUTURE.result(future) is fact)
        return fact, stop, end

    def current_stop_for_cleanup(self):
        """Original cleanup actor's current stop DATA, not a read/CANCEL grant.

        No native consumer/signer admits this as a running cleanup read. The
        original work task must still be live and uncancelled; completed work
        cannot be revived from a delivered historical Future.
        """
        r = SignedReadNotice._cleanup_actor(self)
        _require(self._initialized is True and self._published is True)
        failed = False
        try:
            fact, stop, end = SignedReadNotice._ready_metadata(self)
            SelectorReadiness._native(r.wait.owner, actor=False)
            handle, _ = SelectorReadiness._slots(r.wait.owner)
            _require(handle is None)
            SignedReadNotice._role_seal(self)
            _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
            SignedReadNotice._role_seal(self)
            _require(SignedReadNotice._cleanup_actor(self) is r)
            actual, current_stop, current_end = SignedReadNotice._ready_metadata(self)
            _require(actual is fact and current_stop is stop and current_end <= end)
            SignedReadNotice._role_seal(self)
            _require(SignedReadNotice._cleanup_actor(self) is r
                     and SignedReadNotice._ready_metadata(self)[0] is fact)
            return fact
        except BaseException:
            failed = self._failed = self._unknown = True
            r.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_READ_CLEANUP_NOTICE_UNKNOWN") from None

    def _role_seal(self):
        """Complete callback-free retained role DATA seal, no work authority revival."""
        SignedReadNotice.inspect(self, self._gate)
        r = self._reservation
        b = r.capture.scope.write_scope
        producer = b.producer
        _require(type(producer) is NativePhaseWorkOwner and type(b.refs) is tuple
                 and len(b.refs) == 12 and producer._refs is b.refs
                 and producer._refs_snapshot is b.refs)
        # This reference/type/snapshot validator performs no FD or clock IO and
        # grants no live work policy. It includes generation/process/boot/files,
        # not just the key-ready flag or public-key pins.
        material = NativePhaseWorkOwner._retained_material(producer)
        _require(type(material) is tuple and len(material) == 4
                 and material[0] is r.capture.cleanup._remote_snapshot
                 and material[2] is r.capture.channel and material[3] is b.refs[8])
        return r

    def current_stop_for_reader(self):
        """Fixed original reader's post-notification cursor currentness check.

        This is the pre-admission check, not permission to recv or register a
        fresh interest. The actual delivered notice, stopped cursor and original
        work actor must remain joined after native/clock callbacks. A future
        reader owner must separately retain its exact framing/digest allocation.
        """
        r = SignedReadNotice._actor(self)
        _require(self._initialized is True and self._published is True)
        failed = False
        try:
            fact, stop, end = SignedReadNotice._ready_metadata(self)
            current_stop, current_end = SignedReadNotice._current(self)
            _require(current_stop is stop and current_end <= end)
            # _current samples native selector/FD and the original clock. Seal
            # the delivered Future/fact again, rather than accepting publication
            # history as current admission after those callbacks.
            actual, after_stop, after_end = SignedReadNotice._ready_metadata(self)
            _require(actual is fact and after_stop is stop and after_end <= current_end)
            SignedReadNotice._role_seal(self)
            _require(SignedReadNotice._actor(self) is r
                     and SignedReadNotice._ready_metadata(self)[0] is fact)
            return fact
        except BaseException:
            failed = self._failed = self._unknown = True
            r.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_READER_STOP_CURRENTNESS_UNKNOWN") from None

    def _current(self):
        stop, end = SignedReadNotice._stop(self)
        r = self._reservation
        SelectorReadiness._native(r.wait.owner)
        handle, _ = SelectorReadiness._slots(r.wait.owner)
        _require(handle is None)
        _require(NativePhaseWorkOwner._retained_material(r.capture.scope.write_scope.producer)[0]
                 is r.capture.cleanup._remote_snapshot)
        _require(RemoteCleanupOwner._remaining(r.capture.cleanup) > 0)
        SignedReadNotice._role_seal(self)
        after, current_end = SignedReadNotice._stop(self)
        _require(after is stop and current_end <= end)
        SignedReadNotice._role_seal(self)
        return stop, current_end

    @staticmethod
    def _deliver(future, fact):
        _FUTURE.set_result(future, fact)

    def publish(self):
        r = SignedReadNotice._actor(self)  # wrong task cannot consume the original attempt
        _require(self._attempted is False)
        self._attempted = True
        failed = False
        try:
            stop, end = SignedReadNotice._current(self)
            future = self._future_origin
            _require(not _FUTURE.done(future))
            fact = _SignedReadReady(_MINT, self, r, stop, end)
            self._fact = self._fact_origin = fact
            self._fact_allocation_origin = (self, fact)
            from .presentation_broker_cancel import _native_future_methods
            _native_future_methods(future)
            _scheduler_safe(r.capture.scope.write_scope.loop)
            current_stop, current_end = SignedReadNotice._current(self)
            _require(current_stop is stop and current_end <= end)
            # Final dispatch checks after native currentness callbacks, then pure seals.
            _native_future_methods(future)
            _scheduler_safe(r.capture.scope.write_scope.loop)
            _require(SignedReadNotice._actor(self) is r
                     and SignedReadNotice._stop(self)[0] is stop
                     and SignedReadNotice._role_seal(self) is r
                     and self._fact_origin is fact and not _FUTURE.done(future)
                     and self._future is future and self._future_origin is future
                     and self._published is False and self._failed is False)
            self._published = True  # intent precedes possibly ambiguous native notification
            SignedReadNotice._deliver(future, fact)
            return True
        except BaseException:
            failed = self._failed = self._unknown = True
            r.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_READ_NOTICE_PUBLICATION_UNKNOWN") from None


class SignedStoppedCursor:
    """Original stopped cursor/parser binding; not native receive permission.

    Acquisition is one attempt after delivered notice, on the original work
    task. It retains only framing bytes, or the SAME original partial-body
    digest. This component exposes no feed, registration or recv operation.
    """

    @classmethod
    def retain(cls, notice):
        from .presentation_credential_codec import payload_size
        from .presentation_credential_stream import SignedCleanupAuthPrefix, SignedResultDiscard

        _require(cls is SignedStoppedCursor and type(notice) is SignedReadNotice)
        SignedReadNotice._actor(notice)
        fact = SignedReadNotice.current_stop_for_reader(notice)
        _require(notice._cursor is None and notice._cursor_origin is None
                 and notice._cursor_allocation_origin is None)
        owner = cls.__new__(cls)
        owner._notice = owner._notice_origin = notice
        owner._fact = owner._fact_origin = fact
        owner._reader = owner._reader_origin = owner._reader_allocation_origin = None
        owner._parser = owner._parser_origin = None
        owner._parser_allocation_origin = None
        owner._parser_state_allocation_origin = None
        owner._outer = owner._outer_origin = None
        owner._parser_state = owner._parser_state_origin = None
        owner._initialized = owner._failed = False
        # A partial parser allocation remains attributable even if construction
        # or the final currentness boundary refuses. No second acquisition.
        notice._cursor = notice._cursor_origin = owner
        notice._cursor_allocation_origin = (notice, owner)
        failed = False
        try:
            c = fact.reservation.capture
            prefix = c.envelope.values
            if c.body is None:
                end = 8 + payload_size(prefix[:8]) if len(prefix) >= 8 else len(prefix)
                owner._outer = owner._outer_origin = prefix[end:]
                parser = SignedCleanupAuthPrefix.__new__(SignedCleanupAuthPrefix)
                owner._parser = owner._parser_origin = parser
                owner._parser_allocation_origin = (owner, parser, c)
                SignedCleanupAuthPrefix.__init__(
                    parser, prefix[:end], sender_public=c.scope.pins[0],
                    receiver_public=c.scope.pins[1],
                    expected_context={k: v for k, v in c.scope.expected if k != "phase"})
                owner._parser_state = owner._parser_state_origin = (
                    parser._buffer_origin, bytes(parser._buffer_origin),
                    parser._target_origin, parser._header_done_origin)
            else:
                owner._outer = owner._outer_origin = b""
                parser = SignedResultDiscard.__new__(SignedResultDiscard)
                owner._parser = owner._parser_origin = parser
                owner._parser_allocation_origin = (owner, parser, c)
                SignedResultDiscard.__init__(
                    parser, prefix, sender_public=c.scope.pins[0],
                    receiver_public=c.scope.pins[1], expected=dict(c.scope.expected),
                    binding=c.scope.write_scope.intent.binding,
                    stream=c.body.allocation[1])
                owner._parser_state = owner._parser_state_origin = (
                    parser._stream_origin, c.body.allocation[2], c.body.received,
                    c.body.committed, c.body.hash_value)
            owner._parser_state_allocation_origin = (owner, parser, owner._parser_state_origin)
            owner._initialized = True
            SignedStoppedCursor.current(owner)
            return owner
        except BaseException:
            failed = owner._failed = notice._failed = notice._unknown = True
            fact.reservation.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_STOPPED_CURSOR_ACQUISITION_UNKNOWN") from None

    def __repr__(self):
        return "<SignedStoppedCursor original-parser-binding no-recv-permission>"

    def _metadata(self):
        from .presentation_credential_stream import (
            CommittedFrameDigest,
            SignedCleanupAuthPrefix,
            SignedResultDiscard,
        )

        _require(type(self) is SignedStoppedCursor and self._initialized is True
                 and self._failed is False
                 and type(self._notice) is SignedReadNotice
                 and self._notice is self._notice_origin
                 and type(self._fact) is _SignedReadReady and self._fact is self._fact_origin
                 and self._fact.owner is self._notice
                 and self._notice._cursor_origin is self and self._notice._cursor is self
                 and self._notice._fact_origin is self._fact
                 and self._parser is self._parser_origin
                 and type(self._outer) is bytes and self._outer is self._outer_origin
                 and type(self._parser_state) is tuple
                 and self._parser_state is self._parser_state_origin)
        c = self._fact.reservation.capture
        parser, held = self._parser_origin, self._parser_state_origin
        allocation = self._parser_allocation_origin
        state_allocation = self._parser_state_allocation_origin
        _require(type(allocation) is tuple and len(allocation) == 3
                 and allocation[0] is self and allocation[1] is parser and allocation[2] is c
                 and type(state_allocation) is tuple and len(state_allocation) == 3
                 and state_allocation[0] is self and state_allocation[1] is parser
                 and state_allocation[2] is held)
        SignedReadNotice.inspect(self._notice, c.gate)
        reader = self._reader_origin
        if reader is None:
            _require(self._reader is None and self._reader_allocation_origin is None)
        else:
            _require(type(reader) is SignedCleanupReader and self._reader is reader
                     and type(self._reader_allocation_origin) is tuple
                     and len(self._reader_allocation_origin) == 2
                     and self._reader_allocation_origin[0] is self
                     and self._reader_allocation_origin[1] is reader)
        if c.body is None:
            _require(type(parser) is SignedCleanupAuthPrefix and len(held) == 4
                     and type(held[0]) is bytearray and type(held[1]) is bytes
                     and type(held[2]) is int and type(held[3]) is bool)
            SignedCleanupAuthPrefix._guard(parser)
            _require(type(c.scope.pins) is tuple and len(c.scope.pins) == 2
                     and all(type(v) is bytes and len(v) == 32 for v in c.scope.pins)
                     and type(c.scope.expected) is tuple
                     and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                             and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns")
                                                 else str) for row in c.scope.expected))
            prefix = c.envelope.values
            _require(parser._buffer_origin is held[0]
                     and bytes(parser._buffer_origin) == held[1]
                     and parser._target_origin is held[2]
                     and parser._header_done_origin is held[3]
                     and held[1] + self._outer_origin == prefix
                     and parser._pins_origin is parser._pins
                     and parser._pins == c.scope.pins
                     and parser._expected == tuple((k, v) for k, v in c.scope.expected
                                                   if k != "phase"))
        else:
            _require(type(parser) is SignedResultDiscard and len(held) == 5
                     and type(held[0]) is CommittedFrameDigest
                     and type(held[2]) is int and type(held[3]) is int
                     and type(held[4]) is str and self._outer_origin == b"")
            SignedResultDiscard._guard(parser)
            _require(parser._stage == "body" and parser._stream_origin is held[0]
                     and parser._binding is c.scope.write_scope.intent.binding
                     and parser._binding_origin is c.scope.write_scope.intent.binding
                     and held[0]._binding is c.scope.write_scope.intent.binding
                     and held[0]._binding_origin is c.scope.write_scope.intent.binding
                     and held[0] is c.body.allocation[1]
                     and held[1] is c.body.allocation[2]
                     and held[2] == c.body.received and held[3] == c.body.committed
                     and held[4] == c.body.hash_value
                     and held[0]._received is c.body.committed
                     and held[0]._received_snapshot is c.body.committed)
        return self._fact

    def current(self):
        _require(type(self) is SignedStoppedCursor
                 and type(self._notice_origin) is SignedReadNotice)
        notice = self._notice_origin
        reservation = SignedReadNotice._actor(notice)  # fixed original actor
        failed = False
        try:
            fact = SignedStoppedCursor._metadata(self)
            _require(SignedReadNotice.current_stop_for_reader(notice) is fact)
            _require(SignedStoppedCursor._metadata(self) is fact)
            return self
        except BaseException:
            failed = self._failed = notice._failed = notice._unknown = True
            reservation.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_STOPPED_CURSOR_CURRENTNESS_UNKNOWN") from None


class _IdleReaderAdmission(NamedTuple):
    mint: object
    owner: object
    scope: tuple

    def __repr__(self):
        return "<IdleReaderAdmission original-bound-reader no-native-IO-or-release>"


class SignedCleanupReader:
    """One-shot idle admission of the original bound reader, before native IO.

    This preserves an explicit owner for later native receive qualification.
    Neither this fact nor its count/end is a recv, registration or signer permit.
    No parser advances here; future IO must transfer/track original digest
    progress explicitly rather than weakening the stopped-owner validators.
    """

    @classmethod
    def retain(cls, cursor):
        from .presentation_credential_stream import SignedCleanupAuthPrefix, SignedResultDiscard

        _require(cls is SignedCleanupReader and type(cursor) is SignedStoppedCursor)
        _require(type(cursor._notice_origin) is SignedReadNotice
                 and cursor._notice is cursor._notice_origin
                 and cursor._initialized is True and cursor._failed is False
                 and cursor._notice_origin._cursor is cursor
                 and cursor._notice_origin._cursor_origin is cursor)
        original_notice = cursor._notice_origin
        original_reservation = SignedReadNotice._actor(original_notice)
        _require(cursor._reader is None and cursor._reader_origin is None
                 and cursor._reader_allocation_origin is None)
        owner = cls.__new__(cls)
        owner._cursor = owner._cursor_origin = cursor
        owner._cursor_allocation_origin = (owner, cursor)
        owner._scope = owner._scope_origin = owner._scope_allocation_origin = None
        owner._fact = owner._fact_origin = owner._fact_allocation_origin = None
        owner._attempted = True
        owner._admitted = owner._failed = False
        # Keep partial acquisition before parser/native/clock checks; no retry.
        cursor._reader = cursor._reader_origin = owner
        cursor._reader_allocation_origin = (cursor, owner)
        failed = False
        try:
            SignedStoppedCursor.current(cursor)
            stop = cursor._fact_origin
            r, parser = stop.reservation, cursor._parser_origin
            if r.capture.body is None:
                count = SignedCleanupAuthPrefix.needed.fget(parser)
            else:
                count = SignedResultDiscard.needed.fget(parser)
            _, _, end, budget_failed = CancellationBudget.inspect(r.budget)
            _require(type(count) is int and 0 <= count <= CHUNK_LIMIT
                     and type(end) is int and 0 < end <= r.end and budget_failed is False)
            owner._scope = owner._scope_origin = (stop, parser, count, r.budget, end)
            owner._scope_allocation_origin = (owner, owner._scope_origin)
            SignedCleanupReader._initial_current(owner)
            fact = _IdleReaderAdmission(_READER_MINT, owner, owner._scope_origin)
            owner._fact = owner._fact_origin = fact
            owner._fact_allocation_origin = (owner, fact)
            SignedCleanupReader._initial_current(owner)
            owner._admitted = True
            return owner
        except BaseException:
            failed = owner._failed = cursor._failed = True
            original_notice._failed = original_notice._unknown = True
            original_reservation.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_IDLE_READER_ADMISSION_UNKNOWN") from None

    def __repr__(self):
        return "<SignedCleanupReader original-idle-admission no-native-IO>"

    def _metadata(self):
        _require(type(self) is SignedCleanupReader and self._failed is False
                 and self._attempted is True and type(self._admitted) is bool
                 and type(self._cursor) is SignedStoppedCursor
                 and self._cursor is self._cursor_origin
                 and type(self._cursor_allocation_origin) is tuple
                 and len(self._cursor_allocation_origin) == 2
                 and self._cursor_allocation_origin[0] is self
                 and self._cursor_allocation_origin[1] is self._cursor
                 and self._cursor._reader is self and self._cursor._reader_origin is self
                 and type(self._cursor._reader_allocation_origin) is tuple
                 and len(self._cursor._reader_allocation_origin) == 2
                 and self._cursor._reader_allocation_origin[0] is self._cursor
                 and self._cursor._reader_allocation_origin[1] is self
                 and type(self._scope) is tuple and self._scope is self._scope_origin
                 and len(self._scope) == 5
                 and type(self._scope_allocation_origin) is tuple
                 and len(self._scope_allocation_origin) == 2
                 and self._scope_allocation_origin[0] is self
                 and self._scope_allocation_origin[1] is self._scope)
        stop, parser, count, budget, end = self._scope_origin
        _require(type(stop) is _SignedReadReady and stop is self._cursor._fact_origin
                 and type(stop.reservation) is SignedReadReservation
                 and type(stop.reservation.end) is int
                 and type(count) is int and 0 <= count <= CHUNK_LIMIT
                 and type(end) is int and 0 < end <= stop.reservation.end
                 and type(self._cursor._parser_allocation_origin) is tuple
                 and len(self._cursor._parser_allocation_origin) == 3
                 and self._cursor._parser_allocation_origin[0] is self._cursor
                 and parser is self._cursor._parser_allocation_origin[1]
                 and budget is stop.reservation.budget)
        fact, cell = self._fact_origin, self._fact_allocation_origin
        _require(self._fact is fact)
        if fact is None:
            _require(cell is None and self._admitted is False)
        else:
            _require(type(fact) is _IdleReaderAdmission and fact.mint is _READER_MINT
                     and fact.owner is self and fact.scope is self._scope_origin
                     and type(cell) is tuple and len(cell) == 2
                     and cell[0] is self and cell[1] is fact)
        return self._scope_origin

    def _cursor_current(self):
        scope = SignedCleanupReader._metadata(self)
        cursor = self._cursor_origin
        _require(SignedStoppedCursor.current(cursor) is cursor)
        _require(SignedCleanupReader._metadata(self) is scope)
        stop, parser, count, budget, end = scope
        # Pure primitive joins AFTER original selector/FD/clock callbacks. Do not
        # invoke a caller-selected needed property or adopt changed parser state.
        if stop.reservation.capture.body is None:
            _require(type(parser._target_origin) is int
                     and type(parser._buffer_origin) is bytearray
                     and parser._target_origin - len(parser._buffer_origin) == count)
        else:
            stream = parser._stream_origin
            _require(type(stream._body_length) is int and type(stream._received) is int
                     and min(CHUNK_LIMIT, stream._body_length - stream._received) == count)
        _, _, current_end, failed = CancellationBudget.inspect(budget)
        _require(type(current_end) is int and 0 < current_end <= end and failed is False
                 and SignedCleanupReader._metadata(self) is scope)
        return scope

    def _initial_current(self):
        _require(type(self) is SignedCleanupReader and self._admitted is False
                 and type(self._cursor_origin) is SignedStoppedCursor)
        SignedReadNotice._actor(self._cursor_origin._notice_origin)
        return SignedCleanupReader._cursor_current(self)

    def current_idle(self):
        _require(type(self) is SignedCleanupReader
                 and type(self._cursor_origin) is SignedStoppedCursor)
        cursor = self._cursor_origin
        notice = cursor._notice_origin
        reservation = SignedReadNotice._actor(notice)  # wrong actor cannot poison admission
        _require(self._admitted is True)
        failed = False
        try:
            SignedCleanupReader._cursor_current(self)
            return self._fact_origin
        except BaseException:
            failed = self._failed = cursor._failed = True
            notice._failed = notice._unknown = True
            reservation.capture.cleanup._unknown = True
        if failed:
            raise FrameError("BI1_SIGNED_IDLE_READER_CURRENTNESS_UNKNOWN") from None
