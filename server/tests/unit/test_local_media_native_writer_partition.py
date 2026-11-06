"""Pure partition models, no native operations or process creation."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_writer_partition.py"


def load():
    spec = importlib.util.spec_from_file_location("_partition_guard_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_plan(module):
    additions = ("ordinary_child", "delegate_child")
    return tuple(row for row in module.contract.paired_plan()
                 if not any(request.split(":")[0] in additions for request in row[2]))


def test_actual_refusal_partition_preserves_every_unattempted_phase_once():
    module = load()
    base = base_plan(module)
    assert len(base) == 384
    result = module.remaining_plan(base, 174, 174)
    jobs = result["jobs"]
    assert len(jobs) == 301 and result["unattempted_pairs"] == 209
    assert result["planned_phases"] == 418
    actual = [(job["origin_pair"], phase) for job in jobs for phase in job["origin_phases"]]
    expected = {(index, phase) for index in range(175, 384) for phase in (0, 1)}
    assert len(actual) == len(set(actual)) == len(expected) and set(actual) == expected
    assert all(job["origin_pair"] > 174 for job in jobs)
    assert not result["refused_pair_replayed"] and not result["full_matrix_completed"]
    assert result["source_receipt_reconciliation_required"] is True
    for job in jobs:
        case, selector, requests = base[job["origin_pair"]]
        assert (job["case"], job["selector"]) == (case, selector)
        if case % 4 == 3:
            assert type(job["request"]) is str and len(job["origin_phases"]) == 1
            assert job["request"] == requests[job["origin_phases"][0]]
        else:
            assert job["request"] == requests and job["origin_phases"] == (0, 1)


@pytest.mark.parametrize("completed, refused", [(True, 1), (174, True), (-1, -1),
    (384, 384), (174, 175), (175, 174), (None, 174), (174, "174")])
def test_ambiguous_counts_or_nonmatching_refusal_are_not_resume_authority(completed, refused):
    module = load()
    with pytest.raises(RuntimeError):
        module.remaining_plan(base_plan(module), completed, refused)


def test_duplicate_or_expanded_catalog_cannot_silently_replace_historical_base():
    module = load()
    base = base_plan(module)
    with pytest.raises(RuntimeError):
        module.remaining_plan(module.contract.paired_plan(), 174, 174)
    with pytest.raises(RuntimeError):
        module.remaining_plan((base[0], *base[:-1]), 174, 174)


@pytest.mark.parametrize("refused", [0, 56, 170, 227, 344, 383])
def test_boundary_partitions_preserve_coverage_without_replaying_failed_pair(refused):
    module = load()
    result = module.remaining_plan(base_plan(module), refused, refused)
    assert result["planned_phases"] == (383 - refused) * 2
    assert all(job["origin_pair"] > refused for job in result["jobs"])


def test_valid_unique_but_permuted_catalog_cannot_replace_original_order():
    module = load()
    base = base_plan(module)
    with pytest.raises(RuntimeError):
        module.remaining_plan((base[1], base[0], *base[2:]), 174, 174)


def test_supplement_preserves_both_child_lineages_all_shapes_selectors_and_reads():
    module = load()
    catalog = module.contract.paired_plan()
    result = module.supplemental_plan(catalog)
    jobs = result['jobs']
    observed = []
    for job in jobs:
        case, selector, pair = catalog[job['origin_pair']]
        for phase in job['origin_phases']:
            observed.append((case, selector, pair[phase]))
        if case % 4 == 3:
            assert len(job['origin_phases']) == 1 and type(job['request']) is str
        else:
            assert job['origin_phases'] == (0, 1) and job['request'] == pair
    # Independent product requirement: eight shape/proof contexts, three
    # selectors, both lineage operations and all three page/ID read positions.
    expected = {(case, selector, f'{operation}:{read}')
                for case in range(8) for selector in (1, 16, 128)
                for operation in ('ordinary_child', 'delegate_child')
                for read in ('page', 'ids0', 'ids1')}
    assert len(jobs) == 90 and len(observed) == len(set(observed)) == 144
    assert set(observed) == expected
    assert result['planned_pairs'] == 72 and result['planned_phases'] == 144
    assert result['base_phases_included'] is False
    assert result['full_matrix_completed'] is False
    assert result['execution_admission_review_required'] is True


@pytest.mark.parametrize('mutation', ['base_only', 'duplicate', 'reorder', 'boolean', 'list'])
def test_supplement_cannot_adopt_a_changed_or_ambiguous_catalog(mutation):
    module = load()
    plan = module.contract.paired_plan()
    if mutation == 'base_only':
        plan = base_plan(module)
    elif mutation == 'duplicate':
        plan = (plan[0], *plan[:-1])
    elif mutation == 'reorder':
        plan = (plan[1], plan[0], *plan[2:])
    elif mutation == 'boolean':
        _case, selector, requests = plan[0]
        plan = ((False, selector, requests), *plan[1:])
    else:
        plan = list(plan)
    with pytest.raises(RuntimeError):
        module.supplemental_plan(plan)


def test_explicit_per_phase_layout_preserves_every_historical_supplement_coordinate():
    module = load()
    catalog = module.contract.paired_plan()
    paired = module.supplemental_plan(catalog)
    single = module.supplemental_plan(catalog, layout='per_phase_v2')
    def expand(plan):
        return [(job['origin_pair'], phase, job['case'], job['selector'],
                 catalog[job['origin_pair']][2][phase])
                for job in plan['jobs'] for phase in job['origin_phases']]
    assert expand(paired) == expand(single)
    assert len(single['jobs']) == single['planned_phases'] == 144
    assert single['layout'] == 'per_phase_v2' and paired['layout'] == 'heavy_only_v1'
    assert all(len(job['origin_phases']) == 1 and type(job['request']) is str
               and job['request'] == catalog[job['origin_pair']][2][job['origin_phases'][0]]
               for job in single['jobs'])
    assert single['full_matrix_completed'] is False
    assert single['execution_admission_review_required'] is True


@pytest.mark.parametrize('layout', [True, None, 'auto', 'retry', 'per_phase', []])
def test_unknown_or_automatic_supplement_layout_is_not_execution_admission(layout):
    module = load()
    with pytest.raises(RuntimeError):
        module.supplemental_plan(module.contract.paired_plan(), layout=layout)
