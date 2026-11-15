"""Declared classmethod code custody without calling or binding a method."""

import importlib
import sys

import pytest

from hmp_startup import gateway_entry as entry
from hmp_startup import retained_binding_origin as origin

ROLES = (
    ("entry_files", "EntryFileSnapshotOwner", "verify"),
    ("entry_files", "EntryFileSnapshotOwner", "verify_runtime_files"),
    ("entry_files", "EntryFileSnapshotOwner", "retain_runtime_files"),
    ("entry_files", "EntryFileSnapshotOwner", "retain_runtime_link_files"),
    ("entry_files", "EntryFileSnapshotOwner", "retain"),
    ("entry_files", "EntryFileSnapshotOwner", "_retain"),
    ("entry_files", "EntryFileSnapshotOwner", "complete"),
    ("cache_context", "CacheContextOwner", "retain"),
)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("drift", ("code", "defaults", "keyword_defaults"))
def test_declared_classmethod_drift_refuses_without_call_or_binding(monkeypatch, role, drift):
    short, owner, name = role
    kind = vars(importlib.import_module("hmp_startup." + short))[owner]
    raw = vars(kind)[name]
    assert type(raw) is classmethod
    function = raw.__func__
    record = origin.capture_bound()
    packet, layout, _ = record
    assert origin.current(packet) is packet
    assert origin.current_live(packet, layout) is packet
    changed_code = function.__code__.replace(co_name="synthetic_classmethod_drift")
    calls = []

    def observe(frame, event, value):
        if event == "call" and (frame.f_code is function.__code__ or frame.f_code is changed_code):
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
    assert calls == [] and vars(kind)[name] is raw
    assert origin.current(packet) is packet
    assert origin.current_live(packet, layout) is packet
    assert entry._OWNER is entry._CELL is entry._STARTED is None


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "wrapper", ("plain", "static", "subclass", "descriptor", "bad_function", "none")
)
def test_initial_wrong_method_wrapper_refuses_without_protocols(monkeypatch, role, wrapper):
    short, owner, name = role
    kind = vars(importlib.import_module("hmp_startup." + short))[owner]
    raw = vars(kind)[name]
    function = raw.__func__
    calls = []
    armed = False

    class Wrapped(classmethod):
        def __getattribute__(self, key):
            if armed:
                calls.append("get")
                raise AssertionError("foreign classmethod inspected")
            return object.__getattribute__(self, key)

        def __get__(self, instance, owner=None):
            calls.append("bind")
            raise AssertionError("foreign classmethod bound")

    class Foreign:
        def __getattribute__(self, key):
            if armed:
                calls.append("get")
                raise AssertionError("foreign descriptor inspected")
            return object.__getattribute__(self, key)

        def __get__(self, instance, owner=None):
            calls.append("bind")
            raise AssertionError("foreign descriptor bound")

        def __call__(self, *args, **kwargs):
            calls.append("call")
            raise AssertionError("foreign callable invoked")

    values = {
        "plain": function,
        "static": staticmethod(function),
        "subclass": Wrapped(function),
        "descriptor": Foreign(),
        "bad_function": classmethod(Foreign()),
        "none": None,
    }
    with monkeypatch.context() as change:
        change.setattr(kind, name, values[wrapper])
        armed = True
        try:
            with pytest.raises(origin.RetainedBindingOriginError):
                origin.capture()
            with pytest.raises(RuntimeError, match="BI1_RETAINED_HELPER_ORIGIN_REFUSED"):
                origin.capture_bound()
        finally:
            armed = False
    assert calls == [] and vars(kind)[name] is raw
    assert origin.current(origin.capture()) is not None


@pytest.mark.parametrize(
    "role",
    (
        ("entry_files", "EntryFileSnapshotOwner", "_pure_current"),
        ("cache_context", "CacheContextOwner", "_seal"),
    ),
)
def test_plain_roles_do_not_accept_classmethod_wrappers(monkeypatch, role):
    short, owner, name = role
    kind = vars(importlib.import_module("hmp_startup." + short))[owner]
    function = vars(kind)[name]
    with monkeypatch.context() as change:
        change.setattr(kind, name, classmethod(function))
        with pytest.raises(origin.RetainedBindingOriginError):
            origin.capture()
        with pytest.raises(RuntimeError, match="BI1_RETAINED_HELPER_ORIGIN_REFUSED"):
            origin.capture_bound()


@pytest.mark.parametrize(
    "fault",
    ("hidden_builtin", "coherent_checker_default", "factory_default", "factory_checker_pairs"),
)
def test_parent_rejects_initial_coherent_native_type_nomination(monkeypatch, fault):
    import builtins

    from hmp_startup import link_factory_origin as parent

    calls = []
    bound_code = origin.capture_bound.__code__

    class Foreign:
        def __getattribute__(self, name):
            calls.append("get")
            raise AssertionError("foreign native-type nominee inspected")

    def observe(frame, event, value):
        if event == "call" and frame.f_code is bound_code:
            calls.append("factory")

    assert sys.getprofile() is None
    with monkeypatch.context() as change:
        change.setattr(parent, "_CAPTURE_STARTED", False)
        if fault == "hidden_builtin":
            change.setitem(builtins.__dict__, "classmethod", Foreign)
            change.setitem(origin.current.__kwdefaults__, "_classmethod", Foreign)
            change.setitem(
                origin.capture_bound.__kwdefaults__, "_checker_pairs", (("_classmethod", Foreign),)
            )
        elif fault == "coherent_checker_default":
            change.setitem(origin.current.__kwdefaults__, "_classmethod", Foreign)
            change.setitem(
                origin.capture_bound.__kwdefaults__, "_checker_pairs", (("_classmethod", Foreign),)
            )
        elif fault == "factory_default":
            change.setitem(origin.capture_bound.__kwdefaults__, "_classmethod", Foreign)
        else:
            change.setitem(
                origin.capture_bound.__kwdefaults__, "_checker_pairs", (("_classmethod", Foreign),)
            )
        sys.setprofile(observe)
        try:
            with pytest.raises(RuntimeError, match="BI1_LINK_FACTORY_ORIGIN_REFUSED"):
                parent.capture()
        finally:
            sys.setprofile(None)
    assert calls == []


def test_parent_refuses_hidden_builtin_clone_before_helper_factory(monkeypatch):
    from types import FunctionType

    from hmp_startup import link_factory_origin as parent

    original = origin.current
    namespace = vars(origin)
    real_builtins = namespace["__builtins__"]
    hidden_builtins = dict(real_builtins)
    namespace["__builtins__"] = hidden_builtins
    try:
        clone = FunctionType(
            original.__code__,
            namespace,
            original.__name__,
            original.__defaults__,
            original.__closure__,
        )
    finally:
        namespace["__builtins__"] = real_builtins
    clone.__kwdefaults__ = dict(original.__kwdefaults__)
    assert clone.__builtins__ is hidden_builtins and clone.__globals__ is namespace
    calls = []
    bound_code = origin.capture_bound.__code__

    def observe(frame, event, value):
        if event == "call" and (frame.f_code is bound_code or frame.f_code is clone.__code__):
            calls.append(True)

    with monkeypatch.context() as change:
        change.setattr(parent, "_CAPTURE_STARTED", False)
        change.setattr(origin, "current", clone)
        for name, value in (
            ("_checker", clone),
            ("_checker_code", clone.__code__),
            ("_checker_defaults", clone.__defaults__),
            ("_checker_kw", clone.__kwdefaults__),
            ("_checker_pairs", tuple(clone.__kwdefaults__.items())),
        ):
            change.setitem(origin.capture_bound.__kwdefaults__, name, value)
        assert sys.getprofile() is None
        sys.setprofile(observe)
        try:
            with pytest.raises(RuntimeError, match="BI1_LINK_FACTORY_ORIGIN_REFUSED"):
                parent.capture()
        finally:
            sys.setprofile(None)
    assert calls == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("mode", ("generic", "live"))
def test_wrapper_replacement_after_class_check_refuses_same_function(monkeypatch, role, mode):
    import ast
    from pathlib import Path

    short, owner, name = role
    kind = vars(importlib.import_module("hmp_startup." + short))[owner]
    raw = vars(kind)[name]
    replacement = classmethod(raw.__func__)
    assert replacement is not raw and replacement.__func__ is raw.__func__
    packet, layout, _ = origin.capture_bound()
    checker = origin.current if mode == "generic" else origin.current_live
    tree = ast.parse(Path(origin.__file__).read_text())
    definition = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == checker.__name__
    )
    target = next(
        n.lineno
        for n in ast.walk(definition)
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "raw_function"
    )
    changed = []
    index = origin._MODULES.index("hmp_startup." + short)

    def observe(frame, event, value):
        if (
            event == "line"
            and frame.f_code is checker.__code__
            and frame.f_lineno == target
            and frame.f_locals.get("index") == index
            and frame.f_locals.get("owner") == owner
            and frame.f_locals.get("name") == name
            and not changed
        ):
            monkeypatch.setattr(kind, name, replacement)
            changed.append(True)
        return observe

    assert sys.gettrace() is None
    sys.settrace(observe)
    try:
        with pytest.raises(RuntimeError, match="BI1_RETAINED_HELPER_ORIGIN_REFUSED"):
            if mode == "generic":
                checker(packet)
            else:
                checker(packet, layout)
    finally:
        sys.settrace(None)
        monkeypatch.setattr(kind, name, raw)
    assert changed == [True]
    assert origin.current(packet) is packet
    assert origin.current_live(packet, layout) is packet
