"""Bounded declaration lookup for explicit native SDK class re-exports; never import it."""
from __future__ import annotations

import ast
from pathlib import Path

MAX_SOURCE_BYTES = 1_048_576
MAX_EXPORT_HOPS = 8


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
        assert path.stat().st_size <= MAX_SOURCE_BYTES, "native SDK source too large"
        raw = path.read_bytes()
        assert len(raw) <= MAX_SOURCE_BYTES, "native SDK source too large"
        tree = ast.parse(raw.decode("utf-8"))
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == symbol]
        exports = [(n, a) for n in tree.body if isinstance(n, ast.ImportFrom)
                   for a in n.names if (a.asname or a.name) == symbol]
        assignments = [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                       for target in (n.targets if isinstance(n, ast.Assign) else [n.target])
                       if isinstance(target, ast.Name) and target.id == symbol]
        assert len(classes) + len(exports) == 1 and not assignments, "ambiguous SDK class export"
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
