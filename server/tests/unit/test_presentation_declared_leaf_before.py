"""Actual integrated directory chain and no-follow leaf stat causal checks."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_predecessor', 'wrong_parent',
                                 'wrong_name', 'unsafe_mode', 'coherent_predecessor',
                                 'missing_return', 'lost_return'))
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
actual_run=m._run_directory_observation
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
            if leaf_case=='lost_return':raise RuntimeError('synthetic lost actual leaf return')

def observe_site(actual_owner,resource,predecessor=None,baseline=None,eof=None):
    global native_origin
    if actual_owner is not owner:
        return actual_run(actual_owner,resource,predecessor,baseline,eof)
    held=resource.held_walk;metadata=held[5];ordinal=len(commits)
    registration=resource.registration
    native_origin=registration.native_origin
    assert metadata.definitions[ordinal] is resource.site
    assert predecessor is (None if not commits else commits[-1])
    if resource.site[1]=='directory':
        commit=actual_run(owner,resource,predecessor,baseline,eof)
        assert commit.identity==a._identity(os.fstat(resource.descriptor.fd),True)
        assert commit.mtime is None and commit.consumer.predecessor is predecessor
        assert metadata.commits[-1] is commit and captured[-1][1]() is None
        commits.append(commit)
        return commit
    assert resource.site[1]=='leaf_before' and metadata.progress==[ordinal,None]
    name,parent=resource.arguments
    before=tuple(registration.native_ledger.counts)
    if leaf_case=='copied_predecessor':metadata.commits[-1]=commits[-1]._replace()
    if leaf_case=='coherent_predecessor':
        replacement=commits[-1]._replace()
        metadata.commits[-1]=replacement
        commits[-1].consumer.commit[0]=replacement
        commits[-1].operation.result.acknowledged[0]=replacement
    if leaf_case=='wrong_parent':
        other=resource.descriptor.allocation.parent
        resource=resource._replace(descriptor=other,arguments=(name,other.fd))
    if leaf_case=='wrong_name':resource=resource._replace(arguments=('foreign.py',parent))
    if leaf_case=='unsafe_mode':os.chmod(dep_root/'__init__.py',0o666)
    try:
        if leaf_case=='missing_return':commit=actual_run(owner,resource)
        else:commit=actual_run(owner,resource,predecessor,baseline,eof)
    except a.ArtifactObservationError:
        assert leaf_case!='normal'
        entered=leaf_case in ('unsafe_mode','lost_return')
        assert native_entries==[4]*ordinal+([3] if entered else [])
        assert tuple(registration.native_ledger.counts)==(before[0]+int(entered),before[1])
        assert metadata.progress[0]==ordinal
        if leaf_case=='coherent_predecessor':
            assert metadata.commits[-1] is replacement
            assert commits[-1].consumer.commit[0] is replacement
            assert commits[-1].operation.result.acknowledged[0] is replacement
            assert replacement is not commits[-1]
        else:
            assert all(operation.result.acknowledged[0] is original
                       for operation,original in zip((c.operation for c in commits),commits))
        if entered:
            assert captured[-1][0].state==[True,True,True]
            assert captured[-1][0].result.acknowledged==[None]
            assert registration.native_ledger.failed==[True]
            if leaf_case=='lost_return':assert len(leaf_returns)==1
        observed.update(refused=True,native_leaf_entries=int(entered),cursor=ordinal)
        raise
    if leaf_case=='coherent_predecessor':
        observed.update(unexpected_coherent_copy_accepted=True,
            leaf_ack=commit.operation.result.acknowledged[0] is commit,
            adopted_copy=commit.consumer.predecessor is replacement,
            actual_previous_return_distinct=commits[-1] is not replacement,
            native_leaf_entries=native_entries.count(3))
        raise RuntimeError('synthetic coherent-copy control reached actual leaf ACK')
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


profile_before=sys.getprofile();gc_before=gc.isenabled()
assert profile_before is None
m._prepare_metadata_operation_with_custody=capture_factory
m._run_directory_observation=observe_site
gc.disable()
try:
    sys.setprofile(observe_native)
    try:owner.read()
    except RuntimeReadError:pass
    else:raise AssertionError('explicit injected leaf-before boundary must refuse before opening')
    assert owner._failed and not owner._ready and owner._original_buffer==bytearray()
    assert observed and all(reference() is None for _,reference in captured)
    observed.update(case=leaf_case,directory_acks=len(commits),payloads_reclaimed=True,
                    gc_disabled=not gc.isenabled(),walker_refused=True)
    diagnostic=Path(sys.argv[1])/'metadata-leaf-before-stage.json'
    fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
    assert not observed.get('unexpected_coherent_copy_accepted',False), 'coherent current mirrors replaced literal prior return'
finally:
    sys.setprofile(profile_before)
    m._prepare_metadata_operation_with_custody=factory
    m._run_directory_observation=actual_run
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
