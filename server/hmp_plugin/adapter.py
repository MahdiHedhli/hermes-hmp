"""`HmpAdapter(BasePlatformAdapter)`: listener lifecycle only. T024.

The adapter starts and stops the HMP listener (`server.py`). It relays nothing to or from
conversations: F1 registers no write route (FR-053), so it never calls `handle_message`, and
`send` drops whatever Hermes hands it (in F1 that is only Hermes's reply to the inert P6
authorization trigger, whose pairing code is never relayed, PR6-2) without logging any of it
(SR-007, CS-22).

`connect` follows server-modules.md "Startup order": the compat gate runs first, from file reads
only; `bridge.py` is imported only when the build is SUPPORTED. Then the store opens, the instance
identity loads (ID-2; it may revoke every device on a clone, backup or host change), and the TLS
listener starts. On an unsupported build the listener still starts and serves `/ready`, and every
other path answers ERR-2a (FR-044a).

PR7-6: when the listener sees the key change (a request or the watchdog), it closes and stays
closed; the adapter reports a non-retryable fatal state until the gateway restarts under the new
key.

The adapter runs on every Hermes build, including unsupported ones, where it serves `/ready` and
the ERR-2a refusals. It therefore cannot reach Hermes through `bridge.py`. Its Hermes imports are
the closed, controller-approved exception for the documented platform-plugin API, and nothing more:
`gateway.platforms.base.{BasePlatformAdapter, SendResult}` and `gateway.config.Platform`
(`tools/ci/check_plugin_surface.py`).

Live-bug fix note (plugin-reload hazard; see `request_ctx.py`'s docstring for the mechanism):
`authorize.py` and `reads.py` are imported at THIS module's top level, not inside
`open_components()`, so `Authorize` and `Reads` are bound once, at this load's own import time,
and stay bound to this load's `contract.HmpError` (the class `server.py`'s `error_middleware`
checks `except HmpError` against) no matter what a later plugin reload does to `sys.modules`.
Neither module imports a Hermes internal at its own top level (only `.contract` and
`.logging_policy`), so this adds no new import-surface exposure on an unsupported build.

`bridge.py` cannot follow: S3 (`tools/ci/check_plugin_surface.py`) requires it be imported only
inside a function, never at module level, and only after the compat gate reports SUPPORTED. It
stays a lazy import inside `_bridge_classes()` below, but that function caches the classes at
module level after the first supported call in this load, so a later reload's eviction of
`hermes_plugins.hmp.bridge` cannot hand a *second* supported call in this same load a different
`HermesReadBridge`/`StoreDirectory` pair than the first. (`bridge.py` itself does not raise
`HmpError` -- every bridge call `authorize.py`/`reads.py` makes is wrapped in a generic
`except Exception`, and re-raised as THEIR OWN, now load-stable, `HmpError` -- so this residual
gap in `bridge.py`'s own class identity does not reopen the error-shaping hazard the top-level
`authorize`/`reads` imports close.) The same cache also holds the actual `bridge` module object.

Local media (specs/011-local-image-serving, M3). Availability is the `local_media` eligibility
member (minimum version plus the three native probe rows) AND an in-memory media-chain coherence
check, both decided once when the listener opens; `_media_bind` below never touches a file, a build
list, a manifest, a fingerprint, a Git SHA or any process-wide state, and it binds the verified
module objects to this one listener. The retired exact-build qualification (S6/S6a/S6b) is gone.
S4 (source candidate): the four read routes consume `ServerContext.media_snapshot()` through
`media_emission`. `_media_registry_bind` makes the listener's one registry and binds its actual
module at open; the availability closure fences the exact bound tuple, that module and that
instance by identity. The adapter's only media imports are `local_media_registry` (there) and
`local_media_raster_structure` (in `_media_raster_bind`), each function-local.
S5 (source candidate): `_media_raster_bind` and `_media_fetch_bind` also bind the actual raster
module, the shared payload-carrier module and the route orchestrator module at open, so the fetch
route runs the same objects mint did; the availability closure fences and clears them with the rest.
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any

from gateway.config import Platform
from gateway.platforms.base import BasePlatformAdapter, SendResult

from . import cli, compat, direct_send, identity, prompts, reads, server
from .authorize import Authorize
from .cli import listener_record_path
from .contract import PLATFORM_NAME, OtherWhy, WriteGateState
from .logging_policy import log_event
from .reads import Reads, _fallback_display_name
from .store import Store

IDENTITY_CHANGED_CODE = "hmp_identity_changed"
IDENTITY_CHANGED_MESSAGE = "HMP instance key changed; restart the gateway to serve the new key"


def _readiness_owner_device_ids_from_adapter(adapter: Any) -> frozenset[str]:
    """Strict, readiness-only projection of the loaded legacy adapter controls."""
    live_config = getattr(adapter, "config", None)
    if live_config is None:
        raise ValueError("readiness config unavailable")
    live_extra = getattr(live_config, "extra", None)
    if not isinstance(live_extra, Mapping):
        raise ValueError("readiness config malformed")
    if "owner_device_ids" not in live_extra:
        return frozenset()
    ids = live_extra["owner_device_ids"]
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError("readiness controls malformed")
    return frozenset(ids)


def _readiness_settings_from_adapter(adapter: Any) -> object:
    """Return only the loaded adapter's settings mapping for the readiness projection."""
    live_config = getattr(adapter, "config", None)
    if live_config is None:
        raise ValueError("readiness config unavailable")
    live_extra = getattr(live_config, "extra", None)
    if not isinstance(live_extra, Mapping):
        raise ValueError("readiness config malformed")
    return live_extra


# Live-bug fix (multiplexed gateway, 2026-09-27): the multiplexer brings secondary profiles online
# strictly after this adapter's own `connect()` (`gateway/run_profile_reconcile.py`'s
# `served_profile_names()` is live bookkeeping, refreshed only as profiles are hot-added/removed),
# so a listener record written once at connect can go stale -- `pair offer`'s OD-F8 grant step
# would then only ever offer whatever was served at that instant. These two constants drive the
# adapter's own periodic safety-net refresh (`_periodic_profile_refresh`); `Reads.roster` and
# `Authorize.authorize` additionally refresh opportunistically on every successful call, for free,
# well before the first tick. Module-level so a test can monkeypatch them to run fast.
PROFILE_REFRESH_INITIAL_DELAY_S = 5.0
PROFILE_REFRESH_INTERVAL_S = 15.0

# One published tuple: `(bridge module, HermesReadBridge, StoreDirectory)`, all read from the one
# module object imported. Set once under the lock with a single assignment.
_bridge_cache: tuple[ModuleType, type[Any], type[Any]] | None = None
_bridge_lock = threading.Lock()


def _bridge_published() -> tuple[ModuleType, type[Any], type[Any]]:
    """`(bridge module, HermesReadBridge, StoreDirectory)`, imported from `bridge.py` at most once
    per load of this package. S3 forbids importing `bridge` at module level, so this import cannot
    move to the top of this file the way `authorize`/`reads` did above; caching it here instead
    means only the FIRST supported `open_components()` call in this load ever wins the publication,
    so a reload that happens between that call and a later one (another profile's load, on a
    multiplexed gateway) cannot swap the class a running listener's `ctx.bridge` is built from.

    The import runs outside the lock (an import lock may be held elsewhere). Only the one tuple
    assignment is locked, so concurrent first calls all return the winner's tuple and the module
    and its classes can never come from two different copies."""
    global _bridge_cache
    cached = _bridge_cache
    if cached is None:
        from . import bridge as bridge_module

        fresh = (bridge_module, bridge_module.HermesReadBridge, bridge_module.StoreDirectory)
        with _bridge_lock:
            if _bridge_cache is None:
                _bridge_cache = fresh
            cached = _bridge_cache
    return cached


def _bridge_classes() -> tuple[type[Any], type[Any]]:
    """`(HermesReadBridge, StoreDirectory)` from the one published tuple."""
    _, bridge_cls, directory_cls = _bridge_published()
    return bridge_cls, directory_cls


def _log_unavailable_features(eligibility: compat.Eligibility | None) -> None:
    """One event per feature this Hermes cannot serve for a reason other than its declared
    version. Only fixed enum strings are ever logged."""
    if eligibility is None:
        return
    for feature, status in eligibility.unavailable():
        if status.reason is not compat.Unavailable.VERSION_BELOW_FLOOR:
            log_event("hermes_feature_unavailable", outcome=feature.value)


# --------------------------------------------------------------------------------------------------
# Local-media availability binding (D-M4). Proofs are identity comparisons, never lookups.
# --------------------------------------------------------------------------------------------------

_MEDIA_UNWRAP_LIMIT = 8


class _MediaSplitError(Exception):
    """A required module is not the one this load's listener runs. Closes media; carries nothing."""


def _media_require(ok: bool) -> None:
    if not ok:
        raise _MediaSplitError


def _media_function(value: object) -> FunctionType | None:
    """The exact plain function `value` is, following a `__wrapped__` chain of at most eight steps;
    `None` for anything else (a partial, a builtin, a callable object)."""
    for _ in range(_MEDIA_UNWRAP_LIMIT + 1):
        if type(value) is not FunctionType:
            return None
        wrapped = value.__dict__.get("__wrapped__")
        if wrapped is None:
            return value
        value = wrapped
    raise _MediaSplitError


def _media_prove_function(value: object, module: ModuleType) -> None:
    """P-fn: the function's executing namespace IS `module`."""
    function = _media_function(value)
    _media_require(function is not None and function.__globals__ is vars(module))


def _media_prove_chain(
    bridge_module: ModuleType, reads_module: ModuleType
) -> tuple[tuple[ModuleType, ...], tuple[ModuleType, ...]]:
    """The media chain, from the caches the media sites themselves read. Returns the actual cache
    objects `(bridge cache, reads cache)` after proving their cross-references. A call fills a
    cache that is still empty (an import outside the publication lock); it reads no file of its
    own and attests nothing about loaded bytes."""
    chain = vars(bridge_module)["_local_media_modules"]()
    reads_media = vars(reads_module)["_local_media_modules"]()
    _media_require(type(chain) is tuple and len(chain) == 7)
    _media_require(type(reads_media) is tuple and len(reads_media) == 1)
    _media_require(all(type(member) is ModuleType for member in (*chain, *reads_media)))
    sidecar, candidate, active_scan, result, file_safety, active_batch, binding = chain
    _media_require(reads_media[0] is sidecar)
    _media_require(vars(candidate)["_scan"] is active_scan)  # P-ref
    _media_require(vars(result)["_scan"] is active_scan)
    _media_require(vars(active_batch)["_scan"] is active_scan)
    _media_require(vars(active_batch)["_candidate"] is candidate)
    _media_require(vars(binding)["_batch"] is active_batch)
    _media_require(vars(binding)["_sidecar"] is sidecar)
    _media_prove_function(vars(candidate)["collect_candidates"], candidate)
    _media_prove_function(vars(candidate)["classify_candidate"], file_safety)
    _media_prove_function(vars(candidate)["parse_image_result"], result)
    _media_prove_function(vars(active_batch)["scan_active_batch"], active_batch)
    _media_prove_function(vars(binding)["classify"], binding)
    _media_prove_function(vars(sidecar)["_text"], sidecar)
    return chain, reads_media


def _media_registry_bind() -> tuple[ModuleType, Any]:
    """S4: this listener's one registry and the actual module it comes from, both made here, once,
    at listener open, and never re-imported per request. The constructor and the public
    mint/lookup/record_first_served functions must execute in that module's own namespace, and
    the instance must be that module's exact class. It is independent of the seven-member bridge
    chain. A mismatch raises `_MediaSplitError`, which `_media_bind` turns into this listener's
    closed media. It imports no other media module and reads no file."""
    from . import local_media_registry

    module = local_media_registry
    cls = vars(module)["LocalMediaRegistry"]
    _media_require(type(cls) is type and cls.__module__ == module.__name__)
    for name in ("__init__", "mint", "lookup", "record_first_served"):
        _media_prove_function(vars(cls)[name], module)
    registry = cls()
    _media_require(type(registry) is cls)
    return module, registry


def _media_raster_bind() -> ModuleType:
    """S5: the actual raster-structure module phase one runs, bound once at listener open. The
    entry function and every helper it dispatches to must execute in that module's own namespace.
    It reads no file and touches no image; the only media import here is function-local."""
    from . import local_media_raster_structure

    module = local_media_raster_structure
    _media_require(type(module) is ModuleType)
    space = vars(module)
    # The entry, its three format checkers and every helper they reach, by name ...
    for name in (
        "check_raster_structure",
        "_check_png",
        "_check_png_ancillary",
        "_check_jpeg",
        "_jpeg_sof",
        "_jpeg_dqt",
        "_jpeg_dht",
        "_jpeg_scan",
        "_check_webp",
        "_webp_vp8",
        "_webp_vp8l",
        "_webp_alph",
        "_webp_vp8x",
        "_webp_extended_chunk",
        "_check_dims",
        "_refuse",
        "_bad",
    ):
        _media_prove_function(space[name], module)
    # ... then every other function this module itself defines, so a helper added later (or one
    # a name list missed) cannot run in a second namespace; imported functions are not its own.
    for value in tuple(space.values()):
        if type(value) is FunctionType and value.__module__ == module.__name__:
            _media_prove_function(value, module)
    # The closed refusal's constructor runs on every refusal path.
    refusal = space["RasterRefused"]
    _media_require(type(refusal) is type and refusal.__module__ == module.__name__)
    _media_prove_function(vars(refusal)["__init__"], module)
    return module


def _media_fetch_bind(bridge_module: ModuleType) -> tuple[ModuleType, ModuleType]:
    """S5: `(payload carrier module, route orchestrator module)`, proven to be the very objects the
    bridge's phase functions and the route run: the bridge and the orchestrator hold ONE payload
    module (no split carrier class), and the phase, carrier, service and handler functions execute
    in their own modules' namespaces. Imports nothing and reads no file; `server.py` already holds
    the orchestrator at module level, so this load's copy is the one it routes through."""
    fetch = vars(server).get("media_fetch")
    payload = vars(bridge_module).get("media_payload")
    _media_require(type(fetch) is ModuleType and type(payload) is ModuleType)
    _media_require(vars(fetch).get("media_payload") is payload)
    carrier = vars(payload).get("MediaPayload")
    _media_require(type(carrier) is type and carrier.__module__ == payload.__name__)
    for name in ("data", "mime", "sha256", "size"):
        member = vars(carrier)[name]
        _media_require(type(member) is property)
        _media_prove_function(member.fget, payload)
    bridge_cls = vars(bridge_module)["HermesReadBridge"]
    for name in ("media_fetch_phase_one", "media_fetch_phase_two", "_media_fetch_bound"):
        _media_prove_function(vars(bridge_cls)[name], bridge_module)
    service = vars(fetch).get("MediaFetchService")
    lease = vars(fetch).get("_Lease")
    # Every method/accessor of the new private classes runs in the same module as its class.
    # Include refusal constructors and carrier lifetime/serialization guards, not just entry points.
    for module, cls in (
        (payload, carrier),
        (payload, vars(payload)["MediaPayloadRefusal"]),
        (fetch, service),
        (fetch, lease),
        (fetch, vars(fetch)["MediaServiceRefusal"]),
    ):
        _media_require(type(cls) is type and cls.__module__ == module.__name__)
        for member in tuple(vars(cls).values()):
            if type(member) in (classmethod, staticmethod):
                _media_prove_function(member.__func__, module)
            elif type(member) is FunctionType:
                _media_prove_function(member, module)
            elif type(member) is property:
                for accessor in (member.fget, member.fset, member.fdel):
                    if accessor is not None:
                        _media_prove_function(accessor, module)
    for name in ("__init__", "close", "lease", "stats"):
        _media_prove_function(vars(service)[name], fetch)
    for name in ("start", "take", "finish", "_publish", "_done", "_release_if_ready"):
        _media_prove_function(vars(lease)[name], fetch)
    closed = vars(service)["closed"]
    _media_require(type(closed) is property)
    _media_prove_function(closed.fget, fetch)
    for name in (
        "serve", "_final_section", "_stream", "_wait", "_service_ok", "_runner",
        "_abort", "_shaped_badly", "_not_started", "_not_found", "close_service",
    ):
        _media_prove_function(vars(fetch).get(name), fetch)
    for value in tuple(vars(fetch).values()):
        if type(value) is FunctionType and value.__module__ == fetch.__name__:
            _media_prove_function(value, fetch)
    _media_prove_function(vars(server).get("handle_media_fetch"), server)
    _media_prove_function(vars(server).get("build_app"), server)
    return payload, fetch


def _media_closed() -> bool:
    return False


def _media_bind(
    ctx: Any, bridge_module: ModuleType, reads_module: ModuleType
) -> Callable[[], bool]:
    """Bind local-media availability to ONE listener. Call only when this listener's `local_media`
    eligibility member is available. The media-chain cross-references are verified once; on success
    the verified `(bridge cache, reads cache)` tuples are stored on `ctx.media_modules`, this
    listener's own registry and its actual module on `ctx.media_registry` and
    `ctx.media_registry_module`, and the returned callback is the listener's `media_available`. On
    any failure (`Exception`) this listener's media stays closed and nothing process-wide changes,
    so another listener in the same process opens independently. `BaseException` propagates to the
    caller.

    The callback is the cheap use-time fence: no await, import, file or lock. It compares the
    caches the bridge and reads modules hold NOW with the bound tuples by identity, and on a
    mismatch closes this listener's media until the next open. It is not authenticity, a
    loaded-bytecode proof or an attestation, and it never looks at `sys.modules`: whole-package
    eviction replaces module-table entries but leaves these references and caches alone."""
    try:
        # The bound modules are the ones this listener's own bridge and reads objects come from.
        _media_require(type(ctx.bridge) is vars(bridge_module).get("HermesReadBridge"))
        _media_require(type(ctx.reads) is vars(reads_module).get("Reads"))
        chain, reads_media = _media_prove_chain(bridge_module, reads_module)
        registry_module, registry = _media_registry_bind()
        raster_module = _media_raster_bind()
        payload_module, fetch_module = _media_fetch_bind(bridge_module)
    except Exception:
        log_event("local_media_binding", outcome="media_binding_incoherent")
        return _media_closed
    # The exact outer tuple is retained: the fence compares `ctx.media_modules` against it by
    # identity, not only the two caches inside it.
    bound = (chain, reads_media)
    ctx.media_modules = bound
    ctx.media_registry_module = registry_module
    ctx.media_registry = registry
    ctx.media_raster_module = raster_module
    ctx.media_payload_module = payload_module
    ctx.media_fetch_module = fetch_module
    closed = [False]

    def media_available() -> bool:
        if closed[0]:
            return False
        try:
            same = (
                vars(bridge_module)["_local_media_cache"] is chain
                and vars(reads_module)["_local_media_cache"] is reads_media
                and ctx.media_modules is bound
                and ctx.media_registry_module is registry_module
                and ctx.media_registry is registry
            )
            # S5: the three further bound modules, a separate expression so the S4 fence above is
            # byte-for-byte what was reviewed.
            same = same and (
                ctx.media_raster_module is raster_module
                and ctx.media_payload_module is payload_module
                and ctx.media_fetch_module is fetch_module
            )
        except Exception:  # fail closed; the exception text is never logged
            same = False
        if same:
            return True
        closed[0] = True
        ctx.media_modules = None  # a closed listener hands no bound reference to a later caller
        ctx.media_registry_module = None
        ctx.media_registry = None
        ctx.media_raster_module = None
        ctx.media_payload_module = None
        ctx.media_fetch_module = None
        log_event("local_media_binding", outcome="media_binding_changed")
        return False

    return media_available


def open_components(adapter: Any) -> server.ServerContext:
    """Compat gate, store, identity and (on a supported build only) the bridge. Blocking."""
    try:
        result = compat.default_gate().evaluate()
    except Exception:  # the gate fails closed on its own; this guards its loader
        result = compat.CompatResult(
            compat.CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED
        )
    custody = identity.resolve_custody()
    store = Store(server.store_path(custody.anchor_dir))
    store.migrate()
    try:
        ident = identity.load_or_create(store)
    except BaseException:
        store.close()
        raise
    config = getattr(adapter, "config", None)
    extra = getattr(config, "extra", None)
    session_browsing = extra.get("session_browsing", True) if isinstance(extra, Mapping) else True
    eligibility = result.eligibility
    # Availability comes from the one eligibility evaluation done above (Hermes code cannot change
    # without a gateway restart), never from a per-request lookup. A result that carries no
    # eligibility (an injected test double) reports nothing beyond read as available.
    def _available(feature: compat.Feature) -> bool:
        return eligibility is not None and eligibility.available(feature)

    send_available = result.supported and _available(compat.Feature.SEND)
    # Spec 034: the `approvals` and `phone_chat` members, decided once here from the same
    # eligibility evaluation (no per-request lookup). No build list, fingerprint or latch is read.
    approvals_member = result.supported and _available(compat.Feature.APPROVALS)
    phone_member = result.supported and _available(compat.Feature.PHONE_CHAT)
    # Set only after the bridge captured the Phone-chat helpers (AP-10); closed until then.
    phone_bound = [False]

    # Amendment F2 (direct send, OD-F14/OD-F15): `gateway.platforms.hmp.extra.direct_send.enabled`,
    # default False. A malformed (non-mapping) `direct_send` block fails closed to disabled, never
    # to enabled -- mirrors `session_browsing`'s own "anything but an explicit False is on" only
    # in the safe direction (this flag's own safe default is OFF, not ON).
    #
    # Review round 2, should-fix: a closure over `adapter`, not a one-time bool, so every request
    # re-reads the LIVE `adapter.config.extra` (`server.py`'s `handle_chat_send` calls this once
    # per request via `ServerContext.direct_send_enabled()`) -- a host-side flag flip is visible
    # on the next request, not the next gateway restart. Cheap: an in-memory dict lookup, no I/O.
    def _read_direct_send_enabled() -> bool:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        block = live_extra.get("direct_send") if isinstance(live_extra, Mapping) else None
        return isinstance(block, Mapping) and block.get("enabled") is True

    def _read_owner_device_ids() -> frozenset[str]:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        ids = live_extra.get("owner_device_ids") if isinstance(live_extra, Mapping) else None
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            return frozenset()
        return frozenset(ids)

    def _readiness_owner_device_ids() -> frozenset[str]:
        return _readiness_owner_device_ids_from_adapter(adapter)

    def _readiness_settings() -> object:
        return _readiness_settings_from_adapter(adapter)

    def _read_cron_enabled() -> bool:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        block = live_extra.get("cron") if isinstance(live_extra, Mapping) else None
        return isinstance(block, Mapping) and block.get("enabled") is True

    def _read_local_media_enabled() -> bool:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        block = live_extra.get("local_media") if isinstance(live_extra, Mapping) else None
        return isinstance(block, Mapping) and block.get("enabled") is True

    def _read_model_enabled() -> bool:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        block = live_extra.get("model_management") if isinstance(live_extra, Mapping) else None
        return isinstance(block, Mapping) and block.get("enabled") is True

    ctx = server.ServerContext(
        identity=ident,
        store=store,
        compat=result,
        session_browsing_enabled=session_browsing is not False,
        direct_send_flag=_read_direct_send_enabled,
        owner_device_ids=_read_owner_device_ids,
        readiness_owner_device_ids=_readiness_owner_device_ids,
        readiness_settings=_readiness_settings,
        approvals_available=lambda: approvals_member,
        phone_chat_available=lambda: phone_member and phone_bound[0],
        cron_flag=_read_cron_enabled,
        cron_available=lambda: result.supported and _available(compat.Feature.JOBS),
        model_flag=_read_model_enabled,
        model_available=lambda: result.supported and _available(compat.Feature.MODEL),
        session_browsing_available=_available(compat.Feature.SESSION_BROWSING),
        send_available=lambda: send_available,
        media_flag=_read_local_media_enabled,
    )
    _log_unavailable_features(eligibility)
    if result.supported:
        bridge_module, bridge_cls, directory_cls = _bridge_published()

        ctx.bridge = bridge_cls(adapter, directory_cls(store))
        # Live-bug fix: `adapter._observe_served_profiles` is a bound method of the adapter this
        # context belongs to (this function's own `adapter` argument), so it is safe to close over
        # here even though `self._record`/`self._nonce` are not set until `connect()` finishes
        # further down -- neither `Reads.roster` nor `Authorize.authorize` can run before then.
        on_served_profiles = getattr(adapter, "_observe_served_profiles", None)
        prompt_store = prompts.PromptStore(clock=ctx.now)
        ctx.prompt_store = prompt_store
        ctx.reads = Reads(
            ctx.bridge,
            store,
            iid=ident.iid,
            guarantees=ctx.guarantees,
            write_gate=ctx.reported_write_gate,
            send_gate=ctx.reported_send_gate,
            clock=ctx.now,
            on_served_profiles=on_served_profiles,
            prompt_store=prompt_store,
        )
        ctx.authorize = Authorize(
            ctx.bridge, store, clock=ctx.now, on_served_profiles=on_served_profiles
        )
        # Amendment F2: constructed on every supported build, regardless of `direct_send_enabled`
        # -- the flag is re-checked per request (DS-2(b)), not at listener-start time, so a
        # host-side flag flip takes effect on the next request, not the next restart.
        def _approval_timeout(profile: str) -> int:
            bridge = ctx.bridge
            if bridge is None:
                return 300
            return bridge.approval_timeout_s(profile)  # type: ignore[no-any-return]

        ctx.direct_send_deps = direct_send.DirectSendDeps(
            bridge=ctx.bridge,
            store=store,
            locks=direct_send.ProfileLocks(),
            now=ctx.now,
            prompt_store=prompt_store,
            approval_timeout=_approval_timeout,
        )
        if phone_member:
            # AP-10: capture the Phone-chat helpers now, after the probe passed. A later rebinding
            # closes this generation's Phone-chat side; Bot Chat `approvals` is independent.
            phone_bound[0] = ctx.bridge.bind_phone_chat_helpers(  # type: ignore[attr-defined]
                lambda: prompt_store.close_phone_chat(ctx.now())
            )
        # Local media (M3): only a listener whose `local_media` member is available is bound; the
        # result identity may be `None`. Closed (the default) otherwise, with no media import.
        if _available(compat.Feature.LOCAL_MEDIA):
            try:
                ctx.media_available = _media_bind(ctx, bridge_module, reads)
            except BaseException:
                store.close()
                raise
        adapter._hmp_hooks = prompts.AdapterHooks(  # type: ignore[attr-defined]
            store=prompt_store,
            bridge=ctx.bridge,
            now=ctx.now,
            iid=ident.iid,
            phone_available=ctx.is_phone_chat_available,
        )
    log_event("adapter_open", outcome=result.status.value)
    return ctx


class HmpAdapter(BasePlatformAdapter):
    def __init__(self, config: Any) -> None:
        super().__init__(config=config, platform=Platform(PLATFORM_NAME))
        self._server: server.HmpServer | None = None
        self._record: Path | None = None
        # Live-bug fix: the nonce this incarnation's record was written with (SR-7 -- a fresh
        # value per listener START, not per record write) and the last `profiles` this adapter
        # itself wrote, kept only to make a refresh's cheap comparison possible. Both `None` until
        # `connect()` sets them, and both cleared whenever the record itself goes away.
        self._nonce: str | None = None
        self._known_profiles: tuple[tuple[str, str], ...] | None = None
        self._profile_refresh_task: asyncio.Task[None] | None = None
        self._record_lock = threading.Lock()

    @staticmethod
    def _health_snapshot(
        ctx: server.ServerContext, profiles: Sequence[tuple[str, str]]
    ) -> tuple[tuple[str, str, str, str], ...]:
        """Only fixed status codes leave the runtime; credentials and endpoints stay in memory."""
        rows: list[tuple[str, str, str, str]] = []
        for profile, _display in profiles:
            try:
                send = (
                    "disabled" if not ctx.direct_send_enabled()
                    else "unsupported" if not ctx.is_send_available()
                    else "ready"
                    if ctx.reported_send_gate(profile).state is not WriteGateState.CLOSED
                    else "unavailable"
                )
                cron = (
                    "disabled" if not ctx.cron_enabled()
                    else "unsupported" if not ctx.is_cron_available()
                    else "unavailable"
                )
                model = (
                    "disabled" if not ctx.model_enabled()
                    else "unsupported" if not ctx.is_model_available()
                    else "unavailable"
                )
                if cron == "unavailable" or model == "unavailable":
                    endpoint = ctx.bridge.direct_send_endpoint(profile) if ctx.bridge else None
                    if endpoint is not None:
                        if cron == "unavailable":
                            cron = "ready"
                        if model == "unavailable":
                            model = "ready"
            except Exception:
                # A failed live lookup must never become a passing snapshot or leak exception text.
                send = "unavailable" if ctx.direct_send_enabled() else "disabled"
                cron = "unavailable" if ctx.cron_enabled() else "disabled"
                model = "unavailable" if ctx.model_enabled() else "disabled"
            rows.append((profile, send, cron, model))
        return tuple(rows)

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        """Run the compat gate, then start the TLS listener (server-modules.md "Startup order")."""
        if self._server is not None:
            return True
        try:
            settings = server.listener_settings(getattr(self.config, "extra", None))
        except server.ListenerConfigError:
            log_event("adapter_connect", outcome="bad_config")
            return False
        try:
            ctx = await asyncio.to_thread(open_components, self)
        except identity.IdentityError:
            log_event("adapter_connect", outcome="identity_error")
            return False
        srv = server.HmpServer(ctx, settings, on_closed=self._listener_closed)
        try:
            await srv.start()
        except Exception as exc:
            self._close_generation(ctx)
            ctx.store.close()
            log_event("adapter_connect", outcome="listener_failed")
            raise ConnectionError("HMP listener did not start") from exc
        self._server = srv
        anchor = ctx.identity.custody.anchor_dir  # type: ignore[attr-defined]
        self._record = listener_record_path(anchor)
        # SR-7: one nonce for this listener incarnation, generated once here and reused by every
        # later rewrite of the same record (`_sync_refresh`) -- a refresh is not a new listener
        # start, and `remove_listener_record`'s race-safety does not key off this value anyway
        # (it compares the file's own pid and inode), but reusing it keeps the record's nonce
        # semantics exactly what they were before this field could change out from under a reader
        # mid-incarnation.
        self._nonce = secrets.token_hex(16)
        if srv.bound is not None:
            # OD-F8 (2026-09-27): the served profiles, so `pair offer`'s one-command flow can
            # list bots by name without importing Hermes (S1). Best-effort only -- the bridge is
            # None on an unsupported build, and any bridge failure here must never abort listener
            # startup; `pair offer` falls back to its generic placeholder text when this is
            # missing (`cli._served_bots`).
            profiles: list[tuple[str, str]] | None = None
            if ctx.bridge is not None:
                try:
                    profiles = [
                        (p, _fallback_display_name(p)) for p in ctx.bridge.served_profiles()
                    ]
                except Exception:
                    log_event("listener_record_profiles", outcome="failed")
                    profiles = None
            try:  # PR1-4: `hmp pair offer` derives `ep` from this record only
                health = self._health_snapshot(ctx, profiles) if profiles is not None else None
                cli.write_listener_record(
                    self._record,
                    host=srv.bound[0],
                    port=srv.bound[1],
                    iid=ctx.iid,
                    nonce=self._nonce,
                    profiles=profiles,
                    health_checked_at=int(time.time()) if health is not None else None,
                    health=health,
                )
            except OSError:
                log_event("listener_record", outcome="write_failed")
            else:
                self._known_profiles = tuple(profiles) if profiles is not None else None
            if ctx.bridge is not None:
                # Live-bug fix: the multiplexer brings secondary profiles online strictly AFTER
                # this `connect()` returns, so the record just written above can already be stale
                # by the time anyone reads it. `Reads.roster`/`Authorize.authorize` refresh it
                # opportunistically on every successful call; this task is the safety net for an
                # instance nobody has queried yet (`pair offer` reads the record directly, never
                # through a roster/authorize call).
                self._profile_refresh_task = asyncio.get_running_loop().create_task(
                    self._periodic_profile_refresh()
                )
        self._mark_connected()
        return True

    # ------------------------------------------------------------------------------------------
    # Live-bug fix: keep the listener record's `profiles` current while the listener runs.
    # ------------------------------------------------------------------------------------------

    @staticmethod
    def _profile_names_key(profiles: Sequence[tuple[str, str]] | None) -> tuple[str, ...]:
        """The comparison key `_sync_refresh` rewrites on a change of: profile NAMES only, order
        independent -- `_fallback_display_name` is a pure function of the profile name, so it can
        never itself change what this key sees as "the same served set"."""
        return tuple(sorted(name for name, _display in profiles or ()))

    def _sync_refresh(self, served: Iterable[str], *, refresh_health: bool = False) -> None:
        """The one place that compares and, on a change, rewrites the record. Synchronous and
        blocking (file I/O) by design: `Reads.roster`/`Authorize.authorize` already call this from
        inside their own `asyncio.to_thread` worker thread (`server.py`), so no further
        `to_thread` is needed there; `_periodic_profile_refresh` (running ON the loop) wraps this
        call in `asyncio.to_thread` itself instead. Never raises: every failure is caught, logged
        as a fixed code, and leaves whatever record already exists on disk untouched -- either
        because nothing was written (the comparison short-circuited) or because
        `cli.write_listener_record`'s own atomic temp-file-then-`rename` never replaced the real
        path (it fails before that point, or not at all)."""
        srv = self._server
        if srv is None or self._record is None or self._nonce is None:
            return  # disconnected (or never fully connected) since this was scheduled/called
        bound = srv.bound
        if bound is None:
            return
        try:
            profiles = [(p, _fallback_display_name(p)) for p in served]
        except Exception:
            log_event("listener_record_profiles", outcome="refresh_failed")
            return
        if (
            not refresh_health
            and self._profile_names_key(profiles) == self._profile_names_key(self._known_profiles)
        ):
            return  # the periodic tick handles flag/key changes on an unchanged roster
        try:
            health = self._health_snapshot(srv.ctx, profiles)
            with self._record_lock:
                if self._server is not srv or self._record is None:
                    return  # disconnect won the race; never recreate a stale record
                if (
                    not refresh_health
                    and self._profile_names_key(profiles)
                    == self._profile_names_key(self._known_profiles)
                ):
                    return  # an unchanged opportunistic read need not rewrite
                cli.write_listener_record(
                    self._record,
                    host=bound[0],
                    port=bound[1],
                    iid=srv.ctx.iid,
                    nonce=self._nonce,
                    profiles=profiles,
                    health_checked_at=int(time.time()),
                    health=health,
                )
                self._known_profiles = tuple(profiles)
        except OSError:
            log_event("listener_record_profiles", outcome="refresh_write_failed")
            return  # the previous record is untouched (write_listener_record's own atomicity)

    def _observe_served_profiles(self, served: Iterable[str]) -> None:
        """`Reads.roster`/`Authorize.authorize`'s hook (wired in through `open_components`),
        called from their own worker thread with the served set they already fetched for
        themselves. Never raises past this point -- a refresh hiccup must never surface as a
        roster/authorize failure."""
        try:
            self._sync_refresh(served)
        except Exception:
            log_event("listener_record_profiles", outcome="observe_failed")

    async def _periodic_profile_refresh(self) -> None:
        """Supervised safety net (mirrors `gateway.run_profile_reconcile`'s own watcher shape):
        one refresh shortly after connect (the multiplexer's hot-add can land within seconds), then
        every `PROFILE_REFRESH_INTERVAL_S`, until cancelled on disconnect. Runs on the loop; the
        bridge call and the record write are each pushed to a worker thread (`asyncio.to_thread`)
        so neither ever blocks it -- `served_profiles()` is documented as live in-memory
        bookkeeping, but this task treats it as potentially blocking anyway, the same caution
        `open_components` (`asyncio.to_thread(open_components, self)`) and `connect()`'s own
        listener start already take."""
        await asyncio.sleep(PROFILE_REFRESH_INITIAL_DELAY_S)
        while True:
            srv = self._server
            if srv is None or srv.ctx.bridge is None:
                return
            try:
                served = await asyncio.to_thread(srv.ctx.bridge.served_profiles)
            except Exception:
                log_event("listener_record_profiles", outcome="refresh_failed")
            else:
                await asyncio.to_thread(self._sync_refresh, served, refresh_health=True)
            await asyncio.sleep(PROFILE_REFRESH_INTERVAL_S)

    async def _cancel_profile_refresh(self) -> None:
        task, self._profile_refresh_task = self._profile_refresh_task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def _drop_record(self) -> None:
        with self._record_lock:
            record, self._record = self._record, None
            self._nonce = None
            self._known_profiles = None
            if record is not None:
                cli.remove_listener_record(record)

    def _listener_closed(self) -> None:
        srv, self._server = self._server, None
        if srv is None:
            return
        task, self._profile_refresh_task = self._profile_refresh_task, None
        if task is not None:
            task.cancel()  # fire-and-forget: this callback itself is synchronous (server.py)
        self._drop_record()
        self._close_generation(srv.ctx)
        srv.ctx.store.close()
        # PR7-6 step 3: stay closed until the gateway restarts (a later `connect` would load the
        # new key and start a new listener; nothing here restarts it).
        self._set_fatal_error(IDENTITY_CHANGED_CODE, IDENTITY_CHANGED_MESSAGE, retryable=False)

    async def disconnect(self) -> None:
        await self._cancel_profile_refresh()
        srv, self._server = self._server, None
        self._drop_record()
        if srv is not None:
            await srv.stop(notify=False)
            self._close_generation(srv.ctx)
            srv.ctx.store.close()
        self._mark_disconnected()

    @staticmethod
    def _close_generation(ctx: server.ServerContext) -> None:
        """R9: the listener that owned this prompt generation stopped. Its rows expire and a
        stream still bound to it can never insert into a later generation."""
        if ctx.prompt_store is not None:
            ctx.prompt_store.close(ctx.now())

    def _hooks(self) -> prompts.AdapterHooks | None:
        hooks = getattr(self, "_hmp_hooks", None)
        if isinstance(hooks, prompts.AdapterHooks):
            return hooks
        return None

    def note_inert_reply(self, chat_id: str) -> None:
        """The P6 trigger's outbound reply is still dropped (PR6-2)."""
        hooks = self._hooks()
        if hooks is not None:
            hooks.note_inert(chat_id)

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """Phone-chat replies create bounded observations. The inert-trigger reply does not.
        Nothing here is logged (PR6-2, SEC-4)."""
        hooks = self._hooks()
        if hooks is None:
            return SendResult(success=True)
        await hooks.reconcile_chat(chat_id)
        hooks.on_send(chat_id, content, reply_to, metadata)
        return SendResult(success=True)

    async def _send_exec_approval_prompt(self, prompt: Any) -> SendResult:
        """AP-6 / §3.3. An exact match becomes a card; ambiguous entries get deny-only recovery.
        Unbound text cannot become an approval answer."""
        hooks = self._hooks()
        if hooks is None:
            return SendResult(success=False)
        stored = await hooks.on_exec_approval(prompt)
        return SendResult(success=stored)

    async def send_clarify(
        self,
        chat_id: str,
        question: str,
        choices: list[Any] | None,
        clarify_id: str,
        session_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """Phone-chat clarify card. Does not call the base numbered-list implementation."""
        del metadata
        hooks = self._hooks()
        if hooks is None:
            return SendResult(success=False)
        offered = [choice for choice in choices if isinstance(choice, str)] if choices else None
        stored = await hooks.on_clarify(
            chat_id=chat_id,
            question=question,
            choices=offered,
            clarify_id=clarify_id,
            session_key=session_key,
        )
        return SendResult(success=stored)

    async def retire_clarify_card(self, clarify_id: str, notice: str | None = None) -> None:
        """The wait ended with no answer. The next poll omits the card. `notice` is not logged."""
        del notice
        hooks = self._hooks()
        if hooks is not None:
            hooks.retire(clarify_id)

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        del chat_id
        return {"name": PLATFORM_NAME, "type": "dm"}
