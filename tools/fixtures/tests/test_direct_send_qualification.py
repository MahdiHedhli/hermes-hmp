"""F3 fixture qualifications never alter runtime defaults or accept stale fingerprints."""
import json
import sys
from pathlib import Path

import _fixture_common as fc
import direct_send_fixture as dsf
import pytest
import yaml

from hmp_plugin import compat
from hmp_plugin.compat import compute_read_bridge_fingerprint, load_read_compat_list

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
             "qualified_by": "unit fixture", "qualified_at": "2026-09-28T00:00:00+00:00",
             "fingerprint": compute_read_bridge_fingerprint(src, data["bridge_files"])}
    receipt.write_text(json.dumps({**data, "builds": [entry]}))
    build = fc.BuildInfo("stock-base", src, src / "python")
    dsf.install_fixture_qualification(build, out, receipt)
    assert json.loads(target.read_text())["builds"] == [entry]
    load_read_compat_list(target)
    for missing in ("qualified_by", "qualified_at"):
        invalid = {k: v for k, v in entry.items() if k != missing}
        receipt.write_text(json.dumps({**data, "builds": [invalid]}))
        with pytest.raises(fc.FixtureSafetyError, match="schema"):
            dsf.install_fixture_qualification(build, out, receipt)
        assert json.loads(target.read_text())["builds"] == [entry]
    receipt.write_text(json.dumps({**data, "builds": [entry]}))
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


@pytest.mark.parametrize("outcome", ["pass", "failure", "skipped", "empty"])
def test_matrix_receipts_are_loadable_by_the_runtime_gate(tmp_path, monkeypatch, outcome):
    """Exercise both receipt producers and the installer, without launching a gateway.

    Round 3 copied identity-only candidates into the runtime list. Its mandatory provenance
    fields were missing, so the real parser rejected the list before endpoint resolution.
    """
    from types import SimpleNamespace

    builds = tmp_path / "builds"
    src = builds / "stock-base" / "src"
    (src / ".venv" / "bin").mkdir(parents=True)
    python = src / ".venv" / "bin" / "python"
    python.touch()
    (src / "security.py").write_text("# fixture security behavior\n")
    data = {"format": 1, "bridge_files": ["security.py"], "builds": []}
    compat_path = tmp_path / "committed.json"
    compat_path.write_text(json.dumps(data))
    monkeypatch.setattr(run_matrix, "DIRECT_COMPAT_PATH", compat_path)
    monkeypatch.setattr(run_matrix, "resolve_source_sha", lambda spec: None)
    monkeypatch.setattr(run_matrix, "load_build_specs", lambda: [
        run_matrix.BuildSpec("stock-base", "unused", "unused", False)])
    fixture = tmp_path / "fixture"
    plugin = fixture / "_hmp_plugin"
    plugin.mkdir(parents=True)
    installed = plugin / "direct_send_supported_builds.json"
    installed.write_text(json.dumps(data))
    monkeypatch.setattr(compat, "_DIRECT_SEND_LIST", installed)
    monkeypatch.setattr(compat, "locate_hermes_root", lambda: src)
    monkeypatch.setattr(compat, "probe_direct_send_dependencies", lambda **kwargs: ())

    def check_receipt(path, *, provisional):
        parsed = load_read_compat_list(path)
        entry, = parsed.builds
        assert bool(entry.qualified_at)
        assert ("provisional" in entry.qualified_by) is provisional
        dsf.install_fixture_qualification(fc.BuildInfo("stock-base", src, python), fixture, path)
        assert compat._direct_send_build_qualified()
        # Provenance never substitutes for exact source identity.
        source = src / "security.py"
        original = source.read_text()
        source.write_text(original + "# changed\n")
        assert not compat._direct_send_build_qualified()
        source.write_text(original)

    stages = []

    def run(cmd, **kwargs):
        if "pytest" in cmd:
            stages.append("integration")
            check_receipt(Path(kwargs["env"]["HMP_DIRECT_SEND_QUALIFICATION"]), provisional=True)
            report = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--junitxml="))
            case = "" if outcome == "pass" else f"<{outcome}/>"
            cases = "" if outcome == "empty" else f"<testcase>{case}</testcase>"
            Path(report).write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>")
        else:
            stages.append("probe")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run_matrix.subprocess, "run", run)
    out = tmp_path / "matrix"
    receipt = out / "qualified.json"
    result = run_matrix.main([
        "--target", "direct-send", "--builds-dir", str(builds), "--builds", "stock-base",
        "--out", str(out), "--fixture-qualification-out", str(receipt),
    ])
    assert stages == ["probe", "probe", "integration"]
    assert result == (0 if outcome == "pass" else 1)
    if outcome == "pass":
        check_receipt(receipt, provisional=False)
    else:
        assert not receipt.exists()
    assert json.loads(compat_path.read_text()) == data
