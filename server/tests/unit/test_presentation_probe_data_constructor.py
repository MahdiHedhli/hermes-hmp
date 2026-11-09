"""Reject constructor drift before native work or foreign constructor execution."""
from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


def test_probe_data_constructor_origin(tmp_path, monkeypatch):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += r'''
import os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import cache_probe as pm
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
faults=[];budgets=[];calls=[]
constructor=pm.CacheProbeData.__new__;code=constructor.__code__
key='SYNTHETIC_DATA_CONSTRUCTOR_CALLS_ONLY'
assert key not in constructor.__globals__
constructor.__globals__[key]=calls
def foreign(_cls,state,position,identity,ancestors):
    globals()['SYNTHETIC_DATA_CONSTRUCTOR_CALLS_ONLY'].append(True)
    return tuple.__new__(_cls,(state,position,identity,ancestors))
def substitute(frame):
    if frame.f_locals['self'] is owner and not faults:
        faults.append(True)
        reg=frame.f_locals['native_registration']
        budgets.append((tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)))
        constructor.__code__=foreign.__code__
trace_synthetic_boundary(RuntimeCacheProbeOwner._observe_owned.__code__,'actual = run(',substitute)
refused=False
try:
    try:owner.observe()
    except CacheProbeError:refused=True
finally:
    constructor.__code__=code
    constructor.__globals__.pop(key)
reg=owner._origin.native_registration_slot[0]
facts={'faults':len(faults),'refused':refused,'constructor_calls':len(calls),
       'execution_published':owner._probe_execution is not None,
       'no_extra_debit':budgets==[(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))]}
path=Path(sys.argv[1])/'probe-data-constructor-origin-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert faults==[True] and refused and calls==[] and owner._failed and not owner._ready
assert owner._probe_execution is None and owner._origin.records==[]
assert budgets==[(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))]
assert owner._fact is None and pm._FACT is None and owner._bytes_read==0
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
