"""Malformed origin/name DATA must refuse without executing foreign hooks."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('removed_export', 'foreign_policy_name'))
def test_probe_shared_origin_refusal(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\norigin_case=' + repr(case) + '\n'
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
before=(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
hooks=[];closed=False
if origin_case=='removed_export':
    namespace=vars(m)
    original=namespace.pop('_consume_directory_policy')
    absent=object();prior=namespace.get('__getattr__',absent)
    def foreign_getattr(name):hooks.append(name);raise AssertionError('foreign module fallback')
    namespace['__getattr__']=foreign_getattr
    try:
        try:engine._engine_origin_tail(scope.native_probe_plan.engine_origin)
        except BaseException as error:closed=type(error) is a.ArtifactObservationError
    finally:
        namespace['_consume_directory_policy']=original
        if prior is absent:namespace.pop('__getattr__')
        else:namespace['__getattr__']=prior
else:
    class ForeignName:
        def __eq__(self,value):hooks.append('eq');raise AssertionError('foreign name comparison')
    # A malformed DATA record supplies no admission, work or grant authority.
    consumer=m._ProbeConsumer(None,object(),None,[None],())
    try:m._probe_policy_helper(owner,consumer,ForeignName())
    except BaseException as error:closed=type(error) is a.ArtifactObservationError
facts={'case':origin_case,'closed_refusal':closed,'foreign_hooks':list(hooks),
       'counts_unchanged':before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)),
       'execution_published':owner._probe_execution is not None}
path=Path(sys.argv[1])/'probe-shared-origin-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert closed and hooks==[], 'foreign origin/name hook executed before refusal'
assert before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
assert owner._probe_execution is None and owner._bytes_read==0 and owner._count_cell is count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
