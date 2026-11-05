"""Child-only custody causals; fixed worker receives no profile/GO/content."""

import errno
import os
import signal
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from hmp_plugin import presentation_broker_child as module
from hmp_plugin.presentation_broker_child import (
    BrokerChildLaunchError,
    BrokerChildOwner,
    ChildWaitObservation,
)
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_pipes import OwnedPresentationPipes


def fake(monkeypatch):
    child = SimpleNamespace(
        pid=123456, returncode=None, stdin=object(), stdout=object(), stderr=object()
    )
    calls = []

    def start(*args, **kwargs):
        calls.append((args, kwargs))
        return child

    monkeypatch.setattr(module.subprocess, "Popen", start)
    monkeypatch.setattr(module.os, "getpgid", lambda pid: os.getpgrp())
    monkeypatch.setattr(
        module.os, "killpg", lambda *args: pytest.fail("group signal/probe forbidden")
    )
    binding = object()
    owner = BrokerChildOwner(binding)
    owner.start()
    return owner, binding, child, calls


def test_captured_fixed_launch_shared_group_and_stream_only_surface(monkeypatch):
    owner, binding, child, calls = fake(monkeypatch)
    args, kwargs = calls[0]
    assert args[0] is owner._launch.argv
    assert kwargs == {
        "env": {"LANG": "C", "LC_ALL": "C"},
        "stdin": -1,
        "stdout": -1,
        "stderr": -1,
        "bufsize": 0,
        "close_fds": True,
        "pass_fds": (),
        "start_new_session": False,
    }
    assert owner.owns(binding) and not owner.owns(object())
    assert owner.streams.control is child.stdin
    assert owner.streams.result is child.stdout
    assert owner.streams.diagnostic is child.stderr
    for absent in ("child", "group_absent", "probe_group_absence", "closed", "pid"):
        assert not hasattr(owner, absent)
    with pytest.raises(FrameError):
        owner.start()
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [(0, 0), (3 << 8, 3), (9, -9)])
def test_terminal_fact_is_minted_bound_and_cannot_be_reconstructed(monkeypatch, status, code):
    owner, binding, child, _ = fake(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, status))
    assert owner.poll_wait()
    observed = owner.terminal_wait(binding)
    assert (observed.raw_status, observed.exit_code) == (status, code)
    assert owner.validates_wait(binding, observed)
    assert not owner.validates_wait(object(), observed)
    assert not owner.validates_wait(binding, ChildWaitObservation(status, code))
    assert owner.signals_retired and child.returncode == code
    with pytest.raises(FrameError):
        owner.poll_wait()
    with pytest.raises(FrameError):
        owner.terminate_once()


@pytest.mark.parametrize(
    "result",
    [
        (0, 1),
        (99999, 0),
        (123456, 0x7F),
        (True, 0),
        (123456, True),
        (123456, -1),
        (123456, 1 << 80),
        [123456, 0],
        (),
    ],
)
def test_malformed_wrong_nonterminal_wait_is_sticky_unknown(monkeypatch, result):
    owner, binding, child, _ = fake(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda *args: result)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner.uncertain and owner.signals_retired and child.returncode is None
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)
    assert owner._child is child  # strong retention on uncertain path


def test_pending_is_not_terminal_or_closure(monkeypatch):
    owner, binding, child, _ = fake(monkeypatch)
    calls = []

    def pending(*args):
        calls.append(args)
        return (0, 0)

    monkeypatch.setattr(module.os, "waitpid", pending)
    assert not owner.poll_wait()
    assert calls == [(child.pid, os.WNOHANG)]
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)
    assert not owner.uncertain and not owner.signals_retired


def test_echild_retires_signals_without_inventing_returncode(monkeypatch):
    owner, _, child, _ = fake(monkeypatch)

    def stolen(*args):
        raise ChildProcessError(errno.ECHILD, "synthetic stolen reap")

    monkeypatch.setattr(module.os, "waitpid", stolen)
    with pytest.raises(FrameError):
        owner.poll_wait()
    monkeypatch.setattr(module.os, "kill", lambda *args: pytest.fail("unknown child signaled"))
    with pytest.raises(FrameError):
        owner.terminate_once()
    assert child.returncode is None and owner._child_snapshot is child


def test_single_exact_pid_signal_is_not_wait_fact(monkeypatch):
    owner, binding, child, _ = fake(monkeypatch)
    calls = []
    monkeypatch.setattr(module.os, "kill", lambda *args: calls.append(args))
    owner.terminate_once()
    assert calls == [(child.pid, signal.SIGKILL)]
    with pytest.raises(FrameError):
        owner.terminate_once()
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, 9))
    assert owner.poll_wait()
    assert owner.terminal_wait(binding).exit_code == -9


def test_ambiguous_signal_never_retries(monkeypatch):
    owner, _, child, _ = fake(monkeypatch)
    signal_call = []

    def fail(*args):
        signal_call.append(args)
        raise OSError("synthetic ambiguity")

    monkeypatch.setattr(module.os, "kill", fail)
    with pytest.raises(FrameError):
        owner.terminate_once()
    with pytest.raises(FrameError):
        owner.terminate_once()
    assert signal_call == [(child.pid, signal.SIGKILL)]
    assert owner.uncertain and owner._child is child


@pytest.mark.parametrize(
    "drift", ["binding", "recipe", "pid", "handle", "returncode", "stream", "context"]
)
@pytest.mark.parametrize("action", ["poll_wait", "terminate_once"])
def test_drift_before_syscall_poisoned_even_after_restoration(monkeypatch, drift, action):
    owner, _, child, _ = fake(monkeypatch)
    if drift == "binding":
        owner._binding = object()
    elif drift == "recipe":
        owner._launch = replace(owner._launch)
    elif drift == "pid":
        child.pid += 1
    elif drift == "handle":
        owner._child = None
    elif drift == "returncode":
        child.returncode = False
    elif drift == "stream":
        child.stdout = object()
    else:
        owner._context = (os.getpid(), os.getpgrp())  # equal values, different captured context
    monkeypatch.setattr(module.os, "waitpid", lambda *args: pytest.fail("drift wait"))
    monkeypatch.setattr(module.os, "kill", lambda *args: pytest.fail("drift signal"))
    with pytest.raises(FrameError):
        getattr(owner, action)()
    owner._binding = owner._binding_snapshot
    owner._launch = owner._launch_snapshot
    with pytest.raises(FrameError):
        getattr(owner, action)()
    assert owner.uncertain and owner._child_snapshot is child


@pytest.mark.parametrize(
    "field,value", [("raw_status", False), ("exit_code", False), ("exit_code", 99)]
)
def test_observation_value_drift_cannot_be_revalidated(monkeypatch, field, value):
    owner, binding, _, _ = fake(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, 0))
    assert owner.poll_wait()
    observed = owner.terminal_wait(binding)
    object.__setattr__(observed, field, value)
    with pytest.raises(FrameError):
        owner.validates_wait(binding, observed)
    assert owner.uncertain


def test_launch_failure_retains_owner_and_no_retry(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise OSError("synthetic launch ambiguity")

    monkeypatch.setattr(module.subprocess, "Popen", fail)
    owner = BrokerChildOwner(object())
    with pytest.raises(BrokerChildLaunchError) as error:
        owner.start()
    assert error.value.failed_owner is owner
    with pytest.raises(FrameError):
        owner.start()
    assert calls == [1] and owner.uncertain


def test_wrong_group_after_launch_retains_partial_handle_no_signal(monkeypatch):
    owner, _, child, _ = fake(monkeypatch)
    second = BrokerChildOwner(object())
    monkeypatch.setattr(module.os, "getpgid", lambda pid: -1)
    monkeypatch.setattr(module.os, "kill", lambda *args: pytest.fail("layout guess signal"))
    with pytest.raises(FrameError):
        second.start()
    assert second.uncertain and second._child is child
    assert not owner.uncertain


def test_never_launch_seal_is_explicit_once(monkeypatch):
    owner = BrokerChildOwner(object())
    assert not owner.never_launched_closed
    owner.seal_unlaunched()
    assert owner.never_launched_closed
    monkeypatch.setattr(
        module.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("sealed launch")
    )
    with pytest.raises(FrameError):
        owner.start()
    with pytest.raises(FrameError):
        owner.seal_unlaunched()


def test_reentry_poison_is_sticky():
    owner = BrokerChildOwner(object())
    owner._lock.acquire()
    try:
        with pytest.raises(FrameError):
            owner.owns(object())
    finally:
        owner._lock.release()
    with pytest.raises(FrameError):
        owner.start()
    assert owner.signals_retired


def drain_wait(owner, streams):
    if not streams.control.closed:
        streams.control.close()
    pipes = OwnedPresentationPipes(streams.result, streams.diagnostic)
    deadline = time.monotonic() + 3.0
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    while not owner.poll_wait():
        assert time.monotonic() < deadline
        time.sleep(0.005)
    return pipes


def test_actual_fixed_reader_empty_input_same_group_exact_wait():
    binding = object()
    owner = BrokerChildOwner(binding)
    owner.start()
    streams = owner.streams
    assert os.getpgid(owner._pid) == os.getpgrp()
    pipes = drain_wait(owner, streams)
    assert pipes.output == b"" and pipes.drained
    assert owner.terminal_wait(binding).exit_code == 1
    assert owner.validates_wait(binding, owner.terminal_wait(binding))
    assert not hasattr(owner, "group_absent")


def test_actual_child_only_kill_leaves_other_owned_reader_and_controller_alive():
    parser = str(Path(yaml.__file__).parent.resolve())
    binding, other_binding = object(), object()
    owner = BrokerChildOwner(binding, parser_package=parser)
    other = BrokerChildOwner(other_binding, parser_package=parser)
    owner.start()
    other.start()
    streams, other_streams = owner.streams, other.streams
    # Pending exact wait proves only own child has not been reaped; no readiness claim.
    assert not owner.poll_wait() and not other.poll_wait()
    owner.terminate_once()
    pipes = drain_wait(owner, streams)
    assert pipes.drained and owner.terminal_wait(binding).exit_code == -signal.SIGKILL
    assert os.getpid() == owner._context[0] and not other.poll_wait()
    other_pipes = drain_wait(other, other_streams)
    assert other_pipes.drained and other.terminal_wait(other_binding).exit_code == 1


def test_exact_reap_fact_survives_conversion_failure_without_fake_returncode(monkeypatch):
    owner, binding, child, _ = fake(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, 0))

    def fail(status):
        raise RuntimeError("synthetic interruption")

    monkeypatch.setattr(module.os, "waitstatus_to_exitcode", fail)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner._raw_terminal_status == 0 and owner.signals_retired
    assert child.returncode is None and owner._child_snapshot is child
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)


def test_reentry_during_wait_preserves_exact_fact_but_refuses_observation(monkeypatch):
    owner, binding, child, _ = fake(monkeypatch)

    def race(pid, flags):
        with pytest.raises(FrameError):
            owner.owns(binding)
        return (pid, 0)

    monkeypatch.setattr(module.os, "waitpid", race)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner._raw_terminal_status == 0 and child.returncode == 0
    assert owner.uncertain
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)


def test_equal_reconstructed_observation_field_is_not_owner_minted(monkeypatch):
    owner, binding, _, _ = fake(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, 0))
    assert owner.poll_wait()
    owner._wait = ChildWaitObservation(0, 0)
    with pytest.raises(FrameError):
        owner.terminal_wait(binding)


@pytest.mark.parametrize("context", ["fork", "group"])
def test_os_context_change_refuses_before_wait(monkeypatch, context):
    owner, _, _, _ = fake(monkeypatch)
    if context == "fork":
        monkeypatch.setattr(module.os, "getpid", lambda: owner._context[0] + 1)
    else:
        monkeypatch.setattr(module.os, "getpgrp", lambda: owner._context[1] + 1)
    monkeypatch.setattr(module.os, "waitpid", lambda *args: pytest.fail("changed context wait"))
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner.uncertain


def test_in_place_recipe_drift_refuses_before_launch(monkeypatch):
    owner = BrokerChildOwner(object())
    original = owner._launch.argv
    object.__setattr__(owner._launch, "argv", ("/untrusted",))
    monkeypatch.setattr(
        module.subprocess, "Popen", lambda *a, **k: pytest.fail("changed argv launched")
    )
    with pytest.raises(FrameError):
        owner.start()
    object.__setattr__(owner._launch, "argv", original)
    with pytest.raises(FrameError):
        owner.start()
    assert owner.uncertain


@pytest.mark.parametrize("field", ["_pid", "_pid_snapshot"])
@pytest.mark.parametrize("action", ["poll_wait", "terminate_once"])
def test_coercible_equal_foreign_pid_cannot_select_syscall(monkeypatch, field, action):
    owner, _, _, _ = fake(monkeypatch)
    callbacks = []

    class ForeignPid:
        def __eq__(self, other):
            callbacks.append("eq")
            return True

        def __index__(self):
            callbacks.append("index")
            return 654321

    setattr(owner, field, ForeignPid())
    monkeypatch.setattr(module.os, "waitpid", lambda *args: pytest.fail("foreign pid wait"))
    monkeypatch.setattr(module.os, "kill", lambda *args: pytest.fail("foreign pid signal"))
    with pytest.raises(FrameError):
        getattr(owner, action)()
    assert owner.uncertain and callbacks == []


def test_foreign_stream_bundle_properties_never_run_before_signal(monkeypatch):
    owner, _, _, _ = fake(monkeypatch)
    callbacks = []

    class ForeignStreams:
        @property
        def control(self):
            callbacks.append("control")
            owner._pid = 765432
            return owner._stream_snapshot[0]

    owner._streams = ForeignStreams()
    monkeypatch.setattr(module.os, "kill", lambda *args: pytest.fail("foreign stream signal"))
    with pytest.raises(FrameError):
        owner.terminate_once()
    assert owner.uncertain and callbacks == []


def test_foreign_executable_cannot_compare_or_select_path(monkeypatch):
    owner = BrokerChildOwner(object())
    callbacks = []

    class ForeignExecutable:
        def __eq__(self, other):
            callbacks.append("eq")
            return True

        def __fspath__(self):
            callbacks.append("fspath")
            return "/untrusted"

    original = owner._launch.argv
    object.__setattr__(owner._launch, "argv", (ForeignExecutable(), *original[1:]))
    monkeypatch.setattr(
        module.subprocess, "Popen", lambda *a, **k: pytest.fail("foreign executable")
    )
    with pytest.raises(FrameError):
        owner.start()
    assert owner.uncertain and callbacks == []


def test_context_read_failure_retires_signals_stickily(monkeypatch):
    owner, _, _, _ = fake(monkeypatch)

    def fail():
        raise OSError("synthetic context failure")

    monkeypatch.setattr(module.os, "getpgrp", fail)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner.uncertain and owner.signals_retired


def test_original_deadline_checked_inside_owner_before_popen(monkeypatch):
    deadline = time.monotonic_ns() + 1_000_000_000
    owner = BrokerChildOwner(object(), deadline_ns=deadline)
    monkeypatch.setattr(module.time, "monotonic_ns", lambda: deadline)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("late spawn"))
    with pytest.raises(BrokerChildLaunchError):
        owner.start()
    assert owner.uncertain and owner.signals_retired


@pytest.mark.parametrize("deadline", [True, 0, -1, float("inf"), 1 << 63])
def test_original_deadline_requires_exact_bounded_integer(deadline):
    with pytest.raises(FrameError):
        BrokerChildOwner(object(), deadline_ns=deadline)
