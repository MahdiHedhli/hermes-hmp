"""Crash-controller causal tests: no launchctl or service mutation."""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location("character_crash_fixture_test",
    _ROOT / "tools/compat/presentation_broker_crash_fixture.py")
fixture = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fixture
_SPEC.loader.exec_module(fixture)


class Socket:
    def __init__(self, incoming=b"{}\nCRASH_ACK\n"):
        self.incoming, self.sent, self.closed = incoming, [], False

    def recv(self, amount):
        part, self.incoming = self.incoming[:amount], self.incoming[amount:]
        return part

    def sendall(self, value):
        self.sent.append(value)

    def settimeout(self, value):
        pass

    def bind(self, value):
        pass

    def listen(self, value):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def model(monkeypatch, tmp_path):
    case = SimpleNamespace(root=tmp_path, nonce="a" * 32)
    connection, listener = Socket(), Socket()
    connection.listener = listener
    listener.accept = lambda: (connection, None)
    monkeypatch.setattr(fixture.socket, "socket", lambda *a: listener)
    monkeypatch.setattr(fixture.os, "chmod", lambda *a: None)
    monkeypatch.setattr(fixture.probe, "_verify_case", lambda c: None)
    calls = []
    def command(c, verb):
        calls.append(verb)
        return verb
    monkeypatch.setattr(fixture.probe, "_command", command)
    queries = iter([{"absent": True}, {"owned": True, "pid": 200}])
    monkeypatch.setattr(fixture.probe, "_query_result", lambda *a: next(queries))
    # Bootstrap reports its return code, not the query token.
    def commands(c, verb):
        value = command(c, verb)
        return SimpleNamespace(returncode=0) if verb == "bootstrap" else value
    monkeypatch.setattr(fixture.probe, "_command", commands)
    monkeypatch.setattr(fixture.probe, "_kernel_peer", lambda c: SimpleNamespace(pid=200))
    monkeypatch.setattr(fixture, "_hello", lambda *a: {"pid": 200, "child": 201})
    monkeypatch.setattr(fixture.probe, "_eof", lambda *a: True)
    monkeypatch.setattr(fixture.probe, "_save", lambda *a: None)
    monkeypatch.setattr(fixture.probe, "_cleanup",
                        lambda c, r, *a: r.update(cleanup="known_absent"))
    monitors = []
    class Monitor:
        def __init__(self, binding, pid, **kwargs):
            self.pid, self.polls, self.closed = pid, 0, False
            monitors.append(self)
        def ensure_pending(self, binding):
            pass
        def poll(self, binding, **kwargs):
            self.polls += 1
            return SimpleNamespace(observed_at_ns=time.monotonic_ns())
        def close(self, binding):
            self.closed = True
            return True
    monkeypatch.setattr(fixture.observer, "ProcessExitObserver", Monitor)
    return case, connection, monitors, calls


def test_happy_path_distinguishes_kernel_exit_from_output_eof_and_causality(model):
    case, connection, monitors, calls = model
    record = {}
    fixture._run(case, record, Path("unused"), {})
    assert record["cleanup_known"] and record["kernel_cleanup_known"]
    assert record["actual_reader_exit_within_window"]
    assert record["manager_kill_causality_proven"] is False
    assert record["reader_output_eof"] is None
    assert [m.pid for m in monitors] == [200, 201]
    assert all(m.closed for m in monitors)
    assert connection.sent == [b"ARM " + b"a" * 32 + b"\n",
                               b"CRASH " + b"a" * 32 + b"\n"]
    assert calls.count("bootstrap") == 1


def test_preexisting_reader_exit_prevents_stimulus(model, monkeypatch):
    case, connection, monitors, _ = model
    original = fixture.observer.ProcessExitObserver
    class Preexisting(original):
        def ensure_pending(self, binding):
            if self.pid == 201:
                raise fixture.observer.ObserverRefusedError("preexisting")
    monkeypatch.setattr(fixture.observer, "ProcessExitObserver", Preexisting)
    record = {}
    with pytest.raises(fixture.observer.ObserverRefusedError):
        fixture._run(case, record, Path("unused"), {})
    assert len(connection.sent) == 1 and connection.sent[0].startswith(b"ARM ")
    assert "crash_requested_ns" not in record
    assert record["kernel_cleanup_known"] and all(m.closed for m in monitors)


def test_job_peer_mismatch_prevents_arm_child_or_crash(model, monkeypatch):
    case, connection, monitors, _ = model
    monkeypatch.setattr(fixture.probe, "_kernel_peer", lambda c: SimpleNamespace(pid=999))
    record = {}
    with pytest.raises(fixture.probe.ProbeRefusedError, match="broker_job_peer"):
        fixture._run(case, record, Path("unused"), {})
    assert not connection.sent and not monitors
    assert not record["kernel_cleanup_known"] and not record["cleanup_known"]


@pytest.mark.parametrize("value", [b"", b"x" * 1025, b"wrong\n"])
def test_lost_or_wrong_crash_ack_never_retries(model, value):
    case, connection, _, calls = model
    connection.incoming = b"{}\n" + value
    record = {}
    with pytest.raises(fixture.probe.ProbeRefusedError):
        fixture._run(case, record, Path("unused"), {})
    assert sum(v.startswith(b"CRASH ") for v in connection.sent) == 1
    assert calls.count("bootstrap") == 1
    assert "actual_reader_exit_within_window" not in record


def test_missing_reader_exit_never_known_cleanup():
    assert not fixture._both_exited({"broker_kernel_exit_observed_ns": 12})
    assert not fixture._both_exited({"broker_kernel_exit_observed_ns": 12,
                                    "reader_kernel_exit_observed_ns": True})


def test_hello_rejects_boolean_pid_and_duplicate_key(monkeypatch):
    monkeypatch.setattr(fixture.os, "getpgid", lambda pid: 300)
    case = SimpleNamespace(nonce="a" * 32)
    row = {"kind": "actual_reader_broker", "nonce": case.nonce, "pid": 200,
           "pgid": 300, "child": 201, "child_pgid": 300, "input_sent": False,
           "go_sent": False, "child_retained_unreaped": True}
    assert fixture._hello(json.dumps(row).encode(), case, 200)["child"] == 201
    row["child"] = True
    with pytest.raises(fixture.probe.ProbeRefusedError):
        fixture._hello(json.dumps(row).encode(), case, 200)
    with pytest.raises(fixture.probe.ProbeRefusedError, match="duplicate"):
        fixture._hello(b'{"pid":200,"pid":201}', case, 200)


def test_main_refuses_without_explicit_flag_before_lock(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fixture"])
    monkeypatch.setattr(os, "open", lambda *a: pytest.fail("must not acquire lock"))
    with pytest.raises(fixture.probe.ProbeRefusedError):
        fixture.main()


@pytest.mark.parametrize("plane", ["control_socket", "listener", "manager", "monitor"])
def test_cleanup_plane_failure_does_not_skip_other_owned_disposal(model, monkeypatch, plane):
    case, connection, monitors, calls = model
    def fail(*args):
        raise OSError("synthetic cleanup failure")
    if plane == "control_socket":
        connection.close = fail
    elif plane == "listener":
        connection.listener.close = fail
    elif plane == "manager":
        monkeypatch.setattr(fixture.probe, "_cleanup", fail)
    else:
        original = fixture.observer.ProcessExitObserver
        class MonitorFailure(original):
            def close(self, binding):
                self.closed = True
                if self.pid == 200:
                    raise OSError("synthetic monitor failure")
                return True
        monkeypatch.setattr(fixture.observer, "ProcessExitObserver", MonitorFailure)
    record = {}
    fixture._run(case, record, Path("unused"), {})
    assert not record["cleanup_known"]
    assert len(monitors) == 2 and all(m.closed for m in monitors)
    assert calls.count("bootstrap") == 1
    assert record["cleanup_errors"]


def test_partial_second_observer_retained_closed_once_without_crash(model, monkeypatch):
    case, connection, monitors, calls = model
    original = fixture.observer.ProcessExitObserver
    class Partial(original):
        def __init__(self, binding, pid, **kwargs):
            super().__init__(binding, pid, **kwargs)
            self.close_count = 0
            if pid == 201:
                raise fixture.observer.ObserverAcquisitionError(self, "registration_unknown")
        def poll(self, binding, **kwargs):
            if self.pid == 201:
                raise fixture.observer.ObserverRefusedError("registration_unknown")
            return super().poll(binding, **kwargs)
        def close(self, binding):
            self.close_count += 1
            return super().close(binding)
    monkeypatch.setattr(fixture.observer, "ProcessExitObserver", Partial)
    record = {}
    with pytest.raises(fixture.observer.ObserverAcquisitionError):
        fixture._run(case, record, Path("unused"), {})
    assert len(monitors) == 2 and all(m.close_count == 1 for m in monitors)
    assert not record["cleanup_known"] and not record["kernel_cleanup_known"]
    assert not any(v.startswith(b"CRASH ") for v in connection.sent)
    assert calls.count("bootstrap") == 1


def test_drip_feed_cannot_renew_absolute_receive_deadline(monkeypatch):
    clock = [0]
    class Drip(Socket):
        def recv(self, amount):
            clock[0] += 6
            return b"a"
    monkeypatch.setattr(fixture.time, "monotonic_ns", lambda: clock[0])
    with pytest.raises(fixture.probe.ProbeRefusedError, match="protocol_deadline"):
        fixture._receive_line(Drip(), 10)
    assert clock[0] == 12


def test_oracle_diagnostic_failure_cannot_drop_retained_owner(monkeypatch):
    oracle = fixture._load("crash_oracle_test", "presentation_broker_crash_oracle.py")
    owner = object()
    oracle._RETAINED.append(owner)
    def refusal(*args):
        raise RuntimeError("synthetic startup failure")
    class BrokenDiagnostic:
        def write(self, value):
            raise BrokenPipeError
    class SupervisionReachedError(Exception):
        pass
    def supervised_wait(seconds):
        assert [owner] == oracle._RETAINED
        raise SupervisionReachedError
    monkeypatch.setattr(oracle, "run", refusal)
    monkeypatch.setattr(oracle.sys, "stderr", BrokenDiagnostic())
    monkeypatch.setattr(oracle.time, "sleep", supervised_wait)
    with pytest.raises(SupervisionReachedError):
        oracle.main()


def test_oracle_drip_feed_cannot_renew_command_deadline(monkeypatch):
    oracle = fixture._load("crash_oracle_deadline_test", "presentation_broker_crash_oracle.py")
    clock = [0]
    class Drip(Socket):
        def recv(self, amount):
            clock[0] += 6
            return b"a"
    monkeypatch.setattr(oracle.time, "monotonic_ns", lambda: clock[0])
    with pytest.raises(RuntimeError, match="oracle_refused"):
        oracle._receive_exact(Drip(), b"aaaa", 10)
    assert clock[0] == 12
