"""Local helper DATA controls; not early custody, audit reuse or native admission."""
import pytest

from hmp_plugin import presentation_gateway_package as package
from hmp_plugin import presentation_gateway_recipe as recipe
from hmp_startup import retained_binding_origin as origin


@pytest.mark.parametrize('drift', ('package', 'recipe', 'require', 'comparator',
                                  'class_dispatch', 'manifest_dispatch', 'code',
                                  'defaults', 'keyword_defaults'))
def test_changed_helpers_refuse_without_foreign_dispatch(monkeypatch, drift):
    captured = origin.capture()
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign helper dispatched')

    if drift == 'package':
        monkeypatch.setattr(package.GatewayPackageOwner, '_retained_binding', foreign)
    elif drift == 'recipe':
        monkeypatch.setattr(recipe.GatewayRecipeOwner, '_retained_binding', foreign)
    elif drift == 'require':
        monkeypatch.setattr(package, '_require', foreign)
    elif drift == 'comparator':
        monkeypatch.setattr(package, '_same_recipe_binding', foreign)
    elif drift == 'class_dispatch':
        monkeypatch.setattr(package.GatewayPackageOwner, '__getattribute__', foreign,
                            raising=False)
    elif drift == 'manifest_dispatch':
        monkeypatch.setattr(package._Manifest, '__getattribute__', foreign, raising=False)
    elif drift == 'defaults':
        monkeypatch.setattr(package.GatewayPackageOwner._retained_binding, '__defaults__',
                            (object(),))
    elif drift == 'keyword_defaults':
        monkeypatch.setattr(package.GatewayPackageOwner._retained_binding, '__kwdefaults__',
                            {'synthetic': object()})
    else:
        monkeypatch.setattr(package.GatewayPackageOwner._retained_binding, '__code__',
                            (lambda *args: None).__code__)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)
    assert calls == []


@pytest.mark.parametrize('slot', range(6))
def test_foreign_packet_fields_refuse_without_protocols(slot):
    captured = list(origin.capture())
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append('get')
            raise AssertionError('foreign getter')

        def __iter__(self):
            calls.append('iter')
            raise AssertionError('foreign iterator')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')

    captured[slot] = Foreign()
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(tuple(captured))
    assert calls == []


def test_capture_is_data_not_independent_original_custody():
    captured = origin.capture()
    assert origin.current(captured) is captured
    copied = tuple(list(captured))
    assert copied is not captured
    assert origin.current(copied) is copied  # Future actual parent must refuse this graft.


def test_foreign_live_module_key_refuses_before_hash_or_equality(monkeypatch):
    captured = origin.capture()
    calls = []

    class ForeignKey:
        def __hash__(self):
            calls.append('hash')
            return hash('_synthetic_retained_helper_key')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign key equality')

    key = ForeignKey()
    monkeypatch.setitem(vars(package), key, None)
    calls.clear()  # Setup is not part of the checker refusal interval.
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)
    assert calls == []


@pytest.mark.parametrize('where', ('module', 'class'))
def test_duplicate_expected_keys_cannot_omit_an_original(where):
    packet = list(origin.capture())
    slot = 3 if where == 'module' else 4
    rows = list(packet[slot])
    row = rows[0]
    pairs = row[2]
    assert len(pairs) >= 2
    changed = (pairs[0], pairs[0], *pairs[2:])
    rows[0] = (*row[:2], changed)
    packet[slot] = tuple(rows)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(tuple(packet))


@pytest.mark.parametrize('drift', ('owner', 'key'))
def test_late_class_export_change_refuses_before_following_new_object(monkeypatch, drift):
    import sys
    from pathlib import Path

    captured = origin.capture()
    calls, fired, keys = [], [], []
    namespace = vars(package)
    original_kind = namespace['GatewayPackageOwner']

    class Foreign:
        __slots__ = ()

        def __getattribute__(self, name):
            calls.append('get')
            raise AssertionError('foreign class getter')

        def __hash__(self):
            calls.append('hash')
            return hash('GatewayPackageOwner')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign key equality')

    code = origin.current.__code__
    lines = Path(code.co_filename).read_text().splitlines()
    end = max(line for _, _, line in code.co_lines() if line is not None)
    boundary = [i + 1 for i in range(code.co_firstlineno - 1, end)
                if 'if owner is not None:' in lines[i]]
    assert len(boundary) == 1

    def trace(frame, event, value):
        if frame.f_code is not code:
            return None
        if event == 'line' and frame.f_lineno == boundary[0] and not fired:
            if drift == 'owner':
                monkeypatch.setattr(package, 'GatewayPackageOwner', Foreign())
            else:
                namespace.pop('GatewayPackageOwner')
                key = Foreign()
                keys.append(key)
                namespace[key] = None
            calls.clear()
            fired.append(True)
        return trace

    prior = sys.gettrace()
    assert prior is None
    sys.settrace(trace)
    try:
        with pytest.raises(origin.RetainedBindingOriginError):
            origin.current(captured)
    finally:
        sys.settrace(prior)
        observed_calls = tuple(calls)
        # Remove the collision key BEFORE restoring the ordinary export. Pytest's
        # separate attribute/dict undo queues restore them in the opposite order.
        if keys:
            namespace.pop(keys[0])
            namespace['GatewayPackageOwner'] = original_kind
    assert fired == [True] and observed_calls == ()


@pytest.mark.parametrize('change', ('exports', 'copied_return'))
def test_checker_callback_cannot_adopt_replacement_or_copy(monkeypatch, change):
    checker = origin.current
    original = package.GatewayPackageOwner._retained_binding
    observed, calls = [], []

    def foreign(*args):
        calls.append(True)
        raise AssertionError('foreign validator executed')

    def callback(packet):
        if change == 'exports':
            monkeypatch.setattr(package.GatewayPackageOwner, '_retained_binding', foreign)
            observed.append(packet[5][0][0] is original)
            return checker(packet)
        checked = checker(packet)
        copied = tuple(list(checked))
        observed.append(copied is not packet)
        return copied

    monkeypatch.setattr(origin, 'current', callback)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()
    assert observed == [True] and calls == []
