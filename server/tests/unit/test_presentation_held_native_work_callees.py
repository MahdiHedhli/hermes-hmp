"""Fixed work boundaries hold entry-captured native functions before callbacks."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('method', ('_open', '_read', '_stat', '_fstat', '_readlink'))
@pytest.mark.parametrize('change', ('normal', 'copy_origin', 'pre_os', 'late_os',
                                    'late_posix', 'late_flags', 'late_result_type'))
def test_fixed_work_calls_hold_original_native_origin(tmp_path, monkeypatch, method, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    injected = r'''
actual_method=getattr(a.StartupArtifactOwner,METHOD)
actual_capture=a._capture_native_work_origin;actual_tail=a._native_work_origin_tail
wanted=a.StartupArtifactOwner if METHOD=='_readlink' else GatewayPackageOwner
calls=[];native_calls=[];foreign_calls=[];changed=[];refusals=[];violations=[];targets=[]
original_native=getattr(a.os,METHOD[1:])
restore=[]
class ForeignValue:
    def __index__(self):foreign_calls.append('index');raise AssertionError('foreign index')
    def __bool__(self):foreign_calls.append('bool');raise AssertionError('foreign bool')
def foreign(*args,**kwargs):
    foreign_calls.append('call');raise AssertionError('foreign native function')
def mutate(registration,mode):
    origin=registration.lineage.native
    namespace=origin.native if mode=='late_posix' else a.os
    name=METHOD[1:]
    value=foreign
    if mode=='late_flags':name='O_NONBLOCK';value=ForeignValue()
    if mode=='late_result_type':name='stat_result';value=ForeignValue()
    restore.append((namespace,name,getattr(namespace,name)))
    setattr(namespace,name,value);changed.append(True)
def native_observed(frame):
    if type(frame.f_locals.get('self')) is wanted:native_calls.append(True)
observe_synthetic_native(original_native,actual_method.__code__,native_observed)
def checked_method(target,*args):
    if type(target) is not wanted or type(args[-1]) is not a._NativeScopeRegistration:
        return actual_method(target,*args)
    calls.append(True);targets.append(target)
    count=target._count_cell;before=len(native_calls)
    if CHANGE=='pre_os' and not changed:mutate(args[-1],CHANGE)
    try:return actual_method(target,*args)
    except BaseException:
        refusals.append(True)
        if CHANGE!='normal' and (len(native_calls)!=before or target._count_cell is not count):
            violations.append('effect before held-origin refusal')
        raise
def captured(target,registration):
    origin=actual_capture(target,registration)
    if (CHANGE=='copy_origin' and registration is not None and type(target) is wanted
            and sys._getframe(1).f_code is actual_method.__code__):
        changed.append(True);return origin._replace()
    return origin
def joined(target,registration,origin):
    if (CHANGE.startswith('late_') and registration is not None
            and type(target) is wanted and not changed
            and sys._getframe(1).f_code is actual_method.__code__):
        mutate(registration,CHANGE)
    return actual_tail(target,registration,origin)
setattr(a.StartupArtifactOwner,METHOD,checked_method)
a._capture_native_work_origin=captured;a._native_work_origin_tail=joined
try:
    plugin=GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    held_entry=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
    checked=EntryFileSnapshotOwner.complete(held_entry)
except Exception:
    assert CHANGE!='normal' and calls and refusals and changed
else:assert CHANGE=='normal' and calls and native_calls and checked._ready
finally:
    setattr(a.StartupArtifactOwner,METHOD,actual_method)
    a._capture_native_work_origin=actual_capture;a._native_work_origin_tail=actual_tail
    for namespace,name,value in reversed(restore):setattr(namespace,name,value)
assert foreign_calls==[] and violations==[]
if CHANGE!='normal':
    assert not native_calls
    assert all(row.fd is None or (row.close_attempted and row.closed)
               for target in targets for row in target._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''
    injected = injected.replace('METHOD', repr(method)).replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')
