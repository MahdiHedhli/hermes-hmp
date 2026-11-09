"""A real scope constructor cannot silently overwrite foreign plan state."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'foreign_plan', 'foreign_records',
                                 'foreign_slot', 'foreign_member', 'foreign_dispatch'))
def test_fresh_probe_scope_publication(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nscope_case=' + repr(case) + '\n'
    script += r'''
import os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import cache_probe as cm
from hmp_startup import probe_metadata as pm
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
kind=cm._Scope;actual_new=kind.__new__;descriptor=vars(kind)['__new__']
foreign=object();held=[];calls=[];other_calls=[];facts={};before=[];getter_calls=[]
record_member=vars(kind)['records']
dispatch_member=vars(kind).get('__getattribute__')
lineage=continuation._source.entry_binding[0].native_files;ledger=lineage.ledger
prior=sys.getprofile();assert prior is None
def observe_native(frame,event,arg):
    if event=='c_call' and any(arg is lineage.native.operations[i] for i in (0,1,3,4,5)):
        if frame.f_code is RuntimeCacheProbeOwner._stat_known.__code__:calls.append(True)
        else:other_calls.append(arg.__name__)
def construct(cls,*values,**keywords):
    result=actual_new(cls,*values,**keywords)
    plan=keywords.get('native_probe_plan')
    if type(plan) is pm._FreshProbePlan:
        assert held==[] and plan.owner._probe_plan is None
        records=values[4];slot=keywords['native_registration_slot']
        held.append((plan.owner,plan,result,cm._ROOT,records,slot))
        before.append((tuple(ledger.counts),len(ledger.attempts),len(ledger.scopes)))
        if scope_case=='foreign_plan':plan.owner._probe_plan=foreign
        elif scope_case=='foreign_records':records.append(foreign)
        elif scope_case=='foreign_slot':slot[0]=foreign
        elif scope_case=='foreign_member':
            def replaced_records(instance):
                getter_calls.append(True)
                return record_member.__get__(instance,kind)
            kind.records=property(replaced_records)
        elif scope_case=='foreign_dispatch':
            def replaced_dispatch(instance,name):
                if name=='records':getter_calls.append(True)
                return object.__getattribute__(instance,name)
            kind.__getattribute__=replaced_dispatch
        sys.setprofile(observe_native)
    return result
kind.__new__=staticmethod(construct)
try:
    try:owner=RuntimeCacheProbeOwner.retain(continuation,index)
    except CacheProbeError:facts['refused']=True
    else:facts['retained']=True
finally:
    sys.setprofile(prior);kind.__new__=descriptor
    kind.records=record_member
    if dispatch_member is None:
        if '__getattribute__' in vars(kind):delattr(kind,'__getattribute__')
    else:kind.__getattribute__=dispatch_member
assert len(held)==1 and len(before)==1 and calls==[]
owner,plan,scope,partial,records,slot=held[0]
facts.update(case=scope_case,callbacks=len(held),probe_native_calls=len(calls),
             other_native_calls=list(other_calls),getter_calls=len(getter_calls),
             foreign_records_preserved=records==[foreign],
             foreign_slot_preserved=slot[0] is foreign,
             foreign_preserved=owner._probe_plan is foreign,
             owner_scope_unpublished=owner._scope is None and owner._origin is None,
             original_plan_published=owner._probe_plan is plan,
             debit_unchanged=before[0][:2]==(tuple(ledger.counts),len(ledger.attempts)),
             registration_unchanged=before[0][2]==len(ledger.scopes))
path=Path(sys.argv[1])/'fresh-probe-scope-stage.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
assert facts['debit_unchanged']
if scope_case=='normal':
    assert facts.get('retained') and facts['original_plan_published']
    assert owner._scope is scope and not owner._failed and not owner._ready
else:
    assert facts.get('refused') and not facts.get('retained'), 'constructor drift accepted before original scope publication'
    if scope_case=='foreign_plan':assert facts['foreign_preserved']
    elif scope_case=='foreign_records':assert facts['foreign_records_preserved']
    elif scope_case=='foreign_slot':assert facts['foreign_slot_preserved']
    elif scope_case in ('foreign_member','foreign_dispatch'):assert getter_calls==[]
    assert facts['owner_scope_unpublished']
    assert facts['registration_unchanged'] and owner._failed and cm._ROOT is partial
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
