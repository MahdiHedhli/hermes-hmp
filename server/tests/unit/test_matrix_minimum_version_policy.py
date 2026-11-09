"""Matrix reporting must preserve the owner's minimum-version policy."""
import importlib.util
import sys
from pathlib import Path


def matrix_module():
    path = Path(__file__).resolve().parents[3] / "tools/compat/run_matrix.py"
    spec = importlib.util.spec_from_file_location("hmp_matrix_policy_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_matrix_policy_preserves_unlisted_support_and_required_api_gates(tmp_path):
    result = matrix_module().minimum_version_policy_check(tmp_path)
    assert result["ok"]
    assert all(result[key] for key in (
        "listed_supported", "unlisted_supported", "unknown_version_probes_supported",
        "missing_api_refused", "below_floor_refused_without_probe"))
    assert "synthetic" in result["scope"]


def test_matrix_policy_does_not_qualify_when_actual_gate_is_broken(tmp_path, monkeypatch):
    from hmp_plugin import compat
    original = compat.CompatGate.evaluate

    def refuse(self):
        result = original(self)
        if result.status is compat.CompatStatus.SUPPORTED:
            return compat.CompatResult(compat.CompatStatus.UNSUPPORTED)
        return result

    monkeypatch.setattr(compat.CompatGate, "evaluate", refuse)
    result = matrix_module().minimum_version_policy_check(tmp_path)
    assert not result["ok"] and not result["unlisted_supported"]


def test_matrix_report_preserves_runtime_failure_and_labels_policy_scope(tmp_path, monkeypatch, capsys):
    import json
    module = matrix_module()
    builds = tmp_path / "builds"
    builds.mkdir()
    outcomes = [True, False]
    calls = []

    def process(spec, _builds, _scratch):
        calls.append(spec.label)
        return {"label": spec.label, "qualified": outcomes[0],
                "fingerprint": "a" * 64, "git_sha": None, "source_sha": "b" * 40}

    monkeypatch.setattr(module, "process_build", process)
    args = ["--builds-dir", str(builds), "--out", str(tmp_path / "scratch"),
            "--builds", "stock-base"]
    assert module.main(args) == 0
    passed = json.loads(capsys.readouterr().out)
    assert passed["sc007_unsupported_path_check"] is None
    assert passed["minimum_version_policy_check"]["ok"]
    assert "synthetic" in passed["minimum_version_policy_check"]["scope"]
    assert len(passed["candidate_entries"]) == 1
    outcomes[0] = False
    assert module.main(args) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["candidate_entries"] == []
    assert failed["minimum_version_policy_check"] is None
    assert calls == ["stock-base", "stock-base"]
