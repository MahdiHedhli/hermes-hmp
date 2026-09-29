"""Exact-tag, scratch-home probe for the old gateway's HMP ingress decision.

Launched only by ``test_pantheon_pairing_fixture`` with an archived Hermes
``v2026.8.31`` on PYTHONPATH. It neither starts a gateway nor uses a live home.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from agent.secret_scope import (
    current_secret_scope,
    reset_secret_scope,
    set_multiplex_active,
    set_secret_scope,
)
from gateway.pairing import PairingStore
from gateway.platform_registry import PlatformEntry, platform_registry
from gateway.profile_routing import ProfileRoute
from gateway.run import GatewayRunner, _profile_runtime_scope

import hmp_plugin
from hmp_plugin.adapter import HmpAdapter


def _scratch_home() -> Path:
    home = Path(os.environ["HERMES_HOME"]).resolve()
    real_home = Path.home().resolve()
    assert home.is_absolute() and home != real_home and real_home not in home.parents
    return home


class RegistryContext:
    def register_platform(self, **kwargs: object) -> None:
        platform_registry.register(PlatformEntry(**kwargs))

    def register_cli_command(self, **_kwargs: object) -> None:
        pass


def _source(adapter: HmpAdapter, profile: str, user: str):
    return adapter.build_source(
        chat_id="synthetic-chat",
        chat_type="dm",
        user_id=user,
        user_name="synthetic",
        scope_id=profile,
        guild_id=profile,
    )


def _grant(store: PairingStore, user: str) -> None:
    code = store.generate_code("hmp", user)
    assert isinstance(code, str)
    approved = store.approve_code("hmp", code)
    assert approved is not None and approved["user_id"] == user


def main() -> None:
    home = _scratch_home()
    serenity = home / "profiles" / "serenity"
    serenity.mkdir(parents=True)
    # Synthetic allowlists stay in the isolated fixture. They are used only to
    # prove the difference between routed runtime and transport secret scopes.
    (home / ".env").write_text("GATEWAY_ALLOWED_USERS=transport-only\n", encoding="utf-8")
    (serenity / ".env").write_text("GATEWAY_ALLOWED_USERS=runtime-only\n", encoding="utf-8")

    hmp_plugin.register(RegistryContext())
    adapter = platform_registry.create_adapter("hmp", SimpleNamespace(extra={}))
    assert isinstance(adapter, HmpAdapter)

    runner = object.__new__(GatewayRunner)
    runner.config = SimpleNamespace(
        multiplex_profiles=True,
        multiplex_profile_allowlist=["serenity"],
        profile_routes=[
            ProfileRoute("root", "hmp", "default", guild_id="default"),
            ProfileRoute("named", "hmp", "serenity", guild_id="serenity"),
            ProfileRoute("unserved", "hmp", "ghost", guild_id="ghost"),
        ],
    )
    runner.adapters = {adapter.platform: adapter}
    runner._profile_adapters = {}
    runner.pairing_store = PairingStore(profile="default")
    runner.pairing_stores = {
        "default": runner.pairing_store,
        "serenity": PairingStore(profile="serenity"),
    }
    adapter.gateway_runner = runner
    set_multiplex_active(True)

    root = _source(adapter, "default", "root-user")
    named = _source(adapter, "serenity", "named-user")
    rejected = _source(adapter, "ghost", "root-user")
    assert root.profile == "default" and root.profile_route_rejected is False
    assert named.profile == "serenity" and named.profile_route_rejected is False
    assert rejected.profile is None and rejected.profile_route_rejected is True
    routes = runner.config.profile_routes
    runner.config.profile_routes = []
    unrouted = _source(adapter, "serenity", "named-user")
    assert unrouted.profile is None and unrouted.profile_route_rejected is False
    runner.config.profile_routes = routes

    _grant(runner.pairing_stores["default"], "root-user")
    _grant(runner.pairing_stores["serenity"], "named-user")
    assert runner._is_user_authorized_for_source(root) is True
    assert runner._is_user_authorized_for_source(named) is True
    assert runner._is_user_authorized_for_source(_source(adapter, "default", "named-user")) is False
    assert runner._is_user_authorized_for_source(_source(adapter, "serenity", "root-user")) is False
    assert (
        runner._is_user_authorized_for_source(_source(adapter, "default", "never-enrolled"))
        is False
    )
    assert (
        runner._is_user_authorized_for_source(_source(adapter, "serenity", "never-enrolled"))
        is False
    )

    # An HMP read adapter must reject the route marker before calling authz:
    # Hermes's actual ingress drops that source before auth/session work.
    assert rejected.profile_route_rejected is True

    # A primary transport can route into a named runtime. Authorization still
    # uses the stamped primary transport home, not the named runtime's .env.
    transported = _source(adapter, "serenity", "transport-only")
    transported._authorization_profile_home = home
    routed_only = _source(adapter, "serenity", "runtime-only")
    routed_only._authorization_profile_home = home
    with _profile_runtime_scope(serenity):
        assert runner._is_user_authorized_for_source(transported) is True
        assert runner._is_user_authorized_for_source(routed_only) is False

    # A routed profile may separately enable allow-all. A future HMP bridge
    # must check its canary in both scopes, then refuse the bot even though the
    # primary transport scope itself is restrictive.
    canary = _source(adapter, "serenity", "never-enrolled-canary")
    canary._authorization_profile_home = home
    with _profile_runtime_scope(serenity):
        scoped = current_secret_scope()
        assert scoped is not None
        open_scope = dict(scoped)
        open_scope.pop("GATEWAY_ALLOWED_USERS", None)
        open_scope["GATEWAY_ALLOW_ALL_USERS"] = "true"
        token = set_secret_scope(open_scope)
        try:
            assert runner._is_user_authorized_for_source(canary) is False
            del canary._authorization_profile_home
            assert runner._is_user_authorized_for_source(canary) is True
        finally:
            reset_secret_scope(token)


if __name__ == "__main__":
    main()
