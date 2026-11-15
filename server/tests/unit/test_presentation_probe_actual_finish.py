"""Actual observe must retain the complete original probe return."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('lost_finish_return', 'copied_resources', 'foreign_finished'))
def test_probe_actual_finish_return(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nfinish_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import cache_probe as pm
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import probe_native as engine
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
faults=[];held=[];budgets=[];hooks=[]
prior_profile=sys.getprofile()
original_code=engine._ProbeFinish.__new__.__code__
def capture(execution,resources):
    faults.append(True);held.extend(resources)
    budgets.append((tuple(execution.registration.native_ledger.counts),
                    len(execution.registration.native_ledger.attempts)))
class ForeignFinished:
    def __eq__(self,value):
        hooks.append(True)
        raise AssertionError('foreign finished equality executed')
if finish_case in ('lost_finish_return','foreign_finished'):
    def profile(frame,event,arg):
        if prior_profile is not None:prior_profile(frame,event,arg)
        if frame.f_code is engine._run_fresh_probe.__code__ and event=='return' and type(arg) is engine._ProbeFinish:
            capture(arg.execution,arg.resources)
            if finish_case=='lost_finish_return':
                raise RuntimeError('SYNTHETIC_COMPLETE_PROBE_RETURN_LOSS_ONLY')
            arg.execution.finished[0]=ForeignFinished()
    sys.setprofile(profile)
else:
    def copied(_cls,execution,predecessor,resources,outcome):
        return tuple.__new__(_cls,(execution,predecessor,tuple(list(resources)),outcome))
    def substitute(frame):
        if frame.f_locals['execution'].owner is owner and not faults:
            capture(frame.f_locals['execution'],frame.f_locals['resources'])
            engine._ProbeFinish.__new__.__code__=copied.__code__
    trace_synthetic_boundary(engine._finish.__code__,'result = constructor(kind, *values)',substitute)
refused=False
try:
    try:owner.observe()
    except CacheProbeError:refused=True
finally:
    engine._ProbeFinish.__new__.__code__=original_code
    sys.setprofile(prior_profile)
execution=owner._probe_execution
reg=execution.registration
facts={'case':finish_case,'faults':len(faults),'refused':refused,'foreign_hooks':len(hooks),
       'ready':owner._ready,'fact_published':owner._fact is not None or pm._FACT is not None,
       'held':len(held),'closed':sum(row.closed for row,fd in held),
       'metered_replay':budgets!=[(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))]}
path=Path(sys.argv[1])/'probe-actual-finish-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert faults==[True] and refused and owner._failed and not owner._ready and hooks==[]
assert owner._fact is None and pm._FACT is None and owner._origin.activation._runtime_cache_probe_fact is None
assert held and all(row.closed and row.close_attempted and row.fd is fd for row,fd in held)
assert budgets==[(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))]
assert all(commit.consumer.custody[0].reference_call(commit.consumer.custody[1].reference) is None
           for commit in execution.history)
assert owner._bytes_read==0
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
