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
