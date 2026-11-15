"""Malformed historical DATA must refuse before any foreign attribute lookup."""
import pytest
from hmp_plugin import presentation_startup_probe as probe
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError


@pytest.mark.parametrize('field', ('finish', 'execution', 'plan', 'registration'))
def test_historical_cohort_type_first(field):
    hooks = []

    class Foreign:
        def __getattr__(self, name):
            hooks.append(name)
            raise AssertionError('foreign historical attribute')

    execution = probe._ProbeExecution(*([None] * len(probe._ProbeExecution._fields)))
    if field == 'plan':
        execution = execution._replace(plan=Foreign())
    elif field == 'registration':
        plan = probe._StartupPlan(*([None] * len(probe._StartupPlan._fields)))
        execution = execution._replace(plan=plan, registration=Foreign())
    elif field == 'execution':
        execution = Foreign()
    finish = probe._ProbeFinish(execution, None, (), None, ())
    if field == 'finish':
        finish = Foreign()
    with pytest.raises(ArtifactObservationError):
        probe._historical_cohort(finish, None)
    assert hooks == []


def _snapshot_data():
    """Typed preparation DATA only; none of these values can admit native work."""
    from types import SimpleNamespace
    from hmp_startup.gateway_entry import _NativeFileLedger, _NativeFilePhase

    phase = _NativeFilePhase(object(), object(), object(), object(), [None], [None])
    phase.current[0] = phase.idle
    ledger = _NativeFileLedger(
        None, None, None, [], [0, 0], [None], [False], [], [None],
        [None, None, None], phase,
    )
    activation = object.__new__(probe.activation_module.GatewayActivationOwner)
    scope = probe._Scope(*([None] * len(probe._Scope._fields)))._replace(activation=activation)
    registration = probe._NativeScopeRegistration(
        *([None] * len(probe._NativeScopeRegistration._fields))
    )._replace(scope=scope, native_ledger=ledger, native_phase=phase)
    source = SimpleNamespace(entry=SimpleNamespace(), context_fact=(SimpleNamespace(),))
    plan = probe._StartupPlan(*([None] * len(probe._StartupPlan._fields)))._replace(
        owner=SimpleNamespace(), source=source,
    )
    execution = probe._ProbeExecution(*([None] * len(probe._ProbeExecution._fields)))._replace(
        plan=plan, registration=registration,
    )
    return probe._ProbeFinish(execution, None, (), None, ()), scope, ledger, phase


@pytest.mark.parametrize('state', ('idle', 'active', 'pending'))
def test_historical_snapshot_accepts_healthy_shared_phase_data(state):
    actual, scope, ledger, phase = _snapshot_data()
    marker = object()
    if state == 'active':
        phase.current[0] = phase.active
        ledger.inflight[0] = phase.result[0] = marker
    elif state == 'pending':
        phase.current[0] = phase.pending
        phase.result[0] = marker
    cohort = probe._historical_cohort(actual, scope)
    assert cohort[1][-2] == (phase.current, (phase.current[0],))
    assert cohort[1][-1] == (phase.result, (phase.result[0],))
    assert ledger.counts == [0, 0] and ledger.attempts == []


@pytest.mark.parametrize('fault', (
    'idle_result', 'active_no_inflight', 'pending_inflight', 'failed_phase',
    'failed_ledger', 'failure_record', 'preparation_shape', 'phase_shape',
))
def test_historical_snapshot_refuses_failed_or_torn_shared_phase_data(fault):
    actual, scope, ledger, phase = _snapshot_data()
    marker = object()
    if fault == 'idle_result':
        phase.result[0] = marker
    elif fault == 'active_no_inflight':
        phase.current[0], phase.result[0] = phase.active, marker
    elif fault == 'pending_inflight':
        phase.current[0] = phase.pending
        ledger.inflight[0] = phase.result[0] = marker
    elif fault == 'failed_phase':
        phase.current[0] = phase.failed
    elif fault == 'failed_ledger':
        ledger.failed[0] = True
    elif fault == 'failure_record':
        ledger.failure[0] = marker
    elif fault == 'preparation_shape':
        ledger.preparation.pop()
    else:
        phase.current.append(marker)
    with pytest.raises(ArtifactObservationError):
        probe._historical_cohort(actual, scope)
    assert ledger.counts == [0, 0] and ledger.attempts == []


@pytest.mark.parametrize('fault', ('healthy_phase_change', 'retirement_marker_change'))
def test_real_old_finish_rejects_changes_after_weak_observations(tmp_path, monkeypatch, fault):
    from . import test_presentation_entry_files as base
    from .test_presentation_gateway_approval import operator_composed_script

    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nhistorical_fault=' + repr(fault) + '\n'
    script += r'''
from hmp_plugin import presentation_startup_probe as probe
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError
io=retained._inputs.io_slot[0]
actual=io._origin.cache.effects[0].native_finish
ledger=actual.execution.registration.native_ledger
phase=actual.execution.registration.native_phase
before=(tuple(ledger.counts),len(ledger.attempts))
changed=[]
def corrupt_after_observations(frame):
    if frame.f_locals['actual'] is not actual or changed:return
    changed.append(True)
    if historical_fault=='healthy_phase_change':
        assert phase.current[0] is phase.idle and phase.result[0] is None
        assert ledger.inflight[0] is None
        phase.current[0]=phase.pending
        phase.result[0]=object()  # healthy shape DATA, never a native operation
    else:
        marker=actual.predecessor.consumer.custody[1]
        assert marker.state==[True,True,False]
        marker.state[1]=False
prior_trace=sys.gettrace()
trace_synthetic_boundary(probe._historical_finish_tail.__code__,
    'return mirrors(actual, scope, cohort)',corrupt_after_observations)
try:
    try:probe._historical_finish_tail(actual)
    except ArtifactObservationError:pass
    else:raise AssertionError('changed historical cohort accepted')
finally:sys.settrace(prior_trace)
assert changed==[True]
assert (tuple(ledger.counts),len(ledger.attempts))==before
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
