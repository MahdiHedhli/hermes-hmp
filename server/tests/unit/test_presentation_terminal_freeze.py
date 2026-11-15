"""Actual synthetic producer/Task freeze; DATA only, no terminal write or release."""
import asyncio
import hashlib

import pytest

from hmp_plugin import presentation_terminal_claim as terminal
from hmp_plugin.presentation_broker_cancel import BrokerCancellationOwner
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_cancel_budget import CLEANUP_NS, CancellationBudget
from hmp_plugin.presentation_clock import NativeClockOwner
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

from .test_presentation_broker_service import local as local
from .test_presentation_result_transport import coupled_result as coupled_result
from .test_presentation_supervisor import context as context
from .test_presentation_terminal_claim import wait_producer

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


@pytest.mark.parametrize("case", ["normal", "aborted", "historical_ok_then_cause"])
async def test_original_producer_freezes_actual_minimum_without_granting_wire_permission(
    coupled_result, monkeypatch, case
):
    remote, row, spine, task = coupled_result
    original = terminal.LocalStartedProducer.__init__
    frozen = []

    def initialize(producer, service, connection, record):
        original(producer, service, connection, record)
        scope = producer._scope_snapshot
        if case == "historical_ok_then_cause":
            assert producer.claim_data().outcome == "OK"
            BrokerCancellationOwner._local_cause(scope.control)
        fact = terminal.LocalStartedProducer.freeze_handoff_data(producer)
        frozen.append((producer, fact, CancellationBudget.inspect(scope.control_scope[3])[2]))

    monkeypatch.setattr(terminal.LocalStartedProducer, "__init__", initialize)
    if case == "aborted":
        monkeypatch.setattr(BrokerRegistry, "poll_resource_result", lambda *args: False)
    assert await remote.begin_ready() and await remote.go()
    if case != "aborted":
        assert await remote.result_ready()
        await wait_producer(spine, row[7])
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert len(frozen) == 1
    producer, fact, observed_end = frozen[0]
    assert fact is producer._handoff is producer._handoff_snapshot
    assert fact.producer is producer and fact.scope is producer._scope_snapshot
    assert fact.claim is producer.claim_data() and fact.budget is fact.scope.control_scope[3]
    assert fact.cleanup_end == observed_end
    assert fact.sha256 == hashlib.sha256(fact.wire).hexdigest()
    decoded = terminal.decode_handoff(fact.wire)
    assert decoded.claim == fact.claim
    assert decoded.claim.outcome == ("ABORTED" if case == "aborted" else "OK")
    if case == "normal":
        assert fact.cleanup_end is None and decoded.cleanup is None
    else:
        assert decoded.cleanup == terminal.CleanupStamp(observed_end - CLEANUP_NS, observed_end)
    assert b"Bearer" not in fact.wire and b"/" not in fact.wire
    assert not hasattr(fact, "release") and not hasattr(fact, "acknowledge")
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None
    assert not remote._job_origin_snapshot.credit_released
    # A historical data object cannot be refrozen after later cause/closure.
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    assert producer._handoff_failed and producer._handoff_snapshot is fact


async def test_native_reentry_cannot_retry_or_publish_a_freeze_after_restoration(
    coupled_result, monkeypatch
):
    remote, row, spine, task = coupled_result
    original_init = terminal.LocalStartedProducer.__init__
    original_sample = NativeClockOwner.sample
    producers, reentered = [], []

    def sample(clock):
        if producers and producers[0]._handoff_attempted and not reentered:
            reentered.append(True)
            with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
                producers[0].freeze_handoff_data()
        return original_sample(clock)

    def initialize(producer, service, connection, record):
        original_init(producer, service, connection, record)
        producers.append(producer)
        with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
            producer.freeze_handoff_data()

    monkeypatch.setattr(NativeClockOwner, "sample", sample)
    monkeypatch.setattr(terminal.LocalStartedProducer, "__init__", initialize)
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    await wait_producer(spine, row[7])
    producer = producers[0]
    assert reentered and producer._handoff_attempted and producer._handoff_failed
    assert producer._handoff is None and producer._handoff_snapshot is None
    monkeypatch.setattr(NativeClockOwner, "sample", original_sample)
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None


@pytest.mark.parametrize("phase", ["before_encode", "after_encode", "final_sample"])
@pytest.mark.parametrize("fault", ["scope", "claim", "cause", "shorten", "foreign_budget"])
async def test_freeze_boundary_drift_never_publishes_or_recovers_after_restore(
    coupled_result, monkeypatch, phase, fault
):
    from hmp_plugin.presentation_cancel_budget import CancellationWindow

    remote, row, spine, task = coupled_result
    original_init = terminal.LocalStartedProducer.__init__
    original_encode = terminal.encode_handoff
    original_sample, original_cleanup = NativeClockOwner.sample, NativeClockOwner.cleanup_sample
    producers, scopes, claims, changed, callbacks, encoded = [], [], [], [], [], []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign freeze scope must not be followed")

    def inject():
        producer, scope, claim = producers[0], scopes[0], claims[0]
        changed.append(True)
        if fault == "scope":
            producer._scope = producer._scope_snapshot = scope._replace(task=Foreign())
        elif fault == "claim":
            producer._claim = producer._claim_snapshot = claim._replace(epoch=claim.epoch + 1)
        elif fault == "cause":
            BrokerCancellationOwner._local_cause(scope.control)
        elif fault == "shorten":
            budget = scope.control_scope[3]
            _, last, end, _ = CancellationBudget.inspect(budget)
            CancellationBudget.inherit(
                budget, CancellationWindow(end - CLEANUP_NS - 30_000_000,
                                           end - 30_000_000), last)
        else:
            control_scope = list(scope.control_scope)
            control_scope[3] = Foreign()
            producer._scope = producer._scope_snapshot = scope._replace(
                control_scope=tuple(control_scope))

    def encode(claim, stamp=None):
        if phase == "before_encode" and producers and not changed:
            inject()
        wire = original_encode(claim, stamp)
        encoded.append(True)
        if phase == "after_encode" and not changed:
            inject()
        return wire

    def sampled(original, clock):
        now = original(clock)
        if (phase == "final_sample" and encoded and not changed
                and clock is scopes[0].clock):
            inject()
        return now

    def initialize(producer, service, connection, record):
        original_init(producer, service, connection, record)
        scope, claim = producer._scope_snapshot, producer._claim_snapshot
        producers.append(producer)
        scopes.append(scope)
        claims.append(claim)
        if fault == "shorten":
            BrokerCancellationOwner._local_cause(scope.control)
        try:
            with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
                producer.freeze_handoff_data()
        finally:
            # Restore fixture metadata after the refused attempt, never the
            # actual caused/shortened budget or the irreversible freeze flags.
            producer._scope = producer._scope_snapshot = scope
            producer._claim = producer._claim_snapshot = claim

    monkeypatch.setattr(terminal.LocalStartedProducer, "__init__", initialize)
    monkeypatch.setattr(terminal, "encode_handoff", encode)
    monkeypatch.setattr(NativeClockOwner, "sample", lambda clock: sampled(original_sample, clock))
    monkeypatch.setattr(NativeClockOwner, "cleanup_sample",
                        lambda clock: sampled(original_cleanup, clock))
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    await wait_producer(spine, row[7])
    producer = producers[0]
    assert changed and callbacks == [] and producer._handoff_failed
    assert producer._handoff is None and producer._handoff_snapshot is None
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None
    assert not remote._job_origin_snapshot.credit_released


async def test_wrong_actor_freeze_refuses_before_native_sampling(coupled_result, monkeypatch):
    remote, row, spine, task = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    _, producer = await wait_producer(spine, row[7])
    clock = producer._scope_snapshot.clock
    original, sampled = NativeClockOwner.sample, []

    def sample(owner):
        if owner is clock:
            sampled.append(True)
        return original(owner)

    monkeypatch.setattr(NativeClockOwner, "sample", sample)
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    assert sampled == [] and producer._handoff_attempted and producer._handoff_failed
    assert producer._handoff_snapshot is None
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None


@pytest.mark.parametrize("field", ["connection_task", "record_resources", "service_registry",
                                  "observation", "transfer_writer", "domain_boot"])
async def test_final_control_fd_tail_cannot_publish_under_changed_custody(
    coupled_result, monkeypatch, field
):
    from hmp_plugin import presentation_broker_cancel as cancel

    remote, row, spine, task = coupled_result
    original_init, original_encode = terminal.LocalStartedProducer.__init__, terminal.encode_handoff
    original_sample, original_timeout = NativeClockOwner.sample, cancel._SOCKET_TIMEOUT
    producers, scopes, encoded, sampled, changed, callbacks = [], [], [], [], [], []

    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("changed custody must not be followed")

    def encode(claim, cleanup=None):
        wire = original_encode(claim, cleanup)
        encoded.append(True)
        return wire

    def sample(clock):
        now = original_sample(clock)
        if encoded and clock is scopes[0].clock:
            sampled.append(True)
        return now

    def timeout(sock):
        value = original_timeout(sock)
        if (encoded and sampled and not changed
                and sock is scopes[0].channel._socket_snapshot):
            changed.append(True)
            producer, scope = producers[0], scopes[0]
            if field == "connection_task":
                scope.connection.task = Foreign()
            elif field == "record_resources":
                scope.record.resources = Foreign()
            elif field == "service_registry":
                scope.service._registry = Foreign()
            elif field == "observation":
                producer._observation = producer._observation_snapshot = Foreign()
            elif field == "transfer_writer":
                scope.connection.result_writer = scope.connection.result_writer_snapshot = Foreign()
            else:
                object.__setattr__(scope.domain, "boot", b"changed-clock-boot")
        return value

    def initialize(producer, service, connection, record):
        original_init(producer, service, connection, record)
        scope = producer._scope_snapshot
        producers.append(producer)
        scopes.append(scope)
        observation = producer._observation_snapshot
        writer = connection.result_writer_snapshot
        boot = scope.domain.boot
        try:
            with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
                producer.freeze_handoff_data()
        finally:
            connection.task = scope.task
            record.resources = scope.resources
            service._registry = scope.registry
            producer._observation = producer._observation_snapshot = observation
            connection.result_writer = connection.result_writer_snapshot = writer
            object.__setattr__(scope.domain, "boot", boot)

    monkeypatch.setattr(terminal.LocalStartedProducer, "__init__", initialize)
    monkeypatch.setattr(terminal, "encode_handoff", encode)
    monkeypatch.setattr(NativeClockOwner, "sample", sample)
    monkeypatch.setattr(cancel, "_SOCKET_TIMEOUT", timeout)
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    await wait_producer(spine, row[7])
    producer = producers[0]
    assert changed and callbacks == [] and producer._handoff_failed
    assert producer._handoff_snapshot is None
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None


async def test_encoder_failure_after_producing_bytes_is_sticky_without_publication(
    coupled_result, monkeypatch
):
    remote, row, spine, task = coupled_result
    original_init, original_encode = terminal.LocalStartedProducer.__init__, terminal.encode_handoff
    producers, encoded = [], []

    def encode(claim, cleanup=None):
        wire = original_encode(claim, cleanup)
        encoded.append(len(wire))
        raise RuntimeError("synthetic failure after complete encoding")

    def initialize(producer, service, connection, record):
        original_init(producer, service, connection, record)
        producers.append(producer)
        with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
            producer.freeze_handoff_data()

    monkeypatch.setattr(terminal.LocalStartedProducer, "__init__", initialize)
    monkeypatch.setattr(terminal, "encode_handoff", encode)
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    await wait_producer(spine, row[7])
    producer = producers[0]
    assert encoded and producer._handoff_failed and producer._handoff_snapshot is None
    assert not producer._failed and producer.claim_data().outcome == "OK"
    monkeypatch.setattr(terminal, "encode_handoff", original_encode)
    with pytest.raises(FrameError, match="BI1_LOCAL_HANDOFF_FREEZE_REFUSED"):
        producer.freeze_handoff_data()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None
