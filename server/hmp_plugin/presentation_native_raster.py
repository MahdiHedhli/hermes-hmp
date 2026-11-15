"""One native-source hash/structure pass; not a decoder or authority receipt."""

from __future__ import annotations

import hashlib

from .presentation_budget import PresentationWorkLedger
from .presentation_native_claim import NativeSourceError
from .presentation_raster import AvatarDescriptor, RasterBudget, _check_raster_structure

_MIME = {
    "avatar.png": ("png", "image/png"),
    "avatar.jpg": ("jpeg", "image/jpeg"),
    "avatar.webp": ("webp", "image/webp"),
}


def inspect_native_avatar(data: bytes, name: str, work: PresentationWorkLedger):
    if (
        type(data) is not bytes
        or not 1 <= len(data) <= 2_000_000
        or type(name) is not str
        or name not in _MIME
        or type(work) is not PresentationWorkLedger
    ):
        raise NativeSourceError()
    budget = RasterBudget(work.deadline, work.clock, work)
    budget.begin()
    digest = hashlib.sha256()
    view = memoryview(data)
    try:
        for offset in range(0, len(data), 65_536):
            part = view[offset : min(offset + 65_536, len(data))]
            try:
                budget.hash_slice(len(part))
                digest.update(part)
            finally:
                part.release()
        structure = _check_raster_structure(data, budget)
        kind, mime = _MIME[name]
        if structure.kind != kind or structure.decodability != "unvalidated":
            raise NativeSourceError()
        budget.tick()
        return AvatarDescriptor(
            mime, structure.width, structure.height, digest.hexdigest(), len(data)
        )
    finally:
        view.release()
