"""Entry capture/lineage joins; not complete native link/image admission."""
import builtins

import pytest

from hmp_startup import gateway_entry as entry
from hmp_startup import link_factory_origin as origins


def test_actual_module_entry_keeps_the_capture_return():
    actual = entry._ENTRY_ORIGIN
    assert entry._origin_current(actual) is actual
    captured = tuple.__getitem__(actual, 10)
    assert entry._link_policy_current(captured) is captured


@pytest.mark.parametrize('fault', (
    'field_copy', 'need_alias', 'guard_alias', 'entry_dispatch',
    'policy_factory_export', 'entry_slot',
))
def test_entry_constructor_refuses_changed_originals_before_publication(monkeypatch, fault):
    from hmp_plugin import presentation_link_path_policy as policy

    # Isolated constructor-return instrumentation, not a production retry path.
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    original_entry = entry._ENTRY_ORIGIN
    kind, actual_new = entry._EntryOrigin, entry._EntryOrigin.__new__
    constructor_calls, foreign_calls = [], []
    foreign_slot = object()

    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError('foreign entry dependency invoked')

    def changed(cls, *values):
        constructor_calls.append(True)
        if fault == 'field_copy':
            values = (*values[:10], tuple(list(values[10])))
        result = actual_new(cls, *values)
        if fault == 'need_alias':
            monkeypatch.setattr(entry, '_require', foreign)
        elif fault == 'guard_alias':
            monkeypatch.setattr(entry, '_link_policy_current', foreign)
        elif fault == 'entry_dispatch':
            monkeypatch.setattr(kind, '__getattribute__', foreign, raising=False)
        elif fault == 'policy_factory_export':
            monkeypatch.setattr(policy, '_new_policy', foreign)
        elif fault == 'entry_slot':
            monkeypatch.setattr(entry, '_ENTRY_ORIGIN', foreign_slot)
        return result

    monkeypatch.setattr(kind, '__new__', staticmethod(changed))
    expected_error = entry.GatewayEntryError if fault == 'field_copy' else RuntimeError
    with pytest.raises(expected_error):
        entry._capture_origin()
    assert constructor_calls == [True] and foreign_calls == []
    assert entry._ENTRY_ORIGIN is (foreign_slot if fault == 'entry_slot' else original_entry)
    assert origins._CAPTURE_STARTED is True


@pytest.mark.parametrize('fault', ('need_alias', 'start_code', 'entry_member'))
def test_initialization_import_rejoins_entry_before_capture(monkeypatch, fault):
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    actual_import = builtins.__import__
    reached, foreign_calls = [], []

    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError('foreign early entry dependency invoked')

    def forbidden_code(*args, **kwargs):
        raise AssertionError('changed early entry code invoked')

    def observed_import(name, globals=None, locals=None, fromlist=(), level=0):
        result = actual_import(name, globals, locals, fromlist, level)
        if (globals is not None and globals.get('__name__') == entry.__name__
                and 'link_factory_origin' in (fromlist or ()) and not reached):
            reached.append(True)
            if fault == 'need_alias':
                monkeypatch.setattr(entry, '_require', foreign)
            elif fault == 'start_code':
                monkeypatch.setattr(entry.GatewayEntryOwner.start.__func__, '__code__',
                                    forbidden_code.__code__)
            else:
                monkeypatch.setattr(entry._EntryOrigin, 'link_policy', property(foreign))
        return result

    monkeypatch.setattr(builtins, '__import__', observed_import)
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        entry._capture_origin()
    assert reached == [True] and foreign_calls == []
    assert origins._CAPTURE_STARTED is False  # refused before its capture helper


def test_isolated_real_entry_lineage_retains_exact_early_capture(tmp_path, monkeypatch):
    from . import test_presentation_entry_files as base

    marker = 'entry = GatewayEntryOwner.start()\n'
    assert base.SCRIPT.count(marker) == 1
    script = base.SCRIPT.replace(marker, marker + r'''
from hmp_startup import gateway_entry as original_entry_module
actual_lineage = GatewayEntryOwner._native_file_lineage(entry)
actual_capture = tuple.__getitem__(original_entry_module._ENTRY_ORIGIN, 10)
assert tuple.__getitem__(actual_lineage, 4) is actual_capture
assert original_entry_module._link_policy_current(actual_capture) is actual_capture
assert original_entry_module._origin_current(original_entry_module._ENTRY_ORIGIN) is original_entry_module._ENTRY_ORIGIN
''', 1)
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, 'normal')


def test_old_lineage_constructor_keeps_nonadmitting_default():
    # Compatibility DATA only. No original entry/ledger or link grant is minted.
    lineage = entry._NativeFileLineage(object(), object(), (), object())
    assert tuple.__getitem__(lineage, 4) is None


@pytest.mark.parametrize('fault', (
    'origin_copy', 'link_copy', 'need_alias', 'owner_slot', 'raising', 'reentrant', 'tuple_new',
))
def test_owner_constructor_cannot_replace_original_entry_or_replay(monkeypatch, fault):
    # Isolated pre-bootstrap fault controls. Never enter the real interpreter/
    # bootstrap path from this pytest process; the normal path has its own child.
    monkeypatch.setattr(entry, '_OWNER', None)
    monkeypatch.setattr(entry, '_CELL', None)
    monkeypatch.setattr(entry, '_STARTED', None)
    monkeypatch.setattr(entry, '_START_ATTEMPTED', False)
    actual_origin, actual_need = entry._ENTRY_ORIGIN, entry._require
    constructor_calls, native_calls, foreign_calls, replacements = [], [], [], []
    foreign_owner = object()

    def forbidden_native(*args, **kwargs):
        native_calls.append(True)
        raise AssertionError('pre-bootstrap native observation reached')

    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError('foreign entry helper invoked')

    def changed(cls):
        constructor_calls.append(True)
        owner = object.__new__(cls)
        if fault in ('origin_copy', 'link_copy'):
            changed_origin = (actual_origin._replace() if fault == 'origin_copy'
                              else actual_origin._replace(
                                  link_policy=tuple(list(tuple.__getitem__(actual_origin, 10)))))
            replacements.append(changed_origin)
            monkeypatch.setattr(entry, '_ENTRY_ORIGIN', changed_origin)
        elif fault == 'need_alias':
            monkeypatch.setattr(entry, '_require', foreign)
        elif fault == 'owner_slot':
            monkeypatch.setattr(entry, '_OWNER', foreign_owner)
        elif fault == 'raising':
            raise RuntimeError('synthetic owner return lost')
        elif fault == 'tuple_new':
            monkeypatch.setitem(entry._NativeFileLineage.__new__.__globals__, '_tuple_new', foreign)
        else:
            with pytest.raises(entry.GatewayEntryError):
                entry.GatewayEntryOwner.start()
            raise RuntimeError('synthetic outer constructor stopped after reentry')
        return owner

    monkeypatch.setattr(entry, '_interpreter', forbidden_native)
    monkeypatch.setattr(entry.GatewayEntryOwner, '__new__', staticmethod(changed), raising=False)
    with pytest.raises(RuntimeError):
        entry.GatewayEntryOwner.start()
    assert constructor_calls == [True] and native_calls == [] and foreign_calls == []
    assert entry._START_ATTEMPTED is True
    assert entry._OWNER is (foreign_owner if fault == 'owner_slot' else None)
    assert entry._ENTRY_ORIGIN is (replacements[0] if replacements else actual_origin)
    # Restore only the deliberately foreign fixture slots; the implementation
    # has not overwritten them. Its actual attempt flag must still forbid replay.
    monkeypatch.setattr(entry, '_require', actual_need)
    monkeypatch.setattr(entry, '_OWNER', None)
    monkeypatch.setattr(entry, '_ENTRY_ORIGIN', actual_origin)
    with pytest.raises(entry.GatewayEntryError):
        entry.GatewayEntryOwner.start()
    assert constructor_calls == [True] and native_calls == [] and foreign_calls == []
