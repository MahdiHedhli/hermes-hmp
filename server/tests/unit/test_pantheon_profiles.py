"""Fail-closed checks for the old Hermes tag's future read adapter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin.pantheon_profiles import (
    ProfileResolutionError,
    profile_home,
    served_profile_homes,
)


def _fixture(tmp_path: Path):
    default = tmp_path / "hermes"
    named = default / "profiles" / "serenity"
    named.mkdir(parents=True, exist_ok=True)
    paths = {"default": default, "serenity": named}
    def validate(name: str) -> None:
        if name not in paths:
            raise ValueError("invalid profile")

    runner = SimpleNamespace(
        config=SimpleNamespace(
            multiplex_profiles=True, multiplex_profile_allowlist=["serenity"]
        ),
        pairing_stores={"default": object(), "serenity": object()},
    )
    api = dict(
        profiles_to_serve=lambda **_kw: list(paths.items()),
        get_active_profile_name=lambda: "default",
        get_hermes_home=lambda: default,
        get_profile_dir=lambda name: paths[name],
        profile_exists=lambda name: name in paths,
        profile_matches_home=lambda name, home: paths.get(name) == home,
        validate_profile_name=validate,
    )
    return runner, api, paths


def test_exact_served_name_never_falls_back_to_default(tmp_path: Path) -> None:
    runner, api, paths = _fixture(tmp_path)
    homes = served_profile_homes(runner, **api)
    assert profile_home("serenity", homes) == paths["serenity"]
    with pytest.raises(ProfileResolutionError):
        profile_home("ghost", homes)
    with pytest.raises(ProfileResolutionError):
        profile_home("Default", homes)


def test_mismatched_or_missing_profile_state_refuses_all(tmp_path: Path) -> None:
    runner, api, paths = _fixture(tmp_path)
    api["profiles_to_serve"] = lambda **_kw: [
        ("default", paths["default"]), ("serenity", paths["default"])
    ]
    with pytest.raises(ProfileResolutionError):
        served_profile_homes(runner, **api)

    runner, api, _ = _fixture(tmp_path)
    runner.pairing_stores.pop("serenity")
    with pytest.raises(ProfileResolutionError):
        served_profile_homes(runner, **api)


def test_unknown_mode_and_custom_active_home_refuse(tmp_path: Path) -> None:
    runner, api, _ = _fixture(tmp_path)
    runner.config.multiplex_profiles = None
    with pytest.raises(ProfileResolutionError):
        served_profile_homes(runner, **api)

    runner.config.multiplex_profiles = True
    api["get_active_profile_name"] = lambda: "custom"
    with pytest.raises(ProfileResolutionError):
        served_profile_homes(runner, **api)


def test_named_profile_symlink_cannot_alias_root_home(tmp_path: Path) -> None:
    runner, api, paths = _fixture(tmp_path)
    named = paths["serenity"]
    named.rmdir()
    named.symlink_to(paths["default"], target_is_directory=True)
    with pytest.raises(ProfileResolutionError):
        served_profile_homes(runner, **api)
