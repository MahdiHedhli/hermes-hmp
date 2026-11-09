"""Complete real runtime-source walk and causal late finish refusal."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'late_link', 'late_ack', 'foreign_ordinal'))
def test_actual_complete_metadata_finish(tmp_path, monkeypatch, case):
    script, fixture_mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nfinish_case=' + repr(case) + '\n'
    script += r'''
import gc, os, sys
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner, RuntimeReadError
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_native_metadata as m
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
actual_run=m._run_directory_observation
actual_finish=m._finished_declared_file_tail
actual_capsule=m._finished_capsule_tail
commits=[];finish_calls=[];late=[];foreign_hooks=[];observed={}
foreign=object()
class ForeignOrdinal:
    def __eq__(self,other):
        foreign_hooks.append('eq')
        raise RuntimeError('synthetic final ordinal hook')

def observe_run(actual_owner,*args):
    result=actual_run(actual_owner,*args)
    if actual_owner is owner:commits.append(result)
    return result

def finish(actual_owner,registration,held,last):
    if actual_owner is not owner:return actual_finish(actual_owner,registration,held,last)
    assert commits and commits[-1] is last
    metadata=held[5]
    assert len(commits)==len(metadata.definitions)
    assert all(node.site is site for node,site in zip(commits,metadata.definitions,strict=True))
    assert metadata.progress==[len(metadata.definitions),None]
    assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
    finish_calls.append((held,last))
    candidate=last
    if finish_case=='foreign_ordinal':candidate=last._replace(ordinal=ForeignOrdinal())
    def poison(frame,event,arg):
        if frame.f_code is actual_capsule.__code__ and event=='return' and arg is last and not late:
            if finish_case=='late_link':commits[0].consumer.custody[2][0]=foreign
            elif finish_case=='late_ack':commits[0].operation.result.acknowledged[0]=foreign
            else:return
            late.append(True)
    prior=sys.getprofile()
    assert prior is None
    sys.setprofile(poison)
    try:
        try:result=actual_finish(actual_owner,registration,held,candidate)
        except a.ArtifactObservationError:
            observed['finish_refused']=True
            raise
        observed['finish_accepted']=True
        return result
    finally:sys.setprofile(prior)

m._run_directory_observation=observe_run
m._finished_declared_file_tail=finish
gc_before=gc.isenabled();gc.disable()
try:
    try:owner.read()
    except RuntimeReadError:observed['owner_refused']=True
    else:observed['owner_ready']=owner._ready
    assert len(finish_calls)==1
    held,last=finish_calls[0]
    observed.update(case=finish_case,metadata_sites=len(commits),
                    complete_definition_sequence=True,late_events=len(late),
                    foreign_hooks=list(foreign_hooks),
                    walk_state=held[0].state[0],file_progress=held[2][0],
                    gc_disabled=not gc.isenabled())
    if finish_case=='late_link':assert commits[0].consumer.custody[2][0] is foreign
    if finish_case=='late_ack':assert commits[0].operation.result.acknowledged[0] is foreign
    path=Path(sys.argv[1])/'metadata-complete-finish-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
    assert foreign_hooks==[], 'final ordinal must refuse before foreign comparison'
    if finish_case=='normal':
        assert observed.get('finish_accepted') and observed.get('owner_ready')
        assert held[0].state==[2] and held[2]==[1]
        assert bytes(owner._original_buffer)==(dep_root/'__init__.py').read_bytes()
        owner.release();assert owner._original_buffer==bytearray()
    else:
        assert observed.get('finish_refused') and observed.get('owner_refused')
        assert not owner._ready and owner._failed and owner._original_buffer==bytearray()
        assert held[0].state==[1] and held[2]==[0]
        if finish_case.startswith('late_'):assert late==[True]
finally:
    m._run_directory_observation=actual_run
    m._finished_declared_file_tail=actual_finish
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
