"""Owned full writer matrix orchestration; inert import, no automatic retries.

Private synthetic fixture only. Does not install, activate or qualify a release.
Every declared pair gets a fresh retained source/root and two exclusive DB scopes.
"""
import importlib.util
import os
import shutil
import stat
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_writer_matrix_driver", Path(__file__).with_name("local_media_native_serving_driver.py"))
driver = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(driver)
RESERVE_BYTES = 32 * 1024 ** 3
PROCESS_ALLOWANCE_BYTES = 1024 ** 3


def run_matrix(root, native_repository, native_commit, expected_hmp_commit):
    """Run all pairs once; any failure retains its root and prevents later admission.

    Capacity is an admission check, not a reservation or hard storage bound.
    No prior evidence is deleted. No continuation/retry of an attempted pair is
    provided; an uncertain outcome needs explicit reconciliation outside this runner.
    """
    require = driver.commands._require
    require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root and
            driver._sha(native_commit) and driver._sha(expected_hmp_commit))
    info = root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            stat.S_IMODE(info.st_mode) == 0o700 and not any(root.iterdir()))
    plan = driver.writer_contract.paired_plan()
    require(type(plan) is tuple and len(plan) == 384)
    state = {"schema": 1, "stage": "prepared", "expected_hmp_commit": expected_hmp_commit,
             "native_commit": native_commit, "processes_planned": len(plan),
             "phases_planned": 2 * len(plan), "completed": [], "current": None,
             "reserve_bytes": RESERVE_BYTES, "process_allowance_bytes": PROCESS_ALLOWANCE_BYTES,
             "full_matrix_completed": False, "production_qualified": False}
    checkpoint = root / "matrix-state.json"
    driver.commands._save(checkpoint, state)
    for index, (case, selector, pair) in enumerate(plan):
        free = shutil.disk_usage(root).free
        require(type(free) is int and free >= 0)
        state["free_bytes_before_admission"] = free
        if free < RESERVE_BYTES + PROCESS_ALLOWANCE_BYTES:
            state["stage"] = "capacity_refused_before_next_pair"
            driver.commands._save(checkpoint, state)
            return state
        child = root / f"pair-{index:03}"
        child.mkdir(mode=0o700)  # Exclusive; never adopt or overwrite another attempt.
        state["current"] = {"index": index, "case": case, "selector": selector,
                            "requests": pair, "root": str(child)}
        state["stage"] = "pair_attempted"
        driver.commands._save(checkpoint, state)
        try:
            receipt = driver.run_fixture(child, native_repository, native_commit,
                sample_binding_seed=True, binding_cost_case=case,
                binding_cost_selector=selector, binding_writer=pair,
                expected_hmp_commit=expected_hmp_commit)
            require(receipt["completed"] is True and
                    receipt["hmp_commit"] == expected_hmp_commit)
        except BaseException:
            # No exception text/native data, replay, cancellation or later admission.
            state["stage"] = "pair_failed_no_retry"
            driver.commands._save(checkpoint, state)
            raise
        state["completed"].append({"index": index, "case": case, "selector": selector,
            "requests": pair, "report_sha256": receipt["report_sha256"]})
        state["stage"] = "pair_completed"
        state["current"] = None
        driver.commands._save(checkpoint, state)
    state["stage"] = "matrix_completed_artifact_review_pending"
    state["full_matrix_completed"] = True
    driver.commands._save(checkpoint, state)
    return state
