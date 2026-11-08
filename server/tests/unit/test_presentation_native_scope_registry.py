"""Original scope registration DATA; no native effect or work-permission claim."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize('kind', ('probe', 'reader'))
@pytest.mark.parametrize('change', ('normal', 'copied_owner', 'foreign_owner', 'copied_registry',
                                  'guard_pair', 'copied_slot', 'foreign_slot'))
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
import hmp_plugin.presentation_startup_artifacts as am
record=owner._native_scope_registration
actual_guard=am._owner_guard
pure_calls=[]
def forbidden_guard(*args):pure_calls.append('guard');raise AssertionError('capture callback')
am._owner_guard=forbidden_guard
try:assert am._capture_native_scope(owner._origin,owner._cell,owner._root_cell) is record
finally:am._owner_guard=actual_guard
assert pure_calls==[]
assert _native_scope_current(owner,record) is record
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
if change=='copied_slot':owner._origin.native_registration_slot[0]=record._replace()
if change=='foreign_slot':owner._origin.native_registration_slot[0]=ForeignRegistration()
actual_guard=am._owner_guard
if change=='guard_pair':
    def changed_guard(target):
        value=actual_guard(target)
        if target is owner:
            copied=record._replace()
            owner._native_scope_registration=copied
            registry[record.index]=copied
            am._owner_guard=actual_guard
        return value
    am._owner_guard=changed_guard
try:observed=_native_scope_current(owner,record)
except ArtifactObservationError:assert change!='normal'
else:assert change=='normal' and observed is record
am._owner_guard=actual_guard
assert calls==[]
# Fixture restoration tests only data-shape custody, never operation recovery.
owner._native_scope_registration=record
registry[record.index]=record
owner._origin.native_registration_slot[:]=[record]
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


@pytest.mark.parametrize('kind', ('probe', 'reader'))
@pytest.mark.parametrize('change', ('foreign_slot', 'foreign_scope_slot', 'coherent_roots'))
def test_registration_rejoins_before_publication(tmp_path, monkeypatch, kind, change):
    from . import test_presentation_cache_probe as probe
    from . import test_presentation_cache_reader as reader
    from . import test_presentation_entry_files as runner

    actual_run = runner.test_actual_entry_and_wrapper_files
    klass, error, module, slot = (('RuntimeCacheProbeOwner', 'CacheProbeError', 'pm',
                                  '_runtime_cache_probe_cell') if kind == 'probe' else
                                 ('DeclaredCacheReadOwner', 'CacheReadError', 'cm',
                                  '_cache_read_cell'))
    marker = f'owner={klass}.retain(continuation,index)'
    injected = r'''
import hmp_plugin.presentation_startup_artifacts as am
actual_register=am._register_native_scope
foreign_calls=[]
foreign=object()
held=[]
def changed_register(target,scope,cell,root):
    registry=scope.native_files.ledger.scopes
    held.extend((target,registry,len(registry)))
    actual_guard=am._owner_guard
    calls=[0]
    def changed_guard(value):
        result=actual_guard(value)
        if value is target:
            calls[0]+=1
            if calls[0]==2:
                if CHANGE=='foreign_slot':target._native_scope_registration=foreign
                elif CHANGE=='foreign_scope_slot':scope.native_registration_slot[0]=foreign
                else:
                    newcell=tuple(list(cell));newroot=tuple(list(root))
                    target._cell=MODULE._CELL=newcell
                    target._root_cell=MODULE._ROOT=newroot
                    setattr(scope.activation,SLOT,newroot)
        return result
    am._owner_guard=changed_guard
    try:return actual_register(target,scope,cell,root)
    finally:am._owner_guard=actual_guard
am._register_native_scope=changed_register
try:
    try:CLASS.retain(continuation,index)
    except ERROR as refused:
        assert refused.failed_owner is held[0] and held[0]._failed
        assert len(held[1])==held[2]
        if CHANGE=='foreign_slot':assert held[0]._native_scope_registration is foreign
        if CHANGE=='foreign_scope_slot':
            assert held[0]._origin.native_registration_slot[0] is foreign
    else:raise AssertionError('callback replacement adopted')
finally:am._register_native_scope=actual_register
assert foreign_calls==[]
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change)).replace('MODULE', module).replace('SLOT', repr(slot))
    injected = injected.replace('CLASS', klass).replace('ERROR', error)

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    if kind == 'probe':
        probe.test_fresh_cache_probe(tmp_path, monkeypatch, 'missing')
    else:
        reader.test_declared_cache_reader(tmp_path, monkeypatch, 'normal')
