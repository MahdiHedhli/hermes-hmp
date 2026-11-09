"""Bounded declaration lookup for explicit native SDK class re-exports; never import it."""
from __future__ import annotations

import ast
from pathlib import Path

MAX_SOURCE_BYTES = 1_048_576
MAX_EXPORT_HOPS = 8


def _target_names(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        return set().union(*(_target_names(n) for n in node.elts))
    if isinstance(node, ast.Starred):
        return _target_names(node.value)
    return set()


def _other_binding(node, symbol, permitted):
    # Inspect module-scope bindings, including control-flow bodies, but never
    # mistake function/class-local assignments for exported module bindings.
    if isinstance(node, ast.ClassDef):
        if node.name == symbol and node not in permitted:
            return True
        children = [*node.bases, *node.decorator_list, *(k.value for k in node.keywords)]
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name == symbol:
            return True
        children = [*node.decorator_list, *node.args.defaults,
                    *(v for v in node.args.kw_defaults if v is not None)]
    else:
        if isinstance(node, ast.ImportFrom):
            if any((a.asname or a.name) == symbol for a in node.names):
                return node not in permitted
        if isinstance(node, ast.Import):
            if any((a.asname or a.name.split(".")[0]) == symbol for a in node.names):
                return True
        targets = []
        if isinstance(node, (ast.Assign, ast.Delete)):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr,
                               ast.For, ast.AsyncFor)):
            targets = [node.target]
        elif isinstance(node, getattr(ast, "TypeAlias", ())):
            targets = [node.name]
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            targets = [node.optional_vars]
        if any(symbol in _target_names(t) for t in targets):
            return True
        if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
            if node.name == symbol:
                return True
        if isinstance(node, ast.MatchMapping) and node.rest == symbol:
            return True
        children = ast.iter_child_nodes(node)
    return any(_other_binding(n, symbol, permitted) for n in children)


def public_class_tree(root: Path, module: str, symbol: str) -> tuple[ast.Module, str]:
    root = root.absolute()
    assert not root.is_symlink(), "native SDK root is a symlink"
    seen = set()
    for _ in range(MAX_EXPORT_HOPS):
        parts = module.split(".")
        assert parts[0] in {"hermes_cli", "gateway"}, "native export leaves SDK namespace"
        assert len(parts) <= 8 and all(p.isidentifier() for p in parts), "invalid SDK module"
        assert symbol.isidentifier() and (module, symbol) not in seen, "cyclic SDK export"
        seen.add((module, symbol))
        relative = Path(*parts).with_suffix(".py")
        path = root
        for part in relative.parts:
            path /= part
            assert not path.is_symlink(), "native SDK export contains a symlink"
        assert path.is_file() and path.resolve().is_relative_to(root.resolve())
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        assert len(raw) <= MAX_SOURCE_BYTES, "native SDK source too large"
        tree = ast.parse(raw.decode("utf-8"))
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == symbol]
        exports = [(n, a) for n in tree.body if isinstance(n, ast.ImportFrom)
                   for a in n.names if (a.asname or a.name) == symbol]
        assert len(classes) + len(exports) == 1, "ambiguous SDK class export"
        permitted = {*classes, *(n for n, _ in exports)}
        assert not any(_other_binding(n, symbol, permitted) for n in tree.body), (
            "unsupported or rebound SDK class export"
        )
        if classes:
            return tree, symbol
        node, alias = exports[0]
        assert node.module is not None, "unsupported SDK module export"
        if node.level:
            parent = parts[:-1]
            assert node.level <= len(parent), "relative SDK export escapes root"
            prefix = parent[:len(parent) - node.level + 1]
            module = ".".join([*prefix, *node.module.split(".")])
        else:
            module = node.module
        symbol = alias.name
    raise AssertionError("native SDK class export depth exceeded")
