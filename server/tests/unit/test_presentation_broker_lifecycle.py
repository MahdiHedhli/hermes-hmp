"""Control grammar only: no native decisions, processes, files or custody proof."""

import dataclasses
import itertools

import pytest

from hmp_plugin.presentation_broker_codec import BrokerBinding, decode_frame, encode_frame
from hmp_plugin.presentation_broker_lifecycle import (
    MessageDisposition as D,
)
from hmp_plugin.presentation_broker_lifecycle import (
    OperationGrammar,
    ReplayWindow,
    operation_id,
)
from hmp_plugin.presentation_jobs import FrameError


def binding(serial=1, *, suffix="a" * 48, channel="3" * 64):
    return BrokerBinding("a" * 52, "1" * 32, "2" * 64, channel, f"{serial:016x}{suffix}")


def frame(scope, kind, sequence):
    # Body syntax is not input3/output2 validation; these fixtures grant nothing.
    return decode_frame(
        encode_frame(scope, kind, sequence, b"data" if kind in ("BEGIN", "RESULT") else b""),
        expected=scope,
    )


def step(model, sender, kind, sequence):
    return model.observe(frame(model._binding, kind, sequence), sender=sender)


def start(model):
    step(model, "client", "BEGIN", 0)
    step(model, "broker", "READY", 0)
    step(model, "client", "GO", 1)


@pytest.mark.parametrize("role", ["gateway", "broker"])
def test_happy_message_flow_requests_ack_but_never_proves_closure(role):
    model = OperationGrammar(binding(), role=role)
    start(model)
    assert step(model, "broker", "RESULT", 1) is D.RESULT_CANDIDATE
    assert model.candidate_message is (role == "gateway")
    assert step(model, "client", "ACK", 2) is D.ACK_REQUEST
    with pytest.raises(FrameError):
        step(model, "client", "ACK", 3)
    assert not model.candidate_message


def test_every_permutation_except_exact_happy_order_refuses():
    events = [
        ("client", "BEGIN", 0),
        ("broker", "READY", 0),
        ("client", "GO", 1),
        ("broker", "RESULT", 1),
        ("client", "ACK", 2),
    ]
    accepted = []
    for order in itertools.permutations(events):
        model = OperationGrammar(binding(), role="gateway")
        try:
            for args in order:
                step(model, *args)
        except FrameError:
            continue
        accepted.append(order)
    assert accepted == [tuple(events)]


def test_cancel_result_race_is_cleanup_only_on_both_sides():
    gateway = OperationGrammar(binding(), role="gateway")
    broker = OperationGrammar(binding(), role="broker")
    for model in (gateway, broker):
        start(model)
    # Result was already planned by broker while cancellation was planned by gateway.
    step(broker, "broker", "RESULT", 1)
    gateway.invalidate()
    step(gateway, "client", "CANCEL", 2)
    assert step(broker, "client", "CANCEL", 2) is D.CONTROL
    assert step(gateway, "broker", "RESULT", 1) is D.RESULT_DISCARDED
    assert not gateway.candidate_message
    for model in (gateway, broker):
        assert step(model, "client", "ACK", 3) is D.ACK_REQUEST
        with pytest.raises(FrameError):
            step(model, "broker", "CLOSED", 2)


def test_cancellation_after_terminal_message_cannot_restore_candidate():
    model = OperationGrammar(binding(), role="gateway")
    start(model)
    step(model, "broker", "RESULT", 1)
    assert model.candidate_message
    model.invalidate()
    assert not model.candidate_message
    step(model, "client", "CANCEL", 2)
    assert step(model, "client", "ACK", 3) is D.ACK_REQUEST
    assert not model.candidate_message


def test_cancel_ready_race_never_allows_go():
    model = OperationGrammar(binding(), role="gateway")
    step(model, "client", "BEGIN", 0)
    model.invalidate()
    step(model, "client", "CANCEL", 1)
    step(model, "broker", "READY", 0)  # already in flight, useful only for cleanup
    step(model, "broker", "CLOSED", 1)
    assert step(model, "client", "ACK", 2) is D.ACK_REQUEST
    assert not model.candidate_message


@pytest.mark.parametrize("role,action", [("gateway", "GO"), ("broker", "RESULT")])
def test_stale_local_intent_never_resumes_normal_work(role, action):
    model = OperationGrammar(binding(), role=role)
    step(model, "client", "BEGIN", 0)
    step(model, "broker", "READY", 0)
    if action == "RESULT":
        step(model, "client", "GO", 1)
    model.invalidate()
    with pytest.raises(FrameError):
        step(model, "client" if action == "GO" else "broker", action, 1)
    assert not model.candidate_message


@pytest.mark.parametrize("role,action", [("gateway", "BEGIN"), ("broker", "READY")])
def test_invalidated_local_start_or_ready_is_not_new_work(role, action):
    model = OperationGrammar(binding(), role=role)
    if role == "broker":
        step(model, "client", "BEGIN", 0)
    model.invalidate()
    with pytest.raises(FrameError):
        step(model, "client" if role == "gateway" else "broker", action, 0)


@pytest.mark.parametrize(
    "events",
    [
        [("client", "BEGIN", 0), ("broker", "CLOSED", 0), ("client", "ACK", 1)],
        [
            ("client", "BEGIN", 0),
            ("client", "CANCEL", 1),
            ("broker", "CLOSED", 0),
            ("client", "ACK", 2),
        ],
        [
            ("client", "BEGIN", 0),
            ("broker", "READY", 0),
            ("broker", "CLOSED", 1),
            ("client", "ACK", 1),
        ],
    ],
)
def test_known_terminal_message_without_result_is_cleanup_only(events):
    model = OperationGrammar(binding(), role="gateway")
    for args in events:
        outcome = step(model, *args)
    assert outcome is D.ACK_REQUEST and not model.candidate_message


@pytest.mark.parametrize(
    "response,decision",
    [("PENDING", D.STATUS_PENDING), ("UNKNOWN", D.STATUS_UNKNOWN), ("CLOSED", D.CONTROL)],
)
def test_status_never_restores_result_or_starts_execution(response, decision):
    model = OperationGrammar(binding(), role="gateway", mode="status")
    step(model, "client", "STATUS", 0)
    assert step(model, "broker", response, 0) is decision
    assert not model.candidate_message
    if response == "CLOSED":
        assert step(model, "client", "ACK", 1) is D.ACK_REQUEST
    else:
        with pytest.raises(FrameError):
            step(model, "client", "ACK", 1)


@pytest.mark.parametrize(
    "mode,events",
    [
        ("status", [("client", "BEGIN", 0)]),
        ("status", [("client", "STATUS", 0), ("broker", "RESULT", 0)]),
        ("status", [("client", "STATUS", 0), ("client", "GO", 1)]),
        ("operation", [("client", "STATUS", 0)]),
        ("operation", [("client", "BEGIN", 0), ("broker", "PENDING", 0)]),
        ("operation", [("client", "BEGIN", 0), ("broker", "UNKNOWN", 0)]),
        ("operation", [("client", "BEGIN", 0), ("client", "ACK", 1)]),
        ("operation", [("client", "BEGIN", 0), ("broker", "READY", 1)]),
        ("operation", [("broker", "BEGIN", 0)]),
    ],
)
def test_status_operation_roles_and_sequence_are_not_interchangeable(mode, events):
    model = OperationGrammar(binding(), role="gateway", mode=mode)
    with pytest.raises(FrameError):
        for args in events:
            step(model, *args)
    with pytest.raises(FrameError):
        step(model, "client", "BEGIN", 0)  # poison is sticky; no retry/resume


def test_wrong_binding_does_not_retarget_session():
    model = OperationGrammar(binding(), role="gateway")
    for other in (binding(channel="5" * 64), binding(2)):
        model = OperationGrammar(binding(), role="gateway")
        with pytest.raises(FrameError):
            model.observe(frame(other, "BEGIN", 0), sender="client")
        assert not model.candidate_message


def test_reentrant_use_is_refused_not_a_second_intent():
    model = OperationGrammar(binding(), role="gateway")
    assert model._lock.acquire(blocking=False)
    try:
        with pytest.raises(FrameError):
            step(model, "client", "BEGIN", 0)
    finally:
        model._lock.release()
    with pytest.raises(FrameError):
        step(model, "client", "BEGIN", 0)


def test_ack_and_changed_random_suffix_or_channel_never_reset_replay_history():
    original = binding()
    window = ReplayWindow(original)
    window.consume(original)
    model = OperationGrammar(original, role="gateway")
    start(model)
    step(model, "broker", "RESULT", 1)
    step(model, "client", "ACK", 2)
    for replay in (original, binding(suffix="b" * 48), binding(channel="5" * 64)):
        with pytest.raises(FrameError):
            window.consume(replay)
    window.consume(binding(2))


def test_out_of_order_admission_is_bounded_and_consumes_each_serial_once():
    window = ReplayWindow(binding())
    for serial in (3, 1, 2, 65, 64, 63):
        window.consume(binding(serial))
    for serial in (1, 2, 3, 65, 64, 63):
        with pytest.raises(FrameError):
            window.consume(binding(serial))
    window.consume(binding(4))  # still within the last64 inclusive65..2
    assert window._seen.bit_length() <= 64
    window.consume(binding((1 << 63) - 1))
    assert window._seen == 1  # no shift/allocation proportional to the huge gap
    with pytest.raises(FrameError):
        window.consume(binding(5))


@pytest.mark.parametrize(
    "field,value", [("iid", "a" * 51 + "q"), ("listener", "5" * 32), ("broker", "5" * 64)]
)
def test_foreign_scope_cannot_advance_window(field, value):
    window = ReplayWindow(binding())
    with pytest.raises(FrameError):
        window.consume(dataclasses.replace(binding(1000), **{field: value}))
    window.consume(binding(1))
    assert window._high == 1


@pytest.mark.parametrize("serial", [0, 1 << 63])
def test_invalid_serial_cannot_consume_or_wrap(serial):
    window = ReplayWindow(binding())
    with pytest.raises(FrameError):
        window.consume(binding(serial))
    window.consume(binding(1))
    with pytest.raises(FrameError):
        OperationGrammar(binding(serial), role="gateway")


@pytest.mark.parametrize("serial", [True, None, 0, -1, 1 << 63, 1.0])
def test_gateway_operation_id_has_no_implicit_counter_reset(serial):
    with pytest.raises(FrameError):
        operation_id(serial)


def test_operation_id_uses_nonzero_serial_and_fresh_192bit_suffix(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "hmp_plugin.presentation_broker_lifecycle.secrets.token_hex",
        lambda n: calls.append(n) or "f" * 48,
    )
    assert operation_id(7) == "0000000000000007" + "f" * 48
    assert calls == [24]


@pytest.mark.parametrize(
    "field,value", [("_binding", binding(2)), ("_role", "broker"), ("_mode", "status")]
)
def test_captured_session_configuration_cannot_retarget_between_messages(field, value):
    model = OperationGrammar(binding(), role="gateway")
    step(model, "client", "BEGIN", 0)
    setattr(model, field, value)
    with pytest.raises(FrameError):
        step(model, "broker", "READY", 0)
    assert not model.candidate_message


def test_binding_value_mutation_does_not_survive_in_candidate_property():
    model = OperationGrammar(binding(), role="gateway")
    start(model)
    step(model, "broker", "RESULT", 1)
    assert model.candidate_message
    object.__setattr__(model._binding, "channel", "5" * 64)
    assert not model.candidate_message
    object.__setattr__(model._binding, "channel", "3" * 64)
    assert not model.candidate_message  # observing drift is sticky even after restoration
    with pytest.raises(FrameError):
        step(model, "client", "ACK", 2)


def test_window_scope_rebinding_is_sticky_and_cannot_erase_history():
    window = ReplayWindow(binding())
    window.consume(binding())
    original = window._scope
    window._scope = ("a" * 52, "5" * 32, "2" * 64)
    with pytest.raises(FrameError):
        window.consume(dataclasses.replace(binding(2), listener="5" * 32))
    window._scope = original
    with pytest.raises(FrameError):
        window.consume(binding(2))


@pytest.mark.parametrize("version", [True, False, 0, 3, 2.0, "2", None])
def test_selected_grammar_rejects_unknown_or_coerced_versions(version):
    with pytest.raises(FrameError):
        OperationGrammar(binding(), role="broker", protocol_version=version)


def test_selected_v2_invalidation_accepts_only_cleanup_cancel_without_candidate():
    from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader
    from hmp_plugin.presentation_cancel_budget import CancellationWindow

    b = binding()
    grammar = OperationGrammar(b, role="broker", protocol_version=2)
    grammar.observe(BrokerFrame(BrokerHeader(b, "BEGIN", 0, 4, 2), b"data"), sender="client")
    grammar.invalidate()
    body = CancellationWindow(0, 250_000_000).encode()
    grammar.observe(BrokerFrame(BrokerHeader(b, "CANCEL", 1, 16, 2), body), sender="client")
    assert grammar._cancel and grammar._invalidated and not grammar.candidate_message
    with pytest.raises(FrameError):
        grammar.observe(BrokerFrame(BrokerHeader(b, "CANCEL", 2, 16, 2), body), sender="client")


@pytest.mark.parametrize("kind", ["GO", "RESULT", "STATUS", "ACK", "CLOSED", "PENDING", "UNKNOWN"])
def test_selected_v2_grammar_does_not_activate_unjoined_lifecycle(kind):
    from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader

    b = binding()
    grammar = OperationGrammar(b, role="broker", protocol_version=2)
    grammar.observe(BrokerFrame(BrokerHeader(b, "BEGIN", 0, 4, 2), b"data"), sender="client")
    body = b"data" if kind == "RESULT" else b""
    with pytest.raises(FrameError):
        grammar.observe(BrokerFrame(BrokerHeader(b, kind, 1, len(body), 2), body), sender="client")


@pytest.mark.parametrize("version", [1, 2])
def test_explicit_grammar_never_downgrades_or_upgrades_frames(version):
    from hmp_plugin.presentation_broker_codec import BrokerFrame, BrokerHeader

    b = binding()
    grammar = OperationGrammar(b, role="broker", protocol_version=version)
    with pytest.raises(FrameError):
        grammar.observe(BrokerFrame(BrokerHeader(b, "BEGIN", 0, 4, 3 - version), b"data"),
                        sender="client")
    assert grammar._failed and not grammar._begun


def test_selected_v2_status_construction_stays_closed():
    with pytest.raises(FrameError):
        OperationGrammar(binding(), role="gateway", mode="status", protocol_version=2)



def v2_step(model, sender, kind, sequence, body=None):
    from hmp_plugin.presentation_broker_codec import decode_frame, encode_frame

    if body is None:
        body = b"data" if kind in ("BEGIN", "RESULT") else b""
    frame = decode_frame(encode_frame(model._binding, kind, sequence, body, version=2),
                         expected=model._binding, expected_version=2)
    return model.observe(frame, sender=sender)


def terminal_body(model, outcome="OK", **changes):
    from hmp_plugin.presentation_terminal_claim import (
        CleanupStamp,
        StartedClaim,
        claim_binding,
        encode_handoff,
    )

    claim = StartedClaim(claim_binding(model._binding), "alpha", "METADATA", 2_000_000_000,
                         "f" * 64, 1, "a" * 64, "b" * 64, "c" * 64, "d" * 64,
                         outcome, 0, "e" * 64 if outcome == "OK" else None)
    cleanup = changes.pop("cleanup", None)
    if outcome == "ABORTED" or (model._role == "broker" and model._invalidated):
        cleanup = CleanupStamp(0, 250_000_000) if cleanup is None else cleanup
    return encode_handoff(claim._replace(**changes), cleanup)


def v2_result(model):
    v2_step(model, "client", "BEGIN", 0)
    v2_step(model, "broker", "READY", 0)
    v2_step(model, "client", "GO", 1)
    return v2_step(model, "broker", "RESULT", 1)


@pytest.mark.parametrize("role", ["gateway", "broker"])
def test_v2_result_terminal_ack_is_only_correlated_data(role):
    import hashlib

    model = OperationGrammar(binding(), role=role, protocol_version=2)
    assert v2_result(model) is D.RESULT_CANDIDATE
    assert model._terminal_message is None  # RESULT alone cannot be ACKed
    body = terminal_body(model)
    assert v2_step(model, "broker", "TERMINAL", 2, body) is D.TERMINAL_CLAIM
    assert model.candidate_message is (role == "gateway")
    assert v2_step(model, "client", "ACK", 2, hashlib.sha256(body).digest()) is D.ACK_REQUEST
    assert not hasattr(model, "release") and not hasattr(model, "complete")
    with pytest.raises(FrameError):
        v2_step(model, "client", "ACK", 3, hashlib.sha256(body).digest())


@pytest.mark.parametrize("role", ["gateway", "broker"])
@pytest.mark.parametrize("stage", [0, 1, 2])
def test_v2_abort_uses_next_broker_sequence_and_retires_candidate(role, stage):
    import hashlib

    model = OperationGrammar(binding(), role=role, protocol_version=2)
    v2_step(model, "client", "BEGIN", 0)
    if stage:
        v2_step(model, "broker", "READY", 0)
    if stage == 2:
        v2_step(model, "client", "GO", 1)
        v2_step(model, "broker", "RESULT", 1)
    if role == "broker":
        model.invalidate()  # syntax only, not an actual closure/budget fact
    body = terminal_body(model, "ABORTED")
    assert v2_step(model, "broker", "TERMINAL", stage, body) is D.TERMINAL_ABORTED
    assert not model.candidate_message and model._invalidated
    assert v2_step(model, "client", "ACK", 2 if stage == 2 else 1,
                   hashlib.sha256(body).digest()) is D.ACK_REQUEST


@pytest.mark.parametrize("role", ["gateway", "broker"])
@pytest.mark.parametrize("cancel_first", [False, True])
def test_v2_cancel_racing_frozen_ok_never_remints_or_revives(role, cancel_first):
    import hashlib

    from hmp_plugin.presentation_cancel_budget import CancellationWindow

    model = OperationGrammar(binding(), role=role, protocol_version=2)
    v2_result(model)
    body = terminal_body(model)
    cancel = CancellationWindow(0, 250_000_000).encode()
    if cancel_first:
        v2_step(model, "client", "CANCEL", 2, cancel)
        body = terminal_body(model)  # historical claim unchanged; sender stamp is separate
    outcome = v2_step(model, "broker", "TERMINAL", 2, body)
    assert outcome is (D.TERMINAL_DISCARDED if cancel_first else D.TERMINAL_CLAIM)
    digest = model._terminal_digest
    syntax = model._terminal_syntax_snapshot
    if not cancel_first:
        v2_step(model, "client", "CANCEL", 2, cancel)
    assert model._terminal_digest is digest and model._terminal_outcome == "OK"
    assert model._terminal_syntax is syntax and model._terminal_syntax_snapshot is syntax
    assert not model.candidate_message
    assert v2_step(model, "client", "ACK", 3, hashlib.sha256(body).digest()) is D.ACK_REQUEST


@pytest.mark.parametrize("fault", ["early_ack", "wrong_digest", "wrong_sequence", "scope",
                                  "ok_without_result", "duplicate_result", "duplicate_terminal"])
def test_v2_terminal_transcript_faults_are_sticky(fault):
    import hashlib

    from hmp_plugin.presentation_terminal_claim import claim_binding

    model = OperationGrammar(binding(), role="gateway", protocol_version=2)
    if fault == "ok_without_result":
        v2_step(model, "client", "BEGIN", 0)
    else:
        v2_result(model)
    body = terminal_body(model)
    with pytest.raises(FrameError):
        if fault == "early_ack":
            v2_step(model, "client", "ACK", 2, hashlib.sha256(body).digest())
        elif fault == "scope":
            body = terminal_body(model, binding=claim_binding(binding(2)))
            v2_step(model, "broker", "TERMINAL", 2, body)
        elif fault == "ok_without_result":
            v2_step(model, "broker", "TERMINAL", 0, body)
        elif fault == "duplicate_result":
            v2_step(model, "broker", "RESULT", 2)
        else:
            v2_step(model, "broker", "TERMINAL", 2, body)
            if fault == "duplicate_terminal":
                v2_step(model, "broker", "TERMINAL", 3, body)
            else:
                v2_step(model, "client", "ACK", 3 if fault == "wrong_sequence" else 2,
                        hashlib.sha256(body).digest() if fault == "wrong_sequence" else b"x" * 32)
    assert model._failed and not model.candidate_message


def test_v2_late_result_and_ok_remain_discarded_after_cancel():
    from hmp_plugin.presentation_cancel_budget import CancellationWindow

    model = OperationGrammar(binding(), role="gateway", protocol_version=2)
    v2_step(model, "client", "BEGIN", 0)
    v2_step(model, "broker", "READY", 0)
    v2_step(model, "client", "GO", 1)
    v2_step(model, "client", "CANCEL", 2, CancellationWindow(0, 250_000_000).encode())
    assert v2_step(model, "broker", "RESULT", 1) is D.RESULT_DISCARDED
    assert v2_step(model, "broker", "TERMINAL", 2, terminal_body(model)) is D.TERMINAL_DISCARDED
    assert not model.candidate_message


def test_v2_broker_abort_requires_sticky_invalidation_not_merely_body_claim():
    model = OperationGrammar(binding(), role="broker", protocol_version=2)
    v2_step(model, "client", "BEGIN", 0)
    with pytest.raises(FrameError):
        v2_step(model, "broker", "TERMINAL", 0, terminal_body(model, "ABORTED"))
    assert model._failed


@pytest.mark.parametrize("fault", ["digest", "outcome", "partial", "foreign", "paired_syntax"])
def test_terminal_syntax_seal_refuses_valid_shaped_scalar_or_reference_drift(fault):
    from hmp_plugin.presentation_broker_lifecycle import _TerminalSyntax

    model = OperationGrammar(binding(), role="gateway", protocol_version=2)
    v2_result(model)
    v2_step(model, "broker", "TERMINAL", 2, terminal_body(model))
    original = model._terminal_syntax_snapshot
    assert not any(type(value) in (dict, list) for value in original)
    with pytest.raises(AttributeError):
        object.__setattr__(original, "outcome", "ABORTED")
    if fault == "digest":
        model._terminal_digest = bytes(bytearray(original.digest))
    elif fault == "outcome":
        model._terminal_outcome = "ABORTED"
    elif fault == "partial":
        model._terminal_syntax = None
    elif fault == "foreign":
        model._terminal_syntax = model._terminal_syntax_snapshot = object()
    else:
        model._terminal_syntax = model._terminal_syntax_snapshot = _TerminalSyntax(b"x" * 32, "OK")
    assert not model.candidate_message and model._failed
    model._terminal_digest = original.digest
    model._terminal_outcome = original.outcome
    model._terminal_syntax = model._terminal_syntax_snapshot = original
    assert not model.candidate_message  # detected drift is sticky, not recoverable permission



def test_already_invalidated_broker_cannot_hide_sender_window_in_ok_handoff():
    from hmp_plugin.presentation_terminal_claim import decode_handoff, encode_handoff

    model = OperationGrammar(binding(), role="broker", protocol_version=2)
    v2_result(model)
    historical = decode_handoff(terminal_body(model)).claim
    model.invalidate()
    with pytest.raises(FrameError):
        v2_step(model, "broker", "TERMINAL", 2, encode_handoff(historical))
    assert model._failed and model._terminal_syntax_snapshot is None


def test_ack_hash_covers_sender_stamp_and_wrapper_not_only_historical_claim():
    import hashlib

    from hmp_plugin.presentation_terminal_claim import decode_handoff, encode_claim

    model = OperationGrammar(binding(), role="gateway", protocol_version=2)
    v2_result(model)
    body = terminal_body(model)
    v2_step(model, "broker", "TERMINAL", 2, body)
    inner = encode_claim(decode_handoff(body).claim)
    assert hashlib.sha256(inner).digest() != model._terminal_digest
    with pytest.raises(FrameError):
        v2_step(model, "client", "ACK", 2, hashlib.sha256(inner).digest())
    assert model._failed
