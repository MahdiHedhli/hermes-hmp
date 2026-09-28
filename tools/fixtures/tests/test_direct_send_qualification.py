"""F3 fixture qualifications never alter runtime defaults or accept stale fingerprints."""
import json
import sys
from pathlib import Path

import _fixture_common as fc
import direct_send_fixture as dsf
import pytest
import yaml

from hmp_plugin.compat import compute_read_bridge_fingerprint

COMPAT = Path(__file__).resolve().parents[2] / "compat"
sys.path.insert(0, str(COMPAT))
import bridge_files  # noqa: E402
import run_matrix  # noqa: E402


def test_config_owner_is_explicit_and_survives_flag_rewrite(tmp_path):
    paths = fc.instance_paths(tmp_path, "A")
    (paths.home / "profiles" / "f1-alpha").mkdir(parents=True)
    kwargs = {"hmp_port": 1234, "api_server_port": 5678, "api_key": "fixture-key",
              "model_base_url": "http://127.0.0.1:9876"}
    for owners, enabled in [((), True), (("fixture-device",), True), (("fixture-device",), False)]:
        dsf.write_direct_send_config(paths, ("f1-alpha",), owner_device_ids=owners,
                                    direct_send_enabled=enabled, **kwargs)
        config = yaml.safe_load((paths.home / "config.yaml").read_text())
        extra = config["gateway"]["platforms"]["hmp"]["extra"]
        assert extra["owner_device_ids"] == list(owners)
        assert extra["direct_send"]["enabled"] is enabled


def test_fixture_receipt_requires_exact_boundary_and_bytes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    source = src / "security.py"
    source.write_text("# fixture security behavior\n")
    out = tmp_path / "fixture"
    plugin = out / "_hmp_plugin"
    plugin.mkdir(parents=True)
    target = plugin / "direct_send_supported_builds.json"
    data = {"format": 1, "bridge_files": ["security.py"], "builds": []}
    target.write_text(json.dumps(data))
    receipt = tmp_path / "receipt.json"
    entry = {"label": "stock-base", "git_sha": None,
             "fingerprint": compute_read_bridge_fingerprint(src, data["bridge_files"])}
    receipt.write_text(json.dumps({**data, "builds": [entry]}))
    build = fc.BuildInfo("stock-base", src, src / "python")
    dsf.install_fixture_qualification(build, out, receipt)
    assert json.loads(target.read_text())["builds"] == [entry]
    source.write_text("# changed security behavior\n")
    with pytest.raises(fc.FixtureSafetyError, match="no exact"):
        dsf.install_fixture_qualification(build, out, receipt)
    receipt.write_text(json.dumps({**data, "bridge_files": [], "builds": [entry]}))
    with pytest.raises(fc.FixtureSafetyError, match="boundary"):
        dsf.install_fixture_qualification(build, out, receipt)


def test_boundary_growth_requires_requalification(tmp_path):
    target = tmp_path / "compat.json"
    entry = {"label": "previous", "fingerprint": "old-observed-value", "git_sha": None}
    target.write_text(json.dumps({"bridge_files": ["old.py"], "builds": [entry]}))
    bridge_files.write_merged({"new.py"}, target)
    data = json.loads(target.read_text())
    assert data["builds"] == []
    assert data["requalification_required"][0]["fingerprint"] == entry["fingerprint"]
    assert data["bridge_files"] == ["new.py", "old.py"]


@pytest.mark.parametrize("outcome", ["", "<skipped/>", "<failure/>", "<error/>"])
def test_matrix_rejects_skipped_failed_or_empty_suite(tmp_path, outcome):
    path = tmp_path / "integration.xml"
    path.write_text(f"<testsuites><testsuite><testcase>{outcome}</testcase></testsuite></testsuites>")
    assert run_matrix.integration_report_passed(path) is (outcome == "")
    path.write_text("<testsuites/>")
    assert not run_matrix.integration_report_passed(path)


@pytest.mark.parametrize("fail_stage", ["boundary", "behavior", "integration"])
def test_matrix_failure_never_qualifies_build(tmp_path, monkeypatch, fail_stage):
    from types import SimpleNamespace

    builds = tmp_path / "builds"
    src = builds / "stock-base" / "src"
    (src / ".venv" / "bin").mkdir(parents=True)
    (src / ".venv" / "bin" / "python").touch()
    (src / "security.py").write_text("# fixture\n")
    compat_path = tmp_path / "compat.json"
    compat_path.write_text(json.dumps({"format": 1, "bridge_files": ["security.py"], "builds": []}))
    monkeypatch.setattr(run_matrix, "DIRECT_COMPAT_PATH", compat_path)
    monkeypatch.setattr(run_matrix, "resolve_source_sha", lambda spec: None)
    stages = iter(["boundary", "behavior", "integration"])
    reached = []

    def run(*args, **kwargs):
        stage = next(stages)
        reached.append(stage)
        return SimpleNamespace(returncode=int(stage == fail_stage), stdout="", stderr="")

    monkeypatch.setattr(run_matrix.subprocess, "run", run)
    spec = run_matrix.BuildSpec("stock-base", "unused", "unused", False)
    result = run_matrix.process_direct_build(spec, builds, tmp_path / "matrix")
    assert result["qualified"] is False
    assert reached[-1] == fail_stage
    assert json.loads(compat_path.read_text())["builds"] == []
