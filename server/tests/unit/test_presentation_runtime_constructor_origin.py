"""Original runtime constructor metadata, without invoking a constructor."""
import importlib
import sys

import pytest

from hmp_startup import gateway_entry as entry
from hmp_startup import link_factory_origin as origins

KINDS = (
    ('runtime_files', 'RuntimePackage'),
    ('runtime_files', 'LinkHop'),
    ('runtime_files', 'ExecutableLinkPlan'),
    ('runtime_files', 'RuntimeFilePlan'),
    ('entry_files', '_Inputs'),
    ('cache_context', 'CacheInputData'),
    ('cache_context', '_ContextSource'),
)


@pytest.mark.parametrize('role', KINDS)
@pytest.mark.parametrize('drift', ('code', 'defaults', 'keyword_defaults',
                                  'globals_name', 'globals_builtin', 'extra_global'))
def test_runtime_constructor_drift_refuses_without_constructor_calls(monkeypatch, role, drift):
    short, name = role
    kind = vars(importlib.import_module('hmp_startup.' + short))[name]
    constructor = vars(kind)['__new__'].__func__
    parent = entry._ENTRY_ORIGIN.link_policy
    assert origins.current(parent) is parent
    changed_code = constructor.__code__.replace(co_name='synthetic_constructor_drift')
    calls = []

    def observe(frame, event, value):
        if event == 'call' and (frame.f_code is constructor.__code__
                                or frame.f_code is changed_code):
            calls.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with monkeypatch.context() as change:
            if drift == 'code':
                change.setattr(constructor, '__code__', changed_code)
            elif drift == 'defaults':
                change.setattr(constructor, '__defaults__', (object(),))
            elif drift == 'keyword_defaults':
                change.setattr(constructor, '__kwdefaults__', {'unexpected': object()})
            elif drift == 'globals_name':
                change.setitem(constructor.__globals__, '__name__', 'synthetic_wrong_module')
            elif drift == 'globals_builtin':
                change.setitem(constructor.__globals__, '__builtins__', object())
            else:
                change.setitem(constructor.__globals__, 'synthetic_extra_global', object())
            with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
                origins.current(parent)
    finally:
        sys.setprofile(None)
    assert calls == []
    assert origins.current(parent) is parent


@pytest.mark.parametrize('role', KINDS)
def test_initial_constructor_filename_subclass_refuses_without_protocols(monkeypatch, role):
    short, name = role
    kind = vars(importlib.import_module('hmp_startup.' + short))[name]
    constructor = vars(kind)['__new__'].__func__
    calls = []

    class Text(str):
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign filename compared')

        def __ne__(self, other):
            calls.append('ne')
            raise AssertionError('foreign filename compared')

    code = constructor.__code__.replace(co_filename=Text(constructor.__code__.co_filename))
    assert type(code.co_filename) is Text
    with monkeypatch.context() as change:
        change.setattr(constructor, '__code__', code)
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins._pin_type(kind)
    assert calls == []


@pytest.mark.parametrize('fault', ('class_key', 'keyword_key', 'globals_key'))
def test_initial_constructor_namespace_keys_refuse_without_protocols(fault):
    import gc
    from typing import NamedTuple

    class SyntheticConstructor(NamedTuple):
        field: int

    kind = SyntheticConstructor
    constructor = vars(kind)['__new__'].__func__
    calls = []
    armed = False
    label = '_fields' if fault == 'class_key' else 'synthetic_key'

    class Key:
        def __hash__(self):
            if armed:
                calls.append('hash')
            return hash(label)

        def __eq__(self, other):
            if armed:
                calls.append('eq')
                raise AssertionError('foreign key compared')
            return False

    key = Key()
    dictionaries = [v for v in gc.get_referents(vars(kind)) if type(v) is dict]
    assert len(dictionaries) == 1
    namespace = dictionaries[0]
    original = dict(namespace)
    original_kw = constructor.__kwdefaults__
    original_globals = dict(constructor.__globals__)
    if fault == 'class_key':
        namespace.pop('_fields')
        namespace[key] = None
    elif fault == 'keyword_key':
        constructor.__kwdefaults__ = {key: None}
    else:
        constructor.__globals__[key] = None
    armed = True
    error = None
    try:
        origins._pin_type(kind)
    except RuntimeError as caught:
        error = caught
    finally:
        armed = False
        namespace.clear()
        namespace.update(original)
        constructor.__kwdefaults__ = original_kw
        constructor.__globals__.clear()
        constructor.__globals__.update(original_globals)
    assert type(error) is RuntimeError and error.args == ('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
    assert calls == []


@pytest.mark.parametrize('fault', ('global_tuple', 'global_pair', 'global_key',
                                  'global_duplicate', 'keyword_tuple', 'keyword_nonempty'))
def test_malformed_constructor_snapshots_refuse_without_protocols(fault):
    calls = []

    class ForeignTuple(tuple):
        def __iter__(self):
            calls.append('iter')
            raise AssertionError('foreign tuple iterated')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign tuple measured')

    class Foreign:
        def __hash__(self):
            calls.append('hash')
            raise AssertionError('foreign key hashed')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign key compared')

    parent = entry._ENTRY_ORIGIN.link_policy
    pins = list(parent[4])
    pin = list(pins[12])
    assert pin[0].__name__ == '_Inputs' and len(pin) == 12 and pin[9] is None
    globals_pairs = pin[11]
    if fault == 'global_tuple':
        pin[11] = ForeignTuple(globals_pairs)
    elif fault == 'global_pair':
        pin[11] = (ForeignTuple(globals_pairs[0]), *globals_pairs[1:])
    elif fault == 'global_key':
        pin[11] = ((Foreign(), globals_pairs[0][1]), *globals_pairs[1:])
    elif fault == 'global_duplicate':
        assert len(globals_pairs) >= 2
        pin[11] = (globals_pairs[0], globals_pairs[0], *globals_pairs[2:])
    elif fault == 'keyword_tuple':
        pin[10] = ForeignTuple()
    else:
        pin[10] = (('unexpected', object()),)
    pins[12] = tuple(pin)
    candidate = (*parent[:4], tuple(pins))
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.current(candidate)
    assert calls == []
    assert origins.current(parent) is parent
