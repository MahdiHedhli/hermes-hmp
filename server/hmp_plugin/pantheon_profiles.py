"""Strict profile discovery for the exact ``v2026.8.31`` Hermes read adapter.

This module imports no Hermes internals. The eventual tag-specific bridge supplies
the reviewed profile helpers after its own exact-build gate. In particular, callers
must never use that tag's ``_resolve_profile_home_for_source`` for a read: it
silently substitutes the root home for an invalid explicit profile.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


class ProfileResolutionError(RuntimeError):
    """A fixed, non-sensitive refusal to map a requested profile to a home."""


def served_profile_homes(
    runner: Any,
    *,
    profiles_to_serve: Callable[..., Sequence[tuple[str, Path]]],
    get_active_profile_name: Callable[[], str],
    get_hermes_home: Callable[[], Path],
    get_profile_dir: Callable[[str], Path],
    profile_exists: Callable[[str], bool],
    profile_matches_home: Callable[[str, Path], bool],
    validate_profile_name: Callable[[str], None],
) -> Mapping[str, Path]:
    """Return only profiles the old, running gateway claims to serve.

    ``profiles_to_serve`` is the old gateway's own selection helper. The active
    profile is included separately because ``_start_secondary_profile_adapters``
    serves its primary adapter even when a multiplex allowlist omits that name.
    A multiplex startup records per-profile pairing stores after it has brought
    the secondary profiles online; require that live record before advertising
    any bot. Missing or inconsistent state is an error, never a root fallback.
    """
    config = getattr(runner, "config", None)
    multiplex = getattr(config, "multiplex_profiles", None)
    if type(multiplex) is not bool:
        raise ProfileResolutionError("multiplex mode is unavailable")
    allowlist = getattr(config, "multiplex_profile_allowlist", None)
    if allowlist is not None and (
        not isinstance(allowlist, list)
        or not all(isinstance(name, str) for name in allowlist)
    ):
        raise ProfileResolutionError("profile allowlist is invalid")

    active = get_active_profile_name()
    if not isinstance(active, str) or active == "custom":
        raise ProfileResolutionError("active profile is unavailable")
    try:
        validate_profile_name(active)
    except ValueError as exc:
        raise ProfileResolutionError("active profile is invalid") from exc
    active_home = get_hermes_home()
    if not isinstance(active_home, Path) or not active_home.is_absolute():
        raise ProfileResolutionError("active home is unavailable")
    if not profile_exists(active) or not profile_matches_home(active, active_home):
        raise ProfileResolutionError("active home does not match profile")

    pairs = profiles_to_serve(multiplex=multiplex, profile_allowlist=allowlist)
    if not isinstance(pairs, (list, tuple)):
        raise ProfileResolutionError("served profiles are unavailable")
    out: dict[str, Path] = {}
    canonical_homes: set[Path] = set()
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ProfileResolutionError("served profile entry is invalid")
        name, home = pair
        if not isinstance(name, str) or not isinstance(home, Path) or not home.is_absolute():
            raise ProfileResolutionError("served profile entry is invalid")
        try:
            validate_profile_name(name)
        except ValueError as exc:
            raise ProfileResolutionError("served profile name is invalid") from exc
        if (
            name in out
            or not profile_exists(name)
            or home != get_profile_dir(name)
            or not profile_matches_home(name, home)
            or (name != "default" and home.is_symlink())
        ):
            raise ProfileResolutionError("served profile home is invalid")
        canonical = home.resolve(strict=False)
        if canonical in canonical_homes:
            raise ProfileResolutionError("profiles share a home")
        canonical_homes.add(canonical)
        out[name] = home

    if multiplex:
        # The primary adapter remains served even when its name is omitted from
        # the secondary-profile allowlist. Never derive that home from a route.
        if active not in out:
            home = get_profile_dir(active)
            if (
                not isinstance(home, Path)
                or not home.is_absolute()
                or home.is_symlink()
                or not profile_matches_home(active, home)
                or home.resolve(strict=False) in canonical_homes
            ):
                raise ProfileResolutionError("primary profile home is invalid")
            out[active] = home
        if "default" not in out:
            raise ProfileResolutionError("default profile is not served")
        stores = getattr(runner, "pairing_stores", None)
        if not isinstance(stores, Mapping) or any(name not in stores for name in out):
            raise ProfileResolutionError("served profile authorization is not ready")
    elif len(out) != 1 or active not in out:
        raise ProfileResolutionError("standalone profile does not match gateway")

    return out


def profile_home(profile: str, homes: Mapping[str, Path]) -> Path:
    """Resolve an exact served name only; no normalization or default alias."""
    if not isinstance(profile, str) or profile not in homes:
        raise ProfileResolutionError("profile is not served")
    return homes[profile]


def verify_source_route(
    runner: Any,
    adapter: Any,
    homes: Mapping[str, Path],
    profile: str,
    source: Any,
    *,
    match_profile_route: Callable[..., Any],
) -> None:
    """Require the old gateway's actual HMP route rule (or standalone primary).

    A ``source.profile`` stamp alone is not evidence of a matched route: old
    ``build_source`` falls back on a lookup failure. Only the old matcher can
    tell a multiplexed matched route from that fallback. A standalone gateway
    has no route stamp and must serve exactly its active profile.
    """
    profile_home(profile, homes)
    config = getattr(runner, "config", None)
    multiplex = getattr(config, "multiplex_profiles", None)
    if type(multiplex) is not bool or getattr(adapter, "gateway_runner", None) is not runner:
        raise ProfileResolutionError("gateway route state is unavailable")
    transport_ref = getattr(source, "_transport_adapter_ref", None)
    if not callable(transport_ref) or transport_ref() is not adapter:
        raise ProfileResolutionError("source transport is unavailable")
    platform = getattr(getattr(source, "platform", None), "value", None)
    if (
        platform != "hmp"
        or getattr(source, "scope_id", None) != profile
        or getattr(source, "guild_id", None) != profile
        or not isinstance(getattr(source, "chat_id", None), str)
        or not source.chat_id
        or getattr(source, "profile_route_rejected", None) is not False
    ):
        raise ProfileResolutionError("source is not an HMP profile route")
    if not multiplex:
        if len(homes) != 1 or getattr(source, "profile", None) is not None:
            raise ProfileResolutionError("standalone source is not primary")
        return
    if getattr(source, "profile", None) != profile:
        raise ProfileResolutionError("source profile does not match route")
    routes = getattr(config, "profile_routes", None)
    if not isinstance(routes, (list, tuple)) or not routes:
        raise ProfileResolutionError("profile route is unavailable")
    try:
        matched = match_profile_route(
            routes,
            platform="hmp",
            guild_id=source.guild_id,
            chat_id=source.chat_id,
            thread_id=getattr(source, "thread_id", None),
            parent_chat_id=getattr(source, "parent_chat_id", None),
        )
    except Exception as exc:
        raise ProfileResolutionError("profile route is unavailable") from exc
    if matched is None or getattr(matched, "profile", None) != profile:
        raise ProfileResolutionError("source has no matching profile route")


def existing_session_id(
    profile: str,
    homes: Mapping[str, Path],
    source: Any,
    session_store: Any,
    *,
    multiplex: bool,
) -> str | None:
    """Look up an old-tag session without minting a key, session, or database.

    The caller must separately prove the live gateway's mode, that Hermes
    matched a real route in multiplex mode, and that it authorized this user.
    The old ``build_source`` can fall back when no route matched, so its profile
    stamp alone is insufficient for disclosure. This primitive stays unwired
    until that ingress-equivalence gate is qualified. Use the old store's key
    generator: a standalone named profile uses the legacy namespace, unlike a
    multiplexed profile.
    """
    profile_home(profile, homes)
    if type(multiplex) is not bool:
        raise ProfileResolutionError("multiplex mode is unavailable")
    stamped = getattr(source, "profile", None)
    # In a standalone gateway, Hermes disables profile routing and leaves the
    # source stamp unset, even when its active profile has a non-default name.
    # In multiplex mode an exact route stamp is required; proof that a matching
    # rule produced it is a separate, still-unqualified authorization gate.
    if (
        getattr(source, "profile_route_rejected", None) is not False
        or (multiplex and stamped != profile)
        or (not multiplex and (len(homes) != 1 or stamped is not None))
    ):
        raise ProfileResolutionError("source is not routed to profile")
    try:
        key = session_store._generate_session_key(source)
        if not isinstance(key, str) or not key:
            raise ProfileResolutionError("session key is unavailable")
        entry = session_store.lookup_by_session_key(key)
    except ProfileResolutionError:
        raise
    except Exception as exc:
        raise ProfileResolutionError("session lookup is unavailable") from exc
    if entry is None:
        return None
    session_id = getattr(entry, "session_id", None)
    if not isinstance(session_id, str) or not session_id:
        raise ProfileResolutionError("session entry is invalid")
    return session_id
