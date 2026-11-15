"""Only the literal native call may report the typed missing diagnostic."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('before_native', 'after_native'))
def test_probe_diagnostic_boundary(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ndiagnostic_case=' + repr(case) + '\n'
    script += r'''
import gc,os
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
first=len(reg.native_ledger.attempts)
faults=[];native_calls=[];diagnostic_constructors=[]
def native_observed(frame):
    if frame.f_locals.get('owner') is owner:native_calls.append(True)
observe_synthetic_native(reg.native_origin.operations[3],m._produce_directory_metadata.__code__,native_observed)
prior_profile=sys.getprofile()
constructor_code=m._ReportedMissingMetadataReturn.__new__.__code__
def profile(frame,event,arg):
    if prior_profile is not None:prior_profile(frame,event,arg)
    if event=='call' and frame.f_code is constructor_code:diagnostic_constructors.append(True)
sys.setprofile(profile)
def inject(frame):
    if frame.f_locals.get('owner') is owner and not faults:
        operation=frame.f_locals['operation']
        faults.append(True)
        # Exact matching exception; the source of the report is deliberately
        # lifecycle/control or post-return bookkeeping rather than native stat.
        raise reg.native_origin.errors[1](scope.native_probe_engine_origin[5],
                                          'SYNTHETIC_NON_NATIVE_DIAGNOSTIC',operation.arguments[0])
fragment=('if operation.operation == 4:' if diagnostic_case=='before_native' else
          'operation.state[1] = True')
trace_synthetic_boundary(m._produce_directory_metadata.__code__,fragment,inject)
refused=False
old_gc=gc.isenabled();gc.disable()
try:
    try:engine._run_fresh_probe(owner,scope,reg,scope.native_probe_plan)
    except a.ArtifactObservationError:refused=True
    operation=reg.native_ledger.attempts[first]
    facts={'case':diagnostic_case,'faults':len(faults),'stat_calls':len(native_calls),
           'diagnostic_constructors':len(diagnostic_constructors),'refused':refused,
           'returned':operation.state[1],'unknown':operation.state[2],
           'ended':operation.ended[0],'history':len(owner._probe_execution.history)}
    path=Path(sys.argv[1])/'probe-diagnostic-boundary-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    assert faults==[True] and refused
    assert diagnostic_constructors==[], 'non-native failure constructed reported-missing outcome'
    assert native_calls==([] if diagnostic_case=='before_native' else [True])
    assert operation.state[1] is (diagnostic_case=='after_native')
    assert operation.state[2] is True and operation.ended[0] is True
    assert owner._probe_execution.history==[] and owner._bytes_read==0
finally:
    sys.setprofile(prior_profile)
    if old_gc:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
