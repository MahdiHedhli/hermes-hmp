"""Scope hashing has no filesystem/provider/runtime effects."""
import hashlib
import json

import pytest

from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_input_v3 import encode_input_v3
from hmp_plugin.presentation_jobs import FrameError


def input_value():
    return dict(schema=3, challenge="a" * 64, epoch=1, profile="default",
                root="/srv/hermes", home="/srv/hermes", operation="METADATA",
                expected_avatar_sha=None, uid=501, gid=20, dir_modes=[448, 488, 493],
                leaf_modes=[384, 416, 420], source_manifest_sha="b" * 64,
                deadline_ns=2000000000,
                directory_policy=[[0, 0, 493], [0, 0, 493], [501, 20, 448]],
                iid="a" * 52, canonical_fallback="Hermes", observed_at=100,
                parent_work_counts=dict(read_bytes=0, hash_bytes=0, opens=3,
                                        metadata=12, path_bytes=30, yaml_nodes=0,
                                        yaml_tokens=0, raster_units=0))


def binding(**updates):
    args = dict(iid="a" * 52, listener="1" * 32, broker="2" * 64,
                channel="3" * 64, operation="4" * 64)
    args.update(updates)
    return BrokerBinding(**args)


def test_scope_matches_closed_original_input_contract():
    value = input_value()
    packet = encode_input_v3(value)
    result = derive_input_scope(packet, binding())
    expected = dict(v=1, iid=value["iid"], listener="1" * 32, operation_id="4" * 64,
                    profile="default", kind="METADATA", expected_avatar_sha=None,
                    challenge="a" * 64, epoch=1, deadline_ns=2000000000,
                    input_sha256=hashlib.sha256(packet).hexdigest())
    assert result.input_sha256 == expected["input_sha256"]
    assert result.scope_sha256 == hashlib.sha256(json.dumps(expected, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize("field,new", [
    ("challenge", "c" * 64), ("epoch", 2), ("deadline_ns", 2000000001),
    ("canonical_fallback", "Renamed"), ("source_manifest_sha", "c" * 64),
])
def test_any_original_input_change_changes_scope(field, new):
    original = input_value()
    changed = dict(original, **{field: new})
    assert derive_input_scope(encode_input_v3(original), binding()) != derive_input_scope(
        encode_input_v3(changed), binding())


def test_avatar_kind_and_expected_digest_are_bound():
    value = input_value()
    first = derive_input_scope(encode_input_v3(value), binding())
    value.update(operation="AVATAR", expected_avatar_sha="c" * 64)
    second = derive_input_scope(encode_input_v3(value), binding())
    value["expected_avatar_sha"] = "d" * 64
    third = derive_input_scope(encode_input_v3(value), binding())
    assert len({first.scope_sha256, second.scope_sha256, third.scope_sha256}) == 3


def test_cross_instance_refused_and_operation_listener_cannot_be_borrowed():
    packet = encode_input_v3(input_value())
    original = derive_input_scope(packet, binding())
    with pytest.raises(FrameError):
        derive_input_scope(packet, binding(iid="b" * 52))
    for changed in (binding(listener="5" * 32), binding(operation="6" * 64)):
        assert derive_input_scope(packet, changed).scope_sha256 != original.scope_sha256
    with pytest.raises(FrameError):
        derive_input_scope(packet + b"extra", binding())
