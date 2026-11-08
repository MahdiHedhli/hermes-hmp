"""Fresh-probe provenance with zero payload reads and original cleanup custody."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('change', ('normal', 'copied', 'missing', 'tail', 'actor', 'stat'))
def test_fresh_probe_holds_registration_before_actor_and_stat(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'owner=RuntimeCacheProbeOwner.retain(continuation,index)'
    injected = r'''
record=owner._origin.native_registration_slot[0]
actual_owned=RuntimeCacheProbeOwner._observe_owned
actual_stat=RuntimeCacheProbeOwner._stat_known
actual_walk=pm._native_walk_scope;actual_context=pm._context
calls=[];changed=[]
def replace_record():
    copied=record._replace()
    owner._origin.native_registration_slot[0]=copied
    owner._native_scope_registration=copied
    record.lineage.ledger.scopes[record.index]=copied
    changed.append(True)
def observed_owned(target,s,selected,path,proof,registration,root,cell,count):
    assert target is owner and registration is record
    calls.append('owned')
    argument=record._replace() if CHANGE=='copied' else (None if CHANGE=='missing' else record)
    return actual_owned(target,s,selected,path,proof,argument,root,cell,count)
def observed_stat(target,name,parent,s,native_registration=None):
    assert target is owner and native_registration is record
    calls.append('stat')
    argument=record._replace() if CHANGE=='stat' else record
    return actual_stat(target,name,parent,s,argument)
def changed_context():
    value=actual_context()
    if CHANGE=='actor' and not changed and sys._getframe(1).f_code.co_name=='observe':
        replace_record()
    return value
def changed_walk(target,registration):
    value=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='tail' and target is owner and not changed
            and frame.f_code.co_name=='_observe_owned' and 'fact' in frame.f_locals
            and all(row.closed for row,fd in frame.f_locals['held'])):
        replace_record()
    return value
RuntimeCacheProbeOwner._observe_owned=observed_owned
RuntimeCacheProbeOwner._stat_known=observed_stat
pm._context=changed_context;pm._native_walk_scope=changed_walk
try:
    try:result=owner.observe()
    except CacheProbeError:
        assert CHANGE!='normal' and owner._failed and not owner._ready
        assert owner._fact is None and pm._FACT is None
        assert owner._origin.activation._runtime_cache_probe_fact is None
        if CHANGE in ('copied','missing','actor','stat'):assert owner._origin.records==[]
        if CHANGE in ('actor','tail'):assert changed==[True]
    else:
        assert CHANGE=='normal' and result is owner and owner._ready
        assert owner._fact[2].state=='missing_component' and 'stat' in calls
finally:
    RuntimeCacheProbeOwner._observe_owned=actual_owned
    RuntimeCacheProbeOwner._stat_known=actual_stat
    pm._context=actual_context;pm._native_walk_scope=actual_walk
assert calls and owner._bytes_read==0
assert all(row.closed for row in owner._origin.records)
assert checked._fact_cell[2]._count_cell is old_count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')


@pytest.mark.parametrize('change', ('normal', 'registration', 'fact'))
def test_fresh_probe_query_keeps_originals(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'owner=RuntimeCacheProbeOwner.retain(continuation,index)'
    injected = r'''
owner.observe()
record=owner._origin.native_registration_slot[0];fact=owner._fact
count=owner._count_cell;records=tuple(owner._origin.records)
actual_walk=pm._native_walk_scope;changed=[]
def changed_walk(target,registration):
    result=actual_walk(target,registration)
    if (CHANGE!='normal' and target is owner and not changed
            and sys._getframe(1).f_code.co_name=='current_binding'):
        if CHANGE=='registration':
            copied=record._replace()
            owner._origin.native_registration_slot[0]=copied
            owner._native_scope_registration=copied
            record.lineage.ledger.scopes[record.index]=copied
        else:
            copied=tuple(list(fact))
            owner._fact=pm._FACT=owner._origin.activation._runtime_cache_probe_fact=copied
        changed.append(True)
    return result
pm._native_walk_scope=changed_walk
try:
    try:result=owner.current_binding()
    except CacheProbeError:assert CHANGE!='normal' and changed==[True] and owner._failed
    else:assert CHANGE=='normal' and result is fact
finally:pm._native_walk_scope=actual_walk
assert owner._count_cell is count and owner._bytes_read==0
assert len(owner._origin.records)==len(records)
assert all(current is original and original.closed
           for current,original in zip(owner._origin.records,records,strict=True))
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')
