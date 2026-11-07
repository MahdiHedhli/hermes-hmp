"""Bounded committed-frame DATA parser; no authentication or native IO grant.

Native integration must retain its actual authenticated record and prove the
allowed transition. Caller-created commitments and returned facts are DATA only.
RESULT bytes are hashed/discarded. Only bounded TERMINAL metadata is retained.
"""
from __future__ import annotations

import hashlib
import os
import threading
from typing import NamedTuple

from .presentation_broker_codec import (
    HEADER_LIMIT,
    TERMINAL_LIMIT,
    BrokerBinding,
    BrokerHeader,
    _binding,
    header_size,
)
from .presentation_credential_codec import JSON_LIMIT
from .presentation_credential_phase import ConsistentCommitment, check_committed_header
from .presentation_credential_stream import (
    _HASH_TYPE,
    CHUNK_LIMIT,
    CommittedFrameDigest,
    ConsistentFrameDigest,
)
from .presentation_jobs import OUTPUT_LIMIT, FrameError

_HASH_HEX = _HASH_TYPE.hexdigest
_HASH_UPDATE = _HASH_TYPE.update
_SHA256 = hashlib.sha256


def _require(value):
    if value is not True:
        raise FrameError("BI1_COMMITTED_FRAME_DISCARD_REFUSED")


class DiscardedFrame(NamedTuple):
    digest: ConsistentFrameDigest
    phase: str
    sequence: int
    terminal: bytes | None

    def __repr__(self):
        return "<DiscardedFrame consistency-DATA no-terminal-acceptance-or-release>"


class CommittedFrameDiscard:
    def __init__(self, commitment, *, binding, phase, sequence):
        _require(type(self) is CommittedFrameDiscard and "_initialized" not in vars(self))
        self._initialized = self._failed = self._finished = self._inflight = False
        self._finish_attempted = self._finish_returned = False
        self._buffer = self._buffer_origin = bytearray()
        self._buffer_allocation = (self, self._buffer_origin)
        self._terminal = self._terminal_origin = bytearray()
        self._terminal_allocation = (self, self._terminal_origin)
        self._target = self._target_origin = 8
        self._header = self._header_origin = self._header_allocation = None
        self._stream = self._stream_origin = self._stream_allocation = self._hash_allocation = None
        self._digest = self._digest_allocation = self._fact = self._fact_allocation = None
        self._context = self._context_origin = (os.getpid(), threading.get_ident())
        try:
            _require(type(commitment) is ConsistentCommitment
                     and type(commitment.canonical_json) is bytes
                     and 1 <= len(commitment.canonical_json) <= JSON_LIMIT
                     and type(commitment.frame_sha256) is str
                     and type(commitment.frame_length) is int
                     and type(phase) is str and phase in ("RESULT", "TERMINAL")
                     and type(sequence) is int and sequence in (0, 1, 2)
                     and (phase != "RESULT" or sequence == 1))
            _binding(binding)
            self._claim = self._claim_origin = commitment
            self._claim_allocation = (self, commitment)
            self._claim_values = (commitment.canonical_json,
                                  commitment.frame_sha256, commitment.frame_length)
            self._binding = self._binding_origin = binding
            self._binding_allocation = (self, binding)
            self._binding_values = (binding.iid, binding.listener, binding.broker,
                                    binding.channel, binding.operation)
            self._expected = self._expected_origin = (phase, sequence)
            self._limit = OUTPUT_LIMIT if phase == "RESULT" else TERMINAL_LIMIT
            _require(9 <= commitment.frame_length <= 8 + HEADER_LIMIT + self._limit)
            self._initialized = True
            CommittedFrameDiscard._owned(self)
        except BaseException:
            CommittedFrameDiscard._fail(self)
            raise FrameError("BI1_COMMITTED_FRAME_DISCARD_REFUSED") from None

    def __repr__(self):
        return "<CommittedFrameDiscard bounded consistency-DATA payload-redacted>"

    def _owned(self):
        _require(type(self) is CommittedFrameDiscard)
        context = (os.getpid(), threading.get_ident())
        _require(self._initialized is True and self._failed is False and self._inflight is False
                 and all(type(v) is bool for v in (
                     self._finished, self._finish_attempted, self._finish_returned))
                 and type(self._context) is tuple and self._context is self._context_origin
                 and len(self._context) == 2 and all(type(v) is int for v in self._context)
                 and self._context == context)
        for actual, origin, allocation in (
            (self._buffer, self._buffer_origin, self._buffer_allocation),
            (self._terminal, self._terminal_origin, self._terminal_allocation),
        ):
            _require(type(actual) is bytearray and actual is origin
                     and type(allocation) is tuple and len(allocation) == 2
                     and allocation[0] is self and allocation[1] is actual)
        claim = self._claim_origin
        _require(type(claim) is ConsistentCommitment and self._claim is claim
                 and type(self._claim_allocation) is tuple and len(self._claim_allocation) == 2
                 and self._claim_allocation[0] is self and self._claim_allocation[1] is claim
                 and type(self._claim_values) is tuple and len(self._claim_values) == 3
                 and type(claim.canonical_json) is bytes and type(claim.frame_sha256) is str
                 and type(claim.frame_length) is int
                 and claim.canonical_json is self._claim_values[0]
                 and claim.frame_sha256 is self._claim_values[1]
                 and claim.frame_length is self._claim_values[2])
        binding = self._binding_origin
        _require(type(binding) is BrokerBinding and self._binding is binding
                 and type(self._binding_allocation) is tuple and len(self._binding_allocation) == 2
                 and self._binding_allocation[0] is self
                 and self._binding_allocation[1] is binding)
        _binding(binding)
        _require(type(self._binding_values) is tuple and len(self._binding_values) == 5
                 and all(type(v) is str for v in self._binding_values)
                 and (binding.iid, binding.listener, binding.broker, binding.channel,
                      binding.operation) == self._binding_values
                 and type(self._expected) is tuple and self._expected is self._expected_origin
                 and len(self._expected) == 2 and type(self._expected[0]) is str
                 and self._expected[0] in ("RESULT", "TERMINAL")
                 and type(self._expected[1]) is int and self._expected[1] in (0, 1, 2)
                 and (self._expected[0] != "RESULT" or self._expected[1] == 1)
                 and type(self._limit) is int
                 and self._limit == (OUTPUT_LIMIT if self._expected[0] == "RESULT"
                                     else TERMINAL_LIMIT)
                 and type(self._target) is int and self._target is self._target_origin
                 and 8 <= self._target <= 8 + HEADER_LIMIT
                 and len(self._buffer) <= self._target)
        header, stream = self._header_origin, self._stream_origin
        if header is None:
            _require(self._header is None and self._header_allocation is None
                     and stream is None and self._stream is None
                     and self._stream_allocation is None and self._hash_allocation is None
                     and not self._terminal and self._finish_attempted is False)
            if len(self._buffer) < 8:
                _require(self._target == 8)
            else:
                _require(self._target == 8 + header_size(bytes(self._buffer[:8])))
            return
        _require(type(header) is BrokerHeader and self._header is header
                 and type(self._header_allocation) is tuple and len(self._header_allocation) == 3
                 and self._header_allocation[0] is self and self._header_allocation[1] is header
                 and type(self._header_allocation[2]) is bytes
                 and bytes(self._buffer) == self._header_allocation[2]
                 and len(self._buffer) == self._target
                 and type(header.kind) is str and header.kind == self._expected[0]
                 and type(header.sequence) is int and header.sequence == self._expected[1]
                 and type(header.version) is int and header.version == 2
                 and type(header.body_length) is int
                 and (4 if header.kind == "RESULT" else 1) <= header.body_length <= self._limit
                 and type(stream) is CommittedFrameDigest and self._stream is stream
                 and type(self._stream_allocation) is tuple and len(self._stream_allocation) == 3
                 and self._stream_allocation[0] is self and self._stream_allocation[1] is stream
                 and self._stream_allocation[2] is header
                 and type(self._hash_allocation) is tuple and len(self._hash_allocation) == 3
                 and self._hash_allocation[0] is self and self._hash_allocation[1] is stream
                 and type(self._hash_allocation[2]) is _HASH_TYPE
                 and stream._hasher is self._hash_allocation[2]
                 and stream._hasher_origin is self._hash_allocation[2]
                 and stream._commitment is claim and stream._commitment_origin is claim
                 and stream._binding is binding and stream._binding_origin is binding
                 and type(stream._received) is int and stream._received is stream._received_snapshot
                 and 0 <= stream._received <= header.body_length
                 and type(stream._body_length) is int and stream._body_length == header.body_length
                 and type(stream._header_length) is int
                 and stream._header_length == len(self._buffer)
                 and stream._initialized is True and stream._failed is False)
        _require((header.kind == "RESULT" and not self._terminal)
                 or (header.kind == "TERMINAL"
                     and len(self._terminal) == stream._received <= TERMINAL_LIMIT))

    def _live(self):
        CommittedFrameDiscard._owned(self)
        _require(self._finished is False)
        stream = self._stream_origin
        if stream is not None:
            CommittedFrameDigest._guard(stream)
            CommittedFrameDiscard._owned(self)

    def _needed(self):
        CommittedFrameDiscard._live(self)
        if self._stream_origin is None:
            return self._target - len(self._buffer)
        return min(CHUNK_LIMIT, self._stream_origin._body_length - self._stream_origin._received)

    @property
    def needed(self):
        _require(type(self) is CommittedFrameDiscard and self._finish_attempted is False)
        try:
            return CommittedFrameDiscard._needed(self)
        except BaseException:
            CommittedFrameDiscard._fail(self)
        raise FrameError("BI1_COMMITTED_FRAME_DISCARD_REFUSED") from None

    def feed(self, chunk):
        _require(type(self) is CommittedFrameDiscard and self._finish_attempted is False)
        failed = False
        raw = None
        try:
            count = CommittedFrameDiscard._needed(self)
            _require(type(chunk) is bytes and 0 < len(chunk) <= count)
            self._inflight = True
            if self._stream_origin is None:
                self._buffer_origin.extend(chunk)
                if len(self._buffer_origin) == 8:
                    self._target = self._target_origin = 8 + header_size(bytes(self._buffer_origin))
                if len(self._buffer_origin) == self._target and self._target > 8:
                    raw = bytes(self._buffer_origin)
                    header = check_committed_header(self._claim_origin, raw,
                                                     binding=self._binding_origin)
                    _require(type(header) is BrokerHeader and type(header.kind) is str
                             and header.kind == self._expected[0]
                             and type(header.sequence) is int
                             and header.sequence == self._expected[1]
                             and type(header.body_length) is int
                             and (4 if header.kind == "RESULT" else 1)
                             <= header.body_length <= self._limit)
                    self._header = self._header_origin = header
                    self._header_allocation = (self, header, raw)
                    stream = CommittedFrameDigest.__new__(CommittedFrameDigest)
                    self._stream = self._stream_origin = stream
                    self._stream_allocation = (self, stream, header)
                    CommittedFrameDigest.__init__(stream, self._claim_origin, raw,
                                                  binding=self._binding_origin)
                    self._hash_allocation = (self, stream, stream._hasher_origin)
            else:
                if self._expected[0] == "TERMINAL":
                    self._terminal_origin.extend(chunk)
                CommittedFrameDigest.feed(self._stream_origin, chunk)
            self._inflight = False
            CommittedFrameDiscard._live(self)
            return
        except BaseException:
            failed = True
            CommittedFrameDiscard._fail(self)
        finally:
            chunk = raw = None
        if failed:
            raise FrameError("BI1_COMMITTED_FRAME_DISCARD_REFUSED") from None

    def finish(self):
        _require(type(self) is CommittedFrameDiscard and self._finish_attempted is False)
        self._finish_attempted = True
        failed = False
        terminal = raw = check = None
        try:
            _require(CommittedFrameDiscard._needed(self) == 0)
            stream = self._stream_origin
            raw = self._header_allocation[2]
            hasher = self._hash_allocation[2]
            terminal = (bytes(self._terminal_origin)
                        if self._expected[0] == "TERMINAL" else None)
            result = CommittedFrameDigest.finish(stream)
            self._digest = result
            self._digest_allocation = (self, result)
            self._finish_returned = True
            CommittedFrameDiscard._owned(self)
            _require(type(result) is ConsistentFrameDigest
                     and type(result.frame_sha256) is str and type(result.frame_length) is int
                     and result.frame_sha256 == self._claim_values[1]
                     and result.frame_length == self._claim_values[2]
                     and stream is self._stream_origin and stream._finished is True
                     and stream._received == stream._body_length)
            values = (result.frame_sha256, result.frame_length)
            terminal_hash = None
            if terminal is not None:
                check = _SHA256(raw)
                _HASH_UPDATE(check, terminal)
                terminal_hash = _HASH_HEX(check)
            current = _HASH_HEX(hasher)
            CommittedFrameDiscard._owned(self)
            _require(type(current) is str and current == values[0]
                     and type(result.frame_sha256) is str and result.frame_sha256 is values[0]
                     and type(result.frame_length) is int and result.frame_length is values[1]
                     and self._digest is result and self._hash_allocation[2] is hasher
                     and type(self._digest_allocation) is tuple
                     and len(self._digest_allocation) == 2
                     and self._digest_allocation[0] is self
                     and self._digest_allocation[1] is result
                     and self._header_allocation[2] is raw
                     and (terminal is None or (type(terminal_hash) is str
                          and terminal_hash == values[0]
                          and bytes(self._terminal_origin) == terminal)))
            fact = DiscardedFrame(result, self._expected[0], self._expected[1], terminal)
            self._fact = fact
            self._fact_allocation = (self, fact)
            self._finished = True
            # Private terminal bytes transfer only to the bounded consistency fact.
            self._terminal_origin.clear()
            return fact
        except BaseException:
            failed = True
            CommittedFrameDiscard._fail(self)
        finally:
            terminal = raw = check = None
        if failed:
            raise FrameError("BI1_COMMITTED_FRAME_DISCARD_REFUSED") from None

    def _fail(self):
        self._failed = True
        self._inflight = False
        for cell in (self._buffer_allocation, self._terminal_allocation):
            if (type(cell) is tuple and len(cell) == 2 and cell[0] is self
                    and type(cell[1]) is bytearray):
                cell[1][:] = b"\x00" * len(cell[1])
                cell[1].clear()
