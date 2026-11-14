"""Fixture observer causals; native tests own only new no-content children."""

import importlib.util
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "tools/compat/darwin_process_exit_observer.py"
_SPEC = importlib.util.spec_from_file_location("darwin_exit_observer_test_module", _SCRIPT)
observer = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = observer
_SPEC.loader.exec_module(observer)


@dataclass
class Event:
    ident: int
    filter: int = -5
    flags: int = 0
    fflags: int = 0
    data: int = 0
    udata: int = 0


@pytest.fixture
def model(monkeypatch):
    queues = []

    class Queue:
        def __init__(self):
            self.fd = 60000 + len(queues)
            self._closed = False
            self.calls = []
            self.responses = []
            self.change = None
            self.close_count = 0
            queues.append(self)

        @property
        def closed(self):
            return self._closed

        def fileno(self):
            return self.fd

        def control(self, changes, maximum, timeout):
            self.calls.append((changes, maximum, timeout))
            if changes:
                self.change = changes[0]
                e = self.change
                return [Event(e.ident, e.filter, e.flags | 0x4000, e.fflags, 0, e.udata)]
            return self.responses.pop(0) if self.responses else []

        def close(self):
            self.close_count += 1
            self._closed = True

    def identity(fd):
        assert type(fd) is int
        q = next(q for q in queues if q.fd == fd)
        if q.closed:
            raise OSError(9, "synthetic EBADF")
        return fd, 10, fd, 0o10000

    real_fstat = os.fstat

    def fstat(fd):
        if fd < 60000:
            return real_fstat(fd)
        identity(fd)
        return os.stat_result((0o10000, fd, 10, 1, 0, 0, 0, 0, 0, 0))

    monkeypatch.setattr(observer.sys, "platform", "darwin")
    for name, value in {"_QTYPE": Queue, "_ETYPE": Event, "_QMAKE": Queue,
                        "_QFD": Queue.fileno, "_QCONTROL": Queue.control,
                        "_QCLOSE": Queue.close, "_QCLOSED": Queue.closed}.items():
        monkeypatch.setattr(observer, name, value)
    monkeypatch.setattr(observer, "_api", lambda: None)
    monkeypatch.setattr(observer, "_identity", identity)
    monkeypatch.setattr(observer.os, "fstat", fstat)
    native_inheritable = os.get_inheritable
    monkeypatch.setattr(observer.os, "get_inheritable",
                        lambda fd: False if fd >= 60000 else native_inheritable(fd))

    def make(pid=200000):
        binding = object()
        now = time.monotonic_ns()
        owner = observer.ProcessExitObserver(binding, pid, observe_end_ns=now + 1_000_000_000,
                                             cleanup_end_ns=now + 3_000_000_000)
        return owner, binding, queues[-1]

    return make, queues, Queue


def exit_row(queue, **changes):
    e = queue.change
    row = Event(e.ident, e.filter, 0x8075, 0x80000000, 0, e.udata)
    for name, value in changes.items():
        setattr(row, name, value)
    return row


def test_receipt_is_not_exit_and_event_is_not_reap(model):
    make, _, _ = model
    owner, binding, queue = make()
    assert owner._registered and owner._eligible and owner._fact is None
    assert owner.poll(binding) is None
    owner.ensure_pending(binding)
    queue.responses.append([exit_row(queue)])
    fact = owner.poll(binding)
    assert fact.pid == 200000 and fact.observed_at_ns > 0
    assert owner.fact(binding) is fact
    assert owner.poll(binding) is fact
    for name in ("exit_code", "reaped", "descendants_absent", "release", "signal"):
        assert not hasattr(fact, name)
    assert owner.close(binding) is True and owner.close(binding) is True
    assert queue.close_count == 1 and owner.fact(binding) is fact


@pytest.mark.parametrize("pid", [True, 1, 0, -1, "200000", 1.0, 2**31])
def test_bad_pid_before_queue_creation(model, pid):
    _, queues, _ = model
    now = time.monotonic_ns()
    with pytest.raises(observer.ObserverAcquisitionError):
        observer.ProcessExitObserver(object(), pid, observe_end_ns=now + 1_000_000,
                                     cleanup_end_ns=now + 2_000_000)
    assert not queues


@pytest.mark.parametrize("field,value", [("observe_end_ns", True), ("cleanup_end_ns", False),
                                         ("observe_end_ns", 0), ("cleanup_end_ns", 2**63)])
def test_bad_deadline_before_queue_creation(model, field, value):
    _, queues, _ = model
    now = time.monotonic_ns()
    values = {"observe_end_ns": now + 1_000_000_000, "cleanup_end_ns": now + 3_000_000_000}
    values[field] = value
    with pytest.raises(observer.ObserverAcquisitionError):
        observer.ProcessExitObserver(object(), 200000, **values)
    assert not queues


@pytest.mark.parametrize("change", ["none", "overflow", "errno", "pid", "cookie", "filter"])
def test_bad_receipt_never_arms(model, monkeypatch, change):
    _, queues, queue_type = model
    original = queue_type.control

    def control(q, changes, maximum, timeout):
        rows = original(q, changes, maximum, timeout)
        if changes:
            if change == "none":
                return []
            if change == "overflow":
                return rows * 2
            if change == "errno":
                rows[0].data = 3
            elif change == "pid":
                rows[0].ident += 1
            elif change == "cookie":
                rows[0].udata += 1
            else:
                rows[0].filter = -1
        return rows

    monkeypatch.setattr(observer, "_QCONTROL", control)
    now = time.monotonic_ns()
    with pytest.raises(observer.ObserverAcquisitionError) as caught:
        observer.ProcessExitObserver(object(), 200000, observe_end_ns=now + 1_000_000_000,
                                     cleanup_end_ns=now + 3_000_000_000)
    assert caught.value.failed_owner._eligible is False
    assert queues[0].calls[0][1:] == (1, 0)


def test_preexisting_exit_refuses_experiment_but_keeps_kernel_fact(model, monkeypatch):
    _, _, queue_type = model
    original = queue_type.control

    def control(q, changes, maximum, timeout):
        rows = original(q, changes, maximum, timeout)
        return rows if changes else [exit_row(q)]

    monkeypatch.setattr(observer, "_QCONTROL", control)
    binding = object()
    now = time.monotonic_ns()
    with pytest.raises(observer.ObserverAcquisitionError, match="preexisting") as caught:
        observer.ProcessExitObserver(binding, 200000, observe_end_ns=now + 1_000_000_000,
                                     cleanup_end_ns=now + 3_000_000_000)
    owner = caught.value.failed_owner
    assert owner.fact(binding).pid == 200000
    assert owner._eligible is False and owner._registered
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    assert owner.close(binding) is True


@pytest.mark.parametrize("change", ["pid", "filter", "cookie", "error", "flags", "fflags", "bool"])
def test_unexpected_event_sticky_integrity_refusal(model, change):
    make, _, _ = model
    owner, binding, queue = make()
    values = {"pid": {"ident": 200001}, "filter": {"filter": -1},
              "cookie": {"udata": queue.change.udata + 1}, "error": {"flags": 0x4000},
              "flags": {"flags": 0x8075 | 0x200}, "fflags": {"fflags": 0x40000000},
              "bool": {"ident": True}}[change]
    queue.responses.append([exit_row(queue, **values)])
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    calls = len(queue.calls)
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding, cleanup=True)
    assert len(queue.calls) == calls
    assert owner.close(binding) is True


def test_work_expiry_cleanup_only_does_not_restore_or_renew(model, monkeypatch):
    make, _, _ = model
    owner, binding, queue = make()
    old_observe, old_cleanup = owner._observe_end, owner._cleanup_end
    monkeypatch.setattr(observer.time, "monotonic_ns", lambda: old_observe)
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    queue.responses.append([exit_row(queue)])
    fact = owner.poll(binding, cleanup=True)
    assert fact.observed_at_ns == old_observe and owner._eligible is False
    assert owner._observe_end is old_observe and owner._cleanup_end is old_cleanup
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    assert owner.close(binding) is True


def test_wrong_binding_does_not_operate_or_poison_valid_owner(model):
    make, _, _ = model
    owner, binding, queue = make()
    calls = len(queue.calls)
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(object())
    assert len(queue.calls) == calls
    assert owner.poll(binding) is None
    assert owner.close(binding) is True


def test_context_and_fd_drift_never_close_replacement(model, monkeypatch):
    make, _, _ = model
    owner, binding, queue = make()
    monkeypatch.setattr(observer, "_identity", lambda fd: (fd, 11, 99, 0o10000))
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    assert owner.close(binding) is False and queue.close_count == 0
    assert owner.close(binding) is False and queue.close_count == 0


def test_noop_close_not_success_or_retry(model, monkeypatch):
    make, _, _ = model
    monkeypatch.setattr(observer, "_QCLOSE", lambda q: None)
    owner, binding, queue = make()
    assert owner.close(binding) is False
    assert owner.close(binding) is False and queue.closed is False


def test_closed_flag_laundering_not_success(model):
    make, _, _ = model
    owner, binding, queue = make()
    owner._closed_known = True
    assert owner.close(binding) is False
    assert queue.close_count == 0 and queue.closed is False


@pytest.mark.skipif(sys.platform != "darwin", reason="Darwin kernel-only observation")
def test_native_exit_receipt_and_unrelated_reader_isolation():
    binding = object()
    children = []
    owners = []
    try:
        for _ in range(2):
            child = subprocess.Popen(
                [sys.executable, "-I", "-B", "-S", "-c", "import sys;sys.stdin.buffer.read(1)"],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                bufsize=0, close_fds=True, env={"LANG": "C", "LC_ALL": "C"},
            )
            children.append(child)
            now = time.monotonic_ns()
            owner = observer.ProcessExitObserver(binding, child.pid,
                observe_end_ns=now + 2_000_000_000, cleanup_end_ns=now + 4_000_000_000)
            owners.append(owner)
            owner.ensure_pending(binding)
        children[0].stdin.close()  # natural EOF of this own synthetic child only
        end = time.monotonic() + 2
        fact = None
        while fact is None:
            fact = owners[0].poll(binding)
            assert time.monotonic() < end
            time.sleep(0.001)
        assert fact.pid == children[0].pid
        assert children[0].wait(timeout=2) == 0  # independent parent reap, NOT observer proof
        assert owners[1].poll(binding) is None and children[1].poll() is None
        assert owners[0].fact(binding) is fact
    finally:
        for child in children:
            if not child.stdin.closed:
                child.stdin.close()
            child.wait(timeout=3)  # own controlled EOF; no controller signal
        for owner in owners:
            assert owner.close(binding) is True


@pytest.mark.parametrize("boundary", ["control", "fileno", "closed", "identity", "clock"])
def test_swallowed_reentry_never_mints_or_resumes_io(model, monkeypatch, boundary):
    make, _, queue_type = model
    state = {"owner": None, "binding": None}
    original_control = observer._QCONTROL
    original_fd = observer._QFD
    original_closed = observer._QCLOSED
    original_identity = observer._identity
    original_clock = time.monotonic_ns

    def reenter():
        if state["owner"] is not None:
            with pytest.raises(observer.ObserverRefusedError):
                state["owner"].poll(state["binding"])

    def control(q, changes, maximum, timeout):
        rows = original_control(q, changes, maximum, timeout)
        if boundary == "control":
            reenter()
        return rows

    def fileno(q):
        value = original_fd(q)
        if boundary == "fileno":
            reenter()
        return value

    def closed(q):
        value = original_closed.__get__(q, queue_type)
        if boundary == "closed":
            reenter()
        return value

    def identity(fd):
        value = original_identity(fd)
        if boundary == "identity":
            reenter()
        return value

    def clock():
        value = original_clock()
        if boundary == "clock":
            reenter()
        return value

    monkeypatch.setattr(observer, "_QCONTROL", control)
    monkeypatch.setattr(observer, "_QFD", fileno)
    monkeypatch.setattr(observer, "_QCLOSED", property(closed))
    monkeypatch.setattr(observer, "_identity", identity)
    monkeypatch.setattr(observer.time, "monotonic_ns", clock)
    owner, binding, queue = make()
    queue.responses.append([exit_row(queue)])
    state.update(owner=owner, binding=binding)
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    assert owner._fact is None and owner._integrity_lost and owner._eligible is False
    state["owner"] = None
    calls = len(queue.calls)
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding, cleanup=True)
    assert owner.close(binding) is False
    assert len(queue.calls) == calls and queue.close_count == 0


def test_observed_identity_drift_stays_poisoned_after_restoration(model, monkeypatch):
    make, _, _ = model
    owner, binding, queue = make()
    original = observer._identity
    monkeypatch.setattr(observer, "_identity", lambda fd: (fd, 55, 66, 0o10000))
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding)
    monkeypatch.setattr(observer, "_identity", original)
    calls = len(queue.calls)
    assert owner._integrity_lost
    assert owner.close(binding) is False
    with pytest.raises(observer.ObserverRefusedError):
        owner.poll(binding, cleanup=True)
    assert queue.close_count == 0 and len(queue.calls) == calls


@pytest.mark.parametrize("boundary", ["postclose_fstat", "postclose_closed", "repeat_closed"])
def test_swallowed_close_reentry_never_certifies(model, monkeypatch, boundary):
    make, _, queue_type = model
    state = {"owner": None, "binding": None, "armed": False}
    original_closed = observer._QCLOSED
    original_fstat = observer.os.fstat

    def reenter():
        if state["armed"]:
            with pytest.raises(observer.ObserverRefusedError):
                state["owner"].poll(state["binding"])

    def closed(q):
        value = original_closed.__get__(q, queue_type)
        if value and boundary != "postclose_fstat":
            reenter()
        return value

    def fstat(fd):
        try:
            return original_fstat(fd)
        except OSError:
            if boundary == "postclose_fstat":
                reenter()
            raise

    monkeypatch.setattr(observer, "_QCLOSED", property(closed))
    monkeypatch.setattr(observer.os, "fstat", fstat)
    owner, binding, queue = make()
    state.update(owner=owner, binding=binding)
    if boundary == "repeat_closed":
        assert owner.close(binding) is True
    state["armed"] = True
    assert owner.close(binding) is False
    assert owner._integrity_lost
    if boundary != "repeat_closed":
        assert owner._close_fact is None
    assert queue.close_count == 1
    state["armed"] = False
    assert owner.close(binding) is False
    assert queue.close_count == 1
