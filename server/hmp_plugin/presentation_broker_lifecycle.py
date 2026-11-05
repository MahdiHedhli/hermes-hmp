"""Source-only broker grammar/replay state, never authority or custody receipts.

The future transport must authenticate its endpoint, record outgoing intents
before writes/awaits, and preserve the original native deadline/authorization.
No result here proves a child closed or permits publication/GO/slot release.
"""

from __future__ import annotations

import secrets
import threading
from enum import Enum

from .presentation_broker_codec import BrokerBinding, BrokerFrame, BrokerHeader, _binding, _row
from .presentation_jobs import FrameError

_SERIAL_MAX = (1 << 63) - 1
_WINDOW_BITS = 64
_WINDOW_MASK = (1 << _WINDOW_BITS) - 1


def _fail() -> None:
    raise FrameError("BI1_BROKER_LIFECYCLE_REFUSED")


def operation_id(serial: int) -> str:
    """Gateway correlation generation, not a capability. Serial must never wrap."""
    if type(serial) is not int or not 1 <= serial <= _SERIAL_MAX:
        _fail()
    suffix = secrets.token_hex(24)
    if (
        type(suffix) is not str
        or len(suffix) != 48
        or any(c not in "0123456789abcdef" for c in suffix)
    ):
        _fail()
    return f"{serial:016x}{suffix}"


def _serial(operation: str) -> int:
    value = int(operation[:16], 16)
    if not 1 <= value <= _SERIAL_MAX:
        _fail()
    return value


class ReplayWindow:
    """One retained listener scope; construction is NOT permission to reset history.

    Service enrollment/replacement and resource admission are unimplemented gates.
    Consume before capacity decisions/spawn; terminal ACK never alters this window.
    """

    def __init__(self, scope: BrokerBinding):
        _binding(scope)
        self._scope = (scope.iid, scope.listener, scope.broker)
        self._scope_snapshot = self._scope
        self._poisoned = False
        self._high = 0
        self._seen = 0
        self._lock = threading.Lock()

    def consume(self, binding: BrokerBinding) -> None:
        if not self._lock.acquire(blocking=False):
            _fail()
        try:
            if self._poisoned or self._scope is not self._scope_snapshot:
                self._poisoned = True
                _fail()
            _binding(binding)
            if (binding.iid, binding.listener, binding.broker) != self._scope:
                _fail()
            serial = _serial(binding.operation)
            if serial > self._high:
                distance = serial - self._high
                self._seen = (
                    0 if distance >= _WINDOW_BITS else self._seen << distance
                ) & _WINDOW_MASK
                self._high = serial
                self._seen |= 1
                return
            age = self._high - serial
            if age >= _WINDOW_BITS or self._seen & (1 << age):
                _fail()
            self._seen |= 1 << age
        finally:
            self._lock.release()


class MessageDisposition(Enum):
    CONTROL = "control"
    RESULT_CANDIDATE = "result_candidate"
    RESULT_DISCARDED = "result_discarded"
    ACK_REQUEST = "ack_request"
    STATUS_PENDING = "status_pending"
    STATUS_UNKNOWN = "status_unknown"


class OperationGrammar:
    """One connection's role-aware message grammar, not an execution owner.

    Call observe for outgoing frames BEFORE possibly partial writes, and for
    incoming frames only through the eventual qualified endpoint/decoder. Clock,
    native freshness, body validation, global ACK and actual cleanup live outside.
    """

    def __init__(self, binding: BrokerBinding, *, role: str, mode: str = "operation",
                 protocol_version: int = 1):
        _binding(binding)
        if type(role) is not str or role not in ("gateway", "broker"):
            _fail()
        if type(mode) is not str or mode not in ("operation", "status"):
            _fail()
        if (type(protocol_version) is not int or protocol_version not in (1, 2)
                or (protocol_version == 2 and mode != "operation")):
            _fail()
        self._version = self._version_snapshot = protocol_version
        _serial(binding.operation)
        self._binding = binding
        self._role = role
        self._mode = mode
        self._binding_reference = binding
        self._binding_values = (
            binding.iid,
            binding.listener,
            binding.broker,
            binding.channel,
            binding.operation,
        )
        self._role_snapshot, self._mode_snapshot = role, mode
        self._client_next = 0
        self._broker_next = 0
        self._begun = False
        self._ready = False
        self._go = False
        self._cancel = False
        self._terminal_message: str | None = None
        self._acked_message = False
        self._invalidated = False
        self._failed = False
        self._lock = threading.Lock()

    def _configured(self) -> bool:
        if type(self._binding) is not BrokerBinding or self._binding is not self._binding_reference:
            return False
        try:
            values = (
                self._binding.iid,
                self._binding.listener,
                self._binding.broker,
                self._binding.channel,
                self._binding.operation,
            )
        except AttributeError:
            return False
        return (
            all(type(value) is str for value in values)
            and type(self._role) is str and type(self._mode) is str
            and type(self._binding_values) is tuple and len(self._binding_values) == 5
            and all(type(value) is str for value in self._binding_values)
            and type(self._role_snapshot) is str and type(self._mode_snapshot) is str
            and type(self._client_next) is int and 0 <= self._client_next <= _SERIAL_MAX + 1
            and type(self._broker_next) is int and 0 <= self._broker_next <= _SERIAL_MAX + 1
            and all(type(v) is bool for v in (self._begun, self._ready, self._go, self._cancel,
                                             self._acked_message, self._invalidated, self._failed))
            and (self._terminal_message is None or (type(self._terminal_message) is str
                 and self._terminal_message in ("RESULT", "CLOSED", "PENDING", "UNKNOWN")))
            and type(self._version) is int and self._version in (1, 2)
            and self._version is self._version_snapshot
            and (self._version != 2 or self._mode == "operation")
            and values == self._binding_values
            and type(self._role) is str and self._role in ("gateway", "broker")
            and self._role == self._role_snapshot
            and type(self._mode) is str and self._mode in ("operation", "status")
            and self._mode == self._mode_snapshot
        )

    @property
    def candidate_message(self) -> bool:
        """Only a message candidate: never native authorization or custody proof."""
        if not self._configured():
            self._failed = True
            return False
        return (
            self._role == "gateway"
            and self._terminal_message == "RESULT"
            and not self._invalidated
            and not self._failed
        )

    def invalidate(self) -> None:
        """Sticky publication/GO fence before cancellation/deadline/scope handoff."""
        self._invalidated = True

    def observe(self, frame: BrokerFrame, *, sender: str) -> MessageDisposition:
        if not self._lock.acquire(blocking=False):
            self._failed = True
            _fail()
        try:
            if not self._configured() or self._failed or self._acked_message:
                _fail()
            if type(frame) is not BrokerFrame or type(frame.header) is not BrokerHeader:
                _fail()
            _row(frame.header)
            if (
                type(frame.body) is not bytes
                or len(frame.body) != frame.header.body_length
                or type(frame.header.version) is not int
                or frame.header.version != self._version
                or (self._version == 2
                    and frame.header.kind not in ("BEGIN", "READY", "GO", "CANCEL", "RESULT"))
                or frame.header.binding != self._binding
                or type(sender) is not str
                or sender not in ("client", "broker")
            ):
                _fail()
            expected = self._client_next if sender == "client" else self._broker_next
            if frame.header.sequence != expected:
                _fail()
            if self._mode == "status":
                disposition = self._status(sender, frame.header.kind)
            else:
                disposition = self._operation(sender, frame.header.kind)
            if sender == "client":
                self._client_next += 1
            else:
                self._broker_next += 1
            if self._failed:
                _fail()
            return disposition
        except BaseException as error:
            self._failed = True
            if isinstance(error, FrameError):
                raise FrameError("BI1_BROKER_LIFECYCLE_REFUSED") from None
            raise
        finally:
            self._lock.release()

    def _status(self, sender: str, kind: str) -> MessageDisposition:
        if sender == "client":
            if kind == "STATUS" and not self._begun:
                self._begun = True
            elif kind == "ACK" and self._terminal_message == "CLOSED":
                self._acked_message = True
                return MessageDisposition.ACK_REQUEST
            else:
                _fail()
        elif (
            self._begun
            and self._terminal_message is None
            and kind in ("CLOSED", "PENDING", "UNKNOWN")
        ):
            self._terminal_message = kind
            if kind == "PENDING":
                return MessageDisposition.STATUS_PENDING
            if kind == "UNKNOWN":
                return MessageDisposition.STATUS_UNKNOWN
        else:
            _fail()
        return MessageDisposition.CONTROL

    def _operation(self, sender: str, kind: str) -> MessageDisposition:
        if sender == "client":
            if kind == "BEGIN" and not self._begun:
                if self._invalidated and self._role == "gateway":
                    _fail()
                self._begun = True
            elif kind == "GO" and self._begun and self._ready and not self._go:
                if self._cancel or self._invalidated or self._terminal_message is not None:
                    _fail()
                self._go = True
            elif kind == "CANCEL" and self._begun and not self._cancel:
                # Includes a terminal/CANCEL race before ACK: cleanup only.
                self._cancel = True
                self._invalidated = True
            elif kind == "ACK" and self._terminal_message in ("RESULT", "CLOSED"):
                self._acked_message = True
                return MessageDisposition.ACK_REQUEST
            else:
                _fail()
            return MessageDisposition.CONTROL
        if not self._begun or self._terminal_message is not None:
            _fail()
        if kind == "READY" and not self._ready:
            if self._invalidated and self._role == "broker":
                _fail()
            self._ready = True
            return MessageDisposition.CONTROL
        if kind == "CLOSED":
            self._terminal_message = kind
            return MessageDisposition.CONTROL
        if kind == "RESULT" and self._ready and self._go:
            if self._invalidated and self._role == "broker":
                _fail()  # broker may send only independently verified CLOSED after cancellation
            self._terminal_message = kind
            return (
                MessageDisposition.RESULT_DISCARDED
                if self._invalidated
                else MessageDisposition.RESULT_CANDIDATE
            )
        _fail()
