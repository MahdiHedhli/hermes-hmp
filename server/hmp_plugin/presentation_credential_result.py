"""Original immutable native RESULT signing; no transfer/terminal/publication fact."""

from __future__ import annotations

import asyncio
import hashlib
from contextlib import suppress
from typing import NamedTuple

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_codec import BrokerHeader, encode_header
from .presentation_broker_registry import BrokerRegistry, _Record
from .presentation_broker_resources import BrokerReaderResources
from .presentation_cancel_budget import CancellationBudget
from .presentation_control_binding import PreparedControlBinding
from .presentation_credential_codec import encode_record, signing_bytes
from .presentation_credential_control import (
    CredentialCancelAdoption,
    CredentialControlCursor,
    CredentialGoPhase,
)
from .presentation_credential_files import RoleKeySelection
from .presentation_credential_go_relay import CredentialGoRelay
from .presentation_credential_phase import _EXPECTED, check_commitment, check_committed_header
from .presentation_jobs import OUTPUT_LIMIT, FrameError
from .presentation_remote_cleanup import _TASK

_RESULT_MINT = object()


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_RESULT_REFUSED")


class _ResultScope(NamedTuple):
    control: object
    relay: object
    relay_fact: object
    refs: tuple
    resources: object
    cursor: object
    expected: tuple
    pins: tuple

    def __repr__(self):
        return "<CredentialResultScope original-service redacted>"


class _FrozenResult(NamedTuple):
    mint: object
    owner: object
    scope: _ResultScope
    payload: bytes
    header: bytes
    payload_sha: str
    frame_sha: str
    raw: bytes

    def __repr__(self):
        return "<FrozenCredentialResult signed-data-only payload-redacted>"


class CredentialResultProducer:
    @classmethod
    def retain(cls, control):
        _require(cls is CredentialResultProducer and type(control) is BrokerCancellationOwner)
        adoption = control._signed_cancel_snapshot
        _require(type(adoption) is CredentialCancelAdoption
                 and type(adoption._refs_snapshot) is tuple and len(adoption._refs_snapshot) == 19)
        refs = CredentialCancelAdoption._consume_scope(adoption, adoption._refs_snapshot[0])
        relay = control._credential_go_relay_snapshot
        _require(type(relay) is CredentialGoRelay and control._credential_go_relay is relay
                 and control._credential_result is None
                 and control._credential_result_snapshot is None
                 and type(refs[4]) is _Record
                 and type(refs[4].resources_snapshot) is BrokerReaderResources)
        fact = CredentialGoRelay.completed_local(relay)
        cursor = control._signed_cursor_snapshot
        _require(type(cursor) is CredentialControlCursor
                 and type(cursor._expected_snapshot) is tuple
                 and len(cursor._expected_snapshot) == len(_EXPECTED) - 2
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                         for row in cursor._expected_snapshot)
                 and type(refs[11]) is RoleKeySelection
                 and type(refs[11].own_public) is bytes and len(refs[11].own_public) == 32
                 and type(refs[11].peer_public) is bytes and len(refs[11].peer_public) == 32)
        expected = dict(cursor._expected_snapshot)
        expected.update(phase="RESULT", role="broker", direction="b2g", sequence=1)
        owner = cls.__new__(cls)
        owner._scope = owner._scope_snapshot = _ResultScope(
            control, relay, fact, refs, refs[4].resources_snapshot, cursor,
            tuple(sorted(expected.items())), (refs[11].own_public, refs[11].peer_public))
        owner._attempted = owner._failed = owner._retired = owner._complete = False
        owner._payload = owner._payload_snapshot = None
        owner._frozen = owner._frozen_snapshot = None
        control._credential_result = control._credential_result_snapshot = owner
        try:
            CredentialResultProducer._current(owner)
            return owner
        except BaseException:
            owner._failed = owner._retired = True
            raise

    def __repr__(self):
        return "<CredentialResultProducer no-transfer payload-redacted>"

    def _local(self):
        _require(type(self) is CredentialResultProducer and type(self._scope) is _ResultScope
                 and self._scope is self._scope_snapshot)
        s = self._scope_snapshot
        _require(type(s.control) is BrokerCancellationOwner and type(s.relay) is CredentialGoRelay
                 and type(s.refs) is tuple and len(s.refs) == 19
                 and type(s.resources) is BrokerReaderResources
                 and s.control._credential_result is self
                 and s.control._credential_result_snapshot is self
                 and s.control._credential_go_relay_snapshot is s.relay
                 and CredentialGoRelay.completed_local(s.relay) is s.relay_fact
                 and s.relay_fact.scope.refs is s.refs
                 and s.relay_fact.scope.control is s.control
                 and s.relay_fact.scope.resources is s.resources
                 and type(s.relay_fact.scope.phase) is CredentialGoPhase
                 and type(s.relay_fact.scope.adoption) is CredentialCancelAdoption
                 and s.control._signed_go is s.relay_fact.scope.phase
                 and s.control._signed_go_snapshot is s.relay_fact.scope.phase
                 and s.control._signed_cancel is s.relay_fact.scope.adoption
                 and s.control._signed_cancel_snapshot is s.relay_fact.scope.adoption
                 and s.control._credential_binding is s.control._credential_binding_snapshot
                 and s.control._credential_binding_snapshot
                     is s.relay_fact.scope.adoption._binding_snapshot
                 and type(s.refs[4]) is _Record
                 and s.refs[4].resources is s.resources
                 and s.refs[4].resources_snapshot is s.resources
                 and s.resources._operation is s.refs[4]
                 and s.resources._operation_snapshot is s.refs[4]
                 and s.resources._cleanup_budget_snapshot is s.refs[17]
                 and type(s.expected) is tuple and len(s.expected) == len(_EXPECTED)
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (
                             int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in s.expected)
                 and {row[0] for row in s.expected} == _EXPECTED
                 and type(s.pins) is tuple and len(s.pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in s.pins)
                 and type(s.refs[11]) is RoleKeySelection
                 and type(s.refs[11].own_public) is bytes and len(s.refs[11].own_public) == 32
                 and type(s.refs[11].peer_public) is bytes and len(s.refs[11].peer_public) == 32
                 and s.pins == (s.refs[11].own_public, s.refs[11].peer_public)
                 and type(s.cursor) is CredentialControlCursor
                 and s.control._signed_cursor is s.cursor
                 and s.control._signed_cursor_snapshot is s.cursor
                 and s.cursor is s.relay_fact.scope.adoption._cursor_snapshot
                 and s.cursor._expected is s.cursor._expected_snapshot
                 and type(s.cursor._expected_snapshot) is tuple
                 and len(s.cursor._expected_snapshot) == len(_EXPECTED) - 2
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                         for row in s.cursor._expected_snapshot)
                 and all(type(v) is bool for v in (
                     self._attempted, self._failed, self._retired, self._complete))
                 and self._failed is False and self._retired is False
                 and self._payload is self._payload_snapshot
                 and (self._payload is None or (type(self._payload) is bytes
                                               and 4 <= len(self._payload) <= OUTPUT_LIMIT))
                 and self._frozen is self._frozen_snapshot)
        expected = dict(s.cursor._expected_snapshot)
        expected.update(phase="RESULT", role="broker", direction="b2g", sequence=1)
        _require(s.expected == tuple(sorted(expected.items())))
        if self._complete:
            f = self._frozen_snapshot
            _require(type(f) is _FrozenResult and f.mint is _RESULT_MINT
                     and f.owner is self and f.scope is s and f.payload is self._payload_snapshot
                     and type(f.raw) is bytes and 0 < len(f.raw) <= 2048
                     and type(f.header) is bytes and 8 < len(f.header) <= 1032
                     and type(f.payload_sha) is str and len(f.payload_sha) == 64
                     and type(f.frame_sha) is str and len(f.frame_sha) == 64
                     and f.header == encode_header(BrokerHeader(
                         s.refs[4].binding, "RESULT", 1, len(f.payload), 2)))
        else:
            _require(self._frozen is None)
        return s

    def _current(self):
        s = CredentialResultProducer._local(self)
        _require(PreparedControlBinding._creator_local(
            s.control._credential_binding_snapshot) is s.refs)
        phase = s.control._signed_go_snapshot
        _require(type(phase) is CredentialGoPhase
                 and phase.creator_current() is s.relay_fact.scope.receipt)
        BrokerReaderResources._check(s.resources)
        _require(PreparedControlBinding._creator_local(
            s.control._credential_binding_snapshot) is s.refs)
        _require(CredentialResultProducer._local(self) is s
                 and asyncio.current_task() is s.refs[15] and _TASK.cancelling(s.refs[15]) == 0
                 and s.control._retired is False and s.control._failed is False
                 and s.control._io_unknown is False
                 and type(s.resources._phase) is str and s.resources._phase == "LOCAL_DRAINED"
                 and s.resources._normal_complete is True
                 and s.resources._invalidated is False and s.resources._poisoned is False)
        original, cause, end, failed = CancellationBudget.inspect(s.refs[17])
        _require(type(original) is int and original == s.refs[4].deadline_ns
                 and cause is None and end is None and failed is False)
        return s

    def retire_from_control(self, control):
        """Pure owned-memory withdrawal before native cleanup sampling; no I/O."""
        if (type(self) is not CredentialResultProducer
                or type(self._scope_snapshot) is not _ResultScope
                or self._scope is not self._scope_snapshot
                or self._scope_snapshot.control is not control
                or type(control) is not BrokerCancellationOwner or control._retired is not True
                or control._credential_result is not self
                or control._credential_result_snapshot is not self):
            return False
        self._retired = True
        self._payload = self._payload_snapshot = None
        self._frozen = self._frozen_snapshot = None
        return True

    def prepare(self):
        held = part = header = raw = digest = frozen = None
        failed = cancelled = False
        s = CredentialResultProducer._local(self)
        _require(asyncio.current_task() is s.refs[15] and _TASK.cancelling(s.refs[15]) == 0
                 and self._attempted is False)
        self._attempted = True  # before native candidate acquisition, never retry
        try:
            _require(CredentialResultProducer._current(self) is s)
            held = BrokerRegistry.take_resource_candidate(s.refs[2], s.refs[3])
            # Retain actual native return before any postcheck.
            self._payload = self._payload_snapshot = held
            _require(CredentialResultProducer._current(self) is s
                     and type(held) is bytes and self._payload is held)
            header = encode_header(BrokerHeader(s.refs[4].binding, "RESULT", 1, len(held), 2))
            digest = hashlib.sha256(header)
            for offset in range(0, len(held), 65536):
                _require(CredentialResultProducer._current(self) is s and self._payload is held)
                part = memoryview(held)[offset:offset + 65536]
                digest.update(part)
                part = None
            frame_sha = digest.hexdigest()
            payload_sha = hashlib.sha256(held).hexdigest()
            statement = dict(s.expected)
            statement.update(v=1, family="phase", alg="Ed25519",
                key_id=hashlib.sha256(s.pins[0]).hexdigest(),
                peer_key_id=hashlib.sha256(s.pins[1]).hexdigest(),
                frame_sha256=frame_sha, frame_length=len(header) + len(held))
            data = signing_bytes(statement)
            _require(CredentialResultProducer._current(self) is s and self._payload is held)
            raw = encode_record(statement, s.refs[12].sign(data))
            _require(CredentialResultProducer._current(self) is s and self._payload is held)
            checked = check_commitment(raw, sender_public=s.pins[0], receiver_public=s.pins[1],
                                       expected=dict(s.expected))
            check_committed_header(checked, header, binding=s.refs[4].binding)
            _require(CredentialResultProducer._current(self) is s and self._payload is held)
            frozen = _FrozenResult(_RESULT_MINT, self, s, held, header, payload_sha, frame_sha, raw)
            self._frozen = self._frozen_snapshot = frozen
            self._complete = True
        except asyncio.CancelledError:
            failed = cancelled = True
        except BaseException:
            failed = True
        finally:
            if failed:
                self._failed = self._retired = True
                self._payload = self._payload_snapshot = None
                self._frozen = self._frozen_snapshot = None
                # Preserve failed owner/refusal even if original cause sampling is unknown.
                with suppress(BaseException):
                    BrokerCancellationOwner._local_cause(s.control)
            held = part = header = raw = digest = frozen = None
        if cancelled:
            raise asyncio.CancelledError from None
        if failed:
            raise FrameError("BI1_CREDENTIAL_RESULT_PREPARATION_REFUSED") from None
        return self._frozen_snapshot.raw  # signed data only, not an actual transfer
