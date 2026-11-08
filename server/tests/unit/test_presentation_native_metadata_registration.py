"""Actual metadata calls keep held registrations and expose no copied authority."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('method', ('_stat', '_fstat'))
@pytest.mark.parametrize('change', ('normal', 'copy', 'missing', 'post_return_copy'))
def test_native_metadata_keeps_original_registration(tmp_path, monkeypatch, kind, method, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_method=getattr(a.StartupArtifactOwner,METHOD);actual_walk=a._native_walk_scope
calls=[];refusals=[];violations=[];native_calls=[];replaced=[];observed=[];targets=[]
wanted=GatewayPackageOwner if KIND=='package' else a.StartupArtifactOwner
native=getattr(a.os,METHOD[1:])
def native_observed(frame):
    if type(frame.f_locals.get('self')) is wanted:native_calls.append(True)
observe_synthetic_native(native,actual_method.__code__,native_observed)
def checked_method(target,*args):
    if type(target) is not wanted or type(args[-1]) is not a._NativeScopeRegistration:
        return actual_method(target,*args)
    calls.append(True);targets.append(target)
    count=target._count_cell;records=len(target._origin.records);before=len(native_calls)
    supplied=list(args)
    if CHANGE=='copy':supplied[-1]=supplied[-1]._replace()
    if CHANGE=='missing':supplied[-1]=None
    try:return actual_method(target,*supplied)
    except BaseException:
        refusals.append(True)
        if target._count_cell is not count or len(target._origin.records)!=records:
            violations.append('metadata refusal changed file progress')
        if CHANGE in ('copy','missing') and len(native_calls)!=before:
            violations.append('native metadata entered before registration refusal')
        if CHANGE=='post_return_copy' and len(native_calls)!=before+1:
            violations.append('late refusal did not observe exactly one actual native call')
        raise
def callback_walk(target,registration):
    result=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='post_return_copy' and registration is not None
            and type(target) is wanted and not replaced
            and frame.f_code is actual_method.__code__
            and type(frame.f_locals.get('value')) is a.os.stat_result):
        observed.append(frame.f_locals['value'])
        copied=registration._replace()
        target._native_scope_registration=copied
        target._origin.native_registration_slot[0]=copied
        registration.lineage.ledger.scopes[registration.index]=copied
        replaced.append(True)
    return result
setattr(a.StartupArtifactOwner,METHOD,checked_method);a._native_walk_scope=callback_walk
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception:
    assert CHANGE!='normal' and calls and refusals
else:assert CHANGE=='normal' and calls and native_calls and checked._ready
finally:setattr(a.StartupArtifactOwner,METHOD,actual_method);a._native_walk_scope=actual_walk
assert violations==[]
if CHANGE=='post_return_copy':
    assert replaced and observed and all(type(value) is a.os.stat_result for value in observed)
    assert all(row.close_attempted and row.closed for target in targets
               for row in target._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''
    injected = injected.replace('KIND', repr(kind)).replace('METHOD', repr(method))
    injected = injected.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')
