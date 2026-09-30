"""T030: reads (roster, snapshot, history, resets, persisted baselines) and T029 P6, unit level.

The real `Reads`, `Authorize` and `HermesReadBridge` run over a real HMP store and fake Hermes
objects (`fake_hermes.py`), then end to end through the F1 route table (`hmp_kit`).

The fixture-mutation integration tests on real Hermes builds are in
`tests/integration/test_reads_fixture.py`. They wait for T060/T062.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hmp_plugin.authorize import INSTANCE_WIDE_NOTE, Authorize, approve_command, ensure_chat
from hmp_plugin.bridge import HermesReadBridge, StoreDirectory
from hmp_plugin.contract import (
    AuthzState,
    ErrorCode,
    Guarantees,
    HistoryPage,
    HistoryReset,
    HmpError,
    ResetReason,
    SessionSummary,
    WireMessage,
    WriteGate,
    WriteGateState,
)
from hmp_plugin.reads import (
    Reads,
    _encode_sessions_cursor,
    _fallback_display_name,
    _is_bot_view_session,
)
from hmp_plugin.store import Store

from . import hmp_kit
from .fake_hermes import World

USER = "hmpu_" + "a" * 32
OTHER = "hmpu_" + "b" * 32
T0 = 1_900_000_000


class Recorder:
    """Wraps a bridge and records every call, in order."""

    def __init__(self, inner: Any, log: list[str]) -> None:
        self._inner = inner
        self._log = log

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._inner, name)

        def call(*a: Any, **k: Any) -> Any:
            self._log.append(name)
            return target(*a, **k)

        return call


class Harness:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.world = World(tmp)
        self.store_path = tmp / "hmp.sqlite3"
        self.log: list[str] = []
        self.now = T0
        self.open()

    def open(self) -> None:
        self.store = Store(self.store_path)
        self.store.migrate()
        self.bridge = HermesReadBridge(
            self.world.adapter,
            StoreDirectory(self.store),
            hermes=self.world.api,  # type: ignore[arg-type]
            title_lookup_qualified=True,
        )
        self.recorder = Recorder(self.bridge, self.log)
        self.reads = Reads(
            self.recorder,  # type: ignore[arg-type]
            self.store,
            iid="i" * 52,
            guarantees=Guarantees,
            write_gate=lambda: WriteGate(WriteGateState.CLOSED, "guarantees_unavailable"),
            clock=lambda: self.now,
        )
        self.authorize = Authorize(  # type: ignore[arg-type]
            self.recorder, self.store, clock=lambda: self.now
        )

    def restart(self) -> None:
        """An HMP restart: a new store connection and new components, same Hermes."""
        self.store.close()
        self.open()

    def chat(self, user: str = USER, profile: str = "alpha") -> str:
        return ensure_chat(self.store, user, profile)

    def start(self, session: str, user: str = USER, profile: str = "alpha") -> list[int]:
        chat = self.chat(user, profile)
        self.world.start_conversation(profile, chat, session)
        db = self.world.dbs[profile]
        return [
            db.append(session, "user" if i % 2 == 0 else "assistant", f"m{i}") for i in range(5)
        ]

    def chats_count(self) -> int:
        with self.store.transaction() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0])

    def baseline(self, user: str = USER, profile: str = "alpha") -> Any:
        return self.store.get_session_baseline(user, profile)


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    harness = Harness(tmp_path)
    harness.world.approve(USER, "alpha")
    return harness


def _ids(page: HistoryPage) -> list[int]:
    return [m.id for m in page.messages]


# --------------------------------------------------------------------------------------------------
# `_fallback_display_name`, the pure roster naming rule (labels.ts:54-63)
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ("default", "Hermes"),
        ("Default", "Hermes"),  # matched case-insensitively, like the JS `.toLowerCase()`
        ("DEFAULT", "Hermes"),
        ("liteforms-connector", "Liteforms Connector"),  # kebab
        ("net_min", "Net Min"),  # snake
        ("netmin", "Netmin"),  # single word, still capitalized
        ("Research Buddy", "Research Buddy"),  # already capitalised, no separators: unchanged
        ("already-Capitalised", "Already Capitalised"),  # `-` still becomes a space either way
        ("", ""),  # empty maps to itself, exactly as the JS (`''.replace(...) === ''`)
        ("   ", ""),  # blank/whitespace-only
        ("--weird__id--", "Weird Id"),  # odd: leading/trailing/doubled separators collapse
        ("a", "A"),  # single character
    ],
)
def test_fallback_display_name(profile: str, expected: str) -> None:
    assert _fallback_display_name(profile) == expected


# --------------------------------------------------------------------------------------------------
# RO-1 roster
# --------------------------------------------------------------------------------------------------


def test_roster(h: Harness) -> None:
    h.world.runner.served = ["alpha", "beta", "lonely"]
    roster = h.reads.roster(USER)
    assert roster.instance == "i" * 52
    assert type(roster.served_at) is int and roster.served_at == T0
    assert roster.guarantees == Guarantees()
    assert roster.write_gate.state is WriteGateState.CLOSED
    assert [(b.profile, b.authz) for b in roster.bots] == [
        ("alpha", AuthzState.AUTHORIZED),
        ("beta", AuthzState.PENDING_OPERATOR),
        ("lonely", AuthzState.NOT_ROUTED),
    ]
    # `display_name` never reads Hermes (deferred, see reads.py's module docstring): the desktop's
    # own fallback rule Title-Cases the (single-word, unpunctuated) fixture ids.
    assert [b.display_name for b in roster.bots] == ["Alpha", "Beta", "Lonely"]
    assert h.chats_count() == 0  # reading the roster mints nothing
    assert "conversation_ref" not in h.log  # no bot content is read for the roster


def test_roster_default_profile_falls_back_to_hermes(h: Harness) -> None:
    h.world.runner.homes["default"] = h.world.runner.homes["alpha"]
    h.world.runner.served = ["default"]
    roster = h.reads.roster(USER)
    assert [b.display_name for b in roster.bots] == ["Hermes"]


def test_roster_falls_back_to_kebab_and_snake_title_case(h: Harness) -> None:
    for extra in ("liteforms-connector", "net_min"):
        h.world.runner.homes[extra] = h.world.runner.homes["alpha"]
    h.world.runner.served = ["liteforms-connector", "net_min"]
    roster = h.reads.roster(USER)
    assert [b.display_name for b in roster.bots] == ["Liteforms Connector", "Net Min"]


def test_roster_marks_unverifiable_bots(h: Harness) -> None:
    h.world.runner.authz_raises = True
    bots = {b.profile: b.authz for b in h.reads.roster(USER).bots}
    assert bots == {
        "alpha": AuthzState.UNVERIFIABLE,
        "beta": AuthzState.UNVERIFIABLE,
        "lonely": AuthzState.NOT_ROUTED,  # decided before any grant is read
    }


# --------------------------------------------------------------------------------------------------
# Live-bug fix (multiplexed gateway): `on_served_profiles`, called on every successful roster read
# with the served set it already fetched for itself -- the adapter's hook for keeping the listener
# record's `profiles` current between its own periodic refresh ticks (`adapter._sync_refresh`).
# --------------------------------------------------------------------------------------------------


def _reads_with_hook(h: Harness, on_served_profiles: Any) -> Reads:
    return Reads(
        h.recorder,
        h.store,
        iid="i" * 52,
        guarantees=Guarantees,
        write_gate=lambda: WriteGate(WriteGateState.CLOSED, "guarantees_unavailable"),
        clock=lambda: h.now,
        on_served_profiles=on_served_profiles,
    )


def test_roster_calls_the_served_profiles_hook_on_success(h: Harness) -> None:
    seen: list[list[str]] = []
    _reads_with_hook(h, seen.append).roster(USER)
    assert seen == [["alpha", "beta", "lonely"]]


def test_roster_hook_sees_a_changed_served_set_on_the_next_call(h: Harness) -> None:
    """The whole point: a later roster read observes whatever the multiplexer serves NOW, not
    what it served when `Reads` was built."""
    seen: list[list[str]] = []
    reads = _reads_with_hook(h, seen.append)
    reads.roster(USER)
    h.world.runner.served = ["alpha", "beta", "lonely", "netmin"]  # a hot-added profile
    reads.roster(USER)
    assert seen == [["alpha", "beta", "lonely"], ["alpha", "beta", "lonely", "netmin"]]


def test_roster_hook_failure_never_breaks_the_roster_read(h: Harness) -> None:
    def boom(_served: Any) -> None:
        raise RuntimeError("disk full")

    roster = _reads_with_hook(h, boom).roster(USER)  # must not raise
    assert {b.profile for b in roster.bots} == {"alpha", "beta", "lonely"}


def test_roster_without_a_hook_is_unaffected(h: Harness) -> None:
    # `h.reads` is built with no `on_served_profiles` (the `Harness` default): the regression
    # guard that the hook is genuinely optional.
    roster = h.reads.roster(USER)
    assert {b.profile for b in roster.bots} == {"alpha", "beta", "lonely"}


# --------------------------------------------------------------------------------------------------
# ERR-3 gate, authorization first
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("profile", "setup", "code", "http", "authz"),
    [
        ("beta", None, ErrorCode.FORBIDDEN, 403, "pending_operator"),
        ("alpha", "allow_all", ErrorCode.FORBIDDEN, 403, "refused_allow_all"),
        ("lonely", None, ErrorCode.NOT_ROUTED, 409, "not_routed"),
        ("ghost", None, ErrorCode.NOT_ROUTED, 409, "not_served"),
        ("alpha", "raises", ErrorCode.OTHER, 503, "unverifiable"),
    ],
)
def test_gate_refuses_before_any_lookup(
    h: Harness, profile: str, setup: str | None, code: ErrorCode, http: int, authz: str
) -> None:
    if setup == "allow_all":
        h.world.runner.allow_all_transport = True
    elif setup == "raises":
        h.world.runner.authz_raises = True
    for call in (
        lambda: h.reads.snapshot(USER, profile, 50),
        lambda: h.reads.history(USER, profile, 0, 100),
    ):
        h.log.clear()
        with pytest.raises(HmpError) as err:
            call()
        assert (err.value.code, err.value.http, err.value.extras["authz"]) == (code, http, authz)
        if authz == "unverifiable":
            assert err.value.extras["why"] == "unverifiable"
        assert h.log == ["authz_state"]  # nothing else reached Hermes
    assert h.world.api.acquired == 0 and h.baseline(USER, profile) is None


def test_snapshot_reads_tail_first(h: Harness) -> None:
    order: list[str] = []
    real_tail = h.reads._tail

    def tail() -> Any:
        order.append("tail")
        return real_tail()

    h.reads._tail = tail  # type: ignore[method-assign]
    h.log.clear()
    h.reads.snapshot(USER, "alpha", 50)
    assert order == ["tail"] and h.log[0] == "authz_state"
    # The tail is read before the gate: a refused request also read it first, and nothing else.
    with pytest.raises(HmpError):
        h.reads.snapshot(USER, "beta", 50)
    assert order == ["tail", "tail"]


# --------------------------------------------------------------------------------------------------
# RO-3 snapshot
# --------------------------------------------------------------------------------------------------


def test_never_started_conversation_is_empty_and_mints_nothing(h: Harness) -> None:
    snap = h.reads.snapshot(USER, "alpha", 50)
    assert snap.head_message_id is None and snap.messages == () and snap.session_id is None
    assert snap.conversation_id == "default"
    assert h.chats_count() == 0
    assert h.world.adapter._session_store.entries == {}
    assert h.baseline() is None
    # A chat that exists but whose conversation never started is also empty and unchanged.
    h.chat()
    assert h.reads.snapshot(USER, "alpha", 50).head_message_id is None
    assert h.chats_count() == 1 and h.world.adapter._session_store.entries == {}
    page = h.reads.history(USER, "alpha", 0, 100)
    assert isinstance(page, HistoryPage) and page.messages == () and page.head_message_id is None


def test_snapshot_window_and_baseline(h: Harness) -> None:
    ids = h.start("s1")
    snap = h.reads.snapshot(USER, "alpha", 3)
    assert [m.id for m in snap.messages] == ids[-3:]
    assert all(isinstance(m, WireMessage) for m in snap.messages)
    assert snap.head_message_id == ids[-1] and snap.session_id == "s1"
    assert snap.turn.observed_state.value == "unknown" and snap.partial is None
    assert snap.partial_lost is False and snap.open_requests == ()
    assert type(snap.tail.seq) is int and snap.tail.epoch
    b = h.baseline()
    assert (b["session_id"], b["lineage_tip"], b["active_row_count"]) == ("s1", "s1", 5)


def test_epoch_changes_per_process(h: Harness) -> None:
    h.start("s1")
    first = h.reads.snapshot(USER, "alpha", 5).tail.epoch
    h.restart()
    assert h.reads.snapshot(USER, "alpha", 5).tail.epoch != first


def test_read_failure_is_internal_error_not_empty(h: Harness) -> None:
    h.start("s1")
    h.world.dbs["alpha"].fail = True
    for call in (
        lambda: h.reads.snapshot(USER, "alpha", 5),
        lambda: h.reads.history(USER, "alpha", 0, 5),
    ):
        with pytest.raises(HmpError) as err:
            call()
        assert (err.value.code, err.value.http, err.value.extras) == (
            ErrorCode.OTHER,
            500,
            {"why": "internal_error"},
        )


# --------------------------------------------------------------------------------------------------
# RO-6 / RO-8 history and every reset reason
# --------------------------------------------------------------------------------------------------


def test_append_gives_rows_after_the_cursor(h: Harness) -> None:
    ids = h.start("s1")
    head = h.reads.snapshot(USER, "alpha", 50).head_message_id
    new = [h.world.dbs["alpha"].append("s1", "assistant", f"n{i}") for i in range(3)]
    page = h.reads.history(USER, "alpha", head, 100)  # type: ignore[arg-type]
    assert isinstance(page, HistoryPage) and _ids(page) == new
    assert page.head_message_id == new[-1]
    page = h.reads.history(USER, "alpha", ids[0], 2)
    assert isinstance(page, HistoryPage) and _ids(page) == ids[1:3]
    assert page.head_message_id == new[-1]  # more rows remain after this page


def test_in_place_compaction_is_history_rewritten(h: Harness) -> None:
    h.start("s1")
    head = h.reads.snapshot(USER, "alpha", 50).head_message_id
    h.world.dbs["alpha"].compact_in_place("s1", keep=2)
    reset = h.reads.history(USER, "alpha", head, 100)  # type: ignore[arg-type]
    assert reset == HistoryReset(reason=ResetReason.HISTORY_REWRITTEN)
    # A second device holding the same stale cursor after the baseline moved: RO-8 (a).
    reset = h.reads.history(USER, "alpha", head, 100)  # type: ignore[arg-type]
    assert reset == HistoryReset(reason=ResetReason.HISTORY_REWRITTEN)


def test_row_count_drop_is_history_rewritten(h: Harness) -> None:
    """RO-8 (b): the active row count dropped although the cursor row itself survived."""
    ids = h.start("s1")
    h.reads.snapshot(USER, "alpha", 50)
    db = h.world.dbs["alpha"]
    for row in db.rows:
        if row["id"] in ids[1:3]:
            row["active"] = 0
    reset = h.reads.history(USER, "alpha", ids[-1], 100)
    assert reset == HistoryReset(reason=ResetReason.HISTORY_REWRITTEN)


def test_new_session_is_session_replaced(h: Harness) -> None:
    ids = h.start("s1")
    h.reads.snapshot(USER, "alpha", 50)
    chat = h.chat()
    h.world.start_conversation("alpha", chat, "s2")  # `/new`
    h.world.dbs["alpha"].append("s2", "user", "fresh")
    reset = h.reads.history(USER, "alpha", ids[-1], 100)
    assert reset == HistoryReset(reason=ResetReason.SESSION_REPLACED)
    assert h.baseline()["session_id"] == "s2"


def test_session_replaced_across_an_hmp_restart(h: Harness) -> None:
    """RO-6 / FR-052: the replacement happened while HMP was down; the persisted baseline
    sees it."""
    ids = h.start("s1")
    chat = h.chat()
    h.reads.snapshot(USER, "alpha", 50)
    h.store.close()  # HMP stops
    h.world.start_conversation("alpha", chat, "s2")  # `/new` while HMP is down
    h.world.dbs["alpha"].append("s2", "user", "fresh")
    h.open()  # HMP starts again: new process state, same store file
    reset = h.reads.history(USER, "alpha", ids[-1], 100)
    assert reset == HistoryReset(reason=ResetReason.SESSION_REPLACED)


def test_pruned_route_is_session_replaced(h: Harness) -> None:
    ids = h.start("s1")
    h.reads.snapshot(USER, "alpha", 50)
    h.world.adapter._session_store.entries.clear()
    assert h.reads.history(USER, "alpha", ids[-1], 100) == HistoryReset(
        reason=ResetReason.SESSION_REPLACED
    )
    assert h.baseline() is None


def test_compression_continuation_is_lineage_changed(h: Harness) -> None:
    ids = h.start("s1")
    h.reads.snapshot(USER, "alpha", 50)
    db = h.world.dbs["alpha"]
    db.children["s1"] = "s1b"  # the tip moves; the routed session is unchanged
    db.append("s1b", "assistant", "after compression")
    assert h.reads.history(USER, "alpha", ids[-1], 100) == HistoryReset(
        reason=ResetReason.LINEAGE_CHANGED
    )
    # The routed session itself moves to the continuation: still the same lineage.
    h.world.start_conversation("alpha", h.chat(), "s1b")
    assert h.reads.history(USER, "alpha", ids[-1], 100) == HistoryReset(
        reason=ResetReason.LINEAGE_CHANGED
    )


def test_unresolvable_cursor(h: Harness) -> None:
    h.start("s1")
    h.reads.snapshot(USER, "alpha", 50)
    assert h.reads.history(USER, "alpha", 10_000, 100) == HistoryReset(
        reason=ResetReason.CURSOR_NOT_RESOLVABLE
    )
    other = h.world.dbs["alpha"].append("s-foreign", "user", "not ours")
    assert h.reads.history(USER, "alpha", other, 100) == HistoryReset(
        reason=ResetReason.CURSOR_NOT_RESOLVABLE
    )


def test_cursor_for_never_started_conversation(h: Harness) -> None:
    assert h.reads.history(USER, "alpha", 5, 100) == HistoryReset(
        reason=ResetReason.CURSOR_NOT_RESOLVABLE
    )
    assert h.chats_count() == 0


def test_history_never_mixes_users(h: Harness) -> None:
    h.world.approve(OTHER, "alpha")
    mine = h.start("s-mine", USER)
    theirs = h.start("s-theirs", OTHER)
    page = h.reads.history(USER, "alpha", 0, 100)
    assert isinstance(page, HistoryPage) and _ids(page) == mine
    assert h.reads.history(USER, "alpha", theirs[0], 100) == HistoryReset(
        reason=ResetReason.CURSOR_NOT_RESOLVABLE
    )


# --------------------------------------------------------------------------------------------------
# Amendment A1 (session browsing, OD-F9/OD-F10, OD-F11): SES-1 list, SES-2 messages
# --------------------------------------------------------------------------------------------------


def _summary(
    session_id: str = "s1",
    *,
    title: str | None,
    source: str = "cli",
    hidden: bool = False,
) -> SessionSummary:
    return SessionSummary(
        session_id=session_id,
        title=title,
        source=source,
        started_at=0.0,
        last_active_at=None,
        message_count=0,
        hidden=hidden,
    )


@pytest.mark.parametrize(
    ("title", "source", "hidden", "expected"),
    [
        # Positive: the canonical, hidden "Bot Chat" -- whatever its source label.
        ("Bot Chat", "desktop", True, True),
        ("Bot Chat", "acp", True, True),
        # Negative: OD-F11's named channel sources, none titled "Bot Chat".
        (None, "cli", False, False),
        ("A CLI session", "cli", False, False),
        ("Team chat", "telegram", False, False),
        ("Team chat", "discord", False, False),
        (None, "cron", False, False),
        # Negative: right title, but not hidden -- an ordinary session a user happened to name
        # "Bot Chat" (Hermes itself allows renaming a non-canonical, non-hidden row freely;
        # `_set_session_title`'s "Hidden is the discriminator" rule).
        ("Bot Chat", "cli", False, False),
        # Negative: hidden, but wrong title.
        ("Something else", "desktop", True, False),
        # Negative: no title at all.
        (None, "desktop", True, False),
    ],
)
def test_is_bot_view_session_selector(
    title: str | None, source: str, hidden: bool, expected: bool
) -> None:
    """OD-F11 (2026-09-27): the selector matches Hermes's own canonical-Bot-Chat identity rule
    (`_is_bot_view_session`'s docstring cites the three Hermes sources), never a source check."""
    assert _is_bot_view_session(_summary(title=title, source=source, hidden=hidden)) is expected


def test_list_sessions_gate_denies_before_any_lookup(h: Harness) -> None:
    with pytest.raises(HmpError) as err:
        h.reads.list_sessions(OTHER, "alpha", cursor=None, limit=30)
    assert err.value.code == ErrorCode.FORBIDDEN
    assert "list_sessions" not in h.log


def test_list_sessions_is_mobile_and_od_f11_filtering(h: Harness) -> None:
    """OD-F11 (2026-09-27, superseding OD-F10's breadth): only the bot's own canonical "Bot Chat"
    and the caller's own session are ever listed -- never a channel session (Telegram here),
    whatever its own title says."""
    h.world.dbs["alpha"].seed_session("s-mine", source="local")
    mine = h.start("s-mine")  # the phone's own HMP conversation
    db = h.world.dbs["alpha"]
    db.seed_session("s-telegram", source="telegram", title="hi\x00there", started_at=5.0)
    db.append("s-telegram", "user", "hey")
    db.seed_session("s-bot-chat", source="desktop", title="Bot Chat", hidden=True, started_at=6.0)
    db.append("s-bot-chat", "user", "bot chat turn")
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    by_source = {item.source: item for item in page.sessions}
    assert set(by_source) == {"local", "desktop"}  # "telegram" never listed (OD-F11)
    assert by_source["local"].is_mobile is True and by_source["local"].message_count == len(mine)
    assert by_source["desktop"].is_mobile is False
    assert by_source["desktop"].title == "Bot Chat"


def test_list_sessions_ref_is_stable_across_calls(h: Harness) -> None:
    h.world.dbs["alpha"].seed_session("s1", source="desktop", title="Bot Chat", hidden=True)
    ref1 = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    ref2 = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    assert ref1 == ref2 and ref1.startswith("ses1_")


def test_list_sessions_ordinary_sessions_are_never_read_or_paged(h: Harness) -> None:
    """None of these three ordinary sessions is the canonical Bot Chat or the caller's own: the
    page is empty with no `next_cursor`, and no bridge call names any of them."""
    db = h.world.dbs["alpha"]
    for i, source in enumerate(("cli", "telegram", "discord")):
        db.seed_session(f"s{i}", source=source, title=f"secret-{i}", started_at=float(i))
        db.append(f"s{i}", "user", "private")
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=2)
    assert page.sessions == () and page.next_cursor is None
    assert "list_sessions" not in h.log and "session_summary" not in h.log


def _bot_chat(h: Harness, session_id: str = "bc", **kw: Any) -> None:
    kw.setdefault("source", "desktop")
    kw.setdefault("title", "Bot Chat")
    kw.setdefault("hidden", True)
    kw.setdefault("started_at", 1.0)
    h.world.dbs["alpha"].seed_session(session_id, **kw)
    h.world.dbs["alpha"].append(session_id, "user", "canonical turn", timestamp=10.0)


def test_visible_titled_compression_child_keeps_bot_chat_list_and_ref(h: Harness) -> None:
    """Hermes's compression INSERT does not copy hidden; the root remains the identity."""
    _bot_chat(h)
    old_ref = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    db = h.world.dbs["alpha"]
    db.sessions["bc"]["title"] = None
    db.sessions["bc"]["end_reason"] = "compression"
    db.seed_session("tip", source="desktop", title="Bot Chat", parent_session_id="bc")
    db.children["bc"] = "tip"
    new_id = db.append("tip", "assistant", "continued", timestamp=20.0)

    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    assert [(item.title, item.is_mobile) for item in page.sessions] == [("Bot Chat", False)]
    assert page.sessions[0].session_ref.startswith("ses1_")
    # The list may mint a new ref for the projected tip; the old root ref remains readable.
    snap = h.reads.session_snapshot(USER, "alpha", old_ref, 50)
    assert any(message.id == new_id for message in snap.messages)


def test_list_sessions_35_newer_cron_sessions_do_not_hide_the_bot_chat(h: Harness) -> None:
    """SES-1 used to fetch a raw recent page and filter after paginating, so enough newer
    sessions pushed the Bot Chat off it. It is now resolved directly: exactly it comes back, and
    nothing about the 35 others is read or shown."""
    _bot_chat(h)
    before = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    db = h.world.dbs["alpha"]
    for i in range(35):
        db.seed_session(
            f"cron-{i}", source="cron", title=f"cron-title-{i}", started_at=100.0 + i
        )
        db.append(f"cron-{i}", "user", f"cron-body-{i}", timestamp=1000.0 + i)
    h.log.clear()
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    assert [(i.title, i.source, i.is_mobile) for i in page.sessions] == [
        ("Bot Chat", "desktop", False)
    ]
    assert page.next_cursor is None  # no extra page: nothing but the two allowed sessions exists
    assert page.sessions[0].session_ref == before.sessions[0].session_ref  # refs stay stable
    assert "cron" not in repr(page)
    assert "list_sessions" not in h.log and h.log.count("session_summary") <= 2
    # Even with a smaller page size the cursor only ever points at the (<= 2) allowed sessions.
    small = h.reads.list_sessions(USER, "alpha", cursor=None, limit=1)
    assert len(small.sessions) == 1 and small.next_cursor is None


def test_list_sessions_own_and_bot_chat_page_through_at_most_two_items(h: Harness) -> None:
    _bot_chat(h)
    h.world.dbs["alpha"].seed_session("s-mine", source="local", started_at=2.0)
    h.start("s-mine")
    for i in range(35):
        h.world.dbs["alpha"].seed_session(f"cron-{i}", source="cron", started_at=100.0 + i)
    page1 = h.reads.list_sessions(USER, "alpha", cursor=None, limit=1)
    assert len(page1.sessions) == 1 and page1.next_cursor is not None
    page2 = h.reads.list_sessions(USER, "alpha", cursor=page1.next_cursor, limit=1)
    assert len(page2.sessions) == 1 and page2.next_cursor is None
    both = {page1.sessions[0].source, page2.sessions[0].source}
    assert both == {"local", "desktop"}
    full = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    assert len(full.sessions) == 2 and full.next_cursor is None
    past_the_end = h.reads.list_sessions(USER, "alpha", cursor=_encode_sessions_cursor(2), limit=1)
    assert past_the_end.sessions == () and past_the_end.next_cursor is None


def test_list_sessions_visible_only_bot_chat_is_not_listed(h: Harness) -> None:
    """A visible session that merely carries the title is not the canonical Bot Chat (A1 needs
    hidden) -- and neither is a hidden but archived one."""
    _bot_chat(h, hidden=False)
    assert h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions == ()
    h.world.dbs["alpha"].sessions["bc"]["hidden"] = True
    assert len(h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions) == 1
    h.world.dbs["alpha"].sessions["bc"]["archived"] = True
    assert h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions == ()


def test_list_sessions_compressed_bot_chat_lists_the_tip_once(h: Harness) -> None:
    db = h.world.dbs["alpha"]
    db.seed_session("root", source="desktop", hidden=True, end_reason="compression")
    db.seed_session(
        "tip", source="desktop", title="Bot Chat", hidden=True, parent_session_id="root"
    )
    db.children["root"] = "tip"
    db.append("root", "user", "before", timestamp=1.0)
    db.append("tip", "assistant", "after", timestamp=2.0)
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    assert [(i.title, i.message_count) for i in page.sessions] == [("Bot Chat", 1)]
    snap = h.reads.session_snapshot(USER, "alpha", page.sessions[0].session_ref, 50)
    assert [m.text for m in snap.messages] == ["after"]


def test_list_sessions_unqualified_build_lists_only_the_own_conversation(h: Harness) -> None:
    """The title lookup is outside the read fingerprint: on a build without the exact-build
    direct-send qualification no Bot Chat is listed, though the caller's own session still is."""
    _bot_chat(h)
    h.world.dbs["alpha"].seed_session("s-mine", source="local", started_at=2.0)
    h.start("s-mine")
    reads = _unqualified_reads(h)
    page = reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    assert [i.source for i in page.sessions] == ["local"]
    assert "get_session_by_title" not in h.world.dbs["alpha"].calls


def _unqualified_reads(h: Harness) -> Reads:
    bridge = HermesReadBridge(
        h.world.adapter,
        StoreDirectory(h.store),  # type: ignore[arg-type]
        hermes=h.world.api,  # type: ignore[arg-type]
    )
    return Reads(
        bridge,
        h.store,
        iid="i" * 52,
        guarantees=Guarantees,
        write_gate=lambda: WriteGate(WriteGateState.CLOSED, "guarantees_unavailable"),
        clock=lambda: h.now,
    )


def test_is_bot_view_session_rejects_archived() -> None:
    archived = SessionSummary(
        session_id="s",
        title="Bot Chat",
        source="desktop",
        started_at=0.0,
        last_active_at=None,
        message_count=0,
        hidden=True,
        archived=True,
    )
    assert _is_bot_view_session(archived) is False


def test_list_sessions_malformed_cursor_is_bad_request(h: Harness) -> None:
    for bad in ("not-b64u!!", "AA", ""):
        with pytest.raises(HmpError) as err:
            h.reads.list_sessions(USER, "alpha", cursor=bad, limit=30)
        assert err.value.code == ErrorCode.BAD_REQUEST


def test_session_snapshot_and_history_unknown_ref_is_not_found(h: Harness) -> None:
    with pytest.raises(HmpError) as err:
        h.reads.session_snapshot(USER, "alpha", "ses1_unguessable", 200)
    assert err.value.code == ErrorCode.NOT_FOUND
    with pytest.raises(HmpError) as err:
        h.reads.session_history(USER, "alpha", "ses1_unguessable", 1, 100)
    assert err.value.code == ErrorCode.NOT_FOUND


def test_session_ref_foreign_user_is_not_found(h: Harness) -> None:
    h.world.approve(OTHER, "alpha")
    h.world.dbs["alpha"].seed_session("s1", source="desktop", title="Bot Chat", hidden=True)
    ref = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    with pytest.raises(HmpError) as err:
        h.reads.session_snapshot(OTHER, "alpha", ref, 200)
    assert err.value.code == ErrorCode.NOT_FOUND


def _session_ref(h: Harness, session_id: str, source: str = "desktop") -> str:
    """A `session_ref` obtainable via `list_sessions`: under OD-F11 that means the session must be
    the canonical, hidden "Bot Chat" -- otherwise it is never listed and never minted a ref."""
    h.world.dbs["alpha"].seed_session(session_id, source=source, title="Bot Chat", hidden=True)
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    return next(i.session_ref for i in page.sessions if i.session_ref)


def test_session_snapshot_reads_the_foreign_session(h: Harness) -> None:
    db = h.world.dbs["alpha"]
    db.append("s-foreign", "user", "hello there")
    ids = [db.rows[-1]["id"]]
    ref = _session_ref(h, "s-foreign")
    snap = h.reads.session_snapshot(USER, "alpha", ref, 200)
    assert snap.session_ref == ref and [m.id for m in snap.messages] == ids
    assert snap.head_message_id == ids[-1] and snap.truncated is False


def test_session_history_pages_and_resets(h: Harness) -> None:
    db = h.world.dbs["alpha"]
    ref = _session_ref(h, "s-foreign")
    ids = [db.append("s-foreign", "user" if i % 2 == 0 else "assistant", f"m{i}") for i in range(3)]
    h.reads.session_snapshot(USER, "alpha", ref, 200)  # seeds the baseline
    page = h.reads.session_history(USER, "alpha", ref, ids[0], 100)
    assert isinstance(page, HistoryPage) and [m.id for m in page.messages] == ids[1:]

    db.compact_in_place("s-foreign", keep=1)
    reset = h.reads.session_history(USER, "alpha", ref, ids[-1], 100)
    assert reset == HistoryReset(reason=ResetReason.HISTORY_REWRITTEN)


def test_session_history_lineage_changed_on_compression(h: Harness) -> None:
    db = h.world.dbs["alpha"]
    ref = _session_ref(h, "s-root")
    db.sessions["s-root"]["end_reason"] = "compression"
    db.append("s-root", "user", "first")
    h.reads.session_snapshot(USER, "alpha", ref, 200)  # baseline at the root
    db.append("s-tip", "assistant", "second")
    db.seed_session("s-tip", source="desktop", parent_session_id="s-root")
    db.children["s-root"] = "s-tip"
    reset = h.reads.session_history(USER, "alpha", ref, 1, 100)
    assert reset == HistoryReset(reason=ResetReason.LINEAGE_CHANGED)


def test_session_baseline_never_mixes_with_default_conversation_baseline(h: Harness) -> None:
    """SES-2's baseline is its own table (`other_session_baselines`), keyed additionally by
    `session_id`, so browsing a foreign session can never perturb the phone's own conversation
    reset detection (RO-6), and vice versa."""
    mine = h.start("s-mine")
    ref = _session_ref(h, "s-foreign")
    h.world.dbs["alpha"].append("s-foreign", "user", "hi")
    h.reads.session_snapshot(USER, "alpha", ref, 200)
    page = h.reads.history(USER, "alpha", mine[0], 100)
    assert isinstance(page, HistoryPage) and _ids(page) == mine[1:]


# --------------------------------------------------------------------------------------------------
# SES-2 re-checks the CURRENT OD-F11 selector: a ref minted while a session qualified is not a
# standing capability.
# --------------------------------------------------------------------------------------------------


def _shape(err: HmpError) -> tuple[Any, int, dict[str, object]]:
    return (err.code, err.http, dict(err.extras))


def _both_refused(h: Harness, ref: str, *, user: str = USER, profile: str = "alpha") -> list[Any]:
    out = []
    for call in (
        lambda: h.reads.session_snapshot(user, profile, ref, 50),
        lambda: h.reads.session_history(user, profile, ref, 0, 50),
    ):
        with pytest.raises(HmpError) as err:
            call()
        out.append(_shape(err.value))
    return out


def _assert_dead_ref(h: Harness, ref: str, **kw: str) -> None:
    """`404 not_found` for both SES-2 routes, before any row is read, and byte-for-byte the answer
    an unknown ref gets -- so a stale or foreign ref cannot be told apart from a made-up one."""
    h.log.clear()
    got = _both_refused(h, ref, **kw)
    assert not {"latest", "after", "head"} & set(h.log)  # no row content was ever read
    assert got == _both_refused(h, "ses1_unguessable", **kw)
    assert got[0][0] == ErrorCode.NOT_FOUND and got[0][1] == 404


def _listed_bot_chat_ref(h: Harness) -> str:
    _bot_chat(h)
    page = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30)
    ref = page.sessions[0].session_ref
    assert h.reads.session_snapshot(USER, "alpha", ref, 50).messages  # alive while canonical
    return ref


def test_session_ref_dies_when_the_bot_chat_is_archived(h: Harness) -> None:
    ref = _listed_bot_chat_ref(h)
    h.world.dbs["alpha"].sessions["bc"]["archived"] = True
    _assert_dead_ref(h, ref)


def test_session_ref_dies_when_the_bot_chat_is_unhidden(h: Harness) -> None:
    ref = _listed_bot_chat_ref(h)
    h.world.dbs["alpha"].sessions["bc"]["hidden"] = False
    _assert_dead_ref(h, ref)


def test_session_ref_dies_when_the_bot_chat_is_retitled(h: Harness) -> None:
    ref = _listed_bot_chat_ref(h)
    h.world.dbs["alpha"].sessions["bc"]["title"] = "Something else"
    _assert_dead_ref(h, ref)


def test_session_ref_dies_when_the_bot_chat_is_replaced(h: Harness) -> None:
    """A different session becomes the canonical Bot Chat (not a compression of the old one): the
    old ref no longer names it, and the new one is readable under its own ref."""
    ref = _listed_bot_chat_ref(h)
    h.world.dbs["alpha"].sessions["bc"]["title"] = None
    _bot_chat(h, "bc2")
    _assert_dead_ref(h, ref)
    new_ref = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    assert new_ref != ref and h.reads.session_snapshot(USER, "alpha", new_ref, 50).messages


def test_session_ref_follows_compression_of_the_bot_chat(h: Harness) -> None:
    """Compression is not replacement: a ref for an ancestor id stays valid, reading the tip."""
    ref = _listed_bot_chat_ref(h)
    db = h.world.dbs["alpha"]
    db.sessions["bc"]["end_reason"] = "compression"
    db.seed_session("bc-tip", source="desktop", parent_session_id="bc", hidden=True)
    db.children["bc"] = "bc-tip"
    db.append("bc-tip", "assistant", "post-compression", timestamp=20.0)
    snap = h.reads.session_snapshot(USER, "alpha", ref, 50)
    assert [m.text for m in snap.messages] == ["post-compression"]


def test_manually_inserted_channel_session_ref_is_not_found(h: Harness) -> None:
    """A row planted in the ref table for a Telegram session (a store written by another build,
    a bug, a restore) was never eligible: it is dead with or without a canonical Bot Chat."""
    db = h.world.dbs["alpha"]
    db.seed_session("s-telegram", source="telegram", title="private chat")
    db.append("s-telegram", "user", "telegram-secret")
    ref = h.store.mint_or_get_session_ref(USER, "alpha", "s-telegram", "ses1_planted", T0)
    _assert_dead_ref(h, ref)
    _bot_chat(h)  # a canonical chat existing changes nothing for the planted ref
    _assert_dead_ref(h, ref)
    # Nor does a hidden, non-canonical session titled something else.
    db.seed_session("s-hidden", source="desktop", title="Hidden thing", hidden=True)
    db.append("s-hidden", "user", "hidden-secret")
    _assert_dead_ref(
        h, h.store.mint_or_get_session_ref(USER, "alpha", "s-hidden", "ses1_planted2", T0)
    )


def test_session_ref_profile_isolation(h: Harness) -> None:
    h.world.approve(USER, "beta")
    ref = _listed_bot_chat_ref(h)
    # The alpha ref presented under beta: unknown in beta's scope.
    _assert_dead_ref(h, ref, profile="beta")
    # A beta-scoped ref planted for alpha's canonical session id: beta has no such session.
    planted = h.store.mint_or_get_session_ref(USER, "beta", "bc", "ses1_beta_planted", T0)
    _assert_dead_ref(h, planted, profile="beta")
    # And beta's OWN canonical Bot Chat is unreachable through an alpha-scoped ref.
    beta = h.world.dbs["beta"]
    beta.seed_session("bcb", source="desktop", title="Bot Chat", hidden=True)
    beta.append("bcb", "user", "beta-secret")
    alpha_planted = h.store.mint_or_get_session_ref(USER, "alpha", "bcb", "ses1_alpha_planted", T0)
    _assert_dead_ref(h, alpha_planted)


def test_own_conversation_ref_dies_when_replaced_or_archived(h: Harness) -> None:
    h.world.dbs["alpha"].seed_session("s-mine", source="local", started_at=2.0)
    mine = h.start("s-mine")
    ref = h.reads.list_sessions(USER, "alpha", cursor=None, limit=30).sessions[0].session_ref
    assert len(h.reads.session_snapshot(USER, "alpha", ref, 50).messages) == len(mine)
    h.world.dbs["alpha"].sessions["s-mine"]["archived"] = True
    _assert_dead_ref(h, ref)
    h.world.dbs["alpha"].sessions["s-mine"]["archived"] = False
    h.world.dbs["alpha"].seed_session("s-mine2", source="local", started_at=3.0)
    h.world.start_conversation("alpha", h.chat(), "s-mine2")  # the conversation moved on
    _assert_dead_ref(h, ref)


def test_session_ref_on_an_unqualified_build_is_not_found(h: Harness) -> None:
    ref = _listed_bot_chat_ref(h)
    reads = _unqualified_reads(h)
    with pytest.raises(HmpError) as err:
        reads.session_snapshot(USER, "alpha", ref, 50)
    assert err.value.code == ErrorCode.NOT_FOUND


def test_session_ref_selector_failure_is_an_error_never_rows(h: Harness) -> None:
    ref = _listed_bot_chat_ref(h)
    h.log.clear()
    h.world.dbs["alpha"].fail = True
    with pytest.raises(HmpError) as err:
        h.reads.session_snapshot(USER, "alpha", ref, 50)
    assert err.value.code == ErrorCode.OTHER and err.value.http == 500
    assert not {"latest", "after", "head"} & set(h.log)
    h.world.dbs["alpha"].fail = False
    h.world.dbs["alpha"].sessions["bc"]["archived"] = None  # flag cannot be established
    with pytest.raises(HmpError) as err:
        h.reads.session_history(USER, "alpha", ref, 0, 50)
    assert err.value.code == ErrorCode.OTHER and err.value.http == 500


# --------------------------------------------------------------------------------------------------
# T029 P6 outcome table (PR6-1), no code relay (PR6-2), instance-wide note (PR6-3)
# --------------------------------------------------------------------------------------------------


def _authorize(h: Harness, user: str, profile: str) -> Any:
    import asyncio

    async def main() -> Any:
        try:
            return h.authorize.authorize(user, profile)
        finally:
            await asyncio.sleep(0)

    return asyncio.run(main())


def test_p6_authorized(h: Harness) -> None:
    assert _authorize(h, USER, "alpha") == (200, {"authz": "authorized"})
    assert h.world.adapter.handled == [] and h.chats_count() == 0


@pytest.mark.parametrize(
    ("profile", "setup", "code", "http", "authz"),
    [
        ("alpha", "allow_all", ErrorCode.REFUSED_ALLOW_ALL, 409, "refused_allow_all"),
        ("lonely", None, ErrorCode.NOT_ROUTED, 409, "not_routed"),
        ("ghost", None, ErrorCode.NOT_ROUTED, 409, "not_served"),
        ("alpha", "raises", ErrorCode.OTHER, 503, "unverifiable"),
    ],
)
def test_p6_refusals(
    h: Harness, profile: str, setup: str | None, code: ErrorCode, http: int, authz: str
) -> None:
    if setup == "allow_all":
        h.world.runner.allow_all_routed = {"alpha"}
    elif setup == "raises":
        h.world.runner.authz_raises = True
    with pytest.raises(HmpError) as err:
        _authorize(h, USER, profile)
    assert (err.value.code, err.value.http, err.value.extras["authz"]) == (code, http, authz)
    if authz == "unverifiable":
        assert err.value.extras["why"] == "unverifiable"
    assert h.world.adapter.handled == [] and h.chats_count() == 0


def test_p6_pending_sends_the_trigger_and_never_relays_a_code(h: Harness) -> None:
    status, body = _authorize(h, OTHER, "alpha")
    assert status == 202
    assert set(body) == {"authz", "user_id", "instruction", "approve_command"}
    assert body["authz"] == "pending_operator" and body["user_id"] == OTHER
    # SR-5: the instruction is worded conditionally -- it never asserts a request exists.
    assert body["instruction"].startswith(f"If a hmp pairing request for user {OTHER} appears")
    assert "hermes -p alpha pairing approve hmp <request_id>" in body["instruction"]
    # approve_command (owner requirement, 2026-09-27): one copy-pasteable command that finds and
    # approves only this user's own pending hmp request(s) on this profile.
    assert body["approve_command"] == (
        "hermes -p alpha pairing list | "
        f"awk -v u={OTHER} '$1==\"hmp\" && $3==u {{print $2}}' | "
        'while read -r id; do hermes -p alpha pairing approve hmp "$id"; done'
    )
    assert len(h.world.adapter.handled) == 1 and h.chats_count() == 1
    # Hermes answers the trigger with a pairing code through the adapter's `send`; nothing
    # the bridge could return reaches the body (PR6-2). Never in `instruction` or
    # `approve_command` either -- both are built only from fixed text, the profile name and the
    # caller's own user_id.
    assert "code" not in str(body).lower()
    # A second request reuses the same chat (the session key never moves), and -- inside the
    # SR-5 cooldown window -- sends no second trigger.
    chat = h.store.get_chat(OTHER, "alpha", "default")["chat_id"]
    status2, body2 = _authorize(h, OTHER, "alpha")
    assert h.store.get_chat(OTHER, "alpha", "default")["chat_id"] == chat and h.chats_count() == 1
    assert status2 == 202 and body2["authz"] == "pending_operator"
    # The cooldown only suppresses the trigger; the response -- instruction and approve_command
    # both -- is still returned in full on every call.
    assert body2["instruction"] == body["instruction"]
    assert body2["approve_command"] == body["approve_command"]
    assert len(h.world.adapter.handled) == 1  # no second trigger


# --------------------------------------------------------------------------------------------------
# Live-bug fix (multiplexed gateway): `Authorize`'s own `on_served_profiles` hook -- `authorize()`
# has no served-set of its own on hand, so on a successful call it fetches one just for the hook.
# --------------------------------------------------------------------------------------------------


def _authorize_with_hook(h: Harness, on_served_profiles: Any) -> Authorize:
    return Authorize(
        h.recorder, h.store, clock=lambda: h.now, on_served_profiles=on_served_profiles
    )


def test_authorize_calls_the_served_profiles_hook_on_success(h: Harness) -> None:
    import asyncio

    seen: list[list[str]] = []
    authorize = _authorize_with_hook(h, seen.append)

    async def main() -> Any:
        try:
            return authorize.authorize(USER, "alpha")
        finally:
            await asyncio.sleep(0)

    assert asyncio.run(main()) == (200, {"authz": "authorized"})
    assert seen == [["alpha", "beta", "lonely"]]


def test_authorize_hook_failure_never_breaks_the_authorize_read(h: Harness) -> None:
    import asyncio

    def boom(_served: Any) -> None:
        raise RuntimeError("disk full")

    authorize = _authorize_with_hook(h, boom)

    async def main() -> Any:
        try:
            return authorize.authorize(USER, "alpha")
        finally:
            await asyncio.sleep(0)

    assert asyncio.run(main()) == (200, {"authz": "authorized"})  # must not raise


def test_authorize_without_a_hook_is_unaffected(h: Harness) -> None:
    # `h.authorize` is built with no `on_served_profiles` (the `Harness` default).
    assert _authorize(h, USER, "alpha") == (200, {"authz": "authorized"})


# --------------------------------------------------------------------------------------------------
# approve_command (owner requirement, 2026-09-27): quoting and no code relay
# --------------------------------------------------------------------------------------------------


def test_approve_command_shape_for_a_plain_profile() -> None:
    got = approve_command("alpha", OTHER)
    assert got == (
        "hermes -p alpha pairing list | "
        f"awk -v u={OTHER} '$1==\"hmp\" && $3==u {{print $2}}' | "
        'while read -r id; do hermes -p alpha pairing approve hmp "$id"; done'
    )


@pytest.mark.parametrize(
    "profile",
    [
        "my profile",  # a space
        "o'brien",  # an embedded single quote
        "$(rm -rf /)",  # a command substitution attempt
        "a;b",  # a statement separator
        "a`b`c",  # backticks
        "a\nb",  # an embedded newline
        "",  # empty
    ],
)
def test_approve_command_quotes_odd_profile_names_safely(profile: str) -> None:
    import shlex

    got = approve_command(profile, OTHER)
    # The command is built only from two `hermes -p <profile> ...` invocations and one `awk -v
    # u=<user_id> ...`; every occurrence of the profile is exactly one shlex-quoted shell word, so
    # re-splitting the whole line must reproduce it byte for byte, whatever the profile contains.
    words = shlex.split(got)
    assert words.count(profile) == 2
    assert f"u={OTHER}" in got  # OTHER itself is always shlex-safe unquoted (hmpu_ + hex)
    # The quoted profile can never let the profile's own text break out into a second shell
    # command: shlex.split above is the proof (it never raises and recovers the exact profile as
    # a single word, never as a bare fragment like a stray "rm").
    assert "rm" not in words or profile == "rm"


def test_approve_command_never_carries_a_hermes_pairing_code() -> None:
    # approve_command is built only from fixed text, the profile name and the caller's own
    # user_id (PR6-2): the same inputs as `instruction`, never Hermes's reply to the trigger.
    got = approve_command("alpha", OTHER)
    assert "code" not in got.lower()


def test_p6_authorize_cooldown_expires(h: Harness) -> None:
    """SR-5: once the cooldown window has passed, a further call sends a fresh trigger again."""
    from hmp_plugin.contract import AUTHORIZE_TRIGGER_COOLDOWN_S

    _authorize(h, OTHER, "alpha")
    assert len(h.world.adapter.handled) == 1
    h.now += AUTHORIZE_TRIGGER_COOLDOWN_S - 1
    _authorize(h, OTHER, "alpha")
    assert len(h.world.adapter.handled) == 1  # still inside the window
    h.now += 1
    _authorize(h, OTHER, "alpha")
    assert len(h.world.adapter.handled) == 2  # window elapsed: a fresh trigger


def test_p6_trigger_failure_is_unverifiable(h: Harness) -> None:
    h.log.clear()
    with pytest.raises(HmpError) as err:
        h.authorize.authorize(OTHER, "alpha")  # no running loop: no hand-off possible
    assert err.value.http == 503 and err.value.extras["authz"] == "unverifiable"


def test_p6_instance_wide_note(h: Harness) -> None:
    h.world.api.env["GATEWAY_ALLOWED_USERS"] = "someone-else"
    status, body = _authorize(h, OTHER, "alpha")
    assert status == 202 and body["note"] == INSTANCE_WIDE_NOTE
    # OD-F6(c): HMP only discloses. Nothing it did changed a grant.
    assert h.world.runner.approved == {"alpha": {USER}}
    assert h.world.api.env == {"GATEWAY_ALLOWED_USERS": "someone-else"}


# --------------------------------------------------------------------------------------------------
# Through the F1 route table
# --------------------------------------------------------------------------------------------------


def _wire_env(tmp_path: Path) -> tuple[hmp_kit.Env, World]:
    env = hmp_kit.Env(tmp_path / "hmp")
    world = World(tmp_path / "hermes")
    bridge = HermesReadBridge(
        world.adapter,
        StoreDirectory(env.store),
        hermes=world.api,  # type: ignore[arg-type]
        title_lookup_qualified=True,
    )
    env.ctx.bridge = bridge
    env.ctx.reads = Reads(
        bridge,
        env.store,
        iid=env.iid,
        guarantees=env.ctx.guarantees,
        write_gate=env.ctx.write_gate,
        clock=env.clock,
    )
    env.ctx.authorize = Authorize(bridge, env.store, clock=env.clock)
    return env, world


def test_routes_end_to_end(tmp_path: Path) -> None:
    env, world = _wire_env(tmp_path)

    async def scenario(client: Any) -> None:
        dev = await hmp_kit.pair(env, client)
        headers = env.headers(dev)
        user_id = env.store.get_device(dev.device_id)["user_id"]

        status, body = await hmp_kit.get(client, "/bots", headers=headers)
        assert status == 200 and type(body["served_at"]) is int
        assert body["instance"] == env.iid and body["write_gate"]["state"] == "closed"
        assert set(body["guarantees"]) == {
            "no_defer",
            "atomic_anchor",
            "approval_request_id",
            "confirmed_settle",
        }
        assert [b["authz"] for b in body["bots"]] == ["pending_operator"] * 2 + ["not_routed"]

        status, body = await hmp_kit.post(client, "/bots/alpha/authorize", {}, headers=headers)
        assert status == 202 and body["authz"] == "pending_operator"
        world.approve(user_id, "alpha")

        chat = env.store.get_chat(user_id, "alpha", "default")["chat_id"]
        status, body = await hmp_kit.get(
            client, "/bots/alpha/conversations/default", headers=headers
        )
        assert status == 200 and body["head_message_id"] is None and body["messages"] == []

        world.start_conversation("alpha", chat, "s1")
        ids = [world.dbs["alpha"].append("s1", "user", f"[F1 SYNTHETIC] {i}") for i in range(3)]
        status, body = await hmp_kit.get(
            client, "/bots/alpha/conversations/default?limit=2", headers=headers
        )
        assert status == 200 and [m["id"] for m in body["messages"]] == ids[1:]
        assert body["head_message_id"] == ids[-1] and body["tail"]["seq"] == 0

        status, body = await hmp_kit.get(
            client, f"/bots/alpha/conversations/default/messages?after={ids[0]}", headers=headers
        )
        assert status == 200 and [m["id"] for m in body["messages"]] == ids[1:]

        world.dbs["alpha"].compact_in_place("s1", keep=1)
        status, body = await hmp_kit.get(
            client, f"/bots/alpha/conversations/default/messages?after={ids[-1]}", headers=headers
        )
        assert status == 200
        assert body == {"reset": {"reason": "history_rewritten", "snapshot_required": True}}

        for path in (
            "/bots/alpha/conversations/other",
            "/bots/alpha/conversations/other/messages?after=1",
            "/bots/alpha/conversations/Default",
        ):
            status, body = await hmp_kit.get(client, path, headers=headers)
            assert status == 404 and body["error"]["code"] == "not_found"

        status, body = await hmp_kit.get(
            client, "/bots/beta/conversations/default", headers=headers
        )
        assert status == 403 and body["error"] == {
            "code": "forbidden",
            "message": "forbidden",
            "authz": "pending_operator",
        }

        # -- Amendment A1 (session browsing, OD-F9/OD-F10, OD-F11): SES-1/SES-2 end to end ------
        world.dbs["alpha"].seed_session("s1", source="local")  # the phone's own session ("s1")
        # A channel session (OD-F11: never listed) and the bot's own canonical, hidden "Bot Chat"
        # (OD-F11: the only non-mobile row ever listed).
        world.dbs["alpha"].seed_session("s-telegram", source="telegram", title="unrelated chat")
        world.dbs["alpha"].seed_session(
            "s-bot-chat", source="desktop", title="Bot Chat", hidden=True
        )
        did = world.dbs["alpha"].append("s-bot-chat", "user", "hi from the bot chat")

        status, body = await hmp_kit.get(client, "/bots/alpha/sessions", headers=headers)
        assert status == 200 and body["next_cursor"] is None
        by_source = {item["source"]: item for item in body["sessions"]}
        assert set(by_source) == {"local", "desktop"}  # "telegram" never listed (OD-F11)
        assert by_source["local"]["is_mobile"] is True  # the phone's own HMP conversation (s1)
        assert by_source["desktop"]["is_mobile"] is False
        assert by_source["desktop"]["title"] == "Bot Chat"
        ref = by_source["desktop"]["session_ref"]
        assert ref.startswith("ses1_")
        # Never on the wire: raw session_id, session_key, cwd, billing, model fields.
        desktop = by_source["desktop"]
        assert "session_id" not in desktop and "session_key" not in desktop

        status, body = await hmp_kit.get(
            client, f"/bots/alpha/sessions/{ref}/messages", headers=headers
        )
        assert status == 200 and body["session_ref"] == ref
        assert [m["id"] for m in body["messages"]] == [did]
        assert body["head_message_id"] == did and body["truncated"] is False

        status, body = await hmp_kit.get(
            client, f"/bots/alpha/sessions/{ref}/messages?after={did}", headers=headers
        )
        assert status == 200 and body["messages"] == [] and body["head_message_id"] == did

        status, body = await hmp_kit.get(
            client, "/bots/alpha/sessions/ses1_doesnotexist/messages", headers=headers
        )
        assert status == 404 and body["error"]["code"] == "not_found"

        status, body = await hmp_kit.get(
            client, "/bots/alpha/sessions?cursor=not-valid-base64!!", headers=headers
        )
        assert status == 400 and body["error"]["code"] == "bad_request"

        # A ref never leaks across bots: it was minted for alpha, not beta.
        status, body = await hmp_kit.get(
            client, f"/bots/beta/sessions/{ref}/messages", headers=headers
        )
        assert status == 403  # the per-bot gate refuses beta first (ERR-3 ordering)

    hmp_kit.run(env, scenario)
