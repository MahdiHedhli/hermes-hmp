"""Causal controls for the unqualified whole-engine failure contract."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('retire_before_stat', 'lost_native_return', 'wrong_actor',
                                 'stage_code_drift'))
def test_probe_engine_failure_contract(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nfailure_case=' + repr(case) + '\n'
    script += r'''
import gc,os,threading
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner
from hmp_startup import probe_native as engine
from hmp_plugin import presentation_startup_artifacts as a
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
# This is the SAME normal admission now used by observe(), not flag spoofing or
# a test-only bypass. Run the experimental engine from an ordinary frame so its
# nested fault boundaries are actually traced.
scope,selected,path,proof,reg,root,cell,count=RuntimeCacheProbeOwner._start(owner)
plan=scope.native_probe_plan
before=(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
faults=[];native_calls=[];references=[];held_rows=[]
owner._fixture_foreign_stage_calls=0
original_stage_code=engine._produce_shared.__code__
def observed(frame):
    if frame.f_locals.get('owner') is owner:native_calls.append(True)
observe_synthetic_native(reg.native_origin.operations[3],engine.metadata._produce_directory_metadata.__code__,observed)
if failure_case=='retire_before_stat':
    def retire(frame):
        if frame.f_locals.get('owner') is owner and not faults:
            faults.append(True)
            continuation._retired=True
    trace_synthetic_boundary(engine.metadata._produce_directory_metadata.__code__,'if operation.operation == 4:',retire)
elif failure_case=='lost_native_return':
    def lose(frame):
        execution=frame.f_locals['consumer'].execution
        if execution.owner is owner and execution.opened and not faults:
            faults.append(True)
            operation=frame.f_locals['operation']
            assert operation.state[0] is True and operation.state[1] is True
            references.append(operation.result.custody_slot[0].reference)
            held_rows.extend(scope.records)
            raise RuntimeError('synthetic producer-return loss after actual native return')
    trace_synthetic_boundary(engine.metadata._produce_directory_metadata.__code__,'snapshot = _native_metadata_snapshot(',lose)
if failure_case=='stage_code_drift':
    def foreign_stage(owner,consumer):
        vars(owner)['_fixture_foreign_stage_calls']+=1
        raise RuntimeError('synthetic foreign stage must never execute')
    def replace_stage(frame):
        if frame.f_locals['owner'] is owner and not faults:
            faults.append(True)
            engine._produce_shared.__code__=foreign_stage.__code__
    trace_synthetic_boundary(engine.metadata._run_directory_observation.__code__,
                             'producer_started = True',replace_stage)
refused=[]
def invoke():
    try:engine._run_fresh_probe(owner,scope,reg,plan)
    except a.ArtifactObservationError:refused.append(True)
    else:refused.append(False)
old_gc=gc.isenabled();gc.disable()
try:
    if failure_case=='wrong_actor':
        worker=threading.Thread(target=invoke);worker.start();worker.join(timeout=10)
        assert not worker.is_alive()
    else:invoke()
    if failure_case=='stage_code_drift':engine._produce_shared.__code__=original_stage_code
    execution=owner._probe_execution
    facts={'case':failure_case,'refused':refused,'faults':len(faults),
           'stat_calls':len(native_calls),'foreign_stage_calls':owner._fixture_foreign_stage_calls,
           'execution_published':execution is not None,
           'counts_unchanged':before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)),
           'ledger_failed':reg.native_ledger.failed[0],
           'retained_raw_capsules':sum(reference() is not None for reference in references),
           'known_rows':len(held_rows),'known_rows_closed':sum(row.closed for row in held_rows)}
    path=Path(sys.argv[1])/'fresh-probe-engine-failure-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    assert refused==[True]
    if failure_case=='retire_before_stat':
        assert faults==[True] and native_calls==[], 'retired continuation reached native stat'
    elif failure_case=='lost_native_return':
        assert faults==[True] and references and held_rows
        assert all(reference() is None for reference in references), 'actual raw capsule retained after producer unwind'
        assert all(row.closed and row.close_attempted for row in held_rows), 'known reserved cleanup blocked'
    elif failure_case=='stage_code_drift':
        assert faults==[True] and owner._fixture_foreign_stage_calls==0, 'changed original stage code executed after latch'
    else:
        assert owner._probe_execution is None, 'foreign actor published execution before eligibility'
        assert before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
        assert reg.native_ledger.failed==[False] and reg.native_ledger.inflight==[None]
        assert reg.native_phase.current[0] is reg.native_phase.idle and reg.native_phase.result==[None]
finally:
    if old_gc:gc.enable()
assert owner._bytes_read==0 and owner._count_cell is count and not owner._ready
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
