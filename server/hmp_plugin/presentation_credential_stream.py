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

from .presentation_broker_codec import BrokerBinding, _binding
from .presentation_credential_phase import ConsistentCommitment, check_committed_header
from .presentation_jobs import FrameError

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
