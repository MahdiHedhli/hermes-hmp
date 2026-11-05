"""Source-only broker admission/retention, never phone rights or remote closure.

No service imports this. Outer authenticated original/STATUS grammar is mandatory
before lookup/ACK. Started owners have deliberately NO terminal-release API until
the separately reviewed actual resource binder exists. Keep this registry alive.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType

from .presentation_broker_child import BrokerChildOwner, BrokerReaderStreams
from .presentation_broker_codec import BrokerBinding, _binding
from .presentation_broker_lifecycle import ReplayWindow
from .presentation_broker_resources import BrokerReaderResources
from .presentation_child_launch import ChildLaunch, child_launch, parser_package_path
from .presentation_jobs import (
    _PROFILE,
    MAX_AVATAR,
    MAX_METADATA,
    MAX_PROCESSES,
    MAX_TERMINAL_JOURNAL,
    MAX_WAITING,
    FrameError,
)


class BrokerTicket:
    __slots__ = ()


class RegistryStatus(Enum):
    PENDING = "pending"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class _State(Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    TERMINAL_UNLAUNCHED = "terminal_unlaunched"


@dataclass(frozen=True)
class RegistryCounts:
    waiting: int
    active: int
    metadata: int
    avatar: int
    terminal: int
    unknown: int


@dataclass(slots=True)
class _Record:
    binding: BrokerBinding
    profile: str
    kind: str
    deadline_ns: int
    snapshot: tuple[str | int, ...]
    owner: BrokerChildOwner | None = None
    owner_snapshot: BrokerChildOwner | None = None
    state: _State = _State.QUEUED
    start_attempted: bool = False
    unknown: bool = False
    managed: bool = False
    resources: BrokerReaderResources | None = None
    resources_snapshot: BrokerReaderResources | None = None
    resources_ready: bool = False


def _recipe_value(recipe: ChildLaunch) -> tuple:
    # Validate exact closed primitives BEFORE comparison/hash/coercion/callback.
    if (
        type(recipe) is not ChildLaunch
        or type(recipe.argv) is not tuple
        or not 5 <= len(recipe.argv) <= 8
        or any(type(value) is not str for value in recipe.argv)
        or type(recipe.environment) is not MappingProxyType
        or any(type(k) is not str or type(v) is not str for k, v in recipe.environment.items())
        or type(recipe.close_fds) is not bool
        or type(recipe.start_new_session) is not bool
        or type(recipe.pass_fds) is not tuple
        or recipe.pass_fds != ()
    ):
        raise FrameError("BI1_BROKER_REGISTRY_RECIPE_REFUSED")
    return (
        recipe.argv,
        tuple(sorted(recipe.environment.items())),
        recipe.close_fds,
        recipe.pass_fds,
        recipe.start_new_session,
    )


def _signature_valid(value: tuple) -> bool:
    return (
        type(value) is tuple
        and len(value) == 5
        and type(value[0]) is tuple
        and all(type(v) is str for v in value[0])
        and type(value[1]) is tuple
        and all(
            type(pair) is tuple and len(pair) == 2 and all(type(v) is str for v in pair)
            for pair in value[1]
        )
        and type(value[2]) is bool
        and type(value[3]) is tuple
        and value[3] == ()
        and type(value[4]) is bool
    )


def _values(binding: BrokerBinding, profile: str, kind: str, deadline_ns: int) -> tuple:
    _binding(binding)
    if (
        type(profile) is not str
        or _PROFILE.fullmatch(profile) is None
        or type(kind) is not str
        or kind not in ("METADATA", "AVATAR")
        or type(deadline_ns) is not int
        or not 0 < deadline_ns < (1 << 63)
    ):
        raise FrameError("BI1_BROKER_REGISTRY_INPUT_REFUSED")
    return (
        binding.iid,
        binding.listener,
        binding.broker,
        binding.channel,
        binding.operation,
        profile,
        kind,
        deadline_ns,
    )


class BrokerRegistry:
    def __init__(self, scope: BrokerBinding, *, parser_package: str | None = None):
        _binding(scope)
        self._scope = (scope.iid, scope.listener, scope.broker)
        self._scope_snapshot = self._scope
        self._context = (os.getpid(), os.getpgrp())
        self._context_snapshot = self._context
        self._parser = None if parser_package is None else parser_package_path(parser_package)
        self._recipe = replace(child_launch(self._parser), start_new_session=False)
        self._recipe_snapshot = self._recipe
        self._recipe_refs = (
            self._recipe.argv,
            self._recipe.environment,
            self._recipe.close_fds,
            self._recipe.pass_fds,
            self._recipe.start_new_session,
        )
        self._recipe_values = _recipe_value(self._recipe)
        self._replay = ReplayWindow(scope)
        self._replay_snapshot = self._replay
        self._parser_snapshot = self._parser
        self._records: dict[BrokerTicket, _Record] = {}
        self._operations: dict[str, BrokerTicket] = {}
        self._lock = threading.Lock()
        self._poisoned = False

    def _poison(self) -> None:
        self._poisoned = True
        raise FrameError("BI1_BROKER_REGISTRY_UNCERTAIN")

    def _check(self) -> None:
        try:
            self._check_state()
        except FrameError:
            self._poison()
        except BaseException:
            self._poison()

    def _check_state(self) -> None:
        if (
            type(self._poisoned) is not bool
            or self._poisoned
            or self._scope is not self._scope_snapshot
            or type(self._scope) is not tuple
            or len(self._scope) != 3
            or any(type(value) is not str for value in self._scope)
            or self._context is not self._context_snapshot
            or type(self._context) is not tuple
            or len(self._context) != 2
            or any(type(value) is not int for value in self._context)
            or (os.getpid(), os.getpgrp()) != self._context
            or self._parser is not self._parser_snapshot
            or type(self._replay) is not ReplayWindow
            or self._replay is not self._replay_snapshot
            or type(self._recipe) is not ChildLaunch
            or self._recipe is not self._recipe_snapshot
            or type(self._recipe_refs) is not tuple
            or len(self._recipe_refs) != 5
            or any(
                a is not b
                for a, b in zip(
                    (
                        self._recipe.argv,
                        self._recipe.environment,
                        self._recipe.close_fds,
                        self._recipe.pass_fds,
                        self._recipe.start_new_session,
                    ),
                    self._recipe_refs,
                    strict=True,
                )
            )
            or not _signature_valid(self._recipe_values)
            or _recipe_value(self._recipe) != self._recipe_values
            or type(self._records) is not dict
            or type(self._operations) is not dict
            or len(self._records) > MAX_TERMINAL_JOURNAL
            or len(self._operations) != len(self._records)
        ):
            self._poison()
        # Validate ALL key types before any dictionary lookup can call foreign equality.
        if any(
            type(t) is not BrokerTicket or type(r) is not _Record for t, r in self._records.items()
        ):
            self._poison()
        if any(
            type(k) is not str or type(t) is not BrokerTicket for k, t in self._operations.items()
        ):
            self._poison()
        for ticket, record in self._records.items():
            if (
                type(record.snapshot) is not tuple
                or len(record.snapshot) != 8
                or any(type(value) is not str for value in record.snapshot[:7])
                or type(record.snapshot[7]) is not int
                or _values(record.binding, record.profile, record.kind, record.deadline_ns)
                != record.snapshot
                or record.snapshot[:3] != self._scope
                or self._operations.get(record.binding.operation) is not ticket
                or type(record.state) is not _State
                or type(record.start_attempted) is not bool
                or type(record.unknown) is not bool
                or type(record.managed) is not bool
                or type(record.resources_ready) is not bool
                or record.resources is not record.resources_snapshot
                or (
                    record.resources is not None
                    and type(record.resources) is not BrokerReaderResources
                )
                or (record.resources_ready and (not record.managed or record.resources is None))
                or (record.resources is not None and not record.managed)
                or record.owner is not record.owner_snapshot
                or (record.owner is not None and type(record.owner) is not BrokerChildOwner)
                or (record.owner is None and not record.unknown)
                or (record.state is _State.QUEUED and record.start_attempted)
                or (record.state is _State.ACTIVE and not record.start_attempted)
                or (
                    record.state is _State.TERMINAL_UNLAUNCHED
                    and (record.start_attempted or record.unknown)
                )
            ):
                self._poison()
        for key, ticket in self._operations.items():
            if (
                type(key) is not str
                or type(ticket) is not BrokerTicket
                or ticket not in self._records
            ):
                self._poison()
        counts = self._counts()
        profiles = [r.profile for r in self._records.values() if r.state is _State.ACTIVE]
        if (
            counts.waiting > MAX_WAITING
            or counts.active > MAX_PROCESSES
            or counts.metadata > MAX_METADATA
            or counts.avatar > MAX_AVATAR
            or len(set(profiles)) != len(profiles)
        ):
            self._poison()

    def _enter(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._poison()
        try:
            self._check()
        except BaseException:
            self._lock.release()
            raise

    def _counts(self) -> RegistryCounts:
        records = self._records.values()
        return RegistryCounts(
            sum(r.state is _State.QUEUED for r in records),
            sum(r.state is _State.ACTIVE for r in records),
            sum(r.state is _State.ACTIVE and r.kind == "METADATA" for r in records),
            sum(r.state is _State.ACTIVE and r.kind == "AVATAR" for r in records),
            sum(r.state is _State.TERMINAL_UNLAUNCHED for r in records),
            sum(r.unknown for r in records),
        )

    @property
    def counts(self) -> RegistryCounts:
        self._enter()
        try:
            return self._counts()
        finally:
            self._lock.release()

    def _scope_binding(self, binding: BrokerBinding) -> None:
        _binding(binding)
        if (binding.iid, binding.listener, binding.broker) != self._scope:
            raise FrameError("BI1_BROKER_REGISTRY_SCOPE_REFUSED")

    def reserve(
        self, binding: BrokerBinding, profile: str, kind: str, deadline_ns: int
    ) -> BrokerTicket:
        self._enter()
        try:
            values = _values(binding, profile, kind, deadline_ns)
            self._scope_binding(binding)
            self._replay.consume(binding)  # burn even on later capacity/deadline refusal
            now = time.monotonic_ns()
            if (
                not now < deadline_ns <= now + 2_000_000_000
                or len(self._records) >= MAX_TERMINAL_JOURNAL
                or self._counts().waiting >= MAX_WAITING
            ):
                raise FrameError("BI1_BROKER_REGISTRY_ADMISSION_REFUSED")
            copied = BrokerBinding(*values[:5])
            ticket = BrokerTicket()
            record = _Record(copied, profile, kind, deadline_ns, values, unknown=True)
            self._records[ticket] = record
            self._operations[copied.operation] = ticket
            try:
                owner = BrokerChildOwner(
                    record, parser_package=self._parser, deadline_ns=record.deadline_ns
                )
                record.owner = record.owner_snapshot = owner
                if _recipe_value(owner.startup_recipe) != self._recipe_values:
                    self._poison()
                self._check()
                record.unknown = False
            except BaseException:
                record.unknown = True  # retained, never reclassified unlaunched
                raise FrameError("BI1_BROKER_REGISTRY_OWNER_UNCERTAIN") from None
            return ticket
        finally:
            self._lock.release()

    def _record(self, ticket: BrokerTicket) -> _Record:
        if type(ticket) is not BrokerTicket or ticket not in self._records:
            raise FrameError("BI1_BROKER_REGISTRY_TICKET_REFUSED")
        return self._records[ticket]

    def start(self, ticket: BrokerTicket) -> BrokerReaderStreams:
        self._enter()
        try:
            record = self._record(ticket)
            counts = self._counts()
            if (
                record.state is not _State.QUEUED
                or record.managed
                or record.unknown
                or record.owner is None
                or record.start_attempted
                or time.monotonic_ns() >= record.deadline_ns
                or counts.active >= MAX_PROCESSES
                or (record.kind == "METADATA" and counts.metadata >= MAX_METADATA)
                or (record.kind == "AVATAR" and counts.avatar >= MAX_AVATAR)
                or any(
                    r.state is _State.ACTIVE and r.profile == record.profile
                    for r in self._records.values()
                )
            ):
                raise FrameError("BI1_BROKER_REGISTRY_START_REFUSED")
            record.state = _State.ACTIVE
            record.start_attempted = True
            try:
                if not record.owner.owns(record):
                    self._poison()
                self._check()
                if time.monotonic_ns() >= record.deadline_ns:
                    raise FrameError("BI1_BROKER_REGISTRY_START_DEADLINE")
                record.owner.start()
                self._check()
                if time.monotonic_ns() >= record.deadline_ns:
                    raise FrameError("BI1_BROKER_REGISTRY_START_DEADLINE")
                return record.owner.streams
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_START_UNCERTAIN") from None
        finally:
            self._lock.release()

    def start_resources(self, ticket: BrokerTicket) -> None:
        self._enter()
        try:
            record = self._record(ticket)
            counts = self._counts()
            if (
                record.state is not _State.QUEUED
                or record.unknown
                or record.managed
                or record.owner is None
                or record.start_attempted
                or time.monotonic_ns() >= record.deadline_ns
                or counts.active >= MAX_PROCESSES
                or (record.kind == "METADATA" and counts.metadata >= MAX_METADATA)
                or (record.kind == "AVATAR" and counts.avatar >= MAX_AVATAR)
                or any(
                    r.state is _State.ACTIVE and r.profile == record.profile
                    for r in self._records.values()
                )
            ):
                raise FrameError("BI1_BROKER_REGISTRY_START_REFUSED")
            record.managed = True  # no unmanaged fallback after any managed intent
            try:
                resources = BrokerReaderResources.__new__(BrokerReaderResources)
                record.resources = record.resources_snapshot = resources
                resources.__init__(
                    record,
                    record.owner,
                    binding=record.binding,
                    profile=record.profile,
                    kind=record.kind,
                    deadline_ns=record.deadline_ns,
                )
                record.resources_ready = True
                self._check()
                record.state = _State.ACTIVE
                record.start_attempted = True
                if time.monotonic_ns() >= record.deadline_ns:
                    raise FrameError("BI1_BROKER_REGISTRY_START_DEADLINE")
                resources.start()
                self._check()
                if time.monotonic_ns() >= record.deadline_ns:
                    resources.abort()
                    raise FrameError("BI1_BROKER_REGISTRY_START_DEADLINE")
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_START_UNCERTAIN") from None
        finally:
            self._lock.release()

    def _managed(self, ticket: BrokerTicket, *, normal: bool = False) -> _Record:
        record = self._record(ticket)
        if (
            record.state is not _State.ACTIVE
            or not record.managed
            or not record.resources_ready
            or type(record.resources) is not BrokerReaderResources
            or (normal and record.unknown)
        ):
            raise FrameError("BI1_BROKER_REGISTRY_RESOURCES_REFUSED")
        return record

    def stage_resource_input(self, ticket: BrokerTicket, packet: bytes) -> None:
        self._enter()
        try:
            record = self._managed(ticket, normal=True)
            try:
                record.resources.stage_input(packet)
                self._check()
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_INPUT_REFUSED") from None
        finally:
            self._lock.release()

    def relay_resource_go(self, ticket: BrokerTicket) -> None:
        """Qualified private service only, after original native+authenticated GO."""
        self._enter()
        try:
            record = self._managed(ticket, normal=True)
            try:
                record.resources.relay_go()
                self._check()
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_GO_REFUSED") from None
        finally:
            self._lock.release()

    def poll_resource_result(self, ticket: BrokerTicket) -> bool:
        self._enter()
        try:
            record = self._managed(ticket, normal=True)
            try:
                result = record.resources.poll_result()
                self._check()
                return result
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_RESULT_REFUSED") from None
        finally:
            self._lock.release()

    def take_resource_candidate(self, ticket: BrokerTicket) -> bytes:
        self._enter()
        try:
            record = self._managed(ticket, normal=True)
            try:
                result = record.resources.take_candidate()
                self._check()
                return result
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_CANDIDATE_REFUSED") from None
        finally:
            self._lock.release()

    def abort_resources(self, ticket: BrokerTicket) -> None:
        self._enter()
        try:
            record = self._managed(ticket)
            record.resources.abort()
            self._check()
        finally:
            self._lock.release()

    def poll_resource_cleanup(self, ticket: BrokerTicket) -> bool:
        self._enter()
        try:
            record = self._managed(ticket)
            result = record.resources.poll_cleanup()
            self._check()
            return result  # LOCAL only; remains ACTIVE/PENDING, no slot release
        finally:
            self._lock.release()

    def resource_local_observation(self, ticket: BrokerTicket):
        self._enter()
        try:
            record = self._managed(ticket)
            observation = record.resources.local_observation(record)
            self._check()
            return observation
        finally:
            self._lock.release()

    def poll_wait(self, ticket: BrokerTicket) -> bool:
        self._enter()
        try:
            record = self._record(ticket)
            if record.state is not _State.ACTIVE or record.owner is None or record.managed:
                raise FrameError("BI1_BROKER_REGISTRY_WAIT_REFUSED")
            try:
                if not record.owner.owns(record):
                    self._poison()
                result = record.owner.poll_wait()
                self._check()
                return result  # child fact only; reservation remains ACTIVE
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_WAIT_UNCERTAIN") from None
        finally:
            self._lock.release()

    def terminate_once(self, ticket: BrokerTicket) -> None:
        self._enter()
        try:
            record = self._record(ticket)
            if record.state is not _State.ACTIVE or record.owner is None or record.managed:
                raise FrameError("BI1_BROKER_REGISTRY_SIGNAL_REFUSED")
            try:
                if not record.owner.owns(record):
                    self._poison()
                record.owner.terminate_once()
                self._check()
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_SIGNAL_UNCERTAIN") from None
        finally:
            self._lock.release()

    def _sealed(self, record: _Record) -> None:
        try:
            if (
                record.unknown
                or record.start_attempted
                or type(record.owner) is not BrokerChildOwner
                or not record.owner.owns(record)
                or record.owner.never_launched_closed is not True
            ):
                self._poison()
        except BaseException:
            self._poison()

    def seal_unlaunched(self, ticket: BrokerTicket) -> None:
        self._enter()
        try:
            record = self._record(ticket)
            if (
                record.state is not _State.QUEUED
                or record.unknown
                or record.owner is None
                or record.managed
            ):
                raise FrameError("BI1_BROKER_REGISTRY_SEAL_REFUSED")
            try:
                record.owner.seal_unlaunched()
                self._sealed(record)
                self._check()
                record.state = _State.TERMINAL_UNLAUNCHED
            except BaseException:
                record.unknown = True
                raise FrameError("BI1_BROKER_REGISTRY_SEAL_UNCERTAIN") from None
        finally:
            self._lock.release()

    def status(self, binding: BrokerBinding) -> RegistryStatus:
        self._enter()
        try:
            self._scope_binding(binding)
            ticket = self._operations.get(binding.operation)
            if ticket is None:
                return RegistryStatus.UNKNOWN
            record = self._record(ticket)
            if record.state is _State.TERMINAL_UNLAUNCHED:
                self._sealed(record)
                self._check()
                return RegistryStatus.CLOSED
            return RegistryStatus.PENDING
        finally:
            self._lock.release()

    def acknowledge(self, binding: BrokerBinding) -> bool:
        """Outer qualified original/STATUS grammar required. No token-only authority."""
        self._enter()
        try:
            self._scope_binding(binding)
            ticket = self._operations.get(binding.operation)
            if ticket is None:
                return False  # no history/closure claim, no work or slot released
            record = self._record(ticket)
            if record.state is not _State.TERMINAL_UNLAUNCHED:
                raise FrameError("BI1_BROKER_REGISTRY_ACK_REFUSED")
            self._sealed(record)
            self._check()
            del self._operations[record.binding.operation]
            del self._records[ticket]
            return True
        finally:
            self._lock.release()
