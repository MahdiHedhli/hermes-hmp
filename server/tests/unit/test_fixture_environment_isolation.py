"""Fixture child environments use synthetic values and never launch native code."""
import importlib.util
import sys
from pathlib import Path

import pytest


def common():
    path = Path(__file__).resolve().parents[3] / "tools/fixtures/_fixture_common.py"
    spec = importlib.util.spec_from_file_location("hmp_fixture_environment_test", path)
    module = importlib.util.module_from_spec(spec)
    before = list(sys.path)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
        sys.path[:] = before
    return module


@pytest.mark.parametrize("name", ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_SESSION_TOKEN",
    "UNKNOWN_FUTURE_PROVIDER_TOKEN", "HTTPS_PROXY", "PYTHONPATH", "PYTHONHOME",
    "PYTHONSTARTUP", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "HERMES_HOME", "XDG_CONFIG_HOME"))
def test_inherited_secret_and_injection_names_never_reach_child(monkeypatch, name):
    monkeypatch.setenv(name, "synthetic-test-value")
    assert name not in common().clean_hermes_env()


def test_explicit_isolated_paths_and_process_settings_survive(tmp_path, monkeypatch):
    monkeypatch.setenv("LANG", "C")
    module = common()
    extra = {"HERMES_HOME": str(tmp_path / "hermes"), "XDG_STATE_HOME": str(tmp_path / "state")}
    env = module.clean_hermes_env(extra=extra)
    assert env["LANG"] == "C" and env["PATH"]
    assert all(env[key] == value for key, value in extra.items())
    assert set(env) <= module._PROCESS_ENV_KEYS | module._FIXTURE_ENV_KEYS


@pytest.mark.parametrize("extra", ({"OPENAI_API_KEY": "synthetic"},
    {"PYTHONPATH": "/synthetic"}, {"HERMES_HOME": ""}, {"HERMES_HOME": "bad\x00path"}))
def test_explicit_escape_or_invalid_path_refused(extra):
    module = common()
    with pytest.raises(module.FixtureSafetyError):
        module.clean_hermes_env(extra=extra)


def test_real_owner_home_refused_for_explicit_native_home():
    module = common()
    with pytest.raises(module.FixtureSafetyError):
        module.clean_hermes_env(extra={"HERMES_HOME": str(Path.home() / ".hermes")})


def test_seed_child_uses_fixed_module_path_and_no_inherited_credentials(tmp_path, monkeypatch):
    from types import SimpleNamespace
    module = common()
    monkeypatch.setenv("UNKNOWN_FUTURE_PROVIDER_TOKEN", "synthetic-test-value")
    monkeypatch.setenv("PYTHONPATH", "/synthetic-external-code")
    captured = []

    def run(command, **kwargs):
        captured.append((command, kwargs["env"]))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", run)
    build = module.BuildInfo("synthetic", tmp_path / "source", tmp_path / "python")
    module.run_seed_script(build, tmp_path / "synthetic-helper.py")
    assert len(captured) == 1
    command, env = captured[0]
    assert command == [str(build.venv_python), str(tmp_path / "synthetic-helper.py")]
    assert env["PYTHONPATH"] == str(module.SERVER_DIR)
    assert "UNKNOWN_FUTURE_PROVIDER_TOKEN" not in env


@pytest.mark.parametrize("reply,code", (("{\"aiohttp\":\"1\",\"cryptography\":\"2\",\"qrcode\":\"3\"}", 0),
    ("{\"aiohttp\":null,\"cryptography\":\"2\",\"qrcode\":null}", 0),
    ("private-child-diagnostic", 1), ("[]", 0)))
def test_dependency_preflight_never_installs_or_leaks_child_diagnostics(tmp_path, monkeypatch, reply, code):
    from types import SimpleNamespace
    module = common()
    monkeypatch.setenv("UNKNOWN_FUTURE_PROVIDER_TOKEN", "synthetic-test-value")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=code, stdout=reply, stderr="private-child-diagnostic")

    monkeypatch.setattr(module.subprocess, "run", run)
    build = module.BuildInfo("synthetic", tmp_path / "source", tmp_path / "python")
    if code == 0 and reply.startswith('{"aiohttp":"1"'):
        module.ensure_runtime_deps(build)
    else:
        with pytest.raises(module.FixtureSafetyError, match="locked environment") as exc:
            module.ensure_runtime_deps(build)
        assert "private-child-diagnostic" not in str(exc.value)
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[:3] == [str(build.venv_python), "-I", "-c"]
    assert "UNKNOWN_FUTURE_PROVIDER_TOKEN" not in kwargs["env"]
    assert "uv" not in command and "pip" not in command and "install" not in command


@pytest.mark.parametrize("failure", ("launch", "timeout"))
def test_dependency_child_launch_failures_drop_private_exception_context(tmp_path, monkeypatch, failure):
    module = common()

    def run(*_args, **_kwargs):
        if failure == "timeout":
            raise module.subprocess.TimeoutExpired("synthetic", 1,
                output="private-child-output", stderr="private-child-error")
        raise OSError("private-launch-error")

    monkeypatch.setattr(module.subprocess, "run", run)
    build = module.BuildInfo("synthetic", tmp_path / "source", tmp_path / "python")
    with pytest.raises(module.FixtureSafetyError, match="locked environment") as exc:
        module.ensure_runtime_deps(build)
    assert "private" not in str(exc.value)
    assert exc.value.__context__ is None and exc.value.__cause__ is None


@pytest.mark.parametrize("request_error", (False, True))
def test_fixture_shutdown_timeout_never_kills_or_replays_stop(request_error):
    module = common()
    events = []

    class Process:
        def poll(self): return None
        def terminate(self):
            events.append("terminate")
            if request_error: raise OSError("synthetic acknowledgement loss")
        def wait(self, **_kwargs):
            events.append("wait")
            raise module.subprocess.TimeoutExpired("synthetic", 1)
        def kill(self): raise AssertionError("forced shutdown forbidden")

    process = Process()
    owner = module.FixtureProcessOwner(process)
    for _ in range(2):
        if request_error and not owner.stop_attempted:
            with pytest.raises(OSError): owner.request_stop()
        else:
            owner.request_stop()
        with pytest.raises(module.FixtureSafetyError, match="retain process"):
            owner.wait_stopped(0)
    assert events == ["terminate", "wait", "wait"]
    assert owner.process is process and owner.stop_attempted


def test_fixture_shutdown_refuses_foreign_process():
    module = common()
    owner = module.FixtureProcessOwner(object())
    owner.process = object()
    with pytest.raises(module.FixtureSafetyError, match="owner changed"):
        owner.request_stop()
    with pytest.raises(module.FixtureSafetyError, match="owner changed"):
        owner.wait_stopped(0)
