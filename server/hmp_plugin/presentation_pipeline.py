"""Worker-only composition from a closed fixed read to the allowlisted DTO.

No authentication, routes, file opening or worker creation occurs here. Inputs
are local processing evidence, never native authority. Emission requires the
parent's final native reauthorization and complete child/FD cleanup proof.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .presentation import project_presentation
from .presentation_files import FixedReadResult
from .presentation_raster import RasterBudget, inspect_fixed_avatar
from .presentation_yaml import PresentationYamlError, RawPresentationFields
from .presentation_yaml_adapter import parse_presentation_yaml


@dataclass(frozen=True, repr=False)
class ProcessedPresentation:
    metadata: dict[str, object]
    avatar_bytes: bytes | None


def reduce_fixed_result(
    result: FixedReadResult,
    *,
    iid: str,
    profile: str,
    canonical_fallback: str,
    observed_at: int,
    clock: Callable[[], float],
    deadline: float,
    raster_budget: RasterBudget,
    expected_avatar_revision: str | None = None,
) -> ProcessedPresentation:
    if type(result) is not FixedReadResult or result.raster_and_yaml_unvalidated is not True:
        raise PresentationYamlError("READ_RESULT_SCHEMA")
    if (
        type(raster_budget) is not RasterBudget
        or raster_budget._deadline != deadline
        or raster_budget._clock is not clock
    ):
        raise PresentationYamlError("BUDGET_SCOPE")
    # No raw profile object can leave the worker: parse events and reduce only
    # the five frozen display fields before constructing the closed response.
    if result.work_ledger is not None and raster_budget._ledger is not result.work_ledger:
        raise PresentationYamlError("WORK_SCOPE")
    fields = RawPresentationFields(None, None, None, None, None)
    if result.metadata is not None:
        fields = parse_presentation_yaml(
            result.metadata, clock=clock, deadline=deadline, ledger=result.work_ledger
        )
    avatar = None
    if result.avatar is not None:
        if result.avatar_name is None or result.avatar_sha256 is None:
            raise PresentationYamlError("READ_RESULT_SCHEMA")
        if (
            expected_avatar_revision is not None
            and result.avatar_sha256 != expected_avatar_revision
        ):
            raise PresentationYamlError("AVATAR_CHANGED")
        suffix = {"avatar.png": "png", "avatar.jpg": "jpg", "avatar.webp": "webp"}.get(
            result.avatar_name
        )
        if suffix is None:
            raise PresentationYamlError("READ_RESULT_SCHEMA")
        descriptor = inspect_fixed_avatar(
            result.avatar, suffix, result.avatar_sha256, raster_budget
        )
        avatar = {
            "revision": descriptor.sha256,
            "mime": descriptor.mime,
            "bytes": descriptor.length,
            "width": descriptor.width,
            "height": descriptor.height,
        }
    elif expected_avatar_revision is not None:
        raise PresentationYamlError("AVATAR_CHANGED")
    now = clock()
    if type(now) is not float or not 0 <= now < deadline:
        raise PresentationYamlError("DEADLINE")
    metadata = project_presentation(
        iid=iid,
        profile=profile,
        bot_title=fields.title,
        profile_display_name=fields.display_name,
        canonical_fallback=canonical_fallback,
        shape=fields.shape,
        color=fields.color,
        custom=fields.custom,
        avatar=avatar,
        observed_at=observed_at,
    )
    now = clock()
    if type(now) is not float or not 0 <= now < deadline:
        raise PresentationYamlError("DEADLINE")
    return ProcessedPresentation(metadata, result.avatar)


@dataclass(frozen=True, repr=False)
class CompletedPresentationWork:
    result: ProcessedPresentation
    charges: dict[str, int]
    source_proof: dict[str, object]
    chain: tuple[tuple[int, ...], ...]
    absence_bitmap: int


def run_fixed_worker(
    scope,
    *,
    fs,
    iid: str,
    profile: str,
    canonical_fallback: str,
    observed_at: int,
    clock: Callable[[], float],
    expected_avatar_revision: str | None = None,
) -> CompletedPresentationWork:
    """Processing entry for the future GO-authorized disposable child only.

    The caller must establish native authority and parent/child custody first.
    A scope marker is not a grant. This function creates no process or route.
    Its sole ledger cannot be supplied/reset/replaced between phases.
    """
    from . import wire
    from .presentation_budget import PresentationWorkLedger
    from .presentation_files import OwnedWorkerRead, read_fixed_presentation_files

    wire.require_iid(iid)
    if type(scope) is not OwnedWorkerRead or profile != (scope.profile or "default"):
        raise PresentationYamlError("WORK_SCOPE")
    work = PresentationWorkLedger(clock=clock, deadline=scope.deadline)
    fixed = read_fixed_presentation_files(scope, fs=fs, clock=clock, ledger=work)
    processed = reduce_fixed_result(
        fixed,
        iid=iid,
        profile=profile,
        canonical_fallback=canonical_fallback,
        observed_at=observed_at,
        clock=clock,
        deadline=scope.deadline,
        raster_budget=RasterBudget(deadline=scope.deadline, clock=clock, ledger=work),
        expected_avatar_revision=expected_avatar_revision,
    )
    absent = 0 if fixed.metadata is not None else 1
    for bit, name in enumerate(("avatar.png", "avatar.jpg", "avatar.webp"), start=1):
        if fixed.avatar_name != name:
            absent |= 1 << bit
    proof = {
        "profile_meta": list(fixed.metadata_nine) if fixed.metadata_nine is not None else None,
        "profile_sha": fixed.metadata_sha256,
        "avatar_meta": list(fixed.avatar_nine) if fixed.avatar_nine is not None else None,
        "avatar_body_sha": fixed.avatar_sha256,
    }
    return CompletedPresentationWork(
        processed,
        work.snapshot(),
        proof,
        tuple(row for _, row in fixed.directory_nines),
        absent,
    )


def encode_completed_worker(
    work: CompletedPresentationWork, *, challenge: str, epoch: int
) -> bytes:
    """Bounded private processing frame, never an authorization receipt.

    No raw profile bytes or filesystem paths enter IPC. Parent ownership and
    original authority must still be checked before any public response.
    """
    from .presentation_jobs import encode_output

    if type(work) is not CompletedPresentationWork:
        raise PresentationYamlError("WORK_RESULT_SCHEMA")
    metadata = work.result.metadata
    fields: dict[str, object] = {}
    if metadata["name_source"] == "bot_title":
        fields["title"] = metadata["display_name"]
    elif metadata["name_source"] == "profile_display_name":
        fields["display_name"] = metadata["display_name"]
    character = metadata["character"]
    if character is not None:
        fields["custom"] = True
        if character["version"] == 1:
            fields.update(shape=character["shape"], color=character["color"], custom=True)
        else:
            custom = character["custom"]
            fields["shape"] = "blobatar:" + custom["seed"]
            if custom["kind"] is not None:
                fields["shape"] += ":" + custom["kind"]
    avatar = metadata["avatar"]
    header = {
        "schema": 1,
        "challenge": challenge,
        "epoch": epoch,
        "outcome": "OK",
        "fields": fields,
        "mime": avatar["mime"] if avatar else None,
        "width": avatar["width"] if avatar else 0,
        "height": avatar["height"] if avatar else 0,
        "avatar_sha": avatar["revision"] if avatar else None,
        "avatar_length": avatar["bytes"] if avatar else 0,
        "source_proof": work.source_proof,
        "absence_bitmap": work.absence_bitmap,
        "chain": [list(row) for row in work.chain],
        "ledger": {
            "body_bytes": work.charges["read_bytes"],
            "opens": work.charges["opens"],
            "metadata": work.charges["metadata"],
            "path_bytes": work.charges["path_bytes"],
            "raster_units": work.charges["raster_units"],
            "yaml_nodes": work.charges["yaml_nodes"],
        },
        "cleanup": {"known_fds_closed": True, "unknown_close": False},
    }
    return encode_output(header, work.result.avatar_bytes or b"")
