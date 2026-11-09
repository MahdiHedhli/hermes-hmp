"""Complete real runtime-source walk and causal late finish refusal."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'empty', 'lost_final', 'late_link', 'late_ack', 'foreign_ordinal',
                                 'copied_directory_baseline', 'wrong_directory_baseline',
                                 'foreign_root_parent', 'changed_directory'))
def test_actual_complete_metadata_finish(tmp_path, monkeypatch, case):
    script, fixture_mutation = operator_composed_script('links')
    if case == 'empty':
        original = r'(dep_root / "__init__.py").write_text("VALUE = 1\n")'
        assert script.count(original) == 1
        script = script.replace(original, '(dep_root / "__init__.py").write_text("")')
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
commits=[];finish_calls=[];late=[];foreign_hooks=[];observed={};early_held=[]
early_cases=('copied_directory_baseline','wrong_directory_baseline','foreign_root_parent','changed_directory')
foreign=object()
class ForeignOrdinal:
    def __eq__(self,other):
        foreign_hooks.append('eq')
        raise RuntimeError('synthetic final ordinal hook')

def observe_run(actual_owner,*args):
    resource=args[0]
    if actual_owner is owner and finish_case in early_cases:
        site=resource.site
        target=(site[1]=='directory_after_hash' and (
            (finish_case in ('copied_directory_baseline','wrong_directory_baseline') and site[0]==4 and site[2]==0)
            or (finish_case=='foreign_root_parent' and site[0]==3 and site[2]==0)
            or (finish_case=='changed_directory' and site[0]==4 and site[2]==len(resource.held_walk[0].components)-2)))
        if target:
            predecessor,baseline,eof=args[1:]
            held=resource.held_walk;metadata=held[5]
            assert predecessor is commits[-1] and eof.eof is True
            assert baseline is commits[site[2]] and baseline.site==(4,'directory',site[2])
            original_resource=resource
            if finish_case=='copied_directory_baseline':baseline=baseline._replace()
            elif finish_case=='wrong_directory_baseline':baseline=commits[1]
            elif finish_case=='foreign_root_parent':
                assert resource.descriptor is None and resource.arguments==('/',None)
                other=baseline.resource.descriptor
                resource=resource._replace(descriptor=other,arguments=('/',other.fd))
            before=tuple(resource.registration.native_ledger.counts)
            attempts=len(resource.registration.native_ledger.attempts)
            entries=[];mode=None
            if finish_case=='changed_directory':
                mode=os.stat(dep_root,follow_symlinks=False).st_mode&0o777
                os.chmod(dep_root,mode^0o010)
            def target_native(frame,event,arg):
                if (event=='c_call' and frame.f_code is m._produce_directory_metadata.__code__
                        and arg is resource.registration.native_origin.operations[site[0]]):entries.append(True)
            prior=sys.getprofile();assert prior is None
            early_held.append(held)
            sys.setprofile(target_native)
            try:
                try:actual_run(actual_owner,resource,predecessor,baseline,eof)
                except a.ArtifactObservationError:
                    entered=int(finish_case=='changed_directory')
                    ledger=resource.registration.native_ledger
                    assert entries==[True]*entered
                    assert tuple(ledger.counts)==(before[0]+entered,before[1])
                    assert len(ledger.attempts)==attempts+entered
                    assert metadata.progress==[len(commits),None]
                    assert metadata.commits[-1] is predecessor
                    assert predecessor.operation.result.acknowledged[0] is predecessor
                    assert eof.result.acknowledged[0] is eof and eof.result.raw[0] is eof.result.unset
                    if entered:
                        operation=ledger.attempts[-1]
                        assert operation.state==[True,True,True] and operation.result.acknowledged==[None]
                        assert ledger.failed==[True]
                    observed.update(early_refused=True,target_native_entries=entered,
                                    literal_baseline_retained=original_resource.held_walk is held,
                                    actual_eof_preserved=True)
                    raise
                else:raise AssertionError('altered final directory inputs must refuse')
            finally:
                sys.setprofile(prior)
                if mode is not None:os.chmod(dep_root,mode)
    result=actual_run(actual_owner,*args)
    if actual_owner is owner:
        commits.append(result)
        if finish_case=='lost_final' and result.next_ordinal==len(result.resource.metadata.definitions):
            raise RuntimeError('synthetic lost actual final metadata return')
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
    if finish_case in early_cases:
        assert not finish_calls and len(early_held)==1 and observed.get('early_refused')
        held=early_held[0];last=commits[-1]
        assert held[5].progress==[len(commits),None]
    elif finish_case=='lost_final':
        assert not finish_calls and commits
        last=commits[-1];held=last.resource.held_walk
        assert last.next_ordinal==len(held[5].definitions)
        assert held[5].progress==[len(held[5].definitions),None]
        observed.update(actual_last_return_lost=True,complete_native_sequence=True)
    else:
        assert len(finish_calls)==1
        held,last=finish_calls[0]
    observed.update(case=finish_case,metadata_sites=len(commits),
                    complete_definition_sequence=finish_case not in early_cases,late_events=len(late),
                    foreign_hooks=list(foreign_hooks),
                    walk_state=held[0].state[0],file_progress=held[2][0],
                    gc_disabled=not gc.isenabled())
    if finish_case=='late_link':assert commits[0].consumer.custody[2][0] is foreign
    if finish_case=='late_ack':assert commits[0].operation.result.acknowledged[0] is foreign
    path=Path(sys.argv[1])/'metadata-complete-finish-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
    assert foreign_hooks==[], 'final ordinal must refuse before foreign comparison'
    if finish_case in ('normal','empty'):
        assert observed.get('finish_accepted') and observed.get('owner_ready')
        assert held[0].state==[2] and held[2]==[1]
        assert bytes(owner._original_buffer)==(dep_root/'__init__.py').read_bytes()
        if finish_case=='empty':
            assert owner._bytes_read==0 and last.consumer.eof.eof is True
            assert last.consumer.eof.operation.state==[True,True,False]
            assert last.consumer.eof.result.acknowledged[0] is last.consumer.eof
        owner.release();assert owner._original_buffer==bytearray()
    else:
        assert observed.get('owner_refused')
        assert observed.get('finish_refused') or finish_case=='lost_final' or finish_case in early_cases
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
