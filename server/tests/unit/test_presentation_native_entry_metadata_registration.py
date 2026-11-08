"""Entry metadata walkers retain original IO provenance, not operation authority."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('_tree', '_metadata', '_names', '_walk'))
@pytest.mark.parametrize('change', ('normal', 'copied', 'missing'))
def test_entry_metadata_walkers_forward_original_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'try:checked=EntryFileSnapshotOwner.complete(retained)'
    injected = r'''
kind=KIND;change=CHANGE
actual_method=getattr(EntryFileSnapshotOwner,kind)
calls=[];held=[]
def observed(target,io,*args,**kwargs):
    assert target is retained and not kwargs and args
    record=io._origin.native_registration_slot[0]
    assert record is not None and args[-1] is record
    calls.append(record)
    if not held:held.extend((io,io._count_cell,len(io._origin.records)))
    forwarded=list(args)
    if change=='copied':forwarded[-1]=record._replace()
    if change=='missing':forwarded[-1]=None
    return actual_method(target,io,*forwarded)
setattr(EntryFileSnapshotOwner,kind,observed)
try:
    try:checked=EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:
        assert change!='normal' and retained._failed and not retained._ready
        assert retained._fact_cell is None and len(calls)==1
        io,count,records=held
        assert io._count_cell is count and len(io._origin.records)==records
    else:
        assert change=='normal' and retained._ready and calls
        assert all(value is calls[0] for value in calls)
finally:setattr(EntryFileSnapshotOwner,kind,actual_method)
io=inputs.io_slot[0]
assert all(row.closed for row in io._origin.records)
assert all(row.closed for row in inputs.scans)
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


@pytest.mark.parametrize('kind', ('_tree', '_metadata', '_names', 'complete'))
def test_entry_metadata_final_callbacks_refuse_replacement(tmp_path, monkeypatch, kind):
    from . import test_presentation_cache_observation as cache
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'try:checked=EntryFileSnapshotOwner.complete(retained)'
    injected = r'''
kind=KIND;changed=[];origins=[]
actual_io=EntryFileSnapshotOwner._io_current
actual_origins=EntryFileSnapshotOwner._origins
def replace_record(io):
    record=io._origin.native_registration_slot[0]
    assert record is not None
    copied=record._replace()
    io._origin.native_registration_slot[0]=copied
    io._native_scope_registration=copied
    record.lineage.ledger.scopes[record.index]=copied
    changed.append(True)
def changed_io(target,io,native_registration=None):
    value=actual_io(target,io,native_registration)
    frame=sys._getframe(1)
    final=(frame.f_code.co_name==kind and 'result' in frame.f_locals
           and (frame.f_locals['scan'].closed if kind=='_names' else
                all(row.closed for row,fd in frame.f_locals['held'])))
    if kind!='complete' and target is retained and final and not changed:replace_record(io)
    return value
def changed_origins(target):
    value=actual_origins(target)
    if target is retained:
        origins.append(True)
        if kind=='complete' and len(origins)==3:replace_record(inputs.io_slot[0])
    return value
EntryFileSnapshotOwner._io_current=changed_io
EntryFileSnapshotOwner._origins=changed_origins
try:
    try:EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:
        assert changed==[True] and retained._failed and not retained._ready
        assert retained._fact_cell is None
        assert entry._activation._entry_files_fact_cell is None
    else:raise AssertionError('final entry callback published replaced registration')
finally:
    EntryFileSnapshotOwner._io_current=actual_io
    EntryFileSnapshotOwner._origins=actual_origins
io=inputs.io_slot[0]
assert all(row.closed for row in io._origin.records)
assert all(row.closed for row in inputs.scans)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('KIND', repr(kind))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        script = runner.SCRIPT.replace('GatewayPackageOwner.verify_recipe(recipe)',
                                      'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
        monkeypatch.setattr(runner, 'SCRIPT', script.replace(marker, injected + marker))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    cache.test_original_cache_absence_io(tmp_path, monkeypatch, 'missing_leaf')
