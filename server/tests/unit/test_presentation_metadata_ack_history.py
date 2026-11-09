"""Actual synthetic native ACK history; never a live host or user-data probe."""
import pytest

from . import test_presentation_entry_files as base
from .test_presentation_metadata_caller import test_fixed_directory_caller as _actual_caller


@pytest.mark.parametrize('history_case', ('normal', 'copied_commit', 'missing_commit'))
def test_actual_ack_retains_original_raw_free_history(tmp_path, monkeypatch, history_case):
    original_execute = base.test_actual_entry_and_wrapper_files

    def execute_with_history_probe(path, mutation):
        script = base.SCRIPT
        anchor = '            assert marker.state==[True,True,False]\n'
        probe = r'''
            assert metadata.commits==[returned] and metadata.commits[0] is returned
            consumer=returned.consumer
            assert consumer.history is metadata.commits and consumer.predecessors==()
            assert returned.operation.result.acknowledged[0] is returned
            assert m._acked_directory_commit_tail(owner,consumer,returned) is returned
            history_case=HISTORY_CASE
            if history_case!='normal':
                original_history=list(metadata.commits)
                if history_case=='copied_commit':
                    copied=returned._replace(identity=tuple(returned.identity))
                    assert copied is not returned
                    metadata.commits[0]=copied
                else:metadata.commits.clear()
                before=(tuple(ledger.counts),tuple(metadata.progress),
                        tuple(operation.result.acknowledged),tuple(ledger.attempts))
                try:m._acked_directory_commit_tail(owner,consumer,returned)
                except a.ArtifactObservationError:pass
                else:raise AssertionError('foreign/missing ACK history accepted')
                assert before==(tuple(ledger.counts),tuple(metadata.progress),
                               tuple(operation.result.acknowledged),tuple(ledger.attempts))
                # Restore this synthetic fixture only; production never repairs
                # foreign history or retries ambiguous native work.
                metadata.commits[:]=original_history
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
        monkeypatch.setattr(base, 'SCRIPT', script.replace(anchor, anchor + probe))
        original_execute(path, mutation)

    monkeypatch.setattr(base, 'test_actual_entry_and_wrapper_files', execute_with_history_probe)
    _actual_caller(tmp_path, monkeypatch, 'normal')
