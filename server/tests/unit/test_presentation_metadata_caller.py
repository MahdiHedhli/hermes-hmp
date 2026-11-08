"""Uninstalled fixed caller over an original synthetic native descriptor."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ['normal', 'lost_return', 'revoked_lost_return',
                                 'foreign_slot_lost_return', 'foreign_inner_lost_return',
                                 'late_marker_drift', 'disposal_revocation',
                                 'lost_return_interrupt_before', 'lost_return_interrupt_after'])
def test_fixed_directory_caller(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
import ast, gc, inspect, weakref
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_native_metadata as m
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
seen=[]
def exercise(frame):
    if frame.f_locals['self'] is not owner or seen:return
    walk=frame.f_locals['native_walk']
    registration=frame.f_locals['native_registration']
    descriptor=frame.f_locals['row']
    resource=a._prepare_native_metadata_resource(owner,registration,walk,descriptor,None)
    ledger,phase=registration.native_ledger,registration.native_phase
    counts=tuple(ledger.counts);attempts=len(ledger.attempts)
    preparation=tuple(ledger.preparation)
    metadata=walk[5]
    assert metadata.progress==[0,None]
    factory=m._prepare_metadata_operation_with_custody
    captured=[];returns=[];native_entries=[];foreign_inner=[]
    foreign_slot=object()
    activation_names=vars(walk[0].scope.activation)
    retired_before=activation_names['_retired']
    trace_before,profile_before=sys.gettrace(),sys.getprofile()
    assert trace_before is profile_before is None
    gc_before=gc.isenabled()
    producer_code=m._produce_directory_metadata.__code__
    ack_tail_code=m._acked_directory_commit_tail.__code__
    caller_code=m._run_directory_observation.__code__
    late_events=[];finalizer_events=[];arm_events=[];detach_faults=[]
    interrupt_case=case in ('lost_return_interrupt_before','lost_return_interrupt_after')
    target_line=-1
    if interrupt_case:
        lines,start=inspect.getsourcelines(m._run_directory_observation)
        tree=ast.parse(''.join(lines))
        stores=[node for node in ast.walk(tree) if isinstance(node,ast.Assign)
                and len(node.targets)==1 and isinstance(node.targets[0],ast.Subscript)
                and isinstance(node.targets[0].value,ast.Name)
                and node.targets[0].value.id=='held_link'
                and isinstance(node.targets[0].slice,ast.Constant)
                and node.targets[0].slice.value==0
                and isinstance(node.value,ast.Constant) and node.value.value is None]
        assert len(stores)==1
        after=[node for node in ast.walk(tree) if isinstance(node,ast.Assign)
               and any(isinstance(target,ast.Name) and target.id=='unmatched_marker'
                       for target in node.targets)]
        assert after
        target=(stores[0] if case=='lost_return_interrupt_before'
                else min(after,key=lambda node:node.lineno))
        target_line=start+target.lineno-1
    class RevokeOnDisposal:
        def __del__(self):
            activation_names['_retired']=True
            finalizer_events.append(True)
    native_callee=registration.native_origin.operations[4]
    def capture_factory(actual_owner,actual_resource):
        triple=factory(actual_owner,actual_resource)
        operation,marker,payload=triple
        assert actual_owner is owner and actual_resource is resource
        assert marker.operation is operation
        captured.append((operation,marker,weakref.ref(payload)))
        return triple
    def interrupt_cleanup(frame,event,arg):
        if frame.f_code is not caller_code:return None
        if event=='line' and frame.f_lineno==target_line:
            assert detach_faults==[]
            operation,marker,payload_reference=captured[0]
            assert payload_reference() is not None
            if case=='lost_return_interrupt_before':
                assert marker.owner_link[0] is payload_reference()
            else:assert marker.owner_link[0] is None
            detach_faults.append(True)
            sys.settrace(trace_before)
            raise RuntimeError('synthetic memory retirement interruption')
        return interrupt_cleanup
    def observe_native(frame,event,arg):
        if (event=='c_call' and arg is native_callee
                and frame.f_code is producer_code):
            assert len(captured)==1 and frame.f_locals['operation'] is captured[0][0]
            native_entries.append(True)
        if (interrupt_case and event=='c_return'
                and arg is registration.native_origin.actor_calls[2]
                and frame.f_code is a._native_actor_context.__code__
                and frame.f_back.f_code is caller_code and not arm_events):
            assert returns==[True] and native_entries==[True]
            # Do not materialize caller f_locals: a cached Python3.11 snapshot
            # could itself retain the payload beyond the caller's fastlocals.
            frame.f_back.f_trace=interrupt_cleanup
            sys.settrace(interrupt_cleanup)
            arm_events.append(True)
    def lose_return(frame,event,arg):
        if frame.f_code is ack_tail_code:
            if (event=='return' and frame.f_back.f_code is caller_code
                    and case in ('late_marker_drift','disposal_revocation')):
                operation,marker,payload_reference=captured[0]
                assert type(arg) is m._DirectoryPolicyCommit
                assert arg is operation.result.acknowledged[0]
                assert late_events==[]
                late_events.append(True)
                if case=='late_marker_drift':marker.marker_slot[0]=foreign_slot
                else:payload_reference().category[0]=RevokeOnDisposal()
            return lose_return
        if frame.f_code is not producer_code:return None
        if event=='return':
            operation,marker,payload_reference=captured[0]
            assert type(arg) is m._DirectoryMetadataReturn and arg.operation is operation
            assert frame.f_locals['raw'] is operation.result.unset
            assert frame.f_locals['actual'] is frame.f_locals['payload'] is None
            assert payload_reference() is not None
            returns.append(True)
            if case not in ('normal','late_marker_drift','disposal_revocation'):
                sys.settrace(trace_before)
                if case=='revoked_lost_return':activation_names['_retired']=True
                if case=='foreign_slot_lost_return':marker.marker_slot[0]=foreign_slot
                if case=='foreign_inner_lost_return':
                    copied_marker=marker._replace()
                    foreign_inner.append(copied_marker)
                    operation.result.custody_origin.marker_member.__set__(
                        payload_reference(),copied_marker)
                raise RuntimeError('synthetic producer return loss')
        return lose_return
    m._prepare_metadata_operation_with_custody=capture_factory
    gc.disable()
    try:
        sys.setprofile(observe_native)
        sys.settrace(lose_return)
        try:
            returned=m._run_directory_observation(owner,resource)
        except a.ArtifactObservationError as exc:
            assert case!='normal'
            assert exc.failed_owner is owner
            assert str(exc)=='BI1_STARTUP_ARTIFACTS_REFUSED'
            assert exc.__cause__ is exc.__context__ is None
            cursor=exc.__traceback__
            while cursor is not None:
                if cursor.tb_frame.f_code is m._run_directory_observation.__code__:
                    values=cursor.tb_frame.f_locals
                    assert values['actual'] is values['payload'] is None
                    assert values['producer_started'] and values['producer_unwound']
                cursor=cursor.tb_next
        else:
            assert case=='normal' and type(returned) is m._DirectoryPolicyCommit
            assert returned is captured[0][0].result.acknowledged[0]
        finally:
            sys.settrace(trace_before)
            sys.setprofile(profile_before)
        assert len(captured)==1 and returns==[True] and native_entries==[True]
        operation,marker,payload_reference=captured[0]
        if interrupt_case:
            alive=payload_reference() is not None
            stage=dict(case=case,producer_returns=len(returns),native_entries=len(native_entries),
                       armed=len(arm_events),injected=len(detach_faults),payload_alive=alive,
                       owned_link_retains_payload=(alive and
                           marker.owner_link[0] is payload_reference()),
                       debit_preserved=ledger.counts==[counts[0]+1,counts[1]],
                       phase_failed=phase.current[0] is phase.failed)
            path=Path(sys.argv[1])/'caller-interruption-stage.json'
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:json.dump(stage,stream,sort_keys=True)
            assert arm_events==detach_faults==[True]
        assert not gc.isenabled() and payload_reference() is None
        assert operation.result.custody_link==[None]
        assert ledger.counts==[counts[0]+1,counts[1]]
        assert len(ledger.attempts)==attempts+1 and ledger.attempts[-1] is operation
        assert ledger.inflight==[None] and phase.result==[None]
        if case=='normal':
            assert ledger.failed==[False] and ledger.failure==[None]
            assert phase.current[0] is phase.idle and metadata.progress==[1,None]
            assert marker.state==[True,True,False]
        else:
            assert ledger.failed==[True] and ledger.failure[0] is operation
            assert phase.current[0] is phase.failed
            assert operation.state==[True,True,True] and operation.ended==[True]
            if case in ('late_marker_drift','disposal_revocation'):
                assert metadata.progress==[1,None] and late_events==[True]
                assert type(operation.result.acknowledged[0]) is m._DirectoryPolicyCommit
                assert operation.result.consumer[0].commit[0] is operation.result.acknowledged[0]
            else:
                assert metadata.progress[0]==0
                assert metadata.progress[1] is operation.result.consumer[0]
                assert operation.result.acknowledged==[None]
            if interrupt_case:
                assert marker.state==[False,False,False]
            else:assert marker.state[:2]==[True,True]
        if case in ('foreign_slot_lost_return','late_marker_drift'):
            assert marker.marker_slot[0] is foreign_slot and marker.state[2] is True
        else:assert marker.marker_slot[0] is marker
        if case=='foreign_inner_lost_return':
            assert len(foreign_inner)==1 and foreign_inner[0] is not marker
            assert marker.state[2] is True
        if case in ('revoked_lost_return','disposal_revocation'):
            assert activation_names['_retired'] is True
        if case=='disposal_revocation':assert finalizer_events==[True]
        seen.append(True)
    finally:
        sys.settrace(trace_before)
        sys.setprofile(profile_before)
        m._prepare_metadata_operation_with_custody=factory
        if gc_before:gc.enable()
        activation_names['_retired']=retired_before
        # Dispose this synthetic fixture only. Never production refund/rearm.
        if len(ledger.attempts)>attempts:
            assert ledger.attempts.pop() is captured[0][0]
        ledger.counts[0]=counts[0]
        ledger.inflight[0]=None;ledger.failed[0]=False;ledger.failure[0]=None
        phase.current[0]=phase.idle;phase.result[0]=None
        metadata.progress[:]=[0,None]
        ledger.preparation[:]=preparation
original_fstat=vars(a.StartupArtifactOwner)['_fstat']
original_file_code=a.StartupArtifactOwner._file.__code__
def at_original_fstat(actual_owner,fd,scope,registration=None):
    if actual_owner is owner and not seen:
        frame=sys._getframe(1)
        assert frame.f_code is original_file_code
        assert frame.f_locals['native_registration'] is registration
        assert frame.f_locals['fd'] is fd
        exercise(frame)
    return original_fstat(actual_owner,fd,scope,registration)
a.StartupArtifactOwner._fstat=at_original_fstat
try:owner.read()
finally:a.StartupArtifactOwner._fstat=original_fstat
assert seen==[True] and owner._ready
assert owner.completed_binding()[4] is owner._original_buffer
owner.release()
assert owner._original_buffer==bytearray()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
