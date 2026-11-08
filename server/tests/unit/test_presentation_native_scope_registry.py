"""Original scope registration DATA; no native effect or work-permission claim."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('probe', 'reader'))
@pytest.mark.parametrize('change', ('normal', 'copied_owner', 'foreign_owner', 'copied_registry'))
def test_original_native_scope_registration(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_cache_reader as reader
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    klass = 'RuntimeCacheProbeOwner' if kind == 'probe' else 'DeclaredCacheReadOwner'
    marker = f'owner={klass}.retain(continuation,index)'
    injected = r'''
from hmp_plugin.presentation_startup_artifacts import (
    _native_scope_current,ArtifactObservationError)
record=_native_scope_current(owner)
assert record.owner is owner and record.scope is owner._origin
assert record.cell is owner._cell and record.root is owner._root_cell
assert record.context is owner._origin.context
assert record.lineage is entry._scope.native_files
registry=record.lineage.ledger.scopes
assert registry[record.index] is record
calls=[]
class ForeignRegistration:
    def __getattr__(self,name):calls.append('get');raise AssertionError('foreign getter')
    def __eq__(self,other):calls.append('eq');raise AssertionError('foreign equality')
change=CHANGE
if change=='copied_owner':owner._native_scope_registration=record._replace()
if change=='foreign_owner':owner._native_scope_registration=ForeignRegistration()
if change=='copied_registry':registry[record.index]=record._replace()
try:observed=_native_scope_current(owner)
except ArtifactObservationError:assert change!='normal'
else:assert change=='normal' and observed is record
assert calls==[]
# Fixture restoration tests only data-shape custody, never operation recovery.
owner._native_scope_registration=record
registry[record.index]=record
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    if kind == 'probe':
        probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')
    else:
        reader.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')
