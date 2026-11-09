"""Actual directory chain then no-follow leaf stat; no complete walker admission."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_predecessor', 'wrong_parent',
                                 'wrong_name', 'unsafe_mode'))
def test_original_declared_leaf_before(tmp_path, monkeypatch, case):
    script, fixture_mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nleaf_case=' + repr(case) + '\n'
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
original_stat=vars(a.StartupArtifactOwner)['_stat']
original_file_code=a.StartupArtifactOwner._file.__code__
captured=[];commits=[];native_entries=[];leaf_returns=[];observed={}
native_origin=None

def capture_factory(actual_owner,resource):
    operation,marker,payload=factory(actual_owner,resource)
    captured.append((operation,weakref.ref(payload)))
    return operation,marker,payload

def observe_native(frame,event,arg):
    if frame.f_code is m._produce_directory_metadata.__code__:
        if event=='c_call' and native_origin is not None:
            if arg is native_origin.operations[3]:native_entries.append(3)
            elif arg is native_origin.operations[4]:native_entries.append(4)
        if event=='return' and arg is not None and arg.operation.operation==3:
            leaf_returns.append((a._identity(arg.raw),arg.raw.st_mtime))

def at_original_fstat(actual_owner,fd,scope,registration=None):
    global native_origin
    if actual_owner is owner:
        frame=sys._getframe(1)
        try:
            assert frame.f_code is original_file_code
            held=frame.f_locals['native_walk'];metadata=held[5]
            assert metadata.definitions[len(commits)][1]=='directory'
            native_origin=registration.native_origin
            descriptor=frame.f_locals['row']
            resource=a._prepare_native_metadata_resource(owner,registration,held,descriptor,None)
            commit=m._run_directory_observation(owner,resource)
            assert commit.identity==a._identity(os.fstat(fd),True) and commit.mtime is None
            assert commit.consumer.predecessor is (None if not commits else commits[-1])
            assert metadata.commits[-1] is commit and captured[-1][1]() is None
            commits.append(commit)
        finally:frame=None
    return original_fstat(actual_owner,fd,scope,registration)

def at_original_stat(actual_owner,name,parent,scope,registration=None):
    if actual_owner is not owner:return original_stat(actual_owner,name,parent,scope,registration)
    frame=sys._getframe(1)
    try:
        assert frame.f_code is original_file_code
        held=frame.f_locals['native_walk'];metadata=held[5]
        ordinal=len(commits)
        assert metadata.progress==[ordinal,None]
        assert metadata.definitions[ordinal][1]=='leaf_before'
        descriptor=frame.f_locals['held'][-1][0]
        resource=a._prepare_native_metadata_resource(owner,registration,held,descriptor,name)
        before=tuple(registration.native_ledger.counts)
        if leaf_case=='copied_predecessor':metadata.commits[-1]=commits[-1]._replace()
        if leaf_case=='wrong_parent':
            other=frame.f_locals['held'][-2][0]
            resource=resource._replace(descriptor=other,arguments=(name,other.fd))
        if leaf_case=='wrong_name':resource=resource._replace(arguments=('foreign.py',parent))
        if leaf_case=='unsafe_mode':os.chmod(dep_root/'__init__.py',0o666)
        try:commit=m._run_directory_observation(owner,resource)
        except a.ArtifactObservationError:
            assert leaf_case!='normal'
            entered=leaf_case=='unsafe_mode'
            assert native_entries==[4]*ordinal+([3] if entered else [])
            assert tuple(registration.native_ledger.counts)==(before[0]+int(entered),before[1])
            assert metadata.progress[0]==ordinal
            assert all(operation.result.acknowledged[0] is original
                       for operation,original in zip((c.operation for c in commits),commits))
            if entered:
                assert captured[-1][0].state==[True,True,True]
                assert captured[-1][0].result.acknowledged==[None]
                assert registration.native_ledger.failed==[True]
            observed.update(refused=True,native_leaf_entries=int(entered),cursor=ordinal)
            raise
        assert leaf_case=='normal' and len(leaf_returns)==1
        assert commit.identity==leaf_returns[0][0] and commit.mtime==leaf_returns[0][1]
        assert len(commit.identity)==9 and type(commit.mtime) in (int,float)
        assert commit.consumer.predecessor is commits[-1]
        assert metadata.commits[-1] is commit and metadata.progress==[ordinal+1,None]
        assert commit.operation.result.acknowledged[0] is commit
        assert captured[-1][1]() is None and not gc.isenabled()
        assert native_entries==[4]*ordinal+[3]
        observed.update(actual_leaf_ack=True,native_leaf_entries=1,cursor=ordinal+1,
                        same_result_identity=True,same_result_mtime=True)
        raise RuntimeError('synthetic boundary after original leaf-before ACK')
    finally:frame=None

profile_before=sys.getprofile();gc_before=gc.isenabled()
assert profile_before is None
m._prepare_metadata_operation_with_custody=capture_factory
a.StartupArtifactOwner._fstat=at_original_fstat
a.StartupArtifactOwner._stat=at_original_stat
gc.disable()
try:
    sys.setprofile(observe_native)
    try:owner.read()
    except RuntimeReadError:pass
    else:raise AssertionError('incomplete metadata walker must remain refused')
    assert owner._failed and not owner._ready and owner._original_buffer==bytearray()
    assert observed and all(reference() is None for _,reference in captured)
    observed.update(case=leaf_case,directory_acks=len(commits),payloads_reclaimed=True,
                    gc_disabled=not gc.isenabled(),walker_refused=True)
    diagnostic=Path(sys.argv[1])/'metadata-leaf-before-stage.json'
    fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
finally:
    sys.setprofile(profile_before)
    m._prepare_metadata_operation_with_custody=factory
    a.StartupArtifactOwner._fstat=original_fstat
    a.StartupArtifactOwner._stat=original_stat
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
