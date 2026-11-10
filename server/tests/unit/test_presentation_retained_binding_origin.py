"""Local helper DATA controls; not early custody, audit reuse or native admission."""
import pytest

from hmp_plugin import presentation_gateway_package as package
from hmp_plugin import presentation_gateway_recipe as recipe
from hmp_plugin import presentation_startup_selection as selection
from hmp_plugin import presentation_gateway_activation as activation
from hmp_plugin import presentation_startup_artifacts as artifacts
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


@pytest.mark.parametrize('module', (package, artifacts))
def test_foreign_live_module_key_refuses_before_hash_or_equality(monkeypatch, module):
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
    monkeypatch.setitem(vars(module), key, None)
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


@pytest.mark.parametrize('module,owner,name', (
    (selection, 'StartupSelectionOwner', '_retained_binding'),
    (selection, None, '_approved_recipe'),
    (selection, None, '_approval_binding'),
    (selection, None, '_require'),
    (selection, 'SelectionLoadError', '__init__'),
    (package, 'PackageInventoryError', '__init__'),
    (recipe, 'GatewayRecipeError', '__init__'),
    (activation, 'GatewayActivationOwner', '_retained_scope'),
    (activation, None, '_require'),
    (activation, 'ActivationCaptureError', '__init__'),
    (artifacts, None, '_descriptor_closed_in_scope'),
    (artifacts, None, '_native_descriptor_closed'),
    (artifacts, None, '_native_descriptor_opened'),
    (artifacts, None, '_native_file_allocation_original'),
    (artifacts, None, '_expected'),
    (artifacts, None, '_require'),
    (artifacts, 'ArtifactObservationError', '__init__'),
))
def test_selected_code_only_drift_refuses_before_helper_or_error_dispatch(
        monkeypatch, module, owner, name):
    captured = origin.capture()
    function = getattr(module if owner is None else getattr(module, owner), name)

    def foreign(*args, **kwargs):
        raise AssertionError('changed selected helper dispatched')

    class ForeignError(Exception):
        def __init__(self, *args, **kwargs):
            # Match the original constructor's __class__ closure width; changing
            # only code leaves its original class cell/function identity intact.
            __class__
            raise AssertionError('changed refusal constructor dispatched')

    code = ForeignError.__init__.__code__ if name == '__init__' else foreign.__code__
    assert len(code.co_freevars) == len(function.__code__.co_freevars)
    monkeypatch.setattr(function, '__code__', code)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)


@pytest.mark.parametrize('drift', ('export', 'owner_dispatch', 'scope_dispatch',
                                  'defaults', 'keyword_defaults'))
def test_selection_exports_dispatch_and_metadata_refuse(monkeypatch, drift):
    captured = origin.capture()
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('changed selection object dispatched')

    if drift == 'export':
        monkeypatch.setattr(selection, '_approval_binding', foreign)
    elif drift == 'owner_dispatch':
        monkeypatch.setattr(selection.StartupSelectionOwner, '__getattribute__', foreign,
                            raising=False)
    elif drift == 'scope_dispatch':
        monkeypatch.setattr(selection._ApprovedSelectionSource, '__getattribute__', foreign,
                            raising=False)
    elif drift == 'defaults':
        monkeypatch.setattr(selection._approval_binding, '__defaults__', (True,))
    else:
        monkeypatch.setattr(selection._approved_recipe, '__kwdefaults__', {'synthetic': True})
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)
    assert calls == []


@pytest.mark.parametrize('module,name', ((recipe, '_approved_recipe'),
                                       (recipe, 'StartupSelectionOwner'),
                                       (package, 'StartupSelectionOwner'),
                                       (recipe, 'GatewayActivationOwner'),
                                       (selection, '_LATE_MODULES'),
                                       (package, '_descriptor_closed_in_scope'),
                                       (recipe, '_expected'),
                                       (selection, 'ExpectedArtifact'),
                                       (artifacts, '_Scope')))
def test_initial_import_alias_must_join_its_actual_defining_object(monkeypatch, module, name):
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('inconsistent defining alias dispatched')

    # The inconsistent value is present BEFORE capture. Independent per-module
    # snapshots are individually coherent and cannot alone detect this mismatch.
    monkeypatch.setattr(module, name, foreign)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()
    assert calls == []


def test_activation_projection_is_not_a_live_owner_or_scope_verdict(monkeypatch):
    captured = origin.capture()
    owner = object.__new__(activation.GatewayActivationOwner)
    scope = activation._ActivationScope(*(None for _ in range(11)))
    owner._scope = scope
    monkeypatch.setattr(activation, '_ENTRY_OWNER', owner)
    monkeypatch.setattr(activation, '_ENTRY_CELL', (owner, scope))
    assert origin.current(captured) is captured  # Legitimate allocation changes values.
    assert activation.GatewayActivationOwner._retained_scope(owner) is scope
    # The projection is still current, but the ORIGINAL validator freshly refuses
    # a different live cell; its previous DATA result never authorizes this state.
    monkeypatch.setattr(activation, '_ENTRY_CELL', (owner, None))
    assert origin.current(captured) is captured
    with pytest.raises(activation.ActivationCaptureError):
        activation.GatewayActivationOwner._retained_scope(owner)


@pytest.mark.parametrize('key', ('_ENTRY_OWNER', '_ENTRY_CELL'))
def test_activation_projection_requires_live_keys_even_without_pinning_values(monkeypatch, key):
    captured = origin.capture()
    monkeypatch.delattr(activation, key)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)


@pytest.mark.parametrize('key', ('_ENTRY_OWNER', '_ENTRY_CELL'))
def test_expected_static_pair_cannot_be_replaced_with_an_excluded_live_key(key):
    packet = list(origin.capture())
    rows = list(packet[3])
    module, namespace, pairs = rows[3]
    rows[3] = (module, namespace, ((key, namespace[key]), *pairs[1:]))
    packet[3] = tuple(rows)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(tuple(packet))


@pytest.mark.parametrize('kind', ('owner', 'scope'))
def test_activation_class_dispatch_drift_refuses_before_foreign_getter(monkeypatch, kind):
    captured = origin.capture()
    calls = []

    def foreign(*args):
        calls.append(True)
        raise AssertionError('activation dispatch changed')

    selected = (activation.GatewayActivationOwner if kind == 'owner'
                else activation._ActivationScope)
    monkeypatch.setattr(selected, '__getattribute__', foreign, raising=False)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)
    assert calls == []


def test_activation_projection_does_not_allow_other_namespace_growth(monkeypatch):
    captured = origin.capture()
    monkeypatch.setattr(activation, '_synthetic_new_static_export', None, raising=False)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)


@pytest.mark.parametrize('module,name', (
    (artifacts, 'ExpectedArtifact'), (artifacts, 'ArtifactObservationError'),
    (artifacts, '_Descriptor'), (artifacts, '_NativeScopeRegistration'),
    (artifacts, '_NativeOpenAllocation'), (artifacts, '_NativeCloseAllocation'),
    (artifacts, '_NativeOpenedDescriptor'), (artifacts, '_Scope'),
    (package, 'RetainedPackageData'), (package, '_Scan'), (recipe, '_Recipe'),
))
def test_shared_retained_data_class_dispatch_cannot_change(monkeypatch, module, name):
    captured = origin.capture()
    calls = []

    def foreign(*args):
        calls.append(True)
        raise AssertionError('changed retained-data getter dispatched')

    monkeypatch.setattr(getattr(module, name), '__getattribute__', foreign, raising=False)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(captured)
    assert calls == []
