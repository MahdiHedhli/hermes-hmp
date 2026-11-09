"""Known matrix builds must not be parameterized twice by candidate selection."""
import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize("candidate,present", (("stock-base", True), ("experimental", True),
    ("owner-local", True), ("new-candidate", True), ("missing-candidate", False), ("", False)))
def test_read_fixture_candidate_is_enrolled_once(tmp_path, monkeypatch, candidate, present):
    for name in {"stock-base", "experimental"} | ({candidate} if present else set()):
        (tmp_path / name / "src").mkdir(parents=True)
    monkeypatch.setenv("HMP_HERMES_BUILDS_DIR", str(tmp_path))
    monkeypatch.setenv("HMP_COMPAT_CANDIDATE_LABEL", candidate)
    path = Path(__file__).resolve().parents[1] / "integration/test_reads_fixture.py"
    spec = importlib.util.spec_from_file_location("hmp_fixture_candidate_census", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # declarations only; no fixture/gateway/test invocation
    assert module.BUILDS[:2] == ("stock-base", "experimental")
    assert len(module.BUILDS) == len(set(module.BUILDS))
    if candidate:
        assert module.BUILDS.count(candidate) == int(present)
