#!/usr/bin/env python3
"""Closed-plugin-surface check for `server/hmp_plugin` (HMP v1 PR-2, FR-054, T013).

A static AST scan; it never imports or runs the plugin. Standard library only.

Rules:
  S1  Imports. Outside `bridge.py`, a module may import only the standard library, the approved
      runtime packages (aiohttp, cryptography; qrcode in `cli.py` only, and only lazily, inside a
      function, not at module level) and its own package. `qrcode` is restricted to `cli.py`
      even for `bridge.py`, which is otherwise exempt from this rule for Hermes internals.
      Every other absolute import is treated as a Hermes internal, which fails closed for unknown
      packages.
      Closed exceptions, exact (module, name) pairs, only as `from … import …`:
      - `adapter.py` may import exactly `gateway.platforms.base.{BasePlatformAdapter, SendResult}`
        and `gateway.config.Platform`, the documented platform-plugin API (ruling on T013);
      - `identity.py` may import exactly `hermes_constants.get_default_hermes_root`, the documented
        plugin API that anchors the instance key, on every build (ruling on IR-6, option (a)).
  S2  Dynamic imports. `__import__`, `import_module`, `module_from_spec`, `exec_module`,
      `load_module`, `spec_from_file_location`, `spec_from_loader`, and the builtins `exec`,
      `eval` and `compile` are allowed only in `bridge.py` and inside `compat.py`'s
      `probe_dependencies`.
      `find_spec` is allowed only in `bridge.py` and `compat.py`.
  S3  Bridge isolation. No module imports `bridge` at module level; `compat.py` never imports it.
      `bridge.py` is imported only after the compat gate reports SUPPORTED.
  S4  Registration. `__init__.py` defines `register(ctx)`, which makes exactly two calls on
      `ctx`, `register_platform` and `register_cli_command`, once each, as plain top-level
      statements. `ctx` is used for nothing else.
  S5  No other registration. No module calls any `register_*` attribute outside `register`.
  S6  Manifest. `plugin.yaml` declares `name: hmp`, `kind: platform`, `version: 1.0.0-f1`, and no
      `provides_tools`, `provides_hooks`, `hooks` or `capabilities`.

Known limit: an AST scan cannot follow data flow. It cannot see a Hermes object handed to a
non-bridge module at runtime. Code review covers that; this check covers imports and registration.

Usage: python tools/ci/check_plugin_surface.py [PACKAGE_DIR]   (exit 0 = pass, 1 = violations)
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACKAGE = Path(__file__).resolve().parents[2] / "server" / "hmp_plugin"

BRIDGE_MODULE = "bridge.py"
COMPAT_MODULE = "compat.py"
PROBE_FUNCTION = "probe_dependencies"
INIT_MODULE = "__init__.py"
ADAPTER_MODULE = "adapter.py"
IDENTITY_MODULE = "identity.py"

THIRD_PARTY_ALLOWED: frozenset[str] = frozenset({"aiohttp", "cryptography"})
# Third-party packages allowed in exactly one module. `qrcode` is the operator CLI's terminal QR
# renderer (T032; reviews/dependencies.md): only `cli.py` may import it.
CLI_MODULE = "cli.py"
ROUTES_MODULE = "routes.py"
# `yaml` (PyYAML) is the parser of `hermes hmp routes add`: routes.py only, imported lazily.
MODULE_ONLY_THIRD_PARTY: dict[str, str] = {"qrcode": CLI_MODULE, "yaml": ROUTES_MODULE}

# S1 closed exception: (module file, imported module) -> allowed names. Exact pairs only.
DOCUMENTED_PLUGIN_API: dict[tuple[str, str], frozenset[str]] = {
    (ADAPTER_MODULE, "gateway.platforms.base"): frozenset({"BasePlatformAdapter", "SendResult"}),
    (ADAPTER_MODULE, "gateway.config"): frozenset({"Platform"}),
    (IDENTITY_MODULE, "hermes_constants"): frozenset({"get_default_hermes_root"}),
}

DYNAMIC_IMPORT_NAMES: frozenset[str] = frozenset(
    {
        "__import__",
        "import_module",
        "module_from_spec",
        "exec_module",
        "load_module",
        "spec_from_file_location",
        "spec_from_loader",
    }
)
# Builtins that execute code; matched only as bare names (so `re.compile` is fine).
CODE_EXEC_BUILTINS: frozenset[str] = frozenset({"exec", "eval", "compile"})
FIND_SPEC = "find_spec"

REGISTER_CALLS: tuple[str, ...] = ("register_platform", "register_cli_command")

MANIFEST_REQUIRED: dict[str, str] = {"name": "hmp", "kind": "platform", "version": "1.0.0-f1"}
MANIFEST_FORBIDDEN: frozenset[str] = frozenset(
    {"provides_tools", "provides_hooks", "hooks", "capabilities"}
)


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


def _stdlib_roots() -> frozenset[str]:
    names = getattr(sys, "stdlib_module_names", None)
    if names is None:  # pragma: no cover - Python < 3.10 is unsupported
        raise SystemExit("check_plugin_surface.py needs Python >= 3.10")
    return frozenset(names)


STDLIB = _stdlib_roots()


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


class _ModuleScanner(ast.NodeVisitor):
    """Collects S1, S2, S3 and S5 violations for one module."""

    def __init__(self, rel: str) -> None:
        self.rel = rel
        # Package-relative POSIX path: only the top-level bridge.py / compat.py / adapter.py
        # carry exceptions, never a same-named file in a subpackage.
        self.name = Path(rel).as_posix()
        self.violations: list[Violation] = []
        self._func_stack: list[str] = []
        self._depth = 0  # >0 inside a def or class body
        self._type_checking = 0  # >0 inside `if TYPE_CHECKING:`

    def _add(self, rule: str, node: ast.AST, message: str) -> None:
        self.violations.append(Violation(rule, self.rel, getattr(node, "lineno", 0), message))

    # --- scopes ---
    def _visit_scope(self, node: ast.AST, name: str) -> None:
        self._func_stack.append(name)
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1
        self._func_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scope(node, node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node, node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_scope(node, "<lambda>")

    def visit_If(self, node: ast.If) -> None:
        test = node.test
        is_tc = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )
        if is_tc:
            self.visit(node.test)
            self._type_checking += 1
            for stmt in node.body:
                self.visit(stmt)
            self._type_checking -= 1
            for stmt in node.orelse:
                self.visit(stmt)
        else:
            self.generic_visit(node)

    # --- S1 / S3 ---
    def _check_absolute(self, node: ast.AST, module: str, names: list[str] | None) -> None:
        root = module.split(".", 1)[0]
        only_module = MODULE_ONLY_THIRD_PARTY.get(root)
        if only_module is not None:
            # A module-restricted third-party package (qrcode: cli.py only, lazily). This check
            # runs BEFORE the bridge.py exemption below: bridge.py is otherwise exempt from S1
            # (it may import any Hermes internal), but that exemption must never extend to a
            # package that is restricted to one *other* module -- bridge.py may not import
            # qrcode either.
            if self.name != only_module:
                self._add(
                    "S1",
                    node,
                    f"import of '{module}' is restricted to {only_module}; not allowed in "
                    f"{self.name}",
                )
                return
            if self._depth == 0 and not self._type_checking:
                self._add(
                    "S1",
                    node,
                    f"'{module}' must be imported lazily (inside a function), not at module "
                    f"level, in {only_module}",
                )
                return
            return
        if root in STDLIB or root in THIRD_PARTY_ALLOWED or self.name == BRIDGE_MODULE:
            return
        allowed = DOCUMENTED_PLUGIN_API.get((self.name, module))
        if allowed is not None and names is not None and "*" not in names:
            extra = sorted(set(names) - allowed)
            if not extra:
                return
            self._add("S1", node, f"'{module}' names {extra} are outside the approved plugin API")
            return
        self._add(
            "S1",
            node,
            f"import of '{module}' (not stdlib or approved third-party: treated as a Hermes "
            f"internal; only {BRIDGE_MODULE} may import it)",
        )

    def _check_bridge_import(self, node: ast.AST) -> None:
        if self.name == BRIDGE_MODULE:
            return
        if self.name == COMPAT_MODULE:
            self._add("S3", node, f"{COMPAT_MODULE} must never import bridge")
        elif self._depth == 0 and not self._type_checking:
            self._add("S3", node, "bridge imported at module level (import it only after the gate)")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_absolute(node, alias.name, None)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        names = [a.name for a in node.names]
        if node.level and node.level > 0:
            module = node.module or ""
            if module.split(".", 1)[0] == "bridge" or (not module and "bridge" in names):
                self._check_bridge_import(node)
        elif node.module:
            self._check_absolute(node, node.module, names)
        self.generic_visit(node)

    # --- S2 / S5 ---
    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        is_exec = isinstance(node.func, ast.Name) and name in CODE_EXEC_BUILTINS
        if name in DYNAMIC_IMPORT_NAMES or is_exec:
            in_probe = self.name == COMPAT_MODULE and PROBE_FUNCTION in self._func_stack
            if self.name != BRIDGE_MODULE and not in_probe:
                self._add("S2", node, f"dynamic import or code execution via '{name}'")
        elif name == FIND_SPEC and self.name not in (BRIDGE_MODULE, COMPAT_MODULE):
            self._add("S2", node, "'find_spec' is allowed only in compat.py and bridge.py")
        if (
            name
            and name.startswith("register_")
            and isinstance(node.func, ast.Attribute)
            and not (self.name == INIT_MODULE and self._func_stack[:1] == ["register"])
        ):
            self._add("S5", node, f"registration call '{name}' outside __init__.register")
        self.generic_visit(node)


def _check_register(tree: ast.Module, rel: str) -> list[Violation]:
    """S4."""
    out: list[Violation] = []
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "register"]
    if len(funcs) != 1:
        return [Violation("S4", rel, 1, "__init__.py must define exactly one top-level register()")]
    fn = funcs[0]
    params = fn.args.posonlyargs + fn.args.args
    if (
        len(params) != 1
        or fn.args.vararg
        or fn.args.kwarg
        or fn.args.kwonlyargs
        or fn.decorator_list
    ):
        return [Violation("S4", rel, fn.lineno, "register must take exactly one parameter (ctx)")]
    ctx = params[0].arg

    # Every call on ctx, anywhere in register (nested blocks included).
    ctx_calls = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == ctx
    ]
    attrs = [c.func.attr for c in ctx_calls]  # type: ignore[union-attr]
    if sorted(attrs) != sorted(REGISTER_CALLS):
        out.append(
            Violation(
                "S4",
                rel,
                fn.lineno,
                f"register makes {len(attrs)} ctx call(s) {attrs}; expected exactly "
                f"{list(REGISTER_CALLS)} once each",
            )
        )
    # Each call must be a plain top-level statement of register (no loop, branch or nesting).
    top_level_calls = {
        id(stmt.value)
        for stmt in fn.body
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
    }
    for call in ctx_calls:
        if id(call) not in top_level_calls:
            out.append(
                Violation("S4", rel, call.lineno, "ctx call must be a plain top-level statement")
            )
    # ctx is used only as the receiver of those calls.
    receivers = {id(c.func.value) for c in ctx_calls}  # type: ignore[union-attr]
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id == ctx and id(n) not in receivers:
            out.append(Violation("S4", rel, n.lineno, "ctx used other than as a call receiver"))
    return out


def _parse_manifest(text: str) -> dict[str, str]:
    """Top-level `key: value` pairs of a simple YAML mapping (indented lines are skipped)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.split(" #", 1)[0].strip().strip("'\"")
    return out


def _check_manifest(package: Path) -> list[Violation]:
    """S6."""
    path = package / "plugin.yaml"
    rel = str(path.name)
    if not path.is_file():
        return [Violation("S6", rel, 0, "plugin.yaml missing")]
    data = _parse_manifest(path.read_text(encoding="utf-8"))
    out = [
        Violation("S6", rel, 0, f"'{k}' must be '{v}', found {data.get(k)!r}")
        for k, v in MANIFEST_REQUIRED.items()
        if data.get(k) != v
    ]
    out += [
        Violation("S6", rel, 0, f"'{k}' must not be declared (closed surface)")
        for k in sorted(MANIFEST_FORBIDDEN & data.keys())
    ]
    return out


def check_package(package: Path) -> list[Violation]:
    package = Path(package)
    violations: list[Violation] = []
    modules = sorted(package.rglob("*.py"))
    if not (package / INIT_MODULE).is_file():
        violations.append(Violation("S4", INIT_MODULE, 0, "__init__.py missing"))
    for path in modules:
        rel = path.relative_to(package).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            violations.append(Violation("PARSE", rel, exc.lineno or 0, str(exc.msg)))
            continue
        scanner = _ModuleScanner(rel)
        scanner.visit(tree)
        violations.extend(scanner.violations)
        if rel == INIT_MODULE:
            violations.extend(_check_register(tree, rel))
    violations.extend(_check_manifest(package))
    return violations


def main(argv: list[str]) -> int:
    package = Path(argv[1]) if len(argv) > 1 else DEFAULT_PACKAGE
    if not package.is_dir():
        print(f"check_plugin_surface: no such package directory: {package}", file=sys.stderr)
        return 1
    violations = check_package(package)
    for v in violations:
        print(v)
    if violations:
        print(f"check_plugin_surface: FAIL ({len(violations)} violation(s))")
        return 1
    print("check_plugin_surface: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
