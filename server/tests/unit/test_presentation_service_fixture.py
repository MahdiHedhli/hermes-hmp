"""Controller preflight/cleanup causals only; no launchctl/job/process effect."""
import importlib.util
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location("service_fixture_unit",
    Path(__file__).resolve().parents[3] / "tools/compat/presentation_service_fixture.py")
fixture = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fixture
_SPEC.loader.exec_module(fixture)


@pytest.fixture
def early_model(monkeypatch):
    calls = []
    class Listener:
        def __init__(self):
            self.fail_close = False
            self.closed = False
        def bind(self, address):
            calls.append("bind")
        def listen(self, count):
            pass
        def settimeout(self, timeout):
            pass
        def accept(self):
            pytest.fail("must not accept after failed bootstrap")
        def close(self):
            self.closed = True
            if self.fail_close:
                raise OSError("synthetic close failure")
    listener = Listener()
    monkeypatch.setattr(fixture.protocol, "own_socket", lambda: listener)
    def close_socket(sock):
        sock.close()
        return True  # model of separately tested native disposal plane
    monkeypatch.setattr(fixture.protocol, "close_socket", close_socket)
    monkeypatch.setattr(fixture.probe, "_verify_case", lambda *args: None)
    monkeypatch.setattr(fixture.probe, "_save", lambda *args: None)
    monkeypatch.setattr(fixture.os, "chmod", lambda *args: None)
    def command(case, verb):
        calls.append(verb)
        return SimpleNamespace(returncode=1 if verb == "bootstrap" else 0)
    monkeypatch.setattr(fixture.probe, "_command", command)
    monkeypatch.setattr(fixture.probe, "_query_result", lambda *args: {"absent": True})
    def cleanup(case, record, *args):
        calls.append("cleanup")
        record["cleanup"] = "known_absent"
    monkeypatch.setattr(fixture.probe, "_cleanup", cleanup)
    case = SimpleNamespace(root=Path("/synthetic/service-case"), nonce="a" * 32)
    return case, listener, calls


@pytest.mark.asyncio
async def test_nonfresh_label_never_submits_or_binds(early_model, monkeypatch):
    case, listener, calls = early_model
    monkeypatch.setattr(fixture.probe, "_query_result", lambda *args: {"absent": False})
    record = {"submission_attempted": False}
    with pytest.raises(fixture.probe.ProbeRefusedError, match="absence_unknown"):
        await fixture._run(case, "b" * 64, Path("unused"), record, Path("unused"), {})
    assert calls == ["print"] and listener.closed
    assert record["submission_attempted"] is False and record["cleanup_known"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("close_failure", [False, True])
async def test_bootstrap_ambiguity_never_retries_and_still_attempts_manager_cleanup(
    early_model, close_failure
):
    case, listener, calls = early_model
    listener.fail_close = close_failure
    record = {}
    with pytest.raises(fixture.probe.ProbeRefusedError, match="bootstrap_ambiguous"):
        await fixture._run(case, "b" * 64, Path("unused"), record, Path("unused"), {})
    assert calls.count("bootstrap") == 1 and calls[-1] == "cleanup"
    assert record["cleanup"] == "known_absent"
    assert record["cleanup_known"] is False  # no broker kernel observation
    assert bool(record["cleanup_errors"]) is close_failure


@pytest.mark.asyncio
async def test_lost_control_reply_does_not_resend_or_reset_sequence(monkeypatch):
    sent = []
    async def send(sock, value, end_ns):
        sent.append(value)
    async def lost(*args):
        raise TimeoutError("synthetic lost response")
    monkeypatch.setattr(fixture.protocol, "send_control", send)
    monkeypatch.setattr(fixture.protocol, "receive_control", lost)
    control = fixture.Control(object(), time.monotonic_ns() + 1_000_000_000)
    with pytest.raises(TimeoutError):
        await control.command("inspect")
    assert sent == [{"mode": "inspect", "sequence": 1}] and control.sequence == 1


def test_controller_namespace_does_not_execute_package_initializer(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    (tmp_path / "__init__.py").write_text("raise RuntimeError('MUST_NOT_EXECUTE')\n")
    suffixes = ("presentation_broker_service", "presentation_broker_codec",
        "presentation_broker_lifecycle", "presentation_broker_endpoint",
        "presentation_parent_policy",
        "presentation_posix", "presentation_budget", "presentation_input_v3")
    for suffix in suffixes:
        (tmp_path / (suffix + ".py")).write_text("marker = 1\n")
    try:
        modules = fixture._client_modules(tmp_path)
        assert len(modules) == 8 and all(m.marker == 1 for m in modules.values())
        assert not list(tmp_path.rglob("__pycache__"))
        assert not list(tmp_path.rglob("*.pyc"))
        with pytest.raises(fixture.probe.ProbeRefusedError, match="namespace_reuse"):
            fixture._client_modules(tmp_path)
    finally:
        for key in tuple(sys.modules):
            if key == "_service_fixture_client" or key.startswith("_service_fixture_client."):
                del sys.modules[key]


def test_main_requires_explicit_flag_before_lock_or_socket(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fixture"])
    monkeypatch.setattr(fixture.os, "open", lambda *args: pytest.fail("no lock before flag"))
    with pytest.raises(fixture.probe.ProbeRefusedError):
        fixture.main()


def test_bytecode_enabled_refuses_before_lock_or_import(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-local-fixture"])
    monkeypatch.setattr(fixture.sys, "platform", "darwin")
    monkeypatch.setattr(fixture.os, "geteuid", lambda: 501)
    monkeypatch.setattr(fixture.os, "open", lambda *args: pytest.fail("no lock"))
    with pytest.raises(fixture.probe.ProbeRefusedError, match="bytecode_disabled"):
        fixture.main()
    with pytest.raises(fixture.probe.ProbeRefusedError, match="bytecode_disabled"):
        fixture._client_modules(tmp_path)


def test_missing_controller_dependency_refuses_before_lock(monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-local-fixture"])
    monkeypatch.setattr(fixture.sys, "platform", "darwin")
    monkeypatch.setattr(fixture.os, "geteuid", lambda: 501)
    monkeypatch.setattr(fixture.os, "open", lambda *args: pytest.fail("no lock"))
    def missing(name):
        assert name == "yaml"
        raise ModuleNotFoundError("synthetic missing yaml")
    monkeypatch.setattr(fixture.importlib, "import_module", missing)
    with pytest.raises(fixture.probe.ProbeRefusedError, match="pyyaml_dependency_missing"):
        fixture.main()
