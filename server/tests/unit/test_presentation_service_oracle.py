"""Fixture startup/control refusals only; no service or process is launched."""
import asyncio
import importlib.util
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location("service_oracle_unit",
    Path(__file__).resolve().parents[3] / "tools/compat/presentation_service_oracle.py")
oracle = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = oracle
_SPEC.loader.exec_module(oracle)


def test_enrollment_closed_canonical_file_and_private_mode(tmp_path):
    path = tmp_path / "enrollment.json"
    row = {"fixture": "SYNTHETIC_ONLY", "number": 1}
    path.write_bytes(oracle.canonical(row))
    path.chmod(0o600)
    assert oracle.enrollment_file(path) == row
    path.chmod(0o644)
    with pytest.raises(RuntimeError):
        oracle.enrollment_file(path)


def test_enrollment_rejects_symlink_duplicate_and_noncanonical(tmp_path):
    path = tmp_path / "record"
    path.write_bytes(b'{"a":1}')
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        oracle.enrollment_file(link)
    for raw in (b'{"a":1,"a":2}', b'{"a": 1}', b'x' * 2049):
        path.write_bytes(raw)
        with pytest.raises((RuntimeError, ValueError)):
            oracle.enrollment_file(path)


@pytest.mark.skipif(os.name != "posix", reason="bounded FIFO open requires POSIX")
def test_enrollment_fifo_refuses_without_blocking(tmp_path):
    path = tmp_path / "fifo"
    os.mkfifo(path, 0o600)
    with pytest.raises(RuntimeError):
        oracle.enrollment_file(path)


def test_native_socket_allocation_is_retained_before_initializer(monkeypatch):
    retained = []
    class NativeModel:
        def __new__(cls):
            return object.__new__(cls)
        def __init__(self, *args):
            assert retained == [self]
            raise OSError("synthetic initializer failure")
    monkeypatch.setattr(oracle, "_RETAINED", retained)
    monkeypatch.setattr(oracle.socket, "socket", NativeModel)
    with pytest.raises(OSError):
        oracle.own_socket()
    assert len(retained) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b'{"a": 1}\n', b'{"a":1,"a":2}\n', b'x' * 513])
async def test_control_refuses_noncanonical_duplicate_or_oversized(monkeypatch, raw):
    data = bytearray(raw)
    async def recv(sock, amount):
        part = bytes(data[:amount])
        del data[:amount]
        return part
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_recv", recv)
    with pytest.raises((RuntimeError, ValueError)):
        await oracle.receive_control(object(), time.monotonic_ns() + 500_000_000)


@pytest.mark.asyncio
async def test_control_progress_cannot_renew_deadline(monkeypatch):
    clock = [10]
    async def recv(sock, amount):
        clock[0] += 6
        return b"x"
    monkeypatch.setattr(asyncio.get_running_loop(), "sock_recv", recv)
    monkeypatch.setattr(oracle.time, "monotonic_ns", lambda: clock[0])
    with pytest.raises(RuntimeError):
        await oracle.receive_control(object(), 20)
    assert clock[0] == 22


def test_diagnostic_failure_still_retains_unknown_owner(monkeypatch):
    owner = object()
    monkeypatch.setattr(oracle, "_RETAINED", [owner])
    def fail(*args):
        raise RuntimeError("synthetic startup refusal")
    def write(*args):
        raise BrokenPipeError
    class SupervisionReachedError(Exception):
        pass
    def sleep(seconds):
        assert oracle._RETAINED[0] is owner
        raise SupervisionReachedError
    monkeypatch.setattr(oracle, "run", fail)
    monkeypatch.setattr(oracle.sys, "stderr", SimpleNamespace(write=write))
    monkeypatch.setattr(oracle.time, "sleep", sleep)
    with pytest.raises(SupervisionReachedError):
        oracle.main()


def test_no_fixture_marker_refuses_before_startup_file_access(monkeypatch):
    monkeypatch.setattr(oracle.hashlib, "sha256",
                        lambda *args: pytest.fail("must not inspect code"))
    with pytest.raises(RuntimeError):
        oracle.run([])


@pytest.mark.parametrize("state", ["partial", "uncertain", "wrong_owner"])
def test_reader_identity_never_touches_opaque_or_uncertain_child(monkeypatch, state):
    from hmp_plugin.presentation_broker_child import BrokerChildOwner
    operation = object()
    owner = BrokerChildOwner(operation)
    calls = []
    class OpaqueChild:
        @property
        def returncode(self):
            calls.append("returncode")
            pytest.fail("partial child attributes must stay opaque")
    owner._child = owner._child_snapshot = OpaqueChild()
    if state == "uncertain":
        owner._constructor_returned = True
        owner._uncertain = True
    elif state == "wrong_owner":
        owner = SimpleNamespace(_child=OpaqueChild(), _constructor_returned=True)
    monkeypatch.setattr(oracle, "_CHILD_OWNER_TYPE", BrokerChildOwner)
    assert oracle.reader_identity(owner, operation) == (None, None)
    assert not calls


def test_serve_deadline_cannot_outlive_fixed_oracle_phase(monkeypatch):
    monkeypatch.setattr(oracle.time, "monotonic_ns", lambda: 1_000_000_000)
    assert oracle.serve_deadline(1_100_000_000, 1_200_000_000) == 1_100_000_000
    for deadline in (True, 1_000_000_000, 1_300_000_000):
        with pytest.raises(RuntimeError):
            oracle.serve_deadline(deadline, 1_200_000_000)


@pytest.mark.parametrize("held_io_reference", [False, True])
def test_raw_close_requires_real_descriptor_disposal(held_io_reference):
    left, right = oracle.socket.socketpair()
    try:
        if held_io_reference:
            left._io_refs = 1  # native close marks closed but defers FD disposal
        assert oracle.close_socket(left) is (not held_io_reference)
        assert (left.fileno() == -1) is (not held_io_reference)
    finally:
        left._io_refs = 0
        left.close()
        right.close()
