"""Persistent runtime plain-code custody; descriptor constructors remain separate."""

import importlib
import sys

import pytest

from hmp_startup import gateway_approval  # original Entry loads fixed runtime modules
from hmp_startup import retained_binding_origin as origin

ROLES = (
    ("runtime_files", "RuntimeFilesError", "__init__"),
    ("runtime_files", None, "_require"),
    ("runtime_files", None, "_pairs"),
    ("runtime_files", None, "_document"),
    ("runtime_files", None, "_path"),
    ("runtime_files", None, "_inside"),
    ("runtime_files", None, "_typed_equal"),
    ("runtime_files", None, "_library_name"),
    ("runtime_files", "LinkHop", "__repr__"),
    ("runtime_files", "ExecutableLinkPlan", "__repr__"),
    ("runtime_files", None, "_link_plan"),
    ("runtime_files", "RuntimeFilePlan", "__repr__"),
    ("runtime_files", None, "build_runtime_plan"),
    ("runtime_files", None, "build_runtime_link_plan"),
    ("runtime_files", None, "_build_runtime_plan"),
    ("runtime_files", None, "plan_current"),
    ("runtime_files", None, "loaded_origins"),
    ("entry_files", "EntryFilesError", "__init__"),
    ("entry_files", None, "_require"),
    ("entry_files", None, "_same_package"),
    ("entry_files", None, "_pairs"),
    ("entry_files", "_Inputs", "__repr__"),
    ("entry_files", None, "_decode"),
    ("entry_files", "EntryFileSnapshotOwner", "_current"),
    ("entry_files", "EntryFileSnapshotOwner", "_pure_lineage"),
    ("entry_files", "EntryFileSnapshotOwner", "_pure_current"),
    ("entry_files", "EntryFileSnapshotOwner", "_io_current"),
    ("entry_files", "EntryFileSnapshotOwner", "_names"),
    ("entry_files", "EntryFileSnapshotOwner", "_tree"),
    ("entry_files", "EntryFileSnapshotOwner", "_metadata"),
    ("entry_files", "EntryFileSnapshotOwner", "_walk"),
    ("entry_files", "EntryFileSnapshotOwner", "_origins"),
    ("entry_files", "EntryFileSnapshotOwner", "__repr__"),
    ("cache_context", "CacheContextError", "__init__"),
    ("cache_context", None, "_require"),
    ("cache_context", "CacheInputData", "__repr__"),
    ("cache_context", "_ContextSource", "__repr__"),
    ("cache_context", None, "_context"),
    ("cache_context", None, "_getter_current"),
    ("cache_context", None, "_rows"),
    ("cache_context", "CacheContextOwner", "__repr__"),
    ("cache_context", "CacheContextOwner", "_seal"),
    ("cache_context", "CacheContextOwner", "retained_binding"),
    ("cache_context", "CacheContextOwner", "current_binding"),
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
    (7, "_artifacts", 4, None),
    (7, "_PRIVATE", 0, "_PRIVATE"),
    (7, "_table_rows", 0, "_table_rows"),
    (7, "ExpectedArtifact", 4, "ExpectedArtifact"),
    (7, "_expected", 4, "_expected"),
    (7, "_HashedArtifact", 4, "_HashedArtifact"),
    (8, "GatewayActivationOwner", 3, "GatewayActivationOwner"),
    (8, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
    (8, "_same_origins", 0, "_same_origins"),
    (8, "_Scan", 0, "_Scan"),
    (8, "_table_rows", 0, "_table_rows"),
    (8, "_Tree", 0, "_Tree"),
    (8, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
    (8, "_same_recipe_binding", 1, "_same_recipe_binding"),
    (8, "ExpectedArtifact", 4, "ExpectedArtifact"),
    (8, "StartupArtifactOwner", 4, "StartupArtifactOwner"),
    (8, "_capture_native_scope", 4, "_capture_native_scope"),
    (8, "_descriptor_closed_in_scope", 4, "_descriptor_closed_in_scope"),
    (8, "_descriptor_refused", 4, "_descriptor_refused"),
    (8, "_expected", 4, "_expected"),
    (8, "_HashedArtifact", 4, "_HashedArtifact"),
    (8, "_identity", 4, "_identity"),
    (8, "_native_registration_tail", 4, "_native_registration_tail"),
    (8, "_native_walk_scope", 4, "_native_walk_scope"),
    (8, "_Scope", 4, "_Scope"),
    (8, "gateway_entry", 6, None),
    (8, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
    (9, "GatewayPackageOwner", 0, "GatewayPackageOwner"),
    (9, "GatewayRecipeOwner", 1, "GatewayRecipeOwner"),
    (9, "_same_recipe_binding", 1, "_same_recipe_binding"),
    (9, "ExpectedArtifact", 4, "ExpectedArtifact"),
    (9, "RuntimeFilePlan", 7, "RuntimeFilePlan"),
    (9, "RuntimePackage", 7, "RuntimePackage"),
    (9, "plan_current", 7, "plan_current"),
    (9, "EntryFileSnapshotOwner", 8, "EntryFileSnapshotOwner"),
    (9, "_Inputs", 8, "_Inputs"),
    (9, "_same_package", 8, "_same_package"),
    (9, "GatewayEntryOwner", 6, "GatewayEntryOwner"),
    (9, "_origin_current", 6, "_origin_current"),
)


@pytest.mark.parametrize("alias", ALIASES)
def test_initial_wrong_imported_alias_cannot_become_coherent_authority(monkeypatch, alias):
    index, name, _, _ = alias
    module = sys.modules[origin._MODULES[index]]
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
