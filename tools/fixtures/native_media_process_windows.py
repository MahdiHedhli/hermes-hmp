"""Private source-only process windows; actual root/channel/readback issuers are unbound.

These local records are not parent authority. Every authority boundary calls the
fixed refusing root seam. Tests replace it only in explicitly inert source models.
No native import, process/network startup, configuration or activation route.
The fixed close primitive is unreachable without separately qualified cleanup ownership.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from functools import wraps


class WindowRefusedError(RuntimeError):
    pass


def _require(condition, code):
    if not condition:
        raise WindowRefusedError(code)


def _command_bytes(command):
    _require(type(command) is dict, "WINDOW_COMMAND")
    body = json.dumps(command, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    _require(len(body) <= 4096, "WINDOW_COMMAND_CAP")
    return body


def _require_root_continuation_issuer(_issuance):
    raise WindowRefusedError("ROOT_CONTINUATION_ISSUER_UNBOUND")


def _require_root_persistent_readback(_issuance, _runtime, _actor):
    raise WindowRefusedError("ROOT_PERSISTENT_READBACK_UNBOUND")


def _require_root_process_retirement(_issuance, _previous):
    raise WindowRefusedError("ROOT_PROCESS_RETIREMENT_UNBOUND")


def _require_root_transition(_issuance, _transition):
    raise WindowRefusedError("ROOT_PARENT_TRANSITION_UNBOUND")


def _require_root_handle_acquisition(_issuance, _debt, _handle):
    raise WindowRefusedError("ROOT_HANDLE_ACQUISITION_UNBOUND")


def _require_root_cleanup_ownership(_issuance, _debt):
    raise WindowRefusedError("ROOT_HANDLE_CLEANUP_UNBOUND")


@dataclass(frozen=True, init=False, repr=False)
class _ParentObservation:
    revision: int
    state: tuple

    def __init__(self):
        raise WindowRefusedError("ROOT_PARENT_OBSERVATION_UNBOUND")


@dataclass(frozen=True, repr=False)
class _Transition:
    revision: int
    kind: str
    before: _ParentObservation
    after: tuple


class _HandleDebt:
    def __init__(self, ledger):
        _require(type(ledger) is WindowLedger and ledger._opening, "WINDOW_HANDLE_ISSUER")
        self.ledger, self.issuance = ledger, ledger.window.issuance
        self.handle = None
        self.returned_handle = None
        self.state = "RESERVED"


def _terminal(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except BaseException as error:
            window = (
                self
                if type(self) is vars(self).get("_window_source_type", ProcessWindowLease)
                else vars(self).get("window")
            )
            if window is not None and type(window) is vars(window).get(
                "_window_source_type", ProcessWindowLease
            ):
                window.poison(error)
            if not isinstance(error, Exception):
                raise
        raise WindowRefusedError("WINDOW_UNAVAILABLE") from None

    return wrapped


@dataclass(frozen=True)
class WindowDescription:
    role: str
    purpose: str
    ordinal: int | None
    positions: tuple[int, ...]
    generation: object
    source: object
    config: object
    custody: object
    deadline: float

    def __post_init__(self):
        _require(self.role in ("A", "B"), "WINDOW_ROLE")
        _require(self.purpose in ("LISTENER", "STOPPED_PRODUCER_SEED"), "WINDOW_PURPOSE")
        _require(
            type(self.positions) is tuple
            and all(type(n) is int and n >= 0 for n in self.positions),
            "WINDOW_POSITIONS",
        )
        _require(tuple(sorted(set(self.positions))) == self.positions, "WINDOW_ORDER")
        _require(
            type(self.deadline) in (int, float) and math.isfinite(self.deadline), "WINDOW_DEADLINE"
        )
        if self.purpose == "LISTENER":
            _require(
                type(self.ordinal) is int and 1 <= self.ordinal <= (3 if self.role == "A" else 2),
                "WINDOW_ORDINAL",
            )
        else:
            _require(self.ordinal is None, "WINDOW_NO_LISTENER")


@dataclass(frozen=True, repr=False)
class _ActorRecord:
    name: str
    role: str
    iid: str
    device: str
    user: str
    bearer: str
    p4: str


@dataclass(frozen=True, repr=False)
class _ProducerRecord:
    invocation: str
    profile: str
    raw: str
    receipt_body: bytes
    origin: object


class _JournalState:
    """Pure retained data only; constructing this cannot issue an authority lease."""

    def __init__(self, plan, caps, deadline, clock):
        _require(type(plan) is tuple and all(type(b) is bytes for b in plan), "WINDOW_PLAN")
        _require(
            type(caps) is dict
            and all(type(k) is str and type(v) is int and v >= 0 for k, v in caps.items()),
            "WINDOW_CAPS",
        )
        _require(type(deadline) in (int, float) and math.isfinite(deadline), "WINDOW_DEADLINE")
        keys = []
        for body in plan:
            command = json.loads(body)
            _require(
                _command_bytes(command) == body
                and command.get("role") in ("A", "B")
                and type(command.get("sequence")) is int
                and 1 <= command["sequence"] <= 64,
                "WINDOW_PLAN_KEY",
            )
            keys.append((command["role"], command["sequence"]))
        _require(len(set(keys)) == len(keys), "WINDOW_PLAN_DUPLICATE")
        self.plan, self.caps, self.deadline, self.clock = plan, dict(caps), deadline, clock
        self.issuances = {}
        self.assigned = set()
        self.next_position = 0
        self.consumed = set()
        self.observations = {}
        self.unknown = set()
        self.credits = dict.fromkeys(caps, 0)
        self.held = self.peak = 0
        self.first_failure = None
        self.debts = []
        self.rejected_observations = {}
        self.busy = False
        self.roles = {}
        self.enrolled = {}
        self.produce_claims = set()
        self.seed_claims = set()
        self.grant_claims = set()
        self.producers = {}
        self.actor_records = {}
        self.final_read_started = set()
        self.minted = set()
        self.routed = set()
        self.late_used = set()
        self.last_phases = {}
        self.observation = None
        self.handle_debts = []

    def snapshot(self):
        _require(
            all(
                type(getattr(self, name)) is set
                for name in (
                    "consumed",
                    "assigned",
                    "unknown",
                    "produce_claims",
                    "seed_claims",
                    "grant_claims",
                    "final_read_started",
                    "minted",
                    "routed",
                    "late_used",
                )
            )
            and all(
                type(getattr(self, name)) is dict
                for name in (
                    "last_phases",
                    "enrolled",
                    "observations",
                    "actor_records",
                    "producers",
                )
            )
            and type(self.handle_debts) is list,
            "WINDOW_STATE_TYPES",
        )
        _require(
            type(self.credits) is dict
            and all(type(k) is str and type(v) is int and v >= 0 for k, v in self.credits.items()),
            "WINDOW_CREDITS",
        )
        _require(
            all(type(n) is int and n >= 0 for n in (self.held, self.peak, self.next_position)),
            "WINDOW_STATE",
        )
        return (
            tuple(sorted(self.credits.items())),
            self.held,
            self.peak,
            tuple(sorted(self.consumed)),
            self.next_position,
            tuple(sorted(self.assigned)),
            tuple(sorted(self.last_phases.items())),
            tuple(sorted(self.enrolled.items())),
            tuple(sorted(self.produce_claims)),
            tuple(sorted(self.seed_claims)),
            tuple(sorted(self.grant_claims)),
            tuple(sorted(self.final_read_started)),
            tuple(sorted(self.minted)),
            tuple(sorted(self.routed)),
            tuple(sorted(self.late_used)),
            tuple(sorted(self.unknown)),
            tuple(sorted(self.observations.items())),
            tuple(
                sorted(
                    (name, tuple(vars(record).items()))
                    for name, record in self.actor_records.items()
                )
            ),
            tuple(
                sorted(
                    (name, tuple(vars(record).items())[:-1])
                    for name, record in self.producers.items()
                )
            ),
            tuple((debt.state, debt.handle) for debt in self.handle_debts),
        )


class _RootContinuationIssuance:
    def __init__(self):
        raise WindowRefusedError("ROOT_CONTINUATION_ISSUER_UNBOUND")


class CommandLease:
    def __init__(self, window, position, body):
        _require(type(window) is ProcessWindowLease and window._busy, "WINDOW_COMMAND_ISSUER")
        self.window, self.position, self.body = window, position, body
        self.runtime = None
        self.completed = False
        self.started = False


class ActorContinuationLease:
    def __init__(self, window, record):
        _require(type(window) is ProcessWindowLease and window._busy, "WINDOW_ACTOR_ISSUER")
        _require(type(record) is _ActorRecord, "WINDOW_ACTOR_RECORD")
        self.window, self.record = window, record
        self.snapshot = tuple(vars(record).items())
        self.restored = False

    @_terminal
    def current(self):
        self.window._authority()
        _require(
            self.window._journal.actor_records.get(self.record.name) is self.record
            and tuple(vars(self.record).items()) == self.snapshot,
            "WINDOW_ACTOR_CHANGED",
        )
        return self.record


class ProducerContinuationLease:
    def __init__(self, window, record):
        _require(type(window) is ProcessWindowLease and window._busy, "WINDOW_PRODUCER_ISSUER")
        _require(type(record) is _ProducerRecord, "WINDOW_PRODUCER_RECORD")
        self.window, self.record = window, record
        self.snapshot = tuple(vars(record).items())
        self.used = False

    @_terminal
    def consume(self, runtime):
        self.window.runtime_checkpoint(runtime)
        record = self.record
        _require(
            self.window._journal.producers.get(record.invocation) is record
            and tuple(vars(record).items()) == self.snapshot
            and not self.used,
            "WINDOW_PRODUCER_CHANGED",
        )
        if record.invocation in runtime.raw:
            _require(
                runtime.raw[record.invocation] == record.raw
                and _command_bytes(runtime.producer_receipts[record.invocation])
                == record.receipt_body,
                "WINDOW_PRODUCER_CHANGED",
            )
        self.used = True
        return record.raw, json.loads(record.receipt_body)


class WindowLedger:
    """One view of issued parent data, never an independent allowance or parent proof."""

    def __init__(self, window):
        _require(type(window) is ProcessWindowLease, "WINDOW_LEDGER")
        self.window = window
        window._authority()
        self._handles = set()
        self._opening = False

    @property
    def end(self):
        return self.window.description.deadline

    def tick(self):
        self.window._authority()

    @_terminal
    def charge(self, kind, amount):
        self.tick()
        journal = self.window._journal
        _require(type(amount) is int and amount >= 0 and kind in journal.caps, "WINDOW_CHARGE")
        _require(journal.credits[kind] + amount <= journal.caps[kind], "WINDOW_BUDGET")
        journal.credits[kind] += amount
        self.window._commit("charge")

    @_terminal
    def open(self):
        self.tick()
        journal = self.window._journal
        _require("held" in journal.caps and journal.held < journal.caps["held"], "WINDOW_FD_BUDGET")
        self._opening = True
        try:
            debt = _HandleDebt(self)
        finally:
            self._opening = False
        self._handles.add(debt)
        journal.handle_debts.append(debt)
        journal.held += 1
        journal.peak = max(journal.peak, journal.held)
        self.window._commit("reserve_handle")
        return debt

    def _owned(self, debt):
        _require(
            type(debt) is _HandleDebt
            and debt in self._handles
            and debt.ledger is self
            and debt.issuance is self.window.issuance,
            "WINDOW_HANDLE_NOT_OWNED",
        )

    @_terminal
    def acquired(self, debt, handle):
        self._owned(debt)
        _require(
            debt.state == "RESERVED" and type(handle) is int and handle >= 0, "WINDOW_HANDLE_RETURN"
        )
        # Retain even when the acquisition/checkpoint subsequently refuses.
        debt.handle = debt.returned_handle = handle
        debt.state = "RETURNED_UNKNOWN"
        _require_root_handle_acquisition(self.window.issuance, debt, handle)
        self._owned(debt)
        _require(debt.handle == handle and debt.returned_handle == handle, "WINDOW_HANDLE_CHANGED")
        debt.state = "OWNED"
        self.window._commit("acquire_handle")

    @_terminal
    def close_owned(self, debt):
        self._owned(debt)
        _require(
            debt.state == "OWNED"
            and debt.handle == debt.returned_handle
            and type(debt.handle) is int,
            "WINDOW_HANDLE_NOT_CLOSABLE",
        )
        before = self.window._journal.snapshot()
        observation = self.window._journal.observation
        _require_root_cleanup_ownership(self.window.issuance, debt)
        self._owned(debt)
        _require(
            self.window._journal.snapshot() == before
            and self.window._journal.observation is observation,
            "WINDOW_CLEANUP_CALLBACK_STATE",
        )
        _require(
            debt.state == "OWNED" and debt.handle == debt.returned_handle, "WINDOW_HANDLE_CHANGED"
        )
        # This method owns the fixed primitive; no Boolean/DTO or generic close
        # callback can supply a known-close receipt. Clear eligibility first.
        handle = debt.handle
        debt.state = "CLOSE_ATTEMPTED"
        try:
            os.close(handle)
        except BaseException:
            debt.state = "CLOSE_UNKNOWN"
            raise
        debt.state = "CLOSED"
        _require(self.window._journal.held > 0, "WINDOW_FD_ACCOUNTING")
        self.window._journal.held -= 1
        self.window._commit("known_handle_close")


class ProcessWindowLease:
    @_terminal
    def __init__(self, issuance):
        _require(type(issuance) is _RootContinuationIssuance, "WINDOW_ISSUANCE")
        _require_root_continuation_issuer(issuance)
        journal, description = issuance.journal, issuance.description
        self._journal = journal
        self._window_source_type, self._journal_source_type = ProcessWindowLease, _JournalState
        self.active = None
        _require(
            type(journal) is _JournalState and type(description) is WindowDescription,
            "WINDOW_SOURCE_TYPES",
        )
        _require(journal.issuances.get(issuance) is description, "WINDOW_NOT_ISSUED")
        _require(description.deadline <= journal.deadline, "WINDOW_DEADLINE")
        _require(not journal.first_failure and not journal.busy, "WINDOW_TERMINAL")
        _require(not set(description.positions) & journal.assigned, "WINDOW_OVERLAP")
        _require(all(p < len(journal.plan) for p in description.positions), "WINDOW_PLAN")
        journal.assigned.update(description.positions)
        self.issuance, self._journal, self.description = issuance, journal, description
        self._namespace = globals()
        self._source_shape = tuple(
            (name, self._namespace[name])
            for name in (
                "ProcessWindowLease",
                "WindowLedger",
                "CommandLease",
                "ActorContinuationLease",
                "ProducerContinuationLease",
                "_ActorRecord",
                "_ProducerRecord",
                "_JournalState",
                "_RootContinuationIssuance",
                "_require_root_continuation_issuer",
                "_require_root_persistent_readback",
                "_require_root_process_retirement",
                "_require_root_transition",
                "_require_root_handle_acquisition",
                "_require_root_cleanup_ownership",
                "_ParentObservation",
                "_Transition",
                "_HandleDebt",
            )
        )
        self._issue_types = (issuance.dispatcher_type, issuance.runtime_type)
        self._snapshot = tuple(vars(description).items())
        self._plan, self._caps = journal.plan, tuple(journal.caps.items())
        self._deadline, self._clock = journal.deadline, journal.clock
        self._busy = False
        self.first_failure = None
        self.dispatcher = self.runtime = None
        self.cursor = 0
        self.active = None
        self.last_ticket = None
        self.started = self.stopped = False
        self.actors = {}
        self.producer_leases = {}
        self._commit("issue")
        self.ledger = WindowLedger(self)
        self._authority()

    def poison(self, error):
        journal = vars(self).get("_journal")
        if type(journal) is vars(self).get("_journal_source_type", _JournalState):
            if vars(self).get("first_failure") is None:
                self.first_failure = error
            if journal.first_failure is None:
                journal.first_failure = error
            journal.debts.append(error)
            ticket = vars(self).get("active") or vars(self).get("last_ticket")
            if ticket is not None:
                journal.unknown.add(ticket.position)
                observation = journal.observations.pop(ticket.position, None)
                if observation is not None:
                    journal.rejected_observations[ticket.position] = observation

    def _guard(self, *, allow_terminal=False):
        journal = self._journal
        _require(
            self._namespace is globals()
            and all(self._namespace.get(name) is value for name, value in self._source_shape),
            "WINDOW_SOURCE_CHANGED",
        )
        _require(
            type(self) is self._window_source_type
            and type(self.issuance) is _RootContinuationIssuance,
            "WINDOW_SOURCE_TYPES",
        )
        _require(
            journal.issuances.get(self.issuance) is self.description
            and self.issuance.journal is journal
            and self.issuance.description is self.description,
            "WINDOW_ISSUANCE_CHANGED",
        )
        _require(
            (self.issuance.dispatcher_type, self.issuance.runtime_type) == self._issue_types,
            "WINDOW_SOURCE_TYPES",
        )
        _require(
            (allow_terminal or (self.first_failure is None and journal.first_failure is None))
            and tuple(vars(self.description).items()) == self._snapshot
            and journal.plan is self._plan
            and tuple(journal.caps.items()) == self._caps
            and journal.deadline == self._deadline
            and journal.clock is self._clock,
            "WINDOW_TERMINAL",
        )

    def _authority(self):
        try:
            _require(not self._busy and not self._journal.busy, "WINDOW_REENTRY")
            self._busy = self._journal.busy = True
            self._guard()
            observation = self._journal.observation
            _require(
                type(observation) is _ParentObservation
                and self._journal.snapshot() == observation.state,
                "WINDOW_PARENT_STATE",
            )
            before = self._journal.snapshot()
            _require_root_continuation_issuer(self.issuance)
            self._guard()
            _require(
                self._busy
                and self._journal.busy
                and self._journal.snapshot() == before
                and self._journal.observation is observation,
                "WINDOW_CALLBACK_STATE",
            )
            now = self._journal.clock()
            self._guard()
            _require(
                self._busy
                and self._journal.busy
                and self._journal.snapshot() == before
                and self._journal.observation is observation,
                "WINDOW_CALLBACK_STATE",
            )
            _require(
                type(now) in (int, float)
                and math.isfinite(now)
                and now < self.description.deadline <= self._journal.deadline,
                "WINDOW_DEADLINE",
            )
        except BaseException as error:
            self.poison(error)
            if not isinstance(error, Exception):
                raise
        else:
            return
        finally:
            self._busy = self._journal.busy = False
        raise WindowRefusedError("WINDOW_UNAVAILABLE") from None

    def _commit(self, kind):
        journal = self._journal
        _require(not self._busy and not journal.busy, "WINDOW_REENTRY")
        ordinary = kind != "known_handle_close"
        self._guard(allow_terminal=not ordinary)
        sticky = (self.first_failure, journal.first_failure, len(journal.debts))
        operation = (
            self.active,
            self.last_ticket,
            self.dispatcher,
            self.runtime,
            self.cursor,
            self.started,
            self.stopped,
        )
        before = journal.observation
        _require(type(before) is _ParentObservation, "WINDOW_PARENT_OBSERVATION")
        after = journal.snapshot()
        # Monotonic credit/peak/consumption checks are necessary source guards,
        # never a substitute for the actual parent's immutable observation.
        _require(
            all(dict(after[0])[name] >= value for name, value in before.state[0])
            and after[2] >= before.state[2]
            and set(after[3]) >= set(before.state[3])
            and after[4] >= before.state[4],
            "WINDOW_STATE_REGRESSION",
        )
        transition = _Transition(before.revision + 1, kind, before, after)
        self._busy = journal.busy = True
        try:
            returned = _require_root_transition(self.issuance, transition)
            _require(
                all(
                    current is saved
                    for current, saved in zip(
                        (self.active, self.last_ticket, self.dispatcher, self.runtime),
                        operation[:4],
                        strict=True,
                    )
                )
                and (self.cursor, self.started, self.stopped) == operation[4:],
                "WINDOW_TRANSITION_OPERATION",
            )
            # A normal callback return does not erase a caught nested refusal.
            # Inspect current state directly; never recurse into _authority.
            self._guard(allow_terminal=not ordinary)
            _require(
                self.first_failure is sticky[0]
                and journal.first_failure is sticky[1]
                and len(journal.debts) == sticky[2],
                "WINDOW_TRANSITION_POISON",
            )
            now = journal.clock()
            self._guard(allow_terminal=not ordinary)
            _require(
                self.first_failure is sticky[0]
                and journal.first_failure is sticky[1]
                and len(journal.debts) == sticky[2],
                "WINDOW_TRANSITION_POISON",
            )
            _require(
                all(
                    current is saved
                    for current, saved in zip(
                        (self.active, self.last_ticket, self.dispatcher, self.runtime),
                        operation[:4],
                        strict=True,
                    )
                )
                and (self.cursor, self.started, self.stopped) == operation[4:],
                "WINDOW_TRANSITION_OPERATION",
            )
            if ordinary:
                _require(
                    type(now) in (int, float)
                    and math.isfinite(now)
                    and now < self.description.deadline <= journal.deadline,
                    "WINDOW_TRANSITION_DEADLINE",
                )
            _require(
                self._busy
                and journal.busy
                and journal.snapshot() == after
                and journal.observation is before,
                "WINDOW_CALLBACK_STATE",
            )
            _require(
                type(returned) is _ParentObservation
                and returned.revision == transition.revision
                and returned.state == after,
                "WINDOW_PARENT_OBSERVATION",
            )
            journal.observation = returned
        finally:
            self._busy = journal.busy = False

    @_terminal
    def claim(self, dispatcher):
        self._authority()
        _require(
            self.dispatcher is None and type(dispatcher) is self._issue_types[0], "WINDOW_CLAIMED"
        )
        if self.description.purpose == "LISTENER":
            previous = self._journal.roles.get(self.description.role)
            if previous is not None:
                _require_root_process_retirement(self.issuance, previous)
                self._authority()
            expected = 1 if previous is None else previous.description.ordinal + 1
            _require(self.description.ordinal == expected, "WINDOW_ORDINAL")
            self._journal.roles[self.description.role] = self
        self.dispatcher = dispatcher
        self._commit("claim_window")

    @_terminal
    def consume(self, dispatcher, command):
        self._authority()
        _require(dispatcher is self.dispatcher and self.active is None, "WINDOW_DISPATCHER")
        _require(self.cursor < len(self.description.positions), "WINDOW_COMPLETE")
        position = self.description.positions[self.cursor]
        body = _command_bytes(command)
        self._authority()
        _require(
            position == self._journal.next_position
            and position not in self._journal.consumed
            and body == self._plan[position]
            and command.get("role") == self.description.role,
            "WINDOW_NEXT_COMMAND",
        )
        self._busy = True
        try:
            ticket = CommandLease(self, position, body)
        finally:
            self._busy = False
        self._journal.consumed.add(position)
        self._journal.next_position += 1
        self.cursor += 1
        self.active = self.last_ticket = ticket
        self._commit("consume_command")
        return ticket

    @_terminal
    def checkpoint(self, dispatcher, ticket):
        self._authority()
        _require(
            dispatcher is self.dispatcher
            and type(ticket) is CommandLease
            and ticket.window is self
            and self.active is ticket
            and not ticket.completed
            and ticket.position in self._journal.consumed
            and ticket.body == self._plan[ticket.position],
            "WINDOW_TICKET_CHANGED",
        )

    @_terminal
    def complete(self, ticket, observation):
        self.checkpoint(self.dispatcher, ticket)
        body = json.dumps(
            observation, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        self.checkpoint(self.dispatcher, ticket)
        self._journal.observations[ticket.position] = body
        ticket.completed = True
        self.active = None
        self._commit("complete_command")

    @_terminal
    def actor(self, name):
        self._authority()
        record = self._journal.actor_records.get(name)
        _require(
            type(record) is _ActorRecord
            and record.role == self.description.role
            and name in self._journal.enrolled,
            "WINDOW_ACTOR_UNBOUND",
        )
        if name not in self.actors:
            self._busy = True
            try:
                self.actors[name] = ActorContinuationLease(self, record)
            finally:
                self._busy = False
        return self.actors[name]

    @_terminal
    def producer(self, invocation, profile):
        self._authority()
        record = self._journal.producers.get(invocation)
        _require(
            type(record) is _ProducerRecord and record.profile == profile, "WINDOW_PRODUCER_UNBOUND"
        )
        if invocation not in self.producer_leases:
            self._busy = True
            try:
                self.producer_leases[invocation] = ProducerContinuationLease(self, record)
            finally:
                self._busy = False
        return self.producer_leases[invocation]

    @_terminal
    def advance_phase(self, phase):
        self._authority()
        _require(
            type(phase) is int
            and phase >= self._journal.last_phases.get(self.description.role, -1),
            "WINDOW_PHASE_REGRESSION",
        )
        self._journal.last_phases[self.description.role] = phase
        self._commit("advance_phase")

    @_terminal
    def attach_runtime(self, runtime):
        self._authority()
        _require(
            self.runtime is None and type(runtime) is self._issue_types[1], "WINDOW_RUNTIME_CLAIMED"
        )
        self.runtime = runtime

    @_terminal
    def runtime_checkpoint(self, runtime):
        self._authority()
        _require(runtime is self.runtime and runtime.window is self, "WINDOW_RUNTIME_CHANGED")

    @_terminal
    def restore_actor(self, runtime, lease):
        self.runtime_checkpoint(runtime)
        _require(
            type(lease) is ActorContinuationLease and lease.window is self and not lease.restored,
            "WINDOW_ACTOR_CLAIMED",
        )
        record = lease.current()
        _require_root_persistent_readback(self.issuance, runtime, lease)
        self.runtime_checkpoint(runtime)
        lease.current()
        lease.restored = True
        return record

    @_terminal
    def before_action(self, runtime, command):
        self.runtime_checkpoint(runtime)
        op = command["op"]
        journal = self._journal
        ticket = self.active
        _require(
            type(ticket) is CommandLease
            and ticket.window is self
            and not ticket.started
            and ticket.body == _command_bytes(command),
            "WINDOW_ACTION_TICKET",
        )
        ticket.started = True
        ticket.runtime = runtime
        _require(not self.stopped, "WINDOW_STOPPED")
        for name in tuple(journal.actor_records):
            if journal.actor_records[name].role == self.description.role:
                lease = self.actor(name)
                if not lease.restored:
                    runtime.restore_actor(lease)
                else:
                    _require_root_persistent_readback(self.issuance, runtime, lease)
                self.runtime_checkpoint(runtime)
                lease.current()
        if op in ("SEED", "GRANT", "OWN_READ", "LATE_OWN_READ", "CROSS_PROBE", "REVOKE", "ROTATE"):
            _require(
                command["actor"] in journal.actor_records and command["actor"] in runtime.actors,
                "WINDOW_ACTOR_UNBOUND",
            )
        if op == "START_GATEWAY":
            _require(
                self.description.purpose == "LISTENER"
                and not self.started
                and self.description.role not in journal.final_read_started,
                "WINDOW_RESTART",
            )
            self.started = True
        elif op == "STOP_GATEWAY":
            _require(
                self.description.ordinal != (3 if self.description.role == "A" else 2)
                and self.description.role not in journal.final_read_started
                and self.description.role not in journal.minted
                and not self.stopped,
                "WINDOW_FINAL_STOP",
            )
            self.stopped = True
        elif op == "BIND_ACTOR":
            _require(command["actor"] not in journal.enrolled, "WINDOW_ACTOR_REBIND")
            journal.enrolled[command["actor"]] = None
        elif op == "PRODUCE":
            invocation = command["args"]["invocation"]
            _require(invocation not in journal.produce_claims, "WINDOW_PRODUCER_REPLAY")
            journal.produce_claims.add(invocation)
        elif op == "SEED":
            profile = command["profile"]
            _require(profile not in journal.seed_claims, "WINDOW_SEED_REPLAY")
            lease = self.producer(command["args"]["invocation"], profile)
            raw, receipt = lease.consume(runtime)
            runtime.raw[lease.record.invocation] = raw
            runtime.producer_receipts[lease.record.invocation] = receipt
            journal.seed_claims.add(profile)
        elif op == "GRANT":
            key = (command["actor"], command["profile"])
            _require(key not in journal.grant_claims, "WINDOW_GRANT_REPLAY")
            journal.grant_claims.add(key)
        elif op in ("OWN_READ", "LATE_OWN_READ") and command["phase"] != "CLOSED_NONOWNER_CASES":
            journal.final_read_started.add(self.description.role)
        if op == "LATE_OWN_READ":
            permit = command["args"]["permit"]
            _require(permit not in journal.late_used, "WINDOW_LATE_REPLAY")
            journal.late_used.add(permit)
        self._commit("claim_action")
        self.runtime_checkpoint(runtime)

    @_terminal
    def after_action(self, runtime, command, observation):
        self.runtime_checkpoint(runtime)
        journal = self._journal
        op = command["op"]
        _require(
            type(self.active) is CommandLease
            and self.active.runtime is runtime
            and self.active.started
            and self.active.body == _command_bytes(command),
            "WINDOW_ACTION_TICKET",
        )
        if op == "BIND_ACTOR":
            actor = runtime.actors[command["actor"]]
            record = _ActorRecord(
                actor.name,
                self.description.role,
                actor.iid,
                actor.device_id,
                actor.user_id,
                actor.bearer,
                command["args"]["p4CaptureSHA256"],
            )
            _require(
                journal.enrolled.get(actor.name) is None
                and actor.name not in journal.actor_records,
                "WINDOW_ACTOR_REBIND",
            )
            journal.actor_records[actor.name] = record
            journal.enrolled[actor.name] = record.p4
        elif op == "PRODUCE":
            invocation = command["args"]["invocation"]
            _require(invocation not in journal.producers, "WINDOW_PRODUCER_REPLAY")
            record = _ProducerRecord(
                invocation,
                command["profile"],
                runtime.raw[invocation],
                json.dumps(
                    runtime.producer_receipts[invocation],
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode(),
                self.active,
            )
            journal.producers[invocation] = record
        if runtime.minted:
            journal.minted.add(self.description.role)
        journal.routed.update(runtime.routed)
        self._commit("action_result")
        self.runtime_checkpoint(runtime)
