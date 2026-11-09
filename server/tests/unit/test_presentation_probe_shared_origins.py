"""Malformed origin/name DATA must refuse without executing foreign hooks."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('removed_export', 'foreign_policy_name', 'shared_helper_replaced',
                                  'shared_stage_selector', 'namespace_rejoin'))
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
hooks=[];closed=False;faults=[];fault_budget=[];native_calls=[]
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
elif origin_case=='shared_helper_replaced':
    original=m._probe_shared_call
    def foreign_helper(*args):hooks.append('shared_helper');raise AssertionError('foreign helper called')
    m._probe_shared_call=foreign_helper
    try:
        try:engine._engine_origin_tail(scope.native_probe_plan.engine_origin)
        except BaseException as error:closed=type(error) is a.ArtifactObservationError
    finally:m._probe_shared_call=original
elif origin_case in ('shared_stage_selector','namespace_rejoin'):
    name=('_probe_shared_call' if origin_case=='shared_stage_selector'
          else '_probe_function_namespace')
    original=vars(m)[name]
    prior_trace,prior_profile=sys.gettrace(),sys.getprofile()
    def foreign_helper(*args):hooks.append('late_helper');raise AssertionError('foreign helper called')
    def substitute(frame):
        if faults:return
        faults.append(True)
        fault_budget.append((tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts)))
        vars(m)[name]=foreign_helper
    target=(m._run_directory_observation.__code__ if origin_case=='shared_stage_selector'
            else m._rejoin_probe_stages.__code__)
    statement=('actual = produce(owner, consumer)' if origin_case=='shared_stage_selector'
               else 'actual = _probe_stage_functions(owner, resource)')
    trace_synthetic_boundary(target,statement,substitute)
    observe_synthetic_native(a.os.stat,m._produce_directory_metadata.__code__,
                             lambda frame:native_calls.append(True))
    try:
        try:engine._run_fresh_probe(owner,scope,reg,scope.native_probe_plan)
        except BaseException as error:closed=type(error) is a.ArtifactObservationError
    finally:
        vars(m)[name]=original
        sys.settrace(prior_trace);sys.setprofile(prior_profile)
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
if origin_case in ('shared_stage_selector','namespace_rejoin'):
    assert faults==[True] and native_calls==[] and len(fault_budget)==1
    assert fault_budget[0]==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
    assert owner._probe_execution is not None and owner._probe_execution.failed==[True]
    assert not owner._ready and owner._fact is None and scope.records==[]
else:
    assert before==(tuple(reg.native_ledger.counts),len(reg.native_ledger.attempts))
    assert owner._probe_execution is None
assert owner._bytes_read==0 and owner._count_cell is count
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
