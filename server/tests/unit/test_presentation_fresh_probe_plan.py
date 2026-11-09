"""Original fresh-probe DATA binding, before any probe filesystem operation."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_owner_plan', 'foreign_cursor',
                                 'foreign_pending', 'foreign_history', 'reallocate'))
def test_original_fresh_probe_plan(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\nplan_case=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.cache_probe import RuntimeCacheProbeOwner,CacheProbeError
from hmp_startup import probe_metadata as pm
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeCacheProbeOwner.retain(continuation,index)
scope=owner._origin;original=scope.native_probe_plan
assert type(original) is pm._FreshProbePlan and owner._probe_plan is original
assert original.selected is scope.parent[1] and original.selected.plan_row is rows[index].plan_row
assert original.path is original.selected.plan_row.location.path
assert original.components==('/',*original.path[1:].split('/'))
assert original.proof is original.selected.proof and original.context is scope.context
assert len(original.definitions)==len(original.variants)==6*len(original.components)
assert 'no-admission' in repr(original)
assert pm._fresh_probe_plan_tail(owner,scope,original) is original
registration=owner._native_scope_registration;ledger=registration.native_ledger
before=(tuple(ledger.counts),len(ledger.attempts),tuple(scope.records))
native_calls=[];foreign_hooks=[];foreign=object()
class ForeignCursor:
    def __eq__(self,other):foreign_hooks.append('eq');raise AssertionError('foreign comparison')
    def __index__(self):foreign_hooks.append('index');raise AssertionError('foreign index')
native=registration.native_origin
def observe_native(frame,event,arg):
    if event=='c_call' and any(arg is native.operations[i] for i in (0,1,3,4,5)):
        native_calls.append(True)
prior=sys.getprofile();assert prior is None
sys.setprofile(observe_native)
try:
    if plan_case=='copied_owner_plan':owner._probe_plan=original._replace()
    elif plan_case=='foreign_cursor':original.progress[0]=ForeignCursor()
    elif plan_case=='foreign_pending':original.progress[1]=foreign
    elif plan_case=='foreign_history':original.commits.append(foreign)
    if plan_case=='reallocate':
        try:pm._new_fresh_probe_plan(owner,original.root,original.selected,original.context)
        except pm.ProbePlanError:pass
        else:raise AssertionError('original retain plan reallocated after retain')
    elif plan_case!='normal':
        try:owner.observe()
        except CacheProbeError as exc:
            assert exc.__context__ is None and exc.__cause__ is None
        else:raise AssertionError('foreign original-plan mirrors admitted probe work')
        assert not owner._started and not owner._failed and not owner._ready
        if plan_case=='copied_owner_plan':assert owner._probe_plan is not original
        elif plan_case=='foreign_cursor':assert type(original.progress[0]) is ForeignCursor
        elif plan_case=='foreign_pending':assert original.progress[1] is foreign
        else:assert original.commits==[foreign]
    else:assert pm._fresh_probe_plan_tail(owner,scope,original) is original
    assert native_calls==[] and foreign_hooks==[]
    assert before==(tuple(ledger.counts),len(ledger.attempts),tuple(scope.records))
    assert owner._bytes_read==0 and scope.native_probe_plan is original
finally:
    sys.setprofile(prior)
    # Restore only disposable fixture DATA before the separate positive path.
    # No production helper resets a cursor, refunds work or repairs permissions.
    owner._probe_plan=original
    original.progress[:]=[0,None];original.commits.clear()
owner.observe()
assert owner._ready and owner.current_binding()[2].state=='missing_component'
assert owner._bytes_read==0 and scope.native_probe_plan is original
assert original.progress==[0,None] and original.commits==[] and original.ancestors==[]
assert all(row.closed and row.close_attempted and not row.unknown for row in scope.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
