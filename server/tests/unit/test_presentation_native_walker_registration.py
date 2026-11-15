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


@pytest.mark.parametrize('change', ('source_fact', 'registration'))
def test_file_final_callback_cannot_publish_stale_fact(tmp_path, monkeypatch, change):
    from . import test_presentation_entry_files as runner
    from . import test_presentation_runtime_source_read as source

    actual_run = runner.test_actual_entry_and_wrapper_files
    marker = 'owner=RuntimeSourceReadOwner.retain(continuation,index)'
    injected = r'''
import hmp_plugin.presentation_startup_artifacts as am
import hmp_plugin.presentation_source_digest as dm
actual_fact=dm.fact;actual_walk=am._native_walk_scope
made=[None];changed=[]
def observed_fact(*args):
    value=actual_fact(*args)
    if value.root.owner is owner:made[0]=value
    return value
def changed_walk(target,registration):
    value=actual_walk(target,registration)
    if target is owner and made[0] is not None and not changed:
        changed.append(True)
        if CHANGE=='source_fact':
            original=made[0].source_hash
            copied=bytes(bytearray(original))
            assert copied==original and copied is not original
            made[0].root.effect.result=copied
        else:
            copied=registration._replace()
            owner._native_scope_registration=copied
            owner._origin.native_registration_slot[0]=copied
            registration.lineage.ledger.scopes[registration.index]=copied
    return value
dm.fact=observed_fact;am._native_walk_scope=changed_walk
try:
    try:owner.read()
    except RuntimeReadError:
        assert changed==[True] and owner._failed and not owner._ready
        assert owner._receipt is None and owner._read_fact is None
    else:raise AssertionError('final callback published stale source fact')
finally:dm.fact=actual_fact;am._native_walk_scope=actual_walk
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''.replace('CHANGE', repr(change))

    def injected_run(directory, mutation):
        assert runner.SCRIPT.count(marker) == 1
        monkeypatch.setattr(runner, 'SCRIPT', runner.SCRIPT.replace(marker, marker + injected))
        actual_run(directory, mutation)

    monkeypatch.setattr(runner, 'test_actual_entry_and_wrapper_files', injected_run)
    source.test_runtime_source_read(tmp_path, monkeypatch, 'normal')


def test_package_last_origin_callback_rejoins_registration(tmp_path, monkeypatch):
    from . import test_presentation_entry_files as runner
    from .test_presentation_gateway_approval import operator_composed_script

    script, mutation = operator_composed_script('links')
    marker = 'plugin = GatewayPackageOwner.verify_recipe(recipe)'
    assert script.count(marker) == 1
    injected = r'''
from hmp_plugin.presentation_gateway_package import PackageInventoryError
actual_origins=GatewayPackageOwner._origins
seen=[];changed=[]
def changed_origins(target):
    value=actual_origins(target)
    seen.append(target)
    if len(seen)==2:
        record=target._origin.native_registration_slot[0]
        copied=record._replace()
        target._native_scope_registration=copied
        target._origin.native_registration_slot[0]=copied
        record.lineage.ledger.scopes[record.index]=copied
        changed.append(target)
    return value
GatewayPackageOwner._origins=changed_origins
try:
    try:GatewayPackageOwner.verify_recipe_source_hashes(recipe,entry)
    except PackageInventoryError as refused:
        target=refused.failed_owner
        assert changed==[target] and target._failed and not target._ready
        assert target._fact is None and target._fact_cell is None
        assert target._origin.activation._package_fact_cell is None
    else:raise AssertionError('last origins callback published replaced registration')
finally:GatewayPackageOwner._origins=actual_origins
print(json.dumps({'mutation':mutation,'runtime_admitted':False}))
raise SystemExit(0)
'''
    monkeypatch.setattr(runner, 'SCRIPT', script.replace(marker, injected))
    runner.test_actual_entry_and_wrapper_files(tmp_path, mutation)
