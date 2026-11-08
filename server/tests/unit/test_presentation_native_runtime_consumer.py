"""Original runtime read consumption/EOF ACK in isolated synthetic file fixtures."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'wrong_thread', 'duplicate', 'reentrant',
                                 'before_feed_swap', 'after_feed_lost_ack',
                                 'eof_lost_ack', 'after_ack_lost_return',
                                 *(f'interrupt_{prefix}{point}'
                                   for prefix in ('', 'eof_')
                                   for point in ('ack', 'raw', 'envelope', 'cursor',
                                                 'progress', 'eof', 'phase', 'return'))))
def test_native_runtime_consumer(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
import inspect,sys,threading
from types import BuiltinMethodType
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_source_digest as sd
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.runtime_reader import RuntimeSourceReadOwner,RuntimeReadError
from hmp_startup.cache_selection import selected_cache_input_attempts
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
original=owner._original_buffer
replacement=bytearray(b'FOREIGN_BUFFER_MUST_SURVIVE')
actual_consume=a._consume_native_runtime_read
interrupt_point=None;interrupt_eof=False;target_line=None
if case.startswith('interrupt_'):
    interrupt_point=case[len('interrupt_'):]
    if interrupt_point.startswith('eof_'):
        interrupt_eof=True;interrupt_point=interrupt_point[len('eof_'):]
    target={
        'ack':'envelope.raw_cell[0] = envelope.result.unset',
        'raw':'envelope.envelope_cell[0] = None',
        'envelope':'step.progress[0] = commit.ordinal',
        'cursor':'step.progress[2] = commit.count',
        'progress':'step.eof[0] = commit.eof',
        'eof':'phase = operation.registration.native_phase',
        'phase':'phase.current[0] = phase.idle',
        'return':'return commit',
    }[interrupt_point]
    lines,first=inspect.getsourcelines(actual_consume)
    matches=[first+i for i,line in enumerate(lines) if line.strip()==target]
    assert len(matches)==1
    target_line=matches[0]
actual_append,actual_eof=sd.append,sd.consume_eof
seen=[];commits=[];checks=[];after_eof=[];late_metadata=[];native_metadata=[]
def profile(frame,event,arg):
    if event=='c_call' and after_eof and any(arg is call for call in native_metadata):
        late_metadata.append(True)
    if (case=='reentrant' and event=='c_return' and type(arg) is BuiltinMethodType
        and arg.__self__ is original and arg.__name__=='extend' and not checks):
        envelope=seen[-1]
        assert envelope.consumption_cell[0] is not None
        before=(owner._failed,owner._unknown,bytes(original),envelope.result.raw[0])
        try:actual_consume(owner,envelope)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('reentrant consumption accepted')
        assert before==(owner._failed,owner._unknown,bytes(original),envelope.result.raw[0])
        checks.append(True)
def lose_feed(root,buffer,chunk,observations):
    actual_append(root,buffer,chunk,observations)
    if root.owner is owner and case=='after_feed_lost_ack':
        assert root.effect.size>0
        checks.append(True)
        raise OSError('SYNTHETIC_AFTER_FEED_LOST_ACK')
def lose_eof(root,buffer,count,observations):
    result=actual_eof(root,buffer,count,observations)
    if root.owner is owner and case=='eof_lost_ack':
        assert root.effect.eof is count
        after_eof.append(True)
        checks.append(True)
        raise OSError('SYNTHETIC_EOF_LOST_ACK')
    return result
sd.append,sd.consume_eof=lose_feed,lose_eof
def consume(self,envelope):
    assert self is owner and type(envelope) is a._NativeReadResult
    seen.append(envelope)
    native_metadata[:]=[envelope.operation.native.operations[i] for i in (3,4)]
    if case=='wrong_thread' and not checks:
        before=(owner._failed,owner._unknown,bytes(original),envelope.result.raw[0],
                envelope.operation.registration.native_phase.current[0])
        result=[]
        def foreign():
            try:actual_consume(self,envelope)
            except a.ArtifactObservationError:result.append('refused')
            else:result.append('accepted')
        thread=threading.Thread(target=foreign);thread.start();thread.join(5)
        assert not thread.is_alive() and result==['refused']
        assert before==(owner._failed,owner._unknown,bytes(original),envelope.result.raw[0],
                        envelope.operation.registration.native_phase.current[0])
        assert envelope.consumption_cell[0] is None
        checks.append(True)
    if case=='before_feed_swap' and not checks:
        owner._buffer=replacement
        checks.append(True)
    def interrupt(frame,event,arg):
        if (event=='line' and frame.f_code is actual_consume.__code__
            and frame.f_lineno==target_line and not checks):
            assert frame.f_locals['commit'].eof is interrupt_eof
            checks.append(True)
            if interrupt_eof:after_eof.append(True)
            raise InterruptedError('SYNTHETIC_OWNED_ACK_TRANSITION_ONLY')
        return interrupt
    selected_interrupt=(interrupt_point is not None
                        and (envelope.consumer.remaining==0) is interrupt_eof)
    if selected_interrupt:sys.settrace(interrupt)
    try:commit=actual_consume(self,envelope)
    finally:
        if selected_interrupt:sys.settrace(None)
    assert envelope.ack_cell[0] is commit and envelope.commit_cell[0] is commit
    assert envelope.raw_cell[0] is envelope.result.unset
    assert envelope.envelope_cell[0] is None
    phase=envelope.operation.registration.native_phase
    assert phase.current[0] is phase.idle and phase.result[0] is None
    assert commit.count is owner._count_cell
    commits.append(commit)
    if case=='duplicate' and not checks:
        before=(owner._failed,owner._unknown,bytes(original),commit,
                tuple(envelope.operation.ledger.counts))
        try:actual_consume(self,envelope)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('ACKed read consumed twice')
        assert before==(owner._failed,owner._unknown,bytes(original),
                        envelope.ack_cell[0],tuple(envelope.operation.ledger.counts))
        checks.append(True)
    if case=='after_ack_lost_return' and not checks:
        checks.append(True)
        raise OSError('SYNTHETIC_AFTER_ACK_LOST_RETURN')
    return commit
a._consume_native_runtime_read=consume
sys.setprofile(profile)
try:
    try:owner.read()
    except RuntimeReadError:
        assert case in ('before_feed_swap','after_feed_lost_ack',
                        'eof_lost_ack','after_ack_lost_return') or interrupt_point is not None
        assert checks and seen and owner._failed and original==bytearray()
        last=seen[-1]
        assert last.raw_cell[0] is last.result.unset
        if interrupt_point is not None:
            assert checks==[True]
            if interrupt_eof:assert late_metadata==[]
            assert type(last.ack_cell[0]) is a._NativeRuntimeReadCommit
            assert last.ack_cell[0].eof is interrupt_eof
            assert last.envelope_cell[0] is None
            assert last.result.category[0]==('returned_bytes' if interrupt_point=='return'
                                             else 'returned_bytes_ack_unconfirmed')
        elif case=='after_ack_lost_return':
            assert last.ack_cell[0] is commits[-1]
            assert last.result.category[0]=='returned_bytes'
        else:
            assert last.ack_cell[0] is None
            assert last.result.category[0]=='returned_bytes_abandoned'
        if case=='before_feed_swap':assert replacement==b'FOREIGN_BUFFER_MUST_SURVIVE'
        if case=='eof_lost_ack':assert after_eof==[True] and late_metadata==[]
    else:
        assert case in ('normal','wrong_thread','duplicate','reentrant')
        assert owner._ready and seen and len(commits)==len(seen)
        assert bytes(original)==(dep_root/'__init__.py').read_bytes()
        assert [row.eof for row in commits]==[False]*(len(commits)-1)+[True]
        assert commits[-1].remaining==0 and commits[-1].count[2]==len(original)
        if case!='normal':assert checks==[True]
        owner.release();assert original==bytearray()
finally:
    sys.setprofile(None)
assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
