"""Pure remaining-phase partition; no IO, actor, retry or native execution.

A caller must independently reconcile terminal source-bound receipts before
using this plan. The refused pair is excluded, never silently counted or replayed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_writer_partition_contract", Path(__file__).with_name("local_media_native_writer_sample.py"))
contract = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(contract)


BASE_SOURCE = "21937dcc50fac8c118843e496c9c1c92eb43856f"
BASE_PLAN_SHA256 = "19132a9bf2051bd5c83b17bc34cf7c1ea88969c9b2abbe1c2b4e58e6dd9d40bb"


def require(value):
    if not value:
        raise RuntimeError("native_writer_partition_refused")


def remaining_plan(base_pairs, completed_pairs, refused_pair):
    """Preserve all unattempted phases; largest shape gets one fresh process each.

    Inputs describe the historical base inventory, not the expanded follow-up.
    This produces evidence scope only; it grants no resume or execution authority.
    """
    require(type(base_pairs) is tuple and len(base_pairs) == 384 and
            type(completed_pairs) is int and type(refused_pair) is int and
            completed_pairs == refused_pair and 0 <= refused_pair < len(base_pairs))
    for row in base_pairs:
        require(type(row) is tuple and len(row) == 3)
        case, selector, pair = row
        require(type(pair) is tuple and len(pair) == 2)
        contract.validate_request(case, selector, pair)
    encoded = json.dumps(base_pairs, separators=(",", ":")).encode("ascii")
    require(len(set(base_pairs)) == len(base_pairs) and
            hashlib.sha256(encoded).hexdigest() == BASE_PLAN_SHA256)
    jobs = []
    for origin in range(refused_pair + 1, len(base_pairs)):
        case, selector, pair = base_pairs[origin]
        groups = ((0,), (1,)) if case % 4 == 3 else ((0, 1),)
        for phases in groups:
            request = pair[phases[0]] if len(phases) == 1 else pair
            jobs.append({"origin_pair": origin, "origin_phases": phases,
                         "case": case, "selector": selector, "request": request})
    expected = {(i, phase) for i in range(refused_pair + 1, len(base_pairs)) for phase in (0, 1)}
    actual = [(job["origin_pair"], phase) for job in jobs for phase in job["origin_phases"]]
    require(len(actual) == len(set(actual)) == len(expected) and set(actual) == expected)
    return {"base_source": BASE_SOURCE, "base_plan_sha256": BASE_PLAN_SHA256,
            "jobs": tuple(jobs), "unattempted_pairs": len(base_pairs) - refused_pair - 1,
            "planned_phases": len(expected), "refused_pair": refused_pair,
            "refused_pair_replayed": False, "full_matrix_completed": False,
            "source_receipt_reconciliation_required": True}


EXPANDED_CATALOG_SOURCE = "e8653d5e48b2270394d7a6a738cf0f6570cb6687"
EXPANDED_PLAN_SHA256 = "0a495f4ccbfd646f7d0fddae209b6f7500ec2fecb8965290bd0b6f5751531f15"


def supplemental_plan(expanded_pairs, *, layout="heavy_only_v1"):
    """Pure coverage plan for the additional child-lineage scenarios only.

    These are new observations, not a retry of historical base requests. No
    source receipt, process, root, execution or production authority is supplied.
    """
    require(type(layout) is str and layout in ("heavy_only_v1", "per_phase_v2"))
    require(type(expanded_pairs) is tuple and len(expanded_pairs) == 456)
    for row in expanded_pairs:
        require(type(row) is tuple and len(row) == 3 and
                type(row[2]) is tuple and len(row[2]) == 2)
        contract.validate_request(*row)
    encoded = json.dumps(expanded_pairs, separators=(",", ":")).encode("ascii")
    require(hashlib.sha256(encoded).hexdigest() == EXPANDED_PLAN_SHA256)
    additions = frozenset(("ordinary_child", "delegate_child"))
    selected = tuple((index, row) for index, row in enumerate(expanded_pairs)
                     if all(request.split(":")[0] in additions for request in row[2]))
    require(len(selected) == 72)
    jobs = []
    for origin, (case, selector, pair) in selected:
        groups = ((0,), (1,)) if layout == "per_phase_v2" or case % 4 == 3 else ((0, 1),)
        for phases in groups:
            jobs.append({"origin_pair": origin, "origin_phases": phases,
                         "case": case, "selector": selector,
                         "request": pair[phases[0]] if len(phases) == 1 else pair})
    expected = {(origin, phase) for origin, _ in selected for phase in (0, 1)}
    actual = [(job["origin_pair"], phase) for job in jobs for phase in job["origin_phases"]]
    require(len(jobs) == (144 if layout == "per_phase_v2" else 90) and
            len(actual) == len(set(actual)) == len(expected) == 144 and set(actual) == expected)
    return {"catalog_source": EXPANDED_CATALOG_SOURCE,
            "catalog_sha256": EXPANDED_PLAN_SHA256,
            "scope": "child_lineage_supplement", "layout": layout, "jobs": tuple(jobs),
            "planned_pairs": 72, "planned_phases": 144,
            "base_phases_included": False, "full_matrix_completed": False,
            "execution_admission_review_required": True}


def unattempted_after_refusal(prior_jobs, completed_jobs, refused_job, *, layout):
    """Pure next-scope DATA; never adopt/replay the completed or refused prefix.

    The caller must independently reconcile actual source-bound terminal evidence
    and review before admission. Counts and this plan alone supply no authority.
    """
    require(type(layout) is str and layout == "per_phase_v2" and
            type(prior_jobs) is tuple and len(prior_jobs) == 301 and
            type(completed_jobs) is int and
            type(refused_job) is int and completed_jobs == refused_job and
            0 <= refused_job < 301)
    additions = ("ordinary_child", "delegate_child")
    base = tuple(row for row in contract.paired_plan()
                 if not any(request.split(":")[0] in additions for request in row[2]))
    expected_prior = remaining_plan(base, 174, 174)["jobs"]
    for job in prior_jobs:
        require(type(job) is dict and set(job) ==
                {"origin_pair", "origin_phases", "case", "selector", "request"})
        require(all(type(job[key]) is int for key in ("origin_pair", "case", "selector")) and
                type(job["origin_phases"]) is tuple and
                all(type(phase) is int for phase in job["origin_phases"]) and
                (type(job["request"]) is str or
                 (type(job["request"]) is tuple and
                  all(type(request) is str for request in job["request"]))))
    require(json.dumps(prior_jobs, sort_keys=True, separators=(",", ":")) ==
            json.dumps(expected_prior, sort_keys=True, separators=(",", ":")))
    jobs = []
    for previous_index in range(refused_job + 1, len(prior_jobs)):
        previous = prior_jobs[previous_index]
        requests = ((previous["request"],) if type(previous["request"]) is str
                    else previous["request"])
        for phase, request in zip(previous["origin_phases"], requests, strict=True):
            jobs.append({"previous_job": previous_index,
                         "origin_pair": previous["origin_pair"], "origin_phases": (phase,),
                         "case": previous["case"], "selector": previous["selector"],
                         "request": request})
    expected = [(job["origin_pair"], phase) for job in prior_jobs[refused_job + 1:]
                for phase in job["origin_phases"]]
    actual = [(job["origin_pair"], job["origin_phases"][0]) for job in jobs]
    require(actual == expected and len(actual) == len(set(actual)))
    return {"base_source": BASE_SOURCE, "base_plan_sha256": BASE_PLAN_SHA256,
            "previous_plan_source": EXPANDED_CATALOG_SOURCE,
            "layout": layout, "jobs": tuple(jobs), "planned_phases": len(expected),
            "excluded_completed_jobs": completed_jobs, "excluded_refused_job": refused_job,
            "original_refused_pair": 174, "refused_job_replayed": False,
            "full_matrix_completed": False, "source_receipt_reconciliation_required": True}
