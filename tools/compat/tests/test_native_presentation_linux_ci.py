"""Synthetic CI failure/privacy contracts; no download, Docker or native run."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

_SPEC = importlib.util.spec_from_file_location(
    "linux_ci", Path(__file__).parents[1] / "native_presentation_linux_ci.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


@pytest.mark.parametrize("diagnostic_failure", [False, True])
def test_setup_failure_never_falls_back_to_raw_console_output(
    tmp_path, monkeypatch, capsys, diagnostic_failure
):
    # Simulated bootstrap metadata only; stub preparer raises before any real setup.
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(
            platform="linux",
            dont_write_bytecode=True,
            flags=SimpleNamespace(isolated=1, optimize=0),
            modules=sys.modules,
        ),
    )
    monkeypatch.setattr(module.os, "uname", lambda: SimpleNamespace(machine="x86_64"))
    tools = tmp_path / "tools"
    tools.mkdir(mode=0o700)
    (tools / "native_presentation_linux_prepare.py").write_text(
        'def prepare(*args):\n raise RuntimeError("SYNTHETIC_SECRET_DO_NOT_PRINT")\n'
    )
    monkeypatch.setattr(module, "__file__", str(tools / "native_presentation_linux_ci.py"))
    workspace, temporary = tmp_path / "workspace", tmp_path / "temporary"
    temporary.mkdir(mode=0o700)
    workspace.mkdir(mode=0o700)
    for name in ("native-reference", "hmp"):
        (workspace / name).mkdir(mode=0o700)
    output = tmp_path / "synthetic-github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setitem(sys.modules, "_native_ci_preparer", None)
    original_open = os.open

    def maybe_fail(path, *args, **kwargs):
        if diagnostic_failure and str(path).endswith("/private-failure.json"):
            raise OSError("SYNTHETIC_DIAGNOSTIC_FAILURE")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", maybe_fail)
    assert module.run(workspace, temporary) == 1
    captured = capsys.readouterr()
    assert "SYNTHETIC_SECRET" not in captured.out + captured.err
    assert "SYNTHETIC_DIAGNOSTIC_FAILURE" not in captured.out + captured.err
    result = json.loads(captured.out)
    assert result["stage"] == "prepare-pinned-software" and result["errorType"] == "RuntimeError"
    assert result["diagnosticWriteFailed"] is diagnostic_failure
    root = Path(output.read_text().strip().split("=", 1)[1])
    assert root.parent == temporary and root.stat().st_mode & 0o777 == 0o700
    if not diagnostic_failure:
        path = root / "private-failure.json"
        assert path.stat().st_mode & 0o777 == 0o600
        assert "SYNTHETIC_SECRET_DO_NOT_PRINT" in path.read_text()


def test_workflow_limits_trigger_permissions_and_exports_ciphertext_only():
    path = Path(__file__).parents[3] / ".github/workflows/native-presentation-linux.yml"
    workflow = yaml.safe_load(path.read_text())
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["on"]) == {"push"}
    assert workflow["on"]["push"]["branches"] == ["feat/native-linux-preparation-20261116"]
    job = workflow["jobs"]["complete-native-journey"]
    assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == 50
    steps = job["steps"]
    assert len(steps) == 5
    assert all(
        step["uses"] == "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
        for step in steps[:2]
    )
    assert all(step["with"]["persist-credentials"] is False for step in steps[:2])
    assert steps[1]["with"]["ref"] == "ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df"
    artifact = steps[-1]
    assert artifact["uses"] == "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    assert artifact["with"]["path"] == "${{ steps.encrypt.outputs.ciphertext }}"
    assert artifact["with"]["retention-days"] == 2
    assert "secrets." not in path.read_text()
