"""Fixed file walkers receive held provenance DATA, never path/IO authority."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('source', 'cache'))
@pytest.mark.parametrize('change', ('normal', 'copy_argument', 'missing_argument', 'paired_copy'))
def test_file_walker_holds_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_reader as cache
    from . import test_presentation_entry_files as runner
    from . import test_presentation_runtime_source_read as source

    actual_run = runner.test_actual_entry_and_wrapper_files
    klass, error = (('RuntimeSourceReadOwner', 'RuntimeReadError') if kind == 'source'
                    else ('DeclaredCacheReadOwner', 'CacheReadError'))
    marker = f'owner={klass}.retain(continuation,index)'
    injected = r'''
from hmp_plugin.presentation_startup_artifacts import StartupArtifactOwner
held=owner._origin.native_registration_slot[0]
actual_file=StartupArtifactOwner._file
calls=[]
def held_file(target,expected,native_registration=None):
    assert target is owner and native_registration is held
    calls.append('file')
    argument=native_registration
    if CHANGE=='copy_argument':argument=held._replace()
    if CHANGE=='missing_argument':argument=None
    if CHANGE=='paired_copy':
        copied=held._replace()
        owner._native_scope_registration=copied
        owner._origin.native_registration_slot[0]=copied
        held.lineage.ledger.scopes[held.index]=copied
    return actual_file(target,expected,argument)
StartupArtifactOwner._file=held_file
try:
    try:owner.read()
    except ERROR:
        assert CHANGE!='normal' and owner._failed
        assert owner._origin.records==[] and owner._bytes_read==0
    else:assert CHANGE=='normal' and owner._ready
finally:StartupArtifactOwner._file=actual_file
assert calls==['file']
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change)).replace('ERROR', error)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    if kind == 'source':
        source.test_runtime_source_read(tmp_path, monkeypatch, 'normal')
    else:
        cache.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')
