"""Original early dependency capture controls; not native/host qualification."""
import builtins
import sys
from types import ModuleType

import pytest

from hmp_plugin import presentation_native_link as link
from hmp_startup import link_factory_origin as origins
from .test_presentation_link_metadata_boundary import Foreign


@pytest.mark.parametrize('slot', ('checker', 'dependency'))
def test_capture_fences_keyword_dict_subclasses_before_items(monkeypatch, slot):
    calls = []

    class Trap(dict):
        def items(self):
            calls.append('items')
            raise AssertionError('foreign keyword dictionary was dispatched')

    selected = (link._engine_origin_tail if slot == 'checker'
                else link.metadata._capture_payload_origin)
    monkeypatch.setattr(selected, '__kwdefaults__', Trap(selected.__kwdefaults__ or {}))
    with pytest.raises(RuntimeError):
        link._capture_engine()
    assert calls == []


@pytest.mark.parametrize('name', ('metadata', 'artifacts_module', 'custody_module', 'policy', 'sys'))
def test_capture_fences_module_aliases_before_vars(monkeypatch, name):
    calls = []
    monkeypatch.setattr(link, name, Foreign(calls))
    with pytest.raises(RuntimeError):
        link._capture_engine()
    assert calls == []


@pytest.mark.parametrize('fault', ('checker_export', 'core_code', 'getter_code',
                                  'closure', 'constructor_namespace_key'))
def test_capture_reseals_originals_after_held_checker_return(monkeypatch, fault):
    calls, observed = [], []
    checker_code = link._engine_origin_tail.__code__
    capture_code = link._capture_engine.__code__

    def foreign(*args, **kwargs):
        calls.append('foreign checker')
        raise AssertionError('foreign checker executed')

    def changed(*args, **kwargs):
        raise AssertionError('changed dependency code executed')

    class Key:
        def __hash__(self):
            calls.append('hash')
            return 147293

        def __eq__(self, other):
            calls.append('equality')
            raise AssertionError('foreign namespace equality executed')

    def observe(frame, event, returned):
        if frame.f_code is not checker_code:
            return None
        frame.f_trace_lines = False
        if event == 'return' and frame.f_back.f_code is capture_code and not observed:
            observed.append(True)
            if fault == 'checker_export':
                monkeypatch.setattr(link, '_engine_origin_tail', foreign)
            elif fault == 'core_code':
                monkeypatch.setattr(link._require, '__code__', changed.__code__)
            elif fault == 'getter_code':
                monkeypatch.setattr(link.metadata._MetadataResult.raw.fget, '__code__', changed.__code__)
            elif fault == 'closure':
                function = link.ArtifactObservationError.__init__
                index = function.__code__.co_freevars.index('__class__')
                monkeypatch.setattr(function.__closure__[index], 'cell_contents', RuntimeError)
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


def test_parent_refuses_self_consistent_foreign_sys_root(monkeypatch):
    fake = ModuleType('sys')
    fake.modules = dict(sys.modules)
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    seen = []
    code = link._capture_engine.__code__

    def observe(frame, event, returned):
        if frame.f_code is not code:
            return None
        frame.f_trace_lines = False
        if event == 'call':
            # Inject at the intended engine boundary, after the earlier retained-
            # helper capture; changing it before that capture tests another guard.
            monkeypatch.setattr(link, 'sys', fake)
        if event == 'return':
            if type(returned) is tuple:
                engine = returned[0]
                seen.append(engine[4][0] is fake and engine[4][2] is fake.modules)
            monkeypatch.setattr(link, 'sys', sys)
        return observe

    prior = sys.gettrace()
    assert prior is None
    sys.settrace(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.capture()
    finally:
        sys.settrace(prior)
    assert seen == [True] and origins._CAPTURE_STARTED is True


def test_engine_capture_never_delegates_to_pin_helpers(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('capture delegated to a replaceable helper')

    monkeypatch.setattr(origins, '_pin_function', foreign)
    monkeypatch.setattr(origins, '_pin_type', foreign)
    packet = link._capture_engine()[0]
    assert link._engine_origin_tail(packet) is packet and calls == []


def test_engine_capture_has_no_initialization_import_callback(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('capture executed an import callback')

    with monkeypatch.context() as context:
        context.setattr(builtins, '__import__', foreign)
        packet = link._capture_engine()[0]
    assert link._engine_origin_tail(packet) is packet and calls == []


def test_capture_rejects_a_non_native_record_allocator_before_call(monkeypatch):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign record allocator executed')

    monkeypatch.setattr(link, '_RECORD_ALLOCATOR', foreign)
    with pytest.raises(link.ArtifactObservationError):
        link._capture_engine()
    assert calls == []
