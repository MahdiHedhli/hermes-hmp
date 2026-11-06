"""Original private-service/registry composition with synthetic peer/clock facts.

No production enrollment, phone authority, worker launch, provider or host data.
"""

import asyncio
import hashlib
import os
import time
from dataclasses import replace

import pytest

from hmp_plugin.presentation_broker_codec import encode_frame
from hmp_plugin.presentation_broker_registry import BrokerRegistry
from hmp_plugin.presentation_broker_service import BrokerServiceSpine, SocketChannel
from hmp_plugin.presentation_credential_begin import CredentialBeginReceiver
from hmp_plugin.presentation_credential_codec import encode_record, signing_bytes
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_scope import derive_input_scope
from hmp_plugin.presentation_jobs import FrameError

from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_credential_native_binding import key_pair


async def exchange(local, tmp_path, monkeypatch, mutation=None):
    spine, enrollment, connect, make_packet, _, _ = local
    darwin_model(monkeypatch)
    keys = key_pair(tmp_path, enrollment.installation_generation)
    cleanup_case = bool(mutation and mutation.startswith("signed_control_native_cleanup_"))
    end = time.monotonic_ns() + (400_000_000 if cleanup_case else 1_800_000_000)
    gateway = SocketChannel(
        connect(),
        replace(enrollment, gateway_pid=os.getpid(), service_pid=os.getpid() + 1),
        role="gateway",
        endpoint=spine._endpoint,
        observation=spine._observation,
    )
    held = {}
    ready_case = bool(mutation and mutation.startswith("signed_control_native_ready_"))
    write_case = bool(ready_case and "_ready_write_" in mutation)
    write_go_case = bool(write_case and mutation.endswith(("go_join", "early_go", "shadow_wait")))
    ready_event = asyncio.Event()
    control_retained_event = asyncio.Event()
    cleanup_cause_event = asyncio.Event()
    from hmp_plugin.presentation_credential_queued import CredentialQueuedOwner

    original_init = CredentialQueuedOwner.__init__

    def queued_init(work, service, record):
        if mutation == "queued_factory_channel":
            callbacks = []
            held["callbacks"] = callbacks
            held["original_channel"] = record.channel_snapshot

            class ForeignChannel:
                def __getattribute__(self, name):
                    callbacks.append(name)
                    raise AssertionError("foreign constructor channel getter")

            record.channel_snapshot = ForeignChannel()
        original_init(work, service, record)

    monkeypatch.setattr(CredentialQueuedOwner, "__init__", queued_init)
    original_reserve = BrokerRegistry.reserve
    reserve_calls = []

    def reserve(registry, *args):
        ticket = original_reserve(registry, *args)
        reserve_calls.append(ticket)
        if mutation == "after_reserve":
            keys["broker"].retire()
        return ticket

    monkeypatch.setattr(BrokerRegistry, "reserve", reserve)
    original_bind = BrokerRegistry.bind_input_receipt_once

    def bound(registry, ticket, packet):
        original_bind(registry, ticket, packet)
        if mutation == "after_bind":
            keys["broker"].retire()

    monkeypatch.setattr(BrokerRegistry, "bind_input_receipt_once", bound)

    async def broker():
        record = await BrokerServiceSpine._accept_owned(spine, end)
        held["record"] = record
        channel = SocketChannel(
            record.socket,
            enrollment,
            role="broker",
            endpoint=spine._endpoint,
            observation=spine._observation,
        )
        record.channel = record.channel_snapshot = channel
        owner = CredentialHandshakeOwner.retain(
            channel,
            keys["broker"],
            enrollment.scope,
            end - 100_000_000 if mutation in ("earlier_accept", "queued_after_admission") else end,
        )
        await owner.run()
        receiver = CredentialBeginReceiver.retain(owner)
        held["receiver"] = receiver
        await receiver.run()
        if mutation == "before_adopt":
            keys["broker"].retire()
        elif mutation == "registry":
            spine._registry = object()
        try:
            ticket = BrokerServiceSpine._adopt_credential_begin(spine, record)
            with pytest.raises(FrameError):
                BrokerServiceSpine._adopt_credential_begin(spine, record)
            assert record.ticket is ticket and record.credential_adoption_failed is False
            if mutation == "legacy_control":
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_result_transport import BrokerResultWriter, _native_io

                native = spine._registry_snapshot._record(ticket)
                original_budget = CancellationBudget.inspect(native.cleanup_budget)
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    BrokerCancellationOwner.retain(
                        channel, spine._registry_snapshot, ticket, record.grammar
                    )
                assert (
                    channel._cancel_receiver is None and channel._cancel_receiver_snapshot is None
                )
                assert CancellationBudget.inspect(native.cleanup_budget) == original_budget
                # Direct initialization is also rejected before capturing another
                # operation's failure custody or scheduling native Tasks/Futures.
                direct = BrokerCancellationOwner.__new__(BrokerCancellationOwner)
                grammar_before = dict(record.grammar.__dict__)
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.__init__(
                        direct, channel, spine._registry_snapshot, ticket, record.grammar
                    )
                assert record.grammar.__dict__ == grammar_before
                assert CancellationBudget.inspect(native.cleanup_budget) == original_budget
                assert direct._failure_origin_snapshot == (None, None)
                assert direct._allocation_snapshot is None and direct._slot_snapshot.task is None
                assert direct._go_future_snapshot is None and direct._cancel_future_snapshot is None
                assert (
                    channel._cancel_receiver is None and channel._cancel_receiver_snapshot is None
                )
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    BrokerResultWriter.retain(spine, record, receiver._result_snapshot.packet)
                assert record.result_writer is None and record.result_writer_snapshot is None
                assert channel._result_writer is None and channel._result_writer_snapshot is None
                with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
                    _native_io(channel)
                held["legacy_refused"] = True
            work = record.credential_work_snapshot
            assert work is record.credential_work
            held["work"] = work
            native = spine._registry_snapshot._record(ticket)
            if mutation and mutation.startswith("queued_"):
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_clock import NativeClockOwner

                if mutation == "queued_after_admission":
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: receiver._end + 1)
                elif mutation == "queued_key":
                    keys["broker"].retire()
                elif mutation == "queued_budget":
                    CancellationBudget.refuse(native.cleanup_budget)
                elif mutation == "queued_receipt":
                    native.input_receipt = object()
                elif mutation == "queued_grammar":
                    record.grammar._ready = True
                elif mutation == "queued_flags":
                    record.credential_adoption_failed = True
                elif mutation == "queued_deadline":
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: native.deadline_ns)
                elif mutation in (
                    "queued_final_key",
                    "queued_foreign_refs",
                    "queued_foreign_budget",
                    "queued_forged_receipt",
                    "queued_socket_receipt",
                ):
                    sample = NativeClockOwner.sample
                    socket_check = SocketChannel._check
                    callbacks = []
                    held["callbacks"] = callbacks

                    class Foreign:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign getter")

                        def __eq__(self, other):
                            callbacks.append("comparison")
                            raise AssertionError("foreign comparison")

                        def __iter__(self):
                            callbacks.append("iterate")
                            raise AssertionError("foreign reference iteration")

                        def __getitem__(self, index):
                            callbacks.append(index)
                            raise AssertionError("foreign reference indexing")

                    def changed(clock):
                        now = sample(clock)
                        if mutation == "queued_final_key":
                            keys["broker"].retire()
                        elif mutation == "queued_foreign_budget":
                            native.cleanup_budget = Foreign()
                        elif mutation in ("queued_forged_receipt", "queued_socket_receipt"):
                            forged = native.input_receipt_snapshot._replace(input_sha=Foreign())
                            native.input_receipt = native.input_receipt_snapshot = forged
                        else:
                            work._refs = Foreign()
                        return now

                    if mutation == "queued_socket_receipt":

                        def socket_changed(channel):
                            result = socket_check(channel)
                            forged = native.input_receipt_snapshot._replace(input_sha=Foreign())
                            native.input_receipt = native.input_receipt_snapshot = forged
                            return result

                        monkeypatch.setattr(SocketChannel, "_check", socket_changed)
                    else:
                        monkeypatch.setattr(NativeClockOwner, "sample", changed)
                elif mutation == "queued_wrong_task":

                    async def foreign_task():
                        return work.current_queued()

                    await asyncio.create_task(foreign_task())
            assert work.current_queued() is native
            if mutation and mutation.startswith("signed_control_native_"):
                from hmp_plugin.presentation_broker_cancel import (
                    _CANCEL_RECEIPT_MINT,
                    BrokerCancellationOwner,
                    _CancelReceipt,
                )
                from hmp_plugin.presentation_cancel_budget import CancellationBudget

                budget = native.cleanup_budget_snapshot
                before = CancellationBudget.inspect(budget)
                grammar_before = dict(record.grammar.__dict__)
                if ready_case:
                    import json
                    from io import FileIO

                    from hmp_plugin import presentation_credential_ready as ready_module
                    from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                    from hmp_plugin.presentation_broker_registry import BrokerRegistry
                    from hmp_plugin.presentation_credential_codec import decode_record
                    from hmp_plugin.presentation_credential_phase import _EXPECTED, check_commitment
                    from hmp_plugin.presentation_credential_ready import CredentialReadyProducer

                    control = BrokerCancellationOwner.stage_credential_go_control(work)
                    held["native_control"] = control
                    resources = process = child = None
                    try:
                        if not mutation.endswith("no_resources"):
                            BrokerRegistry.start_resources(spine._registry_snapshot, ticket)
                            resources = native.resources_snapshot
                            process = resources._process_snapshot
                            child = process._child_snapshot
                            if not mutation.endswith("no_input"):
                                BrokerRegistry.stage_resource_input(spine._registry_snapshot,
                                                                    ticket, work._refs_snapshot[8])
                        if mutation.endswith("no_fact"):
                            resources._control_snapshot._input_write_observation_origin = None
                        if mutation.endswith("wrong_fact"):
                            pipe = resources._control_snapshot
                            fact = pipe._input_write_observation_origin._replace(
                                packet_sha256="f" * 64)
                            pipe._input_write_observation = fact
                            pipe._input_write_observation_origin = fact
                        acquisition_failed = mutation.endswith(("no_resources", "no_input",
                                                               "no_fact", "wrong_fact"))
                        if acquisition_failed:
                            with pytest.raises(FrameError):
                                CredentialReadyProducer.retain(control)
                            held["ready_acquisition_refused"] = True
                            return ticket
                        if mutation.endswith("wrong_task"):
                            async def wrong_ready_actor():
                                with pytest.raises(FrameError):
                                    CredentialReadyProducer.retain(control)
                            await asyncio.create_task(wrong_ready_actor())
                            assert control._credential_ready is None
                        producer = CredentialReadyProducer.retain(control)
                        held["ready_producer"] = producer
                        with pytest.raises(FrameError):
                            CredentialReadyProducer.retain(control)
                        original_claim = json.loads(
                            receiver._result_snapshot.commitment.canonical_json)
                        callbacks = []
                        if mutation.endswith("forged_begin_claim"):
                            from dataclasses import replace
                            forged = dict(original_claim, input_sha256="f" * 64)
                            object.__setattr__(receiver._result_snapshot, "commitment", replace(
                                receiver._result_snapshot.commitment,
                                canonical_json=json.dumps(forged).encode()))
                        if mutation.endswith(("late_fd_close", "late_fd_replace", "foreign_phase")):
                            from hmp_plugin.presentation_clock import NativeClockOwner
                            sample = NativeClockOwner.sample
                            altered = []

                            class ForeignPhase:
                                def __eq__(self, other):
                                    callbacks.append("eq")
                                    raise AssertionError("foreign phase comparison")

                            def late_sample(clock):
                                now = sample(clock)
                                if not altered and asyncio.current_task() is record.task:
                                    altered.append(True)
                                    pipe = resources._control_snapshot
                                    if mutation.endswith("late_fd_close"):
                                        FileIO.close(pipe._stream_snapshot)
                                    elif mutation.endswith("late_fd_replace"):
                                        extra_read, extra_write = os.pipe()
                                        held["ready_extra_read"] = extra_read
                                        os.dup2(extra_write, pipe._identity_snapshot[0])
                                        os.close(extra_write)
                                    else:
                                        resources._phase = ForeignPhase()
                                return now

                            monkeypatch.setattr(NativeClockOwner, "sample", late_sample)
                        if mutation.endswith("retired"):
                            keys["broker"].retire()
                        elif mutation.endswith("post_crypto"):
                            encode = ready_module.encode_record

                            def retired_encode(*args, **options):
                                raw = encode(*args, **options)
                                keys["broker"].retire()
                                return raw

                            monkeypatch.setattr(ready_module, "encode_record", retired_encode)
                        if mutation.endswith(("retired", "post_crypto", "late_fd_close",
                                              "late_fd_replace", "foreign_phase")):
                            with pytest.raises(FrameError):
                                producer.prepare_ready()
                            assert producer._attempted is True and producer._record is None
                            assert callbacks == []
                            if mutation.endswith(("late_fd_close", "late_fd_replace")):
                                assert resources._control_snapshot._resource_uncertain is True
                            with pytest.raises(FrameError):
                                producer.prepare_ready()
                        else:
                            raw = producer.prepare_ready()
                            held["ready_record"] = raw
                            expected = {k: original_claim[k] for k in _EXPECTED}
                            expected.update(phase="READY", role="broker", direction="b2g",
                                            sequence=0)
                            checked = check_commitment(raw,
                                sender_public=keys["broker"]._selection.own_public,
                                receiver_public=keys["broker"]._selection.peer_public,
                                expected=expected)
                            assert checked.frame_length == len(encode_frame(
                                native.binding, "READY", 0, b"", version=2))
                            assert json.loads(decode_record(raw).canonical_json)["role"] == "broker"
                            with pytest.raises(FrameError):
                                producer.prepare_ready()
                            assert producer._record is raw
                        if write_case:
                            await exercise_ready_writer(producer, control, keys, monkeypatch,
                                                        held, mutation, ready_event)
                            if write_go_case:
                                ready_event.set()
                                async with asyncio.timeout_at(native.deadline_ns / 1e9):
                                    await asyncio.wait((control._cancel_future_snapshot,
                                                       control._allocation_snapshot.task),
                                                      return_when=asyncio.FIRST_COMPLETED)
                                    if not mutation.endswith("shadow_wait"):
                                        assert control._cancel_future_snapshot.done()
                                        consumed = await BrokerServiceSpine._v2_control(
                                            spine, control)
                                        assert consumed.header.kind == "CANCEL"
                                        BrokerCancellationOwner.abort(control)
                                    outcome = await asyncio.gather(
                                        control._allocation_snapshot.task, return_exceptions=True)
                                if mutation.endswith("shadow_wait"):
                                    assert isinstance(outcome[0], FrameError)
                                    assert control._go_receipt is None
                                    assert held["writer_foreign_calls"] == []
                                    del held["ready_writer"]._future_origin.add_done_callback
                                else:
                                    assert control._go_receipt is not None
                                    if isinstance(outcome[0], BaseException):
                                        raise outcome[0]
                                    assert outcome[0].header.kind == "CANCEL"
                                held["writer_go_join_checked"] = True
                        assert record.grammar._ready is (write_case and held["writer_ok"])
                        assert record.grammar._broker_next == (1 if record.grammar._ready else 0)
                        assert (control._go_receipt is None) is (not write_go_case
                                                               or mutation.endswith("shadow_wait"))
                        assert resources._go_attempted is False
                        assert resources._control_snapshot._go._attempted is False
                        return ticket
                    finally:
                        ready_event.set()
                        BrokerCancellationOwner.abort(control)
                        await asyncio.gather(control._allocation_snapshot.task,
                                             return_exceptions=True)
                        if child is not None:
                            # Exact disposable fixture ownership only: closing
                            # its native stdin ends the reader waiting for GO.
                            for stream in (child.stdin, child.stdout, child.stderr):
                                if (type(stream) is FileIO
                                        and not FileIO.closed.__get__(stream, FileIO)):
                                    FileIO.close(stream)
                            until = time.monotonic() + 3
                            while process._wait is None:
                                if process.poll_wait():
                                    break
                                assert time.monotonic() < until
                                await asyncio.sleep(0.005)
                            if resources._pipes_snapshot is not None:
                                selector = resources._pipes_snapshot._selector
                                if selector is not None:
                                    type(selector).close(selector)
                        if "ready_extra_read" in held:
                            os.close(held["ready_extra_read"])
                cleanup = mutation.startswith("signed_control_native_cleanup_")
                go_chain = (mutation.startswith("signed_control_native_go_chain_")
                            or (cleanup and ("after_go" in mutation
                                             or mutation.endswith("late_go"))))
                if go_chain:
                    control = BrokerCancellationOwner.stage_credential_go_control(work)
                    if mutation != "signed_control_native_go_chain_missing_ready":
                        from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader
                        # Explicit synthetic prior READY grammar fact only. No
                        # signed READY write/resource qualification is claimed.
                        record.grammar.observe(BrokerFrame(BrokerHeader(
                            record.grammar._binding, "READY", 0, 0, 2), b""), sender="broker")
                else:
                    control = BrokerCancellationOwner.retain_credential_cancel(work)
                held["native_control"] = control
                control_retained_event.set()
                inherit = CancellationBudget.inherit

                def inherited(budget, window, now):
                    held["native_local_end"] = CancellationBudget.inspect(budget)[2]
                    inherit(budget, window, now)
                    if mutation == "signed_control_native_retire":
                        keys["broker"].retire()

                monkeypatch.setattr(CancellationBudget, "inherit", inherited)
                if mutation in ("signed_control_native_phase_drift",
                                "signed_control_native_end_drift"):
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    complete = CredentialControlCursor.completed_current
                    current = BrokerServiceSpine._current
                    callbacks, ready, causes = [], [], []
                    cause = BrokerCancellationOwner._local_cause

                    class ForeignCursorValue:
                        def __eq__(self, other):
                            callbacks.append("eq")
                            raise AssertionError("foreign cursor comparison")

                        def __gt__(self, other):
                            callbacks.append("gt")
                            raise AssertionError("foreign cursor ordering")

                        def __lt__(self, other):
                            callbacks.append("lt")
                            raise AssertionError("foreign cursor ordering")

                    def completed(cursor):
                        result = complete(cursor)
                        ready.append(True)
                        return result

                    def changed(service):
                        current(service)
                        if ready and asyncio.current_task() is control._allocation_snapshot.task:
                            cursor = control._signed_cursor_snapshot
                            if mutation == "signed_control_native_phase_drift":
                                cursor._phase = ForeignCursorValue()
                            else:
                                cursor._end = cursor._end_snapshot = ForeignCursorValue()

                    def observed_cause(owner):
                        causes.append(True)
                        cause(owner)

                    monkeypatch.setattr(CredentialControlCursor, "completed_current", completed)
                    monkeypatch.setattr(BrokerServiceSpine, "_current", changed)
                    monkeypatch.setattr(BrokerCancellationOwner, "_local_cause", observed_cause)
                    held["native_foreign_callbacks"] = callbacks
                    held["native_local_causes"] = causes
                if mutation == "signed_control_native_notice_retire":
                    current = BrokerServiceSpine._current

                    def retired_notice(service):
                        current(service)
                        if control._notice_completed is True:
                            keys["broker"].retire()

                    monkeypatch.setattr(BrokerServiceSpine, "_current", retired_notice)
                waiter = control._cancel_future_snapshot
                if cleanup:
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    from hmp_plugin.presentation_readiness import SelectorReadiness
                    wait = SelectorReadiness.wait
                    waits = []
                    held["cleanup_waits"] = waits

                    async def observed_wait(waiter, cutoff, **options):
                        if asyncio.current_task() is control._allocation_snapshot.task:
                            cursor = control._signed_cursor_snapshot
                            waits.append((cutoff, cursor._consumed, cursor._target,
                                          id(cursor._buffer_origin)))
                        try:
                            return await wait(waiter, cutoff, **options)
                        except TimeoutError:
                            if mutation.endswith("unknown_readiness"):
                                waiter._unknown = True
                            raise

                    monkeypatch.setattr(SelectorReadiness, "wait", observed_wait)
                    if mutation.endswith("earlier_cause"):
                        BrokerCancellationOwner._local_cause(control)
                        held["cleanup_initial_end"] = CancellationBudget.inspect(budget)[2]
                        cleanup_cause_event.set()
                    if mutation.endswith(("sample_error", "guard_timeout")):
                        sample = NativeClockOwner.sample

                        def failed_sample(clock):
                            if asyncio.current_task() is control._allocation_snapshot.task:
                                cursor = control._signed_cursor_snapshot
                                if mutation.endswith("sample_error") or cursor._waiter is not None:
                                    if mutation.endswith("guard_timeout"):
                                        raise TimeoutError("synthetic guard failure, not expiry")
                                    raise RuntimeError("synthetic clock failure, not expiry")
                            return sample(clock)

                        monkeypatch.setattr(NativeClockOwner, "sample", failed_sample)
                    rejected = mutation.endswith(("expired_tail", "retired_tail", "late_go",
                                                   "bad_signature", "unknown_readiness",
                                                   "sample_error", "guard_timeout"))
                    if rejected:
                        with pytest.raises(FrameError):
                            await BrokerServiceSpine._v2_control(spine, control)
                        assert not waiter.done() and control._cancel_receipt is None
                        assert record.grammar._cancel is False
                        assert native.start_attempted is False and native.resources is None
                        if mutation.endswith(("sample_error", "guard_timeout")):
                            assert CancellationBudget.inspect(budget)[2] is None
                            assert waits == []
                        if mutation.endswith("unknown_readiness"):
                            assert len(waits) == 1
                        BrokerCancellationOwner.abort(control)
                        await asyncio.gather(control._allocation_snapshot.task,
                                             return_exceptions=True)
                    else:
                        consumed = await BrokerServiceSpine._v2_control(spine, control)
                        notice = waiter.result()
                        assert consumed is notice.frame and control._retired is True
                        assert notice.end <= end + 250_000_000
                        if mutation.endswith("earlier_cause"):
                            assert notice.end == held["cleanup_initial_end"]
                        else:
                            assert notice.end == end + 250_000_000
                            assert any(row[0] == end for row in waits)
                            assert any(row[0] == end + 250_000_000 for row in waits)
                            work_wait = next(row for row in waits if row[0] == end)
                            cleanup_wait = next(row for row in waits
                                                if row[0] == end + 250_000_000)
                            assert work_wait[1:] == cleanup_wait[1:]  # same offset/target/buffer
                        assert native.deadline_ns == end  # signed work end is never rewritten
                        assert native.start_attempted is False and native.resources is None
                        BrokerCancellationOwner.abort(control)
                        outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                       return_exceptions=True)
                        assert outcome == [consumed] and control._stop_known is True
                    held["cleanup_checked"] = True
                    return ticket
                if go_chain:
                    if mutation.endswith(("index_drift", "expired", "retired")):
                        from hmp_plugin.presentation_clock import NativeClockOwner
                        sample = NativeClockOwner.sample
                        callbacks = []

                        class ForeignFrameIndex:
                            def __eq__(self, other):
                                callbacks.append("eq")
                                raise AssertionError("foreign frame index comparison")
                            def __add__(self, other):
                                callbacks.append("add")
                                raise AssertionError("foreign frame index arithmetic")
                            def __index__(self):
                                callbacks.append("index")
                                raise AssertionError("foreign frame indexing")

                        def changed_go(clock):
                            now = sample(clock)
                            phase = control._signed_go_snapshot
                            cursor = control._signed_cursor_snapshot
                            if mutation.endswith("index_drift") and cursor._complete:
                                cursor._frame_index = ForeignFrameIndex()
                            elif phase._notified:
                                if mutation.endswith("expired"):
                                    return end
                                if mutation.endswith("retired"):
                                    keys["broker"].retire()
                            return now

                        monkeypatch.setattr(NativeClockOwner, "sample", changed_go)
                        if mutation.endswith("expired"):
                            monkeypatch.setattr(NativeClockOwner, "cleanup_sample", lambda _: end)
                        held["go_transition_callbacks"] = callbacks
                    expected = mutation in ("signed_control_native_go_chain_cancel",
                                            "signed_control_native_go_chain_before_go")
                    if expected:
                        consumed = await BrokerServiceSpine._v2_control(spine, control)
                        assert consumed.header.kind == "CANCEL"
                        assert (consumed.header.sequence
                                == (1 if mutation.endswith("before_go") else 2))
                        if mutation.endswith("cancel"):
                            go = control._go_future_snapshot.result()
                            assert go is control._go_receipt_snapshot
                            assert go.frame.header.kind == "GO"
                            assert control._signed_cursor_snapshot._wire_before > 0
                        with pytest.raises(FrameError, match="SIGNED_CONTROL_READER_NOT_IMPLEMENTED"
                                           ):
                            BrokerServiceSpine._v2_work_current(spine, control)
                        assert native.resources is None and native.start_attempted is False
                        BrokerCancellationOwner.abort(control)
                        outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                       return_exceptions=True)
                        assert outcome == [consumed] and control._stop_known is True
                    else:
                        outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                       return_exceptions=True)
                        assert isinstance(outcome[0], FrameError) and not waiter.done()
                        if mutation.endswith(("missing_ready", "index_drift")):
                            assert control._go_receipt is None
                            assert CancellationBudget.inspect(budget) == before
                        else:
                            assert control._go_future_snapshot.done()
                            assert control._retired is True
                            assert CancellationBudget.inspect(budget)[2] is not None
                        assert native.start_attempted is False and native.resources is None
                        if "go_transition_callbacks" in held:
                            assert held["go_transition_callbacks"] == []
                            assert control._signed_cursor_snapshot._wire_before == (
                                0 if mutation.endswith("index_drift")
                                else held["signed_auth_length"]
                                + len(encode_frame(control._go_receipt.frame.header.binding,
                                                   "GO", 1, b"", version=2)))
                    return ticket
                if mutation.startswith("signed_control_native_service_"):
                    from hmp_plugin.presentation_credential_control import CredentialCancelAdoption
                    adoption = control._signed_cancel_snapshot
                    if mutation == "signed_control_native_service_initial_drift":
                        current = BrokerServiceSpine._current
                        calls = []

                        def initial_drift(service):
                            current(service)
                            if (adoption._consume_attempted
                                    and asyncio.current_task() is record.task):
                                calls.append(True)
                                service._refused = True

                        monkeypatch.setattr(BrokerServiceSpine, "_current", initial_drift)
                        with pytest.raises(FrameError):
                            await CredentialCancelAdoption.wait_notice(adoption, spine)
                        assert adoption._consume_attempted is True
                        assert adoption._consume_failed is True and not waiter.done()
                        assert adoption._attempted is False and control._cancel_receipt is None
                        # White-box restoration tests the consumed-attempt fence;
                        # production does not restore retired/refused state.
                        spine._refused = False
                        control._failed = control._retired = False
                        count = len(calls)
                        with pytest.raises(FrameError):
                            await CredentialCancelAdoption.wait_notice(adoption, spine)
                        assert len(calls) == count
                        monkeypatch.setattr(BrokerServiceSpine, "_current", current)
                        BrokerCancellationOwner.abort(control)
                        await asyncio.gather(control._allocation_snapshot.task,
                                             return_exceptions=True)
                        return ticket
                    if mutation == "signed_control_native_service_final_future_drift":
                        guard = BrokerCancellationOwner._guard
                        qualified = SocketChannel._qualified_clock
                        active, callbacks = [], []

                        class ForeignFinalFuture:
                            def __getattribute__(self, name):
                                callbacks.append(name)
                                raise AssertionError("foreign final future getter")

                        def guarded(owner, **options):
                            active.append(True)
                            try:
                                return guard(owner, **options)
                            finally:
                                active.pop()

                        def changed_clock(channel):
                            clock = qualified(channel)
                            if (active and adoption._consume_attempted is True
                                    and asyncio.current_task() is record.task):
                                control._cancel_future = control._cancel_future_snapshot = (
                                    ForeignFinalFuture())
                            return clock

                        monkeypatch.setattr(BrokerCancellationOwner, "_guard", guarded)
                        monkeypatch.setattr(SocketChannel, "_qualified_clock", changed_clock)
                        with pytest.raises(FrameError):
                            await CredentialCancelAdoption.wait_notice(adoption, spine)
                        assert callbacks == [] and not waiter.done()
                        assert adoption._consume_attempted is True
                        assert adoption._consume_failed is True
                        BrokerCancellationOwner.abort(control)
                        await asyncio.gather(control._allocation_snapshot.task,
                                             return_exceptions=True)
                        return ticket
                    if mutation == "signed_control_native_service_wrong_task":
                        async def foreign_consumer():
                            with pytest.raises(FrameError):
                                await CredentialCancelAdoption.wait_notice(adoption, spine)
                        await asyncio.create_task(foreign_consumer())
                        assert adoption._consume_attempted is False
                    if mutation == "signed_control_native_service_wrong_spine":
                        foreign_spine = BrokerServiceSpine.__new__(BrokerServiceSpine)
                        with pytest.raises(FrameError):
                            await CredentialCancelAdoption.wait_notice(adoption, foreign_spine)
                        assert adoption._consume_attempted is False
                    if mutation in ("signed_control_native_service_retired",
                                    "signed_control_native_service_foreign_future"):
                        current = BrokerServiceSpine._current
                        callbacks = []

                        class ForeignFuture:
                            def __getattribute__(self, name):
                                callbacks.append(name)
                                raise AssertionError("foreign future getter")

                        def changed_consumer(service):
                            current(service)
                            if (adoption._consume_attempted is True
                                    and control._notice_completed is True
                                    and asyncio.current_task() is record.task):
                                if mutation == "signed_control_native_service_retired":
                                    keys["broker"].retire()
                                else:
                                    control._cancel_future = control._cancel_future_snapshot = (
                                        ForeignFuture())

                        monkeypatch.setattr(BrokerServiceSpine, "_current", changed_consumer)
                        with pytest.raises(FrameError):
                            await BrokerServiceSpine._v2_control(spine, control)
                        assert adoption._consume_complete is False
                        assert adoption._consume_failed is True and callbacks == []
                        assert waiter.done()  # historical notification is not usable authority
                        BrokerCancellationOwner.abort(control)
                        await asyncio.gather(control._allocation_snapshot.task,
                                             return_exceptions=True)
                        return ticket
                    consumed = await BrokerServiceSpine._v2_control(spine, control)
                    assert consumed is control._cancel_receipt_snapshot.frame
                    assert adoption._consume_complete is True
                    with pytest.raises(FrameError):
                        await CredentialCancelAdoption.wait_notice(adoption, spine)
                    assert control._go_receipt is None and native.start_attempted is False
                    BrokerCancellationOwner.abort(control)
                    outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                   return_exceptions=True)
                    assert outcome == [consumed] and control._stop_known is True
                    held["consumed_native_notice"] = consumed
                    return ticket
                done, _ = await asyncio.wait(
                    (waiter, control._allocation_snapshot.task), timeout=0.5,
                    return_when=asyncio.FIRST_COMPLETED)
                assert done
                success = mutation in ("signed_control_native_cancel",
                                       "signed_control_native_retire_parked")
                if success:
                    notice = waiter.result()
                    assert type(notice) is _CancelReceipt and notice.mint is _CANCEL_RECEIPT_MINT
                    assert notice is control._cancel_receipt_snapshot
                    assert notice.allocation is control._allocation_snapshot
                    assert control._go_receipt is None and native.start_attempted is False
                    assert record.grammar._cancel is True and record.grammar._go is False
                    assert record.grammar._client_next == 2
                    assert notice.end == min(notice.window.end_ns, held["native_local_end"])
                    assert CancellationBudget.inspect(budget)[2] == notice.end
                    if mutation == "signed_control_native_retire_parked":
                        keys["broker"].retire()
                    BrokerCancellationOwner.abort(control)
                    outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                   return_exceptions=True)
                    assert outcome == [notice.frame]
                    assert control._stop_known is True and control._failed is False
                    held["native_notice"] = notice
                else:
                    outcome = await asyncio.gather(control._allocation_snapshot.task,
                                                   return_exceptions=True)
                    assert isinstance(outcome[0], FrameError)
                    if mutation == "signed_control_native_notice_retire":
                        assert waiter.done() and control._notice_completed is True
                        assert control._failed is True and control._io_unknown is True
                    else:
                        assert not waiter.done() and control._cancel_receipt is None
                    if mutation not in ("signed_control_native_retire",
                                         "signed_control_native_notice_retire"):
                        assert CancellationBudget.inspect(budget) == before
                        assert record.grammar.__dict__ == grammar_before
                    if mutation in ("signed_control_native_phase_drift",
                                    "signed_control_native_end_drift"):
                        assert held["native_foreign_callbacks"] == []
                        assert held["native_local_causes"] == []
                return ticket
            if mutation and mutation.startswith("signed_control_"):
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget

                budget_before = CancellationBudget.inspect(native.cleanup_budget_snapshot)
                grammar_before = dict(record.grammar.__dict__)
                if mutation in ("signed_control_init_refs", "signed_control_final_refs"):
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    completed = CredentialBeginReceiver._completed_current
                    retain = CredentialControlCursor.retain
                    callbacks = []
                    calls = []
                    active = []

                    class ForeignRefs:
                        def __getitem__(self, index):
                            callbacks.append(index)
                            raise AssertionError("foreign refs indexing")

                        def __iter__(self):
                            callbacks.append("iterate")
                            raise AssertionError("foreign refs iteration")

                    def changed_completed(receiver):
                        result = completed(receiver)
                        if active:
                            calls.append(True)
                            wanted = 1 if mutation == "signed_control_init_refs" else 2
                            if len(calls) == wanted:
                                record.cancel_owner._credential_binding_snapshot._refs_snapshot = (
                                    ForeignRefs())
                        return result

                    def retained(cls, control):
                        active.append(True)
                        return retain(control)

                    monkeypatch.setattr(CredentialBeginReceiver, "_completed_current",
                                        changed_completed)
                    monkeypatch.setattr(CredentialControlCursor, "retain", classmethod(retained))
                    with pytest.raises(FrameError, match="CONTROL_ACQUISITION_REFUSED"):
                        BrokerCancellationOwner.stage_credential_control(work)
                    control = record.cancel_owner
                    assert control._failed is True and callbacks == []
                    await asyncio.gather(control._allocation_snapshot.task, return_exceptions=True)
                    assert control._go_receipt is None and control._cancel_receipt is None
                    assert (CancellationBudget.inspect(native.cleanup_budget_snapshot)
                            == budget_before)
                    assert record.grammar.__dict__ == grammar_before
                    held["signed_cursor"] = control._signed_cursor_snapshot
                    return ticket
                control = BrokerCancellationOwner.stage_credential_control(work)
                held["staged_control"] = control
                cursor = control._signed_cursor_snapshot
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.stage_credential_control(work)
                if mutation == "signed_control_key":
                    keys["broker"].retire()
                elif mutation == "signed_control_deadline":
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    monkeypatch.setattr(NativeClockOwner, "sample", lambda _: end)
                elif mutation in ("signed_control_retire_after_read", "signed_control_counter"):
                    from hmp_plugin import presentation_broker_cancel as cancel_module
                    recv = cancel_module._SOCKET_RECV

                    def retired_recv(sock, wanted):
                        part = recv(sock, wanted)
                        if mutation == "signed_control_counter":
                            cursor._consumed = cursor._consumed_snapshot = 1
                        else:
                            keys["broker"].retire()
                        return part

                    monkeypatch.setattr(cancel_module, "_SOCKET_RECV", retired_recv)
                elif mutation == "signed_control_buffer":
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    sample = NativeClockOwner.sample
                    held["signed_original_buffer"] = cursor._buffer_origin
                    replacement = bytearray(b"preserve")

                    def buffer_changed(clock):
                        now = sample(clock)
                        if cursor._last_read is not None and cursor._read_intent:
                            cursor._buffer = cursor._buffer_origin = replacement
                            cursor._buffer_values = bytes(replacement)
                            cursor._consumed = cursor._consumed_snapshot = len(replacement) + 8
                            cursor._target = cursor._target_snapshot = len(replacement) + 8
                        return now

                    monkeypatch.setattr(NativeClockOwner, "sample", buffer_changed)
                elif mutation in ("signed_control_blocking", "signed_control_timeout"):
                    from hmp_plugin import presentation_broker_cancel as cancel_module
                    check = SocketChannel._check
                    checked, received = [], []

                    def changed_socket(checked_channel):
                        check(checked_channel)
                        if asyncio.current_task() is control._allocation_snapshot.task:
                            checked.append(True)
                            if len(checked) == 2:
                                if mutation == "signed_control_blocking":
                                    os.set_blocking(checked_channel._fd, True)
                                else:
                                    checked_channel._socket_snapshot.settimeout(0.01)

                    def forbidden_recv(sock, wanted):
                        received.append(True)
                        raise AssertionError("blocking recv must be refused before syscall")

                    monkeypatch.setattr(SocketChannel, "_check", changed_socket)
                    monkeypatch.setattr(cancel_module, "_SOCKET_RECV", forbidden_recv)
                    held["signed_forbidden_recv"] = received
                elif mutation == "signed_control_wrong_task":
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    with pytest.raises(FrameError):
                        CredentialControlCursor._guard(cursor)
                outcome = await asyncio.gather(control._allocation_snapshot.task,
                                               return_exceptions=True)
                assert len(outcome) == 1 and isinstance(outcome[0], FrameError)
                if mutation in ("signed_control_blocking", "signed_control_timeout"):
                    assert held["signed_forbidden_recv"] == [] and cursor._consumed == 0
                    channel._socket_snapshot.setblocking(False)
                assert control._go_receipt is None and control._cancel_receipt is None
                assert CancellationBudget.inspect(native.cleanup_budget_snapshot) == budget_before
                assert record.grammar.__dict__ == grammar_before
                success = mutation in ("signed_control_go", "signed_control_cancel",
                                       "signed_control_fragmented", "signed_control_wrong_task")
                assert cursor._complete is success and cursor._failed is not success
                if success:
                    assert str(outcome[0]) == "BI1_SIGNED_CONTROL_RECEIPT_INTEGRATION_REQUIRED"
                    assert cursor._consumed == len(cursor._raw) + len(cursor._frame)
                    assert channel._reading is False
                else:
                    assert cursor._raw is None
                    if mutation == "signed_control_buffer":
                        assert cursor._buffer_origin == b"preserve"
                        assert held["signed_original_buffer"] == b""
                    else:
                        assert cursor._buffer_origin == b""
                    if mutation == "signed_control_counter":
                        assert cursor._last_read == (0, 8)
                    if mutation in ("signed_control_signature", "signed_control_scope",
                                    "signed_control_sequence", "signed_control_boot"):
                        assert cursor._consumed == held["signed_auth_length"]
                    if mutation in ("signed_control_key", "signed_control_deadline"):
                        assert cursor._consumed == 0
                    if mutation == "signed_control_retire_after_read":
                        assert cursor._consumed == 8
                held["signed_cursor"] = cursor
            if mutation in (
                "control_binding",
                "control_binding_creator_drift",
                "control_binding_reader_drift",
                "control_binding_material_key",
                "control_binding_material_control",
                "control_binding_material_budget",
            ):
                from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_control_binding import PreparedControlBinding

                original_budget = native.cleanup_budget_snapshot
                budget_before = CancellationBudget.inspect(original_budget)
                grammar_before = dict(record.grammar.__dict__)
                material = PreparedControlBinding.reader_material_current
                held["material_passed"] = False

                def observed_material(binding):
                    assert asyncio.current_task() is binding._allocation.task
                    assert asyncio.current_task() is not binding._creator
                    with pytest.raises(FrameError):
                        PreparedControlBinding.creator_current(binding)
                    with pytest.raises(FrameError):
                        PreparedControlBinding.creator_material_current(binding)
                    material(binding)
                    held["material_passed"] = True

                monkeypatch.setattr(
                    PreparedControlBinding, "reader_material_current", observed_material
                )
                control = BrokerCancellationOwner.prepare_credential(work)
                held["prepared_control"] = control
                prepared = control._credential_binding_snapshot
                assert (
                    prepared._bound is True and prepared._allocation is control._allocation_snapshot
                )
                assert prepared._creator is asyncio.current_task()
                assert prepared._allocation.task is not asyncio.current_task()
                assert prepared._allocation.task.get_coro() is control._slot_snapshot.coroutine
                with pytest.raises(FrameError, match="SIGNED_CONTROL_READER_NOT_IMPLEMENTED"):
                    BrokerCancellationOwner._guard(control)
                with pytest.raises(FrameError, match="SIGNED_CONTROL_READER_NOT_IMPLEMENTED"):
                    BrokerServiceSpine._v2_work_current(spine, control)
                with pytest.raises(FrameError):
                    BrokerCancellationOwner.prepare_credential(work)
                original_task = control._allocation_snapshot.task
                if mutation in ("control_binding_creator_drift", "control_binding_reader_drift"):
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    from hmp_plugin.presentation_control_binding import PreparedControlBinding

                    callbacks = []
                    held["binding_callbacks"] = callbacks

                    class Foreign:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign control getter")

                    if mutation == "control_binding_creator_drift":
                        sample = NativeClockOwner.sample

                        def changed(clock):
                            now = sample(clock)
                            prepared._control_snapshot = Foreign()
                            return now

                        monkeypatch.setattr(NativeClockOwner, "sample", changed)
                        with pytest.raises(FrameError):
                            PreparedControlBinding.creator_current(prepared)
                    else:
                        prepared._allocation = Foreign()
                if mutation == "control_binding_material_key":
                    keys["broker"].retire()
                elif mutation in (
                    "control_binding_material_control",
                    "control_binding_material_budget",
                ):
                    current = BrokerServiceSpine._current
                    callbacks = []
                    held["binding_callbacks"] = callbacks

                    class ForeignMaterial:
                        def __getattribute__(self, name):
                            callbacks.append(name)
                            raise AssertionError("foreign reader material getter")

                    def material_changed(service):
                        current(service)
                        if asyncio.current_task() is original_task:
                            if mutation == "control_binding_material_control":
                                prepared._control_snapshot = ForeignMaterial()
                            else:
                                native.cleanup_budget = ForeignMaterial()

                    monkeypatch.setattr(BrokerServiceSpine, "_current", material_changed)
                outcome = await asyncio.gather(original_task, return_exceptions=True)
                assert len(outcome) == 1 and isinstance(outcome[0], FrameError)
                assert control._failed is True and control._wire_received == 0
                assert control._go_receipt is None and control._cancel_receipt is None
                assert channel._reading is False and control._buffer_origin == b""
                assert CancellationBudget.inspect(original_budget) == budget_before
                assert record.grammar.__dict__ == grammar_before
            return ticket
        except FrameError:
            with pytest.raises(FrameError):
                BrokerServiceSpine._adopt_credential_begin(spine, record)
            raise

    task = asyncio.create_task(broker())
    owner = CredentialHandshakeOwner.retain(gateway, keys["gateway"], enrollment.scope, end)
    try:
        await owner.run()
        binding = owner._operation_binding()
        packet = make_packet(binding, end)
        scope = derive_input_scope(packet, binding)
        frame = encode_frame(binding, "BEGIN", 0, packet, version=2)
        transcript = owner._transcript_snapshot
        value = dict(owner._common)
        value.pop("clock_domain")
        value.update(
            v=1,
            family="phase",
            alg="Ed25519",
            phase="BEGIN",
            role="gateway",
            direction="g2b",
            key_id=hashlib.sha256(keys["gateway"]._selection.own_public).hexdigest(),
            peer_key_id=hashlib.sha256(keys["gateway"]._selection.peer_public).hexdigest(),
            gateway_boot=transcript.gateway_boot,
            broker_boot=transcript.broker_boot,
            channel=transcript.channel,
            transcript_sha256=transcript.transcript_sha256,
            sequence=0,
            input_sha256=scope.input_sha256,
            scope_sha256=scope.scope_sha256,
            frame_sha256=hashlib.sha256(frame).hexdigest(),
            frame_length=len(frame),
        )
        raw = encode_record(value, keys["gateway"]._private_key.sign(signing_bytes(value)))
        await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, raw + frame)
        if mutation and mutation.startswith("signed_control_"):
            from hmp_plugin.presentation_cancel_budget import CancellationWindow

            async def send_cleanup_wire(wire_bytes, auth_length):
                if mutation.endswith("late_go"):
                    split = 0
                elif mutation.endswith(("header", "earlier_cause")):
                    split = auth_length + 9
                elif mutation.endswith("body"):
                    split = len(wire_bytes) - 8
                else:
                    split = 8
                if mutation.endswith("sample_error"):
                    split = len(wire_bytes)
                if split:
                    await asyncio.get_running_loop().sock_sendall(
                        gateway._socket_snapshot, wire_bytes[:split])
                if split < len(wire_bytes):
                    if mutation.endswith("earlier_cause"):
                        await asyncio.sleep(0.1)
                    else:
                        offset = 0.30 if mutation.endswith("expired_tail") else 0.015
                        await asyncio.sleep(max(0, (end - time.monotonic_ns()) / 1e9) + offset)
                    if mutation.endswith("retired_tail"):
                        keys["broker"].retire()
                    await asyncio.get_running_loop().sock_sendall(
                        gateway._socket_snapshot, wire_bytes[split:])

            if cleanup_case and mutation.endswith("earlier_cause"):
                # Establish the actual local cause before encoding a later
                # remote window; scheduler speed cannot reverse this causal.
                async with asyncio.timeout_at(end / 1e9):
                    await cleanup_cause_event.wait()
            phase = "CANCEL" if mutation in ("signed_control_cancel", "signed_control_hash",
                                             "signed_control_window") else "GO"
            if mutation.startswith("signed_control_native_"):
                phase = "GO" if (mutation == "signed_control_native_go"
                    or write_go_case
                    or (cleanup_case and ("after_go" in mutation or mutation.endswith("late_go")))
                    or (mutation.startswith("signed_control_native_go_chain_")
                    and not mutation.endswith("before_go"))) else "CANCEL"
            body = CancellationWindow(end - 250_000_000, end).encode() if phase == "CANCEL" else b""
            if mutation.startswith("signed_control_native_") and phase == "CANCEL":
                start = time.monotonic_ns()
                if mutation == "signed_control_native_future_window":
                    start += 1_000_000_000
                body = CancellationWindow(start, start + 250_000_000).encode()
                if cleanup_case:
                    start = (held["cleanup_initial_end"] - 250_000_000 + 50_000_000
                             if mutation.endswith("earlier_cause") else end)
                    body = CancellationWindow(start, start + 250_000_000).encode()
            if mutation == "signed_control_window":
                body = b"\0" * 16
            control_frame = encode_frame(binding, phase, 1, body, version=2)
            control_value = dict(value, phase=phase, sequence=1,
                                 frame_sha256=hashlib.sha256(control_frame).hexdigest(),
                                 frame_length=len(control_frame))
            if mutation == "signed_control_scope":
                control_value["scope_sha256"] = "f" * 64
            if mutation == "signed_control_sequence":
                control_value["sequence"] = 2
            if mutation == "signed_control_boot":
                control_value["broker_boot"] = "f" * len(control_value["broker_boot"])
            control_raw = encode_record(control_value, keys["gateway"]._private_key.sign(
                signing_bytes(control_value)))
            if (mutation in ("signed_control_signature", "signed_control_native_signature")
                    or (cleanup_case and mutation.endswith("bad_signature"))):
                control_raw = control_raw[:-1] + bytes([control_raw[-1] ^ 1])
            if mutation == "signed_control_hash":
                control_frame = control_frame[:-1] + bytes([control_frame[-1] ^ 1])
            held["signed_auth_length"] = len(control_raw)
            wire = control_raw + control_frame
            if ready_case:
                await asyncio.wait_for(ready_event.wait(), timeout=5)
                if write_go_case and mutation.endswith("early_go"):
                    await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, wire)
                    async with asyncio.timeout_at(end / 1e9):
                        await held["writer_join_entered"].wait()
                    assert held["native_control"]._go_receipt is None
                    assert held["ready_writer"]._complete is False
                    assert held["record"].grammar._ready is False
                    held["writer_resume"].set()
                if write_case:
                    if mutation.endswith("kernel_wait"):
                        padding = bytearray()
                        while len(padding) < held["writer_padding"]:
                            async with asyncio.timeout_at(end / 1e9):
                                padding.extend(await asyncio.get_running_loop().sock_recv(
                                    gateway._socket_snapshot,
                                    held["writer_padding"] - len(padding)))
                        assert bytes(padding) == b"S" * held["writer_padding"]
                    count = (len(held["writer_wire"]) if write_go_case
                             or mutation.endswith("kernel_wait")
                             else held.get("writer_actual_bytes", 0))
                    observed = bytearray()
                    while len(observed) < count:
                        async with asyncio.timeout_at(end / 1e9):
                            observed.extend(await asyncio.get_running_loop().sock_recv(
                                gateway._socket_snapshot, count - len(observed)))
                    assert bytes(observed) == held["writer_wire"][:count]
                    held["writer_wire_observed"] = bytes(observed)
                if not (write_go_case and mutation.endswith("early_go")):
                    await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, wire)
                if write_go_case and not mutation.endswith("shadow_wait"):
                    control = held["native_control"]
                    async with asyncio.timeout_at(end / 1e9):
                        await asyncio.wait((control._go_future_snapshot,
                                           control._allocation_snapshot.task),
                                          return_when=asyncio.FIRST_COMPLETED)
                    assert control._go_future_snapshot.done()
                    start = time.monotonic_ns()
                    window = CancellationWindow(start, start + 250_000_000).encode()
                    next_frame = encode_frame(binding, "CANCEL", 2, window, version=2)
                    next_value = dict(value, phase="CANCEL", sequence=2,
                                      frame_sha256=hashlib.sha256(next_frame).hexdigest(),
                                      frame_length=len(next_frame))
                    next_raw = encode_record(next_value, keys["gateway"]._private_key.sign(
                        signing_bytes(next_value)))
                    await asyncio.get_running_loop().sock_sendall(
                        gateway._socket_snapshot, next_raw + next_frame)
            elif cleanup_case and "after_go" not in mutation:
                await send_cleanup_wire(wire, len(control_raw))
            elif cleanup_case:
                await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, wire)
                window2 = CancellationWindow(end, end + 250_000_000).encode()
                frame2 = encode_frame(binding, "CANCEL", 2, window2, version=2)
                value2 = dict(value, phase="CANCEL", sequence=2,
                              frame_sha256=hashlib.sha256(frame2).hexdigest(),
                              frame_length=len(frame2))
                raw2 = encode_record(value2, keys["gateway"]._private_key.sign(
                    signing_bytes(value2)))
                await send_cleanup_wire(raw2 + frame2, len(raw2))
            elif mutation == "signed_control_fragmented":
                for part in (wire[:4], wire[4:8], wire[8:-1], wire[-1:]):
                    await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, part)
                    await asyncio.sleep(0)
            else:
                await asyncio.get_running_loop().sock_sendall(gateway._socket_snapshot, wire)
            if (mutation.startswith("signed_control_native_go_chain_")
                    and not mutation.endswith("before_go")):
                if not mutation.endswith(("missing_ready", "index_drift")):
                    # Internal fixture coordination observes an actual GO-read
                    # notification, NOT a production execution acknowledgement.
                    # Cancellation starts here, after BEGIN/GO fixture setup.
                    async with asyncio.timeout_at(end / 1e9):
                        await control_retained_event.wait()
                        native_control = held["native_control"]
                        go_future = native_control._go_future_snapshot
                        await asyncio.wait((go_future, native_control._allocation_snapshot.task),
                                           return_when=asyncio.FIRST_COMPLETED)
                        assert go_future.done()
                start = time.monotonic_ns()
                body2 = CancellationWindow(start, start + 250_000_000).encode()
                frame2 = encode_frame(binding, "CANCEL", 2, body2, version=2)
                value2 = dict(value, phase="CANCEL", sequence=2,
                              frame_sha256=hashlib.sha256(frame2).hexdigest(),
                              frame_length=len(frame2))
                if mutation.endswith("wrong_sequence"):
                    value2["sequence"] = 1
                raw2 = encode_record(value2, keys["gateway"]._private_key.sign(
                    signing_bytes(value2)))
                if mutation.endswith("bad_signature"):
                    raw2 = raw2[:-1] + bytes([raw2[-1] ^ 1])
                await asyncio.get_running_loop().sock_sendall(
                    gateway._socket_snapshot, raw2 + frame2)
        if (mutation and mutation.startswith("signed_control_")) or mutation in (
            None,
            "earlier_accept",
            "queued_after_admission",
            "legacy_control",
            "control_binding",
            "control_binding_creator_drift",
            "control_binding_reader_drift",
            "control_binding_material_key",
            "control_binding_material_control",
            "control_binding_material_budget",
        ):
            held["ticket"] = await task
        else:
            with pytest.raises(FrameError):
                await task
        return held, reserve_calls
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        if "record" in held:
            # Fixture closes its own local descriptors only, not registry debt.
            channel = held.get("original_channel", held["record"].channel_snapshot)
            channel.close()
            channel.close_clock()
        gateway.close()
        gateway.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_original_service_adopts_exact_input_once_without_worker(
    local, tmp_path, monkeypatch
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch)
    record, receiver, ticket = held["record"], held["receiver"], held["ticket"]
    assert calls == [ticket] and record.ticket is ticket
    assert record.credential_adoption_attempted is True
    assert record.credential_adoption_complete is True
    native = spine._registry_snapshot._record(ticket)
    assert (
        native.input_bind_attempted is True
        and native.input_receipt is native.input_receipt_snapshot
    )
    assert native.input_receipt.input_sha == hashlib.sha256(receiver._result.packet).hexdigest()
    assert native.start_attempted is False and native.resources is None and native.managed is False
    assert spine._registry_snapshot.counts.waiting == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", ["before_adopt", "after_reserve", "after_bind", "registry"])
async def test_adoption_failure_consumes_attempt_and_retains_any_original_ticket(
    local, tmp_path, monkeypatch, mutation
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    record = held["record"]
    assert record.credential_adoption_attempted is True
    assert (
        record.credential_adoption_complete is False and record.credential_adoption_failed is True
    )
    if mutation in ("after_reserve", "after_bind"):
        assert calls == [record.ticket] and record.ticket is not None
        native = spine._registry_snapshot._record(record.ticket)
        if mutation == "after_bind":
            assert native.input_bind_attempted is True and native.input_receipt is not None
        else:
            assert native.input_bind_attempted is False and native.input_receipt is None
        assert native.resources is None and native.start_attempted is False
        assert spine._registry_snapshot.counts.waiting == 1
        # A retained ticket/receipt is not credential resource or GO permission.
        with pytest.raises(FrameError, match="PHASE_INTEGRATION_REQUIRED"):
            SocketChannel._credential_work_ready(record.channel_snapshot)
    else:
        assert calls == [] and record.ticket is None
        assert spine._registry_snapshot.counts.waiting == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_adoption_finishes_under_earlier_local_cap_without_renewing_work_end(
    local, tmp_path, monkeypatch
):
    spine = local[0]
    held, calls = await exchange(local, tmp_path, monkeypatch, "earlier_accept")
    receiver, ticket = held["receiver"], held["ticket"]
    native = spine._registry_snapshot._record(ticket)
    assert calls == [ticket]
    assert receiver._end == receiver._end_snapshot < receiver._expected["work_end_ns"]
    assert native.deadline_ns == receiver._expected["work_end_ns"]
    assert native.start_attempted is False and native.resources is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_queued_work_uses_original_work_end_after_local_admission_cap(
    local, tmp_path, monkeypatch
):
    held, _ = await exchange(local, tmp_path, monkeypatch, "queued_after_admission")
    work = held["work"]
    assert work._initialized is True and work._refused is False
    assert work._end == held["receiver"]._expected["work_end_ns"]
    assert held["record"].credential_adoption_complete is True


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation",
    [
        "queued_key",
        "queued_budget",
        "queued_receipt",
        "queued_flags",
        "queued_final_key",
        "queued_foreign_refs",
        "queued_deadline",
        "queued_wrong_task",
        "queued_foreign_budget",
        "queued_forged_receipt",
        "queued_socket_receipt",
        "queued_grammar",
    ],
)
async def test_queued_current_refuses_late_drift_without_resource_or_go(
    local, tmp_path, monkeypatch, mutation
):
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    record, work = held["record"], held["work"]
    assert record.credential_adoption_complete is True
    assert calls == [record.ticket] and work._refused is True
    native = local[0]._registry_snapshot._record(record.ticket)
    assert native.resources is None and native.start_attempted is False
    assert held.get("callbacks", []) == []
    with pytest.raises(FrameError):
        work.current_queued()


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_queued_constructor_rejects_foreign_channel_before_getters(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "queued_factory_channel")
    record = held["record"]
    assert held["callbacks"] == [] and calls == [record.ticket]
    assert (
        record.credential_adoption_complete is False and record.credential_adoption_failed is True
    )
    assert record.credential_work_snapshot._initialized is False
    native = local[0]._registry_snapshot._record(record.ticket)
    assert native.resources is None and native.start_attempted is False


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_credential_channel_refuses_legacy_control_and_result_before_claims(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "legacy_control")
    assert held["legacy_refused"] is True and calls == [held["ticket"]]
    assert held["record"].credential_adoption_complete is True
    assert held["work"]._refused is False


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_prepared_credential_control_binds_original_task_and_performs_no_io(
    local, tmp_path, monkeypatch
):
    held, calls = await exchange(local, tmp_path, monkeypatch, "control_binding")
    control = held["prepared_control"]
    assert calls == [held["ticket"]] and control._failed is True
    assert held["record"].cancel_owner is control
    assert control._credential_binding_snapshot._refs is held["work"]._refs_snapshot
    assert local[0]._registry_snapshot._record(held["ticket"]).resources is None
    assert held["material_passed"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation", ["control_binding_creator_drift", "control_binding_reader_drift"]
)
async def test_prepared_control_rejects_foreign_context_without_getters_or_io(
    local, tmp_path, monkeypatch, mutation
):
    held, calls = await exchange(local, tmp_path, monkeypatch, mutation)
    assert held["binding_callbacks"] == [] and calls == [held["ticket"]]
    control = held["prepared_control"]
    assert control._failed is True and control._wire_received == 0
    assert control._go_receipt is None and control._cancel_receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize(
    "mutation",
    [
        "control_binding_material_key",
        "control_binding_material_control",
        "control_binding_material_budget",
    ],
)
async def test_controller_reader_material_rejects_revocation_and_callback_drift(
    local, tmp_path, monkeypatch, mutation
):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert held["material_passed"] is False and held.get("binding_callbacks", []) == []
    control = held["prepared_control"]
    assert control._failed is True and control._wire_received == 0
    assert control._go_receipt is None and control._cancel_receipt is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_go", "signed_control_cancel", "signed_control_scope",
    "signed_control_sequence", "signed_control_signature", "signed_control_hash",
    "signed_control_key", "signed_control_deadline", "signed_control_retire_after_read",
    "signed_control_fragmented", "signed_control_wrong_task", "signed_control_boot",
    "signed_control_window", "signed_control_counter", "signed_control_buffer",
    "signed_control_init_refs", "signed_control_final_refs",
    "signed_control_blocking", "signed_control_timeout",
])
async def test_original_signed_control_cursor_without_native_receipts(local, tmp_path, monkeypatch,
                                                                     mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "signed_cursor" in held


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_native_cancel", "signed_control_native_go",
    "signed_control_native_future_window", "signed_control_native_signature",
    "signed_control_native_retire", "signed_control_native_retire_parked",
    "signed_control_native_phase_drift", "signed_control_native_end_drift",
    "signed_control_native_notice_retire",
])
async def test_signed_cancel_native_receipt_and_owned_local_stop(local, tmp_path, monkeypatch,
                                                               mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "native_control" in held


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_native_service_cancel", "signed_control_native_service_wrong_task",
    "signed_control_native_service_wrong_spine", "signed_control_native_service_retired",
    "signed_control_native_service_foreign_future",
    "signed_control_native_service_initial_drift",
    "signed_control_native_service_final_future_drift",
])
async def test_original_service_consumes_only_current_signed_cancel(local, tmp_path, monkeypatch,
                                                                  mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "native_control" in held


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("mutation", [
    "signed_control_native_go_chain_cancel", "signed_control_native_go_chain_before_go",
    "signed_control_native_go_chain_missing_ready", "signed_control_native_go_chain_bad_signature",
    "signed_control_native_go_chain_wrong_sequence", "signed_control_native_go_chain_index_drift",
    "signed_control_native_go_chain_expired", "signed_control_native_go_chain_retired",
])
async def test_signed_go_receipt_then_same_cursor_cancel_without_worker_relay(local, tmp_path,
                                                                            monkeypatch, mutation):
    held, _ = await exchange(local, tmp_path, monkeypatch, mutation)
    assert "native_control" in held


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("suffix", [
    "before_auth", "before_header", "before_body", "after_go_auth", "after_go_header",
    "after_go_body", "earlier_cause", "expired_tail", "retired_tail", "late_go",
    "bad_signature", "unknown_readiness", "sample_error", "guard_timeout",
])
async def test_original_cleanup_time_cursor_without_budget_renewal(local, tmp_path, monkeypatch,
                                                                 suffix):
    held, _ = await exchange(local, tmp_path, monkeypatch,
                             "signed_control_native_cleanup_" + suffix)
    assert held["cleanup_checked"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("suffix", [
    "signed", "wrong_task", "no_resources", "no_input", "no_fact", "wrong_fact",
    "retired", "post_crypto", "late_fd_close", "late_fd_replace", "foreign_phase",
    "forged_begin_claim",
])
async def test_fixed_ready_signature_requires_actual_resource_input_write(local, tmp_path,
                                                                         monkeypatch, suffix):
    held, _ = await exchange(local, tmp_path, monkeypatch,
                             "signed_control_native_ready_" + suffix)
    assert "ready_record" in held or "ready_producer" in held or held["ready_acquisition_refused"]


async def exercise_ready_writer(producer, control, keys, monkeypatch, held, mutation, ready_event):
    import errno

    from hmp_plugin import presentation_credential_ready as module
    from hmp_plugin.presentation_credential_ready import CredentialReadyWriter

    refs = producer._refs_snapshot
    channel = refs[4][14]
    if mutation.endswith("wrong_task"):
        async def foreign_factory():
            with pytest.raises(FrameError):
                CredentialReadyWriter.retain(producer)
        await asyncio.create_task(foreign_factory())
        assert producer._writer is None and channel._credential_ready_writer is None
    writer = CredentialReadyWriter.retain(producer)
    held["ready_writer"] = writer
    with pytest.raises(FrameError):
        CredentialReadyWriter.retain(producer)
    if mutation.endswith("wrong_task"):
        async def foreign_write():
            with pytest.raises(FrameError):
                await writer.write_ready()
        await asyncio.create_task(foreign_write())
        assert writer._attempted is False and channel._writing is False
    held["writer_wire"] = producer._record + encode_frame(
        refs[4][4].binding, "READY", 0, b"", version=2)
    held["writer_actual_bytes"] = 0
    calls = []
    foreign_calls = []
    held["writer_foreign_calls"] = foreign_calls
    if mutation.endswith(("future_shadow", "foreign_fact")):
        def foreign(*args):
            foreign_calls.append(args)
            raise AssertionError("foreign Future method")
        if mutation.endswith("future_shadow"):
            writer._future_origin.add_done_callback = foreign
        else:
            class ForeignFact:
                def __getattribute__(self, name):
                    foreign_calls.append(name)
                    raise AssertionError("foreign input-write observation")
            changed = (*refs[:7], ForeignFact(), *refs[8:])
            producer._refs = producer._refs_snapshot = changed
            writer._refs = writer._refs_snapshot = (producer, changed, *writer._refs[2:])
        with pytest.raises(FrameError):
            await writer.write_ready()
        assert writer._attempted is False and not channel._writing
        assert not foreign_calls
        if mutation.endswith("future_shadow"):
            del writer._future_origin.add_done_callback
        else:
            producer._refs = producer._refs_snapshot = refs
            writer._refs = writer._refs_snapshot = (producer, refs, *writer._refs[2:])
        held["writer_ok"] = False
        held["writer_checked"] = True
        return
    if mutation.endswith("early_go"):
        from hmp_plugin import presentation_readiness as readiness
        original_wait = readiness.SelectorReadiness.wait
        held["writer_resume"] = asyncio.Event()
        held["writer_join_entered"] = asyncio.Event()
        original_join = CredentialReadyWriter.join_control
        async def observed_join(owner, controller):
            assert owner is writer and controller is control
            assert control._signed_cursor_snapshot._completion_snapshot is not None
            held["writer_join_entered"].set()
            return await original_join(owner, controller)
        monkeypatch.setattr(CredentialReadyWriter, "join_control", observed_join)
        async def paused_write_wait(owner, end_ns, **options):
            if type(owner) is readiness.SelectorWriteReadiness:
                ready_event.set()
                async with asyncio.timeout_at(end_ns / 1e9):
                    await held["writer_resume"].wait()
            return await original_wait(owner, end_ns, **options)
        monkeypatch.setattr(readiness.SelectorReadiness, "wait", paused_write_wait)
    if mutation.endswith("deadline"):
        from hmp_plugin.presentation_clock import NativeClockOwner
        original_sample = NativeClockOwner.sample
        def expired(clock):
            value = original_sample(clock)
            if writer._attempted and asyncio.current_task() is refs[4][15]:
                return refs[4][4].deadline_ns
            return value
        monkeypatch.setattr(NativeClockOwner, "sample", expired)
    if mutation.endswith("registration_unknown"):
        from hmp_plugin import presentation_readiness as readiness
        original_install = readiness._install_writer
        def ambiguous_install(*args):
            original_install(*args)
            raise OSError("synthetic add outcome unknown after native registration")
        monkeypatch.setattr(readiness, "_install_writer", ambiguous_install)
    original_future = writer._future_origin
    native = module._SEND
    def send(sock, data):
        calls.append(len(data))
        if mutation.endswith("kernel_wait") and len(calls) == 1:
            held["writer_padding"] = 0
            try:
                while True:
                    held["writer_padding"] += native(sock, b"S" * 16384)
            except BlockingIOError:
                assert held["writer_padding"] > 0
                ready_event.set()  # peer drains only this known synthetic preload
                raise
        if mutation.endswith(("wouldblock", "early_go", "registration_unknown")) \
                and len(calls) == 1:
            raise BlockingIOError(errno.EAGAIN, "synthetic known zero-progress wait")
        if mutation.endswith("zero"):
            return 0
        if mutation.endswith("unknown"):
            n = native(sock, data[:7])
            held["writer_actual_bytes"] += n
            raise OSError("synthetic unknown native-send outcome")
        limit = 37 if mutation.endswith(("partial", "wouldblock")) else len(data)
        n = native(sock, data[:limit])
        held["writer_actual_bytes"] += n
        if mutation.endswith("postsend_key"):
            keys["broker"].retire()
        if mutation.endswith("offset_drift"):
            writer._offset = writer._offset_snapshot = writer._offset + 1
        if mutation.endswith("future_swap"):
            replacement = asyncio.get_running_loop().create_future()
            held["writer_substitute_future"] = replacement
            writer._future = writer._future_origin = replacement
        return n
    monkeypatch.setattr(module, "_SEND", send)
    fails = mutation.endswith(("zero", "unknown", "postsend_key", "offset_drift",
                               "future_swap", "deadline", "registration_unknown"))
    if fails:
        with pytest.raises(OSError if mutation.endswith("_write_unknown") else FrameError):
            await writer.write_ready()
        assert writer._complete is False and writer._failed is True
        assert original_future.result() is False
        assert refs[4][18]._ready is False
        previous = list(calls)
        with pytest.raises(FrameError):
            await writer.write_ready()
        assert calls == previous
        if mutation.endswith(("unknown", "offset_drift", "future_swap", "registration_unknown")):
            assert writer._unknown and channel._writing
            with pytest.raises(FrameError):
                CredentialReadyWriter._released(writer, channel)
            if mutation.endswith("future_swap"):
                assert not held["writer_substitute_future"].done()
                assert original_future is writer._refs_snapshot[5][0]
        else:
            assert not writer._unknown and channel._writing is False
    else:
        await writer.write_ready()
        assert writer._complete and writer._future_origin.result() is True
        assert writer._offset == len(held["writer_wire"]) == held["writer_actual_bytes"]
        assert writer._grammar_attempted and refs[4][18]._ready
        assert channel._writing is False and writer._active is False and not writer._unknown
        CredentialReadyWriter._released(writer, channel)
        previous = list(calls)
        with pytest.raises(FrameError):
            await writer.write_ready()
        assert calls == previous
        if mutation.endswith(("partial", "wouldblock")):
            assert len(calls) > 2
        if mutation.endswith(("wouldblock", "kernel_wait")):
            assert writer._waiter_origin._retired and not writer._waiter_origin._unknown
    if mutation.endswith("shadow_wait"):
        def foreign_wait(*args):
            foreign_calls.append(args)
            raise AssertionError("foreign wait callback")
        writer._future_origin.add_done_callback = foreign_wait
    held["writer_ok"] = not fails
    assert control._go_receipt is None and refs[5]._go_attempted is False
    held["writer_checked"] = True


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("suffix", [
    "signed", "partial", "wouldblock", "wrong_task", "zero", "unknown",
    "postsend_key", "offset_drift", "future_shadow", "foreign_fact",
    "go_join", "early_go", "shadow_wait", "future_swap", "kernel_wait",
    "deadline", "registration_unknown",
])
async def test_fixed_ready_write_joins_actual_native_send_without_retry(
    local, tmp_path, monkeypatch, suffix
):
    held, _ = await exchange(local, tmp_path, monkeypatch,
                            "signed_control_native_ready_write_" + suffix)
    assert held["writer_checked"]
    assert len(held["writer_wire_observed"]) == held["writer_actual_bytes"]
    if held["writer_ok"] and suffix != "shadow_wait":
        # Historical local closure is usable by the outer same-loop fixture
        # after the service task stopped and role keys retired; no send/GO right.
        from hmp_plugin.presentation_credential_ready import CredentialReadyWriter
        channel = held["record"].channel_snapshot
        CredentialReadyWriter._released(held["ready_writer"], channel)
        cursor = held["native_control"]._signed_cursor_snapshot
        if cursor._io_unknown:
            # Writer retirement cannot release the distinct interrupted read.
            assert channel._reading and not channel._closed_known
            assert not channel._clock_closed_known
        else:
            assert channel._closed_known and channel._clock_closed_known
