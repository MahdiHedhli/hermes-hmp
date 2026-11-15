"""Actual EOF receipt survives exactly accounted post-read metadata, not new reads."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'empty', 'missing_eof', 'copied_eof',
                                 'missing_baseline', 'changed_file', 'lost_return',
                                 'foreign_baseline_resource', 'foreign_baseline_variant'))
def test_original_postread_receipts(tmp_path, monkeypatch, case):
    script, fixture_mutation = operator_composed_script('links')
    if case == 'empty':
        original = r'(dep_root / "__init__.py").write_text("VALUE = 1\n")'
        assert script.count(original) == 1
        script = script.replace(original, '(dep_root / "__init__.py").write_text("")')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\npost_case=' + repr(case) + '\n'
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
captured=[];commits=[];native_entries=[];post_returns=[];observed={};read_entries=[]
baselines=[];eofs=[];native_origin=None;active_role=None;foreign_hooks=[]
class ForeignBaseline:
    def __getattr__(self,name):
        foreign_hooks.append(name)
        raise RuntimeError('synthetic foreign baseline hook')

def capture_factory(actual_owner,resource):
    operation,marker,payload=factory(actual_owner,resource)
    captured.append((operation,weakref.ref(payload)))
    return operation,marker,payload

def observe_native(frame,event,arg):
    if (event=='c_call' and frame.f_code is a.StartupArtifactOwner._read.__code__
            and native_origin is not None and arg is native_origin.operations[1]):
        read_entries.append(True)
    if frame.f_code is m._produce_directory_metadata.__code__:
        if (event=='c_call' and native_origin is not None
                and (arg is native_origin.operations[3] or arg is native_origin.operations[4])):
            native_entries.append(active_role)
        if (event=='return' and arg is not None
                and arg.operation.resource.site[1]=='leaf_after_read'):
            post_returns.append((a._identity(arg.raw),arg.raw.st_mtime))
            if post_case=='lost_return':raise RuntimeError('synthetic lost post-read return')

def observe_site(actual_owner,resource,predecessor=None,baseline=None,eof=None):
    global native_origin,active_role
    if actual_owner is not owner:
        return actual_run(actual_owner,resource,predecessor,baseline,eof)
    held=resource.held_walk;metadata=held[5];ordinal=len(commits)
    active_role=resource.site[1];operation=resource.site[0]
    registration=resource.registration
    assert metadata.definitions[ordinal] is resource.site
    native_origin=registration.native_origin
    assert predecessor is (None if not commits else commits[-1])
    if active_role!='leaf_after_read':
        commit=actual_run(owner,resource,predecessor,baseline,eof)
        if active_role=='leaf_before':baselines.append(commit)
        assert metadata.commits[-1] is commit and captured[-1][1]() is None
        commits.append(commit)
        return commit
    assert len(baselines)==1 and type(eof) is a._NativeRuntimeReadCommit
    assert baseline is baselines[0]
    assert eof.eof is True and eof.remaining==0 and eof.count[2]==resource.variant.expected.size
    if not eofs:eofs.append(eof)
    assert eofs[0] is eof
    baseline=baselines[0]
    before=tuple(registration.native_ledger.counts)
    if operation==4:
        assert a._native_runtime_read_closed_tail(owner,eof,eof.step) is eof
        if post_case=='changed_file':
            leaf=dep_root/'__init__.py';st=os.stat(leaf,follow_symlinks=False)
            os.utime(leaf,ns=(st.st_atime_ns,st.st_mtime_ns+1000000000))
    if post_case=='missing_eof':eof=None
    if post_case=='copied_eof':eof=eof._replace()
    if post_case=='missing_baseline':baseline=None
    if post_case=='foreign_baseline_resource':
        baseline=baseline._replace(resource=ForeignBaseline())
    if post_case=='foreign_baseline_variant':
        baseline=baseline._replace(resource=baseline.resource._replace(variant=ForeignBaseline()))
    try:commit=actual_run(owner,resource,predecessor,baseline,eof)
    except a.ArtifactObservationError:
        assert post_case not in ('normal','empty') and operation==4
        entered=post_case in ('changed_file','lost_return')
        assert native_entries.count('leaf_after_read')==int(entered)
        assert tuple(registration.native_ledger.counts)==(before[0]+int(entered),before[1])
        assert metadata.progress[0]==ordinal and metadata.commits[-1] is commits[-1]
        assert eofs[0].result.acknowledged[0] is eofs[0]
        assert eofs[0].step.eof==[True] and eofs[0].result.raw[0] is eofs[0].result.unset
        if entered:
            assert captured[-1][0].state==[True,True,True]
            assert captured[-1][0].result.acknowledged==[None]
            assert registration.native_ledger.failed==[True]
        observed.update(refused=True,post_entries=int(entered),actual_eof_preserved=True)
        raise
    assert post_case in ('normal','empty')
    assert commit.identity==baselines[0].identity==post_returns[-1][0]
    assert commit.consumer.predecessor is commits[-1]
    assert commit.consumer.eof is eofs[0] and commit.consumer.baseline is baselines[0]
    assert metadata.commits[-1] is commit and captured[-1][1]() is None
    commits.append(commit)
    assert a._native_runtime_read_history_tail(owner,eofs[0],eofs[0].step) is eofs[0]
    try:a._native_runtime_read_closed_tail(owner,eofs[0],eofs[0].step)
    except a.ArtifactObservationError:pass
    else:raise AssertionError('later metadata must not renew current read closure')
    if operation==3:
        assert native_entries.count('leaf_after_read')==2 and len(post_returns)==2
        if post_case=='empty':
            assert eofs[0].count[2]==0 and read_entries==[True]
            assert eofs[0].eof is True and eofs[0].step.eof==[True]
            assert eofs[0].operation.state==[True,True,False]
            assert eofs[0].result.acknowledged[0] is eofs[0]
            observed.update(empty_actual_eof=True,actual_read_calls=1)
        observed.update(actual_post_pair_ack=True,post_entries=2,
                        literal_eof_retained=True,current_read_closure_refused=True)
        raise RuntimeError('synthetic boundary after actual post-read pair ACK')
    return commit

profile_before=sys.getprofile();gc_before=gc.isenabled()
assert profile_before is None
m._prepare_metadata_operation_with_custody=capture_factory
m._run_directory_observation=observe_site
gc.disable()
try:
    sys.setprofile(observe_native)
    try:owner.read()
    except RuntimeReadError:pass
    else:raise AssertionError('explicit injected boundary must refuse before final ancestors')
    assert owner._failed and not owner._ready and owner._original_buffer==bytearray()
    assert observed and all(reference() is None for _,reference in captured)
    observed.update(case=post_case,metadata_acks=len(commits),payloads_reclaimed=True,
                    gc_disabled=not gc.isenabled(),walker_refused=True,foreign_hooks=list(foreign_hooks))
    diagnostic=Path(sys.argv[1])/'metadata-postread-stage.json'
    fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(observed,stream,sort_keys=True)
    assert foreign_hooks==[], 'typed baseline must refuse before foreign hooks'
finally:
    sys.setprofile(profile_before)
    m._prepare_metadata_operation_with_custody=factory
    m._run_directory_observation=actual_run
    if gc_before:gc.enable()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, fixture_mutation)
