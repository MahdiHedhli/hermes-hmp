"""Source-only closed framing. These tokens/frames are never authority receipts."""

import dataclasses
import json
import struct

import pytest

from hmp_plugin.presentation_broker_codec import (
    FRAME_LIMIT,
    HEADER_LIMIT,
    MAGIC,
    BrokerBinding,
    decode_frame,
    decode_header,
    encode_frame,
    header_size,
)
from hmp_plugin.presentation_jobs import INPUT_LIMIT, OUTPUT_LIMIT, FrameError


@pytest.fixture
def binding():
    return BrokerBinding("a" * 52, "1" * 32, "2" * 64, "3" * 64, "4" * 64)


def row(binding, **updates):
    value = {
        "v": 1,
        "kind": "GO",
        "iid": binding.iid,
        "listener": binding.listener,
        "broker": binding.broker,
        "channel": binding.channel,
        "operation": binding.operation,
        "sequence": 1,
        "body_length": 0,
    }
    value.update(updates)
    return value


def header(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return MAGIC + struct.pack(">I", len(raw)) + raw


def test_golden_canonical_go_is_fixed_and_immutable(binding):
    raw = (
        b'{"body_length":0,"broker":"'
        + b"2" * 64
        + b'","channel":"'
        + b"3" * 64
        + b'","iid":"'
        + b"a" * 52
        + b'","kind":"GO","listener":"'
        + b"1" * 32
        + b'","operation":"'
        + b"4" * 64
        + b'","sequence":1,"v":1}'
    )
    expected = b"HBR1" + len(raw).to_bytes(4, "big") + raw
    assert encode_frame(binding, "GO", 1) == expected
    decoded = decode_frame(expected, expected=binding)
    assert decoded.header.kind == "GO" and decoded.body == b""
    with pytest.raises(dataclasses.FrozenInstanceError):
        decoded.header.sequence = 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        decoded.header.binding.channel = "5" * 64


@pytest.mark.parametrize(
    "kind", ["READY", "GO", "CANCEL", "CLOSED", "ACK", "STATUS", "PENDING", "UNKNOWN"]
)
@pytest.mark.parametrize("sequence", [0, 3])
def test_control_frames_have_no_body_but_do_not_imply_lifecycle(binding, kind, sequence):
    encoded = encode_frame(binding, kind, sequence)
    assert decode_frame(encoded, expected=binding).header.sequence == sequence
    with pytest.raises(FrameError):
        encode_frame(binding, kind, sequence, b"x")


@pytest.mark.parametrize("kind, limit", [("BEGIN", INPUT_LIMIT + 4), ("RESULT", OUTPUT_LIMIT)])
def test_body_exact_bounds_and_header_first_validation(binding, kind, limit):
    for count in (4, limit):
        body = b"\0" * count  # only framing; not a valid input3/output2 or custody proof
        encoded = encode_frame(binding, kind, 0, body)
        n = header_size(encoded[:8])
        parsed = decode_header(encoded[: 8 + n], expected=binding)
        assert parsed.body_length == count
        assert decode_frame(encoded, expected=binding).body == body
    for count in (0, 3, limit + 1):
        with pytest.raises(FrameError):
            # No body exists or is allocated: reject the overclaim at header stage.
            decode_header(header(row(binding, kind=kind, body_length=count)), expected=binding)
    assert FRAME_LIMIT == 8 + HEADER_LIMIT + OUTPUT_LIMIT


@pytest.mark.parametrize("kind", ["go", "HELLO", "EXEC", "RESULT\n", "", 1, None])
def test_unknown_or_wrong_type_kind_cannot_select_an_operation(binding, kind):
    with pytest.raises(FrameError):
        decode_header(header(row(binding, kind=kind)), expected=binding)


@pytest.mark.parametrize(
    "field, value",
    [
        ("sequence", True),
        ("sequence", 1.0),
        ("sequence", -1),
        ("sequence", 4),
        ("body_length", False),
        ("body_length", 0.0),
        ("body_length", -1),
        ("v", True),
        ("v", 1.0),
        ("v", 2),
        ("v", "1"),
    ],
)
def test_header_number_fields_are_exact_bounded_integers(binding, field, value):
    with pytest.raises(FrameError):
        decode_header(header(row(binding, **{field: value})), expected=binding)


@pytest.mark.parametrize(
    "field, value",
    [
        ("iid", "b" * 52),  # invalid final base32 bits
        ("listener", "5" * 32),
        ("broker", "5" * 64),
        ("channel", "5" * 64),
        ("operation", "5" * 64),
    ],
)
def test_each_binding_plane_is_compared_before_body_acceptance(binding, field, value):
    with pytest.raises(FrameError):
        decode_header(header(row(binding, **{field: value})), expected=binding)


@pytest.mark.parametrize("field", ["listener", "broker", "channel", "operation"])
@pytest.mark.parametrize("invalid", [None, True, "A" * 64, "x", "0\n"])
def test_binding_values_have_exact_closed_syntax(binding, field, invalid):
    with pytest.raises(FrameError):
        dataclasses.replace(binding, **{field: invalid})


@pytest.mark.parametrize(
    "transform",
    [
        lambda raw: b" " + raw,
        lambda raw: raw.replace(b'"v":1', b'"v":1,"v":1'),
        lambda raw: raw.replace(b'"v":1', b'"v":NaN'),
        lambda raw: raw.replace(b'"v":1', b'"v":Infinity'),
        lambda raw: raw.replace(b'"v":1', b'"v":1e0'),
        lambda raw: raw.replace(b'"kind":"GO"', b'"kind":"\\u0047O"'),
        lambda raw: raw.replace(b'"sequence":1', b'"sequence":-0'),
        lambda raw: raw[:-1] + b',"unexpected":"SYNTHETIC_PRIVATE_VALUE"}',
        lambda raw: b'{"v":1}',
        lambda raw: b"[]",
        lambda raw: b"null",
        lambda raw: b"\xff",
    ],
)
def test_noncanonical_duplicate_unknown_or_malformed_headers_refuse_without_echo(
    binding, transform
):
    raw = transform(encode_frame(binding, "GO", 1)[8:])
    packet = MAGIC + struct.pack(">I", len(raw)) + raw
    with pytest.raises(FrameError) as error:
        decode_header(packet, expected=binding)
    assert str(error.value) == "BI1_BROKER_FRAME_REFUSED"


def test_different_key_order_and_missing_fields_refuse(binding):
    value = row(binding)
    raw = json.dumps(value, separators=(",", ":")).encode("ascii")
    with pytest.raises(FrameError):
        decode_header(MAGIC + len(raw).to_bytes(4, "big") + raw, expected=binding)
    del value["channel"]
    with pytest.raises(FrameError):
        decode_header(header(value), expected=binding)


@pytest.mark.parametrize(
    "prefix",
    [b"", b"HBR1", b"FAIL\0\0\0\1", b"HBR1\0\0\0\0", b"HBR1\0\0\4\1", b"HBR1\xff\xff\xff\xff"],
)
def test_invalid_prefix_never_admits_header_or_body(prefix):
    with pytest.raises(FrameError):
        header_size(prefix)


def test_truncated_or_trailing_header_and_body_are_refused(binding):
    valid = encode_frame(binding, "BEGIN", 0, b"data")
    n = header_size(valid[:8])
    for packet in (valid[:-1], valid + b"extra", valid[: 8 + n], valid[: 8 + n - 1]):
        with pytest.raises(FrameError):
            decode_frame(packet, expected=binding)
    with pytest.raises(FrameError):
        decode_header(valid, expected=binding)  # body is not part of header API
    with pytest.raises(FrameError):
        decode_frame(b"x" * (FRAME_LIMIT + 1), expected=binding)


@pytest.mark.parametrize("value", [None, [], bytearray(b"data"), "data"])
def test_mutable_or_coerced_body_is_not_accepted(binding, value):
    with pytest.raises(FrameError):
        encode_frame(binding, "BEGIN", 0, value)


def test_v2_cancel_requires_explicit_selection_and_exact_fixed_body(binding):
    body = struct.pack(">QQ", 10, 250_000_010)
    packet = encode_frame(binding, "CANCEL", 2, body, version=2)
    parsed = decode_frame(packet, expected=binding, expected_version=2)
    assert parsed.body == body and parsed.header.version == 2
    with pytest.raises(FrameError):
        decode_frame(packet, expected=binding)  # no auto-upgrade
    legacy = encode_frame(binding, "CANCEL", 2)
    with pytest.raises(FrameError):
        decode_frame(legacy, expected=binding, expected_version=2)  # no downgrade
    for size in (0, 15, 17, 32):
        with pytest.raises(FrameError):
            encode_frame(binding, "CANCEL", 2, b"x" * size, version=2)
        with pytest.raises(FrameError):
            decode_header(header(row(binding, v=2, kind="CANCEL", body_length=size)),
                          expected=binding, expected_version=2)


@pytest.mark.parametrize("version", [True, 0, 3, 1.0, "2", None])
def test_protocol_selection_is_exact_and_closed(binding, version):
    with pytest.raises(FrameError):
        encode_frame(binding, "GO", 1, version=version)
    with pytest.raises(FrameError):
        decode_frame(encode_frame(binding, "GO", 1), expected=binding,
                     expected_version=version)


@pytest.mark.parametrize("kind", ["GO", "READY", "STATUS", "PENDING", "UNKNOWN", "CLOSED", "ACK"])
def test_v2_other_control_frames_remain_bodyless(binding, kind):
    packet = encode_frame(binding, kind, 1, version=2)
    assert decode_frame(packet, expected=binding, expected_version=2).body == b""
    with pytest.raises(FrameError):
        encode_frame(binding, kind, 1, b"x" * 16, version=2)
