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
    fields = RawPresentationFields(None, None, None, None, None)
    if result.metadata is not None:
        fields = parse_presentation_yaml(result.metadata, clock=clock, deadline=deadline)
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
