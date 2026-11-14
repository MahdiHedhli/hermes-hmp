"""Held cache/link provenance with actual isolated metadata/cleanup observations."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('cache', 'link'))
@pytest.mark.parametrize('change', ('normal', 'copied', 'missing', 'tail'))
def test_cache_link_forwards_original_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'try:checked=EntryFileSnapshotOwner.complete(retained)'
    injected = r'''
kind=KIND;change=CHANGE
original_walk=a._native_walk_scope
original_pass=cache_module.observe_pass
original_link=a.StartupArtifactOwner._link_snapshot
calls=[];changed=[];held=[]
def observed_pass(source,owner,phase,previous,native_registration=None):
    record=owner._origin.native_registration_slot[0]
    assert native_registration is record and record is not None
    calls.append((phase,record));held.append((owner,source,owner._count_cell,len(owner._origin.records)))
    argument=record._replace() if change=='copied' else (None if change=='missing' else record)
    return original_pass(source,owner,phase,previous,argument)
def observed_link(owner,phase,previous,native_registration=None):
    record=owner._origin.native_registration_slot[0]
    assert native_registration is record and record is not None
    calls.append((phase,record));held.append((owner,None,owner._count_cell,len(owner._origin.records)))
    argument=record._replace() if change=='copied' else (None if change=='missing' else record)
    return original_link(owner,phase,previous,argument)
def changed_walk(owner,registration):
    result=original_walk(owner,registration)
    frame=sys._getframe(1)
    final=(frame.f_code.co_name=='observe_pass' and 'result' in frame.f_locals
           if kind=='cache' else
           frame.f_code.co_name=='_link_path' and frame.f_locals.get('result') is not None
           and all(row.closed for row,fd in frame.f_locals['held']))
    if change=='tail' and held and owner is held[0][0] and final and not changed:
        copied=registration._replace()
        owner._origin.native_registration_slot[0]=copied
        owner._native_scope_registration=copied
        registration.lineage.ledger.scopes[registration.index]=copied
        changed.append(True)
    return result
if kind=='cache':cache_module.observe_pass=observed_pass
else:a.StartupArtifactOwner._link_snapshot=observed_link
a._native_walk_scope=changed_walk
try:
    try:checked=EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:
        assert change!='normal' and retained._failed
        io,source,before_count,before_records=held[0]
        assert io._failed and not io._ready
        assert all(row.closed for row in io._origin.records)
        if change in ('copied','missing'):
            assert io._count_cell is before_count and len(io._origin.records)==before_records
        if change=='tail':
            assert changed==[True]
            if kind=='cache':assert source.before[0] is None and io._count_cell is before_count
            else:
                assert io._bytes_read==before_count[2]+sum(len(row.data)
                    for row in io._origin.runtime.reads if row.returned)
    else:
        assert change=='normal' and len(calls)==2
        assert calls[0][0]==0 and calls[1][0]==1 and calls[0][1] is calls[1][1]
        io=inputs.io_slot[0]
        link=inputs.runtime_plan.executable_link
        assert len(io._origin.runtime.reads)==2*len(link.hops)
        assert io._bytes_read==(io._initial_count_cell[2]
            +sum(row.size for row in inputs.runtime_plan.pending)+2*link.text_bytes)
finally:
    cache_module.observe_pass=original_pass
    a.StartupArtifactOwner._link_snapshot=original_link
    a._native_walk_scope=original_walk
assert calls
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('KIND', repr(kind)).replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        script = runner.SCRIPT.replace('GatewayPackageOwner.verify_recipe(recipe)',
                                      'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
        monkeypatch.setattr(runner, 'SCRIPT', script.replace(marker, injected + marker))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')


@pytest.mark.parametrize('change', ('normal', 'registration', 'fact'))
def test_link_recheck_holds_fact_registration_and_byte_count(tmp_path, monkeypatch, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'try:checked=EntryFileSnapshotOwner.complete(retained)'
    injected = r'''
checked=EntryFileSnapshotOwner.complete(retained)
io=inputs.io_slot[0];count=io._count_cell;reads=len(io._origin.runtime.reads)
record=io._origin.native_registration_slot[0];fact=io._fact_cell
actual_walk=a._native_walk_scope;changed=[]
def changed_walk(owner,registration):
    result=actual_walk(owner,registration)
    frame=sys._getframe(1)
    if (CHANGE!='normal' and owner is io and not changed
            and frame.f_code.co_name=='recheck_link_metadata' and 'metadata' in frame.f_locals):
        if CHANGE=='registration':
            copied=record._replace()
            io._origin.native_registration_slot[0]=copied
            io._native_scope_registration=copied
            record.lineage.ledger.scopes[record.index]=copied
        else:
            copied=tuple(list(fact))
            io._fact_cell=io._origin.activation._artifact_fact_cell=copied
        changed.append(True)
    return result
a._native_walk_scope=changed_walk
try:
    try:result=a.StartupArtifactOwner.recheck_link_metadata(io)
    except a.ArtifactObservationError:assert CHANGE!='normal' and changed==[True]
    else:assert CHANGE=='normal' and result is fact[4]
finally:a._native_walk_scope=actual_walk
assert io._count_cell is count and len(io._origin.runtime.reads)==reads
assert all(row.closed for row in io._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        script = runner.SCRIPT.replace('GatewayPackageOwner.verify_recipe(recipe)',
                                      'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
        monkeypatch.setattr(runner, 'SCRIPT', script.replace(marker, injected + marker))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')
