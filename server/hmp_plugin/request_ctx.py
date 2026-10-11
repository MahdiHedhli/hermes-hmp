"""Request/response plumbing shared by every HMP route handler: `ServerContext`, its `CTX_KEY`,
`context()`, the body/response helpers, the per-IP rate-limit key and bearer authentication.
Split out of `server.py` (live-bug fix, T024/T025/T026/T027 follow-up).

This is a leaf module: it imports nothing from `server.py`, `pairing.py`, `tokens.py` or
`revoke.py`, and none of those import each other for these names either -- `server.py` and every
route-handler module import THIS module instead, at their own top level.

Why this file exists (SEC-4 / plugin-reload hazard). Hermes's plugin loader can load this whole
package more than once in one process -- a multiplexed gateway serving several profiles, or a
plugin reload (`hermes_cli/plugins_loader.py`, `_load_directory_module` /
`_evict_modules(module_name)`) -- and evicts every `hermes_plugins.hmp` and
`hermes_plugins.hmp.*` entry from `sys.modules` before each such load. A listener built from
load N keeps running load N's objects: its `ServerContext`, and the `web.AppKey` `CTX_KEY` it
stored on the aiohttp `Application` (compared by identity, not value). If load N+1 happens later
in the same process, `sys.modules` now holds load N+1's copies of every submodule, even though
load N's listener, and its already-built `Application`, are still running.

Before this fix, `pairing.py`, `tokens.py` and `revoke.py` resolved `context` /
`json_response` / `peer_key` / `read_json_body` with a *request-time* `from .server import ...`
inside each handler function. That statement re-resolves against whatever is CURRENTLY in
`sys.modules` when the handler runs -- load N+1's `server` module, once a later load has evicted
and re-imported it -- so `context(request)` looked up load N+1's `CTX_KEY` on load N's `app`, a
`KeyError`. That is the live `500` on `POST /hmp/v1/pair/request`:
`event=handler_error outcome=internal_error exception_type=KeyError at=server.py:context:297`.

Importing these names at module level, from a module that has no import path back to `server.py`,
binds each loaded copy of `pairing.py` / `tokens.py` / `revoke.py` / `server.py` to the matching
copy of these helpers exactly once, at that copy's own import time. A later reload of the package
can still replace what `sys.modules` holds, but it can no longer split a running app's helpers
away from the `CTX_KEY` and `ServerContext` it was built with.
"""

from __future__ import annotations

import dataclasses
import enum
import ipaddress
import secrets
import ssl
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from aiohttp import web

from . import gate, wire
from .auth import AuthContext, Authenticator
from .compat import CompatResult
from .contract import (
    LIMITER_TABLE_MAX,
    MAX_BODY_BYTES,
    ErrorCode,
    Guarantees,
    HmpError,
    ReadBridge,
    WriteGate,
    WriteGateState,
)
from .logging_policy import log_bridge_exception, log_event

# --------------------------------------------------------------------------------------------------
# Peer address parsing: shared by `server.address_allowed` (TR-4 bind/peer policy) and `peer_key`
# below (TR-6 loopback rate-limit collapse).
# --------------------------------------------------------------------------------------------------


def parse_peer_ip(text: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """The peer address `text` names, with an IPv4-mapped IPv6 literal unwrapped to its IPv4
    form; `None` if `text` is not an IP literal."""
    if not isinstance(text, str) or not text:
        return None
    try:
        addr = ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return None
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return addr


LOOPBACK_RATE_LIMIT_KEY = "loopback"


def peer_key(request: web.Request) -> str:
    """The per-IP rate-limit key. Never logged (SEC-4: no peer addresses).

    Every loopback peer (127.0.0.0/8, `::1`, and an IPv4-mapped `::ffff:127.x` form) collapses to
    one fixed key (TR-6): 127.0.0.0/10 alone is 16,777,216 distinct addresses, and loopback lets a
    caller pick its own source address freely, so treating each as its own bucket would let one
    caller manufacture unlimited "per-IP" rate-limit budget and, once the shared `RateLimiter`
    table is at its `LIMITER_TABLE_MAX` bound, evict other peers' live entries by flooding it with
    one-shot loopback keys.
    """
    remote = request.remote or ""
    addr = parse_peer_ip(remote)
    if addr is not None and addr.is_loopback:
        return LOOPBACK_RATE_LIMIT_KEY
    return remote


# --------------------------------------------------------------------------------------------------
# Rate limits (TR-6)
# --------------------------------------------------------------------------------------------------


class RateLimiter:
    """Fixed one-minute windows per `(bucket, key)`, LRU-bounded to `LIMITER_TABLE_MAX` entries
    (TR-6). In memory only: a restart resets it, which only ever loosens a limit briefly."""

    WINDOW_S = 60

    def __init__(self, max_entries: int = LIMITER_TABLE_MAX) -> None:
        self._max = max_entries
        self._table: OrderedDict[tuple[str, str], tuple[int, int]] = OrderedDict()

    def allow(self, bucket: str, key: str, limit: int, now: int) -> bool:
        slot = (bucket, key)
        window = now // self.WINDOW_S
        start, count = self._table.pop(slot, (window, 0))
        if start != window:
            start, count = window, 0
        count += 1
        self._table[slot] = (start, count)
        while len(self._table) > self._max:
            self._table.popitem(last=False)
        return count <= limit

    def check(self, bucket: str, key: str, limit: int, now: int) -> None:
        if not self.allow(bucket, key, limit, now):
            raise HmpError(ErrorCode.RATE_LIMITED)

    def __len__(self) -> int:
        return len(self._table)


# --------------------------------------------------------------------------------------------------
# Server context
# --------------------------------------------------------------------------------------------------


class ServingIdentity(Protocol):
    """What the server needs from `identity.LoadedIdentity`."""

    @property
    def iid(self) -> str: ...

    def private_key(self) -> Any: ...

    def k_grace(self) -> bytes: ...

    def still_current(self) -> bool: ...

    def server_ssl_context(self) -> ssl.SSLContext: ...


@dataclass(frozen=True, slots=True, repr=False)
class MediaBound:
    """What `ServerContext.media_snapshot` returns: the listener's bound references, by identity.
    `bound` is the exact `ctx.media_modules` tuple; `chain` is the bridge's seven-member cache and
    `reads_media` the reads cache; `registry_module` and `registry` are the listener's own. S5
    adds three more bound modules: `raster_module` (the actual raster-structure module whose
    `check_raster_structure` phase one runs), `payload_module` (the one carrier module the bridge
    and the route share) and `fetch_module` (the orchestrator whose namespace the route runs in).
    No value here is a wire, native or request field."""

    bound: tuple[Any, ...]
    chain: tuple[Any, ...]
    reads_media: tuple[Any, ...]
    registry_module: Any
    registry: Any
    raster_module: Any = None
    payload_module: Any = None
    fetch_module: Any = None

    def __repr__(self) -> str:
        return "MediaBound()"

    __str__ = __repr__

    def same_as(self, other: MediaBound) -> bool:
        return (
            self.bound is other.bound
            and self.chain is other.chain
            and self.reads_media is other.reads_media
            and self.registry_module is other.registry_module
            and self.registry is other.registry
            and self.raster_module is other.raster_module
            and self.payload_module is other.payload_module
            and self.fetch_module is other.fetch_module
        )


class ReadWorkerBudget:
    """One listener-owner budget retained across disconnect and reconnect generations."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.active = 0
        self.operator = 0
        self.poisoned = False

    def reserve(self, *, operator: bool) -> bool:
        with self.lock:
            if self.poisoned or self.active >= 4 or (operator and self.operator >= 2):
                return False
            self.active += 1
            if operator:
                self.operator += 1
            return True

    def release(self, *, operator: bool) -> None:
        with self.lock:
            if self.active <= 0 or (operator and self.operator <= 0):
                self.poisoned = True
                return
            self.active -= 1
            if operator:
                self.operator -= 1


@dataclass
class ServerContext:
    """Everything a route handler may use. Built once per listener start."""

    identity: ServingIdentity
    store: Any  # store.Store
    compat: CompatResult
    bridge: ReadBridge | None = None
    reads: Any = None  # reads.Reads, only on a supported build
    authorize: Any = None  # authorize.Authorize, only on a supported build
    clock: Callable[[], int] = field(default=lambda: int(time.time()))
    limiter: RateLimiter = field(default_factory=RateLimiter)
    on_identity_changed: Callable[[], None] | None = None
    guarantee_cache: Guarantees | None = None
    # Amendment A1 (session browsing) kill switch: `gateway.platforms.hmp.extra.session_browsing`,
    # default true. When false, `server.build_app` never registers SES-1/SES-2 at all -- the same
    # "not registered, 404" pattern F1 already uses for send/SSE/approvals/clarify/stop.
    session_browsing_enabled: bool = True
    # Local startup-only registration. No HTTP request or remote capability can turn this on.
    controls_requests_enabled: bool = False
    # Amendment F2 (direct send, HMP_V1.md §7a DS-2(b)/DS-10): the owner-dogfood host flag
    # `gateway.platforms.hmp.extra.direct_send.enabled`, default FALSE (OD-F14/OD-F15). Unlike
    # `session_browsing_enabled`, this does NOT control route registration -- `chat/messages` is
    # always registered (server-modules.md); with the flag off, it answers `503 write_gate_closed`
    # instead of `404`, matching how GU-4's original write gate already behaves when closed.
    #
    # Review round 2, should-fix: this used to be a plain `bool`, captured once at listener-start
    # time (`adapter.open_components`) despite that module's own comment claiming a per-request
    # re-check. It is now a zero-argument callable, re-invoked on every request
    # (`handle_chat_send`) -- `adapter.py` binds it to a closure over the live adapter config, so a
    # host-side flag flip is visible on the very next request, not the next gateway restart, at the
    # cost of one cheap in-memory dict lookup per call (no I/O).
    direct_send_flag: Callable[[], bool] = field(default=lambda: False)
    # `direct_send.DirectSendDeps`, only on a supported build (mirrors `reads`/`authorize` above).
    direct_send_deps: Any = None
    # v1.3 prompt rows (process memory). None until a supported listener builds one.
    prompt_store: Any = None
    # Approval availability (spec 034, owner policy 2026-10-01): the `approvals` and `phone_chat`
    # eligibility members, computed once at listener open from the actual API checks. Both default
    # CLOSED, so a context built without availability information never opens an approval route.
    # No exact build, manifest, fingerprint or latch is consulted.
    approvals_available: Callable[[], bool] = field(default=lambda: False)
    phone_chat_available: Callable[[], bool] = field(default=lambda: False)
    # Mobile cron is a separate persistent-execution gate. Both settings are
    # read from live HMP config for every request, and default to deny.
    owner_device_ids: Callable[[], frozenset[str]] = field(default=lambda: frozenset())
    # Readiness-only source readers preserve malformed source values instead of using the
    # fail-closed operational closures above.
    readiness_owner_device_ids: Callable[[], frozenset[str]] | None = field(
        default=None, repr=False
    )
    readiness_settings: Callable[[], object] | None = field(default=None, repr=False)
    readiness_generation: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    read_worker_budget: ReadWorkerBudget = field(default_factory=ReadWorkerBudget, repr=False)
    cron_flag: Callable[[], bool] = field(default=lambda: False)
    cron_available: Callable[[], bool] = field(default=lambda: False)
    model_flag: Callable[[], bool] = field(default=lambda: False)
    model_available: Callable[[], bool] = field(default=lambda: False)
    # Minimum-version eligibility (owner policy 2026-10-01): whether this Hermes install provides
    # what send and session browsing need. Kept separate from the host flags above, which only say
    # whether the owner turned a feature on.
    send_available: Callable[[], bool] = field(default=lambda: True)
    session_browsing_available: bool = True
    # Local media (specs/011-local-image-serving). `media_flag` re-reads the live host config on
    # every call and defaults closed. `media_available` is the listener-scoped availability binding
    # (D-M4): it defaults to closed, `adapter.py` replaces it only on a listener whose `local_media`
    # eligibility member is available and whose media chain verified coherent, and the callback
    # itself runs the cheap in-memory use-time identity fence. `media_modules` holds the verified
    # strong references the bound listener uses -- `(bridge cache tuple, reads cache tuple)`, the
    # very objects `bridge.py` and `reads.py` cache -- so a caller uses the same objects
    # without a fresh import. S4's four read routes and the S5 fetch route consume them through
    # `media_snapshot()`, and a result is never cached here.
    media_flag: Callable[[], bool] = field(default=lambda: False)
    media_available: Callable[[], bool] = field(default=lambda: False)
    media_modules: tuple[tuple[Any, ...], tuple[Any, ...]] | None = None
    # S4: this listener's one registry (shared by mint here and the later S5 fetch) and the actual
    # `local_media_registry` module it came from, bound once at listener open by `adapter.py`. They
    # are NOT part of the `media_modules` shape. Both default `None`; the availability closure
    # fences them by identity and clears them when it closes this listener's media.
    media_registry_module: Any = None
    media_registry: Any = None
    # S5: three more per-listener bound references, set at open beside the registry and fenced and
    # cleared by the same availability closure: the actual `local_media_raster_structure` module,
    # the shared payload-carrier module and the route orchestrator module. All default `None`.
    media_raster_module: Any = None
    media_payload_module: Any = None
    media_fetch_module: Any = None

    def is_approvals_available(self) -> bool:
        """Bot Chat approvals. Only an exact `True` opens it; anything else closes it."""
        try:
            if self.approvals_available() is not True:
                return False
            store = self.prompt_store
            return store is None or not store.closed
        except Exception as exc:  # fail closed
            log_bridge_exception(exc)
            return False

    def is_phone_chat_available(self) -> bool:
        """Phone chat sends and answers. Closed when the eligibility member is closed, and for the
        life of this listener once the binding fence closed its local generation (AP-10)."""
        try:
            if self.phone_chat_available() is not True:
                return False
            store = self.prompt_store
            return store is None or not (store.closed or store.phone_closed)
        except Exception as exc:  # fail closed
            log_bridge_exception(exc)
            return False

    def approval_surface_available(self, surface: str) -> bool:
        """The member a row's or route's surface needs: `bot_chat` -> approvals, else phone chat."""
        if surface == "bot_chat":
            return self.is_approvals_available()
        return self.is_phone_chat_available()

    def media_enabled(self) -> bool:
        try:
            return self.media_flag() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def is_media_available(self) -> bool:
        """Only an exact `True` opens it; an exception, a falsy or a non-bool closes. In-memory,
        synchronous and free of any await or import, so a caller can consume it on the loop."""
        try:
            return self.media_available() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def media_snapshot(self) -> MediaBound | None:
        """The exact references this listener bound, or `None`. Synchronous: it first runs the
        availability closure (an exact-true, identity-fenced check), then reads the context's own
        slots without an await, import, file or lock, so a caller can mint on the loop with nothing
        between this call and the mint. It never builds, copies or looks up an object: every
        member is the very object bound at listener open. Fails closed, logging only the type."""
        try:
            if self.media_available() is not True:
                return None
            bound = self.media_modules
            module, registry = self.media_registry_module, self.media_registry
            if type(bound) is not tuple or len(bound) != 2:
                return None
            chain, reads_media = bound
            if type(chain) is not tuple or type(reads_media) is not tuple:
                return None
            if module is None or registry is None:
                return None
            raster = self.media_raster_module
            payload, fetch = self.media_payload_module, self.media_fetch_module
            if raster is None or payload is None or fetch is None:
                return None
            return MediaBound(bound, chain, reads_media, module, registry, raster, payload, fetch)
        except Exception as exc:
            log_bridge_exception(exc)
            return None

    def is_owner_device(self, device_id: str) -> bool:
        try:
            decision = self.store.owner_controls_decision(device_id)
            if decision is not None:
                return decision
            return device_id in self.owner_device_ids()
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def is_approval_owner_device(self, device_id: str) -> bool:
        """Approval/clarify and Phone-send routes: the configured allowlist AND no host denial.

        The per-device controls grant (`is_owner_device`) is a separate privilege for jobs and
        model management. It never opens an approval route on its own: only an exact
        `owner_device_ids` entry does, and an explicit host denial still closes it. Any failed
        read denies."""
        try:
            if self.store.owner_controls_decision(device_id) is False:
                return False
            return device_id in self.owner_device_ids()
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def cron_enabled(self) -> bool:
        try:
            return self.cron_flag() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def is_cron_available(self) -> bool:
        try:
            return self.cron_available() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def model_enabled(self) -> bool:
        try:
            return self.model_flag() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def is_model_available(self) -> bool:
        try:
            return self.model_available() is True
        except Exception as exc:
            log_bridge_exception(exc)
            return False

    def is_send_available(self) -> bool:
        try:
            return self.send_available() is True
        except Exception as exc:  # fail closed
            log_bridge_exception(exc)
            return False

    def direct_send_effective(self) -> bool:
        """The owner's flag AND this Hermes providing what send needs."""
        return self.direct_send_enabled() and self.is_send_available()

    def direct_send_enabled(self) -> bool:
        try:
            return bool(self.direct_send_flag())
        except Exception as exc:  # fail closed: a broken reader never turns the flag on
            log_bridge_exception(exc)
            return False

    @property
    def readiness_workers(self) -> int:
        with self.read_worker_budget.lock:
            return self.read_worker_budget.active

    @property
    def operator_workers(self) -> int:
        with self.read_worker_budget.lock:
            return self.read_worker_budget.operator

    @property
    def iid(self) -> str:
        return self.identity.iid

    def now(self) -> int:
        return int(self.clock())

    def guarantees(self) -> Guarantees:
        """GU-2 flags from the bridge's capability map; all false without a bridge or when the
        bridge fails (fail closed). Cached once derived: the map is fixed per process."""
        if self.guarantee_cache is not None:
            return self.guarantee_cache
        if self.bridge is None:
            return Guarantees()
        try:
            caps = self.bridge.capability_versions()
        except Exception as exc:
            log_bridge_exception(exc)
            return Guarantees()

        def higher(flag: str, _key: str, _version: int) -> None:
            log_event("capability_higher", outcome=flag)

        self.guarantee_cache = gate.derive_guarantees(caps, log_higher_version=higher)
        return self.guarantee_cache

    def write_gate(self) -> WriteGate:
        return gate.write_gate(self.guarantees())

    def reported_write_gate(self) -> WriteGate:
        """An instance-level diagnostic for `/ready` and legacy roster fallback.

        It does not know whether each named profile has its own key. `Reads.roster` folds
        per-profile send gates into a conservative top-level value, and newer clients use each
        authorized bot's own `send_gate`. The route rechecks everything per request."""
        base = self.write_gate()
        if not self.direct_send_effective():
            return (
                gate.direct_send_gate(base_write_gate=base, flag_enabled=False, endpoint=None)
                if base.state is WriteGateState.OPEN
                else base
            )
        if base.state is not WriteGateState.OPEN:
            return WriteGate(state=WriteGateState.OPEN_GUARDED, reason=None)
        return base

    def reported_send_gate(self, profile: str) -> WriteGate:
        """Bot Chat send availability for one profile, using the route's actual prerequisites.

        Never send the endpoint or key over the wire. A send that this Hermes cannot serve or a
        failed secret lookup reports a closed gate and does not turn a global owner flag into
        per-profile authority.
        The send route rechecks all prerequisites at submission time.
        """
        base = self.write_gate()
        if not self.direct_send_effective():
            return gate.direct_send_gate(base_write_gate=base, flag_enabled=False, endpoint=None)
        deps = self.direct_send_deps
        bridge = self.bridge
        if deps is None or bridge is None:
            return gate.direct_send_gate(base_write_gate=base, flag_enabled=True, endpoint=None)
        try:
            endpoint = bridge.direct_send_endpoint(profile)
        except Exception as exc:
            log_bridge_exception(exc)
            endpoint = None
        return gate.direct_send_gate(
            base_write_gate=base, flag_enabled=True, endpoint=endpoint
        )


CTX_KEY: web.AppKey[ServerContext] = web.AppKey("hmp_ctx", ServerContext)


def context(request: web.Request) -> ServerContext:
    return request.app[CTX_KEY]


# --------------------------------------------------------------------------------------------------
# Responses and bodies
# --------------------------------------------------------------------------------------------------


def _plain(value: Any) -> Any:
    """Dataclasses, enums and tuples to JSON-ready values (wire names are field names).

    A field whose metadata sets `omit_if_none` is left out when its value is `None`. That is how
    additive optional fields (V-3) stay off the wire until they have a value. Existing fields
    that are part of the frozen shape, including an explicit JSON `null`, are still encoded.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out: dict[str, Any] = {}
        for f in dataclasses.fields(value):
            item = getattr(value, f.name)
            if item is None and f.metadata.get("omit_if_none"):
                continue
            out[f.name] = _plain(item)
        return out
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def json_response(body: Any, status: int = 200) -> web.Response:
    return web.Response(
        status=status,
        body=wire.dump_json(_plain(body)),
        content_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


def error_response(err: HmpError) -> web.Response:
    return json_response(err.body(), status=err.http)


async def read_json_body(request: web.Request) -> dict[str, Any]:
    """The request body as an I-JSON object (TR-9): `413 too_large` over the limits, otherwise
    `400 bad_request` for anything that is not I-JSON with an object at the top level."""
    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        raise HmpError(ErrorCode.TOO_LARGE)
    try:
        raw = await request.read()  # bounded by `client_max_size` (MAX_BODY_BYTES)
    except web.HTTPRequestEntityTooLarge as exc:
        raise HmpError(ErrorCode.TOO_LARGE) from exc
    if len(raw) > MAX_BODY_BYTES:
        raise HmpError(ErrorCode.TOO_LARGE)
    try:
        return wire.parse_body(raw)
    except wire.TooLargeError as exc:
        raise HmpError(ErrorCode.TOO_LARGE) from exc
    except wire.WireError as exc:
        raise HmpError(ErrorCode.BAD_REQUEST) from exc


# --------------------------------------------------------------------------------------------------
# Bearer authentication (TR-5, PR5-6)
# --------------------------------------------------------------------------------------------------


def single_header(request: web.Request, name: str) -> str | None:
    """A header that must appear exactly once; a missing or repeated one is None."""
    values = request.headers.getall(name, [])
    if len(values) != 1:
        return None
    return values[0]


def bearer(request: web.Request) -> AuthContext:
    """TR-5 / PR5-6 bearer authentication for one request (`auth.Authenticator`)."""
    ctx = context(request)
    return Authenticator(ctx.store, ctx.iid, ctx.now).authenticate(
        single_header(request, "Authorization"), single_header(request, "HMP-Instance")
    )
