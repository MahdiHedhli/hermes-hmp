"""Child process for the optional exact-Pantheon-tag HMP adapter fixture.

The parent test pins PYTHONPATH to the archived Hermes tag plus this HMP source and points
HERMES_HOME/XDG_STATE_HOME at disposable scratch directories. This child never starts the
Hermes gateway, but does use the old platform registry and HMP's real TLS listener.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from aiohttp import ClientSession, Fingerprint
from gateway.config import Platform
from gateway.platform_registry import PlatformEntry, platform_registry
from gateway.session import SessionSource, SessionStore, build_session_key
from hermes_cli.profiles import (
    get_active_profile_name,
    get_profile_dir,
    profile_exists,
    profile_matches_home,
    profiles_to_serve,
    validate_profile_name,
)
from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)
from hermes_state import SessionDB

import hmp_plugin
from hmp_plugin.adapter import HmpAdapter
from hmp_plugin.compat import CompatStatus
from hmp_plugin.pantheon_profiles import (
    ProfileResolutionError,
    existing_session_id,
    profile_home,
    served_profile_homes,
)


def _scratch_env(name: str) -> Path:
    path = Path(os.environ[name]).resolve()
    real_home = Path.home().resolve()
    assert path.is_absolute() and path != real_home and real_home not in path.parents
    return path


class RegistryContext:
    def __init__(self) -> None:
        self.cli_registered = False

    def register_platform(self, **kwargs: Any) -> None:
        platform_registry.register(PlatformEntry(**kwargs))

    def register_cli_command(self, **kwargs: Any) -> None:
        assert kwargs["name"] == "hmp"
        self.cli_registered = True


async def main() -> None:
    home = _scratch_env("HERMES_HOME")
    state = _scratch_env("XDG_STATE_HOME")
    (home / "plugin-data" / "hmp" / "instance").mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    # The real old profile helpers are the source of the gateway's served set.
    # The HMP resolver must refuse a ghost name even though this Hermes tag's
    # own _resolve_profile_home_for_source would return the root home for it.
    (home / "profiles" / "serenity").mkdir(parents=True)
    runner = SimpleNamespace(
        config=SimpleNamespace(
            multiplex_profiles=True, multiplex_profile_allowlist=["serenity"]
        ),
        pairing_stores={"default": object(), "serenity": object()},
    )
    profile_api = {
        "profiles_to_serve": profiles_to_serve,
        "get_active_profile_name": get_active_profile_name,
        "get_hermes_home": get_hermes_home,
        "get_profile_dir": get_profile_dir,
        "profile_exists": profile_exists,
        "profile_matches_home": profile_matches_home,
        "validate_profile_name": validate_profile_name,
    }
    homes = served_profile_homes(runner, **profile_api)
    assert set(homes) == {"default", "serenity"}
    assert profile_home("serenity", homes) == get_profile_dir("serenity")
    try:
        profile_home("ghost", homes)
    except ProfileResolutionError:
        pass
    else:
        raise AssertionError("unknown profile resolved to another profile's home")
    runner.pairing_stores.pop("serenity")
    try:
        served_profile_homes(runner, **profile_api)
    except ProfileResolutionError:
        pass
    else:
        raise AssertionError("profile was offered before authorization state was ready")
    runner.pairing_stores["serenity"] = object()
    runner.config.multiplex_profile_allowlist = []
    assert set(served_profile_homes(runner, **profile_api)) == {"default"}
    runner.config.multiplex_profiles = False
    assert set(served_profile_homes(runner, **profile_api)) == {"default"}
    runner.config.multiplex_profiles = True
    # A named primary is served by the live gateway even if the secondary
    # allowlist omits it. The old helper returns only default in that case.
    token = set_hermes_home_override(get_profile_dir("serenity"))
    try:
        assert get_active_profile_name() == "serenity"
        assert set(served_profile_homes(runner, **profile_api)) == {"default", "serenity"}
        runner.config.multiplex_profiles = False
        assert set(served_profile_homes(runner, **profile_api)) == {"serenity"}
    finally:
        reset_hermes_home_override(token)
    runner.config.multiplex_profiles = True
    runner.config.multiplex_profile_allowlist = ["serenity"]

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    registration = RegistryContext()
    hmp_plugin.register(registration)
    assert registration.cli_registered

    # In this tag, standalone gateways use the legacy `agent:main` session namespace even when
    # their active profile is named. A read adapter must not always pass the profile name to
    # build_session_key: that would miss a real standalone Bot Chat. Use the old store's own
    # key generator as the authority, without creating a store or touching state.db.
    source = SessionSource(
        platform=Platform("hmp"), chat_id="probe", chat_type="dm", user_id="probe",
        profile="serenity",
    )
    session_store = object.__new__(SessionStore)
    session_store.config = SimpleNamespace(
        multiplex_profiles=False,
        group_sessions_per_user=True,
        thread_sessions_per_user=False,
    )
    assert session_store._generate_session_key(source) == build_session_key(source, profile=None)
    assert session_store._generate_session_key(source) != build_session_key(
        source, profile="serenity"
    )
    session_store.config.multiplex_profiles = True
    assert session_store._generate_session_key(source) == build_session_key(
        source, profile="serenity"
    )

    # Exercise the unwired HMP lookup primitive against the tag's real key
    # generator in both modes. The routing lookup is a sentinel: this probe
    # must not create a Hermes session or touch the gateway's routing file.
    source.profile_route_rejected = False

    class Lookup:
        def __init__(self, expected: str) -> None:
            self.expected = expected

        def _generate_session_key(self, inbound: SessionSource) -> str:
            return session_store._generate_session_key(inbound)

        def lookup_by_session_key(self, key: str) -> SimpleNamespace:
            assert key == self.expected
            return SimpleNamespace(session_id="existing-only")

    for multiplex, namespace in ((False, None), (True, "serenity")):
        session_store.config.multiplex_profiles = multiplex
        source.profile = "serenity" if multiplex else None
        served = homes if multiplex else {"serenity": homes["serenity"]}
        expected_key = build_session_key(source, profile=namespace)
        assert (
            existing_session_id(
                "serenity", served, source, Lookup(expected_key), multiplex=multiplex
            )
            == "existing-only"
        )
    source.profile_route_rejected = True
    try:
        existing_session_id("serenity", homes, source, Lookup("unused"), multiplex=True)
    except ProfileResolutionError:
        pass
    else:
        raise AssertionError("rejected route reached session lookup")

    # The old SessionDB offers a read-only constructor. Confirm it refuses a missing file and
    # that profile-scoped history reads leave both scratch databases and sidecars byte-for-byte
    # unchanged. This is a storage/profile primitive, not full Bot Chat qualification.
    missing_db = state / "missing-state.db"
    try:
        SessionDB(missing_db, read_only=True)
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError("read-only SessionDB opened a missing database")
    assert not missing_db.exists()

    def contents(profile_home: Path) -> dict[str, str]:
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in profile_home.iterdir()
            if path.is_file() and path.name.startswith("state.db")
        }

    expected = {
        "default": "synthetic primary history row",
        "serenity": "synthetic named history row",
    }
    for profile, text in expected.items():
        read_db = profile_home(profile, homes) / "state.db"
        writer = SessionDB(read_db)
        try:
            writer.create_session("shared-session", source="hmp")
            writer.append_message("shared-session", "assistant", text)
        finally:
            writer.close()

    before = {profile: contents(profile_home(profile, homes)) for profile in expected}
    assert all(files for files in before.values())
    for profile, text in expected.items():
        read_db = profile_home(profile, homes) / "state.db"
        reader = SessionDB(read_db, read_only=True)
        try:
            rows = reader.get_messages("shared-session")
            assert [row["content"] for row in rows] == [text]
            assert reader.get_session("shared-session")["id"] == "shared-session"
            assert reader.resolve_resume_session_id("shared-session") == "shared-session"
            assert reader.get_compression_lineage("shared-session") == ["shared-session"]
            assert reader.get_active_message_ids("shared-session") == [rows[0]["id"]]
            listed = reader.list_sessions_rich(
                limit=10, include_hidden=True, order_by_last_active=True,
                project_compression_tips=True,
            )
            assert [row["id"] for row in listed] == ["shared-session"]
        finally:
            reader.close()
    assert {profile: contents(profile_home(profile, homes)) for profile in expected} == before

    # A real compression parent/child tests the old lineage and tip APIs,
    # which are different from the current split SessionDB's API. This still
    # runs wholly in disposable profile databases and must not alter them on
    # the read pass.
    for profile in expected:
        read_db = profile_home(profile, homes) / "state.db"
        writer = SessionDB(read_db)
        try:
            writer.create_session("compressed-root", source="hmp")
            writer.append_message("compressed-root", "user", "synthetic before")
            writer.end_session("compressed-root", "compression")
            writer.create_session(
                "compressed-child", source="hmp", parent_session_id="compressed-root"
            )
            writer.append_message("compressed-child", "assistant", "synthetic after")
        finally:
            writer.close()
    before_lineage = {
        profile: contents(profile_home(profile, homes)) for profile in expected
    }
    for profile in expected:
        read_db = profile_home(profile, homes) / "state.db"
        reader = SessionDB(read_db, read_only=True)
        try:
            assert reader.get_compression_lineage("compressed-root") == [
                "compressed-root", "compressed-child"
            ]
            assert reader.resolve_resume_session_id("compressed-root") == "compressed-child"
            assert reader.get_active_message_ids("compressed-child")
        finally:
            reader.close()
    assert {
        profile: contents(profile_home(profile, homes)) for profile in expected
    } == before_lineage

    adapter = platform_registry.create_adapter(
        "hmp", SimpleNamespace(extra={"bind": "127.0.0.1", "port": port})
    )
    assert isinstance(adapter, HmpAdapter)
    try:
        assert await adapter.connect()
        listener = adapter._server
        assert listener is not None and listener.bound is not None
        assert listener.ctx.compat.status is CompatStatus.UNSUPPORTED
        assert listener.ctx.bridge is None and listener.ctx.reads is None
        assert "hmp_plugin.bridge" not in sys.modules

        # Pin the self-signed listener certificate to the exact HMP instance for this fixture.
        pin = Fingerprint(hashlib.sha256(listener.ctx.identity.certificate_der()).digest())
        base = f"https://127.0.0.1:{listener.bound[1]}/hmp/v1"
        async with ClientSession() as client:
            async with client.get(base + "/ready", ssl=pin) as response:
                assert response.status == 200
                assert (await response.json())["write_gate"]["state"] == "closed"
            async with client.get(base + "/bots", ssl=pin) as response:
                assert response.status == 503
                assert (await response.json())["error"]["why"] == "hermes_build_unsupported"
    finally:
        await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
