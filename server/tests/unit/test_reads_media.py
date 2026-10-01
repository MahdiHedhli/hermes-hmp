"""S2d: the four read cores and their optional non-wire media twins, against golden closed-gate
bytes.

The scenario driver below imports only modules that exist at the accepted baseline `575a9bc`
(before any sidecar), so the SAME code produced `GOLDEN` there: `generate_golden` and
`generate_route_golden` were run against a read-only `git archive` copy of that commit (never a
checkout) and the output pasted below. Every comparison in this file is to that baseline record,
not to the new wrappers of this tree. Nothing here claims S2 is complete.

Bodies and logs are normalized by replacing the test temp root with `<T>`; logged strings over 40
characters become `<length:sha8>`. Bodies are pinned by SHA-256 and length.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import server, wire
from hmp_plugin.authorize import ensure_chat
from hmp_plugin.bridge import HermesReadBridge, StoreDirectory
from hmp_plugin.contract import (
    AuthzState,
    ConversationRef,
    ErrorCode,
    Guarantees,
    HistoryReset,
    HmpError,
    ResetReason,
    Row,
    WriteGate,
    WriteGateState,
)
from hmp_plugin.reads import Reads
from hmp_plugin.request_ctx import _plain
from hmp_plugin.store import Store

from . import hmp_kit
from .fake_hermes import World

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
USER = "hmpu_" + "a" * 32
OTHER = "hmpu_" + "b" * 32
T0 = 1_900_000_000
BASELINE_COMMIT = "575a9bc"


def sc() -> Any:
    """The carrier module, loaded lazily: the driver must also run where it does not exist."""
    return importlib.import_module("hmp_plugin.local_media_sidecar")


def _short(value: object) -> str:
    text = str(value)
    if len(text) <= 40:
        return text
    return f"<{len(text)}:{hashlib.sha256(text.encode()).hexdigest()[:8]}>"


def _digest(body: str) -> tuple[str, int]:
    raw = body.encode()
    return hashlib.sha256(raw).hexdigest(), len(raw)


class NoOptIn(HermesReadBridge):
    """A real bridge that does not select the media twins (the closed-gate shape)."""

    LOCAL_MEDIA_SIDECAR = False


class SpyPromptStore:
    """Records the observation hooks `Reads` calls, with the discard sets."""

    def __init__(self, log: list[str], tmp: Path) -> None:
        self.log, self.tmp = log, tmp

    def purge(self, now: int) -> None:
        self.log.append(f"purge {now}")

    def list_visible(self, iid: str, user_id: str, profile: str, *, now: int) -> list[Any]:
        self.log.append(f"list_visible {_short(iid)} {user_id[-4:]} {profile} {now}")
        return []

    def discard_durable_observations(
        self, iid: str, user_id: str, profile: str, pairs: set[tuple[str, str]]
    ) -> None:
        shown = sorted(
            f"{role}:{_short(text.replace(str(self.tmp), '<T>'))}" for role, text in pairs
        )
        self.log.append(f"discard {profile} {shown}")


def instrument(world: World, tmp: Path, events: list[str]) -> None:
    """One ordered log of every native call the bridge makes, with normalized arguments."""

    def arg(value: object) -> str:
        return _short(str(value).replace(str(tmp), "<T>"))

    def wrap(obj: Any, name: str, label: str) -> None:
        real = getattr(obj, name)

        def call(*a: Any, **k: Any) -> Any:
            # Arguments that are objects or carry a random chat id are not part of the record.
            if label in {"release", "authz", "lookup_session"}:
                events.append(label)
            else:
                pairs = [arg(x) for x in a] + [f"{key}={arg(v)}" for key, v in sorted(k.items())]
                events.append(f"{label}({','.join(pairs)})")
            return real(*a, **k)

        setattr(obj, name, call)

    for profile, db in world.dbs.items():
        for name in (
            "get_messages",
            "resolve_resume_session_id",
            "get_compression_chain",
            "get_active_message_ids",
            "get_session",
        ):
            wrap(db, name, f"{profile}.{name}")
    wrap(world.api, "acquire", "acquire")
    wrap(world.api, "release", "release")
    wrap(world.runner, "_routed_profile_home", "routed_home")
    wrap(world.runner, "_is_user_authorized_for_source", "authz")
    wrap(world.adapter._session_store, "lookup_by_session_key", "lookup_session")


_BASELINE_QUERIES = {
    "session_baselines": "SELECT * FROM session_baselines ORDER BY 1, 2, 3",
    "other_session_baselines": "SELECT * FROM other_session_baselines ORDER BY 1, 2, 3",
}


class Run:
    """One fake world, one real store, the real bridge and `Reads`. `mode`: `old` calls the four
    old methods; `media` and `unsupported` call the `*_with_media` twins and keep only `.public`
    as the observed result (the sidecar is kept aside)."""

    def __init__(
        self,
        tmp: Path,
        *,
        mode: str = "old",
        bridge_factory: Callable[..., Any] | None = None,
        approved: bool = True,
    ) -> None:
        self.tmp, self.mode = tmp, mode
        self.world = World(tmp / "w")
        self.store = Store(tmp / "hmp.sqlite3")
        self.store.migrate()
        self.events: list[str] = []
        self.prompt: list[str] = []
        instrument(self.world, tmp, self.events)
        factory = bridge_factory or (NoOptIn if mode == "unsupported" else HermesReadBridge)
        self.bridge = factory(self.world.adapter, StoreDirectory(self.store), hermes=self.world.api)
        self.reads = Reads(
            self.bridge,
            self.store,
            iid="i" * 52,
            guarantees=Guarantees,
            write_gate=lambda: WriteGate(WriteGateState.CLOSED, "guarantees_unavailable"),
            clock=lambda: T0,
            epoch="e" * 16,
            prompt_store=SpyPromptStore(self.prompt, tmp),
        )
        if approved:
            self.world.approve(USER, "alpha")
        self.steps: list[list[Any]] = []
        self.sidecars: dict[str, Any] = {}
        self.results: dict[str, Any] = {}

    # -- world helpers -------------------------------------------------------------------------

    @property
    def home(self) -> Path:
        return self.world.runner.homes["alpha"]

    @property
    def db(self) -> Any:
        return self.world.dbs["alpha"]

    def image(self, name: str = "gen_a.png", *, pad: int = 0, home: str | None = None) -> str:
        # The padding comes first, so a large `pad` pushes the `image` key past the tool-text cap.
        return json.dumps(
            {"pad": "x" * pad, "success": True, "image": f"{home or self.home}/cache/images/{name}"}
        )

    def tool(self, session: str, content: Any, name: str = "image_generate") -> int:
        row_id = self.db.next_id
        return self.db.append(
            session, "tool", content, tool_name=name, tool_call_id=f"call_{row_id}"
        )

    def start(self, session: str = "s1") -> None:
        chat = ensure_chat(self.store, USER, "alpha")
        self.world.start_conversation("alpha", chat, session)

    def seed_rows(self, session: str) -> list[int]:
        """Nine rows: ids 1..9 on a fresh database."""
        db, home = self.db, self.home
        return [
            db.append(session, "user", "hello"),
            self.tool(session, self.image("gen_a.png", pad=5000)),  # valid; `image` past the cap
            db.append(session, "assistant", f"MEDIA: {home}/cache/images/gen_a.png"),
            self.tool(session, json.dumps({"success": False, "error": "nope"})),  # invalid
            self.tool(session, self.image("x.png", home="/elsewhere/profile")),  # foreign prefix
            self.tool(session, self.image("gen_c.png", pad=70_000)),  # over 64 KiB
            self.tool(session, "ok", name="terminal"),  # normal tool
            self.tool(session, self.image("gen_b.png")),  # valid, short
            db.append(session, "assistant", "done"),
        ]

    def mint_ref(self, session_id: str, ref: str = "ses1_golden") -> str:
        return self.store.mint_or_get_session_ref(USER, "alpha", session_id, ref, T0)

    def race_tips(self, tips: list[str]) -> None:
        """The first calls of `resolve_resume_session_id` answer `tips`, then the real tip."""
        inner, queue = self.db.resolve_resume_session_id, list(tips)

        def resolve(session_id: str) -> str:
            tip = queue.pop(0) if queue else inner(session_id)
            self.events.append(f"  -> tip {_short(tip)}")
            return tip

        self.db.resolve_resume_session_id = resolve

    # -- observed calls ------------------------------------------------------------------------

    def snapshot(self, limit: int, name: str | None = None) -> Any:
        return self._do(name or f"snapshot_{limit}", "snapshot", (USER, "alpha", limit))

    def history(self, after: int, limit: int, name: str | None = None) -> Any:
        return self._do(
            name or f"history_{after}_{limit}", "history", (USER, "alpha", after, limit)
        )

    def ses_snapshot(self, ref: str, limit: int, name: str | None = None) -> Any:
        return self._do(
            name or f"ses_snapshot_{limit}", "session_snapshot", (USER, "alpha", ref, limit)
        )

    def ses_history(self, ref: str, after: int, limit: int, name: str | None = None) -> Any:
        return self._do(
            name or f"ses_history_{after}_{limit}",
            "session_history",
            (USER, "alpha", ref, after, limit),
        )

    def _do(self, name: str, method: str, args: tuple[Any, ...]) -> Any:
        while name in self.results:
            name += "#"  # a repeated step name stays addressable
        e0, p0 = len(self.events), len(self.prompt)
        call = getattr(self.reads, method + ("" if self.mode == "old" else "_with_media"))
        outcome: list[Any]
        out = None
        try:
            out = call(*args)
            if self.mode != "old":
                self.sidecars[name] = out.sidecar
                out = out.public
            response = server._result_response(out)
            body = response.body.decode().replace(str(self.tmp), "<T>")  # type: ignore[union-attr]
            plain = wire.dump_json(_plain({"reset": out} if isinstance(out, HistoryReset) else out))
            assert plain == response.body  # the hashed bytes are the actual wire serialization
            outcome = ["ok", *_digest(body)]
        except HmpError as exc:
            outcome = ["err", exc.code.value, exc.http]
        self.results[name] = out
        with self.store.transaction() as conn:
            baselines = [
                _short(tuple(row))
                for table in ("session_baselines", "other_session_baselines")
                for row in conn.execute(_BASELINE_QUERIES[table]).fetchall()
            ]
        self.steps.append([name, outcome, self.events[e0:], self.prompt[p0:], baselines])
        return out


# --------------------------------------------------------------------------------------------------
# Scenarios. Each takes a `Run`; none touches a sidecar, so the same code runs at the baseline.
# --------------------------------------------------------------------------------------------------


def scn_regular(r: Run) -> None:
    r.start()
    r.seed_rows("s1")
    r.snapshot(100)
    r.snapshot(4)
    r.history(0, 100)
    r.history(1, 3)
    r.history(9, 5)  # an empty page past the newest row
    r.db.seed_session("sb", source="desktop", title="Bot Chat", hidden=True)
    r.seed_rows("sb")
    ref = r.mint_ref("sb")
    r.ses_snapshot(ref, 100)
    r.ses_snapshot(ref, 3)
    r.ses_history(ref, 12, 4)  # rows after the 12th: ids 13..
    r.ses_history(ref, 0, 100, name="ses_from_start")


def scn_resets(r: Run) -> None:
    r.start()
    ids = r.seed_rows("s1")
    r.snapshot(100)  # baseline saved
    r.history(9999, 5)  # cursor_not_resolvable via the probe
    r.db.compact_in_place("s1", keep=2)
    r.history(ids[3], 5)  # the cursor row is inactive: history_rewritten via the probe
    r.history(0, 5)  # same session and tip, fewer active rows: history_rewritten
    r.db.children["s1"] = "s2"
    r.db.append("s2", "user", "later")
    r.history(0, 5)  # lineage_changed (tip moved)
    r.world.adapter._session_store.entries.clear()
    r.history(0, 5)  # session_replaced (route pruned), baseline dropped
    r.history(0, 5)  # no baseline: an empty page
    r.history(3, 5)  # no baseline and a cursor: cursor_not_resolvable
    # a browsed session
    r.db.seed_session("sb", source="desktop", title="Bot Chat", hidden=True)
    r.seed_rows("sb")
    ref = r.mint_ref("sb")
    r.ses_history(ref, 0, 100)
    r.ses_history(ref, 777, 5)
    r.db.compact_in_place("sb", keep=1)
    r.ses_history(ref, 20, 5)


def scn_no_conversation(r: Run) -> None:
    r.snapshot(10)
    r.history(0, 10)
    r.history(5, 10)
    r.start()  # a started conversation leaves a baseline...
    r.seed_rows("s1")
    r.snapshot(10)
    r.world.adapter._session_store.entries.clear()  # ...then the route is pruned
    r.snapshot(10, name="snapshot_pruned")
    r.history(0, 10, name="history_after_pruned")


def scn_faults(r: Run) -> None:
    r.start()
    r.seed_rows("s1")
    r.ses_snapshot("ses1_missing", 5)  # unknown ref: 404
    r.db.seed_session("sx")
    ref = r.mint_ref("sx", "ses1_gone")
    del r.db.sessions["sx"]  # minted but the Hermes session no longer exists
    r.ses_snapshot(ref, 5, name="ses_gone")
    r.db.fail = True
    r.snapshot(5, name="snapshot_db_fail")
    r.history(0, 5, name="history_db_fail")
    r.db.fail = False
    real = r.db.get_messages
    r.db.get_messages = lambda *a, **k: "not a list"  # type: ignore[method-assign]
    r.snapshot(5, name="snapshot_rows_not_list")
    r.history(0, 5, name="history_rows_not_list")
    r.db.get_messages = lambda *a, **k: ["not a mapping"]  # type: ignore[method-assign]
    r.snapshot(5, name="snapshot_row_not_mapping")
    r.db.get_messages = real  # type: ignore[method-assign]
    r.world.runner.approved.clear()  # the per-bot gate refuses before anything else
    r.snapshot(5, name="snapshot_unapproved")
    r.history(0, 5, name="history_unapproved")


def scn_race_unequal(r: Run) -> None:
    r.start()
    r.seed_rows("s1")
    r.race_tips(["sL", "s1"])  # the lineage read says `sL`, the rows' query says `s1`
    r.snapshot(100)
    r.race_tips(["sL", "s1"])
    r.history(0, 100)


def scn_race_long_lineage(r: Run) -> None:
    r.start()
    r.seed_rows("s1")
    r.race_tips(["L" * 300, "s1"])  # only the separately read lineage tip is unrepresentable
    r.snapshot(100)
    r.race_tips(["L" * 300, "s1"])
    r.history(0, 100)
    r.race_tips(["L" * 257, "s1"])
    r.snapshot(100, name="snapshot_lineage_257")
    r.race_tips(["L" * 256, "s1"])
    r.snapshot(100, name="snapshot_lineage_256")


def scn_session_256(r: Run) -> None:
    sid = "a" * 256
    r.start(sid)
    r.seed_rows(sid)
    r.snapshot(100)
    r.history(0, 100)


def scn_session_257(r: Run) -> None:
    sid = "a" * 257
    r.start(sid)
    r.seed_rows(sid)
    r.snapshot(100)
    r.history(0, 100)


def _tip_chain(r: Run, length: int) -> None:
    r.start()
    tip = "t" * length
    r.db.children["s1"] = tip
    r.seed_rows(tip)


def scn_tip_256(r: Run) -> None:
    _tip_chain(r, 256)
    r.snapshot(100)
    r.history(0, 100)


def scn_tip_300(r: Run) -> None:
    _tip_chain(r, 300)
    r.snapshot(100)
    r.history(0, 100)


def _many_rows(r: Run, count: int) -> None:
    r.start()
    r.db.append("s1", "user", "first")
    for i in range(count - 2):
        r.db.append("s1", "assistant", f"m{i}")
    r.tool("s1", r.image("gen_z.png"))


def scn_rows_1000(r: Run) -> None:
    _many_rows(r, 1000)
    r.snapshot(1000)
    r.history(0, 1000)


def scn_rows_1001(r: Run) -> None:
    _many_rows(r, 1001)
    r.snapshot(1001)
    r.history(0, 1001)


SCENARIOS: dict[str, Callable[[Run], None]] = {
    "regular": scn_regular,
    "resets": scn_resets,
    "no_conversation": scn_no_conversation,
    "faults": scn_faults,
    "race_unequal": scn_race_unequal,
    "race_long_lineage": scn_race_long_lineage,
    "session_256": scn_session_256,
    "session_257": scn_session_257,
    "tip_256": scn_tip_256,
    "tip_300": scn_tip_300,
    "rows_1000": scn_rows_1000,
    "rows_1001": scn_rows_1001,
}


def run_scenario(tmp: Path, name: str, mode: str = "old") -> Run:
    run = Run(tmp, mode=mode, approved=True)
    SCENARIOS[name](run)
    return run


# --------------------------------------------------------------------------------------------------
# The four routes, over actual aiohttp. The handlers are the unchanged production handlers; the
# media modes put a thin adapter between them and `Reads` that unwraps `.public` (what the later
# handler slice will do), so the bytes are those of the real route responses.
# --------------------------------------------------------------------------------------------------


class PublicOnly:
    """Handlers call the four old names; this serves them from the media twins' `.public`."""

    def __init__(self, reads: Reads) -> None:
        self._reads = reads

    def snapshot(self, *a: Any) -> Any:
        return self._reads.snapshot_with_media(*a).public

    def history(self, *a: Any) -> Any:
        return self._reads.history_with_media(*a).public

    def session_snapshot(self, *a: Any) -> Any:
        return self._reads.session_snapshot_with_media(*a).public

    def session_history(self, *a: Any) -> Any:
        return self._reads.session_history_with_media(*a).public


def run_routes(tmp: Path, mode: str = "old") -> list[list[Any]]:
    env = hmp_kit.Env(tmp / "hmp")
    world = World(tmp / "w")
    bridge_cls = NoOptIn if mode == "unsupported" else HermesReadBridge
    bridge = bridge_cls(world.adapter, StoreDirectory(env.store), hermes=world.api)
    reads = Reads(
        bridge,
        env.store,
        iid=env.iid,
        guarantees=env.ctx.guarantees,
        write_gate=env.ctx.write_gate,
        clock=env.clock,
        epoch="e" * 16,
    )
    env.ctx.bridge = bridge
    env.ctx.reads = reads if mode == "old" else PublicOnly(reads)
    from hmp_plugin.authorize import Authorize

    env.ctx.authorize = Authorize(bridge, env.store, clock=env.clock)
    out: list[list[Any]] = []

    async def scenario(client: Any) -> None:
        dev = await hmp_kit.pair(env, client)
        headers = env.headers(dev)
        user_id = env.store.get_device(dev.device_id)["user_id"]
        status, _ = await hmp_kit.post(client, "/bots/alpha/authorize", {}, headers=headers)
        assert status == 202
        world.approve(user_id, "alpha")
        chat = env.store.get_chat(user_id, "alpha", "default")["chat_id"]

        async def get(path: str) -> None:
            resp = await client.get(hmp_kit.url(path), headers=headers)
            body = (await resp.read()).decode().replace(str(tmp), "<T>")
            out.append([path, resp.status, *_digest(body)])

        await get("/bots/alpha/conversations/default")  # nothing started yet
        world.start_conversation("alpha", chat, "s1")
        db, home = world.dbs["alpha"], world.runner.homes["alpha"]

        def image(name: str, pad: int = 0) -> str:
            return json.dumps(
                {"pad": "x" * pad, "success": True, "image": f"{home}/cache/images/{name}"}
            )

        for session in ("s1", "sb"):
            ids = [
                db.append(session, "user", "hello"),
                db.append(
                    session,
                    "tool",
                    image("gen_a.png", 5000),
                    tool_name="image_generate",
                    tool_call_id=f"{session}_a",
                ),
                db.append(session, "assistant", f"MEDIA: {home}/cache/images/gen_a.png"),
                db.append(
                    session,
                    "tool",
                    json.dumps({"success": False}),
                    tool_name="image_generate",
                    tool_call_id=f"{session}_b",
                ),
                db.append(
                    session,
                    "tool",
                    image("gen_b.png"),
                    tool_name="image_generate",
                    tool_call_id=f"{session}_c",
                ),
            ]
            if session == "s1":
                await get("/bots/alpha/conversations/default?limit=100")
                await get("/bots/alpha/conversations/default?limit=2")
                await get(f"/bots/alpha/conversations/default/messages?after={ids[0]}&limit=3")
                await get(f"/bots/alpha/conversations/default/messages?after={ids[-1]}")
                db.compact_in_place("s1", keep=1)
                await get(f"/bots/alpha/conversations/default/messages?after={ids[-1]}")
            else:
                db.seed_session("sb", source="desktop", title="Bot Chat", hidden=True)
                ref = env.store.mint_or_get_session_ref(user_id, "alpha", "sb", "ses1_golden", T0)
                await get(f"/bots/alpha/sessions/{ref}/messages")
                await get(f"/bots/alpha/sessions/{ref}/messages?limit=2")
                await get(f"/bots/alpha/sessions/{ref}/messages?after={ids[1]}&limit=2")
                await get(f"/bots/alpha/sessions/{ref}/messages/from-start?limit=3")
                await get("/bots/alpha/sessions/ses1_unknown/messages")

    hmp_kit.run(env, scenario)
    return out


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=1, sort_keys=True)


def generate_golden(tmp: Path) -> dict[str, Any]:
    """Run once at the baseline commit; not called by any test."""
    golden: dict[str, Any] = {"scenarios": {}}
    for name in SCENARIOS:
        run = run_scenario(tmp / name, name)
        golden["scenarios"][name] = run.steps
    golden["routes"] = run_routes(tmp / "routes")
    return golden


# ==================================================================================================
# Tests. Everything below may use the sidecar; nothing above does.
# ==================================================================================================

MODES = ["old", "media", "unsupported"]
NAMES = sorted(SCENARIOS)
BIG = {"rows_1000", "rows_1001"}


def assert_golden(run: Run, name: str) -> None:
    expected = GOLDEN["scenarios"][name]
    assert [s[0] for s in run.steps] == [s[0] for s in expected]
    for got, want in zip(run.steps, expected, strict=True):
        assert got == want, got[0]


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("mode", MODES)
def test_every_mode_matches_the_baseline_golden(tmp_path: Path, mode: str, name: str) -> None:
    """Wire bytes, the native call/event log, the baseline rows and the observation discard sets
    of the OLD methods, of the twins' `.public` on an opted-in bridge, and of the twins on a bridge
    that has not opted in, all equal what commit 575a9bc produced."""
    assert_golden(run_scenario(tmp_path, name, mode), name)


@pytest.mark.parametrize("mode", MODES)
def test_route_bytes_match_the_baseline_golden(tmp_path: Path, mode: str) -> None:
    assert run_routes(tmp_path, mode) == GOLDEN["routes"]


def test_the_golden_is_sensitive_to_a_changed_text_byte(tmp_path: Path) -> None:
    run = Run(tmp_path)
    run.start()
    run.seed_rows("s1")
    run.db.rows[0]["content"] = "hellp"  # a one-byte change in the first row
    run.snapshot(100)
    assert run.steps[0][1] != GOLDEN["scenarios"]["regular"][0][1]


def test_provenance_of_the_golden_is_recorded_commit_and_sources() -> None:
    assert GOLDEN["provenance"]["commit"].startswith(BASELINE_COMMIT)
    repo = PACKAGE.parents[1]
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not available")
    for name, digest in GOLDEN["provenance"]["sources"].items():
        shown = subprocess.run(
            [git, "-C", str(repo), "show", f"{BASELINE_COMMIT}:server/hmp_plugin/{name}"],
            capture_output=True,
            check=False,
        )
        if shown.returncode != 0:
            pytest.skip("baseline commit is not available in this checkout")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, name


# --- sidecar contents ----------------------------------------------------------------------------


def summary(sidecar: Any) -> tuple[Any, ...]:
    return (
        sidecar.status.value,
        sidecar.origin.value,
        sidecar.session_id,
        sidecar.query_tip,
        sidecar.lineage_tip,
        [c.tool_row_id for c in sidecar.candidates],
    )


NULLS = (None, None, None)


def own(
    status: str, session: str | None, query: str | None, lineage: str | None, ids: list[int]
) -> tuple[Any, ...]:
    return (status, "own_conversation", session, query, lineage, ids)


def browsed(
    status: str, session: str | None, query: str | None, lineage: str | None, ids: list[int]
) -> tuple[Any, ...]:
    return (status, "browsed_session", session, query, lineage, ids)


def media_run(tmp_path: Path, name: str) -> Run:
    return run_scenario(tmp_path, name, "media")


def test_regular_reads_collect_exactly_the_returned_valid_image_tool_rows(tmp_path: Path) -> None:
    got = {k: summary(v) for k, v in media_run(tmp_path, "regular").sidecars.items()}
    assert got == {
        "snapshot_100": own("candidates", "s1", "s1", "s1", [8, 2]),
        # the tail window holds rows 6..9: row 2 is older, and the over-64 KiB row 6 is no candidate
        "snapshot_4": own("candidates", "s1", "s1", "s1", [8]),
        "history_0_100": own("candidates", "s1", "s1", "s1", [8, 2]),
        "history_1_3": own("candidates", "s1", "s1", "s1", [2]),  # rows 2, 3, 4 only
        "history_9_5": own("no_rows", *NULLS, []),
        "ses_snapshot_100": browsed("candidates", "sb", "sb", "sb", [17, 11]),
        "ses_snapshot_3": browsed("candidates", "sb", "sb", "sb", [17]),
        # rows 13..16 hold only an invalid, a foreign-prefix, an over-64 KiB and a normal tool row
        "ses_history_12_4": browsed("candidates", "sb", "sb", "sb", []),
        "ses_from_start": browsed("candidates", "sb", "sb", "sb", [17, 11]),
    }


def test_resets_and_missing_conversations_yield_no_rows_and_null_metadata(tmp_path: Path) -> None:
    run = media_run(tmp_path, "resets")
    got = {k: summary(v) for k, v in run.sidecars.items()}
    nothing = ("no_rows", "own_conversation", None, None, None, [])
    assert got == {
        "snapshot_100": own("candidates", "s1", "s1", "s1", [8, 2]),
        "history_9999_5": nothing,  # cursor_not_resolvable from the probe
        "history_4_5": nothing,  # history_rewritten from the probe
        # the page after an in-place compaction: its two re-inserted rows get fresh ids; row 10 is
        # the copied valid image row (a new id, so a new candidate)
        "history_0_5": own("candidates", "s1", "s1", "s1", [10]),
        "history_0_5#": nothing,  # lineage_changed, decided before any rows are queried
        "history_0_5##": nothing,  # session_replaced (route pruned)
        "history_0_5###": nothing,  # no conversation, no baseline: an empty page
        "history_3_5": nothing,  # no conversation, a cursor: cursor_not_resolvable
        "ses_history_0_100": browsed("candidates", "sb", "sb", "sb", [20, 14]),
        "ses_history_777_5": ("no_rows", "browsed_session", None, None, None, []),
        "ses_history_20_5": ("no_rows", "browsed_session", None, None, None, []),
    }
    assert [type(run.results[k]).__name__ for k in ("history_4_5", "history_0_5#")] == [
        "HistoryReset",
        "HistoryReset",
    ]
    none = {k: summary(v) for k, v in media_run(tmp_path / "n", "no_conversation").sidecars.items()}
    nothing = ("no_rows", "own_conversation", None, None, None, [])
    assert none == {
        "snapshot_10": nothing,
        "history_0_10": nothing,
        "history_5_10": nothing,
        "snapshot_10#": own("candidates", "s1", "s1", "s1", [8, 2]),
        "snapshot_pruned": nothing,
        "history_after_pruned": nothing,
    }


def test_query_tip_and_lineage_tip_race_stays_representable_but_inconsistent(
    tmp_path: Path,
) -> None:
    run = media_run(tmp_path, "race_unequal")
    for sidecar in run.sidecars.values():
        assert summary(sidecar) == own("candidates", "s1", "s1", "sL", [8, 2])
        assert sidecar.provenance_consistent is False
    consistent = media_run(tmp_path / "ok", "regular").sidecars["snapshot_100"]
    assert consistent.provenance_consistent is True


def test_separately_overlong_lineage_tip_downgrades_to_empty_unsupported(tmp_path: Path) -> None:
    run = media_run(tmp_path, "race_long_lineage")
    got = {k: summary(v) for k, v in run.sidecars.items()}
    for key in ("snapshot_100", "history_0_100", "snapshot_lineage_257"):
        assert got[key] == ("unsupported_bridge", "own_conversation", None, None, None, []), key
    # 256 is representable: the boundary is exact
    assert got["snapshot_lineage_256"] == own("candidates", "s1", "s1", "L" * 256, [8, 2])
    # the text read is untouched and the native queries were not repeated (golden compare above)
    assert_golden(run, "race_long_lineage")


def test_session_and_tip_length_boundaries(tmp_path: Path) -> None:
    a256 = "a" * 256
    ok = {k: summary(v) for k, v in media_run(tmp_path / "a", "session_256").sidecars.items()}
    assert ok["snapshot_100"] == own("candidates", a256, a256, a256, [8, 2])
    assert ok["history_0_100"] == own("candidates", a256, a256, a256, [8, 2])
    for sidecar in media_run(tmp_path / "b", "session_257").sidecars.values():
        assert summary(sidecar) == ("unsupported_bridge", "own_conversation", None, None, None, [])
    t256, t300 = "t" * 256, "t" * 300
    ok = {k: summary(v) for k, v in media_run(tmp_path / "c", "tip_256").sidecars.items()}
    assert ok["snapshot_100"] == own("candidates", "s1", t256, t256, [8, 2])
    for sidecar in media_run(tmp_path / "d", "tip_300").sidecars.values():
        assert summary(sidecar) == ("unsupported_bridge", "own_conversation", None, None, None, [])
    assert len(t300) == 300


def test_one_thousand_rows_are_collected_and_1001_downgrade_without_truncation(
    tmp_path: Path,
) -> None:
    ok = media_run(tmp_path / "a", "rows_1000")
    for key, sidecar in ok.sidecars.items():
        assert summary(sidecar) == own("candidates", "s1", "s1", "s1", [1000]), key
        assert len(ok.results[key].messages) == 1000
    over = media_run(tmp_path / "b", "rows_1001")
    for key, sidecar in over.sidecars.items():
        assert summary(sidecar) == ("unsupported_bridge", "own_conversation", None, None, None, [])
        assert len(over.results[key].messages) == 1001  # every row of the text read is kept


@pytest.mark.parametrize("name", [n for n in NAMES if n != "faults"])
def test_a_bridge_without_the_marker_is_unsupported_for_every_outcome(
    tmp_path: Path, name: str
) -> None:
    run = run_scenario(tmp_path, name, "unsupported")
    assert run.sidecars
    for key, sidecar in run.sidecars.items():
        assert summary(sidecar)[0] == "unsupported_bridge", key
        assert summary(sidecar)[2:] == (None, None, None, []), key


def test_faults_have_no_sidecar_and_the_same_error_mapping(tmp_path: Path) -> None:
    run = media_run(tmp_path, "faults")
    assert run.sidecars == {}
    assert [s[1] for s in run.steps] == [s[1] for s in GOLDEN["scenarios"]["faults"]]


# --- the four cores are shared --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "core", "args"),
    [
        ("snapshot", "_snapshot", (USER, "alpha", 5)),
        ("history", "_history_read", (USER, "alpha", 0, 5)),
        ("session_snapshot", "_session_snapshot", (USER, "alpha", "ref", 5)),
        ("session_history", "_session_history_read", (USER, "alpha", "ref", 0, 5)),
    ],
)
def test_old_and_twin_call_the_same_private_core_with_media_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, old: str, core: str, args: tuple[Any, ...]
) -> None:
    run = Run(tmp_path)
    seen: list[tuple[str, bool]] = []

    def spy(self: Any, *a: Any, media: bool, **k: Any) -> Any:
        seen.append((core, media))
        raise HmpError(ErrorCode.OTHER, 500)

    monkeypatch.setattr(Reads, core, spy)
    for method in (old, old + "_with_media"):
        with pytest.raises(HmpError):
            getattr(run.reads, method)(*args)
    assert seen == [(core, False), (core, True)]


# --- bridge shapes and the opt-in marker ----------------------------------------


class ShapeBridge(HermesReadBridge):
    """An opted-in bridge whose twins are scripted; `calls` records which entry points ran."""

    script: Any = None

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self.calls: list[str] = []

    def latest(self, ref: Any, limit: int) -> Any:
        self.calls.append("latest")
        return super().latest(ref, limit)

    def after(self, ref: Any, after_id: int, limit: int) -> Any:
        self.calls.append("after")
        return super().after(ref, after_id, limit)

    def latest_with_media(self, ref: Any, limit: int) -> Any:
        self.calls.append("latest_with_media")
        if self.script is None:
            return super().latest_with_media(ref, limit)
        return self.script(self, "latest", ref, limit)

    def after_with_media(self, ref: Any, after_id: int, limit: int) -> Any:
        self.calls.append("after_with_media")
        if self.script is None:
            return super().after_with_media(ref, after_id, limit)
        return self.script(self, "after", ref, after_id, limit)


def shaped(script: Callable[..., Any]) -> Callable[..., ShapeBridge]:
    class Shaped(ShapeBridge):
        pass

    Shaped.script = staticmethod(script)
    return Shaped


def parsed(bridge: Any, kind: str, ref: Any, *args: Any) -> list[Row]:
    """The old, unwrapped native read (never the twin), for building scripted shapes."""
    method = HermesReadBridge.latest if kind == "latest" else HermesReadBridge.after
    return method(bridge, ref, *args)


class ListSub(list):  # type: ignore[type-arg]
    pass


def _bad_shapes(bridge: Any, kind: str, ref: Any, *args: Any) -> dict[str, Any]:
    rows = parsed(bridge, kind, ref, *args)
    return {
        "none": None,
        "tuple": tuple(rows),
        "list_subclass": ListSub(rows),
        "non_row_item": [*rows, "x"],
        "dict": {"rows": rows},
        "text": "rows",
    }


@pytest.mark.parametrize(
    "shape", ["none", "tuple", "list_subclass", "non_row_item", "dict", "text"]
)
@pytest.mark.parametrize("kind", ["snapshot", "history", "ses_snapshot", "ses_history"])
def test_unapproved_bridge_shapes_are_internal_errors_with_no_second_query(
    tmp_path: Path, kind: str, shape: str
) -> None:
    run = Run(
        tmp_path,
        mode="media",
        bridge_factory=shaped(lambda b, k, ref, *a: _bad_shapes(b, k, ref, *a)[shape]),
    )
    run.start()
    run.seed_rows("s1")
    run.db.seed_session("sb")
    run.seed_rows("sb")
    ref = run.mint_ref("sb")
    run.events.clear()
    {
        "snapshot": lambda: run.snapshot(5),
        "history": lambda: run.history(0, 5),
        "ses_snapshot": lambda: run.ses_snapshot(ref, 5),
        "ses_history": lambda: run.ses_history(ref, 0, 5),
    }[kind]()
    assert run.steps[-1][1] == ["err", "other", 500]
    # the scripted shape performed ONE old-style read; no old method or twin was retried
    assert run.bridge.calls == ["latest_with_media" if "snapshot" in kind else "after_with_media"]
    assert sum(e.startswith("alpha.get_messages") for e in run.events) == 1


def test_reset_is_not_an_approved_shape_for_latest(tmp_path: Path) -> None:
    run = Run(
        tmp_path,
        mode="media",
        bridge_factory=shaped(lambda *a: ResetReason.HISTORY_REWRITTEN),
    )
    run.start()
    run.seed_rows("s1")
    run.snapshot(5)
    assert run.steps[-1][1] == ["err", "other", 500]


def test_exact_list_fallback_is_unchanged_text_with_null_unsupported_metadata(
    tmp_path: Path,
) -> None:
    def fallback(bridge: Any, kind: str, ref: Any, *args: Any) -> Any:
        return parsed(bridge, kind, ref, *args)

    ran = Run(tmp_path, mode="media", bridge_factory=shaped(fallback))
    ran.start()
    ran.seed_rows("s1")
    ran.snapshot(100)
    ran.history(0, 100)
    golden = GOLDEN["scenarios"]["regular"]
    assert ran.steps[0][1] == golden[0][1] and ran.steps[1][1] == golden[2][1]
    for sidecar in ran.sidecars.values():
        assert summary(sidecar) == ("unsupported_bridge", "own_conversation", None, None, None, [])
    # one native page read per request, in the golden order: the fallback is never re-queried
    assert [e for e in ran.steps[0][2] if "get_messages" in e] == [
        "alpha.get_messages(s1,latest=True,limit=100)"
    ]
    assert ran.bridge.calls == ["latest_with_media", "after_with_media"]


@pytest.mark.parametrize("reason", [ResetReason.HISTORY_REWRITTEN, ResetReason.GAP])
def test_after_twin_reset_is_unchanged_and_mapped_as_the_old_path(
    tmp_path: Path, reason: ResetReason
) -> None:
    run = Run(tmp_path, mode="media", bridge_factory=shaped(lambda *a: reason))
    run.start()
    run.seed_rows("s1")
    out = run.history(0, 5)
    want = reason if reason is ResetReason.HISTORY_REWRITTEN else ResetReason.CURSOR_NOT_RESOLVABLE
    assert out == HistoryReset(reason=want)
    assert summary(run.sidecars["history_0_5"]) == (
        "no_rows",
        "own_conversation",
        None,
        None,
        None,
        [],
    )


def _crafted(extra_ids: list[int]) -> Callable[..., Any]:
    def script(bridge: Any, kind: str, ref: Any, *args: Any) -> Any:
        real = (
            HermesReadBridge.latest_with_media(bridge, ref, *args)
            if kind == "latest"
            else HermesReadBridge.after_with_media(bridge, ref, *args)
        )
        carrier = sc()
        made = [carrier.MediaCandidate(i, bytes(32)) for i in extra_ids]
        return carrier.BridgeMediaRows(real.rows, real.query, tuple(made))

    return script


def test_candidates_must_be_tool_rows_returned_in_the_public_page(tmp_path: Path) -> None:
    # 3 is a returned assistant row, 999 does not exist, 2 and 8 are returned tool rows
    run = Run(tmp_path, mode="media", bridge_factory=shaped(_crafted([8, 3, 999, 2])))
    run.start()
    run.seed_rows("s1")
    run.snapshot(100)
    assert summary(run.sidecars["snapshot_100"])[5] == [8, 2]


def test_history_head_and_unreturned_rows_authorize_nothing(tmp_path: Path) -> None:
    run = Run(tmp_path, mode="media", bridge_factory=shaped(_crafted([8, 2])))
    run.start()
    run.seed_rows("s1")
    page = run.history(1, 2)  # rows 2 and 3; the lineage head is 9 and row 8 is a tool row
    assert [m.id for m in page.messages] == [2, 3] and page.head_message_id == 9
    assert summary(run.sidecars["history_1_2"])[5] == [2]
    tail = Run(tmp_path / "t", mode="media", bridge_factory=shaped(_crafted([2, 8])))
    tail.start()
    tail.seed_rows("s1")
    tail.snapshot(2)  # rows 8 and 9: the older tool row 2 is outside the tail window
    assert summary(tail.sidecars["snapshot_2"])[5] == [8]


def test_origin_label_is_only_an_observation(tmp_path: Path) -> None:
    run = media_run(tmp_path, "regular")
    assert {run.sidecars[k].origin.value for k in run.sidecars if k.startswith("ses_")} == {
        "browsed_session"
    }
    assert {run.sidecars[k].origin.value for k in run.sidecars if not k.startswith("ses_")} == {
        "own_conversation"
    }


class TruthyMarker(ShapeBridge):
    LOCAL_MEDIA_SIDECAR = 1  # truthy, but not the explicit `True`

    def latest_with_media(self, ref: Any, limit: int) -> Any:
        raise AssertionError("must not be selected")

    after_with_media = latest_with_media  # type: ignore[assignment]


class StringMarker(TruthyMarker):
    LOCAL_MEDIA_SIDECAR = "yes"  # type: ignore[assignment]


@pytest.mark.parametrize("factory", [TruthyMarker, StringMarker, NoOptIn])
def test_only_an_explicit_true_class_marker_selects_the_twins(tmp_path: Path, factory: Any) -> None:
    run = Run(tmp_path, mode="media", bridge_factory=factory)
    run.start()
    run.seed_rows("s1")
    run.snapshot(100)
    run.history(0, 100)
    assert run.steps[0][1] == GOLDEN["scenarios"]["regular"][0][1]
    for sidecar in run.sidecars.values():
        assert summary(sidecar) == ("unsupported_bridge", "own_conversation", None, None, None, [])


class DynamicBridge:
    """Answers every name, including `LOCAL_MEDIA_SIDECAR` and `latest_with_media`, dynamically.
    An instance or `hasattr` probe would select the twins; the class marker must not."""

    def __init__(self, *a: Any, **k: Any) -> None:
        self.inner = HermesReadBridge(*a, **k)
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        if name == "LOCAL_MEDIA_SIDECAR":
            return True
        target = getattr(self.inner, name)

        def call(*a: Any, **k: Any) -> Any:
            self.calls.append(name)
            if name.endswith("_with_media"):
                raise AssertionError("dynamic twin selected")
            return target(*a, **k)

        return call


def test_dynamic_instance_level_optin_is_never_probed(tmp_path: Path) -> None:
    run = Run(tmp_path, mode="media", bridge_factory=DynamicBridge)
    assert run.bridge.LOCAL_MEDIA_SIDECAR is True and hasattr(run.bridge, "latest_with_media")
    run.start()
    run.seed_rows("s1")
    run.snapshot(100)
    run.history(1, 3)
    assert run.steps[0][1] == GOLDEN["scenarios"]["regular"][0][1]
    assert run.steps[1][1] == GOLDEN["scenarios"]["regular"][3][1]
    assert not [c for c in run.bridge.calls if c.endswith("_with_media")]
    assert {"latest", "after"} <= set(run.bridge.calls)
    for sidecar in run.sidecars.values():
        assert sidecar.status.value == "unsupported_bridge" and sidecar.session_id is None


class OptInSpy(hmp_kit.SpyBridge):
    """`SpyBridge` answers every attribute with a raising callable, `LOCAL_MEDIA_SIDECAR` too."""

    def authz_state(self, user_id: str, profile: str) -> AuthzState:
        self.calls.append("authz_state")
        return AuthzState.AUTHORIZED

    def conversation_ref(self, user_id: str, profile: str) -> ConversationRef:
        self.calls.append("conversation_ref")
        return ConversationRef(user_id, profile, "s1")

    def lineage(self, ref: ConversationRef) -> Any:
        from hmp_plugin.contract import LineageInfo

        self.calls.append("lineage")
        return LineageInfo("s1", "s1", None, 0, ("s1",))

    def latest(self, ref: ConversationRef, limit: int) -> list[Row]:
        self.calls.append("latest")
        return []


def test_spy_bridge_dynamic_optin_stays_unsupported_with_old_calls_only() -> None:
    spy = OptInSpy()
    assert callable(spy.LOCAL_MEDIA_SIDECAR)  # the dynamic answer: truthy, not `True`
    store = _NullStore()
    reads = Reads(
        spy,  # type: ignore[arg-type]
        store,
        iid="i" * 52,
        guarantees=Guarantees,
        write_gate=lambda: WriteGate(WriteGateState.CLOSED, None),
        clock=lambda: T0,
        epoch="e" * 16,
    )
    result = reads.snapshot_with_media(USER, "alpha", 5)
    assert spy.calls == ["authz_state", "conversation_ref", "lineage", "latest"]
    assert result.sidecar.status.value == "unsupported_bridge"
    assert result.public.messages == ()


class _NullStore:
    def get_session_baseline(self, *a: Any) -> None:
        return None

    def set_session_baseline(self, *a: Any) -> None:
        return None


# --- carrier faults are not masked ---------------------------------------------------------------


def test_only_the_narrow_lineage_metadata_refusal_is_a_downgrade(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    carrier = sc()
    original = carrier.MediaSidecar.__init__

    def picky(self: Any, **kw: Any) -> None:
        # only the candidate-bearing construction fails; the empty fallback would succeed, so a
        # broad `except` around the first call would silently turn this fault into a downgrade
        if kw["status"] is carrier.SidecarStatus.CANDIDATES:
            raise RuntimeError("invariant")
        original(self, **kw)

    monkeypatch.setattr(carrier.MediaSidecar, "__init__", picky)
    run = Run(tmp_path, mode="media")
    run.start()
    run.seed_rows("s1")
    with pytest.raises(RuntimeError, match="invariant"):
        run.snapshot(5)

    def refuse(self: Any, **kw: Any) -> None:
        if kw["status"] is carrier.SidecarStatus.CANDIDATES:
            raise carrier.MediaCarrierRefusal
        original(self, **kw)

    monkeypatch.setattr(carrier.MediaSidecar, "__init__", refuse)
    run.snapshot(5)  # the refusal alone is the documented downgrade
    assert summary(run.sidecars["snapshot_5"]) == (
        "unsupported_bridge",
        "own_conversation",
        None,
        None,
        None,
        [],
    )

    def refuse_always(self: Any, **kw: Any) -> None:
        raise carrier.MediaCarrierRefusal

    monkeypatch.setattr(carrier.MediaSidecar, "__init__", refuse_always)
    with pytest.raises(carrier.MediaCarrierRefusal):  # a failing fallback is not masked either
        run.snapshot(5, name="again")


def test_native_faults_in_the_twin_map_exactly_like_the_old_path(tmp_path: Path) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise OSError("database is locked")

    run = Run(tmp_path, mode="media", bridge_factory=shaped(boom))
    run.start()
    run.seed_rows("s1")
    run.snapshot(5)
    run.history(0, 5)
    assert [s[1] for s in run.steps] == [["err", "other", 500]] * 2


# --- inertness -----------------------------------------------------------------------------------


def _fresh(mode: str) -> subprocess.CompletedProcess[str]:
    tests = Path(__file__).resolve().parents[1]
    code = (
        "import sys, tempfile, pathlib\n"
        f"sys.path[:0] = [{str(tests.parent)!r}, {str(tests)!r}]\n"
        "from unit.test_reads_media import Run, NoOptIn\n"
        "def loaded(): return sorted(m for m in sys.modules if 'local_media' in m)\n"
        "assert not loaded(), loaded()\n"
        "tmp = pathlib.Path(tempfile.mkdtemp())\n"
        f"run = Run(tmp, mode={('old' if mode == 'old' else 'media')!r}, "
        f"bridge_factory={'NoOptIn' if mode == 'unsupported' else 'None'})\n"
        "run.start(); run.seed_rows('s1')\n"
        "run.snapshot(10); run.history(0, 10)\n"
        "print(','.join(m.rsplit('.', 1)[-1] for m in loaded()))\n"
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("old", ""),
        ("unsupported", "local_media_sidecar"),
        (
            "media",
            "local_media_active_scan,local_media_candidate,local_media_file_safety,"
            "local_media_result,local_media_sidecar",
        ),
    ],
)
def test_modules_load_only_when_a_twin_actually_runs(mode: str, expected: str) -> None:
    done = _fresh(mode)
    assert done.returncode == 0, done.stderr[-600:]
    lines = [line for line in done.stdout.splitlines() if "local_media" in line or not line]
    assert (lines[-1] if lines else "") == expected, done.stdout[-400:]


def test_server_has_no_reference_to_the_twins_or_media_modules() -> None:
    source = (PACKAGE / "server.py").read_text(encoding="utf-8")
    assert "_with_media" not in source and "local_media" not in source
    ast.parse(source)


def test_contract_read_bridge_and_wire_types_are_unchanged() -> None:
    from hmp_plugin.contract import ReadBridge, WireMessage

    assert not {n for n in vars(ReadBridge) if "media" in n.lower()}
    assert "media" not in set(WireMessage.__dataclass_fields__)
    assert re.search(r"LOCAL_MEDIA", (PACKAGE / "contract.py").read_text(encoding="utf-8")) is None


# Captured once at the baseline commit (see the module docstring); never regenerated from this tree.
GOLDEN: dict[str, Any] = {
    "provenance": {
        "commit": "575a9bc1cba5d5ec4c41741c5a5eb723f505f65c",
        "sources": {
            "bridge.py": "e6d11873fd7d2bcc8e49ea452b77206db350d0f448594bdaa4e776f435e1b15c",
            "reads.py": "620e0e9d3d8a39464ab5c5cc70591097de9c2252781c28eaa869d6d702358e3f",
            "request_ctx.py": "9bead317d63ab016a665333bded7fc3dca7c54354eb1b77ea57b943bd13166dd",
            "server.py": "688cd7a0e8bf574f27ad4cb8e18fb622a4ab34dd2122292ad9071b2db4b98d09",
            "wire.py": "dd78bb759834fad624291d1326929c97e7ac1dfa0333cd78fca8010c8570ce7d",
        },
    },
    "routes": [
        [
            "/bots/alpha/conversations/default",
            200,
            "49b5af0b3afc6e5a5e6000eb083e0b0f8e1a295ab2dd247dbaca5db9e7fe3f49",
            232,
        ],
        [
            "/bots/alpha/conversations/default?limit=100",
            200,
            "081c445f7fc24d82b12de3b8cd4a6292ce73ea30ba75f65d288b1e957304913a",
            4989,
        ],
        [
            "/bots/alpha/conversations/default?limit=2",
            200,
            "8d8467f607a4c33d50f76df9953e1f93a4b84b59a92f322b9c0a929c3e76fa4a",
            609,
        ],
        [
            "/bots/alpha/conversations/default/messages?after=1&limit=3",
            200,
            "9897d278c5606837117ee1a57d251079b8e0d637d7a13cc2a22dfe675adc144d",
            4480,
        ],
        [
            "/bots/alpha/conversations/default/messages?after=5",
            200,
            "8bfa8fdc4ce938a660b19fc51bc88eed1e9491024ea5f35930bfc1d4142a2d06",
            35,
        ],
        [
            "/bots/alpha/conversations/default/messages?after=5",
            200,
            "6d5b6841374bae1fe3837710054c641dd3eb44a9833ea6eeaedc29982c154cd6",
            65,
        ],
        [
            "/bots/alpha/sessions/ses1_golden/messages",
            200,
            "885b6423666cb9fdd67d2e98ddeb2c30107df174710f1ad4dc188fcaeacb1f83",
            4844,
        ],
        [
            "/bots/alpha/sessions/ses1_golden/messages?limit=2",
            200,
            "2f8a32a4ea484f88b99fba3429b03fc3f0d9a6d479831e841b416418679c2616",
            463,
        ],
        [
            "/bots/alpha/sessions/ses1_golden/messages?after=8&limit=2",
            200,
            "379fa86b7249e20c7809cb350173b4813fce38e515a43f45fcec0b811e9d34af",
            327,
        ],
        [
            "/bots/alpha/sessions/ses1_golden/messages/from-start?limit=3",
            200,
            "7b370b392f7469ac3545d2812c6e8c87c79c1ce61194d4c0cee612f7b39eb267",
            4415,
        ],
        [
            "/bots/alpha/sessions/ses1_unknown/messages",
            404,
            "dea78f843e46c45482b84c9d9db6d16b10a294376e65bcf67a43484f071428c1",
            52,
        ],
    ],
    "scenarios": {
        "faults": [
            [
                "ses_snapshot_5",
                ["err", "not_found", 404],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [],
                [],
            ],
            [
                "ses_gone",
                ["err", "not_found", 404],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sx)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "snapshot_db_fail",
                ["err", "other", 500],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "history_db_fail",
                ["err", "other", 500],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "snapshot_rows_not_list",
                ["err", "other", 500],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "history_rows_not_list",
                ["err", "other", 500],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "snapshot_row_not_mapping",
                ["err", "other", 500],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "release",
                ],
                [],
                [],
            ],
            [
                "snapshot_unapproved",
                ["err", "forbidden", 403],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [],
                [],
            ],
            [
                "history_unapproved",
                ["err", "forbidden", 403],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [],
                [],
            ],
        ],
        "no_conversation": [
            [
                "snapshot_10",
                ["ok", "49b5af0b3afc6e5a5e6000eb083e0b0f8e1a295ab2dd247dbaca5db9e7fe3f49", 232],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [
                    "purge 1900000000",
                    "discard alpha []",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                [],
            ],
            [
                "history_0_10",
                ["ok", "2809a66a431464565d93919110585cc1d2bff76d326aaa47f5f8041c677ad51e", 38],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [],
                [],
            ],
            [
                "history_5_10",
                ["ok", "3734f3678f75aaa5a8e34afd0fa7d47afba992a5c39855e21167fad16b6ae668", 69],
                ["authz", "routed_home(alpha)", "authz", "authz"],
                [],
                [],
            ],
            [
                "snapshot_10#",
                ["ok", "70e0a92261715420b7edaa8035f88a4bc026a351c2f2a44695bc2e7e49297b60", 9624],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=10)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', "
                    "'assistant:done', 'tool:<4000:7ccedf2d>', "
                    "'tool:<78:410a9e1c>', 'tool:<81:5e3cd78b>', 'tool:ok', "
                    '\'tool:{"success": false, "error": "nope"}\', '
                    "'user:hello']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<77:94db8ddf>"],
            ],
            [
                "snapshot_pruned",
                ["ok", "49b5af0b3afc6e5a5e6000eb083e0b0f8e1a295ab2dd247dbaca5db9e7fe3f49", 232],
                ["authz", "routed_home(alpha)", "authz", "authz", "lookup_session"],
                [
                    "purge 1900000000",
                    "discard alpha []",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                [],
            ],
            [
                "history_after_pruned",
                ["ok", "2809a66a431464565d93919110585cc1d2bff76d326aaa47f5f8041c677ad51e", 38],
                ["authz", "routed_home(alpha)", "authz", "authz", "lookup_session"],
                [],
                [],
            ],
        ],
        "race_long_lineage": [
            [
                "snapshot_100",
                ["ok", "892fbce035434663f86b1af6aba967b564ff70ed47e3d915c56ba98156a3ab68", 9922],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip <300:10bf7a12>",
                    "alpha.get_active_message_ids(<300:10bf7a12>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', "
                    "'assistant:done', 'tool:<4000:7ccedf2d>', "
                    "'tool:<78:410a9e1c>', 'tool:<81:5e3cd78b>', 'tool:ok', "
                    '\'tool:{"success": false, "error": "nope"}\', '
                    "'user:hello']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<375:d4ac6684>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip <300:10bf7a12>",
                    "alpha.get_active_message_ids(<300:10bf7a12>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<375:d4ac6684>"],
            ],
            [
                "snapshot_lineage_257",
                ["ok", "a4349dd5aedd194a22f48544ead99ab5e873ca4a2d5ffdc9a7bd6d1cd0422aee", 9879],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip <257:2ca61ea8>",
                    "alpha.get_active_message_ids(<257:2ca61ea8>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', "
                    "'assistant:done', 'tool:<4000:7ccedf2d>', "
                    "'tool:<78:410a9e1c>', 'tool:<81:5e3cd78b>', 'tool:ok', "
                    '\'tool:{"success": false, "error": "nope"}\', '
                    "'user:hello']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<332:50a8e7bc>"],
            ],
            [
                "snapshot_lineage_256",
                ["ok", "9023e10850af80f4764c70fcba68e3091279dcabcdb3fdfc7fc89cb23f1179c0", 9878],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip <256:2162d3a3>",
                    "alpha.get_active_message_ids(<256:2162d3a3>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', "
                    "'assistant:done', 'tool:<4000:7ccedf2d>', "
                    "'tool:<78:410a9e1c>', 'tool:<81:5e3cd78b>', 'tool:ok', "
                    '\'tool:{"success": false, "error": "nope"}\', '
                    "'user:hello']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<331:28d6d5a1>"],
            ],
        ],
        "race_unequal": [
            [
                "snapshot_100",
                ["ok", "0093c1875397ea10e1443c1010cf75a874ca3313c1bdcbf6c26f2b2d07a0f523", 9624],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip sL",
                    "alpha.get_active_message_ids(sL)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": "
                    'false, "error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<77:edbfe502>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "  -> tip sL",
                    "alpha.get_active_message_ids(sL)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "  -> tip s1",
                    "alpha.get_messages(s1,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<77:edbfe502>"],
            ],
        ],
        "regular": [
            [
                "snapshot_100",
                ["ok", "70e0a92261715420b7edaa8035f88a4bc026a351c2f2a44695bc2e7e49297b60", 9624],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": false, "
                    '"error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<77:94db8ddf>"],
            ],
            [
                "snapshot_4",
                ["ok", "40aea829da1beb255d618301f2922e03c22aa48f7c0ca717ced158c4376380a6", 4839],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=4)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:done', 'tool:<4000:7ccedf2d>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<77:94db8ddf>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>"],
            ],
            [
                "history_1_3",
                ["ok", "6e87b7eaac59d9c56ca594a8a07028a6efc5fd95cebccd60f65744cb1bd391f4", 4505],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=0,include_inactive=True,limit=1)",
                    "alpha.get_messages(s1,after_id=1,limit=3)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>"],
            ],
            [
                "history_9_5",
                ["ok", "a1b6914c739134c1f9bd3fb2398ad36fc98df65b48485ca85cc7896a27bfe4c2", 35],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=8,include_inactive=True,limit=1)",
                    "alpha.get_messages(s1,after_id=9,limit=5)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>"],
            ],
            [
                "ses_snapshot_100",
                ["ok", "15cc5ba1adb3d80fe1513908f8ac2a616c3383565de1bcdf5233e9894bbbda97", 9492],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,latest=True,limit=100)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>", "<77:f60846a1>"],
            ],
            [
                "ses_snapshot_3",
                ["ok", "3443feeb8658319af94fddb4e540970986ac5c7f2929e6196dcbc984024e03d5", 539],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,latest=True,limit=3)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>", "<77:f60846a1>"],
            ],
            [
                "ses_history_12_4",
                ["ok", "77486bc6acc5a18028d15ae8687793b67945ca41f9c7d939bb30ea5f843b2d5e", 4736],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,after_id=11,include_inactive=True,limit=1)",
                    "alpha.get_messages(sb,after_id=12,limit=4)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>", "<77:f60846a1>"],
            ],
            [
                "ses_from_start",
                ["ok", "7f2d2687f8110b91266a31f13a0be2c4fa625b29073d0e98d45a4d334ea7f1a7", 9446],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>", "<77:f60846a1>"],
            ],
        ],
        "resets": [
            [
                "snapshot_100",
                ["ok", "70e0a92261715420b7edaa8035f88a4bc026a351c2f2a44695bc2e7e49297b60", 9624],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": false, "
                    '"error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<77:94db8ddf>"],
            ],
            [
                "history_9999_5",
                ["ok", "3734f3678f75aaa5a8e34afd0fa7d47afba992a5c39855e21167fad16b6ae668", 69],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=9998,include_inactive=True,limit=1)",
                    "release",
                ],
                [],
                ["<77:94db8ddf>"],
            ],
            [
                "history_4_5",
                ["ok", "6d5b6841374bae1fe3837710054c641dd3eb44a9833ea6eeaedc29982c154cd6", 65],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                ],
                [],
                ["<77:63d9db84>"],
            ],
            [
                "history_0_5",
                ["ok", "ad232cb12d62c79a9643401102c2d1a104d3890294b022b32d2ccd37cfaf878f", 358],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=0,limit=5)",
                    "release",
                ],
                [],
                ["<77:63d9db84>"],
            ],
            [
                "history_0_5#",
                ["ok", "7da4249ea71db4ee67d35c7850f16b5e0879daadd560d64abaa1d89b30dcfa74", 63],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s2)",
                    "release",
                ],
                [],
                ["<77:4f212bed>"],
            ],
            [
                "history_0_5##",
                ["ok", "329fe53faee399dd74a53858b5bc69e293a5598c6f251629e3acdc7019fbfaab", 64],
                ["authz", "routed_home(alpha)", "authz", "authz", "lookup_session"],
                [],
                [],
            ],
            [
                "history_0_5###",
                ["ok", "2809a66a431464565d93919110585cc1d2bff76d326aaa47f5f8041c677ad51e", 38],
                ["authz", "routed_home(alpha)", "authz", "authz", "lookup_session"],
                [],
                [],
            ],
            [
                "history_3_5",
                ["ok", "3734f3678f75aaa5a8e34afd0fa7d47afba992a5c39855e21167fad16b6ae668", 69],
                ["authz", "routed_home(alpha)", "authz", "authz", "lookup_session"],
                [],
                [],
            ],
            [
                "ses_history_0_100",
                ["ok", "ca468110fd29e77079818abec3c92b25ff545855978da8b262e42495161fcc12", 9446],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<77:f60846a1>"],
            ],
            [
                "ses_history_777_5",
                ["ok", "3734f3678f75aaa5a8e34afd0fa7d47afba992a5c39855e21167fad16b6ae668", 69],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_messages(sb,after_id=776,include_inactive=True,limit=1)",
                    "release",
                ],
                [],
                ["<77:f60846a1>"],
            ],
            [
                "ses_history_20_5",
                ["ok", "6d5b6841374bae1fe3837710054c641dd3eb44a9833ea6eeaedc29982c154cd6", 65],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_session(sb)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.resolve_resume_session_id(sb)",
                    "alpha.get_compression_chain(sb)",
                    "alpha.get_active_message_ids(sb)",
                    "release",
                ],
                [],
                ["<77:310d442d>"],
            ],
        ],
        "rows_1000": [
            [
                "snapshot_1000",
                ["ok", "abdc114cd3d1da6b9bcc2f7fab45528312176027058c508c61e364a5879ac28a", 95148],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=1000)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:m0', 'assistant:m1', "
                    "'assistant:m10', 'assistant:m100', 'assistant:m101', "
                    "'assistant:m102', 'assistant:m103', 'assistant:m104', "
                    "'assistant:m105', 'assistant:m106', 'assistant:m107', "
                    "'assistant:m108', 'assistant:m109', 'assistant:m11', "
                    "'assistant:m110', 'assistant:m111', 'assistant:m112', "
                    "'assistant:m113', 'assistant:m114', 'assistant:m115', "
                    "'assistant:m116', 'assistant:m117', 'assistant:m118', "
                    "'assistant:m119', 'assistant:m12', 'assistant:m120', "
                    "'assistant:m121', 'assistant:m122', 'assistant:m123', "
                    "'assistant:m124', 'assistant:m125', 'assistant:m126', "
                    "'assistant:m127', 'assistant:m128', 'assistant:m129', "
                    "'assistant:m13', 'assistant:m130', 'assistant:m131', "
                    "'assistant:m132', 'assistant:m133', 'assistant:m134', "
                    "'assistant:m135', 'assistant:m136', 'assistant:m137', "
                    "'assistant:m138', 'assistant:m139', 'assistant:m14', "
                    "'assistant:m140', 'assistant:m141', 'assistant:m142', "
                    "'assistant:m143', 'assistant:m144', 'assistant:m145', "
                    "'assistant:m146', 'assistant:m147', 'assistant:m148', "
                    "'assistant:m149', 'assistant:m15', 'assistant:m150', "
                    "'assistant:m151', 'assistant:m152', 'assistant:m153', "
                    "'assistant:m154', 'assistant:m155', 'assistant:m156', "
                    "'assistant:m157', 'assistant:m158', 'assistant:m159', "
                    "'assistant:m16', 'assistant:m160', 'assistant:m161', "
                    "'assistant:m162', 'assistant:m163', 'assistant:m164', "
                    "'assistant:m165', 'assistant:m166', 'assistant:m167', "
                    "'assistant:m168', 'assistant:m169', 'assistant:m17', "
                    "'assistant:m170', 'assistant:m171', 'assistant:m172', "
                    "'assistant:m173', 'assistant:m174', 'assistant:m175', "
                    "'assistant:m176', 'assistant:m177', 'assistant:m178', "
                    "'assistant:m179', 'assistant:m18', 'assistant:m180', "
                    "'assistant:m181', 'assistant:m182', 'assistant:m183', "
                    "'assistant:m184', 'assistant:m185', 'assistant:m186', "
                    "'assistant:m187', 'assistant:m188', 'assistant:m189', "
                    "'assistant:m19', 'assistant:m190', 'assistant:m191', "
                    "'assistant:m192', 'assistant:m193', 'assistant:m194', "
                    "'assistant:m195', 'assistant:m196', 'assistant:m197', "
                    "'assistant:m198', 'assistant:m199', 'assistant:m2', "
                    "'assistant:m20', 'assistant:m200', 'assistant:m201', "
                    "'assistant:m202', 'assistant:m203', 'assistant:m204', "
                    "'assistant:m205', 'assistant:m206', 'assistant:m207', "
                    "'assistant:m208', 'assistant:m209', 'assistant:m21', "
                    "'assistant:m210', 'assistant:m211', 'assistant:m212', "
                    "'assistant:m213', 'assistant:m214', 'assistant:m215', "
                    "'assistant:m216', 'assistant:m217', 'assistant:m218', "
                    "'assistant:m219', 'assistant:m22', 'assistant:m220', "
                    "'assistant:m221', 'assistant:m222', 'assistant:m223', "
                    "'assistant:m224', 'assistant:m225', 'assistant:m226', "
                    "'assistant:m227', 'assistant:m228', 'assistant:m229', "
                    "'assistant:m23', 'assistant:m230', 'assistant:m231', "
                    "'assistant:m232', 'assistant:m233', 'assistant:m234', "
                    "'assistant:m235', 'assistant:m236', 'assistant:m237', "
                    "'assistant:m238', 'assistant:m239', 'assistant:m24', "
                    "'assistant:m240', 'assistant:m241', 'assistant:m242', "
                    "'assistant:m243', 'assistant:m244', 'assistant:m245', "
                    "'assistant:m246', 'assistant:m247', 'assistant:m248', "
                    "'assistant:m249', 'assistant:m25', 'assistant:m250', "
                    "'assistant:m251', 'assistant:m252', 'assistant:m253', "
                    "'assistant:m254', 'assistant:m255', 'assistant:m256', "
                    "'assistant:m257', 'assistant:m258', 'assistant:m259', "
                    "'assistant:m26', 'assistant:m260', 'assistant:m261', "
                    "'assistant:m262', 'assistant:m263', 'assistant:m264', "
                    "'assistant:m265', 'assistant:m266', 'assistant:m267', "
                    "'assistant:m268', 'assistant:m269', 'assistant:m27', "
                    "'assistant:m270', 'assistant:m271', 'assistant:m272', "
                    "'assistant:m273', 'assistant:m274', 'assistant:m275', "
                    "'assistant:m276', 'assistant:m277', 'assistant:m278', "
                    "'assistant:m279', 'assistant:m28', 'assistant:m280', "
                    "'assistant:m281', 'assistant:m282', 'assistant:m283', "
                    "'assistant:m284', 'assistant:m285', 'assistant:m286', "
                    "'assistant:m287', 'assistant:m288', 'assistant:m289', "
                    "'assistant:m29', 'assistant:m290', 'assistant:m291', "
                    "'assistant:m292', 'assistant:m293', 'assistant:m294', "
                    "'assistant:m295', 'assistant:m296', 'assistant:m297', "
                    "'assistant:m298', 'assistant:m299', 'assistant:m3', "
                    "'assistant:m30', 'assistant:m300', 'assistant:m301', "
                    "'assistant:m302', 'assistant:m303', 'assistant:m304', "
                    "'assistant:m305', 'assistant:m306', 'assistant:m307', "
                    "'assistant:m308', 'assistant:m309', 'assistant:m31', "
                    "'assistant:m310', 'assistant:m311', 'assistant:m312', "
                    "'assistant:m313', 'assistant:m314', 'assistant:m315', "
                    "'assistant:m316', 'assistant:m317', 'assistant:m318', "
                    "'assistant:m319', 'assistant:m32', 'assistant:m320', "
                    "'assistant:m321', 'assistant:m322', 'assistant:m323', "
                    "'assistant:m324', 'assistant:m325', 'assistant:m326', "
                    "'assistant:m327', 'assistant:m328', 'assistant:m329', "
                    "'assistant:m33', 'assistant:m330', 'assistant:m331', "
                    "'assistant:m332', 'assistant:m333', 'assistant:m334', "
                    "'assistant:m335', 'assistant:m336', 'assistant:m337', "
                    "'assistant:m338', 'assistant:m339', 'assistant:m34', "
                    "'assistant:m340', 'assistant:m341', 'assistant:m342', "
                    "'assistant:m343', 'assistant:m344', 'assistant:m345', "
                    "'assistant:m346', 'assistant:m347', 'assistant:m348', "
                    "'assistant:m349', 'assistant:m35', 'assistant:m350', "
                    "'assistant:m351', 'assistant:m352', 'assistant:m353', "
                    "'assistant:m354', 'assistant:m355', 'assistant:m356', "
                    "'assistant:m357', 'assistant:m358', 'assistant:m359', "
                    "'assistant:m36', 'assistant:m360', 'assistant:m361', "
                    "'assistant:m362', 'assistant:m363', 'assistant:m364', "
                    "'assistant:m365', 'assistant:m366', 'assistant:m367', "
                    "'assistant:m368', 'assistant:m369', 'assistant:m37', "
                    "'assistant:m370', 'assistant:m371', 'assistant:m372', "
                    "'assistant:m373', 'assistant:m374', 'assistant:m375', "
                    "'assistant:m376', 'assistant:m377', 'assistant:m378', "
                    "'assistant:m379', 'assistant:m38', 'assistant:m380', "
                    "'assistant:m381', 'assistant:m382', 'assistant:m383', "
                    "'assistant:m384', 'assistant:m385', 'assistant:m386', "
                    "'assistant:m387', 'assistant:m388', 'assistant:m389', "
                    "'assistant:m39', 'assistant:m390', 'assistant:m391', "
                    "'assistant:m392', 'assistant:m393', 'assistant:m394', "
                    "'assistant:m395', 'assistant:m396', 'assistant:m397', "
                    "'assistant:m398', 'assistant:m399', 'assistant:m4', "
                    "'assistant:m40', 'assistant:m400', 'assistant:m401', "
                    "'assistant:m402', 'assistant:m403', 'assistant:m404', "
                    "'assistant:m405', 'assistant:m406', 'assistant:m407', "
                    "'assistant:m408', 'assistant:m409', 'assistant:m41', "
                    "'assistant:m410', 'assistant:m411', 'assistant:m412', "
                    "'assistant:m413', 'assistant:m414', 'assistant:m415', "
                    "'assistant:m416', 'assistant:m417', 'assistant:m418', "
                    "'assistant:m419', 'assistant:m42', 'assistant:m420', "
                    "'assistant:m421', 'assistant:m422', 'assistant:m423', "
                    "'assistant:m424', 'assistant:m425', 'assistant:m426', "
                    "'assistant:m427', 'assistant:m428', 'assistant:m429', "
                    "'assistant:m43', 'assistant:m430', 'assistant:m431', "
                    "'assistant:m432', 'assistant:m433', 'assistant:m434', "
                    "'assistant:m435', 'assistant:m436', 'assistant:m437', "
                    "'assistant:m438', 'assistant:m439', 'assistant:m44', "
                    "'assistant:m440', 'assistant:m441', 'assistant:m442', "
                    "'assistant:m443', 'assistant:m444', 'assistant:m445', "
                    "'assistant:m446', 'assistant:m447', 'assistant:m448', "
                    "'assistant:m449', 'assistant:m45', 'assistant:m450', "
                    "'assistant:m451', 'assistant:m452', 'assistant:m453', "
                    "'assistant:m454', 'assistant:m455', 'assistant:m456', "
                    "'assistant:m457', 'assistant:m458', 'assistant:m459', "
                    "'assistant:m46', 'assistant:m460', 'assistant:m461', "
                    "'assistant:m462', 'assistant:m463', 'assistant:m464', "
                    "'assistant:m465', 'assistant:m466', 'assistant:m467', "
                    "'assistant:m468', 'assistant:m469', 'assistant:m47', "
                    "'assistant:m470', 'assistant:m471', 'assistant:m472', "
                    "'assistant:m473', 'assistant:m474', 'assistant:m475', "
                    "'assistant:m476', 'assistant:m477', 'assistant:m478', "
                    "'assistant:m479', 'assistant:m48', 'assistant:m480', "
                    "'assistant:m481', 'assistant:m482', 'assistant:m483', "
                    "'assistant:m484', 'assistant:m485', 'assistant:m486', "
                    "'assistant:m487', 'assistant:m488', 'assistant:m489', "
                    "'assistant:m49', 'assistant:m490', 'assistant:m491', "
                    "'assistant:m492', 'assistant:m493', 'assistant:m494', "
                    "'assistant:m495', 'assistant:m496', 'assistant:m497', "
                    "'assistant:m498', 'assistant:m499', 'assistant:m5', "
                    "'assistant:m50', 'assistant:m500', 'assistant:m501', "
                    "'assistant:m502', 'assistant:m503', 'assistant:m504', "
                    "'assistant:m505', 'assistant:m506', 'assistant:m507', "
                    "'assistant:m508', 'assistant:m509', 'assistant:m51', "
                    "'assistant:m510', 'assistant:m511', 'assistant:m512', "
                    "'assistant:m513', 'assistant:m514', 'assistant:m515', "
                    "'assistant:m516', 'assistant:m517', 'assistant:m518', "
                    "'assistant:m519', 'assistant:m52', 'assistant:m520', "
                    "'assistant:m521', 'assistant:m522', 'assistant:m523', "
                    "'assistant:m524', 'assistant:m525', 'assistant:m526', "
                    "'assistant:m527', 'assistant:m528', 'assistant:m529', "
                    "'assistant:m53', 'assistant:m530', 'assistant:m531', "
                    "'assistant:m532', 'assistant:m533', 'assistant:m534', "
                    "'assistant:m535', 'assistant:m536', 'assistant:m537', "
                    "'assistant:m538', 'assistant:m539', 'assistant:m54', "
                    "'assistant:m540', 'assistant:m541', 'assistant:m542', "
                    "'assistant:m543', 'assistant:m544', 'assistant:m545', "
                    "'assistant:m546', 'assistant:m547', 'assistant:m548', "
                    "'assistant:m549', 'assistant:m55', 'assistant:m550', "
                    "'assistant:m551', 'assistant:m552', 'assistant:m553', "
                    "'assistant:m554', 'assistant:m555', 'assistant:m556', "
                    "'assistant:m557', 'assistant:m558', 'assistant:m559', "
                    "'assistant:m56', 'assistant:m560', 'assistant:m561', "
                    "'assistant:m562', 'assistant:m563', 'assistant:m564', "
                    "'assistant:m565', 'assistant:m566', 'assistant:m567', "
                    "'assistant:m568', 'assistant:m569', 'assistant:m57', "
                    "'assistant:m570', 'assistant:m571', 'assistant:m572', "
                    "'assistant:m573', 'assistant:m574', 'assistant:m575', "
                    "'assistant:m576', 'assistant:m577', 'assistant:m578', "
                    "'assistant:m579', 'assistant:m58', 'assistant:m580', "
                    "'assistant:m581', 'assistant:m582', 'assistant:m583', "
                    "'assistant:m584', 'assistant:m585', 'assistant:m586', "
                    "'assistant:m587', 'assistant:m588', 'assistant:m589', "
                    "'assistant:m59', 'assistant:m590', 'assistant:m591', "
                    "'assistant:m592', 'assistant:m593', 'assistant:m594', "
                    "'assistant:m595', 'assistant:m596', 'assistant:m597', "
                    "'assistant:m598', 'assistant:m599', 'assistant:m6', "
                    "'assistant:m60', 'assistant:m600', 'assistant:m601', "
                    "'assistant:m602', 'assistant:m603', 'assistant:m604', "
                    "'assistant:m605', 'assistant:m606', 'assistant:m607', "
                    "'assistant:m608', 'assistant:m609', 'assistant:m61', "
                    "'assistant:m610', 'assistant:m611', 'assistant:m612', "
                    "'assistant:m613', 'assistant:m614', 'assistant:m615', "
                    "'assistant:m616', 'assistant:m617', 'assistant:m618', "
                    "'assistant:m619', 'assistant:m62', 'assistant:m620', "
                    "'assistant:m621', 'assistant:m622', 'assistant:m623', "
                    "'assistant:m624', 'assistant:m625', 'assistant:m626', "
                    "'assistant:m627', 'assistant:m628', 'assistant:m629', "
                    "'assistant:m63', 'assistant:m630', 'assistant:m631', "
                    "'assistant:m632', 'assistant:m633', 'assistant:m634', "
                    "'assistant:m635', 'assistant:m636', 'assistant:m637', "
                    "'assistant:m638', 'assistant:m639', 'assistant:m64', "
                    "'assistant:m640', 'assistant:m641', 'assistant:m642', "
                    "'assistant:m643', 'assistant:m644', 'assistant:m645', "
                    "'assistant:m646', 'assistant:m647', 'assistant:m648', "
                    "'assistant:m649', 'assistant:m65', 'assistant:m650', "
                    "'assistant:m651', 'assistant:m652', 'assistant:m653', "
                    "'assistant:m654', 'assistant:m655', 'assistant:m656', "
                    "'assistant:m657', 'assistant:m658', 'assistant:m659', "
                    "'assistant:m66', 'assistant:m660', 'assistant:m661', "
                    "'assistant:m662', 'assistant:m663', 'assistant:m664', "
                    "'assistant:m665', 'assistant:m666', 'assistant:m667', "
                    "'assistant:m668', 'assistant:m669', 'assistant:m67', "
                    "'assistant:m670', 'assistant:m671', 'assistant:m672', "
                    "'assistant:m673', 'assistant:m674', 'assistant:m675', "
                    "'assistant:m676', 'assistant:m677', 'assistant:m678', "
                    "'assistant:m679', 'assistant:m68', 'assistant:m680', "
                    "'assistant:m681', 'assistant:m682', 'assistant:m683', "
                    "'assistant:m684', 'assistant:m685', 'assistant:m686', "
                    "'assistant:m687', 'assistant:m688', 'assistant:m689', "
                    "'assistant:m69', 'assistant:m690', 'assistant:m691', "
                    "'assistant:m692', 'assistant:m693', 'assistant:m694', "
                    "'assistant:m695', 'assistant:m696', 'assistant:m697', "
                    "'assistant:m698', 'assistant:m699', 'assistant:m7', "
                    "'assistant:m70', 'assistant:m700', 'assistant:m701', "
                    "'assistant:m702', 'assistant:m703', 'assistant:m704', "
                    "'assistant:m705', 'assistant:m706', 'assistant:m707', "
                    "'assistant:m708', 'assistant:m709', 'assistant:m71', "
                    "'assistant:m710', 'assistant:m711', 'assistant:m712', "
                    "'assistant:m713', 'assistant:m714', 'assistant:m715', "
                    "'assistant:m716', 'assistant:m717', 'assistant:m718', "
                    "'assistant:m719', 'assistant:m72', 'assistant:m720', "
                    "'assistant:m721', 'assistant:m722', 'assistant:m723', "
                    "'assistant:m724', 'assistant:m725', 'assistant:m726', "
                    "'assistant:m727', 'assistant:m728', 'assistant:m729', "
                    "'assistant:m73', 'assistant:m730', 'assistant:m731', "
                    "'assistant:m732', 'assistant:m733', 'assistant:m734', "
                    "'assistant:m735', 'assistant:m736', 'assistant:m737', "
                    "'assistant:m738', 'assistant:m739', 'assistant:m74', "
                    "'assistant:m740', 'assistant:m741', 'assistant:m742', "
                    "'assistant:m743', 'assistant:m744', 'assistant:m745', "
                    "'assistant:m746', 'assistant:m747', 'assistant:m748', "
                    "'assistant:m749', 'assistant:m75', 'assistant:m750', "
                    "'assistant:m751', 'assistant:m752', 'assistant:m753', "
                    "'assistant:m754', 'assistant:m755', 'assistant:m756', "
                    "'assistant:m757', 'assistant:m758', 'assistant:m759', "
                    "'assistant:m76', 'assistant:m760', 'assistant:m761', "
                    "'assistant:m762', 'assistant:m763', 'assistant:m764', "
                    "'assistant:m765', 'assistant:m766', 'assistant:m767', "
                    "'assistant:m768', 'assistant:m769', 'assistant:m77', "
                    "'assistant:m770', 'assistant:m771', 'assistant:m772', "
                    "'assistant:m773', 'assistant:m774', 'assistant:m775', "
                    "'assistant:m776', 'assistant:m777', 'assistant:m778', "
                    "'assistant:m779', 'assistant:m78', 'assistant:m780', "
                    "'assistant:m781', 'assistant:m782', 'assistant:m783', "
                    "'assistant:m784', 'assistant:m785', 'assistant:m786', "
                    "'assistant:m787', 'assistant:m788', 'assistant:m789', "
                    "'assistant:m79', 'assistant:m790', 'assistant:m791', "
                    "'assistant:m792', 'assistant:m793', 'assistant:m794', "
                    "'assistant:m795', 'assistant:m796', 'assistant:m797', "
                    "'assistant:m798', 'assistant:m799', 'assistant:m8', "
                    "'assistant:m80', 'assistant:m800', 'assistant:m801', "
                    "'assistant:m802', 'assistant:m803', 'assistant:m804', "
                    "'assistant:m805', 'assistant:m806', 'assistant:m807', "
                    "'assistant:m808', 'assistant:m809', 'assistant:m81', "
                    "'assistant:m810', 'assistant:m811', 'assistant:m812', "
                    "'assistant:m813', 'assistant:m814', 'assistant:m815', "
                    "'assistant:m816', 'assistant:m817', 'assistant:m818', "
                    "'assistant:m819', 'assistant:m82', 'assistant:m820', "
                    "'assistant:m821', 'assistant:m822', 'assistant:m823', "
                    "'assistant:m824', 'assistant:m825', 'assistant:m826', "
                    "'assistant:m827', 'assistant:m828', 'assistant:m829', "
                    "'assistant:m83', 'assistant:m830', 'assistant:m831', "
                    "'assistant:m832', 'assistant:m833', 'assistant:m834', "
                    "'assistant:m835', 'assistant:m836', 'assistant:m837', "
                    "'assistant:m838', 'assistant:m839', 'assistant:m84', "
                    "'assistant:m840', 'assistant:m841', 'assistant:m842', "
                    "'assistant:m843', 'assistant:m844', 'assistant:m845', "
                    "'assistant:m846', 'assistant:m847', 'assistant:m848', "
                    "'assistant:m849', 'assistant:m85', 'assistant:m850', "
                    "'assistant:m851', 'assistant:m852', 'assistant:m853', "
                    "'assistant:m854', 'assistant:m855', 'assistant:m856', "
                    "'assistant:m857', 'assistant:m858', 'assistant:m859', "
                    "'assistant:m86', 'assistant:m860', 'assistant:m861', "
                    "'assistant:m862', 'assistant:m863', 'assistant:m864', "
                    "'assistant:m865', 'assistant:m866', 'assistant:m867', "
                    "'assistant:m868', 'assistant:m869', 'assistant:m87', "
                    "'assistant:m870', 'assistant:m871', 'assistant:m872', "
                    "'assistant:m873', 'assistant:m874', 'assistant:m875', "
                    "'assistant:m876', 'assistant:m877', 'assistant:m878', "
                    "'assistant:m879', 'assistant:m88', 'assistant:m880', "
                    "'assistant:m881', 'assistant:m882', 'assistant:m883', "
                    "'assistant:m884', 'assistant:m885', 'assistant:m886', "
                    "'assistant:m887', 'assistant:m888', 'assistant:m889', "
                    "'assistant:m89', 'assistant:m890', 'assistant:m891', "
                    "'assistant:m892', 'assistant:m893', 'assistant:m894', "
                    "'assistant:m895', 'assistant:m896', 'assistant:m897', "
                    "'assistant:m898', 'assistant:m899', 'assistant:m9', "
                    "'assistant:m90', 'assistant:m900', 'assistant:m901', "
                    "'assistant:m902', 'assistant:m903', 'assistant:m904', "
                    "'assistant:m905', 'assistant:m906', 'assistant:m907', "
                    "'assistant:m908', 'assistant:m909', 'assistant:m91', "
                    "'assistant:m910', 'assistant:m911', 'assistant:m912', "
                    "'assistant:m913', 'assistant:m914', 'assistant:m915', "
                    "'assistant:m916', 'assistant:m917', 'assistant:m918', "
                    "'assistant:m919', 'assistant:m92', 'assistant:m920', "
                    "'assistant:m921', 'assistant:m922', 'assistant:m923', "
                    "'assistant:m924', 'assistant:m925', 'assistant:m926', "
                    "'assistant:m927', 'assistant:m928', 'assistant:m929', "
                    "'assistant:m93', 'assistant:m930', 'assistant:m931', "
                    "'assistant:m932', 'assistant:m933', 'assistant:m934', "
                    "'assistant:m935', 'assistant:m936', 'assistant:m937', "
                    "'assistant:m938', 'assistant:m939', 'assistant:m94', "
                    "'assistant:m940', 'assistant:m941', 'assistant:m942', "
                    "'assistant:m943', 'assistant:m944', 'assistant:m945', "
                    "'assistant:m946', 'assistant:m947', 'assistant:m948', "
                    "'assistant:m949', 'assistant:m95', 'assistant:m950', "
                    "'assistant:m951', 'assistant:m952', 'assistant:m953', "
                    "'assistant:m954', 'assistant:m955', 'assistant:m956', "
                    "'assistant:m957', 'assistant:m958', 'assistant:m959', "
                    "'assistant:m96', 'assistant:m960', 'assistant:m961', "
                    "'assistant:m962', 'assistant:m963', 'assistant:m964', "
                    "'assistant:m965', 'assistant:m966', 'assistant:m967', "
                    "'assistant:m968', 'assistant:m969', 'assistant:m97', "
                    "'assistant:m970', 'assistant:m971', 'assistant:m972', "
                    "'assistant:m973', 'assistant:m974', 'assistant:m975', "
                    "'assistant:m976', 'assistant:m977', 'assistant:m978', "
                    "'assistant:m979', 'assistant:m98', 'assistant:m980', "
                    "'assistant:m981', 'assistant:m982', 'assistant:m983', "
                    "'assistant:m984', 'assistant:m985', 'assistant:m986', "
                    "'assistant:m987', 'assistant:m988', 'assistant:m989', "
                    "'assistant:m99', 'assistant:m990', 'assistant:m991', "
                    "'assistant:m992', 'assistant:m993', 'assistant:m994', "
                    "'assistant:m995', 'assistant:m996', 'assistant:m997', "
                    "'tool:<81:2979c23e>', 'user:first']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<80:56fdf1aa>"],
            ],
            [
                "history_0_1000",
                ["ok", "d955c79c2efbb5bd1c990138ba585a3a7f0caf9eb4144f13ae3ccf250abeaef5", 94954],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=0,limit=1000)",
                    "release",
                ],
                [],
                ["<80:56fdf1aa>"],
            ],
        ],
        "rows_1001": [
            [
                "snapshot_1001",
                ["ok", "d8cbb96ba848d9e8819859a525bc47bd37c43ed0150b510db572062046eeaacb", 95244],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,latest=True,limit=1001)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:m0', 'assistant:m1', "
                    "'assistant:m10', 'assistant:m100', 'assistant:m101', "
                    "'assistant:m102', 'assistant:m103', 'assistant:m104', "
                    "'assistant:m105', 'assistant:m106', 'assistant:m107', "
                    "'assistant:m108', 'assistant:m109', 'assistant:m11', "
                    "'assistant:m110', 'assistant:m111', 'assistant:m112', "
                    "'assistant:m113', 'assistant:m114', 'assistant:m115', "
                    "'assistant:m116', 'assistant:m117', 'assistant:m118', "
                    "'assistant:m119', 'assistant:m12', 'assistant:m120', "
                    "'assistant:m121', 'assistant:m122', 'assistant:m123', "
                    "'assistant:m124', 'assistant:m125', 'assistant:m126', "
                    "'assistant:m127', 'assistant:m128', 'assistant:m129', "
                    "'assistant:m13', 'assistant:m130', 'assistant:m131', "
                    "'assistant:m132', 'assistant:m133', 'assistant:m134', "
                    "'assistant:m135', 'assistant:m136', 'assistant:m137', "
                    "'assistant:m138', 'assistant:m139', 'assistant:m14', "
                    "'assistant:m140', 'assistant:m141', 'assistant:m142', "
                    "'assistant:m143', 'assistant:m144', 'assistant:m145', "
                    "'assistant:m146', 'assistant:m147', 'assistant:m148', "
                    "'assistant:m149', 'assistant:m15', 'assistant:m150', "
                    "'assistant:m151', 'assistant:m152', 'assistant:m153', "
                    "'assistant:m154', 'assistant:m155', 'assistant:m156', "
                    "'assistant:m157', 'assistant:m158', 'assistant:m159', "
                    "'assistant:m16', 'assistant:m160', 'assistant:m161', "
                    "'assistant:m162', 'assistant:m163', 'assistant:m164', "
                    "'assistant:m165', 'assistant:m166', 'assistant:m167', "
                    "'assistant:m168', 'assistant:m169', 'assistant:m17', "
                    "'assistant:m170', 'assistant:m171', 'assistant:m172', "
                    "'assistant:m173', 'assistant:m174', 'assistant:m175', "
                    "'assistant:m176', 'assistant:m177', 'assistant:m178', "
                    "'assistant:m179', 'assistant:m18', 'assistant:m180', "
                    "'assistant:m181', 'assistant:m182', 'assistant:m183', "
                    "'assistant:m184', 'assistant:m185', 'assistant:m186', "
                    "'assistant:m187', 'assistant:m188', 'assistant:m189', "
                    "'assistant:m19', 'assistant:m190', 'assistant:m191', "
                    "'assistant:m192', 'assistant:m193', 'assistant:m194', "
                    "'assistant:m195', 'assistant:m196', 'assistant:m197', "
                    "'assistant:m198', 'assistant:m199', 'assistant:m2', "
                    "'assistant:m20', 'assistant:m200', 'assistant:m201', "
                    "'assistant:m202', 'assistant:m203', 'assistant:m204', "
                    "'assistant:m205', 'assistant:m206', 'assistant:m207', "
                    "'assistant:m208', 'assistant:m209', 'assistant:m21', "
                    "'assistant:m210', 'assistant:m211', 'assistant:m212', "
                    "'assistant:m213', 'assistant:m214', 'assistant:m215', "
                    "'assistant:m216', 'assistant:m217', 'assistant:m218', "
                    "'assistant:m219', 'assistant:m22', 'assistant:m220', "
                    "'assistant:m221', 'assistant:m222', 'assistant:m223', "
                    "'assistant:m224', 'assistant:m225', 'assistant:m226', "
                    "'assistant:m227', 'assistant:m228', 'assistant:m229', "
                    "'assistant:m23', 'assistant:m230', 'assistant:m231', "
                    "'assistant:m232', 'assistant:m233', 'assistant:m234', "
                    "'assistant:m235', 'assistant:m236', 'assistant:m237', "
                    "'assistant:m238', 'assistant:m239', 'assistant:m24', "
                    "'assistant:m240', 'assistant:m241', 'assistant:m242', "
                    "'assistant:m243', 'assistant:m244', 'assistant:m245', "
                    "'assistant:m246', 'assistant:m247', 'assistant:m248', "
                    "'assistant:m249', 'assistant:m25', 'assistant:m250', "
                    "'assistant:m251', 'assistant:m252', 'assistant:m253', "
                    "'assistant:m254', 'assistant:m255', 'assistant:m256', "
                    "'assistant:m257', 'assistant:m258', 'assistant:m259', "
                    "'assistant:m26', 'assistant:m260', 'assistant:m261', "
                    "'assistant:m262', 'assistant:m263', 'assistant:m264', "
                    "'assistant:m265', 'assistant:m266', 'assistant:m267', "
                    "'assistant:m268', 'assistant:m269', 'assistant:m27', "
                    "'assistant:m270', 'assistant:m271', 'assistant:m272', "
                    "'assistant:m273', 'assistant:m274', 'assistant:m275', "
                    "'assistant:m276', 'assistant:m277', 'assistant:m278', "
                    "'assistant:m279', 'assistant:m28', 'assistant:m280', "
                    "'assistant:m281', 'assistant:m282', 'assistant:m283', "
                    "'assistant:m284', 'assistant:m285', 'assistant:m286', "
                    "'assistant:m287', 'assistant:m288', 'assistant:m289', "
                    "'assistant:m29', 'assistant:m290', 'assistant:m291', "
                    "'assistant:m292', 'assistant:m293', 'assistant:m294', "
                    "'assistant:m295', 'assistant:m296', 'assistant:m297', "
                    "'assistant:m298', 'assistant:m299', 'assistant:m3', "
                    "'assistant:m30', 'assistant:m300', 'assistant:m301', "
                    "'assistant:m302', 'assistant:m303', 'assistant:m304', "
                    "'assistant:m305', 'assistant:m306', 'assistant:m307', "
                    "'assistant:m308', 'assistant:m309', 'assistant:m31', "
                    "'assistant:m310', 'assistant:m311', 'assistant:m312', "
                    "'assistant:m313', 'assistant:m314', 'assistant:m315', "
                    "'assistant:m316', 'assistant:m317', 'assistant:m318', "
                    "'assistant:m319', 'assistant:m32', 'assistant:m320', "
                    "'assistant:m321', 'assistant:m322', 'assistant:m323', "
                    "'assistant:m324', 'assistant:m325', 'assistant:m326', "
                    "'assistant:m327', 'assistant:m328', 'assistant:m329', "
                    "'assistant:m33', 'assistant:m330', 'assistant:m331', "
                    "'assistant:m332', 'assistant:m333', 'assistant:m334', "
                    "'assistant:m335', 'assistant:m336', 'assistant:m337', "
                    "'assistant:m338', 'assistant:m339', 'assistant:m34', "
                    "'assistant:m340', 'assistant:m341', 'assistant:m342', "
                    "'assistant:m343', 'assistant:m344', 'assistant:m345', "
                    "'assistant:m346', 'assistant:m347', 'assistant:m348', "
                    "'assistant:m349', 'assistant:m35', 'assistant:m350', "
                    "'assistant:m351', 'assistant:m352', 'assistant:m353', "
                    "'assistant:m354', 'assistant:m355', 'assistant:m356', "
                    "'assistant:m357', 'assistant:m358', 'assistant:m359', "
                    "'assistant:m36', 'assistant:m360', 'assistant:m361', "
                    "'assistant:m362', 'assistant:m363', 'assistant:m364', "
                    "'assistant:m365', 'assistant:m366', 'assistant:m367', "
                    "'assistant:m368', 'assistant:m369', 'assistant:m37', "
                    "'assistant:m370', 'assistant:m371', 'assistant:m372', "
                    "'assistant:m373', 'assistant:m374', 'assistant:m375', "
                    "'assistant:m376', 'assistant:m377', 'assistant:m378', "
                    "'assistant:m379', 'assistant:m38', 'assistant:m380', "
                    "'assistant:m381', 'assistant:m382', 'assistant:m383', "
                    "'assistant:m384', 'assistant:m385', 'assistant:m386', "
                    "'assistant:m387', 'assistant:m388', 'assistant:m389', "
                    "'assistant:m39', 'assistant:m390', 'assistant:m391', "
                    "'assistant:m392', 'assistant:m393', 'assistant:m394', "
                    "'assistant:m395', 'assistant:m396', 'assistant:m397', "
                    "'assistant:m398', 'assistant:m399', 'assistant:m4', "
                    "'assistant:m40', 'assistant:m400', 'assistant:m401', "
                    "'assistant:m402', 'assistant:m403', 'assistant:m404', "
                    "'assistant:m405', 'assistant:m406', 'assistant:m407', "
                    "'assistant:m408', 'assistant:m409', 'assistant:m41', "
                    "'assistant:m410', 'assistant:m411', 'assistant:m412', "
                    "'assistant:m413', 'assistant:m414', 'assistant:m415', "
                    "'assistant:m416', 'assistant:m417', 'assistant:m418', "
                    "'assistant:m419', 'assistant:m42', 'assistant:m420', "
                    "'assistant:m421', 'assistant:m422', 'assistant:m423', "
                    "'assistant:m424', 'assistant:m425', 'assistant:m426', "
                    "'assistant:m427', 'assistant:m428', 'assistant:m429', "
                    "'assistant:m43', 'assistant:m430', 'assistant:m431', "
                    "'assistant:m432', 'assistant:m433', 'assistant:m434', "
                    "'assistant:m435', 'assistant:m436', 'assistant:m437', "
                    "'assistant:m438', 'assistant:m439', 'assistant:m44', "
                    "'assistant:m440', 'assistant:m441', 'assistant:m442', "
                    "'assistant:m443', 'assistant:m444', 'assistant:m445', "
                    "'assistant:m446', 'assistant:m447', 'assistant:m448', "
                    "'assistant:m449', 'assistant:m45', 'assistant:m450', "
                    "'assistant:m451', 'assistant:m452', 'assistant:m453', "
                    "'assistant:m454', 'assistant:m455', 'assistant:m456', "
                    "'assistant:m457', 'assistant:m458', 'assistant:m459', "
                    "'assistant:m46', 'assistant:m460', 'assistant:m461', "
                    "'assistant:m462', 'assistant:m463', 'assistant:m464', "
                    "'assistant:m465', 'assistant:m466', 'assistant:m467', "
                    "'assistant:m468', 'assistant:m469', 'assistant:m47', "
                    "'assistant:m470', 'assistant:m471', 'assistant:m472', "
                    "'assistant:m473', 'assistant:m474', 'assistant:m475', "
                    "'assistant:m476', 'assistant:m477', 'assistant:m478', "
                    "'assistant:m479', 'assistant:m48', 'assistant:m480', "
                    "'assistant:m481', 'assistant:m482', 'assistant:m483', "
                    "'assistant:m484', 'assistant:m485', 'assistant:m486', "
                    "'assistant:m487', 'assistant:m488', 'assistant:m489', "
                    "'assistant:m49', 'assistant:m490', 'assistant:m491', "
                    "'assistant:m492', 'assistant:m493', 'assistant:m494', "
                    "'assistant:m495', 'assistant:m496', 'assistant:m497', "
                    "'assistant:m498', 'assistant:m499', 'assistant:m5', "
                    "'assistant:m50', 'assistant:m500', 'assistant:m501', "
                    "'assistant:m502', 'assistant:m503', 'assistant:m504', "
                    "'assistant:m505', 'assistant:m506', 'assistant:m507', "
                    "'assistant:m508', 'assistant:m509', 'assistant:m51', "
                    "'assistant:m510', 'assistant:m511', 'assistant:m512', "
                    "'assistant:m513', 'assistant:m514', 'assistant:m515', "
                    "'assistant:m516', 'assistant:m517', 'assistant:m518', "
                    "'assistant:m519', 'assistant:m52', 'assistant:m520', "
                    "'assistant:m521', 'assistant:m522', 'assistant:m523', "
                    "'assistant:m524', 'assistant:m525', 'assistant:m526', "
                    "'assistant:m527', 'assistant:m528', 'assistant:m529', "
                    "'assistant:m53', 'assistant:m530', 'assistant:m531', "
                    "'assistant:m532', 'assistant:m533', 'assistant:m534', "
                    "'assistant:m535', 'assistant:m536', 'assistant:m537', "
                    "'assistant:m538', 'assistant:m539', 'assistant:m54', "
                    "'assistant:m540', 'assistant:m541', 'assistant:m542', "
                    "'assistant:m543', 'assistant:m544', 'assistant:m545', "
                    "'assistant:m546', 'assistant:m547', 'assistant:m548', "
                    "'assistant:m549', 'assistant:m55', 'assistant:m550', "
                    "'assistant:m551', 'assistant:m552', 'assistant:m553', "
                    "'assistant:m554', 'assistant:m555', 'assistant:m556', "
                    "'assistant:m557', 'assistant:m558', 'assistant:m559', "
                    "'assistant:m56', 'assistant:m560', 'assistant:m561', "
                    "'assistant:m562', 'assistant:m563', 'assistant:m564', "
                    "'assistant:m565', 'assistant:m566', 'assistant:m567', "
                    "'assistant:m568', 'assistant:m569', 'assistant:m57', "
                    "'assistant:m570', 'assistant:m571', 'assistant:m572', "
                    "'assistant:m573', 'assistant:m574', 'assistant:m575', "
                    "'assistant:m576', 'assistant:m577', 'assistant:m578', "
                    "'assistant:m579', 'assistant:m58', 'assistant:m580', "
                    "'assistant:m581', 'assistant:m582', 'assistant:m583', "
                    "'assistant:m584', 'assistant:m585', 'assistant:m586', "
                    "'assistant:m587', 'assistant:m588', 'assistant:m589', "
                    "'assistant:m59', 'assistant:m590', 'assistant:m591', "
                    "'assistant:m592', 'assistant:m593', 'assistant:m594', "
                    "'assistant:m595', 'assistant:m596', 'assistant:m597', "
                    "'assistant:m598', 'assistant:m599', 'assistant:m6', "
                    "'assistant:m60', 'assistant:m600', 'assistant:m601', "
                    "'assistant:m602', 'assistant:m603', 'assistant:m604', "
                    "'assistant:m605', 'assistant:m606', 'assistant:m607', "
                    "'assistant:m608', 'assistant:m609', 'assistant:m61', "
                    "'assistant:m610', 'assistant:m611', 'assistant:m612', "
                    "'assistant:m613', 'assistant:m614', 'assistant:m615', "
                    "'assistant:m616', 'assistant:m617', 'assistant:m618', "
                    "'assistant:m619', 'assistant:m62', 'assistant:m620', "
                    "'assistant:m621', 'assistant:m622', 'assistant:m623', "
                    "'assistant:m624', 'assistant:m625', 'assistant:m626', "
                    "'assistant:m627', 'assistant:m628', 'assistant:m629', "
                    "'assistant:m63', 'assistant:m630', 'assistant:m631', "
                    "'assistant:m632', 'assistant:m633', 'assistant:m634', "
                    "'assistant:m635', 'assistant:m636', 'assistant:m637', "
                    "'assistant:m638', 'assistant:m639', 'assistant:m64', "
                    "'assistant:m640', 'assistant:m641', 'assistant:m642', "
                    "'assistant:m643', 'assistant:m644', 'assistant:m645', "
                    "'assistant:m646', 'assistant:m647', 'assistant:m648', "
                    "'assistant:m649', 'assistant:m65', 'assistant:m650', "
                    "'assistant:m651', 'assistant:m652', 'assistant:m653', "
                    "'assistant:m654', 'assistant:m655', 'assistant:m656', "
                    "'assistant:m657', 'assistant:m658', 'assistant:m659', "
                    "'assistant:m66', 'assistant:m660', 'assistant:m661', "
                    "'assistant:m662', 'assistant:m663', 'assistant:m664', "
                    "'assistant:m665', 'assistant:m666', 'assistant:m667', "
                    "'assistant:m668', 'assistant:m669', 'assistant:m67', "
                    "'assistant:m670', 'assistant:m671', 'assistant:m672', "
                    "'assistant:m673', 'assistant:m674', 'assistant:m675', "
                    "'assistant:m676', 'assistant:m677', 'assistant:m678', "
                    "'assistant:m679', 'assistant:m68', 'assistant:m680', "
                    "'assistant:m681', 'assistant:m682', 'assistant:m683', "
                    "'assistant:m684', 'assistant:m685', 'assistant:m686', "
                    "'assistant:m687', 'assistant:m688', 'assistant:m689', "
                    "'assistant:m69', 'assistant:m690', 'assistant:m691', "
                    "'assistant:m692', 'assistant:m693', 'assistant:m694', "
                    "'assistant:m695', 'assistant:m696', 'assistant:m697', "
                    "'assistant:m698', 'assistant:m699', 'assistant:m7', "
                    "'assistant:m70', 'assistant:m700', 'assistant:m701', "
                    "'assistant:m702', 'assistant:m703', 'assistant:m704', "
                    "'assistant:m705', 'assistant:m706', 'assistant:m707', "
                    "'assistant:m708', 'assistant:m709', 'assistant:m71', "
                    "'assistant:m710', 'assistant:m711', 'assistant:m712', "
                    "'assistant:m713', 'assistant:m714', 'assistant:m715', "
                    "'assistant:m716', 'assistant:m717', 'assistant:m718', "
                    "'assistant:m719', 'assistant:m72', 'assistant:m720', "
                    "'assistant:m721', 'assistant:m722', 'assistant:m723', "
                    "'assistant:m724', 'assistant:m725', 'assistant:m726', "
                    "'assistant:m727', 'assistant:m728', 'assistant:m729', "
                    "'assistant:m73', 'assistant:m730', 'assistant:m731', "
                    "'assistant:m732', 'assistant:m733', 'assistant:m734', "
                    "'assistant:m735', 'assistant:m736', 'assistant:m737', "
                    "'assistant:m738', 'assistant:m739', 'assistant:m74', "
                    "'assistant:m740', 'assistant:m741', 'assistant:m742', "
                    "'assistant:m743', 'assistant:m744', 'assistant:m745', "
                    "'assistant:m746', 'assistant:m747', 'assistant:m748', "
                    "'assistant:m749', 'assistant:m75', 'assistant:m750', "
                    "'assistant:m751', 'assistant:m752', 'assistant:m753', "
                    "'assistant:m754', 'assistant:m755', 'assistant:m756', "
                    "'assistant:m757', 'assistant:m758', 'assistant:m759', "
                    "'assistant:m76', 'assistant:m760', 'assistant:m761', "
                    "'assistant:m762', 'assistant:m763', 'assistant:m764', "
                    "'assistant:m765', 'assistant:m766', 'assistant:m767', "
                    "'assistant:m768', 'assistant:m769', 'assistant:m77', "
                    "'assistant:m770', 'assistant:m771', 'assistant:m772', "
                    "'assistant:m773', 'assistant:m774', 'assistant:m775', "
                    "'assistant:m776', 'assistant:m777', 'assistant:m778', "
                    "'assistant:m779', 'assistant:m78', 'assistant:m780', "
                    "'assistant:m781', 'assistant:m782', 'assistant:m783', "
                    "'assistant:m784', 'assistant:m785', 'assistant:m786', "
                    "'assistant:m787', 'assistant:m788', 'assistant:m789', "
                    "'assistant:m79', 'assistant:m790', 'assistant:m791', "
                    "'assistant:m792', 'assistant:m793', 'assistant:m794', "
                    "'assistant:m795', 'assistant:m796', 'assistant:m797', "
                    "'assistant:m798', 'assistant:m799', 'assistant:m8', "
                    "'assistant:m80', 'assistant:m800', 'assistant:m801', "
                    "'assistant:m802', 'assistant:m803', 'assistant:m804', "
                    "'assistant:m805', 'assistant:m806', 'assistant:m807', "
                    "'assistant:m808', 'assistant:m809', 'assistant:m81', "
                    "'assistant:m810', 'assistant:m811', 'assistant:m812', "
                    "'assistant:m813', 'assistant:m814', 'assistant:m815', "
                    "'assistant:m816', 'assistant:m817', 'assistant:m818', "
                    "'assistant:m819', 'assistant:m82', 'assistant:m820', "
                    "'assistant:m821', 'assistant:m822', 'assistant:m823', "
                    "'assistant:m824', 'assistant:m825', 'assistant:m826', "
                    "'assistant:m827', 'assistant:m828', 'assistant:m829', "
                    "'assistant:m83', 'assistant:m830', 'assistant:m831', "
                    "'assistant:m832', 'assistant:m833', 'assistant:m834', "
                    "'assistant:m835', 'assistant:m836', 'assistant:m837', "
                    "'assistant:m838', 'assistant:m839', 'assistant:m84', "
                    "'assistant:m840', 'assistant:m841', 'assistant:m842', "
                    "'assistant:m843', 'assistant:m844', 'assistant:m845', "
                    "'assistant:m846', 'assistant:m847', 'assistant:m848', "
                    "'assistant:m849', 'assistant:m85', 'assistant:m850', "
                    "'assistant:m851', 'assistant:m852', 'assistant:m853', "
                    "'assistant:m854', 'assistant:m855', 'assistant:m856', "
                    "'assistant:m857', 'assistant:m858', 'assistant:m859', "
                    "'assistant:m86', 'assistant:m860', 'assistant:m861', "
                    "'assistant:m862', 'assistant:m863', 'assistant:m864', "
                    "'assistant:m865', 'assistant:m866', 'assistant:m867', "
                    "'assistant:m868', 'assistant:m869', 'assistant:m87', "
                    "'assistant:m870', 'assistant:m871', 'assistant:m872', "
                    "'assistant:m873', 'assistant:m874', 'assistant:m875', "
                    "'assistant:m876', 'assistant:m877', 'assistant:m878', "
                    "'assistant:m879', 'assistant:m88', 'assistant:m880', "
                    "'assistant:m881', 'assistant:m882', 'assistant:m883', "
                    "'assistant:m884', 'assistant:m885', 'assistant:m886', "
                    "'assistant:m887', 'assistant:m888', 'assistant:m889', "
                    "'assistant:m89', 'assistant:m890', 'assistant:m891', "
                    "'assistant:m892', 'assistant:m893', 'assistant:m894', "
                    "'assistant:m895', 'assistant:m896', 'assistant:m897', "
                    "'assistant:m898', 'assistant:m899', 'assistant:m9', "
                    "'assistant:m90', 'assistant:m900', 'assistant:m901', "
                    "'assistant:m902', 'assistant:m903', 'assistant:m904', "
                    "'assistant:m905', 'assistant:m906', 'assistant:m907', "
                    "'assistant:m908', 'assistant:m909', 'assistant:m91', "
                    "'assistant:m910', 'assistant:m911', 'assistant:m912', "
                    "'assistant:m913', 'assistant:m914', 'assistant:m915', "
                    "'assistant:m916', 'assistant:m917', 'assistant:m918', "
                    "'assistant:m919', 'assistant:m92', 'assistant:m920', "
                    "'assistant:m921', 'assistant:m922', 'assistant:m923', "
                    "'assistant:m924', 'assistant:m925', 'assistant:m926', "
                    "'assistant:m927', 'assistant:m928', 'assistant:m929', "
                    "'assistant:m93', 'assistant:m930', 'assistant:m931', "
                    "'assistant:m932', 'assistant:m933', 'assistant:m934', "
                    "'assistant:m935', 'assistant:m936', 'assistant:m937', "
                    "'assistant:m938', 'assistant:m939', 'assistant:m94', "
                    "'assistant:m940', 'assistant:m941', 'assistant:m942', "
                    "'assistant:m943', 'assistant:m944', 'assistant:m945', "
                    "'assistant:m946', 'assistant:m947', 'assistant:m948', "
                    "'assistant:m949', 'assistant:m95', 'assistant:m950', "
                    "'assistant:m951', 'assistant:m952', 'assistant:m953', "
                    "'assistant:m954', 'assistant:m955', 'assistant:m956', "
                    "'assistant:m957', 'assistant:m958', 'assistant:m959', "
                    "'assistant:m96', 'assistant:m960', 'assistant:m961', "
                    "'assistant:m962', 'assistant:m963', 'assistant:m964', "
                    "'assistant:m965', 'assistant:m966', 'assistant:m967', "
                    "'assistant:m968', 'assistant:m969', 'assistant:m97', "
                    "'assistant:m970', 'assistant:m971', 'assistant:m972', "
                    "'assistant:m973', 'assistant:m974', 'assistant:m975', "
                    "'assistant:m976', 'assistant:m977', 'assistant:m978', "
                    "'assistant:m979', 'assistant:m98', 'assistant:m980', "
                    "'assistant:m981', 'assistant:m982', 'assistant:m983', "
                    "'assistant:m984', 'assistant:m985', 'assistant:m986', "
                    "'assistant:m987', 'assistant:m988', 'assistant:m989', "
                    "'assistant:m99', 'assistant:m990', 'assistant:m991', "
                    "'assistant:m992', 'assistant:m993', 'assistant:m994', "
                    "'assistant:m995', 'assistant:m996', 'assistant:m997', "
                    "'assistant:m998', 'tool:<81:2979c23e>', 'user:first']",
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<80:5954e770>"],
            ],
            [
                "history_0_1001",
                ["ok", "56a8bc861f10cfa7d428471e1bfeebae9c4c67b67e834a98456579a126895104", 95050],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(s1)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(s1,after_id=0,limit=1001)",
                    "release",
                ],
                [],
                ["<80:5954e770>"],
            ],
        ],
        "session_256": [
            [
                "snapshot_100",
                ["ok", "1c4588148b5e46576880e856fa29a772b42625ed217b1ea1f0fb295f78fe54af", 9878],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.resolve_resume_session_id(<256:02d7160d>)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.get_active_message_ids(<256:02d7160d>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(<256:02d7160d>)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.get_messages(<256:02d7160d>,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": "
                    'false, "error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<585:7a10da83>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.resolve_resume_session_id(<256:02d7160d>)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.get_active_message_ids(<256:02d7160d>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(<256:02d7160d>)",
                    "alpha.get_compression_chain(<256:02d7160d>)",
                    "alpha.get_messages(<256:02d7160d>,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<585:7a10da83>"],
            ],
        ],
        "session_257": [
            [
                "snapshot_100",
                ["ok", "44d2c70f40522da62425bed650d24a572bb59e4ac8269fc8e50fe87aa66a42c9", 9879],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.resolve_resume_session_id(<257:e8d95cc2>)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.get_active_message_ids(<257:e8d95cc2>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(<257:e8d95cc2>)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.get_messages(<257:e8d95cc2>,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": "
                    'false, "error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<587:88decbed>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.resolve_resume_session_id(<257:e8d95cc2>)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.get_active_message_ids(<257:e8d95cc2>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(<257:e8d95cc2>)",
                    "alpha.get_compression_chain(<257:e8d95cc2>)",
                    "alpha.get_messages(<257:e8d95cc2>,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<587:88decbed>"],
            ],
        ],
        "tip_256": [
            [
                "snapshot_100",
                ["ok", "79ffb2e8f4f0c095a0261614d2e469fea1688b086cb316396a21c673abd71dfc", 9878],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(<256:207f4a3c>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(<256:207f4a3c>,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": false, "
                    '"error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<331:16c36d93>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(<256:207f4a3c>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(<256:207f4a3c>,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<331:16c36d93>"],
            ],
        ],
        "tip_300": [
            [
                "snapshot_100",
                ["ok", "eef1fc7e72c28194c5082738269778567368ecf793a3098e529ceb89cf454b59", 9922],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(<300:0afa5eb0>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(<300:0afa5eb0>,latest=True,limit=100)",
                    "release",
                ],
                [
                    "purge 1900000000",
                    "discard alpha ['assistant:<47:767ddf1b>', 'assistant:done', "
                    "'tool:<4000:7ccedf2d>', 'tool:<78:410a9e1c>', "
                    "'tool:<81:5e3cd78b>', 'tool:ok', 'tool:{\"success\": false, "
                    '"error": "nope"}\', \'user:hello\']',
                    "purge 1900000000",
                    "list_visible <52:b5abd8de> aaaa alpha 1900000000",
                ],
                ["<375:3aa0b966>"],
            ],
            [
                "history_0_100",
                ["ok", "761ac14912635392b954f087a369fa9d38cdec9c6cfd48341f4c09e829e68862", 9430],
                [
                    "authz",
                    "routed_home(alpha)",
                    "authz",
                    "authz",
                    "lookup_session",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_active_message_ids(<300:0afa5eb0>)",
                    "release",
                    "routed_home(alpha)",
                    "acquire(<T>/w/homes/alpha/state.db)",
                    "alpha.resolve_resume_session_id(s1)",
                    "alpha.get_compression_chain(s1)",
                    "alpha.get_messages(<300:0afa5eb0>,after_id=0,limit=100)",
                    "release",
                ],
                [],
                ["<375:3aa0b966>"],
            ],
        ],
    },
}
