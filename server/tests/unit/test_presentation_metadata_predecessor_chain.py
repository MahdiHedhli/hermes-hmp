"""Two real synthetic directory observations; the incomplete walker stays refused."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('mutation', ('normal', 'copied_predecessor', 'missing_predecessor'))
def test_original_predecessor_chain_before_second_native_call(tmp_path, monkeypatch, mutation):
    script, fixture_mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nhistory_case=' + repr(mutation) + '\n'
    script += r'''
import gc, os, weakref
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner, RuntimeReadError
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_native_metadata as m
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
factory=m._prepare_metadata_operation_with_custody
original_fstat=vars(a.StartupArtifactOwner)['_fstat']
original_file_code=a.StartupArtifactOwner._file.__code__
captured=[];commits=[];native_entries=[];observed={}
native_callee=None
def capture_factory(actual_owner,resource):
    triple=factory(actual_owner,resource)
    operation,marker,payload=triple
    assert actual_owner is owner
    captured.append((operation,weakref.ref(payload)))
    return triple
def observe_native(frame,event,arg):
    if (event=='c_call' and arg is native_callee
            and frame.f_code is m._produce_directory_metadata.__code__):
        native_entries.append(True)
def at_original_fstat(actual_owner,fd,scope,registration=None):
    global native_callee
    frame=None
    if actual_owner is owner and len(commits)<2:
        frame=sys._getframe(1)
        try:
            assert frame.f_code is original_file_code
            held=frame.f_locals['native_walk']
            descriptor=frame.f_locals['row']
            metadata=held[5]
            ordinal=len(commits)
            assert metadata.progress==[ordinal,None]
            assert len(metadata.commits)==ordinal
            native_callee=registration.native_origin.operations[4]
            resource=a._prepare_native_metadata_resource(owner,registration,held,descriptor,None)
            before=tuple(registration.native_ledger.counts)
            if ordinal==1:
                assert metadata.commits[0] is commits[0]
                if history_case=='copied_predecessor':metadata.commits[0]=commits[0]._replace()
                if history_case=='missing_predecessor':metadata.commits.clear()
            try:commit=m._run_directory_observation(owner,resource,
                                                    None if not commits else commits[-1])
            except a.ArtifactObservationError:
                assert ordinal==1 and history_case!='normal' and len(native_entries)==1
                assert tuple(registration.native_ledger.counts)==before
                assert captured[-1][0].state[:2]==[False,False]
                assert captured[-1][0].result.acknowledged==[None]
                observed.update(second_refused=True,second_uncharged=True,
                                original_ack=(commits[0].operation.result.acknowledged[0]
                                              is commits[0]),
                                foreign_history_preserved=(len(metadata.commits)==0
                                    if history_case=='missing_predecessor'
                                    else metadata.commits[0] is not commits[0]),
                                cursor=metadata.progress[0])
                raise
            assert len(native_entries)==ordinal+1
            assert metadata.commits[ordinal] is commit
            assert commit.operation.result.acknowledged[0] is commit
            assert commit.consumer.predecessor is (None if ordinal==0 else commits[0])
            assert captured[-1][1]() is None and not gc.isenabled()
            commits.append(commit)
            if ordinal==1:
                assert history_case=='normal' and metadata.progress==[2,None]
                observed.update(second_ack=True,cursor=2,
                                original_chain=commit.consumer.predecessor is metadata.commits[0])
                # Stop this disposable old-walker fixture without manufacturing
                # completion or refunding either actual metadata operation.
                raise RuntimeError('synthetic boundary after second actual directory ACK')
        finally:frame=None
    return original_fstat(actual_owner,fd,scope,registration)
profile_before=sys.getprofile();gc_before=gc.isenabled()
assert profile_before is None
m._prepare_metadata_operation_with_custody=capture_factory
a.StartupArtifactOwner._fstat=at_original_fstat
gc.disable()
try:
    sys.setprofile(observe_native)
    try:owner.read()
    except RuntimeReadError:pass
    else:raise AssertionError('incomplete metadata walker must remain refused')
    assert owner._failed and not owner._ready and owner._original_buffer==bytearray()
    assert len(captured)==2 and all(reference() is None for _,reference in captured)
    if history_case=='normal':
        assert observed['second_ack'] and observed['original_chain'] and len(native_entries)==2
    else:
        assert observed['second_refused'] and observed['second_uncharged']
        assert observed['original_ack'] and observed['foreign_history_preserved']
        assert observed['cursor']==1 and len(native_entries)==1
    observed.update(history_case=history_case,engine_native_entries=len(native_entries),
                    payloads_reclaimed=True,gc_disabled=not gc.isenabled(),walker_refused=True)
    diagnostic=Path(sys.argv[1])/'metadata-predecessor-chain-stage.json'
    diagnostic_fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(diagnostic_fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
finally:
    sys.setprofile(profile_before)
    m._prepare_metadata_operation_with_custody=factory
    a.StartupArtifactOwner._fstat=original_fstat
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
