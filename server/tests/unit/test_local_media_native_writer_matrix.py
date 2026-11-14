"""Matrix admission/ownership models; never execute Git, native DB or network work."""
import importlib.util
import json
import types
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_writer_matrix.py"


def load():
    spec = importlib.util.spec_from_file_location("_writer_matrix_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, *, failure=None, capacity_at=None, wrong_source=False):
    module, calls = load(), []
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)

    def space(path):
        assert path == root
        return types.SimpleNamespace(free=0 if capacity_at == len(calls) else 100 * 1024 ** 3)

    def run(child, native, commit, **kwargs):
        index = len(calls)
        calls.append((child, kwargs))
        assert child.is_dir() and not tuple(child.iterdir())
        assert native == tmp_path / "native" and commit == "a" * 40
        if index == failure:
            raise RuntimeError("synthetic failure")
        return {"completed": True, "hmp_commit": "c" * 40 if wrong_source else "b" * 40,
                "report_sha256": "d" * 64}

    monkeypatch.setattr(module.shutil, "disk_usage", space)
    monkeypatch.setattr(module.driver, "run_fixture", run)
    return module, root, calls


def test_all_pairs_retained_once_with_exact_source_and_no_reuse(tmp_path, monkeypatch):
    module, root, calls = fixture(tmp_path, monkeypatch)
    result = module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40)
    assert result["full_matrix_completed"] is True and result["production_qualified"] is False
    assert result["stage"] == "matrix_completed_artifact_review_pending"
    assert len(calls) == len(result["completed"]) == 456
    assert len({child for child, _ in calls}) == 456
    phases = [(kw["binding_cost_case"], kw["binding_cost_selector"], request)
              for _, kw in calls for request in kw["binding_writer"]]
    assert len(phases) == len(set(phases)) == 912
    assert all(kw["expected_hmp_commit"] == "b" * 40 for _, kw in calls)
    saved = json.loads((root / "matrix-state.json").read_text())
    assert saved["full_matrix_completed"] is True and saved["current"] is None
    with pytest.raises(RuntimeError):
        module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40)
    assert len(calls) == 456


@pytest.mark.parametrize("capacity_at", [0, 2])
def test_low_capacity_stops_before_next_pair_and_preserves_prior_results(
    tmp_path, monkeypatch, capacity_at
):
    module, root, calls = fixture(tmp_path, monkeypatch, capacity_at=capacity_at)
    result = module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40)
    assert len(calls) == len(result["completed"]) == capacity_at
    assert result["stage"] == "capacity_refused_before_next_pair"
    assert not result["full_matrix_completed"]
    assert not (root / f"pair-{capacity_at:03}").exists()


@pytest.mark.parametrize("failure", [0, 2])
def test_failure_preserves_attempt_and_never_retries_or_admits_later_pair(
    tmp_path, monkeypatch, failure
):
    module, root, calls = fixture(tmp_path, monkeypatch, failure=failure)
    with pytest.raises(RuntimeError):
        module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40)
    saved = json.loads((root / "matrix-state.json").read_text())
    assert saved["stage"] == "pair_failed_no_retry" and saved["current"]["index"] == failure
    assert len(saved["completed"]) == failure and len(calls) == failure + 1
    assert (root / f"pair-{failure:03}").is_dir()
    assert not (root / f"pair-{failure + 1:03}").exists()
    assert not saved["full_matrix_completed"]


def test_wrong_source_cannot_promote_completion_or_admit_next_pair(tmp_path, monkeypatch):
    module, root, calls = fixture(tmp_path, monkeypatch, wrong_source=True)
    with pytest.raises(RuntimeError):
        module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40)
    saved = json.loads((root / "matrix-state.json").read_text())
    assert len(calls) == 1 and not saved["completed"]
    assert saved["stage"] == "pair_failed_no_retry"


def test_supplement_runs_only_additions_without_claiming_full_matrix(tmp_path, monkeypatch):
    module, root, calls = fixture(tmp_path, monkeypatch)
    result = module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40,
                               scope="divergence_supplement")
    assert result["scope_execution_completed"] is True
    assert result["full_matrix_completed"] is False and result["production_qualified"] is False
    assert result["stage"] == "supplement_completed_artifact_review_pending"
    assert len(calls) == len(result["completed"]) == 72
    phases = [(kw["binding_cost_case"], kw["binding_cost_selector"], request)
              for _, kw in calls for request in kw["binding_writer"]]
    expected = {(case, selector, scenario + ":" + seam)
                for case in range(8) for selector in (1, 16, 128)
                for scenario in ("ordinary_child", "delegate_child")
                for seam in module.driver.writer_contract.SEAMS}
    assert len(phases) == len(set(phases)) == len(expected) == 144
    assert set(phases) == expected


@pytest.mark.parametrize("scope", [None, True, "resume", "all", ""])
def test_unknown_execution_scope_refuses_before_state_or_pair_creation(
    tmp_path, monkeypatch, scope
):
    module, root, calls = fixture(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError):
        module.run_matrix(root, tmp_path / "native", "a" * 40, "b" * 40, scope=scope)
    assert calls == [] and not tuple(root.iterdir())
