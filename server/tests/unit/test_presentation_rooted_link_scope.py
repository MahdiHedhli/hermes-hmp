"""Actual execution-only root route; prefix acceptance, not native startup."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('fault', (
    'normal', 'inputs_copy', 'snapshot_cell_copy', 'entry_origin_copy',
    'started_copy', 'owner_scope_copy', 'late_callee_code',
    'initial_guard_export', 'initial_guard_code', 'initial_engine_export',
    'last_owner_scope_copy', 'last_snapshot_subclass', 'last_snapshot_class_key',
))
def test_actual_link_scope_roots_survive_complete_guard(tmp_path, monkeypatch, fault):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.index('original_bytes=plugin._bytes_read')]
    script += '\nfault=' + repr(fault) + '\n'
    script += r'''
from hmp_plugin import presentation_native_link as nl
retained=EntryFileSnapshotOwner.retain_runtime_link_files(entry,recipe,plugin)
checker=nl._native_link_scope_current
checker_code=checker.__code__
guard_function=a.StartupArtifactOwner._guard
guard_code=guard_function.__code__
engine_function=nl._engine_origin_tail
engine_code=engine_function.__code__
tail_code=a._native_work_registration_tail.__code__
pin_code=nl._effect_pin.__code__
ledger=entry._scope.native_files.ledger
native_operations=entry._scope.native_files.native.operations
injected=[];completed=[];foreign_calls=[];later_effects=[];caught=[];stages=[];mutation_complete=[];failure_frames=[];restores=[];later_closes=[]
class PrefixComplete(Exception):pass
def foreign(*args,**kwargs):
    foreign_calls.append(True)
    raise AssertionError('replaced Scope checker executed')
class ForeignEngine:
    def __getattribute__(self,name):
        foreign_calls.append('engine attribute')
        raise AssertionError('foreign engine attribute evaluated')
armed=[False]
class ForeignClassKey:
    def __hash__(self):return hash('__dict__')
    def __eq__(self,other):
        if armed[0]:
            foreign_calls.append('class key')
            raise AssertionError('foreign class key equality')
        return False
def prefix_state(local):
    execution=local['execution']
    return (tuple(ledger.counts),tuple(ledger.attempts),tuple(ledger.scopes),
            execution,tuple(execution.history),tuple(execution.actions),
            execution.cursor[0],tuple(execution.opened),tuple(execution.closed))
def observe(frame,event,result):
    if event=='c_call':
        if injected:
            if (result is native_operations[0] or result is native_operations[1]
                    or result is native_operations[3] or result is native_operations[4]
                    or result is native_operations[5]):later_effects.append(True)
            elif result is native_operations[2]:later_closes.append(True)
        return
    if event!='return':return
    code=frame.f_code
    if (code is not checker_code and code is not guard_code and code is not engine_code
            and code is not tail_code and code is not pin_code):return
    if code is checker_code:
        stages.append((frame.f_lineno,result is not None,sorted(frame.f_locals)))
    caller=frame.f_back
    if frame.f_code is checker_code and result is not None:
        assert result is frame.f_locals['scope']
        completed.append(True)
        if fault=='normal':
            # Deliberate complete-checker prefix stop, not full startup.
            raise PrefixComplete()
    if fault.startswith('initial_'):
        if (frame.f_code is engine_code and caller is not None
                and caller.f_code is checker_code and not injected):
            injected.append(prefix_state(caller.f_locals))
            if fault=='initial_guard_export':
                a.StartupArtifactOwner._guard=foreign
                assert vars(a.StartupArtifactOwner)['_guard'] is foreign
            elif fault=='initial_guard_code':
                guard_function.__code__=foreign.__code__
                assert guard_function.__code__ is foreign.__code__
            else:
                changed=ForeignEngine();nl._engine_origin_tail=changed
                assert vars(nl)['_engine_origin_tail'] is changed
            mutation_complete.append(True)
        return
    if fault.startswith('last_'):
        if (frame.f_code is tail_code and caller is not None
                and caller.f_code is checker_code and not injected):
            local=caller.f_locals
            injected.append(prefix_state(caller.f_locals))
            if fault=='last_owner_scope_copy':
                copied=local['scope']._replace()
                assert copied is not local['scope']
                vars(local['owner'])['_scope']=vars(local['owner'])['_origin']=copied
                assert vars(local['owner'])['_scope'] is copied
                assert vars(local['owner'])['_origin'] is copied
            elif fault=='last_snapshot_subclass':
                original=local['snapshot_kind']
                class CompatibleSnapshot(original):__slots__=()
                local['snapshot'].__class__=CompatibleSnapshot
                assert type(local['snapshot']) is CompatibleSnapshot
                restores.append(('snapshot',local['snapshot'],original))
            else:
                import gc
                kind=local['snapshot_kind'];view=vars(kind)
                dictionaries=[value for value in gc.get_referents(view) if type(value) is dict]
                assert len(dictionaries)==1
                names=dictionaries[0];descriptor=names.pop('__dict__')
                key=ForeignClassKey();names[key]=descriptor;armed[0]=True
                assert any(type(candidate) is ForeignClassKey for candidate in names)
                restores.append(('class_key',names,key,descriptor))
            mutation_complete.append(True)
        return
    if fault=='late_callee_code':
        if (frame.f_code is pin_code and result is checker and caller is not None
                and caller.f_code in (nl._resource_tail.__code__,nl._lifetime_tail.__code__)
                and not injected):
            assert checker.__code__ is checker_code
            assert type(result) is type(checker)
            injected.append(prefix_state(caller.f_locals))
            checker.__code__=foreign.__code__
            assert checker.__code__ is foreign.__code__
            mutation_complete.append(True)
        return
    if (frame.f_code is guard_code and caller is not None
            and caller.f_code is checker_code and not injected):
        local=caller.f_locals
        assert result is local['scope']
        assert local['execution'].registration is local['registration']
        assert local['resource'].execution is local['execution']
        assert local['runtime'].inputs is local['inputs']
        assert local['digest'].binding is local['binding']
        assert local['started'][5] is local['entry_origin']
        injected.append(prefix_state(caller.f_locals))
        if fault=='inputs_copy':
            copied=local['inputs']._replace()
            assert copied is not local['inputs']
            local['snapshot_names']['_inputs']=copied
            assert local['snapshot_names']['_inputs'] is copied
        elif fault=='snapshot_cell_copy':
            copied=tuple(list(local['snapshot_cell']))
            assert copied is not local['snapshot_cell']
            local['snapshot_names']['_root_cell']=copied
            assert local['snapshot_names']['_root_cell'] is copied
        elif fault=='entry_origin_copy':
            copied=local['entry_origin']._replace()
            assert copied is not local['entry_origin']
            local['entry_names']['_ENTRY_ORIGIN']=copied
            assert local['entry_names']['_ENTRY_ORIGIN'] is copied
        elif fault=='started_copy':
            copied=tuple(list(local['started']))
            assert copied is not local['started']
            local['entry_names']['_STARTED']=copied
            assert local['entry_names']['_STARTED'] is copied
        elif fault=='owner_scope_copy':
            copied=local['scope']._replace()
            assert copied is not local['scope']
            vars(local['owner'])['_scope']=vars(local['owner'])['_origin']=copied
            assert vars(local['owner'])['_scope'] is copied
            assert vars(local['owner'])['_origin'] is copied
        mutation_complete.append(True)
prior=sys.getprofile();assert prior is None and sys.gettrace() is None
sys.setprofile(observe)
try:
    EntryFileSnapshotOwner.complete(retained)
except EntryFilesError as error:
    caught.append(error)
    current=error
    for _ in range(12):
        if current is None:break
        trace=current.__traceback__;chain=[]
        while trace is not None:
            chain.append((trace.tb_frame.f_code.co_name,trace.tb_lineno));trace=trace.tb_next
        failure_frames.append((type(current).__name__,chain))
        current=current.__context__
finally:
    sys.setprofile(prior)
    checker.__code__=checker_code
    a.StartupArtifactOwner._guard=guard_function
    guard_function.__code__=guard_code
    nl._engine_origin_tail=engine_function
    armed[0]=False
    for row in restores:
        if row[0]=='snapshot':row[1].__class__=row[2]
        else:
            row[1].pop(row[2]);row[1]['__dict__']=row[3]
assert len(injected)==1 and len(caught)==1,(len(injected),len(caught),stages,failure_frames)
assert mutation_complete==[True]
assert bool(completed) is (fault=='normal'),(fault,completed)
assert caught[0].failed_owner is retained
assert retained._failed and not retained._ready and retained._fact_cell is None
assert entry._activation._artifact_owner._failed
assert foreign_calls==[] and later_effects==[]
assert ledger.inflight==[None]
counts,attempts,scopes,execution,history,actions,cursor,opened,closed=injected[0]
assert tuple(ledger.counts)==(counts[0]+counts[1],0),(counts,ledger.counts)
if fault!='normal':assert len(later_closes)==counts[1]
# A deliberate exception in the normal profile observer disables that observer;
# its cleanup is proved by exact accounting/receipts, not a C-call count.
assert len(ledger.attempts)==len(attempts)
assert all(current is original for current,original in zip(ledger.attempts,attempts,strict=True))
assert len(ledger.scopes)==len(scopes)
assert all(current is original for current,original in zip(ledger.scopes,scopes,strict=True))
assert len(execution.history)==len(history) and len(execution.actions)==len(actions)
assert all(current is original for current,original in zip(execution.history,history,strict=True))
assert all(current is original for current,original in zip(execution.actions,actions,strict=True))
assert execution.cursor[0] is cursor
assert len(execution.closed)==len(closed)+counts[1]
for descriptor in opened:
    receipt=descriptor.close.result[0]
    assert type(receipt) is tuple and len(receipt)==3
    assert receipt[0] is descriptor.close and receipt[1] is descriptor.fd and receipt[2] is None
    assert descriptor.close.state==[True,False] and descriptor.close.raw[0] is None
    assert any(current is receipt for current in execution.closed)
assert sys.getprofile() is None and sys.gettrace() is None
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


@pytest.mark.parametrize('location', ('origin', 'rows', 'row', 'row_name'))
def test_malformed_root_route_data_invokes_no_foreign_hooks(location):
    from hmp_plugin import presentation_native_link as link
    from hmp_plugin import presentation_startup_artifacts as artifacts

    hooks = []

    class Foreign:
        def __getitem__(self, key):
            hooks.append('getitem')
            raise AssertionError('foreign origin lookup')

        def __iter__(self):
            hooks.append('iter')
            raise AssertionError('foreign origin iteration')

    class ForeignName(str):
        def __eq__(self, other):
            hooks.append('eq')
            raise AssertionError('foreign row name comparison')

    value = Foreign()
    rows = value if location == 'rows' else (value,)
    if location == 'row_name':
        rows = ((ForeignName('_engine_origin_tail'),) + (None,) * 6,)
    origin = value if location == 'origin' else (None, None, rows, None, None, None)
    execution = tuple.__new__(link._LinkExecution, (None, None, None, origin) + (None,) * 17)
    resource = tuple.__new__(artifacts._NativeLinkMetadataResource, (None,) * 7)
    with pytest.raises(artifacts.ArtifactObservationError):
        link._native_link_scope_current(execution, resource)
    assert hooks == []
