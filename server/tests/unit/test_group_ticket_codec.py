"""Synthetic bytes only; no ticket mint, native import, socket or phone authority."""

import json
from dataclasses import FrozenInstanceError, fields

import pytest

from hmp_plugin.group_ticket_codec import (
    GroupTicketCodecRefusalError,
    build_group_ticket_request,
    parse_group_ticket_reply,
)

PROFILE = "/synthetic/profile"
INSTANCE = "synthetic-instance"
TICKET = "SYNTHETIC_ONLY_" + "x" * 30


def envelope():
    return {
        "protocol": 1,
        "id": 1,
        "ok": True,
        "result": {
            "ticket": TICKET,
            "expires_in_seconds": 30,
            "instance_id": INSTANCE,
            "profile_id": PROFILE,
            "runtime_protocol": 1,
        },
    }


def encode(value):
    return json.dumps(value, ensure_ascii=True).encode("ascii") + b"\n"


def parse(raw):
    return parse_group_ticket_reply(raw, profile_id=PROFILE, instance_id=INSTANCE)


def test_fixed_request_has_profile_scope_policy_and_no_subject():
    raw = build_group_ticket_request(profile_id=PROFILE, instance_id=INSTANCE)
    assert raw.endswith(b"\n") and len(raw) < 65_537
    assert json.loads(raw) == {
        "protocol": 1,
        "id": 1,
        "verb": "session-ticket",
        "params": {
            "profile_id": PROFILE,
            "instance_id": INSTANCE,
            "purpose": "interactive",
            "scope": "profile",
            "restart_wait": "refuse",
        },
    }


def test_grant_is_frozen_narrow_and_not_printed():
    grant = parse(encode(envelope()))
    assert grant.ticket == TICKET and grant.expires_in_seconds == 30
    assert [field.name for field in fields(grant)] == ["ticket", "expires_in_seconds"]
    assert TICKET not in repr(grant) and TICKET not in str(grant)
    with pytest.raises(FrozenInstanceError):
        grant.ticket = "changed"


@pytest.mark.parametrize(
    "where,field,value",
    [
        ("root", "protocol", True),
        ("root", "protocol", 2),
        ("root", "id", True),
        ("root", "id", "1"),
        ("root", "id", 2),
        ("root", "ok", 1),
        ("root", "ok", False),
        ("result", "runtime_protocol", True),
        ("result", "runtime_protocol", 2),
        ("result", "profile_id", "/foreign"),
        ("result", "profile_id", None),
        ("result", "instance_id", "foreign"),
        ("result", "instance_id", []),
        ("result", "expires_in_seconds", True),
        ("result", "expires_in_seconds", 0),
        ("result", "expires_in_seconds", -1),
        ("result", "expires_in_seconds", 30.0),
        ("result", "expires_in_seconds", 1 << 31),
        ("result", "ticket", ""),
        ("result", "ticket", "x" * 257),
        ("result", "ticket", "not a token"),
        ("result", "ticket", "x\ny"),
        ("result", "ticket", "x/y"),
        ("result", "ticket", "é"),
        ("result", "ticket", None),
        ("result", "ticket", []),
    ],
)
def test_identity_types_protocol_expiry_and_ticket_refusals(where, field, value):
    value_object = envelope()
    target = value_object if where == "root" else value_object["result"]
    target[field] = value
    with pytest.raises(
        GroupTicketCodecRefusalError, match=r"^Native group ticket reply unavailable\.$"
    ):
        parse(encode(value_object))


@pytest.mark.parametrize(
    "root", [True, None, [], 1, "text", {}, {"ok": False, "error": "PRIVATE_RAW"}]
)
def test_wrong_root_and_native_refusal_never_publish_raw_diagnostics(root):
    with pytest.raises(GroupTicketCodecRefusalError) as caught:
        parse(encode(root))
    assert "PRIVATE_RAW" not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\n",
        b"{}",
        b"{}\r\n",
        b"{}\n{}\n",
        b"{}\n ",
        b"\xff\n",
        b"[" * 2000 + b"\n",
        b'{"x":NaN}\n',
        b'{"x":Infinity}\n',
        b'{"ok":true,"ok":false}\n',
        b'{"result":{"ticket":"a","ticket":"b"}}\n',
        b" " * 65_537 + b"\n",
    ],
)
def test_framing_json_duplicates_and_decoder_failures_are_fixed(raw):
    with pytest.raises(GroupTicketCodecRefusalError) as caught:
        parse(raw)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert caught.value.args == ("Native group ticket reply unavailable.",)


class Hostile:
    def __len__(self):
        raise AssertionError("foreign length")

    def __str__(self):
        raise AssertionError("foreign string conversion")

    def encode(self, *args, **kwargs):
        raise AssertionError("foreign encoder")


@pytest.mark.parametrize(
    "bad", [Hostile(), None, 1, True, b"bytes", "", "x" * 4097, "\ud800", "null\x00", "é" * 4096]
)
def test_binding_refusal_before_foreign_hooks_or_oversize_encoding(bad):
    with pytest.raises(GroupTicketCodecRefusalError):
        build_group_ticket_request(profile_id=bad, instance_id=INSTANCE)
    with pytest.raises(GroupTicketCodecRefusalError):
        parse_group_ticket_reply(encode(envelope()), profile_id=PROFILE, instance_id=bad)


@pytest.mark.parametrize("bad", [Hostile(), None, 1, True, "string", bytearray(b"{}\n")])
def test_input_must_be_exact_immutable_bytes(bad):
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(bad)


def test_bounded_scalar_additions_are_ignored_not_retained():
    value = envelope()
    value["future"] = "safe observation"
    value["result"]["future"] = 42
    assert parse(encode(value)).ticket == TICKET


@pytest.mark.parametrize("bad", [{}, [], "x" * 257, float("inf"), 1 << 64, "\ud800"])
@pytest.mark.parametrize("where", ["root", "result"])
def test_ignored_metadata_still_has_closed_scalar_bounds(where, bad):
    value = envelope()
    target = value if where == "root" else value["result"]
    target["future"] = bad
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(encode(value))


def test_successful_native_ascii_escaped_envelope_bound_including_additions():
    # Exact field maxima + worst JSON ASCII escaping of legal non-NUL controls.
    profile, instance = "\x01" * 4096, "\x01" * 256
    value = envelope()
    value["result"].update(
        profile_id=profile, instance_id=instance, ticket="." * 256, expires_in_seconds=(1 << 31) - 1
    )
    for target, count in [(value, 4), (value["result"], 3)]:
        for index in range(count):
            target["x" + "\x01" * 62 + str(index)] = "\x01" * 256
    raw = encode(value)
    assert len(raw) <= 44_800 < 65_537
    assert len(build_group_ticket_request(profile_id=profile, instance_id=instance)) < 65_537
    grant = parse_group_ticket_reply(raw, profile_id=profile, instance_id=instance)
    assert grant.ticket == "." * 256


def test_extra_field_count_and_key_bounds_refuse():
    for key in ["x" * 65, "\ud800"]:
        value = envelope()
        value[key] = 1
        with pytest.raises(GroupTicketCodecRefusalError):
            parse(encode(value))
    value = envelope()
    for index in range(5):
        value[str(index)] = 1
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(encode(value))


def test_every_websocket_token_character_is_supported_without_whitespace():
    ticket = "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    value = envelope()
    value["result"]["ticket"] = ticket
    assert parse(encode(value)).ticket == ticket


@pytest.mark.parametrize("fragment", ['"id": 1', '"ticket": "' + TICKET + '"'])
def test_duplicate_guard_independent_of_other_required_fields(fragment):
    raw = encode(envelope())
    assert raw.count(fragment.encode()) == 1
    raw = raw.replace(fragment.encode(), (fragment + ", " + fragment).encode(), 1)
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(raw)


def test_frame_limit_independent_of_valid_json_and_closed_fields():
    raw = b" " * 65_536 + encode(envelope())
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(raw)


def test_numeric_exponent_overflow_is_not_a_supported_scalar_addition():
    value = envelope()
    value["future"] = 0
    raw = encode(value).replace(b'"future": 0', b'"future": 1e999')
    with pytest.raises(GroupTicketCodecRefusalError):
        parse(raw)


def test_empty_future_scalar_is_harmless_and_not_retained():
    value = envelope()
    value["future"] = ""
    assert parse(encode(value)).ticket == TICKET
