"""Real compat-gate readers (T023): the git-metadata SHA reader, the read-bridge fingerprint,
`read_compat_builds.json` loading, and the dependency probe. `test_compat_gate.py` covers the
eligibility function's fixed evaluation order, and `test_compat_matching.py` the CS-19 matching
rule, which is now evidence only. This file covers what implements the tested-sample evidence
readers, the JSON loader and the probe (Hermes-tree containment, CS-21), including against the
real T004-extracted Hermes builds (`tools/hermes_builds/extract.py`), which have no `.git` and so
only ever exercise the fingerprint path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from hmp_plugin.compat import (
    DependencySpec,
    GitFingerprintReader,
    _resolve_gitdir,  # white-box test of the git-metadata parser
    compute_read_bridge_fingerprint,
    load_read_compat_list,
    probe_dependencies,
    resolve_git_head_sha,
)

BRIDGE_FILES = ("a.py", "sub/b.py")


def _write_bridge_files(root: Path) -> None:
    (root / "a.py").write_text("A = 1\n")
    (root / "sub").mkdir()
    (root / "sub" / "b.py").write_text("B = 2\n")


# --------------------------------------------------------------------------------------------
# compute_read_bridge_fingerprint (R8 step 3)
# --------------------------------------------------------------------------------------------


def test_fingerprint_is_deterministic(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    fp1 = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    fp2 = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    assert fp1 == fp2
    assert fp1 is not None
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_ignores_bridge_files_list_order(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    fp_forward = compute_read_bridge_fingerprint(tmp_path, list(BRIDGE_FILES))
    fp_reversed = compute_read_bridge_fingerprint(tmp_path, list(reversed(BRIDGE_FILES)))
    assert fp_forward == fp_reversed


def test_fingerprint_changes_with_content(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    before = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    (tmp_path / "a.py").write_text("A = 2\n")
    after = compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES)
    assert before != after


def test_fingerprint_none_on_missing_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("A = 1\n")
    # "sub/b.py" is never created.
    assert compute_read_bridge_fingerprint(tmp_path, BRIDGE_FILES) is None


def test_fingerprint_distinguishes_path_from_content_boundary(tmp_path: Path) -> None:
    # A naive `path + content` concatenation could collide two different splits of the same
    # bytes; the length-prefixed encoding must not.
    (tmp_path / "x").write_text("ab")
    (tmp_path / "y").write_text("")
    fp1 = compute_read_bridge_fingerprint(tmp_path, ["x", "y"])

    (tmp_path / "x").write_text("a")
    (tmp_path / "y").write_text("b")
    fp2 = compute_read_bridge_fingerprint(tmp_path, ["x", "y"])
    assert fp1 != fp2


# --------------------------------------------------------------------------------------------
# resolve_git_head_sha (R8 steps 2, 5): file-reads-only git metadata parsing
# --------------------------------------------------------------------------------------------


def _init_git_dir(root: Path, *, head_ref: str = "refs/heads/main") -> Path:
    git_dir = root / ".git"
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "HEAD").write_text(f"ref: {head_ref}\n")
    return git_dir


def test_no_git_directory_is_none(tmp_path: Path) -> None:
    assert resolve_git_head_sha(tmp_path) is None


def test_loose_ref_resolves(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path)
    sha = "a" * 40
    (git_dir / "refs" / "heads" / "main").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_detached_head_resolves(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    sha = "b" * 40
    (git_dir / "HEAD").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_packed_refs_fallback(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path)  # ref file for refs/heads/main never created
    sha = "c" * 40
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        f"{sha} refs/heads/main\n"
        f"{'d' * 40} refs/heads/other\n"
    )
    assert resolve_git_head_sha(tmp_path) == sha


def test_symbolic_ref_chain(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path, head_ref="refs/heads/alias")
    sha = "e" * 40
    (git_dir / "refs" / "heads" / "alias").write_text("ref: refs/heads/main\n")
    (git_dir / "refs" / "heads" / "main").write_text(sha + "\n")
    assert resolve_git_head_sha(tmp_path) == sha


def test_ref_cycle_raises(tmp_path: Path) -> None:
    git_dir = _init_git_dir(tmp_path, head_ref="refs/heads/a")
    (git_dir / "refs" / "heads" / "a").write_text("ref: refs/heads/b\n")
    (git_dir / "refs" / "heads" / "b").write_text("ref: refs/heads/a\n")
    with pytest.raises(ValueError, match="cycle"):
        resolve_git_head_sha(tmp_path)


def test_unresolvable_ref_raises(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)  # refs/heads/main never created, no packed-refs
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_empty_head_raises(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_malformed_head_raises(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("not a ref and not a sha\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_linked_worktree_gitdir_file(tmp_path: Path) -> None:
    """`.git` as a file pointer (a linked worktree), with `commondir` pointing back at the main
    git dir where `refs`/`packed-refs` actually live."""
    main_git = tmp_path / "main" / ".git"
    (main_git / "refs" / "heads").mkdir(parents=True)
    sha = "1234567890abcdef1234567890abcdef12345678"
    (main_git / "refs" / "heads" / "main").write_text(sha + "\n")

    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    linked_gitdir = tmp_path / "main" / ".git" / "worktrees" / "worktree"
    linked_gitdir.mkdir(parents=True)
    (linked_gitdir / "HEAD").write_text("ref: refs/heads/main\n")
    (linked_gitdir / "commondir").write_text("../..\n")
    (worktree_root / ".git").write_text(f"gitdir: {linked_gitdir}\n")

    assert resolve_git_head_sha(worktree_root) == sha


def test_malformed_gitdir_file_raises(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("not a gitdir pointer\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_gitdir_file_pointing_nowhere_raises(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: does/not/exist\n")
    with pytest.raises(ValueError):
        resolve_git_head_sha(tmp_path)


def test_resolve_gitdir_common_dir_defaults_to_worktree(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    dirs = _resolve_gitdir(tmp_path)
    assert dirs.worktree == git_dir
    assert dirs.common == git_dir


# --------------------------------------------------------------------------------------------
# GitFingerprintReader: the real BuildIdentityReader
# --------------------------------------------------------------------------------------------


def test_reader_no_git_gives_fingerprint_only_identity(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    reader = GitFingerprintReader(BRIDGE_FILES)
    identity = reader.read(tmp_path)
    assert identity is not None
    assert identity.git_sha is None
    assert len(identity.fingerprint) == 64


def test_reader_with_git_gives_both(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    sha = "f" * 40
    (git_dir / "HEAD").write_text(sha + "\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    identity = reader.read(tmp_path)
    assert identity is not None
    assert identity.git_sha == sha


def test_reader_missing_bridge_file_is_unidentifiable(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("A = 1\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    assert reader.read(tmp_path) is None


def test_reader_unresolvable_git_is_unidentifiable(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("garbage\n")
    reader = GitFingerprintReader(BRIDGE_FILES)
    assert reader.read(tmp_path) is None


def test_reader_is_stable_across_calls(tmp_path: Path) -> None:
    _write_bridge_files(tmp_path)
    reader = GitFingerprintReader(BRIDGE_FILES)
    first = reader.read(tmp_path)
    second = reader.read(tmp_path)
    assert first == second


# --------------------------------------------------------------------------------------------
# load_read_compat_list
# --------------------------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data))


def test_load_valid_list(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    _write_json(
        path,
        {
            "format": 1,
            "bridge_files": ["a.py", "b.py"],
            "builds": [
                {
                    "git_sha": "a" * 40,
                    "fingerprint": "b" * 64,
                    "label": "stock",
                    "qualified_by": "run-1",
                    "qualified_at": "2026-01-01",
                }
            ],
        },
    )
    result = load_read_compat_list(path)
    assert result.bridge_files == ("a.py", "b.py")
    assert len(result.builds) == 1
    assert result.builds[0].label == "stock"


def test_load_empty_builds(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    _write_json(path, {"format": 1, "bridge_files": [], "builds": []})
    result = load_read_compat_list(path)
    assert result.builds == ()


def test_load_the_committed_read_compat_builds_json() -> None:
    """The real, shipped file: the research R8 `bridge_files`, always non-empty, and (T064) a
    non-empty `builds` list -- reproducibility against a fresh T063 run is checked separately,
    below, gated on extracted builds being available (`test_committed_read_compat_builds_
    reproduces_a_fresh_t063_run`)."""
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    result = load_read_compat_list(path)
    assert len(result.builds) > 0, "T064 must populate read_compat_builds.json's builds list"
    assert len(result.bridge_files) > 0
    assert "hermes_constants.py" in result.bridge_files


@pytest.mark.parametrize(
    "data",
    [
        {},  # missing format
        {"format": 2, "bridge_files": [], "builds": []},  # wrong format
        {"format": 1, "bridge_files": "not-a-list", "builds": []},
        {"format": 1, "bridge_files": [1, 2], "builds": []},
        {"format": 1, "bridge_files": [], "builds": "not-a-list"},
        {"format": 1, "bridge_files": [], "builds": [{"fingerprint": "x" * 64}]},  # missing label
        {"format": 1, "bridge_files": [], "builds": ["not-an-object"]},
    ],
)
def test_load_malformed_list_raises(tmp_path: Path, data: object) -> None:
    path = tmp_path / "list.json"
    _write_json(path, data)
    with pytest.raises(ValueError):
        load_read_compat_list(path)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_read_compat_list(tmp_path / "does-not-exist.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError):
        load_read_compat_list(path)


# --------------------------------------------------------------------------------------------
# probe_dependencies: synthetic tree exercising the real dependency table's mechanics
# (module import, qualname resolution, signature shape, Hermes-tree containment)
# --------------------------------------------------------------------------------------------


@pytest.fixture()
def synthetic_module_tree(tmp_path: Path):
    """A synthetic Hermes tree (`src`) and a second, foreign tree (`elsewhere`) that is on
    `sys.path` but is not part of the Hermes tree."""
    root = tmp_path / "src"
    root.mkdir()
    (root / "good_mod.py").write_text(
        "class Widget:\n"
        "    def method(self, x):\n"
        "        return x\n"
        "\n"
        "def free_function(a, b=1):\n"
        "    return a + b\n"
    )
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()
    (foreign / "outside_mod.py").write_text("VALUE = 1\n")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(foreign))
    for name in ("good_mod", "outside_mod"):
        sys.modules.pop(name, None)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        sys.path.remove(str(foreign))
        for name in ("good_mod", "outside_mod"):
            sys.modules.pop(name, None)


def test_probe_all_present_and_contained(synthetic_module_tree: Path) -> None:
    specs = (
        DependencySpec("good_mod", "Widget"),
        DependencySpec("good_mod", "Widget.method"),
        DependencySpec("good_mod", "free_function"),
    )
    assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == ()


def test_probe_missing_module(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("does_not_exist_mod"),)
    assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
        "does_not_exist_mod",
    )


def test_probe_missing_attribute(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("good_mod", "NoSuchClass"),)
    assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
        "good_mod.NoSuchClass",
    )


def test_probe_missing_nested_attribute(synthetic_module_tree: Path) -> None:
    specs = (DependencySpec("good_mod", "Widget.no_such_method"),)
    assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
        "good_mod.Widget.no_such_method",
    )


def test_probe_module_outside_the_hermes_tree_is_missing(synthetic_module_tree: Path) -> None:
    """E5: a module that imports fine but lives outside the Hermes tree is not a Hermes
    dependency (a shadow module on `sys.path`)."""
    specs = (DependencySpec("outside_mod"),)
    assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == ("outside_mod",)


def test_probe_without_a_hermes_root_reports_everything_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hmp_plugin import compat as compat_mod

    monkeypatch.setattr(compat_mod, "locate_hermes_root", lambda: None)
    specs = (DependencySpec("good_mod", "Widget"), DependencySpec("other_mod"))
    assert probe_dependencies(specs=specs) == ("good_mod.Widget", "other_mod")


def test_probe_treats_site_packages_and_hermes_home_plugins_as_outside(
    synthetic_module_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E5: inside the root by path, but under `site-packages` or `<HERMES_HOME>/plugins`."""
    site = synthetic_module_tree / "venv" / "lib" / "site-packages"
    site.mkdir(parents=True)
    (site / "shadow_site.py").write_text("def f():\n    return 1\n")
    plugins = synthetic_module_tree / "home" / "plugins" / "evil"
    plugins.mkdir(parents=True)
    (plugins / "shadow_plugin.py").write_text("def f():\n    return 1\n")
    monkeypatch.setenv("HERMES_HOME", str(synthetic_module_tree / "home"))
    sys.path[:0] = [str(site), str(plugins)]
    try:
        specs = (DependencySpec("shadow_site", "f"), DependencySpec("shadow_plugin", "f"))
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
            "shadow_site.f",
            "shadow_plugin.f",
        )
    finally:
        sys.path.remove(str(site))
        sys.path.remove(str(plugins))
        sys.modules.pop("shadow_site", None)
        sys.modules.pop("shadow_plugin", None)


def test_probe_a_moved_file_still_resolves_under_the_root(synthetic_module_tree: Path) -> None:
    """E4: containment is the Hermes tree, not a list of file names, so a symbol that moved to
    another file under the root keeps working."""
    (synthetic_module_tree / "pkg").mkdir()
    (synthetic_module_tree / "pkg" / "__init__.py").write_text("")
    (synthetic_module_tree / "pkg" / "moved.py").write_text("def relocated():\n    return 1\n")
    sys.modules.pop("pkg", None)
    sys.modules.pop("pkg.moved", None)
    try:
        specs = (DependencySpec("pkg.moved", "relocated"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == ()
    finally:
        sys.modules.pop("pkg", None)
        sys.modules.pop("pkg.moved", None)


def test_probe_never_calls_anything(synthetic_module_tree: Path) -> None:
    (synthetic_module_tree / "dangerous_mod.py").write_text(
        "def free_function():\n    raise RuntimeError('must never be called by the probe')\n"
    )
    sys.modules.pop("dangerous_mod", None)
    try:
        specs = (DependencySpec("dangerous_mod", "free_function"),)
        # imported and shape-checked, never invoked
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == ()
    finally:
        sys.modules.pop("dangerous_mod", None)


def test_probe_unwraps_decorated_internals(synthetic_module_tree: Path) -> None:
    """A `@contextmanager` internal (like `gateway.run._profile_runtime_scope`) is defined in
    its own module, not in `contextlib.py`; its stdlib wrapper layer is allowed. A wrapper layer
    defined OUTSIDE the Hermes tree is not (SR-3): the wrapper code is what actually runs."""
    (synthetic_module_tree / "scoped_mod.py").write_text(
        "import contextlib\n"
        "from outside_mod import passthrough\n"
        "\n"
        "@contextlib.contextmanager\n"
        "def scope(home):\n"
        "    yield home\n"
        "\n"
        "@passthrough\n"
        "def wrapped(x):\n"
        "    return x\n"
        "\n"
        "from outside_mod import elsewhere\n"
    )
    (synthetic_module_tree.parent / "elsewhere" / "outside_mod.py").write_text(
        "import functools\n"
        "VALUE = 1\n"
        "def passthrough(fn):\n"
        "    @functools.wraps(fn)\n"
        "    def inner(*a, **k):\n"
        "        return fn(*a, **k)\n"
        "    return inner\n"
        "def elsewhere():\n"
        "    return 1\n"
    )
    for name in ("scoped_mod", "outside_mod"):
        sys.modules.pop(name, None)
    try:
        import inspect as _inspect

        import scoped_mod  # type: ignore[import-not-found]

        assert _inspect.getsourcefile(scoped_mod.scope).endswith("contextlib.py")  # the trap
        specs = (DependencySpec("scoped_mod", "scope"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == ()
        # `wrapped`'s OUTER layer (`passthrough`'s `inner`) is defined outside the Hermes tree.
        specs = (DependencySpec("scoped_mod", "wrapped"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
            "scoped_mod.wrapped",
        )
        # Unwrapping never hides a real definition outside the tree.
        specs = (DependencySpec("scoped_mod", "elsewhere"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
            "scoped_mod.elsewhere",
        )
    finally:
        sys.modules.pop("scoped_mod", None)


def test_probe_treats_a_wrapped_cycle_as_missing(synthetic_module_tree: Path) -> None:
    """SR-3: `inspect.unwrap` raises `ValueError` on a `__wrapped__` cycle. Fail closed."""
    (synthetic_module_tree / "cyclic_mod.py").write_text(
        "def a(x):\n"
        "    return x\n"
        "def b(x):\n"
        "    return x\n"
        "a.__wrapped__ = b\n"
        "b.__wrapped__ = a\n"
    )
    sys.modules.pop("cyclic_mod", None)
    try:
        specs = (DependencySpec("cyclic_mod", "a"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
            "cyclic_mod.a",
        )
    finally:
        sys.modules.pop("cyclic_mod", None)


def test_probe_treats_an_undeterminable_source_as_missing(synthetic_module_tree: Path) -> None:
    """SR-3: an object `inspect.getsourcefile` cannot place (a `functools.partial`, a callable
    instance, a C function) must never fall back to the module's own file."""
    (synthetic_module_tree / "partial_mod.py").write_text(
        "import functools\n"
        "def base(x, y):\n"
        "    return x + y\n"
        "curried = functools.partial(base, 1)\n"
    )
    sys.modules.pop("partial_mod", None)
    try:
        specs = (DependencySpec("partial_mod", "curried"),)
        assert probe_dependencies(hermes_root=synthetic_module_tree, specs=specs) == (
            "partial_mod.curried",
        )
    finally:
        sys.modules.pop("partial_mod", None)


def test_probe_named_parameter_is_not_satisfied_by_kwargs(synthetic_module_tree: Path) -> None:
    """E6: a writer that only has `**kwargs` would silently swallow `paused`."""
    (synthetic_module_tree / "writer_mod.py").write_text(
        "def named(name, paused=False, *, repeat=None):\n    return 1\n"
        "def swallowing(name, **kwargs):\n    return 1\n"
        "def positional_only(name, paused=False, /):\n    return 1\n"
        "def three(a, b, c, d=None):\n    return 1\n"
        "def two(a, b):\n    return 1\n"
    )
    sys.modules.pop("writer_mod", None)
    try:
        params = frozenset({"name", "paused", "repeat"})
        assert probe_dependencies(
            hermes_root=synthetic_module_tree,
            specs=(DependencySpec("writer_mod", "named", params=params),),
        ) == ()
        assert probe_dependencies(
            hermes_root=synthetic_module_tree,
            specs=(
                DependencySpec("writer_mod", "swallowing", params=frozenset({"paused"})),
                DependencySpec("writer_mod", "positional_only", params=frozenset({"paused"})),
                DependencySpec("writer_mod", "two", min_positional=3),
            ),
        ) == ("writer_mod.swallowing", "writer_mod.positional_only", "writer_mod.two")
        assert probe_dependencies(
            hermes_root=synthetic_module_tree,
            specs=(DependencySpec("writer_mod", "three", min_positional=3),),
        ) == ()
    finally:
        sys.modules.pop("writer_mod", None)


def test_dependency_tables_split_session_browsing_and_name_paused() -> None:
    from hmp_plugin.compat import (
        CRON_DEPENDENCIES,
        DIRECT_SEND_DEPENDENCIES,
        MODEL_DEPENDENCIES,
        READ_CORE_DEPENDENCIES,
        READ_DEPENDENCIES,
        SESSION_BROWSING_DEPENDENCIES,
    )

    browsing = {(d.module, d.qualname) for d in SESSION_BROWSING_DEPENDENCIES}
    assert browsing == {
        ("hermes_state", "SessionDB.list_sessions_rich"),
        ("hermes_state", "SessionDB.get_session"),
    }
    assert not browsing & {(d.module, d.qualname) for d in READ_CORE_DEPENDENCIES}
    assert ("hermes_state", "SessionDB.get_session") in {
        (d.module, d.qualname) for d in DIRECT_SEND_DEPENDENCIES
    }
    assert READ_DEPENDENCIES == READ_CORE_DEPENDENCIES + SESSION_BROWSING_DEPENDENCIES
    writer = next(d for d in CRON_DEPENDENCIES if d.qualname == "create_job")
    assert "paused" in writer.params
    assert any(d.qualname == "_write_profile_model" and d.min_positional == 3
               for d in MODEL_DEPENDENCIES)
    assert not any(d.module == "fastapi" for d in MODEL_DEPENDENCIES)


def test_probe_default_specs_is_the_core_read_table() -> None:
    import inspect as _inspect

    from hmp_plugin.compat import READ_CORE_DEPENDENCIES

    default = _inspect.signature(probe_dependencies).parameters["specs"].default
    assert default is READ_CORE_DEPENDENCIES
    assert len(READ_CORE_DEPENDENCIES) > 0


# --------------------------------------------------------------------------------------------
# Real T004-extracted builds (research R10; no .git -> fingerprint-only path, CS-19/CS-21).
# Gated on the same HMP_HERMES_BUILDS_DIR extraction location tools/ci/check_all.sh uses; skipped
# (not failed) when it has not been produced, exactly like test_register.py's HMP_HERMES_SRC gate.
#
# T035 (worker f1/w-refclient): the default is namespaced by this checkout's own worktree
# directory name, the same change and for the same reason as tools/ci/check_all.sh's default (see
# that file: a single fixed "$TMPDIR/hermes_bot_mobile_hermes_builds" shared by every worktree on
# the host makes concurrent F1 workers race each other's extractions). Both defaults derive the
# same path for the same worktree because both key off the worktree directory's basename, so a
# worker that extracted once via check_all.sh's default still finds it here without setting
# HMP_HERMES_BUILDS_DIR explicitly. An explicit HMP_HERMES_BUILDS_DIR (as the F1 worker rules'
# "Load limits" require -- a private extraction under the worker's own scratchpad) always wins.
# --------------------------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BUILDS_DIR = (
    Path(tempfile.gettempdir()) / f"hermes_bot_mobile_hermes_builds-{_REPO_ROOT.name}"
)
_BUILDS_DIR = Path(os.environ.get("HMP_HERMES_BUILDS_DIR", str(_DEFAULT_BUILDS_DIR)))
_STOCK_SRC = _BUILDS_DIR / "stock-base" / "src"
_EXPERIMENTAL_SRC = _BUILDS_DIR / "experimental" / "src"
# Machine-local optional builds (tools/hermes_builds/builds.yaml); see the T064 reproduction test.
_MACHINE_LOCAL_LABELS = (
    "owner-local", "upstream", "v921-git", "v924-archive", "v924-git",
    "omarchy-y520-git",
)

_extracted_builds_reason = (
    f"no T004 extraction at {_BUILDS_DIR} "
    f"(run: python3 tools/hermes_builds/extract.py --out {_BUILDS_DIR} "
    "--builds stock-base,experimental --skip-venv)"
)


def _committed_bridge_files() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    return load_read_compat_list(path).bridge_files


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_has_no_git_and_uses_fingerprint_path() -> None:
    assert not (_STOCK_SRC / ".git").exists()
    reader = GitFingerprintReader(_committed_bridge_files())
    identity = reader.read(_STOCK_SRC)
    assert identity is not None
    assert identity.git_sha is None  # CS-19: no .git -> only a fingerprint-only entry can match
    assert len(identity.fingerprint) == 64


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_fingerprint_is_stable_across_reads() -> None:
    bridge_files = _committed_bridge_files()
    reader = GitFingerprintReader(bridge_files)
    first = reader.read(_STOCK_SRC)
    second = reader.read(_STOCK_SRC)
    third = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    assert first is not None
    assert first == second
    assert first.fingerprint == third


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_real_builds_have_distinct_fingerprints() -> None:
    bridge_files = _committed_bridge_files()
    stock_fp = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    experimental_fp = compute_read_bridge_fingerprint(_EXPERIMENTAL_SRC, bridge_files)
    assert stock_fp is not None
    assert experimental_fp is not None
    assert stock_fp != experimental_fp


@pytest.mark.skipif(not _STOCK_SRC.is_dir(), reason=_extracted_builds_reason)
def test_real_build_every_bridge_file_present() -> None:
    """A missing listed file would make the build unidentifiable (R8 step 5) — confirm the
    committed list actually resolves against a real extracted tree, file by file, so a failure
    here points at exactly which file is missing rather than just "fingerprint is None"."""
    missing = [f for f in _committed_bridge_files() if not (_STOCK_SRC / f).is_file()]
    assert missing == []


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_evidence_matching_against_real_builds_fingerprint_only_path() -> None:
    """CS-19's "no .git -> fingerprint-only entry" case, driven by the real fingerprint of a real
    extracted build. The match is evidence (`tested`), never an admission."""
    from hmp_plugin.compat import BuildEntry, match_build

    bridge_files = _committed_bridge_files()
    reader = GitFingerprintReader(bridge_files)
    stock_fp = compute_read_bridge_fingerprint(_STOCK_SRC, bridge_files)
    assert stock_fp is not None
    entry = BuildEntry(
        fingerprint=stock_fp,
        git_sha=None,
        label="stock-base (test)",
        qualified_by="test_compat",
        qualified_at="2026-01-01",
    )
    stock_identity = reader.read(_STOCK_SRC)
    experimental_identity = reader.read(_EXPERIMENTAL_SRC)
    assert stock_identity is not None and experimental_identity is not None
    assert match_build(stock_identity, (entry,)) is entry
    assert match_build(experimental_identity, (entry,)) is None


@pytest.mark.skipif(
    not (_STOCK_SRC.is_dir() and _EXPERIMENTAL_SRC.is_dir()), reason=_extracted_builds_reason
)
def test_committed_read_compat_builds_reproduces_a_fresh_t063_run(tmp_path: Path) -> None:
    """T064 acceptance: an independent re-run of T063's `tools/compat/run_matrix.py` must
    reproduce every entry in the committed `read_compat_builds.json` -- this replaces the old "the
    committed list starts empty" placeholder assertion now that T064 has populated it. Slow (spins
    up a real gateway per build); skipped like the rest of this file's real-build tests unless
    T004's extraction has already been run."""
    path = Path(__file__).resolve().parents[2] / "hmp_plugin" / "read_compat_builds.json"
    committed = load_read_compat_list(path)
    assert len(committed.builds) > 0, "read_compat_builds.json's builds list is still empty"

    run_matrix = Path(__file__).resolve().parents[3] / "tools" / "compat" / "run_matrix.py"
    json_out = tmp_path / "matrix.json"
    # A machine-local optional build (builds.yaml `optional: true`, e.g. `owner-local`) can only be
    # re-run where its clone exists; everywhere else it is left out of the re-run and of the
    # comparison below. Every other committed entry must still be reproduced.
    machine_local = {
        label for label in _MACHINE_LOCAL_LABELS if not (_BUILDS_DIR / label / "src").is_dir()
    }
    expected = [entry for entry in committed.builds if entry.label not in machine_local]
    labels = sorted({entry.label for entry in expected})
    # A present `git_install` build (e.g. `owner-local`) records its git SHA from its clone, which
    # lives outside the located `_refs`; `HMP_HERMES_REFS_DIR` names that directory (the same one
    # given to extract.py / run_matrix.py `--refs-dir`).
    refs_dir = os.environ.get("HMP_HERMES_REFS_DIR")
    result = subprocess.run(
        [
            sys.executable, str(run_matrix),
            "--builds-dir", str(_BUILDS_DIR),
            "--out", str(tmp_path / "scratch"),
            "--builds", ",".join(labels),
            "--json-out", str(json_out),
            *(("--refs-dir", refs_dir) if refs_dir else ()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"run_matrix.py failed:\n{result.stdout}\n{result.stderr}"
    fresh = json.loads(json_out.read_text(encoding="utf-8"))
    fresh_by_label = {e["label"]: e for e in fresh["candidate_entries"]}
    for entry in expected:
        assert entry.label in fresh_by_label, (
            f"{entry.label!r} in read_compat_builds.json was not reproduced by a fresh T063 run "
            f"(fresh qualified labels: {sorted(fresh_by_label)})"
        )
        fresh_entry = fresh_by_label[entry.label]
        assert fresh_entry["fingerprint"] == entry.fingerprint, entry.label
        assert fresh_entry["git_sha"] == entry.git_sha, entry.label
