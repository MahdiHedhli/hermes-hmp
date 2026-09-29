"""T028: the read bridge, against fake Hermes objects (`fake_hermes.py`), plus the CS-21 checks.

Acceptance (tasks.md T028):
- unit tests with fake Hermes objects;
- the AST import set and the probe-resolved source files are both contained in the committed
  `bridge_files`. The probe-resolved half needs a Hermes build with its own venv. It runs against
  `HMP_HERMES_SRC`, or against `$HMP_HERMES_BUILDS_DIR/{stock-base,experimental}/src`, and skips
  with a reason when neither exists.

Integration reads on both builds are T035's.
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import enum
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import bridge, compat
from hmp_plugin.bridge import (
    CANARY_USER_PREFIX,
    INERT_TRIGGER_TEXT,
    BridgeError,
    HermesApi,
    HermesReadBridge,
)
from hmp_plugin.contract import AuthzState, ConversationRef, ResetReason

from .fake_hermes import UNRESOLVED, FakeDirectory, World

SERVER_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVER_DIR.parent
BRIDGE_SOURCE = (SERVER_DIR / "hmp_plugin" / "bridge.py").read_text(encoding="utf-8")

USER = "hmpu_" + "a" * 32
OTHER = "hmpu_" + "b" * 32
CHAT = "c_" + "1" * 32
CMID = "01890000-0000-7000-8000-000000000001"


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


@pytest.fixture
def directory() -> FakeDirectory:
    return FakeDirectory()


@pytest.fixture
def br(world: World, directory: FakeDirectory) -> HermesReadBridge:
    return HermesReadBridge(world.adapter, directory, hermes=world.api)  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------------------
# Served set
# --------------------------------------------------------------------------------------------------


def test_served_profiles(br: HermesReadBridge) -> None:
    assert br.served_profiles() == ["alpha", "beta", "lonely"]


def test_served_profiles_fail_loudly(world: World, br: HermesReadBridge) -> None:
    world.runner.served = [1]  # type: ignore[list-item]
    with pytest.raises(BridgeError):
        br.served_profiles()
    world.adapter.gateway_runner = None  # type: ignore[assignment]
    with pytest.raises(BridgeError):
        br.served_profiles()


# --------------------------------------------------------------------------------------------------
# Per-bot authorization: fails closed to UNVERIFIABLE
# --------------------------------------------------------------------------------------------------


def test_authz_states(world: World, br: HermesReadBridge) -> None:
    world.approve(USER, "alpha")
    assert br.authz_state(USER, "alpha") is AuthzState.AUTHORIZED
    assert br.authz_state(OTHER, "alpha") is AuthzState.PENDING_OPERATOR
    assert br.authz_state(USER, "beta") is AuthzState.PENDING_OPERATOR
    assert br.authz_state(USER, "lonely") is AuthzState.NOT_ROUTED  # served, no route
    assert br.authz_state(USER, "ghost") is AuthzState.NOT_SERVED


def test_allow_all_in_either_scope_is_refused(world: World, br: HermesReadBridge) -> None:
    world.approve(USER, "alpha")
    world.runner.allow_all_transport = True
    assert br.authz_state(USER, "alpha") is AuthzState.REFUSED_ALLOW_ALL
    world.runner.allow_all_transport = False
    world.runner.allow_all_routed = {"alpha"}
    assert br.authz_state(USER, "alpha") is AuthzState.REFUSED_ALLOW_ALL
    assert br.authz_state(USER, "beta") is AuthzState.PENDING_OPERATOR


def test_canary_is_a_fresh_never_enrolled_user(world: World, br: HermesReadBridge) -> None:
    br.authz_state(USER, "alpha")
    br.authz_state(USER, "alpha")
    canaries = [
        s.user_id for s in world.adapter.sources if s.user_id.startswith(CANARY_USER_PREFIX)
    ]
    assert len(canaries) == 2 and canaries[0] != canaries[1]


@pytest.mark.parametrize(
    "breakage",
    ["raises", "non_bool", "unresolved_home", "no_runner", "served_raises", "build_source"],
)
def test_authz_fails_closed(world: World, br: HermesReadBridge, breakage: str) -> None:
    world.approve(USER, "alpha")
    if breakage == "raises":
        world.runner.authz_raises = True
    elif breakage == "non_bool":
        world.runner.authz_answer = 1
    elif breakage == "unresolved_home":
        world.runner.homes["alpha"] = UNRESOLVED
    elif breakage == "no_runner":
        world.adapter.gateway_runner = None  # type: ignore[assignment]
    elif breakage == "served_raises":
        world.runner.served = None  # type: ignore[assignment]
    else:
        world.adapter.build_source = None  # type: ignore[assignment,method-assign]
    assert br.authz_state(USER, "alpha") is AuthzState.UNVERIFIABLE


def test_profile_route_rejected_forces_not_routed(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    """SR-6: Hermes's own ingress drops a source whose route was rejected and fell back to the
    owner profile (`build_source`'s `profile_route_rejected`), even when that fallback profile
    equals the one requested. The bridge must fail closed to NOT_ROUTED/BridgeError the same way,
    not just compare `source.profile`."""
    world.approve(USER, "alpha")
    world.adapter.route_rejected = True
    assert br.authz_state(USER, "alpha") is AuthzState.NOT_ROUTED
    result = _in_loop(lambda: br.request_authorization(USER, "alpha"))
    assert result.authz is AuthzState.NOT_ROUTED
    directory.chats[(USER, "alpha")] = CHAT
    with pytest.raises(BridgeError):
        br.conversation_ref(USER, "alpha")


def test_authz_uses_the_users_chat_when_present(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    directory.chats[(USER, "alpha")] = CHAT
    br.authz_state(USER, "alpha")
    user_sources = [s for s in world.adapter.sources if s.user_id == USER]
    assert user_sources and all(s.chat_id == CHAT for s in user_sources)


# --------------------------------------------------------------------------------------------------
# PR6-3 instance-wide note input
# --------------------------------------------------------------------------------------------------


def test_instance_wide_grant(world: World, br: HermesReadBridge) -> None:
    assert br.instance_wide_grant("alpha") is False
    world.api.env["GATEWAY_ALLOWED_USERS"] = "someone"
    assert br.instance_wide_grant("alpha") is True
    world.api.env = {"HMP_ALLOWED_USERS": " x "}
    assert br.instance_wide_grant("alpha") is True


def test_instance_wide_grant_failure_discloses(world: World, br: HermesReadBridge) -> None:
    def boom(_name: str) -> str:
        raise RuntimeError("scope")

    world.api.platform_gate_env = boom  # type: ignore[method-assign]
    assert br.instance_wide_grant("alpha") is True


def test_instance_wide_grant_from_adapter_extra_allow_from(
    world: World, br: HermesReadBridge
) -> None:
    """SR-1 problem 2: `platforms.hmp.extra.allow_from` is read from the transport adapter, so
    Hermes's own `_adapter_extra_allowlist_authorizes` treats it as instance-wide -- the bridge
    must disclose it exactly like the env allowlists, even though no env variable is set."""
    assert br.instance_wide_grant("alpha") is False
    world.adapter.config.extra["allow_from"] = "hmpu_" + "c" * 32
    assert br.instance_wide_grant("alpha") is True
    world.adapter.config.extra["allow_from"] = ""  # blank counts as absent, matching Hermes
    assert br.instance_wide_grant("alpha") is False
    world.adapter.config.extra["allow_from"] = ["hmpu_" + "d" * 32]  # a YAML list is also truthy
    assert br.instance_wide_grant("alpha") is True


# --------------------------------------------------------------------------------------------------
# P6 inert trigger (GU-4 exception, PR6-1, PR6-2)
# --------------------------------------------------------------------------------------------------


def _in_loop(fn: Any) -> Any:
    async def main() -> Any:
        result = fn()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return result

    return asyncio.run(main())


def test_trigger_sent_only_when_pending(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    directory.chats[(USER, "alpha")] = CHAT
    directory.labels[USER] = "f1-fixture-label-1"
    result = _in_loop(lambda: br.request_authorization(USER, "alpha"))
    assert result.authz is AuthzState.PENDING_OPERATOR
    assert len(world.adapter.handled) == 1
    event = world.adapter.handled[0]
    assert event.text == INERT_TRIGGER_TEXT and not event.text.startswith("/")
    assert event.allow_gateway_control is False
    assert event.user_id == USER and event.user_name == "f1-fixture-label-1"
    assert event.source.chat_id == CHAT and event.source.profile == "alpha"

    world.approve(USER, "alpha")
    result = _in_loop(lambda: br.request_authorization(USER, "alpha"))
    assert result.authz is AuthzState.AUTHORIZED
    assert len(world.adapter.handled) == 1  # nothing handed off for a non-pending bot


@pytest.mark.parametrize("state", ["allow_all", "not_routed", "not_served", "unverifiable"])
def test_no_trigger_for_other_states(
    world: World, br: HermesReadBridge, directory: FakeDirectory, state: str
) -> None:
    profile = {"not_routed": "lonely", "not_served": "ghost"}.get(state, "alpha")
    directory.chats[(USER, profile)] = CHAT
    if state == "allow_all":
        world.runner.allow_all_transport = True
    if state == "unverifiable":
        world.runner.authz_raises = True
    result = _in_loop(lambda: br.request_authorization(USER, profile))
    assert result.authz is not AuthzState.PENDING_OPERATOR
    assert world.adapter.handled == []


def test_trigger_without_chat_or_loop_is_unverifiable(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    assert _in_loop(lambda: br.request_authorization(USER, "alpha")).authz is (
        AuthzState.UNVERIFIABLE
    )
    directory.chats[(USER, "alpha")] = CHAT
    # No running event loop: the trigger cannot be handed off, so no pending request exists.
    assert br.request_authorization(USER, "alpha").authz is AuthzState.UNVERIFIABLE
    assert world.adapter.handled == []


def test_trigger_result_carries_nothing_from_hermes(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    directory.chats[(USER, "alpha")] = CHAT
    result = _in_loop(lambda: br.request_authorization(USER, "alpha"))
    assert dict(result.extras) == {} and result.request_id is None  # PR6-2


def _install_fake_event_module(
    monkeypatch: pytest.MonkeyPatch, *, defer: bool, control: bool, admission: bool = False
) -> None:
    class MessageType(enum.Enum):
        TEXT = "text"

    fields: list[Any] = [
        ("text", str),
        ("message_type", MessageType),
        ("source", object, dataclasses.field(default=None)),
        ("message_id", object, dataclasses.field(default=None)),
        ("user_id", object, dataclasses.field(default=None)),
        ("user_name", object, dataclasses.field(default=None)),
        ("internal", bool, dataclasses.field(default=False)),
    ]
    if control:
        fields.append(("allow_gateway_control", bool, dataclasses.field(default=True)))
    if defer:
        fields.append(("defer_policy", str, dataclasses.field(default="hermes")))
    if admission:
        fields.append(("admission_ticket", object, dataclasses.field(default=None)))
    event_cls = dataclasses.make_dataclass("MessageEvent", fields)
    module = types.ModuleType("gateway.platforms.event")
    module.MessageEvent = event_cls  # type: ignore[attr-defined]
    module.MessageType = MessageType  # type: ignore[attr-defined]
    for name in ("gateway", "gateway.platforms"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "gateway.platforms.event", module)


def test_real_trigger_event_on_experimental_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_event_module(monkeypatch, defer=True, control=True, admission=True)
    event = HermesApi().inert_trigger_event(source="src", user_id=USER, user_name="label")
    assert event.text == INERT_TRIGGER_TEXT
    assert event.allow_gateway_control is False and event.internal is False
    assert event.defer_policy == "reject"  # a busy bot refuses, never queues (P2)
    assert event.message_id.startswith("hmp:auth:")


def test_real_trigger_event_on_stock_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_event_module(monkeypatch, defer=False, control=True)
    event = HermesApi().inert_trigger_event(source="src", user_id=USER, user_name="label")
    assert event.allow_gateway_control is False and not hasattr(event, "defer_policy")


def test_real_trigger_event_refuses_without_command_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_event_module(monkeypatch, defer=False, control=False)
    with pytest.raises(BridgeError):
        HermesApi().inert_trigger_event(source="src", user_id=USER, user_name="label")


# --------------------------------------------------------------------------------------------------
# Conversation reads: never mint, fail loudly
# --------------------------------------------------------------------------------------------------


def _seed(world: World, directory: FakeDirectory, session: str = "s1") -> list[int]:
    directory.chats[(USER, "alpha")] = CHAT
    world.start_conversation("alpha", CHAT, session)
    db = world.dbs["alpha"]
    return [
        db.append(session, "user", "[F1 SYNTHETIC] hello", pmid=f"hmp:{CHAT}:{CMID}"),
        db.append(
            session, "assistant", [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
        ),
        db.append(session, "tool", None),
        db.append(session, "user", "x", pmid=f"hmp:c_other:{CMID}"),
    ]


def test_conversation_ref_never_mints(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    assert br.conversation_ref(USER, "alpha") is None  # no chat: nothing looked up
    directory.chats[(USER, "alpha")] = CHAT
    assert br.conversation_ref(USER, "alpha") is None  # chat, never started
    assert world.adapter._session_store.entries == {}
    assert directory.chats == {(USER, "alpha"): CHAT}
    assert world.api.acquired == 0
    world.start_conversation("alpha", CHAT, "s1")
    assert br.conversation_ref(USER, "alpha") == ConversationRef(USER, "alpha", "s1")


def test_conversation_ref_failures(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    directory.chats[(USER, "lonely")] = CHAT
    with pytest.raises(BridgeError):
        br.conversation_ref(USER, "lonely")  # not routed
    directory.chats[(USER, "alpha")] = CHAT
    world.adapter._session_store = None  # type: ignore[assignment]
    with pytest.raises(BridgeError):
        br.conversation_ref(USER, "alpha")


def test_latest_rows(world: World, br: HermesReadBridge, directory: FakeDirectory) -> None:
    ids = _seed(world, directory)
    ref = ConversationRef(USER, "alpha", "s1")
    rows = br.latest(ref, 3)
    assert [r.id for r in rows] == ids[1:]
    assert rows[0].text == "ab" and rows[1].text == "" and rows[1].role == "tool"
    assert rows[2].client_message_id is None  # another chat's id is never attributed here
    first = br.latest(ref, 10)[0]
    assert first.client_message_id == CMID and first.created_at == 1_900_000_000.5
    assert br.head(ref) == ids[-1]
    assert world.api.acquired == world.api.released > 0


def test_after_and_resets(world: World, br: HermesReadBridge, directory: FakeDirectory) -> None:
    ids = _seed(world, directory)
    ref = ConversationRef(USER, "alpha", "s1")
    assert [r.id for r in br.after(ref, 0, 100)] == ids  # type: ignore[union-attr]
    assert [r.id for r in br.after(ref, ids[1], 100)] == ids[2:]  # type: ignore[union-attr]
    assert [r.id for r in br.after(ref, ids[1], 1)] == ids[2:3]  # type: ignore[union-attr]
    assert br.after(ref, 999, 10) is ResetReason.CURSOR_NOT_RESOLVABLE
    other = world.dbs["alpha"].append("s-other", "user", "y")
    assert br.after(ref, other, 10) is ResetReason.CURSOR_NOT_RESOLVABLE
    world.dbs["alpha"].compact_in_place("s1", keep=2)  # RO-8: fresh ids, same session
    assert br.after(ref, ids[-1], 10) is ResetReason.HISTORY_REWRITTEN


def test_lineage(world: World, br: HermesReadBridge, directory: FakeDirectory) -> None:
    ids = _seed(world, directory)
    ref = ConversationRef(USER, "alpha", "s1")
    info = br.lineage(ref)
    assert (info.session_id, info.lineage_tip, info.head_row_id, info.active_row_count) == (
        "s1",
        "s1",
        ids[-1],
        4,
    )
    assert info.chain == ("s1",)
    world.dbs["alpha"].children["s1"] = "s1b"  # a compression continuation
    world.dbs["alpha"].append("s1b", "assistant", "later")
    info = br.lineage(ref)
    assert info.lineage_tip == "s1b" and info.chain == ("s1", "s1b") and info.active_row_count == 1


def test_read_failures_raise_never_empty(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    _seed(world, directory)
    ref = ConversationRef(USER, "alpha", "s1")
    world.dbs["alpha"].fail = True
    for call in (lambda: br.latest(ref, 5), lambda: br.after(ref, 0, 5), lambda: br.lineage(ref)):
        with pytest.raises(BridgeError):
            call()
    world.dbs["alpha"].fail = False
    world.runner.homes["alpha"] = UNRESOLVED
    with pytest.raises(BridgeError):
        br.latest(ref, 5)


def test_missing_database_is_never_created(
    world: World, br: HermesReadBridge, directory: FakeDirectory
) -> None:
    _seed(world, directory)
    db_file = Path(world.runner.homes["alpha"]) / "state.db"
    db_file.unlink()
    with pytest.raises(BridgeError):
        br.latest(ConversationRef(USER, "alpha", "s1"), 5)
    assert not db_file.exists() and world.api.acquired == 0


# --------------------------------------------------------------------------------------------------
# Amendment A1 (session browsing, OD-F9/OD-F10): SES-1 list, SES-2 resolve
# --------------------------------------------------------------------------------------------------


def test_list_sessions_narrows_to_ses1_fields(world: World, br: HermesReadBridge) -> None:
    db = world.dbs["alpha"]
    db.seed_session("s-cli", source="cli", title="a CLI session", started_at=100.0)
    db.append("s-cli", "user", "hi")
    summaries = br.list_sessions(USER, "alpha", sources_excluded=(), limit=10, offset=0)
    assert len(summaries) == 1
    s = summaries[0]
    got = (s.session_id, s.title, s.source, s.message_count)
    assert got == ("s-cli", "a CLI session", "cli", 1)
    assert s.started_at == 100.0 and s.last_active_at is not None


def test_list_sessions_multi_source_and_pagination(world: World, br: HermesReadBridge) -> None:
    db = world.dbs["alpha"]
    for i in range(5):
        db.seed_session(f"s{i}", source="cli" if i % 2 == 0 else "desktop", started_at=float(i))
    page1 = br.list_sessions(USER, "alpha", sources_excluded=(), limit=2, offset=0)
    page2 = br.list_sessions(USER, "alpha", sources_excluded=(), limit=2, offset=2)
    assert len(page1) == 2 and len(page2) == 2
    assert {s.session_id for s in page1} != {s.session_id for s in page2}


def test_list_sessions_archived_excluded_hidden_included(
    world: World, br: HermesReadBridge
) -> None:
    """The bridge call itself stays generic (OD-F11): archived stays excluded, but hidden is now
    included -- the canonical Bot Chat is always hidden, so `reads.py`'s own selector, not this
    bridge call, is what narrows the result back down."""
    db = world.dbs["alpha"]
    db.seed_session("s-visible", source="cli")
    db.seed_session("s-archived", source="cli", archived=True)
    db.seed_session("s-hidden", source="cli", hidden=True)
    summaries = br.list_sessions(USER, "alpha", sources_excluded=(), limit=10, offset=0)
    assert {s.session_id for s in summaries} == {"s-visible", "s-hidden"}
    assert next(s for s in summaries if s.session_id == "s-hidden").hidden is True
    assert next(s for s in summaries if s.session_id == "s-visible").hidden is False


def test_list_sessions_collapses_compression_lineage_to_one_row(
    world: World, br: HermesReadBridge
) -> None:
    """§1.1 of the amendment: a compression chain surfaces as one row, at the tip's content."""
    db = world.dbs["alpha"]
    db.seed_session("s-root", source="cli", title="old title", started_at=1.0)
    db.append("s-root", "user", "first")
    db.seed_session("s-tip", source="cli", title="new title", started_at=2.0)
    db.append("s-tip", "assistant", "second")
    db.children["s-root"] = "s-tip"
    summaries = br.list_sessions(USER, "alpha", sources_excluded=(), limit=10, offset=0)
    assert len(summaries) == 1  # never two rows for one lineage
    s = summaries[0]
    assert s.session_id == "s-tip" and s.title == "new title" and s.message_count == 1


def test_list_sessions_exclude_sources(world: World, br: HermesReadBridge) -> None:
    db = world.dbs["alpha"]
    db.seed_session("s-cli", source="cli")
    db.seed_session("s-tool", source="tool")
    summaries = br.list_sessions(USER, "alpha", sources_excluded=("tool",), limit=10, offset=0)
    assert [s.session_id for s in summaries] == ["s-cli"]
    everything = br.list_sessions(USER, "alpha", sources_excluded=(), limit=10, offset=0)
    assert {s.session_id for s in everything} == {"s-cli", "s-tool"}


def test_list_sessions_fails_loudly_never_empty(world: World, br: HermesReadBridge) -> None:
    world.dbs["alpha"].seed_session("s1", source="cli")
    world.dbs["alpha"].fail = True
    with pytest.raises(BridgeError):
        br.list_sessions(USER, "alpha", sources_excluded=(), limit=10, offset=0)


def test_resolve_session_existence_and_scoping(world: World, br: HermesReadBridge) -> None:
    world.dbs["alpha"].seed_session("s1", source="cli")
    ref = br.resolve_session(USER, "alpha", "s1")
    assert ref == ConversationRef(USER, "alpha", "s1")
    assert br.resolve_session(USER, "alpha", "unknown-session") is None
    # Never mints, never crosses profiles: the same id under a different (unrouted) profile.
    assert br.resolve_session(USER, "beta", "s1") is None


def test_capability_versions(world: World, br: HermesReadBridge) -> None:
    assert br.capability_versions() == {}  # stock: no map
    world.api.capabilities = {"defer_policy_reject": 1, "admission_precondition": True}
    assert br.capability_versions() == {"defer_policy_reject": 1, "admission_precondition": True}
    world.api.capabilities = ["not", "a", "map"]
    assert br.capability_versions() == {}


# --------------------------------------------------------------------------------------------------
# Amendment F2 (direct send, HMP_V1.md §7a): resolve_bot_chat, lease_snapshot, direct_send_endpoint
# --------------------------------------------------------------------------------------------------


def test_resolve_bot_chat_none_when_no_row_titled_bot_chat(
    world: World, br: HermesReadBridge
) -> None:
    """DS-4(2)/DS-9: no Bot Chat exists yet -- never created here."""
    assert br.resolve_bot_chat("alpha") is None
    world.dbs["alpha"].seed_session("s1", title="Not Bot Chat")
    assert br.resolve_bot_chat("alpha") is None


def test_resolve_bot_chat_resolves_the_live_tip_and_full_chain(
    world: World, br: HermesReadBridge
) -> None:
    db = world.dbs["alpha"]
    db.seed_session("root1", title="Bot Chat", hidden=True, end_reason="compression")
    db.append("root1", "user", "hi", timestamp=1.0)
    db.seed_session("tip1", parent_session_id="root1")
    db.children["root1"] = "tip1"  # a compression rotation
    db.append("tip1", "assistant", "hello", timestamp=2.0)

    target = br.resolve_bot_chat("alpha")
    assert target is not None
    assert target.root_session_id == "root1"
    assert target.live_tip_session_id == "tip1"
    assert target.compression_chain == ("root1", "tip1")
    assert target.head_message_id == db.rows[-1]["id"]  # the tip's own latest active row


def test_lease_snapshot_none_on_failure_never_empty(world: World, br: HermesReadBridge) -> None:
    """Ownership uncertainty fails CLOSED: a registry home the fake never seeded is `None`, not an
    (incorrectly reassuring) empty list."""
    assert br.lease_snapshot("alpha") is None
    world.api.leases_by_home[world.runner.homes["alpha"]] = []
    assert br.lease_snapshot("alpha") == []
    world.api.leases_by_home[world.runner.homes["alpha"]] = [{"session_id": "tip1"}]
    assert br.lease_snapshot("alpha") == [{"session_id": "tip1"}]


def test_lease_snapshot_none_on_unresolvable_profile_home(
    world: World, br: HermesReadBridge
) -> None:
    world.runner.homes["alpha"] = UNRESOLVED
    assert br.lease_snapshot("alpha") is None


def test_direct_send_endpoint_requires_loopback_and_a_key(
    world: World, br: HermesReadBridge
) -> None:
    profile = "alpha"
    # Neither a config extra nor a key configured -> None (fail closed).
    assert br.direct_send_endpoint(profile) is None

    world.api.api_server_keys[profile] = "k" * 20
    # A key alone, no host override -> defaults to the documented loopback default.
    endpoint = br.direct_send_endpoint(profile)
    assert endpoint is not None
    assert endpoint.host == "127.0.0.1"
    assert endpoint.port == 8642
    assert endpoint.api_key == "k" * 20
    assert endpoint.path_prefix == ""  # default profile: no /p/<profile> mirror


def test_direct_send_endpoint_refuses_a_non_loopback_bind(
    world: World, br: HermesReadBridge
) -> None:
    """DS-2(b)/DS-6, review finding #6: HMP independently refuses to use this mechanism unless it
    can positively confirm the bind is loopback -- Hermes itself only warns, never refuses."""
    profile = "alpha"
    world.api.api_server_keys[profile] = "k" * 20
    world.api.api_server_extra_by_profile[profile] = {"host": "0.0.0.0"}  # noqa: S104
    assert br.direct_send_endpoint(profile) is None


def test_direct_send_endpoint_named_profile_gets_its_own_mirrored_path_and_key(
    world: World, br: HermesReadBridge
) -> None:
    """A named (secondary) profile's key is independently scoped -- never the default's."""
    world.api.api_server_keys["alpha"] = "default-key-" + "a" * 8
    world.api.api_server_keys["beta"] = "beta-key----" + "b" * 8
    endpoint = br.direct_send_endpoint("beta")
    assert endpoint is not None
    assert endpoint.api_key == world.api.api_server_keys["beta"]
    assert endpoint.path_prefix == "/p/beta"


def test_direct_send_endpoint_named_profile_with_no_key_fails_closed(
    world: World, br: HermesReadBridge
) -> None:
    """ "Named profiles fail closed rather than inherit the owner's key" (the review's own
    citation of `_check_auth`'s comment) -- `beta` never succeeds just because `alpha` has a key."""
    world.api.api_server_keys["alpha"] = "k" * 20
    assert br.direct_send_endpoint("beta") is None


def test_direct_send_endpoint_localhost_alias_maps_to_loopback_literal(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 2, BLOCKER #3: `localhost` is a configured NAME, never resolved by HMP itself
    -- it is rewritten to the IPv4 loopback literal before any socket is opened."""
    profile = "alpha"
    world.api.api_server_keys[profile] = "k" * 20
    world.api.api_server_extra_by_profile[profile] = {"host": "localhost"}
    endpoint = br.direct_send_endpoint(profile)
    assert endpoint is not None
    assert endpoint.host == "127.0.0.1"


def test_direct_send_endpoint_does_not_probe_a_closed_port(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 3: a configured loopback bind is returned without a separate TCP probe.
    Nothing is listening on this port; the aiohttp request is what fails closed later."""
    import socket

    profile = "alpha"
    world.api.api_server_keys[profile] = "k" * 20
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    world.api.api_server_extra_by_profile[profile] = {"host": "127.0.0.1", "port": port}
    endpoint = br.direct_send_endpoint(profile)
    assert endpoint is not None
    assert endpoint.host == "127.0.0.1"
    assert endpoint.port == port


def test_direct_send_endpoint_default_profile_prefers_extras_inline_key(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 2, should-fix: mirrors `api_server.py`'s own `extra.get("key", ...)`
    precedence for the DEFAULT profile -- an inline `extra.key` wins over the scoped secret."""
    profile = "alpha"
    world.api.api_server_keys[profile] = "scoped-secret-" + "s" * 8
    world.api.api_server_extra_by_profile[profile] = {"key": "inline-extra-key"}
    endpoint = br.direct_send_endpoint(profile)
    assert endpoint is not None
    assert endpoint.api_key == "inline-extra-key"


def test_direct_send_endpoint_named_profile_never_reads_extra_key(
    world: World, br: HermesReadBridge
) -> None:
    """A named profile's own `extra.key` (if it even had one) is never consulted -- only its own
    scoped secret, exactly like `api_server.py`'s `_expected_api_key` for a non-default profile."""
    profile = "beta"
    world.api.api_server_keys[profile] = "scoped-secret-" + "s" * 8
    world.api.api_server_extra_by_profile[profile] = {"key": "should-never-be-used"}
    endpoint = br.direct_send_endpoint(profile)
    assert endpoint is not None
    assert endpoint.api_key == "scoped-secret-" + "s" * 8


def test_direct_send_endpoint_named_profile_short_key_fails_closed(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 2, should-fix: the same `min_length=16` usability floor `api_server.py`'s
    `_expected_api_key` applies to a named profile's scoped key."""
    world.api.api_server_keys["beta"] = "short-key"  # 9 chars, well under the floor
    assert br.direct_send_endpoint("beta") is None


def test_direct_send_endpoint_default_profile_short_extra_key_fails_closed(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 3: the default profile's `extra.key` has the same 16-char floor. A short
    inline key fails closed (gate stays closed) even when a usable scoped secret exists -- it is
    not sent, and it does not fall through to that secret."""
    profile = "alpha"
    world.api.api_server_keys[profile] = "k" * 20
    world.api.api_server_extra_by_profile[profile] = {"key": "short-key"}
    assert br.direct_send_endpoint(profile) is None


def test_resolve_bot_chat_unions_ancestors_when_lineage_returns_only_the_tip(
    world: World, br: HermesReadBridge
) -> None:
    """Review round 3: `get_compression_lineage` returning only `[session_id]` must not drop
    ancestors. The independent `parent_session_id` walk (via `get_session`) is unioned in."""
    db = world.dbs["alpha"]
    db.lineage_returns_self_only = True
    db.seed_session("root", end_reason="compression")
    db.seed_session("mid", parent_session_id="root", end_reason="compression")
    db.seed_session("child", title="Bot Chat", parent_session_id="mid")
    db.children["root"] = "mid"
    db.children["mid"] = "child"
    db.append("child", "user", "hi", timestamp=1.0)

    target = br.resolve_bot_chat("alpha")
    assert target is not None
    assert target.live_tip_session_id == "child"
    assert target.root_session_id == "root"
    assert set(target.compression_chain) == {"root", "mid", "child"}
    assert target.compression_chain[0] == "root"


def test_resolve_bot_chat_fails_closed_when_the_parent_chain_is_uncertain(
    world: World, br: HermesReadBridge
) -> None:
    """A parent id that does not resolve means the lineage cannot be established. Fail closed
    (the send path maps this to `session_busy`), never a chain that omits the missing ancestor."""
    db = world.dbs["alpha"]
    db.lineage_returns_self_only = True
    db.seed_session("tip", title="Bot Chat", parent_session_id="gone")
    db.append("tip", "user", "hi", timestamp=1.0)
    with pytest.raises(BridgeError, match="compression lineage uncertain"):
        br.resolve_bot_chat("alpha")


# --------------------------------------------------------------------------------------------------
# CS-21: the bridge's reach, from its own source
# --------------------------------------------------------------------------------------------------


def _attribute_calls(tree: ast.AST) -> dict[str, set[str]]:
    reach: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in bridge.REACHED_METHODS
        ):
            reach.setdefault(node.value.id, set()).add(node.attr)
    return reach


def test_reached_methods_match_the_source() -> None:
    reach = _attribute_calls(ast.parse(BRIDGE_SOURCE))
    assert {k: frozenset(v) for k, v in reach.items()} == dict(bridge.REACHED_METHODS)


def test_getattr_reads_only_listed_data_attributes() -> None:
    names = set()
    for node in ast.walk(ast.parse(BRIDGE_SOURCE)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
        ):
            names.add(node.args[1].value)
    assert names <= bridge.REACHED_DATA_ATTRIBUTES


def _hermes_imports() -> set[tuple[str, str]]:
    out = set()
    for node in ast.walk(ast.parse(BRIDGE_SOURCE)):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            top = node.module.split(".")[0]
            if top in sys.stdlib_module_names or top == "__future__":
                continue
            out.update((node.module, a.name) for a in node.names)
    return out


def test_every_reached_internal_is_probed() -> None:
    # Amendment F2 (direct send, HMP_V1.md §7a): `bridge.py` now serves two compat targets --
    # reads (`READ_DEPENDENCIES`) and the guarded direct-send path (`DIRECT_SEND_DEPENDENCIES`,
    # e.g. `hermes_cli.active_sessions.active_session_registry_snapshot`). An import reached only
    # for direct send is still probed, just by the other tuple -- the union is what this AST-level
    # defense-in-depth check actually needs to cover.
    probed = {(d.module, d.qualname) for d in compat.READ_DEPENDENCIES} | {
        (d.module, d.qualname) for d in compat.DIRECT_SEND_DEPENDENCIES
    }
    optional = {("gateway.platforms.base", "PLATFORM_ADAPTER_CAPABILITIES")}  # absent on stock
    assert _hermes_imports() - optional <= probed
    probed_names = {q.rsplit(".", 1)[-1] for _m, q in probed if q}
    for methods in bridge.REACHED_METHODS.values():
        assert methods <= probed_names


# --------------------------------------------------------------------------------------------------
# CS-21: committed `bridge_files` contains the AST import set and the probe-resolved files
# --------------------------------------------------------------------------------------------------


def _build_sources() -> list[Path]:
    found = []
    if os.environ.get("HMP_HERMES_SRC"):
        found.append(Path(os.environ["HMP_HERMES_SRC"]))
    builds_dir = os.environ.get("HMP_HERMES_BUILDS_DIR")
    if builds_dir:
        for label in ("stock-base", "experimental"):
            src = Path(builds_dir) / label / "src"
            if src.is_dir() and src not in found:
                found.append(src)
    return found


BUILD_SOURCES = _build_sources()
TOOL = REPO_ROOT / "tools" / "compat" / "bridge_files.py"


@pytest.mark.skipif(
    not BUILD_SOURCES, reason="no Hermes build: set HMP_HERMES_SRC or HMP_HERMES_BUILDS_DIR"
)
@pytest.mark.parametrize("src", BUILD_SOURCES, ids=lambda p: p.parent.name)
def test_committed_bridge_files_contain_ast_set(src: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--hermes-src", str(src), "--ast-only", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(
    not BUILD_SOURCES, reason="no Hermes build: set HMP_HERMES_SRC or HMP_HERMES_BUILDS_DIR"
)
@pytest.mark.parametrize("src", BUILD_SOURCES, ids=lambda p: p.parent.name)
def test_committed_bridge_files_contain_probe_set(src: Path, tmp_path: Path) -> None:
    python = src / ".venv" / "bin" / "python"
    if not python.is_file():
        pytest.skip("this build has no venv (extracted with --skip-venv): probe set not computable")
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERMES_")}
    env["HERMES_HOME"] = str(tmp_path / "hermes-home")
    proc = subprocess.run(
        [str(python), str(TOOL), "--hermes-src", str(src), "--check"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["/approve always", "/deny", "/stop", "/reset", "always", "yes"])
async def test_phone_event_cannot_control_gateway_when_waiter_appears_during_delivery(
    br, directory, monkeypatch, text
) -> None:
    _install_fake_event_module(monkeypatch, defer=True, control=True, admission=True)
    directory.chats[(USER, "alpha")] = CHAT
    calls = []

    async def deliver(event):
        # A waiter arrived after the caller's preflight. The event itself must deny control.
        calls.append(event)
        assert event.allow_gateway_control is False
        assert event.internal is False
        assert event.defer_policy == "reject"
        event._gateway_accepted = True
        event.admission_ticket = types.SimpleNamespace(
            reported=types.SimpleNamespace(value="admitted")
        )

    br._adapter.handle_message = deliver
    assert await br.deliver_phone_message(user_id=USER, profile="alpha", text=text, message_id=CMID)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "expected"),
    [("admitted", True), ("refused_busy", False), (None, None)],
)
async def test_phone_delivery_waits_for_durable_admission(
    br, directory, monkeypatch, outcome, expected
) -> None:
    _install_fake_event_module(monkeypatch, defer=True, control=True, admission=True)
    monkeypatch.setattr(bridge, "PHONE_ADMISSION_WAIT_S", 0.03, raising=False)
    directory.chats[(USER, "alpha")] = CHAT

    async def deliver(event):
        # Task scheduling is not a durable admission. The later ticket is authoritative.
        event._gateway_accepted = True
        ticket = types.SimpleNamespace(reported=None)
        event.admission_ticket = ticket
        if outcome is not None:
            asyncio.get_running_loop().call_later(
                0.01, setattr, ticket, "reported", types.SimpleNamespace(value=outcome)
            )

    br._adapter.handle_message = deliver
    actual = await br.deliver_phone_message(
        user_id=USER, profile="alpha", text="hello", message_id=CMID
    )
    assert actual is expected


def test_prompt_timeout_hints_use_target_profile_a_b_a(br, world, monkeypatch) -> None:
    approval = types.ModuleType("tools.approval_context")
    clarify = types.ModuleType("tools.clarify_gateway")
    approval._get_approval_timeout = lambda: {"alpha": 73, "beta": 241}[world.runner.scope]
    clarify.get_clarify_timeout = lambda: {"alpha": 51, "beta": 0}[world.runner.scope]
    monkeypatch.setitem(sys.modules, "tools.approval_context", approval)
    monkeypatch.setitem(sys.modules, "tools.clarify_gateway", clarify)
    for profile, expected in (("alpha", (73, 51)), ("beta", (241, 0)), ("alpha", (73, 51))):
        assert (br.approval_timeout_s(profile), br.clarify_timeout_s(profile)) == expected
        assert world.runner.scope is None


@pytest.mark.skipif(
    not BUILD_SOURCES, reason="no Hermes build: set HMP_HERMES_SRC or HMP_HERMES_BUILDS_DIR"
)
@pytest.mark.parametrize("src", BUILD_SOURCES, ids=lambda p: p.parent.name)
def test_real_hermes_approval_qualification(src: Path) -> None:
    """B3: real guards/resolvers, with pending waiters and control-enabled comparisons."""
    python = src / ".venv" / "bin" / "python"
    if not python.is_file():
        pytest.skip("this build has no venv")
    for tool_args in (
        [str(TOOL), "--dependencies-attr", "DIRECT_SEND_DEPENDENCIES", "--target",
         str(SERVER_DIR / "hmp_plugin" / "direct_send_supported_builds.json"), "--check"],
        [str(REPO_ROOT / "tools" / "compat" / "approval_probes.py")],
    ):
        proc = subprocess.run(
            [str(python), *tool_args, "--hermes-src", str(src)],
            capture_output=True, text=True, check=False, cwd=REPO_ROOT,
        )
        assert proc.returncode == 0, proc.stderr
