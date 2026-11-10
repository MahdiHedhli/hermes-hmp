"""Early-origin DATA controls, not entry/lineage or native admission tests."""
import sys

import pytest

from hmp_startup import gateway_approval as approval

from hmp_plugin import presentation_link_path_policy as policy
from hmp_startup import link_factory_origin as origins


@pytest.fixture
def captured(monkeypatch):
    # An isolated source-test attempt, never production reset/recovery behavior.
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    return origins.capture()


def test_actual_capture_return_rejoins_without_calling_policy(captured):
    assert origins.current(captured) is captured
    assert origins.factory(captured) is policy._new_policy
    assert tuple(row[0] for row in captured[1]) == (
        'hmp_startup.link_factory_origin', 'hmp_plugin.presentation_link_path_policy',
        'hmp_plugin.presentation_startup_artifacts', 'hmp_startup.runtime_files')
    assert all(row[1].__closure__ is None for row in captured[3])


def test_capture_is_one_attempt_and_cannot_recover_a_lost_return(captured):
    del captured  # no original-object receipt is reconstructed from a global slot
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.capture()


@pytest.mark.parametrize('fault', (
    'factory_export', 'parts_export', 'need_code', 'current_export',
    'pin_helper_export', 'validator_default', 'validator_extra_default',
    'policy_module', 'native_module', 'policy_dispatch', 'policy_member',
    'native_type_export', 'constructor_globals', 'capture_marker', 'helper_projection_schema',
))
def test_changed_original_bindings_refuse_before_foreign_calls(captured, monkeypatch, fault):
    from hmp_startup import runtime_files

    calls = []
    held_factory = origins.factory

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign origin dependency invoked')

    def changed_code(*args, **kwargs):
        raise AssertionError('changed origin dependency code invoked')

    if fault == 'factory_export':
        monkeypatch.setattr(policy, '_new_policy', foreign)
    elif fault == 'parts_export':
        monkeypatch.setattr(policy, '_parts', foreign)
    elif fault == 'need_code':
        monkeypatch.setattr(policy._need, '__code__', changed_code.__code__)
    elif fault == 'current_export':
        monkeypatch.setattr(origins, 'current', foreign)
    elif fault == 'pin_helper_export':
        monkeypatch.setattr(origins, '_pin_type', foreign)
    elif fault == 'validator_default':
        monkeypatch.setitem(origins.current.__kwdefaults__, '_any', foreign)
    elif fault == 'validator_extra_default':
        monkeypatch.setitem(origins.current.__kwdefaults__, 'foreign', foreign)
    elif fault == 'policy_module':
        monkeypatch.setitem(sys.modules, 'hmp_plugin.presentation_link_path_policy', object())
    elif fault == 'native_module':
        monkeypatch.setitem(sys.modules, 'hmp_startup.runtime_files', object())
    elif fault == 'policy_dispatch':
        monkeypatch.setattr(policy._LinkPathPolicy, '__getattribute__', foreign, raising=False)
    elif fault == 'policy_member':
        monkeypatch.setattr(policy._LinkPathPolicy, 'plan', property(foreign))
    elif fault == 'native_type_export':
        monkeypatch.setattr(runtime_files, 'LinkHop', object())
    elif fault == 'constructor_globals':
        monkeypatch.setitem(policy._LinkPathPolicy.__new__.__globals__, '_tuple_new', foreign)
    elif fault == 'capture_marker':
        monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    elif fault == 'helper_projection_schema':
        from hmp_startup import retained_binding_origin
        monkeypatch.setattr(retained_binding_origin, '_LIVE_GLOBALS', ((), (), (), ()))
    else:
        raise AssertionError('unhandled causal fault')
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        held_factory(captured)
    assert calls == []


def test_foreign_namespace_key_refuses_without_hash_or_equality(captured, monkeypatch):
    calls = []

    class ForeignKey:
        def __hash__(self):
            calls.append('hash')
            return 192837465
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign key equality invoked')

    key = ForeignKey()
    monkeypatch.setitem(vars(policy), key, object())
    before = tuple(calls)
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.factory(captured)
    assert tuple(calls) == before


@pytest.mark.parametrize('field', range(5))
def test_foreign_origin_fields_cannot_select_a_helper(captured, field):
    class Foreign:
        def __getattribute__(self, name):
            raise AssertionError('foreign getter invoked')
        def __iter__(self):
            raise AssertionError('foreign iteration invoked')

    changed = list(captured)
    changed[field] = Foreign()
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.factory(tuple(changed))


def test_data_copy_is_not_misreported_as_independent_entry_ownership(captured):
    copied = tuple(list(captured))
    assert copied is not captured
    # The generic DATA seal has no entry owner to distinguish these. Actual LP2
    # entry/lineage integration MUST compare the independently held original
    # capture return by identity. No admission or receipt claim is made here.
    assert origins.current(copied) is copied


@pytest.mark.parametrize('fault', ('export', 'code', 'validator_default'))
def test_initialization_import_cannot_nominate_capture_helpers(monkeypatch, fault):
    import builtins

    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    actual_import = builtins.__import__
    reached = []
    foreign_calls = []

    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError('foreign capture dependency invoked')

    def forbidden_code(*args, **kwargs):
        raise AssertionError('changed capture code invoked')

    def observed_import(name, globals=None, locals=None, fromlist=(), level=0):
        result = actual_import(name, globals, locals, fromlist, level)
        if (name == 'hmp_plugin' and 'presentation_link_path_policy' in (fromlist or ())
                and not reached):
            reached.append(True)
            if fault == 'export':
                monkeypatch.setattr(origins, '_pin_type', foreign)
            elif fault == 'code':
                monkeypatch.setattr(origins._pin_type, '__code__', forbidden_code.__code__)
            else:
                monkeypatch.setitem(origins.current.__kwdefaults__, '_any', foreign)
        return result

    monkeypatch.setattr(builtins, '__import__', observed_import)
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.capture()
    assert reached == [True] and foreign_calls == []
    assert origins._CAPTURE_STARTED is True
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.capture()  # no second initialization attempt after uncertainty


def test_retained_helper_module_fenced_before_namespace_inspection(monkeypatch):
    import builtins
    import hmp_startup

    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    actual_import = builtins.__import__
    reached, calls = [], []

    class Foreign:
        __slots__ = ()

        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign module namespace inspected')

    def observed_import(name, globals=None, locals=None, fromlist=(), level=0):
        result = actual_import(name, globals, locals, fromlist, level)
        if name == 'hmp_startup' and 'retained_binding_origin' in (fromlist or ()):
            monkeypatch.setattr(hmp_startup, 'retained_binding_origin', Foreign())
            reached.append(True)
        return result

    monkeypatch.setattr(builtins, '__import__', observed_import)
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.capture()
    assert reached == [True] and calls == []
    assert origins._CAPTURE_STARTED is True


@pytest.mark.parametrize('name', ('_descriptor_closed_in_scope', '_native_file_allocation_original'))
def test_artifact_code_held_before_later_engine_capture_cannot_be_renominated(monkeypatch, name):
    from hmp_plugin import presentation_native_link as engine
    from hmp_plugin import presentation_startup_artifacts as artifacts
    from hmp_startup import retained_binding_origin as helpers

    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    target = getattr(artifacts, name)
    original_code = target.__code__
    helper_capture_code, engine_capture_code = helpers.capture.__code__, engine._capture_engine.__code__
    parent_capture_code = origins.capture.__code__
    reached, held_original, engine_adopted, foreign_calls = [], [], [], []

    def forbidden_code(*args, **kwargs):
        raise AssertionError('renominated artifact helper executed')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is forbidden_code.__code__:
            foreign_calls.append(True)
        if event != 'return' or frame.f_back.f_code is not parent_capture_code:
            return
        if frame.f_code is helper_capture_code and not reached:
            held_original.append(any(row[0] is target and row[1] is original_code
                                     for row in value[5]))
            monkeypatch.setattr(target, '__code__', forbidden_code.__code__)
            reached.append(True)
        elif frame.f_code is engine_capture_code and reached:
            # Prove the later real engine capture accepted the changed code as
            # its own candidate. Only the earlier held record distinguishes it.
            artifact = next(row for row in value[4][3]
                            if row[0] == 'hmp_plugin.presentation_startup_artifacts')
            engine_adopted.append(any(row[0] is target and row[1] is forbidden_code.__code__
                                      for row in artifact[5]))

    previous = sys.getprofile()
    assert previous is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.capture()
    finally:
        sys.setprofile(previous)
    assert reached == [True] and held_original == [True] and engine_adopted == [True]
    assert foreign_calls == [] and origins._CAPTURE_STARTED is True


@pytest.mark.parametrize('name', ('bool', 'int', 'list', 'bytes', 'bytearray', 'sum', 'ord', 'super'))
def test_original_execution_builtin_value_refuses_replacement_before_dispatch(captured, name):
    import builtins

    calls = []
    original = getattr(builtins, name)
    assign = setattr
    refused = False

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('changed execution builtin dispatched')

    # Restore even when validation fails; pytest/stdlib itself needs these names.
    assign(builtins, name, foreign)
    try:
        try:
            origins.current(captured)
        except RuntimeError:
            refused = True
    finally:
        assign(builtins, name, original)
    assert refused and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
@pytest.mark.parametrize('name', ('sum', 'ord'))
def test_execution_builtin_is_rejoined_after_checker_return(captured, boundary, name):
    import builtins

    helper = captured[0][6]
    checker_code = (helper[3][1][2] if boundary == 'component' else
                    next(row[2] for row in captured[0][4][2] if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    original = getattr(builtins, name)
    assign = setattr
    observed, calls = [], []
    refused = False

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('late execution builtin dispatched')

    def observe(frame, event, value):
        if (event == 'return' and frame.f_code is checker_code
                and frame.f_back.f_code is parent_code and not observed):
            assign(builtins, name, foreign)
            observed.append(True)

    previous = sys.getprofile()
    assert previous is None
    sys.setprofile(observe)
    try:
        try:
            origins.current(captured)
        except RuntimeError:
            refused = True
    finally:
        sys.setprofile(previous)
        assign(builtins, name, original)
    assert observed == [True] and refused and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
@pytest.mark.parametrize('fault', ('export', 'code'))
def test_selected_helper_state_rejoined_after_final_checker_return(
        captured, monkeypatch, boundary, fault):
    from hmp_plugin import presentation_gateway_package as package

    helper = captured[0][6]
    checker_code = (helper[3][1][2] if boundary == 'component' else
                    next(row[2] for row in captured[0][4][2]
                         if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    target = package.GatewayPackageOwner._retained_binding
    observed, calls = [], []

    def foreign(*args):
        calls.append(True)
        raise AssertionError('foreign retained helper executed')

    def forbidden_code(*args):
        raise AssertionError('changed retained helper code executed')

    def profile(frame, event, value):
        if (event == 'return' and frame.f_code is checker_code
                and frame.f_back.f_code is parent_code and not observed):
            if fault == 'export':
                monkeypatch.setattr(package.GatewayPackageOwner, '_retained_binding', foreign)
            else:
                monkeypatch.setattr(target, '__code__', forbidden_code.__code__)
            observed.append(True)

    prior = sys.getprofile()
    assert prior is None
    sys.setprofile(profile)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.current(captured)
    finally:
        sys.setprofile(prior)
    assert observed == [True] and calls == []


@pytest.mark.parametrize('fault', ('capture_export', 'current_export', 'capture_code',
                                  'current_code', 'capture_defaults', 'current_keywords',
                                  'roles', 'error_constructor', 'packet'))
def test_retained_component_bootstrap_refuses_before_dispatch(captured, monkeypatch, fault):
    helper = captured[0][6]
    component = helper[0]
    calls = []

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign component executed')

    def forbidden_code(*args, **kwargs):
        raise AssertionError('changed component code executed')

    changed = captured
    if fault == 'capture_export':
        monkeypatch.setattr(component, 'capture', foreign)
    elif fault == 'current_export':
        monkeypatch.setattr(component, 'current', foreign)
    elif fault in ('capture_code', 'current_code'):
        target = component.capture if fault == 'capture_code' else component.current
        monkeypatch.setattr(target, '__code__', forbidden_code.__code__)
    elif fault == 'capture_defaults':
        monkeypatch.setattr(component.capture, '__defaults__', (object(),))
    elif fault == 'current_keywords':
        monkeypatch.setattr(component.current, '__kwdefaults__', {'synthetic': foreign})
    elif fault == 'roles':
        monkeypatch.setattr(component, '_FUNCTIONS', ())
    elif fault == 'error_constructor':
        monkeypatch.setattr(component.RetainedBindingOriginError, '__init__', foreign,
                            raising=False)
    else:
        copied = (*helper[:6], object())
        environment = (*captured[0][:6], copied)
        changed = (environment, *captured[1:])
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.current(changed)
    assert calls == []


def test_component_builtin_all_refuses_before_dispatch(captured):
    import builtins

    calls = []
    original = builtins.all

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign builtin all executed')

    refused = False
    builtins.all = foreign
    try:
        try:
            origins.current(captured)
        except RuntimeError:
            refused = True
    finally:
        builtins.all = original
    assert refused and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
@pytest.mark.parametrize('method', ('_retained_binding', '_seal'))
def test_approval_helper_code_rejoined_after_later_callbacks(captured, monkeypatch, boundary, method):
    from hmp_startup import gateway_approval as approval

    helper = captured[0][6]
    boundary_code = (helper[3][1][2] if boundary == 'component' else
                     next(row[2] for row in captured[0][4][2]
                          if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    target = getattr(approval.GatewayApprovalOwner, method)
    observed, calls = [], []

    def foreign(*args, **kwargs):
        raise AssertionError('changed approval validator executed')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is foreign.__code__:
            calls.append(True)
        if (event == 'return' and frame.f_code is boundary_code
                and frame.f_back.f_code is parent_code and not observed):
            monkeypatch.setattr(target, '__code__', foreign.__code__)
            observed.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.current(captured)
    finally:
        sys.setprofile(None)
    assert observed == [True] and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
@pytest.mark.parametrize('owner,method', (('GatewayEntryOwner', '_retained_binding'),
                                        (None, '_native_file_ledger_shape')))
def test_entry_helper_code_rejoined_after_later_callbacks(captured, monkeypatch, boundary, owner, method):
    from hmp_startup import gateway_entry as entry

    helper = captured[0][6]
    boundary_code = (helper[3][1][2] if boundary == 'component' else
                     next(row[2] for row in captured[0][4][2]
                          if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    target = getattr(entry if owner is None else getattr(entry, owner), method)
    observed, calls = [], []

    def foreign(*args, **kwargs):
        raise AssertionError('changed entry validator executed')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is foreign.__code__:
            calls.append(True)
        if (event == 'return' and frame.f_code is boundary_code
                and frame.f_back.f_code is parent_code and not observed):
            monkeypatch.setattr(target, '__code__', foreign.__code__)
            observed.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.current(captured)
    finally:
        sys.setprofile(None)
    assert observed == [True] and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
def test_prebound_approval_alias_rejoined_after_later_callbacks(captured, monkeypatch, boundary):
    from hmp_plugin import presentation_startup_selection as selection

    helper = captured[0][6]
    boundary_code = (helper[3][1][2] if boundary == 'component' else
                     next(row[2] for row in captured[0][4][2]
                          if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    observed = []

    def observe(frame, event, value):
        if (event == 'return' and frame.f_code is boundary_code
                and frame.f_back.f_code is parent_code and not observed):
            monkeypatch.setattr(selection, '_APPROVAL_OWNER_TYPE', object())
            observed.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.current(captured)
    finally:sys.setprofile(None)
    assert observed == [True]


@pytest.mark.parametrize('name', ('OperatorApprovalPath', '_OperatorFileReceipt', '_ReadEffect'))
def test_shared_record_dispatch_held_before_later_engine_capture(monkeypatch, name):
    from hmp_plugin import presentation_native_link as engine
    from hmp_plugin import presentation_startup_artifacts as artifacts
    from hmp_startup import retained_binding_origin as helpers

    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    target = getattr(artifacts, name)
    helper_code, engine_code = helpers.capture.__code__, engine._capture_engine.__code__
    parent_code = origins.capture.__code__
    reached, held_original, engine_returned, calls = [], [], [], []

    def foreign(*args):raise AssertionError('changed shared record getter executed')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is foreign.__code__:calls.append(True)
        if event != 'return' or frame.f_back.f_code is not parent_code:return
        if frame.f_code is helper_code and not reached:
            held_original.append(any(row[0] is target for row in value[4]))
            monkeypatch.setattr(target, '__getattribute__', foreign, raising=False)
            reached.append(True)
        elif frame.f_code is engine_code and reached:engine_returned.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.capture()
    finally:sys.setprofile(None)
    assert reached == [True] and held_original == [True] and engine_returned == [True]
    assert calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
@pytest.mark.parametrize('name', ('OperatorApprovalPath', '_OperatorFileReceipt', '_ReadEffect'))
def test_shared_record_dispatch_rejoined_after_later_callbacks(captured, monkeypatch, boundary, name):
    from hmp_plugin import presentation_startup_artifacts as artifacts

    helper = captured[0][6]
    boundary_code = (helper[3][1][2] if boundary == 'component' else
                     next(row[2] for row in captured[0][4][2]
                          if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    observed, calls = [], []

    def foreign(*args):raise AssertionError('changed shared getter executed')

    def observe(frame, event, value):
        if event == 'call' and frame.f_code is foreign.__code__:calls.append(True)
        if (event == 'return' and frame.f_code is boundary_code
                and frame.f_back.f_code is parent_code and not observed):
            monkeypatch.setattr(getattr(artifacts, name), '__getattribute__', foreign, raising=False)
            observed.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        expected_error = artifacts.ArtifactObservationError if boundary == 'component' else RuntimeError
        expected_args = ('BI1_STARTUP_ARTIFACTS_REFUSED',) if boundary == 'component' else (
            'BI1_LINK_FACTORY_ORIGIN_REFUSED',)
        with pytest.raises(expected_error) as caught:
            origins.current(captured)
        assert type(caught.value) is expected_error and caught.value.args == expected_args
    finally:sys.setprofile(None)
    assert observed == [True] and calls == []


@pytest.mark.parametrize('boundary', ('component', 'engine'))
def test_native_spec_accessor_default_rejoined_after_callbacks(captured, monkeypatch, boundary):
    from hmp_startup import gateway_approval as approval

    helper = captured[0][6]
    boundary_code = (helper[3][1][2] if boundary == 'component' else
                     next(row[2] for row in captured[0][4][2]
                          if row[0] == '_engine_origin_tail'))
    parent_code = origins.current.__code__
    observed, calls = [], []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign native spec accessor dispatched')

    replacement = Foreign()

    def observe(frame, event, value):
        if (event == 'return' and frame.f_code is boundary_code
                and frame.f_back.f_code is parent_code and not observed):
            monkeypatch.setitem(approval._api_state.__kwdefaults__, '_spec_dict', replacement)
            observed.append(True)

    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
            origins.current(captured)
    finally:sys.setprofile(None)
    assert observed == [True] and calls == []
