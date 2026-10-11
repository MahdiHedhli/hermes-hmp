"""GU-2 derivation, GU-3 cross-check and GU-4 write gate (T031)."""

from __future__ import annotations

import pytest

from hmp_plugin.contract import (
    CAPABILITY_FLOORS,
    DIRECT_SEND_GATE_CLOSED_REASON,
    GUARANTEE_FLAGS,
    DirectSendEndpoint,
    Guarantees,
    WriteGate,
    WriteGateState,
)
from hmp_plugin.gate import cross_check_guarantees, derive_guarantees, direct_send_gate, write_gate

ALL_TRUE_CAPS = dict(CAPABILITY_FLOORS.values())


def test_absent_map_is_every_flag_false() -> None:
    g = derive_guarantees(None)
    assert g == Guarantees()


def test_empty_map_is_every_flag_false() -> None:
    assert derive_guarantees({}) == Guarantees()


@pytest.mark.parametrize("flag", GUARANTEE_FLAGS)
def test_floor_boundaries_per_flag(flag: str) -> None:
    key, floor = CAPABILITY_FLOORS[flag]

    below = derive_guarantees({key: floor - 1})
    at = derive_guarantees({key: floor})
    above = derive_guarantees({key: floor + 1})

    assert getattr(below, flag) is False
    assert getattr(at, flag) is True
    assert getattr(above, flag) is True
    # every other flag stays false: each key only ever affects its own flag
    for other in GUARANTEE_FLAGS:
        if other != flag:
            assert getattr(at, other) is False


@pytest.mark.parametrize("flag", GUARANTEE_FLAGS)
@pytest.mark.parametrize("bad_version", [True, False, "1", "2", 1.0, 2.5, None, [], {}])
def test_non_genuine_int_versions_are_absent(flag: str, bad_version: object) -> None:
    key, _floor = CAPABILITY_FLOORS[flag]
    g = derive_guarantees({key: bad_version})
    assert getattr(g, flag) is False


def test_bool_true_is_not_floor_one() -> None:
    # A version of exactly `True` must not satisfy a floor of 1 just because `True == 1`.
    key, floor = CAPABILITY_FLOORS["no_defer"]
    assert floor == 1
    g = derive_guarantees({key: True})
    assert g.no_defer is False


def test_all_floors_met_sets_every_flag() -> None:
    g = derive_guarantees(ALL_TRUE_CAPS)
    assert g == Guarantees(
        no_defer=True, atomic_anchor=True, approval_request_id=True, confirmed_settle=True
    )


def test_non_mapping_capabilities_is_absent() -> None:
    assert derive_guarantees("not-a-mapping") == Guarantees()  # type: ignore[arg-type]


def test_log_higher_version_called_only_when_above_floor() -> None:
    key, floor = CAPABILITY_FLOORS["no_defer"]
    calls: list[tuple[str, str, int]] = []
    derive_guarantees({key: floor}, log_higher_version=lambda *a: calls.append(a))
    assert calls == []
    derive_guarantees({key: floor + 3}, log_higher_version=lambda *a: calls.append(a))
    assert calls == [("no_defer", key, floor + 3)]


def test_log_higher_version_not_called_when_flag_false() -> None:
    key, floor = CAPABILITY_FLOORS["no_defer"]
    calls: list[tuple[str, str, int]] = []
    derive_guarantees({key: floor - 1}, log_higher_version=lambda *a: calls.append(a))
    assert calls == []


# --------------------------------------------------------------------------------------------
# GU-3: symbol cross-check downgrades only, never upgrades
# --------------------------------------------------------------------------------------------


def test_cross_check_downgrades_true_to_false_on_absent_symbol() -> None:
    g = Guarantees(no_defer=True, atomic_anchor=True)
    out = cross_check_guarantees(g, {"gateway.platforms.base.defer_policy": False})
    assert out.no_defer is False
    assert out.atomic_anchor is True  # untouched: its own symbol wasn't checked False


def test_cross_check_logs_inconsistency() -> None:
    g = Guarantees(no_defer=True)
    calls: list[tuple[str, str]] = []
    cross_check_guarantees(
        g,
        {"gateway.platforms.base.defer_policy": False},
        log_inconsistency=lambda *a: calls.append(a),
    )
    assert calls == [("no_defer", "gateway.platforms.base.defer_policy")]


def test_cross_check_never_upgrades_a_false_flag() -> None:
    g = Guarantees(no_defer=False)
    out = cross_check_guarantees(g, {"gateway.platforms.base.defer_policy": True})
    assert out.no_defer is False


def test_cross_check_unchecked_symbol_is_a_no_op() -> None:
    g = Guarantees(no_defer=True, atomic_anchor=True, approval_request_id=True)
    out = cross_check_guarantees(g, {})  # caller checked nothing
    assert out == g


# --------------------------------------------------------------------------------------------
# GU-4: write gate
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("no_defer", "atomic_anchor", "expected_open"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_write_gate_state(no_defer: bool, atomic_anchor: bool, expected_open: bool) -> None:
    g = Guarantees(no_defer=no_defer, atomic_anchor=atomic_anchor)
    wg = write_gate(g)
    if expected_open:
        assert wg.state is WriteGateState.OPEN
        assert wg.reason is None
    else:
        assert wg.state is WriteGateState.CLOSED
        assert wg.reason == "guarantees_unavailable"


def test_write_gate_ignores_the_other_two_flags() -> None:
    open_regardless = write_gate(
        Guarantees(
            no_defer=True,
            atomic_anchor=True,
            approval_request_id=False,
            confirmed_settle=False,
        )
    )
    assert open_regardless.state is WriteGateState.OPEN


# ------------------------------------------------------------------------------------------------
# GU-4a / HMP_V1.md §7a DS-2(b): the direct-send route's own gate (amendment F2)
# ------------------------------------------------------------------------------------------------

CLOSED = WriteGate(state=WriteGateState.CLOSED, reason="guarantees_unavailable")
OPEN = WriteGate(state=WriteGateState.OPEN, reason=None)
AN_ENDPOINT = DirectSendEndpoint(host="127.0.0.1", port=8642, api_key="k" * 20, path_prefix="")


def test_direct_send_gate_open_requires_owner_switch_and_endpoint() -> None:
    """A full Hermes guarantee cannot bypass this route's owner switch or loopback key."""
    result = direct_send_gate(base_write_gate=OPEN, flag_enabled=True, endpoint=AN_ENDPOINT)
    assert result is OPEN
    assert result.state is WriteGateState.OPEN
    assert direct_send_gate(
        base_write_gate=OPEN, flag_enabled=False, endpoint=AN_ENDPOINT
    ).state is WriteGateState.CLOSED
    assert direct_send_gate(
        base_write_gate=OPEN, flag_enabled=True, endpoint=None
    ).state is WriteGateState.CLOSED


def test_direct_send_gate_guarded_requires_both_flag_and_endpoint() -> None:
    assert direct_send_gate(
        base_write_gate=CLOSED, flag_enabled=True, endpoint=AN_ENDPOINT
    ).state is WriteGateState.OPEN_GUARDED

    flag_off = direct_send_gate(base_write_gate=CLOSED, flag_enabled=False, endpoint=AN_ENDPOINT)
    assert flag_off.state is WriteGateState.CLOSED
    assert flag_off.reason == DIRECT_SEND_GATE_CLOSED_REASON

    no_endpoint = direct_send_gate(base_write_gate=CLOSED, flag_enabled=True, endpoint=None)
    assert no_endpoint.state is WriteGateState.CLOSED
    assert no_endpoint.reason == DIRECT_SEND_GATE_CLOSED_REASON

    neither = direct_send_gate(base_write_gate=CLOSED, flag_enabled=False, endpoint=None)
    assert neither.state is WriteGateState.CLOSED


def test_direct_send_gate_closed_reason_is_route_specific() -> None:
    """`write_gate_closed`, never the original route's `guarantees_unavailable` (ERR-2 addition)."""
    result = direct_send_gate(base_write_gate=CLOSED, flag_enabled=False, endpoint=None)
    assert result.reason == "write_gate_closed"
    assert result.reason != CLOSED.reason
