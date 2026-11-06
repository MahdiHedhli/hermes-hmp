"""Partial native constructor custody; no input, GO, profile or group signal."""

import gc
import os
import signal
import time
import weakref
from io import FileIO
from pathlib import Path

import pytest
import yaml

from hmp_plugin import presentation_broker_child as module
from hmp_plugin.presentation_jobs import FrameError


def unknown(owner):
    assert owner.uncertain and owner.signals_retired
    assert owner._pid is None and owner._pid_snapshot is None
    assert owner._streams is None and owner._constructor_returned is False
    for action in (owner.start, owner.poll_wait, owner.terminate_once, owner.seal_unlaunched):
        with pytest.raises(FrameError):
            action()


def test_exact_native_allocation_retained_before_constructor_failure(monkeypatch):
    owner = module.BrokerChildOwner(object())
    allocated = []

    def initialize(child, *args, **kwargs):
        assert type(child) is module._POPEN_TYPE
        assert owner._child is child and owner._child_snapshot is child
        assert owner._constructor_returned is False
        allocated.append(weakref.ref(child))
        assert not hasattr(child, "pid")
        raise OSError("synthetic before child creation")

    monkeypatch.setattr(module, "_initialize_popen", initialize)
    with pytest.raises(module.BrokerChildLaunchError) as caught:
        owner.start()
    assert caught.value.failed_owner is owner
    gc.collect()
    assert allocated[0]() is owner._child_snapshot
    unknown(owner)


def test_allocation_failure_has_no_constructor_or_retry(monkeypatch):
    owner = module.BrokerChildOwner(object())
    calls = []

    def allocate():
        calls.append(1)
        raise MemoryError("synthetic allocation refusal")

    monkeypatch.setattr(module, "_allocate_popen", allocate)
    monkeypatch.setattr(module, "_initialize_popen", lambda *a, **k: pytest.fail("initialized"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert owner._child is None and calls == [1]
    unknown(owner)


def test_foreign_allocated_handle_has_no_getter_effect(monkeypatch):
    class Foreign:
        @property
        def pid(self):
            pytest.fail("partial PID getter")

        @property
        def stdin(self):
            pytest.fail("partial stream getter")

    owner = module.BrokerChildOwner(object())
    foreign = Foreign()
    monkeypatch.setattr(module, "_allocate_popen", lambda: foreign)
    monkeypatch.setattr(module, "_initialize_popen", lambda *a, **k: pytest.fail("initialized"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert owner._child is foreign and owner._child_snapshot is foreign
    unknown(owner)


@pytest.mark.parametrize("active", [[object()], None, True, ()])
def test_foreign_or_nonempty_active_never_allocates_or_sweeps(monkeypatch, active):
    owner = module.BrokerChildOwner(object())
    monkeypatch.setattr(module.subprocess, "_active", active)
    monkeypatch.setattr(module, "_allocate_popen", lambda: pytest.fail("allocated"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert module.subprocess._active is active
    unknown(owner)


def test_foreign_active_container_never_calls_length(monkeypatch):
    class Foreign:
        def __len__(self):
            pytest.fail("foreign length")

        def __iter__(self):
            pytest.fail("foreign traversal")

    owner = module.BrokerChildOwner(object())
    monkeypatch.setattr(module.subprocess, "_active", Foreign())
    monkeypatch.setattr(module, "_allocate_popen", lambda: pytest.fail("allocated"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    unknown(owner)


def test_active_list_replacement_after_allocation_is_not_swept(monkeypatch):
    owner = module.BrokerChildOwner(object())
    native = module._allocate_popen
    allocated = []

    def allocate():
        child = native()
        allocated.append(child)
        monkeypatch.setattr(module.subprocess, "_active", [])
        return child

    monkeypatch.setattr(module, "_allocate_popen", allocate)
    monkeypatch.setattr(module, "_initialize_popen", lambda *a, **k: pytest.fail("initialized"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert owner._child_snapshot is allocated[0]
    unknown(owner)


def test_original_deadline_crosses_during_allocation_no_constructor(monkeypatch):
    deadline = time.monotonic_ns() + 1_000_000_000
    owner = module.BrokerChildOwner(object(), deadline_ns=deadline)
    native = module._allocate_popen

    def allocate():
        child = native()
        monkeypatch.setattr(module.time, "monotonic_ns", lambda: deadline)
        return child

    monkeypatch.setattr(module, "_allocate_popen", allocate)
    monkeypatch.setattr(module, "_initialize_popen", lambda *a, **k: pytest.fail("late init"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert owner._deadline_ns is deadline and owner._child_snapshot is not None
    unknown(owner)


def test_allocation_reentry_poisons_before_constructor(monkeypatch):
    binding = object()
    owner = module.BrokerChildOwner(binding)
    native = module._allocate_popen

    def allocate():
        child = native()
        with pytest.raises(FrameError):
            owner.owns(binding)
        return child

    monkeypatch.setattr(module, "_allocate_popen", allocate)
    monkeypatch.setattr(module, "_initialize_popen", lambda *a, **k: pytest.fail("initialized"))
    with pytest.raises(module.BrokerChildLaunchError):
        owner.start()
    assert owner._child_snapshot is not None
    unknown(owner)


def test_real_partial_native_handle_gc_then_second_reader_no_destructor_reap(monkeypatch):
    if os.name != "posix" or os.geteuid() <= 0:
        pytest.skip("non-root POSIX actual fixed reader")
    parser = str(Path(yaml.__file__).resolve().parent)
    first = module.BrokerChildOwner(object(), parser_package=parser)
    second = module.BrokerChildOwner(object(), parser_package=parser)
    initialize = module._initialize_popen
    actual = []
    polls = []

    def fail_after_native_init(child, *args, **kwargs):
        assert first._child is child and first._child_snapshot is child
        initialize(child, *args, **kwargs)
        # Fixture independently retains this exact successfully initialized
        # native child for cleanup. This does not restore the failed owner.
        actual.append(child)
        raise OSError("synthetic after successful native constructor")

    def clean_fixture_child(child):
        if child.returncode is None:
            os.kill(child.pid, signal.SIGKILL)  # exact own unreaped fixture child only
            pid, status = os.waitpid(child.pid, 0)
            assert pid == child.pid
            child.returncode = os.waitstatus_to_exitcode(status)
        for stream in (child.stdin, child.stdout, child.stderr):
            if type(stream) is FileIO and stream.closed is False:
                FileIO.close(stream)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_initialize_popen", fail_after_native_init)
        try:
            with pytest.raises(module.BrokerChildLaunchError):
                first.start()
            native_child = actual[0]
            patch.setattr(native_child, "_internal_poll", lambda *a, **k: polls.append(1))
            reference = weakref.ref(native_child)
            gc.collect()
            assert reference() is first._child_snapshot
            assert module._empty_active() is module.subprocess._active
            assert polls == []
            unknown(first)
            pending = os.waitpid(native_child.pid, os.WNOHANG)
            if pending != (0, 0):
                native_child.returncode = os.waitstatus_to_exitcode(pending[1])
                pytest.fail("synthetic no-input reader exited unexpectedly")
            patch.setattr(module, "_initialize_popen", initialize)
            second.start()
            actual.append(second._child_snapshot)
            assert polls == [] and not module.subprocess._active
            FileIO.close(second.streams.control)  # only empty input, never GO
            end = time.monotonic() + 2
            while not second.poll_wait():
                assert time.monotonic() < end
                time.sleep(0.001)
            assert second.terminal_wait(second._binding_snapshot).exit_code == 1
            assert polls == [] and first.uncertain
        finally:
            for child in actual:
                clean_fixture_child(child)
