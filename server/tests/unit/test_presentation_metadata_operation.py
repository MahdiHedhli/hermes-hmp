"""Operation preparation over an actual original opened synthetic descriptor."""
from __future__ import annotations

import pytest

from . import test_presentation_entry_files as base
from .test_presentation_gateway_approval import operator_composed_script


@pytest.mark.parametrize('case', ('normal', 'copied_descriptor', 'copied_registration',
                                 'foreign_descriptor', 'unexpected_name',
                                 'latched', 'copied_consumer', 'wrong_pending',
                                 'copied_operation', 'wrong_result_consumer',
                                 'active', 'active_wrong_phase', 'active_failed',
                                 'active_missing_debit', 'active_wrong_result',
                                 'active_failure_record', 'latch_postpublication_failure',
                                 'admit', 'admit_wrong_actor', 'admit_before_debit_failure',
                                 'admit_after_debit_failure', 'admit_foreign_slot_failure',
                                 'produce', 'produce_snapshot_failure',
                                 'produce_foreign_raw_failure', 'consume',
                                 'consume_wrong_actor', 'consume_policy_failure',
                                 'ack', 'ack_wrong_actor', 'ack_late_failure'))
def test_original_metadata_operation(tmp_path, monkeypatch, case):
    script, mutation = operator_composed_script('links')
    script = script.replace('GatewayPackageOwner.verify_recipe(recipe)',
                            'GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)')
    script = script[:script.rfind('print(json.dumps')]
    script += '\ncase=' + repr(case) + '\n'
    script += r'''
from hmp_startup.gateway_continuation import GatewayContinuationOwner
from hmp_startup.cache_selection import selected_cache_input_attempts
from hmp_startup.runtime_reader import RuntimeSourceReadOwner
from hmp_plugin import presentation_startup_artifacts as a
from hmp_plugin import presentation_native_metadata as m
continuation=GatewayContinuationOwner.retain(entry,approval,recipe,checked)
rows=selected_cache_input_attempts(continuation)
index=next(i for i,row in enumerate(rows) if row.plan_row.source.path==str(dep_root/'__init__.py'))
owner=RuntimeSourceReadOwner.retain(continuation,index)
seen=[];foreign_calls=[]
class Foreign:
    def __getattr__(self,name):
        foreign_calls.append(name)
        raise AssertionError('foreign descriptor getter')
def prepare(frame):
    if frame.f_locals['self'] is not owner or seen:return
    held=frame.f_locals['native_walk']
    registration=frame.f_locals['native_registration']
    descriptor=frame.f_locals['row']
    assert type(descriptor) is a._NativeOpenedDescriptor and len(held)==6
    ledger=registration.native_ledger
    counts=tuple(ledger.counts);attempts=len(ledger.attempts)
    phase=registration.native_phase
    progress=held[5].progress
    assert progress==[0,None] and phase.current[0] is phase.idle
    candidate=descriptor;candidate_registration=registration;name=None
    if case=='copied_descriptor':candidate=descriptor._replace()
    elif case=='copied_registration':candidate_registration=registration._replace()
    elif case=='foreign_descriptor':candidate=Foreign()
    elif case=='unexpected_name':name='UNRELATED_COMPONENT'
    try:
        resource=a._prepare_native_metadata_resource(
            owner,candidate_registration,held,candidate,name)
    except a.ArtifactObservationError:
        assert case in ('copied_descriptor','copied_registration',
                        'foreign_descriptor','unexpected_name')
    else:
        assert case in ('normal','latched','copied_consumer','wrong_pending',
                        'copied_operation','wrong_result_consumer',
                        'active','active_wrong_phase','active_failed',
                        'active_missing_debit','active_wrong_result','active_failure_record',
                        'latch_postpublication_failure','admit','admit_wrong_actor','admit_before_debit_failure',
                        'admit_after_debit_failure','admit_foreign_slot_failure',
                        'produce','produce_snapshot_failure','produce_foreign_raw_failure',
                        'consume','consume_wrong_actor','consume_policy_failure',
                        'ack','ack_wrong_actor','ack_late_failure')
        assert resource.descriptor is descriptor
        assert resource.metadata is held[5] and resource.held_walk is held
        assert resource.arguments[0] is descriptor.fd
        assert resource.site==(4,'directory',0) and resource.ordinal==0
        operation=m._prepare_metadata_operation(owner,resource)
        assert type(operation) is m._MetadataOperation and operation.resource is resource
        assert operation.callee is registration.native_origin.operations[4]
        assert operation.arguments is resource.arguments and operation.attempts is ledger.attempts
        assert operation.index==attempts and operation.budget[0] is ledger.counts
        assert operation.budget[1:]==(counts[0],counts[1],counts[0]+1)
        assert operation.state==[False,False,False] and operation.ended==[False]
        result=operation.result
        assert result.attempt[0] is operation and result.consumer==[None]
        assert result.raw[0] is result.unset and result.category==[None]
        assert result.snapshot==result.acknowledged==result.envelope==[None]
        consumer=m._prepare_directory_consumer(owner,operation)
        assert type(consumer) is m._DirectoryConsumer and consumer.operation is operation
        assert consumer.resource is resource and result.consumer[0] is consumer
        assert consumer.consumption==consumer.commit==[None]
        assert consumer.owner_type is type(owner)
        assert consumer.material is owner._origin.material_origin[0]
        assert consumer.material_code is owner._origin.material_origin[1]
        assert consumer.file_function is a.StartupArtifactOwner._file
        assert consumer.file_code is a.StartupArtifactOwner._file.__code__
        try:m._prepare_directory_consumer(owner,operation)
        except a.ArtifactObservationError:pass
        else:raise AssertionError('directory consumer rebound')
        assert result.consumer[0] is consumer
        if case!='normal':
            try:m._latch_directory_consumer(owner,consumer._replace())
            except a.ArtifactObservationError:pass
            else:raise AssertionError('copied consumer latched')
            assert progress[1] is None and result.consumer[0] is consumer
            if case=='latch_postpublication_failure':
                original_tail=m._latched_directory_resource_tail
                injected=[]
                def refuse_after_publication(actual_owner,actual_consumer):
                    assert actual_owner is owner and actual_consumer is consumer
                    assert progress[1] is consumer
                    assert original_tail(actual_owner,actual_consumer) is resource
                    injected.append(True)
                    raise a.ArtifactObservationError()
                m._latched_directory_resource_tail=refuse_after_publication
                try:
                    try:m._latch_directory_consumer(owner,consumer)
                    except a.ArtifactObservationError:pass
                    else:raise AssertionError('post-publication failure swallowed')
                finally:m._latched_directory_resource_tail=original_tail
                assert injected==[True] and result.consumer[0] is consumer
                assert result.raw[0] is result.unset
            else:
                assert m._latch_directory_consumer(owner,consumer) is consumer
            assert progress[1] is consumer
            try:m._latch_directory_consumer(owner,consumer)
            except a.ArtifactObservationError:pass
            else:raise AssertionError('metadata consumer latched twice')
            candidate_consumer=consumer
            if case=='copied_consumer':candidate_consumer=consumer._replace()
            elif case=='wrong_pending':progress[1]=consumer._replace()
            elif case=='copied_operation':
                candidate_consumer=consumer._replace(operation=operation._replace())
                progress[1]=candidate_consumer
            elif case=='wrong_result_consumer':result.consumer[0]=consumer._replace()
            try:
                try:returned=m._latched_directory_resource_tail(owner,candidate_consumer)
                except a.ArtifactObservationError:
                    assert case not in ('latched','active','active_wrong_phase','active_failed',
                                       'active_missing_debit','active_wrong_result',
                                       'active_failure_record','latch_postpublication_failure','admit','admit_wrong_actor','admit_before_debit_failure',
                        'admit_after_debit_failure','admit_foreign_slot_failure',
                        'produce','produce_snapshot_failure','produce_foreign_raw_failure',
                        'consume','consume_wrong_actor','consume_policy_failure',
                        'ack','ack_wrong_actor','ack_late_failure')
                else:
                    assert (case in ('latched','latch_postpublication_failure',
                                    'admit','admit_wrong_actor','admit_before_debit_failure',
                        'admit_after_debit_failure','admit_foreign_slot_failure',
                        'produce','produce_snapshot_failure','produce_foreign_raw_failure',
                        'consume','consume_wrong_actor','consume_policy_failure',
                        'ack','ack_wrong_actor','ack_late_failure')
                            or case.startswith('active')) and returned is resource
                # Latched structural validation never renews unclaimed admission.
                try:a._native_declared_metadata_plan_tail(owner,registration,held)
                except a.ArtifactObservationError:pass
                else:raise AssertionError('latched plan renewed')
                if case in ('admit','admit_wrong_actor','admit_before_debit_failure',
                            'admit_after_debit_failure','admit_foreign_slot_failure'):
                    preparation_before=tuple(ledger.preparation)
                    if case in ('admit_before_debit_failure','admit_after_debit_failure',
                                'admit_foreign_slot_failure'):
                        checkpoint=('_directory_admission_preparation_tail'
                                    if case=='admit_before_debit_failure'
                                    else '_active_directory_operation_tail')
                        fault_original=getattr(m,checkpoint)
                        fault_events=[];foreign_slot=object()
                        def refuse_admission_checkpoint(*arguments):
                            assert fault_original(*arguments) is operation
                            fault_events.append(True)
                            if case=='admit_foreign_slot_failure':
                                phase.result[0]=foreign_slot
                            raise a.ArtifactObservationError()
                        setattr(m,checkpoint,refuse_admission_checkpoint)
                        try:
                            try:
                                try:m._admit_directory_operation(owner,consumer)
                                except a.ArtifactObservationError:pass
                                else:raise AssertionError('admission fault swallowed')
                            finally:setattr(m,checkpoint,fault_original)
                            debit=0 if case=='admit_before_debit_failure' else 1
                            assert fault_events==[True]
                            assert ledger.counts==[counts[0]+debit,counts[1]]
                            assert len(ledger.attempts)==attempts+debit
                            if debit:assert ledger.attempts[-1] is operation
                            assert operation.state==[bool(debit),False,True]
                            assert ledger.failed==[True] and ledger.failure[0] is operation
                            assert phase.current[0] is phase.failed and ledger.inflight==[None]
                            if case=='admit_foreign_slot_failure':
                                assert phase.result[0] is foreign_slot
                            else:assert phase.result==[None]
                            assert result.raw[0] is result.unset
                            try:m._admit_directory_operation(owner,consumer)
                            except a.ArtifactObservationError:pass
                            else:raise AssertionError('failed admission replayed')
                            assert ledger.counts==[counts[0]+debit,counts[1]]
                        finally:
                            # Restore this disposable fixture only, never production debt.
                            if len(ledger.attempts)>attempts:
                                assert ledger.attempts.pop() is operation
                            ledger.counts[0]=counts[0]
                            ledger.inflight[0]=None
                            ledger.failed[0]=False
                            ledger.failure[0]=None
                            phase.current[0]=phase.idle
                            phase.result[0]=None
                            operation.state[:]=[False,False,False]
                            ledger.preparation[:]=preparation_before
                    elif case=='admit':
                        try:
                            assert m._admit_directory_operation(owner,consumer) is operation
                            assert m._active_directory_operation_tail(owner,consumer) is operation
                            assert len(ledger.attempts)==attempts+1
                            assert ledger.attempts[-1] is operation
                            assert ledger.counts==[counts[0]+1,counts[1]]
                            assert result.raw[0] is result.unset
                            try:m._admit_directory_operation(owner,consumer)
                            except a.ArtifactObservationError:pass
                            else:raise AssertionError('operation admitted twice')
                            assert ledger.counts==[counts[0]+1,counts[1]]
                        finally:
                            # Synthetic fixture retirement; no production refund path.
                            assert ledger.attempts.pop() is operation
                            ledger.counts[0]=counts[0]
                            ledger.inflight[0]=None
                            phase.current[0]=phase.idle
                            phase.result[0]=None
                            operation.state[:]=[False,False,False]
                            ledger.preparation[:]=preparation_before
                    else:
                        import threading
                        wrong_actor=[]
                        def admit_from_wrong_thread():
                            try:m._admit_directory_operation(owner,consumer)
                            except BaseException as exc:wrong_actor.append(type(exc))
                        worker=threading.Thread(target=admit_from_wrong_thread)
                        worker.start();worker.join(5)
                        assert not worker.is_alive()
                        assert wrong_actor==[a._NativeActorMismatchError]
                        assert operation.ended==[True] and operation.state==[False]*3
                        assert ledger.counts==list(counts) and len(ledger.attempts)==attempts
                        assert ledger.failed==[False] and ledger.failure==[None]
                        assert phase.current[0] is phase.idle and phase.result==[None]
                        assert ledger.inflight==[None] and progress[1] is consumer
                        try:m._admit_directory_operation(owner,consumer)
                        except a.ArtifactObservationError:pass
                        else:raise AssertionError('wrong-actor intent replayed')
                        operation.ended[0]=False  # fixture-only teardown
                        ledger.preparation[:]=preparation_before
                if case.startswith(('produce','consume','ack')):
                    preparation_before=tuple(ledger.preparation)
                    snapshot_original=m._native_metadata_snapshot
                    captured=[];foreign_raw=object()
                    def observe_original_metadata(actual_owner,actual_registration,native,value):
                        assert actual_owner is owner and actual_registration is registration
                        assert native is registration.native_origin
                        assert type(value) is native.result_type and result.raw[0] is value
                        assert operation.ended==[True] and operation.state==[True,True,False]
                        assert phase.current[0] is phase.active
                        assert ledger.inflight[0] is operation
                        captured.append(True)
                        observed=snapshot_original(actual_owner,actual_registration,native,value)
                        if case=='produce_snapshot_failure':
                            raise a.ArtifactObservationError(owner)
                        if case=='produce_foreign_raw_failure':result.raw[0]=foreign_raw
                        return observed
                    m._native_metadata_snapshot=observe_original_metadata
                    try:
                        try:
                            try:actual=m._produce_directory_metadata(owner,consumer)
                            except a.ArtifactObservationError as exc:
                                assert case in ('produce_snapshot_failure',
                                                'produce_foreign_raw_failure')
                                assert str(exc)=='BI1_STARTUP_ARTIFACTS_REFUSED'
                                assert exc.failed_owner is owner
                                assert exc.__context__ is None and exc.__cause__ is None
                                cursor=exc.__traceback__
                                while cursor is not None:
                                    if (cursor.tb_frame.f_code
                                            is m._produce_directory_metadata.__code__):
                                        values=cursor.tb_frame.f_locals
                                        assert values['raw'] is result.unset
                                        assert values['snapshot'] is values['actual'] is None
                                    cursor=cursor.tb_next
                                assert ledger.failed==[True] and ledger.failure[0] is operation
                                assert operation.state==[True,True,True]
                                assert phase.current[0] is phase.failed
                                assert phase.result==[None] and ledger.inflight==[None]
                                expected_raw=(foreign_raw if case=='produce_foreign_raw_failure'
                                              else result.unset)
                                assert result.raw[0] is expected_raw
                                assert result.snapshot==result.envelope==[None]
                            else:
                                assert case in ('produce','consume','consume_wrong_actor',
                                                'consume_policy_failure','ack','ack_wrong_actor',
                                                'ack_late_failure')
                                assert type(actual) is m._DirectoryMetadataReturn
                                pending=m._pending_directory_return_tail(owner,consumer,actual)
                                assert pending is actual
                                assert result.raw[0] is actual.raw
                                assert result.snapshot[0] is actual.snapshot
                                assert type(actual.raw) is registration.native_origin.result_type
                                assert phase.current[0] is phase.pending
                                assert ledger.inflight==[None] and phase.result[0] is operation
                                try:m._pending_directory_return_tail(owner,consumer,actual._replace())
                                except a.ArtifactObservationError:pass
                                else:raise AssertionError('copied native return accepted')
                                try:m._admit_directory_operation(owner,consumer)
                                except a.ArtifactObservationError:pass
                                else:raise AssertionError('pending native result admitted work')
                                assert result.acknowledged==consumer.commit==[None]
                                if case.startswith(('consume','ack')):
                                    try:m._consume_directory_policy(owner,consumer,actual._replace())
                                    except a.ArtifactObservationError:pass
                                    else:raise AssertionError('copied pending result consumed')
                                    assert consumer.consumption==consumer.commit==[None]
                                    assert result.raw[0] is actual.raw and ledger.failed==[False]
                                    if case=='consume_wrong_actor':
                                        import threading
                                        consumption_errors=[]
                                        def consume_from_wrong_thread():
                                            try:m._consume_directory_policy(owner,consumer,actual)
                                            except BaseException as exc:
                                                consumption_errors.append((type(exc),
                                                    exc.__context__ is None,
                                                    getattr(exc,'failed_owner',None) is owner))
                                        worker=threading.Thread(target=consume_from_wrong_thread)
                                        worker.start();worker.join(5)
                                        assert not worker.is_alive()
                                        expected_error=(a.ArtifactObservationError,True,True)
                                        assert consumption_errors==[expected_error]
                                        assert consumer.consumption==consumer.commit==[None]
                                        assert ledger.failed==[False] and ledger.failure==[None]
                                        assert result.raw[0] is actual.raw
                                        assert phase.current[0] is phase.pending
                                    policy_original=m._directory_identity
                                    policy_events=[]
                                    if case=='consume_policy_failure':
                                        def refuse_policy(snapshot,uid):
                                            assert snapshot is actual.snapshot
                                            assert uid==operation.context[1]
                                            policy_original(snapshot,uid)
                                            policy_events.append(True)
                                            raise a.ArtifactObservationError(owner)
                                        m._directory_identity=refuse_policy
                                    try:
                                        try:commit=m._consume_directory_policy(owner,consumer,actual)
                                        except a.ArtifactObservationError as exc:
                                            assert case=='consume_policy_failure'
                                            assert exc.failed_owner is owner
                                            assert exc.__context__ is None
                                            assert policy_events==[True]
                                            assert ledger.failed==[True]
                                            assert ledger.failure[0] is operation
                                            assert result.raw[0] is result.unset
                                            assert result.snapshot==result.envelope==[None]
                                            assert consumer.consumption[0] is operation
                                            assert consumer.commit==result.acknowledged==[None]
                                            assert phase.current[0] is phase.failed
                                            assert progress[0] is resource.ordinal
                                        else:
                                            assert case in ('consume','consume_wrong_actor','ack',
                                                            'ack_wrong_actor','ack_late_failure')
                                            assert type(commit) is m._DirectoryPolicyCommit
                                            assert commit.identity==actual.snapshot.identity[:5]
                                            assert commit.owner is owner
                                            assert commit.operation is operation
                                            assert commit.resource is resource
                                            assert consumer.consumption[0] is actual
                                            assert consumer.commit[0] is commit
                                            assert m._prepared_directory_commit_tail(
                                                owner,consumer,actual,commit) is commit
                                            assert result.acknowledged==[None]
                                            assert phase.current[0] is phase.pending
                                            assert result.raw[0] is actual.raw
                                            try:m._consume_directory_policy(owner,consumer,actual)
                                            except a.ArtifactObservationError:pass
                                            else:
                                                raise AssertionError('policy consumed twice')
                                            assert consumer.commit[0] is commit
                                            assert ledger.failed==[False]
                                            if case.startswith('ack'):
                                                try:m._ack_directory_policy(
                                                    owner,consumer,actual,commit._replace())
                                                except a.ArtifactObservationError:pass
                                                else:raise AssertionError('copied commit ACKed')
                                                assert result.acknowledged==[None]
                                                if case=='ack_wrong_actor':
                                                    import threading
                                                    ack_errors=[]
                                                    def ack_from_wrong_thread():
                                                        try:m._ack_directory_policy(
                                                            owner,consumer,actual,commit)
                                                        except BaseException as exc:
                                                            ack_errors.append((type(exc),
                                                                exc.__context__ is None))
                                                    worker=threading.Thread(
                                                        target=ack_from_wrong_thread)
                                                    worker.start();worker.join(5)
                                                    assert not worker.is_alive()
                                                    expected=(a.ArtifactObservationError,True)
                                                    assert ack_errors==[expected]
                                                    assert result.acknowledged==[None]
                                                    assert consumer.consumption[0] is actual
                                                    assert result.raw[0] is actual.raw
                                                    assert phase.current[0] is phase.pending
                                                    assert ledger.failed==[False]
                                                ack_original=m._acked_directory_commit_tail
                                                ack_events=[]
                                                if case=='ack_late_failure':
                                                    def refuse_after_ack(*args):
                                                        assert ack_original(*args) is commit
                                                        ack_events.append(True)
                                                        raise a.ArtifactObservationError(owner)
                                                    m._acked_directory_commit_tail=refuse_after_ack
                                                try:
                                                    try:acked=m._ack_directory_policy(
                                                        owner,consumer,actual,commit)
                                                    except a.ArtifactObservationError as exc:
                                                        assert case=='ack_late_failure'
                                                        assert exc.failed_owner is owner
                                                        assert exc.__context__ is None
                                                        assert ack_events==[True]
                                                        assert ledger.failed==[True]
                                                        assert ledger.failure[0] is operation
                                                        assert operation.state==[True,True,True]
                                                        assert phase.current[0] is phase.failed
                                                    else:
                                                        assert case in ('ack','ack_wrong_actor')
                                                        assert acked is commit
                                                        assert ack_original(
                                                            owner,consumer,commit) is commit
                                                        assert phase.current[0] is phase.idle
                                                        assert ledger.failed==[False]
                                                finally:
                                                    m._acked_directory_commit_tail=ack_original
                                                assert result.acknowledged[0] is commit
                                                assert consumer.commit[0] is commit
                                                assert consumer.consumption[0] is commit
                                                assert result.raw[0] is result.unset
                                                assert result.snapshot==result.envelope==[None]
                                                assert result.category==[None]
                                                assert progress==[commit.next_ordinal,None]
                                                assert phase.result==ledger.inflight==[None]
                                                try:m._ack_directory_policy(
                                                    owner,consumer,actual,commit)
                                                except a.ArtifactObservationError:pass
                                                else:raise AssertionError('ACK replayed')
                                                assert result.acknowledged[0] is commit
                                                assert progress==[commit.next_ordinal,None]
                                    finally:m._directory_identity=policy_original
                            assert captured==[True]
                            assert ledger.counts==[counts[0]+1,counts[1]]
                            assert ledger.attempts[-1] is operation
                        finally:m._native_metadata_snapshot=snapshot_original
                    finally:
                        # Dispose only this synthetic fixture; no production ACK/refund.
                        assert ledger.attempts.pop() is operation
                        ledger.counts[0]=counts[0]
                        ledger.inflight[0]=None
                        ledger.failed[0]=False
                        ledger.failure[0]=None
                        phase.current[0]=phase.idle
                        phase.result[0]=None
                        operation.state[:]=[False,False,False]
                        operation.ended[0]=False
                        result.raw[0]=result.unset
                        result.snapshot[0]=result.envelope[0]=result.category[0]=None
                        consumer.consumption[0]=consumer.commit[0]=None
                        result.acknowledged[0]=None
                        # Disposable fixture teardown, never production rollback.
                        progress[0]=resource.ordinal
                        ledger.preparation[:]=preparation_before
                if case.startswith('active'):
                    # Guard-only synthetic ACTIVE state, not production admission.
                    # No native operation is called and all original cells restore.
                    try:m._active_directory_operation_tail(owner,consumer)
                    except a.ArtifactObservationError:pass
                    else:raise AssertionError('unused intent accepted as ACTIVE')
                    ledger.attempts.append(operation)
                    ledger.counts[0]=operation.budget[3]
                    ledger.inflight[0]=operation
                    phase.current[0]=phase.active
                    phase.result[0]=operation
                    operation.state[0]=True
                    try:
                        if case=='active_wrong_phase':phase.current[0]=phase.pending
                        elif case=='active_failed':ledger.failed[0]=True
                        elif case=='active_failure_record':ledger.failure[0]=object()
                        elif case=='active_missing_debit':ledger.counts[0]=counts[0]
                        elif case=='active_wrong_result':phase.result[0]=operation._replace()
                        try:active=m._active_directory_operation_tail(owner,consumer)
                        except a.ArtifactObservationError:assert case!='active'
                        else:assert case=='active' and active is operation
                    finally:
                        assert ledger.attempts.pop() is operation
                        ledger.counts[0]=counts[0]
                        ledger.inflight[0]=None
                        ledger.failed[0]=False
                        ledger.failure[0]=None
                        phase.current[0]=phase.idle
                        phase.result[0]=None
                        operation.state[0]=False
            finally:
                progress[1]=None
                result.consumer[0]=consumer
    assert counts==tuple(ledger.counts) and len(ledger.attempts)==attempts
    assert progress==[0,None] and held[5].progress is progress
    assert phase.current[0] is phase.idle and phase.result[0] is None
    assert foreign_calls==[] and not owner._failed and not owner._unknown
    seen.append(True)
trace_synthetic_boundary(a.StartupArtifactOwner._file.__code__,
                         'info = StartupArtifactOwner._fstat(self, fd, s, native_registration)',
                         prepare)
owner.read()
assert seen==[True] and owner._ready
assert owner.completed_binding()[4] is owner._original_buffer
owner.release()
assert owner._original_buffer==bytearray()
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
'''
    monkeypatch.setattr(base, 'SCRIPT', script)
    base.test_actual_entry_and_wrapper_files(tmp_path, mutation)


@pytest.mark.parametrize('field', ('resource', 'site', 'arguments'))
def test_operation_preparation_does_not_invoke_foreign_fields(field):
    from hmp_plugin import presentation_native_metadata as metadata
    from hmp_plugin import presentation_startup_artifacts as artifacts

    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign length')

        def __getitem__(self, index):
            calls.append('index')
            raise AssertionError('foreign index')

    owner = object()
    if field == 'resource':
        resource = Foreign()
    else:
        values = dict.fromkeys(artifacts._NativeMetadataResource._fields)
        values.update(owner=owner, site=(4, 'directory', 0), arguments=(1234,))
        values[field] = Foreign()
        resource = artifacts._NativeMetadataResource(**values)
    with pytest.raises(artifacts.ArtifactObservationError):
        metadata._prepare_metadata_operation(owner, resource)
    assert calls == []


def test_directory_consumer_preparation_refuses_foreign_operation():
    from hmp_plugin import presentation_native_metadata as metadata
    from hmp_plugin import presentation_startup_artifacts as artifacts

    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign operation getter')

    with pytest.raises(artifacts.ArtifactObservationError):
        metadata._prepare_directory_consumer(object(), Foreign())
    assert calls == []
