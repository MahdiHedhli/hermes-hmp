"""Operation and resource registrations must agree before any nested access."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('helper', ('lifetime', 'policy'))
def test_probe_foreign_operation_registration_refuses(tmp_path, monkeypatch, helper):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nhelper_case=' + repr(helper) + '\n'
    script += r'''
import os
from hmp_plugin import presentation_native_metadata as metadata
from hmp_plugin import presentation_startup_artifacts as artifacts
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
reg=owner._origin.native_registration_slot[0]
hooks=[]
class Foreign:
    def __getattribute__(self,name):hooks.append('attribute');raise AssertionError('foreign registration touched')
resource=artifacts._NativeProbeMetadataResource(owner,reg,None,None,(3,'probe_initial',0),0,None,('/',None))
operation=metadata._MetadataOperation(*([None]*len(metadata._MetadataOperation._fields)))
operation=operation._replace(resource=resource,registration=Foreign())
consumer=metadata._ProbeConsumer(None,operation,None,[None],())
before=(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
refused=False
try:
    if helper_case=='lifetime':metadata._probe_current_lifetime_tail(owner,consumer)
    else:metadata._probe_policy_helper(owner,consumer,'_make_shared_commit')
except BaseException as error:refused=type(error) is artifacts.ArtifactObservationError
facts={'helper':helper_case,'refused':refused,'foreign_hooks':hooks,
       'budget_unchanged':before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))}
path=Path(sys.argv[1])/'probe-operation-registration-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert refused and hooks==[]
assert before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
assert owner._probe_execution is None and owner._origin.records==[] and not owner._failed
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
