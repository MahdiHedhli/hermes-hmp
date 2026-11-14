"""Admission and no-replay models; no Git, clone, native service or network work."""
import hashlib
import importlib.util
import json
import os
import types
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_writer_remaining.py"


def load():
    spec = importlib.util.spec_from_file_location("_remaining_owner_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, *, fault=None, fail_at=None, capacity_at=None):
    module, calls = load(), []
    monkeypatch.setattr(module.driver.sys, "platform", "darwin")
    base = tuple(row for row in module.driver.writer_contract.paired_plan() if
                 not any(r.split(":")[0] in ("ordinary_child", "delegate_child") for r in row[2]))
    completed = [{"index": i, "case": base[i][0], "selector": base[i][1],
                  "requests": list(base[i][2]), "report_sha256": "d" * 64} for i in range(174)]
    prefix_rows = [{**row, "source_files_verified": 12563, "artifacts": [None] * 30}
                   for row in completed]
    current = {"index": 174, "case": base[174][0], "selector": base[174][1],
               "requests": list(base[174][2])}
    state = {"stage": "pair_failed_no_retry", "expected_hmp_commit": module.partition.BASE_SOURCE,
             "native_commit": "a" * 40, "full_matrix_completed": False,
             "completed": completed, "current": current}
    prefix = {"source": module.partition.BASE_SOURCE, "native": "a" * 40,
              "full_matrix_complete": False, "pairs": prefix_rows}
    actor = {"role": "native_serving", "wait_known": True, "settlement_only_used": True,
             "settlement_wait_active": False, "returncode": 0, "process_pid": 123}
    failed = {"hmp_commit": module.partition.BASE_SOURCE, "native_commit": "a" * 40,
              "binding_cost_case": current["case"], "binding_cost_selector": current["selector"],
              "binding_writer": current["requests"], "commands": [actor]}
    if fault == "actor_live":
        actor["settlement_wait_active"] = True
    if fault == "actor_unknown":
        actor["wait_known"] = False
    if fault == "false_returncode":
        actor["returncode"] = False
    if fault == "wrong_request":
        current["requests"] = ["control:page", "append:page"]
    if fault == "prefix_bool_selector":
        prefix_rows[0]["selector"] = True
    if fault == "prefix_float_index":
        prefix_rows[0]["index"] = 0.0
    if fault == "wrong_source":
        prefix["source"] = "c" * 40

    def save(name, value):
        path = tmp_path / (name + ".json")
        data = json.dumps(value).encode()
        path.write_bytes(data)
        path.chmod(0o600)
        return path, hashlib.sha256(data).hexdigest()

    evidence = {"prefix": save("prefix", prefix), "state": save("state", state),
                "failed": save("failed", failed)}
    review = {"verdict": "ACCEPT", "proof_sha256": evidence["prefix"][1],
              "source": module.partition.BASE_SOURCE, "pairs": 174, "phases": 348,
              "artifacts": 5220, "copied_source_files": 2185962}
    if fault == "pending_review":
        review["verdict"] = "PENDING"
    if fault == "wrong_proof_review":
        review["proof_sha256"] = "e" * 64
    evidence["review"] = save("review", review)
    if fault == "tampered_evidence":
        evidence["failed"][0].write_text("{}")
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)

    def run(child, native, commit, **kwargs):
        index = len(calls)
        calls.append((child, kwargs))
        assert child.is_dir() and not tuple(child.iterdir())
        if index == fail_at:
            raise RuntimeError("synthetic owned failure")
        return {"completed": fault != "returned_false",
                "hmp_commit": "c" * 40 if fault == "returned_source" else "b" * 40,
                "report_sha256": "f" * 64}

    monkeypatch.setattr(module.driver, "run_fixture", run)
    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: types.SimpleNamespace(
        free=0 if capacity_at == len(calls) else 100 * 1024 ** 3))
    kwargs = {"evidence": evidence, "native_archive_cache": (tmp_path / "cache.tar", "c" * 64)}
    return module, root, calls, kwargs


def test_all_unattempted_jobs_execute_once_and_cannot_claim_full_matrix(tmp_path, monkeypatch):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch)
    result = module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    assert len(calls) == len(result["completed"]) == 301
    assert result["scope_execution_completed"] is True
    assert result["full_matrix_completed"] is False and result["original_refusal_preserved"] is True
    phases = [(r["origin_pair"], phase) for r in result["completed"]
              for phase in r["origin_phases"]]
    assert len(phases) == len(set(phases)) == 418
    assert all(index > 174 for index, _ in phases)
    assert all(k["expected_hmp_commit"] == "b" * 40 for _, k in calls)
    assert all(k["native_archive_cache"] == kwargs["native_archive_cache"] for _, k in calls)
    with pytest.raises(RuntimeError):
        module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    assert len(calls) == 301


@pytest.mark.parametrize("fault", ["actor_live", "actor_unknown", "false_returncode",
    "wrong_request",
    "prefix_bool_selector", "prefix_float_index", "wrong_source", "pending_review",
    "wrong_proof_review", "tampered_evidence"])
def test_unreconciled_evidence_refuses_before_admission_or_state_write(
    tmp_path, monkeypatch, fault
):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch, fault=fault)
    with pytest.raises(RuntimeError):
        module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    assert calls == [] and not tuple(root.iterdir())


@pytest.mark.parametrize("stop", [0, 2])
def test_owned_failure_keeps_exact_attempt_and_never_replays_or_admits_later_job(
    tmp_path, monkeypatch, stop
):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch, fail_at=stop)
    with pytest.raises(RuntimeError):
        module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    state = json.loads((root / "remaining-state.json").read_text())
    assert state["stage"] == "job_failed_no_retry" and state["current"]["index"] == stop
    assert len(calls) == stop + 1 and len(state["completed"]) == stop
    assert not (root / f"job-{stop + 1:03}").exists()
    assert state["full_matrix_completed"] is False


@pytest.mark.parametrize("stop", [0, 2])
def test_capacity_stops_before_next_job_root_without_losing_prior_results(
    tmp_path, monkeypatch, stop
):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch, capacity_at=stop)
    state = module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    assert len(calls) == len(state["completed"]) == stop
    assert state["stage"] == "capacity_refused_before_next_job"
    assert not (root / f"job-{stop:03}").exists() and not state["scope_execution_completed"]


@pytest.mark.parametrize("fault", ["returned_source", "returned_false"])
def test_unconfirmed_or_wrong_source_result_cannot_be_completed_or_retried(
    tmp_path, monkeypatch, fault
):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch, fault=fault)
    with pytest.raises(RuntimeError):
        module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    state = json.loads((root / "remaining-state.json").read_text())
    assert len(calls) == 1 and not state["completed"]
    assert state["stage"] == "job_failed_no_retry" and state["current"]["index"] == 0


@pytest.mark.parametrize("fault", ["symlink", "hardlink", "public_mode"])
def test_evidence_file_identity_guards_precede_any_job(tmp_path, monkeypatch, fault):
    module, root, calls, kwargs = fixture(tmp_path, monkeypatch)
    path, digest = kwargs["evidence"]["review"]
    if fault == "symlink":
        alias = tmp_path / "review-alias"
        alias.symlink_to(path)
        kwargs["evidence"]["review"] = (alias, digest)
    if fault == "hardlink":
        os.link(path, tmp_path / "second-link")
    if fault == "public_mode":
        path.chmod(0o644)
    with pytest.raises(RuntimeError):
        module.run_remaining(root, tmp_path / "native", "a" * 40, "b" * 40, **kwargs)
    assert calls == [] and not tuple(root.iterdir())
