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
success = mutation in ("normal", "reexec") or mutation.startswith(("retained_", "current_"))
try:
    owner = GatewayEntryOwner.start()
except GatewayEntryError as error:
    assert not success, mutation
    assert error.failed_owner is entry._OWNER and entry._OWNER._failed
    assert "gateway.run" not in sys.modules or mutation in (
        "late", "bootstrap_late", "post_activation_late")
else:
    assert success, mutation
    assert entry._OWNER is owner and owner._ready and not owner._failed
    assert owner._activation._scope.bootstrap is owner._bootstrap
    assert owner._activation._scope.environment == environment
    assert sys.argv is before[0] and tuple(sys.argv) == before[1]
    assert sys.orig_argv is before[2] and tuple(sys.orig_argv) == before[3]
    assert "gateway.run" not in sys.modules
    assert owner._invocation() is owner._scope
if success:
    original_binding = owner.current_binding()
    original_data = owner.retained_data()
    assert type(original_data) is entry.EntryStartupData
    assert original_binding[2] is entry._STARTED is owner._started_cell
    assert original_data.arguments == before[1] and original_data.original_arguments == before[3]
    assert original_data.main_file not in repr(original_data)
    old_method = vars(GatewayEntryOwner)["start"]
    old_code = old_method.__func__.__code__
    if mutation == "retained_namespace":
        sys.modules[entry.__name__] = ModuleType(entry.__name__)
    if mutation == "retained_argv": sys.argv = ["synthetic-later-native-entry"]
    if mutation == "retained_thread":
        import threading
        refused = []
        def wrong_thread():
            for query in (owner.retained_data, owner.current_binding):
                try: query()
                except GatewayEntryError: refused.append(True)
        thread = threading.Thread(target=wrong_thread)
        thread.start(); thread.join()
        assert refused == [True, True]
    if mutation == "retained_process":
        pid = entry.os.fork()
        if pid == 0:
            try:
                for query in (owner.retained_data, owner.current_binding):
                    try: query()
                    except GatewayEntryError: pass
                    else: raise AssertionError("forked process accepted")
                assert not owner._activation._uncertain and not owner._failed
                entry.os._exit(0)
            except BaseException:
                entry.os._exit(3)
        waited, status = entry.os.waitpid(pid, 0)
        assert waited == pid and status == 0
    if mutation == "retained_foreign_started": entry._STARTED = object()
    if mutation == "retained_bootstrap_alias": owner._bootstrap = ModuleType("replacement")
    if mutation == "current_module_file": entry.__file__ = entry.__file__ + ".changed"
    if mutation == "current_loader": entry.__spec__.loader = object()
    if mutation == "current_argv_callback":
        origin_current, getpid = entry._origin_current, entry.os.getpid
        armed_query = False
        def arm_after_origin(origin):
            global armed_query
            result = origin_current(origin)
            armed_query = True
            return result
        def change_argv_during_activation():
            global armed_query
            value = getpid()
            if armed_query:
                armed_query = False
                sys.argv = ["synthetic-tail-change"]
            return value
        entry._origin_current = arm_after_origin
        entry.os.getpid = change_argv_during_activation
    if mutation == "current_code":
        def different_start(): return None
        old_method.__func__.__code__ = different_start.__code__
    if mutation in ("retained_foreign_started", "retained_bootstrap_alias"):
        try: owner.retained_data()
        except GatewayEntryError: pass
        else: raise AssertionError("changed original started binding accepted")
    else:
        assert owner.retained_data() is original_data
    if mutation in ("retained_namespace", "retained_argv", "retained_foreign_started",
                    "retained_bootstrap_alias", "current_module_file", "current_loader",
                    "current_code", "current_argv_callback"):
        try: owner.current_binding()
        except GatewayEntryError: pass
        else: raise AssertionError("changed current entry accepted")
    else: assert owner.current_binding()[2] is original_binding[2]
    assert owner._ready and not owner._failed and not owner._activation._uncertain
    if mutation == "current_code": old_method.__func__.__code__ = old_code
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
if mutation == "origin_file": entry.__file__ += ".changed"
if mutation == "origin_record": entry._ENTRY_ORIGIN = entry._ENTRY_ORIGIN._replace(file="/changed")
if mutation == "started_foreign": entry._STARTED = object()
if mutation == "final_origin_callback":
    actual_origin, getpid = entry._origin_current, entry.os.getpid
    armed_origin = False
    def arm_after_final_origin(origin):
        global armed_origin
        result = actual_origin(origin)
        if entry._OWNER._activation is not None: armed_origin = True
        return result
    def change_file_after_origin_check():
        global armed_origin
        value = getpid()
        if armed_origin:
            armed_origin = False
            entry.__file__ += ".changed"
        return value
    entry._origin_current = arm_after_final_origin
    entry.os.getpid = change_file_after_origin_check
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
    "post_activation_invocation", "origin_file", "origin_record", "started_foreign",
    "retained_namespace", "retained_argv", "retained_thread", "retained_process",
    "retained_foreign_started",
    "retained_bootstrap_alias", "current_module_file", "current_loader", "current_code",
    "final_origin_callback", "current_argv_callback",
])
def test_original_invocation_through_bootstrap(tmp_path, mutation):
    if os.name != "posix" or os.sys.platform not in ("darwin", "linux"):
        pytest.skip("supported POSIX entry fixture")
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
