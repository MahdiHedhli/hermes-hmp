"""Fresh native key predicates and per-audit namespace identity controls.

These are local capture/refusal checks, not native-work or device qualification.
"""
import builtins
import sys

import pytest

from hmp_plugin import presentation_native_link as link


@pytest.mark.parametrize('slot', ('_id', '_map', '_not_identity'))
@pytest.mark.parametrize('drift', ('entry', 'dictionary'))
def test_replaced_native_primitive_default_refuses_before_dispatch(monkeypatch, slot, drift):
    original = link._capture_engine()[0]
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign native primitive executed')

    if drift == 'entry':
        monkeypatch.setitem(link._engine_origin_tail.__kwdefaults__, slot, foreign)
    else:
        changed = dict(link._engine_origin_tail.__kwdefaults__)
        changed[slot] = foreign
        monkeypatch.setattr(link._engine_origin_tail, '__kwdefaults__', changed)
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail(original)
    assert calls == []


def test_python_map_imitation_cannot_supply_a_native_constructor(monkeypatch):
    original = link._capture_engine()[0]
    calls = []

    class map:
        __module__ = 'builtins'

        def __new__(cls, *args, **kwargs):
            calls.append(True)
            raise AssertionError('foreign map constructor executed')

    monkeypatch.setitem(link._engine_origin_tail.__kwdefaults__, '_map', map)
    actual = builtins.map
    caught = False
    builtins.map = map
    try:
        try:
            link._engine_origin_tail(original)
        except link.ArtifactObservationError:
            caught = True
    finally:
        builtins.map = actual
    assert caught and calls == []


@pytest.mark.parametrize('slot', ('_id', '_map', '_not_identity'))
@pytest.mark.parametrize('fault', ('value', 'duplicate_and_omitted'))
def test_original_keyword_pairs_are_rejoined_before_native_index_use(slot, fault):
    original = link._capture_engine()[0]
    rows = list(original[2])
    position = next(i for i, row in enumerate(rows) if row[0] == '_engine_origin_tail')
    row = rows[position]
    if fault == 'value':
        pairs = tuple((name, object() if name == slot else value) for name, value in row[6])
    else:
        replacement = next(pair for pair in row[6] if pair[0] == '_type')
        pairs = tuple(replacement if pair[0] == slot else pair for pair in row[6])
    rows[position] = (*row[:6], pairs)
    changed = (*original[:2], tuple(rows), *original[3:])
    calls = []
    code = link._engine_origin_tail.__code__
    native_id = builtins.id

    def observe(frame, event, value):
        if frame.f_code is code and event == 'c_call' and value is native_id:
            calls.append(True)

    prior = sys.getprofile()
    assert prior is None
    sys.setprofile(observe)
    try:
        with pytest.raises(link.ArtifactObservationError):
            link._engine_origin_tail(changed)
    finally:
        sys.setprofile(prior)
    assert calls == []


@pytest.mark.parametrize('export', ('id', 'map', 'is_not'))
def test_capture_rechecks_native_exports_after_checker_return(export):
    calls, observed = [], []
    checker_code = link._engine_origin_tail.__code__
    capture_code = link._capture_engine.__code__
    module = sys.modules['_operator'] if export == 'is_not' else builtins
    original = getattr(module, export)
    assign = setattr

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('changed native export executed')

    def observe(frame, event, value):
        if frame.f_code is not checker_code:
            return None
        frame.f_trace_lines = False
        if event == 'return' and frame.f_back.f_code is capture_code and not observed:
            observed.append(True)
            assign(module, export, foreign)
        return observe

    prior = sys.gettrace()
    assert prior is None
    caught = False
    sys.settrace(observe)
    try:
        try:
            link._capture_engine()
        except RuntimeError:
            caught = True
    finally:
        sys.settrace(prior)
        assign(module, export, original)
    assert observed == [True] and caught and calls == []


@pytest.mark.parametrize('namespace', ('module', 'constructor'))
def test_another_call_rescans_foreign_keys_without_metaclass_protocols(monkeypatch, namespace):
    original = link._capture_engine()[0]
    assert link._engine_origin_tail(original) is original
    calls = []

    class Meta(type):
        def __eq__(self, other):
            calls.append('metaclass equality')
            raise AssertionError('foreign metaclass equality executed')

        def __hash__(self):
            calls.append('metaclass hash')
            raise AssertionError('foreign metaclass hash executed')

    class Key(metaclass=Meta):
        def __hash__(self):
            calls.append('key hash')
            return hash(key_name)

        def __eq__(self, other):
            calls.append('key equality')
            raise AssertionError('foreign key equality executed')

        def __len__(self):
            calls.append('length')
            raise AssertionError('foreign length executed')

    names = vars(link) if namespace == 'module' else link._LinkSnapshot.__new__.__globals__
    # Preserve size but replace an original key with a colliding foreign key.
    # Skipping the key-type fence would reach its equality on later lookup.
    key_name = '_ENGINE_FUNCTIONS' if namespace == 'module' else '_tuple_new'
    key = Key()
    monkeypatch.delitem(names, key_name)
    monkeypatch.setitem(names, key, object())
    calls.clear()
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail(original)
    assert calls == []


def test_reordered_equivalent_namespace_keeps_original_identity_semantics():
    original = link._capture_engine()[0]
    names = vars(link)
    value = names.pop('_ENGINE_FUNCTIONS')
    names['_ENGINE_FUNCTIONS'] = value
    assert link._engine_origin_tail(original) is original
    assert link._dependency_mirrors(original[4]) is original[4]


@pytest.mark.parametrize('entries', ({}, {'synthetic_unused_keyword': True}))
def test_empty_and_nonempty_keyword_snapshots_remain_fresh(monkeypatch, entries):
    monkeypatch.setattr(link.policy._need, '__kwdefaults__', entries)
    original = link._capture_engine()[0]
    assert link._engine_origin_tail(original) is original
    entries['changed_after_capture'] = object()
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail(original)


def test_equal_copied_function_namespace_cannot_replace_original_reference():
    original = link._capture_engine()[0]
    dependencies = original[4]
    modules = list(dependencies[3])
    row = modules[0]
    functions = list(row[5])
    selected = functions[0]
    copied = dict(selected[2])
    assert copied is not selected[2]
    functions[0] = (*selected[:2], copied, *selected[3:])
    modules[0] = (*row[:5], tuple(functions))
    changed = (*dependencies[:3], tuple(modules))
    with pytest.raises(link.ArtifactObservationError):
        link._engine_origin_tail((*original[:4], changed))
