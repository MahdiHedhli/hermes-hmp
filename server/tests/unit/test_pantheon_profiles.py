"""Fail-closed checks for the old Hermes tag's future read adapter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin.pantheon_profiles import (
    ProfileResolutionError,
    existing_session_id,
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
    api = {
        "profiles_to_serve": lambda **_kw: list(paths.items()),
        "get_active_profile_name": lambda: "default",
        "get_hermes_home": lambda: default,
        "get_profile_dir": lambda name: paths[name],
        "profile_exists": lambda name: name in paths,
        "profile_matches_home": lambda name, home: paths.get(name) == home,
        "validate_profile_name": validate,
    }
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


def test_existing_session_uses_store_key_without_creating_a_session(tmp_path: Path) -> None:
    _, _, homes = _fixture(tmp_path)
    source = SimpleNamespace(profile="serenity", profile_route_rejected=False)
    calls: list[str] = []

    class Store:
        def _generate_session_key(self, value: object) -> str:
            assert value is source
            calls.append("key")
            return "agent:main:old-tag-key"

        def lookup_by_session_key(self, key: str) -> object:
            assert key == "agent:main:old-tag-key"
            calls.append("lookup")
            return SimpleNamespace(session_id="existing-session")

    assert (
        existing_session_id("serenity", homes, source, Store(), multiplex=True)
        == "existing-session"
    )
    assert calls == ["key", "lookup"]


def test_existing_session_refuses_unserved_and_rejected_sources_before_store_access(
    tmp_path: Path,
) -> None:
    _, _, homes = _fixture(tmp_path)

    class ForbiddenStore:
        def _generate_session_key(self, _source: object) -> str:
            raise AssertionError("untrusted source reached the store")

    for profile, source in (
        ("ghost", SimpleNamespace(profile="ghost", profile_route_rejected=False)),
        ("serenity", SimpleNamespace(profile="default", profile_route_rejected=False)),
        ("serenity", SimpleNamespace(profile="serenity", profile_route_rejected=True)),
        ("serenity", SimpleNamespace(profile="serenity")),
    ):
        with pytest.raises(ProfileResolutionError):
            existing_session_id(profile, homes, source, ForbiddenStore(), multiplex=True)


def test_existing_session_distinguishes_absent_from_invalid_lookup(tmp_path: Path) -> None:
    _, _, homes = _fixture(tmp_path)
    source = SimpleNamespace(profile="default", profile_route_rejected=False)

    class Store:
        def __init__(self, entry: object) -> None:
            self.entry = entry

        def _generate_session_key(self, _source: object) -> str:
            return "key"

        def lookup_by_session_key(self, _key: str) -> object:
            return self.entry

    assert existing_session_id("default", homes, source, Store(None), multiplex=True) is None
    with pytest.raises(ProfileResolutionError, match="session entry is invalid"):
        existing_session_id(
            "default", homes, source, Store(SimpleNamespace(session_id="")), multiplex=True
        )


def test_standalone_named_profile_requires_unstamped_source(tmp_path: Path) -> None:
    _, _, homes = _fixture(tmp_path)
    named_only = {"serenity": homes["serenity"]}

    class Store:
        def _generate_session_key(self, _source: object) -> str:
            return "agent:main:legacy"

        def lookup_by_session_key(self, _key: str) -> object:
            return SimpleNamespace(session_id="existing")

    unstamped = SimpleNamespace(profile=None, profile_route_rejected=False)
    assert (
        existing_session_id("serenity", named_only, unstamped, Store(), multiplex=False)
        == "existing"
    )
    for source, served in (
        (SimpleNamespace(profile="serenity", profile_route_rejected=False), named_only),
        (unstamped, homes),
    ):
        with pytest.raises(ProfileResolutionError, match="source is not routed"):
            existing_session_id("serenity", served, source, Store(), multiplex=False)
