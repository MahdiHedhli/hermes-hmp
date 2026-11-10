"""Local helper DATA controls; not early custody, audit reuse or native admission."""
import pytest

from hmp_startup import gateway_approval as approval

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


@pytest.mark.parametrize('owner,name', ((None, '_native_file_allocation_original'),
                                       ('ArtifactObservationError', '__init__')))
def test_identical_code_cannot_hide_a_different_execution_builtins_dictionary(
        monkeypatch, owner, name):
    import builtins
    from types import FunctionType

    selected = artifacts if owner is None else getattr(artifacts, owner)
    original = getattr(selected, name)
    namespace = original.__globals__
    canonical = namespace['__builtins__']
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('hidden execution builtin dispatched')

    hidden = dict(vars(builtins))
    hidden['super'] = foreign
    # Function.__builtins__ is fixed at creation, independently of the restored
    # globals entry. Code/globals/defaults/closure remain otherwise identical.
    namespace['__builtins__'] = hidden
    try:
        clone = FunctionType(original.__code__, namespace, original.__name__,
                             original.__defaults__, original.__closure__)
    finally:
        namespace['__builtins__'] = canonical
    clone.__kwdefaults__ = original.__kwdefaults__
    assert clone.__globals__ is namespace and clone.__code__ is original.__code__
    assert clone.__builtins__ is hidden and namespace['__builtins__'] is canonical
    monkeypatch.setattr(selected, name, clone)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()
    assert calls == []


@pytest.mark.parametrize('module', (package, artifacts))
def test_canonical_builtin_module_globals_keep_actual_function_dictionary(monkeypatch, module):
    import builtins

    monkeypatch.setattr(module, '__builtins__', builtins)
    captured = origin.capture()
    assert origin.current(captured) is captured
    assert all(row[0].__builtins__ is vars(builtins) for row in captured[5])


@pytest.mark.parametrize('owner,name', (
    ('GatewayApprovalOwner', '_retained_binding'), ('GatewayApprovalOwner', '_seal'),
    ('GatewayApprovalOwner', '_closed_custody'), (None, '_require'),
    (None, '_same_entry'), (None, '_api_state'), ('GatewayApprovalError', '__init__')))
def test_approval_validator_code_drift_refuses_without_dispatch(monkeypatch, owner, name):
    packet = origin.capture()
    namespace = approval if owner is None else getattr(approval, owner)
    target = getattr(namespace, name)

    def foreign(*args, **kwargs):
        raise AssertionError('approval replacement dispatched')

    class ForeignError(Exception):
        def __init__(self, *args, **kwargs):
            __class__  # Preserve the native constructor's class-cell shape.
            raise AssertionError('approval replacement constructor dispatched')

    code = ForeignError.__init__.__code__ if target.__closure__ else foreign.__code__
    assert len(code.co_freevars) == len(target.__code__.co_freevars)
    monkeypatch.setattr(target, '__code__', code)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(packet)


def test_approval_projection_does_not_authorize_changed_live_state(monkeypatch):
    packet = origin.capture()
    for key in ('_OWNER', '_CELL', '_ROOT', '_FACT'):
        monkeypatch.setattr(approval, key, object())
    assert origin.current(packet) is packet
    # DATA currentness cannot authorize even an exact-class owner allocation.
    owner = object.__new__(approval.GatewayApprovalOwner)
    with pytest.raises(approval.GatewayApprovalError):
        approval.GatewayApprovalOwner._retained_binding(owner)


@pytest.mark.parametrize('key', ('_OWNER', '_CELL', '_ROOT', '_FACT'))
def test_approval_projection_requires_all_live_keys(monkeypatch, key):
    packet = origin.capture()
    monkeypatch.delattr(approval, key)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(packet)


@pytest.mark.parametrize('key', ('_OWNER', '_CELL', '_ROOT', '_FACT'))
def test_approval_static_projection_cannot_include_excluded_live_key(key):
    packet = list(origin.capture())
    rows = list(packet[3])
    module, namespace, pairs = rows[5]
    rows[5] = (module, namespace, ((key, namespace[key]), *pairs[1:]))
    packet[3] = tuple(rows)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(tuple(packet))


@pytest.mark.parametrize('name', ('GatewayActivationOwner', '_LATE_MODULES', 'ExpectedArtifact',
    '_Scope', '_descriptor_closed_in_scope', '_OperatorFileReceipt', '_ReadEffect'))
def test_approval_imports_join_original_defining_objects(monkeypatch, name):
    monkeypatch.setattr(approval, name, object())
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()


@pytest.mark.parametrize('owner,name', (('GatewayEntryOwner', '_retained_binding'),
    (None, '_native_file_ledger_shape'), (None, '_require'), ('GatewayEntryError', '__init__')))
def test_entry_validator_code_drift_refuses_without_dispatch(monkeypatch, owner, name):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    target = getattr(entry if owner is None else getattr(entry, owner), name)

    def foreign(*args, **kwargs):
        raise AssertionError('entry replacement dispatched')

    class ForeignError(Exception):
        def __init__(self, *args, **kwargs):
            __class__
            raise AssertionError('entry replacement constructor dispatched')

    code = ForeignError.__init__.__code__ if target.__closure__ else foreign.__code__
    assert len(code.co_freevars) == len(target.__code__.co_freevars)
    monkeypatch.setattr(target, '__code__', code)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(packet)


@pytest.mark.parametrize('name', ('GatewayEntryOwner', 'GatewayEntryError', '_Invocation',
    '_EntryOrigin', 'EntryStartupData', '_InterpreterOrigin', 'InterpreterStartupData',
    '_NativeIOOrigin', '_NativeFileLineage', '_NativeFileLedger', '_NativeFilePhase'))
def test_entry_class_dispatch_drift_refuses_without_getter(monkeypatch, name):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    calls = []

    def foreign(*args):
        calls.append(True)
        raise AssertionError('entry field getter dispatched')

    monkeypatch.setattr(getattr(entry, name), '__getattribute__', foreign, raising=False)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(packet)
    assert calls == []


@pytest.mark.parametrize('key', ('_OWNER', '_CELL', '_STARTED', '_START_ATTEMPTED', '_ENTRY_ORIGIN'))
def test_entry_projection_requires_all_live_keys(monkeypatch, key):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    monkeypatch.delattr(entry, key)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(packet)


@pytest.mark.parametrize('key', ('_OWNER', '_CELL', '_STARTED', '_START_ATTEMPTED', '_ENTRY_ORIGIN'))
def test_entry_static_projection_cannot_include_live_key(key):
    packet = list(origin.capture())
    rows = list(packet[3])
    module, namespace, pairs = rows[6]
    rows[6] = (module, namespace, ((key, namespace[key]), *pairs[1:]))
    packet[3] = tuple(rows)
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.current(tuple(packet))


def test_entry_projection_does_not_authorize_changed_live_state(monkeypatch):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    for key in ('_OWNER', '_CELL', '_STARTED', '_START_ATTEMPTED', '_ENTRY_ORIGIN'):
        monkeypatch.setattr(entry, key, object())
    assert origin.current(packet) is packet
    owner = object.__new__(entry.GatewayEntryOwner)
    with pytest.raises(entry.GatewayEntryError):
        entry.GatewayEntryOwner._retained_binding(owner)


@pytest.mark.parametrize('replacement', (None, object()))
def test_entry_projection_cannot_authorize_a_changed_origin(monkeypatch, replacement):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    original = entry._ENTRY_ORIGIN
    assert entry._origin_current(original) is original
    monkeypatch.setattr(entry, '_ENTRY_ORIGIN', replacement)
    assert origin.current(packet) is packet
    with pytest.raises(entry.GatewayEntryError):
        entry._origin_current(original)


def test_entry_projection_cannot_reopen_start_attempt(monkeypatch):
    from hmp_startup import gateway_entry as entry
    packet = origin.capture()
    assert entry._OWNER is None and entry._CELL is None and entry._STARTED is None
    monkeypatch.setattr(entry, '_START_ATTEMPTED', True)
    assert origin.current(packet) is packet
    with pytest.raises(entry.GatewayEntryError):
        entry.GatewayEntryOwner.start()
    assert entry._OWNER is None and entry._CELL is None and entry._STARTED is None
    assert entry._START_ATTEMPTED is True


@pytest.mark.parametrize('module,name', ((approval, 'GatewayEntryOwner'),))
def test_approval_entry_alias_cannot_nominate_an_independent_owner(monkeypatch, module, name):
    monkeypatch.setattr(module, name, object())
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()


def test_entry_activation_alias_joins_original_owner(monkeypatch):
    from hmp_startup import gateway_entry as entry
    monkeypatch.setattr(entry, 'GatewayActivationOwner', object())
    with pytest.raises(origin.RetainedBindingOriginError):
        origin.capture()


@pytest.mark.parametrize('current', (False, True))
def test_retained_approval_validation_does_not_reenter_import_machinery(monkeypatch, current):
    import builtins

    original_import = builtins.__import__
    attempted = []

    def guarded_import(name, *args, **kwargs):
        if name == 'hmp_startup.gateway_approval':
            attempted.append(name)
            raise AssertionError('retained validator reentered import machinery')
        return original_import(name, *args, **kwargs)

    owner = object.__new__(approval.GatewayApprovalOwner)
    source = selection._ApprovedSelectionSource(owner, ())
    monkeypatch.setattr(builtins, '__import__', guarded_import)
    with pytest.raises(approval.GatewayApprovalError):
        selection._approval_binding(source, current)
    assert attempted == []


@pytest.mark.parametrize('fault', ('none', 'foreign', 'missing'))
def test_static_approval_alias_refuses_initial_incoherence(monkeypatch, fault):
    if fault == 'missing':monkeypatch.delattr(selection, '_APPROVAL_OWNER_TYPE')
    else:monkeypatch.setattr(selection, '_APPROVAL_OWNER_TYPE', None if fault == 'none' else object())
    with pytest.raises(origin.RetainedBindingOriginError):origin.capture()


@pytest.mark.parametrize('fault', ('none', 'foreign', 'missing'))
def test_static_approval_alias_refuses_late_drift(monkeypatch, fault):
    packet = origin.capture()
    if fault == 'missing':monkeypatch.delattr(selection, '_APPROVAL_OWNER_TYPE')
    else:monkeypatch.setattr(selection, '_APPROVAL_OWNER_TYPE', None if fault == 'none' else object())
    with pytest.raises(origin.RetainedBindingOriginError):origin.current(packet)
