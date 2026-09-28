"""Fake Hermes objects for the read-bridge, reads and authorize unit tests (T028-T030).

They model only what `bridge.py` reaches (`bridge.REACHED_METHODS`, `bridge.HermesApi`), with the
semantics read from the reviewed builds:
- `runner.served_profile_names()`;
- `runner._routed_profile_home(p)`, which returns a sentinel object for an unresolvable profile;
- `runner._is_user_authorized_for_source(source)`, which reads the pairing grants of
  `source.profile` and any allow-all in the current scope;
- `adapter.build_source(...)`, which stamps `profile` from the configured `guild_id` route;
- `session_store.lookup_by_session_key`;
- `SessionDB.get_messages`, `get_active_message_ids`, `resolve_resume_session_id`, and
  `get_compression_chain`, all with Hermes's `active` flag and keyset paging.

Every value is synthetic. Nothing here touches a real Hermes home.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

UNRESOLVED = object()  # stands in for `gateway.run_adapters.UNRESOLVED_PROFILE_HOME`


class FakeSessionDB:
    """Messages keyed by session: each row `{id, session_id, role, content, timestamp,
    platform_message_id, active}`. Row ids are global and increasing, as in SQLite.

    Amendment A1 (session browsing): `sessions` adds a separate `sessions` table (a session can
    exist, and be listed, with zero messages), seeded with `seed_session`. `list_sessions_rich`/
    `get_session` model the real `hermes_state_sessions.py` semantics this amendment relies on
    (§1.1/§1.3 of the design doc, independently re-verified against `~/.hermes/hermes-agent/
    hermes_state_sessions.py` for this fake): `exclude_children` (always on for A1) hides any
    session that is itself a compression continuation (a value in `self.children`), and
    `_project_compression_tips` then overwrites a compression ROOT's surfaced `id`/`title`/
    `message_count`/`last_active` with its live tip's -- "one row per lineage"."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.next_id = 1
        self.children: dict[str, str] = {}  # compression continuation: parent -> child
        self.calls: list[str] = []
        self.fail = False
        # Review round 3: when set, `get_compression_lineage` returns only `[session_id]`, the
        # shape Hermes returns when its forward spine omits the start id.
        self.lineage_returns_self_only = False
        self.sessions: dict[str, dict[str, Any]] = {}  # A1: session_id -> `sessions` row metadata

    # -- seeding (test side) -------------------------------------------------------------------

    def append(
        self,
        session_id: str,
        role: str,
        content: Any,
        *,
        pmid: str | None = None,
        timestamp: float = 1_900_000_000.5,
        tool_calls: Any = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> int:
        row_id = self.next_id
        self.next_id += 1
        self.rows.append(
            {
                "id": row_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "platform_message_id": pmid,
                "active": 1,
                # Hermes `messages` columns. `get_messages` returns `tool_calls` already decoded
                # (a list) or, if a caller hands the column through, the stored JSON string.
                "tool_calls": tool_calls,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
            }
        )
        return row_id

    def compact_in_place(self, session_id: str, keep: int) -> None:
        """Hermes's default compaction: archive every active row, re-insert the last `keep`
        with fresh ids (RO-8)."""
        active = [r for r in self.rows if r["session_id"] == session_id and r["active"] == 1]
        for r in active:
            r["active"] = 0
        for r in active[-keep:] if keep else []:
            self.append(
                session_id,
                r["role"],
                r["content"],
                pmid=r["platform_message_id"],
                tool_calls=r.get("tool_calls"),
                tool_name=r.get("tool_name"),
                tool_call_id=r.get("tool_call_id"),
            )

    # -- the reached API -----------------------------------------------------------------------

    def _check(self, name: str) -> None:
        self.calls.append(name)
        if self.fail:
            raise OSError("database is locked")

    def get_messages(
        self,
        session_id: str,
        include_inactive: bool = False,
        include_compacted: bool = False,
        limit: int | None = None,
        offset: int = 0,
        latest: bool = False,
        after_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._check("get_messages")
        assert not include_compacted and not offset
        if after_id is not None and latest:
            raise ValueError("after_id is incompatible with latest")
        rows = [
            dict(r)
            for r in self.rows
            if r["session_id"] == session_id
            and (include_inactive or r["active"] == 1)
            and (after_id is None or r["id"] > after_id)
        ]
        if latest:
            rows = rows[-limit:] if limit else rows
        elif limit is not None:
            rows = rows[:limit]
        return rows

    def get_active_message_ids(self, session_id: str) -> list[int]:
        self._check("get_active_message_ids")
        return [r["id"] for r in self.rows if r["session_id"] == session_id and r["active"] == 1]

    def get_compression_chain(self, session_id: str) -> list[str]:
        self._check("get_compression_chain")
        chain = [session_id]
        while chain[-1] in self.children:
            chain.append(self.children[chain[-1]])
        return chain

    def get_compression_lineage(self, session_id: str) -> list[str]:
        """Amendment F2, review round 2 BLOCKER #2: models the real `SessionDB.
        get_compression_lineage` -- walk BACKWARD via the reverse of `self.children` (parent ->
        child) to the true root, then forward via `get_compression_chain`, regardless of which id
        in the lineage `session_id` itself is."""
        self._check("get_compression_lineage")
        if self.lineage_returns_self_only:
            return [session_id]
        reverse = {child: parent for parent, child in self.children.items()}
        root = session_id
        seen = {root}
        while root in reverse and reverse[root] not in seen:
            root = reverse[root]
            seen.add(root)
        return self.get_compression_chain(root)

    def resolve_resume_session_id(self, session_id: str) -> str:
        self._check("resolve_resume_session_id")
        return self.get_compression_chain(session_id)[-1]

    # -- A1: session browsing (list_sessions_rich, get_session) --------------------------------

    def seed_session(
        self,
        session_id: str,
        *,
        source: str = "cli",
        title: str | None = None,
        started_at: float = 1_900_000_000.0,
        archived: bool = False,
        hidden: bool = False,
        parent_session_id: str | None = None,
        end_reason: str | None = None,
    ) -> None:
        """A1 test seeding: a `sessions` row, independent of any message rows.

        `parent_session_id` is the column `SessionDB.get_session` returns and the round-3
        lineage walk reads. `end_reason` is stored for tests that model a compression parent."""
        self.sessions[session_id] = {
            "id": session_id,
            "source": source,
            "title": title,
            "started_at": started_at,
            "archived": archived,
            "hidden": hidden,
            "parent_session_id": parent_session_id,
            "end_reason": end_reason,
        }

    def _own_message_count(self, session_id: str) -> int:
        return sum(1 for r in self.rows if r["session_id"] == session_id and r["active"] == 1)

    def _own_last_active(self, session_id: str) -> float:
        active = [r for r in self.rows if r["session_id"] == session_id and r["active"] == 1]
        if not active:
            return self.sessions[session_id]["started_at"]
        return max(r["timestamp"] for r in active)

    def _chain_from(self, root: str) -> list[str]:
        chain = [root]
        while chain[-1] in self.children:
            chain.append(self.children[chain[-1]])
        return chain

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        self._check("get_session")
        meta = self.sessions.get(session_id)
        return dict(meta) if meta is not None else None

    def get_session_by_title(self, title: str) -> dict[str, Any] | None:
        """Amendment F2 (direct send, DS-4(2)): models `hermes_state_titles.py`'s exact-title
        lookup. Only ever the FIRST match by insertion order, mirroring the real "one row per
        title" invariant (Hermes enforces `UNIQUE(title)` on non-null titles)."""
        self._check("get_session_by_title")
        for _sid, meta in self.sessions.items():
            if meta.get("title") == title:
                return dict(meta)
        return None

    def list_sessions_rich(
        self,
        source: str | None = None,
        sources: list[str] | None = None,
        exclude_sources: list[str] | None = None,
        cwd_prefix: str | None = None,
        limit: int = 20,
        offset: int = 0,
        include_children: bool = False,
        min_message_count: int = 0,
        project_compression_tips: bool = True,
        order_by_last_active: bool = False,
        include_archived: bool = False,
        archived_only: bool = False,
        id_query: str | None = None,
        search_query: str | None = None,
        compact_rows: bool = False,
        include_pinned: bool = False,
        session_key: str | None = None,
        include_hidden: bool = False,
    ) -> list[dict[str, Any]]:
        self._check("list_sessions_rich")
        continuations = set(self.children.values())
        roots = []
        for sid, meta in self.sessions.items():
            if not include_children and sid in continuations:
                continue
            if archived_only:
                if not meta["archived"]:
                    continue
            elif not include_archived and meta["archived"]:
                continue
            if not include_hidden and not archived_only and meta["hidden"]:
                continue
            if source is not None and meta["source"] != source:
                continue
            if sources is not None and meta["source"] not in sources:
                continue
            if exclude_sources and meta["source"] in exclude_sources:
                continue
            roots.append(sid)

        def effective_last_active(sid: str) -> float:
            return max(self._own_last_active(s) for s in self._chain_from(sid))

        if order_by_last_active:
            roots.sort(key=effective_last_active, reverse=True)
        else:
            roots.sort(key=lambda s: self.sessions[s]["started_at"], reverse=True)
        page = roots[offset : offset + limit]

        out: list[dict[str, Any]] = []
        for sid in page:
            meta = self.sessions[sid]
            out.append(
                {
                    "id": sid,
                    "source": meta["source"],
                    "title": meta["title"],
                    "started_at": meta["started_at"],
                    "last_active": self._own_last_active(sid),
                    "message_count": self._own_message_count(sid),
                    "archived": int(meta["archived"]),
                    "hidden": int(meta["hidden"]),
                }
            )
        if project_compression_tips and not include_children:
            out = self._project_compression_tips(out)
        return out

    def _project_compression_tips(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        projected = []
        for s in sessions:
            chain = self._chain_from(s["id"])
            tip = chain[-1]
            if tip == s["id"]:
                projected.append(s)
                continue
            merged = dict(s)
            merged["id"] = tip
            tip_title = self.sessions[tip]["title"]
            merged["title"] = tip_title if tip_title is not None else s["title"]
            merged["message_count"] = self._own_message_count(tip)
            merged["last_active"] = self._own_last_active(tip)
            projected.append(merged)
        return projected


@dataclass
class FakeRunner:
    homes: dict[str, Any]  # profile -> home path (or UNRESOLVED)
    served: list[str] = field(default_factory=list)
    approved: dict[str, set[str]] = field(default_factory=dict)  # profile -> user ids
    allow_all_transport: bool = False
    allow_all_routed: set[str] = field(default_factory=set)
    authz_raises: bool = False
    authz_answer: Any = None  # when set, returned as is (e.g. a non-bool)
    scope: str | None = None  # the profile scope currently entered
    calls: list[str] = field(default_factory=list)

    def served_profile_names(self) -> list[str]:
        self.calls.append("served_profile_names")
        return list(self.served)

    def _routed_profile_home(self, profile: str) -> Any:
        self.calls.append("_routed_profile_home")
        return self.homes.get(profile, UNRESOLVED)

    def _is_user_authorized_for_source(self, source: Any) -> Any:
        self.calls.append("_is_user_authorized_for_source")
        if self.authz_raises:
            raise RuntimeError("pairing store unreadable")
        if self.authz_answer is not None:
            return self.authz_answer
        if self.allow_all_transport:
            return True
        if self.scope is not None and self.scope in self.allow_all_routed:
            return True
        return source.user_id in self.approved.get(source.profile, set())


@dataclass
class FakeSessionStore:
    entries: dict[str, Any] = field(default_factory=dict)

    def lookup_by_session_key(self, key: str) -> Any:
        return self.entries.get(key)

    def bind(self, key: str, session_id: str) -> None:
        self.entries[key] = SimpleNamespace(session_id=session_id)


class FakeAdapter:
    def __init__(self, runner: FakeRunner, routes: dict[str, str]) -> None:
        self.gateway_runner = runner
        self._session_store = FakeSessionStore()
        self.routes = routes  # guild_id -> profile (`gateway.profile_routes`)
        self.handled: list[Any] = []
        self.sources: list[Any] = []
        # SR-6: when True, every built source carries `profile_route_rejected = True` (Hermes's
        # own ingress marker for a rejected/fallen-back route).
        self.route_rejected = False
        # SR-1: HMP's own `PlatformConfig.extra` (`platforms.hmp.extra`); `allow_from` is
        # instance-wide when non-empty.
        self.config = SimpleNamespace(extra={})

    def build_source(self, **kw: Any) -> Any:
        source = SimpleNamespace(
            **kw,
            profile=self.routes.get(kw.get("guild_id") or ""),
            profile_route_rejected=self.route_rejected,
        )
        self.sources.append(source)
        return source

    async def handle_message(self, event: Any) -> None:
        self.handled.append(event)


class FakeHermesApi:
    def __init__(self, runner: FakeRunner, db_by_home: dict[Path, FakeSessionDB]) -> None:
        self.runner = runner
        self.db_by_home = db_by_home
        self.env: dict[str, str] = {}
        self.capabilities: Any = None
        self.acquired = 0
        self.released = 0
        self.events: list[dict[str, Any]] = []
        # Amendment F2 (direct send): keyed by the profile home resolved at the time of the call
        # (via `profile_runtime_scope`'s `_scope`, which sets `runner.scope` to the profile name).
        # `leases_by_home` models `active_session_registry_snapshot`'s per-registry-home result;
        # `api_server_extra_by_profile`/`api_server_keys` model the profile-scoped config/secret
        # reads `direct_send_endpoint` makes inside that same scope.
        self.leases_by_home: dict[Path, list[dict[str, Any]] | None] = {}
        self.api_server_extra_by_profile: dict[str, dict[str, Any]] = {}
        self.api_server_keys: dict[str, str] = {}

    @contextlib.contextmanager
    def _scope(self, home: Path) -> Iterator[None]:
        previous = self.runner.scope
        self.runner.scope = next(p for p, h in self.runner.homes.items() if h == home)
        try:
            yield
        finally:
            self.runner.scope = previous

    def profile_runtime_scope(self, profile_home: Path) -> Any:
        return self._scope(Path(profile_home))

    @staticmethod
    def session_key(profile: str, chat_id: str) -> str:
        return f"agent:{profile}:hmp:dm:{chat_id}"

    def build_session_key(self, source: Any, profile: str | None) -> str:
        return self.session_key(profile or "main", source.chat_id)

    def acquire(self, db_path: Path) -> FakeSessionDB:
        self.acquired += 1
        return self.db_by_home[Path(db_path).parent]

    def release(self, db: Any) -> None:
        self.released += 1

    def platform_gate_env(self, name: str) -> str:
        return self.env.get(name, "")

    def capability_map(self) -> Any:
        return self.capabilities

    def active_session_registry_snapshot(self, registry_home: Path) -> list[dict[str, Any]] | None:
        """`None` here means the caller asked for a registry home the test never seeded a result
        for -- distinct from an intentionally-empty list (`[]`, "not busy")."""
        return self.leases_by_home.get(Path(registry_home))

    def api_server_extra(self) -> dict[str, Any]:
        """Reads the CURRENT scope's profile (set by `_scope`, ambient like the real
        `get_scoped_secret`/`load_gateway_config` this models)."""
        return dict(self.api_server_extra_by_profile.get(self.runner.scope or "", {}))

    def scoped_api_server_key(self) -> str:
        return self.api_server_keys.get(self.runner.scope or "", "")

    def inert_trigger_event(self, *, source: Any, user_id: str, user_name: str) -> Any:
        from hmp_plugin.bridge import INERT_TRIGGER_TEXT

        event = {
            "text": INERT_TRIGGER_TEXT,
            "source": source,
            "user_id": user_id,
            "user_name": user_name,
            "allow_gateway_control": False,
        }
        self.events.append(event)
        return SimpleNamespace(**event)


class FakeDirectory:
    def __init__(self) -> None:
        self.chats: dict[tuple[str, str], str] = {}
        self.labels: dict[str, str] = {}

    def chat_id(self, user_id: str, profile: str) -> str | None:
        return self.chats.get((user_id, profile))

    def operator_label(self, user_id: str) -> str | None:
        return self.labels.get(user_id)


@dataclass
class World:
    """One fake Hermes gateway: profiles `alpha` (routed), `beta` (routed) and `lonely` (served,
    not routed), each with its own home and `SessionDB`."""

    tmp: Path
    runner: FakeRunner = field(init=False)
    adapter: FakeAdapter = field(init=False)
    api: FakeHermesApi = field(init=False)
    dbs: dict[str, FakeSessionDB] = field(init=False)

    def __post_init__(self) -> None:
        homes: dict[str, Any] = {}
        self.dbs = {}
        db_by_home: dict[Path, FakeSessionDB] = {}
        for p in ("alpha", "beta", "lonely"):
            home = self.tmp / "homes" / p
            home.mkdir(parents=True, exist_ok=True)
            (home / "state.db").write_bytes(b"")
            homes[p] = home
            self.dbs[p] = db_by_home[home] = FakeSessionDB()
        self.runner = FakeRunner(homes=homes, served=["alpha", "beta", "lonely"])
        self.adapter = FakeAdapter(self.runner, routes={"alpha": "alpha", "beta": "beta"})
        self.api = FakeHermesApi(self.runner, db_by_home)

    def approve(self, user_id: str, profile: str) -> None:
        self.runner.approved.setdefault(profile, set()).add(user_id)

    def start_conversation(self, profile: str, chat_id: str, session_id: str) -> None:
        """What a first admitted turn does: bind the session key to a session."""
        self.adapter._session_store.bind(FakeHermesApi.session_key(profile, chat_id), session_id)
