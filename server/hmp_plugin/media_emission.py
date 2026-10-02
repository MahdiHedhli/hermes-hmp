"""Descriptor emission for the four read routes (spec 011 S4; HMP v1 §7e LM-4, LM-5, LM-9).

One entry point, `read`, serves RO-3, RO-6, SES-2 (snapshot and paged) and SES-2a. It chooses the
read ONCE, from the owner device, the exact-true host flag and the listener's availability
snapshot. Any closed input runs the old read untouched: no media twin, no batch, no registry
call, and exactly the old response bytes.

An open listener runs the exact `Reads` media twin and, when the sidecar holds candidates, the
bridge's one `bind_media_batch`, both in the SAME `asyncio.to_thread` job (copied ContextVars, the
default executor). A failure of the twin keeps its original semantics. Any optional failure after
that (a foreign sidecar or binding, a refused batch, a gate change) keeps the successful public
text exactly and mints nothing; nothing here reruns a read.

Minting is a synchronous section on the loop with no await: owner, exact-true flag, availability
snapshot and registry identity are rechecked and then each accepted row is minted newest first,
at most 128. Authority comes from the fresh batch alone. A returned `role:"tool"`,
`tool_name:"image_generate"` message whose row id the batch accepted gets a `WireMediaDescriptor`;
nothing is parsed from text, no `MediaOrigin` is consulted, and no file, path or stat is touched.

This module imports no `local_media_*` module. It uses only the references the listener bound at
open (`ServerContext.media_snapshot`), so it never re-imports per request.
"""

from __future__ import annotations

import asyncio
import dataclasses
import re
from collections.abc import Callable
from types import FunctionType
from typing import Any, Final

from .contract import (
    MEDIA_DESCRIPTORS_PER_RESPONSE,
    ErrorCode,
    HistoryPage,
    HistoryReset,
    HmpError,
    OtherWhy,
    SessionSnapshot,
    SnapshotResponse,
    WireMediaDescriptor,
)
from .request_ctx import MediaBound, ServerContext

MEDIA_TOOL_NAME: Final = "image_generate"
MAX_DESCRIPTORS: Final = MEDIA_DESCRIPTORS_PER_RESPONSE
_REF_RE: Final = re.compile(r"[A-Za-z0-9_-]{43}")
_PUBLIC_WITH_MESSAGES: Final = (SnapshotResponse, HistoryPage, SessionSnapshot)


def _select(ctx: ServerContext, device_id: str) -> MediaBound | None:
    """The one read selection: owner device, exact-true flag, availability snapshot."""
    if not ctx.is_approval_owner_device(device_id) or not ctx.media_enabled():
        return None
    return ctx.media_snapshot()


def _function_attr(owner: object, name: str) -> Any:
    value = getattr(owner, name, None)
    return value if type(value) is FunctionType else None


async def read(
    ctx: ServerContext,
    who: Any,
    profile: str,
    name: str,
    old_call: Callable[..., Any],
    args: tuple[Any, ...],
) -> Any:
    """`old_call(*args)` or its media twin plus descriptors. `name` is the `Reads` method name;
    `args` always begins `(user_id, profile, ...)`."""
    bound = _select(ctx, who.device_id)
    reads, bridge = ctx.reads, ctx.bridge
    twin = None if reads is None else _function_attr(type(reads), f"{name}_with_media")
    if (
        bound is None
        or twin is None
        or bridge is None
        or not callable(getattr(bridge, "bind_media_batch", None))
    ):
        return await asyncio.to_thread(old_call, *args)

    def job() -> tuple[Any, Any]:
        got = twin(reads, *args)  # a text-read failure propagates with its own semantics
        try:
            return got, _bind(bound, bridge, got, who.user_id, profile)
        except Exception:  # optional: the text result stands, nothing is minted
            return got, None

    got, binding = await asyncio.to_thread(job)
    return _emit(ctx, who, profile, bound, got, binding)


def _bind(bridge_bound: MediaBound, bridge: Any, got: Any, user_id: str, profile: str) -> Any:
    """In the worker thread: one batch for a valid exact candidates sidecar, else `None`."""
    sidecar_module = bridge_bound.chain[0]
    if type(got) is not sidecar_module.MediaReadResult:
        return None
    sidecar = got.sidecar
    if type(sidecar) is not sidecar_module.MediaSidecar:
        return None
    if sidecar.status is not sidecar_module.SidecarStatus.CANDIDATES or not sidecar.candidates:
        return None
    if sidecar.user_id != user_id or sidecar.profile != profile:
        return None
    return bridge.bind_media_batch(sidecar)


def _fallback_public(got: Any) -> Any:
    """A twin result that is not the bound module's wrapper has no sidecar to trust, but its text
    may still be an exact public type; keep that (never rerun), else it is a bridge fault."""
    try:
        public = got.public
    except Exception:
        public = None
    if type(public) in (*_PUBLIC_WITH_MESSAGES, HistoryReset):
        return public
    raise HmpError(ErrorCode.OTHER, 500, why=OtherWhy.INTERNAL_ERROR.value)


def _emit(
    ctx: ServerContext, who: Any, profile: str, bound: MediaBound, got: Any, binding: Any
) -> Any:
    """Synchronous (no await). The public text, with descriptors when every check holds."""
    if type(got) is not bound.chain[0].MediaReadResult:
        return _fallback_public(got)
    public = got.public
    if binding is None or type(public) not in _PUBLIC_WITH_MESSAGES:
        return public
    try:
        minted = _mint(ctx, who, profile, bound, got, binding)
        if not minted:
            return public
        messages = tuple(
            dataclasses.replace(m, media=minted[m.id])
            if m.role == "tool" and m.tool_name == MEDIA_TOOL_NAME and m.id in minted
            else m
            for m in public.messages
        )
        return dataclasses.replace(public, messages=messages)
    except Exception:  # optional boundary: exactly the successful text
        return public


def _mint(
    ctx: ServerContext, who: Any, profile: str, bound: MediaBound, got: Any, binding: Any
) -> dict[int, WireMediaDescriptor]:
    # Gate recheck, then mint, with no await anywhere in between.
    if not ctx.is_approval_owner_device(who.device_id) or not ctx.media_enabled():
        return {}
    final = ctx.media_snapshot()
    if final is None or not final.same_as(bound):
        return {}
    sidecar_module, binding_module = bound.chain[0], bound.chain[6]
    registry_module, registry = bound.registry_module, bound.registry
    sidecar = got.sidecar
    if type(sidecar) is not sidecar_module.MediaSidecar:
        return {}
    if type(binding) is not binding_module.MediaBatchBinding:
        return {}
    if binding.sidecar is not sidecar or not binding.ok:
        return {}
    if type(binding.kind) is not binding_module.MintKind:
        return {}
    if sidecar.status is not sidecar_module.SidecarStatus.CANDIDATES:
        return {}
    if sidecar.user_id != who.user_id or sidecar.profile != profile:
        return {}
    tip, session_id = binding.tip, binding.session_id
    if type(tip) is not str or type(session_id) is not str or not sidecar.provenance_consistent:
        return {}
    kind = registry_module.SessionKind(binding.kind.value)
    accepted = binding.accepted
    if type(accepted) is not tuple or len(accepted) > MAX_DESCRIPTORS:
        return {}
    digests = {c.tool_row_id: c.raw_digest for c in sidecar.candidates}
    returned: dict[int, int] = {}
    for m in got.public.messages:
        if m.role == "tool" and m.tool_name == MEDIA_TOOL_NAME:
            returned[m.id] = returned.get(m.id, 0) + 1
    make = registry_module.Binding
    minted: dict[int, WireMediaDescriptor] = {}
    for row_id in sorted(accepted, reverse=True)[:MAX_DESCRIPTORS]:
        digest = digests.get(row_id)
        if returned.get(row_id) != 1 or digest is None:
            continue
        ref = _mint_one(
            registry,
            lambda row_id=row_id, digest=digest: make(
                device_id=who.device_id,
                user_id=who.user_id,
                instance_id=ctx.iid,
                profile=profile,
                kind=kind,
                session_id=session_id,
                tip=tip,
                tool_row_id=row_id,
                raw_digest=digest,
            ),
        )
        if ref is not None:
            minted[row_id] = WireMediaDescriptor(kind="image", ref=ref)
    return minted


def _mint_one(registry: Any, build: Callable[[], Any]) -> str | None:
    """One candidate's ref, or `None`: a failed candidate mints none for itself and no other."""
    try:
        ref = registry.mint(build())
    except Exception:
        return None
    return ref if type(ref) is str and _REF_RE.fullmatch(ref) else None
