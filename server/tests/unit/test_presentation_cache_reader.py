"""Declared cache bytes only; no cache-miss fallback or payload execution."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'changed', 'wrong_thread', 'replay',
                                 'read_error', 'fact_copy', 'late_buffer', 'release_foreign',
                                 'late_effect', 'late_ledger', 'late_lifecycle',
                                 'native_count_drift', 'foreign_read_claim', 'late_owner',
                                 'consumer_wrong_thread', 'consumer_duplicate',
                                 'consumer_feed_failure', 'consumer_eof_ack_failure',
                                 'metadata_plan_copy',
                                 *(f'interrupt_{prefix}{point}'
                                   for prefix in ('', 'eof_')
                                   for point in ('ack', 'raw', 'envelope', 'cursor',
                                                 'progress', 'eof', 'phase', 'return'))))
def test_declared_cache_reader(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script.replace('import sample_dep\n', 'import sample_dep\n' + r'''
import importlib.util
prepared_cache=Path(importlib.util.cache_from_source(str(dep_root/'__init__.py')))
prepared_cache.parent.mkdir(mode=0o700)
cache_payload=b'SYNTHETIC_NOT_EXECUTABLE_CACHE_ONLY' * 4096
prepared_cache.write_bytes(cache_payload);prepared_cache.chmod(0o600)
''', 1)
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup import cache_reader as cm
from hmp_startup.cache_reader import DeclaredCacheReadOwner,CacheReadError
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
old_count=checked._fact_cell[2]._count_cell
owner=DeclaredCacheReadOwner.retain(continuation,index)
assert owner._origin.native_files is continuation._source.entry_binding[0].native_files
assert owner._origin.source_digest is None
original=owner._buffer
if case=='changed':prepared_cache.write_bytes(b'X'*len(cache_payload))
if case=='wrong_thread':
    import threading
    refused=[]
    def other_thread():
        try:owner.read()
        except CacheReadError:refused.append(True)
        else:refused.append(False)
    other=threading.Thread(target=other_thread);other.start();other.join(timeout=10)
    assert not other.is_alive() and refused==[True] and not owner._started and not owner._failed
if case=='read_error':
    import errno
    read_calls=0
    def fail_after_prefix(frame):
        global read_calls
        if frame.f_locals['self'] is owner:
            read_calls+=1
            if read_calls==2:raise OSError(errno.EIO,'synthetic lost read acknowledgement')
    trace_synthetic_boundary(DeclaredCacheReadOwner._read_native.__code__,
                             '_require(type(data) is bytes)',fail_after_prefix)
if case in ('native_count_drift','foreign_read_claim'):
    foreign_claim=object()
    def drift_after_actual_read(frame):
        if frame.f_locals['self'] is owner:
            if case=='native_count_drift':owner._count_cell=tuple(list(owner._count_cell))
            else:owner._read_claim=foreign_claim
    trace_synthetic_boundary(DeclaredCacheReadOwner._read_native.__code__,
                             '_require(type(data) is bytes)',drift_after_actual_read)
if case=='late_owner':
    foreign_owner=object()
    def drift_owner_after_native_return(frame):
        if frame.f_locals['self'] is owner:
            assert frame.f_locals['result_slot'][0] is not None
            owner._origin.activation._cache_read_owner=foreign_owner
    trace_synthetic_boundary(DeclaredCacheReadOwner._read_native.__code__,
                             'same = (_OWNER is self',drift_owner_after_native_return)
if case in ('late_buffer','late_effect','late_ledger','late_lifecycle'):
    actual_context=cm._context
    def replace_after_close():
        if owner._started and owner._origin.records and all(
                row.closed for row in owner._origin.records):
            if case=='late_buffer':owner._buffer=bytearray(b'FOREIGN')
            elif case=='late_effect':
                effect=owner._origin.reads[-1]
                effect.after=tuple(list(effect.after))
            elif case=='late_ledger':
                copied=tuple(list(cm._RESULTS))
                cm._RESULTS=owner._results=owner._origin.activation._cache_read_results=copied
            else:owner._started=False
        return actual_context()
    cm._context=replace_after_close
from hmp_plugin import presentation_startup_artifacts as a
actual_consume=a._consume_native_cache_read
consumer_checks=[];observed_commits=[]
def consume_cache(self,envelope):
    assert self is owner and type(envelope.cache_return) is a._NativeCacheReadReturn
    actual=envelope.cache_return
    if case=='consumer_wrong_thread' and not consumer_checks:
        import threading
        prior=(owner._failed,owner._unknown,bytes(original),envelope.raw_cell[0])
        refused=[]
        def wrong_thread():
            try:actual_consume(self,envelope)
            except a.ArtifactObservationError:refused.append(True)
        thread=threading.Thread(target=wrong_thread);thread.start();thread.join(timeout=10)
        assert not thread.is_alive() and refused==[True]
        assert prior==(owner._failed,owner._unknown,bytes(original),envelope.raw_cell[0])
        consumer_checks.append(True)
    commit=actual_consume(self,envelope)
    assert type(commit) is a._NativeCacheReadCommit
    assert commit.cache_attempt is actual.attempt and commit.cache_result is actual.result
    assert commit.cache_index is actual.index and commit.header==bytes(original[:16])
    assert not hasattr(commit,'heads') and not hasattr(commit,'result_heads')
    assert envelope.raw_cell[0] is envelope.result.unset and envelope.envelope_cell[0] is None
    assert commit.eof is (len(envelope.raw)==0)
    observed_commits.append(commit)
    if case=='consumer_duplicate':
        prior=(owner._failed,owner._unknown,bytes(original))
        try:actual_consume(self,envelope)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('duplicate cache consumer accepted')
        assert prior==(owner._failed,owner._unknown,bytes(original))
        consumer_checks.append(True)
    return commit
a._consume_native_cache_read=consume_cache
if case.startswith('interrupt_'):
    point=case[len('interrupt_'):]
    interrupt_eof=point.startswith('eof_')
    if interrupt_eof:point=point[len('eof_'):]
    boundary={
        'ack':'envelope.raw_cell[0] = envelope.result.unset',
        'raw':'envelope.envelope_cell[0] = None',
        'envelope':'step.progress[0] = commit.ordinal',
        'cursor':'step.progress[2] = commit.count',
        'progress':'step.progress[3] = None',
        'eof':'phase = operation.registration.native_phase',
        'phase':'phase.current[0] = phase.idle',
        'return':'return commit',
    }[point]
    interrupted=[]
    def interrupt_ack(frame):
        envelope=frame.f_locals['envelope']
        if envelope.consumer.owner is owner and frame.f_locals['eof'] is interrupt_eof:
            assert not interrupted
            interrupted.append(envelope)
            raise OSError('SYNTHETIC_CACHE_PARTIAL_ACK')
    trace_synthetic_boundary(actual_consume.__code__,boundary,interrupt_ack)
if case in ('consumer_feed_failure','consumer_eof_ack_failure'):
    def interrupt_consumer(frame):
        envelope=frame.f_locals['envelope']
        if envelope.consumer.owner is owner and (
                case=='consumer_feed_failure' or frame.f_locals['eof']):
            consumer_checks.append(True)
            raise OSError('SYNTHETIC_CACHE_CONSUMER_INTERRUPTION')
    boundary=('step.hash_update(step.digest, data)' if case=='consumer_feed_failure'
              else 'envelope.ack_cell[0] = commit')
    trace_synthetic_boundary(actual_consume.__code__,boundary,interrupt_consumer)
if case=='metadata_plan_copy':
    plan_swap=[]
    def replace_metadata_plan(frame):
        if frame.f_locals['self'] is owner:
            held=frame.f_locals['native_walk']
            assert type(held) is tuple and len(held)==6
            original_plan=held[5]
            assert original_plan is held[0].metadata_slot[0]
            copied=original_plan._replace(progress=list(original_plan.progress))
            held[0].metadata_slot[0]=copied
            plan_swap.append((held,original_plan,copied))
    trace_synthetic_boundary(a.StartupArtifactOwner._file.__code__,
                             '_finish_native_declared_walk(self, native_registration, native_walk)',
                             replace_metadata_plan)
try:owner.read()
except CacheReadError:
    assert case in ('changed','read_error','late_buffer','late_effect',
                    'late_ledger','late_lifecycle','native_count_drift',
                    'foreign_read_claim','late_owner','consumer_feed_failure',
                    'consumer_eof_ack_failure','metadata_plan_copy') or case.startswith('interrupt_')
    assert owner._failed
    assert not owner._ready and owner._fact is None and cm._READY is None
    assert original==bytearray()
    if case=='metadata_plan_copy':
        assert len(plan_swap)==1
        held,original_plan,copied=plan_swap[0]
        assert held[5] is original_plan and held[0].metadata_slot[0] is copied
        assert held[3] is held[2][0] and held[4][0]==1
    if case.startswith('interrupt_'):
        assert len(interrupted)==1 and owner._unknown
        envelope=interrupted[0]
        assert type(envelope.ack_cell[0]) is a._NativeCacheReadCommit
        assert envelope.raw_cell[0] is envelope.result.unset
        assert envelope.envelope_cell[0] is None
        assert envelope.operation.ledger.failed[0] is True
        assert envelope.operation.state[2] is True
        assert envelope.result.category[0] in ('returned_bytes_ack_unconfirmed','returned_bytes')
        before=(len(cm._ATTEMPTS),len(cm._RESULTS))
        try:owner.read()
        except CacheReadError:pass
        else:raise AssertionError('partial ACK replayed')
        assert before==(len(cm._ATTEMPTS),len(cm._RESULTS))
    if case=='read_error':
        assert owner._bytes_read==65536 and owner._unknown
        assert len(owner._origin.reads)==2 and owner._origin.reads[-1].unknown
    if case=='late_buffer':assert owner._buffer==bytearray(b'FOREIGN')
    if case=='late_owner':
        assert owner._origin.activation._cache_read_owner is foreign_owner
        assert owner._read_claim is not None and owner._unknown
    if case in ('native_count_drift','foreign_read_claim'):
        attempt=cm._ATTEMPTS[0]
        result=attempt[4][0]
        assert result[0] is attempt and result[2]==65536
        assert result[1][2]==65536 and owner._unknown and not cm._RESULTS
        if case=='foreign_read_claim':
            assert owner._read_claim is foreign_claim and owner._reading
        else:assert owner._count_cell is not attempt[3]

else:
    assert case in ('normal','wrong_thread','replay','fact_copy','release_foreign',
                    'consumer_wrong_thread','consumer_duplicate')
    assert observed_commits and observed_commits[-1].eof is True
    assert sum(c.eof for c in observed_commits)==1
    assert all(c.result.raw[0] is c.result.unset and c.result.envelope[0] is None
               for c in observed_commits)
    import gc
    gc.collect()
    assert not any(type(value) is a._NativeCacheReadReturn
                   and value.result[1][0] is owner for value in gc.get_objects())
    fact=owner.current_binding()
    assert original==cache_payload and owner._bytes_read==len(cache_payload)
    assert fact[4] is original and fact[5].bytecode_header==cache_payload[:16]
    if case=='replay':
        try:owner.read()
        except CacheReadError:pass
        else:raise AssertionError('read replayed')
        assert owner.current_binding() is fact
    if case=='fact_copy':
        owner._fact=cm._READY=tuple(list(fact))
        try:owner.current_binding()
        except CacheReadError:pass
        else:raise AssertionError('copied completion adopted')
    if case=='release_foreign':owner._buffer=bytearray(b'FOREIGN')
    owner.release()
    assert original==bytearray() and owner._released
    if case=='release_foreign':assert owner._buffer==bytearray(b'FOREIGN')
if case.startswith('consumer_'):assert consumer_checks
assert checked._fact_cell[2]._count_cell is old_count
assert all(row.closed and row.close_attempted and not row.unknown for row in owner._origin.records)
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)
