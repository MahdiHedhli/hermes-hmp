"""Startup policy DATA cannot gain admission from an unconfigured scope."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('unset_origin', 'foreign_module', 'wrong_owner', 'copied_registration'))
def test_startup_metadata_unconfigured_scope_refuses(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\npolicy_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_plugin import presentation_native_metadata as metadata
from hmp_plugin import presentation_startup_artifacts as artifacts
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner
owner=checked._fact_cell[2]
if policy_case=='wrong_owner':
    continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
    rows=selected_cache_input_attempts(continuation)
    index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
    owner=RuntimeCacheProbeOwner.retain(continuation,index)
reg=owner._origin.native_registration_slot[0]
assert owner._origin.native_startup_probe_origin is None
hooks=[];refusals=[]
class Foreign:
    def __getattribute__(self,name):hooks.append('attribute');raise AssertionError('foreign metadata touched')
    def __iter__(self):hooks.append('iter');raise AssertionError('foreign metadata iterated')
resource=artifacts._NativeStartupProbeMetadataResource(
    owner,reg._replace() if policy_case=='copied_registration' else reg,
    Foreign(),None,(3,'startup_initial',1),0,None,('SYNTHETIC_NEVER_READ',None))
before=(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts),
        tuple(owner._origin.records),owner._count_cell,owner._bytes_read,
        owner._failed,owner._unknown)
name='hmp_plugin.presentation_startup_probe';absent=object();prior=sys.modules.get(name,absent)
if policy_case=='foreign_module':
    module=type(sys)(name)
    def foreign_getattr(name):hooks.append('module');raise AssertionError('foreign module getter')
    module.__getattr__=foreign_getattr;sys.modules[name]=module
try:
    for function in (metadata._resource_tail,metadata._closed_probe_engine_origin,
                     metadata._probe_stage_functions,metadata._prepare_metadata_operation_with_custody):
        try:function(owner,resource)
        except BaseException as error:refusals.append(type(error) is artifacts.ArtifactObservationError)
        else:refusals.append(False)
finally:
    if policy_case=='foreign_module':
        if prior is absent:sys.modules.pop(name)
        else:sys.modules[name]=prior
facts={'case':policy_case,'closed_refusals':refusals,'foreign_hooks':hooks,
       'debit_unchanged':before[:2]==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))}
path=Path(sys.argv[1])/'startup-metadata-gate-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert refusals==[True]*4 and hooks==[]
assert before[:2]==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
assert len(owner._origin.records)==len(before[2])
assert all(current is original for current,original in zip(owner._origin.records,before[2],strict=True))
assert owner._count_cell is before[3] and owner._bytes_read==before[4]
assert owner._failed is before[5] and owner._unknown is before[6]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
