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


def test_root_first_owner_namespace_fence_precedes_descriptor_lookup(tmp_path, monkeypatch):
    marker = 'entry = GatewayEntryOwner.start()\n'
    extra = r'''
import gc
from hmp_startup import gateway_entry as original_entry
from hmp_startup import retained_binding_origin as selected_helpers
from hmp_startup import link_factory_origin as parent_audit
parent=tuple.__getitem__(original_entry._ENTRY_ORIGIN,10)
kind=type(entry)
raw=[v for v in gc.get_referents(vars(kind)) if type(v) is dict]
assert len(raw)==1
raw=raw[0];snapshot=dict(raw);calls=[];live=[];active=False
class Collision:
    def __hash__(self):
        if active:calls.append('hash')
        return hash('__dict__')
    def __eq__(self,other):
        if active:calls.append('eq')
        return False
key=Collision()
raw.pop('__dict__');raw[key]=None
live_code=selected_helpers.current_live.__code__
def observe(frame,event,value):
    if event=='call' and frame.f_code is live_code:live.append(True)
assert sys.getprofile() is None
sys.setprofile(observe);active=True;error=None
try:parent_audit.current_started(parent)
except RuntimeError as caught:error=caught
finally:
    active=False;sys.setprofile(None)
    # No hashing/equality of the foreign key while restoring the original class.
    raw.clear();raw.update(snapshot)
assert type(error) is RuntimeError and error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
assert calls==[] and live==[],(calls,live)
'''
    monkeypatch.setattr(base, 'SCRIPT', base.SCRIPT.replace(marker, marker+extra, 1))
    base.test_actual_entry_and_wrapper_files(tmp_path, 'normal')


@pytest.mark.parametrize('fault', ('modules','classes','module_row','module_object',
                                  'module_namespace','class_row','class_kind','entry_kind'))
def test_malformed_pre_live_root_data_refuses_without_protocols(tmp_path, monkeypatch, fault):
    marker='entry = GatewayEntryOwner.start()\n'
    extra='\nroot_fault='+repr(fault)+'\n'+r'''
from hmp_startup import gateway_entry as original_entry
from hmp_startup import retained_binding_origin as selected_helpers
from hmp_startup import link_factory_origin as parent_audit
parent=tuple.__getitem__(original_entry._ENTRY_ORIGIN,10)
assert parent_audit.current_started(parent) is parent
calls=[];live=[]
class Foreign:
    def __getattribute__(self,name):calls.append('get');raise AssertionError('foreign getter')
    def __iter__(self):calls.append('iter');raise AssertionError('foreign iterator')
    def __len__(self):calls.append('len');raise AssertionError('foreign length')
    def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
    def __hash__(self):calls.append('hash');raise AssertionError('foreign hash')
helper=parent[0][6];packet=list(helper[6])
if root_fault=='modules':packet[3]=Foreign()
elif root_fault=='classes':packet[4]=Foreign()
elif root_fault.startswith('module_'):
    rows=list(packet[3]);row=list(rows[6])
    if root_fault=='module_row':rows[6]=Foreign()
    else:
        row[0 if root_fault=='module_object' else 1]=Foreign();rows[6]=tuple(row)
    packet[3]=tuple(rows)
else:
    rows=list(packet[4]);index=30 if root_fault=='entry_kind' else 27
    if root_fault=='class_row':rows[index]=Foreign()
    else:rows[index]=(Foreign(),*rows[index][1:])
    packet[4]=tuple(rows)
packet=tuple(packet);layout=(packet,*helper[7][1][1:]);record=(packet,layout,helper[7][2])
helper=(*helper[:6],packet,record);candidate=((*parent[0][:6],helper,parent[0][7]),*parent[1:])
code=selected_helpers.current_live.__code__
def observe(frame,event,value):
    if event=='call' and frame.f_code is code:live.append(True)
assert sys.getprofile() is None
sys.setprofile(observe);error=None
try:parent_audit.current_started(candidate)
except RuntimeError as caught:error=caught
finally:sys.setprofile(None)
assert type(error) is RuntimeError and error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
assert calls==[] and live==[]
'''
    monkeypatch.setattr(base,'SCRIPT',base.SCRIPT.replace(marker,marker+extra,1))
    base.test_actual_entry_and_wrapper_files(tmp_path,'normal')


@pytest.mark.parametrize('fault', ('entry_copy','owner_invocation','live_export','live_code','live_default'))
def test_original_roots_and_live_callee_rejoin_after_selected_return(tmp_path, monkeypatch, fault):
    marker='entry = GatewayEntryOwner.start()\n'
    extra='\nreturn_fault='+repr(fault)+'\n'+r'''
from hmp_startup import gateway_entry as original_entry
from hmp_startup import retained_binding_origin as selected_helpers
from hmp_startup import link_factory_origin as parent_audit
from hmp_plugin import presentation_native_link as native_link
parent=tuple.__getitem__(original_entry._ENTRY_ORIGIN,10)
assert parent_audit.current_started(parent) is parent
held=selected_helpers.current_live;code=held.__code__;defaults=dict(held.__kwdefaults__)
original=original_entry._ENTRY_ORIGIN;invocation=entry._scope
reached=[];foreign_calls=[];engine_calls=[]
def foreign(*args,**kwargs):raise AssertionError('foreign selected callee')
def observe(frame,event,value):
    if event=='call' and frame.f_code is foreign.__code__:foreign_calls.append(True)
    if event=='call' and frame.f_code is native_link._engine_live_tail.__code__:engine_calls.append(True)
    if event=='return' and frame.f_code is code:
        assert value is parent[0][6][6]
        if return_fault=='entry_copy':original_entry._ENTRY_ORIGIN=original._replace()
        elif return_fault=='owner_invocation':entry._scope=invocation._replace()
        elif return_fault=='live_export':selected_helpers.current_live=foreign
        elif return_fault=='live_code':held.__code__=foreign.__code__
        else:held.__kwdefaults__['_error']=foreign
        reached.append(True)
assert sys.getprofile() is None
sys.setprofile(observe);error=None
try:parent_audit.current_started(parent)
except RuntimeError as caught:error=caught
finally:
    sys.setprofile(None);original_entry._ENTRY_ORIGIN=original;entry._scope=invocation
    selected_helpers.current_live=held;held.__code__=code
    held.__kwdefaults__.clear();held.__kwdefaults__.update(defaults)
assert type(error) is RuntimeError and error.args==('BI1_LINK_FACTORY_ORIGIN_REFUSED',)
assert reached==[True] and foreign_calls==engine_calls==[]
'''
    monkeypatch.setattr(base,'SCRIPT',base.SCRIPT.replace(marker,marker+extra,1))
    base.test_actual_entry_and_wrapper_files(tmp_path,'normal')
