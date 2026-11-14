"""Actual opens keep the caller-held original registration across callbacks."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('change', ('normal', 'copy', 'missing', 'post_return_copy'))
def test_actual_open_keeps_original_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_open=a.StartupArtifactOwner._open;actual_walk=a._native_walk_scope
calls=[];refusals=[];violations=[];replaced=[];known=[];mutations=[]
writeback_confirmed=[];close_calls=[];close_returns=[];targets=[]
import errno
from hmp_plugin.presentation_gateway_package import PackageInventoryError
wanted=GatewayPackageOwner if KIND=='package' else a.StartupArtifactOwner
open_code=actual_open.__code__;walk_code=actual_walk.__code__
active={};native_calls=[]
close_code=a._close_native_file_known.__code__
def observe(frame,event,callee):
    if (event in ('c_call','c_return') and frame.f_code is close_code
            and callee is frame.f_locals.get('close_call')):
        close=frame.f_locals['close'];fd=frame.f_locals['fd']
        if event=='c_call':close_calls.append((close,fd))
        elif event=='c_return':
            try:a.os.fstat(fd)
            except OSError as caught:
                close_returns.append((close,fd,caught.errno==errno.EBADF))
            else:close_returns.append((close,fd,False))
    if (event=='c_call' and frame.f_code is open_code
            and type(frame.f_locals.get('self')) is wanted
            and callee is frame.f_locals.get('open_call')):
        native_calls.append(True)
def traced(frame,event,value):
    if frame.f_code is open_code:
        if event=='call':
            values=frame.f_locals;target=values['self'];supplied=values['native_registration']
            if supplied is None or type(target) is not wanted:return None
            calls.append(True);targets.append(target)
            ledger=supplied.native_ledger
            active[id(frame)]=(target,target._count_cell,len(target._origin.records),len(native_calls),
                               ledger,tuple(ledger.counts),len(ledger.attempts))
            if CHANGE in ('copy','missing'):
                candidate=supplied._replace() if CHANGE=='copy' else None
                # The independent confirmation below also proves this completed.
                values['native_registration']=candidate
                mutations.append((supplied,candidate))
            return traced
        if id(frame) not in active:return None
        if event=='exception':
            target,count,records,attempts,ledger,counts,claims=active[id(frame)]
            refusals.append(True)
            if CHANGE in ('copy','missing'):
                # Read the actual bound local after the trace's writeback.
                assert frame.f_locals['native_registration'] is mutations[-1][1]
                assert (mutations[-1][1] is not mutations[-1][0]
                        if CHANGE=='copy' else mutations[-1][1] is None)
                writeback_confirmed.append(mutations[-1])
                if (target._count_cell is not count or len(target._origin.records)!=records
                        or len(native_calls)!=attempts or tuple(ledger.counts)!=counts
                        or len(ledger.attempts)!=claims):
                    violations.append('descriptor acquisition before registration refusal')
        if event=='return':active.pop(id(frame),None)
        return traced
    if frame.f_code is walk_code:
        if event=='return' and CHANGE=='post_return_copy' and not replaced:
            caller=frame.f_back;values=frame.f_locals
            target=values['owner'];registration=values['registration']
            if (registration is not None and type(target) is wanted
                    and caller.f_code is open_code
                    and type(caller.f_locals.get('fd')) is int):
                row=caller.f_locals['row'];fd=caller.f_locals['fd']
                assert value is target._origin
                assert target._native_scope_registration is registration
                assert target._origin.native_registration_slot[0] is registration
                assert registration.lineage.ledger.scopes[registration.index] is registration
                assert row.fd is fd and not row.closed
                copied=registration._replace()
                target._native_scope_registration=copied
                target._origin.native_registration_slot[0]=copied
                registration.lineage.ledger.scopes[registration.index]=copied
                assert copied is not registration
                assert target._native_scope_registration is copied
                assert target._origin.native_registration_slot[0] is copied
                assert registration.lineage.ledger.scopes[registration.index] is copied
                known.append((row,fd));replaced.append(True)
        return traced
    return None
prior_trace=sys.gettrace();prior_profile=sys.getprofile()
assert prior_trace is None and prior_profile is None
sys.settrace(traced);sys.setprofile(observe)
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception as caught:
    assert CHANGE!='normal' and calls and refusals
    if KIND=='package':
        assert type(caught) is PackageInventoryError and caught.failed_owner is targets[0]
        assert targets[0]._failed
    else:
        assert type(caught) is EntryFilesError and caught.failed_owner is held_entry
        assert held_entry._failed
else:assert CHANGE=='normal' and calls and checked._ready
finally:sys.settrace(prior_trace);sys.setprofile(prior_profile)
assert violations==[]
assert CHANGE not in ('copy','missing') or (mutations and len(writeback_confirmed)==len(mutations))
if CHANGE=='post_return_copy':
    assert replaced and known
    for row,fd in known:
        close=row.close
        assert row.close_attempted and row.unknown and row.allocation.refused==[True]
        assert close.state==[True,False] and close.raw==[None]
        receipt=close.result[0]
        assert type(receipt) is tuple and len(receipt)==3
        assert receipt[0] is close and receipt[1] is fd and receipt[2] is None
        assert sum(claim is close and actual is fd for claim,actual in close_calls)==1
        assert sum(claim is close and actual is fd and closed
                   for claim,actual,closed in close_returns)==1
        # Diagnostic closed intentionally refuses an unknown open result. The
        # literal native close receipt and immediate EBADF prove cleanup here.
        assert not row.closed
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('KIND', repr(kind)).replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')
