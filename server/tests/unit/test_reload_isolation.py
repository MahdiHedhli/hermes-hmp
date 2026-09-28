"""Regression test for the live `500` on `POST /hmp/v1/pair/request` the owner hit on a real,
multiplexed Hermes gateway (8afaab37): `event=handler_error outcome=internal_error
exception_type=KeyError at=server.py:context:297 last=web_app.py:__getitem__:199`.

Root cause (see `hmp_plugin/request_ctx.py`'s docstring for the full account): Hermes's plugin
loader can load `server/hmp_plugin` more than once in one process -- a multiplexed gateway serving
several profiles, or a plugin reload. Before every such load it evicts `hermes_plugins.hmp` and
every `hermes_plugins.hmp.*` submodule from `sys.modules`
(`hermes_cli/plugins_loader.py`, `_load_directory_module` / `_evict_modules`). A listener already
built from load N keeps running load N's `ServerContext` and the `web.AppKey` `CTX_KEY` it stored
on the aiohttp `Application` (compared by identity). Before this fix, `pairing.py` / `tokens.py` /
`revoke.py` resolved `server.py`'s shared helpers with a *request-time* `from .server import ...`
inside each handler, and `adapter.py`'s `open_components()` resolved `authorize.py` / `reads.py`
the same way at *connect-time*. Both re-resolve against whatever is CURRENTLY in `sys.modules`,
which after a later load is load N+1's copy -- a different `CTX_KEY` object, and a different
`contract.HmpError` class than the one load N's `error_middleware` checks `except HmpError`
against.

This test reproduces the real mechanism, not a stand-in for it: it loads the package twice
exactly as Hermes's loader does (`importlib.util.spec_from_file_location` with
`submodule_search_locations`, under the real `hermes_plugins.hmp` name, evicting
`hermes_plugins.hmp*` between loads), then drives requests against the FIRST load's app -- built
with the FIRST load's `ServerContext` via the real `adapter.open_components()` -- after the SECOND
load has replaced every `hermes_plugins.hmp` submodule in `sys.modules`. `monkeypatch` owns every
`sys.modules` mutation this test makes, so it is undone automatically at teardown regardless of
outcome (`monkeypatch.setitem` / `monkeypatch.delitem` revert like any other monkeypatch, on
success or on failure).

Before the fix (checked against fa987c7 -- see the worker report for how), this test is RED:
`POST /pair/request` 500s with `exception_type=KeyError`, exactly the owner's report; and the P6
`/bots/{p}/authorize` route also gets a `500` (an `HmpError` raised by `authorize.py`, resolved to
a later load's `contract` module, escapes load 1's `error_middleware` uncaught) where it should
get a `503` (`other`/`unverifiable`).
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer

from hmp_plugin import crypto, wire
from hmp_plugin.contract import OFFER_TTL_S, TAG_OFFER, TAG_PAIR_DONE, TAG_PAIR_REQ

from .hmp_kit import Device, get, post

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "hmp_plugin"
MODULE_NAME = "hermes_plugins.hmp"
NS_PARENT = "hermes_plugins"


def _load(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Load `server/hmp_plugin` as `hermes_plugins.hmp`, exactly the way Hermes's real plugin
    loader does it (`hermes_cli/plugins_loader.py`, `PluginManager._load_directory_module`):
    evict any stale `hermes_plugins.hmp*` entries first (`_evict_modules`), then
    `spec_from_file_location(..., submodule_search_locations=[plugin_dir])` + `exec_module`.
    Every `sys.modules` write goes through `monkeypatch`, so a second call in the same test
    correctly evicts the first call's entries, and everything reverts at test teardown either
    way -- this never leaks `hermes_plugins.hmp*` state into another test.
    """
    prefix = MODULE_NAME + "."
    for name in [n for n in sys.modules if n == MODULE_NAME or n.startswith(prefix)]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    if NS_PARENT not in sys.modules:
        ns_pkg = types.ModuleType(NS_PARENT)
        ns_pkg.__path__ = []  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, NS_PARENT, ns_pkg)
    init_file = PACKAGE_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        MODULE_NAME, init_file, submodule_search_locations=[str(PACKAGE_DIR)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = MODULE_NAME
    module.__path__ = [str(PACKAGE_DIR)]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, MODULE_NAME, module)
    spec.loader.exec_module(module)
    return module


def _stub_gateway_platform_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """`adapter.py` imports `gateway.config.Platform` and
    `gateway.platforms.base.{BasePlatformAdapter, SendResult}` at module level -- the one
    documented-API exception `check_plugin_surface.py` allows it (S1). A stand-in for those,
    exactly as `test_adapter.py`'s `adapter_module` fixture installs, lets the real `adapter.py`
    import without a Hermes install present."""

    class _BasePlatformAdapter:
        def __init__(self, config: Any, platform: Any) -> None:
            self.config = config
            self.platform = platform

        def _mark_connected(self, *, listener_base: str | None = None) -> None:
            pass

        def _mark_disconnected(self) -> None:
            pass

        def _set_fatal_error(self, code: str, message: str, *, retryable: bool) -> None:
            pass

    class _SendResult:
        def __init__(self, success: bool, message_id: str | None = None, error: str | None = None):
            self.success, self.message_id, self.error = success, message_id, error

    gateway = types.ModuleType("gateway")
    config = types.ModuleType("gateway.config")
    platforms = types.ModuleType("gateway.platforms")
    base = types.ModuleType("gateway.platforms.base")
    config.Platform = lambda name: ("platform", name)  # type: ignore[attr-defined]
    base.BasePlatformAdapter = _BasePlatformAdapter  # type: ignore[attr-defined]
    base.SendResult = _SendResult  # type: ignore[attr-defined]
    for name, mod in (
        ("gateway", gateway),
        ("gateway.config", config),
        ("gateway.platforms", platforms),
        ("gateway.platforms.base", base),
    ):
        monkeypatch.setitem(sys.modules, name, mod)


def test_pair_request_and_authed_routes_survive_a_plugin_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_gateway_platform_api(monkeypatch)

    # ---- Load 1: the package a listener is built from, exactly as Hermes loads it. -------------
    load1 = _load(monkeypatch)
    server1 = importlib.import_module(f"{MODULE_NAME}.server")
    adapter1 = importlib.import_module(f"{MODULE_NAME}.adapter")
    identity1 = importlib.import_module(f"{MODULE_NAME}.identity")
    compat1 = importlib.import_module(f"{MODULE_NAME}.compat")
    del load1  # only imported to trigger __init__.py; the submodules above are what's exercised

    # Isolated custody -- never the owner's real Hermes home (worker rule; also mirrors
    # `hmp_kit.identity_kwargs`). `open_components()` calls `identity.resolve_custody()` and
    # `identity.load_or_create(store)` with no override arguments in production, so both are
    # monkeypatched here to redirect to this test's tmp_path instead of the real default.
    hermes_root = tmp_path / "hermes"
    binding_root = tmp_path / "state" / "hermes-hmp"
    env = {"HERMES_HOME": str(hermes_root)}
    custody = identity1.resolve_custody(env=env, hermes_root=hermes_root, binding_root=binding_root)
    host_id = identity1.HostId("test-source", "synthetic-host-a")

    real_load_or_create = identity1.load_or_create
    monkeypatch.setattr(
        adapter1.identity,
        "resolve_custody",
        lambda *_a, **_k: custody,
    )
    monkeypatch.setattr(
        adapter1.identity,
        "load_or_create",
        lambda store, **_k: real_load_or_create(
            store,
            env=env,
            hermes_root=hermes_root,
            binding_root=binding_root,
            host_id=lambda: host_id,
        ),
    )

    class _FakeGate:
        def evaluate(self) -> Any:
            return compat1.CompatResult(compat1.CompatStatus.SUPPORTED)

    monkeypatch.setattr(adapter1.compat, "default_gate", lambda **_k: _FakeGate())

    # ---- Load 2: a second profile's load on the same multiplexed gateway (or a plugin reload). -
    # This evicts every `hermes_plugins.hmp*` entry load 1 populated -- including
    # `.authorize`, `.reads`, `.bridge` and `.contract` -- from `sys.modules`, exactly as the
    # owner's gateway does when it loads the plugin for its other two profiles.
    _load(monkeypatch)

    # `open_components()` is the real adapter code, called AFTER load 2 exists: this is the exact
    # window in which the old code's lazy `from .authorize import Authorize` / `from .bridge
    # import ...` / `from .reads import ...` would re-resolve against load 2 instead of load 1.
    # `_FakeRunner.served_profile_names()` -> `[]` is all `HermesReadBridge` needs to answer real
    # roster/authorize calls without ever touching actual Hermes internals: no profile is served,
    # so the bridge fails closed on its own terms (`AuthzState.NOT_SERVED`), not by erroring out.
    class _FakeRunner:
        def served_profile_names(self) -> list[str]:
            return []

    fake_adapter = types.SimpleNamespace(gateway_runner=_FakeRunner())
    ctx1 = adapter1.open_components(fake_adapter)
    app1 = server1.build_app(ctx1)

    async def scenario(client: TestClient) -> None:
        # ---- P2 `POST /pair/request` -- the exact route the owner's report named. -------------
        dev = Device()
        oid_raw, secret = crypto.random_bytes(16), crypto.random_bytes(32)
        oid = wire.b64u_encode(oid_raw)
        now = ctx1.now()
        ctx1.store.insert_offer(oid, crypto.secret_hash(TAG_OFFER, secret), now + OFFER_TTL_S)
        msg = crypto.transcript(
            TAG_PAIR_REQ, ctx1.iid, oid_raw, crypto.sha256(secret), dev.pub, dev.name, dev.nd
        )
        body = {
            "v": 1,
            "oid": oid,
            "s": wire.b64u_encode(secret),
            "device_name": dev.name,
            "device_pub": wire.b64u_encode(dev.pub),
            "nd": wire.b64u_encode(dev.nd),
            "sig": dev.sign(msg),
        }
        status, resp = await post(client, "/pair/request", body)
        assert status == 202, resp  # was 500 KeyError before the fix
        pairing_id, ni = resp["pairing_id"], wire.b64u_decode(resp["ni"], length=32)
        dev.pairing_id, dev.ni = pairing_id, ni

        # P3 (as the operator CLI would) then P4, to reach an authed route.
        user_id = "hmpu_" + crypto.random_bytes(16).hex()
        ctx1.store.insert_user(user_id, "test label", now)
        pairing_module = importlib.import_module(f"{MODULE_NAME}.pairing")
        pairing_module.confirm_pairing(
            ctx1.store, pairing_id, user_id=user_id, label="test label", now=now
        )
        ts = dev.next_ts(now)
        pid_raw = wire.b64u_decode(pairing_id, length=16)
        msg4 = crypto.transcript(TAG_PAIR_DONE, ctx1.iid, pid_raw, dev.nd, dev.ni, ts)
        status, resp = await post(
            client, "/pair/complete", {"pairing_id": pairing_id, "ts": ts, "sig": dev.sign(msg4)}
        )
        assert status == 200, resp  # was 500 KeyError before the fix
        headers = {"Authorization": f"Bearer {resp['access_token']}", "HMP-Instance": ctx1.iid}

        # ---- An authed route (RO-1 roster): proves `bearer()`/`context()` survive the reload. --
        status, resp = await get(client, "/bots", headers=headers)
        assert status == 200, resp  # was 500 KeyError before the fix

        # ---- A route that raises `HmpError` from a NON-server module (authorize.py, PR6-1). ----
        # `_FakeRunner` serves no profile, so `HermesReadBridge.authz_state("testbot", ...)`
        # returns `AuthzState.NOT_SERVED` on its own terms (no exception, no real Hermes call),
        # and `authorize.py`'s `_outcome` raises `HmpError(ErrorCode.NOT_ROUTED, authz=...)` --
        # a `409`, never a `500`. Before the fix, `authorize.py` was resolved fresh at
        # `open_components()` call time (after load 2 evicted it), so the `HmpError` it raises
        # came from load 2's `contract` module -- a different class than load 1's
        # `error_middleware` checks `except HmpError` against -- and fell through to the generic
        # `except Exception` handler, giving `500` instead of `409`.
        status, resp = await post(client, "/bots/testbot/authorize", {}, headers=headers)
        assert status == 409, resp  # was 500 (uncaught HmpError) before the fix
        assert resp["error"]["code"] == "not_routed"
        assert resp["error"]["authz"] == "not_served"

    async def main() -> None:
        async with TestClient(TestServer(app1)) as client:
            await scenario(client)

    asyncio.run(main())
