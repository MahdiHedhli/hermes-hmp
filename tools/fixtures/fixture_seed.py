#!/usr/bin/env python3
"""Hermes/`hmp_plugin`-aware fixture seeding worker (T060 `build_fixture.py`, T062 `mutate.py`).

This script is test tooling, not part of the HMP plugin: it lives under `tools/fixtures/` and
`server/hmp_plugin` never imports it (`tools/ci/check_plugin_surface.py`, T013). It is always run
as a subprocess under the *target Hermes build's own* venv python, with that build's `server/` on
`PYTHONPATH` (see `_fixture_common.run_seed_script`), because it needs both `hermes_constants`
(the one Hermes import `hmp_plugin.identity` makes) and the build's own `hermes_state`/
`gateway.session` modules for message seeding — imports that only resolve inside that build's own
environment.

Per contracts/fixture-format.md rule 3: "Messages and session bindings are written through the
target build's own `SessionDB` and `SessionStore` APIs, offline (gateway stopped)." HMP users and
chat bindings go through the HMP plugin's own `store.py` (rule 2/`tasks.md` T060).

Every subcommand takes `--home` (the instance's isolated `HERMES_HOME`, root — never a named
profile: HMP identity binds only at the root, ID-2) and, when it touches HMP identity/store,
`--xdg-state` (the identity binding root, OUTSIDE every Hermes home — see
`_fixture_common.InstancePaths`). Neither is ever read from the environment: this script is also
invoked later, unattended, by the Dart real-server tests (`fixture_pairing_cli.py` is its sibling
for P1-P4 device pairing; this script only ever does P6 bot authorization and Hermes-side session
seeding).
"""

from __future__ import annotations

import argparse
import faulthandler
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_DIR = REPO_ROOT / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


# Opt-in `--diagnostic-stacks`: one nonfatal all-thread Python stack dump to stderr if the
# subcommand is still running after this many seconds (below `run_seed_script`'s 120 s deadline).
# Not a signal handler, no core, no locals/env/argv. Sensitive stderr: capture it privately only.
_DIAGNOSTIC_STACK_SECONDS = 90.0


def _out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload))


def _fail(message: str) -> None:
    _out({"ok": False, "error": message})
    sys.exit(1)


def _set_env(home: str) -> None:
    # hermes_constants reads HERMES_HOME from the environment at call time; every HERMES_*/XDG_*
    # var this process may have inherited is cleared first (fixture-format.md rule 1).
    for key in list(os.environ):
        if key.startswith("HERMES_") or key.startswith("XDG_"):
            del os.environ[key]
    os.environ["HERMES_HOME"] = home


def _hmp_store(home: str, xdg_state: str):
    """Open (migrating if needed) the HMP plugin's own store for `home`. Read-write. Never loads
    or creates instance identity — only `identity.resolve_custody()` (writes nothing) to locate
    the store path, matching `server/hmp_plugin/adapter.py`'s `open_components` ordering.

    `identity.default_binding_root()` appends its own fixed `BINDING_ROOT_NAME` ("hermes-hmp")
    suffix to `$XDG_STATE_HOME`; the live gateway (`adapter.py`'s `open_components`, no explicit
    kwargs) always goes through that function. This helper sets `XDG_STATE_HOME` and leaves
    `binding_root` unset so `resolve_custody` derives the SAME suffixed path the same way --
    passing `--xdg-state` straight through as `binding_root=` would silently point at a sibling
    directory the live gateway never reads or writes, which is exactly the identity-mismatch bug
    this comment is here to stop someone from reintroducing.
    """
    _set_env(home)
    os.environ["XDG_STATE_HOME"] = xdg_state
    from hmp_plugin import identity
    from hmp_plugin import server as hmp_server
    from hmp_plugin.store import Store

    custody = identity.resolve_custody(hermes_root=Path(home))
    store = Store(hmp_server.store_path(custody.anchor_dir))
    store.migrate()
    return store


def cmd_insert_user(args: argparse.Namespace) -> None:
    store = _hmp_store(args.home, args.xdg_state)
    try:
        store.insert_user(args.user_id, args.label, int(time.time()))
    except sqlite3.IntegrityError:
        pass  # already present -- idempotent from the caller's point of view
    finally:
        store.close()
    _out({"ok": True, "user_id": args.user_id})


def cmd_set_chat(args: argparse.Namespace) -> None:
    store = _hmp_store(args.home, args.xdg_state)
    try:
        store.set_chat(args.user_id, args.profile, "default", args.chat_id)
    finally:
        store.close()
    _out({"ok": True, "chat_id": args.chat_id})


def cmd_p6_generate(args: argparse.Namespace) -> None:
    """Offline P6 setup step 1: mint a pairing code for platform "hmp" scoped to *profile*, exactly
    as a live inbound HMP message would (fixture-format.md rule 2's "supported operator path").
    Prints the `request_id` `hermes -p <profile> pairing approve hmp <request_id>` needs; the
    caller runs that real CLI command itself (the actual "approval through the Hermes CLI")."""
    _set_env(args.home)
    from gateway.pairing import PairingStore

    store = PairingStore(profile=args.profile)
    code = store.generate_code("hmp", args.user_id, args.label)
    if code is None:
        _fail(
            f"could not generate a pairing code for user {args.user_id!r} "
            f"on profile {args.profile!r}"
        )
    matches = [
        p for p in store.list_pending("hmp") if p["user_id"] == args.user_id and p["request_id"]
    ]
    if not matches:
        _fail("generated a pairing code but it is not visible in list_pending() afterwards")
    request_id = sorted(matches, key=lambda p: p["age_minutes"])[0]["request_id"]
    _out({"ok": True, "request_id": request_id})


def cmd_find_pending_request(args: argparse.Namespace) -> None:
    """T035: find the `request_id` of a pending "hmp" pairing request that a LIVE P6 trigger
    (`POST /hmp/v1/bots/{profile}/authorize`, `authorize.py`'s `request_authorization` bridge
    call) already created, scoped to *profile* and *user_id* -- the read-only half of
    `cmd_p6_generate` above, without its `generate_code` call, since the live route already
    generated the code itself (inside Hermes's own DM-reply handling; PR6-2 says HMP never sees
    or relays it). Used by the reference-client integration test to find the id the real
    `hermes -p <profile> pairing approve hmp <request_id>` CLI needs, the same way a human
    operator would from `hermes -p <profile> pairing list` -- `PairingStore.list_pending()` never
    returns the code itself (`gateway/pairing.py`), only `request_id`, so this cannot leak it."""
    _set_env(args.home)
    from gateway.pairing import PairingStore

    store = PairingStore(profile=args.profile)
    matches = [
        p for p in store.list_pending("hmp") if p["user_id"] == args.user_id and p["request_id"]
    ]
    if not matches:
        _fail(
            f"no pending 'hmp' pairing request for user {args.user_id!r} "
            f"on profile {args.profile!r} (was the live P6 trigger sent?)"
        )
    request_id = sorted(matches, key=lambda p: p["age_minutes"])[0]["request_id"]
    _out({"ok": True, "request_id": request_id})


def cmd_get_pending_code_hash(args: argparse.Namespace) -> None:
    """T035 (SEC-11 regression fix): read-only fetch of a pending "hmp" pairing request's stored
    salted hash of its code -- never the plaintext code itself. `gateway/pairing.py`'s
    `PairingStore` persists only `sha256(salt + code)` for a generated code
    (`generate_code`/`_hash_code`); `list_pending()` does not expose even that, so this reads the
    platform's own `{platform}-pending.json` the same way `PairingStore` itself does internally
    (`_load_json(_pending_path(...))`), purely to look, never to mutate.

    This lets the reference-client integration test (`test_pairing_code_never_relayed`) check
    whether a specific string it found in a response body, CLI output or log IS the exact code
    that was issued for *request_id* -- by hashing the candidate with the same salt and comparing
    -- without the test process ever needing (or being able) to see the plaintext code, exactly
    the property PR6-2 requires of everyone else too. Must be called before the request is
    approved or denied: approval deletes the pending entry (`PairingStore._finish_approval`)."""
    _set_env(args.home)
    from gateway.pairing import PairingStore

    store = PairingStore(profile=args.profile)
    pending = store._load_json(store._pending_path("hmp"))  # read-only, never mutates
    entry = pending.get(args.request_id)
    if not isinstance(entry, dict) or "hash" not in entry or "salt" not in entry:
        _fail(
            f"no pending 'hmp' request {args.request_id!r} with a stored hash/salt "
            "(already approved/denied, or never existed)"
        )
    _out({"ok": True, "hash": entry["hash"], "salt": entry["salt"]})


def _ensure_platform_registered() -> None:
    from hermes_cli.plugins import discover_plugins

    discover_plugins(force=True)
    from gateway.config import Platform

    Platform("hmp")  # raises if the plugin failed to register -- fail loudly, not silently


def _messages_from_file(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("messages file must contain a JSON array of {role, text} objects")
    return [{"role": m["role"], "content": m["text"]} for m in data]


def _root_session_store(home: str):
    """`SessionStore`'s routing index is anchored to whatever `HERMES_HOME`/override is active at
    CONSTRUCTION time ("the routing index needs exactly one home for its lifetime: the gateway's
    own, captured before any profile scope exists" -- `gateway/session.py`'s `SessionStore.
    __init__`), and the live gateway always constructs its one, process-wide `SessionStore` at
    ROOT, before entering any per-request profile scope. Constructing it here while already
    scoped to a named profile's home (as `set_hermes_home_override` does for `fixture_seed.py`'s
    other commands) anchors the routing index inside that PROFILE's own `sessions/` directory
    instead -- a routing index the live gateway's `_session_store` never reads from, so
    `bridge.py`'s `lookup_by_session_key` finds nothing even though the profile's `state.db` has
    the real, correctly-labelled rows. This constructs it BEFORE any override, exactly matching
    gateway boot, so profile-scoping only ever wraps the `get_or_create_session` CALL."""
    from gateway.config import load_gateway_config
    from gateway.session import SessionStore

    cfg = load_gateway_config()
    return SessionStore(Path(home) / "sessions", cfg)


def _get_or_create_session(store, profile: str, user_id: str, chat_id: str, *, force_new: bool):
    from gateway.config import Platform
    from gateway.session import SessionSource

    source = SessionSource(
        platform=Platform("hmp"), chat_id=chat_id, user_id=user_id, chat_type="dm", profile=profile
    )
    return store.get_or_create_session(source, force_new=force_new)


def cmd_seed_messages(args: argparse.Namespace) -> None:
    """Create (or reuse) the Hermes session for (profile, user, chat) and append *messages_file*'s
    messages to it, offline, via `SessionStore`/`SessionDB` directly (fixture-format.md rule 3).
    Used by `build_fixture.py` for the manifest's `conversations`, and by `mutate.py`'s `append`
    mutation (T062) when `--force-new` is not given."""
    _set_env(args.home)
    _ensure_platform_registered()
    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )
    from hermes_state import SessionDB

    profile_dir = Path(args.home) / "profiles" / args.profile
    store = _root_session_store(args.home)  # BEFORE any profile override -- see its docstring
    token = set_hermes_home_override(str(profile_dir))
    try:
        entry = _get_or_create_session(
            store, args.profile, args.user_id, args.chat_id, force_new=args.force_new
        )
        session_id = entry.session_id
        db = SessionDB(profile_dir / "state.db")
        try:
            messages = _messages_from_file(args.messages_file)
            for msg in messages:
                db.append_message(session_id, role=msg["role"], content=msg["content"])
        finally:
            db.close()
    finally:
        reset_hermes_home_override(token)
    _out({"ok": True, "session_id": session_id})


def cmd_compact(args: argparse.Namespace) -> None:
    """T062 `rewrite`/`in_place_compaction` mutation: archive the active rows of *session_id* and
    insert *messages_file*'s messages as fresh rows under the SAME session id (RO-8 (a)/(b):
    "new row ids, same session")."""
    _set_env(args.home)
    _ensure_platform_registered()
    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )
    from hermes_state import SessionDB

    profile_dir = Path(args.home) / "profiles" / args.profile
    token = set_hermes_home_override(str(profile_dir))
    try:
        db = SessionDB(profile_dir / "state.db")
        try:
            messages = _messages_from_file(args.messages_file)
            new_count = db.archive_and_compact(args.session_id, messages)
        finally:
            db.close()
    finally:
        reset_hermes_home_override(token)
    _out({"ok": True, "session_id": args.session_id, "active_count": new_count})


def cmd_new_session(args: argparse.Namespace) -> None:
    """T062 `new_session`/`session_replaced` mutation: force a fresh session id for the same
    (profile, user, chat) routing key (RO-6's "/new-equivalent"), leaving the old session ended."""
    _set_env(args.home)
    _ensure_platform_registered()
    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )

    profile_dir = Path(args.home) / "profiles" / args.profile
    store = _root_session_store(args.home)  # BEFORE any profile override -- see its docstring
    token = set_hermes_home_override(str(profile_dir))
    try:
        entry = _get_or_create_session(
            store, args.profile, args.user_id, args.chat_id, force_new=True
        )
    finally:
        reset_hermes_home_override(token)
    _out({"ok": True, "session_id": entry.session_id})


def cmd_append(args: argparse.Namespace) -> None:
    """T062 `append` mutation: append *messages_file*'s messages to an already-known session id,
    without touching session routing at all."""
    _set_env(args.home)
    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )
    from hermes_state import SessionDB

    profile_dir = Path(args.home) / "profiles" / args.profile
    token = set_hermes_home_override(str(profile_dir))
    try:
        db = SessionDB(profile_dir / "state.db")
        try:
            messages = _messages_from_file(args.messages_file)
            for msg in messages:
                db.append_message(args.session_id, role=msg["role"], content=msg["content"])
        finally:
            db.close()
    finally:
        reset_hermes_home_override(token)
    _out({"ok": True, "session_id": args.session_id, "appended": len(messages)})


def cmd_seed_session(args: argparse.Namespace) -> None:
    """Amendment A1 (session browsing, OD-F9/OD-F10): create (or upsert) a session that is NOT
    routed through any HMP chat -- a synthetic stand-in for a Desktop-, CLI-, cron- or other
    non-mobile-originated session, so `SessionDB.list_sessions_rich` has more than one `source`
    to list for the same bot (`server-modules.md`, HMP_V1.md §6a). Writes directly through the
    target build's own `SessionDB.create_session`/`set_session_title`/`set_session_archived`/
    `set_session_hidden`/`end_session` (fixture-format.md rule 3): no `SessionStore` routing, no
    HMP chat id, no P6 approval -- these sessions are visible only through the SAME bot-level
    authorization every other session of that profile already requires (OD-F10: no per-session
    grant exists in Hermes).

    `--parent-session-id` plus `--end-reason compression` on the PARENT'S OWN seeding call is how
    a compression lineage is built: seed the root, end it with `end_reason=compression`, then seed
    the tip with `--parent-session-id <root>` -- `get_compression_chain`/`_project_compression_
    tips` walk forward from a `end_reason='compression'` parent to its child exactly as a real
    Hermes compaction does (`hermes_state_sessions.py`, independently read for this amendment).
    """
    _set_env(args.home)
    from hermes_constants import (
        reset_hermes_home_override,
        set_hermes_home_override,
    )
    from hermes_state import SessionDB

    profile_dir = Path(args.home) / "profiles" / args.profile
    token = set_hermes_home_override(str(profile_dir))
    try:
        db = SessionDB(profile_dir / "state.db")
        try:
            db.create_session(
                args.session_id,
                args.source,
                parent_session_id=args.parent_session_id,
            )
            if args.messages_file:
                messages = _messages_from_file(args.messages_file)
                for msg in messages:
                    db.append_message(args.session_id, role=msg["role"], content=msg["content"])
            if args.title is not None:
                db.set_session_title(args.session_id, args.title)
            if args.archived:
                db.set_session_archived(args.session_id, True)
            if args.hidden:
                db.set_session_hidden(args.session_id, True)
            if args.end_reason:
                db.end_session(args.session_id, args.end_reason)
        finally:
            db.close()
    finally:
        reset_hermes_home_override(token)
    _out({"ok": True, "session_id": args.session_id})


def cmd_acquire_lease(args: argparse.Namespace) -> None:
    """F2 direct-send fixture support (HMP_V1.md §7a DS-4(3), T-N015/T-N016): acquire a real
    lease-registry slot for `--session-id`, in the TARGET PROFILE's own registry home (matching
    `bridge.lease_snapshot`'s own `registry_home` scoping), via the build's own
    `hermes_cli.active_sessions.try_acquire_active_session` -- the exact primitive `direct_send.
    py`'s DS-4(3) guard reads back through `active_session_registry_snapshot`. Deliberately run
    WHILE the gateway may be live (a lease represents "someone is using this session right now",
    unlike a `SessionDB`/`SessionStore` write, so this is not `fixture-format.md` rule 3's
    "offline" case).

    `active_session_registry_snapshot` prunes any lease whose OWNING PROCESS is no longer alive
    (`_prune_dead`'s PID liveness check, even leniently for a non-`track_liveness` lease like this
    one) -- so this command prints its one JSON result line, flushes, and then BLOCKS (reading
    stdin, which the parent closes to signal "release now") rather than exiting, exactly mirroring
    a real stuck writer that is still a live process. The caller starts this as a background
    process (never `subprocess.run`) and kills it when the test is done with the synthetic busy
    state -- `hermes_cli.active_sessions.release_active_session` is not called here at all; the
    lease disappears when this process's own PID does, which is the fixture's actual test
    condition."""
    _set_env(args.home)
    from hermes_cli.active_sessions import try_acquire_active_session

    profile_dir = Path(args.home) / "profiles" / args.profile
    metadata = None
    if args.desktop_held:
        # The lease Hermes treats as a live Bot Chat mailbox owner
        # (`find_canonical_live_owner`): HMP's DS-4 exempts it, and `api_server` admits the
        # turn to that mailbox instead of running it locally.
        metadata = {
            "bot_live_delivery_consumer": True,
            "live_session_id": args.session_id,
        }
    lease, refusal = try_acquire_active_session(
        session_id=args.session_id, surface=args.surface, config={},
        registry_home=profile_dir, metadata=metadata,
    )
    if lease is None:
        _fail(f"acquire-lease refused: {refusal}")
    _out({"ok": True, "session_id": args.session_id, "lease_id": lease.lease_id})
    sys.stdout.flush()
    sys.stdin.readline()  # blocks until the parent closes/writes to stdin, or is killed


def cmd_compat_identity(args: argparse.Namespace) -> None:
    """The GU-2c build identity (fingerprint, git_sha) of THIS venv's Hermes install, computed by
    the real `compat.default_gate()` -- the exact code path the live gateway and `hermes hmp
    compat` use. No `--home` needed: identity is a property of the Hermes source tree, not of any
    instance. Used by `build_fixture.py` to check (never silently assume) whether a build is
    listed in `read_compat_builds.json` before bootstrapping a fixture-provenance entry for it
    (see that script's docstring and this task's final report)."""
    del args
    from hmp_plugin import compat

    result = compat.default_gate().evaluate()
    identity = result.identity
    _out(
        {
            "ok": True,
            "supported": result.supported,
            "why": getattr(result.why, "value", None),
            "fingerprint": identity.fingerprint if identity else None,
            "git_sha": identity.git_sha if identity else None,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diagnostic-stacks", action="store_true",
        help="before the subcommand: dump all Python thread stacks to stderr once, nonfatally, "
        f"after {_DIAGNOSTIC_STACK_SECONDS:g} s if still running (stderr is sensitive)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _home_xdg(p: argparse.ArgumentParser) -> None:
        p.add_argument("--home", required=True)
        p.add_argument("--xdg-state", required=True)

    p = sub.add_parser("insert-user")
    _home_xdg(p)
    p.add_argument("--user-id", required=True)
    p.add_argument("--label", required=True)
    p.set_defaults(func=cmd_insert_user)

    p = sub.add_parser("set-chat")
    _home_xdg(p)
    p.add_argument("--user-id", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--chat-id", required=True)
    p.set_defaults(func=cmd_set_chat)

    p = sub.add_parser("p6-generate")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--label", required=True)
    p.set_defaults(func=cmd_p6_generate)

    p = sub.add_parser("find-pending-request")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--user-id", required=True)
    p.set_defaults(func=cmd_find_pending_request)

    p = sub.add_parser("get-pending-code-hash")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--request-id", required=True)
    p.set_defaults(func=cmd_get_pending_code_hash)

    p = sub.add_parser("seed-messages")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--chat-id", required=True)
    p.add_argument("--messages-file", required=True)
    p.add_argument("--force-new", action="store_true")
    p.set_defaults(func=cmd_seed_messages)

    p = sub.add_parser("compact")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--messages-file", required=True)
    p.set_defaults(func=cmd_compact)

    p = sub.add_parser("new-session")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--chat-id", required=True)
    p.set_defaults(func=cmd_new_session)

    p = sub.add_parser("append")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--messages-file", required=True)
    p.set_defaults(func=cmd_append)

    p = sub.add_parser("seed-session")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--title", default=None)
    p.add_argument("--messages-file", default=None)
    p.add_argument("--archived", action="store_true")
    p.add_argument("--hidden", action="store_true")
    p.add_argument("--parent-session-id", default=None)
    p.add_argument("--end-reason", default=None)
    p.set_defaults(func=cmd_seed_session)

    p = sub.add_parser("acquire-lease")
    p.add_argument("--home", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--surface", default="f1-fixture-synthetic-lease")
    p.add_argument(
        "--desktop-held",
        action="store_true",
        help="advertise bot_live_delivery_consumer so the Bot Chat mailbox path owns the turn",
    )
    p.set_defaults(func=cmd_acquire_lease)

    p = sub.add_parser("compat-identity")
    p.set_defaults(func=cmd_compat_identity)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.diagnostic_stacks:
        faulthandler.dump_traceback_later(
            _DIAGNOSTIC_STACK_SECONDS, repeat=False, file=sys.stderr, exit=False
        )
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        _fail(f"{type(exc).__name__}: {exc}")
    finally:
        if args.diagnostic_stacks:
            faulthandler.cancel_dump_traceback_later()
    return 0


if __name__ == "__main__":
    sys.exit(main())
