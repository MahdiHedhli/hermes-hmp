"""Disposable interpreter PM-layout observations; not native runtime qualification."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / "hmp_plugin/presentation_gateway_activation.py"
SCRIPT = r'''
import importlib.util, json, sys, threading
from importlib.machinery import ModuleSpec
from types import ModuleType
spec = importlib.util.spec_from_file_location("synthetic_activation", sys.argv[1])
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
mutation = sys.argv[2]
root = "/synthetic/native"
environment = "/synthetic/pm/generation-A/lib/python3.14/site-packages"
bootstrap = ModuleType("hermes_bootstrap")
bootstrap.__file__ = root + "/hermes_bootstrap.py"
bootstrap.__spec__ = ModuleSpec("hermes_bootstrap", loader=None, origin=bootstrap.__file__)
pm = ModuleType("pm.environments")
pm.__file__ = root + "/pm/environments.py"
pm.__spec__ = ModuleSpec("pm.environments", loader=None, origin=pm.__file__)
exec(compile("def activate_dependencies():\n    raise AssertionError('activation invoked')\n"
             "def selected_venv():\n    raise AssertionError('selection queried')\n",
             pm.__file__, "exec"), vars(pm))
dependency = ModuleType("synthetic_dependency")
dependency.__file__ = environment + "/dependency.py"
dependency.__spec__ = ModuleSpec(dependency.__name__, loader=None, origin=dependency.__file__)
sys.modules.update({"hermes_bootstrap": bootstrap, "pm.environments": pm,
                    "synthetic_dependency": dependency})
sys.path[:] = [root, environment, *sys.path]
callbacks = []
class Foreign:
    def __eq__(self, other):
        callbacks.append("eq")
        raise AssertionError("foreign equality")
    def __call__(self):
        callbacks.append("call")
        raise AssertionError("foreign callable")

def refusal(action):
    try:
        action()
    except m.ActivationCaptureError as error:
        assert str(error) == "BI1_GATEWAY_ACTIVATION_REFUSED"
        return error
    raise AssertionError("mutation accepted")

before = mutation in ("late", "missing_bootstrap", "foreign_bootstrap", "bad_layout",
                      "bad_origin", "foreign_pm_file", "capture_late_callback", "foreign_activate")
if mutation == "late": sys.modules["gateway.run"] = ModuleType("gateway.run")
if mutation == "missing_bootstrap": del sys.modules["hermes_bootstrap"]
if mutation == "foreign_bootstrap": sys.modules["hermes_bootstrap"] = Foreign()
if mutation == "bad_layout": sys.path[1] = "/synthetic/new-environment"
if mutation == "bad_origin": pm.__file__ = root + "/different.py"
if mutation == "foreign_pm_file": pm.__file__ = Foreign()
if mutation == "capture_late_callback":
    getpid = m.os.getpid
    def enter_gateway_during_capture():
        value = getpid()
        if m._ENTRY_CELL is not None:
            sys.modules["gateway.run"] = ModuleType("gateway.run")
        return value
    m.os.getpid = enter_gateway_during_capture
if mutation == "foreign_activate": pm.activate_dependencies = Foreign()
if before:
    error = refusal(m.GatewayActivationOwner.retain)
    owner = m._ENTRY_OWNER
    assert error.failed_owner is owner and owner._uncertain
    if mutation != "capture_late_callback": assert not owner._ready
    refusal(m.GatewayActivationOwner.retain)
else:
    owner = m.GatewayActivationOwner.retain()
    assert owner.current() is owner and owner._scope.environment == environment
    assert root not in repr(owner) and root not in repr(owner._scope)
    if mutation == "normal":
        refusal(m.GatewayActivationOwner.retain)
        assert owner.current() is owner and not owner._uncertain
    elif mutation == "new_selection":
        pm.committed_generation = "/synthetic/pm/generation-B"
        assert owner.current() is owner and owner._scope.environment == environment
    elif mutation == "new_import":
        sys.modules["new_unadmitted_import"] = ModuleType("new_unadmitted_import")
        assert owner.current() is owner  # factory must separately inspect/admit new imports
    else:
        if mutation == "paths": sys.path[1] = environment.replace("generation-A", "generation-B")
        if mutation == "path_list": sys.path = list(sys.path)
        if mutation == "path_foreign": sys.path[1] = Foreign()
        if mutation == "bootstrap": sys.modules["hermes_bootstrap"] = ModuleType("hermes_bootstrap")
        if mutation == "module_file": dependency.__file__ = environment + "/changed.py"
        if mutation == "origin_foreign": dependency.__file__ = Foreign()
        if mutation == "module_spec":
            dependency.__spec__ = ModuleSpec(dependency.__name__, loader=None,
                                             origin=dependency.__file__)
        if mutation == "spec_origin": dependency.__spec__.origin = environment + "/changed.py"
        if mutation == "module_removed": del sys.modules["synthetic_dependency"]
        if mutation == "activation_code":
            pm.activate_dependencies.__code__ = (lambda: None).__code__
        if mutation == "scope": owner._scope = owner._scope._replace(environment="/synthetic/other")
        if mutation == "context_callback":
            getpid = m.os.getpid
            def replace_scope():
                value = getpid()
                owner._scope = owner._scope._replace(environment="/synthetic/other")
                m._ENTRY_CELL = (owner, owner._scope)
                return value
            m.os.getpid = replace_scope
        if mutation == "retire": owner.retire()
        if mutation == "thread":
            results = []
            worker = threading.Thread(target=lambda: results.append(refusal(owner.current)))
            worker.start()
            worker.join()
            assert len(results) == 1
        refusal(owner.current)
        assert owner._uncertain
        refusal(m.GatewayActivationOwner.retain)
assert callbacks == []
print(json.dumps({"mutation": mutation, "passed": True, "runtime_admitted": False}))
'''


@pytest.mark.parametrize("mutation", [
    "normal", "new_selection", "new_import", "late", "missing_bootstrap", "foreign_bootstrap",
    "bad_layout", "bad_origin", "foreign_pm_file", "capture_late_callback",
    "foreign_activate", "paths", "path_list", "path_foreign",
    "bootstrap", "module_file", "origin_foreign", "module_spec", "spec_origin", "module_removed",
    "activation_code", "scope", "context_callback", "retire", "thread",
])
def test_original_gateway_activation_observation(tmp_path, mutation):
    if os.name != "posix":
        pytest.skip("current source capture requires supported POSIX uid semantics")
    import sys

    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", SCRIPT, str(MODULE), mutation],
        cwd=tmp_path, env={"LANG": "C", "LC_ALL": "C"}, capture_output=True, text=True,
        timeout=10, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "mutation": mutation, "passed": True, "runtime_admitted": False,
    }
