"""Pure AT1 host DATA codecs. Generation equality is not peer or phone authentication.

No sockets, clocks, producer calls, ID generation, authority decisions or registrations.
The caller must prove current generation/peer ownership and actual transport EOF/deadlines.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import wire

REQUEST_CAP = 2048
RESPONSE_CAP = 4096
DEPTH_CAP = 4
_COMMON = frozenset({"v", "iid", "pid", "nonce", "op"})
_BEGIN = _COMMON | {"device_id", "profile", "session_id"}
_OPERATION = _COMMON | {"operation_id"}
_STATES = frozenset(
    {"pending", "once_acknowledged", "denied", "cancelled", "expired", "unavailable",
     "cleanup_pending"}
)
_TERMINAL = _STATES - {"pending", "cleanup_pending"}


class HostCodecError(ValueError):
    """Fixed refusal; no input, parser cause or authority metadata is retained."""

    def __init__(self) -> None:
        super().__init__("approval test unavailable")


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise HostCodecError()
    return value


def _hex_id(value: object) -> str:
    if type(value) is not str or len(value) != 32:
        raise HostCodecError()
    if any(ch not in "0123456789abcdef" for ch in value):
        raise HostCodecError()
    return value


def _iid(value: object) -> str:
    if type(value) is not str or len(value) != 52:
        raise HostCodecError()
    failed = False
    try:
        wire.require_iid(value)
    except ValueError:
        failed = True
    # Raise outside the parser exception handler: no raw exception context survives.
    if failed:
        raise HostCodecError()
    return value


def _selector(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 256:
        raise HostCodecError()
    failed = False
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError:
        failed = True
    if failed:
        raise HostCodecError()
    if len(raw) > 256 or any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in value):
        raise HostCodecError()
    return value


@dataclass(frozen=True, slots=True, repr=False)
class HostGeneration:
    """Comparison DATA only. No provenance or capability is conferred by construction."""

    iid: str
    pid: int
    nonce: str

    def __post_init__(self) -> None:
        _iid(self.iid)
        _integer(self.pid, 1, 2**31 - 1)
        _hex_id(self.nonce)


@dataclass(frozen=True, slots=True, repr=False)
class HostBeginRequest:
    generation: HostGeneration
    device_id: str
    profile: str
    session_id: str
    timeout_ms: int = 30000

    def __post_init__(self) -> None:
        _generation(self.generation)
        _selector(self.device_id)
        _selector(self.profile)
        _selector(self.session_id)
        _integer(self.timeout_ms, 1, 60000)


@dataclass(frozen=True, slots=True, repr=False)
class HostOperationRequest:
    generation: HostGeneration
    op: str
    operation_id: str

    def __post_init__(self) -> None:
        _generation(self.generation)
        if type(self.op) is not str or self.op not in ("status", "cancel"):
            raise HostCodecError()
        _hex_id(self.operation_id)


def _generation(value: object) -> HostGeneration:
    if type(value) is not HostGeneration:
        raise HostCodecError()
    # Defensive revalidation also fences artificially mutated dataclass instances.
    _iid(value.iid)
    _integer(value.pid, 1, 2**31 - 1)
    _hex_id(value.nonce)
    return value


def _body(raw: bytes, cap: int) -> dict[str, object]:
    if type(raw) is not bytes or not 1 <= len(raw) <= cap:
        raise HostCodecError()
    failed = False
    try:
        body = wire.parse_body(raw, max_bytes=cap, max_depth=DEPTH_CAP)
    except (ValueError, RecursionError):
        failed = True
    if failed:
        raise HostCodecError()
    return body


def decode_host_request(
    raw: bytes, *, current: HostGeneration
) -> HostBeginRequest | HostOperationRequest:
    """Decode selectors; current is comparison DATA, not verified peer authority."""
    expected = _generation(current)
    body = _body(raw, REQUEST_CAP)
    op = body.get("op")
    if type(op) is not str:
        raise HostCodecError()
    keys = frozenset(body)
    if op == "begin":
        if keys not in (_BEGIN, _BEGIN | {"timeout_ms"}):
            raise HostCodecError()
    elif op not in ("status", "cancel") or keys != _OPERATION:
        raise HostCodecError()
    _integer(body["v"], 1, 1)
    generation = HostGeneration(body["iid"], body["pid"], body["nonce"])
    if generation != expected:
        raise HostCodecError()
    if op == "begin":
        return HostBeginRequest(
            generation, body["device_id"], body["profile"], body["session_id"],
            body.get("timeout_ms", 30000),
        )
    return HostOperationRequest(generation, op, body["operation_id"])


class HostRequestFrameDecoder:
    """One bounded request; invalid/finished decoders are terminal, with no I/O."""

    __slots__ = ("_buffer", "_closed", "_length")

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._length: int | None = None
        self._closed = False

    def _refuse(self) -> None:
        self._closed = True
        self._buffer.clear()
        raise HostCodecError()

    def feed(self, chunk: bytes) -> None:
        if self._closed or type(chunk) is not bytes:
            self._refuse()
        # Copy only the at-most-four header bytes before validating its declared cap.
        offset = 0
        if self._length is None:
            needed = 4 - len(self._buffer)
            take = min(needed, len(chunk))
            self._buffer.extend(chunk[:take])
            offset = take
            if len(self._buffer) < 4:
                return
            self._length = int.from_bytes(self._buffer, "big")
            if not 1 <= self._length <= REQUEST_CAP:
                self._refuse()
        if len(self._buffer) + len(chunk) - offset > 4 + self._length:
            self._refuse()
        self._buffer.extend(chunk[offset:])

    def finish(
        self, *, eof: bool, current: HostGeneration
    ) -> HostBeginRequest | HostOperationRequest:
        if (
            self._closed or eof is not True or self._length is None
            or len(self._buffer) != self._length + 4
        ):
            self._refuse()
        self._closed = True
        payload = bytes(self._buffer[4:])
        self._buffer.clear()
        return decode_host_request(payload, current=current)


def _frame(raw: bytes, cap: int) -> bytes:
    if type(raw) is not bytes or not 1 <= len(raw) <= cap:
        raise HostCodecError()
    return len(raw).to_bytes(4, "big") + raw


def encode_host_request(request: HostBeginRequest | HostOperationRequest) -> bytes:
    """Encode one framed host request. No CLI, peer, connection or EOF claim."""
    if type(request) not in (HostBeginRequest, HostOperationRequest):
        raise HostCodecError()
    generation = _generation(request.generation)
    body: dict[str, object] = {
        "v": 1, "iid": generation.iid, "pid": generation.pid, "nonce": generation.nonce,
    }
    if type(request) is HostBeginRequest:
        body.update(
            op="begin", device_id=_selector(request.device_id), profile=_selector(request.profile),
            session_id=_selector(request.session_id),
            timeout_ms=_integer(request.timeout_ms, 1, 60000),
        )
    else:
        if type(request.op) is not str or request.op not in ("status", "cancel"):
            raise HostCodecError()
        body.update(op=request.op, operation_id=_hex_id(request.operation_id))
    return _frame(wire.dump_json(body), REQUEST_CAP)


@dataclass(frozen=True, slots=True, repr=False)
class HostResponse:
    """Closed host reply DATA; state text does not prove admission or cleanup."""

    result: str
    operation_id: str | None = None
    state: str | None = None
    timeout_ms: int | None = None
    remaining_ms: int | None = None

    def __post_init__(self) -> None:
        _response_body(self)


def _response_body(response: HostResponse) -> dict[str, object]:
    if type(response) is not HostResponse or type(response.result) is not str:
        raise HostCodecError()
    body: dict[str, object] = {"v": 1, "result": response.result}
    optional = (response.operation_id, response.state, response.timeout_ms, response.remaining_ms)
    if response.result == "unavailable":
        if any(value is not None for value in optional):
            raise HostCodecError()
        return body
    body["operation_id"] = _hex_id(response.operation_id)
    if response.result == "accepted":
        if response.state is not None or response.remaining_ms is not None:
            raise HostCodecError()
        body["timeout_ms"] = _integer(response.timeout_ms, 1, 60000)
        return body
    if response.result not in ("completed", "status", "cancel_requested"):
        raise HostCodecError()
    if type(response.state) is not str or response.state not in _STATES:
        raise HostCodecError()
    if response.result == "completed" and response.state not in _TERMINAL:
        raise HostCodecError()
    if response.timeout_ms is not None:
        raise HostCodecError()
    body["state"] = response.state
    if response.result == "status":
        body["remaining_ms"] = _integer(response.remaining_ms, 0, 60000)
    elif response.remaining_ms is not None:
        raise HostCodecError()
    return body


def encode_host_response(response: HostResponse) -> bytes:
    return _frame(wire.dump_json(_response_body(response)), RESPONSE_CAP)


def unavailable_response_frame() -> bytes:
    """The exact same framed bytes for every safe-to-reply host refusal."""
    return encode_host_response(HostResponse("unavailable"))


def decode_host_response_frame(frame: bytes) -> HostResponse:
    """One exact bounded reply frame; multi-frame ordering is a future caller obligation."""
    if type(frame) is not bytes or not 5 <= len(frame) <= RESPONSE_CAP + 4:
        raise HostCodecError()
    length = int.from_bytes(frame[:4], "big")
    if not 1 <= length <= RESPONSE_CAP or len(frame) != length + 4:
        raise HostCodecError()
    body = _body(frame[4:], RESPONSE_CAP)
    _integer(body.get("v"), 1, 1)
    result = body.get("result")
    shapes = {
        "unavailable": {"v", "result"},
        "accepted": {"v", "result", "operation_id", "timeout_ms"},
        "completed": {"v", "result", "operation_id", "state"},
        "status": {"v", "result", "operation_id", "state", "remaining_ms"},
        "cancel_requested": {"v", "result", "operation_id", "state"},
    }
    if type(result) is not str or result not in shapes or set(body) != shapes[result]:
        raise HostCodecError()
    return HostResponse(
        result, body.get("operation_id"), body.get("state"),
        body.get("timeout_ms"), body.get("remaining_ms"),
    )
