"""Actual read returns retain progress while copied registrations refuse publication."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('package', 'artifact'))
@pytest.mark.parametrize('change', ('normal', 'copy', 'missing', 'post_return_copy'))
def test_native_read_keeps_original_registration(tmp_path, monkeypatch, kind, change):
    method = '_read'
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
        if CHANGE in ('copy','missing') and (target._count_cell is not count
                                            or len(target._origin.records)!=records):
            violations.append('read effect before registration refusal')
        if CHANGE in ('copy','missing') and len(native_calls)!=before:
            violations.append('native read entered before registration refusal')
        if CHANGE=='post_return_copy' and len(native_calls)!=before+1:
            violations.append('late refusal did not observe exactly one actual native call')
        if CHANGE=='post_return_copy' and (not observed
                or target._bytes_read!=count[2]+observed[-1] or not target._unknown):
            violations.append('late read progress or unknown debt lost')
        raise
def callback_walk(target,registration):
    result=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='post_return_copy' and registration is not None
            and type(target) is wanted and not replaced
            and frame.f_code is actual_method.__code__
            and type(frame.f_locals.get('data')) is bytes
            and len(frame.f_locals['data'])>0):
        observed.append(len(frame.f_locals['data']))
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
    assert replaced and observed
    assert all(type(value) is int and 0<value<=65536 for value in observed)
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


@pytest.mark.parametrize('change', ('normal', 'copy', 'missing', 'post_return_copy'))
def test_declared_cache_native_read_keeps_original_registration(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_reader as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = '\ntry:owner.read()\n'
    injected = r'''
actual_read=cm.DeclaredCacheReadOwner._read;actual_walk=cm._native_walk_scope
native_calls=[];replaced=[];observed=[];calls=[];refusals=[];violations=[]
def native_observed(frame):
    if frame.f_locals.get('self') is owner:native_calls.append(True)
observe_synthetic_native(cm.os.read,actual_read.__code__,native_observed)
def checked_read(target,fd,requested,s,native_registration=None):
    calls.append(True)
    supplied=native_registration
    if CHANGE=='copy':supplied=supplied._replace()
    if CHANGE=='missing':supplied=None
    try:return actual_read(target,fd,requested,s,supplied)
    except BaseException:
        refusals.append(True)
        if CHANGE in ('copy','missing') and (native_calls or cm._ATTEMPTS
                or cm._RESULTS or target._bytes_read!=0):
            violations.append('cache read entered before registration refusal')
        raise
def callback_walk(target,registration):
    result=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='post_return_copy' and registration is not None
            and target is owner and not replaced and frame.f_code is actual_read.__code__
            and type(frame.f_locals.get('data')) is bytes
            and len(frame.f_locals['data'])>0):
        observed.append(len(frame.f_locals['data']))
        copied=registration._replace()
        target._native_scope_registration=copied
        target._origin.native_registration_slot[0]=copied
        registration.lineage.ledger.scopes[registration.index]=copied
        replaced.append(True)
    return result
cm.DeclaredCacheReadOwner._read=checked_read;cm._native_walk_scope=callback_walk
try:owner.read()
except CacheReadError:
    assert CHANGE!='normal' and calls and refusals
else:
    assert CHANGE=='normal' and calls and native_calls
    assert owner._buffer==cache_payload and owner._bytes_read==len(cache_payload)
finally:cm.DeclaredCacheReadOwner._read=actual_read;cm._native_walk_scope=actual_walk
assert violations==[]
assert all(row.close_attempted and row.closed for row in owner._origin.records)
if CHANGE=='post_return_copy':
    assert replaced and len(native_calls)==1 and observed==[65536]
    assert owner._bytes_read==65536 and owner._unknown
    attempt=cm._ATTEMPTS[0];result=attempt[4][0]
    assert result[0] is attempt and result[2]==65536
    assert result[1] is owner._count_cell and result[1][2]==65536
    assert attempt[0].returned and attempt[0].unknown
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        prefix = runner.SCRIPT[:runner.SCRIPT.index(marker)]
        monkeypatch.setattr(runner, 'SCRIPT', prefix + injected)
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')
