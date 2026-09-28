"""Guarantee derivation (GU-2: strict integer versions, floors), the GU-3 cross-check, and the
GU-4 write gate. Implemented and unit-tested; no F1 route uses the write gate (FR-053). T031.

GU-2 derives each of the four guarantee flags only from Hermes's own versioned capability map
(`gateway.platforms.base.PLATFORM_ADAPTER_CAPABILITIES`, as read by `reads.py`'s
`ReadBridge.capability_versions()`): a flag is `true` iff its key is present at or above its floor
version, where "version" means a genuine `int` — a `bool`, `str` or `float` is treated as absent
(DR-12; `bool` is a `int` subclass in Python, so it is checked and rejected explicitly). An absent
map or an absent key also gives `false`. This module never imports Hermes and never calls into the
bridge; it is pure data-in, data-out over whatever `capability_versions()` returned.

GU-3 lets a symbol-presence cross-check only ever *downgrade* a flag the capability map claimed
true (never upgrade a false one): if the relevant symbol is reported absent, the flag becomes
`false` and the inconsistency is logged. Symbol detection alone never advertises a guarantee.

GU-4 derives the write gate from `no_defer` and `atomic_anchor` alone.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .contract import (
    CAPABILITY_FLOORS,
    DIRECT_SEND_GATE_CLOSED_REASON,
    GUARANTEE_FLAGS,
    WRITE_GATE_CLOSED_REASON,
    WRITE_GATE_REQUIRED_FLAGS,
    DirectSendEndpoint,
    Guarantees,
    WriteGate,
    WriteGateState,
)

# GU-3: symbols usable only as a cross-check on a capability-map `true`, never to advertise a
# guarantee on their own. Dotted names are diagnostic only (for the higher-version/inconsistency
# log callbacks); this module never imports or resolves them.
GUARANTEE_SYMBOLS: Mapping[str, str] = {
    "no_defer": "gateway.platforms.base.defer_policy",
    "atomic_anchor": "gateway.platforms.event.AdmissionPrecondition",
}


def _is_genuine_int(value: object) -> bool:
    """A real JSON/Python integer version — not a `bool` (an `int` subclass), `str` or `float`."""
    return isinstance(value, int) and not isinstance(value, bool)


def derive_guarantees(
    capabilities: Mapping[str, object] | None,
    *,
    log_higher_version: Callable[[str, str, int], None] | None = None,
) -> Guarantees:
    """GU-2: derive the four flags from Hermes's capability map alone.

    `capabilities` is `None` or not a mapping for an absent map (every flag `false`). For each
    flag, an absent key, or a value that is not a genuine `int`, gives `false`; otherwise the flag
    is `true` iff the value is at or above its floor. `log_higher_version(flag, key, version)` is
    called whenever an accepted version exceeds its floor (GU-2: "HMP SHOULD log any version
    higher than the ones it knows").
    """
    caps = capabilities if isinstance(capabilities, Mapping) else {}
    values: dict[str, bool] = {}
    for flag in GUARANTEE_FLAGS:
        key, floor = CAPABILITY_FLOORS[flag]
        version = caps.get(key) if key in caps else None
        ok = version is not None and _is_genuine_int(version) and version >= floor
        values[flag] = ok
        if ok and version > floor and log_higher_version is not None:  # type: ignore[operator]
            log_higher_version(flag, key, version)  # type: ignore[arg-type]
    return Guarantees(**values)


def cross_check_guarantees(
    guarantees: Guarantees,
    symbol_present: Mapping[str, bool],
    *,
    log_inconsistency: Callable[[str, str], None] | None = None,
) -> Guarantees:
    """GU-3: for each flag with a known cross-check symbol, an explicit `False` in
    `symbol_present` downgrades a capability-map `true` to `false` and calls
    `log_inconsistency(flag, symbol)`. A symbol the caller did not check (absent from
    `symbol_present`) never changes anything, and a symbol reported present never upgrades a
    `false` flag: this function can only remove guarantees, never grant one.
    """
    values = {flag: getattr(guarantees, flag) for flag in GUARANTEE_FLAGS}
    for flag, symbol in GUARANTEE_SYMBOLS.items():
        if values[flag] and symbol_present.get(symbol, True) is False:
            values[flag] = False
            if log_inconsistency is not None:
                log_inconsistency(flag, symbol)
    return Guarantees(**values)


def write_gate(guarantees: Guarantees) -> WriteGate:
    """GU-4: open iff `no_defer` and `atomic_anchor` are both true."""
    if all(getattr(guarantees, flag) for flag in WRITE_GATE_REQUIRED_FLAGS):
        return WriteGate(state=WriteGateState.OPEN, reason=None)
    return WriteGate(state=WriteGateState.CLOSED, reason=WRITE_GATE_CLOSED_REASON)


def direct_send_gate(
    *,
    base_write_gate: WriteGate,
    flag_enabled: bool,
    endpoint: DirectSendEndpoint | None,
) -> WriteGate:
    """GU-4a / HMP_V1.md §7a DS-2(b): the gate for `POST .../chat/messages` only.

    If the original GU-4 gate is already `OPEN`, that state wins unchanged -- `OPEN_GUARDED` is
    never returned alongside a genuine `OPEN` (mutually exclusive by construction, §7a). No
    supported build advertises `OPEN` today, so in practice this function almost always evaluates
    the guarded branch: `OPEN_GUARDED` requires **both** the owner-dogfood host flag
    (`gateway.platforms.hmp.extra.direct_send`, default `false`) to be `true` **and** a positively
    loopback-bound, keyed `DirectSendEndpoint` to have been resolved for the target profile
    (`bridge.direct_send_endpoint`, DS-6 -- `None` on any ambiguity, by that function's own
    contract, so this function never re-derives loopback-ness itself). Anything else is `CLOSED`
    with `DIRECT_SEND_GATE_CLOSED_REASON` ("write_gate_closed"), the route-specific code ERR-2
    adds -- never the original route's `guarantees_unavailable`.
    """
    if base_write_gate.state is WriteGateState.OPEN:
        return base_write_gate
    if flag_enabled and endpoint is not None:
        return WriteGate(state=WriteGateState.OPEN_GUARDED, reason=None)
    return WriteGate(state=WriteGateState.CLOSED, reason=DIRECT_SEND_GATE_CLOSED_REASON)
