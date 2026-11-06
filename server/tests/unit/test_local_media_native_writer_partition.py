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
