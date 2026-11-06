"""Explicit fresh supplemental fixture execution; inert import and no resume.

Offline synthetic evidence only. Does not enable production routes or devices.
"""
import importlib.util
import os
import re
import shutil
import stat
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_supplement_partition", Path(__file__).with_name("local_media_native_writer_partition.py"))
partition = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(partition)
_DRIVER_SPEC = importlib.util.spec_from_file_location(
    "_supplement_driver", Path(__file__).with_name("local_media_native_serving_driver.py"))
driver = importlib.util.module_from_spec(_DRIVER_SPEC)
_DRIVER_SPEC.loader.exec_module(driver)
RESERVE = 32 * 1024 ** 3
ALLOWANCE = 1024 ** 3


def run_supplement(root, native_repository, native_commit, expected_hmp_commit, *,
                   native_archive_cache, layout="heavy_only_v1"):
    """Run the reviewed new scope once; retain every attempted root on failure.

    This is not a continuation API. Any interrupted or attempted run needs its
    own evidence reconciliation; an existing root is never adopted or replayed.
    """
    require = driver.commands._require
    require(driver._sha(native_commit) and driver._sha(expected_hmp_commit))
    driver.validate_archive_cache(native_archive_cache)
    require(native_archive_cache is not None)
    plan = partition.supplemental_plan(partition.contract.paired_plan(), layout=layout)
    require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root)
    info = root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            stat.S_IMODE(info.st_mode) == 0o700 and not any(root.iterdir()))
    state = {"schema": 1, "scope": plan["scope"], "layout": plan["layout"], "stage": "prepared",
             "source": expected_hmp_commit, "native": native_commit,
             "catalog_source": plan["catalog_source"],
             "catalog_sha256": plan["catalog_sha256"],
             "jobs_planned": len(plan["jobs"]), "phases_planned": plan["planned_phases"],
             "base_phases_included": False, "full_matrix_completed": False,
             "production_qualified": False, "scope_execution_completed": False,
             "completed": [], "current": None}
    journal = root / "supplement-state.json"
    driver.commands._save(journal, state)
    for index, job in enumerate(plan["jobs"]):
        free = shutil.disk_usage(root).free
        require(type(free) is int and free >= 0)
        if free < RESERVE + ALLOWANCE:
            state["stage"] = "capacity_refused_before_next_job"
            driver.commands._save(journal, state)
            return state
        child = root / f"job-{index:03}"
        child.mkdir(mode=0o700)
        state["stage"] = "job_attempted"
        state["current"] = {"index": index, **job, "root": str(child)}
        driver.commands._save(journal, state)
        try:
            receipt = driver.run_fixture(child, native_repository, native_commit,
                sample_binding_seed=True, binding_cost_case=job["case"],
                binding_cost_selector=job["selector"], binding_writer=job["request"],
                expected_hmp_commit=expected_hmp_commit,
                native_archive_cache=native_archive_cache)
            require(receipt["completed"] is True and
                    receipt["hmp_commit"] == expected_hmp_commit and
                    receipt["native_commit"] == native_commit and
                    type(receipt["report_sha256"]) is str and
                    re.fullmatch("[0-9a-f]{64}", receipt["report_sha256"]) is not None)
        except BaseException:
            state["stage"] = "job_failed_no_retry"
            driver.commands._save(journal, state)
            raise
        state["completed"].append({"index": index, **job,
                                   "report_sha256": receipt["report_sha256"]})
        state["current"] = None
        state["stage"] = "job_completed"
        driver.commands._save(journal, state)
    state["stage"] = "supplement_completed_artifact_review_pending"
    state["scope_execution_completed"] = True
    driver.commands._save(journal, state)
    return state
