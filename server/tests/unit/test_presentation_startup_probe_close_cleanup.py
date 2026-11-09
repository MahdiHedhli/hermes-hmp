"""A lost native close ACK must not stop remaining reserved startup cleanup."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'first', 'middle'))
def test_startup_probe_known_close_cleanup(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += '\ncleanup_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_plugin import presentation_startup_cache as cache_module
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
inputs=retained._inputs
row=next(row for row in inputs.cache_context_slot[0][3] if row.state=='needs_owned_absence')
cache_path=Path(row.location.path)
cache_path.parent.mkdir(mode=0o700)
held=[];attempted=[];faults=[];target=[];budgets=[];active_effects=[];restored=[]
prior_trace,prior_profile=sys.gettrace(),sys.getprofile()
def current(frame):
    cursor=frame
    while cursor is not None:
        if cursor.f_code is cache_module._probe.__code__:
            values=cursor.f_locals
            io,effect,resources=values.get('owner'),values.get('effect'),values.get('held')
            if (type(io) is not a.StartupArtifactOwner or io._origin.cache is None
                    or type(effect) is not cache_module._ProbeEffect
                    or effect.source is not io._origin.cache
                    or effect.returned or effect.phase!=0):return None
            if active_effects and effect is not active_effects[0]:return None
            assert type(resources) is list
            return io,effect,resources
        cursor=cursor.f_back
    return None
def close_observed(frame):
    cohort=current(frame)
    if cohort is None:return
    io,effect,resources=cohort
    allocation=frame.f_locals['allocation'];actual=allocation.result[0]
    assert type(actual) is tuple and actual[0] is allocation
    descriptor=actual[1]
    assert type(descriptor) is a._NativeOpenedDescriptor and descriptor.fd is frame.f_locals['fd']
    if not held:
        held.extend(row for row,fd in resources)
        assert len(held)>2 and all(type(row) is a._NativeOpenedDescriptor for row in held)
        target.append(held[-1] if cleanup_case=='first' else held[len(held)//2])
        active_effects.append(effect)
    attempted.append((descriptor,frame.f_locals['fd']))
observe_synthetic_native(a.os.close,a._close_native_file_known.__code__,close_observed)
def lose_ack(frame):
    cohort=current(frame)
    if cohort is None or cleanup_case=='normal' or faults or not target:return
    io,effect,resources=cohort
    allocation=frame.f_locals['allocation']
    descriptor=allocation.result[0][1]
    if descriptor is not target[0]:return
    assert frame.f_locals['close'].raw[0] is None
    faults.append(True)
    ledger=allocation.ledger
    budgets.append((ledger,tuple(ledger.counts),len(ledger.attempts),len(attempted)))
    raise OSError('SYNTHETIC_STARTUP_CLOSE_ACK_LOSS_ONLY')
trace_synthetic_boundary(a._close_native_file_known.__code__,
                         'close.result[0] = (close, fd, value)',lose_ack)
def scope_ended(frame):
    if not active_effects or frame.f_locals.get('effect') is not active_effects[0]:return
    restored.append(True)
    sys.setprofile(prior_profile);sys.settrace(prior_trace)
    path=Path(sys.argv[1])/'startup-probe-observer-scope-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump({'scope_ended':True,'known':len(held),'close_calls':len(attempted)},stream)
trace_synthetic_boundary(cache_module._probe.__code__,'return result, effect',scope_ended)
refused=False
try:
    try:checked=EntryFileSnapshotOwner.complete(retained)
    except EntryFilesError:refused=True
finally:
    sys.setprofile(prior_profile);sys.settrace(prior_trace)
io=inputs.io_slot[0]
facts={'case':cleanup_case,'refused':refused,'faults':len(faults),
       'known':len(held),'close_calls':len(attempted),
       'closed':sum(row.closed for row in held),'unknown':sum(row.unknown for row in held),
       'effect_unknown':bool(active_effects and active_effects[0].unknown),
       'ready':io._ready,'cache_fact':io._cache_fact is not None}
path=Path(sys.argv[1])/'startup-probe-close-cleanup-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert held and len(active_effects)==1
assert len(attempted)==len(held) and len({id(row) for row,fd in attempted})==len(held)
assert all(any(row is original for original in held) and row.fd is fd for row,fd in attempted)
if cleanup_case=='normal':
    assert not refused and faults==[] and restored==[True] and io._ready and io._cache_fact is not None
    assert all(row.closed and row.close_attempted and not row.unknown for row in held)
    assert active_effects[0].returned and not active_effects[0].unknown
else:
    assert refused and faults==[True] and restored==[] and io._failed and io._unknown and not io._ready
    assert io._cache_fact is None and io._fact_cell is None and entry._activation._artifact_fact_cell is None
    assert active_effects[0].unknown and not active_effects[0].returned
    unknown=[row for row in held if row.unknown]
    assert len(unknown)==1 and unknown[0] is target[0]
    assert target[0].close_attempted and not target[0].closed
    assert all(row.closed and row.close_attempted for row in held if row is not target[0])
    ledger,budget,attempts,closed_at_fault=budgets[0]
    remaining=len(held)-closed_at_fault
    assert ledger.counts==[budget[0]+remaining,budget[1]-remaining]
    assert len(ledger.attempts)==attempts
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
