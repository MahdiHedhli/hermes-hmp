"""Real full probe engine prototype; no image publication or live host traffic."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('missing', 'directory', 'declared'))
def test_complete_fresh_probe_engine(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    if case in ('directory', 'declared'):
        setup = r'''
import importlib.util
prepared_cache=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
prepared_cache.parent.mkdir(mode=0o700)
if ENGINE_CASE=='directory':prepared_cache.mkdir(mode=0o700)
else:prepared_cache.write_bytes(b'SYNTHETIC_DECLARED_CACHE_NOT_READ')
prepared_cache.chmod(0o700 if ENGINE_CASE=='directory' else 0o600)
'''.replace('ENGINE_CASE', repr(case))
        script = script.replace('import sample_dep\n', 'import sample_dep\n' + setup, 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\nengine_case=' + repr(case) + '\n'
    script += r'''
import gc,os
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import probe_native as engine
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
seen=[];facts={}
def exercise(frame):
    if frame.f_locals['self'] is not owner or seen:return
    seen.append(True)
    scope=frame.f_locals['s'];reg=frame.f_locals['native_registration']
    plan=scope.native_probe_plan
    before=(reg.native_ledger.counts[0],reg.native_ledger.counts[1],len(reg.native_ledger.attempts))
    old_gc=gc.isenabled();gc.disable()
    try:
        result=engine._run_fresh_probe(owner,scope,reg,plan)
        actual=owner._probe_execution
        expected=('missing_component' if engine_case=='missing' else
                  'directory' if engine_case=='directory' else 'declared_regular')
        assert result[0]==expected and actual.outcome[0] is result
        assert actual.finished==[True] and actual.failed==[False]
        assert actual.pending==[None] and actual.next_site==[len(plan.definitions)]
        assert actual.history and all(type(commit) is engine._ProbeCommit for commit in actual.history)
        assert [commit.sequence for commit in actual.history]==list(range(len(actual.history)))
        missing=[commit for commit in actual.history if commit.category=='reported_missing']
        if engine_case=='missing':
            assert len(missing)==2 and missing[1].site==missing[0].site+2
            assert all(commit.consumer.operation.state==[True,False,True] for commit in missing)
        else:assert missing==[]
        assert all(commit.consumer.operation.ended==[True] for commit in actual.history)
        assert all(commit.consumer.custody[0].reference_call(
                   commit.consumer.custody[1].reference) is None for commit in actual.history)
        assert len(scope.records)==len(actual.opened)>0
        assert all(row.closed and row.close_attempted and not row.unknown for row in scope.records)
        assert reg.native_ledger.counts[1]==before[1]
        assert reg.native_ledger.counts[0]-before[0]==len(actual.history)+2*len(actual.opened)
        assert len(reg.native_ledger.attempts)-before[2]==len(actual.history)+len(actual.opened)
        assert reg.native_ledger.failed==[False] and reg.native_ledger.inflight==[None]
        assert reg.native_phase.current[0] is reg.native_phase.idle and reg.native_phase.result==[None]
        assert owner._bytes_read==0 and owner._count_cell is actual.count
        assert owner._fact is None and not owner._ready and not gc.isenabled()
        facts.update(case=engine_case,state=result[0],observations=len(actual.history),
                     opened=len(actual.opened),diagnostics=len(missing),boundary_complete=True)
    finally:
        if old_gc:gc.enable()
    path=Path(sys.argv[1])/'fresh-probe-engine-stage.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(facts,stream,sort_keys=True)
    raise RuntimeError('synthetic boundary after complete prototype before legacy publication')
trace_synthetic_boundary(RuntimeCacheProbeOwner._observe_owned.__code__,
                         'plan = s.native_probe_plan',exercise)
try:owner.observe()
except CacheProbeError:pass
else:raise AssertionError('prototype boundary must not publish legacy completion')
assert seen==[True] and facts.get('boundary_complete') is True
assert owner._failed and not owner._ready and owner._bytes_read==0
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
