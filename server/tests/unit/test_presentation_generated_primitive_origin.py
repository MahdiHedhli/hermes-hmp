"""Native closure primitives and field correspondence before helper selection."""

import sys

import pytest

from hmp_startup import link_factory_origin as origins

from .test_presentation_generated_method_origin import ROLES, _function

PRIMITIVE_CELLS = tuple(
    (role, index, name)
    for role in ROLES
    if _function(role).__module__ == "collections"
    for index, name in enumerate(_function(role).__code__.co_freevars)
)


@pytest.mark.parametrize("role,index,name", PRIMITIVE_CELLS)
def test_initial_generated_primitive_or_field_drift_refuses_without_protocols(role, index, name):
    component, owner, _ = role
    module_name = component if component.startswith("hmp_") else "hmp_startup." + component
    kind = vars(sys.modules[module_name])[owner]
    function = _function(role)
    cell = function.__closure__[index]
    original = cell.cell_contents
    calls = []

    class Foreign:
        def __call__(self, *args, **kwargs):
            calls.append("call")
            raise AssertionError("foreign closure primitive invoked")

        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("foreign primitive compared")

    class Number(int):
        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("foreign field count compared")

        def __ne__(self, other):
            calls.append("ne")
            raise AssertionError("foreign field count compared")

    class Format(str):
        def __mod__(self, other):
            calls.append("format")
            raise AssertionError("foreign format used")

    if name == "field_names":
        replacement = tuple(list(original))  # noqa: C414 -- force a distinct equal tuple.
        assert replacement is not original and replacement == original
    elif name == "num_fields":
        replacement = Number(original)
    elif name == "repr_fmt":
        replacement = Format(original)
    else:
        assert name in ("_len", "tuple_new", "_map", "_dict", "_zip", "_tuple")
        replacement = Foreign()
    error = None
    cell.cell_contents = replacement
    try:
        origins._pin_type(kind)
    except BaseException as caught:
        error = caught
    finally:
        cell.cell_contents = original
    assert type(error) is RuntimeError and error.args == ("BI1_LINK_FACTORY_ORIGIN_REFUSED",)
    assert calls == []
    assert origins._pin_type(kind)[0] is kind


def test_coherent_export_default_and_cell_cannot_replace_original_map():
    import builtins

    from hmp_startup import gateway_entry as entry

    kind = vars(sys.modules["hmp_startup.runtime_files"])["RuntimePackage"]
    function = vars(kind)["_replace"]
    cell = function.__closure__[function.__code__.co_freevars.index("_map")]
    original_cell = cell.cell_contents
    original_export = builtins.map
    defaults = origins.current.__kwdefaults__
    original_default = defaults["_map"]
    calls = []

    class Foreign:
        def __call__(self, *args, **kwargs):
            calls.append("call")
            raise AssertionError("nominated map called")

    foreign = Foreign()
    error = None
    try:
        builtins.map = defaults["_map"] = cell.cell_contents = foreign
        origins.current(entry._ENTRY_ORIGIN.link_policy)
    except BaseException as caught:
        error = caught
    finally:
        cell.cell_contents = original_cell
        defaults["_map"] = original_default
        builtins.map = original_export
    assert type(error) is RuntimeError and error.args == ("BI1_LINK_FACTORY_ORIGIN_REFUSED",)
    assert calls == []
    assert origins.current(entry._ENTRY_ORIGIN.link_policy) is entry._ENTRY_ORIGIN.link_policy


def test_original_capture_passes_held_map_despite_late_default_nomination(monkeypatch):
    import builtins
    from types import CodeType

    kind = vars(sys.modules["hmp_startup.runtime_files"])["RuntimePackage"]
    function = vars(kind)["_replace"]
    cell = function.__closure__[function.__code__.co_freevars.index("_map")]
    original_cell = cell.cell_contents
    original_map = builtins.map
    original_defaults = origins._pin_type.__kwdefaults__
    original_default = original_defaults["_map"]
    pin_code = origins._pin_type.__code__
    generators = tuple(
        code
        for code in origins.capture.__code__.co_consts
        if type(code) is CodeType and "pin_type" in code.co_freevars
    )
    assert len(generators) == 1
    target_code = generators[0]
    reached, actual_arguments, calls = [], [], []

    class Foreign:
        def __call__(self, *args, **kwargs):
            calls.append("call")
            raise AssertionError("nominated default map called")

    foreign = Foreign()

    def observe(frame, event, value):
        if event == "call":
            frame.f_trace_lines = frame.f_code is target_code
            if frame.f_code is pin_code and frame.f_locals.get("kind") is kind:
                assert reached == [True]
                assert original_defaults["_map"] is builtins.map is cell.cell_contents is foreign
                actual_arguments.append(frame.f_locals.get("_map") is original_map)
        if (
            event == "line"
            and frame.f_code is target_code
            and not reached
            and frame.f_locals.get("name") == "RuntimePackage"
        ):
            builtins.map = original_defaults["_map"] = cell.cell_contents = foreign
            reached.append(True)
        return observe

    # Test-only capture reset; never production recovery or entry replacement.
    monkeypatch.setattr(origins, "_CAPTURE_STARTED", False)
    assert sys.gettrace() is None and sys.getprofile() is None
    error = None
    sys.settrace(observe)
    try:
        origins.capture()
    except BaseException as caught:
        error = caught
    finally:
        sys.settrace(None)
        cell.cell_contents = original_cell
        original_defaults["_map"] = original_default
        builtins.map = original_map
    assert reached == actual_arguments == [True]
    assert type(error) is RuntimeError and error.args == ("BI1_LINK_FACTORY_ORIGIN_REFUSED",)
    assert calls == []
