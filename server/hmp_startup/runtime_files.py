"""Original recipe-derived combined file plan; snapshot DATA, never admission."""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import NamedTuple

from hmp_plugin import presentation_startup_artifacts as _artifacts
from hmp_plugin.presentation_gateway_package import _PRIVATE, _table_rows
from hmp_plugin.presentation_startup_artifacts import ExpectedArtifact, _expected, _HashedArtifact

_PRIVATE_COMPONENTS = frozenset(
    name.casefold()
    for name in (*_PRIVATE, ".ssh", ".aws", ".gnupg", "keychains", "secrets", "chats")
)
_PREFIX = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z", re.ASCII)


class RuntimeFilesError(Exception):
    def __init__(self):
        super().__init__("BI1_RUNTIME_FILE_PLAN_REFUSED")


def _require(value):
    if value is not True:
        raise RuntimeFilesError


def _pairs(rows):
    result = {}
    for key, value in rows:
        _require(key not in result)
        result[key] = value
    return result


def _document(raw, kind, generation, keys, schema=1):
    _require(type(schema) is int and schema in (1, 2) and type(raw) is bytes)
    value = json.loads(raw, object_pairs_hook=_pairs)
    _require(
        type(value) is dict
        and value.keys() == keys
        and type(value["schema"]) is int
        and value["schema"] == schema
        and type(value["kind"]) is str
        and value["kind"] == kind
        and type(value["generation"]) is str
        and value["generation"] == generation
        and json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
        == raw
    )
    return value


def _path(value):
    _require(
        type(value) is str
        and 1 < len(value.encode("utf-8")) <= 4096
        and value.startswith("/")
        and all(32 <= ord(c) != 127 for c in value)
    )
    parts = value[1:].split("/")
    _require(
        len(parts) <= 64
        and all(
            part not in ("", ".", "..")
            and part.casefold() not in _PRIVATE_COMPONENTS
            and not part.casefold().startswith(".env.")
            for part in parts
        )
    )
    return value


def _inside(path, root):
    return path == root or path.startswith(root + "/")


def _typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(right) is dict:
        return left.keys() == right.keys() and all(
            _typed_equal(left[k], v) for k, v in right.items()
        )
    if type(right) is list:
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    _require(type(right) in (str, int, bool, type(None)))
    return left == right


def _library_name(name):
    if name.endswith(".dylib"):
        return len(name) > 6
    prefix, marker, suffix = name.rpartition(".so")
    return bool(
        prefix
        and marker
        and (
            not suffix
            or (
                suffix.startswith(".")
                and all(
                    part and all("0" <= c <= "9" for c in part) for part in suffix[1:].split(".")
                )
            )
        )
    )


class RuntimePackage(NamedTuple):
    path: str
    entries: tuple
    files: tuple


class LinkHop(NamedTuple):
    path: str
    target: bytes
    destination: str

    def __repr__(self):
        return "<SelectedExecutableLinkHop DATA redacted>"


class ExecutableLinkPlan(NamedTuple):
    hops: tuple
    target: ExpectedArtifact
    uid: int
    mode: int
    text_bytes: int

    def __repr__(self):
        return "<SelectedExecutableLinkPlan DATA redacted>"


def _link_plan(value, executable, permitted, startup_uid):
    _require(type(value) is dict and value.keys() == {"hops", "final"})
    rows, final = value["hops"], value["final"]
    _require(type(rows) is list and 1 <= len(rows) <= 8)
    hops, seen, path = [], set(), executable
    for row in rows:
        _require(type(row) is dict and row.keys() == {"path", "target", "destination"})
        selected = _path(row["path"])
        destination = _path(row["destination"])
        permitted(selected)
        permitted(destination)
        _require(selected == path and selected not in seen)
        seen.add(selected)
        text = row["target"]
        _require(type(text) is str and 1 <= len(text) <= 4096
                 and all(32 <= ord(c) != 127 for c in text))
        parts = text.split("/")
        if text.startswith("/"):
            suffix = parts[1:]
        else:
            leading = 0
            while leading < len(parts) and parts[leading] == "..":
                leading += 1
            _require(leading <= len(posixpath.dirname(selected).split("/")) - 1)
            suffix = parts[leading:]
        _require(bool(suffix) and all(
            part not in ("", ".", "..")
            and part.casefold() not in _PRIVATE_COMPONENTS
            and not part.casefold().startswith(".env.") for part in suffix
        ))
        try:
            target = text.encode("utf-8")
        except UnicodeError:
            raise RuntimeFilesError from None
        _require(1 <= len(target) <= 4096)
        lexical = posixpath.normpath(
            text if text.startswith("/") else posixpath.join(posixpath.dirname(selected), text)
        )
        _require(lexical == destination and destination not in seen)
        hops.append(LinkHop(selected, target, destination))
        path = destination
    _require(type(final) is dict
             and final.keys() == {"path", "size", "sha256", "uid", "mode"})
    final_path = _path(final["path"])
    permitted(final_path)
    _require(final_path == path and final_path not in seen
             and type(startup_uid) is int and startup_uid >= 0
             and type(final["uid"]) is int and final["uid"] in (0, startup_uid)
             and type(final["mode"]) is int and 0 <= final["mode"] <= 0o777
             and not final["mode"] & 0o022 and bool(final["mode"] & 0o111))
    target = ExpectedArtifact(final_path, final["size"], final["sha256"])
    _expected((target,))
    return ExecutableLinkPlan(tuple(hops), target, final["uid"], final["mode"],
                              sum(len(hop.target) for hop in hops))


class RuntimeFilePlan(NamedTuple):
    entry_binding: tuple
    recipe_binding: tuple
    plugin_binding: tuple
    dependency_raw: bytes
    interpreter_raw: bytes
    runtime: object
    packages: tuple
    pending: tuple
    all_files: tuple
    loose: tuple
    prior: tuple
    declarations: tuple
    dependency_paths: tuple
    modules: tuple
    executable_link: ExecutableLinkPlan | None

    def __repr__(self):
        return "<OriginalCombinedRuntimeFilePlan DATA redacted>"


def build_runtime_plan(eb, rb, pb, entry_root, entry_entries, entry_files, wrapper):
    """Regular-only D1 projection; no executable-link fallback."""
    return _build_runtime_plan(eb, rb, pb, entry_root, entry_entries, entry_files, wrapper, 1)


def build_runtime_link_plan(eb, rb, pb, entry_root, entry_entries, entry_files, wrapper):
    """Explicit selected-link DATA; actual observation needs the original IO composition."""
    return _build_runtime_plan(eb, rb, pb, entry_root, entry_entries, entry_files, wrapper, 2)


def _build_runtime_plan(eb, rb, pb, entry_root, entry_entries, entry_files, wrapper, schema):
    _require(type(schema) is int and schema in (1, 2)
             and type(rb[0].expected.recipe_schema) is int
             and rb[0].expected.recipe_schema == schema)
    generation = rb[0].expected.selection.generation
    environment = rb[0].activation_scope.environment
    runtime = eb[2][6].interpreter
    dep_raw, interp_raw = rb[4][3][3][1], rb[4][3][4][1]
    dep = _document(
        dep_raw,
        "HMP_GATEWAY_DEPENDENCIES",
        generation,
        {
            "schema",
            "kind",
            "generation",
            "environment",
            "packages",
            "files",
            "libraries",
            "modules",
        },
    )
    interp = _document(
        interp_raw,
        "HMP_GATEWAY_INTERPRETER",
        generation,
        {"schema", "kind", "generation", "runtime", "loader_policy", "packages", "files"}
        | ({"executable_link"} if schema == 2 else set()),
        schema,
    )
    _require(
        type(dep["environment"]) is str
        and dep["environment"] == environment
        and type(interp["loader_policy"]) is str
        and interp["loader_policy"] == rb[0].expected.selection.loader_policy
    )
    expected_runtime = {
        "paths": list(runtime.paths),
        "version": list(runtime.version),
        "flags": list(runtime.flags),
        "implementation": list(runtime.implementation),
        "platform": runtime.platform,
    }
    _require(_typed_equal(interp["runtime"], expected_runtime))
    _path(environment)
    stdlib, executable = _path(runtime.paths[5]), _path(runtime.paths[0])
    forbidden = (rb[0].expected.selection.directory, rb[0].activation_scope.root)

    def permitted(path, tree=False):
        _path(path)
        for root in forbidden:
            _require(not _inside(path, root) and (not tree or not _inside(root, path)))

    link = (_link_plan(interp["executable_link"], executable, permitted, rb[0].context[1])
            if schema == 2 else None)
    meta = pb[0].expected
    packages = [
        RuntimePackage(meta.root, meta.entries, meta.files),
        RuntimePackage(entry_root, entry_entries, entry_files),
    ]
    declarations = list(meta.files) + list(entry_files) + [wrapper]
    dependencies = []

    def packages_from(rows, allowed):
        _require(type(rows) is list and len(rows) <= 32)
        previous = ""
        for row in rows:
            _require(type(row) is dict and row.keys() == {"path", "entries"})
            path = _path(row["path"])
            _require(path > previous and allowed(path))
            permitted(path, True)
            previous = path
            entries, files = _table_rows(path, row["entries"])
            for entry in entries:
                _path(path + "/" + entry[0])
            packages.append(RuntimePackage(path, entries, files))
            declarations.extend(files)
            yield from files

    dependencies.extend(
        packages_from(
            dep["packages"], lambda path: _inside(path, environment) and path != environment
        )
    )
    tuple(packages_from(interp["packages"], lambda path: _inside(path, stdlib)))

    def files_from(rows, allowed):
        _require(type(rows) is list and len(rows) <= 1024)
        previous = ""
        for row in rows:
            _require(type(row) is dict and row.keys() == {"path", "size", "sha256"})
            path = _path(row["path"])
            _require(path > previous and allowed(path))
            permitted(path)
            previous = path
            expected = ExpectedArtifact(path, row["size"], row["sha256"])
            _expected((expected,))
            declarations.append(expected)
            yield expected

    dependencies.extend(
        files_from(dep["files"], lambda path: _inside(path, environment) and path != environment)
    )
    dependencies.extend(
        files_from(
            dep["libraries"],
            lambda path: not _inside(path, environment) and _library_name(path.rsplit("/", 1)[-1]),
        )
    )
    interpreter_files = tuple(
        files_from(interp["files"], lambda path: _inside(path, stdlib)
                   or path == (executable if link is None else link.target.path))
    )
    target_path = executable if link is None else link.target.path
    _require(any(row.path == target_path for row in interpreter_files))
    if link is not None:
        _require(any(row.path == link.target.path and row.size == link.target.size
                     and row.sha256 == link.target.sha256 for row in interpreter_files))
    _require(len(packages) <= 32 and sum(len(row.entries) for row in packages) <= 20000)
    roots = sorted(row.path for row in packages)
    _require(
        all(not _inside(right, left) for i, left in enumerate(roots) for right in roots[i + 1 :])
    )
    for root in roots:
        permitted(root, True)
    canonical, references = {}, []
    tree_files = {row.path for package in packages for row in package.files}
    for row in declarations:
        _path(row.path)
        _expected((row,))
        _require(not any(_inside(row.path, root) for root in roots) or row.path in tree_files)
        held = canonical.get(row.path)
        if held is None:
            canonical[row.path] = held = row
        else:
            _require(row.size == held.size and row.sha256 == held.sha256)
        references.append((row, held))
    all_files = tuple(canonical.values())
    if link is not None:
        _require(all(hop.path not in canonical
                     and not any(_inside(hop.path, root) for root in roots) for hop in link.hops))
        held = canonical[link.target.path]
        _require(held.size == link.target.size and held.sha256 == link.target.sha256)
        link = ExecutableLinkPlan(link.hops, held, link.uid, link.mode, link.text_bytes)
    prior = pb[3][2][4]
    _require(type(prior) is tuple and len(prior) == len(meta.files))
    for receipt, row in zip(prior, meta.files, strict=True):
        _require(
            type(receipt) is _HashedArtifact
            and receipt.owner is pb[3][0]
            and receipt.scope is pb[0]
            and receipt.expected is row
            and receipt.sha256 == row.sha256
        )
    prior_paths = {row.path for row in meta.files}
    pending = tuple(row for row in all_files if row.path not in prior_paths)
    previous = meta.selection_scope.expected + tuple(row[0] for row in meta.recipe_binding[4][3])
    _expected(previous + all_files)
    if link is not None:
        prefix = pb[3][2][7][2]
        _require(type(prefix) is int and prefix >= 0
                 and len(previous) + len(all_files) + len(link.hops) <= _artifacts._MAX_FILES
                 and prefix + sum(row.size for row in pending) + 2 * link.text_bytes
                 <= _artifacts._MAX_TOTAL)
    loose = tuple(row for row in all_files if not any(_inside(row.path, root) for root in roots))
    modules = dep["modules"]
    _require(
        type(modules) is list
        and len(modules) <= 64
        and all(
            type(name) is str
            and 0 < len(name) <= 1024
            and _PREFIX.fullmatch(name) is not None
            and name.split(".")[0] not in ("hmp_plugin", "hmp_startup")
            for name in modules
        )
        and modules == sorted(set(modules))
        and all(
            not _inside(b.replace(".", "/"), a.replace(".", "/"))
            for i, a in enumerate(modules)
            for b in modules[i + 1 :]
        )
    )
    return RuntimeFilePlan(
        eb,
        rb,
        pb,
        dep_raw,
        interp_raw,
        runtime,
        tuple(packages),
        pending,
        all_files,
        loose,
        prior,
        tuple(references),
        tuple(sorted({row.path for row in dependencies})),
        tuple(modules),
        link,
    )


def plan_current(plan, eb, rb, pb):
    _require(
        type(plan) is RuntimeFilePlan
        and plan.entry_binding is eb
        and plan.recipe_binding is rb
        and plan.plugin_binding is pb
        and plan.dependency_raw is rb[4][3][3][1]
        and plan.interpreter_raw is rb[4][3][4][1]
        and plan.runtime is eb[2][6].interpreter
        and ((rb[0].expected.recipe_schema == 1 and plan.executable_link is None)
             or (rb[0].expected.recipe_schema == 2
                 and type(plan.executable_link) is ExecutableLinkPlan
                 and any(plan.executable_link.target is row for row in plan.all_files)))
    )


def loaded_origins(plan):
    _require(
        type(plan) is RuntimeFilePlan and type(sys.modules) is dict and len(sys.modules) <= 20000
    )
    result = []
    for name, module in tuple(sys.modules.items()):
        _require(type(name) is str)
        if not any(name == prefix or name.startswith(prefix + ".") for prefix in plan.modules):
            continue
        _require(type(module) is ModuleType)
        values = vars(module)
        file, spec = values.get("__file__"), values.get("__spec__")
        _require(
            type(file) is str
            and file in plan.dependency_paths
            and type(spec) is ModuleSpec
            and type(values.get("__name__")) is str
            and values["__name__"] == name
        )
        props = vars(spec)
        _require(type(props.get("name")) is str and props["name"] == name)
        origin, loader = props.get("origin"), props.get("loader")
        _require(
            type(origin) is str
            and origin == file
            and loader is not None
            and values.get("__loader__") is loader
        )
        path, search = values.get("__path__"), props.get("submodule_search_locations")
        _require(
            (path is None and search is None)
            or (
                type(path) in (list, tuple)
                and search is path
                and all(type(value) is str for value in path)
                and tuple(path) == (os.path.dirname(file),)
            )
        )
        frozen = None if path is None else tuple(path)
        result.append((name, module, file, spec, origin, loader, path, frozen))
    return tuple(result)
