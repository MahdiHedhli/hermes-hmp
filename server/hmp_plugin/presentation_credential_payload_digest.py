"""Bounded RESULT-body digest DATA, never native image validation or authority.

The body is the complete result2 wire payload, not just image bytes. A native
caller must bind the actual chunks and original captured seed before using this
for terminal correlation. No buffer, socket, permission or release is supplied.
"""
from __future__ import annotations

import hashlib
import os
import threading
from typing import NamedTuple

from .presentation_credential_stream import _HASH_TYPE, CHUNK_LIMIT
from .presentation_jobs import OUTPUT_LIMIT, FrameError

_COPY = _HASH_TYPE.copy
_HEX = _HASH_TYPE.hexdigest
_UPDATE = _HASH_TYPE.update
_SHA256 = hashlib.sha256


def _require(value):
    if value is not True:
        raise FrameError("BI1_PAYLOAD_DIGEST_REFUSED")


class PayloadDigestFact(NamedTuple):
    owner: object
    hasher: object
    count: int
    sha256: str

    def __repr__(self):
        return "<PayloadDigestFact result2-body-DATA no-image-or-release-authority>"


class _Update:
    def __repr__(self):
        return "<PayloadDigestUpdate one-shot>"


class PayloadDigest:
    def __init__(self, *, source=None, seed_count=0, seed_sha256=None):
        _require(type(self) is PayloadDigest and "_initialized" not in vars(self))
        self._initialized = self._failed = self._inflight = False
        self._finish_attempted = self._finished = False
        self._context = self._context_origin = (os.getpid(), threading.get_ident())
        self._seed = self._seed_origin = (self, source, seed_count, seed_sha256)
        self._seed_cell = (self, self._seed)
        self._digest_cell = None
        self._hasher = self._hasher_origin = self._hash_cell = None
        self._received = self._received_origin = 0
        self._update = self._update_cell = self._fact = self._fact_cell = None
        failed = False
        hasher = actual = None
        try:
            _require(type(seed_count) is int and 0 <= seed_count <= OUTPUT_LIMIT)
            if source is None:
                _require(seed_count == 0 and seed_sha256 is None)
                hasher = _SHA256()
            else:
                _require(type(source) is _HASH_TYPE and type(seed_sha256) is str
                         and len(seed_sha256) == 64)
                actual = _HEX(source)
                _require(type(actual) is str and actual == seed_sha256)
                hasher = _COPY(source)
            self._hasher = self._hasher_origin = hasher
            self._hash_cell = (self, hasher)
            _require(type(hasher) is _HASH_TYPE and hasher is not source)
            actual = _HEX(hasher)
            _require(type(actual) is str and actual == (
                _SHA256().hexdigest() if source is None else seed_sha256))
            self._received = self._received_origin = seed_count
            self._digest_cell = (self, hasher, seed_count, actual)
            self._initialized = True
            PayloadDigest._metadata(self)
        except BaseException:
            failed = self._failed = True
        finally:
            source = hasher = actual = None
        if failed:
            raise FrameError("BI1_PAYLOAD_DIGEST_INITIALIZATION_UNKNOWN") from None

    def __repr__(self):
        return "<PayloadDigest bounded-result2-body-DATA redacted>"

    def _metadata(self):
        _require(type(self) is PayloadDigest and self._initialized is True
                 and self._failed is False
                 and all(type(v) is bool for v in (
                     self._inflight, self._finish_attempted, self._finished))
                 and type(self._context) is tuple and self._context is self._context_origin
                 and len(self._context) == 2 and all(type(v) is int for v in self._context)
                 and type(self._seed) is tuple and self._seed is self._seed_origin
                 and len(self._seed) == 4 and self._seed[0] is self
                 and type(self._seed_cell) is tuple and len(self._seed_cell) == 2
                 and self._seed_cell[0] is self and self._seed_cell[1] is self._seed
                 and (self._seed[1] is None or type(self._seed[1]) is _HASH_TYPE)
                 and type(self._seed[2]) is int and 0 <= self._seed[2] <= OUTPUT_LIMIT
                 and type(self._hasher) is _HASH_TYPE and self._hasher is self._hasher_origin
                 and type(self._hash_cell) is tuple and len(self._hash_cell) == 2
                 and self._hash_cell[0] is self and self._hash_cell[1] is self._hasher
                 and type(self._received) is int and self._received is self._received_origin
                 and self._seed[2] <= self._received <= OUTPUT_LIMIT
                 and type(self._digest_cell) is tuple and len(self._digest_cell) == 4
                 and self._digest_cell[0] is self and self._digest_cell[1] is self._hasher
                 and type(self._digest_cell[2]) is int and self._digest_cell[2] == self._received
                 and type(self._digest_cell[3]) is str and len(self._digest_cell[3]) == 64)
        return self._hasher_origin

    def _current(self):
        hasher = PayloadDigest._metadata(self)
        context = (os.getpid(), threading.get_ident())
        _require(PayloadDigest._metadata(self) is hasher and self._context == context)
        return hasher

    def feed(self, chunk):
        failed = admitted = False
        copy = None
        try:
            hasher = PayloadDigest._metadata(self)
            _require(self._inflight is False and self._finish_attempted is False
                     and self._finished is False and type(chunk) is bytes
                     and 0 < len(chunk) <= CHUNK_LIMIT
                     and self._received + len(chunk) <= OUTPUT_LIMIT)
            before, count = self._received, len(chunk)
            update = _Update.__new__(_Update)
            update.before, update.count = before, count
            update.attempted = update.returned = update.complete = False
            self._update, self._update_cell = update, (self, update)
            self._inflight = True
            admitted = True
            _require(PayloadDigest._current(self) is hasher)
            prior_cell = self._digest_cell
            prior = _HEX(hasher)
            _require(PayloadDigest._current(self) is hasher
                     and self._digest_cell is prior_cell
                     and type(prior) is str and prior == prior_cell[3])
            copy = _COPY(hasher)
            _require(type(copy) is _HASH_TYPE and copy is not hasher)
            _UPDATE(copy, chunk)
            expected = _HEX(copy)
            _require(type(expected) is str)
            _require(PayloadDigest._current(self) is hasher
                     and self._received == before and self._update is update
                     and type(self._update_cell) is tuple and len(self._update_cell) == 2
                     and self._update_cell[0] is self and self._update_cell[1] is update)
            update.attempted = True
            _UPDATE(hasher, chunk)
            update.returned = True
            actual = _HEX(hasher)
            _require(type(actual) is str and actual == expected)
            self._received = self._received_origin = before + count
            self._digest_cell = (self, hasher, before + count, actual)
            _require(PayloadDigest._current(self) is hasher
                     and type(actual) is str and actual == expected
                     and self._received == before + count and self._update is update
                     and type(self._update_cell) is tuple and len(self._update_cell) == 2
                     and self._update_cell[0] is self and self._update_cell[1] is update)
            update.complete = True
            self._inflight = False
            # The current state does not retain completed update self-cycles.
            self._update = self._update_cell = None
        except BaseException:
            failed = True
            if admitted and type(self) is PayloadDigest:
                self._failed = True
        finally:
            chunk = copy = None
        if failed:
            raise FrameError("BI1_PAYLOAD_DIGEST_UPDATE_UNKNOWN") from None

    def finish(self, count):
        hasher = PayloadDigest._metadata(self)
        _require(type(count) is int and count == self._received and self._inflight is False
                 and self._finish_attempted is False and self._finished is False)
        self._finish_attempted = True
        failed = False
        try:
            _require(PayloadDigest._current(self) is hasher)
            digest_cell = self._digest_cell
            value = _HEX(hasher)
            _require(PayloadDigest._current(self) is hasher
                     and self._digest_cell is digest_cell
                     and type(value) is str and value == digest_cell[3])
            fact = PayloadDigestFact(self, hasher, count, value)
            self._fact, self._fact_cell = fact, (self, fact)
            _require(PayloadDigest._current(self) is hasher and self._received == count)
            self._finished = True
            _require(PayloadDigest.current_fact(self, count) is fact)
            return fact
        except BaseException:
            failed = self._failed = True
        if failed:
            raise FrameError("BI1_PAYLOAD_DIGEST_FINISH_UNKNOWN") from None

    def current_fact(self, count):
        """Pure allocation/counter joins; caller owns native currentness separately."""
        hasher = PayloadDigest._metadata(self)
        fact = self._fact
        _require(
            self._inflight is False
            and self._finish_attempted is True
            and self._finished is True
            and type(count) is int
            and self._received == count
            and type(fact) is PayloadDigestFact
            and fact.owner is self
            and fact.hasher is hasher
            and type(fact.count) is int
            and fact.count == count
            and type(fact.sha256) is str
            and len(fact.sha256) == 64
            and type(self._fact_cell) is tuple
            and len(self._fact_cell) == 2
            and self._fact_cell[0] is self
            and self._fact_cell[1] is fact
        )
        return fact
