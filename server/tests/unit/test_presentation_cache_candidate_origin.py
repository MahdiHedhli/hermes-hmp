"""Cache planner definition custody without filesystem access or planner calls."""

import importlib
import sys

import pytest

from hmp_startup import gateway_approval
from hmp_startup import retained_binding_origin as origin

from . import test_presentation_entry_files as base
from .test_presentation_runtime_constructor_origin import (
    KINDS,
)
from .test_presentation_runtime_constructor_origin import (
    test_runtime_constructor_drift_refuses_without_constructor_calls as _constructor_drift,
)

ROLES = (
    ("cache_candidates", "CacheCandidateError", "__init__"),
    ("cache_candidates", None, "_require"),
    ("cache_candidates", None, "_location"),
    ("cache_candidates", None, "planned_cache_path"),
    ("cache_candidates", "PlannedCachePath", "__repr__"),
)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("drift", ("code", "defaults", "keyword_defaults"))
def test_runtime_plain_code_is_retained_and_rejects_drift(monkeypatch, role, drift):
    assert gateway_approval.GatewayEntryOwner is not None
    short, owner, name = role
    module = importlib.import_module("hmp_startup." + short)
    function = vars(module)[name] if owner is None else vars(vars(module)[owner])[name]
    assert type(function.__code__.co_freevars) is tuple
    record = origin.capture_bound()
    packet, layout, _ = record
    assert origin.current(packet) is packet
    assert origin.current_live(packet, layout) is packet
    calls = []
    changed_code = function.__code__.replace(co_name="synthetic_runtime_drift")

    def observe(frame, event, value):
        if event == "call" and frame.f_code is changed_code:
            calls.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with monkeypatch.context() as change:
            if drift == "code":
                change.setattr(function, "__code__", changed_code)
            elif drift == "defaults":
                change.setattr(function, "__defaults__", (object(),))
            else:
                change.setattr(function, "__kwdefaults__", {"unexpected": object()})
            with pytest.raises(origin.RetainedBindingOriginError):
                origin.current(packet)
            with pytest.raises(RuntimeError, match="BI1_RETAINED_HELPER_ORIGIN_REFUSED"):
                origin.current_live(packet, layout)
    finally:
        sys.setprofile(None)
    assert calls == []
    assert origin.current(packet) is packet
    assert origin.current_live(packet, layout) is packet


ALIASES = (
    ("cache_context", "PlannedCachePath"),
    ("cache_context", "_location"),
    ("cache_context", "planned_cache_path"),
    ("cache_candidates", "RuntimeFilesError"),
    ("cache_candidates", "_path"),
)


@pytest.mark.parametrize("alias", ALIASES)
def test_initial_wrong_imported_alias_cannot_become_coherent_authority(monkeypatch, alias):
    component, name = alias
    module = importlib.import_module("hmp_startup." + component)
    calls = []

    class Foreign:
        def __getattribute__(self, key):
            calls.append("get")
            raise AssertionError("foreign alias inspected")

        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("foreign alias compared")

    with monkeypatch.context() as change:
        change.setattr(module, name, Foreign())
        with pytest.raises(origin.RetainedBindingOriginError):
            origin.capture()
        with pytest.raises(RuntimeError, match="BI1_RETAINED_HELPER_ORIGIN_REFUSED"):
            origin.capture_bound()
    assert calls == []
    assert origin.current(origin.capture()) is not None


@pytest.mark.parametrize(
    "drift",
    (
        "code",
        "defaults",
        "keyword_defaults",
        "globals_name",
        "globals_builtin",
        "extra_global",
    ),
)
def test_cache_planner_constructor_metadata(monkeypatch, drift):
    _constructor_drift(monkeypatch, ("cache_candidates", "PlannedCachePath"), drift)


@pytest.mark.parametrize(
    "component,owner,method",
    (
        *ROLES,
        *(
            (component, owner, "__new__")
            for component, owner in (*KINDS, ("cache_candidates", "PlannedCachePath"))
        ),
    ),
)
@pytest.mark.parametrize("drift", ("code", "defaults", "keyword_defaults"))
@pytest.mark.parametrize("audit_mode", ("generic", "started"))
def test_cache_planner_drift_after_selected_return_refuses_without_effects(
    tmp_path, monkeypatch, component, owner, method, drift, audit_mode
):
    marker = "entry = GatewayEntryOwner.start()\n"
    extra = (
        "\nmethod_role="
        + repr((component, owner, method, drift, audit_mode))
        + "\n"
        + r"""
from hmp_startup import gateway_entry as original_entry
from hmp_startup import retained_binding_origin as selected_helpers
from hmp_startup import link_factory_origin as parent_audit
from hmp_plugin import presentation_native_link as native_link
parent=tuple.__getitem__(original_entry._ENTRY_ORIGIN,10)
assert parent_audit.current_started(parent) is parent
component,owner_name,name,drift,audit_mode=method_role
audit=parent_audit.current if audit_mode=="generic" else parent_audit.current_started
names=vars(sys.modules['hmp_startup.'+component])
kind=None if owner_name is None else names[owner_name]
raw=names[name] if kind is None else vars(kind)[name]
function=raw.__func__ if type(raw) is staticmethod else raw
original_code=function.__code__
original_defaults=function.__defaults__;original_kw=function.__kwdefaults__
selected=(selected_helpers.current if audit_mode=="generic" else selected_helpers.current_live)
selected_code=selected.__code__
engine=native_link._engine_origin_tail if audit_mode=="generic" else native_link._engine_live_tail
engine_code=engine.__code__
engine_defaults=engine.__defaults__;engine_kw=engine.__kwdefaults__
engine_pairs=tuple(engine_kw.items())
engine_origin=parent[0][4];engine_layout=parent[0][5]
ledger=entry._scope.native_files.ledger
before=(tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))
reached=[];foreign_calls=[];engine_calls=[]
def foreign(*args,**kwargs):
    foreign_calls.append(True)
    raise AssertionError('changed classmethod called')
changed_code=function.__code__.replace(co_name='synthetic_late_cache_planner')
def observe(frame,event,value):
    if event=='call' and (frame.f_code is original_code or frame.f_code is changed_code):
        foreign_calls.append(True)
    if event=='call' and frame.f_code is engine_code:
        actual_engine=(native_link._engine_origin_tail if audit_mode=="generic"
                       else native_link._engine_live_tail)
        engine_calls.append((actual_engine is engine,
            engine.__code__ is engine_code,engine.__defaults__ is engine_defaults,
            engine.__kwdefaults__ is engine_kw,
            all(engine_kw.get(k) is v for k,v in engine_pairs),
            frame.f_locals.get('origin') is engine_origin,
            (audit_mode=='generic' or frame.f_locals.get('bound_layout') is engine_layout)))
    if event=='return' and frame.f_code is selected_code:
        assert value is parent[0][6][6] and reached==[]
        if drift=='code':function.__code__=changed_code
        elif drift=='defaults':function.__defaults__=(object(),)
        else:function.__kwdefaults__={'unexpected':object()}
        reached.append(True)
assert sys.getprofile() is None
sys.setprofile(observe);error=None;returned=False
try:audit(parent);returned=True
except RuntimeError as caught:error=caught
finally:
    sys.setprofile(None);function.__code__=original_code
    function.__defaults__=original_defaults;function.__kwdefaults__=original_kw
assert type(error) is RuntimeError and error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',), (
    type(error).__name__, None if error is None else error.args,
    returned, reached, engine_calls, foreign_calls)
assert reached==[True] and not returned and foreign_calls==[]
assert len(engine_calls)==1 and all(engine_calls[0]),engine_calls
assert (tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes))==before
assert (names[name] if kind is None else vars(kind)[name]) is raw
assert function.__code__ is original_code
"""
    )
    monkeypatch.setattr(base, "SCRIPT", base.SCRIPT.replace(marker, marker + extra, 1))
    base.test_actual_entry_and_wrapper_files(tmp_path, "normal")
