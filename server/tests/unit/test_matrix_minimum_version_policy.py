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
