"""S2c: the bridge's media-aware read twins, against the fake Hermes objects.

Each guard is a function of a bridge module, so it runs against the real `hmp_plugin.bridge` and
against out-of-tree mutants of its source that must fail it. Nothing here touches a real Hermes
home. Old public wire golden bytes belong to S2d; nothing here claims S2 is complete.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import types
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import bridge as real_bridge
from hmp_plugin import wire
from hmp_plugin.bridge import BridgeError
from hmp_plugin.contract import TOOL_OUTPUT_CAP, ConversationRef, ResetReason
from hmp_plugin.local_media_sidecar import BridgeMediaRows, MediaCandidate

from .fake_hermes import FakeDirectory, World

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
BRIDGE_PATH = PACKAGE / "bridge.py"
BRIDGE_SOURCE = BRIDGE_PATH.read_text(encoding="utf-8")

USER = "hmpu_" + "a" * 32
CHAT = "c_" + "1" * 32
REF = ConversationRef(USER, "alpha", "s1")


def image_result(home: Path, name: str = "gen_a.png", pad: int = 0) -> str:
    # The padding comes first, so a large `pad` pushes the `image` key past the tool-text cap.
    return json.dumps({"pad": "x" * pad, "success": True, "image": f"{home}/cache/images/{name}"})


def make_world(tmp_path: Path) -> tuple[World, FakeDirectory]:
    world, directory = World(tmp_path), FakeDirectory()
    directory.chats[(USER, "alpha")] = CHAT
    world.start_conversation("alpha", CHAT, "s1")
    return world, directory


def tool(world: World, content: Any, name: str = "image_generate", cid: str | None = None) -> int:
    row_id = world.dbs["alpha"].next_id
    return world.dbs["alpha"].append(
        "s1", "tool", content, tool_name=name, tool_call_id=cid or f"call_{row_id}"
    )


def seed(world: World) -> list[int]:
    db, home = world.dbs["alpha"], world.runner.homes["alpha"]
    return [
        db.append("s1", "user", "hello"),
        tool(world, image_result(home, "gen_a.png")),
        db.append("s1", "assistant", "done"),
        tool(world, image_result(home, "gen_b.png")),
    ]


class Recorder:
    """One ordered event log over the fake native objects, for exact old-vs-media comparison."""

    def __init__(self, world: World) -> None:
        self.events: list[Any] = []
        db, runner, api = world.dbs["alpha"], world.runner, world.api
        real_get, real_tip = db.get_messages, db.resolve_resume_session_id
        real_acq, real_rel, real_home = api.acquire, api.release, runner._routed_profile_home

        def get_messages(*a: Any, **k: Any) -> Any:
            self.events.append(("get_messages", a, tuple(sorted(k.items()))))
            return real_get(*a, **k)

        def tip(*a: Any) -> Any:
            self.events.append(("resolve_resume_session_id", a))
            return real_tip(*a)

        def acquire(*a: Any) -> Any:
            self.events.append("acquire")
            return real_acq(*a)

        def release(*a: Any) -> None:
            self.events.append("release")
            real_rel(*a)

        def home(*a: Any) -> Any:
            self.events.append(("_routed_profile_home", a))
            return real_home(*a)

        db.get_messages, db.resolve_resume_session_id = get_messages, tip  # type: ignore[method-assign]
        api.acquire, api.release = acquire, release  # type: ignore[method-assign]
        runner._routed_profile_home = home  # type: ignore[method-assign]


def new_bridge(module: types.ModuleType, world: World, directory: FakeDirectory) -> Any:
    return module.HermesReadBridge(world.adapter, directory, hermes=world.api)


# --------------------------------------------------------------------------------------------------
# Guards: each takes the bridge module under test and raises AssertionError on a violation.
# --------------------------------------------------------------------------------------------------

AFTER_CASES = ["after0", "after_positive", "reset_missing", "reset_inactive", "probe_malformed"]


def run_pair(
    module: types.ModuleType,
    tmp_path: Path,
    kind: str,
    mutate: Callable[[World], None] | None = None,
) -> tuple[Any, list[Any], Any, list[Any]]:
    """The old method and its media twin on two identical worlds: (old, old log, media, log)."""
    outcomes = []
    for suffix in ("old", "media"):
        world, directory = make_world(tmp_path)  # same home path, so the rows are comparable
        ids = seed(world)
        if mutate:
            mutate(world)
        rec, br = Recorder(world), new_bridge(module, world, directory)
        if kind == "latest":
            call = br.latest if suffix == "old" else br.latest_with_media
            args: tuple[Any, ...] = (REF, 3)
        else:
            cursor = {
                "after0": 0,
                "after_positive": ids[1],
                "reset_missing": 999,
                "reset_inactive": ids[1],
                "probe_malformed": ids[1],
            }[kind]
            if kind == "reset_inactive":
                world.dbs["alpha"].rows[1]["active"] = 0
            if kind == "probe_malformed":
                world.dbs["alpha"].rows[1]["active"] = 7
            call = br.after if suffix == "old" else br.after_with_media
            args = (REF, cursor, 100)
        try:
            out: Any = call(*args)
        except module.BridgeError as exc:
            out = type(exc).__name__
        outcomes.append((out, rec.events))
    return outcomes[0][0], outcomes[0][1], outcomes[1][0], outcomes[1][1]


def rows_of(out: Any) -> Any:
    return list(out.rows) if isinstance(out, BridgeMediaRows) else out


def guard_native_logs_equal(module: types.ModuleType, tmp_path: Path) -> None:
    for kind in ["latest", *AFTER_CASES]:
        old, old_log, media, media_log = run_pair(module, tmp_path / kind, kind)
        assert old_log == media_log, kind
        assert rows_of(media) == old, kind


def guard_golden_log(module: types.ModuleType, tmp_path: Path) -> None:
    """The pre-S2c native call sequence, pinned literally (a drift in the shared core fails)."""
    _, log, _, _ = run_pair(module, tmp_path / "l", "latest")
    home = ("_routed_profile_home", ("alpha",))
    assert log == [
        home,
        "acquire",
        ("resolve_resume_session_id", ("s1",)),
        ("get_messages", ("s1",), (("latest", True), ("limit", 3))),
        "release",
    ]
    _, log, _, _ = run_pair(module, tmp_path / "a", "after_positive")
    probe, page = log[3], log[4]
    assert log[:3] == [home, "acquire", ("resolve_resume_session_id", ("s1",))]
    assert probe[:2] == ("get_messages", ("s1",))
    after_id = dict(probe[2])["after_id"]
    assert probe[2] == (("after_id", after_id), ("include_inactive", True), ("limit", 1))
    assert page == ("get_messages", ("s1",), (("after_id", after_id + 1), ("limit", 100)))
    assert log[5:] == ["release"]


def guard_same_home_once(module: types.ModuleType, tmp_path: Path) -> None:
    for kind in ["latest", "after0", "after_positive"]:
        _, old_log, _, media_log = run_pair(module, tmp_path / kind, kind)
        for log in (old_log, media_log):
            assert [e for e in log if e[0] == "_routed_profile_home"] == [
                ("_routed_profile_home", ("alpha",))
            ]


def guard_exact_query_tip(module: types.ModuleType, tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    seed(world)
    db = world.dbs["alpha"]
    db.children["s1"] = "s1b"
    db.append("s1b", "user", "later")
    # Independently later lineage drift: every resolve after the first answers a different tip.
    calls = {"n": 0}

    def drifting(session_id: str) -> str:
        calls["n"] += 1
        return "s1b" if calls["n"] == 1 else "s1c"

    db.resolve_resume_session_id = drifting  # type: ignore[method-assign]
    rec, br = Recorder(world), new_bridge(module, world, directory)
    db.resolve_resume_session_id = drifting  # type: ignore[method-assign]
    out = br.latest_with_media(REF, 5)
    queried = [e[1][0] for e in rec.events if e[0] == "get_messages"]
    assert queried == ["s1b"] and out.query.query_tip == "s1b"
    assert out.query.session_id == "s1" and out.query.profile == "alpha"
    assert calls["n"] == 1
    out2 = br.after_with_media(REF, 0, 5)
    assert out2.query.query_tip == "s1c" and calls["n"] == 2  # exactly one resolve per query


def guard_candidate_after_cap(module: types.ModuleType, tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    home = world.runner.homes["alpha"]
    tool(world, image_result(home, "gen_big.png", pad=TOOL_OUTPUT_CAP + 100))
    br = new_bridge(module, world, directory)
    out = br.latest_with_media(REF, 5)
    (row,) = out.rows
    assert len(row.text) == TOOL_OUTPUT_CAP and row.truncated
    assert "gen_big" not in row.text  # the image key sits beyond the 4000-char cap
    assert [c.tool_row_id for c in out.candidates] == [row.id]
    assert br.latest(REF, 5) == [row]


def guard_filtering(module: types.ModuleType, tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    ids = seed(world)
    out = new_bridge(module, world, directory).latest_with_media(REF, 10)
    assert [c.tool_row_id for c in out.candidates] == [ids[3], ids[1]]  # newest first, both


def guard_module_inertness(module_path: Path) -> None:
    """Fresh interpreter: loading the bridge and running the OLD reads loads no local media."""
    code = (
        "import sys, importlib.util, tempfile, pathlib\n"
        "from hmp_plugin.contract import ConversationRef\n"
        "from tests.unit.fake_hermes import FakeDirectory, World\n"
        f"path = {str(module_path)!r}\n"
        "spec = importlib.util.spec_from_file_location('hmp_plugin._probe_bridge', path)\n"
        "m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m\n"
        "spec.loader.exec_module(m)\n"
        "def media(): return sorted(x for x in sys.modules if 'local_media_' in x)\n"
        "assert not media(), media()\n"
        "w, d = World(pathlib.Path(tempfile.mkdtemp())), FakeDirectory()\n"
        "u = 'hmpu_' + 'a' * 32\n"
        "d.chats[(u, 'alpha')] = 'c_' + '1' * 32\n"
        "w.start_conversation('alpha', 'c_' + '1' * 32, 's1')\n"
        "w.dbs['alpha'].append('s1', 'user', 'x')\n"
        "b = m.HermesReadBridge(w.adapter, d, hermes=w.api)\n"
        "r = ConversationRef(u, 'alpha', 's1')\n"
        "b.latest(r, 5); b.after(r, 0, 5)\n"
        "assert not media(), media()\n"
        "b.latest_with_media(r, 5)\n"
        "got = set(media())\n"
        "ok = {'local_media_active_scan', 'local_media_file_safety', 'local_media_result',\n"
        "      'local_media_sidecar', 'local_media_candidate'}\n"
        "assert {'hmp_plugin.' + n for n in ok} >= got, got\n"
        "assert 'hmp_plugin.local_media_candidate' in got, got\n"
    )
    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent)}
    done = subprocess.run(
        [sys.executable, "-B", "-c", code],
        env=env,
        cwd=PACKAGE.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-600:]


# --- S2c.1: the media-only downgrade --------------------------------------------------------------


@contextlib.contextmanager
def patched(owner: Any, name: str, value: Any) -> Iterator[None]:
    original = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextlib.contextmanager
def counting_collector() -> Iterator[list[Any]]:
    from hmp_plugin import local_media_candidate as cand

    calls: list[Any] = []
    real = cand.collect_candidates

    def spy(*args: Any) -> Any:
        calls.append(args)
        return real(*args)

    with patched(cand, "collect_candidates", spy):
        yield calls


def populate(world: World, session_id: str, total: int) -> None:
    """Exactly `total` rows on `session_id`, two of them strict image_generate results."""
    db, home = world.dbs["alpha"], world.runner.homes["alpha"]
    for i in range(total - 2):
        db.append(session_id, "user", f"m{i}")
    for name in ("gen_a.png", "gen_b.png"):
        row_id = db.next_id
        db.append(
            session_id,
            "tool",
            image_result(home, name),
            tool_name="image_generate",
            tool_call_id=f"call_{row_id}",
        )


# case -> (session id, tip the lineage resolves to, rows on the tip)
CASES: dict[str, tuple[str, str, int]] = {
    "long_session": ("s" * 257, "s" * 257, 6),
    "long_tip": ("s1", "t" * 300, 6),
    "rows_1001": ("s1", "s1", 1001),
    "session_256": ("s" * 256, "s" * 256, 6),
    "tip_256": ("s1", "t" * 256, 6),
    "rows_1000": ("s1", "s1", 1000),
    "plain": ("s1", "s1", 6),
}
DOWNGRADED = ["long_session", "long_tip", "rows_1001"]
REPRESENTABLE = ["session_256", "tip_256", "rows_1000"]


def case_world(tmp_path: Path, case: str) -> tuple[World, FakeDirectory, ConversationRef]:
    session_id, tip, total = CASES[case]
    world, directory = make_world(tmp_path)
    if tip != session_id:
        world.dbs["alpha"].children[session_id] = tip
    populate(world, tip, total)
    return world, directory, ConversationRef(USER, "alpha", session_id)


def call_twin(br: Any, name: str, ref: ConversationRef) -> Any:
    # The native fake ignores nothing here: 2000 exceeds every page the cases build.
    if name.startswith("latest"):
        return getattr(br, name)(ref, 2000)
    return getattr(br, name)(ref, 0, 2000)


METHOD_PAIRS = [("latest", "latest_with_media"), ("after", "after_with_media")]


def run_case(module: types.ModuleType, tmp_path: Path, case: str, name: str) -> dict[str, Any]:
    world, directory, ref = case_world(tmp_path, case)
    rec, br = Recorder(world), new_bridge(module, world, directory)
    parsed: list[Any] = []
    real_rows = br._rows

    def spy_rows(*a: Any) -> Any:
        parsed.append(real_rows(*a))
        return parsed[-1]

    br._rows = spy_rows
    with counting_collector() as collected:
        try:
            out = call_twin(br, name, ref)
        except module.BridgeError:
            raise AssertionError(f"{case}/{name}: unexpected BridgeError") from None
    return {
        "out": out,
        "events": rec.events,
        "parsed": parsed,
        "collected": collected,
        "acquired": world.api.acquired,
        "released": world.api.released,
    }


def guard_downgrade_returns_old_result(module: types.ModuleType, tmp_path: Path) -> None:
    for case in DOWNGRADED:
        for old_name, media_name in METHOD_PAIRS:
            where = f"{case}/{media_name}"
            old = run_case(module, tmp_path / f"{case}{old_name}", case, old_name)
            media = run_case(module, tmp_path / f"{case}{old_name}", case, media_name)
            assert type(media["out"]) is list, where
            assert media["out"] == old["out"] and len(media["out"]) > 0, where
            assert media["events"] == old["events"], where
            assert len(media["parsed"]) == 1 and media["out"] is media["parsed"][0], where
            homes = [e for e in media["events"] if e[0] == "_routed_profile_home"]
            assert len(homes) == 1, where
            assert media["acquired"] == media["released"] == 1, where
            assert media["events"].count("release") == 1, where
            assert media["collected"] == [], where


def guard_boundaries_stay_media(module: types.ModuleType, tmp_path: Path) -> None:
    for case in REPRESENTABLE:
        for old_name, media_name in METHOD_PAIRS:
            where = f"{case}/{media_name}"
            old = run_case(module, tmp_path / f"{case}{old_name}", case, old_name)
            media = run_case(module, tmp_path / f"{case}{old_name}", case, media_name)
            out = media["out"]
            assert type(out) is BridgeMediaRows, where
            assert list(out.rows) == old["out"], where
            assert media["events"] == old["events"], where
            assert len(media["collected"]) == 1, where
            session_id, tip, _ = CASES[case]
            assert out.query.session_id == session_id and out.query.query_tip == tip, where
            assert len(out.candidates) == 2, where


def expect_bridge_error(module: types.ModuleType, fn: Callable[[], Any], where: str) -> None:
    try:
        fn()
    except module.BridgeError:
        return
    raise AssertionError(f"{where}: no BridgeError")


def guard_other_query_errors_surface(module: types.ModuleType, tmp_path: Path) -> None:
    from hmp_plugin import local_media_sidecar as sidecar

    def boom(*a: Any) -> None:
        raise RuntimeError("private")

    for _, media_name in METHOD_PAIRS:
        world, directory, ref = case_world(tmp_path / media_name, "plain")
        br = new_bridge(module, world, directory)
        with patched(sidecar, "MediaRowsQuery", boom):
            expect_bridge_error(module, lambda: call_twin(br, media_name, ref), media_name)  # noqa: B023


def guard_candidate_invariant_surfaces(module: types.ModuleType, tmp_path: Path) -> None:
    from hmp_plugin import local_media_candidate as cand

    dup = MediaCandidate(1, b"\x00" * 32)
    for _, media_name in METHOD_PAIRS:
        world, directory, ref = case_world(tmp_path / media_name, "plain")
        br = new_bridge(module, world, directory)
        with patched(cand, "collect_candidates", lambda *a: (dup, dup)):
            expect_bridge_error(module, lambda: call_twin(br, media_name, ref), media_name)  # noqa: B023


def guard_invalid_raw_fails_equivalently(module: types.ModuleType, tmp_path: Path) -> None:
    from hmp_plugin import local_media_active_scan as scan

    seen: list[str] = []
    with (
        patched(scan, "_parse_image", lambda *a: seen.append("parse")),
        counting_collector() as collected,
    ):
        for bad in ({"rows": []}, [object()], "text"):
            for old, media, args in (
                ("latest", "latest_with_media", (REF, 5)),
                ("after", "after_with_media", (REF, 0, 5)),
            ):
                outcomes = []
                for name in (old, media):
                    world, directory = make_world(tmp_path / f"{name}{id(bad)}")
                    world.dbs["alpha"].get_messages = lambda *a, _b=bad, **k: _b  # type: ignore[method-assign,misc]
                    br = new_bridge(module, world, directory)
                    try:
                        getattr(br, name)(*args)
                    except module.BridgeError as exc:
                        outcomes.append(str(exc))
                    else:
                        raise AssertionError(f"{name}: no BridgeError")
                    assert world.api.acquired == world.api.released == 1
                assert outcomes[0] == outcomes[1]
    assert seen == [] and collected == []


def guard_old_methods_release_before_rows(module: types.ModuleType, tmp_path: Path) -> None:
    """The old methods convert only after release: nothing converts inside the database context."""
    for name, args in (("latest", (REF, 5)), ("after", (REF, 0, 5)), ("after", (REF, 2, 5))):
        world, directory = make_world(tmp_path / f"{name}{args[1:]}")
        seed(world)
        rec, br = Recorder(world), new_bridge(module, world, directory)
        real_rows = br._rows
        br._rows = lambda *a: (rec.events.append("rows"), real_rows(*a))[1]  # noqa: B023
        getattr(br, name)(*args)
        last_query = max(i for i, e in enumerate(rec.events) if e[0] == "get_messages")
        assert rec.events[last_query + 1 :] == ["release", "rows"], (name, args)
        assert rec.events.count("rows") == 1, (name, args)


def guard_invalid_raw_twin_loads_no_media(module_path: Path) -> None:
    """Fresh interpreter: the media twin on invalid raw rows fails before loading any media module
    (the old path's failure, with the old path's module set)."""
    code = (
        "import sys, importlib.util, tempfile, pathlib\n"
        "from hmp_plugin.contract import ConversationRef\n"
        "from tests.unit.fake_hermes import FakeDirectory, World\n"
        f"path = {str(module_path)!r}\n"
        "spec = importlib.util.spec_from_file_location('hmp_plugin._probe_bridge', path)\n"
        "m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m\n"
        "spec.loader.exec_module(m)\n"
        "def media(): return sorted(x for x in sys.modules if 'local_media_' in x)\n"
        "w, d = World(pathlib.Path(tempfile.mkdtemp())), FakeDirectory()\n"
        "u = 'hmpu_' + 'a' * 32\n"
        "d.chats[(u, 'alpha')] = 'c_' + '1' * 32\n"
        "w.start_conversation('alpha', 'c_' + '1' * 32, 's1')\n"
        "w.dbs['alpha'].get_messages = lambda *a, **k: {'rows': []}\n"
        "b = m.HermesReadBridge(w.adapter, d, hermes=w.api)\n"
        "r = ConversationRef(u, 'alpha', 's1')\n"
        "for call in (lambda: b.latest_with_media(r, 5), lambda: b.after_with_media(r, 0, 5)):\n"
        "    try:\n"
        "        call()\n"
        "    except m.BridgeError:\n"
        "        pass\n"
        "    else:\n"
        "        raise SystemExit('no BridgeError')\n"
        "    assert not media(), media()\n"
    )
    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent)}
    done = subprocess.run(
        [sys.executable, "-B", "-c", code],
        env=env,
        cwd=PACKAGE.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-600:] or done.stdout[-200:]


GUARDS: dict[str, Callable[[types.ModuleType, Path], None]] = {
    "native_logs_equal": guard_native_logs_equal,
    "golden_log": guard_golden_log,
    "same_home_once": guard_same_home_once,
    "exact_query_tip": guard_exact_query_tip,
    "candidate_after_cap": guard_candidate_after_cap,
    "filtering": guard_filtering,
    "downgrade_returns_old_result": guard_downgrade_returns_old_result,
    "boundaries_stay_media": guard_boundaries_stay_media,
    "other_query_errors_surface": guard_other_query_errors_surface,
    "candidate_invariant_surfaces": guard_candidate_invariant_surfaces,
    "invalid_raw_equivalent": guard_invalid_raw_fails_equivalently,
    "old_release_before_rows": guard_old_methods_release_before_rows,
}


@pytest.mark.parametrize("name", sorted(GUARDS))
def test_guard_passes_on_real_bridge(name: str, tmp_path: Path) -> None:
    GUARDS[name](real_bridge, tmp_path)


def test_real_bridge_is_inert_at_startup(tmp_path: Path) -> None:
    guard_module_inertness(BRIDGE_PATH)


# --------------------------------------------------------------------------------------------------
# Out-of-tree mutants: each must fail its causal guard (and pass nothing silently).
# --------------------------------------------------------------------------------------------------


def load_mutant(tmp_path: Path, old: str, new: str, tag: str) -> tuple[types.ModuleType, Path]:
    assert BRIDGE_SOURCE.count(old) >= 1, f"mutation anchor missing for {tag}"
    path = tmp_path / f"bridge_{tag}.py"
    path.write_text(BRIDGE_SOURCE.replace(old, new, 1), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"hmp_plugin._mut_{tag}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module, path


# (tag, anchor, replacement, guard that must fail)
MUTANTS = [
    (
        "home_double_query",
        "os.fspath(home)",
        "os.fspath(self._profile_home(ref.profile))",
        "same_home_once",
    ),
    (
        "tip_double_query",
        "        return home, tip, rows\n",
        "        with self._db(ref.profile) as d2:\n"
        "            tip = self._tip(d2, ref.session_id)\n"
        "        return home, tip, rows\n",
        "exact_query_tip",
    ),
    (
        "cap_before_extraction",
        "collect_candidates(raw,",
        "collect_candidates([{'id': r.id, 'role': r.role, 'tool_name': r.tool_name, "
        "'tool_call_id': r.tool_call_id, 'content': r.text} for r in parsed],",
        "candidate_after_cap",
    ),
    (
        "filter_drops_all",
        'r.id for r in parsed if r.role == "tool"',
        'r.id for r in parsed if r.role == "never"',
        "filtering",
    ),
    (
        "filter_newest_only",
        "r.id for r in parsed if",
        "r.id for r in parsed[-1:] if",
        "filtering",
    ),
    (
        "media_arg_drift",
        "self._media_rows(ref, self._latest_query(ref, limit))",
        "self._media_rows(ref, self._latest_query(ref, limit + 1))",
        "native_logs_equal",
    ),
    (
        "core_arg_drift",
        "db.get_messages(tip, latest=True, limit=limit)\n        return",
        "db.get_messages(tip, latest=True, limit=limit + 1)\n        return",
        "golden_log",
    ),
    (
        "probe_arg_drift",
        "after_id=after_id - 1, limit=1",
        "after_id=after_id, limit=1",
        "golden_log",
    ),
    # S2c.1: catch scope, count bound, identity of the returned list, order, and the old methods.
    (
        "downgrade_catch_removed",
        "        except MediaCarrierRefusal:\n            return parsed",
        "        except ZeroDivisionError:\n            return parsed",
        "downgrade_returns_old_result",
    ),
    (
        "downgrade_catch_broad",
        "        except MediaCarrierRefusal:\n            return parsed",
        "        except Exception:\n            return parsed",
        "other_query_errors_surface",
    ),
    (
        "downgrade_metadata_copy",
        "        except MediaCarrierRefusal:\n            return parsed",
        "        except MediaCarrierRefusal:\n            return list(parsed)",
        "downgrade_returns_old_result",
    ),
    (
        "downgrade_metadata_tuple",
        "        except MediaCarrierRefusal:\n            return parsed",
        "        except MediaCarrierRefusal:\n            return tuple(parsed)",
        "downgrade_returns_old_result",
    ),
    (
        "downgrade_count_copy",
        "MAX_ROWS:\n            return parsed",
        "MAX_ROWS:\n            return list(parsed)",
        "downgrade_returns_old_result",
    ),
    (
        "downgrade_count_tuple",
        "MAX_ROWS:\n            return parsed",
        "MAX_ROWS:\n            return tuple(parsed)",
        "downgrade_returns_old_result",
    ),
    (
        "count_bound_ge",
        "len(parsed) > MAX_ROWS",
        "len(parsed) >= MAX_ROWS",
        "boundaries_stay_media",
    ),
    (
        "count_bound_off_by_one_high",
        "len(parsed) > MAX_ROWS",
        "len(parsed) > MAX_ROWS + 1",
        "downgrade_returns_old_result",
    ),
    (
        "count_downgrade_removed",
        "        if len(parsed) > MAX_ROWS:\n            return parsed\n",
        "",
        "downgrade_returns_old_result",
    ),
    (
        "collect_before_count_downgrade",
        "        if len(parsed) > MAX_ROWS:\n",
        "        collect_candidates(raw, os.fspath(home), frozenset())\n"
        "        if len(parsed) > MAX_ROWS:\n",
        "downgrade_returns_old_result",
    ),
    (
        "collect_before_metadata_downgrade",
        "        try:\n            media_query",
        "        collect_candidates(raw, os.fspath(home), frozenset())\n"
        "        try:\n            media_query",
        "downgrade_returns_old_result",
    ),
    (
        "construction_inside_catch",
        "        return BridgeMediaRows(tuple(parsed), media_query, candidates)",
        "        try:\n"
        "            return BridgeMediaRows(tuple(parsed), media_query, candidates)\n"
        "        except MediaCarrierRefusal:\n"
        "            return parsed",
        "candidate_invariant_surfaces",
    ),
    (
        "catch_around_rows",
        "        parsed = self._rows(ref, raw)",
        "        try:\n            parsed = self._rows(ref, raw)\n"
        "        except BridgeError:\n            return []",
        "invalid_raw_equivalent",
    ),
    (
        "old_latest_rows_inside_context",
        "            rows = db.get_messages(tip, latest=True, limit=limit)\n        return home",
        "            rows = db.get_messages(tip, latest=True, limit=limit)\n"
        "            self._rows(ref, rows)\n        return home",
        "old_release_before_rows",
    ),
    (
        "old_after_rows_inside_context",
        "            rows = db.get_messages(tip, after_id=after_id, limit=limit)\n"
        "        return home",
        "            rows = db.get_messages(tip, after_id=after_id, limit=limit)\n"
        "            self._rows(ref, rows)\n        return home",
        "old_release_before_rows",
    ),
]


@pytest.mark.parametrize(("tag", "old", "new", "guard"), MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_fails_its_causal_guard(
    tag: str, old: str, new: str, guard: str, tmp_path: Path
) -> None:
    module, _ = load_mutant(tmp_path, old, new, tag)
    with pytest.raises(AssertionError):
        GUARDS[guard](module, tmp_path / "run")


def test_mutant_import_at_module_scope_fails_inertness(tmp_path: Path) -> None:
    anchor = "from .logging_policy import log_bridge_exception, log_event\n"
    path = tmp_path / "bridge_modscope.py"
    path.write_text(
        BRIDGE_SOURCE.replace(
            anchor, anchor + "from .local_media_sidecar import MediaCandidate as _M\n", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        guard_module_inertness(path)


def test_invalid_raw_twin_loads_no_media_modules() -> None:
    guard_invalid_raw_twin_loads_no_media(BRIDGE_PATH)


def test_mutant_media_import_before_conversion_fails_f2(tmp_path: Path) -> None:
    _, path = load_mutant(
        tmp_path,
        "        parsed = self._rows(ref, raw)",
        "        from .local_media_candidate import collect_candidates as _early  # noqa: F401\n"
        "        parsed = self._rows(ref, raw)",
        "early_import",
    )
    with pytest.raises(AssertionError):
        guard_invalid_raw_twin_loads_no_media(path)


# --------------------------------------------------------------------------------------------------
# Behavior
# --------------------------------------------------------------------------------------------------


def test_release_before_conversion_and_extraction(tmp_path: Path, monkeypatch: Any) -> None:
    from hmp_plugin import local_media_candidate as cand

    world, directory = make_world(tmp_path)
    seed(world)
    rec, br = Recorder(world), new_bridge(real_bridge, world, directory)
    real_rows, real_collect = br._rows, cand.collect_candidates
    br._rows = lambda *a: (rec.events.append("rows"), real_rows(*a))[1]
    monkeypatch.setattr(
        cand, "collect_candidates", lambda *a: (rec.events.append("extract"), real_collect(*a))[1]
    )
    br.latest_with_media(REF, 5)
    assert rec.events[-3:] == ["release", "rows", "extract"]
    rec.events.clear()
    br.after_with_media(REF, 0, 5)
    assert rec.events[-3:] == ["release", "rows", "extract"]


@pytest.mark.parametrize("method", ["latest_with_media", "after_with_media", "latest", "after"])
def test_release_on_native_exception(method: str, tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    seed(world)
    world.dbs["alpha"].fail = True
    br = new_bridge(real_bridge, world, directory)
    args = (REF, 5) if method.startswith("latest") else (REF, 0, 5)
    with pytest.raises(BridgeError):
        getattr(br, method)(*args)
    assert world.api.acquired == world.api.released == 1


def test_invalid_raw_fails_equivalently_before_parsing(tmp_path: Path) -> None:
    guard_invalid_raw_fails_equivalently(real_bridge, tmp_path)


def test_downgrade_preserves_the_exact_old_text_read(tmp_path: Path) -> None:
    """The positive control of the identity guard: the real bridge returns the very parsed list."""
    guard_downgrade_returns_old_result(real_bridge, tmp_path)


def test_collector_refuses_without_changing_rows(tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    home = world.runner.homes["alpha"]
    foreign = {"success": True, "image": "/elsewhere/cache/images/x.png"}
    tool(world, image_result(home, "gen_ok.png", pad=70_000))  # over the 64 KiB bound
    tool(world, json.dumps(foreign))  # outside the home
    tool(world, [{"type": "text", "text": image_result(home)}])  # list content
    tool(world, image_result(home, "../x.png"))  # not a flat name
    tool(world, image_result(home), name="other_tool")
    tool(world, "not json")
    br = new_bridge(real_bridge, world, directory)
    out = br.latest_with_media(REF, 20)
    assert out.candidates == ()
    assert list(out.rows) == br.latest(REF, 20) and len(out.rows) == 6


def test_collector_exception_leaves_rows_and_no_error(tmp_path: Path, monkeypatch: Any) -> None:
    from hmp_plugin import local_media_candidate as cand

    world, directory = make_world(tmp_path)
    seed(world)

    def boom(*a: Any) -> None:
        raise RuntimeError("private")

    monkeypatch.setattr(cand, "raw_tool_candidate", boom)
    br = new_bridge(real_bridge, world, directory)
    out = br.latest_with_media(REF, 10)
    assert out.candidates == () and list(out.rows) == br.latest(REF, 10)


def test_invalid_home_yields_empty_candidates_without_second_query(
    tmp_path: Path, monkeypatch: Any
) -> None:
    world, directory = make_world(tmp_path)
    seed(world)
    rec, br = Recorder(world), new_bridge(real_bridge, world, directory)
    fake_os = types.SimpleNamespace(
        fspath=lambda _h: "a\0b", PathLike=os.PathLike, environ=os.environ, getenv=os.getenv
    )
    monkeypatch.setattr(real_bridge, "os", fake_os)
    out = br.latest_with_media(REF, 10)
    assert out.candidates == () and len(out.rows) == 4
    assert [e for e in rec.events if e[0] == "_routed_profile_home"] == [
        ("_routed_profile_home", ("alpha",))
    ]


def test_home_captured_from_the_one_query(tmp_path: Path) -> None:
    """A second routed-home answer would differ; candidates must follow the first only."""
    world, directory = make_world(tmp_path)
    ids = seed(world)
    real_home = world.runner.homes["alpha"]
    answers = [real_home, tmp_path / "elsewhere"]
    world.runner._routed_profile_home = lambda _p: (
        answers.pop(0) if len(answers) > 1 else answers[0]
    )  # type: ignore[method-assign]
    out = new_bridge(real_bridge, world, directory).latest_with_media(REF, 10)
    assert [c.tool_row_id for c in out.candidates] == [ids[3], ids[1]]


def test_reset_is_returned_unchanged_with_no_extraction(tmp_path: Path, monkeypatch: Any) -> None:
    from hmp_plugin import local_media_candidate as cand

    monkeypatch.setattr(cand, "collect_candidates", lambda *a: pytest.fail("extracted"))
    world, directory = make_world(tmp_path)
    ids = seed(world)
    br = new_bridge(real_bridge, world, directory)
    assert br.after_with_media(REF, 999, 5) is ResetReason.CURSOR_NOT_RESOLVABLE
    world.dbs["alpha"].rows[1]["active"] = 0
    assert br.after_with_media(REF, ids[1], 5) is ResetReason.HISTORY_REWRITTEN


def test_only_reached_reads_and_no_writes(tmp_path: Path) -> None:
    world, directory = make_world(tmp_path)
    seed(world)
    br = new_bridge(real_bridge, world, directory)
    br.latest_with_media(REF, 5)
    br.after_with_media(REF, 1, 5)
    assert set(world.dbs["alpha"].calls) <= {
        "get_messages",
        "resolve_resume_session_id",
        "get_compression_chain",  # the fake resolver's own internal read
    }
    assert set(world.runner.calls) == {"_routed_profile_home"}
    assert (world.runner.calls.count("_routed_profile_home")) == 2  # one per call


def test_class_marker_is_a_real_classvar_only_on_the_bridge() -> None:
    assert real_bridge.HermesReadBridge.LOCAL_MEDIA_SIDECAR is True
    tree = ast.parse(BRIDGE_SOURCE)
    marker = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name)
        and n.target.id == "LOCAL_MEDIA_SIDECAR"
    ]
    assert len(marker) == 1 and "ClassVar" in ast.unparse(marker[0].annotation)


def test_carrier_never_escapes_to_wire_serialization(tmp_path: Path) -> None:
    from hmp_plugin import request_ctx

    world, directory = make_world(tmp_path)
    seed(world)
    out = new_bridge(real_bridge, world, directory).latest_with_media(REF, 5)
    assert out.candidates and isinstance(out.candidates[0], MediaCandidate)
    for carrier in (out, out.query, out.candidates[0]):
        assert not dataclasses.is_dataclass(carrier)
        assert not isinstance(carrier, Mapping | tuple | list)
        with pytest.raises(TypeError):
            wire.dump_json(request_ctx._plain(carrier))
        with pytest.raises(TypeError):
            wire.dump_json({"x": request_ctx._plain([carrier])})


def test_server_routes_cli_compat_remain_media_inert() -> None:
    for name in ("server.py", "routes.py", "cli.py", "compat.py"):
        text = (PACKAGE / name).read_text(encoding="utf-8")
        for needle in ("local_media", "_with_media", "LOCAL_MEDIA_SIDECAR"):
            assert needle not in text, f"{name}: {needle}"


def test_old_methods_still_use_read_wrapper_and_rows_after_release() -> None:
    """Static pin: the original wrappers keep `self._read(run)` and call `_rows` outside the
    database context (the cores return before conversion)."""
    tree = ast.parse(BRIDGE_SOURCE)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "HermesReadBridge")
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    for name in ("latest", "after", "latest_with_media", "after_with_media"):
        assert "self._read(run)" in ast.unparse(methods[name]), name
    for name in ("_latest_query", "_after_query"):
        for node in ast.walk(methods[name]):
            if isinstance(node, ast.With):
                assert "_rows" not in ast.unparse(node), name
