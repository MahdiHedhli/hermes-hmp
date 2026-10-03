#!/usr/bin/env python3
"""Compute the read-bridge file list mechanically (research R8, CS-21; T028).

The list is every Hermes source file that defines a symbol the read bridge reaches. It is the
union of two sets, computed for one Hermes build:

1. **The AST import set.** Every absolute, non-standard-library module that
   `server/hmp_plugin/bridge.py` imports, mapped to its file in the Hermes tree. This is a pure
   file mapping; nothing is imported.
2. **The probe-resolved set.** For each entry of `hmp_plugin.compat.READ_DEPENDENCIES` (the
   dependency probe's list, which covers every internal the bridge reaches; `test_bridge.py` keeps
   the two in step), `inspect.getsourcefile` of the module and of the resolved attribute. This
   imports the Hermes modules, so it must run in that build's own interpreter, with the tree
   importable. `--ast-only` skips it.

Imports inside the reviewed `HermesApi` cron/model methods (`FEATURE_METHOD_IMPORTS`) belong to
those features' own boundaries: they are left out of the target sets above and instead each file is
required to be in `mobile_model_supported_builds.json` / `mobile_cron_supported_builds.json`. The
check proves declared source-file coverage for the imports it sees; it is not a complete call graph
and attests nothing about installed third-party packages.

The committed `bridge_files` list (`server/hmp_plugin/read_compat_builds.json`) must be a superset
of both sets on every qualified build. `--check` verifies that. `--write` merges the computed set
into the committed list. That is a data-only change, and it changes every build fingerprint.

Isolation: Hermes may read `HERMES_HOME` at import time. The tool always points it at a fresh
temporary directory, and refuses a `--hermes-src` inside the real home's `.hermes`. It never
writes into the Hermes tree.

Usage (from the repository root, with the build's venv interpreter):
    <build>/src/.venv/bin/python tools/compat/bridge_files.py --hermes-src <build>/src --check
    python3 tools/compat/bridge_files.py --hermes-src <build>/src --ast-only --check
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import os
import sys
import sysconfig
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
BRIDGE_PATH = SERVER_DIR / "hmp_plugin" / "bridge.py"
READ_COMPAT_PATH = SERVER_DIR / "hmp_plugin" / "read_compat_builds.json"
# Amendment F2 (direct send, HMP_V1.md §7a GAP-2, data-model.md "Direct-send qualification list"):
# a SEPARATE committed list, probed against `compat.DIRECT_SEND_DEPENDENCIES` instead of
# `READ_DEPENDENCIES` (--dependencies-attr below). The AST import set is the same `bridge.py` for
# both targets -- one module serves both the read and the guarded-write path -- only the probe set
# and the committed file being checked/merged differ. Never write the direct-send union into
# `read_compat_builds.json`: that would force every already-qualified read build to requalify for a
# file reads never touch (`hermes_cli/active_sessions.py`).
DIRECT_SEND_COMPAT_PATH = SERVER_DIR / "hmp_plugin" / "direct_send_supported_builds.json"
# The cron and model features keep their own qualification boundaries; they are not part of the
# read/direct/approval lists above and those lists must not grow to cover them.
FEATURE_MANIFEST_PATHS: Mapping[str, Path] = {
    "model": SERVER_DIR / "hmp_plugin" / "mobile_model_supported_builds.json",
    "cron": SERVER_DIR / "hmp_plugin" / "mobile_cron_supported_builds.json",
}
# Audited, exact (class, method) -> (feature manifest, modules that method may import). An import
# is classified as a feature import ONLY at one of these sites and ONLY for a listed module; the
# same module imported anywhere else in `bridge.py` stays in the target's AST set. Those methods
# are reached only from the cron/model route handlers, behind their own qualification gates, never
# from the read, direct-send or approval paths. A new such method must be added here after review.
FEATURE_METHOD_IMPORTS: Mapping[tuple[str, str], tuple[str, frozenset[str]]] = {
    ("HermesApi", "model_config"): ("model", frozenset({"hermes_cli.config"})),
    ("HermesApi", "write_profile_model"): (
        "model",
        frozenset({"hermes_cli.web_routers.profiles"}),
    ),
    ("HermesApi", "create_mobile_cron"): (
        "cron",
        frozenset({"cron.scheduler", "tools.cronjob_prompt_scan"}),
    ),
    ("HermesApi", "edit_mobile_cron"): (
        "cron",
        frozenset(
            {"cron.jobs", "cron.lifecycle_guard", "cron.scheduler", "tools.cronjob_prompt_scan"}
        ),
    ),
}

# Not Hermes: the plugin's own runtime packages (`tools/ci/check_plugin_surface.py` S1), plus
# `fastapi`, which is an external package the Hermes install provides, not a plugin runtime
# package. `bridge.write_profile_model` imports `fastapi.HTTPException` lazily only to recognise
# the native profile writer's validation refusal, so the AST scan must not map it to a Hermes file.
# This classifies the import; it attests nothing about the installed package's provenance.
NON_HERMES_TOP_LEVEL: frozenset[str] = frozenset({"aiohttp", "cryptography", "fastapi", "qrcode"})


class BridgeFilesError(RuntimeError):
    pass


def _import_sites(tree: ast.AST) -> list[tuple[str, tuple[str, ...]]]:
    """Every absolute import as `(module, enclosing scope)`. The scope is the chain of enclosing
    `class:`/`def:` names, outermost first."""
    sites: list[tuple[str, tuple[str, ...]]] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            inner = scope
            if isinstance(child, ast.ClassDef):
                inner = (*scope, f"class:{child.name}")
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                inner = (*scope, f"def:{child.name}")
            if isinstance(child, ast.Import):
                sites.extend((alias.name, scope) for alias in child.names)
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                sites.append((child.module, scope))
            visit(child, inner)

    visit(tree, ())
    return sites


def split_ast_imports(
    bridge_source: str,
    *,
    exclude_modules: frozenset[str] = frozenset(),
    typed_modules: frozenset[str] = frozenset(),
) -> tuple[list[str], dict[str, set[str]]]:
    """`(target imports, feature imports by manifest key)` for `bridge.py`.

    Target imports are the absolute module names `bridge.py` imports, excluding the standard
    library, `__future__`, the plugin's non-Hermes runtime packages and `exclude_modules`. Lazy
    imports inside functions count.

    `exclude_modules` (amendment F2): `bridge.py` serves several compat targets from one file and
    the scan has no per-target granularity. A module imported ONLY for a different target (tracked
    by that OTHER target's own `DependencySpec` tuple in `compat.py`, e.g.
    `hermes_cli.active_sessions` for direct send) is excluded so checking the READ target does not
    spuriously demand it; an import not declared by ANY target's tuple is never excluded.

    Feature imports (`FEATURE_METHOD_IMPORTS`) are split out only at their exact reviewed
    class/method site and only for the listed modules, and never when the module is in
    `typed_modules` (the selected target's own dependency tuple): a dependency the target relies on
    stays in the target set whatever else classifies it."""
    tree = ast.parse(bridge_source)
    target: set[str] = set()
    feature: dict[str, set[str]] = {}
    for name, scope in _import_sites(tree):
        top = name.split(".", 1)[0]
        if top == "__future__" or top in sys.stdlib_module_names or top in NON_HERMES_TOP_LEVEL:
            continue
        reviewed = None
        if len(scope) == 2 and scope[0].startswith("class:") and scope[1].startswith("def:"):
            reviewed = FEATURE_METHOD_IMPORTS.get((scope[0][6:], scope[1][4:]))
        if reviewed is not None and name in reviewed[1] and name not in typed_modules:
            feature.setdefault(reviewed[0], set()).add(name)
            continue
        if name in exclude_modules:
            continue
        target.add(name)
    return sorted(target), feature


def ast_imported_modules(
    bridge_source: str,
    *,
    exclude_modules: frozenset[str] = frozenset(),
    typed_modules: frozenset[str] = frozenset(),
) -> list[str]:
    """The target half of `split_ast_imports`."""
    return split_ast_imports(
        bridge_source, exclude_modules=exclude_modules, typed_modules=typed_modules
    )[0]


def module_file(hermes_src: Path, module: str) -> str:
    """The Hermes-relative source file of `module`, found by path only (never imported)."""
    parts = module.split(".")
    for candidate in (Path(*parts).with_suffix(".py"), Path(*parts) / "__init__.py"):
        if (hermes_src / candidate).is_file():
            return candidate.as_posix()
    raise BridgeFilesError(f"module {module!r} not found under the Hermes tree")


def ast_set(
    hermes_src: Path,
    bridge_path: Path = BRIDGE_PATH,
    *,
    exclude_modules: frozenset[str] = frozenset(),
    typed_modules: frozenset[str] = frozenset(),
) -> set[str]:
    source = bridge_path.read_text(encoding="utf-8")
    return {
        module_file(hermes_src, m)
        for m in ast_imported_modules(
            source, exclude_modules=exclude_modules, typed_modules=typed_modules
        )
    }


def feature_boundaries(
    hermes_src: Path,
    bridge_path: Path = BRIDGE_PATH,
    *,
    typed_modules: frozenset[str] = frozenset(),
    manifest_paths: Mapping[str, Path] = FEATURE_MANIFEST_PATHS,
) -> dict[str, list[str]]:
    """Hermes files of the classified feature imports, each required to be in its OWN feature
    manifest's `bridge_files`. A module with no Hermes source file, or a missing or malformed
    manifest, or an uncovered file, fails. Proves declared source-file coverage only: not a call
    graph, and nothing about the installed third-party packages."""
    _, feature = split_ast_imports(
        bridge_path.read_text(encoding="utf-8"), typed_modules=typed_modules
    )
    out: dict[str, list[str]] = {}
    for key, modules in sorted(feature.items()):
        files = {module_file(hermes_src, m) for m in modules}
        path = manifest_paths[key]
        try:
            committed = set(load_committed(path))
        except (OSError, ValueError, AttributeError) as exc:
            raise BridgeFilesError(f"{key} feature manifest is unreadable or malformed") from exc
        uncovered = sorted(files - committed)
        if uncovered:
            raise BridgeFilesError(f"{key} feature manifest lacks {uncovered}")
        out[key] = sorted(files)
    return out


def _relative(path: str | None, root: Path, what: str) -> str:
    if path is None:
        raise BridgeFilesError(f"no source file for {what}")
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise BridgeFilesError(f"{what} is defined outside the Hermes tree") from exc


def _wrapper_chain_source_files(
    obj: object, *, _seen: frozenset[int] = frozenset()
) -> list[str] | None:
    """Mirrors `hmp_plugin.compat._wrapper_chain_source_files` (SR-3): every source file in
    `obj`'s `__wrapped__` chain, outermost first. `None` on an undeterminable file or a cycle."""
    if id(obj) in _seen:
        return None
    try:
        source = inspect.getsourcefile(obj)  # type: ignore[arg-type]
    except TypeError:
        return None
    if source is None:
        return None
    wrapped = getattr(obj, "__wrapped__", None)
    if wrapped is None:
        return [source]
    rest = _wrapper_chain_source_files(wrapped, _seen=_seen | {id(obj)})
    return None if rest is None else [source, *rest]


def probe_set(hermes_src: Path, specs: Iterable[object]) -> set[str]:
    """`inspect.getsourcefile` of every probed module and attribute, walking the FULL
    `__wrapped__` chain and including every non-stdlib layer's file (SR-3: mirrors
    `hmp_plugin.compat.probe_read_dependencies`'s CS-21 containment rule, so the committed
    `bridge_files` list ends up a superset of what that rule actually requires). Imports Hermes.
    """
    root = hermes_src.resolve()
    stdlib_dir = Path(sysconfig.get_paths()["stdlib"]).resolve()
    out: set[str] = set()
    for spec in specs:
        module_name = spec.module  # type: ignore[attr-defined]
        qualname = spec.qualname  # type: ignore[attr-defined]
        module = importlib.import_module(module_name)
        out.add(_relative(inspect.getsourcefile(module), root, module_name))
        if not qualname:
            continue
        obj: object = module
        for part in qualname.split("."):
            obj = getattr(obj, part)
        chain = _wrapper_chain_source_files(obj)
        if chain is None:
            raise BridgeFilesError(
                f"cannot determine the wrapper-chain source files of {module_name}.{qualname}"
            )
        for source in chain:
            resolved = Path(source).resolve()
            try:
                resolved.relative_to(stdlib_dir)
                continue  # stdlib: never part of bridge_files
            except ValueError:
                pass
            out.add(_relative(source, root, f"{module_name}.{qualname}"))
    return out


def load_committed(path: Path = READ_COMPAT_PATH) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("bridge_files")
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise BridgeFilesError("bridge_files is not a list of strings")
    return files


def write_merged(computed: set[str], path: Path = READ_COMPAT_PATH) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = sorted(set(data.get("bridge_files") or []) | computed)
    data["bridge_files"] = merged
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return merged


def _isolate_hermes_home() -> tempfile.TemporaryDirectory[str]:
    home = tempfile.TemporaryDirectory(prefix="hmp-bridge-files-")
    os.environ["HERMES_HOME"] = home.name
    for name in list(os.environ):
        if name.startswith("HERMES_") and name != "HERMES_HOME":
            del os.environ[name]
    return home


def _refuse_real_home(path: Path) -> None:
    real_hermes = (Path.home() / ".hermes").resolve()
    resolved = path.resolve()
    if resolved == real_hermes or real_hermes in resolved.parents:
        raise BridgeFilesError("refusing a Hermes tree inside the real home's .hermes")


# Every compat target's own DependencySpec tuple in `hmp_plugin.compat`, by the CLI's
# `--dependencies-attr` spelling. Used only to compute each target's cross-target exclude set
# above -- never to change which specs are actually probed for a given `--dependencies-attr`.
_ALL_DEPENDENCY_ATTRS: tuple[str, ...] = (
    "READ_DEPENDENCIES",
    "DIRECT_SEND_DEPENDENCIES",
    "PHONE_CHAT_DEPENDENCIES",
)


def compute(
    hermes_src: Path, *, ast_only: bool, dependencies_attr: str = "READ_DEPENDENCIES"
) -> dict[str, list[str]]:
    _refuse_real_home(hermes_src)
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))
    if str(hermes_src) not in sys.path:
        sys.path.insert(0, str(hermes_src))
    import hmp_plugin.compat as compat_module

    dependencies = getattr(compat_module, dependencies_attr)
    this_modules = {spec.module for spec in dependencies}
    typed = frozenset(this_modules)
    other_modules: set[str] = set()
    for attr in _ALL_DEPENDENCY_ATTRS:
        if attr == dependencies_attr or not hasattr(compat_module, attr):
            continue
        other_modules |= {spec.module for spec in getattr(compat_module, attr)}
    exclude = frozenset(other_modules - this_modules)

    result = {"ast": sorted(ast_set(hermes_src, exclude_modules=exclude, typed_modules=typed))}
    # Checked here, before any probe import or `--write`, and kept out of the target's union.
    for key, files in feature_boundaries(hermes_src, typed_modules=typed).items():
        result[f"feature:{key}"] = files
    if not ast_only:
        home = _isolate_hermes_home()
        try:
            result["probe"] = sorted(probe_set(hermes_src, dependencies))
        finally:
            home.cleanup()
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--hermes-src", required=True, type=Path)
    parser.add_argument("--ast-only", action="store_true", help="skip the import-based probe set")
    parser.add_argument(
        "--check", action="store_true", help="fail unless the committed list has every file"
    )
    parser.add_argument(
        "--write", action="store_true", help="merge the computed set into the committed list"
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=READ_COMPAT_PATH,
        help="committed bridge_files JSON to check/merge against "
        "(default: read_compat_builds.json)",
    )
    parser.add_argument(
        "--dependencies-attr",
        default="READ_DEPENDENCIES",
        help="name of the hmp_plugin.compat tuple to probe "
        "(READ_DEPENDENCIES, DIRECT_SEND_DEPENDENCIES or PHONE_CHAT_DEPENDENCIES)",
    )
    args = parser.parse_args(argv)

    try:
        sets = compute(
            args.hermes_src, ast_only=args.ast_only, dependencies_attr=args.dependencies_attr
        )
    except BridgeFilesError as exc:
        print(f"bridge_files: {exc}", file=sys.stderr)
        return 2
    # `feature:*` entries were each checked against their own manifest; they are not target files.
    computed = set().union(*(set(v) for k, v in sets.items() if not k.startswith("feature:")))
    print(json.dumps({**sets, "union": sorted(computed)}, indent=2))

    if args.write:
        write_merged(computed, args.target)
    if args.check:
        missing = sorted(computed - set(load_committed(args.target)))
        if missing:
            print(f"bridge_files: committed list lacks {missing}", file=sys.stderr)
            return 1
        print("bridge_files: committed list contains every computed file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
