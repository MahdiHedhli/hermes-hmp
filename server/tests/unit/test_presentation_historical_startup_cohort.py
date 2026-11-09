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
