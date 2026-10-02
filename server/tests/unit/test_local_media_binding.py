"""M3: local-media availability binding (adapter / request_ctx / bridge / reads), spec 011.

Replaces the retired S6b exact-build listener-binding suite (`test_local_media_listener_binding.py`,
`media_listener_world.py`) and the removed `test_local_media_gate.py`. Covers acceptance cases
A7-A12 and A14 of `specs/011-local-image-serving/tasks.md` in isolated synthetic worlds
(`media_binding_world.World`): a byte copy of the whole package loaded under a unique name, driven
through the copy's REAL `open_components` against a stubbed SUPPORTED result with
`identity is None` (the converted base) and a chosen `local_media` eligibility.

Retirement mapping of the old suite's causal meanings (what survives, in what form, and what is
gone because the thing it tested no longer exists):

* actual media-chain foreign copy / function references (`PROOFS`, old `test_each_explicit_proof_*`)
  -> `test_each_split_edge_closes_this_listener_only` (same damage table, minus the retired
  qualification-core entries; there is no sweep, so each entry closes on its own proof);
* whole-package eviction with an old listener (`test_old_listener_keeps_its_cache_objects_*`)
  -> `test_a10_*`; the old listener keeps its strong references and still opens;
* listener-local closure and reopen (old "latch" family, now deliberately NOT a latch)
  -> `test_a9_*` and `test_a11_*`;
* BaseException store close (old `test_keyboard_interrupt_in_the_preload_*`)
  -> `test_base_exception_*`;
* old reads golden bytes / every route identical with the flag off and on
  -> `test_every_route_answers_identically_*` (plus the unchanged `test_reads_media.py` and
  `test_bridge_media.py` golden suites, which this slice does not touch);
* strict, live, exact-`True` flag and accessors -> `test_a8_*`;
* cache set-once, never refilled, racing first fills -> `test_media_caches_*`, plus the new
  one-tuple `_bridge_published` publication tests;
* AST import and dynamic-lookup pins -> `test_*_pin_*`.
Gone with their subject, deliberately not ported: manifest and builds-list parsing, fingerprints,
the process anchor/latch and its corruption cases, the GIL guard, loaded-origin checks, plugin
directory equality, the preload bracket, the non-media core proof and sweep, and the
`media_qualified` carrier. A12/A14 are their negative replacements.

Nothing here consumes the media callback in a route (none exists yet): owner `503` and non-owner
`404` belong to S5 and are NOT claimed here. Nothing imports Hermes or touches a live home.
"""

from __future__ import annotations

import ast
import builtins
import dataclasses
import io
import logging
import os
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import request_ctx as real_request_ctx

from .media_binding_world import LEGACY_ANCHOR, MEDIA_STEMS, PACKAGE, World

TEST_LATCH = "_m3_test_process_latch"  # used only by the mutant that re-adds a process latch
READ_SRC = {p.name: p.read_text(encoding="utf-8") for p in PACKAGE.glob("*.py")}


@pytest.fixture(autouse=True)
def _restore_process_keys() -> Iterator[None]:
    """Test-only: a test may plant the legacy anchor, and a mutant may write a latch key. Every
    test starts without either and the originals are put back; the product has no such path."""
    missing = object()
    saved = {key: sys.__dict__.get(key, missing) for key in (LEGACY_ANCHOR, TEST_LATCH)}
    for key in saved:
        sys.__dict__.pop(key, None)
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.startswith("hmpm3_")]:
            del sys.modules[name]
        for key, value in saved.items():
            if value is missing:
                sys.__dict__.pop(key, None)
            else:
                sys.__dict__[key] = value


# --------------------------------------------------------------------------------------------
# Mutants: one source edit each, dropping exactly one guard (applied to a COPY, never the repo)
# --------------------------------------------------------------------------------------------

_BIND_GATE = "        if _available(compat.Feature.LOCAL_MEDIA):\n"
M_REQUIRE_IDENTITY = {
    "adapter.py": [
        (
            _BIND_GATE,
            "        if _available(compat.Feature.LOCAL_MEDIA) and type(result.identity) is "
            "compat.BuildIdentity:\n",
        )
    ]
}
M_DROP_ELIGIBILITY = {"adapter.py": [(_BIND_GATE, "        if True:\n")]}
M_NO_COHERENCE = {
    "adapter.py": [
        (
            "    _media_require(type(chain) is tuple and len(chain) == 7)\n",
            "    return chain, reads_media\n"
            "    _media_require(type(chain) is tuple and len(chain) == 7)\n",
        )
    ]
}
M_PROCESS_LATCH = {
    "adapter.py": [
        (
            "    try:\n        # The bound modules are the ones",
            "    import sys\n"
            f"    if sys.__dict__.get({TEST_LATCH!r}):\n        return _media_closed\n"
            "    try:\n        # The bound modules are the ones",
        ),
        (
            '        log_event("local_media_binding", outcome="media_binding_incoherent")\n',
            "        import sys\n"
            f"        sys.__dict__[{TEST_LATCH!r}] = True\n"
            '        log_event("local_media_binding", outcome="media_binding_incoherent")\n',
        ),
    ]
}
_FENCE = (
    '            same = (\n                vars(bridge_module)["_local_media_cache"] is chain\n'
    '                and vars(reads_module)["_local_media_cache"] is reads_media\n            )\n'
)
M_NO_FENCE = {"adapter.py": [(_FENCE, "            same = True\n")]}
M_FENCE_REIMPORTS = {
    "adapter.py": [
        ("import contextlib\n", "import contextlib\nimport importlib\n"),
        (
            'vars(bridge_module)["_local_media_cache"] is chain\n',
            "importlib.import_module(bridge_module.__name__)._local_media_cache is chain\n",
        ),
    ]
}
M_GIL_GUARD = {
    "adapter.py": [
        (
            "    try:\n        # The bound modules are the ones",
            "    import sys\n"
            '    if getattr(sys, "_is_gil_enabled", lambda: True)() is False:\n'
            "        return _media_closed\n"
            "    try:\n        # The bound modules are the ones",
        )
    ]
}
M_READ_LEGACY_ANCHOR = {
    "adapter.py": [
        (
            "    try:\n        # The bound modules are the ones",
            "    import sys\n"
            f"    if sys.__dict__.get({LEGACY_ANCHOR!r}) is not None:\n"
            "        return _media_closed\n"
            "    try:\n        # The bound modules are the ones",
        )
    ]
}
M_WRITE_LEGACY_ANCHOR = {
    "adapter.py": [
        (
            "    ctx.media_modules = (chain, reads_media)\n",
            "    import sys\n"
            f"    sys.__dict__.setdefault({LEGACY_ANCHOR!r}, (1, None, [None]))\n"
            "    ctx.media_modules = (chain, reads_media)\n",
        )
    ]
}
M_UNLOCKED_OVERWRITE = {
    "adapter.py": [
        (
            "            if _bridge_cache is None:\n                _bridge_cache = fresh\n",
            "            _bridge_cache = fresh\n",
        )
    ]
}
M_DROP_BASEEXC = {
    "adapter.py": [
        (
            "            except BaseException:\n"
            "                store.close()\n                raise\n"
            "        adapter._hmp_hooks",
            "            except Exception:\n                store.close()\n                raise\n"
            "        adapter._hmp_hooks",
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
            "            return self.media_available() is True\n",
            "            return bool(self.media_available())\n",
        ),
    ]
}
_FILL_ANCHOR = (
    "    from . import local_media_sidecar  # unlocked: only the set-once publication is locked\n"
)
M_READS_FILL_RAISES_BASE = {
    "reads.py": [(_FILL_ANCHOR, "    raise KeyboardInterrupt\n" + _FILL_ANCHOR)]
}
M_READS_FILL_RAISES = {
    "reads.py": [
        (_FILL_ANCHOR, '    raise RuntimeError("PRIVATE-DETAIL-xyz")\n' + _FILL_ANCHOR)
    ]
}
M_FLAG_TRUTHY = {
    "adapter.py": [
        (
            '        return isinstance(block, Mapping) and block.get("enabled") is True\n\n'
            "    def _read_model_enabled",
            '        return isinstance(block, Mapping) and bool(block.get("enabled"))\n\n'
            "    def _read_model_enabled",
        )
    ]
}


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------


def _open_log(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if "local_media_binding" in r.getMessage()]


class StoreCloses:
    """Counts `Store.close` of one copy without replacing anything the proofs look at."""

    def __init__(self, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        cls = world.mod("store").Store
        original = cls.close

        def close(this: Any) -> Any:
            self.count += 1
            return original(this)

        monkeypatch.setattr(cls, "close", close)


# --------------------------------------------------------------------------------------------
# A7: supported, `identity is None`: media can open. Only the eligibility member gates the bind.
# --------------------------------------------------------------------------------------------


def _property_a7(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    _, ctx = world.open()
    assert ctx.compat.supported is True and ctx.compat.identity is None
    return ctx.is_media_available() is True and ctx.media_modules is not None


def test_a7_a_supported_listener_with_no_build_identity_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a7(tmp_path, monkeypatch, None) is True


def test_a7_mutant_requiring_a_build_identity_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a7(tmp_path, monkeypatch, M_REQUIRE_IDENTITY) is False


def test_the_bound_references_are_the_actual_caches_of_this_listeners_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    _, ctx = world.open()
    assert ctx.media_modules is not None
    chain, reads_media = ctx.media_modules
    bridge, reads = world.mod("bridge"), world.mod("reads")
    assert chain is bridge._local_media_cache and reads_media is reads._local_media_cache
    assert type(chain) is tuple and len(chain) == 7 and len(reads_media) == 1
    assert reads_media[0] is chain[0]  # one sidecar module for the bridge twins and the reads twins
    assert [m.__name__ for m in chain] == [f"{world.pkg}.{stem}" for stem in MEDIA_STEMS]
    assert all(sys.modules[m.__name__] is m for m in chain)  # these ARE the loaded modules
    assert type(ctx.bridge) is vars(bridge)["HermesReadBridge"]
    assert type(ctx.reads) is vars(reads)["Reads"]
    assert ctx.is_media_available() is True and ctx.media_available() is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"features": ("read",)},  # the local_media member is unavailable
        {"supported": False},  # unsupported build: nothing beyond the listener
        {"eligibility": False},  # a result carrying no eligibility reports nothing available
    ],
    ids=["member_unavailable", "unsupported", "no_eligibility"],
)
def test_a_listener_without_the_member_stays_closed_and_imports_no_media_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kwargs: dict[str, Any]
) -> None:
    def build(edits: Any) -> tuple[World, Any]:
        world = World(tmp_path, monkeypatch, label="w", edits=edits, **kwargs)
        return world, world.open()[1]

    world, ctx = build(None)
    assert ctx.is_media_available() is False and ctx.media_modules is None
    assert world.media_modules_loaded() == []
    assert (ctx.bridge is not None) == (kwargs.get("supported", True) is True)
    # The same inputs with the eligibility guard removed DO reach the binder: the guard is causal.
    tmp = tmp_path / "mutant"
    tmp.mkdir()
    mutant = World(tmp, monkeypatch, label="m", edits=M_DROP_ELIGIBILITY, **kwargs)
    if kwargs.get("supported", True) is True:
        assert mutant.open()[1].media_modules is not None
        assert mutant.media_modules_loaded() != []


def test_binding_reads_no_file_and_no_module_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once the caches exist, the bind and the fence perform no file or directory operation."""
    world = World(tmp_path, monkeypatch)
    _, ctx = world.open()
    adapter = world.mod("adapter")
    bridge, reads = world.mod("bridge"), world.mod("reads")
    touched: list[str] = []

    def spy(name: str, real: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            touched.append(name)
            return real(*args, **kwargs)

        return wrapper

    for owner, name in (
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "lstat"),
        (os, "listdir"),
        (os, "scandir"),
        (os, "open"),
        (Path, "stat"),
        (Path, "read_text"),
        (Path, "read_bytes"),
    ):
        monkeypatch.setattr(owner, name, spy(name, getattr(owner, name)))
    callback = adapter._media_bind(ctx, bridge, reads)
    assert callback() is True and ctx.media_available() is True
    assert touched == []


# --------------------------------------------------------------------------------------------
# A9: a split media chain closes THIS listener only; no process latch; another listener opens
# --------------------------------------------------------------------------------------------


def _set(module: Any, attr: str, value: Any) -> None:
    setattr(module, attr, value)


def _donor_attr(module: str, attr: str, donor_module: str | None = None) -> Any:
    def damage(world: World, donor: World) -> None:
        _set(world.mod(module), attr, getattr(donor.mod(donor_module or module), attr))

    return damage


def _cache_damage(which: str, make: Any) -> Any:
    def damage(world: World, donor: World) -> None:
        module = world.mod(which)
        module._local_media_cache = make(world, donor, module._local_media_cache)

    return damage


def _equal_copy(value: tuple[Any, ...]) -> tuple[Any, ...]:
    """An equal tuple that is a DIFFERENT object (`tuple(t)` returns `t` itself)."""
    copy = (*value,)
    assert copy == value and copy is not value
    return copy


def _swap_member(chain: tuple[Any, ...], index: int, value: Any) -> tuple[Any, ...]:
    return (*chain[:index], value, *chain[index + 1 :])


# Each entry damages exactly the one cross-reference a single proof statement checks.
SPLITS: dict[str, Any] = {
    "candidate_scan": lambda w, d: _set(
        w.mod("local_media_candidate"), "_scan", d.mod("local_media_active_scan")
    ),
    "result_scan": lambda w, d: _set(
        w.mod("local_media_result"), "_scan", d.mod("local_media_active_scan")
    ),
    "batch_scan": lambda w, d: _set(
        w.mod("local_media_active_batch"), "_scan", d.mod("local_media_active_scan")
    ),
    "batch_candidate": lambda w, d: _set(
        w.mod("local_media_active_batch"), "_candidate", d.mod("local_media_candidate")
    ),
    "binding_batch": lambda w, d: _set(
        w.mod("local_media_batch_binding"), "_batch", d.mod("local_media_active_batch")
    ),
    "binding_sidecar": lambda w, d: _set(
        w.mod("local_media_batch_binding"), "_sidecar", d.mod("local_media_sidecar")
    ),
    "collect_candidates_fn": _donor_attr("local_media_candidate", "collect_candidates"),
    "classify_candidate_fn": lambda w, d: _set(
        w.mod("local_media_candidate"),
        "classify_candidate",
        d.mod("local_media_file_safety").classify_candidate,
    ),
    "parse_image_result_fn": lambda w, d: _set(
        w.mod("local_media_candidate"),
        "parse_image_result",
        d.mod("local_media_result").parse_image_result,
    ),
    "scan_active_batch_fn": _donor_attr("local_media_active_batch", "scan_active_batch"),
    "binding_classify_fn": _donor_attr("local_media_batch_binding", "classify"),
    "sidecar_text_fn": _donor_attr("local_media_sidecar", "_text"),
    "reads_sidecar_identity": _cache_damage(
        "reads", lambda w, d, cache: (d.mod("local_media_sidecar"),)
    ),
    "bridge_cache_short": _cache_damage("bridge", lambda w, d, cache: cache[:6]),
    "bridge_cache_member_type": _cache_damage(
        "bridge", lambda w, d, cache: _swap_member(cache, 3, "not a module")
    ),
    "reads_cache_long": _cache_damage("reads", lambda w, d, cache: (cache[0], cache[0])),
    "bridge_cache_foreign_member": _cache_damage(
        "bridge", lambda w, d, cache: _swap_member(cache, 4, d.mod("local_media_file_safety"))
    ),
}

# These damage what `open_components` builds (the listener's own bridge / reads objects), so they
# are applied to the copy's adapter namespace and take effect during the open itself.
LISTENER_SPLITS: dict[str, Any] = {
    "bridge_class_from_a_foreign_copy": lambda w, d: _set(
        w.mod("adapter"),
        "_bridge_cache",
        (w.mod("bridge"), d.mod("bridge").HermesReadBridge, d.mod("bridge").StoreDirectory),
    ),
    "bridge_module_from_a_foreign_copy": lambda w, d: _set(
        w.mod("adapter"),
        "_bridge_cache",
        (d.mod("bridge"), w.mod("bridge").HermesReadBridge, w.mod("bridge").StoreDirectory),
    ),
    "reads_class_from_a_foreign_copy": lambda w, d: _set(
        w.mod("adapter"), "Reads", d.mod("reads").Reads
    ),
    "reads_module_from_a_foreign_copy": lambda w, d: _set(
        w.mod("adapter"), "reads", d.mod("reads")
    ),
}


def _two_worlds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any = None
) -> tuple[World, World]:
    """`(world, donor)`: two coherent package copies with filled media caches."""
    donor_dir = tmp_path / "donor"
    donor_dir.mkdir()
    world = World(tmp_path, monkeypatch, label="w", edits=edits)
    donor = World(donor_dir, monkeypatch, label="d", edits=edits)
    world.fill_caches()
    donor.fill_caches()
    return world, donor


def test_a_clean_pair_of_worlds_opens_both(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world, donor = _two_worlds(tmp_path, monkeypatch)
    assert world.open()[1].is_media_available() is True
    assert donor.open()[1].is_media_available() is True


@pytest.mark.parametrize("name", sorted(SPLITS) + sorted(LISTENER_SPLITS))
def test_each_split_edge_closes_this_listener_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    name: str,
) -> None:
    world, donor = _two_worlds(tmp_path, monkeypatch)
    (SPLITS.get(name) or LISTENER_SPLITS[name])(world, donor)
    with caplog.at_level(logging.INFO):
        adapter, ctx = world.open()
    # This listener's media is closed with the one fixed outcome, and nothing else changed:
    assert ctx.is_media_available() is False and ctx.media_modules is None
    assert _open_log(caplog) == ["event=local_media_binding outcome=media_binding_incoherent"]
    assert ctx.bridge is not None and ctx.reads is not None  # read and send wiring is untouched
    assert hasattr(adapter, "_hmp_hooks")
    # No latch: an independent coherent listener in the same process opens afterwards.
    assert donor.open()[1].is_media_available() is True


def test_a9_the_same_load_reopens_once_the_split_is_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, donor = _two_worlds(tmp_path, monkeypatch)
    candidate = world.mod("local_media_candidate")
    good = candidate._scan
    candidate._scan = donor.mod("local_media_active_scan")
    adapter, broken = world.open()
    assert broken.is_media_available() is False
    candidate._scan = good
    _, repaired = world.open(adapter)
    assert repaired.is_media_available() is True and repaired.media_modules is not None
    assert broken.is_media_available() is False  # the earlier listener stays closed (its own state)


def _property_a9(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any
) -> tuple[bool, bool]:
    """`(split closes this listener, a coherent second listener opens)` under `edits`."""
    world, donor = _two_worlds(tmp_path, monkeypatch, edits)
    SPLITS["candidate_scan"](world, donor)
    closed = world.open()[1].is_media_available() is False
    return closed, donor.open()[1].is_media_available() is True


def test_a9_real_source_closes_the_split_and_a_second_listener_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a9(tmp_path, monkeypatch, None) == (True, True)


def test_a9_mutant_without_coherence_admits_the_split(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a9(tmp_path, monkeypatch, M_NO_COHERENCE)[0] is False


def test_a9_mutant_with_a_process_latch_blocks_the_second_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a9(tmp_path, monkeypatch, M_PROCESS_LATCH) == (True, False)


def test_an_ordinary_exception_in_a_cache_fill_closes_this_listener_with_no_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    world = World(tmp_path, monkeypatch, edits=M_READS_FILL_RAISES)
    closes = StoreCloses(world, monkeypatch)
    with caplog.at_level(logging.DEBUG):
        adapter, ctx = world.open()
    assert ctx.is_media_available() is False and ctx.media_modules is None
    assert closes.count == 0 and hasattr(adapter, "_hmp_hooks")  # the listener itself still opens
    assert "PRIVATE-DETAIL-xyz" not in caplog.text
    assert _open_log(caplog) == ["event=local_media_binding outcome=media_binding_incoherent"]


# --------------------------------------------------------------------------------------------
# A10: whole-package eviction after open: the old listener keeps its bound objects
# --------------------------------------------------------------------------------------------


def _property_a10(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    _, old_ctx = world.open()
    assert old_ctx.media_modules is not None
    bound = old_ctx.media_modules
    old_chain, old_reads = bound
    old_bridge, old_adapter = world.mod("bridge"), world.mod("adapter")
    world.reload()  # the Hermes loader evicts the package and loads a second copy
    new_bridge = world.mod("bridge")
    assert new_bridge is not old_bridge
    assert sys.modules.get(old_chain[0].__name__) is not old_chain[0]
    assert old_ctx.media_modules is bound  # the very tuple, not a fresh lookup
    assert old_ctx.media_modules[0] is old_bridge._local_media_cache
    assert old_adapter._bridge_published()[0] is old_bridge  # the old load keeps its own bridge
    still_open = old_ctx.is_media_available() is True
    # The old listener's references are intact and are NOT the reloaded copy's.
    same = old_ctx.media_modules[0] is old_chain and old_ctx.media_modules[1] is old_reads
    _, new_ctx = world.open()
    fresh = new_ctx.media_modules is not None and new_ctx.media_modules[0] is not old_chain
    return bool(still_open and same and fresh and new_ctx.is_media_available() is True)


def test_a10_an_old_listener_keeps_its_bound_objects_after_whole_package_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a10(tmp_path, monkeypatch, None) is True


def test_a10_mutant_that_compares_against_a_fresh_import_closes_after_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch, edits=M_FENCE_REIMPORTS)
    _, ctx = world.open()
    assert ctx.is_media_available() is True  # before any eviction the mutant looks fine
    world.reload()
    assert ctx.is_media_available() is False  # ...but a handler that re-imports splits here


# FUTURE (S4/S5, not claimed here): mint and fetch do not exist yet. When they land, the
# acceptance for A10 additionally requires them to use `ctx.media_modules` by identity and never a
# fresh import; this file pins only the availability binding and the bound strong references.


# --------------------------------------------------------------------------------------------
# A11: use-time identity fence: mismatch closes THIS listener until reopen
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("which", ["bridge", "reads"])
def test_a11_a_changed_cache_closes_this_listener_until_reopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    which: str,
) -> None:
    world = World(tmp_path, monkeypatch)
    adapter, ctx = world.open()
    module = world.mod(which)
    original = module._local_media_cache
    assert ctx.is_media_available() is True
    module._local_media_cache = _equal_copy(original)  # equal by value, a different object
    with caplog.at_level(logging.INFO):
        assert ctx.is_media_available() is False
        module._local_media_cache = original  # restoring the identity does not reopen it
        assert ctx.is_media_available() is False and ctx.media_available() is False
    assert ctx.media_modules is None  # a closed listener hands out no bound reference
    assert _open_log(caplog) == ["event=local_media_binding outcome=media_binding_changed"]
    # Reopen: a fresh listener binds again; the earlier one stays closed.
    _, reopened = world.open(adapter)
    assert reopened.is_media_available() is True and ctx.is_media_available() is False


def test_a11_a_missing_cache_attribute_closes_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    _, ctx = world.open()
    del world.mod("bridge")._local_media_cache
    assert ctx.is_media_available() is False


def test_a11_a_new_cache_object_closes_the_old_listener_and_opens_the_next(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    adapter, first = world.open()
    bridge = world.mod("bridge")
    bridge._local_media_cache = _equal_copy(bridge._local_media_cache)
    _, second = world.open(adapter)
    assert first.is_media_available() is False
    assert second.is_media_available() is True
    assert second.media_modules is not None
    assert second.media_modules[0] is bridge._local_media_cache


def test_a11_mutant_without_the_fence_never_notices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch, edits=M_NO_FENCE)
    _, ctx = world.open()
    bridge = world.mod("bridge")
    bridge._local_media_cache = _equal_copy(bridge._local_media_cache)
    assert ctx.is_media_available() is True  # the fence is the only thing that closes it


def test_a11_another_package_copy_is_unaffected_by_this_listeners_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, donor = _two_worlds(tmp_path, monkeypatch)
    _, other = donor.open()
    _, ctx = world.open()
    bridge = world.mod("bridge")
    bridge._local_media_cache = _equal_copy(bridge._local_media_cache)
    assert ctx.is_media_available() is False and other.is_media_available() is True


# --------------------------------------------------------------------------------------------
# A12: free-threaded flag simulated: no closure from interpreter mode alone, no GIL assumption
# --------------------------------------------------------------------------------------------


def _property_a12(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: False, raising=False)
    world = World(tmp_path, monkeypatch, edits=edits)
    _, ctx = world.open()
    return ctx.is_media_available() is True and ctx.media_modules is not None


def test_a12_a_simulated_free_threaded_interpreter_does_not_close_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a12(tmp_path, monkeypatch, None) is True


def test_a12_mutant_with_a_gil_guard_closes_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a12(tmp_path, monkeypatch, M_GIL_GUARD) is False


def test_a12_every_cache_publication_and_media_registry_uses_a_lock_not_the_gil() -> None:
    lock_type = type(threading.Lock())
    from hmp_plugin import local_media_registry

    assert "threading.Lock()" in READ_SRC["local_media_registry.py"]
    assert "_is_gil_enabled" not in "".join(READ_SRC.values())
    for name in ("bridge.py", "reads.py"):
        assert "_local_media_lock = threading.Lock()" in READ_SRC[name]
        assert 'with _local_media_lock:\n        if _local_media_cache is None:' in READ_SRC[name]
    assert "_bridge_lock = threading.Lock()" in READ_SRC["adapter.py"]
    assert "with _bridge_lock:\n            if _bridge_cache is None:" in READ_SRC["adapter.py"]
    assert hasattr(local_media_registry, "threading") and lock_type is type(threading.Lock())


# --------------------------------------------------------------------------------------------
# A14: a legacy process anchor is ignored and never written
# --------------------------------------------------------------------------------------------


def _legacy_anchor() -> Any:
    return (1, threading.Lock(), ["closed"])


def _property_a14_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    anchor = _legacy_anchor()
    sys.__dict__[LEGACY_ANCHOR] = anchor
    world = World(tmp_path, monkeypatch, edits=edits)
    _, ctx = world.open()
    untouched = (
        sys.__dict__[LEGACY_ANCHOR] is anchor
        and anchor[2] == ["closed"]
        and anchor[1].acquire(blocking=False)  # never locked either
    )
    return bool(ctx.is_media_available() is True and untouched)


def test_a14_a_legacy_closed_anchor_is_ignored_and_left_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a14_ignored(tmp_path, monkeypatch, None) is True


def test_a14_mutant_that_reads_the_legacy_key_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a14_ignored(tmp_path, monkeypatch, M_READ_LEGACY_ANCHOR) is False


def _property_a14_never_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any
) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    _, ctx = world.open()
    bridge = world.mod("bridge")
    bridge._local_media_cache = _equal_copy(bridge._local_media_cache)
    ctx.is_media_available()  # closes through the fence
    return ctx.is_media_available() is False and LEGACY_ANCHOR not in sys.__dict__


def test_a14_neither_open_nor_closure_writes_the_legacy_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a14_never_written(tmp_path, monkeypatch, None) is True


def test_a14_mutant_that_writes_the_legacy_key_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_a14_never_written(tmp_path, monkeypatch, M_WRITE_LEGACY_ANCHOR) is False


def test_no_module_names_the_legacy_anchor_or_the_process_dict() -> None:
    for name, source in READ_SRC.items():
        assert LEGACY_ANCHOR not in source, name
    for name in ("adapter.py", "request_ctx.py", "bridge.py", "reads.py"):
        assert "sys.__dict__" not in READ_SRC[name], name


# --------------------------------------------------------------------------------------------
# A8 (binding half): strict, live, default-off flag; exact-True accessors; closed defaults
# --------------------------------------------------------------------------------------------


def test_server_context_media_fields_are_closed_callables_and_a_reference_slot() -> None:
    fields = {f.name: f for f in dataclasses.fields(real_request_ctx.ServerContext)}
    media = {n for n in fields if "media" in n}
    assert media == {"media_flag", "media_available", "media_modules"}
    for name in ("media_flag", "media_available"):
        assert str(fields[name].type).startswith("Callable"), fields[name].type  # never a bool
        assert fields[name].default_factory is dataclasses.MISSING
        assert fields[name].default() is False  # type: ignore[misc]
    assert fields["media_modules"].default is None
    assert not [n for n in media if str(fields[n].type) == "bool"]
    assert not hasattr(real_request_ctx.ServerContext, "media_qualification_open")
    assert not hasattr(real_request_ctx.ServerContext, "media_qualified")


def _bare_ctx(request_ctx_mod: Any, **kw: Any) -> Any:
    return request_ctx_mod.ServerContext(identity=None, store=None, compat=None, **kw)  # type: ignore[arg-type]


def _property_accessors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    edits: Any,
    caplog: pytest.LogCaptureFixture,
) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    ctx = _bare_ctx(world.mod("request_ctx"))
    if ctx.media_enabled() is not False or ctx.is_media_available() is not False:
        return False
    for value in (1, "yes", [1], object(), None, 0):
        ctx.media_flag = lambda v=value: v  # type: ignore[misc]
        ctx.media_available = lambda v=value: v  # type: ignore[misc]
        if ctx.media_enabled() is not False or ctx.is_media_available() is not False:
            return False

    def boom() -> bool:
        raise RuntimeError("PRIVATE-DETAIL-xyz")

    ctx.media_flag = boom  # type: ignore[assignment]
    ctx.media_available = boom  # type: ignore[assignment]
    with caplog.at_level(logging.DEBUG):
        if ctx.media_enabled() is not False or ctx.is_media_available() is not False:
            return False
    if "PRIVATE-DETAIL-xyz" in caplog.text or "RuntimeError" not in caplog.text:
        return False
    counter = {"n": 0}

    def counted() -> bool:
        counter["n"] += 1
        return True

    ctx.media_flag = counted  # type: ignore[assignment]
    ctx.media_available = counted  # type: ignore[assignment]
    results = [
        ctx.media_enabled(),
        ctx.is_media_available(),
        ctx.media_enabled(),
        ctx.is_media_available(),
    ]
    exact = all(type(r) is bool for r in results)
    return bool(results == [True] * 4 and counter["n"] == 4 and exact)


def test_a8_accessors_are_exact_true_fail_closed_and_uncached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert _property_accessors(tmp_path, monkeypatch, None, caplog) is True


def test_a8_mutant_truthy_accessors_are_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert _property_accessors(tmp_path, monkeypatch, M_CTX_TRUTHY, caplog) is False


def _property_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    adapter, ctx = world.open()
    if ctx.media_enabled() is not False:  # default off
        return False
    extras: list[tuple[Any, bool]] = [
        ({"enabled": True}, True),
        ({"enabled": False}, False),
        ({"enabled": "true"}, False),
        ({"enabled": "yes"}, False),
        ({"enabled": 1}, False),
        ({"enabled": None}, False),
        ({"enabled": [True]}, False),
        ({}, False),
        (True, False),  # a non-mapping block
        ("enabled", False),
        (["enabled"], False),
        (None, False),
    ]
    for block, expected in extras:
        adapter.config.extra["local_media"] = block
        if ctx.media_enabled() is not expected:
            return False
    adapter.config.extra.pop("local_media")
    if ctx.media_enabled() is not False:
        return False
    # Live: the CURRENT config object, not the one captured at open.
    captured = adapter.config
    adapter.config = type(captured)({"local_media": {"enabled": True}})
    swapped_on = ctx.media_enabled() is True
    adapter.config = type(captured)({"local_media": {"enabled": "yes"}})
    swapped_bad = ctx.media_enabled() is False
    adapter.config = None
    return bool(swapped_on and swapped_bad and ctx.media_enabled() is False)


def test_a8_flag_is_strict_exact_true_default_off_and_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_flag(tmp_path, monkeypatch, None) is True


def test_a8_mutant_truthy_flag_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_flag(tmp_path, monkeypatch, M_FLAG_TRUTHY) is False


def test_a8_the_flag_and_availability_are_independent_of_each_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    adapter, ctx = world.open(world.adapter({"local_media": {"enabled": True}}))
    assert ctx.media_enabled() is True and ctx.is_media_available() is True
    adapter.config.extra["local_media"] = {"enabled": False}
    assert ctx.media_enabled() is False and ctx.is_media_available() is True  # flag is not binding
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    off = World(other_dir, monkeypatch, label="o", features=("read",))
    _, off_ctx = off.open(off.adapter({"local_media": {"enabled": True}}))
    assert off_ctx.media_enabled() is True and off_ctx.is_media_available() is False


def test_every_route_answers_identically_with_the_flag_and_availability_off_and_on(
    tmp_path: Path,
) -> None:
    """The old-read bytes: no route reads either media callback, so every route's bytes are the
    same however they are set. (Owner `503` and non-owner `404` belong to S5: not claimed.)"""
    from hmp_plugin import server

    from .hmp_kit import PATH_PREFIX, Env, pair, run

    env = Env(tmp_path)
    calls = {"flag": 0, "available": 0}
    state = {"on": False}

    def flag() -> bool:
        calls["flag"] += 1
        return state["on"]

    def available() -> bool:
        calls["available"] += 1
        return state["on"]

    env.ctx.media_flag = flag
    env.ctx.media_available = available
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
    assert server.build_app
    assert seen["off"] and seen["off"] == seen["on"]
    assert calls == {"flag": 0, "available": 0}
    assert "media" not in READ_SRC["server.py"].lower().replace("immediately", "")


# --------------------------------------------------------------------------------------------
# Cache publication: one locked tuple, imports outside the lock
# --------------------------------------------------------------------------------------------


def test_bridge_publication_is_one_tuple_of_module_and_both_classes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    adapter = world.mod("adapter")
    assert adapter._bridge_cache is None  # nothing fills it at import
    results: list[Any] = []
    barrier = threading.Barrier(8)

    def call() -> None:
        barrier.wait()
        results.append(adapter._bridge_published())

    threads = [threading.Thread(target=call) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert len(results) == 8 and all(r is results[0] for r in results)
    module, bridge_cls, directory_cls = results[0]
    assert adapter._bridge_cache is results[0]
    assert vars(module)["HermesReadBridge"] is bridge_cls
    assert vars(module)["StoreDirectory"] is directory_cls
    assert adapter._bridge_classes() == (bridge_cls, directory_cls)
    assert module is world.mod("bridge")


def _property_bridge_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any) -> bool:
    world = World(tmp_path, monkeypatch, edits=edits)
    adapter = world.mod("adapter")
    assert f"{world.pkg}.bridge" not in sys.modules  # nothing imported it yet
    winner = (object(), object(), object())
    result: list[Any] = []
    with adapter._bridge_lock:  # another first caller's publication is in progress
        thread = threading.Thread(target=lambda: result.append(adapter._bridge_published()))
        thread.start()
        deadline = time.monotonic() + 10
        # The importing caller finishes its import while the lock is held: imports are NOT
        # under the publication lock.
        while f"{world.pkg}.bridge" not in sys.modules:
            assert time.monotonic() < deadline and thread.is_alive()
            time.sleep(0.005)
        adapter._bridge_cache = winner
    thread.join(10)
    return bool(result and result[0] is winner and adapter._bridge_cache is winner)


def test_bridge_publication_import_runs_outside_the_lock_and_the_winner_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_bridge_race(tmp_path, monkeypatch, None) is True


def test_bridge_publication_mutant_that_overwrites_the_winner_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_bridge_race(tmp_path, monkeypatch, M_UNLOCKED_OVERWRITE) is False


def test_a_published_bridge_tuple_is_returned_unchanged_with_no_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path, monkeypatch)
    adapter = world.mod("adapter")
    sentinel = (object(), object(), object())
    adapter._bridge_cache = sentinel
    assert adapter._bridge_published() is sentinel
    assert f"{world.pkg}.bridge" not in sys.modules


LAST_MEDIA_MODULE = {"bridge": "local_media_batch_binding", "reads": "local_media_sidecar"}


@pytest.mark.parametrize("which", ["bridge", "reads"])
def test_media_caches_are_empty_until_filled_then_returned_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    world = World(tmp_path, monkeypatch)
    module = world.mod(which)
    assert module._local_media_cache is None  # nothing fills it at import or start-up
    sentinel = (object(),)
    module._local_media_cache = sentinel
    assert module._local_media_modules() is sentinel
    assert world.media_modules_loaded() == []  # not one media module was imported


@pytest.mark.parametrize("which", ["bridge", "reads"])
def test_media_caches_racing_first_fills_publish_one_tuple_and_never_overwrite_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    world = World(tmp_path, monkeypatch)
    module = world.mod(which)
    winner = (object(),)
    result: list[Any] = []
    with module._local_media_lock:
        thread = threading.Thread(target=lambda: result.append(module._local_media_modules()))
        thread.start()
        deadline = time.monotonic() + 10
        while f"{world.pkg}.{LAST_MEDIA_MODULE[which]}" not in sys.modules:
            assert time.monotonic() < deadline and thread.is_alive()
            time.sleep(0.005)
        module._local_media_cache = winner
    thread.join(10)
    assert result and result[0] is winner and module._local_media_cache is winner


# --------------------------------------------------------------------------------------------
# BaseException: the store closes, no hooks are installed, nothing process-wide latches
# --------------------------------------------------------------------------------------------


def _property_base_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edits: Any
) -> bool:
    world = World(tmp_path, monkeypatch, edits={**M_READS_FILL_RAISES_BASE, **(edits or {})})
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
        and LEGACY_ANCHOR not in sys.__dict__
    )


def test_base_exception_in_the_binding_closes_the_store_before_any_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_base_exception(tmp_path, monkeypatch, None) is True


def test_base_exception_mutant_that_only_catches_exception_leaks_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _property_base_exception(tmp_path, monkeypatch, M_DROP_BASEEXC) is False


# --------------------------------------------------------------------------------------------
# AST pins
# --------------------------------------------------------------------------------------------

MEDIA_FUNCTIONS = (
    "_media_require",
    "_media_function",
    "_media_prove_function",
    "_media_prove_chain",
    "_media_closed",
    "_media_bind",
)
FORBIDDEN_NAMES = {"importlib", "__import__", "import_module", "find_spec", "sys"}
DISK_NAMES = {"open", "os", "Path", "stat", "listdir", "scandir", "read_text", "read_bytes", "glob"}
RETIRED = {
    "local_media_gate",
    "media_qualified",
    "media_qualification_open",
    "_media_qualifier",
    "_media_sweep",
    "_media_prove_core",
    "_media_prove_method",
    "_LOAD_SELF",
    "media_listener_qualifier",
    "BuildIdentity",
    "_bridge_classes_cache",
    "_bridge_module_cache",
}


def _functions(source: str) -> dict[str, ast.AST]:
    return {n.name: n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)}


def _identifiers(source: str) -> set[str]:
    """Every identifier a module's CODE uses (docstrings and comments excluded)."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.add(node.name)
        elif isinstance(node, ast.arg):
            found.add(node.arg)
        elif isinstance(node, ast.alias):
            found.add(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _media_function_violations(source: str) -> list[str]:
    bad: list[str] = []
    funcs = _functions(source)
    for name in MEDIA_FUNCTIONS:
        if name not in funcs:
            bad.append(f"missing {name}")
            continue
        for node in ast.walk(funcs[name]):
            label = node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)
            if label in FORBIDDEN_NAMES or label in DISK_NAMES:
                bad.append(f"{name}: {label}")
            if isinstance(node, ast.Attribute) and label == "modules":
                bad.append(f"{name}: modules")
            if isinstance(node, ast.Import | ast.ImportFrom | ast.Await):
                bad.append(f"{name}: {type(node).__name__}")
    return bad


def test_media_binding_functions_use_no_dynamic_import_module_table_disk_or_await() -> None:
    assert _media_function_violations(READ_SRC["adapter.py"]) == []


@pytest.mark.parametrize(
    "injection",
    [
        "    import importlib\n",
        "    __import__('x')\n",
        "    import sys\n",
        "    sys.modules.get('x')\n",
        "    importlib.util.find_spec('x')\n",
        "    open('x')\n",
        "    Path('x').read_text()\n",
        "    os.stat('x')\n",
    ],
)
def test_the_binding_pin_detects_forbidden_lookups_and_disk_access(injection: str) -> None:
    source = READ_SRC["adapter.py"].replace(
        "def _media_closed() -> bool:\n    return False\n",
        "def _media_closed() -> bool:\n" + injection + "    return False\n",
    )
    assert source != READ_SRC["adapter.py"]
    assert _media_function_violations(source)


def test_the_fence_callback_contains_no_await_import_or_lock() -> None:
    tree = _functions(READ_SRC["adapter.py"])["media_available"]
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Await | ast.Import | ast.ImportFrom | ast.With), node
        assert not (isinstance(node, ast.Attribute) and node.attr in {"acquire", "release"})


def test_the_retired_gate_binder_and_qualification_names_are_gone() -> None:
    for name in ("adapter.py", "request_ctx.py", "bridge.py", "reads.py", "server.py"):
        leftover = RETIRED & _identifiers(READ_SRC[name])
        assert not leftover, (name, leftover)
    assert not (PACKAGE / "local_media_gate.py").exists()
    assert not (PACKAGE / "local_media_supported_builds.json").exists()
    here = Path(__file__).parent
    assert not (here / "test_local_media_gate.py").exists()
    assert not (here / "test_local_media_listener_binding.py").exists()
    assert not (here / "media_listener_world.py").exists()


def test_publication_assigns_one_global_tuple_and_has_no_split_names() -> None:
    tree = ast.parse(READ_SRC["adapter.py"])
    assigned = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_bridge_cache" for t in node.targets)
    ]
    # The module-level initializer is an AnnAssign; the publication is the one `Assign`.
    assert len(assigned) == 1
    module_level = {
        t.target.id
        for t in tree.body
        if isinstance(t, ast.AnnAssign) and isinstance(t.target, ast.Name)
    }
    assert {"_bridge_cache"} <= module_level
    assert not {n for n in module_level if "bridge" in n and n not in {"_bridge_cache"}}


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


@pytest.mark.parametrize("name", ["adapter.py", "bridge.py", "reads.py"])
def test_adapter_bridge_and_reads_use_no_dynamic_module_lookup(name: str) -> None:
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
    assert _dynamic_media_lookups(clean) == []
    assert _dynamic_media_lookups(clean + "\n\ndef g():\n" + injection + "    return 1\n")


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


def test_media_imports_live_only_in_the_cache_fill_functions_and_never_in_the_adapter() -> None:
    assert _media_import_owners(READ_SRC["bridge.py"]) == {
        "_local_media_modules": set(MEDIA_STEMS)
    }
    assert _media_import_owners(READ_SRC["reads.py"]) == {
        "_local_media_modules": {"local_media_sidecar"}
    }
    assert _media_import_owners(READ_SRC["adapter.py"]) == {}
    assert _media_import_owners(READ_SRC["request_ctx.py"]) == {}


def test_the_adapter_imports_bridge_only_inside_the_publication_function() -> None:
    tree = ast.parse(READ_SRC["adapter.py"])
    top = [n for n in tree.body if isinstance(n, ast.ImportFrom)]
    assert not any("bridge" in {a.name for a in n.names} or n.module == "bridge" for n in top)
    inside = [
        n
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        for n in ast.walk(fn)
        if isinstance(n, ast.ImportFrom) and any(a.name == "bridge" for a in n.names)
    ]
    assert len(inside) == 1
    owner = [
        fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        and any(isinstance(n, ast.ImportFrom) and any(a.name == "bridge" for a in n.names)
                for n in ast.walk(fn))
    ]
    assert owner == ["_bridge_published"]
