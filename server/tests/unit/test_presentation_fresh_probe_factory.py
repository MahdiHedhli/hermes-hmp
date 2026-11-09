"""Actual constructor callbacks cannot nominate original probe plan/code DATA."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'variant_observe', 'variant_material',
                                 'plan_observe', 'plan_definitions'))
def test_fresh_probe_factory_originals_before_constructors(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nfactory_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import probe_metadata as pm
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
original_factory=pm._new_fresh_probe_plan
site_new=pm._ProbeSite.__new__;site_descriptor=vars(pm._ProbeSite)['__new__']
plan_new=pm._FreshProbePlan.__new__;plan_descriptor=vars(pm._FreshProbePlan)['__new__']
pure=vars(RuntimeCacheProbeOwner)['_pure'];pure_code=pure.__code__
observe=vars(RuntimeCacheProbeOwner)['_observe_owned'];observe_code=observe.__code__
facts={};callbacks=[];foreign_execution=[];native_calls=[];held_inputs=[]
supplied_definitions=[]
def foreign_body(self,*args,**kwargs):foreign_execution.append(True)
def site_constructor(cls,*values):
    if factory_case.startswith('variant_') and not callbacks:
        target=observe if factory_case=='variant_observe' else pure
        target.__code__=foreign_body.__code__;callbacks.append(factory_case)
    return site_new(cls,*values)
def plan_constructor(cls,*values):
    if factory_case=='plan_observe' and not callbacks:
        observe.__code__=foreign_body.__code__;callbacks.append(factory_case)
    if factory_case=='plan_definitions':
        supplied_definitions.append(values[15])
        changed=list(values);changed[15]=tuple(list(values[15]))
        values=tuple(changed);callbacks.append(factory_case)
    return plan_new(cls,*values)
def tracked_factory(owner,root,selected,context):
    lineage=root[2].entry_binding[0].native_files
    ledger=lineage.ledger;before=(tuple(ledger.counts),len(ledger.attempts))
    def profile(frame,event,arg):
        if event=='c_call' and any(arg is lineage.native.operations[i] for i in (0,1,3,4,5)):
            native_calls.append(True)
    prior=sys.getprofile();assert prior is None
    held_inputs.append((owner,root,selected,context))
    sys.setprofile(profile)
    try:
        try:result=original_factory(owner,root,selected,context)
        except pm.ProbePlanError:
            facts['factory_refused']=True
            raise
        else:
            facts.update(factory_returned=True,
                         changed_observe_adopted=result.observe_code is foreign_body.__code__,
                         changed_material_adopted=result.material_code is foreign_body.__code__,
                         changed_definition_tuple=(bool(supplied_definitions) and
                             result.definitions is not supplied_definitions[0]))
            return result
    finally:
        sys.setprofile(prior)
        assert before==(tuple(ledger.counts),len(ledger.attempts))
        assert native_calls==[]
pm._ProbeSite.__new__=staticmethod(site_constructor)
pm._FreshProbePlan.__new__=staticmethod(plan_constructor)
pm._new_fresh_probe_plan=tracked_factory
try:
    try:owner=RuntimeCacheProbeOwner.retain(continuation,index)
    except CacheProbeError:facts['retain_refused']=True
    else:
        facts['retained']=True
        assert owner._ready is False and owner._started is False
finally:
    pm._ProbeSite.__new__=site_descriptor
    pm._FreshProbePlan.__new__=plan_descriptor
    pm._new_fresh_probe_plan=original_factory
    pure.__code__=pure_code;observe.__code__=observe_code
facts.update(case=factory_case,callbacks=list(callbacks),
             foreign_execution=len(foreign_execution),native_filesystem_calls=len(native_calls))
path=Path(sys.argv[1])/'fresh-probe-factory-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert len(held_inputs)==1 and native_calls==[]
if factory_case=='normal':
    assert facts.get('factory_returned') and facts.get('retained') and callbacks==[]
else:
    assert callbacks==[factory_case]
    assert facts.get('factory_refused'), 'constructor callback changed original plan DATA before factory closure'
    assert facts.get('retain_refused') and not facts.get('retained')
    assert foreign_execution==[]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
