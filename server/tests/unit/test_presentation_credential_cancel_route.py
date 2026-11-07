"""Real private sockets and disposable resources; synthetic native peer/authority.

No production startup, worker GO, providers, user content or remote closure credit.
"""

import asyncio
import os
import time
from dataclasses import replace
from io import FileIO

import pytest

from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_cancel import (
    _CANCEL_RECEIPT_MINT,
    BrokerCancellationOwner,
    _CancelReceipt,
)
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_broker_service import BrokerServiceSpine, SocketChannel
from hmp_plugin.presentation_cancel_budget import CancellationBudget
from hmp_plugin.presentation_credential_begin import CredentialBeginReceiver
from hmp_plugin.presentation_credential_handshake import CredentialHandshakeOwner
from hmp_plugin.presentation_credential_ready import CredentialReadyProducer, CredentialReadyWriter
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

from .test_presentation_broker_service import local as local
from .test_presentation_credential_native_binding import key_pair
from .test_presentation_remote import prepare
from .test_presentation_selected_protocol import darwin_model
from .test_presentation_supervisor import context as context


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("stage", ["before_ready", "ready", "after_go", "go_current",
                                  "go_current_wrong_actor", "go_current_deadline", "go_relay",
                                  "go_relay_wrong_actor",
                                  "go_relay_result", "go_relay_zero", "go_relay_partial",
                                  "go_relay_unknown", "go_relay_post_drift", "go_relay_tail_key",
                                  "go_relay_tail_retired", "go_relay_tail_cancel",
                                  "go_relay_tail_ready", "go_relay_result_sign",
                                  "go_relay_result_sign_wrong_actor", "go_relay_result_sign_key",
                                  "go_relay_result_sign_expired", "go_relay_result_sign_take_drift",
                                  "go_relay_result_sign_post_crypto_key",
                                  "go_relay_result_sign_take_alias", "go_relay_result_sign_write",
                                  "go_relay_result_sign_write_wrong_actor",
                                  "go_relay_result_sign_write_tail_key",
                                  "go_relay_result_sign_write_tail_control",
                                  "go_relay_result_sign_write_post_alias",
                                  "go_relay_result_sign_write_settlement",
                                  "go_relay_result_sign_write_init",
                                  "go_relay_result_sign_write_zero",
                                  "go_relay_result_sign_write_partial",
                                  "go_relay_result_sign_write_unknown",
                                  "go_relay_result_sign_write_tail_phase",
                                  "go_relay_result_sign_write_settlement_key",
                                  "go_relay_result_sign_write_blocked_cancel"])
async def test_original_gateway_cancel_reaches_original_authenticated_broker(
    context, local, tmp_path, monkeypatch, stage
):
    spine, enrollment, connect, _, _, _ = local
    darwin_model(monkeypatch)
    gateway = SocketChannel(connect(), replace(enrollment, gateway_pid=os.getpid(),
        service_pid=os.getpid() + 1), role="gateway", endpoint=spine._endpoint,
        observation=spine._observation)
    prepared = await prepare(context, (gateway, None, spine))
    authority, operation, _, _, _, _, packet, binding = prepared
    end = int(authority._record(operation).deadline * 1_000_000_000)
    keys = key_pair(tmp_path, enrollment.installation_generation)
    held = {}
    before_ready = stage == "before_ready"
    after_go = stage == "after_go" or stage.startswith(("go_current", "go_relay"))
    control_ready, gateway_waiting = asyncio.Event(), asyncio.Event()
    go_checked = asyncio.Event()
    result_failure = stage in ("go_relay_result_sign_key", "go_relay_result_sign_expired",
                               "go_relay_result_sign_take_drift",
                               "go_relay_result_sign_post_crypto_key",
                               "go_relay_result_sign_take_alias")
    relay_failure = stage in ("go_relay_zero", "go_relay_partial", "go_relay_unknown",
                              "go_relay_post_drift", "go_relay_tail_key", "go_relay_tail_retired",
                              "go_relay_tail_cancel", "go_relay_tail_ready")
    writer_failure = stage in ("go_relay_result_sign_write_tail_key",
                               "go_relay_result_sign_write_tail_control",
                               "go_relay_result_sign_write_post_alias",
                               "go_relay_result_sign_write_settlement",
                               "go_relay_result_sign_write_init",
                                  "go_relay_result_sign_write_zero",
                               "go_relay_result_sign_write_partial",
                               "go_relay_result_sign_write_unknown",
                               "go_relay_result_sign_write_tail_phase",
                               "go_relay_result_sign_write_settlement_key",
                               "go_relay_result_sign_write_blocked_cancel")
    operation_failure = relay_failure or result_failure or writer_failure

    async def broker():
        record = await BrokerServiceSpine._accept_owned(spine, end)
        channel = SocketChannel(record.socket, enrollment, role="broker", endpoint=spine._endpoint,
                                observation=spine._observation)
        record.channel = record.channel_snapshot = channel
        held["broker_channel"] = channel
        handshake = CredentialHandshakeOwner.retain(channel, keys["broker"], binding, end)
        await handshake.run()
        receiver = CredentialBeginReceiver.retain(handshake)
        await receiver.run()
        ticket = BrokerServiceSpine._adopt_credential_begin(spine, record)
        native = BrokerRegistry._record(spine._registry_snapshot, ticket)
        work = record.credential_work_snapshot
        control = (BrokerCancellationOwner.retain_credential_cancel(work) if before_ready
                   else BrokerCancellationOwner.stage_credential_go_control(work))
        held["control"] = control
        resources = process = child = None
        try:
            BrokerRegistry.start_resources(spine._registry_snapshot, ticket)
            resources = native.resources_snapshot
            held["disposable_resources"] = resources
            process = resources._process_snapshot
            child = process._child_snapshot
            BrokerRegistry.stage_resource_input(spine._registry_snapshot, ticket, packet)
            if before_ready:
                control_ready.set()
            else:
                producer = CredentialReadyProducer.retain(control)
                producer.prepare_ready()
                writer = CredentialReadyWriter.retain(producer)
                await writer.write_ready()
                held["broker_ready_writer"] = writer
            if stage.startswith(("go_current", "go_relay")):
                from hmp_plugin.presentation_credential_control import CredentialGoPhase
                from hmp_plugin.presentation_jobs import FrameError

                phase = control._signed_go_snapshot
                with pytest.raises(FrameError):
                    phase.creator_current()  # no notification yet, never relay permission
                assert phase._creator_refused is False
                async with asyncio.timeout_at(end / 1e9):
                    await asyncio.wait((control._go_future_snapshot,
                                       control._allocation_snapshot.task),
                                       return_when=asyncio.FIRST_COMPLETED)
                assert control._go_future_snapshot.done()
                try:
                    if stage == "go_current_wrong_actor":
                        async def wrong_current():
                            with pytest.raises(FrameError):
                                phase.creator_current()
                        await asyncio.create_task(wrong_current())
                        assert phase._creator_refused is False
                    if stage == "go_current_deadline":
                        from hmp_plugin.presentation_clock import NativeClockOwner
                        sample = NativeClockOwner.sample
                        calls = []

                        def expired_go(clock):
                            value = sample(clock)
                            if clock is channel._clock_owner_snapshot and not calls:
                                calls.append(True)
                                return end
                            return value

                        monkeypatch.setattr(NativeClockOwner, "sample", expired_go)
                        with pytest.raises(FrameError):
                            phase.creator_current()
                        assert phase._creator_refused is True and calls == [True]
                        with pytest.raises(FrameError):
                            phase.creator_current()
                        assert calls == [True]  # restored sampled time cannot revive consumer
                    else:
                        receipt = CredentialGoPhase.creator_current(phase)
                        assert receipt is control._go_receipt_snapshot
                        assert receipt is control._go_future_snapshot.result()
                    if stage.startswith("go_relay"):
                        from hmp_plugin import presentation_control_pipe as pipe_module
                        from hmp_plugin.presentation_credential_go_relay import CredentialGoRelay

                        relay = CredentialGoRelay.retain(control)
                        held["go_relay"] = relay
                        if stage == "go_relay_wrong_actor":
                            async def wrong_relay():
                                with pytest.raises(FrameError):
                                    relay.relay()
                            await asyncio.create_task(wrong_relay())
                            assert relay._attempted is False and relay._failed is False
                        write = pipe_module.os.write
                        held["relay_native_calls"] = 0
                        pipe_fd = resources._control_snapshot._identity_snapshot[0]

                        def observed_write(fd, data):
                            if fd != pipe_fd:
                                return write(fd, data)
                            held["relay_native_calls"] += 1
                            if stage == "go_relay_unknown":
                                raise OSError("synthetic uncertain control write")
                            if stage == "go_relay_zero":
                                return 0
                            result = write(fd, data[:7] if stage == "go_relay_partial" else data)
                            if stage == "go_relay_post_drift":
                                resources._control_snapshot._credential_go_relay = None
                            return result

                        monkeypatch.setattr(pipe_module.os, "write", observed_write)
                        if stage.startswith("go_relay_tail_"):
                            monotonic = pipe_module.time.monotonic

                            held["relay_foreign_ready_calls"] = []

                            class ForeignReady:
                                def __getattribute__(self, name):
                                    held["relay_foreign_ready_calls"].append(name)
                                    raise AssertionError("foreign READY producer getter")

                            def changed_write_tail():
                                import sys
                                value = monotonic()
                                if (sys._getframe(1).f_code
                                        is pipe_module.OwnedControlPipe._write_go.__code__):
                                    held["relay_tail_observed"] = True
                                    if stage == "go_relay_tail_key":
                                        keys["broker"].retire()
                                    elif stage == "go_relay_tail_retired":
                                        control._retired = True
                                    elif stage == "go_relay_tail_ready":
                                        control._credential_ready = ForeignReady()
                                    else:
                                        assert asyncio.current_task().cancel()
                                return value

                            monkeypatch.setattr(pipe_module.time, "monotonic", changed_write_tail)
                        if relay_failure:
                            with pytest.raises(FrameError):
                                relay.relay()
                            assert relay._failed and not relay._complete
                            assert relay._fact_snapshot is None and not control._go_relay_completed
                            expected_count = (0 if stage == "go_relay_zero" else
                                              7 if stage == "go_relay_partial" else
                                              65 if stage == "go_relay_post_drift" else None)
                            assert relay._count_snapshot == expected_count
                            if stage.startswith("go_relay_tail_"):
                                assert held["relay_tail_observed"]
                                assert held["relay_native_calls"] == 0
                                assert held["relay_foreign_ready_calls"] == []
                            if stage == "go_relay_post_drift":
                                assert relay._write_unknown and relay._write_returned
                            calls = held["relay_native_calls"]
                            with pytest.raises(FrameError):
                                relay.relay()
                            with pytest.raises(FrameError):
                                CredentialGoRelay.retain(control)
                            assert held["relay_native_calls"] == calls
                            held["go_current_checked"] = True
                            return None  # failed native work: no fabricated CANCEL/closure receipt
                        fact = relay.relay()
                        assert relay._complete and control._go_relay_completed
                        assert fact is relay._fact_snapshot and fact.count == 65
                        assert fact.close is resources._control_snapshot._close_observation
                        with pytest.raises(FrameError):
                            relay.relay()
                        with pytest.raises(FrameError):
                            CredentialGoRelay.retain(control)
                        if stage.startswith("go_relay_result"):
                            async with asyncio.timeout_at(end / 1e9):
                                # Exact native owner has a poll API, no asyncio completion event.
                                while not BrokerRegistry.poll_resource_result(  # noqa: ASYNC110
                                        spine._registry_snapshot, ticket):
                                    await asyncio.sleep(0.001)
                            held["actual_result_observed"] = True
                            if stage.startswith("go_relay_result_sign"):
                                import hashlib
                                import json

                                from hmp_plugin.presentation_credential_codec import decode_record
                                from hmp_plugin.presentation_credential_result import (
                                    CredentialResultProducer,
                                )

                                producer = CredentialResultProducer.retain(control)
                                held["result_producer"] = producer
                                if stage == "go_relay_result_sign_wrong_actor":
                                    async def wrong_result():
                                        with pytest.raises(FrameError):
                                            producer.prepare()
                                    await asyncio.create_task(wrong_result())
                                    assert not producer._attempted and not producer._failed
                                if stage == "go_relay_result_sign_key":
                                    keys["broker"].retire()
                                if stage == "go_relay_result_sign_expired":
                                    from hmp_plugin.presentation_clock import NativeClockOwner
                                    sample = NativeClockOwner.sample
                                    calls = []

                                    def expired_result(clock):
                                        now = sample(clock)
                                        if clock is channel._clock_owner_snapshot and not calls:
                                            calls.append(True)
                                            return end
                                        return now

                                    monkeypatch.setattr(NativeClockOwner, "sample", expired_result)
                                if stage in ("go_relay_result_sign_take_drift",
                                             "go_relay_result_sign_take_alias"):
                                    take = BrokerRegistry.take_resource_candidate
                                    held["result_alias_getters"] = []

                                    class ForeignGo:
                                        def __getattribute__(self, name):
                                            held["result_alias_getters"].append(name)
                                            raise AssertionError("foreign GO alias getter")

                                    def changed_take(registry, owned_ticket):
                                        payload = take(registry, owned_ticket)
                                        if stage == "go_relay_result_sign_take_alias":
                                            control._signed_go = ForeignGo()
                                        else:
                                            control._retired = True
                                        return payload

                                    monkeypatch.setattr(BrokerRegistry, "take_resource_candidate",
                                                        changed_take)
                                if stage == "go_relay_result_sign_post_crypto_key":
                                    from hmp_plugin import (
                                        presentation_credential_result as result_mod,
                                    )
                                    encode = result_mod.encode_record

                                    def retired_crypto(statement, signature):
                                        raw = encode(statement, signature)
                                        keys["broker"].retire()
                                        return raw

                                    monkeypatch.setattr(result_mod, "encode_record", retired_crypto)
                                if result_failure:
                                    with pytest.raises(FrameError) as caught:
                                        producer.prepare()
                                    assert producer._failed and producer._retired
                                    assert producer._payload_snapshot is None
                                    assert producer._frozen_snapshot is None
                                    assert caught.value.__context__ is None
                                    trace = caught.value.__traceback__
                                    while trace:
                                        if trace.tb_frame.f_code.co_filename.endswith(
                                                "presentation_credential_result.py"):
                                            for name in ("held", "part", "header", "raw", "digest",
                                                         "frozen"):
                                                assert trace.tb_frame.f_locals.get(name) is None
                                        trace = trace.tb_next
                                    taken = stage in ("go_relay_result_sign_take_drift",
                                                      "go_relay_result_sign_post_crypto_key",
                               "go_relay_result_sign_take_alias")
                                    assert resources._result_taken is taken
                                    if taken:
                                        assert not resources._candidate_snapshot
                                    with pytest.raises(FrameError):
                                        producer.prepare()
                                    with pytest.raises(FrameError):
                                        CredentialResultProducer.retain(control)
                                    assert record.result_writer is None
                                    held["go_current_checked"] = True
                                    return None  # no transfer or terminal proof after refusal
                                raw = producer.prepare()
                                frozen = producer._frozen_snapshot
                                statement = json.loads(decode_record(raw).canonical_json)
                                digest = hashlib.sha256(frozen.header)
                                digest.update(frozen.payload)
                                assert statement["phase"] == "RESULT"
                                assert statement["role"] == "broker" and statement["sequence"] == 1
                                assert statement["frame_sha256"] == digest.hexdigest()
                                assert statement["frame_length"] == (
                                    len(frozen.header) + len(frozen.payload))
                                assert resources._result_taken and not resources._candidate_snapshot
                                assert record.result_writer is None
                                assert channel._result_writer is None
                                if stage.startswith("go_relay_result_sign_write"):
                                    from hmp_plugin import (
                                        presentation_credential_result_write as rw,
                                    )
                                    if stage.endswith("_init"):
                                        check = SocketChannel._check
                                        calls = []

                                        def refused_initial(ch):
                                            if ch is channel and not calls:
                                                calls.append(True)
                                                assert producer._writer_snapshot is not None
                                                raise FrameError("synthetic-initial-check")
                                            return check(ch)

                                        monkeypatch.setattr(SocketChannel, "_check",
                                                            refused_initial)
                                        with pytest.raises(FrameError):
                                            rw.CredentialResultWriter.retain(producer)
                                        partial = producer._writer_snapshot
                                        assert partial._failed and partial._payload_snapshot is None
                                        with pytest.raises(FrameError):
                                            rw.CredentialResultWriter.retain(producer)
                                        assert producer._writer_snapshot is partial
                                        held["go_current_checked"] = True
                                        return None
                                    signed_writer = rw.CredentialResultWriter.retain(producer)
                                    held["signed_result_writer"] = signed_writer
                                    if stage.endswith("_wrong_actor"):
                                        async def wrong_writer():
                                            with pytest.raises(FrameError):
                                                await signed_writer.send()
                                        await asyncio.create_task(wrong_writer())
                                        assert not signed_writer._attempted
                                    actual_send = rw._SEND
                                    sent = bytearray()
                                    phase_eq = []
                                    if "_tail_" in stage:
                                        inheritable = rw.os.get_inheritable
                                        changed = []

                                        def changed_tail(fd):
                                            value = inheritable(fd)
                                            if (fd == channel._fd_snapshot and signed_writer._active
                                                    and not changed):
                                                changed.append(True)
                                                if stage.endswith("_key"):
                                                    keys["broker"].retire()
                                                elif stage.endswith("_phase"):
                                                    class ForeignPhase:
                                                        def __eq__(self, other):
                                                            phase_eq.append(True)
                                                            raise AssertionError("foreign phase eq")
                                                    resources._phase = ForeignPhase()
                                                else:
                                                    control._retired = True
                                            return value

                                        monkeypatch.setattr(rw.os, "get_inheritable", changed_tail)
                                    if "_settlement" in stage:
                                        settle = rw.CredentialResultWriter._settled

                                        def refused_settlement(owned):
                                            settle(owned)
                                            if owned is signed_writer:
                                                if stage.endswith("_key"):
                                                    keys["broker"].retire()
                                                else:
                                                    raise FrameError("synthetic-settlement-refusal")

                                        monkeypatch.setattr(rw.CredentialResultWriter, "_settled",
                                                            refused_settlement)

                                    def counted_result(sock, data):
                                        if stage.endswith("_blocked_cancel"):
                                            import errno
                                            held["go_current_checked"] = True
                                            go_checked.set()
                                            raise BlockingIOError(errno.EAGAIN, "synthetic-block")
                                        if stage.endswith("_zero"):
                                            return 0
                                        if stage.endswith("_partial") and sent:
                                            return 0
                                        if stage.endswith(("_partial", "_unknown")):
                                            count = actual_send(sock, data[:7])
                                        else:
                                            count = actual_send(sock, data)
                                        sent.extend(data[:count])
                                        if stage.endswith("_post_alias"):
                                            channel._credential_result_writer = object()
                                        if stage.endswith("_unknown"):
                                            raise OSError("synthetic-unknown-after-send")
                                        return count

                                    monkeypatch.setattr(rw, "_SEND", counted_result)
                                    if stage.endswith("_blocked_cancel"):
                                        with pytest.raises(asyncio.CancelledError):
                                            await signed_writer.send()
                                        raise asyncio.CancelledError
                                    if writer_failure:
                                        with pytest.raises(FrameError) as caught:
                                            await signed_writer.send()
                                        assert caught.value.__context__ is None
                                        assert signed_writer._failed and not signed_writer._complete
                                        assert signed_writer._fact_snapshot is None
                                        assert signed_writer._payload_snapshot is None
                                        assert producer._payload_snapshot is None
                                        assert producer._frozen_snapshot is None
                                        if stage.endswith("_unknown"):
                                            assert signed_writer._offset == 0 and len(sent) == 7
                                            assert signed_writer._unknown
                                        else:
                                            assert signed_writer._offset == len(sent)
                                        if "_tail_" in stage:
                                            assert not sent and not phase_eq
                                        if stage.endswith("_post_alias"):
                                            assert sent and not signed_writer._complete
                                        with pytest.raises(FrameError):
                                            await signed_writer.send()
                                        held["go_current_checked"] = True
                                        return None
                                    fact = await signed_writer.send()
                                    assert signed_writer._complete and not signed_writer._unknown
                                    assert fact is signed_writer._fact_snapshot
                                    assert fact.count == len(sent)
                                    assert sent == raw + frozen.header + frozen.payload
                                    assert signed_writer._payload_snapshot is None
                                    assert not channel._writing
                                    held["signed_result_sent"] = True
                                frozen = None
                                other = BrokerCancellationOwner.__new__(BrokerCancellationOwner)
                                other._retired = True
                                other._credential_result = producer
                                other._credential_result_snapshot = producer
                                assert producer.retire_from_control(other) is False
                                assert (producer._payload_snapshot is None) is (
                                    stage.startswith("go_relay_result_sign_write"))
                                from hmp_plugin.presentation_clock import NativeClockOwner
                                cleanup_sample = NativeClockOwner.cleanup_sample

                                def observed_retirement(clock):
                                    if (clock is channel._clock_owner_snapshot
                                            and control._retired):
                                        assert producer._retired
                                        assert producer._payload_snapshot is None
                                        assert producer._frozen_snapshot is None
                                        held["result_retired_before_clock"] = True
                                    return cleanup_sample(clock)

                                monkeypatch.setattr(NativeClockOwner, "cleanup_sample",
                                                    observed_retirement)
                                with pytest.raises(FrameError):
                                    producer.prepare()
                                with pytest.raises(FrameError):
                                    CredentialResultProducer.retain(control)
                    else:
                        assert resources._go_attempted is False
                        assert resources._control_snapshot._go._attempted is False
                    held["go_current_checked"] = True
                finally:
                    go_checked.set()
            frame = await BrokerServiceSpine._v2_control(spine, control)
            adoption = control._signed_cancel_snapshot
            assert adoption._consume_complete is True and adoption._consume_failed is False
            receipt = adoption._native_receipt_origin
            assert receipt is control._cancel_receipt_snapshot
            assert type(receipt) is _CancelReceipt and receipt.mint is _CANCEL_RECEIPT_MINT
            assert receipt.frame is frame and frame.header.kind == "CANCEL"
            assert frame.header.sequence == (2 if after_go else 1)
            assert receipt.allocation is control._allocation_snapshot
            held["broker_cancel_receipt"] = receipt
            budget = CancellationBudget.inspect(native.cleanup_budget_snapshot)
            held["broker_cancel_end"] = budget[2]
            assert (control._go_receipt is not None) is after_go
            assert resources._go_attempted is stage.startswith("go_relay")
            assert resources._control_snapshot._go._attempted is stage.startswith("go_relay")
            status = BrokerRegistry.status(spine._registry_snapshot, native.binding)
            assert status is RegistryStatus.PENDING
            if stage.startswith("go_relay_result_sign"):
                producer = held["result_producer"]
                assert producer._retired and producer._payload_snapshot is None
                assert producer._frozen_snapshot is None
                assert held["result_retired_before_clock"]
            return frame
        finally:
            BrokerCancellationOwner.abort(control)
            await asyncio.gather(control._allocation_snapshot.task, return_exceptions=True)
            # Own disposable fixture streams only. This is not broker/native release.
            if child is not None:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if type(stream) is FileIO and not FileIO.closed.__get__(stream, FileIO):
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

    broker_task = asyncio.create_task(broker())
    try:
        handshake = CredentialHandshakeOwner.retain(gateway, keys["gateway"], binding, end)
        await handshake.run()
        remote = authority.bind_remote(operation, gateway, handshake._operation_binding(), packet)
        canceller = None
        if before_ready:
            from hmp_plugin.presentation_credential_ready_read import NativeReadyReceiver
            from hmp_plugin.presentation_jobs import FrameError
            from hmp_plugin.presentation_readiness import SelectorReadiness

            wait = SelectorReadiness.wait

            async def observed_wait(owned, cutoff, **options):
                reader = gateway._credential_ready_receiver_snapshot
                if (type(reader) is NativeReadyReceiver and reader._started
                        and owned._origin_scope.task is reader._base_origin.allocation.task):
                    gateway_waiting.set()
                return await wait(owned, cutoff, **options)

            monkeypatch.setattr(SelectorReadiness, "wait", observed_wait)

            async def request_before_ready():
                async with asyncio.timeout_at(end / 1e9):
                    await control_ready.wait()
                    await gateway_waiting.wait()
                task = remote._cleanup_owner_snapshot._allocations_snapshot[1].task
                assert task.cancel()  # actual original gateway fixture task only

            canceller = asyncio.create_task(request_before_ready())
            held["canceller"] = canceller
            with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
                await remote.begin_ready()
            await canceller
        else:
            assert await remote.begin_ready() is True
        cleanup = remote._cleanup_owner_snapshot
        if before_ready:
            assert cleanup._credential_work_snapshot._ready_transition_snapshot is None
            assert "broker_ready_writer" not in held
        else:
            assert held["broker_ready_writer"]._complete is True
        if after_go:
            assert await remote.go() is True
            control = held["control"]
            async with asyncio.timeout_at(end / 1e9):
                await asyncio.wait((control._go_future_snapshot, control._allocation_snapshot.task),
                                   return_when=asyncio.FIRST_COMPLETED)
            assert control._go_future_snapshot.done() and control._go_receipt is not None
            if stage.startswith(("go_current", "go_relay")):
                async with asyncio.timeout_at(end / 1e9):
                    await go_checked.wait()
                if broker_task.done():
                    if broker_task.cancelled():
                        assert stage in ("go_relay_tail_cancel",
                                         "go_relay_result_sign_write_blocked_cancel")
                    else:
                        broker_task.result()  # preserve actual service failure
                assert held["go_current_checked"]
        RemoteCleanupOwner.request(cleanup)
        async with asyncio.timeout(3):
            local_closed = await asyncio.shield(cleanup._allocations_snapshot[0].task)
            if stage in ("go_relay_tail_cancel",
                                         "go_relay_result_sign_write_blocked_cancel"):
                outcome = (await asyncio.gather(broker_task, return_exceptions=True))[0]
                assert type(outcome) is asyncio.CancelledError and broker_task.cancelled()
                frame = None
            else:
                frame = await broker_task
        if operation_failure:
            assert frame is None
            if relay_failure:
                assert held["go_relay"]._fact_snapshot is None
            else:
                assert held["go_relay"]._complete
                assert held["result_producer"]._payload_snapshot is None
                assert held["result_producer"]._frozen_snapshot is None
            if stage.endswith("_blocked_cancel"):
                signed_writer = held["signed_result_writer"]
                assert signed_writer._cancel_requested and signed_writer._retired
                assert signed_writer._failed and not signed_writer._complete
                assert signed_writer._fact_snapshot is None
                assert signed_writer._payload_snapshot is None
                assert signed_writer._waiter_origin._retired
                assert not signed_writer._unknown and not signed_writer._active
                assert held["control"]._allocation_snapshot.task.done()
            assert not cleanup._result_token and remote._result_owner is None
            return  # local cleanup result is not remote settlement
        if stage.startswith("go_relay_result"):
            assert held["actual_result_observed"]
        assert local_closed is True and cleanup._socket_closed and cleanup._clock_closed
        assert cleanup._cancel_write_completed is True
        signer = (cleanup._pre_ready_cancel_commitment_snapshot if before_ready
                  else cleanup._credential_cancel_commitment_snapshot)
        writer = signer._writer_snapshot
        assert writer._complete and writer._offset == len(writer._scope_snapshot.wire)
        assert signer._frame_snapshot.endswith(frame.body)
        assert held["broker_cancel_end"] == cleanup._cancel_end_snapshot
        assert held["broker_cancel_receipt"].end == cleanup._cancel_end_snapshot
        assert not cleanup._result_token and remote._result_owner is None
        assert authority._record(operation).child is None
        assert held["control"]._allocation_snapshot.task.done()
    finally:
        canceller = held.get("canceller")
        if canceller is not None:
            if not canceller.done():
                canceller.cancel()
            await asyncio.gather(canceller, return_exceptions=True)
        if not broker_task.done():
            broker_task.cancel()
        await asyncio.gather(broker_task, return_exceptions=True)
        if (stage in ("go_relay_tail_cancel", "go_relay_result_sign_write_blocked_cancel")
                and broker_task.cancelled()):
            # Only after the original service is terminal: sole fixture reaper
            # finishes its own child disposal; no replacement protocol reader.
            resources = held.get("disposable_resources")
            if resources is not None:
                process = resources._process_snapshot
                child = process._child_snapshot
                for stream in (child.stdin, child.stdout, child.stderr):
                    if type(stream) is FileIO and not FileIO.closed.__get__(stream, FileIO):
                        FileIO.close(stream)
                until = time.monotonic() + 3
                while process._wait is None:
                    if process.poll_wait():
                        break
                    assert time.monotonic() < until
                    await asyncio.sleep(0.005)
                selector = resources._pipes_snapshot._selector
                if selector is not None:
                    type(selector).close(selector)
        assert gateway.close() and gateway.close_clock()
        # Native resource/terminal qualification is deliberately unfinished.
        # Do not manufacture service/registry release from the control receipt.
        service_closed = await spine.stop_local_sockets()
        held["service_local_retirement"] = service_closed
        broker_channel = held.get("broker_channel")
        if broker_channel is not None:
            closed = broker_channel.close()
            if operation_failure and not closed:
                from hmp_plugin.presentation_clock import NativeClockOwner
                # Fixture-owned native disposal after refusal; no protocol fact repaired.
                broker_channel._socket_snapshot.close()
                assert NativeClockOwner.close_local(broker_channel._clock_owner_snapshot)
                held["broker_fixture_disposal_only"] = True
            else:
                assert closed and broker_channel.close_clock()
        for key in keys.values():
            key.retire()


@pytest.mark.parametrize("field", ["packet_sha256", "packet_length", "identity", "context",
                                 "stream"])
def test_go_relay_input_fact_fences_foreign_fields_before_callbacks(tmp_path, field):
    from hmp_plugin.presentation_control_pipe import ControlInputWriteObservation
    from hmp_plugin.presentation_credential_go_relay import _input_shape
    from hmp_plugin.presentation_jobs import FrameError

    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("foreign input fact getter")

        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("foreign input fact equality")

        def __len__(self):
            calls.append("len")
            raise AssertionError("foreign input fact length")

    with open(tmp_path / "synthetic-input-shape", "wb", buffering=0) as stream:
        fact = ControlInputWriteObservation(object(), object(), stream, object(), object(),
                                            (1, 2, 3), (1, 1), "a" * 64, 4)
        assert _input_shape(fact) is None  # shape only, no native receipt or authority
        forged = fact._replace(**{field: Foreign()})
        with pytest.raises(FrameError):
            _input_shape(forged)
        assert calls == []


def test_result_handoff_rejects_foreign_channel_before_getters():
    from hmp_plugin.presentation_jobs import FrameError

    calls = []

    class ForeignChannel:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("foreign handoff channel getter")

    writer = CredentialReadyWriter.__new__(CredentialReadyWriter)
    writer._refs = writer._refs_snapshot = (object(), (), (), ForeignChannel(), object(), ())
    writer._active = False
    writer._complete = True
    with pytest.raises(FrameError):
        CredentialReadyWriter._metadata(writer)
    assert not calls
