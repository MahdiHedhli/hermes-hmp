#!/usr/bin/env python3
"""Hermes-aware worker for the flag-less profile history fixture (specs/005 open item C6).

Test tooling, not part of the plugin: `server/hmp_plugin` never imports it. It runs in a fresh
child process under the target build's own interpreter, with an isolated `HERMES_HOME`, and uses
Hermes' own `load_gateway_config`, `GatewayRunner`, `SessionStore`, `SessionDB`,
`build_session_key`, `canonical_identity` and route matcher. Only adapter plumbing that is
unrelated to storage, key generation, routing or the lookup under test is replaced: an
`hmp`-named platform registry entry, an adapter subclass with no network, and the chat-id
directory. Every message and id is synthetic.

Phases (each prints one JSON object with counts and booleans only; no ids, no text):

- `seed-standalone`: a standalone gateway of the named profile (`HERMES_HOME` is the profile
  home, no multiplex) creates a session through its own `SessionStore` and appends messages.
- `seed-routed`: the root multiplexing gateway creates a session for an exact routed source through
  its shared `SessionStore`, inside the profile's runtime scope, as inbound traffic does.
- `read`: a fresh root gateway state (new `GatewayRunner`, new `SessionStore` loaded from disk)
  answers the real `HermesReadBridge` reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_DIR = REPO_ROOT / "server"


def _out(payload: dict[str, Any]) -> None:
    payload["blocked_network_attempts"] = _BLOCKED_NETWORK
    installs = Path(os.environ["HERMES_HOME"]) / "installs"
    payload["runtime_bootstrap_dir_created"] = installs.exists()
    print(json.dumps(payload, sort_keys=True))


def _digest(value: str | None) -> str | None:
    return None if value is None else hashlib.sha256(value.encode()).hexdigest()[:16]


_BLOCKED_NETWORK = 0


def _block_network() -> None:
    """Refuse every non-local socket connection and count the attempts. Gateway startup must not
    reach the network in this fixture (no dependency bootstrap, no download, no model call)."""
    import socket

    real_connect = socket.socket.connect

    def guarded(self: Any, address: Any) -> Any:
        global _BLOCKED_NETWORK
        if self.family == getattr(socket, "AF_UNIX", None):
            return real_connect(self, address)
        _BLOCKED_NETWORK += 1
        raise OSError("network is blocked in this fixture")

    socket.socket.connect = guarded  # type: ignore[method-assign]


def _isolate(home: str) -> None:
    for key in list(os.environ):
        if key.startswith(("HERMES_", "XDG_")):
            del os.environ[key]
    os.environ["HERMES_HOME"] = home
    # Gateway startup otherwise starts a background download of an optional security scanner.
    os.environ["TIRITH_ENABLED"] = "false"
    _block_network()
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))


def _register_platform() -> Any:
    from gateway.config import Platform
    from gateway.platform_registry import PlatformEntry, platform_registry

    platform_registry.register(
        PlatformEntry(
            name="hmp",
            label="HMP fixture",
            adapter_factory=lambda _cfg: None,
            check_fn=lambda: True,
            source="plugin",
        )
    )
    return Platform("hmp")


def _adapter_class() -> Any:
    from gateway.platforms.base import BasePlatformAdapter

    class FixtureAdapter(BasePlatformAdapter):
        """No network. Inherits the real `build_source`, which asks the runner's real route
        matcher to stamp the profile."""

        async def connect(self, *, is_reconnect: bool = False) -> bool:  # pragma: no cover
            return True

        async def disconnect(self) -> None:  # pragma: no cover
            return None

        async def send(self, chat_id: str, content: str, reply_to: Any = None, **kw: Any) -> Any:
            raise NotImplementedError  # pragma: no cover

        async def get_chat_info(self, chat_id: str) -> dict[str, Any]:  # pragma: no cover
            return {"name": chat_id, "type": "dm"}

    return FixtureAdapter


def _root_gateway(platform: Any) -> tuple[Any, Any]:
    """The root multiplexing runner and its adapter, built the way gateway boot does: config from
    the root home, one shared `SessionStore`, served profiles from `profiles_to_serve`."""
    from gateway.config import PlatformConfig, load_gateway_config
    from gateway.run import GatewayRunner
    from hermes_cli.profiles import profiles_to_serve

    config = load_gateway_config()
    runner = GatewayRunner(config)
    runner._note_served_profiles(profiles_to_serve(bool(config.multiplex_profiles)))
    adapter = _adapter_class()(PlatformConfig(enabled=True), platform)
    adapter.gateway_runner = runner
    runner.adapters[platform] = adapter
    adapter.set_session_store(runner.session_store)
    return runner, adapter


def _messages(count: int) -> list[dict[str, str]]:
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"synthetic message {i + 1}"}
        for i in range(count)
    ]


def cmd_seed_standalone(args: argparse.Namespace) -> None:
    profile_home = Path(args.root_home) / "profiles" / args.profile
    _isolate(str(profile_home))
    platform = _register_platform()
    from gateway.config import load_gateway_config
    from gateway.session import SessionSource, SessionStore

    config = load_gateway_config()
    store = SessionStore(config.sessions_dir, config)
    source = SessionSource(platform=platform, chat_id=args.chat, user_id=args.user, chat_type="dm")
    entry = store.get_or_create_session(source)
    for message in _messages(args.messages):
        store.append_to_transcript(entry.session_id, message)
    _out(
        {
            "own_multiplex_flag_as_loaded": config.multiplex_profiles,
            "key_namespace": entry.session_key.split(":")[1],
            "session_digest": _digest(entry.session_id),
            "messages": args.messages,
        }
    )


def cmd_seed_routed(args: argparse.Namespace) -> None:
    _isolate(args.root_home)
    platform = _register_platform()
    from gateway.run import _profile_runtime_scope
    from gateway.session_identity import canonical_identity

    runner, adapter = _root_gateway(platform)
    source = adapter.build_source(
        chat_id=args.chat,
        chat_type="dm",
        user_id=args.user,
        scope_id=args.profile,
        guild_id=args.profile,
    )
    canonical_identity(source, runner=runner, adapter=adapter)
    home = runner._routed_profile_home(args.profile)
    with _profile_runtime_scope(Path(home)):
        entry = runner.session_store.get_or_create_session(source, force_new=args.force_new)
        for message in _messages(args.messages):
            runner.session_store.append_to_transcript(entry.session_id, message)
    _out(
        {
            "root_multiplex": runner.config.multiplex_profiles,
            "source_profile_matches": source.profile == args.profile,
            "route_rejected": source.profile_route_rejected,
            "key_namespace": entry.session_key.split(":")[1],
            "session_digest": _digest(entry.session_id),
            "messages": args.messages,
        }
    )


class _Directory:
    """The HMP chat-id mapping is HMP store plumbing, not under test."""

    def __init__(self, chat: str) -> None:
        self._chat = chat

    def chat_id(self, user_id: str, profile: str) -> str | None:
        return self._chat

    def operator_label(self, user_id: str) -> str | None:
        return None


def _attempt(fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "value": fn()}
    except Exception as exc:  # the bridge raises BridgeError on any Hermes failure
        return {"ok": False, "error": type(exc).__name__}


def cmd_read(args: argparse.Namespace) -> None:
    _isolate(args.root_home)
    platform = _register_platform()
    runner, adapter = _root_gateway(platform)
    from hmp_plugin.bridge import HermesReadBridge

    bridge = HermesReadBridge(adapter, _Directory(args.chat))
    served = bridge.served_profiles()
    result: dict[str, Any] = {
        "profile_served": args.profile in served,
        "root_multiplex": runner.config.multiplex_profiles,
        "route_count": len(runner.config.profile_routes),
    }

    # Surface 1: the canonical conversation the Phone opens for this bot. `Reads.snapshot` is
    # `conversation_ref` + `lineage` + `latest`; `Reads.history` is `conversation_ref` + `lineage`
    # + `after`. The gate (authorization) is not part of this fixture.
    ref = _attempt(lambda: bridge.conversation_ref(args.user, args.profile))
    result["canonical_ref_resolved"] = ref["ok"] and ref["value"] is not None
    result["canonical_ref_error"] = None if ref["ok"] else ref["error"]
    if result["canonical_ref_resolved"]:
        cref = ref["value"]
        lineage = bridge.lineage(cref)
        snapshot = bridge.latest(cref, 50)
        history = bridge.after(cref, 0, 50)
        result["canonical_session_digest"] = _digest(cref.session_id)
        result["canonical_snapshot_rows"] = len(snapshot)
        result["canonical_history_rows"] = len(history) if isinstance(history, list) else None
        result["canonical_active_rows"] = lineage.active_row_count
        result["canonical_head_is_newest"] = (
            bool(snapshot) and lineage.head_row_id == snapshot[-1].id
        )
        result["canonical_roles"] = [row.role for row in snapshot]
    else:
        result.update(
            canonical_session_digest=None,
            canonical_snapshot_rows=0,
            canonical_history_rows=0,
            canonical_active_rows=0,
        )

    # Surface 2: the id-addressed session read (Phone session browse: `list_sessions`,
    # `resolve_session`, then `lineage`/`latest`/`after` on the resolved ref). It reads the
    # profile's own `state.db` by session id and never consults the `SessionStore` routing key.
    listed = _attempt(
        lambda: bridge.list_sessions(
            args.user, args.profile, sources_excluded=(), limit=50, offset=0
        )
    )
    result["browse_list_error"] = None if listed["ok"] else listed["error"]
    summaries = listed["value"] if listed["ok"] else []
    result["browse_sessions_listed"] = len(summaries)
    from hmp_plugin.reads import _is_bot_view_session

    own_session_id = ref["value"].session_id if result["canonical_ref_resolved"] else None
    browse: list[dict[str, Any]] = []
    for summary in summaries:
        resolved = bridge.resolve_session(args.user, args.profile, summary.session_id)
        rows = bridge.latest(resolved, 50) if resolved is not None else []
        browse.append(
            {
                "session_digest": _digest(summary.session_id),
                "resolved": resolved is not None,
                "rows": len(rows),
                "message_count": summary.message_count,
                # `Reads.list_sessions` keeps only the caller's own canonical session and the
                # bot's hidden "Bot Chat"; this is that same predicate, not a second rule.
                "phone_list_visible": summary.session_id == own_session_id
                or _is_bot_view_session(summary),
            }
        )
    result["browse"] = sorted(browse, key=lambda item: item["session_digest"] or "")
    _out(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    for name, fn in (
        ("seed-standalone", cmd_seed_standalone),
        ("seed-routed", cmd_seed_routed),
        ("read", cmd_read),
    ):
        p = sub.add_parser(name)
        p.add_argument("--root-home", required=True)
        p.add_argument("--profile", required=True)
        p.add_argument("--user", required=True)
        p.add_argument("--chat", required=True)
        p.add_argument("--messages", type=int, default=4)
        p.add_argument("--force-new", action="store_true")
        p.set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
