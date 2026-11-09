"""Probe root DATA uses shared intent allocation without native admission."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_registration', 'copied_plan',
                                 'wrong_arguments', 'foreign_resource', 'other_site',
                                 'foreign_ordinal', 'fake_module_fake_type',
                                 'fake_module_actual_type', 'helper_export', 'helper_code'))
def test_fresh_probe_shared_intent(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nresource_case=' + repr(case) + '\n'
    script += r'''
import gc,os,weakref
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import probe_metadata as pm
from hmp_plugin import presentation_native_metadata as m
from hmp_plugin import presentation_startup_artifacts as a
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
seen=[];foreign_hooks=[];native_calls=[];facts={}
class Foreign:
    def __getattr__(self,name):foreign_hooks.append(name);raise AssertionError('foreign getter')
    def __eq__(self,other):foreign_hooks.append('eq');raise AssertionError('foreign equality')
    def __index__(self):foreign_hooks.append('index');raise AssertionError('foreign index')
def exercise(frame):
    if frame.f_locals['self'] is not owner or seen:return
    seen.append(True)
    scope=frame.f_locals['s'];reg=frame.f_locals['native_registration'];plan=scope.native_probe_plan
    ledger=reg.native_ledger;phase=reg.native_phase
    before=(tuple(ledger.counts),len(ledger.attempts),tuple(scope.records))
    assert owner._started and not owner._retaining and not owner._admitting
    prior=sys.getprofile();assert prior is None
    def profile(frame,event,arg):
        if event=='c_call' and any(arg is reg.native_origin.operations[i] for i in (0,1,3,4,5)):
            native_calls.append(True)
    gc_before=gc.isenabled();gc.disable();sys.setprofile(profile)
    try:
        resource=pm._prepare_fresh_probe_resource(owner,reg,plan)
        assert resource.registration is reg and resource.metadata is plan
        assert resource.site is plan.definitions[0] and resource.variant is plan.variants[0]
        assert resource.arguments==('/',None) and resource.descriptor is None
        if resource_case=='copied_registration':
            candidate=resource._replace(registration=reg._replace())
        elif resource_case=='copied_plan':candidate=resource._replace(metadata=plan._replace())
        elif resource_case=='wrong_arguments':candidate=resource._replace(arguments=('foreign',None))
        elif resource_case=='foreign_resource':candidate=Foreign()
        elif resource_case=='other_site':
            candidate=resource._replace(ordinal=1,site=plan.definitions[1],variant=plan.variants[1])
        elif resource_case=='foreign_ordinal':candidate=resource._replace(ordinal=Foreign())
        else:candidate=resource
        substitutions=('fake_module_fake_type','fake_module_actual_type','helper_export','helper_code')
        if resource_case in substitutions:
            from types import ModuleType
            owner._fixture_resource_calls=0
            def foreign_helper(owner,resource):
                vars(owner)['_fixture_resource_calls']+=1
                return resource
            original_module=sys.modules['hmp_startup.probe_metadata']
            original_helper=pm._fresh_probe_resource_tail
            original_code=original_helper.__code__
            if resource_case.startswith('fake_module'):
                fake=ModuleType('hmp_startup.probe_metadata')
                kind=type('FakeProbeResource',(),{}) if resource_case.endswith('fake_type') else type(resource)
                fake._ProbeObservationResource=kind
                fake._fresh_probe_resource_tail=foreign_helper
                candidate=kind() if resource_case.endswith('fake_type') else resource
                sys.modules['hmp_startup.probe_metadata']=fake
            elif resource_case=='helper_export':pm._fresh_probe_resource_tail=foreign_helper
            else:original_helper.__code__=foreign_helper.__code__
            refused=False
            try:
                try:m._resource_tail(owner,candidate)
                except (pm.ProbePlanError,a.ArtifactObservationError):refused=True
            finally:
                sys.modules['hmp_startup.probe_metadata']=original_module
                pm._fresh_probe_resource_tail=original_helper
                original_helper.__code__=original_code
            facts.update(substitution_refused=refused,foreign_helper_calls=owner._fixture_resource_calls)
            assert refused and owner._fixture_resource_calls==0
        elif resource_case=='normal':
            operation,marker,payload=m._prepare_metadata_operation_with_custody(owner,candidate)
            reference=weakref.ref(payload)
            assert type(operation) is m._MetadataOperation and operation.resource is resource
            assert operation.registration is reg and operation.ledger is ledger
            assert operation.operation==3 and operation.callee is reg.native_origin.operations[3]
            assert operation.arguments is resource.arguments and operation.state==[False,False,False]
            assert operation.ended==[False] and operation.result.acknowledged==[None]
            assert operation.result.consumer==[None] and operation.result.raw[0] is operation.result.unset
            try:m._prepare_directory_consumer(owner,operation)
            except a.ArtifactObservationError:pass
            else:raise AssertionError('probe DATA admitted to declared-file consumer')
            assert operation.result.consumer==[None] and plan.progress==[0,None]
            # Dispose only these original, empty fixture cells. No ACK, refund,
            # native work, fabricated retirement receipt or failed-state reset.
            assert operation.result.custody_link[0] is payload
            operation.result.custody_link[0]=None
            payload=None
            assert reference() is None and not gc.isenabled()
            facts.update(shared_original_factory=True,unsupported_consumer_refused=True,
                         empty_payload_reclaimed=True)
        else:
            try:m._prepare_metadata_operation_with_custody(owner,candidate)
            except (pm.ProbePlanError,a.ArtifactObservationError):pass
            else:raise AssertionError('changed probe resource reached shared intent allocation')
            facts['changed_input_refused']=True
        assert native_calls==[] and foreign_hooks==[]
        assert before==(tuple(ledger.counts),len(ledger.attempts),tuple(scope.records))
        assert phase.current[0] is phase.idle and phase.result[0] is None
        assert ledger.inflight==[None] and ledger.failed==[False]
        assert plan.progress==[0,None] and plan.commits==[] and plan.ancestors==[]
    finally:
        sys.setprofile(prior)
        if gc_before:gc.enable()
    facts.update(case=resource_case,filesystem_native_calls=len(native_calls),foreign_hooks=list(foreign_hooks))
    facts['boundary_complete']=True
    path=Path(sys.argv[1])/'fresh-probe-resource-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    raise RuntimeError('synthetic boundary after pure probe intent before first native observation')
trace_synthetic_boundary(RuntimeCacheProbeOwner._observe_owned.__code__,
                         'plan = s.native_probe_plan',exercise)
try:owner.observe()
except CacheProbeError:pass
else:raise AssertionError('injected prefix boundary must stop legacy observation')
assert seen==[True] and facts.get('boundary_complete') is True and owner._failed and not owner._ready
assert owner._bytes_read==0 and owner._origin.records==[]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
