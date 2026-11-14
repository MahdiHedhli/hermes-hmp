"""Opt-in nonfatal seed stack diagnostics (specs/005 amendment 5). Real child processes run
`fixture_seed.main` with a synthetic handler: never a Hermes build, gateway, model or network. The
short interval is injected only inside those synthetic children; the production constant (90 s)
and the `run_seed_script` deadline (120 s) are asserted unchanged."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import _fixture_common as fc
import build_fixture as bf
import direct_send_fixture as dsf
import fixture_seed as fs
import pytest

CHILD = """
import sys, time
sys.path.insert(0, {tools!r})
import fixture_seed as fs
fs._DIAGNOSTIC_STACK_SECONDS = 0.4
MODE = {mode!r}

def synthetic_slow_handler(args):
    if MODE == "slow":
        time.sleep(1.2)
    if MODE == "raise":
        raise RuntimeError("synthetic")
    fs._out({{"ok": True, "handler": "done"}})
    if MODE == "exit":
        sys.exit(3)

fs.cmd_compat_identity = synthetic_slow_handler
code = 0
try:
    code = fs.main({argv!r})
except SystemExit as exc:  # outside fs.main: only its `finally` can have cancelled the timer
    code = exc.code
if MODE != "slow":
    time.sleep(1.0)  # well past the interval: a timer left armed would dump here
sys.exit(code)
"""
TOOLS = str(Path(fs.__file__).resolve().parent)


def _run(mode: str, *flags: str) -> subprocess.CompletedProcess[str]:
    code = CHILD.format(tools=TOOLS, mode=mode, argv=[*flags, "compat-identity"])
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False,
        env={"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60,
    )


def _stdout_contract(run: subprocess.CompletedProcess[str]) -> None:
    assert json.loads(run.stdout) == {"ok": True, "handler": "done"}
    assert run.stdout.count("\n") == 1


def test_constants_are_unchanged() -> None:
    assert fs._DIAGNOSTIC_STACK_SECONDS == 90.0
    import inspect

    assert inspect.signature(fc.run_seed_script).parameters["timeout"].default == 120.0


def test_slow_handler_dumps_one_stack_to_stderr_and_stdout_is_unchanged() -> None:
    run = _run("slow", "--diagnostic-stacks")
    assert run.returncode == 0
    _stdout_contract(run)  # success even after the dump
    assert "synthetic_slow_handler" in run.stderr
    assert run.stderr.count("most recent call first") == 1  # exit=False, repeat=False


def test_default_invocation_has_no_trace_and_same_stdout() -> None:
    run = _run("slow")
    assert run.returncode == 0
    _stdout_contract(run)
    assert run.stderr == ""


@pytest.mark.parametrize(
    ("mode", "code", "stdout"),
    [
        ("fast", 0, {"ok": True, "handler": "done"}),
        ("exit", 3, {"ok": True, "handler": "done"}),  # handler SystemExit, caught outside main
        ("raise", 1, {"ok": False, "error": "RuntimeError: synthetic"}),  # _fail -> SystemExit
    ],
)
def test_timer_is_cancelled_on_return_systemexit_and_failure(mode, code, stdout) -> None:
    run = _run(mode, "--diagnostic-stacks")
    assert run.returncode == code
    assert json.loads(run.stdout) == stdout and run.stdout.count("\n") == 1
    assert "most recent call first" not in run.stderr and "synthetic" not in run.stderr


def test_flag_must_precede_the_subcommand_with_the_real_parser() -> None:
    parser = fs.build_parser()
    assert parser.parse_args(["compat-identity"]).diagnostic_stacks is False
    assert parser.parse_args(["--diagnostic-stacks", "compat-identity"]).diagnostic_stacks is True
    with pytest.raises(SystemExit):
        parser.parse_args(["compat-identity", "--diagnostic-stacks"])


def _instance() -> dict:
    return {
        "key": "A", "users": [{"key": "u"}],
        "profiles": [{
            "name": "p", "authorize_for": ["u"], "conversation": "c",
            "other_sessions": [{"session_id": "s", "source": "cli", "conversation": "c"}],
        }],
    }


@pytest.mark.parametrize("flag", [False, True])
def test_only_seed_messages_receives_the_flag(tmp_path, monkeypatch, flag) -> None:
    calls: list[tuple[str, ...]] = []

    def record(build, script, *args, **kw):
        calls.append(args)
        return SimpleNamespace(stdout=json.dumps({"request_id": "r", "session_id": "sid"}))

    monkeypatch.setattr(fc, "run_seed_script", record)
    paths = fc.instance_paths(tmp_path, "A")
    monkeypatch.setattr(
        fc, "run_hermes_cli", lambda *a, **k: (paths.home / "profiles" / "p").mkdir(parents=True)
        if a[2:4] == ("profile", "create") else None,
    )
    monkeypatch.setattr(fc, "assert_instance_paths_safe", lambda p: None)
    monkeypatch.setattr(fc, "ensure_plugin_data_dir", lambda p: None)
    monkeypatch.setattr(bf, "_write_config_yaml", lambda *a, **k: None)
    monkeypatch.setattr(bf, "_install_plugin_symlink", lambda *a, **k: None)
    monkeypatch.setattr(bf, "_generate_conversation_messages", lambda *a, **k: [])
    kwargs = {"private_seed_diagnostics": True} if flag else {}
    bf.build_instance_if_needed(
        None, paths, {"label_prefix": "x", "conversations": {"c": {}}}, _instance(), tmp_path,
        force=False, **kwargs,
    )
    commands = [c[0] for c in calls]
    assert set(commands) >= {"insert-user", "set-chat", "p6-generate", "seed-session"}
    flagged = [c for c in calls if "--diagnostic-stacks" in c]
    if flag:
        assert len(flagged) == 1 and flagged[0][:2] == ("--diagnostic-stacks", "seed-messages")
    else:
        assert flagged == [] and "seed-messages" in commands


def test_build_fixture_flag_defaults_false_and_is_offline_only() -> None:
    import inspect

    for fn in (bf.build_instance, bf.build_instance_if_needed):
        assert inspect.signature(fn).parameters["private_seed_diagnostics"].default is False
    with pytest.raises(SystemExit):
        bf.main(["--build", "b", "--out", "/nonexistent", "--serve", "--private-seed-diagnostics"])


def _capturing_build(tmp_path: Path, monkeypatch, body: str) -> list[list[str]]:
    script = tmp_path / "stub_build.py"
    script.write_text(body, encoding="utf-8")
    monkeypatch.setattr(dsf, "BUILD_FIXTURE", script)
    argvs: list[list[str]] = []
    real_run = subprocess.run
    monkeypatch.setattr(
        dsf.subprocess, "run", lambda a, **k: argvs.append(list(a)) or real_run(a, **k)
    )
    return argvs


def test_build_offline_passes_the_flag_and_failure_trace_stays_private(
    tmp_path, monkeypatch
) -> None:
    argvs = _capturing_build(
        tmp_path, monkeypatch,
        "import sys\nassert '--private-seed-diagnostics' in sys.argv\n"
        "sys.stderr.write('Stack (most recent call first): STACK-MARKER')\nsys.exit(5)\n",
    )
    out = tmp_path / "out"
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", out, builds_dir=str(tmp_path))
    assert "--private-seed-diagnostics" in argvs[0]
    message = str(caught.value)
    assert "exit_code=5" in message and "private_output=retained" in message
    assert "STACK-MARKER" not in message and caught.value.__cause__ is None
    kept = out / dsf.BUILD_FAILURE_OUTPUT
    assert stat.S_IMODE(kept.stat().st_mode) == 0o600
    assert "STACK-MARKER" in kept.read_text(encoding="utf-8")


def test_build_offline_success_stdout_contract_survives_a_stack_on_stderr(
    tmp_path, monkeypatch
) -> None:
    _capturing_build(
        tmp_path, monkeypatch,
        "import sys, json\nsys.stderr.write('Stack (most recent call first): STACK-MARKER')\n"
        "print(json.dumps({'ok': True, 'instances': []}))\n",
    )
    monkeypatch.delenv("HMP_DIRECT_SEND_QUALIFICATION", raising=False)
    monkeypatch.delenv("HMP_APPROVAL_QUALIFICATION", raising=False)
    out = tmp_path / "out"
    assert dsf.build_offline("b", out, builds_dir=str(tmp_path)) == {"ok": True, "instances": []}
    assert not (out / dsf.BUILD_FAILURE_OUTPUT).exists()


def test_unsafe_destination_launches_no_child_and_never_gets_the_flag(
    tmp_path, monkeypatch
) -> None:
    argvs = _capturing_build(tmp_path, monkeypatch, "import sys\nsys.exit(1)\n")
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    (tmp_path / "link").symlink_to(real)
    with pytest.raises(dsf.fc.FixtureSafetyError) as caught:
        dsf.build_offline("b", tmp_path / "link" / "out", builds_dir=str(tmp_path))
    assert "phase=build_offline_destination" in str(caught.value)
    assert argvs == []


MARKER = "zq_private_stack_marker"
CHILD_FILE = """
import sys, time
sys.path.insert(0, {tools!r})
import fixture_seed as fs
fs._DIAGNOSTIC_STACK_SECONDS = 0.4

def {marker}_handler(args):
    time.sleep(1.2)
    fs._out({{"ok": True}})

fs.cmd_compat_identity = {marker}_handler
sys.exit(fs.main(["--diagnostic-stacks", "compat-identity"]))
"""
STUB_BUILDER = """
import subprocess, sys
r = subprocess.run([sys.executable, {child!r}], capture_output=True)
sys.stderr.buffer.write(r.stderr)
sys.exit(5)
"""
# No marker text in this source: a long traceback prints source lines into the report.
NESTED_TEST = """
import os
from pathlib import Path

import direct_send_fixture as dsf


def test_nested_build_failure(monkeypatch):
    monkeypatch.setattr(dsf, "BUILD_FIXTURE", Path(os.environ["NESTED_STUB"]))
    out = Path(os.environ["NESTED_OUT"])
    try:
        dsf.build_offline("b", out, builds_dir=os.environ["NESTED_SCRATCH"])
    except dsf.fc.FixtureSafetyError:
        if os.environ.get("NESTED_LEAK"):
            raise AssertionError((out / dsf.BUILD_FAILURE_OUTPUT).read_text())
        raise
"""


def _nested_report(tmp_path: Path, name: str, leak: bool) -> tuple[str, str]:
    """Run the failing nested pytest; return (public report, private retained failure file)."""
    scratch = tmp_path / name
    scratch.mkdir(mode=0o700)
    scratch.chmod(0o700)
    child = scratch / f"{MARKER}_child.py"
    child.write_text(CHILD_FILE.format(tools=TOOLS, marker=MARKER), encoding="utf-8")
    stub = scratch / "stub_build.py"
    stub.write_text(STUB_BUILDER.format(child=str(child)), encoding="utf-8")
    (scratch / "test_nested.py").write_text(NESTED_TEST, encoding="utf-8")
    out = scratch / "out"
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": os.pathsep.join([TOOLS, str(Path(TOOLS).parents[1] / "server")]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NESTED_STUB": str(stub), "NESTED_OUT": str(out), "NESTED_SCRATCH": str(scratch),
    }
    if leak:
        env["NESTED_LEAK"] = "1"
    log = scratch / "nested_report.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as sink:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--tb=long", "-q",
             "--rootdir", str(scratch), str(scratch / "test_nested.py")],
            stdout=sink, stderr=subprocess.STDOUT, env=env, cwd=scratch, check=False, timeout=120,
        )
    assert done.returncode == 1  # the nested test failed, so a report was produced
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    kept = out / dsf.BUILD_FAILURE_OUTPUT
    assert stat.S_IMODE(kept.stat().st_mode) == 0o600
    return log.read_text(encoding="utf-8"), kept.read_text(encoding="utf-8")


def test_real_diagnostic_stack_stays_out_of_the_public_pytest_report(tmp_path) -> None:
    report, private = _nested_report(tmp_path, "closed", leak=False)
    # the real faulthandler dump happened and was retained privately, with both markers
    assert "most recent call first" in private
    assert f"{MARKER}_handler" in private and f"{MARKER}_child.py" in private
    # the public long report reached the closed failure but carries no stack text
    assert "FixtureSafetyError" in report and "exit_code=5" in report
    assert MARKER not in report and "most recent call first" not in report


def test_leaky_control_proves_the_nested_report_would_show_the_marker(tmp_path) -> None:
    report, private = _nested_report(tmp_path, "leaky", leak=True)
    assert f"{MARKER}_handler" in private
    assert MARKER in report  # a leak is detectable by the same check
