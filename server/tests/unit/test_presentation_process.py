import errno
import time
from types import SimpleNamespace

import pytest

from hmp_plugin import presentation_process as module
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_pipes import OwnedPresentationPipes
from hmp_plugin.presentation_process import PresentationProcessOwner, ProcessLaunchError


def fake_owner(monkeypatch):
    child = SimpleNamespace(pid=123456, returncode=None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: child)
    owner = PresentationProcessOwner()
    owner.start()
    return owner, child


def test_exact_actual_child_eof_terminal_wait_and_group_probe():
    owner = PresentationProcessOwner()
    owner.start()
    child = owner.child
    pipes = OwnedPresentationPipes(child.stdout, child.stderr)
    # Only fixed isolated reader, empty input; no profile/private file is read.
    child.stdin.close()
    deadline = time.monotonic() + 2.0
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    while not owner.poll_wait():
        assert time.monotonic() < deadline
        time.sleep(0.005)
    assert owner.reaped and owner.exit_code == 1
    assert child.returncode == 1 and owner.signals_retired
    assert owner.probe_group_absence()
    assert pipes.output == b""


@pytest.mark.parametrize("result", [(0, 0), (123456, 0), (123456, 3 << 8)])
def test_pending_and_terminal_status_are_distinct(monkeypatch, result):
    owner, child = fake_owner(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: result)
    assert owner.poll_wait() is (result[0] != 0)
    if result[0]:
        assert owner.reaped and owner.signals_retired
        assert child.returncode == result[1] >> 8
    else:
        assert not owner.reaped and child.returncode is None


@pytest.mark.parametrize("result", [(99999, 0), (123456, 0x7F), (True, 0)])
def test_wrong_nonterminal_or_malformed_wait_is_not_reap(monkeypatch, result):
    owner, child = fake_owner(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: result)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner.uncertain and not owner.reaped and child.returncode is None


def test_echild_is_unknown_not_popen_compatibility_success(monkeypatch):
    owner, _ = fake_owner(monkeypatch)

    def fail(pid, flags):
        raise ChildProcessError(errno.ECHILD, "synthetic other reaper")

    monkeypatch.setattr(module.os, "waitpid", fail)
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert owner.uncertain and not owner.reaped


def test_failed_launch_retains_exact_owner_without_retry(monkeypatch):
    owner = PresentationProcessOwner()
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise OSError("synthetic uncertain launch")

    monkeypatch.setattr(module.subprocess, "Popen", fail)
    with pytest.raises(ProcessLaunchError) as captured:
        owner.start()
    assert captured.value.failed_owner is owner
    with pytest.raises(FrameError):
        owner.start()
    assert calls == [1] and owner.uncertain


def test_caught_launch_recipe_reentry_blocks_process_creation(monkeypatch):
    owner = PresentationProcessOwner()
    recipe = module.child_launch()
    calls = []

    def reenter():
        with pytest.raises(FrameError):
            owner.start()
        return recipe

    monkeypatch.setattr(module, "child_launch", reenter)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: calls.append(1))
    with pytest.raises(FrameError):
        owner.start()
    assert calls == [] and owner.uncertain


def test_mutated_popen_pid_cannot_select_another_child_for_wait(monkeypatch):
    owner, child = fake_owner(monkeypatch)
    child.pid = 654321
    calls = []
    monkeypatch.setattr(module.os, "waitpid", lambda *args: calls.append(args))
    with pytest.raises(FrameError):
        owner.poll_wait()
    assert calls == [] and owner.uncertain


@pytest.mark.parametrize("outcome", ["gone", "exists", "denied"])
def test_post_reap_group_probe_is_zero_only_and_absence_requires_esrch(monkeypatch, outcome):
    owner, _ = fake_owner(monkeypatch)
    monkeypatch.setattr(module.os, "waitpid", lambda pid, flags: (pid, 0))
    assert owner.poll_wait()
    calls = []

    def probe(pid, number):
        calls.append((pid, number))
        if outcome != "exists":
            raise OSError(errno.ESRCH if outcome == "gone" else errno.EPERM, "synthetic")

    monkeypatch.setattr(module.os, "killpg", probe)
    if outcome == "denied":
        with pytest.raises(FrameError):
            owner.probe_group_absence()
    else:
        assert owner.probe_group_absence() is (outcome == "gone")
    assert owner.group_absent is (outcome == "gone")
    assert calls == [(123456, 0)]
    with pytest.raises(FrameError):
        owner.probe_group_absence()
    assert calls == [(123456, 0)]
