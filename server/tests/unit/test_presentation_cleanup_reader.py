"""Actual same-task duplex CANCEL/drain on synthetic private enrolled sockets."""
import asyncio
import errno
import os
import socket
from contextlib import suppress

import pytest

from hmp_plugin import presentation_cleanup_reader as cleanup
from hmp_plugin import presentation_result_transport as result
from hmp_plugin import presentation_terminal_claim as terminal
from hmp_plugin.presentation_broker_codec import BrokerHeader, encode_header, header_size
from hmp_plugin.presentation_broker_service import BrokerServiceSpine, SocketChannel
from hmp_plugin.presentation_cancel_budget import CancellationBudget, CancellationWindow
from hmp_plugin.presentation_jobs import State
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

from .test_presentation_broker_service import local as local
from .test_presentation_result_transport import coupled_result as coupled_result
from .test_presentation_supervisor import context as context
from .test_presentation_terminal_claim import claim as claim

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


@pytest.mark.parametrize("phase,drift", [
    ("prefix", None), ("header", None), ("body", None),
    ("prefix", "outer"), ("body", "remaining_foreign"),
    ("body", "remaining_int"), ("prefix", "kernel_blocking"),
    ("prefix", "python_timeout"), ("body", "shorten_blocked"),
    ("body", "shorten_before"), ("body", "change_init_before"),
    ("body", "change_init_after"), ("body", "retired_proof"),
    ("body", "shorten_ready"), ("body", "signal_before"),
    ("body", "signal_after"), ("body", "change_pair"),
    ("body", "native_shorten"), ("body", "complete_terminal"),
    ("body", "torn_cancel"), ("body", "external_work"), ("body", "external_cleanup"),
    ("body", "external_cleanup_before"),
])
async def test_post_go_cancel_writes_while_original_reader_drains_torn_result(
    coupled_result, monkeypatch, phase, drift, claim
):
    remote, row, spine, _ = coupled_result
    original_send, original_cancel = result._LOOP.sock_sendall, SocketChannel.send_cancel
    original_wait = result.SelectorReadiness.wait
    reader_waiting = asyncio.Event()
    written, parked = asyncio.Event(), asyncio.Event()
    trace = []
    writer_entered = asyncio.Event()
    cancel_writes = []
    cut = []
    body_header, remaining_wire, cancel_fragments = [], [], []
    external_cases = {"external_work", "external_cleanup", "external_cleanup_before"}
    blocked_cases = external_cases | {"shorten_blocked", "shorten_ready"}
    foreign = bytearray(b"foreign must remain untouched")
    mutations, native_calls, callbacks = [], [], []
    original_activate = cleanup.CleanupReadGate.activate
    original_recv = cleanup._RECV
    original_initialize = cleanup._initialize_future
    original_timeout = cleanup._TIMEOUT

    def timeout(sock):
        owner = remote._cleanup_owner_snapshot
        gate = owner._read_gate_snapshot if owner is not None else None
        if drift == "native_shorten" and gate is not None and gate._activated and not mutations:
            mutations.append(drift)
            end = CancellationBudget.inspect(gate._refs[8])[2]
            cleanup.CleanupReadGate.inherit(
                gate, CancellationWindow(end - 550_000_000, end - 300_000_000))
        return original_timeout(sock)

    monkeypatch.setattr(cleanup, "_TIMEOUT", timeout)
    notice_faults = {"change_init_before", "change_init_after", "retired_proof",
                     "signal_before", "signal_after", "change_pair"}
    change_cases = notice_faults | {"shorten_before"}

    def initialize(future, loop):
        owner = remote._cleanup_owner_snapshot
        gate = owner._read_gate_snapshot if owner is not None else None
        is_change = (gate is not None and gate._change_active
                     and gate._change_origin.future is future)
        if is_change and drift == "change_init_before":
            raise RuntimeError("synthetic pre-initialization failure")
        original_initialize(future, loop)
        if is_change and drift == "change_init_after":
            raise RuntimeError("synthetic post-initialization failure")

    original_signal = cleanup.CleanupReadGate._signal_change
    foreign_notice = asyncio.get_running_loop().create_future()

    def signal(gate, future):
        if drift == "signal_before":
            raise RuntimeError("synthetic pre-signal failure")
        original_signal(gate, future)
        if drift == "signal_after":
            raise RuntimeError("synthetic post-signal failure")

    monkeypatch.setattr(cleanup.CleanupReadGate, "_signal_change", signal)
    monkeypatch.setattr(cleanup, "_initialize_future", initialize)
    original_retire = BrokerServiceSpine._retire_connection
    cleanup_waiting, rebound, release_peer = asyncio.Event(), asyncio.Event(), asyncio.Event()
    ends = []

    async def retire(service, record):
        if drift in blocked_cases:
            await release_peer.wait()  # synthetic service retains its original socket
        if drift == "complete_terminal":
            handoff = terminal.encode_handoff(claim, terminal.CleanupStamp(1, 250_000_001))
            header = encode_header(BrokerHeader(remote._binding_snapshot, "TERMINAL",
                                               2, len(handoff), 2))
            await original_send(asyncio.get_running_loop(), record.socket,
                                remaining_wire[0] + header + handoff)
        return await original_retire(service, record)

    monkeypatch.setattr(BrokerServiceSpine, "_retire_connection", retire)

    class Foreign:
        def __sub__(self, other):
            callbacks.append("subtraction")
            raise AssertionError("foreign arithmetic must not run")

    def activate(gate, reader):
        value = original_activate(gate, reader)
        if drift == "kernel_blocking":
            os.set_blocking(row[3]._fd_snapshot, True)
            mutations.append(drift)
        elif drift == "python_timeout":
            row[3]._socket_snapshot.settimeout(0.1)
            mutations.append(drift)
        return value

    def recv(sock, count):
        native_calls.append(count)
        if drift in change_cases and not mutations:
            mutations.append(drift)
            raise BlockingIOError(errno.EAGAIN, "synthetic known EAGAIN before EOF")
        assert drift not in ("kernel_blocking", "python_timeout")
        part = original_recv(sock, count)
        gate = remote._cleanup_owner_snapshot._read_gate_snapshot
        if drift not in ({None, "complete_terminal", "torn_cancel"} | blocked_cases) \
                and not mutations:
            mutations.append(drift)
            if drift == "outer":
                gate._outer = gate._outer_origin = foreign
            elif drift == "remaining_foreign":
                gate._remaining_body = Foreign()
            elif drift == "remaining_int":
                gate._remaining_body += 1
        return part

    monkeypatch.setattr(cleanup.CleanupReadGate, "activate", activate)
    monkeypatch.setattr(cleanup, "_RECV", recv)

    async def send(loop, sock, data):
        owner = remote._cleanup_owner_snapshot
        if (owner is not None and data is not None and data is owner._cancel_wire_snapshot):
            cancel_writes.append(data)
        if (drift == "torn_cancel" and owner is not None
                and data is owner._cancel_wire_snapshot and data is not None):
            cancel_fragments.append(data[:3])
            await original_send(loop, sock, data[:3])
            raise OSError("synthetic partial CANCEL")
        records = spine._records
        writer = records[0].result_writer_snapshot if records else None
        if (writer is not None and writer._write_attempted and not cut
                and sock is writer._scope_snapshot.channel._socket_snapshot):
            if phase == "body" and not body_header:
                body_header.append(8 + header_size(data[:8]))
                assert len(data) == body_header[0]
                return await original_send(loop, sock, data)
            end_header = body_header[0] if body_header else 8 + header_size(data[:8])
            n = (3 if phase in ("prefix", "body")
                 else 8 + (end_header - 8) // 2)
            cut.append(end_header + n if phase == "body" else n)
            remaining_wire.append(data[n:])
            await original_send(loop, sock, data[:n])
            written.set()
            await parked.wait()  # original service task is retired by its actual CANCEL reader
            raise AssertionError("torn result must never be resumed/appended")
        return await original_send(loop, sock, data)

    async def cancel(channel, owner):
        work = owner._allocations_snapshot[1].task
        trace.append((work, work.done(), channel._reading,
                      owner._read_gate_snapshot._fact_origin is not None))
        writer_entered.set()
        if drift == "external_cleanup_before":
            await parked.wait()  # before original CANCEL intent or native write
        return await original_cancel(channel, owner)

    async def wait(waiter, end, **options):
        owner = remote._cleanup_owner_snapshot
        gate = owner._read_gate_snapshot if owner is not None else None
        if gate is not None and gate._activated:
            ends.append(end)
            cleanup_waiting.set()
            if len(ends) > 1 and end < ends[0]:
                rebound.set()
            if drift in ("shorten_before", "retired_proof", "signal_before",
                         "signal_after", "change_pair") and len(ends) == 1:
                if drift == "change_pair":
                    change = gate._change_origin
                    gate._change = gate._change_origin = cleanup._Change(
                        foreign_notice, change.epoch, change.generation, change.end)
                earlier = CancellationWindow(end - 290_000_000, end - 40_000_000)
                cleanup.CleanupReadGate.inherit(gate, earlier)
        reader = remote._result_owner_snapshot
        if (reader is not None and cut and reader._cursor_origin.received == cut[0]
                and waiter._origin_scope.sock is row[3]._socket_snapshot):
            reader_waiting.set()
        try:
            return await original_wait(waiter, end, **options)
        finally:
            if gate is not None and gate._activated and drift == "retired_proof":
                waiter._attempted = "unknown"

    monkeypatch.setattr(result._LOOP, "sock_sendall", send)
    monkeypatch.setattr(SocketChannel, "send_cancel", cancel)
    monkeypatch.setattr(result.SelectorReadiness, "wait", wait)
    assert await remote.begin_ready() and await remote.go()
    await written.wait()
    owner = remote._cleanup_owner_snapshot
    work = owner._allocations_snapshot[1].task
    try:
        await asyncio.wait_for(reader_waiting.wait(), 1)
    except TimeoutError:
        r = remote._result_owner_snapshot
        c = r._cursor_origin if r is not None else None
        waiter = c.waiter if c is not None else None
        coro, stack = work.get_coro(), []
        while hasattr(coro, "cr_await"):
            stack.append(coro.cr_code.co_name)
            coro = coro.cr_await
        waiter_state = (None if waiter is None else
                        (waiter._attempted, waiter._retired, waiter._unknown,
                         waiter._future_origin.done()))
        pytest.fail(f"partial wait missing: cut={cut}, received="
                    f"{None if c is None else c.received}, "
                    f"failed={None if r is None else r._failed}, "
                    f"intent={owner._intent}, unknown={owner._unknown}, work_done={work.done()}, "
                    f"waiter={waiter_state}, stack={stack}")
    RemoteCleanupOwner.request(owner)
    if drift in blocked_cases:
        try:
            await asyncio.wait_for(cleanup_waiting.wait(), 1)
            gate = owner._read_gate_snapshot
            waiter = gate._waiter
            assert waiter._attempted and not waiter._retired
            assert asyncio.current_task() is owner._caller_snapshot
            await asyncio.wait_for(writer_entered.wait(), 1)
            assert len(trace) == 1  # order peer EOF after the original writer entry
            if drift in external_cases:
                target = (work if drift == "external_work"
                          else owner._allocations_snapshot[0].task)
                target.cancel()  # only the exact synthetic original Task
            else:
                _, _, end, failed = CancellationBudget.inspect(gate._refs[8])
                assert not failed
                earlier = CancellationWindow(end - 290_000_000, end - 40_000_000)
                if drift == "shorten_ready":
                    cleanup._FUTURE.set_result(waiter._future_origin, None)
                    assert waiter._future_origin.done()  # readiness hint, no payload consumed
                cleanup.CleanupReadGate.inherit(gate, earlier)
                await asyncio.wait_for(rebound.wait(), 1)
                assert ends[1] == earlier.end_ns
                assert waiter._retired and not waiter._unknown
                assert CancellationBudget.inspect(gate._refs[8])[2] == earlier.end_ns
                # Controlled stream EOF must not wait for variable native service teardown.
                spine._records[0].socket.shutdown(socket.SHUT_WR)
        finally:
            release_peer.set()
    with suppress(BaseException):
        await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
    if drift in external_cases or drift == "torn_cancel":
        with suppress(BaseException):
            await asyncio.wait_for(asyncio.shield(work), 1)
    gate = owner._read_gate_snapshot
    assert gate._requested and gate._activated and gate._fact_origin is not None
    if drift == "complete_terminal":
        assert gate._terminal_data == terminal.TerminalHandoff(
            claim, terminal.CleanupStamp(1, 250_000_001))
        assert not gate._failed and gate._done and not gate._eof
        assert owner._unknown and not owner._socket_closed and not owner._clock_closed
        assert remote._job_origin_snapshot.result is None
        assert not remote._job_origin_snapshot.credit_released
        assert gate._generation == 0  # unaccepted wire stamp never adopted
        return
    if drift in external_cases or drift == "torn_cancel":
        assert work.done() and gate._done and owner._unknown
        assert not owner._socket_closed and not owner._clock_closed
        assert remote._job_origin_snapshot.result is None
        assert not remote._job_origin_snapshot.credit_released
        assert len(trace) == 1  # no replacement cleanup writer
        if drift == "external_cleanup_before":
            assert not cancel_writes and not owner._cancel_write_attempted
            assert not owner._write_fact_consumed and owner._cancel_wire_snapshot is None
        else:
            assert len(cancel_writes) == 1
        if drift == "torn_cancel":
            assert cancel_fragments == [owner._cancel_wire_snapshot[:3]]
            assert not owner._cancel_write_completed and owner._write_fact_consumed
        return
    if drift in notice_faults:
        assert mutations == [drift] and gate._failed and owner._unknown
        assert gate._change_active and native_calls
        if drift == "retired_proof":
            assert gate._io_unknown and row[3]._reading
        elif drift in ("change_init_before", "change_init_after"):
            assert not gate._change_initialized
        else:
            assert gate._change_initialized
            assert not foreign_notice.done()
        if drift in ("signal_before", "signal_after"):
            assert CancellationBudget.inspect(gate._refs[8])[3]
        assert not remote._job_origin_snapshot.credit_released
        return
    if drift == "shorten_before":
        assert mutations == [drift] and gate._generation == 1 and ends
        assert CancellationBudget.inspect(gate._refs[8])[2] == ends[0] - 40_000_000
        assert gate._eof and not gate._io_unknown
        assert owner._socket_closed and owner._clock_closed
        assert not remote._job_origin_snapshot.credit_released
        return
    if drift not in (None, "shorten_blocked", "shorten_ready"):
        row[3]._socket_snapshot.setblocking(False)  # restore only the synthetic test socket
        assert mutations == [drift] and not callbacks
        assert foreign == b"foreign must remain untouched"
        assert gate._failed and owner._unknown
        if drift in ("kernel_blocking", "python_timeout", "native_shorten"):
            assert not native_calls
        else:
            assert native_calls and gate._io_unknown and row[3]._reading
        assert work.done() and gate._done
        assert remote._job_origin_snapshot.result is None
        assert not remote._job_origin_snapshot.credit_released
        return
    assert trace == [(work, False, True, True)]
    assert owner._cancel_write_completed and owner._write_fact_consumed
    assert work.done() and owner._work_joined and gate._done
    assert gate._eof and not gate._io_unknown
    assert not row[3]._reading
    assert remote._job_origin_snapshot.state is State.UNKNOWN
    assert remote._job_origin_snapshot.result is None
    assert gate._terminal_data is None  # torn RESULT/EOF is never a qualified terminal
    assert owner._socket_closed and owner._clock_closed
    assert not remote._job_origin_snapshot.credit_released
