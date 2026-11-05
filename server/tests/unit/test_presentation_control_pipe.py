import os
import time

import pytest

from hmp_plugin.presentation_control_pipe import OwnedControlPipe
from hmp_plugin.presentation_input_v3 import encode_input_v3
from hmp_plugin.presentation_jobs import FrameError


def packet():
    return encode_input_v3(
        {
            "schema": 3,
            "challenge": "a" * 64,
            "epoch": 1,
            "profile": "default",
            "root": "/srv/hermes",
            "home": "/srv/hermes",
            "operation": "METADATA",
            "expected_avatar_sha": None,
            "uid": 501,
            "gid": 20,
            "dir_modes": [448, 488, 493],
            "leaf_modes": [384, 416, 420],
            "source_manifest_sha": "b" * 64,
            "deadline_ns": int((time.monotonic() + 1) * 1e9),
            "directory_policy": [[0, 0, 493], [0, 0, 493], [501, 20, 448]],
            "iid": "a" * 52,
            "canonical_fallback": "Hermes",
            "observed_at": 100,
            "parent_work_counts": {
                "read_bytes": 0,
                "hash_bytes": 0,
                "opens": 3,
                "metadata": 12,
                "path_bytes": 30,
                "yaml_nodes": 0,
                "yaml_tokens": 0,
                "raster_units": 0,
            },
        }
    )


@pytest.fixture
def pipe():
    read, write = os.pipe()
    stream = os.fdopen(write, "wb", buffering=0)
    handle, child = object(), object()
    owner = OwnedControlPipe(stream, handle=handle, child=child, current=lambda: True)
    yield owner, read, stream, handle, child
    if not stream.closed:
        stream.close()
    os.close(read)


def test_input_then_exact_go_and_actual_eof(pipe):
    owner, read, stream, handle, child = pipe
    data = packet()
    owner.write_input(data)
    owner.send_go(handle, child, "a" * 64)
    assert os.read(read, 8192) == data + b"a" * 64 + b"\n"
    assert os.read(read, 1) == b"" and stream.closed and owner.closed


def test_wrong_go_and_duplicate_input_cannot_replay(pipe):
    owner, read, _, handle, child = pipe
    data = packet()
    owner.write_input(data)
    with pytest.raises(FrameError):
        owner.write_input(data)
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)
    owner.close_for_drain()
    assert os.read(read, 8192) == data
    assert os.read(read, 1) == b""


def test_caught_current_callback_reentry_prevents_any_input_effect(pipe):
    owner, read, _, _, _ = pipe

    def reenter():
        with pytest.raises(FrameError):
            owner.write_input(packet())
        return True

    owner._current = reenter
    with pytest.raises(FrameError):
        owner.write_input(packet())
    owner.close_for_drain()
    assert os.read(read, 1) == b""


def test_changed_blocking_flag_refuses_before_input_write(pipe):
    owner, read, stream, _, _ = pipe
    os.set_blocking(stream.fileno(), True)
    with pytest.raises(FrameError):
        owner.write_input(packet())
    assert owner.uncertain
    os.set_blocking(stream.fileno(), False)
    owner.close_for_drain()
    assert os.read(read, 1) == b""


def test_go_pipe_callback_poison_cannot_reach_actual_write(pipe):
    owner, read, _, handle, child = pipe
    data = packet()
    owner.write_input(data)
    original = owner._go._pipe_info

    def poison(fd):
        info = original(fd)
        with pytest.raises(FrameError):
            owner.send_go(handle, child, "a" * 64)
        return info

    owner._go._pipe_info = poison
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)
    owner.close_for_drain()
    assert os.read(read, 8192) == data
    assert os.read(read, 1) == b""


def test_expired_after_go_pipe_callback_cannot_reach_actual_write(pipe):
    owner, read, _, handle, child = pipe
    data = packet()
    owner.write_input(data)
    original = owner._go._pipe_info

    def expire(fd):
        info = original(fd)
        owner._deadline = time.monotonic() - 1.0
        return info

    owner._go._pipe_info = expire
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)
    owner.close_for_drain()
    assert os.read(read, 8192) == data


@pytest.mark.parametrize("stage", ["input", "go"])
def test_reentry_during_final_write_never_reports_clean_success(pipe, monkeypatch, stage):
    from hmp_plugin import presentation_control_pipe as module

    owner, read, _, handle, child = pipe
    data = packet()
    if stage == "go":
        owner.write_input(data)
    actual_write = os.write

    def poison(fd, body):
        count = actual_write(fd, body)
        with pytest.raises(FrameError):
            if stage == "input":
                owner.write_input(data)
            else:
                owner.send_go(handle, child, "a" * 64)
        return count

    monkeypatch.setattr(module.os, "write", poison)
    with pytest.raises(FrameError):
        if stage == "input":
            owner.write_input(data)
        else:
            owner.send_go(handle, child, "a" * 64)
    assert owner.uncertain and not owner.closed
    if stage == "input":
        assert not owner._input_ready
    owner.close_for_drain()
    expected = data if stage == "input" else data + b"a" * 64 + b"\n"
    assert os.read(read, 8192) == expected


def test_current_scope_lost_during_pipe_check_cannot_send_go(pipe):
    owner, read, _, handle, child = pipe
    data = packet()
    owner.write_input(data)
    active = [True]
    owner._current = lambda: active[0]
    original = owner._go._pipe_info

    def changed(fd):
        info = original(fd)
        active[0] = False
        return info

    owner._go._pipe_info = changed
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)
    owner.close_for_drain()
    assert os.read(read, 8192) == data


@pytest.mark.parametrize("change", ["inode", "blocking"])
def test_final_current_callback_cannot_change_pipe_before_go(pipe, change):
    owner, read, stream, handle, child = pipe
    data = packet()
    owner.write_input(data)
    new_read, new_write = os.pipe()
    count = [0]

    def mutate():
        count[0] += 1
        if count[0] == 2:
            if change == "inode":
                os.dup2(new_write, stream.fileno())
                os.set_blocking(stream.fileno(), False)
            else:
                os.set_blocking(stream.fileno(), True)
        return True

    owner._current = mutate
    try:
        with pytest.raises(FrameError):
            owner.send_go(handle, child, "a" * 64)
        assert count[0] == 2 and owner.uncertain and not owner.closed
        assert os.read(read, 8192) == data
        if change == "inode":
            os.set_blocking(new_read, False)
            with pytest.raises(BlockingIOError):
                os.read(new_read, 65)
        else:
            os.set_blocking(stream.fileno(), False)
            owner.close_for_drain()
            assert os.read(read, 1) == b""
    finally:
        os.close(new_read)
        os.close(new_write)


def test_work_refusal_then_real_close_preserves_legacy_uncertain_but_mints_only_local_fact(pipe):
    from hmp_plugin.presentation_control_pipe import ControlCloseObservation

    owner, read, _, handle, child = pipe
    with pytest.raises(FrameError):
        owner.write_input(b"not input3")
    assert owner.work_refused and owner.uncertain and not owner.resource_uncertain
    owner.close_for_drain()
    observed = owner.close_observation(handle, child)
    assert os.read(read, 1) == b""
    assert owner.validates_close(handle, child, observed)
    assert not owner.validates_close(handle, child, ControlCloseObservation(observed.descriptor))
    assert owner.uncertain and owner.work_refused  # never restore GO/native authority
    with pytest.raises(FrameError):
        owner.send_go(handle, child, "a" * 64)


def test_close_fact_is_not_available_before_actual_close(pipe):
    owner, _, _, handle, child = pipe
    owner.closed = True  # a caller-written boolean is no close syscall
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    owner.closed = False


def test_partial_acquisition_error_retains_exact_failed_owner_and_stream(monkeypatch):
    from hmp_plugin import presentation_control_pipe as module
    from hmp_plugin.presentation_control_pipe import ControlAcquisitionError

    read, write = os.pipe()
    stream = os.fdopen(write, "wb", buffering=0)

    def failed(fd, blocking):
        raise OSError("synthetic blocking configuration failure")

    monkeypatch.setattr(module.os, "set_blocking", failed)
    try:
        with pytest.raises(ControlAcquisitionError) as error:
            OwnedControlPipe(stream, handle=object(), child=object(), current=lambda: True)
        owner = error.value.failed_owner
        assert isinstance(error.value, FrameError)
        assert str(error.value) == "BI1_CONTROL_PIPE_REFUSED"
        assert owner._stream_snapshot is stream and not stream.closed
        assert owner.resource_uncertain and owner.work_refused and owner.uncertain
        with pytest.raises(FrameError):
            owner.close_observation(owner._handle, owner._child)
    finally:
        stream.close()
        os.close(read)


def test_close_exception_cannot_be_retried_or_reclassified(monkeypatch, pipe):
    from hmp_plugin import presentation_control_pipe as module

    owner, _, stream, handle, child = pipe
    calls = []

    def failed(target):
        assert target is stream
        calls.append(1)
        raise OSError("synthetic close ambiguity")

    monkeypatch.setattr(module, "_native_close", failed)
    with pytest.raises(FrameError):
        owner.close_for_drain()
    with pytest.raises(FrameError):
        owner.close_for_drain()
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    assert calls == [1] and owner.resource_uncertain
    monkeypatch.undo()  # fixture teardown still owns this actual unclosed stream


def test_identity_drift_stays_resource_uncertain_after_restoration_and_real_close(pipe):
    owner, read, stream, handle, child = pipe
    os.set_blocking(stream.fileno(), True)
    with pytest.raises(FrameError):
        owner.write_input(packet())
    assert owner.resource_uncertain
    os.set_blocking(stream.fileno(), False)
    owner.close_for_drain()
    assert os.read(read, 1) == b""
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    assert owner.resource_uncertain


def test_replaced_stream_never_closes_the_foreign_stream(pipe):
    owner, _, _, _, _ = pipe
    callbacks = []

    class ForeignStream:
        def fileno(self):
            callbacks.append("fileno")
            return 9

        def close(self):
            callbacks.append("close")

    owner._stream = ForeignStream()
    with pytest.raises(FrameError):
        owner.close_for_drain()
    assert callbacks == [] and owner.resource_uncertain


def test_replaced_close_observation_cannot_be_restored_after_detection(pipe):
    from hmp_plugin.presentation_control_pipe import ControlCloseObservation

    owner, _, _, handle, child = pipe
    owner.close_for_drain()
    original = owner.close_observation(handle, child)
    owner._close_observation = ControlCloseObservation(original.descriptor)
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    owner._close_observation = original
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    assert owner.resource_uncertain


def test_wrong_close_fact_scope_does_not_match_another_owner(pipe):
    owner, _, _, handle, child = pipe
    owner.close_for_drain()
    with pytest.raises(FrameError):
        owner.close_observation(object(), child)
    with pytest.raises(FrameError):
        owner.close_observation(handle, object())
    assert owner.validates_close(handle, child, owner.close_observation(handle, child))


def test_overridden_noop_close_cannot_replace_actual_native_close(monkeypatch, pipe):
    owner, read, stream, handle, child = pipe
    callbacks = []
    monkeypatch.setattr(stream, "close", lambda: callbacks.append("override"))
    owner.close_for_drain()
    assert stream.closed and os.read(read, 1) == b"" and callbacks == []
    assert owner.validates_close(handle, child, owner.close_observation(handle, child))


def test_native_boundary_noop_does_not_mint_close_fact(monkeypatch, pipe):
    from hmp_plugin import presentation_control_pipe as module

    owner, _, stream, handle, child = pipe
    monkeypatch.setattr(module, "_native_close", lambda target: None)
    with pytest.raises(FrameError):
        owner.close_for_drain()
    with pytest.raises(FrameError):
        owner.close_observation(handle, child)
    assert owner.resource_uncertain and not stream.closed


def test_self_reporting_proxy_close_cannot_mint_native_close_fact():
    read, write = os.pipe()
    stream = os.fdopen(write, "wb", buffering=0)

    class Proxy:
        closed = False

        def fileno(self):
            return stream.fileno()

        def close(self):
            self.closed = True  # intentionally leaves actual descriptor open

    handle, child = object(), object()
    try:
        owner = OwnedControlPipe(Proxy(), handle=handle, child=child, current=lambda: True)
        owner.close_for_drain()
        assert owner.closed and not stream.closed  # legacy flag is not the new fact
        with pytest.raises(FrameError):
            owner.close_observation(handle, child)
    finally:
        stream.close()
        os.close(read)


def test_native_fileio_nonowning_close_cannot_mint_os_close_fact():
    from io import FileIO

    read, write = os.pipe()
    stream = FileIO(write, "wb", closefd=False)
    handle, child = object(), object()
    try:
        owner = OwnedControlPipe(stream, handle=handle, child=child, current=lambda: True)
        owner.close_for_drain()
        assert stream.closed and os.fstat(write)  # native wrapper close left actual FD open
        os.set_blocking(read, False)
        with pytest.raises(BlockingIOError):
            os.read(read, 1)
        with pytest.raises(FrameError):
            owner.close_observation(handle, child)
    finally:
        stream.close()
        os.close(write)
        os.close(read)
