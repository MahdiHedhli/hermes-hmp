"""Native-shaped group observations do not manufacture phone authority."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from hmp_plugin.group_capabilities import InvalidGroupCapabilitiesError, parse_group_capabilities

_ERROR = "Native group capabilities unavailable."


def _payload():
    # Source-shaped sample, not a captured runtime response or native fixture pass.
    return {
        "protocol_version": 2,
        "driver": True,
        "persistent_process": True,
        "methods": [
            "groups.capabilities",
            "groups.list",
            "groups.state",
            "groups.log",
            "groups.create",
            "groups.rename",
            "groups.context",
            "groups.disband",
            "groups.send",
            "groups.attachment.upload",
            "groups.attachment.download",
            "groups.stop",
            "groups.continue",
            "groups.retry",
            "groups.discard",
            "groups.approve",
            "groups.peer.register",
            "groups.peer.invite",
            "groups.peer.revoke",
        ],
        "features": [
            "room_identity",
            "monotonic_log",
            "replayable_disband",
            "peer_renewal_horizon",
        ],
        "max_log_limit": 500,
        "authority_gateway_id": "synthetic-owner-only",
        "seatable_profiles": ["default", "helper"],
        "room_link": {"enabled": True, "catalog": {"private": "not retained"}},
    }


def _refused(value):
    with pytest.raises(InvalidGroupCapabilitiesError) as caught:
        parse_group_capabilities(value)
    assert str(caught.value) == _ERROR
    assert caught.value.args == (_ERROR,)


def test_native_shape_drops_non_observation_metadata():
    raw = _payload()
    result = parse_group_capabilities(raw)
    assert result.protocol_version == 2
    assert result.driver is True and result.persistent_process is True
    assert result.methods == frozenset(raw["methods"]) and len(result.methods) == 19
    assert result.features == frozenset(raw["features"])
    assert result.log_page_limit == 500
    assert {field.name for field in fields(result)} == {
        "protocol_version",
        "driver",
        "persistent_process",
        "methods",
        "features",
        "log_page_limit",
    }
    assert all(result.advertises(method) for method in raw["methods"])
    assert "synthetic-owner-only" not in repr(result)


@pytest.mark.parametrize(
    "driver,persistent", [(False, False), (False, True), (True, False), (True, True)]
)
def test_advertisement_and_driver_are_independent_not_authorization(driver, persistent):
    raw = _payload()
    raw["driver"] = driver
    raw["persistent_process"] = persistent
    result = parse_group_capabilities(raw)
    assert result.advertises("groups.send") is True
    assert result.advertises("groups.peer.invite") is True
    assert result.driver is driver and result.persistent_process is persistent
    for name in ("ready", "allowed", "authorized", "supported"):
        assert not hasattr(result, name)
    raw["methods"] = []
    empty = parse_group_capabilities(raw)
    assert empty.advertises("groups.send") is False


@pytest.mark.parametrize("version", [1, 77, (1 << 31) - 1])
def test_future_bounded_additions_preserve_known_fields_without_retaining_unknowns(version):
    raw = _payload()
    raw["protocol_version"] = version
    raw["methods"] += ["groups.Future-verb", "synthetic-sensitive-unknown", "groups.send"]
    raw["features"] += ["future-capability", "synthetic-sensitive-unknown", "room_identity"]
    raw["futureField"] = {"ignored": object()}
    raw["max_log_limit"] = 2000
    result = parse_group_capabilities(raw)
    assert result.protocol_version == version and result.driver is True
    assert result.advertises("groups.send") is True
    assert len(result.methods) == 19 and len(result.features) == 4
    assert "synthetic-sensitive-unknown" not in result.methods | result.features
    assert result.log_page_limit == 500


@pytest.mark.parametrize("count", [1, 7, 499, 500])
def test_lower_native_log_bound_is_preserved(count):
    raw = _payload()
    raw["max_log_limit"] = count
    assert parse_group_capabilities(raw).log_page_limit == count


@pytest.mark.parametrize(
    "name",
    [
        "protocol_version",
        "driver",
        "persistent_process",
        "methods",
        "features",
        "max_log_limit",
    ],
)
def test_missing_required_field_is_not_success_or_empty_fallback(name):
    raw = _payload()
    del raw[name]
    _refused(raw)


@pytest.mark.parametrize("name", ["protocol_version", "max_log_limit"])
@pytest.mark.parametrize("value", [True, False, 0, -1, 2**31, 2.0, "2", None])
def test_integer_fields_are_exact_positive_bounded_integers(name, value):
    raw = _payload()
    raw[name] = value
    _refused(raw)


@pytest.mark.parametrize("name", ["driver", "persistent_process"])
@pytest.mark.parametrize("value", [1, 0, "true", "false", [], {}, None])
def test_flag_fields_are_exact_booleans_not_truthiness(name, value):
    raw = _payload()
    raw[name] = value
    _refused(raw)


@pytest.mark.parametrize("name", ["methods", "features"])
@pytest.mark.parametrize(
    "value",
    [(), "groups.send", {}, None, [None], [True], [1], [""], ["x" * 81], ["non-ascii-\u00e9"]],
)
def test_token_containers_and_elements_are_bounded_plain_json(name, value):
    raw = _payload()
    raw[name] = value
    _refused(raw)


@pytest.mark.parametrize("name,limit", [("methods", 128), ("features", 32)])
def test_list_limit_counts_unknown_and_duplicate_tokens_before_normalizing(name, limit):
    raw = _payload()
    raw[name] = ["unknown"] * limit
    parsed = parse_group_capabilities(raw)
    assert getattr(parsed, name) == frozenset()
    raw[name].append("unknown")
    _refused(raw)


def test_key_count_and_length_bound_unknown_metadata_before_lookup():
    raw = _payload()
    raw.update({"extra" + str(i): None for i in range(64 - len(raw))})
    assert parse_group_capabilities(raw).driver is True
    raw["overflow"] = None
    _refused(raw)
    for key in ("", "x" * 129):
        raw = _payload()
        raw[key] = None
        _refused(raw)


def test_custom_key_is_refused_before_its_lookup_equality_can_execute():
    calls = []

    class ForeignKey:
        def __hash__(self):
            return hash("driver")

        def __eq__(self, other):
            calls.append(True)
            raise AssertionError("key equality must not execute")

    raw = _payload()
    del raw["driver"]
    raw[ForeignKey()] = True
    _refused(raw)
    assert calls == []


def test_ignored_values_are_not_inspected_or_retained():
    class ForeignValue:
        def __repr__(self):
            raise AssertionError("repr must not execute")

        def __str__(self):
            raise AssertionError("str must not execute")

    raw = _payload()
    ignored = ForeignValue()
    for key in ("authority_gateway_id", "seatable_profiles", "room_link", "unknown"):
        raw[key] = ignored
    result = parse_group_capabilities(raw)
    assert all(getattr(result, f.name) is not ignored for f in fields(result))
    assert result.driver is True


def test_no_input_mutation_no_result_aliases_and_frozen_result():
    raw = _payload()
    expected_methods, expected_features = list(raw["methods"]), list(raw["features"])
    result = parse_group_capabilities(raw)
    assert raw["methods"] == expected_methods and raw["features"] == expected_features
    raw["methods"].clear()
    raw["features"].clear()
    raw["driver"] = False
    assert result.driver is True and len(result.methods) == 19 and len(result.features) == 4
    with pytest.raises(FrozenInstanceError):
        result.driver = False


def test_foreign_containers_and_queries_do_not_execute_user_callbacks():
    class ForeignDict(dict):
        def __len__(self):
            raise AssertionError("foreign len must not execute")

    class ForeignList(list):
        def __len__(self):
            raise AssertionError("foreign len must not execute")

    class ForeignString(str):
        def __hash__(self):
            raise AssertionError("foreign hash must not execute")

    _refused(ForeignDict())
    for name in ("methods", "features"):
        raw = _payload()
        raw[name] = ForeignList()
        _refused(raw)
        raw[name] = [ForeignString("groups.send")]
        _refused(raw)
    result = parse_group_capabilities(_payload())
    for method in (ForeignString("groups.send"), object(), "groups.unknown", "x" * 81):
        with pytest.raises(InvalidGroupCapabilitiesError) as caught:
            result.advertises(method)
        assert str(caught.value) == _ERROR


@pytest.mark.parametrize("value", [None, [], (), "native-result", False, 2, object()])
def test_non_object_top_level_is_refused(value):
    _refused(value)


def test_integer_subclass_cannot_run_comparison_or_conversion():
    class ForeignInteger(int):
        def __le__(self, other):
            raise AssertionError("comparison must not execute")

        def __ge__(self, other):
            raise AssertionError("comparison must not execute")

        def __int__(self):
            raise AssertionError("conversion must not execute")

    for key in ("protocol_version", "max_log_limit"):
        raw = _payload()
        raw[key] = ForeignInteger(2)
        _refused(raw)
