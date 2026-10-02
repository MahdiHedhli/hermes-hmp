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
    "hermes_version.py",
    "issue_draft.py",
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
    "logging_policy.py",
    # S4: descriptor emission for the four read routes; imports no local_media_* module.
    "media_emission.py",
    # Optional, inert local-image modules: no production module imports them (see the test below).
    "local_media_active_scan.py",
    "local_media_file_safety.py",
    "local_media_raster_structure.py",
    "local_media_result.py",
    "local_media_registry.py",  # process-local ref registry (LM-9); inert, stdlib only
    "local_media_sidecar.py",  # non-wire read-result carriers (LM-8); inert, stdlib + contract
    "local_media_candidate.py",  # bounded candidate extraction (LM-8); inert, accepted modules only
    "local_media_active_batch.py",  # request-scoped active batch (C6a); inert, scanner + candidate
    "local_media_batch_binding.py",  # closed batch binding (C6b); inert, batch + sidecar + stdlib
}
DATA_FILES = {
    "plugin.yaml",
    "read_compat_builds.json",
    "write_supported_builds.json",
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
# The optional modules are not wired in. Only local_media_result.py (the optional wrapper) may
# import the optional scanner; local_media_candidate.py imports its accepted modules at MODULE scope
# only; the bridge (candidate and sidecar) and reads.py (sidecar) import only inside function
# bodies; nothing else may import any local_media_* module. Dynamic imports (`__import__`,
# `importlib`) are not detected by these static pins.

OPTIONAL_MODULES = sorted(m[:-3] for m in CONTRACT_MODULES if m.startswith("local_media_"))
ALLOWED_OPTIONAL_IMPORTS = {
    "local_media_result": {"local_media_active_scan"},
    # S2c: the bridge may load exactly these two, only below a function boundary (pinned below).
    # C6b: the same function-local rule for the batch scan and its binding result. S6b: the one
    # cache-fill function `_local_media_modules` loads the whole chain the preload must prove.
    "bridge": {
        "local_media_active_batch",
        "local_media_active_scan",
        "local_media_batch_binding",
        "local_media_candidate",
        "local_media_file_safety",
        "local_media_result",
        "local_media_sidecar",
    },
    # M3: the adapter's availability binding proves and holds the objects the bridge and reads
    # caches already hold; the retired gate is gone. S4: its one media import is the registry,
    # function-local, in `_media_registry_bind` (pinned in test_s4_descriptors.py).
    "adapter": {"local_media_registry"},
    # S2d: the read cores load the carrier only below a function boundary (pinned below).
    "reads": {"local_media_sidecar"},
    "local_media_candidate": {
        "local_media_active_scan",
        "local_media_file_safety",
        "local_media_result",
        "local_media_sidecar",
    },
    # C6a: the batch loads exactly the accepted scanner and candidate, at module scope only.
    "local_media_active_batch": {"local_media_active_scan", "local_media_candidate"},
    # C6b: the binding loads exactly the accepted batch and sidecar, at module scope only.
    "local_media_batch_binding": {"local_media_active_batch", "local_media_sidecar"},
}


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


MODULE_SCOPE_ONLY = {
    "local_media_candidate",
    "local_media_active_batch",
    "local_media_batch_binding",
}
FUNCTION_SCOPE_ONLY = {"adapter", "bridge", "reads"}


def _import_scopes(source: str) -> list[str]:
    """One label per local_media_* import: `module` (a direct statement of the module), `function`
    (inside any function body) or `nested` (class/if/try/with outside every function)."""
    found: list[str] = []

    def visit(node: ast.AST, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)) and _local_media_imports(
                ast.unparse(child)
            ):
                if in_function:
                    found.append("function")
                else:
                    found.append("module" if isinstance(node, ast.Module) else "nested")
            visit(child, in_function or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))

    visit(ast.parse(source), False)
    return found


def _scopes_allowed(stem: str, source: str) -> bool:
    """The scope rule for `stem`. The module allowlist (`ALLOWED_OPTIONAL_IMPORTS`) is separate."""
    scopes = _import_scopes(source)
    if stem in MODULE_SCOPE_ONLY:
        return all(scope == "module" for scope in scopes)
    if stem in FUNCTION_SCOPE_ONLY:
        return all(scope == "function" for scope in scopes)
    return True


def _imports_allowed(stem: str, source: str) -> bool:
    found = _local_media_imports(source)
    return found <= ALLOWED_OPTIONAL_IMPORTS.get(stem, set()) and _scopes_allowed(stem, source)


def test_import_scopes_match_the_accepted_boundary_in_every_module() -> None:
    for path in sorted(PACKAGE.glob("*.py")):
        assert _imports_allowed(path.stem, path.read_text(encoding="utf-8")), path.name


def test_real_modules_use_the_exact_scopes() -> None:
    def scopes(name: str) -> set[str]:
        return set(_import_scopes((PACKAGE / name).read_text(encoding="utf-8")))

    assert scopes("local_media_candidate.py") == {"module"}
    assert scopes("local_media_active_batch.py") == {"module"}
    batch = (PACKAGE / "local_media_active_batch.py").read_text(encoding="utf-8")
    assert _local_media_imports(batch) == {"local_media_active_scan", "local_media_candidate"}
    assert scopes("bridge.py") == {"function"}
    assert scopes("adapter.py") == {"function"}  # S4: only the registry, below a function
    assert scopes("reads.py") == {"function"}
    reads = (PACKAGE / "reads.py").read_text(encoding="utf-8")
    assert _local_media_imports(reads) == {"local_media_sidecar"}


_IMPORT_FORMS = {
    "from_module": "from .local_media_{m} import X\n",
    "from_package": "from . import local_media_{m}\n",
    "plain": "import hmp_plugin.local_media_{m}\n",
    "alias": "from . import local_media_{m} as _m\n",
}


def _wrapped(form: str, where: str) -> str:
    line = _IMPORT_FORMS[form]

    def indent(text: str, levels: int) -> str:
        return "".join("    " * levels + part + "\n" for part in text.splitlines())

    return {
        "module": line,
        "function": "def f():\n" + indent(line, 1),
        "method": "class C:\n    def f(self):\n" + indent(line, 2),
        "class": "class C:\n" + indent(line, 1),
        "if": "if True:\n" + indent(line, 1),
        "try": "try:\n" + indent(line, 1) + "except ImportError:\n    pass\n",
    }[where]


@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
@pytest.mark.parametrize("where", ["function", "method", "class", "if", "try"])
def test_candidate_imports_must_be_module_scope_only(form: str, where: str) -> None:
    ok = _imports_allowed("local_media_candidate", _wrapped(form, "module").format(m="sidecar"))
    assert ok  # positive control: the accepted module-scope form
    assert not _imports_allowed("local_media_candidate", _wrapped(form, where).format(m="sidecar"))


@pytest.mark.parametrize("stem", ["bridge", "reads"])
@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
@pytest.mark.parametrize("where", ["module", "class", "if", "try"])
def test_bridge_and_reads_imports_must_be_function_local(stem: str, form: str, where: str) -> None:
    assert _imports_allowed(stem, _wrapped(form, "function").format(m="sidecar"))  # control
    assert not _imports_allowed(stem, _wrapped(form, where).format(m="sidecar"))


@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
@pytest.mark.parametrize("where", ["module", "function", "method", "class", "if", "try"])
def test_adapter_may_import_no_media_module_in_any_scope(form: str, where: str) -> None:
    # M3: the retired gate was the adapter's only allowed media import. S4 allows the registry
    # alone, function-local (below), and still none of these.
    for module in ("gate", "sidecar", "candidate", "active_batch", "batch_binding"):
        source = _wrapped(form, where).format(m=module)
        assert not _imports_allowed("adapter", source), (module, where)


@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
@pytest.mark.parametrize("where", ["module", "class", "if", "try"])
def test_adapter_registry_import_must_be_function_local(form: str, where: str) -> None:
    assert _imports_allowed("adapter", _wrapped(form, "function").format(m="registry"))  # control
    assert not _imports_allowed("adapter", _wrapped(form, where).format(m="registry"))


@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
def test_adapter_may_import_no_other_media_module(form: str) -> None:
    for module in ("sidecar", "candidate", "active_batch", "batch_binding"):
        source = _wrapped(form, "function").format(m=module)
        assert not _imports_allowed("adapter", source), module


@pytest.mark.parametrize("form", sorted(_IMPORT_FORMS))
def test_reads_may_import_only_the_sidecar(form: str) -> None:
    for module in ("candidate", "result", "registry", "active_scan", "file_safety"):
        source = _wrapped(form, "function").format(m=module)
        assert not _imports_allowed("reads", source), module


@pytest.mark.parametrize("stem", ["server", "wire", "contract", "compat", "cli", "routes"])
@pytest.mark.parametrize("where", ["module", "function", "class", "if", "try"])
def test_every_other_module_imports_no_optional_module(stem: str, where: str) -> None:
    for module in ("sidecar", "candidate", "registry"):
        source = _wrapped("from_module", where).format(m=module)
        assert not _imports_allowed(stem, source), (stem, module)


def test_wrapper_allowance_is_actually_used() -> None:
    wrapper = (PACKAGE / "local_media_result.py").read_text(encoding="utf-8")
    assert _local_media_imports(wrapper) == {"local_media_active_scan"}


def _module_scope_local_media_imports(source: str) -> set[str]:
    """local_media_* imports that run at import time: outside every function body."""
    found: set[str] = set()

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                found.update(_local_media_imports(ast.unparse(child)))
            visit(child)

    visit(ast.parse(source))
    return found


def test_bridge_media_imports_are_function_local_and_exact() -> None:
    bridge = (PACKAGE / "bridge.py").read_text(encoding="utf-8")
    assert _local_media_imports(bridge) == {
        "local_media_active_batch",
        "local_media_active_scan",
        "local_media_batch_binding",
        "local_media_candidate",
        "local_media_file_safety",
        "local_media_result",
        "local_media_sidecar",
    }
    assert not _module_scope_local_media_imports(bridge)
    # The detector sees a module-scope import (guards the pin itself).
    assert _module_scope_local_media_imports("from . import local_media_sidecar\n")
    assert _module_scope_local_media_imports("if True:\n    from .local_media_sidecar import X\n")
    assert not _module_scope_local_media_imports(
        "def f():\n    from . import local_media_sidecar\n"
    )


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
