"""Disposable-child processing flow, not a launcher or native authority.

Only the future owned child entry may call this with its fixed scope factory.
The factory must use parent-qualified directory policy; no request selects it.
Stream calls can block, so the parent still owns hard deadline and termination.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import BinaryIO

from .presentation_files import FileOps, OwnedWorkerRead
from .presentation_jobs import FrameError
from .presentation_pipeline import encode_completed_worker, run_fixed_worker
from .presentation_worker_control import read_worker_go


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
    )
    wire = encode_completed_worker(completed, challenge=row["challenge"], epoch=row["epoch"])
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
