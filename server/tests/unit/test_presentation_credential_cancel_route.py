"""Real private sockets and disposable resources; synthetic native peer/authority.

No production startup, worker GO, providers, user content or remote closure credit.
"""

import asyncio
import os
import time
from dataclasses import replace
from io import FileIO

import pytest

from hmp_plugin import presentation_cancel_budget as budget_api
from hmp_plugin import presentation_credential_cleanup_budget as cb
from hmp_plugin import presentation_credential_terminal as ct
from hmp_plugin import presentation_credential_terminal_write as tw
from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_cancel import (
    _CANCEL_RECEIPT_MINT,
    BrokerCancellationOwner,
    _CancelReceipt,
)
from hmp_plugin.presentation_broker_codec import BrokerFrame
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

_NEXT_FRAME_SUFFIXES = ("_notice_native_finished_nextframe",
    "_notice_native_finished_nextframe_badclaim",
    "_notice_native_finished_nextframe_claimslot",
    "_notice_native_finished_nextframe_budgetshorter",
    "_notice_native_finished_nextframe_budgetlater",
    "_notice_native_finished_nextframe_budgetlost",
    "_notice_native_finished_nextframe_budgetdrift",
    "_notice_native_finished_nextframe_budgetfuture",
    "_notice_native_finished_nextframe_budgetexpired",
    "_notice_native_finished_nextframe_budgetslot")
_BODY_FINISH_SUFFIXES = ("_notice_native_finished",
    "_notice_native_finished_seedmutated",
    "_notice_native_finished_next",
    *_NEXT_FRAME_SUFFIXES,
    "_notice_native_finished_initial",
    "_notice_native_finished_lost",
    "_notice_native_finished_digest",
    "_notice_native_finished_ledger",
    "_notice_native_finished_shadow",
    "_notice_native_finished_seal",
    "_notice_native_finished_resultcell",
    "_notice_native_finished_received",
    "_notice_native_finished_result",
)


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("stage", ["before_ready", "ready", "after_go", "go_current",
                                  "go_current_wrong_actor", "go_current_deadline",
                                  "go_current_park_expiry", "go_relay",
                                  "go_relay_wrong_actor",
                                  "go_relay_result", "go_relay_zero", "go_relay_partial",
                                  "go_relay_unknown", "go_relay_post_drift", "go_relay_tail_key",
                                  "go_relay_tail_retired", "go_relay_tail_cancel",
                                  "go_relay_tail_ready", "go_relay_result_sign",
                                  "go_relay_result_sign_wrong_actor", "go_relay_result_sign_key",
                                  "go_relay_result_sign_expired", "go_relay_result_sign_take_drift",
                                  "go_relay_result_sign_post_crypto_key",
                                  "go_relay_result_sign_take_alias", "go_relay_result_sign_write",
                                  "go_relay_result_sign_write_completed_fact",
                                  "go_relay_result_sign_write_completed_scope",
                                  "go_relay_result_sign_write_avatar",
                                  "go_relay_result_sign_write_deliver_normal",
                                  "go_relay_result_sign_write_deliver_avatar",
                                  "go_relay_result_sign_write_deliver_short",
                                  "go_relay_result_sign_write_deliver_zero",
                                  "go_relay_result_sign_write_deliver_lost",
                                  "go_relay_result_sign_write_deliver_cause",
                                  "go_relay_result_sign_write_deliver_slot",
                                  "go_relay_result_sign_write_deliver_signedalias",
                                  "go_relay_result_sign_write_deliver_produceralias",
                                  "go_relay_result_sign_write_deliver_blocked",
                                  "go_relay_result_sign_write_deliver_cancelled",
                                  "go_relay_result_sign_write_terminal_latecause",
                                  "go_relay_result_sign_write_terminal_key",
                                  "go_relay_result_sign_write_terminal_scope",
                                  "go_relay_result_sign_write_terminal_handoff",
                                  "go_relay_result_sign_write_terminal_verify",
                                  "go_relay_result_sign_write_terminal_header",
                                  "go_relay_result_sign_write_terminal_frame",
                                  "go_relay_result_sign_write_wrong_actor",
                                  "go_relay_result_sign_write_tail_key",
                                  "go_relay_result_sign_write_tail_control",
                                  "go_relay_result_sign_write_post_alias",
                                  "go_relay_result_sign_write_settlement",
                                  "go_relay_result_sign_write_init",
                                  "go_relay_result_sign_write_hashinit",
                                  "go_relay_result_sign_write_hashscope",
                                  "go_relay_result_sign_write_hashsha",
                                  "go_relay_result_sign_write_zero",
                                  "go_relay_result_sign_write_partial",
                                  "go_relay_result_sign_write_unknown",
                                  "go_relay_result_sign_write_tail_phase",
                                  "go_relay_result_sign_write_settlement_key",
                                  "go_relay_result_sign_write_blocked_cancel",
                                  "go_relay_result_sign_write_body",
                                  "go_relay_result_sign_write_body_adopt",
                                  "go_relay_result_sign_write_body_terminal_normal",
                                  "go_relay_result_sign_write_body_terminal_avatar",
                                  "go_relay_result_sign_write_body_terminal_wait",
                                  "go_relay_result_sign_write_body_terminal_authcredit",
                                  "go_relay_result_sign_write_body_terminal_framecredit",
                                  "go_relay_result_sign_write_body_terminal_finalkey",
                                  "go_relay_result_sign_write_body_terminal_frameswap",
                                  "go_relay_result_sign_write_body_terminal_finishswap",
                                  "go_relay_result_sign_write_body_terminal_factpair",
                                  "go_relay_result_sign_write_body_terminal_factcallback",
                                  "go_relay_result_sign_write_body_terminal_factcounter",
                                  "go_relay_result_sign_write_body_adopt_capture_phase",
                                  "go_relay_result_sign_write_body_adopt_notice",
                                  "go_relay_result_sign_write_body_adopt_notice_actors",
                                  "go_relay_result_sign_write_body_adopt_notice_scheduler",
                                  "go_relay_result_sign_write_body_adopt_notice_future",
                                  "go_relay_result_sign_write_body_adopt_notice_swapped",
                                  "go_relay_result_sign_write_body_adopt_notice_drift",
                                  "go_relay_result_sign_write_body_adopt_notice_ambiguous",
                                  "go_relay_result_sign_write_body_adopt_notice_revoked",
                                  "go_relay_result_sign_write_body_adopt_notice_barrier",
                                  "go_relay_result_sign_write_body_adopt_wrong_actor",
                                  "go_relay_result_sign_write_body_adopt_key",
                                  "go_relay_result_sign_write_body_adopt_header",
                                  "go_relay_result_sign_write_body_adopt_tail_token",
                                  "go_relay_result_sign_write_body_adopt_pending_pair",
                                  "go_relay_result_sign_write_body_adopt_pair",
                                  "go_relay_result_sign_write_body_adopt_attempt",
                                  "go_relay_result_sign_write_body_adopt_fact",
                                  "go_relay_result_sign_write_body_wrong_actor",
                                  "go_relay_result_sign_write_body_avatar",
                                  "go_relay_result_sign_write_body_avatar_revision",
                                  "go_relay_result_sign_write_body_challenge",
                                  "go_relay_result_sign_write_body_parent",
                                  "go_relay_result_sign_write_body_digest",
                                  "go_relay_result_sign_write_body_feed_key",
                                  "go_relay_result_sign_write_body_stream_pair",
                                  "go_relay_result_sign_write_body_hash_pair",
                                  "go_relay_result_sign_write_body_cancel",
                                  "go_relay_result_sign_write_body_cancel_cause_wake",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_advanced",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_consumed",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_continued",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_hashlost",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_initial",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_lost",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_digest",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_ledger",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_shadow",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_result",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_seal",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_resultcell",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_received",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_badclaim",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_claimslot",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetshorter",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetlater",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetlost",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetdrift",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetfuture",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetexpired",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_nextframe_budgetslot",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_next",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished_seedmutated",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_notice_native_finished",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_countbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_reserve_custodybad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_copybad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_scopebad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_countbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_capturebad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_genericbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_subclassbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_tailbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_waiterbad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_releasebad",
                                  "go_relay_result_sign_write_body_cancel_cause_wake_releasewaiterbad",
                                  "go_relay_result_sign_write_body_cancel_stale",
                                  "go_relay_result_sign_write_body_cancel_pair",
                                  "go_relay_result_sign_write_body_cancel_progress",
                                  "go_relay_result_sign_write_body_cancel_custody",
                                  "go_relay_result_sign_write_body_cancel_tail_waiter",
                                  "go_relay_result_sign_write_body_cancel_tail_custody",
                                  "go_relay_result_sign_write_body_cancel_release_waiter",
                                  "go_relay_result_sign_write_body_cancel_release_custody"])
async def test_original_gateway_cancel_reaches_original_authenticated_broker(
    context, local, tmp_path, monkeypatch, stage
):
    from hmp_plugin.presentation_jobs import FrameError

    spine, enrollment, connect, _, _, _ = local
    darwin_model(monkeypatch)
    gateway = SocketChannel(connect(), replace(enrollment, gateway_pid=os.getpid(),
        service_pid=os.getpid() + 1), role="gateway", endpoint=spine._endpoint,
        observation=spine._observation)
    body_terminal = stage.startswith("go_relay_result_sign_write_body_terminal_")
    body_terminal_fault = body_terminal and stage.endswith(
        ("_authcredit", "_framecredit", "_finalkey", "_frameswap", "_finishswap")
    )
    terminal_can_send = asyncio.Event()
    expected_avatar_sha = None
    if (stage.startswith("go_relay_result_sign_write_body")
            or stage in ("go_relay_result_sign_write_avatar",
                         "go_relay_result_sign_write_deliver_avatar")):
        from pathlib import Path

        from .test_presentation_broker_resources import image
        asset = Path(context[2].home) / "assets" / "avatar.png"
        asset.parent.mkdir(mode=0o700, exist_ok=True)
        asset.write_bytes(image())
        asset.chmod(0o600)
        if (
            (body_terminal and stage.endswith("_avatar"))
            or "_body_avatar" in stage
            or stage
            in ("go_relay_result_sign_write_avatar", "go_relay_result_sign_write_deliver_avatar")
        ):
            import hashlib

            from hmp_plugin.presentation_authority import ListenerFence, ParentAuthorityAdapter
            old_authority, old_operation, native = context
            old = old_authority._record(old_operation)
            avatar_authority = ParentAuthorityAdapter(old.lease.iid, service=native)
            avatar_operation = avatar_authority.reserve(old.lease, "AVATAR", old.headers,
                listener=object(), fence=ListenerFence(1), store=object(), bridge=object(),
                identity=object(), native_owner=object())
            context = avatar_authority, avatar_operation, native
            expected_avatar_sha = hashlib.sha256(image()).hexdigest()
    prepared = await prepare(context, (gateway, None, spine),
                             expected_avatar_sha=expected_avatar_sha)
    authority, operation, _, _, _, _, packet, binding = prepared
    end = int(authority._record(operation).deadline * 1_000_000_000)
    keys = key_pair(tmp_path, enrollment.installation_generation)
    held = {}
    before_ready = stage == "before_ready"
    after_go = stage == "after_go" or stage.startswith(("go_current", "go_relay"))
    control_ready, gateway_waiting = asyncio.Event(), asyncio.Event()
    go_checked = asyncio.Event()
    native_body_ready, native_body_queued, native_body_observed = (
        asyncio.Event(), asyncio.Event(), asyncio.Event())

    async def queue_native_body_tail(sock, tail):
        # Original private synthetic peer fault injection only. This does not
        # qualify broker currentness or a complete successful result writer.
        await native_body_ready.wait()
        extra = b""
        if stage.endswith(("_notice_native_finished_next", *_NEXT_FRAME_SUFFIXES)):
            import hashlib
            import json

            from hmp_plugin.presentation_broker_codec import encode_frame
            from hmp_plugin.presentation_credential_codec import (
                decode_record,
                encode_record,
                signing_bytes,
            )
            raw = held["signed_result_writer"]._scope_snapshot.raw
            value = json.loads(decode_record(raw).canonical_json)
            actual_binding = held[
                "gateway_body"
            ]._scope_origin.envelope_scope.write_scope.intent.binding
            held["terminal_fixture_binding_reconciled"] = binding != actual_binding
            from hmp_plugin.presentation_input_v3 import decode_input_v3
            from hmp_plugin.presentation_terminal_claim import (
                StartedClaim,
                claim_binding,
                encode_handoff,
            )
            write = held["gateway_body"]._scope_origin.envelope_scope.write_scope
            packet = write.intent.packet
            request = decode_input_v3(packet)
            domain = write.remote._clock_domain_values_snapshot
            domain_wire = json.dumps((domain[0], domain[1], domain[2].hex(), domain[3]),
                separators=(",", ":"), ensure_ascii=True).encode("ascii")
            claim = StartedClaim(claim_binding(actual_binding), request["profile"],
                request["operation"], request["deadline_ns"], request["challenge"],
                request["epoch"], hashlib.sha256(packet).hexdigest(),
                request["source_manifest_sha"], value["generation"],
                hashlib.sha256(domain_wire).hexdigest(), "OK", 0, held["result2_body_sha"])
            if stage.endswith("_nextframe_badclaim"):
                claim = claim._replace(result_sha256="0" * 64)
            stamp = None
            if stage.endswith(("_budgetshorter", "_budgetlater", "_budgetlost", "_budgetdrift",
                               "_budgetfuture", "_budgetexpired", "_budgetslot")):
                from hmp_plugin.presentation_cancel_budget import CancellationBudget
                from hmp_plugin.presentation_terminal_claim import CleanupStamp
                budget = write.remote._cleanup_budget
                _, original_now, original_end, failed = CancellationBudget.inspect(budget)
                assert not failed and type(original_end) is int
                delta = 1 if stage.endswith("_budgetlater") else -10_000_000
                sender_end = original_end + delta
                if stage.endswith("_budgetfuture"):
                    sender_end = request["deadline_ns"] + 250_000_000
                elif stage.endswith("_budgetexpired"):
                    sender_end = original_now - 1
                stamp = CleanupStamp(sender_end - 250_000_000, sender_end)
                held["terminal_sender_end"] = stamp.end_ns
            held["terminal_claim_wire"] = encode_handoff(claim, stamp)
            terminal_frame = encode_frame(actual_binding, "TERMINAL", 2,
                held["terminal_claim_wire"], version=2)
            value.update(phase="TERMINAL", sequence=2,
                frame_sha256=hashlib.sha256(terminal_frame).hexdigest(),
                frame_length=len(terminal_frame))
            extra = encode_record(value, keys["broker"]._private_key.sign(signing_bytes(value)))
            held["body_terminal_auth_wire"] = extra
            if stage.endswith(_NEXT_FRAME_SUFFIXES):
                held["body_terminal_frame_wire"] = terminal_frame
                extra += terminal_frame
        await asyncio.get_running_loop().sock_sendall(sock, tail + extra)
        held["native_body_tail"] = tail
        native_body_queued.set()
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
                                  "go_relay_result_sign_write_hashinit",
                                  "go_relay_result_sign_write_hashscope",
                                  "go_relay_result_sign_write_hashsha",
                                  "go_relay_result_sign_write_zero",
                               "go_relay_result_sign_write_partial",
                               "go_relay_result_sign_write_unknown",
                               "go_relay_result_sign_write_tail_phase",
                               "go_relay_result_sign_write_settlement_key",
                               "go_relay_result_sign_write_blocked_cancel")
    finish_case = "_notice_native_finished" in stage
    body_frame = stage.endswith(_NEXT_FRAME_SUFFIXES)
    body_next = stage.endswith(
        ("_notice_native_finished_next", *_NEXT_FRAME_SUFFIXES)
    )
    finish_failure = finish_case and not stage.endswith(
        (
            "_notice_native_finished",
            "_notice_native_finished_next",
            *_NEXT_FRAME_SUFFIXES,
        )
    )
    body_stage = stage.startswith("go_relay_result_sign_write_body")
    body_fault = (
        (body_terminal and stage.endswith(("_factpair", "_factcallback", "_factcounter")))
        or body_terminal_fault
        or (
            body_stage
            and not body_terminal
            and "_body_adopt" not in stage
            and stage
            not in (
                "go_relay_result_sign_write_body",
                "go_relay_result_sign_write_body_adopt",
                "go_relay_result_sign_write_body_wrong_actor",
                "go_relay_result_sign_write_body_avatar",
            )
        )
    )
    adopted_key_retirement = stage in (
        "go_relay_result_sign_write_body_adopt_key",
        "go_relay_result_sign_write_body_adopt_notice_revoked")
    terminal_fault = stage.startswith("go_relay_result_sign_write_terminal_")
    terminal_delivery = body_terminal or stage.startswith("go_relay_result_sign_write_deliver_")
    operation_failure = (
        terminal_fault or terminal_delivery
        or relay_failure
        or result_failure
        or writer_failure
        or body_fault
        or adopted_key_retirement
        or stage == "go_current_park_expiry"
    )

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

                                if body_stage and stage.endswith(
                                        ("_challenge", "_parent", "_avatar_revision")):
                                    from hmp_plugin.presentation_input_v3 import decode_input_v3
                                    from hmp_plugin.presentation_output_v2 import (
                                        decode_output_v2,
                                        encode_output_v2,
                                    )
                                    take = BrokerRegistry.take_resource_candidate
                                    input_row = decode_input_v3(packet)

                                    def changed_native_result(registry, owned_ticket):
                                        wire = take(registry, owned_ticket)
                                        row, avatar = decode_output_v2(
                                            wire, input_row["challenge"], input_row["epoch"])
                                        if stage.endswith("_challenge"):
                                            row["challenge"] = "0" * 64
                                        elif stage.endswith("_parent"):
                                            row["chain"][0][0] += 1
                                        else:
                                            import struct
                                            import zlib
                                            compressed = zlib.compress(b"\x00\x01\x02\x03\xff")
                                            payload = b"IDAT" + compressed
                                            chunk = (struct.pack(">I", len(compressed)) + payload
                                                     + struct.pack(">I", zlib.crc32(payload)))
                                            avatar = avatar[:33] + chunk + avatar[-12:]
                                            row["avatar_length"] = len(avatar)
                                            row["avatar_sha"] = hashlib.sha256(avatar).hexdigest()
                                            row["source_proof"]["avatar_body_sha"] = (
                                                row["avatar_sha"])
                                        encoded = encode_output_v2(row, avatar)
                                        if stage.endswith("_avatar_revision"):
                                            from hmp_plugin.presentation_output_v2 import (
                                                compare_parent_snapshot,
                                            )
                                            checked, _ = decode_output_v2(
                                                encoded, input_row["challenge"], input_row["epoch"])
                                            parent = (
                                                remote._job_origin_snapshot.parent_result_context)
                                            compare_parent_snapshot(checked, snapshot=parent[1],
                                                                    parent_home=parent[0])
                                            assert checked["avatar_sha"] != expected_avatar_sha
                                            held["revision_claim_codec_valid"] = True
                                        return encoded

                                    monkeypatch.setattr(BrokerRegistry, "take_resource_candidate",
                                                        changed_native_result)
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

                                    if stage.endswith(
                                        ("_init", "_hashinit", "_hashscope", "_hashsha")
                                    ):
                                        check = SocketChannel._check
                                        calls = []

                                        def refused_initial(ch):
                                            if ch is channel and not calls:
                                                calls.append(True)
                                                assert producer._writer_snapshot is not None
                                                raise FrameError("synthetic-initial-check")
                                            return check(ch)

                                        foreign_hash_calls = []
                                        if stage.endswith(("_hashinit", "_hashscope", "_hashsha")):
                                            real_hash = rw._PAYLOAD_SHA

                                            class ForeignHashScope:
                                                def __getattribute__(self, name):
                                                    foreign_hash_calls.append(name)
                                                    raise AssertionError("foreign hash scope")

                                            class ForeignHashSHA:
                                                def __eq__(self, value):
                                                    foreign_hash_calls.append("eq")
                                                    raise AssertionError("foreign hash digest")

                                            def lost_acquisition_hash(payload):
                                                result = real_hash(payload)
                                                calls.append(True)
                                                writer = producer._writer_snapshot
                                                if stage.endswith("_hashscope"):
                                                    changed = ForeignHashScope()
                                                elif stage.endswith("_hashsha"):
                                                    changed = writer._scope_snapshot._replace(
                                                        payload_sha=ForeignHashSHA())
                                                else:
                                                    raise FrameError(
                                                        "SYNTHETIC_PAYLOAD_HASH_ACK_LOST")
                                                writer._scope = writer._scope_snapshot = changed
                                                return result

                                            monkeypatch.setattr(rw, "_PAYLOAD_SHA",
                                                                lost_acquisition_hash)
                                        else:
                                            monkeypatch.setattr(SocketChannel, "_check",
                                                                refused_initial)
                                        with pytest.raises(FrameError) as caught:
                                            rw.CredentialResultWriter.retain(producer)
                                        assert caught.value.__context__ is None
                                        assert foreign_hash_calls == []
                                        partial = producer._writer_snapshot
                                        assert partial._failed and partial._payload_snapshot is None
                                        with pytest.raises(FrameError):
                                            rw.CredentialResultWriter.retain(producer)
                                        assert producer._writer_snapshot is partial
                                        held["go_current_checked"] = True
                                        return None
                                    signed_writer = rw.CredentialResultWriter.retain(producer)
                                    held["signed_result_writer"] = signed_writer
                                    from hashlib import sha256 as result2_hash
                                    held["result2_body_sha"] = result2_hash(
                                        signed_writer._payload_snapshot).hexdigest()
                                    if stage.endswith("_wrong_actor"):
                                        async def wrong_writer():
                                            with pytest.raises(FrameError):
                                                await signed_writer.send()
                                        await asyncio.create_task(wrong_writer())
                                        assert not signed_writer._attempted
                                    actual_send = rw._SEND
                                    sent = bytearray()
                                    phase_eq = []
                                    if "_tail_" in stage and not body_stage:
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
                                        if body_stage and type(data) is memoryview:
                                            if "_body_cancel" in stage:
                                                if ("_wake_reserve" in stage
                                                        and not held.get("partial_body_sent")):
                                                    count = actual_send(sock, data[:13])
                                                    sent.extend(data[:count])
                                                    held["partial_body_sent"] = count
                                                    if stage.endswith(
                                                        (
                                                            "_notice_native",
                                                            "_notice_native_advanced",
                                                            "_notice_native_consumed",
                                                            "_notice_native_continued",
                                                            "_notice_native_hashlost",
                                                            *_BODY_FINISH_SUFFIXES,
                                                        )
                                                    ):
                                                        tail_end = (len(data) if finish_case else
                                                                    19 if stage.endswith(
                                                            "_notice_native_continued") else 16)
                                                        tail = bytes(data[13:tail_end])
                                                        if finish_case and stage.endswith(
                                                            "_digest"
                                                        ):
                                                            tail = tail[:-1] + bytes([tail[-1] ^ 1])

                                                        task = asyncio.create_task(
                                                            queue_native_body_tail(sock, tail))
                                                        held["native_body_sender"] = task
                                                    return count
                                                return 0  # truncated synthetic peer
                                            if stage.endswith("_digest"):
                                                changed = bytes(data)
                                                changed = changed[:-1] + bytes([changed[-1] ^ 1])
                                                count = actual_send(sock, changed)
                                                sent.extend(changed[:count])
                                                held["body_wire_changed"] = True
                                                return count
                                        if stage.endswith("_blocked_cancel"):
                                            import errno
                                            held["go_current_checked"] = True
                                            go_checked.set()
                                            raise BlockingIOError(errno.EAGAIN, "synthetic-block")
                                        if stage.endswith("_zero") and not terminal_delivery:
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
                                    if body_stage and stage.endswith("_digest"):
                                        assert held["body_wire_changed"]
                                        assert len(sent) == (
                                            len(raw) + len(frozen.header) + len(frozen.payload))
                                    else:
                                        assert sent == raw + frozen.header + frozen.payload
                                    assert signed_writer._payload_snapshot is None
                                    assert not channel._writing
                                    if (
                                        stage
                                        in (
                                            "go_relay_result_sign_write",
                                            "go_relay_result_sign_write_avatar",
                                        )
                                        or terminal_fault
                                        or terminal_delivery
                                        or stage.startswith("go_relay_result_sign_write_completed_")
                                    ):
                                        from hmp_plugin import (
                                            presentation_credential_result_completed,
                                        )
                                        rc = presentation_credential_result_completed
                                        assert rc.current(signed_writer) is fact
                                        assert fact.scope.payload_sha == hashlib.sha256(
                                            frozen.payload).hexdigest()
                                        assert producer._payload_snapshot is None
                                        assert producer._frozen_snapshot is None
                                        from hmp_plugin.presentation_terminal_claim import (
                                            LocalStartedProducer,
                                        )
                                        if stage.endswith("_completed_fact"):
                                            changed = fact._replace(count=fact.count + 1)
                                            signed_writer._fact = changed
                                            signed_writer._fact_snapshot = changed
                                        elif stage.endswith("_completed_scope"):
                                            changed = fact.scope._replace(payload_sha="0" * 64)
                                            signed_writer._scope = changed
                                            signed_writer._scope_snapshot = changed
                                        if stage.startswith(
                                            "go_relay_result_sign_write_completed_"
                                        ):
                                            with pytest.raises(FrameError):
                                                LocalStartedProducer.retain(
                                                    spine, fact.scope.result_scope.refs[1])
                                            native_record = fact.scope.result_scope.refs[4]
                                            assert native_record.terminal_producer._failed
                                            with pytest.raises(FrameError):
                                                LocalStartedProducer.retain(
                                                    spine, fact.scope.result_scope.refs[1])
                                        else:
                                            terminal = LocalStartedProducer.retain(
                                                spine, fact.scope.result_scope.refs[1])
                                            claim = terminal.claim_data()
                                            assert claim.outcome == "OK" and claim.exit_code == 0
                                            assert claim.operation_kind == (
                                                "AVATAR"
                                                if stage.endswith("_avatar")
                                                else "METADATA"
                                            )
                                            assert claim.result_sha256 == fact.scope.payload_sha
                                            assert terminal._transfer_snapshot is fact
                                            assert terminal._observation_snapshot is (
                                                resources._observation_identity)

                                            async def wrong_export_actor():
                                                with pytest.raises(
                                                    (FrameError, AuthorityRefusalError)
                                                ):
                                                    ct.CredentialTerminalProducer.retain(terminal)

                                            await asyncio.create_task(wrong_export_actor())
                                            assert terminal._signed_exporter is None
                                            exporter = ct.CredentialTerminalProducer.retain(
                                                terminal
                                            )
                                            held["terminal_exporter"] = exporter

                                            async def wrong_prepare_actor():
                                                with pytest.raises(
                                                    (FrameError, AuthorityRefusalError)
                                                ):
                                                    exporter.prepare()

                                            await asyncio.create_task(wrong_prepare_actor())
                                            assert not exporter._attempted
                                            actual_encode, actual_verify = (
                                                ct.encode_record,
                                                ct.check_complete_frame,
                                            )
                                            signed_calls, foreign_header_calls = [], []

                                            class ForeignTerminalKind:
                                                def __eq__(self, value):
                                                    foreign_header_calls.append(value)
                                                    raise AssertionError("foreign terminal kind")

                                            def terminal_encode(value, signature):
                                                signed_calls.append(None)
                                                encoded = actual_encode(value, signature)
                                                if stage.endswith("_terminal_latecause"):
                                                    BrokerCancellationOwner._local_cause(control)
                                                elif stage.endswith("_terminal_key"):
                                                    keys["broker"].retire()
                                                elif stage.endswith("_terminal_scope"):
                                                    changed = exporter._scope_origin._replace(
                                                        pins=()
                                                    )
                                                    exporter._scope = exporter._scope_origin = (
                                                        changed
                                                    )
                                                elif stage.endswith("_terminal_handoff"):
                                                    changed = exporter._handoff_origin._replace(
                                                        wire=b"{}"
                                                    )
                                                    exporter._handoff = exporter._handoff_origin = (
                                                        changed
                                                    )
                                                return encoded

                                            def terminal_verify(*args, **kwargs):
                                                header = actual_verify(*args, **kwargs)
                                                if stage.endswith("_terminal_verify"):
                                                    keys["broker"].retire()
                                                elif stage.endswith("_terminal_header"):
                                                    object.__setattr__(header, "kind",
                                                                       ForeignTerminalKind())
                                                return header

                                            actual_frame = ct.encode_frame

                                            def terminal_frame(*args, **kwargs):
                                                value = actual_frame(*args, **kwargs)
                                                return value[:-1] + bytes([value[-1] ^ 1])

                                            if stage.endswith("_terminal_frame"):
                                                monkeypatch.setattr(
                                                    ct, "encode_frame", terminal_frame
                                                )
                                            monkeypatch.setattr(
                                                ct, "encode_record", terminal_encode
                                            )
                                            monkeypatch.setattr(
                                                ct, "check_complete_frame", terminal_verify
                                            )
                                            if terminal_fault:
                                                with pytest.raises(
                                                    (FrameError, AuthorityRefusalError)
                                                ):
                                                    exporter.prepare()
                                                assert exporter._failed and exporter._attempted
                                                assert not exporter._complete
                                                assert exporter._frozen_origin is None
                                            else:
                                                envelope = exporter.prepare()
                                                assert envelope.handoff.claim is claim
                                                assert envelope.handoff.cleanup_end is None
                                                assert envelope.checked.frame_length == len(
                                                    envelope.frame)
                                            assert producer._payload_snapshot is None
                                            assert signed_writer._payload_snapshot is None
                                            assert signed_calls == [None]
                                            with pytest.raises((FrameError, AuthorityRefusalError)):
                                                exporter.prepare()
                                            with pytest.raises((FrameError, AuthorityRefusalError)):
                                                ct.CredentialTerminalProducer.retain(terminal)
                                            assert signed_calls == [None]
                                            assert foreign_header_calls == []
                                            assert len(sent) == fact.count
                                            held["terminal_sign_calls"] = len(signed_calls)
                                            if terminal_delivery:
                                                delivery = tw.CredentialTerminalWriter.retain(
                                                    exporter
                                                )
                                                held["terminal_delivery"] = delivery
                                                real_send, writes, transmitted = (
                                                    tw._SEND,
                                                    [],
                                                    bytearray(),
                                                )
                                                foreign_write_calls = []

                                                class ForeignWriteCell:
                                                    def __getitem__(self, key):
                                                        foreign_write_calls.append(key)
                                                        raise AssertionError("foreign write cell")

                                                def terminal_send(sock, value):
                                                    writes.append(len(value))
                                                    if stage.endswith("_zero"):
                                                        return 0
                                                    if stage.endswith("_blocked"):
                                                        import errno
                                                        raise BlockingIOError(errno.EAGAIN,
                                                                              "synthetic terminal")
                                                    if stage.endswith("_cancelled"):
                                                        raise asyncio.CancelledError
                                                    limit = (
                                                        113
                                                        if stage.endswith("_short")
                                                        else (
                                                            13
                                                            if stage.endswith(
                                                                (
                                                                    "_lost",
                                                                    "_cause",
                                                                    "_slot",
                                                                    "_signedalias",
                                                                    "_produceralias",
                                                                )
                                                            )
                                                            else len(value)
                                                        )
                                                    )
                                                    count = real_send(sock, value[:limit])
                                                    transmitted.extend(value[:count])
                                                    if stage.endswith("_lost"):
                                                        raise OSError("SYNTHETIC_TERMINAL_ACK_LOST")
                                                    if stage.endswith("_cause"):
                                                        BrokerCancellationOwner._local_cause(control)
                                                    if stage.endswith("_slot"):
                                                        delivery._scope_cell = ForeignWriteCell()
                                                    if stage.endswith("_signedalias"):
                                                        signed_writer._terminal_writer = object()
                                                    if stage.endswith("_produceralias"):
                                                        exporter._writer = object()
                                                    return count

                                                monkeypatch.setattr(tw, "_SEND", terminal_send)
                                                if body_terminal and stage.endswith("_wait"):
                                                    await terminal_can_send.wait()
                                                if stage.endswith(
                                                    (
                                                        "_zero",
                                                        "_lost",
                                                        "_cause",
                                                        "_slot",
                                                        "_signedalias",
                                                        "_produceralias",
                                                        "_blocked",
                                                        "_cancelled",
                                                    )
                                                ):
                                                    expected_error = (
                                                        asyncio.CancelledError
                                                        if stage.endswith("_cancelled")
                                                        else FrameError
                                                    )
                                                    with pytest.raises(expected_error):
                                                        await delivery.send()
                                                    assert delivery._failed and delivery._unknown
                                                    assert not delivery._complete
                                                    assert delivery._offset == (
                                                        13
                                                        if stage.endswith(
                                                            (
                                                                "_cause",
                                                                "_slot",
                                                                "_signedalias",
                                                                "_produceralias",
                                                            )
                                                        )
                                                        else 0
                                                    )
                                                else:
                                                    transfer = await delivery.send()
                                                    assert transfer is delivery._fact_origin
                                                    assert transfer.count == len(transmitted)
                                                    assert (
                                                        transmitted == envelope.raw + envelope.frame
                                                    )
                                                    assert (
                                                        not delivery._active
                                                        and not channel._writing
                                                    )
                                                first_writes = len(writes)
                                                with pytest.raises(FrameError):
                                                    await delivery.send()
                                                assert len(writes) == first_writes
                                                assert foreign_write_calls == []
                                                if stage.endswith(
                                                    ("_slot", "_signedalias", "_produceralias")
                                                ):
                                                    assert delivery._active and channel._writing
                                                    assert delivery._count_cell[2] == 13
                                                assert signed_writer._payload_snapshot is None

                                        assert producer._payload_snapshot is None
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
            if stage == "go_current_park_expiry":
                # Actual CANCEL and actual original timeout. Never extend/sample a
                # replacement budget or manufacture a completed receipt/task.
                original_task = control._allocation_snapshot.task
                async with asyncio.timeout_at(end / 1e9):
                    await asyncio.wait((original_task, control._cancel_future_snapshot),
                                       return_when=asyncio.FIRST_COMPLETED)
                    assert control._notice_completed and control._parked
                    assert control._cancel_future_snapshot.done()
                    assert control._stop_intent_snapshot is None
                    assert type(control._timeout_snapshot) is asyncio.Timeout
                    frozen_end = CancellationBudget.inspect(control._scope_snapshot[3])[2]
                    assert type(frozen_end) is int
                    await asyncio.gather(original_task, return_exceptions=True)
                assert original_task.done() and not original_task.cancelled()
                failure = original_task.exception()
                assert type(failure) is FrameError
                assert failure.args == ("BI1_CREDENTIAL_CANCEL_ADOPTION_REFUSED",)
                assert asyncio.Timeout.expired(control._timeout_snapshot)
                assert control._park_future_snapshot.done()
                assert control._park_future_snapshot.cancelled()
                assert control._failed and control._io_unknown
                assert CancellationBudget.inspect(control._scope_snapshot[3])[2] == frozen_end
                with pytest.raises(FrameError):
                    await BrokerServiceSpine._v2_control(spine, control)
                adoption = control._signed_cancel_snapshot
                assert adoption._consume_attempted and not adoption._consume_complete
                assert adoption._consume_failed
                assert adoption._native_receipt_origin is control._cancel_receipt_snapshot
                assert adoption._native_receipt_origin is not None
                held["actual_park_expiry_refused"] = True
                return None
            try:
                frame = await BrokerServiceSpine._v2_control(spine, control)
            except FrameError as consumer_failure:
                if stage in ("go_relay", "go_current_wrong_actor",
                             "go_relay_result_sign_write_body_adopt_notice_ambiguous",
                             "go_relay_result_sign_write_body_adopt_capture_phase"):
                    import json as diagnostic_json

                    from hmp_plugin.presentation_remote_cleanup import _FUTURE, _TASK
                    original_task = control._allocation_snapshot.task
                    timeout = control._timeout_snapshot
                    from hmp_plugin.presentation_cleanup_reader import (
                        CleanupReadGate as DiagnosticGate,
                    )
                    from hmp_plugin.presentation_credential_control import CredentialControlCursor
                    original_cursor = control._signed_cursor_snapshot
                    gateway_root = remote._cleanup_owner_snapshot
                    gateway_gate = (gateway_root._read_gate_snapshot
                                    if type(gateway_root) is RemoteCleanupOwner else None)
                    snapshot = {
                        "signed_gateway_notice_present": (
                            type(gateway_gate) is DiagnosticGate
                            and gateway_gate._signed_notice_allocation_origin is not None),
                        "task_done": _TASK.done(original_task),
                        "task_cancelled": _TASK.cancelled(original_task),
                        "task_cancelling": _TASK.cancelling(original_task),
                        "failed": control._failed, "io_unknown": control._io_unknown,
                        "parked": control._parked, "retired": control._retired,
                        "notice_attempted": control._notice_attempted,
                        "notice_completed": control._notice_completed,
                        "stop_intent_present": control._stop_intent_snapshot is not None,
                        "park_future_done": _FUTURE.done(control._park_future_snapshot),
                        "park_future_cancelled": _FUTURE.cancelled(control._park_future_snapshot),
                        "go_future_done": _FUTURE.done(control._go_future_snapshot),
                        "cancel_future_done": _FUTURE.done(control._cancel_future_snapshot),
                        "timeout_expired": (asyncio.Timeout.expired(timeout)
                                            if type(timeout) is asyncio.Timeout else None),
                    }
                    if type(original_cursor) is CredentialControlCursor:
                        for field in ("_failed", "_io_unknown", "_read_intent", "_complete"):
                            value = original_cursor.__dict__.get(field)
                            snapshot["cursor" + field] = value if type(value) is bool else None
                    try:
                        original_end, _, cleanup_end, failed = CancellationBudget.inspect(
                            control._scope_snapshot[3])
                        snapshot.update(budget_original_end=original_end,
                                        budget_end=cleanup_end, budget_failed=failed)
                    except BaseException:
                        snapshot["budget_metadata_refused"] = True
                    # Exact primitive fixture state only: no new clock sample, body,
                    # private key, error text, permission, retry or success recovery.
                    consumer_failure.add_note(diagnostic_json.dumps(snapshot, sort_keys=True))
                # Keep the original controller cause visible; do not turn a stale
                # creator refusal into success or manufacture native closure.
                original_task = control._allocation_snapshot.task
                if original_task.done() and not original_task.cancelled():
                    controller_failure = original_task.exception()
                    if controller_failure is not None:
                        raise controller_failure from consumer_failure
                raise
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

    if stage.startswith("go_relay_result_sign_write_body"):
        from hmp_plugin.presentation_credential_result_body import NativeResultBodyOwner
        from hmp_plugin.presentation_credential_result_read import NativeResultEnvelopeReceiver
        from hmp_plugin.presentation_remote import RemoteOperationOwner

        original_exchange = RemoteOperationOwner._go_exchange

        async def original_signed_body(owned):
            result = await original_exchange(owned)
            producer = owned._cleanup_owner_snapshot._credential_work_snapshot
            if "_wake_reserve" in stage:
                SocketChannel._go_written(owned._channel_snapshot, owned)
                assert RemoteCleanupOwner._publish_write_quiescence(owned._cleanup_owner_snapshot)
            envelope = NativeResultEnvelopeReceiver.retain(
                producer._go_commitment_snapshot._writer_snapshot)
            await envelope.run()
            if stage.endswith("_wrong_actor"):
                async def wrong_body_factory():
                    with pytest.raises(FrameError):
                        NativeResultBodyOwner.retain(envelope)
                await asyncio.create_task(wrong_body_factory())
                assert envelope._body_owner is None
            body = NativeResultBodyOwner.retain(envelope)
            held["gateway_body"] = body
            if stage.endswith("_wrong_actor"):
                async def wrong_body_receive():
                    with pytest.raises(FrameError):
                        await body.receive()
                await asyncio.create_task(wrong_body_receive())
                assert not body._attempted and not body._failed
            if stage.endswith("_feed_key"):
                from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2
                feed = BoundedResultBufferV2.feed

                def revoked_feed(buffer, part):
                    feed(buffer, part)
                    if buffer is body._scope_origin.buffer:
                        keys["gateway"].retire()

                monkeypatch.setattr(BoundedResultBufferV2, "feed", revoked_feed)
            if stage.endswith(("_stream_pair", "_hash_pair")):
                import hashlib

                from hmp_plugin.presentation_credential_phase import check_commitment
                from hmp_plugin.presentation_credential_stream import CommittedFrameDigest
                if stage.endswith("_stream_pair"):
                    e = envelope._scope_origin
                    f = envelope._completion_origin
                    checked = check_commitment(f.raw, sender_public=e.pins[0],
                        receiver_public=e.pins[1], expected=dict(e.expected))
                    replacement = CommittedFrameDigest(checked, f.frame,
                                                        binding=e.write_scope.intent.binding)
                    body._stream = body._stream_origin = replacement
                else:
                    replacement = hashlib.sha256()
                    body._hash = body._hash_origin = replacement
                held["body_replacement"] = replacement
            if "_body_cancel" in stage:
                from hmp_plugin import presentation_credential_result_body as body_module
                from hmp_plugin.presentation_readiness import SelectorReadiness
                wait = SelectorReadiness.wait
                waiting = asyncio.Event()
                stale = None
                if stage.endswith(("_stale", "_pair")):
                    import socket
                    left, right = socket.socketpair()
                    left.setblocking(False)
                    right.setblocking(False)
                    entered = asyncio.Event()

                    async def earlier_wait():
                        owned = SelectorReadiness(left)
                        entered.set()
                        try:
                            await wait(owned, end)
                        except body_module._ReadinessCancelledError as error:
                            return error.retirement
                        raise AssertionError("prior synthetic wait unexpectedly returned")

                    old_task = asyncio.create_task(earlier_wait())
                    await entered.wait()
                    old_task.cancel()
                    stale = await old_task
                    assert stale.mint is body_module._CANCEL_RETIREMENT_MINT
                    left.close()
                    right.close()

                if "_tail_" in stage or "_release_" in stage:
                    retirement_current = NativeResultBodyOwner._retirement_current
                    wake_guard = SelectorReadiness._wake_guard

                    def observed_retirement(owned_body, receipt, *, released=False):
                        held["inside_body_retirement"] = (owned_body, released)
                        try:
                            return retirement_current(owned_body, receipt, released=released)
                        finally:
                            held.pop("inside_body_retirement", None)

                    def changed_final_wake(waiter):
                        wake_guard(waiter)
                        at = held.get("inside_body_retirement")
                        expected_released = "_release_" in stage
                        if (at == (body, expected_released) and waiter is body._waiter_origin
                                and not held.get("body_retirement_tail_changed")):
                            held["body_retirement_tail_changed"] = True
                            if stage.endswith("_custody"):
                                held["foreign_accumulator"] = bytearray(b"untouched")
                                body._scope_origin.buffer._buffer = held["foreign_accumulator"]
                            else:
                                old = waiter._wake_binding_origin
                                waiter._wake_binding = waiter._wake_binding_origin = old._replace(
                                    end=old.end + 1)

                    monkeypatch.setattr(NativeResultBodyOwner, "_retirement_current",
                                        observed_retirement)
                    monkeypatch.setattr(SelectorReadiness, "_wake_guard", changed_final_wake)

                if stage.endswith(("_waiterbad", "_releasewaiterbad")):
                    import socket
                    other_left, other_right = socket.socketpair()
                    other_left.setblocking(False)
                    other_right.setblocking(False)
                    held["wake_other_sockets"] = (other_left, other_right)
                    held["wake_other_waiter"] = SelectorReadiness(other_left)
                if stage.endswith(("_tailbad", "_waiterbad", "_releasebad", "_releasewaiterbad")):
                    import sys
                    wake_guard = SelectorReadiness._wake_guard
                    def changed_body_wake_guard(waiter):
                        value = wake_guard(waiter)
                        caller = sys._getframe(1).f_code
                        outer = sys._getframe(2).f_code
                        active = (caller is SelectorReadiness._woken_local.__code__
                            and outer is NativeResultBodyOwner._wake_retirement_current.__code__)
                        historical = (
                            caller is NativeResultBodyOwner._wake_retirement_released.__code__)
                        target = historical if "_release" in stage else active
                        actual = body._waiter_origin
                        if historical and body._wake_receipt_origin is not None:
                            actual = body._wake_receipt_origin.wait.waiter
                        if (waiter is actual and target
                                and not held.get("body_wake_tail_changed")):
                            held["body_wake_tail_changed"] = True
                            if "waiterbad" in stage:
                                body._waiter = body._waiter_origin = held["wake_other_waiter"]
                            else:
                                body._received = body._received_snapshot = body._received + 1
                        return value
                    monkeypatch.setattr(SelectorReadiness, "_wake_guard", changed_body_wake_guard)
                async def observed_wait(waiter, cutoff, **options):
                    if waiter is not body._waiter_origin:
                        return await wait(waiter, cutoff, **options)
                    waiting.set()
                    try:
                        return await wait(waiter, cutoff, **options)
                    except body_module._ReadinessWakeRetiredError as error:
                        if "_cause_wake" not in stage:
                            raise
                        if stage.endswith("_copybad"):
                            raise body_module._ReadinessWakeRetiredError(
                                error.retirement._replace()) from None
                        if stage.endswith("_scopebad"):
                            copied = waiter._origin_scope._replace()
                            waiter._scope = waiter._scope_snapshot = waiter._origin_scope = copied
                        if stage.endswith("_countbad"):
                            body._received = body._received_snapshot = body._received + 1
                        if stage.endswith("_capturebad"):
                            gate = owned._cleanup_owner_snapshot._read_gate_snapshot
                            copied = gate._signed_capture_origin._replace()
                            gate._signed_capture = gate._signed_capture_origin = copied
                        if stage.endswith("_genericbad"):
                            raise body_module.ReadinessWakeError from None
                        if stage.endswith("_subclassbad"):
                            actual = error.retirement
                            class ForeignWake(body_module._ReadinessWakeRetiredError):
                                def __init__(self):
                                    body_module.ReadinessWakeError.__init__(self)
                                @property
                                def retirement(self):
                                    held["foreign_wake_getter"] = True
                                    return actual
                            raise ForeignWake() from None
                        raise
                    except body_module._ReadinessCancelledError:
                        if stage.endswith("_stale"):
                            raise body_module._ReadinessCancelledError(stale) from None
                        if stage.endswith("_pair"):
                            waiter._origin_scope = waiter._scope_snapshot = stale.scope
                            waiter._future_origin = waiter._future_snapshot = stale.future
                            waiter._wake_binding = waiter._wake_binding_origin = stale.binding
                            waiter._handle = waiter._handle_snapshot = stale.handle
                            waiter._handle_args = waiter._handle_args_snapshot = stale.handle_args
                            raise body_module._ReadinessCancelledError(stale) from None
                        if stage.endswith("_progress"):
                            body._received = body._received_snapshot = body._received + 1
                        if stage == "go_relay_result_sign_write_body_cancel_custody":
                            held["foreign_accumulator"] = bytearray(b"untouched")
                            body._scope_origin.buffer._buffer = held["foreign_accumulator"]
                        raise

                async def original_cause():
                    await waiting.wait()
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    from hmp_plugin.presentation_credential_cleanup_capture import (
                        inspect_signed_cleanup,
                    )
                    cleanup = owned._cleanup_owner_snapshot
                    sample = NativeClockOwner.cleanup_sample
                    def withdrawn_partial_before_clock(clock):
                        if clock is owned._clock_owner_snapshot and cleanup._intent:
                            assert body._retired and body._candidate_snapshot is None
                            assert not body._scope_origin.accumulator
                            assert body._scope_origin.job.result is None
                            assert body._scope_origin.job.remote_result_token is None
                            held["partial_capture_withdrawn_before_clock"] = True
                        return sample(clock)
                    monkeypatch.setattr(NativeClockOwner, "cleanup_sample",
                                        withdrawn_partial_before_clock)
                    RemoteCleanupOwner.request(cleanup)
                    gate = cleanup._read_gate_snapshot
                    captured = gate._signed_capture_origin
                    assert captured is not None
                    assert inspect_signed_cleanup(captured, gate, cleanup) is captured
                    assert captured.body.owner is body and captured.body.active
                    assert not captured.body.validated and captured.envelope.complete
                    assert captured.body.received == captured.body.committed == 0
                    assert captured.body.waiter.owner is body._waiter_origin
                    assert captured.body.waiter.scope.task is cleanup._allocations_snapshot[1].task
                    assert not captured.body.waiter.future_done
                    assert captured.write is None  # no invented pre-GO-notice quiescence
                    assert not gate._requested and gate._fact_origin is None
                    assert cleanup._cancel_attempted and not cleanup._work_joined
                    assert held["partial_capture_withdrawn_before_clock"]
                    held["signed_partial_cleanup_capture_checked"] = True

                monkeypatch.setattr(SelectorReadiness, "wait", observed_wait)
                if stage.endswith(("_reserve_countbad", "_reserve_custodybad")):
                    native = SelectorReadiness._native
                    held["reservation_native_checks"] = 0

                    def final_reservation_native(waiter, **options):
                        result = native(waiter, **options)
                        gate = owned._cleanup_owner_snapshot._read_gate_snapshot
                        if (waiter is body._waiter_origin and gate._signed_reservation_attempted
                                and gate._signed_reservation_origin is None
                                and not gate._capture_cause.done()):
                            held["reservation_native_checks"] += 1
                            if held["reservation_native_checks"] == 2:
                                if stage.endswith("_countbad"):
                                    body._committed_snapshot += 1
                                else:
                                    replacement = bytearray(b"untouched synthetic replacement")
                                    body._scope_origin.buffer._buffer = replacement
                                    held["reservation_buffer_replacement"] = replacement
                                held["reservation_body_tail_changed"] = True
                        return result

                    monkeypatch.setattr(SelectorReadiness, "_native", final_reservation_native)
                if "_cause_wake" in stage:
                    wait_native = asyncio.wait
                    async def original_cause_on_registered_wait(futures, **options):
                        cleanup = owned._cleanup_owner_snapshot
                        waiter = body._waiter_origin
                        if (asyncio.current_task() is cleanup._allocations_snapshot[1].task
                                and waiter is not None and waiter._attempted
                                and waiter._handle_snapshot is not None
                                and any(f is cleanup._barriers_snapshot.cause for f in futures)
                                and not held.get("original_body_cause_wake")):
                            held["original_body_cause_wake"] = True
                            RemoteCleanupOwner.request(cleanup)  # actual original-actor first cause
                            assert not cleanup._cancel_attempted
                            assert cleanup._read_gate_snapshot._signed_capture_origin is not None
                            if "_wake_reserve" in stage:
                                gate = cleanup._read_gate_snapshot
                                reservation = gate._signed_reservation_origin
                                assert held["partial_body_sent"] == 13
                                if stage.endswith("bad"):
                                    assert reservation is None and gate._signed_reservation_failed
                                    assert held["reservation_body_tail_changed"]
                                else:
                                    assert reservation is not None
                                    assert not gate._signed_reservation_failed
                                    assert reservation.capture.body.owner is body
                                    assert reservation.capture.body.received == 13
                                    assert reservation.capture.body.committed == 13
                                    assert reservation.wait.owner is waiter
                                    assert reservation.write is cleanup._write_fact_snapshot
                                assert not gate._requested and gate._fact_origin is None
                                held["body_reservation_checked"] = True
                        return await wait_native(futures, **options)
                    monkeypatch.setattr(asyncio, "wait", original_cause_on_registered_wait)
                else:
                    held["body_canceller"] = asyncio.create_task(original_cause())
            if "_wake_reserve_notice" in stage:
                try:
                    await body.receive()
                except FrameError:
                    notice = owned._cleanup_owner_snapshot._read_gate_snapshot._signed_notice_origin
                    assert notice is not None and notice._initialized
                    if stage.endswith(("_notice_native", "_notice_native_advanced",
                                       "_notice_native_consumed", "_notice_native_continued",
                                       "_notice_native_hashlost", *_BODY_FINISH_SUFFIXES)):
                        native_body_ready.set()
                        async with asyncio.timeout_at(end / 1e9):
                            await native_body_queued.wait()
                    assert notice.publish() is True
                    assert notice._future_origin.result() is notice._fact_origin
                    assert notice._fact_origin.stop is body._wake_receipt_origin
                    assert notice._fact_origin.reservation.capture.body.committed == 13
                    assert body._candidate_snapshot is None
                    assert notice.current_stop_for_reader() is notice._fact_origin
                    assert notice.current_stop_for_reader().stop is body._wake_receipt_origin
                    assert body._candidate_snapshot is None and not body._scope_origin.accumulator
                    from hmp_plugin.presentation_credential_cleanup_notice import (
                        SignedCleanupReader,
                        SignedStoppedCursor,
                    )
                    cursor = SignedStoppedCursor.retain(notice)
                    assert cursor.current() is cursor
                    assert cursor._parser._stream_origin is body._initialization_origin[1]
                    assert cursor._parser._stream_origin._received == 13
                    idle_reader = SignedCleanupReader.retain(cursor)
                    idle_fact = idle_reader.current_idle()
                    assert idle_reader.current_idle() is idle_fact
                    assert idle_fact.scope[1] is cursor._parser_origin
                    assert idle_fact.scope[2] == cursor._parser.needed
                    assert body._candidate_snapshot is None and not body._scope_origin.accumulator
                    if stage.endswith(("_notice_native", "_notice_native_advanced",
                                       "_notice_native_consumed", "_notice_native_continued",
                                       "_notice_native_hashlost", *_BODY_FINISH_SUFFIXES)):
                        from hmp_plugin.presentation_credential_cleanup_read import (
                            NativeCleanupRead,
                        )
                        native = NativeCleanupRead.retain(idle_reader)
                        held["native_body_owner"] = native
                        if stage.endswith("_notice_native_continued") or finish_case:
                            receive = NativeCleanupRead._receive

                            def short_body_receive(sock, count):
                                return receive(sock, min(3, count) if (
                                    not finish_case or not native._consume_complete) else count)

                            monkeypatch.setattr(NativeCleanupRead, "_receive",
                                                staticmethod(short_body_receive))
                        observer = NativeCleanupRead.current_for_cleanup

                        def body_native_observer(owner):
                            value = observer(owner)
                            assert owner is native
                            assert value.count == (
                                len(held["terminal_claim_wire"])
                                if body_frame
                                else len(held["body_terminal_auth_wire"])
                                if body_next
                                else len(held["native_body_tail"]) - 3
                                if finish_case
                                else 3
                            )
                            assert body._stream_origin._received == (
                                13 + len(held["native_body_tail"]) if finish_case else
                                19 if stage.endswith("_notice_native_continued") else
                                16 if stage.endswith("_notice_native_consumed") else 13)
                            if body_frame:
                                assert value is native._terminal_frame_origin.done
                                assert value.total_received == (
                                    len(held["native_body_tail"])
                                    + len(held["body_terminal_auth_wire"])
                                    + len(held["body_terminal_frame_wire"])
                                )
                            elif body_next:
                                assert value is native._terminal_origin.fact
                                assert value.total_received == (
                                    len(held["native_body_tail"]) + value.count)
                            elif finish_case:
                                assert value is native._body_finish_origin.fact
                                assert value.total_received == len(held["native_body_tail"])
                            elif stage.endswith("_notice_native_continued"):
                                assert value is native._next_read_origin.fact
                                assert value.total_received == value.total_committed == 6
                            held["body_notice_consumed"] = True
                            native_body_observed.set()
                            return value

                        monkeypatch.setattr(NativeCleanupRead, "current_for_cleanup",
                                            body_native_observer)
                        receipt = native.run_once()
                        assert receipt.count == 3
                        assert native.current_pending() is receipt
                        assert native._pending_origin == held["native_body_tail"][:3]
                        assert body._stream_origin._received == 13
                        assert body._committed == 13 and body._candidate_snapshot is None
                        assert not body._scope_origin.accumulator
                        if stage.endswith(("_notice_native_consumed", "_notice_native_continued",
                                           *_BODY_FINISH_SUFFIXES)):
                            progress = native.consume_pending()
                            assert progress.count == 3 and native._consume_complete
                            assert progress.before.stream is body._initialization_origin[1]
                            assert progress.after.stream is progress.before.stream
                            assert progress.before.received == 13 and progress.after.received == 16
                            assert body._committed == 13 and not body._scope_origin.accumulator
                            assert native._pending_origin is None
                            with pytest.raises(FrameError):
                                native.consume_pending()
                            with pytest.raises(FrameError):
                                native.current_pending()
                            assert not native._failed and not native._unknown
                            held["body_parser_consumed"] = True
                            if stage.endswith("_notice_native_continued") or finish_case:
                                if stage.endswith("_notice_native_finished_seedmutated"):
                                    seed = native._payload_seed_origin
                                    original_source = seed.source
                                    original_source.update(b"uncredited-native-body-hash-change")
                                    with pytest.raises(FrameError):
                                        native.read_and_consume_next()
                                    assert native._failed and native._unknown
                                    assert native._body_finish_allocation is None
                                    assert seed.data._received == 16
                                    assert body._stream_origin is body._initialization_origin[1]
                                    assert body._stream_origin._received == 16
                                    assert body._hash_origin is original_source
                                    assert original_source.hexdigest() != seed.sha256
                                    assert (
                                        body._committed == 13 and not body._scope_origin.accumulator
                                    )
                                    held["body_finish_refused"] = held["body_notice_published"] = (
                                        True
                                    )
                                    raise
                                next_fact = native.read_and_consume_next()
                                assert next_fact.count == (
                                    len(held["native_body_tail"]) - 3 if finish_case else 3)
                                assert next_fact.ordinal == 1
                                assert next_fact.total_received == next_fact.total_committed == (
                                    len(held["native_body_tail"]) if finish_case else 6)
                                assert next_fact.after.stream is body._initialization_origin[1]
                                assert next_fact.after.received == (
                                    13 + len(held["native_body_tail"]) if finish_case else 19)
                                assert body._committed == 13 and not body._scope_origin.accumulator
                                assert native._next_read_origin.pending is None
                                if finish_case:
                                    from hmp_plugin.presentation_credential_stream import (
                                        SignedResultDiscard,
                                    )
                                    body_finish = SignedResultDiscard.finish
                                    held["body_finish_calls"] = 0
                                    def observed_body_finish(parser):
                                        held["body_finish_calls"] += 1
                                        value = body_finish(parser)
                                        if stage.endswith("_lost"):
                                            raise OSError("synthetic body finish ack lost")
                                        if stage.endswith("_ledger"):
                                            class ForeignBodyLedger:
                                                def __getattr__(self, name):
                                                    held["foreign_body_ledger"] = True
                                                    raise AssertionError("foreign body ledger")
                                            native._ledger_origin = ForeignBodyLedger()
                                        if stage.endswith("_result"):
                                            value = replace(value,
                                                frame_length=value.frame_length + 1)
                                        return value
                                    monkeypatch.setattr(SignedResultDiscard, "finish",
                                                        observed_body_finish)
                                    if stage.endswith(("_initial", "_shadow")):
                                        body_fence = NativeCleanupRead._final_socket_fence
                                        def body_finish_fence(owner, scope):
                                            value = body_fence(owner, scope)
                                            if native._body_finish_allocation is not None:
                                                if stage.endswith("_initial"):
                                                    raise FrameError("SYNTHETIC_BODY_FINISH_FENCE")
                                                def foreign_finish():
                                                    held["foreign_body_finish"] = True
                                                    raise AssertionError("foreign body finish")
                                                cursor._parser_origin.finish = foreign_finish
                                            return value
                                        monkeypatch.setattr(NativeCleanupRead,
                                            "_final_socket_fence", body_finish_fence)
                                    if stage.endswith(("_resultcell", "_received")):
                                        from hmp_plugin import (
                                            presentation_credential_cleanup_body as bf,
                                        )

                                        final_hash = bf._HASH_HEX
                                        def body_finish_hash(hasher):
                                            value = final_hash(hasher)
                                            finish = native._body_finish_origin
                                            if (finish is not None and finish.returned
                                                    and not held.get("body_final_hash_changed")):
                                                held["body_final_hash_changed"] = True
                                                class ForeignBodyReturn:
                                                    def __getitem__(self, key):
                                                        held["foreign_body_result_index"] = True
                                                        raise AssertionError("foreign result cell")
                                                    def __eq__(self, other):
                                                        held["foreign_body_received_eq"] = True
                                                        raise AssertionError("foreign received")
                                                foreign = ForeignBodyReturn()
                                                if stage.endswith("_resultcell"):
                                                    finish.result_cell = foreign
                                                else:
                                                    body._stream_origin._received = foreign
                                                    body._stream_origin._received_snapshot = foreign
                                            return value
                                        monkeypatch.setattr(bf, "_HASH_HEX", body_finish_hash)
                                    if stage.endswith("_seal"):
                                        original_progress = native._progress_allocation_origin[1]
                                        class ForeignBodySeal:
                                            def __getattr__(self, name):
                                                held["foreign_body_seal_getter"] = True
                                                raise AssertionError("foreign body seal")
                                        copied = original_progress._replace(after=ForeignBodySeal())
                                        native._progress = native._progress_origin = copied
                                        with pytest.raises(FrameError):
                                            native.finish_body()
                                        assert native._body_finish_allocation is None
                                        assert held["body_finish_calls"] == 0
                                        assert not native._failed
                                        assert "foreign_body_seal_getter" not in held
                                        held["body_finish_refused"] = True
                                    elif finish_failure:
                                        with pytest.raises(FrameError):
                                            native.finish_body()
                                        finish = native._body_finish_origin
                                        assert finish.failed and not finish.complete
                                        assert finish.scope.total == len(held["native_body_tail"])
                                        assert not cursor._parser_origin._buffer_origin
                                        assert body._stream_origin is body._initialization_origin[1]
                                        assert body._committed == 13
                                        assert not body._scope_origin.accumulator
                                        assert held["body_finish_calls"] == (
                                            0 if stage.endswith(("_initial", "_shadow")) else 1)
                                        assert "foreign_body_ledger" not in held
                                        assert "foreign_body_finish" not in held
                                        assert "foreign_body_result_index" not in held
                                        assert "foreign_body_received_eq" not in held
                                        with pytest.raises(FrameError):
                                            native.finish_body()
                                        held["body_finish_refused"] = True
                                    else:
                                        held["body_finish_fact"] = native.finish_body()
                                        assert held["body_finish_fact"].payload_sha256 == (
                                            held["result2_body_sha"])
                                        seed = native._payload_seed_origin
                                        assert body._hash_origin is seed.source
                                        assert seed.source.hexdigest() == seed.sha256
                                        assert seed.data._hasher_origin is not seed.source
                                        assert body._committed == seed.count == 13
                                        assert held["body_finish_fact"].digest.frame_sha256 == (
                                            body._stream_origin._commitment.frame_sha256)
                                        assert body._stream_origin is body._initialization_origin[1]
                                        assert body._committed == 13
                                        assert not body._scope_origin.accumulator
                                        for action in (native.finish_body,
                                                       native.read_and_consume_next):
                                            with pytest.raises(FrameError):
                                                action()
                                        if body_next:
                                            next_scope = native.begin_terminal()
                                            assert (
                                                next_scope.predecessor is held["body_finish_fact"]
                                            )
                                            for ordinal in (1, 2):
                                                assert (
                                                    native.read_terminal_auth().ordinal == ordinal
                                                )
                                            next_auth = native.finish_terminal_auth()
                                            if body_frame:
                                                terminal_scope = native.start_terminal_frame()
                                                assert terminal_scope.receipt is next_auth
                                                ordinal = 0
                                                while terminal_scope.parser.needed:
                                                    ordinal += 1
                                                    fact = native.read_terminal_frame()
                                                    assert fact.ordinal == ordinal
                                                terminal_data = native.finish_terminal_frame()
                                                assert (
                                                    terminal_data.data.terminal
                                                    == held["terminal_claim_wire"]
                                                )
                                                if stage.endswith("_nextframe_claimslot"):
                                                    from hmp_plugin import (
                                                        presentation_credential_cleanup_claim as cc,
                                                    )
                                                    real_hash, calls = cc._SHA256, []
                                                    foreign_calls = []

                                                    class ForeignClaimCell:
                                                        def __getitem__(self, key):
                                                            foreign_calls.append(key)
                                                            raise AssertionError("foreign indexing")

                                                    def drift_claim_slot(value):
                                                        calls.append(None)
                                                        result = real_hash(value)
                                                        if len(calls) == 3:
                                                            native._claim_attempt_cell = (
                                                                ForeignClaimCell()
                                                            )
                                                        return result

                                                    monkeypatch.setattr(
                                                        cc, "_SHA256", drift_claim_slot
                                                    )
                                                if stage.endswith(("_nextframe_badclaim",
                                                                   "_nextframe_claimslot")):
                                                    with pytest.raises(FrameError):
                                                        native.correlate_terminal_claim()
                                                    assert native._claim_attempt_origin.failed
                                                    assert not native._claim_attempt_origin.complete
                                                    if stage.endswith("_nextframe_claimslot"):
                                                        assert foreign_calls == []
                                                else:
                                                    async def wrong_claim_actor():
                                                        with pytest.raises(FrameError):
                                                            native.correlate_terminal_claim()

                                                    await asyncio.create_task(wrong_claim_actor())
                                                    assert native._claim_attempt is None
                                                    assert native._claim_attempt_origin is None
                                                    assert native._claim_attempt_cell is None
                                                    correlated = native.correlate_terminal_claim()
                                                    assert (
                                                        correlated.handoff.claim.result_sha256
                                                        == (held["result2_body_sha"])
                                                    )
                                                    assert correlated.predecessor is (
                                                        held["body_finish_fact"])
                                                    assert "no-budget-adoption" in repr(correlated)
                                                    budget_type = budget_api.CancellationBudget
                                                    budget = native._scope_origin.idle_scope[3]
                                                    before_end = budget_type.inspect(budget)[
                                                        2
                                                    ]

                                                    async def wrong_budget_actor():
                                                        with pytest.raises((FrameError,
                                                                            AuthorityRefusalError)):
                                                            native.inherit_terminal_cleanup()

                                                    await asyncio.create_task(wrong_budget_actor())
                                                    assert native._budget_publication is None
                                                    if stage.endswith(
                                                        (
                                                            "_budgetlost",
                                                            "_budgetdrift",
                                                            "_budgetfuture",
                                                            "_budgetexpired",
                                                            "_budgetslot",
                                                        )
                                                    ):
                                                        real_inherit, writes = cb._INHERIT, []
                                                        foreign_calls = []

                                                        class ForeignBudgetRefs:
                                                            def __getitem__(self, key):
                                                                foreign_calls.append(key)
                                                                raise AssertionError("foreign refs")

                                                        def lost_budget_ack(owner, window, now):
                                                            writes.append(owner)
                                                            real_inherit(owner, window, now)
                                                            if stage.endswith("_budgetdrift"):
                                                                reservation = (
                                                                    correlated.scope.idle_scope[
                                                                        0
                                                                    ].reservation
                                                                )
                                                                cleanup = (
                                                                    reservation.capture.cleanup
                                                                )
                                                                replacement = ForeignBudgetRefs()
                                                                cleanup._refs = replacement
                                                                cleanup._refs_snapshot = replacement
                                                                return None
                                                            if stage.endswith("_budgetslot"):
                                                                native._budget_publication_cell = (
                                                                    ForeignBudgetRefs())
                                                            if stage.endswith("_budgetlost"):
                                                                raise FrameError(
                                                                    "SYNTHETIC_BUDGET_ACK_LOST")
                                                            return None

                                                        monkeypatch.setattr(
                                                            cb, "_INHERIT", lost_budget_ack
                                                        )
                                                        with pytest.raises((FrameError,
                                                                            AuthorityRefusalError)):
                                                            native.inherit_terminal_cleanup()
                                                        _, _, actual_end, broken = (
                                                            budget_type.inspect(budget))
                                                        assert broken and actual_end == min(
                                                            before_end, held["terminal_sender_end"])
                                                        expected_writes = (
                                                            [] if stage.endswith("_budgetfuture")
                                                            else [budget])
                                                        assert writes == expected_writes
                                                        with pytest.raises((FrameError,
                                                                            AuthorityRefusalError)):
                                                            native.inherit_terminal_cleanup()
                                                        assert writes == expected_writes
                                                        assert foreign_calls == []
                                                        held["body_finish_refused"] = True
                                                        held["body_notice_published"] = True
                                                        raise FrameError(
                                                            "SYNTHETIC_BUDGET_NO_RETRY"
                                                        ) from None
                                                    budget_fact = native.inherit_terminal_cleanup()
                                                    assert budget_fact.budget is budget
                                                    assert budget_fact.previous_end == before_end
                                                    sender_end = held.get(
                                                        "terminal_sender_end", before_end
                                                    )
                                                    assert budget_fact.effective_end == min(
                                                        before_end, sender_end)
                                                    assert budget_type.inspect(budget)[
                                                        2
                                                    ] == (budget_fact.effective_end)
                                                    assert "no-ACK" in repr(budget_fact)
                                                    with pytest.raises(FrameError):
                                                        native.inherit_terminal_cleanup()
                                                with pytest.raises(FrameError):
                                                    native.correlate_terminal_claim()
                                                assert terminal_data.total_received == (
                                                    next_auth.total_received
                                                    + len(held["body_terminal_frame_wire"]))
                                            assert next_auth.count == len(
                                                held["body_terminal_auth_wire"]
                                            )
                                            assert body._committed == 13
                                            assert not body._scope_origin.accumulator
                        if stage.endswith("_notice_native_hashlost"):
                            from hmp_plugin.presentation_credential_stream import (
                                SignedResultDiscard,
                            )
                            feed = SignedResultDiscard.feed

                            def lost_hash_return(parser, chunk):
                                feed(parser, chunk)
                                raise FrameError("SYNTHETIC_POST_HASH_ACK_LOST")

                            monkeypatch.setattr(SignedResultDiscard, "feed", lost_hash_return)
                            with pytest.raises(FrameError):
                                native.consume_pending()
                            assert body._stream_origin._received == 16
                            assert native._native_count_allocation_origin[1] == 3
                            assert native._consume_attempted and not native._consume_returned
                            assert native._progress_origin is None
                            assert native._pending_origin is None and native._unknown
                            with pytest.raises(FrameError):
                                native.consume_pending()
                            held["body_hash_ack_lost"] = True
                        elif not finish_failure:
                            async with asyncio.timeout_at(end / 1e9):
                                await native_body_observed.wait()
                        if stage.endswith("_notice_native_advanced"):
                            from hmp_plugin.presentation_credential_cleanup_notice import (
                                SignedReadNotice,
                            )
                            from hmp_plugin.presentation_credential_stream import (
                                SignedResultDiscard,
                            )
                            stop = body._wake_receipt_origin
                            pending = native._pending_origin
                            SignedResultDiscard.feed(cursor._parser_origin, pending)
                            assert body._stream_origin is body._initialization_origin[1]
                            assert body._stream_origin._received == 16
                            assert body._committed == 13 and not body._scope_origin.accumulator
                            assert NativeResultBodyOwner._wake_binding_metadata(body, stop) is stop
                            assert SignedReadNotice._stop_binding_metadata(notice)[0] is stop
                            # Historical wake continuity is no current digest proof.
                            with pytest.raises(FrameError):
                                NativeResultBodyOwner._wake_retirement_metadata(body, stop)
                            with pytest.raises(FrameError):
                                SignedReadNotice._stop_metadata(notice)
                            with pytest.raises(FrameError):
                                native.current_pending()
                            assert native._native_count_allocation_origin[1] == 3
                            assert native._pending_origin is None
                            held["body_progress_boundary_refused"] = True
                            pending = None
                        held["body_notice_published"] = True
                        raise
                    with pytest.raises(FrameError):
                        notice.current_stop_for_cleanup()  # sender cannot borrow cleanup actor
                    checked = asyncio.Event()
                    remaining = RemoteCleanupOwner._remaining
                    reading_notice = False

                    def body_cleanup_probe(cleanup):
                        nonlocal reading_notice
                        value = remaining(cleanup)
                        if (cleanup is owned._cleanup_owner_snapshot
                                and asyncio.current_task() is cleanup._allocations_snapshot[0].task
                                and not reading_notice and not held.get("body_notice_consumed")):
                            reading_notice = True
                            try:
                                fact = notice.current_stop_for_cleanup()
                                assert fact is notice._fact_origin
                                assert fact.stop is body._wake_receipt_origin
                                assert not cleanup._work_joined
                                assert not cleanup._allocations_snapshot[1].task.done()
                                with pytest.raises(AuthorityRefusalError):
                                    channel = body._scope_origin.envelope_scope.write_scope.channel
                                    RemoteCleanupOwner._cancel_actor(cleanup, channel)
                                assert not cleanup._cancel_write_attempted
                                held["body_notice_consumed"] = True
                                checked.set()
                            finally:
                                reading_notice = False
                        return value

                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining", body_cleanup_probe)
                    async with asyncio.timeout_at(end / 1e9):
                        await checked.wait()
                    # The original native envelope binding, not the digest's
                    # mutable aliases, selects the expected identity.
                    from hmp_plugin.presentation_broker_codec import BrokerBinding
                    remaining_for_binding = RemoteCleanupOwner._remaining
                    original_binding = body._scope_origin.envelope_scope.write_scope.intent.binding

                    def body_binding_clock_drift(cleanup):
                        value = remaining_for_binding(cleanup)
                        if (asyncio.current_task() is cleanup._allocations_snapshot[1].task
                                and not held.get("body_cursor_binding_changed")):
                            held["body_cursor_binding_changed"] = True
                            replacement = BrokerBinding(
                                original_binding.iid, original_binding.listener,
                                original_binding.broker, original_binding.channel,
                                original_binding.operation)
                            cursor._parser._binding = cursor._parser._binding_origin = replacement
                            stream = cursor._parser._stream_origin
                            stream._binding = stream._binding_origin = replacement
                            assert replacement == original_binding
                            assert replacement is not original_binding
                        return value

                    monkeypatch.setattr(RemoteCleanupOwner, "_remaining", body_binding_clock_drift)
                    with pytest.raises(FrameError):
                        idle_reader.current_idle()
                    assert held["body_cursor_binding_changed"] and cursor._failed
                    assert idle_reader._failed
                    assert notice._unknown and owned._cleanup_owner_snapshot._unknown
                    with pytest.raises(FrameError):
                        notice.publish()
                    held["body_notice_published"] = True
                    raise
            assert await body.receive() is True
            assert body._validated and body._candidate_snapshot[1] == image()
            assert body.current_candidate() is body._fact_snapshot
            async def foreign_candidate_reader():
                with pytest.raises(FrameError):
                    body.current_candidate()
            await asyncio.create_task(foreign_candidate_reader())
            assert body.current_candidate() is body._fact_snapshot
            if body_terminal:
                from hmp_plugin.presentation_credential_terminal_read import NativeTerminalReceiver

                async def wrong_terminal_actor():
                    with pytest.raises(FrameError):
                        NativeTerminalReceiver.retain(body)

                await asyncio.create_task(wrong_terminal_actor())
                assert body._terminal_reader_origin is None
                reader = NativeTerminalReceiver.retain(body)
                held["normal_terminal_reader"] = reader
                from hmp_plugin import presentation_credential_terminal_read as nr
                foreign_terminal_calls = []
                original_auth = reader._auth
                original_frame = None

                class ForeignNormalCredit:
                    def __getitem__(self, key):
                        foreign_terminal_calls.append(key)
                        raise AssertionError("foreign normal credit")

                if stage.endswith("_wait"):
                    from hmp_plugin.presentation_readiness import SelectorReadiness
                    actual_wait = SelectorReadiness.wait

                    async def observed_terminal_wait(interest, cutoff, **options):
                        if interest is reader._waiter:
                            assert cutoff == reader._scope_origin.write.intent.end_ns
                            held["normal_terminal_waited"] = True
                            terminal_can_send.set()
                        return await actual_wait(interest, cutoff, **options)

                    monkeypatch.setattr(SelectorReadiness, "wait", observed_terminal_wait)
                if stage.endswith("_authcredit"):
                    actual_feed = nr.SignedCleanupAuthPrefix.feed

                    def corrupt_auth_credit(parser, chunk):
                        actual_feed(parser, chunk)
                        if parser is original_auth:
                            reader._credit = reader._credit_origin = ForeignNormalCredit()

                    monkeypatch.setattr(nr.SignedCleanupAuthPrefix, "feed", corrupt_auth_credit)
                if stage.endswith(("_framecredit", "_frameswap")):
                    actual_feed = nr.CommittedFrameDiscard.feed

                    def corrupt_frame_credit(parser, chunk):
                        nonlocal original_frame
                        actual_feed(parser, chunk)
                        if parser is reader._frame:
                            original_frame = parser
                            if stage.endswith("_framecredit"):
                                reader._credit = reader._credit_origin = ForeignNormalCredit()
                            else:
                                replacement = nr.CommittedFrameDiscard(reader._checked,
                                    binding=reader._scope_origin.write.intent.binding,
                                    phase="TERMINAL", sequence=2)
                                replacement._buffer_origin.extend(b"synthetic replacement")
                                held["normal_foreign_frame"] = replacement
                                reader._frame = replacement
                                reader._frame_cell = (reader, replacement)

                    monkeypatch.setattr(nr.CommittedFrameDiscard, "feed", corrupt_frame_credit)
                if stage.endswith("_finishswap"):
                    actual_finish = nr.CommittedFrameDiscard.finish

                    def replace_after_finish(parser):
                        nonlocal original_frame
                        result = actual_finish(parser)
                        if parser is reader._frame:
                            original_frame = parser
                            replacement = nr.CommittedFrameDiscard(reader._checked,
                                binding=reader._scope_origin.write.intent.binding,
                                phase="TERMINAL", sequence=2)
                            replacement._buffer_origin.extend(b"synthetic replacement")
                            held["normal_foreign_frame"] = replacement
                            reader._frame = replacement
                            reader._frame_cell = (reader, replacement)
                        return result

                    monkeypatch.setattr(nr.CommittedFrameDiscard, "finish", replace_after_finish)
                if stage.endswith("_finalkey"):
                    actual_hash = nr._SHA256

                    def retire_after_normal_hash(value):
                        result = actual_hash(value)
                        if reader._frame_done is not None:
                            keys["gateway"].retire()
                        return result

                    monkeypatch.setattr(nr, "_SHA256", retire_after_normal_hash)
                if body_terminal_fault:
                    try:
                        await reader.receive()
                    except FrameError:
                        assert reader._failed and not reader._complete and reader._fact is None
                        assert foreign_terminal_calls == []
                        assert not original_auth._buffer_origin
                        if original_frame is not None:
                            assert not original_frame._buffer_origin
                            assert not original_frame._terminal_origin
                        if stage.endswith(("_frameswap", "_finishswap")):
                            assert (
                                held["normal_foreign_frame"]._buffer_origin
                                == b"synthetic replacement"
                            )
                        assert body._candidate_snapshot is None
                        assert body._scope_origin.job.result is None
                        held["normal_terminal_refused"] = True
                        raise
                    raise AssertionError("normal terminal fault escaped")
                terminal_fact = await reader.receive()
                async def wrong_correlation_actor():
                    with pytest.raises(FrameError):
                        reader.current_correlation()
                await asyncio.create_task(wrong_correlation_actor())
                assert not reader._failed and reader._complete
                assert reader.current_correlation() is terminal_fact
                if stage.endswith(("_factpair", "_factcallback", "_factcounter")):
                    if stage.endswith("_factpair"):
                        reader._fact = nr._Fact(*terminal_fact)
                        reader._fact_cell = (reader, reader._fact)
                    elif stage.endswith("_factcounter"):
                        class ForeignNormalCount:
                            def __eq__(self, other):
                                foreign_terminal_calls.append("counter equality")
                                raise AssertionError("foreign counter equality")

                        reader._received = reader._received_origin = ForeignNormalCount()
                    else:
                        actual_hash = nr._SHA256

                        def replace_correlation_during_current(value):
                            result = actual_hash(value)
                            reader._fact = reader._fact_origin = nr._Fact(*terminal_fact)
                            reader._fact_cell = reader._fact_cell_origin = (reader, reader._fact)
                            held["normal_fact_callback_replaced"] = True
                            return result

                        monkeypatch.setattr(nr, "_SHA256", replace_correlation_during_current)
                    with pytest.raises(FrameError):
                        reader.current_correlation()
                    if stage.endswith("_factcallback"):
                        assert held["normal_fact_callback_replaced"]
                    assert foreign_terminal_calls == []
                    assert reader._failed and not reader._complete
                    assert reader._fact is None and body._candidate_snapshot is None
                    assert body._scope_origin.job.result is None
                    held["normal_terminal_refused"] = True
                    raise FrameError("synthetic paired correlation replacement")
                held["normal_terminal_fact"] = terminal_fact
                if stage.endswith("_wait"):
                    assert held["normal_terminal_waited"]
                    assert reader._waiter._retired and not reader._waiter._unknown
                assert (
                    terminal_fact.handoff.claim.result_sha256
                    == body._fact_snapshot.body_wire_sha256
                )
                assert terminal_fact.handoff.claim.operation_kind == (
                    "AVATAR" if stage.endswith("_avatar") else "METADATA")
                assert body.current_candidate() is body._fact_snapshot
                assert not body._adopted and body._scope_origin.job.result is None
                with pytest.raises(FrameError):
                    await reader.receive()
                with pytest.raises(FrameError):
                    NativeTerminalReceiver.retain(body)
            assert body._scope_origin.job.result is None
            assert body._scope_origin.job.remote_result_token is None
            assert not body._scope_origin.accumulator
            from hmp_plugin.presentation_jobs import RemotePhase
            assert owned._job_origin_snapshot.remote_phase is RemotePhase.GO_SENT
            if "_body_adopt" in stage:
                if stage.endswith("_wrong_actor"):
                    async def wrong_adoption_actor():
                        with pytest.raises(FrameError):
                            body.adopt()
                    await asyncio.create_task(wrong_adoption_actor())
                    assert not body._adoption_attempted and not body._failed
                if stage.endswith(("_pending_pair", "_attempt")):
                    from hmp_plugin.presentation_clock import NativeClockOwner
                    from hmp_plugin.presentation_credential_result_body import _BodyAdoption
                    sample_adoption = NativeClockOwner.sample
                    def replace_pending(clock):
                        now = sample_adoption(clock)
                        if body._adoption_origin is not None:
                            if stage.endswith("_attempt"):
                                body._adoption_attempted = False
                            else:
                                prior = body._adoption_origin
                                body._adoption = body._adoption_origin = _BodyAdoption(
                                    prior.mint, body, prior.scope, prior.candidate_fact, object())
                            held["pending_adoption_replaced"] = True
                        return now
                    monkeypatch.setattr(NativeClockOwner, "sample", replace_pending)
                    with pytest.raises(FrameError):
                        body.adopt()
                    assert held["pending_adoption_replaced"]
                    assert body._failed and body._retired
                    assert body._scope_origin.job.result is None
                    assert body._scope_origin.job.remote_result_token is None
                else:
                    assert body.adopt() is True
                    assert body.current_adopted() is body._adoption_origin
                    assert body._scope_origin.job.result is body._candidate_snapshot
                    assert body._scope_origin.job.remote_result_token is body._token_origin
                    assert body._scope_origin.job.remote_phase is RemotePhase.RESULT_VALIDATED
                    assert owned._result_owner_snapshot is None  # no legacy owner masquerade
                    with pytest.raises(FrameError):
                        body.adopt()
                    assert body.current_adopted() is body._adoption_origin
                    if stage.endswith("_wrong_actor"):
                        async def wrong_adopted_reader():
                            with pytest.raises(FrameError):
                                body.current_adopted()
                        await asyncio.create_task(wrong_adopted_reader())
                        assert body.current_adopted() is body._adoption_origin
                    if stage.endswith("_pair"):
                        from hmp_plugin.presentation_credential_result_body import _BodyAdoption
                        prior = body._adoption_origin
                        token = object()
                        body._token = body._token_origin = token
                        body._adoption = body._adoption_origin = _BodyAdoption(
                            prior.mint, body, prior.scope, prior.candidate_fact, token)
                        body._scope_origin.job.remote_result_token = token
                    if stage.endswith("_fact"):
                        from hmp_plugin import presentation_credential_result_body as body_module
                        check = body_module.check_commitment
                        class ForeignFact:
                            def __getattribute__(self, name):
                                held["foreign_adopted_fact_accessed"] = True
                                raise AssertionError("foreign adopted fact accessed")
                        def replaced_fact(*args, **kwargs):
                            checked = check(*args, **kwargs)
                            body._fact = body._fact_snapshot = ForeignFact()
                            return checked
                        monkeypatch.setattr(body_module, "check_commitment", replaced_fact)
                    if stage.endswith("_key"):
                        keys["gateway"].retire()
                    if stage.endswith("_header"):
                        body._candidate_snapshot[0]["outcome"] = "MUTATED"
                    if stage.endswith("_tail_token"):
                        from hmp_plugin import presentation_credential_result_body as body_module
                        timeout = body_module._TIMEOUT
                        def changed_timeout(sock):
                            value = timeout(sock)
                            if sock is body._scope_origin.envelope_scope.write_scope.sock:
                                body._scope_origin.job.remote_result_token = object()
                                held["adopted_tail_token_changed"] = True
                            return value
                        monkeypatch.setattr(body_module, "_TIMEOUT", changed_timeout)
                    if stage.endswith(("_key", "_header", "_tail_token", "_pair", "_fact")):
                        with pytest.raises(FrameError) as adopted_refusal:
                            body.current_adopted()
                        assert adopted_refusal.value.__context__ is None
                        assert body._failed and body._retired
                        assert body._candidate_snapshot is None and body._adoption_origin is None
                        assert body._adoption_allocation_origin is None
                        assert body._scope_origin.job.result is None
                        assert body._scope_origin.job.remote_result_token is None
                        if stage.endswith("_tail_token"):
                            assert held["adopted_tail_token_changed"]
                        if stage.endswith("_fact"):
                            assert "foreign_adopted_fact_accessed" not in held
            if "_adopt_notice" in stage:
                from hmp_plugin import presentation_credential_result_body as body_module
                from hmp_plugin.presentation_remote_cleanup import _FUTURE
                publish = RemoteCleanupOwner._publish_write_quiescence
                def published_go(owner):
                    result = publish(owner)
                    if (owner is owned._cleanup_owner_snapshot and body._adopted
                            and not body._notice_attempted and not owner._intent
                            and owner._go_notice_fact is not None):
                        future = owner._result_barrier_snapshot[0]
                        loop = body._scope_origin.envelope_scope.write_scope.loop
                        expected_failure = stage.endswith(("_scheduler", "_future", "_ambiguous"))
                        changed_dispatch = False
                        saved_thread, saved_debug = loop._thread_id, loop._debug
                        timeout = body_module._TIMEOUT
                        def final_dispatch(sock):
                            nonlocal changed_dispatch
                            value = timeout(sock)
                            if (body._notice_snapshot is not None and not changed_dispatch
                                    and sock is body._scope_origin.envelope_scope.write_scope.sock):
                                changed_dispatch = True
                                if stage.endswith("_scheduler"):
                                    def foreign_schedule(*args, **kwargs):
                                        held["foreign_notice_dispatch"] = True
                                        raise AssertionError("foreign scheduler dispatched")
                                    loop.call_soon = foreign_schedule
                                if stage.endswith("_future"):
                                    def foreign_future(*args, **kwargs):
                                        held["foreign_notice_dispatch"] = True
                                        raise AssertionError("foreign Future dispatched")
                                    future.add_done_callback = foreign_future
                                if stage.endswith("_ambiguous"):
                                    import threading
                                    loop._debug = True
                                    loop._thread_id = threading.get_ident() + 1
                            return value
                        if expected_failure:
                            # A real native Future callback makes native scheduling observable.
                            if stage.endswith("_ambiguous"):
                                _FUTURE.add_done_callback(future, lambda _: None)
                            monkeypatch.setattr(body_module, "_TIMEOUT", final_dispatch)
                        try:
                            if expected_failure:
                                with pytest.raises(FrameError) as notice_refusal:
                                    body.notify()
                                assert notice_refusal.value.__context__ is None
                                assert changed_dispatch and body._notice_attempted
                                assert body._failed and body._retired
                                assert owner._result_token is None
                                assert body._notice_snapshot is None
                                assert body._scope_origin.job.result is None
                                assert "foreign_notice_dispatch" not in held
                                assert _FUTURE.done(future) is stage.endswith("_ambiguous")
                                if stage.endswith("_ambiguous"):
                                    assert _FUTURE.result(future) is True
                                with pytest.raises(FrameError):
                                    body.notify()
                                held["signed_notice_refused"] = True
                            else:
                                if stage.endswith("_actors"):
                                    with pytest.raises(AuthorityRefusalError):
                                        body.current_notice()  # work is not the caller
                                assert body.notify() is True
                                assert body._notified
                                assert owner._result_token is body._token_origin
                                assert owned._result_owner_snapshot is None
                                with pytest.raises(FrameError):
                                    body.notify()  # original work cannot notify twice
                                held["signed_notice_published"] = True
                        finally:
                            # Restore only fixture dispatch after refusal, without replay/credit.
                            loop._thread_id, loop._debug = saved_thread, saved_debug
                            if "call_soon" in vars(loop):
                                del loop.call_soon
                            if changed_dispatch and stage.endswith("_future"):
                                del future.add_done_callback
                            monkeypatch.setattr(body_module, "_TIMEOUT", timeout)
                    return result
                monkeypatch.setattr(RemoteCleanupOwner, "_publish_write_quiescence", published_go)
            from hmp_plugin.presentation_clock import NativeClockOwner
            sample = NativeClockOwner.cleanup_sample

            def original_withdrawal(clock):
                if (clock is owned._clock_owner_snapshot
                        and owned._cleanup_owner_snapshot._intent):
                    if stage in (
                            "go_relay_result_sign_write_body_wrong_actor",
                            "go_relay_result_sign_write_body_adopt",
                            "go_relay_result_sign_write_body_adopt_wrong_actor",
                            "go_relay_result_sign_write_body_adopt_notice",
                            "go_relay_result_sign_write_body_adopt_notice_actors"):
                        from hmp_plugin.presentation_credential_cleanup_capture import (
                            inspect_signed_cleanup,
                        )
                        cleanup = owned._cleanup_owner_snapshot
                        gate = cleanup._read_gate_snapshot
                        capture = gate._signed_capture_origin
                        assert capture is not None
                        assert inspect_signed_cleanup(capture, gate, cleanup) is capture
                        assert capture.receiver is envelope
                        assert capture.scope is envelope._scope_origin
                        assert capture.body.owner is body and capture.body.validated
                        assert capture.body.scope is body._scope_origin
                        assert capture.body.received == body._received_snapshot
                        assert capture.body.allocation is body._initialization_origin
                        assert capture.envelope.complete and not capture.envelope.active
                        assert capture.work is cleanup._allocations_snapshot[1]
                        assert not gate._requested and gate._fact_origin is None
                        assert not gate._activated  # frozen DATA, not cooperative permission
                        held["signed_cleanup_capture_checked"] = True
                    assert body._retired and body._candidate_snapshot is None
                    assert body._fact_snapshot is None
                    assert body._adoption_origin is None and body._token_origin is None
                    assert body._notice_snapshot is None
                    assert (body._scope_origin.envelope_scope.write_scope.refs[0]
                            ._result_token is None)
                    assert body._scope_origin.job.result is None
                    assert body._scope_origin.job.remote_result_token is None
                    with pytest.raises(FrameError):
                        body.current_candidate()
                    assert not body._scope_origin.accumulator
                    held["body_retired_before_clock"] = True
                return sample(clock)

            monkeypatch.setattr(NativeClockOwner, "cleanup_sample", original_withdrawal)
            if stage == "go_relay_result_sign_write_body_avatar":
                current = NativeResultBodyOwner._current
                class ForeignCommitment:
                    def __getitem__(self, key):
                        held["foreign_commitment_indexed"] = True
                        raise AssertionError("foreign commitment indexing executed")
                def substituted_current(owner):
                    scope = current(owner)
                    if owner is body:
                        owner._stream_origin._commitment_values = ForeignCommitment()
                    return scope
                monkeypatch.setattr(NativeResultBodyOwner, "_current", substituted_current)
                with pytest.raises(FrameError):
                    body.current_candidate()
                assert "foreign_commitment_indexed" not in held
                assert body._failed and body._retired
                assert body._candidate_snapshot is None and body._fact_snapshot is None
            if stage == "go_relay_result_sign_write_body":
                # Paired candidate aliases do not authorize mutated validated metadata.
                body._candidate_snapshot[0]["outcome"] = "MUTATED"
                with pytest.raises(FrameError) as candidate_refusal:
                    body.current_candidate()
                assert candidate_refusal.value.__context__ is None
                trace = candidate_refusal.value.__traceback__
                while trace is not None:
                    if trace.tb_frame.f_code.co_name == "current_candidate":
                        assert all(trace.tb_frame.f_locals[k] is None
                                   for k in ("fact", "s", "checked"))
                    assert trace.tb_frame.f_code.co_name != "_candidate_local"
                    trace = trace.tb_next
                assert body._failed and body._retired
                assert body._candidate_snapshot is None and body._fact_snapshot is None
                with pytest.raises(FrameError):
                    body.current_candidate()
                assert body._scope_origin.job.result is None
                assert body._scope_origin.job.remote_result_token is None
            return result

        monkeypatch.setattr(RemoteOperationOwner, "_go_exchange", original_signed_body)

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
            if body_fault:
                with pytest.raises((FrameError, AuthorityRefusalError, asyncio.CancelledError)):
                    await remote.go()
                if "gateway_body" not in held and broker_task.done():
                    broker_task.result()  # preserve actual synthetic sender failure
                body = held["gateway_body"]
                assert body._retired and body._candidate_snapshot is None
                assert body._fact_snapshot is None and not body._scope_origin.accumulator
                assert remote._job_origin_snapshot.result is None
                assert cleanup._result_token is None
                if "_cause_wake" in stage:
                    task = cleanup._allocations_snapshot[1].task
                    if "_wake_reserve_notice" in stage:
                        async with asyncio.timeout_at(end / 1e9):
                            outcome = (await asyncio.gather(task, return_exceptions=True))[0]
                        if (not held.get("body_notice_published")
                                and isinstance(outcome, BaseException)):
                            raise outcome  # preserve actual original actor/fixture error
                        if stage.endswith("_notice_native_hashlost"):
                            assert held["body_hash_ack_lost"] and not native_body_observed.is_set()
                        elif stage.endswith(("_budgetlost", "_budgetdrift", "_budgetfuture",
                                             "_budgetexpired", "_budgetslot")):
                            assert held["body_finish_refused"]
                            step = held["native_body_owner"]._budget_publication_origin
                            assert step.failed
                            assert step.attempted is not stage.endswith("_budgetfuture")
                            assert step.returned is stage.endswith(
                                ("_budgetdrift", "_budgetexpired", "_budgetslot")
                            )
                            assert not step.complete
                        elif finish_failure:
                            assert held["body_finish_refused"] and not native_body_observed.is_set()
                        else:
                            assert held["body_notice_consumed"]
                        if stage.endswith(("_notice_native", "_notice_native_advanced",
                                       "_notice_native_consumed", "_notice_native_continued",
                                       "_notice_native_hashlost", *_BODY_FINISH_SUFFIXES)):
                            native = held["native_body_owner"]
                            assert native._received == 3 and native._count_known
                            assert native._pending_origin is None
                            assert native._pending_allocation_origin is None
                            assert native._failed and native._unknown and cleanup._unknown
                    assert held["original_body_cause_wake"] and task.done()
                    assert not task.cancelled() and task.cancelling() == 0
                    assert body._cancel_receipt_snapshot is None
                    assert not cleanup._cancel_attempted
                    assert not cleanup._read_gate_snapshot._requested
                    assert cleanup._read_gate_snapshot._fact_origin is None
                    if "_wake_reserve" in stage:
                        assert held["body_reservation_checked"]
                        if "_wake_reserve_notice" in stage:
                            assert held["body_notice_published"]
                        if stage.endswith("_custodybad"):
                            assert held["reservation_buffer_replacement"] == (
                                b"untouched synthetic replacement")
                    async with asyncio.timeout(3):
                        await asyncio.shield(cleanup._allocations_snapshot[0].task)
                    if stage.endswith(
                        (
                            "_notice_native_advanced",
                            "_notice_native_consumed",
                            "_notice_native_continued",
                            "_notice_native_hashlost",
                            *_BODY_FINISH_SUFFIXES,
                        )
                    ):
                        if stage.endswith(("_notice_native_consumed", "_notice_native_continued",
                                           *_BODY_FINISH_SUFFIXES)):
                            assert held["body_parser_consumed"]
                        elif stage.endswith("_notice_native_hashlost"):
                            assert held["body_hash_ack_lost"]
                        else:
                            assert held["body_progress_boundary_refused"]
                        assert body._wake_receipt_origin is not None
                        with pytest.raises(FrameError):
                            NativeResultBodyOwner._released(body, body._scope_origin.envelope)
                        assert body._io_unknown  # no historical release credit after raw feed
                    elif stage.endswith("bad"):
                        assert body._io_unknown
                        if "_release" in stage:
                            assert body._wake_receipt_origin is not None
                        else:
                            assert body._wake_receipt_origin is None
                        with pytest.raises(FrameError):
                            NativeResultBodyOwner._released(body, body._scope_origin.envelope)
                        if any(name in stage for name in (
                                "_tailbad", "_waiterbad", "_releasebad", "_releasewaiterbad")):
                            assert held["body_wake_tail_changed"]
                        if stage.endswith("_subclassbad"):
                            assert "foreign_wake_getter" not in held
                    else:
                        assert body._wake_receipt_origin is not None and not body._io_unknown
                        NativeResultBodyOwner._released(body, body._scope_origin.envelope)
                if stage.endswith("_avatar_revision"):
                    assert held["revision_claim_codec_valid"]
                    assert body._finish_attempted
                    assert body._received == body._scope_origin.envelope_fact.header.body_length
                    assert body._scope_origin.expected == expected_avatar_sha
                if "_body_cancel" in stage and "_release_" not in stage and stage.endswith(
                        ("_stale", "_pair", "_progress", "_custody", "_waiter")):
                    assert body._io_unknown and body._cancel_receipt_snapshot is None
                if "_release_" in stage:
                    await asyncio.gather(cleanup._allocations_snapshot[1].task,
                                         return_exceptions=True)
                    with pytest.raises(FrameError):
                        NativeResultBodyOwner._released(body, body._scope_origin.envelope)
                    assert body._io_unknown and body._cancel_receipt_snapshot is not None
                if "_tail_" in stage or "_release_" in stage:
                    assert held["body_retirement_tail_changed"]
                if stage.endswith("_body_cancel"):
                    assert not body._io_unknown and body._cancel_receipt_snapshot is not None
                if stage.endswith("_custody"):
                    assert held["foreign_accumulator"] == b"untouched"
                if stage.endswith("_stream_pair"):
                    assert held["body_replacement"]._received == 0
                if stage.endswith("_hash_pair"):
                    import hashlib
                    assert held["body_replacement"].hexdigest() == hashlib.sha256().hexdigest()
                return  # no private candidate or remote/native release after refusal
            try:
                assert await remote.go() is True
            except BaseException:
                if stage.startswith("go_relay_result_sign_write_body"):
                    task = cleanup._allocations_snapshot[1].task
                    if task.done() and not task.cancelled():
                        task.result()
                raise
            if "_adopt_notice" in stage:
                body = held["gateway_body"]
                if stage.endswith(("_scheduler", "_future", "_ambiguous")):
                    assert held["signed_notice_refused"]
                    assert not cleanup._result_awaited
                    assert cleanup._result_token is None
                    assert not remote._job_origin_snapshot.credit_released
                    if stage.endswith("_ambiguous"):
                        with pytest.raises((FrameError, AuthorityRefusalError)):
                            await remote.result_ready()
                        assert cleanup._result_awaited
                        assert cleanup._result_token is None
                else:
                    assert held["signed_notice_published"]
                    if stage.endswith("_actors"):
                        async def wrong_notice_caller():
                            with pytest.raises(AuthorityRefusalError):
                                body.current_notice()
                            with pytest.raises(FrameError):
                                body.notify()
                        await asyncio.create_task(wrong_notice_caller())
                        assert not body._failed and not cleanup._result_awaited
                    if stage.endswith("_revoked"):
                        keys["gateway"].retire()
                    if stage.endswith("_barrier"):
                        original_future = cleanup._result_barrier_snapshot[0]
                        cleanup._result_barrier = (original_future,)
                        cleanup._result_barrier_snapshot = cleanup._result_barrier
                    if stage.endswith("_swapped"):
                        from hmp_plugin.presentation_credential_result_body import _BodyNotice
                        prior = body._notice_snapshot
                        body._notice = body._notice_snapshot = _BodyNotice(
                            prior.mint, body, prior.scope, prior.adoption, prior.allocation)
                    if stage.endswith("_drift"):
                        from hmp_plugin import presentation_credential_result_body as body_module
                        timeout = body_module._TIMEOUT
                        def changed_notice_token(sock):
                            value = timeout(sock)
                            if sock is body._scope_origin.envelope_scope.write_scope.sock:
                                cleanup._result_token = cleanup._result_token_snapshot = object()
                                held["caller_notice_token_drift"] = True
                            return value
                        monkeypatch.setattr(body_module, "_TIMEOUT", changed_notice_token)
                    if stage.endswith(("_swapped", "_drift", "_revoked", "_barrier")):
                        with pytest.raises((FrameError, AuthorityRefusalError)):
                            await remote.result_ready()
                        assert body._failed and body._retired
                        assert cleanup._result_token is None
                        assert remote._job_origin_snapshot.result is None
                        if stage.endswith("_drift"):
                            assert held["caller_notice_token_drift"]
                    else:
                        assert await remote.result_ready() is True
                        assert remote._job_origin_snapshot.result is body._candidate_snapshot
                        assert not remote._job_origin_snapshot.credit_released
            if adopted_key_retirement:
                # Retired signing authority cannot authorize a later cancel/terminal receipt.
                assert held["gateway_body"]._failed and held["gateway_body"]._retired
                assert remote._job_origin_snapshot.result is None
                assert remote._job_origin_snapshot.remote_result_token is None
                assert cleanup._result_token is None
                RemoteCleanupOwner.request(cleanup)
                async with asyncio.timeout(3):
                    await asyncio.shield(cleanup._allocations_snapshot[0].task)
                return  # fixture-only disposal; no remote settlement credit
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
        if stage.endswith("_capture_phase"):
            class ForeignCapturePhase:
                def __eq__(self, other):
                    held["foreign_capture_phase_equality"] = True
                    return False
            remote._job_origin_snapshot.remote_phase = ForeignCapturePhase()
        RemoteCleanupOwner.request(cleanup)
        if stage.endswith("_capture_phase"):
            gate = cleanup._read_gate_snapshot
            assert "foreign_capture_phase_equality" not in held
            assert gate._capture_kind == "signed" and gate._capture_failed
            assert gate._signed_capture_origin is None and gate._fact_origin is None
            assert not gate._requested and not gate._activated
            assert held["gateway_body"]._retired
            assert remote._job_origin_snapshot.result is None
        async with asyncio.timeout(3):
            local_closed = await asyncio.shield(cleanup._allocations_snapshot[0].task)
            if stage in ("go_relay_tail_cancel",
                                         "go_relay_result_sign_write_blocked_cancel"):
                outcome = (await asyncio.gather(broker_task, return_exceptions=True))[0]
                assert type(outcome) is asyncio.CancelledError and broker_task.cancelled()
                frame = None
            elif terminal_delivery:
                outcome = (await asyncio.gather(broker_task, return_exceptions=True))[0]
                held["terminal_delivery_broker_outcome"] = outcome
                if isinstance(outcome, BaseException):
                    assert isinstance(outcome, (FrameError, AuthorityRefusalError))
                    frame = None
                else:
                    assert type(outcome) is BrokerFrame and outcome.header.kind == "CANCEL"
                    frame = outcome
            elif terminal_fault:
                outcome = (await asyncio.gather(broker_task, return_exceptions=True))[0]
                if stage.endswith(("_terminal_key", "_terminal_verify")):
                    assert type(outcome) is FrameError
                    assert outcome.args == ("BI1_CONTROL_CREDENTIAL_BINDING_REFUSED",)
                    frame = None
                else:
                    assert type(outcome) is BrokerFrame and outcome.header.kind == "CANCEL"
                    frame = outcome
            else:
                frame = await broker_task
        if terminal_delivery:
            if body_terminal:
                assert held["normal_terminal_reader"]._complete
                assert held["normal_terminal_fact"].received == (
                    held["terminal_delivery"]._offset)
            delivery = held["terminal_delivery"]
            assert delivery._attempted
            assert not cleanup._result_token and remote._result_owner is None
            assert not remote._job_origin_snapshot.credit_released
            return  # counted local send alone is not receiver acceptance or native settlement
        if terminal_fault:
            exporter = held["terminal_exporter"]
            assert exporter._failed and exporter._attempted and not exporter._complete
            assert exporter._frozen_origin is None and held["terminal_sign_calls"] == 1
            assert held["signed_result_writer"]._payload_snapshot is None
            assert held["result_producer"]._payload_snapshot is None
            assert not cleanup._result_token and remote._result_owner is None
            assert not remote._job_origin_snapshot.credit_released
            return  # exporter refusal is neither RESULT failure nor native settlement
        if stage == "go_current_park_expiry":
            assert frame is None and held["actual_park_expiry_refused"]
            assert held["control"]._stop_intent_snapshot is None
            assert not cleanup._result_token and remote._result_owner is None
            assert not remote._job_origin_snapshot.credit_released
            return  # known local facts cannot convert expired broker custody into release
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
        if body_stage:
            assert held["body_retired_before_clock"]
            assert held["gateway_body"]._candidate_snapshot is None
    finally:
        native_body_sender = held.get("native_body_sender")
        if native_body_sender is not None:
            if not native_body_sender.done():
                native_body_sender.cancel()
            await asyncio.gather(native_body_sender, return_exceptions=True)
        body_canceller = held.get("body_canceller")
        if body_canceller is not None:
            if not body_canceller.done():
                body_canceller.cancel()
            await asyncio.gather(body_canceller, return_exceptions=True)
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
        gateway_closed = gateway.close()
        if not gateway_closed and (body_fault or adopted_key_retirement):
            from hmp_plugin.presentation_clock import NativeClockOwner
            own_body = held.get("gateway_body")
            if own_body is None:
                assert gateway._credential_result_receiver_snapshot._io_unknown
            elif not adopted_key_retirement:
                assert own_body._io_unknown
            else:
                assert own_body._failed and own_body._retired
                assert own_body._scope_origin.job.result is None
                assert own_body._scope_origin.job.remote_result_token is None
            gateway._socket_snapshot.close()  # fixture-owned disposal, no release fact
            assert NativeClockOwner.close_local(gateway._clock_owner_snapshot)
        else:
            assert gateway_closed and gateway.close_clock()
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
        other_sockets = held.get("wake_other_sockets")
        if other_sockets is not None:
            for other_socket in other_sockets:
                other_socket.close()  # fixture-only unrelated unregistered descriptors
            held["wake_other_waiter"]._future_origin.cancel()
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
