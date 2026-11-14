"""Actual synthetic native ACK history; never a live host or user-data probe."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_metadata_caller import test_fixed_directory_caller as _actual_caller


@pytest.mark.parametrize('history_case', ('normal', 'copied_commit', 'missing_commit',
                                          'foreign_ordinal', 'foreign_next', 'append_interrupt'))
def test_actual_ack_retains_original_raw_free_history(tmp_path, monkeypatch, history_case):
    original_execute = base.test_actual_entry_and_wrapper_files

    def execute_with_history_probe(path, mutation):
        script = base.SCRIPT
        anchor = '            assert marker.state==[True,True,False]\n'
        probe = r'''
            assert metadata.commits==[returned] and metadata.commits[0] is returned
            consumer=returned.consumer
            assert consumer.history is metadata.commits and consumer.predecessor is None
            assert returned.operation.result.acknowledged[0] is returned
            assert m._acked_directory_history_tail(owner,consumer,returned) is returned
            history_case=HISTORY_CASE
            if history_case!='normal':
                original_history=list(metadata.commits)
                if history_case=='copied_commit':
                    copied=returned._replace(identity=tuple(returned.identity))
                    assert copied is not returned
                    metadata.commits[0]=copied
                elif history_case=='missing_commit':metadata.commits.clear()
                else:
                    class Foreign:
                        def __eq__(self,other):
                            raise AssertionError('foreign ordinal equality must not run')
                        def __index__(self):
                            raise AssertionError('foreign ordinal indexing must not run')
                    returned=(returned._replace(ordinal=Foreign())
                              if history_case=='foreign_ordinal'
                              else returned._replace(next_ordinal=Foreign()))
                before=(tuple(ledger.counts),tuple(metadata.progress),
                        tuple(operation.result.acknowledged),tuple(ledger.attempts))
                try:m._acked_directory_history_tail(owner,consumer,returned)
                except a.ArtifactObservationError:pass
                else:raise AssertionError('foreign/missing ACK history accepted')
                assert before==(tuple(ledger.counts),tuple(metadata.progress),
                               tuple(operation.result.acknowledged),tuple(ledger.attempts))
                # Restore this synthetic fixture only; production never repairs
                # foreign history or retries ambiguous native work.
                metadata.commits[:]=original_history
                returned=original_history[0]
            assert native_entries==[True] and returns==[True]
            stage=dict(history_case=history_case,native_entries=len(native_entries),
                       original_ack=metadata.commits[0] is returned,
                       payload_alive=payload_reference() is not None,
                       gc_disabled=not gc.isenabled(),debit_preserved=True)
            diagnostic=Path(sys.argv[1])/'metadata-ack-history-stage.json'
            diagnostic_fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(diagnostic_fd,'w') as stream:json.dump(stage,stream,sort_keys=True)
'''.replace('HISTORY_CASE', repr(history_case))
        assert script.count(anchor) == 1
        script = script.replace(anchor, anchor + probe)
        if history_case == 'append_interrupt':
            setup = '    def lose_return(frame,event,arg):\n'
            replacement = r'''
    history_injected=[]
    ack_lines,ack_start=inspect.getsourcelines(m._ack_directory_policy)
    cursor_lines=[ack_start+i for i,line in enumerate(ack_lines)
                  if line.strip()=='consumer.resource.metadata.progress[0] = commit.next_ordinal']
    assert len(cursor_lines)==1
    def lose_return(frame,event,arg):
        if frame.f_code is m._ack_directory_policy.__code__:
            if event=='line' and frame.f_lineno==cursor_lines[0]:
                assert history_injected==[] and len(metadata.commits)==1
                assert metadata.progress[0]==0
                assert metadata.commits[0] is captured[0][0].result.acknowledged[0]
                history_injected.append(True)
                sys.settrace(trace_before)
                raise RuntimeError('synthetic after-history before-cursor interruption')
            return lose_return
'''
            assert script.count(setup) == 1
            script = script.replace(setup, replacement)
            allowed = "case not in ('normal','late_marker_drift','disposal_revocation')"
            assert script.count(allowed) == 1
            script = script.replace(allowed, allowed[:-1] + ",'append_interrupt')")
            normal = "        if case=='normal':\n"
            interrupted = r'''
        if case=='append_interrupt':
            assert history_injected==[True] and metadata.progress[0]==0
            assert metadata.progress[1] is operation.result.consumer[0]
            assert len(metadata.commits)==1
            assert metadata.commits[0] is operation.result.acknowledged[0]
            assert ledger.failed==[True] and ledger.failure[0] is operation
            assert phase.current[0] is phase.failed
            assert marker.state==[True,True,False]
            diagnostic=Path(sys.argv[1])/'metadata-ack-history-stage.json'
            diagnostic_fd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            stage=dict(history_case='append_interrupt',native_entries=len(native_entries),
                       producer_returns=len(returns),injected=len(history_injected),
                       history_retained=True,cursor=metadata.progress[0],
                       payload_alive=payload_reference() is not None,
                       gc_disabled=not gc.isenabled(),phase_failed=True)
            with os.fdopen(diagnostic_fd,'w') as stream:json.dump(stage,stream,sort_keys=True)
            seen.append(True)
            return
'''
            assert script.count(normal) == 1
            script = script.replace(normal, interrupted + normal)
        monkeypatch.setattr(base, 'SCRIPT', script)
        original_execute(path, mutation)

    monkeypatch.setattr(base, 'test_actual_entry_and_wrapper_files', execute_with_history_probe)
    _actual_caller(tmp_path, monkeypatch,
                   'append_interrupt' if history_case == 'append_interrupt' else 'normal')
