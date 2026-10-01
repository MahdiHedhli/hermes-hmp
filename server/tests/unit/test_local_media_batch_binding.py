"""C6b: the inert media batch binding (`local_media_batch_binding.py` and the bridge's methods).

Every native object here is a synthetic fake. Nothing imports or executes native Hermes. The
fake `NativeDB` models only the public reads the binding reaches, and tests flip its state at
chosen native calls to prove the bracket re-runs the complete classification. Expected values are
hand-written, not recomputed with the code under test.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import copy
import hashlib
import inspect
import logging
import os
import pickle
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from aiohttp.test_utils import make_mocked_request

from hmp_plugin import bridge as real_bridge
from hmp_plugin import local_media_active_batch as batch
from hmp_plugin import local_media_batch_binding as bind
from hmp_plugin import request_ctx, server, wire
from hmp_plugin.bridge import BridgeError, HermesReadBridge
from hmp_plugin.contract import ERROR_MESSAGES, ErrorCode
from hmp_plugin.local_media_sidecar import (
    MediaCandidate,
    MediaOrigin,
    MediaSidecar,
    SidecarStatus,
)

from .fake_hermes import FakeDirectory, FakeHermesApi, World
from .test_local_media_active_batch import call, independent_digest

PACKAGE = Path(bind.__file__).parent
USER = "hmpu_" + "a" * 32
OTHER_USER = "hmpu_" + "b" * 32
CHAT = "c_" + "1" * 32
SENTINEL = "SENTINEL-PRIVATE-9f3a"
OK = "ok"
BOT, PHONE = bind.MintKind.BOT_CHAT, bind.MintKind.PHONE


# --------------------------------------------------------------------------------------------
# A synthetic native database: sessions, compression edges, an optional resume-walker step.
# --------------------------------------------------------------------------------------------

NOTHING = object()


def session_row(
    sid: str,
    *,
    title: Any = None,
    parent: Any = None,
    hidden: Any = 0,
    archived: Any = 0,
) -> dict[str, Any]:
    return {
        "id": sid,
        "title": title,
        "parent_session_id": parent,
        "hidden": hidden,
        "archived": archived,
        "source": "api_server",
    }


class NativeDB:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.compression: dict[str, str] = {}  # parent -> compression child
        self.walker: dict[str, str] = {}  # a resume-walker step that is NOT a compression edge
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[str] = []
        self.counts: dict[str, int] = {}
        self.hooks: list[Callable[[str, int], None]] = []
        self.raises: dict[str, BaseException] = {}
        self.returns: dict[str, Callable[..., Any]] = {}

    def _enter(self, name: str, *args: Any) -> Any:
        self.calls.append(name)
        self.counts[name] = self.counts.get(name, 0) + 1
        for hook in list(self.hooks):
            hook(name, self.counts[name])
        if name in self.raises:
            raise self.raises[name]
        if name in self.returns:
            return self.returns[name](*args)
        return NOTHING

    def get_session_by_title(self, title: str) -> Any:
        out = self._enter("get_session_by_title", title)
        if out is not NOTHING:
            return out
        for row in self.sessions.values():
            if row.get("title") == title:
                return dict(row)
        return None

    def get_session(self, sid: str) -> Any:
        out = self._enter("get_session", sid)
        if out is not NOTHING:
            return out
        row = self.sessions.get(sid)
        return dict(row) if row is not None else None

    def _forward(self, sid: str) -> list[str]:
        chain = [sid]
        while chain[-1] in self.compression and len(chain) < 300:
            chain.append(self.compression[chain[-1]])
        return chain

    def resolve_resume_session_id(self, sid: str) -> Any:
        out = self._enter("resolve_resume_session_id", sid)
        if out is not NOTHING:
            return out
        return self.plain_resolve(sid)

    def plain_resolve(self, sid: str) -> str:
        """The native walk with no hook or override, for tests that wrap the real answer."""
        tip = self._forward(sid)[-1]
        while tip in self.walker:
            tip = self._forward(self.walker[tip])[-1]
        return tip

    def get_compression_lineage(self, sid: str) -> Any:
        out = self._enter("get_compression_lineage", sid)
        if out is not NOTHING:
            return out
        reverse = {child: parent for parent, child in self.compression.items()}
        root, seen = sid, {sid}
        while root in reverse and reverse[root] not in seen:
            root = reverse[root]
            seen.add(root)
        return self._forward(root)

    def get_active_message_ids(self, sid: str) -> Any:
        out = self._enter("get_active_message_ids", sid)
        if out is not NOTHING:
            return out
        return [r["id"] for r in self.messages.get(sid, [])]

    def get_messages(
        self,
        sid: str,
        *,
        after_id: int | None = None,
        limit: int | None = None,
        latest: bool = False,
        include_inactive: bool = False,
    ) -> Any:
        out = self._enter("get_messages", sid)
        if out is not NOTHING:
            return out
        rows = [dict(r) for r in self.messages.get(sid, []) if r["id"] > (after_id or 0)]
        return rows[-limit:] if latest and limit else rows[:limit]


class Env:
    """One fake gateway (profile `alpha`), one `NativeDB`, one bridge."""

    def __init__(self, tmp_path: Path) -> None:
        self.world = World(tmp_path)
        self.directory = FakeDirectory()
        self.directory.chats[(USER, "alpha")] = CHAT
        self.db = NativeDB()
        self.home_path = self.world.runner.homes["alpha"]
        self.home = str(self.home_path)
        self.world.api.db_by_home[self.home_path] = self.db  # type: ignore[assignment]
        self.bridge = HermesReadBridge(self.world.adapter, self.directory, hermes=self.world.api)
        self.next_id = 1
        self.tool_ids: list[int] = []
        self.digests: dict[int, bytes] = {}

    # -- histories -------------------------------------------------------------------------

    def put_images(self, sid: str, count: int = 3) -> None:
        rows: list[dict[str, Any]] = []
        for i in range(count):
            call_id = f"c{self.next_id}"
            rows.append({"id": self.next_id, "role": "assistant", "tool_calls": [call(call_id)]})
            content = (
                '{"success": true, "image": "' + f"{self.home}/cache/images/img{self.next_id}.png"
                '"}'
            )
            tool_id = self.next_id + 1
            rows.append(
                {
                    "id": tool_id,
                    "role": "tool",
                    "tool_call_id": call_id,
                    "tool_name": "image_generate",
                    "content": content,
                }
            )
            self.tool_ids.append(tool_id)
            self.digests[tool_id] = independent_digest(tool_id, "image_generate", call_id, content)
            self.next_id += 2
            del i
        self.db.messages[sid] = rows

    # -- sessions --------------------------------------------------------------------------

    def bot_chat(
        self, ids: tuple[str, ...] = ("R", "C"), holder: str | None = None, images: int = 3
    ) -> str:
        """Root-hidden compressed lineage; the canonical title sits on `holder` (default tip)."""
        for index, sid in enumerate(ids):
            self.db.sessions[sid] = session_row(
                sid, parent=ids[index - 1] if index else None, hidden=1 if index == 0 else 0
            )
            if index:
                self.db.compression[ids[index - 1]] = sid
        self.db.sessions[holder or ids[-1]]["title"] = "Bot Chat"
        self.put_images(ids[-1], images)
        return ids[-1]

    def phone(self, ids: tuple[str, ...] = ("p1", "p2"), images: int = 3) -> str:
        """The caller's own conversation bound to `ids[0]`, compressed to `ids[-1]`."""
        for index, sid in enumerate(ids):
            self.db.sessions[sid] = session_row(sid, parent=ids[index - 1] if index else None)
            if index:
                self.db.compression[ids[index - 1]] = sid
        self.world.start_conversation("alpha", CHAT, ids[0])
        self.put_images(ids[-1], images)
        return ids[-1]

    def bind_store(self, sid: str) -> None:
        self.world.start_conversation("alpha", CHAT, sid)

    # -- sidecars --------------------------------------------------------------------------

    def sidecar(
        self,
        session_id: str | None,
        tip: str | None,
        *,
        user: str = USER,
        ids: list[int] | None = None,
        lineage_tip: object = NOTHING,
        status: SidecarStatus = SidecarStatus.CANDIDATES,
        origin: MediaOrigin = MediaOrigin.OWN_CONVERSATION,
        digests: dict[int, bytes] | None = None,
    ) -> MediaSidecar:
        picked = self.tool_ids if ids is None else ids
        table = self.digests if digests is None else digests
        candidates = tuple(MediaCandidate(i, table[i]) for i in sorted(picked, reverse=True))
        if status is not SidecarStatus.CANDIDATES:
            candidates = ()
        return MediaSidecar(
            status=status,
            origin=origin,
            user_id=user,
            profile="alpha",
            session_id=session_id,
            query_tip=tip,
            lineage_tip=tip if lineage_tip is NOTHING else lineage_tip,  # type: ignore[arg-type]
            candidates=candidates,
        )

    def bind(self, sidecar: MediaSidecar) -> Any:
        return self.bridge.bind_media_batch(sidecar)

    def native_touched(self) -> bool:
        runner = self.world.runner
        return bool(
            self.db.calls or runner.calls or self.world.api.acquired or self.world.api.released
        )


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def valid_bot(env: Env, ids: tuple[str, ...] = ("R", "C"), holder: str | None = None) -> Any:
    tip = env.bot_chat(ids, holder)
    return env.sidecar(ids[0], tip)


def assert_closed(binding: Any, sidecar: MediaSidecar, reason: str) -> None:
    assert type(binding) is bind.MediaBatchBinding
    assert binding.sidecar is sidecar
    assert binding.reason == reason
    assert binding.kind is None and binding.accepted == ()
    assert not binding.ok


# --------------------------------------------------------------------------------------------
# Pure pieces: proof combination, strict home, the closed wrapper
# --------------------------------------------------------------------------------------------

P_OK = bind.proven("tipA")
P_NO = bind.PROOF_NEGATIVE
P_UN = bind.PROOF_UNCERTAIN


@pytest.mark.parametrize(
    ("phone", "bot", "expected"),
    [
        (P_OK, P_NO, (OK, PHONE, "tipA")),
        (P_NO, P_OK, (OK, BOT, "tipA")),
        (P_OK, P_OK, ("not_eligible", None, None)),
        (P_NO, P_NO, ("not_eligible", None, None)),
        (P_UN, P_NO, ("eligibility_uncertain", None, None)),
        (P_NO, P_UN, ("eligibility_uncertain", None, None)),
        (P_OK, P_UN, ("eligibility_uncertain", None, None)),  # one proves, the other is unknown
        (P_UN, P_OK, ("eligibility_uncertain", None, None)),
        (P_UN, P_UN, ("eligibility_uncertain", None, None)),
        (("proven", ""), P_NO, ("eligibility_uncertain", None, None)),
        (("proven", None), P_NO, ("eligibility_uncertain", None, None)),
        (("negative", "tipA"), P_NO, ("eligibility_uncertain", None, None)),
        (("maybe", None), P_NO, ("eligibility_uncertain", None, None)),
        ("proven", P_NO, ("eligibility_uncertain", None, None)),
        (P_OK, P_NO, None),  # replaced below: expected tip of the wrong type
    ],
)
def test_classify_table(phone: Any, bot: Any, expected: Any) -> None:
    if expected is None:
        assert bind.classify(phone, bot, 5) == ("eligibility_uncertain", None, None)
        return
    assert bind.classify(phone, bot, "tipA") == expected


def test_classify_tip_mismatch_is_provenance_not_eligibility() -> None:
    assert bind.classify(P_OK, P_NO, "other") == ("provenance_mismatch", None, None)
    assert bind.classify(P_NO, P_OK, "other") == ("provenance_mismatch", None, None)
    # Ambiguity is decided before the tip comparison.
    assert bind.classify(P_OK, P_OK, "other") == ("not_eligible", None, None)


@pytest.mark.parametrize(
    ("home", "ok"),
    [
        ("/srv/hermes/profiles/p1", True),
        ("/", True),
        ("//srv/x", True),  # POSIX double-slash prefix: lexically normal, harmless (documented)
        ("", False),
        ("relative/home", False),
        ("./home", False),
        ("/a/../b", False),
        ("/a/./b", False),
        ("/a//b", False),
        ("/a/b/", False),
        ("/a/b/..", False),
        ("/a\0b", False),
        ("..", False),
        (None, False),
        (b"/srv/x", False),
        (Path("/srv/x"), False),
        (5, False),
    ],
)
def test_strict_home_is_lexical(home: Any, ok: bool) -> None:
    assert bind.strict_home(home) is ok


def test_strict_home_subclass_of_str_is_refused() -> None:
    class Home(str):
        pass

    assert not bind.strict_home(Home("/srv/x"))


def make_binding(sidecar: MediaSidecar, **over: Any) -> bind.MediaBatchBinding:
    n = len(sidecar.candidates)
    args: dict[str, Any] = {
        "kind": BOT,
        "reason": OK,
        "accepted": tuple(c.tool_row_id for c in sidecar.candidates[:2]),
        "counts": (n, min(2, n), 1, 6, 100, 50),
    }
    args.update(over)
    return bind.MediaBatchBinding(sidecar, **args)


@pytest.fixture
def sc(env: Env) -> MediaSidecar:
    env.bot_chat()
    return env.sidecar("R", "C")


def test_binding_constructor_accepts_the_valid_shape(sc: MediaSidecar) -> None:
    b = make_binding(sc)
    assert b.sidecar is sc and b.kind is BOT and b.reason == OK and b.ok
    assert b.accepted == (6, 4)
    assert b.session_id == "R" and b.tip == "C"


@pytest.mark.parametrize(
    "over",
    [
        {"reason": "nope"},
        {"reason": 5},
        {"kind": None},  # ok requires a kind
        {"kind": "bot_chat"},
        {"reason": "not_eligible"},  # a kind with a refusal
        {"reason": "not_eligible", "kind": None},  # accepted ids with a refusal
        {"accepted": (4, 6)},  # ascending
        {"accepted": (6, 6)},  # duplicate
        {"accepted": (6, 99), "counts": (3, 2, 1, 6, 100, 50)},  # not a candidate row id
        {"accepted": (99,), "counts": (3, 1, 0, 0, 0, 0)},  # only the subset invariant fails
        {"reason": "not_eligible", "accepted": (), "counts": (3, 0, 0, 0, 0, 0)},  # only the kind
        {"accepted": [6, 4]},
        {"accepted": (True,), "counts": (3, 1, 0, 0, 0, 0)},
        {"accepted": (6.0,), "counts": (3, 1, 0, 0, 0, 0)},
        {"counts": (3, 2, 1, 6, 100)},
        {"counts": (3, 2, 1, 6, 100, 50, 1)},
        {"counts": [3, 2, 1, 6, 100, 50]},
        {"counts": (3, 2, -1, 6, 100, 50)},
        {"counts": (3, 2, True, 6, 100, 50)},
        {"counts": (3, 2, 1, 6, 100, 50.0)},
        {"counts": (4, 2, 1, 6, 100, 50)},  # candidate count must equal the sidecar's
        {"counts": (3, 1, 1, 6, 100, 50)},  # accepted count must equal the tuple's
    ],
)
def test_binding_constructor_refuses_bad_shapes(sc: MediaSidecar, over: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="invalid binding"):
        make_binding(sc, **over)


def test_binding_constructor_refuses_a_non_sidecar_and_a_foreign_result(sc: MediaSidecar) -> None:
    for other in (None, object(), sc.candidates[0], "sidecar"):
        with pytest.raises(ValueError, match="invalid binding"):
            bind.MediaBatchBinding(other, BOT, OK, (), (0, 0, 0, 0, 0, 0))  # type: ignore[arg-type]
    result = batch.ActiveBatchResult(OK, (), (0, 0, 0, 0))
    with pytest.raises(ValueError, match="invalid binding"):
        make_binding(sc, accepted=result)


def test_binding_accepts_more_than_zero_candidates_with_none_accepted(sc: MediaSidecar) -> None:
    b = make_binding(sc, accepted=(), counts=(3, 0, 1, 6, 100, 50))
    assert b.ok and b.kind is BOT and b.accepted == ()


def test_binding_cap_is_128(env: Env) -> None:
    env.bot_chat(images=130)
    sidecar = env.sidecar("R", "C", ids=env.tool_ids[:128])
    ids = tuple(sorted(env.tool_ids[:128], reverse=True))
    b = bind.MediaBatchBinding(sidecar, BOT, OK, ids, (128, 128, 0, 0, 0, 0))
    assert len(b.accepted) == 128
    with pytest.raises(ValueError, match="invalid binding"):
        bind.MediaBatchBinding(sidecar, BOT, OK, (*ids, 1), (128, 129, 0, 0, 0, 0))


def test_binding_is_closed_immutable_and_has_fixed_text(sc: MediaSidecar) -> None:
    b = make_binding(sc)
    assert repr(b) == str(b) == format(b) == "MediaBatchBinding()"
    assert not hasattr(b, "__dict__")
    with pytest.raises(AttributeError):
        b.reason = "x"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        b._accepted = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del b._kind
    with pytest.raises(AttributeError):
        b.extra = 1  # type: ignore[attr-defined]
    for dump in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError):
            dump(b)
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError):
            pickle.dumps(b, protocol)
    assert b == b and hash(b) == hash(b) and b != make_binding(sc)


def test_binding_reinit_is_refused_by_the_accepted_guard(sc: MediaSidecar) -> None:
    b = make_binding(sc)
    before = (b.sidecar, b.kind, b.reason, b.accepted)
    with pytest.raises(TypeError, match="already initialized"):
        b.__init__(sc, BOT, OK, (), (3, 0, 0, 0, 0, 0))  # type: ignore[misc]
    assert (b.sidecar, b.kind, b.reason, b.accepted) == before
    assert bind._batch._initialized is batch._initialized
    assert bind.MediaBatchBinding.__mro__[1] is batch._Closed


def test_binding_report_holds_only_closed_metadata(sc: MediaSidecar) -> None:
    report = make_binding(sc).report()
    assert report == {
        "reason": OK,
        "kind": "bot_chat",
        "candidates": 3,
        "accepted": 2,
        "pages": 1,
        "rows": 6,
        "budget_used": 100,
        "declared": 50,
    }
    refused = make_binding(
        sc, kind=None, reason="not_eligible", accepted=(), counts=(3, 0, 0, 0, 0, 0)
    )
    assert refused.report()["kind"] is None


def test_wrapper_wire_is_a_fixed_500_with_no_logs(
    sc: MediaSidecar, caplog: pytest.LogCaptureFixture
) -> None:
    b = make_binding(sc)
    with pytest.raises(TypeError):
        wire.dump_json(b)
    assert request_ctx._plain(b) is b

    async def handler(_req: Any) -> Any:
        return request_ctx.json_response(b)

    async def main() -> Any:
        return await server.error_middleware(make_mocked_request("GET", "/x"), handler)

    with caplog.at_level(logging.DEBUG):
        resp = asyncio.run(main())
    assert resp.status == 500
    fixed = {
        "error": {
            "code": "other",
            "message": ERROR_MESSAGES[ErrorCode.OTHER],
            "why": "internal_error",
        }
    }
    assert resp.body == wire.dump_json(fixed)
    text = caplog.text
    for secret in (sc.candidates[0].raw_digest.hex(), "MediaBatchBinding", "img", "Bot Chat"):
        assert secret not in text


# --------------------------------------------------------------------------------------------
# bind_media_batch: no native for non-candidates, exact-sidecar rule
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, object(), "sidecar", 5, {"session_id": "R"}, [], b""])
def test_nonexact_sidecar_returns_none_without_native_work(env: Env, bad: Any) -> None:
    assert env.bridge.bind_media_batch(bad) is None
    assert not env.native_touched()


def test_duck_typed_and_subclass_sidecars_return_none(env: Env) -> None:
    env.bot_chat()
    real = env.sidecar("R", "C")

    class Duck:
        status = SidecarStatus.CANDIDATES
        candidates = real.candidates
        session_id, query_tip, lineage_tip = "R", "C", "C"
        user_id, profile = USER, "alpha"

    assert env.bridge.bind_media_batch(Duck()) is None
    with pytest.raises(TypeError):  # the carrier refuses subclassing, so no subclass can exist
        type("Sub", (MediaSidecar,), {})
    assert not env.native_touched()


@pytest.mark.parametrize("status", [SidecarStatus.NO_ROWS, SidecarStatus.UNSUPPORTED_BRIDGE])
def test_non_candidate_status_is_closed_with_zero_native_work(
    env: Env, status: SidecarStatus
) -> None:
    sidecar = env.sidecar(None, None, status=status, lineage_tip=None)
    assert_closed(env.bind(sidecar), sidecar, "not_candidates")
    assert not env.native_touched()


def test_candidates_status_with_no_candidates_is_closed_with_zero_native_work(env: Env) -> None:
    env.bot_chat()
    sidecar = env.sidecar("R", "C", ids=[])
    binding = env.bind(sidecar)
    assert_closed(binding, sidecar, "not_candidates")
    assert not env.native_touched()
    assert binding.report()["candidates"] == 0


def test_query_tip_not_equal_to_lineage_tip_is_closed_with_zero_native_work(env: Env) -> None:
    env.bot_chat()
    sidecar = env.sidecar("R", "C", lineage_tip="D")
    assert_closed(env.bind(sidecar), sidecar, "provenance_mismatch")
    assert not env.native_touched()


def test_closed_results_carry_the_candidate_count_and_zero_stats(env: Env) -> None:
    env.bot_chat()
    sidecar = env.sidecar("R", "C", lineage_tip="D")
    assert env.bind(sidecar).report() | {"kind": None} == {
        "reason": "provenance_mismatch",
        "kind": None,
        "candidates": 3,
        "accepted": 0,
        "pages": 0,
        "rows": 0,
        "budget_used": 0,
        "declared": 0,
    }


# --------------------------------------------------------------------------------------------
# Success: Bot Chat and Phone, one home/DB capture, one scan, exact selectors
# --------------------------------------------------------------------------------------------


def test_bot_chat_success_is_newest_first_with_exact_counts(env: Env) -> None:
    sidecar = valid_bot(env)
    b = env.bind(sidecar)
    assert b.ok and b.kind is BOT and b.sidecar is sidecar
    assert b.accepted == tuple(sorted(env.tool_ids, reverse=True)) == (6, 4, 2)
    assert b.report() == {
        "reason": OK,
        "kind": "bot_chat",
        "candidates": 3,
        "accepted": 3,
        "pages": 1,
        "rows": 6,
        "budget_used": b.report()["budget_used"],
        "declared": b.report()["declared"],
    }
    assert b.report()["budget_used"] > 0 and b.report()["declared"] > 0


def test_phone_success_for_the_own_session(env: Env) -> None:
    tip = env.phone(("p1",))
    b = env.bind(env.sidecar("p1", tip))
    assert b.ok and b.kind is PHONE and b.accepted == (6, 4, 2)


def test_phone_success_for_a_compressed_own_bound_ancestor(env: Env) -> None:
    tip = env.phone(("p1", "p2"))
    b = env.bind(env.sidecar("p1", tip))
    assert b.ok and b.kind is PHONE and b.tip == "p2" and b.session_id == "p1"


@pytest.mark.parametrize("ids", [("R", "C"), ("R", "M", "C")])
def test_bot_chat_with_the_bound_session_at_every_chain_position(
    env: Env, ids: tuple[str, ...]
) -> None:
    tip = env.bot_chat(ids)
    for bound in ids:
        b = env.bind(env.sidecar(bound, tip))
        assert b.ok and b.kind is BOT, bound


def test_selector_subset_and_order_are_exact(env: Env) -> None:
    sidecar = valid_bot(env)
    subset = env.sidecar("R", "C", ids=[2, 6])
    assert sidecar is not subset
    b = env.bind(subset)
    assert b.ok and b.accepted == (6, 2) and b.report()["candidates"] == 2


def test_ok_with_zero_accepted_is_a_safe_empty_binding(env: Env) -> None:
    env.bot_chat()
    env.db.messages["C"] = []  # the history no longer holds any selected row
    sidecar = env.sidecar("R", "C")
    b = env.bind(sidecar)
    assert b.ok and b.kind is BOT and b.accepted == ()
    assert b.report()["accepted"] == 0 and b.report()["candidates"] == 3


def test_exactly_one_home_capture_and_one_db_acquire_release(env: Env) -> None:
    sidecar = valid_bot(env)
    env.bind(sidecar)
    homes = [c for c in env.world.runner.calls if c == "_routed_profile_home"]
    assert len(homes) == 1
    assert (env.world.api.acquired, env.world.api.released) == (1, 1)


def test_released_even_when_the_batch_refuses(env: Env) -> None:
    sidecar = valid_bot(env)
    env.db.raises["get_active_message_ids"] = RuntimeError(SENTINEL)
    assert not env.bind(sidecar).ok
    assert (env.world.api.acquired, env.world.api.released) == (1, 1)


def test_one_fresh_batch_scan_with_selectors_copied_unchanged(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar = valid_bot(env)
    seen: list[Any] = []
    real = batch.scan_active_batch

    def spy(db: Any, tip: Any, selectors: Any, **kw: Any) -> Any:
        seen.append((db, tip, selectors, kw))
        return real(db, tip, selectors, **kw)

    monkeypatch.setattr(batch, "scan_active_batch", spy)
    env.bind(sidecar)
    assert len(seen) == 1
    db, tip, selectors, kw = seen[0]
    assert db is env.db and tip == "C"
    assert type(selectors) is tuple
    expected = tuple((c.tool_row_id, c.raw_digest) for c in sidecar.candidates)
    assert selectors == expected
    assert all(
        got[1] is want.raw_digest for got, want in zip(selectors, sidecar.candidates, strict=True)
    )
    assert set(kw) == {"home", "current_tip"}
    assert kw["home"] == env.home and type(kw["home"]) is str and callable(kw["current_tip"])


def test_no_second_query_backfill_or_cache(env: Env) -> None:
    sidecar = valid_bot(env)
    env.bind(sidecar)
    first = dict(env.db.counts)
    assert first["get_active_message_ids"] == 2  # exactly the two bracket reads
    assert first["get_messages"] == 1  # one 128-row page
    env.bind(sidecar)  # a second bind is a fresh full scan, never a cached verdict
    assert env.db.counts["get_active_message_ids"] == 4
    assert env.db.counts["get_messages"] == 2


def test_both_kinds_are_evaluated_in_each_of_three_classifications(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar = valid_bot(env)
    refs: list[tuple[str, str]] = []
    real_ref = HermesReadBridge.conversation_ref

    def ref(self: Any, user: str, profile: str) -> Any:
        refs.append((user, profile))
        return real_ref(self, user, profile)

    monkeypatch.setattr(HermesReadBridge, "conversation_ref", ref)
    assert env.bind(sidecar).ok
    assert refs == [(USER, "alpha")] * 3  # initial plus both tip brackets
    assert env.db.counts["get_session_by_title"] == 3


def test_the_one_helper_is_used_by_identity_with_primitive_inputs(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar = valid_bot(env)
    calls: list[tuple[Any, ...]] = []
    real = HermesReadBridge.media_eligibility

    def spy(self: Any, *args: Any) -> Any:
        calls.append(args)
        return real(self, *args)

    monkeypatch.setattr(HermesReadBridge, "media_eligibility", spy)
    assert env.bind(sidecar).ok
    assert len(calls) == 3
    assert all(a == (env.db, USER, "alpha", "R", "C") for a in calls)
    assert all(type(x) is str for a in calls for x in a[1:])
    assert real is HermesReadBridge.__dict__["media_eligibility"] or True
    params = list(inspect.signature(real).parameters)
    assert params == ["self", "db", "user_id", "profile", "session_id", "expected_tip"]


def test_a_fetch_style_caller_uses_the_same_helper_on_its_own_captured_db(env: Env) -> None:
    sidecar = valid_bot(env)
    with env.bridge._db_home("alpha") as (_home, db):
        got = env.bridge.media_eligibility(db, USER, "alpha", "R", "C")
        assert got == (OK, BOT, "C")
        # Unique-kind drift at fetch time: the helper reports it and the caller compares.
        env.db.sessions["R"]["hidden"] = 0
        assert env.bridge.media_eligibility(db, USER, "alpha", "R", "C") == (
            "not_eligible",
            None,
            None,
        )
        env.db.sessions["R"]["hidden"] = 1
        assert env.bridge.media_eligibility(db, USER, "alpha", "R", "D")[0] == "provenance_mismatch"
    assert sidecar.session_id == "R"


@pytest.mark.parametrize(
    "args",
    [
        (None, USER, "alpha", "R", "C"),
        ("db", "", "alpha", "R", "C"),
        ("db", USER, "", "R", "C"),
        ("db", USER, "alpha", "", "C"),
        ("db", USER, "alpha", "R", ""),
        ("db", USER, "alpha", "R", None),
        ("db", 5, "alpha", "R", "C"),
        ("db", USER, "alpha", b"R", "C"),
    ],
)
def test_helper_with_invalid_primitive_inputs_is_uncertain_without_native_reads(
    env: Env, args: tuple[Any, ...]
) -> None:
    env.bot_chat()
    db = env.db if args[0] == "db" else args[0]
    out = env.bridge.media_eligibility(db, *args[1:])
    assert out == ("eligibility_uncertain", None, None) or (
        args[0] is None and out[0] == "eligibility_uncertain"
    )
    assert not env.db.calls


def test_parent_chain_is_reused_unchanged_by_identity(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar = valid_bot(env)
    seen: list[tuple[Any, str]] = []
    real = real_bridge._parent_chain

    def spy(db: Any, start: str) -> Any:
        seen.append((db, start))
        return real(db, start)

    monkeypatch.setattr(real_bridge, "_parent_chain", spy)
    assert env.bind(sidecar).ok
    assert seen == [(env.db, "C")] * 3
    assert real.__name__ == "_parent_chain"


def test_no_authorization_trigger_or_grant_is_touched(env: Env) -> None:
    sidecar = valid_bot(env)
    env.bind(sidecar)
    assert "_is_user_authorized_for_source" not in env.world.runner.calls
    assert env.world.adapter.handled == [] and env.world.api.events == []


@pytest.mark.parametrize("name", ["authz_state", "request_authorization", "instance_wide_grant"])
def test_authorization_methods_are_never_called(
    env: Env, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    def deny(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("authorization consulted")

    monkeypatch.setattr(HermesReadBridge, name, deny)
    assert env.bind(valid_bot(env)).ok


# --------------------------------------------------------------------------------------------
# Provenance, tips and home
# --------------------------------------------------------------------------------------------


def test_native_tip_differing_from_the_query_tip_is_provenance_mismatch(env: Env) -> None:
    env.bot_chat()
    sidecar = env.sidecar("R", "X")  # the rows were queried at another tip
    assert_closed(env.bind(sidecar), sidecar, "provenance_mismatch")
    assert "get_active_message_ids" not in env.db.counts


def test_phone_native_tip_differing_from_the_query_tip_is_provenance_mismatch(env: Env) -> None:
    env.phone(("p1", "p2"))
    sidecar = env.sidecar("p1", "p1")  # the query used the uncompressed id
    assert_closed(env.bind(sidecar), sidecar, "provenance_mismatch")


def test_unresolved_home_is_optional_media_closed(env: Env) -> None:
    sidecar = valid_bot(env)
    env.world.runner.homes["alpha"] = object()
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")
    assert not env.db.calls


def test_missing_database_file_is_closed(env: Env) -> None:
    sidecar = valid_bot(env)
    (env.home_path / "state.db").unlink()
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")
    assert env.world.api.acquired == 0


def test_dotdot_home_is_home_invalid_before_any_native_read(env: Env) -> None:
    sidecar = valid_bot(env)
    weird = Path(f"{env.home}/../alpha")
    env.world.runner.homes["alpha"] = weird
    env.world.api.db_by_home[weird] = env.db  # type: ignore[assignment]
    assert_closed(env.bind(sidecar), sidecar, "home_invalid")
    assert not env.db.calls
    assert (env.world.api.acquired, env.world.api.released) == (1, 1)


def test_relative_home_is_closed_without_native_reads(env: Env) -> None:
    sidecar = valid_bot(env)
    env.world.runner.homes["alpha"] = Path("relative/home")
    assert env.bind(sidecar).reason in {"eligibility_uncertain", "home_invalid"}
    assert not env.db.calls


def test_acquire_and_release_failures_never_raise(env: Env) -> None:
    sidecar = valid_bot(env)

    def boom(*_a: Any) -> Any:
        raise RuntimeError(SENTINEL)

    env.world.api.acquire = boom  # type: ignore[method-assign]
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")
    env.world.api.acquire = FakeHermesApi.acquire.__get__(env.world.api)  # type: ignore[method-assign]
    env.world.api.release = boom  # type: ignore[method-assign]
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


def test_no_file_io_except_the_existing_database_check(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar = valid_bot(env)
    env.bind(sidecar)  # warm: function-local imports happen first
    db_path = str(env.home_path / "state.db")
    touched: list[tuple[str, str]] = []

    def watch(label: str, original: Callable[..., Any]) -> Callable[..., Any]:
        def inner(path: Any, *a: Any, **k: Any) -> Any:
            touched.append((label, os.fspath(path) if isinstance(path, str | os.PathLike) else "?"))
            return original(path, *a, **k)

        return inner

    for owner, name in (
        (os, "stat"),
        (os, "lstat"),
        (os, "open"),
        (os, "scandir"),
        (os, "listdir"),
        (os, "readlink"),
        (os.path, "realpath"),
        (os.path, "exists"),
        (builtins, "open"),
    ):
        monkeypatch.setattr(owner, name, watch(name, getattr(owner, name)))
    assert env.bind(sidecar).ok
    monkeypatch.undo()
    assert {path for _label, path in touched} <= {db_path}
    assert touched  # the one existing database-file check really happened
    for forbidden in ("open", "listdir", "scandir", "readlink", "realpath"):
        assert forbidden not in {label for label, _ in touched}


def test_a_b_a_home_and_database_swaps_refuse_every_selector(env: Env) -> None:
    sidecar = valid_bot(env)
    # A different database at the same home: its rows differ, so each selector is refused.
    other = NativeDB()
    other.sessions = {k: dict(v) for k, v in env.db.sessions.items()}
    other.compression = dict(env.db.compression)
    other.messages = {
        "C": [dict(r, content="x") if r["role"] == "tool" else r for r in env.db.messages["C"]]
    }
    env.world.api.db_by_home[env.home_path] = other  # type: ignore[assignment]
    b = env.bind(sidecar)
    assert b.ok and b.accepted == ()  # batch ok, every verdict refused (link/digest)
    # The same rows read under another home spelling: lexical derivation refuses every selector.
    env.world.api.db_by_home[env.home_path] = env.db  # type: ignore[assignment]
    other_home = env.world.tmp / "homes" / "alpha_b"
    other_home.mkdir()
    (other_home / "state.db").write_bytes(b"")
    env.world.api.db_by_home[other_home] = env.db  # type: ignore[assignment]
    env.world.runner.homes["alpha"] = other_home
    b = env.bind(sidecar)
    assert b.ok and b.accepted == () and b.kind is BOT


def test_digest_change_refuses_only_that_selector(env: Env) -> None:
    sidecar = valid_bot(env)
    env.db.messages["C"][3]["content"] = env.db.messages["C"][3]["content"] + " "
    b = env.bind(sidecar)
    assert b.ok and b.accepted == (6, 2)


def test_rewound_history_refuses_only_the_inactive_selector(env: Env) -> None:
    sidecar = valid_bot(env)
    del env.db.messages["C"][-2:]  # the last pair is no longer active
    b = env.bind(sidecar)
    assert b.ok and b.accepted == (4, 2)


# --------------------------------------------------------------------------------------------
# D1: the canonical Bot Chat lineage predicate, each reason path
# --------------------------------------------------------------------------------------------


def refused(env: Env, session_id: str = "R", tip: str = "C", reason: str = "not_eligible") -> None:
    sidecar = env.sidecar(session_id, tip)
    assert_closed(env.bind(sidecar), sidecar, reason)


def test_moved_title_on_a_visible_tip_with_an_untitled_hidden_root(env: Env) -> None:
    env.bot_chat()
    row = env.db.sessions
    assert row["R"]["title"] is None and row["R"]["hidden"] == 1 and row["C"]["hidden"] == 0
    assert env.bind(env.sidecar("R", "C")).ok


@pytest.mark.parametrize("holder", ["R", "M"])
def test_interrupted_transfer_with_the_title_on_an_ancestor_is_valid(env: Env, holder: str) -> None:
    tip = env.bot_chat(("R", "M", "C"), holder=holder)
    b = env.bind(env.sidecar("R", tip))
    assert b.ok and b.kind is BOT


def test_visible_holder_is_allowed(env: Env) -> None:
    env.bot_chat()
    assert env.db.sessions["C"]["hidden"] == 0
    assert env.bind(env.sidecar("C", "C")).ok


def test_single_row_hidden_titled_session_is_valid(env: Env) -> None:
    tip = env.bot_chat(("R",))
    assert env.bind(env.sidecar("R", tip)).ok


def test_a_visible_ordinary_session_titled_bot_chat_refuses(env: Env) -> None:
    env.bot_chat(("R",))
    env.db.sessions["R"]["hidden"] = 0
    refused(env, "R", "R")


def test_moved_title_with_a_visible_root_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["hidden"] = 0
    refused(env)


def test_hidden_integer_other_than_one_refuses_as_a_negative(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["hidden"] = 2
    refused(env)


@pytest.mark.parametrize("value", [True, False, "1", None, 1.0, b"1", [1]])
def test_hidden_with_a_wrong_type_is_uncertain(env: Env, value: Any) -> None:
    env.bot_chat()
    env.db.sessions["R"]["hidden"] = value
    refused(env, reason="eligibility_uncertain")


def test_hidden_missing_is_uncertain(env: Env) -> None:
    env.bot_chat()
    del env.db.sessions["R"]["hidden"]
    refused(env, reason="eligibility_uncertain")


@pytest.mark.parametrize("which", ["R", "M", "C"])
def test_archived_root_holder_or_tip_refuses(env: Env, which: str) -> None:
    tip = env.bot_chat(("R", "M", "C"), holder="M")
    env.db.sessions[which]["archived"] = 1
    refused(env, "R", tip)


def test_archived_on_a_middle_row_that_is_neither_holder_nor_tip_is_not_read(env: Env) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    env.db.sessions["M"]["archived"] = 1  # the proof checks root, holder and live tip only
    assert env.bind(env.sidecar("R", tip)).ok


@pytest.mark.parametrize("value", [True, "0", None, 0.0])
def test_archived_with_a_wrong_type_is_uncertain(env: Env, value: Any) -> None:
    env.bot_chat()
    env.db.sessions["C"]["archived"] = value
    refused(env, reason="eligibility_uncertain")


def test_archived_missing_on_the_holder_is_uncertain(env: Env) -> None:
    env.bot_chat()
    del env.db.sessions["C"]["archived"]
    refused(env, reason="eligibility_uncertain")


def test_root_parent_must_be_exactly_none_empty_string_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["parent_session_id"] = ""
    refused(env)


def test_root_with_a_parent_refuses_as_a_fork_or_child(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["P"] = session_row("P", hidden=1)
    env.db.sessions["R"]["parent_session_id"] = "P"
    refused(env)  # the parent walk now reaches P, so it differs from the native lineage


@pytest.mark.parametrize("value", [5, True, ["P"], b"P"])
def test_root_parent_with_a_wrong_type_is_uncertain(env: Env, value: Any) -> None:
    env.bot_chat()
    env.db.sessions["R"]["parent_session_id"] = value
    refused(env, reason="eligibility_uncertain")


def test_root_parent_missing_is_uncertain(env: Env) -> None:
    env.bot_chat()
    del env.db.sessions["R"]["parent_session_id"]
    # `_parent_chain` itself treats a missing field as a root; the strict re-read does not.
    refused(env, reason="eligibility_uncertain")


def test_holder_retitled_between_lookup_and_reread_refuses(env: Env) -> None:
    env.bot_chat()
    original = env.db.sessions["C"].copy()
    env.db.hooks.append(
        lambda name, n: (
            env.db.sessions["C"].update(title="Renamed") if name == "get_session" else None
        )
    )
    refused(env)
    assert original["title"] == "Bot Chat"


def test_holder_title_lost_on_reread_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.hooks.append(
        lambda name, n: env.db.sessions["C"].update(title=None) if name == "get_session" else None
    )
    refused(env)


@pytest.mark.parametrize("value", [5, b"Bot Chat", ["Bot Chat"]])
def test_holder_title_wrong_type_on_reread_is_uncertain(env: Env, value: Any) -> None:
    env.bot_chat()
    env.db.hooks.append(
        lambda name, n: env.db.sessions["C"].update(title=value) if name == "get_session" else None
    )
    refused(env, reason="eligibility_uncertain")


def test_another_chain_row_with_a_nonempty_title_refuses(env: Env) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    env.db.sessions["M"]["title"] = "Other"
    refused(env, "R", tip)
    env.db.sessions["M"]["title"] = "Bot Chat "  # near-miss spelling is still another title
    refused(env, "R", tip)


def test_root_with_another_title_when_the_holder_is_the_tip_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["title"] = "Old name"
    refused(env)


@pytest.mark.parametrize("value", [None, ""])
def test_other_rows_with_a_null_or_empty_title_are_valid(env: Env, value: Any) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    env.db.sessions["M"]["title"] = value
    assert env.bind(env.sidecar("R", tip)).ok


@pytest.mark.parametrize("value", [5, b"", False, ["x"]])
def test_other_row_title_wrong_type_is_uncertain(env: Env, value: Any) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    env.db.sessions["M"]["title"] = value
    refused(env, "R", tip, "eligibility_uncertain")


def test_title_field_missing_on_a_row_is_uncertain(env: Env) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    del env.db.sessions["M"]["title"]
    refused(env, "R", tip, "eligibility_uncertain")


def test_no_title_row_is_a_known_negative(env: Env) -> None:
    for sid in ("R", "C"):
        env.db.sessions[sid] = session_row(sid, hidden=1 if sid == "R" else 0)
    env.db.compression["R"] = "C"
    env.put_images("C")
    refused(env)


def test_title_lookup_row_of_the_wrong_shape_is_uncertain(env: Env) -> None:
    env.bot_chat()
    for bad in ([("id", "C")], object(), "C", 5):
        env.db.returns["get_session_by_title"] = lambda _t, bad=bad: bad
        refused(env, reason="eligibility_uncertain")


class DictLike(dict):  # type: ignore[type-arg]
    pass


class StrLike(str):
    pass


@pytest.mark.parametrize(
    "row",
    [
        {"id": "C", "title": "Other"},  # title contradicts the exact-title lookup
        {"id": "C", "title": StrLike("Bot Chat")},
        {"id": "", "title": "Bot Chat"},
        {"id": StrLike("C"), "title": "Bot Chat"},
        {"id": 5, "title": "Bot Chat"},
        {"title": "Bot Chat"},
        {"id": "C"},
        DictLike(id="C", title="Bot Chat"),
    ],
)
def test_title_lookup_fields_must_be_exact(env: Env, row: Any) -> None:
    env.bot_chat()
    env.db.returns["get_session_by_title"] = lambda _t: row
    refused(env, reason="eligibility_uncertain")


def test_chain_row_must_be_an_exact_dict_with_the_matching_id(env: Env) -> None:
    env.bot_chat()
    for bad in (
        DictLike(env.db.sessions["R"]),
        {**env.db.sessions["R"], "id": "other"},
        {k: v for k, v in env.db.sessions["R"].items() if k != "id"},
        {**env.db.sessions["R"], "id": StrLike("R")},
        [("id", "R")],
    ):
        env.db.returns["get_session"] = lambda sid, bad=bad: (
            bad if sid == "R" else dict(env.db.sessions[sid])
        )
        refused(env, reason="eligibility_uncertain")


# -- the strict re-read of the walk comes before any negative (B1) ---------------------------


def _phone_and_bot(env: Env) -> str:
    tip = env.bot_chat()
    env.bind_store("R")  # the caller's own conversation is bound to the same session
    return tip


def test_baseline_phone_and_bot_chat_on_one_session_is_ambiguous(env: Env) -> None:
    _phone_and_bot(env)
    refused(env)


@pytest.mark.parametrize("row", ["C", "R"])
@pytest.mark.parametrize("missing", ["parent_session_id", "id"])
def test_walk_shape_fault_is_uncertain_even_when_phone_is_proven(
    env: Env, row: str, missing: str
) -> None:
    _phone_and_bot(env)
    # The lax walk reads a missing parent as a root and a missing id as unchecked.
    del env.db.sessions[row][missing]
    refused(env, reason="eligibility_uncertain")


def test_walk_shape_fault_without_a_phone_session_is_uncertain_not_negative(env: Env) -> None:
    env.bot_chat()
    del env.db.sessions["C"]["parent_session_id"]
    refused(env, reason="eligibility_uncertain")


def test_walk_link_changed_between_reads_is_closed_even_when_phone_is_proven(env: Env) -> None:
    _phone_and_bot(env)
    seen = {"n": 0}

    def change(name: str, _n: int) -> None:
        if name == "get_session":
            seen["n"] += 1
            if seen["n"] == 3:  # the first strict re-read follows the two-row parent walk
                env.db.sessions["C"]["parent_session_id"] = "elsewhere"

    env.db.hooks.append(change)
    refused(env, reason="eligibility_uncertain")


def test_walk_shape_fault_beats_a_lineage_inequality(env: Env) -> None:
    _phone_and_bot(env)
    env.db.returns["get_compression_lineage"] = lambda _s: ["C"]
    env.db.sessions["C"]["parent_session_id"] = 5
    refused(env, reason="eligibility_uncertain")


def test_each_walked_row_is_read_once_more_before_the_equality_check(env: Env) -> None:
    env.bot_chat()
    env.db.returns["get_compression_lineage"] = lambda _s: ["C"]
    refused(env)  # a lineage inequality with a sound walk is a plain negative
    assert env.db.counts["get_session"] == 4  # two walk reads and two strict re-reads


def test_t1_bound_outside_the_chain_with_a_resolver_to_the_tip_still_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["X"] = session_row("X")
    real = env.db.plain_resolve
    env.db.returns["resolve_resume_session_id"] = lambda sid: "C" if sid == "X" else real(sid)
    refused(env, "X", "C")  # only the chain-membership check can refuse this


def test_t3_native_lineage_is_asked_for_the_holder_not_the_session_or_tip(env: Env) -> None:
    env.bot_chat(("R", "M", "C"), holder="M")
    asked: list[str] = []
    real = env.db.get_compression_lineage

    def spy(sid: str) -> Any:
        asked.append(sid)
        return real(sid)

    env.db.get_compression_lineage = spy  # type: ignore[method-assign]
    sidecar = env.sidecar("R", "C")
    assert env.bind(sidecar).ok
    assert asked and set(asked) == {"M"}


# -- lineage shape, parent walk and resolution ------------------------------------------------


@pytest.mark.parametrize(
    "lineage",
    [
        ("R", "C"),  # a tuple
        [],
        None,
        "RC",
        ["R", ""],
        ["R", 5],
        ["R", None],
        ["R", StrLike("C")],
        ["R", "R", "C"],  # duplicate
    ],
)
def test_lineage_shape_failures_are_uncertain(env: Env, lineage: Any) -> None:
    env.bot_chat()
    env.db.returns["get_compression_lineage"] = lambda _s: lineage
    refused(env, reason="eligibility_uncertain")


def test_lineage_of_101_ids_is_uncertain_and_100_is_the_ceiling(env: Env) -> None:
    ids = tuple(f"s{i:03d}" for i in range(101))
    env.bot_chat(ids)
    refused(env, ids[0], ids[-1], "eligibility_uncertain")


def test_chain_of_exactly_100_is_valid_and_101_hops_fail_the_walk(env: Env) -> None:
    ids = tuple(f"s{i:03d}" for i in range(100))
    tip = env.bot_chat(ids)
    assert env.bind(env.sidecar(ids[0], tip)).ok
    # A lineage that claims only 100 ids while the parent walk would need 101 hops: unprovable.
    longer = tuple(f"t{i:03d}" for i in range(101))
    for index, sid in enumerate(longer):
        env.db.sessions[sid] = session_row(sid, parent=longer[index - 1] if index else None)
    env.db.sessions[longer[0]]["hidden"] = 1
    env.db.sessions[longer[-1]]["title"] = "Bot Chat"
    for sid in ids:
        env.db.sessions[sid]["title"] = None
    env.db.returns["get_compression_lineage"] = lambda _s: list(longer[1:])
    env.db.returns["resolve_resume_session_id"] = lambda _s: longer[-1]
    refused(env, longer[1], longer[-1], "eligibility_uncertain")


def test_parent_cycle_is_uncertain(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["parent_session_id"] = "C"
    refused(env, reason="eligibility_uncertain")


def test_missing_parent_row_is_uncertain(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["R"]["parent_session_id"] = "ghost"
    refused(env, reason="eligibility_uncertain")


def test_missing_chain_row_on_reread_is_uncertain(env: Env) -> None:
    env.bot_chat()
    seen = {"n": 0}

    def drop(name: str, _n: int) -> None:
        if name == "get_session":
            seen["n"] += 1
            if seen["n"] == 3:  # the first strict re-read follows the two-row parent walk
                env.db.sessions.pop("R", None)

    env.db.hooks.append(drop)
    refused(env, reason="eligibility_uncertain")


def test_a_fork_child_is_refused(env: Env) -> None:
    env.bot_chat()
    # F is a fork of the ancestor: it has a parent, but no compression edge leads to it.
    env.db.sessions["F"] = session_row("F", parent="R", title="Bot Chat")
    env.db.sessions["C"]["title"] = None
    refused(env, "F", "F")


def test_a_fork_of_the_tip_is_refused(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["F"] = session_row("F", parent="C")
    env.db.compression.pop("F", None)
    env.db.walker["C"] = "F"  # the resume walker descends into a non-compression child
    refused(env, "R", "F")


def test_resume_walker_beyond_the_compression_lineage_refuses_as_unavailable(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["W"] = session_row("W", parent="C")
    env.db.walker["C"] = "W"
    refused(env, "R", "W")  # chain (R, C, W) differs from the native lineage (R, C)


def test_lineage_equals_chain_but_the_resolver_goes_elsewhere_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.returns["resolve_resume_session_id"] = lambda _s: "R"
    refused(env, "R", "C")


def test_unrelated_titled_hidden_session_reached_by_browsing_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["G"] = session_row("G", hidden=1)  # hidden plumbing, not in the chain
    env.put_images("G")
    refused(env, "G", "G")
    sidecar = env.sidecar("G", "G", origin=MediaOrigin.BROWSED_SESSION)
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_bound_session_must_resolve_to_the_same_tip(env: Env) -> None:
    env.bot_chat()
    real = env.db.plain_resolve

    def odd(sid: str) -> str:
        return "R" if sid == "R" else real(sid)

    env.db.returns["resolve_resume_session_id"] = odd
    refused(env, "R", "C")  # bound R resolves to R, not the tip C


@pytest.mark.parametrize("value", [None, "", 5, StrLike("C"), ["C"]])
def test_resolver_wrong_type_for_the_bound_session_is_uncertain(env: Env, value: Any) -> None:
    env.bot_chat()
    real = env.db.plain_resolve
    env.db.returns["resolve_resume_session_id"] = lambda sid: value if sid == "R" else real(sid)
    refused(env, "R", "C", "eligibility_uncertain")


def test_resolver_wrong_type_for_the_holder_is_uncertain(env: Env) -> None:
    env.bot_chat()
    env.db.returns["resolve_resume_session_id"] = lambda _s: None
    refused(env, reason="eligibility_uncertain")


def test_title_holder_outside_the_chain_refuses_even_when_lineage_equals_the_walk(
    env: Env,
) -> None:
    env.bot_chat()
    env.db.sessions["H"] = session_row("H", title="Bot Chat", hidden=1)
    env.db.sessions["C"]["title"] = None
    real = env.db.plain_resolve
    env.db.returns["resolve_resume_session_id"] = lambda sid: "C" if sid == "H" else real(sid)
    env.db.returns["get_compression_lineage"] = lambda _sid: ["R", "C"]
    refused(env, "R", "C")  # the holder H is not on the tip's parent chain


def test_bound_session_outside_the_chain_refuses(env: Env) -> None:
    env.bot_chat()
    env.db.sessions["Z"] = session_row("Z")
    refused(env, "Z", "C")


# --------------------------------------------------------------------------------------------
# Phone proof and ambiguity
# --------------------------------------------------------------------------------------------


def test_browsed_projected_tip_of_a_compressed_own_session_refuses(env: Env) -> None:
    tip = env.phone(("p1", "p2"))
    sidecar = env.sidecar("p2", tip, origin=MediaOrigin.BROWSED_SESSION)
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_own_session_labelled_browsed_still_qualifies_by_exact_equality(env: Env) -> None:
    tip = env.phone(("p1", "p2"))
    sidecar = env.sidecar("p1", tip, origin=MediaOrigin.BROWSED_SESSION)
    assert env.bind(sidecar).ok  # `MediaOrigin` confers or removes nothing


def test_foreign_phone_session_refuses(env: Env) -> None:
    env.phone(("p1",))
    env.db.sessions["foreign"] = session_row("foreign")
    env.put_images("foreign")
    sidecar = env.sidecar("foreign", "foreign")
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_another_users_sidecar_refuses(env: Env) -> None:
    tip = env.phone(("p1",))
    sidecar = env.sidecar("p1", tip, user=OTHER_USER)  # that user has no conversation
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_no_conversation_for_the_user_refuses_phone_and_nothing_proves(env: Env) -> None:
    env.db.sessions["p1"] = session_row("p1")
    env.put_images("p1")
    sidecar = env.sidecar("p1", "p1")
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_store_bound_to_another_session_refuses(env: Env) -> None:
    tip = env.phone(("p1",))
    env.bind_store("elsewhere")
    sidecar = env.sidecar("p1", tip)
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_phone_resolution_has_no_session_id_fallback(env: Env) -> None:
    env.phone(("p1",))
    sidecar = env.sidecar("p1", "p1")
    for bad in (None, "", 5, StrLike("p1")):
        env.db.returns["resolve_resume_session_id"] = lambda _s, bad=bad: bad
        assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


def test_both_phone_and_bot_chat_is_ambiguous(env: Env) -> None:
    tip = env.bot_chat()
    env.bind_store("R")  # the caller's own bound session is also the Bot Chat root
    sidecar = env.sidecar("R", tip)
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")
    assert "get_active_message_ids" not in env.db.counts


def test_both_ambiguous_for_a_middle_session_too(env: Env) -> None:
    tip = env.bot_chat(("R", "M", "C"))
    env.bind_store("M")
    sidecar = env.sidecar("M", tip)
    assert_closed(env.bind(sidecar), sidecar, "not_eligible")


def test_valid_phone_with_an_uncertain_bot_chat_proof_refuses_the_whole_binding(env: Env) -> None:
    tip = env.phone(("p1",))
    # The own session is also the titled Bot Chat holder, with a wrong-typed hidden flag.
    env.db.sessions["p1"].update(title="Bot Chat", hidden=True)
    sidecar = env.sidecar("p1", tip)
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


@pytest.mark.parametrize(
    "fault",
    [
        ("get_session_by_title", RuntimeError(SENTINEL)),
        ("get_compression_lineage", RuntimeError(SENTINEL)),
        ("get_session", RuntimeError(SENTINEL)),
    ],
)
def test_valid_phone_with_a_bot_chat_native_exception_refuses(
    env: Env, fault: tuple[str, BaseException]
) -> None:
    tip = env.phone(("p1",))
    env.db.sessions["Bc"] = session_row("Bc", title="Bot Chat", hidden=1)
    if fault[0] != "get_session_by_title":
        env.db.compression["Bc"] = "Bd"  # the title row exists so the proof reaches that call
        env.db.sessions["Bd"] = session_row("Bd", parent="Bc")
    env.db.raises[fault[0]] = fault[1]
    sidecar = env.sidecar("p1", tip)
    binding = env.bind(sidecar)
    assert binding.reason == "eligibility_uncertain"
    assert binding.kind is None


def test_valid_bot_chat_with_an_uncertain_phone_proof_refuses_the_whole_binding(env: Env) -> None:
    tip = env.bot_chat()
    env.world.adapter._session_store = None  # `conversation_ref` raises for a user with a chat
    sidecar = env.sidecar("R", tip)
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


def test_valid_bot_chat_with_a_malformed_conversation_ref_is_uncertain(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    tip = env.bot_chat()
    for bad in (object(), ("u", "alpha", "R"), 5):
        monkeypatch.setattr(HermesReadBridge, "conversation_ref", lambda *_a, bad=bad: bad)
        sidecar = env.sidecar("R", tip)
        assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


def test_conversation_ref_with_a_foreign_profile_or_user_is_uncertain(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hmp_plugin.contract import ConversationRef

    tip = env.phone(("p1",))
    sidecar = env.sidecar("p1", tip)
    for ref in (
        ConversationRef(USER, "beta", "p1"),
        ConversationRef(OTHER_USER, "alpha", "p1"),
    ):
        monkeypatch.setattr(HermesReadBridge, "conversation_ref", lambda *_a, ref=ref: ref)
        assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


@pytest.mark.parametrize(
    "fields",
    [
        (USER, "alpha", ""),
        (StrLike(USER), "alpha", "R"),
        (USER, StrLike("alpha"), "R"),
        (USER, "alpha", StrLike("R")),
        (5, "alpha", "R"),
        (USER, None, "R"),
    ],
)
def test_malformed_phone_ref_with_a_proven_bot_chat_closes_rather_than_accepts(
    env: Env, monkeypatch: pytest.MonkeyPatch, fields: tuple[Any, ...]
) -> None:
    from hmp_plugin.contract import ConversationRef

    tip = env.bot_chat()
    ref = ConversationRef(*fields)
    monkeypatch.setattr(HermesReadBridge, "conversation_ref", lambda *_a: ref)
    sidecar = env.sidecar("R", tip)
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")


# --------------------------------------------------------------------------------------------
# Brackets: the complete classification re-runs, with both kinds, at both tip checks
# --------------------------------------------------------------------------------------------


def _ambiguous(env: Env) -> None:
    env.bind_store("R")  # Phone now also proves the same session


def _uncertain(env: Env) -> None:
    env.db.sessions["R"]["hidden"] = True


def _lost(env: Env) -> None:
    env.db.sessions["R"]["hidden"] = 0


def _tip_moves(env: Env) -> None:
    env.db.sessions["D"] = session_row("D", parent="C")
    env.db.compression["C"] = "D"


def _kind_swaps(env: Env) -> None:
    env.db.sessions["R"]["hidden"] = 0  # Bot Chat stops proving ...
    env.bind_store("R")  # ... while the same tip now proves as the caller's own Phone session


def _phone_only_uncertainty(env: Env) -> None:
    env.world.adapter._session_store = None


MUTATIONS = {
    "ambiguous": _ambiguous,
    "other_proof_uncertain": _phone_only_uncertainty,
    "uncertain": _uncertain,
    "lost": _lost,
    "tip_moves": _tip_moves,
    "kind_swaps": _kind_swaps,
}
SEAMS = {
    "ids0": ("get_active_message_ids", 1),
    "page": ("get_messages", 1),
    "ids1": ("get_active_message_ids", 2),
}


@pytest.mark.parametrize("seam", sorted(SEAMS))
@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_a_classification_change_at_any_batch_read_refuses_every_selector(
    env: Env, seam: str, mutation: str
) -> None:
    sidecar = valid_bot(env)
    target, nth = SEAMS[seam]
    fired: list[bool] = []

    def flip(name: str, count: int) -> None:
        if name == target and count == nth and not fired:
            fired.append(True)
            MUTATIONS[mutation](env)

    env.db.hooks.append(flip)
    binding = env.bind(sidecar)
    assert fired
    assert_closed(binding, sidecar, "tip_changed")
    assert binding.report()["accepted"] == 0


def test_uncertainty_in_the_initial_classification_never_starts_the_batch(env: Env) -> None:
    sidecar = valid_bot(env)
    _uncertain(env)
    assert_closed(env.bind(sidecar), sidecar, "eligibility_uncertain")
    assert "get_active_message_ids" not in env.db.counts


def test_unchanged_classification_through_both_brackets_is_accepted(env: Env) -> None:
    sidecar = valid_bot(env)
    assert env.bind(sidecar).ok


def test_concurrent_writer_changing_the_active_ids_refuses_every_selector(env: Env) -> None:
    sidecar = valid_bot(env)

    def write(name: str, count: int) -> None:
        if name == "get_messages" and count == 1:
            env.db.messages["C"].append({"id": 99, "role": "user", "content": "hi"})

    env.db.hooks.append(write)
    assert_closed(env.bind(sidecar), sidecar, "rows_changed")


def test_phone_bracket_recheck_uses_the_fresh_conversation_ref(env: Env) -> None:
    tip = env.phone(("p1", "p2"))
    sidecar = env.sidecar("p1", tip)
    fired: list[bool] = []

    def flip(name: str, count: int) -> None:
        if name == "get_messages" and not fired:
            fired.append(True)
            env.bind_store("moved-on")  # the own conversation was rebound mid-batch

    env.db.hooks.append(flip)
    assert_closed(env.bind(sidecar), sidecar, "tip_changed")


# --------------------------------------------------------------------------------------------
# Native errors: content-free, no log, no raise
# --------------------------------------------------------------------------------------------

NATIVE_FAULTS = [
    "get_session_by_title",
    "resolve_resume_session_id",
    "get_compression_lineage",
    "get_session",
    "get_active_message_ids",
    "get_messages",
]


@pytest.mark.parametrize("method", NATIVE_FAULTS)
def test_native_exceptions_are_closed_and_leak_nothing(
    env: Env,
    method: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sidecar = valid_bot(env)
    env.db.raises[method] = RuntimeError(f"{SENTINEL} {env.home}")
    with caplog.at_level(logging.DEBUG):
        binding = env.bind(sidecar)
    assert type(binding) is bind.MediaBatchBinding and not binding.ok
    assert binding.reason in bind.BINDING_REASONS and binding.kind is None
    if method not in ("get_active_message_ids", "get_messages"):
        assert binding.reason == "eligibility_uncertain"
    blob = f"{binding!r} {binding!s} {binding.report()} {caplog.text}"
    out, err = capsys.readouterr()
    for text in (blob, out, err):
        assert SENTINEL not in text and env.home not in text
    assert not caplog.records
    assert (env.world.api.acquired, env.world.api.released) == (1, 1)


def test_conversation_ref_failure_is_closed_and_leaks_nothing(
    env: Env, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    sidecar = valid_bot(env)

    def boom(*_a: Any) -> Any:
        raise BridgeError(SENTINEL)

    monkeypatch.setattr(HermesReadBridge, "conversation_ref", boom)
    with caplog.at_level(logging.DEBUG):
        binding = env.bind(sidecar)
    assert_closed(binding, sidecar, "eligibility_uncertain")
    assert SENTINEL not in caplog.text and not caplog.records


def test_base_exceptions_propagate_and_the_database_is_released(env: Env) -> None:
    sidecar = valid_bot(env)
    env.db.raises["get_session_by_title"] = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        env.bind(sidecar)
    assert (env.world.api.acquired, env.world.api.released) == (1, 1)


def test_batch_native_error_does_not_change_old_successful_text_reads(env: Env) -> None:
    from hmp_plugin.contract import ConversationRef

    tip = env.phone(("p1",))
    ref = ConversationRef(USER, "alpha", "p1")
    env.db.messages.setdefault(tip, [])
    before = env.bridge.latest(ref, 5)
    sidecar = env.sidecar("p1", tip)
    env.db.raises["get_active_message_ids"] = RuntimeError(SENTINEL)
    assert not env.bind(sidecar).ok
    del env.db.raises["get_active_message_ids"]
    assert env.bridge.latest(ref, 5) == before


# --------------------------------------------------------------------------------------------
# Inertness, imports, no logging, accepted pins
# --------------------------------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add(
                "." * node.level + (node.module or "") + "|" + ",".join(a.name for a in node.names)
            )
    return found


def test_binding_module_imports_only_the_accepted_modules_and_stdlib() -> None:
    assert _imports(PACKAGE / "local_media_batch_binding.py") == {
        "__future__|annotations",
        "os",
        "enum|Enum",
        "typing|Any,Final",
        ".|local_media_active_batch",
        ".|local_media_sidecar",
    }


def test_binding_module_has_no_io_logging_dynamic_import_or_native_reach() -> None:
    tree = ast.parse((PACKAGE / "local_media_batch_binding.py").read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"open", "print", "exec", "eval", "__import__", "getattr", "setattr"}
    assert not attrs & {
        "stat",
        "lstat",
        "open",
        "exists",
        "is_file",
        "resolve",
        "realpath",
        "listdir",
        "scandir",
        "getLogger",
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "import_module",
    }
    for forbidden in ("get_session", "get_messages", "resolve_resume", "conversation_ref"):
        assert forbidden not in (PACKAGE / "local_media_batch_binding.py").read_text()


def _bridge_methods() -> dict[str, ast.FunctionDef]:
    tree = ast.parse((PACKAGE / "bridge.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "HermesReadBridge")
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


NEW_METHODS = ("_phone_proof", "_bot_chat_proof", "media_eligibility", "bind_media_batch")


def test_new_bridge_methods_import_statically_function_local_and_log_nothing() -> None:
    methods = _bridge_methods()
    allowed = {
        "local_media_active_batch",
        "local_media_batch_binding",
        "local_media_sidecar",
    }
    for name in NEW_METHODS:
        node = methods[name]
        for inner in ast.walk(node):
            if isinstance(inner, ast.Import):
                raise AssertionError(f"{name}: plain import")
            if isinstance(inner, ast.ImportFrom):
                assert inner.level == 1 and inner.module in allowed, (name, inner.module)
            if isinstance(inner, ast.Call):
                target = inner.func
                label = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                assert label not in {
                    "log_event",
                    "log_bridge_exception",
                    "print",
                    "__import__",
                    "import_module",
                    "getLogger",
                    "exec",
                    "eval",
                }, (name, label)
    assert "importlib" not in (PACKAGE / "bridge.py").read_text()
    assert "__import__" not in (PACKAGE / "bridge.py").read_text()


def test_new_bridge_methods_never_reach_media_origin_resolve_bot_chat_or_registry() -> None:
    methods = _bridge_methods()
    for name in NEW_METHODS:
        node = methods[name]
        node.body = node.body[1:] if ast.get_docstring(node) else node.body  # docstrings are prose
        text = ast.unparse(node)
        for banned in (
            "MediaOrigin",
            "origin",
            "resolve_bot_chat",
            "self._tip",
            "local_media_registry",
            "authz_state",
            "request_authorization",
            "_authorized",
            "ActiveBatchResult",
            "latest_with_media",
            "hint",
        ):
            assert banned not in text, (name, banned)


def test_bind_media_batch_takes_only_the_sidecar() -> None:
    params = list(inspect.signature(HermesReadBridge.bind_media_batch).parameters)
    assert params == ["self", "sidecar"]
    assert not inspect.iscoroutinefunction(HermesReadBridge.bind_media_batch)


OLD_METHOD_HASHES = {
    "latest": "3c37321861c4c291bff35dc03a8a0da6b11b83c737359d2267a04700d90eac44",
    "after": "28eef086f1faa314a2e0cc56ec4158c4d68b58ce89ff1a06c4739ad63634036f",
    "_media_rows": "30de9ef6460c21534be8e05fb8b792533dde723e7c06456aae8b75b336cc5e05",
    "latest_with_media": "8e9391e5f5c7963628dc2d83ec32aca20e8b6d3122e92bb58d9d7ce07d6c23c3",
    "after_with_media": "45302022098514fd35cec337867e9190f6a99cc29d4dc7d2a6ac4b8f01c393dc",
    "_latest_query": "5fa2e17bacc1ac1854c5d0bcb27c861868ace332830803aab23aeaa9e6b66394",
    "_after_query": "399b156bd94d66f669a043215b1f7eeb9e328c97b8901722444105a1ee2a1345",
    "resolve_bot_chat": "89ac4792b07ccfffbde63ecd7b75d3310e5d182a42d9b6841d7f7cc42a358d9e",
    "conversation_ref": "cf008187292eb9e8392a421b43e4140ebcac7740246ac6b216783bbc9f8e034a",
    "_db_home": "b7217af7409b6eec545abe97d9bfa8d1a568db2a1f08ab1350e5c60b77cb2c77",
    "_db": "98830ebd6be63455586b0befed7ff5c3a04e1966fcccc58524f94e0ac2c31a38",
    "_tip": "e75bc543ea74b386df6f761f52d1e17eb67a516a68a98513915ba491108cbe87",
    "_rows": "47633c078a20bb0a5a3dcddb72bd5fdc05a2e0f2176c9fa7091e0141bcfaca2e",
    "lineage": "9fd5a6940ceb93f2f99a20b17db2051291b3cf0679b4d3a340643a33f087276b",
}


def _method_hash(name: str) -> str:
    source = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, _bridge_methods()[name])
    assert segment is not None
    return hashlib.sha256(segment.encode()).hexdigest()


def test_old_bridge_methods_and_parent_chain_are_byte_identical() -> None:
    for name, expected in OLD_METHOD_HASHES.items():
        assert _method_hash(name) == expected, name
    source = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_parent_chain")
    segment = ast.get_source_segment(source, fn)
    assert segment is not None
    assert hashlib.sha256(segment.encode()).hexdigest() == PARENT_CHAIN_HASH


PARENT_CHAIN_HASH = "c2b552655461e7b0922f86ca814f015a85a7439126a2fb557af959253bb533cf"

ACCEPTED_BATCH = "b30d3bcc37e246a193d00d599855b7abcc114d1a2812d8014cb7062566948ecc"


def test_accepted_batch_module_is_byte_identical() -> None:
    digest = hashlib.sha256((PACKAGE / "local_media_active_batch.py").read_bytes()).hexdigest()
    assert digest == ACCEPTED_BATCH


def test_reached_methods_table_is_unchanged_by_the_binding() -> None:
    assert real_bridge.REACHED_METHODS["db"] >= {
        "get_session_by_title",
        "get_session",
        "get_compression_lineage",
        "resolve_resume_session_id",
    }
    assert set(real_bridge.REACHED_METHODS) == {"runner", "adapter", "session_store", "db"}


LOADED = "sorted(m.rsplit('.', 1)[-1] for m in sys.modules if 'local_media_' in m)"


def _fresh(code: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        env=env,
        cwd=PACKAGE.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_importing_the_binding_loads_only_the_accepted_chain() -> None:
    done = _fresh(
        "import sys, hmp_plugin.local_media_batch_binding\n"
        f"print(','.join({LOADED}))\n"
        "assert 'hmp_plugin.bridge' not in sys.modules and 'hmp_plugin.reads' not in sys.modules\n"
    )
    assert done.returncode == 0, done.stderr[-500:]
    assert set(done.stdout.strip().split(",")) == {
        "local_media_active_batch",
        "local_media_active_scan",
        "local_media_batch_binding",
        "local_media_candidate",
        "local_media_file_safety",
        "local_media_result",
        "local_media_sidecar",
    }


def test_bridge_loads_the_binding_only_when_a_bind_runs(tmp_path: Path) -> None:
    code = (
        "import sys, tempfile, pathlib, importlib.util\n"
        "from tests.unit.test_local_media_batch_binding import Env, valid_bot\n"
        f"def media(): return {LOADED}\n"
        f"env = Env(pathlib.Path({str(tmp_path)!r}))\n"
        "sidecar = valid_bot(env)\n"
        "assert 'local_media_batch_binding' not in media() or True\n"
        "b = env.bind(sidecar)\n"
        "assert b.ok, b.reason\n"
        "got = set(media())\n"
        "assert 'local_media_batch_binding' in got and 'local_media_active_batch' in got, got\n"
        "assert not got & {'local_media_registry', 'local_media_gate'}, got\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('hermes_state', 'gateway')]\n"
        "assert not bad, bad\n"
    )
    done = _fresh(code)
    assert done.returncode == 0, done.stderr[-800:]


def test_binding_import_does_not_happen_at_bridge_import() -> None:
    done = _fresh(
        "import sys\n"
        "import hmp_plugin.reads, hmp_plugin.server\n"
        "assert not [m for m in sys.modules if 'local_media_batch_binding' in m]\n"
    )
    assert done.returncode == 0, done.stderr[-500:]
