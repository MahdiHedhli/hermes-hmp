"""Generated record metadata without invoking helpers or evaluating annotations."""

import importlib
import sys
from types import FunctionType

import pytest

from hmp_startup import gateway_entry as entry
from hmp_startup import link_factory_origin as origins

KINDS = (
    ("hmp_plugin.presentation_link_path_policy", "_LinkPathPolicy"),
    ("hmp_plugin.presentation_link_path_policy", "_LinkPathCursor"),
    ("hmp_plugin.presentation_startup_artifacts", "ExpectedArtifact"),
    ("hmp_plugin.presentation_link_path_policy", "_LinkScopeBlueprint"),
    ("hmp_plugin.presentation_startup_artifacts", "_RuntimeSource"),
    ("hmp_plugin.presentation_startup_artifacts", "_Scope"),
    ("link_factory_origin", "_FilesystemEncodingOrigin"),
    ("link_factory_origin", "_EncodedBasename"),
    ("runtime_files", "RuntimePackage"),
    ("runtime_files", "LinkHop"),
    ("runtime_files", "ExecutableLinkPlan"),
    ("runtime_files", "RuntimeFilePlan"),
    ("entry_files", "_Inputs"),
    ("cache_context", "CacheInputData"),
    ("cache_context", "_ContextSource"),
    ("cache_candidates", "PlannedCachePath"),
)


def _observed_roles():
    rows = []
    for component, owner in KINDS:
        kind = vars(
            importlib.import_module(
                component if component.startswith("hmp_") else "hmp_startup." + component
            )
        )[owner]
        names = (
            "_make",
            "_replace",
            "__replace__",
            "_asdict",
            "__getnewargs__",
            "__annotate_func__",
        )
        names += ("__repr__",)
        for name in names:
            raw = vars(kind).get(name)
            if raw is None:
                continue  # Actual role absence, without interpreter-version branching.
            function = raw.__func__ if type(raw) is classmethod else raw
            assert type(function) is FunctionType
            assert function.__globals__ is vars(sys.modules[function.__module__])
            if name == "__repr__" and function.__module__ not in ("collections", "typing"):
                continue  # Declared HMP repr methods are outside generated-role tests.
            assert function.__module__ in ("collections", "typing")
            rows.append((component, owner, name))
    return tuple(rows)


ROLES = _observed_roles()


def _function(role):
    component, owner, name = role
    kind = vars(
        sys.modules[component if component.startswith("hmp_") else "hmp_startup." + component]
    )[owner]
    raw = vars(kind)[name]
    return raw.__func__ if type(raw) is classmethod else raw


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("drift", ("code", "defaults", "keyword_defaults", "cell"))
def test_generated_metadata_drift_refuses_without_helper_calls(monkeypatch, role, drift):
    function = _function(role)
    parent = entry._ENTRY_ORIGIN.link_policy
    assert origins.current(parent) is parent
    original_code = function.__code__
    changed_code = original_code.replace(co_name="synthetic_generated_metadata_drift")
    calls = []

    def observe(frame, event, value):
        if event == "call" and (frame.f_code is original_code or frame.f_code is changed_code):
            calls.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    cell = None
    try:
        with monkeypatch.context() as change:
            if drift == "code":
                change.setattr(function, "__code__", changed_code)
            elif drift == "defaults":
                change.setattr(function, "__defaults__", (object(),))
            elif drift == "keyword_defaults":
                change.setattr(function, "__kwdefaults__", {"synthetic": object()})
            else:
                assert type(function.__closure__) is tuple and function.__closure__
                cell = function.__closure__[0]
                original_cell_value = cell.cell_contents
                cell.cell_contents = object()
            with pytest.raises(RuntimeError, match="BI1_LINK_FACTORY_ORIGIN_REFUSED"):
                origins.current(parent)
    finally:
        sys.setprofile(None)
        if cell is not None:
            cell.cell_contents = original_cell_value
    assert calls == []
    assert origins.current(parent) is parent


ANNOTATION_CELLS = tuple(
    (role, index)
    for role in ROLES
    if role[2] == "__annotate_func__"
    for index, cell in enumerate(_function(role).__closure__)
    if type(cell.cell_contents) is dict
)


if ANNOTATION_CELLS:

    @pytest.mark.parametrize("role,index", ANNOTATION_CELLS)
    @pytest.mark.parametrize("fault", ("content", "foreign_key"))
    def test_annotation_dictionary_contents_are_fresh_without_evaluation(
        monkeypatch, role, index, fault
    ):
        function = _function(role)
        values = function.__closure__[index].cell_contents
        assert type(values) is dict and all(type(k) is str for k in values)
        parent = entry._ENTRY_ORIGIN.link_policy
        assert origins.current(parent) is parent
        calls = []
        armed = False

        class Key(str):
            __hash__ = str.__hash__

            def __eq__(self, other):
                if armed:
                    calls.append("eq")
                    raise AssertionError("foreign annotation key compared")
                return str.__eq__(self, other)

        with monkeypatch.context() as change:
            key = "synthetic_annotation_value" if fault == "content" else Key("synthetic_key")
            change.setitem(values, key, object())
            armed = True
            try:
                with pytest.raises(RuntimeError, match="BI1_LINK_FACTORY_ORIGIN_REFUSED"):
                    origins.current(parent)
            finally:
                armed = False
        assert calls == []
        assert origins.current(parent) is parent


def test_generated_collector_fences_real_sys_namespace_before_module_lookup():
    kind = vars(sys.modules["hmp_startup.runtime_files"])["RuntimePackage"]
    namespace = vars(sys)
    calls = []
    armed = False

    class Key(str):
        def __hash__(self):
            if armed:
                calls.append("hash")
                raise AssertionError("foreign sys key hashed")
            return str.__hash__(self)

        def __eq__(self, other):
            if armed:
                calls.append("eq")
                raise AssertionError("foreign sys key compared")
            return str.__eq__(self, other)

    key = Key("modules")
    original = namespace.pop("modules")
    namespace[key] = original
    error = None
    armed = True
    try:
        origins._pin_type(kind)
    except BaseException as caught:
        error = caught
    finally:
        armed = False
        namespace.pop(key)
        namespace["modules"] = original
    assert type(error) is RuntimeError, (type(error).__name__, calls)
    assert error.args == ("BI1_LINK_FACTORY_ORIGIN_REFUSED",)
    assert calls == []
    assert origins.current(entry._ENTRY_ORIGIN.link_policy) is entry._ENTRY_ORIGIN.link_policy


@pytest.mark.parametrize("audit_mode", ("generic", "started"))
@pytest.mark.parametrize("drift", ("code", "defaults", "keyword_defaults"))
def test_generated_changes_after_selected_checker_return_refuse(
    tmp_path, monkeypatch, audit_mode, drift
):
    from .test_presentation_cache_candidate_origin import (
        test_cache_planner_drift_after_selected_return_refuses_without_effects as late_check,
    )

    late_check(
        tmp_path, monkeypatch, "runtime_files", "RuntimePackage", "_replace", drift, audit_mode
    )
