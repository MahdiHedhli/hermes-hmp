"""Native fixed reader + full closed character projection; no HTTP/auth API.

Only the future actual native service may issue claims and authorize emission.
This owner retains source/result memory until explicit discard. A completed
object is not permission to emit, or proof a native thread/handler was drained.
"""

from __future__ import annotations

import json

from .presentation import HEX64, project_presentation
from .presentation_budget import PresentationWorkLedger
from .presentation_memory import PresentationMemoryBudget
from .presentation_native_claim import NativeReadClaim, NativeReadRegistry, NativeSourceError
from .presentation_native_files import NativePresentationFileReader
from .presentation_native_raster import inspect_native_avatar
from .presentation_native_yaml import NativePresentationYaml
from .presentation_yaml import RawPresentationFields
from .reads import _fallback_display_name


class NativePresentationProjection:
    def __init__(self, source, metadata, memory, leases):
        self._source, self.metadata = source, metadata
        self._memory, self._leases = memory, leases

    @property
    def avatar(self):
        return None if self._source is None else self._source.avatar

    def __repr__(self):
        return "<NativePresentationProjection private>"

    def __copy__(self):
        raise TypeError("native projection cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("native projection cannot be copied")

    def __reduce__(self):
        raise TypeError("native projection cannot be serialized")

    def discard(self):
        self.metadata = None
        if self._source is not None:
            self._source.discard()
            self._source = None
        while self._leases:
            self._memory.release(self._leases.pop())


class NativePresentationProjector:
    def __init__(self, registry: NativeReadRegistry, reader: NativePresentationFileReader):
        if (
            type(registry) is not NativeReadRegistry
            or type(reader) is not NativePresentationFileReader
            or reader._registry is not registry
        ):
            raise NativeSourceError()
        self._registry, self._reader = registry, reader
        self._yaml = NativePresentationYaml()

    def run(self, claim, work, memory, *, iid, observed_at, expected_avatar_revision=None):
        if (
            type(claim) is not NativeReadClaim
            or claim._owner is not self._registry
            or type(work) is not PresentationWorkLedger
            or type(memory) is not PresentationMemoryBudget
        ):
            raise NativeSourceError()
        profile, deadline, *_ = self._registry._check(claim)
        if work.clock is not self._registry._clock or work.deadline != deadline:
            raise NativeSourceError()
        if expected_avatar_revision is not None and (
            type(expected_avatar_revision) is not str
            or HEX64.fullmatch(expected_avatar_revision) is None
        ):
            raise NativeSourceError()
        source = result = fields = descriptor = dto = encoded = None
        leases = []
        parser_lease = None
        failed = False
        failure_reason = "native_source_unavailable"
        try:
            source = self._reader.read(claim, work, memory)
            # Conservative logical strings/slices/selected keys envelope for
            # sequential scan+event passes and reducer. Not a parser heap/RSS cap.
            parser_lease = memory.reserve(
                "yaml", 12 * (len(source.metadata or b"") + 1) + 1_048_576
            )
            fields = RawPresentationFields(None, None, None, None, None)
            if source.metadata is not None:
                fields = self._yaml.parse(source.metadata, work)
            avatar = None
            if source.avatar is not None:
                # Hash memoryviews do not copy the body. Cover bounded marker,
                # table/digest/small slice representations used by the scanner.
                leases.append(memory.reserve("raster", 65_536))
                descriptor = inspect_native_avatar(source.avatar, source.avatar_name, work)
                if (
                    expected_avatar_revision is not None
                    and descriptor.sha256 != expected_avatar_revision
                ):
                    failure_reason = "native_avatar_revision_changed"
                    raise NativeSourceError()
                avatar = {
                    "revision": descriptor.sha256,
                    "mime": descriptor.mime,
                    "bytes": descriptor.length,
                    "width": descriptor.width,
                    "height": descriptor.height,
                }
            elif expected_avatar_revision is not None:
                failure_reason = "native_avatar_revision_changed"
                raise NativeSourceError()
            self._registry._check(claim)
            work.tick()
            # Cover DTO dict/string processing and simultaneous UTF8 conversion.
            leases.append(memory.reserve("result", 4096 * 4))
            leases.append(memory.reserve("conversion", 4096))
            dto = project_presentation(
                iid=iid,
                profile=profile,
                bot_title=fields.title,
                profile_display_name=fields.display_name,
                canonical_fallback=_fallback_display_name(profile),
                shape=fields.shape,
                color=fields.color,
                custom=fields.custom,
                avatar=avatar,
                observed_at=observed_at,
            )
            encoded = json.dumps(
                dto, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
            if len(encoded) > 4096:
                raise NativeSourceError()
            self._registry._check(claim)
            work.tick()
            result = NativePresentationProjection(source, encoded, memory, leases)
            source = encoded = dto = fields = descriptor = avatar = None
            leases = []
        except BaseException:
            # Leave this exception handler before releasing payload reservations:
            # the active original exception may still retain parser/source frames.
            fields = descriptor = dto = encoded = avatar = result = None
            failed = True
        if failed:
            if source is not None:
                source.discard()
                source = None
            while leases:
                memory.release(leases.pop())
            if parser_lease is not None:
                memory.release(parser_lease)
            raise NativeSourceError(failure_reason) from None
        if parser_lease is not None:
            memory.release(parser_lease)
        return result
