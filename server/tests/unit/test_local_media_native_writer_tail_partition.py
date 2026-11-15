"""Pure post-refusal scope models; no filesystem/native operations."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / 'tools/compat/local_media_native_writer_partition.py'


def load():
    spec = importlib.util.spec_from_file_location('_tail_partition_tests', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def previous(module):
    base = tuple(row for row in module.contract.paired_plan() if not any(
        request.split(':')[0] in ('ordinary_child', 'delegate_child') for request in row[2]))
    return module.remaining_plan(base, 174, 174)['jobs']


def test_actual_never_started_scope_preserves_all120_phases_excludes_both_refusals():
    module = load()
    prior = previous(module)
    plan = module.unattempted_after_refusal(prior, 201, 201, layout='per_phase_v2')
    assert prior[201]['origin_pair'] == 323
    actual = [(job['origin_pair'], phase) for job in plan['jobs']
              for phase in job['origin_phases']]
    assert len(plan['jobs']) == plan['planned_phases'] == len(set(actual)) == 120
    assert set(actual) == {(origin, phase) for origin in range(324, 384) for phase in (0, 1)}
    for job in plan['jobs']:
        old = prior[job['previous_job']]
        assert job['previous_job'] > 201
        assert job['case'] == old['case'] and job['selector'] == old['selector']
        phases = old['origin_phases']
        requests = (old['request'],) if type(old['request']) is str else old['request']
        assert job['request'] == requests[phases.index(job['origin_phases'][0])]
    assert plan['original_refused_pair'] == 174 and plan['excluded_refused_job'] == 201
    assert plan['refused_job_replayed'] is False and plan['full_matrix_completed'] is False
    assert plan['source_receipt_reconciliation_required'] is True


@pytest.mark.parametrize('completed,refused', [(True, 1), (201, True), (201.0, 201),
    (200, 201), (-1, -1), (301, 301), (202, 201)])
def test_ambiguous_or_nonmatching_terminal_counts_are_not_admission(completed, refused):
    module = load()
    with pytest.raises(RuntimeError):
        module.unattempted_after_refusal(
            previous(module), completed, refused, layout='per_phase_v2')


@pytest.mark.parametrize('layout', ['auto', 'retry', 'heavy_only_v1', True, None])
def test_no_implicit_or_failure_driven_layout_selection(layout):
    module = load()
    with pytest.raises(RuntimeError):
        module.unattempted_after_refusal(previous(module), 201, 201, layout=layout)


@pytest.mark.parametrize('change', ['order', 'duplicate', 'boolean', 'phase_list', 'request'])
def test_changed_prior_execution_catalog_cannot_be_adopted(change):
    module = load()
    jobs = list(previous(module))
    if change == 'order':
        jobs[0], jobs[1] = jobs[1], jobs[0]
    elif change == 'duplicate':
        jobs[1] = jobs[0]
    else:
        job = dict(jobs[0])
        if change == 'boolean':
            job['case'] = True
        elif change == 'phase_list':
            job['origin_phases'] = list(job['origin_phases'])
        else:
            job['request'] = 'eligibility:page'
        jobs[0] = job
    with pytest.raises(RuntimeError):
        module.unattempted_after_refusal(tuple(jobs), 201, 201, layout='per_phase_v2')


def test_terminal_boundary_has_empty_unattempted_scope_without_completion_claim():
    module = load()
    plan = module.unattempted_after_refusal(previous(module), 300, 300, layout='per_phase_v2')
    assert plan['jobs'] == () and plan['planned_phases'] == 0
    assert plan['refused_job_replayed'] is False and plan['full_matrix_completed'] is False
