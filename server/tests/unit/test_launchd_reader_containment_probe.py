"""Controller safety tests; no launchctl call or real service mutation."""

import importlib.util
import socket
import subprocess
import sys
import threading
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "tools/compat/launchd_reader_containment_probe.py"
_SPEC = importlib.util.spec_from_file_location("containment_probe_test_module", _SCRIPT)
probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = probe
_SPEC.loader.exec_module(probe)


@pytest.fixture
def case(tmp_path):
    return probe._make_case(tmp_path.resolve() / "fixture", "shared")


def result(code=0, out=b"", err=b""):
    return subprocess.CompletedProcess([], code, out, err)


def test_exact_owned_job_parser_never_retains_environment(case):
    output = "\tprogram = /usr/bin/env\n\targuments = {\n"
    output += "".join("\t\t" + arg + "\n" for arg in case.argv)
    output += "\t}\n\tpid = 123\n\tenvironment = {\n\t\tSECRET = hidden\n\t}\n"
    parsed = probe._query_result(case, result(out=output.encode()))
    assert parsed["owned"] and parsed["pid"] == 123
    assert "hidden" not in str(parsed) and "SECRET" not in str(parsed)
    altered = output.replace(case.nonce, "wrong")
    assert not probe._query_result(case, result(out=altered.encode()))["owned"]


def test_absence_requires_exact_label_and_error(case):
    assert probe._query_result(
        case, result(113, err=f'Could not find service "{case.label}"'.encode())
    )["absent"]
    assert not probe._query_result(case, result(113, err=b"Could not find service other"))["absent"]
    assert not probe._query_result(case, result(1, err=b"permission denied"))["absent"]


def test_unknown_or_oversize_parser_refuses(case):
    assert not probe._query_result(case, result(out=b"unknown format"))["owned"]
    with pytest.raises(probe.ProbeRefusedError, match="too_large"):
        probe._query_result(case, result(out=b"x" * 131073))


@pytest.mark.parametrize("verb", ["kill", "remove", "enable", "kickstart"])
def test_nonallowlisted_commands_never_run(case, monkeypatch, verb):
    run = Mock()
    monkeypatch.setattr(probe.subprocess, "run", run)
    with pytest.raises(probe.ProbeRefusedError):
        probe._command(case, verb)
    run.assert_not_called()


def test_wrong_domain_never_runs(case, monkeypatch):
    run = Mock()
    monkeypatch.setattr(probe.subprocess, "run", run)
    with pytest.raises(probe.ProbeRefusedError):
        probe._command(replace(case, domain="system"), "bootout")
    run.assert_not_called()


def test_bootout_only_exact_target_minimal_environment(case, monkeypatch):
    run = Mock(return_value=result())
    monkeypatch.setattr(probe.subprocess, "run", run)
    probe._command(case, "bootout")
    args, kwargs = run.call_args
    assert args[0] == ["/bin/launchctl", "bootout", case.target]
    assert kwargs["env"] == {"LANG": "C", "LC_ALL": "C"}
    assert kwargs["timeout"] == 5 and kwargs["stdin"] == subprocess.DEVNULL


def test_changed_input_refuses(case):
    (case.root / "reader.py").write_text("changed")
    with pytest.raises(probe.ProbeRefusedError, match="input_changed"):
        probe._verify_case(case)


def test_cleanup_query_exception_retains_unknown(case, tmp_path, monkeypatch):
    record = {"submission_attempted": True, "cleanup": "pending"}
    state = {"cases": [record]}
    monkeypatch.setattr(probe, "_command", Mock(side_effect=TimeoutError))
    with pytest.raises(TimeoutError):
        probe._cleanup(case, record, tmp_path / "receipt.json", state)
    assert record["cleanup"] == "unknown"


def test_cleanup_foreign_job_never_boots_out(case, tmp_path, monkeypatch):
    command = Mock(return_value=result(out=b"unrecognized or foreign"))
    monkeypatch.setattr(probe, "_command", command)
    record = {"submission_attempted": True}
    probe._cleanup(case, record, tmp_path / "receipt.json", {"cases": [record]})
    assert record["cleanup"] == "unknown_ownership"
    assert [c.args[1] for c in command.call_args_list] == ["print"]


def test_cleanup_bootout_timeout_no_retry(case, tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "_query_result", Mock(return_value={"owned": True, "absent": False}))
    command = Mock(side_effect=[result(), TimeoutError()])
    monkeypatch.setattr(probe, "_command", command)
    record = {"submission_attempted": True}
    with pytest.raises(TimeoutError):
        probe._cleanup(case, record, tmp_path / "receipt.json", {"cases": [record]})
    assert record["cleanup"] == "unknown" and record["bootout_attempted"]
    assert [c.args[1] for c in command.call_args_list] == ["print", "bootout"]


def test_cleanup_known_absent_never_mutates(case, tmp_path, monkeypatch):
    command = Mock(return_value=result(113, err=f'Could not find service "{case.label}"'.encode()))
    monkeypatch.setattr(probe, "_command", command)
    record = {"submission_attempted": True, "cleanup": "pending"}
    probe._cleanup(case, record, tmp_path / "receipt.json", {"cases": [record]})
    assert record["cleanup"] == "known_absent"
    assert [c.args[1] for c in command.call_args_list] == ["print"]


def test_cleanup_changed_fixture_retains_unknown_without_command(case, tmp_path, monkeypatch):
    (case.root / "broker.py").write_text("changed")
    command = Mock()
    monkeypatch.setattr(probe, "_command", command)
    record = {"submission_attempted": True, "cleanup": "pending"}
    with pytest.raises(probe.ProbeRefusedError):
        probe._cleanup(case, record, tmp_path / "receipt.json", {"cases": [record]})
    assert record["cleanup"] == "unknown"
    command.assert_not_called()


def test_explicit_opt_in_guard_performs_no_file_mutation(monkeypatch):
    monkeypatch.setattr(probe.sys, "argv", [str(_SCRIPT)])
    opened = Mock()
    monkeypatch.setattr(probe.os, "open", opened)
    with pytest.raises(probe.ProbeRefusedError, match="explicit_nonroot"):
        probe.main()
    opened.assert_not_called()


def test_reader_stop_observes_actual_peer_eof():
    local, remote = socket.socketpair()
    received = []

    def reader():
        received.append(remote.recv(1))
        remote.close()

    worker = threading.Thread(target=reader)
    worker.start()
    record = {}
    try:
        probe._stop_reader(local, record)
        assert record["reader_communication_cleanup"] == "eof"
        assert record["reader_cleanup_observed_ns"] >= record["explicit_reader_stop_ns"]
    finally:
        local.close()
        worker.join(timeout=3)
    assert not worker.is_alive() and received == [b"x"]


def test_reader_stop_timeout_is_not_cleanup_proof(monkeypatch):
    local, remote = socket.socketpair()
    monkeypatch.setattr(probe, "_eof", Mock(return_value=False))
    record = {}
    try:
        probe._stop_reader(local, record)
        assert remote.recv(1) == b"x"
        assert record["reader_communication_cleanup"] == "unknown"
    finally:
        local.close()
        remote.close()


def test_main_unknown_reader_cleanup_stops_before_second_case(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(probe.sys, "argv", [str(_SCRIPT), "--run-local-fixture"])
    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe, "_LOCK", tmp_path / "lock")
    monkeypatch.setattr(probe, "_POINTER", tmp_path / "pointer.json")
    root = tmp_path / "run"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(probe.tempfile, "mkdtemp", Mock(return_value=str(root)))

    def uncertain(case, record, receipt, state):
        record.update(
            submission_attempted=True,
            expected_observation=True,
            cleanup="known_absent",
            reader_communication_cleanup="unknown",
        )

    run = Mock(side_effect=uncertain)
    monkeypatch.setattr(probe, "_case", run)
    assert probe.main() == 1
    assert run.call_count == 1
    assert (tmp_path / "lock").exists()
    assert '"status": "terminal_refused"' in capsys.readouterr().out
