"""Synthetic native-return snapshot drift; no live-host or user-data reads."""
from . import test_presentation_entry_files as base
from .test_presentation_metadata_caller import test_fixed_directory_caller as _actual_caller


def test_snapshot_constructor_cannot_replace_actual_native_identity(tmp_path, monkeypatch):
    original_execute = base.test_actual_entry_and_wrapper_files

    def execute_with_constructor_probe(path, mutation):
        script = base.SCRIPT
        replacements = [
            ("    captured=[];returns=[];native_entries=[];foreign_inner=[]", r'''
    captured=[];returns=[];native_entries=[];foreign_inner=[]
    snapshot_factory=a._NativeMetadataSnapshot.__new__
    snapshot_factory_descriptor=vars(a._NativeMetadataSnapshot)['__new__']
    constructor_calls=[];native_identities=[];snapshot_matches=[]
    def drift_snapshot(cls,identity,mtime):
        frame=sys._getframe(1)
        try:
            assert frame.f_code is a._native_metadata_snapshot.__code__
            assert cls is a._NativeMetadataSnapshot
        finally:frame=None
        constructor_calls.append(True)
        return snapshot_factory(cls,(identity[0]+1,*identity[1:]),mtime+1)
'''),
            ("            returns.append(True)", r'''
            native_identities.append(a._identity(arg.raw,True))
            snapshot_matches.append(arg.snapshot.identity==a._identity(arg.raw)
                                    and arg.snapshot.mtime==arg.raw.st_mtime)
            returns.append(True)
'''),
            ("    m._prepare_metadata_operation_with_custody=capture_factory", r'''
    a._NativeMetadataSnapshot.__new__=staticmethod(drift_snapshot)
    m._prepare_metadata_operation_with_custody=capture_factory
'''),
            ("        assert not gc.isenabled() and payload_reference() is None", r'''
        stage=dict(case='snapshot_constructor_drift',constructor_calls=len(constructor_calls),
                   native_entries=len(native_entries),producer_returns=len(returns),
                   snapshot_matches_native=snapshot_matches==[True],
                   commit_matches_native=(len(native_identities)==1
                                          and returned.identity==native_identities[0]),
                   payload_alive=payload_reference() is not None,
                   gc_disabled=not gc.isenabled(),marker_state=list(marker.state),
                   debit_preserved=ledger.counts==[counts[0]+1,counts[1]],
                   phase_idle=phase.current[0] is phase.idle)
        diagnostic_path=Path(sys.argv[1])/'caller-snapshot-constructor-stage.json'
        diagnostic_fd=os.open(diagnostic_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(diagnostic_fd,'w') as stream:json.dump(stage,stream,sort_keys=True)
        assert snapshot_matches==[True] and returned.identity==native_identities[0]
        assert not gc.isenabled() and payload_reference() is None
'''),
            ("        m._prepare_metadata_operation_with_custody=factory", r'''
        a._NativeMetadataSnapshot.__new__=snapshot_factory_descriptor
        m._prepare_metadata_operation_with_custody=factory
'''),
        ]
        for old, new in replacements:
            assert script.count(old) == 1, old
            script = script.replace(old, new)
        monkeypatch.setattr(base, 'SCRIPT', script)
        original_execute(path, mutation)

    monkeypatch.setattr(base, 'test_actual_entry_and_wrapper_files', execute_with_constructor_probe)
    _actual_caller(tmp_path, monkeypatch, 'normal')
