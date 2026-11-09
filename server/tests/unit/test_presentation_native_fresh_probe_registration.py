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
from hmp_plugin import presentation_native_metadata as metadata
from hmp_startup import probe_native as engine
record=owner._origin.native_registration_slot[0]
actual_owned=RuntimeCacheProbeOwner._observe_owned
actual_walk=pm._native_walk_scope
calls=[];changed=[];argument_refusals=[];supplied_budgets=[]
def replace_record():
    copied=record._replace()
    owner._origin.native_registration_slot[0]=copied
    owner._native_scope_registration=copied
    record.lineage.ledger.scopes[record.index]=copied
    changed.append(True)
def at_owned(frame):
    if frame.f_locals['self'] is owner:
        assert frame.f_locals['native_registration'] is record
        calls.append('owned')
trace_synthetic_boundary(actual_owned.__code__,'native_registry = native_registration.lineage.ledger.scopes',at_owned)
def observed_stat(frame):
    if frame.f_locals.get('owner') is owner:
        assert frame.f_locals['operation'].registration is record
        calls.append('stat')
observe_synthetic_native(pm.os.stat,metadata._produce_directory_metadata.__code__,observed_stat)
if CHANGE in ('copied','missing'):
    def supplied_record(frame):
        if frame.f_locals['self'] is owner and not argument_refusals:
            argument=record._replace() if CHANGE=='copied' else None
            calls.append('supplied')
            supplied_budgets.append((tuple(record.native_ledger.counts),len(record.native_ledger.attempts)))
            try:actual_owned(owner,frame.f_locals['s'],frame.f_locals['selected'],
                             frame.f_locals['path'],frame.f_locals['proof'],argument,
                             frame.f_locals['root'],frame.f_locals['cell'],frame.f_locals['count'])
            except BaseException as error:argument_refusals.append(type(error) is metadata.ArtifactObservationError)
            else:argument_refusals.append(False)
            raise RuntimeError('SYNTHETIC_SUPPLIED_REGISTRATION_REFUSAL_ONLY')
    trace_synthetic_boundary(RuntimeCacheProbeOwner.observe.__code__,
                             'return RuntimeCacheProbeOwner._observe_owned(',supplied_record)
if CHANGE=='stat':
    def supplied_stat_record(frame):
        if frame.f_locals['owner'] is owner and not argument_refusals:
            consumer=frame.f_locals['consumer'];operation=consumer.operation
            assert operation.registration is record
            forged=consumer._replace(operation=operation._replace(registration=record._replace()))
            calls.append('stat_prepare')
            supplied_budgets.append((tuple(record.native_ledger.counts),len(record.native_ledger.attempts)))
            try:metadata._probe_current_lifetime_tail(owner,forged)
            except BaseException as error:argument_refusals.append(type(error) is metadata.ArtifactObservationError)
            else:argument_refusals.append(False)
            raise RuntimeError('SYNTHETIC_SUPPLIED_STAT_REGISTRATION_ONLY')
    trace_synthetic_boundary(metadata._produce_directory_metadata.__code__,
                             'operation = _admit_directory_operation(owner, consumer)',supplied_stat_record)
original_profile=sys.getprofile()
def actor_profile(frame,event,arg):
    if original_profile is not None:original_profile(frame,event,arg)
    if CHANGE!='actor' or changed or event!='c_return' or frame.f_code is not metadata._native_actor_context.__code__:return
    caller=frame.f_back
    if (caller.f_code is metadata._admit_directory_operation.__code__
            and caller.f_locals.get('owner') is owner
            and arg is record.native_origin.actor_calls[2]):replace_record()
sys.setprofile(actor_profile)
def changed_walk(target,registration):
    value=actual_walk(target,registration)
    frame=sys._getframe(1)
    if (CHANGE=='tail' and target is owner and not changed
            and frame.f_code is actual_owned.__code__ and 'fact' in frame.f_locals
            and all(row.closed for row,fd in frame.f_locals['resources'])):replace_record()
    return value
pm._native_walk_scope=changed_walk
try:
    try:result=owner.observe()
    except CacheProbeError:
        assert CHANGE!='normal' and owner._failed and not owner._ready
        assert owner._fact is None and pm._FACT is None
        assert owner._origin.activation._runtime_cache_probe_fact is None
        if CHANGE in ('copied','missing','actor','stat'):assert owner._origin.records==[]
        if CHANGE in ('copied','missing','stat'):
            assert argument_refusals==[True] and 'stat' not in calls
            assert supplied_budgets==[(tuple(record.native_ledger.counts),len(record.native_ledger.attempts))]
        if CHANGE in ('actor','tail'):assert changed==[True]
    else:
        assert CHANGE=='normal' and result is owner and owner._ready
        assert owner._fact[2].state=='missing_component' and 'stat' in calls
finally:
    sys.setprofile(original_profile);pm._native_walk_scope=actual_walk
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


@pytest.mark.parametrize('kind', ('directory', 'declared'))
def test_present_probe_leaf_rechecks_keep_original_registration(tmp_path, monkeypatch, kind):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'owner=RuntimeCacheProbeOwner.retain(continuation,index)'
    injected = r'''
record=owner._origin.native_registration_slot[0]
from hmp_plugin import presentation_native_metadata as metadata
calls=[]
def observed_stat(frame):
    if frame.f_locals.get('owner') is owner:
        assert frame.f_locals['operation'].registration is record
        calls.append(frame.f_locals['arguments'][0])
observe_synthetic_native(pm.os.stat,metadata._produce_directory_metadata.__code__,observed_stat)
owner.observe()
assert owner._ready and owner._fact[2].state==EXPECTED
leaf=owner._origin.parent[1].plan_row.location.path.rsplit('/',1)[1]
assert calls.count(leaf)==2
assert owner._bytes_read==0 and all(row.closed for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('EXPECTED', repr('directory' if kind == 'directory' else 'declared_regular'))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    probe.test_fresh_cache_probe(tmp_path, monkeypatch, kind)
