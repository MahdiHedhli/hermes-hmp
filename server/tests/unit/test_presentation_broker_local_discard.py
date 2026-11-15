"""Local descriptor cleanup evidence only, never full broker/service closure."""

import os
import time
from types import SimpleNamespace

import pytest

from hmp_plugin import presentation_broker_child as child_module
from hmp_plugin.presentation_broker_child import BrokerChildOwner
from hmp_plugin.presentation_broker_codec import BrokerBinding
from hmp_plugin.presentation_broker_lifecycle import operation_id
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_control_pipe import ControlCloseObservation, OwnedControlPipe
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_pipes import OwnedPresentationPipes


@pytest.fixture
def actual():
    binding = BrokerBinding("a" * 52, "b" * 32, "c" * 64, "d" * 64, operation_id(1))
    registry = BrokerRegistry(binding)
    ticket = registry.reserve(binding, "default", "METADATA", time.monotonic_ns() + 1_900_000_000)
    record = registry._records[ticket]
    streams = registry.start(ticket)
    process = record.owner
    pipes = OwnedPresentationPipes(streams.result, streams.diagnostic)
    control = OwnedControlPipe(streams.control, handle=record, child=process, current=lambda: True)
    control.close_for_drain()
    fact = control.close_observation(record, process)
    deadline = time.monotonic() + 3
    while not registry.poll_wait(ticket):
        assert time.monotonic() < deadline
        time.sleep(0.005)
    kwargs = {"process": process, "binding": record, "control": control, "control_fact": fact}
    yield registry, ticket, binding, pipes, kwargs
    # Fixture-only final cleanup: the exact own child is already reaped. No protocol
    # success or reservation release is inferred if an adversarial branch refused.
    if not pipes.drained:
        pipes._selector.close()
        for stream in (streams.result, streams.diagnostic):
            if not stream.closed:
                stream.close()


def test_actual_local_eof_keeps_started_registry_pending_and_cannot_restore_output(actual):
    registry, _ticket, binding, pipes, kwargs = actual
    end = time.monotonic_ns() + 250_000_000
    while not pipes.drained:
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert pipes.output == b"" and pipes.output_discarded and pipes.refused
    assert registry.counts.active == 1 and registry.status(binding) is RegistryStatus.PENDING
    with pytest.raises(FrameError):
        registry.acknowledge(binding)
    with pytest.raises(FrameError):
        pipes.poll(deadline=time.monotonic() + 1)
    with pytest.raises(FrameError):
        pipes.poll_discard(deadline=time.monotonic() + 0.2)  # no direct/group-proof mixing


@pytest.mark.parametrize("field", ["process", "control", "control_fact"])
def test_foreign_proof_object_never_runs_callbacks(actual, field):
    _, _, _, pipes, kwargs = actual
    callbacks = []

    class Foreign:
        def __getattr__(self, name):
            callbacks.append(name)
            raise RuntimeError("foreign callback")

    kwargs[field] = Foreign()
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
    assert callbacks == [] and pipes.refused


def test_reconstructed_control_fact_does_not_authorize_discard(actual, monkeypatch):
    _, _, _, pipes, kwargs = actual
    kwargs["control_fact"] = ControlCloseObservation(kwargs["control_fact"].descriptor)
    monkeypatch.setattr(pipes, "_poll_discard_io", lambda **k: pytest.fail("foreign fact I/O"))
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)


def test_wrong_binding_cannot_select_the_retained_child(actual, monkeypatch):
    _, _, _, pipes, kwargs = actual
    kwargs["binding"] = object()
    monkeypatch.setattr(pipes, "_poll_discard_io", lambda **k: pytest.fail("wrong binding I/O"))
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)


def test_cleanup_end_cannot_be_extended_even_after_eof(actual):
    _, _, _, pipes, kwargs = actual
    end = time.monotonic_ns() + 240_000_000
    pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end + 1)
    assert pipes.uncertain


@pytest.mark.parametrize("offset", [-1, 251_000_000])
def test_expired_or_excess_budget_does_not_read_and_cannot_be_renewed(actual, monkeypatch, offset):
    _, _, _, pipes, kwargs = actual
    monkeypatch.setattr(pipes, "_poll_discard_io", lambda **k: pytest.fail("invalid budget I/O"))
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + offset)
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 200_000_000)
    assert pipes.uncertain


def test_surviving_actual_pipe_writer_does_not_become_full_closure(monkeypatch):
    # Synthetic exact-wait backend, REAL owned pipe FDs. This is not a real child
    # qualification: it tests a surviving writer's bounded local-FD behavior.
    stdin_read, stdin_write = os.pipe()
    result_read, result_write = os.pipe()
    diagnostic_read, diagnostic_write = os.pipe()
    streams = [
        os.fdopen(fd, mode, buffering=0)
        for fd, mode in ((stdin_write, "wb"), (result_read, "rb"), (diagnostic_read, "rb"))
    ]
    child = SimpleNamespace(
        pid=765432, returncode=None, stdin=streams[0], stdout=streams[1], stderr=streams[2]
    )
    monkeypatch.setattr(child_module, "_POPEN_TYPE", type(child))
    monkeypatch.setattr(child_module, "_allocate_popen", lambda: child)
    monkeypatch.setattr(child_module, "_initialize_popen", lambda *a, **k: None)
    monkeypatch.setattr(child_module.os, "getpgid", lambda pid: os.getpgrp())
    monkeypatch.setattr(child_module.os, "waitpid", lambda pid, flags: (pid, 0))
    binding = object()
    process = BrokerChildOwner(binding)
    process.start()
    pipes = OwnedPresentationPipes(streams[1], streams[2])
    control = OwnedControlPipe(streams[0], handle=binding, child=process, current=lambda: True)
    try:
        control.close_for_drain()
        assert process.poll_wait()
        fact = control.close_observation(binding, process)
        end = time.monotonic_ns() + 250_000_000
        pipes.poll_local_discard(
            process=process, binding=binding, control=control, control_fact=fact, cleanup_end_ns=end
        )
        assert not pipes.drained and pipes.output == b"" and pipes.refused
        assert os.write(result_write, b"synthetic-discard") > 0  # another real writer still owns it
        pipes.poll_local_discard(
            process=process, binding=binding, control=control, control_fact=fact, cleanup_end_ns=end
        )
        assert not pipes.drained and pipes.output == b""
    finally:
        pipes._selector.close()
        for stream in streams:
            if not stream.closed:
                stream.close()
        for fd in (stdin_read, result_write, diagnostic_write):
            os.close(fd)


def test_local_close_uses_owning_native_fileio_despite_noop_overrides(actual, monkeypatch):
    from io import FileIO

    _, _, _, pipes, kwargs = actual
    callbacks = []
    for stream in pipes._streams.values():
        monkeypatch.setattr(stream, "close", lambda: callbacks.append("override"))
        monkeypatch.setattr(stream, "fileno", lambda: pytest.fail("foreign fileno callback"))
    end = time.monotonic_ns() + 250_000_000
    while not pipes.drained:
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert callbacks == []
    assert all(FileIO.closed.__get__(s, FileIO) for s in pipes._streams.values())


def test_nonowning_native_read_wrapper_cannot_be_local_close_proof(actual):
    from io import FileIO

    _, _, _, pipes, kwargs = actual
    stream = pipes._streams["result"]
    fd = FileIO.fileno(stream)
    borrowed = FileIO(fd, "rb", closefd=False)
    process = kwargs["process"]
    # Controlled synthetic ownership projection: keep exact owner stream identity
    # consistent while replacing the native stream with a non-owning wrapper.
    original = process._child.stdout
    snapshot = process._stream_snapshot
    view = process._streams
    process._child.stdout = borrowed
    process._stream_snapshot = (snapshot[0], borrowed, snapshot[2])
    object.__setattr__(view, "result", borrowed)
    pipes._streams["result"] = borrowed
    try:
        with pytest.raises(FrameError):
            pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
        assert os.fstat(fd) and not pipes.drained and pipes.uncertain
    finally:
        borrowed.close()
        pipes._streams["result"] = original
        process._child.stdout = original
        process._stream_snapshot = snapshot
        object.__setattr__(view, "result", original)


def test_native_local_close_failure_is_unknown_not_success_or_retry(actual, monkeypatch):
    from hmp_plugin import presentation_pipes as module

    _, _, _, pipes, kwargs = actual
    calls = []

    def fail(stream, identity):
        calls.append(stream)
        raise OSError("synthetic invoked native close failure")

    monkeypatch.setattr(module, "_close_local_file", fail)
    end = time.monotonic_ns() + 250_000_000
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert len(calls) == 1 and pipes.uncertain and not pipes.drained


def test_local_selector_close_bypasses_noop_instance_override(actual, monkeypatch):
    _, _, _, pipes, kwargs = actual
    recipe = pipes._selector_recipe
    native, native_type = recipe[2], recipe[3]
    callbacks = []
    monkeypatch.setattr(pipes._selector, "close", lambda: callbacks.append("override"))
    end = time.monotonic_ns() + 250_000_000
    while not pipes.drained:
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert callbacks == [] and native_type.closed.__get__(native, native_type) is True


def test_local_selector_noop_boundary_cannot_be_drained(actual, monkeypatch):
    from hmp_plugin import presentation_pipes as module

    _, _, _, pipes, kwargs = actual
    recipe = pipes._selector_recipe
    native, native_type = recipe[2], recipe[3]
    calls = []
    monkeypatch.setattr(module, "_close_local_selector", lambda *args: calls.append(args))
    end = time.monotonic_ns() + 250_000_000
    with pytest.raises(FrameError):
        while not pipes.drained:
            pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert len(calls) == 1 and native_type.closed.__get__(native, native_type) is False
    assert pipes.uncertain and not pipes.drained
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert len(calls) == 1


def test_local_unregister_bypasses_instance_callback_and_closes_only_held_streams(
    actual, monkeypatch
):
    _, _, _, pipes, kwargs = actual
    callbacks = []
    monkeypatch.setattr(pipes._selector, "unregister", lambda fd: callbacks.append(fd))
    end = time.monotonic_ns() + 250_000_000
    while not pipes.drained:
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert callbacks == [] and pipes.drained


def test_native_read_close_noop_is_not_drained_or_retried(actual, monkeypatch):
    from hmp_plugin import presentation_pipes as module

    _, _, _, pipes, kwargs = actual
    calls = []
    monkeypatch.setattr(module, "_close_local_file", lambda *args: calls.append(args))
    end = time.monotonic_ns() + 250_000_000
    with pytest.raises(FrameError):
        while not pipes.drained:
            pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert len(calls) == 1 and pipes.uncertain and not pipes.drained
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=end)
    assert len(calls) == 1


def test_coercible_foreign_read_fd_never_selects_io(actual):
    _, _, _, pipes, kwargs = actual
    callbacks = []

    class ForeignFd:
        def __index__(self):
            callbacks.append("index")
            return 987654

    prior = pipes._identities["result"]
    pipes._identities["result"] = (ForeignFd(), prior[1], prior[2])
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
    assert callbacks == [] and pipes.uncertain


def test_legacy_noop_read_closes_cannot_be_laundered_into_local_facts(actual, monkeypatch):
    from io import FileIO

    _, _, _, pipes, kwargs = actual
    for stream in pipes._streams.values():
        monkeypatch.setattr(stream, "close", lambda: None)
    deadline = time.monotonic() + 1
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    assert pipes.drained and all(
        not FileIO.closed.__get__(s, FileIO) for s in pipes._streams.values()
    )
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
    assert pipes.uncertain and not pipes.drained
    # Fixture owns those original native handles; bypass injected no-op teardown.
    for stream in pipes._streams.values():
        FileIO.close(stream)


def test_legacy_noop_selector_close_cannot_be_laundered_into_local_facts(actual, monkeypatch):
    _, _, _, pipes, kwargs = actual
    monkeypatch.setattr(pipes._selector, "close", lambda: None)
    deadline = time.monotonic() + 1
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    with pytest.raises(FrameError):
        pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
    assert pipes.uncertain and not pipes.drained
    recipe = pipes._selector_recipe
    recipe[4](recipe[0])  # exact fixture's concrete close; no source success claimed


def test_actual_legacy_native_closed_state_can_be_adopted_for_local_discard(actual):
    _, _, _, pipes, kwargs = actual
    deadline = time.monotonic() + 1
    while not pipes.drained:
        pipes.poll(deadline=deadline)
    pipes.poll_local_discard(**kwargs, cleanup_end_ns=time.monotonic_ns() + 250_000_000)
    assert pipes.drained and pipes.output_discarded and pipes.output == b""
