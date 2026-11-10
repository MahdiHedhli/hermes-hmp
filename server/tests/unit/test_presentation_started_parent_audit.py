"""Strict rooted parent entrypoint, before production selector activation."""
import pytest
from hmp_startup import link_factory_origin as origins
from . import test_presentation_entry_files as base


def test_started_parent_refuses_pre_entry_without_generic_fallback(monkeypatch):
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    packet = origins.capture()
    assert origins.current(packet) is packet
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.current_started(packet)


@pytest.mark.parametrize('fault', ('normal', 'parent_copy', 'record_copy', 'owner_invocation',
                                  'after_live_return', 'live_code', 'owner_class_after_return'))
def test_actual_started_parent_original_roots(tmp_path, monkeypatch, fault):
    marker = 'entry = GatewayEntryOwner.start()\n'
    assert base.SCRIPT.count(marker) == 1
    extra = '\nstarted_fault=' + repr(fault) + '\n' + r'''
from hmp_startup import gateway_entry as original_entry
from hmp_startup import link_factory_origin as parent_audit
from hmp_plugin import presentation_native_link as native_link
original=original_entry._ENTRY_ORIGIN
parent=tuple.__getitem__(original,10)
record=tuple.__getitem__(original,11)
assert parent[0][7] is record
assert parent_audit.current(parent) is parent
live_calls=[];foreign_calls=[];mutations=[]
root_witness=(original_entry._STARTED[5] is original and
              original_entry._STARTED[2] is original_entry._CELL and
              original_entry._CELL[1] is entry._scope)
original_scope=entry._scope
original_kind=type(entry)
original_started=original_entry._STARTED
original_code=native_link._engine_live_tail.__code__
selected=parent
if started_fault=='parent_copy':selected=tuple(list(parent))
elif started_fault=='record_copy':
    copied=tuple(list(record));env=(*parent[0][:7],copied)
    selected=(env,*parent[1:])
elif started_fault=='owner_invocation':entry._scope=original_scope._replace()
elif started_fault=='live_code':
    def foreign(*args,**kwargs):raise AssertionError('foreign live code ran')
    native_link._engine_live_tail.__code__=foreign.__code__
def observe(frame,event,value):
    if event=='call' and frame.f_code is original_code:
        live_calls.append((frame.f_locals.get('origin'),frame.f_locals.get('bound_layout')))
    if started_fault=='live_code' and event=='call' and frame.f_code is native_link._engine_live_tail.__code__:
        foreign_calls.append(True)
    if event=='return' and frame.f_code is original_code:
        if started_fault=='after_live_return':
            original_entry._STARTED=tuple(list(original_started))
            mutations.append('started_copy')
        elif started_fault=='owner_class_after_return':
            def trap(*args,**kwargs):
                foreign_calls.append(True)
                raise AssertionError('foreign owner descriptor/getter ran')
            class ChangedOwner(original_kind):
                __slots__=()
                __dict__=property(trap)
                __getattribute__=trap
            object.__setattr__(entry,'__class__',ChangedOwner)
            mutations.append('owner_class')
assert sys.getprofile() is None
sys.setprofile(observe)
refused=False;returned=None;error=None
try:
    returned=parent_audit.current_started(selected)
except RuntimeError as caught:
    refused=True;error=caught
finally:
    sys.setprofile(None)
    object.__setattr__(entry,'__class__',original_kind)
    entry._scope=original_scope
    original_entry._STARTED=original_started
    native_link._engine_live_tail.__code__=original_code
assert root_witness
if refused:assert type(error) is RuntimeError and error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
if started_fault=='normal':
    assert not refused and returned is parent and len(live_calls)==1
elif started_fault in ('after_live_return','owner_class_after_return'):
    assert refused and returned is None and len(live_calls)==1
else:assert refused and returned is None and live_calls==[]
if live_calls:assert live_calls[0][0] is record[0] and live_calls[0][1] is record[1]
assert foreign_calls==[]
assert mutations==(['started_copy'] if started_fault=='after_live_return' else
                   ['owner_class'] if started_fault=='owner_class_after_return' else [])
assert original_entry._ENTRY_ORIGIN is original and entry._scope is original_scope
'''
    script = base.SCRIPT.replace(marker, marker + extra, 1)
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, 'normal')
