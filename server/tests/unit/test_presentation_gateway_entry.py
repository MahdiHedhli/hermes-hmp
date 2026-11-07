"""Actual disposable bootstrap imports, not installed PM or gateway qualification."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
SCRIPT = r'''
import json, sys
from types import ModuleType
package, root, environment, mutation = sys.argv[1:]
namespace = ModuleType("hmp_plugin")
namespace.__path__ = [package]
sys.modules[namespace.__name__] = namespace
sys.path.insert(0, str(__import__("pathlib").Path(package).parent))
from hmp_startup.gateway_entry import GatewayEntryOwner, GatewayEntryError
from hmp_startup import gateway_entry as entry
if mutation == "late": sys.modules["gateway.run"] = ModuleType("gateway.run")
if mutation == "already_bootstrapped":
    sys.modules["hermes_bootstrap"] = ModuleType("hermes_bootstrap")
sys.path.insert(0, root)
before = sys.argv, tuple(sys.argv), sys.orig_argv, tuple(sys.orig_argv)
try:
    owner = GatewayEntryOwner.start()
except GatewayEntryError as error:
    assert mutation != "normal", mutation
    assert error.failed_owner is entry._OWNER and entry._OWNER._failed
    assert "gateway.run" not in sys.modules or mutation in (
        "late", "bootstrap_late", "post_activation_late")
else:
    assert mutation == "normal", mutation
    assert entry._OWNER is owner and owner._ready and not owner._failed
    assert owner._activation._scope.bootstrap is owner._bootstrap
    assert owner._activation._scope.environment == environment
    assert sys.argv is before[0] and tuple(sys.argv) == before[1]
    assert sys.orig_argv is before[2] and tuple(sys.orig_argv) == before[3]
    assert "gateway.run" not in sys.modules
    assert owner._invocation() is owner._scope
try:
    GatewayEntryOwner.start()
except GatewayEntryError:
    pass
else:
    raise AssertionError("duplicate/retry accepted")
assert getattr(entry, "bootstrap_effect_count", 0) == (0 if mutation in (
    "late", "already_bootstrapped") else 1)
print(json.dumps({"case": mutation,
                  "bootstrap_count": getattr(entry, "bootstrap_effect_count", 0)}))
'''
BOOTSTRAP = r'''
import sys
from types import ModuleType
from hmp_startup import gateway_entry as entry
assert entry._OWNER is not None and not entry._OWNER._ready
assert entry._CELL[0] is entry._OWNER
assert sys.argv[0].endswith("entry.py")  # original wrapper survives PM boundary
assert "gateway.run" not in sys.modules
entry.bootstrap_effect_count = 1
import pm.environments
sys.path.insert(1, sys.argv[3])
mutation = sys.argv[4]
if mutation == "coherent_invocation":
    sys.argv, sys.orig_argv = list(sys.argv), list(sys.orig_argv)
    replacement = entry._OWNER._scope._replace(
        argv=sys.argv, original=sys.orig_argv)
    entry._OWNER._scope = replacement
    entry._CELL = (entry._OWNER, replacement)
if mutation == "argv_value": sys.argv[0] = __file__
if mutation == "argv_identity": sys.argv = list(sys.argv)
if mutation == "orig_value": sys.orig_argv.append("--changed")
if mutation == "orig_identity": sys.orig_argv = list(sys.orig_argv)
if mutation == "main_file": sys.modules["__main__"].__file__ = __file__
if mutation == "main_identity": sys.modules["__main__"] = ModuleType("__main__")
if mutation == "bootstrap_late": sys.modules["gateway.run"] = ModuleType("gateway.run")
if mutation == "root_cell": entry._CELL = (entry._OWNER, object())
if mutation == "context": entry.os.getpid = lambda: -1
if mutation == "exception": raise RuntimeError("synthetic bootstrap failure")
if mutation.startswith("post_activation_"):
    original_getpid = entry.os.getpid
    def context_callback():
        value = original_getpid()
        if entry._OWNER._activation is not None:
            if mutation == "post_activation_late":
                sys.modules["gateway.run"] = ModuleType("gateway.run")
            elif mutation == "post_activation_bootstrap":
                entry._OWNER._bootstrap = ModuleType("replacement")
            elif mutation == "post_activation_invocation":
                replacement = entry._OWNER._scope._replace(arguments=tuple(sys.argv))
                entry._OWNER._scope = replacement
                entry._CELL = (entry._OWNER, replacement)
            elif mutation == "post_activation_owner":
                entry._OWNER._activation = object()
        return value
    entry.os.getpid = context_callback
'''


@pytest.mark.parametrize("mutation", [
    "normal", "late", "already_bootstrapped", "argv_value", "argv_identity",
    "orig_value", "orig_identity", "main_file", "main_identity", "bootstrap_late",
    "root_cell", "context", "exception", "post_activation_late",
    "post_activation_bootstrap", "post_activation_owner", "coherent_invocation",
    "post_activation_invocation",
])
def test_original_invocation_through_bootstrap(tmp_path, mutation):
    root = tmp_path / "native"
    (root / "pm").mkdir(parents=True)
    (root / "pm/__init__.py").write_text("")
    (root / "pm/environments.py").write_text("def activate_dependencies():\n    pass\n")
    (root / "hermes_bootstrap.py").write_text(BOOTSTRAP)
    environment = tmp_path / "generation/lib/python3.14/site-packages"
    environment.mkdir(parents=True)
    script = tmp_path / "entry.py"
    script.write_text(SCRIPT)
    result = subprocess.run(
        [os.sys.executable, "-I", "-B", str(script), str(PACKAGE), str(root),
         str(environment), mutation], capture_output=True, text=True, timeout=20,
        env={"LANG": "C", "LC_ALL": "C"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["case"] == mutation
