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
`authorize`/`reads` imports close.)
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from gateway.config import Platform
from gateway.platforms.base import BasePlatformAdapter, SendResult

from . import cli, compat, direct_send, identity, mobile_cron, mobile_model, server
from .authorize import Authorize
from .cli import listener_record_path
from .contract import PLATFORM_NAME, OtherWhy
from .logging_policy import log_event
from .reads import Reads, _fallback_display_name
from .store import Store

IDENTITY_CHANGED_CODE = "hmp_identity_changed"
IDENTITY_CHANGED_MESSAGE = "HMP instance key changed; restart the gateway to serve the new key"

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

_bridge_classes_cache: tuple[type[Any], type[Any]] | None = None


def _bridge_classes() -> tuple[type[Any], type[Any]]:
    """`(HermesReadBridge, StoreDirectory)`, imported from `bridge.py` at most once per load of
    this package. S3 forbids importing `bridge` at module level, so this import cannot move to
    the top of this file the way `authorize`/`reads` did above; caching it here instead means
    only the FIRST supported `open_components()` call in this load ever executes the `from
    .bridge import ...` statement, so a reload that happens between that call and a later one
    (another profile's load, on a multiplexed gateway) cannot swap the class a running listener's
    `ctx.bridge` is built from out from under it."""
    global _bridge_classes_cache
    if _bridge_classes_cache is None:
        from .bridge import HermesReadBridge, StoreDirectory

        _bridge_classes_cache = (HermesReadBridge, StoreDirectory)
    return _bridge_classes_cache


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

    def _read_cron_enabled() -> bool:
        live_config = getattr(adapter, "config", None)
        live_extra = getattr(live_config, "extra", None)
        block = live_extra.get("cron") if isinstance(live_extra, Mapping) else None
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
        cron_flag=_read_cron_enabled,
        cron_qualified=lambda: result.supported and mobile_cron.qualified_build(),
        model_flag=_read_model_enabled,
        model_qualified=lambda: result.supported and mobile_model.qualified_build(),
    )
    if result.supported:
        bridge_cls, directory_cls = _bridge_classes()

        ctx.bridge = bridge_cls(adapter, directory_cls(store))
        # Live-bug fix: `adapter._observe_served_profiles` is a bound method of the adapter this
        # context belongs to (this function's own `adapter` argument), so it is safe to close over
        # here even though `self._record`/`self._nonce` are not set until `connect()` finishes
        # further down -- neither `Reads.roster` nor `Authorize.authorize` can run before then.
        on_served_profiles = getattr(adapter, "_observe_served_profiles", None)
        ctx.reads = Reads(
            ctx.bridge,
            store,
            iid=ident.iid,
            guarantees=ctx.guarantees,
            write_gate=ctx.reported_write_gate,
            send_gate=ctx.reported_send_gate,
            clock=ctx.now,
            on_served_profiles=on_served_profiles,
        )
        ctx.authorize = Authorize(
            ctx.bridge, store, clock=ctx.now, on_served_profiles=on_served_profiles
        )
        # Amendment F2: constructed on every supported build, regardless of `direct_send_enabled`
        # -- the flag is re-checked per request (DS-2(b)), not at listener-start time, so a
        # host-side flag flip takes effect on the next request, not the next restart.
        ctx.direct_send_deps = direct_send.DirectSendDeps(
            bridge=ctx.bridge,
            store=store,
            locks=direct_send.ProfileLocks(),
            now=ctx.now,
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
                cli.write_listener_record(
                    self._record,
                    host=srv.bound[0],
                    port=srv.bound[1],
                    iid=ctx.iid,
                    nonce=self._nonce,
                    profiles=profiles,
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

    def _sync_refresh(self, served: Iterable[str]) -> None:
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
        if self._profile_names_key(profiles) == self._profile_names_key(self._known_profiles):
            return  # unchanged: no rewrite (cheap comparison short-circuits the write)
        try:
            cli.write_listener_record(
                self._record,
                host=bound[0],
                port=bound[1],
                iid=srv.ctx.iid,
                nonce=self._nonce,
                profiles=profiles,
            )
        except OSError:
            log_event("listener_record_profiles", outcome="refresh_write_failed")
            return  # the previous record is untouched (write_listener_record's own atomicity)
        self._known_profiles = tuple(profiles)

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
                await asyncio.to_thread(self._sync_refresh, served)
            await asyncio.sleep(PROFILE_REFRESH_INTERVAL_S)

    async def _cancel_profile_refresh(self) -> None:
        task, self._profile_refresh_task = self._profile_refresh_task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def _drop_record(self) -> None:
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
            srv.ctx.store.close()
        self._mark_disconnected()

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """Drop the content, unlogged. F1 delivers nothing to devices (PR6-2, SR-007)."""
        del chat_id, content, reply_to, metadata
        return SendResult(success=True)

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        del chat_id
        return {"name": PLATFORM_NAME, "type": "dm"}
