"""The process-local image ref registry (LM-9): causal guards, not a mirror of the code."""

from __future__ import annotations

import ast
import base64
import dataclasses
import pickle
import re
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import local_media_registry as reg
from hmp_plugin.local_media_registry import (
    Binding,
    Caller,
    FirstServe,
    LocalMediaRegistry,
    RegistryRefusal,
    SessionKind,
)

REF_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
D1 = b"\x01" * 32
D2 = b"\x02" * 32


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Rand:
    """Distinct, deterministic 32-byte values."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self, size: int) -> bytes:
        self.n += 1
        return self.n.to_bytes(size, "big")


def caller(**kw: str) -> Caller:
    base = {"device_id": "dev-a", "user_id": "usr-a", "instance_id": "ins-a", "profile": "prof-a"}
    return Caller(**{**base, **kw})


def binding(**kw: object) -> Binding:
    base: dict[str, object] = {
        "device_id": "dev-a",
        "user_id": "usr-a",
        "instance_id": "ins-a",
        "profile": "prof-a",
        "kind": SessionKind.BOT_CHAT,
        "session_id": "sess-1",
        "tip": "tip-1",
        "tool_row_id": 7,
        "raw_digest": b"\xaa" * 32,
    }
    return Binding(**{**base, **kw})  # type: ignore[arg-type]


def make(
    clock: Clock | None = None, ttl: float = 1800, per_device: int = 512, total: int = 4096
) -> tuple[LocalMediaRegistry, Clock]:
    clock = clock or Clock()
    return (
        LocalMediaRegistry(
            _clock=clock, _random=Rand(), _limits=reg._Limits(ttl, per_device, total)
        ),
        clock,
    )


# --- defaults ---------------------------------------------------------------------------------


def test_production_constants_are_pinned() -> None:
    assert (reg.MEDIA_REF_TTL_S, reg.MAX_REFS_PER_DEVICE, reg.MAX_REFS_TOTAL) == (1800, 512, 4096)
    limits = reg._Limits()
    assert (limits.ttl_s, limits.per_device, limits.total) == (1800, 512, 4096)
    assert LocalMediaRegistry()._limits == limits


@pytest.mark.parametrize(
    "bad",
    [
        {"ttl_s": 1801},
        {"ttl_s": 0},
        {"per_device": 513},
        {"per_device": 0},
        {"total": 4097},
        {"total": 0},
    ],
)
def test_test_seams_can_only_lower_limits(bad: dict[str, float]) -> None:
    with pytest.raises(RegistryRefusal):
        reg._Limits(**bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [
        {"ttl_s": True},
        {"ttl_s": float("nan")},
        {"ttl_s": float("inf")},
        {"ttl_s": "1"},
        {"per_device": True},
        {"per_device": 1.0},
        {"total": True},
        {"total": 5.0},
    ],
)
def test_limits_reject_non_genuine_numbers(bad: dict[str, object]) -> None:
    with pytest.raises(RegistryRefusal):
        reg._Limits(**bad)  # type: ignore[arg-type]


def test_limits_accept_lower_int_and_float_ttl() -> None:
    limits = reg._Limits(0.5, 1, 1)
    assert (limits.ttl_s, limits.per_device, limits.total) == (0.5, 1, 1)


def test_limits_seam_must_be_a_genuine_limits_object() -> None:
    class Duck:
        ttl_s, per_device, total = 1e9, 10**6, 10**6

    class Sub(reg._Limits):
        pass

    for bad in (Duck(), SimpleNamespace(ttl_s=1e9, per_device=10**6, total=10**6), 5, "x"):
        with pytest.raises(RegistryRefusal):
            LocalMediaRegistry(_limits=bad)  # type: ignore[arg-type]
    with pytest.raises(RegistryRefusal):
        LocalMediaRegistry(_limits=Sub())
    # A raised-cap duck object cannot enlarge the registry: the cap stays at production.
    assert LocalMediaRegistry(_limits=None)._limits == reg._Limits()


def test_non_callable_clock_or_random_seam_is_refused() -> None:
    with pytest.raises(RegistryRefusal):
        LocalMediaRegistry(_clock=5)  # type: ignore[arg-type]
    with pytest.raises(RegistryRefusal):
        LocalMediaRegistry(_random=b"x")  # type: ignore[arg-type]


def test_real_default_clock_and_random_are_the_production_sources() -> None:
    import secrets
    import time

    r = LocalMediaRegistry()
    assert r._clock is time.monotonic
    assert r._random is secrets.token_bytes
    assert reg.token_bytes is secrets.token_bytes


def test_real_default_refs_are_fresh_43_char_base64url() -> None:
    r = LocalMediaRegistry()
    refs = {r.mint(binding(tool_row_id=i)) for i in range(50)}
    assert len(refs) == 50
    assert all(REF_RE.match(x) for x in refs)


def test_ref_encodes_exactly_the_32_random_bytes() -> None:
    r = LocalMediaRegistry(_random=lambda n: b"\xfb" * n)
    ref = r.mint(binding())
    assert base64.urlsafe_b64decode(ref + "=") == b"\xfb" * 32
    assert "=" not in ref and len(ref) == 43


def test_random_source_returning_wrong_size_or_repeating_is_refused() -> None:
    with pytest.raises(RegistryRefusal):
        LocalMediaRegistry(_random=lambda n: b"x" * 5).mint(binding())
    r = LocalMediaRegistry(_random=lambda n: b"\x07" * n)
    r.mint(binding())
    with pytest.raises(RegistryRefusal):  # collision with a live ref is never reused
        r.mint(binding(tool_row_id=8))
    assert r._audit() == 1


# --- binding / lookup separation --------------------------------------------------------------


def test_lookup_returns_binding_tip_and_row_digest_for_native_checks() -> None:
    r, clock = make()
    b = binding(kind=SessionKind.PHONE, tip="tip-9", tool_row_id=3, raw_digest=b"\x09" * 32)
    snap = r.lookup(r.mint(b), caller())
    assert snap is not None
    assert snap.binding == b
    assert (snap.binding.kind, snap.binding.tip, snap.binding.tool_row_id) == (
        SessionKind.PHONE,
        "tip-9",
        3,
    )
    assert snap.binding.raw_digest == b"\x09" * 32
    assert snap.minted_at == clock.now and snap.first_served is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.first_served = D1  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.binding.tip = "x"  # type: ignore[misc]


@pytest.mark.parametrize("field", ["device_id", "user_id", "instance_id", "profile"])
def test_each_caller_dimension_separates_entries(field: str) -> None:
    r, _ = make()
    ref = r.mint(binding())
    assert r.lookup(ref, caller()) is not None
    assert r.lookup(ref, caller(**{field: "other"})) is None
    assert r.lookup(ref, caller()) is not None  # a wrong caller did not delete it


@pytest.mark.parametrize("field", ["device_id", "user_id", "instance_id", "profile"])
def test_bindings_differing_in_one_dimension_get_distinct_refs(field: str) -> None:
    r, _ = make()
    assert r.mint(binding()) != r.mint(binding(**{field: "other"}))


@pytest.mark.parametrize(
    "change",
    [
        {"kind": SessionKind.PHONE},
        {"session_id": "s2"},
        {"tip": "t2"},
        {"tool_row_id": 8},
        {"raw_digest": b"\xbb" * 32},
    ],
)
def test_bindings_differing_in_any_other_field_get_distinct_refs(change: dict[str, object]) -> None:
    r, _ = make()
    assert r.mint(binding()) != r.mint(binding(**change))


def test_every_refusal_is_the_same_none() -> None:
    r, clock = make(per_device=1)
    live = r.mint(binding(tool_row_id=1))
    evicted = r.mint(binding(tool_row_id=2))  # evicts `live`
    expiring = r.mint(binding(tool_row_id=3, device_id="dev-b"))
    clock.now += 1800
    cases = [
        (live, caller()),  # evicted
        (expiring, caller(device_id="dev-b")),  # expired
        (evicted, caller()),  # expired too
        ("A" * 43, caller()),  # unknown
        ("A" * 42, caller()),  # bad grammar
        ("A" * 44, caller()),
        ("A" * 42 + "=", caller()),
        ("A" * 42 + "+", caller()),
        ("A" * 42 + "\n", caller()),
        ("", caller()),
        (None, caller()),
        (b"A" * 43, caller()),
        (123, caller()),
    ]
    results = [r.lookup(ref, c) for ref, c in cases]
    assert results == [None] * len(cases)
    assert all(x is None for x in results)


def test_foreign_caller_and_unknown_ref_are_indistinguishable_in_effect() -> None:
    r, _ = make()
    ref = r.mint(binding())
    assert r.lookup(ref, caller(profile="x")) is r.lookup("B" * 43, caller()) is None


def test_bad_grammar_never_reaches_the_entries() -> None:
    r, _ = make()
    r.mint(binding())
    before = dict(r._entries)
    assert r.lookup("%" * 43, caller()) is None
    assert r._entries == before


# --- TTL --------------------------------------------------------------------------------------


def test_ttl_boundary_live_just_before_expired_at_exactly_ttl() -> None:
    r, clock = make()
    ref = r.mint(binding())
    clock.now += 1799.999
    assert r.lookup(ref, caller()) is not None
    clock.now += 0.001
    assert r.lookup(ref, caller()) is None
    assert r._audit() == 0


def test_lookup_and_idempotent_mint_never_extend_ttl() -> None:
    r, clock = make()
    b = binding()
    ref = r.mint(b)
    clock.now += 1000
    assert r.lookup(ref, caller()) is not None
    assert r.mint(b) == ref
    clock.now += 799  # 1799 after the one real mint
    assert r.lookup(ref, caller()) is not None
    clock.now += 1
    assert r.lookup(ref, caller()) is None
    assert r.mint(b) != ref  # a fresh ref, a fresh TTL
    assert r._audit() == 1


def test_idempotent_mint_returns_same_ref_and_keeps_mint_time() -> None:
    r, clock = make()
    b = binding()
    ref = r.mint(b)
    t0 = clock.now
    clock.now += 500
    assert r.mint(b) == ref
    snap = r.lookup(ref, caller())
    assert snap is not None and snap.minted_at == t0
    assert r._audit() == 1


def test_expired_entries_are_swept_at_mint_and_indexes_stay_consistent() -> None:
    r, clock = make()
    for i in range(10):
        r.mint(binding(tool_row_id=i, device_id=f"d{i % 3}"))
    clock.now += 1800
    r.mint(binding(tool_row_id=99))
    assert r._audit() == 1
    assert len(r._by_binding) == 1 and set(r._device_lru) == {"dev-a"}


def test_a_clock_that_steps_back_cannot_revive_an_entry() -> None:
    r, clock = make()
    ref = r.mint(binding())
    clock.now += 1800
    assert r.lookup(ref, caller()) is None
    ref2 = r.mint(binding())
    clock.now -= 5000
    assert r.lookup(ref2, caller()) is not None
    clock.now += 4999
    assert r.lookup(ref2, caller()) is not None  # time never ran backward for the registry


def test_clock_clamp_alone_keeps_an_expired_entry_expired() -> None:
    r, clock = make()
    ref_a = r.mint(binding(tool_row_id=1))  # minted at 1000
    clock.now = 2800
    assert r.lookup("B" * 43, caller()) is None  # a lookup of another ref moves registry time
    clock.now = 1500  # the raw clock steps back to when A would still be live
    assert r.lookup(ref_a, caller()) is None  # never read at 2800: only the clamp expires it
    assert r._audit() == 0


@pytest.mark.parametrize(
    "bad", [float("nan"), float("inf"), float("-inf"), True, None, "5", b"5", object()]
)
def test_non_finite_or_non_numeric_clock_values_are_refused(bad: object) -> None:
    r = LocalMediaRegistry(_clock=lambda: bad, _random=Rand())  # type: ignore[arg-type,return-value]
    with pytest.raises(RegistryRefusal):
        r.mint(binding())
    assert r._audit() == 0


def test_a_nan_clock_cannot_make_a_permanent_entry() -> None:
    values = iter([1000.0, float("nan"), 5000.0])
    r = LocalMediaRegistry(_clock=lambda: next(values), _random=Rand())
    ref = r.mint(binding())
    with pytest.raises(RegistryRefusal):
        r.lookup(ref, caller())
    assert r.lookup(ref, caller()) is None  # real time 5000 expires it; NaN did not poison it


def test_seam_exceptions_become_content_free_refusals() -> None:
    def bad_clock() -> float:
        raise ValueError("SECRET-CLOCK-TEXT")

    def bad_random(n: int) -> bytes:
        raise OSError("SECRET-RANDOM-TEXT")

    for r, call in (
        (LocalMediaRegistry(_clock=bad_clock), lambda r: r.mint(binding())),
        (LocalMediaRegistry(_random=bad_random), lambda r: r.mint(binding())),
    ):
        with pytest.raises(RegistryRefusal) as info:
            call(r)
        exc = info.value
        assert exc.args == ("local media registry refused",)
        assert exc.__context__ is None and exc.__cause__ is None
        assert "SECRET" not in repr(exc) + str(exc)
        assert not r._lock.locked()


def test_field_bound_is_256_accept_257_refuse() -> None:
    assert reg.MAX_FIELD_CHARS == 256
    names = ("device_id", "user_id", "instance_id", "profile", "session_id", "tip")
    for name in names:
        assert getattr(binding(**{name: "x" * 256}), name) == "x" * 256
        with pytest.raises(RegistryRefusal):
            binding(**{name: "x" * 257})
    for name in ("device_id", "user_id", "instance_id", "profile"):
        caller(**{name: "x" * 256})
        with pytest.raises(RegistryRefusal):
            caller(**{name: "x" * 257})


# --- capacity / LRU ---------------------------------------------------------------------------


def test_per_device_cap_evicts_that_devices_lru_only() -> None:
    r, _ = make(per_device=3, total=100)
    other = r.mint(binding(device_id="dev-b", tool_row_id=0))
    refs = [r.mint(binding(tool_row_id=i)) for i in range(3)]
    assert r.lookup(refs[0], caller()) is not None  # refs[1] is now the device's LRU
    new = r.mint(binding(tool_row_id=50))
    assert r.lookup(refs[1], caller()) is None
    for kept in (refs[0], refs[2], new):
        assert r.lookup(kept, caller()) is not None
    assert r.lookup(other, caller(device_id="dev-b")) is not None
    assert r._audit() == 4  # three for dev-a, one for dev-b


def test_total_cap_evicts_global_lru_across_devices() -> None:
    r, _ = make(per_device=10, total=4)
    refs = [r.mint(binding(device_id=f"d{i}", tool_row_id=i)) for i in range(4)]
    assert r.lookup(refs[0], caller(device_id="d0")) is not None  # refs[1] is the global LRU
    new = r.mint(binding(device_id="d9", tool_row_id=9))
    assert r.lookup(refs[1], caller(device_id="d1")) is None
    for i in (0, 2, 3):
        assert r.lookup(refs[i], caller(device_id=f"d{i}")) is not None
    assert r.lookup(new, caller(device_id="d9")) is not None
    assert r._audit() == 4
    assert "d1" not in r._device_lru


def test_idempotent_mint_counts_as_use_but_does_not_grow() -> None:
    r, _ = make(per_device=2)
    b0, b1 = binding(tool_row_id=0), binding(tool_row_id=1)
    ref0, ref1 = r.mint(b0), r.mint(b1)
    assert r.mint(b0) == ref0  # ref1 is now LRU
    r.mint(binding(tool_row_id=2))
    assert r.lookup(ref1, caller()) is None
    assert r.lookup(ref0, caller()) is not None
    assert r._audit() == 2


def test_evicted_binding_mints_a_new_ref_not_the_old_one() -> None:
    r, _ = make(per_device=1)
    b0 = binding(tool_row_id=0)
    old = r.mint(b0)
    r.mint(binding(tool_row_id=1))
    assert b0 not in r._by_binding
    assert r.mint(b0) != old
    assert r.lookup(old, caller()) is None


def test_production_caps_hold_at_the_edges() -> None:
    r = LocalMediaRegistry(_random=Rand())
    first = r.mint(binding(tool_row_id=0))
    for i in range(1, 512):
        r.mint(binding(tool_row_id=i))
    assert r.lookup(first, caller()) is not None  # 512 fit; this made `first` most recent
    r.mint(binding(tool_row_id=512))  # 513th evicts the LRU, not `first`
    assert r._audit() == 512
    assert r.lookup(first, caller()) is not None
    for d in range(1, 8):
        for i in range(512):
            r.mint(binding(device_id=f"d{d}", tool_row_id=i))
    assert r._audit() == 4096
    r.mint(binding(device_id="d8", tool_row_id=0))
    assert r._audit() == 4096


# --- first-served CAS -------------------------------------------------------------------------


def snap_of(r: LocalMediaRegistry, ref: str, c: Caller | None = None):
    s = r.lookup(ref, c or caller())
    assert s is not None
    return s


def test_cas_sets_if_absent_then_permits_same_digest() -> None:
    r, _ = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.RECORDED
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.UNCHANGED
    assert snap_of(r, ref).first_served == D1
    assert s.first_served is None  # the old snapshot is a copy, not a live view


def test_cas_different_digest_deletes_entry_and_refuses() -> None:
    r, _ = make()
    b = binding()
    ref = r.mint(b)
    s = snap_of(r, ref)
    r.record_first_served(ref, s, caller(), D1)
    assert r.record_first_served(ref, s, caller(), D2) is FirstServe.REFUSED
    assert r.lookup(ref, caller()) is None
    assert r._audit() == 0
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.REFUSED  # stays gone
    assert r.mint(b) != ref


def test_cas_refuses_an_expired_snapshot() -> None:
    r, clock = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    clock.now += 1800
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.REFUSED
    assert r._audit() == 0


def test_cas_refuses_after_eviction() -> None:
    r, _ = make(per_device=1)
    ref = r.mint(binding(tool_row_id=0))
    s = snap_of(r, ref)
    r.mint(binding(tool_row_id=1))
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.REFUSED


def test_cas_refuses_a_replacement_entry_and_leaves_it_alone() -> None:
    # Same binding re-minted after expiry (new ref), and a forced same-ref replacement.
    r, clock = make()
    b = binding()
    ref = r.mint(b)
    s = snap_of(r, ref)
    clock.now += 1800
    new = r.mint(b)
    assert r.record_first_served(new, s, caller(), D1) is FirstServe.REFUSED  # stale snapshot
    assert r.lookup(new, caller()) is not None  # the replacement survived
    assert snap_of(r, new).first_served is None
    # Same ref string, different stored entry:
    r2 = LocalMediaRegistry(_clock=clock, _random=lambda n: b"\x05" * n)
    ref_a = r2.mint(b)
    sa = snap_of(r2, ref_a)
    clock.now += 1800
    ref_b = r2.mint(b)
    assert ref_a == ref_b
    assert r2.record_first_served(ref_a, sa, caller(), D1) is FirstServe.REFUSED
    assert snap_of(r2, ref_b).first_served is None


def test_cas_snapshot_from_another_registry_or_ref_is_refused() -> None:
    r, _ = make()
    other, _ = make()
    ref = r.mint(binding())
    ref2 = r.mint(binding(tool_row_id=2))
    oref = other.mint(binding())
    assert r.record_first_served(ref, snap_of(other, oref), caller(), D1) is FirstServe.REFUSED
    assert r.record_first_served(ref, snap_of(r, ref2), caller(), D1) is FirstServe.REFUSED
    assert snap_of(r, ref).first_served is None and snap_of(r, ref2).first_served is None


def test_cas_refuses_a_copied_snapshot_with_a_forged_binding_and_reused_token() -> None:
    r, _ = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    forged = dataclasses.replace(s, binding=binding(tool_row_id=99, tip="forged"))
    assert forged._token is s._token
    assert r.record_first_served(ref, forged, caller(), D1) is FirstServe.REFUSED
    assert snap_of(r, ref).first_served is None
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.RECORDED  # genuine passes


def _recorded(r: LocalMediaRegistry, b: Binding | None = None) -> tuple[str, object]:
    ref = r.mint(b or binding())
    s = snap_of(r, ref)
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.RECORDED
    return ref, s


def _assert_d1_unchanged(r: LocalMediaRegistry, ref: str, s: object) -> None:
    assert snap_of(r, ref).first_served == D1
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.UNCHANGED  # type: ignore[arg-type]
    assert r._audit() >= 1


def test_foreign_snapshot_cannot_delete_a_recorded_entry_by_offering_d2() -> None:
    r, clock = make()
    ref, s = _recorded(r)
    # (a) another ref's snapshot (same registry), both fresh and with its own D1 recorded
    ref2 = r.mint(binding(tool_row_id=2))
    s2 = snap_of(r, ref2)
    assert r.record_first_served(ref, s2, caller(), D2) is FirstServe.REFUSED
    r.record_first_served(ref2, s2, caller(), D1)
    assert r.record_first_served(ref, snap_of(r, ref2), caller(), D2) is FirstServe.REFUSED
    _assert_d1_unchanged(r, ref, s)
    assert snap_of(r, ref2).first_served == D1
    # (b) another registry's snapshot
    other, _ = make()
    oref = other.mint(binding())
    assert r.record_first_served(ref, snap_of(other, oref), caller(), D2) is FirstServe.REFUSED
    _assert_d1_unchanged(r, ref, s)
    # (c) a stale snapshot of a replaced entry that shares the ref string
    r3 = LocalMediaRegistry(_clock=clock, _random=lambda n: b"\x05" * n)
    b = binding()
    ref_a = r3.mint(b)
    stale = snap_of(r3, ref_a)
    clock.now += 1800
    ref_b = r3.mint(b)
    assert ref_a == ref_b
    live = snap_of(r3, ref_b)
    assert r3.record_first_served(ref_b, live, caller(), D1) is FirstServe.RECORDED
    assert r3.record_first_served(ref_b, stale, caller(), D2) is FirstServe.REFUSED
    _assert_d1_unchanged(r3, ref_b, live)


@pytest.mark.parametrize("field", ["device_id", "user_id", "instance_id", "profile"])
def test_foreign_caller_cannot_delete_a_recorded_entry_by_offering_d2(field: str) -> None:
    r, _ = make()
    ref, s = _recorded(r)
    assert r.record_first_served(ref, s, caller(**{field: "x"}), D2) is FirstServe.REFUSED
    assert r.lookup(ref, caller(**{field: "x"})) is None
    _assert_d1_unchanged(r, ref, s)


@pytest.mark.parametrize("field", ["device_id", "user_id", "instance_id", "profile"])
def test_foreign_caller_with_a_foreign_snapshot_cannot_delete_either(field: str) -> None:
    r, _ = make()
    ref, s = _recorded(r)
    ref2 = r.mint(binding(tool_row_id=2))
    assert (
        r.record_first_served(ref, snap_of(r, ref2), caller(**{field: "x"}), D2)
        is FirstServe.REFUSED
    )
    _assert_d1_unchanged(r, ref, s)


@pytest.mark.parametrize("field", ["device_id", "user_id", "instance_id", "profile"])
def test_cas_rechecks_caller_context_without_deleting(field: str) -> None:
    r, _ = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    assert r.record_first_served(ref, s, caller(**{field: "x"}), D1) is FirstServe.REFUSED
    assert snap_of(r, ref).first_served is None
    assert r.record_first_served(ref, s, caller(), D1) is FirstServe.RECORDED


@pytest.mark.parametrize("digest", [b"", b"\x01" * 31, b"\x01" * 33, "x" * 32, None, bytearray(32)])
def test_cas_bad_digest_refuses_and_changes_nothing(digest: object) -> None:
    r, _ = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    assert r.record_first_served(ref, s, caller(), digest) is FirstServe.REFUSED  # type: ignore[arg-type]
    assert snap_of(r, ref).first_served is None


def test_cas_bad_ref_or_snapshot_refuses() -> None:
    r, _ = make()
    ref = r.mint(binding())
    s = snap_of(r, ref)
    for bad in ("short", None, ref + "A", 5):
        assert r.record_first_served(bad, s, caller(), D1) is FirstServe.REFUSED
    assert r.record_first_served(ref, None, caller(), D1) is FirstServe.REFUSED  # type: ignore[arg-type]
    assert snap_of(r, ref).first_served is None


def test_idempotent_mint_keeps_the_first_served_digest() -> None:
    r, _ = make()
    b = binding()
    ref = r.mint(b)
    r.record_first_served(ref, snap_of(r, ref), caller(), D1)
    assert r.mint(b) == ref
    assert snap_of(r, ref).first_served == D1


def _race(r: LocalMediaRegistry, ref: str) -> list[tuple[bytes, FirstServe]]:
    snaps = [snap_of(r, ref) for _ in range(8)]
    digests = [bytes([i]) * 32 for i in range(8)]
    start = threading.Barrier(8)
    results: list[tuple[bytes, FirstServe]] = []
    guard = threading.Lock()

    def worker(i: int) -> None:
        start.wait()
        out = r.record_first_served(ref, snaps[i], caller(), digests[i])
        with guard:
            results.append((digests[i], out))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_competing_threads_serve_at_most_one_distinct_digest() -> None:
    for _ in range(50):
        r = LocalMediaRegistry()
        ref = r.mint(binding())
        results = _race(r, ref)
        served = {d for d, out in results if out is not FirstServe.REFUSED}
        assert len(served) <= 1
        assert len(results) == 8
        # Exactly one thread recorded; the entry is gone because a loser deleted it.
        assert [o for _, o in results].count(FirstServe.RECORDED) == 1
        assert r.lookup(ref, caller()) is None
        assert r._audit() == 0


def test_threads_hammering_mint_lookup_keep_indexes_consistent() -> None:
    r = LocalMediaRegistry(_limits=reg._Limits(1800, 20, 50))
    errors: list[BaseException] = []

    def work(n: int) -> None:
        try:
            for i in range(300):
                b = binding(device_id=f"d{n % 4}", tool_row_id=i % 40)
                ref = r.mint(b)
                r.lookup(ref, caller(device_id=f"d{n % 4}"))
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert r._audit() <= 50


# --- no leaks ---------------------------------------------------------------------------------

SECRETS = ["SECRET-DEVICE", "SECRET-USER", "SECRET-INSTANCE", "SECRET-PROFILE", "SECRET-SESSION"]


def _secret_binding() -> Binding:
    return binding(
        device_id=SECRETS[0],
        user_id=SECRETS[1],
        instance_id=SECRETS[2],
        profile=SECRETS[3],
        session_id=SECRETS[4],
        tip="SECRET-TIP",
        tool_row_id=987654321,
        raw_digest=b"SECRETDIGEST" + bytes(20),
    )


def test_reprs_and_strs_reveal_nothing() -> None:
    r = LocalMediaRegistry()
    b = _secret_binding()
    ref = r.mint(b)
    c = caller(device_id=SECRETS[0], user_id=SECRETS[1], instance_id=SECRETS[2], profile=SECRETS[3])
    snap = r.lookup(ref, c)
    assert snap is not None
    for obj in (r, b, c, snap, FirstServe.RECORDED, SessionKind.PHONE):
        for text in (repr(obj), str(obj), f"{obj}", format(obj)):
            assert ref not in text
            assert "SECRET" not in text and "SECRETDIGEST" not in text
            assert ref[:10] not in text
    assert repr(r) == "LocalMediaRegistry()" and repr(b) == "Binding()"
    assert repr([b, snap, c]) == "[Binding(), EntrySnapshot(), Caller()]"


def test_refusal_exceptions_carry_no_parameters() -> None:
    attempts = [
        lambda: Binding(**{**_fields(), "device_id": "SECRET-BAD" * 1000}),
        lambda: Binding(**{**_fields(), "raw_digest": b"SECRET-SHORT"}),
        lambda: Binding(**{**_fields(), "kind": "SECRET-KIND"}),
        lambda: Binding(**{**_fields(), "tool_row_id": True}),
        lambda: Caller("SECRET-X", "", "i", "p"),
        lambda: LocalMediaRegistry().mint("SECRET-NOT-A-BINDING"),  # type: ignore[arg-type]
        lambda: LocalMediaRegistry(_random=lambda n: b"SECRET-RANDOM").mint(binding()),
    ]
    for attempt in attempts:
        with pytest.raises(RegistryRefusal) as info:
            attempt()
        exc = info.value
        assert exc.args == ("local media registry refused",)
        assert "SECRET" not in repr(exc) + str(exc)
        assert exc.__cause__ is None and exc.__suppress_context__
        assert exc.__context__ is None
        assert pickle.loads(pickle.dumps(exc)).args  # noqa: S301 - our own exception == exc.args


def _fields() -> dict[str, object]:
    return dataclasses.asdict(binding()) | {"kind": SessionKind.BOT_CHAT}


@pytest.mark.parametrize(
    "change",
    [
        {"device_id": ""},
        {"user_id": 5},
        {"tip": None},
        {"session_id": b"x"},
        {"tool_row_id": 1.5},
        {"tool_row_id": False},
        {"tool_row_id": ""},
        {"tool_row_id": "7"},
        {"raw_digest": "a" * 32},
        {"raw_digest": b"a" * 31},
        {"kind": "bot_chat"},
        {"profile": "p" * 257},
    ],
)
def test_binding_rejects_malformed_fields(change: dict[str, object]) -> None:
    with pytest.raises(RegistryRefusal):
        binding(**change)


def test_registry_stores_no_path_or_name_field() -> None:
    names = {f.name for f in dataclasses.fields(Binding)}
    assert names == {
        "device_id", "user_id", "instance_id", "profile", "kind",
        "session_id", "tip", "tool_row_id", "raw_digest",
    }  # fmt: skip
    assert {f.name for f in dataclasses.fields(reg.EntrySnapshot)} == {
        "binding", "minted_at", "first_served", "_token",
    }  # fmt: skip


def test_new_instance_starts_empty() -> None:
    a = LocalMediaRegistry()
    ref = a.mint(binding())
    assert LocalMediaRegistry().lookup(ref, caller()) is None


# --- module contract --------------------------------------------------------------------------

PACKAGE = Path(reg.__file__).parent


def test_module_is_stdlib_only_and_has_no_module_level_instance() -> None:
    tree = ast.parse(Path(reg.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and (node.module or "").split(".")[0] != "hmp_plugin"
        if isinstance(node, ast.Import):
            assert all(not a.name.startswith("hmp_plugin") for a in node.names)
    assert not [v for v in vars(reg).values() if isinstance(v, LocalMediaRegistry)]
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert "logging" not in imported


def test_importing_registry_is_inert_in_a_fresh_interpreter() -> None:
    code = (
        "import sys, threading, hmp_plugin\n"
        "before, mods = threading.active_count(), set(sys.modules)\n"
        "import hmp_plugin.local_media_registry\n"
        "new = {m for m in set(sys.modules) - mods if m.startswith('hmp_plugin')}\n"
        "assert new == {'hmp_plugin.local_media_registry'}, new\n"
        "assert threading.active_count() == before\n"
    )
    done = subprocess.run(
        [sys.executable, "-B", "-c", code],
        env={"PYTHONPATH": str(PACKAGE.parent), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-500:]


def test_every_state_touching_step_runs_with_the_lock_held() -> None:
    r, clock = make(per_device=2, total=3)
    seen: list[str] = []

    def guarded(name: str) -> None:
        real = getattr(r, name)

        def wrapper(*a: object, **k: object) -> object:
            assert r._lock.locked(), name
            seen.append(name)
            return real(*a, **k)

        setattr(r, name, wrapper)

    for name in ("_now", "_remove", "_sweep_expired", "_touch", "_live", "_new_ref"):
        guarded(name)
    b = binding()
    ref = r.mint(b)
    r.mint(b)
    s = snap_of(r, ref)
    r.record_first_served(ref, s, caller(), D1)
    r.record_first_served(ref, s, caller(), D1)
    r.mint(binding(tool_row_id=2))
    r.mint(binding(tool_row_id=3))  # evicts
    r.record_first_served(ref, s, caller(), D2)  # may delete
    clock.now += 1800
    r.lookup(ref, caller())
    r.mint(binding(tool_row_id=4))  # sweeps
    assert {"_now", "_remove", "_sweep_expired", "_touch", "_live", "_new_ref"} <= set(seen)
    assert not r._lock.locked()
