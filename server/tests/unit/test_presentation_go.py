"""Finite GO ownership/write causals; real pipe and injected uncertain syscall."""

import os
import stat

import pytest

from hmp_plugin.presentation_go import GoHandoff
from hmp_plugin.presentation_jobs import FrameError


def test_real_pipe_gets_exact_go_once():
    read, write = os.pipe()
    os.set_blocking(write, False)
    handle, child = object(), object()
    try:
        sender = GoHandoff(handle=handle, child=child, fd=write, current=lambda: True)
        sender.send(handle, child, "a" * 64)
        assert os.read(read, 65) == b"a" * 64 + b"\n"
        with pytest.raises(FrameError):
            sender.send(handle, child, "a" * 64)
    finally:
        os.close(write)
        os.close(read)


@pytest.mark.parametrize("count", [0, 1, 64, None, True])
def test_partial_or_invalid_write_never_retries(count):
    calls = []
    handle, child = object(), object()

    def write(fd, body):
        calls.append((fd, body))
        return count

    sender = GoHandoff(
        handle=handle,
        child=child,
        fd=99,
        current=lambda: True,
        write=write,
        pipe_info=lambda fd: (1, 2, stat.S_IFIFO | 0o600, False),
    )
    with pytest.raises(FrameError):
        sender.send(handle, child, "a" * 64)
    with pytest.raises(FrameError):
        sender.send(handle, child, "a" * 64)
    assert len(calls) == 1


def test_wrong_child_or_retired_scope_never_writes():
    calls = []
    current = [True]
    handle, child = object(), object()
    sender = GoHandoff(
        handle=handle,
        child=child,
        fd=99,
        current=lambda: current[0],
        write=lambda fd, body: calls.append(body),
        pipe_info=lambda fd: (1, 2, stat.S_IFIFO | 0o600, False),
    )
    with pytest.raises(FrameError):
        sender.send(handle, object(), "a" * 64)
    assert calls == []
    current[0] = False
    with pytest.raises(FrameError):
        sender.send(handle, child, "a" * 64)
    assert calls == []


def test_blocking_pipe_is_refused_before_writer_binding():
    read, write = os.pipe()
    try:
        with pytest.raises(FrameError):
            GoHandoff(handle=object(), child=object(), fd=write, current=lambda: True)
    finally:
        os.close(read)
        os.close(write)


def test_replaced_pipe_identity_never_writes():
    handle, child = object(), object()
    info = [(1, 2, stat.S_IFIFO | 0o600, False)]
    calls = []
    sender = GoHandoff(
        handle=handle,
        child=child,
        fd=99,
        current=lambda: True,
        write=lambda fd, body: calls.append(body),
        pipe_info=lambda fd: info[0],
    )
    info[0] = (1, 3, stat.S_IFIFO | 0o600, False)
    with pytest.raises(FrameError):
        sender.send(handle, child, "a" * 64)
    assert calls == []


def test_write_then_exception_does_not_resend_go():
    read, write = os.pipe()
    os.set_blocking(write, False)
    handle, child = object(), object()
    calls = []

    def lost_ack(fd, body):
        calls.append(body)
        os.write(fd, body)
        raise OSError("synthetic lost acknowledgement")

    try:
        sender = GoHandoff(
            handle=handle, child=child, fd=write, current=lambda: True, write=lost_ack
        )
        with pytest.raises(FrameError):
            sender.send(handle, child, "a" * 64)
        assert os.read(read, 65) == b"a" * 64 + b"\n"
        with pytest.raises(FrameError):
            sender.send(handle, child, "a" * 64)
        assert len(calls) == 1
    finally:
        os.close(write)
        os.close(read)


@pytest.mark.parametrize("callback", ["current", "pipe_info"])
def test_callback_reentry_is_sticky_and_performs_no_write(callback):
    handle, child = object(), object()
    holder = {}
    writes = []

    def reenter():
        if "sender" in holder:
            with pytest.raises(FrameError):
                holder["sender"].send(handle, child, "a" * 64)

    def current():
        if callback == "current":
            reenter()
        return True

    def pipe_info(fd):
        if callback == "pipe_info":
            reenter()
        return (1, 2, stat.S_IFIFO | 0o600, False)

    holder["sender"] = GoHandoff(
        handle=handle,
        child=child,
        fd=99,
        current=current,
        write=lambda fd, body: writes.append(body),
        pipe_info=pipe_info,
    )
    with pytest.raises(FrameError):
        holder["sender"].send(handle, child, "a" * 64)
    with pytest.raises(FrameError):
        holder["sender"].send(handle, child, "a" * 64)
    assert writes == []
