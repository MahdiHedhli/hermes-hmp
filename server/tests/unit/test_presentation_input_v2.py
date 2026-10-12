import copy

import pytest

from hmp_plugin.presentation_input_v2 import decode_input_v2, encode_input_v2, validate_input_v2
from hmp_plugin.presentation_jobs import FrameError


def row():
    return {
        "schema": 2,
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
        "deadline_ns": 2_000_000_000,
        "directory_policy": [[0, 0, 493], [0, 0, 493], [501, 20, 448]],
        "iid": "a" * 52,
        "canonical_fallback": "Hermes",
        "observed_at": 100,
    }


def test_closed_v2_roundtrip_with_parent_policy_and_projection_context():
    value = row()
    assert decode_input_v2(encode_input_v2(value)) == value


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema", 1),
        ("uid", 0),
        ("observed_at", True),
        ("iid", "wrong"),
        ("canonical_fallback", "x" * 257),
        ("canonical_fallback", " Hermes "),
        ("canonical_fallback", "\u202eHermes"),
        ("canonical_fallback", ""),
        ("home", "/srv/other"),
    ],
)
def test_invalid_or_legacy_context_refuses(key, value):
    data = row()
    data[key] = value
    with pytest.raises(FrameError):
        validate_input_v2(data)


@pytest.mark.parametrize(
    "rule", [[0, 0, 0o777], [999, 20, 0o700], [501, 99, 0o700], [501, 20, True]]
)
def test_root_home_policy_cannot_weaken_or_change_owner(rule):
    data = row()
    data["directory_policy"][-1] = rule
    with pytest.raises(FrameError):
        validate_input_v2(data)


def test_named_profile_geometry_is_exact_and_policy_includes_slash():
    data = row()
    data["profile"] = "alpha"
    data["home"] = "/srv/hermes/profiles/alpha"
    data["directory_policy"] += [[501, 20, 448], [501, 20, 448]]
    assert validate_input_v2(data) == data
    bad = copy.deepcopy(data)
    bad["directory_policy"].pop(0)
    with pytest.raises(FrameError):
        validate_input_v2(bad)


def test_prefix_ceiling_counts_filesystem_root():
    data = row()
    home = "/" + "/".join("p" + str(i) for i in range(31))
    data["root"] = data["home"] = home
    data["directory_policy"] = [[0, 0, 493] for _ in range(32)]
    data["directory_policy"][-1] = [501, 20, 448]
    assert decode_input_v2(encode_input_v2(data)) == data
    data["root"] = data["home"] = home + "/extra"
    data["directory_policy"].append([501, 20, 448])
    with pytest.raises(FrameError):
        validate_input_v2(data)


def test_unknown_fields_and_missing_parent_projection_context_are_closed():
    for key in ("iid", "canonical_fallback", "observed_at", "directory_policy"):
        data = row()
        data.pop(key)
        with pytest.raises(FrameError):
            validate_input_v2(data)
    data = row()
    data["authorization"] = "synthetic-not-allowed"
    with pytest.raises(FrameError):
        validate_input_v2(data)


def test_v2_control_requires_exact_go_eof_and_rejects_legacy_input():
    import io

    from hmp_plugin.presentation_jobs import encode_input
    from hmp_plugin.presentation_worker_control import read_worker_go_v2

    data = row()
    body = encode_input_v2(data)
    suffix = b"a" * 64 + b"\n"
    assert read_worker_go_v2(io.BytesIO(body + suffix), clock=lambda: 1.0, deadline=2.0) == data
    for invalid in (b"", b"b" * 64 + b"\n", suffix + b"extra"):
        with pytest.raises(FrameError):
            read_worker_go_v2(io.BytesIO(body + invalid), clock=lambda: 1.0, deadline=2.0)
    legacy = {
        key: value
        for key, value in data.items()
        if key not in {"directory_policy", "iid", "canonical_fallback", "observed_at"}
    }
    legacy["schema"] = 1
    with pytest.raises(FrameError):
        read_worker_go_v2(
            io.BytesIO(encode_input(legacy) + suffix), clock=lambda: 1.0, deadline=2.0
        )


def test_scope_reconstruction_preserves_exact_singleton_policy_and_identity():
    from hmp_plugin.presentation_worker import scope_from_v2

    data = row()
    scope = scope_from_v2(data, effective_uid=501, effective_gid=20)
    assert scope.profile is None
    assert scope.home_path == data["home"]
    assert [rule.modes for rule in scope.directory_rules] == [(493,), (493,), (448,)]
    for uid, gid in ((0, 20), (502, 20), (501, 21), (True, 20)):
        with pytest.raises(FrameError):
            scope_from_v2(data, effective_uid=uid, effective_gid=gid)
    data["profile"] = "alpha"
    data["home"] = "/srv/hermes/profiles/alpha"
    data["directory_policy"] += [[501, 20, 448], [501, 20, 448]]
    assert scope_from_v2(data, effective_uid=501, effective_gid=20).profile == "alpha"


def test_v2_processing_does_no_file_work_before_go_or_identity_refusal():
    import io

    from hmp_plugin.presentation_worker import process_child_stream_v2

    class NoFileEffects:
        def __getattr__(self, name):
            raise AssertionError("unexpected filesystem effect: " + name)

    for suffix, uid in ((b"wrong", 501), (b"a" * 64 + b"\n", 0)):
        output = io.BytesIO()
        with pytest.raises(FrameError):
            process_child_stream_v2(
                io.BytesIO(encode_input_v2(row()) + suffix),
                output,
                fs=NoFileEffects(),
                clock=lambda: 1.0,
                deadline=2.0,
                effective_uid=uid,
                effective_gid=20,
            )
        assert output.getvalue() == b""
