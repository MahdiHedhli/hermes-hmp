"""Bounded original-frame digest data, never authorization or custody proof.

The original authenticated receiver must retain its actual checked commitment,
read its own bounded header/body cursor and enforce native/lifecycle authority.
This helper performs no IO and cannot attest signature verification or transfer.
"""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass

from .presentation_broker_codec import HEADER_LIMIT, BrokerBinding, _binding, header_size
from .presentation_credential_codec import RECORD_LIMIT, payload_size
from .presentation_credential_phase import (
    _EXPECTED,
    ConsistentCommitment,
    check_broker_cleanup_commitment,
    check_commitment,
    check_committed_header,
)
from .presentation_jobs import OUTPUT_LIMIT, FrameError

CHUNK_LIMIT = 65_536
_HASH_TYPE = type(hashlib.sha256())


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_STREAM_REFUSED")


@dataclass(frozen=True)
class ConsistentFrameDigest:
    """Data-only full-frame hash; not a signature, write or native release fact."""

    frame_sha256: str
    frame_length: int


class CommittedFrameDigest:
    """One thread-confined digest of exact prefix/header and bounded body chunks."""

    def __init__(self, commitment: ConsistentCommitment, header: bytes, *, binding: BrokerBinding):
        if type(self) is not CommittedFrameDigest or "_initialized" in vars(self):
            raise FrameError("BI1_CREDENTIAL_STREAM_REFUSED")
        self._initialized = False
        self._failed = self._finished = False
        self._context = (os.getpid(), threading.get_ident())
        try:
            _require(type(commitment) is ConsistentCommitment and type(header) is bytes)
            _binding(binding)
            decoded = check_committed_header(commitment, header, binding=binding)
            self._commitment = self._commitment_origin = commitment
            self._commitment_values = (
                commitment.canonical_json,
                commitment.frame_sha256,
                commitment.frame_length,
            )
            self._binding = self._binding_origin = binding
            self._binding_values = (
                binding.iid,
                binding.listener,
                binding.broker,
                binding.channel,
                binding.operation,
            )
            self._body_length = decoded.body_length
            self._header_length = len(header)
            self._received = self._received_snapshot = 0
            self._hasher = self._hasher_origin = hashlib.sha256(header)
            self._initialized = True
            self._guard()
        except BaseException:
            self._failed = True
            raise

    def __repr__(self):
        return "<CommittedFrameDigest payload-redacted>"

    def _guard(self):
        _require(
            type(self) is CommittedFrameDigest
            and self._initialized is True
            and self._failed is False
            and self._finished is False
        )
        _require(
            type(self._context) is tuple
            and len(self._context) == 2
            and all(type(item) is int for item in self._context)
        )
        _require(self._context == (os.getpid(), threading.get_ident()))
        _require(
            self._commitment is self._commitment_origin
            and type(self._commitment) is ConsistentCommitment
        )
        claim = self._commitment
        _require(
            type(claim.canonical_json) is bytes
            and type(claim.frame_sha256) is str
            and type(claim.frame_length) is int
            and type(self._commitment_values) is tuple
            and len(self._commitment_values) == 3
            and type(self._commitment_values[0]) is bytes
            and type(self._commitment_values[1]) is str
            and type(self._commitment_values[2]) is int
        )
        _require(
            (claim.canonical_json, claim.frame_sha256, claim.frame_length)
            == self._commitment_values
        )
        _require(type(self._binding) is BrokerBinding and self._binding is self._binding_origin)
        _binding(self._binding)
        _require(
            type(self._binding_values) is tuple
            and len(self._binding_values) == 5
            and all(type(item) is str for item in self._binding_values)
        )
        current = (
            self._binding.iid,
            self._binding.listener,
            self._binding.broker,
            self._binding.channel,
            self._binding.operation,
        )
        _require(current == self._binding_values)
        _require(
            type(self._body_length) is int
            and type(self._header_length) is int
            and self._body_length >= 0
            and 8 <= self._header_length <= 1032
            and self._body_length + self._header_length == claim.frame_length
            and type(self._received) is int
            and self._received is self._received_snapshot
            and 0 <= self._received <= self._body_length
            and type(self._hasher) is _HASH_TYPE
            and self._hasher is self._hasher_origin
        )

    @property
    def remaining(self) -> int:
        try:
            self._guard()
            return self._body_length - self._received
        except BaseException:
            self._failed = True
            raise

    def feed(self, chunk: bytes) -> None:
        try:
            self._guard()
            _require(
                type(chunk) is bytes
                and 0 < len(chunk) <= CHUNK_LIMIT
                and len(chunk) <= self._body_length - self._received
            )
            self._hasher.update(chunk)
            self._guard()  # a failed native hash boundary cannot publish progress
            self._received = self._received_snapshot = self._received + len(chunk)
        except BaseException:
            self._failed = True
            raise

    def finish(self) -> ConsistentFrameDigest:
        try:
            self._guard()
            _require(self._received == self._body_length)
            actual = self._hasher.hexdigest()
            self._guard()
            _require(type(actual) is str and actual == self._commitment.frame_sha256)
            self._finished = True
            return ConsistentFrameDigest(actual, self._header_length + self._received)
        except BaseException:
            self._failed = True
            raise


class SignedResultDiscard:
    """Bounded framing/digest DATA continuation, never a socket or cleanup permit.

    `prefix` is the already-consumed bounded HBA1/outer header, never image bytes.
    Optional `stream` is the SAME original partial-body digest, not a copied hash.
    The caller must separately prove original cursor/actor/budget/IO authority.
    """

    def __init__(self, prefix: bytes, *, sender_public: bytes, receiver_public: bytes,
                 expected: dict, binding: BrokerBinding, stream=None):
        _require(type(self) is SignedResultDiscard and "_initialized" not in vars(self))
        self._initialized = self._failed = self._finished = False
        self._context = (os.getpid(), threading.get_ident())
        self._buffer = self._buffer_origin = bytearray()
        self._stage = self._stage_origin = "auth_prefix"
        self._target = self._target_origin = 8
        self._auth_end = self._auth_end_origin = None
        self._stream = self._stream_origin = None
        self._resume = stream
        self._binding = self._binding_origin = binding
        failed = False
        try:
            _require(type(prefix) is bytes and len(prefix) <= RECORD_LIMIT + 8 + HEADER_LIMIT
                     and type(expected) is dict and all(type(k) is str for k in expected)
                     and expected.keys() == _EXPECTED
                     and all(type(v) is (int if k in ("sequence", "work_end_ns") else str)
                             for k, v in expected.items())
                     and expected["phase"] == "RESULT" and expected["role"] == "broker"
                     and expected["direction"] == "b2g" and expected["sequence"] == 1
                     and type(sender_public) is bytes and len(sender_public) == 32
                     and type(receiver_public) is bytes and len(receiver_public) == 32
                     and (stream is None or type(stream) is CommittedFrameDigest))
            _binding(binding)
            self._expected = self._expected_origin = tuple(sorted(expected.items()))
            self._pins = self._pins_origin = (sender_public, receiver_public)
            self._initialized = True
            offset = 0
            while offset < len(prefix):
                _require(self._stage != "body")  # never replay or retain consumed image bytes
                count = min(self.needed, len(prefix) - offset)
                self.feed(prefix[offset:offset + count])
                offset += count
            _require(stream is None or self._stage == "body")
        except BaseException:
            failed = self._failed = True
            self._buffer_origin.clear()
        finally:
            prefix = stream = None
        if failed:
            raise FrameError("BI1_SIGNED_DISCARD_DATA_REFUSED") from None

    def __repr__(self):
        return "<SignedResultDiscard framing-and-digest-data no-IO-permission>"

    def _guard(self):
        _require(type(self) is SignedResultDiscard and self._initialized is True
                 and self._failed is False and self._finished is False
                 and type(self._context) is tuple and len(self._context) == 2
                 and all(type(v) is int for v in self._context)
                 and self._context == (os.getpid(), threading.get_ident())
                 and type(self._buffer) is bytearray and self._buffer is self._buffer_origin
                 and self._stage is self._stage_origin and type(self._stage) is str
                 and self._stage in ("auth_prefix", "auth", "header_prefix", "header", "body")
                 and type(self._target) is int and self._target is self._target_origin
                 and 8 <= self._target <= RECORD_LIMIT + 8 + HEADER_LIMIT
                 and len(self._buffer) <= self._target
                 and self._auth_end is self._auth_end_origin
                 and self._binding is self._binding_origin and type(self._binding) is BrokerBinding
                 and type(self._expected) is tuple and self._expected is self._expected_origin
                 and len(self._expected) == len(_EXPECTED)
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in self._expected)
                 and {row[0] for row in self._expected} == _EXPECTED
                 and type(self._pins) is tuple and self._pins is self._pins_origin
                 and len(self._pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in self._pins)
                 and self._stream is self._stream_origin)
        _binding(self._binding)
        if self._stage == "auth_prefix":
            _require(self._auth_end is None and self._target == 8)
        else:
            _require(type(self._auth_end) is int and 73 <= self._auth_end <= RECORD_LIMIT)
            if self._stage == "auth":
                _require(self._target == self._auth_end)
            elif self._stage == "header_prefix":
                _require(self._target == self._auth_end + 8
                         and len(self._buffer) >= self._auth_end)
            else:
                _require(self._auth_end + 9 <= self._target
                         <= self._auth_end + 8 + HEADER_LIMIT
                         and len(self._buffer) >= self._auth_end + 8)
        if self._stage == "body":
            _require(type(self._stream) is CommittedFrameDigest
                     and len(self._buffer) == self._target)
            CommittedFrameDigest._guard(self._stream)
        else:
            _require(self._stream is None)

    @property
    def needed(self) -> int:
        try:
            SignedResultDiscard._guard(self)
            if self._stage == "body":
                return min(CHUNK_LIMIT, CommittedFrameDigest.remaining.fget(self._stream))
            return self._target - len(self._buffer)
        except BaseException:
            self._failed = True
            self._buffer_origin.clear()
        raise FrameError("BI1_SIGNED_DISCARD_DATA_REFUSED") from None

    def feed(self, chunk: bytes) -> None:
        failed = False
        raw = header = None
        try:
            count = SignedResultDiscard.needed.fget(self)
            _require(type(chunk) is bytes and 0 < len(chunk) <= count)
            if self._stage == "body":
                CommittedFrameDigest.feed(self._stream, chunk)
                SignedResultDiscard._guard(self)
                return
            self._buffer_origin.extend(chunk)
            if len(self._buffer) != self._target:
                return
            if self._stage == "auth_prefix":
                self._auth_end = self._auth_end_origin = 8 + payload_size(bytes(self._buffer))
                self._target = self._target_origin = self._auth_end
                self._stage = self._stage_origin = "auth"
            elif self._stage == "auth":
                check_commitment(bytes(self._buffer), sender_public=self._pins[0],
                                 receiver_public=self._pins[1], expected=dict(self._expected))
                self._target = self._target_origin = self._auth_end + 8
                self._stage = self._stage_origin = "header_prefix"
            elif self._stage == "header_prefix":
                self._target = self._target_origin = self._target + header_size(
                    bytes(self._buffer[self._auth_end:]))
                self._stage = self._stage_origin = "header"
            else:
                raw = bytes(self._buffer[:self._auth_end])
                header = bytes(self._buffer[self._auth_end:])
                checked = check_commitment(raw, sender_public=self._pins[0],
                    receiver_public=self._pins[1], expected=dict(self._expected))
                decoded = check_committed_header(checked, header, binding=self._binding)
                _require(decoded.kind == "RESULT" and decoded.sequence == 1
                         and decoded.version == 2 and 4 <= decoded.body_length <= OUTPUT_LIMIT)
                if self._resume is None:
                    stream = CommittedFrameDigest(checked, header, binding=self._binding)
                else:
                    stream = self._resume
                    CommittedFrameDigest._guard(stream)
                    _require(stream._binding is self._binding
                             and stream._commitment == checked
                             and stream._header_length == len(header)
                             and stream._body_length == decoded.body_length)
                self._stream = self._stream_origin = stream
                self._stage = self._stage_origin = "body"
            SignedResultDiscard._guard(self)
        except BaseException:
            failed = self._failed = True
            self._buffer_origin.clear()
        finally:
            chunk = raw = header = None
        if failed:
            raise FrameError("BI1_SIGNED_DISCARD_DATA_REFUSED") from None

    def finish(self) -> ConsistentFrameDigest:
        try:
            _require(SignedResultDiscard.needed.fget(self) == 0 and self._stage == "body")
            fact = CommittedFrameDigest.finish(self._stream)
            self._finished = True
            self._buffer_origin.clear()
            return fact  # full-frame DATA only, not terminal/native settlement
        except BaseException:
            self._failed = True
            self._buffer_origin.clear()
        raise FrameError("BI1_SIGNED_DISCARD_DATA_REFUSED") from None


class SignedCleanupAuthPrefix:
    """One bounded authentication record, DATA only; no frame/body read permit.

    Retains an actual partial HBA1 record without deciding runtime transitions.
    Feed never accepts the following outer header or body. A refused record is
    permanently failed, not eligible for another phase parser or cursor restart.
    """

    def __init__(self, prefix: bytes, *, sender_public: bytes, receiver_public: bytes,
                 expected_context: dict):
        _require(type(self) is SignedCleanupAuthPrefix and "_initialized" not in vars(self))
        self._initialized = self._failed = self._finished = False
        self._buffer = self._buffer_origin = bytearray()
        self._context = self._context_origin = (os.getpid(), threading.get_ident())
        self._target = self._target_origin = 8
        self._header_done = self._header_done_origin = False
        failed = False
        try:
            keys = _EXPECTED - {"phase"}
            _require(type(prefix) is bytes and len(prefix) <= RECORD_LIMIT
                     and type(expected_context) is dict
                     and all(type(k) is str for k in expected_context)
                     and expected_context.keys() == keys
                     and all(type(v) is (int if k in ("sequence", "work_end_ns") else str)
                             for k, v in expected_context.items())
                     and expected_context["role"] == "broker"
                     and expected_context["direction"] == "b2g"
                     and expected_context["sequence"] in (0, 1, 2)
                     and type(sender_public) is bytes and len(sender_public) == 32
                     and type(receiver_public) is bytes and len(receiver_public) == 32
                     and sender_public != receiver_public)
            self._expected = self._expected_origin = tuple(sorted(expected_context.items()))
            self._pins = self._pins_origin = (sender_public, receiver_public)
            self._initialized = True
            offset = 0
            while offset < len(prefix):
                count = min(SignedCleanupAuthPrefix.needed.fget(self), len(prefix) - offset)
                _require(count > 0)
                SignedCleanupAuthPrefix.feed(self, prefix[offset:offset + count])
                offset += count
        except BaseException:
            failed = self._failed = True
            self._buffer_origin.clear()
        finally:
            prefix = None
        if failed:
            raise FrameError("BI1_CLEANUP_AUTH_PREFIX_REFUSED") from None

    def __repr__(self):
        return "<SignedCleanupAuthPrefix data-only redacted>"

    def _guard(self):
        _require(type(self) is SignedCleanupAuthPrefix and self._initialized is True
                 and self._failed is False and self._finished is False
                 and type(self._context) is tuple and self._context is self._context_origin
                 and len(self._context) == 2 and all(type(v) is int for v in self._context)
                 and self._context == (os.getpid(), threading.get_ident())
                 and type(self._buffer) is bytearray and self._buffer is self._buffer_origin
                 and type(self._target) is int and self._target is self._target_origin
                 and type(self._header_done) is bool
                 and self._header_done is self._header_done_origin
                 and ((self._header_done is False and self._target == 8)
                      or (self._header_done is True and 73 <= self._target <= RECORD_LIMIT))
                 and len(self._buffer) <= self._target
                 and type(self._pins) is tuple and self._pins is self._pins_origin
                 and len(self._pins) == 2
                 and all(type(v) is bytes and len(v) == 32 for v in self._pins)
                 and self._pins[0] != self._pins[1]
                 and type(self._expected) is tuple and self._expected is self._expected_origin
                 and len(self._expected) == len(_EXPECTED) - 1
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] in ("sequence", "work_end_ns") else str)
                         for row in self._expected)
                 and {row[0] for row in self._expected} == _EXPECTED - {"phase"})

    @property
    def needed(self):
        try:
            SignedCleanupAuthPrefix._guard(self)
            return self._target - len(self._buffer)
        except BaseException:
            self._failed = True
            self._buffer_origin.clear()
        raise FrameError("BI1_CLEANUP_AUTH_PREFIX_REFUSED") from None

    def feed(self, chunk: bytes):
        failed = False
        try:
            count = SignedCleanupAuthPrefix.needed.fget(self)
            _require(type(chunk) is bytes and 0 < len(chunk) <= count)
            self._buffer_origin.extend(chunk)
            if self._header_done is False and len(self._buffer) == 8:
                self._target = self._target_origin = 8 + payload_size(bytes(self._buffer))
                self._header_done = self._header_done_origin = True
            SignedCleanupAuthPrefix._guard(self)
        except BaseException:
            failed = self._failed = True
            self._buffer_origin.clear()
        finally:
            chunk = None
        if failed:
            raise FrameError("BI1_CLEANUP_AUTH_PREFIX_REFUSED") from None

    def finish(self) -> ConsistentCommitment:
        failed = False
        raw = None
        try:
            _require(SignedCleanupAuthPrefix.needed.fget(self) == 0
                     and self._header_done is True)
            raw = bytes(self._buffer)
            result = check_broker_cleanup_commitment(
                raw, sender_public=self._pins[0], receiver_public=self._pins[1],
                expected_context=dict(self._expected))
            SignedCleanupAuthPrefix._guard(self)
            self._finished = True
            self._buffer_origin.clear()
        except BaseException:
            failed = self._failed = True
            self._buffer_origin.clear()
        finally:
            raw = None
        if failed:
            raise FrameError("BI1_CLEANUP_AUTH_PREFIX_REFUSED") from None
        return result
