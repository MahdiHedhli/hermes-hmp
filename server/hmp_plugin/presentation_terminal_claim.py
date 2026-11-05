"""Typed local started-reader observations and closed claim data; no release.

A decoded claim is not a producer qualification, remote custody capability,
native permission or journal ACK. Wire/COMPLETE/publication remain closed.
"""
from __future__ import annotations

import hashlib
import json
from typing import NamedTuple

from .presentation_broker_codec import TERMINAL_LIMIT, BrokerBinding, _binding
from .presentation_cancel_budget import CLEANUP_NS, MAX_NS
from .presentation_input_v3 import decode_input_v3
from .presentation_jobs import _PROFILE, INPUT_LIMIT, FrameError, _digest, _json

CLAIM_LIMIT = TERMINAL_LIMIT
_INPUT_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_STARTED_CLAIM_REFUSED")


class _InputReceipt(NamedTuple):
    mint: object
    record: object
    binding: BrokerBinding
    record_scope: tuple
    challenge: str
    epoch: int
    input_sha: str
    worker_source_sha: str
    expected_avatar_sha: object

    def __repr__(self):
        return "<OperationInputReceipt redacted>"


def bind_input(record, packet):
    from .presentation_broker_registry import _Record

    _require(type(record) is _Record and type(packet) is bytes
             and 4 <= len(packet) <= INPUT_LIMIT + 4)
    _binding(record.binding)
    _require(type(record.profile) is str and type(record.kind) is str
             and type(record.deadline_ns) is int)
    row = decode_input_v3(packet)
    _require((row["iid"], row["profile"], row["operation"], row["deadline_ns"])
             == (record.binding.iid, record.profile, record.kind, record.deadline_ns)
             and ((record.kind == "METADATA" and row["expected_avatar_sha"] is None)
                  or (record.kind == "AVATAR" and type(row["expected_avatar_sha"]) is str)))
    return _InputReceipt(_INPUT_MINT, record, record.binding, record.snapshot, row["challenge"],
                         row["epoch"], hashlib.sha256(packet).hexdigest(),
                         row["source_manifest_sha"], row["expected_avatar_sha"])


def input_current(record, packet=None):
    from .presentation_broker_registry import _Record

    _require(type(record) is _Record)
    receipt = record.input_receipt_snapshot
    _binding(record.binding)
    _require(type(receipt) is _InputReceipt and receipt.mint is _INPUT_MINT
             and record.input_receipt is receipt and receipt.record is record
             and receipt.binding is record.binding and receipt.record_scope is record.snapshot
             and type(record.snapshot) is tuple and len(record.snapshot) == 8
             and all(type(v) is str for v in record.snapshot[:7])
             and type(record.snapshot[7]) is int
             and type(record.profile) is str and type(record.kind) is str
             and type(record.deadline_ns) is int
             and (record.profile, record.kind, record.deadline_ns) == record.snapshot[5:])
    if packet is not None:
        _require(type(packet) is bytes and 4 <= len(packet) <= INPUT_LIMIT + 4
                 and hashlib.sha256(packet).hexdigest() == receipt.input_sha)
        row = decode_input_v3(packet)
        _require((row["challenge"], row["epoch"], row["source_manifest_sha"],
                  row["expected_avatar_sha"])
                 == (receipt.challenge, receipt.epoch, receipt.worker_source_sha,
                     receipt.expected_avatar_sha))
    return receipt


class _ClaimBinding(NamedTuple):
    iid: str
    listener: str
    broker: str
    channel: str
    operation: str


def claim_binding(binding):
    _binding(binding)
    return _ClaimBinding(binding.iid, binding.listener, binding.broker,
                         binding.channel, binding.operation)


class StartedClaim(NamedTuple):
    binding: _ClaimBinding
    profile: str
    operation_kind: str
    deadline_ns: int
    challenge: str
    epoch: int
    input_sha256: str
    worker_source_sha256: str
    installation_generation: str
    clock_domain_sha256: str
    outcome: str
    exit_code: int
    result_sha256: str | None

    def __repr__(self):
        return "<StartedClaim data-only redacted>"


def _values(claim):
    _require(type(claim) is StartedClaim)
    _require(type(claim.binding) is _ClaimBinding)
    _binding(BrokerBinding(*claim.binding))
    _require(type(claim.profile) is str and _PROFILE.fullmatch(claim.profile) is not None
             and type(claim.operation_kind) is str
             and claim.operation_kind in ("METADATA", "AVATAR")
             and type(claim.deadline_ns) is int and 0 < claim.deadline_ns <= MAX_NS - CLEANUP_NS
             and type(claim.epoch) is int and 1 <= claim.epoch < 1 << 63
             and type(claim.outcome) is str and claim.outcome in ("OK", "ABORTED")
             and type(claim.exit_code) is int and -255 <= claim.exit_code <= 255)
    for value in (claim.challenge, claim.input_sha256, claim.worker_source_sha256,
                  claim.installation_generation, claim.clock_domain_sha256):
        _digest(value)
    if claim.outcome == "OK":
        _require(claim.exit_code == 0)
        _digest(claim.result_sha256)
    else:
        _require(claim.result_sha256 is None)
    b = claim.binding
    return {"schema": 1, "kind": "STARTED_READER_TERMINAL", "iid": b.iid,
            "listener": b.listener, "broker": b.broker, "channel": b.channel,
            "operation": b.operation, "profile": claim.profile,
            "operation_kind": claim.operation_kind,
            "deadline_ns": claim.deadline_ns, "challenge": claim.challenge, "epoch": claim.epoch,
            "input_sha256": claim.input_sha256, "worker_source_sha256": claim.worker_source_sha256,
            "installation_generation": claim.installation_generation,
            "clock_domain_sha256": claim.clock_domain_sha256, "outcome": claim.outcome,
            "exit_code": claim.exit_code, "result_sha256": claim.result_sha256}


def encode_claim(claim):
    raw = json.dumps(_values(claim), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(len(raw) <= CLAIM_LIMIT)
    return raw


def decode_claim(raw):
    row = _json(raw, CLAIM_LIMIT)
    keys = {"schema", "kind", "iid", "listener", "broker", "channel", "operation", "profile",
            "operation_kind", "deadline_ns", "challenge", "epoch", "input_sha256",
            "worker_source_sha256", "installation_generation", "clock_domain_sha256",
            "outcome", "exit_code", "result_sha256"}
    _require(row.keys() == keys and type(row["schema"]) is int and row["schema"] == 1
             and type(row["kind"]) is str and row["kind"] == "STARTED_READER_TERMINAL")
    claim = StartedClaim(_ClaimBinding(row["iid"], row["listener"], row["broker"], row["channel"],
        row["operation"]), row["profile"], row["operation_kind"], row["deadline_ns"],
        row["challenge"],
        row["epoch"], row["input_sha256"], row["worker_source_sha256"],
        row["installation_generation"], row["clock_domain_sha256"], row["outcome"],
        row["exit_code"],
        row["result_sha256"])
    _require(encode_claim(claim) == raw)
    return claim


class _ProducerScope(NamedTuple):
    service: object
    connection: object
    registry: object
    ticket: object
    record: object
    resources: object
    resources_scope: tuple
    process: object
    channel: object
    control: object
    control_scope: tuple
    receipt: _InputReceipt
    clock: object
    domain: object
    domain_values: tuple
    enrollment: object
    values: tuple
    records: dict
    task: object


class LocalStartedProducer:
    """One retained local observation producer; exposes data, no completion API."""

    @classmethod
    def retain(cls, service, connection):
        from .presentation_broker_registry import BrokerRegistry
        from .presentation_broker_service import BrokerServiceSpine, _Connection

        _require(cls is LocalStartedProducer and type(service) is BrokerServiceSpine
                 and type(connection) is _Connection)
        registry = service._registry
        _require(type(registry) is BrokerRegistry)
        BrokerRegistry._enter(registry)
        try:
            record = BrokerRegistry._record(registry, connection.ticket)
            _require(record.terminal_producer is None and record.terminal_producer_snapshot is None)
            producer = LocalStartedProducer.__new__(LocalStartedProducer)
            record.terminal_producer = record.terminal_producer_snapshot = producer
        finally:
            registry._lock.release()
        LocalStartedProducer.__init__(producer, service, connection, record)
        return producer

    def __init__(self, service, connection, record):
        import asyncio

        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_broker_resources import BrokerReaderResources
        from .presentation_broker_service import SocketChannel

        self._scope = self._scope_snapshot = None
        self._observation = self._observation_snapshot = None
        self._claim = self._claim_snapshot = None
        self._transfer = self._transfer_snapshot = None
        self._initialized = self._failed = False
        try:
            control, channel = connection.cancel_owner, connection.channel_snapshot
            _require(type(control) is BrokerCancellationOwner and type(channel) is SocketChannel
                     and type(record.resources) is BrokerReaderResources)
            BrokerCancellationOwner._guard(control, cleanup=True)
            receipt = input_current(record)
            _require(record.resources._input_receipt_origin is receipt
                     and record.resources._input_receipt_snapshot is receipt)
            clock = SocketChannel._qualified_clock(channel)
            self._scope = self._scope_snapshot = _ProducerScope(
                service, connection, service._registry, connection.ticket, record, record.resources,
                record.resources._scope_snapshot, record.owner, channel, control,
                control._scope_snapshot, receipt, clock,
                clock._domain_snapshot, clock._domain_values, channel._enrollment_snapshot,
                channel._values_snapshot, service._registry._records, asyncio.current_task())
            self._initialized = True
            LocalStartedProducer._current(self)
            from .presentation_broker_registry import BrokerRegistry

            observation = BrokerRegistry.resource_local_observation(
                self._scope.registry, self._scope.ticket)
            self._observation = self._observation_snapshot = observation
            LocalStartedProducer._guard(self)
            _require(BrokerReaderResources.validates_local(
                self._scope.resources, record, observation) is True)
            caused = LocalStartedProducer._current(self)
            s = self._scope_snapshot
            if caused:
                _require(s.resources._invalidated is True)
                outcome, digest = "ABORTED", None
            else:
                from .presentation_result_transport import (
                    _TRANSFER_MINT,
                    BrokerResultWriter,
                    _CompletedResultTransfer,
                    _WriterScope,
                )

                writer = connection.result_writer_snapshot
                _require(type(writer) is BrokerResultWriter)
                BrokerResultWriter._guard(writer)  # metadata-only original scope fence
                fact = writer._transfer_fact_snapshot
                _require(type(fact) is _CompletedResultTransfer and fact.mint is _TRANSFER_MINT
                         and fact is writer._transfer_fact and fact.writer is writer
                         and type(fact.scope) is _WriterScope
                         and fact.scope is writer._scope_snapshot and fact.scope.record is record
                         and fact.scope.connection is connection and fact.scope.channel is channel
                         and fact.scope.control is control and fact.scope.task is s.task
                         and writer._write_completed is True and writer._failed is False
                         and s.resources._normal_complete is True
                         and s.resources._invalidated is False)
                input_current(record, fact.scope.packet)
                self._transfer = self._transfer_snapshot = fact
                outcome, digest = "OK", fact.sha256
            domain = s.domain_values
            _require(type(domain) is tuple and len(domain) == 4
                     and type(domain[0]) is str and type(domain[1]) is str
                     and type(domain[2]) is bytes and len(domain[2]) <= 64
                     and (domain[3] is None or (type(domain[3]) is tuple and len(domain[3]) == 2
                          and all(type(v) is int and 0 <= v < 1 << 63 for v in domain[3]))))
            domain_wire = json.dumps((domain[0], domain[1], domain[2].hex(), domain[3]),
                                     separators=(",", ":"), ensure_ascii=True).encode("ascii")
            domain_sha = hashlib.sha256(domain_wire).hexdigest()
            # Native/clock boundaries cannot silently change outcome during mint.
            _require(LocalStartedProducer._current(self) is caused)
            claim = StartedClaim(claim_binding(record.binding), record.profile, record.kind,
                record.deadline_ns,
                receipt.challenge, receipt.epoch, receipt.input_sha, receipt.worker_source_sha,
                s.values[7], domain_sha, outcome, observation.exit_code, digest)
            encode_claim(claim)  # closed-data validation before the sole immutable outcome mint
            self._claim = self._claim_snapshot = claim
        except BaseException:
            self._failed = True  # retained producer allocation, no second outcome or release
            raise FrameError("BI1_STARTED_PRODUCER_REFUSED") from None

    def __repr__(self):
        return "<LocalStartedProducer no-release redacted>"

    def _guard(self):
        import asyncio

        from .presentation_broker_cancel import BrokerCancellationOwner
        from .presentation_broker_child import BrokerChildOwner, ChildWaitObservation
        from .presentation_broker_registry import BrokerRegistry, BrokerTicket, _Record
        from .presentation_broker_resources import (
            BrokerLocalDrainObservation,
            BrokerReaderResources,
        )
        from .presentation_broker_service import (
            BrokerServiceSpine,
            SocketChannel,
            _Connection,
            _values_shape,
        )
        from .presentation_clock import NativeClockOwner
        from .presentation_remote_cleanup import _TASK

        s = self._scope
        _require(self._initialized is True and self._failed is False
                 and type(s) is _ProducerScope and s is self._scope_snapshot
                 and type(s.service) is BrokerServiceSpine and type(s.connection) is _Connection
                 and type(s.registry) is BrokerRegistry and type(s.ticket) is BrokerTicket
                 and type(s.record) is _Record and type(s.resources) is BrokerReaderResources
                 and type(s.process) is BrokerChildOwner
                 and type(s.control) is BrokerCancellationOwner
                 and type(s.channel) is SocketChannel and type(s.clock) is NativeClockOwner
                 and type(s.task) is _TASK and asyncio.current_task() is s.task
                 and s.connection.task is s.task and s.connection.ticket is s.ticket
                 and s.service._registry is s.registry
                 and type(s.records) is dict and s.registry._records is s.records
                 and s.records.get(s.ticket) is s.record
                 and s.record.terminal_producer is self
                 and s.record.terminal_producer_snapshot is self
                 and s.record.unknown is False and s.record.resources is s.resources
                 and s.record.resources_snapshot is s.resources
                 and type(s.resources_scope) is tuple and len(s.resources_scope) == 8
                 and s.resources._scope is s.resources_scope
                 and s.resources._scope_snapshot is s.resources_scope
                 and s.record.owner is s.process and s.record.owner_snapshot is s.process
                 and s.connection.channel is s.channel
                 and s.connection.channel_snapshot is s.channel
                 and s.connection.cancel_owner is s.control
                 and type(s.control_scope) is tuple and len(s.control_scope) == 10
                 and s.control._scope_snapshot is s.control_scope and s.control_scope[0] is s.record
                 and s.channel._clock_owner_snapshot is s.clock
                 and s.channel._enrollment_snapshot is s.enrollment
                 and s.channel._values_snapshot is s.values
                 and _values_shape(s.values) and s.values[8] == 2
                 and s.clock._domain_snapshot is s.domain and s.clock._domain is s.domain
                 and s.clock._domain_values is s.domain_values
                 and self._observation is self._observation_snapshot
                 and self._claim is self._claim_snapshot
                 and self._transfer is self._transfer_snapshot)
        _require(input_current(s.record) is s.receipt
                 and s.resources._input_receipt_origin is s.receipt
                 and s.resources._input_receipt_snapshot is s.receipt)
        BrokerServiceSpine._metadata(s.service)
        BrokerCancellationOwner._guard(s.control, cleanup=True)
        _require(SocketChannel._qualified_clock(s.channel) is s.clock)
        if self._observation is not None:
            observation = self._observation
            _require(type(observation) is BrokerLocalDrainObservation
                     and s.resources._observation is observation
                     and s.resources._observation_identity is observation
                     and observation.scope is s.resources_scope
                     and type(observation.exit_code) is int
                     and type(s.resources._wait) is ChildWaitObservation
                     and s.resources._wait is s.resources._wait_identity
                     and type(s.resources._wait.exit_code) is int
                     and observation.exit_code == s.resources._wait.exit_code)

    def _current(self):
        from .presentation_cancel_budget import CancellationBudget
        from .presentation_clock import NativeClockOwner

        LocalStartedProducer._guard(self)
        s = self._scope_snapshot
        budget = s.control_scope[3]
        _, _, end, failed = CancellationBudget.inspect(budget)
        _require(failed is False)
        now = (NativeClockOwner.sample(s.clock) if end is None
               else NativeClockOwner.cleanup_sample(s.clock))
        LocalStartedProducer._guard(self)
        original, _, end, failed = CancellationBudget.inspect(budget)
        _require(failed is False and type(now) is int and original == s.record.deadline_ns
                 and 0 <= now < (original if end is None else end))
        return end is not None

    def claim_data(self):
        """Immutable historical claim data only; no current authorization/closure API."""
        _require(self._initialized is True and self._failed is False
                 and type(self._claim) is StartedClaim and self._claim is self._claim_snapshot)
        return self._claim
