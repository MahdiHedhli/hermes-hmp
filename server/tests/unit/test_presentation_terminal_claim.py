"""Closed claims and real synthetic local closure; no wire acceptance/release.

Unix/owned-reader fixtures explicitly mock peer/Darwin clock qualification.
"""
import asyncio
import hashlib
import json
from contextlib import suppress

import pytest

from hmp_plugin import presentation_terminal_claim as terminal
from hmp_plugin.presentation_authority import AuthorityRefusalError
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_broker_resources import BrokerLocalDrainObservation
from hmp_plugin.presentation_jobs import FrameError, RemotePhase, State
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner
from hmp_plugin.presentation_result_transport import BrokerResultWriter

from .test_presentation_broker_service import binding
from .test_presentation_broker_service import local as local
from .test_presentation_result_transport import coupled_result as coupled_result
from .test_presentation_supervisor import context as context


@pytest.fixture
def claim():
    return terminal.StartedClaim(terminal.claim_binding(binding()), "alpha", "METADATA",
        2_000_000_000,
        "f" * 64, 1, "a" * 64, "b" * 64, "c" * 64, "d" * 64, "OK", 0, "e" * 64)


def test_claim_roundtrip_is_data_not_a_custody_capability(claim):
    raw = terminal.encode_claim(claim)
    assert terminal.decode_claim(raw) == claim
    assert len(raw) <= terminal.CLAIM_LIMIT
    assert "data-only" in repr(claim)
    assert not hasattr(claim, "release") and not hasattr(claim, "acknowledge")
    assert b"/" not in raw and b"authorization" not in raw


@pytest.mark.parametrize("change", [
    {"epoch": True}, {"deadline_ns": True}, {"deadline_ns": 0}, {"epoch": 0},
    {"epoch": 1 << 63}, {"exit_code": True}, {"exit_code": -256}, {"exit_code": 256},
    {"profile": "../bad"}, {"operation_kind": "SHELL"}, {"input_sha256": "z" * 64},
    {"challenge": None}, {"result_sha256": None}, {"outcome": "OK", "exit_code": 1},
    {"outcome": "ABORTED"}, {"installation_generation": "x"}, {"outcome": "UNKNOWN"},
])
def test_closed_claim_rejects_invalid_primitive_combinations(claim, change):
    with pytest.raises(FrameError):
        terminal.encode_claim(claim._replace(**change))


def test_aborted_claim_has_no_result_digest_even_for_exit_zero(claim):
    aborted = claim._replace(outcome="ABORTED", result_sha256=None)
    assert terminal.decode_claim(terminal.encode_claim(aborted)) == aborted


@pytest.mark.parametrize("fault", ["extra", "missing", "duplicate", "noncanonical", "schema_bool"])
def test_claim_decode_rejects_nonclosed_or_noncanonical_data(claim, fault):
    raw = terminal.encode_claim(claim)
    row = json.loads(raw)
    if fault == "extra":
        row["qualified"] = True
    elif fault == "missing":
        del row["result_sha256"]
    elif fault == "schema_bool":
        row["schema"] = True
    elif fault == "duplicate":
        raw = b'{"schema":1,' + raw[1:]
    if fault not in ("duplicate", "noncanonical"):
        raw = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    if fault == "noncanonical":
        raw += b" "
    with pytest.raises(FrameError):
        terminal.decode_claim(raw)


def test_claim_oversize_is_rejected_before_json_decode():
    with pytest.raises(FrameError):
        terminal.decode_claim(b" " * (terminal.CLAIM_LIMIT + 1))


async def wait_producer(spine, b):
    for _ in range(100):
        ticket = spine._registry._operations.get(b.operation)
        if ticket is not None:
            record = spine._registry._record(ticket)
            producer = record.terminal_producer
            if producer is not None and (producer._claim_snapshot is not None or producer._failed):
                return record, producer
        await asyncio.sleep(0.001)
    pytest.fail("synthetic local producer did not settle")


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_normal_claim_uses_actual_closure_input_and_completed_transfer(coupled_result):
    remote, row, spine, task = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    record, producer = await wait_producer(spine, row[7])
    data = producer.claim_data()
    writer = producer._scope_snapshot.connection.result_writer_snapshot
    fact = writer._transfer_fact_snapshot
    assert data.outcome == "OK" and data.exit_code == 0
    assert data.result_sha256 == fact.sha256 and writer._payload is None
    assert data.input_sha256 == hashlib.sha256(row[6]).hexdigest()
    assert data.worker_source_sha256 == "b" * 64
    assert data.installation_generation == "e" * 64  # distinct install and worker-source contexts
    assert record.input_receipt_snapshot is producer._scope_snapshot.receipt
    assert terminal.decode_claim(terminal.encode_claim(data)) == data
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    job = remote._job_origin_snapshot
    assert job.state is State.RUNNING and job.remote_phase is RemotePhase.RESULT_VALIDATED
    assert row[0]._record(row[1]).headers is not None and not job.credit_released
    assert not hasattr(producer, "release")
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert producer.claim_data() is data  # historical immutable data, never a new permission
    assert record.terminal_producer is producer and job.result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_cancel_before_result_mints_only_aborted_local_data(coupled_result, monkeypatch):
    remote, row, spine, task = coupled_result
    monkeypatch.setattr(BrokerRegistry, "poll_resource_result", lambda *args: False)
    assert await remote.begin_ready() and await remote.go()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    record = spine._registry._record(spine._registry._operations[row[7].operation])
    producer = record.terminal_producer
    assert producer.claim_data().outcome == "ABORTED"
    assert producer.claim_data().result_sha256 is None
    assert record.resources._invalidated and record.resources._observation is not None
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert not row[0].owner.inspect(row[0]._record(row[1]).handle)[2]
    assert row[0]._record(row[1]).headers is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_input_receipt_is_bound_before_resources_and_cannot_be_replaced(coupled_result):
    remote, row, spine, _ = coupled_result
    assert await remote.begin_ready()
    ticket = spine._registry._operations[row[7].operation]
    record = spine._registry._record(ticket)
    receipt = record.input_receipt_snapshot
    assert receipt.input_sha == hashlib.sha256(row[6]).hexdigest()
    assert b"/" not in receipt.input_sha.encode()
    with pytest.raises(FrameError):
        spine._registry.bind_input_receipt_once(ticket, row[6])
    assert record.input_receipt is receipt and record.input_receipt_snapshot is receipt
    assert record.start_attempted and record.terminal_producer is None


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
@pytest.mark.parametrize("fault", ["observation_copy", "missing_transfer"])
async def test_lookalike_observation_or_missing_transfer_cannot_mint_ok(
    coupled_result, monkeypatch, fault
):
    remote, row, spine, task = coupled_result
    if fault == "observation_copy":
        original = BrokerRegistry.resource_local_observation
        def copied(registry, ticket):
            observation = original(registry, ticket)
            return BrokerLocalDrainObservation(observation.scope, observation.exit_code)
        monkeypatch.setattr(BrokerRegistry, "resource_local_observation", copied)
    else:
        original = BrokerResultWriter.send
        async def missing(writer):
            value = await original(writer)
            writer._transfer_fact = writer._transfer_fact_snapshot = None
            return value
        monkeypatch.setattr(BrokerResultWriter, "send", missing)
    assert await remote.begin_ready()
    with suppress(AuthorityRefusalError, FrameError):
        assert await remote.go()
        await remote.result_ready()
    with pytest.raises(FrameError):
        await task
    record, producer = await wait_producer(spine, row[7])
    assert producer._failed and producer._claim_snapshot is None
    assert record.terminal_producer_snapshot is producer
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert row[0]._record(row[1]).headers is not None



def test_claim_and_nested_binding_are_immutable_values_without_native_alias(claim):
    native = binding()
    data = claim._replace(binding=terminal.claim_binding(native))
    with pytest.raises(AttributeError):
        object.__setattr__(data, "outcome", "ABORTED")
    with pytest.raises(AttributeError):
        object.__setattr__(data.binding, "iid", "changed")
    assert data.outcome == "OK" and data.binding.iid == native.iid
    assert data.binding is not native


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_completed_transfer_scope_replacement_is_refused_before_attributes(
    coupled_result, monkeypatch
):
    remote, row, spine, task = coupled_result
    original = BrokerResultWriter.send
    callbacks = []
    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign transfer scope must not run")
    async def retarget(writer):
        sent = await original(writer)
        writer._scope = writer._scope_snapshot = Foreign()
        return sent
    monkeypatch.setattr(BrokerResultWriter, "send", retarget)
    assert await remote.begin_ready()
    with suppress(AuthorityRefusalError, FrameError):
        assert await remote.go()
        await remote.result_ready()
    with pytest.raises(FrameError):
        await task
    record, producer = await wait_producer(spine, row[7])
    assert callbacks == [] and producer._failed and producer._claim_snapshot is None
    assert record.terminal_producer is producer
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_post_native_binding_field_drift_never_invokes_foreign_equality(
    coupled_result, monkeypatch
):
    from hmp_plugin.presentation_clock import NativeClockOwner

    remote, row, spine, task = coupled_result
    original = NativeClockOwner.sample
    callbacks, changed = [], []
    held_binding = []
    class Foreign:
        def __eq__(self, value):
            callbacks.append(value)
            raise AssertionError("binding fields must be validated before equality")
    def sample(clock):
        now = original(clock)
        ticket = spine._registry._operations.get(row[7].operation)
        if ticket is not None:
            record = spine._registry._record(ticket)
            producer = record.terminal_producer
            if (producer is not None and producer._initialized and not changed
                    and producer._scope_snapshot.clock is clock):
                held_binding.append((record.binding, record.binding.iid))
                object.__setattr__(record.binding, "iid", Foreign())
                changed.append(True)
        return now
    monkeypatch.setattr(NativeClockOwner, "sample", sample)
    try:
        assert await remote.begin_ready()
        with suppress(AuthorityRefusalError, FrameError):
            assert await remote.go()
            await remote.result_ready()
        with pytest.raises(FrameError):
            await task
        assert changed and callbacks == []
        _record, producer = await wait_producer(spine, row[7])
        assert producer._failed and producer._claim_snapshot is None
    finally:
        for bound, iid in held_binding:
            object.__setattr__(bound, "iid", iid)  # fixture disposal only, after refusal


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_receipt_twin_replacement_after_observation_cannot_change_epoch(
    coupled_result, monkeypatch
):
    remote, row, spine, task = coupled_result
    original = BrokerRegistry.resource_local_observation
    held = []
    def retarget(registry, ticket):
        observation = original(registry, ticket)
        record = registry._record(ticket)
        receipt = record.input_receipt_snapshot
        held.append((record, receipt))
        fake = receipt._replace(epoch=receipt.epoch + 1)
        record.input_receipt = record.input_receipt_snapshot = fake
        return observation
    monkeypatch.setattr(BrokerRegistry, "resource_local_observation", retarget)
    try:
        assert await remote.begin_ready()
        with suppress(AuthorityRefusalError, FrameError):
            assert await remote.go()
            await remote.result_ready()
        with pytest.raises(FrameError):
            await task
        record, producer = await wait_producer(spine, row[7])
        assert held and producer._failed and producer._claim_snapshot is None
        assert record.resources._input_receipt_snapshot is held[0][1]
    finally:
        for record, receipt in held:
            record.input_receipt = record.input_receipt_snapshot = receipt


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [2], indirect=True)
async def test_decoded_claim_never_acknowledges_started_registry_debt(coupled_result):
    remote, row, spine, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    _, producer = await wait_producer(spine, row[7])
    decoded = terminal.decode_claim(terminal.encode_claim(producer.claim_data()))
    assert type(decoded) is terminal.StartedClaim
    assert not isinstance(decoded, terminal.LocalStartedProducer)
    with pytest.raises(FrameError):
        spine._registry.acknowledge(row[7])
    assert spine._registry.status(row[7]) is RegistryStatus.PENDING
    assert remote._job_origin_snapshot.state is State.RUNNING
    assert not remote._job_origin_snapshot.credit_released
    assert row[0]._record(row[1]).headers is not None
