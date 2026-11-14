"""Synthetic DATA controls only; no sockets, native waiters or authenticated caller."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from hmp_plugin import approval_test_host_codec as codec
from hmp_plugin import wire

_IID = "a" * 52  # Canonical base32 of 32 zero bytes, synthetic only.
_NONCE = "0" * 32
_OPERATION_ID = "1" * 32


def _current() -> codec.HostGeneration:
    return codec.HostGeneration(_IID, 7, _NONCE)


def _begin(**changes: object) -> dict[str, object]:
    return {
        "v": 1, "iid": _IID, "pid": 7, "nonce": _NONCE, "op": "begin",
        "device_id": "synthetic-device", "profile": "synthetic-profile",
        "session_id": "synthetic-session", **changes,
    }


def _raw(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode()


def _frame(raw: bytes, length: int | None = None) -> bytes:
    return (len(raw) if length is None else length).to_bytes(4, "big") + raw


def _fixed_refusal(call: Callable[[], object]) -> None:
    # A synthetic rejected marker must not escape via message, cause, context or repr.
    with pytest.raises(codec.HostCodecError) as caught:
        call()
    error = caught.value
    assert str(error) == "approval test unavailable"
    assert error.args == ("approval test unavailable",)
    assert "REJECTED_PRIVATE_MARKER" not in repr(error)
    assert error.__cause__ is None
    assert error.__context__ is None


class _FakeAdmission:
    """Proves syntactic refusal before a downstream fake; grants no authority."""

    def __init__(self) -> None:
        self.calls: list[codec.HostBeginRequest | codec.HostOperationRequest] = []

    def receive(self, raw: bytes) -> None:
        request = codec.decode_host_request(raw, current=_current())
        self.calls.append(request)


def test_valid_begin_preserves_exact_selectors_and_default_before_fake_admission() -> None:
    fake = _FakeAdmission()
    fake.receive(_raw(_begin(profile="e\u0301", session_id="\u00e9")))
    assert len(fake.calls) == 1
    request = fake.calls[0]
    assert type(request) is codec.HostBeginRequest
    assert request.profile == "e\u0301"
    assert request.session_id == "\u00e9"
    assert request.timeout_ms == 30000
    assert request.generation == _current()


@pytest.mark.parametrize("op", ["status", "cancel"])
def test_host_operations_do_not_accept_phone_fields(op: str) -> None:
    body = {"v": 1, "iid": _IID, "pid": 7, "nonce": _NONCE, "op": op}
    body.update(op=op, operation_id=_OPERATION_ID)
    request = codec.decode_host_request(_raw(body), current=_current())
    assert type(request) is codec.HostOperationRequest
    assert request.op == op
    assert request.operation_id == _OPERATION_ID
    assert codec.encode_host_request(request) == _frame(_raw(body))
    for field in ("choice", "user_id", "device_id", "phone_test_id", "timeout_ms"):
        fake = _FakeAdmission()
        _fixed_refusal(
            lambda fake=fake, field=field: fake.receive(
                _raw({**body, field: "REJECTED_PRIVATE_MARKER"})
            )
        )
        assert fake.calls == []


@pytest.mark.parametrize("operation_id", [None, True, 1, "", "A" * 32, "1" * 31,
                                       "g" * 32, "REJECTED_PRIVATE_MARKER"])
def test_host_operation_identifier_is_closed(operation_id: object) -> None:
    body = {"v": 1, "iid": _IID, "pid": 7, "nonce": _NONCE,
            "op": "cancel", "operation_id": operation_id}
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(_raw(body)))
    assert fake.calls == []


@pytest.mark.parametrize("timeout", [1, 60000])
def test_timeout_boundaries_are_preserved(timeout: int) -> None:
    request = codec.decode_host_request(_raw(_begin(timeout_ms=timeout)), current=_current())
    assert request.timeout_ms == timeout


@pytest.mark.parametrize("field,value", [
    ("v", True), ("v", 1.0), ("v", 2), ("pid", False), ("pid", 7.0),
    ("pid", 0), ("pid", 2**31), ("timeout_ms", True), ("timeout_ms", 1.0),
    ("timeout_ms", 0), ("timeout_ms", 60001), ("timeout_ms", None),
    ("iid", _IID.upper()), ("iid", "a" * 51 + "b"), ("nonce", "A" * 32),
    ("nonce", "0" * 31), ("op", "answer"), ("op", None),
    ("device_id", ""), ("profile", None), ("session_id", ["REJECTED_PRIVATE_MARKER"]),
])
def test_bad_fields_never_reach_fake_admission(field: str, value: object) -> None:
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(_raw(_begin(**{field: value}))))
    assert fake.calls == []


@pytest.mark.parametrize("field", ["v", "iid", "pid", "nonce", "op", "device_id",
                                  "profile", "session_id"])
def test_every_missing_required_field_is_fixed_refusal(field: str) -> None:
    body = _begin()
    del body[field]
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(_raw(body)))
    assert fake.calls == []


@pytest.mark.parametrize("field", ["device_id", "profile", "session_id"])
@pytest.mark.parametrize("value", ["a" * 257, "\u00e9" * 129, "\ud800", "\udfff",
                                  "a\u0000b", "a\u001fb", "a\u007fb", "a\u0080b",
                                  "a\u009fb"])
def test_selector_unicode_and_byte_bounds_do_not_normalize(field: str, value: str) -> None:
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(_raw(_begin(**{field: value}))))
    assert fake.calls == []


@pytest.mark.parametrize("value", ["a" * 256, "\u00e9" * 128, "\U0001f600" * 64,
                                  "e\u0301", "\u2028\u2029"])
def test_valid_unicode_selector_domain_round_trips(value: str) -> None:
    request = codec.HostBeginRequest(_current(), value, value, value)
    decoder = codec.HostRequestFrameDecoder()
    decoder.feed(codec.encode_host_request(request))
    assert decoder.finish(eof=True, current=_current()) == request


@pytest.mark.parametrize("field,value", [("iid", "b" * 51 + "a"), ("pid", 8),
                                        ("nonce", "1" * 32)])
def test_each_stale_generation_component_refuses_before_fake(field: str, value: object) -> None:
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(_raw(_begin(**{field: value}))))
    assert fake.calls == []
    # Other canonical components are valid DATA; equality is not normalization/authentication.
    matching = codec.HostGeneration(value if field == "iid" else _IID,
                                    value if field == "pid" else 7,
                                    value if field == "nonce" else _NONCE)
    assert codec.decode_host_request(_raw(_begin(**{field: value})), current=matching)


@pytest.mark.parametrize("raw", [
    b'{"v":1,"v":1}', b'{"v":1,"\\u0076":1}', b'{"unknown":"REJECTED_PRIVATE_MARKER"}',
    b'[]', b'null', b'{', b'{"x":"\xff"}', b'{"x":"\\ud800"}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{} {}', b'\xef\xbb\xbf{}',
])
def test_raw_syntax_is_context_free_before_fake(raw: bytes) -> None:
    fake = _FakeAdmission()
    _fixed_refusal(lambda: fake.receive(raw))
    assert fake.calls == []


def test_request_caps_before_parser_with_valid_exact_bound_control(monkeypatch) -> None:
    base = _raw(_begin())
    valid = base + b" " * (codec.REQUEST_CAP - len(base))
    calls: list[int] = []
    original = wire.parse_body

    def counted(raw: bytes, **kwargs: int):
        calls.append(len(raw))
        return original(raw, **kwargs)

    monkeypatch.setattr(wire, "parse_body", counted)
    for raw in (b"", valid + b" ", b"x" * 10000):
        _fixed_refusal(lambda raw=raw: codec.decode_host_request(raw, current=_current()))
    assert calls == []
    assert codec.decode_host_request(valid, current=_current()).timeout_ms == 30000
    assert calls == [2048]


def test_depth_is_checked_before_generic_decoder_with_boundary_control(monkeypatch) -> None:
    calls: list[str] = []
    original = wire.json.loads

    def counted(text: str, **kwargs: object):
        calls.append(text)
        return original(text, **kwargs)

    monkeypatch.setattr(wire.json, "loads", counted)
    # Top-level object depth one; nesting in an unknown field still counts before decode.
    _fixed_refusal(lambda: codec.decode_host_request(b'{"x":[[[[0]]]]}', current=_current()))
    assert calls == []
    _fixed_refusal(lambda: codec.decode_host_request(b'{"x":[[[0]]]}', current=_current()))
    assert calls == ['{"x":[[[0]]]}']  # Bounded JSON parsed, then closed schema refuses.


def test_string_brackets_and_escaped_quotes_are_not_depth() -> None:
    value = '[{\\"' * 20
    request = codec.decode_host_request(_raw(_begin(profile=value)), current=_current())
    assert request.profile == value


def test_every_fragment_boundary_requires_eof_before_returning_request() -> None:
    framed = _frame(_raw(_begin()))
    for split in range(len(framed) + 1):
        decoder = codec.HostRequestFrameDecoder()
        assert decoder.feed(framed[:split]) is None
        assert decoder.feed(framed[split:]) is None
        request = decoder.finish(eof=True, current=_current())
        assert type(request) is codec.HostBeginRequest
        _fixed_refusal(lambda decoder=decoder: decoder.finish(eof=True, current=_current()))
        _fixed_refusal(lambda decoder=decoder: decoder.feed(b""))


@pytest.mark.parametrize("length", [0, 2049, 2**32 - 1])
def test_header_refusal_precedes_parser_and_payload_retention(length: int, monkeypatch) -> None:
    calls: list[bytes] = []

    def forbidden(raw: bytes, **kwargs: int):
        calls.append(raw)
        raise AssertionError("parser must not run")

    monkeypatch.setattr(wire, "parse_body", forbidden)
    decoder = codec.HostRequestFrameDecoder()
    _fixed_refusal(lambda: decoder.feed(length.to_bytes(4, "big") + b"x" * 10000))
    assert calls == []
    assert decoder._buffer == bytearray()
    _fixed_refusal(lambda: decoder.feed(_frame(b"{}")))


@pytest.mark.parametrize("variant", ["short_header", "short_body", "trailing", "missing_eof",
                                    "nonbool_eof"])
def test_incomplete_or_trailing_frames_never_return_data(variant: str) -> None:
    frame = _frame(_raw(_begin()))
    decoder = codec.HostRequestFrameDecoder()
    if variant == "trailing":
        _fixed_refusal(lambda: decoder.feed(frame + b"x"))
    else:
        decoder.feed(frame[:3] if variant == "short_header" else
                     frame[:-1] if variant == "short_body" else frame)
        eof = False if variant == "missing_eof" else 1 if variant == "nonbool_eof" else True
        _fixed_refusal(lambda: decoder.finish(eof=eof, current=_current()))
    _fixed_refusal(lambda: decoder.feed(frame))


def test_two_requests_cannot_be_accepted_on_one_decoder() -> None:
    frame = _frame(_raw(_begin()))
    decoder = codec.HostRequestFrameDecoder()
    decoder.feed(frame)
    _fixed_refusal(lambda: decoder.feed(frame))
    _fixed_refusal(lambda: decoder.finish(eof=True, current=_current()))


def test_built_in_types_only_do_not_invoke_subclass_hooks() -> None:
    class HostileBytes(bytes):
        def __len__(self):
            raise AssertionError("untrusted length")

    class HostileString(str):
        def __len__(self):
            raise AssertionError("untrusted length")

    _fixed_refusal(lambda: codec.decode_host_request(HostileBytes(b"{}"), current=_current()))
    _fixed_refusal(lambda: codec.HostBeginRequest(_current(), HostileString("x"), "x", "x"))
    _fixed_refusal(lambda: codec.HostRequestFrameDecoder().feed(HostileBytes(b"x")))


def test_dtos_are_frozen_and_redacted_without_retaining_error_inputs() -> None:
    request = codec.HostBeginRequest(_current(), "REJECTED_PRIVATE_MARKER", "p", "s")
    items = (
        _current(), request, codec.HostOperationRequest(_current(), "cancel", _OPERATION_ID),
        codec.HostResponse("accepted", _OPERATION_ID, timeout_ms=30000),
    )
    for item in items:
        assert "REJECTED_PRIVATE_MARKER" not in repr(item)
        assert _IID not in repr(item)
        assert _OPERATION_ID not in repr(item)
    with pytest.raises(FrozenInstanceError):
        request.profile = "changed"
    _fixed_refusal(lambda: codec.decode_host_request(
        b'{"REJECTED_PRIVATE_MARKER":"\\ud800"}', current=_current()))


@pytest.mark.parametrize("response", [
    codec.HostResponse("unavailable"),
    codec.HostResponse("accepted", _OPERATION_ID, timeout_ms=1),
    codec.HostResponse("accepted", _OPERATION_ID, timeout_ms=60000),
    codec.HostResponse("status", _OPERATION_ID, "pending", remaining_ms=0),
    codec.HostResponse("status", _OPERATION_ID, "cleanup_pending", remaining_ms=60000),
    codec.HostResponse("cancel_requested", _OPERATION_ID, "cleanup_pending"),
    codec.HostResponse("completed", _OPERATION_ID, "once_acknowledged"),
    codec.HostResponse("completed", _OPERATION_ID, "denied"),
    codec.HostResponse("completed", _OPERATION_ID, "cancelled"),
    codec.HostResponse("completed", _OPERATION_ID, "expired"),
    codec.HostResponse("completed", _OPERATION_ID, "unavailable"),
])
def test_exact_response_shapes_round_trip(response: codec.HostResponse) -> None:
    frame = codec.encode_host_response(response)
    assert len(frame) <= 4100
    assert int.from_bytes(frame[:4], "big") == len(frame) - 4
    assert codec.decode_host_response_frame(frame) == response


def test_fixed_unavailable_is_exact_for_all_refusal_causes() -> None:
    raw = b'{"v":1,"result":"unavailable"}'
    frame = len(raw).to_bytes(4, "big") + raw
    for rejected in (b"", b"{}", b"REJECTED_PRIVATE_MARKER", _raw(_begin(pid=8))):
        _fixed_refusal(
            lambda rejected=rejected: codec.decode_host_request(rejected, current=_current())
        )
        assert codec.unavailable_response_frame() == frame


@pytest.mark.parametrize("response,raw", [
    (codec.HostResponse("accepted", _OPERATION_ID, timeout_ms=30000),
     b'{"v":1,"result":"accepted","operation_id":"11111111111111111111111111111111",'
     b'"timeout_ms":30000}'),
    (codec.HostResponse("status", _OPERATION_ID, "pending", remaining_ms=0),
     b'{"v":1,"result":"status","operation_id":"11111111111111111111111111111111",'
     b'"state":"pending","remaining_ms":0}'),
    (codec.HostResponse("cancel_requested", _OPERATION_ID, "cleanup_pending"),
     b'{"v":1,"result":"cancel_requested","operation_id":"11111111111111111111111111111111",'
     b'"state":"cleanup_pending"}'),
    (codec.HostResponse("completed", _OPERATION_ID, "denied"),
     b'{"v":1,"result":"completed","operation_id":"11111111111111111111111111111111",'
     b'"state":"denied"}'),
])
def test_response_bytes_match_independent_literal_contract_shapes(
    response: codec.HostResponse, raw: bytes
) -> None:
    expected = len(raw).to_bytes(4, "big") + raw
    assert codec.encode_host_response(response) == expected
    assert codec.decode_host_response_frame(expected) == response


@pytest.mark.parametrize("body", [
    {"v": True, "result": "unavailable"},
    {"v": 1, "result": "unavailable", "cause": "REJECTED_PRIVATE_MARKER"},
    {"v": 1, "result": "completed", "operation_id": _OPERATION_ID, "state": "pending"},
    {"v": 1, "result": "completed", "operation_id": _OPERATION_ID, "state": "cleanup_pending"},
    {"v": 1, "result": "status", "operation_id": _OPERATION_ID, "state": "pending",
     "remaining_ms": True},
    {"v": 1, "result": "status", "operation_id": _OPERATION_ID, "state": "pending",
     "remaining_ms": 60001},
    {"v": 1, "result": "accepted", "operation_id": "A" * 32, "timeout_ms": 30000},
    {"v": 1, "result": "cancel_requested", "operation_id": _OPERATION_ID, "state": "once"},
    {"v": 1, "result": "accepted", "operation_id": _OPERATION_ID, "timeout_ms": 30000,
     "remaining_ms": 0},
    {"v": 1, "result": "status", "operation_id": _OPERATION_ID, "state": "pending"},
])
def test_response_schema_refusals_are_fixed(body: dict[str, object]) -> None:
    _fixed_refusal(lambda: codec.decode_host_response_frame(_frame(_raw(body))))


def test_response_cap_before_parse_with_valid_exact_bound_control(monkeypatch) -> None:
    raw = b'{"v":1,"result":"unavailable"}'
    valid = raw + b" " * (4096 - len(raw))
    seen: list[int] = []
    original = wire.parse_body

    def counted(payload: bytes, **kwargs: int):
        seen.append(len(payload))
        return original(payload, **kwargs)

    monkeypatch.setattr(wire, "parse_body", counted)
    for frame in (_frame(valid + b" "), _frame(raw, 0), _frame(raw, 4097),
                  _frame(raw)[:-1], _frame(raw) + b"x"):
        _fixed_refusal(lambda frame=frame: codec.decode_host_response_frame(frame))
    assert seen == []
    assert codec.decode_host_response_frame(_frame(valid)) == codec.HostResponse("unavailable")
    assert seen == [4096]


def test_mutated_dto_is_revalidated_before_encoding() -> None:
    request = codec.HostBeginRequest(_current(), "d", "p", "s")
    object.__setattr__(request, "timeout_ms", True)
    _fixed_refusal(lambda: codec.encode_host_request(request))
    response = codec.HostResponse("unavailable")
    object.__setattr__(response, "operation_id", "REJECTED_PRIVATE_MARKER")
    _fixed_refusal(lambda: codec.encode_host_response(response))
