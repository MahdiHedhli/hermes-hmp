"""Actual opened leaf must match the literal earlier no-follow stat receipt."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'changed_file', 'foreign_predecessor',
                                 'missing_return', 'lost_return'))
def test_original_opened_leaf_identity(tmp_path, monkeypatch, case):
    script, fixture_mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nopened_case=' + repr(case) + '\n'
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
captured=[];commits=[];native_entries=[];opened_returns=[];observed={}
native_origin=None;active_role=None

def capture_factory(actual_owner,resource):
    operation,marker,payload=factory(actual_owner,resource)
    captured.append((operation,weakref.ref(payload)))
    return operation,marker,payload

def observe_native(frame,event,arg):
    if frame.f_code is m._produce_directory_metadata.__code__:
        if (event=='c_call' and native_origin is not None
                and (arg is native_origin.operations[3] or arg is native_origin.operations[4])):
            native_entries.append(active_role)
        if (event=='return' and arg is not None
                and arg.operation.resource.site[1]=='leaf_opened'):
            opened_returns.append((a._identity(arg.raw),arg.raw.st_mtime))
            if opened_case=='lost_return':raise RuntimeError('synthetic lost opened-leaf return')

def observe_site(actual_owner,resource,predecessor=None,baseline=None,eof=None):
    global native_origin,active_role
    if actual_owner is not owner:
        return actual_run(actual_owner,resource,predecessor,baseline,eof)
    held=resource.held_walk;metadata=held[5];ordinal=len(commits)
    registration=resource.registration
    active_role=resource.site[1]
    native_origin=registration.native_origin
    assert predecessor is (None if not commits else commits[-1])
    assert metadata.definitions[ordinal] is resource.site
    if active_role!='leaf_opened':
        assert active_role in ('directory','leaf_before')
        commit=actual_run(actual_owner,resource,predecessor,baseline,eof)
        assert metadata.commits[-1] is commit and captured[-1][1]() is None
        commits.append(commit)
        return commit
    predecessor=commits[-1]
    assert predecessor.site[1]=='leaf_before' and metadata.progress==[ordinal,None]
    assert predecessor.resource.held_walk is held
    before=tuple(registration.native_ledger.counts)
    if opened_case=='changed_file':
        leaf=dep_root/'__init__.py';st=os.stat(leaf,follow_symlinks=False)
        os.utime(leaf,ns=(st.st_atime_ns,st.st_mtime_ns+1000000000))
    if opened_case=='foreign_predecessor':predecessor=predecessor._replace()
    try:
        if opened_case=='missing_return':commit=actual_run(owner,resource)
        else:commit=actual_run(owner,resource,predecessor,baseline,eof)
    except a.ArtifactObservationError:
        assert opened_case!='normal'
        entered=opened_case in ('changed_file','lost_return')
        assert native_entries==['directory']*(ordinal-1)+['leaf_before']+(['leaf_opened'] if entered else [])
        assert tuple(registration.native_ledger.counts)==(before[0]+int(entered),before[1])
        assert metadata.progress[0]==ordinal and metadata.commits[-1] is commits[-1]
        assert commits[-1].operation.result.acknowledged[0] is commits[-1]
        if entered:
            assert captured[-1][0].state==[True,True,True]
            assert captured[-1][0].result.acknowledged==[None]
            assert registration.native_ledger.failed==[True]
            if opened_case=='lost_return':assert len(opened_returns)==1
        observed.update(refused=True,native_opened_entries=int(entered),cursor=ordinal)
        raise
    assert opened_case=='normal' and len(opened_returns)==1
    assert commit.identity==opened_returns[0][0]==commits[-1].identity
    assert commit.mtime==opened_returns[0][1]
    assert commit.consumer.predecessor is commits[-1]
    assert metadata.commits[-1] is commit and metadata.progress==[ordinal+1,None]
    assert commit.operation.result.acknowledged[0] is commit
    assert captured[-1][1]() is None and not gc.isenabled()
    assert native_entries==['directory']*(ordinal-1)+['leaf_before','leaf_opened']
    observed.update(actual_opened_ack=True,native_opened_entries=1,cursor=ordinal+1,
                    same_original_leaf_identity=True,same_result_mtime=True)
    raise RuntimeError('synthetic boundary after original opened-leaf ACK')


profile_before=sys.getprofile();gc_before=gc.isenabled()
assert profile_before is None
m._prepare_metadata_operation_with_custody=capture_factory
m._run_directory_observation=observe_site
gc.disable()
try:
    sys.setprofile(observe_native)
    try:owner.read()
    except RuntimeReadError:pass
    else:raise AssertionError('explicit injected opened-leaf boundary must refuse before reading')
    assert owner._failed and not owner._ready and owner._original_buffer==bytearray()
    assert observed and all(reference() is None for _,reference in captured)
    observed.update(case=opened_case,previous_acks=len(commits),payloads_reclaimed=True,
                    gc_disabled=not gc.isenabled(),walker_refused=True)
    diagnostic=Path(sys.argv[1])/'metadata-leaf-opened-stage.json'
    fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
finally:
    sys.setprofile(profile_before)
    m._prepare_metadata_operation_with_custody=factory
    m._run_directory_observation=actual_run
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
