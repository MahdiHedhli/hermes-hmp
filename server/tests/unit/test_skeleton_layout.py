"""The package matches the module tree in contracts/server-modules.md (T013)."""

from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"

CONTRACT_MODULES = {
    "__init__.py",
    "contract.py",
    "wire.py",
    "crypto.py",
    "identity.py",
    "store.py",
    "compat.py",
    "bridge.py",
    "pairing.py",
    "tokens.py",
    "auth.py",
    "reads.py",
    "authorize.py",
    "revoke.py",
    "gate.py",
    "direct_send.py",
    "prompts.py",
    "mobile_cron.py",
    "mobile_model.py",
    "server.py",
    "request_ctx.py",
    "adapter.py",
    "cli.py",
    "routes.py",  # specs/005-new-profile-routing: `hermes hmp routes add`
    "logging_policy.py",
    # Optional, inert local-image modules: no production module imports them (see the test below).
    "local_media_active_scan.py",
    "local_media_file_safety.py",
    "local_media_raster_structure.py",
    "local_media_result.py",
}
DATA_FILES = {
    "plugin.yaml",
    "read_compat_builds.json",
    "write_supported_builds.json",
    "approval_supported_builds.json",
    "mobile_cron_supported_builds.json",
    "mobile_model_supported_builds.json",
}


def test_module_set_is_exactly_the_contract_tree() -> None:
    assert {p.name for p in PACKAGE.glob("*.py")} == CONTRACT_MODULES
    assert not [p for p in PACKAGE.iterdir() if p.is_dir() and p.name != "__pycache__"]


def test_data_files_present() -> None:
    assert {p.name for p in PACKAGE.iterdir()} >= DATA_FILES


# adapter.py subclasses Hermes's BasePlatformAdapter, so it imports only inside a Hermes env.
@pytest.mark.parametrize(
    "module", sorted(m[:-3] for m in CONTRACT_MODULES - {"__init__.py", "adapter.py"})
)
def test_module_imports_without_hermes(module: str) -> None:
    importlib.import_module(f"hmp_plugin.{module}")


def test_read_compat_list_shape() -> None:
    data = json.loads((PACKAGE / "read_compat_builds.json").read_text(encoding="utf-8"))
    assert set(data) == {"format", "bridge_files", "builds"}
    assert data["format"] == 1
    assert isinstance(data["builds"], list)
    files = data["bridge_files"]
    assert files == sorted(set(files)) and all(f.endswith(".py") for f in files)


def test_write_supported_list_shape() -> None:
    data = json.loads((PACKAGE / "write_supported_builds.json").read_text(encoding="utf-8"))
    assert data == {"format": 1, "builds": []}  # GU-2a matrix stays empty in F1 (T064)


# --- local_media_* import inertness ---------------------------------------------------------------
# The four optional modules are not wired in. Only local_media_result.py (the optional wrapper) may
# import the optional scanner; nothing else may import any local_media_* module.

OPTIONAL_MODULES = sorted(m[:-3] for m in CONTRACT_MODULES if m.startswith("local_media_"))
ALLOWED_OPTIONAL_IMPORTS = {"local_media_result": {"local_media_active_scan"}}


def _local_media_imports(source: str) -> set[str]:
    """Every local_media_* module a source imports, at any depth."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [f"{node.module or ''}.{a.name}" for a in node.names]
        else:
            continue
        for name in names:
            found.update(part for part in name.split(".") if part.startswith("local_media_"))
    return found


def test_only_optional_wrapper_imports_optional_modules() -> None:
    for path in sorted(PACKAGE.glob("*.py")):
        allowed = ALLOWED_OPTIONAL_IMPORTS.get(path.stem, set())
        found = _local_media_imports(path.read_text(encoding="utf-8"))
        assert found <= allowed, f"{path.name} imports {sorted(found - allowed)}"


def test_wrapper_allowance_is_actually_used() -> None:
    wrapper = (PACKAGE / "local_media_result.py").read_text(encoding="utf-8")
    assert _local_media_imports(wrapper) == {"local_media_active_scan"}


@pytest.mark.parametrize(
    "line",
    [
        "from . import local_media_result",
        "from .local_media_result import ResultRefusal",
        "from hmp_plugin.local_media_file_safety import x",
        "import hmp_plugin.local_media_raster_structure",
        "def f():\n    from . import local_media_active_scan",
    ],
)
def test_import_detector_catches_forbidden_forms(line: str) -> None:
    assert _local_media_imports(line)


def test_import_detector_ignores_unrelated_imports() -> None:
    assert not _local_media_imports("import json\nfrom . import wire\nfrom .reads import x")


def test_deleting_a_forbidden_import_is_detected_as_the_only_difference() -> None:
    server = (PACKAGE / "server.py").read_text(encoding="utf-8")
    assert not _local_media_imports(server)
    assert _local_media_imports(server + "\nfrom . import local_media_result\n")


def test_startup_modules_load_no_local_media_module() -> None:
    # Fresh interpreter: adapter.py and bridge.py need Hermes, so only the Hermes-free startup path.
    code = (
        "import sys, hmp_plugin\n"
        "import hmp_plugin.server, hmp_plugin.reads, hmp_plugin.compat\n"
        "import hmp_plugin.cli, hmp_plugin.routes\n"
        "bad = sorted(m for m in sys.modules if 'local_media_' in m)\n"
        "assert not bad, bad\n"
    )
    env = {**os.environ, "PYTHONPATH": str(PACKAGE.parent)}
    done = subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr[-500:]
