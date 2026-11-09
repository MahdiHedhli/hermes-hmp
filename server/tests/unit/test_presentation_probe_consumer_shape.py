"""Reject a foreign operation before reading its resource property."""
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_probe_consumer_operation_shape(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += r'''
import os
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
hooks=[];decisions=[];counts=[]
class ForeignOperation:
    @property
    def resource(self):
        hooks.append('resource')
        raise AssertionError('foreign operation resource accessed')
def inject(frame):
    if decisions:return
    consumer=frame.f_locals.get('consumer')
    if type(consumer) is not m._ProbeConsumer or consumer.execution.owner is not owner:return
    forged=m._ProbeConsumer(consumer.execution,ForeignOperation(),consumer.predecessor,
                           consumer.commit,consumer.custody)
    before=(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
    try:engine._consumer_tail(forged,consumer.predecessor)
    except BaseException as error:decisions.append(type(error) is a.ArtifactObservationError)
    else:decisions.append(False)
    counts.append(before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)))
    raise RuntimeError('SYNTHETIC_FOREIGN_OPERATION_SHAPE_ONLY')
trace_synthetic_boundary(engine._latch_shared_consumer.__code__,
                         'execution = consumer.execution',inject)
try:engine._run_fresh_probe(owner,scope,reg,scope.native_probe_plan)
except a.ArtifactObservationError:pass
facts={'closed_refusal':decisions,'foreign_hooks':hooks,'no_extra_debit':counts}
path=Path(sys.argv[1])/'probe-consumer-shape-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert decisions==[True] and hooks==[] and counts==[True]
assert owner._bytes_read==0 and owner._count_cell is count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
