"""Disposable-child processing flow, not a launcher or native authority.

Only the future owned child entry may call this with its fixed scope factory.
The factory must use parent-qualified directory policy; no request selects it.
Stream calls can block, so the parent still owns hard deadline and termination.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import BinaryIO

from .presentation_files import DirectoryRule, FileOps, OwnedWorkerRead, bind_owned_worker_read
from .presentation_input_v2 import _KEYS as _V2_KEYS
from .presentation_input_v2 import prefixes, validate_input_v2
from .presentation_input_v3 import validate_input_v3
from .presentation_jobs import FrameError
from .presentation_pipeline import encode_completed_worker, run_fixed_worker
from .presentation_worker_control import read_worker_go, read_worker_go_v2, read_worker_go_v3


def scope_from_v2(
    row: dict[str, object], *, effective_uid: int, effective_gid: int
) -> OwnedWorkerRead:
    """Reconstruct qualified policy after GO, without filesystem discovery."""
    validate_input_v2(row)
    if (
        type(effective_uid) is not int
        or type(effective_gid) is not int
        or effective_uid != row["uid"]
        or effective_gid != row["gid"]
    ):
        raise FrameError("BI1_CHILD_IDENTITY_REFUSED")
    rules = tuple(
        DirectoryRule(path, uid, gid, (mode,))
        for path, (uid, gid, mode) in zip(
            prefixes(row["home"]), row["directory_policy"], strict=True
        )
    )
    return bind_owned_worker_read(
        root_path=row["root"],
        home_path=row["home"],
        profile=None if row["profile"] == "default" else row["profile"],
        service_uid=row["uid"],
        service_gid=row["gid"],
        directory_rules=rules,
        deadline=row["deadline_ns"] / 1_000_000_000,
        challenge=row["challenge"],
        source_manifest_sha256=row["source_manifest_sha"],
        worker_go_challenge=row["challenge"],
    )


def process_child_stream_v3(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    fs: FileOps,
    clock: Callable[[], float],
    deadline: float,
    effective_uid: int,
    effective_gid: int,
) -> None:
    row = read_worker_go_v3(source, clock=clock, deadline=deadline)

    def factory(value):
        validate_input_v3(value)
        common = {key: value[key] for key in _V2_KEYS}
        common["schema"] = 2
        return scope_from_v2(common, effective_uid=effective_uid, effective_gid=effective_gid)

    _process_row(
        row,
        destination,
        scope_factory=factory,
        fs=fs,
        clock=clock,
        iid=row["iid"],
        canonical_fallback=row["canonical_fallback"],
        observed_at=row["observed_at"],
        parent_counts=row["parent_work_counts"],
        result_version=2,
    )


def process_child_stream_v2(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    fs: FileOps,
    clock: Callable[[], float],
    deadline: float,
    effective_uid: int,
    effective_gid: int,
) -> None:
    """Fixed schema2 processing path; parent still owns authority and custody."""
    row = read_worker_go_v2(source, clock=clock, deadline=deadline)
    _process_row(
        row,
        destination,
        scope_factory=lambda value: scope_from_v2(
            value, effective_uid=effective_uid, effective_gid=effective_gid
        ),
        fs=fs,
        clock=clock,
        iid=row["iid"],
        canonical_fallback=row["canonical_fallback"],
        observed_at=row["observed_at"],
    )


def process_child_stream(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    scope_factory: Callable[[dict[str, object]], OwnedWorkerRead],
    fs: FileOps,
    clock: Callable[[], float],
    deadline: float,
    iid: str,
    canonical_fallback: str,
    observed_at: int,
) -> None:
    row = read_worker_go(source, clock=clock, deadline=deadline)
    _process_row(
        row,
        destination,
        scope_factory=scope_factory,
        fs=fs,
        clock=clock,
        iid=iid,
        canonical_fallback=canonical_fallback,
        observed_at=observed_at,
    )


def _process_row(
    row: dict[str, object],
    destination: BinaryIO,
    *,
    scope_factory: Callable[[dict[str, object]], OwnedWorkerRead],
    fs: FileOps,
    clock: Callable[[], float],
    iid: str,
    canonical_fallback: str,
    observed_at: int,
    parent_counts: dict[str, int] | None = None,
    result_version: int = 1,
) -> None:
    original_deadline = row["deadline_ns"] / 1_000_000_000
    now = clock()
    if type(now) is not float or not 0 <= now < original_deadline:
        raise FrameError("BI1_CHILD_DEADLINE")
    # The factory receives its own bounded primitive copy, never the original
    # comparison/deadline/epoch source retained by this child flow.
    scope = scope_factory(copy.deepcopy(row))
    now = clock()
    if type(now) is not float or not 0 <= now < original_deadline:
        raise FrameError("BI1_CHILD_DEADLINE")
    if type(scope) is not OwnedWorkerRead or (
        scope.root_path != row["root"]
        or scope.home_path != row["home"]
        or (scope.profile or "default") != row["profile"]
        or scope.service_uid != row["uid"]
        or scope.service_gid != row["gid"]
        or scope.deadline != original_deadline
        or scope.challenge != row["challenge"]
        or scope.source_manifest_sha256 != row["source_manifest_sha"]
    ):
        raise FrameError("BI1_CHILD_SCOPE_REFUSED")
    completed = run_fixed_worker(
        scope,
        fs=fs,
        iid=iid,
        profile=row["profile"],
        canonical_fallback=canonical_fallback,
        observed_at=observed_at,
        clock=clock,
        expected_avatar_revision=row["expected_avatar_sha"],
        parent_counts=parent_counts,
    )
    wire = encode_completed_worker(
        completed, challenge=row["challenge"], epoch=row["epoch"], result_version=result_version
    )
    offset = 0
    while offset < len(wire):
        now = clock()
        if type(now) is not float or not 0 <= now < original_deadline:
            raise FrameError("BI1_CHILD_DEADLINE")
        part = wire[offset : offset + 65536]
        # A known partial count advances only that prefix. Exceptions are not
        # retried: bytes may already have reached the private result pipe.
        count = destination.write(part)
        if type(count) is not int or not 1 <= count <= len(part):
            raise FrameError("BI1_CHILD_OUTPUT_REFUSED")
        offset += count
    destination.flush()
    now = clock()
    if type(now) is not float or not 0 <= now < original_deadline:
        raise FrameError("BI1_CHILD_DEADLINE")
