"""`register(ctx)` makes exactly two registrations (HMP v1 PR-2, FR-054), checked at runtime with
a spy context. It also checks that importing the package imports no Hermes module.

When `HMP_HERMES_SRC` names a Hermes source tree (read only), the keyword arguments passed are
also checked against that tree's `PluginContext.register_platform` / `register_cli_command`
signatures, parsed by AST, not imported.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import hmp_plugin
from hmp_plugin import cli, compat
from hmp_plugin.contract import CLI_COMMAND, PLATFORM_NAME

SERVER_DIR = Path(__file__).resolve().parents[2]


class SpyContext:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> None:
            assert not args, f"{name} called with positional args"
            self.calls.append((name, kwargs))

        return record


@pytest.fixture()
def calls() -> list[tuple[str, dict[str, Any]]]:
    ctx = SpyContext()
    hmp_plugin.register(ctx)
    return ctx.calls


def test_exactly_two_registrations(calls: list[tuple[str, dict[str, Any]]]) -> None:
    assert [name for name, _ in calls] == ["register_platform", "register_cli_command"]


def test_platform_registration(calls: list[tuple[str, dict[str, Any]]]) -> None:
    kwargs = calls[0][1]
    assert kwargs["name"] == PLATFORM_NAME == "hmp"
    assert callable(kwargs["adapter_factory"])
    assert kwargs["check_fn"] is compat.runtime_dependencies_present
    # No allow-lists, env grants, prompt hints or other surface (closed surface).
    assert set(kwargs) == {"name", "label", "adapter_factory", "check_fn", "install_hint"}


def test_cli_registration(calls: list[tuple[str, dict[str, Any]]]) -> None:
    kwargs = calls[1][1]
    assert kwargs["name"] == CLI_COMMAND == "hmp"
    assert kwargs["setup_fn"] is cli.setup_parser
    assert kwargs["handler_fn"] is cli.dispatch
    assert set(kwargs) == {"name", "help", "setup_fn", "handler_fn", "description"}


def test_check_fn_is_passive_and_boolean() -> None:
    assert isinstance(compat.runtime_dependencies_present(), bool)


def test_cli_tree_matches_contract() -> None:
    parser = argparse.ArgumentParser(prog="hermes hmp")
    cli.setup_parser(parser)
    ok = [
        ["pair", "offer", "--label", "L", "--user", "U"],
        ["pair", "list"],
        ["pair", "confirm", "pid", "--sas", "S", "--label", "L", "--new-user"],
        ["pair", "confirm", "pid", "--sas", "S", "--label", "L", "--user", "U", "--yes-share"],
        ["pair", "deny", "pid"],
        ["devices", "list"],
        ["devices", "revoke", "dev"],
        ["instance", "show"],
        ["instance", "rotate-key"],
        ["compat"],
    ]
    for argv in ok:
        parser.parse_args(argv)


def test_importing_package_imports_no_hermes_module() -> None:
    code = (
        "import sys, hmp_plugin\n"
        "hermes = {'gateway', 'hermes_cli', 'hermes_constants', 'hermes_state', 'run_agent'}\n"
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in hermes)\n"
        "assert not bad, bad\n"
        "assert 'hmp_plugin.bridge' not in sys.modules\n"
        "assert 'hmp_plugin.adapter' not in sys.modules\n"
        "hmp_plugin.register(type('C', (), {'__getattr__': lambda s, n: (lambda **k: None)})())\n"
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in hermes)\n"
        "assert not bad, bad\n"
    )
    subprocess.run([sys.executable, "-c", code], cwd=SERVER_DIR, check=True)


# ---------------------------------------------------------------------------------------------
# Optional: the registration kwargs against a real Hermes tree (read only, AST parsed).
# ---------------------------------------------------------------------------------------------

HERMES_SRC = os.environ.get("HMP_HERMES_SRC")


def _signature_params(tree: ast.Module, cls: str, method: str) -> tuple[set[str], bool]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == method:
                    a = fn.args
                    names = {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs} - {"self"}
                    return names, a.kwarg is not None
    raise AssertionError(f"{cls}.{method} not found")


@pytest.mark.skipif(not HERMES_SRC, reason="HMP_HERMES_SRC not set")
def test_kwargs_accepted_by_hermes_plugin_api(calls: list[tuple[str, dict[str, Any]]]) -> None:
    src = Path(HERMES_SRC or "")
    tree = ast.parse((src / "hermes_cli" / "plugins.py").read_text(encoding="utf-8"))
    for name, kwargs in calls:
        params, _ = _signature_params(tree, "PluginContext", name)
        assert set(kwargs) <= params, (name, set(kwargs) - params)
    # adapter_factory / check_fn semantics per gateway/platform_registry.py PlatformEntry.
    registry = (src / "gateway" / "platform_registry.py").read_text(encoding="utf-8")
    assert "adapter_factory: Callable[[Any], Any]" in registry
    assert "check_fn: Callable[[], bool]" in registry


@pytest.mark.skipif(not HERMES_SRC, reason="HMP_HERMES_SRC not set")
def test_adapter_matches_hermes_platform_api() -> None:
    """The adapter's documented-API imports exist, and it overrides every abstract method."""
    src = Path(HERMES_SRC or "")
    base = ast.parse((src / "gateway" / "platforms" / "base.py").read_text(encoding="utf-8"))
    config = ast.parse((src / "gateway" / "config.py").read_text(encoding="utf-8"))
    top_classes = {n.name for n in base.body if isinstance(n, ast.ClassDef)}
    assert {"BasePlatformAdapter", "SendResult"} <= top_classes
    assert "Platform" in {n.name for n in config.body if isinstance(n, ast.ClassDef)}

    cls = next(
        n for n in base.body if isinstance(n, ast.ClassDef) and n.name == "BasePlatformAdapter"
    )
    abstract = {
        fn.name
        for fn in cls.body
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(
            (isinstance(d, ast.Name) and d.id == "abstractmethod")
            or (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
            for d in fn.decorator_list
        )
    }
    assert abstract, "no abstract methods found; Hermes API changed"
    adapter = ast.parse((SERVER_DIR / "hmp_plugin" / "adapter.py").read_text(encoding="utf-8"))
    hmp = next(n for n in adapter.body if isinstance(n, ast.ClassDef) and n.name == "HmpAdapter")
    defined = {fn.name for fn in hmp.body if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)}
    assert abstract <= defined, abstract - defined
