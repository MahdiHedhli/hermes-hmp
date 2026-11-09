"""Partial acknowledgement and lost-return contracts on actual shared machinery."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('ack_published', 'raw_cleared', 'snapshot_cleared',
                                 'envelope_cleared', 'category_cleared', 'consumed',
                                 'history_appended', 'cursor_stored', 'phase_result',
                                 'lost_ack_return'))
def test_probe_shared_ack_interruption(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nack_case=' + repr(case) + '\n'
    script += r'''
import gc,os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner
from hmp_startup import probe_native as engine
from hmp_plugin import presentation_native_metadata as m
from hmp_plugin import presentation_startup_artifacts as a
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
scope,selected,path,proof,reg,root,cell,count=RuntimeCacheProbeOwner._start(owner)
faults=[];held_rows=[];references=[];snapshots=[];native_after=[]
def interrupted(frame):
    consumer=frame.f_locals.get('consumer')
    if type(consumer) is m._ProbeConsumer and consumer.execution.owner is owner:
        execution=consumer.execution
        if execution.opened and not faults:
            operation=consumer.operation
            faults.append(True)
            held_rows.extend(scope.records)
            references.append(consumer.custody[5])
            snapshots.append((consumer,operation,frame.f_locals['commit'],
                              tuple(execution.history),execution.next_site[0],
                              tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)))
            raise RuntimeError('SYNTHETIC_ACK_STORE_INTERRUPTION_ONLY')
route={
 'ack_published':(m._ack_directory_policy.__code__,'actor_arguments = (consumer, actual, commit)'),
 'raw_cleared':(m._ack_directory_policy.__code__,'result.snapshot[0] = None'),
 'snapshot_cleared':(m._ack_directory_policy.__code__,'result.envelope[0] = None'),
 'envelope_cleared':(m._ack_directory_policy.__code__,'result.category[0] = None'),
 'category_cleared':(m._ack_directory_policy.__code__,'consumer.consumption[0] = commit'),
 'consumed':(m._ack_directory_policy.__code__,'if type(consumer) is _ProbeConsumer:'),
 'history_appended':(engine._publish_shared_ack.__code__,'execution.next_site[0] = commit.next_site'),
 'cursor_stored':(engine._publish_shared_ack.__code__,'execution.pending[0] = None'),
 'phase_result':(m._ack_directory_policy.__code__,'phase.current[0] = phase.idle'),
 'lost_ack_return':(m._ack_directory_policy.__code__,'return commit'),
}
trace_synthetic_boundary(*route[ack_case],interrupted)
def observed(frame):
    if faults:native_after.append(True)
for native in reg.native_origin.operations[3:5]:
    observe_synthetic_native(native,m._produce_directory_metadata.__code__,observed)
old_gc=gc.isenabled();gc.disable()
refused=False
try:
    try:engine._run_fresh_probe(owner,scope,reg,scope.native_probe_plan)
    except a.ArtifactObservationError:refused=True
    assert faults==[True] and refused and len(snapshots)==1
    consumer,operation,commit,history,cursor,budget,attempts=snapshots[0]
    execution=owner._probe_execution
    facts={'case':ack_case,'refused':refused,'faults':len(faults),
           'raw_capsules_alive':sum(reference() is not None for reference in references),
           'known_rows':len(held_rows),'closed_rows':sum(row.closed for row in held_rows),
           'stat_after_fault':len(native_after),'ack_preserved':operation.result.acknowledged[0] is commit,
           'history_length':len(execution.history),'history_at_fault':len(history),
           'cursor':execution.next_site[0],'cursor_at_fault':cursor,
           'used':reg.native_ledger.counts[0],'used_at_fault':budget[0],
           'attempts':len(reg.native_ledger.attempts),'attempts_at_fault':attempts,
           'failed':reg.native_ledger.failed[0]}
    path=Path(sys.argv[1])/'probe-ack-interruption-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    assert all(reference() is None for reference in references)
    assert held_rows and all(row.closed and row.close_attempted for row in held_rows)
    assert native_after==[] and operation.result.acknowledged[0] is commit
    assert len(execution.history)==len(history) and all(x is y for x,y in zip(execution.history,history,strict=True))
    assert execution.next_site[0]==cursor and len(reg.native_ledger.attempts)==attempts
    assert reg.native_ledger.counts[0]==budget[0]+len(held_rows)
    assert reg.native_ledger.failed==[True] and reg.native_ledger.inflight==[None]
    assert reg.native_phase.current[0] is reg.native_phase.failed and reg.native_phase.result==[None]
    assert owner._bytes_read==0 and owner._count_cell is count and not owner._ready
finally:
    if old_gc:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
