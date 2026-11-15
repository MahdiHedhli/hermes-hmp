"""Registry bookkeeping only: fixture issuers do not prove native authorization."""

import copy
import pickle

import pytest

from hmp_plugin.presentation_native_claim import (
    MAX_RECORDS,
    NativeReadClaim,
    NativeReadRegistry,
    NativeSourceError,
)


def fixture_registry():
    now = [1.0]
    issuer, generation, operation = object(), object(), object()
    registry = NativeReadRegistry(issuer, generation, lambda: now[0])
    registry._begin(issuer, operation, "belac", 3.0)
    claim = registry._issue(
        issuer, operation, home="/unit/home", uid=501, gid=20, authority=object()
    )
    return registry, issuer, operation, claim, now


@pytest.mark.parametrize("action", [copy.copy, copy.deepcopy, pickle.dumps])
def test_claim_cannot_be_copied_or_serialized(action):
    _, _, _, claim, _ = fixture_registry()
    with pytest.raises(TypeError):
        action(claim)


@pytest.mark.parametrize(
    "field,value",
    [
        ("_home", "/other"),
        ("_uid", 0),
        ("_gid", 0),
        ("_authority", object()),
        ("_generation", object()),
    ],
)
def test_changed_binding_is_not_original_claim(field, value):
    registry, _, _, claim, _ = fixture_registry()
    setattr(claim, field, value)
    with pytest.raises(NativeSourceError):
        registry._check(claim)


def test_forged_same_record_cannot_start_or_settle_original():
    registry, _, _, claim, _ = fixture_registry()
    forged = NativeReadClaim(registry, claim._record, claim._home, 501, 20, claim._authority)
    registry._start_read(claim)
    with pytest.raises(NativeSourceError):
        registry._start_read(forged)
    with pytest.raises(NativeSourceError):
        registry._end_read(forged, unknown=False)
    assert claim._in_progress
    registry._end_read(claim, unknown=False)


def test_deadline_cleanup_does_not_renew_or_allow_replay():
    registry, issuer, operation, claim, now = fixture_registry()
    registry._start_read(claim)
    now[0] = 3.0
    with pytest.raises(NativeSourceError):
        registry._check(claim)
    registry._end_read(claim, unknown=False)
    with pytest.raises(NativeSourceError):
        registry._start_read(claim)
    registry._retire(issuer, operation)
    registry._forget_closed(issuer, operation)
    assert not registry._records


def test_unknown_cleanup_debt_cannot_be_forgotten_after_retire():
    registry, issuer, operation, claim, _ = fixture_registry()
    registry._start_read(claim)
    registry._end_read(claim, unknown=True)
    registry._retire(issuer)
    with pytest.raises(NativeSourceError):
        registry._forget_closed(issuer, operation)
    assert len(registry._records) == 1


def test_successful_read_is_single_use_and_settlement_is_single_use():
    registry, _, _, claim, _ = fixture_registry()
    registry._start_read(claim)
    registry._end_read(claim, unknown=False)
    with pytest.raises(NativeSourceError):
        registry._start_read(claim)
    with pytest.raises(NativeSourceError):
        registry._end_read(claim, unknown=False)


def test_original_issuer_and_bounded_records_required():
    registry, issuer, _, _, _ = fixture_registry()
    with pytest.raises(NativeSourceError):
        registry._begin(object(), object(), "belac", 3.0)
    operations = [object() for _ in range(MAX_RECORDS)]
    for operation in operations[:-1]:
        registry._begin(issuer, operation, "belac", 3.0)
    with pytest.raises(NativeSourceError):
        registry._begin(issuer, operations[-1], "belac", 3.0)
    assert len(registry._records) == MAX_RECORDS


@pytest.mark.parametrize("home", ["/", "/a/../b", "/a//b", "/a/", "relative", "/\ud800"])
def test_noncanonical_home_is_refused_before_claim(home):
    issuer, operation = object(), object()
    registry = NativeReadRegistry(issuer, object(), lambda: 1.0)
    registry._begin(issuer, operation, "belac", 3.0)
    with pytest.raises(NativeSourceError):
        registry._issue(issuer, operation, home=home, uid=501, gid=20, authority=object())


def test_foreign_claim_cannot_run_object_hooks():
    registry, _, _, _, _ = fixture_registry()

    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError("foreign claim inspected")

    with pytest.raises(NativeSourceError):
        registry._check(Foreign())
