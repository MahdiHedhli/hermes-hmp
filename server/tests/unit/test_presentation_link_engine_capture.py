"""Original early dependency capture controls; not native/host qualification."""

import builtins
import sys

import pytest

from hmp_plugin import presentation_native_link as link
from hmp_startup import link_factory_origin as origins
from .test_presentation_link_metadata_boundary import Foreign


@pytest.mark.parametrize("slot", ("checker", "dependency"))
def test_capture_fences_keyword_dict_subclasses_before_items(monkeypatch, slot):
    calls = []

    class Trap(dict):
        def items(self):
            calls.append("items")
            raise AssertionError("foreign keyword dictionary was dispatched")

    selected = (
        link._engine_origin_tail if slot == "checker" else link.metadata._capture_payload_origin
    )
    monkeypatch.setattr(selected, "__kwdefaults__", Trap(selected.__kwdefaults__ or {}))
    with pytest.raises(RuntimeError):
        link._capture_engine()
    assert calls == []


@pytest.mark.parametrize(
    "name", ("metadata", "artifacts_module", "custody_module", "policy", "sys")
)
def test_capture_fences_module_aliases_before_vars(monkeypatch, name):
    calls = []
    monkeypatch.setattr(link, name, Foreign(calls))
    with pytest.raises(RuntimeError):
        link._capture_engine()
    assert calls == []


@pytest.mark.parametrize(
    "fault", ("checker_export", "core_code", "getter_code", "closure", "constructor_namespace_key")
)
def test_capture_reseals_originals_after_held_checker_return(monkeypatch, fault):
    calls, observed = [], []
    checker_code = link._engine_origin_tail.__code__
    capture_code = link._capture_engine.__code__

    def foreign(*args, **kwargs):
        calls.append("foreign checker")
        raise AssertionError("foreign checker executed")

    def changed(*args, **kwargs):
        raise AssertionError("changed dependency code executed")

    class Key:
        def __hash__(self):
            calls.append("hash")
            return 147293

        def __eq__(self, other):
            calls.append("equality")
            raise AssertionError("foreign namespace equality executed")

    def observe(frame, event, returned):
        if frame.f_code is not checker_code:
            return None
        frame.f_trace_lines = False
        if event == "return" and frame.f_back.f_code is capture_code and not observed:
            observed.append(True)
            if fault == "checker_export":
                monkeypatch.setattr(link, "_engine_origin_tail", foreign)
            elif fault == "core_code":
                monkeypatch.setattr(link._require, "__code__", changed.__code__)
            elif fault == "getter_code":
                monkeypatch.setattr(
                    link.metadata._MetadataResult.raw.fget, "__code__", changed.__code__
                )
            elif fault == "closure":
                function = link.ArtifactObservationError.__init__
                index = function.__code__.co_freevars.index("__class__")
                monkeypatch.setattr(function.__closure__[index], "cell_contents", RuntimeError)
            else:
                monkeypatch.setitem(link._LinkSnapshot.__new__.__globals__, Key(), object())
                calls.clear()  # insertion is test setup, never a production lookup
        return observe

    prior = sys.gettrace()
    assert prior is None
    sys.settrace(observe)
    try:
        with pytest.raises(RuntimeError):
            link._capture_engine()
    finally:
        sys.settrace(prior)
    assert observed == [True] and calls == []


def test_parent_refuses_self_consistent_foreign_sys_root(tmp_path):
    # Fresh normal entry import, not a direct capture that reenters through imports.
    # The synthetic package namespace avoids plugin bootstrap; no host is started.
    import json
    import subprocess
    from pathlib import Path

    script = r"""
import ast,json,sys
from pathlib import Path
from types import ModuleType
server=sys.argv[1]
package=ModuleType("hmp_plugin")
package.__path__=[str(Path(server)/"hmp_plugin")]
sys.modules[package.__name__]=package
sys.path.insert(0,server)
from hmp_plugin import presentation_native_link as link
from hmp_startup import link_factory_origin as origins
parent_code=origins.capture.__code__
tree=ast.parse(Path(parent_code.co_filename).read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)
           and n.name==parent_code.co_name and n.lineno==parent_code.co_firstlineno]
assert len(functions)==1
# Bind the refusal to the exact parent system-identity guard, not any later error.
def system_check(n):
    return (isinstance(n,ast.Compare) and len(n.ops)==len(n.comparators)==1
        and isinstance(n.ops[0],ast.IsNot) and isinstance(n.comparators[0],ast.Name)
        and n.comparators[0].id=="_sys"
        and isinstance(n.left,ast.Subscript) and isinstance(n.left.value,ast.Subscript)
        and isinstance(n.left.value.value,ast.Name)
        and n.left.value.value.id=="engine_origin"
        and isinstance(n.left.value.slice,ast.Constant) and n.left.value.slice.value==4
        and isinstance(n.left.slice,ast.Constant) and n.left.slice.value==0)
guards=[n for n in functions[0].body if isinstance(n,ast.If)
        and any(system_check(x) for x in ast.walk(n.test))]
assert len(guards)==1 and len(guards[0].body)==1
assert isinstance(guards[0].body[0],ast.Raise)
refusal_line=guards[0].body[0].lineno
fake=ModuleType("sys")
fake.modules=dict(sys.modules)
entered=[];seen=[];parent_errors=[]
code=link._capture_engine.__code__
def observe(frame,event,returned):
    if frame.f_code is parent_code:
        frame.f_trace_lines=False
        if event=="exception":
            parent_errors.append((returned[0].__name__,frame.f_lineno))
        return observe
    if frame.f_code is not code:return None
    frame.f_trace_lines=False
    if event=="call":
        entered.append(True)
        link.sys=fake
    if event=="return":
        if type(returned) is tuple:
            engine=returned[0]
            seen.append(engine[4][0] is fake and engine[4][2] is fake.modules)
        link.sys=sys
    return observe
assert origins._CAPTURE_STARTED is False and sys.gettrace() is None
sys.settrace(observe)
error=None
try:
    from hmp_startup import gateway_entry
except Exception as exc:
    error=(type(exc).__name__,str(exc))
finally:
    sys.settrace(None)
    link.sys=sys
assert entered==[True] and seen==[True]
assert parent_errors==[("RuntimeError",refusal_line)],parent_errors
assert error==("RuntimeError","BI1_LINK_FACTORY_ORIGIN_REFUSED")
assert origins._CAPTURE_STARTED is True
assert sys.gettrace() is None and link.sys is sys
assert not any(n in sys.modules for n in
    ("hermes_bootstrap","gateway.run","hmp_plugin.adapter","hmp_plugin.server"))
print(json.dumps(dict(engine_entered=True,foreign_roots_observed=True,
    exact_parent_guard_refused=True,capture_started=True,host_started=False)))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(Path(__file__).resolve().parents[2])],
        cwd=tmp_path,
        env={"LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "engine_entered": True,
        "foreign_roots_observed": True,
        "exact_parent_guard_refused": True,
        "capture_started": True,
        "host_started": False,
    }


def test_engine_capture_never_delegates_to_pin_helpers(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("capture delegated to a replaceable helper")

    monkeypatch.setattr(origins, "_pin_function", foreign)
    monkeypatch.setattr(origins, "_pin_type", foreign)
    packet = link._capture_engine()[0]
    assert link._engine_origin_tail(packet) is packet and calls == []


def test_engine_capture_has_no_initialization_import_callback(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("capture executed an import callback")

    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", foreign)
        packet = link._capture_engine()[0]
    assert link._engine_origin_tail(packet) is packet and calls == []


def test_capture_rejects_a_non_native_record_allocator_before_call(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("foreign record allocator executed")

    monkeypatch.setattr(link, "_RECORD_ALLOCATOR", foreign)
    with pytest.raises(link.ArtifactObservationError):
        link._capture_engine()
    assert calls == []
