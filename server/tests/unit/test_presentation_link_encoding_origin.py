"""Actual original basename encoding DATA; no file effects or image admission."""
import os
import sys

import pytest

from hmp_startup import link_factory_origin as origins


@pytest.fixture
def captured(monkeypatch):
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    return origins.capture()


@pytest.mark.parametrize('name', ('python', 'native module.py', 'naïve_羊.py', '_runtime.zip'))
def test_actual_encoded_return_matches_original_filesystem_settings(captured, name):
    returned = []
    code = origins.encode_basename.__code__

    def trace(frame, event, result):
        if event == 'call':
            if frame.f_code is not code:
                return None
            frame.f_trace_lines = False
        if event == 'return' and frame.f_code is code:
            returned.append((result, frame.f_locals['data']))
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        value = origins.encode_basename(captured, name)
    finally:
        sys.settrace(previous)
    assert len(returned) == 1 and returned[0][0] is value
    assert value.value is returned[0][1]  # actual saved C-method return, not re-encoded
    assert value.origin is captured and value.name is name
    assert value.encoding_origin is captured[0][3]
    assert value.value == os.fsencode(name)
    assert (value.encoding_origin.encoding, value.encoding_origin.errors) == (
        sys.getfilesystemencoding(), sys.getfilesystemencodeerrors())


@pytest.mark.parametrize('name', ('', '.', '..', '/python', 'part/python', 'bad\0name',
                                 'bad\nname', '\udcff', 'x' * 4097, None, b'python', True))
def test_bad_component_refuses_before_any_encoding_query(captured, name):
    calls = []
    getter, errors = captured[0][3].get_encoding, captured[0][3].get_errors

    def observe(frame, event, value):
        if event == 'c_call' and (value is getter or value is errors):
            calls.append(value)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_BASENAME_REFUSED'):
            origins.encode_basename(captured, name)
    finally:
        sys.setprofile(previous)
    assert calls == []


def test_foreign_basename_protocols_are_never_invoked(captured):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign name getter')
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign name equality')

    with pytest.raises(RuntimeError, match='BI1_LINK_BASENAME_REFUSED'):
        origins.encode_basename(captured, Foreign())
    assert calls == []


@pytest.mark.parametrize('fault', ('getitem', 'iter', 'result_ctor_code', 'result_ctor_globals',
                                  'result_dispatch_after_ctor', 'class_export'))
def test_current_return_drift_refuses_before_foreign_dispatch_or_constructor(captured, monkeypatch, fault):
    reached, calls = [], []
    code = origins.current.__code__
    target = (1 if fault in ('getitem', 'iter') else
              7 if fault == 'result_dispatch_after_ctor' else 6)

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign encoding dependency invoked')

    def changed_code(*args, **kwargs):
        raise AssertionError('changed encoded constructor executed')

    def trace(frame, event, result):
        if event == 'call':
            if frame.f_code is not code:
                return None
            frame.f_trace_lines = False
        if event == 'return' and frame.f_code is code:
            reached.append(True)
            if len(reached) == target:
                sys.settrace(None)
                if fault in ('getitem', 'iter'):
                    monkeypatch.setattr(origins._FilesystemEncodingOrigin,
                                        '__getitem__' if fault == 'getitem' else '__iter__',
                                        foreign, raising=False)
                elif fault == 'result_ctor_code':
                    monkeypatch.setattr(origins._EncodedBasename.__new__, '__code__', changed_code.__code__)
                elif fault == 'result_ctor_globals':
                    monkeypatch.setitem(origins._EncodedBasename.__new__.__globals__, '_tuple_new', foreign)
                elif fault == 'class_export':
                    monkeypatch.setattr(origins, '_EncodedBasename', foreign)
                else:
                    monkeypatch.setattr(origins._EncodedBasename, '__getattribute__', foreign, raising=False)
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.encode_basename(captured, 'python')
    finally:
        sys.settrace(previous)
    assert len(reached) == target and calls == []


@pytest.mark.parametrize('fault', ('getter_export', 'current_default', 'result_ctor', 'result_dispatch'))
def test_actual_setting_getter_return_rejoins_original_dependencies(captured, monkeypatch, fault):
    reached, calls = [], []
    getter = captured[0][3].get_encoding
    code = origins.encode_basename.__code__

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign encoding callback invoked')

    def observe(frame, event, value):
        if event == 'c_return' and value is getter and frame.f_code is code and not reached:
            reached.append(True)
            sys.setprofile(None)
            if fault == 'getter_export':
                monkeypatch.setattr(sys, 'getfilesystemencoding', foreign)
            elif fault == 'current_default':
                monkeypatch.setitem(origins.current.__kwdefaults__, '_type', foreign)
            elif fault == 'result_ctor':
                monkeypatch.setattr(origins._EncodedBasename, '__new__', staticmethod(foreign))
            else:
                monkeypatch.setattr(origins._EncodedBasename, '__getattribute__', foreign, raising=False)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.encode_basename(captured, 'python')
    finally:
        sys.setprofile(previous)
    assert reached == [True] and calls == []
    if fault == 'getter_export':
        assert vars(sys)['getfilesystemencoding'] is foreign
        monkeypatch.setattr(sys, 'getfilesystemencoding', getter)


@pytest.mark.parametrize('fault', ('origin_ctor_code', 'origin_ctor_globals', 'own_helper_code'))
def test_capture_final_rejoin_cannot_nominate_changed_constructor(monkeypatch, fault):
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    code = origins.capture.__code__
    reached, calls = [], []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign startup constructor invoked')

    def changed_code(*args, **kwargs):
        raise AssertionError('changed startup dependency executed')

    # Observe the actual local startup rejoin RETURN immediately before origin
    # construction. The raw C getter returns alone are not this last boundary.
    def trace(frame, event, result):
        if event == 'call':
            if (frame.f_code.co_name != 'rejoin' or frame.f_back is None
                    or frame.f_back.f_code is not code):
                return None
            frame.f_trace_lines = False
        if (event == 'return' and frame.f_code.co_name == 'rejoin'
                and frame.f_back is not None and frame.f_back.f_code is code):
            reached.append(True)
            if len(reached) == 3:
                sys.settrace(None)
                if fault == 'origin_ctor_code':
                    monkeypatch.setattr(origins._FilesystemEncodingOrigin.__new__, '__code__', changed_code.__code__)
                elif fault == 'origin_ctor_globals':
                    monkeypatch.setitem(origins._FilesystemEncodingOrigin.__new__.__globals__, '_tuple_new', foreign)
                else:
                    monkeypatch.setattr(origins.current, '__code__', changed_code.__code__)
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.capture()
    finally:
        sys.settrace(previous)
    assert len(reached) == 3 and calls == [] and origins._CAPTURE_STARTED is True
