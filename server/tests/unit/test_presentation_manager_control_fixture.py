"""Instrumented control causals only: no launchctl, process or service action."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location("manager_control_test",
    Path(__file__).resolve().parents[3] / "tools/compat/presentation_manager_control_fixture.py")
control = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = control
_SPEC.loader.exec_module(control)


@pytest.fixture
def model(monkeypatch, tmp_path):
    clock = [1_000_000_000]
    monkeypatch.setattr(control.time, "monotonic_ns", lambda: clock[0])
    monkeypatch.setattr(control.time, "sleep", lambda seconds: clock.__setitem__(0,
                       clock[0] + 500_000_000))
    monkeypatch.setattr(control.os, "getpgrp", lambda: 500)
    monkeypatch.setattr(control.os, "chmod", lambda *args: None)
    class Socket:
        def __init__(self):
            self.sent, self.closed = [], False
        def bind(self, *args): pass
        def listen(self, *args): pass
        def settimeout(self, *args): pass
        def recv(self, amount): return b"k"
        def sendall(self, value): self.sent.append(value)
        def close(self): self.closed = True
    broker, reader, listener = Socket(), Socket(), Socket()
    queue = iter([broker, reader])
    listener.accept = lambda: (next(queue), None)
    monkeypatch.setattr(control.socket, "socket", lambda *args: listener)
    monkeypatch.setattr(control.actual, "_receive_line", lambda *args, **kwargs: b"unused")
    case = SimpleNamespace(root=tmp_path, mode="new")
    def hello(raw, connection, case):
        return ({"kind": "broker", "pid": 200, "pgid": 400, "child": 201}
                if connection is broker else
                {"kind": "reader", "pid": 201, "pgid": 400 if case.mode == "shared" else 401,
                 "deadline_ns": 13_000_000_000})
    monkeypatch.setattr(control, "_hello", hello)
    monkeypatch.setattr(control.probe, "_verify_case", lambda *args: None)
    monkeypatch.setattr(control.probe, "_save", lambda *args: None)
    monkeypatch.setattr(control.probe, "_command", lambda c, verb: SimpleNamespace(returncode=0))
    results = iter([{"absent": True}, {"owned": True, "pid": 200}])
    monkeypatch.setattr(control.probe, "_query_result", lambda *args: next(results))
    monkeypatch.setattr(control.probe, "_cleanup",
                        lambda c, r, *args: r.update(cleanup="known_absent"))
    owners = []
    class Owner:
        def __init__(self, *args, **kwargs):
            self.closed = False
            owners.append(self)
        def ensure_pending(self, *args): pass
        def close(self, *args):
            self.closed = True
            return True
    monkeypatch.setattr(control.observer, "ProcessExitObserver", Owner)
    def observe(held, binding, record, *, cleanup):
        record.setdefault("broker_kernel_exit_observed_ns", clock[0])
        if cleanup or case.mode == "shared":
            record.setdefault("reader_kernel_exit_observed_ns", clock[0])
    monkeypatch.setattr(control.actual, "_observe", observe)
    return case, broker, reader, owners, clock


@pytest.mark.parametrize("mode", ["new", "shared"])
def test_control_outcome_frozen_before_cleanup_and_both_kernel_exits_required(model, mode):
    case, broker, reader, owners, _ = model
    case.mode = mode
    record = {}
    control._run(case, record, Path("unused"), {})
    assert record["expected_control_observed"] is True
    assert record["reader_exit_observed_during_window"] is (mode == "shared")
    assert record["reader_stop_attempted_ns"] >= record["window_end_ns"]
    assert record["kernel_cleanup_known"] and record["cleanup_known"]
    assert all(owner.closed for owner in owners)
    assert broker.sent == [b"k"] and reader.sent == [b"x"]


def test_preexisting_exit_prevents_crash_and_still_disposes_owned_monitors(model, monkeypatch):
    case, broker, _, owners, _ = model
    original = control.observer.ProcessExitObserver
    class Preexisting(original):
        def ensure_pending(self, *args):
            raise control.observer.ObserverRefusedError("preexisting")
    monkeypatch.setattr(control.observer, "ProcessExitObserver", Preexisting)
    with pytest.raises(control.observer.ObserverRefusedError):
        control._run(case, {}, Path("unused"), {})
    assert not broker.sent and len(owners) == 2 and all(o.closed for o in owners)


def test_manager_cleanup_error_cannot_skip_monitor_disposal(model, monkeypatch):
    case, _, _, owners, _ = model
    def fail(*args): raise OSError("synthetic")
    monkeypatch.setattr(control.probe, "_cleanup", fail)
    record = {}
    control._run(case, record, Path("unused"), {})
    assert not record["cleanup_known"] and all(o.closed for o in owners)
    assert record["cleanup_errors"] == ["manager_cleanup_unknown"]


@pytest.mark.parametrize("reason", ["wrong_job", "wrong_child", "wrong_group", "short_lifetime"])
def test_ineligible_control_refuses_before_stimulus(model, reason):
    case, _, _, _, clock = model
    broker = {"pid": 200, "pgid": 400, "child": 201}
    reader = {"pid": 201, "pgid": 401, "deadline_ns": clock[0] + 12_000_000_000}
    query = {"owned": True, "pid": 200}
    if reason == "wrong_job":
        query["pid"] = 999
    if reason == "wrong_child":
        broker["child"] = 202
    if reason == "wrong_group":
        reader["pgid"] = 400
    if reason == "short_lifetime":
        reader["deadline_ns"] = clock[0] + 2_000_000_000
    with pytest.raises(control.probe.ProbeRefusedError):
        control._eligible(case, broker, reader, query)


def test_timeout_cannot_be_used_as_manager_exit_evidence(model):
    case, _, _, _, _ = model
    record = {"window_end_ns": 12_100_000_000, "reader_deadline_ns": 13_000_000_000,
              "broker_kernel_exit_observed_ns": 2, "reader_kernel_exit_observed_ns": 3}
    with pytest.raises(control.probe.ProbeRefusedError, match="timeout_confounded"):
        control._interpret(case, record)


def test_hello_duplicate_or_kernel_mismatch_refuses(monkeypatch):
    case = SimpleNamespace(nonce="a" * 32)
    monkeypatch.setattr(control.probe, "_kernel_peer", lambda c: SimpleNamespace(pid=999))
    monkeypatch.setattr(control.os, "getpgid", lambda pid: 400)
    raw = json.dumps({"kind": "broker", "nonce": case.nonce, "pid": 200,
                      "pgid": 400, "child": 201}).encode()
    with pytest.raises(control.probe.ProbeRefusedError, match="kernel_peer"):
        control._hello(raw, object(), case)
    with pytest.raises(control.probe.ProbeRefusedError, match="duplicate_key"):
        control._hello(b'{"pid":200,"pid":201}', object(), case)
