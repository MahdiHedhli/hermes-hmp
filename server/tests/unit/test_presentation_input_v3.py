import copy
import json
import struct

import pytest

from hmp_plugin.presentation_input_v3 import decode_input_v3, encode_input_v3, validate_input_v3
from hmp_plugin.presentation_jobs import FrameError


def row():
    return {
        "schema": 3,
        "challenge": "a" * 64,
        "epoch": 1,
        "profile": "default",
        "root": "/srv/hermes",
        "home": "/srv/hermes",
        "operation": "METADATA",
        "expected_avatar_sha": None,
        "uid": 501,
        "gid": 20,
        "dir_modes": [448, 488, 493],
        "leaf_modes": [384, 416, 420],
        "source_manifest_sha": "b" * 64,
        "deadline_ns": 2000000000,
        "directory_policy": [[0, 0, 493], [0, 0, 493], [501, 20, 448]],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
        "parent_work_counts": {
            "read_bytes": 0,
            "hash_bytes": 0,
            "opens": 3,
            "metadata": 12,
            "path_bytes": 30,
            "yaml_nodes": 0,
            "yaml_tokens": 0,
            "raster_units": 0,
        },
    }


def test_full_closed_input3_roundtrip():
    value = row()
    assert decode_input_v3(encode_input_v3(value)) == value


@pytest.mark.parametrize("schema", [1, 2, 4, True, "3"])
def test_no_legacy_or_unknown_input_fallback(schema):
    value = row()
    value["schema"] = schema
    with pytest.raises(FrameError):
        validate_input_v3(value)


@pytest.mark.parametrize(
    "key,value",
    [("opens", 0), ("metadata", 11), ("path_bytes", True), ("yaml_tokens", 1), ("hash_bytes", -1)],
)
def test_understated_or_nonparent_work_is_refused(key, value):
    data = row()
    data["parent_work_counts"][key] = value
    with pytest.raises(FrameError):
        encode_input_v3(data)


def test_missing_extra_and_duplicate_counter_keys_are_closed():
    for mutation in ("missing", "extra", "duplicate"):
        data = copy.deepcopy(row())
        if mutation == "missing":
            data["parent_work_counts"].pop("yaml_tokens")
        if mutation == "extra":
            data["parent_work_counts"]["other"] = 0
        body = json.dumps(data).encode()
        if mutation == "duplicate":
            body = body.replace(b'"opens": 3', b'"opens": 3, "opens": 3')
        with pytest.raises(FrameError):
            decode_input_v3(struct.pack(">I", len(body)) + body)


def test_named_profile_counts_must_follow_the_full_home_chain():
    data = row()
    data["profile"] = "alpha"
    data["home"] = "/srv/hermes/profiles/alpha"
    data["directory_policy"] += [[501, 20, 448], [501, 20, 448]]
    with pytest.raises(FrameError):
        encode_input_v3(data)
    data["parent_work_counts"].update(opens=5, metadata=20, path_bytes=69)
    assert decode_input_v3(encode_input_v3(data)) == data


def test_full_input_envelope_stays_bounded_with_parent_counters():
    data = row()
    data["root"] = data["home"] = "/" + "x" * 4095
    data["directory_policy"] = [[0, 0, 493], [501, 20, 448]]
    data["parent_work_counts"].update(opens=2, metadata=8, path_bytes=12288)
    with pytest.raises(FrameError):
        encode_input_v3(data)


def test_processing_input3_refuses_legacy_before_any_file_effect():
    import io

    from hmp_plugin.presentation_jobs import INPUT_LIMIT, _envelope
    from hmp_plugin.presentation_worker import process_child_stream_v3

    legacy = row()
    legacy["schema"] = 2
    legacy.pop("parent_work_counts")

    class NoFiles:
        def __getattr__(self, name):
            raise AssertionError("unexpected file effect: " + name)

    output = io.BytesIO()
    with pytest.raises(FrameError):
        process_child_stream_v3(
            io.BytesIO(_envelope(legacy, INPUT_LIMIT) + b"a" * 64 + b"\n"),
            output,
            fs=NoFiles(),
            clock=lambda: 1.0,
            deadline=2.0,
            effective_uid=501,
            effective_gid=20,
        )
    assert output.getvalue() == b""
