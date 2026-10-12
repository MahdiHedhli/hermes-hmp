import pytest

from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_output_v2 import (
    compare_parent_totals,
    decode_output_v2,
    encode_output_v2,
    validate_header_v2,
)


def header():
    return {
        "schema": 2,
        "challenge": "a" * 64,
        "epoch": 1,
        "outcome": "OK",
        "fields": {"custom": True},
        "mime": None,
        "width": 0,
        "height": 0,
        "avatar_sha": None,
        "avatar_length": 0,
        "source_proof": {
            "profile_meta": None,
            "profile_sha": None,
            "avatar_meta": None,
            "avatar_body_sha": None,
        },
        "absence_bitmap": 15,
        "chain": [],
        "ledger": {
            "body_bytes": 10,
            "opens": 5,
            "metadata": 14,
            "path_bytes": 50,
            "raster_units": 0,
            "yaml_nodes": 4,
            "hash_bytes": 0,
            "yaml_tokens": 10,
        },
        "cleanup": {"known_fds_closed": True, "unknown_close": False},
    }


def parent():
    return {
        "read_bytes": 0,
        "hash_bytes": 0,
        "opens": 3,
        "metadata": 12,
        "path_bytes": 30,
        "yaml_nodes": 0,
        "yaml_tokens": 0,
        "raster_units": 0,
    }


def test_complete_result2_roundtrip_and_exact_alias_conservation():
    row = header()
    assert decode_output_v2(encode_output_v2(row, b""), "a" * 64, 1) == (row, b"")
    totals = compare_parent_totals(row, parent_home="/srv/hermes", parent_counts=parent())
    assert totals["read_bytes"] == 10 and "body_bytes" not in totals
    assert totals["opens"] == 5  # already includes3parent opens; never add again


@pytest.mark.parametrize("schema", [1, 3, True])
def test_legacy_or_unknown_result_has_no_fallback(schema):
    row = header()
    row["schema"] = schema
    with pytest.raises(FrameError):
        validate_header_v2(row)


@pytest.mark.parametrize(
    "key,value",
    [("hash_bytes", True), ("hash_bytes", 2000001), ("yaml_tokens", 2049), ("yaml_tokens", -1)],
)
def test_new_complete_totals_are_strict_and_bounded(key, value):
    row = header()
    row["ledger"][key] = value
    with pytest.raises(FrameError):
        validate_header_v2(row)


def test_missing_extra_and_under_parent_totals_refuse():
    for key in ("hash_bytes", "yaml_tokens"):
        row = header()
        row["ledger"].pop(key)
        with pytest.raises(FrameError):
            validate_header_v2(row)
    row = header()
    row["ledger"]["read_bytes"] = 10
    with pytest.raises(FrameError):
        validate_header_v2(row)
    for key, amount in (("opens", 2), ("metadata", 11), ("path_bytes", 29)):
        row = header()
        row["ledger"][key] = amount
        with pytest.raises(FrameError):
            compare_parent_totals(row, parent_home="/srv/hermes", parent_counts=parent())


def test_wrong_job_and_trailing_body_cannot_bind():
    wire = encode_output_v2(header(), b"")
    for challenge, epoch in (("b" * 64, 1), ("a" * 64, 2)):
        with pytest.raises(FrameError):
            decode_output_v2(wire, challenge, epoch)
    with pytest.raises(FrameError):
        decode_output_v2(wire + b"extra", "a" * 64, 1)


@pytest.mark.parametrize("epoch", [True, 0, "1"])
def test_expected_epoch_binding_is_exact_integer(epoch):
    with pytest.raises(FrameError):
        decode_output_v2(encode_output_v2(header(), b""), "a" * 64, epoch)
