"""Actual original C open/close with caller-held pre-C allocation, no service."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'lost_return', 'revoked_after_open'))
def test_original_prepared_open_cleanup(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    marker = 'original_bytes=plugin._bytes_read'
    assert script.count(marker) == 1
    script = script[:script.index(marker)]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
checked=EntryFileSnapshotOwner.complete(retained)
assert checked._ready and not checked._failed
owner=checked._fact_cell[2]
registration=owner._native_scope_registration
ledger=registration.native_ledger
counts=tuple(ledger.counts);attempts=tuple(ledger.attempts)
native=registration.native_origin
allocation=a._prepare_native_link_open(owner,registration,'/',None)
assert type(allocation) is a._NativeOpenAllocation
# Hold these actual original references before the native open. No later
# mutable holder/current descriptor or ledger lookup selects cleanup authority.
raw=allocation.raw
assert raw==[None] and allocation.result==[None]
assert ledger.counts==[counts[0]+1,counts[1]+1]
calls=[];losses=[]
open_code=a.StartupArtifactOwner._open.__code__
close_code=a._close_native_file_known.__code__
def observe(frame,event,callee):
    if event=='c_call' and frame.f_code is open_code and callee is native.operations[0]:
        assert frame.f_locals['allocation'] is allocation
        assert ledger.inflight[0] is allocation
        calls.append('open')
    if event=='c_call' and frame.f_code is close_code and callee is native.operations[2]:
        assert frame.f_locals['allocation'] is allocation
        calls.append('close')
def lose_return(frame,event,value):
    if frame.f_code is not open_code:return None
    if event=='return':
        assert type(value) is tuple and value[0].allocation is allocation
        assert raw[0] is value[1]
        losses.append(True)
        sys.settrace(None)
        raise RuntimeError('SYNTHETIC_OPEN_RETURN_LOSS')
    return lose_return
assert sys.gettrace() is sys.getprofile() is None
opened=None;receipt=None;failed=False
sys.setprofile(observe)
if case=='lost_return':sys.settrace(lose_return)
try:
    try:
        opened=a.StartupArtifactOwner._open(owner,'/',None,True,registration,allocation)
    except RuntimeError as error:
        assert case=='lost_return' and str(error)=='SYNTHETIC_OPEN_RETURN_LOSS'
        failed=True
    else:
        assert case!='lost_return' and opened[0].allocation is allocation
        assert opened[1] is raw[0]
        if case=='revoked_after_open':vars(registration.scope.activation)['_retired']=True
finally:
    sys.settrace(None)
    try:
        # At most one close. A lost open return never causes a second open or
        # a close authority recovered from current mutable bookkeeping.
        if not allocation.close.state[0]:
            receipt=a._close_native_file_known(owner,allocation,raw[0],ledger)
    finally:sys.setprofile(None)
assert calls==['open','close']
assert failed is (case=='lost_return')
assert losses==([True] if case=='lost_return' else [])
assert type(receipt) is tuple and receipt is allocation.close.result[0]
assert receipt[0] is allocation.close and receipt[1] is raw[0] and receipt[2] is None
assert allocation.close.state==[True,False]
assert ledger.counts==[counts[0]+2,counts[1]]
assert len(ledger.attempts)==len(attempts)+1 and ledger.attempts[-1] is allocation
assert all(ledger.attempts[i] is row for i,row in enumerate(attempts))
assert ledger.inflight==[None]
assert all(a._descriptor_closed_in_scope(row,owner._origin) for row in owner._origin.records)
if case=='revoked_after_open':assert vars(registration.scope.activation)['_retired'] is True
assert sys.gettrace() is sys.getprofile() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
