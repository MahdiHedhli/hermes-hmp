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
if mutation == "retained_cache_mode_always":entry._imp.check_hash_based_pycs="always"
if mutation == "retained_cache_mode_never":entry._imp.check_hash_based_pycs="never"
if mutation == "retained_cache_prefix":sys.pycache_prefix="/synthetic/cache"
if mutation == "retained_cache_root_prefix":sys.pycache_prefix="/"
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
    runtime = original_data.interpreter
    assert type(runtime) is entry.InterpreterStartupData
    assert runtime.paths[0] == sys.executable and runtime.version == tuple(sys.version_info)
    assert runtime.flags == tuple(sys.flags) and runtime.platform == sys.platform
    assert runtime.paths[0] not in repr(runtime)
    foreign_runtime_calls = []
    if mutation == "current_alias_binding":
        class ForeignAlias:
            def __getattr__(self, name):
                foreign_runtime_calls.append(True)
                raise AssertionError("foreign alias attribute")
            def __eq__(self, other):
                foreign_runtime_calls.append(True)
                raise AssertionError("foreign alias equality")
        sys.modules["typing.io"] = ForeignAlias()
    if mutation == "current_alias_namespace":
        vars(sys.modules["typing"])["io"] = object()
    if mutation == "current_alias_module":
        sys.modules["typing"] = ModuleType("typing")
    if mutation == "current_interpreter_path": sys.executable += ".changed"
    if mutation == "current_interpreter_tag": sys.implementation.cache_tag += "_changed"
    if mutation == "current_interpreter_identity":
        from types import SimpleNamespace
        sys.implementation = SimpleNamespace(**vars(sys.implementation))
    if mutation == "current_interpreter_flags": sys.flags = tuple(sys.flags)
    if mutation == "current_interpreter_foreign":
        class ForeignPath:
            def __eq__(self, other):
                foreign_runtime_calls.append(True)
                raise AssertionError("foreign interpreter equality")
        sys.executable = ForeignPath()
    if mutation == "current_interpreter_cache_mode":
        entry._imp.check_hash_based_pycs = (
            "never" if entry._imp.check_hash_based_pycs != "never" else "always")
    if mutation == "current_interpreter_cache_module":sys.modules["_imp"] = ModuleType("_imp")
    if mutation == "current_interpreter_cache_prefix":sys.pycache_prefix = "/synthetic/cache"
    if mutation == "current_interpreter_cache_write":
        sys.dont_write_bytecode = not sys.dont_write_bytecode
    if mutation in ("current_interpreter_cache_foreign",
                    "current_interpreter_cache_foreign_prefix"):
        class ForeignCache:
            def __eq__(self, other):
                foreign_runtime_calls.append(True)
                raise AssertionError("foreign cache equality")
        if mutation.endswith("prefix"):sys.pycache_prefix=ForeignCache()
        else:entry._imp.check_hash_based_pycs=ForeignCache()
    if mutation == "current_interpreter_cache_noncanonical":sys.pycache_prefix="/synthetic/../cache"
    if mutation == "current_interpreter_cache_write_type":sys.dont_write_bytecode=1
    if mutation == "current_interpreter_cache_unknown":
        entry._imp.check_hash_based_pycs="unsupported"
    hash_origin = original_binding[0].interpreter.source_hash
    if mutation == "current_interpreter_hash_builtin":
        entry._imp.source_hash = lambda *args: (_ for _ in ()).throw(AssertionError("called"))
    if mutation == "current_interpreter_hash_function":
        hash_origin.loader_type.get_code = lambda self, name: b'not-used'
    if mutation == "current_interpreter_hash_code":
        def changed_hash(data): return b'not-used'
        hash_origin.function.__code__ = changed_hash.__code__
    if mutation == "current_interpreter_hash_key":
        setattr(hash_origin.key_owner, hash_origin.key_name, hash_origin.key ^ 1)
    if mutation == "current_interpreter_hash_foreign_key":
        class ForeignKey:
            def __eq__(self, other):
                foreign_runtime_calls.append(True);raise AssertionError("foreign hash key")
        setattr(hash_origin.key_owner, hash_origin.key_name, ForeignKey())
    if mutation == "current_interpreter_hash_globals":
        vars(hash_origin.module)['_imp'] = ModuleType('_imp')
    if mutation == "current_interpreter_hash_module_name":
        class ForeignName:
            def __eq__(self, other):
                foreign_runtime_calls.append(True);raise AssertionError("foreign function module")
        hash_origin.function.__module__ = ForeignName()
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
    if mutation in ("current_argv_callback", "current_interpreter_cache_callback"):
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
                if mutation == "current_argv_callback":sys.argv = ["synthetic-tail-change"]
                else:
                    entry._imp.check_hash_based_pycs = (
                        "never" if entry._imp.check_hash_based_pycs != "never" else "always")
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
    if (mutation in ("retained_namespace", "retained_argv", "retained_foreign_started",
                    "retained_bootstrap_alias", "current_module_file", "current_loader",
                    "current_code", "current_argv_callback")
            or mutation.startswith(("current_interpreter_", "current_alias_"))):
        try: owner.current_binding()
        except GatewayEntryError: pass
        else: raise AssertionError("changed current entry accepted")
    else: assert owner.current_binding()[2] is original_binding[2]
    assert owner._ready and not owner._failed
    assert owner._activation._uncertain is mutation.startswith("current_alias_")
    assert foreign_runtime_calls == []
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
if mutation == "typing_alias_binding": sys.modules["typing.io"] = object()
if mutation == "typing_alias_namespace": vars(sys.modules["typing"])["io"] = object()
if mutation == "typing_alias_module": sys.modules["typing"] = ModuleType("typing")
if mutation == "interpreter_path": sys.executable += ".changed"
if mutation == "interpreter_tag": sys.implementation.cache_tag += "_changed"
if mutation == "interpreter_identity":
    from types import SimpleNamespace
    sys.implementation = SimpleNamespace(**vars(sys.implementation))
if mutation == "interpreter_flags": sys.flags = tuple(sys.flags)
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
    "interpreter_path", "interpreter_tag", "interpreter_identity", "interpreter_flags",
    "current_interpreter_path", "current_interpreter_tag", "current_interpreter_identity",
    "current_interpreter_flags", "current_interpreter_foreign",
    "current_interpreter_cache_mode", "current_interpreter_cache_module",
    "current_interpreter_cache_prefix", "current_interpreter_cache_write",
    "current_interpreter_cache_foreign", "current_interpreter_cache_foreign_prefix",
    "current_interpreter_cache_noncanonical", "current_interpreter_cache_callback",
    "retained_cache_mode_always", "retained_cache_mode_never", "retained_cache_prefix",
    "retained_cache_root_prefix", "current_interpreter_cache_write_type",
    "current_interpreter_cache_unknown",
    "current_interpreter_hash_builtin", "current_interpreter_hash_function",
    "current_interpreter_hash_code", "current_interpreter_hash_key",
    "current_interpreter_hash_foreign_key", "current_interpreter_hash_globals",
    "current_interpreter_hash_module_name",
    "typing_alias_binding", "typing_alias_namespace", "typing_alias_module",
    "current_alias_binding", "current_alias_namespace", "current_alias_module",
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
