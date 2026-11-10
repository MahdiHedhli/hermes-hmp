"""Historical shape and schema controls, not native Link admission evidence."""
import itertools

import pytest

from hmp_plugin import presentation_native_link as link
from hmp_plugin import presentation_startup_artifacts as artifacts
from .test_presentation_link_metadata_boundary import Foreign


def phase_data():
    from hmp_startup.gateway_entry import _NativeFileLedger, _NativeFilePhase

    phase = _NativeFilePhase(object(), object(), object(), object(), [None], [None])
    phase.current[0] = phase.idle
    ledger = _NativeFileLedger(None, None, None, [], [19, 2], [None], [False], [],
                              [None], [None, None, None], phase)
    registration = artifacts._NativeScopeRegistration(
        *([None] * len(artifacts._NativeScopeRegistration._fields)))._replace(
            native_ledger=ledger, native_phase=phase, phase_type=type(phase),
            type_pins=(object, type(ledger), object))
    return registration, ledger, phase


@pytest.mark.parametrize('state,inflight,result', list(itertools.product(
    ('idle', 'active', 'pending'), (False, True), (False, True))))
def test_history_phase_requires_canonical_current_result_and_inflight(state, inflight, result):
    registration, ledger, phase = phase_data()
    marker = object()
    phase.current[0] = getattr(phase, state)
    ledger.inflight[0] = marker if inflight else None
    phase.result[0] = marker if result else None
    before = (tuple(ledger.counts), tuple(ledger.attempts), tuple(ledger.inflight),
              tuple(phase.current), tuple(phase.result))
    healthy = ((state == 'idle' and not inflight and not result)
               or (state == 'active' and inflight and result)
               or (state == 'pending' and not inflight and result))
    if healthy:
        assert link._history_phase_mirrors(registration) is phase
    else:
        with pytest.raises(artifacts.ArtifactObservationError):
            link._history_phase_mirrors(registration)
    assert before == (tuple(ledger.counts), tuple(ledger.attempts), tuple(ledger.inflight),
                      tuple(phase.current), tuple(phase.result))


@pytest.mark.parametrize('fault', ('active_other_result', 'failed', 'failure_record',
                                  'phase_extra', 'inflight_extra', 'foreign_marker'))
def test_torn_or_failed_history_never_becomes_a_live_grant(fault):
    registration, ledger, phase = phase_data()
    calls = []
    if fault == 'active_other_result':
        phase.current[0] = phase.active
        ledger.inflight[0], phase.result[0] = object(), object()
    elif fault == 'failed':
        ledger.failed[0] = True
    elif fault == 'failure_record':
        ledger.failure[0] = object()
    elif fault == 'phase_extra':
        phase.current.append(object())
    elif fault == 'inflight_extra':
        ledger.inflight.append(object())
    else:
        phase.current[0] = Foreign(calls)
    with pytest.raises(artifacts.ArtifactObservationError):
        link._history_phase_mirrors(registration)
    assert calls == [] and ledger.counts == [19, 2] and ledger.attempts == []


@pytest.mark.parametrize('stage', ('snapshot', 'history', 'fact', 'recheck'))
def test_snapshot_entry_fences_foreign_owners_without_dispatch(stage):
    calls = []
    foreign = Foreign(calls)
    functions = {
        'snapshot': lambda: link._snapshot(foreign, foreign, 0, None),
        'history': lambda: link._snapshot_history_mirrors(foreign, foreign, foreign, foreign),
        'fact': lambda: link._make_fact(foreign, foreign, foreign, foreign, foreign, foreign, foreign),
        'recheck': lambda: link._recheck(foreign, foreign, foreign),
    }
    with pytest.raises(artifacts.ArtifactObservationError):
        functions[stage]()
    assert calls == []


def test_raw_free_observation_cannot_implicitly_fall_back_to_legacy_bytes():
    from .test_presentation_link_path_policy import _policy

    selected = _policy()
    owner = object.__new__(artifacts.StartupArtifactOwner)
    count = (owner, object(), 6)
    record = artifacts._LinkRead(selected.hop, 0, 0, count)
    observation = artifacts._NativeReadlinkObservation(record, count, count, 6, object(), object())
    source = artifacts._RuntimeSource(None, None, None, None, None, None,
                                     None, selected.plan, [record], [None], [None], [count], 4096)
    snapshot = artifacts._LinkSnapshot(source, 0, (), (), (observation,), count)
    assert 'data' not in observation._fields and not hasattr(observation, 'data')
    with pytest.raises(artifacts.ArtifactObservationError):
        artifacts._link_reads_current(source, snapshot)
    assert record.data is None and record.acknowledgement is None


def test_fixed_engine_dispatch_rejects_unknown_operation_before_registration_access():
    owner = object.__new__(artifacts.StartupArtifactOwner)
    calls = []
    with pytest.raises(artifacts.ArtifactObservationError):
        artifacts._native_link_function(owner, Foreign(calls), 'arbitrary_operation')
    assert calls == []


def test_bootstrap_keyword_pairs_are_fenced_before_foreign_equality(monkeypatch):
    from hmp_startup.gateway_entry import _NativeFileLineage
    from .test_presentation_link_metadata_boundary import packet

    calls = []
    original = packet()
    kernel_rows = tuple((*row[:6], Foreign(calls))
                        if row[0] == '_closed_link_engine_origin' else row
                        for row in original[3])
    malformed = (*original[:3], kernel_rows)
    parent = ((None, None, None, None, malformed), (), (), (), ())
    lineage = _NativeFileLineage(None, None, None, None, parent)
    owner = object.__new__(artifacts.StartupArtifactOwner)
    registration = artifacts._NativeScopeRegistration(
        *([None] * len(artifacts._NativeScopeRegistration._fields)))._replace(
            owner=owner, lineage=lineage, type_pins=(_NativeFileLineage, object, object))
    # Shape-only refusal: bypass only the unrelated lifetime precondition.
    # No native operation or successful engine admission is exercised here.
    monkeypatch.setattr(artifacts, '_native_work_registration_tail', lambda *args: None)
    with pytest.raises(artifacts.ArtifactObservationError):
        artifacts._native_link_function(owner, registration, '_snapshot')
    assert calls == []
