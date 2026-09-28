"""`tools/ci/check_plugin_surface.py`: the real package passes, and each rule catches its
violation in a synthetic package."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "tools" / "ci" / "check_plugin_surface.py"
PACKAGE = REPO / "server" / "hmp_plugin"

_spec = importlib.util.spec_from_file_location("check_plugin_surface", SCRIPT)
assert _spec and _spec.loader
surface = importlib.util.module_from_spec(_spec)
sys.modules["check_plugin_surface"] = surface
_spec.loader.exec_module(surface)


def test_real_package_passes() -> None:
    assert surface.check_package(PACKAGE) == []


def test_cli_exit_code() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


@pytest.fixture()
def pkg(tmp_path: Path) -> Path:
    dest = tmp_path / "hmp_plugin"
    shutil.copytree(PACKAGE, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def _write(pkg: Path, name: str, body: str) -> None:
    (pkg / name).write_text(textwrap.dedent(body), encoding="utf-8")


def _append(pkg: Path, name: str, body: str) -> None:
    with (pkg / name).open("a", encoding="utf-8") as f:
        f.write("\n" + textwrap.dedent(body))


def _rules(pkg: Path) -> list[tuple[str, str]]:
    return [(v.rule, v.path) for v in surface.check_package(pkg)]


# --- S1 imports ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stmt",
    [
        "import gateway.run",
        "from gateway.run import GatewayRunner",
        "from hermes_state import SessionDB",
        "import hermes_constants",
        "from tools.approval import list_gateway_approvals",
        "import some_unknown_package",
    ],
)
def test_s1_hermes_import_outside_bridge(pkg: Path, stmt: str) -> None:
    _append(pkg, "reads.py", f"def f():\n    {stmt}\n")
    assert ("S1", "reads.py") in _rules(pkg)


def test_s1_qrcode_only_in_cli(pkg: Path) -> None:
    _append(pkg, "cli.py", "def qr():\n    import qrcode\n")
    assert _rules(pkg) == []
    for module in ("reads.py", "server.py", "adapter.py", "bridge.py"):
        _append(pkg, module, "def qr():\n    import qrcode.image\n")
    rules = _rules(pkg)
    # bridge.py is otherwise exempt from S1 (it may import any Hermes internal), but that
    # exemption must not extend to qrcode: it is restricted to cli.py, bridge.py included.
    assert {("S1", m) for m in ("reads.py", "server.py", "adapter.py", "bridge.py")} <= set(rules)
    assert ("S1", "cli.py") not in rules


def test_s1_qrcode_module_level_in_cli_is_flagged(pkg: Path) -> None:
    """`qrcode` may only be imported lazily (inside a function) in cli.py, per condition 2 of
    reviews/dependencies.md's `qrcode` verdict; a module-level `import qrcode` there must be
    flagged even though cli.py is the one module allowed to import it at all."""
    _append(pkg, "cli.py", "import qrcode\n")
    assert ("S1", "cli.py") in _rules(pkg)


def test_s1_qrcode_in_bridge_is_flagged(pkg: Path) -> None:
    """bridge.py is exempt from S1 for Hermes internals, but qrcode is a third-party package
    restricted to cli.py specifically -- bridge.py may not import it, module-level or lazily."""
    _append(pkg, "bridge.py", "import qrcode\n")
    assert ("S1", "bridge.py") in _rules(pkg)
    pkg2_rules_module_level = _rules(pkg)
    assert pkg2_rules_module_level  # non-empty: the violation above is present

    # Also flagged when imported lazily inside a function, not just at module level.
    _append(pkg, "bridge.py", "def f():\n    import qrcode.image\n")
    rules = _rules(pkg)
    assert len([v for v in rules if v == ("S1", "bridge.py")]) >= 2


def test_s1_bridge_may_import_hermes(pkg: Path) -> None:
    _append(pkg, "bridge.py", "import gateway.run\nfrom hermes_state import SessionDB\n")
    assert _rules(pkg) == []


def test_s1_adapter_exception_is_exact(pkg: Path) -> None:
    _append(pkg, "adapter.py", "from gateway.platforms.base import MessageEvent\n")
    assert ("S1", "adapter.py") in _rules(pkg)


@pytest.mark.parametrize(
    "stmt",
    [
        "import gateway.config",
        "from gateway.config import load_gateway_config",
        "from gateway.platforms.base import *",
        "from gateway.platforms._shared import get_scoped_secret",
    ],
)
def test_s1_adapter_other_hermes_imports_rejected(pkg: Path, stmt: str) -> None:
    _append(pkg, "adapter.py", stmt + "\n")
    assert ("S1", "adapter.py") in _rules(pkg)


def test_s1_identity_exception_allows_exactly_the_anchor(pkg: Path) -> None:
    _append(pkg, "identity.py", "from hermes_constants import get_default_hermes_root\n")
    assert _rules(pkg) == []


@pytest.mark.parametrize(
    "stmt",
    [
        "import hermes_constants",
        "from hermes_constants import get_hermes_home",
        "from hermes_constants import get_default_hermes_root, get_hermes_home",
        "from hermes_constants import *",
        "from gateway.config import Platform",  # adapter's exception is adapter-only
        "from gateway.platforms.base import BasePlatformAdapter",
        "from hermes_state import SessionDB",
    ],
)
def test_s1_identity_other_hermes_imports_rejected(pkg: Path, stmt: str) -> None:
    _append(pkg, "identity.py", stmt + "\n")
    assert ("S1", "identity.py") in _rules(pkg)


@pytest.mark.parametrize("module", ["reads.py", "compat.py", "adapter.py", "bridge.py"])
def test_s1_identity_exception_is_identity_only(pkg: Path, module: str) -> None:
    _append(pkg, module, "from hermes_constants import get_default_hermes_root\n")
    rules = _rules(pkg)
    if module == "bridge.py":
        assert rules == []  # the bridge may import any Hermes internal
    else:
        assert ("S1", module) in rules


def test_s1_exception_does_not_extend_to_other_modules(pkg: Path) -> None:
    _append(pkg, "server.py", "from gateway.config import Platform\n")
    assert ("S1", "server.py") in _rules(pkg)


def test_s1_exception_does_not_extend_to_subpackage_namesakes(pkg: Path) -> None:
    (pkg / "sub").mkdir()
    _write(pkg, "sub/__init__.py", "")
    _write(pkg, "sub/bridge.py", "import gateway.run\n")
    assert ("S1", "sub/bridge.py") in _rules(pkg)


def test_s1_stdlib_and_approved_third_party_ok(pkg: Path) -> None:
    _append(pkg, "server.py", "import sqlite3\nimport aiohttp.web\nfrom cryptography import x509\n")
    assert _rules(pkg) == []


# --- S2 dynamic imports -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "import importlib\ndef f():\n    importlib.import_module('gateway.run')\n",
        "def f():\n    __import__('gateway.run')\n",
        "def f():\n    exec('import gateway.run')\n",
        "import importlib.util\ndef f():\n    importlib.util.find_spec('gateway')\n",
    ],
)
def test_s2_dynamic_import_outside_allowed(pkg: Path, body: str) -> None:
    _append(pkg, "reads.py", body)
    assert ("S2", "reads.py") in _rules(pkg)


def test_s2_compat_dynamic_import_only_in_probe(pkg: Path) -> None:
    _append(pkg, "compat.py", "def other():\n    importlib.import_module('gateway.run')\n")
    assert ("S2", "compat.py") in _rules(pkg)


def test_s2_probe_may_import(pkg: Path) -> None:
    src = (pkg / "compat.py").read_text(encoding="utf-8")
    src = src.replace(
        '    raise NotImplementedError("T023: dependency probe")',
        '    importlib.import_module("gateway.run")\n    return ()',
    )
    (pkg / "compat.py").write_text(src, encoding="utf-8")
    assert _rules(pkg) == []


def test_s2_re_compile_is_not_code_execution(pkg: Path) -> None:
    _append(pkg, "wire.py", "import re\nPATTERN = re.compile('x')\n")
    assert _rules(pkg) == []


# --- S3 bridge isolation ------------------------------------------------------------------------


def test_s3_module_level_bridge_import(pkg: Path) -> None:
    _append(pkg, "reads.py", "from . import bridge\n")
    assert ("S3", "reads.py") in _rules(pkg)


def test_s3_lazy_bridge_import_ok(pkg: Path) -> None:
    _append(pkg, "server.py", "def make():\n    from .bridge import HermesReadBridge\n")
    assert _rules(pkg) == []


def test_s3_compat_never_imports_bridge(pkg: Path) -> None:
    _append(pkg, "compat.py", "def make():\n    from .bridge import HermesReadBridge\n")
    assert ("S3", "compat.py") in _rules(pkg)


# --- S4 register --------------------------------------------------------------------------------


def _replace_register(pkg: Path, body: str) -> None:
    src = (pkg / "__init__.py").read_text(encoding="utf-8")
    head = src[: src.index("def register(")]
    (pkg / "__init__.py").write_text(head + textwrap.dedent(body), encoding="utf-8")


REGISTER_OK = """\
def register(ctx):
    ctx.register_platform(name="hmp")
    ctx.register_cli_command(name="hmp")
"""


def test_s4_minimal_register_ok(pkg: Path) -> None:
    _replace_register(pkg, REGISTER_OK)
    assert _rules(pkg) == []


@pytest.mark.parametrize(
    "body",
    [
        REGISTER_OK + "    ctx.register_hook('x', print)\n",
        REGISTER_OK + "    ctx.register_platform(name='hmp2')\n",
        "def register(ctx):\n    ctx.register_platform(name='hmp')\n",
        "def register(ctx):\n    ctx.register_tool(name='t')\n"
        "    ctx.register_platform(name='h')\n",
        REGISTER_OK + "    helper(ctx)\n",
        REGISTER_OK + "    c = ctx\n",
        "def register(ctx):\n    if True:\n        ctx.register_platform(name='hmp')\n"
        "    ctx.register_cli_command(name='hmp')\n",
        "def register(ctx, extra=None):\n    ctx.register_platform(name='hmp')\n"
        "    ctx.register_cli_command(name='hmp')\n",
        "def register(*args):\n    pass\n",
        "def something_else(ctx):\n    pass\n",
    ],
)
def test_s4_bad_register(pkg: Path, body: str) -> None:
    _replace_register(pkg, body)
    assert "S4" in {rule for rule, _ in _rules(pkg)}


# --- S5 registration elsewhere --------------------------------------------------------------


def test_s5_registration_outside_register(pkg: Path) -> None:
    _append(pkg, "server.py", "def later(ctx):\n    ctx.register_hook('x', print)\n")
    assert ("S5", "server.py") in _rules(pkg)


# --- S6 manifest --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("name: hmp\n", "name: hmp-other\n"),
        ("kind: platform\n", "kind: standalone\n"),
        ("version: 1.0.0-f1\n", "version: 1.0.0\n"),
        ("author:", "provides_tools: [x]\nauthor:"),
        ("author:", "hooks: [pre_tool_call]\nauthor:"),
    ],
)
def test_s6_manifest(pkg: Path, old: str, new: str) -> None:
    path = pkg / "plugin.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    assert ("S6", "plugin.yaml") in _rules(pkg)
