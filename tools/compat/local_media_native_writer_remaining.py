"""Source-bound execution of reviewed unattempted phases; no automatic resume.

Offline fixture evidence only. Never grants runtime feature or device authority.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_remaining_partition_contract",
    Path(__file__).with_name("local_media_native_writer_partition.py"))
partition = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(partition)
_DRIVER_SPEC = importlib.util.spec_from_file_location(
    "_remaining_native_driver", Path(__file__).with_name("local_media_native_serving_driver.py"))
driver = importlib.util.module_from_spec(_DRIVER_SPEC)
_DRIVER_SPEC.loader.exec_module(driver)
RESERVE = 32 * 1024 ** 3
ALLOWANCE = 1024 ** 3


def require(value):
    if not value:
        raise RuntimeError("native_remaining_run_refused")


def _sha(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _evidence(reference):
    require(type(reference) is tuple and len(reference) == 2 and
            type(reference[0]) is type(Path()) and reference[0].is_absolute() and
            reference[0].resolve() == reference[0] and _sha(reference[1]))
    data = driver._read_private(reference[0], 32 * 1024 * 1024)
    require(hashlib.sha256(data).hexdigest() == reference[1])
    value = json.loads(data, object_pairs_hook=driver.commands._pairs)
    require(type(value) is dict)
    return value


def verified_plan(evidence, native_commit):
    """Reconcile explicitly reviewed snapshot, historical journal and settled actor.

    The review record is an operator-held offline attestation to an actual
    independent review, not a server permission or cryptographic reviewer identity.
    """
    require(type(evidence) is dict and set(evidence) == {"prefix", "review", "state", "failed"})
    prefix, review, state, failed = (_evidence(evidence[key]) for key in
                                     ("prefix", "review", "state", "failed"))
    require(prefix.get("source") == partition.BASE_SOURCE and prefix.get("native") == native_commit
            and prefix.get("full_matrix_complete") is False and
            review.get("verdict") == "ACCEPT" and
            review.get("proof_sha256") == evidence["prefix"][1] and
            review.get("source") == partition.BASE_SOURCE)
    for key, expected in (("pairs", 174), ("phases", 348), ("artifacts", 5220),
                          ("copied_source_files", 2185962)):
        require(type(review.get(key)) is int and review[key] == expected)
    require(state.get("stage") == "pair_failed_no_retry" and
            state.get("expected_hmp_commit") == partition.BASE_SOURCE and
            state.get("native_commit") == native_commit and
            state.get("full_matrix_completed") is False and
            type(state.get("completed")) is list and len(state["completed"]) == 174 and
            type(prefix.get("pairs")) is list and len(prefix["pairs"]) == 174)
    additions = ("ordinary_child", "delegate_child")
    base = tuple(row for row in driver.writer_contract.paired_plan() if
                 not any(request.split(":")[0] in additions for request in row[2]))
    plan = partition.remaining_plan(base, 174, 174)
    current = state.get("current")
    require(type(current) is dict and type(current.get("index")) is int and current["index"] == 174)
    for index, row in enumerate((*state["completed"], current)):
        case, selector, requests = base[index]
        require(type(row) is dict and type(row.get("index")) is int and row["index"] == index and
                type(row.get("case")) is int and row["case"] == case and
                type(row.get("selector")) is int and row["selector"] == selector and
                type(row.get("requests")) is list and row["requests"] == list(requests))
        if index < 174:
            recorded = prefix["pairs"][index]
            keys = ("index", "case", "selector", "requests", "report_sha256")
            require(type(recorded) is dict)
            require(_canonical({key: recorded.get(key) for key in keys}) ==
                    _canonical({key: row[key] for key in keys}) and
                    _sha(row.get("report_sha256")) and
                    type(recorded.get("source_files_verified")) is int and
                    recorded["source_files_verified"] == 12563 and
                    type(recorded.get("artifacts")) is list and len(recorded["artifacts"]) == 30)
    case, selector, requests = base[174]
    require(failed.get("hmp_commit") == partition.BASE_SOURCE and
            failed.get("native_commit") == native_commit and
            (failed.get("completed") is None or failed.get("completed") is False) and
            type(failed.get("binding_cost_case")) is int and failed["binding_cost_case"] == case and
            type(failed.get("binding_cost_selector")) is int and
            failed["binding_cost_selector"] == selector and
            failed.get("binding_writer") == list(requests) and
            type(failed.get("commands")) is list and failed["commands"])
    actor = failed["commands"][-1]
    require(type(actor) is dict and actor.get("role") == "native_serving" and
            actor.get("wait_known") is True and actor.get("settlement_only_used") is True and
            actor.get("settlement_wait_active") is False and
            type(actor.get("returncode")) is int and actor["returncode"] == 0 and
            type(actor.get("process_pid")) is int and actor["process_pid"] > 0)
    return plan


def run_remaining(root, native_repository, native_commit, expected_hmp_commit, *,
                  evidence, native_archive_cache):
    """Run each reviewed unattempted job once in a new root; stop on any failure."""
    require(driver._sha(native_commit) and driver._sha(expected_hmp_commit))
    driver.validate_archive_cache(native_archive_cache)
    require(native_archive_cache is not None)
    plan = verified_plan(evidence, native_commit)
    require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root)
    info = root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            stat.S_IMODE(info.st_mode) == 0o700 and not any(root.iterdir()))
    state = {"schema": 1, "scope": "unattempted_base_tail", "stage": "prepared",
             "source": expected_hmp_commit, "native": native_commit,
             "base_source": plan["base_source"], "base_plan_sha256": plan["base_plan_sha256"],
             "evidence_sha256": {key: ref[1] for key, ref in evidence.items()},
             "jobs_planned": len(plan["jobs"]), "phases_planned": plan["planned_phases"],
             "original_refused_pair": 174, "original_refusal_preserved": True,
             "full_matrix_completed": False, "scope_execution_completed": False,
             "completed": [], "current": None}
    journal = root / "remaining-state.json"
    driver.commands._save(journal, state)
    for index, job in enumerate(plan["jobs"]):
        if shutil.disk_usage(root).free < RESERVE + ALLOWANCE:
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
                expected_hmp_commit=expected_hmp_commit, native_archive_cache=native_archive_cache)
            require(receipt["completed"] is True and receipt["hmp_commit"] == expected_hmp_commit)
        except BaseException:
            state["stage"] = "job_failed_no_retry"
            driver.commands._save(journal, state)
            raise
        state["completed"].append({"index": index, **job,
                                   "report_sha256": receipt["report_sha256"]})
        state["current"] = None
        state["stage"] = "job_completed"
        driver.commands._save(journal, state)
    state["stage"] = "unattempted_scope_completed_review_pending"
    state["scope_execution_completed"] = True
    driver.commands._save(journal, state)
    return state
