"""Private BI1 presentation frame and ownership core.

This module is intentionally not imported by a route. Native authorization and
the actual child supervisor remain unbound. A caller cannot use a child result
as an authorization receipt.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import secrets
import struct
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

INPUT_LIMIT = 8192
HEADER_LIMIT = 8192
AVATAR_LIMIT = 2_000_000
OUTPUT_LIMIT = 2_008_196
DIAGNOSTIC_LIMIT = 4096
MAX_CHAIN_ROWS = 32
MAX_WAITING = 16
MAX_METADATA = 4
MAX_AVATAR = 2
MAX_PER_PROFILE = 1
MAX_PROCESSES = 6
MAX_TARGET_FDS = 204
MAX_TERMINAL_JOURNAL = 64
JOB_SECONDS = 2.0
_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_CHALLENGE = re.compile(r"[0-9a-f]{64}\Z")
_FIELD_NAMES = frozenset({"display_name", "title", "shape", "color", "custom"})
_SHAPES = frozenset(
    {"circle", "squircle", "pill", "triangle", "hexagon", "cloud", "drop", "blobatar"}
)
_BLOB_KINDS = frozenset(
    {"round", "organic", "boxy", "capsule", "nub", "cloud", "droplet", "hexagon", "sun", "triangle"}
)
_BLOB = re.compile(r"blobatar(?::([a-z0-9]{0,32})(?::([a-z]+))?)?\Z", re.ASCII)
_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z", re.ASCII)
_INPUT_KEYS = frozenset(
    {
        "schema",
        "challenge",
        "epoch",
        "profile",
        "root",
        "home",
        "operation",
        "expected_avatar_sha",
        "uid",
        "gid",
        "dir_modes",
        "leaf_modes",
        "source_manifest_sha",
        "deadline_ns",
    }
)
_HEADER_KEYS = frozenset(
    {
        "schema",
        "challenge",
        "epoch",
        "outcome",
        "fields",
        "mime",
        "width",
        "height",
        "avatar_sha",
        "avatar_length",
        "source_proof",
        "absence_bitmap",
        "chain",
        "ledger",
        "cleanup",
    }
)
_SOURCE_KEYS = frozenset({"profile_meta", "profile_sha", "avatar_meta", "avatar_body_sha"})
_LEDGER_KEYS = frozenset(
    {"body_bytes", "opens", "metadata", "path_bytes", "raster_units", "yaml_nodes"}
)
_CLEANUP_KEYS = frozenset({"known_fds_closed", "unknown_close"})


class FrameError(ValueError):
    """Closed, non-sensitive frame refusal."""


def _fail() -> None:
    raise FrameError("BI1_FRAME_REFUSED")


class BoundedResultBuffer:
    """A one-use private IPC accumulator. The caller supplies observed EOF."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._done = False
        self._declared_header: int | None = None
        self._declared_body: int | None = None

    def feed(self, chunk: bytes) -> None:
        if self._done or type(chunk) is not bytes or not chunk or len(chunk) > 65536:
            _fail()
        if len(self._buffer) + len(chunk) > OUTPUT_LIMIT:
            _fail()
        self._buffer.extend(chunk)
        if len(self._buffer) >= 4 and self._declared_header is None:
            self._declared_header = struct.unpack(">I", self._buffer[:4])[0]
            if self._declared_header > HEADER_LIMIT:
                _fail()
        if self._declared_header is not None and len(self._buffer) >= 4 + self._declared_header:
            if self._declared_body is None:
                header = validate_header(
                    _json(bytes(self._buffer[4 : 4 + self._declared_header]), HEADER_LIMIT)
                )
                self._declared_body = header["avatar_length"]
            if len(self._buffer) > 4 + self._declared_header + self._declared_body:
                _fail()

    def finish(self, challenge: str, epoch: int) -> tuple[dict[str, object], bytes]:
        if self._done:
            _fail()
        self._done = True
        return decode_output(bytes(self._buffer), challenge, epoch)

    def wipe(self) -> None:
        self._buffer[:] = b"\x00" * len(self._buffer)
        self._buffer.clear()
        self._done = True


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            _fail()
        result[key] = value
    return result


def _closed(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or value.keys() != keys:
        _fail()
    return value


def _number(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail()
    return value


def _digest(value: object, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail()
    return value


def _utf8(value: object, ceiling: int) -> str:
    if type(value) is not str or not value:
        _fail()
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as error:
        raise FrameError("BI1_FRAME_REFUSED") from error
    if len(encoded) > ceiling:
        _fail()
    return value


def _path(value: object) -> str:
    path = _utf8(value, 4096)
    if not path.startswith("/") or path == "/" or "\x00" in path:
        _fail()
    parts = path[1:].split("/")
    if len(parts) > 32 or any(part in ("", ".", "..") for part in parts):
        _fail()
    return path


def _json(raw: bytes, ceiling: int) -> dict[str, object]:
    if type(raw) is not bytes or len(raw) > ceiling:
        _fail()
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: _fail(),
        )
    except (UnicodeError, json.JSONDecodeError, TypeError, RecursionError) as error:
        raise FrameError("BI1_FRAME_REFUSED") from error
    if type(value) is not dict:
        _fail()
    return value


def _envelope(value: dict[str, object], ceiling: int) -> bytes:
    try:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise FrameError("BI1_FRAME_REFUSED") from error
    if len(raw) > ceiling:
        _fail()
    return struct.pack(">I", len(raw)) + raw


def _one_frame(wire: bytes, ceiling: int) -> dict[str, object]:
    if type(wire) is not bytes or len(wire) < 4:
        _fail()
    length = struct.unpack(">I", wire[:4])[0]
    if length > ceiling or len(wire) != 4 + length:
        _fail()
    return _json(wire[4:], ceiling)


def validate_input(value: object) -> dict[str, object]:
    row = _closed(value, _INPUT_KEYS)
    if _number(row["schema"], 1, 1) != 1:
        _fail()
    if type(row["challenge"]) is not str or _CHALLENGE.fullmatch(row["challenge"]) is None:
        _fail()
    _number(row["epoch"], 1, (1 << 63) - 1)
    if type(row["profile"]) is not str or _PROFILE.fullmatch(row["profile"]) is None:
        _fail()
    root = _path(row["root"])
    home = _path(row["home"])
    if home != root and not home.startswith(root + "/"):
        _fail()
    if row["operation"] not in ("METADATA", "AVATAR"):
        _fail()
    _digest(row["expected_avatar_sha"], nullable=True)
    _digest(row["source_manifest_sha"])
    _number(row["uid"], 0, (1 << 31) - 1)
    _number(row["gid"], 0, (1 << 31) - 1)
    for name, expected in (
        ("dir_modes", [448, 488, 493]),
        ("leaf_modes", [384, 416, 420]),
    ):
        actual = row[name]
        if (
            type(actual) is not list
            or len(actual) != len(expected)
            or any(
                type(item) is not int or item != wanted
                for item, wanted in zip(actual, expected, strict=True)
            )
        ):
            _fail()
    _number(row["deadline_ns"], 1, (1 << 63) - 1)
    return row


def encode_input(value: dict[str, object]) -> bytes:
    return _envelope(validate_input(value), INPUT_LIMIT)


def decode_input(wire: bytes) -> dict[str, object]:
    return validate_input(_one_frame(wire, INPUT_LIMIT))


def _proof_meta(value: object, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if type(value) is not list or len(value) != 9:
        _fail()
    for item in value:
        _number(item, 0, (1 << 63) - 1)


def validate_header(value: object) -> dict[str, object]:
    row = _closed(value, _HEADER_KEYS)
    _number(row["schema"], 1, 1)
    if type(row["challenge"]) is not str or _CHALLENGE.fullmatch(row["challenge"]) is None:
        _fail()
    _number(row["epoch"], 1, (1 << 63) - 1)
    if row["outcome"] not in ("OK", "REFUSED"):
        _fail()
    fields = row["fields"]
    if type(fields) is not dict or not fields.keys() <= _FIELD_NAMES or len(fields) > 5:
        _fail()
    for key, item in fields.items():
        if key in ("display_name", "title"):
            _utf8(item, 256)
        elif key == "shape":
            if type(item) is not str or len(item) > 128:
                _fail()
            if item not in _SHAPES:
                match = _BLOB.fullmatch(item)
                if match is None or (match[2] is not None and match[2] not in _BLOB_KINDS):
                    _fail()
        elif key == "color":
            if type(item) is not str or _COLOR.fullmatch(item) is None:
                _fail()
        elif type(item) not in (bool, type(None)):
            _fail()
    if row["mime"] not in (None, "image/png", "image/jpeg", "image/webp"):
        _fail()
    _number(row["width"], 0, 1024)
    _number(row["height"], 0, 1024)
    _digest(row["avatar_sha"], nullable=True)
    _number(row["avatar_length"], 0, AVATAR_LIMIT)
    if row["avatar_sha"] is None:
        if (
            row["mime"] is not None
            or row["width"] != 0
            or row["height"] != 0
            or row["avatar_length"] != 0
        ):
            _fail()
    elif row["mime"] is None or row["width"] == 0 or row["height"] == 0:
        _fail()
    proof = _closed(row["source_proof"], _SOURCE_KEYS)
    _proof_meta(proof["profile_meta"], nullable=True)
    _proof_meta(proof["avatar_meta"], nullable=True)
    _digest(proof["profile_sha"], nullable=True)
    _digest(proof["avatar_body_sha"], nullable=True)
    if (proof["profile_meta"] is None) != (proof["profile_sha"] is None):
        _fail()
    if (proof["avatar_meta"] is None) != (proof["avatar_body_sha"] is None):
        _fail()
    if row["avatar_sha"] != proof["avatar_body_sha"]:
        _fail()
    _number(row["absence_bitmap"], 0, 15)
    chain = row["chain"]
    if type(chain) is not list or len(chain) > MAX_CHAIN_ROWS:
        _fail()
    for item in chain:
        _proof_meta(item)
    ledger = _closed(row["ledger"], _LEDGER_KEYS)
    for name, limit in (
        ("body_bytes", 4_131_076),
        ("opens", 80),
        ("metadata", 1024),
        ("path_bytes", 32768),
        ("raster_units", 10000),
        ("yaml_nodes", 256),
    ):
        _number(ledger[name], 0, limit)
    cleanup = _closed(row["cleanup"], _CLEANUP_KEYS)
    if type(cleanup["known_fds_closed"]) is not bool or type(cleanup["unknown_close"]) is not bool:
        _fail()
    if row["outcome"] == "OK" and (not cleanup["known_fds_closed"] or cleanup["unknown_close"]):
        _fail()
    if row["outcome"] == "REFUSED" and (
        fields or row["avatar_length"] or row["avatar_sha"] is not None
    ):
        _fail()
    return row


def encode_output(header: dict[str, object], avatar: bytes) -> bytes:
    row = validate_header(header)
    if type(avatar) is not bytes or len(avatar) != row["avatar_length"]:
        _fail()
    if avatar and hashlib.sha256(avatar).hexdigest() != row["avatar_sha"]:
        _fail()
    wire = _envelope(row, HEADER_LIMIT) + avatar
    if len(wire) > OUTPUT_LIMIT:
        _fail()
    return wire


def decode_output(wire: bytes, challenge: str, epoch: int) -> tuple[dict[str, object], bytes]:
    if type(wire) is not bytes or len(wire) < 4 or len(wire) > OUTPUT_LIMIT:
        _fail()
    length = struct.unpack(">I", wire[:4])[0]
    if length > HEADER_LIMIT or len(wire) < 4 + length:
        _fail()
    row = validate_header(_json(wire[4 : 4 + length], HEADER_LIMIT))
    avatar = wire[4 + length :]
    if row["challenge"] != challenge or row["epoch"] != epoch:
        _fail()
    if len(avatar) != row["avatar_length"]:
        _fail()
    if avatar and hashlib.sha256(avatar).hexdigest() != row["avatar_sha"]:
        _fail()
    return row, avatar


@dataclass(frozen=True)
class CapturedLease:
    iid: str
    device_id: str
    user_id: str
    family_id: str
    profile: str
    credential_digest: str
    native_binding: str
    epoch: int

    def __post_init__(self) -> None:
        for value in (self.iid, self.device_id, self.user_id, self.family_id, self.native_binding):
            _utf8(value, 256)
        if _PROFILE.fullmatch(self.profile) is None:
            _fail()
        _digest(self.credential_digest)
        _number(self.epoch, 1, (1 << 63) - 1)


class AuthorityPort(Protocol):
    async def reauthenticate(self, lease: CapturedLease, stage: str) -> bool: ...


class UnboundAuthority:
    async def reauthenticate(self, lease: CapturedLease, stage: str) -> bool:
        del lease, stage
        return False


class State(Enum):
    QUEUED = "QUEUED"
    AUTHORIZED = "AUTHORIZED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DRAINING = "DRAINING"
    COMPLETE = "COMPLETE"
    REAUTHORIZED = "REAUTHORIZED"
    EMIT = "EMIT"
    REFUSED = "REFUSED"
    UNKNOWN = "UNKNOWN"


class JobHandle:
    """Opaque identity, never a mutable job record or authority token."""

    __slots__ = ()


class RemotePhase(Enum):
    BOUND = "BOUND"
    BEGIN_INTENT = "BEGIN_INTENT"
    READY = "READY"
    GO_INTENT = "GO_INTENT"
    GO_SENT = "GO_SENT"
    RESULT_VALIDATED = "RESULT_VALIDATED"
    DRAINING = "DRAINING"
    UNKNOWN = "UNKNOWN"


class RemoteSlot:
    """Shared one-use retained owner cell, not authority or a second ledger."""
    __slots__ = ("_bound", "_owner", "_owner_snapshot")

    def __init__(self):
        self._owner = self._owner_snapshot = None
        self._bound = False

    def read(self):
        if (type(self._bound) is not bool or self._owner is not self._owner_snapshot
                or (self._owner is None) is self._bound):
            _fail()
        return self._owner

    def install(self, owner):
        if self.read() is not None or owner is None:
            _fail()
        self._owner = self._owner_snapshot = owner
        self._bound = True  # no callback/await; this slot is never reset or cleared


@dataclass
class _Job:
    number: int
    challenge: str
    lease: CapturedLease
    operation: str
    profile: str
    queued_at: float
    deadline: float
    last_clock: float | int
    state: State = State.QUEUED
    child: object | None = None
    remote_slot: RemoteSlot = field(default_factory=RemoteSlot)
    _remote_slot_snapshot: RemoteSlot = field(init=False, repr=False)
    remote_phase: RemotePhase | None = None
    go_sent: bool = False
    output_buffer: BoundedResultBuffer = field(default_factory=BoundedResultBuffer)
    parent_result_context: tuple[str, object] | None = None
    result: tuple[dict[str, object], bytes] | None = None
    remote_result_token: object | None = None
    _remote_candidate_custody_origin: tuple | None = None
    _remote_candidate_custody_snapshot: tuple | None = None
    remote_output_origin: object | None = None
    remote_output_custody: tuple | None = None
    _remote_output_custody_snapshot: tuple | None = None
    result_eof: bool = False
    result_aborted: bool = False
    diagnostic_eof: bool = False
    diagnostic_bytes: int = 0
    wait_done: bool = False
    wait_success: bool = False
    group_gone: bool = False
    ipc_closed: bool = False
    signal_closed: bool = False
    emit_revoked: bool = False
    credit_released: bool = False
    seen_events: set[str] = field(default_factory=set)


    def __post_init__(self):
        self._remote_slot_snapshot = self.remote_slot


@dataclass(frozen=True)
class _TerminalSummary:
    state: State
    go_sent: bool
    credit_released: bool


class JobOwner:
    """A parent-only ownership ledger. Does not spawn, signal, or read files."""

    def __init__(
        self,
        iid: str,
        authority: AuthorityPort | None = None,
        clock: Callable[[], float] = time.monotonic,
        challenge_source: Callable[[], str] = lambda: secrets.token_hex(32),
    ) -> None:
        self._iid = _utf8(iid, 256)
        self._authority = authority if authority is not None else UnboundAuthority()
        self._clock = clock
        self._challenge_source = challenge_source
        self._epoch = 1
        self._next_number = 1
        self._jobs: dict[JobHandle, _Job] = {}
        self._waiting: list[JobHandle] = []
        self._terminal: dict[JobHandle, _TerminalSummary] = {}
        self._terminal_order: deque[JobHandle] = deque()
        self._disabled = False

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def disabled(self) -> bool:
        return self._disabled

    def _checked_clock(self, job: _Job) -> float | int | None:
        """Reject invalid or backward later samples without extending the job deadline."""
        try:
            now = self._clock()
        except Exception:
            return None
        if type(now) not in (float, int) or not 0 <= now < float("inf"):
            return None
        if now < job.last_clock:
            return None
        job.last_clock = now
        return now

    def _current(self, job: _Job) -> bool:
        if self._disabled or job.emit_revoked or job.lease.epoch != self._epoch:
            return False
        now = self._checked_clock(job)
        return now is not None and now < job.deadline

    def queue(self, lease: CapturedLease, operation: str) -> JobHandle:
        if (
            self._disabled
            or lease.iid != self._iid
            or lease.epoch != self._epoch
            or operation not in ("METADATA", "AVATAR")
        ):
            _fail()
        try:
            challenge = self._challenge_source()
        except Exception as error:
            raise FrameError("BI1_CHALLENGE_UNAVAILABLE") from error
        if type(challenge) is not str or _CHALLENGE.fullmatch(challenge) is None:
            _fail()
        if self._next_number > (1 << 64) - 1:
            _fail()
        # The counter makes replay keys unique across terminal-journal eviction;
        # the remaining 192 random bits keep the challenge unpredictable.
        challenge = f"{self._next_number:016x}" + challenge[16:]
        now = self._clock()
        if type(now) not in (float, int) or not 0 <= now < float("inf"):
            _fail()
        try:
            deadline = now + JOB_SECONDS
        except OverflowError:
            _fail()
        if not now < deadline < float("inf"):
            _fail()
        if len(self._waiting) >= MAX_WAITING or any(
            job.challenge == challenge for job in self._jobs.values()
        ):
            _fail()
        job = _Job(
            self._next_number,
            challenge,
            lease,
            operation,
            lease.profile,
            now,
            deadline,
            now,
        )
        handle = JobHandle()
        self._next_number += 1
        self._jobs[handle] = job
        self._waiting.append(handle)
        return handle

    def _resolve(self, handle: JobHandle) -> _Job:
        if (type(self._jobs) is not dict or type(handle) is not JobHandle
                or handle not in self._jobs):
            _fail()
        return self._jobs[handle]

    def challenge(self, handle: JobHandle) -> str:
        """The active private pipe nonce, never a native authorization grant."""
        return self._resolve(handle).challenge

    def inspect(self, handle: JobHandle) -> tuple[State, bool, bool]:
        if type(handle) is not JobHandle:
            _fail()
        if type(self._jobs) is not dict:
            _fail()
        job = self._jobs.get(handle)
        if job is not None:
            return job.state, job.go_sent, job.credit_released
        summary = self._terminal.get(handle)
        if summary is None:
            _fail()
        return summary.state, summary.go_sent, summary.credit_released

    @staticmethod
    def _remote(job: _Job):
        if (type(job.remote_slot) is not RemoteSlot
                or job.remote_slot is not job._remote_slot_snapshot):
            _fail()
        remote = RemoteSlot.read(job.remote_slot)
        if ((remote is None) != (job.remote_phase is None)
                or (remote is not None and type(job.remote_phase) is not RemotePhase)):
            _fail()
        return remote

    def remote_slot(self, handle: JobHandle) -> RemoteSlot:
        job = self._resolve(handle)
        self._remote(job)
        return job.remote_slot

    def bind_remote(self, handle: JobHandle, remote: object) -> None:
        from .presentation_remote import RemoteOperationOwner

        job = self._resolve(handle)
        self._require(job, State.STARTING)
        if (type(remote) is not RemoteOperationOwner or self._remote(job) is not None
                or job.child is not None or job.parent_result_context is None
                or job.go_sent or self._disabled):
            _fail()
        # One shared cell is retained by both ledgers before initialization.
        # No foreign clock, callback or await follows installation here.
        RemoteSlot.install(job.remote_slot, remote)
        from .presentation_output_v2 import BoundedResultBufferV2

        if (type(job.output_buffer) is not BoundedResultBufferV2
                or type(job.output_buffer._buffer) is not bytearray):
            _fail()
        job.remote_output_origin = job.output_buffer
        job.remote_output_custody = job._remote_output_custody_snapshot = (
            job, job.output_buffer, job.output_buffer._buffer)
        job.remote_phase = RemotePhase.BOUND

    def inspect_remote(self, handle: JobHandle) -> RemotePhase | None:
        job = self._resolve(handle)
        self._remote(job)
        return job.remote_phase

    def remote_transition(self, handle: JobHandle, remote: object, phase: RemotePhase) -> None:
        from .presentation_remote import RemoteOperationOwner

        job = self._resolve(handle)
        if type(phase) is not RemotePhase:
            _fail()
        expected = {RemotePhase.BEGIN_INTENT: RemotePhase.BOUND,
                    RemotePhase.READY: RemotePhase.BEGIN_INTENT,
                    RemotePhase.GO_INTENT: RemotePhase.READY,
                    RemotePhase.GO_SENT: RemotePhase.GO_INTENT}.get(phase)
        state = State.RUNNING if phase is RemotePhase.GO_SENT else State.STARTING
        if (expected is None or self._remote(job) is not remote
                or job.remote_phase is not expected or job.state is not state
                or job.child is not None):
            _fail()
        if phase in (RemotePhase.GO_INTENT, RemotePhase.GO_SENT):
            RemoteOperationOwner._authorize_job_go(remote, self, handle, phase)
        if not self._current(job):
            _fail()
        # The shared clock can reenter; recheck exact ownership after it returns.
        if (self._jobs.get(handle) is not job or self._remote(job) is not remote
                or job.remote_phase is not expected or job.state is not state
                or job.child is not None or job.emit_revoked or self._disabled):
            _fail()
        if phase in (RemotePhase.GO_INTENT, RemotePhase.GO_SENT):
            RemoteOperationOwner._authorize_job_go(remote, self, handle, phase)
        if phase is RemotePhase.GO_INTENT:
            remote._go_admission_used = True  # intent before any possibly partial wire write
            job.go_sent = True  # remote intent, not receipt/execution evidence
            job.state = State.RUNNING
        job.remote_phase = phase

    def _retire(self, handle: JobHandle) -> None:
        job = self._resolve(handle)
        if (
            job.state not in (State.REFUSED, State.EMIT)
            or not job.credit_released
            or self._remote(job) is not None
            or (job.child is not None and not self._drained(job))
        ):
            _fail()
        self._terminal[handle] = _TerminalSummary(job.state, job.go_sent, True)
        self._terminal_order.append(handle)
        job.output_buffer.wipe()
        job.result = None
        del self._jobs[handle]
        if len(self._terminal_order) > MAX_TERMINAL_JOURNAL:
            oldest = self._terminal_order.popleft()
            del self._terminal[oldest]

    async def authorize(self, handle: JobHandle) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        self._require(job, State.QUEUED)
        if not self._current(job):
            self.cancel(handle)
            return
        try:
            accepted = await self._authority.reauthenticate(job.lease, "BEFORE")
        except Exception:
            self.unknown(handle)
            return
        if self._jobs.get(handle) is not job:
            return
        if accepted is not True or not self._current(job):
            self.cancel(handle)
            return
        if self._active(job.operation) >= (
            MAX_METADATA if job.operation == "METADATA" else MAX_AVATAR
        ):
            _fail()
        if (
            sum(
                other.state not in (State.QUEUED, State.REFUSED, State.EMIT)
                and not other.credit_released
                and other.profile == job.profile
                and other.operation == "METADATA"
                for other in self._jobs.values()
            )
            >= MAX_PER_PROFILE
        ):
            _fail()
        job.state = State.AUTHORIZED
        self._waiting.remove(handle)

    def _active(self, operation: str) -> int:
        return sum(
            job.operation == operation
            and job.state not in (State.QUEUED, State.REFUSED, State.EMIT)
            and not job.credit_released
            for job in self._jobs.values()
        )

    def _require(self, job: _Job, expected: State) -> None:
        if job.state is not expected:
            _fail()

    def start(self, handle: JobHandle) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        self._require(job, State.AUTHORIZED)
        if not self._current(job):
            self.cancel(handle)
            return
        active = sum(
            other.state
            in (State.STARTING, State.RUNNING, State.DRAINING, State.COMPLETE, State.REAUTHORIZED)
            and not other.credit_released
            for other in self._jobs.values()
        )
        if active >= MAX_PROCESSES or (active + 1) * 34 > MAX_TARGET_FDS:
            _fail()
        job.state = State.STARTING

    def bind_parent_result(self, handle: JobHandle, home: str, snapshot: object) -> None:
        """Select result2 once before launch, retaining exact parent work/chain."""
        from types import MappingProxyType

        from .presentation_budget import PresentationWorkLedger
        from .presentation_output_v2 import BoundedResultBufferV2
        from .presentation_parent_policy import ParentPolicySnapshot

        job = self._resolve(handle)
        self._require(job, State.STARTING)
        if (self._remote(job) is not None or job.child is not None
                or job.parent_result_context is not None):
            _fail()
        if type(snapshot) is not ParentPolicySnapshot:
            _fail()
        counts = PresentationWorkLedger.validate_parent_counts(home, dict(snapshot.counts))
        if (
            type(snapshot.chain) is not tuple
            or len(snapshot.chain) != counts["opens"]
            or any(
                type(item) is not tuple
                or len(item) != 9
                or any(type(v) is not int or not 0 <= v < 1 << 63 for v in item)
                for item in snapshot.chain
            )
        ):
            _fail()
        retained = ParentPolicySnapshot(snapshot.rules, snapshot.chain, MappingProxyType(counts))
        if not self._current(job) or self._jobs.get(handle) is not job:
            _fail()
        # No foreign callbacks after checking the retained sample.
        if (
            self._disabled
            or job.emit_revoked
            or job.lease.epoch != self._epoch
            or job.state is not State.STARTING
            or job.child is not None
            or job.parent_result_context is not None
        ):
            _fail()
        job.output_buffer.wipe()
        job.output_buffer = BoundedResultBufferV2()
        job.parent_result_context = (home, retained)

    def bind_child(self, handle: JobHandle, child: object) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        if job.state not in (State.STARTING, State.DRAINING):
            _fail()
        if job.child is not None or child is None:
            self.unknown(handle)
            return
        late_drain = job.state is State.DRAINING
        job.child = child
        if late_drain or not self._current(job):
            job.state = State.DRAINING
            job.emit_revoked = True

    def go(self, handle: JobHandle, child: object, challenge: str) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        self._require(job, State.STARTING)
        if job.child is not child or challenge != job.challenge or not self._current(job):
            self.unknown(handle)
            return
        job.go_sent = True
        job.state = State.RUNNING

    def feed_result(self, handle: JobHandle, chunk: bytes, child: object) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        if job.state not in (State.RUNNING, State.DRAINING):
            self.unknown(handle)
            return
        if child is not job.child or not job.go_sent or job.result_eof:
            self.unknown(handle)
            return
        try:
            job.output_buffer.feed(chunk)
        except FrameError:
            self.unknown(handle)

    def diagnostic(self, handle: JobHandle, size: int) -> None:
        job = self._resolve(handle)
        if job.state not in (State.RUNNING, State.DRAINING) or type(size) is not int or size < 0:
            self.unknown(handle)
            return
        job.diagnostic_bytes += size
        if job.diagnostic_bytes > DIAGNOSTIC_LIMIT:
            self.unknown(handle)

    def custody(self, handle: JobHandle, event: str, child: object) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        if (
            job.child is None
            or child is None
            or child is not job.child
            or event
            not in (
                "RESULT_EOF",
                "RESULT_ABORTED_EOF",
                "DIAGNOSTIC_EOF",
                "WAIT_OK",
                "WAIT_FAIL",
                "GROUP_GONE",
                "IPC_CLOSED",
                "SIGNAL_CLOSED",
            )
            or event in job.seen_events
        ):
            self.unknown(handle)
            return
        if job.state not in (State.RUNNING, State.DRAINING):
            self.unknown(handle)
            return
        if event in ("RESULT_EOF", "RESULT_ABORTED_EOF") and job.result_eof:
            self.unknown(handle)
            return
        if event == "RESULT_ABORTED_EOF" and (
            job.state is not State.DRAINING or not job.emit_revoked
        ):
            self.unknown(handle)
            return
        if event in ("WAIT_OK", "WAIT_FAIL") and job.wait_done:
            self.unknown(handle)
            return
        if event == "GROUP_GONE" and not job.wait_done:
            self.unknown(handle)
            return
        if event == "IPC_CLOSED" and not (job.result_eof and job.diagnostic_eof):
            self.unknown(handle)
            return
        if event == "SIGNAL_CLOSED" and not job.group_gone:
            self.unknown(handle)
            return
        job.seen_events.add(event)
        if event == "RESULT_ABORTED_EOF":
            # The exact adapter must have established fixed-worker OS closure.
            # This is refusal-only, never a fallback after a parser failure.
            job.result_eof = True
            job.result_aborted = True
            job.output_buffer.wipe()
            job.result = None
        elif event == "RESULT_EOF":
            job.result_eof = True
            if job.go_sent:
                try:
                    result = job.output_buffer.finish(job.challenge, job.lease.epoch)
                    if job.parent_result_context is not None:
                        from .presentation_output_v2 import compare_parent_snapshot

                        home, snapshot = job.parent_result_context
                        compare_parent_snapshot(result[0], snapshot=snapshot, parent_home=home)
                    job.result = result
                except FrameError:
                    self.unknown(handle)
                    return
        elif event == "DIAGNOSTIC_EOF":
            job.diagnostic_eof = True
        elif event in ("WAIT_OK", "WAIT_FAIL"):
            job.wait_done = True
            job.wait_success = event == "WAIT_OK"
        elif event == "GROUP_GONE":
            job.group_gone = True
        elif event == "IPC_CLOSED":
            job.ipc_closed = True
        else:
            job.signal_closed = True
        if self._drained(job):
            if job.go_sent and job.result is None and not job.result_aborted:
                self.unknown(handle)
                return
            if job.result is not None and job.result[0]["cleanup"] != {
                "known_fds_closed": True,
                "unknown_close": False,
            }:
                self.unknown(handle)
                return
            job.state = (
                State.COMPLETE if not job.emit_revoked and self._complete(job) else State.REFUSED
            )
            if job.state is State.REFUSED:
                job.credit_released = True
                self._retire(handle)

    def _drained(self, job: _Job) -> bool:
        return (
            self._remote(job) is None
            and job.result_eof
            and job.diagnostic_eof
            and job.wait_done
            and job.group_gone
            and job.ipc_closed
            and job.signal_closed
        )

    def _complete(self, job: _Job) -> bool:
        return (
            self._remote(job) is None
            and not job.result_aborted
            and job.result is not None
            and job.result[0]["outcome"] == "OK"
            and job.result[0]["cleanup"] == {"known_fds_closed": True, "unknown_close": False}
            and job.wait_success
        )

    async def reauthorize(self, handle: JobHandle) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        self._require(job, State.COMPLETE)
        if not self._current(job):
            self.cancel(handle)
            return
        try:
            accepted = await self._authority.reauthenticate(job.lease, "AFTER")
        except Exception:
            self.unknown(handle)
            return
        if self._jobs.get(handle) is not job:
            return
        if accepted is not True or not self._current(job):
            self.cancel(handle)
            return
        job.state = State.REAUTHORIZED

    def emit_inline(
        self,
        handle: JobHandle,
        still_current: Callable[[CapturedLease], bool],
        sink: Callable[[dict[str, object], bytes], None],
    ) -> None:
        job = self._resolve(handle)
        if self._remote(job) is not None:
            self.unknown(handle)
            return
        self._require(job, State.REAUTHORIZED)
        try:
            current = still_current(job.lease)
        except Exception:
            self.unknown(handle)
            return
        if not self._current(job) or current is not True or job.result is None:
            self.cancel(handle)
            return
        if inspect.iscoroutinefunction(sink):
            self.unknown(handle)
            return
        # No await is permitted between the final current check and sink entry.
        job.state = State.EMIT
        job.emit_revoked = True
        header, avatar = job.result
        try:
            returned = sink(header, avatar)
        except Exception:
            self.unknown(handle)
            raise
        if returned is not None:
            if inspect.iscoroutine(returned):
                returned.close()
            self.unknown(handle)
            return
        job.credit_released = True
        self._retire(handle)

    def deadline(self, handle: JobHandle) -> None:
        if handle in self._terminal:
            return
        job = self._resolve(handle)
        now = self._checked_clock(job)
        if now is None or now >= job.deadline:
            self.cancel(handle)

    def cancel(self, handle: JobHandle) -> None:
        if handle in self._terminal:
            return
        job = self._resolve(handle)
        job.emit_revoked = True
        if self._remote(job) is not None:
            JobOwner._wipe_remote_candidate(job)
            if job.state is not State.UNKNOWN:
                job.state = State.DRAINING
                job.remote_phase = RemotePhase.DRAINING
            return  # remote credits require a separately reviewed terminal proof
        if job.state in (State.QUEUED, State.AUTHORIZED, State.COMPLETE, State.REAUTHORIZED):
            if handle in self._waiting:
                self._waiting.remove(handle)
            job.state = State.REFUSED
            job.credit_released = True
            self._retire(handle)
        elif job.state not in (State.REFUSED, State.UNKNOWN, State.EMIT):
            job.state = State.DRAINING
            if job.remote_phase is not None:
                job.remote_phase = RemotePhase.DRAINING

    def refuse_prelaunch(self, handle: JobHandle) -> None:
        """Caller must first establish policy closure and no launch/input attempt."""
        job = self._resolve(handle)
        if (
            job.state not in (State.STARTING, State.DRAINING)
            or job.child is not None
            or self._remote(job) is not None
            or job.go_sent
            or job.parent_result_context is not None
            or self._disabled
        ):
            _fail()
        job.emit_revoked = True
        job.state = State.REFUSED
        job.credit_released = True
        self._retire(handle)

    def retire_epoch(self) -> None:
        self._epoch += 1
        for handle, job in list(self._jobs.items()):
            if job.state not in (State.REFUSED, State.EMIT, State.UNKNOWN):
                self.cancel(handle)

    @staticmethod
    def _wipe_remote_candidate(job) -> None:
        from .presentation_output_v2 import BoundedResultBufferV2

        # Original owned accumulator only; never invoke a drifted buffer callback.
        origin = job._remote_output_custody_snapshot
        if (type(origin) is tuple and len(origin) == 3 and origin[0] is job
                and type(origin[1]) is BoundedResultBufferV2 and type(origin[2]) is bytearray):
            origin[2][:] = b"\x00" * len(origin[2])
            origin[2].clear()
            origin[1]._done = True
        custody = job._remote_candidate_custody_snapshot
        from .presentation_result_transport import RemoteResultOwner

        if (type(custody) is tuple and len(custody) == 2 and custody[1] is job
                and type(custody[0]) is RemoteResultOwner
                and custody[0]._candidate_job_origin is job):
            RemoteResultOwner.discard(custody[0])  # original owner only, no current work permission
        if (type(custody) is tuple and len(custody) == 2 and custody[1] is job
                and type(custody[0]) is not RemoteResultOwner):
            from .presentation_credential_result_body import NativeResultBodyOwner
            if (type(custody[0]) is NativeResultBodyOwner
                    and custody[0]._candidate_job_origin is job):
                NativeResultBodyOwner.discard(custody[0])
        job.result = None
        job.remote_result_token = None

    def unknown(self, handle: JobHandle) -> None:
        job = self._resolve(handle)
        job.emit_revoked = True
        job.state = State.UNKNOWN
        if job.remote_phase is not None:
            job.remote_phase = RemotePhase.UNKNOWN
        if self._remote(job) is not None:
            JobOwner._wipe_remote_candidate(job)
        else:
            job.output_buffer.wipe()
            job.result = None
        self._disabled = True
