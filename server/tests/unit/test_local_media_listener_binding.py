"""S6b: local-media listener binding (adapter / request_ctx / bridge / reads).

Causal tests in isolated synthetic worlds (`media_listener_world.Synth`): a byte copy of the whole
package loaded under a unique name next to an invented "native" tree, driven through the copy's REAL
`open_components`, REAL `compat.default_gate` and REAL `local_media_gate`. No real native code runs,
no shipped manifest changes, and only the `isolated_anchor` fixture touches the private `sys` key.

Guard tests are written so that an OMITTED guard is detected: each guarded property is a function
that returns whether the property holds, asserted True for the real source and False for a MUTANT
copy (the copy's own source edited to drop exactly that guard). Nothing here consumes the media
callback in a route; no route exists yet.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import functools
import inspect
import logging
import sys
import threading
import time
import types
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from hmp_plugin import request_ctx as real_request_ctx

from .fake_hermes import FakeDirectory
from .media_listener_world import (
    KEY,
    PACKAGE,
    Synth,
)
from .media_listener_world import isolated_anchor as _anchor_snapshot


@pytest.fixture(autouse=True)
def _isolated_anchor() -> Iterator[None]:
    """The ONLY place the private `sys` key is snapshotted and restored (test-only; the product has
    no such path): every test starts with no anchor and the original is put back afterwards."""
    yield from _anchor_snapshot()


STEMS = (
    "adapter",
    "server",
    "request_ctx",
    "auth",
    "crypto",
    "contract",
    "reads",
    "authorize",
    "store",
    "compat",
    "wire",
    "logging_policy",
    "bridge",
    "local_media_gate",
    "local_media_sidecar",
    "local_media_candidate",
    "local_media_active_scan",
    "local_media_result",
    "local_media_file_safety",
    "local_media_active_batch",
    "local_media_batch_binding",
)
MEDIA_CHAIN = tuple(s for s in STEMS if s.startswith("local_media_") and s != "local_media_gate")
USER = "hmpu_" + "a" * 32
CHAT = "c_" + "1" * 32
READ_SRC = {p.name: p.read_text(encoding="utf-8") for p in PACKAGE.glob("*.py")}


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def cell_value() -> Any:
    anchor = sys.__dict__.get(KEY)
    return None if anchor is None else anchor[2][0]


def import_all(world: Synth) -> dict[str, types.ModuleType]:
    return {stem: world.mod(stem) for stem in STEMS}


def spy_gate(world: Synth, before: Any = None) -> SimpleNamespace:
    """Wrap the copy's gate factory (keeping `__wrapped__`, which the proof follows) and its
    preload. The gate module is imported here; a test that must see the gate NOT imported does not
    call this."""
    gate = world.mod("local_media_gate")
    original = gate.media_listener_qualifier
    log = SimpleNamespace(calls=[], preload_calls=0, preload_results=[], preload_errors=[])

    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        log.calls.append((args, tuple(kwargs)))
        preload = kwargs.get("preload")
        if before is not None and preload is not None:
            # Test-only: reach the (adapter, ctx) the preload closes over, AFTER the qualifier's own
            # pre-check and BEFORE any proof, to damage exactly one thing the preload must prove.
            cells = dict(
                zip(
                    preload.__code__.co_freevars,
                    (c.cell_contents for c in preload.__closure__),
                    strict=True,
                )
            )
            before(cells["adapter"], cells["ctx"])
        if preload is not None:

            def counted() -> Any:
                log.preload_calls += 1
                try:
                    out = preload()
                except BaseException as exc:
                    log.preload_errors.append(type(exc))
                    raise
                log.preload_results.append(out)
                return out

            kwargs["preload"] = counted
        return original(*args, **kwargs)

    gate.media_listener_qualifier = wrapper
    return log


def media_modules_in(world: Synth) -> list[str]:
    return sorted(
        n.rsplit(".", 1)[-1]
        for n in sys.modules
        if n.startswith(world.pkg + ".") and "local_media_" in n
    )


def owner(namespace: dict[str, Any]) -> types.ModuleType:
    found = [
        m
        for m in list(sys.modules.values())
        if isinstance(m, types.ModuleType) and vars(m) is namespace
    ]
    assert len(found) == 1
    return found[0]


class StoreCloses:
    """Counts `Store.close` of one copy without replacing anything the proofs look at."""

    def __init__(self, world: Synth, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        cls = world.mod("store").Store
        original = cls.close

        def close(this: Any) -> Any:
            self.count += 1
            return original(this)

        monkeypatch.setattr(cls, "close", close)


# --------------------------------------------------------------------------------------------
# Mutants: one source edit each, dropping exactly one guard
# --------------------------------------------------------------------------------------------

M_DROP_SUPPORTED = {
    "adapter.py": [
        (
            "        if result.supported is not True or type(result.identity) is not "
            "compat.BuildIdentity:\n",
            "        if type(result.identity) is not compat.BuildIdentity:\n",
        )
    ]
}
M_OUTER_SUPPORTED = {
    "adapter.py": [
        (
            "    if result.supported:\n        bridge_cls, directory_cls",
            "    if True:\n        bridge_cls, directory_cls",
        )
    ]
}
M_UNSUPPORTED_REACHES_GATE = {
    "adapter.py": [
        *M_OUTER_SUPPORTED["adapter.py"],
        *M_DROP_SUPPORTED["adapter.py"],
        (
            "        if type(result.identity) is not compat.BuildIdentity:\n",
            "        if False:\n",
        ),
    ]
}
M_DROP_IDENTITY_TYPE = {
    "adapter.py": [
        (
            "        if result.supported is not True or type(result.identity) is not "
            "compat.BuildIdentity:\n",
            "        if result.supported is not True:\n",
        )
    ]
}
M_DROP_PRECHECK = {
    "adapter.py": [
        (
            '            or vars(media_gate).get("compat") is not compat\n',
            "            or False\n",
        ),
        ("            or media_gate.__package__ != __package__\n", "            or False\n"),
    ]
}
M_DROP_BASEEXC = {
    "adapter.py": [
        (
            "        except BaseException:\n            store.close()\n            raise\n",
            "        except Exception:\n            store.close()\n            raise\n",
        )
    ]
}
M_EXTRA_KW = {
    "adapter.py": [
        (
            "media_gate.media_listener_qualifier(result.identity, preload=_preload)",
            "media_gate.media_listener_qualifier(result.identity, preload=_preload, "
            "read_compat_path=None)",
        )
    ]
}
M_DROP_SWEEP = {"adapter.py": [("            _media_sweep(named)\n", "            pass\n")]}
M_FLAG_TRUTHY = {
    "adapter.py": [
        (
            '        block = live_extra.get("local_media") if isinstance(live_extra, Mapping) '
            "else None\n"
            '        return isinstance(block, Mapping) and block.get("enabled") is True',
            '        block = live_extra.get("local_media") if isinstance(live_extra, Mapping) '
            "else None\n"
            '        return isinstance(block, Mapping) and bool(block.get("enabled"))',
        )
    ]
}
M_FLAG_GATES_FACTORY = {
    "adapter.py": [
        (
            "        from . import local_media_gate as media_gate\n",
            "        if not ctx.media_enabled():\n            return _media_closed\n"
            "        from . import local_media_gate as media_gate\n",
        )
    ]
}
M_CTX_TRUTHY = {
    "request_ctx.py": [
        (
            "            return self.media_flag() is True\n",
            "            return bool(self.media_flag())\n",
        ),
        (
            "            return self.media_qualified() is True\n",
            "            return bool(self.media_qualified())\n",
        ),
    ]
}
M_BRIDGE_LOCAL_IMPORT = {
    "bridge.py": [
        (
            "        BridgeMediaRows = sidecar.BridgeMediaRows  # noqa: N806\n",
            "        from .local_media_sidecar import BridgeMediaRows\n",
        )
    ]
}
M_READS_LOCAL_IMPORT = {
    "reads.py": [
        (
            "    BridgeMediaRows = _local_media_modules()[0].BridgeMediaRows  # noqa: N806\n",
            "    from .local_media_sidecar import BridgeMediaRows\n",
        )
    ]
}
M_BINDING_LOCAL_IMPORT = {
    "bridge.py": [
        (
            "        MediaSidecar = sidecar_module.MediaSidecar  # noqa: N806\n",
            "        from .local_media_sidecar import MediaSidecar\n",
        )
    ]
}
M_BRIDGE_IMPORTLIB_CANDIDATE = {
    "bridge.py": [
        (
            "        collect_candidates = candidate.collect_candidates\n",
            "        import importlib\n"
            "        collect_candidates = importlib.import_module(\n"
            "            __package__ + '.local_media_candidate'\n"
            "        ).collect_candidates\n",
        )
    ]
}
M_BINDING_IMPORTLIB_BATCH = {
    "bridge.py": [
        (
            "        scan_active_batch = modules[5].scan_active_batch\n",
            "        import importlib\n"
            "        scan_active_batch = importlib.import_module(\n"
            "            __package__ + '.local_media_active_batch'\n"
            "        ).scan_active_batch\n",
        )
    ]
}
M_UNWRAP_LIMIT_100 = {"adapter.py": [("_MEDIA_UNWRAP_LIMIT = 8\n", "_MEDIA_UNWRAP_LIMIT = 100\n")]}
M_UNWRAP_UNBOUNDED = {
    "adapter.py": [("    for _ in range(_MEDIA_UNWRAP_LIMIT + 1):\n", "    while True:\n")]
}
M_FLAG_CAPTURED_CONFIG = {
    "adapter.py": [
        (
            "    def _read_local_media_enabled() -> bool:\n"
            '        live_config = getattr(adapter, "config", None)\n',
            "    def _read_local_media_enabled() -> bool:\n        live_config = config\n",
        )
    ]
}
M_DROP_PACKAGE_PRECHECK = {
    "adapter.py": [("            or media_gate.__package__ != __package__\n", "")]
}
M_PRELOAD_EAGER_FILL = {
    "bridge.py": [
        (
            "_local_media_cache: tuple[ModuleType, ...] | None = None\n",
            "from . import local_media_sidecar as _eager  # noqa: E402\n\n"
            "_local_media_cache: tuple[ModuleType, ...] | None = None\n",
        )
    ]
}
M_PRELOAD_KEYBOARD_INTERRUPT = {
    "reads.py": [
        (
            "    from . import local_media_sidecar  # unlocked: only the set-once publication is "
            "locked\n",
            "    raise KeyboardInterrupt\n    from . import local_media_sidecar\n",
        )
    ]
}


# --------------------------------------------------------------------------------------------
# 1. Supported precondition: exact SUPPORTED + exact BuildIdentity before ANY gate import
# --------------------------------------------------------------------------------------------


def _untouched(world: Synth, ctx: Any) -> bool:
    return (
        f"{world.pkg}.local_media_gate" not in sys.modules
        and KEY not in sys.__dict__
        and ctx.media_qualified() is False
        and ctx.media_qualification_open() is False
        and media_modules_in(world) == []
    )


def _property_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any, kind: str
) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, supported_listing=(kind != "unlisted"))
    if kind == "deps_missing":
        world.mod("compat").probe_read_dependencies = lambda **_kw: ("synthetic.missing",)
    _, ctx = world.open()
    assert ctx.compat.supported is False and ctx.compat.identity is not None
    if ctx.bridge is not None:  # the supported block must not run for an unsupported result
        return False
    return _untouched(world, ctx)


@pytest.mark.parametrize("kind", ["unlisted", "deps_missing"])
def test_unsupported_with_identity_never_imports_the_gate_or_touches_the_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    assert _property_unsupported(tmp_path, monkeypatch, None, kind) is True


@pytest.mark.parametrize("kind", ["unlisted", "deps_missing"])
@pytest.mark.parametrize("mutant", [M_OUTER_SUPPORTED, M_UNSUPPORTED_REACHES_GATE])
def test_mutants_that_let_an_unsupported_result_reach_the_binding_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, mutant: Any
) -> None:
    assert _property_unsupported(tmp_path, monkeypatch, mutant, kind) is False


class _Truthy:
    def __bool__(self) -> bool:
        return True


def _fake_result(compat: Any, supported: Any, identity: Any) -> Any:
    return SimpleNamespace(supported=supported, identity=identity, status="x")


def _property_truthy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, supported_listing=False)
    adapter_mod = world.mod("adapter")
    adapter, ctx = world.open()
    compat = world.mod("compat")
    good = compat.BuildIdentity(fingerprint="a" * 64, git_sha=None)
    cases = [
        _fake_result(compat, 1, good),
        _fake_result(compat, "yes", good),
        _fake_result(compat, _Truthy(), good),
        _fake_result(compat, [1], good),
        _fake_result(compat, True, None),  # supported but no identity
        _fake_result(compat, True, SimpleNamespace(fingerprint="a" * 64, git_sha=None)),
        _fake_result(compat, True, ("a" * 64, None)),
    ]
    for case in cases:
        if adapter_mod._media_qualifier(adapter, ctx, case) is not adapter_mod._media_closed:
            return False
    return _untouched(world, ctx)


def test_truthy_and_malformed_supported_results_close_without_importing_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_truthy(tmp_path, monkeypatch, None) is True


@pytest.mark.parametrize("mutant", [M_DROP_SUPPORTED, M_DROP_IDENTITY_TYPE])
def test_mutants_that_accept_truthy_or_malformed_results_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: Any
) -> None:
    assert _property_truthy(tmp_path, monkeypatch, mutant) is False


# --------------------------------------------------------------------------------------------
# 2. Shipped empty manifest: one call, identity + preload only, no preload, latched closed
# --------------------------------------------------------------------------------------------


def _factory_call_shape_is_exact(source: str) -> bool:
    """Exactly one call to `media_listener_qualifier`, one positional (the identity), the single
    keyword `preload`, and no `*args`/`**kwargs`."""
    calls = [
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "media_listener_qualifier"
    ]
    if len(calls) != 1:
        return False
    call = calls[0]
    return (
        len(call.args) == 1
        and not isinstance(call.args[0], ast.Starred)
        and [k.arg for k in call.keywords] == ["preload"]
    )


def _property_empty_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, manifest_entry=False)
    log = spy_gate(world)
    adapter, ctx = world.open()
    ok = (
        len(log.calls) == 1
        and len(log.calls[0][0]) == 1
        and log.calls[0][1] == ("preload",)
        and log.preload_calls == 0  # an empty manifest never preloads or imports anything
        and cell_value() == "closed"
        and ctx.media_qualification_open() is False
    )
    # A later-added entry stays closed until a full process restart.
    world.manifest_entry = True
    world.write_lists()
    _, ctx2 = world.open(adapter)
    return bool(ok and ctx2.media_qualification_open() is False and cell_value() == "closed")


def test_shipped_empty_manifest_calls_the_factory_once_and_latches_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_empty_manifest(tmp_path, monkeypatch, None) is True
    assert _factory_call_shape_is_exact(READ_SRC["adapter.py"])


def test_mutant_factory_with_an_extra_keyword_is_detected_by_the_ast_pin() -> None:
    mutated = READ_SRC["adapter.py"].replace(*M_EXTRA_KW["adapter.py"][0])
    assert mutated != READ_SRC["adapter.py"]
    assert _factory_call_shape_is_exact(mutated) is False


def test_the_shipped_manifest_in_the_repository_is_still_empty() -> None:
    import json

    raw = json.loads((PACKAGE / "local_media_supported_builds.json").read_text(encoding="utf-8"))
    assert raw["builds"] == []


# --------------------------------------------------------------------------------------------
# 3. Actual objects: every returned module is the one the listener really runs
# --------------------------------------------------------------------------------------------


def _bridge_with_fake_directory(ctx: Any, world: Synth) -> Any:
    directory = FakeDirectory()
    directory.chats[(USER, "alpha")] = CHAT
    return type(ctx.bridge)(SimpleNamespace(), directory, hermes=object())


def _media_page(bridge: Any, world: Synth) -> Any:
    ref = world.mod("contract").ConversationRef(USER, "alpha", "s1")
    query = (Path("/nonexistent-home"), "tip1", [])
    return bridge._media_rows(ref, query)


def test_admission_returns_exactly_the_objects_the_listener_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = Synth(tmp_path, monkeypatch)
    log = spy_gate(world)
    adapter, ctx = world.open()
    assert len(log.preload_results) == 1
    (returned,) = log.preload_results
    assert type(returned) is tuple and len(returned) == len(STEMS)
    assert all(type(m) is types.ModuleType for m in returned)
    by_stem = {m.__name__.rsplit(".", 1)[-1]: m for m in returned}
    assert set(by_stem) == set(STEMS) and len({id(m) for m in returned}) == len(STEMS)

    # Oracle: modules owning the namespaces of functions the listener actually executes.
    adapter_cls = type(adapter)
    runtime = {
        "adapter": owner(adapter_cls.connect.__globals__),
        "request_ctx": owner(type(ctx).media_qualification_open.__globals__),
        "reads": owner(type(ctx.reads)._media_result.__globals__),
        "authorize": owner(type(ctx.authorize).authorize.__globals__),
        "store": owner(type(ctx.store).owner_controls_decision.__globals__),
        "bridge": owner(type(ctx.bridge)._media_rows.__globals__),
        "compat": owner(type(ctx.compat).supported.fget.__globals__),
        "local_media_gate": owner(ctx.media_qualified.__globals__),
    }
    request_ctx_mod = runtime["request_ctx"]
    runtime["auth"] = owner(request_ctx_mod.Authenticator.authenticate.__globals__)
    runtime["crypto"] = vars(runtime["auth"])["crypto"]
    runtime["wire"] = request_ctx_mod.json_response.__globals__["wire"]
    runtime["logging_policy"] = owner(request_ctx_mod.log_event.__globals__)
    runtime["server"] = adapter_cls.connect.__globals__["server"]
    runtime["contract"] = sys.modules[request_ctx_mod.HmpError.__module__]
    for stem, module in runtime.items():
        assert by_stem[stem] is module, stem

    # The media chain is what the media sites really use: the carrier a bridge twin builds comes
    # from the returned sidecar, a binding result from the returned binding module.
    bridge = _bridge_with_fake_directory(ctx, world)
    page = _media_page(bridge, world)
    assert type(page) is by_stem["local_media_sidecar"].BridgeMediaRows
    sidecar = by_stem["local_media_sidecar"]
    empty = sidecar.MediaSidecar(
        status=sidecar.SidecarStatus.NO_ROWS,
        origin=sidecar.MediaOrigin("own_conversation"),
        user_id=USER,
        profile="alpha",
        session_id=None,
        query_tip=None,
        lineage_tip=None,
        candidates=(),
    )
    binding = ctx.bridge.bind_media_batch(empty)
    assert type(binding) is by_stem["local_media_batch_binding"].MediaBatchBinding
    assert vars(runtime["bridge"])["_local_media_cache"] == tuple(by_stem[s] for s in MEDIA_CHAIN)
    assert vars(runtime["reads"])["_local_media_cache"] == (sidecar,)

    # The cell is the baseline and the callback is True.
    assert isinstance(cell_value(), tuple) and cell_value()[0] == "b1"
    assert ctx.media_qualification_open() is True


# --------------------------------------------------------------------------------------------
# 4. Origin under reload: an old listener keeps its own objects and its text bytes
# --------------------------------------------------------------------------------------------


CANDIDATE_HOME = "/synthetic-home"


def _candidate_rows() -> list[dict[str, Any]]:
    """A user row and one strict `image_generate` tool row naming a lexically valid cache file under
    `CANDIDATE_HOME`. Nothing is read from disk: candidate derivation is lexical only."""
    content = '{"success": true, "image": "' + CANDIDATE_HOME + '/cache/images/gen_a.png"}'
    return [
        {"id": 1, "role": "user", "content": "hello", "timestamp": 1.5},
        {
            "id": 2,
            "role": "tool",
            "content": content,
            "tool_name": "image_generate",
            "tool_call_id": "call_2",
            "timestamp": 2.0,
        },
    ]


def _property_old_listener_survives_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any
) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits)
    _, ctx = world.open()
    old = import_all(world)
    bridge_cache, reads_cache = old["bridge"]._local_media_cache, old["reads"]._local_media_cache
    assert bridge_cache is not None and reads_cache is not None
    bridge = _bridge_with_fake_directory(ctx, world)
    raw = _candidate_rows()
    ref = old["contract"].ConversationRef(USER, "alpha", "s1")
    text_before = old["wire"].dump_json(old["request_ctx"]._plain(bridge._rows(ref, raw)))

    world.reload()  # Hermes's whole-package eviction + a second load of the same directory
    new = import_all(world)
    assert all(new[s] is not old[s] for s in STEMS)  # really a different copy of everything
    ok = old["bridge"]._local_media_cache is bridge_cache  # never refilled
    ok = ok and old["reads"]._local_media_cache is reads_cache
    ok = ok and new["bridge"]._local_media_cache is None  # the new load has its own, unfilled
    try:
        # A mixed-copy carrier is refused by its constructor. The page holds a real candidate, so
        # the candidate chain (not an empty-page early exit) ran through the OLD cache.
        page = bridge._media_rows(ref, (Path(CANDIDATE_HOME), "tip1", raw))
        ok = ok and type(page) is old["local_media_sidecar"].BridgeMediaRows
        ok = ok and len(page.candidates) >= 1
        old["reads"]._accept_media(page, allow_reset=False)  # old cached carrier still accepted
    except Exception:
        return False
    return bool(
        ok
        and _old_binding_reaches_the_old_batch(bridge, old, page)
        and _text_same(old, bridge, ref, raw, text_before)
    )


def _text_same(old: Any, bridge: Any, ref: Any, raw: Any, text_before: Any) -> bool:
    text_after = old["wire"].dump_json(old["request_ctx"]._plain(bridge._rows(ref, raw)))
    return bool(text_after == text_before)


def _old_binding_reaches_the_old_batch(bridge: Any, old: Any, page: Any) -> bool:
    """`bind_media_batch` over a CANDIDATES sidecar must run the batch scan of the OLD cached batch
    module. A spy stands in for that cached scan; the native database, home and eligibility proofs
    are replaced by bounded fixtures so no native code or file is touched. Both the NO_ROWS early
    return and an importlib-obtained scan function would leave the spy uncalled."""
    sidecar = old["local_media_sidecar"]
    batch, binding_mod = old["local_media_active_batch"], old["local_media_batch_binding"]
    calls: list[tuple[Any, ...]] = []

    def spy(db: Any, tip: Any, selectors: Any, **kw: Any) -> Any:
        calls.append((tip, selectors, tuple(kw)))
        return SimpleNamespace(
            ok=True, accepted=(2,), stats=(("a", 0), ("b", 0), ("c", 0), ("d", 0))
        )

    candidates = page.candidates
    withheld = sidecar.MediaSidecar(
        status=sidecar.SidecarStatus.CANDIDATES,
        origin=sidecar.MediaOrigin("own_conversation"),
        user_id=USER,
        profile="alpha",
        session_id="s1",
        query_tip="tip1",
        lineage_tip="tip1",
        candidates=candidates,
    )
    original = batch.scan_active_batch
    batch.scan_active_batch = spy
    bridge._db_home = lambda profile: contextlib.nullcontext((Path(CANDIDATE_HOME), object()))
    kind = binding_mod.MintKind.BOT_CHAT
    bridge.media_eligibility = lambda *a: (binding_mod.OK, kind, "tip1")
    try:
        result = bridge.bind_media_batch(withheld)
    except Exception:
        return False
    finally:
        batch.scan_active_batch = original
        del bridge._db_home, bridge.media_eligibility
    return bool(
        len(calls) == 1
        and calls[0][0] == "tip1"
        and type(result) is binding_mod.MediaBatchBinding
        and result.ok
        and result.accepted == (2,)
    )


def test_old_listener_keeps_its_cache_objects_and_text_bytes_after_package_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_old_listener_survives_reload(tmp_path, monkeypatch, None) is True


@pytest.mark.parametrize(
    "mutant",
    [
        M_BRIDGE_LOCAL_IMPORT,
        M_READS_LOCAL_IMPORT,
        M_BINDING_LOCAL_IMPORT,
        M_BRIDGE_IMPORTLIB_CANDIDATE,
        M_BINDING_IMPORTLIB_BATCH,
    ],
)
def test_restoring_a_function_local_or_dynamic_media_import_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: Any
) -> None:
    assert _property_old_listener_survives_reload(tmp_path, monkeypatch, mutant) is False


# --------------------------------------------------------------------------------------------
# 5. Split detection: a swapped same-name copy closes; a swapped gate never reaches the factory
# --------------------------------------------------------------------------------------------


def _two_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any = None
) -> tuple[Synth, dict[str, types.ModuleType], dict[str, types.ModuleType]]:
    """`(world, donor, live)`: a first load's module objects kept as foreign same-name donors, and a
    second (current) load that the listener under test is built from."""
    world = Synth(tmp_path, monkeypatch, edits=edits)
    donor = import_all(world)
    world.reload()
    return world, donor, import_all(world)


def _set(module: types.ModuleType, name: str, value: Any) -> None:
    assert hasattr(module, name), name
    setattr(module, name, value)


def _first_bridge_fill_from_donor(live: Any, donor: Any) -> None:
    live["adapter"]._bridge_module_cache = donor["bridge"]
    live["adapter"]._bridge_classes_cache = (
        donor["bridge"].HermesReadBridge,
        donor["bridge"].StoreDirectory,
    )


SPLITS = {
    "request_ctx": lambda live, donor: _set(live["adapter"], "request_ctx", donor["request_ctx"]),
    "auth": lambda live, donor: _set(live["adapter"], "auth", donor["auth"]),
    "hmp_error": lambda live, donor: _set(
        live["authorize"], "HmpError", donor["contract"].HmpError
    ),
    "bridge_module": _first_bridge_fill_from_donor,
    "reads_vs_bridge_sidecar": lambda live, donor: _set(
        live["reads"], "_local_media_cache", (donor["local_media_sidecar"],)
    ),
    "candidate_scan": lambda live, donor: _set(
        live["local_media_candidate"], "_scan", donor["local_media_active_scan"]
    ),
}
# Edges only the sweep sees (no hand-written edge table): a module, a function and a class of one
# member that name another member but belong to another copy.
SWEEP_ONLY = {
    "module_edge": lambda live, donor: _set(live["authorize"], "crypto", donor["crypto"]),
    "function_edge": lambda live, donor: _set(
        live["reads"], "log_bridge_exception", donor["logging_policy"].log_bridge_exception
    ),
    "class_edge": lambda live, donor: _set(
        live["local_media_candidate"], "MediaCandidate", donor["local_media_sidecar"].MediaCandidate
    ),
}


def _property_split_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: Any, edits: Any = None
) -> bool:
    world, donor, live = _two_loads(tmp_path, monkeypatch, edits)
    log = spy_gate(world)
    if tamper is not None:
        tamper(live, donor)
    _, ctx = world.open()
    closed = ctx.media_qualification_open() is False and cell_value() == "closed"
    if tamper is None:  # control: the same two-load setup, untouched, admits
        return bool(
            ctx.media_qualification_open() is True
            and isinstance(cell_value(), tuple)
            and log.preload_errors == []
        )
    return bool(closed and len(log.calls) == 1)


def test_untouched_two_load_world_admits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _property_split_closes(tmp_path, monkeypatch, None) is True


@pytest.mark.parametrize("name", sorted({**SPLITS, **SWEEP_ONLY}))
def test_a_swapped_copy_closes_and_latches_the_first_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    assert _property_split_closes(tmp_path, monkeypatch, {**SPLITS, **SWEEP_ONLY}[name]) is True


@pytest.mark.parametrize("name", sorted(SWEEP_ONLY))
def test_mutant_without_the_sweep_admits_a_swapped_edge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    assert _property_split_closes(tmp_path, monkeypatch, SWEEP_ONLY[name], M_DROP_SWEEP) is False


def _property_wrong_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world, donor, _ = _two_loads(tmp_path, monkeypatch, edits)
    donor_log = SimpleNamespace(calls=[])
    donor_gate = donor["local_media_gate"]
    original = donor_gate.media_listener_qualifier

    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        donor_log.calls.append(args)
        return original(*args, **kwargs)

    donor_gate.media_listener_qualifier = wrapper
    world.package.local_media_gate = donor_gate  # what `from . import ...` resolves to
    _, ctx = world.open()
    return bool(
        ctx.media_qualification_open() is False and donor_log.calls == [] and cell_value() is None
    )


def test_a_wrong_gate_copy_never_reaches_the_factory_and_never_latches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_wrong_gate(tmp_path, monkeypatch, None) is True


def test_mutant_without_the_gate_precheck_calls_the_factory_and_latches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_wrong_gate(tmp_path, monkeypatch, M_DROP_PRECHECK) is False


def _property_package_mismatch_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any
) -> bool:
    """A gate that is the very same-compat module but reports another `__package__` must never reach
    the factory or move the cell. Only the package half of the pre-check can refuse it: the
    `vars(gate)["compat"] is compat` half holds here. A control with the package restored must reach
    the factory, so the setup is not vacuous."""
    world = Synth(tmp_path, monkeypatch, edits=edits, supported_listing=False)
    adapter_mod = world.mod("adapter")
    adapter, ctx = world.open()  # unsupported: no gate import, no factory
    compat = world.mod("compat")
    log = spy_gate(world)
    gate = world.mod("local_media_gate")
    assert vars(gate)["compat"] is compat  # only `__package__` differs below
    result = SimpleNamespace(
        supported=True, identity=compat.BuildIdentity(fingerprint="a" * 64, git_sha=None)
    )
    original = gate.__package__
    gate.__package__ = original + "_other"
    refused = adapter_mod._media_qualifier(adapter, ctx, result) is adapter_mod._media_closed
    refused = refused and log.calls == [] and cell_value() is None
    gate.__package__ = original
    adapter_mod._media_qualifier(adapter, ctx, result)
    return bool(refused and len(log.calls) == 1)


def test_a_gate_with_another_package_alone_never_reaches_the_factory_or_the_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_package_mismatch_alone(tmp_path, monkeypatch, None) is True


def test_mutant_without_the_package_half_of_the_precheck_reaches_the_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_package_mismatch_alone(tmp_path, monkeypatch, M_DROP_PACKAGE_PRECHECK) is False


class _WatchedDict(dict):  # type: ignore[type-arg]
    """A function `__dict__` that counts `get` calls and fails loudly on a runaway unwrap, so a
    mutant with an unbounded loop ends this test with an error instead of hanging the process."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.gets = 0

    def get(self, key: Any, default: Any = None) -> Any:
        self.gets += 1
        if self.gets > 64:
            raise AssertionError("unbounded unwrap")
        return super().get(key, default)


def _wrapped_chain(steps: int) -> tuple[Any, Any]:
    def base() -> None:
        return None

    top: Any = base
    for _ in range(steps):

        def wrapper() -> None:
            return None

        wrapper.__wrapped__ = top  # type: ignore[attr-defined]
        top = wrapper
    return top, base


def _property_unwrap_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    """Exactly eight `__wrapped__` steps unwrap to the base function, nine and a self-cycle are
    refused with the split error, and none of it can loop without bound."""
    world = Synth(tmp_path, monkeypatch, edits=edits, load=True)
    adapter_mod = world.mod("adapter")
    unwrap, split = adapter_mod._media_function, adapter_mod._MediaSplitError
    try:
        top, base = _wrapped_chain(8)
        if unwrap(top) is not base:
            return False
        if unwrap(base) is not base or unwrap(functools.partial(base)) is not None:
            return False
        top, _ = _wrapped_chain(9)
        try:
            unwrap(top)
            return False
        except split:
            pass
        cycle, _ = _wrapped_chain(0)
        cycle.__dict__ = _WatchedDict()
        cycle.__dict__["__wrapped__"] = cycle  # a function that wraps itself
        try:
            unwrap(cycle)
            return False
        except split:
            pass
        return bool(cycle.__dict__.gets <= adapter_mod._MEDIA_UNWRAP_LIMIT + 1)
    except Exception:  # a runaway unwrap (AssertionError) or an unexpected error is a failure
        return False


def test_unwrap_follows_exactly_eight_steps_and_refuses_nine_and_a_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_unwrap_bound(tmp_path, monkeypatch, None) is True


@pytest.mark.parametrize("mutant", [M_UNWRAP_LIMIT_100, M_UNWRAP_UNBOUNDED])
def test_mutants_that_raise_or_remove_the_unwrap_bound_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: Any
) -> None:
    assert _property_unwrap_bound(tmp_path, monkeypatch, mutant) is False


# --------------------------------------------------------------------------------------------
# 6. Stale home: two plugin directories over one native root
# --------------------------------------------------------------------------------------------


def test_a_second_plugin_directory_is_closed_and_sees_only_its_own_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = Synth(tmp_path, monkeypatch, "a")
    second = Synth(tmp_path, monkeypatch, "b", share=first)
    assert first.plugin != second.plugin and first.pkg != second.pkg
    log_second = spy_gate(second)

    _, ctx_a = first.open()
    assert ctx_a.media_qualification_open() is True
    fixed = cell_value()
    assert fixed[2] == str(first.plugin)

    _, ctx_b = second.open()
    assert ctx_b.media_qualification_open() is False  # a different plugin directory
    assert cell_value() == fixed  # the first baseline is untouched
    assert ctx_a.media_qualification_open() is True
    (returned,) = log_second.preload_results  # the second preload ran, over its own objects
    for module in returned:
        assert module is sys.modules[module.__name__]
        assert module.__name__.startswith(second.pkg + ".") or module.__name__ == second.pkg
        assert Path(module.__file__).parent == second.plugin


# --------------------------------------------------------------------------------------------
# 7. Init closure: with the empty manifest only the gate is loaded, both caches are empty
# --------------------------------------------------------------------------------------------


def _property_init_closure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, manifest_entry=False)
    _, ctx = world.open()
    return bool(
        media_modules_in(world) == ["local_media_gate"]
        and world.mod("bridge")._local_media_cache is None
        and world.mod("reads")._local_media_cache is None
        and ctx.bridge is not None
    )


def test_empty_manifest_loads_only_the_gate_and_fills_no_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_init_closure(tmp_path, monkeypatch, None) is True


def test_mutant_with_an_eager_media_import_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_init_closure(tmp_path, monkeypatch, M_PRELOAD_EAGER_FILL) is False


# --------------------------------------------------------------------------------------------
# 8. Default flag: exact True only, live, and independent of the factory
# --------------------------------------------------------------------------------------------

FLAG_CASES = [
    ({}, False),
    ({"local_media": None}, False),
    ({"local_media": "true"}, False),
    ({"local_media": 1}, False),
    ({"local_media": True}, False),
    ({"local_media": []}, False),
    ({"local_media": {}}, False),
    ({"local_media": {"enabled": "true"}}, False),
    ({"local_media": {"enabled": 1}}, False),
    ({"local_media": {"enabled": [True]}}, False),
    ({"local_media": {"enabled": False}}, False),
    ({"local_media": {"enabled": True}}, True),
]


def _property_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, manifest_entry=False)
    log = spy_gate(world)
    runs = 0
    for extra, expected in FLAG_CASES:
        adapter = world.adapter(extra)
        _, ctx = world.open(adapter)
        runs += 1
        if ctx.media_enabled() is not expected:
            return False
    if len(log.calls) != runs:  # the factory runs whatever the flag says
        return False
    # A live flip shows on the very next call and never repeats the factory.
    adapter = world.adapter({})
    _, ctx = world.open(adapter)
    calls = len(log.calls)
    adapter.config.extra["local_media"] = {"enabled": True}
    flipped_on = ctx.media_enabled() is True
    adapter.config.extra["local_media"] = {"enabled": "yes"}
    flipped_bad = ctx.media_enabled() is False
    adapter.config.extra.pop("local_media")
    in_place = flipped_on and flipped_bad and ctx.media_enabled() is False
    # Live means the CURRENT `adapter.config`, not the object `open_components` captured: replace
    # the whole config, then only its `extra` object, and follow each in both directions. Exact
    # True stays the only opening value.
    captured = adapter.config
    adapter.config = type(captured)({"local_media": {"enabled": True}})
    swapped_config_on = ctx.media_enabled() is True
    adapter.config = type(captured)({"local_media": {"enabled": "yes"}})
    swapped_config_bad = ctx.media_enabled() is False
    adapter.config = captured
    adapter.config.extra = {"local_media": {"enabled": True}}  # a new `extra` object
    swapped_extra_on = ctx.media_enabled() is True
    adapter.config.extra = {"local_media": {"enabled": 1}}
    swapped_extra_bad = ctx.media_enabled() is False
    adapter.config = None  # no config at all closes
    swapped = (swapped_config_on, swapped_config_bad, swapped_extra_on, swapped_extra_bad)
    return bool(
        in_place and all(swapped) and ctx.media_enabled() is False and len(log.calls) == calls
    )


def test_flag_is_exact_true_live_and_independent_of_the_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_flag(tmp_path, monkeypatch, None) is True


@pytest.mark.parametrize("mutant", [M_FLAG_TRUTHY, M_FLAG_GATES_FACTORY, M_FLAG_CAPTURED_CONFIG])
def test_mutants_of_the_flag_rules_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: Any
) -> None:
    assert _property_flag(tmp_path, monkeypatch, mutant) is False


# --------------------------------------------------------------------------------------------
# 9. Types: callable fields only, exact bools, no cache, fail closed
# --------------------------------------------------------------------------------------------


def test_server_context_has_callable_media_fields_and_no_bool_media_field() -> None:
    fields = {f.name: f for f in dataclasses.fields(real_request_ctx.ServerContext)}
    media = {n: f for n, f in fields.items() if "media" in n}
    assert set(media) == {"media_flag", "media_qualified"}
    for field in media.values():
        assert str(field.type).startswith("Callable"), field.type  # never a bool
        assert field.default_factory is dataclasses.MISSING
        assert field.default() is False  # type: ignore[misc]
    assert not [n for n, f in fields.items() if "media" in n and str(f.type) == "bool"]


def _bare_ctx(request_ctx_mod: Any, **kw: Any) -> Any:
    return request_ctx_mod.ServerContext(identity=None, store=None, compat=None, **kw)  # type: ignore[arg-type]


def _property_callable_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any, caplog: pytest.LogCaptureFixture
) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits, load=True)
    mod = world.mod("request_ctx")
    ctx = _bare_ctx(mod)
    if ctx.media_enabled() is not False or ctx.media_qualification_open() is not False:
        return False
    for value in (1, "yes", [1], object(), None, 0):
        ctx.media_flag = lambda v=value: v  # type: ignore[misc]
        ctx.media_qualified = lambda v=value: v  # type: ignore[misc]
        if ctx.media_enabled() is not False or ctx.media_qualification_open() is not False:
            return False

    def boom() -> bool:
        raise RuntimeError("PRIVATE-DETAIL-xyz")

    ctx.media_flag = boom  # type: ignore[assignment]
    ctx.media_qualified = boom  # type: ignore[assignment]
    with caplog.at_level(logging.DEBUG):
        if ctx.media_enabled() is not False or ctx.media_qualification_open() is not False:
            return False
    if "PRIVATE-DETAIL-xyz" in caplog.text or "RuntimeError" not in caplog.text:
        return False
    counter = {"n": 0}

    def counted() -> bool:
        counter["n"] += 1
        return True

    ctx.media_flag = counted  # type: ignore[assignment]
    ctx.media_qualified = counted  # type: ignore[assignment]
    results = [
        ctx.media_enabled(),
        ctx.media_qualification_open(),
        ctx.media_enabled(),
        ctx.media_qualification_open(),
    ]
    return bool(
        results == [True] * 4
        and counter["n"] == 4  # exact bools, never cached
        and all(type(r) is bool for r in results)
    )


def test_media_accessors_are_exact_true_fail_closed_and_uncached(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert _property_callable_semantics(tmp_path, monkeypatch, None, caplog) is True


def test_mutant_truthy_accessors_are_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert _property_callable_semantics(tmp_path, monkeypatch, M_CTX_TRUTHY, caplog) is False


# --------------------------------------------------------------------------------------------
# 10. Profile has no authority
# --------------------------------------------------------------------------------------------


def test_the_callback_takes_no_arguments_and_its_root_comes_from_locate_hermes_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = Synth(tmp_path, monkeypatch)
    _, ctx = world.open()
    assert list(inspect.signature(ctx.media_qualified).parameters) == []
    assert ctx.media_qualification_open() is True
    # Different profile homes / home overrides change nothing.
    for value in (str(tmp_path / "other_profile"), "", str(world.home / "profiles" / "alpha")):
        monkeypatch.setenv("HERMES_HOME", value)
        monkeypatch.setenv("HERMES_PROFILE", "alpha")
        assert ctx.media_qualification_open() is True
    # The root is the process-level locator's, so changing THAT closes the same callback.
    other_root = tmp_path / "other_native"
    other_root.mkdir()
    gate = world.mod("local_media_gate")
    monkeypatch.setattr(gate.compat, "locate_hermes_root", lambda: other_root)
    assert ctx.media_qualification_open() is False
    assert "HERMES_HOME" not in READ_SRC["local_media_gate.py"]


# --------------------------------------------------------------------------------------------
# 11. BaseException: store closed, no hooks, nothing latched
# --------------------------------------------------------------------------------------------


def _property_base_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any, interrupt: bool
) -> bool:
    world = Synth(tmp_path, monkeypatch, edits=edits)
    closes = StoreCloses(world, monkeypatch)
    adapter = world.adapter()
    world.apply_env()
    try:
        world.mod("adapter").open_components(adapter)
    except KeyboardInterrupt:
        pass
    else:
        return False
    return bool(
        closes.count == 1
        and not hasattr(adapter, "_hmp_hooks")
        and cell_value() is None  # the escaped exception latched nothing
    )


def test_keyboard_interrupt_in_the_preload_closes_the_store_before_any_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        _property_base_exception(tmp_path, monkeypatch, M_PRELOAD_KEYBOARD_INTERRUPT, True) is True
    )


def test_mutant_that_only_catches_exception_leaks_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    edits = {**M_PRELOAD_KEYBOARD_INTERRUPT, **M_DROP_BASEEXC}
    assert _property_base_exception(tmp_path, monkeypatch, edits, True) is False


def test_an_ordinary_preload_exception_closes_without_closing_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    edits = {
        "reads.py": [
            (
                M_PRELOAD_KEYBOARD_INTERRUPT["reads.py"][0][0],
                "    raise RuntimeError\n    from . import local_media_sidecar\n",
            )
        ]
    }
    world = Synth(tmp_path, monkeypatch, edits=edits)
    closes = StoreCloses(world, monkeypatch)
    adapter, ctx = world.open()
    assert closes.count == 0 and hasattr(adapter, "_hmp_hooks")
    assert ctx.media_qualification_open() is False and cell_value() == "closed"


# --------------------------------------------------------------------------------------------
# 12. Approval binding unchanged
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"local_media": {"enabled": True}},
        {"local_media": {"enabled": False}},
        {"local_media": {"enabled": "true"}},
    ],
    ids=["absent", "true", "false", "string_true"],
)
def test_media_binding_leaves_the_approval_qualifier_and_its_anchor_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: dict[str, Any]
) -> None:
    before = {k: id(v) for k, v in sys.__dict__.items() if k.startswith("_hermes_hmp")}
    world = Synth(tmp_path, monkeypatch)
    adapter, ctx = world.open(world.adapter(extra))
    # Every approval consumer holds the one approval callback, whatever the media flag says.
    assert ctx.direct_send_deps.approval_qualified == ctx.approval_qualification_open
    assert adapter._hmp_hooks.approval_qualified == ctx.approval_qualification_open
    after = {k: id(v) for k, v in sys.__dict__.items() if k.startswith("_hermes_hmp")}
    assert set(after) - set(before) == {KEY}  # only the media anchor appeared
    assert {k: v for k, v in after.items() if k != KEY} == before
    qualifier = ctx.approval_qualified
    assert qualifier.__globals__ is vars(world.mod("compat"))  # still compat's own callable
    assert ctx.approval_qualification_open() is False  # the shipped approval list is empty
    # The approval wiring in `open_components` is textually unchanged.
    source = READ_SRC["adapter.py"]
    assert (
        "approval_qualified: Callable[[], bool] = (\n"
        "        compat.approval_listener_qualifier(result.identity)\n"
        "        if result.supported is True\n"
        "        else (lambda: False)\n    )"
    ) in source
    assert "approval_qualified=approval_qualified," in source


# --------------------------------------------------------------------------------------------
# 13. Default-off golden: no route reads the media callbacks; every route's bytes are the same
# --------------------------------------------------------------------------------------------


def test_every_route_answers_identically_with_the_flag_off_and_on_and_never_asks_media(
    tmp_path: Path,
) -> None:
    from hmp_plugin import server

    from .hmp_kit import PATH_PREFIX, Env, pair, run

    env = Env(tmp_path)
    calls = {"flag": 0, "qualified": 0}

    def flag() -> bool:
        calls["flag"] += 1
        return state["on"]

    def qualified() -> bool:
        calls["qualified"] += 1
        return state["on"]

    state = {"on": False}
    env.ctx.media_flag = flag
    env.ctx.media_qualified = qualified
    seen: dict[str, list[tuple[str, str, int, bytes]]] = {"off": [], "on": []}

    async def scenario(client: Any) -> None:
        device = await pair(env, client)
        routes = [
            (r.method, r.resource.canonical)
            for r in env.app().router.routes()
            if r.method in {"GET", "POST"}
        ]
        assert any(path.startswith(PATH_PREFIX) for _, path in routes)
        for label in ("off", "on"):
            state["on"] = label == "on"
            for method, path in sorted(routes):
                concrete = path.replace("{", "x_").replace("}", "")
                resp = await client.request(
                    method,
                    concrete,
                    data=b"{}" if method == "POST" else None,
                    headers={"Authorization": f"Bearer {device.access}"},
                )
                seen[label].append((method, path, resp.status, await resp.read()))

    run(env, scenario)
    assert server.build_app  # the real routes were exercised
    assert seen["off"] and seen["off"] == seen["on"]
    assert calls == {"flag": 0, "qualified": 0}
    text = (PACKAGE / "server.py").read_text(encoding="utf-8")
    assert "media" not in text.lower().replace("immediately", "")


# --------------------------------------------------------------------------------------------
# 14. AST pins
# --------------------------------------------------------------------------------------------

PRELOAD_FUNCTIONS = (
    "_media_require",
    "_media_function",
    "_media_prove_function",
    "_media_prove_method",
    "_media_sweep",
    "_media_prove_core",
    "_media_prove_chain",
    "_media_closed",
    "_media_qualifier",
)
FORBIDDEN_NAMES = {"importlib", "__import__", "import_module", "find_spec", "sys"}


def _functions(source: str) -> dict[str, ast.AST]:
    return {n.name: n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)}


def _preload_violations(source: str) -> list[str]:
    bad: list[str] = []
    funcs = _functions(source)
    for name in (*PRELOAD_FUNCTIONS, "_preload"):
        if name not in funcs:
            bad.append(f"missing {name}")
            continue
        for node in ast.walk(funcs[name]):
            label = node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)
            if label in FORBIDDEN_NAMES or (isinstance(node, ast.Attribute) and label == "modules"):
                bad.append(f"{name}: {label}")
            if isinstance(node, ast.Import):
                bad.append(f"{name}: plain import")
            if isinstance(node, ast.ImportFrom) and name != "_media_qualifier":
                bad.append(f"{name}: import")
    return bad


def _media_import_owners(source: str) -> dict[str, set[str]]:
    """{enclosing function name or '<module>': local_media_* modules it imports}."""
    out: dict[str, set[str]] = {}

    def visit(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            inner = child.name if isinstance(child, ast.FunctionDef) else scope
            if isinstance(child, ast.ImportFrom | ast.Import):
                texts = [a.name for a in child.names]
                if isinstance(child, ast.ImportFrom):
                    texts.append(child.module or "")
                names = {
                    part
                    for text in texts
                    for part in text.split(".")
                    if part.startswith("local_media_")
                }
                if names:
                    out.setdefault(scope, set()).update(names)
            visit(child, inner)

    visit(ast.parse(source), "<module>")
    return out


def test_preload_and_qualifier_use_no_dynamic_import_or_module_table() -> None:
    assert _preload_violations(READ_SRC["adapter.py"]) == []


@pytest.mark.parametrize(
    "injection",
    [
        "    import importlib\n",
        "    __import__('x')\n",
        "    import sys\n",
        "    sys.modules.get('x')\n",
        "    importlib.util.find_spec('x')\n",
    ],
)
def test_the_preload_ast_pin_detects_forbidden_lookups(injection: str) -> None:
    source = READ_SRC["adapter.py"].replace(
        "def _media_closed() -> bool:\n    return False\n",
        "def _media_closed() -> bool:\n" + injection + "    return False\n",
    )
    assert source != READ_SRC["adapter.py"]
    assert _preload_violations(source)


DYNAMIC_IMPORT_NAMES = {"importlib", "__import__", "import_module", "find_spec"}


def _dynamic_media_lookups(source: str) -> list[str]:
    """Dynamic module lookups anywhere in a source: `importlib`/`__import__`/`import_module`/
    `find_spec` by name, attribute or import, and `sys.modules`. A local variable that merely is
    called `modules` is not one."""
    bad: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and (node.id in DYNAMIC_IMPORT_NAMES or node.id == "sys"):
            bad.append(node.id)
        elif isinstance(node, ast.Attribute) and (
            node.attr in DYNAMIC_IMPORT_NAMES
            or (
                node.attr == "modules"
                and isinstance(node.value, ast.Name)
                and node.value.id == "sys"
            )
        ):
            bad.append(node.attr)
        elif isinstance(node, ast.Import):
            bad.extend(a.name for a in node.names if a.name.split(".")[0] in {"importlib", "sys"})
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {
            "importlib",
            "sys",
        }:
            bad.append(node.module or "")
        elif isinstance(node, ast.alias) and node.name in DYNAMIC_IMPORT_NAMES:
            bad.append(node.name)
    return bad


@pytest.mark.parametrize("name", ["bridge.py", "reads.py"])
def test_bridge_and_reads_use_no_dynamic_module_lookup(name: str) -> None:
    assert _dynamic_media_lookups(READ_SRC[name]) == []


@pytest.mark.parametrize(
    "injection",
    [
        "    import importlib\n",
        "    from importlib import import_module\n",
        "    __import__('x')\n",
        "    importlib.import_module('x')\n",
        "    import sys\n",
        "    from sys import modules\n",
        "    sys.modules.get('x')\n",
        "    spec = importlib.util.find_spec('x')\n",
    ],
)
def test_the_dynamic_lookup_pin_detects_each_form_and_not_a_plain_modules_name(
    injection: str,
) -> None:
    clean = "def f():\n    modules = (1, 2)\n    return modules[0]\n"
    assert _dynamic_media_lookups(clean) == []  # no generic `modules` wildcard
    assert _dynamic_media_lookups(clean + "\n\ndef g():\n" + injection + "    return 1\n")


def test_media_imports_live_only_in_the_cache_fill_functions() -> None:
    assert _media_import_owners(READ_SRC["bridge.py"]) == {"_local_media_modules": set(MEDIA_CHAIN)}
    assert _media_import_owners(READ_SRC["reads.py"]) == {
        "_local_media_modules": {"local_media_sidecar"}
    }
    assert _media_import_owners(READ_SRC["adapter.py"]) == {
        "_media_qualifier": {"local_media_gate"}
    }


def test_required_set_covers_every_import_reachable_from_the_fill_functions() -> None:
    reachable = set(MEDIA_CHAIN) | {"local_media_gate"}
    frontier = list(reachable)
    while frontier:  # module-scope plugin imports of each media module, transitively
        stem = frontier.pop()
        tree = ast.parse(READ_SRC[f"{stem}.py"])
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                found = [a.name for a in node.names] if node.module is None else [node.module]
                for name in found:
                    if f"{name}.py" in READ_SRC and name not in reachable:
                        reachable.add(name)
                        frontier.append(name)
    assert reachable <= set(STEMS) | {"contract"}, sorted(reachable - set(STEMS))


def test_the_sweep_admits_the_real_package_with_no_false_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = Synth(tmp_path, monkeypatch)
    log = spy_gate(world)
    _, ctx = world.open()
    assert log.preload_errors == [] and len(log.preload_results) == 1
    assert ctx.media_qualification_open() is True


# --------------------------------------------------------------------------------------------
# 15. Reconnect in the same load
# --------------------------------------------------------------------------------------------


def test_a_second_open_in_the_same_load_reuses_the_cached_objects_and_reruns_the_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = Synth(tmp_path, monkeypatch)
    log = spy_gate(world)
    adapter, first = world.open()
    bridge, reads = world.mod("bridge"), world.mod("reads")
    chain, sidecar_only = bridge._local_media_cache, reads._local_media_cache
    fixed = cell_value()
    assert first.media_qualification_open() is True and chain is not None

    _, second = world.open(adapter)
    assert len(log.calls) == 2 and len(log.preload_results) == 2
    assert all(a is b for a, b in zip(*log.preload_results, strict=True))
    assert bridge._local_media_cache is chain and reads._local_media_cache is sidecar_only
    assert type(second.bridge) is type(first.bridge)
    assert cell_value() is fixed  # the factory re-ran against the fixed cell, not a new one
    assert second.media_qualification_open() is True and first.media_qualification_open() is True


def test_the_adapter_never_names_a_reset_or_seam_for_the_process_anchor() -> None:
    for name in ("adapter.py", "request_ctx.py", "bridge.py", "reads.py"):
        text = READ_SRC[name]
        assert "_hermes_hmp_local_media_process_state" not in text, name
        assert "sys.__dict__" not in text and "ANCHOR" not in text, name


# --------------------------------------------------------------------------------------------
# 5b. Every explicit proof is independently necessary (the sweep is OFF in these runs)
# --------------------------------------------------------------------------------------------
# Each entry damages exactly the one thing a single proof statement checks, in a world whose sweep
# is disabled, so only that explicit proof can close it. Omitting the proof makes its case admit.


def _swap(module: str, attr: str, donor_module: str, donor_attr: str | None = None) -> Any:
    def tamper(live: Any, donor: Any) -> None:
        _set(live[module], attr, getattr(donor[donor_module], donor_attr or attr))

    return tamper


def _swap_method(module: str, cls: str, name: str, donor_module: str | None = None) -> Any:
    def tamper(live: Any, donor: Any) -> None:
        source = donor[donor_module or module]
        setattr(getattr(live[module], cls), name, vars(getattr(source, cls))[name])

    return tamper


def _hook(fn: Any) -> Any:
    return ("hook", fn)


def _damage_ctx(attr: str, make: Any) -> Any:
    def hook(adapter: Any, ctx: Any, live: Any, donor: Any) -> None:
        setattr(ctx, attr, make(live, donor))

    return _hook(hook)


def _damage_module(module: str, attr: str, make: Any) -> Any:
    def hook(adapter: Any, ctx: Any, live: Any, donor: Any) -> None:
        setattr(live[module], attr, make(live, donor))

    return _hook(hook)


def _foreign_adapter(world: Synth, donor: Any) -> Any:
    return donor["adapter"].HmpAdapter(SimpleNamespace(extra={"port": 1}))


def _chain(live: Any) -> tuple[Any, ...]:
    return tuple(live[stem] for stem in MEDIA_CHAIN)


def _fabricated_self(live: Any, donor: Any) -> None:
    """A module object with the live adapter's exact namespace CONTENTS but not its namespace:
    every later `vars(own)[...]` lookup would pass, so only P-root can refuse."""
    fake = types.ModuleType(live["adapter"].__name__)
    fake.__dict__.update(vars(live["adapter"]))
    live["adapter"]._LOAD_SELF = fake


PROOFS: dict[str, Any] = {
    "p_root": _fabricated_self,
    "adapter_type": ("adapter", _foreign_adapter),
    "server_context_class": _swap("server", "ServerContext", "request_ctx", "ServerContext"),
    "approval_method": _swap_method("request_ctx", "ServerContext", "approval_qualification_open"),
    "media_method": _swap_method("request_ctx", "ServerContext", "media_qualification_open"),
    "ctx_key": _swap("server", "CTX_KEY", "request_ctx", "CTX_KEY"),
    "server_context_fn": _swap("server", "context", "request_ctx", "context"),
    "server_bearer_fn": _swap("server", "bearer", "request_ctx", "bearer"),
    "server_build_app": _swap("server", "build_app", "server", "build_app"),
    "log_event_fn": _swap("request_ctx", "log_event", "logging_policy", "log_event"),
    "authenticator_class": _swap("auth", "Authenticator", "auth", "Authenticator"),
    "authenticate_method": _swap_method("request_ctx", "Authenticator", "authenticate", "auth"),
    "crypto_module": _damage_module("auth", "crypto", lambda live, donor: object()),
    "crypto_fn": _swap("crypto", "sha256", "crypto", "sha256"),
    "wire_module": lambda live, donor: setattr(live["request_ctx"], "wire", donor["wire"]),
    "wire_fn": _swap("wire", "parse_body", "wire", "parse_body"),
    "hmp_error_server": _swap("server", "HmpError", "contract", "HmpError"),
    "hmp_error_request_ctx": _swap("request_ctx", "HmpError", "contract", "HmpError"),
    "hmp_error_authorize": _swap("authorize", "HmpError", "contract", "HmpError"),
    "reads_class": _swap("adapter", "Reads", "reads", "Reads"),
    "reads_method": _swap_method("reads", "Reads", "_media_result"),
    "reads_require_fn": _swap(
        "server", "require_bot_authorized", "reads", "require_bot_authorized"
    ),
    "reads_accept_fn": _swap("reads", "_accept_media", "reads", "_accept_media"),
    "authorize_class": _swap("adapter", "Authorize", "authorize", "Authorize"),
    "authorize_method": _swap_method("authorize", "Authorize", "authorize"),
    "authorize_ensure_fn": _swap("server", "ensure_chat", "authorize", "ensure_chat"),
    "store_class": _swap("adapter", "Store", "store", "Store"),
    "store_method": _swap_method("store", "Store", "owner_controls_decision"),
    "compat_result_type": _damage_ctx(
        "compat",
        lambda live, donor: donor["compat"].CompatResult(donor["compat"].CompatStatus.SUPPORTED),
    ),
    "compat_default_gate_fn": _damage_module(
        "compat", "default_gate", lambda live, donor: donor["compat"].default_gate
    ),
    "gate_factory_fn": _damage_module(
        "local_media_gate",
        "media_listener_qualifier",
        lambda live, donor: donor["local_media_gate"].media_listener_qualifier,
    ),
    "bridge_cache_missing": _damage_module("adapter", "_bridge_module_cache", lambda *_: None),
    "bridge_instance_type": _damage_ctx("bridge", lambda live, donor: SimpleNamespace()),
    # After the first fill, so the cache and the module attribute disagree.
    "bridge_class_binding": _damage_module(
        "bridge", "HermesReadBridge", lambda live, donor: donor["bridge"].HermesReadBridge
    ),
    "bridge_directory_binding": _damage_module(
        "bridge", "StoreDirectory", lambda live, donor: donor["bridge"].StoreDirectory
    ),
    "bridge_media_method": _swap_method("bridge", "HermesReadBridge", "_media_rows"),
    "bridge_fill_fn": _swap("bridge", "_local_media_modules", "bridge", "_local_media_modules"),
    "reads_fill_fn": _swap("reads", "_local_media_modules", "reads", "_local_media_modules"),
    "bridge_cache_length": lambda live, donor: setattr(
        live["bridge"], "_local_media_cache", (donor["local_media_sidecar"],)
    ),
    "reads_cache_length": lambda live, donor: setattr(
        live["reads"], "_local_media_cache", (live["local_media_sidecar"],) * 2
    ),
    "bridge_cache_member_type": lambda live, donor: setattr(
        live["bridge"], "_local_media_cache", (*_chain(live)[:3], "x", *_chain(live)[4:])
    ),
    "reads_sidecar_identity": lambda live, donor: setattr(
        live["reads"], "_local_media_cache", (donor["local_media_sidecar"],)
    ),
    "candidate_scan_ref": lambda live, donor: setattr(
        live["local_media_candidate"], "_scan", donor["local_media_active_scan"]
    ),
    "result_scan_ref": lambda live, donor: setattr(
        live["local_media_result"], "_scan", donor["local_media_active_scan"]
    ),
    "batch_scan_ref": lambda live, donor: setattr(
        live["local_media_active_batch"], "_scan", donor["local_media_active_scan"]
    ),
    "batch_candidate_ref": lambda live, donor: setattr(
        live["local_media_active_batch"], "_candidate", donor["local_media_candidate"]
    ),
    "binding_batch_ref": lambda live, donor: setattr(
        live["local_media_batch_binding"], "_batch", donor["local_media_active_batch"]
    ),
    "binding_sidecar_ref": lambda live, donor: setattr(
        live["local_media_batch_binding"], "_sidecar", donor["local_media_sidecar"]
    ),
    "collect_candidates_fn": _swap(
        "local_media_candidate", "collect_candidates", "local_media_candidate"
    ),
    "classify_candidate_fn": _swap(
        "local_media_candidate", "classify_candidate", "local_media_file_safety"
    ),
    "parse_image_result_fn": _swap(
        "local_media_candidate", "parse_image_result", "local_media_result"
    ),
    "scan_active_batch_fn": _swap(
        "local_media_active_batch", "scan_active_batch", "local_media_active_batch"
    ),
    "binding_classify_fn": _swap(
        "local_media_batch_binding", "classify", "local_media_batch_binding"
    ),
    "sidecar_text_fn": _swap("local_media_sidecar", "_text", "local_media_sidecar"),
}


def _property_one_proof_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: Any, edits: Any
) -> bool:
    world, donor, live = _two_loads(tmp_path, monkeypatch, edits)
    hook = None
    adapter = None
    if isinstance(entry, tuple) and entry[0] == "adapter":
        adapter = entry[1](world, donor)
    elif isinstance(entry, tuple) and entry[0] == "hook":
        hook = lambda a, c: entry[1](a, c, live, donor)  # noqa: E731
    else:
        entry(live, donor)
    log = spy_gate(world, before=hook)
    _, ctx = world.open(adapter)
    return bool(
        len(log.calls) == 1
        and ctx.media_qualification_open() is False
        and cell_value() == "closed"
        and len(log.preload_errors) == 1  # the preload itself refused (a proof raised)
    )


@pytest.mark.parametrize("name", sorted(PROOFS))
def test_each_explicit_proof_closes_its_own_damage_without_the_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    assert _property_one_proof_closes(tmp_path, monkeypatch, PROOFS[name], M_DROP_SWEEP) is True


def test_the_proof_table_is_not_vacuous_a_clean_world_without_the_sweep_admits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, _, _ = _two_loads(tmp_path, monkeypatch, M_DROP_SWEEP)
    log = spy_gate(world)
    _, ctx = world.open()
    assert log.preload_errors == [] and ctx.media_qualification_open() is True


# --------------------------------------------------------------------------------------------
# 4b. The per-load caches are set once, never refilled and never re-imported
# --------------------------------------------------------------------------------------------

LAST_MEDIA_MODULE = {"bridge": "local_media_batch_binding", "reads": "local_media_sidecar"}


@pytest.mark.parametrize("which", ["bridge", "reads"])
def test_a_filled_cache_is_returned_unchanged_and_triggers_no_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    world = Synth(tmp_path, monkeypatch)
    module = world.mod(which)
    assert module._local_media_cache is None  # nothing fills it at import or start-up
    sentinel = (object(),)
    module._local_media_cache = sentinel
    assert module._local_media_modules() is sentinel
    assert media_modules_in(world) == []  # not one media module was imported


@pytest.mark.parametrize("which", ["bridge", "reads"])
def test_racing_first_fills_publish_one_tuple_and_never_overwrite_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    world = Synth(tmp_path, monkeypatch)
    module = world.mod(which)
    winner = (object(),)
    result: list[Any] = []
    with module._local_media_lock:  # the other filler's publication is in progress
        thread = threading.Thread(target=lambda: result.append(module._local_media_modules()))
        thread.start()
        deadline = time.monotonic() + 10
        while f"{world.pkg}.{LAST_MEDIA_MODULE[which]}" not in sys.modules:
            assert time.monotonic() < deadline and thread.is_alive()
            time.sleep(0.005)
        module._local_media_cache = winner
    thread.join(10)
    assert result and result[0] is winner and module._local_media_cache is winner
